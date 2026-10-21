"""22/10/2026 — HỒI SINH kênh trả kho (`core/thay_kenh.py` lượt `hoi_sinh`, `core/giong_moi.py`): bản sao nguyên kênh cũ,
mã kế cùng dòng, Chrome kho mới, giọng ElevenLabs MỚI (đo ky_tu_moi_phut), lượt thay thật ưu tiên Chrome, tối đa 3 lượt
mở/ngày. Mọi thứ trong tmp; Chrome, DOM, TTS thay bằng hàm giả. Mã kênh/giọng là mã giả."""

from __future__ import annotations

import csv
import datetime as dt
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

from core import giong_moi, kho_chrome, mo_kenh, thay_kenh, tra_kho  # noqa: E402

NOW = dt.datetime(2026, 10, 23, 9, 0)
RANH = (lambda *a: "")
G1, G2, G3, G4 = ("FAKEVOICEAAAA0000001", "FAKEVOICEBBBB0000002", "FAKEVOICECCCC0000003", "FAKEVOICEDDDD0000004")
CU_VOICE = "FAKEVOICEOLD00000099"


@pytest.fixture()
def goc(tmp_path):
    g = tmp_path / "MyTool"
    (g / "vm").mkdir(parents=True)
    return str(g)


def _kenh(goc, ma, voice, them="", ky=274):
    d = Path(goc) / "CHANNEL" / ma
    d.mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text(
        'ma: "{0}"\nten: "x"\nngon_ngu: "ja"\nnhom: "g1"\ntep: "t1"\nvoice_id: "{1}"\nky_tu_moi_phut: {2}\n'
        'tu_chay: true\nthiet_lap_kenh: true\nnuoi_trang_chu: true\ngio_dang: "20:00"\n{3}'.format(ma, voice, ky, them),
        encoding="utf-8")
    return d


def _tra(goc, ma, voice=CU_VOICE, hoi=True, ngay="2026-10-19"):
    d = _kenh(goc, ma, voice, 'tra_kho: "{0}"\nthay_boi: "{1}-K2"\n{2}'.format(ngay, ma, "hoi_sinh: true\n" if hoi else ""))
    p = d / "kenh.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("tu_chay: true", "tu_chay: false"), encoding="utf-8")
    (d / "thiet-lap").mkdir()
    (d / "thiet-lap" / "ho-so.json").write_text(json.dumps({"ten": "Kênh cũ", "handle": "@kenhcu",
                                                            "mo_ta": "あ" * 300 + "。" + "い" * 100}), encoding="utf-8")
    (d / "nv").mkdir()
    (d / "nv" / "nv1.png").write_bytes(b"PNG")
    (d / "style.yaml").write_text('default_character_lock: "nhân vật cũ"\n', encoding="utf-8")
    return d


def _bang(goc, ma, hien_thi):
    d = Path(goc) / "CHANNEL" / ma / "chi-so"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "bang-tom-tat.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Tiêu đề", "Mã video", "Ngày đăng", "Dài", "Mốc mới nhất", "Lượt hiển thị", "Lượt xem"])
        for i, h in enumerate(hien_thi):
            w.writerow(["t", "AAAAAAAAA{0:02d}".format(i), "2026-10-10", "10:00", "200h", str(h), "1"])
    os.utime(p, (NOW.timestamp(), NOW.timestamp()))


def _chrome(cha, ten, dang_nhap=(".google.com", "SID")):
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


def _giong(goc, *ds):
    k = Path(goc).parent / "kho"
    k.mkdir(exist_ok=True)
    (k / "giong-moi.txt").write_text("# giọng mới\n" + "\n".join(ds) + "\n", encoding="utf-8")


