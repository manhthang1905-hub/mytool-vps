"""core/tu_dang_nhap.py — tự đăng nhập Windows bằng LSA secret, bỏ mật khẩu chữ
trần — Việc 3.6, `workspace/LO-TRINH-PHAT-HANH-V3.md` (duyệt 29/09/2026):

    "14 tự đăng nhập Windows bằng LSA secret, bỏ selfheal.ps1"
    "A19 selfheal.ps1 mật khẩu chữ trần."

Kiểm toán 26/09/2026 (`workspace/KE-HOACH-GIA-CO-1-NAM.md`) nói thẳng:
`selfheal.ps1` (ngoài kho, tự VPS sinh ra lúc cài) CHỨA MẬT KHẨU Administrator
CHỮ TRẦN. Windows tự có một chỗ cất mật khẩu autologon KHÔNG lộ ra file/registry
đọc được bằng mắt thường: LSA secret (`LsaStorePrivateData`, khoá
`"DefaultPassword"` — đúng tên Winlogon tự tìm khi registry
`DefaultPassword` trống, xem tài liệu `autologon.exe`/Sysinternals). Máy đặt
được `AutoAdminLogon=1` + LSA secret thì KHÔNG CẦN registry `DefaultPassword`
chữ trần, và KHÔNG CẦN `selfheal.ps1` tự gán lại mật khẩu mỗi 30 phút.

═══ CHỈ VIẾT + TEST MOCK — `dat_tu_dang_nhap` KHÔNG CHẠY THẬT Ở BẢN NÀY ═══

Máy đang chạy phiên này (VPS sản xuất thật, đang tự đăng nhập bằng
`DefaultPassword` chữ trần — xem kết quả `doc_trang_thai()` thật ở
`NHAT-KY-PHAT-TRIEN.md`) — ĐỔI THẲNG cách đăng nhập của một máy đang chạy
video thật, giữa lúc đóng băng trước đêm chạy đầu tiên (29→30/09), là rủi ro
không cần thiết: đổi hỏng thì máy khởi động lại xong ĐỨNG Ở MÀN HÌNH ĐĂNG NHẬP,
không ai vào Remote Desktop để gõ mật khẩu được (không có đầu vào bàn phím vật
lý trên VPS thuê ngoài — mất quyền vào máy). `dat_tu_dang_nhap` ở đây CHỈ được
gọi trong bộ test (đối tượng `luu_lsa`/`ghi_dang_ky` giả) — chạy thật để lại
làm sau, có xác nhận của chủ dự án và một kế hoạch khôi phục nếu hỏng (xem
`GHI-CHU.md`, mục "CÁCH NỐI SAU").

═══ THỨ TỰ GHI CÓ CHỦ Ý: LSA SECRET TRƯỚC, XOÁ CHỮ TRẦN SAU ═══

`dat_tu_dang_nhap` lưu mật khẩu vào LSA secret TRƯỚC, chỉ xoá giá trị
`DefaultPassword` chữ trần trong registry SAU KHI lưu LSA thành công. Đảo thứ
tự (xoá trước, lưu sau) mà bước lưu LSA hỏng giữa chừng (mất quyền, tiến trình
bị giết) sẽ để máy ở trạng thái `AutoAdminLogon=1` mà KHÔNG CÓ MẬT KHẨU NÀO cả
— khởi động lại xong đứng ở màn hình đăng nhập, không tự vào được, giống hệt
rủi ro nói ở trên nhưng do CHÍNH HÀM NÀY gây ra thay vì do chạy nó trên máy
đang sống.

═══ KHÔNG BAO GIỜ IN/GHI MẬT KHẨU RA ═══

Mọi hàm ở đây CHỈ trả `bool`/`None` cho câu hỏi "có mật khẩu chưa" — không
hàm nào trả về hay in ra GIÁ TRỊ mật khẩu, kể cả khi đọc thành công từ LSA
secret (`LsaRetrievePrivateData` bắt buộc phải lấy giá trị thật vào bộ nhớ để
kiểm tồn tại — Win32 không có API "chỉ hỏi có hay không" — nhưng giá trị đó bị
`LsaFreeMemory` giải phóng ngay, không bao giờ được gán vào biến trả về, log,
hay `print()`). `kiem_selfheal()` cũng vậy: chỉ báo CÓ/KHÔNG một khớp mẫu
"có vẻ là gán mật khẩu chữ trần", không bao giờ trích đoạn khớp đó ra.
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Dict, Optional

__all__ = [
    "TEN_LSA_SECRET", "KHOA_WINLOGON", "DUONG_SELFHEAL_MAC_DINH",
    "doc_trang_thai", "kiem_selfheal", "dat_tu_dang_nhap",
]

#: Tên khoá LSA secret Winlogon tự tìm khi registry DefaultPassword trống —
#: KHÔNG tự đặt tên khác, đổi tên là Windows không tìm thấy, autologon hỏng.
TEN_LSA_SECRET = "DefaultPassword"

KHOA_WINLOGON = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

DUONG_SELFHEAL_MAC_DINH = r"C:\ProgramData\VMSetup\selfheal.ps1"

#: Quyền LSA tối thiểu cho từng việc (xem MSDN "Policy Object Access Rights").
_POLICY_CREATE_SECRET = 0x00000010
_POLICY_GET_PRIVATE_INFORMATION = 0x00000004

#: `ERROR_NOT_FOUND` (Win32) — LsaNtStatusToWinError trả mã này khi secret
#: chưa từng tồn tại (STATUS_OBJECT_NAME_NOT_FOUND phía NTSTATUS).
_WIN32_ERROR_NOT_FOUND = 1168

DocDangKy = Callable[[], Dict[str, Any]]
GhiDangKy = Callable[..., None]
LuuLsa = Callable[[str, str], None]
CoLsa = Callable[[str], Optional[bool]]


# ═══════════════════════════════════════════════════════════════════════════
# Registry Winlogon — ĐỌC (không lộ giá trị mật khẩu) + GHI
# ═══════════════════════════════════════════════════════════════════════════


def _doc_dang_ky_that() -> Dict[str, Any]:
    """Đọc `Winlogon` thật. CHỈ trả bool "có mật khẩu chữ trần" — KHÔNG BAO
    GIỜ trả giá trị `DefaultPassword` thật."""
    try:
        import winreg  # noqa: PLC0415 — chỉ có trên Windows, và chỉ cần ở nhánh thật
    except ImportError:
        return {"auto_admin_logon": None, "default_username": None,
                "default_domain": None, "co_mat_khau_tran": None}

    def _doc_1(khoa, ten: str) -> Optional[str]:
        try:
            gia_tri, _kieu = winreg.QueryValueEx(khoa, ten)
            return gia_tri
        except FileNotFoundError:
            return None

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, KHOA_WINLOGON) as khoa:
            auto = _doc_1(khoa, "AutoAdminLogon")
            user = _doc_1(khoa, "DefaultUserName")
            domain = _doc_1(khoa, "DefaultDomainName")
            mat_khau_tran = _doc_1(khoa, "DefaultPassword")
    except OSError:
        return {"auto_admin_logon": None, "default_username": None,
                "default_domain": None, "co_mat_khau_tran": None}

    return {
        "auto_admin_logon": str(auto).strip() == "1" if auto is not None else False,
        "default_username": str(user) if user is not None else "",
        "default_domain": str(domain) if domain is not None else "",
        "co_mat_khau_tran": bool(mat_khau_tran is not None and str(mat_khau_tran).strip()),
    }


def _ghi_dang_ky_that(*, user: str, domain: Optional[str], xoa_mat_khau_tran: bool) -> None:
    """Ghi `AutoAdminLogon=1` + `DefaultUserName`(+`DefaultDomainName`), và
    xoá `DefaultPassword` chữ trần nếu `xoa_mat_khau_tran`. Cần quyền Admin."""
    import winreg  # noqa: PLC0415

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, KHOA_WINLOGON, 0, winreg.KEY_SET_VALUE) as khoa:
        winreg.SetValueEx(khoa, "AutoAdminLogon", 0, winreg.REG_SZ, "1")
        winreg.SetValueEx(khoa, "DefaultUserName", 0, winreg.REG_SZ, str(user))
        if domain is not None:
            winreg.SetValueEx(khoa, "DefaultDomainName", 0, winreg.REG_SZ, str(domain))
        if xoa_mat_khau_tran:
            try:
                winreg.DeleteValue(khoa, "DefaultPassword")
            except FileNotFoundError:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# LSA secret — ctypes advapi32 (LsaOpenPolicy/LsaStorePrivateData/
# LsaRetrievePrivateData/LsaFreeMemory/LsaClose/LsaNtStatusToWinError)
# ═══════════════════════════════════════════════════════════════════════════


def _mo_policy_that(quyen: int):
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    class _LsaObjectAttributes(ctypes.Structure):
        _fields_ = [("Length", wintypes.ULONG),
                    ("RootDirectory", wintypes.HANDLE),
                    ("ObjectName", ctypes.c_void_p),
                    ("Attributes", wintypes.ULONG),
                    ("SecurityDescriptor", wintypes.LPVOID),
                    ("SecurityQualityOfService", wintypes.LPVOID)]

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    oa = _LsaObjectAttributes()
    oa.Length = ctypes.sizeof(oa)
    handle = wintypes.HANDLE()
    trang_thai = advapi32.LsaOpenPolicy(None, ctypes.byref(oa), quyen, ctypes.byref(handle))
    if trang_thai != 0:
        ma_loi = advapi32.LsaNtStatusToWinError(trang_thai)
        raise OSError("LsaOpenPolicy lỗi (mã Windows {0}) — cần chạy bằng quyền Administrator."
                      .format(ma_loi))
    return advapi32, handle


def _lsa_chuoi(ctypes_mod, wintypes_mod, gia_tri: str):
    buf = ctypes_mod.create_unicode_buffer(gia_tri)
    dai = len(gia_tri) * ctypes_mod.sizeof(ctypes_mod.c_wchar)

    class _LsaUnicodeString(ctypes_mod.Structure):
        _fields_ = [("Length", wintypes_mod.USHORT),
                    ("MaximumLength", wintypes_mod.USHORT),
                    ("Buffer", wintypes_mod.LPWSTR)]

    s = _LsaUnicodeString()
    s.Length = dai
    s.MaximumLength = dai + ctypes_mod.sizeof(ctypes_mod.c_wchar)
    s.Buffer = ctypes_mod.cast(buf, wintypes_mod.LPWSTR)
    return s, buf  # giữ `buf` sống tới hết lời gọi API — tránh bị GC sớm


def _luu_lsa_secret_that(ten: str, gia_tri: str) -> None:
    """Lưu MỘT LSA secret. Ném `OSError` nếu hỏng — KHÔNG BAO GIỜ được gọi
    trong phiên này (chỉ dùng qua test mock), xem docstring đầu tệp."""
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    advapi32, handle = _mo_policy_that(_POLICY_CREATE_SECRET)
    try:
        s_ten, _giu_ten = _lsa_chuoi(ctypes, wintypes, ten)
        s_gt, _giu_gt = _lsa_chuoi(ctypes, wintypes, gia_tri)
        trang_thai = advapi32.LsaStorePrivateData(handle, ctypes.byref(s_ten), ctypes.byref(s_gt))
        if trang_thai != 0:
            ma_loi = advapi32.LsaNtStatusToWinError(trang_thai)
            raise OSError("LsaStorePrivateData lỗi (mã Windows {0}).".format(ma_loi))
    finally:
        advapi32.LsaClose(handle)


def _co_lsa_secret_that(ten: str) -> Optional[bool]:
    """`True`/`False` nếu biết chắc, `None` nếu không đọc được (thiếu quyền...).

    Win32 không có API "chỉ hỏi có hay không" — `LsaRetrievePrivateData` phải
    lấy giá trị thật vào bộ nhớ tiến trình để trả STATUS_SUCCESS; hàm này giải
    phóng NGAY bằng `LsaFreeMemory` và không bao giờ đọc/trả nội dung đó.
    """
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    try:
        advapi32, handle = _mo_policy_that(_POLICY_GET_PRIVATE_INFORMATION)
    except OSError:
        return None
    try:
        s_ten, _giu_ten = _lsa_chuoi(ctypes, wintypes, ten)
        con_tro = ctypes.c_void_p()
        trang_thai = advapi32.LsaRetrievePrivateData(handle, ctypes.byref(s_ten), ctypes.byref(con_tro))
        if trang_thai == 0:
            advapi32.LsaFreeMemory(con_tro)  # nội dung KHÔNG được đọc — giải phóng ngay
            return True
        ma_loi = advapi32.LsaNtStatusToWinError(trang_thai)
        if ma_loi == _WIN32_ERROR_NOT_FOUND:
            return False
        return None  # lỗi khác (quyền...) — không rõ, không đoán bừa
    finally:
        advapi32.LsaClose(handle)


# ═══════════════════════════════════════════════════════════════════════════
# API công khai — đọc trạng thái (chỉ đọc, an toàn chạy thật)
# ═══════════════════════════════════════════════════════════════════════════


def doc_trang_thai(*, doc_dang_ky: Optional[DocDangKy] = None,
                   co_lsa: Optional[CoLsa] = None) -> Dict[str, Any]:
    """Máy đang tự đăng nhập bằng CÁCH NÀO — CHỈ ĐỌC, an toàn gọi thật.

    `phuong_thuc`: `"tat"` (AutoAdminLogon không bật) | `"lsa_secret"` (đúng
    đích, không mật khẩu chữ trần) | `"mat_khau_tran_dang_ky"` (CẢNH BÁO —
    đúng thứ kiểm toán 26/09 tìm thấy) | `"thieu_mat_khau"` (AutoAdminLogon=1
    mà không có mật khẩu nào — Windows sẽ KHÔNG tự đăng nhập được) |
    `"khong_ro"` (không đọc được LSA secret, thường vì thiếu quyền Admin).

    KHÔNG hàm nào ở đây trả về giá trị mật khẩu thật — xem docstring đầu tệp.
    """
    doc_dang_ky = doc_dang_ky or _doc_dang_ky_that
    co_lsa = co_lsa or _co_lsa_secret_that

    dk = doc_dang_ky()
    bat = bool(dk.get("auto_admin_logon"))
    lsa = co_lsa(TEN_LSA_SECRET) if bat else None

    if not bat:
        phuong_thuc = "tat"
    elif lsa:
        phuong_thuc = "lsa_secret"
    elif dk.get("co_mat_khau_tran"):
        phuong_thuc = "mat_khau_tran_dang_ky"
    elif lsa is False:
        phuong_thuc = "thieu_mat_khau"
    else:
        phuong_thuc = "khong_ro"

    return {
        "auto_admin_logon": bat,
        "default_username": dk.get("default_username") or "",
        "default_domain": dk.get("default_domain") or "",
        "co_mat_khau_tran_dang_ky": dk.get("co_mat_khau_tran"),
        "co_lsa_secret": lsa,
        "phuong_thuc": phuong_thuc,
    }


# ═══════════════════════════════════════════════════════════════════════════
# selfheal.ps1 — chỉ báo có/không, KHÔNG in mật khẩu
# ═══════════════════════════════════════════════════════════════════════════

#: `-Name DefaultPassword ... -Value '...'`/`"..."` trên cùng một dòng — đúng
#: khuôn PowerShell `Set-ItemProperty`/`New-ItemProperty` hay dùng để ghi
#: registry, và đúng khuôn thật đo được trên VPS này 29/09/2026 (không trích
#: nguyên dòng vào đây — xem lời hứa "không in mật khẩu" đầu tệp).
_RE_SET_DEFAULT_PASSWORD = re.compile(
    r"(?i)-Name\s+DefaultPassword\b[^\n]*-Value\s+['\"][^'\"]+['\"]")
#: `net user <tên> <mật khẩu chữ trần>` — cách khác hay gặp để đặt mật khẩu.
_RE_NET_USER = re.compile(r"(?i)\bnet(?:\.exe)?\s+user\s+\S+\s+\S")
#: Gán chuỗi trực tiếp cho một biến có "pass"/"pwd" trong tên — heuristic rộng,
#: có thể khớp nhầm (vd biến `$passthrough`) nên CHỈ dùng làm tín hiệu PHỤ.
_RE_GAN_BIEN_MAT_KHAU = re.compile(r"(?i)\$\w*(?:pass|pwd)\w*\s*=\s*['\"][^'\"]")
#: `ConvertTo-SecureString -AsPlainText` — nếu có, chuỗi đi vào SecureString
#: ngay (không hẳn là lưu trần lâu dài), nên KHÔNG tự tính là "chữ trần" chỉ
#: vì có mặt heuristic phụ ở trên khi dòng này cũng xuất hiện.
_RE_SECURE_STRING = re.compile(r"(?i)ConvertTo-SecureString")


def kiem_selfheal(*, duong: str = DUONG_SELFHEAL_MAC_DINH) -> Dict[str, Any]:
    """`{"co_tep": bool, "co_mat_khau_tran": bool|None}` — CHỈ đọc, không sửa,
    không bao giờ trích nội dung đã khớp ra kết quả trả về."""
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            noi_dung = tep.read()
    except OSError:
        return {"co_tep": False, "co_mat_khau_tran": None}

    khop_chac_chan = bool(_RE_SET_DEFAULT_PASSWORD.search(noi_dung)
                          or _RE_NET_USER.search(noi_dung))
    khop_phu = bool(_RE_GAN_BIEN_MAT_KHAU.search(noi_dung) and not _RE_SECURE_STRING.search(noi_dung))
    return {"co_tep": True, "co_mat_khau_tran": khop_chac_chan or khop_phu}


# ═══════════════════════════════════════════════════════════════════════════
# Ghi — CHỈ viết + test mock, KHÔNG chạy thật ở bản này (xem docstring đầu tệp)
# ═══════════════════════════════════════════════════════════════════════════


def dat_tu_dang_nhap(
    user: str,
    mat_khau: str,
    *,
    mien: Optional[str] = None,
    luu_lsa: Optional[LuuLsa] = None,
    ghi_dang_ky: Optional[GhiDangKy] = None,
) -> Dict[str, Any]:
    """Chuyển máy sang tự đăng nhập bằng LSA secret, xoá `DefaultPassword`
    chữ trần. Thứ tự CỐ Ý: lưu LSA TRƯỚC, xoá chữ trần SAU (xem docstring đầu
    tệp, mục "THỨ TỰ GHI"). Lưu LSA hỏng thì ném lỗi NGAY, KHÔNG đụng registry
    — máy vẫn còn `DefaultPassword` chữ trần cũ, vẫn tự đăng nhập được (kém an
    toàn hơn, nhưng KHÔNG BAO GIỜ mất khả năng tự đăng nhập).

    ⚠ CHƯA CHẠY THẬT — `luu_lsa`/`ghi_dang_ky` PHẢI được truyền (test mock)
    tới khi chủ dự án xác nhận chạy thật, xem `GHI-CHU.md`.
    """
    ten_nguoi_dung = str(user or "").strip()
    if not ten_nguoi_dung:
        raise ValueError("Thiếu tên người dùng.")
    if not mat_khau:
        raise ValueError("Thiếu mật khẩu.")

    luu_lsa = luu_lsa or _luu_lsa_secret_that
    ghi_dang_ky = ghi_dang_ky or _ghi_dang_ky_that

    luu_lsa(TEN_LSA_SECRET, mat_khau)
    ghi_dang_ky(user=ten_nguoi_dung, domain=mien, xoa_mat_khau_tran=True)

    return {"da_luu_lsa": True, "da_xoa_mat_khau_tran": True,
           "user": ten_nguoi_dung, "domain": str(mien) if mien else ""}


# ── `python -m core.tu_dang_nhap`: đọc thật, chỉ in ra (không mật khẩu) ─────

_NHAN_PHUONG_THUC = {
    "tat": "TẮT (AutoAdminLogon không bật)",
    "lsa_secret": "LSA secret (đúng đích, không mật khẩu chữ trần)",
    "mat_khau_tran_dang_ky": "MẬT KHẨU CHỮ TRẦN trong registry — NÊN CHUYỂN sang LSA secret",
    "thieu_mat_khau": "AutoAdminLogon bật nhưng KHÔNG có mật khẩu nào — sẽ không tự đăng nhập được",
    "khong_ro": "không đọc được LSA secret (thường vì thiếu quyền Administrator)",
}


def _main() -> int:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

    tt = doc_trang_thai()
    print("═══ Tự đăng nhập Windows (chỉ đọc — không in mật khẩu) ═══")
    print("AutoAdminLogon: {0}".format("BẬT" if tt["auto_admin_logon"] else "tắt"))
    print("Tên đăng nhập: {0}".format(tt["default_username"] or "(trống)"))
    print("Cách đang dùng: {0}".format(_NHAN_PHUONG_THUC.get(tt["phuong_thuc"], tt["phuong_thuc"])))

    sh = kiem_selfheal()
    print("")
    print("selfheal.ps1 ({0}): {1}".format(DUONG_SELFHEAL_MAC_DINH,
                                           "CÓ" if sh["co_tep"] else "không có"))
    if sh["co_tep"]:
        if sh["co_mat_khau_tran"] is True:
            print("  → có vẻ CHỨA mật khẩu chữ trần (không in ra nội dung).")
        elif sh["co_mat_khau_tran"] is False:
            print("  → không thấy dấu hiệu chứa mật khẩu chữ trần.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
