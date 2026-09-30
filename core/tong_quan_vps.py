"""Số liệu gọn cho hai màn Tổng quan và Phân tích trên VPS.

Chỉ đọc tệp tại máy. Không gọi YouTube, không quét đối thủ và không gọi API.
Các hàm này được gọi trong luồng nền của Qt; dữ liệu lớn chỉ đọc khi người dùng
mở trang Phân tích hoặc đổi kênh.
"""

from __future__ import annotations

import csv
import datetime as dt
import glob
import os
import subprocess
from typing import Any, Dict, Iterable, List


CAC_BUOC_PHAT_TRIEN = (
    ("nghien_cuu", "Nghiên cứu"),
    ("chon_content", "Chọn nội dung"),
    ("san_xuat", "Sản xuất"),
    ("dang", "Đăng"),
    ("cham_kenh", "Chăm kênh"),
)

_KY_HIEU_BUOC = {"xong": "✓", "dang": "●", "loi": "!", "cho": "·", "tat": "–"}


def _so(chu: Any) -> float:
    try:
        return float(str(chu or "").replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep))
    except (OSError, UnicodeError, csv.Error):
        return []


def _luc(duong: str) -> str:
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(duong)).isoformat(timespec="minutes")
    except OSError:
        return ""


def _dem_dong(duong: str) -> int:
    """Đếm dòng nhanh bằng nhị phân, không tạo hàng trăm nghìn chuỗi trong RAM."""
    try:
        with open(duong, "rb") as tep:
            return max(0, sum(khoi.count(b"\n") for khoi in iter(lambda: tep.read(1024 * 1024), b"")) - 1)
    except OSError:
        return 0


def _moi_nhat(mau: str) -> str:
    tep = glob.glob(mau)
    return max(tep, key=os.path.getmtime) if tep else ""


def _top(hang: Iterable[Dict[str, str]], khoa, so_dong: int = 8) -> List[Dict[str, str]]:
    return sorted(hang, key=khoa, reverse=True)[:so_dong]


def tom_tat_phan_tich(goc: str, ma_kenh: str) -> Dict[str, Any]:
    """Đối thủ, quyết định V7 và độ mới dữ liệu của một kênh."""
    thu_muc = os.path.join(goc, "CHANNEL", ma_kenh, "nghien-cuu")
    tep_ds = os.path.join(thu_muc, "doi-thu.txt")
    tep_dt = os.path.join(thu_muc, "doi-thu.csv")
    tep_nd = os.path.join(thu_muc, "content.csv")
    tep_v7 = _moi_nhat(os.path.join(thu_muc, "cham-v7-*.csv"))

    try:
        with open(tep_ds, "r", encoding="utf-8", errors="replace") as tep:
            so_link = sum(1 for dong in tep if dong.strip())
    except OSError:
        so_link = 0

    doi_thu = _doc_csv(tep_dt)
    dang_theo_doi = [d for d in doi_thu if str(d.get("Trạng thái") or "").lower() != "bỏ"]
    top_doi_thu = _top(
        dang_theo_doi,
        lambda d: (_so(d.get("Điểm")), _so(d.get("Vượt quy mô")), _so(d.get("Subs"))),
    )

    v7 = _doc_csv(tep_v7) if tep_v7 else []
    nen_lam = [d for d in v7 if d.get("Loại") in ("Làm ngay", "Nên làm")]
    # Khi công thức không cho ứng viên nào qua cổng, vẫn hiện các dòng điểm cao
    # nhất và giữ nguyên nhãn "Bỏ". Người vận hành cần thấy V7 đang từ chối hết,
    # thay vì một bảng trắng khiến họ tưởng chưa có dữ liệu.
    top_v7 = (nen_lam or v7)[:8]

    return {
        "kenh": ma_kenh,
        "doi_thu": {
            "so_link": so_link,
            "so_kenh": len(dang_theo_doi),
            "top": top_doi_thu,
            "luc": _luc(tep_dt) or _luc(tep_ds),
        },
        "noi_dung": {"so_video": _dem_dong(tep_nd), "luc": _luc(tep_nd)},
        "v7": {
            "top": top_v7,
            "so_ung_vien": len(nen_lam),
            "so_da_cham": len(v7),
            "luc": _luc(tep_v7),
            "tep": tep_v7,
        },
    }


