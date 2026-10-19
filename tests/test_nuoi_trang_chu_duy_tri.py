"""DUY TRÌ trang chủ (19/10/2026) — `vm/nuoi_trang_chu.py` + skill D18 + ô Tự kiểm. Không Chrome, không mạng, không LLM."""

from __future__ import annotations

import datetime as _dt
import inspect
import json
import os
import random
import sys
import time
import types
from pathlib import Path

import pytest

GOC_KHO = Path(__file__).resolve().parent.parent
VM = GOC_KHO / "vm"
for _d in (str(GOC_KHO), str(VM)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import nuoi_trang_chu as n  # noqa: E402


def luc(gio, phut=0, ngay=19):
    return time.mktime((2026, 10, ngay, gio, phut, 0, 0, 0, -1))


def chu(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def muc(t, cd, ng, nn=30, nguon="duy_tri"):
    return {"luc": chu(t), "n": nn, "pct_chu_de": cd, "pct_ngach": ng, "dem": {}, "dat": cd > 90, "nguon": nguon}


def _kenh(goc, k, yaml):
    d = Path(goc) / "CHANNEL" / k
    d.mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text(yaml, encoding="utf-8")


# ── công tắc chủ (kenh.yaml) ────────────────────────────────────────────────
def test_cong_tac_chu_la_cong_tac_tong(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A", "nuoi_trang_chu: true\n")
    _kenh(g, "B", "nuoi_trang_chu: false\n")
    _kenh(g, "C", "nuoi_trang_chu: false\n")
    _kenh(g, "D", "nuoi_trang_chu: true\nduy_tri_trang_chu: false\n")
    assert n.cong_tac("A", g, {}) == "bat"
    assert n.cong_tac("B", g, {"da_tat_yaml": "x/kenh.yaml"}) == "may_tat"      # false do CHÍNH máy ghi lúc đạt
    assert n.cong_tac("C", g, {}) == "chu_tat"                                  # false do chủ đặt
    assert n.cong_tac("D", g, {}) == "tat_han"
    assert n.cong_tac("Z", g, {}) == "khong_co"
    assert n.duoc_nuoi_lai("bat") and n.duoc_nuoi_lai("may_tat") and not n.duoc_nuoi_lai("chu_tat")
    # 19/10: `true   # ghi chú` của chủ vẫn là BẬT (bản trước so cả phần chú thích → đọc thành tắt)
    _kenh(g, "E", "nuoi_trang_chu: true   # 19/10: chu cho tu nuoi lai\n")
    assert n.cong_tac("E", g, {}) == "bat" and "E" in n.cac_kenh_bat(g)


def test_khong_ghi_kenh_yaml_nua(tmp_path, monkeypatch):
    """Đạt lần đầu → sổ máy chuyển duy trì; kenh.yaml (công tắc chủ) không bị máy ghi."""
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path))
    monkeypatch.setattr(n, "ghi_nao", lambda *a, **k: None)
    assert "tat_nuoi(" not in inspect.getsource(n.chay_phien)
    so = n.so_moi("K")
    n.ghi_lan_do(so, muc(luc(12), 93.3, 20), chu(luc(12)), nguon="phien")
    assert so["trang_thai"] == "dat"
    dt, sk = n.sau_lan_do("K", so, n.duy_tri_moi("K"), "bat", lambda s: None, che="nuoi_dau")
    assert sk == "dat_lan_dau" and dt["che_do"] == "duy_tri"
    assert n.doc_duy_tri("K")["che_do"] == "duy_tri"


# ── luật % ngách ────────────────────────────────────────────────────────────
def test_luat_ngach_tut_theo_muc_tot_nhat_cua_chinh_kenh():
    t0 = luc(12, ngay=4)
    cu = [muc(t0, 100, 56.7)]
    bay = luc(12)
    assert n.danh_gia_do(muc(bay, 96, 26.7), cu, bay)["ngach_tut"]           # < 0,6×56,7 và < 30
    assert not n.danh_gia_do(muc(bay, 96, 33.3), cu, bay)["ngach_tut"]       # ≥ 30% thì không tụt
    cu2 = [muc(t0, 93, 16.7)]
    assert n.danh_gia_do(muc(bay, 96, 6.7), cu2, bay)["ngach_tut"]           # hụt 10 điểm
    assert not n.danh_gia_do(muc(bay, 96, 10.0), cu2, bay)["ngach_tut"]      # hụt 6,7 điểm = nhiễu 2 ô
    assert not n.danh_gia_do(muc(bay, 96, 0.0), [], bay)["ngach_tut"]        # chưa có mức tốt nhất
    # mức tốt nhất chỉ tính 90 ngày gần đây
    rat_cu = [muc(t0 - 100 * 86400, 100, 80)]
    assert n.ngach_tot(rat_cu, bay) == 0.0
    # khoẻ lại có trễ: ≥ 0,75×tốt nhất hoặc ≥ 30
    assert not n.danh_gia_do(muc(bay, 96, 12.0), cu2, bay)["ngach_khoe"] and n.danh_gia_do(muc(bay, 96, 13.3), cu2, bay)["ngach_khoe"]
    dg = n.danh_gia_do(muc(bay, 96, 26.7), cu, bay)
    assert not dg["dat"] and "ngách tụt" in dg["ly_do"]


# ── dưới mục tiêu → nuôi lại; 2 lần đạt liền → về duy trì ───────────────────
def test_duoi_90_bat_nuoi_lai_trong_so_may():
    dt, sk = n.cap_nhat_duy_tri(n.duy_tri_moi("K"), muc(luc(10), 86.7, 30), [], luc(10))
    assert sk == "duoi_muc" and dt["che_do"] == "nuoi_lai" and dt["tu_luc"] == luc(10) and dt["phien_nuoi_lai"] == 0
    dt2, sk2 = n.cap_nhat_duy_tri(n.duy_tri_moi("K"), muc(luc(10), 90.0, 30), [], luc(10))
    assert sk2 == "" and dt2["che_do"] == "duy_tri"                          # đúng 90% = đạt (dưới 90 mới nuôi lại)


def test_hai_lan_dat_lien_moi_ve_duy_tri():
    dt = dict(n.duy_tri_moi("K"), che_do="nuoi_lai", tu_luc=luc(8))
    dt, sk = n.cap_nhat_duy_tri(dt, muc(luc(10), 93.3, 30), [], luc(10))
    assert dt["che_do"] == "nuoi_lai" and dt["dat_lien"] == 1 and sk == ""
    dt, sk = n.cap_nhat_duy_tri(dt, muc(luc(11), 96.7, 30), [], luc(11))     # cùng phiên (< 3 giờ): không tính thêm
    assert dt["che_do"] == "nuoi_lai" and dt["dat_lien"] == 1
    dt, sk = n.cap_nhat_duy_tri(dt, muc(luc(12), 80.0, 30), [], luc(12))     # trượt giữa chừng: đếm lại
    assert dt["dat_lien"] == 0
    dt, _ = n.cap_nhat_duy_tri(dt, muc(luc(13), 93.3, 30), [], luc(13))
    dt, sk = n.cap_nhat_duy_tri(dt, muc(luc(16), 93.3, 30), [], luc(16))
    assert sk == "ve_duy_tri" and dt["che_do"] == "duy_tri" and not dt["cham"] and not dt["bao_dong"]
    # chủ đề đạt mà ngách chưa khoẻ → chưa về
    dt = dict(n.duy_tri_moi("K"), che_do="nuoi_lai", tu_luc=luc(8))
    cu = [muc(luc(8, ngay=4), 100, 40.0)]
    for gio in (10, 14, 18):                                                  # 26,7%: không tụt (≥ 0,6×40) mà chưa khoẻ
        dt, sk = n.cap_nhat_duy_tri(dt, muc(luc(gio), 96.7, 26.7), cu, luc(gio))
    assert dt["che_do"] == "nuoi_lai" and "ngách chưa khoẻ" in dt["ly_do"]


def test_quyet_dinh_cho_kenh_da_dat_nuoi_lai_va_nhip_cham():
    so = n.so_moi("K")
    so.update(trang_thai="dat")
    assert n.quyet_dinh(so, luc(12))[0] == 0
    assert n.quyet_dinh(so, luc(12), dt={"che_do": "nuoi_lai"}) == (15, "")
    so["phien"] = [{"ngay": "2026-10-19", "so_video": 15}, {"ngay": "2026-10-19", "so_video": 5}]
    so_v, ly = n.quyet_dinh(so, luc(20), dt={"che_do": "nuoi_lai", "cham": True})
    assert so_v == 0 and "20" in ly
    assert n.quyet_dinh(so, luc(20), dt={"che_do": "nuoi_lai"})[0] == 15
    for s in range(50):
        assert 60 * 60 <= n.nghi_giua_phien(random.Random(s), cham=True) <= 120 * 60


# ── báo động sau 7 ngày, một lần, nuôi chậm, không dừng ─────────────────────
def test_bao_dong_mot_lan_sau_7_ngay(tmp_path, monkeypatch):
    t0 = luc(10, ngay=10)
    dt = dict(n.duy_tri_moi("K"), che_do="nuoi_lai", tu_luc=t0, phien_nuoi_lai=8)
    assert n.can_bao_dong(dt, t0 + 6.9 * 86400) == ""
    assert n.can_bao_dong(dt, t0 + 7 * 86400) == "khong_hieu_qua"
    assert n.can_bao_dong(dict(dt, phien_nuoi_lai=3), t0 + 7 * 86400) == ""
    assert n.can_bao_dong(dict(dt, phien_nuoi_lai=3), t0 + 10 * 86400) == "it_phien"
    assert n.can_bao_dong(dt, t0 + 7 * 86400, "chu_tat") == ""              # chủ tắt nuôi: đã hỏi chủ, không báo động
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path))
    monkeypatch.setattr(n, "ghi_nao", lambda *a, **k: None)
    gui = []
    from core import bao_dong
    monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: gui.append((a, k)) or True)
    so = {"lan_do": [dict(muc(t0, 70.0, 10), vi_du_lac_de=["X — món ăn ngon", "Y — tin bóng đá"])]}
    n.bao_dong_duy_tri("K", so, dt, "khong_hieu_qua", lambda s: None)
    assert len(gui) == 1 and "món ăn ngon" in gui[0][0][2] and gui[0][1]["kenh"] == "K"
    dt2 = n.doc_duy_tri("K")
    assert dt2["cham"] is True and dt2["bao_dong"].startswith("khong_hieu_qua@") and dt2["che_do"] == "nuoi_lai"
    assert n.can_bao_dong(dt2, t0 + 30 * 86400) == ""                        # đã báo đợt này → không báo lại


