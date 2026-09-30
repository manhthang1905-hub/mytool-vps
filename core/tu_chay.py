"""Chu kỳ một ngày cho MỘT kênh "tự chạy" — không giao diện, không người ngồi xem.

═══ VIỆC CỦA TỆP NÀY ═══

Mọi mảnh đã có sẵn: `core/mot_nut.py` nghiên cứu, `core/cong_thuc_v7.py` chấm
điểm chọn nguồn, `core/auto.py` + `core/auto_khau.py` sản xuất tám khâu,
`core/ban_giao_dang.py` bàn giao cho máy ảo đăng. Tệp này là NGƯỜI CHỈ HUY nối
bốn mảnh ấy lại thành một lượt chạy trong đêm, cho một kênh, không ai bấm gì:

    0) khoá — cả chu kỳ chỉ MỘT tiến trình được giữ (bộ lập lịch + bấm tay có
       thể chồng giờ)
    1) nghiên cứu (miễn phí, trừ khi có ví AI — và `che_do="thu"` không bao
       giờ đưa ví vào, xem mục dưới)
    2) chọn MỘT nguồn — trước tiên nhặt lại lượt CHƯA XONG của chính kênh này
       trong 7 ngày gần nhất (kể cả hôm nay); không có thì mới chọn nguồn mới:
       Công thức V7 nếu kênh đã có cấu hình (chỉ nhận `loai` "Làm ngay"/"Nên
       làm", không rơi về "Một nút" khi V7 đã có ý kiến), không thì lấy top
       bảng "Một nút"; loại video kênh mình đã làm VÀ video kênh khác trong
       cùng nhóm đã làm (không remake trùng nhau)
    3) kiểm kênh đủ điều kiện (giọng đọc, ảnh nhân vật, lời nhắc…) rồi mới van
       ĐĨA TRỐNG (đĩa dưới ngưỡng an toàn thì thử dọn khẩn trước, vẫn thiếu thì
       dừng — xem mục "VAN ĐĨA TRỐNG" dưới), rồi mới van ngân sách — kênh
       không khai trần ngày thì KHÔNG được sản xuất
    4) sản xuất (tốn tiền thật — chỉ chạy ở `che_do="that"`)
    5) bàn giao — điền ngày giờ đăng CHỈ KHI kênh khai `tu_duyet: true`

═══ IDEMPOTENT, VÀ NHỚ QUA NGÀY ═══

Mỗi lần gọi ghi/đọc `CHANNEL/<kênh>/tu-chay/<ngày>.json` — sổ của riêng ngày
đó. Nhưng "hôm nay chưa xong" không chỉ nhìn sổ hôm nay: lượt chết dở HÔM QUA
(máy khởi động lại, mạng rớt ở khâu clip) phải được nhặt lại trước khi mở video
mới — không thì tiền đã trả cho hôm qua coi như đổ sông. `_tim_run_chua_xong`
quét 7 ngày gần nhất; lượt được nhặt về ghi một dòng THAM CHIẾU vào sổ hôm nay
(để `video_moi_ngay` đếm đúng) còn bản chính vẫn nằm ở đúng ngày nó sinh ra.
Muốn dứt khoát bỏ một lượt dở (không remake tiếp) thì tự tay đặt `"bo": true`
vào mục đó trong tệp JSON — từ đó bị bỏ qua vĩnh viễn.

`kenh.yaml` khai `video_moi_ngay` > 1 thì mới được chọn nguồn thứ hai trong
cùng một ngày.

═══ KHOÁ MỘT TIẾN TRÌNH MỖI KÊNH ═══

Bộ lập lịch của VPS và một cú bấm tay có thể rơi trúng cùng một phút. Không có
khoá thì cả hai đều thấy "chưa có lượt nào hôm nay", cùng chọn nguồn, cùng trả
tiền — hai video cho một chỗ trống. `CHANNEL/<kênh>/tu-chay/.khoa` là khoá độc
quyền (tạo bằng `O_CREAT|O_EXCL`, không có khoảng hở đọc-rồi-ghi): còn ai giữ
và còn sống thì tiến trình sau bị từ chối ngay, không đụng gì tới sổ sách.
Tiến trình giữ khoá đã CHẾT (kiểm PID) hoặc khoá đã quá 12 giờ thì được giành
lại — kẹt vĩnh viễn vì một tiến trình treo còn tệ hơn hoạ hiếm hai lượt chồng.

═══ KHÔNG TỰ THÊM VÒNG HỎI JOB NÀO Ở ĐÂY ═══

CLAUDE.md luật 4: hỏi dày không làm job xong sớm hơn, chỉ ăn CPU máy chủ — mà
máy chủ dùng đúng CPU đó để kết sổ tiền. Sản xuất đi qua `core.auto.chay` +
`core.auto_khau`, hai chỗ ĐÃ tự lo nhịp hỏi (poll_delays, webhook/SSE khi có).
Tệp này không viết thêm một `while True: sleep(...)` nào.

Không mạng, không Qt: mọi lời gọi mạng thật (nghiên cứu AI, sản xuất) đi qua
tham số `client`/seam, nên bài kiểm chạy được bằng đồ giả.

═══ `chay_tat_ca` — THỨ TỰ MỘT LƯỢT `--tat-ca` ═══

    1. đồng bộ NHÓM (đối thủ chung, bảng chéo kênh) — `dong_bo_nhom_truoc_khi_chay`.
    2. chạy TỪNG KÊNH lần lượt — `chay_nhieu_kenh` → `chay_mot_ngay` (nghiên cứu → chọn nguồn
       → sản xuất → bàn giao, xem sơ đồ đầu tệp).
    3. DỌN ĐĨA — `don_dep.don_theo_cai_dat` cho từng kênh (chỉ kênh bật `tu_don`).
    4. ghi SỔ NGÀY DÙNG CHUNG cho cả máy (`.md`/`.json`) — gộp chi phí sản xuất + byte đã dọn.
"""

from __future__ import annotations

import datetime as _dt
import errno
import json
import os
import shutil
import sys
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import auto
from . import ban_giao_dang
from . import bao_dong
from . import cong_thuc_v7 as v7
from . import da_lam as da_lam_mod
from . import dieu_phoi
from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from . import don_dep
from . import don_dep_mo_rong
from . import ke_hoach_dang
from . import kiem_trung_y
from . import mot_nut
from . import nghien_cuu_chung
from . import nghien_cuu_nhom
from . import nhuong_phien_kenh
from . import su_co
from . import trung_tieu_de
from . import tu_nhan_da_dang
from . import vong_hoc
from . import xep_lich
from .ghi_dia import ghi_chu, ghi_json
from .kenh import TEP_KENH, doc_kenh, duong_kenh, kiem_kenh, liet_ke_kenh
from .money import micro_to_vnd
from .pricing import (DEFAULT_PRICES, ENGINE_SEEDANCE, ENGINE_VEO3, PriceTable,
                      hold_for_image, hold_for_tts, hold_for_video)
from .srt_scenes import target_seconds_for

__all__ = ["THU_MUC_TU_CHAY", "duong_bao_cao_ngay", "chay_mot_ngay",
           "co_cau_hinh_v7", "ung_vien_xep_hang", "chon_cong_thuc", "CONG_THUC_NGUON",
           "cong_diem_anh_em", "NGUONG_BAC_VIEW",
           "kenh_tu_chay", "chay_nhieu_kenh", "dem_kho_loi_thoai",
           "dong_bo_nhom_truoc_khi_chay", "duong_bao_cao_tat_ca",
           "ghi_bao_cao_tat_ca", "duong_log_tat_ca", "bo_log_tat_ca",
           "chay_tat_ca"]

#: `CHANNEL/<kênh>/tu-chay/<ngày>.json` — sổ nhật ký + quyết định của từng ngày.
THU_MUC_TU_CHAY = "tu-chay"

#: Quét lượt CHƯA XONG trong ngần này ngày gần đây (kể cả hôm nay) trước khi
#: cho phép mở video mới — xem docstring đầu tệp.
SO_NGAY_QUET_LUOT_CHUA_XONG = 7

#: Tên tệp khoá độc quyền, nằm cạnh các sổ ngày trong `tu-chay/`.
TEN_TEP_KHOA = ".khoa"
# Một VPS chỉ nên có MỘT lượt sản xuất nặng tại một thời điểm. Khoá kênh ở
# trên ngăn hai lượt cùng đụng một kênh, nhưng không ngăn lịch chạy TL1/TL2
# trong lúc người dùng đang dựng TL3 — đúng nguyên nhân quá tải thấy 24/09.
TEN_TEP_KHOA_MAY = ".khoa-may"

#: Khoá cũ quá ngần này giây thì giành lại dù PID còn sống — kẹt vĩnh viễn còn
#: tệ hơn hoạ hiếm hai lượt chồng nhau. 12 giờ dài hơn hẳn video chậm nhất.
KHOA_CU_QUA_GIAY = 12 * 3600

# ══════════════════════════════════════════════════════════════════════════
# VAN ĐĨA TRỐNG (21/09/2026) — ổ C chỉ 49,4 GB, lúc thêm van này chỉ còn
# 13,1 GB trống, và 4 kênh × 1 video/ngày (mỗi video 0,4–0,9 GB) có thể đầy
# đĩa trong 4–8 ngày nếu dọn không kịp. Chủ dự án giữ nguyên ổ, bù lại bằng
# dọn gắt — hai hằng số dưới đây là "gắt" đó: ước RỘNG hơn thật một chút,
# thà chặn nhầm một video còn hơn để đầy đĩa giữa chừng (hỏng CẢ BỐN kênh
# dùng chung một ổ C, không riêng kênh đang chạy).
# ══════════════════════════════════════════════════════════════════════════

#: GB "thô" ước cho MỖI PHÚT video hoàn thiện của một kênh. Video cuối
#: (8-video.mp4) cỡ 0,4–0,9 GB cho 8–12 phút — tức ~0,05–0,09 GB/phút — nhưng
#: lúc ĐANG SẢN XUẤT, đĩa còn phải chứa CÙNG LÚC cả hàng dữ liệu GIỮA (ảnh
#: cảnh PNG + clip MP4 câm + mp3 giọng đọc, xem `core/don_dep._MUC_NANG`),
#: nặng ngang hoặc hơn cả video cuối, và chỉ mất đi sau khi lượt được DỌN
#: (đã đăng + qua hạn ân xá) — không phải ngay khi sản xuất xong. 0,2 GB/phút
#: cố tình ước DƯ để không lọt một video làm đầy đĩa giữa chừng.
GB_MOI_PHUT_VIDEO = 0.2

#: Biên dự phòng CỐ ĐỊNH cộng thêm vào ước tính trên cho MỖI video — chừa chỗ
#: cho log/sổ sách phình thêm trong lúc sản xuất và cho sai số ước tính
#: (kịch bản dài hơn thường lệ, engine đổi định dạng…). 1 GB xấp xỉ 1/13 tổng
#: dung lượng trống lúc khảo sát (13,1 GB, 21/09/2026) — đủ rộng để không
#: chặn nhầm một video bình thường, đủ hẹp để không trễ tín hiệu "sắp cạn".
BIEN_DU_PHONG_DIA_GB = 1.0

# Chừa đủ bộ nhớ cho Windows, Qt và tiến trình con. Dưới mốc này lượt đang dở
# được giữ nguyên và lịch chạy sau sẽ thử lại, thay vì cố chạy rồi cả máy sập.
RAM_TRONG_TOI_THIEU_GB = 3.0


def _ram_trong_gb() -> Optional[float]:
    try:
        if os.name == "nt":
            import ctypes  # noqa: PLC0415

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
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(bo)):
                return float(bo.ullAvailPhys) / (1024.0 ** 3)
        return float(int(os.sysconf("SC_AVPHYS_PAGES"))
                     * int(os.sysconf("SC_PAGE_SIZE"))) / (1024.0 ** 3)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def duong_bao_cao_ngay(goc: str, ma_kenh: str, ngay: str) -> str:
    return os.path.join(duong_kenh(goc, ma_kenh), THU_MUC_TU_CHAY, "{0}.json".format(ngay))


def _doc_bao_cao_ngay(goc: str, ma_kenh: str, ngay_str: str) -> Dict[str, Any]:
    duong = duong_bao_cao_ngay(goc, ma_kenh, ngay_str)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        if isinstance(du, dict) and isinstance(du.get("runs"), list):
            return du
    except (OSError, ValueError):
        pass
    return {"ngay": ngay_str, "kenh": ma_kenh, "runs": [], "nhat_ky": []}


def _ghi_bao_cao_ngay(goc: str, ma_kenh: str, ngay_str: str, bao_cao: Dict[str, Any]) -> None:
    ghi_json(duong_bao_cao_ngay(goc, ma_kenh, ngay_str), bao_cao)


def _ma_luot_moi(goc: str, ma_kenh: str) -> str:
    """Mã lượt tiếp theo cho kênh — cùng luật `ui_qt/trang_auto._ma_luot_moi`."""
    thu_muc = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    try:
        da_co = [t for t in os.listdir(thu_muc) if t.isdigit()]
    except OSError:
        da_co = []
    return "{0:04d}".format(max([int(t) for t in da_co] or [0]) + 1)


# ── Khoá một tiến trình mỗi kênh ─────────────────────────────────────────────


