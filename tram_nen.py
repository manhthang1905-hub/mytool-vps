"""CLI: trạm nhận 8765 chạy NỀN — không mở giao diện, không cần cửa sổ nào.

    python tram_nen.py                 bật trạm và giữ tiến trình sống
    python tram_nen.py --canh          chó giữ nhà: kiểm mãi, trạm chết thì bật lại
    python tram_nen.py --kiem          kiểm MỘT lượt rồi thoát (lịch Windows gọi)
    python tram_nen.py --tat           bảo bản nền đang chạy tự lui (trả cổng)
    python tram_nen.py --cong 8765     đổi cổng (mặc định 8765)

Vì sao có tệp này: tới 19/09/2026 trạm HTTP chỉ được dựng trong
`ui_qt/trang_chi_so_ytb.py`, tức nó sống nhờ tiến trình Qt của MyTool. Cửa sổ
tắt là cổng chết, mà `vm/nguon_tool.py` chỉ lấy kế hoạch đăng qua
`GET /ke-hoach?kenh=X` — trạm chết thì video sản xuất xong nằm chết trong thư
mục, không lỗi, không cảnh báo, không bao giờ lên sóng (đo thật 21/09/2026).

Luật đầy đủ về nhường cổng, dấu tích, nhật ký: `core/tram_nen.py`; về chó giữ
nhà và lịch Windows: `core/canh_tram.py` và `core/lich_tu_chay.py`.

Chạy được bằng `pythonw.exe` (không console). Mọi dòng thông báo đi qua
`core.tram_nen.bo_log` — nó tự ghi đĩa và chỉ `print()` khi máy THẬT SỰ có
console, đúng nếp `tu_chay.py --tat-ca`.
"""

from __future__ import annotations

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Console Windows mặc định là cp1252/cp437 — in một chữ có dấu ra đó là
# `UnicodeEncodeError` và kịch bản chết ngay ở dòng `--help` (đo 21/09/2026).
# Cùng chốt đã có ở `core/chi_so_ytb/gom.py`: `pythonw.exe` không có console
# nên `sys.stdout` có thể là `None`, phải chặn trước khi đụng tới.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):
        pass

from core import canh_tram, tram_nen  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Trạm nhận 8765 chạy nền, không cần giao diện Qt.")
    nhom = ap.add_mutually_exclusive_group()
    nhom.add_argument("--canh", action="store_true",
                      help="Chó giữ nhà: kiểm định kỳ, trạm chết thì bật lại (chạy mãi).")
    nhom.add_argument("--kiem", action="store_true",
                      help="Kiểm MỘT lượt rồi thoát — dạng lịch Windows gọi mỗi vài phút.")
    nhom.add_argument("--tat", action="store_true",
                      help="Bảo bản trạm nền đang chạy tự lui, trả cổng lại cho giao diện.")
    ap.add_argument("--cong", type=int, default=tram_nen.CONG_MAC_DINH,
                    help="Cổng nghe (mặc định {0}).".format(tram_nen.CONG_MAC_DINH))
    ap.add_argument("--nhip", type=float, default=canh_tram.NHIP_CANH_GIAY,
                    help="Chỉ với --canh: bao nhiêu giây một lượt kiểm.")
    args = ap.parse_args(argv)

    ghi = tram_nen.bo_log(BASE_DIR)

    if args.tat:
        ok, loi_nhan = tram_nen.xin_nhuong(BASE_DIR)
        ghi("--tat: " + loi_nhan)
        return 0 if ok else 1

    if args.kiem:
        song, loi_nhan = canh_tram.mot_luot(BASE_DIR, args.cong, ghi=ghi)
        # Mã thoát là thứ Task Scheduler ghi lại vào cột "Last Result" — 0 nghĩa
        # là "sau lượt này đã có trạm phục vụ", khác 0 là "vẫn chưa ai nghe".
        return 0 if song else 1

    if args.canh:
        return canh_tram.canh(BASE_DIR, args.cong, nhip=args.nhip, ghi=ghi)

    return tram_nen.chay(BASE_DIR, args.cong, ghi=ghi)


if __name__ == "__main__":
    sys.exit(main())
