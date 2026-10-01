"""Lõi dữ liệu THUẦN cho trang **Bảng điều khiển** (Việc 1,
`workspace/THIET-KE-BANG-DIEU-KHIEN.md`, duyệt 29/09/2026).

Không Qt, không mạng, không ghi đĩa nào ngoài `workspace/viec-da-xong.json` —
mọi thứ khác chỉ ĐỌC lại các tệp đã có (`core.trung_tam.anh_chup()` và bạn bè)
rồi gói thành hình mà trang mới cần: một khối "Việc của bạn" xếp theo mức nặng,
một dòng "Máy", và bộ khung mỗi thẻ kênh (câu tình trạng, video kế tiếp, ba
video gần nhất kèm mũi tên so sánh).

═══ VÌ SAO TÁCH RA KHỎI `ui_qt/trang_dieu_khien.py` ═══

`cau_tinh_trang`, `tien_do_nhat_ky`, `gon_dong_nhat_ky`, `VIEC_KHAU`,
`DON_VI_KHAU`, `_KY_THUAT` từng sống trong `ui_qt/trang_dieu_khien.py` — thuần
nhưng bị nhốt trong một mô-đun import PyQt5. Trang mới (Việc 2) và trang cũ
đều cần đúng logic ấy, nên chúng chuyển sang đây; `ui_qt/trang_dieu_khien.py`
import ngược lại để bài kiểm cũ (`tests/test_dieu_khien_cot_gon.py`) không phải
sửa gì.

Nguồn dữ liệu + hàm được phép gọi lại: xem mục 2 và mục 5 của bản thiết kế.
KHÔNG viết lại logic đã có ở `core.trung_tam`, `core.tu_chay`, `core.kenh`,
`core.ho_so_video`, `core.khuon_bia`, `core.ban_giao_dang`, `core.vm_cai_dat`,
`core.lich_tu_chay` — gọi thẳng.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re as _re
import statistics
from typing import Any, Dict, List, Optional, Tuple

from . import kenh as _kenh_mod
from . import khuon_bia
from . import trung_tam as tt
from . import tu_chay
from . import vm_cai_dat
from .money import MICRO_PER_VND

__all__ = [
    # Chuyển từ ui_qt/trang_dieu_khien.py — trang_dieu_khien import ngược.
    "gon_dong_nhat_ky", "tien_do_nhat_ky", "cau_tinh_trang",
    "VIEC_KHAU", "DON_VI_KHAU",
    # Lõi Bảng điều khiển.
    "anh_bang", "muc_the", "video_ke_tiep", "video_gan_day", "may_dang_hoc",
    "doc_can_ghim", "doc_nhap_thua", "doc_kiem_dom",
    "so_ngay_con_chay", "dong_may", "doc_da_xong", "danh_dau_xong",
    "doc_tinh_trang", "viec_cua_ban",
    # Các đường ghi công tắc — thuần, trang mới lẫn trang cũ gọi được.
    "doi_cong_tac", "doi_ngan_sach", "doi_gio_dang", "doi_nhip_dang",
    "doi_phut_phien", "doi_giu_luot", "tam_dung_tat_ca", "bat_lai_tam_dung",
    # Giám đốc kênh (01/10/2026).
    "doi_giam_doc", "giam_doc_the", "CHE_DO_GIAM_DOC",
    # Mức việc — dùng để sắp xếp/tô màu ở cả hai lớp.
    "HONG", "CANH_BAO", "THUONG",
    # Mức thẻ kênh (`muc_the`).
    "TOT", "CHO_BAN", "LUU_Y", "TAT",
]


# ═══════════════════════════════════════════════════════════════════════════
# 1) CHUYỂN NGUYÊN VĂN từ ui_qt/trang_dieu_khien.py — khối "MỘT CÂU TÌNH TRẠNG"
# ═══════════════════════════════════════════════════════════════════════════
#
# Cắt phần KỸ THUẬT ra khỏi một dòng nhật ký trước khi cho lên màn hình — xem
# lịch sử đầy đủ ở bản gốc (`ui_qt/trang_dieu_khien.py`, khối cùng tên trước
# 29/09/2026): chụp màn hình thật từng phơi nguyên vết lỗi Python hai mươi
# dòng ra ba cột liền, và mốc 210 ký tự đo trên chính dòng lỗi thật đó.
_KY_THUAT = _re.compile(
    r"\((?:[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning)\b|[A-Za-z]:\\)"
    r"[^()]*(?:\([^()]*\)[^()]*)*\)"
)

_DAI_TOI_DA_MOT_DONG = 210


def gon_dong_nhat_ky(dong: str) -> str:
    """Một dòng nhật ký đã bỏ vết lỗi kỹ thuật và cắt cho vừa bề rộng cột."""
    chu = _KY_THUAT.sub("", str(dong or ""))
    chu = _re.sub(r"\s+", " ", chu).strip()
    chu = _re.sub(r"\s+([.,;:])", r"\1", chu)
    chu = _re.sub(r"([(:,;]\s*)+$", "", chu).strip()
    if len(chu) > _DAI_TOI_DA_MOT_DONG:
        cat = chu[:_DAI_TOI_DA_MOT_DONG]
        for dau in (". ", "; ", ", "):
            i = cat.rfind(dau)
            if i >= _DAI_TOI_DA_MOT_DONG // 2:
                return cat[:i + 1].rstrip()
        i = cat.rfind(" ")
        chu = (cat[:i] if i >= _DAI_TOI_DA_MOT_DONG // 2 else cat).rstrip() + "…"
    return chu


#: Tám khâu nói thành VIỆC ĐANG LÀM.
VIEC_KHAU = {
    "kich-ban": "Đang viết kịch bản",
    "giong-doc": "Đang thu giọng đọc",
    "phu-de": "Đang làm phụ đề",
    "bang-canh": "Đang chia cảnh",
    "anh": "Đang tạo ảnh",
    "clip": "Đang tạo clip",
    "thumbnail": "Đang làm ảnh bìa",
    "dung": "Đang ghép video",
}

#: Đơn vị đếm của khâu — để "116/141" đọc thành "116/141 cảnh".
DON_VI_KHAU = {"bang-canh": "cảnh", "anh": "cảnh", "clip": "cảnh"}

#: Vòng tự chạy tự đánh số việc trong nhật ký bằng `[N/M]`. Chỉ nhận dấu
#: trong NGOẶC VUÔNG — "22/09" hay một đường dẫn có gạch chéo không lọt vào.
_TIEN_DO = _re.compile(r"\[(\d{1,4})/(\d{1,4})\]")


def tien_do_nhat_ky(nhat_ky: Any) -> str:
    """`"116/141"` — tiến độ việc đang chạy, lấy từ dấu `[N/M]` của nhật ký."""
    for dong in reversed(list(nhat_ky or [])[-80:]):
        tim = _TIEN_DO.search(str(dong))
        if not tim:
            continue
        lam, tong = int(tim.group(1)), int(tim.group(2))
        if 1 <= lam <= tong and tong >= 2:
            return "{0}/{1}".format(lam, tong)
    return ""


def _cat_chu(chu: str, toi_da: int = 88) -> str:
    chu = str(chu or "").strip()
    if len(chu) <= toi_da:
        return chu
    cat = chu[:toi_da]
    i = cat.rfind(" ")
    return (cat[:i] if i >= toi_da // 2 else cat).rstrip() + "…"


def _khau_dang(k: Dict[str, Any], trang: str) -> Dict[str, Any]:
    for d in ((k.get("luot") or {}).get("khau") or []):
        if str(d.get("trang_thai") or "") == trang:
            return d
    return {}


def _viec_khau(ma_khau: str, ten_ngan: str = "") -> str:
    """"anh" → "Đang tạo ảnh"."""
    return VIEC_KHAU.get(ma_khau) or "Đang làm {0}".format(
        (ten_ngan or ma_khau or "video").lower())


def _lam_gi(ma_khau: str, ten_ngan: str = "") -> str:
    """"anh" → "tạo ảnh" — phần đuôi để ghép vào "Dừng khi …"."""
    viec = _viec_khau(ma_khau, ten_ngan)
    return viec[len("Đang "):] if viec.startswith("Đang ") else viec.lower()


#: `_mot_kenh` ghi "DD/MM HH:MM" vào `k["dang_luc"]` khi có một dòng kế hoạch
#: đã có ngày giờ (`core.trung_tam._mot_kenh`, biến `dang_luc`) — kể cả khi
#: ngày đó ở TƯƠNG LAI. `trang_thai_bay_gio` (nguồn của `bay_gio.chu`) chỉ xét
#: kế hoạch của ĐÚNG hôm nay (`dong_kh_bay_gio` lọc `_ngay(d["ngay"]) == hom_nay`
#: trong `_mot_kenh`), nên một video đã tải lên/hẹn lịch cho một ngày SAU hôm
#: nay lọt qua bộ lọc đó — câu tình trạng rơi xuống "Nghỉ hôm nay"/"Chưa chạy
#: hôm nay" dù kênh KHÔNG hề rảnh việc, chỉ là chưa tới hôm đăng. Phát hiện
#: thẳng từ `dang_luc` (không cần sửa `core.trung_tam`, ngoài phạm vi vá này —
#: chẩn đoán chủ dự án 29/09/2026, dữ liệu thật TL1-T7/TL3-T7).
_RE_DANG_LUC_TUONG_LAI = _re.compile(r"^(\d{2})/(\d{2})\s+(\d{1,2}:\d{2})$")

#: Các câu "bây giờ" coi kênh là RẢNH VIỆC — đúng những chỗ cần được ghi đè
#: nếu hoá ra đã có video chờ lên sóng một ngày sau.
_GOC_RANH_VIEC = ("Nghỉ hôm nay", "Chưa chạy hôm nay", "Chờ lịch ", "Chưa bật lịch")


def _da_hen_tuong_lai(k: Dict[str, Any]) -> str:
    """"20:00 ngày 30/09" nếu kênh đã có video hẹn lịch (tải lên hoặc đã ghi
    ngày giờ trong kế hoạch) cho một ngày SAU hôm nay — "" nếu không."""
    m = _RE_DANG_LUC_TUONG_LAI.match(str((k or {}).get("dang_luc") or "").strip())
    return "{0} ngày {1}/{2}".format(m.group(3), m.group(1), m.group(2)) if m else ""


def cau_tinh_trang(k: Dict[str, Any]) -> str:
    """MỘT câu tiếng Việt nói kênh này đang thế nào — thuần, bài kiểm gọi thẳng.

    Ví dụ: `Đang tạo ảnh — 116/141 cảnh` · `Xong, chờ bạn hẹn giờ đăng` ·
    `Đã hẹn đăng 20:00 hôm nay` · `Dừng khi tạo ảnh — máy chủ ảnh bận` ·
    `Hôm nay chưa chạy` · `Chỉ đăng, không tự làm video`.
    """
    bay = k.get("bay_gio") or {}
    goc = str(bay.get("chu") or "").strip()
    chi_tiet = str(bay.get("chi_tiet") or "").strip()

    if goc.startswith("Đang làm video"):
        d = _khau_dang(k, "dang")
        ma_khau = str(d.get("ma") or "")
        if ma_khau:
            cau = _viec_khau(ma_khau, str(d.get("ten_ngan") or ""))
        elif "khâu" in goc:
            cau = "Đang làm " + goc.split("khâu", 1)[1].strip().lower()
        else:
            cau = "Đang làm video"
        tien = tien_do_nhat_ky(k.get("nhat_ky"))
        if tien:
            dv = DON_VI_KHAU.get(ma_khau, "")
            cau += " — {0}{1}".format(tien, " " + dv if dv else "")
        return cau
    if goc.startswith("Đang chọn video"):
        return "Đang chọn video cho hôm nay"
    if goc.startswith("Đang đăng"):
        return "Đang đăng lên YouTube"

    if goc.startswith("Lỗi: khâu "):
        d = _khau_dang(k, "hong")
        ly_do = gon_dong_nhat_ky(str(d.get("loi") or chi_tiet))
        if ":" in ly_do and not d.get("loi"):
            ly_do = ly_do.split(":", 1)[1].strip() or ly_do
        return _cat_chu("Dừng khi {0}{1}".format(
            _lam_gi(str(d.get("ma") or ""), str(d.get("ten_ngan") or "")),
            " — " + ly_do if ly_do else ""))
    if goc.startswith("Lỗi bàn giao"):
        ly_do = gon_dong_nhat_ky(chi_tiet)
        return _cat_chu("Dừng khi chuyển sang máy đăng"
                        + (" — " + ly_do if ly_do else ""))
    if goc.startswith("Lỗi"):
        ly_do = gon_dong_nhat_ky(goc.split(":", 1)[1] if ":" in goc else chi_tiet)
        return _cat_chu("Dừng vì " + (ly_do or "chưa rõ lý do"))

    if goc.startswith("Chờ duyệt"):
        return "Xong, chờ bạn hẹn giờ đăng"
    if goc.startswith("Đã đăng"):
        return "Đã lên sóng hôm nay"
    if goc.startswith("Chờ đăng "):
        return "Đã hẹn đăng {0} hôm nay".format(goc[len("Chờ đăng "):].strip())
    if goc.startswith("Chờ phiên "):
        gio = str(k.get("dang_luc") or "").split()[-1:] or [""]
        return ("Đã hẹn đăng {0} hôm nay".format(gio[0]) if gio[0]
                else "Đã hẹn đăng hôm nay")
    if goc.startswith("Hẹn đăng "):
        phan = goc[len("Hẹn đăng "):].split()
        if len(phan) == 2:
            return "Đã hẹn đăng {1} ngày {0}".format(phan[0], phan[1])
        return "Đã hẹn đăng " + " ".join(phan)
    if goc.startswith("Quá giờ đăng "):
        return "Quá giờ đăng {0} mà chưa thấy lên sóng".format(
            goc[len("Quá giờ đăng "):].strip())
    if goc.startswith("Xong, chưa bàn giao"):
        return "Xong, chưa chuyển sang máy đăng"
    if goc.startswith("Nghỉ: vượt trần tiền"):
        return "Nghỉ vì đã tiêu hết tiền hôm nay"
    if goc.startswith("Dở ở khâu "):
        d = _khau_dang(k, "cho") or _khau_dang(k, "dang")
        return "Dở dang ở {0} — lượt sau làm tiếp".format(
            _lam_gi(str(d.get("ma") or ""), goc[len("Dở ở khâu "):].strip()))
    if goc.startswith("Chưa đặt trần tiền"):
        return "Chưa đặt tiền mỗi ngày — chưa sản xuất được"
    if goc.startswith(_GOC_RANH_VIEC):
        hen = _da_hen_tuong_lai(k)
        if hen:
            return "Đã hẹn đăng " + hen
    if goc.startswith("Nghỉ hôm nay"):
        return "Hôm nay nghỉ, không có video mới"
    if goc.startswith("Chờ lịch "):
        return "Chờ tới {0} rồi tự chạy".format(goc[len("Chờ lịch "):].strip())
    if goc.startswith("Chưa bật lịch"):
        return "Lịch hằng ngày đang tắt — sẽ không tự chạy"
    if goc.startswith("Chưa chạy hôm nay"):
        return "Hôm nay chưa chạy"
    if goc.startswith("Chỉ đăng"):
        return "Chỉ đăng, không tự làm video"
    if goc.startswith("Tắt tự chạy"):
        return "Đang tắt — kênh này không tự làm video"
    return _cat_chu(goc or "Chưa đọc được tình trạng")


# ═══════════════════════════════════════════════════════════════════════════
# 2) Tiện ích đọc đĩa dùng riêng cho lõi này (không đụng hàm private của
#    core.trung_tam — chỉ đọc tệp, giống hệt khuôn của nó).
# ═══════════════════════════════════════════════════════════════════════════


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return [dict(d) for d in csv.DictReader(tep)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _so(chu: Any) -> Optional[float]:
    if chu is None:
        return None
    if isinstance(chu, (int, float)):
        return float(chu)
    s = str(chu).strip().rstrip("%").replace("~", "").strip()
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _ngay(chu: Any) -> Optional[_dt.date]:
    s = str(chu or "").strip()[:10]
    for dinh in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return _dt.datetime.strptime(s, dinh).date()
        except ValueError:
            continue
    return None


def _doc_duoi(duong: str, so_byte: int = 256 * 1024) -> List[str]:
    """Mấy dòng cuối một tệp chữ — chỉ đọc `so_byte` cuối, không nuốt cả tệp."""
    try:
        with open(duong, "rb") as tep:
            tep.seek(0, os.SEEK_END)
            dai = tep.tell()
            tep.seek(max(0, dai - so_byte))
            tho = tep.read()
    except OSError:
        return []
    return tho.decode("utf-8", "replace").splitlines()


# ═══════════════════════════════════════════════════════════════════════════
# 3) Mức thẻ + video kế tiếp + ba video gần nhất
# ═══════════════════════════════════════════════════════════════════════════

#: Năm mức màu thẻ kênh — khác bốn mức của `TrangDieuKhien` cũ ở chỗ tách
#: riêng "chờ bạn" (vàng, cần người bấm) khỏi "chờ máy/chờ lịch" (xanh, không
#: cần ai làm gì) — mục 3, "Viên trạng thái" của bản thiết kế.
TOT = "tot"
CHO_BAN = "cho_ban"
LUU_Y = "luu_y"
HONG = "hong"
TAT = "tat"


def muc_the(k: Dict[str, Any]) -> str:
    """`tot|cho_ban|luu_y|hong|tat` từ `k["bay_gio"]` — màu viền/nền thẻ kênh.

    `"cho_ban"` (mức MỚI so với `TrangDieuKhien` cũ) là ca "Xong, chờ bạn
    duyệt": kênh không hỏng, nhưng đứng im chờ một người bấm nút, khác hẳn
    "Chờ đăng"/"Chờ phiên"/"Chờ lịch" (kênh tự lo, không ai phải làm gì).
    """
    bay = (k or {}).get("bay_gio") or {}
    muc = str(bay.get("muc") or "")
    chu = str(bay.get("chu") or "")
    if muc == "loi":
        return HONG
    if muc in ("tat", "nghi"):
        # "Nghỉ" vì đã có video hẹn lịch một ngày SAU hôm nay không phải kênh
        # rảnh việc — xem `_da_hen_tuong_lai`/`cau_tinh_trang`.
        if muc == "nghi" and _da_hen_tuong_lai(k or {}):
            return TOT
        return TAT
    if muc == "cho" and chu.startswith("Chờ duyệt"):
        return CHO_BAN
    if muc == "canh_bao":
        return LUU_Y
    return TOT


def video_ke_tiep(k: Dict[str, Any]) -> Dict[str, Any]:
    """Video kế tiếp của kênh: `{tieu_de, loai, ma_goi}` (`{}` nếu chưa có gì).

    Ưu tiên video đang CHỜ BẠN duyệt hoặc đã hẹn đăng hôm nay/tới (đó là thứ
    người ta cần thấy tiếp theo); không có thì tới lượt đang sản xuất dở.
    """
    ke_hoach = list((k or {}).get("ke_hoach") or [])
    for loai in ("cho_duyet", "sap_dang"):
        d = next((d for d in ke_hoach if d.get("loai") == loai and d.get("tieu_de")), None)
        if d:
            return {"tieu_de": d["tieu_de"], "loai": loai, "ma_goi": d.get("ma_goi", "")}
    video = (k or {}).get("video") or {}
    ma_goi_video = str(video.get("ma_goi") or "")
    if video.get("tieu_de"):
        # `k["video"]["tieu_de"]` (từ `core.trung_tam._mot_kenh`) là tiêu đề
        # của GÓI MỚI NHẤT theo mã lượt/bàn giao — không phân biệt gói đó đã
        # CÔNG KHAI hay chưa. Đối chiếu lại đúng dòng kế hoạch của gói này:
        # đã "da_dang" (đã đăng/đã hẹn công khai) thì KHÔNG còn là "video kế
        # tiếp" nữa (chẩn đoán chủ dự án 29/09/2026, dữ liệu thật TL2-T7).
        dong = next((d for d in ke_hoach if d.get("ma_goi") == ma_goi_video), None) \
            if ma_goi_video else None
        if dong is None or dong.get("loai") != "da_dang":
            return {"tieu_de": video["tieu_de"], "loai": "dang_lam",
                    "ma_goi": ma_goi_video}
    return {}


#: Bốn mốc tuổi chuẩn (giờ) — khớp `chi_so_ytb`/`ho_so_video` và cột
#: "Mốc mới nhất" của `bang-tom-tat.csv` (`"{giờ}h"`, xem
#: `core/chi_so_ytb/__init__.py::xuat_tom_tat`).
_MOC_CHUAN_GIO: Tuple[float, ...] = (24.0, 48.0, 72.0, 168.0)

_RE_MOC_GIO = _re.compile(r"([\d.,]+)\s*h", _re.IGNORECASE)


def _gio_moc(chu: Any) -> Optional[float]:
    m = _RE_MOC_GIO.search(str(chu or ""))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _moc_gan_nhat(gio: Optional[float]) -> Optional[float]:
    """Mốc chuẩn gần `gio` nhất, lệch không quá 30% — lệch hơn thì coi như
    KHÔNG cùng mốc (không thể so công bằng)."""
    if gio is None or gio <= 0:
        return None
    gan = min(_MOC_CHUAN_GIO, key=lambda m: abs(m - gio))
    return gan if abs(gan - gio) <= gan * 0.30 else None


def _tuoi_chu(ngay_dang: Optional[_dt.date], gio_moc: Optional[float],
             bay_gio: Optional[_dt.datetime] = None) -> str:
    if gio_moc is not None and gio_moc < 24:
        return "{0:.0f} giờ".format(gio_moc)
    if ngay_dang is None:
        return ""
    bay_gio = bay_gio or _dt.datetime.now()
    so_ngay = (bay_gio.date() - ngay_dang).days
    if so_ngay <= 0:
        return "hôm nay"
    return "{0} ngày".format(so_ngay)


def video_gan_day(goc: str, ma: str, n: int = 3,
                  bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """`n` video mới đăng gần nhất của kênh, kèm mũi tên so trung vị CÙNG MỐC
    TUỔI của chính kênh (quyết định 4, mục 4 bản thiết kế).

    Đọc `chi-so/bang-tom-tat.csv`, lọc video đời trước bằng
    `core.chi_so_ytb.loc_video` (đúng lọc `_mot_kenh` đang dùng) — KHÔNG đọc
    lại `ho-so-video/*.json` cho việc này: cột "Tỷ lệ bấm" + "Mốc mới nhất"
    của bảng tóm tắt đã đủ để so cùng mốc, đọc thêm hồ sơ chỉ tốn IO không
    đổi kết quả.
    """
    thu_muc_kenh = _kenh_mod.duong_kenh(goc, ma)
    hang = _doc_csv(os.path.join(thu_muc_kenh, "chi-so", "bang-tom-tat.csv"))
    try:
        from .chi_so_ytb import loc_video as _loc  # noqa: PLC0415

        hang = _loc.loc_hang_bang(_loc.moc_cua_thu_muc(thu_muc_kenh), hang)
    except Exception:  # noqa: BLE001 — lọc hỏng thì thôi, vẫn có bảng thô
        pass

    theo_moc: Dict[float, List[float]] = {}
    for d in hang:
        moc = _moc_gan_nhat(_gio_moc(d.get("Mốc mới nhất")))
        ctr = _so(d.get("Tỷ lệ bấm"))
        if moc is not None and ctr is not None:
            theo_moc.setdefault(moc, []).append(ctr)

    hang_sap = sorted(hang, key=lambda d: _ngay(d.get("Ngày đăng")) or _dt.date.min,
                      reverse=True)
    ra: List[Dict[str, Any]] = []
    for d in hang_sap[:max(0, int(n))]:
        ngay_dang = _ngay(d.get("Ngày đăng"))
        gio_moc = _gio_moc(d.get("Mốc mới nhất"))
        moc = _moc_gan_nhat(gio_moc)
        ctr = _so(d.get("Tỷ lệ bấm"))
        mui_ten = ""
        if moc is not None and ctr is not None:
            mau = list(theo_moc.get(moc, []))
            if ctr in mau:
                mau.remove(ctr)
            if mau:
                tv = statistics.median(mau)
                if tv > 0:
                    lech = (ctr - tv) / tv
                    mui_ten = "len" if lech > 0.10 else ("xuong" if lech < -0.10 else "ngang")
        ra.append({
            "tieu_de": str(d.get("Tiêu đề") or ""),
            "video_id": str(d.get("Mã video") or ""),
            "ngay_dang": ngay_dang.isoformat() if ngay_dang else "",
            "tuoi": _tuoi_chu(ngay_dang, gio_moc, bay_gio),
            "luot_xem": _so(d.get("Lượt xem")),
            "ty_le_bam": ctr,
            "giu_chan": _so(d.get("% độ dài")),
            "mui_ten": mui_ten,
        })
    return ra


def may_dang_hoc(goc: str, ma: str) -> str:
    """Câu ngắn "Máy đang học: …" cho thẻ kênh.

    Ba nhánh (sửa 30/09/2026, Việc 4b — tắt mượn khuôn nhóm mặc định):

    1. CHƯA có khuôn riêng hợp lệ — thiếu `video_id`, hoặc khuôn đã bị đánh
       dấu `het_hieu_luc` (khuôn mượn nhóm cũ, chính sách đã đổi) — báo đang
       THĂM DÒ: đếm số KIỂU thumbnail khác nhau đã thử trong hồ sơ video.
    2. Khuôn RIÊNG thật của chính kênh (`nguon == "kenh"`) — câu cũ, không còn
       cụm "(mượn khuôn của...)" vì đây đúng là số liệu của chính kênh.
    3. Khuôn MƯỢN còn hợp lệ (`nguon == "nhom"`, không `het_hieu_luc` — một
       máy khác tự bật `bia_khuon_nhom: true`) — GIỮ NGUYÊN câu cũ, nói rõ
       mượn của kênh nào, kẻo chủ kênh tưởng đó là số liệu của chính kênh
       mình (chẩn đoán chủ dự án 29/09/2026, dữ liệu thật TL1-T7/TL2-T7 mượn
       khuôn của TL3-T7).
    """
    khuon = khuon_bia.doc_khuon(goc, ma)
    het_hieu_luc = isinstance(khuon, dict) and bool(khuon.get("het_hieu_luc"))
    if not isinstance(khuon, dict) or not khuon.get("video_id") or het_hieu_luc:
        return _cau_dang_tham_do(goc, ma)

    ngay = str(khuon.get("ngay_so_lieu") or "")[:10]
    cau = ("Máy đang học: khuôn ảnh bìa thắng đổi {0}".format(ngay) if ngay
          else "Máy đang học: đã có khuôn ảnh bìa thắng")
    if khuon.get("nguon") == "kenh":
        cau = cau.replace("Máy đang học: ", "Máy đang học: khuôn riêng: ", 1)
    try:
        cau += " (tỷ lệ bấm {0:.1f}%)".format(float(khuon.get("ctr")))
    except (TypeError, ValueError):
        pass
    kenh_goc = str(khuon.get("kenh_goc") or "").strip()
    if khuon.get("nguon") == "nhom" and kenh_goc and kenh_goc != ma:
        cau += " (mượn khuôn của {0})".format(kenh_goc)
    return cau


#: Tổng số kiểu thumbnail khả dĩ (`core.auto_khau.KIEU_THUMB`) — lùi về hằng
#: số này nếu đọc động hỏng (module đổi tên/không nạp được).
_SO_KIEU_THUMB_MAC_DINH = 7


def _cau_dang_tham_do(goc: str, ma: str) -> str:
    """Câu "Máy đang học: thumbnail: đang thử kiểu (x/tổng)…" khi kênh chưa
    có khuôn thắng hợp lệ — đếm số KIỂU khác nhau (`thumbnail.kieu`) đã từng
    dùng trong hồ sơ video của kênh. Không bao giờ ném lỗi ra ngoài."""
    tong = _SO_KIEU_THUMB_MAC_DINH
    try:
        from . import auto_khau  # noqa: PLC0415
        tong = len(auto_khau.KIEU_THUMB) or _SO_KIEU_THUMB_MAC_DINH
    except Exception:  # noqa: BLE001 — đọc hằng số hỏng thì lùi về mặc định
        tong = _SO_KIEU_THUMB_MAC_DINH

    so_kieu = 0
    try:
        from . import ho_so_video  # noqa: PLC0415
        thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, ma)
        cac_kieu = set()
        for ten in os.listdir(thu_muc):
            if not ten.endswith(".json"):
                continue
            ho_so = ho_so_video.doc_ho_so(goc, ma, ten[:-len(".json")])
            if not isinstance(ho_so, dict):
                continue
            kieu = (ho_so.get("thumbnail") or {}).get("kieu") if isinstance(ho_so.get("thumbnail"), dict) else ""
            if kieu:
                cac_kieu.add(kieu)
        so_kieu = len(cac_kieu)
    except Exception:  # noqa: BLE001 — đếm hỏng thì coi như 0, không chặn thẻ kênh
        so_kieu = 0

    return "Máy đang học: thumbnail: đang thử kiểu ({0}/{1}), chưa đủ dữ liệu riêng".format(
        min(so_kieu, tong), tong)


def _video_ke_tiep_tu(goc: str, ma: str, bay_gio: _dt.datetime) -> str:
    """"29/09 20:00" — khi CHƯA có video kế tiếp, lúc máy mở cửa sản xuất lại
    để chọn nguồn mới cho kênh (`core.tu_chay._cua_so_san_xuat`, chỉ đọc).
    `""` khi không tính được (kênh không tự chạy, thiếu cài đặt, lỗi đọc)."""
    try:
        kenh_obj = _kenh_mod.doc_kenh(goc, ma)
        _mo, _ly_do, thong_tin = tu_chay._cua_so_san_xuat(  # noqa: SLF001
            goc, ma, kenh_obj, bay_gio=bay_gio)
    except Exception:  # noqa: BLE001 — gợi ý phụ, đọc hỏng thì thôi
        return ""
    iso = str(thong_tin.get("mo_cua_san_xuat") or "")
    if not iso:
        return ""
    try:
        return _dt.datetime.fromisoformat(iso).strftime("%d/%m %H:%M")
    except ValueError:
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# 4) Việc tay không có dấu trên đĩa — ghim, nháp thừa
# ═══════════════════════════════════════════════════════════════════════════

#: `- [2026-09-29 20:05] **tiêu đề** — https://www.youtube.com/watch?v=ID`
_RE_GHIM_DAU = _re.compile(
    r"^-\s*\[(?P<luc>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\]\s*"
    r"\*\*(?P<tieu_de>.*?)\*\*\s*—\s*"
    r"https?://www\.youtube\.com/watch\?v=(?P<vid>[\w-]+)\s*$")
#: Dòng ghi chú ngay dưới, thụt hai khoảng trắng: `  > chữ`.
_RE_GHIM_CHU = _re.compile(r"^\s{2}>\s?(?P<chu>.*)$")


def doc_can_ghim(goc: str, ma: str) -> List[Dict[str, str]]:
    """`CHANNEL/<ma>/can-ghim.md` → `[{luc, tieu_de, video_id, ghi_chu}]`.

    Tệp KHÔNG có dấu "đã ghim" — đó là việc của `doc_da_xong`/`danh_dau_xong`
    (khoá `"ghim:<video_id>"`), vì đánh dấu trên chính can-ghim.md sẽ đụng độ
    với con người/điện thoại có thể đang sửa tệp này song song.
    """
    duong = os.path.join(_kenh_mod.duong_kenh(goc, ma), "can-ghim.md")
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            dong = tep.readlines()
    except OSError:
        return []
    ra: List[Dict[str, str]] = []
    cho: Optional[Dict[str, str]] = None
    for d in dong:
        m = _RE_GHIM_DAU.match(d.rstrip("\n"))
        if m:
            cho = {"luc": m.group("luc"), "tieu_de": m.group("tieu_de"),
                  "video_id": m.group("vid"), "ghi_chu": ""}
            ra.append(cho)
            continue
        mc = _RE_GHIM_CHU.match(d.rstrip("\n"))
        if mc and cho is not None:
            cho["ghi_chu"] = mc.group("chu").strip()
            cho = None
    return ra


#: Dòng `dang-dom.log` do `vm/may_dang_dom.py::_canh_bao` ghi qua
#: `logging.Formatter("%(asctime)s %(levelname)s: %(message)s")`:
#: `2026-09-29 10:15:23,456 INFO: CẢNH BÁO K1: NHÁP THỪA trên kênh <id> (…)`.
_RE_NHAP_THUA = _re.compile(
    r"^(?P<luc>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+\s+\S+:\s*"
    r"CẢNH BÁO\s+(?P<ma>\S+?):\s*NHÁP THỪA trên kênh\s+(?P<vid>\S+)")


def doc_nhap_thua(thu_muc_vm: str, ma: str = "") -> List[Dict[str, str]]:
    """Bản nháp thừa còn trên Studio, đọc 256KB cuối `<vm>/logs/dang-dom.log`.

    `ma`: lọc theo đúng mã kênh (rỗng = mọi kênh). Một video có thể được cảnh
    báo nhiều lần (nhiều lượt chạy) — chỉ giữ dòng MỚI NHẤT của mỗi
    `(ma, video_id)`.
    """
    duong = os.path.join(thu_muc_vm, "logs", "dang-dom.log")
    theo_khoa: Dict[Tuple[str, str], Dict[str, str]] = {}
    for dong in _doc_duoi(duong):
        m = _RE_NHAP_THUA.search(dong)
        if not m:
            continue
        ma_kenh = m.group("ma")
        if ma and ma_kenh != ma:
            continue
        khoa = (ma_kenh, m.group("vid"))
        theo_khoa[khoa] = {"luc": m.group("luc"), "kenh": ma_kenh,
                           "video_id": m.group("vid")}
    return sorted(theo_khoa.values(), key=lambda d: d["luc"])


#: Tên tiếng Việt cho các mã bước `kiem_dom()` có thể liệt vào `hong` —
#: `vm/may_dang_dom.py::kiem_dom`/`_kiem_muc_2`/`_kiem_lich_trang_sua`. Không
#: đủ mọi mã (máy có thể thêm mã mới) — mã lạ thì hiện nguyên mã, còn hơn im
#: lặng nuốt mất tin hỏng.
_TEN_BUOC_KIEM = {
    "uc": "mở kênh (chọn UC)",
    "hop_upload": "hộp tải video lên",
    "nut_chon_tep": "nút chọn tệp video",
    "o_tep_video": "ô chọn tệp video",
    "cam_bam": "chặn bấm nhầm nút phản hồi Chrome",
    "hang_video": "hàng video trong danh sách",
    "hang_tieu_de": "cột tiêu đề trong danh sách",
    "hang_sua_nhap": "nút sửa bản nháp",
    "tieu_de": "ô tiêu đề",
    "mo_ta": "ô mô tả",
    "nut_thumbnail": "nút tải ảnh bìa",
    "playlist_mo": "hộp chọn danh sách phát",
    "hien_them": "nút Hiện thêm",
    "o_the": "ô thẻ (tag)",
    "the_da_co": "danh sách thẻ đã có",
    "khong_tre_em": "công tắc Không dành cho trẻ em",
    "ai_co": "ô nội dung do AI tạo",
    "hien_thi_trang_sua": "hộp Chế độ hiển thị",
    "ban_nhap": "bản nháp để kiểm",
    "tien_do": "thanh tiến độ xử lý video",
    "phu_de_them": "nút thêm phụ đề",
    "mhkt_nhap": "ô nhập màn hình kết thúc",
    "mhkt_them": "nút thêm màn hình kết thúc",
    "the_them": "nút thêm thẻ (card)",
    "nut_tiep": "nút Tiếp theo",
    "len_lich_mo": "nút mở hộp Lên lịch",
    "o_ngay_mo": "ô mở lịch chọn ngày",
    "o_gio": "ô giờ đăng",
    "nut_xong": "nút Xong (Lên lịch)",
    "o_ngay": "ô chọn ngày trên lịch",
    "sua_hien_thi_mo": "nút mở Chế độ hiển thị (trang sửa)",
    "sua_hop_hien_thi": "hộp Chế độ hiển thị (trang sửa)",
    "dong_hop_hien_thi": "đóng hộp Chế độ hiển thị",
    "dong_hop_upload": "đóng hộp tải lên",
    "hang_video_playlist": "danh sách phát",
    "loi_bat_ngo": "một bước bất ngờ (xem ghi chú)",
}


def doc_kiem_dom(thu_muc_vm: str, ma: str) -> Optional[Dict[str, Any]]:
    """`<vm>/logs/kiem-dom/<ma>.json` (ghi bởi `--kiem-dom`), kèm tên bước
    tiếng Việt cho từng mã trong `hong`. `None` nếu chưa kiểm lần nào."""
    du = _doc_json(os.path.join(thu_muc_vm, "logs", "kiem-dom", "{0}.json".format(ma)))
    if not isinstance(du, dict):
        return None
    du = dict(du)
    du["hong_ten"] = [_TEN_BUOC_KIEM.get(b, b) for b in (du.get("hong") or [])]
    return du


def doc_tinh_trang(goc: str) -> Dict[str, Any]:
    """`workspace/tinh-trang.json` — ghi bởi `core.gac_tong.bao_cao_su_co`
    (lịch Windows `ShopAPI-GacTong`, mỗi 15 phút, xem `workspace/ban-va/
    2026-09-29-tu-canh-loi/GHI-CHU.md` mục 2). CHỈ ĐỌC LẠI, không tính gì
    thêm — phân tích sự cố "chế độ chạy max" (đứng khâu, lỗi lặp, khoá chết…)
    thuộc về `core.gac_tong`, không lặp lại ở đây (module đó NHẬP ngược
    `core.bang_dieu_khien` để đọc `doc_kiem_dom`, nên module này KHÔNG được
    nhập `core.gac_tong` — nhập ngược sẽ vòng tròn).

    Trả `{"luc","kenh": {ma: {"trang_thai","ly_do"}}, "so_su_co","may": {...}}`
    hoặc `{}` khi chưa có tệp (lịch chưa chạy lần nào / máy chưa nối lịch —
    KHÔNG PHẢI lỗi, chỉ là chưa có dữ liệu)."""
    du = _doc_json(os.path.join(goc, "workspace", "tinh-trang.json"))
    return du if isinstance(du, dict) else {}


# ═══════════════════════════════════════════════════════════════════════════
# 5) "Đã xong" cho việc không có dấu trên đĩa (ghim, nháp thừa)
# ═══════════════════════════════════════════════════════════════════════════

_TEP_VIEC_XONG = ("workspace", "viec-da-xong.json")


def _duong_viec_xong(goc: str) -> str:
    return os.path.join(goc, *_TEP_VIEC_XONG)


def doc_da_xong(goc: str) -> Dict[str, str]:
    """`{"ghim:<vid>": "<iso>", "nhap:<vid>": "<iso>", ...}`."""
    du = _doc_json(_duong_viec_xong(goc))
    return du if isinstance(du, dict) else {}


def danh_dau_xong(goc: str, khoa: str, *, bay_gio: Optional[_dt.datetime] = None) -> None:
    """Đánh dấu một việc-không-có-dấu-trên-đĩa là đã làm — ghi NGUYÊN TỬ
    (`.tmp` rồi `os.replace`, cùng khuôn `core/tien_trinh_con.py::_ghi_so`).

    ĐÂY LÀ TỆP DUY NHẤT `core/bang_dieu_khien.py` ĐƯỢC PHÉP GHI.
    """
    muc = doc_da_xong(goc)
    muc[str(khoa)] = (bay_gio or _dt.datetime.now()).isoformat(timespec="seconds")
    duong = _duong_viec_xong(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(muc, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


# ═══════════════════════════════════════════════════════════════════════════
# 6) Đường ghi công tắc — tách thuần từ `TrangDieuKhien._doi_*` (Qt cũ)
# ═══════════════════════════════════════════════════════════════════════════
#
# Mỗi hàm chỉ làm MỘT việc ghi, không hỏi, không QMessageBox — lớp giao diện
# (Việc 2) lo phần hỏi/báo lỗi. Hai cửa ghi có sẵn, không hàm nào ở đây tự mở
# tệp: `trung_tam.ghi_cai_kenh` (kenh.yaml) và `vm_cai_dat.luu` (may-ao.json).


def doi_cong_tac(goc: str, ma: str, khoa: str, bat: bool) -> None:
    """`tu_chay`/`tu_don` → `kenh.yaml`; `tu_dang`/`tu_tra_loi_cmt` → máy ảo."""
    if khoa in ("tu_chay", "tu_don"):
        tt.ghi_cai_kenh(goc, ma, **{khoa: bool(bat)})
    else:
        vm_cai_dat.luu(goc, ma, **{khoa: bool(bat)})


def doi_ngan_sach(goc: str, ma: str, gia_tri: int) -> None:
    tt.ghi_cai_kenh(goc, ma, ngan_sach_ngay=int(gia_tri))


def doi_giu_luot(goc: str, ma: str, so: int) -> None:
    tt.ghi_cai_kenh(goc, ma, giu_toi_da_luot=int(so))


def doi_gio_dang(goc: str, ma: str, gio: str) -> None:
    if gio:
        tt.ghi_cai_kenh(goc, ma, gio_dang=str(gio))


def doi_nhip_dang(goc: str, ma: str, chu_ky_ngay: int, truoc_gio: int) -> None:
    tt.ghi_cai_kenh(goc, ma, chu_ky_dang_ngay=max(1, int(chu_ky_ngay)),
                    san_xuat_truoc_gio=max(0, int(truoc_gio)))


def doi_phut_phien(goc: str, ma: str, phut: int) -> None:
    vm_cai_dat.luu(goc, ma, phien_truoc_phut=int(phut))


#: Công tắc 3 nấc của giám đốc kênh (`kenh.yaml: giam_doc`) — nhãn người đọc.
CHE_DO_GIAM_DOC = (("tat", "Tắt"), ("goi_y", "Gợi ý (chỉ ghi, không áp)"), ("tu_ap", "Tự áp (có giới hạn)"))


def doi_giam_doc(goc: str, ma: str, che_do: str) -> None:
    """`kenh.yaml: giam_doc: tat | goi_y | tu_ap` — giá trị lạ thì ném lỗi (giao diện báo)."""
    che_do = str(che_do or "").strip().lower()
    if che_do not in {k for k, _ in CHE_DO_GIAM_DOC}:
        raise ValueError("chế độ giám đốc kênh lạ: {0}".format(che_do))
    tt.ghi_cai_kenh(goc, ma, giam_doc=che_do)


def giam_doc_the(goc: str, ma: str) -> Dict[str, Any]:
    """Dòng giám đốc kênh của thẻ kênh: `{che_do, cau, bao_cao}` — `bao_cao` = đường `BAO-CAO-TUAN.md`
    ("" nếu chưa có). Chỉ đọc đĩa; hỏng thì chế độ "tat", câu rỗng."""
    try:
        from .giam_doc import bao_cao as _bc  # noqa: PLC0415
        from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

        cai = _kenh_mod.doc_yaml(os.path.join(_kenh_mod.duong_kenh(goc, ma), _kenh_mod.TEP_KENH)) or {}
        che_do = str(cai.get("giam_doc") or "tat").strip().lower()
        che_do = che_do if che_do in {k for k, _ in CHE_DO_GIAM_DOC} else "tat"
        duong = os.path.join(thu_muc_giam_doc(goc, ma), _bc.TEP_BAO_CAO_MD)
        co = os.path.isfile(duong)
        cau = _bc.cau_the(goc, ma) if (che_do != "tat" or co) else ""
        return {"che_do": che_do, "cau": cau, "bao_cao": duong if co else ""}
    except Exception:  # noqa: BLE001 — dòng phụ, không làm hỏng thẻ
        return {"che_do": "tat", "cau": "", "bao_cao": ""}


#: Khoá `workspace/trung-tam.json` nhớ những kênh mà "Tạm dừng tất cả" đã tắt.
KHOA_TAM_DUNG = "tam_dung_kenh"


def tam_dung_tat_ca(goc: str, dang_bat: List[str]) -> List[str]:
    """Tắt `tu_chay` của từng mã trong `dang_bat`, nhớ lại danh sách đã tắt
    (để `bat_lai_tam_dung` không bật nhầm kênh vốn tắt từ trước). Trả về
    danh sách THẬT SỰ đã tắt được."""
    da_tat: List[str] = []
    for ma in dang_bat:
        tt.ghi_cai_kenh(goc, ma, tu_chay=False)
        da_tat.append(ma)
    tt.luu_cai(goc, **{KHOA_TAM_DUNG: da_tat})
    return da_tat


def bat_lai_tam_dung(goc: str, cac_ma: List[str]) -> None:
    for ma in cac_ma:
        tt.ghi_cai_kenh(goc, ma, tu_chay=True)
    tt.luu_cai(goc, **{KHOA_TAM_DUNG: []})


# ═══════════════════════════════════════════════════════════════════════════
# 7) Dòng MÁY + ví còn chạy bao lâu
# ═══════════════════════════════════════════════════════════════════════════

NGUONG_VI_NGAY_LUU_Y = 3.0
NGUONG_VI_NGAY_HONG = 1.0
NGUONG_VI_VND_HONG = 100_000

GB_DIA_LUU_Y = 25.0
GB_DIA_HONG = 10.0


def so_ngay_con_chay(goc: str, ma_cac_kenh: List[str], so_du_micro: Optional[int],
                     *, bay_gio: Optional[_dt.datetime] = None) -> Optional[float]:
    """Số dư ví ÷ tiền trung bình MỖI NGÀY CÓ SẢN XUẤT trong 7 ngày gần nhất
    (cộng mọi kênh, qua `trung_tam._tien_ngay`) — `None` = "chưa ước được".
    """
    if so_du_micro is None:
        return None
    bay_gio = bay_gio or _dt.datetime.now()
    hom_nay = bay_gio.date()
    tien_theo_ngay: List[int] = []
    for i in range(7):
        ngay = hom_nay - _dt.timedelta(days=i)
        tong, co_sx = 0, False
        for ma in ma_cac_kenh:
            bc = _doc_json(tu_chay.duong_bao_cao_ngay(goc, ma, ngay.isoformat()))
            if isinstance(bc, dict) and isinstance(bc.get("runs"), list):
                t = tt._tien_ngay(bc)  # noqa: SLF001 — hàm nguồn ĐÃ được phép gọi (mục 5)
                if t:
                    tong += t
                    co_sx = True
        if co_sx:
            tien_theo_ngay.append(tong)
    if not tien_theo_ngay:
        return None
    tb_ngay = sum(tien_theo_ngay) / len(tien_theo_ngay)
    if tb_ngay <= 0:
        return None
    return (so_du_micro / MICRO_PER_VND) / tb_ngay


def dong_may(goc: str, anh: Dict[str, Any], *, bay_gio: Optional[_dt.datetime] = None,
            so_du_micro: Optional[int] = None, trang_thai_may: Optional[Dict[str, Any]] = None,
            gio_lich: Optional[str] = None) -> Dict[str, Any]:
    """Dòng "MÁY": ví (+ số ngày còn chạy), ổ đĩa, máy chạy nền, lịch.

    KHÔNG có "máy bật từ bao giờ" (`GetTickCount64`) — đó là một lệnh
    `ctypes` của riêng Windows/giao diện, không phải dữ liệu đọc đĩa; Việc 2
    tự thêm vào khi vẽ trang.
    """
    ma_cac_kenh = [str(k.get("ma") or "") for k in (anh.get("kenh") or [])]
    so_ngay = so_ngay_con_chay(goc, ma_cac_kenh, so_du_micro, bay_gio=bay_gio)
    so_du_vnd = (so_du_micro / MICRO_PER_VND) if so_du_micro is not None else None
    try:  # số ngày của van ví (chi/ngày = số lớn nhất của các nguồn thật) nếu còn tươi (<1 giờ)
        from . import van_vi as _vv  # noqa: PLC0415

        _dg = (_vv.doc_trang_thai(goc).get("danh_gia") or {})
        _t = _vv.doc_trang_thai(goc).get("luc")
        _bg = (bay_gio or _dt.datetime.now()).timestamp()
        if (_dg.get("ngay_con") is not None and _t and 0 <= _bg - float(_t) < 3600
                and (so_ngay is None or float(_dg["ngay_con"]) < so_ngay)):
            so_ngay = float(_dg["ngay_con"])
    except Exception:  # noqa: BLE001
        pass
    muc_vi = TOT
    if so_ngay is not None:
        if so_ngay < NGUONG_VI_NGAY_HONG or (so_du_vnd is not None
                                             and so_du_vnd < NGUONG_VI_VND_HONG):
            muc_vi = HONG
        elif so_ngay < NGUONG_VI_NGAY_LUU_Y:
            muc_vi = LUU_Y

    o_dia = anh.get("o_dia") or {}
    con_gb = o_dia.get("con_gb")
    muc_dia = TOT
    if con_gb is not None:
        muc_dia = HONG if con_gb < GB_DIA_HONG else (LUU_Y if con_gb < GB_DIA_LUU_Y else TOT)

    return {
        "vi": {"micro": so_du_micro, "vnd": so_du_vnd, "so_ngay_con_chay": so_ngay,
              "muc": muc_vi},
        "o_dia": {"con_gb": con_gb, "muc": muc_dia},
        "may_nen": dict(trang_thai_may or {}),
        "lich": {"bat": bool(gio_lich), "gio": gio_lich or ""},
        # 29/09/2026 (full công suất, Bước D): một dòng công suất 24h từ nhật ký
        # khe — `core.cong_suat.ghi_hien_tai` (nhịp điều phối ghi mỗi 10'). Chỉ
        # THÊM trường; bản cũ quá 3 giờ thì rỗng (không nói số cũ).
        "cong_suat": _cong_suat_may(goc),
        # 29/09/2026 (kiểm toán #12): chi phí THẬT ngày hôm qua, đọc lại sổ
        # `workspace/chi-phi/<ngày>.json` — KHÔNG gọi mạng ở đây (`core.chi_phi
        # .lay_va_luu` là lượt gọi thật, do lịch/CLI riêng chạy). Chưa có sổ
        # (máy mới, hoặc lịch chưa chạy lần nào) thì rỗng, trang tự ẩn dòng đó.
        "chi_phi_that": _chi_phi_hom_qua(goc),
        # 01/10/2026: một dòng tổng giám đốc (`giam_doc.tong.cau_the`) — {cau, bao_cao}; chưa họp thì rỗng.
        "cong_ty": _cong_ty(goc),
    }


def _cong_ty(goc: str) -> Dict[str, str]:
    try:
        from .giam_doc import tong  # noqa: PLC0415

        return tong.cau_the(goc)
    except Exception:  # noqa: BLE001 — dòng phụ
        return {"cau": "", "bao_cao": ""}


def _chi_phi_hom_qua(goc: str) -> Dict[str, Any]:
    try:
        from . import chi_phi  # noqa: PLC0415

        cs = chi_phi.hom_qua(goc)
    except Exception:  # noqa: BLE001 — dòng phụ, đọc hỏng thì thôi
        return {}
    if cs is None:
        return {}
    return {
        "ngay": cs.ngay, "tong_micro": cs.tong_micro,
        "moi_video_micro": cs.moi_video_micro,
        "so_video": cs.so_video_doi_chieu, "nguon_so_video": cs.nguon_so_video,
        "dong": cs.dong_mot_dong(),
    }


def _cong_suat_may(goc: str) -> Dict[str, Any]:
    try:
        from . import cong_suat  # noqa: PLC0415

        cs = cong_suat.doc_hien_tai(goc)
    except Exception:  # noqa: BLE001 — dòng phụ, đọc hỏng thì thôi
        return {}
    if not cs:
        return {}
    return {"cau": str(cs.get("cau") or ""), "phan_tram_khe_nang": cs.get("phan_tram_khe_nang"),
            "lan_api": cs.get("lan_api"), "con_du_video_ngay": cs.get("con_du_video_ngay"),
            "de_xuat": cs.get("de_xuat"), "luc": cs.get("luc")}


# ═══════════════════════════════════════════════════════════════════════════
# 8) "Việc của bạn" — 14 dòng, mục 3 bản thiết kế
# ═══════════════════════════════════════════════════════════════════════════

#: Mức việc (khác vocabulary `muc_the`, xem chú thích trên): `HONG` dùng
#: chung giá trị `"hong"` với mức thẻ — kiểm nhanh `if muc == bdk.HONG` đúng ở
#: cả hai chỗ; `CANH_BAO`/`THUONG` là hai mức riêng của bảng việc (⚠ cần
#: người, • thông tin, không gấp).
CANH_BAO = "canh_bao"  # ⚠ — cần người, chưa chặn
THUONG = "thuong"  # • — thông tin, không gấp

_THU_TU_MUC = {HONG: 0, CANH_BAO: 1, THUONG: 2}

#: Ba con máy `GiamSat.trang_thai()` theo dõi — tên tiếng Việt để ghép câu.
_TEN_MAY_NEN = {"agent": "Máy chạy nền (Agent)", "tu_dang": "Máy đăng",
               "tu_tra_loi_cmt": "Máy trả lời bình luận"}


def _doc_che_do_phien(thu_muc_vm: str) -> bool:
    du = _doc_json(os.path.join(thu_muc_vm, "cai-dat-tool.json"))
    return bool(du.get("che_do_phien")) if isinstance(du, dict) else False


def _viec(khoa: str, muc: str, chu: str, goi_y: str = "", kenh: str = "",
         nut: Optional[List[Tuple[str, str, Dict[str, Any]]]] = None,
         xong_tay: bool = False) -> Dict[str, Any]:
    return {"khoa": khoa, "muc": muc, "kenh": kenh, "chu": chu, "goi_y": goi_y,
           "nut": list(nut or []), "xong_tay": xong_tay}


def _viec_cho_duyet(goc: str, k: Dict[str, Any], bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Dòng 1 + 2: video xong chờ duyệt, còn trong hạn hoặc đã quá hạn chờ.

    Gọi lại ĐÚNG bộ dò quá hạn của `tu_chay._cua_so_san_xuat` (mã gói trong
    `qua_han_cho_dang`) thay vì tính lại tuổi gói — sổ [CHỜ QUÁ HẠN] và màn
    hình phải luôn nói cùng một chuyện.
    """
    ma = str(k.get("ma") or "")
    ke_hoach = {d.get("ma_goi"): d for d in (k.get("ke_hoach") or []) if d.get("ma_goi")}
    cho_duyet = [ma_goi for ma_goi, d in ke_hoach.items() if d.get("loai") == "cho_duyet"]
    if not cho_duyet:
        return []
    qua_han: set = set()
    nguong_ngay = 3
    try:
        kenh_obj = _kenh_mod.doc_kenh(goc, ma)
        nguong_ngay = int(getattr(kenh_obj, "cho_dang_toi_da_ngay", 3) or 3)
        _mo, _ly_do, thong_tin = tu_chay._cua_so_san_xuat(  # noqa: SLF001 — hàm nguồn ĐÃ được phép gọi
            goc, ma, kenh_obj, bay_gio=bay_gio)
        qua_han = set(thong_tin.get("qua_han_cho_dang") or [])
    except Exception:  # noqa: BLE001 — dò quá hạn hỏng thì vẫn phải ra dòng 1
        pass

    ra: List[Dict[str, Any]] = []
    for ma_goi in cho_duyet:
        d = ke_hoach[ma_goi]
        tieu_de = str(d.get("tieu_de") or "")
        tham_so = {"ma": ma, "ma_goi": ma_goi}
        if ma_goi in qua_han:
            ra.append(_viec(
                "qua-han:" + ma_goi, CANH_BAO, kenh=ma,
                chu="Video đã chờ quá {0} ngày chưa hẹn giờ — máy đã làm tiếp video "
                    "sau: 「{1}」".format(nguong_ngay, tieu_de),
                goi_y="→ hẹn giờ đăng, hoặc bấm Đã đăng tay nếu đã tự đăng rồi",
                nut=[("Xem video", "xem_video", tham_so),
                     ("Hẹn giờ", "hen_gio", tham_so),
                     ("Đã đăng tay", "danh_dau_dang_tay", tham_so),
                     ("Bỏ", "bo_dang", tham_so)]))
        else:
            ra.append(_viec(
                "cho-duyet:" + ma_goi, CANH_BAO, kenh=ma,
                chu="Video mới xong, chờ bạn hẹn giờ đăng: 「{0}」".format(tieu_de),
                goi_y="→ xem video rồi hẹn giờ đăng",
                nut=[("Xem video", "xem_video", tham_so),
                     ("Hẹn giờ", "hen_gio", tham_so),
                     ("Bỏ", "bo_dang", tham_so)]))
    return ra


