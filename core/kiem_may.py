# -*- coding: utf-8 -*-
"""Kiểm một máy đã cài đủ để tự chạy chưa — VIệc 5.1 (`vm/cai_dat_tu_kho.py`),
`workspace/LO-TRINH-PHAT-HANH-V3.md`, tiêu chí "Sẵn sàng v3.0" mục 3.

═══ VÌ SAO CÓ TỆP NÀY ═══

`CAI-DAT-VPS.bat` cài xong thì cần MỘT lệnh trả lời được câu "máy này đã sẵn
sàng tự chạy chưa" mà không cần mở giao diện — người cài (hoặc chủ dự án qua
RDP) gõ:

    python -m core.kiem_may --day-du

và đọc một bảng OK/THIẾU tiếng Việt, thay vì tự đoán qua từng tệp/log.

═══ MỌI HÀM ĐỀU TỰ NUỐT LỖI, KHÔNG NÉM RA NGOÀI ═══

Đây là công cụ CHẨN ĐOÁN — nó không được phép tự sập vì đúng thứ nó đi tìm
(thư viện thiếu, tệp thiếu, cổng không trả lời) là những thứ RẤT CÓ THỂ đang
thiếu thật trên một máy vừa cài. Mỗi mục kiểm trả về `MucKiem` (tên, OK/THIẾU,
ghi chú) chứ không bao giờ để ngoại lệ văng lên `main()`.

═══ `--day-du` MỚI KIỂM TRẠM/AGENT ═══

Trạm (cổng 8765) và phiên kênh (khoá một-mình cổng 8767, `vm/agent.mot_minh`)
chỉ sống khi MyTool đang MỞ. Kiểm nhanh (không `--day-du`) bỏ qua hai mục này
để chạy được ngay sau khi cài xong, TRƯỚC KHI ai mở MyTool lần đầu — không báo
nhầm "THIẾU" cho một thứ chưa tới lúc phải có.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, List, Optional

__all__ = [
    "MucKiem", "kiem_python", "kiem_thu_vien", "kiem_ffmpeg", "kiem_whisper",
    "kiem_vps_json", "kiem_lich", "kiem_tram", "kiem_agent", "kiem_tat_ca",
    "in_bang", "main",
]

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Thư viện phải `import` được để tool chạy đủ chức năng. `websocket-client`
#: (module thật sự tên `websocket`) là mục MỚI thêm 29/09/2026 — thiếu nó thì
#: máy đăng DOM (`vm/may_dang_dom.py`) hỏng trên máy sạch mà không báo rõ vì
#: sao (xem `workspace/LO-TRINH-PHAT-HANH-V3.md`, mục B).
THU_VIEN_CAN = (
    ("PyQt5 (giao diện)", "PyQt5.QtWidgets"),
    ("Pillow (ảnh/QR)", "PIL"),
    ("httpx (gọi máy chủ ShopAPI)", "httpx"),
    ("cryptography (cất khoá API)", "cryptography"),
    ("segno (mã QR nạp tiền)", "segno"),
    ("openpyxl (đọc/ghi Excel)", "openpyxl"),
    ("faster-whisper (phụ đề)", "faster_whisper"),
    ("huggingface_hub (tải mô hình)", "huggingface_hub"),
    ("PyYAML (đọc kenh.yaml)", "yaml"),
    ("websocket-client (máy đăng DOM)", "websocket"),
)


@dataclass
class MucKiem:
    """Một dòng trong bảng kết quả."""

    ten: str
    ok: bool
    ghi_chu: str = field(default="")


def kiem_python() -> MucKiem:
    du = "{0}.{1}.{2} ({3}-bit)".format(
        sys.version_info[0], sys.version_info[1], sys.version_info[2],
        64 if sys.maxsize > 2**32 else 32)
    if sys.version_info < (3, 9):
        return MucKiem("Python", False, du + " — cần bản 3.9 trở lên")
    if sys.maxsize <= 2**32:
        return MucKiem("Python", False, du + " — cần bản 64-bit")
    return MucKiem("Python", True, du)


def kiem_thu_vien() -> List[MucKiem]:
    ket: List[MucKiem] = []
    for nhan, ten_module in THU_VIEN_CAN:
        try:
            importlib.import_module(ten_module)
        except Exception as loi:  # noqa: BLE001 — báo NGUYÊN lý do, không cần biết loại lỗi
            ket.append(MucKiem(nhan, False, "import lỗi: {0}".format(str(loi)[:150])))
        else:
            ket.append(MucKiem(nhan, True))
    return ket


def kiem_ffmpeg(goc: str = GOC) -> MucKiem:
    try:
        from core.dung_video import tim_ffmpeg
        from core.ffmpeg_goi_san import du_dung
    except Exception as loi:  # noqa: BLE001
        return MucKiem("FFmpeg", False, "không nạp được core.dung_video: {0}".format(str(loi)[:150]))
    try:
        duong = tim_ffmpeg(goc)
    except Exception as loi:  # noqa: BLE001
        return MucKiem("FFmpeg", False, "lỗi khi tìm: {0}".format(str(loi)[:150]))
    if not duong:
        return MucKiem("FFmpeg", False,
                       "chưa có bản nào — chạy lại SETUP.bat hoặc mở tab Dựng video một lần khi có mạng")
    try:
        du = du_dung(duong)
    except Exception as loi:  # noqa: BLE001
        return MucKiem("FFmpeg", False, "có bản ở {0} nhưng kiểm lỗi: {1}".format(duong, str(loi)[:120]))
    if not du:
        return MucKiem("FFmpeg", False,
                       "có bản ở {0} nhưng THIẾU bộ lọc cần (libx264/subtitles/...)".format(duong))
    return MucKiem("FFmpeg", True, duong)


def kiem_whisper(goc: str = GOC) -> MucKiem:
    duong = os.path.join(goc, "models", "faster-whisper-small", "config.json")
    if os.path.isfile(duong):
        return MucKiem("Mô hình Whisper (phụ đề)", True, os.path.dirname(duong))
    return MucKiem(
        "Mô hình Whisper (phụ đề)", False,
        "chưa có models/faster-whisper-small/ — máy chỉ IPv6 có thể không tự tải "
        "được (HuggingFace không vào được), xem hướng dẫn chép tay qua RDP trong README-VPS.md")


def kiem_vps_json(goc: str = GOC) -> MucKiem:
    duong = os.path.join(goc, "vps.json")
    if not os.path.isfile(duong):
        return MucKiem("vps.json (cờ chế độ VPS)", False, "chưa có — chạy CAI-DAT-VPS.bat")
    try:
        with open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError) as loi:
        return MucKiem("vps.json (cờ chế độ VPS)", False, "đọc lỗi: {0}".format(loi))
    vm_dir = str(du.get("vm_dir") or "").strip()
    if not vm_dir:
        return MucKiem("vps.json (cờ chế độ VPS)", False, "thiếu khoá 'vm_dir'")
    duong_vm = vm_dir if os.path.isabs(vm_dir) else os.path.join(goc, vm_dir)
    if not os.path.isdir(duong_vm):
        return MucKiem("vps.json (cờ chế độ VPS)", False,
                       "vm_dir trỏ tới thư mục không có: {0}".format(duong_vm))
    return MucKiem("vps.json (cờ chế độ VPS)", True, "vm_dir={0}".format(vm_dir))


def kiem_lich(goc: str = GOC) -> List[MucKiem]:
    try:
        from core import lich_tu_chay
    except Exception as loi:  # noqa: BLE001
        return [MucKiem("Lịch Task Scheduler", False,
                        "không nạp được core.lich_tu_chay: {0}".format(str(loi)[:150]))]
    ket: List[MucKiem] = []
    for nhan, ten_viec in (
        ("Lịch tự chạy hằng ngày (ShopAPI-TuChay)", lich_tu_chay.TEN_VIEC),
        ("Lịch canh trạm (ShopAPI-CanhTram)", lich_tu_chay.TEN_VIEC_CANH),
        ("Lịch canh trạm lúc đăng nhập (ShopAPI-TramLucDangNhap)",
         lich_tu_chay.TEN_VIEC_TRAM_DANG_NHAP),
    ):
        try:
            tt = lich_tu_chay.trang_thai(goc, ten_viec=ten_viec)
        except Exception as loi:  # noqa: BLE001
            ket.append(MucKiem(nhan, False, "lỗi khi đọc: {0}".format(str(loi)[:120])))
            continue
        da = bool(tt.get("da_dang_ky"))
        ket.append(MucKiem(nhan, da,
                           "giờ={0}".format(tt.get("gio") or "?") if da else "chưa đăng ký"))
    return ket


def _http_get(url: str, timeout: float = 3.0) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as tra_loi:  # noqa: S310 — chỉ gọi loopback
            return tra_loi.read(200).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — máy chưa mở trạm, mọi kiểu lỗi đều nghĩa là "chưa trả lời"
        return None


def kiem_tram(cong: int = 8765) -> MucKiem:
    """Trạm nội bộ (`core/tram.py`), chỉ nghe `127.0.0.1`. Cần MyTool đang mở."""
    noi_dung = _http_get("http://127.0.0.1:{0}/trang-thai".format(cong))
    if noi_dung is None:
        return MucKiem("Trạm (cổng {0})".format(cong), False,
                       "không trả lời — mở MyTool (CHAY-GON.vbs) để bật trạm")
    return MucKiem("Trạm (cổng {0})".format(cong), True, "trả lời GET /trang-thai")


def kiem_agent(cong: int = 8767, timeout: float = 1.0) -> MucKiem:
    """`vm/agent.mot_minh` khoá bằng cách BIND cổng này (không phải HTTP) —
    kết nối được nghĩa là có một phiên kênh đang giữ khoá, không hơn."""
    try:
        with socket.create_connection(("127.0.0.1", cong), timeout=timeout):
            pass
    except OSError:
        return MucKiem(
            "Phiên kênh (khoá agent, cổng {0})".format(cong), False,
            "chưa chạy — bình thường ngoài khoảng ~60 phút trước giờ đăng của một kênh nào đó")
    return MucKiem("Phiên kênh (khoá agent, cổng {0})".format(cong), True, "đang giữ khoá một-mình")


def kiem_tat_ca(goc: str = GOC, *, day_du: bool = False) -> List[MucKiem]:
    """Toàn bộ mục kiểm, theo đúng thứ tự nên đọc (cái nền trước, cái ngọn sau)."""
    ket: List[MucKiem] = [kiem_python()]
    ket += kiem_thu_vien()
    ket.append(kiem_ffmpeg(goc))
    ket.append(kiem_whisper(goc))
    ket.append(kiem_vps_json(goc))
    ket += kiem_lich(goc)
    if day_du:
        ket.append(kiem_tram())
        ket.append(kiem_agent())
    return ket


def in_bang(ket: List[MucKiem], *, ra: Callable[[str], None] = print) -> bool:
    """In bảng OK/THIẾU tiếng Việt. Trả `True` khi MỌI mục đều OK."""
    rong_ten = max([len(m.ten) for m in ket] + [20])
    ke = "-" * (rong_ten + 44)
    ra(ke)
    ra("{0}  {1}".format("MỤC KIỂM".ljust(rong_ten), "TRẠNG THÁI"))
    ra(ke)
    for m in ket:
        the = "OK    " if m.ok else "THIẾU "
        ra("{0}  {1}{2}".format(m.ten.ljust(rong_ten), the, m.ghi_chu))
    ra(ke)
    so_thieu = sum(1 for m in ket if not m.ok)
    if so_thieu:
        ra("{0} / {1} mục THIẾU — xem cột trạng thái ở trên để sửa từng mục.".format(
            so_thieu, len(ket)))
    else:
        ra("Tất cả {0} mục đều OK — máy sẵn sàng tự chạy.".format(len(ket)))
    return so_thieu == 0


def main(argv: Optional[List[str]] = None) -> int:
    phan_tich = argparse.ArgumentParser(
        prog="python -m core.kiem_may",
        description="Kiểm máy đã cài đủ để tự chạy VPS chưa — Python, thư viện, "
                    "FFmpeg, mô hình Whisper, vps.json, 3 lịch Task Scheduler, "
                    "trạm 8765, phiên kênh 8767.")
    phan_tich.add_argument("--day-du", action="store_true",
                           help="kiểm thêm trạm 8765 và phiên kênh 8767 (cần MyTool đang mở)")
    doi_so = phan_tich.parse_args(argv)
    ket = kiem_tat_ca(GOC, day_du=doi_so.day_du)
    dat = in_bang(ket)
    return 0 if dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
