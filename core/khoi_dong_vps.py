"""Móc khởi động "chế độ VPS": bật trạm + nuôi ba con `vm/` cùng MyTool.

Gọi ĐÚNG MỘT LẦN từ `shopapi_studio_qt.py`, ngay sau `cua_so.show()` — cùng
nếp với cửa tự bật trạm sẵn có
(`ui_qt.trang_chi_so_ytb.TrangChiSoYTB._tu_bat_luc_mo`, đợi
`QTimer.singleShot` cho giao diện dựng xong hẳn rồi mới đụng tới các trang
con, xem ghi chú ở đó về vì sao không đụng sớm hơn).

Chỉ có tác dụng khi `core.che_do_vps.la_vps(base_dir)` — máy thường (không
VPS) gọi hàm này là không làm gì cả. Mọi lỗi ở đây bị NUỐT: giám sát hỏng
không được chặn tool mở lên, khách vẫn cần dùng được các tab khác.
"""

from __future__ import annotations

import os

__all__ = ["gan_vao_cua_so"]


def _doi_lai_cong(base_dir: str) -> None:
    """Bảo bản TRẠM NỀN (nếu đang chạy) lui, trả cổng 8765 cho giao diện.

    Từ 21/09/2026 trạm còn chạy được KHÔNG CẦN cửa sổ nào (`tram_nen.py`, do
    chó giữ nhà bật lại mỗi khi tool sập). Rất có thể lúc người dùng mở tool
    lên thì bản nền đang giữ cổng — và `tram.bat()` cố ý TỪ CHỐI lùi cổng khi
    thứ đang giữ là một trạm khác của tool (một cổng một chủ, xem
    `ui_qt/tram_chung.py`). Không đòi lại thì giao diện ngồi câm: nút "Bật cổng
    nhận" báo lỗi, tab VPS không có trạm để giao việc.

    Bản GUI được ưu tiên vì nó là bản ĐẦY ĐỦ: có nhãn trạng thái cho người
    nhìn, có danh sách máy thuê lấy từ máy chủ, và có ví để viết hộ bình luận.
    Bản nền chỉ là lưới an toàn cho lúc không ai mở tool.
    """
    try:
        from core import tram_nen  # noqa: PLC0415

        tram_nen.xin_nhuong(base_dir)
    except Exception:  # noqa: BLE001 — đòi hụt thì giao diện vẫn mở, chỉ là chưa có trạm
        pass


def _trang_giu_tram(app):
    """Trang đang giữ `TrangChiSoYTB` bản có trạm, hay `None`.

    Hỏi theo KHOÁ trước (`ui_qt.tram_chung.KHOA_TRANG_GIU_TRAM`), rồi mới quét
    mọi trang. Lối quét không phải cho chắc ăn: từ 21/09/2026 máy VPS chỉ còn
    ba trang và tab "VPS" (`chrome-sach`) không còn tồn tại — bản giữ trạm
    chuyển sang "Máy & Ví" (`ui_qt/trang_may_vi.py`, thuộc tính `chi_so` giữ
    nguyên tên). Chỉ hỏi theo khoá thì trên VPS trạm KHÔNG bao giờ tự bật, mà
    trạm không bật là cả ba con `vm/` ngồi câm.
    """
    from ui_qt.tram_chung import KHOA_TRANG_GIU_TRAM  # noqa: PLC0415

    lay_trang = getattr(app, "trang", None)
    ung_vien = []
    if callable(lay_trang):
        ung_vien.append(lay_trang(KHOA_TRANG_GIU_TRAM))
    tat_ca = getattr(app, "_trang", None)
    if isinstance(tat_ca, dict):
        ung_vien += list(tat_ca.values())
    for trang in ung_vien:
        chi_so = getattr(trang, "chi_so", None) or getattr(trang, "_chi_so", None)
        if getattr(chi_so, "bao_dam_bat", None) is not None:
            return chi_so
    return None


def _bao_dam_tram(app) -> None:
    """Bật cổng nhận của trạm nếu máy này chưa bật — dùng đúng CỬA đã có
    (`TrangChiSoYTB.bao_dam_bat`) thay vì tự mở một `Tram` thứ hai: cửa đó còn
    cập nhật nhãn/nút trên chính tab ấy, và nó là "nguồn sự thật" duy nhất
    tránh mở đôi cổng 8765 (xem `ui_qt.tram_chung`).
    """
    try:
        chi_so = _trang_giu_tram(app)
        bao_dam_bat = getattr(chi_so, "bao_dam_bat", None)
        if callable(bao_dam_bat):
            bao_dam_bat()
    except Exception:  # noqa: BLE001 — tự bật hỏng không được chặn tool
        pass


def _bat_giam_sat(app, base_dir: str) -> None:
    from core import che_do_vps  # noqa: PLC0415

    try:
        thu_muc = che_do_vps.thu_muc_vm(base_dir)
    except Exception:  # noqa: BLE001 — vps.json hỏng/thiếu vm_dir: thôi giám sát
        return
    try:
        from core.giam_sat_vm import GiamSat  # noqa: PLC0415

        giam_sat = getattr(app, "giam_sat_vm", None)
        if giam_sat is None:
            giam_sat = GiamSat(thu_muc)
            app.giam_sat_vm = giam_sat
        giam_sat.bat()
    except Exception:  # noqa: BLE001 — giám sát hỏng không được chặn tool
        pass


def _khoi_dong(app, base_dir: str) -> None:
    from core import che_do_vps  # noqa: PLC0415

    if not che_do_vps.la_vps(base_dir):
        return
    # Thứ tự QUAN TRỌNG: đòi cổng về TRƯỚC, rồi mới bảo giao diện bật trạm.
    # Ngược lại thì `bao_dam_bat()` gặp cổng bận, từ chối, và lúc bản nền lui
    # xong thì không còn ai gọi lại nữa — cổng trống trơn, tệ hơn cả lúc đầu.
    _doi_lai_cong(base_dir)
    _bao_dam_tram(app)
    _bat_giam_sat(app, base_dir)


def gan_vao_cua_so(app, base_dir: str) -> None:
    """Gọi ngay sau `cua_so.show()`. Không làm gì dưới pytest (bộ test
    không được đụng cổng/tiến trình thật, đúng luật `SHOPAPI_TRAM_CONG`/
    `PYTEST_CURRENT_TEST` đã có ở các cửa tự bật khác) hay khi PyQt5 không
    nạp được `QTimer` (đường báo lỗi khởi động vẫn phải chạy trước cả module
    này — xem `shopapi_studio_qt.py`)."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        from PyQt5.QtCore import QTimer  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return
    QTimer.singleShot(1500, lambda: _khoi_dong(app, base_dir))
