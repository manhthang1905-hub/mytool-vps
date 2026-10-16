"""CLI: vận hành — bật máy lên là mọi thứ tự chạy, chết thì tự hồi phục (luật đầy đủ: `core/van_hanh.py`).

    python van_hanh.py mot-luot [--thu]   một lượt canh (lịch ShopAPI-VanHanh gọi mỗi 5 phút; --thu: CHỈ ĐỌC)
    python van_hanh.py don-khoa [--thu]   dọn khoá cũ theo luật khởi động
    python van_hanh.py dang-ky            đăng ký ShopAPI-VanHanh + ShopAPI-VanHanhLucDangNhap (gọi lại vẫn an toàn)
    python van_hanh.py huy | trang-thai

Điểm vào ở GỐC tool (cạnh `tu_chay.py`, `tram_nen.py`) để tác vụ Windows gọi thẳng `pythonw van_hanh.py` — không cần
`cmd /c cd /d … -m`, không cửa sổ đen chớp mỗi 5 phút. Đừng dời/đổi tên tệp này: lịch Windows trỏ tới nó.
"""

from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.stdout is not None:      # pythonw: không console, sys.stdout = None
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):
        pass

from core import van_hanh  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(van_hanh.main(sys.argv[1:], goc=BASE_DIR))
