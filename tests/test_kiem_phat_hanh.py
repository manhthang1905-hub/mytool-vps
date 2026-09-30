# -*- coding: utf-8 -*-
"""`core/kiem_phat_hanh.py` — kiểm phát hành v3.0 (Việc 5.3).

TOÀN BỘ bài kiểm chạy trên một **kho Git GIẢ dựng trong `tmp_path`** — không
đụng tới kho MyTool thật, và KHÔNG bài nào tự chạy `pytest` thật (chỉ giả lập
`subprocess.run` khi cần kiểm tham số gọi) — máy này đang có lượt sản xuất
chạy thật, luật "VPS không chạy nặng song song" (`CLAUDE.local.md`) cấm mở
thêm một lượt pytest toàn kho trong phiên này.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

import pytest

from core import kiem_phat_hanh as k


def _git(repo: str, *args: str) -> None:
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "Kiem Phat Hanh", "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Kiem Phat Hanh", "GIT_COMMITTER_EMAIL": "t@t.local",
    })
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)


def _ghi(repo: str, rel: str, noi_dung: str = "") -> str:
    duong = os.path.join(repo, *rel.split("/"))
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(noi_dung)
    return duong


@pytest.fixture
def kho_gia(tmp_path):
    """Một kho Git dựng tay, mô phỏng đúng những lỗ hổng lộ trình v3 mục E:

    - `CLAUDE.local.md` bị THEO DÕI dù `.gitignore` chặn (vá E1).
    - `secrets.json` bị `.gitignore` chặn thật (KHÔNG được vào cây sạch).
    - Một tệp bí mật MỚI (`chua_add.py`, client_secret) chưa `git add` — mô
      phỏng agent khác đang sửa dở, kiểm phát hành vẫn phải bắt được.
    - Dữ liệu kênh thật lọt qua .gitignore (`CHANNEL/TL1/nghien-cuu/doithu.json`
      tracked) và một tệp khuôn được phép (`tuyen.csv`).
    - Một tệp .md chứa đường tuyệt đối `C:\\Users\\...`.
    - Một tệp lớn hơn 5MB.
    """
    repo = str(tmp_path / "kho")
    os.makedirs(repo)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.local")
    _git(repo, "config", "user.name", "Kiem Phat Hanh")

    _ghi(repo, ".gitignore", "CLAUDE.local.md\nsecrets.json\n")
    _ghi(repo, "core/tab_ops.py", "def them(a, b):\n    return a + b\n")
    _ghi(repo, "CHANNEL/TL1/nghien-cuu/doithu.json", '{"ten": "kenh doi thu that"}\n')
    _ghi(repo, "CHANNEL/TL1/nghien-cuu/tuyen.csv", "cot1,cot2\n1,2\n")
    _ghi(repo, "docs/ghi-chu.md", "Cài ở C:\\" "Users\\NguoiDung\\Documents\\TL\\MyTool nhé.\n")
    # Nguồn extension `core/ytb_extension/*.js` là mã dùng chung — không được
    # gắn cờ. Chỉ thư mục con theo mã kênh `vm/tien-ich/<k>/` mới bị chặn.
    _ghi(repo, "core/ytb_extension/khuon.js", "// khuon dung chung\n")
    _ghi(repo, "vm/tien-ich/TL1-T7/cau-hinh.json", '{"rieng": "may that"}\n')
    # CLAUDE.local.md: ghi rồi `git add -f` — mô phỏng đã track TRƯỚC khi có
    # dòng .gitignore chặn nó (đúng ca thật của vá E1).
    _ghi(repo, "CLAUDE.local.md", "# bí mật riêng máy nhà\n")
    _git(repo, "add", "-f", "CLAUDE.local.md")
    _git(repo, "add", "core", "CHANNEL", "docs", ".gitignore")
    _git(repo, "commit", "-q", "-m", "khoi tao")

    # Sau commit: một tệp bí mật thật (bị .gitignore chặn — không được lọt).
    _ghi(repo, "secrets.json", '{"khoa": "that"}\n')
    # Một tệp MỚI, CHƯA `git add` (mô phỏng agent khác đang sửa dở).
    _ghi(repo, "core/chua_add.py",
         'client_secret = "abcdefg' 'hijklmnop1234567890"\n')
    # Một tệp lớn (>5MB).
    _ghi(repo, "data/qua_lon.dat", "x" * (6 * 1024 * 1024))

    return repo


# ── xuat_cay_sach ────────────────────────────────────────────────────────────


def test_xuat_cay_sach_khong_phai_git_worktree(tmp_path):
    with pytest.raises(k.KiemPhatHanhError):
        k.xuat_cay_sach(str(tmp_path))


def test_xuat_cay_sach_dung_du_tep(kho_gia, tmp_path):
    dich = str(tmp_path / "sach")
    cay = k.xuat_cay_sach(kho_gia, thu_muc_dich=dich)

    # Có: tracked + untracked-nhưng-không-bị-.gitignore-chặn.
    assert "core/tab_ops.py" in cay.tep
    assert "core/chua_add.py" in cay.tep  # chưa `git add` nhưng không bị ignore
    assert "CLAUDE.local.md" in cay.tep   # tracked dù .gitignore chặn — đúng lỗ hổng E1
    assert "CLAUDE.local.md" in cay.theo_doi
    assert "core/chua_add.py" not in cay.theo_doi  # chưa add -> chưa "theo dõi"

    # Không có: bị .gitignore chặn thật.
    assert "secrets.json" not in cay.tep

    # Tệp thật sự nằm trên đĩa ở thư mục đích.
    assert os.path.isfile(os.path.join(dich, "core", "tab_ops.py"))


def test_xuat_cay_sach_mac_dinh_ngoai_kho(kho_gia, monkeypatch, tmp_path):
    """Không truyền `thu_muc_dich` thì cây sạch nằm NGOÀI kho nguồn, dưới
    `%LOCALAPPDATA%\\shopapi-kiem-phat-hanh\\<ngày-giờ>\\`."""
    gia_local = str(tmp_path / "localappdata")
    monkeypatch.setenv("LOCALAPPDATA", gia_local)
    cay = k.xuat_cay_sach(kho_gia)
    try:
        assert cay.duong.startswith(gia_local)
        assert not cay.duong.startswith(kho_gia)
    finally:
        import shutil
        shutil.rmtree(cay.duong, ignore_errors=True)


# ── quet_cay_sach ────────────────────────────────────────────────────────────


def test_quet_cay_sach_bat_dung_5_loai(kho_gia, tmp_path):
    dich = str(tmp_path / "sach")
    cay = k.xuat_cay_sach(kho_gia, thu_muc_dich=dich)
    phat_hien = k.quet_cay_sach(cay)
    theo_loai = {}
    for p in phat_hien:
        theo_loai.setdefault(p.loai, set()).add(p.duong)

    assert theo_loai.get("claude_local_md") == {"CLAUDE.local.md"}
    assert "CHANNEL/TL1/nghien-cuu/doithu.json" in theo_loai.get("du_lieu_kenh", set())
    assert "CHANNEL/TL1/nghien-cuu/tuyen.csv" not in theo_loai.get("du_lieu_kenh", set())
    assert "core/chua_add.py" in theo_loai.get("bi_mat", set())
    assert "docs/ghi-chu.md" in theo_loai.get("duong_tuyet_doi", set())
    assert "data/qua_lon.dat" in theo_loai.get("tep_lon", set())
    assert "vm/tien-ich/TL1-T7/cau-hinh.json" in theo_loai.get("du_lieu_kenh", set())
    assert "core/ytb_extension/khuon.js" not in theo_loai.get("du_lieu_kenh", set())

    # Tệp sạch không bị gắn cờ gì.
    assert "core/tab_ops.py" not in {p.duong for p in phat_hien}
    assert "core/ytb_extension/khuon.js" not in {p.duong for p in phat_hien}


def test_quet_cay_sach_rong_khi_sach(tmp_path):
    repo = str(tmp_path / "sach2")
    os.makedirs(repo)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.local")
    _git(repo, "config", "user.name", "T")
    _ghi(repo, "core/ok.py", "x = 1\n")
    _git(repo, "add", "core")
    _git(repo, "commit", "-q", "-m", "ok")

    cay = k.xuat_cay_sach(repo, thu_muc_dich=str(tmp_path / "dich2"))
    assert k.quet_cay_sach(cay) == []


# ── san_sang_chay_pytest ─────────────────────────────────────────────────────


def test_san_sang_ram_thap(monkeypatch):
    monkeypatch.setattr(k, "ram_gb", lambda: (2.0, 16.0))
    san_sang, ly_do = k.san_sang_chay_pytest("/khong/quan/trong")
    assert san_sang is False
    assert "RAM" in ly_do


def test_san_sang_khoa_nang_dang_giu(monkeypatch, tmp_path):
    goc = str(tmp_path)
    duong_khoa = os.path.join(goc, "workspace", "tu-chay", ".khoa-may")
    os.makedirs(os.path.dirname(duong_khoa))
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 4242, "bat_dau": time.time()}, tep)

    monkeypatch.setattr(k, "ram_gb", lambda: (10.0, 16.0))
    monkeypatch.setattr(k, "pid_con_song", lambda pid: pid == 4242)

    san_sang, ly_do = k.san_sang_chay_pytest(goc)
    assert san_sang is False
    assert ".khoa-may" in ly_do or "nang" in ly_do


def test_san_sang_luot_dang_khau_nang(monkeypatch, tmp_path):
    goc = str(tmp_path)
    duong_tt = os.path.join(goc, "PROJECTS", "AUTO", "K1", "0001", "trang-thai.json")
    os.makedirs(os.path.dirname(duong_tt))
    with open(duong_tt, "w", encoding="utf-8") as tep:
        json.dump({"khau": {"dung": {"trang_thai": "dang"}}}, tep)

    monkeypatch.setattr(k, "ram_gb", lambda: (10.0, 16.0))
    monkeypatch.setattr(k, "pid_con_song", lambda pid: False)

    san_sang, ly_do = k.san_sang_chay_pytest(goc)
    assert san_sang is False
    assert "dung" in ly_do


def test_san_sang_ok_khi_ranh(monkeypatch, tmp_path):
    goc = str(tmp_path)
    monkeypatch.setattr(k, "ram_gb", lambda: (10.0, 16.0))
    monkeypatch.setattr(k, "pid_con_song", lambda pid: False)
    san_sang, ly_do = k.san_sang_chay_pytest(goc)
    assert san_sang is True
    assert ly_do == ""


# ── chay_pytest_cay_sach (chỉ kiểm THAM SỐ GỌI, không chạy pytest thật) ──────


def test_chay_pytest_cay_sach_goi_dung_tham_so(monkeypatch, tmp_path):
    cay = k.CaySach(duong=str(tmp_path), tep=(), theo_doi=frozenset())
    bat_duoc = {}

    class _KetQua:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    def _run_gia(cmd, cwd=None, env=None, **kwargs):
        bat_duoc["cmd"] = cmd
        bat_duoc["cwd"] = cwd
        bat_duoc["env"] = env
        bat_duoc["creationflags"] = kwargs.get("creationflags")
        return _KetQua()

    monkeypatch.setattr(k.subprocess, "run", _run_gia)
    ket = k.chay_pytest_cay_sach(cay)

    assert ket.da_chay is True
    assert ket.ma_thoat == 0
    assert bat_duoc["cwd"] == cay.duong
    assert bat_duoc["env"]["SHOPAPI_VM_GOC"] == cay.duong
    assert "tests/" in bat_duoc["cmd"]
    assert "-p" in bat_duoc["cmd"] and "no:cacheprovider" in bat_duoc["cmd"]
    if os.name == "nt":
        assert bat_duoc["creationflags"] & subprocess.IDLE_PRIORITY_CLASS


# ── viet_bao_cao ─────────────────────────────────────────────────────────────


def test_viet_bao_cao_chan_khi_co_phat_hien(tmp_path):
    cay = k.CaySach(duong=str(tmp_path / "cay"), tep=("a.py",), theo_doi=frozenset())
    phat_hien = [k.PhatHien("bi_mat", "a.py", "test")]
    duong = k.viet_bao_cao(cay, phat_hien, k.KetQuaPytest(da_chay=False, ly_do_hoan="x"),
                            goc=str(tmp_path), ngay="2026-09-29")
    noi_dung = open(duong, "r", encoding="utf-8").read()
    assert "**CHẶN**" in noi_dung
    assert "a.py" in noi_dung


def test_viet_bao_cao_canh_bao_khi_hoan_pytest(tmp_path):
    cay = k.CaySach(duong=str(tmp_path / "cay"), tep=(), theo_doi=frozenset())
    duong = k.viet_bao_cao(cay, [], k.KetQuaPytest(da_chay=False, ly_do_hoan="đang sản xuất"),
                            goc=str(tmp_path), ngay="2026-09-29")
    noi_dung = open(duong, "r", encoding="utf-8").read()
    assert "**CẢNH BÁO**" in noi_dung
    assert "đang sản xuất" in noi_dung


def test_viet_bao_cao_ok(tmp_path):
    cay = k.CaySach(duong=str(tmp_path / "cay"), tep=(), theo_doi=frozenset())
    duong = k.viet_bao_cao(cay, [], k.KetQuaPytest(da_chay=True, ma_thoat=0, stdout="1 passed"),
                            goc=str(tmp_path), ngay="2026-09-29")
    noi_dung = open(duong, "r", encoding="utf-8").read()
    assert "**OK**" in noi_dung


# ── don_cay_cu ───────────────────────────────────────────────────────────────


def test_don_cay_cu_xoa_cay_qua_han(tmp_path):
    goc_tam = str(tmp_path / "tam")
    cu = os.path.join(goc_tam, "cu")
    moi = os.path.join(goc_tam, "moi")
    os.makedirs(cu)
    os.makedirs(moi)
    han = time.time() - 10 * 86400
    os.utime(cu, (han, han))

    so_xoa = k.don_cay_cu(goc_tam, giu_ngay=3.0)
    assert so_xoa == 1
    assert not os.path.isdir(cu)
    assert os.path.isdir(moi)


def test_don_cay_cu_thu_muc_chua_ton_tai(tmp_path):
    assert k.don_cay_cu(str(tmp_path / "khong-co")) == 0
