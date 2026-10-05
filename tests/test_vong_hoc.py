"""Vòng học trước mỗi lượt (`core/vong_hoc.py`) — Việc 3 của
`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

Không gọi mạng, không cần Qt, không gọi FFmpeg thật (kho nhạc trống/thiếu
FFmpeg là đường lùi có sẵn của `core.kho_nhac.cap_nhat`, không phải lỗi ở đây).

Ba nhóm bài:

1. `truoc_luot` chạy hết bốn bước trên một kênh trống, không ném lỗi.
2. Một bước ném lỗi (giả lập bằng monkeypatch) KHÔNG được chặn các bước sau.
3. Debounce bước 3 (bài học sản xuất): chỉ chạy lại khi có số liệu mới hoặc đã
   quá `GIO_DEBOUNCE_BAI_HOC` giờ kể từ lần học trước.
"""

from __future__ import annotations

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bai_hoc_san_xuat as bh  # noqa: E402
from core import vong_hoc  # noqa: E402

BAY_GIO = dt.datetime(2026, 9, 28, 15, 0, 0)


def _log_thu(nhat_ky):
    def log(dong):
        nhat_ky.append(str(dong))
    return log


def test_truoc_luot_kenh_trong_khong_nem_loi_va_tra_du_khoa(tmp_path):
    goc = str(tmp_path)
    nhat_ky = []
    ket = vong_hoc.truoc_luot(goc, "KENH-TRONG", None, _log_thu(nhat_ky), bay_gio=BAY_GIO)
    assert set(ket.keys()) == {"kho_nhac", "bu_ho_so", "chi_so", "bai_hoc", "khuon_bia", "chien_luoc", "tu_hoc"}
    # Kênh trống: kho nhạc không có gì để làm, hồ sơ trống, nhưng KHÔNG được ném lỗi.
    assert ket["bu_ho_so"] == []


def test_truoc_luot_khuon_bia_kenh_trong_tra_none_khong_loi(tmp_path):
    """Việc 4 (`core/khuon_bia.py`) đã làm — module TỒN TẠI, `truoc_luot` gọi
    thẳng `khuon_bia.cap_nhat`. Kênh trống (chưa có hồ sơ video/số liệu) thì
    chưa ai "thắng" — trả `None`, KHÔNG phải lỗi cần ghi log."""
    goc = str(tmp_path)
    nhat_ky = []
    ket = vong_hoc.truoc_luot(goc, "KENH-TRONG", None, _log_thu(nhat_ky), bay_gio=BAY_GIO)
    assert ket["khuon_bia"] is None
    assert not any("khuôn bìa" in d for d in nhat_ky), (
        "chưa có video nào đủ số liệu không phải là một sự cố cần báo")


def test_truoc_luot_khuon_bia_hong_chi_ghi_log_khong_chan(tmp_path, monkeypatch):
    """Bước 4 hỏng (giả lập) — vẫn không được ném lỗi ra ngoài, chỉ ghi log."""
    goc = str(tmp_path)

    def hong(*a, **kw):
        raise RuntimeError("hỏng giả lập")

    from core import khuon_bia
    monkeypatch.setattr(khuon_bia, "cap_nhat", hong)

    nhat_ky = []
    ket = vong_hoc.truoc_luot(goc, "KENH-TRONG", None, _log_thu(nhat_ky), bay_gio=BAY_GIO)
    assert ket["khuon_bia"] is None
    assert any("khuôn bìa" in d for d in nhat_ky)


def test_mot_buoc_hong_khong_chan_cac_buoc_sau(tmp_path, monkeypatch):
    """Bước 1 (kho nhạc) ném lỗi giả — bước 2/3 vẫn phải chạy tiếp, không dừng
    giữa chừng. Đây là luật đầu tiên của bản thiết kế: không bước nào được
    chặn sản xuất."""
    goc = str(tmp_path)

    def kho_nhac_hong(*a, **kw):
        raise RuntimeError("giả lập FFmpeg hỏng")

    monkeypatch.setattr(vong_hoc.kho_nhac, "cap_nhat", kho_nhac_hong)

    goi_bu_ho_so = {"n": 0}
    def bu_ho_so_gia(goc_, kenh_, **kw):
        goi_bu_ho_so["n"] += 1
        return []
    monkeypatch.setattr(vong_hoc.ho_so_video, "bu_ho_so", bu_ho_so_gia)

    nhat_ky = []
    ket = vong_hoc.truoc_luot(goc, "KENH-X", None, _log_thu(nhat_ky), bay_gio=BAY_GIO)

    assert ket["kho_nhac"] is None, "bước hỏng phải để kết quả None, không văng ra ngoài"
    assert goi_bu_ho_so["n"] == 1, "bước 2 (hồ sơ video) vẫn phải chạy dù bước 1 hỏng"
    assert any("kho nhạc hỏng" in d for d in nhat_ky)


