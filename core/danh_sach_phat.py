"""DANH SÁCH PHÁT CHỦ ĐỀ TỰ ĐỘNG (16/10/2026) — phần THUẦN (kế hoạch, chọn danh sách cho video mới, điều kiện skill).

═══ VÌ SAO ═══
`python -m core.chuyen_doi_sub` báo «danh sách phát chủ đề: CHƯA khai» ở các kênh chính (kenh.yaml không có
`danh_sach_phat_kenh`): mọi video mới rơi vào «danh sách phát đầu tiên» của hộp tải lên. Danh sách phát theo chủ đề
kéo dài phiên xem, mở thêm nguồn gợi ý/duyệt và kéo đăng ký — đòn bẩy YPP rẻ nhất còn thiếu.

═══ LÀM GÌ ═══
1. KẾ HOẠCH (`lap_ke_hoach`, một lượt LLM qua phễu chuẩn `cum_y_nghia.goi_vi` = Claude Max, lùi ví ShopAPI): gom video ĐÃ
   ĐĂNG (`chi-so/bang-tom-tat.csv`) thành `SO_DS_MIN`–`SO_DS_MAX` danh sách theo NGHĨA (không lọc từ khoá); gợi ý cụm V7 +
   nhãn cụm theo nghĩa sẵn có của kênh; tên + mô tả bằng ngôn ngữ kênh; LLM cân nhắc ≥ 2 cách chia, ghi lý do + độ tin.
   Mã kiểm lại (`chuan_hoa_ke_hoach`): số danh sách, tên hợp lệ/không trùng, mỗi video đúng một danh sách; thiếu video
   thì xếp bù (`gan_video`). Video trong danh sách xếp TỐT TRƯỚC theo lượt xem rồi lượt hiển thị; danh sách xếp theo
   tổng lượt xem. → `CHANNEL/<k>/nghien-cuu/danh-sach-phat.json` (tệp dữ liệu, KHÔNG đụng kenh.yaml).
   CHỈ video của chính kênh do tool đăng (`loc_rieng`: sổ máy đăng + kế hoạch đăng + hồ sơ video); video lạ trong bảng
   Studio (tải tay / nội dung người khác) bị loại, ghi ở `ngoai_kenh`.
2. VIDEO MỚI (`gan_moi`): video đã đăng chưa nằm trong danh sách nào của kế hoạch → cột «Danh sách phát» của kế hoạch
   đăng (máy đăng đã thả vào đó) nếu là tên trong kế hoạch, không thì LLM chọn theo nghĩa, hỏng thì danh sách ĐẦU.
3. TẢI LÊN (`ten_cho_tai_len` + `chon_cho_video`, gọi từ `ban_giao_dang`): kenh.yaml khai → như cũ; không khai mà kế
   hoạch có danh sách ĐÃ TẠO → LLM chọn danh sách hợp nhất, hỏng/không khớp → danh sách đầu của kế hoạch.
4. YOUTUBE (`vm/danh_sach_phat_dom.py`, CHỈ qua Studio — không mở trang xem): tạo danh sách còn thiếu (Công khai, có mô
   tả), thêm video ở trang sửa video (ô «Danh sách phát» → Lưu), đọc lại — idempotent:
   tên đã có thì dùng lại, không tạo trùng, không xoá/đổi tên danh sách nào, không bỏ video khỏi danh sách nào.
5. SKILL D15 (`core/ky_nang.py`): `can_chay` — kênh ĐƯỢC PHÁT (`kenh_khong_phat` = song), kenh.yaml không khai, và: chưa
   có kế hoạch (đủ `VIDEO_TOI_THIEU` video) | còn danh sách chưa tạo | còn video chờ thêm | ≥ `MOI_TOI_THIEU` video mới
   chưa được xác nhận nằm trong danh sách nào (video máy đăng đã thả vào danh sách cũng tính — lượt chạy đọc lại «đã có»
   rẻ, bắt cả lần thả hỏng im lặng). Video hỏng `LOI_VIDEO_TOI_DA` lần → bỏ (không kẹt mãi).

    python -X utf8 -m core.danh_sach_phat xem [--kenh K]          # trạng thái + điều kiện skill (chỉ đọc)
    python -X utf8 -m core.danh_sach_phat ke-hoach --kenh K [--thu]  # lập/cập nhật kế hoạch (LLM); --thu: in, không ghi
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

PHIEN_BAN = 1
TEP = ("nghien-cuu", "danh-sach-phat.json")
SO_DS_MIN, SO_DS_MAX = 3, 5
VIDEO_TOI_THIEU = 6          # ít hơn → chưa lập (3 danh sách × 2 video)
MOI_TOI_THIEU = 8            # video mới chưa vào danh sách nào → lập lại / gán thêm
LOI_VIDEO_TOI_DA = 3         # một video hỏng ngần này lần → bỏ
#: 16/10/2026: tên NGẮN như danh sách chủ/máy cũ đã làm (một cụm ngắn ~8–15 ký tự) — tên SEO dài «…｜…» bị
#: cắt cụt trên thẻ danh sách và lệch kiểu cả kênh.
TEN_TOI_DA, MO_TA_TOI_DA = 20, 400
THIEU_TOI_DA = 0.3           # LLM bỏ sót > 30% video → kế hoạch hỏng, hỏi lại
TI_LE_SO_PHU = 0.5           # sổ tool phủ ≥ ngần này bảng Studio → chỉ nhận video có trong sổ (`loc_rieng`)
SO_LAN_HOI = 2
MO_HINH = "claude-opus-5"    # ví; thuê bao Max đi thang riêng (đầu thang opus-5-5)
GIO_CHO_DANG_NHAP = 12.0     # bị đăng xuất → skill nghỉ ngần này giờ (đã báo động), rồi thử lại
DA_TAO, KE_HOACH = "da_tao", "ke_hoach"
COT_DSP, COT_VID = "Danh sách phát", "Video ID"


# ── tiện ích ────────────────────────────────────────────────────────────────

def chuan_ten(s: Any) -> str:
    """So tên danh sách phát: NFKC, gộp khoảng trắng (như `keo_cheo_dom.chuan_ten`)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def _khoa_ten(s: Any) -> str:
    return chuan_ten(s).casefold()


