"""Dọn bản Chrome CŨ trong Chrome Portable của từng kênh (16/10/2026 — chủ duyệt "Cho tự xoá").

Chrome tự cập nhật để lại thư mục phiên bản cũ `<kênh>\\App\\Chrome-bin\\<a.b.c.d>\\` (~1 GB mỗi bản) mà không bao
giờ tự dọn — 8 kênh × 2 bản cũ ≈ 8–10 GB ổ C. Gác tổng gọi qua `core.don_dia.chay` (mỗi 3 giờ); lệnh tay
`python -m core.don_chrome_cu --thu` (chỉ tính) · `--that` (xoá thật).

═══ LUẬT (mỗi luật một câu) ═══

1. Bộ Chrome = thư mục cạnh MyTool có `<tên>\\<tên>.exe` + `App\\Chrome-bin\\chrome.exe` (đúng nếp
   `mo_kenh.tim_chrome_mau`); chỉ xét thư mục con của `Chrome-bin` tên đúng dạng phiên bản, không đi theo liên kết.
2. GIỮ: bản của `chrome.exe`, bản của `new_chrome.exe` (bản cập nhật đang chờ thay), mọi bản mà
   `chrome.VisualElementsManifest.xml` trỏ tới, và bản MỚI NHẤT. Không đọc được bản của `chrome.exe` (hoặc bản ấy không
   có thư mục) → KHÔNG xoá gì ở bộ đó (không chắc thì giữ).
3. Không liệt kê được tiến trình đang chạy → không xoá gì; tiến trình nào chạy từ trong thư mục đó → bỏ qua thư mục.
4. Thử khoá bằng đổi tên `<bản>` → `<bản>.dang-xoa`: Windows từ chối khi còn tệp bên trong đang mở/nạp → đang dùng,
   bỏ qua (không xoá dở một bản đang chạy).
5. Xoá hỏng giữa chừng → dừng thư mục đó, để nguyên (`.dang-xoa`, lượt sau xoá tiếp). Không bao giờ giết Chrome.
6. Không đổi tên/dời chính thư mục Chrome Portable của kênh, không đụng `Data\\` (hồ sơ đăng nhập) hay tệp nào khác.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from typing import Any, Callable, Dict, Iterable, List, Optional

__all__ = ["DUOI_DANG_XOA", "cac_bo_chrome", "phien_ban_exe", "duong_tien_trinh", "ke_hoach", "chay", "tom_tat"]

_RE_BAN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
DUOI_DANG_XOA = ".dang-xoa"
_RE_MANIFEST = re.compile(r"(\d+\.\d+\.\d+\.\d+)[\\/]")


def _gb(so_byte: float) -> str:
    return "{0:.2f} GB".format(so_byte / 1024 ** 3)


def _khoa_ban(ten: str) -> tuple:
    return tuple(int(x) for x in ten.split("."))


def _la_lien_ket(duong: str) -> bool:
    try:
        from .don_dep import _la_lien_ket as f  # noqa: PLC0415 — một định nghĩa symlink/junction cho cả kho
        return bool(f(duong))
    except Exception:  # noqa: BLE001
        return os.path.islink(duong)


def _kich_thuoc(duong: str) -> int:
    tong = 0
    for g, ds, tep in os.walk(duong):
        ds[:] = [d for d in ds if not _la_lien_ket(os.path.join(g, d))]
        for t in tep:
            try:
                tong += os.path.getsize(os.path.join(g, t))
            except OSError:
                pass
    return tong


def cac_bo_chrome(goc: str, cha: Optional[str] = None) -> List[Dict[str, str]]:
    """`[{ten, goc_chrome, bin}]` — mọi Chrome Portable cạnh MyTool (`cha` = thư mục cha của `goc`)."""
    cha = cha or os.path.dirname(os.path.abspath(goc))
    try:
        ten_ds = sorted(os.listdir(cha))
    except OSError:
        return []
    ra = []
    for t in ten_ds:
        if t.startswith((".", "_")):
            continue
        for d in (os.path.join(cha, t), os.path.join(cha, t, t)):
            b = os.path.join(d, "App", "Chrome-bin")
            if (os.path.isfile(os.path.join(d, t + ".exe")) and os.path.isfile(os.path.join(b, "chrome.exe"))
                    and not _la_lien_ket(d) and not _la_lien_ket(b)):
                ra.append({"ten": t, "goc_chrome": d, "bin": b})
                break
    return ra


def phien_ban_exe(duong: str) -> str:
    """Bản tệp (FileVersion) của một .exe Windows, "" nếu không đọc được."""
    if not os.path.isfile(duong):
        return ""
    try:
        import ctypes  # noqa: PLC0415
        from ctypes import wintypes  # noqa: PLC0415

        ver = ctypes.WinDLL("version")
        ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        ver.GetFileVersionInfoSizeW.restype = wintypes.DWORD
        ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        ver.GetFileVersionInfoW.restype = wintypes.BOOL
        ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
                                       ctypes.POINTER(wintypes.UINT)]
        ver.VerQueryValueW.restype = wintypes.BOOL
        n = ver.GetFileVersionInfoSizeW(duong, None)
        if not n:
            return ""
        buf = ctypes.create_string_buffer(n)
        if not ver.GetFileVersionInfoW(duong, 0, n, buf):
            return ""
        p, dai = ctypes.c_void_p(), wintypes.UINT()
        if not ver.VerQueryValueW(buf, "\\", ctypes.byref(p), ctypes.byref(dai)) or dai.value < 16:
            return ""
        o = ctypes.cast(p, ctypes.POINTER(ctypes.c_uint32 * 4)).contents   # VS_FIXEDFILEINFO: chữ ký, cấu trúc, MS, LS
        if o[0] != 0xFEEF04BD:
            return ""
        return "{0}.{1}.{2}.{3}".format(o[2] >> 16, o[2] & 0xFFFF, o[3] >> 16, o[3] & 0xFFFF)
    except Exception:  # noqa: BLE001 — không phải Windows / tệp lạ → không biết bản
        return ""


def duong_tien_trinh() -> Optional[List[str]]:
    """Đường .exe của mọi tiến trình đang chạy; None = không liệt kê được (nơi gọi KHÔNG xoá gì)."""
    try:
        import psutil  # noqa: PLC0415

        return [str(p.info.get("exe")) for p in psutil.process_iter(["exe"]) if p.info.get("exe")]
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        return None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "(Get-CimInstance Win32_Process).ExecutablePath"],
                           capture_output=True, text=True, timeout=90,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:  # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    return [d.strip() for d in (r.stdout or "").splitlines() if d.strip()]


def _ban_manifest(bin_: str) -> List[str]:
    try:
        with open(os.path.join(bin_, "chrome.VisualElementsManifest.xml"), "r", encoding="utf-8", errors="replace") as t:
            return sorted(set(_RE_MANIFEST.findall(t.read())))
    except OSError:
        return []


def ke_hoach(goc: str, *, cha: Optional[str] = None,
             doc_phien_ban: Callable[[str], str] = phien_ban_exe) -> List[Dict[str, Any]]:
    """Chỉ ĐỌC: mỗi bộ Chrome → `{ten, bin, chrome_exe, new_chrome, giu, xoa: [{ten, duong, bytes, do}], bo_qua}`.
    `bo_qua` khác "" = không xoá gì ở bộ này (lý do)."""
    ra = []
    for bo in cac_bo_chrome(goc, cha):
        b = bo["bin"]
        try:
            con = [t for t in os.listdir(b) if os.path.isdir(os.path.join(b, t)) and not _la_lien_ket(os.path.join(b, t))]
        except OSError:
            con = []
        ban = sorted([t for t in con if _RE_BAN.match(t)], key=_khoa_ban)
        do = [t for t in con if t.endswith(DUOI_DANG_XOA) and _RE_BAN.match(t[:-len(DUOI_DANG_XOA)])]
        exe = doc_phien_ban(os.path.join(b, "chrome.exe"))
        moi = doc_phien_ban(os.path.join(b, "new_chrome.exe")) if os.path.isfile(os.path.join(b, "new_chrome.exe")) else ""
        giu = {x for x in (exe, moi) if x} | set(_ban_manifest(b)) | ({ban[-1]} if ban else set())
        x = {"ten": bo["ten"], "bin": b, "chrome_exe": exe, "new_chrome": moi, "giu": sorted(giu, key=_khoa_ban),
             "xoa": [], "bo_qua": ""}
        if not exe or exe not in ban:
            x["bo_qua"] = "không đọc chắc được bản chrome.exe ({0}) — giữ hết".format(exe or "?")
        else:
            for t in ban:
                if t not in giu:
                    d = os.path.join(b, t)
                    x["xoa"].append({"ten": t, "duong": d, "bytes": _kich_thuoc(d), "do": False})
            for t in do:
                if t[:-len(DUOI_DANG_XOA)] not in giu:
                    d = os.path.join(b, t)
                    x["xoa"].append({"ten": t, "duong": d, "bytes": _kich_thuoc(d), "do": True})
        ra.append(x)
    return ra


def _trong(duong: str, cac_exe: Iterable[str]) -> bool:
    goc = os.path.normcase(os.path.abspath(duong)).rstrip("\\/") + os.sep
    return any(os.path.normcase(os.path.abspath(p)).startswith(goc) for p in cac_exe)


class _Dung(Exception):
    """Lỗi đầu tiên khi xoá — dừng cả thư mục."""


def _xoa_dung_khi_loi(duong: str) -> Optional[str]:
    """`shutil.rmtree` dừng ở lỗi đầu tiên (không bỏ qua, không thử lại). Trả lỗi hoặc None."""
    loi: List[str] = []

    def _dung(ham, p, ei):
        try:  # tệp chỉ-đọc: bỏ cờ chỉ-đọc rồi xoá đúng MỘT lần nữa (không phải thử lại khi bị khoá)
            if os.path.exists(p) and not os.access(p, os.W_OK):
                os.chmod(p, stat.S_IWRITE)
                ham(p)
                return
        except OSError:
            pass
        loi.append("{0}: {1}".format(os.path.basename(str(p)), ei[1] if isinstance(ei, tuple) else ei))
        raise _Dung()

    try:
        shutil.rmtree(duong, onerror=_dung)
    except _Dung:
        pass
    except OSError as e:
        loi.append(str(e)[:150])
    return loi[0][:200] if loi else None


def chay(goc: str, *, thu: bool = True, cha: Optional[str] = None,
         doc_phien_ban: Callable[[str], str] = phien_ban_exe,
         tien_trinh: Callable[[], Optional[List[str]]] = duong_tien_trinh) -> Dict[str, Any]:
    """Một lượt. `thu=True`: chỉ tính sẽ giải phóng bao nhiêu (không đổi tên, không xoá). Trả
    `{thu, bo: [ke_hoach + ket từng bản], bytes (sẽ/đã giải phóng), so_ban, loi}`."""
    kh = ke_hoach(goc, cha=cha, doc_phien_ban=doc_phien_ban)
    ra: Dict[str, Any] = {"thu": thu, "bo": kh, "bytes": 0, "so_ban": 0, "loi": ""}
    if not any(x["xoa"] for x in kh):
        return ra
    cac_exe = tien_trinh()
    if cac_exe is None:
        ra["loi"] = "không liệt kê được tiến trình đang chạy — không xoá gì"
        for x in kh:
            for v in x["xoa"]:
                v["ket"] = "bo_qua"
        return ra
    for x in kh:
        for v in x["xoa"]:
            if _trong(v["duong"], cac_exe):
                v["ket"] = "dang_chay"
                continue
            if thu:
                v["ket"] = "se_xoa"
                ra["bytes"] += v["bytes"]
                ra["so_ban"] += 1
                continue
            d = v["duong"]
            if not v["do"]:
                tam = d + DUOI_DANG_XOA
                if os.path.exists(tam):
                    v["ket"] = "bo_qua"
                    continue
                try:
                    os.rename(d, tam)            # Windows: còn tệp đang mở/nạp bên trong → PermissionError
                except OSError:
                    v["ket"] = "dang_dung"
                    continue
                d = tam
            loi = _xoa_dung_khi_loi(d)
            con = _kich_thuoc(d) if os.path.exists(d) else 0
            ra["bytes"] += max(0, v["bytes"] - con)
            if loi:
                v["ket"], v["loi"] = "xoa_do", loi
            else:
                v["ket"] = "da_xoa"
                ra["so_ban"] += 1
    return ra


def tom_tat(kq: Dict[str, Any]) -> str:
    """Một dòng: "Chrome cũ: 16 bản sẽ giải phóng 9.80 GB (8 bộ)"."""
    so_bo = sum(1 for x in kq.get("bo") or [] if x.get("xoa"))
    chu = "Chrome cũ: {0} bản {1} {2} ({3} bộ)".format(
        kq.get("so_ban") or 0, "sẽ giải phóng" if kq.get("thu") else "đã xoá", _gb(kq.get("bytes") or 0), so_bo)
    ket = [v.get("ket") for x in kq.get("bo") or [] for v in x.get("xoa") or []]
    for k, nhan in (("dang_chay", "đang chạy"), ("dang_dung", "đang dùng"), ("xoa_do", "xoá dở")):
        if k in ket:
            chu += " · {0} bản {1} (lượt sau thử lại)".format(ket.count(k), nhan)
    return chu + (" · " + kq["loi"] if kq.get("loi") else "")


def _main(argv: Optional[List[str]] = None) -> int:
    import sys  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    a = list(sys.argv[1:] if argv is None else argv)
    if "--thu" not in a and "--that" not in a:
        print("Dùng: python -m core.don_chrome_cu --thu [--goc <MyTool>]   (chỉ tính)")
        print("      python -m core.don_chrome_cu --that                    (xoá thật bản Chrome cũ)")
        return 0
    goc = a[a.index("--goc") + 1] if "--goc" in a and a.index("--goc") + 1 < len(a) else \
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kq = chay(goc, thu="--thu" in a)
    for x in kq["bo"]:
        print("  {0}: chrome.exe {1}{2} · giữ {3}{4}".format(
            x["ten"], x["chrome_exe"] or "?", " · chờ thay " + x["new_chrome"] if x["new_chrome"] else "",
            ", ".join(x["giu"]), " · " + x["bo_qua"] if x["bo_qua"] else ""))
        for v in x["xoa"]:
            print("      {0} {1} → {2}".format(v["ten"], _gb(v["bytes"]), v.get("ket") or "?"))
    print(tom_tat(kq))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
