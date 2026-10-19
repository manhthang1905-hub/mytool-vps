"""19/10: banner/logo kênh mới bị chấm HỎNG oan (trang công khai >90s mới đổi ảnh) rồi đặt lại cùng tệp mãi.
Sửa gốc: chờ công khai giãn nhịp; quá thì CHỜ lượt sau (không đặt lại); đạt = Studio có ảnh + công khai có ảnh + lần đặt cuối
đúng tệp này (sha lúc đặt). Không Chrome, không mạng."""

from __future__ import annotations

import sys
import types
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
for _p in (str(GOC), str(GOC / "vm")):
    if _p not in sys.path:
        sys.path.append(_p)

import thiet_lap_kenh_dom as t  # noqa: E402

NOW = 1_800_000_000.0
HASH = {"logo": "h1", "banner": "h2", "hinh_mo": "h3"}
HS = {"ten": "テスト", "handle": "@x", "mo_ta": "x", "logo": "logo.png", "banner": "banner.png", "hinh_mo": "wm.png"}


def _ht(banner_co=True, cong_khai=None):
    ht = {"anh": {"logo": True, "banner": banner_co, "hinh_mo": True}}
    if cong_khai is not None:
        ht["cong_khai"] = cong_khai
    return ht


def _so_vua_dat(truoc_banner=""):
    so = t.so_moi("K")
    so["hash_anh"] = dict(HASH)
    for m in ("logo", "hinh_mo"):
        so["muc"][m] = {"tt": "dat"}
    t.ghi_anh_dat(so, "banner", "h2", NOW, {"logo": "L0", "banner": truoc_banner})
    t.hong_muc(so, "banner", "trang công khai chưa đổi", tt="cho")
    return so


# ── chờ công khai giãn nhịp ─────────────────────────────────────────────────
def test_bang_chung_cho_gian_nhip_toi_vai_phut():
    ngu, lan = [], {"n": 0}

    def doc():
        lan["n"] += 1
        return {"banner": "MOI"} if lan["n"] >= 6 else {"banner": ""}
    r = t.bang_chung_anh_luu({"banner": ""}, ["banner"], doc=doc, ngu=ngu.append)
    assert r["banner"][0] is True
    assert ngu == sorted(ngu) and ngu[0] < ngu[-1]                 # giãn dần
    assert sum(ngu) > 90                                            # chờ quá mốc 90s cũ


def test_bang_chung_dung_dung_han():
    ngu = []
    r = t.bang_chung_anh_luu({"banner": ""}, ["banner"], doc=lambda: {"banner": ""}, ngu=ngu.append)
    assert r["banner"][0] is False and abs(sum(ngu) - t.CHO_CONG_KHAI_GIAY) < 1e-6
    assert 90 < t.CHO_CONG_KHAI_GIAY <= 600


# ── sổ lần đặt ──────────────────────────────────────────────────────────────
def test_ghi_anh_dat_cung_tep_giu_moc_truoc_tang_lan():
    so = t.so_moi("K")
    t.ghi_anh_dat(so, "banner", "h2", NOW, {"banner": ""})
    t.ghi_anh_dat(so, "banner", "h2", NOW + 10, {"banner": "MOI"})       # mốc lần 2 đã là ảnh mới → KHÔNG được ghi đè
    assert so["anh_dat"]["banner"] == {"hash": "h2", "luc": NOW + 10, "truoc": "", "lan": 2}
    t.ghi_anh_dat(so, "banner", "h9", NOW + 20, None)                    # tệp khác: sổ mới, mốc không biết
    assert so["anh_dat"]["banner"] == {"hash": "h9", "luc": NOW + 20, "truoc": None, "lan": 1}
    assert "anh_dat" in t.chuan_so({"kenh": "K"}, "K")                    # sổ cũ thiếu khoá → được điền


def test_can_doc_cong_khai_chi_khi_dang_cho_dung_tep():
    so = _so_vua_dat()
    assert t.can_doc_cong_khai(so, HASH)
    assert not t.can_doc_cong_khai(so, dict(HASH, banner="hX"))
    so["muc"]["banner"] = {"tt": "dat"}
    assert not t.can_doc_cong_khai(so, HASH)
    assert not t.can_doc_cong_khai(t.so_moi("K"), HASH)


