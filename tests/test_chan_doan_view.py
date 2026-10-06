"""Chẩn đoán view 07/10/2026 (`workspace/chan-doan/2026-10-07.md`) — ba sửa:

1. `tu_hoc`: kết quả MUỘN (`ket_muon`, hiển thị mốc ≥ 96h so trung vị kênh) thay chỗ 48h làm kết quả chính;
   hai trục ĐO mới `chu_bia_dai`, `mo_dau`.
2. `bien_tap_content._video_cua_minh`: xếp theo số muộn, gắn ★ video thắng của chính kênh.
3. `auto_khau`: khung ký tự chữ bìa 10–20 (viết lại một lượt khi lệch khung).

Dữ liệu giả hoàn toàn (tmp_path), không mạng, không gọi AI thật.
"""

import json
import os
from types import SimpleNamespace

from core import auto_khau, bien_tap_content, tu_hoc


def _kenh(goc, ma, nhom="n1"):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(d, "ho-so-video"), exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('nhom: "{0}"\n'.format(nhom))
    return d


def _ho_so(d, ma_goi, chi_so, **them):
    hs = dict({"ma_goi": ma_goi, "video_id": "vid" + ma_goi[-2:], "tieu_de": "テスト動画 " + ma_goi,
               "chi_so": chi_so}, **them)
    with open(os.path.join(d, "ho-so-video", ma_goi + ".json"), "w", encoding="utf-8") as f:
        json.dump(hs, f, ensure_ascii=False)


