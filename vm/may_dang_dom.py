"""MÁY ĐĂNG DOM/CDP — đăng video lên Studio bằng DOM qua cổng DevTools.

Thiết kế đã duyệt: `workspace/THIET-KE-MAY-DANG-DOM.md` (29/09/2026). Máy đăng
cũ `may_dang.py` (dò ảnh PyAutoGUI) giữ làm ĐƯỜNG LÙI.

Cách chạy:

    python vm/may_dang_dom.py --kenh TL1-T7 --mot-lan [--trong-phien]
    python vm/may_dang_dom.py --kiem-dom --kenh TL1-T7 [--sau] [--ghi-dom-day-du]
    python vm/may_dang_dom.py --kenh TL1-T7 --ma TL1-T7-0007 --bo-loc-ngay

Mã thoát (hợp đồng mục 8 — agent dựa vào đây để quyết có lùi đường ảnh không):

    0  xong / không có mã nào cần đăng / --kiem-dom đạt
    1  hỏng SAU khi đã chạm kênh (đã có videoId) — KHÔNG lùi; lượt sau tiếp nháp
    3  đường DOM không dùng được TRƯỚC khi chạm kênh — được lùi đường ảnh
    4  bị chặn an toàn (van IPv4, khoá máy, sai kênh, máy DOM khác đang chạy)

Chống trùng + chống nháp thừa (mục 3): sổ bền `vm/logs/so-video-id.json`
(ghi nguyên tử — tệp tạm cạnh sổ + os.replace; KHÔNG nằm %TEMP%, KHÔNG chung
với `dang-dodang.json` mà may_dang xoá sau mỗi mã). videoId được ghi NGAY khi
Studio hiện link video, và báo trạm "ĐANG ĐĂNG · nháp <id>" — dòng không còn
EDIT XONG nên đường ảnh tự bỏ qua; lượt sau thấy id trong sổ là mở lại đúng
bản nháp ấy thay vì tải thêm một bản.

Luật an toàn: không bao giờ bật IPv4; không `close_browsers_gently_in_rdp`,
không taskkill, không đụng %TEMP%; chỉ đóng TAB của mình (Chrome do agent mở
thì agent đóng cuối phiên). Nháp thừa trên kênh: CHỈ BÁO, không xoá.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import socket
import struct
import sys
import time
import unicodedata
import urllib.parse
from datetime import date, datetime, timedelta

GOC = os.path.dirname(os.path.abspath(__file__))
if GOC not in sys.path:
    sys.path.insert(0, GOC)

THU_MUC_LOG = os.path.join(GOC, "logs")
DUONG_SO = os.path.join(THU_MUC_LOG, "so-video-id.json")
DUONG_UC = os.path.join(THU_MUC_LOG, "kenh-uc.json")
THU_MUC_KIEM = os.path.join(THU_MUC_LOG, "kiem-dom")
DUONG_DODANG = os.path.join(THU_MUC_LOG, "dang-dodang.json")
DUONG_BAO_CAO = os.path.join(THU_MUC_LOG, "dang-dom-cuoi.json")
CONG_KHOA = 8770
TRAN_TAI_MOI_NGAY = 2
#: Trần số gói TẢI MỚI mỗi kênh mỗi ngày ở chế độ tải bổ sung (--cua-so-gio).
#: 30/09/2026: 3 → 6 (nhịp 6 khe/ngày; agent truyền `--toi-da-ngay` theo
#: `agent.TAI_LEN_TOI_DA_KENH_NGAY`). Trần 3 cũ bỏ TL1-T7-0012 (hẹn 01/10 20:00)
#: vì 0009/0010/0011 đã tải trong ngày.
TAI_LEN_TOI_DA_NGAY = 6
HAN_MHKT_GIAY = 600
HAN_PHIEN_MAC_DINH = 90 * 60
#: 30/09/2026 — CHỜ TẢI XONG 100%: không bao giờ bấm Lên lịch / đóng tab khi chưa
#: có BẰNG CHỨNG tải xong. Hạn chờ = max(10 phút, dung lượng ÷ 1 MB/s × 2); còn
#: thấy % tăng thì kéo dài, trần cứng `CHO_TAI_TRAN_GIAY` (và không quá hạn phiên).
CHO_TAI_TOI_THIEU_GIAY = 600
TOC_DO_TAI_THAP_MB_GIAY = 1.0
CHO_TAI_TRAN_GIAY = 75 * 60
#: Số view 48h cho thẻ lấy từ bản QUÉT NGÀY gần nhất nếu không cũ hơn ngần này
#: giờ; cũ hơn/thiếu thì đọc nhanh trang Số liệu phân tích của kênh (tab B).
TUOI_48H_TOI_DA_GIO = 30.0
#: Trạng thái sổ của gói có video đã lên kênh (nguồn nhập MHKT hợp lệ nếu `mhkt` = ok…).
TT_SO_DA_LEN_KENH = ("xac-nhan", "da-len-lich", "lech-lich", "chua-xac-nhan")
#: 01/10/2026 — BÙ MHKT video cũ (agent gọi `--bu-mhkt` giờ vắng): tối đa ngần này
#: video/kênh/đêm; hỏng ngần này đêm liền thì thôi (vẫn nằm trong mhkt-thieu.json kèm lý do).
BU_MHKT_TOI_DA_DEM = 3
BU_MHKT_TOI_DA_LOI = 3
#: YouTube chỉ cho màn hình kết thúc với video ≥25 giây; Shorts không có mục MHKT.
MHKT_NGAN_NHAT_GIAY = 25
SHORTS_TOI_DA_GIAY = 180

MA_XONG, MA_HONG, MA_LUI, MA_CHAN = 0, 1, 3, 4

TRANG_THAI_OK = "EDIT XONG"
TIEN_TO_DANG_DANG = "ĐANG ĐĂNG"

log = logging.getLogger("may_dang_dom")

#: Chữ trạng thái mặc định (khớp `chu_trang_thai` của studio-selectors.json).
#: Studio TL4 hiển thị TIẾNG NHẬT (đo 29/09/2026: "公開", "2026/09/28 公開日") —
#: giữ đủ ba thứ tiếng.
CHU_TRANG_THAI = {
    "da_len_lich": ["Đã lên lịch", "Scheduled", "予約済み", "予約", "公開予約"],
    "cong_khai": ["Công khai", "Public", "公開"],
    "khong_cong_khai": ["Không công khai", "Unlisted", "限定公開"],
    "rieng_tu": ["Riêng tư", "Private", "非公開"],
    "nhap": ["Nháp", "Draft", "下書き"],
    "loi_tai": ["Tải lên không thành công", "Đã xảy ra lỗi", "đã bị hủy", "アップロードに失敗", "エラーが発生"],
    # 30/09/2026 — tiến độ tải lên (đo thật ở `ytcp-video-upload-progress`: "Đã tải được
    # 83% … Còn 24 giây" → "Đã hoàn tất quá trình tải lên … Quá trình xử lý sẽ sớm bắt
    # đầu" → "Đang xử lý đến độ phân giải tối đa là HD …" → "Đang kiểm tra 14% …" →
    # "Đã kiểm tra xong. Không phát hiện vấn đề nào."). Xử lý/kiểm tra chỉ chạy SAU khi
    # tải xong, nên cũng là bằng chứng tải xong.
    "da_tai_xong": ["Đã hoàn tất quá trình tải lên", "Đã tải lên", "Tải lên hoàn tất", "Upload complete",
                    "アップロード完了", "アップロードが完了"],
    "dang_xu_ly": ["Đang xử lý", "Processing", "処理中"],
    "dang_kiem_tra": ["Đang kiểm tra", "Checking", "チェック中"],
    "xu_ly_xong": ["Đã kiểm tra xong", "Checks complete", "Đã xử lý", "チェック完了", "処理が完了"],
    "dang_tai": ["Đã tải được", "Đang tải lên", "Uploading", "アップロード中"],
    "tai_do": ["bị gián đoạn", "chưa hoàn tất", "Tải lên không thành công", "đã bị hủy",
               "interrupted", "Upload failed", "Processing abandoned", "アップロードが中断", "処理が中止"],
    "mhkt_khong_nguon": ["không có màn hình kết thúc để nhập", "no end screen to import",
                         "doesn't have an end screen", "終了画面がありません"],
}
#: Thứ tự dò có chủ ý: "Không công khai" ⊃ "công khai", "限定公開"/"非公開" ⊃ "公開"
#: → không công khai, riêng tư dò TRƯỚC công khai.
_THU_TU_LOAI = ("loi_tai", "nhap", "da_len_lich", "khong_cong_khai", "rieng_tu", "cong_khai")
LOAI_DA_DANG = ("da_len_lich", "cong_khai", "khong_cong_khai")
#: Trạng thái SỔ nghĩa là đã bấm «Lên lịch» (chống trùng khi kênh không đọc được hàng).
TT_SO_DA_HEN = ("da-len-lich", "xac-nhan", "lech-lich", "chua-xac-nhan")
#: Số lượt `chua_xac_nhan` liền cho một gói trước khi thôi mở Chrome kiểm lại.
TRAN_CHUA_XAC_NHAN = 3


class LoiTruoc(Exception):
    """Hỏng TRƯỚC khi chạm kênh (chưa chọn tệp) → mã 3, được lùi."""


class LoiSau(Exception):
    """Hỏng SAU khi đã chạm kênh (có/có thể có bản nháp) → mã 1, không lùi."""


class DungKenh(Exception):
    """Sai kênh (UC lệch ghim) → dừng kênh, mã 4."""


# ═══ HÀM THUẦN ═══════════════════════════════════════════════════════════

def chuan_hoa_tieu_de(s) -> str:
    """NFKC + gộp khoảng trắng + bỏ đầu cuối — so tiêu đề kế hoạch ↔ kênh."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


_ID = r"([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])"


def rut_video_id(href) -> str:
    """videoId 11 ký tự từ youtu.be/…, /video/…/, watch?v=…, /shorts/… ('' nếu không)."""
    s = str(href or "")
    # `/vi/<id>/`: ảnh thu nhỏ i9.ytimg.com — hàng NHÁP trên danh sách Studio
    # không có link /video/<id>, id chỉ nằm ở ảnh (đo 29/09/2026).
    for mau in (r"youtu\.be/" + _ID, r"/video/" + _ID, r"[?&]v=" + _ID, r"/shorts/" + _ID,
                r"/vi(?:_webp)?/" + _ID):
        m = re.search(mau, s)
        if m:
            return m.group(1)
    return ""


_THANG_EN = {t: i + 1 for i, t in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}


