"""Sổ thời gian job + trần chờ ảnh thích nghi (`core/thoi_gian_job.py`, 20/10/2026). Không mạng, chỉ `tmp_path`."""

from __future__ import annotations

import pytest

from core import auto_khau as ak
from core import thoi_gian_job as tg


@pytest.fixture(autouse=True)
def _xoa_dem():
    tg._DEM.clear()
    yield
    tg._DEM.clear()


def test_ghi_doc_va_cat_giu_300_mau(tmp_path):
    goc = str(tmp_path)
    for i in range(tg.GIU_TOI_DA + 20):
        assert tg.ghi(goc, "image", 10 + i)
    ds = tg.doc(goc)["image"]
    assert len(ds) == tg.GIU_TOI_DA and ds[0] == 30.0 and ds[-1] == 10.0 + tg.GIU_TOI_DA + 19
    assert not tg.ghi(goc, "image", 0) and not tg.ghi("", "image", 5)


def test_tran_anh_chua_du_mau_la_5_phut(tmp_path):
    goc = str(tmp_path)
    for _ in range(tg.SO_MAU_TOI_THIEU - 1):
        tg.ghi(goc, "image", 30)
    assert tg.tran_cho_anh(goc) == 300.0


def test_tran_anh_bang_4_lan_p90_kep_3_12_phut(tmp_path):
    goc = str(tmp_path)
    for i in range(100):                      # p90 = 100 giây → 400 giây
        tg.ghi(goc, "image", 100 if i >= 80 else 50)
    assert tg.tran_cho_anh(goc) == pytest.approx(400.0)
    tg._DEM.clear()
    goc2 = str(tmp_path / "nhanh")
    for _ in range(40):
        tg.ghi(goc2, "image", 20)             # 4 × 20 = 80 giây → sàn 3 phút
    assert tg.tran_cho_anh(goc2) == 180.0
    goc3 = str(tmp_path / "cham")
    for _ in range(40):
        tg.ghi(goc3, "image", 400)            # 4 × 400 → trần 12 phút
    assert tg.tran_cho_anh(goc3) == 720.0


def test_giay_cua_job_uu_tien_moc_may_chu():
    goi = {"created_at": "2026-10-20T06:50:57.761Z", "completed_at": "2026-10-20T06:51:23.165Z"}
    assert tg.giay_cua_job(goi, 99.0) == pytest.approx(25.404, abs=0.01)
    assert tg.giay_cua_job({"status": "succeeded"}, 42.0) == 42.0


class _Bc:
    def __init__(self, goc):
        self.goc = goc


def test_auto_khau_tran_anh_va_ghi_mau(tmp_path):
    goc = str(tmp_path)
    assert ak._tran_cho_anh(object()) == ak.TRAN_CHO_JOB        # không gốc → trần cũ
    assert ak._tran_cho_anh(_Bc(goc)) == 300.0                  # chưa đủ mẫu
    ak._ghi_thoi_gian_job(_Bc(goc), "image", {"created_at": "2026-10-20T00:00:00Z",
                                              "completed_at": "2026-10-20T00:01:10Z"}, 0.0)
    assert tg.doc(goc)["image"] == [70.0]


def test_tao_anh_dung_tran_thich_nghi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    for _ in range(40):
        tg.ghi(goc, "image", 60)              # 4 × 60 = 240 giây
    thay = {}

    def cho_job(bc, job, tran=ak.TRAN_CHO_JOB, ten_viec="", so=None):
        thay["tran"] = tran
        return {"id": "j", "status": "succeeded", "created_at": "2026-10-20T00:00:00Z",
                "completed_at": "2026-10-20T00:00:50Z"}

    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: {"id": "j", "status": "queued"})
    monkeypatch.setattr(ak, "_cho_job", cho_job)

    class _Hop:
        def lay(self):
            return []

    class _Client:
        class images:  # noqa: N801
            create = staticmethod(lambda **kw: None)

    bc = _Bc(goc)
    bc.client = _Client()
    goi = ak._tao_anh(bc, None, "lời nhắc", _Hop(), "khoa")
    assert goi["id"] == "j" and thay["tran"] == pytest.approx(240.0)
    assert tg.doc(goc)["image"][-1] == 50.0
