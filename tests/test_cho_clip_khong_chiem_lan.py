"""Luật 06/10/2026: "Lượt đang CHỜ KHO CLIP không chiếm làn API".

Dấu `workspace/tu-chay/cho-clip/<kênh>.json` (`core.khe.ghi_cho_clip`) do
`auto_khau._cho_engine_clip` dựng/gỡ; `core.khe` (giành tệp làn) và
`core.dieu_phoi.nhip` (đếm làn) không tính lượt có dấu sống + tươi.
Mọi bài dùng `tmp_path`, không mạng, không sinh tiến trình thật.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time
import types

import pytest

from core import auto_khau as ak
from core import dieu_phoi, khe
from core.auto import Cancelled
from core.kenh import Kenh

from tests.test_dieu_phoi import _kenh, _vps

#: PID không thể tồn tại (xem tests/test_khe.py).
PID_GIA_DA_CHET = 999999999


def _cai(goc, **cai):
    duong = os.path.join(goc, "workspace", "cai-dat.json")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(cai, tep)


def _sua_dau(goc, kenh, **thay):
    duong = khe.duong_cho_clip(goc, kenh)
    with open(duong, "r", encoding="utf-8") as tep:
        du = json.load(tep)
    du.update(thay)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(du, tep)


# ── dấu chờ clip ────────────────────────────────────────────────────────────


def test_dau_cho_clip_ghi_doc_xoa(tmp_path):
    goc = str(tmp_path)
    assert khe.doc_cho_clip(goc) == {}
    khe.ghi_cho_clip(goc, "K1", han="2026-10-06T23:00:00", tu="2026-10-06T08:00:00")
    assert os.path.isfile(os.path.join(goc, "workspace", "tu-chay", "cho-clip", "K1.json"))
    du = khe.doc_cho_clip(goc)["K1"]
    assert du["pid"] == os.getpid() and du["han"] == "2026-10-06T23:00:00"
    khe.xoa_cho_clip(goc, "K1")
    assert khe.doc_cho_clip(goc) == {}


def test_dau_cu_hoac_pid_chet_khong_tinh(tmp_path):
    goc = str(tmp_path)
    khe.ghi_cho_clip(goc, "K1")
    _sua_dau(goc, "K1", luc=time.time() - khe.TUOI_CHO_CLIP_GIAY - 60)
    assert khe.doc_cho_clip(goc) == {}                       # cũ > 45' → lượt thường
    assert os.path.isfile(khe.duong_cho_clip(goc, "K1"))     # PID sống: không xoá
    khe.ghi_cho_clip(goc, "K2")
    _sua_dau(goc, "K2", pid=PID_GIA_DA_CHET)
    assert "K2" not in khe.doc_cho_clip(goc)
    assert not os.path.isfile(khe.duong_cho_clip(goc, "K2"))  # PID chết: dọn


def test_xoa_khong_dung_dau_cua_tien_trinh_khac(tmp_path):
    goc = str(tmp_path)
    khe.ghi_cho_clip(goc, "K1")
    _sua_dau(goc, "K1", pid=os.getppid())
    khe.xoa_cho_clip(goc, "K1")
    assert os.path.isfile(khe.duong_cho_clip(goc, "K1"))


# ── khe "api": lượt chờ clip nhường làn ─────────────────────────────────────


def test_lan_api_luot_cho_clip_nhuong_lan(tmp_path):
    goc = str(tmp_path)
    _cai(goc, lan_api=2)
    p1 = khe.thu_giu(goc, "api", "san_xuat", kenh="K1")
    p2 = khe.thu_giu(goc, "api", "san_xuat", kenh="K2")
    assert p1 is not None and p2 is not None
    assert khe.thu_giu(goc, "api", "san_xuat", kenh="K3") is None    # như cũ: hết làn
    khe.ghi_cho_clip(goc, "K1")                                       # K1 chờ kho clip
    p3 = khe.thu_giu(goc, "api", "san_xuat", kenh="K3")
    assert p3 is not None
    assert os.path.basename(p3._duong) == "api-2.json"
    assert khe.thu_giu(goc, "api", "san_xuat", kenh="K4") is None    # K2+K3 = 2 làn
    dem = khe.dem_lan_api(goc)
    assert (dem["dang_lam"], dem["dang_cho_clip"]) == (2, 1)
    assert len(khe.trang_thai(goc)["api"]) == 3
    # K1 thôi chờ → tính làn lại (3/2 tạm thời — không lượt mới nào vào được)
    khe.xoa_cho_clip(goc, "K1")
    assert khe.dem_lan_api(goc)["dang_lam"] == 3
    assert khe.thu_giu(goc, "api", "san_xuat", kenh="K4") is None
    p2.nha()
    assert khe.thu_giu(goc, "api", "san_xuat", kenh="K4") is None    # vẫn 2/2 (K1, K3)
    p1.nha()
    p4 = khe.thu_giu(goc, "api", "san_xuat", kenh="K4")
    assert p4 is not None
    p3.nha()
    p4.nha()
    assert khe.trang_thai(goc)["api"] == [None, None]


def test_lan_api_tran_tong(tmp_path):
    goc = str(tmp_path)
    _cai(goc, lan_api=2, tran_luot_tong=3)
    p1 = khe.thu_giu(goc, "api", "san_xuat", kenh="K1")
    p2 = khe.thu_giu(goc, "api", "san_xuat", kenh="K2")
    khe.ghi_cho_clip(goc, "K1")
    khe.ghi_cho_clip(goc, "K2")
    p3 = khe.thu_giu(goc, "api", "san_xuat", kenh="K3")
    assert p3 is not None
    # còn 1 làn API nhưng đã 3/3 lượt tổng
    assert khe.thu_giu(goc, "api", "san_xuat", kenh="K4") is None
    for p in (p1, p2, p3):
        p.nha()


def test_lan_api_dau_cu_tinh_nhu_luot_thuong(tmp_path):
    goc = str(tmp_path)
    _cai(goc, lan_api=1)
    p1 = khe.thu_giu(goc, "api", "san_xuat", kenh="K1")
    khe.ghi_cho_clip(goc, "K1")
    _sua_dau(goc, "K1", luc=time.time() - khe.TUOI_CHO_CLIP_GIAY - 1)
    assert khe.thu_giu(goc, "api", "san_xuat", kenh="K2") is None
    p1.nha()


# ── auto_khau._cho_engine_clip dựng/gỡ dấu ─────────────────────────────────


class _LoiHetHanMuc(Exception):
    pass


def _bc_gia(goc, dong, *, kiem_dung=lambda: None, khi_ngu=None):
    nhat = []

    def ngu(giay):
        dong["luc"] += _dt.timedelta(seconds=giay)
        if khi_ngu is not None:
            khi_ngu()

    return types.SimpleNamespace(goc=goc, kenh=Kenh(ma="K1"), ghi=nhat.append,
                                 kiem_dung=kiem_dung, ngu=ngu, nhat=nhat)


def test_cho_engine_clip_dung_dau_roi_go_khi_toi_han(tmp_path, monkeypatch):
    goc = str(tmp_path)
    dong = {"luc": _dt.datetime(2026, 10, 6, 22, 0)}
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong["luc"])
    thay = []
    bc = _bc_gia(goc, dong, khi_ngu=lambda: thay.append(dict(khe.doc_cho_clip(goc))))
    lam_tuoi = []
    goc_ghi = khe.ghi_cho_clip

    def ghi_dem(*a, **k):
        lam_tuoi.append(1)
        goc_ghi(*a, **k)

    monkeypatch.setattr(khe, "ghi_cho_clip", ghi_dem)
    het = []

    def mot_canh(_c):
        het.append(_LoiHetHanMuc("hết hạn mức"))
        raise het[-1]

    han = _dt.datetime(2026, 10, 6, 22, 50)
    xong = ak._cho_engine_clip(bc, han, han + _dt.timedelta(hours=6), het,
                               lambda: [{"scene_id": 1}], mot_canh)
    assert xong is True
    assert thay and all(t.get("K1", {}).get("han") == "2026-10-06T22:50:00" for t in thay)
    assert thay[0]["K1"]["tu"] == "2026-10-06T22:00:00"
    assert len(lam_tuoi) >= 50 * 60 // ak.GIAY_LAM_TUOI_CHO_CLIP     # làm tươi ≤ 5'/lần
    assert not os.path.exists(khe.duong_cho_clip(goc, "K1"))


def test_cho_engine_clip_go_dau_khi_engine_co_lai(tmp_path, monkeypatch):
    goc = str(tmp_path)
    dong = {"luc": _dt.datetime(2026, 10, 6, 10, 0)}
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong["luc"])
    bc = _bc_gia(goc, dong)
    xong = ak._cho_engine_clip(bc, _dt.datetime(2026, 10, 6, 23, 0), None, [],
                               lambda: [{"scene_id": 1}], lambda _c: None)
    assert xong is False
    assert not os.path.exists(khe.duong_cho_clip(goc, "K1"))


def test_cho_engine_clip_khong_han_chot_giu_dau_toi_khi_engine_co_lai(tmp_path, monkeypatch):
    """Luật 07/10/2026: `han` None (mặc định) = chờ KHÔNG hạn chót — qua cả mốc
    giờ đăng vẫn chờ, dấu chờ clip (không chiếm làn) giữ suốt, gỡ khi engine có lại."""
    goc = str(tmp_path)
    dong = {"luc": _dt.datetime(2026, 10, 6, 22, 0)}
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong["luc"])
    thay = []
    bc = _bc_gia(goc, dong, khi_ngu=lambda: thay.append(dict(khe.doc_cho_clip(goc))))
    het = []

    def mot_canh(_c):
        if dong["luc"] < _dt.datetime(2026, 10, 7, 8, 0):
            het.append(_LoiHetHanMuc("hết hạn mức"))
            raise het[-1]

    xong = ak._cho_engine_clip(bc, None, None, het, lambda: [{"scene_id": 1}], mot_canh)
    assert xong is False, "không có hạn chót thì không bao giờ trả 'tới hạn' (dựng từ ảnh)"
    assert dong["luc"] == _dt.datetime(2026, 10, 7, 8, 0)
    assert thay and all(t.get("K1", {}).get("han") == "" for t in thay)
    assert not os.path.exists(khe.duong_cho_clip(goc, "K1"))


def test_cho_engine_clip_go_dau_khi_bam_dung(tmp_path, monkeypatch):
    goc = str(tmp_path)
    dong = {"luc": _dt.datetime(2026, 10, 6, 10, 0)}
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong["luc"])
    dem = {"n": 0}

    def kiem_dung():
        dem["n"] += 1
        if dem["n"] > 3:
            assert "K1" in khe.doc_cho_clip(goc)
            raise Cancelled()

    bc = _bc_gia(goc, dong, kiem_dung=kiem_dung)
    with pytest.raises(Cancelled):
        ak._cho_engine_clip(bc, _dt.datetime(2026, 10, 6, 23, 0), None, [],
                            lambda: [{"scene_id": 1}], lambda _c: None)
    assert not os.path.exists(khe.duong_cho_clip(goc, "K1"))


def test_cho_engine_clip_go_dau_khi_loi_bat_ngo(tmp_path, monkeypatch):
    goc = str(tmp_path)
    dong = {"luc": _dt.datetime(2026, 10, 6, 10, 0)}
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong["luc"])
    bc = _bc_gia(goc, dong)

    def thieu():
        if os.path.exists(khe.duong_cho_clip(goc, "K1")):
            raise OSError("đĩa hỏng giữa chừng")
        return [{"scene_id": 1}]

    with pytest.raises(OSError):
        ak._cho_engine_clip(bc, _dt.datetime(2026, 10, 6, 23, 0), None, [], thieu,
                            lambda _c: None)
    assert not os.path.exists(khe.duong_cho_clip(goc, "K1"))


# ── dieu_phoi.nhip: đếm làn bỏ lượt chờ clip ───────────────────────────────


BAY_GIO = _dt.datetime(2026, 9, 29, 14, 0)


def _khoa_kenh(goc, ma, pid=None):
    kh = os.path.join(goc, "CHANNEL", ma, "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(kh), exist_ok=True)
    with open(kh, "w", encoding="utf-8") as tep:
        json.dump({"pid": pid or os.getpid(), "bat_dau": time.time()}, tep)


def _dung_may(goc, so_kenh, dang_lam, cho_clip, **cai):
    _vps(goc, lan_api=4, **cai)
    ma = ["K{0}".format(i) for i in range(1, so_kenh + 1)]
    for m in ma:
        _kenh(goc, m)
    for m in ma[:dang_lam + cho_clip]:
        _khoa_kenh(goc, m)
    for m in ma[dang_lam:dang_lam + cho_clip]:
        khe.ghi_cho_clip(goc, m, han="2026-09-29T23:00:00", tu="2026-09-29T08:00:00")
    return ma


def _nhip(goc, nhat=None):
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=BAY_GIO, ram=10.0, dia_gb=30.0,
                        sinh=lambda g, m: sinh.append(m) or 5000 + len(sinh),
                        log=(nhat.append if nhat is not None else (lambda d: None)))
    return ra, sinh


def test_nhip_4_lam_3_cho_clip_la_4_lan(tmp_path):
    goc = str(tmp_path)
    _dung_may(goc, 9, 4, 3)
    nhat = []
    ra, sinh = _nhip(goc, nhat)
    assert (ra["so_dang"], ra["so_cho_clip"]) == (4, 3)
    assert sinh == [] and ra["chan"] == "hết làn API (4/4 đang chạy, +3 chờ kho clip)"
    k5 = next(c for c in ra["kenh"] if c["ma"] == "K5")
    assert k5["ly_do"] == "chờ kho clip tới 23:00 (không tính làn)"
    assert any("K5: chờ kho clip tới 23:00 (không tính làn)" in d for d in nhat)


def test_nhip_2_lam_3_cho_clip_sinh_them_2(tmp_path):
    goc = str(tmp_path)
    _dung_may(goc, 9, 2, 3)
    ra, sinh = _nhip(goc)
    assert ra["lan_trong"] == 2 and len(sinh) == 2
    assert not set(sinh) & {"K1", "K2", "K3", "K4", "K5"}


def test_nhip_tran_tong_7_luot(tmp_path):
    goc = str(tmp_path)
    _dung_may(goc, 9, 1, 5)                 # 3 làn trống nhưng 6/7 lượt tổng
    ra, sinh = _nhip(goc)
    assert ra["tran_tong"] == 7 and ra["lan_trong"] == 1 and len(sinh) == 1
    goc2 = str(tmp_path / "m2")
    os.makedirs(goc2)
    _dung_may(goc2, 9, 1, 6)                # 7/7 → không sinh dù còn làn API
    ra, sinh = _nhip(goc2)
    assert sinh == [] and ra["chan"].startswith("trần tổng 7/7 lượt")


def test_nhip_dau_cu_hoac_pid_chet_tinh_lan_thuong(tmp_path):
    goc = str(tmp_path)
    _dung_may(goc, 9, 4, 3)
    _sua_dau(goc, "K5", luc=time.time() - khe.TUOI_CHO_CLIP_GIAY - 60)   # cũ
    _sua_dau(goc, "K6", pid=PID_GIA_DA_CHET)                             # PID chết
    ra, sinh = _nhip(goc)
    assert (ra["so_dang"], ra["so_cho_clip"]) == (6, 1)
    assert sinh == [] and ra["chan"] == "hết làn API (6/4 đang chạy, +1 chờ kho clip)"


def test_nhip_khong_ai_cho_clip_nhu_cu(tmp_path):
    goc = str(tmp_path)
    _dung_may(goc, 3, 0, 0)
    _cai_lai = dieu_phoi.doc_cai(goc)
    _cai_lai["lan_api"] = 2
    dieu_phoi.ghi_cai(goc, **_cai_lai)
    ra, sinh = _nhip(goc)
    assert len(sinh) == 2 and ra["so_cho_clip"] == 0 and ra["tran_tong"] == 3
