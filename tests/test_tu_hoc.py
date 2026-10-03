"""Tests `core/tu_hoc.py` — ván, Beta có trọng số, tiên nghiệm nhóm, Thompson, hệ số xếp hạng."""

import json
import os
import random

from core import tu_hoc


def _kenh(goc, ma, nhom="n1"):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('nhom: "{0}"\n'.format(nhom))


def _van(goc, ma, ma_goi, cum, kl48="", kl7=""):
    tu_hoc.ghi_van(goc, ma, ma_goi, {"cum": cum, "cong_thuc": "v7"}, {})
    v = tu_hoc.doc_van(goc, ma)
    if kl48:
        v[ma_goi]["ket48"] = kl48
    if kl7:
        v[ma_goi]["ket7"] = kl7
    tu_hoc._luu_van(goc, ma, v)


def test_do_dai():
    assert [tu_hoc.nhom_do_dai(g) for g in (300, 700, 1000, 1500, None)] == ["<10", "10-15", "15-20", ">20", ""]


def test_ghi_van_giu_ket_qua(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _van(g, "A", "A-1", "x", kl48="thang")
    tu_hoc.ghi_van(g, "A", "A-1", {"cum": "y"}, {"ctr_so": 5})
    v = tu_hoc.doc_van(g, "A")["A-1"]
    assert v["ket48"] == "thang" and v["nuoc"] == {"cum": "y"} and v["du_doan"]["ctr_so"] == 5


def test_cham_van_hs(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    hsd = os.path.join(g, "CHANNEL", "A", "ho-so-video")
    os.makedirs(hsd)
    for i, gio in enumerate((10, 20, 30, 40, 50)):
        hs = {"ma_goi": "A-%d" % i, "cong_thuc": "vph", "thoi_luong_giay": 1000,
              "thumbnail": {"kieu": "k1"}, "chi_so": {"7d": {"gio_xem": gio}}}
        with open(os.path.join(hsd, "A-%d.json" % i), "w", encoding="utf-8") as f:
            json.dump(hs, f)
    r = tu_hoc.cham_van(g, "A")
    assert r["moi"] == 5 and r["ket7"] == 5
    v = tu_hoc.doc_van(g, "A")
    assert v["A-4"]["ket7"] == "thang" and v["A-0"]["ket7"] == "truot"  # trung vị 30
    assert v["A-0"]["nuoc"] == {"cong_thuc": "vph", "kieu_bia": "k1", "do_dai": "15-20"}
    assert "cum" not in v["A-0"]["nuoc"] and "ket48" not in v["A-0"]  # thiếu số thì để trống


def test_beta_trong_so(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _van(g, "A", "1", "x", kl7="thang")          # nặng 1
    _van(g, "A", "2", "x", kl48="thang")         # nặng 0,5
    _van(g, "A", "3", "x", kl48="truot")         # nặng 0,5
    _van(g, "A", "4", "x")                       # chưa kết luận
    o = tu_hoc.bang_diem(g, "A")["cum"]["x"]
    assert (o["a"], o["b"], o["n"]) == (2.5, 1.5, 3)


def test_tien_nghiem_nhom(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _kenh(g, "B")
    _kenh(g, "C", nhom="khac")
    _van(g, "B", "B1", "x", kl7="thang")
    _van(g, "B", "B2", "x", kl7="thang")
    _van(g, "C", "C1", "x", kl7="thang")         # khác nhóm: không tính
    o = tu_hoc.bang_diem(g, "A")["cum"]["x"]
    assert abs(o["a"] - 1.6) < 1e-9 and o["b"] == 1 and o["n"] == 0


def test_thompson_co_dinh(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    for i in range(8):
        _van(g, "A", "m%d" % i, "manh", kl7="thang")
        _van(g, "A", "y%d" % i, "yeu", kl7="truot")
    r1 = tu_hoc.rut(g, "A", "cum", ["manh", "yeu", "moi"], random.Random(7))
    r2 = tu_hoc.rut(g, "A", "cum", ["manh", "yeu", "moi"], random.Random(7))
    assert r1 == r2 and set(r1) == {"manh", "yeu", "moi"}
    assert r1["manh"] > r1["yeu"]
    assert all(0 <= x <= 1 for x in r1.values())


def test_he_so_xep_hang_trong_khoang(tmp_path):
    from core import chien_luoc
    from core.chien_luoc import ngu_canh

    g = str(tmp_path)
    _kenh(g, "A")
    for i in range(4):
        _van(g, "A", "m%d" % i, "manh", kl7="thang")
        _van(g, "A", "y%d" % i, "yeu", kl7="truot")
    nc = ngu_canh.dung(g, "A", co_v7=False)
    bang = {"vph": [{"ma": "1", "diem": 100, "cum": ["manh"], "ly_do": []},
                    {"ma": "2", "diem": 100, "cum": ["yeu"]},
                    {"ma": "3", "diem": 100, "cum": []}]}
    chien_luoc._ap_he_so_cum(nc, bang)
    for d in bang["vph"]:
        assert 0.8 <= d["he_so_cum"] <= 1.2
    assert bang["vph"][-1]["he_so_cum"] == 1.0 or any(d["ma"] == "3" and d["he_so_cum"] == 1.0 for d in bang["vph"])
    assert any("tự học" in x for x in next(d for d in bang["vph"] if d["ma"] == "1")["ly_do"])


def test_bang_diem_md(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _van(g, "A", "1", "x", kl7="thang")
    assert os.path.isfile(tu_hoc.ghi_bang_diem_md(g, "A"))