def _pid_con_song(pid: int) -> bool:
    """Tiến trình mang PID này còn đang chạy thật không.

    Windows: hỏi thẳng kernel bằng quyền chỉ-đọc tối thiểu. Nơi khác:
    `os.kill(pid, 0)` (không giết, chỉ hỏi có tồn tại). Hỏi mà hỏng (không có
    `tasklist`, quyền bị chặn…) thì coi như CÒN SỐNG — an toàn hơn là giành
    khoá bừa của một tiến trình có thể vẫn đang tiêu tiền.
    """
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    # `tasklist` trên VPS này trả "Access denied" khi tiến trình đích chạy với
    # quyền khác, khiến khoá hiểu nhầm PID sống là đã chết. OpenProcess với
    # QUERY_LIMITED_INFORMATION chỉ hỏi sự tồn tại và không can thiệp tiến trình.
    try:
        import ctypes  # noqa: PLC0415

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel.OpenProcess(0x1000, False, int(pid))
        if handle:
            kernel.CloseHandle(handle)
            return True
        ma_loi = ctypes.get_last_error()
        if ma_loi == 5:   # ACCESS_DENIED vẫn chứng minh PID đang tồn tại
            return True
        if ma_loi == 87:  # INVALID_PARAMETER: PID không tồn tại
            return False
    except Exception:  # noqa: BLE001 — còn đường tasklist an toàn phía dưới
        pass

    import subprocess  # noqa: PLC0415

    try:
        ra = subprocess.run(
            ["tasklist", "/FI", "PID eq {0}".format(int(pid)), "/NH"],
            # `tasklist` xuất theo BẢNG MÃ HỆ THỐNG, không phải UTF-8. Trên
            # Windows bản địa hoá, `text=True` trần vỡ bằng UnicodeDecodeError
            # trong luồng đọc nền — cùng nết với `core/capcut.py _capcut_dang_chay`.
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:  # noqa: BLE001
        return True
    if ra.returncode != 0:
        return True
    return str(pid) in (ra.stdout or "")


def _duong_khoa(goc: str, ma_kenh: str) -> str:
    return os.path.join(duong_kenh(goc, ma_kenh), THU_MUC_TU_CHAY, TEN_TEP_KHOA)


def _duong_khoa_may(goc: str) -> str:
    return os.path.join(goc, "workspace", "tu-chay", TEN_TEP_KHOA_MAY)


def _doc_khoa(duong: str) -> Dict[str, Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _tao_tep_khoa(duong: str) -> bool:
    """Tạo tệp khoá KIỂU ĐỘC QUYỀN (`O_CREAT|O_EXCL`) — hai tiến trình cùng
    lúc thì chỉ một tạo được, không có khoảng hở đọc-rồi-ghi. Trả `True` nếu
    tạo được."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    try:
        fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    except OSError:
        pass
    return True


def _giu_khoa(goc: str, ma_kenh: str, *,
              con_song: Callable[[int], bool] = _pid_con_song) -> Tuple[bool, str]:
    """Giành khoá độc quyền cho MỘT kênh — cả chu kỳ `chay_mot_ngay` chỉ một
    tiến trình được giữ khoá này cùng lúc. Trả `(giành được, lý do nếu không)`.
    """
    duong = _duong_khoa(goc, ma_kenh)
    if _tao_tep_khoa(duong):
        return True, ""
    cu = _doc_khoa(duong)
    pid_cu = int(cu.get("pid") or 0)
    bat_dau_cu = float(cu.get("bat_dau") or 0)
    tuoi_giay = (time.time() - bat_dau_cu) if bat_dau_cu else (KHOA_CU_QUA_GIAY + 1)
    if pid_cu and tuoi_giay < KHOA_CU_QUA_GIAY and con_song(pid_cu):
        luc = (_dt.datetime.fromtimestamp(bat_dau_cu).strftime("%H:%M %d/%m")
              if bat_dau_cu else "?")
        return False, "đang chạy ở tiến trình khác (PID {0}, bắt đầu {1})".format(pid_cu, luc)
    # PID đã chết, hoặc khoá quá cũ (>12 giờ) — giành lại.
    try:
        os.remove(duong)
    except OSError:
        pass
    if _tao_tep_khoa(duong):
        return True, ""
    return False, "đang chạy ở tiến trình khác (vừa giành khoá đúng lúc này)"


def _nha_khoa(goc: str, ma_kenh: str) -> None:
    try:
        os.remove(_duong_khoa(goc, ma_kenh))
    except OSError:
        pass


def giu_khoa_may(goc: str, *,
                 con_song: Callable[[int], bool] = _pid_con_song) -> Tuple[bool, str]:
    """Giành quyền chạy MỘT lượt sản xuất nặng trên cả VPS.

    Cả `--kenh` và `--tat-ca` gọi cửa này trước nghiên cứu/API/FFmpeg. Khoá cũ
    được giành lại khi PID đã chết hoặc quá 12 giờ, cùng luật với khoá kênh.
    """
    duong = _duong_khoa_may(goc)
    if _tao_tep_khoa(duong):
        return True, ""
    cu = _doc_khoa(duong)
    pid_cu = int(cu.get("pid") or 0)
    bat_dau_cu = float(cu.get("bat_dau") or 0)
    tuoi_giay = (time.time() - bat_dau_cu) if bat_dau_cu else (KHOA_CU_QUA_GIAY + 1)
    if pid_cu and tuoi_giay < KHOA_CU_QUA_GIAY and con_song(pid_cu):
        luc = (_dt.datetime.fromtimestamp(bat_dau_cu).strftime("%H:%M %d/%m")
               if bat_dau_cu else "?")
        return False, ("máy đang làm một lượt khác (PID {0}, bắt đầu {1}); "
                       "bỏ qua để không quá tải".format(pid_cu, luc))
    try:
        os.remove(duong)
    except OSError:
        pass
    if _tao_tep_khoa(duong):
        return True, ""
    return False, "máy vừa bắt đầu một lượt khác; bỏ qua để không quá tải"


def nha_khoa_may(goc: str) -> None:
    """Chỉ chủ nhân hiện tại được nhả khoá máy."""
    duong = _duong_khoa_may(goc)
    if int(_doc_khoa(duong).get("pid") or 0) != os.getpid():
        return
    try:
        os.remove(duong)
    except OSError:
        pass


# ── Nhặt lại lượt chưa xong (hôm nay hoặc mấy ngày trước) ───────────────────


def _coi_nhu_da_xong(luot: auto.LuotChay) -> bool:
    """L2 (chẩn đoán 26/09/2026) — lượt này có còn CẦN "chạy tiếp" không.

    Coi là XONG khi `luot.xong_het` THẬT (mọi khâu đều XONG/BỎ_QUA), HOẶC khi
    khâu `dung` (dựng video hoàn thiện) đã XONG: các khâu thuộc
    `auto.KHAU_KHONG_CHAN` (hiện chỉ có `thumbnail`) đứng TRƯỚC `dung` trong
    dây chuyền và KHÔNG chặn nó (xem docstring `auto.KHAU_KHONG_CHAN`) — hỏng
    mãi cũng không ngăn được video ra đời. Không có lý do gì để một khâu ảnh
    bìa kẹt giữ cả lượt trong danh sách "chưa xong" mãi mãi, khiến
    `--tat-ca` cứ nhặt lại đúng lượt này mỗi giờ dù video đã dựng xong (và có
    thể đã bàn giao từ lâu) — đúng triệu chứng chủ dự án mô tả.
    """
    return luot.xong_het or luot.tt("dung").trang_thai == auto.XONG


def _luot_da_bi_bo(thu_muc_luot: str) -> bool:
    """Thư mục lượt có tệp đánh dấu `BO-VI-*.txt` (L3 đã tự bỏ) không."""
    try:
        return any(ten.startswith("BO-VI-") and ten.endswith(".txt")
                   for ten in os.listdir(thu_muc_luot))
    except OSError:
        return False


def _nhan_nuoi_luot_mo_coi(goc: str, ma_kenh: str, ngay_hien_tai_str: str,
                           da_thay_ma_luot: set) -> str:
    """L1 (chẩn đoán 26/09/2026) — quét thẳng `PROJECTS/AUTO/<kênh>/` (qua
    `auto.liet_ke_luot`, đọc đĩa, KHÔNG qua sổ) tìm lượt CÓ `trang-thai.json`
    nhưng CHƯA XONG mà `da_thay_ma_luot` (mọi mã lượt đã gặp trong `so_ngay`
    ngày gần đây của sổ — kể cả đã xong hay đã bị "bo") KHÔNG CÓ.

    Đó là lượt MỒ CÔI: tiến trình sinh ra nó bị giết (mất điện, đóng tool,
    Windows hạ tiến trình…) TRƯỚC KHI kịp ghi dòng đầu tiên vào sổ ngày (xem
    docstring đầu tệp, mục "IDEMPOTENT, VÀ NHỚ QUA NGÀY") — `_tim_run_chua_xong`
    vốn CHỈ đọc sổ nên không bao giờ thấy nó, và sau `so_ngay` ngày nó lọt
    khỏi cửa sổ quét, bị quên im lặng mãi mãi (đúng ca TL1-T7/0003 + 0004,
    24/09/2026).

    Ghi một dòng "nhận con nuôi" vào sổ HÔM NAY — cùng khuôn dòng chọn nguồn
    mới ở `_chay_mot_ngay_trong_khoa` — để nhánh 2) coi lượt này như một lượt
    dở bình thường, chạy tiếp đúng chỗ nó đang dang dở.

    Chỉ nhận nuôi MỘT lượt mỗi lần gọi (cũ nhất theo `tao_luc`) — đúng nhịp
    "một video một lúc" của `_tim_run_chua_xong`. Mồ côi còn lại (nếu có
    nhiều, như TL1-T7 có cả 0003 lẫn 0004) sẽ được nhận nuôi ở lần gọi SAU,
    sau khi lượt này xong hoặc bị bỏ (L3). Trả về mã lượt vừa nhận nuôi, hoặc
    chuỗi rỗng nếu không có lượt mồ côi nào.
    """
    # VÁ 29/09/2026 (full công suất): lượt ĐÃ BỊ L3 BỎ (có tệp `BO-VI-*.txt` do
    # `_bo_luot_qua_han` ghi) không bao giờ được nhận nuôi lại. Trước vá, dòng
    # `"bo": true` chỉ che nó chừng nào sổ ngày đó còn trong cửa sổ 7 ngày — sổ
    # rơi khỏi cửa sổ là lượt đã bỏ (TL1-T7/0003, 0004 bỏ 28/09) bị coi là mồ côi
    # và sản xuất lại nguồn cũ từ 05/10.
    ung_vien = [luot for luot in auto.liet_ke_luot(goc, ma_kenh)
               if luot.ma_luot not in da_thay_ma_luot and not _coi_nhu_da_xong(luot)
               and not _luot_da_bi_bo(luot.thu_muc)]
    if not ung_vien:
        return ""
    ung_vien.sort(key=lambda l: (l.tao_luc, l.ma_luot))
    luot = ung_vien[0]

    bao_cao = _doc_bao_cao_ngay(goc, ma_kenh, ngay_hien_tai_str)
    if any(str(r.get("ma_luot")) == luot.ma_luot for r in bao_cao.get("runs") or []):
        return luot.ma_luot  # đã nhận nuôi ở một lần gọi trước, trong sổ hôm nay rồi

    nguon = {
        "nguon": "nhan-nuoi", "ma": "", "kenh": "",
        "link": str(luot.dau_vao.get("link") or ""),
        "tieu_de": str(luot.dau_vao.get("tieu_de") or ""),
        "ly_do": ["lượt mồ côi — có trang-thai.json trong PROJECTS/AUTO nhưng không có "
                 "dòng nào trong sổ tu-chay gần đây (tiến trình cũ bị giết trước khi kịp "
                 "ghi sổ) — nhận lại để không bị quên im lặng"],
    }
    run = {"ma_luot": luot.ma_luot, "nguon": nguon,
          "ngan_sach": {}, "san_xuat": {"da_chay": False, "xong_het": False,
                                        "khau_hong": [], "loi": ""},
          "ban_giao": {"da_ban_giao": False, "ma_goi": "", "ngay_dang": "",
                      "gio_dang": "", "ly_do_trong": "", "loi": ""},
          "nhan_nuoi": True}
    bao_cao["runs"].append(run)
    _ghi_bao_cao_ngay(goc, ma_kenh, ngay_hien_tai_str, bao_cao)
    return luot.ma_luot


def _tim_run_chua_xong(goc: str, ma_kenh: str, ngay_hien_tai: _dt.date,
                       *, so_ngay: int = SO_NGAY_QUET_LUOT_CHUA_XONG
                       ) -> Optional[Tuple[str, str]]:
    """`(ngày, mã lượt)` CŨ NHẤT trong `so_ngay` ngày gần đây (kể cả hôm nay)
    mà lượt chưa xong hết và chưa bị đánh dấu bỏ (`"bo": true`). `None` nếu
    không có lượt nào như vậy.

    Chỉ trả về mảnh nhẹ (ngày, mã) — nơi gọi tự quyết định lấy sổ nào: sổ hôm
    nay đã có sẵn trong bộ nhớ, sổ ngày trước phải đọc lại từ đĩa.

    Không tìm được lượt nào QUA SỔ thì thử thêm một cửa nữa (L1):
    `_nhan_nuoi_luot_mo_coi` quét thẳng đĩa tìm lượt MỒ CÔI — xem docstring
    hàm đó.
    """
    ung_vien: List[Tuple[str, str]] = []
    da_thay_ma_luot: set = set()
    for i in range(max(1, so_ngay)):
        ngay_str = (ngay_hien_tai - _dt.timedelta(days=i)).isoformat()
        bc = _doc_bao_cao_ngay(goc, ma_kenh, ngay_str)
        for r in bc.get("runs") or []:
            ma_luot_bat_ky = str(r.get("ma_luot") or r.get("tham_chieu_ma_luot") or "")
            if ma_luot_bat_ky:
                da_thay_ma_luot.add(ma_luot_bat_ky)
            if r.get("bo") or r.get("tham_chieu_ma_luot"):
                continue  # đánh dấu bỏ tay, hoặc chỉ là dòng tham chiếu — không phải bản chính
            ma_luot = str(r.get("ma_luot") or "")
            if not ma_luot:
                continue
            luot = auto.doc_luot(auto.duong_luot(goc, ma_kenh, ma_luot))
            if luot is None or not _coi_nhu_da_xong(luot):
                ung_vien.append((ngay_str, ma_luot))
    if not ung_vien:
        ma_nuoi = _nhan_nuoi_luot_mo_coi(goc, ma_kenh, ngay_hien_tai.isoformat(), da_thay_ma_luot)
        if ma_nuoi:
            ung_vien.append((ngay_hien_tai.isoformat(), ma_nuoi))
    if not ung_vien:
        return None
    ung_vien.sort(key=lambda x: x[0])  # cũ nhất trước
    return ung_vien[0]


# ── L3: trần tự phục hồi — bỏ hẳn lượt kẹt vĩnh viễn ─────────────────────────
#
# Chẩn đoán 26/09/2026: `_tim_run_chua_xong` nhặt lại một lượt dở MÃI MÃI, kể
# cả khi nguồn/khâu đó đã hỏng cố định (hết ví, lỗi nội dung lặp lại…) — mỗi
# lần `--tat-ca` chạy lại là một lần "phục hồi" vô ích, chiếm mất chỗ mà đáng
# ra để cho `video_moi_ngay` chọn một nguồn KHÁC còn sản xuất được. Bốn cửa
# dưới đây, bất kỳ cửa nào cũng đủ để BỎ HẲN (không bao giờ remake lại):

#: Quá ngần này LẦN được tự phục hồi (nhặt lại, "chạy tiếp") mà vẫn chưa xong
#: thì BỎ — một nguồn kẹt thật không tự khỏi chỉ vì thử thêm một lần nữa.
TRAN_SO_LAN_PHUC_HOI = 3

#: Quá ngần này GIỜ kể từ LẦN PHỤC HỒI ĐẦU TIÊN mà vẫn chưa xong thì BỎ, dù số
#: lần phục hồi chưa chạm trần trên (vd lượt chỉ bị nhặt lại một lần nhưng kẹt
#: tại đó suốt mấy ngày vì chờ RAM/đĩa/ngân sách).
TRAN_GIO_PHUC_HOI = 48.0

#: Ba loại sự cố (xem `core/su_co.py`) mà GẶP LẶP LẠI HAI LẦN LIÊN TIẾP coi
#: như "sẽ không bao giờ tự hết" — khác lỗi mạng thoáng qua, chỉ cần thử lại.
_LOAI_LOI_KHONG_TU_HET = (su_co.HET_TIEN, su_co.CHET, su_co.NOI_DUNG)


def _loai_loi_san_xuat(run: Dict[str, Any]) -> str:
    """Phân loại câu lỗi ĐÃ LƯU của lần sản xuất gần nhất (`run["san_xuat"]["loi"]`,
    một chuỗi đọc lại từ sổ — không còn ngoại lệ gốc) qua `core.su_co.phan_loai`,
    thứ vốn dò theo CÂU CHỮ nên nhận một chuỗi bọc trong `RuntimeError` là đủ."""
    loi = str((run.get("san_xuat") or {}).get("loi") or "")
    return su_co.phan_loai(RuntimeError(loi)) if loi else ""


def _ly_do_vuot_tran_phuc_hoi(run: Dict[str, Any], ngay_hien_tai: _dt.date,
                              ngay_luot_str: str, *,
                              bay_gio: Optional[_dt.datetime] = None,
                              so_ngay_cua_so: int = SO_NGAY_QUET_LUOT_CHUA_XONG
                              ) -> str:
    """Lượt này đã vượt trần tự phục hồi chưa — trả về LÝ DO (câu người đọc
    được) nếu có, chuỗi RỖNG nếu còn được phục hồi tiếp bình thường. Xem bốn
    cửa ở khối chú thích ngay phía trên; cửa thứ tư (sắp lọt cửa sổ quét) là
    lưới an toàn cuối — không thì một lượt cứ mãi ở ranh giới "còn 1 ngày" có
    thể bị quên im lặng ngay sau khi rơi khỏi `so_ngay_cua_so`.
    """
    ph = run.get("phuc_hoi") if isinstance(run.get("phuc_hoi"), dict) else {}

    so_lan = int(ph.get("so_lan") or 0)
    if so_lan >= TRAN_SO_LAN_PHUC_HOI:
        return ("đã tự phục hồi (nhặt lại) {0} lần mà vẫn chưa xong — chạm trần {1} lần, "
                "khả năng nguồn hoặc khâu nào đó kẹt vĩnh viễn.").format(
                    so_lan, TRAN_SO_LAN_PHUC_HOI)

    lan_dau_luc = ph.get("lan_dau_luc")
    if lan_dau_luc:
        bay_gio_dt = bay_gio or _dt.datetime.now()
        try:
            gio_da_troi = (bay_gio_dt.timestamp() - float(lan_dau_luc)) / 3600.0
        except (TypeError, ValueError):
            gio_da_troi = 0.0
        if gio_da_troi > TRAN_GIO_PHUC_HOI:
            return ("đã hơn {0:.0f} giờ kể từ lần tự phục hồi đầu tiên mà vẫn chưa xong "
                    "(chạm trần {1:.0f} giờ).").format(gio_da_troi, TRAN_GIO_PHUC_HOI)

    loai_hien_tai = _loai_loi_san_xuat(run)
    loai_truoc = str(ph.get("loai_loi_truoc") or "")
    if loai_hien_tai and loai_hien_tai == loai_truoc and loai_hien_tai in _LOAI_LOI_KHONG_TU_HET:
        return ("lỗi “{0}” lặp lại liên tiếp — loại lỗi này thử lại không tự hết."
                ).format(su_co.mo_ta(loai_hien_tai))

    try:
        ngay_luot = _dt.date.fromisoformat(ngay_luot_str)
    except ValueError:
        return ""
    con_lai = so_ngay_cua_so - 1 - (ngay_hien_tai - ngay_luot).days
    if con_lai <= 0:
        return ("còn ≤1 ngày nữa là lọt khỏi cửa sổ quét {0} ngày gần nhất (lượt mở từ "
                "{1}) mà vẫn chưa xong — đánh dấu bỏ ngay, tránh bị quên im lặng."
                ).format(so_ngay_cua_so, ngay_luot_str)
    return ""


def _ghi_nhan_phuc_hoi(run: Dict[str, Any], *, bay_gio: Optional[_dt.datetime] = None) -> None:
    """Tăng bộ đếm "đã tự phục hồi mấy lần" + ghi lại LOẠI LỖI của lần này —
    dữ liệu mà `_ly_do_vuot_tran_phuc_hoi` đọc lại ở LẦN GỌI SAU. Ghi vào
    ngay `run` (nằm trong sổ của NGÀY LƯỢT SINH RA, không phải sổ hôm nay khi
    lượt được nhặt từ ngày trước) — nơi gọi tự lo ghi đĩa."""
    bay_gio_dt = bay_gio or _dt.datetime.now()
    ph = run.get("phuc_hoi") if isinstance(run.get("phuc_hoi"), dict) else {}
    run["phuc_hoi"] = {
        "so_lan": int(ph.get("so_lan") or 0) + 1,
        "lan_dau_luc": float(ph.get("lan_dau_luc") or bay_gio_dt.timestamp()),
        "loai_loi_truoc": _loai_loi_san_xuat(run),
    }


def _ten_tep_an_toan(chuoi: str, do_dai: int = 60) -> str:
    """`chuoi` → tên tệp an toàn trên Windows: chỉ giữ chữ/số, đổi phần còn
    lại thành `-`, cắt bớt cho gọn. Không cần `re` cho một việc một dòng."""
    ra = "".join(c if c.isalnum() else "-" for c in chuoi.strip())
    while "--" in ra:
        ra = ra.replace("--", "-")
    ra = ra.strip("-")
    return ra[:do_dai] or "khong-ro-ly-do"


def _bo_luot_qua_han(goc: str, ma_kenh: str, run: Dict[str, Any],
                     bao_cao_cua_run: Dict[str, Any], ngay_luot_str: str,
                     ly_do: str, log: Callable[[str], None]) -> None:
    """L3 — đánh dấu VĨNH VIỄN bỏ một lượt dở đã vượt trần tự phục hồi.

    Bốn việc, ĐÚNG THỨ TỰ chẩn đoán đã chỉ, và tuyệt đối KHÔNG xoá/sửa gì
    trong `PROJECTS/` (luật 1, CLAUDE.md — chỉ GHI THÊM một tệp đánh dấu):

    1. Ghi `"bo": true` + `"ly_do_bo"` vào đúng mục của lượt, trong sổ của
       NGÀY NÓ SINH RA (`bao_cao_cua_run`/`ngay_luot_str` — có thể khác sổ hôm
       nay) — từ đây `_tim_run_chua_xong` bỏ qua nó vĩnh viễn (nhánh lọc
       `r.get("bo")` đã có sẵn từ trước).
    2. Ghi thêm một tệp `BO-VI-<lý do>.txt` NGAY TRONG thư mục lượt — chủ dự
       án mở thư mục kết quả là thấy ngay vì sao, không cần lục sổ JSON.
    3. Ghi một dòng RÕ vào nhật ký lượt (`log`, đi vào cả `nhat_ky` của sổ
       ngày lẫn `tu-chay.log` khi chạy `--tat-ca`).
    4. Báo `bao_dong` mức `nhac` (gộp vào bản tin ngày, không dội chuông giữa
       đêm cho một việc không khẩn cấp).
    """
    run["bo"] = True
    run["ly_do_bo"] = ly_do
    _ghi_bao_cao_ngay(goc, ma_kenh, ngay_luot_str, bao_cao_cua_run)

    ma_luot = str(run.get("ma_luot") or "")
    thu_muc_luot = auto.duong_luot(goc, ma_kenh, ma_luot)
    try:
        os.makedirs(thu_muc_luot, exist_ok=True)
        ten_tep = "BO-VI-{0}.txt".format(_ten_tep_an_toan(ly_do))
        with open(os.path.join(thu_muc_luot, ten_tep), "w", encoding="utf-8") as tep:
            tep.write(
                "Tool đã TỰ Ý bỏ lượt {0}/{1}, không remake tiếp nguồn này.\n\n"
                "Lý do: {2}\n\n"
                "KHÔNG có tệp nào trong thư mục này bị xoá (luật 1, CLAUDE.md) — muốn "
                "làm lại thì mở sổ CHANNEL/{0}/tu-chay/{3}.json, tìm mục có "
                "\"ma_luot\": \"{1}\", xoá hai khoá \"bo\"/\"ly_do_bo\" rồi chạy lại.\n"
                .format(ma_kenh, ma_luot, ly_do, ngay_luot_str))
    except OSError as loi:
        log("  (không ghi được tệp BO-VI trong thư mục lượt: {0})".format(str(loi)[:150]))

    log("[TỰ BỎ LƯỢT] {0}/{1}: {2}".format(ma_kenh, ma_luot, ly_do))

    # G4 (29/09/2026): nhả nguồn đã giữ trong kho nhóm — kênh anh em được chọn lại nó.
    try:
        nghien_cuu_nhom.nha_nguon(goc, ma_kenh, str((run.get("nguon") or {}).get("ma") or ""))
    except Exception:  # noqa: BLE001 — nhả hỏng: bản giữ thành rác sau 7 ngày, tự hết
        pass

    try:
        bao_dong.bao_dong(
            "luot_tu_bo",
            "Tool đã tự bỏ một lượt video dở của kênh {0} (lượt {1}).".format(ma_kenh, ma_luot),
            "Lý do: {0}\nCác tệp cũ vẫn còn nguyên trong PROJECTS/AUTO/{1}/{2}/ — không mất "
            "gì. Tool sẽ tự chọn nguồn khác cho lần chạy sau.".format(ly_do, ma_kenh, ma_luot),
            goc=goc, kenh=ma_kenh, muc=bao_dong.MUC_NHAC)
    except Exception:  # noqa: BLE001 — báo động hỏng không được chặn việc bỏ lượt
        pass


# ── Chọn nguồn ────────────────────────────────────────────────────────────────


#: Xét ngần này ứng viên đầu bảng khi ưu tiên video ĐÃ CÓ lời thoại trong kho.
#:
#: ═══ VÌ SAO CÓ CỬA NÀY (22/09/2026) ═══
#:
#: Đêm 22/09/2026 cả ba kênh chết ở khâu ĐẦU (`kich-ban`): nó cần lời thoại
#: video đối thủ, mà YouTube đang chặn địa chỉ mạng của VPS này (`IpBlocked`,
#: *"IP belonging to a cloud provider"*) — cookie, đổi `player_client`, nâng
#: yt-dlp, proxy đều không cứu được đường tải tiếng. Lời thoại giờ tới từ KHO
#: (`core/loi_thoai.py`), do phiên trình duyệt kênh hút về lúc ~07:30 — tức
#: **một phần pool đối thủ có lời thoại sẵn, phần còn lại thì không**.
#:
#: Xếp hạng mà bỏ qua chuyện đó là tự chọn một nguồn KHÔNG sản xuất được: điểm
#: cao hơn vài phần trăm không đổi được việc đêm nay kênh ra 0 video. Nên nếu
#: đầu bảng chưa có lời thoại mà trong 5 ứng viên đầu có một cái đã có, chọn
#: cái đã có.
#:
#: 5 chứ không phải cả bảng: qua khỏi nhóm đầu thì khoảng cách điểm đã đủ lớn
#: để "có lời thoại sẵn" không bù nổi — lúc ấy thà giữ nguồn mạnh và để khâu
#: kịch bản thử các đường mạng cũ (có ngày chúng vẫn qua).
TOP_N_UU_TIEN_KHO = 5


#: Việc 5b (29/09/2026) — trần lượt gọi AI cho lớp kiểm TRÙNG Ý
#: (`core.kiem_trung_y`) MỖI LƯỢT CHỌN NGUỒN: ứng viên đứng đầu trùng ý thì
#: loại, thử ứng viên kế — nhưng dừng ở đây, không loại vô hạn (một kênh vào
#: ngày cạn đề tài mới không được phép cháy hết ví vào việc hỏi đi hỏi lại).
SO_LAN_KIEM_TRUNG_Y_TOI_DA = 3


#: Trần điểm cho tín hiệu "cụm này đang thắng ở kênh ANH EM", tính theo PHẦN của cột
#: cụm (`cong_thuc_v7` `trong_so["cum"]`, 30/100 — cột nặng nhất thang điểm).
#:
#: ═══ VÌ SAO ĐÚNG MỘT NỬA, KHÔNG BẰNG ═══
#:
#: Bốn kênh trong nhóm `tam-ly-nhat` đánh BỐN TỆP KHÁN GIẢ KHÁC NHAU
#: (`CHANNEL/TL1-T7/nghien-cuu/tuyen.csv`): TL4-T7 "sống lệch nhịp số đông", TL1-T7 "tò
#: mò mình là kiểu người nào", TL2-T7 "trung niên thu gọn đời sống", TL3-T7 "bị đánh giá
#: thấp hơn năng lực thật". Một cụm thắng ở tệp "sống lệch nhịp" KHÔNG chắc thắng ở tệp
#: "trung niên" — cùng chữ 片付け mà tệp 1 nghe là "xin được phép bừa" còn tệp 4 nghe là
#: "chỉ tôi cách dọn", hai lời hứa trái nhau (luật phân xử ghi ngay trong `tuyen.csv`).
#:
#: Thêm nữa, "thắng" đọc từ bảng nhóm là một XẤP XỈ RỘNG: bảng không mang mốc 48 giờ nên
#: `nhom_kenh.doc_bang_nhom` đo bằng hiển thị TRỌN ĐỜI (xem docstring hàm ấy), rộng hơn
#: mốc thật của `_danh_dau_thang`.
#:
#: Hai lý do đó cộng lại: tín hiệu anh em là GỢI Ý, không phải mệnh lệnh — luôn nhỏ hơn thành
#: tích CỦA CHÍNH KÊNH MÌNH (số Studio thật của chính kênh, ở đúng mốc, trên đúng tệp của nó).
#:
#: ═══ B7 (30/09/2026): KHÔNG CÒN HẰNG RIÊNG ═══
#:
#: Trần = cột cụm × `cong_thuc_v7.he_so_tien_nghiem(n48, he_so, k, tat_khi)` — CÙNG hàm và CÙNG
#: tham số `thua_huong_nhom` (cong-thuc-v7.json của kênh) mà V7 dùng cho điểm cụm thừa hưởng: mặc
#: định he_so 0,35 × k/(k+n48), n48 = số video RIÊNG đủ 48h, tắt hẳn khi n48 ≥ 6. Trước đây là
#: hằng `TY_LE_DIEM_ANH_EM = 0.5` cố định (15/100 dù kênh đã có bao nhiêu số riêng).

#: Bậc view mà `ung_vien_xep_hang` dùng làm khoá đầu tiên ở chế độ TRƯỚC V7 — tách thành
#: hằng số vì `cong_diem_anh_em` phải xếp lại TRONG TỪNG BẬC, không được vượt bậc.
NGUONG_BAC_VIEW = 100_000


def co_cau_hinh_v7(goc: str, ma_kenh: str) -> bool:
    """Kênh này có Công thức V7 ĐÁNG TIN từ trước lượt này chưa.

    Tách ra từ thân `_chay_mot_ngay_trong_khoa` (hành vi y nguyên) để trạm
    (`core/chi_so_ytb/tram.py`, cửa `/loi-thoai/can-lay`) hỏi được ĐÚNG câu mà
    vòng chọn nguồn hỏi — hai bên phải xếp hạng bằng cùng một bộ, không thì
    danh sách "cần lấy lời thoại" đi hút những video mà vòng chọn nguồn không
    bao giờ nhìn tới.

    Phải kiểm TRƯỚC bước nghiên cứu, vì nghiên cứu (qua `cong_thuc_v7._cham_v7`
    bên trong) tự ghi cấu hình MẶC ĐỊNH ra đĩa nếu thiếu
    (`nap_cau_hinh(ghi_neu_thieu=True)`) — kiểm SAU thì lúc nào cũng thấy "có",
    mất hẳn ý nghĩa "kênh này đã tự khai Công thức V7".

    Kênh EM mới tách khỏi nhóm (`nhom_kenh.tao_kenh_trong_nhom`) đã có SẴN một
    `cong-thuc-v7.json` từ NGÀY ĐẦU — `cong_thuc_v7.cau_hinh_cho_tep` viết nó
    ra ngay lúc tạo kênh, đánh dấu bằng khoá `tep` (mã tệp khán giả). Nhưng
    kênh ấy CHƯA có video thắng THẬT nào để cột "cụm đang thắng" (nặng nhất,
    30/100) có nghĩa — chỉ riêng việc TỆP TỒN TẠI không đủ để tin công thức.
    Kênh có `tep` thì chỉ coi là "đã có V7" khi đã đạt ngưỡng
    `da_co_video_thang` (impressions/CTR/AVD ở mốc 48h thật). Kênh GỐC tự tay
    khai V7 từ đầu (không có khoá `tep` — TL4-T7, kênh 55+ khách hand-tune)
    giữ NGUYÊN hành vi cũ: có tệp cấu hình là dùng V7 ngay.
    """
    duong_v7 = os.path.join(so.thu_muc_nghien_cuu(goc, ma_kenh), v7.TEP_CAU_HINH)
    if not os.path.isfile(duong_v7):
        return False
    ch_v7_truoc, _duong_ch_v7 = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
    if ch_v7_truoc.get("tep"):
        return bool(v7.da_co_video_thang(goc, ma_kenh, ch=ch_v7_truoc))
    return True


def cong_diem_anh_em(goc: str, ma_kenh: str, ds: List[Dict[str, Any]], co_v7_truoc: bool,
                     log: Optional[Callable[[str], None]] = None, *,
                     nguong_bac_view: Optional[float] = None) -> List[Dict[str, Any]]:
    """Cộng điểm "cụm này đang thắng ở kênh ANH EM trong nhóm" vào bảng ứng viên ĐÃ XẾP,
    rồi xếp lại. Trả về CHÍNH `ds` (đã sắp lại tại chỗ, có thêm khoá `diem_anh_em`/`anh_em`
    ở những dòng được cộng).

    ═══ KHOẢNG TRỐNG HÀM NÀY LẤP ═══

    `nhom_kenh` đã cho bốn kênh chia nhau ĐỐI THỦ (`dong_bo_doi_thu`) và DONE-LIST
    (`video_da_lam_ca_nhom`), và `ghi_bang_nhom` ghi mỗi ngày "kênh nào đang thắng cụm
    nào" — nhưng bảng ấy chỉ có màn hình `trung_tam._nhom()` đọc. Vòng chọn nguồn không
    đọc, nên bốn kênh không KÉO NHAU thật: TL4-T7 đã chứng minh cụm "dọn dẹp/nhà cửa"
    thắng, ba kênh em vẫn bắt đầu từ số không.

    ═══ HAI RÀNG BUỘC CỨNG (đây là chỗ dễ làm hỏng nhất) ═══

    **(a) Trọng số anh em NHỎ HƠN của chính mình.** Trần = cột cụm (`trong_so["cum"]`) ×
    `cong_thuc_v7.he_so_tien_nghiem` (B7, 30/09/2026 — cùng hàm/tham số `thua_huong_nhom` với V7:
    0,35 × k/(k+n48), tắt khi đủ video riêng 48h). Lý do đầy đủ ở chú thích trên `NGUONG_BAC_VIEW`:
    bốn kênh đánh bốn TỆP khác nhau, và "thắng" đọc từ bảng nhóm là xấp xỉ rộng.

    Thêm MỘT TRẦN NỮA, chặt hơn: điểm anh em không bao giờ đưa một ứng viên lên BẰNG hay
    QUA ứng viên **TỰ THẮNG** cao nhất — ứng viên mà CHÍNH kênh mình đã có cột cụm
    (`diem_cum > 0`, tức cụm của nó đang thắng trên số liệu Studio thật của kênh này, ở
    đúng mốc, trên đúng tệp này). Nó được nâng lên SÁT, không được vượt. Kênh EM MỚI chưa
    có ứng viên tự thắng nào (chỉ số trắng) thì không có trần này — đúng chỗ tín hiệu anh
    em là thứ duy nhất nó có.

    **(b) Không kéo kênh em ra khỏi TỆP của nó.** Ứng viên chỉ được cộng khi
    `tuyen_con.nhan_dien(tiêu đề)` trả về ĐÚNG mã tệp mà kênh này đang đánh (`tep` trong
    `kenh.yaml`). Đây là ĐÚNG bộ phân loại tệp đang dùng thật: `tuyen_con.dien_chu_de`
    điền cột `Tuyến / Kênh` của sổ content bằng chính nó, và `cong_thuc_v7.cham` lọc theo
    cột ấy (`o_(d, so.COT_TUYEN) == "khac"`). Không nhận ra tệp (`None`) cũng KHÔNG được
    cộng: "chưa biết" không phải "thuộc tệp của tôi". Vi phạm điều này là phá cả chiến
    lược bốn tệp — ba kênh em sẽ lần lượt bị hút về chủ đề của TL4-T7 và nhóm thành bốn
    bản sao của một kênh.

    Kênh không khai `nhom`, không khai `tep`, hay nhóm chưa có `bang-nhom.csv` → trả `ds`
    Y NGUYÊN, không đổi một thứ hạng nào.

    ═══ CỘNG THẾ NÀO Ở HAI CHẾ ĐỘ ═══

    * **Có V7** (`co_v7_truoc=True`): `diem` là một số nguyên 0–100 so được, nên cộng
      THẬT vào khoá xếp hạng — `-(diem + diem_anh_em)`, sắp ỔN ĐỊNH nên ứng viên bằng
      điểm giữ nguyên thứ tự `cham` đã cho.
    * **Trước V7** (kênh em mới, xếp theo sức nổ của kênh NGUỒN): không có `diem` so được
      — bảng "Một nút" xếp theo bậc view → `vuot` → `tang` → `view`. Ở đây điểm anh em chỉ
      là MỘT BIT, chen vào NGAY SAU bậc view: trong CÙNG bậc, ứng viên chạm cụm đang thắng
      ở kênh anh em (và vẫn đúng tệp mình) đứng trước. Không bao giờ vượt bậc view — bậc
      ấy là bằng chứng cứng duy nhất một kênh chỉ số trắng đang có. Một bit chứ không phải
      một thang điểm, vì ở chế độ này kênh chưa có thành tích RIÊNG nào để so tỷ lệ với.

    Không gọi mạng, không tốn ví, không GHI gì lên đĩa (`nap_cau_hinh(ghi_neu_thieu=False)`).
    """
    def ghi_log(dong: str) -> None:
        if log is not None:
            log(dong)

    if len(ds) < 1:
        return ds

    from . import nhom_kenh  # noqa: PLC0415 — nhập muộn, cùng lý do với `_chon_nguon`
    from . import tuyen_con  # noqa: PLC0415

    nhom = nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
    if not nhom:
        return ds
    tep_minh = nhom_kenh.tep_cua_kenh(goc, ma_kenh)
    if not tep_minh:
        # Không biết mình đánh tệp nào thì KHÔNG canh được ràng buộc (b) — thà không cộng.
        ghi_log("  (kênh trong nhóm “{0}” nhưng chưa khai “tep” trong kenh.yaml — bỏ qua điểm "
               "anh em, vì không canh được luật “ứng viên phải còn trong tệp của kênh”.)"
               .format(nhom))
        return ds

    ch, _duong_ch = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
    bang = nhom_kenh.doc_bang_nhom(
        goc, nhom, cum_cua=lambda td: v7.cum_cua_tieu_de(td, ch), bo_kenh=(ma_kenh,))
    if not bang:
        return ds

    # B7 — tiên nghiệm giảm dần theo số video RIÊNG đủ 48h (cùng hàm, cùng tham số với V7).
    th = ch.get("thua_huong_nhom") or {}
    try:
        n48 = sum(1 for v in v7.video_cua_kenh(goc, ma_kenh, ch) if v.hien_thi_48h is not None)
    except Exception:  # noqa: BLE001 — không đọc được số riêng thì coi như chưa có (tiên nghiệm đủ)
        n48 = 0
    he_so = v7.he_so_tien_nghiem(n48, float(th.get("he_so", 0.35) or 0),
                                 k=float(th.get("k_tien_nghiem", 0) or 0),
                                 tat_khi=int(th.get("tat_khi_video_48h", 0) or 0))
    tran = float((ch.get("trong_so") or {}).get("cum", 30) or 30) * he_so
    if tran <= 0:
        ghi_log("  (điểm anh em tắt: kênh đã có {0} video riêng đủ 48h — dùng số riêng.)".format(n48))
        return ds
    # Trần thứ hai: điểm của ứng viên TỰ THẮNG cao nhất. `None` = chưa có ứng viên nào tự
    # thắng (kênh em mới, hoặc chế độ trước V7 vốn không có cột cụm) → không chặn.
    diem_tu_thang = [float(d.get("diem") or 0) for d in ds if float(d.get("diem_cum") or 0) > 0]
    tran_tu_thang = max(diem_tu_thang) if diem_tu_thang else None

    so_cong = 0
    for d in ds:
        tieu_de = str(d.get("tieu_de") or "")
        if not tieu_de:
            continue
        # (c) 29/09/2026 — dòng V7 đã mang điểm cụm THỪA HƯỞNG của kênh anh em
        # (`cong_thuc_v7.thanh_tich_nhom`, khoá `thua_huong`) thì KHÔNG cộng thêm: cùng một
        # tín hiệu "cụm thắng ở kênh anh em" không được đếm hai lần.
        if d.get("thua_huong"):
            continue
        # (b) — cổng TỆP, trước mọi thứ khác.
        nhan = tuyen_con.nhan_dien(tieu_de, str(d.get("kenh") or ""))
        if not nhan or nhan[0] != tep_minh:
            continue
        tot: Optional[Tuple[float, str, str]] = None  # (chỉ số, mã cụm, kênh anh em)
        for c in v7.cum_cua_tieu_de(tieu_de, ch):
            for ma_anh_em, chi_so in (bang.get(c) or {}).items():
                if tot is None or float(chi_so) > tot[0]:
                    tot = (float(chi_so), c, ma_anh_em)
        if tot is None:
            continue
        diem = tran * tot[0]
        if tran_tu_thang is not None:
            # Nâng lên SÁT ứng viên tự thắng, không qua — chừa đúng 1 điểm.
            diem = min(diem, max(0.0, tran_tu_thang - float(d.get("diem") or 0) - 1.0))
        if diem <= 0:
            continue
        d["diem_anh_em"] = round(diem, 1)
        d["anh_em"] = {"kenh": tot[2], "cum": tot[1],
                       "ten_cum": str(((ch.get("cum") or {}).get(tot[1]) or {}).get("ten") or tot[1]),
                       "chi_so": tot[0]}
        d["ly_do"] = list(d.get("ly_do") or []) + [
            "cụm “{0}” đang thắng ở kênh anh em {1} ({2:.0f}%) — cộng {3:g} (trần {4:g} = cột cụm × "
            "tiên nghiệm {5:.2f}, {6} video riêng đủ 48h)".format(
                d["anh_em"]["ten_cum"], tot[2], tot[0] * 100, d["diem_anh_em"], round(tran, 2), he_so, n48)]
        so_cong += 1

    if not so_cong:
        return ds

    if co_v7_truoc:
        ds.sort(key=lambda d: -(float(d.get("diem") or 0) + float(d.get("diem_anh_em") or 0)))
    else:
        bac = NGUONG_BAC_VIEW if nguong_bac_view is None else float(nguong_bac_view)
        ds.sort(key=lambda d: (0 if float(d.get("view") or 0) >= bac else 1,
                               0 if d.get("diem_anh_em") else 1))
    dau = ds[0]
    if dau.get("anh_em"):
        ghi_log("  KÉO NHAU: đầu bảng “{0}” được cộng {1:g} điểm anh em — cụm “{2}” đang thắng ở "
               "kênh {3} ({4:.0f}%) và ứng viên vẫn thuộc tệp “{5}” của kênh này."
               .format(str(dau.get("tieu_de") or dau.get("ma") or "?")[:60], dau["diem_anh_em"],
                       dau["anh_em"]["ten_cum"], dau["anh_em"]["kenh"],
                       dau["anh_em"]["chi_so"] * 100, tep_minh))
    else:
        ghi_log("  {0} ứng viên được cộng điểm anh em (cụm đang thắng ở kênh cùng nhóm), nhưng "
               "đầu bảng vẫn là ứng viên tự mạnh — tín hiệu anh em là gợi ý, không phải mệnh lệnh."
               .format(so_cong))
    return ds


def _cong_diem_anh_em_an_toan(goc: str, ma_kenh: str, ds: List[Dict[str, Any]],
                              co_v7_truoc: bool,
                              ghi_log: Callable[[str], None], *,
                              nguong_bac_view: Optional[float] = None) -> List[Dict[str, Any]]:
    """`cong_diem_anh_em` bọc trong try/except — điểm anh em là một CẢI THIỆN, không phải
    điều kiện để chạy.

    Cửa này chạy trong vòng chọn nguồn 02:00 (và cả trong trạm `/loi-thoai/can-lay`, qua
    `ung_vien_xep_hang`). Một `bang-nhom.csv` hỏng, một `kenh.yaml` thiếu khoá, hay một
    `cong-thuc-v7.json` dị dạng không được phép làm cả đêm ra 0 video — thà mất tín hiệu
    anh em và giữ đúng thứ hạng cũ.
    """
    try:
        return cong_diem_anh_em(goc, ma_kenh, ds, co_v7_truoc, ghi_log, nguong_bac_view=nguong_bac_view)
    except Exception as loi:  # noqa: BLE001 — xem docstring
        ghi_log("  (không cộng được điểm anh em trong nhóm: {0}) — giữ nguyên thứ hạng."
               .format(str(loi)[:120]))
        return ds


#: Công thức chọn nguồn đã đăng ký (29/09/2026, chủ dự án: "Sẽ có NHIỀU công thức, nhiều
#: cách đánh"). Tên → mô tả. Từ 30/09/2026 mỗi công thức là MỘT TỆP trong `core/chien_luoc/`
#: (tự phát hiện — thêm công thức: chép `core/chien_luoc/_mau.py`, xem `docs/kien-thuc/chien-luoc.md`);
#: bảng này đọc từ sổ đăng ký của gói, sổ hỏng thì dùng bản cố định dưới đây.
_CONG_THUC_NGUON_CO_DINH: Dict[str, str] = {
    "v7": "Công thức V7 — cụm đang thắng + bảng đề xuất của kênh (kênh đang lên, có chỉ số)",
    "vph": "Công thức VPH — video đối thủ ĐỘT BIẾN view/giờ so với video cùng tuổi (trend)",
    "mot_nut": "Bảng Một nút — MỚI/VƯỢT/BỨT, xếp theo sức nổ nguồn",
}


def _cong_thuc_tu_so_dang_ky() -> Dict[str, str]:
    try:
        from . import chien_luoc  # noqa: PLC0415

        return chien_luoc.mo_ta_cong_thuc() or dict(_CONG_THUC_NGUON_CO_DINH)
    except Exception:  # noqa: BLE001 — gói công thức hỏng không được làm tu_chay không nạp nổi
        return dict(_CONG_THUC_NGUON_CO_DINH)


CONG_THUC_NGUON: Dict[str, str] = _cong_thuc_tu_so_dang_ky()
#: Khoá kenh.yaml chọn công thức; `tu_dong` = V7 khi đã qua ngưỡng chuyển V7, còn lại VPH.
KHOA_CONG_THUC = "cong_thuc_chon"


def _vph_mac_dinh(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    from . import cong_thuc_vph  # noqa: PLC0415 — nhập muộn: VPH đọc nhiều sổ

    return cong_thuc_vph.ung_vien_chon_nguon(goc, ma_kenh)


def chon_cong_thuc(goc: str, ma_kenh: str, co_v7_truoc: bool) -> Tuple[str, str]:
    """`(tên công thức, lý do)` cho kênh — đọc kenh.yaml `cong_thuc_chon`.

    * `v7`      — V7 theo chỉ định chủ kênh (cần `cong-thuc-v7.json`; chưa có thì VPH).
    * `vph`     — VPH theo chỉ định.
    * `mot_nut` — bảng Một nút cũ (giữ để quay lại được).
    * `tu_dong` / không khai — V7 nếu kênh đã qua ngưỡng chuyển V7 (`co_v7_truoc`, tức
      `co_cau_hinh_v7` → `cong_thuc_v7.da_co_video_thang`), còn lại VPH.
    Đọc đĩa, không gọi mạng; hỏng thì coi như `tu_dong`.
    """
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        cai = {}
    muon = str(cai.get(KHOA_CONG_THUC) or "tu_dong").strip().lower()
    if muon == "v7":
        if os.path.isfile(os.path.join(so.thu_muc_nghien_cuu(goc, ma_kenh), v7.TEP_CAU_HINH)):
            return "v7", "V7 theo chỉ định chủ kênh (kenh.yaml {0}: v7)".format(KHOA_CONG_THUC)
        return "vph", "kenh.yaml chỉ định v7 nhưng kênh chưa có cong-thuc-v7.json — tạm dùng VPH"
    if muon in CONG_THUC_NGUON:
        return muon, "theo chỉ định chủ kênh (kenh.yaml {0}: {1})".format(KHOA_CONG_THUC, muon)
    lech = "" if muon in ("tu_dong", "") else " (giá trị “{0}” lạ, coi như tu_dong)".format(muon)
    if co_v7_truoc:
        return "v7", "tự động: kênh đã có video thắng thật (qua ngưỡng chuyển V7){0}".format(lech)
    return "vph", ("tự động: kênh chưa qua ngưỡng chuyển V7 — chọn theo đột biến đối thủ{0}"
                   .format(lech))


def ung_vien_xep_hang(goc: str, ma_kenh: str, co_v7_truoc: bool, loai_tru: set,
                      cham_v7: Optional[Callable[..., Any]] = None,
                      doc_danh_sach: Optional[Callable[..., Any]] = None,
                      log: Optional[Callable[[str], None]] = None,
                      # ═══ VÁ 28/09/2026 (LỖI 2) ═══ — chống làm trùng theo TIÊU
                      # ĐỀ, cạnh `loai_tru` (chống trùng theo MÃ). Mặc định rỗng
                      # nên MỌI nơi gọi cũ (trạm `/loi-thoai/can-lay`, bài kiểm)
                      # không cần sửa gì vẫn chạy y hệt trước — xem `_chon_nguon`.
                      da_lam_tieu_de: Optional[Sequence[Tuple[str, str]]] = None,
                      nguong_giong_tieu_de: float = trung_tieu_de.NGUONG_GIONG_TIEU_DE_MAC_DINH,
                      # 29/09/2026 — seam cho bài kiểm: thay `cong_thuc_vph.ung_vien_chon_nguon`.
                      cham_vph: Optional[Callable[..., Any]] = None,
                      ) -> List[Dict[str, Any]]:
    """MỌI nguồn chưa làm, ĐÃ XẾP HẠNG, mạnh nhất trước. Xem `_chon_nguon`.

    ═══ NHIỀU CÔNG THỨC CHỌN NGUỒN (29/09/2026) ═══

    Công thức nào dùng cho kênh nào do `chon_cong_thuc` quyết (kenh.yaml `cong_thuc_chon`:
    `vph` | `v7` | `mot_nut` | `tu_dong`, mặc định `tu_dong`), và dòng log "đang dùng công thức
    X vì …" nói rõ lý do. Mọi công thức trả CÙNG một định dạng dòng; lọc `loai_tru` + chống
    trùng tiêu đề ở đây, kiểm trùng ý / ưu tiên kho / giữ nguồn ở `_chon_nguon` — chung cho
    mọi công thức. `co_v7_truoc` giữ nguyên nghĩa cũ (kênh đã qua ngưỡng chuyển V7), nên trạm
    (`/loi-thoai/can-lay`) gọi y như trước vẫn thấy ĐÚNG bảng vòng chọn nguồn thấy.

    Tách khỏi `_chon_nguon` (trước đây hai việc "xếp hạng" và "lấy cái đầu"
    nằm chung một hàm) vì có NGƯỜI THỨ HAI cần đúng bảng này: cửa
    `/loi-thoai/can-lay` của trạm trả về K ứng viên đầu bảng CHƯA có lời thoại
    trong kho, để phiên trình duyệt sáng hôm sau đi hút đúng chúng. Viết một bộ
    xếp hạng thứ hai cho trạm là bảo đảm hai bên lệch nhau sau vài lần sửa —
    và lệch ở đây nghĩa là trình duyệt hút một pool video mà vòng chọn nguồn
    không bao giờ chọn.

    Không gọi mạng, không tốn ví: `cham_v7`/`doc_danh_sach` đọc sổ trên đĩa
    (`cong_thuc_v7.cham` chấm lại bảng đã quét, `mot_nut.doc_danh_sach` đọc
    `danh-sach-chon.json`). Truyền được để bài kiểm thay bằng đồ giả.

    BƯỚC CUỐI của CẢ HAI nhánh: `cong_diem_anh_em` — cộng tín hiệu "cụm này đang thắng ở
    kênh ANH EM trong nhóm" rồi xếp lại. Đặt ở đây (chứ không ở `_chon_nguon`) chính vì lý
    do hàm này tồn tại: trạm `/loi-thoai/can-lay` phải thấy ĐÚNG bảng mà vòng chọn nguồn
    thấy, không thì trình duyệt đi hút lời thoại của một pool khác. Nhóm chưa có
    `bang-nhom.csv`, hay kênh không thuộc nhóm nào → bảng ra Y NGUYÊN như trước.

    ═══ GÓI `core/chien_luoc/` (30/09/2026) ═══

    Thân ba công thức giờ nằm ở `core/chien_luoc/{vph,v7,mot_nut}.py` (chữ ký hàm này, các seam
    `cham_v7`/`doc_danh_sach`/`cham_vph` và `chon_cong_thuc` giữ nguyên). Kênh khai kenh.yaml
    `chien_luoc` thì trộn nhiều công thức + thăm dò tất định (xem `core.chien_luoc.xep_hang`);
    không khai thì bảng Y HỆT trước — `tests/test_chien_luoc_golden.py` canh từng byte.
    """
    return _xep_hang_chien_luoc(goc, ma_kenh, co_v7_truoc, loai_tru, cham_v7=cham_v7,
                                doc_danh_sach=doc_danh_sach, log=log, da_lam_tieu_de=da_lam_tieu_de,
                                nguong_giong_tieu_de=nguong_giong_tieu_de, cham_vph=cham_vph)


def _xep_hang_chien_luoc(goc: str, ma_kenh: str, co_v7_truoc: bool, loai_tru: set, *,
                         cham_v7: Optional[Callable[..., Any]] = None,
                         doc_danh_sach: Optional[Callable[..., Any]] = None,
                         log: Optional[Callable[[str], None]] = None,
                         da_lam_tieu_de: Optional[Sequence[Tuple[str, str]]] = None,
                         nguong_giong_tieu_de: float = trung_tieu_de.NGUONG_GIONG_TIEU_DE_MAC_DINH,
                         cham_vph: Optional[Callable[..., Any]] = None,
                         tham_do: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Thân `ung_vien_xep_hang` (30/09/2026): dựng `NguCanh` rồi giao `core.chien_luoc.xep_hang`.

    Thân ba công thức cũ nay ở `core/chien_luoc/{vph,v7,mot_nut}.py` (dời nguyên văn), bộ lọc chung
    `_bi_trung_tieu_de` ở `NguCanh.loc`. `tham_do=False` ép lượt KHAI THÁC — `_chon_nguon` dùng khi
    lượt thăm dò không có nguồn nào qua cổng chất lượng."""
    from . import chien_luoc  # noqa: PLC0415
    from .chien_luoc import ngu_canh  # noqa: PLC0415

    nc = ngu_canh.dung(goc, ma_kenh, co_v7=co_v7_truoc, loai_tru=loai_tru,
                       da_lam_tieu_de=da_lam_tieu_de, log=log, nguong_giong=nguong_giong_tieu_de,
                       cham_v7=cham_v7, doc_danh_sach=doc_danh_sach, cham_vph=cham_vph)
    return chien_luoc.xep_hang(nc, tham_do=tham_do)


def _uu_tien_co_kho(goc: str, ma_kenh: str, ds: List[Dict[str, Any]],
                    log: Callable[[str], None]) -> Dict[str, Any]:
    """Trong `TOP_N_UU_TIEN_KHO` ứng viên đầu bảng, chọn cái ĐÃ CÓ lời thoại
    trong kho; không ai có thì giữ nguyên đầu bảng.

    Đây là CHỖ DUY NHẤT vòng chọn nguồn biết tới kho lời thoại — xem lý do đầy
    đủ ở `TOP_N_UU_TIEN_KHO`. Kho hỏng/không đọc được thì im lặng giữ đầu bảng:
    ưu tiên này là một cải thiện xác suất, không phải điều kiện để chạy.
    """
    if len(ds) < 2:
        return ds[0]
    try:
        from . import loi_thoai as kho  # noqa: PLC0415 — nhập muộn như các module khác ở đây

        if kho.co_loi_thoai(goc, ma_kenh, str(ds[0].get("ma") or "")):
            return ds[0]
        for d in ds[1:TOP_N_UU_TIEN_KHO]:
            if kho.co_loi_thoai(goc, ma_kenh, str(d.get("ma") or "")):
                log("  đổi nguồn trong nhóm đầu bảng: “{0}” ĐÃ CÓ lời thoại trong kho (trình "
                   "duyệt kênh hút sẵn), còn “{1}” thì chưa — YouTube đang chặn địa chỉ VPS "
                   "này nên nguồn chưa có lời thoại rất dễ chết ở khâu kịch bản."
                   .format(str(d.get("tieu_de") or d.get("ma") or "?")[:60],
                           str(ds[0].get("tieu_de") or ds[0].get("ma") or "?")[:60]))
                return d
    except Exception as loi:  # noqa: BLE001 — kho hỏng không được chặn lượt chạy
        log("  (không đọc được kho lời thoại: {0}) — giữ nguồn đầu bảng.".format(str(loi)[:100]))
    return ds[0]


def _cai_kenh(goc: str, ma_kenh: str, khoa: str, mac_dinh: Any) -> Any:
    """Một khoá của kenh.yaml (đọc thô) — hỏng/thiếu → `mac_dinh`."""
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        return mac_dinh
    gt = cai.get(khoa, mac_dinh)
    if isinstance(mac_dinh, bool) and isinstance(gt, str):
        return gt.strip().lower() not in ("false", "0", "khong", "không", "no", "off")
    return gt if gt is not None else mac_dinh


#: Số ứng viên đầu bảng đưa biên tập viên AI (`core.bien_tap_content.chon`) — một cửa sổ.
SO_UNG_VIEN_BIEN_TAP = 20
#: Cổng chất lượng (30/09/2026): tối đa ngần này cửa sổ (20 dòng/cửa sổ) cho tới khi đủ `SO_TOT_CAN`
#: nguồn TỐT — bảng công thức đầu có nhiều dòng lệch ngách thì biên tập viên đọc sâu hơn.
SO_CUA_SO_BIEN_TAP = 3
SO_TOT_CAN = 3
#: Không có nguồn TỐT nào thì chỉ nhận TẠM có điểm biên tập ≥ ngưỡng này (và có lý do); không có thì
#: KHÔNG mở lượt (log rõ + cắm cờ nghiên cứu lại) — tiền sản xuất không đổ vào nguồn biên tập viên chê.
NGUONG_TAM_DUNG = 65


def _ap_cham_bien_tap(ds: List[Dict[str, Any]], ket: Dict[str, Any],
                      log: Callable[[str], None]) -> List[Dict[str, Any]]:
    """Áp phán quyết của cổng chất lượng (`bien_tap_content.chon_cua_so`) lên bảng công thức:
    dòng TỐT/TẠM theo thứ tự biên tập (mang `bien_tap` = hạng/điểm/lý do), dòng TỆ BỊ BỎ HẲN (không nối
    lại cuối bảng như trước — trước đó cửa kho lời thoại còn vớt được một dòng bị loại), dòng chưa
    được chấm (ngoài các cửa sổ đã đọc) giữ sau cùng theo thứ tự công thức, không có `bien_tap`."""
    theo_ma = {str(d.get("ma") or ""): (i, d) for i, d in enumerate(ds)}
    hang = {so.ma_video(str(k)) or str(k): v for k, v in (ket.get("hang") or {}).items()}
    diem = {so.ma_video(str(k)) or str(k): v for k, v in (ket.get("diem_bt") or {}).items()}
    ly = {so.ma_video(str(k)) or str(k): v for k, v in (ket.get("ly_do") or {}).items()}
    du_doan = {so.ma_video(str(k)) or str(k): v for k, v in (ket.get("du_doan") or {}).items()}
    moi: List[Dict[str, Any]] = []
    da: set = set()
    for muc in ket.get("thu_tu") or []:
        ma = so.ma_video(str(muc)) or str(muc)
        if ma not in theo_ma or ma in da or hang.get(ma) not in ("TOT", "TAM"):
            continue
        i, d = theo_ma[ma]
        d = dict(d)
        d["bien_tap"] = {"hang_cong_thuc": i + 1, "ly_do": str(ly.get(ma) or ""), "hang": hang[ma],
                         "diem": diem.get(ma), "du_doan": du_doan.get(ma) or {}}
        if ly.get(ma):
            d["ly_do"] = list(d.get("ly_do") or []) + ["Biên tập AI [{0}{1}]: {2}".format(
                hang[ma], " {0}".format(diem[ma]) if diem.get(ma) is not None else "", str(ly[ma])[:300])]
        moi.append(d)
        da.add(ma)
    bo = [ma for ma, h in hang.items() if h == "TE" and ma in theo_ma]
    con = [d for d in ds if str(d.get("ma") or "") not in da and str(d.get("ma") or "") not in hang]
    if moi:
        log("  Biên tập AI xếp lại {0} ứng viên đã chấm (bỏ {1} TỆ) — đầu bảng mới: “{2}” [{3}] (hạng {4} của "
            "công thức).".format(len(moi), len(bo), str(moi[0].get("tieu_de") or "")[:60],
                                 moi[0]["bien_tap"]["hang"], moi[0]["bien_tap"]["hang_cong_thuc"]))
    else:
        log("  Biên tập AI: không ứng viên nào đạt TỐT/TẠM trong {0} dòng đã chấm (bỏ {1} TỆ).".format(
            len(hang), len(bo)))
    return moi + con


def _cong_chat_luong(ds: List[Dict[str, Any]], log: Callable[[str], None]) -> List[Dict[str, Any]]:
    """KIỂM TRA CHẤT LƯỢNG NGUỒN CUỐI CÙNG (30/09/2026, chủ dự án: "chọn content đúng quyết định 80%").

    Có phán quyết biên tập (dòng mang `bien_tap.hang`): chỉ cho qua nguồn TỐT CÓ LÝ DO BIÊN TẬP RÕ.
    Không có TỐT nào → TẠM có lý do và điểm ≥ `NGUONG_TAM_DUNG` (log CẢNH BÁO). Vẫn không có → trả []
    (nơi gọi không mở lượt, cắm cờ nghiên cứu lại). Dòng không đạt được log từng dòng — không im lặng.
    Không có phán quyết nào (chế độ thử, biên tập tắt/hỏng) → giữ nguyên bảng, log một dòng."""
    co_cham = [d for d in ds if isinstance(d.get("bien_tap"), dict) and d["bien_tap"].get("hang")]
    if not co_cham:
        if ds:
            log("  [CỔNG NGUỒN] bảng chưa qua biên tập AI (tắt/hỏng/chế độ thử) — dùng thứ tự công thức.")
        return ds

    def co_ly_do(d: Dict[str, Any]) -> bool:
        return len(str(d["bien_tap"].get("ly_do") or "").strip()) >= 8

    tot = [d for d in co_cham if d["bien_tap"]["hang"] == "TOT" and co_ly_do(d)]
    for d in co_cham:
        if d["bien_tap"]["hang"] == "TOT" and not co_ly_do(d):
            log("  [CỔNG NGUỒN] bỏ “{0}”: chấm TỐT nhưng không có lý do biên tập rõ.".format(
                str(d.get("tieu_de") or "")[:60]))
    if tot:
        log("  [CỔNG NGUỒN] {0} nguồn TỐT qua cổng: {1}".format(len(tot), " | ".join(
            "“{0}” ({1})".format(str(d.get("tieu_de") or "")[:40], d["bien_tap"].get("diem")) for d in tot[:3])))
        return tot
    tam = [d for d in co_cham if d["bien_tap"]["hang"] == "TAM" and co_ly_do(d)
           and float(d["bien_tap"].get("diem") or 0) >= NGUONG_TAM_DUNG]
    if tam:
        log("  [CỔNG NGUỒN] CẢNH BÁO: không có nguồn TỐT — dùng nguồn TẠM điểm cao nhất “{0}” ({1}): {2}".format(
            str(tam[0].get("tieu_de") or "")[:60], tam[0]["bien_tap"].get("diem"),
            str(tam[0]["bien_tap"].get("ly_do") or "")[:160]))
        return tam
    log("  [CỔNG NGUỒN] KHÔNG nguồn nào đạt (0 TỐT, 0 TẠM ≥ {0} điểm có lý do, trong {1} dòng đã chấm) — không mở "
        "lượt, không tốn tiền sản xuất; cắm cờ để nghiên cứu nhóm tìm nguồn mới.".format(NGUONG_TAM_DUNG, len(co_cham)))
    return []


def _chuan_hoa_cho_bien_tap(goc: str, ma_kenh: str, d: Dict[str, Any], ten_ct: str,
                            tep: str) -> Dict[str, Any]:
    """Một dòng ứng viên đủ trường cho biên tập viên AI — công thức nào thiếu trường thì None."""
    ra = dict(d)
    ra.setdefault("cong_thuc", ten_ct)
    ra.setdefault("tep", tep)
    for khoa in ("tuoi_gio", "vph", "dot_bien", "view"):
        ra.setdefault(khoa, None)
    ra.setdefault("cum", [])
    ra["diem_cong_thuc"] = d.get("diem")
    return ra


def _bien_tap_ai(goc: str, ma_kenh: str, ds: List[Dict[str, Any]],
                 goi_chat: Optional[Callable[..., str]], co_v7_truoc: bool,
                 log: Callable[[str], None]) -> List[Dict[str, Any]]:
    """ĐIỂM MÓC biên tập viên AI (29/09/2026): sau khi công thức ra bảng đã lọc, đưa
    `SO_UNG_VIEN_BIEN_TAP` dòng đầu cho `core.bien_tap_content.chon(goc, ma_kenh, top,
    goi_chat)` (module của người khác — chưa có thì bỏ qua) nếu kenh.yaml `bien_tap_ai`
    (mặc định bật). Nó trả thứ tự mới + lý do; lỗi hay trả lạ → GIỮ thứ tự của công thức.
    Lý do được gắn vào dòng (`bien_tap`, `ly_do`) nên đi theo `nguon` vào sổ lượt."""
    if goi_chat is None or len(ds) < 1 or not _cai_kenh(goc, ma_kenh, "bien_tap_ai", True):
        return ds
    try:
        from . import bien_tap_content  # noqa: PLC0415
    except ImportError:
        return ds
    ham = getattr(bien_tap_content, "chon", None)
    if not callable(ham):
        return ds
    ten_ct, _ly = chon_cong_thuc(goc, ma_kenh, co_v7_truoc)
    tep = str(_cai_kenh(goc, ma_kenh, "tep", "") or "")
    # 30/09/2026 — CỔNG CHẤT LƯỢNG: `chon_cua_so` chấm TỪNG ứng viên TỐT/TẠM/TỆ theo cửa sổ 20 dòng,
    # mở cửa sổ kế khi chưa đủ nguồn TỐT (tới `SO_CUA_SO_BIEN_TAP` cửa sổ), nhớ phán quyết 18 giờ.
    ham_cs = getattr(bien_tap_content, "chon_cua_so", None)
    if callable(ham_cs):
        day_du = [_chuan_hoa_cho_bien_tap(goc, ma_kenh, d, ten_ct, tep)
                  for d in ds[:SO_UNG_VIEN_BIEN_TAP * SO_CUA_SO_BIEN_TAP]]
        try:
            ket_cs = ham_cs(goc, ma_kenh, day_du, goi_chat, can_tot=SO_TOT_CAN, ghi=log)
        except Exception as loi:  # noqa: BLE001
            log("  (biên tập AI hỏng: {0}) — giữ thứ tự của công thức.".format(str(loi)[:120]))
            return ds
        if isinstance(ket_cs, dict) and isinstance(ket_cs.get("hang"), dict):
            return _ap_cham_bien_tap(ds, ket_cs, log)
        return ds
    top = [_chuan_hoa_cho_bien_tap(goc, ma_kenh, d, ten_ct, tep) for d in ds[:SO_UNG_VIEN_BIEN_TAP]]
    try:
        try:
            ket = ham(goc, ma_kenh, top, goi_chat, ghi=log)
        except TypeError:
            ket = ham(goc, ma_kenh, top, goi_chat)
    except Exception as loi:  # noqa: BLE001 — biên tập viên hỏng thì giữ thứ tự công thức
        log("  (biên tập AI hỏng: {0}) — giữ thứ tự của công thức.".format(str(loi)[:120]))
        return ds
    ly_chung = ""
    ly_theo_ma: Dict[str, str] = {}
    thu_tu: Any = ket
    if isinstance(ket, tuple) and ket:
        thu_tu, ly_chung = ket[0], (str(ket[1]) if len(ket) > 1 and ket[1] else "")
    elif isinstance(ket, dict):
        thu_tu = ket.get("thu_tu") or ket.get("ung_vien") or ket.get("ds") or []
        ly_raw = ket.get("ly_do")
        if isinstance(ly_raw, dict):
            for khoa, gia in ly_raw.items():
                ma_k = so.ma_video(str(khoa)) or str(khoa)
                ly_theo_ma[ma_k] = str(gia or "")
        else:
            ly_chung = str(ly_raw or "")
    if not isinstance(thu_tu, (list, tuple)) or not thu_tu:
        return ds
    theo_ma = {str(d.get("ma") or ""): (i, d) for i, d in enumerate(ds[:SO_UNG_VIEN_BIEN_TAP])}
    moi: List[Dict[str, Any]] = []
    da: set = set()
    for muc in thu_tu:
        ma, ly = "", ""
        if isinstance(muc, dict):
            ma = str(muc.get("ma") or so.ma_video(str(muc.get("link") or "")) or "")
            ly = str(muc.get("ly_do_bien_tap") or muc.get("ly_do_chon") or "")
        elif isinstance(muc, int) and 0 <= muc < len(top):
            ma = str(top[muc].get("ma") or "")
        else:
            ma = so.ma_video(str(muc or "")) or str(muc or "")
        if ma not in theo_ma or ma in da:
            continue
        ly = ly or ly_theo_ma.get(ma, "")
        i, d = theo_ma[ma]
        d = dict(d)
        d["bien_tap"] = {"hang_cong_thuc": i + 1, "ly_do": ly or ly_chung}
        if ly or ly_chung:
            d["ly_do"] = list(d.get("ly_do") or []) + ["Biên tập AI: " + (ly or ly_chung)[:300]]
        moi.append(d)
        da.add(ma)
    if not moi:
        return ds
    con = [d for d in ds[:SO_UNG_VIEN_BIEN_TAP] if str(d.get("ma") or "") not in da]
    log("  Biên tập AI xếp lại {0} ứng viên đầu bảng — đầu bảng mới: “{1}” (hạng {2} của công thức)."
        .format(len(moi), str(moi[0].get("tieu_de") or "")[:60], moi[0]["bien_tap"]["hang_cong_thuc"]))
    return moi + con + list(ds[SO_UNG_VIEN_BIEN_TAP:])


def _chon_nguon(goc: str, ma_kenh: str, co_v7_truoc: bool, loai_tru: set,
                cham_v7: Callable[..., Any], doc_danh_sach: Callable[..., Any],
                log: Callable[[str], None],
                # ═══ VÁ 28/09/2026 (LỖI 2) ═══ — mặc định rỗng, mọi nơi gọi cũ
                # (bài kiểm cũ, v.v.) không cần sửa vẫn chạy y hệt trước.
                da_lam_tieu_de: Optional[Sequence[Tuple[str, str]]] = None,
                nguong_giong_tieu_de: float = trung_tieu_de.NGUONG_GIONG_TIEU_DE_MAC_DINH,
                # ═══ VIỆC 5b (29/09/2026) ═══ — lớp kiểm NGỮ NGHĨA rẻ, bổ sung
                # cho so chữ ở trên. Mặc định `goi_chat=None`/`kiem_trung_y_bat=
                # False` nên mọi nơi gọi cũ (bài kiểm cũ…) chạy y hệt trước —
                # cùng nếp với `da_lam_tieu_de` phía trên.
                goi_chat: Optional[Callable[..., str]] = None,
                kiem_trung_y_bat: bool = False,
                #: (29/09/2026) dict nhận `so_ung_vien` — số ứng viên xếp hạng được
                #: sau mọi lớp loại, để nơi gọi biết kho sắp cạn (nghiên cứu nhóm).
                thong_ke: Optional[Dict[str, Any]] = None,
                ) -> Optional[Dict[str, Any]]:
    """Chọn MỘT nguồn chưa làm: lấy đầu bảng `ung_vien_xep_hang`, nhưng ƯU TIÊN
    ứng viên ĐÃ CÓ lời thoại trong kho (xem `_uu_tien_co_kho`).

    Kênh ĐÃ có cấu hình Công thức V7 (từ trước lượt này): CHỈ nhận ứng viên
    đạt `loai` "Làm ngay"/"Nên làm" và không bị loại ở cổng nào (`bi_loai`
    rỗng) — V7 đã có ý kiến thì không rơi về bảng "Một nút" nữa, vì bảng đó
    không mang phán đoán chất lượng của V7 (cụm đang thắng, bảng đề xuất,
    nguồn nổ thật…). Không có ứng viên nào đạt mức ấy thì KHÔNG sản xuất hôm
    nay, không phải lỗi.

    Kênh CHƯA có cấu hình V7 (kể cả kênh EM có "tep" nhưng chưa qua ngưỡng
    `da_co_video_thang`, xem nơi gọi): gộp ba bảng "Một nút" đã xếp —
    `moi` ∪ `vuot` ∪ `but` (`danh-sach-chon.json`, khử trùng theo link) — rồi
    tự xếp lại theo SỨC NỔ THẬT của từng ứng viên, vì bảng MỚI vốn chỉ xếp
    theo thứ tự quét được, không theo view: mạnh nhất trước
    (`view ≥ 100.000`), sau đó `vượt` (chặn trần 25 — quá trần không còn đáng
    tin, tránh một kênh cá biệt ăn hẳn bảng), rồi `Tăng/ngày`, cuối cùng
    `view` thô. Đây là bảng nguồn cho kênh EM MỚI (chưa có video thắng để
    Công thức V7 chấm được) — thấy MỘT NGUỒN ĐANG NỔ ĐÚNG TỆP mình còn quan
    trọng hơn thấy đúng thứ tự quét.

    ═══ ƯU TIÊN VIDEO ĐÃ CÓ LỜI THOẠI — MỘT CHỖ, MỘT LẦN (22/09/2026) ═══

    Cả hai bảng (V7 và "Một nút") xếp hạng theo SỨC NỔ của video nguồn, và đó
    vẫn đúng. Nhưng từ đêm 22/09/2026 có thêm một điều kiện cần: nguồn nào
    KHÔNG có lời thoại trong kho thì khâu `kich-ban` phải đi xin YouTube, mà
    YouTube đang chặn địa chỉ VPS này — tức nguồn ấy rất dễ thành 0 video. Nên
    sau khi xếp hạng xong, một cửa duy nhất (`_uu_tien_co_kho`) đổi trong nhóm
    đầu bảng nếu cần. Thứ tự xếp hạng KHÔNG bị sửa; chỉ bước "lấy cái nào"
    trong nhóm đầu là có ý kiến thêm.

    ═══ ĐIỂM ANH EM ĐỨNG TRƯỚC CỬA KHO, KHÔNG ĐỨNG SAU ═══

    `ung_vien_xep_hang` đã cộng tín hiệu "cụm đang thắng ở kênh anh em"
    (`cong_diem_anh_em`) và xếp lại TRƯỚC khi bảng tới đây, nên `_uu_tien_co_kho`
    vẫn nhìn vào "nhóm `TOP_N_UU_TIEN_KHO` đầu bảng" như cũ — chỉ là nhóm ấy giờ
    đã tính cả tín hiệu nhóm. Thứ tự ưu tiên "CÓ LỜI THOẠI TRONG KHO" vẫn là
    tiếng nói CUỐI CÙNG và không bị điểm anh em lật: một nguồn điểm cao mà khâu
    `kich-ban` không sản xuất được vẫn là 0 video, dù cả nhóm có thắng cụm đó.

    ═══ VIỆC 5b — KIỂM TRÙNG Ý TRƯỚC KHI CHỐT (29/09/2026) ═══

    Sau `_uu_tien_co_kho`, `kiem_trung_y_bat=True` (từ `kenh.kiem_trung_y`) thì
    ứng viên ĐANG ĐỨNG ĐẦU (dù đến từ nhánh V7 hay nhánh "Một nút" — cả hai đều
    đi qua `ds`/`_uu_tien_co_kho` như nhau) được hỏi thêm một lượt AI NGẮN: có
    CÙNG CHỦ ĐỀ/LUẬN ĐIỂM với video nào kênh ĐÃ LÀM không (`core.kiem_trung_y`,
    bổ sung cho so CHỮ ở `nguong_giong_tieu_de` — bắt ca "cùng ý khác diễn
    đạt"). Trùng thì loại, thử ứng viên kế, tối đa `SO_LAN_KIEM_TRUNG_Y_TOI_DA`
    lượt gọi. `goi_chat=None` (chế độ "thu", hoặc kênh tắt cờ) thì bỏ qua hẳn
    lớp này — xem `_chay_mot_ngay_trong_khoa`, nơi gọi CHỈ đưa `goi_chat` thật
    khi `che_do == "that"`.
    """
    # Người vận hành đã chốt ở tab “Chọn content” thì quyết định ấy đứng trước
    # vòng chọn tự động. Mỗi kênh chỉ có một tệp lựa chọn, nên không thể biến
    # thành kho video chờ. Nếu nguồn đã làm rồi, bỏ qua và để công thức chọn mới.
    try:
        from . import chon_content as lua_tay  # noqa: PLC0415

        lua = lua_tay.doc_lua_chon(goc, ma_kenh)
        uv = lua.ung_vien if lua is not None else None
        if uv is not None and uv.ma and uv.ma not in loai_tru and uv.link:
            # (LỖI 2) content CHỐT TAY cũng phải qua chống trùng tiêu đề — người
            # vận hành chốt tay trước khi biết kênh vừa remake đúng chủ đề đó
            # (qua nguồn khác mã) vẫn là trùng nội dung, không phải ngoại lệ.
            trung = (trung_tieu_de.tim_tieu_de_trung(uv.tieu_de, da_lam_tieu_de, nguong_giong_tieu_de)
                    if da_lam_tieu_de else None)
            if trung is not None:
                _tieu_de_cu, mo_ta, diem = trung
                log("  content đã chốt tay (“{0}”) TRÙNG TIÊU ĐỀ với {1} (giống {2:.0%}) — bỏ qua, "
                   "để công thức tự chọn nguồn khác.".format(uv.tieu_de[:70], mo_ta, diem))
            else:
                log("  dùng content đã chốt: “{0}” ({1}, {2} điểm).".format(
                    uv.tieu_de[:70], "V7" if uv.luong == lua_tay.LUONG_V7 else "đối thủ", uv.diem))
                lua_tay.danh_dau_dang_san_xuat(goc, ma_kenh)
                return {
                    "nguon": "v7" if uv.luong == lua_tay.LUONG_V7 else "doi-thu",
                    "ma": uv.ma, "link": uv.link, "tieu_de": uv.tieu_de,
                    "kenh": uv.kenh_nguon, "diem": uv.diem, "loai": uv.muc,
                    "ly_do": [uv.ly_do], "chon_tay": True,
                }
    except Exception as loi:  # noqa: BLE001 — tệp chốt hỏng không được chặn lịch
        log("  (không đọc được content đã chốt: {0}) — để công thức tự chọn.".format(str(loi)[:100]))

    ds = ung_vien_xep_hang(goc, ma_kenh, co_v7_truoc, loai_tru,
                           cham_v7=cham_v7, doc_danh_sach=doc_danh_sach, log=log,
                           da_lam_tieu_de=da_lam_tieu_de, nguong_giong_tieu_de=nguong_giong_tieu_de)
    # 29/09/2026 — CỤM THEO NGHĨA (chủ dự án: "lọc theo từ khoá là SAI"): có ví thì cho AI
    # phân cụm các tiêu đề chưa phân (ứng viên đầu bảng, video mình + anh em, trang chủ), rồi
    # xếp lại bằng nhãn mới. Chỉ ở đây vì chỉ ở đây có `goi_chat` (che_do "that").
    if goi_chat is not None and ds and _cai_kenh(goc, ma_kenh, "phan_cum_ai", True):
        try:
            from . import phan_cum_ai  # noqa: PLC0415

            ch_v7_pc, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
            moi_pc = phan_cum_ai.lam_nong(
                goc, ma_kenh, ch_v7_pc, goi_chat, [str(d.get("tieu_de") or "") for d in ds[:200]],
                mo_hinh=str(_cai_kenh(goc, ma_kenh, "mo_hinh", "claude-sonnet-5") or "claude-sonnet-5"),
                log=log)
            if moi_pc:
                ds = ung_vien_xep_hang(goc, ma_kenh, co_v7_truoc, loai_tru,
                                       cham_v7=cham_v7, doc_danh_sach=doc_danh_sach, log=None,
                                       da_lam_tieu_de=da_lam_tieu_de,
                                       nguong_giong_tieu_de=nguong_giong_tieu_de) or ds
        except Exception as loi:  # noqa: BLE001 — phân cụm AI hỏng thì giữ nhãn từ khoá
            log("  (AI phân cụm theo nghĩa hỏng: {0}) — dùng từ khoá.".format(str(loi)[:120]))
    la_tham_do = any(d.get("tham_do") for d in ds)
    ds = _bien_tap_ai(goc, ma_kenh, ds, goi_chat, co_v7_truoc, log)
    if goi_chat is not None:
        ds = _cong_chat_luong(ds, log)
        if not ds and la_tham_do:
            # 30/09/2026 — lượt THĂM DÒ (kenh.yaml `chien_luoc`) không có nguồn nào qua cổng: lùi về
            # bảng KHAI THÁC ngay trong lượt này, không để thăm dò làm kênh mất một ngày.
            log("  [CHIẾN LƯỢC] lượt thăm dò không có nguồn qua cổng — lùi về bảng khai thác.")
            ds = _xep_hang_chien_luoc(goc, ma_kenh, co_v7_truoc, loai_tru, cham_v7=cham_v7,
                                      doc_danh_sach=doc_danh_sach, log=log,
                                      da_lam_tieu_de=da_lam_tieu_de,
                                      nguong_giong_tieu_de=nguong_giong_tieu_de, tham_do=False)
            ds = _cong_chat_luong(_bien_tap_ai(goc, ma_kenh, ds, goi_chat, co_v7_truoc, log), log)
    if thong_ke is not None:
        thong_ke["so_ung_vien"] = len(ds)
    if not ds:
        return None
    if not kiem_trung_y_bat or goi_chat is None or not da_lam_tieu_de:
        return _uu_tien_co_kho(goc, ma_kenh, ds, log)
    return _chon_khong_trung_y(goc, ma_kenh, ds, log, da_lam_tieu_de=da_lam_tieu_de,
                               goi_chat=goi_chat)


def _chon_khong_trung_y(goc: str, ma_kenh: str, ds: List[Dict[str, Any]],
                        log: Callable[[str], None], *,
                        da_lam_tieu_de: Sequence[Tuple[str, str]],
                        goi_chat: Callable[..., str],
                        ) -> Optional[Dict[str, Any]]:
    """Việc 5b (29/09/2026): như `_uu_tien_co_kho`, nhưng ứng viên đứng đầu còn
    phải qua lớp kiểm TRÙNG Ý (`core.kiem_trung_y`) — trùng thì loại, thử ứng
    viên kế trong `ds`, tối đa `SO_LAN_KIEM_TRUNG_Y_TOI_DA` lượt gọi AI.

    Hết lượt gọi (mọi ứng viên đã thử đều trùng ý) thì DỪNG KIỂM, lấy ứng viên
    tốt nhất còn lại KHÔNG kiểm thêm — giữ đúng nếp "không chặn sản xuất": thà
    một ứng viên chưa chắc trùng còn hơn không sản xuất gì đêm nay.
    """
    da_loai: set = set()
    for lan in range(1, SO_LAN_KIEM_TRUNG_Y_TOI_DA + 1):
        con_lai = [d for d in ds if str(d.get("ma") or "") not in da_loai]
        if not con_lai:
            return None
        ung_vien = _uu_tien_co_kho(goc, ma_kenh, con_lai, log)
        tieu_de = str(ung_vien.get("tieu_de") or "")
        ma = str(ung_vien.get("ma") or "")
        trung, voi, ly_do = kiem_trung_y.kiem_trung_y(
            goi_chat, tieu_de, da_lam_tieu_de,
            khoa=_khoa_kiem_trung_y(ma_kenh, ma, lan), ghi=log)
        if not trung:
            return ung_vien
        log("  [Việc 5b] loại “{0}” — TRÙNG Ý với “{1}”: {2} (lượt kiểm {3}/{4})."
           .format(tieu_de[:60], voi[:60] or "?", ly_do[:150] if ly_do else "không rõ lý do",
                   lan, SO_LAN_KIEM_TRUNG_Y_TOI_DA))
        da_loai.add(ma)
        # 30/09/2026: nhớ TỆ vào bộ nhớ cổng chất lượng (`bien-tap/nho-cham.json`) — lượt sau biên tập
        # viên khỏi chấm lại, lớp này khỏi tốn thêm một lượt kiểm cho đúng nguồn ấy. Hỏng thì bỏ qua.
        try:
            from . import bien_tap_content  # noqa: PLC0415

            danh_dau = getattr(bien_tap_content, "danh_dau_te", None)
            if danh_dau is not None:
                danh_dau(goc, ma_kenh, ma, link=str(ung_vien.get("link") or ""), tieu_de=tieu_de,
                         ly_do="trùng ý “{0}”: {1}".format(voi[:60], ly_do[:200] if ly_do else ""))
        except Exception:  # noqa: BLE001
            pass
    con_lai = [d for d in ds if str(d.get("ma") or "") not in da_loai]
    if not con_lai:
        return None
    log("  [Việc 5b] đã thử {0} ứng viên, vẫn trùng ý — dừng kiểm ở lượt gọi này, "
       "lấy ứng viên còn lại tốt nhất, không kiểm thêm.".format(SO_LAN_KIEM_TRUNG_Y_TOI_DA))
    return _uu_tien_co_kho(goc, ma_kenh, con_lai, log)


def _khoa_kiem_trung_y(ma_kenh: str, ma_ung_vien: str, lan: int) -> str:
    """Idempotency-Key ASCII cho một lượt gọi kiểm trùng ý — `goi_van_ban` tự
    sanitize non-ASCII, nhưng mã kênh/mã video ở đây vốn đã ASCII (mã YouTube,
    mã kênh kiểu "TL1-T7")."""
    return "{0}:kiem-trung-y:{1}:k{2}".format(ma_kenh or "?", ma_ung_vien or "?", lan)


def _uoc_chi_phi_micro(kenh, gia: PriceTable) -> int:
    """Ước tiền một video của kênh này, µVND — từ số phút mục tiêu, theo đúng
    cách `core/uoc_tinh_tool.py` quy phút ra số cảnh (80% trần giây/cảnh của
    engine). Không gọi mạng: dùng giá mặc định hoặc giá đã truyền vào."""
    engine = str(getattr(kenh, "engine", "") or "").strip().lower()
    if engine not in (ENGINE_VEO3, ENGINE_SEEDANCE):
        engine = ENGINE_VEO3
    phut = max(0.1, float(getattr(kenh, "phut_muc_tieu", 10.0) or 10.0))
    so_canh = max(1, int(round(phut * 60.0 / target_seconds_for(engine))))
    ky_tu = int(getattr(kenh, "ky_tu_muc_tieu", 0) or 0)
    return (hold_for_image(so_canh, gia) + hold_for_video(engine, gia) * so_canh
            + hold_for_tts(ky_tu, gia))


def _vnd(n: int) -> str:
    return "{0:,}".format(int(n)).replace(",", ".") + "₫"


def _byte_nguoi_doc(n: int) -> str:
    """`5_242_880` → `"5,0 MB"` — chỉ để hiện trong sổ ngày, không tính lại."""
    so_ = float(int(n or 0))
    if so_ < 1024.0:
        return "{0} B".format(int(so_))
    for don_vi in ("KB", "MB", "GB"):
        so_ /= 1024.0
        if so_ < 1024.0 or don_vi == "GB":
            return "{0:.1f} {1}".format(so_, don_vi).replace(".", ",")
    return "{0:.1f} GB".format(so_).replace(".", ",")


def _dung_luong_trong_gb(goc: str) -> Optional[float]:
    """GB còn trống trên ổ chứa `goc` — `None` nếu hỏi hệ điều hành không được
    (quyền bị chặn, ổ mạng rớt…). Không mạng, chỉ một lời gọi hệ thống cục bộ
    (`shutil.disk_usage`, giống `core/trung_tam.py _o_dia` dùng cho bảng tổng
    quan — không nhập trực tiếp từ đó để tránh vòng nhập lẫn nhau, hai tệp
    cùng nhìn một API stdlib là đủ)."""
    try:
        _tong, _dung, con = shutil.disk_usage(goc)
    except OSError:
        return None
    return con / 1024 ** 3


def _uoc_dung_luong_video_gb(kenh) -> float:
    """Ước dung lượng đĩa MỘT video của kênh này cần, GB — theo phút mục tiêu
    (kênh dài hơn thì ảnh/clip/giọng đọc nhiều hơn), cộng biên dự phòng cố
    định. Xem `GB_MOI_PHUT_VIDEO`/`BIEN_DU_PHONG_DIA_GB` đầu tệp cho căn cứ
    chọn số."""
    phut = max(0.1, float(getattr(kenh, "phut_muc_tieu", 10.0) or 10.0))
    return phut * GB_MOI_PHUT_VIDEO + BIEN_DU_PHONG_DIA_GB


def _kiem_dia(con_trong_gb: Optional[float], can_gb: float) -> Tuple[bool, str]:
    """Đĩa còn đủ chỗ để mở/chạy tiếp MỘT video của kênh này không.

    `con_trong_gb` là `None` khi không hỏi được dung lượng còn trống — coi
    như KHÔNG ĐỦ: an toàn hơn liều mở một video giữa lúc không biết còn bao
    nhiêu chỗ, cùng luật "không rõ thì coi là chưa đủ điều kiện" ở những van
    khác trong tệp này (ví dụ `_tim_gio_trong` không đoán bừa một mốc)."""
    if con_trong_gb is None:
        return False, ("không hỏi được dung lượng đĩa còn trống — coi như không đủ, dừng, không "
                       "sản xuất (an toàn hơn liều mở một video giữa lúc không biết còn bao nhiêu "
                       "chỗ trên đĩa).")
    if con_trong_gb < can_gb:
        return False, ("đĩa còn {0:.1f} GB, dưới ngưỡng an toàn {1:.1f} GB cho một video của kênh "
                       "này (đã cộng biên dự phòng) — dừng, không mở/chạy tiếp video, chờ dọn khẩn "
                       "hoặc dọn tay giải phóng thêm chỗ.").format(con_trong_gb, can_gb)
    return True, ""


def _tam_dung_vi_het_tien(goc: str, run: Dict[str, Any], chi_tiet: str,
                         log: Callable[[str], None]) -> None:
    """Ví hết tiền (402) giữa lượt — DỪNG ÊM, giữ nguyên phần đã làm (mọi khâu đã
    xong nằm trên đĩa). Ghi cho van ví (`core.van_vi`) để lượt sau chỉ chạy tiếp
    khi ví đã được nạp, và ĐỔI câu lỗi + xoá bộ đếm phục hồi của lượt để trần L3
    (lỗi HET_TIEN lặp / 3 lần / 48 giờ) KHÔNG bỏ oan lượt chỉ vì chờ nạp tiền."""
    try:
        from . import van_vi  # noqa: PLC0415

        van_vi.ghi_het_tien(goc, chi_tiet)
    except Exception:  # noqa: BLE001
        pass
    sx = run.setdefault("san_xuat", {})
    sx["loi_goc"] = str(chi_tiet)[:400]
    sx["loi"] = "tạm dừng chờ nạp ví — phần đã làm được giữ nguyên, tự chạy tiếp khi ví đủ tiền"
    sx["tam_dung_vi"] = True
    run["phuc_hoi"] = {}
    log("  [VÍ HẾT TIỀN] dừng êm, giữ phần đã làm; sẽ tự chạy tiếp khi ví được nạp.")


def _nhan_het_tien_tu_luot(goc: str, run: Dict[str, Any], luot: Any,
                           log: Callable[[str], None]) -> None:
    """Lượt trả về bình thường nhưng có khâu HỎNG vì hết tiền → coi như `_tam_dung_vi_het_tien`."""
    try:
        for ma in list(luot.khau_dang_hong):
            loi = str(luot.tt(ma).loi or "")
            if loi and su_co.phan_loai(RuntimeError(loi)) == su_co.HET_TIEN:
                _tam_dung_vi_het_tien(goc, run, loi, log)
                return
    except Exception:  # noqa: BLE001 — chỉ là dấu phụ, không được làm hỏng lượt
        return


def _kiem_ngan_sach(han_vnd: int, uoc_vnd: int, da_chi_truoc_do_vnd: int) -> Tuple[bool, str]:
    if han_vnd <= 0:
        return False, ("kênh chưa khai `ngan_sach_ngay` trong kenh.yaml — chạy không người trông mà "
                       "không có trần chi tiêu là tiêu tiền không giới hạn. Dừng, không sản xuất.")
    tong = uoc_vnd + da_chi_truoc_do_vnd
    if tong > han_vnd:
        return False, ("ước video này {0}, cộng đã tiêu hôm nay {1} = {2}, vượt trần ngày {3} "
                       "(ngan_sach_ngay trong kenh.yaml). Dừng, không sản xuất — chờ mai, hoặc "
                       "nâng trần.").format(_vnd(uoc_vnd), _vnd(da_chi_truoc_do_vnd), _vnd(tong),
                                            _vnd(han_vnd))
    return True, ""


def _ghep_ngay_gio(ngay: _dt.date, gio: str) -> Optional[_dt.datetime]:
    """`(ngày, "HH:MM")` → một mốc `datetime`. `gio` gõ sai dạng thì `None` —
    không so được với "bây giờ" thì không chặn, để nơi gọi cứ nhận khe đó
    (đúng cách xử lý cũ, trước khi có luật 60 phút)."""
    try:
        gio_ct = _dt.datetime.strptime((gio or "").strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return None
    return _dt.datetime.combine(ngay, gio_ct)


def _moc_ban_giao_goi(ma_goi: str, thu_muc_done: str,
                      ngay_str: str, gio_str: str) -> Optional[_dt.datetime]:
    """Mốc để tính "đã chờ đăng bao lâu" cho MỘT gói (việc B, 28/09/2026).

    Ưu tiên "Ngày đăng"/"Giờ đăng" đã ghi trong kế hoạch — với `tu_duyet: true`
    đây là giờ tool tự xếp lúc bàn giao (`_tim_gio_trong`); với `tu_duyet: false`
    cột này thường ĐỂ TRỐNG (chờ chủ dự án tự duyệt trong bảng, xem
    `_chay_mot_ngay_trong_khoa` mục 5 "Bàn giao"). Trống thì lùi về giờ SỬA ĐỔI
    của thư mục gói trong `thu_muc_done` — đúng lúc `ban_giao_dang.xuat_goi`
    chép mp4/srt/ảnh vào đó, tức LÚC BÀN GIAO thật. Không có cả hai thì trả
    `None` — không đoán bừa một mốc không có thật; nơi gọi coi gói đó là CHƯA
    ĐỦ DỮ LIỆU để tính hạn, tiếp tục chặn như trước bản vá B (an toàn hơn tự ý
    mở nguồn mới dựa trên một mốc bịa)."""
    if ngay_str:
        try:
            ngay = _dt.datetime.strptime(ngay_str, "%d/%m/%Y").date()
        except ValueError:
            ngay = None
        if ngay is not None:
            moc = _ghep_ngay_gio(ngay, gio_str)
            return moc if moc is not None else _dt.datetime.combine(ngay, _dt.time(0, 0))
    thu_muc_done = (thu_muc_done or "").strip()
    if thu_muc_done and ma_goi:
        try:
            return _dt.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(thu_muc_done, ma_goi)))
        except OSError:
            return None
    return None


