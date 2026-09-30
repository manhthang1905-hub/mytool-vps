"""Trang **CÀI ĐẶT** — các việc hệ thống ít dùng của máy VPS.

Trang cuối trong quy trình vận hành VPS (xem `core/che_do_vps.py`). Ở đây là
mọi thứ KHÔNG phải nội dung: ba con chạy nền, nhật ký, hai lịch Windows, kênh
báo động Telegram, cập nhật tool, và ví.

═══ MỌI THIẾT LẬP SỬA ĐƯỢC NGAY TRÊN GIAO DIỆN ═══

Chủ dự án, 21/09/2026: *"tao muốn nó đơn giản hiệu quả mà có thể quản lý và
thiết lập all ở gui để chủ động"*. Nghĩa là sau trang này, không còn việc nào
bắt họ mở `bao-dong.json` bằng Notepad hay gọi người viết mã.

Ba thứ trước đây chỉ sửa được bằng tay, giờ có ô nhập ở đây:

* **Kênh báo động Telegram** — bật/tắt, mã bot, mã hộp chat, và nút *Gửi thử
  một tin* để biết đường có thông. Ghi vào `bao-dong.json` cạnh `config.json`,
  đúng dạng `core/bao_dong.py` đọc. KHÔNG bao giờ ghi mã bot vào `config.json`
  hay `secrets.json` — xem đầu `core/bao_dong.py` về lý do tách tệp.
* **Lịch chạy hằng ngày** (`ShopAPI-TuChay`) — giờ chạy, bật/tắt.
* **Lịch canh trạm** (`ShopAPI-CanhTram`) — chó giữ nhà cho cổng 8765: mấy
  phút kiểm một lượt, bật/tắt.

═══ TRẠM 8765 KHÔNG ĐI THEO TAB "VPS" ═══

Tab "VPS" cũ (`ui_qt/trang_vps.py`) bị bỏ hẳn: nó để THUÊ máy ảo rồi bấm mở
Remote Desktop VÀO máy — ngồi ngay trên chính máy đó thì vô nghĩa. Nhưng nó
còn chở theo một thứ KHÔNG được mất: `TrangChiSoYTB(phan=("cai","tram"))`, bản
giữ **trạm cổng 8765** mà cả ba con `vm/` nói chuyện qua đó. Nó chuyển sang
đây nguyên con, và trang này khai `self.chi_so` đúng tên cũ để
`ui_qt/tram_chung.tim_tram` vẫn tìm ra.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLineEdit, QPlainTextEdit,
    QScrollArea, QSpinBox, QTabWidget, QTimeEdit, QVBoxLayout, QWidget,
)

from . import theme
from .trang_trung_tam import _TEN_MAY, _giam_sat
from .widgets import (HangXuongDong, gio_hhmm, lan_chay_gon, mo_thu_muc, nhan,
                      nut_chinh, nut_phu, the, tieu_de_trang)

__all__ = ["TrangMayVi", "TrangHeThongVps", "TheMay", "TheBaoDong", "TheLich",
           "TAB_CON"]

TAB_CON = ("Máy", "Trạm && tiện ích", "Ví && Cài đặt")

#: Nguồn nhật ký cố định (không phải một trong ba con chạy nền).
NGUON_LOG = (("Lịch chạy hằng ngày", "lich"),)


class TheLich(QWidget):
    """Hai lịch Windows của máy này, mỗi cái một dòng.

    Bọc `core.lich_tu_chay` — mọi lời gọi `schtasks` chạy NỀN (mất cả giây, đủ
    để cửa sổ đứng hình nếu gọi thẳng trên luồng vẽ).
    """

    def __init__(self, app, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        v.addWidget(nhan("Lịch của Windows", "h2"))
        v.addWidget(nhan(
            "Hai việc này do Windows gọi, không phải tool — nên chúng vẫn chạy "
            "khi cửa sổ tool đang đóng. Máy phải đang bật và đã đăng nhập.",
            "muted"))

        hang = HangXuongDong()
        hang.addWidget(nhan("Chạy mọi kênh lúc"))
        self.o_gio = QTimeEdit(QTime(2, 0))
        self.o_gio.setDisplayFormat("HH:mm")
        self.o_gio.setToolTip("Giờ máy tự làm lần lượt mọi kênh đã bật “Tự chạy”.")
        hang.addWidget(self.o_gio)
        self.nut_chay = nut_phu("Bật", lambda: self._dat_chay(True), rong=74)
        self.nut_tat_chay = nut_phu("Tắt", lambda: self._dat_chay(False), rong=74)
        hang.addWidget(self.nut_chay)
        hang.addWidget(self.nut_tat_chay)
        v.addLayout(hang)
        self.nhan_chay = nhan("đang xem…", "muted")
        self.nhan_chay.setMinimumWidth(1)
        v.addWidget(self.nhan_chay)

        hang2 = HangXuongDong()
        hang2.addWidget(nhan("Canh trạm mỗi"))
        self.o_phut = QSpinBox()
        self.o_phut.setRange(1, 1439)
        self.o_phut.setValue(5)
        self.o_phut.setSuffix(" phút")
        self.o_phut.setToolTip(
            "Cổng 8765 là chỗ ba máy con nhận việc. Việc này kiểm cổng đều đặn, "
            "chết thì bật lại — nên không ai phải ngồi canh.")
        hang2.addWidget(self.o_phut)
        self.nut_tram = nut_phu("Bật", lambda: self._dat_tram(True), rong=74)
        self.nut_tat_tram = nut_phu("Tắt", lambda: self._dat_tram(False), rong=74)
        hang2.addWidget(self.nut_tram)
        hang2.addWidget(self.nut_tat_tram)
        v.addLayout(hang2)
        self.nhan_tram = nhan("đang xem…", "muted")
        self.nhan_tram.setMinimumWidth(1)
        v.addWidget(self.nhan_tram)

        self.hoi()

    # ── Đọc ──────────────────────────────────────────────────────────────────

    def hoi(self) -> None:
        goc = self._app.base_dir

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return (lich_tu_chay.trang_thai(goc),
                    lich_tu_chay.trang_thai_canh_tram(goc))

        self._app.run_bg(viec, on_ok=self._ve, on_err=lambda _l: self._ve(None))

    def _ve(self, ket) -> None:
        if ket is None:
            self.nhan_chay.setText("không đọc được lịch trên máy này.")
            self.nhan_tram.setText("không đọc được lịch trên máy này.")
            return
        chay, tram = ket
        self.nhan_chay.setText(self._cau(chay, "Chưa đặt — không kênh nào tự chạy "
                                               "khi bạn vắng."))
        gio = gio_hhmm((chay or {}).get("gio"))
        if gio:
            t = QTime.fromString(gio, "HH:mm")
            if t.isValid() and not self.o_gio.hasFocus():
                self.o_gio.setTime(t)
        # Việc canh trạm lặp theo PHÚT, không phải mỗi ngày một lượt — in giờ
        # bắt đầu kèm chữ "mỗi ngày" là nói sai hẳn việc nó đang làm.
        self.nhan_tram.setText(self._cau(tram, "Chưa đặt — cổng 8765 chết thì "
                                               "KHÔNG ai bật lại.", co_gio=False))

    @staticmethod
    def _cau(tt_lich: Optional[Dict[str, Any]], khi_tat: str,
             *, co_gio: bool = True) -> str:
        if not tt_lich or not tt_lich.get("da_dang_ky"):
            return khi_tat
        chu = "Đang BẬT"
        gio = gio_hhmm(tt_lich.get("gio")) if co_gio else ""
        if gio:
            chu += ", {0} mỗi ngày".format(gio)
        cuoi = lan_chay_gon(tt_lich.get("lan_chay_cuoi"))
        if cuoi:
            ket = str(tt_lich.get("ket_qua_cuoi") or "").strip()
            chu += " — lần cuối {0}{1}".format(cuoi, " ({0})".format(ket) if ket else "")
        else:
            chu += " — chưa chạy lần nào"
        return chu

    # ── Ghi ──────────────────────────────────────────────────────────────────

    def _dat_chay(self, bat: bool) -> None:
        goc = self._app.base_dir
        gio = self.o_gio.time().toString("HH:mm")

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.dang_ky(goc, gio=gio) if bat else lich_tu_chay.huy(goc)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._app.show_error)

    def _dat_tram(self, bat: bool) -> None:
        goc = self._app.base_dir
        phut = int(self.o_phut.value())

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return (lich_tu_chay.dang_ky_canh_tram(goc, phut) if bat
                    else lich_tu_chay.huy_canh_tram(goc))

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._app.show_error)

    def _xong(self, ket) -> None:
        _ok, msg = ket
        self._app.show_message("Lịch của Windows", msg or "Xong.")
        self.hoi()


class TheBaoDong(QWidget):
    """Kênh báo động Telegram — bật/tắt, mã bot, mã hộp chat, gửi thử.

    Ghi thẳng `bao-dong.json` ở thư mục gốc (`core.bao_dong.bao_dong_path_for`)
    và giữ nguyên mọi khoá khác đang có trong tệp (ví dụ `webhook`) — tệp này
    có thể đã được đặt tay, giao diện không được xoá phần mình không hiểu.
    """

    def __init__(self, app, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        v.addWidget(nhan("Báo sự cố về điện thoại", "h2"))
        v.addWidget(nhan(
            "Máy chạy không người trông thì cái đáng sợ nhất là nó hỏng mà "
            "không ai biết. Điền mã bot Telegram vào đây, tool sẽ nhắn khi ví "
            "cạn, ổ đầy, trạm chết hay một kênh hỏng.", "muted"))

        self.o_bat = QCheckBox("Bật báo sự cố")
        self.o_bat.setToolTip("Tắt thì tool im lặng hoàn toàn, kể cả khi hỏng.")
        self.o_bat.toggled.connect(lambda _b: self._luu())
        v.addWidget(self.o_bat)

        hang = HangXuongDong()
        hang.addWidget(nhan("Mã bot:"))
        self.o_token = QLineEdit()
        self.o_token.setMinimumWidth(180)
        self.o_token.setPlaceholderText("lấy ở @BotFather trên Telegram")
        self.o_token.setToolTip(
            "Chuỗi @BotFather đưa cho bạn khi tạo bot. Nó nằm trong "
            "bao-dong.json, KHÔNG nằm chung với khoá tài khoản của bạn.")
        self.o_token.editingFinished.connect(self._luu)
        hang.addWidget(self.o_token)
        hang.addWidget(nhan("Mã hộp chat:"))
        self.o_chat = QLineEdit()
        self.o_chat.setMinimumWidth(120)
        self.o_chat.setPlaceholderText("ví dụ 123456789")
        self.o_chat.setToolTip("Nhắn cho @userinfobot trên Telegram để biết mã này.")
        self.o_chat.editingFinished.connect(self._luu)
        hang.addWidget(self.o_chat)
        v.addLayout(hang)

        hang2 = HangXuongDong()
        hang2.addWidget(nut_phu("Gửi thử một tin", self._gui_thu, rong=150))
        v.addLayout(hang2)
        self.nhan_kq = nhan("", "muted")
        self.nhan_kq.setMinimumWidth(1)
        v.addWidget(self.nhan_kq)

        self.nap()

    def _duong(self) -> str:
        from core.bao_dong import bao_dong_path_for  # noqa: PLC0415

        return bao_dong_path_for(self._app.base_dir)

    def nap(self) -> None:
        from core.bao_dong import doc_cau_hinh_bao_dong  # noqa: PLC0415

        cfg = doc_cau_hinh_bao_dong(self._app.base_dir) or {}
        tg = cfg.get("telegram") if isinstance(cfg.get("telegram"), dict) else {}
        self._dang_nap = True
        try:
            self.o_bat.setChecked(bool(cfg.get("enabled", False)))
            self.o_token.setText(str(tg.get("bot_token") or ""))
            self.o_chat.setText(str(tg.get("chat_id") or ""))
        finally:
            self._dang_nap = False

    def _luu(self) -> None:
        if getattr(self, "_dang_nap", False):
            return
        from core.bao_dong import doc_cau_hinh_bao_dong  # noqa: PLC0415

        cfg = dict(doc_cau_hinh_bao_dong(self._app.base_dir) or {})
        tg = dict(cfg.get("telegram") or {}) if isinstance(cfg.get("telegram"), dict) else {}
        tg["bot_token"] = self.o_token.text().strip()
        tg["chat_id"] = self.o_chat.text().strip()
        cfg["telegram"] = tg
        cfg["enabled"] = bool(self.o_bat.isChecked())
        duong = self._duong()
        try:
            os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
            tam = duong + ".tam"
            with open(tam, "w", encoding="utf-8") as tep:
                json.dump(cfg, tep, ensure_ascii=False, indent=1)
            os.replace(tam, duong)
        except OSError as loi:
            self.nhan_kq.setText("Không lưu được: {0}".format(loi))
            return
        self.nhan_kq.setText("Đã lưu.")

    def _gui_thu(self) -> None:
        self._luu()
        if not (self.o_token.text().strip() and self.o_chat.text().strip()):
            self.nhan_kq.setText("Điền cả mã bot lẫn mã hộp chat rồi bấm lại.")
            return
        if not self.o_bat.isChecked():
            self.nhan_kq.setText("Đang tắt báo sự cố — bật ô trên rồi bấm lại.")
            return
        self.nhan_kq.setText("Đang gửi…")
        goc = self._app.base_dir

        def viec():
            from core import bao_dong  # noqa: PLC0415

            # Quên khoảng lặng chống spam trước: người vừa bấm thử là muốn thấy
            # tin NGAY, không phải chờ hết một giờ vì lần thử trước.
            bao_dong.quen_lich_su_chong_spam("thu-tin")
            return bao_dong.bao_dong(
                "thu-tin", "MyTool trên VPS: thử đường báo sự cố",
                "Nhận được tin này là đường đã thông.", goc=goc)

        def xong(ok) -> None:
            self.nhan_kq.setText(
                "Đã gửi — mở Telegram xem có tin chưa." if ok else
                "Không gửi được. Kiểm lại mã bot và mã hộp chat, và nhớ nhắn "
                "cho bot một câu trước (Telegram không cho bot nhắn trước).")

        self._app.run_bg(viec, on_ok=xong,
                         on_err=lambda loi: self.nhan_kq.setText(
                             "Không gửi được: {0}".format(loi)))


class TheMay(QWidget):
    """Ba con chạy nền + nhật ký + lịch + báo động + cập nhật tool."""

    def __init__(self, app, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self._den: Dict[str, QWidget] = {}

        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(10)

        v.addWidget(self._the_con())
        v.addWidget(self._the_nhat_ky())
        khung_lich = the()
        vl = QVBoxLayout(khung_lich)
        vl.setContentsMargins(14, 12, 14, 12)
        self.lich = TheLich(app, khung_lich)
        vl.addWidget(self.lich)
        v.addWidget(khung_lich)

        khung_bd = the()
        vb = QVBoxLayout(khung_bd)
        vb.setContentsMargins(14, 12, 14, 12)
        self.bao_dong = TheBaoDong(app, khung_bd)
        vb.addWidget(self.bao_dong)
        v.addWidget(khung_bd)

        v.addWidget(self._the_tool())
        v.addStretch(1)
        self.lam_moi()

    # ── Ba con chạy nền ──────────────────────────────────────────────────────

    def _the_con(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        v.addWidget(nhan("Ba máy chạy nền", "h2"))
        v.addWidget(nhan(
            "Chúng chạy tách khỏi cửa sổ này: đóng tool thì chúng VẪN chạy.",
            "muted"))
        self._hang_con = HangXuongDong(8)
        v.addLayout(self._hang_con)
        self._nhan_con = nhan("", "muted")
        self._nhan_con.setMinimumWidth(1)
        v.addWidget(self._nhan_con)
        return khung

    def _ve_con(self) -> None:
        gs = _giam_sat(self._app)
        if gs is None:
            self._nhan_con.setText("Máy này không có ba máy con để trông.")
            return
        try:
            trang_thai = dict(gs.trang_thai() or {})
        except Exception as loi:  # noqa: BLE001
            self._nhan_con.setText("Không đọc được: {0}".format(str(loi)[:120]))
            return
        for ten, tt_may in trang_thai.items():
            o = self._den.get(ten)
            if o is None:
                from .trang_trung_tam import _OChiSo  # noqa: PLC0415

                o = _OChiSo(_TEN_MAY.get(ten, ten))
                o.clicked.connect(lambda t=ten: self.xem_nhat_ky_may(t))
                self._hang_con.addWidget(o)
                self._den[ten] = o
            from .trang_trung_tam import HONG, THUONG  # noqa: PLC0415

            song = bool((tt_may or {}).get("song"))
            o.dat("đang chạy" if song else "ĐÃ TẮT", THUONG if song else HONG)
            o.setToolTip("Bấm để xem nhật ký của {0}.".format(
                _TEN_MAY.get(ten, ten)))
        self._nhan_con.setText("")
        self._cap_nhat_nguon(trang_thai)

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    def _the_nhat_ky(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        hang = HangXuongDong()
        hang.addWidget(nhan("Nhật ký", "h2"))
        self._o_nguon = QComboBox()
        self._o_nguon.setMinimumWidth(170)
        for ten, khoa in NGUON_LOG:
            self._o_nguon.addItem(ten, khoa)
        self._o_nguon.activated.connect(lambda _i: self.nap_nhat_ky())
        hang.addWidget(self._o_nguon)
        hang.addWidget(nut_phu("Làm mới", self.lam_moi, rong=90))
        hang.addWidget(nut_phu("Bật lại máy", self._bat_lai_may, rong=120))
        hang.addWidget(nut_phu("Mở thư mục", lambda: mo_thu_muc(self._app.base_dir),
                               rong=120))
        v.addLayout(hang)
        self._o_log = QPlainTextEdit()
        self._o_log.setObjectName("log")
        self._o_log.setReadOnly(True)
        self._o_log.setMinimumHeight(180)
        v.addWidget(self._o_log, 1)
        return khung

    def _cap_nhat_nguon(self, trang_thai: Dict[str, Any]) -> None:
        for ten in trang_thai:
            if self._o_nguon.findData("may:" + ten) < 0:
                self._o_nguon.addItem(_TEN_MAY.get(ten, ten), "may:" + ten)

    def xem_nhat_ky_may(self, ten: str) -> None:
        i = self._o_nguon.findData("may:" + ten)
        if i >= 0:
            self._o_nguon.setCurrentIndex(i)
        self.nap_nhat_ky()

    def nap_nhat_ky(self) -> None:
        nguon = str(self._o_nguon.currentData() or "lich")
        dong = []
        if nguon.startswith("may:"):
            gs = _giam_sat(self._app)
            try:
                ra = gs.doc_nhat_ky(nguon[4:], 300) if gs is not None else []
            except Exception as loi:  # noqa: BLE001
                ra = ["(không đọc được nhật ký: {0})".format(loi)]
            dong = ra.splitlines() if isinstance(ra, str) else list(ra or [])
        else:
            from core import trung_tam as tt  # noqa: PLC0415

            duong = os.path.join(self._app.base_dir, "workspace", "tu-chay",
                                 "tu-chay.log")
            dong = tt.doc_duoi(duong, 300)
            if not dong:
                dong = ["(lịch hằng ngày chưa chạy lần nào trên máy này)"]
        self._o_log.setPlainText("\n".join(str(d) for d in dong))
        thanh = self._o_log.verticalScrollBar()
        thanh.setValue(thanh.maximum())

    def _bat_lai_may(self) -> None:
        nguon = str(self._o_nguon.currentData() or "")
        gs = _giam_sat(self._app)
        if gs is None or not nguon.startswith("may:"):
            self._app.show_message(
                "Chọn một máy trước",
                "Chọn tên một máy ở ô bên trái (Agent, Máy đăng, Trả lời bình "
                "luận) rồi bấm lại.")
            return
        ten = nguon[4:]
        self._app.run_bg(lambda: gs.khoi_dong_lai(ten),
                         on_ok=lambda _k: self.lam_moi(),
                         on_err=self._app.show_error)

    # ── Cập nhật tool ────────────────────────────────────────────────────────

    def _the_tool(self) -> QWidget:
        """Nút cập nhật — ở ĐÂY, không phải góc dưới trái thanh bên.

        Chủ dự án, 21/09/2026: nút to nhất góc dưới trái đang là "Cập nhật: đã
        tắt" — chỗ đẹp nhất của cửa sổ dành cho một thứ đang tắt. Máy này chạy
        kênh thật nhiều năm; cập nhật là việc vài tháng một lần, nên nó thuộc
        về chỗ kín đáo này.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        v.addWidget(nhan("Bản tool", "h2"))
        v.addWidget(nhan(
            "Tool tự cập nhật lúc máy rảnh (không cắt ngang lượt đăng/dựng). "
            "Xem thay đổi, cập nhật ngay, quay lại bản trước hay tắt tự động: "
            "trang Cài đặt → Cập nhật tool.", "muted"))
        nut = getattr(getattr(self._app, "_cap_nhat", None), "nut", None)
        if nut is not None:
            nut.setParent(khung)
            hang = HangXuongDong()
            hang.addWidget(nut)
            v.addLayout(hang)
        else:
            v.addWidget(nhan("Đường cập nhật chưa sẵn sàng trên máy này.", "muted"))
        return khung

    def lam_moi(self) -> None:
        self._ve_con()
        self.nap_nhat_ky()


