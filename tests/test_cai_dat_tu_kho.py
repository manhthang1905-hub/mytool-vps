# -*- coding: utf-8 -*-
"""`vm/cai_dat_tu_kho.py` — cài VPS TỪ BẢN CLONE (Việc 5.1).

Mọi bài dùng `tmp_path`, KHÔNG gọi mạng, KHÔNG chạy `pip`/`schtasks`/
`SETUP.bat` thật — `chay=` giả lập lệnh hệ thống (đúng luật CLAUDE.md 3:
"bài kiểm không được gọi mạng"), và các bài đụng `core.lich_tu_chay` chỉ
`monkeypatch` hai hàm CÔNG KHAI của nó (`dang_ky`/`dang_ky_canh_tram`) —
không tự gọi `schtasks` thật.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _nap():
    spec = importlib.util.spec_from_file_location(
        "cai_dat_tu_kho", os.path.join(GOC, "vm", "cai_dat_tu_kho.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def m():
    return _nap()


def _chay_gia(ghi_lai):
    def _fn(lenh):
        ghi_lai.append(list(lenh))
        return 0, ""
    return _fn


def _dung_du_may(tmp_path, m, *, co_setup=True, co_req_vm=True, co_mau=True):
    """Dựng một cây thư mục MyTool tối giản (scripts/SETUP.bat,
    vm/requirements-vm.txt, vm/config.example.json) trong `tmp_path`."""
    goc = tmp_path / "MyTool"
    (goc / "vm").mkdir(parents=True)
    if co_setup:
        (goc / "scripts").mkdir()
        (goc / "scripts" / "SETUP.bat").write_text("@echo off\r\necho gia\r\n", encoding="ascii")
    if co_req_vm:
        (goc / "vm" / "requirements-vm.txt").write_text("requests\nwebsocket-client\n", encoding="ascii")
    if co_mau:
        (goc / "vm" / "config.example.json").write_text(
            json.dumps({"tram": "", "che_do_phien": False, "kenh": ""}), encoding="utf-8")
    return goc


# ── CAI-DAT-VPS.bat: cùng luật CRLF + ASCII thuần với SETUP.bat/CHAY-QT.bat ──
# (xem tests/test_loi_tat.py::test_file_khoi_dong_phai_crlf_va_thuan_ascii —
# cmd.exe băm nát .bat xuống dòng LF, khách 01/09/2026 dính thật với
# "'M' is not recognized"). Tệp MỚI ở đây không nằm trong danh sách bài kiểm
# đó (không sửa file test hiện có, đúng phạm vi được giao), nên tự kiểm ở
# đây thay vì bỏ trống.


def test_cai_dat_vps_bat_crlf_thuan_va_ascii():
    duong = os.path.join(GOC, "CAI-DAT-VPS.bat")
    assert os.path.isfile(duong), "thiếu CAI-DAT-VPS.bat ở gốc kho"
    b = open(duong, "rb").read()
    assert b.count(b"\n") == b.count(b"\r\n"), "CAI-DAT-VPS.bat có dòng LF trần"
    assert all(byte <= 127 for byte in b), "CAI-DAT-VPS.bat phải thuần ASCII"
    assert b"call \"%~dp0scripts\\SETUP.bat\" < NUL" in b, (
        "phải gọi SETUP.bat với stdin rỗng để pause cuối không treo cửa sổ")


# ── --thu: không làm gì thật ─────────────────────────────────────────────────


def test_thu_khong_ghi_tep_nao(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    dong = []
    ket = m.cai(goc=str(goc), bao=dong.append, thu=True)
    assert ket == {} or all(v in (True, False, "") or isinstance(v, str) for v in ket.values())
    assert not (goc / "vps.json").exists()
    assert not (goc / "DONE").exists()
    assert not (goc / "vm" / "config.json").exists()
    assert not (goc / "CLAUDE.local.md").exists()
    assert any("CHẾ ĐỘ THỬ" in d for d in dong)


# ── SETUP.bat: gọi qua chay=, không có thì báo và bỏ qua (không sập) ────────


def test_chay_setup_bat_goi_qua_chay(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    goi = []
    ok = m.chay_setup_bat(str(goc), bao=lambda _d: None, chay=_chay_gia(goi))
    assert ok is True
    assert goi and goi[0][-1] == str(goc / "scripts" / "SETUP.bat")


def test_chay_setup_bat_thieu_tep_khong_sap(tmp_path, m):
    goc = _dung_du_may(tmp_path, m, co_setup=False)
    dong = []
    ok = m.chay_setup_bat(str(goc), bao=dong.append, chay=_chay_gia([]))
    assert ok is False
    assert any("SETUP.bat" in d for d in dong)


# ── vm/requirements-vm.txt ───────────────────────────────────────────────────


def test_cai_requirements_vm_goi_pip(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    goi = []
    ok = m.cai_requirements_vm("python.exe", str(goc), bao=lambda _d: None, chay=_chay_gia(goi))
    assert ok is True
    assert goi[0][:4] == ["python.exe", "-m", "pip", "install"]
    assert goi[0][-1].endswith("requirements-vm.txt")


def test_cai_requirements_vm_thu_khong_goi(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    goi = []
    ok = m.cai_requirements_vm("python.exe", str(goc), bao=lambda _d: None,
                               chay=_chay_gia(goi), thu=True)
    assert ok is True
    assert goi == []


def test_cai_requirements_vm_that_bai_thu_lai_3_lan(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    goi = []

    def _luon_loi(lenh):
        goi.append(list(lenh))
        return 1, "loi gia"

    ok = m.cai_requirements_vm("python.exe", str(goc), bao=lambda _d: None, chay=_luon_loi)
    assert ok is False
    assert len(goi) == 3


# ── vps.json ─────────────────────────────────────────────────────────────


def test_ghi_vps_json_dung_duong_tuong_doi(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    duong = m.ghi_vps_json(str(goc), bao=lambda _d: None)
    assert os.path.isfile(duong)
    with open(duong, encoding="utf-8") as tep:
        du = json.load(tep)
    assert du["vm_dir"] == "vm"


def test_ghi_vps_json_thu_khong_ghi(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.ghi_vps_json(str(goc), bao=lambda _d: None, thu=True)
    assert not (goc / "vps.json").exists()


# ── vm/config.json từ vm/config.example.json ─────────────────────────────


def test_dat_vm_config_tao_moi_tu_mau(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    cai = m.dat_vm_config(str(goc), bao=lambda _d: None)
    duong = goc / "vm" / "config.json"
    assert duong.is_file()
    with open(duong, encoding="utf-8") as tep:
        du = json.load(tep)
    assert du["tram"] == "http://127.0.0.1:8765"
    assert du["che_do_phien"] is True
    assert cai["tram"] == "http://127.0.0.1:8765"


def test_dat_vm_config_giu_nguyen_cau_hinh_da_co(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    duong = goc / "vm" / "config.json"
    duong.write_text(json.dumps({
        "tram": "http://127.0.0.1:8765", "che_do_phien": True,
        "kenh": "TL9-T7", "cac_kenh": ["TL9-T7", "TL10-T7"],
    }), encoding="utf-8")
    m.dat_vm_config(str(goc), bao=lambda _d: None)
    with open(duong, encoding="utf-8") as tep:
        du = json.load(tep)
    assert du["kenh"] == "TL9-T7"
    assert du["cac_kenh"] == ["TL9-T7", "TL10-T7"]


def test_dat_vm_config_bao_dam_trong_cau_hinh_cu_thieu_khoa(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    duong = goc / "vm" / "config.json"
    duong.write_text(json.dumps({"kenh": "TL9-T7"}), encoding="utf-8")
    m.dat_vm_config(str(goc), bao=lambda _d: None)
    with open(duong, encoding="utf-8") as tep:
        du = json.load(tep)
    assert du["tram"] == "http://127.0.0.1:8765"
    assert du["che_do_phien"] is True
    assert du["kenh"] == "TL9-T7"


def test_dat_vm_config_thu_khong_ghi(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.dat_vm_config(str(goc), bao=lambda _d: None, thu=True)
    assert not (goc / "vm" / "config.json").exists()


# ── DONE/ ────────────────────────────────────────────────────────────────


def test_tao_thu_muc_done(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.tao_thu_muc_done(str(goc), bao=lambda _d: None)
    assert (goc / "DONE").is_dir()


# ── CLAUDE.local.md: luật riêng máy (luật chung ở CLAUDE.md) ──────────────


def test_dat_ho_so_phat_trien_sinh_claude_local(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    noi_dung = (goc / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "tối đa 10" in noi_dung
    assert (goc / "NHAT-KY-PHAT-TRIEN.md").is_file()
    assert (goc / "workspace" / "ban-va").is_dir()


def test_dat_ho_so_phat_trien_doi_so_kenh_toi_da(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.dat_ho_so_phat_trien(str(goc), so_kenh_toi_da=7, bao=lambda _d: None)
    noi_dung = (goc / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "tối đa 7" in noi_dung
    assert "tối đa 10" not in noi_dung


def test_dat_ho_so_phat_trien_doc_repo_tu_cap_nhat_json(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    (goc / "cap-nhat.json").write_text(json.dumps({"repo": "vidu/kho-rieng"}), encoding="utf-8")
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    noi_dung = (goc / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "vidu/kho-rieng" in noi_dung
    assert "cấu hình trong `cap-nhat.json`" not in noi_dung  # đã bị thay bằng repo thật


def test_dat_ho_so_phat_trien_tro_luat_chung_claude_md(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    assert "`CLAUDE.md`" in (goc / "CLAUDE.local.md").read_text(encoding="utf-8")


def test_dat_ho_so_phat_trien_giu_ban_nguoi_da_sua(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    (goc / "CLAUDE.local.md").write_text("# Luật riêng\n- mạng chỉ IPv6\n", encoding="utf-8")
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    assert "mạng chỉ IPv6" in (goc / "CLAUDE.local.md").read_text(encoding="utf-8")


def test_dat_ho_so_phat_trien_thay_ban_chep_tu_khuon_cu(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    (goc / "CLAUDE.local.md").write_text(m._DAU_BAN_CU + "\n\nluật cũ trùng CLAUDE.md\n",
                                         encoding="utf-8")
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    moi = (goc / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "luật cũ trùng" not in moi and moi.startswith(m._TIEU_DE_LOCAL)


def test_dat_ho_so_phat_trien_khong_co_cap_nhat_json_van_doc_duoc(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    noi_dung = (goc / "CLAUDE.local.md").read_text(encoding="utf-8")
    # Không có cap-nhat.json thì giữ nguyên câu mặc định, KHÔNG lộ token thô.
    assert "__REPO" not in noi_dung and "__SO_KENH" not in noi_dung


def test_dat_ho_so_phat_trien_khong_ghi_de_nhat_ky_da_co(tmp_path, m):
    goc = _dung_du_may(tmp_path, m)
    duong_nk = goc / "NHAT-KY-PHAT-TRIEN.md"
    duong_nk.write_text("noi dung cu, dung dung vao", encoding="utf-8")
    m.dat_ho_so_phat_trien(str(goc), bao=lambda _d: None)
    assert duong_nk.read_text(encoding="utf-8") == "noi dung cu, dung dung vao"


# ── 5 lịch qua core/lich_tu_chay (chỉ GỌI hàm có sẵn, không gọi schtasks thật) ─


@pytest.fixture(autouse=True)
def _lich_gia(monkeypatch):
    """Mọi bài trong tệp này: KHÔNG bao giờ gọi `schtasks` thật. Hai lịch
    điều phối + gác tổng mặc định giả OK; bài nào cần thì tự thay."""
    from core import lich_tu_chay
    goi = {}

    def _dieu_phoi(g, *a, **k):
        goi["dieu_phoi"] = g
        return True, "ok3"

    def _gac_tong(g, *a, **k):
        goi["gac_tong"] = g
        return True, "ok4"

    monkeypatch.setattr(lich_tu_chay, "dang_ky_dieu_phoi", _dieu_phoi)
    monkeypatch.setattr(lich_tu_chay, "dang_ky_gac_tong", _gac_tong)
    return goi


def test_dang_ky_lich_goi_du_nam_viec(tmp_path, m, monkeypatch, _lich_gia):
    goc = _dung_du_may(tmp_path, m)
    from core import lich_tu_chay

    goi = {}

    def _fake_dang_ky(g, gio, **kw):
        goi["dang_ky"] = (g, gio)
        return True, "ok1"

    def _fake_canh(g, phut, **kw):
        goi["canh_tram"] = (g, phut)
        return True, "ok2"

    monkeypatch.setattr(lich_tu_chay, "dang_ky", _fake_dang_ky)
    monkeypatch.setattr(lich_tu_chay, "dang_ky_canh_tram", _fake_canh)

    ok = m.dang_ky_lich(str(goc), gio="03:30", phut_canh=7, bao=lambda _d: None)
    assert ok is True
    assert goi["dang_ky"] == (str(goc), "03:30")
    assert goi["canh_tram"] == (str(goc), 7)
    assert _lich_gia == {"dieu_phoi": str(goc), "gac_tong": str(goc)}


def test_dang_ky_lich_thu_khong_goi_gi(tmp_path, m, monkeypatch):
    goc = _dung_du_may(tmp_path, m)
    from core import lich_tu_chay

    def _no_call(*a, **k):
        raise AssertionError("không được gọi khi --thu")

    monkeypatch.setattr(lich_tu_chay, "dang_ky", _no_call)
    monkeypatch.setattr(lich_tu_chay, "dang_ky_canh_tram", _no_call)
    monkeypatch.setattr(lich_tu_chay, "dang_ky_dieu_phoi", _no_call)
    monkeypatch.setattr(lich_tu_chay, "dang_ky_gac_tong", _no_call)
    ok = m.dang_ky_lich(str(goc), bao=lambda _d: None, thu=True)
    assert ok is True


def test_dang_ky_lich_mot_ham_hong_khong_sap(tmp_path, m, monkeypatch):
    goc = _dung_du_may(tmp_path, m)
    from core import lich_tu_chay
    monkeypatch.setattr(lich_tu_chay, "dang_ky", lambda g, gio, **k: (False, "hong"))
    monkeypatch.setattr(lich_tu_chay, "dang_ky_canh_tram", lambda g, phut, **k: (True, "ok"))
    ok = m.dang_ky_lich(str(goc), bao=lambda _d: None)
    assert ok is False  # tổng hợp False, nhưng không ném ngoại lệ


# ── Dây chuyền đầy đủ, tất cả seam đều giả ──────────────────────────────────


def test_cai_day_chuyen_day_du_khong_dung_mang(tmp_path, m, monkeypatch):
    goc = _dung_du_may(tmp_path, m)
    from core import lich_tu_chay
    monkeypatch.setattr(lich_tu_chay, "dang_ky", lambda g, gio, **k: (True, "ok"))
    monkeypatch.setattr(lich_tu_chay, "dang_ky_canh_tram", lambda g, phut, **k: (True, "ok"))

    goi = []
    dong = []
    ket = m.cai(goc=str(goc), bao=dong.append, chay=_chay_gia(goi))

    assert ket["setup_bat"] is True
    assert ket["lich"] is True
    assert (goc / "vps.json").is_file()
    assert (goc / "DONE").is_dir()
    assert (goc / "vm" / "config.json").is_file()
    assert (goc / "CLAUDE.local.md").is_file()
    assert any("XONG" in d for d in dong)
