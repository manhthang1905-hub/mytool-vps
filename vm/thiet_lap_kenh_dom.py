"""TỰ THIẾT LẬP KÊNH YouTube trên Studio (03/10/2026) — phần 2: ĐIỀN HỒ SƠ VÀO STUDIO.

Chạy MỘT LẦN cho mỗi kênh, lặp lại an toàn: ĐỌC hiện trạng Studio trước, chỉ SỬA mục khác hồ sơ
(`CHANNEL/<K>/thiet-lap/ho-so.json`, dựng bởi `python -m core.thiet_lap_kenh tao <K>`), sửa xong
ĐỌC LẠI để xác nhận. Máy mới chỉ cần Chrome đã đăng nhập.

Mục (sổ `vm/logs/thiet-lap-kenh/<K>.json`, mỗi mục `dat` / `hong` / `can_nguoi` / `cho`):
  tên · handle · mô tả · logo · banner · hình mờ   (Tuỳ chỉnh kênh → Hồ sơ → Xuất bản)
  quốc gia · từ khoá                               (Cài đặt → Kênh → Thông tin cơ bản)
  mặc định tải lên: ngôn ngữ, danh mục, thẻ        (Cài đặt → Chế độ mặc định cho video tải lên;
                                                    KHÔNG đụng chế độ hiển thị mặc định)
  danh sách phát còn thiếu (so tên), công khai     (Nội dung → Danh sách phát)
Đủ mục `dat` → kênh `xong`; agent tự ghi `thiet_lap_kenh: false` vào kenh.yaml.

Luật đổi tên / handle: YouTube cho 2 lần / 14 ngày → CHỈ đổi khi KHÁC hồ sơ, ghi ngày đổi vào sổ;
Studio từ chối thì ghi lý do + `can_nguoi`, KHÔNG thử lại cùng giá trị. Handle trùng → thử tối đa 3
biến thể nhẹ (thêm -<ngôn ngữ>, số), ghi handle THẬT.

An toàn: gặp xác minh danh tính / đăng nhập lại / CAPTCHA / hộp yêu cầu điện thoại → DỪNG, `can_nguoi`,
không thử lại. Khoá RIÊNG THEO KÊNH dùng chung cơ chế `.khoa`/`.dung` của `vm/nuoi_trang_chu.py`
(CÙNG tệp `logs/nuoi-trang-chu/<K>.khoa` → không bao giờ 2 tiến trình cùng mở Chrome một kênh; agent
đòi Chrome để đăng thì ghi `<K>.dung`, phiên này đóng Chrome ngay, hôm sau/nhịp sau làm tiếp).
Không chạy 02:00–07:00; van IPv4 mở thì hoãn; một lúc chỉ MỘT phiên thiết lập trên máy.

Chạy:  python vm/thiet_lap_kenh_dom.py --kenh TL5-T7 [--thu]
       (`--thu` = chỉ ĐỌC Studio, in khác biệt so với hồ sơ, không sửa, không ghi sổ)
       --mo-lai   xoá `can_nguoi`/từ chối cũ (khi người đã xử lý) rồi chạy tiếp
       --kiem-thuong-hieu [--dat-hinh-mo]   (14/10) CHỈ ĐỌC hình mờ / trailer / video nổi bật / số danh sách phát →
                  `<K>.thuong-hieu.json` + ảnh; `--dat-hinh-mo`: kênh THIẾU hình mờ thì đặt (toàn bộ video), đọc lại.
                  Chạy được cả kênh chính (không cần `thiet_lap_kenh: true`, không ghi sổ `<K>.json`).
       --dat-trang-chu   (14/10, chủ duyệt) bật Thẻ Trang chủ + video giới thiệu cho người CHƯA đăng ký (video thắng nhất
                  của chính kênh: hiển thị × tỷ lệ bấm, dài, công khai, >= 7 ngày) + video nổi bật (nhì) + phần «Video phổ
                  biến»; đọc lại sau Xuất bản. --dat-mo-ta: kênh đang TRỐNG mô tả thì viết (LLM) + đặt. Kèm --khong-luu = điền rồi bỏ.
Mã thoát: 0 xong/đã đủ · 10 hoãn · 20 cần người · 30 không cần chạy · 1 lỗi.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.abspath(__file__))                 # vm/
GOC_TOOL = os.path.dirname(GOC)                                  # MyTool/
for _d in (GOC, GOC_TOOL):          # chỉ NỐI ĐUÔI (agent nạp module này: không đổi thứ tự sys.path của nó)
    if _d not in sys.path:
        sys.path.append(_d)
import nuoi_trang_chu as nuoi  # noqa: E402  — khoá/cờ dừng/khung cấm/khe nang dùng CHUNG, không viết cơ chế thứ hai

THU_MUC_SO = os.path.join(GOC, "logs", "thiet-lap-kenh")
THU_MUC_KHOA_RIENG = THU_MUC_SO                                  # khoá "một phiên thiết lập một lúc"
MA_HOAN, MA_CAN_NGUOI, MA_KHONG_CAN = nuoi.MA_HOAN, nuoi.MA_CAN_NGUOI, nuoi.MA_KHONG_CAN

# ── Hằng số luật (đổi ở đây, test canh) ─────────────────────────────────────
MUC = ("ngon_ngu", "ten", "handle", "mo_ta", "logo", "banner", "hinh_mo", "quoc_gia", "tu_khoa", "mac_dinh", "danh_sach_phat")
TEN_MUC = {"ngon_ngu": "ngôn ngữ Studio", "ten": "tên kênh", "handle": "handle", "mo_ta": "mô tả", "logo": "logo", "banner": "banner",
           "hinh_mo": "hình mờ", "quoc_gia": "quốc gia", "tu_khoa": "từ khoá kênh",
           "mac_dinh": "mặc định tải lên", "danh_sach_phat": "danh sách phát"}
TOI_DA_LAN_NGAY = 2                       # mỗi kênh tối đa 2 phiên thiết lập / ngày
NGHI_SAU_HONG_PHUT = 45                   # phiên hỏng → nghỉ ngần này rồi mới thử lại
CUA_SO_DOI_TEN_NGAY = 14                  # YouTube: 2 lần đổi tên / handle trong 14 ngày
TOI_DA_DOI_TRONG_CUA_SO = 2
TOI_DA_BIEN_THE_HANDLE = 3
NGAN_SACH_PHIEN_PHUT = 25
KHUNG_CAM = nuoi.KHUNG_CAM
CHU_KY_LICH_AGENT_GIAY = 10 * 60

#: Trang / hộp đòi người: URL hoặc chữ trong HỘP THOẠI (đa ngôn ngữ).
URL_CHAN = (("accounts.google.com", "dang_xuat"), ("/signin", "dang_xuat"), ("servicelogin", "dang_xuat"),
            ("/challenge", "xac_minh"), ("recaptcha", "captcha"), ("/speedbump", "xac_minh"),
            ("consent.youtube.com", "dong_y"), ("consent.google.com", "dong_y"))
RE_CHU_CHAN = re.compile(
    r"(xác minh (danh tính|bạn là ai|tài khoản|số điện thoại|qua điện thoại|bằng số điện thoại)|xác nhận (đó là bạn|danh tính)|"
    r"verify (it'?s you|your identity|your phone|phone number)|confirm (it'?s you|your identity)|phone verification|"
    r"本人確認|電話番号(を|の)?(確認|認証|入力)|アカウントの確認|ロボットではありません|captcha|not a robot|"
    r"đăng nhập lại|sign in again|please sign in|再度ログイン|2-step|xác minh 2 bước|2 段階認証|2段階認証)", re.I)
CHU_NUT_XONG = ("Xong", "Done", "完了", "Áp dụng", "Apply", "適用", "Lưu", "Save", "保存")
CHU_NUT_XAC_NHAN = ("Xác nhận", "Tiếp tục", "Có", "Confirm", "Continue", "OK", "Yes", "確認", "続行", "はい", "Đồng ý")
CHU_CONG_KHAI = ("Công khai", "Public", "公開")
CHU_TAO = ("Tạo", "Create", "作成")
CHU_DS_MOI = ("Danh sách phát mới", "New playlist", "新しい再生リスト", "新規再生リスト")
CHU_TAB_DS_PHAT = ("Danh sách phát", "Playlists", "再生リスト")


class CanNguoi(Exception):
    """Cần người xử lý (xác minh danh tính, đăng nhập, CAPTCHA, điện thoại...) — dừng, không thử lại."""


class Hoan(Exception):
    """Chưa chạy được lúc này (không phải lỗi)."""


class LoiMuc(Exception):
    """Một mục hỏng (không đọc/sửa được) — ghi `hong`, đi tiếp mục khác."""


# ═══════════════════════════ HÀM THUẦN (có test) ═════════════════════════════
def chuan(s: Any) -> str:
    """Chuẩn hoá để so: NFKC, gộp khoảng trắng, hạ chữ."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip().casefold()


def chuan_dong(s: Any) -> List[str]:
    """Chữ nhiều dòng → danh sách dòng KHÔNG rỗng đã chuẩn hoá (so mô tả: lệch dòng trống không tính)."""
    s = unicodedata.normalize("NFKC", str(s or "")).replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    return [" ".join(d.split()) for d in s.split("\n") if d.strip()]


def mo_ta_giong(a: Any, b: Any) -> bool:
    return chuan_dong(a) == chuan_dong(b)


def bo_chu(ds: Any) -> set:
    if isinstance(ds, str):
        ds = re.split(r"[,、，\n]+", ds)
    return {chuan(x) for x in (ds or []) if chuan(x)}


def khop_ten(ten: Any, aliases) -> bool:
    return chuan(ten) in {chuan(a) for a in (aliases or ())}


def sha_tep(duong: str) -> str:
    try:
        with open(duong, "rb") as tep:
            return hashlib.sha1(tep.read()).hexdigest()
    except OSError:
        return ""


#: Chữ CHỈ có ở Studio tiếng Việt (thanh bên / tiêu đề) — dùng đọc xác nhận ngôn ngữ giao diện.
CHU_STUDIO_VI = ("Nội dung", "Bảng điều khiển của kênh", "Tuỳ chỉnh", "Tùy chỉnh", "Số liệu phân tích", "Danh sách phát")
RE_MUC_NGON_NGU = r"언어|language|言語|ngôn ngữ"
RE_TIENG_VIET = r"^(tiếng việt|vietnamese|베트남어|ベトナム語)"
URL_NGON_NGU_VI = "https://studio.youtube.com/?hl=vi"


def la_tieng_viet(lang: Any, chu: Any) -> bool:
    """Studio đang hiện tiếng Việt? `<html lang>` bắt đầu `vi` HOẶC thấy >= 2 chữ giao diện tiếng Việt đặc trưng."""
    if str(lang or "").strip().lower().startswith("vi"):
        return True
    t = unicodedata.normalize("NFC", str(chu or ""))
    return sum(1 for w in CHU_STUDIO_VI if w in t) >= 2


#: BẢNG NGÔN NGỮ GIAO DIỆN ĐÍCH (04/10/2026): Studio theo ngôn ngữ của TÀI KHOẢN Google = ngôn ngữ/quốc gia của NGÁCH
#: (không cố định tiếng Việt). `go` = chữ gõ vào ô tìm (thử lần lượt), `re_chon` = nhãn mục trong danh sách,
#: `chu` = chữ ĐẶC TRƯNG của thanh bên Studio ở ngôn ngữ đó (>= 2 chữ → xác nhận), `quoc_gia` = quốc gia khớp.
NGON_NGU_DICH = {
    "vi": {"ten": "Tiếng Việt", "html": "vi", "go": ("Tiếng Việt", "Vietnamese"), "quoc_gia": ("VN",),
           "re_chon": r"(?:^|\s)(tiếng việt|vietnamese|베트남어|ベトナム語)", "chu": CHU_STUDIO_VI},
    "ja": {"ten": "日本語", "html": "ja", "go": ("日本語", "Japanese", "Tiếng Nhật"), "quoc_gia": ("JP",),
           "re_chon": r"(?:^|\s)(日本語|japanese|일본어|tiếng nhật)",
           "chu": ("コンテンツ", "チャンネル ダッシュボード", "アナリティクス", "カスタマイズ", "再生リスト", "収益化", "字幕")},
    "en": {"ten": "English", "html": "en", "go": ("English (United States)", "English"), "quoc_gia": ("US", "GB", "CA", "AU", "IN"),
           "re_chon": r"(?:^|\s)(english|tiếng anh|영어|英語)", "chu": ("Content", "Analytics", "Customization", "Playlists", "Subtitles", "Channel dashboard")},
    "ko": {"ten": "한국어", "html": "ko", "go": ("한국어", "Korean", "Tiếng Hàn"), "quoc_gia": ("KR",),
           "re_chon": r"(?:^|\s)(한국어|korean|tiếng hàn|韓国語)", "chu": ("콘텐츠", "채널 대시보드", "분석", "맞춤설정", "재생목록", "수익 창출")},
}
MA_NGON_NGU_MAC_DINH = "vi"          # kênh KHÔNG khai `ngon_ngu_tai_khoan_dich` → giữ hành vi cũ (tiếng Việt)


def ma_ngon_ngu(x: Any) -> str:
    return str(x or "").strip().lower().split("-")[0].split("_")[0]


def chon_ngon_ngu_dich(khai: Any, quoc_gia: Any = "") -> Tuple[str, str]:
    """Đích ngôn ngữ tài khoản của kênh. `khai` = khoá `ngon_ngu_tai_khoan_dich` trong kenh.yaml (RỖNG → `vi` như cũ:
    triển khai DẦN, kênh nào chưa khai thì KHÔNG đổi). Khai nhưng không có trong bảng, hoặc LỆCH quốc gia hồ sơ
    (vd khai `ja` mà quốc gia VN) → rơi về `vi` kèm lý do. Trả (mã, ghi_chú)."""
    ma = ma_ngon_ngu(khai)
    if not ma:
        return MA_NGON_NGU_MAC_DINH, ""
    if ma not in NGON_NGU_DICH:
        return MA_NGON_NGU_MAC_DINH, "ngon_ngu_tai_khoan_dich={0!r} chưa có trong bảng → giữ tiếng Việt".format(ma)
    qg = str(quoc_gia or "").strip().upper()
    if qg and qg not in NGON_NGU_DICH[ma]["quoc_gia"]:
        return MA_NGON_NGU_MAC_DINH, "ngon_ngu_tai_khoan_dich={0} LỆCH quốc gia hồ sơ {1} → giữ tiếng Việt".format(ma, qg)
    return ma, ""


def la_ngon_ngu_dich(ma: str, lang: Any, chu: Any) -> bool:
    """Studio đang ở ngôn ngữ `ma`? `<html lang>` bắt đầu bằng mã HOẶC >= 2 chữ giao diện đặc trưng."""
    b = NGON_NGU_DICH.get(ma) or NGON_NGU_DICH[MA_NGON_NGU_MAC_DINH]
    if str(lang or "").strip().lower().startswith(b["html"]):
        return True
    t = unicodedata.normalize("NFC", str(chu or ""))
    return sum(1 for w in b["chu"] if w in t) >= 2


#: Nút avatar (menu tài khoản) của youtube.com theo nhãn aria — đo 05/10: vi «Trình đơn tài khoản».
RE_NUT_AVATAR = r"^(trình đơn tài khoản|trình đơn avatar|avatar|アカウント|account menu|menu tài khoản|ảnh hồ sơ|프로필|계정 메뉴)"

#: Tên nước trong menu «Địa điểm» của youtube.com theo ngôn ngữ giao diện (vi/en/ja/ko) — khớp NGUYÊN mục.
TEN_NUOC = {"JP": ("Nhật Bản", "Japan", "日本", "일본"), "KR": ("Hàn Quốc", "South Korea", "韓国", "대한민국"),
            "VN": ("Việt Nam", "Vietnam", "ベトナム", "베트남"), "US": ("Hoa Kỳ", "United States", "アメリカ合衆国", "미국"),
            "TW": ("Đài Loan", "Taiwan", "台湾", "대만"), "TH": ("Thái Lan", "Thailand", "タイ", "태국"),
            "ID": ("Indonesia", "インドネシア", "인도네시아"),
            # 06/10/2026 — thêm cho máy/ngách khác nước (CHƯA đo trên menu thật — tên theo bản dịch YouTube thường gặp;
            # lệch thì `TEN_NUOC.get(gl) or (gl,)` vẫn thử mã nước và skill K06 đọc lại menu để báo).
            "GB": ("Vương quốc Anh", "United Kingdom", "イギリス", "영국"), "CA": ("Canada", "カナダ", "캐나다"),
            "AU": ("Úc", "Australia", "オーストラリア", "오스트레일리아"), "IN": ("Ấn Độ", "India", "インド", "인도"),
            "PH": ("Philippines", "フィリピン", "필리핀"), "SG": ("Singapore", "シンガポール", "싱가포르"),
            "MY": ("Malaysia", "マレーシア", "말레이시아"), "DE": ("Đức", "Germany", "ドイツ", "독일"),
            "FR": ("Pháp", "France", "フランス", "프랑스"), "ES": ("Tây Ban Nha", "Spain", "スペイン", "스페인"),
            "BR": ("Brazil", "ブラジル", "브라질"), "MX": ("Mexico", "México", "メキシコ", "멕시코")}

#: Ngôn ngữ nội dung → nước (khi hồ sơ thiết lập chưa có `quoc_gia`).
GL_THEO_NGON_NGU = {"ja": "JP", "ko": "KR", "vi": "VN", "en": "US", "zh": "TW", "th": "TH", "id": "ID",
                    "de": "DE", "fr": "FR", "pt": "BR", "ms": "MY", "tl": "PH"}


def dia_diem_kenh(kenh: str, goc: str = GOC_TOOL) -> str:
    """05/10: ĐỊA ĐIỂM XEM của kênh (menu avatar YouTube → "Địa điểm" = cookie PREF `gl`) — quyết định trang chủ /
    xu hướng YouTube đề xuất nội dung nước nào. Ưu tiên: `dia_diem_xem` trong kenh.yaml → `quoc_gia` hồ sơ thiết lập
    → suy từ NGÔN NGỮ NỘI DUNG `ngon_ngu` (ja → JP). KHÔNG suy từ ngôn ngữ giao diện (có thể tạm là vi cho máy đăng)."""
    d = nuoi.duong_kenh_yaml(kenh, goc)
    khai = _yaml_gia_tri(d, "dia_diem_xem") if d else ""
    if re.match(r"^[A-Za-z]{2}$", str(khai or "").strip()):
        return str(khai).strip().upper()
    try:
        with open(os.path.join(goc, "CHANNEL", kenh, "thiet-lap", "ho-so.json"), "r", encoding="utf-8") as tep:
            qg = str((json.load(tep) or {}).get("quoc_gia") or "").strip().upper()
        if re.match(r"^[A-Z]{2}$", qg):
            return qg
    except (OSError, ValueError):
        pass
    nn = str((_yaml_gia_tri(d, "ngon_ngu") if d else "") or "").strip().lower()[:2]
    return GL_THEO_NGON_NGU.get(nn, "")


def ngon_ngu_dich_kenh(kenh: str, goc: str = GOC_TOOL) -> Tuple[str, str]:
    """Đọc `ngon_ngu_tai_khoan_dich` của kenh.yaml + quốc gia trong hồ sơ thiết lập (nếu đã dựng)."""
    d = nuoi.duong_kenh_yaml(kenh, goc)
    khai = _yaml_gia_tri(d, "ngon_ngu_tai_khoan_dich") if d else ""
    qg = ""
    try:
        with open(os.path.join(goc, "CHANNEL", kenh, "thiet-lap", "ho-so.json"), "r", encoding="utf-8") as tep:
            qg = str((json.load(tep) or {}).get("quoc_gia") or "")
    except (OSError, ValueError):
        pass
    return chon_ngon_ngu_dich(khai, qg)


def so_moi(kenh: str) -> dict:
    return {"kenh": kenh, "trang_thai": "chua_chay", "ly_do": "", "uc": "", "handle_that": "",
            "muc": {m: {"tt": "chua"} for m in MUC}, "ngay_doi": {"ten": [], "handle": []},
            "tu_choi": {}, "hash_anh": {}, "truoc": {}, "phien": [], "nghi_den_luc": 0.0}


def chuan_so(so: dict, kenh: str) -> dict:
    """Điền khoá thiếu (sổ cũ/hỏng) — không bao giờ ném."""
    moi = so_moi(kenh)
    for k, v in moi.items():
        if k not in so or not isinstance(so[k], type(v)):
            so[k] = v
    for m in MUC:
        so["muc"].setdefault(m, {"tt": "chua"})
    for k in ("ten", "handle"):
        so["ngay_doi"].setdefault(k, [])
    return so


def tinh_trang(so: dict) -> Tuple[str, str]:
    """(trạng thái, lý do) của kênh từ các mục: xong | can_nguoi | hong | dang_lam."""
    muc = so.get("muc") or {}
    tt = {m: (muc.get(m) or {}).get("tt", "chua") for m in MUC}
    if all(v == "dat" for v in tt.values()):
        return "xong", "đủ {0} mục".format(len(MUC))
    cn = [m for m, v in tt.items() if v == "can_nguoi"]
    if cn:
        return "can_nguoi", "; ".join("{0}: {1}".format(TEN_MUC[m], (muc[m].get("ly_do") or "")[:100]) for m in cn)
    hong = [m for m, v in tt.items() if v == "hong"]
    if hong:
        return "hong", "; ".join("{0}: {1}".format(TEN_MUC[m], (muc[m].get("ly_do") or "")[:100]) for m in hong)
    cho = [m for m, v in tt.items() if v == "cho"]
    if cho:
        return "dang_lam", "chờ: " + "; ".join("{0}: {1}".format(TEN_MUC[m], (muc[m].get("ly_do") or "")[:80]) for m in cho)
    return "dang_lam", "còn {0} mục chưa đạt".format(sum(1 for v in tt.values() if v != "dat"))


def dat_muc(so: dict, muc: str, gia_tri: Any, luc: float, ghi_chu: str = "") -> None:
    so["muc"][muc] = {"tt": "dat", "luc": time.strftime("%Y-%m-%d %H:%M", time.localtime(luc)),
                      "gia_tri": gia_tri, "ghi_chu": ghi_chu, "lan": int((so["muc"].get(muc) or {}).get("lan", 0)) + 1}


def hong_muc(so: dict, muc: str, ly_do: str, tt: str = "hong") -> None:
    cu = so["muc"].get(muc) or {}
    so["muc"][muc] = {"tt": tt, "ly_do": str(ly_do)[:300], "lan": int(cu.get("lan", 0)) + 1,
                      "luc": time.strftime("%Y-%m-%d %H:%M"), "mo_lai_luc": cu.get("mo_lai_luc", 0)}


def doi_gan_day(so: dict, muc: str, luc: float) -> List[float]:
    return [t for t in so["ngay_doi"].get(muc, []) if 0 <= luc - t < CUA_SO_DOI_TEN_NGAY * 86400]


def quyet_doi(so: dict, muc: str, hien: Any, mong: Any, luc: float) -> Tuple[str, str]:
    """Luật đổi TÊN / HANDLE. ("giong"|"doi"|"cho"|"tu_choi", lý do).
    giong = đã đúng, KHÔNG đổi (không tốn lượt) · cho = hết 2 lượt/14 ngày · tu_choi = Studio từng từ chối đúng giá trị này."""
    if chuan(hien).lstrip("@") == chuan(mong).lstrip("@") and chuan(hien):
        return "giong", ""
    tc = (so.get("tu_choi") or {}).get(muc) or {}
    if tc and chuan(tc.get("gia_tri")).lstrip("@") == chuan(mong).lstrip("@"):
        # 04/10/2026: Studio từ chối đổi tên/handle gần như luôn là giới hạn 2 lần/14 ngày của YouTube (kênh vừa
        # được đặt tên trước đó) → CHỜ hết cửa sổ rồi TỰ thử lại, không bắt người xử lý.
        mo = _luc_tu_choi(tc) + CUA_SO_DOI_TEN_NGAY * 86400
        if luc < mo:
            return "cho", "Studio từ chối lúc {0} (giới hạn đổi tên/handle của YouTube) — tự thử lại sau {1}".format(
                tc.get("luc"), time.strftime("%Y-%m-%d %H:%M", time.localtime(mo)))
    gan = doi_gan_day(so, muc, luc)
    if len(gan) >= TOI_DA_DOI_TRONG_CUA_SO:
        mo = min(gan) + CUA_SO_DOI_TEN_NGAY * 86400
        return "cho", "đã đổi {0} lần trong {1} ngày — mở lại {2}".format(
            len(gan), CUA_SO_DOI_TEN_NGAY, time.strftime("%Y-%m-%d %H:%M", time.localtime(mo)))
    return "doi", ""


def ghi_doi(so: dict, muc: str, luc: float) -> None:
    so["ngay_doi"].setdefault(muc, []).append(luc)
    so["ngay_doi"][muc] = doi_gan_day(so, muc, luc + 1)[-6:]


def _luc_tu_choi(tc: dict) -> float:
    try:
        return time.mktime(time.strptime(str(tc.get("luc") or ""), "%Y-%m-%d %H:%M"))
    except (ValueError, OverflowError):
        return 0.0


def mo_lai_doi_ten_luc(so: dict) -> float:
    """Mốc sớm nhất YouTube cho đổi lại tên/handle bị từ chối (0 nếu không có từ chối nào)."""
    ds = [_luc_tu_choi(v) + CUA_SO_DOI_TEN_NGAY * 86400 for v in (so.get("tu_choi") or {}).values() if isinstance(v, dict)]
    return min(ds) if ds else 0.0


def ghi_tu_choi(so: dict, muc: str, gia_tri: Any, ly_do: str, luc: float) -> None:
    so["tu_choi"][muc] = {"gia_tri": gia_tri, "ly_do": str(ly_do)[:200], "luc": time.strftime("%Y-%m-%d %H:%M", time.localtime(luc))}


def ten_handle_bi_chan(so: dict, muc: str, luc: float) -> str:
    """"" nếu được phép gõ `ten`/`handle`; ngược lại lý do bị CHẶN (05/10/2026). Mục đang `cho` mà Studio từng từ chối (hoặc đã đủ 2 lượt)
    trong 14 ngày → KHÔNG điền tên/handle (lượt Xuất bản không được dính tên làm cả lượt hỏng). Chặn theo CỬA SỔ, không theo giá trị."""
    if ((so.get("muc") or {}).get(muc) or {}).get("tt") != "cho":
        return ""
    tc = (so.get("tu_choi") or {}).get(muc) or {}
    if tc and _luc_tu_choi(tc) + CUA_SO_DOI_TEN_NGAY * 86400 > luc:
        return "Studio từ chối {0} lúc {1}, chưa qua {2} ngày".format(muc, tc.get("luc"), CUA_SO_DOI_TEN_NGAY)
    gan = doi_gan_day(so, muc, luc)
    if len(gan) >= TOI_DA_DOI_TRONG_CUA_SO:
        return "đã đổi {0} lần trong {1} ngày".format(len(gan), CUA_SO_DOI_TEN_NGAY)
    return ""


RE_LOI_XUAT_BAN = re.compile(r"(lỗi|không thể|không thành công|thất bại|hết lượt|vượt quá|giới hạn|error|couldn.?t|can.?t|cannot|unable|failed|"
                             r"try again|too many|limit|エラー|失敗|できません|できませんでした|問題が発生|上限)", re.I)


def thong_bao_loi_xuat_ban(chu: Any) -> str:
    """Chữ thông báo (toast/hộp/ô) của Studio sau Xuất bản có phải LỖI không? Trả chữ lỗi gọn, '' nếu không."""
    t = " ".join(str(chu or "").split())
    return t[:200] if t and RE_LOI_XUAT_BAN.search(t) else ""


def goc_url_anh(url: Any) -> str:
    """URL ảnh yt3 bỏ phần co giãn sau «=» (đổi ảnh thật thì phần gốc ĐỔI)."""
    return str(url or "").split("=")[0].strip()


