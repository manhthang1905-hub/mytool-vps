"""vm/launcher_ket.py — dọn launcher Chrome Portable KẸT, MỘT luật chung cho mọi việc DOM (16/10/2026).

Chuyện thật: launcher `<K>\\<K>.exe --remote-debugging-port=93xx …` đôi khi SỐNG TIẾP mà không còn `chrome.exe` con
nào. Mọi cửa canh (`agent._chrome_dang_chay` hỏi `tasklist` theo TÊN launcher) thấy tên ấy → "Chrome kênh <K> đang
chạy — việc khác đang dùng" hàng giờ (TL3: từ 17:35 tới 21:21) → kênh đó tắc hết việc DOM: đăng, A/B, danh sách phát,
ghim. Bản cũ chỉ dọn launcher do CHÍNH phiên mình mở (`thiet_lap_kenh_dom.don_launcher_mo_coi`, `agent._don_launcher_sot`)
— launcher của phiên đã chết thì không ai dọn.

═══ LUẬT KẸT (đủ CẢ BA mới tắt) ═══
  1. không còn `chrome.exe` con — con trực tiếp (ParentProcessId) HAY chrome.exe chạy từ thư mục bộ trình duyệt
     `<K>\\` / mang đúng `--user-data-dir` hồ sơ của launcher;
  2. cổng DevTools không đáp (cổng trong dòng lệnh launcher + cổng người gọi biết của kênh);
  3. launcher đã sống ≥ `TUOI_TOI_THIEU_GIAY` (3 phút — launcher vừa bật cần ~5–12 giây mới đẻ Chrome).
Kẹt → `taskkill /F /PID <pid>` ĐÚNG launcher đó (không /T, không theo tên, không đụng kênh khác) + ghi sổ
`<vm>/logs/launcher-ket.jsonl` + não `suc-khoe-may`.

Luật cứng: KHÔNG bao giờ tắt launcher còn Chrome sống; đang tải lên (`dang-dodang.json` còn chủ sống, hoặc `.khoa-may`
giữ việc đăng) thì BỎ QUA cả lượt dọn. Chỉ nhận launcher đúng nếp PortableApps (`<D>\\<D>.exe` + `<D>\\App\\`) — không
bao giờ đụng tiến trình lạ trùng tên thư mục. Chỉ thư viện chuẩn (luật `vm/`). Hai chỗ gọi: cửa canh (trước khi trả
"đang chạy") và lượt canh 5 phút `core/van_hanh.py`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

TUOI_TOI_THIEU_GIAY = 180.0
#: Việc trên `.khoa-may` là việc ĐĂNG (cùng `core.khe.VIEC_DANG_UU_TIEN`) — đang giữ thì không dọn gì.
VIEC_DANG = ("tai_len", "phien", "viec")
TEN_SO = "launcher-ket.jsonl"

_RE_CONG = re.compile(r"--remote-debugging-port[= ](\d+)", re.I)
_RE_HO_SO = re.compile(r'--user-data-dir=(?:"([^"]+)"|(\S+))', re.I)

#: Chỉ lấy chrome.exe và tiến trình nằm đúng nếp `<D>\<D>.exe` (giảm cỡ JSON); tuổi tính sẵn bằng giây.
_LENH_PS = (
    "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and ($_.Name -eq 'chrome.exe' -or "
    "((Split-Path (Split-Path $_.ExecutablePath -Parent) -Leaf) + '.exe') -eq $_.Name) } | Select-Object "
    "@{n='pid';e={$_.ProcessId}},@{n='ppid';e={$_.ParentProcessId}},@{n='ten';e={$_.Name}},"
    "@{n='duong';e={$_.ExecutablePath}},"
    "@{n='lenh';e={ if ($_.CommandLine) { $_.CommandLine.Substring(0, [Math]::Min(700, $_.CommandLine.Length)) } }},"
    "@{n='tuoi';e={[int]((Get-Date) - $_.CreationDate).TotalSeconds}} | ConvertTo-Json -Compress")


def _khong_cua_so() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def liet_ke_tien_trinh(han: float = 40.0):
    """Bảng tiến trình [{pid, ppid, ten, duong, lenh, tuoi}] hoặc None khi không hỏi được (không chắc → không tắt)."""
    try:
        ra = subprocess.run(["powershell", "-NoProfile", "-Command", _LENH_PS], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=han, creationflags=_khong_cua_so())
        du = json.loads((ra.stdout or "").strip() or "[]")
    except Exception:  # noqa: BLE001
        return None
    if isinstance(du, dict):
        du = [du]
    return [x for x in du if isinstance(x, dict)] if isinstance(du, list) else None


def cong_dap(cong: int, han: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:{0}/json/version".format(int(cong)), timeout=han) as tl:
            return tl.status == 200
    except Exception:  # noqa: BLE001 — cổng đóng là chuyện thường
        return False


def pid_con_song(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        ra = subprocess.run(["tasklist", "/FI", "PID eq {0}".format(pid), "/NH"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=10, creationflags=_khong_cua_so())
        return ra.returncode != 0 or str(pid) in (ra.stdout or "")    # hỏi không được → coi như sống
    except Exception:  # noqa: BLE001
        return True


def giet_pid(pid: int) -> bool:
    """`taskkill /F /PID` ĐÚNG một PID (không /T). Lưới an toàn: trong pytest không bao giờ giết thật."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    try:
        ra = subprocess.run(["taskkill", "/F", "/PID", str(int(pid))], capture_output=True, timeout=15,
                            creationflags=_khong_cua_so())
        return ra.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _thuong(s) -> str:
    return os.path.normcase(os.path.normpath(str(s or ""))) if s else ""