def _cua_so_san_xuat(goc: str, ma_kenh: str, kenh: Any,
                     *, bay_gio: Optional[_dt.datetime] = None
                     ) -> Tuple[bool, str, Dict[str, Any]]:
    """Cho mở nguồn mới chỉ khi gần lịch đăng và không còn video chờ."""
    luc = bay_gio or _dt.datetime.now()
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    can = {ten: cot.index(ten) for ten in
           ("Ngày đăng", "Giờ đăng", "Sẵn sàng", "Trạng thái đăng")
           if ten in cot}
    dang_cho: List[str] = []
    dang_cho_ngay: List[_dt.date] = []
    qua_han_cho: List[str] = []
    da_dang: List[_dt.datetime] = []
    # ═══ VIỆC B (chẩn đoán 28/09/2026): KHÔNG BAO GIỜ ĐỨNG IM VÌ GÓI BỊ QUÊN ═══
    #
    # Việc A (`tu_nhan_da_dang`) bắt được đa số ca chủ kênh đăng tay, nhưng
    # không phải MỌI video Studio đều lộ ra ngay (extension chỉ chụp phần TỚI
    # HẠN, xem `vm/agent.py`) — vẫn cần một lưới an toàn CUỐI: gói "Sẵn sàng"
    # mà chờ quá `cho_dang_toi_da_ngay` ngày (mặc định 3) thì THÔI CHẶN, để
    # kênh không đứng im vô hạn chỉ vì một gói bị bỏ quên. KHÔNG xoá gì, KHÔNG
    # đổi trạng thái dòng — video vẫn nằm nguyên trong `thu_muc_done`, và việc A
    # vẫn nhận ra + đánh dấu đúng khi chủ kênh đăng muộn hơn cả mốc này.
    cho_toi_da_ngay = max(0, int(getattr(kenh, "cho_dang_toi_da_ngay", 3) or 0))
    thu_muc_done = str(getattr(kenh, "thu_muc_done", "") or "")
    for dong in hang:
        def o(ten: str) -> str:
            i = can.get(ten, -1)
            return str(dong[i]).strip() if 0 <= i < len(dong) else ""

        trang_thai = o("Trạng thái đăng")
        if "ĐÃ ĐĂNG" in trang_thai.upper():
            try:
                ngay = _dt.datetime.strptime(o("Ngày đăng"), "%d/%m/%Y").date()
                moc = _ghep_ngay_gio(ngay, o("Giờ đăng"))
                if moc is not None:
                    da_dang.append(moc)
            except ValueError:
                pass
        elif o("Sẵn sàng"):
            ma_dong = str(dong[cot.index("Mã gói")]).strip() if "Mã gói" in cot else ""
            if cho_toi_da_ngay > 0:
                moc_bg = _moc_ban_giao_goi(ma_dong, thu_muc_done, o("Ngày đăng"), o("Giờ đăng"))
                if moc_bg is not None and (luc - moc_bg).days >= cho_toi_da_ngay:
                    qua_han_cho.append(ma_dong)
                    continue  # THÔI CHẶN — xem chú thích khối trên
            dang_cho.append(ma_dong)
            try:
                dang_cho_ngay.append(
                    _dt.datetime.strptime(o("Ngày đăng"), "%d/%m/%Y").date())
            except ValueError:
                pass

    thong_tin: Dict[str, Any] = {"so_video_dang_cho": len(dang_cho),
                                 "video_dang_cho": dang_cho}
    if qua_han_cho:
        thong_tin["qua_han_cho_dang"] = qua_han_cho

    # ═══ KHO ĐỆM (29/09/2026, full công suất — `core/xep_lich.py`) ═══
    # Kênh khai `nhip_dang` + `tu_duyet: true`: gói chờ đăng KHÔNG còn chặn cứng.
    # Sản xuất tiếp khi (khe tương lai đã có video + gói QA đạt chưa có lịch)
    # < kho_dem_ngay × số khe/ngày. Gói chờ quá hạn (van B) không tính vào kho.
    if xep_lich.che_do_nhieu_khe(kenh):
        kho = xep_lich.dem_kho_dem(goc, ma_kenh, kenh, bay_gio=luc, bo_qua=qua_han_cho)
        thong_tin.update({"che_do": "kho_dem", "kho_dem": kho["kho"], "kho_dem_can": kho["can"],
                          "so_khe_ngay": kho["so_khe_ngay"],
                          "khe_tuong_lai": kho["khe_tuong_lai"], "goi_cho_lich": kho["goi_cho"]})
        if kho["kho"] < kho["can"]:
            return True, "", thong_tin
        if kho["moc_tuong_lai_som_nhat"]:
            thong_tin["mo_cua_san_xuat"] = kho["moc_tuong_lai_som_nhat"]
        return False, ("kho đệm đã đủ {0}/{1} video ({2} ngày × {3} khe) — sản xuất tiếp khi "
                       "một khe lên sóng{4}.").format(
                           kho["kho"], kho["can"], kho["kho_dem_ngay"], kho["so_khe_ngay"],
                           (" (sớm nhất " + _dt.datetime.fromisoformat(
                               kho["moc_tuong_lai_som_nhat"]).strftime("%d/%m %H:%M") + ")")
                           if kho["moc_tuong_lai_som_nhat"] else ""), thong_tin

    if dang_cho:
        # ═══ V2-tối-giản (chẩn đoán 26/09/2026) ═══
        # Đây KHÔNG phải "không lỗi" — máy đang ĐỨNG IM chờ một người bấm nút,
        # và trước bản vá này nơi gọi vẫn ghi "[OK] ... không lỗi" cho đúng ca
        # này (`finalize()` mặc định `ok=True`). Đánh dấu `cho_nguoi=True` để
        # log/báo cáo ngày/mã thoát CLI phân biệt được "máy rảnh, chờ người"
        # với "máy chạy trơn tru, không có gì phải làm".
        thong_tin["cho_nguoi"] = True
        tu_ngay = min(dang_cho_ngay).strftime("%d/%m") if dang_cho_ngay else "trước đó"
        return False, ("còn {0} video chờ đăng từ {1} — đăng rồi bấm “Đã đăng thủ công” "
                       "thì máy sản xuất tiếp.").format(len(dang_cho), tu_ngay), thong_tin

    truoc_gio = max(0, int(getattr(kenh, "san_xuat_truoc_gio", 0) or 0))
    if truoc_gio <= 0 or not da_dang:
        return True, "", thong_tin

    chu_ky = max(1, int(getattr(kenh, "chu_ky_dang_ngay", 1) or 1))
    ngay_ke = max(da_dang).date() + _dt.timedelta(days=chu_ky)
    moc_dang = _ghep_ngay_gio(ngay_ke, str(getattr(kenh, "gio_dang", "") or ""))
    if moc_dang is None:
        moc_dang = _dt.datetime.combine(ngay_ke, _dt.time(20, 0))
    mo_cua = moc_dang - _dt.timedelta(hours=truoc_gio)
    thong_tin.update({"lan_dang_ke": moc_dang.isoformat(timespec="minutes"),
                      "mo_cua_san_xuat": mo_cua.isoformat(timespec="minutes")})
    if luc < mo_cua:
        return False, ("chưa đến lúc chốt nội dung mới; lần đăng kế tiếp là {0}, "
                       "tool sẽ nghiên cứu và chọn nguồn từ {1}.").format(
                           moc_dang.strftime("%d/%m %H:%M"),
                           mo_cua.strftime("%d/%m %H:%M")), thong_tin
    return True, "", thong_tin


