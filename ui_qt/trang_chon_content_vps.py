"""Trang VPS “Chọn content” — một kênh, hai luồng chấm, một quyết định kế tiếp."""

from __future__ import annotations

from typing import List

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core import chon_content as cc
from core.kenh import liet_ke_kenh

from .widgets import HangXuongDong, nhan, nut_chinh, nut_nguy_hiem, nut_phu, the, tieu_de_trang

__all__ = ["TrangChonContentVps"]

_SO = Qt.UserRole + 1


class _OSo(QTableWidgetItem):
    def __lt__(self, khac):
        a, b = self.data(_SO), khac.data(_SO)
        if a is not None and b is not None:
            return a < b
        return super().__lt__(khac)


def _nghin(x) -> str:
    return "{0:,.0f}".format(x).replace(",", ".") if x else "—"


class TrangChonContentVps(QWidget):
    """Bảng ra quyết định; không chứa các thao tác nuôi dữ liệu Nghiên cứu."""

    LUONG = (("Đối thủ đang thắng", cc.LUONG_DOI_THU), ("Công thức V7", cc.LUONG_V7))

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._ung_vien: List[cc.UngVien] = []
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Chọn content",
            "Chỉ chốt khi sắp đến lịch làm. Mỗi kênh luôn có tối đa một content kế tiếp.",
        ))

        dau = the()
        hd = QVBoxLayout(dau)
        hd.setContentsMargins(18, 14, 18, 14)
        hd.setSpacing(8)
        hang = HangXuongDong()
        hang.addWidget(nhan("Kênh", "h2"))
        self._kenh = QComboBox()
        self._kenh.setMinimumWidth(180)
        self._kenh.addItems(liet_ke_kenh(app.base_dir))
        hang.addWidget(self._kenh)
        hang.addWidget(nhan("Cách chọn", "h2"))
        self._luong = QComboBox()
        self._luong.setMinimumWidth(190)
        for ten, ma in self.LUONG:
            self._luong.addItem(ten, ma)
        hang.addWidget(self._luong)
        self._nut_cham = nut_chinh("Chấm lại", self._tai, rong=110)
        hang.addWidget(self._nut_cham)
        hd.addLayout(hang)
        self._cong_thuc = nhan("", "phu")
        self._cong_thuc.setWordWrap(True)
        hd.addWidget(self._cong_thuc)
        doc.addWidget(dau)

        chot = the()
        hc = QVBoxLayout(chot)
        hc.setContentsMargins(18, 12, 18, 12)
        hc.setSpacing(5)
        hc.addWidget(nhan("Content kế tiếp đã chốt", "h2"))
        self._da_chot = nhan("Chưa chốt — khâu Sản xuất sẽ chờ.", "phu")
        self._da_chot.setWordWrap(True)
        hc.addWidget(self._da_chot)
        self._nut_bo = nut_nguy_hiem("Bỏ lựa chọn", self._bo_chot, rong=120)
        hc.addWidget(self._nut_bo, 0, Qt.AlignLeft)
        doc.addWidget(chot)

        bang_khung = the()
        vb = QVBoxLayout(bang_khung)
        vb.setContentsMargins(18, 14, 18, 14)
        vb.setSpacing(7)
        vb.addWidget(nhan("Ứng viên xếp theo điểm của cách chọn đang xem", "h2"))
        self._bang = QTableWidget(0, 7)
        self._bang.setHorizontalHeaderLabels(("Hạng", "Điểm", "Mức", "Tiêu đề", "Kênh nguồn", "View", "Tăng/ngày"))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setSelectionBehavior(QTableWidget.SelectRows)
        self._bang.setSelectionMode(QTableWidget.SingleSelection)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.setSortingEnabled(True)
        self._bang.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for i, rong in enumerate((48, 58, 86, 390, 150, 90, 95)):
            self._bang.setColumnWidth(i, rong)
        self._bang.setMinimumHeight(300)
        self._bang.itemSelectionChanged.connect(self._chon_dong)
        self._bang.cellDoubleClicked.connect(lambda _r, _c: self._mo_video())
        vb.addWidget(self._bang, 1)
        self._ly_do = QLabel("Chọn một dòng để xem công thức đã cộng điểm vì sao.")
        self._ly_do.setWordWrap(True)
        self._ly_do.setObjectName("muted")
        self._ly_do.setTextFormat(Qt.RichText)
        vb.addWidget(self._ly_do)
        nut = HangXuongDong()
        nut.addWidget(nut_phu("Mở video nguồn", self._mo_video, rong=135))
        self._nut_chot = nut_chinh("Chốt content này", self._chot, rong=150)
        nut.addWidget(self._nut_chot)
        self._trang_thai = nhan("", "phu")
        nut.addWidget(self._trang_thai)
        vb.addLayout(nut)
        doc.addWidget(bang_khung, 1)

        self._kenh.currentIndexChanged.connect(lambda _i: self._doi_kenh())
        self._luong.currentIndexChanged.connect(lambda _i: self._doi_luong())
        self._doi_luong()
        self._ve_da_chot()

    def _ma_kenh(self) -> str:
        return self._kenh.currentText().strip()

    def _ma_luong(self) -> str:
        return str(self._luong.currentData() or cc.LUONG_DOI_THU)

    def doi_du_an(self, ten: str) -> None:
        i = self._kenh.findText(ten)
        if i >= 0:
            self._kenh.setCurrentIndex(i)

    def showEvent(self, su_kien) -> None:  # noqa: N802
        super().showEvent(su_kien)
        self._ve_da_chot()
        if not self._ung_vien and self._ma_kenh():
            self._tai()

    def _doi_kenh(self) -> None:
        self._ung_vien = []
        self._ve_bang()
        self._ve_da_chot()
        if self.isVisible():
            self._tai()

    def _doi_luong(self) -> None:
        if self._ma_luong() == cc.LUONG_DOI_THU:
            chu = ("Đối thủ: 35% tốc độ hiện tại + 25% quy mô view + 20% tăng tốc + "
                   "20% vượt mức thường của kênh nguồn. Điểm là thứ hạng trong sổ đối thủ.")
        else:
            chu = ("V7: chấm theo cụm từng thắng, bảng video đề xuất, độ nổ của nguồn, "
                   "đà tăng và khuôn video. Điểm V7 không dùng để so trực tiếp với điểm Đối thủ.")
        self._cong_thuc.setText(chu)
        self._ung_vien = []
        self._ve_bang()
        if self.isVisible():
            self._tai()

    def _tai(self) -> None:
        kenh = self._ma_kenh()
        if not kenh or self._dang_chay:
            return
        self._dang_chay = True
        self._nut_cham.setEnabled(False)
        self._trang_thai.setText("đang đọc dữ liệu và chấm…")
        luong = self._ma_luong()

        def viec():
            return cc.lay_ung_vien(self._app.base_dir, kenh, luong, gioi_han=100)

        def xong(ds):
            self._dang_chay = False
            self._nut_cham.setEnabled(True)
            self._ung_vien = ds
            self._ve_bang()
            self._trang_thai.setText("{0} ứng viên đủ điều kiện; đang hiện ứng viên điểm cao trước.".format(len(ds)))

        def hong(loi):
            self._dang_chay = False
            self._nut_cham.setEnabled(True)
            self._trang_thai.setText("")
            self._app.show_error(loi)

        self._app.run_bg(viec, on_ok=xong, on_err=hong)

    @staticmethod
    def _o(chu: str, so_=None) -> QTableWidgetItem:
        muc = _OSo(chu) if so_ is not None else QTableWidgetItem(chu)
        if so_ is not None:
            muc.setData(_SO, float(so_))
        return muc

    def _ve_bang(self) -> None:
        self._bang.setSortingEnabled(False)
        self._bang.clearContents()
        self._bang.setRowCount(len(self._ung_vien))
        for r, d in enumerate(self._ung_vien):
            o = (self._o(str(r + 1), r + 1), self._o(str(d.diem), d.diem), self._o(d.muc),
                 self._o(d.tieu_de), self._o(d.kenh_nguon), self._o(_nghin(d.view), d.view),
                 self._o(_nghin(d.tang_ngay), d.tang_ngay))
            for c, muc in enumerate(o):
                muc.setData(Qt.UserRole, d.ma)
                muc.setToolTip(d.ly_do)
                self._bang.setItem(r, c, muc)
        self._bang.setSortingEnabled(True)
        self._bang.sortItems(1, Qt.DescendingOrder)
        self._ly_do.setText("Chọn một dòng để xem công thức đã cộng điểm vì sao.")

    def _dang_chon(self):
        r = self._bang.currentRow()
        muc = self._bang.item(r, 0) if r >= 0 else None
        ma = muc.data(Qt.UserRole) if muc else None
        return next((d for d in self._ung_vien if d.ma == ma), None)

    def _chon_dong(self) -> None:
        d = self._dang_chon()
        if d is None:
            return
        tp = " · ".join("{0} {1:g}".format(k, v) for k, v in d.thanh_phan.items())
        self._ly_do.setText("<b>{0} điểm — {1}</b><br>{2}<br><span style='color:#5f6368'>{3}</span>".format(
            d.diem, d.muc, d.ly_do, tp))

    def _mo_video(self) -> None:
        d = self._dang_chon()
        if d and d.link:
            QDesktopServices.openUrl(QUrl(d.link))

    def _chot(self) -> None:
        d = self._dang_chon()
        if d is None:
            self._app.show_message("Chưa chọn content", "Chọn một ứng viên trong bảng trước.")
            return
        cc.chot(self._app.base_dir, self._ma_kenh(), d)
        self._ve_da_chot()
        self._trang_thai.setText("Đã chuyển đúng một content sang khâu Sản xuất.")

    def _bo_chot(self) -> None:
        cc.bo_chot(self._app.base_dir, self._ma_kenh())
        self._ve_da_chot()

    def _ve_da_chot(self) -> None:
        lua = cc.doc_lua_chon(self._app.base_dir, self._ma_kenh()) if self._ma_kenh() else None
        self._nut_bo.setEnabled(lua is not None)
        if lua is None:
            self._da_chot.setText("Chưa chốt — khâu Sản xuất sẽ chờ.")
            return
        ten_luong = "Đối thủ" if lua.ung_vien.luong == cc.LUONG_DOI_THU else "V7"
        self._da_chot.setText("<b>{0}</b> · {1} điểm theo {2} · {3} · chốt {4}".format(
            lua.ung_vien.tieu_de, lua.ung_vien.diem, ten_luong, lua.trang_thai,
            lua.ngay_chot.replace("T", " ")))