def test_sau_lan_do_bao_dong_khi_qua_han(tmp_path, monkeypatch):
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path))
    monkeypatch.setattr(n, "ghi_nao", lambda *a, **k: None)
    bao = []
    monkeypatch.setattr(n, "bao_dong_duy_tri", lambda k, so, dt, loai, ghi: bao.append(loai))
    t0 = time.time() - 8 * 86400
    so = n.so_moi("K")
    so.update(trang_thai="dat")
    n.ghi_lan_do(so, muc(time.time(), 80.0, 20), chu(time.time()))
    dt = dict(n.duy_tri_moi("K"), che_do="nuoi_lai", tu_luc=t0, phien_nuoi_lai=9)
    dt, sk = n.sau_lan_do("K", so, dt, "may_tat", lambda s: None)
    assert bao == ["khong_hieu_qua"] and dt["che_do"] == "nuoi_lai"


# ── agent: kênh máy tự nuôi lại vào lượt, kênh chủ tắt thì không ───────────
def test_kenh_den_luot_nuoi_lai_ton_trong_cong_tac_chu(tmp_path, monkeypatch):
    goc = tmp_path / "MyTool"
    for k in ("A", "B"):
        _kenh(str(goc), k, "nuoi_trang_chu: false\n")
        (tmp_path / k).mkdir()
        (tmp_path / k / (k + ".exe")).write_text("x")
    so_dir = tmp_path / "so"
    so_dir.mkdir()
    monkeypatch.setattr(n, "THU_MUC_SO", str(so_dir))
    monkeypatch.setattr(n, "cac_kenh_dang_nuoi", lambda thu_muc=None: [])
    (so_dir / "A.json").write_text(json.dumps({"kenh": "A", "trang_thai": "dat", "da_tat_yaml": "x"}), encoding="utf-8")
    (so_dir / "B.json").write_text(json.dumps({"kenh": "B", "trang_thai": "dat"}), encoding="utf-8")
    for k in ("A", "B"):
        (so_dir / (k + ".duy-tri.json")).write_text(json.dumps({"kenh": k, "che_do": "nuoi_lai"}), encoding="utf-8")
    ra, ly = n.kenh_den_luot(luc(12), (), str(goc), ram=40.0, nang_ban=False)
    assert ra == ["A"] and "chủ đang tắt" in ly["B"]
    (so_dir / "A.duy-tri.json").write_text(json.dumps({"kenh": "A", "che_do": "duy_tri"}), encoding="utf-8")
    ra, ly = n.kenh_den_luot(luc(12), (), str(goc), ram=40.0, nang_ban=False)
    assert ra == []                                                          # về duy trì: agent không mở phiên nuôi