def _may(goc):
    """Dòng TLx-T7 đã trả kho (hoi_sinh) + kênh thay TLx-T7-K2 đang chạy dùng lại giọng cũ."""
    (Path(goc) / "vm" / "config.json").write_text(json.dumps({"cac_kenh": ["TLx-T7-K2"]}), encoding="utf-8")
    _tra(goc, "TLx-T7")
    _kenh(goc, "TLx-T7-K2", CU_VOICE, ky=274)
    _bang(goc, "TLx-T7-K2", [5000] * 12)


def _do_gia(goc_, voice, cu, ma="", log=print):
    return {"ky_tu_moi_phut": 281, "cpm_moi": 345.0, "cpm_tham_chieu": 337.0, "kenh_tham_chieu": cu, "luc": "x"}


def _chay(goc, **kw):
    log = []
    kw.setdefault("tra", lambda g, ma, **k: tra_kho.tra(g, ma, ban=RANH, **k))
    kw.setdefault("nhip_chrome", lambda g: tra_kho.nhip_chrome(g, ban=RANH))
    kw.setdefault("do_giong", _do_gia)
    ma = thay_kenh.chay(goc, bay_gio=kw.pop("bay_gio", NOW), log=log.append, **kw)
    return ma, log


def _tao_kenh_ok(g, ma):
    logs = Path(g) / "vm" / "logs"
    (logs / "tao-kenh").mkdir(parents=True, exist_ok=True)
    (logs / "tao-kenh" / (ma + ".json")).write_text(json.dumps({"ket_qua": "ok", "uc": "UCcccccccccccccccccccccc", "ten": "Kênh cũ"}),
                                                    encoding="utf-8")
    (logs / "kenh-uc.json").write_text(json.dumps({ma: "UCcccccccccccccccccccccc"}), encoding="utf-8")
    return 0


# ── 1) sổ giọng mới ─────────────────────────────────────────────────────────────
def test_giong_moi_doc_tep_cap_lan_luot_khong_dung_lai(goc):
    _kenh(goc, "TLa-T7", G1)                                                     # G1 kênh đang chạy dùng
    _tra(goc, "TLx-T7", voice=G2)                                                 # G2 kênh trả kho ghi → cũng cấm
    _giong(goc, "{0}  # trùng kênh chạy".format(G1), "sai-dang", G2, "{0} # nữ".format(G3), G3, G4)
    assert [x["voice_id"] for x in giong_moi.doc_ds(goc)] == [G1, G2, G3, G4]
    assert giong_moi.con_lai(goc) == [G3, G4]
    a = giong_moi.cap(goc, "TLx-T7-K3", NOW)
    assert a["voice_id"] == G3 and a["ghi_chu"] == "nữ"
    assert giong_moi.cap(goc, "TLx-T7-K3", NOW)["voice_id"] == G3                # chạy lại: cùng giọng
    assert giong_moi.cap(goc, "TLy-T7-K4", NOW)["voice_id"] == G4
    assert giong_moi.cap(goc, "TLz-T7-K2", NOW) is None                           # hết
    assert {x["voice_id"]: x["tt"] for x in giong_moi.xet(goc)} == {G1: "dang_dung", G2: "dang_dung", G3: "da_giao", G4: "da_giao"}
    giong_moi.ghi_do(goc, G3, 281, {"cpm_moi": 1})
    assert giong_moi.cap(goc, "TLx-T7-K3")["ky_tu_moi_phut"] == 281


def test_do_ky_tu_moi_phut_theo_ti_le_giong_tham_chieu(goc):
    _tra(goc, "TLx-T7")                                                           # ky 274, mô tả 401 ký tự
    goi = []

    def doc(v, chu, ngon_ngu, dich):
        goi.append((v, ngon_ngu))
        return 60.0 if v == G1 else 62.0                                          # giọng mới nhanh hơn
    kq = giong_moi.do_ky_tu_moi_phut(goc, G1, "TLx-T7", ma="TLx-T7-K3", doc=doc, log=lambda s: None)
    assert goi == [(G1, "ja"), (CU_VOICE, "ja")]
    assert kq["ky_tu_moi_phut"] == round(274 * 62.0 / 60.0) and kq["so_ky_tu"] == 401
    assert (Path(goc) / "workspace" / "mo-kenh" / "do-giong" / "TLx-T7-K3" / "so-do.json").is_file()
    with pytest.raises(RuntimeError):                                             # số đo lạ → không nhận
        giong_moi.do_ky_tu_moi_phut(goc, G1, "TLx-T7", doc=lambda v, c, n, d: 10.0 if v == G1 else 60.0, log=lambda s: None)
    assert giong_moi.cat_mau("あ。" * 600).endswith("。") and len(giong_moi.cat_mau("あ。" * 600)) <= giong_moi.DAI_MAU_TOI_DA


