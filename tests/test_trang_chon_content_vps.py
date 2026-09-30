from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets")

from core import chon_content as cc

_GIU = None


class _App:
    def __init__(self, goc):
        self.base_dir = str(goc)
        self.loi = []
        self.tb = []

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            kq = viec()
        except BaseException as loi:
            return on_err(loi) if on_err else None
        return on_ok(kq) if on_ok else None

    def show_error(self, loi):
        self.loi.append(str(loi))

    def show_message(self, tieu_de, noi_dung):
        self.tb.append((tieu_de, noi_dung))


@pytest.fixture
def trang(tmp_path, monkeypatch):
    global _GIU
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication
    from ui_qt.trang_chon_content_vps import TrangChonContentVps

    os.makedirs(tmp_path / "CHANNEL" / "K1")
    (tmp_path / "CHANNEL" / "K1" / "kenh.yaml").write_text("ten: K1\n", encoding="utf-8")
    uv = [cc.UngVien(cc.LUONG_DOI_THU, "AAAAAAAAAAA", "Một content", "Nguồn", "https://youtu.be/AAAAAAAAAAA",
                     88, "Ưu tiên", "đang lên mạnh", 100000, 5000,
                     {"Nhanh": 100, "Lớn": 80, "Bứt": 90, "Vượt": 70})]
    monkeypatch.setattr(cc, "lay_ung_vien", lambda *a, **k: uv)
    _GIU = QApplication.instance() or QApplication([])
    app = _App(tmp_path)
    t = TrangChonContentVps(app)
    yield t, app
    t.close()


def test_trang_chi_co_hai_luong_ro_rang(trang):
    t, _app = trang
    assert t._luong.count() == 2
    assert [t._luong.itemData(i) for i in range(2)] == [cc.LUONG_DOI_THU, cc.LUONG_V7]
    t._tai()
    assert t._bang.rowCount() == 1
    assert "thứ hạng" in t._cong_thuc.text()


def test_chot_mot_content_va_hien_cho_san_xuat(trang):
    t, app = trang
    t._tai()
    t._bang.selectRow(0)
    t._chot()
    lua = cc.doc_lua_chon(app.base_dir, "K1")
    assert lua and lua.ung_vien.ma == "AAAAAAAAAAA"
    assert "Một content" in t._da_chot.text()
    assert "đúng một content" in t._trang_thai.text()


def test_khong_chon_dong_thi_nhac_ro(trang):
    t, app = trang
    t._tai()
    t._bang.clearSelection()
    t._chot()
    assert app.tb[-1][0] == "Chưa chọn content"
