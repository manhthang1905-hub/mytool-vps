"""Claude Max kiểm cuối ảnh cảnh theo lô (17/10/2026) — mọi lời gọi Max đều giả. Xem `core/kiem_max_anh.py`."""
import json
import os
import threading

import pytest

from core import chon_anh_canh as cac
from core import kiem_max_anh as kma


def _muc(nhan, d=8, **k):
    return dict({"nhan": nhan, "fit": d, "tone": 9, "defects": 9, "style": 9, "horror": False, "ly_do": "x"}, **k)


def _tep(tmp_path, ten):
    p = tmp_path / ten
    p.write_bytes(b"png")
    return str(p)


def test_doc_lo_lay_muc_thap_nhat_co_cung_va_ron():
    du = {"canh": [{"canh": 1, "ung_vien": [_muc("A", 5), _muc("S1-B", 8), _muc("C", 9, chu=True)]},
                   {"canh": 2, "ung_vien": [_muc("A", 9, horror=True), _muc("B", 6)], "sua": "show the phone"},
                   {"canh": 9, "ung_vien": [_muc("A")]}, "rác"]}
    kq = kma.doc_lo(du, [3, 2])
    assert kq[1]["tot"] == 1 and kq[1]["tong"] == 8.0            # "S1-B" đọc được; C có chữ → 0
    assert kq[1]["ung_vien"][2]["tong"] == 0.0
    assert kq[2]["tot"] == 1 and kq[2]["tong"] == 6.0 and kq[2]["sua"] == "show the phone"   # tấm rợn xếp sau
    assert set(kq) == {1, 2} and kma.doc_lo(None, [3]) == {}


def _lo(tmp_path, tra, **kw):
    goi_ds = []

    def goi(tin, khoa):
        goi_ds.append((tin, khoa))
        return tra(tin) if callable(tra) else tra
    lo = kma.KiemMax(goi, goc=str(tmp_path), tran=kw.pop("tran", 50), anh_url=lambda p, r, nhan="": "data:" + nhan,
                     **kw)
    return lo, goi_ds


