"""Vòng học KÍN (06/10/2026): nhãn chuẩn, kết quả tương đối, cảnh báo học, lệnh chiến trường → chọn nguồn,
não thấy kết quả lần thử, bài học khám nghiệm vào lời nhắc, mục "Tín hiệu học" của báo cáo ngày.

Toàn dữ liệu GIẢ trong tmp_path — không mạng, không AI, không đụng số liệu thật."""

import datetime as _dt
import json
import os
import random
import time
from types import SimpleNamespace

import pytest

from core import nao, tu_hoc, vong_hoc
from core.chien_luoc import ket_qua, tan_cong


def _kenh(goc, ma, nhom="n1"):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('nhom: "{0}"\n'.format(nhom))
    return d


def _ho_so(goc, ma, ma_goi, **kw):
    d = os.path.join(goc, "CHANNEL", ma, "ho-so-video")
    os.makedirs(d, exist_ok=True)
    hs = dict({"ma_goi": ma_goi}, **kw)
    with open(os.path.join(d, ma_goi + ".json"), "w", encoding="utf-8") as f:
        json.dump(hs, f, ensure_ascii=False)


def _ghi_van(goc, ma, van):
    tu_hoc._luu_van(goc, ma, van)  # noqa: SLF001


# ── nhãn chuẩn ──────────────────────────────────────────────────────────────

def test_chuan_gia_tri_gop_bien_the_bia():
    assert tu_hoc.chuan_gia_tri("kieu_bia", "khuon_thang_2") == "khuon_thang"
    assert tu_hoc.chuan_gia_tri("kieu_bia", " Chuan_Ngach_3 ") == "chuan_ngach"
    assert tu_hoc.chuan_gia_tri("kieu_bia", "portrait_main") == "portrait_main"
    assert tu_hoc.chuan_gia_tri("cum", "tep_2") == "tep_2"  # chỉ trục bìa mới bỏ hậu tố số


