"""Trang **Bảng điều khiển** = PHÒNG ĐIỀU HÀNH CÔNG TY (Đợt G, 01/10/2026 —
`workspace/VIEC-CON-LAI-30-09.md`; bản đầu: Việc 2, `workspace/THIET-KE-BANG-DIEU-KHIEN.md`).

"Vào VPS thì qua đó nắm tình hình và quản lý được" — đọc 10 giây hiểu, bấm vào
mới chi tiết, màu chỉ để báo. Trên xuống dưới:

* `KhoiCongTy` — CÔNG TY: view/sub/giờ xem 7 ngày (so tuần trước) · video hôm nay
  x/trần · máy · ví ~N ngày · phiên bản + tự cập nhật · tổng giám đốc. Nút
  "Chi tiết máy ▸" mở `DongMay` (ví, đĩa, máy bật, máy nền, quét Studio, lịch,
  chi phí thật) — giữ nguyên mọi ô cũ.
* `KhoiViec` — "⚠ VIỆC CỦA BẠN (n)": chỉ việc máy không tự làm được, xếp hỏng
  (✕) trước — từ `core.bang_dieu_khien.viec_cua_ban` + dòng "Windows sắp hết
  hạn" (`core.tong_quan_vps.canh_bao_windows`).
* Lưới `TheKenhLon` — kênh ĐỎ lên đầu (`bdk.muc_phong`): xếp loại, YPP, 3 cổng,
  3 video + phán quyết, đội AI nói, đang thử, lịch đăng tiếp, công tắc giám đốc
  / tạm dừng / tự lên lịch, 3 nút trang chi tiết (`ui_qt.trang_phong_chi_tiet`)
  + menu "⋯" (xem video, nhật ký, thư mục, cài kênh). Rồi dòng "Kênh khác đang
  tắt: … ▸".

Số nặng của thẻ (`bdk.tinh_so_kenh`) KHÔNG tính trong tiến trình giao diện:
`phong_dieu_hanh` báo `can_tinh`, trang gọi `bdk.sinh_tinh_so` (tiến trình con
ưu tiên thấp) tối đa mỗi `GIAY_TINH_LAI` một lần, lần làm mới sau tự đọc bộ đệm.

KHÔNG viết lại lô-gic của `core.bang_dieu_khien` (Việc 1) — trang này chỉ gọi
và vẽ. Việc tay không có dấu trên đĩa (ghim, nháp thừa) đã có nút "Đã ghim"/
"Đã xoá" gọi `bang_dieu_khien.danh_dau_xong`.

═══ VÌ SAO `anh_chup(..., tat_ca=False)`, KHÔNG PHẢI `True` NHƯ DOCSTRING CỦA
`anh_bang` GỢI Ý ═══

`anh_bang(anh=None)` mặc định tự chụp với `tat_ca=True` — tiện cho bài kiểm
của Việc 1, nhưng `tat_ca=True` dồn MỌI kênh (kể cả kênh tắt hẳn, không do máy
đăng quản) vào danh sách `kenh`, và `kenh_khac` luôn rỗng. Quyết định 5 của
bản thiết kế ("TL4-T7 có thẻ riêng dù đang tắt; TL4-T7-v2 gom vào 'Kênh
khác ▸'") chỉ đúng khi gọi `anh_chup(tat_ca=False)` — lúc đó `core.trung_tam`
tự phân loại: kênh có `tu_chay` HOẶC do máy đăng quản (`trong_vm`) thì vào
`kenh` (có thẻ), còn lại vào `kenh_khac`. Trang này tự chụp rồi TRUYỀN VÀO
`anh_bang(anh=...)` — Việc 1 cho phép làm vậy để đỡ đọc đĩa hai lần.

═══ CÔNG TẮC "TỰ LÊN LỊCH" (`tu_duyet`) GHI THẲNG, KHÔNG QUA `bang_dieu_khien.
doi_cong_tac` ═══

`doi_cong_tac` của Việc 1 chỉ biết hai nhóm khoá: `tu_chay`/`tu_don` (ghi
`kenh.yaml`) và phần còn lại (ghi `may-ao.json`, dành cho `tu_dang`/
`tu_tra_loi_cmt`). `tu_duyet` KHÔNG nằm trong danh sách máy ảo — nó là một
khoá của `kenh.yaml` (`core.tu_chay` đọc nó để quyết định tự hẹn giờ hay chờ
người duyệt). Gọi thẳng `qua doi_cong_tac("tu_duyet", ...)` sẽ ghi NHẦM vào
`may-ao.json`. Trang này vì vậy tự định tuyến `tu_duyet` sang
`core.trung_tam.ghi_cai_kenh` — không sửa `core/bang_dieu_khien.py` (Việc 1).
"""

from __future__ import annotations

import datetime as _dt
import os
import time
from typing import Any, Callable, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu,
    QMessageBox, QProgressBar, QTextEdit, QVBoxLayout, QWidget,
)

from core import bang_dieu_khien as bdk
from core import trung_tam as tt
from core.money import format_vnd

from . import theme
from .trang_dieu_khien import HopCaiDatKenh, HopNhatKyKenh
from .trang_trung_tam import GIAY_HOI_LICH, GIAY_HOI_VI, HopDuyet, _cat, _giam_sat
from .widgets import HangXuongDong, HopXuongDong, gio_hhmm, mo_thu_muc, nhan, nut_phu

__all__ = ["TrangBangDieuKhien", "KhoiViec", "DongMay", "TheKenhLon", "KhoiCongTy"]

#: CLAUDE.md luật 4 — đọc lại tệp mỗi 30 giây, không hỏi máy chủ dày hơn.
NHIP_LAM_MOI_MS = 30_000
#: Sinh tiến trình tính số kênh tối đa 10 phút/lần (kể cả khi lần trước hỏng).
GIAY_TINH_LAI = 10 * 60
#: Windows chỉ hỏi 6 giờ/lần (mục 3, "Làm mới" — `wevtutil` mất tới 8 giây).
GIAY_HOI_WINDOWS = 6 * 60 * 60

#: Bề rộng cửa sổ để lưới thẻ kênh chuyển từ 1 sang 2 cột.
BE_RONG_HAI_COT = 1000

#: Ba màu (chữ · nền · viền) theo mức thẻ kênh (`bdk.muc_the`) — quyết định 4
#: "màu từ theme XANH/VANG/DO + _NEN/_VIEN", không tự chế mã màu mới.
_MAU_THE = {
    bdk.TOT: (theme.XANH, theme.XANH_NEN, theme.XANH_VIEN),
    bdk.CHO_BAN: (theme.CAM, theme.VANG_NEN, theme.VANG_VIEN),
    bdk.LUU_Y: (theme.CAM, theme.VANG_NEN, theme.VANG_VIEN),
    bdk.HONG: (theme.DO, theme.DO_NEN, theme.DO_VIEN),
    bdk.TAT: (theme.XAM, theme.XAM_NEN, theme.VIEN),
}
_DAU_THE = {bdk.TOT: "✓", bdk.CHO_BAN: "⚠", bdk.LUU_Y: "⚠", bdk.HONG: "✕", bdk.TAT: "–"}

#: Ba mức của khối "Việc của bạn" (`bdk.HONG/CANH_BAO/THUONG`).
_MAU_VIEC = {
    bdk.HONG: (theme.DO, theme.DO_NEN, theme.DO_VIEN),
    bdk.CANH_BAO: (theme.CAM, theme.VANG_NEN, theme.VANG_VIEN),
    bdk.THUONG: (theme.CHU_MO, theme.THE, theme.VIEN),
}
_DAU_VIEC = {bdk.HONG: "✕", bdk.CANH_BAO: "⚠", bdk.THUONG: "•"}

#: Ba mức của dòng MÁY (`bdk.dong_may` trả `TOT/LUU_Y/HONG` cho ví và ổ đĩa —
#: khác vocabulary "thuong" của `ui_qt.trang_trung_tam`, nên có bảng riêng).
_MAU_MAY = {
    bdk.TOT: (theme.CHU, theme.THE, theme.VIEN),
    bdk.LUU_Y: (theme.CAM, theme.VANG_NEN, theme.VANG_VIEN),
    bdk.HONG: (theme.DO, theme.DO_NEN, theme.DO_VIEN),
}

_MUI_TEN = {"len": "▲", "xuong": "▼", "ngang": "●"}
_MAU_MUI_TEN = {"len": theme.XANH, "xuong": theme.DO, "ngang": theme.CHU_MO}

#: Khoá `workspace/viec-da-xong.json` cho việc "chép link rồi tự đóng" (ghim,
#: nháp thừa) — người dùng thấy chữ đổi ngay, không phải chờ vòng làm mới sau.


def _khoa_windows() -> str:
    return "windows-canh-bao"


class _OChiSoMay(QFrame):
    """Một ô của dòng MÁY: tên nhỏ ở trên, giá trị ở dưới, bấm được.

    Bản thu gọn của `ui_qt.trang_trung_tam._OChiSo` — không import lại lớp đó
    vì nó gắn với vocabulary màu "thuong/luu_y/hong" của trang Trung tâm, còn
    ở đây dùng `_MAU_MAY` (tot/luu_y/hong, đúng giá trị `bdk.dong_may` trả).
    """

    def __init__(self, tieu_de: str, on_bam: Optional[Callable[[], None]] = None,
                cha: Optional[QWidget] = None):
        super().__init__(cha)
        self.setObjectName("oMay")
        if on_bam is not None:
            self.setCursor(Qt.PointingHandCursor)
        self._on_bam = on_bam
        doc = QVBoxLayout(self)
        doc.setContentsMargins(10, 5, 10, 5)
        doc.setSpacing(0)
        self._nhan_tieu = QLabel(tieu_de)
        self._nhan_tieu.setWordWrap(False)
        self._nhan_tieu.setStyleSheet("color:{0};font-size:11px;".format(theme.CHU_MO))
        self._nhan_gia = QLabel("…")
        self._nhan_gia.setWordWrap(False)
        doc.addWidget(self._nhan_tieu)
        doc.addWidget(self._nhan_gia)
        self.dat("…")

    def dat(self, gia_tri: str, muc: str = bdk.TOT, tip: str = "") -> None:
        chu, nen, vien = _MAU_MAY.get(muc, _MAU_MAY[bdk.TOT])
        self._nhan_gia.setText(str(gia_tri))
        self._nhan_gia.setStyleSheet(
            "color:{0};font-size:13px;font-weight:600;".format(chu))
        self.setStyleSheet(
            "QFrame#oMay{{background:{0};border:1px solid {1};border-radius:9px;}}"
            .format(nen, vien))
        self.setToolTip(tip or "")

    def text(self) -> str:
        return "{0}\n{1}".format(self._nhan_tieu.text(), self._nhan_gia.text())

    def mousePressEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        if self._on_bam is not None:
            self._on_bam()
        super().mousePressEvent(su_kien)


