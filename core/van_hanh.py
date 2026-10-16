"""core/van_hanh.py — VẬN HÀNH: bật máy lên là mọi thứ tự chạy, chết thì tự hồi phục (16/10/2026).

Chủ: *"mọi thứ nên có logic auto mọi thứ bật máy lên là all sẽ hoạt động — dài hạn ổn định không cần tác động"*.
VPS khởi động lại 12:31 ngày 16/10: giao diện Qt (Startup → `CHAY-GON.vbs`), agent `vm/agent.py` (giao diện nuôi
qua `core.giam_sat_vm`), trạm 8765 (`ShopAPI-TramLucDangNhap` + `ShopAPI-CanhTram`) và các lịch `ShopAPI-*` tự lên —
riêng trung tâm trực quan 8790 (`python -m core.truc_quan`, phục vụ cả LAN cho shopapi.vn) KHÔNG ai bật, không ai canh.

═══ MỘT SỔ ĐĂNG KÝ THÀNH PHẦN (`so_dang_ky`) ═══

Mỗi thành phần chạy dài khai: câu hỏi sức khoẻ (cổng trả lời / nhịp tim tươi / tiến trình đúng dòng lệnh), lệnh bật
IDEMPOTENT (bật thừa cũng không chạy đôi: trạm tự nhường cổng, agent giữ khoá 8767, trực quan bind hỏng thì thoát),
lùi dần giữa các lần bật hỏng (`ben_bi.cho_lui_dan`), và TRẦN: hỏng `TRAN_LAN_HONG` lần liền thì thôi bật — mỗi ngày
thử lại đúng MỘT lần — và báo động MỘT lần/ngày (`core.bao_dong` + `workspace/loi-chay-max.md` + não `suc-khoe-may`).

Luật cứng:
  * CHỈ bật thành phần ĐANG CHẾT. Thành phần khoẻ không bao giờ bị "làm tươi"; module này không giết tiến trình nào.
  * Thành phần `ne_ban` (giao diện, agent) HOÃN khi máy đang tải lên hay đang giữ khe dựng/phụ đề/quét
    (`.khoa-may`, `vm/logs/dang-dodang.json` — cùng cách đọc với `an_toan_khoi_dong`, `thiet_lap_kenh_dom`).
    Giao diện còn hoãn khi việc nền cũ của nó còn sống (mở giao diện mới là `tien_trinh_con.don_xac_cu` giết chúng).
  * Cổng còn bị giữ mà câm (trạm đáp gói dò nhưng câm HTTP, 8790 nhận kết nối mà không trả lời) = `ket`: KHÔNG bật
    bản thứ hai (bind sẽ hỏng), chỉ báo.
  * Cơ chế khởi động SẴN CÓ được ưu tiên: sau khi máy lên, giao diện/agent/trạm có quãng ân hạn để Startup + lịch
    sẵn có tự làm; chỉ thứ không ai bật (trực quan 8790) mới được bật ngay. Sổ `workspace/gac-tong/hoi-sinh.json`
    dùng CHUNG với `ben_bi.hoi_sinh_may_nen` — hai người canh không cùng mở đôi giao diện.

═══ NHỊP ═══ Task Scheduler (`core.lich_tu_chay.dang_ky_van_hanh`): `ShopAPI-VanHanh` mỗi 5 phút +
`ShopAPI-VanHanhLucDangNhap` lúc đăng nhập (trễ 1 phút), chạy `pythonw van_hanh.py mot-luot` bằng người dùng ĐÃ ĐĂNG
NHẬP (không /RU, không lưu mật khẩu — cùng nếp `ShopAPI-GacTong`). Vòng lặp bền nhất là vòng ta không tự viết.

═══ LƯỢT ĐẦU SAU KHỞI ĐỘNG ═══ So `luc_khoi_dong()` (GetTickCount64) với mốc đã ghi; khác → `don_khoa_khoi_dong`
(khoá ghi TRƯỚC lúc máy lên = chủ đã chết theo lần khởi động, dù PID nay bị tiến trình khác dùng lại), rồi khi mọi
thành phần lên (hoặc quá `BAO_SAU_GIAY`) ghi MỘT dòng "khởi động hh:mm — X/Y thành phần chạy, đã dọn N khoá cũ"
vào nhật ký + não bộ phận + trang trực quan. Lượt sản xuất dở tự chạy tiếp nhờ `ShopAPI-DieuPhoi`/`ShopAPI-TuChay`
(`tu_chay._tim_run_chua_xong`; khâu `dang` đọc lại thành `hong` trong `auto.doc_luot`) — module này chỉ gỡ khoá
cũ chặn đường đó (khoá kênh `CHANNEL/<k>/tu-chay/.khoa` trỏ PID bị dùng lại thì `dieu_phoi._khoa_kenh_song` tưởng
kênh "đang chạy" mãi).

    python van_hanh.py mot-luot [--thu]    một lượt canh (--thu: CHỈ ĐỌC, in việc sẽ làm)
    python van_hanh.py don-khoa [--thu]    dọn khoá cũ theo luật khởi động (không cần đợi lần khởi động)
    python van_hanh.py dang-ky             đăng ký 2 tác vụ Windows (chạy từ thư mục tool chính, không từ worktree)
    python van_hanh.py huy | trang-thai
"""

from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import khe

__all__ = ["SONG", "CHET", "KET", "ThanhPhan", "so_dang_ky", "luc_khoi_dong", "ly_do_ban", "don_khoa_khoi_dong",
           "mot_luot", "cau_khoi_dong", "duong_trang_thai", "duong_khoi_dong", "main"]

GOC_TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SONG, CHET, KET = "song", "chet", "ket"
TAT, KHONG_CO = "tat", "khong_co"

#: Hỏng ngần này lần bật liền → thôi bật (mỗi ngày thử lại 1 lần), báo động 1 lần/ngày.
TRAN_LAN_HONG = 5
LUI_CO_SO_GIAY, LUI_TRAN_GIAY = 60.0, 1800.0
THU_LAI_SAU_TRAN_GIAY = 24 * 3600.0
#: Báo cáo khởi động: khi mọi thành phần lên, hoặc chậm nhất ngần này giây sau lúc máy lên.
BAO_SAU_GIAY = 15 * 60.0
#: Hai mốc khởi động lệch quá ngần này = một lần khởi động MỚI (GetTickCount64 trôi vài giây giữa các lượt).
LECH_KHOI_DONG_GIAY = 120.0
#: Khoá ghi SAU lúc máy lên mà PID chết: phải già ngần này mới dọn (cùng `ben_bi.TUOI_KHOA_CHET_TOI_THIEU_GIAY`).
TUOI_KHOA_CHET_GIAY = 600.0
#: Hạn cứng một lượt (lịch `IgnoreNew`: một lượt treo là mọi lượt sau bị bỏ qua).
HAN_LUOT_GIAY = 8 * 60.0
#: Sổ hồi sinh chung với gác tổng: bên kia vừa mở giao diện/agent trong ngần này giây thì bên này không mở đôi.
NE_HOI_SINH_GIAY = 10 * 60.0
CONG_TRAM, CONG_TRUC_QUAN, CONG_AGENT = 8765, 8790, 8767
#: Việc trên khe "nang" mà ngắt ngang là hỏng thật (tải lên/quét: trình duyệt kênh; dựng/phụ đề: FFmpeg/Whisper).
VIEC_BAN = {"tai_len": "đang tải video lên", "quet": "đang quét Studio", "dung": "đang dựng video",
            "phu_de": "đang làm phụ đề", "thiet_lap": "đang thiết lập kênh", "studio_may": "đang làm việc Studio"}

