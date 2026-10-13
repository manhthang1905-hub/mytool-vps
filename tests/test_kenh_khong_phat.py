"""Kênh không được YouTube phát (`core/kenh_khong_phat.py`, 12/10/2026): luật thuần, cờ + đợt + báo chủ, chủ xoá cờ
(CLI / nút "Đã kiểm Studio" / kenh.yaml), tự mở lại khi video mới ≥ 300 hiển thị, điều phối không sinh lượt MỚI, gác
tổng báo khẩn thay cho "không video mới".

Không mạng; mọi thứ trong `tmp_path`; chuỗi số dựng tay (`thuoc_thang.Chuoi/Diem`), mã video giả.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

import pytest

from core import auto, dieu_phoi, kenh_khong_phat as kp, thuoc_thang as tt

BAY = _dt.datetime(2026, 10, 12, 9, 0)
NOW = BAY.timestamp()


@pytest.fixture(autouse=True)
def _luat_co_che(request, monkeypatch):
    """Các bài cũ kiểm CƠ CHẾ với luật 12/10 (3 video, dừng sản xuất). Luật mặc định 13/10 (10 video, KHÔNG dừng —
    chủ đổi mail) kiểm riêng ở `test_mac_dinh_13_10_*` (đánh dấu `mac_dinh`)."""
    if "mac_dinh" in request.keywords:
        return
    monkeypatch.setattr(kp, "SO_VIDEO", 3)
    monkeypatch.setattr(kp, "SO_VIDEO_XET_TOI_DA", 8)
    monkeypatch.setattr(kp, "DUNG_SAN_XUAT", True)


@pytest.mark.mac_dinh
def test_mac_dinh_13_10_can_10_video_va_khong_dung_san_xuat():
    assert kp.SO_VIDEO == 10 and kp.DUNG_SAN_XUAT is False
    kq = kp.phan_xet(_chet(), NOW)                       # chỉ 3 video dưới 50 → CHƯA đủ 10 → chưa báo
    assert kq["trang_thai"] != kp.KHONG_PHAT


def _c(ma, tuoi_nay, *diem):
    """Chuỗi giả: video đăng `tuoi_nay` giờ trước BAY, các bản chụp (tuổi, hiển thị)."""
    dang = NOW - tuoi_nay * 3600.0
    return tt.Chuoi(ma=ma, dang=dang, diem=[tt.Diem(tuoi=float(t), hien_thi=float(h), xem=1.0, luc=dang + t * 3600.0)
                                            for t, h in diem])


def _chet():
    return {"FAKEvid0001": _c("FAKEvid0001", 180, (24, 3), (96, 22)),
            "FAKEvid0002": _c("FAKEvid0002", 150, (48, 5), (120, 30)),
            "FAKEvid0003": _c("FAKEvid0003", 100, (73, 8)),
            "FAKEvid0004": _c("FAKEvid0004", 40, (24, 12))}


# ── luật thuần ───────────────────────────────────────────────────────────────

def test_ba_video_duoi_50_sau_72h_la_khong_duoc_phat():
    kq = kp.phan_xet(_chet(), NOW)
    assert kq["trang_thai"] == kp.KHONG_PHAT
    assert [b["ma"] for b in kq["bang_chung"]] == ["FAKEvid0003", "FAKEvid0002", "FAKEvid0001"]
    assert "3 video gần nhất" in kq["ly_do"]


def test_mot_video_tu_50_tro_len_la_duoc_phat():
    ch = _chet()
    ch["FAKEvid0002"] = _c("FAKEvid0002", 150, (48, 5), (120, 60))
    assert kp.phan_xet(ch, NOW)["trang_thai"] == kp.SONG


def test_video_tre_tu_300_la_tu_mo_lai():
    ch = _chet()
    ch["FAKEvid0004"] = _c("FAKEvid0004", 40, (24, 350))
    kq = kp.phan_xet(ch, NOW)
    assert kq["trang_thai"] == kp.SONG and kq["song_vi"]["ma"] == "FAKEvid0004"


def test_thieu_ban_chup_72h_thi_bo_qua_khong_doan():
    ch = _chet()
    ch["FAKEvid0003"] = _c("FAKEvid0003", 100, (49, 8))      # không có bản ≥ 72h, chưa tới 50 → "thiếu số"
    kq = kp.phan_xet(ch, NOW)
    assert kq["trang_thai"] == kp.CHUA_DU and kq["n_thieu"] == 1 and len(kq["bang_chung"]) == 2
    ch["FAKEvid0003"] = _c("FAKEvid0003", 100, (49, 80))     # bản trẻ đã ≥ 50 → được phát
    assert kp.phan_xet(ch, NOW)["trang_thai"] == kp.SONG


def test_moc_xoa_chi_tinh_video_dang_sau():
    moc = NOW - 160 * 3600.0
    kq = kp.phan_xet(_chet(), NOW, moc)
    assert kq["trang_thai"] == kp.CHUA_DU and len(kq["bang_chung"]) == 2


def test_chi_dung_ban_chup_toi_luc_xet_cham_nguoc_duoc():
    ch = _chet()
    ch["FAKEvid0002"].diem.append(tt.Diem(tuoi=200.0, hien_thi=900.0, xem=1.0, luc=NOW + 3600.0))
    assert kp.phan_xet(ch, NOW)["trang_thai"] == kp.KHONG_PHAT   # bản chụp TƯƠNG LAI bị bỏ


# ── cờ, đợt, báo chủ, xoá cờ ────────────────────────────────────────────────

def _kenh_yaml(goc, ma="KX", *dong):
    p = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(('ma: "{0}"'.format(ma), "tu_chay: true", 'ngon_ngu: "ja"') + dong) + "\n")


@pytest.fixture()
def chuoi_gia(monkeypatch):
    du = {"KX": _chet()}
    monkeypatch.setattr(tt, "chuoi_kenh", lambda goc, k: du.get(k, {}))
    return du


def test_bat_co_bao_mot_lan_roi_chu_xoa_bang_cli(tmp_path, chuoi_gia):
    goc = str(tmp_path)
    _kenh_yaml(goc)
    t = kp.cap_nhat(goc, "KX", bay_gio=BAY)
    assert t["trang_thai"] == kp.KHONG_PHAT and t["lan"] == 1
    dung, ly = kp.dang_dung(goc, "KX", bay_gio=BAY)
    assert dung and "không được YouTube phát" in ly
    md = open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8").read()
    assert md.count("**khan** · kênh KX") == 1 and "Dành cho trẻ em" in md and "youtube.com/features" in md
    kp.cap_nhat(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=4), ep=True)          # cùng đợt: không báo lại
    assert open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8").read().count(
        "**khan** · kênh KX") == 1
    sc = kp.su_co(goc, "KX", kp.doc(goc, "KX"))
    assert sc["muc"] == "khan" and sc["dedupe_khoa"] == "kenh_khong_phat:KX:1" and sc["lap_gio"] == 24.0
    t = kp.xoa(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=5))
    assert t["trang_thai"] == kp.CHUA_DU and kp.dang_dung(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=5)) == (False, "")
    assert any(x["su"] == "chu_xoa" for x in t["lich_su"])


def test_nut_da_kiem_studio_va_kenh_yaml_cung_xoa_co(tmp_path, chuoi_gia):
    goc = str(tmp_path)
    _kenh_yaml(goc)
    kp.cap_nhat(goc, "KX", bay_gio=BAY)
    v = kp.viec_cua_ban(goc, "KX", bay_gio=BAY)
    assert v["khoa"] == "khong-phat:KX:1" and "6" in v["goi_y"] and "Dành cho trẻ em" in v["chi_tiet"]
    from core import bang_dieu_khien as bdk

    bdk.danh_dau_xong(goc, v["khoa"], bay_gio=BAY + _dt.timedelta(hours=1))
    assert kp.dang_dung(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=1))[0] is False   # đọc mốc xoá ngay
    t = kp.cap_nhat(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=2))
    assert t["trang_thai"] == kp.CHUA_DU and t["nguon_xoa"] == "chu_nut"
    # kenh.yaml `kenh_khong_phat: tat` → không bao giờ dừng
    _kenh_yaml(goc, "KX", "kenh_khong_phat: tat")
    t = kp.cap_nhat(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=3), ep=True)
    assert kp.dang_dung(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=3))[0] is False


def test_viec_cua_ban_co_muc_hong_kem_nut_da_kiem_studio(tmp_path, chuoi_gia, monkeypatch):
    from core import bang_dieu_khien as bdk

    goc = str(tmp_path)
    _kenh_yaml(goc)
    kp.cap_nhat(goc, "KX", bay_gio=BAY)
    monkeypatch.setattr(bdk, "dong_may", lambda *a, **kw: {"vi": {"muc": bdk.TOT, "so_ngay_con_chay": None},
                                                           "o_dia": {"muc": bdk.TOT, "con_gb": None}})
    viec = bdk.viec_cua_ban(goc, anh={"kenh": [{"ma": "KX"}]}, bay_gio=BAY, gio_lich="02:00")
    v = [x for x in viec if x["khoa"] == "khong-phat:KX:1"]
    assert len(v) == 1 and v[0]["muc"] == bdk.HONG and v[0]["xong_tay"]
    assert [n[1] for n in v[0]["nut"]] == ["xem_chu", "chep_link", "danh_dau_xong"]
    bdk.danh_dau_xong(goc, "khong-phat:KX:1", bay_gio=BAY)
    viec = bdk.viec_cua_ban(goc, anh={"kenh": [{"ma": "KX"}]}, bay_gio=BAY, gio_lich="02:00")
    assert not [x for x in viec if x["khoa"].startswith("khong-phat:")]


def test_kenh_yaml_da_kiem_studio(tmp_path, chuoi_gia):
    goc = str(tmp_path)
    _kenh_yaml(goc, "KX", 'da_kiem_studio: "2026-10-12"')
    t = kp.cap_nhat(goc, "KX", bay_gio=BAY)
    assert t["trang_thai"] == kp.CHUA_DU and t["nguon_xoa"] == "chu_kenh_yaml"


def test_tu_mo_lai_khi_video_moi_tu_300(tmp_path, chuoi_gia):
    goc = str(tmp_path)
    _kenh_yaml(goc)
    kp.cap_nhat(goc, "KX", bay_gio=BAY)
    chuoi_gia["KX"]["FAKEvid0005"] = _c("FAKEvid0005", 30, (24, 420))
    t = kp.cap_nhat(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=1), ep=True)
    assert t["trang_thai"] == kp.SONG and t["lich_su"][-1]["su"] == "tu_mo"


def test_co_cu_qua_48h_khong_chan(tmp_path, chuoi_gia):
    goc = str(tmp_path)
    _kenh_yaml(goc)
    kp.cap_nhat(goc, "KX", bay_gio=BAY)
    assert kp.dang_dung(goc, "KX", bay_gio=BAY + _dt.timedelta(hours=49))[0] is False


def test_cong_san_xuat_khong_mo_nguon_moi(tmp_path, chuoi_gia):
    from core import tu_chay
    from core.kenh import doc_kenh

    goc = str(tmp_path)
    _kenh_yaml(goc)
    kp.cap_nhat(goc, "KX", bay_gio=BAY)
    mo, ly, ttin = tu_chay._cua_so_san_xuat(goc, "KX", doc_kenh(goc, "KX"), bay_gio=BAY)  # noqa: SLF001
    assert mo is False and ttin.get("khong_phat") and "kiểm Studio" in ly


# ── điều phối: không sinh lượt MỚI; lượt dở xếp sau kênh sống ───────────────

def _vps(goc):
    with open(os.path.join(goc, "vps.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump({"dieu_phoi": True, "lan_api": 2}, tep)


def _kenh_dp(goc, ma):
    p = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "{0}"\nngon_ngu: "ja"\nengine: "veo3"\nphut_muc_tieu: 10\ntu_chay: true\ntu_duyet: true\n'
                  'ngan_sach_ngay: 5000000\nnhip_dang: "12:00, 20:00"\nvideo_toi_da_ngay: 4\n'.format(ma))


def test_dieu_phoi_bo_qua_kenh_khong_phat_va_xep_luot_do_sau(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _vps(goc)
    for ma in ("KX", "KY"):
        _kenh_dp(goc, ma)
    du = {"KX": _chet()}
    monkeypatch.setattr(tt, "chuoi_kenh", lambda g, k: du.get(k, {}))
    bay = _dt.datetime(2026, 10, 12, 14, 0)
    t = dieu_phoi.trang_thai_kenh(goc, "KX", bay_gio=bay)
    assert t["chay"] is False and t.get("khong_phat") and "không được YouTube phát" in t["ly_do"]
    sinh = []
    dieu_phoi.nhip(goc, bay_gio=bay, ram=10.0, dia_gb=30.0, sinh=lambda g, ma: sinh.append(ma) or 1,
                   log=lambda d: None)
    assert "KX" not in sinh and "KY" in sinh
    # lượt DỞ của kênh không được phát: vẫn được làm nốt, nhưng xếp SAU kênh sống
    luot = auto.moi_luot(goc, "KX", "0001", {"link": "x", "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)
    so = os.path.join(goc, "CHANNEL", "KX", "tu-chay")
    os.makedirs(so, exist_ok=True)
    with open(os.path.join(so, "2026-10-12.json"), "w", encoding="utf-8") as tep:
        json.dump({"ngay": "2026-10-12", "kenh": "KX", "nhat_ky": [],
                   "runs": [{"ma_luot": "0001", "san_xuat": {"da_chay": True}}]}, tep)
    t = dieu_phoi.trang_thai_kenh(goc, "KX", bay_gio=bay)
    assert t["chay"] is True and t["diem"] == -1000.0 and t.get("khong_phat")


# ── gác tổng: báo khẩn kênh không được phát, im "không video mới" ───────────

def test_gac_tong_thay_khong_video_moi_bang_su_co_khong_phat():
    from core import gac_tong

    sc = {"loai": "kenh_khong_phat", "kenh": "KX", "muc": "khan", "chuyen_gi": "Kênh KX không được YouTube phát",
          "can_lam_gi": "kiểm Studio", "neu_khong_lam": "", "dedupe_khoa": "kenh_khong_phat:KX:1", "lap_gio": 24.0}
    anh = {"luc": BAY.isoformat(), "kenh": {"KX": {"tu_chay": True, "ke_hoach": [], "khong_phat": {"dung": True,
                                                                                                    "su_co": sc}}}}
    ds = gac_tong.kiem_su_co(anh)
    assert [d["loai"] for d in ds if d.get("kenh") == "KX"].count("kenh_khong_phat") == 1
    assert not [d for d in ds if d["loai"] == "khong_video_moi"]