# ═══════════════════════════════════════════════════════════════════════════
# Khối "VIỆC CỦA BẠN"
# ═══════════════════════════════════════════════════════════════════════════


class KhoiViec(QFrame):
    """Danh sách việc tay, mức nặng đứng trước. Rỗng thì một câu ✓ thay lời."""

    def __init__(self, on_hanh_dong: Callable[[str, Dict[str, Any]], None],
                cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._on_hanh_dong = on_hanh_dong
        self.setObjectName("card")
        theme.bong(self)
        doc = QVBoxLayout(self)
        doc.setContentsMargins(14, 10, 14, 10)
        doc.setSpacing(6)
        self._nhan_tieu = nhan("VIỆC CỦA BẠN", "h2")
        doc.addWidget(self._nhan_tieu)
        self._nhan_rong = nhan("✓ Không có việc gì — máy đang tự chạy.")
        self._nhan_rong.setStyleSheet("color:{0};font-weight:600;".format(theme.XANH))
        self._nhan_rong.setVisible(False)
        doc.addWidget(self._nhan_rong)
        self._hop_dong = QWidget()
        self._v_dong = QVBoxLayout(self._hop_dong)
        self._v_dong.setContentsMargins(0, 0, 0, 0)
        self._v_dong.setSpacing(8)
        doc.addWidget(self._hop_dong)

    def nap(self, danh_sach: List[Dict[str, Any]]) -> None:
        while self._v_dong.count():
            muc = self._v_dong.takeAt(0)
            w = muc.widget()
            if w is not None:
                w.deleteLater()
        self._nhan_tieu.setText("⚠ VIỆC CỦA BẠN ({0})".format(len(danh_sach))
                                if danh_sach else "VIỆC CỦA BẠN")
        self._nhan_tieu.setToolTip("Chỉ những việc máy KHÔNG tự làm được — còn lại máy tự lo.")
        self._nhan_rong.setVisible(not danh_sach)
        self._hop_dong.setVisible(bool(danh_sach))
        for viec in danh_sach:
            self._v_dong.addWidget(self._dong(viec))

    #: Bề rộng tối đa (px) của câu — chip đầu của `HopXuongDong`, phải đứng
    #: một dòng (không word-wrap: `HangXuongDong` đặt widget đúng bằng
    #: `sizeHint()` tự nhiên, chữ dài không cắt sẽ tràn khỏi thẻ). Cắt bằng
    #: pixel (`_cat`) như mọi nhãn một-dòng khác trong trang này.
    RONG_CAU = 620

    def _dong(self, viec: Dict[str, Any]) -> QWidget:
        muc = str(viec.get("muc") or bdk.THUONG)
        chu_mau, _nen, _vien = _MAU_VIEC.get(muc, _MAU_VIEC[bdk.THUONG])
        dau = _DAU_VIEC.get(muc, "•")
        kenh = str(viec.get("kenh") or "")
        chu = "{0} {1}{2}".format(
            dau, (kenh + "  ") if kenh else "", viec.get("chu") or "")
        goi_y = str(viec.get("goi_y") or "")

        # Nhãn câu + các nút cùng MỘT hàng chip: đủ rộng thì nằm chung dòng,
        # hẹp thì mục thừa tự rớt xuống dòng dưới (hành vi có sẵn của
        # `HangXuongDong`, không code thêm — xem docstring lớp đó).
        hop = HopXuongDong(8)
        nh = nhan(chu)
        nh.setWordWrap(False)
        _cat(nh, chu, self.RONG_CAU)
        nh.setMinimumWidth(1)
        nh.setStyleSheet("color:{0};font-size:13px;font-weight:600;".format(chu_mau))
        nh.setToolTip("{0}\n{1}".format(chu, goi_y) if goi_y else chu)
        hop.hang.addWidget(nh)
        for nhan_nut, ma_hanh_dong, tham_so in list(viec.get("nut") or []):
            nut = nut_phu(nhan_nut, None, rong=0)
            nut.clicked.connect(
                lambda _c=False, m=ma_hanh_dong, t=dict(tham_so or {}):
                self._on_hanh_dong(m, t))
            hop.hang.addWidget(nut)
        return hop


# ═══════════════════════════════════════════════════════════════════════════
# Dòng "MÁY"
# ═══════════════════════════════════════════════════════════════════════════


class DongMay(QFrame):
    """Ví · Ổ đĩa · Máy bật từ bao giờ · Máy chạy nền · Quét Studio · Lịch."""

    def __init__(self, on_hanh_dong: Callable[[str, Dict[str, Any]], None],
                cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._on_hanh_dong = on_hanh_dong
        self.setObjectName("card")
        theme.bong(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(2)
        v.addWidget(nhan("MÁY", "h2"))
        self._hop = HopXuongDong(8)
        v.addWidget(self._hop)
        hang = self._hop.hang

        self._o_vi = _OChiSoMay("Ví", lambda: self._on_hanh_dong("mo_vi", {}))
        hang.addWidget(self._o_vi)
        self._o_dia = _OChiSoMay("Ổ đĩa trống",
                                 lambda: self._on_hanh_dong("mo_thu_muc", {"duong": ""}))
        hang.addWidget(self._o_dia)
        self._o_bat = _OChiSoMay("Máy bật")
        hang.addWidget(self._o_bat)
        self._o_nen = _OChiSoMay("Máy chạy nền", lambda: self._on_hanh_dong("menu_may", {}))
        hang.addWidget(self._o_nen)
        self._o_quet = _OChiSoMay("Quét Studio")
        hang.addWidget(self._o_quet)
        self._o_lich = _OChiSoMay("Lịch", lambda: self._on_hanh_dong("bat_lich", {}))
        hang.addWidget(self._o_lich)
        # 29/09/2026 (kiểm toán #12): chi phí THẬT hôm qua — `core.chi_phi`,
        # đọc lại sổ đã lưu, không gọi mạng khi vẽ trang. Ẩn hẳn ô (không vẽ
        # "…") khi chưa có sổ ngày nào, xem `_ve_chi_phi`.
        self._o_chi_phi = _OChiSoMay("Chi phí thật hôm qua")
        self._o_chi_phi.setVisible(False)
        hang.addWidget(self._o_chi_phi)
        # 01/10/2026: dòng "công ty" của tổng giám đốc — bấm = Báo cáo công ty. Chưa họp lần nào thì ẩn.
        self._o_cong_ty = _OChiSoMay("Công ty", lambda: self._on_hanh_dong("bao_cao_cong_ty", {}))
        self._o_cong_ty.setVisible(False)
        hang.addWidget(self._o_cong_ty)

    def nap(self, may: Dict[str, Any], duong_goc: str, may_bat_tu: str,
           quet_studio: str) -> None:
        vi = may.get("vi") or {}
        if vi.get("vnd") is None:
            self._o_vi.dat("chưa biết số dư", bdk.TOT,
                           "Chưa đăng nhập, hoặc chưa hỏi được số dư ví.")
        else:
            so_ngay = vi.get("so_ngay_con_chay")
            if so_ngay is not None:
                them = " · đủ ~{0:.0f} ngày".format(so_ngay)
            else:
                # Biết số dư nhưng CHƯA đủ dữ liệu sản xuất để ước ngày còn
                # chạy (`bdk.so_ngay_con_chay`, cần ≥1 ngày có sản xuất trong
                # 7 ngày gần nhất) — nói rõ để khách khỏi tưởng tool thiếu số.
                them = " · chưa ước được"
            self._o_vi.dat("{0}{1}".format(format_vnd(vi.get("micro")), them), vi.get("muc", bdk.TOT),
                           "Bấm để nạp thêm tiền.")

        o_dia = may.get("o_dia") or {}
        con_gb = o_dia.get("con_gb")
        self._o_dia.dat(
            "{0:.0f} GB".format(con_gb) if con_gb is not None else "chưa đọc được",
            o_dia.get("muc", bdk.TOT), "Bấm để mở thư mục tool: " + duong_goc)
        self._duong_goc = duong_goc

        self._o_bat.dat(may_bat_tu or "chưa rõ")

        may_nen = may.get("may_nen") or {}
        song = bool((may_nen.get("agent") or {}).get("song"))
        self._o_nen.dat("đang chạy" if song else "ĐÃ TẮT", bdk.TOT if song else bdk.HONG,
                        "Bấm để bật lại hoặc xem nhật ký.")

        self._o_quet.dat(quet_studio or "chưa quét lần nào")

        lich = may.get("lich") or {}
        if lich.get("bat"):
            gio = str(lich.get("gio") or "")
            tip = "Chạy lúc {0} mỗi ngày.".format(gio) if gio else "Đang bật."
            self._o_lich.dat("Lịch tự chạy: đang bật", bdk.TOT, tip)
        else:
            co_kenh_tu_chay = bool(may.get("_co_kenh_tu_chay"))
            self._o_lich.dat("ĐANG TẮT", bdk.LUU_Y if co_kenh_tu_chay else bdk.TOT,
                             "Bấm để bật lịch.")

        self._ve_chi_phi(may.get("chi_phi_that") or {})
        ct = may.get("cong_ty") or {}
        self._o_cong_ty.setVisible(bool(ct.get("cau")))
        if ct.get("cau"):
            self._o_cong_ty.dat(str(ct["cau"]).split(": ", 1)[-1], bdk.TOT, str(ct["cau"]) + "\nBấm để mở Báo cáo công ty.")

    def _ve_chi_phi(self, cp: Dict[str, Any]) -> None:
        if not cp or not cp.get("tong_micro"):
            self._o_chi_phi.setVisible(False)
            return
        self._o_chi_phi.setVisible(True)
        moi_video = format_vnd(cp.get("moi_video_micro") or 0)
        gia_tri = "{0} · ~{1}/video".format(format_vnd(cp.get("tong_micro") or 0), moi_video)
        tip = "Ngày {0}, {1} video ({2}). Nguồn: GET /v1/usage, đối chiếu sổ tu-chay.".format(
            cp.get("ngay") or "?", cp.get("so_video") or "?", cp.get("nguon_so_video") or "?")
        self._o_chi_phi.dat(gia_tri, bdk.TOT, tip)


# ═══════════════════════════════════════════════════════════════════════════
# Thẻ kênh lớn
# ═══════════════════════════════════════════════════════════════════════════


#: Ba cổng + xếp loại + phán quyết — màu CHỈ để báo (xanh ổn · vàng sát ngưỡng · đỏ hỏng · xám chưa có số).
_MAU_CONG = {
    bdk.TOT: (theme.XANH, theme.XANH_NEN, theme.XANH_VIEN),
    bdk.LUU_Y: (theme.CAM, theme.VANG_NEN, theme.VANG_VIEN),
    bdk.HONG: (theme.DO, theme.DO_NEN, theme.DO_VIEN),
    bdk.CHUA: (theme.CHU_MO, theme.XAM_NEN, theme.VIEN),
}
_MAU_LOAI = {"len": theme.XANH, "chung": theme.CHU_MO, "tut": theme.DO}
_KET_VIDEO = {"thang": ("✓ thắng", theme.XANH), "truot": ("✕ trượt", theme.DO)}


def _so_vn(x: Any, le: int = 0) -> str:
    if x is None:
        return "?"
    try:
        s = "{0:,.{1}f}".format(float(x), le)
    except (TypeError, ValueError):
        return "?"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _chu_pct(pct: Any) -> str:
    if pct is None:
        return ""
    return " ({0}{1}% so tuần trước)".format("+" if pct > 0 else "", pct)


def _hop_trong(bo_cuc: Any) -> QWidget:
    """Vỏ trong suốt cho một hàng chip (không ăn nền xám của QWidget mặc định)."""
    hop = QWidget()
    hop.setObjectName("hopTrong")
    hop.setStyleSheet("QWidget#hopTrong{background:transparent;}")
    hop.setLayout(bo_cuc)
    return hop


class KhoiCongTy(QFrame):
    """Khối CÔNG TY: 7 ngày (view/sub/giờ xem so tuần trước) · video hôm nay x/trần · máy · ví · phiên bản ·
    tổng giám đốc. Ô nào cần bạn nhìn mới có màu."""

    def __init__(self, on_hanh_dong: Callable[[str, Dict[str, Any]], None],
                 cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._on_hanh_dong = on_hanh_dong
        self.setObjectName("card")
        theme.bong(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(4)
        hang_tieu = QHBoxLayout()
        hang_tieu.setContentsMargins(0, 0, 0, 0)
        hang_tieu.addWidget(nhan("CÔNG TY", "h2"))
        hang_tieu.addStretch(1)
        self._nut_chi_tiet = nut_phu("Chi tiết máy ▸", lambda: self._on_hanh_dong("chi_tiet_may", {}))
        hang_tieu.addWidget(self._nut_chi_tiet)
        v.addLayout(hang_tieu)
        self._hop = HopXuongDong(8)
        v.addWidget(self._hop)
        hang = self._hop.hang
        self._o_xem = _OChiSoMay("View 7 ngày")
        self._o_sub = _OChiSoMay("Sub 7 ngày")
        self._o_gio = _OChiSoMay("Giờ xem 7 ngày")
        self._o_video = _OChiSoMay("Video hôm nay")
        self._o_may = _OChiSoMay("Máy", lambda: self._on_hanh_dong("chi_tiet_may", {}))
        self._o_vi = _OChiSoMay("Ví", lambda: self._on_hanh_dong("mo_vi", {}))
        self._o_ban = _OChiSoMay("Phiên bản", lambda: self._on_hanh_dong("mo_vi", {}))
        self._o_tong = _OChiSoMay("Tổng giám đốc", lambda: self._on_hanh_dong("bao_cao_cong_ty", {}))
        for o in (self._o_xem, self._o_sub, self._o_gio, self._o_video, self._o_may, self._o_vi, self._o_ban,
                  self._o_tong):
            hang.addWidget(o)
        self._o_tong.setVisible(False)

    def dat_mo_chi_tiet(self, mo: bool) -> None:
        self._nut_chi_tiet.setText("Chi tiết máy ▾" if mo else "Chi tiết máy ▸")

    def nap(self, ct: Dict[str, Any]) -> None:
        tuan = ct.get("tuan") or {}
        for o, khoa, le in ((self._o_xem, "xem", 0), (self._o_sub, "sub", 0), (self._o_gio, "gio_xem", 0)):
            t = tuan.get(khoa) or {}
            pct = t.get("pct")
            if t.get("nay") is None:
                o.dat("đang tính…" if not ct.get("so_kenh_co_so") else "chưa có số", bdk.TOT,
                      "Số 7 ngày của các kênh YouTube (Studio). Lần đầu mở cần ~1 phút để tính.")
                continue
            muc = bdk.LUU_Y if pct is not None and pct <= -20 else bdk.TOT
            mui = "" if pct is None else (" ▲{0}%".format(pct) if pct > 0 else (" ▼{0}%".format(-pct) if pct < 0 else " ●0%"))
            o.dat(_so_vn(t["nay"], le) + mui, muc,
                  "7 ngày qua, cộng mọi kênh YouTube{0}.\n% chỉ so trên các kênh đã có đủ số tuần trước.".format(
                      _chu_pct(pct)))
        hn, tran = ct.get("video_hom_nay"), ct.get("tran")
        self._o_video.dat("{0} / trần {1}".format(hn if hn is not None else "?", tran if tran else "?"), bdk.TOT,
                          "Video dựng xong từ 0 giờ hôm nay / trần máy làm được mỗi ngày (công suất đo 24 giờ).")
        may = ct.get("may") or {}
        self._o_may.dat(str(may.get("chu") or "?"), may.get("muc") or bdk.TOT,
                        (str(may.get("tip") or "") + "\nBấm để xem chi tiết máy.").strip())
        vi = ct.get("vi") or {}
        ngay = vi.get("ngay")
        self._o_vi.dat("còn ~{0:.0f} ngày".format(ngay) if ngay is not None else "chưa ước được",
                       vi.get("muc") or bdk.TOT,
                       ("Số dư {0}₫. ".format(_so_vn(vi.get("vnd"))) if vi.get("vnd") is not None else "")
                       + "Bấm để nạp tiền / xem ví.")
        pb = ct.get("phien_ban") or {}
        if pb:
            chu = "{0} · tự cập nhật {1}".format(pb.get("ban") or "?", "bật" if pb.get("tu_dong") else "TẮT")
            muc = bdk.TOT
            if pb.get("ban_moi"):
                chu = "{0} → có bản {1}".format(pb.get("ban") or "?", pb["ban_moi"])
                muc = bdk.TOT if pb.get("tu_dong") else bdk.LUU_Y
            if pb.get("loi"):
                muc = bdk.LUU_Y
            self._o_ban.dat(chu, muc, "Kiểm lần cuối {0}{1}".format(
                pb.get("kiem_luc") or "?", "\nLỗi: " + pb["loi"] if pb.get("loi") else ""))
        else:
            self._o_ban.dat("?", bdk.TOT)
        tg = ct.get("tong_giam_doc") or {}
        self._o_tong.setVisible(bool(tg.get("cau")))
        if tg.get("cau"):
            self._o_tong.dat(str(tg["cau"]).split(": ", 1)[-1][:60], bdk.TOT,
                             str(tg["cau"]) + "\nBấm để mở Báo cáo công ty.")


def _nhan_nho(chu: str = "", mau: str = "", dam: bool = False, xuong_dong: bool = True) -> QLabel:
    nh = QLabel(chu)
    nh.setWordWrap(xuong_dong)
    nh.setMinimumWidth(1)
    nh.setStyleSheet("font-size:12px;{0}{1}".format("color:{0};".format(mau) if mau else "",
                                                   "font-weight:600;" if dam else ""))
    return nh


class TheKenhLon(QFrame):
    """Một kênh = một thẻ ở phòng điều hành: xếp loại · tiến độ kiếm tiền · 3 cổng · 3 video gần nhất kèm phán
    quyết · đội AI nói · đang thử gì · lịch đăng tiếp · công tắc giám đốc / tạm dừng · 3 nút trang chi tiết."""

    #: Bề rộng tối thiểu hợp lý — KHÔNG `setFixedWidth`: lưới 2 cột co giãn
    #: theo cửa sổ (`_LuoiThe`), ép cứng bề rộng ở đây sẽ làm cửa sổ hẹp tràn.
    RONG_TOI_THIEU = 420

    def __init__(self, ma: str, on_cong_tac: Callable[[str, str, bool], None],
                 on_hanh_dong: Callable[[str, str], None], cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._ma = ma
        self._muc = bdk.TOT
        self._tu_chay = False
        self._dang_nap = False
        self._on_cong_tac = on_cong_tac
        self._on_hanh_dong = on_hanh_dong
        self.setObjectName("theKenhLon")
        self.setMinimumWidth(self.RONG_TOI_THIEU)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(5)

        hang_ten = QHBoxLayout()
        hang_ten.setContentsMargins(0, 0, 0, 0)
        hang_ten.setSpacing(8)
        self._nhan_ten = QLabel(ma)
        self._nhan_ten.setWordWrap(False)
        self._nhan_ten.setMinimumWidth(1)
        self._nhan_ten.setStyleSheet("font-size:15px;font-weight:700;")
        hang_ten.addWidget(self._nhan_ten, 1)
        self._nhan_loai = QLabel("")
        self._nhan_loai.setWordWrap(False)
        hang_ten.addWidget(self._nhan_loai)
        v.addLayout(hang_ten)

        self._nhan_trang_thai = _nhan_nho()
        v.addWidget(self._nhan_trang_thai)
        self._nhan_khau = _nhan_nho(mau=theme.CHU_MO)
        self._nhan_khau.setStyleSheet("color:{0};font-size:11px;".format(theme.CHU_MO))
        self._nhan_khau.setVisible(False)
        v.addWidget(self._nhan_khau)

        # Tiến độ bật kiếm tiền (YPP).
        hang_ypp = QHBoxLayout()
        hang_ypp.setContentsMargins(0, 2, 0, 0)
        hang_ypp.setSpacing(6)
        self._nhan_ypp_sub = _nhan_nho(xuong_dong=False)
        self._thanh_sub = self._thanh()
        self._nhan_ypp_gio = _nhan_nho(xuong_dong=False)
        self._thanh_gio = self._thanh()
        for w in (self._nhan_ypp_sub, self._thanh_sub, self._nhan_ypp_gio, self._thanh_gio):
            hang_ypp.addWidget(w)
        hang_ypp.setStretch(1, 1)
        hang_ypp.setStretch(3, 1)
        v.addLayout(hang_ypp)

        # Ba cổng.
        hang_cong = QHBoxLayout()
        hang_cong.setContentsMargins(0, 2, 0, 2)
        hang_cong.setSpacing(6)
        self._o_cong: List[QLabel] = []
        for _i in range(3):
            nh = QLabel("")
            nh.setWordWrap(True)
            nh.setMinimumWidth(1)
            nh.setAlignment(Qt.AlignCenter)
            hang_cong.addWidget(nh, 1)
            self._o_cong.append(nh)
        v.addLayout(hang_cong)

        v.addWidget(_nhan_nho("Video gần nhất", theme.CHU_MO, dam=True))
        self._hang_video: List[QLabel] = []
        for _i in range(3):
            nh = _nhan_nho(xuong_dong=False)
            nh.setTextFormat(Qt.RichText)
            v.addWidget(nh)
            self._hang_video.append(nh)

        v.addWidget(_nhan_nho("Đội AI nói", theme.CHU_MO, dam=True))
        self._nhan_giam_doc = _nhan_nho()
        self._nhan_giam_doc.setVisible(False)
        v.addWidget(self._nhan_giam_doc)
        self._nhan_ai: List[QLabel] = []
        for _i in range(3):
            nh = _nhan_nho()
            nh.setVisible(False)
            v.addWidget(nh)
            self._nhan_ai.append(nh)
        self._nhan_ai_rong = _nhan_nho("— chưa có chẩn đoán nào", theme.CHU_MO)
        v.addWidget(self._nhan_ai_rong)

        self._nhan_dang_thu = _nhan_nho()
        v.addWidget(self._nhan_dang_thu)
        self._nhan_ke_tiep = _nhan_nho()
        v.addWidget(self._nhan_ke_tiep)

        # Điều khiển ngay trên thẻ.
        hang_dk = HangXuongDong(6)
        nh_gd = QLabel("Giám đốc kênh")
        nh_gd.setStyleSheet("color:{0};font-size:11px;font-weight:600;".format(theme.CHU_MO))
        hang_dk.addWidget(nh_gd)
        self._o_giam_doc = QComboBox()
        for khoa, ten in bdk.CHE_DO_GIAM_DOC:
            self._o_giam_doc.addItem(ten, khoa)
        self._o_giam_doc.setToolTip(
            "Tắt: không làm gì.\nGợi ý: đọc số hằng ngày, ghi “sẽ làm gì” và tự chấm — KHÔNG đổi gì của kênh.\n"
            "Tự áp: đổi tham số kênh trong giới hạn an toàn (tối đa 2 thay đổi/tuần, tự quay lui).")
        self._o_giam_doc.currentIndexChanged.connect(self._bao_giam_doc)
        hang_dk.addWidget(self._o_giam_doc)
        self._nut_tam_dung = nut_phu("Tạm dừng kênh", self._bam_tam_dung)
        hang_dk.addWidget(self._nut_tam_dung)
        self._o_tu_duyet = QCheckBox("Tự lên lịch")
        self._o_tu_duyet.setToolTip(
            "Bật: video làm xong tự hẹn giờ và lên sóng, không chờ bạn xem trước.\n"
            "Tắt: video nằm chờ bạn bấm “Hẹn giờ” ở khối Việc của bạn.")
        self._o_tu_duyet.toggled.connect(lambda bat: self._bao_cong_tac("tu_duyet", bat))
        hang_dk.addWidget(self._o_tu_duyet)
        v.addWidget(_hop_trong(hang_dk))

        hang_nut = HangXuongDong(6)
        self._nut_bao_cao = nut_phu("Báo cáo tuần", lambda: self._on_hanh_dong(self._ma, "bao_cao_giam_doc"))
        hang_nut.addWidget(self._nut_bao_cao)
        self._nut_bai_hoc = nut_phu("Bài học", lambda: self._on_hanh_dong(self._ma, "bai_hoc"))
        hang_nut.addWidget(self._nut_bai_hoc)
        # `&&`: Qt coi một `&` là phím tắt và giấu đi.
        self._nut_quyet = nut_phu("Quyết định && độ chính xác", lambda: self._on_hanh_dong(self._ma, "quyet_dinh"))
        hang_nut.addWidget(self._nut_quyet)
        self._nut_them = nut_phu("⋯", self._menu_them)
        self._nut_them.setToolTip("Xem video chờ đăng · Nhật ký · Mở thư mục · Cài kênh")
        hang_nut.addWidget(self._nut_them)
        v.addWidget(_hop_trong(hang_nut))
        self._co_video = False
        self._ve_vien()

    @staticmethod
    def _thanh() -> QProgressBar:
        t = QProgressBar()
        t.setRange(0, 1000)
        t.setTextVisible(False)
        t.setFixedHeight(6)
        t.setMinimumWidth(40)
        t.setStyleSheet("QProgressBar{{background:{0};border:none;border-radius:3px;}}"
                        "QProgressBar::chunk{{background:{1};border-radius:3px;}}".format(theme.XAM_NEN, theme.NHAN))
        return t

    def _menu_them(self) -> None:
        menu = QMenu(self)
        a = menu.addAction("Xem video chờ đăng", lambda: self._on_hanh_dong(self._ma, "xem_video"))
        a.setEnabled(self._co_video)
        menu.addAction("Nhật ký", lambda: self._on_hanh_dong(self._ma, "nhat_ky"))
        menu.addAction("Mở thư mục", lambda: self._on_hanh_dong(self._ma, "mo_thu_muc"))
        menu.addAction("⚙ Cài kênh", lambda: self._on_hanh_dong(self._ma, "cai_kenh"))
        menu.exec_(self._nut_them.mapToGlobal(self._nut_them.rect().bottomLeft()))

    def _bam_tam_dung(self) -> None:
        if not self._dang_nap:
            self._on_cong_tac(self._ma, "tu_chay", not self._tu_chay)

    def _bao_cong_tac(self, khoa: str, bat: bool) -> None:
        if not self._dang_nap:
            self._on_cong_tac(self._ma, khoa, bool(bat))

    def _bao_giam_doc(self, _i: int = 0) -> None:
        if not self._dang_nap:
            self._on_hanh_dong(self._ma, "giam_doc=" + str(self._o_giam_doc.currentData() or "tat"))

    def nap(self, k: Dict[str, Any]) -> None:
        self._dang_nap = True
        try:
            self._nap_that(k)
        finally:
            self._dang_nap = False

    def _nap_that(self, k: Dict[str, Any]) -> None:
        ph = k.get("phong") or {}
        so = ph.get("so") or {}
        self._muc = str(ph.get("muc") or bdk.muc_phong(k, so))
        ma = str(k.get("ma") or self._ma)
        # `ten` trong kenh.yaml có thể là "tên — mô tả dài" — tiêu đề thẻ chỉ hiện phần TÊN.
        ten_day_du = str(k.get("ten") or ma)
        ten_ngan = ten_day_du.split(" — ", 1)[0].strip() or ten_day_du
        day_du_hien = ma if ten_ngan == ma else "{0} · {1}".format(ma, ten_ngan)
        _cat(self._nhan_ten, day_du_hien, 330)
        self._nhan_ten.setToolTip(ma if ten_day_du == ma else "{0} · {1}".format(ma, ten_day_du))

        loai = str(so.get("loai") or "")
        if loai in bdk.XEP_LOAI:
            dau, chu = bdk.XEP_LOAI[loai]
            self._nhan_loai.setText("{0} {1}".format(dau, chu))
            self._nhan_loai.setStyleSheet("font-size:13px;font-weight:700;color:{0};".format(_MAU_LOAI[loai]))
            da = so.get("da")
            self._nhan_loai.setToolTip(
                "Xếp loại của tổng giám đốc: lên = hiển thị 7 ngày ≥ 1,2× tuần trước và thắng ≥ 25% video 28 ngày; "
                "tụt = ≤ 0,8× tuần trước.\nĐà hiển thị: {0} · thắng 28 ngày: {1}/{2}".format(
                    _so_vn(da, 2) if da is not None else "chưa đủ 2 tuần số", so.get("thang_28", 0), so.get("kl_28", 0)))
        else:
            self._nhan_loai.setText("đang tính số…" if not so else "")
            self._nhan_loai.setStyleSheet("font-size:11px;color:{0};".format(theme.CHU_MO))

        self._tu_chay = bool(k.get("tu_chay"))
        self._nut_tam_dung.setText("Tạm dừng kênh" if self._tu_chay else "▶ Chạy lại kênh")
        self._nut_tam_dung.setToolTip("Kênh đang tự làm video — bấm để tạm dừng." if self._tu_chay
                                      else "Kênh đang dừng, không tự làm video — bấm để chạy lại.")
        self._o_tu_duyet.blockSignals(True)
        self._o_tu_duyet.setChecked(bool(k.get("tu_duyet")))
        self._o_tu_duyet.blockSignals(False)

        mt = k.get("muc_the") or bdk.muc_the(k)
        cau = bdk.cau_tinh_trang(k) if k.get("bay_gio") is not None else ""
        mau_tt = {bdk.HONG: theme.DO, bdk.CHO_BAN: theme.CAM, bdk.LUU_Y: theme.CAM}.get(mt, theme.CHU_MO)
        self._nhan_trang_thai.setText(("Bây giờ: " + cau) if cau else "")
        self._nhan_trang_thai.setVisible(bool(cau))
        self._nhan_trang_thai.setToolTip(str((k.get("bay_gio") or {}).get("chi_tiet") or cau))
        self._nhan_trang_thai.setStyleSheet("font-size:12px;color:{0};{1}".format(
            mau_tt, "font-weight:700;" if mt in (bdk.HONG, bdk.CHO_BAN, bdk.LUU_Y) else ""))
        chu_khau = _dong_khau(k)
        self._nhan_khau.setText(chu_khau)
        self._nhan_khau.setVisible(bool(chu_khau))

        ypp = ph.get("ypp") or {}
        for nh, thanh, gt, can, ten in ((self._nhan_ypp_sub, self._thanh_sub, ypp.get("sub"), bdk.YPP_SUB, "sub"),
                                        (self._nhan_ypp_gio, self._thanh_gio, ypp.get("gio_xem"), bdk.YPP_GIO,
                                         "giờ xem")):
            nh.setText("{0} {1}/{2}".format(ten.capitalize(), _so_vn(gt), _so_vn(can)))
            thanh.setValue(int(min(1.0, (gt or 0) / can) * 1000))
            thanh.setToolTip("Bật kiếm tiền cần {0} {1}. Hiện có {2} ({3:.0f}%).".format(
                _so_vn(can), ten, _so_vn(gt), 100.0 * (gt or 0) / can))

        cong = list(so.get("cong") or [])
        ten_cong = ("Hiển thị", "Tỉ lệ bấm trang chủ", "Giữ chân")
        for i, nh in enumerate(self._o_cong):
            c = cong[i] if i < len(cong) else {"ten": ten_cong[i], "muc": bdk.CHUA, "chu": "đang tính…"}
            chu_m, nen, vien = _MAU_CONG.get(c.get("muc"), _MAU_CONG[bdk.CHUA])
            nh.setText("{0}\n{1}".format(c.get("ten"), c.get("chu") or ""))
            nh.setStyleSheet("QLabel{{background:{0};border:1px solid {1};border-radius:8px;padding:3px 5px;"
                             "color:{2};font-size:11px;font-weight:600;}}".format(nen, vien, chu_m))
            nh.setToolTip({
                "Hiển thị": "Trung vị lượt hiển thị 48 giờ của ≤ 5 video gần nhất, so ngưỡng thắng của kênh.",
                "Tỉ lệ bấm trang chủ": "Trung vị tỉ lệ bấm ở trang chủ YouTube (≤ 5 video), so mục tiêu kênh. "
                                       "Vàng: từ 80% mục tiêu.",
                "Giữ chân": "Trung vị % thời lượng được xem (≤ 5 video, số ≥ 36 giờ), so video thắng của kênh.",
            }.get(str(c.get("ten")), "") + ("\nTính trên {0} video.".format(c.get("n")) if c.get("n") else ""))

        video = list(so.get("video") or [])
        for i, nh in enumerate(self._hang_video):
            if i >= len(video):
                nh.setText("—" if i == 0 and so else "")
                nh.setVisible(i == 0)
                continue
            d = video[i]
            ket = str(d.get("ket") or "cho")
            if ket in _KET_VIDEO:
                chu_ket, mau = _KET_VIDEO[ket]
            else:
                tuoi = d.get("tuoi_gio")
                chu_ket = "… chờ ({0} giờ)".format(_so_vn(tuoi)) if tuoi is not None else "… chờ"
                mau = theme.CHU_MO
            them = ""
            if d.get("hien_thi_48h") is not None:
                them = " · {0} hiển thị 48h".format(_so_vn(d["hien_thi_48h"]))
            elif d.get("hien_thi") is not None:
                them = " · {0} hiển thị".format(_so_vn(d["hien_thi"]))
            if d.get("doan") in ("thang", "truot") and ket not in _KET_VIDEO:
                them += " · giám đốc đoán {0}".format("thắng" if d["doan"] == "thang" else "trượt")
            td = str(d.get("tieu_de") or d.get("id") or "")
            td_ngan = td if len(td) <= 34 else td[:33] + "…"
            nh.setText('<span style="color:{0};font-weight:700;">{1}</span> <span style="color:{2};">{3}</span>'
                       '<span style="color:{4};">{5}</span>'.format(
                           mau, _html(chu_ket), theme.CHU, _html(td_ngan), theme.CHU_MO, _html(them)))
            nh.setToolTip("{0}\n{1}".format(td, d.get("id") or ""))
            nh.setVisible(True)

        gd = k.get("giam_doc") or {}
        ai = list(ph.get("doi_ai") or [])
        cau_gd = next((x["cau"] for x in ai if x.get("ai") == "Giám đốc kênh"), "")
        if not cau_gd and not ai and gd.get("cau"):
            cau_gd = str(gd["cau"]).split(": ", 1)[-1] if str(gd["cau"]).startswith("Giám đốc kênh") else str(gd["cau"])
        con = [x for x in ai if x.get("ai") != "Giám đốc kênh"]
        self._nhan_giam_doc.setText("Giám đốc kênh: " + cau_gd if cau_gd else "")
        self._nhan_giam_doc.setToolTip(str(gd.get("cau") or cau_gd))
        self._nhan_giam_doc.setVisible(bool(cau_gd))
        for i, nh in enumerate(self._nhan_ai):
            if i < len(con):
                nh.setText("{0}: {1}".format(con[i].get("ai"), con[i].get("cau")))
                nh.setToolTip(str(con[i].get("luc") or ""))
                nh.setVisible(True)
            else:
                nh.setVisible(False)
        self._nhan_ai_rong.setText("— giám đốc kênh đang tắt (chọn “Gợi ý” để đội AI bắt đầu đọc số)"
                                   if str(gd.get("che_do") or "tat") == "tat" else "— chưa có chẩn đoán nào")
        self._nhan_ai_rong.setVisible(not cau_gd and not con)

        thu = list(ph.get("dang_thu") or [])
        self._nhan_dang_thu.setText("Đang thử: " + (" · ".join(thu) if thu else "chưa thử gì"))
        lich = list(ph.get("lich_tiep") or [])
        if not self._tu_chay:
            chu_lich = "Lịch đăng tiếp: kênh đang dừng"
        elif lich:
            phan = []
            for x in lich:
                td = str(x.get("tieu_de") or "")
                phan.append("{0} {1}".format(x.get("chu_luc"), "「{0}」".format(td[:24] + ("…" if len(td) > 24 else ""))
                                             if td else "— trống, máy sẽ làm"))
            chu_lich = "Lịch đăng tiếp: " + " · ".join(phan)
        else:
            vkt = k.get("video_ke_tiep") or {}
            tu = str(k.get("video_ke_tiep_tu") or "")
            chu_lich = ("Lịch đăng tiếp: 「{0}」".format(vkt["tieu_de"]) if vkt.get("tieu_de")
                        else "Lịch đăng tiếp: chưa có — máy làm video mới từ {0}".format(tu) if tu
                        else "Lịch đăng tiếp: chưa có")
        self._nhan_ke_tiep.setText(chu_lich)

        i = self._o_giam_doc.findData(str(gd.get("che_do") or "tat"))
        self._o_giam_doc.blockSignals(True)
        self._o_giam_doc.setCurrentIndex(max(0, i))
        self._o_giam_doc.blockSignals(False)
        self._nut_bao_cao.setEnabled(bool(gd.get("bao_cao")))
        self._nut_bao_cao.setToolTip("" if gd.get("bao_cao") else "Giám đốc chưa ghi báo cáo nào")
        self._co_video = bool(k.get("video_ke_tiep"))
        self._ve_vien()

    def _ve_vien(self) -> None:
        mau = {bdk.HONG: (theme.DO_NEN, theme.DO_VIEN), bdk.LUU_Y: (theme.VANG_NEN, theme.VANG_VIEN),
               bdk.TAT: (theme.XAM_NEN, theme.VIEN)}.get(self._muc, (theme.THE, theme.VIEN))
        self.setStyleSheet("QFrame#theKenhLon{{background:{0};border:1px solid {1};border-radius:12px;}}"
                           .format(*mau))


def _html(s: Any) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _dong_khau(k: Dict[str, Any]) -> str:
    """"Kịch bản ✓ Giọng ✓ …" — chỉ khi lượt hôm nay đang làm hoặc dở dang."""
    khau_list = list((k.get("luot") or {}).get("khau") or [])
    if not khau_list:
        return ""
    bay = k.get("bay_gio") or {}
    if not (k.get("dang_chay") or str(bay.get("muc") or "") in ("dang", "loi")):
        return ""
    from core.auto import KHAU  # noqa: PLC0415 — chỉ cần lúc có lượt đang chạy
    from .trang_dieu_khien import DAU_KHAU  # noqa: PLC0415

    theo_ma = {d.get("ma"): d for d in khau_list}
    phan = []
    for ma_khau, ten_khau, _tien, _sp in KHAU:
        trang = str((theo_ma.get(ma_khau) or {}).get("trang_thai") or "")
        dau = DAU_KHAU.get(trang, "○")
        ten_ngan = tt.TEN_KHAU_NGAN.get(ma_khau, ten_khau)
        phan.append("{0} {1}".format(ten_ngan, dau))
    return "  ".join(phan)


class _LuoiThe(QWidget):
    """Lưới thẻ kênh: 2 cột khi ≥1000px, 1 cột khi hẹp — mục 3 "trang chính".

    Thẻ được GIỮ LẠI giữa các lần làm mới (nếp `TrangTrungTam._ve_the`): trang
    gọi `them`/`xoa` cho đúng phần đổi, KHÔNG dựng lại toàn bộ mỗi 30 giây.
    """

    def __init__(self, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(10)
        self._the: Dict[str, QWidget] = {}
        self._thu_tu: List[str] = []
        self._cot = 1

    def dat_thu_tu(self, thu_tu: List[str]) -> None:
        self._thu_tu = list(thu_tu)
        self._xep_lai()

    def the(self, ma: str) -> Optional[QWidget]:
        return self._the.get(ma)

    def them(self, ma: str, widget: QWidget) -> None:
        self._the[ma] = widget
        self._xep_lai()

    def xoa(self, ma: str) -> None:
        w = self._the.pop(ma, None)
        if w is not None:
            self._grid.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
        self._xep_lai()

    def resizeEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        super().resizeEvent(su_kien)
        cot_moi = 2 if self.width() >= BE_RONG_HAI_COT else 1
        if cot_moi != self._cot:
            self._cot = cot_moi
            self._xep_lai()

    def _xep_lai(self) -> None:
        cot = max(1, self._cot)
        for c in range(cot):
            self._grid.setColumnStretch(c, 1)
        # Thứ tự thẻ đổi được (kênh đỏ lên đầu) — gỡ hết khỏi lưới rồi đặt lại, không để một thẻ chiếm 2 ô.
        for w in self._the.values():
            self._grid.removeWidget(w)
        for i, ma in enumerate(self._thu_tu):
            w = self._the.get(ma)
            if w is None:
                continue
            r, c = divmod(i, cot)
            self._grid.addWidget(w, r, c)


# ═══════════════════════════════════════════════════════════════════════════
# Trang
# ═══════════════════════════════════════════════════════════════════════════


class TrangBangDieuKhien(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._bang: Dict[str, Any] = {}
        self._may: Dict[str, Dict[str, Any]] = {}
        self._lich: Optional[Dict[str, Any]] = None
        self._lich_luc = 0.0
        self._vi_luc = 0.0
        self._windows_luc = 0.0
        self._windows_canh_bao: Dict[str, str] = {}
        self._dang_nap = False
        self._dong = False
        self._the_kenh: Dict[str, TheKenhLon] = {}
        self._mo_kenh_khac = False
        self._phong: Dict[str, Any] = {}
        self._tinh_luc = 0.0
        self._mo_chi_tiet_may = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(8)
        doc.addWidget(self._hang_tieu_de())
        self._khoi_cong_ty = KhoiCongTy(self._hanh_dong)
        doc.addWidget(self._khoi_cong_ty)
        self._dong_may = DongMay(self._hanh_dong)
        self._dong_may.setVisible(False)
        doc.addWidget(self._dong_may)
        self._khoi_viec = KhoiViec(self._hanh_dong)
        doc.addWidget(self._khoi_viec)
        self._nhan_dang_tinh = nhan("", "muted")
        self._nhan_dang_tinh.setVisible(False)
        doc.addWidget(self._nhan_dang_tinh)
        self._luoi = _LuoiThe()
        doc.addWidget(self._luoi)
        self._nhan_kenh_khac = nhan("")
        self._nhan_kenh_khac.setStyleSheet("color:{0};font-size:12px;".format(theme.CHU_MO))
        self._nhan_kenh_khac.setCursor(Qt.PointingHandCursor)
        self._nhan_kenh_khac.mousePressEvent = self._bam_kenh_khac  # type: ignore[assignment]
        self._nhan_kenh_khac.setVisible(False)
        doc.addWidget(self._nhan_kenh_khac)
        doc.addStretch(1)

        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(lambda: self.lam_moi(bat_buoc=False))
        self._dong_ho.start(NHIP_LAM_MOI_MS)

        self._hoi_lich()
        self.lam_moi()

    # ── Vòng đời ─────────────────────────────────────────────────────────────

    def _con_song(self) -> bool:
        return not self._dong and not getattr(self._app, "_dang_dong", False)

    def closeEvent(self, event) -> None:  # noqa: N802 — tên do Qt quy định
        self._dong = True
        self._dong_ho.stop()
        super().closeEvent(event)

    # ── Đầu trang ────────────────────────────────────────────────────────────

    def _hang_tieu_de(self) -> QWidget:
        from .huong_dan import nut_huong_dan  # noqa: PLC0415

        hop = QWidget()
        ngang = QHBoxLayout(hop)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(8)
        tieu = nhan("Phòng điều hành công ty", "h1")
        tieu.setWordWrap(False)
        ngang.addWidget(tieu)
        self._nhan_luc = nhan("", "muted")
        self._nhan_luc.setMinimumWidth(1)
        ngang.addWidget(self._nhan_luc, 1)
        # Huy hiệu "Có bản mới x.y.z" — CHỈ khi máy này TẮT tự cập nhật (bật thì
        # tool tự cài lúc rảnh, không cần ai nhìn). Bấm → Cài đặt, khung Cập nhật.
        self._huy_hieu_cn = nut_phu("", lambda: self._hanh_dong("mo_vi", {}))
        self._huy_hieu_cn.setStyleSheet(
            "color:{0};font-weight:600;".format(theme.XANH))
        self._huy_hieu_cn.setVisible(False)
        ngang.addWidget(self._huy_hieu_cn)
        ngang.addWidget(nut_phu("Làm mới", lambda: self.lam_moi(), rong=90))
        nut_hd = nut_huong_dan("tong-quan", hop)
        if nut_hd is not None:
            ngang.addWidget(nut_hd)
        return hop

    # ── Hành động chung — nút của KhoiViec, DongMay, thẻ kênh ────────────────

    def _kenh(self, ma: str) -> Optional[Dict[str, Any]]:
        for k in (self._bang.get("kenh") or []):
            if k.get("ma") == ma:
                return k
        return None

    def _dong_ke_hoach(self, ma: str, ma_goi: str) -> Optional[Dict[str, Any]]:
        k = self._kenh(ma) or {}
        for d in (k.get("ke_hoach") or []):
            if d.get("ma_goi") == ma_goi:
                return d
        return None

    def _hanh_dong(self, ma_hanh_dong: str, tham_so: Dict[str, Any]) -> None:
        """Một cửa duy nhất cho mọi nút của khối Việc + dòng Máy.

        Tách hành động khỏi widget (thay vì mỗi nút tự biết đường ghi) để bài
        kiểm chỉ cần monkeypatch đúng MỘT chỗ cho mỗi đường ghi, và để thêm một
        hàng việc mới (mục 3, bảng 14 dòng) không phải sửa `KhoiViec`.
        """
        if not self._con_song():
            return
        goc = self._app.base_dir
        ma = str(tham_so.get("ma") or "")
        ma_goi = str(tham_so.get("ma_goi") or "")

        if ma_hanh_dong == "xem_video":
            d = self._dong_ke_hoach(ma, ma_goi)
            video = str((d or {}).get("video") or "")
            if video and os.path.isfile(video):
                mo_thu_muc(video)
            else:
                self._app.show_message("Không thấy video",
                                       "Tệp video của gói này không còn trên máy.")
        elif ma_hanh_dong == "bao_cao_giam_doc":
            self._mo_chi_tiet("bao_cao", ma)
        elif ma_hanh_dong == "bao_cao_cong_ty":
            self._mo_bao_cao_cong_ty()
        elif ma_hanh_dong == "chi_tiet_may":
            self._mo_chi_tiet_may = not self._mo_chi_tiet_may
            self._dong_may.setVisible(self._mo_chi_tiet_may)
            self._khoi_cong_ty.dat_mo_chi_tiet(self._mo_chi_tiet_may)
        elif ma_hanh_dong == "hen_gio":
            d = self._dong_ke_hoach(ma, ma_goi)
            if d is None:
                return
            k = self._kenh(ma) or {}
            hop = HopDuyet(d, str(k.get("gio_dang") or "20:00"), self)
            if hop.exec_() != QDialog.Accepted:
                return
            try:
                tt.duyet_dang(goc, ma, ma_goi, hop.ngay, hop.gio)
            except Exception as loi:  # noqa: BLE001
                self._app.show_error(loi)
                return
            self.lam_moi()
        elif ma_hanh_dong == "bo_dang":
            hoi = QMessageBox.question(
                self, "Bỏ video", "Không đăng video này?\n\nTệp vẫn giữ nguyên "
                "— đổi ý thì hẹn giờ lại là được.")
            if hoi != QMessageBox.Yes:
                return
            try:
                tt.bo_dang(goc, ma, ma_goi)
            except Exception as loi:  # noqa: BLE001
                self._app.show_error(loi)
                return
            self.lam_moi()
        elif ma_hanh_dong == "danh_dau_dang_tay":
            hoi = QMessageBox.question(
                self, "Đã đăng thủ công?",
                "Xác nhận video này đã lên YouTube?\n\nTool sẽ ghi ngày giờ hiện "
                "tại, tính lịch nội dung kế tiếp và tự dọn dữ liệu nặng sau thời "
                "gian an toàn.")
            if hoi != QMessageBox.Yes:
                return
            try:
                from core import ban_giao_dang  # noqa: PLC0415

                ban_giao_dang.danh_dau_dang_tay(goc, ma, ma_goi)
            except Exception as loi:  # noqa: BLE001
                self._app.show_error(loi)
                return
            self.lam_moi()
        elif ma_hanh_dong == "chay_lai":
            self._chay_ngay(ma)
        elif ma_hanh_dong in ("nhat_ky", "nhat_ky_may_dang"):
            self._mo_nhat_ky(ma)
        elif ma_hanh_dong == "xem_chi_tiet_kiem":
            kq = bdk.doc_kiem_dom(tt.thu_muc_vm(goc), ma)
            buoc = ", ".join((kq or {}).get("hong_ten") or []) or "một ô"
            self._app.show_message(
                "Máy đăng — kiểm {0}".format(ma),
                "Không nhận ra: {0}.\nLần kiểm gần nhất: {1}.".format(
                    buoc, (kq or {}).get("ngay") or "?"))
        elif ma_hanh_dong == "chep_link":
            self._chep_link(str(tham_so.get("url") or ""))
        elif ma_hanh_dong == "danh_dau_xong":
            bdk.danh_dau_xong(goc, str(tham_so.get("khoa") or ""))
            self.lam_moi()
        elif ma_hanh_dong in ("duyet_sua", "bo_sua"):
            # Cứu video CTR thấp: CHỈ ghi sổ duyệt (`giam-doc/duyet-sua.json`); gác tổng xếp hàng sửa.
            try:
                from core.giam_doc import cuu_ctr  # noqa: PLC0415

                cuu_ctr.ghi_duyet(goc, ma, str(tham_so.get("id") or ""), duyet=ma_hanh_dong == "duyet_sua")
            except Exception as loi:  # noqa: BLE001
                self._app.show_error(loi)
                return
            self.lam_moi()
        elif ma_hanh_dong == "mo_vi":
            # 29/09/2026 (kiểm toán #12): "may-vi" không nằm trong
            # `core.che_do_vps.TRANG_VPS` nên trên VPS (trang này CHỈ dựng ở
            # chế độ VPS) `show_page` không tìm thấy trang, bấm nút không ra
            # gì. "he-thong" (Cài đặt) mới đúng khoá VPS — cùng file
            # `trang_may_vi.py`, lớp `TrangHeThongVps` (xem `ui_qt/app.py:566`).
            mo = getattr(self._app, "show_page", None)
            if mo is not None:
                mo("he-thong")
        elif ma_hanh_dong == "dang_nhap":
            mo = getattr(self._app, "show_page", None)
            if mo is not None:
                mo("he-thong")
        elif ma_hanh_dong == "mo_thu_muc":
            duong = str(tham_so.get("duong") or "") or goc
            mo_thu_muc(duong)
        elif ma_hanh_dong == "bat_lai_may":
            self._bat_lai_may(str(tham_so.get("ten") or "agent"))
        elif ma_hanh_dong == "menu_may":
            self._menu_may()
        elif ma_hanh_dong == "bat_lich":
            self._mo_lich()
        elif ma_hanh_dong == "xem_canh_bao_windows":
            self._app.show_message(
                self._windows_canh_bao.get("tieu_de") or "Windows",
                self._windows_canh_bao.get("chi_tiet") or "")

    def _chep_link(self, url: str) -> None:
        if not url:
            return
        from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

        clip = QApplication.clipboard()
        if clip is not None:
            clip.setText(url)
        self._nhan_luc.setText("Đã chép: " + url)
        QTimer.singleShot(4000, lambda: self._nhan_luc.setText(self._chu_luc()))

    def _chu_luc(self) -> str:
        luc = str(self._bang.get("luc") or "")[11:16]
        return "Cập nhật {0} · tự làm mới".format(luc) if luc else ""

    def _chay_ngay(self, ma: str) -> None:
        k = self._kenh(ma) or {}
        if not k.get("ngan_sach_ngay"):
            self._app.show_message(
                "Chưa đặt tiền mỗi ngày",
                "Kênh {0} đang để 0₫/ngày — máy KHÔNG sản xuất gì cả. Mở "
                "“⚙ Cài kênh” đặt “Tiền mỗi ngày” rồi bấm lại.".format(ma))
            return
        hoi = QMessageBox.question(
            self, "Chạy lại",
            "Làm video hôm nay cho kênh {0} ngay bây giờ?\n\nTốn tiền thật, "
            "trong trần mỗi ngày.".format(ma))
        if hoi != QMessageBox.Yes:
            return
        goc = self._app.base_dir

        def xong(ket) -> None:
            _ok, msg = ket
            self._nhan_luc.setText(msg)
            QTimer.singleShot(3000, self.lam_moi)

        self._app.run_bg(lambda: tt.chay_ngay(goc, ma), on_ok=xong,
                         on_err=self._app.show_error)

    def _bat_lai_may(self, ten: str) -> None:
        gs = _giam_sat(self._app)
        if gs is None:
            return
        self._app.run_bg(lambda: gs.khoi_dong_lai(ten),
                         on_ok=lambda _k: self.lam_moi(), on_err=self._app.show_error)

    def _menu_may(self) -> None:
        gs = _giam_sat(self._app)
        if gs is None:
            return
        menu = QMenu(self)
        menu.addAction("Bật lại", lambda: self._bat_lai_may("agent"))
        menu.exec_(self.cursor().pos())

    def _mo_lich(self) -> None:
        from .trang_trung_tam import KhoiLich  # noqa: PLC0415

        hop = QDialog(self)
        hop.setWindowTitle("Lịch hằng ngày")
        v = QVBoxLayout(hop)
        v.addWidget(nhan("Tới giờ này mỗi ngày, máy tự làm lần lượt mọi kênh đã bật "
                         "“Tự làm video”. Máy phải đang bật và đã đăng nhập.", "muted"))
        v.addWidget(KhoiLich(self._app, on_doi=self._hoi_lich, cha=hop))
        v.addWidget(nut_phu("Đóng", hop.accept, rong=90))
        hop.exec_()

    def _mo_nhat_ky(self, ma: str) -> None:
        k = self._kenh(ma)
        if k is None:
            return
        hop = HopNhatKyKenh(ma, self)
        hop.nap(k)
        hop.exec_()

    def _ghi_roi_lam_moi(self, ham: Callable[[], None]) -> None:
        try:
            ham()
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self.lam_moi()

    def _mo_cai_kenh(self, ma: str) -> None:
        k = self._kenh(ma)
        if k is None:
            return
        goc = self._app.base_dir
        hop = HopCaiDatKenh(ma, self)
        hop.xin_cong_tac.connect(self._ghi_cong_tac)
        hop.xin_ngan_sach.connect(
            lambda m, gt: self._ghi_roi_lam_moi(lambda: bdk.doi_ngan_sach(goc, m, gt)))
        hop.xin_gio_dang.connect(
            lambda m, g: self._ghi_roi_lam_moi(lambda: bdk.doi_gio_dang(goc, m, g)))
        hop.xin_nhip_dang.connect(
            lambda m, ck, tg: self._ghi_roi_lam_moi(lambda: bdk.doi_nhip_dang(goc, m, ck, tg)))
        hop.xin_phut_phien.connect(
            lambda m, p: self._ghi_roi_lam_moi(lambda: bdk.doi_phut_phien(goc, m, p)))
        hop.xin_giu_luot.connect(
            lambda m, s: self._ghi_roi_lam_moi(lambda: bdk.doi_giu_luot(goc, m, s)))
        from core import vm_cai_dat  # noqa: PLC0415

        hop.nap(k, vm_cai_dat.doc(goc, ma))
        hop.exec_()

    def _the_hanh_dong(self, ma: str, ma_hanh_dong: str) -> None:
        if ma_hanh_dong == "xem_video":
            k = self._kenh(ma) or {}
            vkt = k.get("video_ke_tiep") or {}
            ma_goi = str(vkt.get("ma_goi") or "")
            d = self._dong_ke_hoach(ma, ma_goi) if ma_goi else None
            video = str((d or {}).get("video") or "")
            if video and os.path.isfile(video):
                mo_thu_muc(video)
            else:
                self._app.show_message("Chưa có video",
                                       "Kênh này chưa có video sẵn sàng để xem.")
        elif ma_hanh_dong == "mo_thu_muc":
            k = self._kenh(ma) or {}
            d = ((k.get("luot") or {}).get("thu_muc") or "")
            if not d or not os.path.isdir(d):
                from core.kenh import duong_kenh  # noqa: PLC0415

                d = duong_kenh(self._app.base_dir, ma)
            mo_thu_muc(d)
        elif ma_hanh_dong == "nhat_ky":
            self._mo_nhat_ky(ma)
        elif ma_hanh_dong == "cai_kenh":
            self._mo_cai_kenh(ma)
        elif ma_hanh_dong == "bao_cao_giam_doc":
            self._mo_chi_tiet("bao_cao", ma)
        elif ma_hanh_dong in ("bai_hoc", "quyet_dinh"):
            self._mo_chi_tiet(ma_hanh_dong, ma)
        elif ma_hanh_dong.startswith("giam_doc="):
            self._doi_giam_doc(ma, ma_hanh_dong.split("=", 1)[1])

    def _mo_chi_tiet(self, trang: str, ma: str) -> None:
        """Ba trang chi tiết của phòng điều hành (`ui_qt.trang_phong_chi_tiet`)."""
        if not self._con_song():
            return
        from . import trang_phong_chi_tiet as ct  # noqa: PLC0415

        lop = {"bao_cao": ct.HopBaoCaoTuan, "bai_hoc": ct.HopBaiHoc, "quyet_dinh": ct.HopQuyetDinh}[trang]
        hop = lop(self._app, ma, self)
        hop.exec_()

    def _doi_giam_doc(self, ma: str, che_do: str) -> None:
        """Công tắc 3 nấc `kenh.yaml: giam_doc`. Lên "Tự áp" thì hỏi trước."""
        if not self._con_song() or not ma:
            return
        if che_do == "tu_ap":
            hoi = QMessageBox.question(
                self, "Giám đốc kênh — Tự áp",
                "Giám đốc kênh {0} sẽ TỰ ĐỔI vài tham số của kênh (tỉ trọng công thức, độ dài, luật chọn tuần) "
                "trong giới hạn an toàn: tối đa 2 thay đổi/tuần, tự quay lui khi số tụt. Bật?".format(ma))
            if hoi != QMessageBox.Yes:
                self._nap_lai_the(ma)
                return
        goc = self._app.base_dir
        self._ghi_roi_lam_moi(lambda: bdk.doi_giam_doc(goc, ma, che_do))

    def _mo_bao_cao_cong_ty(self) -> None:
        """Hộp chỉ đọc `workspace/tong-giam-doc/BAO-CAO-CONG-TY.md`."""
        duong = os.path.join(self._app.base_dir, "workspace", "tong-giam-doc", "BAO-CAO-CONG-TY.md")
        self._mo_bao_cao_giam_doc("", duong=duong, tieu_de="Báo cáo công ty — tổng giám đốc")

    def _mo_bao_cao_giam_doc(self, ma: str, *, duong: str = "", tieu_de: str = "") -> None:
        """Hộp chỉ đọc `CHANNEL/<ma>/giam-doc/BAO-CAO-TUAN.md` (hoặc `duong`)."""
        if not duong:
            duong = str(((self._kenh(ma) or {}).get("giam_doc") or {}).get("bao_cao") or "")
        if not duong:
            duong = bdk.giam_doc_the(self._app.base_dir, ma).get("bao_cao") or ""
        try:
            with open(duong, encoding="utf-8") as tep:
                chu = tep.read()
        except OSError:
            self._app.show_message("Chưa có báo cáo", "Giám đốc {0} chưa ghi báo cáo nào.".format(ma or "công ty"))
            return
        hop = QDialog(self)
        hop.setWindowTitle(tieu_de or "Báo cáo tuần — giám đốc kênh {0}".format(ma))
        hop.resize(760, 620)
        v = QVBoxLayout(hop)
        o = QTextEdit()
        o.setReadOnly(True)
        if hasattr(o, "setMarkdown"):
            o.setMarkdown(chu)
        else:
            o.setPlainText(chu)
        v.addWidget(o, 1)
        v.addWidget(nut_phu("Đóng", hop.accept, rong=90))
        hop.exec_()

    def _ghi_cong_tac(self, ma: str, khoa: str, bat: bool) -> None:
        """Cửa ghi công tắc DÙNG CHUNG cho hộp ⚙ Cài kênh và hai công tắc trên
        thẻ — xem docstring đầu tệp vì sao `tu_duyet` không đi qua
        `bdk.doi_cong_tac`."""
        if not self._con_song() or not ma:
            return
        goc = self._app.base_dir
        try:
            if khoa == "tu_duyet":
                tt.ghi_cai_kenh(goc, ma, tu_duyet=bool(bat))
            else:
                bdk.doi_cong_tac(goc, ma, khoa, bool(bat))
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        if khoa == "tu_chay" and bat and not (self._kenh(ma) or {}).get("ngan_sach_ngay"):
            self._app.show_message(
                "Chưa đặt tiền mỗi ngày",
                "Đã bật “Tự làm video” cho {0}, nhưng tiền mỗi ngày đang là 0₫ "
                "— máy sẽ KHÔNG làm gì cho tới khi bạn đặt một con số ở "
                "“⚙ Cài kênh”.".format(ma))
        self.lam_moi()

    def _k_the(self, ma: str) -> Optional[Dict[str, Any]]:
        """Dòng kênh của `anh_bang` kèm phần phòng điều hành — đúng thứ `TheKenhLon.nap` cần."""
        k = self._kenh(ma)
        if k is None:
            return None
        return dict(k, phong=(self._phong.get("the") or {}).get(ma) or {})

    def _nap_lai_the(self, ma: str) -> None:
        the, k = self._the_kenh.get(ma), self._k_the(ma)
        if the is not None and k is not None:
            the.nap(k)

    def _the_cong_tac(self, ma: str, khoa: str, bat: bool) -> None:
        if khoa == "tu_duyet" and bat:
            hoi = QMessageBox.question(
                self, "Tự lên lịch",
                "Video làm xong sẽ tự hẹn giờ và lên sóng, không chờ bạn xem "
                "trước. Bật?")
            if hoi != QMessageBox.Yes:
                self._nap_lai_the(ma)
                return
        if khoa == "tu_chay" and not bat:
            hoi = QMessageBox.question(
                self, "Tạm dừng kênh",
                "Tạm dừng kênh {0}? Máy sẽ KHÔNG làm video mới cho kênh này cho tới khi bạn bấm "
                "“Chạy lại kênh”. Video đã hẹn lịch vẫn lên sóng.".format(ma))
            if hoi != QMessageBox.Yes:
                self._nap_lai_the(ma)
                return
        self._ghi_cong_tac(ma, khoa, bat)

    def _bam_kenh_khac(self, _su_kien=None) -> None:
        self._mo_kenh_khac = not self._mo_kenh_khac
        self._ve_kenh_khac()

    # ── Làm mới ──────────────────────────────────────────────────────────────

    def _gio_lich(self) -> Optional[str]:
        if self._lich is None:
            return None
        if not self._lich.get("da_dang_ky"):
            return ""
        return gio_hhmm(self._lich.get("gio"))

    def _hoi_lich(self) -> None:
        goc = self._app.base_dir

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.trang_thai(goc)

        def xong(ket) -> None:
            self._lich = dict(ket or {})
            self._lich_luc = time.monotonic()
            self.lam_moi(bat_buoc=False)

        self._app.run_bg(viec, on_ok=xong, on_err=lambda _l: None)

    def _ve_huy_hieu_cap_nhat(self) -> None:
        """Đọc `workspace/cap-nhat/trang-thai.json` (một tệp JSON nhỏ, luồng vẽ được)."""
        try:
            from core import cap_nhat_git as cng  # noqa: PLC0415

            tt = cng.doc_trang_thai(self._app.base_dir)
            tat = not cng.doc_cau_hinh(self._app.base_dir)["tu_dong_cap_nhat"]
        except Exception:  # noqa: BLE001
            return
        hien = bool(tat and tt.get("ban_moi"))
        if hien:
            self._huy_hieu_cn.setText("Có bản mới {0}".format(tt["ban_moi"]))
            self._huy_hieu_cn.setToolTip(
                "Máy này đang TẮT tự cập nhật. Bấm để xem thay đổi và cập nhật.")
        self._huy_hieu_cn.setVisible(hien)

    def lam_moi(self, bat_buoc: bool = True) -> None:
        if not self._con_song() or (not bat_buoc and not self.isVisible()):
            return
        self._ve_huy_hieu_cap_nhat()
        if self._dang_nap:
            return
        self._dang_nap = True
        goc = self._app.base_dir
        gio_lich = self._gio_lich()
        gs = _giam_sat(self._app)
        if self._lich is not None and time.monotonic() - self._lich_luc > GIAY_HOI_LICH:
            self._hoi_lich()
        so_du_micro = getattr(self._app, "last_wallet_micro", None)
        co_client = getattr(self._app, "client", None) is not None
        can_windows = (time.monotonic() - self._windows_luc > GIAY_HOI_WINDOWS
                      or self._windows_luc == 0.0)

        def viec():
            anh = tt.anh_chup(goc, tat_ca=False, co_nhom=False, gio_lich=gio_lich)
            may = {}
            if gs is not None:
                try:
                    may = dict(gs.trang_thai() or {})
                except Exception:  # noqa: BLE001
                    may = {}
            bang = bdk.anh_bang(goc, anh=anh, gio_lich=gio_lich, so_du_micro=so_du_micro,
                                trang_thai_may=may, co_client=co_client)
            win = None
            if can_windows:
                try:
                    from core import tong_quan_vps  # noqa: PLC0415

                    win = tong_quan_vps.canh_bao_windows() or {}
                except Exception:  # noqa: BLE001
                    win = {}
            try:
                phong = bdk.phong_dieu_hanh(goc, bang)
            except Exception:  # noqa: BLE001 — phần phòng điều hành hỏng không làm mất khối việc/máy
                phong = {}
            return bang, may, win, phong

        def loi(e) -> None:
            self._dang_nap = False
            self._nhan_luc.setText("Không đọc được: {0}".format(str(e)[:120]))

        self._app.run_bg(viec, on_ok=self._nhan_ket_qua, on_err=loi)

    def _may_bat_tu(self) -> str:
        try:
            import ctypes  # noqa: PLC0415

            giay = ctypes.windll.kernel32.GetTickCount64() / 1000.0  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 — không phải Windows, hay lỗi lạ
            return ""
        ngay, du = divmod(int(giay), 86400)
        gio = du // 3600
        if ngay > 0:
            return "{0} ngày {1} giờ".format(ngay, gio)
        if gio > 0:
            return "{0} giờ".format(gio)
        return "vài phút"

    @staticmethod
    def _quet_studio_gan_nhat(kenh: List[Dict[str, Any]]) -> str:
        moc = ""
        for k in kenh:
            ket = ((k.get("phien") or {}).get("ket_qua") or {})
            for khoa in ("ket_thuc", "bat_dau"):
                gt = str(ket.get(khoa) or "")
                if gt > moc:
                    moc = gt
        if not moc:
            return ""
        hom_nay = _dt.date.today().isoformat()
        gio = moc[11:16] if len(moc) >= 16 else moc
        return "{0} hôm nay".format(gio) if moc.startswith(hom_nay) else "{0} ({1})".format(
            gio, moc[:10])

    def _nhan_ket_qua(self, ket) -> None:
        self._dang_nap = False
        if not self._con_song():
            return
        bang, may, win, phong = ket
        self._bang = bang
        self._may = may
        self._phong = phong or {}
        if win is not None:
            self._windows_canh_bao = win
            self._windows_luc = time.monotonic()
        self._nhan_luc.setText(self._chu_luc())
        self._ve_viec()
        self._ve_may()
        self._khoi_cong_ty.nap(self._phong.get("cong_ty") or {})
        self._ve_the(list(bang.get("kenh") or []))
        self._ve_kenh_khac()
        self._tinh_so_neu_can()
        self._hoi_vi()

    def _tinh_so_neu_can(self) -> None:
        """Số kênh cũ/chưa có → sinh tiến trình con tính (tối đa mỗi `GIAY_TINH_LAI` một lần)."""
        can = list(self._phong.get("can_tinh") or [])
        dang = bool(self._phong.get("dang_tinh"))
        if can and not dang and (not self._tinh_luc or time.monotonic() - self._tinh_luc > GIAY_TINH_LAI):
            self._tinh_luc = time.monotonic()
            try:
                if bdk.sinh_tinh_so(self._app.base_dir, can):
                    dang = True
            except Exception:  # noqa: BLE001
                pass
        self._nhan_dang_tinh.setText("Đang tính số kênh ({0})… lát nữa tự hiện.".format(", ".join(can))
                                     if dang and can else "")
        self._nhan_dang_tinh.setVisible(bool(dang and can))

    def _hoi_vi(self) -> None:
        """Số dư ví tối đa 5 phút/lần (CLAUDE.md luật 4).

        Nạp lại bằng `lam_moi(bat_buoc=False)` sau khi có số mới, KHÔNG tự vá
        thẳng vào `self._bang["may"]["vi"]`: "đủ ~N ngày" là một con số suy ra
        từ số dư (`bdk.dong_may`), tính lại tay ở đây dễ lệch với công thức
        thật hơn là gọi lại đúng một lượt.
        """
        if getattr(self._app, "client", None) is None:
            return
        if self._vi_luc and time.monotonic() - self._vi_luc < GIAY_HOI_VI:
            return
        if not self.isVisible():
            return
        self._vi_luc = time.monotonic()
        client = self._app.client

        def viec():
            from core.api import fetch_balance  # noqa: PLC0415

            return fetch_balance(client)

        def xong(so_du) -> None:
            ghi = getattr(self._app, "note_balance", None)
            if ghi is not None:
                ghi(so_du)
            if self._con_song():
                self.lam_moi(bat_buoc=False)

        self._app.run_bg(viec, on_ok=xong, on_err=lambda _l: None)

    def _ve_viec(self) -> None:
        danh_sach = list(self._bang.get("viec") or [])
        if self._windows_canh_bao:
            # Cùng khuôn `{khoa, muc, kenh, chu, goi_y, nut, xong_tay}` mà
            # `bang_dieu_khien.viec_cua_ban` trả — Việc 1 CỐ Ý không gộp
            # `canh_bao_windows()` vào đó (mục 5 bản thiết kế), nên tự ghép ở
            # đây thành MỘT dòng "Windows sắp hết hạn" (dòng 14) đứng đầu danh
            # sách vì luôn ở mức HỎNG.
            danh_sach = [{
                "khoa": _khoa_windows(), "muc": bdk.HONG, "kenh": "",
                "chu": self._windows_canh_bao.get("tieu_de") or "Windows đã tự tắt máy",
                "goi_y": "→ xem cách xử lý", "xong_tay": False,
                "nut": [("Xem cách xử lý", "xem_canh_bao_windows", {})],
            }] + danh_sach
        self._khoi_viec.nap(danh_sach)

    def _ve_may(self) -> None:
        may = dict(self._bang.get("may") or {})
        kenh = list(self._bang.get("kenh") or [])
        may["_co_kenh_tu_chay"] = any(k.get("tu_chay") for k in kenh)
        self._dong_may.nap(may, self._app.base_dir, self._may_bat_tu(),
                           self._quet_studio_gan_nhat(kenh))

    def _ve_the(self, kenh: List[Dict[str, Any]]) -> None:
        con = {k["ma"] for k in kenh}
        for ma in [m for m in self._the_kenh if m not in con]:
            self._the_kenh.pop(ma)
            self._luoi.xoa(ma)
        the_phong = self._phong.get("the") or {}
        for k in kenh:
            ma = k["ma"]
            t = self._the_kenh.get(ma)
            if t is None:
                t = TheKenhLon(ma, self._the_cong_tac, self._the_hanh_dong, self._luoi)
                self._the_kenh[ma] = t
                self._luoi.them(ma, t)
            t.nap(dict(k, phong=the_phong.get(ma) or {}))
        # Kênh ĐỎ lên đầu (`bdk.muc_phong`), rồi vàng, xanh, tắt.
        thu_tu = [m for m in (self._phong.get("thu_tu") or []) if m in con]
        self._luoi.dat_thu_tu(thu_tu + [k["ma"] for k in kenh if k["ma"] not in thu_tu])

    def _ve_kenh_khac(self) -> None:
        khac = list(self._bang.get("kenh_khac") or [])
        if not khac:
            self._nhan_kenh_khac.setVisible(False)
            return
        ten = ", ".join(str(k.get("ma") or "") for k in khac)
        mui = "▾" if self._mo_kenh_khac else "▸"
        chu = "Kênh khác đang tắt: {0} {1}".format(ten if self._mo_kenh_khac else
                                                    "{0} kênh".format(len(khac)), mui)
        self._nhan_kenh_khac.setText(chu)
        self._nhan_kenh_khac.setToolTip(ten)
        self._nhan_kenh_khac.setVisible(True)
