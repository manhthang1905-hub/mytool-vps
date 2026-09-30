"""core/bang_thong.py — suất tải kết quả về đĩa, liên tiến trình.

═══ MODULE THUẦN — CHƯA NỐI VÀO LUỒNG SỐNG ═══

Việc 1.6 (phần 2) của `workspace/LO-TRINH-PHAT-HANH-V3.md` (Đợt 1, BẮT BUỘC
xong trước Việc 1.4). Cách nối vào đường tải kết quả của `core/auto_khau.py`
(khâu ảnh/clip/giọng đọc — `_tran_luong_cuc_bo`) ghi ở
`workspace/ban-va/2026-09-29-dot1-khe-uu-tien/GHI-CHU.md`.

═══ VÌ SAO CẦN SEMAPHORE RIÊNG, KHÁC `core/khe.py` ═══

`core/khe.py` xếp hàng theo ƯU TIÊN cho khe "nang" (độc quyền) và "api" (N
làn xin phép CHẠY song song). Tải kết quả về đĩa là một việc khác hẳn: không
cần độc quyền, không cần thứ tự ưu tiên P0..P4 — chỉ cần một TRẦN đơn giản
(mặc định 6 suất toàn máy) để không mở hàng trăm luồng tải cùng lúc bịt kín
đường lên (CLAUDE.md luật 5). Vì vậy đây là một semaphore liên tiến trình
thuần tuý: N tệp suất trong `workspace/khe/tai/`, ai tạo được bằng `O_EXCL`
thì giữ, PID chết thì dọn ngay.

`dang_tam_dung()` đọc `core.khe.trang_thai()` — khi khe "nang" đang giữ việc
`"tai_len"` (một tiến trình khác đang tải lên YouTube qua trình duyệt) thì
TẠM DỪNG mọi suất tải kết quả mới, nhường đường truyền cho việc tải lên đang
chạy (đúng tinh thần CLAUDE.md luật 5 — "vừa bắn ảnh lên vừa tải hàng trăm ảnh
xuống trong cùng 5 phút là bịt kín đường của chính máy này").
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
from typing import Any, Dict, Iterator, Optional

from . import khe

__all__ = [
    "TRAN_MAC_DINH", "duong_thu_muc_tai", "duong_suat", "tran",
    "dang_tam_dung", "giu", "PhienBangThong",
]

TRAN_MAC_DINH = 6
_TRAN_MIN, _TRAN_MAX = 1, 12
_NHIP_KIEM_MAC_DINH_GIAY = 1.0
_TEN_THU_MUC = "tai"


def duong_thu_muc_tai(goc: str) -> str:
    return os.path.join(goc, "workspace", "khe", _TEN_THU_MUC)


def duong_suat(goc: str, i: int) -> str:
    return os.path.join(duong_thu_muc_tai(goc), "suat-{0}.json".format(i))


def tran(goc: str) -> int:
    """Trần số suất tải song song. Mặc định 6; ghi đè được qua
    `workspace/cai-dat.json` khoá `tran_bang_thong` (kẹp 1..12).

    Đọc trực tiếp bằng `json.load`, không qua `core.cai_dat` — cùng lý do với
    `core/khe.py::so_lan_api` (khoá này không nằm trong bảng `MAC_DINH` của
    module đó)."""
    try:
        with open(os.path.join(goc, "workspace", "cai-dat.json"), "r",
                  encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return TRAN_MAC_DINH
    if not isinstance(du, dict) or "tran_bang_thong" not in du:
        return TRAN_MAC_DINH
    try:
        n = int(du["tran_bang_thong"])
    except (TypeError, ValueError):
        return TRAN_MAC_DINH
    return max(_TRAN_MIN, min(_TRAN_MAX, n))


def dang_tam_dung(goc: str) -> bool:
    """`True` nếu khe "nang" (`core/khe.py`) đang giữ việc `"tai_len"` — tạm
    dừng mọi suất tải kết quả mới để nhường đường truyền."""
    giu_nang = khe.trang_thai(goc).get("nang")
    return bool(giu_nang and giu_nang.get("viec") == "tai_len")


def _doc_json(duong: str) -> Optional[Dict[str, Any]]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else None
    except (OSError, ValueError):
        return None


def _tao_suat(duong: str) -> bool:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    try:
        fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as tep:
        json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    return True


def _suat_trong(duong: str) -> bool:
    du = _doc_json(duong)
    if du is None:
        return True
    try:
        pid = int(du.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    if not khe.pid_con_song(pid):
        khe.xoa_tep_ben_vung(duong)
        return True
    return False


def _thu_mot_suat(goc: str) -> Optional[str]:
    for i in range(tran(goc)):
        duong = duong_suat(goc, i)
        if _suat_trong(duong) and _tao_suat(duong):
            return duong
    return None


class PhienBangThong:
    """Một suất tải đang giữ — dùng như context manager, hoặc gọi `nha()`."""

    def __init__(self, duong: str, huy: threading.Event) -> None:
        self._duong = duong
        self.huy = huy
        self._da_nha = False

    def __enter__(self) -> threading.Event:
        return self.huy

    def __exit__(self, *_exc: Any) -> bool:
        self.nha()
        return False

    def nha(self) -> None:
        if self._da_nha:
            return
        self._da_nha = True
        khe.xoa_tep_ben_vung(self._duong)


@contextlib.contextmanager
def giu(goc: str, *, cho_toi_da: Optional[float] = None,
        nhip_kiem_giay: float = _NHIP_KIEM_MAC_DINH_GIAY,
        huy: Optional[threading.Event] = None) -> Iterator[threading.Event]:
    """Xin MỘT suất tải kết quả về đĩa (0..`tran(goc)`-1). Context manager —
    BLOCK tới khi có suất trống VÀ không đang `dang_tam_dung()`, hoặc ném
    `core.khe.KheHetGio`/`core.khe.KheDaHuy`.

    Kiểm lại mỗi `nhip_kiem_giay` giây (mặc định 1 — suất tải quay vòng nhanh
    hơn nhiều so với khe "nang"/"api" của `core/khe.py`, không cần giãn 10s).
    """
    huy_thuc = huy if huy is not None else threading.Event()
    bat_dau = time.time()
    duong_giu: Optional[str] = None
    while duong_giu is None:
        if huy_thuc.is_set():
            raise khe.KheDaHuy("bi huy trong luc cho suat tai ve")
        if not dang_tam_dung(goc):
            duong_giu = _thu_mot_suat(goc)
        if duong_giu is None:
            if cho_toi_da is not None and (time.time() - bat_dau) >= cho_toi_da:
                raise khe.KheHetGio(
                    "cho qua {0:.0f}s van chua co suat tai ve".format(cho_toi_da))
            huy_thuc.wait(max(0.02, nhip_kiem_giay))
    phien = PhienBangThong(duong_giu, huy_thuc)
    try:
        yield huy_thuc
    finally:
        phien.nha()