#: Khoá có luật `{pid, mốc}` mà một lần khởi động máy bỏ lại. `{vm}` = thư mục vm của máy (`che_do_vps`).
MAU_KHOA = (
    ("workspace/tu-chay/.khoa-may", "khe máy nặng (.khoa-may)"),
    ("workspace/khe/api-*.json", "làn API"),
    ("workspace/khe/cho/*.json", "vé chờ khe"),
    ("workspace/khe/job/*/*.json", "suất job"),
    ("workspace/khe/dieu-phoi.lock", "nhịp điều phối"),
    ("workspace/tu-chay/cho-clip/*.json", "dấu chờ kho clip"),
    ("CHANNEL/*/tu-chay/.khoa", "khoá kênh tự chạy"),
    ("{vm}/logs/nuoi-trang-chu/*.khoa", "khoá Chrome kênh (nuôi trang chủ)"),
    ("{vm}/logs/thiet-lap-kenh/*.khoa", "khoá Chrome kênh (thiết lập)"),
    ("{vm}/logs/dang-dodang.json", "dấu đang đăng dở"),
    ("logs/dang-dodang.json", "dấu đang đăng dở"),
    ("nao/.khoa-phien", "phiên bộ não"),
)

KiemFn = Callable[[str], Tuple[str, str]]
BatFn = Callable[[str], Tuple[bool, str]]


@dataclass
class ThanhPhan:
    """Một thành phần chạy dài. `kiem(goc) -> (song|chet|ket, câu)`; `bat(goc) -> (sinh được chưa, câu)`."""
    ma: str
    ten: str
    kiem: KiemFn
    bat: BatFn
    cach_bat: str = ""                  # cơ chế bật sẵn có (để báo cáo)
    co_mat: Optional[Callable[[str], bool]] = None    # máy này có thành phần này không
    cho_len_giay: float = 30.0          # bật xong chờ nó lên tiếng tối đa
    an_han_khoi_dong_giay: float = 0.0  # sau khi máy lên: để cơ chế sẵn có tự bật trước
    so_luot_xuong_toi_thieu: int = 1    # chết liền ngần này lượt mới bật (cho người nuôi chính kịp tự bật)
    ne_ban: bool = False                # hoãn khi máy đang tải lên / đang giữ khe dựng–phụ đề
    dieu_kien: Optional[Callable[[str, Dict[str, Any]], str]] = None   # '' = được bật; câu = lý do hoãn


# ── đường dẫn + đĩa ──────────────────────────────────────────────────────────────────────────────────────────────


def duong_thu_muc(goc: str) -> str:
    return os.path.join(goc, "workspace", "van-hanh")


def duong_trang_thai(goc: str) -> str:
    return os.path.join(duong_thu_muc(goc), "trang-thai.json")


def duong_khoi_dong(goc: str) -> str:
    return os.path.join(duong_thu_muc(goc), "khoi-dong.json")


