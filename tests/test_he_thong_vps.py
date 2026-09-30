"""Mặt Hệ thống VPS: không tab lồng nhưng vẫn giữ trạm nhận dữ liệu sống."""

from __future__ import annotations

import os
import types

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import (  # noqa: E402
    QApplication, QPushButton, QStackedWidget, QTabWidget, QWidget,
)

from test_giao_dien_vps import _dung_goc  # noqa: E402
from test_trang_trung_tam import _AppGia, _GiamSatGia  # noqa: E402


class _ChiSoGia(QWidget):
    def __init__(self, _app, phan=()):
        super().__init__()
        self._phan = tuple(phan)
        self._tram = types.SimpleNamespace(dang_chay=True)


@pytest.fixture
def trang(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qapp = QApplication.instance() or QApplication([])
    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()

    import ui_qt.trang_chi_so_ytb as mod_chi_so
    monkeypatch.setattr(mod_chi_so, "TrangChiSoYTB", _ChiSoGia)

    from ui_qt.trang_may_vi import TrangHeThongVps

    t = TrangHeThongVps(app)
    t.show()
    qapp.processEvents()
    yield t, app, qapp
    t.close()
    t.deleteLater()
    qapp.processEvents()


def test_he_thong_khong_tab_con(trang):
    t, _app, _qapp = trang
    assert t.findChildren(QTabWidget) == []


def test_tram_van_duoc_dung_tu_luc_mo_tool(trang):
    t, _app, _qapp = trang
    assert t.chi_so._phan == ("cai", "tram")
    assert t.chi_so._tram.dang_chay is True
    assert t.chi_so.isHidden()


def test_hien_may_nen_va_cac_loi_quan_ly(trang):
    t, _app, _qapp = trang
    assert t.may is None, "khối sức khỏe nặng chỉ dựng khi người dùng mở"
    assert t.vi is None, "ví chỉ được dựng khi người dùng mở"
    chu = {n.text().replace("&&", "&") for n in t.findChildren(QPushButton)}
    assert {"Kiểm tra tool", "Mở cài đặt", "Thêm VPS"} <= chu
    assert "2/3 dịch vụ nền đang chạy" in t._nhan_suc_khoe.text()


def test_khoi_dong_lai_an_toan_hien_xanh(trang, monkeypatch):
    """Thẻ "Khởi động lại giao diện" — CHỈ hiển thị, không tự đóng/mở gì.
    `an_toan_khoi_dong.kiem_tra` bị monkeypatch, không gọi hàm thật."""
    t, _app, _qapp = trang
    from core import an_toan_khoi_dong

    monkeypatch.setattr(an_toan_khoi_dong, "kiem_tra",
                        lambda *a, **k: {"duoc": True, "ly_do": [],
                                          "luc_an_toan_tiep": None})
    t._cap_nhat_khoi_dong_lai()
    assert "An toàn" in t._nhan_khoi_dong_lai.text()
    assert "✕" not in t._nhan_khoi_dong_lai.text()


def test_khoi_dong_lai_chua_an_toan_hien_ly_do(trang, monkeypatch):
    t, _app, _qapp = trang
    from core import an_toan_khoi_dong

    monkeypatch.setattr(an_toan_khoi_dong, "kiem_tra",
                        lambda *a, **k: {"duoc": False,
                                          "ly_do": ["Kênh TL1-T7 đang sản xuất video."],
                                          "luc_an_toan_tiep": None})
    t._cap_nhat_khoi_dong_lai()
    assert "Chưa nên" in t._nhan_khoi_dong_lai.text()
    assert "Kênh TL1-T7 đang sản xuất video." in t._nhan_khoi_dong_lai.text()


def test_hop_trien_khai_nhom_kenh_va_gioi_han_nam(trang):
    _t, app, _qapp = trang
    from ui_qt.trang_trien_khai_vps import HopTrienKhaiVps

    hop = HopTrienKhaiVps(app)
    assert len(hop._o_kenh) == 1
    assert hop.findChild(QStackedWidget).count() == 3
    assert hop._cac_buoc.currentIndex() == 0
    assert hop._chon_day_du.isChecked()
    assert not hop._chon_sach.isChecked()
    assert "Bước 1/3" in hop._chi_buoc.text()
    hop.close()


def test_hop_trien_khai_chi_cho_qua_buoc_khi_da_chon_kenh(trang):
    _t, app, _qapp = trang
    from ui_qt.trang_trien_khai_vps import HopTrienKhaiVps

    hop = HopTrienKhaiVps(app)
    hop._tiep()
    assert hop._cac_buoc.currentIndex() == 0
    assert app.thong_bao[-1][0] == "Chưa chọn kênh"
    next(iter(hop._o_kenh.values())).setChecked(True)
    hop._tiep()
    assert hop._cac_buoc.currentIndex() == 1
    hop._chon_sach.setChecked(True)
    assert not hop._chon_day_du.isChecked(), "hai cách chuyển phải loại trừ nhau"
    hop._tiep()
    assert hop._cac_buoc.currentIndex() == 2
    assert "Tạo kênh mới từ khuôn" in hop._tom_tat.text()
    hop.close()

