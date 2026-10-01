"""Tab **Quản lý kênh** — tab 4, chốt cuối của nhóm AUTOMATION.

Chủ dự án, 31/08/2026: *"TAB 4 - QUẢN LÝ KÊNH"*, trong bức tranh kênh tự chạy
(agent đọc chỉ số, agent sản xuất theo tín hiệu, agent làm khán giả).

═══ TRANG NÀY CÓ GÌ, VÀ VÌ SAO CHỈ CÓ THẾ ═══

Trình thiết kế kênh (`HopKenh` trong `ui_qt/kenh.py`) vốn là HỘP THOẠI mở từ
một nút nhỏ trong tab Tự động — khách phải biết trước là nó nằm đó. Trang này
cho kênh một cửa chính: danh sách mọi kênh trong `CHANNEL/`, bấm vào là mở
đúng hộp thoại ấy. **Không chép lại trình thiết kế** — một bộ mã hai cửa vào,
sửa một chỗ là cả hai cùng được.

Phần agent tự chạy CHƯA có ở đây — nói thật trên màn hình thay vì vẽ nút chưa
chạy được. Khi từng mảnh xong (đọc chỉ số → đánh giá → lệnh sản xuất), chúng
mọc vào trang này.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QSpinBox, QTimeEdit,
    QVBoxLayout, QWidget,
)

from core.kenh import TEP_KENH, doc_kenh, duong_kenh, liet_ke_kenh
from core.money import MICRO_PER_VND, format_vnd

from . import theme
from .widgets import (ChonThuMuc, HangXuongDong, gio_hhmm, lan_chay_gon,
                      mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang)

__all__ = ["TrangQuanLyKenh", "TheTuChay", "HopTaoKenhTrongNhom", "TEP_KHAN_GIA"]

#: Năm tệp khán giả — nguồn duy nhất ở `core.trung_tam` (thẻ này, hộp tạo kênh và
#: trang Trung tâm cùng đọc một danh sách).
from core.trung_tam import TEP_KHAN_GIA  # noqa: E402
from core.trung_tam import _so_tep as _so_tep_gui  # noqa: E402 — mã tệp từ slug


def dien_o_tep(o: QComboBox, goc: str, nhom: str) -> None:
    """Điền ô chọn tệp khán giả theo hồ sơ ngách của NHÓM (`trung_tam.tep_khan_gia_cho_nhom`).

    01/10/2026: trước đây mọi ô chọn tệp đọc thẳng năm tệp tâm lý Nhật (`TEP_KHAN_GIA`) — kênh ngách
    khác không chọn được tệp của chính ngách mình. Nhóm trống/không có hồ sơ → năm tệp cũ. Giữ lựa
    chọn đang có nếu còn trong danh sách; không phát tín hiệu (không kích tự lưu)."""
    from core.trung_tam import tep_khan_gia_cho_nhom  # noqa: PLC0415

    dang = o.currentData()
    o.blockSignals(True)
    try:
        o.clear()
        o.addItem("(chưa chọn)", "")
        try:
            bang = tep_khan_gia_cho_nhom(goc, nhom)
        except Exception:  # noqa: BLE001 — hồ sơ hỏng: năm tệp cũ, không vỡ hộp thoại
            bang = tuple((m, t, t) for m, t in TEP_KHAN_GIA)
        for ma_tep, ten_tep, _ngan in bang:
            o.addItem("{0} — {1}".format(ma_tep, ten_tep), ma_tep)
        i = o.findData(dang) if dang else -1
        o.setCurrentIndex(i if i >= 0 else 0)
    finally:
        o.blockSignals(False)


def _ghi_khoa_tu_chay(goc: str, ma: str, **khoa: Any) -> None:
    """Ghi một loạt khoá vào `kenh.yaml` của kênh `ma` — autosave của thẻ Tự chạy.

    Thân hàm dời sang `core.trung_tam.ghi_cai_kenh` (18/09/2026) để trang
    Trung tâm và thuật sĩ "Thêm kênh" ghi CÙNG một đường, không chép hai bản.
    """
    from core.trung_tam import ghi_cai_kenh  # noqa: PLC0415

    ghi_cai_kenh(goc, ma, **khoa)


class HopTaoKenhTrongNhom(QDialog):
    """Chép một kênh có sẵn thành kênh mới CÙNG NHÓM, đánh TỆP khán giả khác.

    Bọc `core.nhom_kenh.tao_kenh_trong_nhom` — hàm đã lo chép prompt/style/
    ảnh nhân vật, gỡ cờ mẫu, bật `kenh_rieng`, và dọn kênh mới về đúng danh
    sách trắng (không mang phán quyết riêng của kênh gốc về tệp CỦA KÊNH GỐC).
    """

    def __init__(self, app, ma_goc: str = "", cha=None):
        super().__init__(cha)
        self.setWindowTitle("Tạo kênh trong nhóm")
        self._app = app
        self.ma_kenh_moi = ""

        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.addWidget(nhan(
            "Chép một kênh có sẵn thành kênh mới CÙNG NHÓM — kênh mới đánh "
            "một TỆP khán giả khác, mang theo dữ liệu ngách còn thô (đối "
            "thủ, trang chủ), KHÔNG mang phán quyết riêng của kênh gốc. Số "
            "liệu và lịch đăng của kênh mới bắt đầu trắng.", "muted"))

        v.addWidget(nhan("Kênh gốc (chép từ):"))
        self._o_goc = QComboBox()
        for ma in liet_ke_kenh(app.base_dir):
            self._o_goc.addItem(ma, ma)
        i = self._o_goc.findData((ma_goc or "").strip())
        if i >= 0:
            self._o_goc.setCurrentIndex(i)
        v.addWidget(self._o_goc)

        v.addWidget(nhan("Mã kênh mới:"))
        self._o_ma = QLineEdit()
        self._o_ma.setPlaceholderText("ví dụ TL4-T8")
        v.addWidget(self._o_ma)

        v.addWidget(nhan("Tên kênh mới:"))
        self._o_ten = QLineEdit()
        v.addWidget(self._o_ten)

        v.addWidget(nhan("Nhóm kênh:"))
        self._o_nhom = QComboBox()
        self._o_nhom.setEditable(True)
        for n in _danh_sach_nhom(app.base_dir):
            self._o_nhom.addItem(n)
        v.addWidget(self._o_nhom)

        v.addWidget(nhan("Tệp khán giả:"))
        self._o_tep = QComboBox()
        dien_o_tep(self._o_tep, app.base_dir, self._o_nhom.currentText().strip())
        self._o_nhom.currentTextChanged.connect(
            lambda t: dien_o_tep(self._o_tep, app.base_dir, str(t or "").strip()))
        v.addWidget(self._o_tep)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Tạo kênh", self._tao, rong=140))
        hang.addWidget(nut_phu("Huỷ", self.reject, rong=90))
        v.addLayout(hang)

    def _tao(self) -> None:
        from core.nhom_kenh import tao_kenh_trong_nhom  # noqa: PLC0415

        ma_goc = (self._o_goc.currentData() or self._o_goc.currentText()).strip()
        ma_moi = self._o_ma.text().strip()
        if not ma_goc:
            self._app.show_message("Chưa chọn kênh gốc", "Chọn kênh muốn chép trước.")
            return
        if not ma_moi:
            self._app.show_message("Chưa đặt mã kênh mới",
                                   "Gõ mã cho kênh mới, ví dụ TL4-T8.")
            return
        try:
            tao_kenh_trong_nhom(
                self._app.base_dir, ma_goc, ma_moi, self._o_ten.text().strip(),
                self._o_nhom.currentText().strip(), self._o_tep.currentData() or "")
        except Exception as loi:  # noqa: BLE001 — báo lỗi tiếng Việt, không văng
            self._app.show_error(loi)
            return
        self.ma_kenh_moi = ma_moi
        self.accept()


#: Tên khoá trong tệp → chữ người thường đọc. `core.nhom_kenh.kiem_trung_lap`
#: trả câu tiếng Việt nhưng có kèm tên khoá kỹ thuật trong ngoặc
#: ("Cùng giọng đọc (voice_id b34Jyl…)") — câu ấy viết cho người đọc NHẬT KÝ.
#: Đưa thẳng lên màn hình là phạm luật "không dùng từ kỹ thuật trên giao diện"
#: của `MyTool/CLAUDE.md`, nên dịch nốt mấy chữ ấy ở đây thay vì sửa lõi (lõi
#: còn được `core/tu_chay.py` gọi để ghi vào báo cáo).
_TEN_KHOA_TIENG_VIET = (
    ("voice_id", "mã giọng"),
    ("style_name", "tên bộ vẽ"),
    ("thumb_text_hex", "màu chữ bìa"),
    ("nv/nv1.png", "ảnh nhân vật"),
)


def _bo_ten_khoa(chu: str) -> str:
    chu = str(chu or "")
    for khoa, tieng_viet in _TEN_KHOA_TIENG_VIET:
        chu = chu.replace(khoa, tieng_viet)
    return chu


def _danh_sach_nhom(goc: str) -> list:
    """Mọi tên nhóm đang có, theo bảng chữ cái — cho ô "Nhóm kênh" gợi ý."""
    nhoms = set()
    for ma in liet_ke_kenh(goc):
        nhom = doc_kenh(goc, ma).nhom
        if nhom:
            nhoms.add(nhom)
    return sorted(nhoms)


class TheTuChay(QFrame):
    """Thẻ điều khiển kênh TỰ CHẠY — sản xuất không người trông.

    Đọc/ghi thẳng `kenh.yaml` của kênh mà `lay_ma()` trả về. Hai nơi dùng
    chung ĐÚNG một thẻ này (18/09/2026): tab Quản lý kênh (kênh đang bôi đen
    trong danh sách) và trang Trung tâm (kênh đang chọn trên bảng) — một bộ
    mã hai cửa vào, sửa một chỗ là cả hai cùng được.

    `co_lich=False` giấu phần "Lịch hằng ngày" — trang Trung tâm đã có lịch ở
    dải trên cùng, lặp lại ở đây là hai nút cùng làm một việc.
    """

    def __init__(self, app, lay_ma: Callable[[], str], *, co_lich: bool = True,
                 on_luu: Optional[Callable[[], None]] = None):
        super().__init__()
        self.setObjectName("card")
        theme.bong(self)
        self._app = app
        self._lay_ma = lay_ma
        self._co_lich = co_lich
        self._on_luu = on_luu
        self._dung()

    def _dung(self) -> None:
        """Thẻ điều khiển kênh TỰ CHẠY — sản xuất không người trông.

        Đọc/ghi thẳng `kenh.yaml` của kênh đang bôi đen ở danh sách trên,
        không có ô chọn kênh riêng — một chỗ chọn kênh cho cả trang.
        """
        khung = self
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)

        tieu = QHBoxLayout()
        tieu.setContentsMargins(0, 0, 0, 0)
        tieu.addWidget(nhan("Tự chạy theo lịch", "h2"))
        tieu.addStretch(1)
        from .huong_dan import nut_huong_dan  # noqa: PLC0415

        nut_hd = nut_huong_dan("tu-chay-kenh", khung)
        if nut_hd is not None:
            tieu.addWidget(nut_hd)
        v.addLayout(tieu)

        self._o_tu_chay = QCheckBox("Cho kênh này tự chạy")
        self._o_tu_chay.setToolTip(
            "Bật thì kênh này tự cập nhật số liệu và sản xuất khi gần lịch đăng, "
            "không cần bạn ngồi bấm. Tắt (mặc định) thì kênh vẫn chạy tay "
            "như trước, không việc gì đổi.")
        self._o_tu_chay.toggled.connect(lambda _b: self._tu_luu_tu_chay())
        v.addWidget(self._o_tu_chay)

        hang_ns = HangXuongDong()
        # `HangXuongDong` (không phải `QHBoxLayout` trần) ở MỌI hàng nhiều ô
        # dưới đây — `QHBoxLayout` cộng dồn bề rộng tối thiểu của mọi ô lại
        # với nhau và không bao giờ co xuống nữa (đúng lỗi `test_bo_cuc.py`
        # bắt được: nhãn + hai ô chọn dài đẩy cả trang cần 992px). Hàng chip
        # tự xuống dòng thì bề rộng tối thiểu chỉ còn bằng MỘT ô rộng nhất.
        hang_ns.addWidget(nhan("Trần tiền mỗi ngày:"))
        self._o_ngan_sach = QSpinBox()
        self._o_ngan_sach.setRange(0, 50_000_000)
        self._o_ngan_sach.setSingleStep(10_000)
        self._o_ngan_sach.setGroupSeparatorShown(True)
        self._o_ngan_sach.setSuffix(" ₫")
        # Việt Nam ngăn nhóm bằng dấu CHẤM (5.000.000); Qt lấy dấu theo "vùng"
        # của tiến trình, mà tiến trình chạy ở vùng C (dấu phẩy).
        from PyQt5.QtCore import QLocale  # noqa: PLC0415

        self._o_ngan_sach.setLocale(QLocale(QLocale.Vietnamese, QLocale.Vietnam))
        self._o_ngan_sach.setToolTip(
            "Số tiền tối đa kênh này được tiêu MỖI NGÀY khi tự chạy. "
            "KHÔNG ĐẶT TRẦN (để 0₫) thì tool KHÔNG tự sản xuất — chạy không "
            "người trông mà không có trần là tiêu tiền không giới hạn.")
        self._o_ngan_sach.valueChanged.connect(self._doi_ngan_sach)
        hang_ns.addWidget(self._o_ngan_sach)
        v.addLayout(hang_ns)
        self._nhan_ngan_sach = nhan("", "muted")
        v.addWidget(self._nhan_ngan_sach)
        nh_0 = nhan(
            "Để 0₫ KHÔNG phải là “bỏ trần” — nó nghĩa là KHÔNG SẢN XUẤT GÌ CẢ. "
            "Muốn không giới hạn thì đặt một con số rất cao.", "muted")
        nh_0.setMinimumWidth(1)
        v.addWidget(nh_0)

        hang_td = HangXuongDong()
        self._o_tu_duyet = QCheckBox("Tự đăng, không chờ duyệt")
        self._o_tu_duyet.setToolTip(
            "Bật thì tool tự điền giờ đăng vào kế hoạch ngay sau khi sản "
            "xuất xong — máy ảo đăng đúng giờ đó, KHÔNG CÓ AI DUYỆT LẠI bản "
            "trước khi lên sóng. Tắt (mặc định) thì bạn tự gõ giờ đăng khi "
            "đã ưng bản — van an toàn cho người mới bật tự chạy.")
        self._o_tu_duyet.toggled.connect(self._doi_tu_duyet)
        hang_td.addWidget(self._o_tu_duyet)
        hang_td.addWidget(nhan("Giờ đăng:"))
        self._o_gio_dang = QTimeEdit(QTime(20, 0))
        self._o_gio_dang.setDisplayFormat("HH:mm")
        self._o_gio_dang.timeChanged.connect(lambda _t: self._tu_luu_tu_chay())
        hang_td.addWidget(self._o_gio_dang)
        hang_td.addWidget(nhan("Đăng mỗi:"))
        self._o_chu_ky_dang = QSpinBox()
        self._o_chu_ky_dang.setRange(1, 30)
        self._o_chu_ky_dang.setValue(2)
        self._o_chu_ky_dang.setSuffix(" ngày")
        self._o_chu_ky_dang.setToolTip("Khoảng cách giữa hai video đã đăng.")
        self._o_chu_ky_dang.valueChanged.connect(lambda _v: self._tu_luu_tu_chay())
        hang_td.addWidget(self._o_chu_ky_dang)
        hang_td.addWidget(nhan("Chốt nội dung trước:"))
        self._o_san_xuat_truoc = QSpinBox()
        self._o_san_xuat_truoc.setRange(1, 168)
        self._o_san_xuat_truoc.setValue(24)
        self._o_san_xuat_truoc.setSuffix(" giờ")
        self._o_san_xuat_truoc.setToolTip(
            "Chỉ tới gần lịch đăng chừng này giờ tool mới cập nhật số liệu, "
            "chạy V7 và chọn nội dung mới.")
        self._o_san_xuat_truoc.valueChanged.connect(lambda _v: self._tu_luu_tu_chay())
        hang_td.addWidget(self._o_san_xuat_truoc)
        v.addLayout(hang_td)

        self._o_thu_muc_done = ChonThuMuc(
            "", "Thư mục bàn giao:", on_doi=lambda _d: self._tu_luu_tu_chay())
        self._o_thu_muc_done.setToolTip(
            "Sản xuất xong, tool chép gói mp4 + phụ đề + ảnh bìa vào đây để "
            "máy ảo lấy đăng. Để trống thì sản xuất xong KHÔNG bàn giao đi "
            "đâu — tool nói rõ trong báo cáo chứ không âm thầm bỏ qua.")
        v.addWidget(self._o_thu_muc_done)

        hang_nhom = HangXuongDong()
        hang_nhom.addWidget(nhan("Nhóm kênh:"))
        self._o_nhom = QComboBox()
        self._o_nhom.setEditable(True)
        self._o_nhom.setMinimumWidth(140)
        self._o_nhom.setToolTip(
            "Kênh cùng nhóm chia sẻ sổ đối thủ và không remake trùng nguồn "
            "của nhau. Để trống thì kênh đứng một mình.")
        self._o_nhom.editTextChanged.connect(lambda _t: self._tu_luu_tu_chay())
        hang_nhom.addWidget(self._o_nhom)
        hang_nhom.addWidget(nhan("Tệp khán giả:"))
        self._o_tep = QComboBox()
        dien_o_tep(self._o_tep, self._app.base_dir, "")
        self._o_tep.currentIndexChanged.connect(lambda _i: self._tu_luu_tu_chay())
        hang_nhom.addWidget(self._o_tep)
        v.addLayout(hang_nhom)

        # ── Ngày kênh bắt đầu làm nội dung ──────────────────────────────────
        #
        # Bốn kênh thật đều là kênh YouTube CÓ SẴN đổi ngách, nên trên kênh còn
        # video của đời trước và mắt cào Studio cào tuốt. Ô này là chỗ khai ranh
        # giới — xem `core/chi_so_ytb/loc_video.py`. Để trống (mặc định) thì
        # không lọc gì, y như trước.
        hang_moc = HangXuongDong()
        hang_moc.addWidget(nhan("Ngày bắt đầu làm nội dung:"))
        self._o_ngay_bat_dau = QLineEdit()
        self._o_ngay_bat_dau.setFixedWidth(124)
        self._o_ngay_bat_dau.setPlaceholderText("2026-08-22")
        self._o_ngay_bat_dau.setToolTip(
            "Ngày kênh này bắt đầu làm nội dung bằng tool. Video đăng TRƯỚC "
            "ngày này KHÔNG được tính vào số liệu và vòng học — kênh đổi ngách "
            "thì video của đời trước không nói gì về nội dung bây giờ, mà một "
            "video cũ nhiều lượt hiển thị lại bị chấm là “video thắng” và kéo "
            "cả khuôn tiêu đề theo nó.\n\n"
            "Gõ dạng NĂM-THÁNG-NGÀY, ví dụ 2026-08-22. Để trống thì tính hết "
            "mọi video trên kênh. Số liệu cũ KHÔNG bị xoá, chỉ không được tính.")
        self._o_ngay_bat_dau.editingFinished.connect(self._luu_ngay_bat_dau)
        hang_moc.addWidget(self._o_ngay_bat_dau)
        v.addLayout(hang_moc)
        self._nhan_ngay_bat_dau = nhan("", "muted")
        self._nhan_ngay_bat_dau.setMinimumWidth(1)
        v.addWidget(self._nhan_ngay_bat_dau)

        # ── Công tắc của MÁY ẢO (may-ao.json, không phải kenh.yaml) ─────────
        #
        # Trạm đính kèm tệp này vào phản hồi mỗi lượt agent hỏi việc, nên gạt ở
        # đây là máy ảo nhận trong một nhịp tim (≤30 giây) — không phải mở
        # Remote Desktop sửa config tay. Xem `core/vm_cai_dat.py`.
        hang_vm = HangXuongDong()
        self._o_tu_dang = QCheckBox("Máy tự đăng")
        self._o_tu_dang.setToolTip(
            "Cho máy tự đưa video của kênh này lên YouTube trong phiên hằng "
            "ngày. Tắt thì video vẫn được làm và bàn giao, chỉ không ai đăng.")
        self._o_tu_dang.toggled.connect(lambda _b: self._luu_may_ao())
        hang_vm.addWidget(self._o_tu_dang)
        self._o_tu_cmt = QCheckBox("Trả lời bình luận")
        self._o_tu_cmt.setToolTip(
            "Cho máy tự trả lời bình luận dưới video của kênh này.")
        self._o_tu_cmt.toggled.connect(lambda _b: self._luu_may_ao())
        hang_vm.addWidget(self._o_tu_cmt)
        v.addLayout(hang_vm)

        # ── Dọn đĩa ─────────────────────────────────────────────────────────
        hang_don = HangXuongDong()
        self._o_tu_don = QCheckBox("Tự dọn sau khi đăng")
        self._o_tu_don.setToolTip(
            "Video đã lên sóng thì xoá phần nặng của lượt (ảnh, clip, bản dựng, "
            "giọng đọc). Kịch bản, phụ đề, bảng cảnh và ảnh bìa đã chọn thì GIỮ.")
        self._o_tu_don.toggled.connect(lambda _b: self._tu_luu_tu_chay())
        hang_don.addWidget(self._o_tu_don)
        hang_don.addWidget(nhan("chờ"))
        self._o_don_sau = QSpinBox()
        self._o_don_sau.setRange(0, 336)
        self._o_don_sau.setValue(24)
        self._o_don_sau.setSuffix(" giờ")
        self._o_don_sau.setToolTip(
            "Chờ chừng này giờ sau khi video lên sóng rồi mới xoá — chừa chỗ "
            "cho ca YouTube xử lý hỏng phải tải lại.")
        self._o_don_sau.valueChanged.connect(lambda _v: self._tu_luu_tu_chay())
        hang_don.addWidget(self._o_don_sau)
        v.addLayout(hang_don)

        # ── Giọng đọc ───────────────────────────────────────────────────────
        hang_voice = HangXuongDong()
        hang_voice.addWidget(nhan("Giọng đọc:"))
        self._o_voice = QLineEdit()
        self._o_voice.setMinimumWidth(190)
        self._o_voice.setPlaceholderText("mã giọng (Voice ID)")
        # Tên nhà cung cấp giọng nói KHÔNG được có trong bản giao khách — xem
        # `tests/test_khong_lo_bi_mat.py`. Câu chữ ở đây chép đúng cách nói đã
        # duyệt của trình thiết kế kênh (`ui_qt/kenh.py`, bước Giọng đọc).
        self._o_voice.setToolTip(
            "Mỗi kênh một giọng riêng. Chưa có mã? Mở Thư viện giọng của nhà "
            "cung cấp, nghe thử, chọn một giọng rồi bấm “Use” — mã hiện ra "
            "(Voice ID) dán vào ô này.")
        self._o_voice.editingFinished.connect(self._tu_luu_tu_chay)
        hang_voice.addWidget(self._o_voice)
        v.addLayout(hang_voice)
        nh_voice = nhan(
            "Chưa có mã giọng? Mở Thư viện giọng của nhà cung cấp, nghe thử, "
            "chọn một giọng rồi bấm “Use” — mã hiện ra (Voice ID) dán vào ô "
            "trên. Mỗi kênh trong cùng một nhóm phải một giọng khác nhau.",
            "muted")
        nh_voice.setMinimumWidth(1)
        v.addWidget(nh_voice)
        self._nhan_trung = nhan("")
        self._nhan_trung.setMinimumWidth(1)
        self._nhan_trung.setStyleSheet("color:{0};".format(theme.CAM))
        v.addWidget(self._nhan_trung)

        # ── Kịch bản ────────────────────────────────────────────────────────
        hang_kb = HangXuongDong()
        hang_kb.addWidget(nhan("Dài mục tiêu:"))
        self._o_phut = QSpinBox()
        self._o_phut.setRange(3, 60)
        self._o_phut.setValue(15)
        self._o_phut.setSuffix(" phút")
        self._o_phut.setToolTip("Độ dài video nhắm tới. Tool nắn kịch bản về mốc này.")
        self._o_phut.valueChanged.connect(lambda _v: self._tu_luu_tu_chay())
        hang_kb.addWidget(self._o_phut)
        hang_kb.addWidget(nhan("Nhãn tiêu đề:"))
        self._o_nhan_tieu_de = QLineEdit()
        self._o_nhan_tieu_de.setMinimumWidth(90)
        self._o_nhan_tieu_de.setPlaceholderText("ví dụ 雑学")
        self._o_nhan_tieu_de.setToolTip(
            "Mấy chữ gắn ở ĐẦU mọi tiêu đề của kênh. Để trống thì không gắn gì.")
        self._o_nhan_tieu_de.editingFinished.connect(self._tu_luu_tu_chay)
        hang_kb.addWidget(self._o_nhan_tieu_de)
        hang_kb.addWidget(nhan("Viết:"))
        self._o_so_ban = QSpinBox()
        self._o_so_ban.setRange(1, 6)
        self._o_so_ban.setValue(1)
        self._o_so_ban.setSuffix(" bản")
        self._o_so_ban.setToolTip(
            "Viết mấy bản rồi chấm chọn một. Mỗi bản là một lượt gọi — kênh đi "
            "ví thì để 1, kênh đi thuê bao để 3.")
        self._o_so_ban.valueChanged.connect(lambda _v: self._tu_luu_tu_chay())
        hang_kb.addWidget(self._o_so_ban)
        v.addLayout(hang_kb)

        # ── Cách vẽ (style.yaml, không phải kenh.yaml) ──────────────────────
        hang_ve = HangXuongDong()
        hang_ve.addWidget(nhan("Bộ vẽ:"))
        self._o_bo_ve = QComboBox()
        self._o_bo_ve.setMinimumWidth(180)
        self._o_bo_ve.setToolTip(
            "Kênh nhìn ra sao: nét vẽ, màu, khoá giữ nhân vật, kiểu chữ ảnh bìa. "
            "Đổi bộ vẽ là ghi lại 16 khoá hình của kênh.")
        self._o_bo_ve.activated.connect(lambda _i: self._doi_bo_ve())
        hang_ve.addWidget(self._o_bo_ve)
        hang_ve.addWidget(nhan("Màu chữ bìa:"))
        self._o_mau = QLineEdit()
        self._o_mau.setFixedWidth(88)
        self._o_mau.setPlaceholderText("#0E7C86")
        self._o_mau.setToolTip("Màu khối chữ trên ảnh bìa, dạng #RRGGBB.")
        self._o_mau.editingFinished.connect(self._luu_mau_bia)
        hang_ve.addWidget(self._o_mau)
        hang_ve.addWidget(nut_phu("Chọn màu…", self._chon_mau_bia, rong=104))
        self._o_xem_mau = QLabel("     ")
        self._o_xem_mau.setFixedWidth(26)
        hang_ve.addWidget(self._o_xem_mau)
        v.addLayout(hang_ve)

        hang_thu = HangXuongDong()
        hang_thu.addWidget(nut_phu(
            "Chạy thử (không tốn tiền)", self._chay_thu, rong=220))
        v.addLayout(hang_thu)
        self._nhan_ket_qua_thu = nhan("", "muted")
        v.addWidget(self._nhan_ket_qua_thu)

        hop_lich = QWidget()
        v_lich = QVBoxLayout(hop_lich)
        v_lich.setContentsMargins(0, 0, 0, 0)
        v_lich.setSpacing(8)
        v_lich.addWidget(nhan(
            "Lịch chạy nền — áp dụng cho MỌI kênh đã tick “Cho kênh này tự "
            "chạy” ở trên, không riêng kênh đang chọn:", "muted"))
        self._nhan_lich = nhan("Lịch hằng ngày: đang kiểm tra…", "muted")
        v_lich.addWidget(self._nhan_lich)
        hang_lich = HangXuongDong()
        self._o_gio_lich = QTimeEdit(QTime(2, 0))
        self._o_gio_lich.setDisplayFormat("HH:mm")
        self._o_gio_lich.setToolTip(
            "Giờ máy sẽ tự chạy mọi kênh đã bật “tự chạy”. Máy phải đang "
            "bật và đã đăng nhập vào đúng giờ này thì lịch mới chạy được.")
        hang_lich.addWidget(self._o_gio_lich)
        self._nut_lich = nut_phu("Bật lịch", self._bat_tat_lich, rong=110)
        hang_lich.addWidget(self._nut_lich)
        v_lich.addLayout(hang_lich)
        v.addWidget(hop_lich)
        hop_lich.setVisible(self._co_lich)

        v.addWidget(nhan("7 ngày gần nhất của kênh đang chọn:", "h2"))
        self._ds_nhat_ky_tu_chay = QListWidget()
        self._ds_nhat_ky_tu_chay.setToolTip(
            "Chỉ để xem — sửa lượt chạy thì vào tab “Video sản xuất tự động”.")
        self._ds_nhat_ky_tu_chay.setMaximumHeight(140)
        v.addWidget(self._ds_nhat_ky_tu_chay)

    def _luu_ngay_bat_dau(self) -> None:
        """Gõ xong ngày bắt đầu → nói ngay hiểu đúng hay không, rồi mới lưu.

        Ô này là ô GÕ TAY duy nhất trong thẻ mà gõ sai thì hậu quả VÔ HÌNH: mốc
        không đọc được nghĩa là KHÔNG LỌC, tức số liệu rác âm thầm quay lại. Nên
        phải nói ra ngay dưới ô, đừng để người dùng tưởng đã cài xong.
        """
        chu = self._o_ngay_bat_dau.text().strip()
        self._cap_nhat_nhan_ngay_bat_dau(chu)
        self._tu_luu_tu_chay()

    def _cap_nhat_nhan_ngay_bat_dau(self, chu: str) -> None:
        from core.chi_so_ytb.loc_video import chuan_ngay  # noqa: PLC0415

        chu = str(chu or "").strip()
        if not chu:
            self._nhan_ngay_bat_dau.setText(
                "Để trống: tính mọi video trên kênh, kể cả video đăng trước "
                "khi kênh đổi sang nội dung này.")
            self._nhan_ngay_bat_dau.setStyleSheet("")
            return
        sach = chuan_ngay(chu)
        if not sach:
            self._nhan_ngay_bat_dau.setText(
                "Chưa đọc được ngày “{0}” — gõ dạng NĂM-THÁNG-NGÀY, ví dụ "
                "2026-08-22. Đang tính MỌI video cho tới khi sửa đúng."
                .format(chu[:20]))
            self._nhan_ngay_bat_dau.setStyleSheet("color:{0};".format(theme.CAM))
            return
        self._nhan_ngay_bat_dau.setText(
            "Chỉ tính video đăng từ {0} trở đi. Số liệu video cũ vẫn giữ trên "
            "đĩa, chỉ không được tính.".format(sach))
        self._nhan_ngay_bat_dau.setStyleSheet("")

    def _doi_ngan_sach(self, gia_tri: int) -> None:
        self._cap_nhat_nhan_ngan_sach(gia_tri)
        self._tu_luu_tu_chay()

    def _cap_nhat_nhan_ngan_sach(self, gia_tri: int) -> None:
        if gia_tri <= 0:
            self._nhan_ngan_sach.setText("chưa đặt trần — sẽ KHÔNG tự sản xuất")
        else:
            self._nhan_ngan_sach.setText(
                "≈ {0} / ngày".format(format_vnd(int(gia_tri) * MICRO_PER_VND)))

    def _doi_tu_duyet(self, bat: bool) -> None:
        self._tu_luu_tu_chay()

    def nap(self) -> None:
        """Nạp lại thẻ theo kênh đang bôi đen — gọi mỗi khi đổi kênh."""
        if not hasattr(self, "_o_bo_ve"):
            return  # thẻ chưa dựng xong (đang ở giữa __init__)
        ma = self._lay_ma()
        self._dang_nap_tu_chay = True
        try:
            for o in (self._o_tu_chay, self._o_ngan_sach, self._o_tu_duyet,
                     self._o_gio_dang, self._o_chu_ky_dang,
                     self._o_san_xuat_truoc, self._o_thu_muc_done, self._o_nhom,
                     self._o_tep, self._o_tu_dang, self._o_tu_cmt,
                     self._o_tu_don, self._o_don_sau, self._o_voice,
                     self._o_phut, self._o_nhan_tieu_de, self._o_so_ban,
                     self._o_ngay_bat_dau, self._o_bo_ve, self._o_mau):
                o.setEnabled(bool(ma))
            if not ma:
                self._ds_nhat_ky_tu_chay.clear()
                self._nhan_trung.setText("")
                return
            kenh = doc_kenh(self._app.base_dir, ma)
            self._o_tu_chay.setChecked(kenh.tu_chay)
            self._o_ngan_sach.setValue(int(kenh.ngan_sach_ngay))
            self._cap_nhat_nhan_ngan_sach(kenh.ngan_sach_ngay)
            self._o_tu_duyet.setChecked(kenh.tu_duyet)
            gio = QTime.fromString(kenh.gio_dang, "HH:mm") if kenh.gio_dang else QTime(20, 0)
            self._o_gio_dang.setTime(gio if gio.isValid() else QTime(20, 0))
            self._o_chu_ky_dang.setValue(max(1, int(kenh.chu_ky_dang_ngay or 1)))
            self._o_san_xuat_truoc.setValue(max(1, int(kenh.san_xuat_truoc_gio or 24)))
            self._o_thu_muc_done.dat_thang(kenh.thu_muc_done)
            self._nap_combo_nhom(kenh.nhom)
            dien_o_tep(self._o_tep, self._app.base_dir, kenh.nhom)
            self._nhan_ket_qua_thu.setText("")
            # ═══ ĐỪNG ĐÁNH RƠI TỆP KHÁN GIẢ ═══
            #
            # Bốn kênh thật trên VPS khai tệp bằng SLUG
            # (`tep: "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"`), còn ô chọn ở
            # đây lưu MÃ SỐ ("3"). `findData` trượt, ô rơi về "(chưa chọn)", và
            # cú tự lưu kế tiếp ghi `tep: ""` — kênh mất tệp khán giả mà không
            # ai bấm gì. Nhớ nguyên văn giá trị trong tệp và chỉ ghi đè khi
            # người dùng thật sự chọn một tệp KHÁC.
            self._tep_goc = str(kenh.tep or "")
            i_tep = self._o_tep.findData(_so_tep_gui(self._tep_goc))
            self._o_tep.setCurrentIndex(i_tep if i_tep >= 0 else 0)
            self._o_tu_don.setChecked(bool(kenh.tu_don))
            self._o_don_sau.setValue(int(kenh.don_sau_gio or 24))
            self._o_voice.setText(str(kenh.voice_id or ""))
            self._o_phut.setValue(max(3, min(60, int(round(kenh.phut_muc_tieu or 10)))))
            self._o_nhan_tieu_de.setText(str(kenh.nhan_tieu_de or ""))
            self._o_so_ban.setValue(max(1, min(6, int(kenh.so_ban_nhap or 1))))
            self._o_ngay_bat_dau.setText(str(kenh.ngay_bat_dau or ""))
            self._cap_nhat_nhan_ngay_bat_dau(str(kenh.ngay_bat_dau or ""))
            self._nap_may_ao(ma)
            self._nap_cach_ve(ma)
        finally:
            self._dang_nap_tu_chay = False
        self._nap_nhat_ky_tu_chay(ma)
        self._kiem_trung_giong(ma)
        if self._co_lich:
            self._cap_nhat_trang_thai_lich()

    # ── Máy ảo: hai công tắc nằm ở `may-ao.json`, không phải `kenh.yaml` ─────

    def _nap_may_ao(self, ma: str) -> None:
        from core import vm_cai_dat  # noqa: PLC0415

        try:
            cai = vm_cai_dat.doc(self._app.base_dir, ma)
        except Exception:  # noqa: BLE001 — thiếu tệp thì dùng mặc định
            cai = dict(vm_cai_dat.MAC_DINH)
        self._o_tu_dang.setChecked(bool(cai.get("tu_dang")))
        self._o_tu_cmt.setChecked(bool(cai.get("tu_tra_loi_cmt")))

    def _luu_may_ao(self) -> None:
        if getattr(self, "_dang_nap_tu_chay", False):
            return
        ma = self._lay_ma()
        if not ma:
            return
        from core import vm_cai_dat  # noqa: PLC0415

        try:
            vm_cai_dat.luu(self._app.base_dir, ma,
                           tu_dang=self._o_tu_dang.isChecked(),
                           tu_tra_loi_cmt=self._o_tu_cmt.isChecked())
        except Exception as loi:  # noqa: BLE001 — lưu hỏng phải nói, không văng
            self._app.show_error(loi)

    # ── Cách vẽ: 16 khoá hình nằm ở `style.yaml` ────────────────────────────

    def _nap_cach_ve(self, ma: str) -> None:
        """Điền ô "Bộ vẽ" và ô màu chữ bìa từ `style.yaml` của kênh.

        Danh sách bộ vẽ đọc từ `CHANNEL/_KHUON/ve/` qua `core.khuon.liet_ke_ve`
        — cùng một danh sách mà thuật sĩ tạo kênh dùng, không chép lại.
        """
        from core.dong_bo_kenh import doc_style  # noqa: PLC0415
        from core.khuon import liet_ke_ve  # noqa: PLC0415

        try:
            style = doc_style(self._app.base_dir, ma) or {}
        except Exception:  # noqa: BLE001
            style = {}
        dang = str(style.get("style_name") or "").strip()
        self._o_bo_ve.clear()
        self._o_bo_ve.addItem("(giữ nguyên)", "")
        try:
            cac_bo = liet_ke_ve(self._app.base_dir)
        except Exception:  # noqa: BLE001 — thiếu khuôn thì vẫn dùng được ô màu
            cac_bo = []
        self._bo_ve = {b.ma: b for b in cac_bo}
        for b in cac_bo:
            self._o_bo_ve.addItem(b.nhan, b.ma)
        # Khoá `style_name` trong tệp kênh là tên KỸ THUẬT của bộ vẽ; ô chọn
        # hiện tên tiếng Việt, nên dò ngược qua dữ liệu của từng bộ.
        for i, b in enumerate(cac_bo):
            if str(b.du_lieu.get("style_name") or "").strip() == dang or b.ma == dang:
                self._o_bo_ve.setCurrentIndex(i + 1)
                break
        self._dat_mau_bia(str(style.get("thumb_text_hex") or ""))

    def _dat_mau_bia(self, hex_mau: str) -> None:
        self._o_mau.setText(hex_mau)
        self._o_xem_mau.setStyleSheet(
            "background:{0};border:1px solid {1};border-radius:5px;".format(
                hex_mau or theme.NEN, theme.VIEN))

    def _chon_mau_bia(self) -> None:
        from PyQt5.QtGui import QColor  # noqa: PLC0415

        mau = QColorDialog.getColor(QColor(self._o_mau.text().strip() or "#0E7C86"),
                                    self, "Màu khối chữ trên ảnh bìa")
        if not mau.isValid():
            return
        self._dat_mau_bia(mau.name().upper())
        self._luu_mau_bia()

    def _luu_mau_bia(self) -> None:
        if getattr(self, "_dang_nap_tu_chay", False):
            return
        ma = self._lay_ma()
        hex_mau = self._o_mau.text().strip()
        if not ma or not hex_mau:
            return
        from core.dong_bo_kenh import ghi_style  # noqa: PLC0415

        try:
            ghi_style(self._app.base_dir, ma, {"thumb_text_hex": hex_mau})
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._dat_mau_bia(hex_mau)
        self._kiem_trung_giong(ma)

    def _doi_bo_ve(self) -> None:
        """Đổi bộ vẽ = ghi lại TRỌN 16 khoá hình — nên hỏi một câu trước.

        Mọi ô khác trên thẻ này lưu ngay không hỏi, vì sửa nhầm thì sửa lại
        được trong ba giây. Ô này thì không: nó đè lên mười sáu đoạn lời nhắc
        có thể đã được nắn tay nhiều tháng, và không có nút hoàn tác.
        """
        if getattr(self, "_dang_nap_tu_chay", False):
            return
        ma = self._lay_ma()
        ma_bo = str(self._o_bo_ve.currentData() or "")
        if not ma or not ma_bo:
            return
        bo = getattr(self, "_bo_ve", {}).get(ma_bo)
        if bo is None:
            return
        hoi = QMessageBox.question(
            self, "Đổi bộ vẽ",
            "Đổi kênh {0} sang bộ vẽ “{1}”?\n\nViệc này ghi đè 16 khoá hình "
            "trong style.yaml của kênh (nét vẽ, màu, khoá giữ nhân vật, kiểu "
            "chữ ảnh bìa). Không hoàn tác được.".format(ma, bo.nhan))
        if hoi != QMessageBox.Yes:
            self._nap_cach_ve(ma)
            return
        from core.dong_bo_kenh import ghi_style  # noqa: PLC0415
        from core.khuon import KHOA_VE  # noqa: PLC0415

        try:
            ghi_style(self._app.base_dir, ma,
                      {k: bo.du_lieu[k] for k in KHOA_VE if bo.du_lieu.get(k)})
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._dang_nap_tu_chay = True
        try:
            self._nap_cach_ve(ma)
        finally:
            self._dang_nap_tu_chay = False
        self._kiem_trung_giong(ma)

    # ── Kênh anh em có giống nhau quá không ─────────────────────────────────

    def _kiem_trung_giong(self, ma: str) -> None:
        """Cảnh báo tại chỗ khi kênh này trùng giọng/bộ vẽ/màu với kênh anh em.

        Gọi `core.nhom_kenh.kiem_trung_lap` — phép so đã có sẵn và đã trả về
        câu tiếng Việt; viết lại ở đây là hai bộ luật lệch nhau.
        """
        self._nhan_trung.setText("")
        if not ma:
            return
        goc = self._app.base_dir

        def viec():
            from core.nhom_kenh import kiem_trung_lap, nhom_cua_kenh  # noqa: PLC0415

            nhom = nhom_cua_kenh(goc, ma)
            return list(kiem_trung_lap(goc, nhom)) if nhom else []

        def xong(canh_bao) -> None:
            lien_quan = [_bo_ten_khoa(c) for c in canh_bao or [] if ma in str(c)]
            self._nhan_trung.setText(
                "⚠ " + " · ".join(lien_quan) if lien_quan else "")

        self._app.run_bg(viec, on_ok=xong, on_err=lambda _l: None)

    def _tep_dang_chon(self) -> str:
        """Giá trị `tep` sẽ ghi xuống `kenh.yaml`.

        Người dùng KHÔNG đổi tệp thì ghi lại nguyên văn thứ đang có trong tệp
        (có thể là slug), không tự tiện đổi nó thành mã số — đổi cách viết một
        khoá mà không ai yêu cầu là tự đẻ ra một lần khác biệt để sau này đi tìm.
        """
        dang = str(self._o_tep.currentData() or "")
        goc = getattr(self, "_tep_goc", "")
        if goc and _so_tep_gui(goc) == dang:
            return goc
        return dang

    def _nap_combo_nhom(self, nhom_hien: str) -> None:
        self._o_nhom.blockSignals(True)
        try:
            self._o_nhom.clear()
            self._o_nhom.addItem("")
            for n in _danh_sach_nhom(self._app.base_dir):
                if n != nhom_hien:
                    self._o_nhom.addItem(n)
            self._o_nhom.setEditText(nhom_hien or "")
        finally:
            self._o_nhom.blockSignals(False)

    def _tu_luu_tu_chay(self) -> None:
        if getattr(self, "_dang_nap_tu_chay", False):
            return
        ma = self._lay_ma()
        if not ma:
            return
        try:
            _ghi_khoa_tu_chay(
                self._app.base_dir, ma,
                tu_chay=self._o_tu_chay.isChecked(),
                ngan_sach_ngay=self._o_ngan_sach.value(),
                tu_duyet=self._o_tu_duyet.isChecked(),
                gio_dang=self._o_gio_dang.time().toString("HH:mm"),
                chu_ky_dang_ngay=int(self._o_chu_ky_dang.value()),
                san_xuat_truoc_gio=int(self._o_san_xuat_truoc.value()),
                thu_muc_done=self._o_thu_muc_done.value,
                nhom=self._o_nhom.currentText().strip(),
                tep=self._tep_dang_chon(),
                tu_don=self._o_tu_don.isChecked(),
                don_sau_gio=int(self._o_don_sau.value()),
                voice_id=self._o_voice.text().strip(),
                phut_muc_tieu=int(self._o_phut.value()),
                nhan_tieu_de=self._o_nhan_tieu_de.text().strip(),
                so_ban_nhap=int(self._o_so_ban.value()),
                ngay_bat_dau=self._o_ngay_bat_dau.text().strip())
        except Exception as loi:  # noqa: BLE001 — lưu hỏng phải nói, không văng
            self._app.show_error(loi)
            return
        self._kiem_trung_giong(ma)
        if self._on_luu is not None:
            try:
                self._on_luu()
            except Exception:  # noqa: BLE001 — nơi nhận hỏng không chặn việc lưu
                pass

    def _nap_nhat_ky_tu_chay(self, ma: str) -> None:
        import datetime as _dt  # noqa: PLC0415

        from core.tu_chay import duong_bao_cao_ngay  # noqa: PLC0415

        self._ds_nhat_ky_tu_chay.clear()
        hom_nay = _dt.date.today()
        for i in range(7):
            ngay = hom_nay - _dt.timedelta(days=i)
            duong = duong_bao_cao_ngay(self._app.base_dir, ma, ngay.isoformat())
            try:
                with open(duong, "r", encoding="utf-8") as tep:
                    bao_cao = json.load(tep)
            except (OSError, ValueError):
                continue
            runs = [r for r in (bao_cao.get("runs") or []) if not r.get("tham_chieu_ma_luot")]
            if not runs:
                continue
            r = runs[-1]
            nguon = r.get("nguon") or {}
            sx = r.get("san_xuat") or {}
            bg = r.get("ban_giao") or {}
            tieu_de = str(nguon.get("tieu_de") or "(chưa chọn video)")[:40]
            if bg.get("da_ban_giao"):
                trang_thai = "đã bàn giao"
            elif sx.get("xong_het"):
                trang_thai = "xong, chưa bàn giao"
            elif sx.get("da_chay"):
                trang_thai = "đang sản xuất / chưa xong hết"
            else:
                trang_thai = "chưa sản xuất"
            self._ds_nhat_ky_tu_chay.addItem("{0} · {1} · {2}".format(
                ngay.strftime("%d/%m"), tieu_de, trang_thai))
        if self._ds_nhat_ky_tu_chay.count() == 0:
            self._ds_nhat_ky_tu_chay.addItem("(chưa có lượt tự chạy nào trong 7 ngày qua)")

    def _chay_thu(self) -> None:
        ma = self._lay_ma()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn một kênh trong danh sách trước rồi bấm lại.")
            return
        self._nhan_ket_qua_thu.setText("Đang chạy thử — có thể mất một lúc, không tốn tiền…")
        goc = self._app.base_dir

        def viec():
            from core import tu_chay  # noqa: PLC0415

            return tu_chay.chay_mot_ngay(goc, ma, client=None, che_do="thu")

        self._app.run_bg(viec, on_ok=self._xong_chay_thu, on_err=self._loi_chay_thu)

    def _xong_chay_thu(self, ket) -> None:
        tom_tat = str((ket or {}).get("tom_tat") or "").strip()
        run = (ket or {}).get("run") or {}
        nguon = (run.get("nguon") or {}).get("nguon") or ""
        if nguon:
            tom_tat = "{0}  (nguồn: {1})".format(tom_tat, nguon) if tom_tat else \
                "Nguồn: {0}".format(nguon)
        self._nhan_ket_qua_thu.setText(tom_tat or "Không chọn được video nào hôm nay.")

    def _loi_chay_thu(self, loi: BaseException) -> None:
        self._nhan_ket_qua_thu.setText("Chạy thử hỏng: {0}".format(loi))

    # ── Lịch chạy nền (máy này, mọi kênh đã bật tự chạy) ────────────────────

    def _cap_nhat_trang_thai_lich(self) -> None:
        goc = self._app.base_dir

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.trang_thai(goc)

        self._app.run_bg(viec, on_ok=self._ve_trang_thai_lich,
                         on_err=lambda _loi: self._ve_trang_thai_lich(None))

    def _ve_trang_thai_lich(self, tt) -> None:
        if tt is None:
            self._nhan_lich.setText("Lịch hằng ngày: chưa có trên máy này.")
            self._nut_lich.setText("Bật lịch")
            self._nut_lich.setEnabled(False)
            return
        self._nut_lich.setEnabled(True)
        if tt.get("da_dang_ky"):
            # `gio_hhmm` chứ không in thẳng: Windows trả "2:00:00 AM" theo
            # định dạng vùng — xem `ui_qt/widgets.py::gio_hhmm`.
            chu = "đang BẬT, {0} mỗi ngày".format(gio_hhmm(tt.get("gio")) or "?")
            gio_t = QTime.fromString(gio_hhmm(tt.get("gio")), "HH:mm")
            if gio_t.isValid() and not self._o_gio_lich.hasFocus():
                self._o_gio_lich.setTime(gio_t)
            cuoi = lan_chay_gon(tt.get("lan_chay_cuoi"))
            if cuoi:
                chu += " — lần chạy cuối {0}".format(cuoi)
                if tt.get("ket_qua_cuoi"):
                    chu += " ({0})".format(tt.get("ket_qua_cuoi"))
            self._nhan_lich.setText("Lịch hằng ngày: " + chu)
            self._nut_lich.setText("Tắt lịch")
        else:
            self._nhan_lich.setText("Lịch hằng ngày: đang TẮT.")
            self._nut_lich.setText("Bật lịch")

    def _bat_tat_lich(self) -> None:
        goc = self._app.base_dir
        bat = self._nut_lich.text() == "Bật lịch"
        gio = self._o_gio_lich.time().toString("HH:mm")

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.dang_ky(goc, gio=gio) if bat else lich_tu_chay.huy(goc)

        def xong(ket) -> None:
            ok, msg = ket
            self._app.show_message(
                "Lịch hằng ngày",
                msg or ("Đã bật, chạy lúc {0} mỗi ngày.".format(gio) if ok else "Đã tắt lịch."))
            self._cap_nhat_trang_thai_lich()

        def loi(loi_thuc: BaseException) -> None:
            if isinstance(loi_thuc, ImportError):
                self._app.show_message(
                    "Chưa có bộ lập lịch",
                    "Phần lập lịch hằng ngày chưa có trên máy này — cập nhật "
                    "tool rồi thử lại.")
            else:
                self._app.show_error(loi_thuc)

        self._app.run_bg(viec, on_ok=xong, on_err=loi)



class TrangQuanLyKenh(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang(
            "Quản lý kênh",
            "Mỗi kênh một hồ sơ: phong cách, lời nhắc, cách dựng.",
            "quan-ly-kenh"))

        khung = the()
        trong = QVBoxLayout(khung)
        trong.setSpacing(8)

        self._danh_sach = QListWidget()
        self._danh_sach.setToolTip("Nháy đúp một kênh để mở trình thiết kế.")
        self._danh_sach.itemDoubleClicked.connect(lambda _m: self._mo_kenh())
        # Thẻ "Tự chạy hằng ngày" bên dưới đọc/ghi ĐÚNG kênh đang bôi đen ở
        # đây — đổi chọn là thẻ tự nạp lại, không cần một ô chọn kênh riêng.
        self._danh_sach.currentItemChanged.connect(
            lambda _cur, _truoc: self._nap_tu_chay())
        trong.addWidget(self._danh_sach, 1)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Mở kênh", self._mo_kenh, rong=140))
        hang.addWidget(nut_phu("Tạo kênh mới", self._tao_kenh, rong=150))
        hang.addWidget(nut_phu("Nhân bản", self._nhan_ban, rong=130))
        hang.addWidget(nut_phu("Tạo kênh trong nhóm", self._tao_kenh_trong_nhom, rong=180))
        hang.addWidget(nut_phu("Mở thư mục kênh", self._mo_thu_muc, rong=170))
        trong.addLayout(hang)

        trong.addWidget(nhan(
            "Kênh MẪU được cập nhật cùng tool — muốn sửa thì bấm “Nhân bản” ra "
            "bản riêng của bạn trước, bản riêng thì cập nhật tool không đụng "
            "vào. Chạy sản xuất cho kênh nằm ở tab “Video sản xuất tự động”; "
            "số liệu kênh đổ về ở tab “Phân tích & Nghiên cứu”.", "muted"))
        doc.addWidget(khung, 1)
        # "Tự chạy hằng ngày" đứng NGAY sau danh sách kênh — đây là nơi khách
        # quyết kênh nào chạy không người trông và tiêu tối đa bao nhiêu.
        # "Đăng tự động" (bên dưới) chỉ tới lượt khi đã có video làm xong,
        # nên xếp sau đúng thứ tự dây chuyền sản xuất → đăng.
        doc.addWidget(self._the_tu_chay())
        doc.addWidget(self._the_dang_tu_dong())
        self.nap_lai()

    # ── Thẻ "Tự chạy hằng ngày" (lớp `TheTuChay`, dùng chung với Trung tâm) ──

    #: Tên các ô của thẻ mà trang này (và bài kiểm cũ) vẫn gọi thẳng.
    _O_THE = ("_o_tu_chay", "_o_ngan_sach", "_nhan_ngan_sach", "_o_tu_duyet",
              "_o_gio_dang", "_o_chu_ky_dang", "_o_san_xuat_truoc",
              "_o_thu_muc_done", "_o_nhom", "_o_tep",
              "_nhan_ket_qua_thu", "_nhan_lich", "_o_gio_lich", "_nut_lich",
              "_ds_nhat_ky_tu_chay",
              # 21/09/2026 — mọi thiết lập sửa được ngay trên giao diện.
              "_o_tu_dang", "_o_tu_cmt", "_o_tu_don", "_o_don_sau", "_o_voice",
              "_o_phut", "_o_nhan_tieu_de", "_o_so_ban", "_o_bo_ve", "_o_mau",
              "_nhan_trung")

    def _the_tu_chay(self) -> QWidget:
        self._the_tc = TheTuChay(self._app, self._ma_dang_chon)
        for ten in self._O_THE:
            setattr(self, ten, getattr(self._the_tc, ten))
        return self._the_tc

    def _nap_tu_chay(self) -> None:
        the_tc = getattr(self, "_the_tc", None)
        if the_tc is not None:
            the_tc.nap()

    def _chay_thu(self) -> None:
        self._the_tc._chay_thu()

    # ── "Tạo kênh trong nhóm" ────────────────────────────────────────────────

    def _tao_kenh_trong_nhom(self) -> None:
        hop = HopTaoKenhTrongNhom(self._app, self._ma_dang_chon(), self)
        hop.exec_()
        if hop.ma_kenh_moi:
            self._bao_moi_noi(hop.ma_kenh_moi)

    def _the_dang_tu_dong(self) -> QWidget:
        """Công tắc ĐĂNG TỰ ĐỘNG + thẻ Bàn giao & kế hoạch đăng.

        Chủ dự án, 02/09/2026: *"cái bàn giao và kế hoạch đăng... ở chỗ quản
        lý kênh kiểu dạng bật tắt — nếu bật thì có logic về thời gian đăng và
        chu kỳ đăng; cái này chưa quan trọng... cứ để mặc định là tắt"*.

        ═══ CÔNG TẮC DỜI LÊN THẺ TRÊN (21/09/2026) ═══

        Ô tick "Bật đăng tự động" từng nằm ngay đây, và nó đọc/ghi theo ô chọn
        kênh CỦA RIÊNG thẻ sổ đăng — trong khi mọi thiết lập khác của kênh đi
        theo kênh đang bôi đen ở danh sách phía trên. Hai ô chọn kênh trong một
        trang là hai thứ lệch nhau chờ ngày cắn nhau: gạt công tắc tưởng là cho
        kênh này, hoá ra cho kênh kia.

        Chủ dự án, 21/09/2026: *"gom vào một trang cài đặt cho mỗi kênh"*. Nên
        công tắc ấy giờ nằm cùng ba công tắc anh em của nó trên thẻ "Tự chạy
        hằng ngày" (`TheTuChay._o_tu_dang`); ở đây chỉ còn SỔ đăng.
        """
        from .trang_phan_tich import TrangMayVM  # noqa: PLC0415

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Sổ bàn giao & kế hoạch đăng", "h2"))
        v.addWidget(nhan(
            "Công tắc “Máy tự đăng” nằm ở thẻ “Tự chạy hằng ngày” phía trên, "
            "cùng ba công tắc kia và cùng đi theo kênh bạn đang chọn.", "muted"))

        # Thẻ bàn giao dùng lại NGUYÊN CON từ Máy VM (phan=("ban_giao",)) —
        # một bộ mã hai cửa vào, đúng luật của trang này.
        self._so_dang = TrangMayVM(self._app, None, co_tieu_de=False,
                                   phan=("ban_giao",))
        self._so_dang.layout().setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._so_dang)
        return khung

    def _kenh_dang_chon(self) -> str:
        return self._so_dang._chon_kenh.currentText().strip()

    # ── Danh sách ────────────────────────────────────────────────────────────

    def nap_lai(self) -> None:
        """Đọc lại `CHANNEL/` — đĩa là bản chính, y nguyên tắc của tab Tự động."""
        dang = self._ma_dang_chon()
        self._danh_sach.clear()
        for ma in liet_ke_kenh(self._app.base_dir):
            kenh = doc_kenh(self._app.base_dir, ma)
            loai = ("kênh riêng của bạn" if kenh.kenh_rieng
                    else "kênh mẫu của tool" if kenh.mau_cua_tool else "")
            chu = ma if not kenh.ten or kenh.ten == ma else "{0} — {1}".format(ma, kenh.ten)
            if loai:
                chu = "{0}   ({1})".format(chu, loai)
            muc = QListWidgetItem(chu)
            muc.setData(0x0100, ma)  # Qt.UserRole
            self._danh_sach.addItem(muc)
            if ma == dang:
                self._danh_sach.setCurrentItem(muc)
        if self._danh_sach.currentRow() < 0 and self._danh_sach.count():
            self._danh_sach.setCurrentRow(0)
        # `setCurrentItem`/`setCurrentRow` ở trên chỉ phát tín hiệu khi ĐỔI
        # dòng — chọn lại đúng kênh cũ (ví dụ sau khi đóng HopKenh) không bắn
        # `currentItemChanged`, mà `kenh.yaml` có thể vừa bị sửa. Gọi thẳng
        # cho chắc, thẻ Tự chạy tự bỏ qua nếu chưa dựng xong.
        self._nap_tu_chay()

    def _ma_dang_chon(self) -> str:
        muc = self._danh_sach.currentItem() if hasattr(self, "_danh_sach") else None
        return str(muc.data(0x0100)) if muc is not None else ""

    # ── Nút ──────────────────────────────────────────────────────────────────

    def _mo_kenh(self) -> None:
        ma = self._ma_dang_chon()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn một kênh trong danh sách rồi bấm Mở kênh.")
            return
        from .kenh import HopKenh  # noqa: PLC0415

        HopKenh(self._app, ma, self).exec_()
        self._bao_moi_noi()

    def _tao_kenh(self) -> None:
        from .kenh import HopKenh  # noqa: PLC0415

        hop = HopKenh(self._app, "", self)
        hop.exec_()
        self._bao_moi_noi(hop.ma_kenh_moi)

    def _nhan_ban(self) -> None:
        ma = self._ma_dang_chon()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn kênh muốn nhân bản rồi bấm Nhân bản.")
            return
        from .kenh import HopNhanBan  # noqa: PLC0415

        hop = HopNhanBan(self._app, ma, self)
        hop.exec_()
        self._bao_moi_noi(hop.ma_kenh_moi)

    def _mo_thu_muc(self) -> None:
        ma = self._ma_dang_chon()
        duong = duong_kenh(self._app.base_dir, ma)
        if not os.path.isdir(duong):
            duong = duong_kenh(self._app.base_dir)
        mo_thu_muc(duong)

    def _bao_moi_noi(self, ma_moi: str = "") -> None:
        """Sau khi một hộp thoại đóng: đọc lại danh sách Ở CẢ HAI CỬA.

        Tab "Video sản xuất tự động" có ô chọn kênh riêng — sửa kênh ở đây mà
        bên đó không nạp lại thì hai tab nói hai chuyện khác nhau về cùng một
        thư mục.
        """
        self.nap_lai()
        if ma_moi:
            for i in range(self._danh_sach.count()):
                if self._danh_sach.item(i).data(0x0100) == ma_moi:
                    self._danh_sach.setCurrentRow(i)
                    break
        auto = self._app.trang("auto")
        nap = getattr(auto, "_nap_kenh", None)
        if nap is not None:
            try:
                nap()
            except Exception:  # noqa: BLE001 — tab kia hỏng không kéo tab này
                pass
