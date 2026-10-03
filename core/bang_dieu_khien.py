"""Lõi dữ liệu THUẦN cho trang **Bảng điều khiển** (Việc 1,
`workspace/THIET-KE-BANG-DIEU-KHIEN.md`, duyệt 29/09/2026).

Không Qt, không mạng. Chỉ ghi: `workspace/viec-da-xong.json`, bộ đệm số kênh
`workspace/phong-dieu-hanh/so-kenh/*.json` (mục 10) và sổ gạch bài học
`CHANNEL/<ma>/giam-doc/bai-hoc-gach.jsonl` (mục 10, nút "Sai") — mọi thứ khác
chỉ ĐỌC lại các tệp đã có (`core.trung_tam.anh_chup()` và bạn bè) rồi gói thành
hình mà trang cần: một khối "Việc của bạn" xếp theo mức nặng, một dòng "Máy",
bộ khung mỗi thẻ kênh, và (mục 10, 01/10/2026) PHÒNG ĐIỀU HÀNH CÔNG TY: khối
công ty, thẻ kênh (xếp loại, YPP, 3 cổng, phán quyết, đội AI nói, đang thử,
lịch đăng tiếp) và dữ liệu ba trang chi tiết.

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
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    "doi_giam_doc", "giam_doc_the", "CHE_DO_GIAM_DOC", "dong_lich",
    # Mức việc — dùng để sắp xếp/tô màu ở cả hai lớp.
    "HONG", "CANH_BAO", "THUONG",
    # Mức thẻ kênh (`muc_the`).
    "TOT", "CHO_BAN", "LUU_Y", "TAT",
    # Phòng điều hành công ty (01/10/2026, mục 10).
    "CHUA", "CHUYEN_GIA", "XEP_LOAI", "ma_so_kenh", "tinh_so_kenh", "doc_so_kenh", "so_kenh_cu",
    "tinh_va_luu", "dang_tinh", "sinh_tinh_so", "doi_ai_noi", "dang_thu", "lich_dang_tiep",
    "muc_phong", "khoi_cong_ty", "phong_dieu_hanh", "bao_cao_tuan", "so_bai_hoc", "ma_bai",
    "chuyen_gia_cua", "gach_bai_hoc", "doc_bai_hoc_gach", "khoa_bai_hoc_gach", "so_quyet_dinh",
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
    if goc.startswith(("Chờ khe", "Lượt ")):  # do `_chinh_bay_gio` viết sẵn câu người đọc
        return _cat_chu(goc, 120)
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


#: Mẫu câu CODE tự viết trong `core.giam_doc` cho việc chỉ người làm được (không phải lời LLM tự do):
#: quyết định lớn chờ duyệt, đổi tiêu đề trên Studio; và câu cố định của cò sức khoẻ (cảnh báo chính sách).
_VIEC_GD_CAN_NGUOI = ("Quyết định lớn chờ bạn duyệt:", "Đổi tiêu đề video ")


def viec_gd_can_nguoi(chu: str) -> bool:
    """Mục "Việc của bạn" trong báo cáo giám đốc có THẬT SỰ cần người không (còn lại chỉ là gợi ý)."""
    from .giam_doc.suc_khoe import VIEC_CUA_BAN as _sk  # noqa: PLC0415

    return str(chu).startswith(_VIEC_GD_CAN_NGUOI) or str(chu).strip() == _sk.strip()


def goi_y_giam_doc(goc: str, ma: str) -> List[Dict[str, str]]:
    """Gợi ý của giám đốc kênh KHÔNG cần người (xem `viec_gd_can_nguoi`) — hiện ở "Đội AI nói"."""
    try:
        from . import giam_doc as _gd  # noqa: PLC0415

        ds = [c for c in _gd.viec_cua_ban_kenh(goc, ma) if not viec_gd_can_nguoi(c)]
    except Exception:  # noqa: BLE001
        return []
    return [{"ai": "Giám đốc gợi ý", "cau": _mot_cau(c, 220), "luc": ""} for c in ds[:3]]


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

        # 4) ghim chưa đánh dấu — chỉ khi kênh BẬT ghim (chủ kênh 29/09: "ghim để sau").
        try:
            from . import vm_cai_dat  # noqa: PLC0415
            ghim_bat = bool(vm_cai_dat.doc(goc, ma).get("ghim_dom", False))
        except Exception:  # noqa: BLE001
            ghim_bat = False
        for pin in (doc_can_ghim(goc, ma) if ghim_bat else []):
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
        if not isinstance(cb, dict) or not cb.get("chuyen_gi") or cb.get("loai") == "giong_doc_trung":
            continue  # giọng chung: chủ đã quyết GIỮ — chỉ hiện ở khối Cảnh báo (`cb_giong_chung`)
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
                if not viec_gd_can_nguoi(chu_gd):
                    continue  # gợi ý của giám đốc → "Đội AI nói" của kênh (`goi_y_giam_doc`)
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

    # 16) Cứu video CTR thấp (01/10/2026): hội đồng đề xuất đổi tiêu đề — 3 lần đầu mỗi kênh chờ chủ DUYỆT.
    # Bấm chỉ GHI sổ `giam-doc/duyet-sua.json` (`cuu_ctr.ghi_duyet`); nhịp gác tổng xếp hàng sửa giờ vắng.
    try:
        from .giam_doc import cuu_ctr as _cc  # noqa: PLC0415

        for k in kenh_ds:
            ma = str(k.get("ma") or "")
            for m in _cc.cho_duyet(goc, ma):
                ts = {"ma": ma, "id": str(m.get("id") or "")}
                ra.append(_viec(
                    "duyet-sua:" + ts["id"], CANH_BAO, kenh=ma, chu="Giám đốc kênh: " + _cat_chu(_cc.dong_viec_cua_ban(m), 320),
                    goi_y="→ Duyệt: máy đổi tiêu đề giờ vắng, đo CTR trước/sau, tệ hơn thì tự đổi lại (3 lần đầu cần bạn)",
                    nut=[("Duyệt", "duyet_sua", ts), ("Bỏ", "bo_sua", ts),
                         ("Chép link Studio", "chep_link",
                          {"url": "https://studio.youtube.com/video/{0}/edit".format(m.get("video_id"))})]))
    except Exception:  # noqa: BLE001
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
        # 01/10/2026: van ổ (`don_dep_mo_rong.NGUONG_O_GB`) — dưới ngưỡng thì máy không
        # mở video mới, tự chạy lại khi ổ đủ chỗ.
        from .don_dep_mo_rong import NGUONG_O_GB  # noqa: PLC0415

        con = float(o_dia["con_gb"])
        ngung = con < NGUONG_O_GB
        ra.append(_viec(
            "dia", HONG if o_dia["muc"] == HONG else CANH_BAO,
            chu="Ổ đĩa chỉ còn {0:.0f} GB{1}".format(con, " — máy đã ngừng mở video mới" if ngung else ""),
            goi_y=("→ dọn tay DONE/PROJECTS cũ; máy tự chạy lại khi ổ ≥ {0:g} GB".format(NGUONG_O_GB)
                   if ngung else "→ bật “Tự dọn” ở ⚙ Cài đặt của từng kênh, hoặc dọn tay"),
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

    # 13) bộ não (`core/nao de-xuat`): việc lớn chờ chủ duyệt. Lỗi = như không có não.
    try:
        from . import nao as _nao  # noqa: PLC0415

        for dx in _nao.viec_de_xuat(goc):
            if dx["khoa"] in da_xong:
                continue
            ra.append(_viec(dx["khoa"], CANH_BAO, kenh=dx["kenh"], chu=dx["chu"], goi_y=dx["goi_y"],
                            nut=[("Đã xử lý", "danh_dau_xong", {"khoa": dx["khoa"]})], xong_tay=True))
    except Exception:  # noqa: BLE001
        pass

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


def _luot_da_bo(goc: str, ma: str, ma_luot: str) -> Optional[Dict[str, Any]]:
    """Mục lượt `ma_luot` trong sổ `CHANNEL/<ma>/tu-chay/*.json` nếu máy đã TỰ BỎ (`bo: true`)."""
    if not ma_luot:
        return None
    thu = os.path.join(_kenh_mod.duong_kenh(goc, ma), "tu-chay")
    try:
        tep = sorted(f for f in os.listdir(thu) if f[:1].isdigit() and f.endswith(".json"))[-7:]
    except OSError:
        return None
    for f in reversed(tep):
        du = _doc_json(os.path.join(thu, f))
        for r in ((du.get("runs") or []) if isinstance(du, dict) else []):
            if isinstance(r, dict) and str(r.get("ma_luot")) == ma_luot and r.get("bo"):
                return r
    return None


#: Lỗi của lượt chưa bỏ chỉ tô ĐỎ khi kéo dài quá chừng này (máy còn tự chạy lại ở các nhịp sau).
LOI_DO_SAU_GIO = 6


def _chinh_bay_gio(goc: str, k: Dict[str, Any], bay_gio: _dt.datetime) -> Optional[Dict[str, str]]:
    """Sửa thẻ "Bây giờ" cho ĐÚNG hiện trạng (None = giữ nguyên): lượt máy đã tự bỏ → thông tin, không đỏ;
    lỗi mới < 6 giờ → vàng; cổng sản xuất đóng theo luật đúng hạn → "Chờ khe — sản xuất lúc …"."""
    bay = k.get("bay_gio") or {}
    muc, chu = str(bay.get("muc") or ""), str(bay.get("chu") or "")
    ma = str(k.get("ma") or "")
    luot = k.get("luot") or {}
    if muc == "loi":
        ma_luot = str(luot.get("ma_luot") or "")
        run = _luot_da_bo(goc, ma, ma_luot)
        if run:
            ly = cau_tinh_trang(k)
            ly = ly[len("Dừng khi "):] if ly.startswith("Dừng khi ") else ly
            return {"chu": "Lượt {0} bỏ ({1}) — máy đã chuyển nguồn khác".format(ma_luot, _cat_chu(ly.split(" cho job")[0], 60)),
                    "muc": "cho", "chi_tiet": str(run.get("ly_do_bo") or "")}
        try:
            tuoi = (bay_gio.timestamp() - os.path.getmtime(str(luot.get("thu_muc") or ""))) / 3600.0
        except OSError:
            return None
        return dict(bay, muc="canh_bao") if tuoi < LOI_DO_SAU_GIO else None
    if k.get("tu_chay") and chu.startswith(_GOC_RANH_VIEC):
        mo, _ly, ttin = tu_chay._cua_so_san_xuat(  # noqa: SLF001 — hàm thuần đọc, nguồn sự thật của cổng
            goc, ma, _kenh_mod.doc_kenh(goc, ma), bay_gio=bay_gio)
        if mo:
            return None
        gio = lambda s: _dt.datetime.fromisoformat(s).strftime("%d/%m %H:%M")  # noqa: E731
        if ttin.get("khe_ke_tiep") and ttin.get("mo_cua_san_xuat"):
            return {"chu": "Chờ khe — sản xuất lúc " + gio(ttin["mo_cua_san_xuat"]), "muc": "cho",
                    "chi_tiet": "Khe đăng kế tiếp {0}; máy chọn content và sản xuất đúng hạn.".format(gio(ttin["khe_ke_tiep"]))}
        if ttin.get("che_do") == "kho_dem" and ttin.get("mo_cua_san_xuat"):
            return {"chu": "Chờ khe — kho đủ, làm tiếp sau khi video {0} lên sóng".format(gio(ttin["mo_cua_san_xuat"])),
                    "muc": "cho", "chi_tiet": _ly}
    return None


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
        try:
            bay_moi = _chinh_bay_gio(goc, k2, bay_gio)
        except Exception:  # noqa: BLE001 — dò thêm hỏng thì giữ thẻ gốc
            bay_moi = None
        if bay_moi:
            k2["bay_gio"] = bay_moi
            k = k2
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

    viec = viec_cua_ban(goc, anh=dict(anh, kenh=kenh), bay_gio=bay_gio, so_du_micro=so_du_micro,
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


# ═══════════════════════════════════════════════════════════════════════════
# 10) PHÒNG ĐIỀU HÀNH CÔNG TY (Đợt G, 01/10/2026 — workspace/VIEC-CON-LAI-30-09.md)
# ═══════════════════════════════════════════════════════════════════════════
#
# Hai tầng, để trang làm mới 30 giây/lần vẫn nhẹ:
#
# * NẶNG — `tinh_so_kenh` (giám đốc kênh `giam_doc.du_lieu.tom_tat`: 5–25 giây
#   MỘT kênh trên máy thật, phần lớn là `cong_thuc_v7.video_cua_kenh` +
#   `chien_luoc.bai_hoc`). KHÔNG BAO GIỜ chạy trong tiến trình giao diện: giao
#   diện gọi `sinh_tinh_so` → tiến trình con ưu tiên thấp `python -m
#   core.bang_dieu_khien tinh-so <mã…>` ghi `workspace/phong-dieu-hanh/
#   so-kenh/<mã>.json`. Chỉ tính lại khi DỮ LIỆU ĐỔI (`_chu_ky_so_kenh`: mtime
#   bảng tóm tắt/kênh theo ngày/kenh.yaml/giam-doc) hoặc bản cũ quá 6 giờ.
# * NHẸ — mọi thứ còn lại (`phong_dieu_hanh`): đọc lại bộ đệm trên + vài tệp
#   JSON nhỏ (giam-doc/*, cong-suat, tinh-trang, cap-nhat, van-vi). Không mạng.
#
# Mọi con số đều từ hàm có sẵn: 7 ngày/tuần trước = `du_lieu.trong_khoang` (đúng
# cửa sổ `tong.bang_cong_ty`), xếp loại = `tong.xep_loai`, phán quyết video =
# `ket_qua.ket_luan` (qua `tom_tat`), ngưỡng = `nguong_thang_48h`/`ctr_muc_tieu`
# của chính giám đốc kênh, trần máy = `tong.tran_may`, video hôm nay =
# `cong_suat._video_ban_giao`, ví = `dong_may` (van_vi).

#: Mức cổng chưa đủ số để tô màu (khác TOT/LUU_Y/HONG).
CHUA = "chua"

THU_MUC_PHONG = os.path.join("workspace", "phong-dieu-hanh")
#: Sổ đội chuyên gia (Đợt F, agent khác viết): `CHANNEL/<ma>/giam-doc/doi-ai.json`
#: = `{"nen_tang": {"cau": "...", "luc": "..."}, "khan_gia": {...}, "chu_de": {...}}`.
#: Chưa có tệp → thẻ lùi về chẩn đoán giám đốc + khám nghiệm gần nhất.
TEP_DOI_AI = "doi-ai.json"
#: Phiên hội đồng cuối mỗi loại (`giam_doc.hoi_dong.TEP_CUOI`): `{loai: {luc, chuyen_gia: [...], quyet}}`.
TEP_HOI_DONG_CUOI = "hoi-dong-cuoi.json"
#: Sổ gạch bài học (nút "Sai" ở trang Bài học) — mỗi dòng một lần gạch.
TEP_BAI_HOC_GACH = "bai-hoc-gach.jsonl"
SO_KENH_TUOI_TOI_DA_GIAY = 6 * 3600
#: Khoá tiến trình tính số: quá 20 phút coi như chết (một lượt 4 kênh ≈ 1 phút).
KHOA_TINH_QUA_HAN_GIAY = 20 * 60

CHUYEN_GIA = (("nen_tang", "Nền tảng"), ("khan_gia", "Khán giả"), ("chu_de", "Chủ đề"))
_TEN_CHUYEN_GIA = dict(CHUYEN_GIA)
#: Trục bài học → chuyên gia (trục lạ → "chu_de"). Nền tảng = thuật toán (hiển thị,
#: trang chủ, bìa/tiêu đề, nguồn); Khán giả = tệp của kênh (giữ chân, hook, độ dài, sub).
_TRUC_CHUYEN_GIA = {
    "tieu_de": "nen_tang", "bia": "nen_tang", "nguon": "nen_tang", "ctr_trang_chu": "nen_tang",
    "ctr_browse_48h": "nen_tang", "thumbnail_ctr": "nen_tang",
    "hook": "khan_gia", "giu_chan": "khan_gia", "do_dai": "khan_gia", "loi_moi_dk": "khan_gia",
    "do_dai_avd": "khan_gia", "sub_1k_view": "khan_gia",
}
TEN_PHAM_VI = {"kenh": "Kênh này", "nhom": "Nhóm kênh", "ngoai": "Bên ngoài",
               # Sổ kinh nghiệm riêng của từng chuyên gia (`giam_doc.hoi_dong.duong_so`).
               "so_toan_cuc": "Sổ chuyên gia · toàn cục", "so_kenh": "Sổ chuyên gia · kênh này",
               "so_ngach": "Sổ chuyên gia · ngách"}
_THU_PHAM_VI = {"so_toan_cuc": 0, "so_ngach": 0, "so_kenh": 0, "kenh": 1, "nhom": 2, "ngoai": 3}
#: `tong.xep_loai` → (dấu, chữ).
XEP_LOAI = {"len": ("▲", "lên"), "chung": ("●", "chững"), "tut": ("▼", "tụt")}
#: Tên việc của giám đốc (plugin) cho người đọc.
_TEN_VIEC_GD = {"cuu_ctr": "Cứu tỉ lệ bấm", "dan_cum": "Dàn cụm chủ đề", "do_dai": "Độ dài video",
                "muc_tieu_ypp": "Mục tiêu kiếm tiền", "suc_khoe": "Sức khoẻ kênh"}
_TEN_TN = {"mo": "đang đo", "giu": "giữ", "mo_rong": "mở rộng", "bo": "bỏ", "quay_lui": "quay lui",
           "chua_du": "chưa đủ mẫu"}


def _thuat_ngu(chu: Any) -> str:
    """Câu AI viết (có "CTR", "AVD", "gx_1k") → chữ người thường."""
    s = str(chu or "")
    s = s.replace("CTR trang chủ", "tỉ lệ bấm trang chủ")
    s = _re.sub(r"\bCTR\b", "tỉ lệ bấm", s)
    s = _re.sub(r"\bAVD\b", "thời lượng xem TB", s)
    s = _re.sub(r"(?:giờ xem\s+)?gx_1k", "giờ xem/1k hiển thị", s)
    s = _re.sub(r"(?<![\d.])(\d+)\.0\b", r"\1", s)        # 1709.0 → 1709
    return s


def _mot_cau(chu: Any, toi_da: int = 170) -> str:
    s = " ".join(_thuat_ngu(chu).split())
    s = _re.split(r"(?<=[.!?。])\s+", s)[0] if s else ""
    return _cat_chu(s, toi_da)


def ma_youtube(ma: str) -> str:
    """`TL4-T7-v2` → `TL4-T7` (đăng cùng một kênh YouTube — khuôn `tong._cac_kenh`)."""
    return _re.sub(r"[-_]v\d+$", "", str(ma or ""), flags=_re.IGNORECASE)


def ma_so_kenh(goc: str, ma: str) -> str:
    """Mã kênh có số Studio (`chi-so/`) — chính `ma`, không có thì kênh YouTube gốc."""
    if os.path.isdir(os.path.join(_kenh_mod.duong_kenh(goc, ma), "chi-so")):
        return ma
    return ma_youtube(ma)


def _duong_so_kenh(goc: str, ma: str) -> str:
    return os.path.join(goc, THU_MUC_PHONG, "so-kenh", "{0}.json".format(ma))


def _chu_ky_so_kenh(goc: str, ma: str) -> str:
    """Dấu "dữ liệu đổi chưa": mtime các tệp nguồn của `tinh_so_kenh` (rẻ: vài `stat`)."""
    tm = _kenh_mod.duong_kenh(goc, ma)
    ds = [os.path.join(tm, "chi-so", "bang-tom-tat.csv"), os.path.join(tm, "chi-so", "kenh-theo-ngay.csv"),
          os.path.join(tm, _kenh_mod.TEP_KENH)]
    gd = os.path.join(tm, "giam-doc")
    try:
        ds += [os.path.join(gd, t) for t in sorted(os.listdir(gd))]
    except OSError:
        pass
    phan = []
    for d in ds:
        try:
            phan.append("{0:.0f}".format(os.path.getmtime(d)))
        except OSError:
            phan.append("-")
    return "|".join(phan)


def _ghi_json_nguyen_tu(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1, default=str)
    os.replace(tam, duong)


def _tv(xs: List[Any]) -> Optional[float]:
    xs = [float(x) for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _chup_tu(v: Dict[str, Any], tu_gio: float = 36.0) -> Dict[str, Any]:
    """Bản chụp mới nhất của video có tuổi ≥ `tu_gio` (số còn non dưới đó)."""
    ds = [b for b in (v.get("chup") or []) if (b.get("tuoi") or 0) >= tu_gio]
    return ds[-1] if ds else {}


def _vn(x: Optional[float], le: int = 0) -> str:
    if x is None:
        return "?"
    s = "{0:,.{1}f}".format(float(x), le)
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _cong(ten: str, gia_tri: Optional[float], chuan: Optional[float], nguong_vang: float,
          dinh_dang: Callable[[Optional[float]], str], nhan_chuan: str, n: int) -> Dict[str, Any]:
    """Một cổng: `{ten, muc, chu, gia_tri, chuan, n}` — muc TOT ≥ chuẩn, LUU_Y ≥ ngưỡng vàng, HONG dưới."""
    if gia_tri is None:
        return {"ten": ten, "muc": CHUA, "chu": "chưa đủ số", "gia_tri": None, "chuan": chuan, "n": 0}
    if not chuan:
        return {"ten": ten, "muc": CHUA, "chu": "{0} (chưa có chuẩn để so)".format(dinh_dang(gia_tri)),
                "gia_tri": gia_tri, "chuan": chuan, "n": n}
    ti = gia_tri / chuan
    muc = TOT if ti >= 1.0 else (LUU_Y if ti >= nguong_vang else HONG)
    return {"ten": ten, "muc": muc, "chu": "{0} / {1} {2}".format(dinh_dang(gia_tri), nhan_chuan, dinh_dang(chuan)),
            "gia_tri": gia_tri, "chuan": chuan, "n": n}


def _ba_cong(bs: Any) -> List[Dict[str, Any]]:
    """Ba cổng của kênh trên ≤ 5 video gần nhất: Hiển thị (48h, so ngưỡng thắng) · Tỉ lệ bấm trang chủ
    (so mục tiêu kênh, vàng từ 80% — đúng `cuu_ctr.HE_SO_CTR`) · Giữ chân (% thời lượng xem, so trung vị
    video thắng của chính kênh)."""
    from .giam_doc import du_lieu as dl  # noqa: PLC0415
    try:
        from .giam_doc.cuu_ctr import HE_SO_CTR  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        HE_SO_CTR = 0.8  # noqa: N806

    # Hiển thị 48h; video đã quá 48h mà thiếu bản chụp 48h (lỗ hổng đã biết, Đợt E) lấy bản chụp mới nhất —
    # đúng số giám đốc kênh tự trích ("198 @38h") — để cổng không xanh oan chỉ vì còn mỗi video thắng có số.
    h48 = []
    for v in bs.video:
        x = v.get("hien_thi_48h")
        if x is None and (v.get("tuoi_gio") or 0) >= 48:
            x = (dl.moi_nhat(v) or {}).get("hien_thi")
        if x is not None:
            h48.append(x)
    h48 = h48[:5]
    ctr = []
    for v in bs.video[:12]:
        tc = dl.ctr_trang_chu(v)
        if tc and tc.get("ctr_browse") is not None:
            ctr.append(tc["ctr_browse"])
    ctr = ctr[:5]
    giu = [b.get("avd_pct") for b in (_chup_tu(v) for v in bs.video[:12]) if b.get("avd_pct") is not None][:5]
    giu_thang = [_chup_tu(v).get("avd_pct") for v in bs.video if v.get("thang")]
    return [
        _cong("Hiển thị", _tv(h48), bs.nguong_thang_48h, 0.5, _vn, "cần", len(h48)),
        _cong("Tỉ lệ bấm trang chủ", _tv(ctr), bs.ctr_muc_tieu, HE_SO_CTR,
              lambda x: _vn(x, 1) + "%", "mục tiêu", len(ctr)),
        _cong("Giữ chân", _tv(giu), _tv(giu_thang), 0.8, lambda x: _vn(x, 0) + "%", "video thắng", len(giu)),
    ]


def tinh_so_kenh(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """PHẦN NẶNG của thẻ kênh (gọi trong tiến trình con, xem đầu mục 10): tuần này/tuần trước, xếp loại,
    ba cổng, 3 video gần nhất + phán quyết + dự đoán của giám đốc, YPP. Kết quả JSON được."""
    from .giam_doc import du_lieu as dl, so_thi_nghiem as stn, tong  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    bs = dl.tom_tat(goc, ma, bay_gio=bay_gio)
    tuan = _dt.timedelta(days=7)
    # Cùng cửa sổ `tong.bang_cong_ty`: kênh mới (dòng số đầu < 7 ngày) tính từ dòng đầu.
    dau = next((x["luc"] for x in bs.kenh_ngay if x.get("hien_thi") is not None), None)
    tu7 = max(bay_gio - tuan, dau) if dau and dau < bay_gio - _dt.timedelta(days=2) else bay_gio - tuan
    khoa = ("xem", "sub", "gio_xem", "hien_thi")
    nay = {k: dl.trong_khoang(bs, k, tu7, bay_gio) for k in khoa}
    truoc = {k: dl.trong_khoang(bs, k, bay_gio - 2 * tuan, bay_gio - tuan) for k in khoa}
    v28 = [v for v in bs.video if v.get("dang_luc") and v["dang_luc"] >= bay_gio - 4 * tuan]
    kl = [v for v in v28 if v.get("ket_luan") in ("thang", "truot")]
    thang = sum(1 for v in kl if v["ket_luan"] == "thang")
    d = {"da": (round(nay["hien_thi"] / truoc["hien_thi"], 2)
                if nay["hien_thi"] is not None and truoc["hien_thi"] else None),
         "ti_le_thang": round(thang / len(kl), 2) if kl else None}
    try:
        doan = {str(x.get("video_id")): x for x in stn.doc_du_doan(goc, ma)}
    except Exception:  # noqa: BLE001
        doan = {}
    video = []
    for v in bs.video[:3]:
        b = dl.moi_nhat(v) or {}
        dd = doan.get(v["id"]) or {}
        video.append({"id": v["id"], "tieu_de": v.get("tieu_de") or "", "ket": v.get("ket_luan") or "cho",
                      "tuoi_gio": v.get("tuoi_gio"), "hien_thi_48h": v.get("hien_thi_48h"),
                      "hien_thi": b.get("hien_thi"), "doan": str(dd.get("ket") or ""),
                      "doan_dung": dd.get("dung")})
    return {
        "ma": ma, "luc": bay_gio.isoformat(timespec="seconds"), "chu_ky": _chu_ky_so_kenh(goc, ma),
        "tuan": {"nay": nay, "truoc": truoc, "tu": tu7.isoformat(timespec="minutes")},
        "da": d["da"], "ti_le_thang": d["ti_le_thang"], "thang_28": thang, "kl_28": len(kl),
        "loai": tong.xep_loai(d), "cong": _ba_cong(bs), "video": video,
        "ypp": {"sub": (bs.ypp or {}).get("sub"), "gio_xem": (bs.ypp or {}).get("gio_xem")},
        "nguong_48h": bs.nguong_thang_48h, "ghi_chu": list(bs.ghi_chu)[:4],
    }


def doc_so_kenh(goc: str, ma: str) -> Dict[str, Any]:
    """Bộ đệm số kênh đã tính (`{}` khi chưa có)."""
    du = _doc_json(_duong_so_kenh(goc, ma))
    return du if isinstance(du, dict) else {}


def so_kenh_cu(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Cần tính lại: chưa có bộ đệm, dữ liệu nguồn đã đổi, hoặc bản cũ quá 6 giờ (cửa sổ 7 ngày trôi)."""
    du = doc_so_kenh(goc, ma)
    if not du:
        return True
    if du.get("chu_ky") != _chu_ky_so_kenh(goc, ma):
        return True
    try:
        tuoi = ((bay_gio or _dt.datetime.now()) - _dt.datetime.fromisoformat(str(du.get("luc")))).total_seconds()
    except ValueError:
        return True
    return tuoi > SO_KENH_TUOI_TOI_DA_GIAY


