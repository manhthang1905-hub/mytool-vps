"""Hàm THUẦN của `vm/nuoi_trang_chu.py` — không Chrome, không mạng, không LLM."""

from __future__ import annotations

import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

VM = Path(__file__).resolve().parent.parent / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import nuoi_trang_chu as n  # noqa: E402

HOM_NAY = date(2026, 10, 3)


def luc(gio, phut=0, ngay=3):
    return time.mktime((2026, 10, ngay, gio, phut, 0, 0, 0, -1))


def uv(i, ngach, kenh=None, ngay=None, view=100_000, dai=600):
    return {"id": "v%010d" % i, "tieu_de": "t", "kenh": kenh or "K%d" % i, "view": view,
            "ngay": ngay or HOM_NAY - timedelta(days=5), "dai": dai, "ngach": ngach}


# ── chọn video ──────────────────────────────────────────────────────────────
def test_chon_ti_le_ngach_70_30():
    ung = [uv(i, True) for i in range(30)] + [uv(100 + i, False) for i in range(30)]
    ra = n.chon_video(ung, set(), set(), set(), 10, HOM_NAY, random.Random(1))
    assert len(ra) == 10 and sum(1 for v in ra if v["ngach"]) == 7


def test_chon_bu_khi_thieu_nhom():
    ung = [uv(i, True) for i in range(2)] + [uv(100 + i, False) for i in range(30)]
    ra = n.chon_video(ung, set(), set(), set(), 10, HOM_NAY, random.Random(1))
    assert len(ra) == 10 and sum(1 for v in ra if v["ngach"]) == 2


def test_chon_cam_kenh_minh_khong_lap_va_qua_cu():
    ung = [uv(1, True, kenh="Kênh Của Mình"), uv(2, True), uv(3, True), uv(4, True),
           uv(5, True, ngay=HOM_NAY - timedelta(days=61)), uv(6, True, view=0), uv(7, True, dai=60)]
    ra = n.chon_video(ung, {"v0000000002"}, {"v0000000003"}, {"kênh của mình"}, 10, HOM_NAY, random.Random(2))
    assert [v["id"] for v in ra] == ["v0000000004"]


def test_chon_khong_trung_id_va_uu_tien_nhieu_view():
    ung = [uv(1, True), uv(1, True)] + [uv(10 + i, True, view=100) for i in range(40)] + [uv(99, True, view=5_000_000)]
    dem = 0
    for s in range(60):
        ra = n.chon_video(ung, set(), set(), set(), 5, HOM_NAY, random.Random(s))
        assert len({v["id"] for v in ra}) == len(ra)
        dem += any(v["id"] == "v0000000099" for v in ra)
    assert dem > 25            # video 5 triệu view hầu như luôn được chọn


def test_chi_xem_video_thang_khong_bu_video_yeu():
    """03/10: video yếu (view thấp, hoặc không vượt trung vị kênh của nó) KHÔNG được xem, kể cả khi thiếu."""
    kenh_a = [uv(200 + i, True, kenh="A", view=40_000) for i in range(6)]          # video thường của A
    no = uv(300, True, kenh="A", view=200_000)                                      # video nổ của A (≥2× trung vị)
    yeu = [uv(400 + i, True, view=5_000) for i in range(10)]                        # dưới ngưỡng view
    ra = n.chon_video(kenh_a + [no] + yeu, set(), set(), set(), 10, HOM_NAY, random.Random(3))
    assert [v["id"] for v in ra] == [no["id"]]


# ── thời lượng xem ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("dai", [30, 100, 300, 900, 3600, 7200])
def test_thoi_luong_trong_bien(dai):
    for s in range(200):
        x = n.thoi_luong_xem(dai, random.Random(s))
        assert 1 <= x <= n.XEM_TRAN_GIAY and x < dai
        if dai >= 300:
            assert x >= n.XEM_SAN_GIAY
            if dai * 0.85 <= n.XEM_TRAN_GIAY and dai * 0.35 >= n.XEM_SAN_GIAY:
                assert dai * 0.35 - 1 <= x <= dai * 0.85 + 1


def test_tua_khoang_30_phan_tram():
    co = sum(1 for s in range(2000) if n.ke_hoach_xem(900, random.Random(s))["tua"])
    assert 0.2 < co / 2000 < 0.4


