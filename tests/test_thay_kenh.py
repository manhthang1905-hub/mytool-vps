"""20/10/2026 — kênh trả kho không tính ở đâu cả, kho Chrome (`<cha của MyTool>\\kho`), tự phát hiện kênh không được
phân phối + tự thay (`core/thay_kenh.py`, `core/kho_chrome.py`, `core/tra_kho.py`). Mọi thứ trong tmp; Chrome, DOM,
LLM thay bằng hàm giả. Mã kênh/video là mã giả."""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

GOC_REPO = Path(__file__).resolve().parent.parent
for _p in (str(GOC_REPO), str(GOC_REPO / "vm")):
    if _p not in sys.path:
        sys.path.append(_p)

from core import kenh as kenh_mod  # noqa: E402
from core import kho_chrome, mo_kenh, thay_kenh, tra_kho  # noqa: E402

NOW = dt.datetime(2026, 10, 20, 9, 0)
RANH = (lambda *a: "")            # Chrome không chạy, khoá máy rảnh


@pytest.fixture()
def goc(tmp_path):
    g = tmp_path / "MyTool"
    (g / "vm").mkdir(parents=True)
    return str(g)


def _kenh(goc, ma, them=""):
    d = Path(goc) / "CHANNEL" / ma
    d.mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text('ma: "{0}"\nten: "x"\nnhom: "g1"\ntep: "t1"\nvoice_id: "V-{0}"\ntu_chay: true\n'
                                 'thiet_lap_kenh: true\nnuoi_trang_chu: true\n{1}'.format(ma, them), encoding="utf-8")
    return d


def _bang(goc, ma, hien_thi, ngay="2026-10-10", moc="200h", mtime=None):
    d = Path(goc) / "CHANNEL" / ma / "chi-so"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "bang-tom-tat.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Tiêu đề", "Mã video", "Ngày đăng", "Dài", "Mốc mới nhất", "Lượt hiển thị", "Lượt xem"])
        for i, h in enumerate(hien_thi):
            w.writerow(["t", "AAAAAAAAA{0:02d}".format(i), ngay, "10:00", moc, str(h), "1"])
    t = (mtime or NOW).timestamp()
    os.utime(p, (t, t))
    return p


def _chrome(cha, ten, dang_nhap=None):
    d = Path(cha) / ten
    (d / "App" / "Chrome-bin").mkdir(parents=True)
    (d / "App" / "Chrome-bin" / "chrome.exe").write_bytes(b"MZ")
    (d / (ten + ".exe")).write_bytes(b"MZ")
    if dang_nhap:
        pd = d / "Data" / "profile" / "Default" / "Network"
        pd.mkdir(parents=True)
        con = sqlite3.connect(str(pd / "Cookies"))
        con.execute("create table cookies (host_key text, name text, value text)")
        con.execute("insert into cookies values (?, ?, '')", dang_nhap)
        con.commit()
        con.close()
    return d


def _vm_cfg(goc, cac):
    (Path(goc) / "vm" / "config.json").write_text(json.dumps({"cac_kenh": cac}), encoding="utf-8")


# ── 1) luật phát hiện (thuần) ───────────────────────────────────────────────────
def _xet(hien_thi, **kw):
    dong = [{"Mã video": "x", "Ngày đăng": kw.get("ngay", "2026-10-10"), "Mốc mới nhất": kw.get("moc", "200h"),
             "Lượt hiển thị": str(h)} for h in hien_thi]
    return thay_kenh.xet_kenh(dong, kw.get("mtime", NOW.timestamp()), NOW)


