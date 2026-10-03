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


# ── Đợt 2: kieu_tieu_de / hook ──────────────────────────────────────────────

def _van_nhan(goc, ma, ma_goi, truc, gt, kl):
    tu_hoc.ghi_van(goc, ma, ma_goi, {truc: gt}, {})
    v = tu_hoc.doc_van(goc, ma)
    v[ma_goi]["ket7"] = kl
    tu_hoc._luu_van(goc, ma, v)


def test_regex_duong_lui():
    assert tu_hoc.nhan_tieu_de_regex("Bạn có biết vì sao?") == "cau_hoi"
    assert tu_hoc.nhan_tieu_de_regex("5 sai lầm khi nấu cơm") == "canh_bao"
    assert tu_hoc.nhan_tieu_de_regex("7 thói quen của người giàu") == "so_dem"
    assert tu_hoc.nhan_tieu_de_regex("Sự thật ít ai biết") == "bi_mat"
    assert tu_hoc.nhan_tieu_de_regex("Chuyện nhà bên") == "khac"
    assert tu_hoc.nhan_hook_regex("Hãy tưởng tượng bạn đang ở một nơi xa") == "canh_tinh_huong"
    assert tu_hoc.nhan_hook_regex("Năm 1990, có một người đàn ông") == "so_lieu_su_that"
    assert tu_hoc.nhan_hook_regex("Ngày xưa có một người") == "ke_chuyen"


def test_gan_nhan_llm_truoc_regex():
    nhan, doan = tu_hoc.gan_nhan("kieu_tieu_de", ["a?", "b", "c"], {"A": "so_dem", "B": "BAY_BA", "c": "bi_mat"})
    assert nhan == ["so_dem", "khac", "bi_mat"] and doan == [False, True, False]  # nhãn lạ → regex


def test_he_so_trong_khoang_va_trong_thi_khong_doi(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    # trục chưa có ván → không làm gì
    assert tu_hoc.he_so_chon(g, "A", "kieu_tieu_de", ["so_dem", "cau_hoi"], "h") == {}
    sau, ghi = tu_hoc.bo_chon(g, "A", "kieu_tieu_de", ["x", "y"], "h")
    assert sau(0, {"A": 5, "B": 9}, None) == 0 and "he_so" not in ghi
    for i in range(4):
        _van_nhan(g, "A", "A-%d" % i, "kieu_tieu_de", "so_dem", "thang")
        _van_nhan(g, "A", "A-x%d" % i, "kieu_tieu_de", "cau_hoi", "truot")
    he = tu_hoc.he_so_chon(g, "A", "kieu_tieu_de", ["so_dem", "cau_hoi"], "h")
    assert set(he) == {"so_dem", "cau_hoi"} and all(0.9 <= v <= 1.1 for v in he.values())
    assert he == tu_hoc.he_so_chon(g, "A", "kieu_tieu_de", ["so_dem", "cau_hoi"], "h")  # tất định
    assert he["so_dem"] > he["cau_hoi"]


def test_bo_chon_ghi_he_so_va_doi_chon(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    for i in range(30):
        _van_nhan(g, "A", "A-%d" % i, "hook", "ke_chuyen", "thang")
        _van_nhan(g, "A", "A-x%d" % i, "hook", "cau_hoi", "truot")
    sau, ghi = tu_hoc.bo_chon(g, "A", "hook", ["Bạn có biết?", "Ngày xưa có một người"], "h")
    # điểm sát nhau: hệ số (~1,1 vs ~0,9) phải lật được thứ tự
    assert sau(0, {"A": 8, "B": 7.9}, {"A": "cau_hoi", "B": "ke_chuyen"}) == 1
    assert ghi["he_so"]["chon_truoc"] == 0 and ghi["he_so"]["chon_sau"] == 1
    kn = tu_hoc.ket_nhan("hook", ["Bạn có biết?", "Ngày xưa có một người"], 1, ghi)
    assert kn["hook"] == "ke_chuyen" and kn["nhan_doan"] is False and kn["he_so_tu_hoc"]
    # chấm hỏng (callback chưa chạy) → regex, đánh dấu đoán
    kn2 = tu_hoc.ket_nhan("hook", ["Bạn có biết?"], 0, {})
    assert kn2["hook"] == "cau_hoi" and kn2["nhan_doan"] is True


def test_cham_cua_viet_nhieu_ban_dung_sau_cham():
    from core import viet_nhieu_ban as vnb

    cap = {}
    tra = '{"chon": "A", "diem": {"A": 8, "B": 7}, "ly_do": "ok", "kieu": {"A": "so_dem"}}'

    def sau(chon, diem, kieu):
        cap.update(chon=chon, diem=diem, kieu=kieu)
        return 1

    chon, *_ = vnb.cham_va_chon(lambda _p: tra, ["x", "y"], "g", sau_cham=sau)
    assert chon == 1 and cap["kieu"] == {"A": "so_dem"} and cap["diem"] == {"A": 8, "B": 7}

    def hong(chon, diem, kieu):
        raise RuntimeError("x")

    assert vnb.cham_va_chon(lambda _p: tra, ["x", "y"], "g", sau_cham=hong)[0] == 0  # học hỏng → giữ chọn LLM


def test_ba_nhan_cu_tu_tieu_de_that_va_bang_diem_md(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    hsd = os.path.join(g, "CHANNEL", "A", "ho-so-video")
    os.makedirs(hsd)
    ca = [("A-0", {"tieu_de": "5 sai lầm khi học"}), ("A-1", {"tieu_de": "x", "tieu_de_cham": {
        "tu_hoc": {"kieu_tieu_de": "bi_mat", "nhan_doan": False}},
        "kich_ban": {"hook_nhan": {"hook": "cau_hoi", "nhan_doan": False}}})]
    for ma, hs in ca:
        hs.update(ma_goi=ma, chi_so={"7d": {"gio_xem": 10 if ma == "A-0" else 99}})
        with open(os.path.join(hsd, ma + ".json"), "w", encoding="utf-8") as f:
            json.dump(hs, f)
    tu_hoc.ghi_van(g, "A", "A-0", {"cum": "c"}, {})  # ván có sẵn, chưa có nhãn đợt 2
    tu_hoc.cham_van(g, "A")
    v = tu_hoc.doc_van(g, "A")
    assert v["A-0"]["nuoc"]["kieu_tieu_de"] == "canh_bao" and v["A-0"]["nuoc"]["nhan_doan"] is True
    assert "hook" not in v["A-0"]["nuoc"]
    assert v["A-1"]["nuoc"]["kieu_tieu_de"] == "bi_mat" and not v["A-1"]["nuoc"].get("nhan_doan")
    assert v["A-1"]["nuoc"]["hook"] == "cau_hoi"
    for ma in ("A-0", "A-1"):  # buộc có kết luận 7d để vào bảng điểm
        v[ma]["ket7"] = "thang"
    tu_hoc._luu_van(g, "A", v)
    md = open(tu_hoc.ghi_bang_diem_md(g, "A"), encoding="utf-8").read()
    assert "## kieu_tieu_de" in md and "## hook" in md