# ── khung giờ cấm 02:00–07:00 ───────────────────────────────────────────────
@pytest.mark.parametrize("gio,phut,cam", [
    (1, 59, False), (2, 0, True), (5, 0, True), (6, 59, True), (7, 0, False), (21, 30, False)])
def test_khung_cam(gio, phut, cam):
    assert bool(n.khung_cam(luc(gio, phut))) is cam


def test_khung_cam_tinh_ca_do_dai_phien():
    assert n.khung_cam(luc(0, 30), 90)          # kéo tới 02:00
    assert not n.khung_cam(luc(0, 30), 60)
    assert n.khung_cam(luc(23, 0), 190)         # qua nửa đêm chạm 02:00 hôm sau
    assert not n.khung_cam(luc(21, 0), 90)


# ── quyết định phiên: 40 video/ngày, nghỉ giữa phiên, công tắc ──────────────
def so_dang(**kw):
    so = n.so_moi("K")
    so.update(kw)
    return so


def phien(so_video, ngay="2026-10-03"):
    return {"ngay": ngay, "so_video": so_video, "giay_xem": so_video * 300}


def test_phien_dau_toi_da_15_video():
    assert n.quyet_dinh(so_dang(), luc(10)) == (15, "")


def test_toi_da_40_video_moi_ngay():
    so = so_dang(phien=[phien(15), phien(15)])
    assert n.quyet_dinh(so, luc(20))[0] == 10                  # còn 10 video của hạn mức ngày
    so["phien"].append(phien(10))
    so_v, ly = n.quyet_dinh(so, luc(20))
    assert so_v == 0 and "40" in ly
    assert n.quyet_dinh(so, luc(10, ngay=4))[0] == 15           # sang ngày mới đếm lại


def test_khong_con_gioi_han_2_phien_3_gio_10_ngay():
    so = so_dang(bat_dau="2026-01-01", phien=[phien(5), phien(5), phien(5), phien(5)])
    so["phien"][0]["giay_xem"] = 99999
    assert n.quyet_dinh(so, luc(20))[0] == 15


def test_nghi_20_40_phut_giua_cac_phien():
    for s in range(100):
        x = n.nghi_giua_phien(random.Random(s))
        assert 20 * 60 <= x <= 40 * 60
    assert n.nghi_giua_phien(random.Random(1), bi_ngat=True) == 5 * 60
    so = so_dang(nghi_den_luc=luc(20, 30))
    so_v, ly = n.quyet_dinh(so, luc(20, 0))
    assert so_v == 0 and "nghỉ" in ly
    assert n.quyet_dinh(so, luc(20, 31))[0] == 15


def test_khung_cam_chan_quyet_dinh():
    assert n.quyet_dinh(so_dang(), luc(3))[0] == 0
    assert n.quyet_dinh(so_dang(), luc(6, 30))[0] == 0
    assert n.quyet_dinh(so_dang(), luc(0, 30), 90)[0] == 0      # phiên 90 phút chạm 02:00
    assert n.quyet_dinh(so_dang(), luc(7, 0))[0] == 15


def test_can_nguoi_va_dat_khong_chay():
    assert n.quyet_dinh(so_dang(trang_thai="can_nguoi", ly_do="captcha"), luc(10))[0] == 0
    assert n.quyet_dinh(so_dang(trang_thai="dat"), luc(10))[0] == 0


# ── tối đa 4 Chrome + RAM ───────────────────────────────────────────────────
def test_gioi_han_4_chrome_va_ram():
    assert n.duoc_mo_them(0, 4.0) == ""
    assert n.duoc_mo_them(3, 8.0) == ""
    assert "4 Chrome" in n.duoc_mo_them(4, 20.0)
    assert "RAM" in n.duoc_mo_them(1, 3.9)
    assert "RAM" in n.duoc_mo_them(1, None)


def _dung_kenh(tmp_path, monkeypatch, ten, so_theo_kenh):
    goc = tmp_path / "MyTool"
    goc.mkdir(exist_ok=True)
    for k in ten:
        (tmp_path / k).mkdir(exist_ok=True)
        (tmp_path / k / (k + ".exe")).write_text("x")
    monkeypatch.setattr(n, "cac_kenh_bat", lambda g=None: list(ten))
    monkeypatch.setattr(n, "doc_so", lambda k: so_theo_kenh.get(k) or so_dang())
    monkeypatch.setattr(n, "cac_kenh_dang_nuoi", lambda thu_muc=None: [])
    return str(goc)


