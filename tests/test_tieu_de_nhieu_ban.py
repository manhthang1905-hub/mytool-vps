"""Việc 5 (29/09/2026) — N BẢN TIÊU ĐỀ + CHẤM THEO CTR THẬT, nhánh `nguyen_goc`
của `core/auto_khau.py` (`_chon_tieu_de_nguyen_goc`, `_de_bai_n_ban_tieu_de`,
`_doc_nhieu_tieu_de`, `_du_lieu_cham_tieu_de`).

Bài kiểm chốt (theo `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`, Việc 5):
  1. Đối chứng LUÔN CÓ MẶT trong rổ ứng viên.
  2. `goi_chat` giả — chọn đúng bản do bộ chấm trả về.
  3. Đường lui: sinh N bản hỏng / chấm hỏng đều rơi về đối chứng, không vỡ lượt.
  4. Trần 100 ký tự cho tiêu đề CUỐI CÙNG.
  5. `so_tieu_de: 0` giữ đúng nết cũ (không chấm nhiều bản).
  6. `1-tieu-de-cham.json` ghi đủ trường cho hồ sơ video đọc lại.
"""

from __future__ import annotations

import json
import os
import tempfile

from core.auto import LuotChay, TrangThaiKhau
from core.auto_khau import (BoiCanh, _doc_nhieu_tieu_de, _khau_kich_ban,
                            _de_bai_n_ban_tieu_de)
from core.kenh import Kenh


class _KetGia:
    def __init__(self, text, title, video_id):
        self.text = text
        self.title = title
        self.video_id = video_id
        self.loi = ""


def _kenh(**kw):
    mac = dict(ma="TLX-T7", ngon_ngu="ja", voice_id="v", phut_muc_tieu=10,
               ky_tu_moi_phut=300, che_do_tieu_de="nguyen_goc",
               prompt={"2-viet.md": "viet <<CHARS>> <<COMPETITOR_TRANSCRIPT>>"})
    mac.update(kw)
    return Kenh(**mac)


class _GoiChatKichBan:
    """Phân biệt BA loại lượt gọi chữ (không ảnh) bằng dấu hiệu trong lời nhắc:
    NẮN KHUÔN (`de_bai_nan_khuon`), SINH N BẢN (`_de_bai_n_ban_tieu_de`), và
    CHẤM (`_KHUON_CHAM_TIEU_DE`) — khác `_GoiChat` của
    `test_tieu_de_nguyen_goc.py` (chỉ cần phân biệt ảnh/không ảnh)."""

    def __init__(self, *, n_ban=None, cham=None, nan_khuon=None,
                loi_n_ban=False, loi_cham=False):
        self.lan = []
        self._n_ban = n_ban
        self._cham = cham
        self._nan_khuon = nan_khuon
        self._loi_n_ban = loi_n_ban
        self._loi_cham = loi_cham

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        anh = kw.get("anh", "")
        self.lan.append({"loi_nhac": loi_nhac, "anh": anh, "khoa": khoa})
        if anh:
            return "bìa đọc được"
        if "ỨNG VIÊN tiêu đề cho MỘT video" in loi_nhac:
            if self._loi_cham:
                raise RuntimeError("chấm hỏng (giả lập)")
            return self._cham if self._cham is not None else '{"chon": "A", "ly_do": "ok"}'
        if "KHUÔN CỦA KÊNH" in loi_nhac:
            return self._nan_khuon if self._nan_khuon is not None else "TITLE: bản nắn khuôn\n"
        if "cách đặt tên KHÁC NHAU" in loi_nhac:
            if self._loi_n_ban:
                raise RuntimeError("sinh N bản hỏng (giả lập)")
            return self._n_ban if self._n_ban is not None else ""
        return "本" * 4000


def _bc(d, goi_chat, lay=None, tai_anh=None):
    return BoiCanh(goc=".", kenh=None, goi_chat=goi_chat,
                   on_log=lambda _s: None, ngu=lambda _g: None,
                   lay_tu_lieu=lay, tai_anh=tai_anh)


