"""Mặt trước Nội dung phải đơn giản và không nạp mọi màn nặng cùng lúc."""

from __future__ import annotations

import os
import sys
import types

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import QApplication, QWidget  # noqa: E402


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _gan_man_gia(monkeypatch, da_tao):
    thong_so = (
        ("ui_qt.trang_trung_tam", "TrangTrungTam", "video"),
        ("ui_qt.trang_quan_ly_kenh", "TrangQuanLyKenh", "kenh"),
        ("ui_qt.trang_phan_tich", "TrangPhanTich", "nguon"),
        ("ui_qt.trang_auto", "TrangTuDong", "chay_tay"),
    )
    for ten_module, ten_lop, ma in thong_so:
        module = types.ModuleType(ten_module)

        def __init__(self, _app, _ma=ma):
            QWidget.__init__(self)
            self.ma = _ma
            self.du_an = []
            da_tao.append(_ma)

        def doi_du_an(self, ten):
            self.du_an.append(ten)

        lop = type(ten_lop, (QWidget,), {
            "__init__": __init__,
            "doi_du_an": doi_du_an,
        })
        setattr(module, ten_lop, lop)
        monkeypatch.setitem(sys.modules, ten_module, module)


def test_chi_nap_video_khi_trang_noi_dung_that_su_hien(monkeypatch, qapp):
    da_tao = []
    _gan_man_gia(monkeypatch, da_tao)
    from ui_qt.trang_noi_dung import TAB_CON, TrangNoiDung

    trang = TrangNoiDung(object())
    try:
        assert TAB_CON == ("Video", "Kênh", "Nguồn", "Chạy tay")
        assert [trang.tabs.tabText(i) for i in range(trang.tabs.count())] == list(TAB_CON)
        assert da_tao == [], "trang còn ẩn thì không được nạp bảng ảnh nặng"
        trang.show()
        qapp.processEvents()
        assert da_tao == ["video"]
        assert trang.duyet is not None
        assert trang.quan_ly is None and trang.doi_thu is None and trang.san_xuat is None
    finally:
        trang.close()
        trang.deleteLater()


def test_mo_ten_cu_van_den_dung_muc_va_moi_muc_chi_nap_mot_lan(monkeypatch, qapp):
    da_tao = []
    _gan_man_gia(monkeypatch, da_tao)
    from ui_qt.trang_noi_dung import TrangNoiDung

    trang = TrangNoiDung(object())
    try:
        trang.mo_tab("Quản lý kênh")
        qapp.processEvents()
        assert trang.tabs.currentIndex() == 1
        assert da_tao == ["kenh"]
        assert "giọng đọc" in trang._nhan_mo_ta.text().lower()

        trang.mo_tab("Kênh")
        trang.mo_tab("Đối thủ")
        qapp.processEvents()
        assert da_tao == ["kenh", "nguon"]

        trang.doi_du_an("du-an-moi")
        assert trang.duyet is None
        assert trang.quan_ly.du_an == ["du-an-moi"]
        assert trang.doi_thu.du_an == ["du-an-moi"]
        assert trang.san_xuat is None
    finally:
        trang.close()
        trang.deleteLater()
