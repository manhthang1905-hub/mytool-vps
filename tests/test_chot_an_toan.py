"""Bốn chốt an toàn 1 năm: ví, license Windows, hạn thuê VPS, giọng đọc trùng.

KHÔNG rearm thật, KHÔNG gọi mạng, KHÔNG khởi động lại máy: mọi lệnh hệ thống đi
qua seam `chay_lenh`; số dư đi qua seam `lay`. Mọi bài dùng `tmp_path`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

from core import bang_dieu_khien, chot_an_toan, dieu_phoi, gac_tong, su_co, tu_chay, van_vi
from core import ban_quyen_windows as bq

UOC = 20_000.0  # ước 1 video (VND) dùng cho mọi bài


def _lay(vnd):
    return lambda client: {"wallet": str(int(vnd * 1_000_000))}


def _chan(goc, so_du, *, dang_do=False, bay_gio=1_000_000.0, uoc=UOC):
    return van_vi.cho_phep_mo_luot(goc, object(), dang_do=dang_do, uoc_video_vnd=uoc,
                                   bay_gio=bay_gio, lay=_lay(so_du))


# ═══ VÍ ═════════════════════════════════════════════════════════════════════


def test_vi_du_tien_thi_mo_luot(tmp_path):
    duoc, _ly, dg = _chan(str(tmp_path), 100_000)
    assert duoc and dg["muc"] == "ok" and dg["du_video"] == 5


def test_vi_duoi_1_5_lan_1_video_thi_khong_mo_luot_moi(tmp_path):
    goc = str(tmp_path)
    duoc, ly, dg = _chan(goc, 29_000)  # < 20.000 x 1,5 = 30.000
    assert not duoc and "cần nạp" in ly and dg["muc"] == "het"
    assert "Ví sắp hết: còn 29.000₫, đủ khoảng 1 video — cần nạp" in dg["cau"]
    assert van_vi.doc_trang_thai(goc)["chan"] is True


def test_vi_luot_do_van_lam_not_neu_du_1_video(tmp_path):
    goc = str(tmp_path)
    assert _chan(goc, 25_000, dang_do=True)[0] is True     # 25k >= 20k
    assert _chan(goc, 15_000, dang_do=True, bay_gio=2_000_000.0)[0] is False


def test_vi_tu_chay_lai_khi_da_nap_khong_can_ai_bam(tmp_path):
    goc = str(tmp_path)
    assert _chan(goc, 5_000)[0] is False
    # 5 phút sau, đã nạp 200k: đệm số dư hết hạn (bị chặn thì TTL ngắn) → mở lại
    duoc, _ly, _dg = _chan(goc, 200_000, bay_gio=1_000_000.0 + 400)
    assert duoc
    tt = van_vi.doc_trang_thai(goc)
    assert tt["chan"] is False and tt.get("mo_lai_luc")


def test_vi_het_tien_giua_chung_chan_toi_khi_thay_nap(tmp_path):
    goc = str(tmp_path)
    van_vi.ghi_het_tien(goc, "402", so_du_vnd=40_000.0, bay_gio=1_000_000.0)
    # ví vẫn 40k (đủ ngưỡng 30k nhưng chưa nạp thêm) → vẫn chặn
    duoc, ly, _ = _chan(goc, 40_000, bay_gio=1_000_500.0)
    assert not duoc and "chờ nạp tiền" in ly
    # nạp thêm → tự mở, và dấu het_tien được gỡ
    duoc, _ly, _ = _chan(goc, 120_000, bay_gio=1_001_000.0)
    assert duoc
    assert "het_tien" not in van_vi.doc_trang_thai(goc)


def test_vi_khong_doc_duoc_so_du_thi_khong_chan(tmp_path):
    def hong(_client):
        raise RuntimeError("mất mạng")
    duoc, _ly, dg = van_vi.cho_phep_mo_luot(str(tmp_path), object(), uoc_video_vnd=UOC,
                                            bay_gio=5.0, lay=hong)
    assert duoc and dg["muc"] == "khong_ro"


def test_vi_phan_hoi_la_khong_phai_so_thi_khong_chan(tmp_path):
    duoc, _l, dg = van_vi.cho_phep_mo_luot(str(tmp_path), object(), uoc_video_vnd=UOC,
                                           bay_gio=5.0, lay=lambda c: object())
    assert duoc and dg["muc"] == "khong_ro"


def test_vi_canh_bao_som_duoi_3_ngay(tmp_path):
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "workspace", "chi-phi"))
    ngay = (_dt.datetime.fromtimestamp(1_000_000.0) - _dt.timedelta(days=1)).strftime("%Y-%m-%d")
    with open(os.path.join(goc, "workspace", "chi-phi", ngay + ".json"), "w") as tep:
        json.dump({"tong_micro": 100_000 * 1_000_000}, tep)   # 100k₫/ngày
    duoc, _ly, dg = _chan(goc, 150_000)                        # đủ 7 video nhưng chỉ 1,5 ngày
    assert duoc and dg["muc"] == "som"
    assert "Ví còn 150.000₫, máy đang chi khoảng 100.000₫/ngày, đủ khoảng 1,5 ngày" in dg["cau"]
    assert "nên nạp trước ngày" in dg["cau"]


def test_vi_lich_su_toi_da_1_dong_30_phut_va_chi_theo_tut_bo_qua_nap(tmp_path):
    goc = str(tmp_path)
    t0 = 1_000_000.0
    assert van_vi.ghi_lich_su_so_du(goc, 1_000_000, t0) is True
    assert van_vi.ghi_lich_su_so_du(goc, 999_000, t0 + 600) is False          # < 30 phút
    assert van_vi.ghi_lich_su_so_du(goc, 900_000, t0 + 12 * 3600) is True       # tụt 100k / 12h
    assert van_vi.ghi_lich_su_so_du(goc, 2_000_000, t0 + 13 * 3600) is True     # nạp: bỏ qua
    assert van_vi.ghi_lich_su_so_du(goc, 1_900_000, t0 + 24 * 3600) is True     # tụt 100k / 11h
    chi = van_vi.chi_theo_tut_vi(goc, t0 + 24 * 3600)
    assert abs(chi - 200_000) < 1                                               # 200k / 24h
    assert van_vi.chi_theo_tut_vi(goc, t0 + 24 * 3600 + 80 * 3600) is None      # quá cửa sổ 72h


def _so_luot(goc, ma, ngay, so, uoc=100_000):
    d = os.path.join(goc, "CHANNEL", ma, "tu-chay")
    os.makedirs(d, exist_ok=True)
    runs = [{"san_xuat": {"da_chay": True}, "ngan_sach": {"uoc_tinh_vnd": uoc}} for _ in range(so)]
    with open(os.path.join(d, ngay + ".json"), "w", encoding="utf-8") as tep:
        json.dump({"ngay": ngay, "runs": runs}, tep)


def test_chi_ngay_lay_so_lon_nhat_va_khong_theo_so_usage_thap(tmp_path, monkeypatch):
    goc = str(tmp_path)
    mo = _dt.datetime(2026, 10, 1, 12, 0, 0)
    _so_luot(goc, "K1", "2026-10-01", 3)      # 300k hôm nay
    _so_luot(goc, "K1", "2026-09-30", 10)     # 1.000k hôm qua, còn 50% trong 24h => 500k
    os.makedirs(os.path.join(goc, "workspace", "chi-phi"))
    with open(os.path.join(goc, "workspace", "chi-phi", "2026-09-30.json"), "w") as tep:
        json.dump({"tong_micro": 65_000 * 1_000_000}, tep)   # usage thấp: 65k
    from core import tu_chay
    monkeypatch.setattr(tu_chay, "kenh_tu_chay", lambda g: ["K1"])
    monkeypatch.setattr("core.kenh.doc_kenh", lambda g, m: type("K", (), {"nhip_dang": ["1", "2", "3"], "chu_ky_dang_ngay": 1})())
    chi, ct = van_vi.chi_ngay_that(goc, 100_000, mo.timestamp())
    assert abs(ct["luot_24h"] - 800_000) < 1 and ct["du_phong"] == 300_000
    assert chi == 800_000 and ct["chi_phi_7_ngay"] == 65_000


def test_vi_canh_bao_lap_4_gio_khi_con_duoi_1_ngay(tmp_path, monkeypatch):
    monkeypatch.setattr(van_vi, "uoc_mot_video_vnd", lambda g: UOC)
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "workspace", "chi-phi"))
    ngay = (_dt.datetime.fromtimestamp(1_000_000.0) - _dt.timedelta(days=1)).strftime("%Y-%m-%d")
    with open(os.path.join(goc, "workspace", "chi-phi", ngay + ".json"), "w") as tep:
        json.dump({"tong_micro": 100_000 * 1_000_000}, tep)
    r, _ = chot_an_toan.kiem_vi(goc, client=object(), bay_gio=1_000_000.0, lay=_lay(250_000), )
    assert r and r[0]["lap_gio"] == chot_an_toan.LAP_VI_SOM_GIO            # 2,5 ngày
    r, _ = chot_an_toan.kiem_vi(goc, client=object(), bay_gio=1_000_000.0 + 7200, lay=_lay(60_000))
    assert r and r[0]["lap_gio"] == chot_an_toan.LAP_VI_GIO                # 0,6 ngày


def test_vi_su_co_len_giao_dien_qua_gac_tong(tmp_path):
    goc = str(tmp_path)
    r, _so_du = chot_an_toan.kiem_vi(goc, client=object(), bay_gio=1e6, lay=_lay(1_000))
    assert r == []      # tmp không có kênh → không ước được 1 video → không rõ → không báo
    van_vi.ghi_het_tien(goc, "x", so_du_vnd=10.0, bay_gio=1e6)
    r, _ = chot_an_toan.kiem_vi(goc, client=object(), bay_gio=1e6, lay=_lay(10))
    assert any(s["loai"] == "vi_het_tien" and "Nạp" in s["can_lam_gi"] for s in r)
    assert all(s["lap_gio"] == 4.0 for s in r)


# ═══ tu_chay + dieu_phoi nối van ví ═════════════════════════════════════════


def test_tu_chay_het_tien_giua_chung_dung_em_va_khong_bi_bo_oan(tmp_path):
    goc = str(tmp_path)
    run = {"ma_luot": "0001", "san_xuat": {"da_chay": True, "loi": ""}, "phuc_hoi": {
        "so_lan": 2, "lan_dau_luc": 1.0, "loai_loi_truoc": su_co.HET_TIEN}}
    logs = []
    tu_chay._tam_dung_vi_het_tien(goc, run, "402 insufficient_balance", logs.append)  # noqa: SLF001
    assert run["phuc_hoi"] == {}                                   # bộ đếm L3 được xoá
    assert su_co.phan_loai(RuntimeError(run["san_xuat"]["loi"])) != su_co.HET_TIEN
    ly_do = tu_chay._ly_do_vuot_tran_phuc_hoi(  # noqa: SLF001
        run, _dt.date(2026, 9, 30), "2026-09-30")
    assert ly_do == ""                                             # KHÔNG bỏ oan lượt
    assert van_vi.doc_trang_thai(goc)["het_tien"]["chi_tiet"].startswith("402")
    assert any("giữ phần đã làm" in d for d in logs)


def test_tu_chay_nhan_het_tien_tu_khau_hong(tmp_path):
    from core import auto

    luot = auto.LuotChay(ma_kenh="K", ma_luot="1")
    luot.tt("anh").trang_thai = auto.HONG
    luot.tt("anh").loi = "ví hết tiền, nạp thêm"
    run = {"san_xuat": {"loi": ""}}
    tu_chay._nhan_het_tien_tu_luot(str(tmp_path), run, luot, lambda d: None)  # noqa: SLF001
    assert run["san_xuat"]["tam_dung_vi"] is True
    assert "loi_goc" in run["san_xuat"]


def test_tu_chay_chay_mot_ngay_bi_van_vi_chan_lam_moi(tmp_path, monkeypatch):
    from tests.test_tu_chay import (NO_LOG, _danh_sach_gia, _ghi_kenh, _lam_kenh_san_sang)

    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    monkeypatch.setattr(van_vi, "cho_phep_mo_luot",
                        lambda goc_, client, dang_do=False, **k: (False, "ví còn 1₫ thử", {}))
    da_nghien_cuu = []
    ket = tu_chay.chay_mot_ngay(
        goc, "K1", client=object(), che_do="that", hom_nay=_dt.date(2026, 9, 18),
        bay_gio=_dt.datetime(2026, 9, 18, 10, 0), on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: da_nghien_cuu.append(1),
        doc_danh_sach=_danh_sach_gia([]), video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {}, chay_auto=lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert "[VÍ]" in ket["tom_tat"] and da_nghien_cuu == []       # không tốn cả nghiên cứu


def test_dieu_phoi_khong_sinh_luot_moi_khi_vi_can(tmp_path, monkeypatch):
    from tests.test_dieu_phoi import _kenh, _vps

    goc = str(tmp_path)
    _vps(goc)
    _kenh(goc, "K1")
    monkeypatch.setattr(van_vi, "cho_phep_mo_luot",
                        lambda goc_, client, dang_do=False, **k: (False, "ví sắp hết", {}))
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=_dt.datetime(2026, 9, 29, 14, 0), ram=10.0, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1, log=lambda d: None)
    assert sinh == [] and "ví" in ra["chan"]


# ═══ LICENSE WINDOWS ════════════════════════════════════════════════════════

DLV_5_NGAY_1_REARM = ("Timebased activation expiration: 7200 minute(s) (5 day(s))\n"
                      "Remaining Windows rearm count: 1\n")
DLV_176_NGAY = ("Timebased activation expiration: 252828 minute(s) (176 day(s))\n"
                "Remaining Windows rearm count: 2\n")
DLV_20_NGAY_0_REARM = ("Timebased activation expiration: 28800 minute(s) (20 day(s))\n"
                       "Remaining Windows rearm count: 0\n")
DLV_5_NGAY_0_REARM = ("Timebased activation expiration: 7200 minute(s) (5 day(s))\n"
                      "Remaining Windows rearm count: 0\n")
XPR = "Timebased activation will expire 3/24/2027 2:35:57 AM\n"
NGAY = _dt.datetime(2026, 9, 30, 15, 30)
RANH = lambda goc, bay_gio: {"duoc": True, "ly_do": [], "luc_an_toan_tiep": None}  # noqa: E731
BAN = lambda goc, bay_gio: {"duoc": False, "ly_do": ["đang dựng video"], "luc_an_toan_tiep": None}  # noqa: E731


class _May:
    """Giả `cscript`/`shutdown`: ghi lại mọi lệnh, KHÔNG chạy gì thật."""

    def __init__(self, dlv, *, rearm_ok=True):
        self.dlv, self.rearm_ok, self.lenh = dlv, rearm_ok, []

    def __call__(self, lenh):
        self.lenh.append(list(lenh))
        cuoi = lenh[-1]
        if cuoi == "/xpr":
            return 0, XPR
        if cuoi == "/dlv":
            return 0, self.dlv
        if cuoi == "/rearm":
            return (0, "ok") if self.rearm_ok else (1, "Error 0xC004F074")
        if lenh[0] == "shutdown":
            return 0, ""
        return 1, "lạ"

    def da_goi(self, tu):
        return [l for l in self.lenh if tu in l]


def _lic(goc, may, bay_gio=NGAY, **seam):
    seam.setdefault("tu_dang_nhap_bat", lambda: True)
    seam.setdefault("an_toan_fn", RANH)
    return chot_an_toan.kiem_license(goc, bay_gio, chay_lenh=may, **seam)


def test_license_con_lau_khong_rearm_khong_bao(tmp_path):
    may = _May(DLV_176_NGAY)
    ra, ngay = _lic(str(tmp_path), may)
    assert ra == [] and ngay == 176 and may.da_goi("/rearm") == [] and may.da_goi("shutdown") == []


def test_license_5_ngay_con_rearm_thi_tu_rearm_roi_khoi_dong_lai_khi_ranh(tmp_path):
    goc = str(tmp_path)
    may = _May(DLV_5_NGAY_1_REARM)
    ra, _ = _lic(goc, may)
    assert len(may.da_goi("/rearm")) == 1
    assert len(may.da_goi("shutdown")) == 1            # máy rảnh → ra lệnh khởi động lại ngay
    assert any(s["loai"] == "license_khoi_dong_lai" for s in ra)
    lic = chot_an_toan.doc_trang_thai(goc)["license"]
    assert lic["cho_khoi_dong_lai"] is False and lic["so_lan_rearm_tu_dong"] == 1
    assert all("wscript" not in " ".join(l).lower() for l in may.lenh)   # chỉ cscript


def test_license_may_ban_thi_cho_khoi_dong_lai_va_lan_sau_moi_lam(tmp_path):
    goc = str(tmp_path)
    may = _May(DLV_5_NGAY_1_REARM)
    ra, _ = _lic(goc, may, an_toan_fn=BAN)
    assert len(may.da_goi("/rearm")) == 1 and may.da_goi("shutdown") == []
    assert any(s["loai"] == "license_cho_khoi_dong_lai" and "rảnh" in s["chuyen_gi"] for s in ra)
    # 15 phút sau máy rảnh → khởi động lại; KHÔNG rearm lần hai
    _lic(goc, may, bay_gio=NGAY + _dt.timedelta(minutes=15))
    assert len(may.da_goi("/rearm")) == 1 and len(may.da_goi("shutdown")) == 1


def test_license_khong_rearm_hai_lan_du_hom_sau_van_con_han_ngan(tmp_path):
    goc = str(tmp_path)
    may = _May(DLV_5_NGAY_1_REARM)
    _lic(goc, may)
    _lic(goc, may, bay_gio=NGAY + _dt.timedelta(days=1))   # chưa kịp khởi động lại thật
    assert len(may.da_goi("/rearm")) == 1                  # khoá NGAY_KHOA_REARM


def test_license_moi_ngay_chi_doc_slmgr_mot_lan(tmp_path):
    goc = str(tmp_path)
    may = _May(DLV_176_NGAY)
    _lic(goc, may)
    n = len(may.lenh)
    _lic(goc, may, bay_gio=NGAY + _dt.timedelta(hours=3))
    assert len(may.lenh) == n
    _lic(goc, may, bay_gio=NGAY + _dt.timedelta(days=1))
    assert len(may.lenh) > n


def test_license_rearm_loi_thi_bao_khan_va_thu_lai_hom_sau(tmp_path):
    goc = str(tmp_path)
    may = _May(DLV_5_NGAY_1_REARM, rearm_ok=False)
    ra, _ = _lic(goc, may)
    assert any(s["loai"] == "license_rearm_loi" and "RDP" in s["can_lam_gi"] for s in ra)
    _lic(goc, may, bay_gio=NGAY + _dt.timedelta(days=1))
    assert len(may.da_goi("/rearm")) == 2


def test_license_khong_tu_khoi_dong_lai_khi_chua_bat_tu_dang_nhap(tmp_path):
    goc = str(tmp_path)
    may = _May(DLV_5_NGAY_1_REARM)
    ra, _ = _lic(goc, may, tu_dang_nhap_bat=lambda: False)
    assert may.da_goi("shutdown") == []
    assert any(s["muc"] == "khan" and "KHỞI ĐỘNG LẠI" in s["chuyen_gi"] for s in ra)


def test_license_het_rearm_canh_bao_som_30_14_7(tmp_path):
    for dlv, muc, moc in ((DLV_20_NGAY_0_REARM, "nhac", "30"), (DLV_5_NGAY_0_REARM, "khan", "7")):
        goc = str(tmp_path / muc)
        may = _May(dlv)
        ra, _ = _lic(goc, may)
        assert may.da_goi("/rearm") == []                           # hết lượt: không thử
        sc = [s for s in ra if s["loai"] == "license_het_rearm"][0]
        assert sc["dedupe_khoa"].endswith(moc) and sc["can_lam_gi"]
        assert sc["lap_gio"] == 24.0


def test_license_vinh_vien_khong_lam_gi(tmp_path):
    may = _May("License Status: Licensed\n")
    may.__class__ = type("M2", (_May,), {})
    lenh_vv = lambda l: (0, "The machine is permanently activated.\n")  # noqa: E731
    ra, ngay = chot_an_toan.kiem_license(str(tmp_path), NGAY, chay_lenh=lenh_vv,
                                         tu_dang_nhap_bat=lambda: True, an_toan_fn=RANH)
    assert ra == [] and ngay is None


def test_ban_quyen_nen_rearm_khong_con_vap_con_song(tmp_path):
    """Lỗi cũ: `nen_rearm` truyền `con_song=` cho `an_toan_khoi_dong.kiem_tra` (không nhận)."""
    kq = bq.nen_rearm({"vinh_vien": False, "so_ngay_con_lai": 5, "rearm_con_lai": 1},
                      str(tmp_path), bay_gio=_dt.datetime(2026, 9, 29, 15, 30))
    assert kq["trong_han"] and kq["con_rearm"] and kq["an_toan"] is not None


# ═══ HẠN THUÊ VPS ═══════════════════════════════════════════════════════════


def _cai_dat(goc, **kv):
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump(kv, tep)


def test_han_vps_de_trong_hoac_khong_co_thi_bo_qua(tmp_path):
    goc = str(tmp_path)
    assert chot_an_toan.kiem_han_vps(goc, NGAY) == []
    _cai_dat(goc, ngay_het_han_vps="")
    assert chot_an_toan.kiem_han_vps(goc, NGAY) == []


def test_han_vps_nhac_truoc_14_7_3_1_ngay(tmp_path):
    goc = str(tmp_path)
    ket = {}
    for con in (30, 14, 7, 3, 1, 0):
        _cai_dat(goc, ngay_het_han_vps=(NGAY.date() + _dt.timedelta(days=con)).isoformat())
        r = chot_an_toan.kiem_han_vps(goc, NGAY)
        ket[con] = r[0] if r else None
    assert ket[30] is None
    assert [ket[c]["dedupe_khoa"] for c in (14, 7, 3, 1, 0)] == [
        "vps:14", "vps:7", "vps:3", "vps:1", "vps:0"]
    assert ket[14]["muc"] != ket[3]["muc"]              # ≤3 ngày → khẩn
    assert "còn 3 ngày" in ket[3]["chuyen_gi"] and "Gia hạn" in ket[3]["can_lam_gi"]


def test_han_vps_dinh_dang_viet_va_sai(tmp_path):
    goc = str(tmp_path)
    han = (NGAY.date() + _dt.timedelta(days=7)).strftime("%d/%m/%Y")
    _cai_dat(goc, ngay_het_han_vps=han)
    assert chot_an_toan.kiem_han_vps(goc, NGAY)[0]["dedupe_khoa"] == "vps:7"
    _cai_dat(goc, ngay_het_han_vps="tuần sau")
    assert chot_an_toan.kiem_han_vps(goc, NGAY)[0]["loai"] == "han_vps_sai_dinh_dang"


# ═══ GIỌNG ĐỌC TRÙNG ════════════════════════════════════════════════════════


def _kenh_giong(goc, ma, voice, tu_chay_bat=True):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "{0}"\nngon_ngu: "ja"\nengine: "veo3"\nphut_muc_tieu: 10\n'
                  'voice_id: "{1}"\ntu_chay: {2}\n'.format(ma, voice, "true" if tu_chay_bat else "false"))


def test_giong_trung_giua_hai_kenh_tu_chay_thi_canh_bao_khong_tu_doi(tmp_path):
    goc = str(tmp_path)
    for ma in ("A", "B"):
        _kenh_giong(goc, ma, "vvvvvvvvvv")
    _kenh_giong(goc, "C", "vvvvvvvvvv", tu_chay_bat=False)     # không tự chạy → không tính
    ra = chot_an_toan.kiem_giong_trung(goc)
    assert len(ra) == 1 and ra[0]["loai"] == "giong_doc_trung"
    assert "A, B" in ra[0]["chuyen_gi"] and "giong-doc-goi-y.md" in ra[0]["can_lam_gi"]
    assert "voice_id: \"vvvvvvvvvv\"" in open(
        os.path.join(goc, "CHANNEL", "A", "kenh.yaml"), encoding="utf-8").read()   # không đổi


def test_giong_khac_nhau_thi_khong_bao(tmp_path):
    goc = str(tmp_path)
    _kenh_giong(goc, "A", "aaaaaaaaaa")
    _kenh_giong(goc, "B", "bbbbbbbbbb")
    assert chot_an_toan.kiem_giong_trung(goc) == []


# ═══ BA NƠI HIỆN CẢNH BÁO ═══════════════════════════════════════════════════


def test_canh_bao_hien_o_ba_noi_va_loc_lap_theo_lap_gio(tmp_path):
    goc = str(tmp_path)
    bay_gio = _dt.datetime(2026, 9, 30, 10, 0)
    r, _ = chot_an_toan.kiem_vi(goc, client=object(), bay_gio=bay_gio.timestamp(), lay=_lay(1))
    van_vi.ghi_het_tien(goc, "402", so_du_vnd=1.0, bay_gio=bay_gio.timestamp())
    r, _ = chot_an_toan.kiem_vi(goc, client=object(), bay_gio=bay_gio.timestamp(), lay=_lay(1))
    assert r
    anh = {"luc": bay_gio.isoformat(), "kenh": {}, "may": {}}
    guis = []
    gui = lambda *a, **k: guis.append(a) or True   # noqa: E731
    kq = gac_tong.bao_cao_su_co(goc, anh, r, bay_gio=bay_gio, gui_khan=gui, gui_thuong=gui)
    # (1) giao diện: tinh-trang.json → canh_bao_may → bang điều khiển
    tt = json.load(open(gac_tong.duong_tinh_trang(goc), encoding="utf-8"))
    assert tt["canh_bao_may"][0]["loai"] == "vi_het_tien"
    assert tt["canh_bao_may"][0]["can_lam_gi"]
    viec = bang_dieu_khien.doc_tinh_trang(goc)["canh_bao_may"]
    assert viec and "HẾT TIỀN" in viec[0]["chuyen_gi"]
    # (2) loi-chay-max.md
    assert "HẾT TIỀN" in open(gac_tong.duong_loi_chay_max(goc), encoding="utf-8").read()
    # (3) bản tin gác tổng
    tin = gac_tong.ban_tin_ngay(goc, anh, r, bay_gio=bay_gio, so_du_vnd=1.0)
    assert "CẢNH BÁO CẤP MÁY" in tin and "Việc cần làm: Nạp tiền" in tin
    assert kq["so_da_bao"] == 1 and len(guis) == 1
    # lặp: 3 giờ sau chưa báo lại, 4 giờ sau báo lại
    gac_tong.bao_cao_su_co(goc, anh, r, bay_gio=bay_gio + _dt.timedelta(hours=3),
                           gui_khan=gui, gui_thuong=gui)
    assert len(guis) == 1
    gac_tong.bao_cao_su_co(goc, anh, r, bay_gio=bay_gio + _dt.timedelta(hours=4, minutes=1),
                           gui_khan=gui, gui_thuong=gui)
    assert len(guis) == 2


def test_ngay_het_han_bao_moi_24_gio_khong_phai_4_gio(tmp_path):
    goc = str(tmp_path)
    bay_gio = _dt.datetime(2026, 9, 30, 10, 0)
    _cai_dat(goc, ngay_het_han_vps=(bay_gio.date() + _dt.timedelta(days=3)).isoformat())
    r = chot_an_toan.kiem_han_vps(goc, bay_gio)
    anh = {"luc": bay_gio.isoformat(), "kenh": {}, "may": {}}
    guis = []
    gui = lambda *a, **k: guis.append(a) or True   # noqa: E731
    gac_tong.bao_cao_su_co(goc, anh, r, bay_gio=bay_gio, gui_khan=gui, gui_thuong=gui)
    gac_tong.bao_cao_su_co(goc, anh, r, bay_gio=bay_gio + _dt.timedelta(hours=5),
                           gui_khan=gui, gui_thuong=gui)
    assert len(guis) == 1
    gac_tong.bao_cao_su_co(goc, anh, r, bay_gio=bay_gio + _dt.timedelta(hours=25),
                           gui_khan=gui, gui_thuong=gui)
    assert len(guis) == 2