def _chay(bc, kenh, d, dau_vao):
    bc.kenh = kenh
    luot = LuotChay(ma_kenh=kenh.ma, ma_luot="T01", thu_muc=d, dau_vao=dau_vao)
    lam = _khau_kich_ban(bc)
    lam(luot, TrangThaiKhau(ma="kich-ban"))


def _tieu_de_da_ghi(d):
    with open(os.path.join(d, "1-tieu-de.txt"), encoding="utf-8") as f:
        return f.read()


def _tieu_de_cham_json(d):
    duong = os.path.join(d, "1-tieu-de-cham.json")
    if not os.path.isfile(duong):
        return None
    with open(duong, encoding="utf-8") as f:
        return json.load(f)


_LAY_GIA = lambda *a, **k: _KetGia("G" * 800, "対抗の元タイトル", "abc123")  # noqa: E731


# ── `_de_bai_n_ban_tieu_de` / `_doc_nhieu_tieu_de` (đơn vị, thuần) ──────────


class TestDeBaiVaDocNhieuTieuDe:
    def test_de_bai_co_so_ban_va_tieu_de_nguon(self):
        de_bai = _de_bai_n_ban_tieu_de("tiêu đề nguồn", 4)
        assert "tiêu đề nguồn" in de_bai
        assert "4" in de_bai

    def test_de_bai_kem_nhan_khi_co(self):
        de_bai = _de_bai_n_ban_tieu_de("x", 3, "心理学")
        assert "心理学" in de_bai

    def test_doc_nhieu_tieu_de_boc_moi_dong_title(self):
        chu = "TITLE: bản một\nTITLE: bản hai\nTITLE:bản ba\n"
        ds = _doc_nhieu_tieu_de(chu, 5)
        assert ds == ["bản một", "bản hai", "bản ba"]

    def test_doc_nhieu_tieu_de_bo_trung_va_cham_tran(self):
        chu = "\n".join("TITLE: bản {0}".format(i % 2) for i in range(10))
        ds = _doc_nhieu_tieu_de(chu, 5)
        assert ds == ["bản 0", "bản 1"]  # bỏ trùng, không đủ 5 thì trả hết

    def test_doc_nhieu_tieu_de_khong_co_dong_nao(self):
        assert _doc_nhieu_tieu_de("không có gì liên quan cả", 4) == []
        assert _doc_nhieu_tieu_de("", 4) == []


# ── Đối chứng luôn có mặt + đường lui ────────────────────────────────────────


class TestDoiChungVaDuongLui:
    def test_sinh_n_ban_rong_thi_giu_doi_chung(self):
        """`_GoiChat` trả rỗng cho lượt sinh N bản (không có dòng TITLE nào) —
        rổ ứng viên chỉ còn đối chứng, `cham_va_chon` tự chọn nó mà không cần
        gọi AI chấm (đường `len(ban) == 1` của `viet_nhieu_ban.cham_va_chon`)."""
        goi = _GoiChatKichBan(n_ban="không có gì để trả cả")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
            cham = _tieu_de_cham_json(d)
        assert "TITLE: 対抗の元タイトル" in noi_dung
        assert cham is not None
        assert cham["chon"] == 0
        assert cham["ten_chon"] == "đối chứng"
        assert len(cham["ung_vien"]) == 1

    def test_sinh_n_ban_hong_thi_giu_doi_chung_khong_vo_luot(self):
        goi = _GoiChatKichBan(loi_n_ban=True)
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "TITLE: 対抗の元タイトル" in noi_dung

    def test_cham_hong_thi_giu_doi_chung_khong_vo_luot(self):
        goi = _GoiChatKichBan(n_ban="TITLE: bản khác hẳn\n", loi_cham=True)
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
            cham = _tieu_de_cham_json(d)
        assert "TITLE: 対抗の元タイトル" in noi_dung
        assert cham["chon"] == 0
        assert "hỏng" in cham["ly_do"]

    def test_cham_tra_json_sai_dang_thi_giu_doi_chung(self):
        goi = _GoiChatKichBan(n_ban="TITLE: bản khác hẳn\n", cham="không phải JSON")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        # `cham_va_chon` tự rơi về số đo khi JSON hỏng — không ném lỗi ra ngoài
        # (đây là hành vi ĐÃ CÓ của `viet_nhieu_ban.cham_va_chon`), vẫn phải ra
        # một TITLE hợp lệ, không được vỡ lượt.
        assert "TITLE:" in noi_dung


