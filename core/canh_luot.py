"""Canh LƯỢT SẢN XUẤT tách rời (`tu_chay.py --kenh K --tu-dieu-phoi`) — lượt thừa/đứng im TỰ THOÁT (20/10/2026).

═══ VÌ SAO ═══ Một lượt TL3 mở 19/10 05:00 nằm 30 giờ ở 0% CPU mà vẫn giữ làn `api-0`, trong khi các lượt TL3 mới đã
giành khoá kênh (`CHANNEL/<K>/tu-chay/.khoa`) và làm tiếp đúng lượt dở ấy. Khe chỉ dọn làn của PID CHẾT nên không ai lấy
lại làn; điều phối báo "hết làn API (3/4)" cả buổi. Gốc của việc bị giành: khoá kênh coi là "cũ" sau 12 giờ tính từ lúc
GIÀNH (`tu_chay.KHOA_CU_QUA_GIAY`) dù lượt vẫn sống (chờ kho clip 10–16 giờ là chuyện thường 16–18/10).

═══ LUẬT ═══ Một luồng nền (daemon) của chính lượt, mỗi `NHIP_KIEM_GIAY`:
  * làm tươi khoá kênh của mình (`nhip`) — lượt sống không bao giờ bị coi là khoá cũ;
  * (a) khoá kênh do một PID KHÁC còn sống giữ, giành SAU lúc lượt này bắt đầu → `SO_LAN_BI_THAY` lần liền → thoát;
  * (b) không dòng nhật ký nào suốt `GIO_KHONG_TIEN_TRIEN` giờ → thoát. Đo 20/10: trong một lượt khoảng lặng dài nhất
    ~6 phút; lượt chờ kho clip ghi mỗi 20 phút, chờ khe máy nặng mỗi 5 phút, chờ job mỗi 90 giây — 3 giờ im là treo.
Đang giữ khe máy nặng (`.khoa-may`: dựng/phụ đề/QA) thì HOÃN, không thoát giữa chừng. Thoát = ghi nhật ký, nhả làn API
+ khoá kênh NẾU còn là của mình, rồi `os._exit` (luồng job kẹt không giữ được tiến trình). Không giết tiến trình nào khác.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, Dict, Optional

from . import khe

__all__ = ["danh_dau", "kiem_mot_lan", "bat", "GIO_KHONG_TIEN_TRIEN", "NHIP_KIEM_GIAY", "MA_THOAT_CANH"]

GIO_KHONG_TIEN_TRIEN = 3.0
NHIP_KIEM_GIAY = 300.0
SO_LAN_BI_THAY = 2
MA_THOAT_CANH = 4

_MOC = {"cuoi": time.time()}


def danh_dau(luc: Optional[float] = None) -> None:
    """Lượt vừa có tiến triển (một dòng nhật ký)."""
    _MOC["cuoi"] = time.time() if luc is None else float(luc)


def _doc(duong: str) -> Dict[str, Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _lam_tuoi_khoa(duong: str, du: Dict[str, Any], bay_gio: float) -> None:
    """Ghi `nhip` vào khoá kênh CỦA MÌNH — nguyên tử (tệp tạm + đổi tên), hỏng thì bỏ qua nhịp này."""
    tam = "{0}.{1}.nhip".format(duong, os.getpid())
    try:
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(dict(du, nhip=bay_gio), tep)
        os.replace(tam, duong)
    except OSError:
        try:
            os.remove(tam)
        except OSError:
            pass


def _dang_giu_nang(goc: str, pid: int) -> bool:
    try:
        ai = khe.trang_thai(goc).get("nang") or {}
        return int(ai.get("pid") or 0) == pid
    except Exception:  # noqa: BLE001
        return False


def kiem_mot_lan(goc: str, kenh: str, *, bat_dau: float, trang: Dict[str, Any],
                 bay_gio: Optional[float] = None, pid: Optional[int] = None,
                 cuoi: Optional[float] = None) -> Optional[str]:
    """Một nhịp canh. Trả LÝ DO thoát (chuỗi) hay None. `trang` giữ đếm "bị thay" giữa các nhịp."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    pid = os.getpid() if pid is None else pid
    cuoi = _MOC["cuoi"] if cuoi is None else cuoi
    duong = khe.duong_khoa_kenh(goc, kenh)
    du = _doc(duong)
    try:
        pid_k, bat_dau_k = int(du.get("pid") or 0), float(du.get("bat_dau") or 0.0)
    except (TypeError, ValueError):
        pid_k, bat_dau_k = 0, 0.0
    if pid_k == pid:
        trang["da_giu"] = True
        _lam_tuoi_khoa(duong, du, bay_gio)
    bi_thay = bool(pid_k and pid_k != pid and bat_dau_k > bat_dau + khe.GIAY_LECH_BI_THAY
                   and khe.pid_con_song(pid_k))
    trang["bi_thay"] = int(trang.get("bi_thay") or 0) + 1 if bi_thay else 0
    ly_do = None
    if trang["bi_thay"] >= SO_LAN_BI_THAY:
        ly_do = "khoá kênh {0} đã do lượt khác giữ (PID {1}, từ {2}) — lượt này thừa".format(
            kenh, pid_k, time.strftime("%d/%m %H:%M", time.localtime(bat_dau_k)))
    elif bay_gio - cuoi >= GIO_KHONG_TIEN_TRIEN * 3600:
        ly_do = "không tiến triển {0:.1f} giờ (dòng nhật ký cuối {1})".format(
            (bay_gio - cuoi) / 3600.0, time.strftime("%d/%m %H:%M", time.localtime(cuoi)))
    if ly_do and _dang_giu_nang(goc, pid):
        trang["hoan"] = int(trang.get("hoan") or 0) + 1
        return None
    return ly_do