def tinh_va_luu(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    du = tinh_so_kenh(goc, ma, bay_gio=bay_gio)
    _ghi_json_nguyen_tu(_duong_so_kenh(goc, ma), du)
    return du


def _duong_khoa_tinh(goc: str) -> str:
    return os.path.join(goc, THU_MUC_PHONG, ".dang-tinh.json")


def dang_tinh(goc: str) -> bool:
    """Có tiến trình `tinh-so` đang chạy (khoá còn hạn và PID còn sống)."""
    du = _doc_json(_duong_khoa_tinh(goc))
    if not isinstance(du, dict):
        return False
    try:
        if _dt.datetime.now().timestamp() - float(du.get("luc") or 0) > KHOA_TINH_QUA_HAN_GIAY:
            return False
        from .tien_trinh_con import con_song  # noqa: PLC0415

        return con_song(int(du.get("pid") or 0))
    except Exception:  # noqa: BLE001
        return False


def sinh_tinh_so(goc: str, cac_ma: List[str]) -> int:
    """Sinh `python -m core.bang_dieu_khien tinh-so <mã…>` (không cửa sổ, ưu tiên thấp). Trả PID (0 = không)."""
    cac_ma = [m for m in dict.fromkeys(cac_ma) if m]
    if not cac_ma or dang_tinh(goc):
        return 0
    import subprocess  # noqa: PLC0415

    try:
        from .cap_nhat_git import _python_nen  # noqa: PLC0415

        py = _python_nen()
    except Exception:  # noqa: BLE001
        import sys  # noqa: PLC0415

        py = sys.executable
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    tm = os.path.join(goc, THU_MUC_PHONG)
    os.makedirs(tm, exist_ok=True)
    try:
        log = open(os.path.join(tm, "tinh-so.log"), "a", encoding="utf-8")  # noqa: SIM115
    except OSError:
        log = subprocess.DEVNULL  # type: ignore[assignment]
    try:
        p = subprocess.Popen(  # noqa: S603
            [py, "-X", "utf8", "-m", "core.bang_dieu_khien", "tinh-so"] + cac_ma, cwd=goc, creationflags=co,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, close_fds=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except OSError:
        return 0
    finally:
        if log is not subprocess.DEVNULL:
            log.close()
    _ghi_json_nguyen_tu(_duong_khoa_tinh(goc), {"pid": p.pid, "luc": _dt.datetime.now().timestamp(), "ma": cac_ma})
    return p.pid


def _chan_doan_phuong_an(x: Dict[str, Any]) -> str:
    """Câu chẩn đoán trong phương án của một chuyên gia (`phuong_an` là JSON có thể bị cắt "…")."""
    tho = str(x.get("phuong_an") or "")
    try:
        du = json.loads(tho)
        cau = du.get("chan_doan") if isinstance(du, dict) else ""
    except ValueError:
        m = _re.search(r'"chan_doan"\s*:\s*"((?:[^"\\]|\\.)*)', tho)
        cau = m.group(1).replace('\\"', '"') if m else ""
    if not cau:
        cau = next((d.get("cau") for d in (x.get("luan_diem") or []) if isinstance(d, dict) and d.get("giu")), "")
    return str(cau or "")


def _doi_tu_hoi_dong(tm: str) -> List[Dict[str, str]]:
    """Phiên hội đồng MỚI NHẤT (`hoi-dong-cuoi.json`): một câu mỗi chuyên gia còn đứng (không bị loại vì số bịa);
    người được hội đồng chọn có dấu ★."""
    du = _doc_json(os.path.join(tm, TEP_HOI_DONG_CUOI))
    if not isinstance(du, dict):
        return []
    phien = [h for h in du.values() if isinstance(h, dict) and h.get("chuyen_gia")]
    if not phien:
        return []
    h = max(phien, key=lambda x: str(x.get("luc") or ""))
    chon = str((h.get("quyet") or {}).get("chon") or "")
    ra = []
    for khoa, ten in CHUYEN_GIA:
        x = next((c for c in h["chuyen_gia"] if isinstance(c, dict) and c.get("ma") == khoa), None)
        if not x or x.get("loai_bo"):
            continue
        cau = _chan_doan_phuong_an(x)
        if cau:
            ra.append({"ai": ten + (" ★" if khoa == chon else ""), "cau": _mot_cau(cau),
                       "luc": "{0} · {1}".format(str(h.get("luc") or "")[:16].replace("T", " "), h.get("loai") or "")})
    return ra


def doi_ai_noi(goc: str, ma: str) -> List[Dict[str, str]]:
    """Đội AI nói + "Giám đốc gợi ý" (việc giám đốc nhắc mà máy/không cần người xử lý)."""
    return _doi_ai_chinh(goc, ma) + goi_y_giam_doc(goc, ma)


def _doi_ai_chinh(goc: str, ma: str) -> List[Dict[str, str]]:
    """"Đội AI nói": một câu mỗi chuyên gia — `giam-doc/doi-ai.json` nếu có, không thì phiên hội đồng cuối
    (`giam_doc.hoi_dong` → `hoi-dong-cuoi.json`); chưa có đội thì lùi về chẩn đoán giám đốc kênh
    (`bao-cao.json`) + khám nghiệm gần nhất (`kham_nghiem.doc_kham`). `[{ai, cau, luc}]`."""
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    tm = thu_muc_giam_doc(goc, ma)
    ra: List[Dict[str, str]] = []
    du = _doc_json(os.path.join(tm, TEP_DOI_AI))
    if isinstance(du, dict):
        for khoa, ten in CHUYEN_GIA:
            o = du.get(khoa)
            cau = o.get("cau") if isinstance(o, dict) else o
            if cau:
                ra.append({"ai": ten, "cau": _mot_cau(cau), "luc": str((o or {}).get("luc") or "")
                           if isinstance(o, dict) else ""})
    if not ra:
        ra = _doi_tu_hoi_dong(tm)
    if ra:
        return ra
    bc = _doc_json(os.path.join(tm, "bao-cao.json"))
    if isinstance(bc, dict) and bc.get("chan_doan"):
        ra.append({"ai": "Giám đốc kênh", "cau": _mot_cau(bc["chan_doan"]), "luc": str(bc.get("luc") or "")})
    try:
        from .giam_doc import kham_nghiem  # noqa: PLC0415

        ds = kham_nghiem.doc_kham(goc, ma)
    except Exception:  # noqa: BLE001
        ds = []
    if ds and (ds[0].get("ket") or {}).get("chan_doan"):
        d = ds[0]
        ra.append({"ai": "Khám nghiệm", "cau": "video {0} ({1}): {2}".format(
            d.get("video_id"), d.get("moc"), _mot_cau(d["ket"]["chan_doan"], 150)), "luc": str(d.get("luc") or "")})
    return ra


def _ten_viec_gd(viec: Any) -> str:
    return _TEN_VIEC_GD.get(str(viec or ""), str(viec or "việc"))


def dang_thu(goc: str, ma: str) -> List[str]:
    """Thí nghiệm đang mở của giám đốc kênh; chưa có mà đang chế độ gợi ý thì "định thử (chưa áp)"."""
    from .giam_doc import so_thi_nghiem as stn  # noqa: PLC0415
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    try:
        mo = stn.dang_mo(stn.doc(goc, ma))
    except Exception:  # noqa: BLE001
        mo = []
    if mo:
        return [_cat_chu("{0}: {1}".format(_ten_viec_gd(t.get("viec")), _thuat_ngu(t.get("gia_thuyet"))), 150)
                for t in mo[:2]]
    bc = _doc_json(os.path.join(thu_muc_giam_doc(goc, ma), "bao-cao.json"))
    if isinstance(bc, dict) and bc.get("che_do") == "goi_y" and bc.get("se_lam"):
        ra = []
        for x in bc["se_lam"][:2]:
            if not isinstance(x, dict):
                continue
            than = ("{0}: {1} → {2}".format(x.get("khoa"), x.get("cu"), x.get("moi")) if x.get("loai") == "tham_so"
                    else "chỉ đạo “{0}”".format(x.get("moi")))
            ra.append(_cat_chu("Định thử (chưa áp): " + _thuat_ngu(than), 150))
        return ra
    return []


def lich_dang_tiep(goc: str, k: Dict[str, Any], *, bay_gio: Optional[_dt.datetime] = None,
                   n: int = 2) -> List[Dict[str, Any]]:
    """Mốc đăng sắp tới của kênh: `[{luc, chu_luc, tieu_de, loai, da_hen, chu}]`.

    Có mốc TƯƠNG LAI đã hẹn (`xep_lich.moc_da_co`: kế hoạch + sổ máy đăng) → tối đa `n` mốc sớm nhất.
    Chưa có → một khe kế tiếp (`khe_trong_som_nhat`, đã theo nhịp N ngày) kèm giờ máy chọn content/sản xuất
    = khe − `san_xuat_truoc_gio` (luật đúng hạn 03/10/2026)."""
    from . import xep_lich  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    ma = str(k.get("ma") or "")
    tieu = {}
    for d in (k.get("ke_hoach") or []):
        m = xep_lich._moc(str(d.get("ngay") or ""), str(d.get("gio") or ""))  # noqa: SLF001
        if m is not None and d.get("tieu_de") and d.get("loai") not in ("bo", "da_bo"):
            tieu[m] = str(d["tieu_de"])
    ra: List[Dict[str, Any]] = []
    for moc in sorted(m for m in set(xep_lich.moc_da_co(goc, ma)) if m > bay_gio)[:n]:
        cl = moc.strftime("%H:%M %d/%m")
        ra.append({"luc": moc.isoformat(timespec="minutes"), "chu_luc": cl, "tieu_de": tieu.get(moc, ""),
                   "loai": "da_hen", "da_hen": True, "chu": cl + " · đã hẹn"})
    if ra:
        return ra
    kenh = _kenh_mod.doc_kenh(goc, ma)
    ngay, gio = xep_lich.khe_trong_som_nhat(goc, ma, kenh, bay_gio=bay_gio)
    moc = xep_lich._moc(ngay, gio) if ngay else None  # noqa: SLF001
    if moc is None:
        return []
    truoc = max(0, int(getattr(kenh, "san_xuat_truoc_gio", 0) or 0))
    sx = moc - _dt.timedelta(hours=truoc)
    viec = ("máy chọn content & sản xuất lúc " + sx.strftime("%H:%M %d/%m")) if sx > bay_gio         else "máy đang chọn content & sản xuất"
    return [{"luc": moc.isoformat(timespec="minutes"), "chu_luc": "khe " + moc.strftime("%H:%M %d/%m"),
             "tieu_de": "", "loai": "", "da_hen": False,
             "chu": "khe {0} — {1}".format(moc.strftime("%H:%M %d/%m"), viec)}]


def dong_lich(x: Dict[str, Any], gioi_han: int = 24) -> str:
    """Một dòng người đọc của một mốc `lich_dang_tiep` (kèm tiêu đề nếu đã có)."""
    td = str(x.get("tieu_de") or "")
    return str(x.get("chu") or x.get("chu_luc") or "") + (
        " 「{0}」".format(td if len(td) <= gioi_han else td[:gioi_han - 1] + "…") if td else "")


#: Thứ tự thẻ: đỏ lên đầu.
_THU_TU_PHONG = {HONG: 0, LUU_Y: 1, TOT: 2, TAT: 3}


def muc_phong(k: Dict[str, Any], so: Dict[str, Any]) -> str:
    """Màu thẻ ở phòng điều hành: ĐỎ = kênh hỏng hoặc xếp loại tụt; VÀNG = chờ bạn/lưu ý; XÁM = tắt."""
    mt = k.get("muc_the") or muc_the(k)
    if mt == HONG or (so or {}).get("loai") == "tut":
        return HONG
    if mt in (CHO_BAN, LUU_Y):
        return LUU_Y
    return TAT if mt == TAT else TOT


def _tong_tuan(cac_so: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """View/sub/giờ xem 7 ngày cộng mọi kênh YouTube; % so tuần trước CHỈ trên kênh có đủ hai tuần."""
    ra: Dict[str, Dict[str, Any]] = {}
    for khoa in ("xem", "sub", "gio_xem"):
        nay, nay_du, truoc_du, co = 0.0, 0.0, 0.0, False
        for so in cac_so:
            t = (so.get("tuan") or {})
            a, b = (t.get("nay") or {}).get(khoa), (t.get("truoc") or {}).get(khoa)
            if a is None:
                continue
            co = True
            nay += a
            if b is not None:
                nay_du += a
                truoc_du += b
        ra[khoa] = {"nay": nay if co else None,
                    "pct": round(100.0 * (nay_du - truoc_du) / truoc_du) if truoc_du > 0 else None}
    return ra


def khoi_cong_ty(goc: str, bang: Dict[str, Any], *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Khối CÔNG TY: 7 ngày (so tuần trước) · video hôm nay x/trần · máy · ví · phiên bản · số việc của bạn."""
    bay_gio = bay_gio or _dt.datetime.now()
    tat_ca = list(bang.get("kenh") or []) + list(bang.get("kenh_khac") or [])
    cac_ma = list(dict.fromkeys(ma_youtube(str(k.get("ma") or "")) for k in tat_ca if k.get("ma")))
    cac_so = [s for s in (doc_so_kenh(goc, ma_so_kenh(goc, m)) for m in cac_ma) if s]
    tuan = _tong_tuan(cac_so)

    hom_nay, tran = None, None
    try:
        from . import cong_suat  # noqa: PLC0415
        from .giam_doc import tong  # noqa: PLC0415

        hom_nay = cong_suat._video_ban_giao(  # noqa: SLF001 — bộ đếm có sẵn, chỉ đọc
            goc, _dt.datetime.combine(bay_gio.date(), _dt.time()).timestamp())
        tran = tong.tran_may(cong_suat.doc_hien_tai(goc)) or None
    except Exception:  # noqa: BLE001
        pass

    may = bang.get("may") or {}
    tt_ = doc_tinh_trang(goc)
    van_de, muc_may = [], TOT
    if not ((may.get("may_nen") or {}).get("agent") or {"song": True}).get("song", True):
        van_de.append("máy chạy nền tắt")
        muc_may = HONG
    o_dia = may.get("o_dia") or {}
    if o_dia.get("muc") in (HONG, LUU_Y):
        van_de.append("đĩa còn {0:.0f} GB".format(o_dia.get("con_gb") or 0))
        muc_may = HONG if o_dia["muc"] == HONG or muc_may == HONG else LUU_Y
    kenh_tt = (tt_.get("kenh") or {}) if isinstance(tt_.get("kenh"), dict) else {}
    cho_nguoi = sorted(m for m, x in kenh_tt.items() if isinstance(x, dict) and x.get("trang_thai") == "cho_nguoi")
    tu_thu = sorted(m for m, x in kenh_tt.items() if isinstance(x, dict) and x.get("trang_thai") == "tu_cho_co_han")
    if cho_nguoi:
        van_de.append("{0} kênh cần bạn".format(len(cho_nguoi)))
        muc_may = HONG
    ram = ((tt_.get("may") or {}).get("ram") or {})
    tip_may = ["Ổ đĩa trống: {0} GB".format(_vn(o_dia.get("con_gb"))),
               "RAM trống: {0}/{1} GB".format(_vn(ram.get("trong_gb"), 1), _vn(ram.get("tong_gb"), 0))]
    if tu_thu:
        tip_may.append("Kênh đang tự thử lại (máy tự lo): " + ", ".join(tu_thu))

    vi = may.get("vi") or {}
    pb: Dict[str, Any] = {}
    try:
        from . import cap_nhat_git as cng  # noqa: PLC0415

        st = cng.doc_trang_thai(goc) or {}
        pb = {"ban": cng.doc_phien_ban(goc), "tu_dong": bool(cng.doc_cau_hinh(goc).get("tu_dong_cap_nhat")),
              "ban_moi": str(st.get("ban_moi") or ""), "kiem_luc": str(st.get("kiem_luc") or ""),
              "loi": str(st.get("loi") or "")}
    except Exception:  # noqa: BLE001
        pass
    return {
        "tuan": tuan, "so_kenh_co_so": len(cac_so),
        "video_hom_nay": hom_nay, "tran": round(tran) if tran else None,
        "may": {"muc": muc_may, "chu": "Khoẻ" if not van_de else "; ".join(van_de), "tip": "\n".join(tip_may)},
        "vi": {"ngay": vi.get("so_ngay_con_chay"), "vnd": vi.get("vnd"), "muc": vi.get("muc") or TOT},
        "phien_ban": pb, "so_viec": len(bang.get("viec") or []),
        "tong_giam_doc": dict(may.get("cong_ty") or {}),
    }


def _an_bool(f: Callable[[], bool]) -> bool:
    try:
        return bool(f())
    except Exception:  # noqa: BLE001
        return False


def phong_dieu_hanh(goc: str, bang: Dict[str, Any], *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """PHẦN NHẸ (đọc đĩa, gọi mỗi lần làm mới): `{cong_ty, the: {ma: {...}}, thu_tu, can_tinh, dang_tinh}`.
    `bang` = `anh_bang(...)`. `can_tinh` = mã kênh có số cần tính lại (giao diện tự `sinh_tinh_so`)."""
    bay_gio = bay_gio or _dt.datetime.now()
    the: Dict[str, Dict[str, Any]] = {}
    can_tinh: List[str] = []

    def _an(f: Callable[[], Any], mac: Any) -> Any:
        try:
            return f()
        except Exception:  # noqa: BLE001 — một dòng phụ hỏng không làm hỏng thẻ
            return mac

    for k in (bang.get("kenh") or []):
        ma = str(k.get("ma") or "")
        ma_so = ma_so_kenh(goc, ma)
        if _an_bool(lambda: so_kenh_cu(goc, ma_so, bay_gio=bay_gio)):
            can_tinh.append(ma_so)
        so = doc_so_kenh(goc, ma_so)
        ypp = k.get("ypp") or {}
        sub = _so(ypp.get("dang_ky"))
        gio = _so(ypp.get("gio_xem"))
        if sub is None:
            sub = _so((so.get("ypp") or {}).get("sub"))
        if gio is None:
            gio = _so((so.get("ypp") or {}).get("gio_xem"))
        the[ma] = {
            "ma_so": ma_so, "so": so, "muc": muc_phong(k, so),
            "ypp": {"sub": sub, "gio_xem": gio, "can_sub": YPP_SUB, "can_gio": YPP_GIO},
            "doi_ai": _an(lambda: doi_ai_noi(goc, ma), []),
            "dang_thu": _an(lambda: dang_thu(goc, ma), []),
            "lich_tiep": _an(lambda: lich_dang_tiep(goc, k, bay_gio=bay_gio), []),
        }
    for k in (bang.get("kenh_khac") or []):
        ma_so = ma_so_kenh(goc, str(k.get("ma") or ""))
        if ma_so and ma_so not in can_tinh and _an_bool(lambda: so_kenh_cu(goc, ma_so, bay_gio=bay_gio)):
            can_tinh.append(ma_so)
    thu_tu = sorted(the, key=lambda m: (_THU_TU_PHONG.get(the[m]["muc"], 9), m))
    return {"cong_ty": khoi_cong_ty(goc, bang, bay_gio=bay_gio), "the": the, "thu_tu": thu_tu,
            "can_tinh": list(dict.fromkeys(can_tinh)), "dang_tinh": dang_tinh(goc)}


# ── Ba trang chi tiết ──────────────────────────────────────────────────────


def _doc_chu(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def bao_cao_tuan(goc: str, ma: str) -> Dict[str, str]:
    """`{kenh, kenh_duong, cong_ty, cong_ty_duong}` — chữ Markdown của báo cáo tuần kênh + công ty."""
    from .giam_doc import bao_cao as _bc, tong  # noqa: PLC0415
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    dk = os.path.join(thu_muc_giam_doc(goc, ma), _bc.TEP_BAO_CAO_MD) if ma else ""
    dc = os.path.join(goc, tong.THU_MUC, tong.TEP_MD)
    return {"kenh": _thuat_ngu(_doc_chu(dk)) if dk else "", "kenh_duong": dk,
            "cong_ty": _thuat_ngu(_doc_chu(dc)), "cong_ty_duong": dc}


def _khoa_so_cg(d: Dict[str, Any]) -> str:
    """Khoá gộp một bài trong sổ chuyên gia — ĐÚNG khoá `giam_doc.hoi_dong.doc_so`."""
    return str(d.get("khoa") or d.get("cau") or "")[:80]


def _so_chuyen_gia(goc: str, ma: str) -> List[Dict[str, Any]]:
    """Sổ kinh nghiệm riêng của 3 chuyên gia (`hoi_dong.duong_so`), gộp như `hoi_dong.doc_so`: một dòng mỗi
    khoá, n = số video ủng hộ."""
    try:
        from .giam_doc import hoi_dong  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — chưa có đội chuyên gia
        return []
    ra: List[Dict[str, Any]] = []
    for cg in hoi_dong.CHUYEN_GIA:
        try:
            duong = hoi_dong.duong_so(goc, ma, cg["ma"])
        except Exception:  # noqa: BLE001
            continue
        nhom: Dict[str, List[Dict[str, Any]]] = {}
        for dong in _doc_duoi(duong, 2 * 1024 * 1024):
            try:
                d = json.loads(dong)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("cau"):
                nhom.setdefault(_khoa_so_cg(d), []).append(d)
        for khoa, xs in nhom.items():
            vid = sorted({str(x.get("video_id")) for x in xs if x.get("video_id")})
            ra.append({"pham_vi": "so_" + str(cg.get("pham_vi") or "kenh"), "truc": "", "cum": "",
                       "cau": xs[-1]["cau"], "n": len(vid), "tin_cay": "", "bom": True,
                       "bong": all(x.get("bong") for x in xs), "video": vid, "nguon": "so_chuyen_gia",
                       "khoa": khoa, "chuyen_gia": cg["ma"], "ma_bai": "cg:{0}:{1}".format(cg["ma"], khoa)})
    return ra


def chuyen_gia_cua(b: Dict[str, Any]) -> str:
    """Bài học thuộc chuyên gia nào (`b["chuyen_gia"]` nếu đội đã ghi, không thì theo trục)."""
    cg = str(b.get("chuyen_gia") or "")
    return cg if cg in _TEN_CHUYEN_GIA else _TRUC_CHUYEN_GIA.get(str(b.get("truc") or ""), "chu_de")


def ma_bai(b: Dict[str, Any]) -> str:
    """Mã bền của một bài học: khám nghiệm = "kn:" + (trục|giá trị|cụm); nguồn khác = băm câu."""
    import hashlib  # noqa: PLC0415

    khoa = str(b.get("khoa") or "")
    if b.get("nguon") == "kham_nghiem" and khoa.count("|") >= 3:
        truc, gt, _huong, cum = khoa.split("|", 3)
        return "kn:{0}|{1}|{2}".format(truc, gt, cum)
    tho = "|".join(str(b.get(x) or "") for x in ("pham_vi", "truc", "cum", "cau"))
    return "h:" + hashlib.sha1(tho.encode("utf-8")).hexdigest()[:12]


def _duong_gach(goc: str, ma: str) -> str:
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    return os.path.join(thu_muc_giam_doc(goc, ma), TEP_BAI_HOC_GACH)


def doc_bai_hoc_gach(goc: str, ma: str) -> List[Dict[str, Any]]:
    ra: List[Dict[str, Any]] = []
    for dong in _doc_duoi(_duong_gach(goc, ma), 2 * 1024 * 1024):
        try:
            d = json.loads(dong)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("ma_bai"):
            ra.append(d)
    return ra


def khoa_bai_hoc_gach(goc: str, ma: str) -> set:
    """Tập `ma_bai` đã bị gạch — để nơi dựng lời nhắc (chien_luoc.bai_hoc / đội chuyên gia) lọc ra."""
    return {d["ma_bai"] for d in doc_bai_hoc_gach(goc, ma)}


def so_bai_hoc(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Sổ bài học cho trang Bài học (chậm vài giây — gọi ở luồng nền): `chien_luoc.bai_hoc.doc(tat_ca=True)`
    + bài đã gạch trong sổ. Mỗi dòng `{ma_bai, chuyen_gia, ten_chuyen_gia, pham_vi, ten_pham_vi, truc, cum,
    cau, n, tin_cay, bom, bong, video, nguon, khoa, da_gach}`; xếp chuyên gia → phạm vi → n giảm."""
    from .chien_luoc import bai_hoc  # noqa: PLC0415

    ds = _so_chuyen_gia(goc, ma) + list(bai_hoc.doc(goc, ma, tat_ca=True, bay_gio=bay_gio))
    gach = {d["ma_bai"]: d for d in doc_bai_hoc_gach(goc, ma)}
    ra: List[Dict[str, Any]] = []
    co = set()
    for b in ds:
        mb = str(b.get("ma_bai") or ma_bai(b))
        co.add(mb)
        cg = chuyen_gia_cua(b)
        ra.append({"ma_bai": mb, "chuyen_gia": cg, "ten_chuyen_gia": _TEN_CHUYEN_GIA[cg],
                   "pham_vi": b.get("pham_vi") or "kenh", "ten_pham_vi": TEN_PHAM_VI.get(b.get("pham_vi"), "Kênh này"),
                   "truc": b.get("truc") or "", "cum": b.get("cum") or "", "cau": _thuat_ngu(b.get("cau")),
                   "n": int(b.get("n") or 0), "tin_cay": b.get("tin_cay") or "", "bom": bool(b.get("bom")),
                   "bong": bool(b.get("bong")), "video": list(b.get("video") or []), "nguon": b.get("nguon") or "",
                   "khoa": b.get("khoa") or "", "da_gach": mb in gach})
    for mb, g in gach.items():
        if mb in co:
            continue
        cg = g.get("chuyen_gia") if g.get("chuyen_gia") in _TEN_CHUYEN_GIA else "chu_de"
        ra.append({"ma_bai": mb, "chuyen_gia": cg, "ten_chuyen_gia": _TEN_CHUYEN_GIA[cg],
                   "pham_vi": g.get("pham_vi") or "kenh", "ten_pham_vi": TEN_PHAM_VI.get(g.get("pham_vi"), "Kênh này"),
                   "truc": g.get("truc") or "", "cum": g.get("cum") or "", "cau": g.get("cau") or "",
                   "n": int(g.get("n") or 0), "tin_cay": "", "bom": False, "bong": False,
                   "video": list(g.get("video") or []), "nguon": g.get("nguon") or "", "khoa": g.get("khoa") or "",
                   "da_gach": True})
    thu_cg = {k: i for i, (k, _t) in enumerate(CHUYEN_GIA)}
    ra.sort(key=lambda r: (thu_cg.get(r["chuyen_gia"], 9), _THU_PHAM_VI.get(r["pham_vi"], 9), r["da_gach"], -r["n"]))
    return ra


def _go_dong(duong: str, trung: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
    """Gỡ khỏi tệp JSONL các dòng `trung(d)` (ghi nguyên tử, dòng hỏng giữ nguyên). Trả các dòng đã gỡ."""
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            tho = tep.readlines()
    except OSError:
        return []
    giu, go = [], []
    for dong in tho:
        try:
            d = json.loads(dong)
        except ValueError:
            giu.append(dong)
            continue
        if isinstance(d, dict) and trung(d):
            go.append(d)
        else:
            giu.append(dong)
    if go:
        tam = duong + ".tam-gach"
        with open(tam, "w", encoding="utf-8", newline="\n") as tep:
            tep.write("".join(x if x.endswith("\n") else x + "\n" for x in giu))
        os.replace(tam, duong)
    return go


def gach_bai_hoc(goc: str, ma: str, bai: Dict[str, Any], *, ly_do: str = "",
                 bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Nút "Sai": ghi một dòng vào `giam-doc/bai-hoc-gach.jsonl`. Bài KHÁM NGHIỆM (`bai-hoc.jsonl`) và bài trong
    SỔ CHUYÊN GIA (`hoi_dong.duong_so`) thì gỡ luôn các dòng của nó khỏi tệp nguồn (giữ nguyên văn trong
    `dong_goc` của sổ gạch) — không còn vào lời nhắc nào nữa (`kham_nghiem.doc_bai_hoc`, `hoi_dong.doc_so` chỉ
    đọc các tệp đó). Bài từ nguồn khác: chỉ ghi sổ (`da_loai_khoi_loi_nhac=False`) — nơi dựng lời nhắc lọc bằng
    `khoa_bai_hoc_gach`."""
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    mb = str(bai.get("ma_bai") or ma_bai(bai))
    dong_goc: List[Dict[str, Any]] = []
    if mb.startswith("cg:"):
        # Sổ chuyên gia: gỡ mọi dòng cùng khoá — `hoi_dong.doc_so` (lời nhắc chuyên gia) chỉ đọc tệp này.
        _, cg, khoa = mb.split(":", 2)
        try:
            from .giam_doc import hoi_dong  # noqa: PLC0415

            duong = hoi_dong.duong_so(goc, ma, cg)
        except Exception:  # noqa: BLE001
            duong = ""
        dong_goc = _go_dong(duong, lambda d: _khoa_so_cg(d) == khoa) if duong else []
    elif mb.startswith("kn:"):
        truc, gt, cum = mb[3:].split("|", 2)
        dong_goc = _go_dong(os.path.join(thu_muc_giam_doc(goc, ma), "bai-hoc.jsonl"),
                            lambda d: (str(d.get("truc") or "") == truc and str(d.get("gia_tri") or "") == gt
                                       and str(d.get("cum") or "") == cum))
    ghi = {"luc": (bay_gio or _dt.datetime.now()).isoformat(timespec="seconds"), "ma_bai": mb,
           "chuyen_gia": mb.split(":", 2)[1] if mb.startswith("cg:") else chuyen_gia_cua(bai), "pham_vi": bai.get("pham_vi") or "kenh", "truc": bai.get("truc") or "",
           "cum": bai.get("cum") or "", "cau": str(bai.get("cau") or ""), "n": int(bai.get("n") or 0),
           "video": list(bai.get("video") or []), "nguon": bai.get("nguon") or "", "khoa": bai.get("khoa") or "",
           "ly_do": str(ly_do or ""), "da_loai_khoi_loi_nhac": bool(dong_goc), "dong_goc": dong_goc}
    duong_gach = _duong_gach(goc, ma)
    os.makedirs(os.path.dirname(duong_gach), exist_ok=True)
    with open(duong_gach, "a", encoding="utf-8", newline="\n") as tep:
        tep.write(json.dumps(ghi, ensure_ascii=False, default=str) + "\n")
    return ghi


_TEN_CONG = {"hien_thi": "Hiển thị", "ctr": "Tỉ lệ bấm", "giu_chan": "Giữ chân", "khong": "không cổng nào"}
_TEN_LOAI_QD = {"du_doan": "Đoán thắng/trượt", "thi_nghiem": "Thí nghiệm", "chan_doan": "Chẩn đoán cổng (khám nghiệm)",
                "hoi_dong": "Hội đồng chuyên gia", "luot": "Lượt giám đốc", "doi_khe": "Đổi khe đăng (tổng giám đốc)"}
_TEN_CONG_HD = {"ap": "áp", "thu_nho": "chỉ thử nhỏ", "quan_sat": "chỉ quan sát"}


def so_quyet_dinh(goc: str, ma: str) -> Dict[str, Any]:
    """Trang "Quyết định & độ chính xác": `{dong: [{luc, loai, ten_loai, quyet, vi_sao, ket_qua, dung}],
    ti_le: [{loai, ten_loai, dung, tong, so_quyet}]}` từ `du-doan.json`, sổ thí nghiệm, `nhat-ky.jsonl`, bản
    khám nghiệm và sổ đổi khe của tổng giám đốc. `dung`: True/False đã chấm, None = chưa chấm được."""
    from .giam_doc import so_thi_nghiem as stn  # noqa: PLC0415
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    dong: List[Dict[str, Any]] = []

    def them(luc: Any, loai: str, quyet: str, vi_sao: Any, ket_qua: str, dung: Optional[bool]) -> None:
        dong.append({"luc": str(luc or "")[:16].replace("T", " "), "loai": loai, "ten_loai": _TEN_LOAI_QD[loai],
                     "quyet": _thuat_ngu(quyet), "vi_sao": _cat_chu(_thuat_ngu(vi_sao), 400),
                     "ket_qua": ket_qua, "dung": dung})

    for d in stn.doc_du_doan(goc, ma):
        doan = "THẮNG" if d.get("ket") == "thang" else "trượt"
        if "dung" in d:
            kq = "{0} — thật: {1}".format("ĐÚNG" if d["dung"] else "SAI",
                                          "thắng" if d.get("ket_that") == "thang" else "trượt")
        else:
            kq = "chờ đủ 48 giờ"
        them(d.get("luc"), "du_doan", "Video {0}: đoán {1}".format(d.get("video_id"), doan), d.get("ly_do"), kq,
             d.get("dung") if "dung" in d else None)
    for t in stn.doc(goc, ma):
        tt_ = str(t.get("trang_thai") or "")
        ly = (t.get("ket_luan") or {}).get("ly_do") or ""
        dung = True if tt_ in ("giu", "mo_rong") else (False if tt_ in ("bo", "quay_lui") else None)
        them(t.get("bat_dau"), "thi_nghiem", "Thử {0}: {1}".format(_ten_viec_gd(t.get("viec")), t.get("gia_thuyet")),
             t.get("ly_do_llm"), _TEN_TN.get(tt_, tt_) + (" — " + str(ly) if ly else ""), dung)
    for x in stn.doc_nhat_ky(goc, ma, so_dong=200):
        sau = x.get("sau") if isinstance(x.get("sau"), dict) else {}
        if x.get("viec") == "luot":
            quyet = "Lượt {0}{1}: chọn {2}/{3} việc, đoán thêm {4} video".format(
                {"goi_y": "gợi ý", "tu_ap": "tự áp", "tat": "tắt"}.get(sau.get("che_do"), sau.get("che_do") or "?"),
                " (tuần)" if sau.get("tuan") else "", sau.get("chon", 0), sau.get("thuc_don", 0),
                sau.get("du_doan_moi", 0))
            kq = "báo động sức khoẻ" if sau.get("bao_dong") else "—"
        else:
            quyet = "{0}: {1} → {2}".format(x.get("viec"), json.dumps(x.get("truoc"), ensure_ascii=False, default=str)[:80],
                                            json.dumps(x.get("sau"), ensure_ascii=False, default=str)[:80])
            kq = "—"
        them(x.get("luc"), "luot", quyet, x.get("ly_do_llm"), kq, None)
    try:
        from .giam_doc import kham_nghiem  # noqa: PLC0415

        for d in kham_nghiem.doc_kham(goc, ma):
            k = d.get("ket") or {}
            them(d.get("luc"), "chan_doan", "Video {0} ({1}): cổng hỏng = {2}".format(
                d.get("video_id"), d.get("moc"), _TEN_CONG.get(k.get("cong_hong"), k.get("cong_hong") or "?")),
                k.get("chan_doan"), {"thang": "video thắng", "truot": "video trượt"}.get(d.get("ket_luan") or "", "chờ"),
                None)
    except Exception:  # noqa: BLE001
        pass
    # Phiên hội đồng chuyên gia (`hoi-dong.jsonl`), lý do lấy từ phiên cuối cùng loại nếu trùng lúc.
    tm = thu_muc_giam_doc(goc, ma)
    cuoi = _doc_json(os.path.join(tm, TEP_HOI_DONG_CUOI))
    cuoi = cuoi if isinstance(cuoi, dict) else {}
    for dong_tho in _doc_duoi(os.path.join(tm, "hoi-dong.jsonl")):
        try:
            x = json.loads(dong_tho)
        except ValueError:
            continue
        if not isinstance(x, dict):
            continue
        h = cuoi.get(x.get("loai")) if isinstance(cuoi.get(x.get("loai")), dict) else {}
        q = (h.get("quyet") or {}) if h.get("luc") == x.get("luc") else {}
        ten_cg = dict(CHUYEN_GIA).get(str(x.get("chon") or ""), str(x.get("chon") or "—"))
        quyet = "{0}: chọn {1} · độ tin {2}".format(str(x.get("loai") or "").replace("_", " "), ten_cg,
                                                  x.get("do_tin") if x.get("do_tin") is not None else "?")
        if x.get("loai_bo"):
            quyet += " · loại vì số bịa: " + ", ".join(dict(CHUYEN_GIA).get(m, m) for m in x["loai_bo"])
        them(x.get("luc"), "hoi_dong", quyet, q.get("ly_do") or x.get("loi") or "",
             _TEN_CONG_HD.get(str(x.get("cong") or ""), str(x.get("cong") or "—")), None)
    try:
        from .giam_doc import tong  # noqa: PLC0415

        for t in tong.doc_so(goc).get("thay_doi") or []:
            if isinstance(t, dict) and t.get("ma") in (ma, ma_youtube(ma)):
                them(t.get("luc"), "doi_khe", "Khe {0} → {1}".format(t.get("khe_cu"), t.get("khe_moi")),
                     t.get("ly_do") or t.get("ly_do_llm"), str(t.get("trang_thai") or "đã áp"), None)
    except Exception:  # noqa: BLE001
        pass
    dong.sort(key=lambda d: d["luc"], reverse=True)

    ti_le = []
    for loai, ten in _TEN_LOAI_QD.items():
        cham = [d for d in dong if d["loai"] == loai and d["dung"] is not None]
        co = [d for d in dong if d["loai"] == loai]
        # Chỉ loại CHẤM ĐƯỢC (dự đoán, thí nghiệm) — lượt/chẩn đoán/đổi khe chưa có thước đo đúng sai.
        if co and (loai in ("du_doan", "thi_nghiem") or cham):
            ti_le.append({"loai": loai, "ten_loai": ten, "dung": sum(1 for d in cham if d["dung"]),
                          "tong": len(cham), "so_quyet": len(co)})
    # Sổ độ chính xác của hội đồng (`giam_doc.hoi_dong.do_chinh_xac`, đọc không ghi) — có thì THAY phần tự
    # đếm: đúng định nghĩa đúng/sai + quyền tự áp theo thành tích mà giám đốc thật sự dùng.
    try:
        from .giam_doc import hoi_dong  # noqa: PLC0415

        dcx = (hoi_dong.do_chinh_xac(goc, ma, ghi=False) or {}).get("loai") or {}
    except Exception:  # noqa: BLE001
        dcx = {}
    if dcx:
        tuong_ung = {"du_doan": "du_doan", "doi_chuan": "thi_nghiem", "chan_doan_cong": "chan_doan", "chia_khe": "doi_khe"}
        ti_le = [{"loai": k, "ten_loai": str(o.get("ten") or k).capitalize(), "dung": int(o.get("dung") or 0),
                  "tong": int(o.get("n") or 0), "quyen": str(o.get("quyen") or ""),
                  "so_quyet": max(int(o.get("n") or 0), sum(1 for d in dong if d["loai"] == tuong_ung.get(k)))}
                 for k, o in dcx.items() if isinstance(o, dict)]
    return {"dong": dong, "ti_le": ti_le}


# ═══════════════════════════════════════════════════════════════════════════
# 11) CLI — tiến trình con tính số (giao diện sinh, xem `sinh_tinh_so`)
# ═══════════════════════════════════════════════════════════════════════════


def _main(argv: Optional[List[str]] = None) -> int:
    import sys  # noqa: PLC0415

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "tinh-so":
        print("Dùng: python -m core.bang_dieu_khien tinh-so <mã kênh>...")
        return 2
    goc = os.getcwd()
    loi = 0
    try:
        for ma in argv[1:]:
            bat_dau = _dt.datetime.now()
            try:
                tinh_va_luu(goc, ma)
                print("{0} {1}: xong ({2:.1f}s)".format(bat_dau.strftime("%Y-%m-%d %H:%M:%S"), ma,
                                                       (_dt.datetime.now() - bat_dau).total_seconds()), flush=True)
            except Exception as e:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
                loi += 1
                print("{0} {1}: LỖI {2}: {3}".format(bat_dau.strftime("%Y-%m-%d %H:%M:%S"), ma,
                                                     type(e).__name__, str(e)[:200]), flush=True)
    finally:
        try:
            du = _doc_json(_duong_khoa_tinh(goc))
            if isinstance(du, dict) and int(du.get("pid") or 0) in (0, os.getpid()):
                os.remove(_duong_khoa_tinh(goc))
        except (OSError, ValueError, TypeError):
            pass
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(_main())
