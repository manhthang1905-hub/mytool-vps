"""Bài kiểm `core/uu_tien.py` — hàm thuần P0..P4 + lão hoá.

Module nguồn không đĩa/không mạng, nên bài kiểm cũng vậy: chỉ gọi hàm với các
tổ hợp tham số, so kết quả bằng tay theo đúng "Luật điều phối" trong
`workspace/LO-TRINH-PHAT-HANH-V3.md`.
"""

from __future__ import annotations

from core import uu_tien as ut


# ── P0/P1/P3 — tải lên ──────────────────────────────────────────────────────


def test_tai_len_duoi_bien_la_p0():
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=1.0) == ut.P0
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=11.9) == ut.P0


def test_tai_len_dung_bien_khong_con_la_p0():
    # "< bien_xu_ly_gio" là NGHIÊM NGẶT — đúng 12.0 rơi sang bậc P1.
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=12.0) == ut.P1


def test_tai_len_trong_24h_la_p1():
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=12.1) == ut.P1
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=23.9) == ut.P1


def test_tai_len_tu_24h_la_p3():
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=24.0) == ut.P3
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=72.0) == ut.P3


def test_tai_len_thieu_gio_con_lai_an_toan_ve_p3():
    assert ut.uu_tien_co_ban("tai_len") == ut.P3


def test_tai_len_bien_xu_ly_gio_tuy_chinh():
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=5.0, bien_xu_ly_gio=4.0) == ut.P1
    assert ut.uu_tien_co_ban("tai_len", gio_con_lai=3.0, bien_xu_ly_gio=4.0) == ut.P0


# ── P1/P4 — phiên quét ──────────────────────────────────────────────────────


def test_quet_chua_chay_va_qua_gio_la_p1():
    assert ut.uu_tien_co_ban("quet", da_chay_hom_nay=False,
                             da_qua_gio_quet=True) == ut.P1


def test_quet_da_chay_roi_la_p4():
    assert ut.uu_tien_co_ban("quet", da_chay_hom_nay=True,
                             da_qua_gio_quet=True) == ut.P4


def test_quet_chua_toi_gio_la_p4():
    assert ut.uu_tien_co_ban("quet", da_chay_hom_nay=False,
                             da_qua_gio_quet=False) == ut.P4


def test_quet_thieu_co_an_toan_ve_p4():
    assert ut.uu_tien_co_ban("quet") == ut.P4
    assert ut.uu_tien_co_ban("quet", da_chay_hom_nay=False) == ut.P4
    assert ut.uu_tien_co_ban("quet", da_qua_gio_quet=True) == ut.P4


# ── P2/P4 — dựng, phụ đề ─────────────────────────────────────────────────────


def test_dung_va_phu_de_trong_24h_la_p2():
    assert ut.uu_tien_co_ban("dung", gio_con_lai=0.5) == ut.P2
    assert ut.uu_tien_co_ban("phu_de", gio_con_lai=23.9) == ut.P2


def test_dung_va_phu_de_khong_bao_gio_vuot_len_p0_p1():
    # Dù khe công khai trống rất gần (0 giờ), dựng/phụ đề vẫn chỉ P2 — P0/P1
    # dành riêng cho chính việc tải lên.
    assert ut.uu_tien_co_ban("dung", gio_con_lai=0.0) == ut.P2


def test_dung_va_phu_de_xa_hoac_khong_biet_la_p4():
    assert ut.uu_tien_co_ban("dung", gio_con_lai=24.0) == ut.P4
    assert ut.uu_tien_co_ban("phu_de") == ut.P4


# ── P4 — nền và việc lạ ──────────────────────────────────────────────────────


def test_nen_va_viec_la_luon_p4():
    assert ut.uu_tien_co_ban("nen") == ut.P4
    assert ut.uu_tien_co_ban("mot-thu-chua-tung-nghe") == ut.P4


# ── Lão hoá ──────────────────────────────────────────────────────────────────


def test_lao_hoa_khong_cho_thi_giu_nguyen():
    assert ut.lao_hoa(ut.P4, 0.0) == ut.P4
    assert ut.lao_hoa(ut.P4, -5.0) == ut.P4


def test_lao_hoa_hai_gio_mot_bac():
    assert ut.lao_hoa(ut.P4, 2.0) == ut.P3
    assert ut.lao_hoa(ut.P4, 3.9) == ut.P3
    assert ut.lao_hoa(ut.P4, 4.0) == ut.P2


def test_lao_hoa_khong_am_qua_p0():
    assert ut.lao_hoa(ut.P4, 100.0) == ut.P0
    assert ut.lao_hoa(ut.P2, 999.0) == ut.P0


def test_tinh_uu_tien_ap_lao_hoa_len_co_ban():
    # P4 (nền) chờ 6 giờ -> lão hoá 3 bậc -> P1.
    assert ut.tinh_uu_tien("nen", gio_da_cho=6.0) == ut.P1
    # P3 (tải lên xa) chờ 4 giờ -> lão hoá 2 bậc -> P1.
    assert ut.tinh_uu_tien("tai_len", gio_con_lai=48.0, gio_da_cho=4.0) == ut.P1


def test_tinh_uu_tien_khong_cho_bang_co_ban():
    assert ut.tinh_uu_tien("tai_len", gio_con_lai=1.0) == ut.uu_tien_co_ban(
        "tai_len", gio_con_lai=1.0)
