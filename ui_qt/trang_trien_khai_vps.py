"""Quy trình ba bước để chuyển kênh sang một VPS khác."""

from __future__ import annotations

import os
import threading
from typing import Dict

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit,
    QPlainTextEdit, QRadioButton, QScrollArea, QStackedWidget, QVBoxLayout,
    QWidget,
)

from core import goi_vps
from core.kenh import doc_kenh, liet_ke_kenh

from .widgets import mo_thu_muc, nhan, nut_chinh, nut_phu, the

__all__ = ["HopTrienKhaiVps"]


class HopTrienKhaiVps(QDialog):
    """Dẫn người dùng qua chọn kênh → cách chuyển → xác nhận."""

    tin_log = pyqtSignal(str)

    def __init__(self, app, cha=None):
        super().__init__(cha)
        self._app = app
        self._huy = threading.Event()
        self._dang_chay = False
        self._o_kenh: Dict[str, QCheckBox] = {}
        self._nhom: Dict[str, str] = {}
        self.setWindowTitle("Thêm VPS")
        self.resize(700, 650)

        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.addWidget(nhan("Thêm một VPS", "h1"))
        self._chi_buoc = nhan("Bước 1/3 · Chọn kênh", "muted")
        v.addWidget(self._chi_buoc)

        self._cac_buoc = QStackedWidget()
        self._cac_buoc.addWidget(self._buoc_chon_kenh())
        self._cac_buoc.addWidget(self._buoc_chon_cach())
        self._cac_buoc.addWidget(self._buoc_xac_nhan())
        v.addWidget(self._cac_buoc, 1)

        hang = QHBoxLayout()
        self._nut_lui = nut_phu("Quay lại", self._lui, rong=100)
        hang.addWidget(self._nut_lui)
        hang.addStretch(1)
        self._nut_dong = nut_phu("Đóng", self.reject, rong=88)
        hang.addWidget(self._nut_dong)
        self._nut_tiep = nut_chinh("Tiếp tục", self._tiep, rong=125)
        hang.addWidget(self._nut_tiep)
        self._nut_tao = nut_chinh("Tạo thư mục", self._bat_dau, rong=140)
        hang.addWidget(self._nut_tao)
        self._nut_huy = nut_phu("Dừng", self._dung, rong=80)
        hang.addWidget(self._nut_huy)
        v.addLayout(hang)

        self.tin_log.connect(self._log.appendPlainText)
        self._di_buoc(0)

    def _buoc_chon_kenh(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        v.addWidget(nhan(
            "Chọn những kênh VPS mới sẽ chăm. Một VPS nhận tối đa {0} kênh."
            .format(goi_vps.SO_KENH_TOI_DA_MOI_VPS)))

        hang = QHBoxLayout()
        self._chon_nhom = QComboBox()
        self._chon_nhom.addItem("Chọn nhanh theo nhóm chủ đề…", "")
        self._chon_nhom.activated.connect(self._chon_ca_nhom)
        hang.addWidget(self._chon_nhom, 1)
        hang.addWidget(nut_phu("Bỏ chọn tất cả", self._bo_chon, rong=125))
        v.addLayout(hang)

        self._tim = QLineEdit()
        self._tim.setPlaceholderText("Tìm kênh…")
        self._tim.setClearButtonEnabled(True)
        self._tim.textChanged.connect(self._loc_danh_sach)
        v.addWidget(self._tim)

        cac_nhom = set()
        khung_ds = QWidget()
        self._cot_kenh = QVBoxLayout(khung_ds)
        self._cot_kenh.setContentsMargins(4, 4, 4, 4)
        self._cot_kenh.setSpacing(7)
        for ma in liet_ke_kenh(self._app.base_dir):
            try:
                k = doc_kenh(self._app.base_dir, ma)
                nhom = k.nhom or "Kênh riêng"
                tep = k.tep or "chưa đặt khán giả"
                ten = k.ten or ma
            except Exception:  # noqa: BLE001
                nhom, tep, ten = "Kênh lỗi", "không đọc được cấu hình", ma
            o = QCheckBox("{0} — {1}\n{2} · {3}".format(ma, ten, nhom, tep))
            o.toggled.connect(self._cap_nhat_dem)
            self._cot_kenh.addWidget(o)
            self._o_kenh[ma] = o
            self._nhom[ma] = nhom
            cac_nhom.add(nhom)
        for ten_nhom in sorted(cac_nhom):
            self._chon_nhom.addItem(ten_nhom, ten_nhom)
        self._cot_kenh.addStretch(1)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        cuon.setWidget(khung_ds)
        v.addWidget(cuon, 1)

        self._nhan_dem = nhan("Chưa chọn kênh", "muted")
        v.addWidget(self._nhan_dem)
        return w

    def _buoc_chon_cach(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        v.addWidget(nhan("VPS mới sẽ tiếp tục việc cũ hay bắt đầu chủ đề mới?"))

        day_du = the()
        vd = QVBoxLayout(day_du)
        self._chon_day_du = QRadioButton("Chuyển kênh đang làm")
        self._chon_day_du.setChecked(True)
        vd.addWidget(self._chon_day_du)
        vd.addWidget(nhan(
            "Mang theo nghiên cứu, chỉ số và lịch đăng để VPS mới làm tiếp.",
            "muted"))
        v.addWidget(day_du)

        sach = the()
        vs = QVBoxLayout(sach)
        self._chon_sach = QRadioButton("Tạo kênh mới từ khuôn")
        vs.addWidget(self._chon_sach)
        vs.addWidget(nhan(
            "Giữ prompt, phong cách và cấu hình; bỏ lịch sử của kênh cũ.",
            "muted"))
        v.addWidget(sach)
        self._nhom_che_do = QButtonGroup(w)
        self._nhom_che_do.addButton(self._chon_day_du)
        self._nhom_che_do.addButton(self._chon_sach)

        v.addWidget(nhan("Nơi lưu thư mục để chép sang VPS mới", "h2"))
        hang = QHBoxLayout()
        self._dich = QLineEdit(os.path.join(
            self._app.base_dir, "workspace", "trien-khai"))
        hang.addWidget(self._dich, 1)
        hang.addWidget(nut_phu("Chọn…", self._chon_thu_muc, rong=85))
        v.addLayout(hang)
        v.addStretch(1)
        return w

    def _buoc_xac_nhan(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        v.addWidget(nhan("Kiểm tra trước khi tạo", "h2"))
        self._tom_tat = nhan("")
        self._tom_tat.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self._tom_tat)
        v.addWidget(nhan(
            "Sau khi tạo xong: chép nguyên thư mục sang VPS mới và chạy "
            "CAI-DAT-VM.bat.", "muted"))
        self._trang_thai = nhan("", "muted")
        v.addWidget(self._trang_thai)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Tiến trình tạo sẽ hiện ở đây.")
        v.addWidget(self._log, 1)
        return w

    def _di_buoc(self, so: int) -> None:
        so = max(0, min(2, int(so)))
        self._cac_buoc.setCurrentIndex(so)
        ten = ("Chọn kênh", "Chọn cách chuyển", "Xác nhận")[so]
        self._chi_buoc.setText("Bước {0}/3 · {1}".format(so + 1, ten))
        self._nut_lui.setVisible(so > 0 and not self._dang_chay)
        self._nut_tiep.setVisible(so < 2)
        self._nut_tao.setVisible(so == 2 and not self._dang_chay)
        self._nut_huy.setVisible(self._dang_chay)
        self._nut_dong.setEnabled(not self._dang_chay)
        if so == 2:
            self._cap_nhat_xac_nhan()

    def _tiep(self) -> None:
        buoc = self._cac_buoc.currentIndex()
        if buoc == 0:
            kenh = self._da_chon()
            if not kenh:
                self._app.show_message("Chưa chọn kênh", "Chọn ít nhất một kênh để tiếp tục.")
                return
            if len(kenh) > goi_vps.SO_KENH_TOI_DA_MOI_VPS:
                self._app.show_message(
                    "Đã chọn quá nhiều",
                    "Mỗi VPS nhận tối đa {0} kênh.".format(
                        goi_vps.SO_KENH_TOI_DA_MOI_VPS))
                return
        self._di_buoc(buoc + 1)

    def _lui(self) -> None:
        if not self._dang_chay:
            self._di_buoc(self._cac_buoc.currentIndex() - 1)

    def _da_chon(self):
        return [ma for ma, o in self._o_kenh.items() if o.isChecked()]

    def _cap_nhat_dem(self, _bat=False) -> None:
        n = len(self._da_chon())
        tran = goi_vps.SO_KENH_TOI_DA_MOI_VPS
        self._nhan_dem.setText(
            "Đã chọn {0}/{1} kênh".format(n, tran) if n else "Chưa chọn kênh")
        self._nhan_dem.setStyleSheet("color:#dc2626;" if n > tran else "")

    def _chon_ca_nhom(self, _chi_so=0) -> None:
        nhom = str(self._chon_nhom.currentData() or "")
        if not nhom:
            return
        ung_vien = [ma for ma in self._o_kenh if self._nhom[ma] == nhom]
        tran = goi_vps.SO_KENH_TOI_DA_MOI_VPS
        for ma, o in self._o_kenh.items():
            o.setChecked(ma in ung_vien[:tran])

    def _loc_danh_sach(self, chu: str) -> None:
        tim = str(chu or "").strip().casefold()
        for ma, o in self._o_kenh.items():
            o.setVisible(not tim or tim in (ma + " " + o.text()).casefold())

    def _bo_chon(self) -> None:
        for o in self._o_kenh.values():
            o.setChecked(False)

    def _chon_thu_muc(self) -> None:
        duong = QFileDialog.getExistingDirectory(
            self, "Nơi lưu thư mục cho VPS mới", self._dich.text().strip())
        if duong:
            self._dich.setText(duong)

    def _che_do_da_chon(self) -> str:
        return "cau_hinh" if self._chon_sach.isChecked() else "day_du"

    def _cap_nhat_xac_nhan(self) -> None:
        cach = ("Tạo kênh mới từ khuôn" if self._che_do_da_chon() == "cau_hinh"
                else "Chuyển kênh đang làm")
        self._tom_tat.setText(
            "Kênh: {0}\nCách chuyển: {1}\nLưu tại: {2}".format(
                ", ".join(self._da_chon()), cach, self._dich.text().strip()))

    def _bat_dau(self) -> None:
        if self._dang_chay:
            return
        kenh = self._da_chon()
        dich = self._dich.text().strip()
        if not kenh or len(kenh) > goi_vps.SO_KENH_TOI_DA_MOI_VPS:
            self._di_buoc(0)
            return
        if not dich:
            self._app.show_message("Chưa chọn nơi lưu", "Chọn nơi lưu thư mục cho VPS mới.")
            self._di_buoc(1)
            return
        self._dang_chay = True
        self._huy.clear()
        self._log.clear()
        self._trang_thai.setText("Đang tạo và tự kiểm tra…")
        self._di_buoc(2)
        goc = self._app.base_dir
        che_do = self._che_do_da_chon()

        def viec():
            return goi_vps.dong_goi_trien_khai(
                goc, kenh_mang_theo=kenh, thu_muc_dich=dich,
                che_do_kenh=che_do, on_log=self.tin_log.emit, cancel=self._huy)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._loi)

    def _dung(self) -> None:
        self._huy.set()
        self._trang_thai.setText("Đang dừng an toàn…")
        self._nut_huy.setEnabled(False)

    def _mo_lai_nut(self) -> None:
        self._dang_chay = False
        self._nut_huy.setEnabled(True)
        self._di_buoc(2)

    def _xong(self, ket) -> None:
        self._mo_lai_nut()
        if (ket or {}).get("huy"):
            self._trang_thai.setText("Đã dừng. Thư mục tạm đã được dọn.")
            return
        duong = str((ket or {}).get("thu_muc") or "")
        kiem = (ket or {}).get("kiem_tra") or {}
        self._trang_thai.setText(
            "Đã tạo xong và kiểm tra đạt · {0} kênh".format(
                len(kiem.get("kenh") or [])))
        if duong:
            mo_thu_muc(duong)
        self._app.show_message(
            "VPS mới đã sẵn sàng",
            "Chép nguyên thư mục vừa mở sang VPS mới, rồi chạy CAI-DAT-VM.bat.")

    def _loi(self, loi: BaseException) -> None:
        self._mo_lai_nut()
        self._trang_thai.setText("Không tạo được: " + str(loi)[:240])
        self._app.show_error(loi)

    def reject(self) -> None:
        if self._dang_chay:
            self._dung()
            return
        super().reject()
