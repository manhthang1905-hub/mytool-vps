"""Không để tiến trình con của tool sống sót sau khi tool tắt — kiểu gì cũng không.

═══ VÌ SAO ═══

Chủ dự án, 24/08/2026: *"khi tắt tool là mọi thứ tắt hoặc khi bật tool nó cũng
có logic tắt để không có gì kiểu rác zombie"*.

Tool đẻ ra rất nhiều tiến trình con: `ffmpeg` (dựng, dọn dấu), bộ nghe whisper
(tiến trình riêng, xem `core/nghe_ngoai.py`), `yt-dlp`, `pip`, và từ 24/08 là
`claude` (viết kịch bản bằng thuê bao). Mỗi chỗ tự `kill()` khi khách bấm
Dừng — nhưng khách **đóng cửa sổ** hay tool **sập** thì không ai gọi `kill()`
cho ai. Đo thật 24/08: giết tiến trình chạy thử giữa lúc `claude` đang viết,
`claude.exe` vẫn chạy nốt lượt của nó thêm bảy phút, không ai nhìn thấy.

═══ CÁCH LÀM: MỘT CHỖ, PHỦ MỌI CON ═══

Trên Windows có **Job Object**: tool tự đưa mình vào một job có cờ
*kill-on-close*. Mọi tiến trình con cháu sinh ra sau đó **tự động** thuộc job
ấy (thừa hưởng, không cần sửa từng chỗ `Popen`). Khi tiến trình tool biến mất
— đóng bình thường, `os._exit`, crash, Task Manager, mất điện thì không tính —
Windows đóng handle job và **giết sạch** mọi thành viên còn sống. Không cần
`atexit`, không cần sổ sách, không cần tin vào việc mã dọn dẹp có kịp chạy.

Ngoại lệ, và phải có ngoại lệ vì hai lý do trái ngược nhau:

* **Tiến trình tự cập nhật** (`ui_qt/cap_nhat.py`) phải SỐNG sau khi tool
  tắt — nó đợi tool chết rồi mới tráo thư mục và mở lại tool. Giết nó là cập
  nhật không bao giờ xong.
* **VS Code / cửa sổ dòng lệnh mở từ tab Agent** là thứ khách đang làm việc.
  VS Code chỉ có MỘT tiến trình cho cả máy: nếu nó được tool mở lên, đóng tool
  là đóng luôn mọi cửa sổ VS Code của khách, kể cả dự án khác.

Hai loại ấy được sinh ra với cờ `CO_TACH_KHOI_JOB` (CREATE_BREAKAWAY_FROM_JOB)
— job được lập với `BREAKAWAY_OK` nên chúng thoát ra hợp lệ.

═══ LỚP THỨ HAI: SỔ GHI VÀ DỌN XÁC LÚC MỞ ═══

Job Object là lưới chính. Sổ `workspace/tien-trinh-con.json` là lưới phụ cho
những tiến trình dài mà tool tự ghi nhận (`ghi_nhan`): lúc mở tool, `don_xac_cu`
đọc sổ và giết tiến trình nào còn sống **và đúng là nó** — so cả mã tiến trình
lẫn **giờ tạo** (Windows tái dùng mã tiến trình rất nhanh; chỉ so mã là có ngày
giết nhầm chương trình khác của khách). Ngoài Windows, Job Object không có, nên
sổ này là lưới duy nhất; ở đó chỉ giết khi mã tiến trình còn sống và giờ tạo
khớp theo `time.time()` ghi lúc sinh.

═══ CHỦ SỞ HỮU (`chu`) — SỔ NÀY DÙNG CHUNG VỚI SẢN XUẤT, 29/09/2026 ═══

Sổ này KHÔNG chỉ của giao diện: `core/viet_max.py` (khâu viết kịch bản của
`core/tu_chay.py`, chạy như một tiến trình `tu_chay.py` TÁCH RỜI qua lịch
Windows/`core/dieu_phoi.py`, không chung tiến trình với giao diện) cũng gọi
`ghi_nhan` để tiến trình `claude` nó sinh ra được Job Object phủ nếu chẳng may
`tu_chay.py` chết bất ngờ. Trước 29/09/2026, `don_xac_cu` — chạy lúc GIAO DIỆN
mở lên — giết MỌI mục trong sổ này không phân biệt ai ghi: mở giao diện giữa
lúc `tu_chay.py` đang viết kịch bản thật (tiến trình `claude` còn sống, chưa
kịp `bo_ghi_nhan`) là giết đúng lượt sản xuất đang chạy, không ai biết vì sao
(chẩn đoán 29/09/2026, xem `workspace/THIET-KE-BANG-DIEU-KHIEN.md` mục 6 và
`workspace/ban-va/2026-09-29-tu-canh-loi/GHI-CHU.md`).

Từ bản vá này, `ghi_nhan` ghi thêm trường `chu`: `"gui"` (tiến trình do CHÍNH
giao diện — `ui_qt/app.py` — sinh ra khi khách bấm một việc) hay `"tu_chay"`
(tiến trình của một lượt `tu_chay.py --tat-ca`/`--dieu-phoi` TÁCH RỜI đang
chạy, đúng như `viet_max.py` gọi). Không truyền `chu` thì tự đoán qua
`sys.argv[0]` của TIẾN TRÌNH ĐANG GHI (không phải tiến trình con) — đang chạy
`tu_chay.py` thì ghi `"tu_chay"`, còn lại ghi `"gui"`; cách đoán này KHÔNG cần
sửa `core/viet_max.py`/`core/tu_chay.py` (ngoài quyền sở hữu của bản vá này) vì
tiến trình `tu_chay.py --tat-ca`/`--dieu-phoi` luôn có `sys.argv[0]` kết thúc
bằng `tu_chay.py`, còn giao diện luôn chạy từ `shopapi_studio_qt.py`.

`don_xac_cu` (lúc giao diện mở) từ nay CHỈ giết mục `chu == "gui"`. Mục có
`chu == "tu_chay"` (hay bất kỳ giá trị nào khác `"gui"`) được GIỮ NGUYÊN —
đúng tiến trình tách rời, Job Object của giao diện không phủ nó, và nó nên
sống hết lượt của mình dù giao diện có đóng/mở lại bao nhiêu lần. Mục SỔ CŨ
(ghi trước bản vá này, không có trường `chu`) chỉ bị giết khi **tiến trình
CHA của nó đã chết** (`_ppid` + `con_song`, không có tao_luc để so nên đây là
best-effort trên dữ liệu di trú, không phải luật chính) — coi là "mồ côi thật
sự", không phải một lượt `tu_chay.py` còn cha đang sống canh nó.
"""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