def viec_cua_ban(goc: str, *, anh: Dict[str, Any], bay_gio: Optional[_dt.datetime] = None,
                 so_du_micro: Optional[int] = None,
                 trang_thai_may: Optional[Dict[str, Any]] = None,
                 co_client: bool = True, gio_lich: Optional[str] = None,
                 thu_muc_vm: str = "") -> List[Dict[str, Any]]:
    """Danh sách việc tay của "bạn" — mỗi phần tử `{khoa, muc, kenh, chu,
    goi_y, nut, xong_tay}`, xếp hỏng (✕) trước, cần xem (⚠) sau, thông tin (•)
    cuối (mục 3, bảng "Khối việc của bạn").

    `thu_muc_vm`: `trung_tam.thu_muc_vm(goc)` của người gọi (`anh_bang` tự
    điền) — để rỗng thì bỏ qua ba dòng đọc từ `vm/` (ghim/nháp thừa vẫn đọc
    từ `CHANNEL/`, không cần `vm/`).
    """
    bay_gio = bay_gio or _dt.datetime.now()
    kenh_ds = list(anh.get("kenh") or [])
    da_xong = doc_da_xong(goc)
    ra: List[Dict[str, Any]] = []

    for k in kenh_ds:
        ma = str(k.get("ma") or "")
        bay = k.get("bay_gio") or {}
        chu_bay = str(bay.get("chu") or "")

        # 1+2) chờ duyệt / quá hạn chờ.
        ra += _viec_cho_duyet(goc, k, bay_gio)

        # 3) quá giờ đăng mà chưa thấy lên sóng.
        if chu_bay.startswith("Quá giờ đăng "):
            ma_goi = str((k.get("video") or {}).get("ma_goi") or "")
            tham_so = {"ma": ma, "ma_goi": ma_goi}
            ra.append(_viec(
                "qua-gio:" + ma, HONG, kenh=ma, chu=cau_tinh_trang(k),
                goi_y="→ xem nhật ký máy đăng, hoặc đánh dấu đã đăng tay nếu đã tự đăng",
                nut=[("Nhật ký máy đăng", "nhat_ky_may_dang", {"ma": ma}),
                     ("Đã đăng tay", "danh_dau_dang_tay", tham_so)]))

        # 9) mức lỗi — dòng "Bây giờ" của chính kênh đang là LỖI.
        if str(bay.get("muc") or "") == "loi":
            ra.append(_viec(
                "loi:" + ma, HONG, kenh=ma, chu=cau_tinh_trang(k),
                goi_y="→ bấm Chạy lại, hoặc xem nhật ký nếu vẫn hỏng",
                nut=[("Chạy lại", "chay_lai", {"ma": ma}),
                     ("Nhật ký", "nhat_ky", {"ma": ma})]))

        # 4) ghim chưa đánh dấu.
        for pin in doc_can_ghim(goc, ma):
            khoa = "ghim:" + pin["video_id"]
            if khoa in da_xong:
                continue
            url = "https://www.youtube.com/watch?v={0}".format(pin["video_id"])
            ra.append(_viec(
                khoa, THUONG, kenh=ma,
                chu="Ghim bình luận mở đầu cho 「{0}」".format(pin.get("tieu_de") or ""),
                goi_y="→ chép link, ghim bằng điện thoại hoặc máy nhà",
                nut=[("Chép link", "chep_link", {"url": url}),
                     ("Đã ghim", "danh_dau_xong", {"khoa": khoa})],
                xong_tay=True))

        # 5) nháp thừa chưa đánh dấu.
        if thu_muc_vm:
            for nhap in doc_nhap_thua(thu_muc_vm, ma):
                khoa = "nhap:" + nhap["video_id"]
                if khoa in da_xong:
                    continue
                url = "https://studio.youtube.com/video/{0}/edit".format(nhap["video_id"])
                ra.append(_viec(
                    khoa, THUONG, kenh=ma,
                    chu="Có bản nháp thừa trên Studio, bạn xoá tay giúp ({0})".format(
                        nhap["video_id"]),
                    goi_y="→ chép link Studio rồi xoá tay bản nháp thừa",
                    nut=[("Chép link Studio", "chep_link", {"url": url}),
                         ("Đã xoá", "danh_dau_xong", {"khoa": khoa})],
                    xong_tay=True))

        # 10) máy đăng không nhận ra một ô nào đó trên Studio — CHỈ với kênh
        # thật sự dùng máy đăng DOM (`vm/may_dang_dom.py`): kênh đang ở đường
        # ảnh cũ (`cach_dang="anh"`) hay chưa bật máy đăng (`tu_dang=false`)
        # thì kết quả kiểm DOM không liên quan gì tới kênh đó (chẩn đoán chủ
        # dự án 29/09/2026, dữ liệu thật TL4-T7: tu_dang=false, cach_dang=anh).
        cai_vm = vm_cai_dat.doc(goc, ma) if thu_muc_vm else {}
        dung_may_dang_dom = bool(cai_vm.get("tu_dang")) and str(
            cai_vm.get("cach_dang") or "") in ("dom", "tu_dong")
        if thu_muc_vm and dung_may_dang_dom:
            kq = doc_kiem_dom(thu_muc_vm, ma)
            if kq is not None and not kq.get("ok", True):
                buoc = ", ".join(kq.get("hong_ten") or kq.get("hong") or [])
                ra.append(_viec(
                    "kiem-dom:" + ma, CANH_BAO, kenh=ma,
                    chu="Máy đăng không nhận ra {0} trên Studio (kiểm {1}). Cần "
                        "người lập trình sửa.".format(buoc or "một ô", kq.get("ngay") or "?"),
                    goi_y="→ báo người lập trình, kèm ngày kiểm ở trên",
                    nut=[("Xem chi tiết", "xem_chi_tiet_kiem", {"ma": ma})]))

        # 13) số liệu Studio cũ.
        duong_csv = os.path.join(_kenh_mod.duong_kenh(goc, ma), "chi-so", "bang-tom-tat.csv")
        try:
            tuoi_gio = (bay_gio.timestamp() - os.path.getmtime(duong_csv)) / 3600.0
        except OSError:
            tuoi_gio = None
        if tuoi_gio is not None and tuoi_gio > 48 and bool(k.get("tu_chay")):
            ra.append(_viec(
                "so-lieu-cu:" + ma, THUONG, kenh=ma,
                chu="Số liệu Studio cũ {0:.0f} ngày".format(tuoi_gio / 24.0),
                goi_y="→ mở Nghiên cứu để quét lại số liệu",
                nut=[("Nhật ký", "nhat_ky", {"ma": ma})]))

    # 14) Người gác tổng (core.gac_tong, lịch ShopAPI-GacTong mỗi 15') phát
    # hiện sự cố "chế độ chạy max" mà các kiểm phía trên (đọc trực tiếp
    # ke-hoach.csv/bay_gio, không có tầm nhìn máy: đứng khâu, lỗi lặp cùng
    # khâu, khoá chết, RAM/khe...) chưa có. CHỈ ĐỌC workspace/tinh-trang.json
    # (`doc_tinh_trang`), không tính lại gì — kênh đã có mục HỎNG khác ở trên
    # rồi thì bỏ qua, tránh hai dòng cùng báo một kênh.
    da_bao_hong = {v["kenh"] for v in ra if v.get("muc") == HONG and v.get("kenh")}
    for ma_gt, tt_gt in (doc_tinh_trang(goc).get("kenh") or {}).items():
        if not isinstance(tt_gt, dict) or tt_gt.get("trang_thai") != "cho_nguoi":
            continue
        if ma_gt in da_bao_hong:
            continue
        ra.append(_viec(
            "gac-tong:" + ma_gt, HONG, kenh=ma_gt,
            chu=str(tt_gt.get("ly_do") or "Người gác tổng thấy kênh {0} cần bạn xem lại.".format(ma_gt)),
            goi_y="→ mở tool xem chi tiết",
            nut=[("Nhật ký", "nhat_ky", {"ma": ma_gt})]))

    # 14b) Cảnh báo cấp MÁY của các chốt an toàn (`core.chot_an_toan`, ghi vào
    # tinh-trang.json → `canh_bao_may` bởi gác tổng): ví sắp hết/hết tiền, Windows sắp
    # hết hạn/cần khởi động lại, hạn thuê VPS, giọng đọc trùng. Chỉ ĐỌC, không tính lại.
    for cb in (doc_tinh_trang(goc).get("canh_bao_may") or []):
        if not isinstance(cb, dict) or not cb.get("chuyen_gi"):
            continue
        ra.append(_viec(
            "canh-bao-may:" + str(cb.get("loai") or "?"),
            HONG if cb.get("muc") == "khan" else THUONG,
            chu=str(cb["chuyen_gi"]),
            goi_y="→ " + str(cb.get("can_lam_gi") or "xem workspace/loi-chay-max.md")))

    # 15) Giám đốc kênh (01/10/2026): "Việc của bạn" trong báo cáo cuối (gợi ý chỉ chủ đổi được, đổi tiêu
    # đề video trượt, sức khoẻ kênh…). Bấm "Đã xong" thì ẩn; nhắc lại qua bao_dong ≤ 1 lần / 4 giờ (gác tổng).
    try:
        import hashlib  # noqa: PLC0415

        from . import giam_doc as _gd  # noqa: PLC0415

        for k in kenh_ds:
            ma = str(k.get("ma") or "")
            for chu_gd in _gd.viec_cua_ban_kenh(goc, ma, bay_gio=bay_gio):
                khoa = "giam-doc:{0}:{1}".format(ma, hashlib.sha1(chu_gd.encode("utf-8")).hexdigest()[:12])
                if khoa in da_xong:
                    continue
                ra.append(_viec(
                    khoa, THUONG, kenh=ma, chu="Giám đốc kênh: " + _cat_chu(chu_gd, 200),
                    goi_y="→ xem Báo cáo tuần của kênh",
                    nut=[("Báo cáo tuần", "bao_cao_giam_doc", {"ma": ma}),
                         ("Đã xong", "danh_dau_xong", {"khoa": khoa})],
                    xong_tay=True))
    except Exception:  # noqa: BLE001 — giám đốc hỏng không làm hỏng khối việc
        pass

    # 6) ví sắp cạn.
    ma_cac_kenh = [str(k.get("ma") or "") for k in kenh_ds]
    may = dong_may(goc, anh, bay_gio=bay_gio, so_du_micro=so_du_micro,
                   trang_thai_may=trang_thai_may, gio_lich=gio_lich)
    vi = may["vi"]
    if vi["muc"] in (HONG, LUU_Y) and vi["so_ngay_con_chay"] is not None:
        ra.append(_viec(
            "vi", HONG if vi["muc"] == HONG else CANH_BAO,
            chu="Ví còn {0:,.0f}₫ — đủ chạy khoảng {1:.0f} ngày".format(
                vi["vnd"] or 0, vi["so_ngay_con_chay"]).replace(",", "."),
            goi_y="→ nạp thêm tiền vào ví",
            nut=[("Nạp tiền", "mo_vi", {})]))

    # 7) chưa đăng nhập.
    if not co_client:
        ra.append(_viec(
            "dang-nhap", HONG, chu="Chưa đăng nhập ví — kênh không làm video được",
            goi_y="→ đăng nhập lại", nut=[("Đăng nhập", "dang_nhap", {})]))

    # 8) ổ đĩa sắp đầy.
    o_dia = may["o_dia"]
    if o_dia["muc"] in (HONG, LUU_Y) and o_dia["con_gb"] is not None:
        ra.append(_viec(
            "dia", HONG if o_dia["muc"] == HONG else CANH_BAO,
            chu="Ổ đĩa chỉ còn {0:.0f} GB".format(o_dia["con_gb"]),
            goi_y="→ bật “Tự dọn” ở ⚙ Cài đặt của từng kênh, hoặc dọn tay",
            nut=[("Mở thư mục", "mo_thu_muc", {"duong": goc})]))

    # 11) máy chạy nền đã tắt — máy đăng/trả lời chỉ báo khi KHÔNG ở chế độ phiên.
    if trang_thai_may:
        che_do_phien = _doc_che_do_phien(thu_muc_vm) if thu_muc_vm else False
        for khoa_may, ten in _TEN_MAY_NEN.items():
            st = trang_thai_may.get(khoa_may) or {}
            if st.get("song"):
                continue
            if khoa_may != "agent" and che_do_phien:
                continue  # cố ý không nuôi máy đăng/trả lời ngoài phiên — không phải sự cố
            ra.append(_viec(
                "may:" + khoa_may, HONG, chu="{0} đã tắt".format(ten),
                goi_y="→ bấm Bật lại",
                nut=[("Bật lại", "bat_lai_may", {"ten": khoa_may})]))

    # 12) lịch Windows tắt mà có kênh tự làm video.
    if not (gio_lich or "") and any(k.get("tu_chay") for k in kenh_ds):
        ra.append(_viec(
            "lich", CANH_BAO, chu="Lịch tự chạy đang tắt — kênh sẽ không tự làm video",
            goi_y="→ bật lịch chạy hằng ngày", nut=[("Bật lịch", "bat_lich", {})]))

    ra.sort(key=lambda v: _THU_TU_MUC.get(v["muc"], 9))
    return ra


