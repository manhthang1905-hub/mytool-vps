"""Trang Nghiên cứu VPS: đối thủ và content đối thủ trong một sổ bảng tính."""

from __future__ import annotations

import os
from typing import Any, Dict

from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QMenu, QToolButton, QVBoxLayout, QWidget,
)

from core import bang_du_lieu_vps as dl
from core import nghien_cuu_vps as nc
from core.kenh import liet_ke_kenh

from .bang_du_lieu_vps import BangModel, BangProxy, BangView, xuat_proxy
from .widgets import HangXuongDong, nhan, the

__all__ = ["TrangNghienCuuVps"]


class TrangNghienCuuVps(QWidget):
    """Một bảng duy nhất; đổi sổ chứ không xếp tab con lên nhau."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._loai = nc.DOI_THU
        self._cache: Dict[tuple, Dict[str, Any]] = {}
        self._dang_nap = set()
        self._da_nap = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(9)

        dau = QHBoxLayout()
        dau.addWidget(nhan("Nghiên cứu", "h1"))
        dau.addWidget(nhan("Theo dõi thị trường trước khi chọn content", "muted"), 1)
        dau.addWidget(nhan("Kênh", "muted"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.addItems(liet_ke_kenh(app.base_dir))
        self._chon_kenh.setMinimumWidth(165)
        self._chon_kenh.currentTextChanged.connect(self._doi_kenh)
        dau.addWidget(self._chon_kenh)
        doc.addLayout(dau)

        # Ba đầu vào đặt cùng một hàng. Đây là đồng hồ chất lượng dữ liệu, không
        # phải ba nút — người vận hành nhìn một lần là biết thiếu mắt nào.
        self._chat_luong = nhan("Đang kiểm tra dữ liệu…", "phu")
        doc.addWidget(self._chat_luong)
        hang_nguon = HangXuongDong(8)
        self._the_nguon = []
        for ten in ("Danh sách ban đầu", "Studio của kênh", "Trang chủ kênh"):
            o = the()
            o.setMinimumWidth(180)
            v = QVBoxLayout(o)
            v.setContentsMargins(12, 8, 12, 8)
            v.setSpacing(2)
            v.addWidget(nhan(ten, "muted"))
            so = nhan("—", "h2")
            luc = nhan("Chưa có dữ liệu", "muted")
            so.setWordWrap(False)
            v.addWidget(so)
            v.addWidget(luc)
            hang_nguon.addWidget(o)
            self._the_nguon.append((o, so, luc))
        doc.addLayout(hang_nguon)

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)

        cong_cu = HangXuongDong(7)
        cong_cu.addWidget(nhan("Xem"))
        self._chon_so = QComboBox()
        for loai in nc.CAC_SO:
            self._chon_so.addItem(nc.NHAN_SO[loai], loai)
        self._chon_so.setMinimumWidth(170)
        self._chon_so.currentIndexChanged.connect(self._doi_so_tu_o_chon)
        cong_cu.addWidget(self._chon_so)
        cong_cu.addWidget(nhan("Lọc"))
        self._loc = QComboBox()
        self._loc.setMinimumWidth(145)
        self._loc.currentIndexChanged.connect(self._ap_loc)
        cong_cu.addWidget(self._loc)
        self._dem = nhan("0 dòng", "muted")
        cong_cu.addWidget(self._dem)
        self._nut_cot = QToolButton()
        self._nut_cot.setText("Cột  ▾")
        self._nut_cot.setPopupMode(QToolButton.InstantPopup)
        self._menu_cot = QMenu(self._nut_cot)
        self._nut_cot.setMenu(self._menu_cot)
        cong_cu.addWidget(self._nut_cot)
        self._nut_them = QToolButton()
        self._nut_them.setText("Thêm  ▾")
        self._nut_them.setPopupMode(QToolButton.InstantPopup)
        self._menu_them = QMenu(self._nut_them)
        self._menu_them.addAction("Làm mới dữ liệu", self.lam_moi)
        self._menu_them.addAction("Mở link dòng đã chọn", self._mo_link)
        self._menu_them.addAction("Sao chép vùng chọn", self._chep)
        self._menu_them.addAction("Xuất phần đang lọc…", self._xuat)
        self._menu_them.addSeparator()
        self._menu_them.addAction("Mở quản lý nghiên cứu đầy đủ…", self._mo_quan_ly)
        self._nut_them.setMenu(self._menu_them)
        cong_cu.addWidget(self._nut_them)
        v.addLayout(cong_cu)

        hang_tim = QHBoxLayout()
        self._cot_tim = QComboBox()
        self._cot_tim.addItem("Tất cả cột", "")
        self._cot_tim.setMinimumWidth(130)
        self._cot_tim.currentIndexChanged.connect(self._ap_loc)
        hang_tim.addWidget(self._cot_tim)
        from PyQt5.QtWidgets import QLineEdit
        self._tim = QLineEdit()
        self._tim.setPlaceholderText("Tìm trong bảng…")
        self._tim.setClearButtonEnabled(True)
        self._tim.textChanged.connect(lambda _s: self._cho_tim.start())
        hang_tim.addWidget(self._tim, 1)
        v.addLayout(hang_tim)

        self._mo_ta = nhan(nc.MO_TA_SO[self._loai], "muted")
        v.addWidget(self._mo_ta)

        self._model = BangModel(self)
        self._proxy = BangProxy(self)
        self._proxy.setSourceModel(self._model)
        self._bang = BangView()
        self._bang.setModel(self._proxy)
        self._bang.setSortingEnabled(True)
        self._bang.setAlternatingRowColors(True)
        self._bang.setWordWrap(False)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._bang.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self._bang.verticalHeader().setDefaultSectionSize(27)
        self._bang.horizontalHeader().setHighlightSections(False)
        self._bang.doubleClicked.connect(self._double_click)
        self._bang.yeu_cau_menu.connect(self._menu_dong)
        self._bang.selectionModel().selectionChanged.connect(self._ve_chi_tiet)
        v.addWidget(self._bang, 1)

        self._chi_tiet = QLabel("Chọn một dòng để xem. Click tiêu đề cột để sắp xếp; click đúp ô ✎ để ghi.")
        self._chi_tiet.setWordWrap(True)
        self._chi_tiet.setMinimumHeight(38)
        self._chi_tiet.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self._chi_tiet)
        self._trang_thai = nhan("Dữ liệu lưu trên máy", "muted")
        v.addWidget(self._trang_thai)
        doc.addWidget(khung, 1)

        self._cho_tim = QTimer(self)
        self._cho_tim.setSingleShot(True)
        self._cho_tim.setInterval(250)
        self._cho_tim.timeout.connect(self._ap_loc)
        self._nap_loc()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._da_nap:
            self._da_nap = True
            self.lam_moi()

    def _kenh(self) -> str:
        return self._chon_kenh.currentText().strip()

    def _doi_kenh(self, _ma="") -> None:
        self._tim.clear()
        self._nap_tom_tat()
        self._nap_so()

    def lam_moi(self) -> None:
        ma = self._kenh()
        self._cache = {k: v for k, v in self._cache.items() if k[0] != ma}
        self._nap_tom_tat()
        self._nap_so()

    def _nap_tom_tat(self) -> None:
        ma = self._kenh()
        if not ma:
            self._chat_luong.setText("Chưa có kênh để nghiên cứu.")
            return
        self._chat_luong.setText("Đang kiểm tra độ mới của dữ liệu…")
        self._app.run_bg(
            lambda: (ma, nc.tom_tat_nguon(self._app.base_dir, ma)),
            on_ok=self._ve_tom_tat,
            on_err=lambda e: self._chat_luong.setText("Không đọc được nguồn dữ liệu: " + str(e)[:130]),
        )

    def _ve_tom_tat(self, ket) -> None:
        ma, tom_tat = ket
        if ma != self._kenh():
            return
        self._chat_luong.setText(
            "{0}  ·  {1:,} đối thủ đang theo dõi  ·  {2:,} content đã thu thập".format(
                tom_tat["chat_luong"], tom_tat["so_doi_thu"], tom_tat["so_content"])
            .replace(",", "."))
        mau = {"tot": "#e8f5e9", "can": "#fff8e1", "cu": "#fff3e0", "thieu": "#fce8e6"}
        for (khung, so, luc), nguon in zip(self._the_nguon, tom_tat["nguon"]):
            so.setText("{0:,} {1}".format(nguon["so_luong"], nguon["don_vi"]).replace(",", "."))
            luc.setText("{0} · {1}".format(nguon["trang_thai"], nguon["luc"]))
            khung.setStyleSheet("QFrame#card { background: %s; }" % mau.get(nguon["muc"], "#ffffff"))

    def _doi_so_tu_o_chon(self, _i=0) -> None:
        self._doi_so(str(self._chon_so.currentData() or nc.DOI_THU))

    def _doi_so(self, loai: str) -> None:
        if loai not in nc.CAC_SO or loai == self._loai:
            return
        self._loai = loai
        self._tim.clear()
        self._nap_loc()
        self._nap_so()

    def _nap_loc(self) -> None:
        self._loc.blockSignals(True)
        self._loc.clear()
        for ten, ma in dl.LOC_NHANH[self._loai]:
            self._loc.addItem(ten, ma)
        self._loc.blockSignals(False)
        self._mo_ta.setText(nc.MO_TA_SO[self._loai])

    def _nap_so(self) -> None:
        ma, loai = self._kenh(), self._loai
        if not ma:
            return
        khoa = (ma, loai)
        if khoa in self._cache:
            return self._ve_so((ma, loai, self._cache[khoa]))
        if khoa in self._dang_nap:
            return
        self._dang_nap.add(khoa)
        self._model.dat([], [])
        self._dem.setText("đang đọc…")

        def xong(ket):
            self._dang_nap.discard(khoa)
            self._ve_so(ket)

        def loi(e):
            self._dang_nap.discard(khoa)
            self._trang_thai.setText("Không đọc được bảng: " + str(e)[:140])

        self._app.run_bg(lambda: (ma, loai, nc.doc_so(self._app.base_dir, ma, loai)),
                         on_ok=xong, on_err=loi)

    def _ve_so(self, ket) -> None:
        ma, loai, bo = ket
        self._cache[(ma, loai)] = bo
        if ma != self._kenh() or loai != self._loai:
            return
        self._model.dat(bo["cot"], bo["hang"], self._sua_o)
        self._cot_tim.blockSignals(True)
        self._cot_tim.clear()
        self._cot_tim.addItem("Tất cả cột", "")
        for c in bo["cot"]:
            self._cot_tim.addItem(c["nhan"], c["khoa"])
        self._cot_tim.blockSignals(False)
        self._dung_menu_cot()
        for i, c in enumerate(bo["cot"]):
            self._bang.setColumnWidth(i, c.get("rong", 110))
        self._ap_loc()
        self._trang_thai.setText(
            "{0:,} dòng · click tiêu đề để sắp xếp · ô ✎ tự lưu khi sửa".format(len(bo["hang"]))
            .replace(",", "."))

    def _dung_menu_cot(self) -> None:
        self._menu_cot.clear()
        for i, c in enumerate(self._model.cot):
            a = self._menu_cot.addAction(c["nhan"])
            a.setCheckable(True)
            a.setChecked(not self._bang.isColumnHidden(i))
            a.toggled.connect(lambda hien, cot=i: self._bang.setColumnHidden(cot, not hien))
        if self._model.cot:
            self._menu_cot.addSeparator()
            self._menu_cot.addAction("Hiện tất cả", self._hien_tat_ca_cot)

    def _hien_tat_ca_cot(self) -> None:
        for i in range(self._model.columnCount()):
            self._bang.setColumnHidden(i, False)
        self._dung_menu_cot()

    def _sua_o(self, dong: Dict[str, Any], khoa: str, gia_tri: str) -> bool:
        try:
            dl.sua_o_quan_ly(self._app.base_dir, self._kenh(), self._loai, dong, khoa, gia_tri)
        except (OSError, ValueError) as e:
            self._app.show_error(e)
            return False
        self._cache.pop((self._kenh(), self._loai), None)
        self._trang_thai.setText("Đã lưu {0}.".format(khoa.lower()))
        return True

    def _ap_loc(self, _i=0) -> None:
        self._proxy.dat_loc(self._loai, str(self._loc.currentData() or ""), self._tim.text(),
                            str(self._cot_tim.currentData() or ""))
        self._dem.setText("{0:,} / {1:,} dòng".format(
            self._proxy.rowCount(), self._model.rowCount()).replace(",", "."))

    def _dong_chon(self) -> Dict[str, Any]:
        i = self._bang.currentIndex()
        return self._model.dong(self._proxy.mapToSource(i).row()) if i.isValid() else {}

    def _ve_chi_tiet(self, *_a) -> None:
        d = self._dong_chon()
        if not d:
            return
        ten = d.get("Tiêu đề hiển thị") or d.get("Kênh") or ""
        phu = d.get("Ghi chú") or d.get("Tuyến") or d.get("Tuyến / Kênh") or ""
        self._chi_tiet.setText((str(ten) + ("\n" + str(phu) if phu else ""))[:900])

    def _double_click(self, i) -> None:
        src = self._proxy.mapToSource(i)
        if not (src.isValid() and self._model.la_cot_sua(src.column())):
            self._mo_link()

    def _menu_dong(self, diem) -> None:
        i = self._bang.indexAt(diem)
        if i.isValid() and not self._bang.selectionModel().isSelected(i):
            self._bang.selectRow(i.row())
        menu = QMenu(self)
        menu.addAction("Mở link", self._mo_link).setEnabled(bool(dl.link_cua_dong(self._loai, self._dong_chon())))
        menu.addAction("Sao chép", self._chep)
        menu.exec_(self._bang.viewport().mapToGlobal(diem))

    def _mo_link(self) -> None:
        link = dl.link_cua_dong(self._loai, self._dong_chon())
        if link.startswith(("http://", "https://")):
            QDesktopServices.openUrl(QUrl(link))
        else:
            self._app.show_message("Chưa chọn link", "Chọn một dòng có link video hoặc link kênh.")

    def _chep(self) -> None:
        if not self._bang.chep_vung_chon():
            self._app.show_message("Chưa chọn dòng", "Chọn một hoặc nhiều ô trong bảng trước.")

    def _xuat(self) -> None:
        ten = "{0}-nghien-cuu-{1}.csv".format(self._kenh() or "kenh", self._loai)
        duong, _ = QFileDialog.getSaveFileName(
            self, "Xuất phần đang lọc", os.path.join(self._app.base_dir, ten), "Bảng CSV (*.csv)")
        if not duong:
            return
        try:
            dem = xuat_proxy(self._proxy, duong)
        except OSError as e:
            return self._app.show_error(e)
        self._app.show_message("Đã xuất", "Đã lưu {0} dòng vào:\n{1}".format(dem, duong))

    def _mo_quan_ly(self) -> None:
        from .trang_phan_tich import TrangDoiThu

        hop = QDialog(self)
        hop.setWindowTitle("Quản lý nghiên cứu đầy đủ")
        hop.resize(1220, 840)
        v = QVBoxLayout(hop)
        trang = TrangDoiThu(self._app)
        v.addWidget(trang, 1)
        hop.exec_()
        trang.close()
        hop.deleteLater()
        self.lam_moi()

