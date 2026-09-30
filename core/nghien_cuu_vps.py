"""Dữ liệu gọn cho trang Nghiên cứu trên VPS.

Trang này chỉ trả lời hai câu hỏi: đang theo dõi đối thủ nào, và đối thủ đang
làm content gì.  Ba nguồn nuôi câu trả lời được kiểm tra riêng để người vận
hành biết số liệu mới hay cũ mà không phải mở thư mục tìm tệp.

Không gọi mạng. Bảng chi tiết dùng lại :mod:`core.bang_du_lieu_vps` để cùng
một cách đọc, lọc và ghi ô quản lý với các màn dữ liệu khác.
"""

from __future__ import annotations

import datetime as dt
import glob
import os
from typing import Any, Dict, Iterable

from . import bang_du_lieu_vps as dl
from . import tong_quan_vps as tq

DOI_THU = dl.DOI_THU
CONTENT = dl.CONTENT
CAC_SO = (DOI_THU, CONTENT)

NHAN_SO = {
    DOI_THU: "Đối thủ",
    CONTENT: "Content đối thủ",
}

MO_TA_SO = {
    DOI_THU: "Danh bạ các kênh đang theo dõi. Sửa trực tiếp Tuyến, Trạng thái và Ghi chú.",
    CONTENT: "Video đã thu thập từ đối thủ. Lọc, sắp xếp và ghi chú để tìm cơ hội nội dung.",
}


def _dem_dong_khong_rong(duong: str) -> int:
    try:
        with open(duong, "r", encoding="utf-8-sig", errors="replace") as tep:
            return sum(1 for dong in tep if dong.strip())
    except OSError:
        return 0


def _moi_nhat(cac_tep: Iterable[str]) -> str:
    co = [p for p in cac_tep if p and os.path.isfile(p)]
    return max(co, key=os.path.getmtime) if co else ""


def _tuoi_gio(duong: str, bay_gio: dt.datetime) -> float | None:
    if not duong:
        return None
    try:
        moc = dt.datetime.fromtimestamp(os.path.getmtime(duong), tz=bay_gio.tzinfo)
    except OSError:
        return None
    return max(0.0, (bay_gio - moc).total_seconds() / 3600.0)


def _luc_doc(duong: str) -> str:
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(duong)).strftime("%d/%m %H:%M")
    except OSError:
        return "—"


def _do_moi(tuoi_gio: float | None, *, du_lieu_co_dinh: bool = False) -> tuple[str, str]:
    """Nhãn ngắn và mức màu cho một nguồn dữ liệu.

    Danh sách đối thủ người dùng đưa ban đầu là dữ liệu nền, không cần làm mới
    mỗi ngày. Studio và trang chủ là tín hiệu vận hành nên sau ba ngày được
    nói thẳng là cũ.
    """
    if tuoi_gio is None:
        return "Chưa có", "thieu"
    if du_lieu_co_dinh:
        return "Đã nhận", "tot"
    if tuoi_gio <= 36:
        return "Mới", "tot"
    if tuoi_gio <= 72:
        return "Cần cập nhật", "can"
    return "Đã cũ", "cu"


def _nguon(ten: str, duong: str, so_luong: int, don_vi: str,
           bay_gio: dt.datetime, *, co_dinh: bool = False) -> Dict[str, Any]:
    tuoi = _tuoi_gio(duong, bay_gio)
    trang_thai, muc = _do_moi(tuoi, du_lieu_co_dinh=co_dinh)
    return {
        "ten": ten,
        "duong": duong,
        "so_luong": int(so_luong or 0),
        "don_vi": don_vi,
        "luc": _luc_doc(duong),
        "tuoi_gio": tuoi,
        "trang_thai": trang_thai,
        "muc": muc,
    }


def tom_tat_nguon(goc: str, kenh: str,
                  bay_gio: dt.datetime | None = None) -> Dict[str, Any]:
    """Tóm tắt chất lượng/độ mới của ba đầu vào nghiên cứu.

    Chỉ đụng các tệp tổng hợp nhỏ. Không đi xuyên cây ``chi-so/raw`` vốn có
    thể chứa hàng nghìn gói và ảnh; nhờ vậy mở trang không làm VPS tăng tải.
    """
    bay_gio = bay_gio or dt.datetime.now()
    thu_muc_kenh = os.path.join(goc, "CHANNEL", kenh)
    nc = os.path.join(thu_muc_kenh, "nghien-cuu")

    ban_dau = os.path.join(nc, "doi-thu-ban-dua.txt")
    trang_chu = os.path.join(nc, "trang-chu.csv")
    bang_studio = os.path.join(thu_muc_kenh, "chi-so", "bang-tom-tat.csv")
    tong_quan_studio = glob.glob(os.path.join(
        thu_muc_kenh, "chi-so", "kenh", "*", "tong-quan.json"))
    tep_studio = _moi_nhat([bang_studio, *tong_quan_studio])

    phan_tich = tq.tom_tat_phan_tich(goc, kenh)
    nguon = (
        _nguon("Danh sách ban đầu", ban_dau, _dem_dong_khong_rong(ban_dau),
               "kênh", bay_gio, co_dinh=True),
        _nguon("Studio của kênh", tep_studio,
               tq._dem_dong(bang_studio) if os.path.isfile(bang_studio) else len(tong_quan_studio),
               "bản ghi", bay_gio),
        _nguon("Trang chủ kênh", trang_chu, tq._dem_dong(trang_chu),
               "video", bay_gio),
    )
    co = sum(1 for n in nguon if n["duong"])
    moi = sum(1 for n in nguon if n["muc"] == "tot")
    if co == 3 and moi == 3:
        chat_luong, muc = "Đủ nguồn, dữ liệu mới", "tot"
    elif co == 3:
        chat_luong, muc = "Đủ nguồn, có dữ liệu cần cập nhật", "can"
    elif co:
        chat_luong, muc = "Thiếu {0}/3 nguồn".format(3 - co), "thieu"
    else:
        chat_luong, muc = "Chưa có dữ liệu nghiên cứu", "thieu"
    return {
        "kenh": kenh,
        "chat_luong": chat_luong,
        "muc": muc,
        "nguon": list(nguon),
        "so_doi_thu": int(phan_tich["doi_thu"]["so_kenh"]),
        "so_content": int(phan_tich["noi_dung"]["so_video"]),
    }


def doc_so(goc: str, kenh: str, loai: str) -> Dict[str, Any]:
    """Đọc một trong hai sổ nghiên cứu bằng bộ đọc dùng chung."""
    if loai not in CAC_SO:
        raise ValueError("Sổ nghiên cứu không hợp lệ: " + str(loai))
    return dl.doc_bo_du_lieu(goc, kenh, loai)