# ── 2) luồng hồi sinh từ đầu đến cuối ───────────────────────────────────────────
def test_hoi_sinh_tu_dau_den_cuoi(goc, monkeypatch):
    cha = Path(goc).parent
    _may(goc)
    bao = []
    monkeypatch.setattr(thay_kenh, "_bao", lambda g, loai, td, ct, kenh="": bao.append((loai, td)))
    assert thay_kenh.hang_hoi_sinh(goc) == ["TLx-T7"]
    # kho chưa có Chrome mới: không mở lượt, MỘT việc người, nhịp sau không chạy lại vô ích
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    so = thay_kenh.doc_so(goc)
    assert not [l for l in so["luot"].values() if l.get("loai") == "hoi_sinh"]
    v = thay_kenh.viec_cua_ban(goc)
    assert len(v) == 1 and "hồi sinh" in v[0]["chu"] and "TLx-T7" in v[0]["chu"]
    assert thay_kenh.can_lam(goc, NOW) == (False, "không có việc thay kênh")
    # chủ thả Chrome đã đăng nhập + tệp giọng (giọng đầu đang có kênh dùng → bỏ qua)
    _chrome(cha / "kho", "gmail-moi")
    _giong(goc, CU_VOICE, G1)
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    l = thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]
    assert l["moi"] == "TLx-T7-K3" and l["buoc"] == "thuong_hieu" and l["chrome_kho"] == "gmail-moi"
    assert l["giong"] == {"voice_id": G1, "ky_tu_moi_phut": 281}
    assert (cha / "TLx-T7-K3" / "TLx-T7-K3.exe").is_file() and not (cha / "kho" / "gmail-moi").exists()
    d = mo_kenh.doc_trang_thai(goc)["kenh"]["TLx-T7-K3"]
    assert d["hoi_sinh"] and d["giu_nguyen"] and d["kenh_goc"] == "TLx-T7" and mo_kenh.la_giu_nguyen(d)
    assert mo_kenh.giong_cua_hang(d)["voice_id"] == G1 and mo_kenh.giong_cua_hang(d)["ky_tu_moi_phut"] == 281
    assert not thay_kenh.viec_cua_ban(goc)
    # bản sao nguyên kênh cũ, chỉ đổi danh tính + giọng mới
    mo_kenh.nhan_ban_giu_nguyen(goc, "TLx-T7-K3", "TLx-T7", d, NOW)
    y = mo_kenh._kenh_yaml(goc, "TLx-T7-K3")
    assert y["voice_id"] == G1 and int(y["ky_tu_moi_phut"]) == 281 and y["thay_cho"] == "TLx-T7"
    assert str(y["hoi_sinh"]).lower() == "false" and not y.get("tra_kho") and y["gio_dang"] == "20:00"
    assert str(y["tu_chay"]).lower() == "false"
    nv = Path(goc) / "CHANNEL" / "TLx-T7-K3"
    assert (nv / "nv" / "nv1.png").is_file() and "nhân vật cũ" in (nv / "style.yaml").read_text(encoding="utf-8")
    assert thay_kenh.hang_hoi_sinh(goc) == []                                       # đã có lượt: không mở đôi
    # mo_kenh chuẩn bị xong → tạo kênh thương hiệu → cho_mo_kenh → xong
    st = mo_kenh.doc_trang_thai(goc)
    st["kenh"]["TLx-T7-K3"].update(trang_thai="cho_chrome", ten_goi_y="Kênh cũ", handle="@kenhcu-jp")
    mo_kenh.luu_trang_thai(goc, st)
    _chay(goc, chay_tao_kenh=_tao_kenh_ok)
    assert thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]["buoc"] == "cho_mo_kenh"
    st = mo_kenh.doc_trang_thai(goc)
    st["kenh"]["TLx-T7-K3"]["trang_thai"] = "xong"
    mo_kenh.luu_trang_thai(goc, st)
    cu_truoc = (Path(goc) / "CHANNEL" / "TLx-T7" / "kenh.yaml").read_text(encoding="utf-8")
    _chay(goc, chay_tao_kenh=_tao_kenh_ok)
    assert thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]["buoc"] == "xong"
    y = mo_kenh._kenh_yaml(goc, "TLx-T7")
    assert str(y["hoi_sinh"]).lower() == "false" and y["hoi_sinh_thanh"] == "TLx-T7-K3"
    cu_sau = (Path(goc) / "CHANNEL" / "TLx-T7" / "kenh.yaml").read_text(encoding="utf-8")
    khac = set(cu_truoc.splitlines()) ^ set(cu_sau.splitlines())
    assert all(x.startswith(("hoi_sinh:", "hoi_sinh_thanh:")) for x in khac)           # không đụng khoá khác
    assert [b[0] for b in bao] == ["hoi_sinh_xong"]
    _chay(goc, chay_tao_kenh=_tao_kenh_ok)
    assert [b[0] for b in bao] == ["hoi_sinh_xong"] and thay_kenh.hang_hoi_sinh(goc) == []