# ── lượt sau: xác nhận thay vì đặt lại ─────────────────────────────────────
def test_luot_sau_cong_khai_co_banner_thi_dat_khong_dat_lai():
    so = _so_vua_dat()
    kh = t.khac_biet(HS, _ht(cong_khai={"logo": "L0", "banner": "B1"}), so, HASH, NOW + 600)
    assert kh["banner"]["khac"] is False and kh["banner"].get("xac_nhan")
    ghi = []
    t.ghi_ket_qua_so_sanh(so, kh, HASH, NOW + 600, ghi.append)
    assert so["muc"]["banner"]["tt"] == "dat" and so["hash_anh"]["banner"] == "h2"
    # lượt kế: đường thường (sổ đạt + hash) — không cần đọc công khai nữa
    assert not t.can_doc_cong_khai(so, HASH)
    assert t.khac_biet(HS, _ht(), so, HASH, NOW + 7200)["banner"]["khac"] is False


def test_cong_khai_chua_cap_nhat_thi_cho_khong_dat_lai():
    so = _so_vua_dat()
    for ck in ({"logo": "L0", "banner": ""}, None):                      # chưa có banner / không đọc được
        kh = t.khac_biet(HS, _ht(cong_khai=ck), so, HASH, NOW + 3600)
        assert kh["banner"]["khac"] is False and kh["banner"]["giu"][0] == "cho"
    t.ghi_ket_qua_so_sanh(so, kh, HASH, NOW + 3600, lambda *_: None)
    assert so["muc"]["banner"]["tt"] == "cho"
    assert t.tinh_trang(so)[0] == "dang_lam"                              # không phải «hỏng»


def test_cong_khai_van_anh_cu_khong_tinh_dat():
    so = t.so_moi("K")
    t.ghi_anh_dat(so, "logo", "h1", NOW, {"logo": "L0", "banner": ""})
    x, _ = t.xet_anh_da_dat(so, "logo", "h1", True, {"logo": "L0"}, NOW + 60)
    assert x == "cho"
    assert t.xet_anh_da_dat(so, "logo", "h1", True, {"logo": "L1"}, NOW + 60)[0] == "dat"


def test_qua_han_dat_lai_toi_da_mot_lan_roi_hong():
    so = _so_vua_dat()
    tre = NOW + (t.HAN_CHO_CONG_KHAI_GIO + 1) * 3600
    kh = t.khac_biet(HS, _ht(cong_khai={"banner": ""}), so, HASH, tre)
    assert kh["banner"]["khac"] is True                                   # 1 lần đặt lại
    t.ghi_anh_dat(so, "banner", "h2", tre, {"banner": ""})
    assert so["anh_dat"]["banner"]["lan"] == t.TOI_DA_DAT_ANH
    kh = t.khac_biet(HS, _ht(cong_khai={"banner": ""}), so, HASH, tre + (t.HAN_CHO_CONG_KHAI_GIO + 1) * 3600)
    assert kh["banner"]["khac"] is False and kh["banner"]["giu"][0] == "hong"   # hết lượt: báo, KHÔNG đặt lại nữa


def test_studio_mat_anh_dat_lai_co_gioi_han():
    so = _so_vua_dat()
    assert t.xet_anh_da_dat(so, "banner", "h2", False, {"banner": "B1"}, NOW + 60)[0] == "dat_lai"
    so["anh_dat"]["banner"]["lan"] = t.TOI_DA_DAT_ANH
    assert t.xet_anh_da_dat(so, "banner", "h2", False, {"banner": "B1"}, NOW + 60)[0] == "hong"


def test_tep_khac_thi_dat_binh_thuong():
    so = _so_vua_dat()
    kh = t.khac_biet(HS, _ht(cong_khai={"banner": "B1"}), so, dict(HASH, banner="hMOI"), NOW + 60)
    assert kh["banner"]["khac"] is True and not kh["banner"].get("giu")