# ═══════════════════════════════════════════════════════════════════════════
# 9) Ảnh chụp toàn cảnh của trang — gói mọi thứ trên lại
# ═══════════════════════════════════════════════════════════════════════════


#: Ngưỡng bật kiếm tiền YouTube (YPP): 1.000 đăng ký + 4.000 giờ xem.
YPP_SUB, YPP_GIO = 1000, 4000


def con_thieu_ypp(ypp: Dict[str, Any]) -> str:
    """"Còn thiếu để bật kiếm tiền: 438 sub · đủ giờ xem (6.351/4.000)" từ `trung_tam.ypp()` của
    dòng kênh (30/09/2026 — chủ dự án: có view + bật kiếm tiền là mục đích sống của tool). Chưa có số
    Studio → chuỗi nói rõ "chưa có số", không đoán."""
    sub, gio = _so((ypp or {}).get("dang_ky")), _so((ypp or {}).get("gio_xem"))
    if sub is None and gio is None:
        return "Còn thiếu để bật kiếm tiền: chưa có số Studio cấp kênh"

    def vn(x: float) -> str:
        return "{0:,.0f}".format(x).replace(",", ".")

    phan = []
    sub, gio = sub or 0.0, gio or 0.0
    phan.append("{0} sub".format(vn(YPP_SUB - sub)) if sub < YPP_SUB else "đủ sub ({0})".format(vn(sub)))
    phan.append("{0} giờ xem".format(vn(YPP_GIO - gio)) if gio < YPP_GIO
                else "đủ giờ xem ({0}/{1})".format(vn(gio), vn(YPP_GIO)))
    if sub >= YPP_SUB and gio >= YPP_GIO:
        return "Đã đủ điều kiện bật kiếm tiền ({0} sub · {1} giờ xem)".format(vn(sub), vn(gio))
    return "Còn thiếu để bật kiếm tiền: " + " · ".join(phan)