def hieu_qua_kenh(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    """Tối đa 12 video gần nhất ở mốc 24/48/72 giờ."""
    try:
        from . import trung_tam
        from .chi_so_ytb import doc_kenh

        hang = trung_tam.hieu_qua_theo_moc(
            doc_kenh(ma_kenh, goc=os.path.join(goc, "CHANNEL")))
        return hang[:12]
    except Exception:
        return []


def _ket_qua_buoc(chu: Any) -> str:
    """Đổi một dòng kết quả phiên VPS thành trạng thái ngắn của dashboard."""
    s = str(chu or "").strip().lower()
    if not s:
        return "cho"
    if "lỗi" in s or "loi" in s or "không thấy" in s:
        return "loi"
    if "xong" in s or "thành công" in s or "ma 0" in s or "mã 0" in s:
        return "xong"
    if "đang" in s:
        return "dang"
    return "cho"


def trang_thai_quy_trinh(kenh: Dict[str, Any]) -> Dict[str, Any]:
    """Tóm tắt năm bước phát triển của một kênh từ ảnh chụp local.

    Hàm chỉ suy luận từ dữ liệu đã đọc trên máy. Không gọi mạng và không biến
    một bước chưa có dữ liệu thành lỗi. Kết quả dùng chung cho bảng, bộ lọc và
    gợi ý điều chỉnh, tránh mỗi chỗ hiểu trạng thái theo một kiểu.
    """
    bay = dict(kenh.get("bay_gio") or {})
    luot = dict(kenh.get("luot") or {})
    nguon = dict(luot.get("nguon") or {})
    phien = dict(kenh.get("phien") or {})
    ket_phien = dict(phien.get("ket_qua") or {})
    ke_hoach = list(kenh.get("ke_hoach") or [])
    tieu_de = str((kenh.get("video") or {}).get("tieu_de") or "").strip()
    co_nguon = bool(tieu_de or nguon.get("tieu_de") or luot.get("link"))

    buoc: Dict[str, Dict[str, str]] = {
        ma: {"ma": ma, "ten": ten, "trang_thai": "cho", "chi_tiet": "Chưa tới bước này"}
        for ma, ten in CAC_BUOC_PHAT_TRIEN
    }

    # Nghiên cứu: hai nguồn đầu vào local của phiên là Studio và trang chủ.
    kq_nc = [ket_phien.get("quet_studio"), ket_phien.get("quet_trang_chu")]
    if any(kq_nc):
        tt_nc = [_ket_qua_buoc(x) for x in kq_nc if x]
        trang_nc = "xong" if "xong" in tt_nc else ("loi" if "loi" in tt_nc else "cho")
        buoc["nghien_cuu"].update(
            trang_thai=trang_nc,
            chi_tiet=" · ".join(str(x) for x in kq_nc if x)[:300])
    if str(bay.get("chu") or "").lower().startswith("đang chọn"):
        buoc["nghien_cuu"].update(trang_thai="dang", chi_tiet="Đang cập nhật nguồn cho lượt mới")
    elif co_nguon and buoc["nghien_cuu"]["trang_thai"] == "cho":
        buoc["nghien_cuu"].update(trang_thai="xong", chi_tiet="Đã có dữ liệu nguồn cho lượt này")

    if co_nguon:
        buoc["chon_content"].update(trang_thai="xong", chi_tiet=tieu_de or
                                    str(nguon.get("tieu_de") or "Đã chọn nguồn"))
    elif buoc["nghien_cuu"]["trang_thai"] == "dang":
        buoc["chon_content"].update(trang_thai="dang", chi_tiet="Đang chấm và chọn nội dung")

    khau = list(luot.get("khau") or [])
    tt_khau = [str(x.get("trang_thai") or "") for x in khau]
    khau_hong = next((x for x in khau if str(x.get("trang_thai")) == "hong"), None)
    khau_dang = next((x for x in khau if str(x.get("trang_thai")) == "dang"), None)
    if khau_hong:
        buoc["san_xuat"].update(trang_thai="loi", chi_tiet=str(
            khau_hong.get("loi") or khau_hong.get("ten") or "Khâu sản xuất bị lỗi"))
    elif khau_dang:
        buoc["san_xuat"].update(trang_thai="dang", chi_tiet=str(
            khau_dang.get("ten") or "Đang sản xuất"))
    elif khau and all(x in ("xong", "bo-qua") for x in tt_khau):
        buoc["san_xuat"].update(trang_thai="xong", chi_tiet="Video đã sản xuất xong")
    elif khau or co_nguon:
        buoc["san_xuat"].update(trang_thai="cho", chi_tiet="Chờ hoặc đang chuẩn bị sản xuất")

    dong_dang = next((d for d in ke_hoach if d.get("loai") in
                      ("cho_duyet", "sap_dang", "da_dang")), None)
    if dong_dang:
        loai = dong_dang.get("loai")
        if loai == "da_dang":
            buoc["dang"].update(trang_thai="xong", chi_tiet="Video đã đăng")
        elif loai == "cho_duyet":
            buoc["dang"].update(trang_thai="cho", chi_tiet="Video đang chờ duyệt")
        else:
            buoc["dang"].update(trang_thai="cho", chi_tiet="Đã lên lịch {0} {1}".format(
                dong_dang.get("ngay") or "", dong_dang.get("gio") or "").strip())
    if ket_phien.get("dang"):
        trang_dang = _ket_qua_buoc(ket_phien.get("dang"))
        buoc["dang"].update(trang_thai=trang_dang, chi_tiet=str(ket_phien["dang"]))

    if ket_phien.get("cmt"):
        trang_cmt = _ket_qua_buoc(ket_phien.get("cmt"))
        buoc["cham_kenh"].update(trang_thai=trang_cmt, chi_tiet=str(ket_phien["cmt"]))
    elif buoc["dang"]["trang_thai"] == "xong":
        buoc["cham_kenh"].update(trang_thai="cho", chi_tiet="Chờ quét và trả lời bình luận")

    danh_sach = [buoc[ma] for ma, _ten in CAC_BUOC_PHAT_TRIEN]
    return {
        "cac_buoc": danh_sach,
        "chu": "  ".join("{0} {1}".format(_KY_HIEU_BUOC[x["trang_thai"]], x["ten"])
                           for x in danh_sach),
        "co_loi": any(x["trang_thai"] == "loi" for x in danh_sach),
        "dang_lam": any(x["trang_thai"] == "dang" for x in danh_sach),
    }


def goi_y_dieu_chinh(kenh: Dict[str, Any], quy_trinh: Dict[str, Any] | None = None) -> str:
    """Một đề xuất có căn cứ để người vận hành biết nên chỉnh gì trước."""
    bay = dict(kenh.get("bay_gio") or {})
    if bay.get("muc") == "loi":
        return str(bay.get("chu") or "Mở chi tiết và xử lý lỗi đang chặn kênh")
    quy_trinh = quy_trinh or trang_thai_quy_trinh(kenh)
    loi = next((x for x in quy_trinh["cac_buoc"] if x["trang_thai"] == "loi"), None)
    if loi:
        return "Kiểm tra {0}: {1}".format(loi["ten"].lower(), loi["chi_tiet"])
    ke_hoach = list(kenh.get("ke_hoach") or [])
    if any(d.get("loai") == "cho_duyet" for d in ke_hoach):
        return "Duyệt video và chốt lịch đăng"
    n7 = dict(kenh.get("bay_ngay") or {})
    if not n7.get("so_video"):
        return "Chưa có video trong 7 ngày; kiểm tra lịch nội dung"
    ctr = n7.get("ctr")
    if ctr is not None and float(ctr) < 3.5:
        return "CTR {0:.1f}% thấp; xem lại ảnh bìa và tiêu đề".format(float(ctr))
    if bay.get("muc") == "canh_bao":
        return str(bay.get("chu") or "Mở chi tiết để kiểm tra")
    if not kenh.get("tu_chay"):
        return "Kênh đang tắt tự động"
    return "Đang vận hành ổn; tiếp tục theo dõi số liệu"


def tom_tat_toan_bo(cac_kenh: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Các chỉ số toàn bộ kênh cho dải đầu dashboard."""
    ds = list(cac_kenh)
    views = sum(float((k.get("bay_ngay") or {}).get("views") or 0) for k in ds)
    subs = sum(float((k.get("bay_ngay") or {}).get("dang_ky") or 0) for k in ds)
    co_ctr = [(float((k.get("bay_ngay") or {}).get("ctr")),
               int((k.get("bay_ngay") or {}).get("so_video") or 0))
              for k in ds if (k.get("bay_ngay") or {}).get("ctr") is not None]
    tong_video_ctr = sum(max(1, n) for _ctr, n in co_ctr)
    ctr = (sum(c * max(1, n) for c, n in co_ctr) / tong_video_ctr) if tong_video_ctr else None
    can_xu_ly = 0
    dang_lam = 0
    for k in ds:
        qt = trang_thai_quy_trinh(k)
        if (k.get("bay_gio") or {}).get("muc") in ("loi", "canh_bao") or qt["co_loi"] or \
                any(d.get("loai") == "cho_duyet" for d in (k.get("ke_hoach") or [])):
            can_xu_ly += 1
        if qt["dang_lam"] or k.get("dang_chay"):
            dang_lam += 1
    return {"so_kenh": len(ds), "views_7_ngay": views, "ctr_7_ngay": ctr,
            "dang_ky_7_ngay": subs, "can_xu_ly": can_xu_ly, "dang_lam": dang_lam}


def canh_bao_windows(gio: int = 24) -> Dict[str, str]:
    """Tìm shutdown do Windows Evaluation hết hạn trong Event Log gần đây."""
    if os.name != "nt":
        return {}
    mili = max(1, int(gio)) * 60 * 60 * 1000
    cau = "*[System[(EventID=1074) and TimeCreated[timediff(@SystemTime) <= {0}]]]".format(mili)
    try:
        ket = subprocess.run(
            ["wevtutil.exe", "qe", "System", "/q:" + cau, "/f:text", "/c:20", "/rd:true"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
        chu = ket.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return {}
    thuong = chu.lower()
    if "wlms.exe" not in thuong or "license period" not in thuong or "expired" not in thuong:
        return {}
    luc = ""
    vi_tri = thuong.find("wlms.exe")
    truoc = chu[:vi_tri]
    for dong in reversed(truoc.splitlines()):
        if dong.strip().lower().startswith("date:"):
            luc = dong.split(":", 1)[1].strip()[:19]
            break
    return {
        "muc": "loi",
        "tieu_de": "Windows đã tự tắt do hết hạn Evaluation",
        "chi_tiet": "Windows đã tự tắt máy vì hết hạn" +
                    ("; lần gần nhất " + luc if luc else "") +
                    ". Kiểm tra slmgr.vbs /xpr; nếu chưa gia hạn, chạy /rearm bằng quyền "
                    "Administrator hoặc kích hoạt key hợp lệ.",
    }

