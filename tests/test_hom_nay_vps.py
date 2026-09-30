"""Màn Tổng quan VPS: hiệu suất, tiến độ và một bảng quyết định."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget  # noqa: E402

from test_giao_dien_vps import _dung_goc  # noqa: E402
from test_trang_trung_tam import _AppGia, _GiamSatGia  # noqa: E402


@pytest.fixture
def hom_nay(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qapp = QApplication.instance() or QApplication([])
    goc = _dung_goc(tmp_path, monkeypatch)
    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()

    from ui_qt.trang_trung_tam import TrangTongQuanVps

    trang = TrangTongQuanVps(app)
    trang._dong_ho.stop()
    trang.show()
    qapp.processEvents()
    yield trang, app, qapp
    trang.close()
    trang.deleteLater()
    qapp.processEvents()


def _kenh(ma, muc="ok", chu="Đang ổn", *, ke_hoach=(), dang=False, tu_chay=True):
    return {
        "ma": ma, "ten": ma, "nhom": "tam-ly", "tu_chay": tu_chay,
        "dang_chay": dang, "bay_gio": {"muc": muc, "chu": chu},
        "video": {"tieu_de": "Video của " + ma}, "dang_luc": "20:00",
        "bay_ngay": {"so_video": 1, "views": 12000, "ctr": 5.2},
        "ke_hoach": list(ke_hoach),
    }


def test_mat_tong_quan_chi_doc_toan_bo_tinh_hinh(hom_nay):
    trang, _app, _qapp = hom_nay
    assert trang.findChildren(QTabWidget) == []
    assert trang._bang_hom_nay.columnCount() == 7
    assert [trang._bang_hom_nay.horizontalHeaderItem(i).text() for i in range(7)] == [
        "Kênh", "Trạng thái", "Video / lịch", "Dữ liệu 7 ngày",
        "Bật kiếm tiền (YPP)", "Dữ liệu cập nhật", "Nhận định"]

    chu = [w.text() for w in trang.findChildren(QLabel)]
    assert "Tổng quan" in chu
    assert not any(t in " ".join(chu) for t in ("Ổ đĩa", "Ví", "Windows", "Máy đăng"))
    nut = {w.text() for w in trang.findChildren(QPushButton)}
    assert not ({"Thêm kênh", "Công cụ ▾", "Cài kênh", "Làm mới",
                 "Duyệt video", "Đã đăng"} & nut)
    assert trang.minimumSizeHint().width() <= 760


def test_kenh_xep_on_dinh_va_tong_quan_khong_co_hanh_dong(hom_nay):
    trang, _app, qapp = hom_nay
    cho = {"loai": "cho_duyet", "ma_goi": "goi-1", "tieu_de": "Chờ duyệt"}
    trang._anh = {"luc": "2026-09-25 08:00", "kenh": [
        _kenh("ON", dang=True, muc="dang", chu="Đang làm video"),
        _kenh("OK"),
        _kenh("WAIT", muc="cho", chu="Chờ bạn duyệt", ke_hoach=(cho,)),
        _kenh("ERR", muc="loi", chu="Lỗi dựng video"),
    ]}
    trang._ve_bang()
    qapp.processEvents()

    bang = trang._bang_hom_nay
    assert [bang.item(r, 0).text() for r in range(4)] == ["ERR", "OK", "ON", "WAIT"]
    assert all(bang.cellWidget(r, 6) is None for r in range(4))
    assert trang.findChildren(QPushButton) == []
    assert trang._o_dang_lam.text().endswith("\n1")
    assert trang._o_cho_dang.text().endswith("\n1")


def test_noi_ro_so_thuoc_kenh_nao_va_vi_sao_thieu(hom_nay):
    trang, _app, qapp = hom_nay
    co_so = _kenh("TL2-T7")
    co_so["bay_ngay"] = {"so_video": 1, "views": 21, "ctr": 4.83, "dang_ky": 0}
    co_so["phien"] = {"ket_qua": {
        "quet_studio": "lỗi: không thấy Chrome của kênh",
        "quet_trang_chu": "lỗi: không thấy Chrome của kênh",
    }}
    thieu = _kenh("TL1-T7")
    thieu["bay_ngay"] = {"so_video": 0, "views": None, "ctr": None, "dang_ky": None}
    thieu["ypp"] = {"gio_xem": None, "dang_ky": None, "luc": ""}
    thieu["phien"] = co_so["phien"]
    trang._anh = {"luc": "2026-09-25 08:00", "kenh": [co_so, thieu]}
    trang._ve_bang()
    trang._ve_canh_bao()
    qapp.processEvents()

    bang = trang._bang_hom_nay
    assert bang.item(0, 3).text().startswith("Chưa có số liệu")
    assert "Không tìm thấy Chrome" in bang.item(0, 5).text()
    assert "21 view" in bang.item(1, 3).text()
    assert "TL2-T7" in trang._nhan_bao.text()
    assert "1/2 kênh" in trang._nhan_bao.text()
    assert "1/2 kênh" in trang._o_view_7.text()


def test_hom_nay_khong_doc_nhom_hay_tien_trinh_may(hom_nay, monkeypatch):
    trang, _app, _qapp = hom_nay
    from core import trung_tam as tt

    goi = []

    def anh(_goc, **khoa):
        goi.append(khoa)
        return {"luc": "2026-09-25 08:00", "kenh": []}

    monkeypatch.setattr(tt, "anh_chup", anh)
    trang.lam_moi()
    assert goi == [{"tat_ca": True, "co_nhom": False, "gio_lich": "02:00"}]


def test_canh_bao_hom_nay_khong_lan_su_co_may(hom_nay):
    trang, _app, _qapp = hom_nay
    trang._anh = {"o_dia": {"con_gb": 1}, "kenh": [
        _kenh("ERR", muc="loi", chu="Lỗi dựng video")], "la_vps": True}
    trang._may = {"may_dang": {"song": False}}
    viec = trang._viec_can_lam()
    assert viec == [("hong", "ERR: Lỗi dựng video")]


def test_mo_hom_nay_khong_kiem_tra_windows(tmp_path, monkeypatch):
    """Hết hạn Windows thuộc Hệ thống, tuyệt đối không chạy khi mở Hôm nay."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qapp = QApplication.instance() or QApplication([])
    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()

    from core import tong_quan_vps
    from ui_qt.trang_trung_tam import TrangTongQuanVps

    monkeypatch.setattr(
        tong_quan_vps, "canh_bao_windows",
        lambda: (_ for _ in ()).throw(AssertionError("Hôm nay đã gọi kiểm tra Windows")))
    trang = TrangTongQuanVps(app)
    trang._dong_ho.stop()
    qapp.processEvents()
    trang.close()
    trang.deleteLater()