def la_launcher(p: dict, co_thu_muc=os.path.isdir) -> bool:
    """Đúng nếp PortableApps: `<D>\\<D>.exe` (không phải chrome.exe) và có `<D>\\App\\`."""
    duong = str(p.get("duong") or "")
    ten = os.path.basename(duong)
    if not duong or ten.lower() == "chrome.exe":
        return False
    d = os.path.dirname(duong)
    if os.path.splitext(ten)[0].lower() != os.path.basename(d).lower():
        return False
    try:
        return bool(co_thu_muc(os.path.join(d, "App")))
    except Exception:  # noqa: BLE001
        return False


def cong_cua(p: dict):
    m = _RE_CONG.search(str(p.get("lenh") or ""))
    return int(m.group(1)) if m else None


def _ho_so(p: dict) -> str:
    m = _RE_HO_SO.search(str(p.get("lenh") or ""))
    return _thuong(m.group(1) or m.group(2)) if m else ""


def chrome_con(l: dict, ds: list) -> list:
    """chrome.exe của launcher `l`: con trực tiếp, chạy từ thư mục bộ trình duyệt, hoặc mang đúng hồ sơ của nó."""
    goc = _thuong(os.path.dirname(str(l.get("duong") or "")))
    ho_so = _ho_so(l)
    ra = []
    for x in ds:
        if str(x.get("ten") or "").lower() != "chrome.exe":
            continue
        if int(x.get("ppid") or -1) == int(l.get("pid") or -2):
            ra.append(x)
            continue
        chu = os.path.normcase(str(x.get("duong") or "") + " " + str(x.get("lenh") or ""))
        if (goc and goc + os.sep in chu) or (ho_so and ho_so in os.path.normcase(chu)):
            ra.append(x)
    return ra


def dang_tai_len(goc_vm: str, goc_tool: str, song=pid_con_song) -> str:
    """'' nếu không có lượt đăng nào đang dở; câu lý do nếu có (khi đó KHÔNG dọn gì)."""
    for d in {os.path.join(goc_vm, "logs", "dang-dodang.json"), os.path.join(goc_tool, "logs", "dang-dodang.json")}:
        if not os.path.isfile(d):
            continue
        try:
            with open(d, "r", encoding="utf-8-sig") as tep:
                du = json.load(tep)
            pid = int((du or {}).get("pid") or 0) if isinstance(du, dict) else 0
        except (OSError, ValueError, TypeError):
            pid = 0
        if not pid or song(pid):
            return "đang có máy đăng dở ({0})".format(d)
    d = os.path.join(goc_tool, "workspace", "tu-chay", ".khoa-may")
    if os.path.isfile(d):
        try:
            with open(d, "r", encoding="utf-8-sig") as tep:
                du = json.load(tep)
        except (OSError, ValueError):
            return "không đọc được .khoa-may — không chắc, không dọn"
        if isinstance(du, dict):
            try:
                pid = int(du.get("pid") or 0)
            except (TypeError, ValueError):
                pid = 0
            if pid and str(du.get("viec") or "") in VIEC_DANG and song(pid):
                return ".khoa-may đang giữ việc đăng «{0}» (PID {1})".format(du.get("viec"), pid)
    return ""