def test_main_khong_chay_phien_khi_chu_tat(tmp_path, monkeypatch):
    goc = tmp_path / "MyTool"
    _kenh(str(goc), "B", "nuoi_trang_chu: false\n")
    so_dir = tmp_path / "so"
    so_dir.mkdir()
    monkeypatch.setattr(n, "THU_MUC_SO", str(so_dir))
    monkeypatch.setattr(n, "GOC_TOOL", str(goc))
    (so_dir / "B.duy-tri.json").write_text(json.dumps({"kenh": "B", "che_do": "nuoi_lai"}), encoding="utf-8")
    goc_y = n.doc_kenh_yaml
    monkeypatch.setattr(n, "doc_kenh_yaml", lambda k, g=str(goc): goc_y(k, str(goc)))
    monkeypatch.setattr(n, "chay_phien", lambda *a, **k: pytest.fail("không được mở phiên nuôi"))
    assert n.main(["--kenh", "B"]) == n.MA_KHONG_CAN
    (so_dir / "B.json").write_text(json.dumps({"kenh": "B", "trang_thai": "dat", "da_tat_yaml": "x"}), encoding="utf-8")
    monkeypatch.setattr(n, "chay_phien", lambda *a, **k: 0)
    assert n.main(["--kenh", "B"]) == 0                                      # false do máy ghi + nuôi lại → chạy


