"""Bộ dữ liệu nhẹ cho bàn Phân tích trên VPS.

Mỗi lần chỉ đọc một sổ mà người dùng đang xem.  Dữ liệu trả về chỉ giữ các
cột cần ra quyết định, tránh đưa mô tả/hashtag rất dài của gần 20.000 video
vào bộ nhớ giao diện.
"""

from __future__ import annotations

import csv
import datetime as dt
import glob
import os
from typing import Any, Dict, Iterable, List

from . import tong_quan_vps as tq

V7 = "v7"
CONTENT = "content"
DOI_THU = "doi_thu"
HIEU_QUA = "hieu_qua"

NHAN = {
    V7: "Content V7 đề xuất",
    CONTENT: "Kho content nguồn",
    DOI_THU: "Kênh đối thủ",
    HIEU_QUA: "Video đã đăng",
}

# Một câu trả lời cho câu hỏi “bảng này dùng để làm gì?”.  Giao diện chỉ hiện
# đúng câu của bảng đang mở, thay vì bắt người dùng nhớ ý nghĩa của bốn tab.
MO_TA = {
    V7: "Chọn nguồn tốt nhất để làm tiếp; nguồn đã dùng sẽ không bị đề xuất trùng.",
    CONTENT: "Toàn bộ video nguồn đã thu thập để tìm ý tưởng và kiểm tra lịch sử đã dùng.",
    DOI_THU: "Theo dõi quy mô, nhịp ra video và tín hiệu mới của từng kênh đối thủ.",
    HIEU_QUA: "Đối chiếu kết quả video của kênh sau 24, 48 và 72 giờ.",
}

LOC_NHANH = {
    V7: (("Tất cả", ""), ("Nên làm", "qua"), ("Đã loại", "loai"),
         ("Chưa dùng", "chua_dung"), ("Đã dùng", "da_dung"),
         ("Điểm ≥ 40", "diem40"), ("Tăng ≥ 1.000/ngày", "tang1000")),
    CONTENT: (("Tất cả", ""), ("Nên xem trước", "manh"), ("Đang tăng", "tang1000"),
              ("Chưa làm", "chua_lam"), ("Đã làm", "da_lam"), ("Mới 7 ngày", "moi7")),
    DOI_THU: (("Tất cả", ""), ("Đang theo dõi", "theo_doi"),
              ("Mạnh hơn ≥ 5×", "vuot5"), ("Có video mới", "moi"),
              ("Có ghi chú", "ghi_chu")),
    HIEU_QUA: (("Tất cả", ""), ("Chờ đủ 24 giờ", "cho24"), ("Có số 24 giờ", "24"),
               ("Có số 48 giờ", "48"), ("Có số 72 giờ", "72")),
}


def _so(chu: Any) -> float:
    s = str(chu or "").strip().replace(" ", "")
    # CSV máy tạo thường là số trần hoặc thập phân dấu chấm. Nếu người dùng
    # sửa bằng Excel vùng Việt Nam, dấu phẩy với 1–2 số sau là phần thập phân;
    # dấu phẩy trước nhóm 3 số là phân cách hàng nghìn.
    if "," in s and "." not in s:
        sau = s.rsplit(",", 1)[-1]
        s = s.replace(",", ".") if len(sau) <= 2 else s.replace(",", "")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep))
    except (OSError, UnicodeError, csv.Error):
        return []


def _moi_nhat(mau: str) -> str:
    tep = glob.glob(mau)
    return max(tep, key=os.path.getmtime) if tep else ""


def _cot(khoa: str, nhan: str, kieu: str = "chu", rong: int = 110,
         sua: bool = False) -> Dict[str, Any]:
    return {"khoa": khoa, "nhan": nhan, "kieu": kieu, "rong": rong, "sua": sua}


def _chon(d: Dict[str, Any], khoa: Iterable[str]) -> Dict[str, Any]:
    ra = {k: d.get(k, "") for k in khoa}
    ra["_tim"] = " ".join(str(d.get(k, "")) for k in khoa).casefold()
    return ra


