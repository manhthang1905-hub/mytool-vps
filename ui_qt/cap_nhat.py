"""Khung **Cập nhật** trong Cài đặt + nút nhỏ ở thanh bên — giao diện của hệ
cập nhật DUY NHẤT `core/cap_nhat_git.py` (git + kho chung, 30/09/2026).

Chủ dự án, 30/09/2026: *"khi có update mới tool tự nâng version, trên giao diện
tool cũng nhìn được ở setting; mặc định là bật update, còn VPS nào ổn định tao
sẽ tự tắt — tức là có logic cập nhật, có nút ấn cập nhật…"*

═══ GIAO DIỆN CHỈ ĐỌC TỆP TRẠNG THÁI VÀ BẤM NÚT ═══

Kiểm (git fetch), quyết định, áp bản mới đều ở `core.cap_nhat_git` /
`core.dong_bo_git`. Ở đây: đọc `workspace/cap-nhat/trang-thai.json` rồi vẽ, và
mỗi nút gọi đúng một hàm ở luồng nền. Áp bản mới luôn là tiến trình TÁCH RỜI
(`dong_bo_git keo`) — nó đóng rồi mở lại chính cửa sổ này, theo luật máy rảnh.

Không còn đường ZIP (`cap-nhat.py`) hay manifest nào ở đây — hai hệ cùng tráo
tệp là cây git bẩn và cả hai cùng hỏng.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QCheckBox, QFrame, QMessageBox, QVBoxLayout, QWidget

from core import cap_nhat_git as cng

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_phu, the

__all__ = ["BangCapNhat", "NutCapNhat", "doc_phien_ban", "khoa_trang_cai_dat"]

#: Giao diện tự gọi `nhip` (kiểm + tự áp khi được phép) mỗi chừng này — bổ sung
#: cho gác tổng 15', để VPS chưa đặt lịch gác tổng vẫn tự nhận bản mới.
NHIP_KIEM_MS = 30 * 60 * 1000
#: Khung Cập nhật đọc lại tệp trạng thái (rẻ: một tệp JSON nhỏ).
NHIP_VE_MS = 30 * 1000

_TEN_KET_QUA = {
    "thanh_cong": "đã cập nhật",
    "da_lui": "cập nhật lỗi, đã tự lùi về bản cũ",
    "da_quay_lai": "đã quay lại bản trước",
    "hong_kiem": "bản mới không qua kiểm, chưa cài",
    "chua_ap": "chưa cập nhật",
    "loi": "lỗi",
}


def doc_phien_ban(base_dir: str) -> str:
    return cng.doc_phien_ban(base_dir)


def khoa_trang_cai_dat(app) -> str:
    """Trang chứa khung Cập nhật: VPS → "he-thong" (Cài đặt), máy nhà → "wallet"."""
    return "he-thong" if getattr(app, "_la_vps", False) else "wallet"


def _gio_gon(chu: str) -> str:
    """"2026-09-30 23:40" → "23:40 30/09"."""
    try:
        ngay, gio = str(chu).split(" ", 1)
        _n, th, d = ngay.split("-")
        return "{0} {1}/{2}".format(gio[:5], d, th)
    except ValueError:
        return str(chu or "?")


def _ngay_gon(ngay: str) -> str:
    """"2026-09-30" → "30/09"."""
    phan = ngay.split("-")
    return "{0}/{1}".format(phan[2], phan[1]) if len(phan) == 3 else ngay


def mo_ta_trang_thai(tt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, str]:
    """Các câu hiện trên khung (hàm thuần — test được không cần Qt)."""
    ra: Dict[str, str] = {}
    ra["hien_tai"] = "Phiên bản hiện tại: {0}".format(tt.get("hien_tai") or "?")
    if tt.get("ban_moi"):
        ra["ban_moi"] = "Bản mới: {0}".format(tt["ban_moi"])
    elif tt.get("kiem_luc") and not tt.get("loi"):
        ra["ban_moi"] = "Đang dùng bản mới nhất."
    else:
        ra["ban_moi"] = ""
    dong = []
    for d in (tt.get("thay_doi") or [])[:12]:
        dong.append("• {0} ({1}, máy {2}): {3}".format(
            d.get("phien_ban"), _ngay_gon(str(d.get("ngay") or "")),
            d.get("may") or "?", d.get("noi_dung") or ""))
    ra["thay_doi"] = "\n".join(dong)
    trang_thai = []
    if tt.get("kiem_luc"):
        trang_thai.append("Kiểm lần cuối: {0}{1}".format(
            _gio_gon(tt["kiem_luc"]), "" if tt.get("kiem_ok", True) else " (chưa nối được GitHub)"))
    c = tt.get("cap_nhat_cuoi") or {}
    if c:
        trang_thai.append("Lần cập nhật gần nhất: {0} — {1}{2}".format(
            _gio_gon(c.get("luc") or ""), _TEN_KET_QUA.get(c.get("ket_qua"), c.get("ket_qua") or "?"),
            (": " + c["chi_tiet"]) if c.get("chi_tiet") else ""))
    if tt.get("ban_moi"):
        if tt.get("quyet") == "cho":
            trang_thai.append("Sẽ tự cập nhật khi máy rảnh — đang chờ: {0}".format(tt.get("quyet_ly_do") or "?"))
        elif tt.get("quyet") == "ap":
            trang_thai.append("Đang cập nhật…")
        elif not cfg.get("tu_dong_cap_nhat") and not tt.get("hen_cap_nhat"):
            trang_thai.append("Tự động cập nhật đang tắt — bấm “Cập nhật ngay” khi tiện.")
        elif tt.get("quyet_ly_do") and tt.get("quyet") == "khong":
            trang_thai.append("Chưa cập nhật: {0}".format(tt["quyet_ly_do"]))
    if tt.get("loi"):
        trang_thai.append(str(tt["loi"]))
    ra["trang_thai"] = "\n".join(trang_thai)
    doi = tt.get("co_sua_chua_day") or []
    if doi or tt.get("so_commit_chua_day"):
        ten = ", ".join(str(d)[3:].strip() for d in doi[:4]) + (" …" if len(doi) > 4 else "")
        ra["sua"] = ("Máy này có sửa chưa đẩy lên kho ({0}). Tool KHÔNG tự cập nhật để khỏi đè "
                     "mất sửa đó: đẩy lên trước, hoặc bỏ các sửa này.").format(
            "{0} tệp: {1}".format(len(doi), ten) if doi else
            "{0} commit chưa đẩy".format(tt.get("so_commit_chua_day")))
    else:
        ra["sua"] = ""
    return ra


class BangCapNhat(QFrame):
    """Khung Cập nhật: phiên bản, bản mới + thay đổi, các nút, công tắc."""

    def __init__(self, app, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self.setObjectName("card")
        theme.bong(self)
        self._app = app
        self._goc = app.base_dir
        self._ban = False

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(6)
        v.addWidget(nhan("Cập nhật tool", "h2"))
        self._nhan_hien_tai = self._chu("")
        self._nhan_hien_tai.setStyleSheet("font-weight:600;")
        v.addWidget(self._nhan_hien_tai)
        self._nhan_ban_moi = self._chu("")
        v.addWidget(self._nhan_ban_moi)
        self._nhan_thay_doi = self._chu("", "phu")
        v.addWidget(self._nhan_thay_doi)

        self._khung_sua = QFrame()
        vs = QVBoxLayout(self._khung_sua)
        vs.setContentsMargins(0, 4, 0, 4)
        self._nhan_sua = self._chu("")
        self._nhan_sua.setStyleSheet("color:{0};font-weight:600;".format(theme.CAM))
        vs.addWidget(self._nhan_sua)
        hs = HangXuongDong()
        hs.addWidget(nut_phu("Đẩy lên kho", self._day_len, rong=150))
        hs.addWidget(nut_phu("Bỏ các sửa này", self._bo_sua, rong=160))
        vs.addLayout(hs)
        v.addWidget(self._khung_sua)

        hang = HangXuongDong()
        self._nut_kiem = nut_phu("Kiểm tra cập nhật", self._kiem, rong=170)
        self._nut_ngay = nut_chinh("Cập nhật ngay", self._cap_nhat_ngay, rong=160)
        self._nut_lui = nut_phu("Quay lại bản trước", self._quay_lai, rong=170)
        for n in (self._nut_kiem, self._nut_ngay, self._nut_lui):
            hang.addWidget(n)
        v.addLayout(hang)

        self._o_tu_dong = QCheckBox("Tự động cập nhật")
        self._o_tu_dong.setChecked(cng.doc_cau_hinh(self._goc)["tu_dong_cap_nhat"])
        self._o_tu_dong.stateChanged.connect(lambda _s: self._doi_tu_dong())
        v.addWidget(self._o_tu_dong)
        mo = self._chu(
            "Bật sẵn. Có bản mới là tool tự cài lúc máy rảnh — không đang đăng, dựng, "
            "làm phụ đề hay quét, và trong khung phút :15–:45 — rồi tự mở lại; bản mới "
            "lỗi thì tự quay về bản cũ. Máy nào đã chạy ổn định muốn giữ nguyên thì "
            "tắt: tool vẫn báo có bản mới, bạn bấm “Cập nhật ngay” khi tiện.", "phu")
        mo.setContentsMargins(24, 0, 0, 6)
        v.addWidget(mo)
        self._nhan_trang_thai = self._chu("", "muted")
        v.addWidget(self._nhan_trang_thai)

        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(self.ve)
        self._dong_ho.start(NHIP_VE_MS)
        self.ve()

    @staticmethod
    def _chu(chu: str, kieu: str = ""):
        nh = nhan(chu, kieu)
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    # ── vẽ ──────────────────────────────────────────────────────────────────

    def ve(self) -> None:
        cfg = cng.doc_cau_hinh(self._goc)
        tt = cng.doc_trang_thai(self._goc)
        tt.setdefault("hien_tai", cng.doc_phien_ban(self._goc))
        mt = mo_ta_trang_thai(tt, cfg)
        self._nhan_hien_tai.setText(mt["hien_tai"])
        self._nhan_ban_moi.setText(mt["ban_moi"] or "Chưa kiểm — bấm “Kiểm tra cập nhật”.")
        self._nhan_ban_moi.setStyleSheet(
            "color:{0};font-weight:600;".format(theme.XANH) if tt.get("ban_moi") else "")
        self._nhan_thay_doi.setText(mt["thay_doi"])
        self._nhan_thay_doi.setVisible(bool(mt["thay_doi"]))
        self._nhan_sua.setText(mt["sua"])
        self._khung_sua.setVisible(bool(mt["sua"]))
        self._nhan_trang_thai.setText(mt["trang_thai"])
        self._nut_ngay.setEnabled(bool(tt.get("ban_moi")) and not self._ban)
        self._nut_kiem.setEnabled(not self._ban)
        self._nut_lui.setEnabled(not self._ban)
        if self._o_tu_dong.isChecked() != cfg["tu_dong_cap_nhat"]:
            self._o_tu_dong.blockSignals(True)
            self._o_tu_dong.setChecked(cfg["tu_dong_cap_nhat"])
            self._o_tu_dong.blockSignals(False)

    # ── nút ─────────────────────────────────────────────────────────────────

    def _chay(self, viec, tieu_de: str, dang: str) -> None:
        if self._ban:
            return
        self._ban = True
        self._nhan_trang_thai.setText(dang)
        self._nut_ngay.setEnabled(False)
        self._nut_kiem.setEnabled(False)
        self._nut_lui.setEnabled(False)

        def xong(kq) -> None:
            self._ban = False
            self.ve()
            cau = kq.get("cau") if isinstance(kq, dict) else kq
            if cau:
                self._app.show_message(tieu_de, str(cau))

        def hong(loi) -> None:
            self._ban = False
            self.ve()
            self._app.show_message(tieu_de, "Có lỗi: {0}: {1}".format(type(loi).__name__, loi))

        self._app.run_bg(viec, on_ok=xong, on_err=hong)

    def _kiem(self) -> None:
        goc = self._goc

        def viec():
            tt = cng.nhip(goc, bat_buoc_kiem=True)
            if tt.get("ban_moi"):
                return {"cau": ""}
            if tt.get("loi"):
                return {"cau": str(tt["loi"])}
            return {"cau": ""}
        self._chay(viec, "Kiểm tra cập nhật", "Đang hỏi kho chung trên GitHub…")

    def _cap_nhat_ngay(self) -> None:
        goc = self._goc
        self._chay(lambda: cng.yeu_cau_cap_nhat_ngay(goc), "Cập nhật", "Đang kiểm lại trước khi cập nhật…")

    def _quay_lai(self) -> None:
        tags = cng.tag_lui(self._goc)
        if not tags:
            self._app.show_message("Quay lại bản trước",
                                   "Chưa có bản trước nào để quay lại — máy này chưa tự cập nhật lần nào.")
            return
        hoi = QMessageBox.question(
            self, "Quay lại bản trước",
            "Đưa tool về bản ngay trước lần cập nhật gần nhất ({0})?\n\n"
            "Tool sẽ đóng rồi mở lại (khi máy rảnh). Bản đang có trên kho sẽ không tự "
            "cài lại cho tới khi có bản mới hơn.".format(tags[0].replace(cng.dbg.TIEN_TO_TAG, "")))
        if hoi != QMessageBox.Yes:
            return
        goc = self._goc
        self._chay(lambda: cng.yeu_cau_quay_lai(goc), "Quay lại bản trước", "Đang chuẩn bị quay lại…")

    def _day_len(self) -> None:
        hoi = QMessageBox.question(
            self, "Đẩy sửa lên kho",
            "Đẩy các sửa của máy này lên kho chung? Tool kiểm mã, quét khoá/bí mật, rồi tự "
            "nâng phiên bản. Mất vài phút; các VPS khác sẽ tự nhận bản này.")
        if hoi != QMessageBox.Yes:
            return
        goc = self._goc

        def viec():
            ma, chu = cng.day_sua_cuc_bo(goc)
            return {"cau": ("Đã đẩy lên kho.\n\n" if ma == 0 else "Chưa đẩy được (mã {0}).\n\n".format(ma)) + chu}
        self._chay(viec, "Đẩy sửa lên kho", "Đang kiểm và đẩy lên kho…")

    def _bo_sua(self) -> None:
        hoi = QMessageBox.question(
            self, "Bỏ các sửa này",
            "Bỏ các sửa chưa đẩy của máy này để tool cập nhật được?\n\n"
            "Không mất hẳn: tôi cất chúng vào git stash, lấy lại được bằng `git stash pop`.")
        if hoi != QMessageBox.Yes:
            return
        goc = self._goc

        def viec():
            ok, chu = cng.bo_sua_cuc_bo(goc)
            return {"cau": chu if ok else "Chưa bỏ được: " + chu}
        self._chay(viec, "Bỏ các sửa này", "Đang cất các sửa…")

    def _doi_tu_dong(self) -> None:
        bat = self._o_tu_dong.isChecked()
        if not cng.dat_tu_dong(self._goc, bat):
            self._app.show_message("Không lưu được", "Không ghi được cap-nhat.json ở thư mục tool.")
        self.ve()


class NutCapNhat:
    """Nút nhỏ (thanh bên máy nhà / thẻ "Bản tool" trên VPS) + nhịp kiểm của giao diện.

    `do_ngam()`: gọi lúc cửa sổ vừa dựng xong — kiểm một lượt ở luồng nền (không
    chặn cửa sổ), rồi mỗi 30 phút gọi `cap_nhat_git.nhip` (tự áp nếu được phép).
    Bấm nút = mở trang Cài đặt tới khung Cập nhật.
    """

    def __init__(self, app):
        self._app = app
        self.nut = nut_phu("Bản {0}".format(doc_phien_ban(app.base_dir) or "?"), self._bam)
        self.nut.setToolTip("Phiên bản tool. Bấm để xem cập nhật (Cài đặt).")
        self._dong_ho: Optional[QTimer] = None

    def do_ngam(self) -> None:
        goc = self._app.base_dir
        self._app.run_bg(lambda: cng.nhip(goc, bat_buoc_kiem=True),
                         on_ok=self._ve, on_err=lambda _l: None)
        if self._dong_ho is None:
            try:
                cha = self._app if isinstance(self._app, QWidget) else None
                self._dong_ho = QTimer(cha)
                self._dong_ho.timeout.connect(self._nhip)
                self._dong_ho.start(NHIP_KIEM_MS)
            except Exception:  # noqa: BLE001 — không có vòng Qt (test) thì thôi
                self._dong_ho = None

    def _nhip(self) -> None:
        goc = self._app.base_dir
        self._app.run_bg(lambda: cng.nhip(goc), on_ok=self._ve, on_err=lambda _l: None)

    def _ve(self, tt) -> None:
        tt = tt if isinstance(tt, dict) else {}
        hien = tt.get("hien_tai") or doc_phien_ban(self._app.base_dir) or "?"
        if tt.get("ban_moi"):
            self.nut.setText("Có bản mới {0}".format(tt["ban_moi"]))
            self.nut.setToolTip("Đang dùng {0}. Bấm để xem thay đổi và cập nhật.".format(hien))
        else:
            self.nut.setText("Bản {0}".format(hien))
            self.nut.setToolTip("Phiên bản tool. Bấm để xem cập nhật (Cài đặt).")

    def _bam(self) -> None:
        mo = getattr(self._app, "show_page", None)
        if mo is not None:
            mo(khoa_trang_cai_dat(self._app))