def test_kenh_den_luot_cat_o_4_chrome(tmp_path, monkeypatch):
    goc = _dung_kenh(tmp_path, monkeypatch, ["A", "B", "C", "D", "E", "F"], {})
    ra, ly = n.kenh_den_luot(luc(12), (), goc, ram=40.0, nang_ban=False)
    assert ra == ["A", "B", "C", "D"] and "4 Chrome" in ly["E"] and "4 Chrome" in ly["F"]
    ra, ly = n.kenh_den_luot(luc(12), ("A", "B"), goc, ram=40.0, nang_ban=False)    # 2 con đã mở
    assert ra == ["C", "D"] and ly["A"] == "đang nuôi"


def test_kenh_den_luot_kiem_ram_truoc_moi_lan_mo(tmp_path, monkeypatch):
    goc = _dung_kenh(tmp_path, monkeypatch, ["A", "B", "C"], {})
    ra, ly = n.kenh_den_luot(luc(12), (), goc, ram=5.5, nang_ban=False)
    assert ra == ["A", "B"] and "RAM" in ly["C"]               # mỗi Chrome ước ~1 GB
    ra, ly = n.kenh_den_luot(luc(12), (), goc, ram=3.0, nang_ban=False)
    assert ra == [] and all("RAM" in v for v in ly.values())


def test_kenh_den_luot_nhuong_khi_khe_nang_ban_va_khung_cam(tmp_path, monkeypatch):
    goc = _dung_kenh(tmp_path, monkeypatch, ["A", "B"], {"B": so_dang(trang_thai="dat")})
    ra, ly = n.kenh_den_luot(luc(12), (), goc, ram=40.0, nang_ban=True)
    assert ra == [] and "bận" in ly["A"] and "đã đạt" in ly["B"]
    ra, ly = n.kenh_den_luot(luc(3), (), goc, ram=40.0, nang_ban=False)
    assert ra == [] and "khung cấm" in ly["A"]


def test_kenh_den_luot_thieu_chrome(tmp_path, monkeypatch):
    goc = _dung_kenh(tmp_path, monkeypatch, ["A"], {})
    (tmp_path / "A" / "A.exe").unlink()
    ra, ly = n.kenh_den_luot(luc(12), (), goc, ram=40.0, nang_ban=False)
    assert ra == [] and "Chrome Portable" in ly["A"]


# ── tiêu chí đạt: % chủ đề > 90%, 1 lần ─────────────────────────────────────
def test_phan_tram():
    r = n.phan_tram(["dung_ngach"] * 6 + ["dung_chu_de"] * 4)
    assert r["n"] == 10 and r["pct_chu_de"] == 100.0 and r["pct_ngach"] == 60.0
    r = n.phan_tram(["dung_ngach"] * 3 + ["dung_chu_de"] * 4 + ["lac_de"] * 3)
    assert r["pct_chu_de"] == 70.0 and r["pct_ngach"] == 30.0
    assert n.phan_tram([])["n"] == 0


def test_tieu_chi_dat_90_phan_tram():
    assert n.dat_tieu_chi(100, 0, 30)               # % ngách không là điều kiện
    assert n.dat_tieu_chi(93.3, 0, 30)
    assert not n.dat_tieu_chi(90.0, 100, 30)        # phải LỚN HƠN 90
    assert not n.dat_tieu_chi(96.7, 80, 5)          # quá ít ô thì không tính


def ket(chu_de, ngach, nn=30):
    return {"n": nn, "pct_chu_de": chu_de, "pct_ngach": ngach, "dem": {}, "vi_du_lac_de": []}


def test_mot_lan_do_dat_la_dat():
    so = n.so_moi("K")
    n.ghi_lan_do(so, ket(80, 60), "2026-10-03 10:00")
    assert so["trang_thai"] == "dang_nuoi"
    n.ghi_lan_do(so, ket(93.3, 3.3), "2026-10-03 20:00")
    assert so["trang_thai"] == "dat" and so["dat_luc"] == "2026-10-03 20:00" and len(so["lan_do"]) == 2
    assert so["lan_do"][-1]["pct_ngach"] == 3.3     # % ngách vẫn ghi để xem


