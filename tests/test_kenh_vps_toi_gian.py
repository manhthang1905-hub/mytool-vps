"""Mặt Kênh của VPS: một luồng hằng ngày, không tab con và không dựng màn nặng sớm."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import QApplication, QPushButton, QTabWidget  # noqa: E402

from test_giao_dien_vps import _dung_goc  # noqa: E402
from test_trang_trung_tam import _AppGia, _GiamSatGia  # noqa: E402


@pytest.fixture
def trang_kenh(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app_qt = QApplication.instance() or QApplication([])
    goc = _dung_goc(tmp_path, monkeypatch)
    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()

    from ui_qt.trang_trung_tam import TrangKenhVps

    trang = TrangKenhVps(app)
    trang._dong_ho.stop()
    trang.show()
    app_qt.processEvents()
    yield trang, app, app_qt
    trang.close()
    trang.deleteLater()
    app_qt.processEvents()


def test_mat_chinh_khong_con_tab_con(trang_kenh):
    trang, _app, _qapp = trang_kenh
    assert trang.findChildren(QTabWidget) == []
    assert not hasattr(trang, "_tabs")


def test_viec_hang_ngay_hien_thang_va_co_nut_quan_ly(trang_kenh):
    trang, _app, _qapp = trang_kenh
    chu_nut = {nut.text().replace("&&", "&") for nut in trang.findChildren(QPushButton)}
    assert {"Cài kênh", "Công cụ ▾", "Duyệt đăng", "Đã đăng thủ công"} <= chu_nut
    assert trang._tab_duyet.isVisible()
    assert trang._bang_kh.isVisible()


def test_cong_cu_it_dung_chua_duoc_dung_luc_khoi_dong(trang_kenh):
    trang, _app, _qapp = trang_kenh
    assert trang._tab_tien_do is None
    assert trang._tab_hieu_qua is None
    assert trang._tab_nhat_ky is None
    assert trang._tab_cai_dat is None


def test_cong_cu_duoc_dung_muon_khi_can(trang_kenh):
    trang, _app, _qapp = trang_kenh
    widget = trang._lay_cong_cu("_tab_tien_do", trang._dung_tien_do)
    assert widget is trang._tab_tien_do
    assert widget.isHidden()
    assert trang._tab_hieu_qua is None


def test_bam_tien_do_mo_cong_cu_thay_vi_goi_tab_cu(trang_kenh, monkeypatch):
    trang, _app, _qapp = trang_kenh
    da_mo = []
    monkeypatch.setattr(trang, "_mo_chi_tiet_luot", lambda: da_mo.append(trang._ma_chon))
    trang._mo_tien_do("TL2-T7")
    assert trang._ma_chon == "TL2-T7"
    assert da_mo == ["TL2-T7"]

