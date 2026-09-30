"""Mặt Đăng & chăm kênh: lịch đăng, trạng thái phiên và thao tác theo video."""

from __future__ import annotations

from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QMessageBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import trung_tam as tt

from .widgets import nhan, nut_chinh, nut_phu, the

__all__ = ["TrangDangChamSocVps"]


def _gon(so) -> str:
    try:
        n = float(so)
    except (TypeError, ValueError):
        return "—"
    if n >= 1_000_000:
        return ("{0:.1f}tr".format(n / 1_000_000)).replace(".0tr", "tr")
    if n >= 1_000:
        return ("{0:.1f}k".format(n / 1_000)).replace(".0k", "k")
    return str(int(n))


class TrangDangChamSocVps(QWidget):
    """Một bảng vận hành sau sản xuất; không trộn công cụ nghiên cứu vào đây."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._kenh: List[Dict[str, Any]] = []
        self._da_nap = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(9)

        dau = QHBoxLayout()
        dau.addWidget(nhan("Đăng & chăm kênh", "h1"))
        dau.addWidget(nhan("Duyệt lịch đăng, ghi nhận video đăng tay và theo dõi phiên chăm kênh.", "muted"), 1)
        self._nut_moi = nut_phu("Làm mới", self.lam_moi, rong=90)
        dau.addWidget(self._nut_moi)
        doc.addLayout(dau)

        tom_tat = the()
        ht = QHBoxLayout(tom_tat)
        ht.setContentsMargins(12, 9, 12, 9)
        self._tom_tat = nhan("Đang đọc lịch đăng…", "muted")
        self._tom_tat.setWordWrap(True)
        ht.addWidget(self._tom_tat, 1)
        doc.addWidget(tom_tat)

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(12, 10, 12, 10)
        self._bang = QTableWidget(0, 6)
        self._bang.setHorizontalHeaderLabels((
            "Kênh", "Video", "Lịch đăng", "Trạng thái", "Chăm kênh", "Hiệu suất 7 ngày"))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setSelectionMode(QAbstractItemView.SingleSelection)
        self._bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang.setAlternatingRowColors(True)
        self._bang.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._bang.horizontalHeader().setStretchLastSection(True)
        self._bang.setColumnWidth(0, 120)
        self._bang.setColumnWidth(1, 290)
        self._bang.setColumnWidth(2, 120)
        self._bang.setColumnWidth(3, 180)
        self._bang.setColumnWidth(4, 130)
        self._bang.itemSelectionChanged.connect(self._chon_dong)
        v.addWidget(self._bang, 1)

        chan = QHBoxLayout()
        self._chi_tiet = nhan("Chọn một kênh để xử lý video cần đăng.", "muted")
        self._chi_tiet.setWordWrap(True)
        chan.addWidget(self._chi_tiet, 1)
        self._nut_hanh_dong = nut_chinh("Mở quản lý đăng", self._hanh_dong, rong=150)
        self._nut_hanh_dong.setEnabled(False)
        chan.addWidget(self._nut_hanh_dong)
        v.addLayout(chan)
        doc.addWidget(khung, 1)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._da_nap:
            self._da_nap = True
            self.lam_moi()

    def lam_moi(self) -> None:
        self._nut_moi.setEnabled(False)
        self._tom_tat.setText("Đang đọc lịch đăng và phiên chăm kênh…")
        goc = self._app.base_dir
        self._app.run_bg(lambda: tt.anh_chup(goc, tat_ca=True, co_nhom=False),
                         on_ok=self._ve, on_err=self._loi)

    def _loi(self, loi) -> None:
        self._nut_moi.setEnabled(True)
        self._tom_tat.setText("Không đọc được dữ liệu: " + str(loi)[:160])

    def _ve(self, anh) -> None:
        self._nut_moi.setEnabled(True)
        self._kenh = list(anh.get("kenh") or [])
        cho = sum(any(d.get("loai") == "cho_duyet" for d in k.get("ke_hoach") or []) for k in self._kenh)
        hen = sum(any(d.get("loai") == "sap_dang" for d in k.get("ke_hoach") or []) for k in self._kenh)
        phien = sum(bool((k.get("phien") or {}).get("xong_hom_nay")) for k in self._kenh)
        self._tom_tat.setText(
            "{0} kênh  ·  {1} video chờ duyệt  ·  {2} video đã hẹn  ·  {3}/{0} phiên chăm kênh đã chạy hôm nay"
            .format(len(self._kenh), cho, hen, phien))
        self._bang.setRowCount(len(self._kenh))
        for r, k in enumerate(self._kenh):
            bay = k.get("bay_gio") or {}
            video = k.get("video") or {}
            hq = k.get("bay_ngay") or {}
            ke_hoach = self._ke_hoach_can_lam(k)
            if ke_hoach:
                tieu_de = str(ke_hoach.get("tieu_de") or video.get("tieu_de") or "—")
                lich = "{0} {1}".format(
                    ke_hoach.get("ngay") or "Chưa chốt ngày",
                    ke_hoach.get("gio") or "").strip()
                loai = ke_hoach.get("loai")
                trang_thai = ("Chờ duyệt lịch" if loai == "cho_duyet"
                              else "Chờ đăng / xác nhận đăng tay")
            else:
                tieu_de = str(video.get("tieu_de") or "—")
                lich = str(k.get("dang_luc") or "—")
                trang_thai = str(bay.get("chu") or "Chưa có video chờ đăng")
            cham = "Đã chạy hôm nay" if (k.get("phien") or {}).get("xong_hom_nay") else "Chờ phiên tiếp theo"
            hieu_qua = "{0} view · CTR {1}".format(
                _gon(hq.get("views")),
                ("{0:.1f}%".format(float(hq["ctr"])) if hq.get("ctr") is not None else "—"))
            gia_tri = (
                k.get("ma") or "", tieu_de, lich, trang_thai, cham, hieu_qua,
            )
            for c, chu in enumerate(gia_tri):
                o = QTableWidgetItem(str(chu))
                o.setData(Qt.UserRole, r)
                o.setToolTip(str(bay.get("chi_tiet") or ""))
                self._bang.setItem(r, c, o)
        if self._kenh:
            self._bang.selectRow(0)

    def _dang_chon(self) -> Dict[str, Any]:
        r = self._bang.currentRow()
        return self._kenh[r] if 0 <= r < len(self._kenh) else {}

    def _ke_hoach_can_lam(self, k: Dict[str, Any]):
        ds = list(k.get("ke_hoach") or [])
        return (next((d for d in ds if d.get("loai") == "cho_duyet"), None)
                or next((d for d in ds if d.get("loai") == "sap_dang"), None))

    def _chon_dong(self) -> None:
        k = self._dang_chon()
        if not k:
            self._nut_hanh_dong.setEnabled(False)
            return
        d = self._ke_hoach_can_lam(k)
        self._nut_hanh_dong.setEnabled(True)
        if d and d.get("loai") == "cho_duyet":
            self._nut_hanh_dong.setText("Duyệt giờ đăng")
        elif d and d.get("loai") == "sap_dang":
            self._nut_hanh_dong.setText("Đã đăng thủ công")
        else:
            self._nut_hanh_dong.setText("Mở quản lý đăng")
        self._chi_tiet.setText(str((k.get("bay_gio") or {}).get("chi_tiet")
                                   or (k.get("bay_gio") or {}).get("chu") or ""))

    def _hanh_dong(self) -> None:
        k = self._dang_chon()
        if not k:
            return
        d = self._ke_hoach_can_lam(k)
        if d and d.get("loai") == "cho_duyet":
            from .trang_trung_tam import HopDuyet
            hop = HopDuyet(d, k.get("gio_dang") or "20:00", self)
            if hop.exec_() and tt.duyet_dang(
                    self._app.base_dir, k["ma"], d.get("ma_goi") or "", hop.ngay, hop.gio):
                self.lam_moi()
            return
        if d and d.get("loai") == "sap_dang":
            if QMessageBox.question(
                    self, "Đã đăng thủ công?",
                    "Xác nhận video này đã được đăng lên YouTube. Tool sẽ ghi trạng thái và không đăng lại.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            from core.ban_giao_dang import danh_dau_dang_tay
            danh_dau_dang_tay(self._app.base_dir, k["ma"], d.get("ma_goi") or "",
                              ghi_chu="Đánh dấu từ Đăng & chăm kênh")
            self.lam_moi()
            return
        self._mo_quan_ly_day_du()

    def _mo_quan_ly_day_du(self) -> None:
        from .trang_trung_tam import TrangTrungTam

        hop = QDialog(self)
        hop.setWindowTitle("Quản lý đăng & chăm kênh")
        hop.resize(1220, 840)
        v = QVBoxLayout(hop)
        trang = TrangTrungTam(self._app)
        v.addWidget(trang, 1)
        v.addWidget(nut_phu("Đóng", hop.accept, rong=90), 0, Qt.AlignRight)
        hop.exec_()
        trang.close()
        hop.deleteLater()
        self.lam_moi()