# ── tự ghi false vào kenh.yaml ──────────────────────────────────────────────
def test_tat_nuoi_ghi_false_giu_crlf_va_uu_tien_channel(tmp_path):
    ch = tmp_path / "CHANNEL" / "K"
    nhap = tmp_path / "workspace" / "chuan-bi-K" / "CHANNEL" / "K"
    for d in (ch, nhap):
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_bytes(b'ma: "K"\r\nnuoi_trang_chu: true\r\nkhac: 1\r\n')
    assert n.cac_kenh_bat(str(tmp_path)) == ["K"]
    d = n.tat_nuoi("K", str(tmp_path))
    assert d == str(ch / "kenh.yaml")
    assert (ch / "kenh.yaml").read_bytes() == b'ma: "K"\r\nnuoi_trang_chu: false\r\nkhac: 1\r\n'
    assert b"true" in (nhap / "kenh.yaml").read_bytes()         # CHANNEL thắng, nháp không đụng
    assert n.cac_kenh_bat(str(tmp_path)) == []                  # CHANNEL tắt thì kênh không còn được nuôi (nháp true bị bỏ qua)
    assert not n.doc_kenh_yaml("K", str(tmp_path))["bat"]
    assert n.tat_nuoi("K", str(tmp_path)) == d                  # gọi lại không hỏng


def test_tat_nuoi_dung_ban_nhap_khi_chua_co_channel(tmp_path):
    nhap = tmp_path / "workspace" / "chuan-bi-K" / "CHANNEL" / "K"
    nhap.mkdir(parents=True)
    (nhap / "kenh.yaml").write_text("nuoi_trang_chu: true\n", encoding="utf-8")
    assert n.tat_nuoi("K", str(tmp_path)) == str(nhap / "kenh.yaml")
    assert (nhap / "kenh.yaml").read_text(encoding="utf-8") == "nuoi_trang_chu: false\n"
    assert n.cac_kenh_bat(str(tmp_path)) == []


# ── khoá RIÊNG THEO KÊNH + cờ dừng ──────────────────────────────────────────
def test_khoa_theo_kenh(tmp_path, monkeypatch):
    d = str(tmp_path)
    sống = {123}
    monkeypatch.setattr(n, "pid_con_song", lambda p: p in sống or p == __import__("os").getpid())
    assert n.giu_khoa("A", d) and n.chu_khoa("A", d) == __import__("os").getpid()
    assert not n.giu_khoa("A", d)                               # kênh A đã có người giữ
    assert n.giu_khoa("B", d)                                   # kênh khác thì được
    (tmp_path / "C.khoa").write_text('{"pid": 123}')            # tiến trình khác còn sống giữ C
    assert not n.giu_khoa("C", d)
    sống.discard(123)                                           # nó chết → khoá bị dọn, giành được
    assert n.giu_khoa("C", d)
    assert n.giu_khoa("_mo", d)
    assert sorted(n.cac_kenh_dang_nuoi(d)) == ["A", "B", "C"]    # khoá `_mo` không tính là Chrome nuôi
    n.nha_khoa("A", d)
    assert n.chu_khoa("A", d) == 0 and not (tmp_path / "A.khoa").exists()


def test_co_dung(tmp_path):
    d = str(tmp_path)
    assert not n.co_dung("K", d)
    (tmp_path / "K.dung").write_text("1")
    assert n.co_dung("K", d)
    n.xoa_co_dung("K", d)
    assert not n.co_dung("K", d)


# ── nhường việc đăng / khe nang ─────────────────────────────────────────────
def test_ly_do_dung_nhuong_viec_dang_va_khe_nang(tmp_path, monkeypatch):
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path))
    monkeypatch.setattr(n, "khe_nang_ban", lambda goc_tool=None: False)
    monkeypatch.setattr(n, "viec_dang_cho", lambda ag, t, k: "")
    t = luc(12)
    assert n.ly_do_dung(None, "K", t) == ""
    (tmp_path / "K.dung").write_text("1")
    assert "cờ" in n.ly_do_dung(None, "K", t)                   # agent đòi Chrome kênh → dừng
    n.xoa_co_dung("K", str(tmp_path))
    monkeypatch.setattr(n, "khe_nang_ban", lambda goc_tool=None: True)
    assert "bận" in n.ly_do_dung(None, "K", t)
    monkeypatch.setattr(n, "khe_nang_ban", lambda goc_tool=None: False)
    monkeypatch.setattr(n, "viec_dang_cho", lambda ag, t, k: "kênh K có gói chờ tải lên")
    assert "tải lên" in n.ly_do_dung(None, "K", t)
    monkeypatch.setattr(n, "viec_dang_cho", lambda ag, t, k: "")
    assert "khung cấm" in n.ly_do_dung(None, "K", luc(3))


