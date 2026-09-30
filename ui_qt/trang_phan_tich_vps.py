"""Sổ Dữ liệu & nội dung VPS: một màn hình quản lý như bảng tính."""

from __future__ import annotations

import os
from typing import Any, Dict

from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMenu, QToolButton, QVBoxLayout, QWidget,
)

from core import bang_du_lieu_vps as dl
from core import tong_quan_vps as tq
from core import trung_tam as tt
from core.kenh import liet_ke_kenh

from .bang_du_lieu_vps import BangModel, BangProxy, BangView, xuat_proxy
from .widgets import nhan, nut_chinh, the

__all__ = ["TrangPhanTichVps"]


def _gon(so: Any) -> str:
    try:
        n = float(so)
    except (TypeError, ValueError):
        return "—"
    if abs(n) >= 1_000_000:
        return ("{0:.1f}tr".format(n / 1_000_000)).replace(".0tr", "tr")
    if abs(n) >= 1_000:
        return ("{0:.1f}k".format(n / 1_000)).replace(".0k", "k")
    return str(int(n)) if n.is_integer() else "{0:.1f}".format(n)


def _pt(so: Any) -> str:
    try:
        return "{0:.1f}%".format(float(so))
    except (TypeError, ValueError):
        return "—"


class TrangPhanTichVps(QWidget):
    """Luồng cố định: chọn bảng → tìm/lọc → chọn dòng → hành động."""

    _THU_TU = (dl.V7, dl.CONTENT, dl.DOI_THU, dl.HIEU_QUA)

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._loai = dl.V7
        self._cache: Dict[tuple, Dict[str, Any]] = {}
        self._dang_nap = set()
        self._da_nap = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(9)

        dau = QHBoxLayout()
        dau.addWidget(nhan("Dữ liệu & nội dung", "h1"))
        dau.addStretch(1)
        dau.addWidget(nhan("Kênh", "muted"))
        self._chon = QComboBox()
        self._chon.addItems(liet_ke_kenh(app.base_dir))
        self._chon.setMinimumWidth(170)
        self._chon.currentTextChanged.connect(self._doi_kenh)
        dau.addWidget(self._chon)
        doc.addLayout(dau)

        self._tom_tat = nhan("Đang đọc tổng quan kênh…", "muted")
        self._tom_tat.setWordWrap(True)
        doc.addWidget(self._tom_tat)

        ban = the()
        v = QVBoxLayout(ban)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)

        cong_cu = QHBoxLayout()
        cong_cu.addWidget(nhan("Bảng"))
        self._chon_bo = QComboBox()
        self._chon_bo.setMinimumWidth(190)
        for loai in self._THU_TU:
            self._chon_bo.addItem(dl.NHAN[loai], loai)
        self._chon_bo.currentIndexChanged.connect(self._doi_bo_tu_o_chon)
        cong_cu.addWidget(self._chon_bo)
        cong_cu.addWidget(nhan("Lọc"))
        self._loc = QComboBox()
        self._loc.setMinimumWidth(150)
        self._loc.currentIndexChanged.connect(self._ap_loc)
        cong_cu.addWidget(self._loc)
        cong_cu.addStretch(1)
        v.addLayout(cong_cu)

        hang_tim = QHBoxLayout()
        self._cot_tim = QComboBox()
        self._cot_tim.setMinimumWidth(125)
        self._cot_tim.addItem("Tất cả cột", "")
        self._cot_tim.currentIndexChanged.connect(self._ap_loc)
        hang_tim.addWidget(self._cot_tim)
        self._tim = QLineEdit()
        self._tim.setPlaceholderText("Tìm trong toàn bộ bảng…")
        self._tim.setClearButtonEnabled(True)
        self._tim.textChanged.connect(self._cho_tim)
        hang_tim.addWidget(self._tim, 1)
        self._dem = nhan("0 dòng", "muted")
        hang_tim.addWidget(self._dem)
        self._nut_them = QToolButton()
        self._nut_them.setText("Thêm  ▾")
        self._nut_them.setPopupMode(QToolButton.InstantPopup)
        self._menu = QMenu(self._nut_them)
        self._menu.addAction("Làm mới dữ liệu", self.lam_moi)
        self._menu.addSeparator()
        self._act_mo_link = self._menu.addAction("Mở link của dòng", self._mo_link)
        self._menu.addAction("Sao chép dòng đã chọn", self._chep)
        self._menu.addAction("Xuất phần đang lọc ra CSV…", self._xuat)
        self._menu.addSeparator()
        self._act_quan_ly = self._menu.addAction("Mở quản lý chi tiết…", self._mo_chuyen_sau)
        self._nut_them.setMenu(self._menu)
        hang_tim.addWidget(self._nut_them)
        v.addLayout(hang_tim)

        self._huong_dan = nhan(dl.MO_TA[self._loai], "muted")
        self._huong_dan.setWordWrap(True)
        v.addWidget(self._huong_dan)

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
        self._bang.selectionModel().selectionChanged.connect(self._ve_chi_tiet)
        self._bang.doubleClicked.connect(self._double_click)
        self._bang.yeu_cau_menu.connect(self._menu_dong)
        v.addWidget(self._bang, 1)

        chan = QHBoxLayout()
        self._chi_tiet = QLabel("Chọn một dòng để xem đầy đủ. Cột có biểu tượng ✎ có thể sửa trực tiếp.")
        self._chi_tiet.setWordWrap(True)
        self._chi_tiet.setMinimumHeight(42)
        self._chi_tiet.setTextInteractionFlags(Qt.TextSelectableByMouse)
        chan.addWidget(self._chi_tiet, 1)
        self._nut_hanh_dong = nut_chinh("Đánh dấu đã dùng", self._hanh_dong_chinh, rong=158)
        self._nut_hanh_dong.setEnabled(False)
        chan.addWidget(self._nut_hanh_dong)
        v.addLayout(chan)

        self._trang_thai = nhan("Dữ liệu trên máy · click tiêu đề cột để sắp xếp", "muted")
        v.addWidget(self._trang_thai)
        doc.addWidget(ban, 1)

        self._cho_go = QTimer(self)
        self._cho_go.setSingleShot(True)
        self._cho_go.setInterval(250)
        self._cho_go.timeout.connect(self._ap_loc)
        self._nap_danh_sach_loc()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._da_nap:
            self._da_nap = True
            self._nap_tong_quan()
            self._nap_bo_du_lieu()

    def _kenh(self) -> str:
        return self._chon.currentText().strip()

    def _doi_kenh(self, _ma="") -> None:
        self._tim.clear()
        self._nap_tong_quan()
        self._nap_bo_du_lieu()

    def lam_moi(self) -> None:
        ma = self._kenh()
        self._cache = {k: v for k, v in self._cache.items() if k[0] != ma}
        self._nap_tong_quan()
        self._nap_bo_du_lieu()

    def _nap_tong_quan(self) -> None:
        ma = self._kenh()
        if not ma:
            self._tom_tat.setText("Chưa có kênh để hiển thị.")
            return
        goc = self._app.base_dir

        def viec():
            anh = tt.anh_chup(goc, tat_ca=True, co_nhom=False)
            kenh = next((k for k in anh.get("kenh") or [] if k.get("ma") == ma), {})
            return ma, kenh, tq.tom_tat_phan_tich(goc, ma)

        self._app.run_bg(viec, on_ok=self._ve_tong_quan,
                         on_err=lambda e: self._tom_tat.setText("Không đọc được tổng quan: " + str(e)[:140]))

    def _ve_tong_quan(self, ket) -> None:
        ma, kenh, phan_tich = ket
        if ma != self._kenh():
            return
        n7, y = kenh.get("bay_ngay") or {}, kenh.get("ypp") or {}
        d, nd, v7 = phan_tich["doi_thu"], phan_tich["noi_dung"], phan_tich["v7"]
        self._tom_tat.setText(
            "7 ngày: {0} xem · {1} video · CTR {2}    |    YPP: {3} giờ · {4} ĐK    |    "
            "{5} đối thủ · {6} video nguồn · {7} V7 đã chấm".format(
                _gon(n7.get("views")), n7.get("so_video") or 0, _pt(n7.get("ctr")),
                _gon(y.get("gio_xem")), _gon(y.get("dang_ky")), d["so_kenh"],
                _gon(nd["so_video"]), v7["so_da_cham"]))

    def _doi_bo_tu_o_chon(self, _i=0) -> None:
        self._doi_bo_du_lieu(str(self._chon_bo.currentData() or dl.V7))

    def _doi_bo_du_lieu(self, loai: str) -> None:
        if loai not in self._THU_TU:
            return
        i = self._chon_bo.findData(loai)
        if i >= 0 and i != self._chon_bo.currentIndex():
            self._chon_bo.blockSignals(True)
            self._chon_bo.setCurrentIndex(i)
            self._chon_bo.blockSignals(False)
        if loai == self._loai:
            return
        self._loai = loai
        self._tim.clear()
        self._nap_danh_sach_loc()
        self._nap_bo_du_lieu()

    def _nap_danh_sach_loc(self) -> None:
        self._loc.blockSignals(True)
        self._loc.clear()
        for nhan_loc, ma_loc in dl.LOC_NHANH[self._loai]:
            self._loc.addItem(nhan_loc, ma_loc)
        self._loc.blockSignals(False)
        self._huong_dan.setText(dl.MO_TA[self._loai])
        self._act_quan_ly.setText({dl.V7: "Mở Công thức V7…", dl.CONTENT: "Sửa kho content…",
                                   dl.DOI_THU: "Mở quản lý đối thủ…",
                                   dl.HIEU_QUA: "Mở toàn bộ chỉ số…"}[self._loai])
        la_content = self._loai in (dl.V7, dl.CONTENT)
        self._nut_hanh_dong.setText("Đánh dấu đã dùng" if la_content else {
            dl.DOI_THU: "Quản lý đối thủ", dl.HIEU_QUA: "Xem toàn bộ chỉ số"}[self._loai])
        self._cap_nhat_hanh_dong()

    def _nap_bo_du_lieu(self) -> None:
        ma, loai = self._kenh(), self._loai
        if not ma:
            return
        khoa = (ma, loai)
        if khoa in self._cache:
            return self._ve_bo_du_lieu((ma, loai, self._cache[khoa]))
        if khoa in self._dang_nap:
            return
        self._dang_nap.add(khoa)
        self._trang_thai.setText("Đang đọc {0} của {1}…".format(dl.NHAN[loai].lower(), ma))
        self._model.dat([], [])
        self._dem.setText("đang đọc…")
        goc = self._app.base_dir

        def viec():
            return ma, loai, dl.doc_bo_du_lieu(goc, ma, loai)

        def loi(e):
            self._dang_nap.discard(khoa)
            self._trang_thai.setText("Không đọc được dữ liệu: " + str(e)[:150])

        self._app.run_bg(viec, on_ok=self._ve_bo_du_lieu, on_err=loi)

    def _ve_bo_du_lieu(self, ket) -> None:
        ma, loai, bo = ket
        self._dang_nap.discard((ma, loai))
        self._cache[(ma, loai)] = bo
        if ma != self._kenh() or loai != self._loai:
            return
        self._model.dat(bo["cot"], bo["hang"], self._sua_o)
        khoa_cu = str(self._cot_tim.currentData() or "")
        self._cot_tim.blockSignals(True)
        self._cot_tim.clear()
        self._cot_tim.addItem("Tất cả cột", "")
        for c in bo["cot"]:
            self._cot_tim.addItem(c["nhan"], c["khoa"])
        vi_tri = self._cot_tim.findData(khoa_cu)
        self._cot_tim.setCurrentIndex(max(0, vi_tri))
        self._cot_tim.blockSignals(False)
        for i, c in enumerate(bo["cot"]):
            self._bang.setColumnWidth(i, c.get("rong", 110))
        self._proxy.dat_loc(loai, str(self._loc.currentData() or ""), self._tim.text(),
                            str(self._cot_tim.currentData() or ""))
        self._cap_nhat_dem()
        self._chi_tiet.setText("Chọn một dòng để xem đầy đủ. Cột có biểu tượng ✎ có thể sửa trực tiếp.")
        self._trang_thai.setText("{0} dòng · click tiêu đề cột để sắp xếp · click đúp ô ✎ để sửa".format(
            len(bo["hang"])))
        self._cap_nhat_hanh_dong()

    def _sua_o(self, dong: Dict[str, Any], khoa: str, gia_tri: str) -> bool:
        try:
            dl.sua_o_quan_ly(self._app.base_dir, self._kenh(), self._loai, dong, khoa, gia_tri)
        except (OSError, ValueError) as e:
            self._app.show_error(e)
            return False
        self._cache.pop((self._kenh(), self._loai), None)
        self._trang_thai.setText("Đã lưu {0}.".format(khoa.lower()))
        return True

    def _cho_tim(self, _chu: str) -> None:
        self._cho_go.start()

    def _ap_loc(self, _i=0) -> None:
        self._proxy.dat_loc(self._loai, str(self._loc.currentData() or ""), self._tim.text(),
                            str(self._cot_tim.currentData() or ""))
        self._cap_nhat_dem()

    def _cap_nhat_dem(self) -> None:
        self._dem.setText("{0:,} / {1:,} dòng".format(
            self._proxy.rowCount(), self._model.rowCount()).replace(",", "."))

    def _dong_chon(self) -> Dict[str, Any]:
        i = self._bang.currentIndex()
        return self._model.dong(self._proxy.mapToSource(i).row()) if i.isValid() else {}

    def _ve_chi_tiet(self, *_a) -> None:
        d = self._dong_chon()
        if d:
            t = d.get("Tiêu đề hiển thị") or d.get("Tiêu đề") or d.get("Kênh") or ""
            p = d.get("Lý do") or d.get("Ghi chú") or d.get("Tuyến / Kênh") or ""
            self._chi_tiet.setText((str(t) + ("\n" + str(p) if p else ""))[:900])
        self._cap_nhat_hanh_dong()

    def _cap_nhat_hanh_dong(self) -> None:
        co_link = bool(dl.link_cua_dong(self._loai, self._dong_chon()))
        self._act_mo_link.setEnabled(co_link)
        if self._loai not in (dl.V7, dl.CONTENT):
            self._nut_hanh_dong.setEnabled(bool(self._kenh()))
            return
        d = self._dong_chon()
        da = str(d.get("Đã dùng" if self._loai == dl.V7 else "Đã làm") or "").strip()
        self._nut_hanh_dong.setEnabled(co_link and not da)
        self._nut_hanh_dong.setText("Đã ghi nhận" if da else "Đánh dấu đã dùng")
        self._act_mo_link.setEnabled(co_link)

    def _double_click(self, i) -> None:
        src = self._proxy.mapToSource(i)
        if src.isValid() and self._model.la_cot_sua(src.column()):
            return
        self._mo_link()

    def _menu_dong(self, diem) -> None:
        i = self._bang.indexAt(diem)
        if i.isValid() and not self._bang.selectionModel().isSelected(i):
            self._bang.selectRow(i.row())
        menu = QMenu(self)
        if self._loai in (dl.V7, dl.CONTENT):
            a = menu.addAction("Đánh dấu đã dùng", self._danh_dau_da_dung)
            a.setEnabled(self._nut_hanh_dong.isEnabled())
        menu.addAction("Mở link", self._mo_link).setEnabled(bool(dl.link_cua_dong(self._loai, self._dong_chon())))
        menu.addAction("Sao chép", self._chep)
        menu.exec_(self._bang.viewport().mapToGlobal(diem))

    def _hanh_dong_chinh(self) -> None:
        self._danh_dau_da_dung() if self._loai in (dl.V7, dl.CONTENT) else self._mo_chuyen_sau()

    def _chep(self) -> None:
        if not self._bang.chep_vung_chon():
            self._app.show_message("Chưa chọn dòng", "Chọn một hoặc nhiều dòng trong bảng trước.")

    def _xuat(self) -> None:
        ten = "{0}-{1}-da-loc.csv".format(self._kenh() or "kenh", self._loai)
        duong, _ = QFileDialog.getSaveFileName(self, "Xuất phần đang lọc", os.path.join(
            self._app.base_dir, ten), "Bảng CSV (*.csv)")
        if not duong:
            return
        try:
            dem = xuat_proxy(self._proxy, duong)
        except OSError as e:
            return self._app.show_error(e)
        self._app.show_message("Đã xuất", "Đã lưu {0} dòng vào:\n{1}".format(dem, duong))

    def _mo_link(self) -> None:
        link = dl.link_cua_dong(self._loai, self._dong_chon())
        if link.startswith(("http://", "https://")):
            QDesktopServices.openUrl(QUrl(link))
        else:
            self._app.show_message("Dòng này chưa có link", "Chọn dòng có link video hoặc link kênh.")

    def _danh_dau_da_dung(self) -> None:
        from core.da_lam import ghi_da_lam_tay
        link = dl.link_cua_dong(self._loai, self._dong_chon())
        if not link:
            return self._app.show_message("Chưa chọn nguồn", "Chọn một content có link trước.")
        if not ghi_da_lam_tay(self._app.base_dir, self._kenh(), link, "đánh dấu từ Dữ liệu & nội dung"):
            return self._app.show_message("Đã có trong sổ", "Content này đã được ghi nhận hoặc link không hợp lệ.")
        self._cache.pop((self._kenh(), dl.CONTENT), None)
        self._cache.pop((self._kenh(), dl.V7), None)
        self._app.show_message("Đã ghi nhận", "V7 sẽ không đề xuất lại nguồn content này.")
        self._nap_bo_du_lieu()

    def _mo_chuyen_sau(self) -> None:
        hop = QDialog(self)
        if self._loai == dl.V7:
            from .trang_cong_thuc_v7 import TrangCongThucV7
            hop.setWindowTitle("Công thức V7")
            trang = TrangCongThucV7(self._app)
        elif self._loai in (dl.CONTENT, dl.DOI_THU):
            from .trang_phan_tich import TrangDoiThu
            hop.setWindowTitle("Kho content và đối thủ")
            trang = TrangDoiThu(self._app)
        else:
            from .trang_chi_so_ytb import TrangChiSoYTB
            hop.setWindowTitle("Chỉ số kênh")
            trang = TrangChiSoYTB(self._app, phan=("doc",))
        hop.resize(1220, 840)
        v = QVBoxLayout(hop)
        v.addWidget(trang, 1)
        v.addWidget(nut_chinh("Đóng", hop.accept, rong=90), 0, Qt.AlignRight)
        hop.exec_()
        trang.close()
        hop.deleteLater()
        self.lam_moi()
