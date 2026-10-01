"""Sổ thí nghiệm + nhật ký + trạng thái của giám đốc kênh (`core/giam_doc/so_thi_nghiem.py`). Chỉ `tmp_path`."""

from __future__ import annotations

import datetime as _dt
import io
import os

import pytest

from core.giam_doc import so_thi_nghiem as stn

BAY = _dt.datetime(2026, 10, 1, 12, 0)


def _mo(goc, **k):
    a = dict(viec="do_dai", gia_thuyet="dài hơn nhiều giờ xem hơn", chi_so="gx",
             bien={"loai": "tham_so", "khoa": "phut_muc_tieu", "cu": 15, "moi": 17},
             nen={"gia_tri": 4.0, "n": 6}, co_mau=4, han_ngay=28, bay_gio=BAY)
    a.update(k)
    return stn.mo(goc, "A", **a)


def test_mo_doc_va_id_khong_trung(tmp_path):
    goc = str(tmp_path)
    t1, t2 = _mo(goc), _mo(goc)
    assert t1["id"] == "20261001-do_dai-1" and t2["id"] == "20261001-do_dai-2"
    assert t1["trang_thai"] == "mo" and t1["han"] == "2026-10-29T12:00:00" and t1["quay_lui_khi"]["tut_pct"] == 20
    assert [t["id"] for t in stn.doc(goc, "A")] == [t1["id"], t2["id"]]
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "A", "giam-doc", "thi-nghiem.json"))


def test_cap_nhat_cong_video_va_dong(tmp_path):
    goc = str(tmp_path)
    t = _mo(goc)
    stn.cap_nhat(goc, "A", t["id"], video=["v1", "v2"])
    stn.cap_nhat(goc, "A", t["id"], video=["v2", "v3"])
    assert stn.doc(goc, "A")[0]["video"] == ["v1", "v2", "v3"]
    assert stn.cap_nhat(goc, "A", "khong-co", video=["x"]) is None
    stn.dong(goc, "A", t["id"], "giu", {"so": {"moi": 5.0}}, ly_do="tốt hơn 25%", bay_gio=BAY)
    d = stn.doc(goc, "A")[0]
    assert d["trang_thai"] == "giu" and d["ket_luan"]["ly_do"] == "tốt hơn 25%" and not stn.dang_mo(stn.doc(goc, "A"))
    with pytest.raises(ValueError):
        stn.dong(goc, "A", t["id"], "mo")


def test_dang_mo_theo_chi_so_va_het_han(tmp_path):
    goc = str(tmp_path)
    _mo(goc, chi_so="gx", han_ngay=7)
    _mo(goc, chi_so="ti_le_thang", han_ngay=21)
    so_ = stn.doc_so(goc, "A")
    assert len(stn.dang_mo(so_)) == 2 and len(stn.dang_mo(so_, "gx")) == 1
    assert stn.het_han(so_, BAY + _dt.timedelta(days=6)) == []
    assert [t["chi_so"] for t in stn.het_han(so_, BAY + _dt.timedelta(days=8))] == ["gx"]


def test_het_han_gia_han_mot_lan_roi_chua_du(tmp_path):
    goc = str(tmp_path)
    t = _mo(goc, han_ngay=7)
    luc = BAY + _dt.timedelta(days=8)
    assert stn.xu_ly_het_han(goc, "A", t, bay_gio=luc) == "gia_han"
    t = stn.doc(goc, "A")[0]
    assert t["trang_thai"] == "mo" and t["gia_han"] == 1 and t["han"] == (luc + _dt.timedelta(days=7)).isoformat()
    assert stn.xu_ly_het_han(goc, "A", t, bay_gio=luc + _dt.timedelta(days=8)) == "chua_du"
    assert stn.doc(goc, "A")[0]["trang_thai"] == "chua_du"


def test_nhat_ky_noi_dong_va_bo_dong_hong(tmp_path):
    goc = str(tmp_path)
    stn.ghi_nhat_ky(goc, "A", viec="tham_so", khoa="phut_muc_tieu", truoc=15, sau=17, ly_do_llm="x", bay_gio=BAY)
    duong = os.path.join(goc, "CHANNEL", "A", "giam-doc", "nhat-ky.jsonl")
    with io.open(duong, "a", encoding="utf-8") as tep:
        tep.write("{hỏng\n")
    stn.ghi_nhat_ky(goc, "A", viec="chi_dao", sau="ưu tiên cụm X", bay_gio=BAY)
    nk = stn.doc_nhat_ky(goc, "A")
    assert [d["viec"] for d in nk] == ["tham_so", "chi_dao"] and nk[0]["khoa"] == "phut_muc_tieu"
    assert set(nk[0]) >= {"luc", "viec", "truoc", "sau", "ly_do_llm", "so_lieu"}


def test_trang_thai_gop_nong(tmp_path):
    goc = str(tmp_path)
    stn.ghi_trang_thai(goc, "A", da_ghi={"a": {"gia_tri": 1}}, ngay_chay="2026-10-01")
    stn.ghi_trang_thai(goc, "A", da_ghi={"b": {"gia_tri": 2}})
    tt = stn.doc_trang_thai(goc, "A")
    assert set(tt["da_ghi"]) == {"a", "b"} and tt["ngay_chay"] == "2026-10-01"
    assert stn.doc_so(goc, "B") == {"thi_nghiem": [], "nhat_ky": [], "trang_thai": {}}