def test_xet_kenh_hong_dat_thieu_so():
    assert _xet([12, 15, 9, 11, 63, 4, 18, 41, 23, 10])["ket"] == "hong"
    assert _xet([12, 15, 9, 11, 63, 4, 18, 41, 23, 10, 501])["ket"] == "dat"            # một video > 500 → được phát
    assert _xet([150] * 10)["ket"] == "dat"                                             # trung vị ≥ 100
    assert _xet([12] * 9)["ket"] == "thieu_so"                                          # < 10 video
    assert _xet([12] * 10, ngay="2026-10-18")["ket"] == "thieu_so"                      # chưa đủ 72 giờ (cuối ngày đăng)
    assert _xet([12] * 10, moc="48h")["ket"] == "thieu_so"                              # bản chụp mới nhất < 72 giờ
    assert _xet([12] * 10, mtime=(NOW - dt.timedelta(days=3, hours=1)).timestamp())["ket"] == "thieu_so"   # số cũ
    assert thay_kenh.xet_kenh([], None, NOW)["ket"] == "thieu_so"
    # dòng thiếu số không tính; số có dấu phân cách nghìn đọc đúng
    assert _xet(["", ""] + [12] * 10)["ket"] == "hong"
    assert _xet(["1,234"] + [12] * 10)["ket"] == "dat"


# ── 2) kênh trả kho không tính ──────────────────────────────────────────────────
def test_liet_ke_kenh_bo_kenh_tra_kho(goc):
    _kenh(goc, "TLx-T7")
    _kenh(goc, "TLy-T7", 'tra_kho: "2026-10-19"\n')
    assert kenh_mod.liet_ke_kenh(goc) == ["TLx-T7"]
    assert kenh_mod.liet_ke_kenh(goc, ca_tra_kho=True) == ["TLx-T7", "TLy-T7"]
    assert kenh_mod.bo_kenh_tra_kho(goc, ["TLy-T7", "TLx-T7", "KHONG-CO"]) == ["TLx-T7", "KHONG-CO"]
    # lấy lại (đổi tệp) → nhớ đệm theo mtime/cỡ đọc lại
    p = Path(goc) / "CHANNEL" / "TLy-T7" / "kenh.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('tra_kho: "2026-10-19"', 'tra_kho: ""'), encoding="utf-8")
    assert kenh_mod.liet_ke_kenh(goc) == ["TLx-T7", "TLy-T7"]


def test_nguon_kenh_tra_kho_giu_duoc_nha(goc):
    from core import nghien_cuu_nhom as nn
    _kenh(goc, "TLy-T7", 'tra_kho: "2026-10-19"\n')
    _kenh(goc, "TLx-T7")
    assert nn._giu_la_rac(goc, {"kenh": "TLy-T7", "luc": 9e12})                 # trả kho → nhả ngay
    assert not nn._giu_la_rac(goc, {"kenh": "TLx-T7", "luc": 9e12})


def test_kenh_khong_phat_khong_bao_kenh_tra_kho():
    from core import kenh_khong_phat as kp
    assert kp.da_tat({"tra_kho": "2026-10-19"}) and not kp.da_tat({"tra_kho": ""})


# ── 3) kho Chrome: tìm, dời vào/ra kho ──────────────────────────────────────────
def test_tim_chrome_lui_ve_kho(goc):
    cha = Path(goc).parent
    assert tra_kho.thu_muc_kho(goc) == str(cha / "kho")
    _chrome(cha / "kho", "TLy-T7")
    assert tra_kho.tim_chrome(goc, "TLy-T7").endswith(os.path.join("kho", "TLy-T7", "TLy-T7.exe"))
    assert mo_kenh.thu_muc_chrome(goc, "TLy-T7") == tra_kho.tim_chrome(goc, "TLy-T7")
    from core.trung_tam import tim_trinh_duyet
    (Path(goc) / "CHANNEL").mkdir()                              # dấu vết bản một-thư-mục (Chrome nằm cạnh MyTool)
    assert tim_trinh_duyet(os.path.join(goc, "vm"), "TLy-T7") == tra_kho.tim_chrome(goc, "TLy-T7")
    _chrome(cha, "TLx-T7")
    assert tra_kho.tim_chrome(goc, "TLx-T7") == str(cha / "TLx-T7" / "TLx-T7.exe")
    assert mo_kenh.thu_muc_chrome(goc, "MOI") == str(cha / "MOI" / "MOI.exe")       # chưa có ở đâu: đường thường