def test_hai_buoc_lien_tiep_hong_van_khong_nem_loi(tmp_path, monkeypatch):
    goc = str(tmp_path)

    def hong(*a, **kw):
        raise RuntimeError("hỏng")

    monkeypatch.setattr(vong_hoc.kho_nhac, "cap_nhat", hong)
    monkeypatch.setattr(vong_hoc.ho_so_video, "bu_ho_so", hong)
    monkeypatch.setattr(vong_hoc.ho_so_video, "cap_nhat_chi_so", hong)
    monkeypatch.setattr(vong_hoc.bai_hoc_san_xuat, "xuat_markdown", hong)

    nhat_ky = []
    # Không được ném lỗi ra ngoài dù CẢ BỐN bước đều hỏng.
    ket = vong_hoc.truoc_luot(goc, "KENH-X", None, _log_thu(nhat_ky), bay_gio=BAY_GIO)
    assert ket["kho_nhac"] is None and ket["chi_so"] is None and ket["bai_hoc"] is False
    assert len(nhat_ky) >= 4


def test_can_hoc_lai_chua_tung_hoc_thi_hoc_ngay(tmp_path):
    goc = str(tmp_path)
    assert vong_hoc._can_hoc_lai(goc, "KENH-MOI", False, bay_gio=BAY_GIO) is True


def test_can_hoc_lai_co_so_moi_luon_hoc_lai(tmp_path):
    goc = str(tmp_path)
    bh.luu_bai_hoc(goc, "K1", [])
    assert vong_hoc._can_hoc_lai(goc, "K1", True, bay_gio=BAY_GIO) is True


def _dat_mtime(duong: str, moc: dt.datetime) -> None:
    """Ép mtime tệp về đúng `moc` — `luu_bai_hoc` ghi mtime NGAY LÚC GỌI (giờ
    máy thật), không phải `luc` truyền vào (đó chỉ là dữ liệu trong JSON), nên
    bài kiểm ĐỘNG (thời gian máy thật lúc chạy `pytest`) phải tự ép lại mốc
    mới đo đúng ngưỡng debounce, không phụ thuộc đồng hồ máy chạy test."""
    ts = moc.timestamp()
    os.utime(duong, (ts, ts))


def test_can_hoc_lai_khong_co_so_moi_va_con_moi_thi_khong_hoc_lai(tmp_path):
    goc = str(tmp_path)
    bh.luu_bai_hoc(goc, "K1", [])
    _dat_mtime(bh.duong_tep_bai_hoc(goc, "K1"), BAY_GIO - dt.timedelta(hours=1))
    assert vong_hoc._can_hoc_lai(goc, "K1", False, bay_gio=BAY_GIO) is False


def test_can_hoc_lai_qua_24h_thi_hoc_lai_du_khong_co_so_moi(tmp_path):
    goc = str(tmp_path)
    bh.luu_bai_hoc(goc, "K1", [])
    _dat_mtime(bh.duong_tep_bai_hoc(goc, "K1"), BAY_GIO - dt.timedelta(hours=25))
    assert vong_hoc._can_hoc_lai(goc, "K1", False, bay_gio=BAY_GIO) is True


def test_truoc_luot_debounce_khong_goi_xuat_markdown_khi_khong_co_gi_moi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(vong_hoc.kho_nhac, "cap_nhat", lambda *a, **kw: {})
    monkeypatch.setattr(vong_hoc.ho_so_video, "bu_ho_so", lambda *a, **kw: [])
    monkeypatch.setattr(vong_hoc.ho_so_video, "cap_nhat_chi_so",
                        lambda *a, **kw: {"noi_video_id": 0, "cap_nhat_moc": 0, "so_lieu_cu": []})

    bh.luu_bai_hoc(goc, "K1", [])  # "vừa học xong" — ép mtime còn rất mới
    _dat_mtime(bh.duong_tep_bai_hoc(goc, "K1"), BAY_GIO - dt.timedelta(minutes=5))

    goi = {"n": 0}
    def xuat_markdown_gia(*a, **kw):
        goi["n"] += 1
        return ""
    monkeypatch.setattr(vong_hoc.bai_hoc_san_xuat, "xuat_markdown", xuat_markdown_gia)

    ket = vong_hoc.truoc_luot(goc, "K1", None, lambda d: None, bay_gio=BAY_GIO)
    assert goi["n"] == 0, "vừa học xong, không số liệu mới — không được học lại"
    assert ket["bai_hoc"] is False