def test_ma_video_va_ten():
    assert n.ma_video("https://www.youtube.com/watch?v=WATghdSAZ4g&t=1") == "WATghdSAZ4g"
    assert n.chuan_ten(" Ｋ ênh ") == n.chuan_ten("kênh")


# ── chỗ nối ở agent ─────────────────────────────────────────────────────────
def _nap_agent(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("vm_agent_ntc", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "GOC", str(tmp_path))
    logs = []
    monkeypatch.setattr(mod, "ghi", logs.append)
    mod._NUOI_TRANG_CHU.update(luc=0.0, con={}, ly={})
    return mod, logs


class _Con:
    def __init__(self, ma=None):
        self.returncode = ma

    def poll(self):
        return self.returncode


def test_agent_moi_kenh_mot_tien_trinh_con_va_ghi_ly_do_khi_doi(tmp_path, monkeypatch):
    mod, logs = _nap_agent(tmp_path, monkeypatch)
    ly = {"B": "nghỉ giữa phiên, còn 25 phút"}
    monkeypatch.setattr(n, "kenh_den_luot", lambda t, dang=(), goc=None, **k: ([x for x in ("A", "C") if x not in dang], dict(ly)))
    monkeypatch.setattr(mod, "van_ipv4_mo", lambda: False)
    lenh = []
    mo = lambda cmd, **kw: (lenh.append(cmd), _Con())[1]
    assert mod.chay_nuoi_trang_chu(100000.0, mo_con=mo) == 2
    assert [c[-1] for c in lenh] == ["A", "C"] and lenh[0][1].endswith("nuoi_trang_chu.py")
    assert sum("bỏ qua" in x and "kênh B" in x for x in logs) == 1
    assert mod.chay_nuoi_trang_chu(100000.0 + 300, mo_con=mo) == 2          # chưa tới 10 phút: im lặng
    ly["B"] = "nghỉ giữa phiên, còn 15 phút"                                 # chỉ đổi số đếm lùi: KHÔNG ghi lại
    mod.chay_nuoi_trang_chu(100000.0 + 700, mo_con=mo)
    assert sum("kênh B" in x and "bỏ qua" in x for x in logs) == 1
    ly["B"] = "khe nang của máy đang bận"                                    # lý do đổi thật: ghi
    mod.chay_nuoi_trang_chu(100000.0 + 1400, mo_con=mo)
    assert sum("kênh B" in x and "bỏ qua" in x for x in logs) == 2
    assert len(lenh) == 2                                                    # đang chạy thì không mở thêm con


def test_agent_con_xong_duoc_don_va_van_ipv4_hoan(tmp_path, monkeypatch):
    mod, logs = _nap_agent(tmp_path, monkeypatch)
    monkeypatch.setattr(n, "kenh_den_luot", lambda t, dang=(), goc=None, **k: (["A"], {}))
    monkeypatch.setattr(mod, "van_ipv4_mo", lambda: True)
    assert mod.chay_nuoi_trang_chu(100000.0, mo_con=lambda *a, **k: 1 / 0) == 0
    assert any("van IPv4" in x for x in logs)
    mod._NUOI_TRANG_CHU["con"]["A"] = _Con(30)
    mod.chay_nuoi_trang_chu(100001.0)
    assert not mod._NUOI_TRANG_CHU["con"] and any("xong (mã 30)" in x for x in logs)


def test_agent_nhuong_kenh_nuoi(tmp_path, monkeypatch):
    import json as _j
    import os as _o
    mod, logs = _nap_agent(tmp_path, monkeypatch)
    thu_muc = tmp_path / "logs" / "nuoi-trang-chu"
    thu_muc.mkdir(parents=True)
    assert mod._nhuong_kenh_nuoi("K", 0.05) is True                            # không ai nuôi: đi tiếp ngay
    khoa = thu_muc / "K.khoa"
    khoa.write_text(_j.dumps({"pid": 4242}))
    monkeypatch.setattr(mod, "_pid_con_song", lambda p: False)
    assert mod._nhuong_kenh_nuoi("K", 0.05) is True and not (thu_muc / "K.dung").exists()   # khoá của tiến trình chết
    monkeypatch.setattr(mod, "_pid_con_song", lambda p: True)
    # phiên nuôi chịu dừng: xoá khoá trong lúc agent đợi → agent đi tiếp, cờ .dung đã được ghi
    monkeypatch.setattr(mod.time, "sleep", lambda s: khoa.unlink() if khoa.exists() else None)
    assert mod._nhuong_kenh_nuoi("K", 30) is True
    assert (thu_muc / "K.dung").exists() and any("báo dừng sớm" in x for x in logs)
    # phiên nuôi không chịu đóng trong hạn → hoãn việc đăng
    khoa.write_text(_j.dumps({"pid": 4242}))
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    assert mod._nhuong_kenh_nuoi("K", 0.05) is False
    assert any("hoãn việc" in x for x in logs)


def test_giu_khoa_may_chung_moi_qua_nhuong_kenh_nuoi(tmp_path, monkeypatch):
    mod, _ = _nap_agent(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "_duong_khoa_may_chung", lambda: str(tmp_path / ".khoa-may"))
    goi = []
    monkeypatch.setattr(mod, "_nhuong_kenh_nuoi", lambda k, *a: goi.append(k) or False)
    assert mod.giu_khoa_may_chung(viec="tai_len", kenh="TL1-T7") is False and goi == ["TL1-T7"]


def test_tran_chrome_khi_may_dang_dung_va_cpu(monkeypatch):
    assert n.duoc_mo_them(1, 8.0, True) == ""
    assert "tối đa 2" in n.duoc_mo_them(2, 8.0, True)
    assert n.duoc_mo_them(3, 8.0, False) == ""
    monkeypatch.setattr(n, "khe_nang_viec", lambda goc_tool=None: "dung")
    monkeypatch.setattr(n, "cpu_tong_pct", lambda giay=3.0: 40.0)
    assert n.khe_nang_ban() is False                    # đang dựng nhưng CPU còn dư → vẫn nuôi
    monkeypatch.setattr(n, "cpu_tong_pct", lambda giay=3.0: 80.0)
    assert n.khe_nang_ban() is True
    monkeypatch.setattr(n, "cpu_tong_pct", lambda giay=3.0: 10.0)
    monkeypatch.setattr(n, "khe_nang_viec", lambda goc_tool=None: "tai_len")
    assert n.khe_nang_ban() is True                     # việc đăng giữ khe → nhường tuyệt đối


def test_noi_dung_khac_quoc_gia_la_lac_de_bang_ma():
    """04/10: kênh tiếng Nhật — tiêu đề không có kana (tiếng Việt/Anh/Hàn/Trung) là lạc đề, không cần LLM."""
    assert n.sai_ngon_ngu("Tâm lý học: 5 dấu hiệu người thao túng", "ja")
    assert n.sai_ngon_ngu("5 signs of a narcissist", "ja")
    assert n.sai_ngon_ngu("나르시시스트의 특징", "ja")
    assert not n.sai_ngon_ngu("【心理学】本当に賢い人の特徴", "ja")
    assert not n.sai_ngon_ngu("Tâm lý học tiếng Việt", "vi")        # ngôn ngữ khác: để LLM quyết
    goi_bi_goi = []
    ra = n.phan_loai(lambda p: goi_bi_goi.append(p) or "[]", "ngách", [{"id": "aaaaaaaaaaa", "tieu_de": "Tâm lý học", "kenh": "X"}], {})
    assert ra == {"aaaaaaaaaaa": "lac_de"} and goi_bi_goi == []


def test_chi_bam_khong_quan_tam_khi_chac_chan_lac_de():
    """04/10: video tâm lý tiếng Nhật lệch ngách KHÔNG bị bấm; chỉ bấm khi khác ngôn ngữ hoặc LLM nói không phải tâm lý."""
    c = {"a1": "lac_de", "tl:a1": True, "a2": "lac_de", "tl:a2": False, "a3": "lac_de"}
    assert not n.chac_lac_de({"id": "a1", "tieu_de": "恋愛心理学のすごい話"}, c)      # tâm lý, lệch ngách
    assert n.chac_lac_de({"id": "a2", "tieu_de": "簡単レシピで晩ごはん"}, c)          # LLM: không phải tâm lý
    assert not n.chac_lac_de({"id": "a3", "tieu_de": "ゲーム実況です"}, c)             # chưa biết tam_ly → không bấm
    assert n.chac_lac_de({"id": "a4", "tieu_de": "那些成年後依舊能輕鬆交到真心朋友的人"}, c)   # khác ngôn ngữ (không kana)
