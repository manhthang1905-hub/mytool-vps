"""Ba trang chi tiết của PHÒNG ĐIỀU HÀNH (Đợt G, 01/10/2026) — mở từ nút trên thẻ kênh.

* `HopBaoCaoTuan`  — báo cáo tuần của giám đốc kênh + báo cáo công ty (tổng giám đốc), hai thẻ.
* `HopBaiHoc`      — sổ bài học theo CHUYÊN GIA (Nền tảng / Khán giả / Chủ đề) và PHẠM VI (kênh / nhóm /
                     ngoài), có số + video bằng chứng; nút "Sai" gạch bài (`bdk.gach_bai_hoc`).
* `HopQuyetDinh`   — quyết gì, vì sao, kết quả, tỉ lệ đúng theo loại (`bdk.so_quyet_dinh`).

Chỉ VẼ: mọi dữ liệu từ `core.bang_dieu_khien` (thuần, test không cần Qt). Đọc chậm (sổ bài học vài giây)
chạy qua `app.run_bg`.

`nhung=True` (03/10/2026): dựng ngay làm một widget con để NHÚNG vào tab của phòng điều hành
(`ui_qt.trang_bang_dieu_khien`) — bỏ nút "Đóng", không phải cửa sổ riêng.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core import bang_dieu_khien as bdk

from . import theme
from .widgets import nhan, nut_phu

__all__ = ["HopBaoCaoTuan", "HopBaiHoc", "HopQuyetDinh"]


def _html(s: Any) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _o_markdown(chu: str, rong: str) -> QTextEdit:
    o = QTextEdit()
    o.setReadOnly(True)
    if chu:
        if hasattr(o, "setMarkdown"):
            o.setMarkdown(chu)
        else:
            o.setPlainText(chu)
    else:
        o.setPlainText(rong)
    return o


def _nut_dong(hop: QDialog, v: QVBoxLayout, nhung: bool) -> None:
    """Hộp riêng: thêm nút "Đóng". Nhúng vào tab: thành widget con, không nút."""
    if nhung:
        hop.setWindowFlags(Qt.Widget)
        v.setContentsMargins(0, 0, 0, 0)
    else:
        v.addWidget(nut_phu("Đóng", hop.accept, rong=90))


class HopBaoCaoTuan(QDialog):
    """Báo cáo tuần: thẻ "Kênh" (`giam-doc/BAO-CAO-TUAN.md`) + thẻ "Công ty" (`BAO-CAO-CONG-TY.md`)."""

    def __init__(self, app: Any, ma: str, cha: Optional[QWidget] = None, *, nhung: bool = False):
        super().__init__(cha)
        self.setWindowTitle("Báo cáo tuần — {0}".format(ma or "công ty"))
        self.resize(780, 640)
        du = bdk.bao_cao_tuan(app.base_dir, ma)
        v = QVBoxLayout(self)
        self.the = QTabWidget()
        if ma:
            self.the.addTab(_o_markdown(du.get("kenh") or "", "Giám đốc kênh {0} chưa ghi báo cáo tuần nào.".format(ma)),
                            "Kênh {0}".format(ma))
        self.the.addTab(_o_markdown(du.get("cong_ty") or "", "Tổng giám đốc chưa họp tuần nào (họp sáng thứ Hai)."),
                        "Công ty")
        v.addWidget(self.the, 1)
        _nut_dong(self, v, nhung)


class HopBaiHoc(QDialog):
    """Sổ bài học của kênh, gom theo chuyên gia → phạm vi. Bài bị gạch hiện mờ, gạch ngang."""

    def __init__(self, app: Any, ma: str, cha: Optional[QWidget] = None, *, tu_nap: bool = True,
                 nhung: bool = False):
        super().__init__(cha)
        self._app = app
        self._ma = ma
        self._dong: List[Dict[str, Any]] = []
        self.setWindowTitle("Bài học — {0}".format(ma))
        self.resize(820, 680)
        v = QVBoxLayout(self)
        v.addWidget(nhan("Máy rút bài học từ số Studio của chính kênh (và nhóm/bên ngoài khi kênh chưa có số). "
                         "Bài có n ≥ 3 mới được đưa vào lời nhắc. Thấy bài nào SAI thì bấm “Sai” — bài bị gạch, "
                         "ghi vào sổ và bỏ khỏi lời nhắc.", "muted"))
        self._nhan_trang = nhan("Đang đọc sổ bài học…", "muted")
        v.addWidget(self._nhan_trang)
        self._cuon = QScrollArea()
        self._cuon.setWidgetResizable(True)
        self._cuon.setFrameShape(QFrame.NoFrame)
        if nhung:
            self._cuon.setMinimumHeight(420)   # nằm trong trang đã cuộn — không để ô cuộn con bẹp lại
        v.addWidget(self._cuon, 1)
        _nut_dong(self, v, nhung)
        if tu_nap:
            self.nap_lai()

    def nap_lai(self) -> None:
        goc, ma = self._app.base_dir, self._ma
        self._nhan_trang.setText("Đang đọc sổ bài học…")
        self._app.run_bg(lambda: bdk.so_bai_hoc(goc, ma), on_ok=self.ve,
                         on_err=lambda e: self._nhan_trang.setText("Không đọc được sổ bài học: {0}".format(str(e)[:160])))

    def ve(self, dong: List[Dict[str, Any]]) -> None:
        self._dong = list(dong or [])
        than = QWidget()
        v = QVBoxLayout(than)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(6)
        so_gach = sum(1 for d in self._dong if d.get("da_gach"))
        self._nhan_trang.setText("{0} bài học · {1} đã gạch.".format(len(self._dong) - so_gach, so_gach)
                                 if self._dong else "Kênh này chưa có bài học nào.")
        for khoa_cg, ten_cg in bdk.CHUYEN_GIA:
            cua_cg = [d for d in self._dong if d.get("chuyen_gia") == khoa_cg]
            v.addWidget(nhan("{0} ({1})".format(ten_cg, len(cua_cg)), "h2"))
            if not cua_cg:
                v.addWidget(nhan("— chưa có bài nào", "muted"))
                continue
            pham_vi_truoc = None
            for d in cua_cg:
                if d.get("pham_vi") != pham_vi_truoc:
                    pham_vi_truoc = d.get("pham_vi")
                    nh = QLabel(str(d.get("ten_pham_vi") or ""))
                    nh.setStyleSheet("color:{0};font-size:11px;font-weight:700;".format(theme.CHU_MO))
                    v.addWidget(nh)
                v.addWidget(self._hang(d))
        v.addStretch(1)
        self._cuon.setWidget(than)

    def _hang(self, d: Dict[str, Any]) -> QWidget:
        hop = QFrame()
        hop.setObjectName("hangBai")
        hop.setStyleSheet("QFrame#hangBai{{background:{0};border:1px solid {1};border-radius:8px;}}".format(
            theme.XAM_NEN if d.get("da_gach") else theme.THE, theme.VIEN))
        ngang = QHBoxLayout(hop)
        ngang.setContentsMargins(10, 6, 10, 6)
        cot = QVBoxLayout()
        cau = QLabel()
        cau.setWordWrap(True)
        cau.setTextFormat(Qt.RichText)
        mau = theme.XAM if d.get("da_gach") else theme.CHU
        cau.setText('<span style="color:{0};{1}">{2}</span>'.format(
            mau, "text-decoration:line-through;" if d.get("da_gach") else "", _html(d.get("cau"))))
        cot.addWidget(cau)
        phan = ["n = {0}".format(d.get("n", 0))]
        if d.get("tin_cay"):
            phan.append("tin cậy {0}".format({"cao": "cao", "vua": "vừa", "thap": "thấp"}.get(d["tin_cay"], d["tin_cay"])))
        if not d.get("bom") and not d.get("da_gach"):
            phan.append("chưa vào lời nhắc" + (" (bóng — giám đốc chưa tự áp)" if d.get("bong") else ""))
        if d.get("da_gach"):
            phan.append("ĐÃ GẠCH")
        video = list(d.get("video") or [])
        if video:
            phan.append("video: " + ", ".join('<a href="https://www.youtube.com/watch?v={0}">{0}</a>'.format(_html(x))
                                              for x in video[:6]))
        meta = QLabel(" · ".join(phan))
        meta.setTextFormat(Qt.RichText)
        meta.setOpenExternalLinks(True)
        meta.setWordWrap(True)
        meta.setStyleSheet("color:{0};font-size:11px;".format(theme.CHU_MO))
        cot.addWidget(meta)
        ngang.addLayout(cot, 1)
        if not d.get("da_gach"):
            nut = nut_phu("Sai", lambda _c=False, bai=d: self._gach(bai), rong=60)
            nut.setToolTip("Bài này sai — gạch, ghi vào sổ, bỏ khỏi lời nhắc.")
            ngang.addWidget(nut, 0, Qt.AlignTop)
        return hop

    def _gach(self, bai: Dict[str, Any]) -> None:
        hoi = QMessageBox.question(
            self, "Gạch bài học",
            "Bài học này SAI?\n\n“{0}”\n\nBài sẽ bị gạch, ghi vào sổ và không còn đưa vào lời nhắc.".format(
                str(bai.get("cau") or "")[:300]))
        if hoi != QMessageBox.Yes:
            return
        try:
            bdk.gach_bai_hoc(self._app.base_dir, self._ma, bai)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self.nap_lai()


class HopQuyetDinh(QDialog):
    """Quyết định & độ chính xác của giám đốc kênh: bảng quyết định + tỉ lệ đúng theo loại."""

    COT = ("Lúc", "Loại", "Quyết gì", "Vì sao", "Kết quả")

    def __init__(self, app: Any, ma: str, cha: Optional[QWidget] = None, *, tu_nap: bool = True,
                 nhung: bool = False):
        super().__init__(cha)
        self._app = app
        self._ma = ma
        self.setWindowTitle("Quyết định & độ chính xác — {0}".format(ma))
        self.resize(980, 640)
        v = QVBoxLayout(self)
        self._nhan_ti_le = nhan("Đang đọc sổ quyết định…")
        v.addWidget(self._nhan_ti_le)
        self.bang = QTableWidget(0, len(self.COT))
        self.bang.setHorizontalHeaderLabels(list(self.COT))
        self.bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bang.setWordWrap(True)
        self.bang.verticalHeader().setVisible(False)
        tieu = self.bang.horizontalHeader()
        for i, che in enumerate((QHeaderView.ResizeToContents, QHeaderView.ResizeToContents, QHeaderView.Stretch,
                                 QHeaderView.Stretch, QHeaderView.Interactive)):
            tieu.setSectionResizeMode(i, che)
        tieu.resizeSection(4, 150)
        if nhung:
            # Vùng giữa hẹp hơn hộp riêng (~980px): nhường chỗ cho hai cột chữ "Quyết gì" / "Vì sao".
            tieu.setSectionResizeMode(1, QHeaderView.Interactive)
            tieu.resizeSection(1, 130)
            tieu.resizeSection(4, 120)
            self.bang.setMinimumHeight(360)
        v.addWidget(self.bang, 1)
        _nut_dong(self, v, nhung)
        if tu_nap:
            goc = app.base_dir
            app.run_bg(lambda: bdk.so_quyet_dinh(goc, ma), on_ok=self.ve,
                       on_err=lambda e: self._nhan_ti_le.setText("Không đọc được: {0}".format(str(e)[:160])))

    def ve(self, du: Dict[str, Any]) -> None:
        ti_le = list((du or {}).get("ti_le") or [])
        dong = list((du or {}).get("dong") or [])
        phan = []
        ten_quyen = {"tu_ap": "được tự áp", "goi_y": "chỉ gợi ý"}
        for t in ti_le:
            quyen = " · {0}".format(ten_quyen[t["quyen"]]) if t.get("quyen") in ten_quyen else ""
            if t.get("tong"):
                phan.append("<b>{0}</b>: đúng {1}/{2} ({3:.0%}){4}".format(
                    _html(t["ten_loai"]), t["dung"], t["tong"], t["dung"] / t["tong"], quyen))
            elif t.get("so_quyet"):
                phan.append("<b>{0}</b>: {1} quyết định, đang chờ kết quả".format(_html(t["ten_loai"]), t["so_quyet"]))
            else:
                phan.append("<b>{0}</b>: chưa có".format(_html(t["ten_loai"])))
        if phan:
            phan.append("tự áp khi ≥ 70% đúng trên ≥ 10 quyết định")
        self._nhan_ti_le.setTextFormat(Qt.RichText)
        self._nhan_ti_le.setText("Tỉ lệ đúng — " + " · ".join(phan) if phan else
                                 "Giám đốc kênh chưa có quyết định nào (bật “Gợi ý” để giám đốc bắt đầu đoán và tự chấm).")
        self.bang.setRowCount(len(dong))
        for r, d in enumerate(dong):
            o = (d.get("luc"), d.get("ten_loai"), d.get("quyet"), d.get("vi_sao"), d.get("ket_qua"))
            for c, gt in enumerate(o):
                it = QTableWidgetItem(str(gt or ""))
                it.setToolTip(str(gt or ""))
                if c == 4 and d.get("dung") is not None:
                    it.setForeground(QBrush(QColor(theme.XANH if d["dung"] else theme.DO)))
                self.bang.setItem(r, c, it)
        self.bang.resizeRowsToContents()
        QTimer.singleShot(0, self.bang.resizeRowsToContents)  # sau khi cột đã giãn theo cửa sổ