def duong_log(goc: str) -> str:
    return os.path.join(duong_thu_muc(goc), "van-hanh.log")


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = "{0}.{1}.tam".format(duong, os.getpid())
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def _ghi_log(goc: str, dong: str, luc: Optional[float] = None) -> None:
    duong = duong_log(goc)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        if os.path.isfile(duong) and os.path.getsize(duong) > 1_000_000:      # giữ nửa sau, không phình mãi
            with open(duong, "rb") as tep:
                tep.seek(-500_000, os.SEEK_END)
                giu = tep.read()
            with open(duong, "wb") as tep:
                tep.write(giu[giu.find(b"\n") + 1:])
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write("[{0}] {1}\n".format(_dt.datetime.fromtimestamp(luc or time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                                           dong))
    except OSError:
        pass


def doc_cai_dat(goc: str) -> Dict[str, Any]:
    """`workspace/van-hanh/cai-dat.json` — `{"tat": ["giao_dien", ...]}` tắt canh thành phần nào trên máy này."""
    du = _doc_json(os.path.join(duong_thu_muc(goc), "cai-dat.json"))
    return du if isinstance(du, dict) else {}


def thu_muc_vm(goc: str) -> str:
    try:
        from . import che_do_vps  # noqa: PLC0415
        d = che_do_vps.thu_muc_vm(goc)
        if d:
            return str(d)
    except Exception:  # noqa: BLE001 — không ở chế độ VPS / thiếu vps.json
        pass
    return os.path.join(goc, "vm")


def luc_khoi_dong() -> float:
    """Epoch lúc máy khởi động (GetTickCount64 — đếm cả lúc ngủ, VPS không ngủ). 0 = không đo được."""
    try:
        import ctypes  # noqa: PLC0415
        f = ctypes.windll.kernel32.GetTickCount64
        f.restype = ctypes.c_ulonglong
        return time.time() - f() / 1000.0
    except Exception:  # noqa: BLE001
        pass
    try:
        with open("/proc/uptime", "r", encoding="ascii") as tep:
            return time.time() - float(tep.read().split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def _hhmm(luc: float) -> str:
    return _dt.datetime.fromtimestamp(luc).strftime("%H:%M") if luc else "?"


def _pid(du: Any) -> int:
    try:
        return int((du or {}).get("pid") or 0) if isinstance(du, dict) else 0
    except (TypeError, ValueError):
        return 0


def _moc(duong: str, du: Any) -> float:
    """Dấu sống MUỘN NHẤT của một khoá: trường thời gian trong tệp và giờ sửa tệp (khoá được làm tươi sau lúc máy lên
    thì chủ của nó chắc chắn sống sau lần khởi động — không bao giờ coi là khoá cũ)."""
    cac: List[float] = []
    if isinstance(du, dict):
        for k in ("bat_dau", "luc", "luc_xin", "tao_luc", "tu_luc"):
            try:
                if du.get(k) is not None:
                    cac.append(float(du.get(k)))
            except (TypeError, ValueError):
                pass
        if du.get("luc_bat_dau"):
            try:
                cac.append(_dt.datetime.strptime(str(du["luc_bat_dau"])[:19], "%Y-%m-%d %H:%M:%S").timestamp())
            except ValueError:
                pass
    try:
        cac.append(os.path.getmtime(duong))
    except OSError:
        pass
    return max(cac) if cac else 0.0


# ── kiểm sức khoẻ + lệnh bật ────────────────────────────────────────────────────────────────────────────────────


def _cong_nghe(cong: int, cho: float = 2.0) -> bool:
    for may in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((may, cong), timeout=cho):
                return True
        except OSError:
            continue
    return False


def _http_dap(cong: int, duong: str = "/", cho: float = 6.0) -> bool:
    """Có máy chủ HTTP trả lời (mã gì cũng được) — 127.0.0.1 rồi ::1 (trực quan nghe '::' hai ngăn xếp)."""
    import http.client  # noqa: PLC0415
    for may in ("127.0.0.1", "::1"):
        c = http.client.HTTPConnection(may, cong, timeout=cho)
        try:
            c.request("GET", duong)
            c.getresponse().read(64)
            return True
        except (OSError, http.client.HTTPException):
            continue
        finally:
            c.close()
    return False


def _sinh_tach(lenh: List[str], cwd: str, duong_log_con: str = "") -> int:
    """Sinh tiến trình SỐNG LÂU HƠN lượt canh: tách job (breakaway, lùi về không tách nếu job cấm), nhóm mới, không
    cửa sổ, không giữ tay cầm của cha. Trả PID (0 = hỏng)."""
    from .tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415
    co = 0
    for ten in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"):
        co |= getattr(subprocess, ten, 0)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    tep = None
    try:
        if duong_log_con:
            os.makedirs(os.path.dirname(duong_log_con), exist_ok=True)
            tep = open(duong_log_con, "a", encoding="utf-8", errors="replace")  # noqa: SIM115
        for co_thu in dict.fromkeys((co | CO_TACH_KHOI_JOB, co)):
            try:
                p = subprocess.Popen(lenh, cwd=cwd, stdin=subprocess.DEVNULL,  # noqa: S603 — lệnh do tool dựng
                                     stdout=tep or subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT if tep else subprocess.DEVNULL,
                                     env=env, creationflags=co_thu, close_fds=True)
                return int(p.pid or 0)
            except OSError:
                continue
        return 0
    except OSError:
        return 0
    finally:
        if tep is not None:
            tep.close()


def _pythonw(goc: str) -> str:
    from .loi_tat import _pythonw_cho  # noqa: PLC0415 — cùng cách dò Python thật với lich_tu_chay/canh_tram
    return _pythonw_cho(goc)


def lenh_truc_quan(goc: str) -> List[str]:
    """Đúng lệnh bật tay `python -X utf8 -m core.truc_quan` (bản pythonw, không cửa sổ). KHÔNG truyền `--lan`/`--cong`:
    chính `core.truc_quan.dia_chi_nghe` đọc `workspace/truc-quan/cai-dat.json` (mở LAN = nghe '::' hai ngăn xếp)."""
    return [_pythonw(goc), "-X", "utf8", "-m", "core.truc_quan"]


def kiem_truc_quan(goc: str) -> Tuple[str, str]:
    if _http_dap(CONG_TRUC_QUAN, "/vendor/__song__"):
        return SONG, "cổng {0} trả lời".format(CONG_TRUC_QUAN)
    if _cong_nghe(CONG_TRUC_QUAN):
        return KET, "cổng {0} nhận kết nối nhưng không trả lời HTTP — không bật bản thứ hai".format(CONG_TRUC_QUAN)
    return CHET, "cổng {0} không ai trả lời".format(CONG_TRUC_QUAN)


def bat_truc_quan(goc: str) -> Tuple[bool, str]:
    pid = _sinh_tach(lenh_truc_quan(goc), goc, os.path.join(goc, "workspace", "truc-quan", "may-chu.log"))
    return (bool(pid), "đã bật trung tâm trực quan (PID {0})".format(pid) if pid else "không sinh được tiến trình")


def kiem_tram(goc: str) -> Tuple[str, str]:
    from . import tram_nen  # noqa: PLC0415
    cong = tram_nen.tim_tram_dang_song(CONG_TRAM)
    if cong is None:
        return CHET, "không ai trả lời cổng {0} (và các cổng lùi)".format(CONG_TRAM)
    if tram_nen.dap_http(cong):
        return SONG, "trạm trả lời ở cổng {0}".format(cong)
    return KET, "cổng {0} đáp gói dò nhưng câm HTTP — không bật thêm (cổng vẫn bị giữ)".format(cong)


def bat_tram(goc: str) -> Tuple[bool, str]:
    from . import canh_tram  # noqa: PLC0415
    return canh_tram.bat_tram_nen(goc)


def kiem_agent(goc: str) -> Tuple[str, str]:
    if _cong_nghe(CONG_AGENT):
        return SONG, "agent giữ khoá một-mình cổng {0}".format(CONG_AGENT)
    nhip = _doc_json(os.path.join(thu_muc_vm(goc), "logs", "nhip-tim.json"))
    try:
        tuoi = time.time() - float((nhip or {}).get("luc") or 0)
    except (TypeError, ValueError, AttributeError):
        tuoi = 1e9
    if tuoi < 300 and khe.pid_con_song(_pid(nhip)):
        return SONG, "nhịp tim {0:.0f} giây trước".format(tuoi)
    return CHET, "cổng {0} trống, nhịp tim {1}".format(
        CONG_AGENT, "{0:.0f} phút trước".format(tuoi / 60) if tuoi < 1e8 else "không có")


def bat_agent(goc: str) -> Tuple[bool, str]:
    from . import ben_bi  # noqa: PLC0415
    ok = ben_bi._mo_agent_mac_dinh(thu_muc_vm(goc))  # noqa: SLF001 — đúng dòng lệnh core.giam_sat_vm._mo_that
    if ok:
        _ghi_so_hoi_sinh(goc, "luc_mo_agent")
    return ok, "đã mở agent vm" if ok else "không mở được agent vm"


def kiem_giao_dien(goc: str) -> Tuple[str, str]:
    from . import dong_bo_git as dbg  # noqa: PLC0415
    ds = dbg._tien_trinh_python()  # noqa: SLF001
    if not ds:      # chính lượt canh này là một tiến trình python — rỗng = KHÔNG liệt kê được, không bật mù
        return KET, "không liệt kê được tiến trình — không bật mù (tránh mở đôi giao diện)"
    pid = dbg._tim(ds, goc, dbg.TEP_GIAO_DIEN)  # noqa: SLF001
    if pid:
        return SONG, "PID {0}".format(", ".join(str(p) for p in pid))
    return CHET, "không có tiến trình {0}".format(dbg.TEP_GIAO_DIEN)


def bat_giao_dien(goc: str) -> Tuple[bool, str]:
    vbs = os.path.join(goc, "CHAY-GON.vbs")
    if not os.path.isfile(vbs):
        return False, "không thấy CHAY-GON.vbs"
    pid = _sinh_tach(["wscript.exe", vbs], goc)
    if pid:
        _ghi_so_hoi_sinh(goc, "luc_mo_gd")
    return bool(pid), "đã mở giao diện qua CHAY-GON.vbs" if pid else "không mở được CHAY-GON.vbs"


# ── luật hoãn ───────────────────────────────────────────────────────────────────────────────────────────────────


def _duong_so_hoi_sinh(goc: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "hoi-sinh.json")   # = ben_bi._duong_hoi_sinh


def _ghi_so_hoi_sinh(goc: str, khoa: str) -> None:
    so = _doc_json(_duong_so_hoi_sinh(goc))
    so = so if isinstance(so, dict) else {}
    so[khoa] = time.time()
    _ghi_json(_duong_so_hoi_sinh(goc), so)


def _vua_hoi_sinh(goc: str, khoa: str) -> str:
    so = _doc_json(_duong_so_hoi_sinh(goc))
    try:
        luc = float((so or {}).get(khoa) or 0)
    except (TypeError, ValueError, AttributeError):
        luc = 0.0
    if luc and time.time() - luc < NE_HOI_SINH_GIAY:
        return "vừa có người mở lúc {0} (sổ hồi sinh chung) — chờ nó lên".format(_hhmm(luc))
    return ""


def _dang_cap_nhat(goc: str) -> str:
    try:
        from . import cap_nhat_git  # noqa: PLC0415
        return "đang có lượt cập nhật — nó tự khởi động lại mọi thứ" if cap_nhat_git.dang_cap_nhat(goc) else ""
    except Exception:  # noqa: BLE001
        return ""


def ly_do_ban(goc: str, *, luc_boot: float = 0.0, pid_con_song: Optional[Callable[[int], bool]] = None) -> str:
    """'' nếu máy rảnh; câu lý do nếu đang tải lên (`dang-dodang.json`) hay khe "nang" (`.khoa-may`) đang giữ việc ngắt
    ngang là hỏng (VIEC_BAN, hoặc khoá kiểu cũ cả lượt). Dấu ghi TRƯỚC lúc máy lên không tính (chủ đã chết)."""
    song = pid_con_song or khe.pid_con_song
    vm = thu_muc_vm(goc)
    for d in (os.path.join(vm, "logs", "dang-dodang.json"), os.path.join(goc, "logs", "dang-dodang.json")):
        if not os.path.isfile(d):
            continue
        du = _doc_json(d)
        if luc_boot and _moc(d, du) < luc_boot - 2:
            continue
        pid = _pid(du)
        if not pid or song(pid):
            nhan = " ".join(str((du or {}).get(k) or "") for k in ("kenh", "ma")).strip() if isinstance(du, dict) else ""
            return "máy đăng đang tải dở {0} (dang-dodang.json)".format(nhan or "một video")
    d = khe.duong_khoa_nang(goc)
    du = _doc_json(d)
    if isinstance(du, dict) and not (luc_boot and _moc(d, du) < luc_boot - 2):
        pid = _pid(du)
        if pid and song(pid):
            viec = str(du.get("viec") or "")
            if not viec or viec in VIEC_BAN:
                return "khe máy nặng (.khoa-may) đang {0} (PID {1})".format(
                    VIEC_BAN.get(viec, "giữ một lượt sản xuất kiểu cũ").replace("đang ", ""), pid)
    return ""


def _dk_giao_dien(goc: str, kq: Dict[str, Any]) -> str:
    r = _dang_cap_nhat(goc) or _vua_hoi_sinh(goc, "luc_mo_gd")
    if r:
        return r
    try:
        from . import an_toan_khoi_dong  # noqa: PLC0415
        r = " ".join(an_toan_khoi_dong._kiem_tien_trinh_con(goc))  # noqa: SLF001 — giao diện mới giết việc nền cũ
    except Exception:  # noqa: BLE001
        r = ""
    return r


def _dk_tram(goc: str, kq: Dict[str, Any]) -> str:
    if (kq.get("giao_dien") or {}).get("hanh_dong") in ("da_bat", "bat_hong", "se_bat"):
        return "giao diện vừa được mở — nó tự mở trạm 8765"
    return _dang_cap_nhat(goc)


def _dk_agent(goc: str, kq: Dict[str, Any]) -> str:
    gd = kq.get("giao_dien") or {}
    if gd.get("hanh_dong") in ("da_bat", "bat_hong", "se_bat"):
        return "giao diện vừa được mở — nó tự nuôi agent (core.giam_sat_vm)"
    if gd.get("trang_thai") == CHET and int(gd.get("lan_hong") or 0) < 2:
        return "giao diện chưa chạy — mở giao diện trước, nó tự nuôi agent"
    return _dang_cap_nhat(goc) or _vua_hoi_sinh(goc, "luc_mo_agent")


def _co_tep(*phan: str) -> Callable[[str], bool]:
    return lambda goc: all(os.path.isfile(os.path.join(goc, p)) for p in phan)


def so_dang_ky(goc: str) -> List[ThanhPhan]:
    """SỔ ĐĂNG KÝ — thứ tự có nghĩa: giao diện trước (nó mở trạm + nuôi agent), agent xét SAU giao diện."""
    vm = thu_muc_vm(goc)
    return [
        ThanhPhan("giao_dien", "Giao diện MyTool (Qt)", kiem_giao_dien, bat_giao_dien,
                  cach_bat="Startup: MyTool VPS.lnk → CHAY-GON.vbs; gác tổng (ben_bi.hoi_sinh_may_nen)",
                  co_mat=_co_tep("CHAY-GON.vbs", "shopapi_studio_qt.py"), cho_len_giay=20.0,
                  an_han_khoi_dong_giay=600.0, ne_ban=True, dieu_kien=_dk_giao_dien),
        ThanhPhan("tram_8765", "Trạm nhận 8765", kiem_tram, bat_tram,
                  cach_bat="giao diện Qt; ShopAPI-TramLucDangNhap (lúc khởi động) + ShopAPI-CanhTram (5 phút)",
                  co_mat=_co_tep("tram_nen.py"), cho_len_giay=20.0, an_han_khoi_dong_giay=240.0,
                  dieu_kien=_dk_tram),
        ThanhPhan("agent_vm", "Agent máy đăng (vm/agent.py)", kiem_agent, bat_agent,
                  cach_bat="giao diện Qt nuôi (core.giam_sat_vm); gác tổng (ben_bi.hoi_sinh_may_nen)",
                  co_mat=lambda g: os.path.isfile(os.path.join(vm, "agent.py"))
                  and os.path.isfile(os.path.join(vm, "config.json")),
                  cho_len_giay=40.0, an_han_khoi_dong_giay=600.0, so_luot_xuong_toi_thieu=2, ne_ban=True,
                  dieu_kien=_dk_agent),
        ThanhPhan("truc_quan_8790", "Trung tâm trực quan 8790", kiem_truc_quan, bat_truc_quan,
                  cach_bat="(trước 16/10: không ai — bật tay) → chính module này",
                  co_mat=_co_tep(os.path.join("core", "truc_quan.py")), cho_len_giay=20.0),
    ]


# ── dọn khoá cũ sau khởi động ───────────────────────────────────────────────────────────────────────────────────


def _cac_khoa(goc: str) -> List[Tuple[str, str]]:
    vm = thu_muc_vm(goc)
    ra: List[Tuple[str, str]] = []
    thay = set()
    for mau, nhan in MAU_KHOA:
        mau = mau.replace("{vm}", vm.replace("\\", "/"))
        duong_mau = mau if os.path.isabs(mau) else os.path.join(goc, mau)
        for d in sorted(glob.glob(duong_mau)):
            k = os.path.normcase(os.path.abspath(d))
            if k not in thay and os.path.isfile(d):
                thay.add(k)
                ra.append((d, nhan))
    return ra


def don_khoa_khoi_dong(goc: str, luc_boot: float, *, bay_gio: Optional[float] = None, thu: bool = False,
                       pid_con_song: Optional[Callable[[int], bool]] = None) -> List[Dict[str, Any]]:
    """Dọn khoá `{pid, mốc}` máy khởi động bỏ lại — THEO ĐÚNG LUẬT CỦA KHOÁ: chỉ xoá khi chủ chắc chắn đã chết.

    * Dấu sống muộn nhất (`_moc`) TRƯỚC lúc máy lên → chủ chết theo lần khởi động (PID nay có thể đã bị tiến trình
      khác dùng lại — đúng ca `pid_con_song` trả nhầm "sống") → xoá.
    * Sau lúc máy lên mà PID chết và khoá đã ≥ `TUOI_KHOA_CHET_GIAY` → xoá (cùng luật `ben_bi.don_khoa_chet_an_toan`).
    * Còn lại (PID sống sau khởi động, khoá mới, tệp không phải JSON có `pid`) → GIỮ.
    Xoá qua `ben_bi.don_khoa_chet_an_toan` (đổi tên nguyên tử rồi đọc lại — lỡ cuỗm khoá người vừa giành thì trả lại).
    `thu=True`: chỉ báo, không xoá. Trả `[{duong, nhan, pid, xoa, ly_do}]`."""
    from . import ben_bi  # noqa: PLC0415
    song = pid_con_song or khe.pid_con_song
    luc = time.time() if bay_gio is None else float(bay_gio)
    ra: List[Dict[str, Any]] = []
    for d, nhan in _cac_khoa(goc):
        du = _doc_json(d)
        pid = _pid(du)
        try:
            ten = os.path.relpath(d, goc).replace("\\", "/")
        except ValueError:      # khác ổ đĩa
            ten = d
        muc = {"duong": d if ten.startswith("..") else ten, "nhan": nhan, "pid": pid, "xoa": False, "ly_do": ""}
        ra.append(muc)
        if not isinstance(du, dict) or not pid:
            muc["ly_do"] = "không có PID trong tệp — không rõ luật, để nguyên"
            continue
        moc = _moc(d, du)
        truoc_boot = bool(luc_boot) and moc < luc_boot - 2
        if truoc_boot:
            muc["ly_do"] = "ghi lúc {0}, trước khi máy lên {1} — chủ đã chết theo lần khởi động".format(
                _dt.datetime.fromtimestamp(moc).strftime("%d/%m %H:%M"), _hhmm(luc_boot))
            kiem_song: Callable[[int], bool] = lambda _p: False   # noqa: E731
            tuoi_toi_thieu = 0.0
        else:
            try:
                con = song(pid)
            except Exception:  # noqa: BLE001 — không chắc thì coi như còn sống
                con = True
            if con:
                muc["ly_do"] = "PID {0} còn sống (ghi sau khi máy lên) — giữ".format(pid)
                continue
            if luc - moc < TUOI_KHOA_CHET_GIAY:
                muc["ly_do"] = "PID {0} chết nhưng khoá mới {1:.0f} giây — để chủ/khe tự giành".format(pid, luc - moc)
                continue
            muc["ly_do"] = "PID {0} đã chết, khoá {1:.0f} phút".format(pid, (luc - moc) / 60.0)
            kiem_song, tuoi_toi_thieu = song, TUOI_KHOA_CHET_GIAY
        if thu:
            muc["xoa"] = None      # sẽ xoá
            continue
        ok, vi_sao = ben_bi.don_khoa_chet_an_toan(d, pid_thay=pid, bay_gio=luc, tuoi_toi_thieu_giay=tuoi_toi_thieu,
                                                  pid_con_song=kiem_song)
        muc["xoa"] = bool(ok)
        if not ok:
            muc["ly_do"] += " — KHÔNG xoá: " + vi_sao
    return ra


# ── một lượt canh ───────────────────────────────────────────────────────────────────────────────────────────────


def _kiem_an_toan(c: ThanhPhan, goc: str) -> Tuple[str, str]:
    try:
        tt, cau = c.kiem(goc)
        return (tt if tt in (SONG, CHET, KET) else KET), str(cau or "")
    except Exception as loi:  # noqa: BLE001 — hỏi hỏng thì KHÔNG bật mù
        return KET, "không kiểm được ({0}: {1})".format(type(loi).__name__, str(loi)[:120])


def _bao_tran(goc: str, c: ThanhPhan, st: Dict[str, Any], ly_do: str, luc: float, thu: bool,
              gui_bao: Optional[Callable[..., Any]], ghi_nao: Optional[Callable[..., Any]]) -> str:
    """Báo động MỘT lần/ngày cho thành phần chạm trần. Trả 'da_bao' | 'se_bao' | ''."""
    ngay = _dt.datetime.fromtimestamp(luc).strftime("%Y-%m-%d")
    if st.get("bao_ngay") == ngay:
        return ""
    if thu:
        return "se_bao"
    if int(st.get("lan_hong") or 0):
        chuyen = "{0} chết, máy tự bật lại {1} lần không lên ({2}).".format(c.ten, st.get("lan_hong"), ly_do[:160])
    else:
        chuyen = "{0} kẹt {1} lượt kiểm liền — không bật bản thứ hai vì cổng còn bị giữ ({2}).".format(
            c.ten, st.get("lan_xuong"), ly_do[:160])
    can = "Mở máy xem workspace/van-hanh/van-hanh.log; bật tay: {0}.".format(c.cach_bat or c.ma)
    neu = "Thành phần này đứng tới khi có người bật; máy chỉ tự thử lại mỗi ngày một lần."
    try:
        if gui_bao is None:
            from . import bao_dong  # noqa: PLC0415
            gui_bao = bao_dong.bao_dong_khan
        gui_bao("van_hanh:" + c.ma, chuyen, can, neu, goc=goc, bay_gio=luc)
    except Exception:  # noqa: BLE001 — báo động tự nuốt lỗi mạng; không được làm sập lượt canh
        pass
    try:
        from . import ben_bi  # noqa: PLC0415
        ben_bi._ghi_dong_loi_chay_max(goc, _dt.datetime.fromtimestamp(luc), "khan", chuyen + " " + can)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        pass
    _nao(goc, "loi", chuyen, {"ma": c.ma, "lan_hong": st.get("lan_hong")}, "van-hanh|tran|{0}|{1}".format(c.ma, ngay),
         ghi_nao)
    st["bao_ngay"] = ngay
    return "da_bao"


def _nao(goc: str, loai: str, noi_dung: str, so: Dict[str, Any], khoa: str,
         ghi_nao: Optional[Callable[..., Any]] = None) -> None:
    try:
        if ghi_nao is None:
            from .nao_bo_phan import ghi as ghi_nao  # noqa: PLC0415
        ghi_nao(goc, "suc-khoe-may", loai, noi_dung=noi_dung, so=so, nguon="van-hanh", khoa=khoa)
    except Exception:  # noqa: BLE001 — não hỏng không làm hỏng vận hành
        pass


def _xu_ly(goc: str, c: ThanhPhan, st: Dict[str, Any], kq: Dict[str, Any], luc: float, boot: float, ban: str,
           thu: bool, ngu: Callable[[float], None], gui_bao: Optional[Callable[..., Any]],
           ghi_nao: Optional[Callable[..., Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    st = dict(st)
    tt, ly_do = _kiem_an_toan(c, goc)
    ra: Dict[str, Any] = {"ma": c.ma, "ten": c.ten, "trang_thai": tt, "ly_do": ly_do, "hanh_dong": "",
                          "cach_bat": c.cach_bat}
    if tt == SONG:
        if st.get("lan_hong") or st.get("lan_xuong"):
            ra["hoi_phuc"] = True
        st.update(lan_hong=0, lan_xuong=0)
        ra["hanh_dong"] = "khoe"
        ra["lan_hong"] = 0
        return ra, st
    st["lan_xuong"] = int(st.get("lan_xuong") or 0) + 1
    n = int(st.get("lan_hong") or 0)
    ra["lan_hong"] = n
    if tt == KET:
        ra["hanh_dong"] = "ket"
        if st["lan_xuong"] >= TRAN_LAN_HONG:
            ra["bao"] = _bao_tran(goc, c, st, ly_do, luc, thu, gui_bao, ghi_nao)
        return ra, st
    con_an_han = c.an_han_khoi_dong_giay - (luc - boot) if boot else 0.0
    r = ""
    if con_an_han > 0:
        ra["hanh_dong"], r = "cho_khoi_dong", "máy mới lên — chờ cơ chế sẵn có ({0}) thêm {1:.0f} giây".format(
            c.cach_bat, con_an_han)
    elif st["lan_xuong"] < c.so_luot_xuong_toi_thieu:
        ra["hanh_dong"], r = "cho_xac_nhan", "chết lượt {0}/{1} — chờ người nuôi chính tự bật".format(
            st["lan_xuong"], c.so_luot_xuong_toi_thieu)
    else:
        r = c.dieu_kien(goc, kq) if c.dieu_kien else ""
        if r:
            ra["hanh_dong"] = "cho_phu_thuoc"
        elif c.ne_ban and ban:
            ra["hanh_dong"], r = "hoan_ban", ban
    if ra["hanh_dong"]:
        ra["hoan"] = r
        return ra, st
    luc_bat = float(st.get("luc_bat") or 0)
    if n >= TRAN_LAN_HONG and luc - luc_bat < THU_LAI_SAU_TRAN_GIAY:
        ra["hanh_dong"] = "da_tran"
        ra["hoan"] = "đã hỏng {0} lần liền — thôi bật, thử lại lúc {1}".format(
            n, _dt.datetime.fromtimestamp(luc_bat + THU_LAI_SAU_TRAN_GIAY).strftime("%d/%m %H:%M"))
        ra["bao"] = _bao_tran(goc, c, st, ly_do, luc, thu, gui_bao, ghi_nao)
        return ra, st
    if 0 < n < TRAN_LAN_HONG:
        from .ben_bi import cho_lui_dan  # noqa: PLC0415
        cho = cho_lui_dan(n, co_so_giay=LUI_CO_SO_GIAY, tran_giay=LUI_TRAN_GIAY)
        if luc - luc_bat < cho:
            ra["hanh_dong"], ra["hoan"] = "lui", "lùi dần sau {0} lần hỏng — lần bật sau lúc {1}".format(
                n, _dt.datetime.fromtimestamp(luc_bat + cho).strftime("%H:%M:%S"))
            return ra, st
    if thu:
        ra["hanh_dong"] = "se_bat"
        return ra, st
    try:
        ok, cau = c.bat(goc)
    except Exception as loi:  # noqa: BLE001
        ok, cau = False, "{0}: {1}".format(type(loi).__name__, str(loi)[:120])
    st["luc_bat"] = luc
    st["lan_bat_tong"] = int(st.get("lan_bat_tong") or 0) + 1
    ra["bat"] = cau
    tt2 = CHET
    if ok:
        for _ in range(max(1, int(c.cho_len_giay // 2))):
            ngu(2.0)
            tt2, ly2 = _kiem_an_toan(c, goc)
            if tt2 == SONG:
                break
    if ok and tt2 == SONG:
        st.update(lan_hong=0, lan_xuong=0)
        ra.update(hanh_dong="da_bat", trang_thai=SONG, lan_hong=0)
        _nao(goc, "sua", "{0} chết ({1}) — đã tự bật lại".format(c.ten, ly_do), {"ma": c.ma},
             "van-hanh|bat|{0}|{1:.0f}".format(c.ma, luc), ghi_nao)
    else:
        st["lan_hong"] = n + 1
        ra.update(hanh_dong="bat_hong", lan_hong=n + 1)
        if not ok:
            ra["ly_do"] = "{0}; bật hỏng: {1}".format(ly_do, cau)
        if n + 1 >= TRAN_LAN_HONG:
            ra["bao"] = _bao_tran(goc, c, st, ra["ly_do"], luc, thu, gui_bao, ghi_nao)
    return ra, st


def cau_khoi_dong(boot: float, kq: Dict[str, Any], so_khoa_don: int) -> Tuple[str, int, int, List[Dict[str, str]]]:
    """'khởi động hh:mm — X/Y thành phần chạy, đã dọn N khoá cũ; chưa chạy: ...'."""
    co = [v for v in kq.values() if v.get("trang_thai") not in (TAT, KHONG_CO)]
    song = [v for v in co if v.get("trang_thai") == SONG]
    hong = [{"ma": v["ma"], "ten": v["ten"], "ly_do": str(v.get("hoan") or v.get("ly_do") or "")[:160]}
            for v in co if v.get("trang_thai") != SONG]
    cau = "khởi động {0} — {1}/{2} thành phần chạy, đã dọn {3} khoá cũ".format(
        _hhmm(boot), len(song), len(co), so_khoa_don)
    if hong:
        cau += "; chưa chạy: " + "; ".join("{0} ({1})".format(h["ten"], h["ly_do"]) for h in hong)
    return cau, len(song), len(co), hong


class _KhoaLuot:
    """Một lượt canh một lúc (lịch 5 phút + lịch lúc đăng nhập có thể trùng)."""

    def __init__(self, goc: str) -> None:
        self.duong = os.path.join(duong_thu_muc(goc), ".khoa-luot")
        self.co = False

    def __enter__(self) -> bool:
        os.makedirs(os.path.dirname(self.duong), exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as tep:
                    json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
                self.co = True
                return True
            except FileExistsError:
                du = _doc_json(self.duong)
                if khe.pid_con_song(_pid(du)) and time.time() - _moc(self.duong, du) < HAN_LUOT_GIAY + 60:
                    return False
                khe.xoa_tep_ben_vung(self.duong)
            except OSError:
                return False
        return False

    def __exit__(self, *_a: Any) -> bool:
        if self.co:
            khe.xoa_tep_ben_vung(self.duong)
        return False


def mot_luot(goc: str, *, thu: bool = False, thanh_phan: Optional[List[ThanhPhan]] = None,
             bay_gio: Optional[float] = None, luc_boot: Optional[float] = None,
             ly_do_ban_fn: Optional[Callable[..., str]] = None, pid_con_song: Optional[Callable[[int], bool]] = None,
             ngu: Callable[[float], None] = time.sleep, gui_bao: Optional[Callable[..., Any]] = None,
             ghi_nao: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """MỘT lượt: (lượt đầu sau khởi động → dọn khoá cũ) → kiểm từng thành phần, bật cái CHẾT theo luật → (một lần mỗi
    lần khởi động) ghi báo cáo. `thu=True`: CHỈ ĐỌC — không bật, không xoá, không ghi, không báo; trả việc sẽ làm."""
    goc = os.path.abspath(goc)
    luc = time.time() if bay_gio is None else float(bay_gio)
    boot = luc_khoi_dong() if luc_boot is None else float(luc_boot)
    ds = so_dang_ky(goc) if thanh_phan is None else thanh_phan
    tat = set(doc_cai_dat(goc).get("tat") or [])
    so = _doc_json(duong_trang_thai(goc))
    so = so if isinstance(so, dict) else {}
    st_cu = so.get("thanh_phan") if isinstance(so.get("thanh_phan"), dict) else {}
    kd = dict(so.get("khoi_dong") or {}) if isinstance(so.get("khoi_dong"), dict) else {}
    moi_boot = not kd or abs(float(kd.get("boot_luc") or 0) - boot) > LECH_KHOI_DONG_GIAY
    don: List[Dict[str, Any]] = []
    if moi_boot or thu:
        don = don_khoa_khoi_dong(goc, boot, bay_gio=luc, thu=thu, pid_con_song=pid_con_song)
    if moi_boot:
        da_xoa = [m for m in don if m["xoa"] is not False]
        kd = {"boot_luc": boot, "luc_don": luc, "so_khoa_don": len(da_xoa),
              "khoa_don": [{"duong": m["duong"], "ly_do": m["ly_do"]} for m in da_xoa][:30], "bao_luc": None}
        if not thu:
            for m in da_xoa:
                _ghi_log(goc, "dọn khoá cũ {0} ({1}): {2}".format(m["duong"], m["nhan"], m["ly_do"]), luc)
    ban = (ly_do_ban_fn or ly_do_ban)(goc, luc_boot=boot, pid_con_song=pid_con_song)
    kq: Dict[str, Any] = {}
    st_moi: Dict[str, Any] = {}
    for c in ds:
        if c.ma in tat:
            kq[c.ma] = {"ma": c.ma, "ten": c.ten, "trang_thai": TAT, "hanh_dong": "", "ly_do": "tắt trong cai-dat.json"}
            continue
        try:
            co_mat = c.co_mat(goc) if c.co_mat else True
        except Exception:  # noqa: BLE001
            co_mat = True
        if not co_mat:
            kq[c.ma] = {"ma": c.ma, "ten": c.ten, "trang_thai": KHONG_CO, "hanh_dong": "", "ly_do": "máy này không có"}
            continue
        kq[c.ma], st_moi[c.ma] = _xu_ly(goc, c, st_cu.get(c.ma) or {}, kq, luc, boot, ban, thu, ngu, gui_bao, ghi_nao)
        v = kq[c.ma]
        if not thu and (v["hanh_dong"] in ("da_bat", "bat_hong", "da_tran") or v.get("hoi_phuc")):
            _ghi_log(goc, "{0}: {1} — {2}{3}".format(c.ten, _NHAN_HD.get(v["hanh_dong"]) if v["hanh_dong"] != "khoe"
                                                    else "đã sống lại", v["ly_do"],
                                                    " · " + v["bat"] if v.get("bat") else ""), luc)
    cau, n_song, n_tong, hong = cau_khoi_dong(boot, kq, int(kd.get("so_khoa_don") or 0))
    bao_moi = ""
    if not kd.get("bao_luc") and (n_song == n_tong or luc - boot >= BAO_SAU_GIAY):
        bao_moi = cau
        if not thu:
            kd.update(bao_luc=luc, cau=cau)
            _ghi_log(goc, cau, luc)
            _ghi_json(duong_khoi_dong(goc), {"boot_luc": boot, "luc": luc, "cau": cau, "song": n_song,
                                             "tong": n_tong, "hong": hong, "khoa_don": kd.get("so_khoa_don") or 0,
                                             "khoa": kd.get("khoa_don") or []})
            _nao(goc, "ket_qua" if not hong else "loi", cau,
                 {"song": n_song, "tong": n_tong, "khoa_don": kd.get("so_khoa_don") or 0,
                  "hong": [h["ma"] for h in hong]}, "van-hanh|khoi-dong|{0:.0f}".format(boot), ghi_nao)
    ket = {"luc": luc, "boot_luc": boot, "moi_boot": moi_boot, "thu": thu, "don": don, "ban": ban, "thanh_phan": kq,
           "bao_khoi_dong": bao_moi or kd.get("cau") or "", "song": n_song, "tong": n_tong, "hong": hong}
    if not thu:
        _ghi_json(duong_trang_thai(goc), {"luc": luc, "thanh_phan": st_moi, "khoi_dong": kd,
                                          "tom_tat": {"luc": luc, "song": n_song, "tong": n_tong, "hong": hong,
                                                      "khoi_dong": kd.get("cau") or "",
                                                      "ds": [{"ma": v["ma"], "ten": v["ten"],
                                                              "trang_thai": v["trang_thai"],
                                                              "hanh_dong": v.get("hanh_dong") or ""}
                                                             for v in kq.values()]}})
    return ket


# ── in + CLI ────────────────────────────────────────────────────────────────────────────────────────────────────

_NHAN_HD = {"khoe": "không làm gì (khoẻ)", "ket": "KẸT — không bật bản thứ hai, chỉ báo",
            "cho_khoi_dong": "chờ", "cho_xac_nhan": "chờ", "cho_phu_thuoc": "hoãn", "hoan_ban": "hoãn (máy bận)",
            "da_tran": "THÔI BẬT (chạm trần)", "lui": "lùi dần", "se_bat": "SẼ BẬT", "da_bat": "ĐÃ BẬT LẠI",
            "bat_hong": "BẬT HỎNG", "": ""}


def in_ket_qua(ket: Dict[str, Any], goc: str) -> str:
    luc, boot = ket["luc"], ket["boot_luc"]
    d = ["VẬN HÀNH{0} · {1} · máy khởi động {2} ({3:.0f} phút trước){4}".format(
        " — THỬ (chỉ đọc: không bật, không xoá, không ghi, không báo)" if ket["thu"] else "",
        _dt.datetime.fromtimestamp(luc).strftime("%d/%m %H:%M:%S"),
        _dt.datetime.fromtimestamp(boot).strftime("%d/%m %H:%M") if boot else "?", (luc - boot) / 60.0,
        " · LƯỢT ĐẦU sau lần khởi động này" if ket["moi_boot"] else "")]
    d.append("Máy bận: " + (ket["ban"] or "không (không tải lên, khe dựng/phụ đề rảnh)"))
    d.append("Thành phần:")
    for v in ket["thanh_phan"].values():
        d.append("  [{0:<8}] {1:<15} {2} — {3}".format(v["trang_thai"], v["ma"], v["ten"], v.get("ly_do") or ""))
        hd = v.get("hanh_dong") or ""
        if hd and hd != "khoe":
            dong = "               → {0}{1}".format(_NHAN_HD.get(hd, hd), ": " + v["hoan"] if v.get("hoan") else "")
            if hd == "se_bat":
                dong += {"truc_quan_8790": ": " + " ".join(lenh_truc_quan(goc)) + "  (cwd " + goc + ")",
                         "giao_dien": ": wscript CHAY-GON.vbs", "tram_8765": ": pythonw tram_nen.py",
                         "agent_vm": ": python -u -X utf8 vm/agent.py"}.get(v["ma"], "")
            if v.get("bao"):
                dong += " · báo động: " + ("sẽ gửi (1 lần/ngày)" if v["bao"] == "se_bao" else "đã gửi")
            d.append(dong)
    don = ket["don"]
    xoa = [m for m in don if m["xoa"] is not False]
    d.append("Khoá (luật khởi động): {0} tệp, {1} {2}".format(len(don), len(xoa), "sẽ xoá" if ket["thu"] else "đã xoá"))
    for m in don:
        d.append("  {0} {1} — {2}".format("XOÁ" if m["xoa"] is not False else "giữ", m["duong"], m["ly_do"]))
    d.append("Báo cáo khởi động: " + (ket["bao_khoi_dong"] or "(chưa — chờ mọi thành phần lên hoặc 15 phút sau lúc máy lên)"))
    return "\n".join(d)


def main(argv: Optional[List[str]] = None, *, goc: Optional[str] = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    goc = os.path.abspath(goc or GOC_TOOL)
    lenh = a[0] if a and not a[0].startswith("-") else "mot-luot"
    thu = "--thu" in a

    def _in(chu: str) -> None:
        if sys.stdout is not None:
            try:
                print(chu, flush=True)
            except (OSError, ValueError):
                pass

    if lenh in ("dang-ky", "huy", "trang-thai"):
        from . import lich_tu_chay  # noqa: PLC0415
        if lenh == "dang-ky":
            ok, cau = lich_tu_chay.dang_ky_van_hanh(goc)
        elif lenh == "huy":
            ok, cau = lich_tu_chay.huy_van_hanh(goc)
        else:
            ok, cau = True, json.dumps({"lich": lich_tu_chay.trang_thai_van_hanh(goc),
                                        "tom_tat": (_doc_json(duong_trang_thai(goc)) or {}).get("tom_tat")},
                                       ensure_ascii=False, indent=1)
        _in(cau)
        return 0 if ok else 1
    if lenh == "don-khoa":
        boot = luc_khoi_dong()
        ds = don_khoa_khoi_dong(goc, boot, thu=thu)
        for m in ds:
            _in("{0} {1} — {2}".format("XOÁ" if m["xoa"] is not False else "giữ", m["duong"], m["ly_do"]))
            if not thu and m["xoa"]:
                _ghi_log(goc, "dọn khoá cũ {0} ({1}): {2}".format(m["duong"], m["nhan"], m["ly_do"]))
        _in("{0} tệp khoá, {1} {2}.".format(len(ds), sum(1 for m in ds if m["xoa"] is not False),
                                            "sẽ xoá" if thu else "đã xoá"))
        return 0
    if lenh != "mot-luot":
        _in(__doc__ or "")
        return 2
    from . import ben_bi  # noqa: PLC0415
    hen = None
    try:
        if thu:
            ket = mot_luot(goc, thu=True)
        else:
            hen = ben_bi.hen_gio_tu_thoat(goc, "van_hanh", HAN_LUOT_GIAY)
            with _KhoaLuot(goc) as duoc:
                if not duoc:
                    _in("một lượt vận hành khác đang chạy — thoát.")
                    return 0
                ben_bi.ghi_nhip(goc, "van_hanh", "bat_dau")
                ket = mot_luot(goc)
                ben_bi.ghi_nhip(goc, "van_hanh", "xong", song=ket["song"], tong=ket["tong"])
                ben_bi.xoa_loi_vong(goc, "van_hanh")
    except Exception as loi:  # noqa: BLE001 — sập thì ghi sổ sập vòng (lặp → báo động), lượt 5' sau chạy lại
        if not thu:
            ben_bi.ghi_loi_vong(goc, "van_hanh", loi)
        _in("lượt vận hành sập: {0}: {1}".format(type(loi).__name__, loi))
        return 1
    finally:
        if hen is not None:
            hen.cancel()
    _in(in_ket_qua(ket, goc))
    xau = [v for v in ket["thanh_phan"].values() if v.get("hanh_dong") in ("ket", "bat_hong", "da_tran")]
    return 1 if xau else 0


if __name__ == "__main__":
    raise SystemExit(main())