def test_bang_diem_gop_bien_the_va_he_so_theo_nhan_tho(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _ghi_van(g, "A", {"1": {"nuoc": {"kieu_bia": "khuon_thang"}, "ket48": "truot"},
                      "2": {"nuoc": {"kieu_bia": "khuon_thang_2"}, "ket48": "truot"},
                      "3": {"nuoc": {"kieu_bia": "portrait_main"}, "ket48": "thang"}})
    bd = tu_hoc.bang_diem(g, "A")["kieu_bia"]
    assert set(bd) == {"khuon_thang", "portrait_main"} and bd["khuon_thang"]["n"] == 2
    he = tu_hoc.he_so_chon(g, "A", "kieu_bia", ["khuon_thang_2", "khuon_thang_3", "portrait_main"], "hat")
    assert set(he) == {"khuon_thang_2", "khuon_thang_3", "portrait_main"}
    assert he["khuon_thang_2"] == he["khuon_thang_3"]  # cùng một cánh tay
    assert all(0.9 <= x <= 1.1 for x in he.values())


def test_nuoc_tu_ghi_nhan_chuan_va_ban_tho():
    nuoc = tu_hoc._nuoc_tu({}, {"thumbnail": {"kieu": "chuan_ngach_3"}}, None)  # noqa: SLF001
    assert nuoc["kieu_bia"] == "chuan_ngach" and nuoc["kieu_bia_tho"] == "chuan_ngach_3"
    assert "kieu_bia_tho" not in tu_hoc._nuoc_tu({}, {"thumbnail": {"kieu": "k1"}}, None)  # noqa: SLF001


def test_nhan_cum_uu_tien_nhan_luc_chon():
    assert tu_hoc.nhan_cum({"cum_tu_hoc": "a", "cum": ["b"]}) == "a"
    assert tu_hoc.nhan_cum({"cum_tu_hoc": "", "cum": ["b"]}) == "b"
    assert tu_hoc.nhan_cum({"tieu_de": "x"}, lambda td: ["c"]) == "c"


# ── kết luận 48h ────────────────────────────────────────────────────────────

def test_ket48_bo_co_thang_som_va_lui_72h():
    vm_som = SimpleNamespace(thang=True, hien_thi_48h=None)  # cờ "thắng sớm" theo mốc 13h
    assert tu_hoc._ket_luan_48h(ket_qua, vm_som, {"chi_so": {}}, 6000.0) == ""  # noqa: SLF001
    vm_that = SimpleNamespace(thang=True, hien_thi_48h=9000.0)
    assert tu_hoc._ket_luan_48h(ket_qua, vm_that, {"chi_so": {}}, 6000.0) == "thang"  # noqa: SLF001
    hs = {"chi_so": {"48h": {"impressions": None, "views": 6}, "72h": {"impressions": 7000}}}
    assert tu_hoc._ket_luan_48h(ket_qua, None, hs, 6000.0) == "thang"  # noqa: SLF001


# ── kết quả tương đối ───────────────────────────────────────────────────────

def test_ket_tv_va_ket_ctr_so_trung_vi_kenh(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    hien = [50, 120, 300, 800, 2000]
    ctr = [1.0, 2.0, 3.0, 4.0, 5.0]
    van = {}
    for i, (h, c) in enumerate(zip(hien, ctr)):
        ma = "A-%d" % i
        _ho_so(g, "A", ma, chi_so={"48h": {"impressions": h, "ctr": c}})
        van[ma] = {"ma_goi": ma, "nuoc": {"kieu_bia": "k%d" % (i % 2), "cum": "x"}}
    _ghi_van(g, "A", van)
    r = tu_hoc.cham_van(g, "A")
    assert r["ket_tv"] == 5
    v = tu_hoc.doc_van(g, "A")
    assert [v["A-%d" % i]["ket_tv"] for i in range(5)] == ["truot", "truot", "thang", "thang", "thang"]  # tv = 300
    assert "ket_ctr" not in v["A-0"]                     # 50 hiển thị < 100: CTR còn nhiễu
    assert v["A-1"]["ket_ctr"] == "truot" and v["A-4"]["ket_ctr"] == "thang"  # tv CTR(120..2000) = 3,5
    bd = tu_hoc.bang_diem(g, "A")
    assert bd["cum"]["x"]["n_tv"] == 5 and bd["cum"]["x"]["thang_tv"] == 3
    assert "n_ctr" not in bd["cum"]["x"]                 # CTR chỉ chấm trục bao bì
    assert bd["kieu_bia"]["k0"]["n_ctr"] + bd["kieu_bia"]["k1"]["n_ctr"] == 4
    # chấm lại không đổi gì thì không ghi lại
    assert tu_hoc.cham_van(g, "A")["ket_tv"] == 0


def test_ket_tv_khong_cong_khi_da_co_7d(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _ghi_van(g, "A", {"1": {"nuoc": {"cum": "x"}, "ket7": "thang", "ket_tv": "truot"}})
    o = tu_hoc.bang_diem(g, "A")["cum"]["x"]
    assert (o["a"], o["b"], o["n"]) == (2.0, 1.0, 1) and "n_tv" not in o


# ── cảnh báo học ────────────────────────────────────────────────────────────

def test_canh_bao_ghi_doc_va_rut_khong_im_lang(tmp_path, monkeypatch):
    g = str(tmp_path)
    tu_hoc.canh_bao(g, "thu", RuntimeError("hỏng giả"), "A")
    ds = tu_hoc.doc_canh_bao(g, 24.0)
    assert ds and ds[-1]["nguon"] == "thu" and ds[-1]["kenh"] == "A" and "hỏng giả" in ds[-1]["loi"]
    assert tu_hoc.doc_canh_bao(g, 24.0, bay_gio=time.time() + 3 * 86400) == []  # quá 24h

    def hong(*a, **k):
        raise ValueError("sổ hành động hỏng")

    monkeypatch.setattr(nao, "ap_hieu_luc_rut", hong)
    ra = tu_hoc.rut(g, "A", "cum", ["x"], random.Random(1))
    assert set(ra) == {"x"}                                      # vẫn rút được — học không chặn sản xuất
    assert any(d["nguon"] == "nao.ap_hieu_luc_rut" for d in tu_hoc.doc_canh_bao(g))


def test_vong_hoc_buoc_hong_thanh_canh_bao(tmp_path):
    g = str(tmp_path)
    dong = []
    log = vong_hoc._log_kem_canh_bao(g, "A", dong.append)  # noqa: SLF001
    log("  0) [vòng học] tự học (chấm ván) hỏng: KeyError: 'x' — bỏ qua.")
    log("  0) [vòng học] số liệu Studio: nối 1 video_id, điền 0 mốc mới.")
    assert len(dong) == 2
    cb = tu_hoc.doc_canh_bao(g)
    assert len(cb) == 1 and cb[0]["nguon"].startswith("vong_hoc:") and "KeyError" in cb[0]["loi"]


# ── lệnh chiến trường → chọn nguồn (trọng số mềm) ───────────────────────────

def _nc(goc, ma="A", bay_gio=None):
    ghi = []
    return SimpleNamespace(goc=goc, ma_kenh=ma, bay_gio=bay_gio or _dt.datetime(2026, 10, 6, 9, 0),
                           cum_cua=lambda td: [], ghi=ghi.append, _ghi=ghi)


def test_tan_cong_he_so_co_tran():
    assert tan_cong.he_so(0) == 1.0 and tan_cong.he_so(50) == 1.15
    assert tan_cong.he_so(250) == 1.0 + tan_cong.TRAN and tan_cong.he_so(-5) == 1.0 and tan_cong.he_so("x") == 1.0


def test_tan_cong_nan_thu_hang_mem(tmp_path):
    g = str(tmp_path)
    tan_cong.ghi(g, {"de_xuat_tan_cong": [{"kenh": "A", "vung": [{"ma": "vung-b", "ten": "B", "co_hoi": 80,
                                                                  "diem": 92}]},
                                          {"kenh": "Z", "vung": [{"ma": "vung-a", "diem": 99}]}]}, "2026-10-06")
    bang = {"v7": [{"ma": "1", "diem": 100.0, "cum": ["vung-a"]},
                   {"ma": "2", "diem": 80.0, "cum": ["vung-b"]},
                   {"ma": "3", "diem": 70.0, "cum": ["vung-b"]}]}
    n, so_vung = tan_cong.ap_he_so(_nc(g), bang)
    assert (n, so_vung) == (2, 1)
    ds = bang["v7"]
    assert [d["ma"] for d in ds] == ["2", "1", "3"]          # 80 × 1,276 = 102,08 vượt 100
    assert ds[0]["he_so_tan_cong"] <= 1.0 + tan_cong.TRAN and ds[0]["tin_hieu"]["tan_cong"] == "vung-b"
    assert "he_so_tan_cong" not in ds[1]                      # vùng của kênh khác: không đụng


def test_tan_cong_tep_cu_khong_ap(tmp_path):
    g = str(tmp_path)
    tan_cong.ghi(g, {"de_xuat_tan_cong": [{"kenh": "A", "vung": [{"ma": "vung-b", "diem": 90}]}]}, "2026-09-20")
    bang = {"v7": [{"ma": "1", "diem": 10.0, "cum": ["vung-b"]}]}
    assert tan_cong.ap_he_so(_nc(g), bang) == (0, 0) and bang["v7"][0]["diem"] == 10.0
    assert tan_cong.tuoi_ngay(g, _dt.datetime(2026, 10, 6)) == 16


def test_tan_cong_vung_ai_theo_link(tmp_path):
    g = str(tmp_path)
    tan_cong.ghi(g, {"de_xuat_tan_cong": [{"kenh": "A", "vung": [{"ma": "ai-moi", "diem": 100}]}]}, "2026-10-06")
    os.makedirs(os.path.join(g, "workspace", "chien-truong"), exist_ok=True)
    with open(os.path.join(g, tan_cong.TEP_VUNG_AI), "w", encoding="utf-8") as f:
        json.dump({"video": {"https://example.invalid/v1": "ai-moi"}}, f)
    bang = {"vph": [{"ma": "1", "diem": 10.0, "link": "https://example.invalid/v1"}]}
    assert tan_cong.ap_he_so(_nc(g), bang)[0] == 1 and bang["vph"][0]["diem"] == 13.0


def test_xep_hang_nuot_loi_tan_cong_co_canh_bao(tmp_path, monkeypatch):
    from core import chien_luoc

    def hong(*a, **k):
        raise RuntimeError("tệp lệnh hỏng")

    monkeypatch.setattr(tan_cong, "ap_he_so", hong)
    nc = _nc(str(tmp_path))
    chien_luoc._ap_tan_cong(nc, {"v7": []})  # noqa: SLF001 — không ném
    assert any(d["nguon"] == "tan_cong" for d in tu_hoc.doc_canh_bao(str(tmp_path)))
    assert "chiến trường" in nc._ghi[0]


def test_tan_cong_khong_bi_nap_nhu_cong_thuc():
    from core import chien_luoc

    assert "tan_cong" not in chien_luoc.so_dang_ky(tai_lai=True)


# ── bộ não thấy kết quả lần thử ─────────────────────────────────────────────

def _hd_thu(goc, kenh, truc, gia_tri, so_video=2, kiem="2026-10-10"):
    os.makedirs(nao.duong_nao(goc), exist_ok=True)
    nao.ghi_hanh_dong(goc, [{"id": "n001", "luc": "2026-10-03T08:00:00", "lenh": "thu",
                             "tham_so": {"kenh": kenh, "truc": truc, "gia_tri": gia_tri, "so_video": so_video,
                                         "da_dung": 0},
                             "ly_do": "giả thuyết thử nghiệm", "du_doan": "video kế có hiển thị cao hơn trung vị",
                             "kiem_ngay": kiem, "trang_thai": "mo", "cham": None, "ghi_chu_cham": ""}])


def test_tru_luot_ghi_goi_va_bao_cao_in_ket_qua(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _hd_thu(g, "A", "kieu_bia", "khuon_thang")
    tu_hoc.ghi_van(g, "A", "A-0001", {"kieu_bia": "khuon_thang", "cum": "x"})  # nhãn chuẩn khớp lần thử
    ts = nao.doc_hanh_dong(g)[0]["tham_so"]
    assert ts["da_dung"] == 1 and ts["goi"] == ["A-0001"]
    v = tu_hoc.doc_van(g, "A")
    v["A-0001"]["ket48"] = "truot"
    v["A-0001"]["ket_tv"] = "thang"
    _ghi_van(g, "A", v)
    _ho_so(g, "A", "A-0001", chi_so={"48h": {"impressions": 4321, "ctr": 4.2}})
    bc = "\n".join(nao.bao_cao_hanh_dong(g, _dt.datetime(2026, 10, 11), chi_can_chu_y=True))
    assert "TỚI HẠN KIỂM" in bc and "A-0001: 48h trượt" in bc and "4.321" in bc


def test_thu_kieu_bia_khop_bien_the(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _hd_thu(g, "A", "kieu_bia", "khuon_thang_2")              # não ghi biến thể — vẫn là cánh tay khuon_thang
    he = tu_hoc.he_so_chon(g, "A", "kieu_bia", ["khuon_thang_3", "portrait_main"], "hat")
    assert he["khuon_thang_3"] == 1.1                         # `thu` = trần Thompson
    rd = tu_hoc.rut(g, "A", "cum", ["x"], random.Random(0))
    assert 0.0 <= rd["x"] <= 1.0


def test_thu_toi_han_chua_ra_video(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    _hd_thu(g, "A", "cum", "chua-co")
    bc = "\n".join(nao.bao_cao_hanh_dong(g, _dt.datetime(2026, 10, 11), chi_can_chu_y=True))
    assert "chưa ra video nào" in bc


# ── bài học khám nghiệm vào lời nhắc tiêu đề / bìa ──────────────────────────

def test_bai_kham_nghiem_cho_moi_khau_va_lui_kenh_goc(monkeypatch):
    from core import auto_khau
    from core.chien_luoc import bai_hoc

    goi = []

    def gia(goc, ma, dung_cho="", toi_da=5):
        goi.append((ma, dung_cho))
        return "- bài {0} cho {1}".format(dung_cho, ma) if ma == "K" else ""

    monkeypatch.setattr(bai_hoc, "khoi_kham_nghiem", gia)
    assert auto_khau._bai_kham_nghiem("g", "K-v2", "tieu_de") == "- bài tieu_de cho K"  # noqa: SLF001
    assert auto_khau._bai_kham_nghiem("g", "K", "bia") == "- bài bia cho K"  # noqa: SLF001
    assert auto_khau._bai_kham_nghiem("g", "", "bia") == ""  # noqa: SLF001
    assert ("K-v2", "tieu_de") in goi


# ── tín hiệu học thiếu + mục báo cáo ngày ───────────────────────────────────

def test_tin_hieu_thieu_va_muc_hoc(tmp_path, monkeypatch):
    from core import bao_cao_ngay as bc

    g = str(tmp_path)
    _kenh(g, "A")
    _ghi_van(g, "A", {"A-1": {"nuoc": {"kieu_bia": "k"}, "ngay": "2026-09-20"},
                      "A-2": {"nuoc": {"cum": "x"}, "ngay": "2026-10-05"},
                      "A-3": {"nuoc": {"cum": "x"}, "ket48": "truot", "ngay": "2026-09-20"}})
    _ho_so(g, "A", "A-1", lich_dang="21/09/2026 05:00")
    bay = _dt.datetime(2026, 10, 6, 7, 0)
    t = tu_hoc.tin_hieu_thieu(g, "A", bay.timestamp())
    assert t["thieu_48h"] == ["A-1"] and t["khong_cum"] == 1 and t["van"] == 3
    assert t["van_cu_gio"] is None                            # chưa từng chấm (chưa có bang-diem.md)
    tu_hoc.canh_bao(g, "bo_cum", "không có bộ cụm", "A")
    monkeypatch.setattr(bc, "_cac_kenh", lambda goc: ["A", "B"])
    ra = "\n".join(bc._muc_hoc(g, _dt.datetime.now()))  # noqa: SLF001
    assert "Thiếu số 48h" in ra and "A 1" in ra
    assert "chưa chấm" in ra and "Lệnh chiến trường" in ra and "Cảnh báo học 24h: 1" in ra
    assert "B" not in ra.replace("bo_cum", "")               # kênh chưa có ván: không báo


def test_muc_hoc_vong_kin(tmp_path, monkeypatch):
    from core import bao_cao_ngay as bc

    g = str(tmp_path)
    _kenh(g, "A")
    _ghi_van(g, "A", {"A-1": {"nuoc": {"cum": "x"}, "ket48": "truot", "ngay": "2026-09-20"}})
    tu_hoc.ghi_bang_diem_md(g, "A")
    tan_cong.ghi(g, {"de_xuat_tan_cong": []}, _dt.date.today().isoformat())
    monkeypatch.setattr(bc, "_cac_kenh", lambda goc: ["A"])
    assert bc._muc_hoc(g, _dt.datetime.now()) == ["- vòng học kín: mọi kênh có số, có nhãn, chấm đều"]  # noqa: SLF001


@pytest.mark.parametrize("truc", tu_hoc.TRUC_BAO_BI)
def test_truc_bao_bi_co_trong_truc(truc):
    assert truc in tu_hoc.TRUC
