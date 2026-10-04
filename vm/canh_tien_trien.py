"""Luồng canh tiến triển cho tiến trình con (nuôi trang chủ, thiết lập kênh) — 04/10/2026.

Sự cố 04/10: các tiến trình con đứng im hàng giờ giữa một dòng log, không nhả Chrome. Mỗi nơi có tiến triển thật
(ghi log, một lệnh CDP trả về) gọi `danh_dau()`; quá `han_giay` mà không ai gọi → đóng Chrome kênh rồi `os._exit`.
Chỉ dùng thư viện chuẩn.
"""
import os
import threading
import time

HAN_MAC_DINH_GIAY = 15 * 60
MA_TREO = 7
_LUC = [time.monotonic()]


def danh_dau() -> None:
    _LUC[0] = time.monotonic()


def tuoi_giay() -> float:
    return time.monotonic() - _LUC[0]


def kiem_mot_lan(han_giay, dong_chrome, thoat=os._exit, ghi=None) -> bool:
    """Quá hạn không tiến triển → ghi, đóng Chrome (lỗi cũng bỏ qua), thoát. Trả True nếu đã thoát."""
    t = tuoi_giay()
    if t <= han_giay:
        return False
    try:
        if ghi:
            ghi("TREO: {0:.0f} phút không tiến triển — tự đóng Chrome kênh rồi thoát".format(t / 60.0))
    except Exception:  # noqa: BLE001
        pass
    try:
        dong_chrome()
    except Exception:  # noqa: BLE001
        pass
    thoat(MA_TREO)
    return True


def bat_canh(dong_chrome, han_giay=HAN_MAC_DINH_GIAY, ghi=None, chu_ky=30.0, thoat=os._exit, ngu=time.sleep):
    """Bật luồng nền (daemon). Trả luồng."""
    danh_dau()

    def chay():
        while True:
            ngu(chu_ky)
            if kiem_mot_lan(han_giay, dong_chrome, thoat, ghi):
                return
    t = threading.Thread(target=chay, name="canh-tien-trien", daemon=True)
    t.start()
    return t
