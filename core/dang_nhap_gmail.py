"""core/dang_nhap_gmail.py — đăng nhập Gmail của một kênh bằng gói `gmail-login-skill` (workspace/).

Luồng: lấy email/mật khẩu/2FA của kênh từ kho mã hoá (`vm/kho_bi_mat.py`) → chạy skill đăng nhập vào ĐÚNG hồ sơ
user-data của Chrome Portable kênh (`<cha>\\<MÃ>\\Data\\profile`) → cookie ghi thẳng vào hồ sơ đó. Sau đó
`mo_kenh.chrome_da_dang_nhap` thấy `LOGIN_INFO` và luồng mở kênh đi tiếp như thường.

Quy tắc an toàn:
- KHÔNG chạy khi Chrome của kênh đang mở (tránh khoá hồ sơ và chạm trình duyệt đang đăng video).
- KHÔNG bao giờ in/ghi mật khẩu, mã 2FA, cookie. Chỉ trả mã kết quả + lý do ngắn.
- Mật khẩu đi vào skill qua stdin JSON, không qua tham số dòng lệnh (không lộ trong danh sách tiến trình).
- Gặp CAPTCHA / xác minh → dừng, trả `captcha`/`can_xac_minh` để người xử lý; không thử lại mù.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from typing import Any, Callable, Dict, Optional

GOI_SKILL = os.path.join("workspace", "gmail-login-skill")
THU_MUC_HO_SO = os.path.join("workspace", "gmail-login", "ho_so")
HET_GIO_GIAY = 900


def duong_python_skill(goc: str) -> str:
    """Python của gói skill: `.venv` riêng nếu đã cài (cai_dat.bat), không thì Python đang chạy tool."""
    venv = os.path.join(goc, GOI_SKILL, ".venv", "Scripts", "python.exe")
    return venv if os.path.isfile(venv) else sys.executable


def profile_chrome_kenh(exe: str) -> str:
    """Thư mục user-data của Chrome Portable kênh — đúng chỗ `chrome_da_dang_nhap` đọc cookie."""
    return os.path.join(os.path.dirname(os.path.abspath(exe)), "Data", "profile")


def chrome_dang_chay(exe: str) -> bool:
    """Có tiến trình Chrome nào chạy từ thư mục Chrome Portable của kênh không (psutil)."""
    try:
        import psutil  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — không có psutil thì coi như không biết → chặn cho an toàn
        return True
    goc_exe = os.path.dirname(os.path.abspath(exe)).lower()
    for p in psutil.process_iter(["name", "exe"]):
        try:
            if "chrome" not in str(p.info.get("name") or "").lower():
                continue
            duong = str(p.info.get("exe") or "").lower()
            if duong.startswith(goc_exe):
                return True
        except Exception:  # noqa: BLE001 — tiến trình vừa thoát
            continue
    return False


def _lay_dong_json(chu: str) -> Dict[str, Any]:
    for dong in reversed((chu or "").strip().splitlines()):
        dong = dong.strip()
        if dong.startswith("{"):
            try:
                return json.loads(dong)
            except ValueError:
                break
    return {}


def dang_nhap_kenh(goc: str, ma: str, *, chay: Optional[Callable[..., Any]] = None,
                   ghi: Callable[[str], None] = print) -> Dict[str, Any]:
    """Đăng nhập Gmail của kênh `ma`. Trả dict `{"ket_qua", "ly_do", "email_that"}` — KHÔNG có mật khẩu/cookie.

    `chay` (tuỳ chọn, để test): hàm nhận (argv, input_text, cwd, timeout) và trả (returncode, stdout).
    """
    from . import mo_kenh  # noqa: PLC0415 — tránh vòng import lúc nạp module

    vm = os.path.join(goc, "vm")
    if vm not in sys.path:
        sys.path.insert(0, vm)
    import kho_bi_mat  # noqa: PLC0415

    tk = kho_bi_mat.tai_khoan(ma) or {}
    email = str(tk.get("email") or "").strip().lower()
    if not email or not tk.get("mat_khau"):
        return {"ket_qua": "thieu_tai_khoan", "ly_do": "kho chưa có email/mật khẩu cho {0}".format(ma)}

    exe = mo_kenh.thu_muc_chrome(goc, ma)
    if chrome_dang_chay(exe):
        return {"ket_qua": "chrome_dang_chay",
                "ly_do": "Chrome của {0} đang mở — đóng nó rồi đăng nhập lại".format(ma)}

    profile = profile_chrome_kenh(exe)
    os.makedirs(profile, exist_ok=True)
    dau_vao = json.dumps({
        "email": email,
        "mat_khau": str(tk.get("mat_khau") or ""),
        "totp": str(tk.get("totp") or ""),
        "ho_so_dir": os.path.join(goc, THU_MUC_HO_SO),
        "thu_muc_profile": profile,
    }, ensure_ascii=False)
    argv = [duong_python_skill(goc), "-m", "gmail_login", "dang-nhap",
            "--khong-cookie", "--thu-muc-profile", profile]
    cwd = os.path.join(goc, GOI_SKILL)

    # Trình duyệt: chrome.exe trong App của chính Chrome Portable kênh (cùng bản với hồ sơ đã đăng nhập).
    moi_truong = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    chrome_kenh = os.path.join(os.path.dirname(os.path.abspath(exe)), "App", "Chrome-bin", "chrome.exe")
    if os.path.isfile(chrome_kenh):
        moi_truong["GMAIL_LOGIN_CHROME"] = chrome_kenh
    try:
        if chay is None:
            tien = subprocess.run(argv, input=dau_vao, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", cwd=cwd, timeout=HET_GIO_GIAY,
                                  env=moi_truong)
            ma_thoat, out = tien.returncode, tien.stdout
        else:
            ma_thoat, out = chay(argv, dau_vao, cwd, HET_GIO_GIAY)
    except subprocess.TimeoutExpired:
        return {"ket_qua": "hong", "ly_do": "đăng nhập quá {0}s — dừng".format(HET_GIO_GIAY)}
    except OSError as e:
        return {"ket_qua": "hong", "ly_do": "không chạy được gói đăng nhập: {0}".format(type(e).__name__)}

    kq = _lay_dong_json(out)
    if not kq:
        return {"ket_qua": "hong", "ly_do": "gói đăng nhập không trả kết quả (mã thoát {0})".format(ma_thoat)}
    ma_kq = str(kq.get("ket_qua") or "hong")
    that = str(kq.get("email_that") or "").strip().lower()
    if ma_kq == "ok":
        # Hàng rào danh tính: chỉ coi là xong khi Google xác nhận ĐÚNG email của kênh.
        # Cookie của tài khoản khác → sai_danh_tinh; không đọc được danh tính → chưa xác minh (không tự tin).
        if that and that != email:
            ma_kq = "sai_danh_tinh"
        elif not that:
            ma_kq = "chua_xac_minh"
    out_dict = {"ket_qua": ma_kq, "ly_do": str(kq.get("ly_do") or ""), "email_that": that}
    ghi("đăng nhập Gmail {0}: {1}".format(ma, ma_kq))
    return out_dict
