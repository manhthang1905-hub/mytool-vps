"""Bàn Phân tích VPS: một bảng ảo hóa, đổi/lọc được bốn nguồn dữ liệu."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import QApplication, QComboBox, QPushButton, QTabWidget, QTableView, QToolButton  # noqa: E402

from test_giao_dien_vps import _dung_goc  # noqa: E402
from test_trang_trung_tam import _AppGia, _GiamSatGia  # noqa: E402


@pytest.fixture
def trang(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qapp = QApplication.instance() or QApplication([])
    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))

    from core import bang_du_lieu_vps as dl
    from core import tong_quan_vps as tq
    from core import trung_tam as tt

    monkeypatch.setattr(tt, "anh_chup", lambda *_a, **_k: {"kenh": [{
        "ma": "TL1-T7", "bay_ngay": {"views": 12345, "so_video": 2, "ctr": 5.4},
        "ypp": {"gio_xem": 456, "dang_ky": 789, "luc": "25/09 01:00"},
    }]})
    monkeypatch.setattr(tq, "tom_tat_phan_tich", lambda *_a, **_k: {
        "doi_thu": {"so_kenh": 3, "so_link": 393, "luc": "24/09", "top": []},
        "noi_dung": {"so_video": 1200, "luc": "24/09"},
        "v7": {"so_ung_vien": 1, "so_da_cham": 2, "luc": "24/09", "top": []},
    })

    def bo(_g, _k, loai):
        if loai == dl.V7:
            cot = [{"khoa": "Điểm", "nhan": "Điểm", "kieu": "so", "rong": 60},
                   {"khoa": "Tiêu đề hiển thị", "nhan": "Tiêu đề", "kieu": "chu", "rong": 300}]
            hang = [{"Điểm": "71", "Loại": "Bỏ", "Tiêu đề hiển thị": "Một chủ đề",
                     "Lý do": "CTR nguồn thấp", "Link": "https://youtu.be/abcdefghijk",
                     "_tim": "một chủ đề ctr nguồn thấp"},
                    {"Điểm": "91", "Loại": "Nên làm", "Tiêu đề hiển thị": "Cơ hội tốt",
                     "Lý do": "đang lên", "Link": "", "_tim": "cơ hội tốt đang lên"}]
        elif loai == dl.CONTENT:
            cot = [{"khoa": "Tiêu đề hiển thị", "nhan": "Tiêu đề", "kieu": "chu", "rong": 300}]
            hang = [{"Tiêu đề hiển thị": "Kho A", "Đã làm": "", "Điểm": "90", "_tim": "kho a"}]
        else:
            cot, hang = [], []
        return {"loai": loai, "nhan": dl.NHAN[loai], "cot": cot, "hang": hang, "nguon": "gia.csv"}

    monkeypatch.setattr(dl, "doc_bo_du_lieu", bo)
    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()
    from ui_qt.trang_phan_tich_vps import TrangPhanTichVps

    t = TrangPhanTichVps(app)
    t.show()
    qapp.processEvents()
    yield t, app, qapp
    t.close()
    t.deleteLater()
    qapp.processEvents()


def test_chi_mot_bang_khong_tab_con(trang):
    t, _app, _qapp = trang
    assert t.findChildren(QTabWidget) == []
    assert len(t.findChildren(QTableView)) == 1
    assert t._model.rowCount() == 2


def test_bon_bo_du_lieu_gom_trong_mot_o_chon_va_mot_menu(trang):
    t, _app, _qapp = trang
    assert [t._chon_bo.itemData(i) for i in range(t._chon_bo.count())] == [
        "v7", "content", "doi_thu", "hieu_qua"]
    assert len([n for n in t.findChildren(QToolButton) if n.text().startswith("Thêm")]) == 1
    assert len(t.findChildren(QPushButton)) == 1, "chỉ để một hành động chính ngoài bảng"


def test_loc_nhanh_va_tim_kiem_tren_toan_bo_bang(trang):
    t, _app, qapp = trang
    t._loc.setCurrentIndex(t._loc.findData("qua"))
    qapp.processEvents()
    assert t._proxy.rowCount() == 1
    t._loc.setCurrentIndex(0)
    t._tim.setText("ctr nguồn")
    t._cho_go.stop()
    t._ap_loc()
    assert t._proxy.rowCount() == 1
    assert "1 / 2" in t._dem.text()


def test_co_the_gioi_han_tim_trong_mot_cot(trang):
    t, _app, _qapp = trang
    t._cot_tim.setCurrentIndex(t._cot_tim.findData("Tiêu đề hiển thị"))
    t._tim.setText("ctr nguồn")  # chỉ nằm ở Lý do, không nằm trong Tiêu đề
    t._cho_go.stop()
    t._ap_loc()
    assert t._proxy.rowCount() == 0
    t._cot_tim.setCurrentIndex(0)
    t._ap_loc()
    assert t._proxy.rowCount() == 1


def test_doi_sang_kho_content_chi_nap_khi_bam(trang):
    t, _app, _qapp = trang
    t._doi_bo_du_lieu("content")
    assert t._model.rowCount() == 1
    assert t._model.dong(0)["Tiêu đề hiển thị"] == "Kho A"


def test_chon_dong_hien_ly_do_day_du(trang):
    t, _app, qapp = trang
    t._bang.selectRow(0)
    qapp.processEvents()
    assert "nguồn" in t._chi_tiet.text() or "đang lên" in t._chi_tiet.text()


def test_hanh_dong_chinh_chi_bat_khi_chon_content_chua_dung(trang):
    t, _app, qapp = trang
    assert not t._nut_hanh_dong.isEnabled()
    hang_co_link = next(r for r in range(t._proxy.rowCount())
                        if t._model.dong(t._proxy.mapToSource(t._proxy.index(r, 0)).row()).get("Link"))
    t._bang.selectRow(hang_co_link)
    qapp.processEvents()
    assert t._nut_hanh_dong.isEnabled()


def test_doi_thu_co_cot_quan_ly_sua_duoc(trang, monkeypatch):
    t, _app, _qapp = trang
    from core import bang_du_lieu_vps as dl

    monkeypatch.setattr(dl, "doc_bo_du_lieu", lambda *_a, **_k: {
        "loai": dl.DOI_THU, "nhan": dl.NHAN[dl.DOI_THU], "nguon": "doi-thu.csv",
        "cot": [{"khoa": "Trạng thái", "nhan": "Trạng thái", "kieu": "chu",
                 "rong": 100, "sua": True}],
        "hang": [{"Trạng thái": "Theo dõi", "Link kênh": "https://youtube.com/@x", "_tim": "theo dõi"}],
    })
    t._cache.clear()
    t._doi_bo_du_lieu(dl.DOI_THU)
    assert t._model.la_cot_sua(0)
    assert "✎" in t._model.headerData(0, 1)