def _tim_gio_trong(goc: str, ma_kenh: str, gio_dang: str, tu_ngay: _dt.date,
                   *, toi_da_ngay: int = 60,
                   bay_gio: Optional[_dt.datetime] = None) -> Tuple[str, str]:
    """Ngày gần nhất (từ `tu_ngay` trở đi) chưa có dòng nào trong kế hoạch đăng
    ở đúng giờ `gio_dang`, và mốc đó KHÔNG SỚM HƠN "bây giờ + 60 phút".

    ═══ VÌ SAO KHÔNG CHỈ NHÌN `tu_ngay` ═══

    `tu_ngay` là NGÀY LÚC BẮT ĐẦU chu kỳ (`hom_nay`/hôm nay), không phải lúc
    bàn giao xong. Một video tốn 2–4 tiếng sản xuất (`core/auto.py`, 8 khâu),
    và `tu_chay.py --tat-ca` chạy các kênh LẦN LƯỢT — kênh chạy tới lượt buổi
    chiều/tối có thể bàn giao xong SAU cả giờ đăng hôm nay của chính nó. Chốt
    thẳng "hôm nay, giờ X" mà giờ X đã trôi qua là đặt lịch đăng vào QUÁ KHỨ:
    máy ảo (`vm/may_dang.py`) tới giờ không thấy gì để đăng, và không ai biết
    cho tới hôm sau soi lại kế hoạch.

    Nên khe được chọn phải cách "bây giờ" (mặc định `datetime.now()`, seam
    `bay_gio` cho bài kiểm) ít nhất 60 phút — vừa đủ để máy ảo kịp chuẩn bị
    trước khi tới giờ đăng. Không tìm được trong `toi_da_ngay` ngày thì để
    trống — an toàn hơn đặt bừa một ngày xa.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    som_nhat = bay_gio + _dt.timedelta(minutes=60)

    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    co_cot = "Ngày đăng" in cot and "Giờ đăng" in cot
    da_dat: set = set()
    if co_cot:
        i_ngay, i_gio = cot.index("Ngày đăng"), cot.index("Giờ đăng")
        da_dat = {(str(d[i_ngay]).strip() if i_ngay < len(d) else "",
                  str(d[i_gio]).strip() if i_gio < len(d) else "") for d in hang}

    ngay = tu_ngay
    for _i in range(max(1, toi_da_ngay)):
        moc = _ghep_ngay_gio(ngay, gio_dang)
        if moc is not None and moc < som_nhat:
            ngay = ngay + _dt.timedelta(days=1)
            continue
        chuoi = ngay.strftime("%d/%m/%Y")
        if not co_cot or (chuoi, gio_dang) not in da_dat:
            return chuoi, gio_dang
        ngay = ngay + _dt.timedelta(days=1)
    return "", ""


def _dung_goi_chat_mac_dinh(client, log: Callable[[str], None],
                            cancel: Optional[threading.Event]):
    """Hàm gọi AI viết chữ qua ví ShopAPI — cùng luật với
    `ui_qt/trang_auto.py _dung_goi_chat` (khoá cố định theo bước, đợi lâu)."""

    def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5", khoa: str = "",
            toi_da_token: int = 8192, anh: str | List[str] = "") -> str:
        from .goi_van_ban import goi_van_ban, khoi_anh, tin_nhan_viet  # noqa: PLC0415

        def kiem_dung() -> None:
            if cancel is not None and cancel.is_set():
                raise RuntimeError("đã dừng")

        # Việc 4 (28/09/2026, `core/chon_bia.py`): `anh` giờ nhận cả DANH SÁCH
        # nhiều ảnh (giám khảo cần nhìn tấm ghép + ảnh thắng + vài ảnh đã đăng
        # cùng lúc) — một chuỗi vẫn đi đúng đường cũ (một khối ảnh), khác chuỗi
        # là một khối text rồi NỐI THÊM từng ảnh theo đúng thứ tự đưa vào.
        cac_anh = ([anh] if anh else []) if isinstance(anh, str) else [a for a in (anh or []) if a]
        noi_dung: Any = ([{"type": "text", "text": loi_nhac}]
                         + [khoi_anh(a) for a in cac_anh]) if cac_anh else loi_nhac
        return goi_van_ban(client, tin_nhan_viet(noi_dung), mo_hinh=mo_hinh,
                           toi_da_token=int(toi_da_token), khoa=khoa, on_log=log,
                           kiem_dung=kiem_dung)

    return goi


def _dong_keo_nhau(ma_kenh: str, run: Optional[Dict[str, Any]]) -> str:
    """Một câu (hoặc rỗng) cho SỔ NGÀY: nguồn đã chọn có được cộng điểm "cụm đang thắng ở
    kênh anh em" không, từ kênh nào, cụm nào.

    Chủ dự án đọc `workspace/tu-chay/<ngày>.md` mỗi sáng. Trước dòng này, việc bốn kênh có
    KÉO NHAU thật hay không hoàn toàn vô hình: `cong_diem_anh_em` chỉ ghi vào nhật ký lượt
    (`tu-chay.log`, ai đọc cũng phải lội cả trăm dòng) và vào `nguon["ly_do"]` trong sổ
    JSON của từng kênh. Sổ ngày là chỗ duy nhất một người xem được cả bốn kênh cùng lúc —
    và đúng chỗ ấy phải trả lời được câu "tín hiệu nhóm có đang làm gì không".

    Kênh KHÔNG thuộc nhóm nào (hay nhóm chưa có bảng) thì trả RỖNG — không thêm dòng nào,
    sổ không phình ra vì một câu "không có gì".
    """
    nguon = (run or {}).get("nguon") or {}
    ae = nguon.get("anh_em") or {}
    if not ae:
        return ""
    return ("{0}: +{1:g} điểm anh em — cụm “{2}” đang thắng ở kênh {3} ({4:.0f}% video của cụm "
            "đó trên kênh ấy thắng), và “{5}” vẫn thuộc tệp của kênh này.".format(
                ma_kenh, nguon.get("diem_anh_em") or 0, ae.get("ten_cum") or ae.get("cum") or "?",
                ae.get("kenh") or "?", float(ae.get("chi_so") or 0) * 100,
                str(nguon.get("tieu_de") or nguon.get("ma") or "?")[:50]))


def _tom_tat_dong(ma_kenh: str, run: Optional[Dict[str, Any]], che_do: str) -> str:
    if run is None:
        return "{0}: không có lượt nào hôm nay.".format(ma_kenh)
    nguon = run.get("nguon") or {}
    sx = run.get("san_xuat") or {}
    bg = run.get("ban_giao") or {}
    tieu_de = str(nguon.get("tieu_de") or "")[:50]
    if che_do == "thu":
        return "{0}: [THỬ] chọn “{1}” ({2}) — lượt {3}, chưa sản xuất.".format(
            ma_kenh, tieu_de, nguon.get("nguon", ""), run.get("ma_luot", ""))
    if not sx.get("da_chay") and not sx.get("xong_het"):
        ns = run.get("ngan_sach") or {}
        return "{0}: {1}".format(ma_kenh, ns.get("ly_do") or "chưa sản xuất.")
    if sx.get("xong_het"):
        if bg.get("da_ban_giao"):
            phan_bg = "đã bàn giao gói {0}".format(bg.get("ma_goi"))
            if bg.get("ngay_dang"):
                phan_bg += " — đặt lịch {0} {1}".format(bg.get("ngay_dang"), bg.get("gio_dang"))
            else:
                phan_bg += " — {0}".format(bg.get("ly_do_trong") or "chờ tự duyệt")
        else:
            phan_bg = "CHƯA bàn giao ({0})".format(bg.get("ly_do_trong") or bg.get("loi") or "?")
        return "{0}: xong video lượt {1} (“{2}”), {3}.".format(
            ma_kenh, run.get("ma_luot", ""), tieu_de, phan_bg)
    return "{0}: lượt {1} chưa xong hết ({2}).".format(
        ma_kenh, run.get("ma_luot", ""), ", ".join(sx.get("khau_hong") or []) or "đang chạy")


# ── Nhận diện lỗi ĐĨA ĐẦY (khác lỗi sản xuất bình thường) ────────────────────


def _tim_loi_dia_day(loi: BaseException, *, do_sau: int = 4) -> Optional[OSError]:
    """Dò `loi` và tối đa `do_sau` lớp lồng nhau (`__cause__`/`__context__`)
    tìm một `OSError` mang mã ĐĨA ĐẦY — POSIX `errno.ENOSPC`, hoặc Windows
    `WinError 112` ("There is not enough space on the disk"). Trả `None` nếu
    không lớp nào khớp.

    Sản xuất đi qua nhiều mô-đun con (`ffmpeg_goi_san`, `download`,
    `anh_len`…) có thể bọc `OSError` gốc trong một lỗi khác khi báo lên
    (`raise RuntimeError(...) from loi`) — dò lồng vài lớp để không bỏ sót,
    nhưng chặn ở `do_sau` để không vòng vô hạn nếu lỗi tự tham chiếu."""
    hien: Optional[BaseException] = loi
    thay: set = set()
    for _ in range(max(1, do_sau)):
        if hien is None or id(hien) in thay:
            break
        thay.add(id(hien))
        if isinstance(hien, OSError) and (
                getattr(hien, "errno", None) == errno.ENOSPC
                or getattr(hien, "winerror", None) == 112):
            return hien
        hien = hien.__cause__ or hien.__context__
    return None


def _don_khan_ngay(goc: str, can_gb: float, log: Callable[[str], None],
                   *, don_khan_fn: Optional[Callable[..., Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Gọi dọn khẩn (`core.don_dep.don_khan`) NGAY khi đĩa chạm/dưới ngưỡng an
    toàn, hoặc vừa dính đĩa đầy giữa chừng sản xuất — chỉ đụng video ĐÃ ĐĂNG
    của kênh đã tự bật `tu_don` (dọn khẩn không lật lại lựa chọn `tu_don:
    false` của chủ dự án, xem docstring `don_khan`).

    Một lỗi ở đây (đĩa bận, kế hoạch hỏng…) chỉ được ghi log rồi bỏ qua —
    không được ném tiếp, vì đây đã là NHÁNH XỬ LÝ một sự cố đĩa, ném thêm lỗi
    ở đây sẽ nuốt mất dấu vết lỗi gốc đang được xử lý."""
    fn = don_khan_fn or don_dep.don_khan
    try:
        danh_sach = liet_ke_kenh(goc)
        ket = fn(goc, danh_sach, nguong_gb=can_gb)
    except Exception as loi:  # noqa: BLE001
        log("  dọn khẩn hỏng: {0} — bỏ qua.".format(str(loi)[:200]))
        return {"da_chay": False, "loi": str(loi)[:200]}
    if ket.get("da_chay"):
        con_truoc = ket.get("con_truoc_gb")
        con_sau = ket.get("con_sau_gb")
        log("  dọn khẩn: giải phóng {0} — đĩa {1} → {2}.".format(
            _byte_nguoi_doc(ket.get("da_giai_phong_bytes") or 0),
            "{0:.1f} GB".format(con_truoc) if con_truoc is not None else "?",
            "{0:.1f} GB".format(con_sau) if con_sau is not None else "?"))
        if ket.get("bo_qua_khong_tu_don"):
            log("  (bỏ qua {0} kênh chưa bật `tu_don` trong lượt dọn khẩn này — không lật lại "
               "lựa chọn của chủ dự án).".format(len(ket["bo_qua_khong_tu_don"])))
    else:
        log("  dọn khẩn: {0}".format(ket.get("ly_do") or "không có gì để dọn."))
    return ket