def _nha_cua_minh(goc: str, kenh: str, pid: int) -> None:
    for _i, duong in khe._cac_tep_lan_api(goc):  # noqa: SLF001
        if int(_doc(duong).get("pid") or 0) == pid:
            khe.xoa_tep_ben_vung(duong)
    duong = khe.duong_khoa_kenh(goc, kenh)
    if int(_doc(duong).get("pid") or 0) == pid:
        khe.xoa_tep_ben_vung(duong)


def bat(goc: str, kenh: str, *, ghi: Callable[[str], None],
        thoat: Callable[[int], Any] = os._exit, nhip: float = NHIP_KIEM_GIAY,
        dung: Optional[threading.Event] = None) -> threading.Thread:
    """Mở luồng canh (daemon). `thoat`/`nhip`/`dung` là seam cho bài kiểm."""
    bat_dau = time.time()
    danh_dau(bat_dau)
    dung = dung or threading.Event()
    trang: Dict[str, Any] = {}

    def _vong() -> None:
        while not dung.wait(nhip):
            try:
                ly_do = kiem_mot_lan(goc, kenh, bat_dau=bat_dau, trang=trang)
            except Exception:  # noqa: BLE001 — canh hỏng một nhịp không được giết lượt
                continue
            if not ly_do:
                continue
            try:
                ghi("[CANH LƯỢT] tự thoát (PID {0}): {1}. Nhả làn API của mình; lượt dở để điều phối nhặt lại."
                    .format(os.getpid(), ly_do))
                khe._ghi_nhat_ky(goc, {"viec_nk": "canh_luot_thoat", "kenh": kenh,  # noqa: SLF001
                                       "pid": os.getpid(), "ly_do": ly_do})
            except Exception:  # noqa: BLE001
                pass
            try:
                _nha_cua_minh(goc, kenh, os.getpid())
            except Exception:  # noqa: BLE001
                pass
            thoat(MA_THOAT_CANH)
            return

    luong = threading.Thread(target=_vong, daemon=True, name="canh-luot")
    luong.start()
    return luong
