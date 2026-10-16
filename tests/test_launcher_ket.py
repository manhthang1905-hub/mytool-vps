"""Dọn launcher Chrome Portable KẸT (`vm/launcher_ket.py`) + móc ở cửa canh (`agent._chrome_dang_chay`) và lượt canh
5 phút (`core.van_hanh`). Bảng tiến trình là đồ giả, cổng/giết/pid là seam — không sinh tiến trình thật, không giết gì."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

from core import van_hanh as vh

GOC = Path(__file__).resolve().parent.parent


def _nap(ten, tep):
    spec = importlib.util.spec_from_file_location(ten, GOC / "vm" / tep)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lk = _nap("launcher_ket_thu", "launcher_ket.py")

BO = r"C:\TL\KX-T7"
LAUNCHER = {"pid": 500, "ppid": 4, "ten": "KX-T7.exe", "duong": BO + r"\KX-T7.exe",
            "lenh": '"{0}\\KX-T7.exe" --remote-debugging-port=9302 --remote-allow-origins=*'.format(BO), "tuoi": 4 * 3600}
CHROME_CON = {"pid": 501, "ppid": 500, "ten": "chrome.exe", "duong": BO + r"\App\Chrome-bin\chrome.exe",
              "lenh": '"{0}\\App\\Chrome-bin\\chrome.exe" --user-data-dir="{0}\\Data\\profile"'.format(BO), "tuoi": 4 * 3600}
#: Chrome đã tách khỏi launcher (cha khác) nhưng vẫn chạy từ đúng bộ trình duyệt.
CHROME_TACH = dict(CHROME_CON, pid=777, ppid=12)
#: Chrome của KÊNH KHÁC có tên thư mục bắt đầu giống (KX-T7-K2) — không được tính là con.
CHROME_KENH_KHAC = {"pid": 601, "ppid": 600, "ten": "chrome.exe", "duong": BO + r"-K2\App\Chrome-bin\chrome.exe",
                    "lenh": "", "tuoi": 99}


class _Seam:
    def __init__(self, ds, dap=(), song=True):
        self.ds, self.dap, self.song_pid = ds, set(dap), song
        self.giet_ds, self.nao = [], []

    def kw(self, **them):
        kw = dict(liet_ke=lambda: self.ds, cong_dap_fn=lambda c: c in self.dap, giet=self.giet,
                  song=lambda _p: self.song_pid, co_thu_muc=lambda _d: True,
                  ghi_nao=lambda *a, **k: self.nao.append((a, k)), bay_gio=1_000_000.0)
        kw.update(them)
        return kw

    def giet(self, pid):
        self.giet_ds.append(pid)
        return True


def _goc(tmp_path):
    vm = tmp_path / "vm"
    (vm / "logs").mkdir(parents=True)
    return str(vm), str(tmp_path)


def test_ket_thi_tat_dung_pid_va_ghi_so(tmp_path):
    vm, tool = _goc(tmp_path)
    s = _Seam([LAUNCHER, CHROME_KENH_KHAC])
    dong = []
    kq = lk.don(vm, tool, nguon="thu", ghi=dong.append, **s.kw())
    assert s.giet_ds == [500] and [m["pid"] for m in kq["da_tat"]] == [500]
    assert "9302" in kq["da_tat"][0]["ly_do"] and "đã tắt launcher KX-T7.exe" in dong[0]
    so = [json.loads(x) for x in open(os.path.join(vm, "logs", lk.TEN_SO), encoding="utf-8")]
    assert so[0]["pid"] == 500 and so[0]["ket_qua"] == "da_tat" and so[0]["nguon"] == "thu"
    (a, k), = s.nao
    assert a[1:] == ("suc-khoe-may", "sua") and k["khoa"].startswith("launcher-ket|KX-T7.exe|500|")


def test_con_chrome_con_thi_giu(tmp_path):
    vm, tool = _goc(tmp_path)
    for chrome in (CHROME_CON, CHROME_TACH):
        s = _Seam([LAUNCHER, chrome])
        kq = lk.don(vm, tool, **s.kw())
        assert s.giet_ds == [] and kq["giu"][0]["ly_do"].startswith("còn 1 chrome.exe")


def test_cong_dap_thi_giu(tmp_path):
    vm, tool = _goc(tmp_path)
    s = _Seam([LAUNCHER], dap={9302})
    assert lk.don(vm, tool, **s.kw())["giu"][0]["ly_do"] == "cổng 9302 đáp" and s.giet_ds == []
    s = _Seam([dict(LAUNCHER, lenh="")], dap={9305})          # cổng người gọi biết của kênh cũng được hỏi
    assert lk.don(vm, tool, cong_them=(9305,), **s.kw())["giu"] and s.giet_ds == []


def test_launcher_tre_thi_giu(tmp_path):
    vm, tool = _goc(tmp_path)
    s = _Seam([dict(LAUNCHER, tuoi=60)])
    kq = lk.don(vm, tool, **s.kw())
    assert s.giet_ds == [] and "mới bật 60" in kq["giu"][0]["ly_do"]


def test_dang_tai_len_thi_bo_qua_ca_luot(tmp_path):
    vm, tool = _goc(tmp_path)
    s = _Seam([LAUNCHER])
    Path(vm, "logs", "dang-dodang.json").write_text(json.dumps({"kenh": "KX", "pid": 42}), encoding="utf-8")
    kq = lk.don(vm, tool, **s.kw())
    assert "đăng dở" in kq["bo_qua"] and s.giet_ds == [] and not kq["da_tat"]
    # dấu đăng dở của chủ đã chết thì không chặn
    s2 = _Seam([LAUNCHER], song=False)
    assert lk.don(vm, tool, **s2.kw())["da_tat"] and s2.giet_ds == [500]


def test_khoa_may_giu_viec_dang_thi_bo_qua(tmp_path):
    vm, tool = _goc(tmp_path)
    kh = Path(tool, "workspace", "tu-chay")
    kh.mkdir(parents=True)
    (kh / ".khoa-may").write_text(json.dumps({"pid": 43, "viec": "tai_len"}), encoding="utf-8")
    s = _Seam([LAUNCHER])
    assert ".khoa-may" in lk.don(vm, tool, **s.kw())["bo_qua"] and s.giet_ds == []
    (kh / ".khoa-may").write_text(json.dumps({"pid": 43, "viec": "dung"}), encoding="utf-8")   # dựng: không phải đăng
    s = _Seam([LAUNCHER])
    assert lk.don(vm, tool, **s.kw())["da_tat"] and s.giet_ds == [500]


def test_chi_nhan_dung_nep_portable_va_dung_ten(tmp_path):
    vm, tool = _goc(tmp_path)
    la = {"pid": 9, "ppid": 1, "ten": "git.exe", "duong": r"C:\Program Files\Git\git.exe", "lenh": "", "tuoi": 9999}
    s = _Seam([la, LAUNCHER])
    kq = lk.don(vm, tool, co_thu_muc=lambda d: d.startswith(BO), **{k: v for k, v in s.kw().items() if k != "co_thu_muc"})
    assert s.giet_ds == [500] and len(kq["da_tat"]) == 1                 # git.exe trùng tên thư mục nhưng không có App\
    s = _Seam([LAUNCHER])
    assert lk.don(vm, tool, ten_exe="KY-T7.exe", **s.kw())["da_tat"] == [] and s.giet_ds == []


def test_thu_chi_xet_khong_tat_va_khong_doc_duoc_bang(tmp_path):
    vm, tool = _goc(tmp_path)
    s = _Seam([LAUNCHER])
    kq = lk.don(vm, tool, thu=True, **s.kw())
    assert kq["ket"] and s.giet_ds == [] and not s.nao
    kq = lk.don(vm, tool, **_Seam(None).kw(liet_ke=lambda: None))
    assert kq["bo_qua"] == "không đọc được bảng tiến trình"


def test_giet_that_bi_chan_trong_pytest():
    assert lk.giet_pid(999999) is False


# ── móc ở cửa canh agent ────────────────────────────────────────────────────────────────────────────────────────


class _Ra:
    def __init__(self, out):
        self.stdout, self.returncode = out, 0


def test_cua_canh_don_roi_hoi_lai(monkeypatch):
    agent = _nap("vm_agent_launcher", "agent.py")
    con = {"song": True}
    monkeypatch.setattr(agent.subprocess, "run",
                        lambda *a, **k: _Ra("KX-T7.exe   500 Console" if con["song"] else "INFO: No tasks"))
    goi = []

    def don_gia(goc_vm, goc_tool, **kw):
        goi.append(kw["ten_exe"])
        con["song"] = False
        return {"da_tat": [{"pid": 500}]}
    monkeypatch.setattr(agent, "_nap_launcher_ket", lambda: type("M", (), {"don": staticmethod(don_gia)}))
    agent._LAN_XET_LAUNCHER.clear()
    assert agent._chrome_dang_chay(BO + r"\KX-T7.exe") is False and goi == ["KX-T7.exe"]
    # Chrome sống: dọn không tắt gì → vẫn "đang chạy"; lần hỏi kế trong nhịp không xét lại
    con["song"] = True
    monkeypatch.setattr(agent, "_nap_launcher_ket",
                        lambda: type("M", (), {"don": staticmethod(lambda *a, **k: goi.append("x") or {"da_tat": []})}))
    agent._LAN_XET_LAUNCHER.clear()
    assert agent._chrome_dang_chay(BO + r"\KX-T7.exe") is True
    assert agent._chrome_dang_chay(BO + r"\KX-T7.exe") is True and goi.count("x") == 1


# ── lượt canh 5 phút ────────────────────────────────────────────────────────────────────────────────────────────


def test_van_hanh_goi_don_launcher_moi_luot(tmp_path):
    goi = []

    def don_gia(vm, goc, **kw):
        goi.append(kw)
        return {"bo_qua": "", "da_tat": [{"pid": 500, "ten": "KX-T7.exe", "ly_do": "kẹt"}], "tat_hong": [], "ket": [],
                "giu": []}
    ket = vh.mot_luot(str(tmp_path), thanh_phan=[], bay_gio=2_000_000.0, luc_boot=1_000_000.0,
                      ly_do_ban_fn=lambda *a, **k: "", pid_con_song=lambda _p: False, ngu=lambda _s: None,
                      gui_bao=lambda *a, **k: None, ghi_nao=lambda *a, **k: None, don_launcher_fn=don_gia)
    assert goi and goi[0]["nguon"] == "van-hanh" and goi[0]["thu"] is False
    assert ket["launcher"]["da_tat"][0]["pid"] == 500
    assert "Launcher Chrome kẹt: 1 đã tắt" in vh.in_ket_qua(ket, str(tmp_path))


def test_van_hanh_khong_co_vm_thi_bo_qua(tmp_path):
    kq = vh.don_launcher_ket(str(tmp_path))
    assert "không có vm/launcher_ket.py" in kq["bo_qua"] and kq["da_tat"] == []
