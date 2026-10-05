"""core/bao_cao_ngay.py — nguồn nặng bị thay bằng đồ giả; không mạng, không ghi ngoài tmp_path."""
from __future__ import annotations

import datetime as _dt
import os

from core import bao_cao_ngay as bc

BG = _dt.datetime(2026, 10, 6, 7, 0)


def _gia(monkeypatch, **hong):
    """Thay mọi mục bằng bản giả; mục nào có trong `hong` thì ném lỗi."""
    def mk(ten, dong):
        def f(*a, **k):
            if ten in hong:
                raise RuntimeError("hỏng " + ten)
            return dong
        return f
    monkeypatch.setattr(bc, "_muc_video", mk("video", ["- TL1: có video mai"]))
    monkeypatch.setattr(bc, "_muc_skill", mk("skill", ["- không skill nào hỏng/thiếu"]))
    monkeypatch.setattr(bc, "_muc_ypp", mk("ypp", ["- TL1: 100/4000h"]))
    monkeypatch.setattr(bc, "_muc_chien_truong", mk("ct", ["- Thị phần ta 1%"]))
    monkeypatch.setattr(bc, "_muc_loi", mk("loi", ["- không có lỗi"]))
    monkeypatch.setattr(bc, "_muc_may", mk("may", ["- RAM 5/8 GB"]))


def test_tao_du_sau_muc(monkeypatch, tmp_path):
    _gia(monkeypatch)
    t = bc.tao(str(tmp_path), BG)
    for m in ("Video ngày mai", "Skill hỏng/thiếu", "Đường tới YPP", "Chiến trường", "Lỗi 24 giờ", "Máy"):
        assert m in t
    assert len(t.splitlines()) <= 40


def test_muc_hong_khong_vo_ban_tin(monkeypatch, tmp_path):
    _gia(monkeypatch, ypp=1, ct=1, may=1)
    t = bc.tao(str(tmp_path), BG)
    assert t.count("không đọc được") == 3
    assert "TL1: có video mai" in t and "Lỗi 24 giờ" in t


def test_muc_loi_24h_bo_nhac(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "loi-chay-max.md").write_text(
        "- [2026-10-05 12:00] **nhac** · kênh A — nhắc nhẹ\n"
        "- [2026-10-04 12:00] **khan** — lỗi cũ quá 24h\n"
        "- [2026-10-06 03:00] **khan** · kênh B — hỏng thật\n"
        "- [2026-10-06 04:00] **thuong** — lặp\n- [2026-10-06 05:00] **thuong** — lặp\n", encoding="utf-8")
    r = "\n".join(bc._muc_loi(str(tmp_path), BG))  # noqa: SLF001
    assert "hỏng thật" in r and "lặp (x2)" in r
    assert "nhắc nhẹ" not in r and "lỗi cũ" not in r


def test_muc_loi_khong_co_tep(tmp_path):
    assert "chưa có" in bc._muc_loi(str(tmp_path), BG)[0]  # noqa: SLF001


def test_ghi_vao_thu_muc_tam(monkeypatch, tmp_path):
    _gia(monkeypatch)
    p = bc.ghi(str(tmp_path), thu_muc=str(tmp_path / "bc"), bay_gio=BG)
    assert os.path.basename(p) == "2026-10-06.md"
    assert "Báo cáo sức khoẻ" in open(p, encoding="utf-8").read()


def test_gui_mot_lan_moi_ngay(monkeypatch, tmp_path):
    _gia(monkeypatch)
    da = []
    f = lambda g, v: da.append(v) or True  # noqa: E731
    tm = str(tmp_path / "bc")
    assert bc.gui(str(tmp_path), tm, BG, ham_gui=f) == "da_gui"
    assert bc.gui(str(tmp_path), tm, BG, ham_gui=f) == "da_gui_truoc_do"
    assert len(da) == 1
    ngay_mai = BG + _dt.timedelta(days=1)
    assert bc.gui(str(tmp_path), tm, ngay_mai, ham_gui=f) == "da_gui"
    assert len(da) == 2


def test_gui_that_bai_thu_lai_toi_da(monkeypatch, tmp_path):
    _gia(monkeypatch)
    tm = str(tmp_path / "bc")
    n = []

    def hong(g, v):
        n.append(1)
        raise OSError("mạng")
    kq = [bc.gui(str(tmp_path), tm, BG, ham_gui=hong) for _ in range(5)]
    assert kq[:3] == ["that_bai"] * 3 and kq[3:] == ["da_gui_truoc_do"] * 2
    assert len(n) == bc.TOI_DA_GUI_MOI_NGAY


def test_chua_cau_hinh_thi_bo_qua_khong_mang(monkeypatch, tmp_path):
    _gia(monkeypatch)
    monkeypatch.setattr("core.bao_dong._http_post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi mạng")))
    assert bc.gui(str(tmp_path), str(tmp_path / "bc"), BG) == "chua_cau_hinh"


def test_chay_hang_ngay_truoc_0630_khong_lam_gi(monkeypatch, tmp_path):
    _gia(monkeypatch)
    assert bc.chay_hang_ngay(str(tmp_path), str(tmp_path / "bc"), _dt.datetime(2026, 10, 6, 6, 29)) == ""
    assert not (tmp_path / "bc").exists()


def test_chay_hang_ngay_mot_lan(monkeypatch, tmp_path):
    _gia(monkeypatch)
    da = []
    f = lambda g, v: da.append(v) or True  # noqa: E731
    tm = str(tmp_path / "bc")
    s1 = bc.chay_hang_ngay(str(tmp_path), tm, BG, f)
    assert "gửi da_gui" in s1 and os.path.isfile(os.path.join(tm, "2026-10-06.md"))
    assert bc.chay_hang_ngay(str(tmp_path), tm, BG + _dt.timedelta(hours=3), f) == ""
    assert len(da) == 1
