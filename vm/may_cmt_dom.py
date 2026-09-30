"""MÁY BÌNH LUẬN DOM/CDP — bình luận mồi + GHIM + trả lời bình luận, KHÔNG cần OAuth.

Vì sao có tệp này (29/09/2026): `may_cmt.py` đi YouTube Data API, nhưng chưa kênh
nào làm OAuth (`vm/tokens/`, `vm/clients/` trống) → không trả lời được bình luận
nào; và API KHÔNG ghim được bình luận (việc tay ở `CHANNEL/<k>/can-ghim.md`).
Máy này làm cả hai bằng DOM ngay trong Chrome kênh ĐÃ đăng nhập, cùng động cơ và
cùng luật với máy đăng DOM (`cdp.py`, `cdp_studio.TrangStudio`): tab riêng, bấm
có kiểm đích, gõ rồi ĐỌC LẠI, `cam_bam`, không `Runtime.enable`.

Cách chạy:

    python vm/may_cmt_dom.py --kenh TL1-T7 --mot-lan [--trong-phien]   # mồi+ghim rồi trả lời
    python vm/may_cmt_dom.py --kenh TL1-T7 --chi-moi [--trong-phien]   # chỉ mồi+ghim (ghim sớm)
    python vm/may_cmt_dom.py --kenh TL1-T7 --chi-tra-loi --toi-da 2
    python vm/may_cmt_dom.py --kenh TL1-T7 --ma TL1-T7-0005 --chi-moi  # đúng một gói
    python vm/may_cmt_dom.py --kenh TL1-T7 --kiem-dom [--video ID] [--mo-hop]  # CHỈ ĐỌC

Mã thoát (như máy đăng DOM): 0 xong / không có việc · 1 hỏng SAU khi đã chạm kênh
(đã gõ/đăng) · 3 đường DOM không dùng được TRƯỚC khi chạm kênh · 4 bị chặn an toàn
(van IPv4, khoá máy, sai kênh, máy bình luận DOM khác đang chạy).

Sổ:

* `vm/logs/cmt-dom.json` — theo videoId: `da_dang_moi`, `da_ghim`, `comment_id`,
  `trang_thai` (dang-gui | da-dang | da-ghim | ghim-khac | tat-binh-luan | …),
  `lan_gui`, `lan_thu_ghim`, bản sao `van_ban` (gói DONE bị dọn sau khi đăng).
* `vm/replied/<k>.txt` — id bình luận ĐÃ trả lời, CHUNG với `may_cmt.py` (cùng id
  `Ugx…` của YouTube) → hai đường không bao giờ trả lời trùng nhau.

Luật: không bao giờ bật IPv4; không taskkill; chỉ đóng TAB của mình (Chrome do
agent mở thì agent đóng); spam/link/xúc phạm: để NGUYÊN, không xoá, không trả lời.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import os
import random
import re
import socket
import sys
import time
import unicodedata
import urllib.parse
from datetime import datetime, timedelta

GOC = os.path.dirname(os.path.abspath(__file__))
if GOC not in sys.path:
    sys.path.insert(0, GOC)

GOC_TOOL = os.path.dirname(GOC)
THU_MUC_LOG = os.path.join(GOC, "logs")
DUONG_SO_CMT = os.path.join(THU_MUC_LOG, "cmt-dom.json")
DUONG_SO_VIDEO = os.path.join(THU_MUC_LOG, "so-video-id.json")
DUONG_BAO_CAO = os.path.join(THU_MUC_LOG, "cmt-dom-cuoi.json")
THU_MUC_KIEM = os.path.join(THU_MUC_LOG, "kiem-dom")
THU_MUC_REPLIED = os.path.join(GOC, "replied")
CONG_KHOA = 8771

MA_XONG, MA_HONG, MA_LUI, MA_CHAN = 0, 1, 3, 4

#: Mặc định số trả lời tối đa mỗi kênh mỗi phiên (ghi đè: `cmt_toi_da_phien`).
TOI_DA_TRA_LOI = 10
#: Giãn cách ngẫu nhiên giữa hai trả lời (giây).
GIAN_MIN, GIAN_MAX = 20.0, 60.0
#: Chỉ mồi cho video công khai trong chừng này ngày gần đây (theo Ngày đăng kế hoạch / lịch sổ).
CUA_SO_MOI_NGAY = 7
#: Trần số lần GỬI bình luận mồi cho một video và số lần thử ghim. Gửi = 1: đã bấm
#: gửi mà không đọc lại thấy thì DỪNG chờ người xem, không bao giờ tự gửi lần hai.
TRAN_GUI = 1
TRAN_THU_GHIM = 3
#: Trần số bình luận mồi mỗi lượt (an toàn chống spam).
TOI_DA_MOI_LUOT = 3

log = logging.getLogger("may_cmt_dom")

NGON_NGU = {"ja": "Japanese", "vi": "Vietnamese", "en": "English", "es": "Spanish",
            "fr": "French", "de": "German", "pt": "Portuguese", "ko": "Korean",
            "it": "Italian", "tr": "Turkish", "th": "Thai", "id": "Indonesian",
            "zh": "Chinese", "ru": "Russian", "hi": "Hindi", "ar": "Arabic"}


# ═══ HÀM THUẦN ═══════════════════════════════════════════════════════════

def _la_bieu_tuong(ch: str) -> bool:
    o = ord(ch)
    return (0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0xFE00 <= o <= 0xFE0F
            or o in (0x200D, 0x20E3) or 0x1F1E6 <= o <= 0x1F1FF)


def chuan_so_sanh(s) -> str:
    """So chữ đã đăng ↔ chữ mong đợi: NFKC, bỏ biểu tượng cảm xúc (ô gõ YouTube
    có thể đổi 🌱 thành ảnh), bỏ MỌI khoảng trắng/xuống dòng."""
    s = unicodedata.normalize("NFKC", str(s or ""))
    return "".join(ch for ch in s if not ch.isspace() and not _la_bieu_tuong(ch))


def khop_noi_dung(mong, doc) -> bool:
    """Bình luận đọc trên trang có phải đúng chữ mình đăng không. Chấp nhận trang
    cắt bớt (≥20 ký tự đầu khớp) — YouTube thu gọn bình luận dài."""
    a, b = chuan_so_sanh(mong), chuan_so_sanh(doc)
    if not a or not b:
        return False
    if a == b:
        return True
    n = min(len(a), len(b))
    return n >= 20 and (a.startswith(b) or b.startswith(a) or a[:n] == b[:n])


def rut_comment_id(hrefs) -> str:
    """Id bình luận YouTube (`Ugx…`) từ link mốc giờ `…&lc=<id>`."""
    for h in hrefs or []:
        m = re.search(r"[?&]lc=([A-Za-z0-9_.-]{10,})", str(h or ""))
        if m:
            return m.group(1)
    return ""


def id_luong(luong: dict) -> str:
    """Id bình luận gốc của một luồng: thuộc tính `comment-id` (Studio, đo 29/09)
    hoặc `&lc=` trong link mốc giờ (trang xem)."""
    return str((luong or {}).get("comment_id") or "") or rut_comment_id((luong or {}).get("hrefs"))


def khoa_binh_luan(cid: str, tac_gia: str, noi_dung: str) -> str:
    """Khoá sổ đã trả lời: id YouTube nếu đọc được, không thì băm tác giả + chữ."""
    if cid:
        return cid
    h = hashlib.sha1("{0}|{1}".format(tac_gia, chuan_so_sanh(noi_dung)).encode("utf-8")).hexdigest()
    return "h:" + h[:16]


_LINK = re.compile(r"(https?://|www\.|youtu\.be/|\bt\.me/|\bbit\.ly/|discord\.gg|"
                   r"\b[a-z0-9-]{2,}\.(com|net|org|xyz|io|me|ly|shop|site|top|info|link|jp|vn)\b)",
                   re.IGNORECASE)
_SPAM = ("sub4sub", "sub 4 sub", "check my channel", "visit my channel", "my channel",
         "subscribe to me", "đăng ký kênh mình", "ghé kênh", "sub chéo", "kênh của mình",
         "チャンネル登録お願い", "私のチャンネル", "whatsapp", "telegram", "crypto", "bitcoin",
         "forex", "nhận quà", "free gift", "giveaway", "promo code", "onlyfans", "18+")
_XUC_PHAM = ("fuck", "shit", "bitch", "idiot", "stupid", "retard", "đm", "đmm", "dmm", "địt",
             "đĩ", "ngu vãi", "óc chó", "súc vật", "cút", "死ね", "しね", "バカ", "ばか", "アホ",
             "あほ", "カス", "きもい", "キモい", "ゴミ", "くず", "クズ", "うざい")


def loai_binh_luan(noi_dung: str) -> str:
    """"" = trả lời được; khác "" = LÝ DO bỏ qua (để nguyên, không xoá):
    rong | link | spam | xuc_pham | lap_ky_tu."""
    s = unicodedata.normalize("NFKC", str(noi_dung or "")).strip()
    if not chuan_so_sanh(s):
        return "rong"
    thap = s.lower()
    if _LINK.search(s) or "@gmail" in thap:
        return "link"
    if any(w in thap for w in _SPAM):
        return "spam"
    tu = set(re.findall(r"[a-zà-ỹđ]+", thap))
    for w in _XUC_PHAM:
        if (w in tu) if re.fullmatch(r"[a-zà-ỹđ]+", w) else (w in thap):
            return "xuc_pham"
    if re.search(r"(.)\1{9,}", s):
        return "lap_ky_tu"
    return ""


def _dinh_danh_kenh(href) -> str:
    """'@ten' hoặc 'UC…' từ link kênh (tuyệt đối hay tương đối); '' nếu không có."""
    s = str(href or "")
    m = re.search(r"/(@[^/?#]+)", s) or re.search(r"/channel/(UC[A-Za-z0-9_-]{20,})", s)
    return urllib.parse.unquote(m.group(1)).lower() if m else ""


def la_cua_kenh(tac_gia_href, uc: str = "", chu_kenh_href: str = "") -> bool:
    """Bình luận này có phải CỦA CHÍNH KÊNH (không tự trả lời mình)?"""
    tg = _dinh_danh_kenh(tac_gia_href)
    if not tg:
        return False
    if uc and tg == uc.lower():
        return True
    ck = str(chu_kenh_href or "").strip()
    ck = ck.lower() if ck[:1] == "@" or ck[:2] == "UC" else _dinh_danh_kenh(ck)
    return bool(ck) and tg == ck


def ten_ngon_ngu(ma: str) -> str:
    ma = str(ma or "").strip().lower()
    return NGON_NGU.get(ma) or NGON_NGU.get(ma.split("-")[0], "")


def tao_prompt(binh_luan: str, ngon_ngu: str, giong_van: str = "", tieu_de_video: str = "",
               boi_canh: str = "") -> str:
    """Khuôn câu hỏi CÙNG `may_cmt.process_channel` (giọng người thật, không
    biểu tượng, 1–2 câu), ngôn ngữ LẤY TỪ kenh.yaml `ngon_ngu` — không suy từ đuôi -T7."""
    if ngon_ngu:
        dong_nn = ("IMPORTANT: Always reply in {0} (this channel's audience language), "
                   "no matter what language the comment is written in.\n").format(ngon_ngu)
        cuoi = "Write ONLY the reply text, in {0}.".format(ngon_ngu)
    else:
        dong_nn = ("IMPORTANT: Reply in the SAME language as the viewer's comment "
                   "(detect it and match it exactly).\n")
        cuoi = "Write ONLY the reply text, in the viewer's language."
    p = ("You are the channel owner replying to a comment on your own YouTube video.\n" + dong_nn +
         "Sound like a REAL human typing casually — natural, warm, simple and down-to-earth, "
         "the way a normal person actually replies. Often 1 short sentence is enough (max 2). "
         "STRICTLY no emojis, no icons, no hashtags, no links. "
         "Avoid any corporate or marketing tone, avoid stiff/over-formal phrasing and cliches. "
         "If the comment is hostile, stay calm and kind.\n")
    if giong_van:
        p += "Channel voice: {0}\n".format(str(giong_van).strip()[:300])
    if tieu_de_video:
        p += "\nVideo title: {0}\n".format(str(tieu_de_video).strip()[:200])
    if boi_canh:
        p += "\nVideo context (for relevance only):\n{0}\n".format(str(boi_canh).strip()[:900])
    p += "\nViewer comment: {0}\n\n{1}".format(str(binh_luan).strip()[:1500], cuoi)
    return p


def lam_sach_tra_loi(chu: str) -> str:
    """Bỏ ngoặc bao, biểu tượng, link lỡ lọt; gộp dòng; tối đa 500 ký tự."""
    s = str(chu or "").strip()
    if len(s) >= 2 and s[0] in "\"'「『“" and s[-1] in "\"'」』”":
        s = s[1:-1].strip()
    s = "".join(ch for ch in s if not _la_bieu_tuong(ch))
    s = _LINK.sub("", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s[:500].strip()


def doc_ke_hoach(chu_csv: str) -> list:
    """Kế hoạch đăng (CSV) → [dict theo tên cột]."""
    try:
        dong = list(csv.reader(io.StringIO((chu_csv or "").lstrip("﻿"))))
    except csv.Error:
        return []
    if not dong:
        return []
    cot = [str(c).strip() for c in dong[0]]
    ra = []
    for d in dong[1:]:
        if not any(str(x).strip() for x in d):
            continue
        ra.append({c: (str(d[i]).strip() if i < len(d) else "") for i, c in enumerate(cot)})
    return ra


def phan_tich_lich(ngay: str, gio: str = ""):
    """'30/09/2026' + '20:00' → datetime (giờ trống = 00:00). None nếu không đọc được."""
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(ngay or ""))
    if not m:
        m2 = re.match(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})", str(ngay or ""))
        if not m2:
            return None
        y, mo, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
    else:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hh, mm = 0, 0
    g = re.match(r"^\s*(\d{1,2}):(\d{2})", str(gio or ""))
    if g:
        hh, mm = int(g.group(1)), int(g.group(2))
    try:
        return datetime(y, mo, d, hh, mm)
    except ValueError:
        return None


def chon_goi_can_moi(hang: list, so_video: dict, so_cmt: dict, kenh: str, bay_gio: datetime,
                     cua_so_ngay: float = CUA_SO_MOI_NGAY, ma: str = None,
                     ghim_bat: bool = True) -> list:
    """Hàm THUẦN: gói của `kenh` cần bình luận mồi (và/hoặc ghim).

    Nhận: Trạng thái đăng bắt đầu "ĐÃ ĐĂNG" (kể cả "(tay)"), giờ đăng (kế hoạch,
    hoặc `lich` trong sổ videoId) đã qua và trong `cua_so_ngay` ngày gần đây; video
    chưa `da_ghim`, chưa vượt trần gửi/ghim. `ma` truyền → chỉ đúng mã đó, bỏ cửa sổ.
    `ghim_bat=False` (ghim_dom=false, 30/09/2026): video đã `da_dang_moi` là XONG —
    không mở trang xem chỉ để báo "ghim TẮT"; bật ghim lại thì được xét lại.
    Trả [{ma, tieu_de, video_id, lich}] (lich: datetime|None) theo giờ đăng cũ → mới."""
    ra = []
    for d in hang or []:
        m = d.get("Mã gói") or ""
        if not m or (ma and m != ma):
            continue
        if not str(d.get("Trạng thái đăng") or "").upper().startswith("ĐÃ ĐĂNG"):
            continue
        muc_so = (so_video or {}).get("{0}/{1}".format(kenh, m)) or {}
        vid = (d.get("Video ID") or muc_so.get("video_id") or "").strip()
        lich = None
        if muc_so.get("lich"):
            p = str(muc_so["lich"]).split()
            lich = phan_tich_lich(p[0], p[1] if len(p) > 1 else "")
        if lich is None:
            lich = phan_tich_lich(d.get("Ngày đăng"), d.get("Giờ đăng"))
        if not ma:
            if lich is None or lich > bay_gio or lich < bay_gio - timedelta(days=cua_so_ngay):
                continue
        muc = ((so_cmt or {}).get(vid) if vid else None) or {}
        if not muc:
            for k_so, v_so in (so_cmt or {}).items():
                if isinstance(v_so, dict) and v_so.get("kenh") == kenh and v_so.get("ma") == m:
                    muc, vid = v_so, vid or k_so
                    break
        if muc.get("da_ghim"):
            continue
        if not ghim_bat and muc.get("da_dang_moi"):
            continue
        if muc.get("trang_thai") in ("tat-binh-luan", "khong-co-van-ban", "ghim-khac"):
            continue
        if muc.get("trang_thai") == "cho-xac-minh" and \
                str(muc.get("ghim_cho_xac_minh") or "")[:10] == bay_gio.strftime("%Y-%m-%d"):
            continue    # kênh chưa bật tính năng nâng cao: thử ghim lại MỖI NGÀY một lần, không dồn
        if int(muc.get("lan_thu_ghim") or 0) >= TRAN_THU_GHIM:
            continue
        if (not muc.get("da_dang_moi") and int(muc.get("lan_gui") or 0) >= TRAN_GUI
                and int(muc.get("lan_kiem_lai") or 0) >= 3):
            continue
        ra.append({"ma": m, "tieu_de": d.get("Tiêu đề") or "", "video_id": vid, "lich": lich,
                   "mo_ta": d.get("Mô tả") or ""})
    ra.sort(key=lambda x: (x["lich"] or datetime.min))
    return ra


def bo_dong_can_ghim(chu: str, video_id: str):
    """Bỏ mục của `video_id` trong can-ghim.md (dòng "- […] … watch?v=<id>" và
    dòng trích "  > …" ngay sau). Trả (chữ mới, số mục đã bỏ)."""
    if not video_id:
        return chu, 0
    dong = str(chu or "").split("\n")
    ra, bo, bo_trich = [], 0, False
    for d in dong:
        if bo_trich and d.startswith("  >"):
            bo_trich = False
            continue
        bo_trich = False
        if d.lstrip().startswith("-") and video_id in d:
            bo += 1
            bo_trich = True
            continue
        ra.append(d)
    return "\n".join(ra), bo


def duong_luot(goc_tool: str, kenh: str, ma: str) -> str:
    """PROJECTS/AUTO/<k>/<nnnn> của mã gói "<k>-<nnnn>"."""
    duoi = str(ma or "").rsplit("-", 1)[-1]
    return os.path.join(goc_tool, "PROJECTS", "AUTO", kenh, duoi)


def _tieu_de_luot(thu_muc: str) -> str:
    try:
        with open(os.path.join(thu_muc, "1-tieu-de.txt"), "r", encoding="utf-8", errors="replace") as tep:
            for dong in tep:
                if dong.startswith("TITLE:"):
                    return dong[len("TITLE:"):].strip()
    except OSError:
        pass
    return ""


def _chuan_td(s) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def doc_van_ban_moi(goc_tool: str, kenh: str, ma: str, muc_so: dict = None,
                    tieu_de: str = "") -> str:
    """Chữ bình luận mồi: DONE/<k>/<mã>/1-binh-luan.txt → PROJECTS/AUTO/<k>/<nnnn>/
    1-binh-luan.txt (gói DONE bị dọn sau khi đăng) → bản sao trong sổ.

    Lượt PROJECTS có `1-tieu-de.txt` mà TITLE khác tiêu đề kế hoạch → KHÔNG dùng
    (thà bỏ còn hơn đăng nhầm bình luận của video khác)."""
    luot = duong_luot(goc_tool, kenh, ma)
    for duong, kiem_td in ((os.path.join(goc_tool, "DONE", kenh, ma, "1-binh-luan.txt"), False),
                           (os.path.join(luot, "1-binh-luan.txt"), True)):
        try:
            with open(duong, "r", encoding="utf-8", errors="replace") as tep:
                chu = tep.read().replace("\r\n", "\n").strip()
        except OSError:
            continue
        if not chu:
            continue
        if kiem_td and tieu_de:
            td = _tieu_de_luot(luot)
            if td and _chuan_td(td) != _chuan_td(tieu_de):
                log.warning("%s: 1-tieu-de.txt của lượt (%s) khác tiêu đề kế hoạch — không dùng", ma, td[:40])
                continue
        return chu
    return str((muc_so or {}).get("van_ban") or "").strip()


# ═══ SỔ ══════════════════════════════════════════════════════════════════

class SoCmt:
    """Sổ bền `vm/logs/cmt-dom.json` (khoá = videoId). Ghi nguyên tử."""

    def __init__(self, duong: str = DUONG_SO_CMT):
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


class SoDaTraLoi:
    """`vm/replied/<k>.txt` — CHUNG với may_cmt.py (id theo thứ tự cũ → mới, mỗi dòng một id)."""

    TOI_DA = 5000

    def __init__(self, kenh: str, thu_muc: str = THU_MUC_REPLIED):
        self.duong = os.path.join(thu_muc, "{0}.txt".format(kenh))

    def doc(self) -> list:
        try:
            with open(self.duong, "r", encoding="utf-8") as tep:
                return [x.strip() for x in tep if x.strip()]
        except OSError:
            return []

    def co(self, khoa: str) -> bool:
        return khoa in set(self.doc())

    def them(self, khoa: str) -> None:
        ds = self.doc()
        if khoa in ds:
            return
        ds.append(khoa)
        ds = ds[-self.TOI_DA:]
        os.makedirs(os.path.dirname(self.duong), exist_ok=True)
        tam = "{0}.{1}.tam".format(self.duong, os.getpid())
        with open(tam, "w", encoding="utf-8") as tep:
            tep.write("\n".join(ds))
        os.replace(tam, self.duong)


# ═══ JS đọc luồng bình luận (dùng window.__yd của cdp_studio) ═══════════════

_JS_LUONG = r"""
(function(specLuong, specNd, specTg, specGhim, gioiHan){
  const Y = window.__yd; if (!Y) return null;
  const roots = Y.goc(); let rows = [];
  for (const s of (specLuong.chon || [])) { try { rows = Y.qsa(roots, s).filter(Y.hien); } catch (e) {} if (rows.length) break; }
  const one = (r, spec) => { for (const s of ((spec || {}).chon || [])) { try { const x = Y.trong(r, s); if (x.length) return x[0]; } catch (e) {} } return null; };
  return rows.slice(0, gioiHan).map(r => {
    const nd = one(r, specNd), tg = one(r, specTg), gh = one(r, specGhim);
    const hrefs = Y.trong(r, 'a[href]').map(a => a.href);
    const tatCa = Y.trong(r, '#content-text').map(x => String(x.innerText || ''));
    const o = Y.tra(r, 'luong', '', 1);
    o.noi_dung = nd ? String(nd.innerText || '') : '';
    o.tac_gia = tg ? Y.chuan(tg.innerText) : '';
    let a = tg ? (tg.closest ? tg.closest('a') : null) : null;
    if (!a && tg && tg.querySelector) a = tg.querySelector('a');
    o.tac_gia_href = tg ? String(tg.href || (a && a.href) || '') : '';
    o.ghim = !!(gh && Y.hien(gh));
    const cidEl = Y.trong(r, '[comment-id]')[0];
    o.comment_id = cidEl ? String(cidEl.getAttribute('comment-id') || '') : '';
    o.la_chu = !!(Y.trong(r, '.channel-owner, ytcp-author-comment-badge[is-creator]').length &&
                  Y.trong(r, '.channel-owner, ytcp-author-comment-badge[is-creator]')[0] === Y.trong(r, '.channel-owner, ytcp-author-comment-badge[is-creator], #content-text')[0]);
    o.hrefs = hrefs.slice(0, 16);
    o.cac_noi_dung = tatCa.slice(0, 30);
    o.chu_tho = String(r.innerText || '').slice(0, 600);
    return o;
  });
})
"""


class LoiMay(Exception):
    """Một bước của máy bình luận hỏng (kèm `truoc`: True nếu CHƯA chạm kênh)."""

    def __init__(self, ly_do: str, truoc: bool = False):
        super().__init__(ly_do)
        self.truoc = truoc


# ═══ MÁY ═════════════════════════════════════════════════════════════════

class MayCmtDom:
    """Luồng bình luận một kênh. `tao_trang()` trả một `cdp_studio.TrangStudio`
    (hoặc trang giả trong test — cùng giao diện)."""

    def __init__(self, kenh: str, bo_chon: dict, tao_trang, so: SoCmt, nhat_ky=None,
                 ngu=None, rng=None, sinh_tra_loi=None, so_tra_loi: SoDaTraLoi = None,
                 cai: dict = None, goc_tool: str = GOC_TOOL, tra_kenh=None, lay_uc=None):
        self.kenh = kenh
        self.bo = bo_chon
        self.tao_trang = tao_trang
        self.so = so
        self.nk = nhat_ky or log.info
        self.ngu = ngu or time.sleep
        self.rng = rng or random.Random()
        self.sinh_tra_loi = sinh_tra_loi or sinh_tra_loi_mac_dinh
        self.so_tl = so_tra_loi or SoDaTraLoi(kenh)
        self.cai = cai or {}
        self.goc_tool = goc_tool
        self._tra_kenh = tra_kenh          # seam: tieu_de, vid -> [{video_id, loai, tieu_de}]
        self._lay_uc = lay_uc              # seam: () -> uc
        self.uc = ""
        self.tab = []
        self.handle = ""
        self.cham_kenh = False             # đã gõ/đăng gì lên kênh chưa (quyết mã thoát 1/3)
        self.bao_cao = {"kenh": kenh, "moi": [], "tra_loi": [], "bo_qua": [], "loi": [], "anh": []}

    # ── tiện ích ─────────────────────────────────────────────────────────
    def _url(self, ten: str, **kw) -> str:
        return str((self.bo.get("url") or {})[ten]).format(uc=self.uc, **kw)

    def _tab(self):
        t = self.tao_trang()
        self.tab.append(t)
        return t

    def dong_het(self) -> None:
        for t in self.tab:
            try:
                t.dong()
            except Exception:  # noqa: BLE001
                pass
        self.tab = []

    def _chup(self, tr, nhan: str) -> str:
        try:
            duong = tr.chup(nhan)
        except Exception:  # noqa: BLE001
            duong = ""
        if duong:
            self.bao_cao["anh"].append(duong)
            self.nk("ảnh bằng chứng: {0}".format(duong))
        return duong

    def _bang_chung(self, tr, nhan: str) -> None:
        try:
            bc = tr.ghi_bang_chung(nhan)
            if bc.get("anh"):
                self.bao_cao["anh"].append(bc["anh"])
            self.nk("bằng chứng lỗi: {0}".format(bc))
        except Exception:  # noqa: BLE001
            pass

    def _gian(self, a: float, b: float) -> None:
        self.ngu(self.rng.uniform(a, b))

    def lay_uc(self) -> str:
        if not self.uc:
            self.uc = self._lay_uc() if self._lay_uc else ""
        return self.uc

    def doc_luong(self, tr, tien_to: str, gioi_han: int = 40) -> list:
        pt = self.bo.get("phan_tu") or {}
        bt = "(" + _JS_LUONG.strip() + ")({0},{1},{2},{3},{4})".format(
            json.dumps(pt.get(tien_to + "_luong") or {}, ensure_ascii=False),
            json.dumps(pt.get(tien_to + "_noi_dung") or {}, ensure_ascii=False),
            json.dumps(pt.get(tien_to + "_tac_gia") or {}, ensure_ascii=False),
            json.dumps(pt.get("xem_huy_hieu_ghim") or {}, ensure_ascii=False),
            int(gioi_han))
        try:
            ra = tr.js_tho(bt)
            if ra is None:          # thế giới riêng vừa dựng lại, chưa cài __yd
                self._dam_bao_yd(tr)
                ra = tr.js_tho(bt)
            return ra or []
        except Exception as loi:  # noqa: BLE001
            self.nk("đọc luồng bình luận lỗi: {0}".format(str(loi)[:120]))
            return []

    def _dam_bao_yd(self, tr) -> None:
        """Cài `window.__yd` vào thế giới riêng trước khi chạy JS đọc luồng."""
        try:
            tr.co("xem_luong")
        except Exception:  # noqa: BLE001
            pass

    def go_nhieu_dong(self, tr, khoa: str, chu: str, trong: dict = None) -> str:
        """Bấm ô → Ctrl+A → chèn từng dòng, xuống dòng bằng SHIFT+Enter (Enter
        trơn ở vài ô bình luận có thể GỬI luôn) → ĐỌC LẠI. Lệch 2 lần → xoá ô, LoiMay."""
        import cdp_studio  # noqa: PLC0415
        doc = ""
        for lan in range(2):
            pt = tr.tim(khoa, han=10, trong=trong)
            if not pt:
                raise LoiMay("không thấy ô gõ {0}".format(khoa))
            tr.bam(pt)
            tr._ctrl_a()
            tr.phim("Delete")
            dong = str(chu).replace("\r\n", "\n").split("\n")
            for i, d in enumerate(dong):
                if i:
                    tr.phim("Enter", modifiers=8)
                if d:
                    tr.cdp.goi("Input.insertText", {"text": d}, sid=tr.sid, han=30)
                    self._gian(0.05, 0.2)
            self._gian(0.4, 0.9)
            doc = tr.doc_chu(pt) or ""
            if khop_noi_dung(chu, doc) and len(chuan_so_sanh(doc)) >= len(chuan_so_sanh(chu)) - 2:
                return doc
            self.nk("gõ {0}: đọc lại LỆCH (lần {1}): {2!r}".format(
                khoa, lan + 1, cdp_studio.chuan_chu(doc)[:80]))
        try:
            tr._ctrl_a()
            tr.phim("Delete")
        except Exception:  # noqa: BLE001
            pass
        raise LoiMay("đọc lại ô {0} lệch sau 2 lần gõ — KHÔNG gửi".format(khoa))

    # ── trang xem ────────────────────────────────────────────────────────
    def mo_trang_xem(self, tr, vid: str) -> str:
        """Mở trang xem, dừng phát, cuộn tới khung bình luận. Trả "ok" | "tat"."""
        tr.mo(self._url("xem", id=vid), han=60)
        self._gian(2.5, 4.0)
        try:
            tr.js_tho("(function(){const v=document.querySelector('video'); if(v){v.muted=true; v.pause();} return true;})()")
        except Exception:  # noqa: BLE001
            pass
        het = time.monotonic() + 45
        while time.monotonic() < het:
            if tr.co("xem_o_mo") or tr.co("xem_o_go"):
                return "ok"
            if tr.co("xem_bl_tat") and not tr.co("xem_bl_khung"):
                return "tat"
            try:
                tr.js_tho("window.scrollBy(0, {0})".format(int(self.rng.uniform(450, 750))))
            except Exception:  # noqa: BLE001
                pass
            self._gian(1.0, 1.8)
        if tr.co("xem_bl_tat"):
            return "tat"
        raise LoiMay("trang xem {0}: không thấy khung bình luận sau 45s".format(vid), truoc=True)

    def _chu_kenh_href(self, tr) -> str:
        try:
            pt = tr.tim("xem_chu_kenh", han=3)
            return str(tr.doc_thuoc_tinh(pt, "href") or "") if pt else ""
        except Exception:  # noqa: BLE001
            return ""

    def _la_cua_kenh(self, luong: dict) -> bool:
        """Của chính kênh: huy hiệu chủ kênh ở bình luận GỐC (`.channel-owner` /
        `is-creator` — Studio) hoặc link tác giả trùng UC/handle đã học."""
        return bool(luong.get("la_chu")) or la_cua_kenh(luong.get("tac_gia_href"), self.uc, self.handle)

    def _tim_cua_minh(self, luong: list, van_ban: str):
        for x in luong:
            if khop_noi_dung(van_ban, x.get("noi_dung")):
                self._hoc_handle(x)
                return x
        return None

    def _hoc_handle(self, luong_cua_minh: dict) -> None:
        """Handle (@tên) của CHÍNH kênh = tác giả bình luận mồi mình vừa đăng. Không
        lấy từ khối chủ video: video cộng tác hiện HAI kênh (đo 29/09, TL1-T7-0005)."""
        h = _dinh_danh_kenh(luong_cua_minh.get("tac_gia_href"))
        if h and h.startswith("@") and h != self.handle:
            self.handle = h
            try:
                self.so.cap_nhat("_kenh:" + self.kenh, handle=h)
            except OSError:
                pass

    def _nap_handle(self) -> None:
        if not self.handle:
            self.handle = str(self.so.lay("_kenh:" + self.kenh).get("handle") or "")

    def dang_va_ghim(self, goi: dict) -> str:
        """Bình luận mồi + ghim cho MỘT gói. Trả chữ kết quả ngắn (ghi báo cáo)."""
        ma = goi["ma"]
        vid = goi.get("video_id") or ""
        if not vid or goi.get("can_kiem_cong_khai", True):
            ds = self._tra_kenh(goi.get("tieu_de") or "", vid) if self._tra_kenh else []
            import may_dang_dom as mdd  # noqa: PLC0415
            khop = [x for x in ds if (vid and x.get("video_id") == vid) or
                    (not vid and mdd.chuan_hoa_tieu_de(x.get("tieu_de")) ==
                     mdd.chuan_hoa_tieu_de(goi.get("tieu_de")))]
            if not khop:
                return "chưa thấy video trên kênh (khớp tiêu đề) — lượt sau"
            x = khop[0]
            vid = vid or x.get("video_id") or ""
            if x.get("loai") != "cong_khai":
                return "video {0} chưa công khai ({1}) — lượt sau".format(vid, x.get("loai"))
        if not vid:
            return "không đọc được videoId — lượt sau"
        muc = self.so.lay(vid)
        if muc.get("da_ghim"):
            self.so.cap_nhat(vid, kenh=self.kenh, ma=ma)
            return "video {0} đã ghim từ {1} — bỏ".format(vid, muc["da_ghim"])
        van_ban = doc_van_ban_moi(self.goc_tool, self.kenh, ma, muc, tieu_de=goi.get("tieu_de") or "")
        if not van_ban:
            self.so.cap_nhat(vid, kenh=self.kenh, ma=ma, trang_thai="khong-co-van-ban")
            return "không có 1-binh-luan.txt — bỏ"
        self.so.cap_nhat(vid, kenh=self.kenh, ma=ma, tieu_de=goi.get("tieu_de") or "",
                         van_ban=van_ban)
        tr = self._tab()
        try:
            return self._dang_va_ghim_tren_trang(tr, vid, ma, van_ban)
        except LoiMay:
            self._bang_chung(tr, "cmt-loi-" + vid)
            raise
        except Exception as loi:  # noqa: BLE001
            self._bang_chung(tr, "cmt-loi-" + vid)
            raise LoiMay("{0}: {1}".format(type(loi).__name__, str(loi)[:160]))
        finally:
            try:
                tr.dong()
            finally:
                if tr in self.tab:
                    self.tab.remove(tr)

    def _dang_va_ghim_tren_trang(self, tr, vid: str, ma: str, van_ban: str) -> str:
        tt = self.mo_trang_xem(tr, vid)
        if tt == "tat":
            self.so.cap_nhat(vid, trang_thai="tat-binh-luan")
            return "video {0} TẮT bình luận — bỏ".format(vid)
        self._dam_bao_yd(tr)
        self._nap_handle()
        luong = self.doc_luong(tr, "xem")
        cua_minh = self._tim_cua_minh(luong, van_ban)
        ghim_khac = next((x for x in luong if x.get("ghim") and x is not cua_minh), None)
        muc = self.so.lay(vid)
        if cua_minh is None and muc.get("trang_thai") == "dang-gui":
            # Lượt trước chết giữa lúc gửi: tải lại một lần cho chắc trước khi gửi lại.
            self.mo_trang_xem(tr, vid)
            self._gian(2.0, 3.0)
            luong = self.doc_luong(tr, "xem")
            cua_minh = self._tim_cua_minh(luong, van_ban)
        if cua_minh is None:
            if ghim_khac is not None:
                self.so.cap_nhat(vid, trang_thai="ghim-khac", da_ghim="")
                return "video {0} đã có bình luận GHIM khác — không đăng mồi, không đổi ghim".format(vid)
            if int(muc.get("lan_gui") or 0) >= TRAN_GUI:
                self.so.cap_nhat(vid, lan_kiem_lai=int(muc.get("lan_kiem_lai") or 0) + 1)
                self.nk("CẢNH BÁO {0}: đã gửi bình luận mồi mà vẫn không đọc thấy — KHÔNG gửi lại, "
                        "cần người xem https://www.youtube.com/watch?v={0}".format(vid))
                return "đã gửi {0} lần mà không đọc thấy — không gửi lại (cần người xem)".format(TRAN_GUI)
            cua_minh = self._gui_moi(tr, vid, van_ban)
            ket = "đã đăng mồi"
        else:
            ket = "bình luận mồi đã có sẵn"
            if not muc.get("da_dang_moi"):
                self.so.cap_nhat(vid, da_dang_moi=time.strftime("%Y-%m-%d %H:%M:%S"),
                                 comment_id=id_luong(cua_minh),
                                 trang_thai="da-dang")
        if not self.cai.get("ghim_dom", True):
            self.so.cap_nhat(vid, ghim="tat", trang_thai="da-dang")
            return "{0}; ghim TẮT (ghim_dom=false) — bỏ qua bước ghim".format(ket)
        if cua_minh.get("ghim"):
            self._xong_ghim(vid, cua_minh)
            return "{0}; ĐÃ GHIM (sẵn) — https://www.youtube.com/watch?v={1}".format(ket, vid)
        if ghim_khac is not None:
            self.so.cap_nhat(vid, trang_thai="ghim-khac")
            return "{0}; video đã có bình luận ghim KHÁC — không đổi ghim".format(ket)
        hom_nay = time.strftime("%Y-%m-%d")
        if str(self.so.lay("_kenh:" + self.kenh).get("can_xac_minh") or "")[:10] == hom_nay:
            # Hôm nay đã biết kênh bị chặn ghim — không mở lại hộp xác minh cho từng video.
            self.so.cap_nhat(vid, trang_thai="cho-xac-minh", ghim_cho_xac_minh=time.strftime("%Y-%m-%d %H:%M:%S"))
            self._ghi_can_ghim(vid, van_ban, xac_minh=True)
            self.bao_cao.setdefault("can_xac_minh", True)
            return "{0}; chưa ghim — kênh cần bật 'tính năng nâng cao' (đã biết hôm nay)".format(ket)
        if self._ghim(tr, vid, van_ban, cua_minh) == "cho-xac-minh":
            self.bao_cao.setdefault("can_xac_minh", True)
            return ("{0}; CHƯA GHIM ĐƯỢC — kênh cần bật 'tính năng nâng cao' (https://www.youtube.com/verify)"
                    " — https://www.youtube.com/watch?v={1}".format(ket, vid))
        return "{0}; ĐÃ GHIM — https://www.youtube.com/watch?v={1}".format(ket, vid)

    def _gui_moi(self, tr, vid: str, van_ban: str) -> dict:
        muc = self.so.lay(vid)
        tr.bam("xem_o_mo", hau_dieu_kien=lambda: tr.co("xem_o_go"), han_hau=10)
        self.cham_kenh = True
        self.go_nhieu_dong(tr, "xem_o_go", van_ban)
        pt_gui = tr.tim("xem_gui", han=8)
        if not pt_gui:
            raise LoiMay("nút Bình luận không bật sau khi gõ")
        self.so.cap_nhat(vid, trang_thai="dang-gui", lan_gui=int(muc.get("lan_gui") or 0) + 1,
                         gui_luc=time.strftime("%Y-%m-%d %H:%M:%S"))
        tr.bam(pt_gui)
        het = time.monotonic() + 25
        cua_minh = None
        while time.monotonic() < het:
            self._gian(1.0, 1.6)
            cua_minh = self._tim_cua_minh(self.doc_luong(tr, "xem"), van_ban)
            if cua_minh is not None:
                break
        if cua_minh is None:
            raise LoiMay("đã bấm Bình luận nhưng 25s không thấy bình luận hiện — lượt sau kiểm lại")
        cid = id_luong(cua_minh)
        self.so.cap_nhat(vid, da_dang_moi=time.strftime("%Y-%m-%d %H:%M:%S"), comment_id=cid,
                         trang_thai="da-dang")
        self.nk("{0}: đã đăng bình luận mồi (id {1})".format(vid, cid or "?"))
        self._chup(tr, "cmt-moi-" + vid)
        self.bao_cao["moi"].append({"video_id": vid, "comment_id": cid})
        return cua_minh

    def _ghim(self, tr, vid: str, van_ban: str, cua_minh: dict) -> str:
        """Ghim bình luận mồi. Trả "da-ghim" | "cho-xac-minh" (kênh chưa bật
        tính năng nâng cao — YouTube bắt chủ kênh xác minh MỘT LẦN bằng điện thoại,
        tool không làm thay được). Hỏng khác → LoiMay."""
        muc = self.so.lay(vid)
        self.so.cap_nhat(vid, lan_thu_ghim=int(muc.get("lan_thu_ghim") or 0) + 1)
        # Menu ⋮ chỉ hiện khi rê chuột lên bình luận.
        try:
            cu = tr._js("cuon", cua_minh["id"]) or {}
            r = cu.get("rect") or cua_minh.get("rect")
            if r:
                tr._chuot_toi(r["x"] + r["w"] * 0.6, r["y"] + min(r["h"] / 2.0, 30))
        except Exception:  # noqa: BLE001
            pass
        self._gian(0.6, 1.2)
        pt_menu = tr.tim("xem_menu", han=5, trong=cua_minh) or tr.tim("xem_menu", han=2, hien=False,
                                                                       trong=cua_minh)
        if not pt_menu:
            raise LoiMay("không thấy nút ⋮ của bình luận mồi")
        self.cham_kenh = True
        tr.bam(pt_menu, hau_dieu_kien=lambda: tr.co("xem_menu_ghim"), han_hau=8)
        tr.bam("xem_menu_ghim", hau_dieu_kien=lambda: tr.co("xem_xac_nhan_ghim") or tr.co("xem_hop_xac_minh"),
               han_hau=10)
        hop_xm = tr.tim("xem_hop_xac_minh", han=1)
        if hop_xm:
            self._chup(tr, "cmt-ghim-can-xac-minh-" + vid)
            pt_huy = tr.tim("xem_hop_xac_minh_huy", han=3, trong=hop_xm)
            if pt_huy:
                tr.bam(pt_huy)
            else:
                tr.phim("Escape")
            # Không tính vào trần thử ghim: đây là việc của chủ kênh, không phải lỗi bấm.
            self.so.cap_nhat(vid, trang_thai="cho-xac-minh", lan_thu_ghim=int(muc.get("lan_thu_ghim") or 0),
                             ghim_cho_xac_minh=time.strftime("%Y-%m-%d %H:%M:%S"))
            self.so.cap_nhat("_kenh:" + self.kenh, can_xac_minh=time.strftime("%Y-%m-%d %H:%M:%S"))
            self._ghi_can_ghim(vid, van_ban, xac_minh=True)
            self.nk("CẢNH BÁO {0}: YouTube CHẶN GHIM — kênh {1} chưa bật 'tính năng nâng cao'. Chủ kênh "
                    "xác minh MỘT LẦN tại https://www.youtube.com/verify (điện thoại), tool tự ghim lượt sau."
                    .format(vid, self.kenh))
            return "cho-xac-minh"
        pt_xn = tr.tim("xem_xac_nhan_ghim", han=5)
        chu_xn = unicodedata.normalize("NFKC", str(tr.doc_chu(pt_xn) or "")).strip() if pt_xn else ""
        if not pt_xn or chu_xn not in ("Ghim", "Pin", "固定"):
            tr.phim("Escape")
            raise LoiMay("hộp xác nhận ghim lạ (nút «{0}») — không bấm".format(chu_xn[:30]))
        tr.bam(pt_xn)
        het = time.monotonic() + 20
        da = False
        while time.monotonic() < het:
            self._gian(1.0, 1.6)
            x = self._tim_cua_minh(self.doc_luong(tr, "xem"), van_ban)
            if x and x.get("ghim"):
                da = True
                break
        # Đọc lại sau khi tải lại trang — ghim thật phải còn sau F5.
        self.mo_trang_xem(tr, vid)
        self._dam_bao_yd(tr)
        het = time.monotonic() + 15
        x = None
        while time.monotonic() < het:
            x = self._tim_cua_minh(self.doc_luong(tr, "xem"), van_ban)
            if x and x.get("ghim"):
                break
            self._gian(1.0, 1.6)
        if not (x and x.get("ghim")):
            raise LoiMay("đã bấm Ghim{0} nhưng tải lại KHÔNG thấy huy hiệu ghim".format(
                " (trước F5 có)" if da else ""))
        self._chup(tr, "cmt-ghim-" + vid)
        self._xong_ghim(vid, x)
        return "da-ghim"

    def _ghi_can_ghim(self, vid: str, van_ban: str, xac_minh: bool = False) -> None:
        """Ghi (một lần) mục của video vào CHANNEL/<k>/can-ghim.md khi tool CHƯA ghim được."""
        thu_muc = os.path.join(self.goc_tool, "CHANNEL", self.kenh)
        if not os.path.isdir(thu_muc):
            return
        duong = os.path.join(thu_muc, "can-ghim.md")
        try:
            with open(duong, "r", encoding="utf-8") as tep:
                cu = tep.read()
        except OSError:
            cu = ""
        if vid in cu:
            return
        dau = "" if cu.strip() else (
            "# Việc tay còn lại: GHIM bình luận mở đầu\n\n"
            "Tool đã tự ĐĂNG bình luận mở đầu. Mục nào còn ở đây là tool CHƯA ghim được — "
            "mở link, bấm ⋮ ở bình luận của kênh → **Ghim**. Tool ghim được thì tự xoá mục.\n\n")
        if xac_minh and "youtube.com/verify" not in cu:
            dau += ("> **YouTube chặn ghim cho tới khi kênh bật 'tính năng nâng cao'** — chủ kênh xác minh "
                    "MỘT LẦN tại https://www.youtube.com/verify (bằng điện thoại). Xong là tool tự ghim các "
                    "mục dưới ở lượt sau.\n\n")
        dong_dau = (str(van_ban or "").splitlines() or [""])[0][:120]
        moi = "{0}- [{1}] **{2}** — https://www.youtube.com/watch?v={3}\n  > {4}\n".format(
            dau, time.strftime("%Y-%m-%d %H:%M"), (self.so.lay(vid).get("tieu_de") or vid)[:100], vid, dong_dau)
        tam = duong + ".tam"
        with open(tam, "w", encoding="utf-8") as tep:
            tep.write(cu + moi)
        os.replace(tam, duong)

    def _xong_ghim(self, vid: str, luong: dict) -> None:
        self.so.cap_nhat(vid, da_ghim=time.strftime("%Y-%m-%d %H:%M:%S"), trang_thai="da-ghim",
                         comment_id=id_luong(luong) or self.so.lay(vid).get("comment_id", ""))
        self.nk("{0}: bình luận mồi ĐÃ GHIM".format(vid))
        self.bao_cao["moi"].append({"video_id": vid, "ghim": True})
        duong = os.path.join(self.goc_tool, "CHANNEL", self.kenh, "can-ghim.md")
        try:
            with open(duong, "r", encoding="utf-8") as tep:
                cu = tep.read()
        except OSError:
            return
        moi, bo = bo_dong_can_ghim(cu, vid)
        if bo:
            tam = duong + ".tam"
            with open(tam, "w", encoding="utf-8") as tep:
                tep.write(moi)
            os.replace(tam, duong)
            self.nk("can-ghim.md: đã bỏ {0} mục của {1} (không còn việc tay)".format(bo, vid))

    # ── trả lời ──────────────────────────────────────────────────────────
    def _boi_canh(self, luong: dict) -> tuple:
        """(tiêu đề, bối cảnh) của video mà bình luận thuộc về — từ kế hoạch theo Video ID."""
        import may_dang_dom as mdd  # noqa: PLC0415
        vid = ""
        for h in luong.get("hrefs") or []:
            vid = mdd.rut_video_id(h)
            if vid:
                break
        for d in self.cai.get("_ke_hoach") or []:
            if vid and d.get("Video ID") == vid:
                return d.get("Tiêu đề") or "", d.get("Mô tả") or ""
        muc = self.so.lay(vid) if vid else {}
        return muc.get("tieu_de") or "", ""

    def tra_loi(self, toi_da: int) -> dict:
        kq = {"da_tra_loi": 0, "bo_qua": 0, "loi": 0}
        if toi_da <= 0:
            return kq
        tr = self._tab()
        try:
            return self._tra_loi_tren_trang(tr, toi_da, kq)
        except LoiMay:
            self._bang_chung(tr, "cmt-tra-loi-loi")
            raise
        except Exception as loi:  # noqa: BLE001
            self._bang_chung(tr, "cmt-tra-loi-loi")
            raise LoiMay("{0}: {1}".format(type(loi).__name__, str(loi)[:160]), truoc=not self.cham_kenh)
        finally:
            try:
                tr.dong()
            finally:
                if tr in self.tab:
                    self.tab.remove(tr)

    def _tra_loi_tren_trang(self, tr, toi_da: int, kq: dict) -> dict:
        self.lay_uc()
        self._nap_handle()
        tr.mo(self._url("cmt_chua_phan_hoi"), han=60)
        het = time.monotonic() + 40
        while time.monotonic() < het:
            if tr.co("sc_luong") or tr.co("sc_trong"):
                break
            self._gian(1.0, 1.6)
        else:
            raise LoiMay("trang Bình luận của Studio không hiện luồng nào lẫn chữ 'không có'", truoc=True)
        self._gian(1.5, 2.5)
        self._dam_bao_yd(tr)
        da_xet = set()
        ngon_ngu = ten_ngon_ngu(self.cai.get("ngon_ngu"))
        for _vong in range(6):
            luong = self.doc_luong(tr, "sc", gioi_han=60)
            moi = [x for x in luong if x.get("id") and
                   khoa_binh_luan(id_luong(x), x.get("tac_gia"), x.get("noi_dung")) not in da_xet]
            if not moi:
                break
            for x in moi:
                if kq["da_tra_loi"] >= toi_da:
                    return kq
                cid = id_luong(x)
                khoa = khoa_binh_luan(cid, x.get("tac_gia"), x.get("noi_dung"))
                da_xet.add(khoa)
                if self.so_tl.co(khoa):
                    continue
                if self._la_cua_kenh(x) or any(khop_noi_dung(m.get("van_ban"), x.get("noi_dung"))
                                              for m in self.so.doc().values()
                                              if isinstance(m, dict) and m.get("van_ban")):
                    self.so_tl.them(khoa)
                    continue
                ly_do = loai_binh_luan(x.get("noi_dung"))
                if ly_do:
                    kq["bo_qua"] += 1
                    self.so_tl.them(khoa)
                    self.bao_cao["bo_qua"].append({"id": khoa, "ly_do": ly_do,
                                                   "chu": str(x.get("noi_dung") or "")[:80]})
                    self.nk("bỏ qua bình luận {0} ({1}) — để nguyên".format(khoa, ly_do))
                    continue
                tieu_de, boi_canh = self._boi_canh(x)
                cau = lam_sach_tra_loi(self.sinh_tra_loi(tao_prompt(
                    x.get("noi_dung"), ngon_ngu, self.cai.get("giong_van") or "", tieu_de, boi_canh)) or "")
                if not cau:
                    kq["loi"] += 1
                    self.nk("không sinh được câu trả lời cho {0} — lượt sau".format(khoa))
                    continue
                if kq["da_tra_loi"]:
                    self._gian(float(self.cai.get("gian_min") or GIAN_MIN),
                               float(self.cai.get("gian_max") or GIAN_MAX))
                try:
                    self._gui_tra_loi(tr, x, khoa, cau)
                    kq["da_tra_loi"] += 1
                except LoiMay as loi:
                    kq["loi"] += 1
                    self.bao_cao["loi"].append("trả lời {0}: {1}".format(khoa, loi))
                    self.nk("trả lời {0} hỏng: {1}".format(khoa, loi))
                    self._bang_chung(tr, "cmt-tra-loi-" + re.sub(r"[^A-Za-z0-9]", "", khoa)[:20])
                    try:
                        pt = tr.tim("sc_huy_tra_loi", han=2, trong=x)
                        if pt:
                            tr.bam(pt)
                    except Exception:  # noqa: BLE001
                        pass
                    if kq["loi"] >= 3:
                        raise LoiMay("3 lần trả lời hỏng liên tiếp — dừng lượt")
        return kq

    def _gui_tra_loi(self, tr, luong: dict, khoa: str, cau: str) -> None:
        pt = tr.tim("sc_nut_tra_loi", han=5, trong=luong)
        if not pt:
            raise LoiMay("không thấy nút Phản hồi trong luồng")
        tr.bam(pt, hau_dieu_kien=lambda: tr.co("sc_o_tra_loi", trong=luong), han_hau=10)
        self.cham_kenh = True
        self.go_nhieu_dong(tr, "sc_o_tra_loi", cau, trong=luong)
        pt_gui = tr.tim("sc_gui_tra_loi", han=8, trong=luong)
        if not pt_gui:
            raise LoiMay("nút gửi trả lời không bật")
        # Ghi sổ TRƯỚC khi bấm: chết giữa chừng thì thà sót một trả lời còn hơn trả lời đôi.
        self.so_tl.them(khoa)
        tr.bam(pt_gui)
        het = time.monotonic() + 25
        o_dong = False
        while time.monotonic() < het:
            self._gian(1.0, 1.6)
            for x in self.doc_luong(tr, "sc", gioi_han=80):
                if x.get("id") == luong.get("id") or khop_noi_dung(luong.get("noi_dung"), x.get("noi_dung")):
                    if any(khop_noi_dung(cau, c) for c in (x.get("cac_noi_dung") or [])[1:]):
                        self._xong_tra_loi(khoa, cau, luong, "đọc lại thấy trong luồng")
                        return
            o_dong = not tr.co("sc_o_tra_loi", trong=luong)
        if o_dong:
            # Ô trả lời đã tự đóng (Studio nhận) nhưng luồng thu gọn phản hồi — coi là đã gửi.
            self._xong_tra_loi(khoa, cau, luong, "ô đã đóng, luồng không hiện phản hồi")
            return
        self._chup(tr, "cmt-tra-loi-chua-thay")
        raise LoiMay("đã bấm gửi trả lời nhưng 25s không đọc thấy trả lời (đã ghi sổ, không gửi lại)")

    def _xong_tra_loi(self, khoa: str, cau: str, luong: dict, cach: str) -> None:
        self.nk("đã trả lời {0} ({1}): {2}".format(khoa, cach, cau[:80]))
        self.bao_cao["tra_loi"].append({"id": khoa, "chu": cau[:200], "cach": cach,
                                        "binh_luan": str(luong.get("noi_dung") or "")[:120]})
        try:
            import stats  # noqa: PLC0415
            stats.bump(self.kenh, "reply")
        except Exception:  # noqa: BLE001
            pass

    # ── kiểm DOM (CHỈ ĐỌC) ───────────────────────────────────────────────
    def kiem_dom(self, vid: str = "", mo_hop: bool = False) -> dict:
        kq = {"ngay": time.strftime("%Y-%m-%d %H:%M:%S"), "kenh": self.kenh, "hong": [], "co": [],
              "du_phong": {}, "ghi_chu": []}
        tr = self._tab()

        def kiem(khoa, **kw):
            pt = tr.tim(khoa, han=kw.pop("han", 6), **kw)
            (kq["co"] if pt else kq["hong"]).append(khoa)
            if pt and pt.get("cach") != "chon#1" and ((self.bo.get("phan_tu") or {}).get(khoa) or {}).get("chon"):
                kq["du_phong"][khoa] = pt.get("cach")     # khoá CHỈ-chữ (xem_menu_ghim) không tính dự phòng
            return pt
        try:
            self.lay_uc()
            kq["uc"] = self.uc
            tr.mo(self._url("cmt_chua_phan_hoi"), han=60)
            het = time.monotonic() + 40
            while time.monotonic() < het and not (tr.co("sc_luong") or tr.co("sc_trong")):
                self._gian(1.0, 1.6)
            kiem("sc_khung")
            self._dam_bao_yd(tr)
            luong = self.doc_luong(tr, "sc")
            kq["studio_chua_phan_hoi"] = len(luong)
            if luong:
                x = luong[0]
                kq["studio_luong_dau"] = {k: x.get(k) for k in ("tac_gia", "tac_gia_href", "noi_dung", "hrefs")}
                kiem("sc_nut_tra_loi", trong=x)
            elif tr.co("sc_trong"):
                kq["ghi_chu"].append("Studio: không có bình luận chưa phản hồi")
            tr.ghi_bang_chung("kiem-cmt-studio")
            if vid:
                tr.mo(self._url("cmt_video", id=vid), han=60)
                het = time.monotonic() + 30
                while time.monotonic() < het and not (tr.co("sc_luong") or tr.co("sc_trong")):
                    self._gian(1.0, 1.6)
                self._dam_bao_yd(tr)
                lv = self.doc_luong(tr, "sc")
                if not lv and tr.co("sc_bo_loc_phan_hoi"):
                    # Bộ lọc mặc định "Chưa phản hồi" giấu bình luận của chính kênh — bỏ lọc để đo luồng.
                    tr.bam("sc_bo_loc_phan_hoi")
                    het = time.monotonic() + 20
                    while time.monotonic() < het and not tr.co("sc_luong"):
                        self._gian(1.0, 1.6)
                    lv = self.doc_luong(tr, "sc")
                try:
                    html = tr.js_tho("(function(){const e=document.querySelector('ytcp-comments-section "
                                     "ytd-comment-thread-renderer, ytcp-comments-section ytcp-comment-thread, "
                                     "ytcp-comments-section #contents'); return e ? e.outerHTML : '';})()") or ""
                    if html:
                        os.makedirs(cdp_studio_thu_muc(), exist_ok=True)
                        with open(os.path.join(cdp_studio_thu_muc(), "kiem-cmt-studio-luong.html"), "w",
                                  encoding="utf-8") as tep:
                            tep.write(html[:400000])
                except Exception:  # noqa: BLE001
                    pass
                kq["studio_video_luong"] = [{k: x.get(k) for k in ("tac_gia", "tac_gia_href", "noi_dung", "hrefs", "ghim")}
                                            for x in lv[:5]]
                if lv:
                    pt = kiem("sc_nut_tra_loi", trong=lv[0])
                    if pt and mo_hop:
                        tr.bam(pt, hau_dieu_kien=lambda: tr.co("sc_o_tra_loi", trong=lv[0]), han_hau=8)
                        kiem("sc_o_tra_loi", trong=lv[0])
                        kiem("sc_gui_tra_loi", trong=lv[0], cho_tat=True)
                        tr.ghi_bang_chung("kiem-cmt-studio-hop")
                        pt_h = kiem("sc_huy_tra_loi", trong=lv[0])
                        if pt_h:
                            tr.bam(pt_h)
                tr.ghi_bang_chung("kiem-cmt-studio-video")
                tt = self.mo_trang_xem(tr, vid)
                kq["xem"] = tt
                if tt == "ok":
                    self._dam_bao_yd(tr)
                    kiem("xem_o_mo")
                    self._nap_handle()
                    kq["handle"] = self.handle
                    kq["chu_video"] = self._chu_kenh_href(tr)
                    lx = self.doc_luong(tr, "xem")
                    if self.so.lay(vid).get("van_ban"):
                        self._tim_cua_minh(lx, self.so.lay(vid)["van_ban"])
                        kq["handle"] = self.handle
                    kq["xem_luong"] = [{k: x.get(k) for k in ("tac_gia", "tac_gia_href", "noi_dung", "ghim", "hrefs")}
                                       for x in lx[:5]]
                    tr.bam("xem_o_mo", hau_dieu_kien=lambda: tr.co("xem_o_go"), han_hau=8)
                    kiem("xem_o_go")
                    kiem("xem_gui", cho_tat=True)
                    pt_h = kiem("xem_huy")
                    tr.ghi_bang_chung("kiem-cmt-xem")
                    if pt_h:
                        tr.bam(pt_h)
                    if lx:
                        x = lx[0]
                        try:
                            cu = tr._js("cuon", x["id"]) or {}
                            r = cu.get("rect") or x.get("rect")
                            tr._chuot_toi(r["x"] + r["w"] * 0.6, r["y"] + min(r["h"] / 2.0, 30))
                        except Exception:  # noqa: BLE001
                            pass
                        self._gian(0.6, 1.0)
                        pm = kiem("xem_menu", trong=x) or tr.tim("xem_menu", han=2, hien=False, trong=x)
                        if pm and self._la_cua_kenh(x):
                            tr.bam(pm, hau_dieu_kien=lambda: tr.co("xem_menu_ghim"), han_hau=6)
                            kiem("xem_menu_ghim")
                            tr.ghi_bang_chung("kiem-cmt-menu")
                            tr.phim("Escape")
        except Exception as loi:  # noqa: BLE001
            kq["hong"].append("loi:{0}".format(str(loi)[:160]))
            try:
                tr.ghi_bang_chung("kiem-cmt-loi")
            except Exception:  # noqa: BLE001
                pass
        finally:
            try:
                tr.dong()
            finally:
                if tr in self.tab:
                    self.tab.remove(tr)
        kq["ok"] = not kq["hong"]
        return kq


def cdp_studio_thu_muc() -> str:
    return os.path.join(THU_MUC_LOG, "dom")


def sinh_tra_loi_mac_dinh(prompt: str):
    """Sinh câu trả lời — DÙNG LẠI `may_cmt.gen_reply_with_prompt` (trạm /van-ban bằng
    key của tool, Gemini dự phòng). Hỏng nạp → gọi thẳng trạm bằng thư viện chuẩn."""
    try:
        import may_cmt  # noqa: PLC0415
        if getattr(may_cmt, "requests", None) is not None:
            return may_cmt.gen_reply_with_prompt(prompt)
    except Exception as loi:  # noqa: BLE001
        log.warning("không nạp được may_cmt (%s) — gọi thẳng trạm", str(loi)[:100])
    import urllib.request  # noqa: PLC0415
    tram = ""
    try:
        with open(os.path.join(GOC, "cai-dat-tool.json"), "r", encoding="utf-8") as tep:
            tram = str((json.load(tep) or {}).get("tram") or "")
    except (OSError, ValueError):
        pass
    if not tram:
        return None
    for lan in range(3):
        try:
            yeu_cau = urllib.request.Request(
                tram.rstrip("/") + "/van-ban", data=json.dumps({"de_bai": prompt}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(yeu_cau, timeout=150) as tl:
                chu = (json.loads(tl.read().decode("utf-8")) or {}).get("chu") or ""
            if chu.strip():
                return chu.strip()
        except Exception as loi:  # noqa: BLE001
            log.warning("trạm /van-ban lỗi (lần %d): %s", lan + 1, str(loi)[:120])
            time.sleep(5)
    return None


# ═══ CLI ═════════════════════════════════════════════════════════════════

_O_KHOA = None


def _khoa_mot_minh(cong: int = CONG_KHOA) -> bool:
    global _O_KHOA
    try:
        _O_KHOA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA.bind(("127.0.0.1", cong))
        _O_KHOA.listen(1)
        return True
    except OSError:
        return False


def doc_cai_dat(kenh: str, goc_tool: str = GOC_TOOL, thu_muc_vm: str = GOC) -> dict:
    """Thiết lập hiệu lực cho máy bình luận: khối kênh trong `vm/cai-dat-tool.json`
    (agent chép từ trạm) → lùi `CHANNEL/<k>/may-ao.json`; ngôn ngữ + giọng văn từ kenh.yaml."""
    ra = {"tu_dang": False, "tu_tra_loi_cmt": True, "binh_luan_dom": True,
          "cmt_toi_da_phien": TOI_DA_TRA_LOI, "ghim_dom": False}
    try:
        with open(os.path.join(goc_tool, "CHANNEL", kenh, "may-ao.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep) or {}
        ra.update({k: du[k] for k in ("tu_dang", "tu_tra_loi_cmt", "binh_luan_dom", "cmt_toi_da_phien", "ghim_dom")
                   if k in du})
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(thu_muc_vm, "cai-dat-tool.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep) or {}
        rieng = (du.get("kenh") or {}).get(kenh)
        if isinstance(rieng, dict):
            ra.update({k: rieng[k] for k in ("tu_dang", "tu_tra_loi_cmt", "binh_luan_dom", "cmt_toi_da_phien", "ghim_dom")
                       if k in rieng and rieng[k] is not None})
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(goc_tool, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8") as tep:
            for dong in tep:
                m = re.match(r'^ngon_ngu:\s*"?([A-Za-z-]+)"?', dong)
                if m and "ngon_ngu" not in ra:
                    ra["ngon_ngu"] = m.group(1)
                g = re.match(r'^giong_van:\s*"(.*)"\s*$', dong)
                if g and "giong_van" not in ra:
                    ra["giong_van"] = g.group(1)
    except OSError:
        pass
    return ra


def doc_ke_hoach_kenh(kenh: str, cfg: dict = None, goc_tool: str = GOC_TOOL) -> list:
    duong = os.path.join(goc_tool, "CHANNEL", kenh, "ke-hoach-dang", "ke-hoach.csv")
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return doc_ke_hoach(tep.read())
    except OSError:
        pass
    try:
        import agent  # noqa: PLC0415
        import nguon_tool  # noqa: PLC0415
        return doc_ke_hoach(nguon_tool._tai_csv(agent.cau_hinh_kenh(cfg or {}, kenh), kenh))
    except Exception as loi:  # noqa: BLE001
        log.warning("không đọc được kế hoạch %s: %s", kenh, str(loi)[:120])
        return []


def _doc_json(duong: str) -> dict:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _cai_nhat_ky(ra_man_hinh: bool) -> None:
    os.makedirs(THU_MUC_LOG, exist_ok=True)
    tay = []
    try:
        from logging.handlers import RotatingFileHandler  # noqa: PLC0415
        tay.append(RotatingFileHandler(os.path.join(THU_MUC_LOG, "cmt-dom.log"),
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
    ap = argparse.ArgumentParser(prog="may_cmt_dom.py")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--mot-lan", action="store_true", help="mồi+ghim rồi trả lời (phiên kênh)")
    ap.add_argument("--chi-moi", action="store_true", help="chỉ bình luận mồi + ghim")
    ap.add_argument("--chi-tra-loi", action="store_true")
    ap.add_argument("--ma", help="chỉ gói này (bỏ cửa sổ ngày)")
    ap.add_argument("--toi-da", type=int, default=-1, help="số trả lời tối đa lượt này")
    ap.add_argument("--kiem-dom", action="store_true", help="CHỈ ĐỌC: đo bộ chọn bình luận")
    ap.add_argument("--video", default="", help="--kiem-dom: video để đo trang xem + Studio video")
    ap.add_argument("--mo-hop", action="store_true", help="--kiem-dom: mở ô trả lời Studio rồi Hủy")
    ap.add_argument("--trong-phien", action="store_true",
                    help="agent gọi giữa phiên — dùng khoá máy của agent, không tự giữ")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = _doc_lenh(sys.argv[1:] if argv is None else argv)
    _cai_nhat_ky(ra_man_hinh=a.kiem_dom or bool(a.ma) or not a.trong_phien)
    import agent  # noqa: PLC0415
    import cdp as cdp_mod  # noqa: PLC0415
    import cdp_studio  # noqa: PLC0415
    import may_dang_dom as mdd  # noqa: PLC0415

    if not _khoa_mot_minh():
        log.error("đã có một máy bình luận DOM khác đang chạy (cổng %d) — thoát", CONG_KHOA)
        return MA_CHAN
    cai = doc_cai_dat(a.kenh)
    lam_moi = not a.chi_tra_loi
    lam_tra_loi = not a.chi_moi and not a.ma
    if not a.kiem_dom:
        if (a.mot_lan or a.chi_moi) and not cai.get("binh_luan_dom", True):
            log.info("kênh %s: binh_luan_dom đang TẮT — bỏ qua", a.kenh)
            return MA_XONG
        if lam_tra_loi and not cai.get("tu_tra_loi_cmt", True):
            log.info("kênh %s: tu_tra_loi_cmt TẮT — chỉ làm bình luận mồi", a.kenh)
            lam_tra_loi = False
    toi_da = a.toi_da if a.toi_da >= 0 else int(cai.get("cmt_toi_da_phien") or TOI_DA_TRA_LOI)
    hang = doc_ke_hoach_kenh(a.kenh)
    cai["_ke_hoach"] = hang
    so = SoCmt()
    cac = []
    if lam_moi and not a.kiem_dom:
        cac = chon_goi_can_moi(hang, _doc_json(DUONG_SO_VIDEO), so.doc(), a.kenh, datetime.now(),
                               ma=a.ma, ghim_bat=bool(cai.get("ghim_dom", True)))[:TOI_DA_MOI_LUOT]
        log.info("kênh %s: %d gói cần bình luận mồi/ghim%s", a.kenh, len(cac),
                 (": " + ", ".join(g["ma"] for g in cac)) if cac else "")
    if not a.kiem_dom and not cac and not (lam_tra_loi and toi_da > 0):
        log.info("kênh %s: không có việc bình luận", a.kenh)
        return MA_XONG

    tu_giu = not a.trong_phien
    if tu_giu and not agent.giu_khoa_may_chung(viec="binh_luan", kenh=a.kenh, uu_tien=1):
        log.error("không giữ được khe nặng (.khoa-may) — có phiên/đăng/sản xuất đang chạy; không ép")
        return MA_CHAN
    cdp = None
    may = None
    ma_thoat = MA_HONG
    try:
        if agent.van_ipv4_mo():
            log.error("van IPv4 đang mở — không nối Chrome kênh")
            return MA_CHAN
        cfg = agent.doc_cau_hinh()
        bo = json.loads(json.dumps(cdp_studio.doc_bo_chon()))
        loi_bo = cdp_studio.kiem_bo_chon(bo)
        if loi_bo:
            log.error("studio-selectors.json lỗi: %s", "; ".join(loi_bo))
            return MA_LUI
        if bo.get("cam_bam_binh_luan"):
            bo["cam_bam"] = {k: v for k, v in bo["cam_bam_binh_luan"].items() if k != "ghi_chu"}
        try:
            cdp = cdp_mod.ket_noi_kenh(cfg, a.kenh, nhat_ky=log.info)
        except cdp_mod.CdpKhongDung as loi:
            log.error("không dùng được đường DOM: %s (mã %d)", loi.ly_do, loi.ma)
            return loi.ma
        log.info("đã nối Chrome kênh %s (%s, cổng %s%s)", a.kenh, cdp.phien_ban, cdp.cong,
                 ", máy này tự mở" if cdp.tu_mo else "")

        def tao_trang():
            return cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=log.info,
                                                     thu_muc_dom=cdp_studio.THU_MUC_DOM)

        md = mdd.MayDangDom(a.kenh, bo, tao_trang, mdd.SoVideoId(), bao=None, thu_muc_done="",
                            nhat_ky=log.info)
        may = MayCmtDom(a.kenh, bo, tao_trang, so, nhat_ky=log.info, cai=cai,
                        tra_kenh=md.tra_kenh, lay_uc=md.lay_uc)
        try:
            may.lay_uc()
        except mdd.DungKenh as loi:
            log.error("%s", loi)
            return MA_CHAN
        except Exception as loi:  # noqa: BLE001
            log.error("không đọc được UC kênh: %s", loi)
            return MA_LUI
        if a.kiem_dom:
            kq = may.kiem_dom(vid=a.video, mo_hop=a.mo_hop)
            kq["chrome"] = cdp.phien_ban
            os.makedirs(THU_MUC_KIEM, exist_ok=True)
            duong = os.path.join(THU_MUC_KIEM, "{0}-cmt.json".format(a.kenh))
            with open(duong, "w", encoding="utf-8") as tep:
                json.dump(kq, tep, ensure_ascii=False, indent=1, default=str)
            dong = "máy bình luận DOM kiểm {0}: {1}{2}".format(
                a.kenh, "OK" if kq["ok"] else "HỎNG " + ", ".join(kq["hong"]),
                " · dự phòng " + ", ".join("{0}:{1}".format(k, v) for k, v in kq["du_phong"].items())
                if kq["du_phong"] else "")
            log.info("%s → %s", dong, duong)
            try:
                agent.ghi(dong)
            except Exception:  # noqa: BLE001
                pass
            md.dong_het()
            ma_thoat = MA_XONG if kq["ok"] else MA_LUI
            return ma_thoat
        loi_truoc = loi_sau = 0
        for goi in cac:
            try:
                ket = may.dang_va_ghim(dict(goi, can_kiem_cong_khai=True))
                log.info("%s: %s", goi["ma"], ket)
                may.bao_cao["moi"].append({"ma": goi["ma"], "ket": ket})
            except LoiMay as loi:
                log.error("%s: bình luận mồi/ghim hỏng: %s", goi["ma"], loi)
                may.bao_cao["loi"].append("{0}: {1}".format(goi["ma"], loi))
                if loi.truoc and not may.cham_kenh:
                    loi_truoc += 1
                else:
                    loi_sau += 1
            except (mdd.LoiTruoc, mdd.LoiSau) as loi:
                log.error("%s: tra kênh hỏng: %s", goi["ma"], loi)
                may.bao_cao["loi"].append("{0}: {1}".format(goi["ma"], loi))
                loi_truoc += 1
        md.dong_het()
        kq_tl = {}
        if lam_tra_loi and toi_da > 0:
            try:
                kq_tl = may.tra_loi(toi_da)
                log.info("kênh %s: trả lời %d · bỏ qua %d · lỗi %d", a.kenh, kq_tl.get("da_tra_loi", 0),
                         kq_tl.get("bo_qua", 0), kq_tl.get("loi", 0))
                if kq_tl.get("loi"):
                    loi_sau += 1
            except LoiMay as loi:
                log.error("kênh %s: trả lời bình luận hỏng: %s", a.kenh, loi)
                may.bao_cao["loi"].append("trả lời: {0}".format(loi))
                if loi.truoc and not may.cham_kenh:
                    loi_truoc += 1
                else:
                    loi_sau += 1
        may.bao_cao["tra_loi_tong"] = kq_tl
        if loi_sau or (loi_truoc and may.cham_kenh):
            ma_thoat = MA_HONG
        elif loi_truoc:
            ma_thoat = MA_LUI
        else:
            ma_thoat = MA_XONG
        try:
            agent.ghi("bình luận DOM {0}: mồi/ghim {1} gói · trả lời {2} · mã {3}".format(
                a.kenh, len(cac), kq_tl.get("da_tra_loi", 0), ma_thoat))
        except Exception:  # noqa: BLE001
            pass
        return ma_thoat
    except Exception as loi:  # noqa: BLE001 — không chết im lặng
        log.exception("lỗi không lường: %s", loi)
        return MA_HONG
    finally:
        if may is not None:
            may.dong_het()
            try:
                with open(DUONG_BAO_CAO, "w", encoding="utf-8") as tep:
                    json.dump(dict(may.bao_cao, ma_thoat=ma_thoat, luc=time.strftime("%Y-%m-%d %H:%M:%S")),
                              tep, ensure_ascii=False, indent=1, default=str)
            except OSError:
                pass
        if cdp is not None:
            if cdp.tu_mo and not a.trong_phien:
                ok = cdp_mod.dong_trinh_duyet(cdp)
                log.info("đóng Chrome kênh %s (máy này đã mở): %s", a.kenh,
                         "cổng đã đóng" if ok else "CỔNG CHƯA ĐÓNG sau 20s")
            else:
                cdp.dong()
        if tu_giu:
            agent.nha_khoa_may_chung()


if __name__ == "__main__":
    raise SystemExit(main())
