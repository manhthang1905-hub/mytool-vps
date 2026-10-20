"""Lượt bị thay / đứng im tự thoát (`core/canh_luot.py`), làn của lượt bị thay không tính + giành lại được (`core/khe.py`),
khoá kênh làm tươi + chỉ nhả khoá của mình (`core/tu_chay.py`) — 20/10/2026. Chỉ `tmp_path`, không giết tiến trình nào."""

from __future__ import annotations

import json
import os
import threading
import time

from core import canh_luot, khe, tu_chay

#: PID khác còn sống (tiến trình cha của pytest) — đứng vai "lượt mới đã giành khoá kênh".
PID_KHAC = os.getppid()


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(du, tep)


def _doc(duong):
    with open(duong, "r", encoding="utf-8") as tep:
        return json.load(tep)


def _cai(goc, **cai):
    _ghi(os.path.join(goc, "workspace", "cai-dat.json"), dict({"lan_api": 2}, **cai))


def _lan(goc, i, pid, kenh, bat_dau):
    _ghi(khe.duong_khoa_api(goc, i), {"pid": pid, "tid": 1, "nguon": "khe", "loai": "api", "viec": "san_xuat",
                                      "kenh": kenh, "uu_tien": 2, "bat_dau": bat_dau})


# ── khe: làn của lượt bị thay ──────────────────────────────────────────────


def test_lan_bi_thay_khong_tinh_va_gianh_lai_duoc(tmp_path):
    goc = str(tmp_path)
    _cai(goc, lan_api=1)
    cu = time.time() - 30 * 3600
    _lan(goc, 0, os.getpid(), "K1", cu)
    _ghi(khe.duong_khoa_kenh(goc, "K1"), {"pid": PID_KHAC, "bat_dau": time.time() - 3600})
    assert khe.lan_bi_thay_the(goc, _doc(khe.duong_khoa_api(goc, 0)))
    assert khe.trang_thai(goc)["api"] == [None]
    assert khe.dem_lan_api(goc)["dang_lam"] == 0
    phien = khe.thu_giu(goc, "api", "san_xuat", kenh="K2")     # giành lại làn api-0
    assert phien is not None and _doc(khe.duong_khoa_api(goc, 0))["kenh"] == "K2"
    phien.nha()


def test_lan_khong_bi_thay_khi_khoa_kenh_cu_hon_hay_cua_minh(tmp_path):
    goc = str(tmp_path)
    bd = time.time() - 600
    du = {"pid": os.getpid(), "loai": "api", "kenh": "K1", "bat_dau": bd}
    _ghi(khe.duong_khoa_kenh(goc, "K1"), {"pid": PID_KHAC, "bat_dau": bd - 60})   # lượt kia có TRƯỚC: mình sẽ tự rời
    assert not khe.lan_bi_thay_the(goc, du)
    _ghi(khe.duong_khoa_kenh(goc, "K1"), {"pid": os.getpid(), "bat_dau": bd + 5})
    assert not khe.lan_bi_thay_the(goc, du)
    _ghi(khe.duong_khoa_kenh(goc, "K1"), {"pid": 999999999, "bat_dau": bd + 3600})  # người giữ khoá đã chết
    assert not khe.lan_bi_thay_the(goc, du)


def test_nha_khe_khong_xoa_tep_cua_nguoi_khac(tmp_path):
    goc = str(tmp_path)
    _cai(goc, lan_api=1)
    phien = khe.thu_giu(goc, "api", "san_xuat", kenh="K1")
    duong = khe.duong_khoa_api(goc, 0)
    _lan(goc, 0, PID_KHAC, "K2", time.time())                  # làn đã được lượt khác giành lại
    phien.nha()
    assert _doc(duong)["pid"] == PID_KHAC


# ── tu_chay: khoá kênh ─────────────────────────────────────────────────────


def test_nha_khoa_kenh_chi_khi_la_cua_minh(tmp_path):
    goc = str(tmp_path)
    duong = khe.duong_khoa_kenh(goc, "K1")
    _ghi(duong, {"pid": PID_KHAC, "bat_dau": time.time()})
    tu_chay._nha_khoa(goc, "K1")
    assert os.path.isfile(duong)
    _ghi(duong, {"pid": os.getpid(), "bat_dau": time.time()})
    tu_chay._nha_khoa(goc, "K1")
    assert not os.path.isfile(duong)