class TrangMayVi(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(16, 12, 16, 12)
        doc.setSpacing(8)
        doc.addWidget(tieu_de_trang(
            "Máy & Ví",
            "Ba máy chạy nền, nhật ký, lịch Windows, báo sự cố, và tiền.",
            "may-vi"))

        self.tabs = QTabWidget()
        self.may = TheMay(app)
        self.tabs.addTab(self._cuon(self.may), TAB_CON[0])

        # Trạm 8765 — chuyển nguyên con từ tab "VPS" cũ. Tên thuộc tính GIỮ
        # NGUYÊN là `chi_so` để `ui_qt/tram_chung.tim_tram` tìm ra nó.
        from .trang_chi_so_ytb import TrangChiSoYTB  # noqa: PLC0415

        self.chi_so = TrangChiSoYTB(app, phan=("cai", "tram"))
        self.tabs.addTab(self._cuon(self.chi_so), TAB_CON[1])

        from .trang_quan_ly import TrangQuanLy  # noqa: PLC0415

        self.vi = TrangQuanLy(app)
        self.tabs.addTab(self._cuon(self.vi), TAB_CON[2])
        doc.addWidget(self.tabs, 1)

    @staticmethod
    def _cuon(trang: QWidget) -> QWidget:
        from PyQt5.QtCore import Qt  # noqa: PLC0415

        cuon = QScrollArea()
        cuon.setWidget(trang)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cuon.setMinimumWidth(1)
        return cuon

    def xem_nhat_ky_may(self, ten: str) -> None:
        """Trang Điều khiển gọi sang khi người dùng bấm một đèn máy."""
        self.tabs.setCurrentIndex(0)
        self.may.xem_nhat_ky_may(ten)

    def doi_du_an(self, ten: str) -> None:
        for con in (self.chi_so, self.vi):
            tiep = getattr(con, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001
                    pass


class TrangHeThongVps(QWidget):
    """Ba lối vào rõ ràng cho các việc hệ thống.

    Những màn hình nặng chỉ được dựng khi người dùng mở. Riêng ``chi_so`` vẫn
    phải tồn tại từ lúc mở tool vì nó giữ trạm 8765 sống cho các máy con.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self.may = None
        self.vi = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(16, 12, 16, 12)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang(
            "Cài đặt",
            "Chọn đúng việc cần làm; phần chi tiết chỉ mở khi bạn cần.",
            "may-vi"))

        # Khung Cập nhật (30/09/2026): phiên bản, bản mới + thay đổi, Kiểm tra /
        # Cập nhật ngay / Quay lại, công tắc Tự động cập nhật — `ui_qt/cap_nhat.py`.
        from .cap_nhat import BangCapNhat  # noqa: PLC0415

        doc.addWidget(BangCapNhat(app))
        self._nhan_suc_khoe = nhan("Đang đọc trạng thái…", "muted")
        doc.addWidget(self._the_hanh_dong(
            "Sức khỏe tool",
            "Xem máy nền nào đang chạy, đọc lỗi gần nhất, lịch tự chạy và cảnh báo.",
            "Kiểm tra tool", self._mo_suc_khoe, self._nhan_suc_khoe))
        doc.addWidget(self._the_hanh_dong(
            "Sửa và cài đặt",
            "Đổi đường nhận dữ liệu, tài khoản dịch vụ, số dư và các thiết lập ít dùng.",
            "Mở cài đặt", self._mo_cai_dat))
        doc.addWidget(self._the_hanh_dong(
            "Mở rộng sang VPS khác",
            "Chọn kênh và tạo một thư mục sẵn sàng chép sang máy mới.",
            "Thêm VPS", self._mo_trien_khai))
        self._nhan_khoi_dong_lai = nhan("Đang kiểm…", "muted")
        doc.addWidget(self._the_hanh_dong(
            "Khởi động lại giao diện",
            "Đóng rồi mở MyTool lại có an toàn ngay lúc này không — CHỈ để "
            "bạn biết trước, tool không tự đóng/mở cửa sổ nào.",
            "Kiểm lại", self._cap_nhat_khoi_dong_lai, self._nhan_khoi_dong_lai))
        doc.addStretch(1)

        # Trạm phải tồn tại từ lúc mở tool, dù người vận hành chưa mở phần cài.
        from .trang_chi_so_ytb import TrangChiSoYTB  # noqa: PLC0415

        self.chi_so = TrangChiSoYTB(app, phan=("cai", "tram"))
        self.chi_so.setParent(self)
        self.chi_so.hide()
        self._cap_nhat_suc_khoe()
        self._cap_nhat_khoi_dong_lai()

    @staticmethod
    def _the_hanh_dong(tieu_de: str, mo_ta: str, ten_nut: str, lenh,
                       trang_thai: Optional[QWidget] = None) -> QWidget:
        w = the()
        h = QHBoxLayout(w)
        h.setContentsMargins(18, 15, 18, 15)
        h.setSpacing(16)
        chu = QVBoxLayout()
        chu.setSpacing(4)
        chu.addWidget(nhan(tieu_de, "h2"))
        chu.addWidget(nhan(mo_ta, "muted"))
        if trang_thai is not None:
            chu.addWidget(trang_thai)
        h.addLayout(chu, 1)
        h.addWidget(nut_phu(ten_nut, lenh, rong=150))
        return w

    def _cap_nhat_suc_khoe(self) -> None:
        gs = _giam_sat(self._app)
        if gs is None:
            self._nhan_suc_khoe.setText("Không có dịch vụ nền trên máy này.")
            return
        try:
            cac_may = dict(gs.trang_thai() or {})
        except Exception as loi:  # noqa: BLE001
            self._nhan_suc_khoe.setText("Chưa đọc được trạng thái: {0}".format(
                str(loi)[:100]))
            return
        tong = len(cac_may)
        dang_chay = sum(bool((tt or {}).get("song")) for tt in cac_may.values())
        if tong and dang_chay == tong:
            self._nhan_suc_khoe.setText("Ổn · {0}/{0} dịch vụ nền đang chạy".format(tong))
        elif tong:
            self._nhan_suc_khoe.setText(
                "Cần kiểm tra · {0}/{1} dịch vụ nền đang chạy".format(dang_chay, tong))
        else:
            self._nhan_suc_khoe.setText("Chưa có dữ liệu trạng thái.")

    def _cap_nhat_khoi_dong_lai(self) -> None:
        """CHỈ ĐỌC (mục 6) — không tự đóng/mở cửa sổ, không giết tiến trình
        nào. `core.an_toan_khoi_dong.kiem_tra` là hàm thuần, đủ nhanh (vài tệp
        JSON nhỏ) để gọi thẳng trên luồng vẽ, cùng nếp `_cap_nhat_suc_khoe`."""
        goc = self._app.base_dir
        viec_chay_tay = bool(getattr(getattr(self._app, "jobs", None), "is_running", False))
        try:
            from core import an_toan_khoi_dong  # noqa: PLC0415

            kq = an_toan_khoi_dong.kiem_tra(goc, viec_chay_tay=viec_chay_tay)
        except Exception as loi:  # noqa: BLE001
            self._nhan_khoi_dong_lai.setText("Không kiểm được: {0}".format(str(loi)[:120]))
            self._nhan_khoi_dong_lai.setStyleSheet("")
            return
        if kq.get("duoc"):
            self._nhan_khoi_dong_lai.setText(
                "✓ An toàn — đóng rồi mở lại MyTool bây giờ được.")
            self._nhan_khoi_dong_lai.setStyleSheet(
                "color:{0};font-weight:600;".format(theme.XANH))
        else:
            ly_do = "; ".join(str(l) for l in (kq.get("ly_do") or []))
            self._nhan_khoi_dong_lai.setText(
                "✕ Chưa nên: {0}".format(ly_do or "chưa rõ lý do"))
            self._nhan_khoi_dong_lai.setStyleSheet(
                "color:{0};font-weight:600;".format(theme.DO))

    def _mo_trien_khai(self) -> None:
        from .trang_trien_khai_vps import HopTrienKhaiVps  # noqa: PLC0415

        HopTrienKhaiVps(self._app, self).exec_()

    def _bao_dam_may(self) -> TheMay:
        if self.may is None:
            self.may = TheMay(self._app)
        return self.may

    def _mo_suc_khoe(self) -> None:
        self._mo_hop("Sức khỏe tool", self._bao_dam_may(), giu_lai=True)
        self._cap_nhat_suc_khoe()

    def _mo_cai_dat(self) -> None:
        """Một cửa chọn ngắn, thay vì trộn mọi cài đặt lên màn hình chính."""
        hop = QDialog(self)
        hop.setWindowTitle("Sửa và cài đặt")
        hop.resize(560, 310)
        v = QVBoxLayout(hop)
        v.setSpacing(10)
        v.addWidget(nhan("Bạn cần sửa phần nào?", "h1"))
        v.addWidget(nhan(
            "Các thiết lập đang chạy được giữ nguyên cho tới khi bạn chủ động sửa.",
            "muted"))
        v.addWidget(self._the_hanh_dong(
            "Nhận dữ liệu YouTube",
            "Kiểm tra trạm 8765 và kết nối từ máy lấy chỉ số.",
            "Mở", lambda: self._mo_tu_hop(hop, self._mo_tram)))
        v.addWidget(self._the_hanh_dong(
            "Ví và tài khoản",
            "Quản lý số dư và tài khoản các dịch vụ tool sử dụng.",
            "Mở", lambda: self._mo_tu_hop(hop, self._mo_vi)))
        v.addStretch(1)
        hop.exec_()
        hop.deleteLater()

    @staticmethod
    def _mo_tu_hop(hop: QDialog, lenh) -> None:
        hop.accept()
        lenh()

    @staticmethod
    def _cuon(trang: QWidget) -> QWidget:
        from PyQt5.QtCore import Qt  # noqa: PLC0415

        cuon = QScrollArea()
        cuon.setWidget(trang)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cuon.setMinimumWidth(1)
        return cuon

    def _mo_tram(self) -> None:
        self._mo_hop("Trạm nhận dữ liệu", self.chi_so, giu_lai=True)

    def _mo_vi(self) -> None:
        if self.vi is None:
            from .trang_quan_ly import TrangQuanLy  # noqa: PLC0415

            self.vi = TrangQuanLy(self._app)
        self._mo_hop("Ví & tài khoản", self.vi, giu_lai=True)

    def _mo_hop(self, tieu_de: str, trang: QWidget, *, giu_lai: bool) -> None:
        from PyQt5.QtCore import Qt  # noqa: PLC0415

        hop = QDialog(self)
        hop.setWindowTitle(tieu_de)
        hop.resize(1120, 820)
        v = QVBoxLayout(hop)
        cuon = self._cuon(trang)
        v.addWidget(cuon, 1)
        v.addWidget(nut_chinh("Đóng", hop.accept, rong=90), 0, Qt.AlignRight)
        trang.show()
        hop.exec_()
        if giu_lai:
            cuon.takeWidget()
            trang.setParent(self)
            trang.hide()
        hop.deleteLater()

    def xem_nhat_ky_may(self, ten: str) -> None:
        may = self._bao_dam_may()
        may.xem_nhat_ky_may(ten)
        self._mo_hop("Sức khỏe tool", may, giu_lai=True)

    def doi_du_an(self, ten: str) -> None:
        for con in (self.chi_so, self.vi):
            if con is None:
                continue
            tiep = getattr(con, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001
                    pass