__all__ = ["CO_TACH_KHOI_JOB", "vao_job_ket_thuc_cung_tool", "ghi_nhan",
           "bo_ghi_nhan", "dung_tat_ca", "don_xac_cu", "con_song", "giet_pid",
           "TEN_SO", "CHU_GUI", "CHU_TU_CHAY"]

#: Giá trị trường `chu` — xem "CHỦ SỞ HỮU" ở docstring đầu tệp.
CHU_GUI = "gui"
CHU_TU_CHAY = "tu_chay"

#: Cờ `creationflags` cho tiến trình con **phải sống lâu hơn tool**.
#: = `CREATE_BREAKAWAY_FROM_JOB`. Ngoài Windows là 0 (không có nghĩa, vô hại).
CO_TACH_KHOI_JOB = 0x01000000 if os.name == "nt" else 0

#: Sổ ghi tiến trình con dài hạn, trong `workspace/`.
TEN_SO = "tien-trinh-con.json"

_KHOA = threading.Lock()
#: Tiến trình đang sống mà tool tự ghi nhận: pid → Popen.
_DANG_SONG: Dict[int, Any] = {}
#: Handle job — giữ suốt đời tiến trình, KHÔNG BAO GIỜ đóng: đóng là job tan.
_JOB: Optional[int] = None


