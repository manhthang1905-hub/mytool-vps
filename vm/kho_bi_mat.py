"""KHO BÍ MẬT của VPS (05/10/2026) — tài khoản Google từng kênh (email, mật khẩu, khoá TOTP 2FA).

Mã hoá bằng Windows DPAPI (CryptProtectData, phạm vi tài khoản Windows hiện tại): chỉ đúng người dùng Windows
này TRÊN ĐÚNG MÁY NÀY giải mã được — chép tệp sang máy khác là rác. Tệp dữ liệu ở `<gốc tool>/bi-mat/` (gốc bị
.gitignore danh-sách-trắng chặn → KHÔNG BAO GIỜ lên kho chung). Mã này không chứa bí mật nào.

Dùng (chỉ đọc khi cần — đăng nhập lại Google lúc lấy lại token, xác minh 2FA):
    from kho_bi_mat import tai_khoan, ma_2fa
    tk = tai_khoan("TL1-T7")      # {"email","mat_khau","totp"} hoặc {}
    ma = ma_2fa("TL1-T7")         # mã 6 số hiện tại, "" nếu không có khoá
KHÔNG BAO GIỜ in/ghi log giá trị trả về.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import time

GOC_TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THU_MUC = os.path.join(GOC_TOOL, "bi-mat")
TEP = os.path.join(THU_MUC, "tai-khoan.dpapi")
_MO_TA = "MyTool tai khoan kenh"


def _ma_hoa(du: bytes) -> bytes:
    import win32crypt  # noqa: PLC0415 — pywin32 có sẵn trên VPS
    return win32crypt.CryptProtectData(du, _MO_TA, None, None, None, 0)


def _giai_ma(du: bytes) -> bytes:
    import win32crypt  # noqa: PLC0415
    return win32crypt.CryptUnprotectData(du, None, None, None, 0)[1]


def doc_tat_ca(tep: str = None) -> dict:
    """{kênh: {email, mat_khau, totp}} — không có tệp / hỏng → {}."""
    try:
        with open(tep or TEP, "rb") as f:
            return json.loads(_giai_ma(f.read()).decode("utf-8")) or {}
    except Exception:  # noqa: BLE001 — không bao giờ ném chi tiết (có thể dính bí mật)
        return {}


def ghi_tat_ca(du: dict, tep: str = None) -> None:
    tep = tep or TEP
    os.makedirs(os.path.dirname(tep), exist_ok=True)
    tam = tep + ".tam"
    with open(tam, "wb") as f:
        f.write(_ma_hoa(json.dumps(du, ensure_ascii=False).encode("utf-8")))
    os.replace(tam, tep)


def chuan_hoa_totp(khoa: str) -> str:
    """Khoá TOTP base32: bỏ dấu cách/gạch, viết hoa (Google hiển thị 'abcd efgh …')."""
    return "".join(ch for ch in str(khoa or "") if ch.isalnum()).upper()


def them_kenh(kenh: str, email: str, mat_khau: str, totp: str = "", tep: str = None) -> None:
    du = doc_tat_ca(tep)
    du[kenh] = {"email": str(email).strip(), "mat_khau": str(mat_khau), "totp": chuan_hoa_totp(totp)}
    ghi_tat_ca(du, tep)


def tai_khoan(kenh: str, tep: str = None) -> dict:
    return dict(doc_tat_ca(tep).get(kenh) or {})


def ma_totp(khoa: str, luc: float = None, buoc: int = 30, so: int = 6) -> str:
    """RFC 6238 (HMAC-SHA1) — hàm thuần."""
    k = chuan_hoa_totp(khoa)
    if not k:
        return ""
    k += "=" * (-len(k) % 8)
    bi = base64.b32decode(k, casefold=True)
    dem = int((time.time() if luc is None else luc) // buoc)
    h = hmac.new(bi, struct.pack(">Q", dem), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** so)).zfill(so)


def ma_2fa(kenh: str, tep: str = None) -> str:
    return ma_totp(tai_khoan(kenh, tep).get("totp", ""))


def co_tai_khoan(kenh: str, tep: str = None) -> dict:
    """Chỉ báo CÓ/KHÔNG từng trường (an toàn để in): {email: bool, mat_khau: bool, totp: bool}."""
    t = tai_khoan(kenh, tep)
    return {k: bool(t.get(k)) for k in ("email", "mat_khau", "totp")}