# ── nhường: đo-không-xem hoãn đúng luật ─────────────────────────────────────
class _Agent:
    def __init__(self, khoa=True):
        self.khoa, self.da_nha = khoa, 0

    def giu_khoa_may_chung(self, **kw):
        self.kw = kw
        return self.khoa

    def nha_khoa_may_chung(self):
        self.da_nha += 1


def _do_gia(tmp_path, monkeypatch, ly_do="", khoa=True, chrome=""):
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path))
    monkeypatch.setattr(n, "cong_tac", lambda k, g=None, so=None: "may_tat")
    monkeypatch.setattr(n, "khe_nang_ban", lambda goc_tool=None: False)
    ag = _Agent(khoa)
    monkeypatch.setattr(n, "_nap_agent", lambda ghi: ag)
    tl = types.SimpleNamespace(_cfg_kenh=lambda a, k: {}, _nap_cdp=lambda: (types.SimpleNamespace(), None))
    smd = types.SimpleNamespace(tl=tl, ly_do_hoan=lambda *a: ly_do, UU_TIEN_KHOA=3, chrome_dang_mo=lambda *a: chrome)
    monkeypatch.setitem(sys.modules, "studio_may_dom", smd)
    return ag


def test_do_nhuong_khung_cam_viec_dang_va_khoa_may(tmp_path, monkeypatch):
    dong = []
    ag = _do_gia(tmp_path, monkeypatch, ly_do="khung cấm 02:00–07:00 (QUÉT NGÀY)")
    assert n.chay_do("K", dong.append) == n.MA_HOAN and any("khung cấm" in x for x in dong)
    ag = _do_gia(tmp_path, monkeypatch, ly_do="nhường: kênh K có gói chờ tải lên")
    assert n.chay_do("K", dong.append) == n.MA_HOAN
    ag = _do_gia(tmp_path, monkeypatch, khoa=False)                         # .khoa-may bận (tải lên / dựng)
    assert n.chay_do("K", dong.append) == n.MA_HOAN and ag.kw["viec"] == "trang_chu_do" and ag.kw["uu_tien"] == 3
    assert not (tmp_path / "K.khoa").exists()
    ag = _do_gia(tmp_path, monkeypatch, chrome="Chrome kênh K đang chạy — việc khác đang dùng")
    assert n.chay_do("K", dong.append) == n.MA_HOAN and ag.da_nha == 1      # đã nhả khoá máy
    assert not (tmp_path / "K.khoa").exists()                               # và khoá Chrome kênh
    _do_gia(tmp_path, monkeypatch)
    monkeypatch.setattr(n, "cac_kenh_dang_nuoi", lambda thu_muc=None: ["K"])
    assert n.chay_do("K", dong.append) == n.MA_HOAN                         # đang có phiên nuôi: phiên tự đo
    monkeypatch.setattr(n, "cong_tac", lambda k, g=None, so=None: "tat_han")
    assert n.chay_do("K", dong.append) == n.MA_KHONG_CAN


