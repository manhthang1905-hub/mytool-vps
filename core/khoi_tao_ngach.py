"""**Khởi tạo NGÁCH bằng AI** — cửa vào duy nhất cho VPS mới / chủ đề mới / quốc gia mới.

    python -m core.khoi_tao_ngach --chu-de "nấu ăn tại gia" --quoc-gia VN --ngon-ngu vi \\
        [--kenh-mau https://www.youtube.com/@... ...] [--tu-khoa "..." ...] [--ma-kenh K1] [--thu]

Người chỉ nhập chủ đề + quốc gia + ngôn ngữ (thêm 1–3 kênh mẫu hoặc từ khoá nếu có). Bốn bước,
mỗi bước chạy lại được (đã có thì dùng lại, câu trả lời AI có nhớ đệm):

a) **Hồ sơ ngách** `CHANNEL/_NHOM/<nhóm>/ngach.yaml` — LLM (qua ví ShopAPI) đọc khung
   `CHANNEL/_KHUON/ngach-mau.yaml` + hồ sơ ngách tâm lý Nhật làm ví dụ, viết: mô tả ngách theo NGHĨA,
   tệp khán giả, cụm, luật chọn, tiêu chí đối thủ, thị trường (ngôn ngữ, múi giờ, giờ đăng gợi ý,
   bậc làm tròn view…), chuẩn bìa ước lượng, cụm tìm kiếm. Mã kiểm, chuẩn hoá, ghi YAML.
b) **Kênh** `CHANNEL/<MÃ>/` từ khuôn `CHANNEL/_KHUON/kenh-mau/` (cấu hình sản xuất đã chứng minh):
   kenh.yaml theo ngôn ngữ/thị trường mới; LLM VIẾT LẠI theo mục tiêu (không dịch máy) những lời nhắc
   còn mang ngách cũ (hook, chấm hook, SEO, bìa, nhạc) và 8 khoá văn hoá/bìa của style.yaml — lời nhắc
   chung giữ nguyên (con đường kênh thắng: lời nhắc ngắn, sức mạnh nằm ở chấm). Ảnh nhân vật tạo bằng
   ví (một ảnh). Sổ tuyến + Công thức V7 gieo theo tệp.
c) **Nghiên cứu khởi động** — tìm YouTube theo `tu_khoa_tim` + kênh mẫu → hộp thư đối thủ → chuỗi
   "Một nút" có ví (chốt đối thủ, kiểm ngách THEO NGHĨA bằng LLM, quét content = kho nguồn). Từ hôm
   sau mắt cào của phiên quét ngày còn tìm thêm bằng chính Chrome kênh (`/tim-kiem/can-tim`).
d) **Giai đoạn** — kenh.yaml `chien_luoc: "tu_dong"` + `cong-thuc-v7.json` có `tep`: kênh "moi" chọn
   nguồn bằng VPH + lượt thăm dò; có video thắng thật (cổng chuyển V7) thì tự chuyển sang V7.

`--thu`: KHÔNG gọi AI, không gọi mạng, không tạo ảnh — dựng bản nháp từ khuôn và in kế hoạch.
Không bật tiền/tự chạy: `tu_chay`, `tu_duyet`, `ngan_sach_ngay` để chủ kênh quyết (CLAUDE.md).

Việc máy không tự làm được (giọng đọc, đăng nhập Chrome kênh, nạp ví) ghi ở `CHANNEL/<MÃ>/KHOI-TAO.md`
và in cuối lệnh.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .kenh import THU_MUC_PROMPT, TEP_KENH, TEP_STYLE, doc_yaml, duong_kenh

__all__ = [
    "YeuCau", "KetQua", "slug", "khoi_tao", "chay_nen", "main",
    "CAN_VIET_LAI", "KHOA_STYLE_VIET_LAI", "chuan_hoa_ho_so", "ho_so_nhap", "kiem_loi_nhac",
]

#: Khuôn kênh (cấu hình sản xuất đã chứng minh) — tệp lên kho.
THU_MUC_KENH_MAU = os.path.join("_KHUON", "kenh-mau")
TEP_KHUNG_NGACH = os.path.join("_KHUON", "ngach-mau.yaml")
TEP_VI_DU_NGACH = os.path.join("_KHUON", "ngach-mau-ja-tam-ly.yaml")
#: Thư mục làm việc của lệnh trong nhóm (nhớ đệm AI, kết quả tìm kiếm) — ở lại máy, không lên kho.
THU_MUC_KHOI_TAO = "khoi-tao"
TEP_VIEC = "KHOI-TAO.md"

#: Mô hình cho các lượt khởi tạo — một lần cho cả ngách, chất lượng quyết định mọi thứ phía sau
#: (cùng mô hình đọc nghĩa của `trang_chu.MO_HINH_LOC_NGHIA`; chủ dự án: "đừng tiếc token").
MO_HINH = "claude-fable-5"

#: Lời nhắc của kênh mẫu còn mang ngách cũ (tâm lý Nhật) — LLM viết lại theo ngách mới. Các tệp
#: khác chỉ dùng chỗ điền (`<<NGON_NGU>>`, `<<LANGUAGE>>`…) nên đúng cho mọi ngách, chép nguyên văn.
CAN_VIET_LAI = ("2d-hook.md", "2e-cham-hook.md", "6-seo.md", "8-thumbnail.md", "9-nhac.md")
#: Khoá style.yaml mang văn hoá/ngách — viết lại; 13 khoá hình còn lại giữ nguyên.
KHOA_STYLE_VIET_LAI = ("audience_language", "audience_culture_note", "cultural_props",
                       "cultural_metaphors", "cultural_emotion_style", "thumbnail_style",
                       "scene_plan_style", "default_character_prompt")

#: Giá trị không bao giờ khớp tiêu đề nào — đặt vào bộ từ "đường lùi" mà ngách không có, để mã KHÔNG
#: rơi về bộ từ tiếng Nhật mặc định (danh sách rỗng = "dùng hằng cũ").
KHONG_KHOP = "⊘"
_KHOA_KHONG_DUOC_RONG = ("tu_loai_tru", "ten_kenh_loai_tru", "handle_loai_tru", "tu_kenh_hien_nhien",
                         "handle_hien_nhien", "tu_tieu_de_hien_nhien", "tu_tuoi")

#: Theo ngôn ngữ: ký tự đọc lên/phút của giọng đọc (tham khảo — đo lại sau video đầu), chữ bìa
#: viết hoa được không, bậc làm tròn view YouTube hiển thị.
_BAC_LA_TINH = [{"duoi": 1000, "bac": 1}, {"duoi": 10000, "bac": 100}, {"duoi": 1000000, "bac": 1000},
                {"duoi": 10000000, "bac": 100000}, {"bac": 1000000}]
_BAC_VAN = [{"duoi": 10000, "bac": 10}, {"duoi": 1000000, "bac": 1000}, {"bac": 10000}]
BANG_TIENG: Dict[str, Dict[str, Any]] = {
    "ja": {"ky_tu": 270, "hoa": False, "bac": _BAC_VAN},
    "ko": {"ky_tu": 380, "hoa": False, "bac": _BAC_VAN},
    "zh": {"ky_tu": 260, "hoa": False, "bac": _BAC_VAN},
    "vi": {"ky_tu": 832, "hoa": True, "bac": _BAC_LA_TINH},
    "en": {"ky_tu": 920, "hoa": True, "bac": _BAC_LA_TINH},
    "th": {"ky_tu": 600, "hoa": False, "bac": _BAC_LA_TINH},
    "hi": {"ky_tu": 700, "hoa": False, "bac": _BAC_LA_TINH},
    "ar": {"ky_tu": 750, "hoa": False, "bac": _BAC_LA_TINH},
}
_TIENG_MAC_DINH = {"ky_tu": 880, "hoa": True, "bac": _BAC_LA_TINH}

#: Quốc gia → (múi giờ, độ lệch UTC giờ — dùng khi máy thiếu dữ liệu múi giờ).
MUI_GIO: Dict[str, Tuple[str, float]] = {
    "JP": ("Asia/Tokyo", 9), "VN": ("Asia/Ho_Chi_Minh", 7), "US": ("America/New_York", -5),
    "KR": ("Asia/Seoul", 9), "TW": ("Asia/Taipei", 8), "CN": ("Asia/Shanghai", 8),
    "HK": ("Asia/Hong_Kong", 8), "TH": ("Asia/Bangkok", 7), "ID": ("Asia/Jakarta", 7),
    "PH": ("Asia/Manila", 8), "MY": ("Asia/Kuala_Lumpur", 8), "SG": ("Asia/Singapore", 8),
    "IN": ("Asia/Kolkata", 5.5), "GB": ("Europe/London", 0), "DE": ("Europe/Berlin", 1),
    "FR": ("Europe/Paris", 1), "ES": ("Europe/Madrid", 1), "IT": ("Europe/Rome", 1),
    "PT": ("Europe/Lisbon", 0), "BR": ("America/Sao_Paulo", -3), "MX": ("America/Mexico_City", -6),
    "CA": ("America/Toronto", -5), "AU": ("Australia/Sydney", 10), "RU": ("Europe/Moscow", 3),
    "TR": ("Europe/Istanbul", 3), "SA": ("Asia/Riyadh", 3), "AE": ("Asia/Dubai", 4),
}

_RE_CHO_DIEN = re.compile(r"<<[A-Z0-9_]+>>")
_RE_KHOA_JSON = re.compile(r'"([a-z_]{2,})"\s*:')
_RE_NHAN_DONG = re.compile(r"(?m)^([A-Z][A-Z_]{2,}):")
_RE_TEN_PHIEN_BAN = re.compile(r"`([a-z]+_[a-z_]+)`")


# ── Dữ liệu ──────────────────────────────────────────────────────────────────────────────────────


@dataclass
class YeuCau:
    """Đầu vào của lệnh."""

    chu_de: str
    quoc_gia: str
    ngon_ngu: str
    kenh_mau: List[str] = field(default_factory=list)
    tu_khoa: List[str] = field(default_factory=list)
    ma_kenh: str = ""
    nhom: str = ""
    ten_kenh: str = ""
    doi_chu_de: bool = False
    thu: bool = False
    bo_nghien_cuu: bool = False
    lam_lai_ngach: bool = False

    def chuan(self) -> "YeuCau":
        self.chu_de = " ".join(str(self.chu_de or "").split())
        self.quoc_gia = str(self.quoc_gia or "").strip().upper()[:2]
        self.ngon_ngu = str(self.ngon_ngu or "").strip().lower().split("-")[0].split("_")[0]
        self.kenh_mau = [str(x).strip() for x in self.kenh_mau if str(x).strip()][:5]
        self.tu_khoa = [" ".join(str(x).split()) for x in self.tu_khoa if str(x).strip()][:10]
        self.ma_kenh = str(self.ma_kenh or "").strip()
        self.nhom = slug(self.nhom) if self.nhom else slug("{0}-{1}".format(self.chu_de, self.quoc_gia))
        return self


@dataclass
class KetQua:
    """Kết quả một lượt — đủ để in, ghi KHOI-TAO.md và để bài kiểm soi."""

    nhom: str = ""
    duong_ngach: str = ""
    ma_kenh: str = ""
    duong_kenh: str = ""
    thu: bool = False
    ngach_moi: bool = False
    loi_nhac_viet_lai: List[str] = field(default_factory=list)
    loi_nhac_giu_nguyen: List[str] = field(default_factory=list)
    tim_kiem: Dict[str, Any] = field(default_factory=dict)
    nghien_cuu: str = ""
    viec_cua_ban: List[str] = field(default_factory=list)
    tu_thu_lai: List[str] = field(default_factory=list)   # lỗi mà lượt tự chạy sẽ thử lại — chưa báo người
    khoa_loi: List[str] = field(default_factory=list)     # khoá lỗi tự thử lại xảy ra ở lượt này (xem `_viec_tu_thu_lai`)
    nhat_ky: List[str] = field(default_factory=list)


# ── Tiện ích ─────────────────────────────────────────────────────────────────────────────────────

#: Lỗi lượt tự chạy sẽ tự thử lại (hồ sơ ngách AI, viết lại lời nhắc, ảnh nhân vật, nghiên cứu khởi động): chỉ báo
#: NGƯỜI khi cùng lỗi vẫn còn sau ngần này ngày (04/10/2026: "mọi thứ auto 100%").
NGAY_BAO_NGUOI_LOI_TU_THU = 3


def _viec_tu_thu_lai(goc: str, kq: KetQua, khoa: str, cau: str) -> None:
    """Ghi nhớ ngày lỗi `khoa` xuất hiện đầu tiên (`workspace/khoi-tao-ngach/loi-tu-thu-lai.json`). Dưới
    `NGAY_BAO_NGUOI_LOI_TU_THU` ngày → `kq.tu_thu_lai` (máy tự thử lại, không báo người); đủ ngày vẫn hỏng →
    `kq.viec_cua_ban`."""
    key = "{0}|{1}".format(kq.ma_kenh or "?", khoa)
    kq.khoa_loi.append(key)
    hom = _dt.date.today()
    duong = os.path.join(goc, "workspace", "khoi-tao-ngach", "loi-tu-thu-lai.json")
    try:
        with io.open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
        du = du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        du = {}
    dau = None
    try:
        dau = _dt.date.fromisoformat(str(du.get(key) or ""))
    except ValueError:
        dau = None
    if dau is None:
        dau = hom
        du[key] = hom.isoformat()
        try:
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
                json.dump(du, tep, ensure_ascii=False, indent=1)
        except OSError:
            pass
    (kq.viec_cua_ban if (hom - dau).days >= NGAY_BAO_NGUOI_LOI_TU_THU else kq.tu_thu_lai).append(cau)


def _quen_loi_da_het(goc: str, kq: KetQua) -> None:
    """Lượt này không gặp lại lỗi nào của kênh → quên ngày bắt đầu của lỗi đó (lần sau tính lại từ đầu)."""
    if not kq.ma_kenh:
        return
    duong = os.path.join(goc, "workspace", "khoi-tao-ngach", "loi-tu-thu-lai.json")
    try:
        with io.open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
        moi = {k: v for k, v in du.items() if not k.startswith(kq.ma_kenh + "|") or k in kq.khoa_loi}
        if moi != du:
            with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
                json.dump(moi, tep, ensure_ascii=False, indent=1)
    except (OSError, ValueError, AttributeError):
        pass


def slug(chu: str, toi_da: int = 48) -> str:
    """"Nấu ăn tại gia VN" → "nau-an-tai-gia-vn" — ASCII, gạch nối, dùng làm tên nhóm/mã tệp/mã cụm."""
    chu = str(chu or "").replace("đ", "d").replace("Đ", "D")
    chu = unicodedata.normalize("NFKD", chu)
    chu = "".join(c for c in chu if not unicodedata.combining(c))
    chu = re.sub(r"[^A-Za-z0-9]+", "-", chu).strip("-").lower()
    return chu[:toi_da].strip("-")


def _mot_dong(chu: Any, toi_da: int = 2000) -> str:
    """Một dòng, không ký tự làm hỏng bộ đọc YAML tối giản (nháy kép, gạch ngược, xuống dòng)."""
    s = " ".join(str(chu or "").replace('"', "'").replace("\\", "/").split())
    return s[:toi_da]


def _ds_chuoi(gt: Any, toi_da: int = 40, dai: int = 200) -> List[str]:
    ra: List[str] = []
    if isinstance(gt, str):
        gt = [gt]
    for x in gt or []:
        if isinstance(x, (str, int, float)) and str(x).strip():
            s = " ".join(str(x).split())[:dai]
            if s not in ra:
                ra.append(s)
        if len(ra) >= toi_da:
            break
    return ra


def thong_tin_tieng(ma: str) -> Dict[str, Any]:
    return dict(BANG_TIENG.get(str(ma or "").lower(), _TIENG_MAC_DINH))


def _gio_vps(gio_thi_truong: str, quoc_gia: str, mui_gio: str = "",
             bay_gio: Optional[_dt.datetime] = None) -> str:
    """Giờ đăng gợi ý theo GIỜ THỊ TRƯỜNG → giờ của VPS (kenh.yaml `gio_dang` tính theo giờ máy)."""
    m = re.match(r"^\s*(\d{1,2}):(\d{2})", str(gio_thi_truong or ""))
    if not m:
        return ""
    h, p = int(m.group(1)) % 24, int(m.group(2)) % 60
    bay_gio = bay_gio or _dt.datetime.now()
    lech_tt: Optional[float] = None
    ten = mui_gio or MUI_GIO.get(quoc_gia, ("", 0))[0]
    if ten:
        try:
            from zoneinfo import ZoneInfo  # noqa: PLC0415

            lech_tt = bay_gio.astimezone(ZoneInfo(ten)).utcoffset().total_seconds() / 3600.0
        except Exception:  # noqa: BLE001 — máy thiếu dữ liệu múi giờ: bảng tĩnh
            lech_tt = None
    if lech_tt is None:
        lech_tt = float(MUI_GIO.get(quoc_gia, ("", 0))[1])
    lech_vps = (bay_gio.astimezone().utcoffset() or _dt.timedelta()).total_seconds() / 3600.0
    phut = int(round((h * 60 + p) + (lech_vps - lech_tt) * 60)) % (24 * 60)
    return "{0:02d}:{1:02d}".format(phut // 60, phut % 60)


def _doc(duong: str) -> str:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def _ghi(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)
    os.replace(tam, duong)


def _loc_json(chu: str) -> Any:
    from .goi_van_ban import loc_json  # noqa: PLC0415

    return loc_json(chu)


# ── Gọi AI (có nhớ đệm) ──────────────────────────────────────────────────────────────────────────


class BoGoiAI:
    """Bọc hàm gọi AI: nhớ đệm câu trả lời theo (mô hình, lời nhắc) dưới
    `CHANNEL/_NHOM/<nhóm>/khoi-tao/ai/` — chạy lại lệnh không trả tiền lần hai cho cùng một câu hỏi.

    `goi(loi_nhac, *, khoa, toi_da_token, mo_hinh) -> str`. `None` (chế độ `--thu`) → mọi lượt hỏi
    ném lỗi, nơi gọi phải tự dùng bản nháp."""

    def __init__(self, goi: Optional[Callable[..., str]], thu_muc: str, log: Callable[[str], None]):
        self.goi = goi
        self.thu_muc = thu_muc
        self.log = log
        self.so_luot = 0
        self.so_nho = 0

    def hoi(self, buoc: str, loi_nhac: str, *, toi_da_token: int = 8000, mo_hinh: str = MO_HINH) -> str:
        bam = hashlib.sha1((mo_hinh + "\n" + loi_nhac).encode("utf-8")).hexdigest()
        duong = os.path.join(self.thu_muc, "ai", "{0}-{1}.txt".format(slug(buoc, 30), bam[:16]))
        cu = _doc(duong)
        if cu.strip():
            self.so_nho += 1
            self.log("  ({0}: dùng lại câu trả lời AI đã lưu)".format(buoc))
            return cu
        if self.goi is None:
            raise RuntimeError("chế độ thử — không gọi AI")
        self.so_luot += 1
        tra = str(self.goi(loi_nhac, khoa="khoi-tao:{0}:{1}".format(slug(buoc, 30), bam[:12]),
                           toi_da_token=toi_da_token, mo_hinh=mo_hinh) or "")
        if tra.strip():
            _ghi(duong, tra)
        return tra


def goi_tu_client(client: Any, log: Callable[[str], None]) -> Callable[..., str]:
    """Hàm gọi AI thật qua ví ShopAPI (`goi_van_ban` — kiên nhẫn qua 503/khoá lệch)."""
    from .goi_van_ban import goi_van_ban, tin_nhan_viet  # noqa: PLC0415

    def goi(loi_nhac: str, *, khoa: str = "", toi_da_token: int = 8000, mo_hinh: str = MO_HINH) -> str:
        return goi_van_ban(client, tin_nhan_viet(loi_nhac), mo_hinh=mo_hinh,
                           toi_da_token=int(toi_da_token), khoa=khoa, on_log=log)

    return goi


# ── a) Hồ sơ ngách ───────────────────────────────────────────────────────────────────────────────

_NGUYEN_TAC = """NGUYÊN TẮC CHỌN CONTENT ĐÃ CHỨNG MINH (kênh thắng đầu tiên của tool):
- View = Hiển thị × CTR × Giữ chân. Chọn content quyết định ~80% thành công.
- Thứ tự chọn nguồn: bảng đề xuất của chính kênh → sổ đối thủ (video nổ ≥ 8× trung vị kênh nguồn, kênh nguồn
  phần lớn video thuần ngách) → ĐÀ TĂNG (view/ngày lúc chọn) quan trọng hơn tổng view → giống cái đã thắng
  trên kênh, giống cả CHỦ NGỮ (tệp người được nói tới).