# ── Windows ──────────────────────────────────────────────────────────────────

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [(t, ctypes.c_ulonglong) for t in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BASIC_LIMIT),
                    ("IoInfo", _IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _JobObjectExtendedLimitInformation = 9
    _LIMIT_BREAKAWAY_OK = 0x00000800
    _LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259

    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                             ctypes.c_void_p, wintypes.DWORD]
    _k32.SetInformationJobObject.restype = wintypes.BOOL
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.GetCurrentProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)] * 4
    _k32.GetProcessTimes.restype = wintypes.BOOL
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE,
                                        ctypes.POINTER(wintypes.DWORD)]
    _k32.GetExitCodeProcess.restype = wintypes.BOOL
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateProcess.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL

    def _gio_tao_theo_handle(handle: int) -> int:
        tao, thoat, nhan, nguoi = (wintypes.FILETIME() for _ in range(4))
        if not _k32.GetProcessTimes(handle, ctypes.byref(tao), ctypes.byref(thoat),
                                    ctypes.byref(nhan), ctypes.byref(nguoi)):
            return 0
        return (tao.dwHighDateTime << 32) | tao.dwLowDateTime

    def _mo(pid: int, quyen: int) -> Optional[int]:
        h = _k32.OpenProcess(quyen, False, int(pid))
        return h or None

    _TH32CS_SNAPPROCESS = 0x00000002

    class _PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    _k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _k32.Process32FirstW.argtypes = [wintypes.HANDLE,
                                     ctypes.POINTER(_PROCESSENTRY32W)]
    _k32.Process32FirstW.restype = wintypes.BOOL
    _k32.Process32NextW.argtypes = [wintypes.HANDLE,
                                    ctypes.POINTER(_PROCESSENTRY32W)]
    _k32.Process32NextW.restype = wintypes.BOOL

    def _ppid_windows(pid: int) -> Optional[int]:
        """PID cha của `pid` (Toolhelp snapshot). `None` = không tìm thấy/lỗi."""
        snap = _k32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if not snap or snap == wintypes.HANDLE(-1).value:
            return None
        try:
            entry = _PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
            if not _k32.Process32FirstW(snap, ctypes.byref(entry)):
                return None
            while True:
                if entry.th32ProcessID == pid:
                    return int(entry.th32ParentProcessID)
                if not _k32.Process32NextW(snap, ctypes.byref(entry)):
                    return None
        finally:
            _k32.CloseHandle(snap)


def _ppid(pid: int) -> Optional[int]:
    """PID tiến trình CHA của `pid`. `None` khi không xác định được (ngoài
    Windows, hoặc tiến trình đã thoát/lỗi hệ thống) — nơi gọi coi `None` là
    "không rõ", KHÔNG PHẢI "cha đã chết" (xem `don_xac_cu`)."""
    if os.name != "nt":
        return None
    try:
        return _ppid_windows(int(pid))
    except Exception:  # noqa: BLE001
        return None


def _chu_mac_dinh() -> str:
    """`chu` mặc định khi `ghi_nhan` không được truyền — đoán qua tiến trình
    ĐANG GHI (không phải tiến trình con), xem "CHỦ SỞ HỮU" ở docstring đầu
    tệp: đang chạy `tu_chay.py` (mọi chế độ: `--tat-ca`/`--dieu-phoi`/`--thu`)
    thì ghi `"tu_chay"`, còn lại (giao diện, CLI khác) ghi `"gui"`."""
    try:
        ten = os.path.basename(str(sys.argv[0] or "")).lower()
    except (IndexError, TypeError):
        return CHU_GUI
    return CHU_TU_CHAY if ten == "tu_chay.py" else CHU_GUI


def vao_job_ket_thuc_cung_tool() -> bool:
    """Đưa CHÍNH tiến trình này vào job *kill-on-close*. Gọi một lần lúc mở tool.

    Trả về `True` khi đã vào job (hoặc đã vào từ trước). Ngoài Windows, hoặc
    khi hệ thống không cho (rất hiếm — Windows 7 không cho job lồng nhau), trả
    về `False`; tool vẫn chạy bình thường, chỉ mất lưới chính, còn lưới phụ
    (`don_xac_cu`) vẫn hoạt động.
    """
    global _JOB
    if os.name != "nt":
        return False
    with _KHOA:
        if _JOB:
            return True
        job = _k32.CreateJobObjectW(None, None)
        if not job:
            return False
        thong_tin = _EXTENDED_LIMIT()
        thong_tin.BasicLimitInformation.LimitFlags = (
            _LIMIT_KILL_ON_JOB_CLOSE | _LIMIT_BREAKAWAY_OK)
        if not _k32.SetInformationJobObject(
                job, _JobObjectExtendedLimitInformation,
                ctypes.byref(thong_tin), ctypes.sizeof(thong_tin)):
            _k32.CloseHandle(job)
            return False
        if not _k32.AssignProcessToJobObject(job, _k32.GetCurrentProcess()):
            _k32.CloseHandle(job)
            return False
        _JOB = job
        return True