def test_khoa_tach_thu_muc(tmp_path, monkeypatch):
    so_dir, khoa_dir = tmp_path / "so", tmp_path / "khoa"
    so_dir.mkdir()
    khoa_dir.mkdir()
    monkeypatch.setattr(n, "THU_MUC_SO", str(so_dir))
    monkeypatch.setattr(n, "THU_MUC_KHOA", str(khoa_dir))
    assert n.giu_khoa("K") and (khoa_dir / "K.khoa").exists() and n.cac_kenh_dang_nuoi() == ["K"]
    (khoa_dir / "K.dung").write_text("1")
    assert n.co_dung("K")
    n.nha_khoa("K")
    n.xoa_co_dung("K")
    assert not list(khoa_dir.iterdir())


# ── thước đo: quảng cáo / Mix, 2 lần đọc, ổn định nhãn ──────────────────────
def test_loc_o_quang_cao_va_mix():
    o = [{"id": "a" * 11, "loai": "video", "tieu_de": "t"}, {"id": "b" * 11, "loai": "quang_cao"},
         {"id": "c" * 11, "loai": "mix"}, {"id": "d" * 11, "tieu_de": "cũ không có loai"}, {"id": "", "loai": "video"}]
    ra, bo = n.loc_o_do(o)
    assert [x["id"] for x in ra] == ["a" * 11, "d" * 11] and bo == {"quang_cao": 1, "mix": 1}
    assert "list|start_radio" in n._JS_O and "quang_cao" in n._JS_O and "/watch?v=" in n._JS_O   # Shorts (/shorts/) không đọc


def test_o_chua_nap_tieu_de_khong_bi_coi_la_khac_ngon_ngu():
    """19/10: ô tiêu đề rỗng từng bị luật mã coi là 'khác ngôn ngữ' → lạc đề → bấm Không quan tâm mù."""
    assert not n.sai_ngon_ngu("", "ja") and not n.sai_ngon_ngu("  ", "ja")
    assert not n.chac_lac_de({"id": "e" * 11, "tieu_de": ""}, {})
    ra, bo = n.loc_o_do([{"id": "e" * 11, "loai": "video", "tieu_de": ""}, {"id": "f" * 11, "loai": "video", "tieu_de": "心理"}])
    assert [x["id"] for x in ra] == ["f" * 11] and bo == {"khong_ten": 1}


def _goi_gia(theo_luot):
    """LLM giả: lượt thứ i trả nhãn theo `theo_luot[i](so_thu_tu_o)`; ghi số ô mỗi lượt."""
    dem = {"luot": 0, "o": []}

    def goi(prompt):
        dong = [d for d in prompt.splitlines() if d[:1].isdigit() and "|" in d]
        f = theo_luot[min(dem["luot"], len(theo_luot) - 1)]
        dem["luot"] += 1
        dem["o"].append(len(dong))
        return json.dumps([{"i": j + 1, "nhan": f(int(d.split("|")[2][1:])), "tam_ly": True} for j, d in enumerate(dong)])
    return goi, dem