- Tiêu đề: tách "vé vào cửa" (nhãn thể loại ai cũng dùng) khỏi "đòn bẩy" (thứ làm video nổ hơn mức nền).
- Mọi quyết định nội dung đọc NGHĨA bằng AI; danh sách từ khoá chỉ là đường lùi khi AI lỗi."""

DE_BAI_HO_SO = """Bạn là chuyên gia chiến lược kênh YouTube làm theo lối REMAKE (xem video đối thủ đã thắng rồi viết
lại kịch bản cho kênh mình). Hãy dựng HỒ SƠ NGÁCH cho một nhóm kênh MỚI:

- Chủ đề: {chu_de}
- Quốc gia/thị trường: {quoc_gia}
- Ngôn ngữ của kênh và của khán giả: {ten_tieng} (mã {ngon_ngu})
{them}
{nguyen_tac}

KHUNG HỒ SƠ (ý nghĩa từng khoá — đọc kỹ chú thích; phần ví dụ trong khung là một ngách KHÁC, đừng chép):
-----
{khung}
-----

VÍ DỤ ĐẦY ĐỦ của một ngách đang chạy thật (tâm lý học × Nhật) — chỉ để hiểu ĐỘ SÂU cần viết, KHÔNG chép nội dung:
-----
{vi_du}
-----

Yêu cầu:
1. Viết theo NGHĨA, cụ thể cho đúng chủ đề + thị trường trên: cái gì thuộc ngách, cái gì lệch, khán giả thật là ai.
2. 3–5 TỆP KHÁN GIẢ khác nhau rõ (mỗi kênh trong nhóm sẽ đánh một tệp). "ma" là mã ngắn ASCII viết thường có gạch
   nối, ví dụ "moi-tap-nau" (không dùng số trơn).