def doc_anh_cong_khai(uc: Any, mo_url=None) -> Dict[str, str]:
    """Ảnh đại diện (og:image) + banner trên trang CÔNG KHAI (HTTP thường). {logo, banner} = URL gốc; {} nếu không đọc được."""
    if not uc:
        return {}
    try:
        if mo_url is None:
            import urllib.request

            def mo_url(u):
                rq = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"})
                with urllib.request.urlopen(rq, timeout=25) as r:
                    return r.read().decode("utf-8", "replace")
        h = mo_url("https://www.youtube.com/channel/{0}".format(uc))
    except Exception:  # noqa: BLE001
        return {}
    ra: Dict[str, str] = {}
    m = re.search(r'<meta property="og:image" content="([^"]*)"', h)
    if m:
        ra["logo"] = goc_url_anh(m.group(1))
    m = (re.search(r'"banner":\{"imageBannerViewModel":\{"image":\{"sources":\[\{"url":"([^"]+)"', h)
         or re.search(r'"tvBanner":\{"thumbnails":\[\{"url":"([^"]+)"', h))
    ra["banner"] = goc_url_anh(m.group(1)) if m else ""
    return ra


def bang_chung_anh_luu(truoc: Dict[str, str], muc: List[str], doc=None, cho_giay: float = 90.0, ngu=time.sleep) -> Dict[str, Tuple[bool, str]]:
    """Ảnh logo/banner đã LƯU thật chưa? = URL ảnh trên trang CÔNG KHAI KHÁC lần đọc TRƯỚC khi Xuất bản (không tin khung soạn thảo).
    Chờ tối đa `cho_giay` (CDN chậm). Trả {mục: (đạt, lý do)}."""
    doc = doc or (lambda: {})
    ra: Dict[str, Tuple[bool, str]] = {}
    het = time.monotonic() + cho_giay
    while True:
        sau = doc() or {}
        for m in muc:
            if m in ra:
                continue
            if not truoc or m not in truoc:
                ra[m] = (False, "không có bản đọc trang công khai TRƯỚC khi Xuất bản để so")
            elif sau.get(m) and sau[m] != truoc[m]:
                ra[m] = (True, "trang công khai đã đổi ảnh")
        if len(ra) == len(muc) or time.monotonic() >= het:
            break
        ngu(10.0)
    for m in muc:
        if m not in ra:
            ra[m] = (False, "trang công khai vẫn ảnh CŨ sau {0:.0f}s (Xuất bản chưa lưu ảnh)".format(cho_giay))
    return ra