def test_tra_kho_doi_chrome_vao_kho_ban_thi_hoan_lay_lai_doi_ve(goc):
    cha = Path(goc).parent
    _kenh(goc, "TLy-T7")
    _chrome(cha, "TLy-T7")
    kq = tra_kho.tra(goc, "TLy-T7", thay="TLy-T7-K2", ban=lambda *a: "Chrome kênh đang chạy")
    assert kq["chrome"] == "hoan" and (cha / "TLy-T7").is_dir()
    assert tra_kho.chrome_cho_cat(goc) == ["TLy-T7"]
    assert kenh_mod.da_tra_kho(goc, "TLy-T7")
    assert tra_kho.nhip_chrome(goc, ban=RANH)["TLy-T7"][0] == "da_doi"
    assert not (cha / "TLy-T7").exists() and (cha / "kho" / "TLy-T7" / "TLy-T7.exe").is_file()
    assert tra_kho.chrome_cho_cat(goc) == []
    assert tra_kho.tra(goc, "TLy-T7", ban=RANH)["chrome"] == "o_kho"                  # chạy lại an toàn
    kq = tra_kho.lay_lai(goc, "TLy-T7", ban=RANH)
    assert kq["chrome"] == "da_doi" and (cha / "TLy-T7" / "TLy-T7.exe").is_file() and not kenh_mod.da_tra_kho(goc, "TLy-T7")


def test_doi_chrome_khong_de_dich_co_san(goc):
    cha = Path(goc).parent
    _kenh(goc, "TLy-T7", 'tra_kho: "2026-10-19"\n')
    _chrome(cha, "TLy-T7")
    (cha / "kho" / "TLy-T7").mkdir(parents=True)
    assert tra_kho.cat_chrome(goc, "TLy-T7", ban=RANH)[0] == "da_co"
    assert (cha / "TLy-T7" / "TLy-T7.exe").is_file()                                  # không xoá, không đè


def test_kho_chrome_quet_giu_lap_dat(goc):
    kho = Path(goc).parent / "kho"
    _kenh(goc, "TLy-T7", 'tra_kho: "2026-10-19"\n')
    _chrome(kho, "TLy-T7", dang_nhap=(".youtube.com", "LOGIN_INFO"))               # Chrome kênh trả kho
    _chrome(kho, "gmail-moi-1", dang_nhap=(".google.com", "SID"))                  # mới, đăng nhập Gmail tay
    _chrome(kho, "gmail-moi-2")                                                     # chưa đăng nhập
    (kho / "thieu").mkdir()
    loai = {x["ten"]: x["loai"] for x in kho_chrome.quet(goc)}
    assert loai == {"TLy-T7": "kenh", "gmail-moi-1": "moi", "gmail-moi-2": "chua_dang_nhap", "thieu": "thieu_launcher"}
    assert kho_chrome.giu(goc, "gmail-moi-1", "TLx-T7-K2")
    assert not kho_chrome.giu(goc, "gmail-moi-1", "TLz-T7-K2")                      # đã giao kênh khác
    assert kho_chrome.chrome_cua_kenh(goc, "TLx-T7-K2") == "gmail-moi-1"
    assert {x["ten"]: x["loai"] for x in kho_chrome.quet(goc)}["gmail-moi-1"] == "da_dung"
    # sập giữa chừng: đã dời thư mục, chưa đổi tên launcher → chạy lại làm nốt
    cha = Path(goc).parent
    os.rename(kho / "gmail-moi-1", cha / "TLx-T7-K2")
    tt, _ = kho_chrome.lap_dat(goc, "gmail-moi-1", "TLx-T7-K2")
    assert tt == "da_lap" and (cha / "TLx-T7-K2" / "TLx-T7-K2.exe").is_file()
    assert not (cha / "TLx-T7-K2" / "gmail-moi-1.exe").exists()
    assert kho_chrome.lap_dat(goc, "gmail-moi-1", "TLx-T7-K2")[0] == "co_san"


