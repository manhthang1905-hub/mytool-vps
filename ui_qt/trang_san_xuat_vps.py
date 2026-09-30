"""Mặt Sản xuất trên VPS: quản lý khuôn prompt và theo dõi video đang làm."""

from __future__ import annotations

from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QHeaderView, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPlainTextEdit, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import trung_tam as tt
from core import chon_content as cc
from core.dong_bo_kenh import doc_prompts, ghi_prompts
from core.kenh import liet_ke_kenh

from .widgets import nhan, nut_chinh, nut_phu, the

__all__ = ["TrangSanXuatVps"]


class TrangSanXuatVps(QWidget):
    """Một kênh, một bộ prompt, một trạng thái sản xuất tại một thời điểm."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._prompts: List[Tuple[str, str, str]] = []
        self._cac_hang = []
        self._tep = ""
        self._da_nap = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(9)

        dau = QHBoxLayout()
        dau.addWidget(nhan("Sản xuất", "h1"))
        dau.addWidget(nhan("Quản lý công thức tạo video của từng kênh và xem lượt đang chạy.", "muted"), 1)
        dau.addWidget(nhan("Kênh", "muted"))
        self._kenh = QComboBox()
        self._kenh.addItems(liet_ke_kenh(app.base_dir))
        self._kenh.setMinimumWidth(170)
        self._kenh.currentTextChanged.connect(self._doi_kenh)
        dau.addWidget(self._kenh)
        doc.addLayout(dau)

        thong_bao = the()
        vb = QHBoxLayout(thong_bao)
        vb.setContentsMargins(12, 8, 12, 8)
        self._may = nhan(
            "VPS chạy tuần tự · một kênh, một việc nặng · xong mới chuyển kênh", "h2")
        vb.addWidget(self._may, 1)
        doc.addWidget(thong_bao)

        hang_loc = QHBoxLayout()
        hang_loc.addWidget(nhan("Hàng đợi kênh", "h2"))
        hang_loc.addStretch(1)
        self._tim = QLineEdit()
        self._tim.setPlaceholderText("Tìm kênh hoặc content…")
        self._tim.setClearButtonEnabled(True)
        self._tim.setMaximumWidth(270)
        self._tim.textChanged.connect(self._loc_hang)
        hang_loc.addWidget(self._tim)
        self._loc = QComboBox()
        self._loc.addItems(["Tất cả", "Đang làm", "Chờ đăng", "Chờ sản xuất", "Đang nghỉ"])
        self._loc.currentTextChanged.connect(self._loc_hang)
        hang_loc.addWidget(self._loc)
        doc.addLayout(hang_loc)

        self._bang = QTableWidget(0, 7)
        self._bang.setHorizontalHeaderLabels([
            "Thứ tự", "Kênh", "Tình trạng", "Content / video",
            "Tiến độ", "Chờ đăng", "Việc tiếp theo"])
        self._bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setSelectionMode(QAbstractItemView.SingleSelection)
        self._bang.setAlternatingRowColors(True)
        self._bang.setSortingEnabled(True)
        self._bang.verticalHeader().setVisible(False)
        dau_bang = self._bang.horizontalHeader()
        dau_bang.setSectionResizeMode(QHeaderView.ResizeToContents)
        dau_bang.setSectionResizeMode(3, QHeaderView.Stretch)
        dau_bang.setSectionResizeMode(6, QHeaderView.Stretch)
        self._bang.cellClicked.connect(self._chon_hang)
        doc.addWidget(self._bang, 2)

        trang_thai = the()
        vt = QVBoxLayout(trang_thai)
        vt.setContentsMargins(12, 9, 12, 9)
        vt.addWidget(nhan("Video hiện tại", "h2"))
        self._content = nhan("Content kế tiếp: đang kiểm tra…", "muted")
        self._content.setWordWrap(True)
        vt.addWidget(self._content)
        self._tinh_hinh = nhan("Đang đọc trạng thái sản xuất…", "muted")
        self._tinh_hinh.setWordWrap(True)
        vt.addWidget(self._tinh_hinh)
        doc.addWidget(trang_thai)

        khung = the()
        vk = QVBoxLayout(khung)
        vk.setContentsMargins(12, 10, 12, 10)
        vk.setSpacing(8)

        hang = QHBoxLayout()
        hang.addWidget(nhan("Các bước tạo video", "h2"))
        hang.addStretch(1)
        self._nut_luu = nut_chinh("Lưu prompt", self._luu, rong=120)
        self._nut_luu.setEnabled(False)
        hang.addWidget(self._nut_luu)
        hang.addWidget(nut_phu("Mở quy trình video", self._mo_quy_trinh, rong=145))
        vk.addLayout(hang)

        tach = QSplitter(Qt.Horizontal)
        self._ds = QListWidget()
        self._ds.setMinimumWidth(190)
        self._ds.setMaximumWidth(270)
        self._ds.currentRowChanged.connect(self._chon_prompt)
        tach.addWidget(self._ds)

        ben_phai = QWidget()
        vp = QVBoxLayout(ben_phai)
        vp.setContentsMargins(8, 0, 0, 0)
        self._ten_prompt = nhan("Chọn một bước", "h2")
        vp.addWidget(self._ten_prompt)
        self._noi_dung = QPlainTextEdit()
        self._noi_dung.setPlaceholderText("Prompt của bước sản xuất sẽ hiện ở đây.")
        self._noi_dung.textChanged.connect(self._da_sua)
        vp.addWidget(self._noi_dung, 1)
        self._ghi_chu = nhan("Chỉ sửa khi muốn đổi cách kênh này viết, tạo cảnh hoặc làm ảnh bìa.", "muted")
        self._ghi_chu.setWordWrap(True)
        vp.addWidget(self._ghi_chu)
        tach.addWidget(ben_phai)
        tach.setStretchFactor(1, 1)
        vk.addWidget(tach, 1)
        doc.addWidget(khung, 2)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._da_nap:
            self._da_nap = True
            self._nap()

    def _ma(self) -> str:
        return self._kenh.currentText().strip()

    def _doi_kenh(self, _ma="") -> None:
        if self._da_nap:
            self._nap()

    def _nap(self) -> None:
        ma = self._ma()
        self._tep = ""
        self._ds.clear()
        self._noi_dung.clear()
        self._noi_dung.setEnabled(False)
        self._nut_luu.setEnabled(False)
        if not ma:
            self._content.setText("Content kế tiếp: chưa có kênh.")
            self._tinh_hinh.setText("Chưa có kênh.")
            return
        lua = cc.doc_lua_chon(self._app.base_dir, ma)
        if lua is None:
            self._content.setText(
                "Content kế tiếp: chưa chốt. Tool sẽ chấm lại và chọn sát cửa sản xuất.")
        else:
            luong = "đối thủ" if lua.ung_vien.luong == cc.LUONG_DOI_THU else "V7"
            self._content.setText(
                "Content kế tiếp: {0} · {1} điểm theo {2} · {3}.".format(
                    lua.ung_vien.tieu_de, lua.ung_vien.diem, luong, lua.trang_thai))
        try:
            self._prompts = doc_prompts(self._app.base_dir, ma)
        except Exception as loi:  # noqa: BLE001
            self._prompts = []
            self._app.show_error(loi)
        for ten, ten_hien, _chu in self._prompts:
            muc = QListWidgetItem(ten_hien)
            muc.setData(Qt.UserRole, ten)
            self._ds.addItem(muc)
        if self._prompts:
            self._ds.setCurrentRow(0)
        else:
            self._ten_prompt.setText("Kênh chưa có bộ prompt")

        goc = self._app.base_dir

        def viec():
            anh = tt.anh_chup(goc, tat_ca=True, co_nhom=False)
            cac = anh.get("kenh") or []
            return ma, next((k for k in cac if k.get("ma") == ma), {}), cac

        self._app.run_bg(viec, on_ok=self._ve_trang_thai,
                         on_err=lambda e: self._tinh_hinh.setText("Không đọc được trạng thái: " + str(e)[:140]))

    def _ve_trang_thai(self, ket) -> None:
        ma, k, cac = ket
        self._ve_hang_doi(cac)
        if ma != self._ma():
            return
        bay = k.get("bay_gio") or {}
        video = k.get("video") or {}
        luot = k.get("luot") or {}
        khau = next((x for x in luot.get("khau") or [] if x.get("trang_thai") == "dang"), {})
        chu = str(bay.get("chu") or "Chưa có lượt sản xuất")
        tieu_de = str(video.get("tieu_de") or "").strip()
        if tieu_de:
            chu += "  ·  " + tieu_de
        if khau.get("ten"):
            chu += "  ·  " + str(khau["ten"])
        self._tinh_hinh.setText(chu)

    @staticmethod
    def _hang_tu_kenh(k: dict) -> dict:
        ma = str(k.get("ma") or "")
        bay = k.get("bay_gio") or {}
        video = k.get("video") or {}
        luot = k.get("luot") or {}
        khau = luot.get("khau") or []
        dang = next((x for x in khau if x.get("trang_thai") == "dang"), {})
        so_xong = sum(1 for x in khau if x.get("trang_thai") == "xong")
        cho_dang = len(k.get("ke_hoach") or [])
        dang_chay = bool(k.get("dang_chay") or dang)
        tieu_de = str(video.get("tieu_de") or (luot.get("nguon") or {}).get("tieu_de") or "")
        if dang_chay:
            nhom = "Đang làm"
            tiep = "Hoàn tất kênh này rồi mới chuyển kênh sau"
        elif cho_dang:
            nhom = "Chờ đăng"
            tiep = "Xử lý tại tab Đăng & chăm kênh"
        elif tieu_de:
            nhom = "Chờ sản xuất"
            tiep = "Tool tự chạy khi sát lịch đăng"
        else:
            nhom = "Đang nghỉ"
            tiep = "Chờ dữ liệu mới và lần chấm content kế tiếp"
        tien_do = (str(dang.get("ten") or "đang xử lý") if dang_chay
                    else ("{0}/8 khâu".format(so_xong) if khau else "—"))
        return {"ma": ma, "nhom": nhom, "tinh_trang": str(bay.get("chu") or nhom),
                "tieu_de": tieu_de or "Chưa chốt content", "tien_do": tien_do,
                "cho_dang": cho_dang, "tiep": tiep,
                "uu_tien": 0 if dang_chay else 1 if cho_dang else 2 if tieu_de else 3}

    def _ve_hang_doi(self, cac) -> None:
        self._cac_hang = [self._hang_tu_kenh(k) for k in (cac or [])]
        self._cac_hang.sort(key=lambda x: (x["uu_tien"], x["ma"]))
        self._loc_hang()
        dang = next((x for x in self._cac_hang if x["nhom"] == "Đang làm"), None)
        self._may.setText(
            ("Đang xử lý {0} · các kênh khác đang xếp hàng".format(dang["ma"]))
            if dang else "VPS đang rảnh · khi có việc sẽ chạy một kênh đến hết rồi mới chuyển kênh")

    def _loc_hang(self, *_args) -> None:
        tim = self._tim.text().strip().casefold() if hasattr(self, "_tim") else ""
        loc = self._loc.currentText() if hasattr(self, "_loc") else "Tất cả"
        hang = [x for x in self._cac_hang
                if (loc == "Tất cả" or x["nhom"] == loc)
                and (not tim or tim in (x["ma"] + " " + x["tieu_de"] + " " + x["tinh_trang"]).casefold())]
        self._bang.setSortingEnabled(False)
        self._bang.setRowCount(len(hang))
        for r, x in enumerate(hang):
            gia_tri = [str(r + 1), x["ma"], x["tinh_trang"], x["tieu_de"],
                       x["tien_do"], str(x["cho_dang"]), x["tiep"]]
            for c, chu in enumerate(gia_tri):
                o = QTableWidgetItem(chu)
                o.setData(Qt.UserRole, x["ma"])
                if c in (0, 5):
                    o.setTextAlignment(Qt.AlignCenter)
                self._bang.setItem(r, c, o)
        self._bang.setSortingEnabled(True)

    def _chon_hang(self, dong: int, _cot: int) -> None:
        o = self._bang.item(dong, 0)
        ma = str(o.data(Qt.UserRole) or "") if o else ""
        i = self._kenh.findText(ma)
        if i >= 0 and i != self._kenh.currentIndex():
            self._kenh.setCurrentIndex(i)

    def _chon_prompt(self, dong: int) -> None:
        if dong < 0 or dong >= len(self._prompts):
            return
        ten, ten_hien, chu = self._prompts[dong]
        self._tep = ten
        self._ten_prompt.setText(ten_hien)
        self._noi_dung.blockSignals(True)
        self._noi_dung.setPlainText(chu)
        self._noi_dung.blockSignals(False)
        self._noi_dung.setEnabled(True)
        self._nut_luu.setEnabled(False)
        self._ghi_chu.setText("Đang dùng tệp {0}. Sửa xong bấm Lưu prompt.".format(ten))

    def _da_sua(self) -> None:
        self._nut_luu.setEnabled(bool(self._tep and self._noi_dung.toPlainText().strip()))

    def _luu(self) -> None:
        if not self._tep:
            return
        try:
            da = ghi_prompts(self._app.base_dir, self._ma(), {self._tep: self._noi_dung.toPlainText()})
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        if not da:
            self._app.show_message("Chưa lưu", "Prompt đang trống hoặc không thuộc bộ prompt của kênh.")
            return
        for i, (ten, nhan_prompt, _chu) in enumerate(self._prompts):
            if ten == self._tep:
                self._prompts[i] = (ten, nhan_prompt, self._noi_dung.toPlainText())
                break
        self._nut_luu.setEnabled(False)
        self._ghi_chu.setText("Đã lưu. Video tiếp theo của kênh sẽ dùng prompt này.")

    def _mo_quy_trinh(self) -> None:
        from PyQt5.QtWidgets import QDialog
        from .trang_auto import TrangTuDong

        hop = QDialog(self)
        hop.setWindowTitle("Quy trình sản xuất video")
        hop.resize(1220, 840)
        v = QVBoxLayout(hop)
        trang = TrangTuDong(self._app)
        v.addWidget(trang, 1)
        v.addWidget(nut_phu("Đóng", hop.accept, rong=90), 0, Qt.AlignRight)
        hop.exec_()
        trang.close()
        hop.deleteLater()
