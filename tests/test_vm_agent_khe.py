"""`vm/agent.py` giữ khe "nang" qua `core/khe.py` (Đợt 1.5, 29/09/2026).

Dựng một MyTool giả trong `tmp_path` (vps.json + core/khe.py thật + vm/), trỏ
`agent.GOC` vào đó — không đụng `.khoa-may` thật.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import time

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _nap_agent(tmp_path, co_khe=True):
    duong = os.path.join(GOC_KHO, "vm", "agent.py")
    spec = importlib.util.spec_from_file_location("vm_agent_khe_{0}".format(time.time_ns()), duong)
    ag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ag)
    (tmp_path / "vps.json").write_text("{}", encoding="utf-8")
    (tmp_path / "vm").mkdir(exist_ok=True)
    if co_khe:
        (tmp_path / "core").mkdir(exist_ok=True)
        shutil.copyfile(os.path.join(GOC_KHO, "core", "khe.py"),
                        str(tmp_path / "core" / "khe.py"))
    ag.GOC = str(tmp_path / "vm")
    ag._KHOA_MAY_DANG_GIU = False
    return ag


def _khoa(tmp_path):
    return tmp_path / "workspace" / "tu-chay" / ".khoa-may"


def test_giu_qua_khe_ghi_viec_va_nha(tmp_path):
    ag = _nap_agent(tmp_path)
    assert ag.giu_khoa_may_chung(viec="tai_len", kenh="TL1-T7", uu_tien=1) is True
    du = json.loads(_khoa(tmp_path).read_text(encoding="utf-8"))
    assert du["viec"] == "tai_len" and du["kenh"] == "TL1-T7" and du["pid"] == os.getpid()
    assert ag.giu_khoa_may_chung() is True  # gọi lại trong cùng việc: không kẹt
    ag.doi_viec_khoa_may("quet")
    assert json.loads(_khoa(tmp_path).read_text(encoding="utf-8"))["viec"] == "quet"
    ag.nha_khoa_may_chung()
    assert not _khoa(tmp_path).exists()


def test_nhuong_ve_gap_hon_dang_xep_hang(tmp_path):
    ag = _nap_agent(tmp_path)
    cho = tmp_path / "workspace" / "khe" / "cho"
    cho.mkdir(parents=True)
    # vé của một tiến trình SỐNG (chính mình) xin khe nang ở mức P0 (gấp hơn agent P1)
    (cho / "{0}-abcd.json".format(os.getpid())).write_text(json.dumps(
        {"pid": os.getpid(), "id": "abcd", "loai": "nang", "viec": "tai_len",
         "uu_tien": 0, "han": None, "luc_xin": time.time()}), encoding="utf-8")
    assert ag.giu_khoa_may_chung(viec="quet", kenh="TL2-T7", uu_tien=1) is False
    assert not _khoa(tmp_path).exists()


def test_khong_co_khe_thi_lui_ve_khoa_cu(tmp_path):
    ag = _nap_agent(tmp_path, co_khe=False)
    assert ag.giu_khoa_may_chung(viec="quet") is True
    du = json.loads(_khoa(tmp_path).read_text(encoding="utf-8"))
    assert du.get("nguon") == "agent-chrome"
    ag.nha_khoa_may_chung()
    assert not _khoa(tmp_path).exists()


def test_san_xuat_giu_thi_agent_nhuong(tmp_path):
    # Người giữ phải là một TIẾN TRÌNH KHÁC còn sống: từ 29/09/2026 khoá kiểu cũ của
    # CHÍNH tiến trình mình là TÁI NHẬP (xem tests/test_khe_tai_nhap.py).
    import subprocess
    import sys
    con = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        ag = _nap_agent(tmp_path)
        _khoa(tmp_path).parent.mkdir(parents=True, exist_ok=True)
        _khoa(tmp_path).write_text(json.dumps({"pid": con.pid, "viec": "dung",
                                               "bat_dau": time.time()}), encoding="utf-8")
        assert ag.giu_khoa_may_chung(viec="quet") is False
    finally:
        con.kill()
