"""Trang **Bảng điều khiển** — mặt mở đầu mới của máy VPS (Việc 2,
`workspace/THIET-KE-BANG-DIEU-KHIEN.md`, duyệt 29/09/2026).

Mục tiêu (mục 0 của bản thiết kế): mở tool trả lời BA câu trong 5 giây —
(a) các kênh có ổn không, (b) tôi cần làm gì, (c) kết quả ra sao. Ba khối, trên
xuống dưới:

* `KhoiViec` — "VIỆC CỦA BẠN": danh sách việc TAY, xếp hỏng (✕) trước, cần xem
  (⚠) sau, thông tin (•) cuối — từ `core.bang_dieu_khien.viec_cua_ban` cộng
  thêm dòng "Windows sắp hết hạn" (`core.tong_quan_vps.canh_bao_windows`, Việc 1
  cố ý không gộp hàm đó vào `viec_cua_ban`).
* `DongMay` — một dòng: ví (+ còn chạy bao lâu), ổ đĩa, máy bật từ bao giờ, máy
  chạy nền, lần quét Studio gần nhất, lịch hằng ngày. Mỗi ô bấm được.
* Lưới `TheKenhLon` — mỗi kênh một thẻ lớn (câu tình trạng, video kế tiếp, ba
  video gần nhất kèm mũi tên so cùng mốc tuổi, "máy đang học"), rồi dòng
  "Kênh khác đang tắt: … ▸" cho các kênh không tự chạy và không do máy đăng
  quản (quyết định 5 — TL4-T7-v2 gom vào đây, TL4-T7 tự chạy=false nhưng máy
  đăng vẫn quản thì có thẻ riêng, đánh dấu "(đang tắt)").

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
    QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu,
    QMessageBox, QVBoxLayout, QWidget,
)

from core import bang_dieu_khien as bdk
from core import trung_tam as tt
from core.money import format_vnd

from . import theme
from .trang_dieu_khien import HopCaiDatKenh, HopNhatKyKenh
from .trang_trung_tam import GIAY_HOI_LICH, GIAY_HOI_VI, HopDuyet, _cat, _giam_sat, _gon, _pt
from .widgets import HangXuongDong, HopXuongDong, gio_hhmm, mo_thu_muc, nhan, nut_phu

__all__ = ["TrangBangDieuKhien", "KhoiViec", "DongMay", "TheKenhLon"]

#: CLAUDE.md luật 4 — đọc lại tệp mỗi 30 giây, không hỏi máy chủ dày hơn.
NHIP_LAM_MOI_MS = 30_000
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
        self._nhan_tieu.setText("VIỆC CỦA BẠN · {0}".format(len(danh_sach))
                                if danh_sach else "VIỆC CỦA BẠN")
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


class TheKenhLon(QFrame):
    """Một kênh = một thẻ lớn: câu tình trạng, video kế tiếp, ba video gần
    đây kèm mũi tên, "máy đang học", bốn nút."""

    #: Bề rộng tối thiểu hợp lý — KHÔNG `setFixedWidth`: lưới 2 cột co giãn
    #: theo cửa sổ (`_LuoiThe`), ép cứng bề rộng ở đây sẽ làm cửa sổ hẹp tràn.
    RONG_TOI_THIEU = 420

    def __init__(self, ma: str, on_cong_tac: Callable[[str, str, bool], None],
                on_hanh_dong: Callable[[str, str], None], cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._ma = ma
        self._muc = bdk.TOT
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
        v.addLayout(hang_ten)

        hang_ct = QHBoxLayout()
        hang_ct.setContentsMargins(0, 0, 0, 0)
        self._o_tu_chay = QCheckBox("Tự làm video")
        self._o_tu_chay.toggled.connect(
            lambda bat: self._bao_cong_tac("tu_chay", bat))
        hang_ct.addWidget(self._o_tu_chay)
        hang_ct.addStretch(1)
        v.addLayout(hang_ct)
        hang_ct2 = QHBoxLayout()
        hang_ct2.setContentsMargins(0, 0, 0, 0)
        self._o_tu_duyet = QCheckBox("Tự lên lịch")
        self._o_tu_duyet.setToolTip(
            "Bật: video làm xong tự hẹn giờ và lên sóng, không chờ bạn xem trước.\n"
            "Tắt: video nằm chờ bạn bấm “Hẹn giờ” ở khối Việc của bạn.")
        self._o_tu_duyet.toggled.connect(
            lambda bat: self._bao_cong_tac("tu_duyet", bat))
        hang_ct2.addWidget(self._o_tu_duyet)
        hang_ct2.addStretch(1)
        v.addLayout(hang_ct2)

        self._nhan_trang_thai = QLabel("")
        self._nhan_trang_thai.setWordWrap(True)
        self._nhan_trang_thai.setMinimumWidth(1)
        v.addWidget(self._nhan_trang_thai)

        self._nhan_khau = QLabel("")
        self._nhan_khau.setWordWrap(True)
        self._nhan_khau.setMinimumWidth(1)
        self._nhan_khau.setStyleSheet("color:{0};font-size:11px;".format(theme.CHU_MO))
        self._nhan_khau.setVisible(False)
        v.addWidget(self._nhan_khau)

        self._nhan_ke_tiep = QLabel("Video kế tiếp  —")
        self._nhan_ke_tiep.setWordWrap(True)
        self._nhan_ke_tiep.setMinimumWidth(1)
        self._nhan_ke_tiep.setStyleSheet("font-size:12px;")
        v.addWidget(self._nhan_ke_tiep)

        self._nhan_len_song = QLabel("Lên sóng       chưa hẹn giờ")
        self._nhan_len_song.setWordWrap(False)
        self._nhan_len_song.setStyleSheet("color:{0};font-size:12px;".format(theme.CHU_MO))
        v.addWidget(self._nhan_len_song)

        self._luoi_gan_day = QGridLayout()
        self._luoi_gan_day.setContentsMargins(0, 4, 0, 4)
        self._luoi_gan_day.setHorizontalSpacing(8)
        self._luoi_gan_day.setVerticalSpacing(2)
        for c, ten in enumerate(("Gần đây", "Tuổi", "Lượt xem", "Tỷ lệ bấm", "Giữ chân")):
            nh = QLabel(ten)
            nh.setStyleSheet("color:{0};font-size:11px;font-weight:600;".format(theme.CHU_MO))
            if ten == "Tỷ lệ bấm":
                nh.setToolTip("Tỷ lệ bấm (CTR) — số người bấm xem / số người thấy ảnh bìa.")
            self._luoi_gan_day.addWidget(nh, 0, c)
        self._luoi_gan_day.setColumnStretch(0, 1)
        self._hang_gan_day: List[List[QLabel]] = []
        for r in range(1, 4):
            hang: List[QLabel] = []
            for c in range(5):
                nh = QLabel("")
                nh.setStyleSheet("font-size:12px;")
                nh.setMinimumWidth(1)
                if c == 0:
                    nh.setWordWrap(False)
                self._luoi_gan_day.addWidget(nh, r, c)
                hang.append(nh)
            self._hang_gan_day.append(hang)
        v.addLayout(self._luoi_gan_day)

        self._nhan_hoc = QLabel("")
        self._nhan_hoc.setWordWrap(True)
        self._nhan_hoc.setMinimumWidth(1)
        self._nhan_hoc.setStyleSheet("color:{0};font-size:11px;".format(theme.CHU_MO))
        self._nhan_hoc.setVisible(False)
        v.addWidget(self._nhan_hoc)

        hang_nut = HangXuongDong(6)
        self._nut_xem = nut_phu("Xem video chờ đăng",
                                lambda: self._on_hanh_dong(self._ma, "xem_video"))
        hang_nut.addWidget(self._nut_xem)
        hang_nut.addWidget(nut_phu("Mở thư mục", lambda: self._on_hanh_dong(self._ma, "mo_thu_muc")))
        hang_nut.addWidget(nut_phu("Nhật ký", lambda: self._on_hanh_dong(self._ma, "nhat_ky")))
        hang_nut.addWidget(nut_phu("⚙ Cài kênh", lambda: self._on_hanh_dong(self._ma, "cai_kenh")))
        hop_nut = QWidget()
        hop_nut.setLayout(hang_nut)
        v.addWidget(hop_nut)

        self._ve_vien()

    def _bao_cong_tac(self, khoa: str, bat: bool) -> None:
        if not self._dang_nap:
            self._on_cong_tac(self._ma, khoa, bool(bat))

    def nap(self, k: Dict[str, Any]) -> None:
        self._dang_nap = True
        try:
            self._nap_that(k)
        finally:
            self._dang_nap = False

    def _nap_that(self, k: Dict[str, Any]) -> None:
        self._muc = bdk.muc_the(k)
        ma = str(k.get("ma") or "")
        # `ten` trong kenh.yaml có thể là "tên — mô tả dài" (dòng nhắc lời AI
        # đặt tên) — tiêu đề thẻ chỉ hiện phần TÊN, mô tả dồn vào tooltip
        # (chẩn đoán chủ dự án 29/09/2026: tiêu đề thẻ dài tràn cả hàng).
        ten_day_du = str(k.get("ten") or ma)
        ten_ngan = ten_day_du.split(" — ", 1)[0].strip() or ten_day_du
        day_du_hien = ma if ten_ngan == ma else "{0} · {1}".format(ma, ten_ngan)
        day_du_tip = ma if ten_day_du == ma else "{0} · {1}".format(ma, ten_day_du)
        _cat(self._nhan_ten, day_du_hien, 420)
        self._nhan_ten.setToolTip(day_du_tip)

        self._o_tu_chay.blockSignals(True)
        self._o_tu_chay.setChecked(bool(k.get("tu_chay")))
        self._o_tu_chay.blockSignals(False)
        self._o_tu_duyet.blockSignals(True)
        self._o_tu_duyet.setChecked(bool(k.get("tu_duyet")))
        self._o_tu_duyet.blockSignals(False)

        bay = k.get("bay_gio") or {}
        chu_mau, nen, vien = _MAU_THE.get(self._muc, _MAU_THE[bdk.TOT])
        dau = _DAU_THE.get(self._muc, "")
        # Câu NGƯỜI THƯỜNG đọc được (mục 3 "Viên trạng thái") — `bay_gio.chu`
        # là câu KIỂU CŨ (`core.trung_tam.trang_thai_bay_gio`), không phải
        # bảng câu mới ở đây. `cau_tinh_trang` (Việc 1) đã dịch nó.
        cau = bdk.cau_tinh_trang(k) or "—"
        if cau.startswith("Đã hẹn đăng"):
            dau = "⏱"  # khác dấu ✓ chung của mức TOT — mục 3 thiết kế.
        self._nhan_trang_thai.setText("{0} {1}".format(dau, cau).strip())
        self._nhan_trang_thai.setToolTip(bay.get("chi_tiet") or cau)
        self._nhan_trang_thai.setStyleSheet(
            "QLabel{{background:{0};border:1px solid {1};border-radius:8px;"
            "padding:5px 9px;color:{2};font-size:13px;font-weight:700;}}".format(
                nen, vien, chu_mau))

        chu_khau = _dong_khau(k)
        self._nhan_khau.setText(chu_khau)
        self._nhan_khau.setVisible(bool(chu_khau))

        vkt = k.get("video_ke_tiep") or {}
        td = str(vkt.get("tieu_de") or "")
        if td:
            chu_ke_tiep = "Video kế tiếp  「{0}」".format(td)
        else:
            tu = str(k.get("video_ke_tiep_tu") or "")
            chu_ke_tiep = ("Video kế tiếp  — chưa có — máy làm video mới từ {0}".format(tu)
                          if tu else "Video kế tiếp  — chưa có")
        self._nhan_ke_tiep.setText(chu_ke_tiep)
        self._nhan_ke_tiep.setToolTip(td)

        luc = str(k.get("dang_luc") or "")
        self._nhan_len_song.setText("Lên sóng       " + (luc if luc else "chưa hẹn giờ"))

        gan_day = list(k.get("video_gan_day") or [])
        for r, hang in enumerate(self._hang_gan_day):
            if r < len(gan_day):
                d = gan_day[r]
                _cat(hang[0], str(d.get("tieu_de") or ""), 160)
                hang[0].setToolTip(str(d.get("tieu_de") or ""))
                hang[1].setText(str(d.get("tuoi") or "—"))
                lx = d.get("luot_xem")
                hang[2].setText(_gon(lx) if lx is not None else "—")
                ctr = d.get("ty_le_bam")
                mui_ten = _MUI_TEN.get(str(d.get("mui_ten") or ""), "")
                mau_mui = _MAU_MUI_TEN.get(str(d.get("mui_ten") or ""), theme.CHU)
                hang[3].setText(("{0} {1}".format(_pt(ctr), mui_ten)).strip()
                                if ctr is not None else "—")
                hang[3].setStyleSheet("font-size:12px;color:{0};".format(
                    mau_mui if mui_ten else theme.CHU))
                gc = d.get("giu_chan")
                hang[4].setText(_pt(gc) if gc is not None else "—")
                for lb in hang:
                    lb.setVisible(True)
            else:
                for lb in hang:
                    lb.setText("")
        any_gan_day = bool(gan_day)
        for c in range(5):
            self._luoi_gan_day.itemAtPosition(0, c).widget().setVisible(any_gan_day)

        hoc = str(k.get("may_dang_hoc") or "")
        self._nhan_hoc.setText(hoc)
        self._nhan_hoc.setVisible(bool(hoc))

        self._nut_xem.setEnabled(bool(vkt))
        self._nut_xem.setToolTip("" if vkt else "Chưa có video chờ đăng")
        self._ve_vien()

    def _ve_vien(self) -> None:
        _chu, nen, vien = _MAU_THE.get(self._muc, _MAU_THE[bdk.TOT])
        self.setStyleSheet(
            "QFrame#theKenhLon{{background:{0};border:1px solid {1};border-radius:12px;}}"
            .format(theme.THE if self._muc == bdk.TOT else nen,
                    theme.VIEN if self._muc == bdk.TOT else vien))


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

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(8)
        doc.addWidget(self._hang_tieu_de())
        self._khoi_viec = KhoiViec(self._hanh_dong)
        doc.addWidget(self._khoi_viec)
        self._dong_may = DongMay(self._hanh_dong)
        doc.addWidget(self._dong_may)
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
        tieu = nhan("Bảng điều khiển", "h1")
        tieu.setWordWrap(False)
        ngang.addWidget(tieu)
        self._nhan_luc = nhan("", "muted")
        self._nhan_luc.setMinimumWidth(1)
        ngang.addWidget(self._nhan_luc, 1)
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

    def _the_cong_tac(self, ma: str, khoa: str, bat: bool) -> None:
        if khoa == "tu_duyet" and bat:
            hoi = QMessageBox.question(
                self, "Tự lên lịch",
                "Video làm xong sẽ tự hẹn giờ và lên sóng, không chờ bạn xem "
                "trước. Bật?")
            if hoi != QMessageBox.Yes:
                the = self._the_kenh.get(ma)
                k = self._kenh(ma)
                if the is not None and k is not None:
                    the.nap(k)
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

    def lam_moi(self, bat_buoc: bool = True) -> None:
        if not self._con_song() or (not bat_buoc and not self.isVisible()):
            return
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
            return bang, may, win

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
        bang, may, win = ket
        self._bang = bang
        self._may = may
        if win is not None:
            self._windows_canh_bao = win
            self._windows_luc = time.monotonic()
        self._nhan_luc.setText(self._chu_luc())
        self._ve_viec()
        self._ve_may()
        self._ve_the(list(bang.get("kenh") or []))
        self._ve_kenh_khac()
        self._hoi_vi()

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
        for k in kenh:
            ma = k["ma"]
            t = self._the_kenh.get(ma)
            if t is None:
                t = TheKenhLon(ma, self._the_cong_tac, self._the_hanh_dong, self._luoi)
                self._the_kenh[ma] = t
                self._luoi.them(ma, t)
            t.nap(k)
        self._luoi.dat_thu_tu([k["ma"] for k in kenh])

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
