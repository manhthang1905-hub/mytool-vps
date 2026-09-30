"""Nghiên cứu NHÓM + giữ nguồn (29/09/2026, `core/nghien_cuu_nhom.py`).

Canh: còn tươi → lượt sản xuất không nghiên cứu · cũ → nghiên cứu MỘT lần cho cả
nhóm (kênh anh em rảnh + cũ đi kèm) · khoá nhóm bận → dùng dữ liệu < 24h hoặc đợi
lượt sau · giữ nguồn O_EXCL (hai tiến trình giành cùng lúc chỉ một được) · nguồn
kênh anh em giữ bị loại · kênh không nhóm y như cũ.
"""
import datetime as _dt
import json
import os
import subprocess
import sys
import time

from core import nghien_cuu_chung as ncc
from core import nghien_cuu_nhom as nn
from core.tu_chay import chay_mot_ngay
from tests.test_tu_chay import _danh_sach_gia, _ghi_kenh


def _moc_nghien_cuu(goc, ma, gio_truoc):
    d = os.path.join(goc, "CHANNEL", ma, "nghien-cuu")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "bao-cao-mot-nut.md")
    with open(p, "w", encoding="utf-8") as t:
        t.write("x")
    moc = time.time() - gio_truoc * 3600
    os.utime(p, (moc, moc))


def _chay(goc, ma, nut, log):
    return chay_mot_ngay(goc, ma, che_do="that", hom_nay=_dt.date(2026, 9, 28),
                         bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=log.append,
                         chay_mot_nut=nut, doc_danh_sach=_danh_sach_gia([]),
                         video_da_lam_nhom=lambda g, k: set(), tieu_de_da_lam_nhom=lambda g, k: [])


def _nut_dem(goi):
    def nut(goc, ma, client=None, on_log=None, cancel=None):
        goi.append(ma)
        _moc_nghien_cuu(goc, ma, 0)
    return nut


def test_con_tuoi_thi_khong_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng", tu_chay=True)
    _moc_nghien_cuu(goc, "A", 1)
    goi, log = [], []
    _chay(goc, "A", _nut_dem(goi), log)
    assert goi == []
    assert any("còn tươi" in d for d in log), log