def test_het_giong_cho_mot_viec_khong_lay_chrome(goc):
    cha = Path(goc).parent
    _may(goc)
    _chrome(cha / "kho", "gmail-moi")
    _chay(goc)
    l = thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]
    assert l["buoc"] == "giong" and not l.get("chrome_kho") and (cha / "kho" / "gmail-moi").is_dir()
    v = thay_kenh.viec_cua_ban(goc)
    assert len(v) == 1 and v[0]["khoa"] == thay_kenh.KHOA_CAN_GIONG and "giong-moi.txt" in v[0]["goi_y"]
    assert not thay_kenh.can_lam(goc, NOW)[0]
    _giong(goc, G2)
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    l = thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]
    assert l["buoc"] == "thuong_hieu" and l["giong"]["voice_id"] == G2


def test_do_giong_hong_thi_loi_va_thu_lai(goc):
    _may(goc)
    _chrome(Path(goc).parent / "kho", "gmail-moi")
    _giong(goc, G1)

    def hong(*a, **k):
        raise RuntimeError("ví tạm lỗi")
    ma, _ = _chay(goc, do_giong=hong)
    l = thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]
    assert ma == thay_kenh.MA_LOI and l["buoc"] == "do_giong" and "ví tạm lỗi" in l["loi"] and not l.get("chrome_kho")
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    assert thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]["buoc"] == "thuong_hieu"


def test_thay_that_uu_tien_chrome_hon_hoi_sinh(goc):
    cha = Path(goc).parent
    _may(goc)
    (Path(goc) / "vm" / "config.json").write_text(json.dumps({"cac_kenh": ["TLx-T7-K2", "TLb-T7"]}), encoding="utf-8")
    _kenh(goc, "TLb-T7", G4)
    _bang(goc, "TLb-T7", [12, 15, 9, 11, 63, 4, 18, 41, 23, 10])                    # kênh đang chạy HỎNG
    _chrome(cha / "kho", "gmail-moi")
    _chrome(cha, "TLb-T7")
    _giong(goc, G1)
    _chay(goc)
    so = thay_kenh.doc_so(goc)
    assert so["luot"]["TLb-T7"]["chrome_kho"] == "gmail-moi"                          # lượt thay thật lấy Chrome
    assert "hoi_sinh:TLx-T7" not in so["luot"] and so["hoi_sinh_cho"]["ds"] == ["TLx-T7"]
    assert any("hồi sinh" in x["chu"] for x in thay_kenh.viec_cua_ban(goc))
    _chrome(cha / "kho", "gmail-moi-2")
    assert thay_kenh.can_lam(goc, NOW)[0]
    _chay(goc)
    assert thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLx-T7"]["chrome_kho"] == "gmail-moi-2"


