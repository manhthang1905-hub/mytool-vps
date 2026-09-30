"""Gỡ trần tự đặt của khâu ảnh/clip (30/09/2026).

Hai trần tách ra: số job CHỜ máy chủ (`_tran_luong_cho`, `tran_api_vps`, suất
toàn máy `core.khe.giu_job`) và số luồng TẢI/GIẢI MÃ (`_suat_tai_cuc_bo` ≤
`_tran_luong_cuc_bo`). `han_muc_may_chu` làm tươi theo TTL. Nhịp hỏi job
không tăng theo số job. Không mạng: mọi máy chủ ở đây là đồ giả.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import core.auto_khau as ak
from core import che_do_vps, khe


def _vps(goc: str, cai: dict) -> None:
    with open(os.path.join(goc, che_do_vps.TEN_MARKER), "w", encoding="utf-8") as tep:
        json.dump({"vm_dir": goc}, tep)
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w",
              encoding="utf-8") as tep:
        json.dump(cai, tep)


@pytest.fixture(autouse=True)
def _sach_han_muc(monkeypatch):
    from core import su_co

    monkeypatch.setattr(ak, "xin_nhip", lambda *_a, **_k: None)
    ak._HAN_MUC.clear()
    cu = su_co.NHIP.moi_phut
    yield
    ak._HAN_MUC.clear()
    su_co.NHIP.moi_phut = cu


class _ClientMe:
    """Chỉ trả `GET /v1/me` — đếm số lần hỏi."""

    def __init__(self, anh: int = 189) -> None:
        self.anh = anh
        self.so_lan = 0
        self.hong = False

    def request(self, _pt, duong):
        assert duong == "/v1/me"
        self.so_lan += 1
        if self.hong:
            raise RuntimeError("mạng rớt")
        return {"limits": {"requests_per_minute": 600000,
                           "concurrent_jobs": {"image": self.anh, "video": 832,
                                               "tts": 3, "music": 3}}}


class _Bc:
    def __init__(self, client, goc: str = "") -> None:
        self.client = client
        self.goc = goc
        self.dong = []

    def ghi(self, d):
        self.dong.append(d)

    def kiem_dung(self):
        return None


# ── han_muc_may_chu: TTL ─────────────────────────────────────────────────────


class TestHanMucTtl:
    def test_trong_ttl_khong_hoi_lai(self):
        cl = _ClientMe()
        bc = _Bc(cl)
        assert ak.han_muc_may_chu(bc)["concurrent_jobs"]["image"] == 189
        ak.han_muc_may_chu(bc)
        ak.han_muc_may_chu(bc)
        assert cl.so_lan == 1
        assert "_luc_hoi" not in ak.han_muc_may_chu(bc)

    def test_het_ttl_thi_hoi_lai_va_nhan_tran_moi(self, monkeypatch):
        cl = _ClientMe(anh=1)
        bc = _Bc(cl)
        gio = [1_000_000.0]
        monkeypatch.setattr(ak.time, "time", lambda: gio[0])
        assert ak.han_muc_may_chu(bc)["concurrent_jobs"]["image"] == 1
        cl.anh = 189
        gio[0] += ak.TTL_HAN_MUC_GIAY - 1
        assert ak.han_muc_may_chu(bc)["concurrent_jobs"]["image"] == 1
        gio[0] += 2
        assert ak.han_muc_may_chu(bc)["concurrent_jobs"]["image"] == 189
        assert cl.so_lan == 2

    def test_hoi_hong_giu_so_cu_va_khong_hoi_day(self, monkeypatch):
        cl = _ClientMe(anh=40)
        bc = _Bc(cl)
        gio = [2_000_000.0]
        monkeypatch.setattr(ak.time, "time", lambda: gio[0])
        ak.han_muc_may_chu(bc)
        cl.hong = True
        gio[0] += ak.TTL_HAN_MUC_GIAY + 1
        assert ak.han_muc_may_chu(bc)["concurrent_jobs"]["image"] == 40
        # Hỏng rồi cũng không hỏi lại trước TTL.
        gio[0] += 5
        ak.han_muc_may_chu(bc)
        assert cl.so_lan == 2

    def test_chua_tung_hoi_duoc_thi_rong_va_khong_hoi_day(self):
        cl = _ClientMe()
        cl.hong = True
        bc = _Bc(cl)
        assert ak.han_muc_may_chu(bc) == {}
        assert ak.han_muc_may_chu(bc) == {}
        assert cl.so_lan == 1


# ── Hai trần: chờ vs tải/giải mã ─────────────────────────────────────────────


class TestHaiTran:
    def test_tran_luong_cho_theo_ram_trong_that(self, monkeypatch):
        monkeypatch.setattr(ak, "_ram_trong_gb", lambda: 8.6)
        monkeypatch.setattr(ak, "_commit_trong_gb", lambda: 23.0)
        assert ak._tran_luong_cho() == ak.TRAN_LUONG_MAY
        monkeypatch.setattr(ak, "_ram_trong_gb", lambda: 3.2)
        assert 1 <= ak._tran_luong_cho() <= 4
        monkeypatch.setattr(ak, "_ram_trong_gb", lambda: 2.0)
        assert ak._tran_luong_cho() == 1
        # Commit cạn (WinError 1455) cũng hạ trần dù RAM vật lý còn.
        monkeypatch.setattr(ak, "_ram_trong_gb", lambda: 8.6)
        monkeypatch.setattr(ak, "_commit_trong_gb", lambda: 3.1)
        assert ak._tran_luong_cho() <= 2

    def test_vps_24_moi_kenh_du_cong_189(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _vps(goc, {"tran_api_vps": 24})
        monkeypatch.setattr(ak, "_tran_luong_cho", lambda: 48)
        monkeypatch.setattr(ak, "_tran_luong_cuc_bo", lambda: 6)
        bc = _Bc(_ClientMe(anh=189), goc)
        assert ak._so_luong(bc, "image", can=150) == 24
        assert ak._so_luong(bc, "video", can=150) == 24
        assert ak._so_luong(bc, "tts", can=40) == 3

    def test_may_chu_khai_1_thi_dung_1(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _vps(goc, {"tran_api_vps": 24})
        monkeypatch.setattr(ak, "_tran_luong_cho", lambda: 48)
        bc = _Bc(_ClientMe(anh=1), goc)
        assert ak._so_luong(bc, "image", can=150) == 1

    def test_suat_tai_cuc_bo_giu_tran_tai(self, monkeypatch):
        monkeypatch.setattr(ak, "_tran_luong_cuc_bo", lambda: 2)
        dang = [0]
        cao = [0]
        khoa = threading.Lock()

        def mot(_):
            with ak._suat_tai_cuc_bo(None):
                with khoa:
                    dang[0] += 1
                    cao[0] = max(cao[0], dang[0])
                time.sleep(0.03)
                with khoa:
                    dang[0] -= 1

        with ThreadPoolExecutor(max_workers=10) as bo:
            list(bo.map(mot, range(20)))
        assert cao[0] == 2
        assert ak._TAI_CUC_BO_DANG[0] == 0


# ── Suất job toàn máy qua mẻ song song ───────────────────────────────────────


class TestSuatJobToanMay:
    def test_nhieu_luong_nhung_tong_may_khong_vuot(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _vps(goc, {"tran_api_vps": 24, "tran_api_tong": 3})
        monkeypatch.setattr(ak, "_tran_luong_cho", lambda: 48)
        bc = ak.BoiCanh(goc=goc, kenh=None, goi_chat=lambda *a, **k: "",
                        client=_ClientMe(anh=189), on_log=lambda _d: None)
        dang = [0]
        cao = [0]
        khoa = threading.Lock()

        def tao(**_kw):
            with khoa:
                dang[0] += 1
                cao[0] = max(cao[0], dang[0])
            return {"id": "x"}

        def lam(c):
            ak._tao_job(bc, tao, idempotency_key="k{0}".format(c))
            time.sleep(0.05)  # "chờ máy chủ"
            with khoa:
                dang[0] -= 1
            return c, False

        monkeypatch.setattr(khe, "giu_job", _giu_job_nhanh(khe.giu_job))
        xong = ak._chay_song_song(bc, list(range(12)), lam, "ảnh", loai_job="image")
        assert xong == 12
        assert cao[0] == 3
        assert khe.so_job_dang_giu(goc, "image") == 0

    def test_muc_co_san_khong_xin_suat(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _vps(goc, {"tran_api_vps": 24, "tran_api_tong": 1})
        monkeypatch.setattr(ak, "_tran_luong_cho", lambda: 48)
        bc = ak.BoiCanh(goc=goc, kenh=None, goi_chat=lambda *a, **k: "",
                        client=_ClientMe(anh=189), on_log=lambda _d: None)
        # Một người ngoài đang giữ suất duy nhất: mục "có sẵn" vẫn qua ngay.
        with khe.giu_job(goc, "image", tran_may_chu=189):
            xong = ak._chay_song_song(bc, list(range(5)), lambda c: (c, True),
                                      "ảnh", loai_job="image")
        assert xong == 5


def _giu_job_nhanh(goc_fn):
    def boc(*a, **kw):
        kw["nhip_kiem_giay"] = 0.02
        return goc_fn(*a, **kw)
    return boc


# ── Nhịp hỏi: số lượt hỏi RIÊNG không tăng theo số job ───────────────────────


class _MayChuSoChungMu:
    """Sổ chung (`list`) không bao giờ thấy job — ép lưới hỏi riêng chạy."""

    def __init__(self, tre: float) -> None:
        self._tre = tre
        self._khoa = threading.Lock()
        self._job = {}
        self.retrieve_luc = []
        self.jobs = self

    def tao(self, ten):
        ma = "job-" + ten
        self._job[ma] = time.time()
        return ma

    def retrieve(self, ma):
        with self._khoa:
            self.retrieve_luc.append(time.time())
        xong = time.time() - self._job[ma] >= self._tre
        return {"id": ma, "status": "succeeded" if xong else "processing"}

    def list(self, **_kw):
        return {"data": [], "has_more": False, "next_cursor": None}


def test_luot_hoi_rieng_bi_van_theo_nhip_khong_theo_so_job(monkeypatch):
    monkeypatch.setattr(ak, "NHIP_HOI_RIENG", 0.05)
    may = _MayChuSoChungMu(tre=0.4)
    bc = ak.BoiCanh(goc="", kenh=None, goi_chat=lambda *a, **k: "",
                    client=may, on_log=lambda _d: None, nhip_hoi=0.5)
    so = ak.SoTheoDoi(bc, nhip=0.5)
    ma = [may.tao(str(i)) for i in range(30)]
    try:
        with ThreadPoolExecutor(max_workers=30) as bo:
            ket = list(bo.map(lambda m: so.cho(m, tran=60), ma))
    finally:
        so.dong()
    assert all(k["status"] == "succeeded" for k in ket)
    # Trong mọi cửa sổ `nhip` giây, số lượt hỏi riêng ≤ van của sổ.
    luc = sorted(may.retrieve_luc)
    for i, t in enumerate(luc):
        trong_cua_so = sum(1 for u in luc[i:] if u - t < 0.5 - 1e-3)
        assert trong_cua_so <= ak.SO_HOI_RIENG_MOI_NHIP