def test_cu_thi_nghien_cuu_mot_lan_ca_nhom(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng", tu_chay=True)
    _ghi_kenh(goc, "B", nhom="ng", tu_chay=True)
    _ghi_kenh(goc, "C", nhom="ng", tu_chay=True)
    _ghi_kenh(goc, "D", nhom="ng", tu_chay=False)       # không tự chạy → không đụng
    _moc_nghien_cuu(goc, "A", 30)
    _moc_nghien_cuu(goc, "B", 30)
    _moc_nghien_cuu(goc, "C", 1)                          # còn tươi → không làm lại
    goi, log = [], []
    _chay(goc, "A", _nut_dem(goi), log)
    assert goi == ["A", "B"], goi
    assert any("NGHIÊN CỨU NHÓM" in d and "B xong" in d for d in log)
    # khoá nhóm đã nhả, lượt kế của B thấy tươi
    assert not os.path.exists(os.path.join(ncc.thu_muc(goc, "A"), nn.TEP_KHOA))
    goi2 = []
    _chay(goc, "B", _nut_dem(goi2), [])
    assert goi2 == []


def test_anh_em_dang_chay_thi_khong_dung(tmp_path):
    from core import tu_chay
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng", tu_chay=True)
    _ghi_kenh(goc, "B", nhom="ng", tu_chay=True)
    assert tu_chay._giu_khoa(goc, "B")[0]                # B đang có lượt (chính tiến trình này)
    goi, log = [], []
    _chay(goc, "A", _nut_dem(goi), log)
    tu_chay._nha_khoa(goc, "B")
    assert goi == ["A"]
    assert any("bỏ qua B" in d for d in log)


def _khoa_ban(goc, ma):
    p = os.path.join(ncc.thu_muc(goc, ma), nn.TEP_KHOA)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as t:
        json.dump({"pid": os.getpid(), "luc": time.time(), "kenh": "B"}, t)


def test_khoa_ban_du_lieu_duoi_24h_thi_chon_nguon_luon(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng", tu_chay=True)
    _moc_nghien_cuu(goc, "A", 13)
    _khoa_ban(goc, "A")
    goi, log = [], []
    ket = _chay(goc, "A", _nut_dem(goi), log)
    assert goi == [] and "đợi lượt sau" not in ket["tom_tat"]
    assert any("dùng dữ liệu" in d for d in log)


def test_khoa_ban_du_lieu_cu_thi_doi_luot_sau(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng", tu_chay=True)
    _moc_nghien_cuu(goc, "A", 30)
    _khoa_ban(goc, "A")
    goi, log = [], []
    ket = _chay(goc, "A", _nut_dem(goi), log)
    assert goi == [] and "đợi lượt sau" in ket["tom_tat"]


def test_kho_ung_vien_thieu_thi_nghien_cuu_lai_som(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng", tu_chay=True)
    _moc_nghien_cuu(goc, "A", 3)
    assert nn.can_nghien_cuu(goc, "A")[0] is False
    nn.danh_dau_thieu(goc, "A", 2)
    can, ly_do, _t = nn.can_nghien_cuu(goc, "A")
    assert can and "kho ứng viên" in ly_do


def test_kenh_khong_nhom_nghien_cuu_nhu_cu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "C", tu_chay=True)
    _moc_nghien_cuu(goc, "C", 1)
    goi, log = [], []
    _chay(goc, "C", _nut_dem(goi), log)
    assert goi == ["C"]                                   # mỗi lượt vẫn nghiên cứu
    assert nn.giu_nguon(goc, "C", "abcdefghijk") == (True, "")
    assert not os.path.isdir(os.path.join(goc, "CHANNEL", "_NHOM"))


def test_giu_nguon_kenh_khac_bi_loai_va_nha(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng")
    _ghi_kenh(goc, "B", nhom="ng")
    assert nn.giu_nguon(goc, "A", "abcdefghijk", ma_luot="0001") == (True, "")
    assert nn.giu_nguon(goc, "B", "abcdefghijk") == (False, "A")
    assert nn.giu_nguon(goc, "A", "abcdefghijk")[0] is True   # của mình → được
    assert nn.nguon_da_giu_boi_kenh_khac(goc, "B") == {"abcdefghijk": "A"}
    assert nn.nguon_da_giu_boi_kenh_khac(goc, "A") == {}
    nn.nha_nguon(goc, "B", "abcdefghijk")                     # không phải của B → không nhả
    assert nn.nguon_da_giu_boi_kenh_khac(goc, "B")
    nn.nha_nguon(goc, "A", "abcdefghijk")
    assert nn.nguon_da_giu_boi_kenh_khac(goc, "B") == {}


def test_ban_giu_rac_qua_7_ngay_khong_con_luot(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng")
    _ghi_kenh(goc, "B", nhom="ng")
    nn.giu_nguon(goc, "A", "abcdefghijk", ma_luot="0009")
    p = nn._duong_giu(goc, "A", "abcdefghijk")
    du = json.load(open(p, encoding="utf-8"))
    du["luc"] = time.time() - 8 * 86400
    json.dump(du, open(p, "w", encoding="utf-8"))
    assert nn.nguon_da_giu_boi_kenh_khac(goc, "B") == {}
    assert nn.giu_nguon(goc, "B", "abcdefghijk")[0] is True


_CON = r"""
import sys
sys.path.insert(0, sys.argv[1])
import core
core.__path__.insert(0, sys.argv[2])
from core import nghien_cuu_nhom as nn
import time
t = float(sys.argv[5])
while time.time() < t:
    pass
print("OK" if nn.giu_nguon(sys.argv[3], sys.argv[4], "abcdefghijk")[0] else "NO")
"""


def test_hai_tien_trinh_cung_gianh_mot_nguon_chi_mot_duoc(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="ng")
    _ghi_kenh(goc, "B", nhom="ng")
    thu_muc_nn = os.path.dirname(os.path.abspath(nn.__file__))
    luc = str(time.time() + 1.5)
    tien = [subprocess.Popen([sys.executable, "-c", _CON, os.getcwd(), thu_muc_nn, goc, k, luc],
                             stdout=subprocess.PIPE, text=True) for k in ("A", "B")]
    ra = sorted(p.communicate(timeout=120)[0].strip() for p in tien)
    assert ra == ["NO", "OK"], ra
