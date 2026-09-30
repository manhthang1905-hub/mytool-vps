"""`vm/setup_oauth.py` — luồng OAuth từng kênh cho NGƯỜI KHÔNG BIẾT LẬP TRÌNH.

`vm/tokens/` và `vm/clients/` đang TRỐNG trên máy này (chưa OAuth kênh nào) —
mọi bài dưới đây chỉ kiểm phần LOGIC KIỂM TRA (đủ/thiếu điều kiện) và không
được gọi mạng, không mở Chrome thật (đúng luật cứng của phiên vá này). Phần
mở Chrome/chạy OAuth thật (`may_cmt.setup_channel` / `_setup_thu_cong`) không
test được ở đây — cần chạy tay theo `docs/DANG-VA-BINH-LUAN.md`.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent


def _nap(ten_module: str, duong: Path):
    spec = importlib.util.spec_from_file_location(ten_module, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def may_cmt_gia(tmp_path):
    m = _nap("vm_may_cmt_cho_setup", GOC / "vm" / "may_cmt.py")
    vm_gia = tmp_path / "MyTool" / "vm"
    vm_gia.mkdir(parents=True)
    m.BASE_DIR = str(vm_gia)
    m.CLIENTS_DIR = str(vm_gia / "clients")
    m.TOKENS_DIR = str(vm_gia / "tokens")
    os.makedirs(m.CLIENTS_DIR, exist_ok=True)
    os.makedirs(m.TOKENS_DIR, exist_ok=True)
    return m


@pytest.fixture()
def setup_oauth(monkeypatch, may_cmt_gia):
    """Nạp `setup_oauth.py` nhưng ép nó dùng bản `may_cmt` giả (thư mục tạm)
    thay vì module thật đã import sẵn trong tiến trình."""
    import sys

    monkeypatch.setitem(sys.modules, "may_cmt", may_cmt_gia)
    mod = _nap("vm_setup_oauth_test", GOC / "vm" / "setup_oauth.py")
    return mod


def test_thieu_thu_vien_thi_bao_ro_khong_dung_mang(setup_oauth, may_cmt_gia, monkeypatch):
    monkeypatch.setattr(may_cmt_gia, "build", None)
    monkeypatch.setattr(may_cmt_gia, "_THIEU_THU_VIEN", "no module googleapiclient")
    ok, cau = setup_oauth.kiem_tra_truoc("TL1-T7")
    assert ok is False
    assert "CAI-DAT-VPS.bat" in cau


def test_da_co_token_thi_khong_lam_lai(setup_oauth, may_cmt_gia):
    with open(may_cmt_gia.token_path("TL1-T7"), "w", encoding="utf-8") as f:
        f.write("{}")
    ok, cau = setup_oauth.kiem_tra_truoc("TL1-T7")
    assert ok is False
    assert "DA CO token" in cau


def test_thieu_client_secret_thi_tro_toi_huong_dan(setup_oauth, may_cmt_gia):
    ok, cau = setup_oauth.kiem_tra_truoc("TL1-T7")
    assert ok is False
    assert "CHUA co file OAuth client" in cau
    assert "DANG-VA-BINH-LUAN.md" in cau


def test_du_dieu_kien_tra_ve_duong_client(setup_oauth, may_cmt_gia):
    duong_client = os.path.join(may_cmt_gia.CLIENTS_DIR, "TL1-T7.json")
    with open(duong_client, "w", encoding="utf-8") as f:
        f.write('{"installed": {}}')
    ok, ra = setup_oauth.kiem_tra_truoc("TL1-T7")
    assert ok is True
    assert ra == duong_client


def test_khong_go_kenh_thi_bao_cach_dung_khong_gap_loi(setup_oauth, may_cmt_gia, monkeypatch, capsys):
    monkeypatch.setattr(may_cmt_gia, "discover_channels", lambda: [])
    ma = setup_oauth.main([])
    assert ma == 1
    ra = capsys.readouterr().out
    assert "--kenh" in ra


def test_chay_dung_lai_som_khi_thieu_dieu_kien_khong_dung_mang(setup_oauth, capsys):
    """chay() phải DỪNG NGAY ở bước kiểm tra khi thiếu điều kiện — không được
    đụng tới browser/OAuth (không có gì để mock hỏng ở bước sau chứng tỏ nó
    chưa đi tới đó)."""
    ma = setup_oauth.chay("TL-CHUA-CO-GI")
    assert ma == 1
    ra = capsys.readouterr().out
    assert "CHUA co file OAuth client" in ra