def handle_cong_khai(uc: Any) -> str:
    """Handle THẬT đang hiện trên trang công khai của kênh (HTTP thường, không mở Chrome); '' nếu không đọc được."""
    if not uc:
        return ""
    try:
        import urllib.request
        rq = urllib.request.Request("https://www.youtube.com/channel/{0}".format(uc),
                                    headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"})
        with urllib.request.urlopen(rq, timeout=20) as r:
            m = re.search(r'canonicalBaseUrl":"/(@[^"]+)', r.read().decode("utf-8", "replace"))
        return m.group(1) if m else ""
    except Exception:
        return ""


def bien_the_handle(handle: str, ma_ngon_ngu: str = "jp") -> List[str]:
    """Handle gốc rồi tối đa 3 biến thể nhẹ (thêm -<ngôn ngữ>, số). Mỗi cái ≤ 30 ký tự, không trùng nhau."""
    h = str(handle or "").lstrip("@")
    ng = {"ja": "jp"}.get(str(ma_ngon_ngu or "").lower(), str(ma_ngon_ngu or "").lower()) or "jp"
    ra: List[str] = []
    for c in (h, "{0}-{1}".format(h, ng), "{0}2".format(h), "{0}-{1}2".format(h, ng)):
        c = c[:30].rstrip("-.")
        if c and c.lower() not in [x.lower() for x in ra]:
            ra.append(c)
    return ra[:1 + TOI_DA_BIEN_THE_HANDLE]


def phat_hien_chan(url: str, chu_hop_thoai: str = "", chu_trang: str = "") -> str:
    """"" nếu ổn; không thì mã: dang_xuat | xac_minh | captcha | dong_y | dien_thoai (xem `URL_CHAN`/`RE_CHU_CHAN`).
    Chữ trong HỘP THOẠI luôn xét; chữ cả trang chỉ xét khi KHÔNG ở Studio (Studio có sẵn chữ "số điện thoại" ở trang tính năng)."""
    u = str(url or "").lower()
    for mau, ma in URL_CHAN:
        if mau in u:
            return ma
    for chu in (chu_hop_thoai, chu_trang if "studio.youtube.com" not in u else ""):
        m = RE_CHU_CHAN.search(str(chu or ""))
        if m:
            t = m.group(0).lower()
            return "captcha" if ("captcha" in t or "robot" in t or "ロボット" in t) else (
                "dien_thoai" if ("điện thoại" in t or "phone" in t or "電話" in t) else "xac_minh")
    return ""


def khung_cam(luc: float, du_kien_phut: float = 0.0) -> str:
    return nuoi.khung_cam(luc, du_kien_phut)


def lan_hom_nay(so: dict, ngay: str) -> int:
    return sum(1 for p in so.get("phien", []) if p.get("ngay") == ngay and not str(p.get("ket_qua", "")).startswith("hoãn"))


def quyet_dinh(so: dict, luc: float, du_kien_phut: float = 0.0, bo_qua_khung: bool = False, bo_qua_lan: bool = False) -> Tuple[bool, str]:
    """(được chạy phiên mới không, lý do). Thuần: nhận sổ + giờ."""
    tt = so.get("trang_thai")
    if tt == "xong":
        return False, "đã xong"
    if tt == "can_nguoi":
        return False, "đang chờ người xử lý: " + str(so.get("ly_do", ""))[:120]
    if not bo_qua_khung:
        k = khung_cam(luc, du_kien_phut)
        if k:
            return False, k
    if not bo_qua_lan and lan_hom_nay(so, time.strftime("%Y-%m-%d", time.localtime(luc))) >= TOI_DA_LAN_NGAY:
        return False, "đã chạy {0} phiên hôm nay".format(TOI_DA_LAN_NGAY)
    if float(so.get("nghi_den_luc") or 0) > luc:
        return False, "nghỉ tới {0}".format(time.strftime("%H:%M", time.localtime(so["nghi_den_luc"])))
    # 04/10/2026: chỉ còn tên/handle đang CHỜ YouTube mở lại cửa sổ đổi → không mở Chrome mỗi ngày vô ích.
    muc = so.get("muc") or {}
    con = [m for m in MUC if (muc.get(m) or {}).get("tt") != "dat"]
    mo = mo_lai_doi_ten_luc(so)
    if con and all(m in ("ten", "handle") and (muc.get(m) or {}).get("tt") == "cho" for m in con) and mo > luc:
        return False, "chỉ còn tên/handle chờ YouTube cho đổi lại — thử lại {0}".format(
            time.strftime("%Y-%m-%d %H:%M", time.localtime(mo)))
    return True, ""


def khac_biet(hs: dict, ht: dict, so: dict, hash_anh: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
    """So hồ sơ `hs` với hiện trạng Studio `ht`. {mục: {"khac": True/False/None, "hien", "mong", "ghi"}}.
    `khac=None` = chưa đọc được. Chỉ mục KHÁC mới bị sửa. Ảnh: Studio không cho so điểm ảnh → coi là ĐÚNG khi sổ ghi
    đã đặt đúng tệp này (hash) VÀ Studio đang có ảnh."""
    tl = _tl()
    ra: Dict[str, dict] = {}
    muc_so = so.get("muc") or {}

    def mot(m, khac, hien, mong, ghi=""):
        ra[m] = {"khac": khac, "hien": hien, "mong": mong, "ghi": ghi}

    if "ngon_ngu_vi" in ht:
        ten_d = ht.get("ngon_ngu_dich_ten") or "tiếng Việt"
        mot("ngon_ngu", not ht["ngon_ngu_vi"], ten_d if ht["ngon_ngu_vi"] else "KHÔNG phải " + ten_d, ten_d)
    else:
        mot("ngon_ngu", None, None, ht.get("ngon_ngu_dich_ten") or "tiếng Việt")
    if "ten" in ht:
        mot("ten", chuan(ht["ten"]) != chuan(hs.get("ten")), ht["ten"], hs.get("ten"))
    else:
        mot("ten", None, None, hs.get("ten"))
    handle_mong = so.get("handle_that") or hs.get("handle") or ""
    if "handle" in ht:
        mot("handle", chuan(ht["handle"]).lstrip("@") != chuan(handle_mong).lstrip("@"), ht["handle"], handle_mong)
    else:
        mot("handle", None, None, handle_mong)
    if "mo_ta" in ht:
        mot("mo_ta", not mo_ta_giong(ht["mo_ta"], hs.get("mo_ta")), (ht["mo_ta"] or "")[:60], (hs.get("mo_ta") or "")[:60])
    else:
        mot("mo_ta", None, None, (hs.get("mo_ta") or "")[:60])
    for m in ("logo", "banner", "hinh_mo"):
        co = (ht.get("anh") or {}).get(m)
        if co is None:
            mot(m, None, None, hs.get(m))
            continue
        khop_so = (muc_so.get(m) or {}).get("tt") == "dat" and bool(hash_anh) and \
            (so.get("hash_anh") or {}).get(m) == (hash_anh or {}).get(m)
        mot(m, not (co and khop_so), "có ảnh" if co else "chưa có ảnh", hs.get(m),
            "" if khop_so else "chưa có sổ đặt đúng tệp này")
    if "quoc_gia" in ht:
        mot("quoc_gia", not khop_ten(ht["quoc_gia"], tl.ten_quoc_gia(hs.get("quoc_gia")) + (str(hs.get("quoc_gia") or ""),)),
            ht["quoc_gia"], hs.get("quoc_gia"))
    else:
        mot("quoc_gia", None, None, hs.get("quoc_gia"))
    if "tu_khoa" in ht:
        a, b = bo_chu(ht["tu_khoa"]), bo_chu(hs.get("tu_khoa"))
        mot("tu_khoa", a != b, "{0} từ khoá".format(len(a)), "{0} từ khoá".format(len(b)),
            "thiếu {0}, thừa {1}".format(len(b - a), len(a - b)))
    else:
        mot("tu_khoa", None, None, "{0} từ khoá".format(len(bo_chu(hs.get("tu_khoa")))))
    md = hs.get("mac_dinh_tai_len") or {}
    hm = ht.get("mac_dinh")
    if hm is None:
        mot("mac_dinh", None, None, md)
    else:
        sai = []
        if not khop_ten(hm.get("ngon_ngu_video"), tl.ten_ngon_ngu(md.get("ngon_ngu"))):
            sai.append("ngôn ngữ video")
        if not khop_ten(hm.get("ngon_ngu_mo_ta"), tl.ten_ngon_ngu(md.get("ngon_ngu"))):
            sai.append("ngôn ngữ mô tả")
        if not khop_ten(hm.get("danh_muc"), tl.ten_danh_muc(md.get("danh_muc"))):
            sai.append("danh mục")
        if bo_chu(hm.get("the")) != bo_chu(md.get("the")):
            sai.append("thẻ")
        mot("mac_dinh", bool(sai), hm, md, ("khác: " + ", ".join(sai)) if sai else "")
    if "danh_sach_phat" in ht:
        co = [chuan(x) for x in ht["danh_sach_phat"]]
        thieu = [d["ten"] for d in (hs.get("danh_sach_phat") or []) if chuan(d.get("ten")) not in co]
        mot("danh_sach_phat", bool(thieu), "{0} danh sách".format(len(co)), "{0} danh sách".format(len(hs.get("danh_sach_phat") or [])),
            "thiếu: " + " | ".join(thieu) if thieu else "")
    else:
        mot("danh_sach_phat", None, None, "{0} danh sách".format(len(hs.get("danh_sach_phat") or [])))
    return ra


def _tl():
    from core import thiet_lap_kenh as tl  # noqa: PLC0415
    return tl


# ═══════════════════════════ SỔ ═════════════════════════════════════════════
def duong_so(kenh: str) -> str:
    return os.path.join(THU_MUC_SO, kenh + ".json")


def doc_so(kenh: str) -> dict:
    try:
        with open(duong_so(kenh), "r", encoding="utf-8") as tep:
            so = json.load(tep)
        return chuan_so(so if isinstance(so, dict) else {}, kenh)
    except (OSError, ValueError):
        return so_moi(kenh)


#: 04/10: thiết lập kênh chỉ dùng Chrome, gần như không tốn CPU — KHÔNG chờ khe nang (7 kênh sản xuất thì
#: khe nang bận gần cả ngày, thiết lập sẽ không bao giờ tới lượt). Giữ khung cấm, khoá kênh, nhường việc đăng.
CHO_KHE_NANG = False
_BO_QUA_KHE = False          # (dev) `--bo-qua-khung`: bỏ kiểm khe nang — CHỈ dùng khi thử tay
_NHOM_CHON: Optional[set] = None   # (dev) `--nhom ho_so,mac_dinh`: chỉ chạy các nhóm này
_KHONG_GHI_SO = False        # `--thu` / `--khong-luu`: không ghi sổ (không làm bẩn sổ thật)


def luu_so(so: dict) -> None:
    if _KHONG_GHI_SO:
        return
    os.makedirs(THU_MUC_SO, exist_ok=True)
    d = duong_so(so["kenh"])
    with open(d + ".tam", "w", encoding="utf-8") as tep:
        json.dump(so, tep, ensure_ascii=False, indent=1)
    os.replace(d + ".tam", d)
    ghi_bao_cao(so)


def ghi_bao_cao(so: dict) -> None:
    d = ["# Thiết lập kênh — {0}".format(so["kenh"]), "",
         "- Trạng thái: **{0}** {1}".format(so.get("trang_thai"), so.get("ly_do") or ""),
         "- Kênh Studio: {0} · handle thật: {1}".format(so.get("uc") or "?", so.get("handle_that") or "(theo hồ sơ)"), "",
         "| Mục | Trạng thái | Lần | Ghi chú |", "|---|---|---|---|"]
    for m in MUC:
        x = so["muc"].get(m) or {}
        d.append("| {0} | {1} | {2} | {3} |".format(TEN_MUC[m], x.get("tt"), x.get("lan", ""),
                                                    str(x.get("ly_do") or x.get("ghi_chu") or "").replace("|", "/")[:120]))
    try:
        with open(os.path.join(THU_MUC_SO, so["kenh"] + ".md"), "w", encoding="utf-8") as tep:
            tep.write("\n".join(d) + "\n")
    except OSError:
        pass


def _nhat_ky(kenh: str):
    os.makedirs(THU_MUC_SO, exist_ok=True)
    duong = os.path.join(THU_MUC_SO, kenh + ".log")

    def ghi(dong):
        nuoi.canh_tien_trien.danh_dau()
        chu = "{0} {1}".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong)
        try:
            print(chu, flush=True)
        except (OSError, UnicodeEncodeError):
            pass
        try:
            with open(duong, "a", encoding="utf-8") as tep:
                tep.write(chu + "\n")
        except OSError:
            pass
    return ghi


# ═══════════════════════════ kenh.yaml ══════════════════════════════════════
def _yaml_gia_tri(duong: str, khoa: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return nuoi._yaml_chu(tep.read(), khoa)
    except OSError:
        return ""


def thiet_lap_bat(kenh: str, goc: str = GOC_TOOL) -> bool:
    d = nuoi.duong_kenh_yaml(kenh, goc)
    return bool(d) and _yaml_gia_tri(d, "thiet_lap_kenh").lower() == "true"


def cac_kenh_bat(goc: str = GOC_TOOL) -> List[str]:
    """Mọi kênh có `thiet_lap_kenh: true` (CHANNEL/<K> thắng bản nháp chuan-bi-<K>)."""
    import glob
    ra: List[str] = []
    for mau in (os.path.join(goc, "CHANNEL", "*", "kenh.yaml"),
                os.path.join(goc, "workspace", "chuan-bi-*", "CHANNEL", "*", "kenh.yaml")):
        for d in sorted(glob.glob(mau)):
            k = os.path.basename(os.path.dirname(d))
            if k.startswith("_") or k in ra:
                continue
            try:
                if thiet_lap_bat(k, goc):
                    ra.append(k)
            except OSError:
                pass
    return ra


def _sua_yaml(kenh: str, ham, goc: str = GOC_TOOL) -> str:
    d = nuoi.duong_kenh_yaml(kenh, goc)
    if not d:
        return ""
    with open(d, "rb") as tep:
        b = tep.read()
    moi = ham(b)
    if moi == b:
        return d
    with open(d + ".tam", "wb") as tep:
        tep.write(moi)
    os.replace(d + ".tam", d)
    return d


def tat_thiet_lap(kenh: str, goc: str = GOC_TOOL) -> str:
    """Ghi `thiet_lap_kenh: false` vào kenh.yaml. Trả đường tệp, "" nếu không ghi được."""
    d = _sua_yaml(kenh, lambda b: re.sub(rb"(?m)^thiet_lap_kenh:[ \t]*true[ \t]*(?=\r?$)", b"thiet_lap_kenh: false", b), goc)
    return d if d and _yaml_gia_tri(d, "thiet_lap_kenh").lower() == "false" else ""


def ghi_ten_yaml(kenh: str, ten: str, goc: str = GOC_TOOL) -> bool:
    """`ten:` còn là tên tạm "(…) — mô tả" thì thay phần tên thật vào, giữ phần sau " — " (nuôi trang chủ dùng phần trước)."""
    d = nuoi.duong_kenh_yaml(kenh, goc)
    cu = _yaml_gia_tri(d, "ten") if d else ""
    if not d or not (cu.startswith("(") or not cu) or '"' in ten or "\n" in ten:
        return False
    sau = cu.split(" — ", 1)[1] if " — " in cu else ""
    moi = ('ten: "{0} — {1}"'.format(ten, sau) if sau else 'ten: "{0}"'.format(ten)).encode("utf-8")
    _sua_yaml(kenh, lambda b: re.sub(rb"(?m)^ten:[^\r\n]*", lambda _m: moi, b, count=1), goc)
    return True


# ═══════════════════════════ LỊCH CHO AGENT ═════════════════════════════════
def _co_chrome_portable(k: str, goc: str = GOC_TOOL) -> bool:
    return os.path.isfile(os.path.join(goc, "..", k, k + ".exe")) or os.path.isfile(os.path.join(goc, "..", k, k, k + ".exe"))


def kenh_den_luot(luc: float, dang_chay=(), goc: str = GOC_TOOL, ram=None, nang_ban=None) -> Tuple[List[str], Dict[str, str]]:
    """(kênh nên mở tiến trình con, {kênh: lý do bỏ qua}). Agent gọi mỗi ~10 phút.
    Một lúc chỉ MỘT phiên thiết lập trên máy (tuần tự); kênh đang được nuôi trang chủ thì đợi lượt nuôi nghỉ."""
    ly: Dict[str, str] = {}
    ung: List[str] = []
    dang = set(dang_chay) | {k for k in cac_kenh_bat(goc) if nuoi.chu_khoa(k, THU_MUC_KHOA_RIENG)}
    for k in cac_kenh_bat(goc):
        if k in dang:
            ly[k] = "đang thiết lập"
            continue
        so = doc_so(k)
        ok, r = quyet_dinh(so, luc, NGAN_SACH_PHIEN_PHUT)
        if ok and not _co_chrome_portable(k, goc):
            ok, r = False, "chưa có Chrome Portable {0}/{0}.exe".format(k)
        if ok and nuoi.chu_khoa(k):
            ok, r = False, "kênh đang có tiến trình khác giữ Chrome (nuôi trang chủ) — đợi lượt nghỉ"
        if ok:
            ung.append(k)
        else:
            ly[k] = r
    if not ung:
        return [], ly
    if dang:
        return [], dict(ly, **{k: "đang có phiên thiết lập kênh khác — tuần tự từng kênh" for k in ung})
    if CHO_KHE_NANG and (nang_ban if nang_ban is not None else nuoi.khe_nang_ban(goc)):
        return [], dict(ly, **{k: "khe nang của máy đang bận — nhường CPU" for k in ung})
    r = nuoi.duoc_mo_them(len(nuoi.cac_kenh_dang_nuoi()), ram_gb(ram))
    if r:
        return [], dict(ly, **{k: r for k in ung})
    # 04/10/2026: XOAY VÒNG — kênh lâu chưa thử nhất đi trước (giờ sửa nhật ký kênh). Trước đây luôn lấy kênh
    # đầu danh sách: TL4-T7-K2 bị hoãn mãi (gói chờ tải kẹt) chặn TL6-T7/TL6-T7-K2 đã sẵn sàng phía sau.
    def _lan_thu_cuoi(k: str) -> float:
        try:
            return os.path.getmtime(os.path.join(THU_MUC_SO, k + ".log"))
        except OSError:
            return 0.0
    ung.sort(key=_lan_thu_cuoi)
    return ung[:1], dict(ly, **{k: "xếp hàng sau {0}".format(ung[0]) for k in ung[1:]})


def ram_gb(ram):
    return nuoi.ram_trong_gb() if ram is None else ram


# ═══════════════════════════ JS ĐỌC TRẠNG THÁI ══════════════════════════════
_JS_CHUNG = r"""
const q = (s, r) => (r || document).querySelector(s);
const qa = (s, r) => [...(r || document).querySelectorAll(s)];
const hien = e => { if (!e || !e.isConnected) return false; const b = e.getBoundingClientRect(); if (b.width < 1 || b.height < 1) return false;
  const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && cs.display !== 'none'; };
const giaTri = e => !e ? null : ((e.tagName === 'INPUT' || e.tagName === 'TEXTAREA') ? e.value : (e.innerText || ''));
const dongCuoi = e => { if (!e) return null; const t = (e.innerText || '').split('\n').map(x => x.trim()).filter(x => x); return t.length ? t[t.length - 1] : ''; };
const anh = (host, theoNut) => { const h = q(host); if (!h) return null;
  const rm = qa('#remove-button', h).some(hien), src = [];
  qa('img', h).forEach(i => { if (i.src && hien(i)) src.push(i.src); });
  qa('image', h).forEach(i => { const u = i.getAttribute('href') || ''; if (u) src.push(u.length + ':' + u.slice(-30)); });
  return {co: theoNut ? rm : src.length > 0, src: src}; };
const chips = host => qa('ytcp-chip', q(host) || document.createElement('i')).map(c => (c.innerText || '').trim()).filter(x => x);
"""

_JS_HO_SO = "(() => {" + _JS_CHUNG + r"""
  const ten = q('ytcp-channel-editing-channel-name input'), handle = q('ytcp-channel-editing-channel-handle input');
  const mt = q('#description-textbox [role=textbox]') || q('ytcp-social-suggestions-textbox [role=textbox]');
  if (!ten || !handle || !mt) return null;
  const pub = q('ytcp-button#publish-button button') || q('ytcp-button#publish-button');
  const tat = e => !!e && (e.hasAttribute('disabled') || e.getAttribute('aria-disabled') === 'true' || (e.closest('ytcp-button') || e).hasAttribute('disabled') || (e.closest('ytcp-button') || e).getAttribute('aria-disabled') === 'true');
  return {ten: giaTri(ten), handle: giaTri(handle), mo_ta: giaTri(mt), banner: anh('ytcp-banner-upload', true), logo: anh('ytcp-profile-image-upload', false),
          hinh_mo: anh('ytcp-video-watermark-upload', true), url_kenh: giaTri(q('input.ytcpChannelUrlReadonlyInput') || q('ytcp-channel-url input')),
          xuat_ban_tat: tat(pub)};
})()"""

_JS_LOI_O = "((host) => {" + _JS_CHUNG + r"""
  const h = q(host); if (!h) return null;
  const box = q('ytcp-form-input-container', h) || h;
  const loi = [];
  qa('#error-message, .error-message, [id*=error], [class*=error], [role=alert], ytcp-form-error', h).forEach(e => { const t = (e.innerText || '').trim(); if (t && hien(e)) loi.push(t); });
  const inp = q('input', h);
  const dong = (h.innerText || '').split('\n').map(x => x.trim()).filter(x => x);
  return {invalid: box.hasAttribute('invalid') || (inp && inp.getAttribute('aria-invalid') === 'true') || !!q('[invalid]', h),
          loi: [...new Set(loi)].join(' | '), thong_bao: dong.length ? dong[dong.length - 1] : '', chu: (h.innerText || '').trim().slice(0, 400)};
})"""

#: Chữ thông báo (toast/snackbar) + ô đang báo lỗi trên trang (sau Xuất bản).
_JS_LOI_XUAT_BAN = "(() => {" + _JS_CHUNG + r"""
  const ra = [];
  qa('ytcp-toast, tp-yt-paper-toast, ytcp-snackbar, yt-notification-action-renderer, #toast, [role=alert], #error-message, ytcp-form-error').forEach(e => {
    const t = (e.innerText || '').trim(); if (t && hien(e)) ra.push(t); });
  qa('[invalid] #error-message, ytcp-form-input-container[invalid] [id*=error]').forEach(e => { const t = (e.innerText || '').trim(); if (t && hien(e)) ra.push(t); });
  return [...new Set(ra)].join(' | ').slice(0, 400);
})()"""

_JS_HOP_THOAI ="(() => {" + _JS_CHUNG + r"""
  const ds = qa('tp-yt-paper-dialog, ytcp-dialog, ytcp-confirmation-dialog, [role=dialog], [role=alertdialog]').filter(hien);
  // 14/10: bỏ hộp KHÔNG có chữ (vỏ `ytcp-dialog` của hộp chọn video thẻ Trang chủ vẫn «hiện» khi đã đóng)
  return ds.map(d => (d.innerText || '').trim().slice(0, 600)).filter(x => x).join('\n----\n');
})()"""

_JS_CAI_DAT_KENH = "(() => {" + _JS_CHUNG + r"""
  const qg = q('#country-of-residence-select');
  const vb = qa('#keywords-container ytcp-free-text-chip-bar ytcp-chip, ytcp-free-text-chip-bar ytcp-chip').map(c => (c.innerText || '').trim()).filter(x => x);
  if (!qg) return null;
  return {quoc_gia: dongCuoi(qg), tu_khoa: vb, dem: (q('#keywords-container') ? ((q('#keywords-container').innerText.match(/\d+\s*\/\s*\d+/) || [''])[0]) : '')};
})()"""

_JS_MAC_DINH_CO_BAN = "(() => {" + _JS_CHUNG + r"""
  const tc = q('#tags-container'); if (!tc) return null;
  return {the: qa('ytcp-chip', tc).map(c => (c.innerText || '').trim()).filter(x => x),
          che_do: dongCuoi(q('#privacy-select'))};
})()"""

_JS_MAC_DINH_NANG_CAO = "(() => {" + _JS_CHUNG + r"""
  const dm = q('#category-select'), nv = q('#audio-language'), md = q('#metadata-language');
  if (!dm || !nv || !md) return null;
  return {danh_muc: dongCuoi(dm), ngon_ngu_video: dongCuoi(nv), ngon_ngu_mo_ta: dongCuoi(md)};
})()"""

_JS_DS_PHAT = "(() => {" + _JS_CHUNG + r"""
  const s = q('ytcp-playlist-section-content') || q('ytcp-playlist-section'); if (!s) return null;
  const ten = qa('ytcp-playlist-row h3.playlist-title a, ytcp-playlist-row a.playlist-title-link, ytcp-playlist-row #video-title', s).map(a => (a.innerText || '').trim()).filter(x => x);
  const dem = (((s.innerText || '').match(/\d+\s*[–-]\s*\d+\s*\/\s*\d+/) || [''])[0]) || '';
  return {ten: [...new Set(ten)], chu: (s.innerText || '').slice(0, 3000), phan_trang: dem};
})()"""


_JS_NGON_NGU = """(() => ({lang: document.documentElement.lang || '', chu: (document.body ? document.body.innerText : '').slice(0, 5000)}))()"""

#: Phần tử bấm được có NHÃN (aria-label) hoặc chữ khớp regex (tuỳ chọn: chỉ trong hộp thoại); trả tâm điểm.
_JS_THEO_NHAN = """((reSrc, loaiSrc, sel) => { const Y = window.__yd, re = new RegExp(reSrc, 'i'), loai = loaiSrc ? new RegExp(loaiSrc, 'i') : null; const ra = [];
  for (const e of Y.qsa(Y.goc(), sel || 'button, [role=button], a, li, [role=option], [role=radio], [role=menuitem], [role=listitem], [role=combobox], label')) {
    if (!Y.hien(e)) continue; const nh = (e.getAttribute('aria-label') || '') + ' ' + Y.chuan(e.innerText || ''); if (!re.test(nh) || (loai && loai.test(nh)) || nh.length > 160) continue;
    const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4) continue;
    ra.push({chu: nh.trim().slice(0, 80), x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height}); }
  ra.sort((a, b) => (a.w * a.h - b.w * b.h)); return ra.slice(0, 5); })"""

#: Hộp menu đang mở (avatar → menu → danh sách ngôn ngữ): chữ từng hộp, để GHI NHẬT KÝ khi dò.
_JS_MENU_MO = """(() => { const Y = window.__yd; return Y.qsa(Y.goc(), 'tp-yt-iron-dropdown, ytcp-multi-page-menu, ytd-multi-page-menu-renderer, ytcp-popup-container, [role=menu], [role=listbox]')
  .filter(e => Y.hien(e)).map(e => Y.chuan(e.innerText).slice(0, 700)).filter(x => x); })()"""

#: Mục (trong menu đang mở) có chữ khớp regex: trả tâm điểm bấm + chữ. Chọn mục NGẮN nhất (sát lá nhất).
_JS_MUC_MENU = """((reSrc) => { const Y = window.__yd, re = new RegExp(reSrc, 'i'); const ra = [];
  for (const e of Y.qsa(Y.goc(), 'tp-yt-paper-item, tp-yt-paper-icon-item, ytd-compact-link-renderer, [role=menuitem], [role=option], [role=radio], a, ytcp-ve, yt-formatted-string, li')) {
    if (!Y.hien(e)) continue; const t = Y.chuan(e.innerText || e.textContent); if (!t || t.length > 80 || !re.test(t)) continue;
    const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4) continue;
    ra.push({chu: t, x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height}); }
  ra.sort((a, b) => (a.chu.length - b.chu.length) || (a.w * a.h - b.w * b.h)); return ra.slice(0, 5); })"""


# ═══════════════════════════ KIỂM THƯƠNG HIỆU (14/10/2026) ══════════════════
# `--kiem-thuong-hieu`: CHỈ ĐỌC — hình mờ (có? hiển thị lúc nào), video giới thiệu kênh cho người CHƯA đăng ký + video
# nổi bật cho người đăng ký quay lại (Tuỳ chỉnh → Thẻ Trang chủ), số danh sách phát → `<K>.thuong-hieu.json` + ảnh.
# Kèm `--dat-hinh-mo`: kênh THIẾU hình mờ thì đặt (đường `hinh_mo` có sẵn), hiển thị TOÀN BỘ video, đọc lại sau Xuất
# bản. Kênh chính: KHÔNG đụng tên/handle/mô tả/logo/banner (so trước–sau trên trang, lệch → bỏ thay đổi, không Xuất bản).
#: Nút chọn thời gian hiển thị hình mờ (đo 04/10 trên Studio: id/name của tp-yt-paper-radio-button) → mã.
THOI_GIAN_HINH_MO = {"entire-video-radio-button": "toan_bo", "ENTIRE": "toan_bo", "end-of-video-radio-button": "cuoi", "END": "cuoi",
                     "custom-start-time-radio-button": "tuy_chinh", "START": "tuy_chinh"}
PHUT_CAM_GIO_TRON = 5                     # :55–:05 — agent mở phiên đăng quanh giờ tròn, không chen Chrome kênh lúc đó
DU_KIEN_KIEM_PHUT, DU_KIEN_DAT_PHUT, DU_KIEN_TRANG_CHU_PHUT = 8, 14, 15
RE_TRAILER = r"(giới thiệu kênh|người chưa đăng ký|channel trailer|haven.?t subscribed|予告編|登録していない)"
RE_NOI_BAT = r"(video nổi bật|người đăng ký quay lại|featured video|returning subscriber|おすすめ動画|リピーター)"
RE_NUT_THEM = r"^(\+\s*)?(thêm|add|追加)$"
RE_NUT_CO_VIDEO = r"^(thay đổi|xóa|xoá|gỡ|change|remove|変更|削除)$"
RE_TAB_TRANG_CHU = r"(thẻ trang chủ|home tab|ホーム\s?タブ|홈 탭)"


def khung_gio_tron(luc: float, du_kien_phut: float = 0.0, bien: int = PHUT_CAM_GIO_TRON) -> str:
    """"" nếu cả quãng [luc, luc + du_kien_phut] nằm NGOÀI phút :55–:05; không thì lý do (hàm thuần)."""
    t = time.localtime(luc)
    p = t.tm_min + t.tm_sec / 60.0
    if p < bien or p + max(0.0, du_kien_phut) >= 60 - bien:
        return "sát giờ tròn (phút :{0:02d}–:{1:02d}, agent mở phiên đăng) — đợi".format(60 - bien, bien)
    return ""


def doc_hinh_mo(du: Any) -> Dict[str, Any]:
    """Kết quả `_JS_HINH_MO` → {co: True/False/None, thoi_gian: toan_bo|cuoi|tuy_chinh|""|None, nhan}.
    co=None = KHÔNG đọc được ô (không bao giờ coi là thiếu). Có = nút Xoá của ô hiện; thiếu = chỉ có nút Tải lên."""
    if not isinstance(du, dict) or not du.get("thay_o"):
        return {"co": None, "thoi_gian": None, "nhan": ""}
    if du.get("nut_xoa"):
        co = True
    elif du.get("nut_tai_len"):
        co = False
    else:
        return {"co": None, "thoi_gian": None, "nhan": ""}
    chon = [r for r in (du.get("radio") or []) if isinstance(r, dict) and r.get("chon")]
    tg, nhan = ("", "")
    if co and len(chon) == 1:
        r = chon[0]
        tg = THOI_GIAN_HINH_MO.get(str(r.get("id") or "")) or THOI_GIAN_HINH_MO.get(str(r.get("name") or "").upper(), "")
        nhan = str(r.get("chu") or "")
    return {"co": co, "thoi_gian": tg if co else None, "nhan": nhan}


def can_dat_hinh_mo(hm: Any) -> Tuple[bool, str]:
    """Có ĐẶT hình mờ không: CHỈ khi đọc chắc chắn ô đang trống. Không đọc được → KHÔNG đặt (không đoán)."""
    co = (hm or {}).get("co") if isinstance(hm, dict) else None
    if co is None:
        return False, "không đọc được ô hình mờ — không đặt"
    if co:
        return False, "đã có hình mờ — không làm gì"
    return True, "thiếu hình mờ"


def dem_ds_phat(du: Any) -> Optional[int]:
    """Số danh sách phát từ `_JS_DEM_DS_PHAT`: tổng trong chữ phân trang («1–30 / 45», «1 – 3 trên tổng số 3»,
    «1～3/3 件»), không có thì số hàng; trang trống (nút «Danh sách phát mới» giữa trang) = 0; không đọc được = None."""
    if not isinstance(du, dict):
        return None
    hang = max(int(du.get("hang") or 0), len(du.get("ten") or []))
    m = None
    for m in re.finditer(r"(\d+)\s*[–\-~～]\s*(\d+)\D{1,30}?(\d+)", str(du.get("chan") or "")):
        pass
    if m:
        return max(int(m.group(3)), hang)
    if hang:
        return hang
    return 0 if du.get("trong") else None


def doc_tieu_diem(chu: Any, trang_da_dung: bool = False) -> Dict[str, Dict[str, Any]]:
    """Chữ trang «Thẻ Trang chủ» → {trailer, noi_bat}: {co: True/False/None, dong: [...]}. Mỗi mục: dòng tiêu đề khớp
    (`RE_TRAILER` / `RE_NOI_BAT`), rồi các dòng tới tiêu đề kế; có nút «Thêm» mà không có «Thay đổi/Xoá» = CHƯA có video;
    có mục mà không có nút «Thêm» = CÓ. Không thấy tiêu đề: trang đã dựng xong (`trang_da_dung`: công tắc Thẻ Trang chủ +
    khung bố cục đã hiện — Studio 14/10 không còn khối «Tiêu điểm video») = KHÔNG có; chưa chắc trang dựng = None."""
    dong = [" ".join(x.split()) for x in str(chu or "").split("\n") if x.strip()]
    vt = {}
    for i, d in enumerate(dong):
        if len(d) > 120:
            continue
        for k, mau in (("trailer", RE_TRAILER), ("noi_bat", RE_NOI_BAT)):
            if k not in vt and re.search(mau, d, re.I):
                vt[k] = i
    ra: Dict[str, Dict[str, Any]] = {}
    for k in ("trailer", "noi_bat"):
        if k not in vt:
            ra[k] = {"co": False if trang_da_dung else None, "dong": []}
            continue
        sau = [v for v in vt.values() if v > vt[k]]
        doan = dong[vt[k] + 1: min(sau) if sau else vt[k] + 8][:8]
        them = any(re.match(RE_NUT_THEM, d, re.I) for d in doan)
        co_vid = any(re.match(RE_NUT_CO_VIDEO, d, re.I) for d in doan)
        ra[k] = {"co": True if (co_vid or not them) else False, "dong": [dong[vt[k]]] + doan}
    return ra


def lech_ho_so(truoc: Any, sau: Any) -> List[str]:
    """Mục nào của trang Hồ sơ (`_JS_HO_SO`) đã LỆCH giữa hai lần đọc (ngoài hình mờ): tên, handle, mô tả, logo, banner."""
    a, b = truoc if isinstance(truoc, dict) else {}, sau if isinstance(sau, dict) else {}
    if not a or not b:
        return ["không đọc được trang Hồ sơ"]
    ra = [m for m in ("ten", "handle") if chuan(a.get(m)) != chuan(b.get(m))]
    if not mo_ta_giong(a.get("mo_ta"), b.get("mo_ta")):
        ra.append("mo_ta")
    for m in ("logo", "banner"):
        x, y = a.get(m) or {}, b.get(m) or {}
        if bool(x.get("co")) != bool(y.get("co")) or (x.get("src") and y.get("src") and x.get("src") != y.get("src")):
            ra.append(m)
    return ra


# ── trang chủ kênh (14/10, chủ duyệt): bật Thẻ Trang chủ + video giới thiệu (người CHƯA đăng ký) + video nổi bật (người
# đăng ký quay lại) + phần «Video phổ biến»; mô tả kênh cho kênh đang để TRỐNG. Mục đích: thêm người đăng ký (nghẽn YPP).
TUOI_TOI_THIEU_NGAY = 7                   # video giới thiệu: đăng đủ 7 ngày (số hiển thị/bấm đã chín)
DAI_TOI_THIEU_GIAY = 181                  # video DÀI (Shorts <= 180 giây)
SO_UNG_VIEN_TRA = 6                       # tra «Công khai» trên Studio tối đa ngần này ứng viên đầu bảng
MO_TA_KENH_TOI_THIEU, MO_TA_KENH_TOI_DA = 150, 300
RE_PHAN_PHO_BIEN = r"(video phổ biến|popular videos|人気の動画|인기 동영상)"


def giay_dai(s: Any) -> Optional[int]:
    """«13:05» / «1:02:03» → giây; không đọc được → None (hàm thuần)."""
    p = str(s or "").strip().split(":")
    if not 2 <= len(p) <= 3 or not all(x.strip().isdigit() for x in p):
        return None
    g = 0
    for x in p:
        g = g * 60 + int(x)
    return g


def ty_le_so(s: Any) -> float:
    """«5.29%» / «5,29 %» → 0.0529; trống/lạ → 0.0."""
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(s or ""))
    return float(m.group(1).replace(",", ".")) / 100.0 if m else 0.0


def so_nguyen(s: Any) -> int:
    """«35,330» / «35330» / «» → số nguyên (0 nếu không đọc được)."""
    d = re.sub(r"[^\d]", "", str(s or "").split(".")[0])
    return int(d) if d else 0


def xep_video_gioi_thieu(hang, ngay_bat_dau: Any, hom_nay, toi_thieu_ngay: int = TUOI_TOI_THIEU_NGAY,
                         dai_toi_thieu: int = DAI_TOI_THIEU_GIAY) -> List[Dict[str, Any]]:
    """Hàng `chi-so/bang-tom-tat.csv` (csv.DictReader) → ứng viên video giới thiệu, TỐT NHẤT trước theo
    «Lượt hiển thị» × «Tỷ lệ bấm» (≈ lượt bấm từ hiển thị). Chỉ video DÀI, đăng từ `ngay_bat_dau` (kenh.yaml), đủ
    `toi_thieu_ngay` tuổi tính tới `hom_nay` (date), có lượt bấm > 0; trùng mã giữ một. Hàm thuần."""
    try:
        moc = datetime.strptime(str(ngay_bat_dau or "").strip()[:10], "%Y-%m-%d").date() if ngay_bat_dau else None
    except ValueError:
        moc = None
    ra: Dict[str, Dict[str, Any]] = {}
    for h in hang or []:
        if not isinstance(h, dict):
            continue
        vid = str(h.get("Mã video") or "").strip()
        try:
            ngay = datetime.strptime(str(h.get("Ngày đăng") or "").strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        dai = giay_dai(h.get("Dài"))
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) or dai is None or dai < dai_toi_thieu:
            continue
        if (moc and ngay < moc) or (hom_nay - ngay).days < toi_thieu_ngay:
            continue
        ht, tl = so_nguyen(h.get("Lượt hiển thị")), ty_le_so(h.get("Tỷ lệ bấm"))
        diem = round(ht * tl, 1)
        if diem <= 0 or (vid in ra and ra[vid]["diem"] >= diem):
            continue
        ra[vid] = {"vid": vid, "tieu_de": str(h.get("Tiêu đề") or "").strip(), "ngay": ngay.isoformat(), "dai": dai,
                   "hien_thi": ht, "ty_le": tl, "diem": diem}
    return sorted(ra.values(), key=lambda x: (-x["diem"], -x["hien_thi"], x["vid"]))


def chon_gioi_thieu(ung_vien, loai: Dict[str, str]) -> Tuple[Optional[dict], Optional[dict], List[str]]:
    """(video giới thiệu, video nổi bật, ghi chú bỏ): hai ứng viên ĐẦU BẢNG mà Studio đọc CHẮC là «cong_khai» (`loai`:
    mã → loại hàng của `MayDangDom.tra_kenh`). Không thấy / riêng tư / hẹn giờ / không rõ → bỏ qua, ghi lý do. Hàm thuần."""
    chon: List[dict] = []
    bo: List[str] = []
    for u in ung_vien or []:
        if len(chon) >= 2:
            break
        lo = (loai or {}).get(u.get("vid"))
        if lo == "cong_khai":
            chon.append(u)
        else:
            bo.append("{0} «{1}»: {2}".format(u.get("vid"), str(u.get("tieu_de") or "")[:40],
                                            "không thấy trên Studio" if not lo else "Studio: " + str(lo)))
    return (chon[0] if chon else None), (chon[1] if len(chon) > 1 else None), bo


def co_phan_pho_bien(ten_phan) -> bool:
    """Bố cục trang chủ (danh sách tên phần / chữ) đã có phần «Video phổ biến» chưa."""
    ds = [ten_phan] if isinstance(ten_phan, str) else list(ten_phan or [])
    return any(re.search(RE_PHAN_PHO_BIEN, str(x or ""), re.I) for x in ds)


#: Mục của menu «Thêm phần kênh» (đo 14/10: `tp-yt-paper-item[test-id=SHELF_TYPE_…]`, mờ = phần đã có).
RE_MUC_TRAILER = r"^(video giới thiệu kênh|channel trailer|チャンネル予告編)"
RE_MUC_NOI_BAT = r"^(video nổi bật|featured video|おすすめ動画)"
RE_MUC_PHO_BIEN = r"^(video phổ biến|popular videos|人気の動画)$"
RE_NHAN_TIEU_DE = r"(tiêu đề video|video title|動画のタイトル)\s*[:：]?\s*"


def _tieu_diem(ds: Any) -> Dict[str, Any]:
    """Các bản `ytcp-spotlight-*-video-item` → {co, tieu_de, ma}: item HIỆN = đã đặt; tiêu đề = chữ sau «Tiêu đề video»."""
    hien = [x for x in (ds or []) if isinstance(x, dict) and x.get("hien")]
    if not hien:
        return {"co": False, "tieu_de": "", "ma": []}
    chu = str(hien[0].get("chu") or "")
    m = re.search(RE_NHAN_TIEU_DE + r"(.+)$", chu, re.I)
    return {"co": True, "tieu_de": (m.group(2) if m else chu).strip(), "ma": list(hien[0].get("ma") or [])}


def tom_trang_chu(du: Any) -> Dict[str, Any]:
    """Bản đọc `_JS_BO_CUC_TC` → {bat (None = không đọc được công tắc), trailer, noi_bat ({co, tieu_de, ma}), phan (tên các
    phần bố cục đang hiện, bỏ «(số)» + thời lượng), pho_bien, them_tat, hop_chon}. Hàm thuần."""
    du = du if isinstance(du, dict) else {}
    phan = []
    for x in du.get("phan") or []:
        if not isinstance(x, dict) or not x.get("hien"):
            continue
        chu = str(x.get("chu") or "").strip()
        m = re.match(r"^(.*?)\s*\(\d+\)", chu)
        phan.append((m.group(1) if m else chu[:40]).strip())
    them = du.get("them") if isinstance(du.get("them"), dict) else None
    return {"bat": du.get("bat") if isinstance(du.get("bat"), bool) else None, "trailer": _tieu_diem(du.get("trailer")),
            "noi_bat": _tieu_diem(du.get("noi_bat")), "phan": phan, "pho_bien": co_phan_pho_bien(phan),
            "them_tat": (them or {}).get("tat") if them else None, "hop_chon": bool(du.get("hop_chon"))}


def khop_tieu_de(a: Any, b: Any) -> bool:
    """Tiêu đề Studio hiện ↔ tiêu đề mong: giống sau chuẩn hoá, hoặc một bên bị cắt «…» mà phần đầu (>= 20 ký tự) trùng."""
    x, y = (chuan(s).rstrip("….").strip() for s in (a, b))
    if not x or not y:
        return False
    if x == y:
        return True
    ngan, dai = sorted((x, y), key=len)
    return len(ngan) >= 20 and dai.startswith(ngan)


def chon_muc_phan(ds: Any, re_chu: str) -> Optional[dict]:
    """Mục menu «Thêm phần kênh» khớp `re_chu` (chữ đã chuẩn): mục đầu tiên khớp, kèm `tat` để nơi gọi quyết. Hàm thuần."""
    for x in ds or []:
        if isinstance(x, dict) and re.search(re_chu, chuan(x.get("chu")), re.I):
            return x
    return None


def chon_the_video(the: Any, vid: str) -> Optional[dict]:
    """Thẻ trong hộp «Chọn một video cụ thể» có ĐÚNG mã `vid` (ảnh thu nhỏ `/vi/<mã>/`), đang hiện, không mờ. Nhiều hơn
    một thẻ trùng mã = không rõ → None (không đoán). Hàm thuần."""
    ds = [x for x in (the or []) if isinstance(x, dict) and vid and x.get("ma") == vid and x.get("hien") and not x.get("tat")]
    return ds[0] if len(ds) == 1 else None


def lam_sach_mo_ta_kenh(chu: Any) -> str:
    """Trả lời LLM → mô tả kênh: bỏ rào ```/ngoặc kép bao ngoài, gộp dòng trống thừa, cắt khoảng trắng đầu/cuối dòng."""
    s = unicodedata.normalize("NFC", str(chu or "")).replace("\r\n", "\n").replace("\r", "\n").strip()
    s = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", s).strip()
    if len(s) >= 2 and s[0] + s[-1] in ('""', "「」", "『』", "“”"):
        s = s[1:-1].strip()
    s = "\n".join(d.strip() for d in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def do_dai_mo_ta(chu: Any) -> int:
    """Số ký tự mô tả (không tính xuống dòng)."""
    return len(str(chu or "").replace("\n", ""))


def kiem_mo_ta_kenh(chu: Any, toi_thieu: int = MO_TA_KENH_TOI_THIEU, toi_da: int = MO_TA_KENH_TOI_DA) -> List[str]:
    """Lỗi của mô tả kênh tiếng Nhật ([] = đạt): độ dài, phải có kana, không link/email/@handle/markdown,
    không dấu < > (Studio từ chối). Hàm thuần."""
    s = str(chu or "")
    loi = []
    n = do_dai_mo_ta(s)
    if not toi_thieu <= n <= toi_da:
        loi.append("dài {0} ký tự (cần {1}–{2})".format(n, toi_thieu, toi_da))
    if not re.search(r"[぀-ヿ]", s):
        loi.append("không phải tiếng Nhật (không có kana)")
    if re.search(r"https?://|www\.|\S+@\S+\.\w+|(^|\s)@\w", s):
        loi.append("có link / email / @handle")
    if re.search(r"[<>]", s):
        loi.append("có dấu < > (Studio từ chối)")
    if re.search(r"\*\*|^#+\s|```", s, re.M):
        loi.append("có markdown")
    return loi


def loi_nhac_mo_ta_kenh(ten_kenh: str, kh: Dict[str, Any], tieu_de_thang, mau) -> str:
    """Lời nhắc viết MÔ TẢ KÊNH (tiếng Nhật, 150–300 ký tự) theo bản sắc kênh (kenh.yaml `ten`/`luat_chon`/`giong_van`),
    tiêu đề video THẮNG của chính kênh và mô tả THẬT của kênh anh em (bắt giọng, không chép chữ). Hàm thuần."""
    vd = "\n".join("- {0}".format(" / ".join(str(m).split("\n"))[:400]) for m in (mau or []) if str(m or "").strip())
    td = "\n".join("- {0}".format(str(t)[:120]) for t in (tieu_de_thang or []) if str(t or "").strip())
    return (
        "You write the YouTube CHANNEL DESCRIPTION («概要») of a Japanese psychology channel. Reply with the description text only.\n"
        "CHANNEL FACTS\n- current YouTube channel name (if you name the channel, use EXACTLY this; never invent another name): {ten}\n"
        "- identity / angle (internal note, may be partly Vietnamese — do not translate it literally): {goc}\n"
        "- what the channel is about: {luat}\n- voice and tone: {giong}\n"
        "- the channel's best-performing video titles (the promise viewers already click on):\n{td}\n"
        "{vd_}"
        "WRITE: Japanese, {a}-{b} characters, 2-4 short paragraphs (line breaks allowed). First sentence = who the channel is for + the "
        "promise (understanding yourself and the people around you through psychology / brain science, explained gently). Then what "
        "viewers get from the videos, then a warm, natural invitation to subscribe (チャンネル登録). Polite です/ます, calm and warm, no hype, "
        "no exaggerated claims, no medical / therapeutic advice. No URLs, no email, no @handles, no hashtags, no emoji, no markdown, no < or >.\n"
    ).format(ten=ten_kenh or "(unknown)", goc=str(kh.get("ten") or "")[:200], luat=str(kh.get("luat_chon") or "(none)")[:700],
             giong=str(kh.get("giong_van") or "")[:300], td=td or "- (none)", a=MO_TA_KENH_TOI_THIEU, b=MO_TA_KENH_TOI_DA,
             vd_=("DESCRIPTIONS OF SIBLING CHANNELS (match their tone and care, NOT their wording):\n" + vd + "\n") if vd else "")


_JS_HINH_MO = "(() => {" + _JS_CHUNG + r"""
  const h = q('ytcp-video-watermark-upload'); if (!h) return null;
  try { h.scrollIntoView({block: 'center'}); } catch (e) {}
  const nut = id => qa('ytcp-button#' + id, h).some(hien);
  const radio = qa('tp-yt-paper-radio-button', h).filter(hien).map(r => ({id: r.id || '', name: r.getAttribute('name') || '',
    chu: (r.innerText || '').trim().slice(0, 60),
    chon: r.hasAttribute('checked') || r.getAttribute('aria-checked') === 'true' || r.classList.contains('iron-selected')}));
  return {thay_o: true, nut_xoa: nut('remove-button'), nut_thay: nut('replace-button'), nut_tai_len: nut('upload-button'),
          anh: qa('img', h).filter(i => hien(i) && i.src).length, radio: radio, chu: (h.innerText || '').trim().slice(0, 300)};
})()"""

_JS_TRANG_CHU = "(() => {" + _JS_CHUNG + r"""
  const tab = qa('tp-yt-paper-tab').filter(hien).map(t => ({chu: (t.innerText || '').trim().slice(0, 40),
    chon: t.classList.contains('iron-selected') || t.getAttribute('aria-selected') === 'true'}));
  const ds = qa('*').filter(e => /featured|trailer|spotlight/i.test(e.tagName) && hien(e)).slice(0, 30).map(e => ({tag: e.tagName.toLowerCase(),
    id: e.id || '', chu: (e.innerText || '').trim().slice(0, 300),
    nut: qa('ytcp-button, button', e).filter(hien).map(b => ((b.innerText || '').trim() || b.getAttribute('aria-label') || '').slice(0, 40)).filter(x => x).slice(0, 8)}));
  const goc = q('ytcp-channel-editing-sections-tab') || q('ytcp-channel-editing-layout') || q('#main') || document.body;
  const sh = q('ytcp-switch#home-tab-enabled-switch'), sw = sh ? (q('[role=switch]', sh) || sh) : null;
  const ac = sw ? sw.getAttribute('aria-checked') : null;
  return {url: location.href, tab: tab, ds: ds, chu: (goc.innerText || '').slice(0, 5000), ke: !!q('ytcp-shelves-section'),
          bat: sw ? (ac !== null ? ac === 'true' : sh.hasAttribute('checked')) : null, cong_tac: sw ? {aria_checked: ac, checked: sh.hasAttribute('checked')} : null};
})()"""

_JS_DEM_DS_PHAT = "(() => {" + _JS_CHUNG + r"""
  const s = q('ytcp-playlist-section-content') || q('ytcp-playlist-section'); if (!s) return null;
  const hang = qa('ytcp-playlist-row', s).filter(hien).length;
  const ten = qa('ytcp-playlist-row h3.playlist-title a, ytcp-playlist-row a.playlist-title-link, ytcp-playlist-row #video-title', s).map(a => (a.innerText || '').trim()).filter(x => x);
  const ft = q('ytcp-table-footer', s) || q('ytcp-table-footer');
  const t = (s.innerText || '').trim();
  return {hang: hang, ten: [...new Set(ten)].slice(0, 60), chan: ft ? (ft.innerText || '').trim().slice(0, 200) : t.slice(-200),
          trong: hang === 0 && qa('ytcp-button.content-button', s).some(hien), duoi: t.slice(-200)};
})()"""

#: Nút «Xuất bản» của trang Tuỳ chỉnh đã mờ (true) / còn sáng (false) / không thấy (null).
_JS_XUAT_BAN_TAT = "(() => {" + _JS_CHUNG + r"""
  const b = q('ytcp-button#publish-button'); if (!b) return null; const i = q('button', b) || b;
  return [b, i].some(e => e.hasAttribute('disabled') || e.getAttribute('aria-disabled') === 'true');
})()"""

#: Thẻ Trang chủ (đo 14/10 TL2-T7, thăm dò không lưu): công tắc `ytcp-switch#home-tab-enabled-switch button[role=switch]`
#: (aria-checked), nút `ytcp-button#add-section-button`, phần bố cục `ytcp-shelf-list-item`, tiêu điểm
#: `ytcp-spotlight-trailer-video-item` / `ytcp-spotlight-featured-video-item` (có sẵn trong DOM, ẩn khi chưa đặt).
_JS_BO_CUC_TC = "(() => {" + _JS_CHUNG + r"""
  const sw = q('ytcp-switch#home-tab-enabled-switch button[role=switch]');
  const them = q('ytcp-button#add-section-button'), them_i = them ? (q('button', them) || them) : null;
  const ma = e => [...qa('img', e).map(i => i.src || ''), ...qa('[style*="/vi"]', e).map(x => x.getAttribute('style') || '')]
    .map(s => (s.match(/\/vi(?:_webp)?\/([A-Za-z0-9_-]{11})/) || [])[1]).filter(x => x);
  const muc = sel => qa(sel).map(e => ({tag: e.tagName.toLowerCase(), hien: hien(e), chu: (e.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 200), ma: ma(e)}));
  return {bat: sw ? sw.getAttribute('aria-checked') === 'true' : null, ke: !!q('ytcp-shelves-section'),
    them: them ? {hien: hien(them), tat: [them, them_i].some(e => e.hasAttribute('disabled') || e.getAttribute('aria-disabled') === 'true')} : null,
    phan: muc('ytcp-shelf-list-item'), trailer: muc('ytcp-spotlight-trailer-video-item'), noi_bat: muc('ytcp-spotlight-featured-video-item'),
    hop_chon: qa('ytcp-video-pick-dialog tp-yt-paper-dialog').some(hien)};
})()"""

#: Menu «Thêm phần kênh» đang mở: mục `tp-yt-paper-item` (chữ, test-id, mờ, tâm điểm).
_JS_MENU_PHAN = "(() => {" + _JS_CHUNG + r"""
  const lb = qa('tp-yt-paper-listbox, ytcp-text-menu').filter(hien).find(e => qa('tp-yt-paper-item[test-id^="SHELF_TYPE"]', e).length);
  if (!lb) return null;
  return qa('tp-yt-paper-item', lb).filter(hien).map(e => { const r = e.getBoundingClientRect();
    return {chu: (e.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 80), test_id: e.getAttribute('test-id') || '',
      tat: e.hasAttribute('disabled') || e.getAttribute('aria-disabled') === 'true', x: r.x + r.width / 2, y: r.y + r.height / 2}; });
})()"""

#: Hộp «Chọn một video cụ thể» (`ytcp-video-pick-dialog` — MỖI ô tiêu điểm một bản, chỉ bản đang HIỆN): thẻ
#: `ytcp-entity-card` — tiêu đề, MÃ video (ảnh nền `/vi/<mã>/`), mờ, tâm điểm.
_JS_THE_VIDEO = "(() => {" + _JS_CHUNG + r"""
  const dlg = qa('ytcp-video-pick-dialog').find(d => qa('tp-yt-paper-dialog', d).some(hien));
  if (!dlg) return null;
  return {tim: (q('input#search-yours', dlg) || {}).value || '', the: qa('ytcp-entity-card', dlg).filter(hien).slice(0, 60).map(c => {
    const r = c.getBoundingClientRect(), st = [...qa('[style*="/vi"]', c).map(x => x.getAttribute('style') || ''), ...qa('img', c).map(i => i.src || '')].join(' ');
    return {tieu_de: ((q('.title', c) || c).innerText || '').trim().slice(0, 160), ma: (st.match(/\/vi(?:_webp)?\/([A-Za-z0-9_-]{11})/) || [])[1] || '',
      tat: c.getAttribute('aria-disabled') === 'true', hien: true, x: r.x + r.width / 2, y: r.y + r.height / 2}; })};
})()"""


# ═══════════════════════════ ĐIỀU KHIỂN STUDIO ══════════════════════════════
def pref_dat_hl(pref: str, hl: str) -> str:
    """Giá trị cookie PREF của YouTube (`k=v&k=v`) với `hl=<hl>`: giữ MỌI cặp khoá khác, đổi/thêm `hl`. Hàm thuần."""
    cap = [c for c in str(pref or "").split("&") if c.strip()]
    ra, thay = [], False
    for c in cap:
        if c.split("=", 1)[0] == "hl":
            if not thay:
                ra.append("hl=" + hl)
            thay = True
        else:
            ra.append(c)
    if not thay:
        ra.append("hl=" + hl)
    return "&".join(ra)


#: đường dự phòng khi tài khoản Google đã đổi mà Studio chưa đổi (đo 04/10: 4 kênh TL1/2/3/5-T7 kẹt vi-VN)
CACH_NGON_NGU_MAC_DINH = ("tai_khoan", "hl", "cookie", "trinh_duyet")


class Studio:
    """Bọc `TrangStudio` (vm/cdp_studio.py) cho việc thiết lập kênh: tìm theo CSS (cấu trúc phần tử ổn định của
    Studio) rồi dự phòng theo CHỮ đa ngôn ngữ; bấm/gõ có xác minh như máy đăng."""

    def __init__(self, st, ghi, thu_muc_anh: str, ngu=time.sleep):
        self.st, self.ghi, self.thu_muc_anh, self.ngu = st, ghi, thu_muc_anh, ngu
        self.uc = ""
        self.debug = False                      # `--khong-luu`: chụp thêm ảnh giữa các bước để soi hộp cắt ảnh/hình mờ
        self.st.thu_muc_dom = thu_muc_anh

    # ── tìm / bấm / đọc ──
    def tim(self, css, chu=(), han: float = 6.0, cho_tat: bool = False, thu: int = 0):
        css = [css] if isinstance(css, str) else list(css)
        return self.st._tim_spec("tl:" + (css[0] if css else "|".join(chu)), {"chon": css, "chu": list(chu)},  # noqa: SLF001
                                 han, True, cho_tat, None, thu, ghi_du_phong=False)

    def bam(self, css, chu=(), han: float = 8.0, cho_tat: bool = False, hau_dieu_kien=None):
        pt = self.tim(css, chu, han, cho_tat)
        if not pt:
            raise LoiMuc("không thấy {0}".format(css if isinstance(css, str) else (list(css) or list(chu))[0]))
        return self.st.bam(pt, hau_dieu_kien=hau_dieu_kien, cho_tat=cho_tat)

    def co(self, css, chu=(), han: float = 0.0, cho_tat: bool = False) -> bool:
        return self.tim(css, chu, han, cho_tat) is not None

    def js(self, bt: str):
        r = self.st.js_tho(bt)
        nuoi.canh_tien_trien.danh_dau()
        return r

    def url(self) -> str:
        return self.st.url()

    def nhap(self, css, chu: str, nhieu_dong: bool = False, han: float = 8.0) -> str:
        """Bấm ô, Ctrl+A, gõ, ĐỌC LẠI so; lệch → thử 1 lần nữa → LoiMuc. Trả chữ đọc lại."""
        doc = ""
        for lan in range(2):
            pt = self.bam(css, han=han)
            if lan == 0:
                self.st._ctrl_a()                                   # noqa: SLF001
            else:
                self.st._js("chonHet", pt["id"])                    # noqa: SLF001
            if chu:
                self.st._chen(chu)                                  # noqa: SLF001
            else:
                self.st.phim("Delete")
            self.ngu(0.6)
            doc = self.st.doc_chu(self.tim(css, han=2, cho_tat=True)) or ""
            ok = mo_ta_giong(chu, doc) if nhieu_dong else chuan(chu) == chuan(doc)
            if ok:
                return doc
        raise LoiMuc("gõ vào {0} nhưng đọc lại lệch: {1!r}".format(css if isinstance(css, str) else css[0], str(doc)[:60]))

    def doi_hien(self, css, han: float = 10.0) -> bool:
        return self.tim(css, han=han, cho_tat=True) is not None

    # ── trang ──
    def hop_thoai(self) -> str:
        try:
            return str(self.js(_JS_HOP_THOAI) or "")
        except Exception:  # noqa: BLE001
            return ""

    def kiem_chan(self) -> None:
        try:
            chu_trang = str(self.js("document.body ? document.body.innerText.slice(0, 1500) : ''") or "")
        except Exception:  # noqa: BLE001
            chu_trang = ""
        ma = phat_hien_chan(self.url(), self.hop_thoai(), chu_trang)
        if ma:
            raise CanNguoi({"dang_xuat": "Chrome chưa đăng nhập / bị đăng xuất YouTube", "xac_minh": "YouTube đòi xác minh danh tính",
                            "captcha": "YouTube hiện CAPTCHA", "dong_y": "YouTube hiện trang đồng ý điều khoản",
                            "dien_thoai": "YouTube đòi xác minh số điện thoại"}.get(ma, ma))

    def mo(self, url: str, cho_css: str, han: float = 45.0) -> None:
        self.st.mo(url, han=60)
        self.kiem_chan()
        het = time.monotonic() + han
        while time.monotonic() < het:
            if self.co(cho_css):
                self._don_hop_chao()
                return
            self.kiem_chan()
            self.ngu(1.0)
        raise LoiMuc("trang {0} không dựng xong ({1})".format(url[-40:], cho_css))

    def _don_hop_chao(self) -> None:
        """19/10: kênh MỚI mở Studio lần đầu hiện «Chào mừng bạn đến với YouTube Studio» (ytcp-warm-welcome-dialog) che
        mọi nút — bấm «Tiếp tục» theo `hop_la` như máy đăng. Trang vừa tải xong nên hộp nào đang mở cũng không phải của
        luồng thiết lập. Hộp hiện trễ vài giây → dò thêm một lần."""
        for lan in range(2):
            try:
                if self.st.don_hop_la():
                    self.ngu(1.5)
            except Exception:  # noqa: BLE001 — không dẹp được thì luồng cũ xử lý như trước
                return
            if lan == 0:
                self.ngu(2.0)

    def chup(self, nhan: str) -> None:
        try:
            self.st.ghi_bang_chung(nhan)
        except Exception:  # noqa: BLE001
            pass

    def url_hoso(self) -> str:
        return "https://studio.youtube.com/channel/{0}/editing/profile".format(self.uc)

    def vao_studio(self) -> str:
        self.st.mo("https://studio.youtube.com/", han=60)
        self.ngu(3)
        self.kiem_chan()
        het = time.monotonic() + 40
        while time.monotonic() < het:
            m = re.search(r"/channel/(UC[\w-]{20,})", self.url())
            if m:
                self.uc = m.group(1)
                return self.uc
            self.kiem_chan()
            self.ngu(1.5)
        raise CanNguoi("không vào được Studio của kênh (URL {0}) — chưa đăng nhập hoặc tài khoản có nhiều kênh".format(self.url()[:80]))

    # ── ngôn ngữ giao diện Studio ──
    def doc_ngon_ngu(self, han: float = 25.0, dich: str = "vi") -> Tuple[bool, str, str]:
        """Đọc ngôn ngữ giao diện Studio hiện tại ở trang đang mở. Trả (đúng_ngôn_ngữ_đích, html_lang, trích_chữ)."""
        het = time.monotonic() + han
        du: dict = {}
        while True:
            try:
                du = self.js(_JS_NGON_NGU) or {}
            except Exception:  # noqa: BLE001
                du = {}
            # trang dựng xong khi thanh bên có chữ (>= 8 dòng) — chưa xong thì đợi
            if len((du.get("chu") or "").split("\n")) >= 8 or time.monotonic() >= het:
                break
            self.ngu(1.5)
        lang, chu = str(du.get("lang") or ""), str(du.get("chu") or "")
        return la_ngon_ngu_dich(dich, lang, chu), lang, " ".join(chu.split())[:160]

    def _bam_muc_menu(self, re_src: str, nhan: str, han: float = 8.0) -> str:
        """Bấm mục menu theo regex chữ (tâm điểm bằng chuột thật). Trả chữ mục đã bấm; không thấy → LoiMuc."""
        het = time.monotonic() + han
        while True:
            try:
                ds = self.js("({0})({1})".format(_JS_MUC_MENU, json.dumps(re_src, ensure_ascii=False))) or []
            except Exception:  # noqa: BLE001
                ds = []
            if ds:
                x = ds[0]
                self.st._bam_diem(round(x["x"], 1), round(x["y"], 1))      # noqa: SLF001
                return x["chu"]
            if time.monotonic() >= het:
                self.ghi("   menu hiện: {0}".format(" || ".join(self.js(_JS_MENU_MO) or [])[:500]))
                self.chup("ngon-ngu-khong-thay-" + nhan)
                raise LoiMuc("không thấy mục «{0}» trong menu".format(nhan))
            self.ngu(0.8)

    def _bam_nhan(self, re_src: str, nhan: str, loai: str = "", han: float = 8.0, sel: str = "") -> str:
        """Bấm phần tử theo NHÃN/chữ khớp regex (chuột thật vào tâm điểm). Không thấy → LoiMuc."""
        het = time.monotonic() + han
        while True:
            try:
                ds = self.js("({0})({1},{2},{3})".format(_JS_THEO_NHAN, json.dumps(re_src, ensure_ascii=False),
                                                       json.dumps(loai, ensure_ascii=False), json.dumps(sel))) or []
            except Exception:  # noqa: BLE001
                ds = []
            if ds:
                self.st._bam_diem(round(ds[0]["x"], 1), round(ds[0]["y"], 1))      # noqa: SLF001
                return ds[0]["chu"]
            if time.monotonic() >= het:
                self.chup("khong-thay-" + nhan.replace(" ", "-")[:30])
                raise LoiMuc("không thấy «{0}»".format(nhan))
            self.ngu(0.8)

    def _ngon_ngu_trinh_duyet(self, ghi, dich: str = "vi") -> None:
        """Đường dự phòng 1: menu ngôn ngữ của youtube.com (avatar → Ngôn ngữ → ngôn ngữ đích) = ghi cookie PREF của trình duyệt."""
        b = NGON_NGU_DICH.get(dich) or NGON_NGU_DICH[MA_NGON_NGU_MAC_DINH]
        self.st.mo("https://www.youtube.com/", han=60)
        self.ngu(4.0)
        self.kiem_chan()
        self._bam_nhan(RE_NUT_AVATAR, "avatar youtube", sel="button#avatar-btn, #avatar-btn, button[aria-label]")
        self.ngu(1.5)
        ghi("   youtube.com menu avatar: {0}".format(" || ".join(self.js(_JS_MENU_MO) or [])[:300]))
        self._bam_muc_menu(r"ngôn ngữ|language|言語|언어", "Ngôn ngữ")
        self.ngu(1.5)
        muc = self._bam_muc_menu(b["re_chon"], b["ten"])
        ghi("   youtube.com chọn «{0}»".format(muc))
        self.ngu(5.0)

    def _ngon_ngu_cookie(self, ghi, dich: str = "vi") -> None:
        """Đường dự phòng 2: đặt cookie PREF `hl=<đích>` (giữ cặp khác) trên .youtube.com bằng CDP. Chỉ đụng PREF."""
        b = NGON_NGU_DICH.get(dich) or NGON_NGU_DICH[MA_NGON_NGU_MAC_DINH]
        cdp, sid = self.st.cdp, self.st.sid
        ck = cdp.goi("Network.getCookies", {"urls": ["https://www.youtube.com/", "https://studio.youtube.com/"]}, sid=sid, han=15).get("cookies") or []
        pref = [c for c in ck if c.get("name") == "PREF"]
        ghi("   cookie PREF trước: {0}".format(" | ".join("{0}{1}={2}".format(c.get("domain"), c.get("path"), c.get("value")) for c in pref) or "(không có)"))
        goc = pref[0] if pref else {}
        moi = pref_dat_hl(goc.get("value", ""), b["html"])
        c = {"name": "PREF", "value": moi, "domain": ".youtube.com", "path": "/", "secure": True, "sameSite": "None"}
        if goc.get("expires", -1) and goc.get("expires", -1) > 0:
            c["expires"] = goc["expires"]
        else:
            c["expires"] = time.time() + 400 * 86400
        r = cdp.goi("Network.setCookie", c, sid=sid, han=15)
        ghi("   đặt PREF={0} → {1}".format(moi, r.get("success")))
        if not r.get("success"):
            raise LoiMuc("Network.setCookie không thành công")

    def _doc_dia_diem_menu(self, ghi) -> str:
        """Mở youtube.com → menu avatar → đọc dòng «Địa điểm: X» (vi/en/ja/ko). Menu để MỞ cho bước sau. Trả X ("" nếu không thấy)."""
        self.st.mo("https://www.youtube.com/", han=60)
        self.ngu(4.0)
        self.kiem_chan()
        self._bam_nhan(RE_NUT_AVATAR, "avatar youtube",
                       sel="button#avatar-btn, #avatar-btn, button[aria-label]")
        self.ngu(1.5)
        chu = " || ".join(self.js(_JS_MENU_MO) or [])
        m = re.search(r"(địa điểm|location|場所|위치)\s*[:：]\s*([^|\n]+?)(?=\s*(?:\|\||phím tắt|keyboard|キーボード|단축키|cài đặt|settings|設定|$))",
                      chu, re.I)
        return m.group(2).strip() if m else ""

    def _bam_muc_cuon(self, re_src: str, nhan: str, han: float = 8.0) -> str:
        """Như `_bam_muc_menu` nhưng CUỘN mục vào giữa trước khi bấm (danh sách nước dài, phải cuộn)."""
        js = ("((reSrc) => { const Y = window.__yd, re = new RegExp(reSrc, 'i');"
              " for (const e of Y.qsa(Y.goc(), 'tp-yt-paper-item, ytd-compact-link-renderer, [role=menuitem], [role=option], [role=radio], yt-formatted-string')) {"
              "  const t = Y.chuan(e.innerText || e.textContent); if (!t || t.length > 60 || !re.test(t)) continue;"
              "  e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4) continue;"
              "  return {chu: t, x: r.x + r.width / 2, y: r.y + r.height / 2}; } return null; })")
        het = time.monotonic() + han
        while True:
            try:
                x = self.js("({0})({1})".format(js, json.dumps(re_src, ensure_ascii=False)))
            except Exception:  # noqa: BLE001
                x = None
            if x:
                self.ngu(0.6)
                x = self.js("({0})({1})".format(js, json.dumps(re_src, ensure_ascii=False))) or x   # toạ độ sau khi cuộn xong
                self.st._bam_diem(round(x["x"], 1), round(x["y"], 1))      # noqa: SLF001
                return x["chu"]
            if time.monotonic() >= het:
                self.chup("khong-thay-" + nhan.replace(" ", "-")[:30])
                raise LoiMuc("không thấy «{0}» trong menu".format(nhan))
            self.ngu(0.8)

    def dat_dia_diem(self, ghi, gl: str, chi_doc: bool = False) -> dict:
        """05/10: ĐỊA ĐIỂM XEM = nước `gl` — làm ĐÚNG như người: youtube.com → avatar → «Địa điểm» → chọn nước, rồi mở lại
        menu ĐỌC LẠI «Địa điểm: X» (đã đăng nhập thì YouTube có thể lưu theo tài khoản — chỉ ghi cookie chưa chắc ăn).
        Hỏng đường menu → lùi về cookie PREF `gl` rồi vẫn đọc lại bằng menu. Làm MỘT LẦN trong thiết lập kênh (skill).
        Không đổi chữ giao diện → không hại máy đăng. Trả {ket: giong|doi|khac|hong|bo, hien_truoc, hien_sau}."""
        gl = str(gl or "").strip().upper()
        if not gl:
            ghi("địa điểm xem: không xác định được nước của kênh — bỏ qua")
            return {"ket": "bo", "hien_truoc": "", "hien_sau": ""}
        ten = TEN_NUOC.get(gl) or (gl,)
        re_ten = r"^(" + "|".join(re.escape(t) for t in ten) + r")$"
        khop = lambda s: any(t.lower() == str(s or "").strip().lower() for t in ten)   # noqa: E731
        try:
            truoc = self._doc_dia_diem_menu(ghi)
        except Exception as e:  # noqa: BLE001
            truoc = ""
            ghi("địa điểm xem: không đọc được menu ({0})".format(str(e)[:100]))
        ghi("địa điểm xem (menu youtube.com): {0!r} — đích {1}".format(truoc or "?", ten[0]))
        if khop(truoc):
            self.st.phim("Escape")
            return {"ket": "giong", "hien_truoc": truoc, "hien_sau": truoc}
        if chi_doc:
            self.st.phim("Escape")
            return {"ket": "khac", "hien_truoc": truoc, "hien_sau": truoc}
        try:
            if not truoc:
                raise LoiMuc("menu avatar không có dòng Địa điểm")
            self._bam_muc_menu(r"^(địa điểm|location|場所|위치)", "Địa điểm")
            self.ngu(1.5)
            chon = self._bam_muc_cuon(re_ten, ten[0])
            ghi("   youtube.com chọn địa điểm «{0}»".format(chon))
            self.ngu(4.0)
        except Exception as e:  # noqa: BLE001
            ghi("   đường menu hỏng ({0}) — lùi về cookie PREF gl={1}".format(str(e)[:100], gl))
            try:
                self.st.phim("Escape")
            except Exception:  # noqa: BLE001
                pass
            self._dia_diem_cookie(ghi, gl)
        try:
            sau = self._doc_dia_diem_menu(ghi)
            self.st.phim("Escape")
        except Exception as e:  # noqa: BLE001
            sau = ""
            ghi("   đọc lại menu lỗi: {0}".format(str(e)[:100]))
        ok = khop(sau)
        ghi("*** ĐỊA ĐIỂM XEM: {0!r} → {1!r} ({2}) ***".format(truoc or "?", sau or "?", "ĐẠT" if ok else "HỎNG"))
        return {"ket": "doi" if ok else "hong", "hien_truoc": truoc, "hien_sau": sau}

    def _dia_diem_cookie(self, ghi, gl: str) -> dict:
        """Đường lùi: cookie PREF `gl=<gl>` trên .youtube.com (giữ mọi cặp khác)."""
        gl = str(gl or "").strip().upper()
        cdp, sid = self.st.cdp, self.st.sid

        def doc_pref():
            ck = cdp.goi("Network.getCookies", {"urls": ["https://www.youtube.com/"]}, sid=sid, han=15).get("cookies") or []
            return ([c for c in ck if c.get("name") == "PREF"] or [{}])[0]
        try:
            goc = doc_pref()
            cu = next((c.split("=", 1)[1] for c in str(goc.get("value") or "").split("&")
                       if c.split("=", 1)[0] == "gl" and "=" in c), "").upper()
            cap =[c for c in str(goc.get("value") or "").split("&") if c.strip() and c.split("=", 1)[0] != "gl"]
            c = {"name": "PREF", "value": "&".join(cap + ["gl=" + gl]), "domain": ".youtube.com", "path": "/",
                 "secure": True, "sameSite": "None",
                 "expires": goc["expires"] if (goc.get("expires") or -1) > 0 else time.time() + 400 * 86400}
            cdp.goi("Network.setCookie", c, sid=sid, han=15)
            sau = next((x.split("=", 1)[1] for x in str(doc_pref().get("value") or "").split("&")
                        if x.split("=", 1)[0] == "gl" and "=" in x), "").upper()
        except Exception as e:  # noqa: BLE001 — phụ: không chặn các mục thiết lập khác
            ghi("địa điểm xem: lỗi {0}".format(str(e)[:120]))
            return {"ket": "hong", "gl_truoc": "", "gl_sau": "", "ly_do": str(e)[:200]}
        ghi("   cookie PREF gl: {0!r} → {1!r}".format(cu or "mặc định", sau))
        return {"ket": "doi" if sau == gl else "hong", "gl_truoc": cu, "gl_sau": sau}

    def _ngon_ngu_tai_khoan(self, ghi, dich: str = "vi") -> None:
        """Đường CHÍNH: Studio theo ngôn ngữ của TÀI KHOẢN Google (menu youtube.com chỉ đổi riêng trình duyệt).
        myaccount.google.com/language → bút chì sửa ngôn ngữ → ô tìm → ngôn ngữ ĐÍCH → xác nhận."""
        b = NGON_NGU_DICH.get(dich) or NGON_NGU_DICH[MA_NGON_NGU_MAC_DINH]
        self.st.mo("https://myaccount.google.com/language", han=60)
        self.ngu(4.0)
        self.kiem_chan()
        sua = self._bam_nhan(r"수정|edit|chỉnh sửa|sửa|編集|変更|변경", "삭제|delete|xóa|xoá|저장|save|削除|保存", "nút sửa ngôn ngữ ưu tiên")
        ghi("   bấm «{0}»".format(sua))
        self.ngu(2.5)
        self._bam_nhan(r"기본 언어|default language|preferred language|primary language|ngôn ngữ|優先言語|デフォルトの言語|主要言語|言語", "nhãn ô tìm", sel="input")
        self.ngu(0.6)
        muc, loi = "", None
        for go in b["go"]:                                          # gõ lần lượt: tên bản địa → tên Anh → tên Việt
            self.st._chen(go)                                       # noqa: SLF001
            self.ngu(2.0)
            try:
                muc = self._bam_nhan(b["re_chon"], "{0} trong danh sách".format(b["ten"]), loai=r"취소|cancel|hủy|キャンセル", han=4.0,
                                     sel="li, [role=option], [role=radio], [role=listitem], label")
                break
            except LoiMuc as e:
                loi = e
                self.st._ctrl_a()                                   # noqa: SLF001
                self.ngu(0.4)
        if not muc:
            raise loi or LoiMuc("không thấy {0} trong danh sách".format(b["ten"]))
        ghi("   chọn «{0}»".format(muc))
        self.ngu(1.0)
        try:                                                        # nút của HỘP («Lưu ngôn ngữ đã chọn») trước, nút «Lưu» của ngôn ngữ khác sau
            luu = self._bam_nhan(r"선택한 언어|selected language|ngôn ngữ đã chọn|選択した言語", "nút lưu ngôn ngữ đã chọn", han=3.0, sel="button, [role=button]")
        except LoiMuc:
            try:                                                    # 05/10: nút «Lưu ngôn ngữ: <ĐÍCH>» — tránh bấm nhầm nút Lưu của ngôn ngữ gợi ý khác (Esperanto...)
                tho = re.escape(re.split(r"\s*[(（]", muc)[0].strip())
                luu = self._bam_nhan(r"(저장|save|lưu|保存).*" + tho + r"|" + tho + r".*(저장|save|lưu|保存)", "nút lưu ngôn ngữ đích", han=3.0, sel="button, [role=button]")
            except LoiMuc:
                luu = self._bam_nhan(r"저장|save|lưu|保存", "nút lưu ngôn ngữ", loai=r"English|영어|英語", sel="button, [role=button]")
        ghi("   bấm «{0}»".format(luu))
        self.ngu(5.0)
        ghi("   trang tài khoản sau khi lưu: {0}".format(" ".join(str(self.js(_JS_NGON_NGU).get("chu"))[:120].split())))

    def dat_ngon_ngu(self, ghi, chi_doc: bool = False, dich: str = "vi") -> dict:
        """ĐẶT ngôn ngữ giao diện Studio = ngôn ngữ ĐÍCH `dich` (chạy ĐẦU TIÊN: Studio tiếng Hàn làm hỏng mọi bước tìm theo chữ).
        Đọc trước → đã đúng thì thôi. Đường 1: ngôn ngữ ƯU TIÊN của tài khoản Google (Studio theo cái này; menu avatar
        Studio không có mục ngôn ngữ, menu youtube.com chỉ đổi riêng trình duyệt — đo 04/10). Đường 2: `?hl=`. Xong ĐỌC LẠI.
        Trả {ket: giong|doi|hong|khac (chi_doc), lang_truoc, lang_sau, chu, dich}."""
        b = NGON_NGU_DICH.get(dich) or NGON_NGU_DICH[MA_NGON_NGU_MAC_DINH]
        dung, lang, chu = self.doc_ngon_ngu(dich=dich)
        ghi("ngôn ngữ Studio: html lang={0!r} → {1} (chữ: {2})".format(lang, ("ĐÚNG đích " if dung else "KHÔNG phải ") + b["ten"], chu[:90]))
        kq = {"ket": "giong" if dung else "khac", "lang_truoc": lang, "lang_sau": lang, "chu": chu, "dich": dich}
        if dung or chi_doc:
            return kq
        loi_cuoi = ""
        for cach in (tuple(x for x in os.environ.get("TL_NGON_NGU_CACH", "").split(",") if x) or CACH_NGON_NGU_MAC_DINH):
            try:
                if cach == "tai_khoan":
                    self._ngon_ngu_tai_khoan(ghi, dich)
                elif cach == "trinh_duyet":
                    self._ngon_ngu_trinh_duyet(ghi, dich)
                elif cach == "cookie":
                    self._ngon_ngu_cookie(ghi, dich)
                else:
                    self.st.mo("https://studio.youtube.com/?hl=" + b["html"], han=60)
                    self.ngu(4.0)
                self.kiem_chan()
                self.st.mo("https://studio.youtube.com/", han=60)
                self.ngu(3.0)
                dung, lang2, chu2 = self.doc_ngon_ngu(dich=dich)
                kq.update(lang_sau=lang2, chu=chu2)
                ghi("   đọc lại sau đường {0}: html lang={1!r} → {2}".format(cach, lang2, "ĐÚNG đích" if dung else "vẫn không phải"))
                if dung:
                    kq["ket"] = "doi"
                    return kq
                loi_cuoi = "đường {0}: đọc lại vẫn không phải {1}".format(cach, b["ten"])
            except CanNguoi:
                raise
            except Exception as e:  # noqa: BLE001
                loi_cuoi = "đường {0}: {1}".format(cach, str(e)[:120])
                ghi("   {0}".format(loi_cuoi))
                try:
                    self.st.phim("Escape")
                except Exception:  # noqa: BLE001
                    pass
        self.chup("ngon-ngu-hong")
        kq["ket"], kq["ly_do"] = "hong", loi_cuoi
        return kq

    # ── đọc ──
    def doc_ho_so(self) -> dict:
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self.doi_hien("#description-textbox [role=textbox]", 15)
        self.ngu(1.5)
        du = self.js(_JS_HO_SO)
        # ô ảnh (nhất là hình mờ) dựng chậm sau tải lại: chưa thấy ảnh thì đọc lại vài lần trước khi kết luận «chưa có»
        for _ in range(4):
            if not du or all((du.get(m) or {}).get("co") for m in ("logo", "banner", "hinh_mo")):
                break
            self.ngu(2.5)
            du = self.js(_JS_HO_SO) or du
        if not du:
            raise LoiMuc("không đọc được trang Hồ sơ")
        return du

    def mo_cai_dat(self) -> None:
        self.bam(["tp-yt-paper-icon-item#settings-item", "#settings-item"], ("Cài đặt", "Settings", "設定"))
        if not self.doi_hien("ytcp-navigation li#channel", 12):
            raise LoiMuc("hộp Cài đặt không mở")
        self.ngu(1.0)

    def vao_muc_cai_dat(self, id_muc: str, cho_css: str) -> None:
        self.bam(["ytcp-navigation li#{0}".format(id_muc), "li#{0}".format(id_muc)])
        if not self.doi_hien(cho_css, 12):
            raise LoiMuc("mục cài đặt {0} không dựng xong".format(id_muc))
        self.ngu(1.0)

    def dong_cai_dat(self) -> None:
        try:
            self.bam(["ytcp-settings-dialog ytcp-button#cancel-button", "ytcp-button#cancel-button"], CHU_NUT_XONG[:0] + ("Đóng", "Close", "閉じる"), han=4)
        except LoiMuc:
            pass
        self.ngu(0.8)

    def doc_cai_dat(self, ht: dict, loi: dict) -> None:
        try:
            self.mo_cai_dat()
            self.vao_muc_cai_dat("channel", "#country-of-residence-select")
            kc = self.js(_JS_CAI_DAT_KENH)
            if kc:
                ht["quoc_gia"], ht["tu_khoa"] = kc["quoc_gia"], kc["tu_khoa"]
            self.vao_muc_cai_dat("uploads", "#tags-container")
            md = {}
            cb = self.js(_JS_MAC_DINH_CO_BAN)
            if cb:
                md["the"], md["che_do"] = cb["the"], cb["che_do"]
            self.bam(["tp-yt-paper-tab#advancedSettings"], ("Cài đặt nâng cao", "Advanced settings", "詳細設定"))
            self.doi_hien("#category-select", 10)
            na = self.js(_JS_MAC_DINH_NANG_CAO)
            if na:
                md.update(na)
            if "danh_muc" in md and "the" in md:
                ht["mac_dinh"] = md
        except (LoiMuc, Exception) as e:  # noqa: BLE001
            if isinstance(e, CanNguoi):
                raise
            loi["cai_dat"] = str(e)[:150]
            self.chup("doc-cai-dat-hong")
        finally:
            self.dong_cai_dat()

    def doc_ds_phat(self, ht: dict, loi: dict) -> None:
        try:
            self.mo("https://studio.youtube.com/channel/{0}/content/playlists".format(self.uc), "ytcp-playlist-section")
            self.ngu(2.5)
            du = self.js(_JS_DS_PHAT)
            if du is None:
                raise LoiMuc("không đọc được danh sách phát")
            ht["danh_sach_phat"] = du["ten"]
            ht["_ds_phat_chu"] = du["chu"]
        except (LoiMuc, Exception) as e:  # noqa: BLE001
            if isinstance(e, CanNguoi):
                raise
            loi["danh_sach_phat"] = str(e)[:150]
            self.chup("doc-ds-phat-hong")

    def doc_hien_trang(self) -> Tuple[dict, dict]:
        """Đọc TOÀN BỘ hiện trạng (không sửa gì). Trả (hiện trạng, {nhóm: lỗi đọc})."""
        ht: dict = {}
        loi: dict = {}
        try:
            hs = self.doc_ho_so()
            ht.update(ten=hs["ten"], handle=hs["handle"], mo_ta=hs["mo_ta"],
                      anh={m: bool((hs[m] or {}).get("co")) for m in ("logo", "banner", "hinh_mo")},
                      _src={m: (hs[m] or {}).get("src") for m in ("logo", "banner", "hinh_mo")})
        except LoiMuc as e:
            loi["ho_so"] = str(e)[:150]
            self.chup("doc-ho-so-hong")
        self.doc_cai_dat(ht, loi)
        self.doc_ds_phat(ht, loi)
        return ht, loi

    # ── sửa: Hồ sơ ──
    def dat_tep(self, css_nut, duong: str, han: float = 10.0) -> None:
        """Bấm nút → Chrome mở hộp chọn tệp (đã bị chặn) → DOM.setFileInputFiles."""
        duong = os.path.abspath(duong)
        if not os.path.isfile(duong):
            raise LoiMuc("không có tệp ảnh {0}".format(duong))
        cdp, sid = self.st.cdp, self.st.sid
        cdp.tep_cho.pop(sid, None)
        self.bam(css_nut)
        het = time.monotonic() + han
        while time.monotonic() < het:
            p = cdp.tep_cho.pop(sid, None)
            if p and p.get("backendNodeId"):
                cdp.goi("DOM.setFileInputFiles", {"files": [duong], "backendNodeId": p["backendNodeId"]}, sid=sid, han=30)
                self.ngu(2.0)
                if self.debug:
                    self.chup("sau-chon-tep")
                return
            cdp.bom(0.3)
        raise LoiMuc("bấm xong nhưng không mở hộp chọn tệp")

    def xong_hop_cat(self, han: float = 12.0) -> None:
        """Sau khi chọn ảnh có hộp cắt/xem trước: bấm nút Xong/Áp dụng của HỘP đó (nếu có hộp)."""
        het = time.monotonic() + han
        while time.monotonic() < het:
            if self.hop_thoai():
                if self.debug:
                    self.ghi("   hộp cắt/xem trước: " + re.sub(r"\s+", " ", self.hop_thoai())[:160])
                try:
                    self.bam(["tp-yt-paper-dialog ytcp-button#done-button", "ytcp-dialog ytcp-button#done-button",
                              "tp-yt-paper-dialog ytcp-button.done-button", "ytcp-banner-editor ytcp-button#done-button"],
                             CHU_NUT_XONG, han=3)
                    self.ngu(1.5)
                    return
                except LoiMuc:
                    pass
            self.ngu(0.8)

    def doi_o_hop_le(self, host: str, han: float = 4.5) -> dict:
        """Chờ Studio kiểm ô xong (handle: trùng/ngắn…). Báo `invalid` ngay khi thấy; không thấy sau `han` giây = hợp lệ."""
        het = time.monotonic() + han
        e: dict = {}
        while True:
            self.ngu(1.2)
            e = self.js("(" + _JS_LOI_O + ")('{0}')".format(host)) or {}
            if e.get("invalid") or time.monotonic() >= het:
                return e

    def huy_thay_doi(self, ghi=None) -> None:
        """Bấm Hủy ở trang Hồ sơ (bỏ thay đổi chưa Xuất bản) để rời trang không kẹt hộp 'rời trang?'."""
        try:
            if self.co(["ytcp-button#discard-changes-button button"]):
                self.bam(["ytcp-button#discard-changes-button button"], ("Hủy", "Huỷ", "Cancel", "キャンセル"), han=3)
                self.ngu(1.2)
                if self.hop_thoai().strip():
                    self.bam(["tp-yt-paper-dialog ytcp-button#confirm-button", "ytcp-confirmation-dialog ytcp-button#confirm-button"],
                             CHU_NUT_XAC_NHAN, han=3)
        except LoiMuc:
            pass

    def sua_ho_so(self, hs: dict, kh: Dict[str, dict], so: dict, ht: dict, luc: float, ghi, khong_luu: bool = False) -> dict:
        """Điền các mục KHÁC ở trang Hồ sơ rồi Xuất bản. Trả {mục: ("dat"|"hong"|"can_nguoi"|"cho", lý do)}."""
        kq: dict = {}
        thu_muc = _tl().thu_muc_thiet_lap(so["kenh"], GOC_TOOL)
        can = [m for m in ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo") if kh[m]["khac"] in (True, None)]
        for m in ("ten", "handle"):                                 # đang bị chặn đổi → KHÔNG điền, Xuất bản chỉ mang mô tả/ảnh
            ly_chan = ten_handle_bi_chan(so, m, luc) if m in can else ""
            if ly_chan:
                can.remove(m)
                kq[m] = ("cho", ly_chan)
                ghi("   {0}: đang bị chặn đổi ({1}) → KHÔNG điền, Xuất bản không dính {0}".format(TEN_MUC[m], ly_chan))
        if not [m for m in can if m not in kq]:
            return kq
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self.doi_hien("#description-textbox [role=textbox]", 15)
        da_xuat_ban = False
        try:
            sua_gi = False
            # tên
            if "ten" in can:
                v, ly = quyet_doi(so, "ten", ht.get("ten"), hs["ten"], luc)
                if v == "doi":
                    try:
                        self.nhap("ytcp-channel-editing-channel-name input", hs["ten"])
                        self.ngu(1.5)
                        e = self.js("(" + _JS_LOI_O + ")('ytcp-channel-editing-channel-name')")
                        if e and e.get("invalid"):
                            raise LoiMuc("Studio báo tên không hợp lệ: " + str(e.get("loi") or e.get("chu"))[:100])
                        sua_gi = True
                    except LoiMuc as e:
                        kq["ten"] = ("hong", str(e))
                elif v == "giong":
                    kq["ten"] = ("giong", "")
                else:
                    kq["ten"] = ("cho" if v == "cho" else "can_nguoi", ly)
            # handle: thử gốc rồi tối đa 3 biến thể (CHỈ gõ + xem Studio báo, chưa tốn lượt; lượt chỉ tính khi Xuất bản)
            handle_dung = None
            if "handle" in can:
                goc_h = so.get("handle_that") or hs["handle"]
                v, ly = quyet_doi(so, "handle", ht.get("handle"), goc_h, luc)
                if v == "doi":
                    for cand in bien_the_handle(goc_h, (hs.get("mac_dinh_tai_len") or {}).get("ngon_ngu", "jp")):
                        try:
                            self.nhap("ytcp-channel-editing-channel-handle input", cand)
                        except LoiMuc as e:
                            kq["handle"] = ("hong", str(e))
                            break
                        e = self.doi_o_hop_le("ytcp-channel-editing-channel-handle")
                        if not e.get("invalid"):
                            handle_dung = cand
                            sua_gi = True
                            ghi("   handle «{0}»: Studio nhận".format(cand))
                            break
                        ghi("   handle «{0}» Studio không nhận: {1}".format(cand, str(e.get("loi") or e.get("thong_bao") or e.get("chu"))[:100]))
                    else:
                        kq["handle"] = ("hong", "mọi biến thể handle đều bị Studio từ chối/trùng")
                        # trả ô về giá trị cũ để Xuất bản không mang handle lỗi
                        try:
                            self.nhap("ytcp-channel-editing-channel-handle input", str(ht.get("handle") or "").lstrip("@"))
                        except LoiMuc:
                            pass
                elif v == "giong":
                    kq["handle"] = ("giong", "")
                else:
                    kq["handle"] = ("cho" if v == "cho" else "can_nguoi", ly)
            if "mo_ta" in can:
                try:
                    self.nhap("#description-textbox [role=textbox]", hs["mo_ta"], nhieu_dong=True)
                    sua_gi = True
                except LoiMuc as e:
                    kq["mo_ta"] = ("hong", str(e))
            anh_moi = {}
            for muc, host in (("logo", "ytcp-profile-image-upload"), ("banner", "ytcp-banner-upload"), ("hinh_mo", "ytcp-video-watermark-upload")):
                if muc not in can:
                    continue
                try:
                    d = _tl().duong_anh(hs, muc, thu_muc)
                    nut = ["{0} ytcp-button#replace-button".format(host), "{0} ytcp-button#upload-button".format(host)]
                    self.dat_tep(nut, d)
                    self.xong_hop_cat()
                    if muc == "hinh_mo":
                        self.chon_thoi_gian_hinh_mo()
                    anh_moi[muc] = sha_tep(d)
                    sua_gi = True
                except LoiMuc as e:
                    kq[muc] = ("hong", str(e))
                    self.chup("anh-{0}-hong".format(muc))

            if not sua_gi:
                return kq
            if khong_luu:
                ghi("   [--khong-luu] đã điền xong, KHÔNG bấm Xuất bản (bỏ thay đổi)")
                self.chup("khong-luu")
                du = self.js(_JS_HO_SO) or {}
                ghi("   [--khong-luu] đọc lại trang: tên={0!r} handle={1!r} mô tả={2} ký tự, ảnh có: logo={3} banner={4} hình mờ={5}, nút Xuất bản {6}".format(
                    du.get("ten"), du.get("handle"), len(du.get("mo_ta") or ""), (du.get("logo") or {}).get("co"),
                    (du.get("banner") or {}).get("co"), (du.get("hinh_mo") or {}).get("co"), "mờ" if du.get("xuat_ban_tat") else "SÁNG"))
                for m in can:
                    kq.setdefault(m, ("khong_luu", ""))
                return kq
            # Xuất bản. Mốc ảnh công khai LẤY TRƯỚC (bằng chứng đã lưu = URL ảnh công khai đổi sau đó)
            so["truoc"]["cong_khai"] = doc_anh_cong_khai(so.get("uc"))
            self.chup("truoc-xuat-ban")
            self.bam(["ytcp-button#publish-button button", "ytcp-button#publish-button"], ("Xuất bản", "Publish", "公開"), han=6)
            da_xuat_ban = True
            loi_xb = self.xu_ly_sau_xuat_ban(ghi)
            if loi_xb:
                # Studio BÁO LỖI khi Xuất bản → cả lượt coi như CHƯA lưu: ghi chữ thông báo vào sổ, KHÔNG báo đạt, KHÔNG ghi lượt đổi
                ghi("   *** Xuất bản BÁO LỖI: «{0}» — không báo đạt ***".format(loi_xb))
                self.chup("xuat-ban-loi")
                for m in can:
                    if m not in ("ten", "handle") and m not in kq:
                        kq[m] = ("hong", "Xuất bản báo lỗi: " + loi_xb)
                so["truoc"]["loi_xuat_ban"] = loi_xb
                luu_so(so)
                return kq
            # ghi lượt đổi tên/handle NGAY sau Xuất bản (đã tốn lượt dù đọc lại có lệch)
            if "ten" in can and "ten" not in kq:
                ghi_doi(so, "ten", luc)
            if handle_dung:
                ghi_doi(so, "handle", luc)
                so["handle_that"] = "@" + handle_dung
            luu_so(so)
            for muc, h in anh_moi.items():
                so["hash_anh"][muc] = h
            self.ngu(2.0)
            return kq
        finally:
            if not da_xuat_ban:
                self.huy_thay_doi(ghi)

    def chon_thoi_gian_hinh_mo(self) -> None:
        """Hình mờ: đặt hiển thị TOÀN BỘ video (mặc định của Studio có thể là 'Toàn bộ video' — chỉ bấm nếu thấy lựa chọn).
        14/10: DOM thật (ảnh 04/10) là `#entire-video-radio-button` / name=ENTIRE — tên cũ ENTIRE_VIDEO không khớp."""
        try:
            self.bam(["ytcp-video-watermark-upload tp-yt-paper-radio-button#entire-video-radio-button",
                      "ytcp-video-watermark-upload tp-yt-paper-radio-button[name=ENTIRE]",
                      "ytcp-video-watermark-upload tp-yt-paper-radio-button[name=ENTIRE_VIDEO]",
                      "ytcp-video-watermark-upload tp-yt-paper-radio-button[name=FULL_VIDEO]"],
                     ("Toàn bộ video", "Entire video", "動画全体"), han=3)
        except LoiMuc:
            pass

    def xu_ly_sau_xuat_ban(self, ghi, han: float = 40.0, chi_nut: bool = False) -> str:
        """Chờ Xuất bản xong: gặp hộp xác nhận thì bấm Xác nhận (nếu hộp ĐÒI xác minh thì dừng người); xong khi nút Xuất bản mờ lại.
        Trả '' nếu ổn, hoặc CHỮ LỖI của Studio (toast/hộp/ô báo lỗi) — khi đó Xuất bản coi như THẤT BẠI.
        `chi_nut` (thẻ Trang chủ): chỉ nhìn nút Xuất bản, không cần form Hồ sơ."""
        het = time.monotonic() + han
        thay: List[str] = []
        while time.monotonic() < het:
            self.ngu(1.5)
            self.kiem_chan()
            try:
                tb = str(self.js(_JS_LOI_XUAT_BAN) or "")
            except Exception:  # noqa: BLE001
                tb = ""
            if tb.strip():
                thay.append(" ".join(tb.split())[:200])
                loi = thong_bao_loi_xuat_ban(tb)
                if loi:
                    return loi
            ht = self.hop_thoai()
            if ht.strip():
                ghi("   hộp sau Xuất bản: {0}".format(re.sub(r"\s+", " ", ht)[:140]))
                loi = thong_bao_loi_xuat_ban(ht)
                try:
                    self.bam(["tp-yt-paper-dialog ytcp-button.action-button", "tp-yt-paper-dialog ytcp-button#confirm-button",
                              "ytcp-confirmation-dialog ytcp-button#confirm-button"], CHU_NUT_XAC_NHAN, han=3)
                    if loi:
                        return loi
                    continue
                except LoiMuc:
                    self.chup("hop-sau-xuat-ban")
                    if loi:
                        return loi
                    raise LoiMuc("hộp lạ sau Xuất bản, không có nút xác nhận: " + re.sub(r"\s+", " ", ht)[:120])
            if chi_nut:
                if self.js(_JS_XUAT_BAN_TAT) is True:
                    return ""
                continue
            du = self.js(_JS_HO_SO)
            if du is not None and du.get("xuat_ban_tat"):
                return ""
        raise LoiMuc("Xuất bản xong nhưng nút vẫn sáng sau {0:.0f}s (Studio chưa xác nhận lưu){1}".format(
            han, (" — thông báo: " + " | ".join(thay[-3:])) if thay else ""))

    # ── thương hiệu (14/10): đọc hình mờ / thẻ Trang chủ / số danh sách phát; đặt RIÊNG hình mờ ──
    def bang_chung(self, nhan: str) -> dict:
        """Ảnh + bản đồ DOM; trả {anh, ban_do} ({} nếu hụt)."""
        try:
            return self.st.ghi_bang_chung(nhan) or {}
        except Exception:  # noqa: BLE001
            return {}

    def cho_doc_hinh_mo(self, can_co: bool = False, han: float = 20.0) -> Optional[dict]:
        """Đọc ô hình mờ ở trang Hồ sơ đang mở; ô (nhất là ảnh) dựng chậm → đợi tới khi thấy nút Xoá/Tải lên
        (`can_co`: đợi nút Xoá). Trả bản đọc cuối (None nếu không có ô)."""
        het = time.monotonic() + han
        du = None
        while True:
            try:
                du = self.js(_JS_HINH_MO)
            except Exception:  # noqa: BLE001
                du = None
            if du and (du.get("nut_xoa") or (not can_co and du.get("nut_tai_len"))):
                return du
            if time.monotonic() >= het:
                return du
            self.ngu(1.5)

    def doc_thuong_hieu(self) -> Tuple[dict, dict]:
        """CHỈ ĐỌC: hình mờ (trang Hồ sơ), thẻ Trang chủ (trailer/nổi bật), danh sách phát. Trả (kết quả, {nhóm: lỗi})."""
        kq: dict = {"anh": {}}
        loi: dict = {}
        try:
            self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
            self.doi_hien("#description-textbox [role=textbox]", 15)
            tho = self.cho_doc_hinh_mo()
            kq["hinh_mo"], kq["_hinh_mo_tho"] = doc_hinh_mo(tho), tho
            kq["_ho_so"] = self.js(_JS_HO_SO)
            self.ngu(1.0)
            kq["anh"]["hinh_mo"] = self.bang_chung("thuong-hieu-hinh-mo").get("anh", "")
        except LoiMuc as e:
            loi["hinh_mo"] = str(e)[:150]
            kq["hinh_mo"] = doc_hinh_mo(None)
        try:
            # Thẻ Trang chủ: URL `editing/sections` bị đưa về Hồ sơ (đo 14/10) → BẤM tab (chỉ chuyển tab, chưa sửa gì)
            if "/editing/profile" not in self.url():
                self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
            self._bam_nhan(RE_TAB_TRANG_CHU, "tab Thẻ Trang chủ", sel="tp-yt-paper-tab")
            self.ngu(2.0)
            self.kiem_chan()
            du, het, lan_dung = {}, time.monotonic() + 25, 0
            while True:
                du = self.js(_JS_TRANG_CHU) or {}
                dung = du.get("bat") is not None and bool(du.get("ke"))
                lan_dung += 1 if dung else 0
                td = doc_tieu_diem(du.get("chu"), trang_da_dung=lan_dung >= 2)   # 2 lần đọc liền: khung đã dựng hẳn
                if all(td[k]["co"] is not None for k in td) or time.monotonic() >= het:
                    break
                self.ngu(1.5)
            kq["tieu_diem"], kq["_trang_chu"], kq["trang_chu_bat"] = td, du, du.get("bat")
            kq["anh"]["trang_chu"] = self.bang_chung("thuong-hieu-trang-chu").get("anh", "")
        except LoiMuc as e:
            loi["trang_chu"] = str(e)[:150]
            kq["tieu_diem"] = doc_tieu_diem("")
        try:
            self.mo("https://studio.youtube.com/channel/{0}/content/playlists".format(self.uc), "ytcp-playlist-section")
            du, het = None, time.monotonic() + 20
            while True:
                du = self.js(_JS_DEM_DS_PHAT)
                if (du and (du.get("hang") or du.get("trong"))) or time.monotonic() >= het:
                    break
                self.ngu(1.5)
            kq["ds_phat"] = {"so": dem_ds_phat(du), "ten": (du or {}).get("ten") or [], "chan": (du or {}).get("chan") or ""}
            kq["anh"]["ds_phat"] = self.bang_chung("thuong-hieu-ds-phat").get("anh", "")
        except LoiMuc as e:
            loi["ds_phat"] = str(e)[:150]
            kq["ds_phat"] = {"so": None, "ten": [], "chan": ""}
        return kq, loi

    def dat_hinh_mo(self, duong: str, ghi) -> dict:
        """CHỈ đặt hình mờ cho kênh đang THIẾU (đường `hinh_mo` của `sua_ho_so`): chọn tệp → Xong → «Toàn bộ video» →
        so tên/handle/mô tả/logo/banner với lúc mở trang (lệch = bỏ thay đổi) → Xuất bản → TẢI LẠI trang đọc lại.
        Bước nào khác mong đợi → DỪNG (bỏ thay đổi, không bấm thêm gì). Trả {ket: dat|hong|bo, ly_do, anh, doc_lai}."""
        ra: dict = {"ket": "hong", "ly_do": "", "anh": {}, "doc_lai": None}
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self.doi_hien("#description-textbox [role=textbox]", 15)
        hm = doc_hinh_mo(self.cho_doc_hinh_mo())
        ok, ly = can_dat_hinh_mo(hm)
        if not ok:
            ra.update(ket="bo", ly_do=ly)
            return ra
        goc = self.js(_JS_HO_SO)
        if not goc or not self.co(["ytcp-video-watermark-upload ytcp-button#upload-button"]):
            ra["ly_do"] = "trang Hồ sơ khác mong đợi (không đọc được form / không có nút Tải lên của ô hình mờ)"
            self.chup("hinh-mo-khac-mong-doi")
            return ra
        ra["anh"]["truoc"] = self.bang_chung("hinh-mo-truoc").get("anh", "")
        da_xuat_ban = False
        try:
            self.dat_tep(["ytcp-video-watermark-upload ytcp-button#upload-button"], duong)
            self.xong_hop_cat()
            hm2 = doc_hinh_mo(self.cho_doc_hinh_mo(can_co=True, han=15))
            if not hm2["co"]:
                raise LoiMuc("chọn tệp + Xong xong mà ô hình mờ vẫn chưa có ảnh")
            if hm2["thoi_gian"] != "toan_bo":
                self.chon_thoi_gian_hinh_mo()
                self.ngu(1.0)
                hm2 = doc_hinh_mo(self.cho_doc_hinh_mo(can_co=True, han=5))
            ghi("   hình mờ trước Xuất bản: có={0} hiển thị={1} «{2}»".format(hm2["co"], hm2["thoi_gian"], hm2["nhan"]))
            if hm2["thoi_gian"] != "toan_bo":
                raise LoiMuc("không thấy «Toàn bộ video» được chọn (đang: {0!r})".format(hm2.get("nhan")))
            lech = lech_ho_so(goc, self.js(_JS_HO_SO))
            if lech:
                raise LoiMuc("trang Hồ sơ lệch ngoài hình mờ: " + ", ".join(lech))
            ra["anh"]["truoc_xuat_ban"] = self.bang_chung("hinh-mo-truoc-xuat-ban").get("anh", "")
            self.bam(["ytcp-button#publish-button button", "ytcp-button#publish-button"], ("Xuất bản", "Publish", "公開"), han=6)
            da_xuat_ban = True
            loi_xb = self.xu_ly_sau_xuat_ban(ghi)
            if loi_xb:
                raise LoiMuc("Xuất bản báo lỗi: " + loi_xb)
        except LoiMuc as e:
            ra["ly_do"] = str(e)[:300]
            ghi("   hình mờ: DỪNG — {0}".format(ra["ly_do"]))
            self.chup("hinh-mo-hong")
        finally:
            if not da_xuat_ban:
                self.huy_thay_doi(ghi)
        if not da_xuat_ban:
            return ra
        self.ngu(3.0)
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")       # TẢI LẠI: chỉ tin cái Studio đã lưu
        self.doi_hien("#description-textbox [role=textbox]", 15)
        hm3 = doc_hinh_mo(self.cho_doc_hinh_mo(can_co=True, han=30))
        lech = lech_ho_so(goc, self.js(_JS_HO_SO))
        ra["doc_lai"], ra["lech_sau"] = hm3, lech
        ra["anh"]["sau"] = self.bang_chung("hinh-mo-sau").get("anh", "")
        if hm3["co"] and hm3["thoi_gian"] == "toan_bo" and not lech:      # nguồn thật = trang đã tải lại
            ra["ket"] = "dat"
            if ra["ly_do"]:
                ra["ghi_chu"], ra["ly_do"] = ra["ly_do"], ""
        else:
            ra["ly_do"] = "; ".join(x for x in (ra["ly_do"], "đọc lại sau Xuất bản: có={0} hiển thị={1!r}".format(
                hm3["co"], hm3["thoi_gian"]), ("lệch: " + ", ".join(lech)) if lech else "") if x)
        return ra

    def dat_mo_ta(self, chu: str, ghi, khong_luu: bool = False) -> dict:
        """CHỈ đặt MÔ TẢ cho kênh đang để TRỐNG (14/10, chủ duyệt TL1): gõ → đọc lại ô → so tên/handle/logo/banner với lúc
        mở trang (lệch = bỏ thay đổi) → Xuất bản → TẢI LẠI đọc lại. Ô đã có chữ → KHÔNG đụng. `khong_luu`: gõ rồi bỏ.
        Trả {ket: dat|hong|bo|khong_luu, ly_do, anh, doc_lai}."""
        ra: dict = {"ket": "hong", "ly_do": "", "anh": {}, "doc_lai": None}
        css = "#description-textbox [role=textbox]"
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self.doi_hien(css, 15)
        self.ngu(1.5)
        goc = self.js(_JS_HO_SO)
        if not goc:
            ra["ly_do"] = "không đọc được trang Hồ sơ"
            self.chup("mo-ta-khac-mong-doi")
            return ra
        if str(goc.get("mo_ta") or "").strip():
            ra.update(ket="bo", ly_do="kênh đã có mô tả ({0} ký tự) — không đụng".format(len(goc.get("mo_ta") or "")))
            return ra
        ra["anh"]["truoc"] = self.bang_chung("mo-ta-truoc").get("anh", "")
        da_xuat_ban = False
        try:
            self.nhap(css, chu, nhieu_dong=True)
            self.ngu(1.0)
            sau = self.js(_JS_HO_SO)
            lech = [m for m in lech_ho_so(goc, sau) if m != "mo_ta"]
            if lech:
                raise LoiMuc("trang Hồ sơ lệch ngoài mô tả: " + ", ".join(lech))
            if not mo_ta_giong(chu, (sau or {}).get("mo_ta")):
                raise LoiMuc("ô mô tả đọc lại lệch chữ đã gõ")
            ra["anh"]["truoc_xuat_ban"] = self.bang_chung("mo-ta-truoc-xuat-ban").get("anh", "")
            if khong_luu:
                ra.update(ket="khong_luu", ly_do="[--khong-luu] đã gõ + đọc lại đúng, KHÔNG Xuất bản (bỏ thay đổi)")
                return ra
            self.bam(["ytcp-button#publish-button button", "ytcp-button#publish-button"], ("Xuất bản", "Publish", "公開"), han=6)
            da_xuat_ban = True
            loi_xb = self.xu_ly_sau_xuat_ban(ghi)
            if loi_xb:
                raise LoiMuc("Xuất bản báo lỗi: " + loi_xb)
        except CanNguoi:
            raise
        except Exception as e:  # noqa: BLE001 — LoiMuc / LoiThaoTac (bấm hụt): DỪNG, không bấm thêm
            ra["ly_do"] = str(e)[:300]
            ghi("   mô tả: DỪNG — {0}".format(ra["ly_do"]))
            self.chup("mo-ta-hong")
        finally:
            if not da_xuat_ban:
                self.huy_thay_doi(ghi)
        if not da_xuat_ban:
            return ra
        self.ngu(3.0)
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")       # TẢI LẠI: chỉ tin cái Studio đã lưu
        self.doi_hien(css, 15)
        self.ngu(2.0)
        du = self.js(_JS_HO_SO) or {}
        lech = [m for m in lech_ho_so(goc, du) if m != "mo_ta"]
        ra["doc_lai"], ra["lech_sau"] = du.get("mo_ta"), lech
        ra["anh"]["sau"] = self.bang_chung("mo-ta-sau").get("anh", "")
        if mo_ta_giong(chu, du.get("mo_ta")) and not lech:
            ra["ket"], ra["ly_do"] = "dat", ""
        else:
            ra["ly_do"] = "; ".join(x for x in (ra["ly_do"], "đọc lại sau Xuất bản: mô tả {0}".format(
                "KHỚP" if mo_ta_giong(chu, du.get("mo_ta")) else "LỆCH"), ("lệch: " + ", ".join(lech)) if lech else "") if x)
        return ra

    # ── trang chủ (14/10): DOM đo bằng 3 lượt thăm dò KHÔNG lưu trên TL2-T7 ──
    def doc_tc(self) -> dict:
        try:
            return tom_trang_chu(self.js(_JS_BO_CUC_TC))
        except Exception:  # noqa: BLE001
            return tom_trang_chu(None)

    def mo_the_trang_chu(self, han: float = 30.0) -> dict:
        """Tuỳ chỉnh → bấm tab «Thẻ Trang chủ» (URL `editing/sections` bị đưa về Hồ sơ) → đợi công tắc + bố cục dựng xong
        (2 lần đọc liền giống nhau). Trả `tom_trang_chu`; không dựng → LoiMuc."""
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self._bam_nhan(RE_TAB_TRANG_CHU, "tab Thẻ Trang chủ", sel="tp-yt-paper-tab")
        self.ngu(2.0)
        self.kiem_chan()
        het, cu = time.monotonic() + han, None
        while True:
            t = self.doc_tc()
            dung = t["bat"] is not None and t["them_tat"] is not None and bool(t["phan"])
            if dung and cu == t:
                return t
            if time.monotonic() >= het:
                raise LoiMuc("thẻ Trang chủ không dựng xong (công tắc={0}, nút Thêm={1}, {2} phần)".format(t["bat"], t["them_tat"], len(t["phan"])))
            cu = t if dung else None
            self.ngu(1.5)

    def _cho_tc(self, dk, han: float = 10.0) -> dict:
        het = time.monotonic() + han
        while True:
            t = self.doc_tc()
            if dk(t) or time.monotonic() >= het:
                return t
            self.ngu(1.0)

    def them_phan(self, re_muc: str, nhan: str) -> None:
        """«Thêm phần kênh» → bấm mục khớp `re_muc` (chuột thật vào tâm điểm). Không thấy menu / mục / mục đang mờ → Escape, LoiMuc."""
        self.bam(["ytcp-button#add-section-button"], han=5)
        het, ds = time.monotonic() + 6, None
        while ds is None and time.monotonic() < het:
            self.ngu(0.8)
            ds = self.js(_JS_MENU_PHAN)
        x = chon_muc_phan(ds, re_muc)
        if not x or x.get("tat"):
            self.chup("menu-phan-" + nhan.replace(" ", "-")[:20])
            self.st.phim("Escape")
            raise LoiMuc("menu «Thêm phần kênh» {0} «{1}» (menu: {2})".format("có nhưng MỜ mục" if x else "không có mục", nhan,
                                                                          " | ".join(m.get("chu", "") for m in (ds or []))[:200]))
        self.ghi("   + phần «{0}» (test-id {1})".format(x["chu"], x.get("test_id")))
        self.st._bam_diem(round(x["x"], 1), round(x["y"], 1))          # noqa: SLF001
        self.ngu(2.5)

    def chon_video_hop(self, vid: str, tieu_de: str) -> str:
        """Hộp «Chọn một video cụ thể»: tìm theo đầu tiêu đề → bấm ĐÚNG thẻ có mã `vid` (ảnh thu nhỏ) → hộp tự đóng.
        Trả tiêu đề Studio của thẻ đã bấm. Không thấy hộp / thẻ / hộp không đóng → LoiMuc (nơi gọi bỏ thay đổi)."""
        het, du = time.monotonic() + 10, None
        while du is None and time.monotonic() < het:
            du = self.js(_JS_THE_VIDEO)
            if du is None:
                self.ngu(1.0)
        if du is None:
            raise LoiMuc("bấm mục menu xong không thấy hộp «Chọn một video cụ thể»")
        x = None
        for go in dict.fromkeys((tieu_de[:30], tieu_de[:12])):
            try:                                                    # ô tìm «video của bạn» (hộp nổi bật còn tab «kênh khác»)
                self.bam(["ytcp-video-pick-dialog tp-yt-paper-tab#search-yours-tab"], han=3)
            except Exception:  # noqa: BLE001
                pass
            self.bam(["ytcp-video-pick-dialog input#search-yours"], han=4)
            self.st._ctrl_a()                                       # noqa: SLF001
            self.st._chen(go)                                       # noqa: SLF001
            self.st.phim("Enter")
            het, lan = time.monotonic() + 10, 0
            while time.monotonic() < het:
                self.ngu(1.5)
                du = self.js(_JS_THE_VIDEO) or {}
                if chuan(du.get("tim")) != chuan(go):               # chữ chưa vào ĐÚNG ô của hộp đang mở → chưa tin danh sách
                    continue
                lan += 1
                x = chon_the_video(du.get("the"), vid) if lan >= 2 else None    # đợi lọc xong (2 lần đọc)
                if x:
                    break
            if x:
                break
            self.ghi("   hộp chọn: tìm «{0}» (ô đang: {1!r}) không ra thẻ {2} (thẻ: {3})".format(go, du.get("tim"), vid, " | ".join(
                "{0}:{1}".format(t.get("ma"), str(t.get("tieu_de"))[:20]) for t in (du.get("the") or [])[:6])))
        if not x:
            self.chup("hop-chon-khong-thay")
            raise LoiMuc("hộp chọn video không có thẻ đúng mã {0}".format(vid))
        if not str(x.get("tieu_de") or "").strip():
            raise LoiMuc("thẻ mã {0} không có tiêu đề".format(vid))
        if not khop_tieu_de(x.get("tieu_de"), tieu_de):                 # mã khớp là bằng chứng chính; tiêu đề có thể đã sửa sau lần cào
            self.ghi("   (thẻ {0}: tiêu đề Studio «{1}» khác bảng số liệu «{2}»)".format(vid, str(x["tieu_de"])[:50], tieu_de[:50]))
        pt = self.st._js("timChua", {"chon": ["ytcp-video-pick-dialog ytcp-entity-card"]}, "/vi/{0}/".format(vid))   # noqa: SLF001
        if not (pt or {}).get("khop"):
            raise LoiMuc("không định vị được thẻ {0} để bấm".format(vid))
        self.st.bam(dict(pt, khoa="thẻ video " + vid))              # cuộn vào giữa + kiểm điểm bấm trúng thẻ
        t = self._cho_tc(lambda t: not t["hop_chon"], 8)
        if t["hop_chon"]:
            raise LoiMuc("bấm thẻ video xong hộp chọn không đóng")
        return str(x["tieu_de"]).strip()

    def dong_hop_chon(self) -> None:
        """Dọn trước khi bỏ thay đổi: đóng hộp chọn video (nút Đóng) / menu đang mở. Không ném lỗi."""
        try:
            if self.doc_tc()["hop_chon"]:
                self.bam(["ytcp-video-pick-dialog ytcp-icon-button#close"], han=3)
                self.ngu(1.5)
            if self.js(_JS_MENU_PHAN):
                self.st.phim("Escape")
                self.ngu(1.0)
        except Exception:  # noqa: BLE001
            pass

    def dat_trang_chu(self, gt: Optional[dict], nb: Optional[dict], ghi, khong_luu: bool = False) -> dict:
        """Thẻ Trang chủ: BẬT công tắc → «Video giới thiệu kênh» = `gt` → «Video nổi bật (người đăng ký cũ)» = `nb` → phần
        «Video phổ biến» (cái nào có sẵn thì giữ) → so bố cục (không mất phần nào) → Xuất bản → TẢI LẠI đọc lại. Bước nào
        khác mong đợi → DỪNG cả kênh (bỏ mọi thay đổi, không Xuất bản). Trả {ket: dat|giong|hong|khong_luu, ly_do, buoc,
        truoc, doc_lai, anh}."""
        ra: dict = {"ket": "hong", "ly_do": "", "buoc": [], "truoc": None, "doc_lai": None, "anh": {}}
        t0 = self.mo_the_trang_chu()
        ra["truoc"] = t0
        ra["anh"]["truoc"] = self.bang_chung("trang-chu-truoc").get("anh", "")
        ghi("   trang chủ trước: bật={0} · trailer={1!r} · nổi bật={2!r} · phần: {3}".format(
            t0["bat"], t0["trailer"]["tieu_de"], t0["noi_bat"]["tieu_de"], ", ".join(t0["phan"])))
        sua = False
        da_xuat_ban = False
        da_dat: Dict[str, str] = {}
        ra["da_dat"] = da_dat
        try:
            if not t0["bat"]:
                self.bam(["ytcp-switch#home-tab-enabled-switch button[role=switch]"], han=5)
                t = self._cho_tc(lambda t: t["bat"] is True and t["them_tat"] is False, 8)
                if not (t["bat"] is True and t["them_tat"] is False):
                    raise LoiMuc("bấm công tắc mà Thẻ Trang chủ chưa bật (bật={0}, nút Thêm mờ={1})".format(t["bat"], t["them_tat"]))
                ra["buoc"].append("bật Thẻ Trang chủ")
                sua = True
            for khoa, v, re_muc, nhan in (("trailer", gt, RE_MUC_TRAILER, "Video giới thiệu kênh"),
                                          ("noi_bat", nb, RE_MUC_NOI_BAT, "Video nổi bật")):
                hien = self.doc_tc()[khoa]
                if hien["co"]:
                    ra["buoc"].append("{0}: đã có «{1}» — giữ".format(nhan, hien["tieu_de"][:60]))
                    continue
                if not v:
                    ra["buoc"].append("{0}: không có video đủ điều kiện — bỏ".format(nhan))
                    continue
                self.them_phan(re_muc, nhan)
                td_the = self.chon_video_hop(v["vid"], v["tieu_de"])
                t = self._cho_tc(lambda t, k=khoa: t[k]["co"], 8)
                if not (t[khoa]["co"] and khop_tieu_de(t[khoa]["tieu_de"], td_the)):
                    raise LoiMuc("{0}: sau khi chọn, ô hiện {1!r} — không khớp thẻ «{2}»".format(nhan, t[khoa]["tieu_de"][:60], td_the[:60]))
                if t[khoa]["ma"] and v["vid"] not in t[khoa]["ma"]:
                    raise LoiMuc("{0}: ảnh thu nhỏ mang mã {1}, mong {2}".format(nhan, t[khoa]["ma"], v["vid"]))
                da_dat[khoa] = td_the
                ra["buoc"].append("{0} = «{1}» ({2})".format(nhan, td_the[:60], v["vid"]))
                sua = True
            if self.doc_tc()["pho_bien"]:
                ra["buoc"].append("Video phổ biến: đã có — giữ")
            else:
                self.them_phan(RE_MUC_PHO_BIEN, "Video phổ biến")
                if not self._cho_tc(lambda t: t["pho_bien"], 8)["pho_bien"]:
                    raise LoiMuc("bấm «Video phổ biến» mà bố cục không có phần đó")
                ra["buoc"].append("thêm phần Video phổ biến")
                sua = True
            t1 = self.doc_tc()
            mat = [p for p in t0["phan"] if p not in t1["phan"]]
            if mat or t1["bat"] is not True:
                raise LoiMuc("bố cục lệch trước khi Xuất bản: bật={0}, mất phần {1}".format(t1["bat"], mat))
            ghi("   " + " · ".join(ra["buoc"]))
            if not sua:
                ra.update(ket="giong", ly_do="đã đủ — không sửa gì")
                return ra
            ra["anh"]["truoc_xuat_ban_cuoi"] = self.bang_chung("trang-chu-truoc-xuat-ban-cuoi").get("anh", "")   # cuối bố cục
            self.js("(() => { const e = document.querySelector('ytcp-switch#home-tab-enabled-switch'); if (e) e.scrollIntoView({block: 'center'}); return !!e; })()")
            self.ngu(1.0)
            ra["anh"]["truoc_xuat_ban"] = self.bang_chung("trang-chu-truoc-xuat-ban").get("anh", "")             # đầu: công tắc + tiêu điểm
            if khong_luu:
                ra.update(ket="khong_luu", ly_do="[--khong-luu] điền xong + đọc đúng, KHÔNG Xuất bản (bỏ thay đổi)")
                return ra
            self.bam(["ytcp-button#publish-button button", "ytcp-button#publish-button"], ("Xuất bản", "Publish", "公開"), han=6)
            da_xuat_ban = True
            loi_xb = self.xu_ly_sau_xuat_ban(ghi, chi_nut=True)
            if loi_xb:
                raise LoiMuc("Xuất bản báo lỗi: " + loi_xb)
        except CanNguoi:
            raise
        except Exception as e:  # noqa: BLE001 — LoiMuc / LoiThaoTac: DỪNG kênh, không bấm thêm
            ra["ly_do"] = str(e)[:300]
            ghi("   trang chủ: DỪNG — {0}".format(ra["ly_do"]))
            self.chup("trang-chu-hong")
        finally:
            if not da_xuat_ban:
                self.dong_hop_chon()
                try:
                    self.huy_thay_doi(ghi)
                except Exception:  # noqa: BLE001
                    pass
        if not da_xuat_ban:
            return ra
        self.ngu(3.0)
        t9 = self.mo_the_trang_chu()                                # TẢI LẠI: chỉ tin cái Studio đã lưu
        ra["doc_lai"] = t9
        ra["anh"]["sau"] = self.bang_chung("trang-chu-sau").get("anh", "")
        self.js("(() => { const e = [...document.querySelectorAll('ytcp-shelf-list-item')].pop(); if (e) e.scrollIntoView({block: 'center'}); return !!e; })()")
        self.ngu(1.0)
        ra["anh"]["sau_cuoi"] = self.bang_chung("trang-chu-sau-cuoi").get("anh", "")
        sai = [] if t9["bat"] is True else ["Thẻ Trang chủ chưa bật"]
        for khoa, nhan in (("trailer", "video giới thiệu"), ("noi_bat", "video nổi bật")):
            if khoa in da_dat and not khop_tieu_de(t9[khoa]["tieu_de"], da_dat[khoa]):
                sai.append("{0}: {1!r}".format(nhan, t9[khoa]["tieu_de"][:60]))
        if not t9["pho_bien"]:
            sai.append("không có phần Video phổ biến")
        mat = [p for p in t0["phan"] if p not in t9["phan"]]
        if mat:
            sai.append("mất phần " + ", ".join(mat))
        ghi("   trang chủ ĐỌC LẠI: bật={0} · trailer={1!r} · nổi bật={2!r} · phần: {3}".format(
            t9["bat"], t9["trailer"]["tieu_de"], t9["noi_bat"]["tieu_de"], ", ".join(t9["phan"])))
        if not sai:                                                 # nguồn thật = trang đã tải lại
            ra["ket"] = "dat"
            if ra["ly_do"]:
                ra["ghi_chu"], ra["ly_do"] = ra["ly_do"], ""
        else:
            ra["ly_do"] = "; ".join(x for x in (ra["ly_do"], "đọc lại sau Xuất bản: " + "; ".join(sai)) if x)
        return ra

    # ── sửa: Cài đặt kênh / mặc định tải lên ──
    def chon_dropdown(self, css_trigger: str, aliases) -> None:
        if not aliases:
            raise LoiMuc("không biết tên «{0}» bằng tiếng Studio".format(css_trigger))
        self.bam(css_trigger)
        self.ngu(0.8)
        if not self.doi_hien("tp-yt-paper-listbox", 6):
            raise LoiMuc("danh sách chọn của {0} không mở".format(css_trigger))
        # tìm theo chữ trong CÁC mục của danh sách (khớp chính xác tên)
        pt = self.st._tim_spec("chon:" + aliases[0], {"chon": [], "chu": list(aliases)}, 4, True, False, None, 0, ghi_du_phong=False)  # noqa: SLF001
        if not pt:
            self.chup("dropdown-khong-thay")
            raise LoiMuc("không thấy mục «{0}» trong danh sách {1}".format(aliases[0], css_trigger))
        self.st.bam(pt)
        self.ngu(1.0)

    def dat_chip(self, host: str, ds: List[str]) -> None:
        """Xoá hết chip trong `host` rồi gõ lại từng từ khoá + Enter."""
        for _ in range(60):
            pt = self.tim(["{0} ytcp-chip ytcp-icon-button.delete-icon".format(host), "{0} ytcp-chip #delete-icon".format(host)], han=0.5)
            if not pt:
                break
            self.st.bam(pt)
            self.ngu(0.3)
        inp = ["{0} input.text-input".format(host), "{0} input".format(host)]
        for kw in ds:
            self.bam(inp)
            self.st._chen(kw)                                       # noqa: SLF001
            self.st.phim("Enter")
            self.ngu(0.35)

    def luu_cai_dat(self) -> None:
        self.bam(["ytcp-settings-dialog ytcp-button#submit-button button", "ytcp-button#submit-button button", "ytcp-button#submit-button"],
                 ("Lưu", "Save", "保存"), han=6)
        self.ngu(2.5)
        self.kiem_chan()

    def sua_cai_dat_kenh(self, hs: dict, kh: Dict[str, dict], khong_luu: bool = False) -> dict:
        kq: dict = {}
        if not (kh["quoc_gia"]["khac"] in (True, None) or kh["tu_khoa"]["khac"] in (True, None)):
            return kq
        tl = _tl()
        self.mo_cai_dat()
        try:
            self.vao_muc_cai_dat("channel", "#country-of-residence-select")
            if kh["quoc_gia"]["khac"] in (True, None):
                try:
                    self.chon_dropdown("#country-of-residence-select ytcp-dropdown-trigger", tl.ten_quoc_gia(hs.get("quoc_gia")))
                except LoiMuc as e:
                    kq["quoc_gia"] = ("hong", str(e))
            if kh["tu_khoa"]["khac"] in (True, None):
                try:
                    self.dat_chip("#keywords-container", [t for t in hs.get("tu_khoa") or []])
                except LoiMuc as e:
                    kq["tu_khoa"] = ("hong", str(e))
            if khong_luu:
                self.chup("khong-luu-cai-dat")
                self.ghi("   [--khong-luu] đọc lại hộp: {0}".format(json.dumps(self.js(_JS_CAI_DAT_KENH), ensure_ascii=False)[:300]))
                return kq
            self.luu_cai_dat()
        finally:
            self.dong_cai_dat()
        return kq

    def sua_mac_dinh(self, hs: dict, kh: Dict[str, dict], khong_luu: bool = False) -> dict:
        kq: dict = {}
        if kh["mac_dinh"]["khac"] not in (True, None):
            return kq
        tl = _tl()
        md = hs.get("mac_dinh_tai_len") or {}
        self.mo_cai_dat()
        try:
            self.vao_muc_cai_dat("uploads", "#tags-container")
            ghi_chu = kh["mac_dinh"]["ghi"]
            if "thẻ" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.dat_chip("#tags-container", [t for t in md.get("the") or []])
            self.bam(["tp-yt-paper-tab#advancedSettings"], ("Cài đặt nâng cao", "Advanced settings", "詳細設定"))
            self.doi_hien("#category-select", 10)
            if "danh mục" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.chon_dropdown("#category-select ytcp-dropdown-trigger", tl.ten_danh_muc(md.get("danh_muc")))
            if "ngôn ngữ video" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.chon_dropdown("#audio-language ytcp-dropdown-trigger", tl.ten_ngon_ngu(md.get("ngon_ngu")))
            if "ngôn ngữ mô tả" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.chon_dropdown("#metadata-language ytcp-dropdown-trigger", tl.ten_ngon_ngu(md.get("ngon_ngu")))
            if khong_luu:
                self.chup("khong-luu-mac-dinh")
                self.ghi("   [--khong-luu] đọc lại hộp (nâng cao): {0}".format(json.dumps(self.js(_JS_MAC_DINH_NANG_CAO), ensure_ascii=False)[:300]))
                self.bam(["tp-yt-paper-tab#basicInfo"], ("Thông tin cơ bản", "Basic info", "基本情報"), han=4)
                self.ngu(1.0)
                self.ghi("   [--khong-luu] đọc lại hộp (cơ bản): {0}".format(json.dumps(self.js(_JS_MAC_DINH_CO_BAN), ensure_ascii=False)[:300]))
                return kq
            self.luu_cai_dat()
        except LoiMuc as e:
            kq["mac_dinh"] = ("hong", str(e))
            self.chup("mac-dinh-hong")
        finally:
            self.dong_cai_dat()
        return kq

    # ── danh sách phát ──
    def tao_ds_phat(self, ten: str, mo_ta: str) -> None:
        try:                                                       # danh sách còn TRỐNG: nút ngay giữa trang
            self.bam(["ytcp-playlist-section ytcp-button.content-button", "ytcp-playlist-section-content ytcp-button.content-button"],
                     CHU_DS_MOI, han=2.5)
        except LoiMuc:                                             # đã có danh sách: nút Tạo trên đầu trang → mục "Danh sách phát mới"
            self.bam(["ytcp-button#create-icon button", "ytcp-button#create-icon"], CHU_TAO, han=6)
            self.ngu(1.0)
            self.bam([], CHU_DS_MOI, han=6)
        if not self.doi_hien("ytcp-playlist-metadata-editor", 6):          # có thể hiện menu con "Danh sách phát mới"
            self.bam([], CHU_DS_MOI, han=4)
            if not self.doi_hien("ytcp-playlist-metadata-editor", 8):
                raise LoiMuc("hộp tạo danh sách phát không mở")
        self.ngu(1.0)
        self.nhap("ytcp-playlist-metadata-editor #title-textarea [role=textbox]", ten)
        if mo_ta:
            self.nhap("ytcp-playlist-metadata-editor #description-textarea [role=textbox]", mo_ta, nhieu_dong=True)
        che_do = self.js("(() => {" + _JS_CHUNG + "return dongCuoi(q('ytcp-playlist-metadata-visibility'));})()") or ""
        if not khop_ten(che_do, CHU_CONG_KHAI):
            self.chon_dropdown("ytcp-playlist-metadata-visibility ytcp-dropdown-trigger", CHU_CONG_KHAI)
        self.bam(["ytcp-playlist-metadata-editor ~ * ytcp-button#create-button button", "ytcp-button#create-button button",
                  "ytcp-button#create-button"], CHU_TAO, han=6)
        het = time.monotonic() + 20
        while time.monotonic() < het:
            self.ngu(1.0)
            self.kiem_chan()
            if not self.co("ytcp-playlist-metadata-editor"):
                return
        raise LoiMuc("bấm Tạo nhưng hộp danh sách phát không đóng")

    def sua_ds_phat(self, hs: dict, ht: dict, ghi) -> dict:
        thieu = [d for d in hs.get("danh_sach_phat") or []
                 if chuan(d.get("ten")) not in [chuan(x) for x in ht.get("danh_sach_phat") or []]]
        kq: dict = {}
        if not thieu:
            return kq
        self.mo("https://studio.youtube.com/channel/{0}/content/playlists".format(self.uc), "ytcp-playlist-section")
        self.ngu(2.0)
        for d in thieu:
            try:
                self.tao_ds_phat(d["ten"], d.get("mo_ta") or "")
                ghi("   đã tạo danh sách phát «{0}»".format(d["ten"]))
                self.ngu(2.0)
            except LoiMuc as e:
                kq["danh_sach_phat"] = ("hong", "«{0}»: {1}".format(d["ten"], e))
                self.chup("ds-phat-hong")
                break
        return kq


# ═══════════════════════════ PHIÊN ══════════════════════════════════════════
def _nap_cdp():
    """Nạp `vm/cdp.py` + `vm/cdp_studio.py` ĐÚNG tệp (thư mục gốc cũng có một `cdp_studio.py` cũ — agent chèn gốc lên đầu sys.path)."""
    import importlib.util  # noqa: PLC0415
    if GOC in sys.path:
        sys.path.remove(GOC)
    sys.path.insert(0, GOC)
    mods = []
    for ten in ("cdp", "cdp_studio"):
        cu = sys.modules.get(ten)
        if cu is not None and os.path.dirname(os.path.abspath(getattr(cu, "__file__", "") or "")) != GOC:
            del sys.modules[ten]
        if ten not in sys.modules:
            spec = importlib.util.spec_from_file_location(ten, os.path.join(GOC, ten + ".py"))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[ten] = mod
            spec.loader.exec_module(mod)
        mods.append(sys.modules[ten])
    return mods[0], mods[1]


def don_launcher_mo_coi(kenh: str, ghi, cho_giay: float = 15.0) -> int:
    """Sau khi đóng Chrome: launcher Portable `<K>.exe` đôi khi KẸT lại không còn cây Chrome (chặn lần mở kế vì
    `_chrome_dang_chay` hỏi theo tên launcher). Đợi nó tự thoát; vẫn kẹt VÀ không còn tiến trình chrome.exe nào của
    hồ sơ kênh này thì tắt ĐÚNG launcher đó (theo PID, không /T, không đụng kênh khác). Trả số launcher đã tắt."""
    import subprocess  # noqa: PLC0415

    def liet_ke():
        lenh = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*\\" + kenh + "\\*' } | "
                "Select-Object ProcessId,Name | ConvertTo-Json -Compress")
        try:
            ra = subprocess.run(["powershell", "-NoProfile", "-Command", lenh], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=40,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            du = json.loads(ra.stdout.strip() or "[]")
        except Exception:  # noqa: BLE001
            return None
        return du if isinstance(du, list) else [du]
    het = time.monotonic() + cho_giay
    ds = liet_ke()
    while ds and time.monotonic() < het and any(str(x.get("Name", "")).lower() == kenh.lower() + ".exe" for x in ds):
        time.sleep(2)
        ds = liet_ke()
    if not ds:
        return 0
    chrome_con = [x for x in ds if str(x.get("Name", "")).lower() == "chrome.exe"]
    launcher = [x for x in ds if str(x.get("Name", "")).lower() == kenh.lower() + ".exe"]
    if chrome_con or not launcher:
        return 0
    n = 0
    for x in launcher:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(x["ProcessId"])], capture_output=True, timeout=15)
            n += 1
        except Exception:  # noqa: BLE001
            pass
    if n:
        ghi("đã tắt {0} launcher {1}.exe kẹt (không còn Chrome con)".format(n, kenh))
    return n


def in_khac_biet(kh: Dict[str, dict], ghi) -> None:
    for m in MUC:
        x = kh.get(m) or {}
        if x.get("khac") is None:
            dau = "?  KHÔNG ĐỌC ĐƯỢC"
        else:
            dau = "KHÁC" if x["khac"] else "đúng"
        ghi("   {0:<16} {1:<18} hiện: {2!s:<40} mong: {3!s:<40} {4}".format(
            TEN_MUC[m], dau, " ".join(str(x.get("hien")).split())[:40], " ".join(str(x.get("mong")).split())[:40], x.get("ghi") or ""))


def _hash_anh(hs: dict, thu_muc: str) -> Dict[str, str]:
    tl = _tl()
    return {m: sha_tep(tl.duong_anh(hs, m, thu_muc)) for m in ("logo", "banner", "hinh_mo")}


def chuan_bi_ho_so(kenh: str, ghi) -> dict:
    """Hồ sơ đủ + đúng luật; chưa có thì gọi phần 1 (`core.thiet_lap_kenh.tao`)."""
    tl = _tl()
    hs = tl.doc_ho_so(kenh)
    if not hs or tl.kiem_ho_so(hs, tl.thu_muc_thiet_lap(kenh)):
        ghi("chưa có hồ sơ đủ — dựng bằng core.thiet_lap_kenh.tao")
        hs = tl.tao(kenh, log=ghi)
    loi = tl.kiem_ho_so(hs, tl.thu_muc_thiet_lap(kenh))
    if loi:
        raise LoiMuc("hồ sơ chưa đạt luật: " + "; ".join(loi)[:200])
    return hs


def kiem_truoc_khi_chay(agent, kenh: str) -> None:
    if agent.van_ipv4_mo():
        raise Hoan("van IPv4 đang mở")
    # 14/10/2026: agent ghi cờ đăng dở ở `vm/logs/` (GOC), bản cũ chỉ nhìn `MyTool/logs/` (GOC_TOOL) → kiểm cả hai.
    for goc_co in (GOC_TOOL, GOC):
        if os.path.exists(os.path.join(goc_co, "logs", "dang-dodang.json")):
            raise Hoan("đang có máy đăng dở ({0}/logs/dang-dodang.json)".format(os.path.basename(goc_co)))


def nhuong_nuoi(kenh: str, ghi, cho_giay: float = 150.0) -> bool:
    """Kênh đang được nuôi trang chủ: ghi cờ `.dung`, đợi phiên nuôi đóng Chrome (<= cho_giay). True = đã trống."""
    pid = nuoi.chu_khoa(kenh)
    if not pid:
        return True
    try:
        with open(os.path.join(nuoi.THU_MUC_SO, kenh + ".dung"), "w", encoding="utf-8") as tep:
            tep.write(str(time.time()))
    except OSError:
        return False
    ghi("kênh {0} đang được nuôi trang chủ (pid {1}) — báo dừng sớm, đợi đóng Chrome".format(kenh, pid))
    han = time.monotonic() + cho_giay
    while nuoi.chu_khoa(kenh) and time.monotonic() < han:
        time.sleep(3)
    return not nuoi.chu_khoa(kenh)


def ly_do_dung(agent, kenh: str, luc: float) -> str:
    """Phải DỪNG ở bước kế? cờ `.dung` của agent, khung cấm, khe nang, việc đăng chờ — cùng luật với nuôi trang chủ."""
    if nuoi.co_dung(kenh):
        return "agent báo có việc đăng cần Chrome kênh (cờ .dung)"
    if khung_cam(luc, 0):
        return khung_cam(luc, 0)
    if CHO_KHE_NANG and nuoi.khe_nang_ban() and not _BO_QUA_KHE:
        return "khe nang của máy đang bận — nhường CPU"
    return nuoi.viec_dang_cho(agent, luc, kenh)


def chay_phien(kenh: str, ghi, thu: bool = False, mo_lai: bool = False, khong_luu: bool = False,
               bo_qua_khung: bool = False, rng=None, chi_ngon_ngu: bool = False) -> int:
    """`chi_ngon_ngu`: CHỈ kiểm/đặt ngôn ngữ Studio = ngôn ngữ ĐÍCH của kênh (`ngon_ngu_tai_khoan_dich`, mặc định Tiếng Việt) (không đụng hồ sơ, không ghi sổ thiết lập; kết quả
    ghi `logs/thiet-lap-kenh/<K>.ngon-ngu.json`); kết hợp `thu` = chỉ ĐỌC."""
    global _KHONG_GHI_SO, _BO_QUA_KHE
    _KHONG_GHI_SO = bool(thu or khong_luu or chi_ngon_ngu)
    _BO_QUA_KHE = bool(bo_qua_khung)
    rng = rng or random.Random()
    luc0 = time.time()
    so = doc_so(kenh)
    if mo_lai:
        # GIỮ thông tin từ chối tên/handle còn trong cửa sổ 14 ngày (không thử lại tên trước hạn)
        giu = {m for m in ("ten", "handle") if ten_handle_bi_chan(so, m, luc0)}
        so["muc"] = {m: ({"tt": "chua"} if (v or {}).get("tt") in ("can_nguoi", "hong", "cho") and m not in giu else v) for m, v in so["muc"].items()}
        so["tu_choi"] = {m: v for m, v in so["tu_choi"].items() if m in giu}
        so["trang_thai"], so["nghi_den_luc"] = "dang_lam", 0.0
        ghi("--mo-lai: xoá trạng thái can_nguoi/hong/từ chối cũ (giữ từ chối còn hạn: {0})".format(", ".join(sorted(giu)) or "không"))
    if not thu and not khong_luu and not chi_ngon_ngu:
        ok, ly = quyet_dinh(so, luc0, NGAN_SACH_PHIEN_PHUT, bo_qua_khung, bo_qua_lan=mo_lai)      # --mo-lai = lệnh chủ động: không tính trần phiên/ngày
        if not ok:
            ghi("bỏ qua: " + ly)
            return MA_KHONG_CAN if so.get("trang_thai") in ("can_nguoi", "xong") else MA_HOAN
    elif khung_cam(luc0, 0) and not bo_qua_khung:
        ghi("hoãn: " + khung_cam(luc0, 0))
        return MA_HOAN
    try:
        hs = {} if chi_ngon_ngu else chuan_bi_ho_so(kenh, ghi)
    except Exception as e:  # noqa: BLE001
        ghi("hồ sơ lỗi: {0}".format(str(e)[:200]))
        return 1
    agent = nuoi._nap_agent(ghi)                                    # noqa: SLF001
    try:
        kiem_truoc_khi_chay(agent, kenh)
        for r in (nuoi.viec_dang_cho(agent, luc0, kenh), "khe nang của máy đang bận" if (CHO_KHE_NANG and nuoi.khe_nang_ban() and not bo_qua_khung) else ""):
            # chi_ngon_ngu: gói chờ tải lên KHÔNG chặn — chính việc sửa ngôn ngữ mở đường cho gói đó (khoá Chrome kênh vẫn canh)
            if r and not (chi_ngon_ngu and "có gói chờ tải lên" in r):
                raise Hoan("nhường: " + r)
    except Hoan as h:
        ghi("hoãn: {0}".format(h))
        return MA_HOAN
    ch = nuoi.cau_hinh_kenh_moi(agent, kenh)
    chrome = agent.tim_chrome(ch)
    if not chrome:
        ghi("hoãn: không thấy Chrome Portable của kênh {0}".format(kenh))
        return MA_HOAN
    # Một phiên thiết lập MỘT LÚC trên máy (tuần tự) + khoá Chrome RIÊNG THEO KÊNH dùng chung với nuôi trang chủ.
    if not nuoi.giu_khoa("_thiet-lap", THU_MUC_KHOA_RIENG):
        ghi("hoãn: đang có phiên thiết lập kênh khác (tuần tự từng kênh)")
        return MA_HOAN
    khoa_kenh = khoa_mo = False
    cdp = st = S = None
    tu_mo, ma_thoat = False, 0
    phien = {"ngay": time.strftime("%Y-%m-%d", time.localtime(luc0)), "bat_dau": time.strftime("%H:%M", time.localtime(luc0)),
             "bat_dau_luc": luc0, "ket_qua": "đang chạy", "che_do": "thu" if thu else ("khong-luu" if khong_luu else "that")}
    try:
        if not nhuong_nuoi(kenh, ghi):
            ghi("hoãn: kênh {0} vẫn bận (phiên nuôi chưa nhả Chrome)".format(kenh))
            phien["ket_qua"] = "hoãn: nuôi chưa nhả"
            return MA_HOAN
        if not nuoi.giu_khoa(kenh):
            ghi("hoãn: kênh {0} đang có tiến trình khác giữ khoá Chrome".format(kenh))
            phien["ket_qua"] = "hoãn: khoá kênh"
            return MA_HOAN
        khoa_kenh = True
        nuoi.xoa_co_dung(kenh)
        if agent._chrome_dang_chay(chrome):                         # noqa: SLF001
            ghi("hoãn: Chrome kênh {0} đang chạy (không phải phiên của tôi)".format(kenh))
            phien["ket_qua"] = "hoãn: Chrome đang chạy"
            return MA_HOAN
        han = time.monotonic() + 180
        while not nuoi.giu_khoa("_mo"):
            if time.monotonic() > han:
                ghi("hoãn: chờ lượt mở Chrome quá 3 phút")
                return MA_HOAN
            time.sleep(3)
        khoa_mo = True
        r = nuoi.duoc_mo_them(len(nuoi.cac_kenh_dang_nuoi()) - 1, nuoi.ram_trong_gb())
        if r:
            ghi("hoãn: {0}".format(r))
            phien["ket_qua"] = "hoãn: " + r
            return MA_HOAN
        if not (thu or khong_luu or chi_ngon_ngu):
            so["phien"].append(phien)
            luu_so(so)
        ghi("── THIẾT LẬP KÊNH {0}{1} ──".format(kenh, " [CHỈ ĐỌC]" if thu else (" [không lưu]" if khong_luu else "")))
        cdp_mod, cdp_studio = _nap_cdp()
        agent.ghi_che_do_mat_cao(ch, False)
        cong = agent._cong_devtools(ch)                             # noqa: SLF001
        tu_mo = True
        nuoi.canh_tien_trien.bat_canh(lambda: (agent.dong_chrome_kenh(ch), nuoi.nha_khoa(kenh)), ghi=ghi)
        agent.mo_chrome_kenh(ch, "https://studio.youtube.com/", chrome, da_chay=False, quet=False)
        ws = agent._cho_devtools(cong, agent.CHO_DEVTOOLS_GIAY)     # noqa: SLF001
        nuoi.nha_khoa("_mo")
        khoa_mo = False
        if not ws:
            raise RuntimeError("Chrome mở nhưng cổng DevTools {0} không đáp".format(cong))
        cdp = cdp_mod.Cdp.mo(ws, nhat_ky=ghi)
        try:
            cdp.goi("Browser.setPermission", {"permission": {"name": "display-capture"}, "setting": "denied",
                                              "origin": "https://studio.youtube.com"}, han=10)
        except Exception:  # noqa: BLE001
            pass
        thu_muc_anh = os.path.join(THU_MUC_SO, kenh)
        st = cdp_studio.TrangStudio.mo_tab_moi(cdp, nhat_ky=ghi, thu_muc_dom=thu_muc_anh, rng=rng)
        S = Studio(st, ghi, thu_muc_anh)
        S.debug = bool(khong_luu)
        uc = S.vao_studio()
        so["uc"] = uc
        ghi("kênh Studio {0}".format(uc))
        # BƯỚC 0 — NGÔN NGỮ STUDIO (trước mọi mục: Studio tiếng Hàn làm hỏng mọi bước tìm theo chữ vi/ja/en)
        dich, ghi_chu_dich = ngon_ngu_dich_kenh(kenh)
        if ghi_chu_dich:
            ghi("   ⚠ " + ghi_chu_dich)
        ghi("   ngôn ngữ tài khoản ĐÍCH: {0} ({1})".format(dich, NGON_NGU_DICH[dich]["ten"]))
        nn = S.dat_ngon_ngu(ghi, chi_doc=thu, dich=dich)
        # BƯỚC 0b — ĐỊA ĐIỂM XEM (05/10): đúng nước của kênh, một lần như ngôn ngữ (skill, không phải việc mỗi lượt đăng)
        nn["dia_diem"] = S.dat_dia_diem(ghi, dia_diem_kenh(kenh), chi_doc=thu)
        if chi_ngon_ngu:
            nn["kenh"], nn["luc"] = kenh, time.strftime("%Y-%m-%d %H:%M:%S")
            if not thu:
                try:
                    with open(os.path.join(THU_MUC_SO, kenh + ".ngon-ngu.json"), "w", encoding="utf-8") as tep:
                        json.dump(nn, tep, ensure_ascii=False, indent=1)
                except OSError:
                    pass
            phien["ket_qua"] = "ngôn ngữ: " + nn["ket"]
            ghi("*** NGÔN NGỮ STUDIO {0}: {1} (trước {2!r} → sau {3!r}) ***".format(kenh, nn["ket"].upper(), nn["lang_truoc"], nn["lang_sau"]))
            return 0 if nn["ket"] in ("giong", "doi", "khac") else 1
        if nn["ket"] == "hong":
            hong_muc(so, "ngon_ngu", nn.get("ly_do") or "không đổi được sang {0}".format(NGON_NGU_DICH[dich]["ten"]))
            luu_so(so)
            raise RuntimeError("ngôn ngữ Studio không phải {0} và không đổi được: {1}".format(NGON_NGU_DICH[dich]["ten"], nn.get("ly_do")))
        ht, loi_doc = S.doc_hien_trang()
        ht["ngon_ngu_vi"] = nn["ket"] in ("giong", "doi")          # tên khoá cũ giữ cho tương thích: = ĐÚNG ngôn ngữ đích
        ht["ngon_ngu_dich_ten"] = NGON_NGU_DICH[dich]["ten"]
        for k, v in loi_doc.items():
            ghi("   không đọc được nhóm {0}: {1}".format(k, v))
        thu_muc_hs = _tl().thu_muc_thiet_lap(kenh)
        hh = _hash_anh(hs, thu_muc_hs)
        kh = khac_biet(hs, ht, so, hh)
        ghi("so với hồ sơ:")
        in_khac_biet(kh, ghi)
        if thu:
            phien["ket_qua"] = "thử: chỉ đọc"
            _ghi_thu(kenh, hs, ht, kh, loi_doc)
            return 0
        for m in ("ten", "handle", "logo", "banner", "hinh_mo"):
            if kh[m]["hien"] is not None and m not in so["truoc"]:
                so["truoc"][m] = kh[m]["hien"] if m in ("ten", "handle") else None
        so["truoc"].setdefault("mo_ta", (ht.get("mo_ta") or "")[:300])
        luu_so(so)
        # đúng rồi thì ghi `dat` luôn (không động vào)
        for m in MUC:
            if kh[m]["khac"] is False and (so["muc"][m].get("tt") != "dat"):
                dat_muc(so, m, kh[m]["mong"], luc0, "đã đúng sẵn — không sửa")
        _chay_nhom(S, hs, kh, so, ht, luc0, ghi, agent, kenh, khong_luu)
        phien["ket_qua"] = "xong lượt"
    except CanNguoi as c:
        ma_thoat = MA_CAN_NGUOI
        phien["ket_qua"] = "can_nguoi: {0}".format(c)
        if not thu:
            so["trang_thai"], so["ly_do"] = "can_nguoi", "cần người xử lý: {0} (không thử lại)".format(c)
            for m in MUC:
                if so["muc"][m].get("tt") != "dat":
                    hong_muc(so, m, "cần người: {0}".format(c), tt="can_nguoi")
        if S:
            S.chup("can-nguoi")
        ghi("DỪNG — cần người xử lý: {0} (không thử lại)".format(c))
    except Hoan as h:
        phien["ket_qua"] = "hoãn: {0}".format(h)
        ghi("hoãn: {0}".format(h))
        ma_thoat = MA_HOAN
    except Exception as loi:  # noqa: BLE001
        phien["ket_qua"] = "lỗi: {0}".format(str(loi)[:150])
        ghi("PHIÊN LỖI: {0}".format(str(loi)[:200]))
        if S:
            S.chup("phien-loi")
        ma_thoat = 1
    finally:
        phien["ket_thuc_luc"] = time.time()
        if not thu and phien in so["phien"]:
            tt, ly = tinh_trang(so) if so.get("trang_thai") != "can_nguoi" else ("can_nguoi", so.get("ly_do", ""))
            so["trang_thai"], so["ly_do"] = tt, ly
            if tt in ("hong", "dang_lam") and ma_thoat in (0, 1):
                so["nghi_den_luc"] = phien["ket_thuc_luc"] + NGHI_SAU_HONG_PHUT * 60
            try:
                luu_so(so)
            except OSError:
                pass
        try:
            if cdp:
                cdp.dong()
            if tu_mo:
                agent.dong_chrome_kenh(ch)
                don_launcher_mo_coi(kenh, ghi)
        finally:
            if khoa_mo:
                nuoi.nha_khoa("_mo")
            if khoa_kenh:
                nuoi.xoa_co_dung(kenh)
                nuoi.nha_khoa(kenh)
            nuoi.nha_khoa("_thiet-lap", THU_MUC_KHOA_RIENG)
    if not thu and ma_thoat == 0:
        if so.get("trang_thai") == "xong":
            d = tat_thiet_lap(kenh)
            ghi("*** XONG: {0} — {1} ***".format(so["ly_do"], ("đã ghi thiet_lap_kenh: false vào " + d) if d
                                                 else "KHÔNG ghi được false vào kenh.yaml, chủ tự tắt"))
            if ghi_ten_yaml(kenh, hs["ten"]):
                ghi("đã cập nhật `ten:` trong kenh.yaml theo tên mới")
            return 0
        return MA_HOAN if so.get("trang_thai") in ("hong", "dang_lam") else 0
    return ma_thoat


def _chay_nhom(S: Studio, hs, kh, so, ht, luc0, ghi, agent, kenh, khong_luu) -> None:
    """Từng nhóm: sửa mục KHÁC → ĐỌC LẠI xác nhận → ghi `dat`/`hong`. Dừng sớm nếu agent đòi Chrome."""
    nhom = (("ho_so", ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo")),
            ("cai_dat_kenh", ("quoc_gia", "tu_khoa")), ("mac_dinh", ("mac_dinh",)), ("ds_phat", ("danh_sach_phat",)))
    for ten_nhom, muc_nhom in nhom:
        if all(kh[m]["khac"] is False for m in muc_nhom):
            continue
        if _NHOM_CHON and ten_nhom not in _NHOM_CHON:
            continue
        if khong_luu and ten_nhom == "ds_phat":
            ghi("── nhóm ds_phat: [--khong-luu] bỏ qua (tạo danh sách phát là ghi thật vào kênh)")
            continue
        r = ly_do_dung(agent, kenh, time.time())
        if r:
            raise Hoan("dừng sớm nhường việc đăng: " + r)
        ghi("── nhóm {0}: {1}".format(ten_nhom, ", ".join(TEN_MUC[m] for m in muc_nhom if kh[m]["khac"] is not False)))
        try:
            if ten_nhom == "ho_so":
                kq = S.sua_ho_so(hs, kh, so, ht, luc0, ghi, khong_luu)
            elif ten_nhom == "cai_dat_kenh":
                kq = S.sua_cai_dat_kenh(hs, kh, khong_luu)
            elif ten_nhom == "mac_dinh":
                kq = S.sua_mac_dinh(hs, kh, khong_luu)
            else:
                kq = S.sua_ds_phat(hs, ht, ghi)
        except CanNguoi:
            raise
        except (LoiMuc, Exception) as e:  # noqa: BLE001
            ghi("   nhóm {0} hỏng: {1}".format(ten_nhom, str(e)[:160]))
            S.chup("nhom-{0}-hong".format(ten_nhom))
            for m in muc_nhom:
                if kh[m]["khac"] is not False and so["muc"][m].get("tt") != "dat":
                    hong_muc(so, m, str(e))
            luu_so(so)
            continue
        if khong_luu:
            continue
        _doc_lai_va_ghi(S, ten_nhom, muc_nhom, hs, kh, kq, so, luc0, ghi)
        luu_so(so)


def _doc_lai_va_ghi(S: Studio, ten_nhom: str, muc_nhom, hs, kh, kq, so, luc0, ghi) -> None:
    """ĐỌC LẠI Studio sau khi sửa; mục nào khớp hồ sơ → `dat`, còn lại → hong/cho/can_nguoi kèm lý do."""
    ht2: dict = {}
    loi: dict = {}
    try:
        if ten_nhom == "ho_so":
            d = S.doc_ho_so()
            ht2.update(ten=d["ten"], handle=d["handle"], mo_ta=d["mo_ta"],
                       anh={m: bool((d[m] or {}).get("co")) for m in ("logo", "banner", "hinh_mo")},
                       _src={m: (d[m] or {}).get("src") for m in ("logo", "banner", "hinh_mo")})
        elif ten_nhom in ("cai_dat_kenh", "mac_dinh"):
            S.doc_cai_dat(ht2, loi)
        else:
            S.doc_ds_phat(ht2, loi)
    except LoiMuc as e:
        loi["doc_lai"] = str(e)
    # Studio hay còn hiện handle cũ một lúc sau Xuất bản; trang công khai mới là nguồn thật → đối chiếu ở đó
    mong_h = str(so.get("handle_that") or hs.get("handle") or "").lstrip("@").lower()
    if "handle" in muc_nhom and mong_h and str(ht2.get("handle") or "").lstrip("@").lower() != mong_h:
        cong_khai = handle_cong_khai(so.get("uc"))
        if cong_khai and cong_khai.lstrip("@").lower() == mong_h:
            ht2["handle"] = mong_h
    so2 = json.loads(json.dumps(so))
    hh = _hash_anh(hs, _tl().thu_muc_thiet_lap(so["kenh"]))
    # logo/banner: Studio không cho so điểm ảnh → BẰNG CHỨNG ĐÃ LƯU = ảnh trên trang CÔNG KHAI đổi so với trước Xuất bản
    # (khung soạn thảo chưa lưu cũng hiện «có ảnh» nên KHÔNG đủ). Hình mờ: trang Hồ sơ đã TẢI LẠI (doc_ho_so mở lại URL) vẫn có ảnh.
    can_cong_khai = [m for m in ("logo", "banner") if m in muc_nhom and kq.get(m) is None and kh[m]["khac"]]
    bc = bang_chung_anh_luu((so.get("truoc") or {}).get("cong_khai") or {}, can_cong_khai, doc=lambda: doc_anh_cong_khai(so.get("uc")),
                            ngu=S.ngu) if can_cong_khai else {}
    chua_luu = {m: v[1] for m, v in bc.items() if not v[0]}
    for m in ("logo", "banner", "hinh_mo"):
        if m in muc_nhom and kq.get(m) is None and kh[m]["khac"] and m not in chua_luu:
            so2["muc"][m] = {"tt": "dat"}
            so2["hash_anh"][m] = hh[m]
    kh2 = khac_biet(hs, ht2, so2, hh)
    for m in muc_nhom:
        k = kq.get(m)
        if k and k[0] == "giong":
            if so["muc"][m].get("tt") != "dat":
                dat_muc(so, m, kh[m]["mong"], luc0, "đã đúng sẵn")
            continue
        if k and k[0] in ("cho", "can_nguoi", "hong"):
            if k[0] == "can_nguoi" and m in ("ten", "handle"):
                ghi_tu_choi(so, m, hs.get(m) if m == "ten" else (so.get("handle_that") or hs.get(m)), k[1], luc0)
            tt = {"cho": "cho", "can_nguoi": "can_nguoi", "hong": "hong"}[k[0]]
            hong_muc(so, m, k[1], tt=tt)
            if tt == "cho":
                so["muc"][m]["mo_lai_luc"] = time.time() + 6 * 3600
            ghi("   {0}: {1} — {2}".format(TEN_MUC[m], tt.upper(), k[1][:120]))
            continue
        if kh[m]["khac"] is False:
            continue
        if m in chua_luu:
            hong_muc(so, m, "Xuất bản KHÔNG lưu được ảnh: " + chua_luu[m])
            ghi("   {0}: HỎNG — {1}".format(TEN_MUC[m], chua_luu[m][:140]))
            continue
        x = kh2.get(m, {})
        if x.get("khac") is False:
            dat_muc(so, m, kh[m]["mong"], luc0, "đọc lại khớp")
            if m in ("logo", "banner", "hinh_mo"):
                so["hash_anh"][m] = hh[m]
            ghi("   {0}: ĐẠT (đọc lại khớp hồ sơ{1})".format(TEN_MUC[m], (" + " + bc[m][1]) if m in bc else ""))
        else:
            ly = "đọc lại KHÔNG khớp hồ sơ ({0})".format(x.get("ghi") or loi or "?")
            if m in ("ten", "handle"):
                ly = ("Studio không nhận giá trị mới (đọc lại: «{0}») — giới hạn đổi của YouTube, tự thử lại sau {1} "
                      "ngày").format(str(x.get("hien"))[:60], CUA_SO_DOI_TEN_NGAY)
                ghi_tu_choi(so, m, hs.get(m) if m == "ten" else (so.get("handle_that") or hs.get(m)), ly, luc0)
                hong_muc(so, m, ly, tt="cho")
            else:
                hong_muc(so, m, ly)
            ghi("   {0}: HỎNG — {1}".format(TEN_MUC[m], ly[:140]))
    # lượt đổi tên/handle ghi khi Xuất bản; ảnh ghi hash khi đạt


def _ghi_thu(kenh: str, hs: dict, ht: dict, kh: dict, loi: dict) -> None:
    os.makedirs(THU_MUC_SO, exist_ok=True)
    d = ["# Thử (chỉ đọc) — {0} — {1}".format(kenh, time.strftime("%Y-%m-%d %H:%M")), ""]
    for m in MUC:
        x = kh[m]
        d.append("- {0}: {1} · hiện «{2}» · mong «{3}» {4}".format(
            TEN_MUC[m], "?" if x["khac"] is None else ("KHÁC" if x["khac"] else "đúng"), str(x["hien"])[:60], str(x["mong"])[:60], x.get("ghi") or ""))
    if loi:
        d.append("\nLỗi đọc: " + json.dumps(loi, ensure_ascii=False))
    with open(os.path.join(THU_MUC_SO, kenh + ".thu.md"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(d) + "\n")


# ═══════════════════════════ PHIÊN KIỂM THƯƠNG HIỆU (14/10/2026) ═════════════
def duong_thuong_hieu(kenh: str) -> str:
    return os.path.join(THU_MUC_SO, kenh + ".thuong-hieu.json")


def ghi_thuong_hieu(kenh: str, kq: dict) -> str:
    """Ghi `<K>.thuong-hieu.json`; giữ tóm tắt <= 10 lần trước trong `lich_su`."""
    d = duong_thuong_hieu(kenh)
    try:
        with open(d, "r", encoding="utf-8") as tep:
            cu = json.load(tep) or {}
    except (OSError, ValueError):
        cu = {}
    ls = list(cu.get("lich_su") or []) if isinstance(cu, dict) else []
    if isinstance(cu, dict) and cu.get("luc"):
        ls.append({"luc": cu.get("luc"), "che_do": cu.get("che_do"), "ket_qua": cu.get("ket_qua"), "hinh_mo": cu.get("hinh_mo"),
                   "dat_hinh_mo": (cu.get("dat_hinh_mo") or {}).get("ket"), "dat_trang_chu": (cu.get("dat_trang_chu") or {}).get("ket"),
                   "dat_mo_ta": (cu.get("dat_mo_ta") or {}).get("ket")})
    kq["lich_su"] = ls[-10:]
    os.makedirs(THU_MUC_SO, exist_ok=True)
    with open(d + ".tam", "w", encoding="utf-8") as tep:
        json.dump(kq, tep, ensure_ascii=False, indent=1)
    os.replace(d + ".tam", d)
    return d


def anh_hinh_mo_kenh(kenh: str, uc: str, ghi, src_studio=()) -> Tuple[str, str]:
    """Ảnh hình mờ 150×150 của CHÍNH kênh: `thiet-lap/<hinh_mo>` của hồ sơ nếu có sẵn đúng cỡ; không thì cắt tròn từ ẢNH
    HỒ SƠ hiện tại (og:image trang công khai, dự phòng ảnh trên trang Hồ sơ Studio) bằng `anh_hinh_mo_tu_logo`.
    Ảnh dựng ghi vào `vm/logs/thiet-lap-kenh/<K>/` (không ghi vào CHANNEL). Trả (đường, nguồn); hỏng → LoiMuc."""
    tl = _tl()
    tm = tl.thu_muc_thiet_lap(kenh, GOC_TOOL)
    hs = tl.doc_ho_so(kenh, GOC_TOOL)
    d = tl.duong_anh(hs, "hinh_mo", tm) if hs else ""
    if d and os.path.isfile(d) and tl.kich_thuoc_anh(d) == tl.KICH_THUOC["hinh_mo"]:
        return d, "thiet-lap/" + os.path.basename(d)
    goc = [(doc_anh_cong_khai(uc) or {}).get("logo") or ""] + [goc_url_anh(u) for u in (src_studio or ()) if str(u).startswith("http")]
    thu_muc = os.path.join(THU_MUC_SO, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    nguon, loi = os.path.join(thu_muc, "anh-ho-so-goc.img"), ""
    import urllib.request  # noqa: PLC0415
    for u in [x for x in goc if x]:
        try:
            rq = urllib.request.Request(u + "=s800-c-k-c0x00ffffff-no-rj", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(rq, timeout=30) as r:
                b = r.read()
            if len(b) < 2000:
                raise ValueError("ảnh quá nhỏ ({0} byte)".format(len(b)))
            with open(nguon, "wb") as tep:
                tep.write(b)
            dich = tl.anh_hinh_mo_tu_logo(nguon, os.path.join(thu_muc, "hinh-mo.png"))
            if tl.kich_thuoc_anh(dich) != tl.KICH_THUOC["hinh_mo"]:
                raise ValueError("ảnh hình mờ không đúng 150×150")
            ghi("   ảnh hình mờ: cắt từ ảnh hồ sơ hiện tại → {0}".format(dich))
            return dich, "ảnh hồ sơ hiện tại của kênh"
        except Exception as e:  # noqa: BLE001
            loi = str(e)[:120]
    raise LoiMuc("không lấy được ảnh hồ sơ hiện tại của kênh để cắt hình mờ" + (": " + loi if loi else ""))


def chon_video_trang_chu(kenh: str, md, ghi, hom_nay=None) -> dict:
    """Video giới thiệu (tốt nhất) + video nổi bật (nhì) của CHÍNH kênh: xếp bằng `xep_video_gioi_thieu` trên
    `CHANNEL/<K>/chi-so/bang-tom-tat.csv` (từ `ngay_bat_dau` của kenh.yaml), rồi tra từng ứng viên đầu bảng trên danh sách
    Nội dung của Studio (`MayDangDom.tra_kenh`, CHỈ ĐỌC) — CSV không có chế độ hiển thị, chỉ nhận hàng «Công khai»."""
    import csv  # noqa: PLC0415
    nbd = _yaml_gia_tri(nuoi.duong_kenh_yaml(kenh) or "", "ngay_bat_dau")
    duong = os.path.join(GOC_TOOL, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv")
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            hang = list(csv.DictReader(tep))
    except OSError as e:
        raise LoiMuc("không đọc được {0}: {1}".format(duong, e))
    ung = xep_video_gioi_thieu(hang, nbd, hom_nay or datetime.now().date())[:SO_UNG_VIEN_TRA]
    ghi("   ứng viên video giới thiệu ({0} hàng CSV, từ {1}): {2}".format(len(hang), nbd or "?", " · ".join(
        "{0} {1:.0f}".format(u["vid"], u["diem"]) for u in ung) or "không có"))
    loai: Dict[str, str] = {}
    for u in ung:
        if sum(1 for v in loai.values() if v == "cong_khai") >= 2:
            break
        try:
            hang_st = [x for x in md.tra_kenh(u["tieu_de"], u["vid"]) if x.get("video_id") == u["vid"]]
        except Exception as e:  # noqa: BLE001 — không tra được = không nhận (không đoán là công khai)
            ghi("   tra {0} trên Studio lỗi: {1}".format(u["vid"], str(e)[:100]))
            hang_st = []
        loai[u["vid"]] = (hang_st[0].get("loai") or "khong_ro") if hang_st else ""
        ghi("   {0} «{1}»: Studio {2}".format(u["vid"], u["tieu_de"][:40], loai[u["vid"]] or "không thấy"))
    gt, nb, bo = chon_gioi_thieu(ung, loai)
    return {"gioi_thieu": gt, "noi_bat": nb, "bo": bo, "ung_vien": ung, "loai": loai, "ngay_bat_dau": nbd}


def duong_mo_ta_moi(kenh: str, luc: Optional[float] = None) -> str:
    """`workspace/chan-doan/mo-ta-<TLx>-<dd-mm>.txt` (bỏ đuôi `-T7`)."""
    ngan = re.sub(r"-T\d+$", "", kenh)
    return os.path.join(GOC_TOOL, "workspace", "chan-doan", "mo-ta-{0}-{1}.txt".format(ngan, time.strftime("%d-%m", time.localtime(luc))))


def mo_ta_anh_em(kenh: str) -> List[str]:
    """Mô tả THẬT (đọc ở Studio, `mo_ta_hien` của `<K>.thuong-hieu.json`) của kênh khác CÙNG nhóm kenh.yaml."""
    tl = _tl()
    nhom = str(tl._yaml_kenh(kenh, GOC_TOOL).get("nhom") or "")        # noqa: SLF001
    ra = []
    try:
        ten = sorted(os.listdir(THU_MUC_SO))
    except OSError:
        return ra
    for t in ten:
        k = t[:-len(".thuong-hieu.json")] if t.endswith(".thuong-hieu.json") else ""
        if not k or k == kenh or "." in k or (nhom and str(tl._yaml_kenh(k, GOC_TOOL).get("nhom") or "") != nhom):   # noqa: SLF001
            continue
        try:
            with open(os.path.join(THU_MUC_SO, t), "r", encoding="utf-8") as tep:
                mt = str((json.load(tep) or {}).get("mo_ta_hien") or "").strip()
        except (OSError, ValueError):
            continue
        if mt:
            ra.append(mt)
    return ra


def viet_mo_ta_kenh(kenh: str, ten_kenh: str, ghi, goi=None) -> Tuple[str, str]:
    """Mô tả kênh mới (tiếng Nhật 150–300 ký tự) qua `core.goi_van_ban` (Claude Max, lùi ShopAPI), tối đa 3 lượt tới khi
    `kiem_mo_ta_kenh` đạt; ghi `workspace/chan-doan/mo-ta-<TLx>-<dd-mm>.txt`. Tệp hôm nay đã có + đạt → dùng lại (không
    tốn lượt). Trả (chữ, đường tệp); không đạt → LoiMuc."""
    d = duong_mo_ta_moi(kenh)
    try:
        with open(d, "r", encoding="utf-8") as tep:
            cu = lam_sach_mo_ta_kenh(tep.read())
        if cu and not kiem_mo_ta_kenh(cu):
            ghi("   mô tả: dùng lại {0} ({1} ký tự)".format(d, do_dai_mo_ta(cu)))
            return cu, d
    except OSError:
        pass
    tl = _tl()
    kh = tl._yaml_kenh(kenh, GOC_TOOL)                                    # noqa: SLF001
    csv_d = os.path.join(GOC_TOOL, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv")
    try:
        import csv  # noqa: PLC0415
        with open(csv_d, "r", encoding="utf-8-sig", newline="") as tep:
            thang = [u["tieu_de"] for u in xep_video_gioi_thieu(list(csv.DictReader(tep)), kh.get("ngay_bat_dau"),
                                                               datetime.now().date(), toi_thieu_ngay=0)[:6]]
    except OSError:
        thang = []
    mau = mo_ta_anh_em(kenh)
    ghi("   mô tả: viết bằng LLM (tiêu đề thắng {0}, mô tả kênh anh em {1})".format(len(thang), len(mau)))
    if goi is None:
        from core.goi_van_ban import goi_van_ban, tin_nhan_viet  # noqa: PLC0415
        try:
            client = tl.tao_goi_llm().client
        except Exception as e:  # noqa: BLE001 — không có ví thì vẫn đi Claude Max (goi_van_ban tự quyết)
            ghi("   (không dựng được client ShopAPI: {0})".format(str(e)[:100]))
            client = None
        goi = lambda p: goi_van_ban(client, tin_nhan_viet(p), toi_da_token=4096, on_log=ghi)   # noqa: E731
    hoi, loi = loi_nhac_mo_ta_kenh(ten_kenh, kh, thang, mau), []
    for _ in range(3):
        chu = lam_sach_mo_ta_kenh(goi(hoi + (("\nPREVIOUS ANSWER WAS REJECTED: " + "; ".join(loi) + ". Fix it.") if loi else "")))
        loi = kiem_mo_ta_kenh(chu)
        if not loi:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            with open(d, "w", encoding="utf-8") as tep:
                tep.write(chu + "\n")
            ghi("   mô tả: {0} ký tự → {1}".format(do_dai_mo_ta(chu), d))
            return chu, d
        ghi("   mô tả LLM chưa đạt: {0}".format("; ".join(loi)))
    raise LoiMuc("LLM viết mô tả kênh chưa đạt sau 3 lượt: " + "; ".join(loi))


def _cfg_kenh(agent, kenh: str) -> dict:
    """Cấu hình agent có `kenh` trong `cac_kenh` (kênh mới nối đuôi như `nuoi.cau_hinh_kenh_moi`) → đúng cổng DevTools."""
    cfg = agent.doc_cau_hinh()
    cac = list(agent.danh_sach_kenh(cfg))
    for k in nuoi.KENH_MOI_THU_TU + (kenh,):
        if k not in cac:
            cac.append(k)
    return dict(cfg, cac_kenh=cac)


def chay_thuong_hieu(kenh: str, ghi, dat: bool = False, bo_qua_khung: bool = False, rng=None,
                     trang_chu: bool = False, mo_ta: bool = False, khong_luu: bool = False) -> int:
    """`--kiem-thuong-hieu` (CHỈ ĐỌC) [+ `--dat-hinh-mo`] [+ `--dat-trang-chu`] [+ `--dat-mo-ta`]. Luật như máy DOM: khoá máy
    `.khoa-may` (bận → hoãn, không ép), khoá Chrome kênh + một phiên thiết lập một lúc, van IPv4 mở → hoãn, Chrome kênh có
    sẵn thì chỉ mở/đóng TAB của mình, tạm giao diện vi (MayDangDom.lay_uc: đúng UC ghim) rồi TRẢ ngôn ngữ cũ. Không ghi sổ
    thiết lập `<K>.json`. `khong_luu`: trang chủ / mô tả điền xong thì BỎ (không Xuất bản). Mã: 0 xong · 10 hoãn ·
    20 cần người · 1 lỗi."""
    rng = rng or random.Random()
    luc0 = time.time()
    du_kien = DU_KIEN_TRANG_CHU_PHUT if (trang_chu or mo_ta) else (DU_KIEN_DAT_PHUT if dat else DU_KIEN_KIEM_PHUT)
    r = "" if bo_qua_khung else (khung_cam(luc0, du_kien) or khung_gio_tron(luc0, du_kien))
    if r:
        ghi("hoãn: " + r)
        return MA_HOAN
    agent = nuoi._nap_agent(ghi)                                    # noqa: SLF001
    try:
        kiem_truoc_khi_chay(agent, kenh)
        if os.path.exists(os.path.join(GOC, "logs", "dang-dodang.json")):
            raise Hoan("đang có máy đăng dở (vm/logs/dang-dodang.json)")
        r = nuoi.viec_dang_cho(agent, luc0, kenh)
        if r:
            raise Hoan("nhường: " + r)
    except Hoan as h:
        ghi("hoãn: {0}".format(h))
        return MA_HOAN
    if not nuoi.giu_khoa("_thiet-lap", THU_MUC_KHOA_RIENG):
        ghi("hoãn: đang có phiên thiết lập kênh khác (tuần tự)")
        return MA_HOAN
    khoa_may = khoa_kenh = da_doc = False
    cdp = cdp_mod = md = S = None
    ma = 0
    che_do = "+".join(["kiem"] + [x for x, b in (("dat", dat), ("trang-chu", trang_chu), ("mo-ta", mo_ta), ("khong-luu", khong_luu)) if b])
    kq: dict = {"kenh": kenh, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "che_do": che_do, "ket_qua": "đang chạy"}
    try:
        if not agent.giu_khoa_may_chung(viec="thiet_lap", kenh=kenh, uu_tien=1):
            raise Hoan("khoá máy (.khoa-may) đang bận — không ép")
        khoa_may = True
        if not nuoi.giu_khoa(kenh):
            raise Hoan("kênh {0} đang có tiến trình khác giữ khoá Chrome".format(kenh))
        khoa_kenh = True
        nuoi.xoa_co_dung(kenh)
        cdp_mod, cdp_studio = _nap_cdp()
        import may_dang_dom as mdd                                  # noqa: PLC0415 — sau _nap_cdp: đúng vm/
        cfg = _cfg_kenh(agent, kenh)
        if not cdp_mod.hoi_phien_ban(agent._cong_devtools(agent.cau_hinh_kenh(cfg, kenh))):   # noqa: SLF001
            r = nuoi.duoc_mo_them(len(nuoi.cac_kenh_dang_nuoi()), nuoi.ram_trong_gb())
            if r:
                raise Hoan(r)
        try:
            cdp = cdp_mod.ket_noi_kenh(cfg, kenh, nhat_ky=ghi)
        except cdp_mod.CdpKhongDung as e:
            raise Hoan("không nối được Chrome kênh: {0} (mã {1})".format(e.ly_do, e.ma))
        ghi("── KIỂM THƯƠNG HIỆU {0}{1} — Chrome cổng {2}{3} ──".format(
            kenh, "".join(x for x, b in ((" + ĐẶT HÌNH MỜ nếu thiếu", dat), (" + TRANG CHỦ (bật, video giới thiệu/nổi bật, phổ biến)", trang_chu),
                                         (" + MÔ TẢ nếu trống", mo_ta), (" [KHÔNG LƯU]", khong_luu)) if b) or " [CHỈ ĐỌC]", cdp.cong,
            " (máy này tự mở)" if cdp.tu_mo else " (có sẵn — chỉ mở/đóng TAB của mình)"))
        nuoi.canh_tien_trien.bat_canh(lambda: (cdp_mod.dong_trinh_duyet(cdp) if cdp.tu_mo else cdp.dong()), ghi=ghi)
        bo = cdp_studio.doc_bo_chon()
        thu_muc_anh = os.path.join(THU_MUC_SO, kenh)
        md = mdd.MayDangDom(kenh, bo, lambda: cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=ghi, thu_muc_dom=thu_muc_anh, rng=rng),
                            mdd.SoVideoId(), bao=None, thu_muc_done="", nhat_ky=ghi)
        S = Studio(md.tab_b(), ghi, thu_muc_anh)
        try:
            S.uc = md.lay_uc()                                      # đúng UC đã ghim + tạm giao diện vi (trả lại cuối phiên)
        except mdd.DungKenh as e:
            raise CanNguoi(str(e))
        except Exception:  # noqa: BLE001
            S.kiem_chan()                                           # đăng xuất / xác minh → CanNguoi
            raise
        S.kiem_chan()
        kt, loi = S.doc_thuong_hieu()
        da_doc = True
        hm, td, dsp = kt["hinh_mo"], kt["tieu_diem"], kt["ds_phat"]
        hs0 = kt.get("_ho_so") or {}
        kq.update(hinh_mo=hm, tieu_diem={k: v.get("co") for k, v in td.items()}, trang_chu_bat=kt.get("trang_chu_bat"),
                  ds_phat=dsp, anh=kt["anh"], loi_doc=loi, ten_kenh=hs0.get("ten"), mo_ta_hien=str(hs0.get("mo_ta") or ""),
                  chi_tiet={"hinh_mo": kt.get("_hinh_mo_tho"), "tieu_diem": td,
                            "trang_chu": {k: (kt.get("_trang_chu") or {}).get(k) for k in ("url", "tab", "ds", "cong_tac", "chu")}})
        ghi("   hình mờ: {0} · hiển thị: {1} «{2}»".format({True: "CÓ", False: "THIẾU", None: "?"}[hm["co"]], hm["thoi_gian"], hm["nhan"]))
        ghi("   thẻ Trang chủ bật: {0} · trailer người chưa đăng ký: {1} · video nổi bật người đăng ký quay lại: {2} · "
            "danh sách phát: {3}".format(kt.get("trang_chu_bat"), td["trailer"]["co"], td["noi_bat"]["co"], dsp["so"]))
        for k, v in loi.items():
            ghi("   không đọc được {0}: {1}".format(k, v))
        if dat:
            ok, ly = can_dat_hinh_mo(hm)
            if not ok:
                kq["dat_hinh_mo"] = {"ket": "bo", "ly_do": ly}
                ghi("   đặt hình mờ: bỏ — " + ly)
            else:
                r = ly_do_dung(agent, kenh, time.time()) or ("" if bo_qua_khung else khung_gio_tron(time.time(), DU_KIEN_DAT_PHUT / 2))
                if r:
                    raise Hoan("trước khi đặt hình mờ: " + r)
                duong, nguon = anh_hinh_mo_kenh(kenh, S.uc, ghi, ((kt.get("_ho_so") or {}).get("logo") or {}).get("src") or ())
                kq["anh_hinh_mo"] = {"duong": duong, "nguon": nguon}
                kq["dat_hinh_mo"] = S.dat_hinh_mo(duong, ghi)
                ghi("*** HÌNH MỜ {0}: {1} {2} ***".format(kenh, kq["dat_hinh_mo"]["ket"].upper(), kq["dat_hinh_mo"].get("ly_do") or ""))
        if trang_chu:
            r = ly_do_dung(agent, kenh, time.time()) or ("" if bo_qua_khung else khung_gio_tron(time.time(), DU_KIEN_TRANG_CHU_PHUT / 2))
            if r:
                raise Hoan("trước khi đặt trang chủ: " + r)
            cv = chon_video_trang_chu(kenh, md, ghi)
            kq["chon_video"] = {k: cv[k] for k in ("gioi_thieu", "noi_bat", "bo", "loai", "ngay_bat_dau")}
            ghi("   video giới thiệu: {0} · video nổi bật: {1}".format(*(("«{0}» ({1})".format(v["tieu_de"][:50], v["vid"]) if v else "KHÔNG CÓ")
                                                                    for v in (cv["gioi_thieu"], cv["noi_bat"]))))
            kq["dat_trang_chu"] = S.dat_trang_chu(cv["gioi_thieu"], cv["noi_bat"], ghi, khong_luu=khong_luu)
            ghi("*** TRANG CHỦ {0}: {1} {2} ***".format(kenh, kq["dat_trang_chu"]["ket"].upper(), kq["dat_trang_chu"].get("ly_do") or ""))
        if mo_ta:
            if kq["mo_ta_hien"].strip():
                kq["dat_mo_ta"] = {"ket": "bo", "ly_do": "kênh đã có mô tả ({0} ký tự) — không đụng".format(len(kq["mo_ta_hien"]))}
            else:
                r = ly_do_dung(agent, kenh, time.time()) or ("" if bo_qua_khung else khung_gio_tron(time.time(), DU_KIEN_DAT_PHUT / 2))
                if r:
                    raise Hoan("trước khi đặt mô tả: " + r)
                chu, duong = viet_mo_ta_kenh(kenh, kq.get("ten_kenh") or "", ghi)
                kq["dat_mo_ta"] = dict(S.dat_mo_ta(chu, ghi, khong_luu=khong_luu), chu=chu, tep=duong)
            ghi("*** MÔ TẢ {0}: {1} {2} ***".format(kenh, kq["dat_mo_ta"]["ket"].upper(), kq["dat_mo_ta"].get("ly_do") or ""))
        kq["ket_qua"] = "xong"
    except CanNguoi as c:
        ma, kq["ket_qua"] = MA_CAN_NGUOI, "can_nguoi: {0}".format(c)
        if S:
            S.chup("can-nguoi")
        ghi("DỪNG — cần người xử lý: {0} (không thử lại)".format(c))
    except Hoan as h:
        ma, kq["ket_qua"] = MA_HOAN, "hoãn: {0}".format(h)
        ghi("hoãn: {0}".format(h))
    except Exception as e:  # noqa: BLE001
        ma, kq["ket_qua"] = 1, "lỗi: {0}".format(str(e)[:200])
        ghi("PHIÊN LỖI: {0}".format(str(e)[:200]))
        if S:
            S.chup("thuong-hieu-loi")
    finally:
        try:
            if md is not None:
                md.dong_het()                                       # CHỈ tab của phiên này
            if cdp is not None:
                try:
                    import ngon_ngu_tam  # noqa: PLC0415
                    ngon_ngu_tam.tra(cdp, kenh, ghi)
                except Exception as e:  # noqa: BLE001
                    ghi("trả ngôn ngữ giao diện lỗi: {0}".format(str(e)[:120]))
                if cdp.tu_mo:
                    ghi("đóng Chrome kênh {0} (máy này đã mở): {1}".format(kenh, "đã đóng" if cdp_mod.dong_trinh_duyet(cdp) else "CỔNG CHƯA ĐÓNG"))
                    don_launcher_mo_coi(kenh, ghi)
                else:
                    cdp.dong()
        finally:
            if khoa_kenh:
                nuoi.xoa_co_dung(kenh)
                nuoi.nha_khoa(kenh)
            if khoa_may:
                agent.nha_khoa_may_chung()
            nuoi.nha_khoa("_thiet-lap", THU_MUC_KHOA_RIENG)
        if da_doc or ma in (MA_CAN_NGUOI, 1):
            try:
                ghi("đã ghi {0}".format(ghi_thuong_hieu(kenh, kq)))
            except OSError as e:
                ghi("không ghi được kết quả: {0}".format(e))
    return ma


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="Tự thiết lập kênh YouTube trên Studio theo hồ sơ.")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--thu", action="store_true", help="chỉ ĐỌC Studio + in khác biệt, không sửa, không ghi sổ")
    ap.add_argument("--mo-lai", action="store_true", help="xoá can_nguoi/hong/từ chối cũ rồi chạy")
    ap.add_argument("--khong-luu", action="store_true", help="(dev) điền nhưng KHÔNG Xuất bản/Lưu")
    ap.add_argument("--bo-qua-khung", action="store_true", help="(dev) bỏ khung cấm 02–07h")
    ap.add_argument("--ngon-ngu", action="store_true", help="CHỈ kiểm/đặt ngôn ngữ Studio = đích của kênh (ngon_ngu_tai_khoan_dich, mặc định vi) (kèm --thu = chỉ đọc)")
    ap.add_argument("--nhom", default="", help="(dev) chỉ chạy nhóm: ho_so,cai_dat_kenh,mac_dinh,ds_phat")
    ap.add_argument("--kiem-thuong-hieu", action="store_true",
                    help="CHỈ ĐỌC hình mờ + thời gian hiển thị, trailer/video nổi bật (Thẻ Trang chủ), số danh sách phát → <K>.thuong-hieu.json")
    ap.add_argument("--dat-hinh-mo", action="store_true", help="(kèm --kiem-thuong-hieu) kênh THIẾU hình mờ thì đặt, hiển thị toàn bộ video")
    ap.add_argument("--dat-trang-chu", action="store_true",
                    help="bật Thẻ Trang chủ + video giới thiệu (video thắng nhất, công khai, >=7 ngày) + video nổi bật (nhì) + phần Video phổ biến")
    ap.add_argument("--dat-mo-ta", action="store_true", help="kênh đang để TRỐNG mô tả thì viết (LLM, tiếng Nhật 150–300 ký tự) + đặt")
    a = ap.parse_args(argv)
    ghi = _nhat_ky(a.kenh)
    d = nuoi.duong_kenh_yaml(a.kenh)
    if not d:
        ghi("không thấy kenh.yaml của {0}".format(a.kenh))
        return 1
    if a.kiem_thuong_hieu or a.dat_hinh_mo or a.dat_trang_chu or a.dat_mo_ta:   # không cần thiet_lap_kenh: true, không đụng sổ thiết lập
        return chay_thuong_hieu(a.kenh, ghi, dat=a.dat_hinh_mo, bo_qua_khung=a.bo_qua_khung, trang_chu=a.dat_trang_chu,
                                mo_ta=a.dat_mo_ta, khong_luu=a.khong_luu)
    if not a.thu and not a.khong_luu and not a.ngon_ngu and not thiet_lap_bat(a.kenh) and not a.mo_lai:
        so = doc_so(a.kenh)
        ghi("kênh {0} không bật thiet_lap_kenh: true — không chạy{1}".format(a.kenh, " (đã xong)" if so.get("trang_thai") == "xong" else ""))
        return MA_KHONG_CAN
    global _NHOM_CHON
    _NHOM_CHON = {x.strip() for x in a.nhom.split(",") if x.strip()} or None
    return chay_phien(a.kenh, ghi, thu=a.thu, mo_lai=a.mo_lai, khong_luu=a.khong_luu, bo_qua_khung=a.bo_qua_khung, chi_ngon_ngu=a.ngon_ngu)


if __name__ == "__main__":
    sys.exit(main())