def test_toi_da_ba_luot_mo_moi_ngay_ma_ke_cung_dong(goc):
    cha = Path(goc).parent
    (Path(goc) / "vm" / "config.json").write_text(json.dumps({"cac_kenh": []}), encoding="utf-8")
    for ma in ("TLa-T7", "TLb-T7-K2", "TLc-T7-K2", "TLd-T7"):
        _tra(goc, ma)
    _kenh(goc, "TLb-T7-K3", "FAKEVOICEXXXX0000007")                               # dòng TLb đã có K2, K3 → K4
    for i in range(4):
        _chrome(cha / "kho", "gmail-{0}".format(i))
    _giong(goc, G1, G2, G3, G4)
    _chay(goc)
    so = thay_kenh.doc_so(goc)
    hs = {l["cu"]: l for l in so["luot"].values() if l.get("loai") == "hoi_sinh"}
    assert sorted(hs) == ["TLa-T7", "TLb-T7-K2", "TLc-T7-K2"]
    assert {k: l["moi"] for k, l in hs.items()} == {"TLa-T7": "TLa-T7-K2", "TLb-T7-K2": "TLb-T7-K4", "TLc-T7-K2": "TLc-T7-K3"}
    assert len({l["giong"]["voice_id"] for l in hs.values()}) == 3 and len({l["chrome_kho"] for l in hs.values()}) == 3
    assert thay_kenh.hang_hoi_sinh(goc) == ["TLd-T7"] and so["hoi_sinh_xet"]["dung"] == "gioi_han_ngay"
    assert thay_kenh.can_lam(goc, NOW) == (False, "không có việc thay kênh")
    mai = NOW + dt.timedelta(days=1)
    assert thay_kenh.can_lam(goc, mai)[0]
    _chay(goc, bay_gio=mai)
    assert thay_kenh.doc_so(goc)["luot"]["hoi_sinh:TLd-T7"]["chrome_kho"] == "gmail-3"


def test_ke_hoach_chi_doc(goc):
    _may(goc)
    truoc = sorted(str(p) for p in Path(goc).parent.rglob("*"))
    d = "\n".join(thay_kenh.ke_hoach_hoi_sinh(goc))
    assert "TLx-T7 (trả kho 2026-10-19) → TLx-T7-K3" in d and "CẦN Chrome mới" in d and "CẦN giọng mới" in d
    assert "đo theo giọng TLx-T7 (274" in d
    assert sorted(str(p) for p in Path(goc).parent.rglob("*")) == truoc              # không ghi gì