# ── 4) luồng thay tự động ────────────────────────────────────────────────────────
def _dung_may(goc, so_giong=2):
    _vm_cfg(goc, ["TLa-T7", "TLx-T7-K2"])
    _kenh(goc, "TLa-T7")
    _kenh(goc, "TLx-T7-K2")
    _bang(goc, "TLa-T7", [5000] * 12)
    _bang(goc, "TLx-T7-K2", [12, 15, 9, 11, 63, 4, 18, 41, 23, 10])
    d = Path(goc) / "CHANNEL" / "_NHOM" / "g1"
    d.mkdir(parents=True)
    giong = [{"voice_id": "V-TLa-T7", "ky_tu_moi_phut": 270}, {"voice_id": "V-TLx-T7-K2", "ky_tu_moi_phut": 270}]
    giong += [{"voice_id": "V-MOI-{0}".format(i), "ky_tu_moi_phut": 270} for i in range(so_giong - 2)]
    (d / "kho-giong.json").write_text(json.dumps({"giong": giong}), encoding="utf-8")


def _tra_ranh(goc_, ma, **kw):
    return tra_kho.tra(goc_, ma, ban=RANH, **kw)


def _chay(goc, **kw):
    log = []
    kw.setdefault("tra", _tra_ranh)
    kw.setdefault("nhip_chrome", lambda g: tra_kho.nhip_chrome(g, ban=RANH))
    ma = thay_kenh.chay(goc, bay_gio=kw.pop("bay_gio", NOW), log=log.append, **kw)
    return ma, log


def test_luong_thay_tu_dong_tu_dau_den_cuoi(goc, monkeypatch):
    cha = Path(goc).parent
    _dung_may(goc, so_giong=3)
    _chrome(cha, "TLx-T7-K2")
    _chrome(cha / "kho", "gmail-moi", dang_nhap=(".google.com", "SID"))
    bao = []
    monkeypatch.setattr(thay_kenh, "_bao", lambda g, loai, td, ct, kenh="": bao.append((loai, td, ct)))
    tao = []

    def tao_kenh(g, ma):
        tao.append(ma)
        (Path(g) / "vm" / "logs" / "tao-kenh").mkdir(parents=True, exist_ok=True)
        (Path(g) / "vm" / "logs" / "tao-kenh" / (ma + ".json")).write_text(
            json.dumps({"ket_qua": "ok", "uc": "UCaaaaaaaaaaaaaaaaaaaaaa", "ten": "Tên sạch"}), encoding="utf-8")
        (Path(g) / "vm" / "logs" / "kenh-uc.json").write_text(json.dumps({ma: "UCaaaaaaaaaaaaaaaaaaaaaa"}), encoding="utf-8")
        return 0

    assert thay_kenh.can_lam(goc, NOW)[0]
    ma, log = _chay(goc, chay_tao_kenh=tao_kenh)
    assert ma == 0
    so = thay_kenh.doc_so(goc)
    l = so["luot"]["TLx-T7-K2"]
    assert l["moi"] == "TLx-T7-K3" and l["buoc"] == "thuong_hieu" and l["chrome_kho"] == "gmail-moi"
    assert kenh_mod.da_tra_kho(goc, "TLx-T7-K2")                                           # kênh cũ trả kho
    assert (cha / "kho" / "TLx-T7-K2" / "TLx-T7-K2.exe").is_file()                          # Chrome cũ vào kho
    assert (cha / "TLx-T7-K3" / "TLx-T7-K3.exe").is_file() and not (cha / "kho" / "gmail-moi").exists()
    d = mo_kenh.doc_trang_thai(goc)["kenh"]["TLx-T7-K3"]
    assert d["loai"] == thay_kenh.LOAI_MO_KENH and d["kenh_goc"] == "TLx-T7-K2" and d["tu_dong"] and d["can_thuong_hieu"]
    assert so["ket_xet"]["TLa-T7"]["ket"] == "dat" and so["ngay_xet"] == "2026-10-20"
    # mo_kenh chưa chuẩn bị xong → skill không có việc (không tính "chưa đạt")
    assert thay_kenh.can_lam(goc, NOW) == (False, "không có việc thay kênh")
    assert mo_kenh.viec_cua_ban(goc) == []                                                 # không phải việc người
    # chạy lại cùng ngày: không mở lượt thứ hai, không tạo đôi
    _chay(goc, chay_tao_kenh=tao_kenh)
    assert list(thay_kenh.doc_so(goc)["luot"]) == ["TLx-T7-K2"] and not tao
    # mo_kenh chuẩn bị xong (giả) → tạo kênh thương hiệu dưới khoá máy → cho_mo_kenh
    st = mo_kenh.doc_trang_thai(goc)
    st["kenh"]["TLx-T7-K3"].update(trang_thai="cho_chrome", ten_goi_y="Tên：dự kiến")
    mo_kenh.luu_trang_thai(goc, st)
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc, chay_tao_kenh=tao_kenh)
    assert tao == ["TLx-T7-K3"] and thay_kenh.doc_so(goc)["luot"]["TLx-T7-K2"]["buoc"] == "cho_mo_kenh"
    assert thay_kenh.thuong_hieu_xong(goc, "TLx-T7-K3")[0]
    # mo_kenh xong → MỘT tin báo
    st = mo_kenh.doc_trang_thai(goc)
    st["kenh"]["TLx-T7-K3"]["trang_thai"] = "xong"
    mo_kenh.luu_trang_thai(goc, st)
    _chay(goc, chay_tao_kenh=tao_kenh)
    _chay(goc, chay_tao_kenh=tao_kenh)
    assert thay_kenh.doc_so(goc)["luot"]["TLx-T7-K2"]["buoc"] == "xong"
    assert [b[0] for b in bao] == ["thay_kenh_xong"] and "TLx-T7-K3" in bao[0][1]


