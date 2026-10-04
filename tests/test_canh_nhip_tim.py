"""Nhịp tim agent + gác tổng + luồng canh tiến trình con + trần thời gian con (sự cố 04/10/2026)."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import canh_tien_trien as ct  # noqa: E402
from core import gac_tong  # noqa: E402


def _agent():
    spec = importlib.util.spec_from_file_location("vm_agent_nhip", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ghi_va_doc_nhip_tim(tmp_path, monkeypatch):
    a = _agent()
    monkeypatch.setattr(a, "GOC", str(tmp_path))
    a.nhip_tim("bước: thử", ep=True)
    d = json.loads((tmp_path / "logs" / "nhip-tim.json").read_text(encoding="utf-8"))
    assert d["buoc"] == "bước: thử" and d["pid"] > 0 and abs(d["luc"] - time.time()) < 5


def _nhip(goc, tuoi_phut, pid=4242, buoc="bước: quét ngày"):
    (goc / "vm" / "logs").mkdir(parents=True, exist_ok=True)
    now = dt.datetime(2026, 10, 4, 18, 0)
    (goc / "vm" / "logs" / "nhip-tim.json").write_text(json.dumps(
        {"pid": pid, "luc": now.timestamp() - tuoi_phut * 60, "buoc": buoc}), encoding="utf-8")
    return now


def _chay(tmp_path, tuoi, dang_tai, monkeypatch, song=True):
    monkeypatch.setattr(gac_tong, "_pid_con_song", lambda p: song)
    now = _nhip(tmp_path, tuoi)
    da_giet = []
    ra = gac_tong.tu_sua_agent_treo(tmp_path, bay_gio=now, giet=lambda p: da_giet.append(p) or True,
                                    dang_tai=lambda g: dang_tai, la_agent=lambda p: True)
    return ra, da_giet


def test_nhip_moi_khong_giet(tmp_path, monkeypatch):
    assert _chay(tmp_path, 5, False, monkeypatch) == ([], [])


def test_nhip_cu_khong_tai_len_thi_giet_va_ghi_su_co(tmp_path, monkeypatch):
    ra, giet = _chay(tmp_path, 25, False, monkeypatch)
    assert giet == [4242] and "agent treo" in ra[0]["chuyen_gi"] and "quét ngày" in ra[0]["chuyen_gi"]


def test_dang_tai_len_cu_30_phut_khong_giet(tmp_path, monkeypatch):
    assert _chay(tmp_path, 30, True, monkeypatch) == ([], [])


def test_dang_tai_len_cu_70_phut_thi_giet(tmp_path, monkeypatch):
    assert _chay(tmp_path, 70, True, monkeypatch)[1] == [4242]


def test_pid_da_chet_khong_giet(tmp_path, monkeypatch):
    assert _chay(tmp_path, 40, False, monkeypatch, song=False) == ([], [])


def test_canh_tien_trien_dong_chrome_roi_thoat():
    ct.danh_dau()
    ct._LUC[0] -= 16 * 60
    log, thoat = [], []
    assert ct.kiem_mot_lan(15 * 60, lambda: log.append("dong"), thoat.append, log.append)
    assert "dong" in log and thoat == [ct.MA_TREO]


def test_canh_tien_trien_con_tien_trien_thi_khong_thoat():
    ct.danh_dau()
    thoat = []
    assert not ct.kiem_mot_lan(15 * 60, lambda: thoat.append("x"), thoat.append)
    assert thoat == []


class _Con:
    def __init__(self):
        self.killed = False

    def poll(self):
        return None

    def kill(self):
        self.killed = True


def test_tran_thoi_gian_tien_trinh_con(monkeypatch):
    a = _agent()
    dong = []
    monkeypatch.setattr(a, "dong_chrome_kenh", lambda ch: dong.append(ch))
    monkeypatch.setattr(a, "ghi", lambda s: None)
    monkeypatch.setitem(sys.modules, a.__name__, a)
    import nuoi_trang_chu as n
    monkeypatch.setattr(n, "cau_hinh_kenh_moi", lambda ag, k: {"kenh": k})
    cu, moi = _Con(), _Con()
    con = {"TL2": cu, "TL5": moi}
    bd = {"TL2": 1000.0, "TL5": 1000.0 + 119 * 60}
    ra = a.dung_con_qua_tran(con, bd, 1000.0 + 121 * 60, ten="nuôi")
    assert ra == ["TL2"] and cu.killed and not moi.killed and dong == [{"kenh": "TL2"}] and list(con) == ["TL5"]