def _log_nhuong_im(log: Callable[[str], None]) -> Callable[[str], None]:
    """Bọc `log` nuốt dòng "[NHƯỜNG] … treo/chết" (đã in ở lần hỏi trước nghiên cứu)."""
    def _ghi(dong: str) -> None:
        if str(dong).lstrip().startswith("[NHƯỜNG] phiên kênh"):
            return
        log(dong)
    return _ghi


def _kiem_nhuong_phien(goc: str, ma_kenh: str, bay_gio: Optional[_dt.datetime],
                       log: Callable[[str], None]) -> str:
    """Cửa nhường phiên kênh (chẩn đoán 28/09/2026). Trả câu tóm tắt khi PHẢI
    nhường (lượt này dừng, 0 đồng), chuỗi rỗng khi được sản xuất tiếp."""
    try:
        can_cho_phien, qua_tran_phien = nhuong_phien_kenh.kenh_phien_can_nhuong(
            goc, bay_gio=bay_gio)
    except Exception as loi:  # noqa: BLE001 — đọc vm/ hỏng không được chặn sản xuất
        can_cho_phien, qua_tran_phien = [], []
        log("  (không đọc được trạng thái phiên kênh vm/: {0}) — bỏ qua, sản xuất tiếp tục."
           .format(str(loi)[:150]))
    for kenh_qua_tran in qua_tran_phien:
        log("  [NHƯỜNG] phiên kênh {0} đến hạn quá {1:.0f} giờ vẫn chưa chạy — agent có thể "
           "đã treo/chết, sản xuất tiếp tục bình thường (thôi không chờ nữa)."
           .format(kenh_qua_tran, nhuong_phien_kenh.TRAN_GIO_CHO_PHIEN_MAC_DINH))
    if can_cho_phien:
        log("[NHƯỜNG] còn phiên kênh {0} chưa chạy hôm nay (quét Studio/đăng) — sản xuất đợi "
           "lượt sau.".format(", ".join(can_cho_phien)))
        return "{0}: nhường phiên kênh {1} — đợi lượt sau.".format(
            ma_kenh, ", ".join(can_cho_phien))
    return ""


def chay_mot_ngay(
    goc: str, ma_kenh: str, *,
    client: Any = None,
    hom_nay: Optional[_dt.date] = None,
    che_do: str = "that",
    on_log: Optional[Callable[[str], None]] = None,
    cancel: Optional[threading.Event] = None,
    #: "Bây giờ" — dùng để tính khe đăng ĐỦ XA (`_tim_gio_trong`, xem đó).
    #: Mặc định `datetime.now()`; seam để bài kiểm đặt cố định.
    bay_gio: Optional[_dt.datetime] = None,
    # ── seam cho từng bước, để bài kiểm không mạng không tốn ví ─────────────
    chay_mot_nut: Optional[Callable[..., Any]] = None,
    cham_v7: Optional[Callable[..., Any]] = None,
    doc_danh_sach: Optional[Callable[..., Any]] = None,
    video_da_lam_nhom: Optional[Callable[[str, str], Any]] = None,
    #: (LỖI 2, 28/09/2026) seam cho `nhom_kenh.tieu_de_da_lam_ca_nhom` — cùng
    #: nếp `video_da_lam_nhom` ngay trên, để bài kiểm không cần thư mục nhóm
    #: thật trên đĩa.
    tieu_de_da_lam_nhom: Optional[Callable[[str, str], Any]] = None,
    goi_chat: Optional[Callable[..., str]] = None,
    dung_viec: Optional[Callable[[Any], Dict[str, Callable]]] = None,
    chay_auto: Optional[Callable[..., Any]] = None,
    ban_giao: Optional[Callable[..., Tuple[str, bool]]] = None,
    khoa_pid_con_song: Optional[Callable[[int], bool]] = None,
    gia: PriceTable = DEFAULT_PRICES,
) -> Dict[str, Any]:
    """Một chu kỳ ngày cho MỘT kênh. Trả về báo cáo (`dict`), cũng là thứ vừa
    ghi vào `CHANNEL/<kênh>/tu-chay/<ngày>.json`.

    `che_do="thu"` chỉ nghiên cứu + chọn nguồn, KHÔNG BAO GIỜ gọi sản xuất, và
    KHÔNG đưa `client` vào bước nghiên cứu — xem tool sẽ chọn video nào mà
    không tốn một đồng nào, kể cả tiền AI phân loại trang chủ.
    `che_do="that"` mới thật sự sản xuất, và chỉ khi kênh đủ điều kiện + van
    ngân sách cho qua.
    """
    if che_do not in ("that", "thu"):
        raise ValueError("che_do phải là 'that' hoặc 'thu', nhận '{0}'".format(che_do))

    ngay = hom_nay or _dt.date.today()
    ngay_str = ngay.isoformat()

    ok_khoa, ly_do_khoa = _giu_khoa(goc, ma_kenh, con_song=khoa_pid_con_song or _pid_con_song)
    if not ok_khoa:
        return {"kenh": ma_kenh, "ngay": ngay_str, "che_do": che_do, "ok": False,
               "buoc_loi": "khoa", "loi": ly_do_khoa, "run": None,
               "tom_tat": "{0}: {1}".format(ma_kenh, ly_do_khoa), "nhat_ky": [ly_do_khoa]}

    try:
        return _chay_mot_ngay_trong_khoa(
            goc, ma_kenh, ngay=ngay, ngay_str=ngay_str, client=client, che_do=che_do,
            on_log=on_log, cancel=cancel, bay_gio=bay_gio, chay_mot_nut=chay_mot_nut,
            cham_v7=cham_v7, doc_danh_sach=doc_danh_sach, video_da_lam_nhom=video_da_lam_nhom,
            tieu_de_da_lam_nhom=tieu_de_da_lam_nhom,
            goi_chat=goi_chat, dung_viec=dung_viec, chay_auto=chay_auto, ban_giao=ban_giao,
            gia=gia)
    finally:
        _nha_khoa(goc, ma_kenh)


