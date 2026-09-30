"""core/khe.py — khe tài nguyên liên tiến trình (lớp "nang" và lớp "api").

═══ MODULE THUẦN — CHƯA NỐI VÀO LUỒNG SỐNG ═══

Việc 1.2 của `workspace/LO-TRINH-PHAT-HANH-V3.md` (Đợt 1). File này CHỈ định
nghĩa cơ chế xin/giữ/nhả khe — chưa có nơi nào trong `core/auto_khau.py`,
`core/tu_chay.py`, `vm/agent.py` gọi tới nó. Cách nối cho các việc 1.3b/1.4/1.5
được ghi ở `workspace/ban-va/2026-09-29-dot1-khe-uu-tien/GHI-CHU.md`.

═══ THƯ VIỆN CHUẨN, DÙNG CHUNG CHO `core/` VÀ `vm/` ═══

`vm/agent.py` chỉ được phép dùng thư viện chuẩn (máy ảo không pip-install gì —
xem docstring đầu file đó). Vì vậy file này **cố ý không `import` bất cứ module
`core.*` nào khác** — kể cả khi có hàm trùng logic (`pid_con_song` ở đây lặp
lại đúng thuật toán của `core/tu_chay.py::_pid_con_song` và
`vm/agent.py::_pid_con_song`). Đây là chọn lựa có chủ đích, không phải quên
tái dùng: ba bản giữ cùng một thuật toán, nhưng file nào cũng tự đứng được.

═══ HAI LỚP KHE (chốt ở "Luật điều phối" trong lộ trình) ═══

* **"nang"** — độc quyền, ĐÚNG MỘT tiến trình trên cả máy. Gộp lớp B (máy
  nặng: phụ đề Whisper, dựng FFmpeg, đoạn nối mp3/silencedetect, QA + chép
  gói, kho nhạc nền) và lớp C (trình duyệt: quét Studio, lời thoại, tải lên).
  Tệp giữ nằm ĐÚNG đường cũ `workspace/tu-chay/.khoa-may` — cố ý trùng với
  `core/tu_chay.py::TEN_TEP_KHOA_MAY` và `vm/agent.py::_duong_khoa_may_chung`
  để trong giai đoạn chuyển, khoá do module này tạo vẫn được HAI nơi đó đọc và
  hiểu là "đang có người giữ" (chúng chỉ đọc `pid` + `bat_dau`, còn JSON của
  module này có thêm khoá nhưng đọc bằng `dict.get` nên không vỡ).
* **"api"** — N khe song song, việc chỉ CHỜ máy chủ ShopAPI (không ăn CPU cục
  bộ). N mặc định theo RAM máy, ghi đè được qua `workspace/cai-dat.json`
  (khoá `lan_api`).

═══ HÀNG CHỜ + ƯU TIÊN ═══

Xin khe mà chưa trống thì ghi một "vé" vào `workspace/khe/cho/<pid>-<id>.json`
rồi đứng đợi, cứ mỗi ~10 giây (đọc đĩa cục bộ, không mạng) kiểm lại: khe đó có
đang TRỐNG không (không ai giữ, hoặc người giữ đã CHẾT — kiểm bằng
`pid_con_song`, giành lại NGAY, không có luật "khoá cũ 12 giờ vẫn giành" như
`core/tu_chay.py` cũ) VÀ mình có đang ĐỨNG ĐẦU hàng đợi theo khoá sắp xếp
`(uu_tien, han, luc_xin)` không (so bằng số vé đang chờ có khoá "nhỏ hơn" ít
hơn số khe đang trống — vài khe trống thì vài vé đầu hàng đều được thử). Vé
của tiến trình đã chết bị dọn ngay khi bất kỳ ai liệt kê hàng chờ.

`uu_tien` là số càng NHỎ càng gấp (P0 gấp nhất … P4 nền) — khớp
`core/uu_tien.py` (Việc 1.3a, tính P0–P4 kèm lão hoá). Module này không tự
tính P0–P4, chỉ nhận số ưu tiên caller đưa vào và xếp hàng theo đúng số đó;
muốn khe phản ứng với lão hoá thì caller (1.3b/1.4) tự ghi lại số ưu tiên mới
— mỗi lượt kiểm 10 giây đều đọc lại đĩa, không giữ bộ nhớ đệm nào của vé khác.

═══ TRẦN GIỮ (han_giay) ═══

`giu()` là context manager, yield về một `threading.Event`. Vượt `han_giay`
thì Event này được SET (không giết tiến trình) + ghi nhật ký — nơi gọi tự
kiểm `is_set()` trong vòng lặp của mình để tự dừng việc đang làm, y như nút
Dừng. Truyền sẵn `huy=<Event nút Dừng>` thì module này SET LUÔN đúng Event đó
— mã có sẵn đang kiểm `huy.is_set()` được lợi trần giờ mà không cần sửa gì.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import math
import os
import subprocess
import threading
import time
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

__all__ = [
    "LOP_NANG", "LOP_API", "KheHetGio", "KheDaHuy", "PhienGiu",
    "TEN_TEP_KHOA_NANG", "duong_khoa_nang", "duong_thu_muc_khe", "duong_cho",
    "duong_khoa_api", "duong_nhat_ky", "pid_con_song", "ram_gb", "so_lan_api",
    "giu", "thu_giu", "trang_thai", "xoa_tep_ben_vung", "mo_ta_nguoi_giu",
    "TRAN_API_TONG_MAC_DINH", "tran_api_tong", "duong_thu_muc_job", "giu_job",
    "so_job_dang_giu",
]

LOP_NANG = "nang"
LOP_API = "api"

#: Mỗi bao lâu (giây) một tiến trình đang xếp hàng kiểm lại đĩa — cố định theo
#: thiết kế ("mỗi 10s"); bài kiểm được rút ngắn qua tham số `nhip_kiem_giay`.
NHIP_KIEM_MAC_DINH_GIAY = 10.0

#: Tên tệp khoá lớp "nang" — GIỮ NGUYÊN đường của `core/tu_chay.py` cũ.
TEN_TEP_KHOA_NANG = ".khoa-may"

_TRAN_API_MIN, _TRAN_API_MAX = 1, 4


class KheHetGio(TimeoutError):
    """Chờ quá `cho_toi_da` giây mà vẫn chưa tới lượt giữ khe."""


class KheDaHuy(RuntimeError):
    """`huy` (nút Dừng) bị set trong lúc đang xếp hàng chờ khe."""


# ── Đường dẫn ─────────────────────────────────────────────────────────────


def duong_khoa_nang(goc: str) -> str:
    """`workspace/tu-chay/.khoa-may` — ĐÚNG đường `core/tu_chay.TEN_TEP_KHOA_MAY`
    và `vm/agent._duong_khoa_may_chung()` để mã cũ đọc được khoá module này tạo."""
    return os.path.join(goc, "workspace", "tu-chay", TEN_TEP_KHOA_NANG)


def duong_thu_muc_khe(goc: str) -> str:
    return os.path.join(goc, "workspace", "khe")


def duong_cho(goc: str) -> str:
    return os.path.join(duong_thu_muc_khe(goc), "cho")


def duong_khoa_api(goc: str, i: int) -> str:
    return os.path.join(duong_thu_muc_khe(goc), "api-{0}.json".format(i))


def duong_nhat_ky(goc: str) -> str:
    return os.path.join(duong_thu_muc_khe(goc), "nhat-ky.jsonl")


# ── PID còn sống + RAM (thư viện chuẩn, tự đứng) ────────────────────────────


def pid_con_song(pid: int) -> bool:
    """Tiến trình mang PID này còn sống không.

    Lặp lại đúng thuật toán `core/tu_chay.py::_pid_con_song` /
    `vm/agent.py::_pid_con_song` (xem docstring đầu file — cố ý không import).
    Windows: `OpenProcess` quyền tối thiểu, lùi về `tasklist` nếu ctypes hỏng.
    Nơi khác: `os.kill(pid, 0)`. Hỏi mà lỗi thì coi như CÒN SỐNG — an toàn hơn
    là giành khoá bừa của một tiến trình có thể vẫn đang chạy.
    """
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        except Exception:  # noqa: BLE001
            return True
        return True
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if handle:
            kernel.CloseHandle(handle)
            return True
        ma_loi = ctypes.get_last_error()
        if ma_loi == 5:    # ACCESS_DENIED vẫn chứng minh PID đang tồn tại
            return True
        if ma_loi == 87:   # INVALID_PARAMETER: PID không tồn tại
            return False
    except Exception:  # noqa: BLE001 — còn đường tasklist an toàn phía dưới
        pass
    try:
        ra = subprocess.run(
            ["tasklist", "/FI", "PID eq {0}".format(int(pid)), "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:  # noqa: BLE001
        return True
    if ra.returncode != 0:
        return True
    return str(pid) in (ra.stdout or "")


def ram_gb() -> Tuple[Optional[float], Optional[float]]:
    """`(RAM trống GB, RAM tổng GB)` — chỉ đọc, không bao giờ ném lỗi.

    `None` khi không đo được (máy lạ, quyền bị chặn…) — nơi gọi phải tự lo
    trường hợp thiếu số, không được để cả khối chết theo.
    """
    try:
        if os.name == "nt":
            class _BoNho(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            bo = _BoNho()
            bo.dwLength = ctypes.sizeof(_BoNho)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(bo)):  # type: ignore[attr-defined]
                return (float(bo.ullAvailPhys) / (1024.0 ** 3),
                        float(bo.ullTotalPhys) / (1024.0 ** 3))
            return (None, None)
        trong = float(int(os.sysconf("SC_AVPHYS_PAGES"))
                      * int(os.sysconf("SC_PAGE_SIZE"))) / (1024.0 ** 3)
        tong = float(int(os.sysconf("SC_PHYS_PAGES"))
                     * int(os.sysconf("SC_PAGE_SIZE"))) / (1024.0 ** 3)
        return (trong, tong)
    except (AttributeError, OSError, TypeError, ValueError):
        return (None, None)


def _tinh_lan_api_mac_dinh(ram_tong_gb: Optional[float]) -> int:
    """`clamp(1, 4, floor((RAM_tong_GB - 6) / 3))` — không đo được RAM thì coi
    máy nhỏ (1 làn), an toàn hơn là mở tràn trên một máy chưa biết cỡ."""
    if not ram_tong_gb or ram_tong_gb <= 0:
        return _TRAN_API_MIN
    n = int(math.floor((float(ram_tong_gb) - 6.0) / 3.0))
    return max(_TRAN_API_MIN, min(_TRAN_API_MAX, n))


def so_lan_api(goc: str, *, ram_tong_gb: Optional[float] = None) -> int:
    """Số khe "api" song song. Ưu tiên `workspace/cai-dat.json` khoá `lan_api`
    (kẹp 1..4); thiếu/hỏng thì tính theo RAM tổng máy.

    Đọc `cai-dat.json` TRỰC TIẾP bằng `json.load` — không qua `core.cai_dat`
    (khoá `lan_api` không nằm trong bảng `MAC_DINH` của module đó, và file này
    chủ ý không kéo theo module `core.*` nào khác, xem docstring đầu file).
    """
    try:
        with open(os.path.join(goc, "workspace", "cai-dat.json"), "r",
                  encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        du = None
    if isinstance(du, dict) and "lan_api" in du:
        try:
            n = int(du["lan_api"])
            return max(_TRAN_API_MIN, min(_TRAN_API_MAX, n))
        except (TypeError, ValueError):
            pass
    if ram_tong_gb is None:
        ram_tong_gb = ram_gb()[1]
    return _tinh_lan_api_mac_dinh(ram_tong_gb)


# ── Đọc/ghi tệp JSON nhỏ, atomics ────────────────────────────────────────


def _doc_json(duong: str) -> Optional[Dict[str, Any]]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else None
    except (OSError, ValueError):
        return None


def xoa_tep_ben_vung(duong: str) -> None:
    """`os.remove` nhưng chịu được tệp đang bị giữ thoáng qua (Windows —
    phần mềm diệt vi-rút quét đúng lúc, xem `core/ghi_dia.py` mục cùng bệnh).

    ═══ VÌ SAO CẦN THỬ LẠI Ở ĐÂY ═══

    26/09/2026 (lúc viết bài kiểm việc này): đo thật trên máy này, chạy 10
    luồng tranh 3 khe api mở liên tục, một lượt `os.remove` khi NHẢ khe dính
    `WinError 5` thoáng qua. Không thử lại thì tệp bị bỏ lại TRÊN ĐĨA mãi mãi
    dù coi như "đã nhả" — khe đó coi như KẸT VĨNH VIỄN cho tới khi có ai xoá
    tay, dần dần ăn hết số khe còn lại (đúng triệu chứng "khoá một-mình" đã
    từng dính ở VPS này, xem `CLAUDE.local.md`).

    Public (không dấu gạch dưới) để `core/so_job_chung.py` và
    `core/bang_thong.py` dùng lại thay vì tự chép — hai module đó vốn đã phụ
    thuộc `core.khe`, không phải nhóm cần giữ thư viện chuẩn/tự đứng."""
    doi = 0.05
    for lan in range(6):
        try:
            os.remove(duong)
            return
        except FileNotFoundError:
            return
        except OSError:
            if lan >= 5:
                return  # dọn dẹp cố gắng hết sức — không để lỗi xoá vỡ luồng chính
            time.sleep(doi)
            doi = min(doi * 2, 1.0)


#: Tên cũ, dùng nội bộ trong file này.
_xoa_tep = xoa_tep_ben_vung


#: Windows: `os.replace` có thể ném `WinError 5` thoáng qua khi phần mềm diệt
#: vi-rút đang quét đúng tệp tạm vừa đóng (xem `core/ghi_dia.py`, cùng bệnh —
#: file này CỐ Ý không `import core.ghi_dia` để giữ nguyên tắc thư viện chuẩn,
#: tự đứng, xem docstring đầu file). Thử lại vài lần, giãn dần, là đủ.
def _thay_the_chiu_duoc_khoa_thoang_qua(tam: str, duong: str) -> None:
    doi = 0.05
    for lan in range(6):
        try:
            os.replace(tam, duong)
            return
        except OSError:
            if lan >= 5:
                raise
            time.sleep(doi)
            doi = min(doi * 2, 1.0)


def _ghi_json_nguyen_tu(duong: str, du: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = "{0}.{1}-{2}.tam".format(duong, os.getpid(), threading.get_ident())
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)
    _thay_the_chiu_duoc_khoa_thoang_qua(tam, duong)


def _tao_khoa_doc_quyen(duong: str, noi_dung: Dict[str, Any]) -> bool:
    """`O_CREAT|O_EXCL` — không có khoảng hở đọc-rồi-ghi giữa nhiều tiến trình."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    try:
        fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            json.dump(noi_dung, tep, ensure_ascii=False)
    except OSError:
        return False
    return True