def test_truoc_luot_co_so_moi_thi_goi_xuat_markdown(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(vong_hoc.kho_nhac, "cap_nhat", lambda *a, **kw: {})
    monkeypatch.setattr(vong_hoc.ho_so_video, "bu_ho_so", lambda *a, **kw: [])
    monkeypatch.setattr(vong_hoc.ho_so_video, "cap_nhat_chi_so",
                        lambda *a, **kw: {"noi_video_id": 1, "cap_nhat_moc": 2, "so_lieu_cu": []})
    bh.luu_bai_hoc(goc, "K1", [])  # rất mới, nhưng có số MỚI nên vẫn học lại
    _dat_mtime(bh.duong_tep_bai_hoc(goc, "K1"), BAY_GIO - dt.timedelta(minutes=5))

    goi = {"n": 0}
    def xuat_markdown_gia(*a, **kw):
        goi["n"] += 1
        return ""
    monkeypatch.setattr(vong_hoc.bai_hoc_san_xuat, "xuat_markdown", xuat_markdown_gia)

    ket = vong_hoc.truoc_luot(goc, "K1", None, lambda d: None, bay_gio=BAY_GIO)
    assert goi["n"] == 1
    assert ket["bai_hoc"] is True


def test_buoc_5_ghi_chien_luoc_json_cung_debounce_va_hong_khong_chan(tmp_path, monkeypatch):
    """B4 bộ máy chiến lược: bước 5 ghi `nghien-cuu/chien-luoc.json` + 1 dòng log khi chưa có tệp;
    gọi lại ngay (không số mới, tệp < 24h) thì KHÔNG ghi lại; hỏng thì chỉ log."""
    from core.chien_luoc import ket_qua

    goc = str(tmp_path)
    nhat_ky = []
    ket = vong_hoc.truoc_luot(goc, "K5", None, _log_thu(nhat_ky), bay_gio=dt.datetime.now())
    assert ket["chien_luoc"] and os.path.isfile(ket["chien_luoc"])
    assert sum("chiến lược (28 ngày)" in d for d in nhat_ky) == 1
    ket2 = vong_hoc.truoc_luot(goc, "K5", None, _log_thu(nhat_ky), bay_gio=dt.datetime.now())
    assert ket2["chien_luoc"] is None, "tệp còn mới, không có số mới → debounce"

    def hong(*a, **kw):
        raise RuntimeError("hỏng giả lập")

    monkeypatch.setattr(ket_qua, "ghi_tep", hong)
    os.remove(ket["chien_luoc"])
    nhat_ky.clear()
    ket3 = vong_hoc.truoc_luot(goc, "K5", None, _log_thu(nhat_ky), bay_gio=dt.datetime.now())
    assert ket3["chien_luoc"] is None
    assert any("thống kê theo công thức hỏng" in d for d in nhat_ky)


def test_khe_ban_chi_doi_kho_nhac_van_hoc_05_10(tmp_path, monkeypatch):
    """05/10: TL1–TL3 khởi cùng 05:00, khe nặng luôn bận → bản cũ bỏ CẢ vòng học (bảng điểm đứng từ 03/10)."""
    from core import vong_hoc, kho_nhac, tu_hoc
    goi = {"kho_nhac": 0, "cham": 0}
    monkeypatch.setattr(kho_nhac, "cap_nhat", lambda *a, **k: goi.__setitem__("kho_nhac", goi["kho_nhac"] + 1))
    monkeypatch.setattr(tu_hoc, "cham_van", lambda *a, **k: goi.__setitem__("cham", goi["cham"] + 1) or {})
    monkeypatch.setattr(tu_hoc, "ghi_bang_diem_md", lambda *a, **k: "")
    vong_hoc.truoc_luot(str(tmp_path), "K", None, lambda s: None, bo_kho_nhac=True)
    assert goi == {"kho_nhac": 0, "cham": 1}
