"""Bộ điều phối sản xuất song song (`core/dieu_phoi.py`, 29/09/2026).

Không mạng, không ví, không sinh tiến trình thật — `sinh` là seam; mọi bài dùng
`tmp_path` (không đụng `workspace/khe/` thật).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import time

import pytest

from core import auto, dieu_phoi, khe, ke_hoach_dang


def _vps(goc, **cai):
    with open(os.path.join(goc, "vps.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    du = {"dieu_phoi": True, "lan_api": 2}
    du.update(cai)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump(du, tep)


def _kenh(goc, ma, **cai):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    mac = {"ma": ma, "ngon_ngu": "ja", "engine": "veo3", "phut_muc_tieu": 10,
           "tu_chay": True, "tu_duyet": True, "ngan_sach_ngay": 5000000,
           "nhip_dang": '"12:00, 20:00"', "video_toi_da_ngay": 4}
    mac.update(cai)
    dong = []
    for k, v in mac.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, (int, float)):
            dong.append("{0}: {1}".format(k, v))
        elif isinstance(v, str) and v.startswith('"'):
            dong.append("{0}: {1}".format(k, v))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


def _ke_hoach(goc, ma, *dong_kv):
    hang = []
    for kv in dong_kv:
        d = {ten: "" for ten in ke_hoach_dang.COT}
        d.update(kv)
        hang.append([d[ten] for ten in ke_hoach_dang.COT])
    ke_hoach_dang.luu_bang(goc, ma, hang)


# ── bật/tắt ─────────────────────────────────────────────────────────────────


def test_bat_can_vps_va_co(tmp_path):
    goc = str(tmp_path)
    assert dieu_phoi.bat(goc) is False
    _vps(goc, dieu_phoi=False)
    assert dieu_phoi.bat(goc) is False
    _vps(goc)
    assert dieu_phoi.bat(goc) is True


def test_ghi_cai_giu_khoa_khac(tmp_path):
    goc = str(tmp_path)
    _vps(goc, auto_kenh_cuoi="X")
    dieu_phoi.ghi_cai(goc, lan_api=1)
    du = dieu_phoi.doc_cai(goc)
    assert du["lan_api"] == 1 and du["auto_kenh_cuoi"] == "X" and du["dieu_phoi"] is True


def test_cai_dat_ghi_khong_xoa_khoa_dieu_phoi(tmp_path):
    from core import cai_dat

    goc = str(tmp_path)
    _vps(goc, lan_api=3, ngan_sach_ngay_may=100)
    cai_dat.dat(goc, "auto_kenh_cuoi", "TL1-T7")
    du = dieu_phoi.doc_cai(goc)
    assert du["lan_api"] == 3 and du["dieu_phoi"] is True and du["ngan_sach_ngay_may"] == 100


# ── khe nang quanh khâu B ──────────────────────────────────────────────────


def test_giu_nang_tat_thi_khong_lam_gi(tmp_path):
    goc = str(tmp_path)
    with dieu_phoi.giu_nang(goc, "dung") as h:
        assert h is None
    assert not os.path.exists(khe.duong_khoa_nang(goc))


def test_giu_nang_bat_thi_giu_dung_tep_khoa_may(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    with dieu_phoi.giu_nang(goc, "dung", kenh="K1"):
        du = json.load(open(khe.duong_khoa_nang(goc), encoding="utf-8"))
        assert du["viec"] == "dung" and du["pid"] == os.getpid()
    assert not os.path.exists(khe.duong_khoa_nang(goc))


def test_giu_nang_bam_dung_luc_xep_hang_thanh_cancelled(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _vps(goc)
    # một "tiến trình khác" (PID sống — chính cha của pytest không chắc; dùng PID mình
    # nhưng khác nội dung → khe coi là đang giữ vì pid sống)
    os.makedirs(os.path.dirname(khe.duong_khoa_nang(goc)), exist_ok=True)
    with open(khe.duong_khoa_nang(goc), "w", encoding="utf-8") as tep:
        json.dump({"pid": os.getpid(), "nguon": "khe", "viec": "tai_len"}, tep)
    monkeypatch.setattr(khe, "NHIP_KIEM_MAC_DINH_GIAY", 0.05)
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    with pytest.raises(auto.Cancelled):
        with dieu_phoi.giu_nang(goc, "dung", kenh="K1", cancel=cancel):
            pass


def test_boc_khau_nang_chi_boc_phu_de_va_dung(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    _kenh(goc, "K1")
    da_thay = []

    def dung(luot, tt):
        da_thay.append(json.load(open(khe.duong_khoa_nang(goc), encoding="utf-8"))["viec"])
        return "ok"
    dung.soi_lai = True

    def anh(luot, tt):
        da_thay.append(os.path.exists(khe.duong_khoa_nang(goc)))
        return "anh"

    viec = dieu_phoi.boc_khau_nang({"dung": dung, "anh": anh}, goc=goc, kenh="K1")
    assert viec["anh"] is anh
    assert getattr(viec["dung"], "soi_lai", False) is True
    assert viec["dung"](None, None) == "ok" and viec["anh"](None, None) == "anh"
    assert da_thay == ["dung", False]


def test_thu_nang_ban_thi_bo_qua(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    with dieu_phoi.thu_nang(goc, "nen") as duoc:
        assert duoc is True
        with dieu_phoi.thu_nang(goc, "nen") as duoc2:
            assert duoc2 is False


# ── sổ job chung cắm vào SoTheoDoi ──────────────────────────────────────────


class _TrangGia:
    def __init__(self, data):
        self.data = data


class _ClientGia:
    def __init__(self):
        self.so_lan_list = 0
        self.jobs = self

    def list(self, status=None, limit=None, cursor=None):  # noqa: A003
        self.so_lan_list += 1
        if status == "succeeded":
            return {"data": [{"id": "j1", "status": "succeeded", "output": {"u": 1}},
                             {"id": "j2", "status": "succeeded"}], "has_more": False}
        return {"data": [], "has_more": False}


class _BcGia:
    def __init__(self, goc, client):
        self.goc = goc
        self.client = client
        self.on_log = None
        self.ngu = lambda s: None
        self.nhat = []

    def ghi(self, d):
        self.nhat.append(d)


def test_so_job_chung_hai_so_mot_luot_hoi(tmp_path, monkeypatch):
    from core import auto_khau as ak

    goc = str(tmp_path)
    _vps(goc)
    monkeypatch.setattr(ak.SoTheoDoi, "_mot_luot", ak.SoTheoDoi._mot_luot)
    monkeypatch.setattr(ak, "_tai_ket_qua_mot_lan", ak._tai_ket_qua_mot_lan)
    monkeypatch.setattr(ak, "_noi_mp3", ak._noi_mp3)
    monkeypatch.setattr(ak, "xin_nhip", lambda *a, **k: None)
    monkeypatch.setitem(dieu_phoi._MOC, "da_cai", False)
    assert dieu_phoi.cai_moc_tien_trinh(goc, kenh="K1") is True
    client = _ClientGia()
    s1 = ak.SoTheoDoi(_BcGia(goc, client), nhip=999)
    s2 = ak.SoTheoDoi(_BcGia(goc, client), nhip=999)
    with s1._khoa:
        s1._so["j1"] = {"co": threading.Event(), "goi": None}
    with s2._khoa:
        s2._so["j2"] = {"co": threading.Event(), "goi": None}
    s1._mot_luot()
    s2._mot_luot()
    assert client.so_lan_list == 2  # MỘT vòng (succeeded + failed) cho cả hai sổ
    assert s1._lay("j1")["status"] == "succeeded"
    assert s2._lay("j2")["status"] == "succeeded"


# ── nhịp điều phối ─────────────────────────────────────────────────────────


def test_nhip_sinh_dung_so_lan_cho_kenh_thieu_kho_nhat(tmp_path):
    goc = str(tmp_path)
    _vps(goc, lan_api=2)
    for ma in ("K1", "K2", "K3"):
        _kenh(goc, ma)
    bay_gio = _dt.datetime(2026, 9, 29, 14, 0)
    # K1 đã có 5/6 kho → ít thiếu nhất; K2, K3 trống
    _ke_hoach(goc, "K1", *[{"Mã gói": "K1-{0}".format(i), "Ngày đăng": "0{0}/10/2026".format(i),
                            "Giờ đăng": "20:00", "Sẵn sàng": "x"} for i in range(1, 6)])
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=bay_gio, ram=10.0, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1000 + len(sinh), log=lambda d: None)
    assert sinh == ["K2", "K3"]
    assert ra["lan_trong"] == 2
    # nhịp sau ngay lập tức: hai lượt vừa sinh (PID giả chết) nhưng giãn cách 55'
    sinh.clear()
    ra = dieu_phoi.nhip(goc, bay_gio=bay_gio, ram=10.0, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 2000, log=lambda d: None)
    assert "K2" not in sinh and "K3" not in sinh


def test_nhip_ram_thap_khong_sinh(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    _kenh(goc, "K1")
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=_dt.datetime(2026, 9, 29, 14, 0), ram=2.5, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1, log=lambda d: None)
    assert sinh == [] and "RAM" in ra["chan"]


def test_nhip_may_nghet_ha_lan_api_ve_1(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _vps(goc, lan_api=2)
    _kenh(goc, "K1")
    # K1 đang chạy: khoá kênh do chính tiến trình này giữ (PID sống)
    kh = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(kh), exist_ok=True)
    with open(kh, "w", encoding="utf-8") as tep:
        json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    nhat = []
    ra = dieu_phoi.nhip(goc, bay_gio=_dt.datetime(2026, 9, 29, 14, 0), ram=1.5, dia_gb=30.0,
                        sinh=lambda g, ma: 1, log=nhat.append)
    assert ra.get("ha_lan") is True
    assert dieu_phoi.doc_cai(goc)["lan_api"] == 1
    assert any("NGHẸT" in d for d in nhat)


def test_nhip_tat_thi_khong_lam_gi(tmp_path):
    goc = str(tmp_path)
    assert dieu_phoi.nhip(goc, sinh=lambda g, m: 1) == {"bat": False}


def test_nhip_tran_may_video_ngay(tmp_path):
    goc = str(tmp_path)
    _vps(goc, video_toi_da_ngay_may=1)
    _kenh(goc, "K1")
    so = os.path.join(goc, "CHANNEL", "K1", "tu-chay")
    os.makedirs(so, exist_ok=True)
    with open(os.path.join(so, "2026-09-29.json"), "w", encoding="utf-8") as tep:
        json.dump({"ngay": "2026-09-29", "kenh": "K1", "nhat_ky": [],
                   "runs": [{"ma_luot": "0001", "bo": True, "san_xuat": {"da_chay": True}}]}, tep)
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=_dt.datetime(2026, 9, 29, 14, 0), ram=10.0, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1, log=lambda d: None)
    assert sinh == [] and "trần máy" in ra["chan"]


def test_trang_thai_kenh_luot_do_duoc_uu_tien(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    _kenh(goc, "K1")
    luot = auto.moi_luot(goc, "K1", "0001", {"link": "x", "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)
    so = os.path.join(goc, "CHANNEL", "K1", "tu-chay")
    os.makedirs(so, exist_ok=True)
    with open(os.path.join(so, "2026-09-29.json"), "w", encoding="utf-8") as tep:
        json.dump({"ngay": "2026-09-29", "kenh": "K1", "nhat_ky": [],
                   "runs": [{"ma_luot": "0001", "san_xuat": {"da_chay": True}}]}, tep)
    tt = dieu_phoi.trang_thai_kenh(goc, "K1", bay_gio=_dt.datetime(2026, 9, 29, 14, 0))
    assert tt["chay"] is True and tt["diem"] == -1000.0


def test_bao_tri_kenh_xep_lai_va_tra_dong_trang_thai(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    _kenh(goc, "K1")
    _ke_hoach(goc, "K1", {"Mã gói": "K1-0001", "Ngày đăng": "28/09/2026", "Giờ đăng": "20:00",
                          "Sẵn sàng": "x"})
    nhat = []
    ra = dieu_phoi.bao_tri_kenh(goc, "K1", on_log=nhat.append,
                                bay_gio=_dt.datetime(2026, 9, 29, 14, 0))
    assert ra["ok"] is True and ra["tom_tat"].startswith("K1: [điều phối]")
    assert any("XẾP LẠI LỊCH" in d for d in nhat)
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    d = dict(zip(cot, hang[0]))
    assert (d["Ngày đăng"], d["Giờ đăng"]) == ("30/09/2026", "12:00")


def test_ghi_so_ngay_luot_noi_them(tmp_path):
    from core import tu_chay

    goc = str(tmp_path)
    dieu_phoi.ghi_so_ngay_luot(goc, [{"kenh": "K1", "ok": True, "tom_tat": "K1: xong video"}],
                               tong_uoc_vnd=85800)
    ngay = _dt.date.today().isoformat()
    du = json.load(open(tu_chay.duong_bao_cao_tat_ca(goc, ngay, "json"), encoding="utf-8"))
    assert du["runs"][-1]["tong_uoc_vnd"] == 85800
    assert "K1: xong video" in open(tu_chay.duong_bao_cao_tat_ca(goc, ngay, "md"),
                                    encoding="utf-8").read()


def test_sinh_tien_trinh_lui_khi_breakaway_bi_tu_choi(tmp_path):
    goc = str(tmp_path)
    goi = []

    class _P:
        pid = 4242

    def popen(lenh, **kw):
        goi.append(kw["creationflags"])
        if kw["creationflags"] & 0x01000000:
            raise OSError("access denied")
        return _P()

    assert dieu_phoi.sinh_tien_trinh(goc, "K1", popen=popen) == 4242
    if os.name == "nt":
        assert len(goi) == 2 and not goi[1] & 0x01000000


# ── CLI gốc ────────────────────────────────────────────────────────────────


def _nap_cli():
    import importlib.util

    duong = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tu_chay.py")
    spec = importlib.util.spec_from_file_location("_tu_chay_cli_dieu_phoi", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_cho_lan_qua_han_thoat_ma_3(tmp_path, monkeypatch):
    cli = _nap_cli()
    goc = str(tmp_path)
    _vps(goc)
    monkeypatch.setattr(cli, "BASE_DIR", goc)

    class _Cfg:
        problem = ""

    monkeypatch.setattr(cli, "load_config", lambda p: _Cfg())

    import contextlib

    @contextlib.contextmanager
    def giu_het_gio(*a, **k):
        raise khe.KheHetGio("het")
        yield  # noqa: unreachable

    monkeypatch.setattr(khe, "giu", giu_het_gio)
    assert cli.main(["--kenh", "K1", "--tu-dieu-phoi"]) == 3


def test_dang_ky_lich_dieu_phoi_lech_5_phut(tmp_path):
    from core import lich_tu_chay

    goc = str(tmp_path)
    open(os.path.join(goc, "tu_chay.py"), "w").close()
    goi = []
    ok, _cau = lich_tu_chay.dang_ky_dieu_phoi(goc, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is True
    lenh = goi[0]
    assert lenh[:4] == ["schtasks", "/Create", "/TN", "ShopAPI-DieuPhoi"]
    assert lenh[lenh.index("/MO") + 1] == "10"
    assert lenh[lenh.index("/ST") + 1].endswith("5")
    assert "--dieu-phoi" in lenh[lenh.index("/TR") + 1]

def test_luot_cu_giu_ca_may_khong_tu_khoa_chet(tmp_path):
    """Lượt `--tat-ca` khởi động TRƯỚC khi bật điều phối giữ `.khoa-may` cả lượt
    (PID mình) — bật điều phối giữa chừng không được làm nó chờ chính nó."""
    from core import tu_chay

    goc = str(tmp_path)
    ok, _ = tu_chay.giu_khoa_may(goc)
    assert ok
    _vps(goc)
    bat_dau = time.time()
    with dieu_phoi.giu_nang(goc, "dung", kenh="K1") as h:
        assert h is None
    with dieu_phoi.thu_nang(goc, "nen") as duoc:
        assert duoc is True
    assert time.time() - bat_dau < 2
    assert os.path.exists(khe.duong_khoa_nang(goc))  # vẫn là khoá của lượt cũ
    tu_chay.nha_khoa_may(goc)