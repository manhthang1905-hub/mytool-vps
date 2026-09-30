"""Chốt đúng *một* content kế tiếp cho mỗi kênh.

Trang Nghiên cứu nuôi dữ liệu. Module này chỉ làm bước ra quyết định giữa hai
luồng độc lập:

* ``doi-thu`` dùng điểm NHANH/LỚN/BỨT/VƯỢT của :mod:`core.cham_diem_content`.
* ``v7`` dùng năm cửa Cụm/Đề xuất/Nổ/Đang lên/Khuôn của
  :mod:`core.cong_thuc_v7`.

Hai thang điểm đều là 0..100 nhưng không được trộn để xếp hạng chung. Mỗi thang
trả lời một câu hỏi khác nhau. Kết quả chốt được ghi đè vào một tệp JSON duy
nhất để khâu Sản xuất đọc; vì vậy đây không thể biến thành kho video chờ làm.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from . import cham_diem_content as cdc
from . import doi_thu_kenh as so
from .da_lam import doc_ma_da_lam

__all__ = [
    "LUONG_DOI_THU", "LUONG_V7", "TEP_LUA_CHON", "UngVien", "LuaChon",
    "ung_vien_doi_thu", "ung_vien_v7", "lay_ung_vien", "doc_lua_chon",
    "chot", "bo_chot", "danh_dau_dang_san_xuat", "hoan_tat_lua_chon",
]

LUONG_DOI_THU = "doi-thu"
LUONG_V7 = "v7"
TEP_LUA_CHON = "content-tiep-theo.json"


@dataclass
class UngVien:
    luong: str
    ma: str
    tieu_de: str
    kenh_nguon: str
    link: str
    diem: int
    muc: str
    ly_do: str
    view: float = 0.0
    tang_ngay: float = 0.0
    thanh_phan: Dict[str, float] = field(default_factory=dict)


@dataclass
class LuaChon:
    kenh: str
    trang_thai: str
    ngay_chot: str
    ung_vien: UngVien


def _chu(dong, o, ten: str) -> str:
    i = o.get(ten)
    return str(dong[i]).strip() if i is not None and i < len(dong) else ""


def _so(chu) -> float:
    try:
        return float(str(chu or "").replace(".", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _muc_doi_thu(diem: int) -> str:
    if diem >= 75:
        return "Ưu tiên"
    if diem >= 50:
        return "Cân nhắc"
    return "Theo dõi"


def ung_vien_doi_thu(goc: str, kenh: str, *, gioi_han: int = 50,
                     hom_nay: Optional[_dt.date] = None) -> List[UngVien]:
    """Xếp content đối thủ chưa làm bằng đúng công thức điểm của sổ Nghiên cứu."""
    cot, hang = so.doc_bang(goc, kenh)
    if not hang:
        return []
    diem = cdc.cham_bang(cot, hang, hom_nay=hom_nay)
    o = {ten: i for i, ten in enumerate(cot)}
    da_lam = doc_ma_da_lam(goc, kenh)
    ra: List[UngVien] = []
    for dong, d in zip(hang, diem):
        link = _chu(dong, o, so.COT_LINK)
        ma = so.ma_video(link) or ""
        tieu_de = _chu(dong, o, "Tiêu đề video")
        da_lam_o = _chu(dong, o, so.COT_DA_LAM) if so.COT_DA_LAM in o else ""
        if not ma or not tieu_de or ma in da_lam or da_lam_o:
            continue
        ra.append(UngVien(
            luong=LUONG_DOI_THU, ma=ma, tieu_de=tieu_de,
            kenh_nguon=_chu(dong, o, "Kênh"), link=link, diem=d.diem,
            muc=_muc_doi_thu(d.diem), ly_do=d.giai_thich(),
            view=d.lon_tho, tang_ngay=d.nhanh_tho,
            thanh_phan={
                "Nhanh": round(d.nhanh * 100, 1),
                "Lớn": round(d.lon * 100, 1),
                "Bứt": round(d.but * 100, 1),
                "Vượt": round(d.vuot * 100, 1),
            },
        ))
    ra.sort(key=lambda x: (-x.diem, -x.tang_ngay, -x.view))
    return ra[:max(0, gioi_han)]


def ung_vien_v7(goc: str, kenh: str, *, gioi_han: int = 50) -> List[UngVien]:
    """Xếp content theo V7, giữ nguyên điểm và các lý do do V7 sinh ra."""
    from . import cong_thuc_v7 as v7  # nhập muộn: V7 đọc nhiều nguồn dữ liệu

    kq = v7.cham(goc, kenh)
    ra = [UngVien(
        luong=LUONG_V7, ma=d.ma, tieu_de=d.tieu_de_viet or d.tieu_de,
        kenh_nguon=d.kenh, link=d.link, diem=d.diem, muc=d.loai,
        ly_do=" · ".join(d.ly_do) or "V7 chưa có đủ tín hiệu để giải thích",
        view=float(d.view or 0), tang_ngay=float(d.tang or 0),
        thanh_phan={
            "Cụm": d.diem_cum, "Đề xuất": d.diem_pool, "Nổ": d.diem_no,
            "Đang lên": d.diem_len, "Khuôn": d.diem_khuon,
        },
    ) for d in kq.ung_vien]
    return ra[:max(0, gioi_han)]


def lay_ung_vien(goc: str, kenh: str, luong: str, *, gioi_han: int = 50) -> List[UngVien]:
    if luong == LUONG_DOI_THU:
        return ung_vien_doi_thu(goc, kenh, gioi_han=gioi_han)
    if luong == LUONG_V7:
        return ung_vien_v7(goc, kenh, gioi_han=gioi_han)
    raise ValueError("Luồng chọn content không hợp lệ: " + str(luong))


def _duong(goc: str, kenh: str) -> str:
    return os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_LUA_CHON)


def doc_lua_chon(goc: str, kenh: str) -> Optional[LuaChon]:
    try:
        with open(_duong(goc, kenh), "r", encoding="utf-8") as tep:
            raw = json.load(tep)
        uv = UngVien(**raw["ung_vien"])
        return LuaChon(kenh=str(raw.get("kenh") or kenh),
                       trang_thai=str(raw.get("trang_thai") or "chờ sản xuất"),
                       ngay_chot=str(raw.get("ngay_chot") or ""), ung_vien=uv)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _luu(goc: str, lua_chon: LuaChon) -> str:
    duong = _duong(goc, lua_chon.kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(asdict(lua_chon), tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)
    return duong


def chot(goc: str, kenh: str, ung_vien: UngVien, *,
         luc: Optional[_dt.datetime] = None) -> str:
    """Chốt ứng viên làm content kế tiếp; lựa chọn cũ được thay thế nguyên tử."""
    if ung_vien.luong not in (LUONG_DOI_THU, LUONG_V7) or not ung_vien.ma:
        raise ValueError("Ứng viên content không hợp lệ")
    moc = (luc or _dt.datetime.now()).replace(microsecond=0).isoformat()
    return _luu(goc, LuaChon(kenh=kenh, trang_thai="chờ sản xuất", ngay_chot=moc,
                              ung_vien=ung_vien))


def danh_dau_dang_san_xuat(goc: str, kenh: str) -> bool:
    """Cho khâu Sản xuất báo đã nhận lựa chọn mà không tạo thêm bản ghi."""
    lua_chon = doc_lua_chon(goc, kenh)
    if lua_chon is None:
        return False
    lua_chon.trang_thai = "đang sản xuất"
    _luu(goc, lua_chon)
    return True


def hoan_tat_lua_chon(goc: str, kenh: str, ma: str = "") -> bool:
    """Tiêu thụ lựa chọn sau khi video đã được bàn giao sang khâu đăng.

    ``ma`` ngăn một lượt cũ xoá nhầm lựa chọn mới mà người vận hành vừa chốt
    trong lúc lượt trước đang hoàn tất. Không còn tệp lựa chọn nghĩa là tab
    Chọn content lại sẵn sàng chấm đúng dữ liệu mới nhất cho video kế tiếp.
    """
    lua_chon = doc_lua_chon(goc, kenh)
    if lua_chon is None or (ma and lua_chon.ung_vien.ma != ma):
        return False
    return bo_chot(goc, kenh)


def bo_chot(goc: str, kenh: str) -> bool:
    """Bỏ lựa chọn hiện tại. Dùng khi muốn chấm lại sát lịch hơn."""
    try:
        os.remove(_duong(goc, kenh))
        return True
    except FileNotFoundError:
        return False
