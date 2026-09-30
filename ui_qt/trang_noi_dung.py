"""Trang Nội dung của chế độ VPS.

Mặt trước chỉ nói theo bốn việc người vận hành cần làm. Các màn hình cũ vẫn
được giữ nguyên, nhưng chỉ được tạo khi người dùng mở mục tương ứng. Cách này
tránh nạp đồng thời các bảng nghiên cứu, sản xuất và cài đặt kênh vốn rất nặng.
"""

from __future__ import annotations

import importlib
from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from .widgets import nhan, tieu_de_trang

__all__ = ["TrangNoiDung", "TAB_CON"]

# Tên ngắn, theo đúng việc cần làm. Mục dùng hằng ngày đứng trước; công cụ can
# thiệp dây chuyền đứng cuối vì chỉ mở khi cần xử lý thủ công.
TAB_CON = ("Video", "Kênh", "Nguồn", "Chạy tay")

_MO_TA = (
    "Duyệt, đăng và theo dõi từng video.",
    "Tên kênh, giọng đọc, hình ảnh và chế độ tự động.",
    "Theo dõi đối thủ, chọn ý tưởng và công thức nội dung.",
    "Can thiệp vào dây chuyền sản xuất khi cần.",
)

# (module, lớp, thuộc tính tương thích với mã cũ)
_TRANG = (
    ("ui_qt.trang_trung_tam", "TrangTrungTam", "duyet"),
    ("ui_qt.trang_quan_ly_kenh", "TrangQuanLyKenh", "quan_ly"),
    ("ui_qt.trang_phan_tich", "TrangPhanTich", "doi_thu"),
    ("ui_qt.trang_auto", "TrangTuDong", "san_xuat"),
)

_TEN_CU = {
    "Duyệt & đăng": "Video",
    "Duyệt && đăng": "Video",
    "Quản lý kênh": "Kênh",
    "Cài đặt kênh": "Kênh",
    "Đối thủ": "Nguồn",
    "Sản xuất": "Chạy tay",
}


class TrangNoiDung(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._da_nap: Dict[int, QWidget] = {}
        self._dang_doi = False

        # Bốn thuộc tính này từng được tạo ngay lập tức. Giữ tên để mã gọi cũ
        # vẫn dùng được, nhưng màn chưa mở có giá trị None.
        self.duyet: Optional[QWidget] = None
        self.quan_ly: Optional[QWidget] = None
        self.doi_thu: Optional[QWidget] = None
        self.san_xuat: Optional[QWidget] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(16, 12, 16, 12)
        doc.setSpacing(7)
        doc.addWidget(tieu_de_trang(
            "Nội dung",
            "Video, kênh, nguồn và công cụ xử lý khi cần.",
            "noi-dung"))

        self._nhan_mo_ta = nhan(_MO_TA[0], "muted")
        self._nhan_mo_ta.setMinimumWidth(1)
        doc.addWidget(self._nhan_mo_ta)

        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(1)
        for i, ten in enumerate(TAB_CON):
            cho = QLabel("Đang mở…")
            cho.setAlignment(Qt.AlignCenter)
            self.tabs.addTab(cho, ten)
            self.tabs.setTabToolTip(i, _MO_TA[i])
        self.tabs.currentChanged.connect(self._mo_muc)
        doc.addWidget(self.tabs, 1)

        # Trang Nội dung đang ẨN lúc tool mở ở Điều khiển. Không dựng cả một
        # Trung tâm thứ hai trong nền: bảng ảnh bìa và báo cáo lớn từng làm
        # private RAM tăng thêm hàng trăm MB dù người dùng chưa mở trang này.
        # `showEvent` dưới đây sẽ dựng đúng mục đang chọn ở lần mở đầu tiên.

    def showEvent(self, su_kien) -> None:  # noqa: N802 — tên Qt
        super().showEvent(su_kien)
        self._mo_muc(self.tabs.currentIndex())

    def _mo_muc(self, chi_so: int) -> None:
        if chi_so < 0 or chi_so >= len(_TRANG):
            return
        self._nhan_mo_ta.setText(_MO_TA[chi_so])
        if chi_so in self._da_nap or self._dang_doi:
            return

        self._dang_doi = True
        try:
            ten_module, ten_lop, ten_thuoc_tinh = _TRANG[chi_so]
            lop = getattr(importlib.import_module(ten_module), ten_lop)
            trang = lop(self._app)
            setattr(self, ten_thuoc_tinh, trang)
            self._da_nap[chi_so] = trang

            vo = self._cuon(trang)
            cho = self.tabs.widget(chi_so)
            self.tabs.removeTab(chi_so)
            self.tabs.insertTab(chi_so, vo, TAB_CON[chi_so])
            self.tabs.setTabToolTip(chi_so, _MO_TA[chi_so])
            self.tabs.setCurrentIndex(chi_so)
            if cho is not None:
                cho.deleteLater()
        finally:
            self._dang_doi = False

    @staticmethod
    def _cuon(trang: QWidget) -> QWidget:
        """Mỗi màn cũ có vùng cuộn dọc riêng để không mất phần cuối."""
        cuon = QScrollArea()
        cuon.setWidget(trang)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cuon.setMinimumWidth(1)
        return cuon

    def mo_tab(self, ten: str) -> None:
        """Mở mục theo tên mới hoặc tên của giao diện cũ."""
        can = _TEN_CU.get(str(ten or "").replace("&&", "&"), str(ten or ""))
        for i, nhan_tab in enumerate(TAB_CON):
            if nhan_tab == can:
                self.tabs.setCurrentIndex(i)
                self._mo_muc(i)
                return

    def doi_du_an(self, ten: str) -> None:
        # Màn chưa mở sẽ đọc dự án hiện tại từ app khi nó được tạo.
        for con in tuple(self._da_nap.values()):
            tiep = getattr(con, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001 — một mục hỏng không kéo mục khác
                    pass