def _chay_mot_ngay_trong_khoa(
    goc: str, ma_kenh: str, *, ngay: _dt.date, ngay_str: str, client: Any, che_do: str,
    on_log: Optional[Callable[[str], None]], cancel: Optional[threading.Event],
    bay_gio: Optional[_dt.datetime],
    chay_mot_nut: Optional[Callable[..., Any]], cham_v7: Optional[Callable[..., Any]],
    doc_danh_sach: Optional[Callable[..., Any]],
    video_da_lam_nhom: Optional[Callable[[str, str], Any]],
    tieu_de_da_lam_nhom: Optional[Callable[[str, str], Any]],
    goi_chat: Optional[Callable[..., str]], dung_viec: Optional[Callable[[Any], Dict[str, Callable]]],
    chay_auto: Optional[Callable[..., Any]], ban_giao: Optional[Callable[..., Tuple[str, bool]]],
    gia: PriceTable,
) -> Dict[str, Any]:
    """Thân việc thật của :func:`chay_mot_ngay`, chạy TRONG khoá độc quyền của
    kênh (tách riêng để `chay_mot_ngay` giữ khoá gọn trong một `try/finally`)."""

    chay_mot_nut_fn = chay_mot_nut or mot_nut.chay
    cham_v7_fn = cham_v7 or v7.cham
    doc_danh_sach_fn = doc_danh_sach or mot_nut.doc_danh_sach
    ban_giao_fn = ban_giao or ban_giao_dang.ban_giao

    nhat_ky: List[str] = []

    def log(dong: str) -> None:
        nhat_ky.append(str(dong))
        if on_log is not None:
            on_log(dong)

    bao_cao = _doc_bao_cao_ngay(goc, ma_kenh, ngay_str)
    # Lượt được nhặt lại từ MỘT NGÀY TRƯỚC sống ở sổ của ngày đó — sổ hôm nay
    # chỉ giữ một dòng THAM CHIẾU (đếm vào video_moi_ngay). Mặc định cả hai
    # trỏ vào cùng sổ hôm nay; đổi khi thật sự nhặt từ ngày khác.
    bao_cao_goc = bao_cao
    ngay_goc_str = ngay_str
    run_hien_tai: Optional[Dict[str, Any]] = None

    def finalize(*, ok: bool = True, buoc_loi: str = "", loi: str = "",
                tom_tat: str = "", cho_nguoi: bool = False) -> Dict[str, Any]:
        bao_cao["nhat_ky"] = list(bao_cao.get("nhat_ky") or []) + nhat_ky
        _ghi_bao_cao_ngay(goc, ma_kenh, ngay_str, bao_cao)
        if bao_cao_goc is not bao_cao:
            _ghi_bao_cao_ngay(goc, ma_kenh, ngay_goc_str, bao_cao_goc)
        return {"kenh": ma_kenh, "ngay": ngay_str, "che_do": che_do, "ok": ok,
               "buoc_loi": buoc_loi, "loi": loi, "run": run_hien_tai,
               # V2-tối-giản: máy ĐANG ĐỨNG IM CHỜ MỘT NGƯỜI (còn gói chờ đăng)
               # — khác "ok" (không có gì phải làm) lẫn "lỗi" (máy hỏng). Nơi in
               # log/báo cáo/mã thoát (root `tu_chay.py`, `_dung_md_tat_ca`) đọc
               # cờ này để không còn lỡ ghi "[OK] ... không lỗi" cho ca này.
               "cho_nguoi": cho_nguoi,
               "tom_tat": tom_tat or _tom_tat_dong(ma_kenh, run_hien_tai, che_do),
               # Một câu cho SỔ NGÀY: nguồn hôm nay có được "kéo nhau" trong nhóm không.
               # Chủ dự án đọc `workspace/tu-chay/<ngày>.md` mỗi sáng và đây là chỗ DUY
               # NHẤT nói được chuyện đó — xem `_dong_keo_nhau`.
               "keo_nhau": _dong_keo_nhau(ma_kenh, run_hien_tai),
               "nhat_ky": nhat_ky}

    if not os.path.isfile(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)):
        return finalize(ok=False, buoc_loi="doc_kenh", loi="không thấy kênh " + ma_kenh,
                        tom_tat="{0}: không thấy kênh (thiếu {1}).".format(ma_kenh, TEP_KENH))
    try:
        kenh = doc_kenh(goc, ma_kenh)
    except Exception as loi:  # noqa: BLE001
        return finalize(ok=False, buoc_loi="doc_kenh", loi=str(loi),
                        tom_tat="{0}: không đọc được kênh — {1}".format(ma_kenh, loi))

    # ═══ VIỆC A (chẩn đoán 28/09/2026): TỰ NHẬN VIDEO ĐÃ ĐĂNG ═══
    #
    # Chủ kênh đăng TAY trên YouTube (Studio, hẹn giờ của chính YouTube…) chứ
    # không qua tool, và không biết/không muốn bấm "Đã đăng thủ công" — kênh sẽ
    # đứng im vô hạn chờ một thao tác không bao giờ tới (xem cửa `_cua_so_san_xuat`
    # ngay dưới). Đối chiếu tiêu đề video THẬT trên kênh (Studio,
    # `CHANNEL/<kênh>/chi-so/kenh/`) với các dòng kế hoạch đang chờ — khớp chắc
    # chắn (một-đối-một, xem `core.tu_nhan_da_dang`) thì tự đánh dấu ĐÃ ĐĂNG,
    # ĐÚNG NHƯ chủ kênh tự bấm. Đặt ở ĐẦU lượt, TRƯỚC cả `_tim_run_chua_xong`
    # lẫn `_cua_so_san_xuat`: thuần đọc đĩa, 0 đồng, không phụ thuộc lượt dở
    # hay cửa nhịp đăng — một lỗi ở đây (kế hoạch hỏng, chưa có lượt quét nào…)
    # không được chặn cả chu kỳ, chỉ ghi log rồi bỏ qua.
    try:
        tu_nhan_da_dang.tu_nhan_video_da_dang(goc, ma_kenh, bay_gio=bay_gio, on_log=log)
    except Exception as loi:  # noqa: BLE001 — tự nhận hỏng không được chặn cả lượt chạy
        log("  (tự nhận video đã đăng hỏng: {0}) — bỏ qua, không chặn lượt chạy."
           .format(str(loi)[:200]))

    # ═══ XẾP LẠI GÓI LỠ LỊCH (29/09/2026, `core/xep_lich.py`) ═══
    # Chỉ kênh khai `nhip_dang`: gói QA đạt chưa tải mà lịch đã trôi qua → dời
    # sang khe trống sớm nhất (≥ bây giờ + bien_xu_ly_gio), không nằm chết trong DONE.
    if xep_lich.che_do_nhieu_khe(kenh):
        try:
            for ma_goi_doi, cu, moi in xep_lich.xep_lai_goi_lo_lich(
                    goc, ma_kenh, kenh, bay_gio=bay_gio):
                log("[XẾP LẠI LỊCH] {0}: lỡ lịch {1} (chưa tải lên) — dời sang {2}."
                   .format(ma_goi_doi, cu, moi))
        except Exception as loi:  # noqa: BLE001 — xếp lại hỏng không được chặn lượt
            log("  (xếp lại lịch hỏng: {0}) — bỏ qua.".format(_ta_loi_day_du(loi)[:200]))

    # ═══ BƯỚC 0 (Việc 3, 28/09/2026): HỌC TỪ SỐ LIỆU ═══
    #
    # `core.vong_hoc.truoc_luot` — chuẩn hoá kho nhạc, bù/cập nhật hồ sơ video +
    # nối số liệu Studio thật, rút bài học sản xuất (debounce). Chạy TRƯỚC "1)
    # Nghiên cứu", NGAY SAU Việc A ở trên: cùng nếp — thuần đọc/ghi đĩa, 0 đồng,
    # không phụ thuộc lượt dở hay cửa nhịp đăng, và tự bọc try/except NGAY BÊN
    # TRONG (`vong_hoc.py`, mỗi bước một try/except riêng) nên một bước hỏng
    # (ffmpeg thiếu, chưa quét Studio lần nào…) không kéo sập cả bốn bước còn
    # lại. Cờ `kenh.yaml: vong_hoc` (mặc định BẬT) tắt được cho từng kênh.
    # Điều phối BẬT (29/09/2026): vòng học chạy chuẩn hoá kho nhạc bằng FFmpeg —
    # lớp "nang". Thử giữ khe MỘT LẦN; khe đang bận (kênh khác đang dựng/tải lên)
    # thì bỏ qua lượt này — vòng học có debounce, lượt sau làm bù.
    if getattr(kenh, "vong_hoc", True):
        with dieu_phoi.thu_nang(goc, "nen", kenh=ma_kenh) as _duoc_vong_hoc:
            if not _duoc_vong_hoc:
                log("  0) [vòng học] khe máy nặng đang bận — để lượt sau.")
            else:
                try:
                    # Việc 4 (28/09/2026): bước 4 của vòng học (`core.khuon_bia.cap_nhat`)
                    # cần MỘT lượt AI nhìn ảnh khi người thắng vừa đổi — truyền hàm gọi
                    # chat THẬT thay vì `None` như trước Việc 4. `_dung_goi_chat_mac_dinh`
                    # chỉ DỰNG một closure ở đây, chưa gọi mạng; `vong_hoc`/`khuon_bia` tự
                    # `try/except` khi thật sự gọi, nên `client=None` (chế độ không cần
                    # ví) vẫn an toàn — lỗi chỉ rơi vào đúng bước 4, không chặn lượt.
                    vong_hoc.truoc_luot(
                        goc, ma_kenh, _dung_goi_chat_mac_dinh(client, log, cancel),
                        log, bay_gio=bay_gio)
                except Exception as loi:  # noqa: BLE001 — vòng học hỏng không được chặn cả lượt chạy
                    log("  (vòng học hỏng: {0}) — bỏ qua, không chặn lượt chạy."
                       .format(str(loi)[:200]))

    # Lượt dở luôn đi trước nghiên cứu và cửa nhịp đăng: lần chạy sau tiếp tục
    # đúng nguồn cũ, không chất thêm video và không trả tiền lần hai.
    tim_som = _tim_run_chua_xong(
        goc, ma_kenh, ngay, so_ngay=SO_NGAY_QUET_LUOT_CHUA_XONG)
    # ═══ VÁ 28/09/2026 — nạp lại `bao_cao`, tránh `finalize()` ghi đè mất
    # dòng "nhận con nuôi" vừa ghi ═══
    #
    # `_tim_run_chua_xong` có thể vừa TỰ GHI (L1, `_nhan_nuoi_luot_mo_coi`) một
    # dòng "nhận con nuôi" vào sổ HÔM NAY, trực tiếp trên ĐĨA qua một cặp
    # `_doc_bao_cao_ngay`/`_ghi_bao_cao_ngay` RIÊNG — không đụng gì tới biến
    # `bao_cao` đã nạp ở trên (TRƯỚC lệnh gọi này). Không nạp lại thì `finalize()`
    # ở cuối hàm ghi ĐÈ bản `bao_cao` CŨ (thiếu đúng dòng vừa nhận nuôi) lên
    # đĩa — XOÁ MẤT dòng vừa ghi, lượt mồ côi coi như chưa từng được nhìn thấy.
    #
    # Lỗi THẬT bắt được 27→28/09/2026 trên chính VPS này: `tu-chay.log` in
    # đúng "[TỰ PHỤC HỒI] Có lượt đang dở" (chứng tỏ `_nhan_nuoi_luot_mo_coi` đã
    # chạy) nhưng sổ ngày rốt cuộc KHÔNG có dòng nào, và TL1-T7/0003+0004 vẫn
    # y nguyên trên đĩa sau hai lượt lịch chạy liền (27/09 21:08, 28/09 05:00) —
    # đọc lại log lộ đúng cơ chế này. An toàn tuyệt đối: giữa hai dòng
    # này chưa có gì khác từng đổi `bao_cao`, nên nạp lại là vô hại khi
    # `_tim_run_chua_xong` không ghi gì (đọc lại đúng y nguyên nội dung cũ).
    bao_cao = _doc_bao_cao_ngay(goc, ma_kenh, ngay_str)
    bao_cao_goc = bao_cao

    # ═══ VAN VÍ (30/09/2026, V8/3.3, `core/van_vi.py`) ═══
    # Trước khi mở lượt MỚI (hoặc nhặt lượt dở), hỏi số dư ví (GET /v1/balance,
    # miễn phí, có nhớ đệm). Ví < ước 1 video x 1,5 → KHÔNG mở lượt mới; lượt dở
    # chỉ làm nốt khi ví ≥ ước 1 video. Đặt TRƯỚC nghiên cứu (tốn AI) và TRƯỚC
    # bước nhặt lượt dở (không đếm oan một "lần phục hồi" của trần L3 khi chỉ
    # đang chờ nạp tiền). Không đọc được số dư → không chặn. Ví đủ lại thì lần
    # chạy sau tự đi tiếp, không cần ai bấm.
    if che_do == "that" and client is not None:
        try:
            from . import van_vi  # noqa: PLC0415

            duoc_vi, ly_do_vi, _dg_vi = van_vi.cho_phep_mo_luot(
                goc, client, dang_do=tim_som is not None)
        except Exception as loi_vi:  # noqa: BLE001 — van hỏng không được chặn cả máy
            duoc_vi, ly_do_vi = True, ""
            log("  (van ví không kiểm được: {0}) — bỏ qua.".format(str(loi_vi)[:120]))
        if not duoc_vi:
            log("[VÍ] " + ly_do_vi)
            return finalize(tom_tat="{0}: [VÍ] {1}".format(ma_kenh, ly_do_vi))

    if tim_som is None:
        cho_mo, ly_do_nhip, thong_tin_nhip = _cua_so_san_xuat(
            goc, ma_kenh, kenh, bay_gio=bay_gio)
        bao_cao["nhip_dang"] = thong_tin_nhip
        # Việc B: ghi rõ ra sổ ngày MỌI gói vừa được "thôi chặn" vì chờ quá hạn
        # — chủ dự án đọc sổ sáng hôm sau biết ngay tại sao kênh lại sản xuất
        # tiếp dù còn gói chưa đăng, và biết video đó vẫn nằm nguyên trong DONE.
        for ma_goi_qua_han in thong_tin_nhip.get("qua_han_cho_dang") or []:
            log("[CHỜ QUÁ HẠN] {0} chờ quá {1} ngày — thôi chờ, sản xuất tiếp; "
               "video vẫn nằm trong DONE, đăng lúc nào tool tự nhận."
               .format(ma_goi_qua_han, max(0, int(getattr(kenh, "cho_dang_toi_da_ngay", 3) or 0))))
        if not cho_mo:
            if thong_tin_nhip.get("cho_nguoi"):
                log("[CHỜ NGƯỜI] " + ly_do_nhip)
                return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_nhip), cho_nguoi=True)
            log("[NHỊP ĐĂNG] " + ly_do_nhip)
            return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_nhip))

        # ═══ CỬA RẺ TRƯỚC NGHIÊN CỨU (29/09/2026) ═══
        # Kiểm toán 29/09: 11/30 lượt nghiên cứu (mỗi lượt 20–50 phút, hàng chục
        # lượt gọi AI) bị VỨT vì hai cửa rẻ nằm SAU nghiên cứu — trần video/ngày
        # ("Đã đủ … video hôm nay") và nhường phiên kênh. Không lượt dở thì chắc
        # chắn sẽ mở nguồn mới → hỏi hai cửa này TRƯỚC, thoát sớm, 0 đồng.
        tran_ngay_som = xep_lich.tran_video_ngay(kenh)
        if len(bao_cao["runs"]) >= tran_ngay_som:
            log("Đã đủ {0} video hôm nay cho kênh này — không nghiên cứu, không chọn thêm."
               .format(tran_ngay_som))
            return finalize(tom_tat="{0}: đã đủ {1} video hôm nay, không làm thêm."
                            .format(ma_kenh, tran_ngay_som))
        ket_nhuong_som = _kiem_nhuong_phien(goc, ma_kenh, bay_gio, log)
        if ket_nhuong_som:
            return finalize(tom_tat=ket_nhuong_som)
    else:
        log("[TỰ PHỤC HỒI] Có lượt đang dở — ưu tiên chạy tiếp, bỏ qua cửa mở nguồn mới.")

    # V7 đã có cấu hình TRƯỚC lượt này chưa — kiểm TRƯỚC bước nghiên cứu, vì
    # nghiên cứu (qua cong_thuc_v7._cham_v7 bên trong) tự ghi cấu hình MẶC ĐỊNH
    # ra đĩa nếu thiếu (`nap_cau_hinh(ghi_neu_thieu=True)`), nên kiểm SAU sẽ
    # luôn thấy "có" — mất hẳn ý nghĩa "kênh này đã tự khai Công thức V7".
    # Một hàm, không phải mười dòng tại chỗ: trạm (`/loi-thoai/can-lay`) phải
    # hỏi được ĐÚNG câu này để xếp hạng bằng cùng một bộ — xem `co_cau_hinh_v7`,
    # nơi giữ nguyên văn lý do của từng nhánh.
    co_v7_truoc = co_cau_hinh_v7(goc, ma_kenh)

    # Kênh EM CHƯA có danh bạ đối thủ (`nghien-cuu/doi-thu.csv`) — lượt "một nút" ĐẦU
    # TIÊN của nó phải chấm lại gần hết hộp thư THÔ mang sang từ kênh gốc (`nhom_kenh`
    # gộp mọi link chưa ai chấm), cỡ vài trăm kênh. Có ví ở đúng lượt đầu này là vài
    # trăm lượt gọi AI cho một kênh còn chưa chắc sống được — để dành ví cho lượt sau,
    # khi hộp thư đã mỏng lại. `che_do="thu"` vốn đã không đưa client (xem dưới); đây
    # thêm một điều kiện NỮA riêng cho `che_do="that"`.
    co_danh_ba_truoc = os.path.isfile(db.duong_so(goc, ma_kenh))

    # ═══ NGHIÊN CỨU TẬP TRUNG THEO NHÓM (29/09/2026, `core/nghien_cuu_nhom.py`) ═══
    # Kênh có `nhom`, chế độ thật: còn tươi → bỏ hẳn bước nghiên cứu; cũ → nghiên
    # cứu MỘT lần cho cả nhóm dưới khoá nhóm; khoá bận → dùng dữ liệu < 24h hoặc
    # đợi lượt sau. Kênh không nhóm / chế độ thử → nhánh cũ ngay dưới, y nguyên.
    nhom_nc = ""
    if tim_som is None and che_do == "that":
        try:
            nhom_nc = nghien_cuu_chung.nhom_cua(goc, ma_kenh)
        except Exception:  # noqa: BLE001
            nhom_nc = ""
    if tim_som is None and nhom_nc:
        can_nc, ly_do_nc, tuoi_nc = nghien_cuu_nhom.can_nghien_cuu(goc, ma_kenh)
        if not can_nc:
            log("1) Nghiên cứu: {0} — bỏ qua, chọn nguồn từ dữ liệu sẵn có.".format(ly_do_nc))
        else:
            log("1) Nghiên cứu NHÓM {0} ({1})…".format(nhom_nc, ly_do_nc))
            ket_nc = nghien_cuu_nhom.chay_nhom(
                goc, ma_kenh, client=client, chay_mot_nut=chay_mot_nut_fn, on_log=log,
                cancel=cancel, co_danh_ba=lambda m: os.path.isfile(db.duong_so(goc, m)))
            if ket_nc.get("ban"):
                giu_nc = ket_nc.get("giu") or {}
                if tuoi_nc is not None and tuoi_nc < nghien_cuu_nhom.GIO_DUNG_DU_LIEU_CU:
                    log("  nghiên cứu nhóm đang chạy ở lượt {0} (PID {1}) — dùng dữ liệu {2:.1f} "
                       "giờ trước, không nghiên cứu riêng.".format(
                           giu_nc.get("kenh", "?"), giu_nc.get("pid", "?"), tuoi_nc))
                else:
                    log("[NGHIÊN CỨU NHÓM] lượt {0} đang nghiên cứu cho nhóm, dữ liệu kênh này đã "
                       "cũ — đợi lượt sau.".format(giu_nc.get("kenh", "?")))
                    return finalize(tom_tat="{0}: nghiên cứu nhóm đang chạy ở lượt khác — đợi "
                                            "lượt sau.".format(ma_kenh))
            elif (ket_nc.get("loi") or {}).get(ma_kenh):
                loi_nc = ket_nc["loi"][ma_kenh]
                return finalize(ok=False, buoc_loi="nghien_cuu", loi=loi_nc,
                                tom_tat="{0}: nghiên cứu hỏng — {1}".format(ma_kenh, loi_nc[:200]))
    elif tim_som is None:
        log("1) Nghiên cứu (một nút)…")
        try:
        # "thu" KHÔNG bao giờ đưa client vào nghiên cứu — mot_nut chỉ bật ba
        # chỗ AI (đọc trang chủ lưỡng lự, hỏi đối thủ, gán tuyến) khi client
        # khác None; đưa client vào dù không sản xuất là vẫn tốn tiền AI ở
        # bước này, trái với lời hứa "thu = không tốn một đồng nào".
            client_nghien_cuu = client if che_do == "that" else None
            if client_nghien_cuu is not None and not co_danh_ba_truoc:
                client_nghien_cuu = None
                log("  kênh chưa có danh bạ đối thủ (nghien-cuu/doi-thu.csv) — đây là lượt ĐẦU "
               "TIÊN, hộp thư còn nguyên khối mang từ kênh gốc (cỡ vài trăm link chưa ai "
               "chấm). Không đưa ví vào lượt này — chấm bằng luật cứng trước, để dành "
               "100–200 lượt gọi AI cho các lượt sau khi hộp thư đã mỏng lại.")
            chay_mot_nut_fn(goc, ma_kenh, client=client_nghien_cuu, on_log=log, cancel=cancel)
        except Exception as loi:  # noqa: BLE001
            return finalize(ok=False, buoc_loi="nghien_cuu", loi=str(loi)[:400],
                            tom_tat="{0}: nghiên cứu hỏng — {1}".format(ma_kenh, str(loi)[:200]))
    else:
        log("1) Không nghiên cứu lại — tiếp tục lượt dở để khỏi đổi nguồn và khỏi tăng tải.")

    # ── 2) Chọn nguồn: nhặt lại lượt chưa xong (hôm nay hoặc tới 7 ngày
    # trước) trước khi tính chuyện mở nguồn mới ─────────────────────────────
    run: Optional[Dict[str, Any]] = None
    tim = tim_som
    # (LỖI 1b) `tim_som` trỏ tới một (ngày, mã lượt) mà cuối cùng KHÔNG tra ra
    # được bản ghi `run` thật trong sổ — bất thường (sổ mất dòng/hỏng), khác
    # hẳn việc L3 CHỦ ĐỘNG bỏ lượt ngay dưới. Cờ này chỉ được đặt ở đây, TRƯỚC
    # khi L3 có cơ hội tự đặt `run = None` vì một lý do hợp lệ khác.
    tim_som_bat_thuong = False
    if tim is not None:
        ngay_tim, ma_luot_tim = tim
        if ngay_tim == ngay_str:
            run = next((r for r in bao_cao["runs"] if str(r.get("ma_luot")) == ma_luot_tim), None)
        else:
            bc_goc = _doc_bao_cao_ngay(goc, ma_kenh, ngay_tim)
            run_goc = next((r for r in bc_goc["runs"] if str(r.get("ma_luot")) == ma_luot_tim), None)
            if run_goc is not None:
                run = run_goc
                bao_cao_goc = bc_goc
                ngay_goc_str = ngay_tim
                if not any(r.get("tham_chieu_ma_luot") == ma_luot_tim for r in bao_cao["runs"]):
                    bao_cao["runs"].append({"tham_chieu_ma_luot": ma_luot_tim,
                                           "tham_chieu_ngay": ngay_tim})
        if run is None:
            tim_som_bat_thuong = True

        # ═══ L3: TRẦN TỰ PHỤC HỒI (chẩn đoán 26/09/2026) ═══
        # Nhặt lại một lượt kẹt vô hạn định là tự đốt CPU/lượt gọi mãi cho một
        # nguồn đã hỏng, và chiếm mất chỗ mà `video_moi_ngay` lẽ ra dành cho
        # một nguồn KHÁC còn sản xuất được. Vượt trần (số lần, số giờ, lỗi lặp
        # lại, hoặc sắp lọt cửa sổ quét) thì BỎ HẲN lượt này (không xoá gì) —
        # nhánh dưới coi như không có lượt dở, tự chọn nguồn mới.
        if run is not None:
            ly_do_bo = _ly_do_vuot_tran_phuc_hoi(run, ngay, ngay_goc_str, bay_gio=bay_gio)
            if ly_do_bo:
                _bo_luot_qua_han(goc, ma_kenh, run, bao_cao_goc, ngay_goc_str, ly_do_bo, log)
                run = None
            else:
                _ghi_nhan_phuc_hoi(run, bay_gio=bay_gio)
                _ghi_bao_cao_ngay(goc, ma_kenh, ngay_goc_str, bao_cao_goc)

    # `run` không phải một lượt ĐÃ THẬT SỰ CHẠY (`da_chay=True`) — nghĩa là ta
    # sắp coi như "mở một lượt mới" (chọn nguồn mới hoàn toàn, HOẶC vừa nhặt
    # một lượt nhận nuôi/tham chiếu mà `chay_auto_fn` chưa hề đụng tới). Cờ
    # này dùng CHUNG cho cả cửa nhịp đăng (vá LỖI 1 ngay dưới) lẫn nhường phiên
    # kênh (chẩn đoán 28/09/2026, xem chú thích ở khối kế tiếp).
    sap_mo_luot_moi = run is None or not bool((run.get("san_xuat") or {}).get("da_chay"))

    # ═══ VÁ 28/09/2026 (LỖI 1a/1b/1c) — CỬA NHỊP ĐĂNG PHẢI ÁP DỤNG CHO MỌI
    # LƯỢT "MỞ MỚI" THẬT SỰ, không chỉ nhánh `tim_som is None` ở trên ═══
    #
    # Chẩn đoán 27→28/09/2026: kênh TL1-T7 sản xuất 2 lượt TRÙNG ĐỀ (0006 lúc
    # 21:08 27/09, 0007 lúc 05:00 28/09) từ hai nguồn khác mã, trong lúc còn
    # một gói "Sẵn sàng" chờ đăng lẽ ra phải chặn cửa. `tim_som is not None`
    # (khối trên) chỉ có nghĩa "TỪNG thấy dấu vết một lượt dở" — KHÔNG có
    # nghĩa lượt đó vẫn còn thật sự dở và đang chạy; nghiên cứu + cửa nhịp
    # đăng đã bị nhánh trên bỏ qua với đúng giả định "đang chạy tiếp lượt cũ".
    # Ba ca dưới đây kết thúc với `sap_mo_luot_moi` — tức giả định đó SAI —
    # nên phải quay lại qua đúng cửa, y hệt nhánh `tim_som is None`:
    #   (a) L3 vừa TỰ BỎ lượt (khối ngay trên đặt `run = None`) — chủ động,
    #       coi như không có lượt dở, được phép mở nguồn mới NẾU cửa cho.
    #   (b) tra sổ không ra được `run` tương ứng (`tim_som_bat_thuong`) — BẤT
    #       THƯỜNG (sổ mất dòng/hỏng), khác hẳn (a) — chốt an toàn: ghi lỗi rõ
    #       rồi DỪNG, TUYỆT ĐỐI không tự ý mở nguồn mới trong lượt này.
    #   (c) lượt NHẬN NUÔI (`_nhan_nuoi_luot_mo_coi`, L1) nhưng CHƯA TỪNG CHẠY
    #       (`san_xuat.da_chay` còn False) — đúng ca TL1-T7/0003+0004, mồ côi
    #       từ khâu kịch bản dở 24/09/2026, tool chưa hề đụng tới sản xuất.
    # Lượt ĐÃ THẬT SỰ chạy dở (`da_chay=True`) không rơi vào đây — chạy tiếp
    # bình thường ở nhánh "2) Lượt … chưa xong" phía dưới, không qua cửa lại.
    if tim_som is not None and sap_mo_luot_moi:
        if run is None and tim_som_bat_thuong:
            loi_du_lieu = LookupError(
                "_tim_run_chua_xong trỏ tới lượt {0} (ngày {1}) nhưng không tra ra được "
                "bản ghi run tương ứng trong sổ tu-chay — sổ ngày đó có thể mất dòng hoặc "
                "hỏng.".format(tim_som[1], tim_som[0]))
            mo_ta_loi = _ta_loi_day_du(loi_du_lieu)
            log("[LỖI DỮ LIỆU] {0} — dừng lượt này, TUYỆT ĐỐI không mở nguồn mới; cần tra "
               "sổ CHANNEL/{1}/tu-chay/{2}.json thủ công.".format(mo_ta_loi, ma_kenh, tim_som[0]))
            return finalize(ok=False, buoc_loi="tim_run_chua_xong", loi=mo_ta_loi,
                            tom_tat="{0}: sổ ngày bất thường (xem log) — dừng, không mở nguồn mới."
                            .format(ma_kenh))

        cho_mo, ly_do_nhip, thong_tin_nhip = _cua_so_san_xuat(
            goc, ma_kenh, kenh, bay_gio=bay_gio)
        bao_cao["nhip_dang"] = thong_tin_nhip
        for ma_goi_qua_han in thong_tin_nhip.get("qua_han_cho_dang") or []:
            log("[CHỜ QUÁ HẠN] {0} chờ quá {1} ngày — thôi chờ, sản xuất tiếp; "
               "video vẫn nằm trong DONE, đăng lúc nào tool tự nhận."
               .format(ma_goi_qua_han, max(0, int(getattr(kenh, "cho_dang_toi_da_ngay", 3) or 0))))
        if not cho_mo:
            if thong_tin_nhip.get("cho_nguoi"):
                log("[CHỜ NGƯỜI] (lượt {0}) ".format(tim_som[1]) + ly_do_nhip)
                return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_nhip), cho_nguoi=True)
            log("[NHỊP ĐĂNG] (lượt {0}) ".format(tim_som[1]) + ly_do_nhip)
            return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_nhip))

    # ═══ NHƯỜNG PHIÊN KÊNH (chẩn đoán 28/09/2026) ═══
    #
    # Sắp MỞ MỘT LƯỢT SẢN XUẤT MỚI — hoặc chọn nguồn mới hoàn toàn (`run is
    # None`), hoặc vừa nhặt một lượt CHƯA TỪNG được `chay_auto_fn` đụng tới
    # (`san_xuat.da_chay` còn False — đúng ca lượt mồ côi vừa được L1 "nhận
    # nuôi" ngay trong lượt gọi này, xem `_nhan_nuoi_luot_mo_coi`). Một lượt
    # ĐÃ da_chay=True (thật sự dở dang, đã trót đổ tiền/giờ vào) thì KHÔNG
    # nhường — chạy tiếp bình thường, bỏ dở nó phí hoài công đã đổ vào.
    #
    # Vì sao cần: `tu_chay.py --tat-ca` và phiên kênh của `vm/agent.py` (quét
    # Studio — nguồn dữ liệu học — và ĐĂNG THEO LỊCH ĐÃ HẸN GIỜ) dùng CHUNG
    # khoá máy (`.khoa-may`). Một lượt sản xuất MỚI có thể chiếm khoá NHIỀU
    # GIỜ; nếu đúng lúc đó có kênh đến hạn phiên (đặc biệt là đăng đã hẹn giờ
    # thật) thì `vm.agent.chay_hang_doi_phien` (mỗi nhịp tim chỉ thử MỘT ứng
    # viên, xem chẩn đoán "việc C" cùng ngày) không bao giờ chen được vào — lỡ
    # giờ đăng đã hẹn, hoặc để kho dữ liệu học khô cạn. Kiểm ở đây — KHÔNG cần
    # khởi động lại gì, tệp này được nạp lại mỗi giờ nên có hiệu lực ngay ở
    # lượt kế tiếp — để CHỦ ĐỘNG nhường trước khi giành khoá cho việc chưa hề
    # bắt tay vào làm, thay vì đợi `vm/` tự chen (nó không chen được).
    # Nhánh "không lượt dở" đã hỏi cửa này TRƯỚC nghiên cứu (xem "CỬA RẺ"); hỏi
    # lại ở đây vẫn đúng (nghiên cứu có thể kéo dài, một phiên vừa đến hạn) nhưng
    # không in lại dòng "[NHƯỜNG] … treo" đã in.
    if sap_mo_luot_moi:
        ket_nhuong = _kiem_nhuong_phien(goc, ma_kenh, bay_gio,
                                        log if tim_som is not None else _log_nhuong_im(log))
        if ket_nhuong:
            return finalize(tom_tat=ket_nhuong)

    if run is not None:
        o_dau = "" if ngay_goc_str == ngay_str else " (mở ngày {0})".format(ngay_goc_str)
        log("2) Lượt {0}{1} chưa xong — chạy tiếp (“{2}”), không chọn nguồn mới, không mở video "
           "trả tiền lần hai.".format(run["ma_luot"], o_dau,
                                      str(run.get("nguon", {}).get("tieu_de", ""))[:60]))
    else:
        # `video_toi_da_ngay` (29/09/2026) thắng `video_moi_ngay` khi khai > 0.
        if len(bao_cao["runs"]) >= xep_lich.tran_video_ngay(kenh):
            log("Đã đủ {0} video hôm nay cho kênh này — không chọn thêm."
               .format(xep_lich.tran_video_ngay(kenh)))
            return finalize(tom_tat="{0}: đã đủ {1} video hôm nay, không làm thêm."
                            .format(ma_kenh, xep_lich.tran_video_ngay(kenh)))

        log("2) Chọn nguồn…")
        da_lam = da_lam_mod.doc_ma_da_lam(goc, ma_kenh)
        da_lam_nhom: set = set()
        try:
            if video_da_lam_nhom is not None:
                da_lam_nhom = set(video_da_lam_nhom(goc, ma_kenh) or ())
            else:
                from . import nhom_kenh  # noqa: PLC0415 — có thể chưa tồn tại (worker khác đang viết)

                da_lam_nhom = set(nhom_kenh.video_da_lam_ca_nhom(goc, ma_kenh) or ())
        except ImportError:
            pass
        except Exception as loi:  # noqa: BLE001 — nhóm kênh hỏng thì bỏ qua, không chặn lượt riêng
            log("  (không đọc được video đã làm của cả nhóm: {0}) — bỏ qua.".format(str(loi)[:100]))

        da_chon_hom_nay = {str(r.get("nguon", {}).get("ma") or "") for r in bao_cao["runs"]}
        loai_tru = set(da_lam) | da_lam_nhom | da_chon_hom_nay
        # G4 (29/09/2026): nguồn kênh ANH EM đã giành (`giu-nguon/`, đang sản xuất,
        # chưa kịp vào da_lam) — loại, không để hai kênh cùng làm một nguồn.
        try:
            giu_khac = nghien_cuu_nhom.nguon_da_giu_boi_kenh_khac(goc, ma_kenh)
        except Exception as loi:  # noqa: BLE001 — kho giữ nguồn hỏng không chặn lượt
            giu_khac = {}
            log("  (không đọc được kho giữ nguồn của nhóm: {0}) — bỏ qua.".format(str(loi)[:100]))
        if giu_khac:
            loai_tru |= set(giu_khac)
            log("  loại {0} nguồn kênh anh em đang giữ ({1}).".format(
                len(giu_khac), ", ".join(sorted(set(giu_khac.values())))))

        # ═══ VÁ 28/09/2026 (LỖI 2) — chống làm trùng theo TIÊU ĐỀ ═══
        # `loai_tru` ở trên chỉ chặn theo MÃ VIDEO NGUỒN: hai đối thủ khác kênh
        # chép cùng chủ đề (mã khác nhau) lọt qua được — đúng ca TL1-T7-0006
        # (nguồn 8nPciHbf194) và TL1-T7-0007 (nguồn OmuR0oP6CYc) CÙNG một tiêu
        # đề tiếng Nhật, 27→28/09/2026. Gộp tiêu đề đã làm của CHÍNH kênh này
        # (mọi lượt AUTO + kế hoạch đăng + video đã công khai) và của CẢ NHÓM
        # (đối thủ khác kênh trong nhóm remake cùng chủ đề) — xem
        # `core.trung_tieu_de`, `core.nhom_kenh.tieu_de_da_lam_ca_nhom`.
        da_lam_tieu_de: List[Tuple[str, str]] = list(trung_tieu_de.doc_tieu_de_da_lam(goc, ma_kenh))
        try:
            if tieu_de_da_lam_nhom is not None:
                da_lam_tieu_de += list(tieu_de_da_lam_nhom(goc, ma_kenh) or ())
            else:
                from . import nhom_kenh  # noqa: PLC0415 — có thể chưa tồn tại (worker khác đang viết)

                da_lam_tieu_de += list(nhom_kenh.tieu_de_da_lam_ca_nhom(goc, ma_kenh) or ())
        except ImportError:
            pass
        except Exception as loi:  # noqa: BLE001 — nhóm kênh hỏng thì bỏ qua, không chặn lượt riêng
            log("  (không đọc được tiêu đề đã làm của cả nhóm: {0}) — bỏ qua.".format(str(loi)[:100]))

        # ═══ VIỆC 5b (29/09/2026) — LỚP KIỂM TRÙNG Ý ═══
        #
        # `che_do == "that"` mới đưa `goi_chat` thật — đúng nếp dòng
        # `client_nghien_cuu = client if che_do == "that" else None` ở bước
        # nghiên cứu phía trên: `che_do="thu"` (chạy thử) PHẢI giữ đúng lời hứa
        # "chọn nguồn không tốn một đồng nào" (docstring `chay_mot_ngay`) — lớp
        # kiểm trùng ý là một lượt gọi AI, không được lọt vào chế độ thử.
        nguon = None
        ma_luot_moi_ = _ma_luot_moi(goc, ma_kenh)
        thong_ke_chon: Dict[str, Any] = {}
        for _lan_giu in range(3):
            nguon = _chon_nguon(
                goc, ma_kenh, co_v7_truoc, loai_tru, cham_v7_fn, doc_danh_sach_fn, log,
                da_lam_tieu_de=da_lam_tieu_de,
                goi_chat=(_dung_goi_chat_mac_dinh(client, log, cancel) if che_do == "that" else None),
                kiem_trung_y_bat=getattr(kenh, "kiem_trung_y", True),
                thong_ke=thong_ke_chon)
            if nguon is None or che_do != "that":
                break
            # G4: GIÀNH nguồn bằng O_EXCL — kênh anh em chạy song song vừa chọn đúng
            # nguồn này thì chỉ một bên được, bên kia chọn nguồn kế.
            try:
                duoc_giu, ai_giu = nghien_cuu_nhom.giu_nguon(
                    goc, ma_kenh, str(nguon.get("ma") or ""), ma_luot=ma_luot_moi_)
            except Exception as loi:  # noqa: BLE001 — kho giữ nguồn hỏng không chặn lượt
                duoc_giu, ai_giu = True, ""
                log("  (không giữ được nguồn trong kho nhóm: {0}) — đi tiếp.".format(str(loi)[:100]))
            if duoc_giu:
                break
            log("  nguồn {0} vừa bị {1} giành — chọn nguồn khác.".format(nguon.get("ma"), ai_giu))
            loai_tru.add(str(nguon.get("ma") or ""))
            nguon = None
        if nhom_nc and "so_ung_vien" in thong_ke_chon:
            so_uv =int(thong_ke_chon.get("so_ung_vien") or 0) - (1 if nguon is not None else 0)
            if so_uv < nghien_cuu_nhom.NGUONG_UNG_VIEN:
                nghien_cuu_nhom.danh_dau_thieu(goc, ma_kenh, so_uv)
                log("  kho ứng viên còn {0} (< {1}) — lượt sau nghiên cứu lại cho nhóm."
                   .format(so_uv, nghien_cuu_nhom.NGUONG_UNG_VIEN))
        if nguon is None:
            return finalize(tom_tat="{0}: không có nguồn mới phù hợp hôm nay.".format(ma_kenh))

        # 30/09/2026 — công thức đã ra nguồn + cờ thăm dò, để hồ sơ video / thống kê theo công thức
        # (`core/chien_luoc/ket_qua.py`) nối được. Dòng không qua bộ trộn thì công thức = `nguon`.
        nguon.setdefault("cong_thuc", "chon_tay" if nguon.get("chon_tay") else str(nguon.get("nguon") or ""))
        nguon.setdefault("tham_do", False)
        # Mirror `ui_qt/trang_auto.py _chay` (nhánh nhiều link): mỗi nguồn một
        # `dau_vao` với đúng ba khoá `link`/`tieu_de`/`chu_bia`, tiêu đề để
        # trống để khâu kịch bản của kênh tự đặt theo `che_do_tieu_de`.
        run = {"ma_luot": ma_luot_moi_, "nguon": nguon,
              "ngan_sach": {}, "san_xuat": {"da_chay": False, "xong_het": False,
                                            "khau_hong": [], "loi": ""},
              "ban_giao": {"da_ban_giao": False, "ma_goi": "", "ngay_dang": "",
                          "gio_dang": "", "ly_do_trong": "", "loi": ""}}
        bao_cao["runs"].append(run)
        # Checkpoint trước việc nặng. Windows hạ tiến trình ở dòng sau thì lần
        # lịch kế vẫn thấy đúng lượt và nguồn để tự phục hồi.
        _ghi_bao_cao_ngay(goc, ma_kenh, ngay_str, bao_cao)
        luot_moi_ = auto.moi_luot(goc, ma_kenh, ma_luot_moi_,
                                  {"link": nguon["link"], "tieu_de": "", "chu_bia": ""})
        auto.ghi_luot(luot_moi_)
        log("  chọn “{0}” ({1}, nguồn {2}) — lượt {3}.".format(
            nguon["tieu_de"][:60] or nguon["link"], nguon["kenh"], nguon["nguon"], ma_luot_moi_))

    run_hien_tai = run
    ma_luot = str(run["ma_luot"])

    if che_do == "thu":
        log("Chế độ THỬ: chỉ nghiên cứu + chọn nguồn, không sản xuất, không tốn ví.")
        return finalize()

    nguon_luot = dict(run.get("nguon") or {})
    luot = auto.moi_luot(
        goc, ma_kenh, ma_luot,
        {"link": str(nguon_luot.get("link") or ""), "tieu_de": "", "chu_bia": ""})
    if auto.doc_luot(luot.thu_muc) is None:
        auto.ghi_luot(luot)

    if not luot.xong_het:
        # ── 3a) Kênh đủ điều kiện sản xuất chưa — kiểm TRƯỚC van ngân sách:
        # một kênh thiếu giọng đọc/ảnh nhân vật mà vẫn để lọt qua ngân sách
        # thì lỗi hiện ra giữa chừng một khâu, sau khi đã có thể đã tốn vài
        # bước đầu — thà nói ngay từ đầu, cùng luật `ui_qt/trang_auto.py`.
        thieu = kiem_kenh(kenh)
        if thieu:
            log("[KÊNH CHƯA ĐỦ] " + "; ".join(thieu))
            return finalize(ok=False, buoc_loi="kiem_kenh", loi="; ".join(thieu),
                            tom_tat="{0}: kênh chưa đủ điều kiện — {1}".format(ma_kenh, thieu[0]))

        # ── 3a-2) Van đĩa trống — TRƯỚC ngân sách: đĩa dưới ngưỡng an toàn
        # thì KHÔNG mở/chạy tiếp video dù ngân sách có cho phép hay không.
        # Đầy đĩa giữa chừng làm hỏng CẢ BỐN kênh dùng chung ổ C, còn hết
        # ngân sách chỉ dừng đúng một kênh — van đĩa đứng trước. Còn thiếu
        # thì thử dọn khẩn (video ĐÃ ĐĂNG của kênh đã bật `tu_don`) rồi kiểm
        # lại một lần — có thể đủ để chạy luôn hôm nay, khỏi chờ lượt sau.
        can_gb = _uoc_dung_luong_video_gb(kenh)
        con_trong_gb = _dung_luong_trong_gb(goc)
        du_dia, ly_do_dia = _kiem_dia(con_trong_gb, can_gb)
        don_khan_ket: Optional[Dict[str, Any]] = None
        if not du_dia:
            log("[ĐĨA] " + ly_do_dia)
            don_khan_ket = _don_khan_ngay(goc, can_gb, log)
            con_sau_don_khan = don_khan_ket.get("con_sau_gb")
            if con_sau_don_khan is not None:
                con_trong_gb = con_sau_don_khan
            du_dia, ly_do_dia = _kiem_dia(con_trong_gb, can_gb)
        run["dia"] = {"con_trong_gb": con_trong_gb, "can_gb": can_gb, "du": du_dia,
                     "ly_do": ly_do_dia, "don_khan": don_khan_ket}
        if not du_dia:
            log("[ĐĨA] vẫn không đủ sau dọn khẩn — " + ly_do_dia)
            return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_dia))
        if don_khan_ket is not None:
            log("  đĩa đã đủ sau dọn khẩn — chạy tiếp.")

        # Van RAM động: con số luồng trong auto_khau đã tự hạ theo RAM còn
        # trống, nhưng khi Windows chỉ còn dưới 3 GB thì ngay cả một worker
        # nặng cũng có thể làm cả VPS bị hạ. Giữ nguyên lượt và để lịch sau tự
        # thử lại là cách phục hồi an toàn.
        ram_trong = _ram_trong_gb()
        if ram_trong is not None and ram_trong < RAM_TRONG_TOI_THIEU_GB:
            ly_do_ram = ("RAM chỉ còn {0:.1f} GB, dưới ngưỡng an toàn {1:.1f} GB — "
                          "tạm chưa sản xuất; lượt được giữ nguyên để lần chạy sau tự tiếp tục."
                          ).format(ram_trong, RAM_TRONG_TOI_THIEU_GB)
            run["bo_nho"] = {"con_trong_gb": ram_trong,
                              "toi_thieu_gb": RAM_TRONG_TOI_THIEU_GB,
                              "du": False}
            log("[BỘ NHỚ] " + ly_do_ram)
            return finalize(ok=False, buoc_loi="bo_nho", loi=ly_do_ram,
                            tom_tat="{0}: {1}".format(ma_kenh, ly_do_ram))
        run["bo_nho"] = {"con_trong_gb": ram_trong,
                          "toi_thieu_gb": RAM_TRONG_TOI_THIEU_GB,
                          "du": True}

        # ── 3b) Van ngân sách ────────────────────────────────────────────
        uoc_micro = _uoc_chi_phi_micro(kenh, gia or DEFAULT_PRICES)
        uoc_vnd = micro_to_vnd(uoc_micro)
        da_chi_truoc_do = sum(
            int((r.get("ngan_sach") or {}).get("uoc_tinh_vnd") or 0)
            for r in bao_cao["runs"]
            if str(r.get("ma_luot")) != ma_luot and (r.get("san_xuat") or {}).get("da_chay"))
        han = int(kenh.ngan_sach_ngay or 0)
        cho_phep, ly_do_ns = _kiem_ngan_sach(han, uoc_vnd, da_chi_truoc_do)
        run["ngan_sach"] = {"uoc_tinh_vnd": uoc_vnd, "da_chi_truoc_do_vnd": da_chi_truoc_do,
                           "han_muc_vnd": han, "cho_phep": cho_phep, "ly_do": ly_do_ns}
        if not cho_phep:
            log("[NGÂN SÁCH] " + ly_do_ns)
            return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_ns))
        log("3) Ngân sách: ước {0}, đã tiêu hôm nay {1}, trần {2} — cho chạy."
           .format(_vnd(uoc_vnd), _vnd(da_chi_truoc_do), _vnd(han)))

        log("4) Sản xuất…")
        run["san_xuat"]["da_chay"] = True
        try:
            goi_chat_fn = goi_chat or _dung_goi_chat_mac_dinh(client, log, cancel)
            if dung_viec is not None:
                # Bài kiểm đưa `dung_viec` giả thì không cần `BoiCanh` THẬT của
                # `core.auto_khau` (mô-đun nặng, không liên quan tới việc đang
                # kiểm) — một hộp thuộc tính nhẹ là đủ, vì chỉ có `dung_viec`
                # giả đọc nó.
                dung_viec_fn = dung_viec
                bc: Any = _HopThuocTinh(goc=goc, kenh=kenh, client=client, on_log=log,
                                        cancel=cancel, goi_chat=goi_chat_fn)
            else:
                from .auto_khau import BoiCanh, dung_bo_viec  # noqa: PLC0415

                dung_viec_fn = dung_bo_viec
                bc = BoiCanh(goc=goc, kenh=kenh, goi_chat=goi_chat_fn, client=client,
                            on_log=log, cancel=cancel)
            if chay_auto is not None:
                chay_auto_fn = chay_auto
                viec = dung_viec_fn(bc)
            else:
                from .hang_doi_auto import khoa_khau_may  # noqa: PLC0415

                chay_auto_fn = auto.chay
                viec = khoa_khau_may(dung_viec_fn(bc), cancel=cancel, ghi=log)
                # Điều phối BẬT: phụ đề/dựng giữ khe "nang" LIÊN TIẾN TRÌNH (không
                # còn `.khoa-may` cả lượt). Tắt → không làm gì.
                viec = dieu_phoi.boc_khau_nang(viec, goc=goc, kenh=ma_kenh,
                                               cancel=cancel, ghi=log)
            luot = chay_auto_fn(luot, viec, on_log=log, cancel=cancel)
            _nhan_het_tien_tu_luot(goc, run, luot, log)
        except Exception as loi:  # noqa: BLE001
            if su_co.phan_loai(loi) == su_co.HET_TIEN:
                _tam_dung_vi_het_tien(goc, run, str(loi), log)
            loi_dia_day = _tim_loi_dia_day(loi)
            if loi_dia_day is not None:
                # ĐĨA ĐẦY, không phải lỗi sản xuất bình thường (mạng rớt,
                # engine hỏng…) — đánh dấu riêng để KHÔNG bị coi như lỗi API
                # thường rồi đốt thêm lượt thử lại vô ích trong lúc đĩa vẫn
                # còn 0 byte trống. Dọn khẩn ngay — lượt SAU (mai, hoặc bấm
                # tay lại hôm nay) có cơ may chạy được nếu dọn khẩn giải
                # phóng đủ chỗ.
                run["san_xuat"]["loi"] = str(loi_dia_day)[:400]
                run["san_xuat"]["dia_day"] = True
                log("  [ĐĨA ĐẦY] sản xuất dừng giữa chừng vì hết dung lượng đĩa: {0}"
                   .format(run["san_xuat"]["loi"]))
                can_gb = _uoc_dung_luong_video_gb(kenh)
                run["dia"] = {"don_khan": _don_khan_ngay(goc, can_gb, log)}
                return finalize(ok=False, buoc_loi="dia_day", loi=run["san_xuat"]["loi"],
                                tom_tat="{0}: đĩa đầy giữa chừng sản xuất — {1}".format(
                                    ma_kenh, run["san_xuat"]["loi"]))
            run["san_xuat"]["loi"] = str(loi)[:400]
            log("  sản xuất hỏng: " + run["san_xuat"]["loi"])
            return finalize(ok=False, buoc_loi="san_xuat", loi=run["san_xuat"]["loi"],
                            tom_tat="{0}: sản xuất hỏng — {1}".format(ma_kenh, run["san_xuat"]["loi"]))
        run["san_xuat"]["xong_het"] = bool(luot.xong_het)
        run["san_xuat"]["khau_hong"] = list(luot.khau_dang_hong)
        if not luot.xong_het:
            log("  chưa xong hết — " + auto.tom_tat(luot))
    else:
        log("4) Sản xuất — lượt {0} đã xong hết từ trước, bỏ qua.".format(ma_luot))
        run["san_xuat"]["xong_het"] = True

    khau_dung = luot.tt("dung")
    if khau_dung.trang_thai == auto.XONG:
        log("5) Bàn giao…")
        if not kenh.thu_muc_done:
            ly_do = ("kênh chưa khai `thu_muc_done` trong kenh.yaml — sản xuất xong nhưng KHÔNG "
                     "bàn giao, video vẫn nằm nguyên trong PROJECTS/AUTO.")
            run["ban_giao"]["ly_do_trong"] = ly_do
            log("  " + ly_do)
        else:
            ngay_dang, gio_dang, ly_do_trong = "", "", ""
            if xep_lich.che_do_nhieu_khe(kenh):
                # Nhiều khe/ngày (29/09/2026): khe trống sớm nhất ≥ bây giờ +
                # bien_xu_ly_gio (mặc định 12h) — đủ để máy đăng tải lên trước.
                ngay_dang, gio_dang = xep_lich.khe_trong_som_nhat(
                    goc, ma_kenh, kenh, bay_gio=bay_gio)
                if not ngay_dang:
                    ly_do_trong = ("không tìm được khe trống trong 60 ngày tới cho nhịp "
                                   + ", ".join(kenh.nhip_dang) + " — để trống, tự đặt tay.")
            elif kenh.tu_duyet and kenh.gio_dang:
                # `bay_gio` là lúc BÀN GIAO XONG (bây giờ), không phải lúc
                # `chay_mot_ngay` bắt đầu — sản xuất tốn vài tiếng nên hai mốc
                # có thể khác ngày. Xem docstring `_tim_gio_trong`.
                ngay_dang, gio_dang = _tim_gio_trong(goc, ma_kenh, kenh.gio_dang, ngay,
                                                     bay_gio=bay_gio)
                if not ngay_dang:
                    ly_do_trong = ("không tìm được ngày trống trong 60 ngày tới cho giờ "
                                  + kenh.gio_dang + " — để trống, tự đặt tay.")
            elif kenh.tu_duyet and not kenh.gio_dang:
                ly_do_trong = "tu_duyet: true nhưng gio_dang trống trong kenh.yaml — để trống ngày giờ."
            else:
                ly_do_trong = "tu_duyet: false — để trống ngày giờ, tự duyệt trong bảng kế hoạch."
            try:
                # QA + chép gói (FFmpeg giải mã soát + chép mp4) — lớp "nang".
                with dieu_phoi.giu_nang(goc, "qa_chep", kenh=ma_kenh, uu_tien=2,
                                        cancel=cancel, ghi=log):
                    ma_goi, _moi = ban_giao_fn(goc, ma_kenh, ma_luot, kenh.thu_muc_done,
                                              ngay=ngay_dang, gio=gio_dang)
                run["ban_giao"].update(da_ban_giao=True, ma_goi=ma_goi, ngay_dang=ngay_dang,
                                       gio_dang=gio_dang, ly_do_trong=ly_do_trong)
                # Một content chỉ là quyết định cho video này. Khi đã bàn giao
                # sang khâu đăng, bỏ đúng lựa chọn vừa dùng để lần kế tiếp được
                # chấm lại trên dữ liệu mới thay vì tích một kho content cũ.
                try:
                    from . import chon_content as lua_tay  # noqa: PLC0415

                    ma_nguon = str((run.get("nguon") or {}).get("ma") or "")
                    lua_tay.hoan_tat_lua_chon(goc, ma_kenh, ma_nguon)
                except Exception as loi_chot:  # noqa: BLE001 — bàn giao đã thành công
                    log("  (chưa dọn được lựa chọn content: {0})".format(
                        str(loi_chot)[:100]))
                if ngay_dang and gio_dang:
                    log("  bàn giao gói {0} — đã đặt lịch {1} {2} (tu_duyet: true)."
                       .format(ma_goi, ngay_dang, gio_dang))
                else:
                    log("  bàn giao gói {0} — {1}".format(ma_goi, ly_do_trong))
            except Exception as loi:  # noqa: BLE001
                run["ban_giao"]["loi"] = str(loi)[:400]
                log("  bàn giao hỏng: " + run["ban_giao"]["loi"])
                return finalize(ok=False, buoc_loi="ban_giao", loi=run["ban_giao"]["loi"],
                                tom_tat="{0}: bàn giao hỏng — {1}".format(ma_kenh, run["ban_giao"]["loi"]))

    return finalize()


