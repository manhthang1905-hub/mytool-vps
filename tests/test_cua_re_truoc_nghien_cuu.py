"""Cửa rẻ TRƯỚC nghiên cứu (29/09/2026): trần video/ngày và nhường phiên kênh
được hỏi TRƯỚC bước "1) Nghiên cứu" — không đốt 20–50 phút nghiên cứu rồi mới
vứt kết quả."""
import datetime as _dt

from core import tu_chay
from core.tu_chay import _doc_bao_cao_ngay, _ghi_bao_cao_ngay, chay_mot_ngay
from tests.test_tu_chay import (NO_LOG, _chay_auto_het, _lam_kenh_san_sang, _danh_sach_gia, _dong_de_xuat, _ghi_kenh,
                                _ghi_vm_config, _ghi_vm_trang_thai)


def _dem_nghien_cuu():
    goi = []
    return goi, (lambda *a, **k: goi.append(1))


def test_tran_ngay_da_du_thi_khong_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, video_moi_ngay=1, voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/LLLLLLLLLLL", "tieu_de": "x", "kenh": "Z"}]
    hom_nay = _dt.date(2026, 9, 18)
    chay_mot_ngay(goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
                  chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
                  video_da_lam_nhom=lambda g, k: set(), dung_viec=lambda bc: {},
                  chay_auto=_chay_auto_het, ban_giao=lambda *a, **k: ("GOI", True))
    goi, nut = _dem_nghien_cuu()
    log = []
    ket = chay_mot_ngay(goc, "K1", che_do="that", hom_nay=hom_nay, on_log=log.append,
                        chay_mot_nut=nut, doc_danh_sach=_danh_sach_gia(moi),
                        video_da_lam_nhom=lambda g, k: set(), dung_viec=lambda bc: {},
                        chay_auto=_chay_auto_het)
    assert goi == []  # KHÔNG nghiên cứu
    assert ket["run"] is None and ket["ok"] is True
    assert any("không nghiên cứu" in d for d in log), log

def test_nhuong_phien_hoi_truoc_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_vm_config(goc, cac_kenh=["K1"])
    _ghi_vm_trang_thai(goc, **{"phien_cuoi@K1": "2026-09-27",
                               "phien_muc_tieu@K1@2026-09-28": "07:30"})
    goi, nut = _dem_nghien_cuu()
    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=log.append,
        chay_mot_nut=nut, doc_danh_sach=_danh_sach_gia([_dong_de_xuat("https://youtu.be/AAAAAAAAAAA")]),
        video_da_lam_nhom=lambda g, k: set())
    assert goi == []
    assert ket["run"] is None
    assert sum("[NHƯỜNG]" in d for d in log) == 1


def test_khong_vuong_cua_thi_van_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    goi, nut = _dem_nghien_cuu()
    chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=lambda d: None,
        chay_mot_nut=nut, doc_danh_sach=_danh_sach_gia([_dong_de_xuat("https://youtu.be/AAAAAAAAAAA")]),
        video_da_lam_nhom=lambda g, k: set())
    assert goi == [1]


def test_ham_nhuong_im_nuot_dong_treo():
    ra = []
    ghi = tu_chay._log_nhuong_im(ra.append)
    ghi("  [NHƯỜNG] phiên kênh K1 đến hạn quá 6 giờ")
    ghi("[NHƯỜNG] còn phiên kênh K1")
    assert ra == ["[NHƯỜNG] còn phiên kênh K1"]