def test_phan_loai_bau_hai_luot_va_phan_xu():
    o = [{"id": "v%010d" % i, "tieu_de": "心理の話%d" % i, "kenh": "k%d" % i} for i in range(6)]
    l1 = lambda i: "dung_ngach" if i < 3 else "dung_chu_de"
    l2 = lambda i: "dung_ngach" if i < 2 else ("lac_de" if i == 5 else "dung_chu_de")   # ô 2 và ô 5 lệch
    l3 = lambda i: "dung_chu_de" if i == 2 else "lac_de"                                   # phân xử: ô 2 → chủ đề, ô 5 → lạc đề
    goi, dem = _goi_gia([l1, l2, l3])
    cache = {}
    nl, od = n.phan_loai_bau(goi, "ngách", o, cache)
    assert dem["o"] == [6, 6, 2]                                              # lượt 3 chỉ cho ô lệch
    assert od["n"] == 6 and od["khop"] == round(4 / 6, 3) and len(od["lech"]) == 2
    assert [nl["v%010d" % i] for i in range(6)] == ["dung_ngach", "dung_ngach", "dung_chu_de", "dung_chu_de", "dung_chu_de", "lac_de"]
    assert cache["v0000000005"] == "lac_de" and cache["tl:v0000000005"] is True
    goi2, dem2 = _goi_gia([l1])
    nl2, od2 = n.phan_loai_bau(goi2, "ngách", o, cache)                       # đã cache: không gọi LLM
    assert dem2["luot"] == 0 and nl2 == nl and od2["n"] == 0
    goi3, dem3 = _goi_gia([l1, l1])
    _nl3, od3 = n.phan_loai_bau(goi3, "ngách", o, cache, bo_cache=True)       # kiểm thước: phân loại lại mọi ô
    assert dem3["o"] == [6, 6] and od3["khop"] == 1.0


def test_gop_hai_lan_doc_va_do_khop_nhan():
    o1 = [{"id": "v%02d" % i, "kenh": "k", "tieu_de": "t%d" % i} for i in range(30)]
    o2 = [{"id": "v%02d" % i, "kenh": "k", "tieu_de": "t%d" % i} for i in range(10, 40)]
    nl = {"v%02d" % i: ("lac_de" if i in (1, 2, 35) else ("dung_ngach" if i % 3 == 0 else "dung_chu_de")) for i in range(40)}
    k = n.gop_hai_lan(o1, nl, o2, nl)
    assert k["n"] == 40 and k["pct_chu_de"] == 92.5 and k["doc"][0]["pct_chu_de"] == 93.3 and k["doc"][1]["pct_chu_de"] == 96.7
    assert k["chenh_chu_de"] == 3.4 and k["trung_o"] == 0.5 and len(k["vi_du_lac_de"]) == 3
    a = {"x": "dung_ngach", "y": "lac_de", "z": "dung_chu_de"}
    b = {"x": "dung_chu_de", "y": "lac_de", "z": "dung_chu_de", "w": "lac_de"}
    r = n.do_khop_nhan(a, b)
    assert r["n"] == 3 and r["khop"] == round(2 / 3, 3) and r["lech"] == [("x", "dung_ngach", "dung_chu_de")]
    so = n.so_moi("K")
    n.ghi_lan_do(so, dict(k, bo_qua={"mix": 2}, hl="ja"), "2026-10-19 12:00", nguon="duy_tri")
    m = so["lan_do"][-1]
    assert m["nguon"] == "duy_tri" and m["chenh_chu_de"] == 3.4 and m["bo_qua"] == {"mix": 2} and m["hl"] == "ja"


