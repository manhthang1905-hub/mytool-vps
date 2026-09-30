"""Bình luận MỞ ĐẦU tự đăng (`vm/may_cmt.py::dang_binh_luan_moi`) + né tự trả lời
chính mình.

Bối cảnh: `vm/tokens/` và `vm/clients/` đang TRỐNG trên máy này (chưa OAuth kênh
nào) — không được gọi mạng thật. Mọi bài dưới đây tự dựng một `yt` giả (chỉ có
đúng các phương thức mã cần gọi) và tự trỏ các thư mục trạng thái vào `tmp_path`,
không đụng gì tới `vm/tokens`, `vm/clients`, `DONE/`, `CHANNEL/` thật của tool.

Ba điều canh:
1. YouTube Data API v3 KHÔNG có cách ghim (pin) — `post_seed_comment` chỉ được
   phép gọi `commentThreads().insert()`, không có gì gọi tới "pin"/"setPinned".
2. Đăng bình luận mở đầu phải NHỚ đã đăng (idempotent) — chạy lần hai không đăng lại.
3. Bot KHÔNG được tự trả lời một bình luận do CHÍNH kênh đăng (kể cả bình luận
   mở đầu vừa tự đăng ở #1).
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent


def _nap_may_cmt():
    spec = importlib.util.spec_from_file_location("vm_may_cmt", GOC / "vm" / "may_cmt.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def mod(tmp_path):
    """Một bản `may_cmt` với mọi thư mục trạng thái trỏ vào `tmp_path` - độc
    lập hoàn toàn với `vm/tokens`, `vm/clients`, `DONE/`, `CHANNEL/` thật."""
    m = _nap_may_cmt()
    # BASE_DIR giả = <tmp_path>/MyTool/vm -> DONE/CHANNEL "giả" nằm cạnh nó,
    # đúng nếp `os.path.dirname(BASE_DIR)` mà mã đang dùng.
    goc_gia = tmp_path / "MyTool"
    vm_gia = goc_gia / "vm"
    vm_gia.mkdir(parents=True)
    m.BASE_DIR = str(vm_gia)
    m.SEEDED_DIR = str(vm_gia / "da-dang-cmt-moi")
    os.makedirs(m.SEEDED_DIR, exist_ok=True)
    m.DRY_RUN = False
    return m


def _dung_goi_done(mod, kenh, ma_goi, tieu_de="Tiêu đề thật", binh_luan="Xin chào các bạn!"):
    """Dựng một gói DONE/<kenh>/<ma_goi>/ với 1-tieu-de.txt + 1-binh-luan.txt."""
    goc_done = Path(os.path.dirname(mod.BASE_DIR)) / "DONE" / kenh / ma_goi
    goc_done.mkdir(parents=True, exist_ok=True)
    (goc_done / "1-tieu-de.txt").write_text(f"TITLE: {tieu_de}\n", encoding="utf-8")
    if binh_luan is not None:
        (goc_done / "1-binh-luan.txt").write_text(binh_luan, encoding="utf-8")
    return goc_done


class _YTGia:
    """YouTube client giả - CHỈ có đúng các phương thức mã thật gọi tới, để lộ
    ngay nếu có chỗ nào lỡ gọi một API không tồn tại (vd một API "pin" tưởng
    tượng). Dáng gọi CHUỖI giống googleapiclient thật:
    `yt.channels().list(...).execute()`, `yt.commentThreads().insert(...).execute()`.
    """

    def __init__(self, video_items=None):
        self._video_items = video_items or []
        self.da_insert = []          # ghi lại MỌI lời gọi commentThreads().insert(...)
        self._modo = None
        self._last_list_kw = {}

    def channels(self):
        self._modo = "channels"
        return self

    def list(self, **kw):
        self._last_list_kw = kw
        return self

    def playlistItems(self):
        self._modo = "playlist"
        return self

    def commentThreads(self):
        self._modo = "commentThreads"
        return self

    def insert(self, part=None, body=None):
        self.da_insert.append({"part": part, "body": body})
        return self

    def execute(self):
        if self._modo == "playlist":
            return {"items": self._video_items}
        if self._modo == "commentThreads":
            return {"id": "thread123"}
        if self._modo == "channels":
            if self._last_list_kw.get("part") == "id,snippet":
                return {"items": [{"id": "UCabc123", "snippet": {"title": "Kênh test"}}]}
            if self._last_list_kw.get("part") == "contentDetails":
                return {"items": [{"contentDetails": {
                    "relatedPlaylists": {"uploads": "UUabc123"}}}]}
        return {"items": []}


def _video_item(video_id, title, published_at="2026-09-26T00:00:00Z"):
    return {"snippet": {"title": title, "publishedAt": published_at},
            "contentDetails": {"videoId": video_id}}


def _http_error(mod, noi_dung: bytes, status: int = 403):
    """Dựng một `HttpError` THẬT (đúng loại mã `except HttpError` bên trong
    `dang_binh_luan_moi`) mà KHÔNG gọi mạng: `httplib2.Response` chỉ là một
    dict-like mô tả status, không mở kết nối nào."""
    import httplib2

    return mod.HttpError(httplib2.Response({"status": status}), noi_dung, uri="http://x")


# ── 1. Khớp tiêu đề (hàm thuần, không gọi mạng) ─────────────────────────────


def test_khop_tieu_de_giong_het(mod):
    assert mod._khop_tieu_de("Tiêu đề thật", "Tiêu đề thật") is True


def test_khop_tieu_de_gan_dung_van_khop(mod):
    assert mod._khop_tieu_de("Tiêu đề thật.", "Tiêu đề thật") is True


def test_khop_tieu_de_khac_han_khong_khop(mod):
    assert mod._khop_tieu_de("Video về mèo", "Video về chó") is False


def test_khop_tieu_de_rong_khong_khop(mod):
    assert mod._khop_tieu_de("", "Tiêu đề thật") is False


# ── 2. post_seed_comment() CHỈ gọi insert() — không có gì gọi "pin" ─────────


def test_post_seed_comment_chi_goi_insert_khong_co_pin(mod):
    yt = _YTGia()
    ra = mod.post_seed_comment(yt, "VID123", "  Xin chào!  ")
    assert ra == {"id": "thread123"}
    assert len(yt.da_insert) == 1
    goi = yt.da_insert[0]
    assert goi["part"] == "snippet"
    assert goi["body"]["snippet"]["videoId"] == "VID123"
    assert goi["body"]["snippet"]["topLevelComment"]["snippet"]["textOriginal"] == "Xin chào!"
    # KHÔNG có khoá nào liên quan "pin" trong toàn bộ thân gọi - xác nhận API
    # không hỗ trợ ghim nên mã cũng không cố nhét gì vào đó.
    assert "pin" not in json.dumps(goi["body"]).lower()
    assert not hasattr(yt, "setPinned")


def test_khong_co_ma_nao_goi_api_pin_tuong_tuong(mod):
    """API thật (googleapiclient) không có method pin/setPinned trên resource
    comments/commentThreads — bài này canh KHÔNG BAO GIỜ có mã nào trong
    may_cmt.py gọi một cái tên như vậy (grep tĩnh, không cần mạng)."""
    noi_dung = (GOC / "vm" / "may_cmt.py").read_text(encoding="utf-8")
    # Mau CO THAT cua mot loi goi/truong API (khong phai chu "isPinned" nhac
    # toi trong loi ghi chu tieng Viet - ghi chu dung khong dau ":"/"(" ngay sau).
    for tu_cam in (".setPinned(", '"isPinned":', ".pin()"):
        assert tu_cam not in noi_dung, (
            f"'{tu_cam}' xuất hiện trong may_cmt.py — YouTube Data API v3 KHÔNG "
            f"hỗ trợ ghim bình luận, đừng cố gọi API không tồn tại.")


# ── 3. tim_video_id_theo_tieu_de(): chọn video MỚI NHẤT khớp tiêu đề ────────


def test_tim_video_id_chon_video_moi_nhat_khop(mod):
    yt = _YTGia(video_items=[
        _video_item("CU", "Tiêu đề thật", published_at="2026-01-01T00:00:00Z"),
        _video_item("MOI", "Tiêu đề thật", published_at="2026-09-26T00:00:00Z"),
        _video_item("KHAC", "Video khác hẳn", published_at="2026-09-25T00:00:00Z"),
    ])
    ra = mod.tim_video_id_theo_tieu_de(yt, "UUabc", "Tiêu đề thật")
    assert ra == "MOI"


def test_tim_video_id_khong_khop_tra_none(mod):
    yt = _YTGia(video_items=[_video_item("V1", "Chẳng liên quan gì")])
    assert mod.tim_video_id_theo_tieu_de(yt, "UUabc", "Tiêu đề thật") is None


# ── 4. dang_binh_luan_moi(): quét gói DONE, đăng, và NHỚ (idempotent) ───────


def test_dang_binh_luan_moi_dang_va_ghi_nho(mod, monkeypatch):
    kenh = "TL9-T9"
    _dung_goi_done(mod, kenh, f"{kenh}-0001", tieu_de="Video một", binh_luan="Chào video 1")

    yt = _YTGia(video_items=[_video_item("VID1", "Video một")])

    monkeypatch.setattr(mod, "load_credentials", lambda ch: object())
    monkeypatch.setattr(mod, "youtube_from_creds", lambda creds: yt)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)   # khong cho that trong test

    ket = mod.dang_binh_luan_moi(kenh)
    assert ket == {"da_dang": 1, "cho_video": 0, "loi": 0}
    assert len(yt.da_insert) == 1
    assert yt.da_insert[0]["body"]["snippet"]["videoId"] == "VID1"
    assert f"{kenh}-0001" in mod._seeded_set(kenh)

    # Chạy lại lần hai — KHÔNG được đăng thêm lần nữa (idempotent).
    ket2 = mod.dang_binh_luan_moi(kenh)
    assert ket2 == {"da_dang": 0, "cho_video": 0, "loi": 0}
    assert len(yt.da_insert) == 1, "đăng trùng — gói đã seed rồi mà vẫn gọi insert lần nữa"


def test_dang_binh_luan_moi_video_chua_len_song_thi_cho(mod, monkeypatch):
    kenh = "TL9-T9"
    _dung_goi_done(mod, kenh, f"{kenh}-0001", tieu_de="Video chưa lên", binh_luan="Chào!")

    yt = _YTGia(video_items=[])  # chưa có video nào khớp — vd còn hẹn giờ
    monkeypatch.setattr(mod, "load_credentials", lambda ch: object())
    monkeypatch.setattr(mod, "youtube_from_creds", lambda creds: yt)

    ket = mod.dang_binh_luan_moi(kenh)
    assert ket == {"da_dang": 0, "cho_video": 1, "loi": 0}
    assert yt.da_insert == []
    assert f"{kenh}-0001" not in mod._seeded_set(kenh), (
        "gói CHƯA đăng được mà bị đánh dấu seeded — lần sau sẽ mất video này vĩnh viễn")


def test_dang_binh_luan_moi_khong_co_token_thi_bo_qua_im_lang(mod, monkeypatch):
    kenh = "TL9-T9"
    _dung_goi_done(mod, kenh, f"{kenh}-0001")
    monkeypatch.setattr(mod, "load_credentials", lambda ch: None)
    ket = mod.dang_binh_luan_moi(kenh)
    assert ket == {"da_dang": 0, "cho_video": 0, "loi": 0}


def test_dang_binh_luan_moi_khong_co_goi_done_thi_khong_lam_gi(mod, monkeypatch):
    """Nếp vm/ đặt cạnh Chrome, không có DONE/CHANNEL cạnh nó — phải chạy êm,
    không lỗi, không gọi tới load_credentials (đỡ 1 lần gọi phí)."""
    goi_load = []
    monkeypatch.setattr(mod, "load_credentials", lambda ch: goi_load.append(ch))
    ket = mod.dang_binh_luan_moi("KENH-KHONG-CO-DONE")
    assert ket == {"da_dang": 0, "cho_video": 0, "loi": 0}
    assert goi_load == [], "không có gói nào cần đăng thì không cần đọc token làm gì"


def test_dang_binh_luan_moi_loi_quota_thi_dung_khong_seed(mod, monkeypatch):
    kenh = "TL9-T9"
    _dung_goi_done(mod, kenh, f"{kenh}-0001", tieu_de="V1", binh_luan="Chào")
    _dung_goi_done(mod, kenh, f"{kenh}-0002", tieu_de="V2", binh_luan="Chào 2")

    yt = _YTGia(video_items=[_video_item("VID1", "V1"), _video_item("VID2", "V2")])

    def _insert_loi(_yt, _vid, _text):
        raise _http_error(mod, b"quotaExceeded")

    monkeypatch.setattr(mod, "post_seed_comment", _insert_loi)
    monkeypatch.setattr(mod, "load_credentials", lambda ch: object())
    monkeypatch.setattr(mod, "youtube_from_creds", lambda creds: yt)

    ket = mod.dang_binh_luan_moi(kenh)
    assert ket["da_dang"] == 0
    assert ket["loi"] == 1
    # Dừng NGAY ở gói đầu gặp lỗi quota — gói thứ hai chưa được thử.
    assert f"{kenh}-0001" not in mod._seeded_set(kenh)
    assert f"{kenh}-0002" not in mod._seeded_set(kenh)


def test_dang_binh_luan_moi_video_tat_binh_luan_thi_bo_han(mod, monkeypatch):
    """commentsDisabled là lỗi VĨNH VIỄN (video đó tắt bình luận) - khác lỗi
    quota (tạm thời): phải đánh dấu seeded để KHÔNG thử lại vô ích mỗi ngày."""
    kenh = "TL9-T9"
    _dung_goi_done(mod, kenh, f"{kenh}-0001", tieu_de="V1", binh_luan="Chào")
    yt = _YTGia(video_items=[_video_item("VID1", "V1")])

    def _insert_loi(_yt, _vid, _text):
        raise _http_error(mod, b"commentsDisabled")

    monkeypatch.setattr(mod, "post_seed_comment", _insert_loi)
    monkeypatch.setattr(mod, "load_credentials", lambda ch: object())
    monkeypatch.setattr(mod, "youtube_from_creds", lambda creds: yt)

    ket = mod.dang_binh_luan_moi(kenh)
    assert ket["loi"] == 1
    assert f"{kenh}-0001" in mod._seeded_set(kenh)


# ── 5. Né tự trả lời chính mình ──────────────────────────────────────────────


def test_top_comment_info_tra_ve_id_kenh_tac_gia(mod):
    thread = {"snippet": {"topLevelComment": {"id": "c1", "snippet": {
        "authorDisplayName": "Ai đó",
        "textOriginal": "Hay quá",
        "authorChannelId": {"value": "UCviewer"},
    }}}}
    cid, ten, text, author_ch = mod.top_comment_info(thread)
    assert (cid, ten, text, author_ch) == ("c1", "Ai đó", "Hay quá", "UCviewer")


def test_la_cua_chinh_kenh(mod):
    assert mod._la_cua_chinh_kenh("UCabc", "UCabc") is True
    assert mod._la_cua_chinh_kenh("UCkhac", "UCabc") is False
    assert mod._la_cua_chinh_kenh("", "UCabc") is False
    assert mod._la_cua_chinh_kenh(None, "UCabc") is False


# ── 6. Báo cáo "cần ghim" — việc tay còn lại, kèm link thẳng ────────────────


def test_ghi_can_ghim_tao_file_va_co_link(mod):
    thu_muc_channel = Path(os.path.dirname(mod.BASE_DIR)) / "CHANNEL" / "TL9-T9"
    thu_muc_channel.mkdir(parents=True)
    mod._ghi_can_ghim("TL9-T9", "Video một", "VID1", "Chào các bạn!\nCòn nữa")
    noi_dung = (thu_muc_channel / "can-ghim.md").read_text(encoding="utf-8")
    assert "https://www.youtube.com/watch?v=VID1" in noi_dung
    assert "Video một" in noi_dung
    assert "Ghim" in noi_dung


def test_ghi_can_ghim_khong_co_thu_muc_channel_thi_im_lang(mod):
    # Không tạo CHANNEL/TL9-T9 — hàm phải không ném lỗi.
    mod._ghi_can_ghim("TL9-T9", "Video một", "VID1", "Chào")
