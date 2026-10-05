"""Bước kéo chéo trong agent (06/10/2026): 1 lần/ngày, trong khung giờ, không khi có con khác / van IPv4 mở."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm"))
import agent  # noqa: E402


class _Con:
    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -9


def _reset(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "_tep_keo_cheo_ngay", lambda: str(tmp_path / "keo-cheo-ngay.json"))
    monkeypatch.setattr(agent, "van_ipv4_mo", lambda: False)
    monkeypatch.setattr(agent, "ghi", lambda *a, **k: None)
    agent._KEO_CHEO.update({"con": {}, "bd": {}, "ngay": ""})


def _luc(gio):
    return time.mktime((2026, 10, 6, gio, 5, 0, 0, 0, -1))


def test_mot_lan_moi_ngay_trong_khung_gio(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    mo = []
    con = _Con()

    def mo_con(cmd, **k):
        mo.append(cmd)
        return con

    assert agent.chay_keo_cheo(_luc(7), mo_con) == 0 and not mo              # trước 09:00
    assert agent.chay_keo_cheo(_luc(10), mo_con) == 1 and len(mo) == 1
    assert "--ke-hoach" in mo[0] and mo[0][-2].endswith("keo_cheo_dom.py")
    assert json.load(open(tmp_path / "keo-cheo-ngay.json", encoding="utf-8"))["ngay"] == "2026-10-06"
    con.returncode = 0
    assert agent.chay_keo_cheo(_luc(11), mo_con) == 0 and len(mo) == 1         # hôm nay đã chạy
    agent._KEO_CHEO.update({"con": {}, "bd": {}, "ngay": ""})                 # agent khởi động lại → đọc tệp
    assert agent.chay_keo_cheo(_luc(12), mo_con) == 0 and len(mo) == 1


def test_khong_chay_khi_con_khac_hay_ipv4(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    mo = []
    mo_con = lambda cmd, **k: mo.append(cmd) or _Con()  # noqa: E731
    assert agent.chay_keo_cheo(_luc(10), mo_con, con_khac=1) == 0 and not mo
    monkeypatch.setattr(agent, "van_ipv4_mo", lambda: True)
    assert agent.chay_keo_cheo(_luc(10), mo_con) == 0 and not mo


def test_con_qua_tran_bi_dung(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "dong_chrome_kenh", lambda *a, **k: None)
    con = _Con()
    assert agent.chay_keo_cheo(_luc(10), lambda cmd, **k: con) == 1
    assert agent.chay_keo_cheo(_luc(10) + agent.TRAN_KEO_CHEO_GIAY + 5, lambda cmd, **k: con) == 0
    assert con.returncode == -9