class _HopThuocTinh:
    """Hộp thuộc tính nhẹ, đứng thay `core.auto_khau.BoiCanh` khi bài kiểm đã
    đưa `dung_viec` giả (không đọc `BoiCanh` thật, nên không cần nó nặng)."""

    def __init__(self, **thuoc_tinh: Any) -> None:
        self.__dict__.update(thuoc_tinh)


def kenh_tu_chay(goc: str) -> List[str]:
    """Mã các kênh có `tu_chay: true` trong `kenh.yaml`, theo bảng chữ cái."""
    ra: List[str] = []
    for ma in liet_ke_kenh(goc):
        try:
            k = doc_kenh(goc, ma)
        except Exception:  # noqa: BLE001 — một kênh hỏng không được chặn cả danh sách
            continue
        if k.tu_chay:
            ra.append(ma)
    return ra


def _ta_loi_day_du(loi: BaseException) -> str:
    """`"TênLớp: nội dung"` — KHÔNG BAO GIỜ RỖNG, kể cả khi `str(loi)` rỗng
    (vd `KeyError()`, `AssertionError()` không kèm thông điệp).

    Bắt đúng từ sự cố THẬT trên VPS này (16:00 26/09/2026): cả ba kênh cùng ghi
    "lỗi ngoài dự kiến: " TRỐNG TRƠN (và "đồng bộ đối thủ nhóm hỏng: " cũng rỗng),
    vì chỗ bắt lỗi cũ gọi thẳng `str(loi)` — không dò được lỗi gì, mất dấu vết.
    Tên lớp luôn có (`type(loi).__name__`), nên chuỗi trả về ở đây KHÔNG BAO GIỜ
    rỗng, kể cả với một ngoại lệ không mang thông điệp nào.
    """
    thong_diep = str(loi).strip()
    ten_lop = type(loi).__name__
    return "{0}: {1}".format(ten_lop, thong_diep) if thong_diep else ten_lop


def _log_traceback_day_du(log: Callable[[str], None], loi: BaseException) -> None:
    """Ghi TOÀN BỘ traceback của `loi` vào `log` — mỗi dòng traceback một lần gọi
    `log`, thụt vào hai khoảng để không lẫn với các dòng nhật ký thường.

    Dùng cho đúng những chỗ bắt "lỗi NGOÀI DỰ KIẾN" (không phải sự cố đã biết
    trước, có câu chữa sẵn) — một lỗi câm (không thông điệp) vẫn để lại đủ dấu
    vết tra được thay vì mất dạng vĩnh viễn (đúng ca 16:00 26/09/2026).

    Ghi log lỗi không được phép tự ném thêm lỗi — mọi trục trặc ở đây đều bị
    nuốt lặng lẽ.
    """
    try:
        for dong in traceback.format_exception(type(loi), loi, loi.__traceback__):
            for dong_con in dong.splitlines():
                log("    " + dong_con)
    except Exception:  # noqa: BLE001 — ghi log lỗi không được phép ném thêm lỗi
        pass


def chay_nhieu_kenh(goc: str, danh_sach_kenh: List[str], *, client: Any = None,
                    che_do: str = "that",
                    chay_mot_ngay_fn: Optional[Callable[..., Dict[str, Any]]] = None,
                    on_log: Optional[Callable[[str], None]] = print,
                    **kwargs: Any) -> Dict[str, Any]:
    """Chạy `chay_mot_ngay` LẦN LƯỢT cho từng kênh trong `danh_sach_kenh`.

    Một kênh hỏng (kể cả ném lỗi ngoài dự kiến) không được chặn kênh sau —
    `python tu_chay.py --tat-ca` phải cố sản xuất được cho MỌI kênh còn lại.

    Mỗi dòng kết quả mang thêm `bat_dau`/`ket_thuc` (giờ thật, ISO giây) — các
    kênh chạy LẦN LƯỢT (không song song), một video tốn 2–4 tiếng, nên một
    lượt `--tat-ca` trải dài tự nhiên qua nhiều giờ trong ngày; đây là chỗ DUY
    NHẤT ghi lại đúng độ trải đó để sổ ngày (`chay_tat_ca`) hiện ra cho người
    đọc, không phải đoán.
    """
    chay_fn = chay_mot_ngay_fn or chay_mot_ngay
    ket_qua: List[Dict[str, Any]] = []
    co_loi = False
    for ma in danh_sach_kenh:
        bat_dau = _dt.datetime.now().isoformat(timespec="seconds")
        try:
            ket = chay_fn(goc, ma, client=client, che_do=che_do, on_log=on_log, **kwargs)
            ok = bool(ket.get("ok", True))
            ket_qua.append({"kenh": ma, "ok": ok, "tom_tat": ket.get("tom_tat", ""),
                           "loi": ket.get("loi", ""), "bat_dau": bat_dau,
                           "keo_nhau": ket.get("keo_nhau", ""),
                           # V2-tối-giản: máy đứng im CHỜ NGƯỜI (gói chờ đăng) —
                           # khác "ok" thường, xem chú thích ở `finalize()`.
                           "cho_nguoi": bool(ket.get("cho_nguoi")),
                           "ket_thuc": _dt.datetime.now().isoformat(timespec="seconds")})
            if not ok:
                co_loi = True
        except Exception as loi:  # noqa: BLE001 — xem docstring
            co_loi = True
            # VÁ 28/09/2026: `str(loi)` có thể RỖNG (vd `KeyError()`,
            # `AssertionError()` không kèm thông điệp) — đúng sự cố thật 16:00
            # 26/09/2026: cả ba kênh cùng ghi "lỗi ngoài dự kiến: " trống trơn,
            # không dò được vì sao. `_ta_loi_day_du` luôn kèm tên lớp lỗi, không
            # bao giờ rỗng; traceback đầy đủ ghi riêng vào log để tra được
            # chính xác dòng nào hỏng.
            mo_ta_loi = _ta_loi_day_du(loi)
            if on_log is not None:
                on_log("[{0}] lỗi ngoài dự kiến: {1}".format(ma, mo_ta_loi))
                _log_traceback_day_du(on_log, loi)
            ket_qua.append({"kenh": ma, "ok": False,
                           "tom_tat": "{0}: lỗi ngoài dự kiến — {1}".format(ma, mo_ta_loi),
                           "loi": mo_ta_loi[:400], "bat_dau": bat_dau,
                           "ket_thuc": _dt.datetime.now().isoformat(timespec="seconds")})
    return {"ket_qua": ket_qua, "co_loi": co_loi}