def test_kho_het_chrome_van_tra_kho_va_bao_mot_viec(goc, monkeypatch):
    _dung_may(goc, so_giong=3)
    bao = []
    monkeypatch.setattr(thay_kenh, "_bao", lambda g, loai, td, ct, kenh="": bao.append(loai))
    _chay(goc)
    l = thay_kenh.doc_so(goc)["luot"]["TLx-T7-K2"]
    assert kenh_mod.da_tra_kho(goc, "TLx-T7-K2") and l["buoc"] == "chon_chrome"
    v = thay_kenh.viec_cua_ban(goc)
    assert len(v) == 1 and "Kho hết Chrome mới đã đăng nhập" in v[0]["chu"]
    assert not thay_kenh.can_lam(goc, NOW)[0]                                              # chờ người, không chạy lại vô ích
    _chay(goc)
    assert bao == ["kho_chrome_het"]                                                         # báo một lần
    # chủ thả Chrome chưa đăng nhập → bỏ qua + việc người; Chrome đã đăng nhập → đi tiếp
    _chrome(Path(goc).parent / "kho", "chua-dn")
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    assert any("chưa đăng nhập Gmail" in x["chu"] for x in thay_kenh.viec_cua_ban(goc))
    _chrome(Path(goc).parent / "kho", "da-dn", dang_nhap=(".youtube.com", "LOGIN_INFO"))
    _chay(goc)
    assert thay_kenh.doc_so(goc)["luot"]["TLx-T7-K2"]["chrome_kho"] == "da-dn"


def test_het_giong_chua_dung_thi_viec_nguoi(goc):
    _dung_may(goc, so_giong=2)
    (Path(goc) / "CHANNEL" / "_NHOM" / "g1" / "kho-giong.json").write_text(      # giọng duy nhất đang có kênh chạy dùng
        json.dumps({"giong": [{"voice_id": "V-TLa-T7", "ky_tu_moi_phut": 270}]}), encoding="utf-8")
    _chrome(Path(goc).parent / "kho", "gmail-moi", dang_nhap=(".google.com", "SID"))
    _chay(goc)
    l = thay_kenh.doc_so(goc)["luot"]["TLx-T7-K2"]
    assert l["buoc"] == "giong" and "hết giọng" in thay_kenh.viec_cua_ban(goc)[0]["chu"]
    assert "TLx-T7-K3" not in mo_kenh.doc_trang_thai(goc)["kenh"]