3. 4–10 CỤM chủ đề (mỗi cụm vài từ khoá ĐÚNG ngôn ngữ kênh; từ quá chung thì chấm nhầm).
4. Mọi danh sách từ khoá (tu_manh, tu_yeu, tu_loai_tru…) viết bằng {ten_tieng}, là đường lùi khi AI lỗi —
   gọn, chắc chắn, không chung chung. tu_loai_tru là thể loại KHÁC HẲN ngách (không remake được).
5. tu_khoa_tim: 8–12 cụm người xem {ten_tieng} thật sự gõ trên YouTube để tìm video của ngách (đa dạng góc).
6. tieu_chi_doi_thu: đúng 4 tiêu chí một kênh phải đạt để là đối thủ remake được (ngôn ngữ, nội dung chính,
   khán giả, dạng video).
7. luat_nan_khuon: đúng 2 câu dặn cách nắn một tiêu đề nguồn về KHUÔN tiêu đề đang thắng của kênh (hình dạng câu,
   cách mở, dấu câu/ngoặc quen dùng ở thị trường này) — không bịa số liệu.
8. thi_truong.gio_dang_goi_y: giờ đăng tốt nhất theo GIỜ ĐỊA PHƯƠNG thị trường (HH:MM). thi_truong.quy_mo: "nho",
   "vua" hoặc "lon" (cỡ thị trường YouTube của ngôn ngữ này cho ngách này).
9. bia_chuan_ngach: chuẩn ảnh bìa ƯỚC LƯỢNG theo hiểu biết về bìa thắng của ngách ở thị trường này (cùng cấu trúc
   ví dụ; màu chỉ dùng: trang, vang, do, den, cam, tim, xanh, xanh_dam, hong). Đặt so_bia_mau = 0 (chưa đo).
10. the_loai_en: thể loại bằng TIẾNG ANH, 1–3 từ (ví dụ "home cooking"), dùng trong lời nhắc ảnh bìa.
11. giong_van: một dòng TIẾNG ANH tả giọng đọc, dạng "<Language> — <tính chất>" (ví dụ
    "Vietnamese — warm, natural, conversational, like a friend explaining at home").
12. ten_kenh_goi_y: tên kênh gợi ý bằng {ten_tieng} (ngắn, dễ nhớ).