# ── trong phiên: Xuất bản xong, công khai chậm → CHỜ (không HỎNG) ────────────
class _GiaStudio(t.Studio):
    def __init__(self, banner_co=True):
        super().__init__(types.SimpleNamespace(), lambda *_: None, "x", ngu=lambda s: None)
        self.uc, self.banner_co = "UCxxx", banner_co

    def mo(self, *a, **k): pass
    def doi_hien(self, *a, **k): return True
    def chup(self, *a, **k): pass
    def js(self, bt): return {}
    def huy_thay_doi(self, ghi=None): pass
    def nhap(self, *a, **k): pass
    def dat_tep(self, *a, **k): pass
    def xong_hop_cat(self, *a, **k): pass
    def bam(self, *a, **k): pass
    def xu_ly_sau_xuat_ban(self, ghi, han=40.0): return ""

    def doc_ho_so(self):
        return {"ten": "テスト", "handle": "@x", "mo_ta": "x", "logo": {"co": True}, "banner": {"co": self.banner_co},
                "hinh_mo": {"co": True}}


def _gia(monkeypatch, cong_khai):
    class TL:
        @staticmethod
        def thu_muc_thiet_lap(*a, **k): return "x"
        @staticmethod
        def duong_anh(hs, muc, tm): return __file__
    monkeypatch.setattr(t, "_tl", lambda: TL)
    monkeypatch.setattr(t, "luu_so", lambda so: None)
    monkeypatch.setattr(t, "doc_anh_cong_khai", lambda uc, mo_url=None: dict(cong_khai))
    monkeypatch.setattr(t, "_hash_anh", lambda hs, tm: {m: t.sha_tep(__file__) for m in ("logo", "banner", "hinh_mo")})


def _kh_banner():
    kh = {m: {"khac": False, "hien": "", "mong": ""} for m in t.MUC}
    kh["banner"] = {"khac": True, "hien": "chưa có ảnh", "mong": "banner.png"}
    return kh


def test_phien_dau_cong_khai_cham_thi_cho_va_ghi_so_dat(monkeypatch):
    _gia(monkeypatch, {"logo": "L0", "banner": ""})                       # công khai mãi chưa có banner
    so = t.so_moi("K")
    so["uc"] = "UCxxx"
    S, kh = _GiaStudio(), _kh_banner()
    kq = S.sua_ho_so(HS, kh, so, {"ten": "テスト", "handle": "@x"}, NOW, lambda *_: None)
    assert so["anh_dat"]["banner"]["hash"] == t.sha_tep(__file__) and so["anh_dat"]["banner"]["truoc"] == ""
    t._doc_lai_va_ghi(S, "ho_so", ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo"), HS, kh, kq, so, NOW, lambda *_: None)
    assert so["muc"]["banner"]["tt"] == "cho" and "không đặt lại" in so["muc"]["banner"]["ly_do"]
    # lượt sau: công khai đã có banner → ĐẠT mà không đặt lại
    hh = {m: t.sha_tep(__file__) for m in ("logo", "banner", "hinh_mo")}
    assert t.can_doc_cong_khai(so, hh)
    kh2 = t.khac_biet(HS, _ht(cong_khai={"logo": "L0", "banner": "B1"}), so, hh, NOW + 900)
    assert kh2["banner"]["khac"] is False and kh2["banner"].get("xac_nhan")


def test_phien_dau_studio_khong_co_anh_van_hong(monkeypatch):
    _gia(monkeypatch, {"logo": "L0", "banner": ""})
    so = t.so_moi("K")
    so["uc"] = "UCxxx"
    S, kh = _GiaStudio(banner_co=False), _kh_banner()
    kq = S.sua_ho_so(HS, kh, so, {"ten": "テスト", "handle": "@x"}, NOW, lambda *_: None)
    t._doc_lai_va_ghi(S, "ho_so", ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo"), HS, kh, kq, so, NOW, lambda *_: None)
    assert so["muc"]["banner"]["tt"] == "hong"