def test_moi_ngay_toi_da_mot_luot_thay(goc):
    _dung_may(goc, so_giong=4)
    _vm_cfg(goc, ["TLa-T7", "TLx-T7-K2", "TLz-T7"])
    _kenh(goc, "TLz-T7")
    _bang(goc, "TLz-T7", [3] * 10)
    _chay(goc)
    assert len(thay_kenh.doc_so(goc)["luot"]) == 1 and not kenh_mod.da_tra_kho(goc, "TLz-T7")
    _chay(goc, bay_gio=NOW + dt.timedelta(days=1))
    assert len(thay_kenh.doc_so(goc)["luot"]) == 2 and kenh_mod.da_tra_kho(goc, "TLz-T7")


def test_tat_cong_tac(goc):
    _dung_may(goc)
    (Path(goc) / "workspace").mkdir(exist_ok=True)
    (Path(goc) / "workspace" / "cai-dat.json").write_text('{"thay_kenh_tu_dong": false}', encoding="utf-8")
    assert not thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    assert not kenh_mod.da_tra_kho(goc, "TLx-T7-K2")


# ── 5) mo_kenh.kich_hoat: kênh thay tự động ─────────────────────────────────────
def test_kich_hoat_kenh_thay_doi_thuong_hieu_va_11_tren_11(goc):
    cha = Path(goc).parent
    p = _kenh(goc, "TLx-T7-K3", "tu_duyet: false\n") / "kenh.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("tu_chay: true", "tu_chay: false"), encoding="utf-8")
    exe = _chrome(cha, "TLx-T7-K3") / "TLx-T7-K3.exe"
    st = mo_kenh.doc_trang_thai(goc)
    st["kenh"]["TLx-T7-K3"] = {"trang_thai": "cho_chrome", "tu_dong": True, "can_thuong_hieu": True, "chrome_kho": "g"}
    mo_kenh.luu_trang_thai(goc, st)
    ghep = []
    so = {"trang_thai": "xong", "muc": {"m{0}".format(i): {"tt": "dat"} for i in range(10)}}
    chung = dict(them_vao_vm=lambda vm, ma, chrome="": ghep.append(ma), doc_so=lambda m: so, log=lambda s: None,
                 bay_gio=NOW, kiem_dang_nhap=lambda e: (True, ""))
    r = mo_kenh.kich_hoat(goc, "TLx-T7-K3", **chung)
    assert r["trang_thai"] == "cho_chrome" and "thương hiệu" in r["ly_do"] and not ghep
    logs = Path(goc) / "vm" / "logs"
    (logs / "tao-kenh").mkdir(parents=True)
    (logs / "tao-kenh" / "TLx-T7-K3.json").write_text('{"ket_qua": "da_co", "uc": "UCbbbbbbbbbbbbbbbbbbbbbb"}', encoding="utf-8")
    (logs / "kenh-uc.json").write_text('{"TLx-T7-K3": "UCbbbbbbbbbbbbbbbbbbbbbb"}', encoding="utf-8")
    r = mo_kenh.kich_hoat(goc, "TLx-T7-K3", **chung)
    assert r["trang_thai"] == "dang_thiet_lap" and ghep == ["TLx-T7-K3"] and exe.is_file()
    from core import vm_cai_dat
    assert vm_cai_dat.doc(goc, "TLx-T7-K3").get("tu_dang") is False                       # chưa bật tự đăng
    r = mo_kenh.kich_hoat(goc, "TLx-T7-K3", **chung)                                     # 10/11 → chưa bật
    assert r["trang_thai"] == "dang_thiet_lap" and "10/11" in r["ly_do"]
    assert str(mo_kenh._kenh_yaml(goc, "TLx-T7-K3").get("tu_chay")).lower() == "false"
    so["muc"]["m10"] = {"tt": "dat"}
    r = mo_kenh.kich_hoat(goc, "TLx-T7-K3", **chung)
    y = mo_kenh._kenh_yaml(goc, "TLx-T7-K3")
    assert r["trang_thai"] == "xong" and str(y.get("tu_chay")).lower() == "true" and str(y.get("tu_duyet")).lower() == "true"
    assert vm_cai_dat.doc(goc, "TLx-T7-K3").get("tu_dang") is True