_COT = {
    V7: (
        _cot("Hạng", "Hạng", "so", 58), _cot("Điểm", "Điểm", "so", 62),
        _cot("Loại", "Quyết định", "chu", 100), _cot("Tăng/ngày", "Tăng/ngày", "so", 95),
        _cot("View", "View", "so", 90), _cot("Tiêu đề hiển thị", "Tiêu đề", "chu", 360),
        _cot("Kênh", "Kênh nguồn", "chu", 150), _cot("Cụm", "Cụm", "chu", 140),
        _cot("Đã dùng", "Đã dùng", "chu", 85), _cot("Lý do", "Vì sao", "chu", 300),
    ),
    CONTENT: (
        _cot("Điểm", "Điểm", "so", 62), _cot("Tăng/ngày", "Tăng/ngày", "so", 95),
        _cot("View", "View", "so", 90), _cot("Ngày đăng", "Ngày đăng", "ngay", 92),
        _cot("Tiêu đề hiển thị", "Tiêu đề", "chu", 360), _cot("Kênh", "Kênh nguồn", "chu", 150),
        _cot("Tuyến / Kênh", "Tuyến", "chu", 145), _cot("Chủ đề", "Chủ đề", "chu", 145),
        _cot("Đã làm", "Đã dùng", "chu", 85),
        _cot("Ghi chú", "Ghi chú", "chu", 220, sua=True),
    ),
    DOI_THU: (
        _cot("Điểm", "Điểm", "so", 62), _cot("Vượt quy mô", "Vượt quy mô", "so", 105),
        _cot("Subs", "Đăng ký", "so", 90), _cot("Kênh", "Kênh", "chu", 220),
        _cot("Tuyến", "Tuyến", "chu", 150, sua=True),
        _cot("Trạng thái", "Trạng thái", "chu", 110, sua=True),
        _cot("Số video", "Số video", "so", 80), _cot("Mới 7 ngày", "Mới 7 ngày", "so", 92),
        _cot("Quét lúc", "Quét lúc", "ngay", 135),
        _cot("Ghi chú", "Ghi chú", "chu", 230, sua=True),
    ),
    HIEU_QUA: (
        _cot("Tiêu đề", "Video", "chu", 340), _cot("Ngày đăng", "Ngày đăng", "ngay", 95),
        _cot("Hiển thị 24h", "Hiển thị 24h", "so", 105), _cot("CTR 24h", "CTR 24h", "so", 78),
        _cot("Xem 24h", "Xem 24h", "so", 78), _cot("Hiển thị 48h", "Hiển thị 48h", "so", 105),
        _cot("CTR 48h", "CTR 48h", "so", 78), _cot("Xem 48h", "Xem 48h", "so", 78),
        _cot("Hiển thị 72h", "Hiển thị 72h", "so", 105), _cot("CTR 72h", "CTR 72h", "so", 78),
        _cot("Xem 72h", "Xem 72h", "so", 78),
    ),
}


def _goi(loai: str, hang: List[Dict[str, Any]], nguon: str) -> Dict[str, Any]:
    return {"loai": loai, "nhan": NHAN[loai], "cot": list(_COT[loai]),
            "hang": hang, "nguon": nguon}