def _so(x: Any) -> float:
    try:
        return float(str(x or "").replace(",", "").replace("%", "").strip() or 0)
    except ValueError:
        return 0.0


def _luc(bay: Optional[_dt.datetime] = None) -> str:
    return (bay or _dt.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def _doc_luc(chu: Any) -> Optional[_dt.datetime]:
    try:
        return _dt.datetime.strptime(str(chu or "")[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _thu_muc_kenh(goc: str, kenh: str) -> str:
    return os.path.join(goc, "CHANNEL", kenh)


def duong(goc: str, kenh: str) -> str:
    return os.path.join(_thu_muc_kenh(goc, kenh), *TEP)


def doc(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        with io.open(duong(goc, kenh), encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi(goc: str, kenh: str, du: Dict[str, Any]) -> str:
    """Ghi nguyên tử (tệp tạm + os.replace)."""
    p = duong(goc, kenh)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    du = dict(du, phien_ban=PHIEN_BAN, kenh=kenh, luc_cap_nhat=_luc())
    with io.open(p + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
    return p


def _kenh_yaml(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        from .kenh import doc_yaml  # noqa: PLC0415
        return doc_yaml(os.path.join(_thu_muc_kenh(goc, kenh), "kenh.yaml")) or {}
    except Exception:  # noqa: BLE001
        return {}


def ten_yaml(goc: str, kenh: str, k: Any = None) -> List[str]:
    """`danh_sach_phat_kenh` khai tay trong kenh.yaml ("a | b | c") — có thì kênh do K14 lo, máy này không lập."""
    v = getattr(k, "danh_sach_phat_kenh", None) if k is not None else _kenh_yaml(goc, kenh).get("danh_sach_phat_kenh")
    return [t.strip() for t in str(v or "").split("|") if t.strip()]


def duoc_phat(goc: str, kenh: str) -> Tuple[bool, str]:
    """`core.kenh_khong_phat`: chỉ trạng thái «song» (YouTube đang phát) mới là được phát."""
    try:
        from . import kenh_khong_phat  # noqa: PLC0415
        tt = kenh_khong_phat.doc(goc, kenh)
    except Exception as loi:  # noqa: BLE001
        return False, "không đọc được trạng thái phát: {0}".format(str(loi)[:80])
    if tt.get("trang_thai") == "song":
        return True, "được phát"
    return False, "kênh chưa được xác nhận đang phát ({0}: {1})".format(
        tt.get("trang_thai") or "chưa tính", str(tt.get("ly_do") or "")[:80])


# ── video của kênh ──────────────────────────────────────────────────────────

def video_tool(goc: str, kenh: str) -> set:
    """Mã video tool đã đăng cho kênh: sổ máy đăng `vm/logs/so-video-id.json` (khoá `<kênh>/…`), cột «Video ID» của kế
    hoạch đăng, hồ sơ video `CHANNEL/<k>/ho-so-video/*.json`."""
    ra: set = set()
    try:
        with io.open(os.path.join(goc, "vm", "logs", "so-video-id.json"), encoding="utf-8") as tep:
            so = json.load(tep)
        ra |= {str(m.get("video_id")) for kh, m in (so or {}).items()
               if isinstance(m, dict) and str(kh).startswith(kenh + "/") and m.get("video_id")}
    except (OSError, ValueError, AttributeError):
        pass
    try:
        from . import ke_hoach_dang  # noqa: PLC0415
        cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
        if COT_VID in cot:
            i = cot.index(COT_VID)
            ra |= {h[i].strip() for h in hang if len(h) > i and h[i].strip()}
    except Exception:  # noqa: BLE001
        pass
    thu_muc = os.path.join(_thu_muc_kenh(goc, kenh), "ho-so-video")
    try:
        ten = [t for t in os.listdir(thu_muc) if t.endswith(".json")]
    except OSError:
        ten = []
    for t in ten:
        try:
            with io.open(os.path.join(thu_muc, t), encoding="utf-8") as tep:
                v = (json.load(tep) or {}).get("video_id")
            if v:
                ra.add(str(v))
        except (OSError, ValueError, AttributeError):
            continue
    return ra


def loc_rieng(goc: str, kenh: str, video: List[Dict[str, Any]],
              tool: Optional[set] = None) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """CHỈ video của CHÍNH kênh do tool đăng (16/10/2026: bảng Studio có video lạ — tải tay / nội dung người khác — không
    được vào danh sách phát chủ đề). Sổ của tool phủ ≥ `TI_LE_SO_PHU` bảng → giữ video có trong sổ; phủ ít hơn (lịch sử
    kênh làm ở MÁY KHÁC, sổ máy này không có) → giữ cả bảng Studio, nguồn ghi rõ để người soát.
    Trả (video giữ, [mã bị loại], nguồn)."""
    tool = video_tool(goc, kenh) if tool is None else tool
    co = [v for v in video if v["id"] in tool]
    if video and len(co) >= TI_LE_SO_PHU * len(video):
        return co, [v["id"] for v in video if v["id"] not in tool], "so_tool"
    return list(video), [], "studio_lich_su_may_khac" if video else ""


def video_kenh(goc: str, kenh: str, rieng: bool = True) -> List[Dict[str, Any]]:
    """Video ĐÃ ĐĂNG từ `chi-so/bang-tom-tat.csv`: `[{id, tieu_de, view, hien_thi, ngay}]`, bỏ dòng không mã / không
    tiêu đề thật (tiêu đề = mã: Studio chưa trả tên — không xếp được theo nghĩa); `rieng` → chỉ video của kênh
    (`loc_rieng`)."""
    ra = _video_bang(goc, kenh)
    return loc_rieng(goc, kenh, ra)[0] if rieng else ra


def _video_bang(goc: str, kenh: str) -> List[Dict[str, Any]]:
    p = os.path.join(_thu_muc_kenh(goc, kenh), "chi-so", "bang-tom-tat.csv")
    try:
        with io.open(p, encoding="utf-8-sig") as tep:
            hang = list(csv.DictReader(tep))
    except OSError:
        return []
    ra, thay = [], set()
    for h in hang:
        vid = str(h.get("Mã video") or "").strip()
        td = " ".join(str(h.get("Tiêu đề") or "").split())
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) or vid in thay or not td or td == vid:
            continue
        thay.add(vid)
        ra.append({"id": vid, "tieu_de": td, "view": _so(h.get("Lượt xem")), "hien_thi": _so(h.get("Lượt hiển thị")),
                   "ngay": str(h.get("Ngày đăng") or "")[:10]})
    return ra


def xep_tot_truoc(ids: Sequence[str], thong_tin: Dict[str, Dict[str, Any]]) -> List[str]:
    """Tốt trước: lượt xem giảm dần, rồi lượt hiển thị; hoà thì giữ thứ tự cũ."""
    vt = {v: i for i, v in enumerate(ids)}
    return sorted(dict.fromkeys(ids), key=lambda v: (-_so((thong_tin.get(v) or {}).get("view")),
                                                     -_so((thong_tin.get(v) or {}).get("hien_thi")), vt[v]))


def _cot_ke_hoach_dang(goc: str, kenh: str) -> Dict[str, str]:
    """Video ID → tên «Danh sách phát» máy đăng đã nhắm (kế hoạch đăng)."""
    try:
        from . import ke_hoach_dang  # noqa: PLC0415
        cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    except Exception:  # noqa: BLE001
        return {}
    if COT_DSP not in cot or COT_VID not in cot:
        return {}
    i, j = cot.index(COT_VID), cot.index(COT_DSP)
    return {h[i].strip(): h[j].strip() for h in hang if len(h) > max(i, j) and h[i].strip() and h[j].strip()}


# ── gợi ý cụm sẵn có ────────────────────────────────────────────────────────

def goi_y_cum(goc: str, kenh: str, tieu_de: Sequence[str]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """(bộ cụm V7 `{mã: {ten, tu}}`, {tiêu đề: mã cụm theo nghĩa đã gán}) — hỏng thì rỗng (chỉ là gợi ý)."""
    try:
        from . import cum_y_nghia  # noqa: PLC0415
        bo = cum_y_nghia.BoNho(goc, kenh)
        return dict(bo.cum), {t: bo.tra(t) for t in tieu_de if bo.tra(t)}
    except Exception:  # noqa: BLE001
        return {}, {}


def _mo_ta_ngach(goc: str, kenh: str) -> str:
    try:
        from . import cum_y_nghia  # noqa: PLC0415
        return cum_y_nghia._mo_ta_ngach(goc, kenh)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return ""


def _ten_ngon_ngu(ma: str) -> str:
    return {"ja": "tiếng Nhật", "vi": "tiếng Việt", "en": "tiếng Anh", "ko": "tiếng Hàn", "zh": "tiếng Trung",
            "es": "tiếng Tây Ban Nha", "pt": "tiếng Bồ Đào Nha"}.get(str(ma or "").lower()[:2], "ngôn ngữ của kênh")


# ── LLM: lập kế hoạch ───────────────────────────────────────────────────────

def de_bai_ke_hoach(video: Sequence[Dict[str, Any]], cum: Dict[str, Any], nhan: Dict[str, str], ds_co: Sequence[str],
                    ngon_ngu: str = "ja", mo_ta_ngach: str = "") -> str:
    ds_cum = "\n".join("- {0}: {1}{2}".format(m, str((c or {}).get("ten") or ""), " (vd: {0})".format(
        "、".join(str(t) for t in ((c or {}).get("tu") or [])[:5])) if (c or {}).get("tu") else "")
        for m, c in (cum or {}).items()) or "(chưa có)"
    dong = "\n".join("{0}. {1}{2} — {3:.0f} lượt xem".format(i + 1, v["tieu_de"][:140], "  〔cụm {0}〕".format(
        nhan[v["tieu_de"]]) if nhan.get(v["tieu_de"]) else "", _so(v.get("view"))) for i, v in enumerate(video))
    nn = _ten_ngon_ngu(ngon_ngu)
    return (
        "Bạn là biên tập viên kênh YouTube{ngach}. Chia các video ĐÃ ĐĂNG dưới đây thành {a}–{b} DANH SÁCH PHÁT THEO CHỦ ĐỀ "
        "để người xem xem liền nhiều video (tăng thời gian phiên, lượt gợi ý và đăng ký).\n"
        "Gom theo Ý NGHĨA — người vừa xem video này sẽ muốn xem tiếp video nào — KHÔNG theo chữ chung. Bỏ qua nhãn 【】 "
        "và hashtag.\n\n"
        "CỤM CHỦ ĐỀ SẴN CÓ của kênh (gợi ý, dùng lại khi hợp; chữ ví dụ chỉ để hiểu nghĩa):\n{cum}\n\n"
        "DANH SÁCH PHÁT ĐÃ CÓ trên kênh (không đổi tên được; chỉ dùng lại ĐÚNG NGUYÊN VĂN khi thật sự hợp một nhóm, "
        "còn lại đặt tên khác hẳn): {co}\n\n"
        "Yêu cầu:\n"
        "- Mỗi video vào ĐÚNG MỘT danh sách (ghi số thứ tự). Mỗi danh sách ≥ 2 video.\n"
        "- \"ten\": {nn}, tự nhiên, đúng thứ người xem hay tìm (có từ chủ đề rõ), hợp giọng các tiêu đề của kênh, "
        "≤ {tt} ký tự — NGẮN gọn, một cụm chủ đề (~8–15 ký tự), KHÔNG dấu ｜/|, "
        "không 【】, không emoji, không dấu < >, không tên kênh, các tên khác hẳn nhau.\n"
        "- \"mo_ta\": 1–3 câu {nn} (≤ 200 ký tự): danh sách giúp người xem hiểu/được gì; tự nhiên, có từ khoá chủ đề, "
        "không hashtag, không < >.\n"
        "- Cân nhắc ít nhất HAI cách chia khác nhau, chọn cách người xem sẽ xem liền nhiều nhất; \"ly_do\" (tiếng Việt, "
        "ngắn) và \"do_tin\" 0–1 cho mỗi danh sách; \"phan_bien\": điểm yếu của cách chia đã chọn.\n\n"
        "VIDEO (số. tiêu đề 〔cụm đã gán〕 — lượt xem):\n{dong}\n\n"
        "Trả về DUY NHẤT một object JSON: {{\"danh_sach\": [{{\"ten\": \"...\", \"mo_ta\": \"...\", \"cum\": [\"mã cụm\"], "
        "\"video\": [1, 2], \"ly_do\": \"...\", \"do_tin\": 0.8}}], \"phan_bien\": \"...\"}}"
    ).format(ngach=" ({0})".format(mo_ta_ngach) if mo_ta_ngach else "", a=SO_DS_MIN, b=SO_DS_MAX, cum=ds_cum,
             co=" | ".join(ds_co) if ds_co else "(chưa có)", nn=nn, tt=TEN_TOI_DA, dong=dong)


def _sach_chu(s: Any, toi_da: int) -> str:
    s = re.sub(r"[<>]", "", " ".join(str(s or "").split()))
    s = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", s).strip()
    return s[:toi_da].strip()


def chuan_hoa_ke_hoach(du: Any, video: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Câu trả lời LLM → (`[{ten, mo_ta, cum, video:[id], ly_do, do_tin}]`, [id video bị sót]). Sai luật → ValueError.
    Luật: SO_DS_MIN–SO_DS_MAX danh sách; tên khác rỗng, ≤ TEN_TOI_DA, không trùng (NFKC, không phân biệt hoa/thường);
    mỗi video đúng một danh sách (lần đầu thắng); danh sách < 2 video bị bỏ (video của nó thành «sót»)."""
    if not isinstance(du, dict) or not isinstance(du.get("danh_sach"), list):
        raise ValueError("kế hoạch không có mảng danh_sach")
    ids = [v["id"] for v in video]
    ra, thay_ten, thay_vid = [], set(), set()
    for d in du["danh_sach"]:
        if not isinstance(d, dict):
            continue
        ten = _sach_chu(d.get("ten"), TEN_TOI_DA + 20)
        if not ten or len(ten) > TEN_TOI_DA or _khoa_ten(ten) in thay_ten:
            raise ValueError("tên danh sách không hợp lệ/trùng: {0!r}".format(str(d.get("ten"))[:80]))
        ds_vid = []
        for so in d.get("video") or []:
            try:
                i = int(so) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(ids) and ids[i] not in thay_vid:
                thay_vid.add(ids[i])
                ds_vid.append(ids[i])
        try:
            do_tin = max(0.0, min(1.0, float(d.get("do_tin"))))
        except (TypeError, ValueError):
            do_tin = None
        thay_ten.add(_khoa_ten(ten))
        ra.append({"ten": ten, "mo_ta": _sach_chu(d.get("mo_ta"), MO_TA_TOI_DA),
                   "cum": [str(c) for c in (d.get("cum") or []) if str(c).strip()][:3] if isinstance(d.get("cum"), list) else [],
                   "video": ds_vid, "ly_do": str(d.get("ly_do") or "")[:300], "do_tin": do_tin})
    for d in [d for d in ra if len(d["video"]) < 2]:
        ra.remove(d)
        thay_vid -= set(d["video"])
    if not SO_DS_MIN <= len(ra) <= SO_DS_MAX:
        raise ValueError("cần {0}–{1} danh sách (≥ 2 video mỗi cái), LLM trả {2}".format(SO_DS_MIN, SO_DS_MAX, len(ra)))
    sot = [v for v in ids if v not in thay_vid]
    if len(sot) > THIEU_TOI_DA * len(ids):
        raise ValueError("LLM bỏ sót {0}/{1} video".format(len(sot), len(ids)))
    return ra, sot


def de_bai_gan(ds: Sequence[Dict[str, Any]], muc: Sequence[Tuple[str, str]]) -> str:
    return ("Xếp mỗi video YouTube vào ĐÚNG MỘT danh sách phát chủ đề của kênh, theo Ý NGHĨA (video nói về gì, người "
            "xem danh sách nào sẽ muốn xem nó) — không theo chữ chung. Bỏ qua nhãn 【】 và hashtag.\n\nDANH SÁCH PHÁT:\n"
            + "\n".join("{0}. {1} — {2}".format(i + 1, d["ten"], str(d.get("mo_ta") or "")[:120]) for i, d in enumerate(ds))
            + "\n\nVIDEO:\n" + "\n".join("{0}. {1}".format(i + 1, td[:160]) for i, (_v, td) in enumerate(muc))
            + "\n\nTrả về DUY NHẤT một object JSON {\"<số video>\": <số danh sách>, ...}, đủ mọi video.")


def gan_video(goi: Optional[Callable[..., str]], ds: Sequence[Dict[str, Any]], muc: Sequence[Tuple[str, str]],
              kenh: str = "") -> Dict[str, int]:
    """`{id video: chỉ số danh sách}` — LLM theo nghĩa; mục LLM trả sai/thiếu → danh sách ĐẦU (0). `goi` None hoặc LLM
    hỏng hẳn → ném (lượt sau hỏi lại, không đổ bừa mọi video vào danh sách đầu)."""
    if not muc:
        return {}
    if len(ds) == 1:
        return {v: 0 for v, _t in muc}
    if goi is None:
        raise RuntimeError("không gọi được AI để xếp video vào danh sách phát")
    from .goi_van_ban import loc_json  # noqa: PLC0415

    khoa = "dsp-gan-{0}-{1}".format(kenh, hashlib.sha1("|".join(v for v, _t in muc).encode("utf-8")).hexdigest()[:10])
    du = loc_json(goi(de_bai_gan(ds, muc), mo_hinh=MO_HINH, khoa=khoa, toi_da_token=max(1024, 20 * len(muc) + 400)))
    if isinstance(du, list):
        du = {str(i + 1): x for i, x in enumerate(du)}
    if not isinstance(du, dict):
        raise ValueError("câu trả lời xếp video không phải JSON object")
    ra = {}
    for i, (v, _t) in enumerate(muc):
        try:
            j = int(du.get(str(i + 1))) - 1
        except (TypeError, ValueError):
            j = -1
        ra[v] = j if 0 <= j < len(ds) else 0
    return ra


def lap_ke_hoach(goc: str, kenh: str, goi: Optional[Callable[..., str]], *, video: Optional[List[Dict[str, Any]]] = None,
                 ds_co: Sequence[str] = (), log: Callable[[str], None] = lambda s: None) -> Dict[str, Any]:
    """Kế hoạch MỚI cho kênh (chưa ghi đĩa). Ném khi thiếu video / không gọi được AI / LLM hỏng `SO_LAN_HOI` lần."""
    loai: List[str] = []
    nguon = "truyen_vao"
    if video is None:
        video, loai, nguon = loc_rieng(goc, kenh, _video_bang(goc, kenh))
    if len(video) < VIDEO_TOI_THIEU:
        raise ValueError("mới có {0} video đã đăng (cần ≥ {1})".format(len(video), VIDEO_TOI_THIEU))
    if goi is None:
        raise RuntimeError("không gọi được AI (ví chặn / chưa cấu hình)")
    from .goi_van_ban import loc_json  # noqa: PLC0415

    cum, nhan = goi_y_cum(goc, kenh, [v["tieu_de"] for v in video])
    ngon_ngu = str(_kenh_yaml(goc, kenh).get("ngon_ngu") or "ja")
    de = de_bai_ke_hoach(video, cum, nhan, ds_co, ngon_ngu, _mo_ta_ngach(goc, kenh))
    loi_cuoi: Any = None
    for lan in range(SO_LAN_HOI):
        khoa = "dsp-ke-hoach-{0}-{1}-{2}".format(kenh, hashlib.sha1(de.encode("utf-8")).hexdigest()[:10], lan)
        try:
            du = loc_json(goi(de if not lan else de + "\n\n(Lần trước sai luật: {0}. Sửa đúng luật.)".format(loi_cuoi),
                              mo_hinh=MO_HINH, khoa=khoa, toi_da_token=6000))
            ds, sot = chuan_hoa_ke_hoach(du, video)
            break
        except Exception as loi:  # noqa: BLE001
            loi_cuoi = str(loi)[:200]
            log("  kế hoạch danh sách phát lần {0} hỏng: {1}".format(lan + 1, loi_cuoi))
    else:
        raise RuntimeError("LLM lập kế hoạch hỏng {0} lần: {1}".format(SO_LAN_HOI, loi_cuoi))
    tt = {v["id"]: v for v in video}
    if sot:
        g = gan_video(goi, ds, [(v, tt[v]["tieu_de"]) for v in sot], kenh)
        for v, j in g.items():
            ds[j]["video"].append(v)
    return {"luc": _luc(), "nguon": "llm", "so_video": len(video), "phan_bien": str((du or {}).get("phan_bien") or "")[:500],
            "tieu_de": {v["id"]: v["tieu_de"][:100] for v in video}, "nguon_video": nguon, "ngoai_kenh": loai,
            "danh_sach": _xep(ds, tt), "video_loi": {}, "video_bo": {}}


def _xep(ds: List[Dict[str, Any]], tt: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Video tốt trước; danh sách theo tổng lượt xem giảm dần; gắn mã p1…; trường trạng thái mặc định."""
    for d in ds:
        d["video"] = xep_tot_truoc(d["video"], tt)
    ds = sorted(ds, key=lambda d: -sum(_so((tt.get(v) or {}).get("view")) for v in d["video"]))
    for i, d in enumerate(ds):
        d.setdefault("ma", "p{0}".format(i + 1))
        for khoa, mac in (("trang_thai", KE_HOACH), ("da_them", []), ("tai_dung", False), ("luc_tao", ""),
                          ("luc_bam_tao", ""), ("loi", 0), ("loi_cuoi", "")):
            d.setdefault(khoa, mac)
    return ds


# ── trạng thái + video mới ──────────────────────────────────────────────────

def _bo(ke: Dict[str, Any]) -> set:
    return set((ke.get("video_bo") or {}).keys())


def la_cua_chu(d: Dict[str, Any]) -> bool:
    """Danh sách phát CỦA CHỦ: đã có trên kênh trước kế hoạch (tool không tạo — trùng tên nên «dùng lại»). Chủ 16/10/2026:
    để yên — chỉ dùng để khớp tên lúc tải lên, D15 KHÔNG BAO GIỜ thêm video vào. (`tai_dung` = dấu cũ cùng nghĩa.)"""
    return bool(d.get("cua_chu") or d.get("tai_dung"))


def chuan_cua_chu(ke: Dict[str, Any], ten_co: Sequence[str] = ()) -> int:
    """Đánh dấu `cua_chu` (trùng tên một danh sách đã có từ trước: `ten_co`, hoặc dấu `tai_dung`) và NHẢ các video kế
    hoạch xếp vào đó mà chưa xác nhận → `cho_xep` (lượt sau xếp lại theo nghĩa vào danh sách TOOL tạo). Trả số video nhả."""
    co = {_khoa_ten(t) for t in ten_co}
    n = 0
    for d in ke.get("danh_sach") or []:
        if not (la_cua_chu(d) or (_khoa_ten(d.get("ten")) in co and not d.get("luc_bam_tao"))):
            continue
        d["cua_chu"] = True
        nha = [v for v in d.get("video") or [] if v not in (d.get("da_them") or [])]
        if nha:
            d["video"] = [v for v in d.get("video") or [] if v in (d.get("da_them") or [])]
            ke["cho_xep"] = list(dict.fromkeys(list(ke.get("cho_xep") or []) + nha))
            n += len(nha)
    return n


def video_moi(ke: Dict[str, Any], video: Sequence[Dict[str, Any]]) -> List[str]:
    """Video đã đăng chưa nằm trong danh sách nào của kế hoạch (bỏ video đã bị loại)."""
    co = {v for d in ke.get("danh_sach") or [] for v in d.get("video") or []} | _bo(ke)
    return [v["id"] for v in video if v["id"] not in co]


def video_chua_xac_nhan(ke: Dict[str, Any], video: Sequence[Dict[str, Any]]) -> List[str]:
    """Video đã đăng chưa được XÁC NHẬN trong danh sách nào (đọc lại «đã tích») — kể cả video máy đăng đã thả vào."""
    co = {v for d in ke.get("danh_sach") or [] for v in d.get("da_them") or []} | _bo(ke) | set(ke.get("video_cua_chu") or [])
    return [v["id"] for v in video if v["id"] not in co]


def viec_con(ke: Dict[str, Any]) -> Dict[str, int]:
    """{chua_tao, cho_them}: danh sách chưa tạo trên YouTube · video đã xếp mà chưa xác nhận thêm (bỏ video bị loại)."""
    bo = _bo(ke)
    ds = ke.get("danh_sach") or []
    return {"chua_tao": sum(1 for d in ds if d.get("trang_thai") != DA_TAO),
            "cho_them": sum(1 for d in ds if not la_cua_chu(d) for v in d.get("video") or []
                            if v not in (d.get("da_them") or []) and v not in bo),
            "cho_xep": len(ke.get("cho_xep") or [])}


def gan_moi(goc: str, kenh: str, ke: Dict[str, Any], goi: Optional[Callable[..., str]],
            video: Optional[List[Dict[str, Any]]] = None) -> int:
    """Xếp video mới vào danh sách của kế hoạch (sửa `ke` tại chỗ, chưa ghi đĩa): cột «Danh sách phát» của kế hoạch đăng
    trước (máy đăng đã thả vào đó), còn lại LLM theo nghĩa. Trả số video đã xếp."""
    video = video_kenh(goc, kenh) if video is None else video
    tat_ca = ke.get("danh_sach") or []
    ds = [d for d in tat_ca if not la_cua_chu(d)]                    # danh sách CỦA CHỦ: không bao giờ xếp video vào
    tt = {v["id"]: v for v in video}
    nha = [v for v in ke.get("cho_xep") or [] if v in tt]
    moi = list(dict.fromkeys(nha + [v for v in video_moi(ke, video) if v not in set(ke.get("video_cua_chu") or [])]))
    if not moi or not ds:
        return 0
    theo_ten = {_khoa_ten(d["ten"]): i for i, d in enumerate(ds)}
    cua_chu = {_khoa_ten(d["ten"]) for d in tat_ca if la_cua_chu(d)}
    cot = _cot_ke_hoach_dang(goc, kenh)
    gan: Dict[str, int] = {}
    for v in moi:
        if v not in nha and _khoa_ten(cot.get(v)) in cua_chu:      # máy đăng đã thả vào danh sách của chủ: ghi nhận, để yên
            ke.setdefault("video_cua_chu", []).append(v)
            continue
        j = theo_ten.get(_khoa_ten(cot.get(v)))
        if j is not None:
            gan[v] = j
    con = [(v, tt[v]["tieu_de"]) for v in moi if v not in gan and v not in set(ke.get("video_cua_chu") or [])]
    gan.update(gan_video(goi, ds, con, kenh))
    ke["cho_xep"] = [v for v in ke.get("cho_xep") or [] if v not in gan and v in tt]
    for v, j in gan.items():
        if v not in ds[j]["video"]:
            ds[j]["video"].append(v)
    for d in ds:
        d["video"] = [v for v in d["video"] if v in (d.get("da_them") or [])] + xep_tot_truoc(
            [v for v in d["video"] if v not in (d.get("da_them") or [])], tt)
    ke.setdefault("tieu_de", {}).update({v: tt[v]["tieu_de"][:100] for v in gan})
    ke["luc_gan_moi"] = _luc()
    return len(gan)


def ghi_ket_video(ke: Dict[str, Any], d: Dict[str, Any], vid: str, ket: str) -> str:
    """Kết quả MỘT lần thêm (`keo_cheo_dom.KeoCheo.them`): ok/da_co → xác nhận; lỗi → đếm, đủ `LOI_VIDEO_TOI_DA` → bỏ.
    Trả "xac_nhan" | "loi" | "bo"."""
    if ket in ("ok", "da_co"):
        if vid not in d.setdefault("da_them", []):
            d["da_them"].append(vid)
        (ke.get("video_loi") or {}).pop(vid, None)
        return "xac_nhan"
    vl = ke.setdefault("video_loi", {})
    vl[vid] = int(vl.get(vid) or 0) + 1
    if vl[vid] >= LOI_VIDEO_TOI_DA:
        ke.setdefault("video_bo", {})[vid] = "hỏng {0} lần: {1}".format(vl[vid], str(ket)[:160])
        return "bo"
    return "loi"


# ── điều kiện skill D15 ─────────────────────────────────────────────────────

def can_chay(goc: str, kenh: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """(nên chạy máy danh sách phát cho kênh?, lý do) — CHỈ ĐỌC đĩa, rẻ."""
    if ten_yaml(goc, kenh):
        return False, "kenh.yaml đã khai danh_sach_phat_kenh (K14 lo)"
    ok, ly = duoc_phat(goc, kenh)
    if not ok:
        return False, ly
    ke = doc(goc, kenh)
    dx = _doc_luc((ke.get("dang_xuat") or {}).get("luc"))
    if dx and (bay or _dt.datetime.now()) - dx < _dt.timedelta(hours=GIO_CHO_DANG_NHAP):
        return False, "Chrome kênh bị đăng xuất lúc {0:%H:%M %d/%m} — chờ người đăng nhập (đã báo)".format(dx)
    video = video_kenh(goc, kenh)
    if not ke.get("danh_sach"):
        if len(video) < VIDEO_TOI_THIEU:
            return False, "mới có {0} video đã đăng (cần ≥ {1})".format(len(video), VIDEO_TOI_THIEU)
        return True, "chưa có danh sách phát chủ đề ({0} video)".format(len(video))
    vc = viec_con(ke)
    if vc["chua_tao"]:
        return True, "{0} danh sách chưa tạo trên YouTube".format(vc["chua_tao"])
    if vc["cho_them"]:
        return True, "{0} video chờ thêm vào danh sách".format(vc["cho_them"])
    if vc["cho_xep"] and any(not la_cua_chu(d) for d in ke["danh_sach"]):
        return True, "{0} video cần xếp lại (danh sách của chủ không nhận video)".format(vc["cho_xep"])
    moi = video_chua_xac_nhan(ke, video)
    if len(moi) >= MOI_TOI_THIEU:
        return True, "{0} video mới chưa vào danh sách nào (≥ {1})".format(len(moi), MOI_TOI_THIEU)
    return False, "đủ: {0} danh sách, {1} video mới chưa xác nhận (< {2})".format(
        len(ke["danh_sach"]), len(moi), MOI_TOI_THIEU)


# ── tải lên: danh sách cho video mới ────────────────────────────────────────

def ten_cho_tai_len(goc: str, kenh: str, k: Any = None) -> Tuple[List[str], str]:
    """(tên danh sách, nguồn "kenh_yaml" | "ke_hoach" | "") — kenh.yaml khai thì giữ như cũ; không thì danh sách ĐÃ TẠO
    của kế hoạch (thứ tự kế hoạch: mạnh nhất trước)."""
    tu_yaml = ten_yaml(goc, kenh, k)
    if tu_yaml:
        return tu_yaml, "kenh_yaml"
    ds = [d["ten"] for d in doc(goc, kenh).get("danh_sach") or [] if d.get("trang_thai") == DA_TAO and d.get("ten")]
    return (ds, "ke_hoach") if ds else ([], "")


def chon_cho_video(ten: Sequence[str], nguon: str, tieu_de: str, mo_ta: str, goi_ai) -> str:
    """LLM chọn danh sách hợp nhất (`ban_giao_dang.chon_danh_sach_phat`); nguồn kế hoạch mà LLM hỏng/không khớp → danh
    sách ĐẦU. Nguồn kenh.yaml giữ hành vi cũ ("" → máy đăng lấy mục đầu của hộp)."""
    if not ten:
        return ""
    from .ban_giao_dang import chon_danh_sach_phat  # noqa: PLC0415 — tránh vòng nhập

    dsp = chon_danh_sach_phat(" | ".join(ten), tieu_de, mo_ta, goi_ai)
    return dsp or (ten[0] if nguon == "ke_hoach" else "")


def mo_ta_ngan(goc: str, kenh: str) -> str:
    """Một cụm cho `chuyen_doi_sub.dong_nao`: "" khi chưa có danh sách nào đã tạo."""
    ke = doc(goc, kenh)
    ds = [d for d in ke.get("danh_sach") or [] if d.get("trang_thai") == DA_TAO]
    if not ds:
        return ""
    return "có (tự lập {0} danh sách, {1} video đã xác nhận)".format(len(ds), sum(len(d.get("da_them") or []) for d in ds))


# ── CLI ─────────────────────────────────────────────────────────────────────

def cat_ngoai_kenh(goc: str, kenh: str, ke: Dict[str, Any], video: Optional[List[Dict[str, Any]]] = None,
                   tool: Optional[set] = None) -> int:
    """Kế hoạch cũ: gỡ khỏi KẾ HOẠCH các video không phải của kênh (`loc_rieng`) chưa xác nhận trên YouTube (đã xác
    nhận thì giữ — máy không bao giờ bỏ video khỏi danh sách phát). Trả số video gỡ."""
    _giu, loai, nguon = loc_rieng(goc, kenh, _video_bang(goc, kenh) if video is None else video, tool)
    n = 0
    for d in ke.get("danh_sach") or []:
        truoc = len(d.get("video") or [])
        d["video"] = [v for v in d.get("video") or [] if v not in loai or v in (d.get("da_them") or [])]
        n += truoc - len(d["video"])
    ke["nguon_video"], ke["ngoai_kenh"] = nguon, loai
    return n


def cap_nhat_ke_hoach(goc: str, kenh: str, goi: Optional[Callable[..., str]], *, ds_co: Sequence[str] = (),
                      thu: bool = False, log: Callable[[str], None] = print) -> Tuple[Dict[str, Any], str]:
    """Chưa có kế hoạch → lập; có rồi → xếp video mới. Ghi đĩa (trừ `thu`). Trả (kế hoạch, việc đã làm)."""
    ke = doc(goc, kenh)
    if not ke.get("danh_sach"):
        ke = lap_ke_hoach(goc, kenh, goi, ds_co=ds_co, log=log)
        if chuan_cua_chu(ke, ds_co):                                 # LLM dùng lại tên của chủ → nhả, xếp ngay
            gan_moi(goc, kenh, ke, goi)
        viec = "lập kế hoạch {0} danh sách".format(len(ke["danh_sach"]))
    else:
        dau = [bool(d.get("cua_chu")) for d in ke["danh_sach"]]
        h = chuan_cua_chu(ke, ds_co)
        c = cat_ngoai_kenh(goc, kenh, ke)
        n = gan_moi(goc, kenh, ke, goi)
        viec = ", ".join(x for x in ("nhả {0} video khỏi danh sách của chủ".format(h) if h else "",
                                     "đánh dấu danh sách của chủ" if dau != [bool(d.get("cua_chu")) for d in ke["danh_sach"]]
                                     and not h else "",
                                     "bỏ {0} video không phải của kênh".format(c) if c else "",
                                     "xếp {0} video mới".format(n) if n else "") if x)
    if viec and not thu:
        ghi(goc, kenh, ke)
    return ke, viec


def in_ke_hoach(ke: Dict[str, Any], in_ra: Callable[[str], None] = print) -> None:
    td = ke.get("tieu_de") or {}
    for d in ke.get("danh_sach") or []:
        in_ra("  [{0}] «{1}» — {2} video, xác nhận {3}, {4}{5}".format(
            d.get("ma"), d.get("ten"), len(d.get("video") or []), len(d.get("da_them") or []), d.get("trang_thai"),
            " (CỦA CHỦ — không thêm video)" if la_cua_chu(d) else ""))
        if d.get("mo_ta"):
            in_ra("       {0}".format(d["mo_ta"]))
        for v in (d.get("video") or [])[:40]:
            in_ra("       - {0} {1}".format(v, str(td.get(v) or "")[:60]))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.danh_sach_phat")
    ap.add_argument("lenh", choices=("xem", "ke-hoach"))
    ap.add_argument("--kenh", action="append", default=[])
    ap.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--thu", action="store_true")
    a = ap.parse_args(argv)
    goc = a.goc
    from .kenh import da_tra_kho  # noqa: PLC0415

    kenh_ds = a.kenh or sorted(x for x in os.listdir(os.path.join(goc, "CHANNEL"))
                               if os.path.isfile(os.path.join(goc, "CHANNEL", x, "kenh.yaml")) and not da_tra_kho(goc, x))
    if a.lenh == "xem":
        for k in kenh_ds:
            ok, ly = can_chay(goc, k)
            print("{0:<12} {1:<9} {2}".format(k, "NÊN CHẠY" if ok else "-", ly))
            in_ke_hoach(doc(goc, k))
        return 0
    if len(kenh_ds) != 1:
        print("ke-hoach cần đúng một --kenh")
        return 2
    from .cum_y_nghia import goi_vi  # noqa: PLC0415
    ke, viec = cap_nhat_ke_hoach(goc, kenh_ds[0], goi_vi(goc, print), thu=a.thu)
    print("{0}: {1}".format(kenh_ds[0], viec or "không có gì mới"))
    in_ke_hoach(ke)
    return 0


if __name__ == "__main__":
    sys.exit(main())