def test_khoa_kenh_lam_tuoi_khong_bi_coi_la_cu(tmp_path):
    goc = str(tmp_path)
    duong = khe.duong_khoa_kenh(goc, "K1")
    cu = time.time() - 13 * 3600
    _ghi(duong, {"pid": PID_KHAC, "bat_dau": cu, "nhip": time.time() - 60})
    ok, ly = tu_chay._giu_khoa(goc, "K1")
    assert not ok and "PID" in ly
    _ghi(duong, {"pid": PID_KHAC, "bat_dau": cu})                # không nhịp: > 12 giờ là khoá cũ như trước
    ok, _ly = tu_chay._giu_khoa(goc, "K1")
    assert ok
    tu_chay._nha_khoa(goc, "K1")


# ── canh_luot ──────────────────────────────────────────────────────────────


def test_bi_thay_hai_nhip_lien_thi_thoat(tmp_path):
    goc = str(tmp_path)
    bd = time.time() - 3600
    _ghi(khe.duong_khoa_kenh(goc, "K1"), {"pid": PID_KHAC, "bat_dau": bd + 600})
    trang = {}
    assert canh_luot.kiem_mot_lan(goc, "K1", bat_dau=bd, trang=trang, cuoi=time.time()) is None
    ly = canh_luot.kiem_mot_lan(goc, "K1", bat_dau=bd, trang=trang, cuoi=time.time())
    assert ly and "lượt khác" in ly


def test_khoa_cua_minh_duoc_lam_tuoi_va_khong_thoat(tmp_path):
    goc = str(tmp_path)
    bd = time.time() - 60
    duong = khe.duong_khoa_kenh(goc, "K1")
    _ghi(duong, {"pid": os.getpid(), "bat_dau": bd + 1})
    trang = {}
    assert canh_luot.kiem_mot_lan(goc, "K1", bat_dau=bd, trang=trang, cuoi=time.time()) is None
    assert trang["da_giu"] and _doc(duong)["nhip"] > bd and _doc(duong)["pid"] == os.getpid()


def test_im_qua_3_gio_thi_thoat_tru_khi_giu_khe_nang(tmp_path):
    goc = str(tmp_path)
    bd = time.time() - 5 * 3600
    cuoi = time.time() - (canh_luot.GIO_KHONG_TIEN_TRIEN + 0.1) * 3600
    ly = canh_luot.kiem_mot_lan(goc, "K1", bat_dau=bd, trang={}, cuoi=cuoi)
    assert ly and "không tiến triển" in ly
    _ghi(khe.duong_khoa_nang(goc), {"pid": os.getpid(), "bat_dau": time.time(), "nguon": "khe", "viec": "dung"})
    trang = {}
    assert canh_luot.kiem_mot_lan(goc, "K1", bat_dau=bd, trang=trang, cuoi=cuoi) is None and trang["hoan"] == 1
    assert canh_luot.kiem_mot_lan(goc, "K1", bat_dau=bd, trang={}, cuoi=time.time() - 3600) is None


def test_luong_canh_thoat_va_nha_lan_cua_minh(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _cai(goc, lan_api=2)
    _lan(goc, 0, os.getpid(), "K1", time.time())
    _lan(goc, 1, PID_KHAC, "K2", time.time())
    monkeypatch.setattr(canh_luot, "GIO_KHONG_TIEN_TRIEN", 0.0)
    thoat, nhat = [], []
    xong = threading.Event()

    def _thoat(ma):
        thoat.append(ma)
        xong.set()

    canh_luot.bat(goc, "K1", ghi=nhat.append, thoat=_thoat, nhip=0.01)
    assert xong.wait(5.0)
    assert thoat == [canh_luot.MA_THOAT_CANH] and any("CANH LƯỢT" in d for d in nhat)
    assert not os.path.isfile(khe.duong_khoa_api(goc, 0)) and os.path.isfile(khe.duong_khoa_api(goc, 1))
    canh_luot.danh_dau()