def doc_bo_du_lieu(goc: str, kenh: str, loai: str) -> Dict[str, Any]:
    """Đọc đúng một bộ dữ liệu. Không gọi mạng."""
    nc = os.path.join(goc, "CHANNEL", kenh, "nghien-cuu")
    if loai == V7:
        from .da_lam import doc_ma_da_lam
        from .doi_thu_kenh import ma_video

        da_dung = doc_ma_da_lam(goc, kenh)
        duong = _moi_nhat(os.path.join(nc, "cham-v7-*.csv"))
        ra = []
        for d in _doc_csv(duong) if duong else []:
            d = dict(d)
            d["Tiêu đề hiển thị"] = d.get("Tiêu đề (Việt)") or d.get("Tiêu đề") or ""
            d["Đã dùng"] = da_dung.get(ma_video(d.get("Link") or ""), "")
            ra.append(_chon(d, ("Hạng", "Điểm", "Loại", "Tăng/ngày", "View",
                                "Tiêu đề hiển thị", "Tiêu đề", "Kênh", "Cụm", "Đã dùng",
                                "Lý do", "Link")))
        return _goi(loai, ra, duong)
    if loai == CONTENT:
        from .da_lam import doc_ma_da_lam
        from .doi_thu_kenh import ma_video

        da_dung = doc_ma_da_lam(goc, kenh)
        duong = os.path.join(nc, "content.csv")
        ra = []
        for d in _doc_csv(duong):
            d = dict(d)
            d["Tiêu đề hiển thị"] = d.get("Tiêu đề (Việt)") or d.get("Tiêu đề video") or ""
            d["Đã làm"] = da_dung.get(ma_video(d.get("Link video") or ""), "")
            ra.append(_chon(d, ("Điểm", "Tăng/ngày", "View", "Ngày đăng", "Lần đầu thấy",
                                "Tiêu đề hiển thị", "Tiêu đề video", "Kênh", "Tuyến / Kênh",
                                "Chủ đề", "Đã làm", "Ghi chú", "Link video")))
        return _goi(loai, ra, duong)
    if loai == DOI_THU:
        duong = os.path.join(nc, "doi-thu.csv")
        khoa = ("Điểm", "Vượt quy mô", "Subs", "Kênh", "Tuyến", "Trạng thái", "Số video",
                "Mới 7 ngày", "Lần đầu thấy", "Quét lúc", "Ghi chú", "Link kênh")
        return _goi(loai, [_chon(d, khoa) for d in _doc_csv(duong)], duong)
    if loai == HIEU_QUA:
        ra = []
        for d in tq.hieu_qua_kenh(goc, kenh):
            video_id = str(d.get("video_id") or "")
            o: Dict[str, Any] = {
                "Tiêu đề": d.get("tieu_de") or video_id,
                "Ngày đăng": str(d.get("ngay_dang") or "")[:10],
                "Link": "https://www.youtube.com/watch?v=" + video_id if video_id else "",
            }
            for moc in (24, 48, 72):
                x = d.get(moc)
                o["Hiển thị {0}h".format(moc)] = getattr(x, "impressions", "") if x else ""
                o["CTR {0}h".format(moc)] = getattr(x, "ctr", "") if x else ""
                o["Xem {0}h".format(moc)] = getattr(x, "avd_pct", "") if x else ""
            ra.append(_chon(o, tuple(o)))
        return _goi(loai, ra, "CHANNEL/{0}/chi-so".format(kenh))
    raise ValueError("Bộ dữ liệu không hợp lệ: " + str(loai))


def gia_tri_so(chu: Any) -> float:
    """Giá trị dùng để sắp xếp/lọc cột số."""
    return _so(chu)


def _trong_7_ngay(chu: Any, hom_nay: dt.date) -> bool:
    s = str(chu or "").strip()[:10]
    for mau in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return 0 <= (hom_nay - dt.datetime.strptime(s, mau).date()).days <= 7
        except ValueError:
            pass
    return False