# ── 3) biến thể tên/handle khi hộp Tạo kênh không nhận ──────────────────────────
def test_bien_the_thuong_hieu(goc):
    assert thay_kenh.bien_the_ten("心の話", "ja") == "心の話ch" and thay_kenh.bien_the_ten("Story", "en") == "Story 2"
    assert thay_kenh.bien_the_handle("@abc") == "@abc-2" and thay_kenh.bien_the_handle("abc-jp-2") == "@abc-jp-3"
    _kenh(goc, "TLx-T7-K3", G1)
    st = mo_kenh.doc_trang_thai(goc)
    st["kenh"]["TLx-T7-K3"] = {"trang_thai": "cho_chrome", "ten_goi_y": "心の話", "handle": "@kokoro-jp"}
    mo_kenh.luu_trang_thai(goc, st)
    l = {"cu": "TLx-T7", "moi": "TLx-T7-K3"}
    tu_choi = {"ket_qua": "hong", "ly_do": "không mở/gõ/bấm được hộp thoại tạo kênh (handle có thể đã có người dùng)"}
    di = lambda k: thay_kenh._bien_the_thuong_hieu(goc, l, "TLx-T7-K3", k, lambda s: None)  # noqa: E731
    assert not di(tu_choi) and di(tu_choi)
    d = mo_kenh.doc_trang_thai(goc)["kenh"]["TLx-T7-K3"]
    assert d["handle"] == "@kokoro-jp-2" and d["ten_goi_y"] == "心の話"
    assert not di(tu_choi) and di(tu_choi)
    d = mo_kenh.doc_trang_thai(goc)["kenh"]["TLx-T7-K3"]
    assert d["handle"] == "@kokoro-jp-3" and d["ten_goi_y"] == "心の話ch"
    assert not l.get("cho_nguoi")
    assert not di(tu_choi) and not di(tu_choi)                                        # tối đa 2 cấp → việc người
    assert l["cho_nguoi"]["khoa"] == "thay-kenh:tao-kenh:TLx-T7-K3"
    l2 = {"cu": "a", "moi": "TLx-T7-K3"}
    da_bam = dict(tu_choi, da_bam_tao={"luc": "x"})                                     # đã bấm Tạo → không đổi (tránh trùng)
    assert not thay_kenh._bien_the_thuong_hieu(goc, l2, "TLx-T7-K3", da_bam, print)
    assert not thay_kenh._bien_the_thuong_hieu(goc, l2, "TLx-T7-K3", da_bam, print)


# ── 4) mo_kenh.chuan_bi: kênh hồi sinh dùng giọng mới đã đo, thiếu giọng thì không dựng ─────
def test_chuan_bi_kenh_hoi_sinh_giong_moi(goc):
    from core import thiet_lap_kenh as tl
    _tra(goc, "TLx-T7")
    hang = {"tep": "t1", "nhom": "g1", "loai": thay_kenh.LOAI_MO_KENH, "kenh_goc": "TLx-T7", "tu_dong": True,
            "giu_nguyen": True, "can_thuong_hieu": True, "hoi_sinh": True}
    chung = dict(goi=lambda p, **k: "{}", tao_anh=lambda p, dich, **k: None,
                 tao_ho_so=lambda kenh, g, **kw: tl.doc_ho_so(kenh, g),
                 kiem_handle=lambda h: h != "kenhcu", chep_chrome=lambda g, m, log=print, **k: ("da_chep", "giả"),
                 gieo=lambda *a, **k: None, log=lambda s: None, bay_gio=NOW)
    mo_kenh.luu_trang_thai(goc, {"kenh": {"TLx-T7-K3": dict(hang, trang_thai="de_xuat", kiem_cuoi=0, loi="")}})
    with pytest.raises(RuntimeError):                                              # chưa có giọng mới → không dùng giọng cũ
        mo_kenh.chuan_bi(goc, "TLx-T7-K3", **chung)
    assert not (Path(goc) / "CHANNEL" / "TLx-T7-K3").exists()
    hang["giong"] = {"voice_id": G1, "ky_tu_moi_phut": 281}
    mo_kenh.luu_trang_thai(goc, {"kenh": {"TLx-T7-K3": dict(hang, trang_thai="de_xuat", kiem_cuoi=0, loi="")}})
    d = mo_kenh.chuan_bi(goc, "TLx-T7-K3", **chung)
    y = mo_kenh._kenh_yaml(goc, "TLx-T7-K3")
    assert d["voice_id"] == G1 and y["voice_id"] == G1 and int(y["ky_tu_moi_phut"]) == 281
    assert y["thay_cho"] == "TLx-T7" and str(y["hoi_sinh"]).lower() == "false" and d["ten_goi_y"] == "Kênh cũ"
    assert d["handle"] != "@kenhcu"                                                 # handle cũ đã có chủ → biến thể