# ── nghiêng ngách hẹp khi nuôi lại ──────────────────────────────────────────
def test_nguon_ngach_hep_va_uu_tien(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A", 'nhom: "n1"\ntep: "t1"\n')
    _kenh(g, "B", 'nhom: "n1"\ntep: "t1"\n')
    _kenh(g, "C", 'nhom: "n1"\ntep: "t2"\n')
    nc = tmp_path / "CHANNEL" / "A" / "nghien-cuu"
    nc.mkdir()
    (nc / "danh-sach-chon.json").write_text(json.dumps({"moi": [{"link": "https://www.youtube.com/watch?v=" + "M" * 11}]}),
                                            encoding="utf-8")
    giu = tmp_path / "CHANNEL" / "_NHOM" / "n1" / "nghien-cuu" / "giu-nguon"
    giu.mkdir(parents=True)
    for ma, k, luot in (("W" * 11, "A", "0002"), ("O" * 11, "A", "0001"), ("S" * 11, "B", "0009"), ("X" * 11, "C", "0003")):
        (giu / (ma + ".json")).write_text(json.dumps({"ma": ma, "kenh": k, "ma_luot": luot}), encoding="utf-8")
    bang = tmp_path / "CHANNEL" / "_NHOM" / "n1" / "bang-nhom.csv"
    bang.write_text("Kênh,Mã video,Lượt xem\nA,v1,50\nA,v2,5000\nA,v3,90\n", encoding="utf-8")
    kh = tmp_path / "CHANNEL" / "A" / "ke-hoach-dang"
    kh.mkdir()
    (kh / "ke-hoach.csv").write_text("Mã gói,Video ID\nA-0001,v1\nA-0002,v2\n", encoding="utf-8")
    hep = n.nguon_ngach_hep("A", g)
    assert hep == {"M" * 11: 3, "W" * 11: 4, "O" * 11: 3, "S" * 11: 2}     # C khác tệp: không lấy
    # chon_video: nguồn ngách hẹp vượt video nhiều view hơn
    hom = _dt.date(2026, 10, 19)
    uv = [{"id": "%011d" % i, "tieu_de": "t", "kenh": "K%d" % i, "view": 200_000, "ngay": hom - _dt.timedelta(days=5), "dai": 600,
           "ngach": True} for i in range(20)]
    uv.append({"id": "W" * 11, "tieu_de": "t", "kenh": "KW", "view": 60_000, "ngay": hom - _dt.timedelta(days=5), "dai": 600,
               "ngach": True, "uu_tien": 4})
    def dem(ds):
        return sum(any(v["id"] == "W" * 11 for v in n.chon_video(ds, (), (), (), 3, hom, random.Random(s))) for s in range(40))
    assert dem(uv) >= 12                                                     # vào nhóm mạnh nhất (xáo trong top 2×)
    assert dem([dict(v, uu_tien=1) for v in uv]) == 0                        # không ưu tiên: view thấp nhất, không bao giờ lọt


# ── tóm tắt cho 8790 / Tự kiểm / skill D18 ──────────────────────────────────
def test_tom_tat_va_o_tu_kiem(tmp_path):
    g = str(tmp_path)
    thu = tmp_path / "vm" / "logs" / "nuoi-trang-chu"
    thu.mkdir(parents=True)
    _kenh(g, "A", "nuoi_trang_chu: false\n")
    _kenh(g, "B", "nuoi_trang_chu: false\n")
    _kenh(g, "C", "nuoi_trang_chu: false\n")
    bay = time.time()
    (thu / "A.json").write_text(json.dumps({"kenh": "A", "trang_thai": "dat", "da_tat_yaml": "x",
                                            "lan_do": [muc(bay - 3600, 96.7, 40)]}), encoding="utf-8")
    (thu / "B.json").write_text(json.dumps({"kenh": "B", "trang_thai": "dat", "da_tat_yaml": "x",
                                            "lan_do": [muc(bay - 3600, 80.0, 20)]}), encoding="utf-8")
    (thu / "B.duy-tri.json").write_text(json.dumps({"kenh": "B", "che_do": "nuoi_lai", "tu_luc": bay - 2 * 86400,
                                                    "phien_nuoi_lai": 4}), encoding="utf-8")
    (thu / "C.json").write_text(json.dumps({"kenh": "C", "trang_thai": "dang_nuoi", "lan_do": [muc(bay - 3600, 70.0, 10)]}),
                                encoding="utf-8")
    (thu / "C.duy-tri.json").write_text(json.dumps({"kenh": "C", "che_do": "nuoi_lai", "tu_luc": bay - 3600}), encoding="utf-8")
    ta, tb, tc = (n.tom_tat_duy_tri(k, g, bay) for k in "ABC")
    assert ta["tt"] == "dat" and not ta["den_han"]
    assert tb["tt"] == "thu_lai" and "4 phiên" in tb["cau"]
    assert tc["tt"] == "nguoi" and "chủ đang tắt" in tc["cau"]
    from core import tu_kiem as tk
    K = tk.BoiCanh(g, bay=_dt.datetime.fromtimestamp(bay), tai=lambda u: (-1, b""), kenh_ds=["A", "B", "C", "Z"], so={})
    ds = {m["kenh"]: m for m in tk.kiem_trang_chu(K)}
    assert set(ds) == {"A", "B", "C"}
    assert ds["A"]["tt"] == tk.DAT and ds["B"]["tt"] == tk.THU_LAI and ds["C"]["tt"] == tk.CHO and ds["C"]["nguoi"]
    assert "nuoi_trang_chu: true" in ds["C"]["can_lam"]
    # skill D18
    from core import ky_nang as kn
    assert kn.k_duy_tri_trang_chu(g, "A")[0] == kn.DAT and kn.k_duy_tri_trang_chu(g, "C")[0] == kn.LOI