def xet(ds: list, *, ten_exe: str = "", cong_them=(), tuoi_toi_thieu: float = TUOI_TOI_THIEU_GIAY,
        cong_dap_fn=cong_dap, co_thu_muc=os.path.isdir) -> list:
    """Xét từng launcher → [(tiến trình, 'ket'|'giu', lý do)]. `ten_exe` = chỉ xét đúng tên đó."""
    kq = []
    for p in ds:
        if ten_exe and str(p.get("ten") or "").lower() != ten_exe.lower():
            continue
        if not la_launcher(p, co_thu_muc):
            continue
        con = chrome_con(p, ds)
        if con:
            kq.append((p, "giu", "còn {0} chrome.exe".format(len(con))))
            continue
        cong = [c for c in [cong_cua(p)] + list(cong_them or ()) if c]
        dap = [c for c in dict.fromkeys(cong) if cong_dap_fn(c)]
        if dap:
            kq.append((p, "giu", "cổng {0} đáp".format(dap[0])))
            continue
        try:
            tuoi = float(p.get("tuoi") or 0)
        except (TypeError, ValueError):
            tuoi = 0.0
        if tuoi < tuoi_toi_thieu:
            kq.append((p, "giu", "mới bật {0:.0f} giây".format(tuoi)))
            continue
        kq.append((p, "ket", "không Chrome con, cổng {0} câm, sống {1:.0f} phút".format(
            "/".join(str(c) for c in dict.fromkeys(cong)) or "(không khai)", tuoi / 60.0)))
    return kq


def _nao_mac_dinh(goc_tool: str):
    """Ghi não `suc-khoe-may` qua `core.nao_bo_phan` khi chạy trong MyTool; không có thì thôi (không hỏng)."""
    def ghi_nao(goc, bo_phan, loai, **kw):
        try:
            if goc_tool not in sys.path:
                sys.path.append(goc_tool)                 # CUỐI sys.path: không che module nào của vm/
            from core.nao_bo_phan import ghi  # noqa: PLC0415
            return ghi(goc, bo_phan, loai, **kw)
        except Exception:  # noqa: BLE001
            return False
    return ghi_nao


def _ghi_so(goc_vm: str, dong: dict) -> None:
    try:
        d = os.path.join(goc_vm, "logs")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, TEN_SO), "a", encoding="utf-8") as tep:
            tep.write(json.dumps(dong, ensure_ascii=False) + "\n")
    except OSError:
        pass


def don(goc_vm: str, goc_tool: str = "", *, ten_exe: str = "", cong_them=(), nguon: str = "", ghi=None,
        thu: bool = False, liet_ke=liet_ke_tien_trinh, cong_dap_fn=cong_dap, giet=giet_pid, song=pid_con_song,
        co_thu_muc=os.path.isdir, ghi_nao=None, tuoi_toi_thieu: float = TUOI_TOI_THIEU_GIAY,
        bay_gio: float = None) -> dict:
    """MỘT lượt dọn. Trả {bo_qua, da_tat:[...], tat_hong:[...], ket:[...] (thu), giu:[...]}. Không bao giờ ném lỗi."""
    goc_tool = goc_tool or os.path.dirname(os.path.abspath(goc_vm))
    ghi = ghi or (lambda _s: None)
    kq = {"bo_qua": "", "da_tat": [], "tat_hong": [], "ket": [], "giu": []}
    try:
        r = dang_tai_len(goc_vm, goc_tool, song)
        if r:
            kq["bo_qua"] = r
            return kq
        ds = liet_ke()
        if ds is None:
            kq["bo_qua"] = "không đọc được bảng tiến trình"
            return kq
        luc = time.time() if bay_gio is None else float(bay_gio)
        for p, kl, ly in xet(ds, ten_exe=ten_exe, cong_them=cong_them, tuoi_toi_thieu=tuoi_toi_thieu,
                              cong_dap_fn=cong_dap_fn, co_thu_muc=co_thu_muc):
            mo = {"pid": int(p.get("pid") or 0), "ten": str(p.get("ten") or ""), "ly_do": ly,
                  "tuoi": float(p.get("tuoi") or 0), "cong": cong_cua(p)}
            if kl != "ket":
                kq["giu"].append(mo)
                continue
            if thu:
                kq["ket"].append(mo)
                continue
            ok = bool(giet(mo["pid"]))
            kq["da_tat" if ok else "tat_hong"].append(mo)
            cau = "{0} launcher {1} kẹt (PID {2}: {3})".format("đã tắt" if ok else "TẮT HỎNG", mo["ten"], mo["pid"], ly)
            ghi(cau)
            _ghi_so(goc_vm, dict(mo, luc=luc, gio=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(luc)),
                                 nguon=nguon, ket_qua="da_tat" if ok else "tat_hong"))
            (ghi_nao or _nao_mac_dinh(goc_tool))(
                goc_tool, "suc-khoe-may", "sua" if ok else "loi", noi_dung=cau, nguon=nguon or "launcher-ket",
                so={"pid": mo["pid"], "ten": mo["ten"], "tuoi_phut": round(mo["tuoi"] / 60.0, 1), "cong": mo["cong"],
                    "ok": ok},
                khoa="launcher-ket|{0}|{1}|{2:.0f}".format(mo["ten"], mo["pid"], (luc - mo["tuoi"]) // 60))
    except Exception as loi:  # noqa: BLE001 — dọn hỏng không được làm vỡ cửa canh
        kq["bo_qua"] = "lỗi dọn launcher: {0}".format(str(loi)[:120])
    return kq