# ══════════════════════════════════════════════════════════════════════════
# `tu_chay.py --tat-ca` — đồng bộ nhóm, chạy mọi kênh, ghi sổ NGÀY DÙNG CHUNG
# ══════════════════════════════════════════════════════════════════════════
#
# Ba việc thêm ngoài vòng lặp từng kênh ở `chay_nhieu_kenh` (vốn không biết gì
# về "nhóm" hay "sổ ngày dùng chung" — nó chỉ chạy `chay_mot_ngay` lần lượt):
#
#   1) đồng bộ dữ liệu NHÓM (đối thủ chung, bảng chéo kênh) TRƯỚC khi mở video
#      nào — xem `core/nhom_kenh.py`. Một nhóm hỏng không được chặn kênh khác.
#   2) sổ ngày CHO CẢ MÁY, không phải cho một kênh — `CHANNEL/<kênh>/tu-chay/`
#      đã có (một kênh, một ngày); đây là `workspace/tu-chay/` (mọi kênh, một
#      ngày), để chủ dự án mở MỘT tệp là biết hôm nay cả 5 kênh ra sao, tốn
#      bao nhiêu — không phải mở năm thư mục.
#   3) log ra ĐĨA — `pythonw.exe` (Task Scheduler gọi tới) không có console,
#      `print()` không có ai đọc và ở một số máy còn ném lỗi vì `sys.stdout`
#      là `None`. Xem `bo_log_tat_ca`.


#: `workspace/tu-chay/<ngày>.json` + `.md` — sổ NGÀY CHO CẢ MÁY (mọi kênh),
#: khác hẳn `CHANNEL/<kênh>/tu-chay/<ngày>.json` (một kênh) ở trên.
THU_MUC_BAO_CAO_TAT_CA = os.path.join("workspace", "tu-chay")

#: Vượt ngần này thì `bo_log_tat_ca` xoá tệp cũ rồi ghi lại từ đầu — cách đơn
#: giản nhất để log không phình vô hạn qua nhiều tháng chạy mỗi đêm.
GIOI_HAN_LOG_TAT_CA_BYTE = 5 * 1024 * 1024


def dong_bo_nhom_truoc_khi_chay(
    goc: str, danh_sach_kenh: List[str], *,
    on_log: Optional[Callable[[str], None]] = None,
    dong_bo_doi_thu_fn: Optional[Callable[[str, str], Any]] = None,
    ghi_bang_nhom_fn: Optional[Callable[[str, str], Any]] = None,
) -> List[str]:
    """Trước khi chạy TỪNG kênh: gộp hộp thư đối thủ + ghi bảng chéo kênh cho
    mọi NHÓM có mặt trong `danh_sach_kenh` (mỗi nhóm chỉ một lượt, dù có nhiều
    kênh cùng nhóm) — xem `core/nhom_kenh.dong_bo_doi_thu`/`ghi_bang_nhom`.

    Một nhóm hỏng (CSV kẹt, ổ đĩa bận…) chỉ được GHI LOG rồi bỏ qua — không
    được chặn `--tat-ca` của những kênh không thuộc nhóm đó, và cũng không
    được chặn cả kênh CÙNG nhóm: đồng bộ hỏng thì kênh vẫn tự chạy được, chỉ
    là không thấy dữ liệu mới nhất của anh em.

    Trả về tên các nhóm đã thử đồng bộ — để `chay_tat_ca` ghi vào sổ ngày.
    """
    def log(dong: str) -> None:
        if on_log is not None:
            try:
                on_log(dong)
            except Exception:  # noqa: BLE001 — log hỏng không được chặn việc thật
                pass

    from . import nhom_kenh  # noqa: PLC0415 — nhập muộn, cùng lý do với `_chon_nguon`

    dong_bo_fn = dong_bo_doi_thu_fn or nhom_kenh.dong_bo_doi_thu
    ghi_bang_fn = ghi_bang_nhom_fn or nhom_kenh.ghi_bang_nhom

    nhom_da_thu: List[str] = []
    da_thay: set = set()
    for ma in danh_sach_kenh:
        try:
            nhom = nhom_kenh.nhom_cua_kenh(goc, ma)
        except Exception as loi:  # noqa: BLE001
            log("  (không đọc được nhóm của kênh {0}: {1}) — bỏ qua.".format(ma, str(loi)[:100]))
            continue
        if not nhom or nhom in da_thay:
            continue
        da_thay.add(nhom)
        nhom_da_thu.append(nhom)
        try:
            ket = dong_bo_fn(goc, nhom)
            log("  đồng bộ nhóm “{0}”: {1} kênh, +{2} link đối thủ, +{3} dòng trang chủ."
               .format(nhom, ket.get("kenh", 0), ket.get("link_them", 0),
                       ket.get("trang_chu_them", 0)))
        except Exception as loi:  # noqa: BLE001
            # VÁ 28/09/2026: cùng lỗi "câm" như trên — đúng sự cố thật 16:00
            # 26/09/2026 ("đồng bộ đối thủ nhóm hỏng: " cũng rỗng trơn).
            log("  đồng bộ đối thủ nhóm “{0}” hỏng: {1} — bỏ qua, không chặn lượt chạy."
               .format(nhom, _ta_loi_day_du(loi)))
            _log_traceback_day_du(log, loi)
        try:
            ghi_bang_fn(goc, nhom)
        except Exception as loi:  # noqa: BLE001
            log("  ghi bảng chéo kênh nhóm “{0}” hỏng: {1} — bỏ qua.".format(nhom, _ta_loi_day_du(loi)))
    return nhom_da_thu


def dem_kho_loi_thoai(goc: str, danh_sach_kenh: List[str],
                      ngay_str: str = "") -> Dict[str, int]:
    """Gộp số liệu KHO LỜI THOẠI của mọi kênh trong lượt — cho sổ ngày.

    Đếm theo THƯ MỤC KHO, không theo kênh: 4 kênh cùng nhóm dùng CHUNG một kho
    (`CHANNEL/_NHOM/<nhóm>/loi-thoai/`, xem `core/loi_thoai.thu_muc_kho`), nên
    cộng từng kênh là nhân bốn đúng cùng một đống tệp và sổ ngày nói một con số
    gấp bốn sự thật.

    Kho hỏng/không đọc được thì trả `{}` — sổ ngày bỏ dòng ấy đi, không chặn
    việc ghi sổ (sổ là thứ duy nhất còn đọc lại được sáng hôm sau).
    """
    ket = {"co": 0, "khong_co": 0, "hom_nay": 0}
    da_dem: set = set()
    try:
        from . import loi_thoai as kho  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return {}
    for ma in danh_sach_kenh or []:
        try:
            duong = os.path.normcase(os.path.abspath(kho.thu_muc_kho(goc, ma)))
            if duong in da_dem:
                continue
            da_dem.add(duong)
            mot = kho.dem(goc, ma, hom_nay=ngay_str)
        except Exception:  # noqa: BLE001 — một kênh hỏng không được chặn cả sổ
            continue
        for k in ket:
            ket[k] += int(mot.get(k) or 0)
    return ket


def duong_bao_cao_tat_ca(goc: str, ngay_str: str, duoi: str) -> str:
    return os.path.join(goc, THU_MUC_BAO_CAO_TAT_CA, "{0}.{1}".format(ngay_str, duoi))


def _doc_bao_cao_tat_ca_ngay(goc: str, ngay_str: str) -> Dict[str, Any]:
    duong = duong_bao_cao_tat_ca(goc, ngay_str, "json")
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        if isinstance(du, dict) and isinstance(du.get("runs"), list):
            return du
    except (OSError, ValueError):
        pass
    return {"ngay": ngay_str, "runs": []}


def _gio_ngan(iso: str) -> str:
    """`"2026-09-18T14:32:07"` → `"14:32:07"` — chỉ để hiện cho người đọc,
    không parse lại ở đâu khác."""
    iso = str(iso or "")
    return iso.split("T", 1)[-1] if "T" in iso else iso


def _dung_md_tat_ca(ngay_str: str, runs: List[Dict[str, Any]]) -> str:
    dong = ["# Tự chạy — {0}".format(ngay_str), ""]
    for i, r in enumerate(runs, 1):
        dong.append("## Lượt {0} — {1} (chế độ {2})".format(i, r.get("luc", "?"), r.get("che_do", "?")))
        dong.append("")
        for k in r.get("ket_qua") or []:
            khoang = ""
            if k.get("bat_dau") or k.get("ket_thuc"):
                khoang = " ({0} → {1})".format(_gio_ngan(k.get("bat_dau")), _gio_ngan(k.get("ket_thuc")))
            # V2-tối-giản: máy đứng im CHỜ NGƯỜI (gói chờ đăng) không còn được
            # gọi là "OK" — xem chú thích ở `finalize()`/`chay_nhieu_kenh`.
            if k.get("cho_nguoi"):
                nhan = "CHỜ NGƯỜI"
            elif k.get("ok"):
                nhan = "OK"
            else:
                nhan = "LỖI"
            dong.append("- [{0}] {1}{2}".format(nhan, k.get("tom_tat", ""), khoang))
            # Một dòng con cho KÊNH NÀO ĐANG KÉO KÊNH NÀO — xem `_dong_keo_nhau`. Rỗng
            # (kênh đứng một mình, hay nhóm chưa có bảng) thì không thêm gì.
            if k.get("keo_nhau"):
                dong.append("  - kéo nhau: {0}".format(k["keo_nhau"]))
        if not r.get("ket_qua"):
            dong.append("- (không có kênh nào để chạy)")
        dong.append("")
        dong.append("Tổng ước chi lượt này: {0}".format(_vnd(int(r.get("tong_uoc_vnd") or 0))))
        if r.get("nhom_dong_bo"):
            dong.append("Đã đồng bộ nhóm: {0}".format(", ".join(r["nhom_dong_bo"])))
        con_gb = r.get("dia_con_trong_gb")
        if con_gb is not None:
            dong.append("Đĩa còn trống (cuối lượt): {0:.1f} GB".format(con_gb))
        don = r.get("don_dep") or {}
        if don.get("tong_bytes"):
            # L4 (chẩn đoán 26/09/2026): nhãn từng CỐ ĐỊNH ghi "video đã đăng quá
            # hạn ân xá" dù `don-dep.log` (nguồn sự thật thật sự, xem
            # `core/don_dep._ghi_log`) có thể ghi lý do KHÁC hẳn — luật hai
            # ("quá N lượt, chưa đăng", `core.don_dep.LY_DO_QUA_SO_LUOT`) cũng
            # dọn qua đúng cửa này. Dùng ĐÚNG lý do đã xoá (`don["ly_do"]`, gom
            # ở `chay_tat_ca` từ `da_don`); sổ CŨ chưa có trường này thì giữ
            # nguyên câu cũ để không suy diễn ngược.
            ly_do_ds = don.get("ly_do") or []
            nhan_ly_do = ", ".join(ly_do_ds) if ly_do_ds else don_dep.LY_DO_DA_DANG
            dong.append("Đã dọn đĩa (thường, {0}): giải phóng {1}"
                       .format(nhan_ly_do, _byte_nguoi_doc(don.get("tong_bytes") or 0)))
            for ma_k, so_byte in (don.get("theo_kenh") or {}).items():
                if so_byte:
                    dong.append("  - {0}: {1}".format(ma_k, _byte_nguoi_doc(so_byte)))
        # Kho lời thoại — chủ dự án đọc sổ này mỗi sáng, và đây là chỗ DUY NHẤT
        # nói được ngay rằng phiên trình duyệt hôm qua có đổ được lời thoại vào
        # kho hay không. Không có nó thì việc kho cạn chỉ lộ ra lúc khâu
        # `kich-ban` chết — đúng cái đã xảy ra đêm 22/09/2026, và lúc ấy thì
        # tiền của cả đêm đã mất rồi. `+0 hôm nay` là một tín hiệu: phiên trình
        # duyệt không chạy, hoặc `lay_loi_thoai` đang tắt, hoặc bảng phụ đề của
        # YouTube đã đổi DOM (xem `core/ytb_extension/loi-thoai.js`).
        kho = r.get("kho_loi_thoai") or {}
        if kho:
            dong.append("Kho lời thoại (trình duyệt kênh hút về): {0} video có lời thoại · "
                       "+{1} lấy được hôm nay · {2} video không có bảng phụ đề"
                       .format(kho.get("co") or 0, kho.get("hom_nay") or 0,
                               kho.get("khong_co") or 0))
        don_khan = r.get("don_khan") or {}
        if don_khan.get("tong_bytes"):
            dong.append("Đã dọn KHẨN (đĩa chạm ngưỡng an toàn giữa lượt, {0} lần): giải phóng {1}"
                       .format(don_khan.get("so_lan") or 0, _byte_nguoi_doc(don_khan.get("tong_bytes") or 0)))
        don_mo_rong = r.get("don_mo_rong") or {}
        if don_mo_rong.get("tong_bytes"):
            dong.append("Đã dọn mở rộng (báo cáo ngày cũ, nhật ký dọn dẹp quá cỡ): giải phóng {0}"
                       .format(_byte_nguoi_doc(don_mo_rong.get("tong_bytes") or 0)))
        # Khối "Sức khoẻ đĩa" — xem `core.don_dep_mo_rong.dinh_dang_suc_khoe_dia_md`.
        # Đo mà không đo được (đĩa lỗi, quyền bị chặn…) thì bỏ qua lặng lẽ —
        # một sổ ngày thiếu một khối phụ vẫn hơn cả sổ ngày ghi không ra.
        sk = r.get("suc_khoe_dia") or {}
        if sk:
            dong.append(don_dep_mo_rong.dinh_dang_suc_khoe_dia_md(sk).rstrip("\n"))
        dong.append("")
    return "\n".join(dong) + "\n"


def ghi_bao_cao_tat_ca(goc: str, ngay_str: str, luot: Dict[str, Any]) -> Tuple[str, str]:
    """Nối THÊM một lượt `--tat-ca` vào sổ ngày dùng chung cho cả máy.

    Chạy `--tat-ca` hai lần trong cùng một ngày (bấm tay đè lên lịch, hay lịch
    chạy lại sau khi máy khởi động lại) thì GIỮ CẢ HAI lượt, mỗi lượt một mốc
    giờ riêng — không ghi đè, không mất dấu vết lượt trước. Ghi nguyên tử
    (`ghi_json`/`ghi_chu`: tệp tạm rồi đổi tên) — cùng nết mọi sổ khác trong
    tool. Trả `(đường .md, đường .json)`.
    """
    so_ = _doc_bao_cao_tat_ca_ngay(goc, ngay_str)
    so_["runs"].append(luot)
    duong_json = duong_bao_cao_tat_ca(goc, ngay_str, "json")
    duong_md = duong_bao_cao_tat_ca(goc, ngay_str, "md")
    ghi_json(duong_json, so_)
    ghi_chu(duong_md, _dung_md_tat_ca(ngay_str, so_["runs"]))
    return duong_md, duong_json


def duong_log_tat_ca(goc: str) -> str:
    return os.path.join(goc, "workspace", "tu-chay", "tu-chay.log")


def _ghi_dong_log(duong_log: str, dong: str, *,
                  gioi_han_byte: int = GIOI_HAN_LOG_TAT_CA_BYTE) -> None:
    try:
        os.makedirs(os.path.dirname(duong_log), exist_ok=True)
        try:
            if os.path.getsize(duong_log) > gioi_han_byte:
                os.remove(duong_log)  # "xoay" kiểu đơn giản nhất: đầy thì xoá, ghi lại từ đầu
        except OSError:
            pass
        moc = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(duong_log, "a", encoding="utf-8") as tep:
            tep.write("[{0}] {1}\n".format(moc, dong))
    except OSError:
        pass  # ghi log hỏng không được phép làm chết lượt --tat-ca đang chạy thật


def bo_log_tat_ca(goc: str, *, gioi_han_byte: int = GIOI_HAN_LOG_TAT_CA_BYTE,
                  in_console: bool = True) -> Callable[[str], None]:
    """`on_log` cho `--tat-ca`: LUÔN ghi vào `workspace/tu-chay/tu-chay.log`,
    và chỉ thử in ra console khi máy THẬT SỰ có console.

    `pythonw.exe` (thứ Task Scheduler gọi tới, xem `core/lich_tu_chay.py`)
    không có console — `sys.stdout` có thể là `None`, và gọi `print()` lúc đó
    ném `AttributeError` giữa chừng một lượt đang tốn tiền thật. Tệp log trên
    đĩa là nơi DUY NHẤT chủ dự án còn đọc lại được việc đêm qua đã xảy ra gì.
    """
    duong_log = duong_log_tat_ca(goc)

    def log(dong: str) -> None:
        _ghi_dong_log(duong_log, str(dong), gioi_han_byte=gioi_han_byte)
        if in_console and sys.stdout is not None:
            try:
                print(dong)
            except Exception:  # noqa: BLE001 — console vừa đóng giữa chừng thì kệ, đã ghi log rồi
                pass

    return log


def chay_tat_ca(
    goc: str, *, client: Any = None, che_do: str = "that",
    hom_nay: Optional[_dt.date] = None,
    on_log: Optional[Callable[[str], None]] = None,
    chay_mot_ngay_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    dong_bo_doi_thu_fn: Optional[Callable[[str, str], Any]] = None,
    ghi_bang_nhom_fn: Optional[Callable[[str, str], Any]] = None,
    don_theo_cai_dat_fn: Optional[Callable[[str, str], Dict[str, Any]]] = None,
    don_mo_rong_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    danh_sach_kenh: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Toàn bộ việc của `python tu_chay.py --tat-ca`, ĐÚNG THỨ TỰ:

        1. đồng bộ dữ liệu NHÓM (đối thủ chung, bảng chéo kênh) — `dong_bo_nhom_truoc_khi_chay`.
        2. chạy LẦN LƯỢT mọi kênh có `tu_chay: true` — `chay_nhieu_kenh` (mỗi kênh một lượt
           `chay_mot_ngay`: nghiên cứu → chọn nguồn → sản xuất → bàn giao).
        3. DỌN ĐĨA — `don_dep.don_theo_cai_dat` cho từng kênh (chỉ kênh bật `tu_don`; mặc định
           tắt, xem `core/don_dep.py`). Chạy SAU vòng sản xuất vì dọn theo NGÀY ĐĂNG + hạn ân xá,
           không liên quan gì tới lượt vừa sản xuất — đặt sau chỉ để một lượt `--tat-ca` vừa lo
           sản xuất mới vừa tiện tay dọn rác cũ, khỏi cần một lịch riêng.
        3b. DỌN MỞ RỘNG — `don_dep_mo_rong.don_tat_ca_theo_cai_dat` (báo cáo ngày cũ, nhật ký
            dọn dẹp quá cỡ). CÙNG cờ `tu_don` như bước 3, không cờ riêng, không nới lỏng gì
            thêm — xem `core/don_dep_mo_rong.py`.
        4. ghi SỔ NGÀY DÙNG CHUNG cho cả máy (`.md` + `.json`, `workspace/tu-chay/`) — tổng hợp cả
           chi phí sản xuất lẫn byte đã giải phóng.

    CLI giữ một khoá chung toàn VPS trước khi vào đây. Khoá đó được dùng chung
    với agent Chrome nên nghiên cứu/sản xuất/FFmpeg và quét/đăng/chăm kênh phải
    xếp hàng, không còn hai khối nặng tranh RAM trên cùng máy.
    """
    ngay = hom_nay or _dt.date.today()
    ngay_str = ngay.isoformat()

    def log(dong: str) -> None:
        if on_log is not None:
            try:
                on_log(dong)
            except Exception:  # noqa: BLE001
                pass

    danh_sach = danh_sach_kenh if danh_sach_kenh is not None else kenh_tu_chay(goc)
    if not danh_sach:
        log("Không có kênh nào bật `tu_chay: true` trong kenh.yaml — không có gì để chạy.")
        rong = {"ket_qua": [], "co_loi": False, "danh_sach": [], "nhom_dong_bo": [],
               "tong_uoc_vnd": 0, "don_dep": {"theo_kenh": {}, "tong_bytes": 0}}
        ghi_bao_cao_tat_ca(goc, ngay_str, {
            "luc": _dt.datetime.now().isoformat(timespec="seconds"), "che_do": che_do,
            "ket_qua": [], "tong_uoc_vnd": 0, "nhom_dong_bo": [],
            "don_dep": {"theo_kenh": {}, "tong_bytes": 0}})
        return rong

    log("═══ ĐỒNG BỘ DỮ LIỆU NHÓM ({0} kênh) ═══".format(len(danh_sach)))
    nhom_dong_bo = dong_bo_nhom_truoc_khi_chay(
        goc, danh_sach, on_log=log, dong_bo_doi_thu_fn=dong_bo_doi_thu_fn,
        ghi_bang_nhom_fn=ghi_bang_nhom_fn)

    log("═══ CHẠY {0} KÊNH (chế độ {1}) ═══".format(len(danh_sach), che_do))
    bao_cao = chay_nhieu_kenh(goc, danh_sach, client=client, che_do=che_do,
                              chay_mot_ngay_fn=chay_mot_ngay_fn, on_log=log,
                              hom_nay=hom_nay, **kwargs)

    # Tổng ước chi hôm nay: đọc lại sổ CỦA TỪNG KÊNH (đã ghi bởi chay_mot_ngay
    # bên trong chay_nhieu_kenh) — chỉ cộng lượt THẬT SỰ đã sản xuất
    # (`san_xuat.da_chay`), "thu" không sản xuất nên luôn cộng ra 0.
    # Cùng lúc gom số liệu DỌN KHẨN (`_don_khan_ngay`, kích khi van đĩa trong
    # `chay_mot_ngay` chạm ngưỡng an toàn giữa lượt) — sổ ngày dùng chung phải
    # nói rõ đã dọn khẩn bao nhiêu, không chỉ dọn THƯỜNG cuối lượt bên dưới.
    tong_uoc_vnd = 0
    tong_don_khan_bytes = 0
    so_lan_don_khan = 0
    for ma in danh_sach:
        bc = _doc_bao_cao_ngay(goc, ma, ngay_str)
        for r in bc.get("runs") or []:
            if (r.get("san_xuat") or {}).get("da_chay"):
                tong_uoc_vnd += int((r.get("ngan_sach") or {}).get("uoc_tinh_vnd") or 0)
            don_khan_r = (r.get("dia") or {}).get("don_khan") or {}
            if don_khan_r.get("da_chay"):
                tong_don_khan_bytes += int(don_khan_r.get("da_giai_phong_bytes") or 0)
                so_lan_don_khan += 1

    # ── Dọn đĩa — SAU vòng sản xuất, TRƯỚC khi ghi sổ (để sổ có luôn số byte
    # đã giải phóng). Một kênh dọn hỏng (đĩa bận, quyền bị chặn…) chỉ được ghi
    # log rồi bỏ qua — không được chặn kênh khác, và càng không được chặn cả
    # việc ghi sổ ngày của lượt --tat-ca đang chạy thật.
    log("═══ DỌN ĐĨA ({0} kênh) ═══".format(len(danh_sach)))
    don_fn = don_theo_cai_dat_fn or don_dep.don_theo_cai_dat
    don_theo_kenh: Dict[str, int] = {}
    tong_don_bytes = 0
    # L4 (chẩn đoán 26/09/2026): gom LÝ DO THẬT của từng lượt đã xoá (từ
    # `da_don[].ly_do` — cùng nguồn sự thật với `don-dep.log`,
    # `core.don_dep._ghi_log`), để sổ ngày dùng chung không còn đoán bừa "video
    # đã đăng quá hạn ân xá" cho những lượt thực ra bị xoá vì luật "quá N lượt,
    # chưa đăng" (`don_dep.LY_DO_QUA_SO_LUOT`) — xem `_dung_md_tat_ca`.
    ly_do_don_thay: List[str] = []
    for ma in danh_sach:
        try:
            ket_don = don_fn(goc, ma)
        except Exception as loi:  # noqa: BLE001
            log("  {0}: dọn đĩa hỏng: {1} — bỏ qua, không chặn --tat-ca.".format(ma, str(loi)[:200]))
            continue
        so_byte = int((ket_don or {}).get("tong_bytes") or 0)
        don_theo_kenh[ma] = so_byte
        tong_don_bytes += so_byte
        for d in (ket_don or {}).get("da_don") or []:
            ly_do_thuc = str(d.get("ly_do") or "")
            if ly_do_thuc and ly_do_thuc not in ly_do_don_thay:
                ly_do_don_thay.append(ly_do_thuc)
        if (ket_don or {}).get("chay") and so_byte:
            log("  {0}: đã dọn, giải phóng {1}.".format(ma, _byte_nguoi_doc(so_byte)))

    # ── Dọn MỞ RỘNG — báo cáo ngày cũ + nhật ký dọn dẹp quá cỡ. CÙNG cờ
    # `tu_don` như trên (từng kênh tự đọc lại cờ của mình bên trong hàm), nên
    # gọi một lần cho CẢ danh sách là đủ, không cần vòng `try/except` riêng ở
    # đây — hàm đã tự bọc "một kênh hỏng không chặn kênh khác".
    don_mo_rong_call = don_mo_rong_fn or don_dep_mo_rong.don_tat_ca_theo_cai_dat
    try:
        ket_don_mo_rong = don_mo_rong_call(goc, danh_sach) or {}
    except Exception as loi:  # noqa: BLE001 — dọn mở rộng hỏng không được chặn --tat-ca
        log("  dọn mở rộng hỏng: {0} — bỏ qua, không chặn --tat-ca.".format(str(loi)[:200]))
        ket_don_mo_rong = {}
    if ket_don_mo_rong.get("tong_bytes"):
        log("  dọn mở rộng: giải phóng {0} (báo cáo ngày cũ, log dọn dẹp)."
           .format(_byte_nguoi_doc(ket_don_mo_rong["tong_bytes"])))

    # ── Sức khoẻ đĩa — ĐO, không đụng gì, luôn chạy dù `tu_don` tắt hết. Chủ
    # dự án đọc sổ ngày mỗi sáng và đây là chỗ DUY NHẤT thấy ngay đĩa còn bao
    # nhiêu mà không phải mở đĩa C: ra đếm tay.
    try:
        suc_khoe_dia = don_dep_mo_rong.suc_khoe_dia(goc, danh_sach)
    except Exception as loi:  # noqa: BLE001 — đo hỏng không được chặn --tat-ca
        log("  đo sức khoẻ đĩa hỏng: {0}".format(str(loi)[:200]))
        suc_khoe_dia = {}
    if suc_khoe_dia.get("canh_bao_dia"):
        log("  [ĐĨA] ⚠ còn {0:.1f} GB, dưới ngưỡng an toàn {1:.1f} GB."
           .format(suc_khoe_dia.get("dia_con_trong_gb") or 0.0,
                   suc_khoe_dia.get("nguong_canh_bao_gb") or 0.0))

    luot = {"luc": _dt.datetime.now().isoformat(timespec="seconds"), "che_do": che_do,
           "ket_qua": bao_cao["ket_qua"], "tong_uoc_vnd": tong_uoc_vnd,
           "nhom_dong_bo": nhom_dong_bo,
           "dia_con_trong_gb": _dung_luong_trong_gb(goc),
           "kho_loi_thoai": dem_kho_loi_thoai(goc, danh_sach, ngay_str),
           "don_dep": {"theo_kenh": don_theo_kenh, "tong_bytes": tong_don_bytes,
                      "ly_do": ly_do_don_thay},
           "don_khan": {"tong_bytes": tong_don_khan_bytes, "so_lan": so_lan_don_khan},
           "don_mo_rong": ket_don_mo_rong,
           "suc_khoe_dia": suc_khoe_dia}
    duong_md, duong_json = ghi_bao_cao_tat_ca(goc, ngay_str, luot)
    log("Đã ghi sổ ngày dùng chung: {0}".format(duong_md))

    bao_cao["danh_sach"] = danh_sach
    bao_cao["nhom_dong_bo"] = nhom_dong_bo
    bao_cao["tong_uoc_vnd"] = tong_uoc_vnd
    bao_cao["don_dep"] = luot["don_dep"]
    bao_cao["don_mo_rong"] = luot["don_mo_rong"]
    bao_cao["suc_khoe_dia"] = luot["suc_khoe_dia"]
    bao_cao["duong_bao_cao_md"] = duong_md
    bao_cao["duong_bao_cao_json"] = duong_json
    return bao_cao