def hop_loc_nhanh(loai: str, ma_loc: str, dong: Dict[str, Any],
                  hom_nay: dt.date | None = None) -> bool:
    """Một câu hỏi nhanh trên một dòng; dùng được cả trong Qt và bài kiểm."""
    if not ma_loc:
        return True
    if loai == V7:
        qua = str(dong.get("Loại") or "") in ("Làm ngay", "Nên làm")
        return {"qua": qua, "loai": not qua,
                "chua_dung": not bool(str(dong.get("Đã dùng") or "").strip()),
                "da_dung": bool(str(dong.get("Đã dùng") or "").strip()),
                "diem40": _so(dong.get("Điểm")) >= 40,
                "tang1000": _so(dong.get("Tăng/ngày")) >= 1000}.get(ma_loc, True)
    if loai == CONTENT:
        da = bool(str(dong.get("Đã làm") or "").strip())
        return {"manh": _so(dong.get("Điểm")) >= 80 and not da,
                "tang1000": _so(dong.get("Tăng/ngày")) >= 1000,
                "chua_lam": not da, "da_lam": da,
                "moi7": _trong_7_ngay(dong.get("Lần đầu thấy") or dong.get("Ngày đăng"),
                                        hom_nay or dt.date.today())}.get(ma_loc, True)
    if loai == DOI_THU:
        tt = str(dong.get("Trạng thái") or "").strip().casefold()
        return {"theo_doi": tt not in ("bỏ", "bo"),
                "vuot5": _so(dong.get("Vượt quy mô")) >= 5,
                "moi": _so(dong.get("Mới 7 ngày")) > 0 or
                       _trong_7_ngay(dong.get("Lần đầu thấy"), hom_nay or dt.date.today()),
                "ghi_chu": bool(str(dong.get("Ghi chú") or "").strip())}.get(ma_loc, True)
    if loai == HIEU_QUA:
        if ma_loc == "cho24":
            return str(dong.get("Hiển thị 24h") or "").strip() == ""
        if ma_loc in ("24", "48", "72"):
            return str(dong.get("Hiển thị {0}h".format(ma_loc)) or "").strip() != ""
    return True


def link_cua_dong(loai: str, dong: Dict[str, Any]) -> str:
    return str(dong.get({V7: "Link", CONTENT: "Link video", DOI_THU: "Link kênh",
                         HIEU_QUA: "Link"}.get(loai, "Link")) or "").strip()


_COT_DUOC_SUA = {
    CONTENT: {"Ghi chú"},
    DOI_THU: {"Tuyến", "Trạng thái", "Ghi chú"},
}


def sua_o_quan_ly(goc: str, kenh: str, loai: str, dong: Dict[str, Any],
                  khoa: str, gia_tri: str) -> None:
    """Ghi một ô quản lý trở lại CSV nguồn theo cách thay tệp nguyên tử.

    Chỉ các cột do người dùng sở hữu mới được sửa. Số liệu thu thập và điểm V7
    vẫn là dữ liệu máy sinh, tránh một cú click nhầm làm sai quyết định.
    """
    if khoa not in _COT_DUOC_SUA.get(loai, set()):
        raise ValueError("Cột này là số liệu tự động, không thể sửa trực tiếp.")
    ten_tep = {CONTENT: "content.csv", DOI_THU: "doi-thu.csv"}.get(loai)
    if not ten_tep:
        raise ValueError("Bảng này chỉ đọc.")
    duong = os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", ten_tep)
    khoa_link = "Link video" if loai == CONTENT else "Link kênh"
    link = str(dong.get(khoa_link) or "").strip()
    if not link:
        raise ValueError("Dòng này thiếu link định danh nên chưa thể lưu an toàn.")
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            doc = csv.DictReader(tep)
            cot = list(doc.fieldnames or [])
            hang = list(doc)
    except (OSError, UnicodeError, csv.Error) as e:
        raise OSError("Không đọc được bảng nguồn: " + str(e)) from e
    if khoa not in cot:
        cot.append(khoa)
    moi = " ".join(str(gia_tri or "").split())[:500 if khoa == "Ghi chú" else 120]
    tim_thay = False
    for d in hang:
        if str(d.get(khoa_link) or "").strip() == link:
            d[khoa] = moi
            tim_thay = True
            break
    if not tim_thay:
        raise ValueError("Dòng đã thay đổi trong tệp nguồn; hãy bấm Làm mới rồi sửa lại.")
    tam = duong + ".tmp"
    try:
        with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
            viet = csv.DictWriter(tep, fieldnames=cot, extrasaction="ignore")
            viet.writeheader()
            viet.writerows(hang)
        os.replace(tam, duong)
    except OSError:
        try:
            if os.path.exists(tam):
                os.remove(tam)
        except OSError:
            pass
        raise

