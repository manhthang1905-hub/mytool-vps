"""QTableView ảo hóa cho bàn dữ liệu VPS."""

from __future__ import annotations

import csv
from typing import Any, Callable, Dict, List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QTableView

from core import bang_du_lieu_vps as dl


class BangModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cot: List[Dict[str, Any]] = []
        self.hang: List[Dict[str, Any]] = []
        self._on_sua: Optional[Callable[[Dict[str, Any], str, str], bool]] = None

    def dat(self, cot, hang, on_sua=None) -> None:
        self.beginResetModel()
        self.cot, self.hang = list(cot or []), list(hang or [])
        self._on_sua = on_sua
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.hang)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.cot)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.hang) or index.column() >= len(self.cot):
            return None
        meta = self.cot[index.column()]
        raw = self.hang[index.row()].get(meta["khoa"], "")
        if role == Qt.DisplayRole:
            if raw in (None, ""):
                return ""
            if meta.get("kieu") == "so":
                n = dl.gia_tri_so(raw)
                return "{:,.0f}".format(n).replace(",", ".")
            return str(raw)
        if role == Qt.UserRole:
            return dl.gia_tri_so(raw) if meta.get("kieu") == "so" else str(raw or "").casefold()
        if role == Qt.TextAlignmentRole and meta.get("kieu") == "so":
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ToolTipRole:
            return str(raw or "")
        return None

    def flags(self, index):
        co = super().flags(index)
        if index.isValid() and self.la_cot_sua(index.column()):
            co |= Qt.ItemIsEditable
        return co

    def la_cot_sua(self, cot: int) -> bool:
        return 0 <= cot < len(self.cot) and bool(self.cot[cot].get("sua"))

    def setData(self, index, value, role=Qt.EditRole):  # noqa: N802
        if role != Qt.EditRole or not index.isValid() or not self.la_cot_sua(index.column()):
            return False
        meta = self.cot[index.column()]
        dong = self.hang[index.row()]
        khoa, moi = meta["khoa"], str(value or "").strip()
        if moi == str(dong.get(khoa) or "").strip():
            return True
        if self._on_sua is None or not self._on_sua(dong, khoa, moi):
            return False
        dong[khoa] = moi
        dong["_tim"] = " ".join(str(v) for k, v in dong.items() if not k.startswith("_")).casefold()
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.UserRole, Qt.ToolTipRole])
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section < len(self.cot):
            meta = self.cot[section]
            return meta["nhan"] + ("  ✎" if meta.get("sua") else "")
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        return None

    def dong(self, hang: int) -> Dict[str, Any]:
        return self.hang[hang] if 0 <= hang < len(self.hang) else {}


class BangProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loai = dl.V7
        self.ma_loc = ""
        self.tim = ""
        self.khoa_tim = ""
        self.setSortRole(Qt.UserRole)
        self.setDynamicSortFilter(True)

    def dat_loc(self, loai: str, ma_loc: str, tim: str, khoa_tim: str = "") -> None:
        self.loai, self.ma_loc, self.tim = loai, ma_loc, str(tim or "").strip().casefold()
        self.khoa_tim = str(khoa_tim or "")
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):  # noqa: N802
        model = self.sourceModel()
        dong = model.dong(source_row)
        noi_tim = dong.get(self.khoa_tim, "") if self.khoa_tim else dong.get("_tim", "")
        return dl.hop_loc_nhanh(self.loai, self.ma_loc, dong) and (
            not self.tim or self.tim in str(noi_tim or "").casefold())


class BangView(QTableView):
    """Ctrl+C sao chép vùng chọn theo định dạng dán được vào Excel."""
    yeu_cau_menu = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.yeu_cau_menu.emit)

    def keyPressEvent(self, event):  # noqa: N802
        if event.matches(QKeySequence.Copy):
            self.chep_vung_chon()
            return
        super().keyPressEvent(event)

    def chep_vung_chon(self) -> str:
        chi_so = sorted(self.selectedIndexes(), key=lambda x: (x.row(), x.column()))
        if not chi_so:
            return ""
        hang = {}
        for i in chi_so:
            hang.setdefault(i.row(), {})[i.column()] = str(i.data(Qt.DisplayRole) or "")
        dau, cuoi = min(i.column() for i in chi_so), max(i.column() for i in chi_so)
        chu = "\n".join("\t".join(c.get(x, "") for x in range(dau, cuoi + 1))
                          for _, c in sorted(hang.items()))
        QApplication.clipboard().setText(chu)
        return chu


def xuat_proxy(proxy: BangProxy, duong: str) -> int:
    """Xuất đúng phần đang lọc/sắp xếp, UTF-8 BOM để Excel đọc đúng tiếng Việt."""
    model = proxy.sourceModel()
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.writer(tep)
        but.writerow([c["nhan"] for c in model.cot])
        for r in range(proxy.rowCount()):
            but.writerow([proxy.index(r, c).data(Qt.DisplayRole) or ""
                          for c in range(proxy.columnCount())])
    return proxy.rowCount()
