"""Sổ thời gian job ShopAPI THÀNH CÔNG + trần chờ ẢNH THÍCH NGHI (20/10/2026).

═══ VÌ SAO ═══ Trần chờ một job cố định `auto_khau.TRAN_CHO_JOB` = 12 phút. Đo 20/10/2026 (`tu-chay.log` cả ngày): 1.806
lượt chờ ảnh chạm đúng mốc 11–12 phút rồi "nhận việc rồi bỏ đó — đặt lại bằng khoá mới" (máy chủ treo job, chính máy chủ
tự đánh `failed` sau ~20 phút), trong khi job ảnh THÀNH CÔNG ở máy chủ (`completed_at − created_at`, 369 job trong sổ
job chung) có p50 71 giây, p90 107 giây, p99 ~3,5 phút. Đợi job treo đủ 12 phút × 3 lần mỗi vòng cảnh là ~80 giờ
luồng/ngày đứng chờ suông. Chủ: "tiền không giới hạn, vài job trùng chấp nhận được, giờ phí thì không".

═══ LUẬT ═══ Mỗi job xong ghi một mẫu (giây) vào `workspace/khe/thoi-gian-job.json` (giữ `GIU_TOI_DA` mẫu mới nhất mỗi
loại; nhiều tiến trình ghi qua khoá tệp ngắn, giành không được thì BỎ mẫu đó — sổ chỉ là số đo). Trần chờ job ẢNH =
kẹp(`HE_SO_P90` × p90, 3 phút, 12 phút); chưa đủ `SO_MAU_TOI_THIEU` mẫu → `TRAN_ANH_CHUA_DU_MAU` (5 phút). Clip/giọng đọc
GIỮ trần cũ (clip là chỗ "cứu cảnh" khác hẳn; số đo của chúng vẫn ghi để quyết sau).
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

__all__ = ["ghi", "doc", "p90", "tran_cho_anh", "giay_cua_job", "duong_so"]

GIU_TOI_DA = 300
SO_MAU_TOI_THIEU = 30
HE_SO_P90 = 4.0
TRAN_ANH_MIN_GIAY, TRAN_ANH_MAX_GIAY = 3 * 60.0, 12 * 60.0
TRAN_ANH_CHUA_DU_MAU = 5 * 60.0
#: Tính lại trần mỗi tiến trình tối đa mỗi ngần này giây (đọc đĩa rẻ nhưng mỗi cảnh đều hỏi).
_TTL_GIAY = 60.0
_KHOA_LUONG = threading.Lock()
_DEM: Dict[str, Any] = {}


def duong_so(goc: str) -> str:
    return os.path.join(goc, "workspace", "khe", "thoi-gian-job.json")


def doc(goc: str) -> Dict[str, List[float]]:
    try:
        with open(duong_so(goc), "r", encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {}
    if not isinstance(du, dict):
        return {}
    ra: Dict[str, List[float]] = {}
    for k, v in du.items():
        if isinstance(v, list):
            ra[str(k)] = [float(x) for x in v if isinstance(x, (int, float)) and x > 0]
    return ra


def _giu_khoa(duong: str) -> bool:
    for _lan in range(20):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(duong) > 10.0:   # người giữ chết giữa chừng
                    os.remove(duong)
                    continue
            except OSError:
                pass
            time.sleep(0.05)
        except OSError:
            return False
    return False


def ghi(goc: str, loai: str, giay: float) -> bool:
    """Thêm một mẫu `giay` cho `loai` ("image"/"video"/"tts"). Trả False nếu bỏ mẫu (khoá bận, đĩa hỏng)."""
    try:
        giay = float(giay)
    except (TypeError, ValueError):
        return False
    if not goc or not loai or giay <= 0:
        return False
    duong = duong_so(goc)
    khoa = duong + ".lock"
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
    except OSError:
        return False
    if not _giu_khoa(khoa):
        return False
    try:
        du = doc(goc)
        ds = du.get(loai, []) + [round(giay, 1)]
        du[loai] = ds[-GIU_TOI_DA:]
        from .ghi_dia import ghi_json  # noqa: PLC0415

        ghi_json(duong, du, indent=None)
        return True
    except Exception:  # noqa: BLE001 — sổ đo hỏng không được làm hỏng job vừa xong
        return False
    finally:
        try:
            os.remove(khoa)
        except OSError:
            pass


def p90(ds: List[float]) -> Optional[float]:
    if not ds:
        return None
    s = sorted(ds)
    return s[min(len(s) - 1, int(0.9 * len(s)))]


def tran_cho_anh(goc: str, *, bay_gio: Optional[float] = None) -> float:
    """Trần chờ (giây) một job ẢNH: kẹp(4 × p90 mẫu gần nhất, 3', 12'); < 30 mẫu → 5'."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    with _KHOA_LUONG:
        cu = _DEM.get(goc)
        if cu and 0.0 <= bay_gio - cu[0] < _TTL_GIAY:
            return cu[1]
    ds = doc(goc).get("image", []) if goc else []
    if len(ds) < SO_MAU_TOI_THIEU:
        tran = TRAN_ANH_CHUA_DU_MAU
    else:
        tran = max(TRAN_ANH_MIN_GIAY, min(TRAN_ANH_MAX_GIAY, HE_SO_P90 * float(p90(ds) or 0.0)))
    with _KHOA_LUONG:
        _DEM[goc] = (bay_gio, tran)
    return tran


def _gio_iso(chu: Any) -> Optional[float]:
    import datetime as _dt  # noqa: PLC0415

    try:
        return _dt.datetime.fromisoformat(str(chu).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def giay_cua_job(goi: Any, du_phong: float) -> float:
    """Thời gian job ở MÁY CHỦ (`completed_at − created_at`) nếu gói có; không thì `du_phong` (đo phía máy)."""
    if isinstance(goi, dict):
        a, b = _gio_iso(goi.get("created_at")), _gio_iso(goi.get("completed_at"))
        if a is not None and b is not None and b > a:
            return b - a
    return float(du_phong)