def _khe_trong(duong: str) -> bool:
    """Khe tại `duong` có TRỐNG không — trống nghĩa là chưa có tệp giữ, hoặc
    người giữ đã CHẾT (dọn tệp cũ luôn, giành lại NGAY, không có luật giờ)."""
    du = _doc_json(duong)
    if du is None:
        return True
    pid = 0
    try:
        pid = int(du.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    if not pid_con_song(pid):
        _xoa_tep(duong)
        return True
    return False


def _ghi_nhat_ky(goc: str, muc: Dict[str, Any]) -> None:
    muc = dict(muc)
    muc.setdefault("luc", time.time())
    try:
        duong = duong_nhat_ky(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        # Xoay vòng 5 MB (29/09/2026): nhật ký sống 24/7 không được phình vô hạn;
        # `core.cong_suat.doc_nhat_ky_khe` đọc cả bản `.1`.
        try:
            if os.path.getsize(duong) > 5 * 1024 * 1024:
                os.replace(duong, os.path.join(os.path.dirname(duong), "nhat-ky.1.jsonl"))
        except OSError:
            pass
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write(json.dumps(muc, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ── Hàng chờ + khoá sắp xếp ưu tiên ─────────────────────────────────────────


def _khoa_sap_xep(ve: Dict[str, Any]) -> Tuple[float, float, float]:
    try:
        uu_tien = float(ve.get("uu_tien"))
    except (TypeError, ValueError):
        uu_tien = 2.0
    han = ve.get("han")
    try:
        han = float(han) if han is not None else float("inf")
    except (TypeError, ValueError):
        han = float("inf")
    try:
        luc_xin = float(ve.get("luc_xin") or 0.0)
    except (TypeError, ValueError):
        luc_xin = 0.0
    return (uu_tien, han, luc_xin)


def _duong_ve(goc: str, pid: int, id_ve: str) -> str:
    return os.path.join(duong_cho(goc), "{0}-{1}.json".format(pid, id_ve))


def _liet_ke_ve(goc: str) -> List[Dict[str, Any]]:
    """Liệt kê vé đang chờ — TỰ DỌN vé của tiến trình đã chết trong lúc đọc."""
    thu_muc = duong_cho(goc)
    try:
        ten_tep = os.listdir(thu_muc)
    except OSError:
        return []
    ket_qua: List[Dict[str, Any]] = []
    for ten in ten_tep:
        if not ten.endswith(".json"):
            continue
        duong = os.path.join(thu_muc, ten)
        du = _doc_json(duong)
        if du is None:
            continue
        try:
            pid = int(du.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        if not pid_con_song(pid):
            _xoa_tep(duong)
            continue
        ket_qua.append(du)
    return ket_qua


def _duong_khe_lop(goc: str, lop: str) -> List[str]:
    if lop == LOP_NANG:
        return [duong_khoa_nang(goc)]
    if lop == LOP_API:
        return [duong_khoa_api(goc, i) for i in range(so_lan_api(goc))]
    raise ValueError("lop phai la 'nang' hoac 'api', nhan: {0!r}".format(lop))


def _thu_mot_lan(goc: str, lop: str, viec: str, kenh: str, uu_tien: float,
                 han: Optional[float], han_giay: Optional[float],
                 luc_xin: float) -> Optional[str]:
    """Một lượt thử giành khe. Trả đường dẫn khe vừa giữ được, hay `None`."""
    duong_list = _duong_khe_lop(goc, lop)
    trong = [d for d in duong_list if _khe_trong(d)]
    if not trong:
        return None
    khoa_minh = (float(uu_tien),
                float(han) if han is not None else float("inf"),
                float(luc_xin))
    dung_truoc = sum(1 for v in _liet_ke_ve(goc)
                     if v.get("loai") == lop and _khoa_sap_xep(v) < khoa_minh)
    if dung_truoc >= len(trong):
        return None
    noi_dung = {"pid": os.getpid(), "tid": threading.get_ident(), "nguon": "khe",
                "loai": lop, "viec": viec,
                "kenh": kenh, "uu_tien": uu_tien, "bat_dau": time.time(),
                "han_giay": han_giay}
    for duong in trong:
        if _tao_khoa_doc_quyen(duong, noi_dung):
            return duong
    return None


# ── Tái nhập + mô tả người giữ (vá TỰ KHOÁ CHẾT 29/09/2026) ─────────────────
#
# Sự cố thật 18:36→19:53 ngày 29/09: PID 6668 (`--tat-ca` kiểu CŨ, giữ
# `.khoa-may` = khe "nang" suốt lượt, định dạng `{pid, bat_dau}`) tới khâu phụ
# đề thì xin khe "nang" qua `giu()` — khe thấy người giữ là PID còn sống (CHÍNH
# NÓ) nên chờ mãi; TL2/TL3 xếp hàng sau → cả 3 kênh đứng 77 phút. Luật mới:
# tệp khe "nang" đang thuộc CHÍNH tiến trình xin (định dạng cũ = cả tiến trình;
# định dạng khe = đúng luồng đã giữ) → coi như đã giữ, cho qua ngay, khi nhả
# KHÔNG xoá khoá của người giữ ngoài.


def _minh_dang_giu_nang(goc: str, *, ca_dinh_dang_khe: bool = True) -> bool:
    """`ca_dinh_dang_khe=False` (dùng cho `thu_giu`, không chờ): chỉ nhận khoá kiểu
    CŨ của chính tiến trình — `thu_giu` lồng nhau cùng luồng vẫn trả None như trước
    (không tự khoá chết được vì nó không chờ)."""
    du = _doc_json(duong_khoa_nang(goc))
    if not du:
        return False
    try:
        if int(du.get("pid") or 0) != os.getpid():
            return False
    except (TypeError, ValueError):
        return False
    if du.get("nguon") != "khe":
        return True   # khoá cả tiến trình kiểu cũ (tu_chay/agent) — mọi luồng đều đã có
    if not ca_dinh_dang_khe:
        return False
    try:
        return int(du.get("tid") or 0) == threading.get_ident()
    except (TypeError, ValueError):
        return False


def mo_ta_nguoi_giu(du: Optional[Dict[str, Any]]) -> str:
    """Một câu người đọc được về người giữ khe — hiểu cả định dạng CŨ `{pid, bat_dau}`
    (`core/tu_chay.giu_khoa_may`, `vm/agent`) lẫn định dạng của module này."""
    if not du:
        return "không ai"
    try:
        pid = int(du.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    try:
        tu = time.strftime("%H:%M", time.localtime(float(du.get("bat_dau") or 0))) \
            if du.get("bat_dau") else "?"
    except (TypeError, ValueError, OSError, OverflowError):
        tu = "?"
    if du.get("nguon") == "khe":
        viec = " ".join(x for x in (str(du.get("viec") or ""), str(du.get("kenh") or "")) if x)
        return "PID {0} · {1} · từ {2}".format(pid, viec or "?", tu)
    return "PID {0} (khoá cả lượt kiểu cũ{1}) · từ {2}".format(
        pid, " " + str(du.get("viec")) if du.get("viec") else "", tu)


# ── Giám sát han_giay (không giết, chỉ báo) ─────────────────────────────────


def _bat_giam_sat_han(goc: str, huy: threading.Event, han_giay: Optional[float],
                      lop: str, viec: str, kenh: str
                      ) -> Tuple[threading.Event, Optional[threading.Thread]]:
    dung = threading.Event()
    if not han_giay or han_giay <= 0:
        return dung, None

    def _vong() -> None:
        if dung.wait(float(han_giay)):
            return
        if not huy.is_set():
            huy.set()
        _ghi_nhat_ky(goc, {"viec_nk": "vuot_han", "lop": lop, "viec": viec,
                           "kenh": kenh, "pid": os.getpid(), "han_giay": han_giay})

    luong = threading.Thread(target=_vong, daemon=True, name="khe-giam-sat-han")
    luong.start()
    return dung, luong


def _tat_giam_sat_han(dung: threading.Event, luong: Optional[threading.Thread]) -> None:
    dung.set()
    if luong is not None:
        luong.join(timeout=1.0)


# ── API công khai ────────────────────────────────────────────────────────


@contextlib.contextmanager
def giu(goc: str, lop: str, viec: str, kenh: str = "", uu_tien: float = 2,
        han: Optional[float] = None, han_giay: Optional[float] = None,
        huy: Optional[threading.Event] = None,
        cho_toi_da: Optional[float] = None,
        nhip_kiem_giay: Optional[float] = None) -> Iterator[threading.Event]:
    """Xin và giữ một khe `lop` ("nang" hay "api"). Context manager — BLOCK
    (xếp hàng, kiểm mỗi `nhip_kiem_giay` giây, mặc định 10) tới khi giành
    được, hoặc ném `KheHetGio`/`KheDaHuy`.

    `viec`/`kenh` chỉ để ghi vào tệp giữ + nhật ký (đọc bằng mắt, và để
    `core/bang_thong.py` biết khe "nang" đang giữ việc gì). `uu_tien`/`han` để
    xếp hàng (số `uu_tien` CÀNG NHỎ CÀNG GẤP — khớp `core/uu_tien.py`).

    yield về một `threading.Event` — bị SET khi `han_giay` bị vượt (không giết
    tiến trình, chỉ báo), hoặc khi `huy` (nếu caller tự truyền, ví dụ Event của
    nút Dừng) được set từ bên ngoài. Không truyền `huy` thì module tự tạo một
    Event riêng và trả về đúng Event ấy.
    """
    huy_thuc = huy if huy is not None else threading.Event()
    nhip = nhip_kiem_giay if nhip_kiem_giay is not None else NHIP_KIEM_MAC_DINH_GIAY
    pid = os.getpid()
    if lop == LOP_NANG and _minh_dang_giu_nang(goc):
        # TÁI NHẬP: đã giữ sẵn (xem `_minh_dang_giu_nang`) — không chờ chính mình,
        # nhả cũng không xoá khoá của lớp giữ bên ngoài.
        _ghi_nhat_ky(goc, {"viec_nk": "tai_nhap", "lop": lop, "viec": viec, "kenh": kenh,
                           "pid": pid})
        yield huy_thuc
        return
    id_ve = uuid.uuid4().hex[:8]
    luc_xin = time.time()
    duong_ve = _duong_ve(goc, pid, id_ve)

    _ghi_nhat_ky(goc, {"viec_nk": "xin", "lop": lop, "viec": viec, "kenh": kenh,
                       "uu_tien": uu_tien, "pid": pid, "ram_trong_gb": ram_gb()[0]})
    _ghi_json_nguyen_tu(duong_ve, {"pid": pid, "id": id_ve, "loai": lop,
                                   "viec": viec, "kenh": kenh, "uu_tien": uu_tien,
                                   "han": han, "luc_xin": luc_xin})

    duong_khoa_giu: Optional[str] = None
    try:
        while duong_khoa_giu is None:
            if huy_thuc.is_set():
                raise KheDaHuy("bi huy trong luc xep hang cho khe '{0}'".format(lop))
            duong_khoa_giu = _thu_mot_lan(goc, lop, viec, kenh, uu_tien, han,
                                          han_giay, luc_xin)
            if duong_khoa_giu is not None:
                break
            if cho_toi_da is not None and (time.time() - luc_xin) >= cho_toi_da:
                raise KheHetGio(
                    "cho qua {0:.0f}s van chua toi luot khe '{1}' ({2})".format(
                        cho_toi_da, lop, viec))
            huy_thuc.wait(max(0.05, nhip))
    finally:
        _xoa_tep(duong_ve)

    phut_cho = (time.time() - luc_xin) / 60.0
    _ghi_nhat_ky(goc, {"viec_nk": "duoc", "lop": lop, "viec": viec, "kenh": kenh,
                       "uu_tien": uu_tien, "pid": pid, "phut_cho": phut_cho,
                       "ram_trong_gb": ram_gb()[0]})
    dung_giam_sat, luong_giam_sat = _bat_giam_sat_han(goc, huy_thuc, han_giay,
                                                       lop, viec, kenh)
    try:
        yield huy_thuc
    finally:
        _tat_giam_sat_han(dung_giam_sat, luong_giam_sat)
        _xoa_tep(duong_khoa_giu)
        _ghi_nhat_ky(goc, {"viec_nk": "nha", "lop": lop, "viec": viec, "kenh": kenh,
                           "pid": pid, "ram_trong_gb": ram_gb()[0]})


class PhienGiu:
    """Vé đang giữ một khe — trả về từ `thu_giu()` khi giành được.

    Tự dùng được như context manager (`with phien:`) để nhả khi xong, hoặc gọi
    thẳng `phien.nha()`. `phien.huy` là Event bị set khi vượt `han_giay`.
    """

    def __init__(self, goc: str, duong_khoa: str, lop: str, viec: str, kenh: str,
                huy: threading.Event, han_giay: Optional[float]) -> None:
        self._goc = goc
        self._duong = duong_khoa
        self._lop = lop
        self._viec = viec
        self._kenh = kenh
        self.huy = huy
        self._da_nha = False
        self._dung_giam_sat, self._luong_giam_sat = _bat_giam_sat_han(
            goc, huy, han_giay, lop, viec, kenh)

    def __enter__(self) -> threading.Event:
        return self.huy

    def __exit__(self, *_exc: Any) -> bool:
        self.nha()
        return False

    def nha(self) -> None:
        if self._da_nha:
            return
        self._da_nha = True
        _tat_giam_sat_han(self._dung_giam_sat, self._luong_giam_sat)
        if self._duong:   # rỗng = phiên TÁI NHẬP, khoá thuộc lớp giữ bên ngoài
            _xoa_tep(self._duong)
        _ghi_nhat_ky(self._goc, {"viec_nk": "nha", "lop": self._lop,
                                 "viec": self._viec, "kenh": self._kenh,
                                 "pid": os.getpid(), "ram_trong_gb": ram_gb()[0]})


def thu_giu(goc: str, lop: str, viec: str, kenh: str = "", uu_tien: float = 2,
           han: Optional[float] = None, han_giay: Optional[float] = None
           ) -> Optional[PhienGiu]:
    """MỘT lần thử giành khe `lop`, KHÔNG xếp hàng/chờ — trả `None` ngay nếu
    chưa tới lượt (còn khe trống nhưng có vé ưu tiên hơn đang đợi thì cũng trả
    `None`, để không giành trước người đã xếp hàng bằng `giu()`)."""
    luc_xin = time.time()
    if lop == LOP_NANG and _minh_dang_giu_nang(goc, ca_dinh_dang_khe=False):
        _ghi_nhat_ky(goc, {"viec_nk": "tai_nhap", "lop": lop, "viec": viec, "kenh": kenh,
                           "pid": os.getpid()})
        return PhienGiu(goc, "", lop, viec, kenh, threading.Event(), None)
    duong = _thu_mot_lan(goc, lop, viec, kenh, uu_tien, han, han_giay, luc_xin)
    if duong is None:
        return None
    huy = threading.Event()
    _ghi_nhat_ky(goc, {"viec_nk": "duoc", "lop": lop, "viec": viec, "kenh": kenh,
                       "uu_tien": uu_tien, "pid": os.getpid(), "phut_cho": 0.0,
                       "ram_trong_gb": ram_gb()[0]})
    return PhienGiu(goc, duong, lop, viec, kenh, huy, han_giay)


def trang_thai(goc: str) -> Dict[str, Any]:
    """Ai đang giữ khe nào + hàng đang chờ những gì. Chỉ đọc đĩa, không mạng.

    Trả `{"nang": <tệp giữ hay None>, "api": [<tệp giữ hay None>, ...],
    "cho": [<vé>, ...]}`. Người giữ đã chết bị coi như không giữ (không tự
    xoá tệp ở đây — dọn thật diễn ra đúng lúc có ai đó THỬ giành khe)."""
    giu_nang = _doc_json(duong_khoa_nang(goc))
    if giu_nang is not None:
        try:
            con = pid_con_song(int(giu_nang.get("pid") or 0))
        except (TypeError, ValueError):
            con = False
        if not con:
            giu_nang = None
    api_slots: List[Optional[Dict[str, Any]]] = []
    for i in range(so_lan_api(goc)):
        d = _doc_json(duong_khoa_api(goc, i))
        if d is not None:
            try:
                con = pid_con_song(int(d.get("pid") or 0))
            except (TypeError, ValueError):
                con = False
            if not con:
                d = None
        api_slots.append(d)
    cho = sorted(_liet_ke_ve(goc), key=_khoa_sap_xep)
    return {"nang": giu_nang, "api": api_slots, "cho": cho}


# ── Khe JOB toàn máy (30/09/2026, gỡ trần ảnh/clip) ─────────────────────────
#
# Lớp "api" ở trên là số LƯỢT sản xuất chạy song song (mỗi lượt một kênh).
# Trong một lượt, khâu ảnh/clip lại mở N luồng, mỗi luồng giữ đúng MỘT job
# đang chờ máy chủ (`che_do_vps.tran_api_vps`, vd 24/kênh). N kênh cộng lại
# thì phải có một trần TOÀN MÁY nữa, để 4 kênh × 24 không vượt trần máy chủ
# khai ở `GET /v1/me` (`concurrent_jobs.<loại>` — ĐỘNG theo số khách, từng
# xuống 1 lúc 16:25 ngày 30/09).
#
# Cơ chế giống `core/bang_thong.py`: N tệp suất `workspace/khe/job/<loại>/<i>.json`,
# ai tạo được bằng `O_EXCL` thì giữ, PID chết thì dọn. N = min(`tran_api_tong`,
# trần máy chủ đưa vào). Không mạng, không hỏi máy chủ ở đây — nơi gọi truyền
# trần máy chủ (đã có TTL) vào.

#: Trần tổng số job chờ máy chủ cả máy, mỗi loại job, khi `cai-dat.json` chưa
#: có khoá `tran_api_tong`. 96 = 4 làn × 24, vẫn dưới trần ảnh 189 đo 30/09.
TRAN_API_TONG_MAC_DINH = 96
_TRAN_API_TONG_MIN, _TRAN_API_TONG_MAX = 1, 512
#: Suất giữ quá ngần này giây thì coi như mồ côi dù PID "còn sống" (Windows tái
#: dùng PID). Một việc ảnh+clip dài nhất (4 ứng viên + đặt lại clip) vẫn dưới.
_TUOI_SUAT_JOB_TOI_DA = 6 * 3600.0
#: Dọn suất của tiến trình chết tối đa mỗi ngần này giây mỗi tiến trình — quét
#: cả trăm tệp mỗi nhịp chờ của mỗi luồng là phí đĩa vô ích.
_NHIP_DON_JOB_GIAY = 30.0
_DON_JOB: Dict[str, float] = {}
_KHOA_DON_JOB = threading.Lock()


def tran_api_tong(goc: str) -> int:
    """`workspace/cai-dat.json: tran_api_tong` (mặc định 96, kẹp 1..512).
    Tệp thiếu/hỏng/không phải số → mặc định, không bao giờ ném lỗi."""
    try:
        with open(os.path.join(goc, "workspace", "cai-dat.json"), "r",
                  encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return TRAN_API_TONG_MAC_DINH
    if not isinstance(du, dict) or "tran_api_tong" not in du:
        return TRAN_API_TONG_MAC_DINH
    try:
        n = int(du["tran_api_tong"])
    except (TypeError, ValueError):
        return TRAN_API_TONG_MAC_DINH
    return max(_TRAN_API_TONG_MIN, min(_TRAN_API_TONG_MAX, n))


def _ten_loai_an_toan(loai: str) -> str:
    ten = "".join(ch for ch in str(loai or "") if ch.isalnum() or ch in "-_")
    return ten or "khac"


def duong_thu_muc_job(goc: str, loai: str) -> str:
    return os.path.join(duong_thu_muc_khe(goc), "job", _ten_loai_an_toan(loai))


def _suat_job_con_song(duong: str, bay_gio: float) -> bool:
    du = _doc_json(duong)
    if du is None:
        # Vừa tạo mà chưa ghi xong JSON (O_EXCL rồi mới ghi) — coi như đang giữ.
        try:
            return (bay_gio - os.path.getmtime(duong)) < 60.0
        except OSError:
            return False
    try:
        pid = int(du.get("pid") or 0)
        bat_dau = float(du.get("bat_dau") or 0.0)
    except (TypeError, ValueError):
        return False
    if bat_dau and bay_gio - bat_dau > _TUOI_SUAT_JOB_TOI_DA:
        return False
    return pid_con_song(pid)


def _don_suat_job(goc: str, loai: str, ep: bool = False) -> None:
    """Xoá suất của tiến trình đã chết / suất mồ côi. Tối đa mỗi 30 giây."""
    khoa = _ten_loai_an_toan(loai)
    bay_gio = time.time()
    with _KHOA_DON_JOB:
        if not ep and bay_gio - _DON_JOB.get(khoa, 0.0) < _NHIP_DON_JOB_GIAY:
            return
        _DON_JOB[khoa] = bay_gio
    thu_muc = duong_thu_muc_job(goc, loai)
    try:
        ten_tep = os.listdir(thu_muc)
    except OSError:
        return
    for ten in ten_tep:
        if not ten.endswith(".json"):
            continue
        duong = os.path.join(thu_muc, ten)
        if not _suat_job_con_song(duong, bay_gio):
            _xoa_tep(duong)


def so_job_dang_giu(goc: str, loai: str) -> int:
    """Số suất job `loai` đang có người sống giữ (chỉ đọc, để báo/kiểm)."""
    thu_muc = duong_thu_muc_job(goc, loai)
    try:
        ten_tep = os.listdir(thu_muc)
    except OSError:
        return 0
    bay_gio = time.time()
    return sum(1 for ten in ten_tep if ten.endswith(".json")
               and _suat_job_con_song(os.path.join(thu_muc, ten), bay_gio))


def _thu_giu_job(goc: str, loai: str, n: int, viec: str) -> Optional[str]:
    thu_muc = duong_thu_muc_job(goc, loai)
    noi_dung = {"pid": os.getpid(), "tid": threading.get_ident(),
                "loai": loai, "viec": viec, "bat_dau": time.time()}
    # Bắt đầu ở một chỗ ngẫu nhiên: cả trăm luồng cùng quét từ 0 thì luồng nào
    # cũng đụng đúng các tệp đầu.
    dau = int.from_bytes(os.urandom(2), "little") % max(1, n)
    for k in range(n):
        duong = os.path.join(thu_muc, "{0}.json".format((dau + k) % n))
        if _tao_khoa_doc_quyen(duong, noi_dung):
            return duong
    return None


@contextlib.contextmanager
def giu_job(goc: str, loai: str, *, tran_may_chu: int = 0, viec: str = "",
            huy: Optional[threading.Event] = None,
            kiem_dung: Optional[Callable[[], None]] = None,
            cho_toi_da: Optional[float] = None,
            nhip_kiem_giay: float = 2.0) -> Iterator[int]:
    """Giữ MỘT suất job `loai` toàn máy trong lúc job ấy chờ máy chủ.

    Số suất = min(`tran_api_tong(goc)`, `tran_may_chu`) (`tran_may_chu` ≤ 0 =
    không biết → chỉ theo `tran_api_tong`). Hết suất thì đợi (mỗi
    `nhip_kiem_giay` giây, đọc đĩa cục bộ, không mạng). `kiem_dung()` được gọi
    mỗi nhịp — nó ném gì (nút Dừng) thì ném nguyên lên. Quá `cho_toi_da` →
    `KheHetGio`; `huy` set → `KheDaHuy`. yield về số suất đang áp.
    """
    n = tran_api_tong(goc)
    try:
        if int(tran_may_chu or 0) > 0:
            n = min(n, int(tran_may_chu))
    except (TypeError, ValueError):
        pass
    n = max(1, n)
    bat_dau = time.time()
    duong: Optional[str] = None
    while duong is None:
        if kiem_dung is not None:
            kiem_dung()
        if huy is not None and huy.is_set():
            raise KheDaHuy("bi huy trong luc cho suat job '{0}'".format(loai))
        duong = _thu_giu_job(goc, loai, n, viec)
        if duong is not None:
            break
        _don_suat_job(goc, loai)
        duong = _thu_giu_job(goc, loai, n, viec)
        if duong is not None:
            break
        if cho_toi_da is not None and (time.time() - bat_dau) >= cho_toi_da:
            raise KheHetGio("cho qua {0:.0f}s van chua co suat job '{1}'".format(
                cho_toi_da, loai))
        # Giãn ngẫu nhiên ±25% để cả trăm luồng đợi không thức dậy cùng nhịp.
        gian = max(0.02, float(nhip_kiem_giay)) * (
            0.75 + (int.from_bytes(os.urandom(1), "little") / 255.0) * 0.5)
        if huy is not None:
            huy.wait(gian)
        else:
            time.sleep(gian)
    try:
        yield n
    finally:
        _xoa_tep(duong)