# ── Chọn đúng bản bộ chấm trả về ─────────────────────────────────────────────


class TestChonBanTheoBoCham:
    def test_chon_ban_n_thu_hai_qua_cham(self):
        # Đối chứng = A, bản N đầu tiên = B — bộ chấm chọn B.
        goi = _GoiChatKichBan(n_ban="TITLE: bản hay hơn\nTITLE: bản khác\n",
                              cham='{"chon": "B", "ly_do": "giống dạng CTR cao"}')
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
            cham = _tieu_de_cham_json(d)
        assert "TITLE: bản hay hơn" in noi_dung
        assert cham["chon"] == 1
        assert cham["ten_chon"] == "bản 1"
        assert cham["tieu_de_chon"] == "bản hay hơn"
        assert cham["ly_do"] == "giống dạng CTR cao"
        assert [u["tieu_de"] for u in cham["ung_vien"]] == [
            "対抗の元タイトル", "bản hay hơn", "bản khác"]

    def test_nan_khuon_bat_them_mot_ung_vien(self, monkeypatch):
        import core.auto_khau as ak

        monkeypatch.setattr(ak, "tieu_de_thang_cua_kenh",
                            lambda goc, ma, toi_da=6: ["mẫu thắng 1", "mẫu thắng 2"])
        goi = _GoiChatKichBan(n_ban="", cham='{"chon": "B", "ly_do": "khuôn tốt"}')
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4, nan_khuon_tieu_de=True), d, {"link": "http://x"})
            cham = _tieu_de_cham_json(d)
        assert [u["ten"] for u in cham["ung_vien"]] == ["đối chứng", "nắn khuôn"]
        assert cham["chon"] == 1
        assert cham["tieu_de_chon"] == "bản nắn khuôn"


# ── Trần 100 ký tự ───────────────────────────────────────────────────────────


class TestTran100KyTu:
    def test_tieu_de_thang_dai_hon_100_bi_cat(self):
        ban_dai = "あ" * 150
        goi = _GoiChatKichBan(n_ban="TITLE: " + ban_dai,
                              cham='{"chon": "B", "ly_do": "dài nhưng thắng"}')
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=4), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        dong_title = [l for l in noi_dung.splitlines() if l.startswith("TITLE:")][0]
        tieu_de_ghi = dong_title[len("TITLE: "):]
        assert len(tieu_de_ghi) <= 100


# ── `so_tieu_de: 0` giữ nết cũ ───────────────────────────────────────────────


class TestSoTieuDeTat:
    def test_so_tieu_de_0_khong_chot_json_khong_goi_them(self):
        goi = _GoiChatKichBan()
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=0), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "TITLE: 対抗の元タイトル" in noi_dung
        assert _tieu_de_cham_json(d) is None
        # Không có lượt gọi nào cho NẮN KHUÔN / N BẢN / CHẤM — `so_tieu_de: 0`
        # và `nan_khuon_tieu_de` mặc định tắt đi đúng đường cũ (chỉ ảnh bìa +
        # kịch bản).
        danh_dau = ("cách đặt tên KHÁC NHAU", "ỨNG VIÊN tiêu đề cho MỘT video",
                   "KHUÔN CỦA KÊNH")
        assert not any(d in l["loi_nhac"] for l in goi.lan for d in danh_dau)

    def test_so_tieu_de_0_nan_khuon_bat_van_di_duong_cu(self, monkeypatch):
        import core.auto_khau as ak

        monkeypatch.setattr(ak, "tieu_de_thang_cua_kenh",
                            lambda goc, ma, toi_da=6: ["mẫu thắng"])
        goi = _GoiChatKichBan(nan_khuon="TITLE: khuôn cũ không chấm\n")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=_LAY_GIA, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(so_tieu_de=0, nan_khuon_tieu_de=True), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "TITLE: khuôn cũ không chấm" in noi_dung
        assert _tieu_de_cham_json(d) is None