def anh_bang(goc: str, *, bay_gio: Optional[_dt.datetime] = None,
            anh: Optional[Dict[str, Any]] = None, gio_lich: Optional[str] = None,
            so_du_micro: Optional[int] = None, trang_thai_may: Optional[Dict[str, Any]] = None,
            co_client: bool = True) -> Dict[str, Any]:
    """Mọi thứ trang Bảng điều khiển cần, MỘT lượt: `{kenh, kenh_khac, viec,
    may, luc}`. Không tự đọc mạng/gọi `schtasks` — `gio_lich`/`so_du_micro`/
    `trang_thai_may` do lớp giao diện tự hỏi rồi truyền vào (CLAUDE.md luật 4).

    `anh`: dùng lại `trung_tam.anh_chup(goc, tat_ca=True, co_nhom=False,
    gio_lich=…)` nếu người gọi đã có sẵn (đỡ đọc đĩa hai lần); không đưa thì
    tự chụp.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    if anh is None:
        anh = tt.anh_chup(goc, bay_gio=bay_gio, tat_ca=True, co_nhom=False, gio_lich=gio_lich)
    thu_muc_vm = tt.thu_muc_vm(goc)

    kenh: List[Dict[str, Any]] = []
    for k in (anh.get("kenh") or []):
        k2 = dict(k)
        k2["muc_the"] = muc_the(k)
        vkt = video_ke_tiep(k)
        k2["video_ke_tiep"] = vkt
        if not vkt and bool(k.get("tu_chay")):
            k2["video_ke_tiep_tu"] = _video_ke_tiep_tu(goc, str(k.get("ma") or ""), bay_gio)
        k2["video_gan_day"] = video_gan_day(goc, str(k.get("ma") or ""), 3, bay_gio=bay_gio)
        k2["may_dang_hoc"] = may_dang_hoc(goc, str(k.get("ma") or ""))
        k2["con_thieu_ypp"] = con_thieu_ypp(k.get("ypp") or {})
        k2["giam_doc"] = giam_doc_the(goc, str(k.get("ma") or ""))
        kenh.append(k2)

    viec = viec_cua_ban(goc, anh=anh, bay_gio=bay_gio, so_du_micro=so_du_micro,
                        trang_thai_may=trang_thai_may, co_client=co_client,
                        gio_lich=gio_lich, thu_muc_vm=thu_muc_vm)
    may = dong_may(goc, anh, bay_gio=bay_gio, so_du_micro=so_du_micro,
                   trang_thai_may=trang_thai_may, gio_lich=gio_lich)

    return {
        "kenh": kenh,
        "kenh_khac": list(anh.get("kenh_khac") or []),
        "viec": viec,
        "may": may,
        "luc": anh.get("luc") or bay_gio.isoformat(timespec="seconds"),
    }