Trả về DUY NHẤT một JSON (không rào ```), đúng các khoá:
{{"mo_ta_ngach": "...", "dang_thang": "...", "mo_ta_cho_loc_ai": "...", "luat_chon": ["..."],
 "tieu_chi_doi_thu": ["...", "...", "...", "..."], "khan_gia_mo_ta": "...",
 "tep_khan_gia": [{{"ma": "...", "ten": "...", "ten_ngan": "..."}}],
 "cum": {{"ma-cum": {{"ten": "...", "tu": ["..."]}}}}, "ngach": {{"tu": ["..."], "tu_lac": ["..."]}},
 "tu_manh": ["..."], "tu_yeu": ["..."], "tu_loai_tru": ["..."], "ten_kenh_loai_tru": ["..."],
 "handle_loai_tru": ["..."], "tu_kenh_hien_nhien": ["..."], "handle_hien_nhien": ["..."],
 "tu_tieu_de_hien_nhien": ["..."], "tu_tuoi": ["..."], "tu_chan_dung": [], "tu_cach_lam": [],
 "mau_tieu_de": "kênh YouTube ... {ten_tieng}", "mo_ta_kenh_cho_ai": "...", "dang_thang_cho_ai": "...",
 "luat_kenh_nguon": {{"dung": "...", "gan": "...", "lac": "..."}}, "mo_ta_phan_cum": "{ten_tieng} (ngách ...)",
 "nhan_the_loai_mau": "", "vi_du_phan_cum": "...", "luat_nan_khuon": ["...", "..."], "the_loai_en": "...",
 "tu_khoa_tim": ["..."], "giong_van": "...", "ten_kenh_goi_y": "...",
 "thi_truong": {{"mui_gio": "...", "gio_dang_goi_y": "HH:MM", "quy_mo": "nho|vua|lon", "ctr_trang_chu_muc_tieu": 5.0}},
 "bia_chuan_ngach": {{"so_bia_mau": 0, "chu": {{...}}, "nen": {{...}}, "nhan_vat": {{...}}}}}}"""


def _cat_vi_du(chu: str, toi_da: int = 9000) -> str:
    """Bỏ các khối danh sách từ khoá dài (chỉ cần hiểu độ sâu phần NGHĨA), cắt theo trần ký tự."""
    if len(chu) <= toi_da:
        return chu
    return chu[:toi_da] + "\n# … (cắt bớt)\n"


def de_bai_ho_so(goc: str, yc: YeuCau, tieu_de_kenh_mau: Optional[Dict[str, List[str]]] = None) -> str:
    from .ho_so_ngach import ten_tieng  # noqa: PLC0415

    them: List[str] = []
    if yc.tu_khoa:
        them.append("- Từ khoá người dùng gợi ý: " + "; ".join(yc.tu_khoa))
    for link, tds in (tieu_de_kenh_mau or {}).items():
        them.append("- Kênh mẫu người dùng đưa ({0}), tiêu đề gần đây:\n  ".format(link)
                    + "\n  ".join("· " + t for t in tds[:15]))
    if yc.kenh_mau and not tieu_de_kenh_mau:
        them.append("- Kênh mẫu người dùng đưa: " + ", ".join(yc.kenh_mau))
    return DE_BAI_HO_SO.format(
        chu_de=yc.chu_de, quoc_gia=yc.quoc_gia, ngon_ngu=yc.ngon_ngu,
        ten_tieng=ten_tieng(yc.ngon_ngu) or yc.ngon_ngu, them="\n".join(them),
        nguyen_tac=_NGUYEN_TAC,
        khung=_cat_vi_du(_doc(os.path.join(duong_kenh(goc), TEP_KHUNG_NGACH)), 11000),
        vi_du=_cat_vi_du(_doc(os.path.join(duong_kenh(goc), TEP_VI_DU_NGACH)), 9000))


def ho_so_nhap(yc: YeuCau) -> Dict[str, Any]:
    """Bản NHÁP không cần AI (chế độ `--thu`, hoặc AI hỏng hẳn): khung tối thiểu theo chủ đề + thị
    trường — đủ để mã chạy đúng tiếng/thị trường, KHÔNG đủ để chọn nguồn tốt. Ghi chú rõ trong tệp."""
    from .ho_so_ngach import ten_tieng  # noqa: PLC0415

    tieng = ten_tieng(yc.ngon_ngu) or yc.ngon_ngu
    return {
        "mo_ta_ngach": "{0} — {1}, thị trường {2}".format(yc.chu_de, tieng, yc.quoc_gia),
        "dang_thang": "",
        "mo_ta_cho_loc_ai": "Thuộc ngách: video {0} nói {1}. Không thuộc ngách: thể loại khác chủ đề này, "
                            "Shorts, video tổng hợp/cắt clip/reup.".format(yc.chu_de, tieng),
        "luat_chon": ["Chỉ chọn video có trọng tâm là {0}; thể loại khác là lệch ngách.".format(yc.chu_de)],
        "tieu_chi_doi_thu": ["kênh nói {0}".format(tieng), "nội dung chính là {0}".format(yc.chu_de),
                             "hợp khán giả {0}".format(yc.quoc_gia),
                             "video dài có lời đọc (không Shorts, không reup)"],
        "tep_khan_gia": [{"ma": slug(yc.chu_de, 30) or "tep-chinh", "ten": "Khán giả chính của " + yc.chu_de,
                          "ten_ngan": "Chính"}],
        "cum": {}, "tu_khoa_tim": list(yc.tu_khoa) or [yc.chu_de],
        "mau_tieu_de": "kênh YouTube {0} {1}".format(yc.chu_de, tieng),
        "mo_ta_phan_cum": "{0} (ngách {1})".format(tieng, yc.chu_de),
        "the_loai_en": "", "luat_nan_khuon": [],
        "thi_truong": {}, "_nhap": True,
    }


def chuan_hoa_ho_so(du: Dict[str, Any], yc: YeuCau) -> Dict[str, Any]:
    """JSON của AI (hay bản nháp) → dict ghi được ra `ngach.yaml`: kiểm kiểu, chuẩn hoá mã, điền phần mã
    tự biết (bậc làm tròn view theo tiếng, múi giờ theo quốc gia), chặn rơi về bộ từ tiếng Nhật."""
    from .ho_so_ngach import MAU_TIEU_DE_GOC, ten_tieng  # noqa: PLC0415

    du = dict(du or {})
    tieng = ten_tieng(yc.ngon_ngu) or yc.ngon_ngu
    ra: Dict[str, Any] = {}
    ra["mo_ta_ngach"] = _mot_dong(du.get("mo_ta_ngach") or yc.chu_de, 600)
    ra["ngon_ngu_nguon"] = yc.ngon_ngu
    ra["dang_thang"] = _mot_dong(du.get("dang_thang"), 400)
    ra["mo_ta_cho_loc_ai"] = " ".join(str(du.get("mo_ta_cho_loc_ai") or "").split())[:1500]
    # Không bao giờ để trống: `bien_tap_content` lùi về khán giả MẶC ĐỊNH của mã (người Nhật 55+) khi khoá rỗng.
    ra["khan_gia_mo_ta"] = _mot_dong(du.get("khan_gia_mo_ta"), 300) or "khán giả {0} xem {1} ({2})".format(
        tieng, yc.chu_de, yc.quoc_gia)
    ra["luat_chon"] = _ds_chuoi(du.get("luat_chon"), 8, 400)
    ra["tieu_chi_doi_thu"] = _ds_chuoi(du.get("tieu_chi_doi_thu"), 6, 300)

    tep: List[Dict[str, str]] = []
    cam = {"1", "2", "3", "4", "7", "8"}       # mã số của năm tệp tâm lý Nhật trong mã — tránh đụng
    for d in du.get("tep_khan_gia") or []:
        if not isinstance(d, dict):
            continue
        ten = _mot_dong(d.get("ten"), 120)
        ngan = _mot_dong(d.get("ten_ngan"), 40) or ten[:30]
        ma = slug(str(d.get("ma") or ""), 40)
        if not ma or ma.isdigit() or ma in cam:
            ma = slug(ngan or ten, 40)
        if not ma or ma.isdigit():
            ma = "tep-{0}".format(len(tep) + 1)
        while ma in {t["ma"] for t in tep}:
            ma += "-2"
        tep.append({"ma": ma, "ten": ten or ma, "ten_ngan": ngan or ma})
        if len(tep) >= 6:
            break
    if not tep:
        tep = [{"ma": slug(yc.chu_de, 30) or "tep-chinh", "ten": "Khán giả chính", "ten_ngan": "Chính"}]
    ra["tep_khan_gia"] = tep

    cum: Dict[str, Dict[str, Any]] = {}
    for ma, c in (du.get("cum") or {}).items() if isinstance(du.get("cum"), dict) else []:
        if not isinstance(c, dict):
            continue
        tu = _ds_chuoi(c.get("tu"), 15, 60)
        k = slug(str(ma), 40)
        if k and tu:
            cum[k] = {"ten": _mot_dong(c.get("ten") or k, 80), "tu": tu}
    if cum:
        ra["cum"] = cum
    ng = du.get("ngach") if isinstance(du.get("ngach"), dict) else {}
    if ng.get("tu") or ng.get("tu_lac"):
        ra["ngach"] = {"tu": _ds_chuoi(ng.get("tu"), 20, 60), "tu_lac": _ds_chuoi(ng.get("tu_lac"), 20, 60)}
    for k in ("tu_manh", "tu_yeu", "tu_loai_tru", "ten_kenh_loai_tru", "handle_loai_tru",
              "tu_kenh_hien_nhien", "handle_hien_nhien", "tu_tieu_de_hien_nhien", "tu_tuoi",
              "tu_chan_dung", "tu_cach_lam"):
        ds = _ds_chuoi(du.get(k), 30, 60)
        if k in ("handle_loai_tru", "handle_hien_nhien"):
            ds = [x.lower() for x in ds]
        elif k in ("tu_loai_tru", "ten_kenh_loai_tru", "tu_kenh_hien_nhien", "tu_tieu_de_hien_nhien"):
            # Mã so khớp PHÂN BIỆT hoa/thường (viết cho chữ Nhật) — chữ La-tinh thêm dạng viết hoa đầu câu.
            hoa = [x[:1].upper() + x[1:] for x in ds if x[:1].isalpha() and x[:1].upper() != x[:1]]
            ds = ds + [x for x in hoa if x not in ds]
        if not ds and k in _KHOA_KHONG_DUOC_RONG:
            ds = [KHONG_KHOP]
        ra[k] = ds
    ra["chu_de_con_mac_dinh"] = False

    mau = _mot_dong(du.get("mau_tieu_de"), 160) or "kênh YouTube {0} {1}".format(yc.chu_de, tieng)
    if mau == MAU_TIEU_DE_GOC and not (yc.ngon_ngu == "ja" and "tâm lý" in yc.chu_de.lower()):
        mau = "kênh YouTube {0} {1}".format(yc.chu_de, tieng)
    ra["mau_tieu_de"] = mau
    ra["mo_ta_kenh_cho_ai"] = _mot_dong(du.get("mo_ta_kenh_cho_ai"), 400)
    ra["dang_thang_cho_ai"] = _mot_dong(du.get("dang_thang_cho_ai"), 300)
    lk = du.get("luat_kenh_nguon") if isinstance(du.get("luat_kenh_nguon"), dict) else {}
    lk = {k: _mot_dong(lk.get(k), 400) for k in ("dung", "gan", "lac") if str(lk.get(k) or "").strip()}
    if lk:
        ra["luat_kenh_nguon"] = lk
    ra["mo_ta_phan_cum"] = _mot_dong(du.get("mo_ta_phan_cum"), 120) or "{0} (ngách {1})".format(tieng, yc.chu_de)
    ra["nhan_the_loai_mau"] = _mot_dong(du.get("nhan_the_loai_mau"), 120)
    ra["vi_du_phan_cum"] = _mot_dong(du.get("vi_du_phan_cum"), 300)
    ra["luat_nan_khuon"] = _ds_chuoi(du.get("luat_nan_khuon"), 2, 400)
    ra["the_loai_en"] = _mot_dong(du.get("the_loai_en"), 40)
    ra["tu_khoa_tim"] = _ds_chuoi(list(du.get("tu_khoa_tim") or []) + list(yc.tu_khoa), 14, 80)
    # Kênh thứ 2+ của nhóm DÙNG LẠI hồ sơ (không hỏi AI lại) — giữ giọng văn + tên gợi ý trong tệp để kênh sau
    # không rơi về câu tiếng Việt "<chủ đề> — <QG>" làm tên kênh.
    if str(du.get("giong_van") or "").strip():
        ra["giong_van"] = _mot_dong(du.get("giong_van"), 200)
    if str(du.get("ten_kenh_goi_y") or "").strip():
        ra["ten_kenh_goi_y"] = _mot_dong(du.get("ten_kenh_goi_y"), 80)
    ra["ctr_trang_chu_thang"] = "~5–6% (ước, chưa đo trên kênh)"
    ra["ctr_trang_chu_truot"] = "~3–4% (ước, chưa đo trên kênh)"

    tt_ai = du.get("thi_truong") if isinstance(du.get("thi_truong"), dict) else {}
    mg = str(tt_ai.get("mui_gio") or "").strip()
    if not re.match(r"^[A-Za-z]+/[A-Za-z_+\-]+", mg):
        mg = MUI_GIO.get(yc.quoc_gia, ("", 0))[0]
    thi_truong: Dict[str, Any] = {"quoc_gia": yc.quoc_gia, "ngon_ngu": yc.ngon_ngu}
    if mg:
        thi_truong["mui_gio"] = mg
    gio = str(tt_ai.get("gio_dang_goi_y") or "").strip()
    if re.match(r"^\d{1,2}:\d{2}$", gio):
        thi_truong["gio_dang_goi_y"] = gio
    thi_truong["bac_lam_tron_view"] = thong_tin_tieng(yc.ngon_ngu)["bac"]
    try:
        ctr = float(tt_ai.get("ctr_trang_chu_muc_tieu") or 5.0)
        thi_truong["ctr_trang_chu_muc_tieu"] = round(max(2.0, min(12.0, ctr)), 1)
    except (TypeError, ValueError):
        thi_truong["ctr_trang_chu_muc_tieu"] = 5.0
    quy_mo = str(tt_ai.get("quy_mo") or "").strip().lower()
    if quy_mo in ("nho", "vua"):
        thi_truong["bac_view_manh"] = 30000 if quy_mo == "nho" else 60000
    ra["thi_truong"] = thi_truong

    bia = du.get("bia_chuan_ngach")
    if isinstance(bia, dict) and isinstance(bia.get("chu"), dict):
        bia = json.loads(json.dumps(bia, ensure_ascii=False))
        bia["so_bia_mau"] = 0
        ra["bia_chuan_ngach"] = bia
    if du.get("_nhap"):
        ra["_nhap"] = True
    return ra


def _yaml_ngach(du: Dict[str, Any], yc: YeuCau, *, nhap: bool) -> str:
    import yaml  # noqa: PLC0415

    du = {k: v for k, v in du.items() if not k.startswith("_")}
    dau = (
        "# ============================================================================\n"
        "# Hồ sơ ngách — nhóm \"{nhom}\" ({chu_de} · {qg} · {nn})\n"
        "# ============================================================================\n"
        "# Sinh bởi `python -m core.khoi_tao_ngach` ngày {ngay}{nhap}.\n"
        "# Khung + ý nghĩa từng khoá: CHANNEL/_KHUON/ngach-mau.yaml. Sửa tay thoải mái — chạy lại lệnh\n"
        "# KHÔNG ghi đè tệp này (trừ khi thêm --lam-lai-ngach). Từ khoá chỉ là ĐƯỜNG LÙI khi AI lỗi;\n"
        "# chọn/lọc content theo NGHĨA do AI đọc mo_ta_ngach + mo_ta_cho_loc_ai + luat_chon.\n"
        "# \"{khong}\" trong một bộ từ = cố ý KHÔNG có từ nào (không rơi về bộ từ tiếng Nhật mặc định).\n"
        "# bia_chuan_ngach là ƯỚC LƯỢNG (so_bia_mau: 0) — vòng học bìa tự đo lại trên bìa thật.\n"
        "# ============================================================================\n\n"
    ).format(nhom=yc.nhom, chu_de=yc.chu_de, qg=yc.quoc_gia, nn=yc.ngon_ngu,
             ngay=_dt.date.today().isoformat(), khong=KHONG_KHOP,
             nhap=" — BẢN NHÁP KHÔNG CÓ AI (chế độ thử): chạy lại không --thu để AI viết bản thật"
             if nhap else "")
    return dau + yaml.safe_dump(du, allow_unicode=True, sort_keys=False, width=110,
                                default_flow_style=False)


def buoc_ho_so(goc: str, yc: YeuCau, ai: BoGoiAI, kq: KetQua, log: Callable[[str], None], *,
               lay_kenh: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """a) Viết (hoặc dùng lại) `CHANNEL/_NHOM/<nhóm>/ngach.yaml`. Trả hồ sơ thô (dict)."""
    from .ho_so_ngach import doc_ngach_tho, duong_ngach_yaml  # noqa: PLC0415

    duong = duong_ngach_yaml(goc, yc.nhom)
    kq.duong_ngach = duong
    cu = doc_ngach_tho(goc, yc.nhom)
    if cu and not yc.lam_lai_ngach and not (cu.get("ban_nhap") and not yc.thu):
        log("a) Hồ sơ ngách đã có: {0} — dùng lại (thêm --lam-lai-ngach để AI viết lại).".format(duong))
        return cu
    kq.ngach_moi = True
    tieu_de_mau: Dict[str, List[str]] = {}
    if yc.kenh_mau and not yc.thu:
        lay = lay_kenh or _lay_kenh_mac_dinh
        for link in yc.kenh_mau[:3]:
            try:
                ch = lay(link, lang=yc.ngon_ngu)
                tds = [v.title for v in (getattr(ch, "videos", None) or []) if getattr(v, "title", "")][:15]
                if tds:
                    tieu_de_mau[link] = tds
            except Exception as loi:  # noqa: BLE001 — kênh mẫu đọc hỏng: đi tiếp không có tiêu đề
                log("  (không đọc được kênh mẫu {0}: {1})".format(link, str(loi)[:100]))
    du: Optional[Dict[str, Any]] = None
    if not yc.thu:
        log("a) AI viết hồ sơ ngách cho “{0}” ({1}, {2})…".format(yc.chu_de, yc.quoc_gia, yc.ngon_ngu))
        for lan in range(2):
            try:
                tra = ai.hoi("ho-so-ngach" + ("" if lan == 0 else "-lan2"),
                             de_bai_ho_so(goc, yc, tieu_de_mau) +
                             ("" if lan == 0 else "\n\n(Lần trước JSON hỏng — chỉ trả JSON hợp lệ.)"),
                             toi_da_token=12000)
                tho = _loc_json(tra)
                if isinstance(tho, dict) and tho.get("mo_ta_ngach") and tho.get("tep_khan_gia"):
                    du = tho
                    break
                log("  AI trả hồ sơ thiếu khoá chính — hỏi lại.")
            except Exception as loi:  # noqa: BLE001
                log("  AI viết hồ sơ hỏng: {0}".format(str(loi)[:160]))
        if du is None:
            _viec_tu_thu_lai(goc, kq, "ho_so_ngach", "AI chưa viết được hồ sơ ngách — tool dùng BẢN NHÁP. Chạy lại lệnh khi "
                             "ví/mạng ổn (kèm --lam-lai-ngach), hoặc sửa tay {0}.".format(duong))
    else:
        log("a) [THỬ] Hồ sơ ngách: bản nháp từ khuôn (không gọi AI).")
    nhap = du is None
    hs = chuan_hoa_ho_so(du if du is not None else ho_so_nhap(yc), yc)
    if nhap:
        # Bản nháp được đánh dấu: lần chạy thật kế tiếp tự để AI viết lại (không "dùng lại" bản nháp).
        hs["ban_nhap"] = True
    hs["_giong_van"] = _mot_dong((du or {}).get("giong_van"), 200)
    hs["_ten_kenh"] = _mot_dong((du or {}).get("ten_kenh_goi_y"), 80)
    if yc.thu:
        log("  [THỬ] sẽ ghi {0} ({1} tệp khán giả, {2} cụm tìm kiếm) — chế độ thử không ghi.".format(
            duong, len(hs.get("tep_khan_gia") or []), len(hs.get("tu_khoa_tim") or [])))
        return hs
    _ghi(duong, _yaml_ngach(hs, yc, nhap=nhap))
    log("  đã ghi {0} ({1} tệp khán giả, {2} cụm, {3} cụm tìm kiếm).".format(
        duong, len(hs.get("tep_khan_gia") or []), len(hs.get("cum") or {}), len(hs.get("tu_khoa_tim") or [])))
    return hs


def _lay_kenh_mac_dinh(link: str, lang: str = "") -> Any:
    from . import youtube  # noqa: PLC0415

    return youtube.fetch_channel(link, max_videos=20, lang=lang, source="kênh mẫu")


# ── b) Kênh ──────────────────────────────────────────────────────────────────────────────────────


def chon_ma_kenh(goc: str, yc: YeuCau) -> str:
    """Mã kênh: `--ma-kenh` nếu có; không thì thư mục trình duyệt `<MÃ>\\<MÃ>.exe` cạnh MyTool chưa thành
    kênh; không có nữa thì K1, K2… đầu tiên còn trống."""
    if yc.ma_kenh:
        return yc.ma_kenh
    cha = os.path.dirname(os.path.abspath(goc))
    try:
        ten = sorted(os.listdir(cha))
    except OSError:
        ten = []
    for t in ten:
        if t.startswith((".", "_")) or not os.path.isfile(os.path.join(cha, t, t + ".exe")):
            continue
        if not os.path.exists(duong_kenh(goc, t)):
            return t
    i = 1
    while os.path.exists(duong_kenh(goc, "K{0}".format(i))):
        i += 1
    return "K{0}".format(i)


def _kenh_cung_nhom(goc: str, nhom: str, tru: str = "") -> List[Dict[str, Any]]:
    """kenh.yaml (thô) của các kênh khác đã thuộc nhóm `nhom` (bỏ `tru`, bỏ thư mục `_…`)."""
    ra: List[Dict[str, Any]] = []
    try:
        ten = sorted(os.listdir(duong_kenh(goc)))
    except OSError:
        return ra
    for t in ten:
        if t.startswith(("_", ".")) or t == tru:
            continue
        y = doc_yaml(os.path.join(duong_kenh(goc, t), TEP_KENH)) or {}
        if str(y.get("nhom") or "").strip() == nhom:
            ra.append(y)
    return ra


def chon_tep(goc: str, nhom: str, hs: Dict[str, Any], ma: str) -> Dict[str, Any]:
    """Tệp khán giả cho kênh `ma`: tệp ĐẦU TIÊN của hồ sơ chưa kênh nào trong nhóm đánh (mỗi kênh một tệp —
    `DE_BAI_HO_SO` mục 2); hết tệp trống thì tệp đầu."""
    ds = [t for t in (hs.get("tep_khan_gia") or []) if isinstance(t, dict) and t.get("ma")]
    if not ds:
        return {}
    da_dung = {str(y.get("tep") or "").strip() for y in _kenh_cung_nhom(goc, nhom, tru=ma)}
    return next((t for t in ds if str(t["ma"]) not in da_dung), ds[0])


def kiem_loi_nhac(cu: str, moi: str) -> str:
    """"" nếu bản viết lại giữ đủ phần MÁY đọc của bản cũ (chỗ điền `<<…>>`, khoá JSON đầu ra, nhãn
    dòng, tên phiên bản trong ``), ngược lại là câu nói thiếu gì. Bản viết lại hỏng thì giữ bản cũ."""
    if not str(moi or "").strip():
        return "rỗng"
    thieu = sorted(set(_RE_CHO_DIEN.findall(cu)) - set(_RE_CHO_DIEN.findall(moi)))
    if thieu:
        return "mất chỗ điền " + ", ".join(thieu)
    for ten, rx in (("khoá JSON", _RE_KHOA_JSON), ("nhãn dòng", _RE_NHAN_DONG),
                    ("tên phiên bản", _RE_TEN_PHIEN_BAN)):
        mat = sorted(set(rx.findall(cu)) - set(rx.findall(moi)))
        if mat:
            return "mất {0} {1}".format(ten, ", ".join(mat[:5]))
    if len(moi) < 0.35 * len(cu):
        return "ngắn bất thường ({0}/{1} ký tự)".format(len(moi), len(cu))
    return ""


DE_BAI_VIET_LAI = """Bạn viết LỜI NHẮC (prompt) cho dây chuyền làm video YouTube tự động. Dưới đây là một lời nhắc đang
chạy thật ở kênh ngách TÂM LÝ HỌC × NHẬT BẢN. Hãy VIẾT LẠI nó cho kênh mới:

- Ngách mới: {mo_ta_ngach}
- Thị trường: {quoc_gia}; khán giả: {khan_gia}; ngôn ngữ video: {ten_tieng}
- Tệp khán giả của nhóm: {tep}

Nguyên tắc (con đường kênh thắng):
1. Giữ MỤC TIÊU và cơ chế của lời nhắc gốc (nó đã chứng minh). Lời nhắc NGẮN, nêu mục tiêu cụ thể — không nhồi
   luật mới; sức mạnh nằm ở bước chấm.
2. KHÔNG dịch máy móc: thay mọi chỗ mang ngách/văn hoá cũ (tâm lý, Nhật Bản, chữ/nhãn tiếng Nhật, khán giả lớn
   tuổi xem TV, ví dụ, ẩn dụ) bằng thứ ĐÚNG với ngách + khán giả mới. Nhãn khối cố định viết bằng {ten_tieng}.
3. GIỮ NGUYÊN từng ký tự mọi chỗ điền dạng <<TEN>>, mọi khoá JSON và tên phiên bản đầu ra, mọi nhãn dòng
   (VD "DESCRIPTION:"), và định dạng trả về — máy đọc chúng.
4. Giữ ngôn ngữ viết của chính lời nhắc gốc (gốc viết tiếng Việt thì viết tiếng Việt, gốc viết tiếng Anh thì tiếng
   Anh). Ngôn ngữ của NỘI DUNG đầu ra do chỗ điền <<NGON_NGU>>/<<LANGUAGE>> quyết.

Trả về DUY NHẤT nội dung lời nhắc mới, không giải thích, không rào ```.

=== LỜI NHẮC GỐC ({ten_tep}) ===
{noi_dung}"""

DE_BAI_STYLE = """Một kênh YouTube hoạt hình phẳng (flat vector) đổi sang ngách mới. Viết lại 8 khoá phong cách theo ngách +
thị trường mới, giữ nguyên nét vẽ và nhân vật tham chiếu (hình người tròn trắng, viền đen dày, không mô tả thêm
chi tiết cơ thể).

- Ngách mới: {mo_ta_ngach}
- Thị trường: {quoc_gia}; khán giả: {khan_gia}; ngôn ngữ: {ten_tieng_anh}

Bản đang dùng (ngách tâm lý × Nhật — chỉ để hiểu ĐỘ CỤ THỂ cần viết, KHÔNG chép văn hoá Nhật):
{style_cu}

Yêu cầu: TIẾNG ANH, mỗi khoá MỘT dòng, không dùng dấu nháy kép, không xuống dòng. cultural_metaphors giữ dạng
"cảm xúc: cảnh | cảm xúc: cảnh" (10–13 mục). Bối cảnh, đồ vật, ẩn dụ là đời thường của khán giả {quoc_gia}.
Trả về DUY NHẤT một JSON với đúng các khoá: {khoa}"""


def _viet_lai_loi_nhac(ai: BoGoiAI, ten_tep: str, noi_dung: str, hs: Dict[str, Any], yc: YeuCau) -> str:
    from .ho_so_ngach import ten_tieng  # noqa: PLC0415

    return ai.hoi("loi-nhac-" + ten_tep, DE_BAI_VIET_LAI.format(
        mo_ta_ngach=hs.get("mo_ta_ngach") or yc.chu_de, quoc_gia=yc.quoc_gia,
        khan_gia=hs.get("khan_gia_mo_ta") or "(chưa rõ)", ten_tieng=ten_tieng(yc.ngon_ngu) or yc.ngon_ngu,
        tep="; ".join(t.get("ten", "") for t in hs.get("tep_khan_gia") or []),
        ten_tep=ten_tep, noi_dung=noi_dung), toi_da_token=8000).strip()


def _style_moi(ai: Optional[BoGoiAI], style_cu: Dict[str, Any], hs: Dict[str, Any], yc: YeuCau,
               log: Callable[[str], None]) -> Dict[str, str]:
    from .ho_so_ngach import ten_tieng  # noqa: PLC0415

    ten_anh = ten_tieng(yc.ngon_ngu, anh=True) or yc.ngon_ngu
    if ai is not None and not yc.thu:
        try:
            tra = ai.hoi("style", DE_BAI_STYLE.format(
                mo_ta_ngach=hs.get("mo_ta_ngach") or yc.chu_de, quoc_gia=yc.quoc_gia,
                khan_gia=hs.get("khan_gia_mo_ta") or "(chưa rõ)", ten_tieng_anh=ten_anh,
                style_cu="\n".join("{0}: {1}".format(k, style_cu.get(k, "")) for k in KHOA_STYLE_VIET_LAI),
                khoa=", ".join(KHOA_STYLE_VIET_LAI)), toi_da_token=6000)
            du = _loc_json(tra)
            if isinstance(du, dict):
                ra = {k: _mot_dong(du.get(k), 3000) for k in KHOA_STYLE_VIET_LAI if str(du.get(k) or "").strip()}
                if len(ra) >= 6:
                    ra["audience_language"] = ra.get("audience_language") or ten_anh
                    return ra
            log("  AI viết style thiếu khoá — dùng bản trung tính.")
        except Exception as loi:  # noqa: BLE001
            log("  AI viết style hỏng ({0}) — dùng bản trung tính.".format(str(loi)[:120]))
    the_loai = hs.get("the_loai_en") or "YouTube"
    return {
        "audience_language": ten_anh,
        "audience_culture_note": "Design for {0} viewers in {1} who watch {2} videos. Use concrete everyday "
                                 "settings, props and seasons familiar to this audience.".format(
                                     ten_anh, yc.quoc_gia, the_loai),
        "cultural_props": "everyday objects familiar to {0} viewers in {1}".format(ten_anh, yc.quoc_gia),
        "cultural_metaphors": "joy: warm light through a window | worry: clouds over a familiar street | "
                              "relief: a deep breath on a quiet balcony | pride: a finished result on the table",
        "cultural_emotion_style": "Show emotion through posture and concrete everyday moments of {0} viewers; "
                                  "keep it warm and grounded.".format(ten_anh),
        "thumbnail_style": _mot_dong(str(style_cu.get("thumbnail_style") or "").replace("psychology", the_loai)),
        "scene_plan_style": _mot_dong(str(style_cu.get("scene_plan_style") or "").replace(
            "Japanese", "{0}".format(yc.quoc_gia))),
        "default_character_prompt": _mot_dong(str(style_cu.get("default_character_prompt") or "").replace(
            "psychology", the_loai)),
    }


def _dat_khoa(chu: str, khoa: str, gia_tri: Any) -> str:
    from .dong_bo_kenh import dat_khoa_yaml  # noqa: PLC0415

    if isinstance(gia_tri, bool):
        return dat_khoa_yaml(chu, khoa, "true" if gia_tri else "false")
    if isinstance(gia_tri, (int, float)):
        return dat_khoa_yaml(chu, khoa, str(gia_tri))
    return dat_khoa_yaml(chu, khoa, _mot_dong(gia_tri), nhay=True)


def _tao_anh_nv(client: Any, prompt: str, dich: str, khoa: str) -> str:
    """MỘT ảnh nhân vật tham chiếu (100₫) qua `images.create_and_wait` (SDK tự giãn nhịp hỏi theo
    `estimated_seconds`), tải về bằng `/v1/jobs/{id}/download`. Trả đường tệp."""
    job = client.images.create_and_wait(prompt=prompt, n=1, aspect_ratio="16:9", idempotency_key=khoa,
                                        timeout=900)
    ma = str((job or {}).get("id") or (job or {}).get("job_id") or "")
    if not ma:
        raise RuntimeError("máy chủ không trả mã job ảnh")
    goc_url = str(getattr(client, "base_url", "") or "https://api.shopapi.vn").rstrip("/")
    dau = client._build_headers(accept="*/*")  # noqa: SLF001
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    tam = dich + ".tam"
    with client._http.stream("GET", "{0}/v1/jobs/{1}/download".format(goc_url, ma), headers=dau) as ph:  # noqa: SLF001
        if ph.status_code >= 400:
            ph.read()
            raise RuntimeError("tải ảnh nhân vật hỏng ({0})".format(ph.status_code))
        with open(tam, "wb") as tep:
            for khuc in ph.iter_bytes(1 << 16):
                tep.write(khuc)
    if os.path.getsize(tam) < 1000:
        os.remove(tam)
        raise RuntimeError("ảnh nhân vật tải về rỗng")
    os.replace(tam, dich)
    return dich


def buoc_kenh(goc: str, yc: YeuCau, hs: Dict[str, Any], ai: BoGoiAI, kq: KetQua,
              log: Callable[[str], None], *, tao_anh: Optional[Callable[[str, str], str]] = None) -> str:
    """b) Dựng `CHANNEL/<MÃ>/` từ khuôn `CHANNEL/_KHUON/kenh-mau/` (hoặc đổi chủ đề kênh có sẵn)."""
    from .ho_so_ngach import ten_tieng  # noqa: PLC0415

    ma = chon_ma_kenh(goc, yc)
    kq.ma_kenh = ma
    mau = os.path.join(duong_kenh(goc), THU_MUC_KENH_MAU)
    if not os.path.isfile(os.path.join(mau, TEP_KENH)):
        raise RuntimeError("Thiếu khuôn kênh {0} — cập nhật tool (kho có sẵn thư mục này).".format(mau))
    dich = duong_kenh(goc, ma)
    kq.duong_kenh = dich
    co_san = os.path.isfile(os.path.join(dich, TEP_KENH))
    if co_san and not yc.doi_chu_de:
        raise RuntimeError("Đã có kênh {0}. Muốn đổi chủ đề kênh này thì thêm --doi-chu-de; muốn kênh mới thì "
                           "đặt --ma-kenh khác.".format(ma))
    if not co_san:
        from .kenh import kiem_ma_kenh_moi  # noqa: PLC0415

        loi = kiem_ma_kenh_moi(goc, ma)
        if loi:
            raise RuntimeError(loi)

    tep = chon_tep(goc, yc.nhom, hs, ma)
    tt = hs.get("thi_truong") or {}
    tieng = thong_tin_tieng(yc.ngon_ngu)
    ten_anh = ten_tieng(yc.ngon_ngu, anh=True) or yc.ngon_ngu
    giong = (hs.get("_giong_van") or hs.get("giong_van")
             or "{0} — natural, warm, conversational, clear for listening".format(ten_anh))
    # Tên gợi ý của hồ sơ chỉ cho kênh ĐẦU của nhóm; kênh sau ghép thêm tên ngắn của tệp (tên thật trên Studio do
    # bước thiết lập kênh viết lại sau — đây chỉ là tên làm việc).
    goi_y = hs.get("_ten_kenh") or hs.get("ten_kenh_goi_y") or ""
    if goi_y and any(str(y.get("ten") or "").strip() == goi_y for y in _kenh_cung_nhom(goc, yc.nhom, tru=ma)):
        goi_y = "{0} · {1}".format(goi_y, tep.get("ten_ngan") or tep.get("ma") or ma)
    gio = _gio_vps(tt.get("gio_dang_goi_y") or "", yc.quoc_gia, tt.get("mui_gio") or "")
    khoa_kenh: Dict[str, Any] = {
        "ma": ma, "ten": yc.ten_kenh or goi_y or "{0} — {1}".format(yc.chu_de, yc.quoc_gia),
        "nhom": yc.nhom, "tep": tep.get("ma") or "", "ngon_ngu": yc.ngon_ngu, "giong_van": giong,
        # Nước của kênh: hồ sơ Studio (quốc gia cư trú) + địa điểm xem youtube.com (skill K06) đọc khoá này —
        # không suy từ tiếng (en ≠ luôn US, es ≠ luôn ES).
        "quoc_gia": yc.quoc_gia, "dia_diem_xem": yc.quoc_gia,
        "ky_tu_moi_phut": int(tieng["ky_tu"]), "chu_bia_hoa": bool(tieng["hoa"]),
        "ngay_bat_dau": _dt.date.today().isoformat(), "chien_luoc": "tu_dong", "de_bai_bien_tap": "gon",
        "kenh_rieng": True,
    }
    if gio:
        khoa_kenh["gio_dang"] = gio
    if not co_san:
        # Kênh mới: tự thiết lập trên Studio (tên, handle, mô tả, logo, banner, SEO…) — máy mới chỉ cần Chrome đã đăng nhập.
        khoa_kenh["thiet_lap_kenh"] = True
    if yc.thu:
        log("b) [THỬ] Sẽ {0} kênh {1} ({2}) ở {3}: nhóm {4}, tệp {5}, giờ đăng {6} (giờ VPS).".format(
            "đổi chủ đề" if co_san else "tạo", ma, khoa_kenh["ten"], dich, yc.nhom, khoa_kenh["tep"],
            gio or "20:00"))

    # ── dựng ở chỗ tạm (kênh mới) hoặc sao lưu rồi sửa tại chỗ (đổi chủ đề). Chế độ thử: không ghi gì ──
    if co_san:
        chu_kenh = _doc(os.path.join(dich, TEP_KENH))
        lam = dich
        if not yc.thu:
            luu = os.path.join(dich, "khoi-tao-cu", time.strftime("%Y%m%d-%H%M%S"))
            os.makedirs(luu, exist_ok=True)
            for ten in (TEP_KENH, TEP_STYLE, THU_MUC_PROMPT):
                p = os.path.join(dich, ten)
                if os.path.isdir(p):
                    shutil.copytree(p, os.path.join(luu, ten))
                elif os.path.isfile(p):
                    shutil.copy2(p, os.path.join(luu, ten))
            # Nghiên cứu của ngách CŨ (đối thủ, content, tuyến, V7) không dùng cho ngách mới — DỜI đi, không xoá.
            if os.path.isdir(os.path.join(dich, "nghien-cuu")):
                shutil.move(os.path.join(dich, "nghien-cuu"), os.path.join(luu, "nghien-cuu"))
            log("  đổi chủ đề: bản cũ (kenh.yaml, style.yaml, prompt/, nghien-cuu/) cất ở {0}".format(luu))
    else:
        chu_kenh = _doc(os.path.join(mau, TEP_KENH))
        lam = duong_kenh(goc, "_tao-" + ma)
        if not yc.thu:
            if os.path.exists(lam):
                shutil.rmtree(lam, ignore_errors=True)
            os.makedirs(os.path.join(lam, THU_MUC_PROMPT))

    try:
        for k, v in khoa_kenh.items():
            chu_kenh = _dat_khoa(chu_kenh, k, v)
        if not co_san:
            chu_kenh = ("# KÊNH {0} — dựng bởi `python -m core.khoi_tao_ngach` ngày {1} ({2} · {3} · {4}).\n"
                        "# Công tắc tiền/tự động đang TẮT — xem KHOI-TAO.md cạnh tệp này.\n").format(
                            ma, _dt.date.today().isoformat(), yc.chu_de, yc.quoc_gia, yc.ngon_ngu) + chu_kenh
        if not yc.thu:
            _ghi(os.path.join(lam, TEP_KENH), chu_kenh)

        # style.yaml: khuôn + 8 khoá viết lại
        chu_style = _doc(os.path.join(mau, TEP_STYLE))
        style_cu = doc_yaml(os.path.join(mau, TEP_STYLE)) or {}
        moi = _style_moi(None if yc.thu else ai, style_cu, hs, yc, log)
        for k, v in moi.items():
            chu_style = _dat_khoa(chu_style, k, v)
        if not yc.thu:
            _ghi(os.path.join(lam, TEP_STYLE), chu_style)
        else:
            log("  [THỬ] style.yaml: viết lại {0} khoá văn hoá/bìa theo ngách.".format(len(KHOA_STYLE_VIET_LAI)))

        # prompt/: chép nguyên văn, viết lại những tệp còn mang ngách cũ
        thu_prompt = os.path.join(mau, THU_MUC_PROMPT)
        for ten in sorted(os.listdir(thu_prompt)):
            if not ten.endswith(".md"):
                continue
            cu = _doc(os.path.join(thu_prompt, ten))
            noi = cu
            if ten in CAN_VIET_LAI:
                if yc.thu:
                    log("  [THỬ] prompt/{0}: AI sẽ viết lại theo ngách (giữ chỗ điền + định dạng).".format(ten))
                    kq.loi_nhac_viet_lai.append(ten)
                    continue
                else:
                    try:
                        moi_chu = _viet_lai_loi_nhac(ai, ten, cu, hs, yc)
                        loi = kiem_loi_nhac(cu, moi_chu)
                        if loi:
                            log("  prompt/{0}: bản viết lại hỏng ({1}) — giữ bản khuôn.".format(ten, loi))
                            _viec_tu_thu_lai(goc, kq, "prompt:" + ten, "Xem lại prompt/{0} của kênh {1}: AI viết lại "
                                             "hỏng ({2}), đang dùng bản khuôn ngách cũ.".format(ten, ma, loi))
                        else:
                            noi = moi_chu.rstrip() + "\n"
                    except Exception as loi_ai:  # noqa: BLE001
                        log("  prompt/{0}: AI hỏng ({1}) — giữ bản khuôn.".format(ten, str(loi_ai)[:100]))
                        _viec_tu_thu_lai(goc, kq, "prompt:" + ten, "Xem lại prompt/{0} của kênh {1}: AI chưa viết "
                                         "lại được.".format(ten, ma))
                (kq.loi_nhac_viet_lai if noi is not cu else kq.loi_nhac_giu_nguyen).append(ten)
            else:
                kq.loi_nhac_giu_nguyen.append(ten)
            if not yc.thu:
                _ghi(os.path.join(lam, THU_MUC_PROMPT, ten), noi)

        if not yc.thu and not co_san:
            os.rename(lam, dich)
    except Exception:
        if not co_san and not yc.thu:
            shutil.rmtree(lam, ignore_errors=True)
        raise

    if yc.thu:
        return dich

    # ── ảnh nhân vật tham chiếu ──
    nv = os.path.join(dich, "nv", "nv1.png")
    if not os.path.isfile(nv):
        st = doc_yaml(os.path.join(dich, TEP_STYLE)) or {}
        prompt_nv = "{0}. {1}. Plain light background, full body, centered, no text, no watermark.".format(
            st.get("default_character_prompt") or "", st.get("default_character_lock") or "")
        if tao_anh is not None:
            try:
                tao_anh(prompt_nv, nv)
                log("  đã tạo ảnh nhân vật tham chiếu nv/nv1.png")
            except Exception as loi:  # noqa: BLE001
                log("  tạo ảnh nhân vật hỏng: {0}".format(str(loi)[:150]))
        if not os.path.isfile(nv):
            _viec_tu_thu_lai(goc, kq, "anh_nhan_vat", "Bỏ một ảnh nhân vật (.png) vào CHANNEL/{0}/nv/nv1.png — mỗi "
                             "cảnh dùng nó làm tham chiếu (gợi ý lời tả: style.yaml `default_character_prompt`).".format(ma))

    # ── sổ tuyến + Công thức V7 (giai đoạn "moi" → tự chuyển V7 khi có video thắng thật) ──
    try:
        from . import tuyen_noi_dung as tn  # noqa: PLC0415

        tn.gieo_cho_kenh(goc, ma, ma, khoa_kenh["tep"])
    except Exception as loi:  # noqa: BLE001
        log("  gieo sổ tuyến hỏng: {0}".format(str(loi)[:120]))
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415
        from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

        ch = v7.cau_hinh_cho_tep(v7._cau_hinh_mac_dinh_cho_kenh(goc, ma), khoa_kenh["tep"])  # noqa: SLF001
        _ghi(os.path.join(thu_muc_nghien_cuu(goc, ma), v7.TEP_CAU_HINH),
             json.dumps(ch, ensure_ascii=False, indent=2))
    except Exception as loi:  # noqa: BLE001
        log("  gieo Công thức V7 hỏng: {0}".format(str(loi)[:120]))

    # ── máy đăng: đưa kênh vào vm/config.json khi đã thấy trình duyệt của kênh ──
    try:
        from . import trung_tam as tt_mod  # noqa: PLC0415

        vm = tt_mod.thu_muc_vm(goc)
        chrome = tt_mod.tim_trinh_duyet(vm, ma)
        if chrome and os.path.isfile(os.path.join(vm, "config.json")):
            tt_mod.them_kenh_vao_vm(vm, ma, chrome=chrome)
            log("  máy đăng: đã nhận kênh {0} (trình duyệt {1}).".format(ma, chrome))
        else:
            kq.viec_cua_ban.append(
                "Trình duyệt của kênh: đặt Chrome portable ở {0}\\{1}\\{1}.exe (cạnh thư mục MyTool), đăng nhập "
                "YouTube + vào Studio một lần, rồi ở Số liệu kênh → Thêm kênh → Dùng kênh có sẵn → tick "
                "“Cho máy đăng lo kênh này”.".format(os.path.dirname(os.path.abspath(goc)), ma))
    except Exception as loi:  # noqa: BLE001
        log("  (không kiểm được máy đăng: {0})".format(str(loi)[:100]))
    if not co_san:
        log("  thiết lập kênh: kenh.yaml `thiet_lap_kenh: true` — agent dựng hồ sơ (LLM + cổng ảnh ShopAPI) rồi tự điền "
            "tên/handle/mô tả/logo/banner/từ khoá/danh sách phát vào Studio khi Chrome kênh đã đăng nhập.")
    log("b) Kênh {0}: {1} ({2} lời nhắc viết lại, {3} giữ nguyên).".format(
        ma, dich, len(kq.loi_nhac_viet_lai), len(kq.loi_nhac_giu_nguyen)))
    return dich


# ── c) Nghiên cứu khởi động ──────────────────────────────────────────────────────────────────────


def _tim_mac_dinh(q: str, *, limit: int = 20, lang: str = "") -> List[Any]:
    from . import youtube  # noqa: PLC0415

    return youtube.search_videos(q, limit=limit, lang=lang)


def gieo_doi_thu(goc: str, ma: str, hs: Dict[str, Any], yc: YeuCau, kq: KetQua, log: Callable[[str], None],
                 *, tim: Optional[Callable[..., List[Any]]] = None, toi_da_kenh: int = 40) -> Dict[str, Any]:
    """Tìm YouTube theo `tu_khoa_tim` (+ kênh mẫu) → hộp thư đối thủ của kênh. Lọc rẻ bằng tiếng + bộ từ
    loại trừ CỦA NGÁCH (`trang_chu.dung_tieng`, `kenh_bi_loai`); phán đúng/sai ngách là việc của chuỗi
    Một nút sau đó (LLM đọc nghĩa). Ghi `khoi-tao/tim-kiem.json` trong nhóm để soi lại."""
    from . import doi_thu_kenh as so  # noqa: PLC0415
    from .ho_so_ngach import doc_ngach  # noqa: PLC0415
    from .trang_chu import dung_tieng, kenh_bi_loai  # noqa: PLC0415

    ket: Dict[str, Any] = {"cum": [], "kenh": [], "bi_loai": 0, "loi": []}
    if yc.kenh_mau:
        from .youtube import normalize_channel_url  # noqa: PLC0415

        mau = [normalize_channel_url(x) or x for x in yc.kenh_mau]
        if not yc.thu:
            so.them_ban_dua(goc, ma, mau)
        ket["kenh_mau"] = mau
        log("c) kênh mẫu → hộp thư: {0}".format(", ".join(mau)))
    cum = [str(x) for x in (hs.get("tu_khoa_tim") or []) if str(x).strip()][:12]
    ket["cum"] = cum
    if yc.thu:
        log("c) [THỬ] Sẽ tìm YouTube {0} cụm: {1}".format(len(cum), " · ".join(cum)[:300]))
        kq.tim_kiem = ket
        return ket
    hsn = doc_ngach(goc, ma)
    loc = {"tu_loai_tru": list(hsn.tu_loai_tru), "ten_kenh_loai_tru": list(hsn.ten_kenh_loai_tru),
           "handle_loai_tru": list(hsn.handle_loai_tru)}
    tim = tim or _tim_mac_dinh
    dem: Dict[str, Dict[str, Any]] = {}
    for q in cum:
        try:
            hits = tim(q, limit=20, lang=yc.ngon_ngu) or []
        except Exception as loi:  # noqa: BLE001 — một cụm hỏng không bỏ cả lượt
            ket["loi"].append("{0}: {1}".format(q, str(loi)[:120]))
            continue
        for h in hits:
            cid = str(getattr(h, "channel_id", "") or "")
            ten = str(getattr(h, "channel_name", "") or "")
            td = str(getattr(h, "title", "") or "")
            if not cid:
                continue
            link = "https://www.youtube.com/channel/{0}".format(cid)
            td_thuong = td.lower()
            if not dung_tieng(td + " " + ten, yc.ngon_ngu) or kenh_bi_loai(ten, link, **loc) \
                    or any(t.lower() in td_thuong for t in loc["tu_loai_tru"] if t != KHONG_KHOP):
                ket["bi_loai"] += 1
                continue
            d = dem.setdefault(link, {"link": link, "ten": ten, "so_lan": 0, "view": 0, "cum": []})
            d["so_lan"] += 1
            d["view"] = max(d["view"], int(getattr(h, "views", 0) or 0))
            if q not in d["cum"]:
                d["cum"].append(q)
        time.sleep(0)  # giữ chỗ cho nhịp nghỉ nếu cần — yt-dlp đã tự nghỉ giữa các lượt
    xep = sorted(dem.values(), key=lambda d: (-d["so_lan"], -d["view"]))[:max(1, int(toi_da_kenh))]
    ket["kenh"] = xep
    if xep:
        cu = so.doc_doi_thu(goc, ma)
        da_co = {x.strip() for x in cu.splitlines() if x.strip()}
        moi = [d["link"] for d in xep if d["link"] not in da_co]
        if moi:
            so.luu_doi_thu(goc, ma, (cu.strip() + "\n" if cu.strip() else "") + "\n".join(moi))
        ket["vao_hop_thu"] = len(moi)
    _ghi(os.path.join(duong_kenh(goc), "_NHOM", yc.nhom, THU_MUC_KHOI_TAO, "tim-kiem.json"),
         json.dumps(ket, ensure_ascii=False, indent=1))
    log("c) tìm YouTube {0} cụm → {1} kênh ứng viên vào hộp thư (loại {2} kết quả lệch tiếng/loại trừ{3}).".format(
        len(cum), len(xep), ket["bi_loai"], "; {0} cụm lỗi".format(len(ket["loi"])) if ket["loi"] else ""))
    kq.tim_kiem = ket
    return ket


def buoc_nghien_cuu(goc: str, ma: str, hs: Dict[str, Any], yc: YeuCau, kq: KetQua, log: Callable[[str], None], *,
                    client: Any = None, tim: Optional[Callable[..., List[Any]]] = None,
                    chay_mot_nut: Optional[Callable[..., Any]] = None) -> None:
    """c) Gieo hộp thư + chạy chuỗi Một nút (chốt đối thủ có AI, kiểm ngách theo nghĩa, quét content)."""
    gieo_doi_thu(goc, ma, hs, yc, kq, log, tim=tim)
    if yc.thu:
        log("c) [THỬ] Sau đó: chuỗi Một nút có ví — chốt đối thủ (4 cửa + AI), kiểm ngách theo nghĩa bằng LLM, "
            "quét content → kho nguồn. Lịch 02:00 tự chọn nguồn từ kho đó.")
        kq.nghien_cuu = "thử"
        return
    if yc.bo_nghien_cuu:
        log("c) bỏ chuỗi Một nút (--bo-nghien-cuu) — lượt tự chạy 02:00 sẽ làm.")
        kq.nghien_cuu = "bỏ qua"
        return
    if chay_mot_nut is None:
        from . import mot_nut  # noqa: PLC0415

        chay_mot_nut = mot_nut.chay
    log("c) chuỗi Một nút (chốt đối thủ theo nghĩa + quét content)…")
    try:
        bc = chay_mot_nut(goc, ma, client=client, on_log=lambda m: log("   " + str(m)))
        kq.nghien_cuu = str(getattr(bc, "tom_tat", lambda: "")() or "xong")
    except Exception as loi:  # noqa: BLE001 — nghiên cứu hỏng không xoá kênh vừa dựng
        kq.nghien_cuu = "hỏng: " + str(loi)[:200]
        _viec_tu_thu_lai(goc, kq, "nghien_cuu", "Nghiên cứu khởi động hỏng ({0}) — lượt tự chạy sẽ thử lại; hoặc "
                         "chạy `python tu_chay.py --kenh {1} --thu` để xem.".format(str(loi)[:120], ma))
    log("c) nghiên cứu: " + kq.nghien_cuu[:300])


# ── Ghép bốn bước ────────────────────────────────────────────────────────────────────────────────


def _viet_viec(goc: str, kq: KetQua, yc: YeuCau) -> None:
    from .ho_so_ngach import ten_tieng  # noqa: PLC0415

    _quen_loi_da_het(goc, kq)
    viec = list(kq.viec_cua_ban)
    viec.append("Chọn giọng đọc: điền `voice_id` (một giọng {0} RIÊNG, khác mọi kênh trên máy) trong "
                "CHANNEL/{1}/kenh.yaml hoặc Quản lý kênh.".format(ten_tieng(yc.ngon_ngu) or yc.ngon_ngu,
                                                                     kq.ma_kenh))
    viec.append("Đo lại `ky_tu_moi_phut` sau video đầu (số ký tự kịch bản ÷ số phút của 2-giong-doc.mp3).")
    viec.append("Chạy thử miễn phí: `python tu_chay.py --kenh {0} --thu` — log phải có ứng viên đúng ngách.".format(
        kq.ma_kenh))
    viec.append("Bật tiền + tự động khi đã ổn: `ngan_sach_ngay`, `tu_chay` (Quản lý kênh). Duyệt tay ≥ 7 ngày đầu "
                "(`tu_duyet` để tắt).")
    kq.viec_cua_ban = viec
    if yc.thu or not kq.duong_kenh or not os.path.isdir(kq.duong_kenh):
        return
    dong = ["# Khởi tạo kênh {0} — {1}".format(kq.ma_kenh, _dt.datetime.now().strftime("%Y-%m-%d %H:%M")), "",
            "Chủ đề: {0} · quốc gia {1} · ngôn ngữ {2} · nhóm `{3}`".format(
                yc.chu_de, yc.quoc_gia, yc.ngon_ngu, yc.nhom),
            "Hồ sơ ngách: `{0}`".format(os.path.relpath(kq.duong_ngach, goc) if kq.duong_ngach else "?"),
            "Lời nhắc viết lại theo ngách: {0}".format(", ".join(kq.loi_nhac_viet_lai) or "(không)"),
            "Nghiên cứu khởi động: {0}".format(kq.nghien_cuu or "-"), "", "## Việc của bạn", ""]
    dong += ["{0}. {1}".format(i, v) for i, v in enumerate(viec, 1)]
    if kq.tu_thu_lai:
        dong += ["", "## Máy tự thử lại (chưa cần bạn; báo bạn nếu còn hỏng sau {0} ngày)".format(
            NGAY_BAO_NGUOI_LOI_TU_THU), ""] + ["- " + v for v in kq.tu_thu_lai]
    _ghi(os.path.join(kq.duong_kenh, TEP_VIEC), "\n".join(dong) + "\n")


def khoi_tao(goc: str, yc: YeuCau, *, goi: Optional[Callable[..., str]] = None, client: Any = None,
             tim: Optional[Callable[..., List[Any]]] = None, lay_kenh: Optional[Callable[..., Any]] = None,
             tao_anh: Optional[Callable[[str, str], str]] = None,
             chay_mot_nut: Optional[Callable[..., Any]] = None,
             log: Callable[[str], None] = print) -> KetQua:
    """Chạy bốn bước. `goi`/`tim`/`lay_kenh`/`tao_anh`/`chay_mot_nut` là chỗ cắm cho bài kiểm (đồ giả, không
    tốn tiền); để `None` mà có `client` thì dùng bản thật qua ví ShopAPI. `yc.thu` → không gọi gì cả."""
    yc.chuan()
    kq = KetQua(nhom=yc.nhom, thu=yc.thu)

    def ghi(m: str) -> None:
        kq.nhat_ky.append(str(m))
        log(m)

    if not yc.chu_de or len(yc.quoc_gia) != 2 or not yc.ngon_ngu:
        raise ValueError("Cần đủ --chu-de, --quoc-gia (2 chữ, vd VN) và --ngon-ngu (vd vi).")
    if goi is None and client is not None and not yc.thu:
        goi = goi_tu_client(client, ghi)
    if tao_anh is None and client is not None and not yc.thu:
        def _tao_anh_that(prompt: str, dich: str) -> str:
            return _tao_anh_nv(client, prompt, dich, "khoi-tao:nv:{0}".format(
                hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:16]))
        tao_anh = _tao_anh_that
    thu_muc = os.path.join(duong_kenh(goc), "_NHOM", yc.nhom, THU_MUC_KHOI_TAO)
    ai = BoGoiAI(None if yc.thu else goi, thu_muc, ghi)
    if not yc.thu and goi is None:
        ghi("  (không có ví — AI không chạy; hồ sơ/lời nhắc dùng bản nháp)")
    ghi("── Khởi tạo ngách “{0}” · {1} · {2} → nhóm {3}{4} ──".format(
        yc.chu_de, yc.quoc_gia, yc.ngon_ngu, yc.nhom, " [CHẾ ĐỘ THỬ — không tốn tiền]" if yc.thu else ""))
    hs = buoc_ho_so(goc, yc, ai, kq, ghi, lay_kenh=lay_kenh)
    buoc_kenh(goc, yc, hs, ai, kq, ghi, tao_anh=tao_anh)
    buoc_nghien_cuu(goc, kq.ma_kenh, hs, yc, kq, ghi, client=client, tim=tim, chay_mot_nut=chay_mot_nut)
    ghi("d) Giai đoạn: kenh.yaml `chien_luoc: tu_dong` → kênh mới chọn nguồn bằng VPH + thăm dò; khi có video "
        "thắng thật (cổng chuyển V7) tự sang V7.")
    _viet_viec(goc, kq, yc)
    ghi("── Xong. AI: {0} lượt gọi mới, {1} lượt dùng lại. Việc của bạn: ──".format(ai.so_luot, ai.so_nho))
    for i, v in enumerate(kq.viec_cua_ban, 1):
        ghi("  {0}. {1}".format(i, v))
    return kq


# ── Chạy nền từ giao diện ────────────────────────────────────────────────────────────────────────


def duong_nhat_ky(goc: str) -> str:
    return os.path.join(goc, "workspace", "khoi-tao-ngach", time.strftime("%Y%m%d-%H%M%S") + ".log")


def chay_nen(goc: str, *, chu_de: str, quoc_gia: str, ngon_ngu: str, kenh_mau: Sequence[str] = (),
             tu_khoa: Sequence[str] = (), ma_kenh: str = "", doi_chu_de: bool = False, thu: bool = False,
             popen: Optional[Callable[..., Any]] = None, python: str = "") -> Tuple[bool, str]:
    """Nút trên giao diện: mở `python -m core.khoi_tao_ngach …` TÁCH KHỎI tool (vài phút gọi AI; đóng
    tool không dừng nó), nhật ký vào `workspace/khoi-tao-ngach/<giờ>.log`."""
    lenh = [python or sys.executable or "python", "-m", "core.khoi_tao_ngach", "--chu-de", chu_de,
            "--quoc-gia", quoc_gia, "--ngon-ngu", ngon_ngu]
    for x in kenh_mau:
        lenh += ["--kenh-mau", x]
    for x in tu_khoa:
        lenh += ["--tu-khoa", x]
    if ma_kenh:
        lenh += ["--ma-kenh", ma_kenh]
    if doi_chu_de:
        lenh.append("--doi-chu-de")
    if thu:
        lenh.append("--thu")
    nhat_ky = duong_nhat_ky(goc)
    os.makedirs(os.path.dirname(nhat_ky), exist_ok=True)
    co = 0
    if os.name == "nt":
        try:
            from .tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            CO_TACH_KHOI_JOB = 0  # noqa: N806
        co = 0x00000008 | 0x00000200 | 0x08000000 | CO_TACH_KHOI_JOB
    moi_truong = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    try:
        with open(nhat_ky, "a", encoding="utf-8") as tep:
            (popen or subprocess.Popen)(lenh, cwd=goc, stdout=tep, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL, creationflags=co, env=moi_truong,
                                        close_fds=True)
    except OSError as loi:
        return False, "Không mở được lượt khởi tạo: {0}".format(loi)
    return True, ("Đã bắt đầu {0} ngách “{1}” ({2}, {3}). Lượt chạy riêng vài phút — xong thì kênh hiện trong "
                  "danh sách, việc còn lại ghi ở CHANNEL/<mã>/KHOI-TAO.md. Nhật ký: {4}").format(
                      "chạy thử" if thu else "khởi tạo", chu_de, quoc_gia, ngon_ngu, nhat_ky)


# ── Dòng lệnh ────────────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Khởi tạo ngách bằng AI: hồ sơ ngách + kênh + nghiên cứu khởi động.")
    ap.add_argument("--chu-de", required=True, help="Chủ đề, ví dụ \"nấu ăn tại gia\".")
    ap.add_argument("--quoc-gia", required=True, help="Mã quốc gia 2 chữ, ví dụ VN, JP, US.")
    ap.add_argument("--ngon-ngu", required=True, help="Mã ngôn ngữ, ví dụ vi, ja, en.")
    ap.add_argument("--kenh-mau", action="append", default=[], help="Link kênh mẫu (lặp lại được, tối đa 3).")
    ap.add_argument("--tu-khoa", action="append", default=[], help="Từ khoá gợi ý (lặp lại được).")
    ap.add_argument("--ma-kenh", default="", help="Mã kênh (tên thư mục). Trống = theo thư mục trình duyệt / K1.")
    ap.add_argument("--nhom", default="", help="Tên nhóm (mặc định: theo chủ đề + quốc gia).")
    ap.add_argument("--ten-kenh", default="", help="Tên hiển thị của kênh.")
    ap.add_argument("--doi-chu-de", action="store_true", help="Đổi chủ đề cho kênh --ma-kenh đang có.")
    ap.add_argument("--lam-lai-ngach", action="store_true", help="AI viết lại ngach.yaml dù đã có.")
    ap.add_argument("--bo-nghien-cuu", action="store_true", help="Không chạy chuỗi Một nút ngay.")
    ap.add_argument("--thu", action="store_true", help="Chế độ thử: không gọi AI, không mạng, không tốn tiền.")
    ap.add_argument("--goc", default="", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    goc = os.path.abspath(a.goc or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    yc = YeuCau(chu_de=a.chu_de, quoc_gia=a.quoc_gia, ngon_ngu=a.ngon_ngu, kenh_mau=a.kenh_mau,
                tu_khoa=a.tu_khoa, ma_kenh=a.ma_kenh, nhom=a.nhom, ten_kenh=a.ten_kenh,
                doi_chu_de=a.doi_chu_de, thu=a.thu, bo_nghien_cuu=a.bo_nghien_cuu,
                lam_lai_ngach=a.lam_lai_ngach)
    client = None
    if not a.thu:
        from .api import build_client  # noqa: PLC0415
        from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415

        cau_hinh = load_config(os.path.join(goc, CONFIG_FILENAME))
        if cau_hinh.problem:
            print("Không đọc được cấu hình/khoá ShopAPI ({0}). Đăng nhập ở Tài khoản & Cài đặt, hoặc chạy --thu."
                  .format(cau_hinh.problem))
            return 1
        client = build_client(cau_hinh)
    try:
        khoi_tao(goc, yc, client=client)
    except Exception as loi:  # noqa: BLE001 — nói thật, mã 1
        print("LỖI: {0}".format(loi))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