def test_chuan_bi_kenh_thay_giong_khac_moi_kenh_dang_chay(goc):
    """`giong_rieng`: cấm giọng của MỌI kênh đang chạy (không chỉ cùng tệp); giọng kênh trả kho được dùng lại."""
    _kenh(goc, "TLa-T7")                                        # nhóm g1, tệp t1, voice V-TLa-T7
    _kenh(goc, "TLb-T7", 'nhom_cu: "khac"\n')
    _kenh(goc, "TLy-T7", 'tra_kho: "2026-10-19"\n')
    cam = thay_kenh.giong_dang_dung(goc, tru="MOI")
    assert "V-TLa-T7" in cam and "V-TLb-T7" in cam and "V-TLy-T7" not in cam


# ── 6) skill + agent nạp nóng ───────────────────────────────────────────────────
def test_skill_d20():
    from core import ky_nang
    k = ky_nang.theo_ma("D20")
    assert k and k.toan_may and k.tu_ap and k.dieu_kien is not None and not k.nang
    assert k.chay("G", "")[-2:] == ["core.thay_kenh", "chay"]


def _nap_agent(tmp_path):
    spec = importlib.util.spec_from_file_location("agent_thay_kenh", GOC_REPO / "vm" / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC = str(tmp_path / "vm")
    mod.THU_MUC_TIEN_ICH = str(tmp_path / "tien-ich")
    return mod


def test_agent_nap_nong_kenh_moi_noi_duoi(tmp_path, monkeypatch):
    ag = _nap_agent(tmp_path)
    ghi = []
    monkeypatch.setattr(ag, "ghi", ghi.append)
    monkeypatch.setattr(ag, "bao_dam_tien_ich", lambda ch: "")
    monkeypatch.setattr(ag, "ghi_che_do_mat_cao", lambda *a, **k: None)
    cau_hinh = {"cac_kenh": ["A", "B"]}
    cac = ["A", "B"]
    hl = {k: ag.cau_hinh_kenh(cau_hinh, k) for k in cac}
    them = ag.nap_kenh_moi(cau_hinh, cac, hl, doc=lambda: {"cac_kenh": ["A", "B", "C"]})
    assert them == ["C"] and cac == ["A", "B", "C"] and "C" in hl
    assert ag._cong_devtools(hl["C"], "C") == ag.CONG_DEVTOOLS_GOC + 2
    assert ag.nap_kenh_moi(cau_hinh, cac, hl, doc=lambda: {"cac_kenh": ["A", "B", "C"]}) == []
    # đổi thứ tự / gỡ kênh → không nạp (cổng DevTools theo vị trí)
    assert ag.nap_kenh_moi(cau_hinh, cac, hl, doc=lambda: {"cac_kenh": ["B", "A", "C", "D"]}) == [] and cac == ["A", "B", "C"]


def test_agent_tim_chrome_kenh_tra_kho_trong_kho(tmp_path):
    ag = _nap_agent(tmp_path)
    tool = tmp_path / "MyTool"
    (tool / "CHANNEL").mkdir(parents=True)
    ag.GOC = str(tool / "vm")
    _chrome(tmp_path / "kho", "TLy-T7")
    assert ag.tim_chrome({"kenh": "TLy-T7"}).endswith(os.path.join("kho", "TLy-T7", "TLy-T7.exe"))