def phan_tich_ngay(chu):
    """Ngày trong chữ Studio/kế hoạch: `30 thg 9, 2026`, `30 tháng 9, 2026`,
    `30/09/2026`, `2026-09-30`, `Sep 30, 2026`. Trả (date, vị trí kết thúc) hoặc (None, 0)."""
    s = unicodedata.normalize("NFKC", str(chu or ""))
    cac = [
        (r"(\d{1,2})\s*(?:thg|tháng|Thg|Tháng)\s*(\d{1,2})\s*,?\s*(?:năm\s*)?(\d{4})", "dmy"),
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", "dmy"),
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "ymd"),
        (r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", "ymd"),
        (r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", "mdy_en"),
    ]
    tot = None
    for mau, kieu in cac:
        m = re.search(mau, s)
        if not m:
            continue
        try:
            if kieu == "dmy":
                d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            elif kieu == "ymd":
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            else:
                th = _THANG_EN.get(m.group(1).lower())
                if not th:
                    continue
                d = date(int(m.group(3)), th, int(m.group(2)))
        except ValueError:
            continue
        if tot is None or m.start() < tot[2]:
            tot = (d, m.end(), m.start())
    return (tot[0], tot[1]) if tot else (None, 0)


def phan_tich_gio(chu):
    """Giờ:phút (24h; nhận SA/CH/AM/PM). Trả (h, m) hoặc None."""
    s = unicodedata.normalize("NFKC", str(chu or ""))
    m = re.search(r"(\d{1,2}):(\d{2})(?::\d{2})?\s*(SA|CH|AM|PM|sáng|chiều|tối)?", s, re.I)
    if not m:
        return None
    h, p = int(m.group(1)), int(m.group(2))
    buoi = (m.group(3) or "").lower()
    if buoi in ("ch", "pm", "chiều", "tối") and h < 12:
        h += 12
    if buoi in ("sa", "am", "sáng") and h == 12:
        h = 0
    if h > 23 or p > 59:
        return None
    return h, p


def phan_tich_ngay_gio(chu):
    """datetime từ chữ có cả ngày và giờ (giờ tìm SAU ngày), hoặc None."""
    d, het = phan_tich_ngay(chu)
    if not d:
        return None
    s = unicodedata.normalize("NFKC", str(chu or ""))
    g = phan_tich_gio(s[het:]) or phan_tich_gio(s)
    if not g:
        return None
    return datetime(d.year, d.month, d.day, g[0], g[1])


def phan_tich_trang_thai(chu, bo_chu: dict = None):
    """(loai, datetime|None) từ chữ trạng thái/hiển thị của Studio.

    loai ∈ loi_tai | nhap | da_len_lich | khong_cong_khai | cong_khai | rieng_tu | khong_ro.
    Thứ tự dò có chủ ý: "Không công khai" chứa "công khai" nên dò trước."""
    s = unicodedata.normalize("NFKC", str(chu or ""))
    thap = s.lower()
    bo = dict(CHU_TRANG_THAI)
    bo.update({k: v for k, v in (bo_chu or {}).items() if k in CHU_TRANG_THAI})
    loai = "khong_ro"
    for k in _THU_TU_LOAI:
        if any(w.lower() in thap for w in bo.get(k) or []):
            loai = k
            break
    return loai, phan_tich_ngay_gio(s)


def dinh_dang_ngay(d, mau: str) -> str:
    """`{d} thg {m}, {Y}` → '30 thg 9, 2026'; `{dd}/{mm}/{Y}` → '30/09/2026'."""
    return (str(mau).replace("{dd}", "%02d" % d.day).replace("{mm}", "%02d" % d.month)
            .replace("{d}", str(d.day)).replace("{m}", str(d.month)).replace("{Y}", str(d.year)))


def han_cho_tai(duong_mp4: str) -> float:
    """Hạn chờ tải lên (giây) theo dung lượng tệp: max(10 phút, MB ÷ 1 MB/s × 2)."""
    try:
        mb = os.path.getsize(duong_mp4) / 1048576.0
    except (OSError, TypeError):
        mb = 0.0
    return max(float(CHO_TAI_TOI_THIEU_GIAY), mb / TOC_DO_TAI_THAP_MB_GIAY * 2.0)


_PHAN_TRAM = re.compile(r"(\d{1,3})\s*%")
_DONG_TIEN_DO = re.compile(
    r"^\s*(đang xử lý|đang kiểm tra|đã kiểm tra xong|đã tải được|đang tải lên|"
    r"đã hoàn tất quá trình tải lên|tải lên hoàn tất|tải lên không thành công|processing|"
    r"checking|checks complete|upload complete|uploading|upload failed|アップロード|処理|チェック)",
    re.I)


def _chu_loai(bo_chu, loai: str) -> list:
    return [str(w).lower() for w in (((bo_chu or {}).get(loai)) or CHU_TRANG_THAI.get(loai) or [])]


def phan_loai_tien_do(chu, bo_chu: dict = None) -> tuple:
    """(loại, %) của chữ tiến độ tải lên — hàm thuần. Loại: "loi" | "xong" (có
    BẰNG CHỨNG tải xong: hoàn tất / đang xử lý / đang kiểm tra / kiểm tra xong /
    100%) | "dang" (còn đang tải) | "" (không đọc được)."""
    chu = str(chu or "")
    thap = chu.lower()
    m = _PHAN_TRAM.findall(chu)
    pct = int(m[0]) if m else None
    if any(w and w in thap for w in _chu_loai(bo_chu, "loi_tai")):
        return "loi", pct
    if any(w and w in thap for w in (_chu_loai(bo_chu, "da_tai_xong") + _chu_loai(bo_chu, "xu_ly_xong")
                                     + _chu_loai(bo_chu, "dang_xu_ly") + _chu_loai(bo_chu, "dang_kiem_tra"))):
        return "xong", pct
    if pct is not None:
        return ("xong" if pct >= 100 else "dang"), pct
    if any(w and w in thap for w in _chu_loai(bo_chu, "dang_tai")):
        return "dang", pct
    return "", None


def loc_dong_tien_do(chu) -> str:
    """Chỉ giữ các DÒNG trạng thái tải lên trong một khối chữ lớn (hộp tải lên,
    hàng danh sách) — tránh dương tính giả kiểu "Video đã tải lên gần đây nhất"."""
    return " | ".join(d.strip() for d in str(chu or "").splitlines() if _DONG_TIEN_DO.match(d))


def danh_gia_hau_kiem(trang_thai: str, dai, dai_tep, chu_hang: str = "", bo_chu: dict = None) -> dict:
    """HẬU KIỂM tải lên — hàm thuần. `trang_thai`/`dai`: `status`/`lengthSeconds`
    của video trong gói `get_creator_videos` Studio; `dai_tep`: thời lượng mp4;
    `chu_hang`: chữ hàng Nội dung (lùi khi không bắt được gói). Trả
    {"ket": "ok" | "hong" | "chua-ro", "ly_do"}."""
    tt = str(trang_thai or "").upper()
    if tt:
        if any(x in tt for x in ("FAIL", "REJECT", "DELETE", "ABANDON")):
            return {"ket": "hong", "ly_do": "Studio báo {0}".format(tt)}
        if "UPLOADING" in tt:
            return {"ket": "hong", "ly_do": "Studio: tải lên CHƯA HOÀN TẤT ({0})".format(tt)}
        if dai and dai_tep:
            if abs(float(dai) - float(dai_tep)) <= 2.0:
                return {"ket": "ok", "ly_do": "thời lượng {0:.0f}s khớp tệp {1:.1f}s ({2})".format(
                    float(dai), float(dai_tep), tt)}
            if "PROCESSED" in tt:
                return {"ket": "hong", "ly_do": "thời lượng Studio {0:.0f}s ≠ tệp {1:.1f}s".format(
                    float(dai), float(dai_tep))}
        if "UPLOADED" in tt or "PROCESSING" in tt:
            return {"ket": "ok", "ly_do": "đang xử lý bình thường ({0})".format(tt)}
        return {"ket": "chua-ro", "ly_do": "trạng thái {0}, không đọc được thời lượng".format(tt)}
    thap = str(chu_hang or "").lower()
    loi = [w for w in (_chu_loai(bo_chu, "tai_do") + _chu_loai(bo_chu, "loi_tai")) if w and w in thap]
    if loi:
        return {"ket": "hong", "ly_do": "hàng Nội dung báo «{0}»".format(loi[0])}
    if any(w and w in thap for w in _chu_loai(bo_chu, "dang_xu_ly") + _chu_loai(bo_chu, "dang_kiem_tra")):
        return {"ket": "ok", "ly_do": "hàng Nội dung: đang xử lý"}
    return {"ket": "chua-ro", "ly_do": "không bắt được trạng thái Studio"}


def thoi_luong_mp4_mvhd(duong: str):
    """Thời lượng (giây) đọc hộp `moov/mvhd` của mp4 bằng Python thuần — VPS
    không có ffprobe (get_mp4_duration của may_dang hỏng WinError 2 ngày 28/09).
    None nếu không đọc được."""
    try:
        with open(duong, "rb") as f:
            f.seek(0, 2)
            tong = f.tell()

            def duyet(bat_dau, ket_thuc, can):
                vt = bat_dau
                while vt + 8 <= ket_thuc:
                    f.seek(vt)
                    dau = f.read(8)
                    if len(dau) < 8:
                        return None
                    co, loai = struct.unpack(">I4s", dau)
                    dau_len = 8
                    if co == 1:
                        co = struct.unpack(">Q", f.read(8))[0]
                        dau_len = 16
                    elif co == 0:
                        co = ket_thuc - vt
                    if co < dau_len:
                        return None
                    if loai == can:
                        return vt + dau_len, vt + co
                    vt += co
                return None

            moov = duyet(0, tong, b"moov")
            if not moov:
                return None
            mvhd = duyet(moov[0], moov[1], b"mvhd")
            if not mvhd:
                return None
            f.seek(mvhd[0])
            ban = f.read(4)
            if not ban:
                return None
            if ban[0] == 1:
                f.read(16)
                thang, dai = struct.unpack(">IQ", f.read(12))
            else:
                f.read(8)
                thang, dai = struct.unpack(">II", f.read(8))
            if not thang:
                return None
            return dai / float(thang)
    except (OSError, struct.error):
        return None


def _fmt_card_ts(sec):
    """Như `may_dang._fmt_card_ts` (chép — không import may_dang vì nó đụng
    pyautogui/DPI lúc nạp): 'MM:SS:00' (MM=phút, SS=giây)."""
    sec = max(0, int(round(sec)))
    return "{0:02d}:{1:02d}:00".format(sec // 60, sec % 60)


def compute_card_timestamps(duration, n=5, tail_gap=10):
    """Như `may_dang.compute_card_timestamps`: n mốc đều trong 50% cuối video."""
    t_start = duration * 0.5
    t_last = duration - tail_gap
    if t_last <= t_start:
        t_last = max(t_start, duration - 1)
    step = (t_last - t_start) / (n - 1) if n > 1 else 0
    return [_fmt_card_ts(t_start + i * step) for i in range(n)]


def _doc_ngay_ke_hoach(s):
    s = str(s or "").strip()
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def _doc_gio_ke_hoach(s):
    g = phan_tich_gio(s)
    return g


def gio_hen_hieu_luc(ngay_s, gio_s, bay_gio: datetime):
    """(datetime hẹn, ghi chú). Giờ đã qua (hoặc còn < 5 phút) → bây giờ + 15
    phút làm tròn LÊN bội 5, ghi rõ. Thiếu ngày/giờ → (None, lý do)."""
    d = _doc_ngay_ke_hoach(ngay_s)
    g = _doc_gio_ke_hoach(gio_s)
    if not d or not g:
        return None, "thiếu Ngày đăng/Giờ đăng"
    dt = datetime(d.year, d.month, d.day, g[0], g[1])
    if dt <= bay_gio + timedelta(minutes=5):
        moi = (bay_gio + timedelta(minutes=15)).replace(second=0, microsecond=0)
        du = moi.minute % 5
        if du:
            moi += timedelta(minutes=5 - du)
        return moi, "giờ hẹn {0} đã qua → dời {1} (+15 phút, làm tròn 5)".format(
            dt.strftime("%d/%m/%Y %H:%M"), moi.strftime("%d/%m/%Y %H:%M"))
    return dt, ""


def tach_the(the) -> list:
    return [t.strip() for t in str(the or "").replace("、", ",").split(",") if t.strip()]


def kiem_du_lieu_dong(d: dict) -> list:
    """Lỗi dữ liệu chặn tải (mục 2.2 bước 0). [] = ổn."""
    loi = []
    td = str(d.get("tieu_de") or "")
    if not td.strip():
        loi.append("tiêu đề rỗng")
    if len(td) > 100:
        loi.append("tiêu đề {0} ký tự > 100".format(len(td)))
    if "<" in td or ">" in td:
        loi.append("tiêu đề chứa < hoặc >")
    if len(str(d.get("mo_ta") or "")) > 5000:
        loi.append("mô tả > 5000 ký tự")
    the = tach_the(d.get("the"))
    if len(", ".join(the)) > 500:
        loi.append("tổng thẻ > 500 ký tự")
    return loi


def dong_tu_hang(r: list) -> dict:
    """Dòng khổ rộng của `nguon_tool.get_rows` → dict gọn."""
    import nguon_tool as nt  # noqa: PLC0415

    def o(i):
        return str(r[i]).strip() if i < len(r) and r[i] is not None else ""
    return {"ma": o(nt.O_MA), "kenh": o(nt.O_KENH), "the": o(nt.O_THE),
            "trang_thai": o(nt.O_TRANG_THAI), "tieu_de": o(nt.O_TIEU_DE),
            "mo_ta": (str(r[nt.O_MO_TA]) if nt.O_MO_TA < len(r) else "").strip(),
            "link": [o(i) for i in nt.O_LINK], "ngay": o(nt.O_NGAY), "gio": o(nt.O_GIO)}


def chon_ma_can_dang(hang: list, kenh: str, bay_gio: datetime,
                     bo_loc_ngay: bool = False, ma: str = None,
                     cua_so: tuple = None) -> list:
    """Dòng cần đăng của `kenh` (mục 3 chặn 3): Trạng thái ∈ {EDIT XONG} ∪ bắt
    đầu "ĐANG ĐĂNG" (đang dở, có nháp). Lọc ngày như may_dang: ngày hôm nay
    và giờ chưa qua; dòng ĐANG ĐĂNG của hôm nay nhận cả khi giờ đã qua (tiếp
    nháp, giờ tự dời +15'). `bo_loc_ngay` (--ma chạy tay) bỏ lọc ngày."""
    ra = []
    for r in (hang or [])[1:]:
        d = dong_tu_hang(r)
        if not d["ma"] or d["kenh"] != kenh:
            continue
        if ma and d["ma"] != ma:
            continue
        tt = d["trang_thai"]
        dang_do = tt.startswith(TIEN_TO_DANG_DANG)
        if not (tt == TRANG_THAI_OK or dang_do):
            continue
        if cua_so and not bo_loc_ngay:
            # TẢI LÊN BỔ SUNG (29/09/2026): nhận lịch TƯƠNG LAI trong cửa sổ
            # (bây giờ + biên, bây giờ + cửa sổ] — gói xong SAU phiên sáng vẫn
            # kịp tải/hẹn lịch, không phải đợi đúng ngày đăng.
            ng = _doc_ngay_ke_hoach(d["ngay"])
            g = _doc_gio_ke_hoach(d["gio"])
            if not ng or not g:
                continue
            dt = datetime(ng.year, ng.month, ng.day, g[0], g[1])
            if not (bay_gio + cua_so[0] < dt <= bay_gio + cua_so[1]):
                continue
            ra.append(d)
            continue
        if not bo_loc_ngay:
            ng = _doc_ngay_ke_hoach(d["ngay"])
            g = _doc_gio_ke_hoach(d["gio"])
            if not ng or not g or ng != bay_gio.date():
                continue
            if not dang_do and datetime(ng.year, ng.month, ng.day, g[0], g[1]) <= bay_gio:
                continue
        ra.append(d)
    return ra


def gioi_han_tai_moi(cac: list, so: dict, kenh: str, hom_nay: str,
                     toi_da: int = TAI_LEN_TOI_DA_NGAY) -> list:
    """Trần TẢI MỚI mỗi kênh mỗi ngày (hàm thuần). Gói đã có videoId trong sổ
    (tiếp nháp / xác nhận) không tính vào trần; gói chưa có id chỉ lấy đủ số
    còn lại = `toi_da` − số gói của kênh đã tải mới hôm nay (`ngay_tai`)."""
    da_tai = sum(1 for k, m in (so or {}).items()
                 if str(k).startswith(kenh + "/") and isinstance(m, dict)
                 and m.get("ngay_tai") == hom_nay)
    con = max(0, int(toi_da) - da_tai)
    co_id = [d for d in cac if ((so or {}).get("{0}/{1}".format(kenh, d["ma"])) or {}).get("video_id")]
    chua = [d for d in cac if d not in co_id]
    return co_id + chua[:con]


def trung_tieu_de(hang: list, kenh: str) -> list:
    """Các cặp mã cùng kênh TRÙNG tiêu đề (cảnh báo — TL1-T7-0006/0007)."""
    thay, ra = {}, []
    for r in (hang or [])[1:]:
        d = dong_tu_hang(r)
        if d["kenh"] != kenh or not d["tieu_de"]:
            continue
        k = chuan_hoa_tieu_de(d["tieu_de"])
        if k in thay:
            ra.append((thay[k], d["ma"]))
        else:
            thay[k] = d["ma"]
    return ra


def quyet_dinh(dong: dict, muc_so: dict, ket_qua_kenh: list, hom_nay: str = None,
               tran: int = TRAN_TAI_MOI_NGAY) -> dict:
    """Bảng quyết định mục 3 (hàm thuần).

    `muc_so`: mục sổ videoId của gói ({} nếu chưa có). `ket_qua_kenh`: các hàng
    video tra được trên kênh (lọc tiêu đề + hàng mang id), mỗi hàng
    {video_id, tieu_de, loai, luc}. Trả {hanh_dong: tai_moi|da_co|
    bao_chu_kenh|dung, video_id, nhap_thua:[id], tay, ly_do}.

    30/09/2026 (chủ kênh chốt): KHÔNG còn `tiep_nhap` — nháp của lượt hỏng để
    kệ, lượt sau tải mới (trần `tran` lần/ngày/gói giữ số nháp có hạn)."""
    muc = muc_so or {}
    hom_nay = hom_nay or date.today().isoformat()
    vid = str(muc.get("video_id") or "")
    tt = chuan_hoa_tieu_de(dong.get("tieu_de"))
    hang = [h for h in (ket_qua_kenh or []) if h]
    cung = [h for h in hang if chuan_hoa_tieu_de(h.get("tieu_de")) == tt]
    lan_hom_nay = int(muc.get("lan_tai_moi") or 0) if muc.get("ngay_tai") == hom_nay else 0

    def ket(hd, **kw):
        kw.setdefault("video_id", "")
        kw.setdefault("nhap_thua", [])
        kw.setdefault("tay", False)
        kw.setdefault("ly_do", "")
        kw["hanh_dong"] = hd
        return kw

    def tai_moi(thua, ly_do):
        if lan_hom_nay >= tran:
            return ket("dung", nhap_thua=thua,
                       ly_do="đã tải mới {0} lần hôm nay (trần {1}) — không tải thêm".format(
                           lan_hom_nay, tran))
        return ket("tai_moi", nhap_thua=thua, ly_do=ly_do)

    if vid:
        h = next((x for x in hang if x.get("video_id") == vid), None)
        thua = [x["video_id"] for x in cung
                if x.get("video_id") and x.get("video_id") != vid and x.get("loai") == "nhap"]
        if muc.get("trang_thai") == "tai-hong":
            # 30/09/2026: HẬU KIỂM lượt trước thấy video tải lên hỏng (gián đoạn /
            # lỗi xử lý / sai thời lượng) → để kệ bản ấy (chủ kênh xem), TẢI MỚI.
            return tai_moi(thua + [vid], "id {0} hậu kiểm tải lên HỎNG — để kệ, tải mới".format(vid))
        if h and h.get("loai") in LOAI_DA_DANG:
            return ket("da_co", video_id=vid, loai=h.get("loai"), luc=h.get("luc"),
                       nhap_thua=thua, ly_do="sổ có id, kênh báo {0}".format(h.get("loai")))
        if h and h.get("loai") == "nhap":
            # 30/09/2026 chủ kênh chốt: lượt hỏng để lại nháp thì ĐỂ KỆ (chủ kênh
            # tự xoá) — không mở lại/sửa tiếp/xoá; id cũ vào `id_cu`, TẢI MỚI.
            return tai_moi(thua + [vid], "id {0} còn là NHÁP (lượt trước hỏng) — để kệ nháp, tải mới".format(vid))
        if h and h.get("loai") == "rieng_tu":
            return ket("bao_chu_kenh", video_id=vid, nhap_thua=thua,
                       ly_do="video {0} của sổ đang RIÊNG TƯ (không phải nháp)".format(vid))
        if muc.get("trang_thai") in TT_SO_DA_HEN and not (h and h.get("loai") == "loi_tai"):
            # Chống trùng thật: sổ ghi đã bấm «Lên lịch» mà kênh không thấy/không
            # đọc được hàng → KHÔNG tải lại, báo chủ kênh.
            return ket("bao_chu_kenh", video_id=vid, nhap_thua=thua,
                       ly_do="sổ ghi {0} đã hẹn lịch ({1}) mà kênh {2} — không tải lại".format(
                           vid, muc.get("trang_thai"),
                           "báo {0}".format(h.get("loai")) if h else "không thấy"))
        return tai_moi(thua + [vid], "id {0} lỗi tải/không còn trên kênh".format(vid))

    da_dang = [h for h in cung if h.get("loai") in LOAI_DA_DANG]
    nhap = [h for h in cung if h.get("loai") == "nhap" and h.get("video_id")]
    rieng = [h for h in cung if h.get("loai") == "rieng_tu"]
    if da_dang:
        h = da_dang[0]
        return ket("da_co", video_id=h.get("video_id") or "", loai=h.get("loai"), luc=h.get("luc"),
                   tay=True, nhap_thua=[x["video_id"] for x in nhap],
                   ly_do="cùng tiêu đề đã {0} trên kênh".format(h.get("loai")))
    if rieng:
        return ket("bao_chu_kenh", video_id=rieng[0].get("video_id") or "",
                   nhap_thua=[x["video_id"] for x in nhap],
                   ly_do="cùng tiêu đề có video RIÊNG TƯ (không nháp) — chờ chủ kênh")
    if nhap:
        # 30/09/2026: nháp cùng tiêu đề để kệ (chủ kênh tự xoá) — chỉ báo, tải mới.
        return tai_moi([x["video_id"] for x in nhap],
                       "cùng tiêu đề chỉ có NHÁP trên kênh — để kệ nháp, tải mới")
    return tai_moi([], "chưa có trên kênh")


def lich_da_dat_khop(muc: dict, lich_s: str) -> bool:
    """Giờ hẹn `lich_s` ('dd/mm/YYYY HH:MM') có đúng là giờ ĐÃ ĐẶT và ĐỌC LẠI
    khớp trong ô lúc tải không (theo sổ). Hàm thuần.

    `lich_dat` do `_hien_thi` ghi từ 30/09. Sổ đời trước chưa có khoá này thì
    nhận `lich` khi trạng thái `da-len-lich` (chỉ `_hien_thi` ghi `lich` sau khi
    ô ngày/giờ đã đọc lại khớp và nút «Lên lịch» đã bấm)."""
    muc = muc or {}
    if not lich_s:
        return False
    if muc.get("lich_dat"):
        return str(muc["lich_dat"]) == lich_s
    return muc.get("trang_thai") == "da-len-lich" and str(muc.get("lich") or "") == lich_s


#: Thời kỳ "Thời gian thực — 48 giờ qua" trong gói thô Studio mà mắt cào lưu
#: (`chi-so/kenh/kenh-*/raw/*get_cards*.json` → `latestActivityCardData`).
_KY_48H = "ANALYTICS_TIME_PERIOD_TYPE_REALTIME_LAST_48_HOURS"


def view_48h_tu_goi(goi: dict) -> dict:
    """{video_id: view 48h} từ MỘT gói `get_cards` (khuôn mắt cào lưu: {"response": …})."""
    for the in (((goi or {}).get("response") or {}).get("cards") or []):
        for du in ((the.get("latestActivityCardData") or {}).get("datas") or []):
            if du.get("timePeriod") != _KY_48H:
                continue
            top = du.get("topEntitiesData") or {}
            try:
                ids = top["dimensionColumns"][0]["strings"]["values"]
                so = top["metricColumns"][0]["counts"]["values"]
            except (KeyError, IndexError, TypeError):
                continue
            return {str(i): int(v or 0) for i, v in zip(ids, so) if i}
    return {}


def _luc_goi(duong: str, goi: dict):
    """Giờ chụp (epoch) của một gói: dấu tên tệp `YYYYmmdd-HHMMSS_…` (giờ máy, mắt
    cào đặt) → `captured_at` → mtime."""
    try:
        return time.mktime(time.strptime(os.path.basename(duong)[:15], "%Y%m%d-%H%M%S"))
    except (ValueError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(str(goi.get("captured_at") or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    try:
        return os.path.getmtime(duong)
    except OSError:
        return None


def doc_view_48h_kem_luc(thu_muc_chi_so: str) -> tuple:
    """({video_id: view 48h}, giờ chụp epoch | None) từ gói `get_cards` MỚI NHẤT có
    khối thời gian thực (Studio chỉ trả top video của kênh có view trong 48h) —
    bản chụp kênh của QUÉT NGÀY. ({}, None) nếu chưa có. Chỉ đọc."""
    import glob  # noqa: PLC0415
    tep = sorted(glob.glob(os.path.join(thu_muc_chi_so, "kenh", "kenh-*", "raw", "*get_cards*.json")),
                 key=os.path.basename, reverse=True)
    for duong in tep[:40]:
        try:
            with open(duong, "r", encoding="utf-8") as f:
                goi = json.load(f)
        except (OSError, ValueError):
            continue
        v = view_48h_tu_goi(goi)
        if v:
            return v, _luc_goi(duong, goi)
    return {}, None


def doc_view_48h(thu_muc_chi_so: str) -> dict:
    """{video_id: view 48 giờ qua} — xem :func:`doc_view_48h_kem_luc`."""
    return doc_view_48h_kem_luc(thu_muc_chi_so)[0]


def danh_sach_thieu_mhkt(so: dict) -> dict:
    """Video ĐÃ lên kênh mà sổ ghi chưa có MHKT (`mhkt` không bắt đầu "ok"). Hàm thuần.
    01/10/2026: kèm kết quả BÙ MHKT gần nhất (`bu`, `ly_do`, `bu_loi_lan`) — video
    `mhkt=khong-the` (không còn tồn tại / <25 giây / Shorts) vẫn liệt kê kèm lý do,
    nhưng không vào hàng bù (:func:`hang_bu_mhkt`)."""
    ra = {}
    for k, m in sorted((so or {}).items()):
        if not isinstance(m, dict) or not m.get("video_id"):
            continue
        if m.get("trang_thai") not in TT_SO_DA_LEN_KENH:
            continue
        if str(m.get("mhkt") or "").startswith("ok"):
            continue
        ra[k] = {"video_id": m.get("video_id"), "mhkt": m.get("mhkt") or "", "lich": m.get("lich") or ""}
        if m.get("mhkt_bu_ket"):
            ra[k].update(bu="{0} {1}".format(m.get("mhkt_bu_ket"), m.get("mhkt_bu_luc") or "").strip(),
                         ly_do=m.get("mhkt_bu_ly_do") or "", bu_loi_lan=int(m.get("mhkt_bu_loi_lan") or 0))
    return ra


def can_bu_mhkt(m, toi_da_loi: int = BU_MHKT_TOI_DA_LOI) -> bool:
    """Mục sổ có vào hàng BÙ MHKT không: đã lên kênh, tải không hỏng, `mhkt` là
    bo / lỗi / rỗng (không bắt đầu "ok", không "khong-the"), chưa hỏng đủ trần."""
    if not isinstance(m, dict) or not m.get("video_id"):
        return False
    if m.get("trang_thai") not in TT_SO_DA_LEN_KENH or m.get("tai_xong") is False:
        return False
    mh = str(m.get("mhkt") or "")
    if mh.startswith("ok") or mh.startswith("khong-the"):
        return False
    try:
        return int(m.get("mhkt_bu_loi_lan") or 0) < int(toi_da_loi)
    except (TypeError, ValueError):
        return True


def hang_bu_mhkt(so: dict, kenh: str, hom_nay: str, toi_da: int = BU_MHKT_TOI_DA_DEM,
                 toi_da_loi: int = BU_MHKT_TOI_DA_LOI) -> list:
    """Hàm THUẦN: [(khoá sổ, videoId)] của `kenh` cần BÙ MHKT đêm `hom_nay`
    ("YYYY-MM-DD") — lịch cũ trước. Mỗi video thử tối đa một lần/đêm; video đã
    THỬ THẬT đêm nay (kết quả ok/loi) trừ vào trần `toi_da`/kênh/đêm."""
    da_thu, ds = 0, []
    for k, m in (so or {}).items():
        if not isinstance(m, dict) or not str(k).startswith(kenh + "/"):
            continue
        if m.get("mhkt_bu_ngay") == hom_nay:
            if m.get("mhkt_bu_ket") in ("ok", "loi"):
                da_thu += 1
            continue
        if not can_bu_mhkt(m, toi_da_loi):
            continue
        ds.append((phan_tich_ngay_gio(m.get("lich") or "") or datetime.max, str(k), str(m["video_id"])))
    ds.sort()
    return [(k, vid) for _l, k, vid in ds][:max(0, int(toi_da) - da_thu)]


def doc_view_tong(thu_muc_chi_so: str) -> dict:
    """{video_id: lượt xem mốc mới nhất} từ `bang-tom-tat.csv` (lùi khi thiếu số 48h)."""
    import csv  # noqa: PLC0415
    ra = {}
    try:
        with open(os.path.join(thu_muc_chi_so, "bang-tom-tat.csv"), "r", encoding="utf-8-sig") as f:
            for d in csv.DictReader(f):
                vid = str(d.get("Mã video") or "").strip()
                try:
                    ra[vid] = int(str(d.get("Lượt xem") or "0").replace(".", "").replace(",", "") or 0)
                except ValueError:
                    ra[vid] = 0
    except OSError:
        pass
    return {k: v for k, v in ra.items() if k}


def chon_video_the(view_48h: dict, view_tong: dict, loai_tru=(), co_san=(), toi_da: int = 4) -> list:
    """Link cho thẻ video (hàm thuần — chỉ đạo chủ dự án 29/09/2026).

    * `co_san`: link người điền ở cột "Link card 1–4" — ƯU TIÊN, giữ thứ tự.
    * Phần còn lại: video CỦA KÊNH xếp theo view 48 giờ qua (giảm dần); thiếu
      số 48h (hoặc chưa đủ video) thì lùi về tổng view mốc gần nhất.
    * `loai_tru`: chính video đang đăng + video đã hẹn lịch chưa công khai.
    Trả tối đa `toi_da` link `https://youtu.be/<id>`; không có gì → [].
    """
    bo = {str(x) for x in loai_tru if x}
    ra, da = [], set()
    for link in co_san or ():
        link = str(link or "").strip()
        vid = rut_video_id(link) or link
        if link and vid not in da and vid not in bo:
            ra.append(link)
            da.add(vid)
    xep = sorted((v for v in (view_48h or {}) if v not in bo),
                 key=lambda v: (-(view_48h[v] or 0), -(view_tong or {}).get(v, 0), v))
    xep += sorted((v for v in (view_tong or {}) if v not in bo and v not in (view_48h or {})),
                  key=lambda v: (-(view_tong[v] or 0), v))
    for vid in xep:
        if len(ra) >= toi_da:
            break
        if vid not in da:
            ra.append("https://youtu.be/" + vid)
            da.add(vid)
    return ra[:toi_da]


def tep_goi(thu_muc: str) -> dict:
    """{mp4, anh, srt} của gói. Ảnh: ưu tiên CHON-*.jpg rồi .jpg/.png/.webp đầu."""
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return {"mp4": "", "anh": "", "srt": ""}
    mp4 = next((t for t in ten if t.lower().endswith(".mp4")), "")
    srt = next((t for t in ten if t.lower().endswith(".srt")), "")
    anh = next((t for t in ten if t.upper().startswith("CHON-") and t.lower().endswith(".jpg")), "") \
        or next((t for t in ten if os.path.splitext(t)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")), "")
    j = (lambda t: os.path.join(thu_muc, t) if t else "")
    return {"mp4": j(mp4), "anh": j(anh), "srt": j(srt)}


# ═══ SỔ videoId ══════════════════════════════════════════════════════════

class SoVideoId:
    """Sổ bền `vm/logs/so-video-id.json`, khoá "<kênh>/<mã>". Ghi nguyên tử."""

    def __init__(self, duong: str = DUONG_SO):
        self.duong = duong

    def doc(self) -> dict:
        try:
            with open(self.duong, "r", encoding="utf-8") as tep:
                du = json.load(tep)
            return du if isinstance(du, dict) else {}
        except (OSError, ValueError):
            return {}

    def lay(self, khoa: str) -> dict:
        return dict(self.doc().get(khoa) or {})

    def cap_nhat(self, khoa: str, **truong) -> dict:
        du = self.doc()
        muc = dict(du.get(khoa) or {})
        muc.update(truong)
        muc["cap_nhat"] = time.strftime("%Y-%m-%d %H:%M:%S")
        du[khoa] = muc
        os.makedirs(os.path.dirname(self.duong) or ".", exist_ok=True)
        tam = "{0}.{1}.tam".format(self.duong, os.getpid())
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
            tep.flush()
            os.fsync(tep.fileno())
        os.replace(tam, self.duong)
        return muc

    def cac_id(self) -> set:
        return {str(m.get("video_id")) for m in self.doc().values()
                if isinstance(m, dict) and m.get("video_id")}


# ═══ MÁY ĐĂNG ════════════════════════════════════════════════════════════

class MayDangDom:
    """Luồng đăng một kênh (mục 2.2). Trang thật (`cdp_studio.TrangStudio`)
    hoặc giả (`StudioGia` trong test) — cùng giao diện."""

    def __init__(self, kenh: str, bo_chon: dict, tao_trang, so: SoVideoId, bao,
                 thu_muc_done: str, nhat_ky=None, bay_gio=None, ngu=None,
                 han_giay: float = HAN_PHIEN_MAC_DINH, cai_dat_kenh: dict = None,
                 duong_uc: str = DUONG_UC, duong_dodang: str = DUONG_DODANG,
                 lam_the: bool = True, lam_mhkt: bool = True, han_mhkt: float = HAN_MHKT_GIAY,
                 thu_muc_chi_so: str = None):
        self.kenh = kenh
        self.bo = bo_chon
        self.tao_trang = tao_trang
        self.so = so
        self.bao = bao
        self.thu_muc_done = thu_muc_done
        self.nk = nhat_ky or log.info
        self.bay_gio = bay_gio or datetime.now
        self.ngu = ngu or time.sleep
        self.het_han = time.monotonic() + max(60.0, float(han_giay) - 5 * 60)
        self.cai = cai_dat_kenh or {}
        self.duong_uc = duong_uc
        self.duong_dodang = duong_dodang
        self.lam_the = lam_the
        self.lam_mhkt = lam_mhkt
        self.han_mhkt = han_mhkt
        #: số liệu Studio mắt cào đã quét (chọn video cho thẻ theo view 48h)
        self.thu_muc_chi_so = (thu_muc_chi_so if thu_muc_chi_so is not None else
                               os.path.join(os.path.dirname(GOC), "CHANNEL", kenh, "chi-so"))
        self.vid_dang = ""
        self.uc = ""
        self._tb = None
        self.tab = []
        self.dang_tai = False        # tab A đang tải video (chưa chắc tải xong)
        self.tai_xong_ok = False     # đã có BẰNG CHỨNG tải xong 100% cho gói đang đăng
        self.han_tai = float(CHO_TAI_TOI_THIEU_GIAY)
        self._d_dang = None
        self.tieu_de_theo_ma = {}    # mã gói → tiêu đề (tìm video nguồn MHKT trong hộp chọn)
        self.mhkt_nguon = ""         # videoId đã nhập MHKT từ đó (ghi sổ `mhkt_nguon`)
        self.tab_giu = []            # tab tải lên cố ý để mở — Chrome KHÔNG được đóng
        self.bao_cao = {"kenh": kenh, "goi": [], "nhap_thua": [], "canh_bao": []}

    # ── tiện ích ─────────────────────────────────────────────────────────
    def _url(self, ten: str, **kw) -> str:
        return str((self.bo.get("url") or {})[ten]).format(uc=self.uc, **kw)

    def _chu(self, loai: str) -> list:
        return list(((self.bo.get("chu_trang_thai") or {}).get(loai)) or CHU_TRANG_THAI.get(loai) or [])

    def _canh_bao(self, s: str) -> None:
        self.nk("CẢNH BÁO " + s)
        self.bao_cao["canh_bao"].append(s)

    def con_han(self, giay: float = 0) -> bool:
        return time.monotonic() + giay < self.het_han

    def khoa_so(self, ma: str) -> str:
        return "{0}/{1}".format(self.kenh, ma)

    def ghi_dodang(self, ma: str, buoc: str, vid: str = "") -> None:
        try:
            os.makedirs(os.path.dirname(self.duong_dodang), exist_ok=True)
            with open(self.duong_dodang, "w", encoding="utf-8") as tep:
                json.dump({"kenh": self.kenh, "ma": ma, "luc_bat_dau": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "pid": os.getpid(), "video_id": vid, "buoc": buoc,
                           "may": "dom"}, tep, ensure_ascii=False)
        except OSError:
            pass

    def xoa_dodang(self) -> None:
        try:
            os.remove(self.duong_dodang)
        except OSError:
            pass

    def tab_b(self):
        if self._tb is None:
            self._tb = self.tao_trang()
            self.tab.append(self._tb)
        return self._tb

    def dong_het(self) -> None:
        for t in self.tab:
            try:
                t.dong()
            except Exception:  # noqa: BLE001
                pass
        self.tab = []
        self._tb = None

    # ── bước 1: UC ───────────────────────────────────────────────────────
    def lay_uc(self) -> str:
        if self.uc:
            return self.uc
        tb = self.tab_b()
        try:
            tb.mo(self._url("studio"), han=60)
        except Exception as loi:  # noqa: BLE001
            raise LoiTruoc("không mở được Studio: {0}".format(loi))
        uc = ""
        for _ in range(30):
            m = re.search(r"/channel/(UC[A-Za-z0-9_-]{20,})", tb.url() or "")
            if m:
                uc = m.group(1)
                break
            self.ngu(1)
        if not uc:
            raise LoiTruoc("không đọc được UC kênh từ Studio (chưa đăng nhập?) — url {0}".format(
                (tb.url() or "")[:100]))
        ghim = {}
        try:
            with open(self.duong_uc, "r", encoding="utf-8") as tep:
                ghim = json.load(tep) or {}
        except (OSError, ValueError):
            ghim = {}
        cu = str(ghim.get(self.kenh) or "")
        if not cu:
            ghim[self.kenh] = uc
            try:
                os.makedirs(os.path.dirname(self.duong_uc), exist_ok=True)
                with open(self.duong_uc, "w", encoding="utf-8") as tep:
                    json.dump(ghim, tep, ensure_ascii=False, indent=1)
                self.nk("ghim UC kênh {0} = {1} (lần đầu)".format(self.kenh, uc))
            except OSError:
                pass
        elif cu != uc:
            raise DungKenh("Chrome kênh {0} đang đăng nhập {1}, ghim là {2} — DỪNG kênh".format(
                self.kenh, uc, cu))
        self.uc = uc
        return uc

    # ── bước 2: tra kênh ─────────────────────────────────────────────────
    def _doc_danh_sach(self, tr, han: float = 30.0):
        het = time.monotonic() + han
        while True:
            if tr.co("hang_video"):
                self.ngu(1.5)
                return tr.doc_hang()
            if tr.co("danh_sach_trong"):
                return []
            if time.monotonic() >= het:
                return None
            self.ngu(1)

    def _hang_kenh(self, h: dict) -> dict:
        vid = ""
        for href in h.get("hrefs") or []:
            vid = rut_video_id(href)
            if vid:
                break
        chu = h.get("che_do") or h.get("chu") or ""
        loai, luc = phan_tich_trang_thai(chu, self.bo.get("chu_trang_thai"))
        if loai == "khong_ro":
            loai, luc2 = phan_tich_trang_thai(h.get("chu") or "", self.bo.get("chu_trang_thai"))
            luc = luc or luc2
        if h.get("nut_nhap") and loai != "loi_tai":
            loai = "nhap"
        return {"video_id": vid, "tieu_de": h.get("tieu_de") or "", "loai": loai, "luc": luc,
                "hang": h}

    def _q(self, tieu_de: str) -> str:
        return urllib.parse.quote(json.dumps(str(tieu_de), ensure_ascii=False)[1:-1], safe="")

    def tra_kenh(self, tieu_de: str, vid: str = "") -> list:
        loi_cls = LoiSau if vid else LoiTruoc
        tb = self.tab_b()
        try:
            tb.mo(self._url("loc_tieu_de", q=self._q(tieu_de)), han=60)
        except Exception as loi:  # noqa: BLE001
            raise loi_cls("không mở được danh sách lọc tiêu đề: {0}".format(loi))
        rows = self._doc_danh_sach(tb)
        if rows is None:
            raise loi_cls("không đọc được danh sách video (không thấy hàng lẫn trang trống)")
        ra = [self._hang_kenh(h) for h in rows]
        self.nhap_khong_id = [x for x in ra if x["loai"] == "nhap" and not x["video_id"]]
        if vid and not any(x["video_id"] == vid for x in ra):
            try:
                tb.mo(self._url("danh_sach"), han=60)
                rows2 = self._doc_danh_sach(tb) or []
            except Exception:  # noqa: BLE001
                rows2 = []
            ds2 = [self._hang_kenh(h) for h in rows2]
            ra += [x for x in ds2 if x["video_id"] == vid]
            self.nhap_khong_id += [x for x in ds2 if x["loai"] == "nhap" and not x["video_id"]]
        return ra

    # ── bước 3a: tải mới ─────────────────────────────────────────────────
    def _tai_moi(self, ta, d: dict, tep: dict, k: str, qd: dict) -> str:
        ma = d["ma"]
        ta.giu_khi_roi(True)
        if not ta.mo(self._url("upload"), cho_khoa="hop_upload", han=60):
            raise LoiTruoc("không mở được hộp tải lên")
        ta.don_hop_la()
        if not ta.tim("nut_chon_tep", han=30):
            raise LoiTruoc("không thấy nút Chọn tệp")
        muc = self.so.lay(k)
        hom_nay = self.bay_gio().date().isoformat()
        lan = (int(muc.get("lan_tai_moi") or 0) if muc.get("ngay_tai") == hom_nay else 0) + 1
        id_cu = list(muc.get("id_cu") or [])
        if muc.get("video_id"):
            id_cu.append(muc["video_id"])
        self.so.cap_nhat(k, video_id="", trang_thai="dang-tai", lan_tai_moi=lan,
                         ngay_tai=hom_nay, id_cu=id_cu)
        try:
            cach = ta.dat_tep("nut_chon_tep", tep["mp4"], khoa_input="o_tep_video")
        except Exception as loi:  # noqa: BLE001 — chưa chọn được tệp = chưa chạm kênh
            raise LoiTruoc("không chọn được tệp video: {0}".format(loi))
        self.dang_tai = True
        self.nk("{0}: đã chọn tệp ({1}) — YouTube bắt đầu tải".format(ma, cach))
        self.ghi_dodang(ma, "chon-tep")
        link = ta.tim("link_video", han=120)
        vid = ""
        if link:
            vid = rut_video_id(ta.doc_thuoc_tinh(link, "href")) or rut_video_id(ta.doc_chu(link))
        if not vid:
            chu = ta.doc_chu("hop_upload") or ""
            if any(w.lower() in chu.lower() for w in self._chu("gioi_han")):
                raise LoiSau("kênh báo đã đạt giới hạn tải lên")
            ta.ghi_bang_chung("khong-lay-duoc-id-" + ma)
            raise LoiSau("đã chọn tệp nhưng không lấy được videoId — có thể còn một bản nháp "
                         "'8 video' trên kênh (chỉ báo, không xoá)")
        self.so.cap_nhat(k, video_id=vid, trang_thai="nhap")
        self.nk("{0}: videoId {1} (đã ghi sổ)".format(ma, vid))
        self.ghi_dodang(ma, "nhap", vid)
        self.bao(ma, "{0} · nháp {1}".format(TIEN_TO_DANG_DANG, vid), video_id=vid)
        return vid

    # ── bước 3b: tiếp nháp ───────────────────────────────────────────────
    def _mo_nhap(self, ta, d: dict, vid: str) -> None:
        for url in (self._url("loc_tieu_de", q=self._q(d["tieu_de"])), self._url("danh_sach")):
            try:
                ta.mo(url, han=60)
            except Exception:  # noqa: BLE001
                continue
            for h in self._doc_danh_sach(ta) or []:
                if any(rut_video_id(x) == vid for x in h.get("hrefs") or []):
                    if not h.get("nut_nhap"):
                        raise LoiSau("hàng {0} không có nút Chỉnh sửa bản nháp".format(vid))
                    ta.bam(h["nut_nhap"], hau_dieu_kien=lambda: ta.co("hop_upload"), han_hau=30)
                    self.nk("{0}: đã mở lại bản nháp {1}".format(d["ma"], vid))
                    return
        raise LoiSau("không tìm thấy bản nháp {0} để mở lại".format(vid))

    # ── bước 4: chi tiết ─────────────────────────────────────────────────
    def _dam_bao_chon(self, ta, khoa: str) -> None:
        pt = ta.tim(khoa, han=15)
        if not pt:
            raise LoiSau("không thấy {0}".format(khoa))
        if str(ta.doc_thuoc_tinh(pt, "aria-checked")) == "true":
            return
        ta.bam(pt, hau_dieu_kien=lambda: str(ta.doc_thuoc_tinh(khoa, "aria-checked")) == "true",
               han_hau=8)

    def _danh_sach_phat(self, ta) -> str:
        ten = str(self.cai.get("danh_sach_phat") or "").strip()
        ta.bam("playlist_mo", hau_dieu_kien=lambda: ta.co("playlist_muc"), han_hau=15)
        chon = ta.tim("playlist_muc", han=5)
        if chon and ten:
            so = int(chon.get("so") or 1)
            chon = None
            for i in range(so):
                pt = ta.tim("playlist_muc", han=0, thu=i)
                if pt and ten in chuan_hoa_tieu_de(ta.doc_chu(pt)):
                    chon = pt
                    break
            if not chon:
                self._canh_bao("không thấy danh sách phát tên «{0}» — lấy cái đầu".format(ten))
                chon = ta.tim("playlist_muc", han=0)
        if not chon:
            raise Exception("không có danh sách phát nào")
        if str(ta.doc_thuoc_tinh(chon, "aria-checked")) != "true":
            ta.bam(chon)
        ta.bam("playlist_xong", hau_dieu_kien=lambda: not ta.co("playlist_muc"), han_hau=10)
        return "ok"

    def _the_seo(self, ta, the: str) -> str:
        ds = tach_the(the)
        if not ds:
            return "bo"
        co_san = ta.tim("the_da_co", han=0)
        if co_san and int(co_san.get("so") or 0) >= len(ds):
            return "ok"
        ta.go_tho("o_the", ", ".join(ds) + ",")
        ta.phim("Enter")
        pt = ta.tim("the_da_co", han=5)
        if not pt:
            raise Exception("gõ thẻ xong không thấy chip nào")
        return "ok"

    def _chi_tiet(self, ta, d: dict, tep: dict) -> None:
        ta.go("tieu_de", d["tieu_de"])
        ta.go("mo_ta", d["mo_ta"])
        if tep.get("anh"):
            try:
                if ta.du_phong.get("nut_thumbnail") or not ta.tim("nut_thumbnail", han=0):
                    ta.ghi_bang_chung("chi-tiet-" + d["ma"])   # để chốt chon#1 nút thumbnail
                ta.dat_tep("nut_thumbnail", tep["anh"])
            except Exception as loi:  # noqa: BLE001 — thumbnail hỏng: cảnh báo, đi tiếp
                self._canh_bao("{0}: thumbnail hỏng ({1})".format(d["ma"], loi))
        else:
            self._canh_bao("{0}: gói không có ảnh thumbnail".format(d["ma"]))
        try:
            self._danh_sach_phat(ta)
        except Exception as loi:  # noqa: BLE001 — mềm
            self._canh_bao("{0}: danh sách phát bỏ qua ({1})".format(d["ma"], loi))
            if ta.co("playlist_xong"):
                try:
                    ta.bam("playlist_xong")
                except Exception:  # noqa: BLE001
                    pass
        self._dam_bao_chon(ta, "khong_tre_em")
        if not ta.co("ai_co") and not ta.co("o_the"):
            ta.bam("hien_them", hau_dieu_kien=lambda: ta.co("ai_co") or ta.co("o_the"), han_hau=10)
        self._dam_bao_chon(ta, "ai_co")
        try:
            self._the_seo(ta, d.get("the"))
        except Exception as loi:  # noqa: BLE001 — mềm
            self._canh_bao("{0}: thẻ SEO bỏ qua ({1})".format(d["ma"], loi))
        self._con_hop(ta, "chi tiết")

    def _con_hop(self, ta, buoc: str) -> None:
        if not ta.co("hop_upload"):
            raise LoiSau("hộp tải lên đã đóng giữa chừng (sau {0})".format(buoc))

    # ── bước 5: thành phần ───────────────────────────────────────────────
    def _tiep(self, ta, hau, ten: str) -> None:
        try:
            ta.bam("nut_tiep", hau_dieu_kien=hau, han_hau=30)
        except Exception as loi:  # noqa: BLE001
            raise LoiSau("không sang được bước {0}: {1}".format(ten, loi))

    def _phu_de(self, ta, d: dict, srt: str) -> str:
        if not srt:
            self._canh_bao("{0}: gói không có .srt — KHÔNG có phụ đề".format(d["ma"]))
            return "bo"
        if "chỉnh sửa" in chuan_hoa_tieu_de(ta.doc_chu("phu_de_them") or "").lower():
            self.nk("{0}: phụ đề đã có (nút là «Chỉnh sửa») — bỏ qua".format(d["ma"]))
            return "ok"
        try:
            ta.bam("phu_de_them", hau_dieu_kien=lambda: ta.co("phu_de_tai_tep") or ta.co("phu_de_ngon_ngu"),
                   han_hau=15)
            if ta.co("phu_de_ngon_ngu") and not ta.co("phu_de_tai_tep"):
                ngon = str(self.cai.get("ngon_ngu") or "")
                ten = (self.bo.get("ngon_ngu_video") or {}).get(ngon)
                if not ten:
                    raise Exception("Studio hỏi ngôn ngữ video mà kênh chưa khai ngon_ngu")
                ta.bam("phu_de_ngon_ngu")
                muc = ta.tim_chu([ten], han=5)
                if not muc:
                    raise Exception("không thấy mục ngôn ngữ «{0}»".format(ten))
                ta.bam(muc)
            pt_tai = ta.tim("phu_de_tai_tep", han=10)
            if pt_tai and pt_tai.get("cach") != "chon#1":
                ta.ghi_bang_chung("phu-de-mo-" + d["ma"])      # để chốt chon#1 "Tải tệp lên"
            ta.bam("phu_de_tai_tep", hau_dieu_kien=lambda: ta.co("phu_de_co_moc") or ta.co("phu_de_tiep_tuc"),
                   han_hau=15)
            if ta.co("phu_de_co_moc"):
                self._dam_bao_chon(ta, "phu_de_co_moc")
            ta.dat_tep("phu_de_tiep_tuc", srt)
            # Nút Xong tắt trong lúc trình soạn nạp SRT → chờ nó BẬT rồi mới bấm,
            # và chờ trình soạn ĐÓNG HẲN (đo 29/09: bấm MHKT khi nó còn mở = bị che).
            if not ta.tim("phu_de_xong", han=60):
                raise Exception("nút Xong của trình soạn phụ đề không bật")
            ta.bam("phu_de_xong")
            if not ta.cho_mat_ca_tat("phu_de_trinh_soan", han=90):
                raise Exception("trình soạn phụ đề không đóng sau Xong")
            self.ngu(2)
            return "ok"
        except Exception as loi:  # noqa: BLE001 — mềm, nhưng cảnh báo TO
            self._canh_bao("{0}: PHỤ ĐỀ HỎNG ({1}) — video lên lịch không có phụ đề".format(d["ma"], loi))
            try:
                ta.ghi_bang_chung("phu-de-" + d["ma"])
                if ta.co("phu_de_xong") or ta.co("phu_de_tai_tep") or ta.co("phu_de_tiep_tuc"):
                    ta.phim("Escape")
            except Exception:  # noqa: BLE001
                pass
            return "bo"

    def _nguon_mhkt(self) -> list:
        """Video NGUỒN để nhập MHKT: video của kênh đã lên kênh mà sổ ghi `mhkt`
        bắt đầu "ok" (ok / ok:nhap / ok:mau…), tải lên không hỏng, mới cập nhật
        trước. [(video_id, tiêu đề)] — 30/09/2026: bản cũ luôn chọn thẻ ĐẦU của hộp
        chọn (video mới nhất) và hỏng dây chuyền khi video ấy không có MHKT
        (TL2-T7-0007/0008, TL1-T7-0013: "Video này không có màn hình kết thúc để nhập")."""
        ds = []
        for k, m in (self.so.doc() or {}).items():
            if not isinstance(m, dict) or not str(k).startswith(self.kenh + "/"):
                continue
            vid = str(m.get("video_id") or "")
            if not vid or vid == self.vid_dang or m.get("trang_thai") not in TT_SO_DA_LEN_KENH:
                continue
            if not str(m.get("mhkt") or "").startswith("ok") or m.get("tai_xong") is False:
                continue
            ma = str(k).split("/", 1)[1]
            ds.append((str(m.get("cap_nhat") or ""), vid, self.tieu_de_theo_ma.get(ma, "")))
        ds.sort(reverse=True)
        return [(vid, td) for _cn, vid, td in ds]

    def _mhkt(self, ta, d: dict) -> str:
        """Màn hình kết thúc ở bước Thành phần (PHỤ — hỏng thì vẫn lên lịch):
        1. NHẬP từ một video ĐÃ CÓ MHKT (sổ `mhkt` = ok…) — chọn đúng thẻ của video
           ấy trong hộp "Chọn một video cụ thể" (tìm theo videoId, lùi tìm theo tiêu
           đề), video nguồn báo "không có MHKT" thì thử nguồn kế;
        2. không có nguồn hợp lệ → TỰ DỰNG từ mẫu "1 video, 1 đăng ký" (1 phần tử
           Video + nút Đăng ký, mẫu của Studio đặt ở 20 giây cuối)."""
        if not self.lam_mhkt:
            return "bo"
        if "chỉnh sửa" in chuan_hoa_tieu_de(ta.doc_chu("mhkt_them") or "").lower():
            self.nk("{0}: màn hình kết thúc đã có — bỏ qua".format(d["ma"]))
            return "ok"
        het = time.monotonic() + self.han_mhkt
        while True:
            pt = ta.tim("mhkt_nhap", han=0) or ta.tim("mhkt_them", han=0)
            if pt or time.monotonic() >= het or not self.con_han(120):
                break
            self.ngu(5)
        if not pt:
            self._canh_bao("{0}: Màn hình kết thúc bỏ qua (nút Nhập từ video/Thêm chưa sẵn sàng)".format(d["ma"]))
            return "bo"
        nguon = self._nguon_mhkt()
        self.nk("{0}: MHKT — {1}".format(d["ma"], "nguồn đã có MHKT: " + ", ".join(v for v, _t in nguon[:4])
                                        if nguon else "không có video nguồn nào đã có MHKT → dựng từ mẫu"))
        try:
            kq = self._mhkt_nhap_nguon(ta, d, nguon, mo_bang="mhkt_nhap") if nguon and ta.co("mhkt_nhap") else ""
            if not kq:
                kq = self._mhkt_dung_mau(ta, d, mo_bang="mhkt_them")
            return kq
        except Exception as loi:  # noqa: BLE001 — PHỤ
            self.nk("{0}: màn hình kết thúc lỗi: {1}".format(d["ma"], loi))
            self._dong_trinh_soan(ta, "mhkt-" + d["ma"])
            self._canh_bao("{0}: Màn hình kết thúc bỏ qua ({1})".format(d["ma"], str(loi)[:120]))
            return "bo"

    def _mhkt_mo(self, ta, khoa: str) -> None:
        """Bấm nút mở MHKT (`mhkt_nhap`/`mhkt_them`/`mhkt_mo_sua`); Studio báo lỗi
        ("Thử lại") thì bấm lại một lần."""
        ta.bam(khoa, hau_dieu_kien=lambda: ta.co("hop_mhkt") or ta.co("mhkt_chon_video")
               or ta.co("nut_thu_lai"), han_hau=30)
        if ta.co("nut_thu_lai"):
            ta.bam("nut_thu_lai", hau_dieu_kien=lambda: ta.co("hop_mhkt") or ta.co("mhkt_chon_video"),
                   han_hau=30)
        self.ngu(2)

    def _mhkt_luu(self, ta, d: dict, cach: str) -> bool:
        luu = ta.tim("mhkt_luu", han=10, cho_tat=True)
        if not luu or luu.get("tat"):
            self.nk("{0}: MHKT ({1}) — nút Lưu chưa bật".format(d["ma"], cach))
            return False
        ta.bam(luu, hau_dieu_kien=lambda: not ta.co("hop_mhkt"), han_hau=30)
        return True

    def _cho_nhap_mhkt(self, ta) -> str:
        """Sau khi bấm thẻ video nguồn: "ok" (hộp chọn đóng, trình soạn có phần
        tử) | "khong_nguon" (Studio báo video ấy không có MHKT) | "" (hết hạn)."""
        for i in range(40):
            if not ta.co("mhkt_chon_video") and (ta.co("mhkt_phan_tu") or ta.tim("mhkt_luu", han=0)):
                return "ok"
            if i >= 2:
                chu = (ta.doc_chu("mhkt_hop_chon", han=1) or "").lower()
                if any(w and w in chu for w in _chu_loai(self.bo.get("chu_trang_thai"), "mhkt_khong_nguon")):
                    return "khong_nguon"
            self.ngu(1)
        return "ok" if ta.co("mhkt_phan_tu") else ""

    def _mhkt_nhap_nguon(self, ta, d: dict, nguon: list, mo_bang: str = "mhkt_nhap") -> str:
        """Nhập MHKT từ video nguồn. Trả "ok:nhap" hoặc "" (không nhập được — hộp
        chọn đã đóng, có thể còn trình soạn mở cho bước dựng mẫu)."""
        if not ta.co("hop_mhkt") and not ta.co("mhkt_chon_video"):
            self._mhkt_mo(ta, mo_bang)
        if not ta.co("mhkt_chon_video") and ta.co("mhkt_nhap_trong"):
            ta.bam("mhkt_nhap_trong", hau_dieu_kien=lambda: ta.co("mhkt_chon_video"), han_hau=15)
        if not ta.tim("mhkt_chon_video", han=10):
            self.nk("{0}: hộp chọn video nguồn MHKT không mở".format(d["ma"]))
            return ""
        for vid, td in nguon[:4]:
            the = ta.tim_chua("mhkt_chon_video", vid, han=4)
            if not the and td and ta.co("mhkt_tim_video"):
                ta.go_tho("mhkt_tim_video", td[:60])
                self.ngu(3)
                the = ta.tim_chua("mhkt_chon_video", vid, han=6)
            if not the:
                self.nk("{0}: không thấy video nguồn {1} trong hộp chọn".format(d["ma"], vid))
                continue
            ta.bam(the)
            kq = self._cho_nhap_mhkt(ta)
            if kq == "ok":
                if self._mhkt_luu(ta, d, "nhập " + vid):
                    self.mhkt_nguon = vid
                    self.nk("{0}: màn hình kết thúc = nhập từ {1} (video đã có MHKT)".format(d["ma"], vid))
                    return "ok:nhap"
                return ""
            self.nk("{0}: video nguồn {1} {2}".format(
                d["ma"], vid, "KHÔNG có MHKT (Studio báo) — thử nguồn kế" if kq == "khong_nguon"
                else "nhập không xong trong hạn"))
        for _ in range(2):
            if ta.co("mhkt_dong_chon"):
                ta.bam("mhkt_dong_chon")
                self.ngu(1.5)
        return ""

    def _mhkt_dung_mau(self, ta, d: dict, mo_bang: str = "mhkt_them") -> str:
        """TỰ DỰNG MHKT từ mẫu "1 video, 1 đăng ký" (phần tử Video — Studio để loại
        "Video tải lên gần đây nhất"/"Phù hợp nhất với người xem" — + nút Đăng ký, ở
        20 giây cuối như mọi mẫu của Studio). Ném lỗi nếu không dựng được."""
        if ta.co("mhkt_chon_video") and ta.co("mhkt_dong_chon"):
            ta.bam("mhkt_dong_chon")
            self.ngu(1.5)
        if not ta.co("hop_mhkt"):
            khoa = mo_bang if ta.co(mo_bang) else ("mhkt_them" if ta.co("mhkt_them") else "mhkt_nhap")
            self._mhkt_mo(ta, khoa)
            if ta.co("mhkt_chon_video") and ta.co("mhkt_dong_chon"):
                ta.bam("mhkt_dong_chon")      # nút mở thẳng hộp chọn (TL3) — đóng, dùng trình soạn
                self.ngu(1.5)
        if not ta.co("hop_mhkt"):
            raise Exception("không mở được trình soạn màn hình kết thúc")
        if not ta.co("mhkt_phan_tu"):
            mau = ta.tim("mhkt_mau_video_dk", han=3)
            if not mau:
                pt = ta.tim("mhkt_mau", han=10)
                so = int((pt or {}).get("so") or 0)
                for i in range(so):
                    ung = ta.tim("mhkt_mau", han=0, thu=i)
                    chu = chuan_hoa_tieu_de(ta.doc_chu(ung) if ung else "").lower()
                    if re.search(r"\b1 video\b", chu) and re.search(r"đăng ký|subscribe|登録", chu) \
                            and not re.search(r"danh sách|playlist|再生リスト", chu):
                        mau = ung
                        break
                if not mau and so > 1:
                    mau = ta.tim("mhkt_mau", han=0, thu=1)   # đo 30/09: thẻ thứ 2 = "1 video, 1 đăng ký"
            if not mau:
                raise Exception("không thấy mẫu «1 video, 1 đăng ký»")
            ta.bam(mau)
            self.ngu(3)
            if not ta.tim("mhkt_phan_tu", han=10):
                raise Exception("mẫu «1 video, 1 đăng ký» không tạo được thành phần")
        doc = [x.get("chu") for x in ta.doc_tat_ca("mhkt_phan_tu")][:4]
        if not self._mhkt_luu(ta, d, "mẫu"):
            raise Exception("dựng mẫu xong mà nút Lưu chưa bật")
        self.nk("{0}: màn hình kết thúc = TỰ DỰNG mẫu «1 video, 1 đăng ký» (20 giây cuối){1}".format(
            d["ma"], " — " + " | ".join(str(x) for x in doc if x) if doc else ""))
        return "ok:mau"

    def _dong_trinh_soan(self, ta, nhan: str) -> None:
        """Dọn hộp chọn + trình soạn còn mở (hỏng giữa chừng): nút X của hộp
        chọn, rồi "Hủy thay đổi" của trình soạn — KHÔNG lưu gì."""
        try:
            ta.ghi_bang_chung(nhan)
            for _ in range(2):
                if ta.co("the_dong_chon"):
                    ta.bam("the_dong_chon")
                    self.ngu(1)
            if ta.co("hop_con_huy"):
                ta.bam("hop_con_huy")
                self.ngu(1.5)
        except Exception:  # noqa: BLE001
            pass

    def _mhkt_trong_trinh_soan(self, ta, d: dict) -> str:
        """[CŨ — 30/09/2026 không còn dùng trong luồng đăng, xem `_mhkt`] Nhập màn
        hình kết thúc từ VIDEO GẦN NHẤT (quyết định 3). Đo 29/09:
        nút "Nhập từ video" ở bước Thành phần có khi mở thẳng hộp "Chọn một
        video cụ thể" (TL3), có khi mở trình soạn (TL1) — trong trình soạn có
        nút "Nhập từ video" riêng. Chọn thẻ ĐẦU (video mới nhất) → trình soạn
        nhận thành phần, nút Lưu bật → Lưu. Không nhập được thì lùi về MẪU
        dựng sẵn (0 = "Lấy màn hình kết thúc của video gần đây nhất",
        5 = "1 video, 1 danh sách phát, 1 đăng ký")."""
        self.ngu(2)
        if not ta.co("mhkt_chon_video") and ta.co("mhkt_nhap_trong"):
            ta.bam("mhkt_nhap_trong", hau_dieu_kien=lambda: ta.co("mhkt_chon_video"), han_hau=15)
        chon = ta.tim("mhkt_chon_video", han=10)
        if chon:
            ta.bam(chon, hau_dieu_kien=lambda: not ta.co("mhkt_chon_video"), han_hau=15)
            self.ngu(3)
            luu = ta.tim("mhkt_luu", han=10, cho_tat=True)
            if luu and not luu.get("tat"):
                ta.bam(luu, hau_dieu_kien=lambda: not ta.co("hop_mhkt"), han_hau=30)
                self.nk("{0}: màn hình kết thúc = nhập từ video mới nhất ({1})".format(
                    d["ma"], chuan_hoa_tieu_de(chon.get("mo_ta"))[:60]))
                return "ok:nhap"
            self.nk("{0}: nhập từ video xong mà nút Lưu chưa bật — thử mẫu".format(d["ma"]))
        for thu, ten in ((0, "video gần đây nhất"), (5, "1 video + 1 danh sách phát + đăng ký")):
            mau = ta.tim("mhkt_mau", han=10, thu=thu)
            if not mau or int(mau.get("so") or 0) <= thu:
                continue
            ta.bam(mau)
            self.ngu(3)
            luu = ta.tim("mhkt_luu", han=5, cho_tat=True)
            if luu and not luu.get("tat"):
                ta.bam(luu, hau_dieu_kien=lambda: not ta.co("hop_mhkt"), han_hau=30)
                self.nk("{0}: màn hình kết thúc = mẫu «{1}»".format(d["ma"], ten))
                return "ok:" + ("gan-nhat" if thu == 0 else "mau-5")
            self.nk("{0}: mẫu «{1}» không tạo được thành phần".format(d["ma"], ten))
        raise Exception("không nhập được màn hình kết thúc")

    def them_mhkt_trang_sua(self, d: dict, vid: str) -> str:
        """Bổ sung màn hình kết thúc qua TRANG SỬA (video đã lên lịch). Chỉ
        bấm Lưu của TRÌNH SOẠN; nút Lưu của trang nằm trong cam_bam."""
        tb = self.tab_b()
        tb.mo(self._url("sua", id=vid), han=60)
        tb.tim("tieu_de", han=40)
        self.vid_dang = vid
        try:
            # 30/09/2026: cùng luật với luồng đăng — nhập từ video ĐÃ CÓ MHKT, không có
            # thì tự dựng mẫu (xem `_mhkt`).
            nguon = self._nguon_mhkt()
            kq = ""
            if nguon:
                self._mhkt_mo(tb, "mhkt_mo_sua")
                kq = self._mhkt_nhap_nguon(tb, d, nguon, mo_bang="mhkt_mo_sua")
            if not kq:
                kq = self._mhkt_dung_mau(tb, d, mo_bang="mhkt_mo_sua")
        except Exception as loi:  # noqa: BLE001
            self._dong_trinh_soan(tb, "mhkt-sua-" + d["ma"])
            self._canh_bao("{0}: màn hình kết thúc (trang sửa) hỏng: {1}".format(d["ma"], loi))
            return "bo"
        # Đọc lại: nút mở trình soạn còn đó, trình soạn đã đóng
        self.ngu(2)
        tb.ghi_bang_chung("mhkt-doc-lai-" + d["ma"])
        return kq if not tb.co("hop_mhkt") else "bo"

    # ── BÙ MHKT video cũ (01/10/2026) ────────────────────────────────────
    def _mo_trang_sua_bu(self, tb, vid: str) -> tuple:
        """Mở trang sửa `vid` (bắt gói `get_creator_videos` nếu trang có). Trả
        (có trang sửa, có bắt được gói nào, gói của đúng video này hoặc None)."""
        url = self._url("sua", id=vid)
        goi, bat_duoc, da_mo = None, False, False
        bat = getattr(tb, "bat_json", None)
        if callable(bat):
            try:
                ds = bat(url, "get_creator_videos", han=30) or []
                da_mo = True
                for g in ds:
                    bat_duoc = True
                    for v in ((g or {}).get("videos") or []):
                        if str(v.get("videoId") or "") == vid:
                            goi = v
                            break
                    if goi:
                        break
            except Exception as loi:  # noqa: BLE001 — lùi về mở trang thường
                self.nk("bù MHKT {0}: bắt gói Studio lỗi: {1}".format(vid, str(loi)[:120]))
        if not da_mo:
            tb.mo(url, han=60)
        return bool(tb.tim("tieu_de", han=40)), bat_duoc, goi

    def _doc_phan_tu_mhkt(self, tb) -> list:
        try:
            ds = [chuan_hoa_tieu_de((x or {}).get("chu") or "") for x in (tb.doc_tat_ca("mhkt_phan_tu") or [])]
        except Exception:  # noqa: BLE001
            ds = []
        ds = [x for x in ds if x]
        return ds or ["(có thành phần)"]

    def _doc_lai_mhkt(self, tb, vid: str, ma: str) -> list:
        """ĐỌC LẠI sau khi lưu: tải lại trang sửa, mở trình soạn MHKT, đếm thành
        phần (hàng `ytve-endscreen-row`), chụp bằng chứng rồi "Hủy thay đổi" (không
        lưu gì). Trả danh sách chữ thành phần; [] nếu không thấy."""
        tb.mo(self._url("sua", id=vid), han=60)
        if not tb.tim("tieu_de", han=40) or not tb.tim("mhkt_mo_sua", han=20):
            raise Exception("đọc lại: trang sửa / mục Màn hình kết thúc không hiện")
        self._mhkt_mo(tb, "mhkt_mo_sua")
        if tb.co("mhkt_chon_video") and tb.co("mhkt_dong_chon"):
            tb.bam("mhkt_dong_chon")
            self.ngu(1.5)
        co = tb.tim("mhkt_phan_tu", han=15)
        doc = self._doc_phan_tu_mhkt(tb) if co else []
        self._dong_trinh_soan(tb, "bu-mhkt-doc-lai-" + ma)
        return doc

    def bu_mhkt_mot(self, khoa: str, vid: str) -> dict:
        """BÙ màn hình kết thúc cho MỘT video đã đăng mà thiếu MHKT, qua TRANG SỬA:
        nhập từ video của kênh ĐÃ CÓ MHKT (sổ `mhkt` = ok…), không có thì dựng mẫu
        «1 video, 1 đăng ký» (20 giây cuối) → Lưu (nút Lưu của TRÌNH SOẠN) → ĐỌC LẠI
        (mở lại trình soạn, đếm thành phần). Ghi sổ: ok → `mhkt=ok:bu`; video không
        còn / <25 giây / Shorts → `mhkt=khong-the` + lý do; hỏng → giữ `mhkt`, tăng
        `mhkt_bu_loi_lan` (đêm sau thử lại, trần `BU_MHKT_TOI_DA_LOI`)."""
        ma = str(khoa).split("/", 1)[-1]
        d = {"ma": ma, "tieu_de": self.tieu_de_theo_ma.get(ma, "")}
        muc = self.so.lay(khoa)
        self.vid_dang = vid
        self.mhkt_nguon = ""

        def ket(k, ly_do="", cach="", doc=None):
            luc = self.bay_gio().strftime("%Y-%m-%d %H:%M:%S")
            truong = {"mhkt_bu_ngay": luc[:10], "mhkt_bu_luc": luc, "mhkt_bu_ket": k,
                      "mhkt_bu_ly_do": ly_do}
            if k == "ok":
                truong.update(mhkt="ok:bu", mhkt_bu_cach=cach, mhkt_bu_doc_lai=" | ".join(doc or [])[:300])
                if self.mhkt_nguon:
                    truong["mhkt_nguon"] = self.mhkt_nguon
            elif k == "khong-the":
                truong["mhkt"] = "khong-the"
            else:
                truong["mhkt_bu_loi_lan"] = int(muc.get("mhkt_bu_loi_lan") or 0) + 1
            self.so.cap_nhat(khoa, **truong)
            if k == "ok":
                self.nk("{0}: BÙ MHKT video {1} XONG ({2}) — đọc lại: {3}".format(
                    ma, vid, cach, " | ".join(doc or [])[:200]))
            elif k == "khong-the":
                self.nk("{0}: BÙ MHKT video {1} BỎ QUA — {2}".format(ma, vid, ly_do))
            else:
                self._canh_bao("{0}: bù MHKT video {1} hỏng (lần {2}/{3}): {4}".format(
                    ma, vid, truong["mhkt_bu_loi_lan"], BU_MHKT_TOI_DA_LOI, ly_do))
            return dict(truong, ket=k)

        tb = self.tab_b()
        kq = ""
        try:
            co_trang, bat_duoc, goi = self._mo_trang_sua_bu(tb, vid)
            tt = str((goi or {}).get("status") or "")
            try:
                dai = float(goi["lengthSeconds"]) if goi and str(goi.get("lengthSeconds") or "").strip() else None
            except (TypeError, ValueError, KeyError):
                dai = None
            if dai is None:
                try:
                    dai = float(muc.get("thoi_luong") or muc.get("thoi_luong_tep") or 0) or None
                except (TypeError, ValueError):
                    dai = None
            if not co_trang:
                if bat_duoc and goi is None:
                    return ket("khong-the", "video không còn trên kênh (Studio không trả video này)")
                return ket("loi", "không mở được trang sửa video")
            if re.search(r"DELETED|REJECTED|FAILED|REMOVED", tt.upper()):
                return ket("khong-the", "video hỏng/bị gỡ trên Studio ({0})".format(tt))
            if dai is not None and dai < MHKT_NGAN_NHAT_GIAY:
                return ket("khong-the", "video dưới {0} giây ({1:.0f}s) — YouTube không cho MHKT".format(
                    MHKT_NGAN_NHAT_GIAY, dai))
            if not tb.tim("mhkt_mo_sua", han=20):
                if dai is not None and dai <= SHORTS_TOI_DA_GIAY:
                    return ket("khong-the", "Shorts/video ngắn ({0:.0f}s) — trang sửa không có mục "
                                            "Màn hình kết thúc".format(dai))
                return ket("loi", "trang sửa không thấy mục Màn hình kết thúc")
            self._mhkt_mo(tb, "mhkt_mo_sua")
            if tb.co("hop_mhkt") and not tb.co("mhkt_chon_video") and tb.tim("mhkt_phan_tu", han=8):
                doc = self._doc_phan_tu_mhkt(tb)
                self._dong_trinh_soan(tb, "bu-mhkt-co-san-" + ma)
                return ket("ok", cach="co-san", doc=doc)
            nguon = self._nguon_mhkt()
            self.nk("{0}: BÙ MHKT video {1} — {2}".format(
                ma, vid, "nguồn đã có MHKT: " + ", ".join(v for v, _t in nguon[:4]) if nguon
                else "kênh chưa có video nào có MHKT → dựng mẫu «1 video, 1 đăng ký»"))
            kq = self._mhkt_nhap_nguon(tb, d, nguon, mo_bang="mhkt_mo_sua") if nguon else ""
            if not kq:
                kq = self._mhkt_dung_mau(tb, d, mo_bang="mhkt_mo_sua")
        except Exception as loi:  # noqa: BLE001 — một video hỏng, video kế vẫn làm
            self._dong_trinh_soan(tb, "bu-mhkt-" + ma)
            return ket("loi", "nhập/dựng MHKT hỏng: {0}".format(str(loi)[:160]))
        self.ngu(3)
        try:
            doc = self._doc_lai_mhkt(tb, vid, ma)
        except Exception as loi:  # noqa: BLE001
            self._dong_trinh_soan(tb, "bu-mhkt-doc-lai-" + ma)
            return ket("loi", "đã lưu ({0}) nhưng đọc lại hỏng: {1}".format(kq, str(loi)[:120]))
        if not doc:
            return ket("loi", "đã lưu ({0}) nhưng đọc lại không thấy thành phần MHKT".format(kq))
        return ket("ok", cach=kq.split(":", 1)[-1] if kq else "?", doc=doc)

    def bu_mhkt(self, cac: list) -> int:
        """Bù MHKT cho danh sách [(khoá sổ, videoId)] — dừng khi gần hết hạn phiên.
        Mã thoát: MA_XONG nếu không video nào hỏng."""
        hong = 0
        for khoa, vid in cac:
            if not self.con_han(240):
                self.nk("bù MHKT: gần hết hạn phiên — dừng, video còn lại để đêm sau")
                break
            if self.bu_mhkt_mot(khoa, vid).get("ket") == "loi":
                hong += 1
        return MA_HONG if hong else MA_XONG

    def link_the(self, d: dict, vid_dang: str = "") -> list:
        """Link cho thẻ video: cột "Link card 1–4" người điền (ưu tiên) + video
        view cao nhất 48 giờ qua của CHÍNH kênh (chỉ đạo chủ dự án 29/09/2026).
        Loại chính video đang đăng và video đã hẹn lịch chưa công khai (sổ)."""
        loai = {vid_dang} if vid_dang else set()
        bay_gio = self.bay_gio()
        for k, m in (self.so.doc() or {}).items():
            if not isinstance(m, dict) or not str(k).startswith(self.kenh + "/"):
                continue
            lich = phan_tich_ngay_gio(m.get("lich") or "")
            if m.get("video_id") and (m.get("trang_thai") in ("nhap", "dang-tai", "loi-tai", "tai-hong")
                                      or (lich and lich > bay_gio)):
                loai.add(str(m["video_id"]))
        # 30/09/2026: số 48h lấy từ bản QUÉT NGÀY gần nhất (mắt cào chỉ quét ban đêm);
        # cũ quá `TUOI_48H_TOI_DA_GIO` hoặc thiếu thì mới đọc nhanh trên tab B.
        v48, luc = doc_view_48h_kem_luc(self.thu_muc_chi_so) if self.thu_muc_chi_so else ({}, None)
        tuoi = (time.time() - luc) / 3600.0 if luc else None
        nguon = "QUÉT NGÀY {0}".format("{0:.0f} giờ trước".format(tuoi) if tuoi is not None else "?")
        if not v48 or tuoi is None or tuoi > TUOI_48H_TOI_DA_GIO:
            nhanh = self._doc_nhanh_48h()
            if nhanh:
                v48, nguon = nhanh, "đọc nhanh Studio (bản QUÉT NGÀY {0})".format(
                    "thiếu" if tuoi is None else "{0:.0f} giờ tuổi".format(tuoi))
        tong = doc_view_tong(self.thu_muc_chi_so) if self.thu_muc_chi_so else {}
        ds = chon_video_the(v48, tong, loai_tru=loai, co_san=d.get("link") or [])
        self.nk("{0}: thẻ video → {1} (48h: {2}; nguồn {3})".format(
            d["ma"], ", ".join(rut_video_id(x) or x for x in ds) or "không có", v48 or "không có số", nguon))
        return ds

    def _doc_nhanh_48h(self) -> dict:
        """Đọc nhanh view 48h: mở Số liệu phân tích của kênh trên tab B, bắt gói
        `get_cards` (cùng gói mắt cào lưu). {} nếu không làm được."""
        if not self.uc:
            return {}
        try:
            tb = self.tab_b()
            bat = getattr(tb, "bat_json", None)
            if not callable(bat):
                return {}
            url = "https://studio.youtube.com/channel/{0}/analytics/tab-overview/period-default".format(self.uc)
            for goi in bat(url, "get_cards", han=30) or []:
                v = view_48h_tu_goi({"response": goi})
                if v:
                    return v
        except Exception as loi:  # noqa: BLE001 — PHỤ: lùi về số đang có
            self.nk("đọc nhanh view 48h lỗi: {0}".format(str(loi)[:120]))
        return {}

    def _dat_dau_phat(self, ta, moc: str) -> None:
        """Đặt ĐẦU PHÁT của trình soạn về `moc` TRƯỚC khi thêm thẻ: thẻ mới
        lấy đúng giờ đầu phát (đo 29/09). Gõ vào ô mốc của từng thẻ thì sai,
        vì trình soạn tự xếp thẻ theo thời gian — thẻ mới (00:00) chen lên đầu,
        ô "thẻ thứ i" không còn là thẻ vừa thêm."""
        ta.go_tho("the_dau_phat", moc)
        ta.phim("Enter")
        self.ngu(1)
        doc = [x.get("value") or x.get("chu") for x in ta.doc_tat_ca("the_dau_phat")]
        if doc and moc not in doc:
            self.nk("đầu phát đọc lại {0} ≠ {1}".format(doc, moc))

    def _them_mot_the(self, ta, loai: str, so_the: int) -> None:
        """Mở ô chọn cho một thẻ mới. Thẻ ĐẦU TIÊN: danh sách loại mặc định
        (0=video, 1=danh sách phát); từ thẻ thứ hai: nút "+ Thẻ" → menu."""
        if so_the == 0 and ta.co("the_loai_dau"):
            pt = ta.tim("the_loai_dau", han=5, thu=0 if loai == "video" else 1)
            ta.bam(pt)
        else:
            ta.bam("the_nut_them", hau_dieu_kien=lambda: ta.co("the_menu_video"), han_hau=8)
            ta.bam("the_menu_video" if loai == "video" else "the_menu_ds")
        self.ngu(1.5)

    def _dien_the(self, ta, d: dict, links: list, moc: list) -> int:
        """Điền thẻ vào trình soạn đang mở. Trả số thẻ đã thêm (bộ chọn đo
        29/09/2026 trên trình soạn Thẻ `ytve-modal-host`)."""
        so_the = 0
        # 1 thẻ danh sách phát (như may_dang cũ) — kênh chưa có danh sách phát thì bỏ
        self._dat_dau_phat(ta, moc[0])
        self._them_mot_the(ta, "ds", so_the)
        ds = ta.tim("the_chon_ds", han=10)
        if ds:
            ta.bam(ds, hau_dieu_kien=lambda: not ta.co("the_chon_ds"), han_hau=10)
            so_the += 1
        else:
            self.nk("{0}: kênh không có danh sách phát cho thẻ".format(d["ma"]))
            if ta.co("the_dong_chon"):
                ta.bam("the_dong_chon")
        for link in links:
            vid = rut_video_id(link)
            if not vid or so_the >= len(moc):
                continue
            self._dat_dau_phat(ta, moc[min(so_the, len(moc) - 1)])
            self._them_mot_the(ta, "video", so_the)
            the = ta.tim_chua("the_chon_video", vid, han=6)
            if not the and ta.co("the_tim_video"):
                ta.go_tho("the_tim_video", link)
                self.ngu(3)
                the = ta.tim_chua("the_chon_video", vid, han=8)
            if not the:
                self.nk("{0}: không thấy video {1} trong hộp chọn — bỏ thẻ này".format(d["ma"], vid))
                if ta.co("the_dong_chon"):
                    ta.bam("the_dong_chon")
                    self.ngu(1)
                continue
            ta.bam(the, hau_dieu_kien=lambda: not ta.co("the_chon_video"), han_hau=10)
            so_the += 1
        return so_the

    def _luu_the(self, ta, d: dict, links: list, moc: list) -> str:
        so_the = self._dien_the(ta, d, links, moc)
        if not so_the:
            raise Exception("không thêm được thẻ nào")
        thay = sorted(x.get("value") or x.get("chu") for x in ta.doc_tat_ca("the_moc"))
        mong = sorted(moc[:so_the])
        if thay != mong:
            raise Exception("mốc thẻ đọc lại {0} ≠ {1} — không lưu".format(thay, mong))
        ta.bam("the_luu", hau_dieu_kien=lambda: not ta.co("hop_the"), han_hau=30)
        self.nk("{0}: đã lưu {1} thẻ, mốc {2}".format(d["ma"], so_the, ", ".join(thay)))
        return "ok:{0}".format(so_the)

    def _huy_the(self, ta, d: dict, loi) -> str:
        self._canh_bao("{0}: thẻ bỏ qua ({1})".format(d["ma"], loi))
        try:
            ta.ghi_bang_chung("the-" + d["ma"])
            for _ in range(2):
                if ta.co("the_dong_chon"):
                    ta.bam("the_dong_chon")
                    self.ngu(1)
            if ta.co("hop_con_huy"):
                ta.bam("hop_con_huy")
                self.ngu(1.5)
        except Exception:  # noqa: BLE001
            pass
        return "bo"

    def _the_video(self, ta, d: dict, tep: dict, vid_dang: str = "") -> str:
        """Thẻ (PHỤ) ở bước Thành phần: 1 thẻ danh sách phát + tối đa 4 thẻ
        video view cao nhất 48h, mốc trong 50% cuối (thời lượng từ mvhd)."""
        if not self.lam_the:
            return "bo"
        dur = thoi_luong_mp4_mvhd(tep.get("mp4") or "")
        if not dur:
            self._canh_bao("{0}: không đọc được thời lượng mp4 — bỏ thẻ".format(d["ma"]))
            return "bo"
        moc = compute_card_timestamps(dur, n=5, tail_gap=10)
        links = self.link_the(d, vid_dang)
        try:
            ta.bam("the_them", hau_dieu_kien=lambda: ta.co("hop_the"), han_hau=30)
            self.ngu(2)
            return self._luu_the(ta, d, links, moc)
        except Exception as loi:  # noqa: BLE001 — PHỤ
            return self._huy_the(ta, d, loi)

    def them_the_trang_sua(self, d: dict, vid: str, tep: dict, lam_lai: bool = False) -> str:
        """Thêm thẻ SAU khi đã lên lịch, qua trang sửa (chỉ đạo 29/09: thẻ là
        PHỤ — lên lịch trước, thêm thẻ sau). Chỉ bấm "Lưu" của trình soạn Thẻ;
        nút Lưu của trang nằm trong cam_bam. Đọc lại bằng cách mở lại trình soạn."""
        dur = thoi_luong_mp4_mvhd(tep.get("mp4") or "")
        if not dur:
            return "bo"
        moc = compute_card_timestamps(dur, n=5, tail_gap=10)
        links = self.link_the(d, vid)
        tb = self.tab_b()
        tb.mo(self._url("sua", id=vid), han=60)
        tb.tim("tieu_de", han=40)
        tb.bam("the_mo_sua", hau_dieu_kien=lambda: tb.co("hop_the"), han_hau=20)
        self.ngu(2)
        if tb.co("the_moc") and lam_lai:
            for _ in range(10):
                if not tb.co("the_xoa"):
                    break
                tb.bam("the_xoa")
                self.ngu(1)
            self.nk("{0}: đã xoá thẻ cũ để làm lại".format(d["ma"]))
        if tb.co("the_moc"):
            self.nk("{0}: video đã có thẻ — không thêm chồng".format(d["ma"]))
            kq = "ok:co-san"
            if tb.co("hop_con_huy"):
                tb.bam("hop_con_huy")
        else:
            try:
                kq = self._luu_the(tb, d, links, moc)
            except Exception as loi:  # noqa: BLE001
                return self._huy_the(tb, d, loi)
        # Đọc lại: mở lại trình soạn, đếm thẻ + tên, rồi Hủy (không đổi gì)
        self.ngu(2)
        tb.bam("the_mo_sua", hau_dieu_kien=lambda: tb.co("hop_the"), han_hau=20)
        self.ngu(2)
        tb.tim("the_moc", han=5)
        moc_doc = [x.get("value") or x.get("chu") for x in tb.doc_tat_ca("the_moc")]
        ten = [x.get("chu") for x in tb.doc_tat_ca("the_muc_ten")]
        so = len(moc_doc)
        self.nk("{0}: đọc lại trình soạn Thẻ — {1} thẻ, mốc {2}; thẻ đang mở: {3}".format(
            d["ma"], so, ", ".join(moc_doc), " | ".join(ten)))
        ten = moc_doc
        tb.ghi_bang_chung("the-doc-lai-" + d["ma"])
        if tb.co("hop_con_huy"):
            tb.bam("hop_con_huy")
            self.ngu(1.5)
        self.bao_cao["the_doc_lai"] = ten
        return kq if so else "bo"

    def _ve_thanh_phan(self, ta, buoc: str) -> None:
        """Sau một bước PHỤ hỏng: nếu còn hộp con che (nút Tiếp không hiện),
        Escape tối đa 2 lần — rồi kiểm hộp tải lên vẫn còn.

        Đo 29/09 (lần đăng thử 1): trình soạn thẻ còn mở CHE nút Tiếp mà nút
        vẫn "hiện" → phải kiểm bị che (elementFromPoint), và trình soạn trong
        `ytve-modal-host` đóng bằng nút "Hủy thay đổi" chứ không chắc bằng Escape."""
        for _ in range(3):
            if ta.co("nut_tiep") and not ta.bi_che("nut_tiep"):
                break
            try:
                # 30/09: trình soạn phụ đề sót lại (Escape không đóng) — panel
                # "Bản xem trước phụ đề" của nó che MHKT/Thẻ/nút Tiếp → bấm Xong.
                if ta.co("phu_de_trinh_soan", cho_tat=True) and ta.co("phu_de_xong"):
                    ta.bam("phu_de_xong")
                    if ta.cho_mat_ca_tat("phu_de_trinh_soan", han=30):
                        self.nk("đóng trình soạn phụ đề sót lại bằng Xong (sau {0})".format(buoc))
                    self.ngu(1.5)
                    continue
                if ta.co("the_dong_chon"):
                    ta.bam("the_dong_chon")
                    self.ngu(1)
                    continue
                if ta.co("hop_con_huy"):
                    ta.bam("hop_con_huy")
                    self.ngu(1.5)
                    continue
            except Exception as loi:  # noqa: BLE001
                self.nk("dọn hộp con sau {0}: {1}".format(buoc, loi))
            ta.phim("Escape")
            self.ngu(1)
        self._con_hop(ta, buoc)

    def _thanh_phan(self, ta, d: dict, tep: dict, k: str) -> None:
        # Hậu điều kiện bằng khoá ĐÃ ĐO trên trang thật (ô tiêu đề biến mất khi
        # rời bước Chi tiết) — không dựa vào nút phụ đề/MHKT/thẻ chưa đo.
        self._tiep(ta, lambda: not ta.co("tieu_de"), "Thành phần video")
        self.ngu(2)
        ta.ghi_bang_chung("thanh-phan-" + d["ma"])
        pd = self._phu_de(ta, d, tep.get("srt"))
        self._ve_thanh_phan(ta, "phụ đề")
        mh = self._mhkt(ta, d)
        self._ve_thanh_phan(ta, "màn hình kết thúc")
        th = self._the_video(ta, d, tep, getattr(self, "vid_dang", ""))
        self._ve_thanh_phan(ta, "thẻ")
        self.so.cap_nhat(k, phu_de=pd, mhkt=mh, the=th, mhkt_nguon=self.mhkt_nguon)

    # ── bước 6–7: kiểm tra, hiển thị ─────────────────────────────────────
    def _kiem_tra(self, ta, k: str) -> None:
        truoc = ta.doc_chu("hop_upload") or ""
        self._tiep(ta, lambda: (ta.doc_chu("hop_upload") or "") != truoc, "Kiểm tra")
        self.ngu(2)
        chu = ta.doc_chu("hop_upload") or ""
        if any(w.lower() in chu.lower() for w in self._chu("loi_tai")):
            self.so.cap_nhat(k, trang_thai="loi-tai")
            ta.ghi_bang_chung("loi-tai")
            raise LoiSau("VIDEO_ERROR — Studio báo lỗi tải/xử lý")
        # Sang Hiển thị: `len_lich_mo` là khoá ĐÃ ĐO; bấm Tiếp tới khi thấy nó
        # (tối đa 3 lần — phòng khi lần bấm trước rơi vào lúc hộp chưa sẵn).
        for lan in range(3):
            if ta.co("len_lich_mo"):
                return
            try:
                ta.bam("nut_tiep", hau_dieu_kien=lambda: ta.co("len_lich_mo"), han_hau=20)
                return
            except Exception as loi:  # noqa: BLE001
                self.nk("sang bước Hiển thị lần {0}: {1}".format(lan + 1, loi))
        ta.ghi_bang_chung("khong-toi-hien-thi")
        raise LoiSau("không sang được bước Hiển thị")

    def _doc_tien_do(self, ta, lan: int) -> tuple:
        """(chữ tiến độ, nguồn). Thử lần lượt: thanh tiến độ của hộp tải lên →
        các DÒNG trạng thái trong chữ cả hộp → (mỗi ~60 giây) hàng video trong danh
        sách Nội dung trên tab B (không đụng tab A đang tải)."""
        chu = chuan_hoa_tieu_de(ta.doc_chu("tien_do", han=2) or "")
        if chu:
            return chu, "thanh tiến độ"
        chu = loc_dong_tien_do(ta.doc_chu("hop_upload", han=2) or "")
        if chu:
            return chu, "hộp tải lên"
        d = self._d_dang
        if lan % 6 == 5 and d and self.vid_dang:
            try:
                for x in self.tra_kenh(d["tieu_de"], self.vid_dang):
                    if x["video_id"] == self.vid_dang:
                        chu = loc_dong_tien_do((x.get("hang") or {}).get("chu") or "")
                        if chu:
                            return chu, "danh sách Nội dung"
            except Exception as loi:  # noqa: BLE001 — nguồn phụ
                self.nk("đọc tiến độ ở danh sách Nội dung lỗi: {0}".format(str(loi)[:100]))
        return "", ""

    def _cho_tai_xong(self, ta, k: str, toi_da: float = None) -> bool:
        """30/09/2026 — CHỜ TẢI XONG 100%. Trả True CHỈ khi có BẰNG CHỨNG tải xong
        (chữ "Đã hoàn tất quá trình tải lên"/"Upload complete", "Đang xử lý", "Đang
        kiểm tra"/"Đã kiểm tra xong", 100% — xem `phan_loai_tien_do`). Không đọc
        được tiến độ thì thử nguồn khác (`_doc_tien_do`) và CHỜ TIẾP tới hạn
        (`han_cho_tai`: max(10 phút, dung lượng ÷ 1 MB/s × 2); % còn tăng thì kéo
        dài; trần `CHO_TAI_TRAN_GIAY` và hạn phiên) — hết hạn trả False; KHÔNG
        BAO GIỜ đi tiếp khi chưa có bằng chứng. Bản cũ trả False sau 30 giây không
        đọc được tiến độ và nơi gọi (`_hien_thi`) vẫn bấm Lên lịch."""
        han = float(toi_da) if toi_da is not None else float(self.han_tai or CHO_TAI_TOI_THIEU_GIAY)
        ma = str(k).split("/", 1)[-1]
        bat_dau = time.monotonic()
        da_cho = 0.0
        lan = 0
        pct_cu = None
        loai_cu = None
        het = han
        while True:
            chu, nguon = self._doc_tien_do(ta, lan)
            loai, pct = phan_loai_tien_do(chu, self.bo.get("chu_trang_thai"))
            if lan % 6 == 0 or loai != loai_cu:
                self.nk("{0}: tiến độ tải lên {1} — «{2}» ({3})".format(
                    ma, "{0}%".format(pct) if pct is not None else "?", chu[:160] or "không đọc được",
                    nguon or "không nguồn nào đọc được"))
            lan += 1
            loai_cu = loai
            if loai == "loi":
                self.so.cap_nhat(k, trang_thai="loi-tai", tai_xong=False)
                raise LoiSau("tải lên lỗi: {0}".format(chu[:80]))
            if loai == "xong":
                self.dang_tai = False
                self.tai_xong_ok = True
                luc = time.strftime("%H:%M:%S")
                self.so.cap_nhat(k, tai_xong_luc=time.strftime("%Y-%m-%d %H:%M:%S"),
                                 bang_chung_tai=chu[:160])
                self.nk("{0}: ĐÃ TẢI XONG lúc {1} — bằng chứng «{2}» ({3})".format(ma, luc, chu[:120], nguon))
                return True
            troi = max(time.monotonic() - bat_dau, da_cho)
            if pct is not None and pct_cu is not None and pct > pct_cu:
                het = max(het, troi + 5 * 60)        # còn đang lên — kéo dài hạn
            if pct is not None:
                pct_cu = pct
            tran = min(float(CHO_TAI_TRAN_GIAY),
                       max(60.0, (self.het_han + 4 * 60 - time.monotonic()) + troi))
            het = min(het, tran)
            if troi >= het:
                self._canh_bao("{0}: {1:.0f} phút chưa có BẰNG CHỨNG tải xong (cuối: «{2}») — KHÔNG lên "
                               "lịch, GIỮ tab tải lên".format(ma, troi / 60.0, chu[:80] or "không đọc được"))
                return False
            self.ngu(10)
            da_cho += 10

    def _hien_thi(self, ta, d: dict, lich: datetime, k: str) -> datetime:
        if not (ta.co("o_ngay_mo") or ta.co("o_gio")):   # đang mở sẵn thì đừng bấm (bấm = gập lại)
            ta.bam("len_lich_mo", hau_dieu_kien=lambda: ta.co("o_ngay_mo") or ta.co("o_gio"), han_hau=10)
        da_ngay = False
        for mau in self.bo.get("dinh_dang_ngay") or ["{d} thg {m}, {Y}", "{dd}/{mm}/{Y}"]:
            try:
                if not ta.co("o_ngay"):
                    ta.bam("o_ngay_mo", hau_dieu_kien=lambda: ta.co("o_ngay"), han_hau=8)
                ta.go_tho("o_ngay", dinh_dang_ngay(lich.date(), mau))
                ta.phim("Enter")
                self.ngu(0.8)
                doc = ta.doc_chu("o_ngay_mo") or ta.doc_thuoc_tinh("o_ngay", "value") or ""
                dd, _ = phan_tich_ngay(doc)
                if dd == lich.date():
                    da_ngay = True
                    break
                self.nk("{0}: ô ngày đọc lại {1!r} ≠ {2} (mẫu {3})".format(
                    d["ma"], doc, lich.date(), mau))
            except Exception as loi:  # noqa: BLE001
                self.nk("{0}: gõ ngày mẫu {1} lỗi: {2}".format(d["ma"], mau, loi))
        if not da_ngay:
            raise LoiSau("không đặt được NGÀY hẹn {0}".format(lich.strftime("%d/%m/%Y")))
        gio = lich.strftime("%H:%M")
        ta.go_tho("o_gio", gio)
        ta.phim("Enter")
        self.ngu(0.8)
        doc_g = phan_tich_gio(ta.doc_thuoc_tinh("o_gio", "value") or ta.doc_chu("o_gio") or "")
        if doc_g != (lich.hour, lich.minute):
            raise LoiSau("ô giờ đọc lại {0} ≠ {1}".format(doc_g, gio))
        chu_nut = chuan_hoa_tieu_de(ta.doc_chu("nut_xong") or "")
        if not any(w.lower() in chu_nut.lower() for w in ("Lên lịch", "Schedule", "予約", "スケジュール")):
            raise LoiSau("nút cuối không mang chữ «Lên lịch» ({0!r}) — không bấm".format(chu_nut))
        # 30/09/2026: KHÔNG BAO GIỜ bấm Lên lịch khi chưa có bằng chứng tải xong 100%.
        if not self.tai_xong_ok and not self._cho_tai_xong(ta, k):
            self.so.cap_nhat(k, trang_thai="nhap", tai_xong=False)
            try:
                ta.ghi_bang_chung("chua-tai-xong-" + d["ma"])
            except Exception:  # noqa: BLE001
                pass
            raise LoiSau("CHƯA có bằng chứng video đã tải lên xong — KHÔNG bấm «Lên lịch»")
        ta.bam("nut_xong", hau_dieu_kien=lambda: ta.co("hop_da_xong") or not ta.co("hop_upload"),
               han_hau=60)
        # `lich_dat`: ngày + giờ ĐÃ ĐỌC LẠI khớp trong ô trước khi bấm «Lên lịch»
        # — xác nhận dùng nó khi Studio chỉ hiện "Đã lên lịch" không kèm giờ.
        self.so.cap_nhat(k, trang_thai="da-len-lich", lich=lich.strftime("%d/%m/%Y %H:%M"),
                         lich_dat=lich.strftime("%d/%m/%Y %H:%M"))
        if ta.tim("hop_da_xong", han=20):
            try:
                ta.bam("dong_hop_da_xong", hau_dieu_kien=lambda: not ta.co("hop_da_xong"), han_hau=10)
            except Exception:  # noqa: BLE001
                ta.phim("Escape")
        ta.giu_khi_roi(False)
        return lich

    # ── bước 9: xác nhận thật ────────────────────────────────────────────
    def xac_nhan(self, d: dict, vid: str, lich: datetime, k: str) -> dict:
        tb = self.tab_b()
        loai, luc, chu = "khong_ro", None, ""
        for lan in range(3):
            try:
                tb.mo(self._url("sua", id=vid), han=45)
                if tb.tim("hien_thi_trang_sua", han=30):
                    chu = tb.doc_chu("hien_thi_trang_sua") or ""
                    loai, luc = phan_tich_trang_thai(chu, self.bo.get("chu_trang_thai"))
            except Exception as loi:  # noqa: BLE001
                self.nk("xác nhận {0} lần {1}: {2}".format(vid, lan + 1, loi))
            # Trang sửa chỉ hiện "Chế độ hiển thị Đã lên lịch" KHÔNG kèm giờ (đo
            # 30/09) — đọc lại 3 lần cũng vậy; đã nhận được trạng thái thì thôi.
            if loai in LOAI_DA_DANG:
                break
            self.ngu(5)
        if not (loai == "da_len_lich" and luc) and loai not in ("cong_khai", "khong_cong_khai"):
            try:
                for x in self.tra_kenh(d["tieu_de"], vid):
                    if x["video_id"] == vid:
                        # hàng danh sách (ô hiển thị + ô ngày) có thể mang giờ
                        if x["loai"] != "khong_ro" or loai == "khong_ro":
                            loai = x["loai"]
                        luc = x["luc"] or luc
                        break
            except Exception:  # noqa: BLE001
                pass
        if not (loai == "da_len_lich" and luc) and loai not in ("cong_khai", "khong_cong_khai"):
            try:
                luc3, chu_hop = self._doc_lich_hop(tb, vid)
                self.nk("xác nhận {0}: hộp Chế độ hiển thị — {1}".format(vid, chuan_hoa_tieu_de(chu_hop)[:160]))
                if luc3:
                    loai, luc = "da_len_lich", luc3
            except Exception as loi:  # noqa: BLE001
                self.nk("xác nhận {0}: đọc hộp Chế độ hiển thị lỗi: {1}".format(vid, loi))
        lich_s = lich.strftime("%d/%m/%Y %H:%M")
        if loai == "da_len_lich" and luc and abs((luc - lich).total_seconds()) <= 60:
            self.so.cap_nhat(k, trang_thai="xac-nhan", lich=lich_s, lan_chua_xac_nhan=0)
            self.bao(d["ma"], "ĐÃ ĐĂNG", video_id=vid, lich=lich_s)
            self.nk("{0}: XÁC NHẬN đã lên lịch {1} (video {2})".format(d["ma"], lich_s, vid))
            return {"ket_qua": "xong", "video_id": vid, "lich": lich_s}
        muc = self.so.lay(k) or {}
        if loai == "da_len_lich" and not luc and lich_da_dat_khop(muc, lich_s):
            # 30/09 (TL1-T7-0011 lặp chua_xac_nhan 2 lượt): Studio xác nhận
            # "Đã lên lịch" mà không hiện giờ ở đâu đọc được; giờ đã ĐỌC LẠI
            # khớp trong ô lúc tải (sổ `lich_dat`) → coi là xác nhận, ghi rõ.
            ghi = "trạng thái Studio «Đã lên lịch»; giờ theo ô đã đọc lại lúc tải (Studio không hiện giờ)"
            self.so.cap_nhat(k, trang_thai="xac-nhan", lich=lich_s, lan_chua_xac_nhan=0,
                             xac_nhan_cach="trang-thai+lich-dat")
            self.bao(d["ma"], "ĐÃ ĐĂNG", video_id=vid, lich=lich_s)
            self.nk("{0}: XÁC NHẬN đã lên lịch {1} (video {2}) — {3}".format(d["ma"], lich_s, vid, ghi))
            return {"ket_qua": "xong", "video_id": vid, "lich": lich_s, "ghi_chu": ghi}
        if loai == "da_len_lich" and luc:
            thuc = luc.strftime("%d/%m/%Y %H:%M")
            self.so.cap_nhat(k, trang_thai="lech-lich", lich=thuc)
            self.bao(d["ma"], "LỆCH LỊCH {0}".format(thuc), video_id=vid, lich=thuc)
            try:
                tb.ghi_bang_chung("lech-lich-" + d["ma"])
            except Exception:  # noqa: BLE001
                pass
            return {"ket_qua": "lech_lich", "video_id": vid, "lich": thuc,
                    "ly_do": "kênh hẹn {0}, kế hoạch {1}".format(thuc, lich_s)}
        if loai in ("cong_khai", "khong_cong_khai") and lich <= self.bay_gio() + timedelta(minutes=1):
            self.so.cap_nhat(k, trang_thai="xac-nhan", lich=lich_s)
            self.bao(d["ma"], "ĐÃ ĐĂNG", video_id=vid, lich=lich_s)
            return {"ket_qua": "xong", "video_id": vid, "lich": lich_s}
        ly_do = "không đọc được lịch trên Studio ({0}: {1!r})".format(loai, chuan_hoa_tieu_de(chu)[:80])
        lan_cxn = int(muc.get("lan_chua_xac_nhan") or 0) + 1
        # Không ghi `lich` ở đây: `lich` của sổ chỉ đến từ ô đã đọc lại (_hien_thi)
        # hoặc từ Studio — lịch kế hoạch chưa kiểm không được thành "đã đặt".
        self.so.cap_nhat(k, trang_thai="da-len-lich", lan_chua_xac_nhan=lan_cxn)
        if lan_cxn >= TRAN_CHUA_XAC_NHAN:
            # Không lặp mở Chrome vô hạn: đổi Trạng thái đăng khỏi ĐANG ĐĂNG
            # → chon_ma_can_dang thôi chọn; chủ kênh kiểm tay.
            self.bao(d["ma"], "CHƯA XÁC NHẬN LỊCH · {0}".format(vid), video_id=vid)
            self._canh_bao("{0}: {1} lượt liền không xác nhận được lịch video {2} — thôi kiểm, "
                           "chủ kênh xem tay".format(d["ma"], lan_cxn, vid))
        return {"ket_qua": "chua_xac_nhan", "video_id": vid, "lich": lich_s, "ly_do": ly_do}

    def _doc_lich_hop(self, tb, vid: str):
        """Dự phòng xác nhận: mở hộp Chế độ hiển thị ở trang sửa (khoá ĐÃ ĐO
        29/09), đọc ô ngày + ô giờ, Escape — KHÔNG bấm Xong/Lưu (Lưu nằm trong
        cam_bam). Trả (datetime|None, chữ của hộp)."""
        tb.mo(self._url("sua", id=vid), han=45)
        tb.tim("tieu_de", han=30)
        pt = tb.tim("sua_hien_thi_mo", han=10)
        if not pt:
            return None, ""
        # 30/09: `sua_hop_hien_thi` không khớp hộp thật → nhận cả ô ngày/giờ
        # hiện ra làm dấu hộp đã mở.
        tb.bam(pt, hau_dieu_kien=lambda: tb.co("sua_hop_hien_thi") or tb.co("o_ngay_mo") or tb.co("o_gio"),
               han_hau=10)
        self.ngu(1)
        chu_hop = tb.doc_chu("sua_hop_hien_thi") or ""
        if not chu_hop:
            try:
                tb.ghi_bang_chung("xac-nhan-hop-hien-thi-" + vid)   # để chốt bộ chọn hộp
            except Exception:  # noqa: BLE001
                pass
        luc = None
        if tb.co("o_ngay_mo") and tb.co("o_gio"):
            ngay, _ = phan_tich_ngay(tb.doc_chu("o_ngay_mo") or "")
            gio = phan_tich_gio(tb.doc_thuoc_tinh("o_gio", "value") or "")
            if ngay and gio:
                luc = datetime(ngay.year, ngay.month, ngay.day, gio[0], gio[1])
        for _ in range(2):
            if not (tb.co("sua_hop_hien_thi") or tb.co("o_ngay_mo")):
                break
            tb.phim("Escape")
            self.ngu(1)
        return luc, chu_hop

    def hau_kiem_tai_len(self, d: dict, vid: str, tep: dict, k: str) -> dict:
        """30/09/2026 — HẬU KIỂM sau khi lưu: mở trang sửa video trên tab B, bắt gói
        `get_creator_videos` của Studio → trạng thái xử lý + thời lượng, so với
        tệp mp4 (lệch ≤2 giây) hoặc "đang xử lý bình thường"; không bắt được gói
        thì lùi về chữ hàng video trong danh sách Nội dung (chỉ bắt lỗi rõ ràng).
        Ghi sổ `tai_xong`, `thoi_luong`, `thoi_luong_tep`, `hau_kiem`."""
        ma = d["ma"]
        dai_tep = thoi_luong_mp4_mvhd(tep.get("mp4") or "")
        tt, dai = "", None
        tb = self.tab_b()
        bat = getattr(tb, "bat_json", None)
        if callable(bat):
            try:
                for goi in bat(self._url("sua", id=vid), "get_creator_videos", han=30) or []:
                    for v in ((goi or {}).get("videos") or []):
                        if str(v.get("videoId") or "") != vid:
                            continue
                        tt = str(v.get("status") or "")
                        try:
                            dai = float(v["lengthSeconds"]) if str(v.get("lengthSeconds") or "").strip() else None
                        except (TypeError, ValueError, KeyError):
                            dai = None
                        break
                    if tt:
                        break
            except Exception as loi:  # noqa: BLE001 — lùi đường chữ
                self.nk("{0}: hậu kiểm — bắt gói Studio lỗi: {1}".format(ma, str(loi)[:120]))
        chu_hang = ""
        if not tt:
            try:
                for x in self.tra_kenh(d["tieu_de"], vid):
                    if x["video_id"] == vid:
                        chu_hang = str((x.get("hang") or {}).get("chu") or "")
                        break
            except Exception as loi:  # noqa: BLE001
                self.nk("{0}: hậu kiểm — đọc danh sách Nội dung lỗi: {1}".format(ma, str(loi)[:120]))
            if chu_hang:
                self.nk("{0}: hậu kiểm — hàng Nội dung «{1}»".format(ma, chuan_hoa_tieu_de(chu_hang)[:200]))
        kq = danh_gia_hau_kiem(tt, dai, dai_tep, chu_hang, self.bo.get("chu_trang_thai"))
        self.so.cap_nhat(k, tai_xong=kq["ket"] != "hong", thoi_luong=dai,
                         thoi_luong_tep=round(dai_tep, 1) if dai_tep else None,
                         hau_kiem="{0}: {1}".format(kq["ket"], kq["ly_do"]), trang_thai_studio=tt)
        self.nk("{0}: HẬU KIỂM tải lên video {1} — {2}: {3}".format(ma, vid, kq["ket"].upper(), kq["ly_do"]))
        return kq

    def _bao_su_co_tai_len(self, ma: str, vid: str, ly_do: str) -> None:
        """Sự cố tải lên → `vm/logs/su-co-tai-len.jsonl` + một dòng
        `workspace/loi-chay-max.md` (người gác tổng đọc) — không ném lỗi."""
        # Chỉ báo khi videoId khớp ĐÚNG mục sổ của gói (không bao giờ báo cho id lạ).
        if str(self.so.lay(self.khoa_so(ma)).get("video_id") or "") != str(vid or ""):
            self.nk("{0}: sự cố tải lên của {1} không khớp sổ — bỏ qua, không báo".format(ma, vid))
            return
        dong = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "kenh": self.kenh, "ma": ma,
                "video_id": vid, "ly_do": ly_do}
        # Ghi CẠNH SỔ đang dùng (bài kiểm dùng sổ trong thư mục tạm → không chạm vm/logs thật).
        thu_muc = os.path.dirname(os.path.abspath(self.so.duong))
        try:
            os.makedirs(thu_muc, exist_ok=True)
            with open(os.path.join(thu_muc, "su-co-tai-len.jsonl"), "a", encoding="utf-8") as tep:
                tep.write(json.dumps(dong, ensure_ascii=False) + "\n")
        except OSError:
            pass
        if os.path.normcase(os.path.abspath(self.so.duong)) != os.path.normcase(os.path.abspath(DUONG_SO)):
            return      # không phải sổ thật của máy → không báo gác tổng
        goc_tool = os.path.dirname(GOC)
        md = os.path.join(goc_tool, "workspace", "loi-chay-max.md")
        if os.path.isfile(os.path.join(goc_tool, "vps.json")) and os.path.isfile(md):
            try:
                with open(md, "a", encoding="utf-8") as tep:
                    tep.write("- [{0}] **khan** · kênh {1} — {2}: hậu kiểm tải lên video {3} HỎNG ({4}) — "
                              "gói đánh dấu TẢI MỚI lượt sau; bản trên kênh để kệ, chủ kênh xem/xoá.\n".format(
                                  time.strftime("%Y-%m-%d %H:%M"), self.kenh, ma, vid, ly_do))
            except OSError:
                pass

    def _da_co(self, d: dict, qd: dict, lich, k: str) -> dict:
        vid = qd.get("video_id") or ""
        if qd.get("tay"):
            self.so.cap_nhat(k, video_id=vid, trang_thai="xac-nhan", tay=True)
            self.bao(d["ma"], "ĐÃ ĐĂNG (tay)", video_id=vid)
            self.nk("{0}: cùng tiêu đề đã lên kênh ({1}) — báo ĐÃ ĐĂNG (tay), không tải".format(
                d["ma"], qd.get("loai")))
            return {"ket_qua": "da_co", "video_id": vid, "ly_do": qd.get("ly_do")}
        muc = self.so.lay(k)
        lich_so = phan_tich_ngay_gio(muc.get("lich") or "") or lich
        if lich_so is None:
            self.bao(d["ma"], "ĐÃ ĐĂNG", video_id=vid)
            return {"ket_qua": "da_co", "video_id": vid}
        kq = self.xac_nhan(d, vid, lich_so, k)
        if kq["ket_qua"] == "xong":
            kq["ket_qua"] = "da_co"
        return kq

    # ── một gói ──────────────────────────────────────────────────────────
    def dang_mot_goi(self, d: dict) -> dict:
        ma = d["ma"]
        k = self.khoa_so(ma)
        self.dang_tai = False
        tep = tep_goi(os.path.join(self.thu_muc_done, ma))
        loi = kiem_du_lieu_dong(d)
        if not tep["mp4"]:
            loi.append("gói không có .mp4 ({0})".format(os.path.join(self.thu_muc_done, ma)))
        lich, ghi_chu = gio_hen_hieu_luc(d.get("ngay"), d.get("gio"), self.bay_gio())
        if lich is None:
            loi.append(ghi_chu)
        if loi:
            self.nk("{0}: LỖI DỮ LIỆU — không tải: {1}".format(ma, "; ".join(loi)))
            return {"ket_qua": "loi_du_lieu", "ly_do": "; ".join(loi)}
        if ghi_chu:
            self._canh_bao("{0}: {1}".format(ma, ghi_chu))
        self.ghi_dodang(ma, "bat-dau")
        self.tai_xong_ok = False
        self.mhkt_nguon = ""
        self._d_dang = d
        self.han_tai = han_cho_tai(tep["mp4"])
        vid = ""
        ta = None
        try:
            self.lay_uc()
            muc = self.so.lay(k)
            hang = self.tra_kenh(d["tieu_de"], muc.get("video_id") or "")
            qd = quyet_dinh(d, muc, hang, self.bay_gio().date().isoformat())
            self.nk("{0}: quyết định {1} {2} — {3}".format(ma, qd["hanh_dong"], qd.get("video_id") or "",
                                                         qd.get("ly_do")))
            for x in qd.get("nhap_thua") or []:
                self.bao_cao["nhap_thua"].append({"ma": ma, "video_id": x})
                self._canh_bao("{0}: NHÁP THỪA trên kênh {1} (chỉ báo, không xoá)".format(ma, x))
            hd = qd["hanh_dong"]
            if hd == "tai_moi" and getattr(self, "nhap_khong_id", None):
                # 30/09/2026: nháp để kệ (chủ kênh tự xoá) — trước đây dừng hẳn
                # ở đây (lặp hỏng mãi); giờ chỉ báo rồi tải mới.
                self._canh_bao("{0}: kênh có {1} nháp không đọc được id (để kệ, chủ kênh xoá)".format(
                    ma, len(self.nhap_khong_id)))
            if hd == "bao_chu_kenh":
                self._canh_bao("{0}: {1} — không tải, không đánh dấu".format(ma, qd.get("ly_do")))
                return {"ket_qua": "bao_chu_kenh", "video_id": qd.get("video_id"), "ly_do": qd.get("ly_do")}
            if hd == "dung":
                return {"ket_qua": "hong_sau", "ly_do": qd.get("ly_do")}
            if hd == "da_co":
                return self._da_co(d, qd, lich, k)
            if not self.con_han(10 * 60):
                return {"ket_qua": "hong_truoc", "ly_do": "không đủ hạn phiên để bắt đầu gói"}
            ta = self.tao_trang()
            self.tab.append(ta)
            if hd == "tai_moi":
                vid = self._tai_moi(ta, d, tep, k, qd)
            else:
                vid = qd["video_id"]
                self.so.cap_nhat(k, video_id=vid, trang_thai="nhap")
                if qd.get("nhan_moi"):
                    self.bao(ma, "{0} · nháp {1}".format(TIEN_TO_DANG_DANG, vid), video_id=vid)
                self.ghi_dodang(ma, "tiep-nhap", vid)
                self._mo_nhap(ta, d, vid)
            self.vid_dang = vid
            try:
                self._chi_tiet(ta, d, tep)
                self._thanh_phan(ta, d, tep, k)
                self._kiem_tra(ta, k)
                self.ghi_dodang(ma, "hien-thi", vid)
                lich = self._hien_thi(ta, d, lich, k)
            except LoiSau:
                raise
            except Exception as loi:  # noqa: BLE001 — sau khi có id: mọi hỏng là "sau"
                try:
                    ta.ghi_bang_chung("hong-" + ma)
                except Exception:  # noqa: BLE001
                    pass
                raise LoiSau(str(loi))
            kq = self.xac_nhan(d, vid, lich, k)
            # 30/09/2026 — HẬU KIỂM tải lên sau khi lưu (mục 3c/3d của chủ kênh).
            try:
                hk = self.hau_kiem_tai_len(d, vid, tep, k)
            except Exception as loi:  # noqa: BLE001 — hậu kiểm hỏng ≠ video hỏng
                hk = {"ket": "chua-ro", "ly_do": "hậu kiểm lỗi: {0}".format(str(loi)[:100])}
                self.so.cap_nhat(k, tai_xong=True, hau_kiem="chua-ro: " + hk["ly_do"])
            if hk["ket"] == "hong" and str(self.so.lay(k).get("video_id") or "") == vid:
                self.so.cap_nhat(k, trang_thai="tai-hong", tai_xong=False)
                self.bao(ma, "{0} · tải hỏng {1}".format(TIEN_TO_DANG_DANG, vid), video_id=vid)
                self._canh_bao("{0}: HẬU KIỂM tải lên video {1} HỎNG ({2}) — lượt sau TẢI MỚI".format(
                    ma, vid, hk["ly_do"]))
                self._bao_su_co_tai_len(ma, vid, hk["ly_do"])
                return {"ket_qua": "hong_sau", "video_id": vid,
                        "ly_do": "hậu kiểm tải lên hỏng: " + hk["ly_do"]}
            kq["hau_kiem"] = hk["ket"]
            return kq
        except LoiTruoc as loi:
            self.nk("{0}: HỎNG TRƯỚC khi chạm kênh — {1}".format(ma, loi))
            if ta is not None:
                try:
                    ta.ghi_bang_chung("hong-truoc-" + ma)
                except Exception:  # noqa: BLE001
                    pass
            return {"ket_qua": "hong_truoc", "ly_do": str(loi)}
        except LoiSau as loi:
            self.nk("{0}: HỎNG SAU khi chạm kênh (video {1}) — {2}".format(ma, vid or "?", loi))
            return {"ket_qua": "hong_sau", "video_id": vid, "ly_do": str(loi)}
        finally:
            if ta is not None and self.dang_tai and vid:
                # Hỏng giữa chừng lúc video còn đang tải: cho nó tải NỐT (hạn theo
                # dung lượng, trong hạn phiên) — đóng tab lúc này là mất phần đã tải.
                try:
                    self._cho_tai_xong(ta, k)
                except Exception:  # noqa: BLE001
                    pass
            if ta is not None and not self.dang_tai:
                try:
                    ta.dong()
                    self.tab.remove(ta)
                except Exception:  # noqa: BLE001
                    pass
            elif ta is not None:
                # Vẫn chưa chắc tải xong: KHÔNG đóng tab — agent đóng Chrome
                # cuối phiên. Sổ đã ghi id để lượt sau tiếp.
                self._canh_bao("{0}: để tab tải lên mở (chưa chắc tải xong)".format(ma))
                self.tab_giu.append(ta)
                try:
                    if ta in self.tab:
                        self.tab.remove(ta)
                except Exception:  # noqa: BLE001
                    pass
            self.xoa_dodang()

    def chay(self, cac_dong: list) -> int:
        """Đăng lần lượt; trả mã thoát 0/1/3/4."""
        ma_thoat = MA_XONG
        for d in cac_dong:
            if not self.con_han(10 * 60):
                self._canh_bao("hết hạn phiên — dừng trước {0}".format(d["ma"]))
                ma_thoat = max(ma_thoat, MA_HONG) if ma_thoat != MA_LUI else ma_thoat
                break
            try:
                kq = self.dang_mot_goi(d)
            except DungKenh as loi:
                self.nk(str(loi))
                self.bao_cao["goi"].append({"ma": d["ma"], "ket_qua": "dung_kenh", "ly_do": str(loi)})
                return MA_CHAN
            kq["ma"] = d["ma"]
            self.bao_cao["goi"].append(kq)
            self.nk("{0}: KẾT QUẢ {1}{2}".format(d["ma"], kq["ket_qua"],
                                                   " — " + kq["ly_do"] if kq.get("ly_do") else ""))
            if kq["ket_qua"] == "hong_truoc":
                return MA_LUI if ma_thoat == MA_XONG else MA_HONG
            if kq["ket_qua"] not in ("xong", "da_co"):
                ma_thoat = MA_HONG
        return ma_thoat


# ═══ --kiem-dom ══════════════════════════════════════════════════════════

def kiem_dom(cdp, kenh: str, bo: dict, sau: bool = False, nhat_ky=None,
             ghi_dom_day_du: bool = False, tao_trang=None, duong_uc: str = DUONG_UC,
             ngu=None) -> dict:
    """Mức 1 (chỉ đọc) + mức 2 (--sau, cần một bản nháp). KHÔNG chọn tệp,
    KHÔNG gõ gì, KHÔNG bấm Lên lịch, KHÔNG lưu. Trả báo cáo {ok, hong, du_phong...}."""
    import cdp_studio  # noqa: PLC0415
    nk = nhat_ky or log.info
    ngu = ngu or time.sleep
    kq = {"ngay": time.strftime("%Y-%m-%d %H:%M:%S"), "kenh": kenh, "muc": 2 if sau else 1,
          "chrome": getattr(cdp, "phien_ban", ""), "uc": "", "ok": False, "hong": [],
          "du_phong": [], "chi_tiet": {}, "ghi_chu": [], "bang_chung": []}
    if tao_trang is None:
        def tao_trang():
            t = cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=nk)
            t.ghi_dom_day_du = ghi_dom_day_du
            return t
    tr = tao_trang()

    def ghi(khoa, pt, buoc):
        kq["chi_tiet"][khoa] = ({"khop": True, "cach": pt.get("cach"), "sel": pt.get("sel"),
                                 "mo_ta": pt.get("mo_ta"), "tat": pt.get("tat"), "so": pt.get("so"),
                                 "buoc": buoc}
                                if pt else {"khop": False, "buoc": buoc})
        if not pt:
            if khoa not in kq["hong"]:
                kq["hong"].append(khoa)
        elif pt.get("cach") != "chon#1":
            kq["du_phong"].append("{0}:{1}".format(khoa, pt.get("cach")))
        return pt

    def bang_chung(nhan):
        try:
            kq["bang_chung"].append(tr.ghi_bang_chung("kiem-" + nhan))
        except Exception as loi:  # noqa: BLE001
            kq["ghi_chu"].append("không ghi được bằng chứng {0}: {1}".format(nhan, loi))

    def dong_hop_upload(buoc):
        pt = ghi("dong_hop_upload", tr.tim("dong_hop_upload", han=5), buoc)
        if pt:
            try:
                tr.bam(pt, hau_dieu_kien=lambda: not tr.co("hop_upload"), han_hau=15)
            except Exception as loi:  # noqa: BLE001
                kq["ghi_chu"].append("đóng hộp tải lên: {0}".format(loi))
                bang_chung("dong-hop-upload")

    may = MayDangDom(kenh, bo, lambda: tr, SoVideoId(os.devnull), lambda *a, **k: True,
                     "", nhat_ky=nk, ngu=ngu, duong_uc=duong_uc)
    may._tb = tr
    try:
        # 1. Studio → UC
        try:
            kq["uc"] = may.lay_uc()
        except (LoiTruoc, DungKenh) as loi:
            kq["hong"].append("uc")
            kq["ghi_chu"].append(str(loi))
            bang_chung("uc")
            return kq
        # 2. Hộp tải lên (KHÔNG chọn tệp)
        tr.mo(may._url("upload"), han=60)
        ghi("hop_upload", tr.tim("hop_upload", han=45), "upload")
        tr.don_hop_la()
        ghi("nut_chon_tep", tr.tim("nut_chon_tep", han=20), "upload")
        ghi("o_tep_video", tr.tim("o_tep_video", han=5, hien=False, cho_tat=True), "upload")
        # Nút "Gửi ý kiến phản hồi" (nghi nguồn hộp "Allow … see this tab?")
        # PHẢI được máy dò nhận là CẤM bấm — kiểm mỗi lần.
        ph = tr.tim("nut_phan_hoi", han=3, cho_tat=True)
        kq["cam_bam_phan_hoi"] = (ph or {}).get("cam") or ("không thấy nút" if not ph else "")
        if ph and not ph.get("cam"):
            kq["hong"].append("cam_bam")
            kq["ghi_chu"].append("nút phản hồi KHÔNG bị nhận là cấm bấm — sửa cam_bam")
        bang_chung("upload")
        dong_hop_upload("upload")
        # 3. Danh sách
        tr.mo(may._url("danh_sach"), han=60)
        rows = may._doc_danh_sach(tr, han=40)
        ghi("hang_video", tr.tim("hang_video", han=0), "danh_sach")
        ghi("hang_tieu_de", tr.tim("hang_tieu_de", han=0), "danh_sach")
        hang = [may._hang_kenh(h) for h in rows or []]
        kq["hang"] = [{"video_id": x["video_id"], "tieu_de": x["tieu_de"][:60], "loai": x["loai"],
                       "luc": x["luc"].strftime("%d/%m/%Y %H:%M") if x["luc"] else "",
                       "che_do": chuan_hoa_tieu_de((x["hang"] or {}).get("che_do"))[:80],
                       "nhap": bool((x["hang"] or {}).get("nut_nhap"))} for x in hang[:15]]
        nhap = [x for x in hang if (x["hang"] or {}).get("nut_nhap")]
        kq["so_nhap"] = len(nhap)
        kq["nhap_8_video"] = [x["video_id"] for x in nhap if chuan_hoa_tieu_de(x["tieu_de"]) == "8 video"]
        if nhap:
            ghi("hang_sua_nhap", tr.tim("hang_sua_nhap", han=0), "danh_sach")
        bang_chung("danh-sach")
        # 4. Trang sửa video mới nhất (không phải nháp) — không lưu gì
        moi = next((x for x in hang if x["video_id"] and not (x["hang"] or {}).get("nut_nhap")), None)
        if moi:
            tr.mo(may._url("sua", id=moi["video_id"]), han=60)
            for khoa in ("tieu_de", "mo_ta", "playlist_mo", "hien_them"):
                ghi(khoa, tr.tim(khoa, han=30 if khoa == "tieu_de" else 8), "trang_sua")
            if not tr.co("o_the") and tr.co("hien_them"):
                try:
                    tr.bam("hien_them", hau_dieu_kien=lambda: tr.co("o_the"), han_hau=10)
                except Exception as loi:  # noqa: BLE001
                    kq["ghi_chu"].append("bấm Hiện thêm (trang sửa): {0}".format(loi))
            pt_o_the = ghi("o_the", tr.tim("o_the", han=8), "trang_sua")
            # "the_da_co" (chip thẻ đã có) CHỈ xuất hiện khi video đang được
            # kiểm thật sự có thẻ — video hợp lệ nhưng không gắn thẻ nào thì
            # ô này trống, không phải selector hỏng. Vá 30/09/2026: TL3-T7 bị
            # báo giả HỎNG vì video tự kiểm hôm đó không có thẻ (xem
            # vm/logs/kiem-dom/TL3-T7.json, workspace/loi-chay-max.md). Chỉ
            # coi là HỎNG khi ô nhập thẻ (`o_the`) — selector anh em, phải có
            # mặt cùng lúc — cũng KHÔNG tìm thấy, tức cả khối "Thẻ" trên
            # Studio không tải được, không riêng gì chip.
            pt_the_co = tr.tim("the_da_co", han=5)
            if pt_the_co:
                ghi("the_da_co", pt_the_co, "trang_sua")
            elif pt_o_the:
                kq["chi_tiet"]["the_da_co"] = {
                    "khop": None, "buoc": "trang_sua",
                    "ghi_chu": "video {0} không có thẻ nào — bỏ qua, không tính hỏng".format(
                        moi["video_id"])}
                kq["ghi_chu"].append(
                    "the_da_co: video {0} không có thẻ để kiểm (đã bỏ qua, không "
                    "phải selector hỏng — vá 30/09/2026)".format(moi["video_id"]))
            else:
                ghi("the_da_co", None, "trang_sua")  # o_the cũng hỏng -> khối Thẻ hỏng thật
            for khoa in ("khong_tre_em", "ai_co"):
                ghi(khoa, tr.tim(khoa, han=5), "trang_sua")
            try:
                kq["trang_sua_da_chon"] = {
                    k: tr.doc_thuoc_tinh(k, "aria-checked") for k in ("khong_tre_em", "ai_co")}
            except Exception:  # noqa: BLE001
                pass
            pt = ghi("hien_thi_trang_sua", tr.tim("hien_thi_trang_sua", han=10), "trang_sua")
            if pt:
                chu = tr.doc_chu(pt) or ""
                loai, luc = phan_tich_trang_thai(chu, bo.get("chu_trang_thai"))
                kq["trang_sua"] = {"video_id": moi["video_id"], "chu_hien_thi": chuan_hoa_tieu_de(chu)[:200],
                                   "loai": loai, "luc": luc.strftime("%d/%m/%Y %H:%M") if luc else ""}
            bang_chung("trang-sua")
        else:
            kq["ghi_chu"].append("kênh chưa có video (ngoài nháp) để kiểm trang sửa")
        # 5. Mức 2 — đi các bước của một bản nháp, không đặt gì
        if sau:
            if not nhap:
                kq["ghi_chu"].append("--sau: kênh KHÔNG có bản nháp — chỉ thăm dò hộp Lên lịch ở trang "
                                     "sửa (không lưu); bước Thành phần/Kiểm tra CHƯA kiểm được")
                kq["muc_2_thay"] = True
                if moi:
                    _kiem_lich_trang_sua(tr, may, kq, ghi, bang_chung, moi["video_id"], ngu)
                else:
                    kq["hong"].append("ban_nhap")
            else:
                _kiem_muc_2(tr, may, kq, ghi, bang_chung, dong_hop_upload, nhap, ngu)
    except Exception as loi:  # noqa: BLE001 — kiểm hỏng giữa chừng vẫn phải có báo cáo
        kq["hong"].append("loi_bat_ngo")
        kq["ghi_chu"].append("lỗi bất ngờ: {0}".format(str(loi)[:200]))
        bang_chung("loi-bat-ngo")
    finally:
        kq["ok"] = not kq["hong"]
        try:
            tr.dong()
        except Exception:  # noqa: BLE001
            pass
    return kq


def _kiem_muc_2(tr, may, kq, ghi, bang_chung, dong_hop_upload, nhap, ngu) -> None:
    uu = [x for x in nhap if chuan_hoa_tieu_de(x["tieu_de"]) == "8 video"] or nhap
    chon = uu[0]
    kq["nhap_da_mo"] = chon["video_id"]
    # Mở lại trang danh sách để lấy nút nháp còn sống (ghim cũ có thể đã mất).
    tr.mo(may._url("danh_sach"), han=60)
    rows = may._doc_danh_sach(tr, han=40) or []
    h = next((r for r in rows if any(rut_video_id(x) == chon["video_id"] for x in r.get("hrefs") or [])), None)
    if not h or not h.get("nut_nhap"):
        kq["hong"].append("hang_sua_nhap")
        return
    try:
        tr.bam(h["nut_nhap"], hau_dieu_kien=lambda: tr.co("hop_upload"), han_hau=30)
    except Exception as loi:  # noqa: BLE001
        kq["hong"].append("hang_sua_nhap")
        kq["ghi_chu"].append("mở bản nháp: {0}".format(loi))
        bang_chung("mo-nhap")
        return
    ngu(2)
    for khoa in ("tieu_de", "mo_ta", "nut_thumbnail", "playlist_mo", "khong_tre_em", "hien_them"):
        ghi(khoa, tr.tim(khoa, han=20 if khoa == "tieu_de" else 8), "nhap_chi_tiet")
    if not tr.co("ai_co") and tr.co("hien_them"):
        try:
            tr.bam("hien_them", hau_dieu_kien=lambda: tr.co("ai_co") or tr.co("o_the"), han_hau=10)
        except Exception as loi:  # noqa: BLE001
            kq["ghi_chu"].append("bấm Hiện thêm (nháp): {0}".format(loi))
    ghi("ai_co", tr.tim("ai_co", han=8), "nhap_chi_tiet")
    ghi("o_the", tr.tim("o_the", han=5), "nhap_chi_tiet")
    ghi("tien_do", tr.tim("tien_do", han=3, cho_tat=True), "nhap_chi_tiet")
    try:
        kq["tien_do_chu"] = chuan_hoa_tieu_de(tr.doc_chu("tien_do") or "")[:120]
    except Exception:  # noqa: BLE001
        pass
    bang_chung("nhap-chi-tiet")

    def tiep(hau, ten):
        pt = ghi("nut_tiep", tr.tim("nut_tiep", han=10), ten)
        if not pt:
            return False
        try:
            tr.bam(pt, hau_dieu_kien=hau, han_hau=30)
            return True
        except Exception as loi:  # noqa: BLE001
            kq["hong"].append("buoc_" + ten)
            kq["ghi_chu"].append("sang bước {0}: {1}".format(ten, loi))
            bang_chung("buoc-" + ten)
            return False

    if tiep(lambda: tr.co("phu_de_them", cho_tat=True) or tr.co("mhkt_them", cho_tat=True)
            or tr.co("the_them", cho_tat=True), "thanh_phan"):
        ngu(2)
        for khoa in ("phu_de_them", "mhkt_nhap", "mhkt_them", "the_them"):
            ghi(khoa, tr.tim(khoa, han=8, cho_tat=True), "thanh_phan")
        bang_chung("thanh-phan")
        if tiep(lambda: not tr.co("phu_de_them", cho_tat=True) and not tr.co("mhkt_them", cho_tat=True),
                "kiem_tra"):
            ngu(2)
            bang_chung("kiem-tra")
            if tiep(lambda: tr.co("len_lich_mo"), "hien_thi"):
                ngu(1.5)
                pt = ghi("len_lich_mo", tr.tim("len_lich_mo", han=10), "hien_thi")
                bang_chung("hien-thi")
                if pt:
                    try:
                        tr.bam(pt, hau_dieu_kien=lambda: tr.co("o_ngay_mo") or tr.co("o_gio"), han_hau=10)
                    except Exception as loi:  # noqa: BLE001
                        kq["ghi_chu"].append("mở Lên lịch: {0}".format(loi))
                ptn = ghi("o_ngay_mo", tr.tim("o_ngay_mo", han=8), "hien_thi")
                ghi("o_gio", tr.tim("o_gio", han=5), "hien_thi")
                ptx = ghi("nut_xong", tr.tim("nut_xong", han=5, cho_tat=True), "hien_thi")
                if ptx:
                    kq["nut_xong_chu"] = chuan_hoa_tieu_de(tr.doc_chu(ptx) or "")
                try:
                    kq["o_ngay_mo_chu"] = chuan_hoa_tieu_de(tr.doc_chu("o_ngay_mo") or "")
                    kq["o_gio_gia_tri"] = str(tr.doc_thuoc_tinh("o_gio", "value") or "")
                except Exception:  # noqa: BLE001
                    pass
                bang_chung("len-lich")
                if ptn:
                    try:
                        tr.bam(ptn, hau_dieu_kien=lambda: tr.co("o_ngay"), han_hau=8)
                        ghi("o_ngay", tr.tim("o_ngay", han=5), "hien_thi")
                        bang_chung("chon-ngay")
                        tr.phim("Escape")
                        ngu(1)
                        if not tr.co("hop_upload"):
                            kq["ghi_chu"].append("Escape ở ô ngày đã đóng cả hộp tải lên")
                    except Exception as loi:  # noqa: BLE001
                        ghi("o_ngay", None, "hien_thi")
                        kq["ghi_chu"].append("mở ô ngày: {0}".format(loi))
    if tr.co("hop_upload"):
        dong_hop_upload("dong_nhap")
        ngu(1.5)
        if tr.co("hop_upload"):
            kq["ghi_chu"].append("hộp tải lên chưa đóng sau khi bấm X")
            bang_chung("chua-dong")


def _kiem_lich_trang_sua(tr, may, kq, ghi, bang_chung, vid, ngu) -> None:
    """Mức 2 THAY THẾ khi kênh không có nháp: trên trang sửa của một video đã
    đăng, mở hộp Chế độ hiển thị → mở "Lên lịch" → mở ô ngày → đọc → Huỷ.
    KHÔNG gõ, KHÔNG bấm Xong/Lưu: nút Lưu của trang nằm trong `cam_bam` (máy
    từ chối bấm), và phải còn TẮT sau khi thăm dò — không thì bấm "Huỷ thay
    đổi" rồi rời trang (beforeunload chấp nhận = bỏ thay đổi)."""
    tr.mo(may._url("sua", id=vid), han=60)
    tr.tim("tieu_de", han=30)
    luu = tr.tim("sua_luu", han=5, cho_tat=True)
    kq["sua_luu_truoc"] = {"thay": bool(luu), "tat": (luu or {}).get("tat"), "cam": (luu or {}).get("cam")}
    # Hộp danh sách phát: mở, dò mục + nút Xong, Escape — KHÔNG tích mục nào.
    pt = ghi("playlist_mo", tr.tim("playlist_mo", han=8), "lich_trang_sua")
    if pt:
        try:
            tr.bam(pt, hau_dieu_kien=lambda: tr.co("playlist_muc"), han_hau=10)
            ghi("playlist_muc", tr.tim("playlist_muc", han=5), "lich_trang_sua")
            ghi("playlist_xong", tr.tim("playlist_xong", han=5), "lich_trang_sua")
            bang_chung("sua-playlist")
        except Exception as loi:  # noqa: BLE001
            ghi("playlist_muc", None, "lich_trang_sua")
            kq["ghi_chu"].append("mở hộp danh sách phát: {0}".format(loi))
            bang_chung("sua-playlist-hong")
        for _ in range(2):
            if not tr.co("playlist_muc"):
                break
            tr.phim("Escape")
            ngu(1)
    pt = ghi("sua_hien_thi_mo", tr.tim("sua_hien_thi_mo", han=8), "lich_trang_sua")
    if not pt:
        return
    try:
        tr.bam(pt, hau_dieu_kien=lambda: tr.co("len_lich_mo") or tr.co("sua_hop_hien_thi"), han_hau=10)
    except Exception as loi:  # noqa: BLE001
        kq["hong"].append("sua_hien_thi_mo")
        kq["ghi_chu"].append("mở hộp Chế độ hiển thị: {0}".format(loi))
        bang_chung("sua-hien-thi-mo")
        return
    ngu(1)
    ghi("sua_hop_hien_thi", tr.tim("sua_hop_hien_thi", han=5), "lich_trang_sua")
    pt = ghi("len_lich_mo", tr.tim("len_lich_mo", han=8), "lich_trang_sua")
    bang_chung("sua-hien-thi")
    if pt:
        try:
            tr.bam(pt, hau_dieu_kien=lambda: tr.co("o_ngay_mo") or tr.co("o_gio"), han_hau=10)
        except Exception as loi:  # noqa: BLE001
            kq["ghi_chu"].append("mở Lên lịch (trang sửa): {0}".format(loi))
        ngu(1)
        ptn = ghi("o_ngay_mo", tr.tim("o_ngay_mo", han=8), "lich_trang_sua")
        ghi("o_gio", tr.tim("o_gio", han=5), "lich_trang_sua")
        try:
            kq["o_ngay_mo_chu"] = chuan_hoa_tieu_de(tr.doc_chu("o_ngay_mo") or "")
            kq["o_gio_gia_tri"] = str(tr.doc_thuoc_tinh("o_gio", "value") or "")
        except Exception:  # noqa: BLE001
            pass
        bang_chung("sua-lich")
        if ptn:
            try:
                tr.bam(ptn, hau_dieu_kien=lambda: tr.co("o_ngay"), han_hau=8)
                ghi("o_ngay", tr.tim("o_ngay", han=5), "lich_trang_sua")
                kq["o_ngay_gia_tri"] = str(tr.doc_thuoc_tinh("o_ngay", "value") or "")
                bang_chung("sua-chon-ngay")
                tr.phim("Escape")
                ngu(1)
            except Exception as loi:  # noqa: BLE001
                ghi("o_ngay", None, "lich_trang_sua")
                kq["ghi_chu"].append("mở ô ngày (trang sửa): {0}".format(loi))
    # Hộp Chế độ hiển thị KHÔNG có nút Huỷ (đo 29/09: chỉ "Xong" = áp vào
    # form) → đóng bằng Escape, KHÔNG bấm Xong.
    for _ in range(2):
        if not tr.co("sua_hop_hien_thi"):
            break
        tr.phim("Escape")
        ngu(1)
    if tr.co("sua_hop_hien_thi"):
        kq["hong"].append("dong_hop_hien_thi")
        kq["ghi_chu"].append("Escape không đóng được hộp Chế độ hiển thị")
    luu = tr.tim("sua_luu", han=5, cho_tat=True)
    kq["sua_luu_sau"] = {"thay": bool(luu), "tat": (luu or {}).get("tat"), "cam": (luu or {}).get("cam")}
    if luu and not luu.get("tat"):
        kq["ghi_chu"].append("nút Lưu trang sửa BẬT sau thăm dò — bấm Huỷ thay đổi, không lưu")
        try:
            tr.bam("sua_huy_thay_doi", han_hau=5)
        except Exception as loi:  # noqa: BLE001
            kq["ghi_chu"].append("Huỷ thay đổi: {0} — rời trang (beforeunload chấp nhận = bỏ)".format(loi))
    bang_chung("sua-sau-huy")
    tr.mo(may._url("danh_sach"), han=60)


def ghi_bao_cao_kiem(kq: dict, thu_muc: str = THU_MUC_KIEM) -> str:
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, "{0}.json".format(kq.get("kenh") or "kenh"))
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(kq, tep, ensure_ascii=False, indent=1, default=str)
    os.replace(tam, duong)
    return duong


# ═══ CLI ═════════════════════════════════════════════════════════════════

_O_KHOA = None


def _khoa_mot_minh(cong: int = CONG_KHOA) -> bool:
    """Chỉ MỘT máy đăng DOM mỗi máy — ổ khoá cổng TCP 127.0.0.1 (chết là HĐH nhả)."""
    global _O_KHOA
    try:
        _O_KHOA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA.bind(("127.0.0.1", cong))
        _O_KHOA.listen(1)
        return True
    except OSError:
        return False


def _tu_dang_bat(kenh: str) -> bool:
    try:
        with open(os.path.join(GOC, "cai-dat-tool.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep) or {}
    except (OSError, ValueError):
        return False
    rieng = (du.get("kenh") or {}).get(kenh)
    if isinstance(rieng, dict) and "tu_dang" in rieng:
        return bool(rieng["tu_dang"])
    return bool(du.get("tu_dang", False))


def _cai_dat_kenh(kenh: str) -> dict:
    """may-ao.json (tuỳ chọn `danh_sach_phat`) + ngôn ngữ từ kenh.yaml — chỉ đọc."""
    ra = {}
    goc_tool = os.path.dirname(GOC)
    try:
        with open(os.path.join(goc_tool, "CHANNEL", kenh, "may-ao.json"), "r", encoding="utf-8") as tep:
            ra.update(json.load(tep) or {})
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(goc_tool, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8") as tep:
            for dong in tep:
                m = re.match(r'^ngon_ngu:\s*"?([A-Za-z-]+)"?', dong)
                if m:
                    ra["ngon_ngu"] = m.group(1)
                    break
    except OSError:
        pass
    return ra


def tao_bao_truc_tiep(kenh: str, goc_tool: str = None):
    """Báo trạng thái KHÔNG qua trạm (29/09/2026): trạm 8765 chạy NHÚNG trong
    cửa sổ MyTool nên còn nạp `core/ke_hoach_dang` ĐỜI CŨ (lỗi `splitlines`
    nuốt xuống dòng Mô tả mỗi lần ghi lại kế hoạch, và bỏ qua video_id) cho tới
    khi MyTool được mở lại. Chỉ dùng trên VPS (MyTool cùng máy, có `vps.json`):
    ghi thẳng bằng mã MỚI trên đĩa — cùng hai hàm mà route `/dang-xong` mới gọi."""
    goc_tool = goc_tool or os.path.dirname(GOC)
    if not os.path.isfile(os.path.join(goc_tool, "vps.json")):
        raise RuntimeError("--bao-truc-tiep chỉ dùng được trên VPS (có vps.json)")
    if goc_tool not in sys.path:
        sys.path.insert(0, goc_tool)
    from core import ke_hoach_dang  # noqa: PLC0415
    from core import ho_so_video  # noqa: PLC0415

    def bao(ma, trang_thai, **them):
        vid = them.get("video_id") or None
        duoc = ke_hoach_dang.danh_dau(goc_tool, kenh, ma, trang_thai, video_id=vid)
        log.info("báo trực tiếp kế hoạch %s: %s → %s%s%s", kenh, ma, trang_thai,
                 " · Video ID " + vid if vid else "", "" if duoc else " (KHÔNG thấy mã)")
        if vid and str(trang_thai).startswith("ĐÃ ĐĂNG"):
            try:
                ho_so_video.ghi_video_id(goc_tool, kenh, ma, vid, them.get("lich") or "")
            except Exception as loi:  # noqa: BLE001 — hồ sơ hỏng không chặn báo ĐÃ ĐĂNG
                log.warning("ghi video_id vào hồ sơ lỗi: %s", loi)
        return duoc
    return bao


def _cai_nhat_ky(ra_man_hinh: bool) -> None:
    os.makedirs(THU_MUC_LOG, exist_ok=True)
    tay = []
    try:
        from logging.handlers import RotatingFileHandler
        tay.append(RotatingFileHandler(os.path.join(THU_MUC_LOG, "dang-dom.log"),
                                       maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"))
    except OSError:
        pass
    try:
        if ra_man_hinh or (sys.stderr and sys.stderr.isatty()) or not tay:
            tay.append(logging.StreamHandler(sys.stdout))
    except Exception:  # noqa: BLE001
        pass
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    for t in tay:
        t.setFormatter(fmt)
        log.addHandler(t)
    log.setLevel(logging.INFO)


def _doc_lenh(argv):
    ap = argparse.ArgumentParser(prog="may_dang_dom.py")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--mot-lan", action="store_true")
    ap.add_argument("--kiem-dom", action="store_true")
    ap.add_argument("--sau", action="store_true")
    ap.add_argument("--ma")
    ap.add_argument("--bo-loc-ngay", action="store_true")
    ap.add_argument("--trong-phien", action="store_true",
                    help="agent gọi giữa phiên — dùng khoá máy của agent, không tự giữ")
    ap.add_argument("--ghi-dom-day-du", action="store_true")
    ap.add_argument("--bao-truc-tiep", action="store_true",
                    help="VPS: ghi kế hoạch bằng core.ke_hoach_dang.danh_dau trên đĩa, không qua trạm")
    ap.add_argument("--them-the", action="store_true",
                    help="với --ma: thêm thẻ cho video ĐÃ lên lịch qua trang sửa (id lấy từ sổ)")
    ap.add_argument("--cua-so-gio", type=float, default=0.0,
                    help="tải bổ sung: nhận lịch trong (bây giờ + biên, bây giờ + N giờ]")
    ap.add_argument("--bien-gio", type=float, default=2.0)
    ap.add_argument("--toi-da-ngay", type=int, default=TAI_LEN_TOI_DA_NGAY,
                    help="trần số lần TẢI MỚI mỗi kênh mỗi ngày (chế độ cửa sổ)")
    ap.add_argument("--them-mhkt", action="store_true",
                    help="với --ma: bổ sung màn hình kết thúc (nhập từ video mới nhất) qua trang sửa")
    ap.add_argument("--lam-lai-the", action="store_true",
                    help="với --them-the: xoá thẻ đang có rồi thêm lại")
    ap.add_argument("--khong-the", action="store_true")
    ap.add_argument("--khong-mhkt", action="store_true")
    ap.add_argument("--bu-mhkt", action="store_true",
                    help="BÙ MHKT video đã đăng mà thiếu (sổ mhkt=bo/lỗi/rỗng) qua trang sửa — agent gọi giờ vắng")
    ap.add_argument("--toi-da-video", type=int, default=BU_MHKT_TOI_DA_DEM,
                    help="với --bu-mhkt: tối đa số video/kênh/đêm")
    ap.add_argument("--han-giay", type=float, default=0.0,
                    help="hạn phiên (giây); 0 = theo config phien_han_dang_giay")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = _doc_lenh(sys.argv[1:] if argv is None else argv)
    _cai_nhat_ky(ra_man_hinh=a.kiem_dom or bool(a.ma))
    import agent  # noqa: PLC0415
    import cdp as cdp_mod  # noqa: PLC0415
    import cdp_studio  # noqa: PLC0415
    import nguon_tool  # noqa: PLC0415

    if not _khoa_mot_minh():
        log.error("đã có một máy đăng DOM khác đang chạy (cổng %d) — thoát", CONG_KHOA)
        return MA_CHAN
    tu_giu = not a.trong_phien
    if tu_giu and not agent.giu_khoa_may_chung():
        log.error("không giữ được khoá máy (.khoa-may) — có việc nặng/phiên kênh đang chạy; không ép")
        return MA_CHAN
    cdp = None
    may = None
    tab_cua_toi = []
    try:
        if agent.van_ipv4_mo():
            log.error("van IPv4 đang mở — không nối Chrome kênh")
            return MA_CHAN
        cfg = agent.doc_cau_hinh()
        bo = cdp_studio.doc_bo_chon()
        loi_bo = cdp_studio.kiem_bo_chon(bo)
        if loi_bo:
            log.error("studio-selectors.json lỗi: %s", "; ".join(loi_bo))
            return MA_LUI
        if a.bu_mhkt:
            # BÙ MHKT: hàng lấy từ SỔ (không cần kế hoạch); kế hoạch chỉ để tìm video
            # nguồn theo tiêu đề — đọc hỏng thì vẫn làm (tìm theo videoId).
            cac = hang_bu_mhkt(SoVideoId().doc(), a.kenh, date.today().isoformat(), a.toi_da_video)
            if not cac:
                log.info("kênh %s: không có video nào cần bù MHKT đêm nay", a.kenh)
                return MA_XONG
            log.info("kênh %s: bù MHKT %d video: %s", a.kenh, len(cac), ", ".join(k for k, _v in cac))
            try:
                if a.bao_truc_tiep:
                    goc_tool = os.path.dirname(GOC)
                    if goc_tool not in sys.path:
                        sys.path.insert(0, goc_tool)
                    from core import ke_hoach_dang  # noqa: PLC0415
                    hang = [[""] * nguon_tool.RONG_DONG] + nguon_tool.hang_tu_csv(
                        ke_hoach_dang.doc_van_ban(goc_tool, a.kenh), a.kenh)
                else:
                    hang = nguon_tool.get_rows(dict(cfg, cac_kenh=[a.kenh]))
            except Exception as loi:  # noqa: BLE001
                log.info("bù MHKT: không đọc được kế hoạch (%s) — tìm nguồn theo videoId", str(loi)[:120])
                hang = [[]]
        elif not a.kiem_dom:
            if a.mot_lan and not a.ma and not _tu_dang_bat(a.kenh):
                log.info("kênh %s: tu_dang đang TẮT — bỏ qua", a.kenh)
                return MA_XONG
            if a.bao_truc_tiep:
                # Đọc THẲNG kế hoạch trên đĩa (cùng tệp trạm phục vụ ở /ke-hoach) —
                # trạm tắt thì bản đệm vm/ke-hoach-<k>.csv có thể đã cũ.
                goc_tool = os.path.dirname(GOC)
                if goc_tool not in sys.path:
                    sys.path.insert(0, goc_tool)
                from core import ke_hoach_dang  # noqa: PLC0415
                hang = [[""] * nguon_tool.RONG_DONG] + nguon_tool.hang_tu_csv(
                    ke_hoach_dang.doc_van_ban(goc_tool, a.kenh), a.kenh)
            else:
                hang = nguon_tool.get_rows(dict(cfg, cac_kenh=[a.kenh]))
            for x, y in trung_tieu_de(hang, a.kenh):
                log.warning("CẢNH BÁO kế hoạch %s và %s TRÙNG tiêu đề", x, y)
            if a.them_the or a.them_mhkt:
                # Bổ sung thẻ / màn hình kết thúc cho video ĐÃ lên lịch: dòng lấy theo mã, bất kể trạng thái.
                cac = [d for d in (dong_tu_hang(r) for r in hang[1:]) if d["ma"] == a.ma]
                vid_so = SoVideoId().lay("{0}/{1}".format(a.kenh, a.ma)).get("video_id")
                if not a.ma or not cac or not vid_so:
                    log.error("--them-the cần --ma có trong kế hoạch VÀ có video_id trong sổ")
                    return MA_HONG
            else:
                cua_so = ((timedelta(hours=a.bien_gio), timedelta(hours=a.cua_so_gio))
                          if a.cua_so_gio > 0 else None)
                cac = chon_ma_can_dang(hang, a.kenh, datetime.now(), bo_loc_ngay=a.bo_loc_ngay,
                                       ma=a.ma, cua_so=cua_so)
                if cua_so:
                    cac = gioi_han_tai_moi(cac, SoVideoId().doc(), a.kenh,
                                           date.today().isoformat(), a.toi_da_ngay)
            if not cac:
                log.info("kênh %s: không có mã cần đăng%s", a.kenh,
                         " (mã {0})".format(a.ma) if a.ma else "")
                return MA_XONG
            log.info("kênh %s: %d mã cần đăng: %s", a.kenh, len(cac), ", ".join(d["ma"] for d in cac))
        try:
            cdp = cdp_mod.ket_noi_kenh(cfg, a.kenh, nhat_ky=log.info)
        except cdp_mod.CdpKhongDung as loi:
            log.error("không dùng được đường DOM: %s (mã %d)", loi.ly_do, loi.ma)
            return loi.ma
        log.info("đã nối Chrome kênh %s (%s, cổng %s%s)", a.kenh, cdp.phien_ban, cdp.cong,
                 ", máy này tự mở" if cdp.tu_mo else "")
        if a.kiem_dom:
            kq = kiem_dom(cdp, a.kenh, bo, sau=a.sau, nhat_ky=log.info, ghi_dom_day_du=a.ghi_dom_day_du)
            duong = ghi_bao_cao_kiem(kq)
            dong = "máy đăng DOM kiểm {0} mức {1}: {2}{3}{4}".format(
                a.kenh, kq["muc"], "OK" if kq["ok"] else "HỎNG " + ", ".join(kq["hong"]),
                " · dự phòng " + ", ".join(kq["du_phong"]) if kq["du_phong"] else "",
                " · " + kq["chrome"] if kq.get("chrome") else "")
            log.info("%s → %s", dong, duong)
            try:
                agent.ghi(dong)
            except Exception:  # noqa: BLE001
                pass
            return MA_XONG if kq["ok"] else MA_LUI

        def tao_trang():
            t = cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=log.info,
                                                  thu_muc_dom=cdp_studio.THU_MUC_DOM)
            tab_cua_toi.append(t)
            return t

        thu_muc = nguon_tool.thu_muc_dang(cfg, a.kenh) or os.path.join(os.path.dirname(GOC), "DONE", a.kenh)
        bao = (tao_bao_truc_tiep(a.kenh) if a.bao_truc_tiep else
               (lambda ma, tt, **them: nguon_tool.bao_dang(cfg, ma, tt, kenh=a.kenh, **them)))
        may = MayDangDom(
            a.kenh, bo, tao_trang, SoVideoId(), bao,
            thu_muc, nhat_ky=log.info,
            han_giay=float(a.han_giay or cfg.get("phien_han_dang_giay") or HAN_PHIEN_MAC_DINH),
            cai_dat_kenh=_cai_dat_kenh(a.kenh), lam_the=not a.khong_the, lam_mhkt=not a.khong_mhkt)
        may.tieu_de_theo_ma = {x["ma"]: x["tieu_de"] for x in (dong_tu_hang(r) for r in hang[1:])
                               if x.get("ma") and x.get("kenh") == a.kenh}
        ma_thoat = MA_HONG
        try:
            if a.bu_mhkt:
                may.lay_uc()
                ma_thoat = may.bu_mhkt(cac)
            elif a.them_the or a.them_mhkt:
                d = cac[0]
                khoa = "{0}/{1}".format(a.kenh, a.ma)
                vid = may.so.lay(khoa)["video_id"]
                may.lay_uc()
                ma_thoat = MA_XONG
                if a.them_mhkt:
                    kq_mh = may.them_mhkt_trang_sua(d, vid)
                    may.so.cap_nhat(khoa, mhkt=kq_mh)
                    log.info("%s: màn hình kết thúc (trang sửa) → %s", a.ma, kq_mh)
                    if not kq_mh.startswith("ok"):
                        ma_thoat = MA_HONG
                if a.them_the:
                    kq_the = may.them_the_trang_sua(d, vid, tep_goi(os.path.join(thu_muc, a.ma)),
                                                    lam_lai=a.lam_lai_the)
                    may.so.cap_nhat(khoa, the=kq_the)
                    log.info("%s: thẻ (trang sửa) → %s", a.ma, kq_the)
                    if not kq_the.startswith("ok"):
                        ma_thoat = MA_HONG
            else:
                ma_thoat = may.chay(cac)
        finally:
            may.dong_het()
            try:
                # Video thiếu MHKT: danh sách cập nhật mỗi lượt; agent bù giờ vắng (`--bu-mhkt`).
                # Ghi CẠNH SỔ đang dùng (sổ thật → vm/logs).
                with open(os.path.join(os.path.dirname(os.path.abspath(may.so.duong)), "mhkt-thieu.json"),
                          "w", encoding="utf-8") as tep:
                    json.dump(danh_sach_thieu_mhkt(may.so.doc()), tep, ensure_ascii=False, indent=1)
            except OSError:
                pass
            try:
                with open(DUONG_BAO_CAO, "w", encoding="utf-8") as tep:
                    json.dump(dict(may.bao_cao, ma_thoat=ma_thoat,
                                   luc=time.strftime("%Y-%m-%d %H:%M:%S")),
                              tep, ensure_ascii=False, indent=1, default=str)
            except OSError:
                pass
        log.info("kênh %s: xong, mã thoát %d", a.kenh, ma_thoat)
        return ma_thoat
    except Exception as loi:  # noqa: BLE001 — không chết im lặng
        log.exception("lỗi không lường: %s", loi)
        return MA_HONG
    finally:
        if cdp is not None:
            # Tab của mình đã được đóng ở `may.dong_het()`/`kiem_dom` — trừ tab
            # tải lên CHƯA CHẮC tải xong (cố ý để mở, xem dang_mot_goi).
            if may is not None and may.tab_giu:
                log.warning("CÒN tab tải lên chưa chắc tải xong — KHÔNG đóng Chrome kênh %s (cổng %s); "
                            "đóng sau khi tải xong", a.kenh, cdp.cong)
                cdp.dong()
            elif cdp.tu_mo and not a.trong_phien:
                ok = cdp_mod.dong_trinh_duyet(cdp)
                log.info("đóng Chrome kênh %s (máy này đã mở): %s", a.kenh,
                         "cổng đã đóng" if ok else "CỔNG CHƯA ĐÓNG sau 20s")
            else:
                cdp.dong()
        if tu_giu:
            agent.nha_khoa_may_chung()


if __name__ == "__main__":
    raise SystemExit(main())
