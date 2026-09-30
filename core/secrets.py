"""Kho bí mật dùng chung: khoá API, token đăng nhập, mật khẩu máy riêng...

Bất cứ chỗ nào trong tool cần cất một cục JSON mà KHÔNG được nằm trần trên đĩa
(khoá API, mật khẩu RDP...) đều đi qua :class:`SecretStore` ở đây, thay vì tự
mở file JSON thường. Hai người gọi hiện tại: :mod:`core.config` (khoá API,
refresh token) và :mod:`core.vps_rieng` (mật khẩu máy ảo tự thêm).

═══ VÌ SAO DPAPI, VÀ VÌ SAO CHỈ BẢO VỆ CÁI KHOÁ CHỨ KHÔNG PHẢI CẢ CỤC DỮ LIỆU ═══

`CryptProtectData`/`CryptUnprotectData` của Windows mã hoá bằng một khoá gắn
với TÀI KHOẢN NGƯỜI DÙNG HIỆN TẠI trên ĐÚNG MÁY NÀY (DPAPI) — không cần tool tự
quản lý mật khẩu chủ. Chép file sang máy khác hay tài khoản Windows khác thì
giải mã hỏng, đúng như mô tả trong README.md.

DPAPI qua `ctypes` xử lý buffer nhỏ (một khoá 44 byte) thì gọn và ít chỗ sai;
bắt nó ôm cả cục JSON (có thể vài KB, danh sách nhiều máy riêng) thì phải tự lo
cấp phát/giải phóng bộ nhớ native cho dữ liệu lớn — vừa dễ rò rỉ vừa khó test.
Nên: sinh một khoá Fernet ngẫu nhiên, mã hoá DỮ LIỆU bằng `cryptography`
(thư viện thuần Python, đã có sẵn trong requirements.txt), rồi chỉ nhờ DPAPI
bảo vệ đúng cái KHOÁ đó. Mất khoá là mất tất cả — DPAPI lo đúng phần khó nhất
(gắn với người dùng+máy), Fernet lo đúng phần còn lại (mã hoá dữ liệu, kiểm tra
toàn vẹn, không giới hạn kích thước).

═══ MÁY KHÔNG PHẢI WINDOWS ═══

`encryption_available()` trả `False`. Kho rơi về lưu THẲNG dạng chữ (không mã
hoá) và bật cờ cảnh báo (:attr:`SecretStore.warning`) để nơi gọi hiện lên màn
hình — thà chạy được ở chế độ kém an toàn hơn còn hơn tool không mở nổi trên
máy phát triển/CI không phải Windows. Bộ test chạy trên máy nào cũng qua được
vì mọi chỗ đòi mã hoá thật đều tự bỏ qua khi `encryption_available()` là False.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import sys
from ctypes import wintypes
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

__all__ = ["SecretStore", "secrets_path_for", "encryption_available"]

#: Tên file kho bí mật mặc định, nằm cạnh `config.json` — CONTRACT giữ nguyên
#: tên này vì `.gitignore` và `core/package.py` (gói gửi khách) đều chặn đích
#: danh chữ này.
SECRETS_FILENAME = "secrets.json"

#: Phiên bản định dạng file. `0` = lưu chữ thường (máy không mã hoá được),
#: `1` = khoá Fernet được DPAPI bảo vệ. Giữ số này để sau có nâng cấp cách mã
#: hoá thì bản cũ vẫn đọc được (đọc theo `v`, không đoán theo hình dạng file).
_PHIEN_BAN_CHU_THUONG = 0
_PHIEN_BAN_DPAPI_FERNET = 1


def secrets_path_for(config_path: str) -> str:
    """`.../config.json` → `.../secrets.json` (cùng thư mục, tên cố định).

    Nhận đường dẫn `config.json` thay vì một thư mục để nơi gọi khỏi phải tách
    thư mục ra tay — `config.py` vốn đã cầm sẵn đường dẫn đầy đủ của
    `config.json`.
    """
    folder = os.path.dirname(os.path.abspath(config_path))
    return os.path.join(folder, SECRETS_FILENAME)


def encryption_available() -> bool:
    """Máy này có DPAPI không. Chỉ Windows có — dùng để quyết định mã hoá thật
    hay lưu chữ thường kèm cảnh báo."""
    return sys.platform.startswith("win")


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.c_void_p)]


def _khai_bao_kieu_ham_win32() -> None:
    """Ép kiểu tham số của các hàm Win32 dùng chung.

    Không khai `argtypes`/`restype` thì `ctypes` mặc định coi con trỏ là
    `c_int` (32-bit) — trên Windows 64-bit, địa chỉ bộ nhớ vượt quá 32-bit
    làm `LocalFree` ném `ArgumentError: int too long to convert`. Chạy một
    lần khi nạp module là đủ, khỏi lặp lại ở từng lời gọi.
    """
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p
    for ten in ("CryptProtectData", "CryptUnprotectData"):
        ham = getattr(ctypes.windll.crypt32, ten)
        ham.argtypes = [
            ctypes.POINTER(_DATA_BLOB), ctypes.c_wchar_p, ctypes.POINTER(_DATA_BLOB),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DATA_BLOB),
        ]
        ham.restype = wintypes.BOOL


if sys.platform.startswith("win"):
    _khai_bao_kieu_ham_win32()


def _dpapi_protect(du_lieu: bytes) -> bytes:
    """Mã hoá `du_lieu` bằng DPAPI, gắn với tài khoản Windows hiện tại."""
    vao = ctypes.create_string_buffer(du_lieu, len(du_lieu))
    blob_vao = _DATA_BLOB(len(du_lieu), ctypes.cast(vao, ctypes.c_void_p))
    blob_ra = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_vao), None, None, None, None, 0, ctypes.byref(blob_ra)
    )
    if not ok:
        raise OSError("CryptProtectData thất bại (mã {0})".format(ctypes.get_last_error()))
    try:
        return ctypes.string_at(blob_ra.pbData, blob_ra.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_ra.pbData)


def _dpapi_unprotect(du_lieu: bytes) -> bytes:
    """Giải mã cục DPAPI. Sai tài khoản/máy hoặc dữ liệu hỏng → ném `OSError`."""
    vao = ctypes.create_string_buffer(du_lieu, len(du_lieu))
    blob_vao = _DATA_BLOB(len(du_lieu), ctypes.cast(vao, ctypes.c_void_p))
    blob_ra = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_vao), None, None, None, None, 0, ctypes.byref(blob_ra)
    )
    if not ok:
        raise OSError("CryptUnprotectData thất bại (mã {0})".format(ctypes.get_last_error()))
    try:
        return ctypes.string_at(blob_ra.pbData, blob_ra.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_ra.pbData)


class SecretStore:
    """Một file JSON bí mật, mã hoá theo máy khi máy hỗ trợ DPAPI.

    `load()`/`save()` không bao giờ ném lỗi ra ngoài vì mất/hỏng kho bí mật
    không nên chặn cả tool — nơi gọi đọc :attr:`warning` để biết có chuyện bất
    thường và tự quyết định hiện gì lên màn hình (xem `core.config.load_config`).
    """

    def __init__(self, path: str):
        self.path = path
        #: Rỗng = bình thường; có chữ = bí mật đang KHÔNG được mã hoá (máy
        #: không hỗ trợ DPAPI) hoặc lần đọc/ghi gần nhất bị hỏng.
        self.warning = ""

    def _canh_bao_khong_ma_hoa(self) -> str:
        return (
            "Máy này không mã hoá được kho bí mật (chỉ Windows mới có DPAPI). "
            "\"{0}\" đang lưu dạng chữ thường — đừng chép file này cho ai.".format(self.path)
        )

    def load(self) -> Dict[str, Any]:
        """Đọc kho. Thiếu file → `{}` không cảnh báo (lần chạy đầu là chuyện
        bình thường). Hỏng/giải mã không nổi → `{}` kèm cảnh báo."""
        self.warning = ""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as tep:
                goi = json.load(tep)
        except (OSError, ValueError):
            self.warning = (
                "Kho bí mật \"{0}\" bị hỏng, không đọc được. Đăng nhập lại, "
                "tool sẽ ghi kho mới.".format(self.path)
            )
            return {}

        if not isinstance(goi, dict):
            self.warning = (
                "Kho bí mật \"{0}\" sai định dạng. Đăng nhập lại, tool sẽ ghi "
                "kho mới.".format(self.path)
            )
            return {}

        phien_ban = goi.get("v")

        if phien_ban == _PHIEN_BAN_CHU_THUONG:
            du_lieu = goi.get("du_lieu")
            if not isinstance(du_lieu, dict):
                return {}
            # Dù máy này mã hoá được hay không, file ĐANG nằm dạng chữ thường
            # (chép từ máy khác, hoặc lần ghi trước lỗi DPAPI) — vẫn đọc được,
            # chỉ cảnh báo để nơi gọi hiện lên màn hình.
            self.warning = self._canh_bao_khong_ma_hoa()
            return du_lieu

        if phien_ban == _PHIEN_BAN_DPAPI_FERNET:
            if not encryption_available():
                self.warning = (
                    "Kho bí mật \"{0}\" được mã hoá bằng DPAPI của Windows, "
                    "nhưng máy này không phải Windows nên không đọc được. "
                    "Đăng nhập lại.".format(self.path)
                )
                return {}
            try:
                khoa = _dpapi_unprotect(base64.b64decode(goi["khoa"]))
                thanh_van = Fernet(khoa).decrypt(goi["du_lieu"].encode("ascii"))
                du_lieu = json.loads(thanh_van.decode("utf-8"))
            except (KeyError, ValueError, TypeError, OSError, InvalidToken):
                self.warning = (
                    "Kho bí mật \"{0}\" không giải mã được — có thể đã chép từ "
                    "máy khác hoặc tài khoản Windows khác. Đăng nhập lại, tool "
                    "sẽ ghi kho mới.".format(self.path)
                )
                return {}
            if not isinstance(du_lieu, dict):
                return {}
            return du_lieu

        # `v` lạ (file từ bản tool tương lai?) — không đoán mò, coi như hỏng.
        self.warning = (
            "Kho bí mật \"{0}\" ghi bởi một bản tool khác, không đọc được ở "
            "đây. Đăng nhập lại, tool sẽ ghi kho mới.".format(self.path)
        )
        return {}

    def save(self, data: Dict[str, Any]) -> None:
        """Ghi kho. Luôn qua file tạm rồi `os.replace` — mất điện giữa chừng
        không để lại file dở dang đè lên bản cũ còn tốt."""
        self.warning = ""
        if encryption_available():
            khoa = Fernet.generate_key()
            ma_hoa = Fernet(khoa).encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            try:
                khoa_bao_ve = _dpapi_protect(khoa)
            except OSError:
                self.warning = self._canh_bao_khong_ma_hoa()
                goi: Dict[str, Any] = {"v": _PHIEN_BAN_CHU_THUONG, "du_lieu": data}
            else:
                goi = {
                    "v": _PHIEN_BAN_DPAPI_FERNET,
                    "khoa": base64.b64encode(khoa_bao_ve).decode("ascii"),
                    "du_lieu": ma_hoa.decode("ascii"),
                }
        else:
            self.warning = self._canh_bao_khong_ma_hoa()
            goi = {"v": _PHIEN_BAN_CHU_THUONG, "du_lieu": data}

        folder = os.path.dirname(os.path.abspath(self.path))
        if folder:
            os.makedirs(folder, exist_ok=True)
        temp_path = self.path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as tep:
            json.dump(goi, tep, ensure_ascii=False)
        os.replace(temp_path, self.path)

    def clear(self) -> None:
        """Xoá kho. Đã xoá rồi hoặc chưa từng có thì im lặng — đây là hành
        động dọn dẹp, không phải chỗ cần báo lỗi."""
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