def test_gom_du_lo_thi_mot_luot_cho_ca_lo(tmp_path):
    tra = json.dumps({"canh": [{"canh": i, "ung_vien": [_muc("A", 8)]} for i in range(1, 4)]})
    lo, goi_ds = _lo(tmp_path, tra, lo=3, cho_gom=30)
    kq = [None] * 3

    def mot(i):
        kq[i] = lo.kiem({"ma": i, "loi_doc": "x", "khoanh_khac": "k", "tep": [_tep(tmp_path, "%d.png" % i)]})
    ts = [threading.Thread(target=mot, args=(i,)) for i in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(10)
    assert len(goi_ds) == 1 and all(k["ok"] and k["tong"] == 8.0 for k in kq)
    noi = goi_ds[0][0][0]["content"]
    assert "Scene 3" in noi[0]["text"] and len(noi) == 4                   # 1 chữ + 3 ảnh (không ref)
    assert kma.da_dung_hom_nay(str(tmp_path)) == 1


def test_lo_khong_du_thi_cho_gom_roi_tu_cham(tmp_path):
    lo, goi_ds = _lo(tmp_path, json.dumps({"canh": [{"canh": 1, "ung_vien": [_muc("A", 7)]}]}), lo=6, cho_gom=0.2)
    kq = lo.kiem({"ma": 1, "loi_doc": "x", "khoanh_khac": "", "tep": [_tep(tmp_path, "a.png")]})
    assert kq["ok"] and len(goi_ds) == 1


def test_max_khong_dung_hoac_het_tran_thi_lui_ve_vi(tmp_path):
    class MaxKhongDung(RuntimeError):
        pass

    def hong(_tin):
        raise MaxKhongDung("cạn hạn mức tuần")
    lo, goi_ds = _lo(tmp_path, hong, lo=1)
    kq = lo.kiem({"ma": 1, "tep": [_tep(tmp_path, "a.png")]})
    assert kq["ok"] is False and "cạn hạn mức" in kq["ly_do"]
    assert lo.kiem({"ma": 2, "tep": [_tep(tmp_path, "b.png")]})["ok"] is False and len(goi_ds) == 1   # khỏi thử lại
    lo2, goi2 = _lo(tmp_path, "{}", lo=1, tran=1)                       # lượt đã dùng hôm nay = 1 (ở trên)
    assert lo2.kiem({"ma": 3, "tep": [_tep(tmp_path, "c.png")]})["ok"] is False and goi2 == []
    assert kma.KiemMax(None, goc=str(tmp_path)).kiem({"tep": []})["ly_do"] == "máy không có Claude Max"


# ═══ NỐI VÀO chon_canh ═══

class _May:
    def __init__(self, tmp_path, diem):
        self.tmp, self.diem, self.ve_goi, self.cham_goi = tmp_path, diem, [], []

    def ve(self, prompt, vong):
        self.ve_goi.append(vong)
        return [_tep(self.tmp, "v{0}-{1}.png".format(vong, i)) for i in (1, 2, 3)]

    def cham(self, tep, prompt):
        vong = int(os.path.basename(tep[0])[1])
        self.cham_goi.append(vong)
        return cac.doc_cham({"khoanh_khac": "she reads a text", "ung_vien": [
            {"so": i + 1, "noi_dung": d, "giong": 9, "loi": 9, "phong_cach": 9} for i, d in
            enumerate(self.diem[vong])]}, 3)


def _chay(may, kiem_cuoi, so=None):
    return cac.chon_canh(so_canh=1, prompt="Close-up of the reference character", loi_doc="x", ve=may.ve,
                         cham=may.cham, viet_lai=lambda p, g: "REWRITE of the reference character " + str(len(g)),
                         so=so, ghi=lambda *_: None, kiem_cuoi=kiem_cuoi, nguong_cuoi=7.0)


def test_max_doi_sang_tam_a_khi_dat(tmp_path):
    may = _May(tmp_path, {0: [9, 8, 7]})
    goi = []

    def kc(tep, kk):
        goi.append((tep, kk))
        return {"ok": True, "tot": 2, "tong": 8.0, "ung_vien": {0: {"tong": 4.0}, 1: {"tong": 6.0}, 2: {"tong": 8.0}}}
    kq = _chay(may, kc)
    assert len(goi) == 1 and len(goi[0][0]) == 3 and goi[0][1] == "she reads a text"
    assert kq["chon"]["so"] == 3 and kq["chon"]["boi"] == "max" and kq["chon"]["max_doi"] is True
    assert kq["chon"]["max_tong"] == 8.0 and may.ve_goi == [0]


def test_max_duoi_nguong_thi_viet_lai_va_kiem_lai_tran_hai_vong(tmp_path):
    may = _May(tmp_path, {0: [9, 8, 8], 1: [9, 9, 8], 2: [9, 8, 8]})
    goi = []

    def kc(tep, kk):
        goi.append(tep)
        return {"ok": True, "tot": 0, "tong": 5.0, "ung_vien": {0: {"tong": 5.0}}, "sua": "show the phone"}
    kq = _chay(may, kc)
    assert may.ve_goi == [0, 1, 2] and len(goi) == 3                  # Max kiểm mỗi vòng; tổng 2 vòng viết lại
    assert "Claude Max 5.0/10" in kq["canh_bao"] and kq["xong"]


def test_max_khong_dung_thi_giu_lua_chon_vi_va_ghi_so(tmp_path):
    so = cac.SoChon(str(tmp_path))
    may = _May(tmp_path, {0: [6, 9, 7]})
    kq = _chay(may, lambda t, k: {"ok": False, "ly_do": "Claude Max không dùng được (cạn)"}, so=so)
    assert kq["chon"]["so"] == 2 and kq["chon"]["boi"] == "vi" and "cạn" in kq["max_bo_qua"]
    assert so.lay(1)["max_bo_qua"] and cac.tom_tat(str(tmp_path))["max_bo_qua"] == 1


def test_chay_tiep_dung_lai_ket_qua_max(tmp_path):
    so = cac.SoChon(str(tmp_path))
    may = _May(tmp_path, {0: [9, 8, 7]})
    goi = []

    def kc(tep, kk):
        goi.append(tep)
        return {"ok": True, "tot": 1, "tong": 8.0, "ung_vien": {0: {"tong": 3.0}, 1: {"tong": 8.0}}}
    _chay(may, kc, so=so)
    kq = _chay(_May(tmp_path, {0: [9, 8, 7]}), kc, so=so)
    assert len(goi) == 1 and kq["chon"]["so"] == 2                      # lượt sau không gọi Max lại


def test_khong_cai_dat_thi_tat_kiem_max(tmp_path):
    from types import SimpleNamespace
    from core import auto_khau
    assert auto_khau._kiem_max_cua_luot(SimpleNamespace(goc=str(tmp_path)), SimpleNamespace(thu_muc="x"), "") is None