def _moc(imp, gio, ctr=5.0):
    return {"impressions": imp, "moc_gio_that": gio, "ctr": ctr, "views": imp // 10}


# ── 1. tu_hoc: kết quả muộn ─────────────────────────────────────────────────

def test_moc_muon_lay_moc_muon_nhat_trong_cua_so():
    hs = {"chi_so": {"48h": _moc(300, 48), "72h": _moc(900, 80), "ngay4": _moc(5000, 107),
                     "ngay5": _moc(5200, 131), "ngay20": _moc(9000, 480), "ngay6": {"impressions": None,
                                                                                   "moc_gio_that": 150}}}
    m = tu_hoc.moc_muon(hs)
    assert m["impressions"] == 5200 and m["moc"] == "ngay5"
    assert tu_hoc.moc_muon({"chi_so": {"48h": _moc(1, 48)}}) == {}
    assert tu_hoc.moc_muon({}) == {}


def test_ket_muon_lat_video_no_muon_thanh_thang(tmp_path):
    """Ca thật (số giả): 48h chỉ 300 hiển thị → 'trượt' theo 48h, nhưng @119h nổ 30.000 → phải là 'thắng'."""
    g = str(tmp_path)
    d = _kenh(g, "A")
    so = [(1500, 55), (200, 50), (120, 60), (300, 30000), (900, 400), (80, 70)]   # (48h, muộn)
    for i, (h48, muon) in enumerate(so):
        _ho_so(d, "A-%02d" % i, {"48h": _moc(h48, 48), "ngay4": _moc(muon, 110)})
    r = tu_hoc.cham_van(g, "A")
    assert r["ket_muon"] == 6
    v = tu_hoc.doc_van(g, "A")
    # trung vị muộn = (60+70)/2 = 65 → 70, 400, 30000 thắng; video 1.500 hiển thị @48h (55 muộn) trượt
    assert v["A-03"]["ket_muon"] == "thang" and v["A-04"]["ket_muon"] == "thang"
    assert v["A-00"]["ket_muon"] == "truot"
    # 48h nói ngược với A-03 (300 @48h): kết quả chính bây giờ là ket_muon, không phải ket48/ket_tv.
    v["A-03"]["ket48"], v["A-03"]["ket_tv"] = "truot", "truot"
    o = tu_hoc._dem({"A-03": dict(v["A-03"], nuoc={"cum": "x"})})["cum"]["x"]
    assert (o["a"], o["b"], o["n"], o["n_tv"]) == (tu_hoc.TRONG_SO_MUON, 0.0, 1, 0)


def test_ket7_van_dung_tren_ket_muon():
    van = {"1": {"nuoc": {"cum": "x"}, "ket7": "truot", "ket_muon": "thang", "ket48": "thang"}}
    o = tu_hoc._dem(van)["cum"]["x"]
    assert (o["a"], o["b"]) == (0.0, tu_hoc.TRONG_SO_7D)


def test_chua_co_ket_muon_thi_giu_duong_48h():
    van = {"1": {"nuoc": {"cum": "x"}, "ket48": "thang", "ket_tv": "truot"}}
    o = tu_hoc._dem(van)["cum"]["x"]
    assert (o["a"], o["b"], o["n_tv"]) == (tu_hoc.TRONG_SO_48H, tu_hoc.TRONG_SO_TV, 1)


def test_ket_muon_can_du_video(tmp_path):
    g = str(tmp_path)
    d = _kenh(g, "A")
    for i in range(tu_hoc.N_TOI_THIEU_TV - 1):
        _ho_so(d, "A-%02d" % i, {"ngay4": _moc(100 * (i + 1), 110)})
    tu_hoc.cham_van(g, "A")
    assert not any("ket_muon" in v for v in tu_hoc.doc_van(g, "A").values())


def test_truc_do_chu_bia_va_mo_dau():
    assert [tu_hoc.nhom_chu_bia(c) for c in ("実は", "「この人、ズレてる」", "「この人、ズレてる」 低IQの人の思考",
                                             "あ" * 25, "")] == ["<10", "<10", "15-20", ">20", ""]
    assert tu_hoc.nhom_chu_bia("年金だけで 暮らせる人") == "10-14"
    hs = lambda g: {"phan": {"danh_sach": [{"so": 1, "giay": g}, {"so": 2, "giay": 100}]}}  # noqa: E731
    assert [tu_hoc.nhom_mo_dau(hs(x)) for x in (50, 75, 200)] == ["<60", "60-90", ">90"]
    assert tu_hoc.nhom_mo_dau({}) == "" and tu_hoc.nhom_mo_dau({"phan": None}) == ""
    assert "chu_bia_dai" in tu_hoc.TRUC and "mo_dau" in tu_hoc.TRUC
    assert "chu_bia_dai" in tu_hoc.TRUC_BAO_BI


def test_cham_van_bu_truc_do_cho_van_cu(tmp_path):
    g = str(tmp_path)
    d = _kenh(g, "A")
    _ho_so(d, "A-01", {"48h": _moc(200, 48)}, chu_bia="実は",
           phan={"danh_sach": [{"so": 1, "giay": 130.0}]})
    tu_hoc.ghi_van(g, "A", "A-01", {"cum": "x", "kieu_tieu_de": "khac"}, {})
    tu_hoc.cham_van(g, "A")
    nuoc = tu_hoc.doc_van(g, "A")["A-01"]["nuoc"]
    assert nuoc["chu_bia_dai"] == "<10" and nuoc["mo_dau"] == ">90" and nuoc["cum"] == "x"


def test_bang_diem_md_co_ket_muon(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    tu_hoc.ghi_van(g, "A", "1", {"cum": "x"}, {})
    v = tu_hoc.doc_van(g, "A")
    v["1"]["ket_muon"] = "thang"
    tu_hoc._luu_van(g, "A", v)
    with open(tu_hoc.ghi_bang_diem_md(g, "A"), encoding="utf-8") as f:
        chu = f.read()
    assert "1 có kết quả muộn" in chu and "| x | 1/1" in chu


# ── 2. biên tập viên đọc số muộn ────────────────────────────────────────────

def test_video_cua_minh_xep_theo_so_muon_va_gan_sao(tmp_path):
    g = str(tmp_path)
    d = _kenh(g, "A")
    _ho_so(d, "A-01", {"48h": _moc(300, 48), "ngay4": _moc(30000, 119)})   # nổ muộn
    _ho_so(d, "A-02", {"48h": _moc(1500, 48), "ngay4": _moc(1600, 110)})
    _ho_so(d, "A-03", {"48h": _moc(100, 48), "ngay4": _moc(150, 110)})
    _ho_so(d, "A-04", {"48h": _moc(90, 48), "ngay4": _moc(120, 110)})
    _ho_so(d, "A-05", {"48h": _moc(50, 48)})                                   # chưa có số muộn
    chu = bien_tap_content._video_cua_minh(g, "A")
    dong = [x for x in chu.splitlines() if x.startswith("- ")]
    assert "A-01" in dong[0] and dong[0].startswith("- ★ ")
    assert "MUỘN 119h: 30.000 hiển thị" in dong[0] and "48h: 300 hiển thị" in dong[0]
    assert "A-05" in dong[-1]
    # trung vị muộn = 875 → ngưỡng ★ = max(1000, 1750): A-02 (1.600) không ★
    assert not any("★" in x for x in dong[1:])
    assert chu.splitlines()[0].startswith("(Xếp theo hiển thị MUỘN")


def test_video_cua_minh_khong_sao_khi_so_nho(tmp_path):
    g = str(tmp_path)
    d = _kenh(g, "A")
    for i, x in enumerate((400, 50, 60, 70)):   # 400 ≥ 2 × trung vị nhưng < sàn 1.000
        _ho_so(d, "A-%02d" % i, {"48h": _moc(x // 2, 48), "ngay4": _moc(x, 110)})
    chu = bien_tap_content._video_cua_minh(g, "A")
    assert "★" not in chu and not chu.startswith("(Xếp")


# ── 3. khung ký tự chữ bìa ──────────────────────────────────────────────────

def test_chu_bia_lech_khung():
    f = auto_khau.chu_bia_lech_khung
    assert f("実は") == "ngan" and f("自分から") == "ngan"
    assert f("「この人、ズレてる」 低IQの人の思考の癖") == ""          # 17 ký tự
    assert f("【心理学】夜中の同じ時間に目覚める人、実は〇〇です。潜在意識が伝える深層心理") == "dai"
    assert f("") == ""
    assert f("Secret", "en") == "" and f("実は", "Japanese") == "ngan"
    assert auto_khau.chu_bia_trong_khung("年金だけで 豊かに暮らす人の習慣")
    assert not auto_khau.chu_bia_trong_khung("年金だけで 豊かに暮らす人の習慣", "en")
    assert not auto_khau.chu_bia_trong_khung("実は")


def _bc_gia(ghi):
    return SimpleNamespace(ghi=ghi.append, kiem_dung=lambda: None)


def _luot_gia():
    return SimpleNamespace(ma_kenh="A", ma_luot="0001")


def test_sua_khung_chu_bia_nhan_ban_moi_trong_khung(tmp_path, monkeypatch):
    nhac = []
    monkeypatch.setattr(auto_khau, "_goi", lambda bc, ln, khoa, **kw: nhac.append((ln, khoa))
                        or "TITLE: x\nTHUMB: 年金だけで 豊かに暮らす人の習慣")
    ghi = []
    d = str(tmp_path / "AUTO" / "A" / "0001")
    os.makedirs(d)
    moi = auto_khau._sua_khung_chu_bia(_bc_gia(ghi), _luot_gia(), SimpleNamespace(ngon_ngu="ja"), d,
                                       "PROMPT GOC", "実は")
    assert moi == "年金だけで 豊かに暮らす人の習慣"
    assert len(nhac) == 1 and nhac[0][0].startswith("PROMPT GOC") and "10–20" in nhac[0][0]
    assert "実は" in nhac[0][0]


def test_sua_khung_chu_bia_giu_ban_cu_khi_ban_moi_hong(tmp_path, monkeypatch):
    d = str(tmp_path / "AUTO" / "A" / "0001")
    os.makedirs(d)
    k = SimpleNamespace(ngon_ngu="ja")
    monkeypatch.setattr(auto_khau, "_goi", lambda *a, **kw: "TITLE: x\nTHUMB: 短い")
    assert auto_khau._sua_khung_chu_bia(_bc_gia([]), _luot_gia(), k, d, "P", "実は") == "実は"

    def hong(*a, **kw):
        raise RuntimeError("cổng rớt")
    monkeypatch.setattr(auto_khau, "_goi", hong)
    assert auto_khau._sua_khung_chu_bia(_bc_gia([]), _luot_gia(), k, d, "P", "実は") == "実は"


def test_kenh_faithful_chu_bia_trong_khung_thi_chot_chu(tmp_path):
    """`8-thumbnail.md` bảo cắt chữ về ≤ 14 ký tự — chữ bìa đã qua khung 10–20 phải được CHỐT nguyên văn, kẻo
    khâu vẽ cắt lại thành mảnh 「実は」. Ngoài khung / ngôn ngữ không đếm ký tự thì giữ nết cũ (không chốt)."""
    from core.auto import LuotChay
    from tests.test_chu_tren_anh_bia import _BC, _JSON_BIA
    from tests.test_chu_tren_anh_bia import _kenh as _kenh_bia

    def gui(chu, **kw):
        bc = _BC(_kenh_bia(che_do_tieu_de="faithful", **kw), _JSON_BIA)
        auto_khau._loi_nhac_bia(bc, LuotChay(ma_kenh="TL4-T7", ma_luot="0009", thu_muc=str(tmp_path)),
                                bc.kenh.prompt["8-thumbnail.md"], "タイトル", chu, list(auto_khau.KIEU_THUMB))
        return bc.loi_nhac_da_gui[0]

    assert "MANDATORY — EXACT THUMBNAIL TEXT" in gui("年金だけで 豊かに暮らす人の習慣")
    assert "MANDATORY" not in gui("実は")
    assert "MANDATORY" not in gui("Quiet people win", ngon_ngu="en")
    assert "COMPETITOR THUMBNAIL LAYOUT" not in gui("年金だけで 豊かに暮らす人の習慣")


def test_sua_khung_chu_bia_khong_goi_khi_trong_khung_hoac_khong_co_loi_nhac(tmp_path, monkeypatch):
    goi = []
    monkeypatch.setattr(auto_khau, "_goi", lambda *a, **kw: goi.append(1) or "")
    k = SimpleNamespace(ngon_ngu="ja")
    d = str(tmp_path)
    assert auto_khau._sua_khung_chu_bia(_bc_gia([]), _luot_gia(), k, d, "P", "年金だけで 豊かに暮らす人") \
        == "年金だけで 豊かに暮らす人"
    assert auto_khau._sua_khung_chu_bia(_bc_gia([]), _luot_gia(), k, d, "  ", "実は") == "実は"
    assert auto_khau._sua_khung_chu_bia(_bc_gia([]), _luot_gia(), SimpleNamespace(ngon_ngu="en"), d, "P",
                                        "Hi") == "Hi"
    assert goi == []