# ── Sổ ghi ───────────────────────────────────────────────────────────────────


def _duong_so(goc: str) -> str:
    return os.path.join(goc, "workspace", TEN_SO)


def _doc_so(goc: str) -> List[Dict[str, Any]]:
    try:
        with open(_duong_so(goc), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return []
    return [m for m in du_lieu if isinstance(m, dict)] \
        if isinstance(du_lieu, list) else []


def _ghi_so(goc: str, muc: List[Dict[str, Any]]) -> None:
    duong = _duong_so(goc)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tam"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(muc, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass  # sổ là lưới phụ — ghi hỏng không được làm hỏng việc chính


def _gio_tao(tien_trinh: Any) -> int:
    """Dấu vân tay để lần sau biết "đúng là nó": giờ tạo tiến trình."""
    if os.name == "nt":
        try:
            return _gio_tao_theo_handle(int(tien_trinh._handle))  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return 0
    return int(time.time())


def ghi_nhan(tien_trinh: Any, goc: str = "", ten: str = "",
            chu: Optional[str] = None) -> None:
    """Ghi nhận một tiến trình con dài (đang sống). `goc` rỗng thì chỉ nhớ
    trong bộ nhớ, không ghi sổ.

    `chu`: `CHU_GUI`/`CHU_TU_CHAY` (xem "CHỦ SỞ HỮU" ở docstring đầu tệp) —
    để trống thì tự đoán bằng `_chu_mac_dinh()` (tiến trình ĐANG GHI, không
    phải tiến trình con). `don_xac_cu` chỉ giết mục `chu == CHU_GUI`."""
    pid = int(getattr(tien_trinh, "pid", 0) or 0)
    if not pid:
        return
    with _KHOA:
        _DANG_SONG[pid] = tien_trinh
    if goc:
        chu = chu or _chu_mac_dinh()
        muc = [m for m in _doc_so(goc) if m.get("pid") != pid]
        muc.append({"pid": pid, "tao_luc": _gio_tao(tien_trinh), "chu": chu,
                    "ten": ten, "ghi_luc": int(time.time())})
        _ghi_so(goc, muc[-200:])


def bo_ghi_nhan(tien_trinh: Any, goc: str = "") -> None:
    """Tiến trình đã xong — rút khỏi sổ để lần mở sau khỏi đi tìm."""
    pid = int(getattr(tien_trinh, "pid", 0) or 0)
    with _KHOA:
        _DANG_SONG.pop(pid, None)
    if goc and pid:
        _ghi_so(goc, [m for m in _doc_so(goc) if m.get("pid") != pid])


def dung_tat_ca() -> int:
    """Giết mọi tiến trình con đã ghi nhận mà còn sống. Trả về số đã giết.

    Gọi lúc đóng cửa sổ và lúc trình thông dịch thoát (`atexit`). Trên
    Windows đây chỉ là lớp lịch sự trước lớp Job Object; ngoài Windows đây là
    lớp duy nhất."""
    with _KHOA:
        muc = list(_DANG_SONG.values())
        _DANG_SONG.clear()
    da = 0
    for tt in muc:
        try:
            if tt.poll() is None:
                tt.kill()
                da += 1
        except Exception:  # noqa: BLE001
            pass
    return da


def con_song(pid: int, tao_luc: int = 0) -> bool:
    """Tiến trình `pid` còn sống không — và nếu có `tao_luc`, có đúng là nó không."""
    if os.name == "nt":
        h = _mo(pid, _PROCESS_QUERY_LIMITED_INFORMATION)
        if not h:
            return False
        try:
            ma = wintypes.DWORD()
            if not _k32.GetExitCodeProcess(h, ctypes.byref(ma)) \
                    or ma.value != _STILL_ACTIVE:
                return False
            return not tao_luc or _gio_tao_theo_handle(h) == tao_luc
        finally:
            _k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _ghi_log(goc: str, dong: str) -> None:
    """Ghi một dòng vào `workspace/tien-trinh-con.log`. Ghi hỏng thì bỏ qua —
    đây là log cho người đọc lại, không phải sổ dùng để quyết định gì."""
    try:
        duong = os.path.join(goc, "workspace", "tien-trinh-con.log")
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write("[{0}] {1}\n".format(
                time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def _giet(pid: int) -> bool:
    if os.name == "nt":
        h = _mo(pid, _PROCESS_TERMINATE)
        if not h:
            return False
        try:
            return bool(_k32.TerminateProcess(h, 1))
        finally:
            _k32.CloseHandle(h)
    try:
        os.kill(pid, 9)
        return True
    except OSError:
        return False


def giet_pid(pid: int) -> bool:
    """Giết thẳng một PID biết trước — dùng cho nơi khác cần dừng đúng MỘT
    tiến trình đã xác định là treo (ví dụ `core.gac_tong` dừng một lượt
    `tu_chay.py` đứng khâu quá lâu). KHÔNG đụng sổ `tien-trinh-con.json` —
    chỉ là bọc mỏng cho `TerminateProcess`/`os.kill`, không tính vân tay giờ
    tạo (nơi gọi tự chịu trách nhiệm đã xác nhận đúng tiến trình cần giết)."""
    return _giet(int(pid))


def don_xac_cu(goc: str) -> int:
    """Lúc mở tool: giết tiến trình con của lần chạy trước còn sót, CHỈ mục
    `chu == CHU_GUI` (tiến trình do giao diện tự sinh) — mục `chu ==
    CHU_TU_CHAY` (một lượt `tu_chay.py` tách rời) được GIỮ NGUYÊN, mục sổ CŨ
    không có trường `chu` chỉ bị giết khi tiến trình CHA của nó (dò bằng
    `_ppid`) đã CHẾT (không dò được `_ppid` thì coi là "chưa chắc", không
    giết — xem "CHỦ SỞ HỮU" ở docstring đầu tệp). Trả về số đã giết. Trong
    MỌI trường hợp còn giết đều đòi hỏi thêm **mã tiến trình còn sống VÀ giờ
    tạo khớp** — không bao giờ giết nhầm chương trình khác đã nhận lại cùng
    mã.

    ═══ CHẶN DƯỚI PYTEST ═══

    `workspace/tien-trinh-con.json` là sổ DÙNG CHUNG với `tu_chay.py`: khâu
    viết kịch bản (`core/viet_max.py`) ghi tiến trình `claude` của LƯỢT SẢN
    XUẤT THẬT đang chạy vào đúng sổ này. Một bài test dựng `CuaSoChinh(<gốc
    thật>)` (vô tình trỏ gốc thật, hay cố ý để soi hộp thoại) mà chạy đúng
    lúc đó sẽ đọc phải sổ ấy và **giết tiến trình `claude` đang viết dở** —
    khách mất cả lượt, không ai biết vì sao. Vì vậy dưới pytest hàm này
    không giết gì hết, chỉ ghi log để biết là đã bị chặn (không im lặng)."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        _ghi_log(goc, "CHẶN don_xac_cu dưới pytest ({0}) — không giết gì, "
                  "gốc={1}".format(os.environ["PYTEST_CURRENT_TEST"], goc))
        return 0
    muc = _doc_so(goc)
    if not muc:
        return 0
    da = 0
    con_lai: List[Dict[str, Any]] = []
    for m in muc:
        try:
            pid, tao_luc = int(m.get("pid") or 0), int(m.get("tao_luc") or 0)
        except (TypeError, ValueError):
            continue  # rác không đọc được — bỏ luôn, không có gì để giữ lại
        if not pid or pid == os.getpid():
            continue  # rỗng, hoặc trùng PID của chính tiến trình đang chạy hàm này
        chu = m.get("chu")
        if chu is None:
            cha = _ppid(pid)
            duoc_giet = cha is not None and not con_song(cha)
        else:
            duoc_giet = str(chu) == CHU_GUI
        if not duoc_giet:
            con_lai.append(m)  # chu == tu_chay (hoặc cha còn sống/không rõ) — không đụng
            continue
        if con_song(pid, tao_luc) and _giet(pid):
            da += 1
        # đã xác định "được giết" — dù kill thành công hay tiến trình đã tự
        # thoát trước đó, mục này rút khỏi sổ (không giữ lại rác vô thời hạn).
    _ghi_so(goc, con_lai)
    return da


def mo_con(lenh: List[str], goc: str = "", ten: str = "", **tham_so: Any):
    """`subprocess.Popen` kèm ghi nhận. Dùng cho tiến trình chạy lâu."""
    tien_trinh = subprocess.Popen(lenh, **tham_so)
    ghi_nhan(tien_trinh, goc, ten)
    return tien_trinh


atexit.register(dung_tat_ca)
