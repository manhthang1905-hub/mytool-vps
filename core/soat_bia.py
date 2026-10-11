"""SOÁT CHỮ ẢNH BÌA — chữ đúng trước khi vẽ, và chữ TRÊN ẢNH đúng y chữ đã soát (12/10/2026).

═══ VÌ SAO CÓ TỆP NÀY ═══

Chẩn đoán 12/10/2026 (`workspace/chan-doan/view-giam-2026-10-12.md`): lứa 08–10/10 hỏng ở "đóng gói" (CTR 48h
1,4–2,5%; trên số của ta, CTR 48h ≥ 3,6% thì 7/8 video nổ, ≤ 3,3% chỉ 1/9). Một lỗi cụ thể: bìa TL1-0021 in
「意かれない / 無意識に意きつける」 — chữ ĐÚNG là 惹かれない / 惹きつける (tiêu đề cùng video viết 惹きつける). Kênh
lấy chữ bìa bằng cách cho AI ĐỌC ảnh bìa đối thủ, AI đọc nhầm 惹 thành 意; mọi cổng sau đều so chữ trên ảnh với
CHÍNH chữ sai ấy nên đều "khớp". Lỗi được nêu từ chẩn đoán 07/10 mà vẫn lên sóng 08/10 (CTR 2,01%).

Hai việc, cả hai đều là LLM đọc NGHĨA (CLAUDE.md §5), máy chỉ so:

1. `soat_chu` — TRƯỚC khi vẽ: một biên tập viên bản ngữ soát chữ bìa so với tiêu đề + đoạn kịch bản (kanji sai /
   đồng âm / giống hình như 意↔惹, okurigana sai, chữ thừa/thiếu, câu không tự nhiên). Sai → sửa ÍT NHẤT, rồi
   một lượt soát lại bản sửa (tối đa `SO_LUOT_SOAT` lượt). `nghi_sai_kanji` là gợi ý MÁY (rẻ, tất định) đưa kèm
   cho biên tập viên: cụm kanji+kana không có trong nguồn mà nguồn có cùng đuôi kana với một kanji khác.
2. `kiem_chu_anh` — SAU khi vẽ: AI đọc MÙ chữ trên ảnh (không được biết chữ mong đợi — biết rồi là "đọc ra" đúng
   chữ mong đợi), ≥ 2 lượt độc lập; máy so TỪNG KÝ TỰ (bỏ dấu câu/khoảng trắng, chuẩn NFKC) với chữ đã soát. Lệch,
   chữ thừa (vết chữ cũ, chữ lạc), ký tự vỡ, vết xoá → TRƯỢT. Hai lượt vênh nhau → lượt thứ ba phân xử.

Không ném lỗi ra ngoài: AI hỏng thì trả `ok`/`dat` = None ("chưa kiểm được") — NƠI GỌI quyết (cổng bìa coi None là
chưa được giao: thử lại sau, không bao giờ coi là đạt). `goi_chat` là hàm chữ của tool:
`goi(loi_nhac, mo_hinh=…, khoa=…, toi_da_token=…, anh=[data url…]) -> str` — bài kiểm truyền hàm giả.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = [
    "TEP_SOAT", "THANG_MO_HINH_CHU", "THANG_MO_HINH_ANH", "SO_LUOT_SOAT", "SO_LAN_DOC",
    "chuan_hoa", "khop_chu", "nghi_sai_kanji", "soat_chu", "doc_anh", "kiem_chu_anh",
    "doc_so", "ghi_so", "van_tay_tep",
]

#: Sổ soát trong `7-thumbnail/` — kết quả theo CHỮ (soát chính tả) và theo ẢNH (đọc chữ trên ảnh): chạy lại
#: khâu không trả tiền lần hai cho cùng một chữ / cùng một ảnh.
TEP_SOAT = "soat-bia.json"
#: Thang mô hình (mạnh trước, `core.bien_tap_content.THANG_MO_HINH` — cùng giá trên ShopAPI). Lượt hỏng / trả
#: rác thì lùi bậc sau.
THANG_MO_HINH_CHU = ("claude-fable-5", "claude-opus-5", "claude-sonnet-5")
THANG_MO_HINH_ANH = ("claude-opus-5", "claude-fable-5", "claude-sonnet-5")
#: Số lượt soát chính tả tối đa cho MỘT chữ (soát → sửa → soát lại bản sửa …).
SO_LUOT_SOAT = 3
#: Số lượt đọc mù độc lập chữ trên ảnh (vênh nhau thì thêm MỘT lượt phân xử).
SO_LAN_DOC = 2
#: Bản sửa chỉ được nhận khi độ dài (đã chuẩn hoá) lệch bản gốc không quá ngần này ký tự — "sửa ít nhất".
LECH_DO_DAI_SUA = 3

_RE_BO = re.compile(r"[\s\W_]+", re.UNICODE)
_KANJI = "一-鿿㐀-䶿々〆"
_RE_TU_KANJI_KANA = re.compile("([" + _KANJI + "]+)([ぁ-ゟ]{2,})")


def chuan_hoa(chu: str) -> str:
    """NFKC (７→7, Ｑ→Q, ｶ→カ) + bỏ khoảng trắng/dấu câu/ký hiệu — CÙNG phép bỏ với `chon_bia._chuan_hoa_chu`,
    nhưng KHÔNG hạ chữ hoa (so từng ký tự)."""
    return _RE_BO.sub("", unicodedata.normalize("NFKC", str(chu or "")))


#: Ký tự THỪA tối đa ở ĐẦU/CUỐI chữ đọc ra mà vẫn coi là khớp: AI đọc ảnh hay "thấy" vệt sáng/tia sáng sát chữ thành
#: 「、、」/「くく」 (đo thật 12/10 trên bìa TL1-0021: Opus đọc 「、、意かれない…」, Sonnet 「くく意かれない…」). Phần
#: chữ mong đợi vẫn phải nằm NGUYÊN VẸN, liền một khối, từng ký tự — 意 thay 惹 là trượt.
THUA_DAU_CUOI_TOI_DA = 2


def khop_chu(doc: str, mong: str) -> bool:
    """Chữ đọc trên ảnh khớp TỪNG KÝ TỰ chữ mong đợi (sau `chuan_hoa`): bằng nhau, hoặc chữ mong đợi nằm nguyên
    khối trong chữ đọc ra và phần thừa ở đầu/cuối ≤ `THUA_DAU_CUOI_TOI_DA` ký tự. Mong đợi rỗng → ảnh phải không
    có chữ."""
    d, m = chuan_hoa(doc), chuan_hoa(mong)
    if d == m:
        return True
    return bool(m) and m in d and len(d) - len(m) <= THUA_DAU_CUOI_TOI_DA


def _goi_json(goi_chat: Callable[..., str], loi_nhac: str, *, thang: Sequence[str], khoa: str,
              anh: Optional[List[str]] = None, toi_da_token: int = 1500) -> Optional[Dict[str, Any]]:
    """Một lượt hỏi AI → dict JSON; lượt hỏng/không ra JSON thì lùi bậc thang mô hình. Hết thang → None."""
    from .goi_van_ban import loc_json  # noqa: PLC0415
    for i, mo_hinh in enumerate(thang or ("",)):
        kw: Dict[str, Any] = {"khoa": "{0}:m{1}".format(khoa, i) if i else khoa, "toi_da_token": toi_da_token}
        if mo_hinh:
            kw["mo_hinh"] = mo_hinh
        if anh:
            kw["anh"] = list(anh)
        try:
            du = loc_json(str(goi_chat(loi_nhac, **kw) or ""))
        except Exception as loi:  # noqa: BLE001 — lỗi mạng/cổng: bậc sau
            if type(loi).__name__ == "Cancelled":  # người bấm Dừng / cổng ngừng nhận — không nuốt
                raise
            continue
        if isinstance(du, dict):
            return du
    return None


# ── 1) Soát chính tả chữ bìa TRƯỚC khi vẽ ─────────────────────────────────────


def nghi_sai_kanji(chu: str, nguon: str, toi_da: int = 6) -> List[Dict[str, str]]:
    """Gợi ý MÁY (chỉ để đưa cho biên tập viên, không tự sửa): cụm KANJI+KANA (≥ 2 kana) trong `chu` mà nguồn
    (tiêu đề + kịch bản) không có, trong khi nguồn có cùng 2 kana đầu của đuôi đó đứng sau một KANJI KHÁC —
    「意きつける」 (nguồn: 惹きつける / 引きつけ) → gợi ý 惹きつける, 引きつける. Chữ không có kanji → []."""
    nguon = str(nguon or "")
    ra: List[Dict[str, str]] = []
    da: set = set()
    for m in _RE_TU_KANJI_KANA.finditer(str(chu or "")):
        tu, kanji, duoi = m.group(0), m.group(1), m.group(2)
        if tu in nguon or (kanji[-1] + duoi[:2]) in nguon:
            continue
        goi_y = []
        for k in re.finditer("([" + _KANJI + "])" + re.escape(duoi[:2]), nguon):
            moi = kanji[:-1] + k.group(1) + duoi
            if k.group(1) != kanji[-1] and moi not in goi_y:
                goi_y.append(moi)
        if goi_y and tu not in da:
            da.add(tu)
            ra.append({"sai": tu, "goi_y": "、".join(goi_y[:3])})
        if len(ra) >= toi_da:
            break
    return ra


LOI_NHAC_SOAT = """You are a meticulous NATIVE {tieng} proofreader for YouTube thumbnail text. The text below will be \
printed HUGE on a thumbnail seen by millions; a single wrong character makes the channel look careless.

Video title: {tieu_de}
Script excerpt (context for the intended meaning):
{ngu_canh}

THUMBNAIL TEXT (a space only marks a line break): 「{chu}」
{goi_y}
Check EVERY character: wrong kanji (homophones or look-alike kanji — e.g. 意 written instead of 惹 in 惹きつける / \
惹かれる), wrong okurigana, typos, missing or extra characters, words that do not exist, broken grammar, phrasing a \
native viewer would find unnatural. Do NOT judge style, hook strength or length — only correctness.
If the text is fully correct return {{"dung": true, "loi": [], "chu_sua": ""}}.
Otherwise fix ONLY the errors with the smallest possible change: same meaning, same length (±2 characters), keep the \
space(s) at the same line break.
Return JSON only: {{"dung": true|false, "loi": [{{"sai": "...", "dung": "...", "ly_do": "one short reason"}}], \
"chu_sua": "<the corrected full text, empty if correct>"}}"""

_TEN_TIENG = {"ja": "Japanese", "ko": "Korean", "zh": "Chinese", "en": "English", "vi": "Vietnamese",
              "es": "Spanish", "pt": "Portuguese", "de": "German", "fr": "French", "th": "Thai",
              "id": "Indonesian"}


def _tieng(ngon_ngu: str) -> str:
    nn = str(ngon_ngu or "ja").strip().lower().split("-")[0].split("_")[0]
    return _TEN_TIENG.get(nn, nn or "Japanese")


def soat_chu(goi_chat: Optional[Callable[..., str]], chu: str, *, tieu_de: str = "", ngu_canh: str = "",
             ngon_ngu: str = "ja", thang: Sequence[str] = THANG_MO_HINH_CHU, khoa: str = "soat-bia",
             so_luot: int = SO_LUOT_SOAT) -> Dict[str, Any]:
    """Soát chính tả chữ bìa `chu`. Trả `{ok, chu, sua, loi, goi_y, so_luot, ly_do}`:

    * `ok` True  — `chu` (bản gốc hoặc bản đã sửa và soát lại ĐẠT) đúng; `sua` = có sửa không;
    * `ok` False — biên tập viên thấy lỗi nhưng không ra được bản sửa soát lại đạt (`chu` = bản gốc);
    * `ok` None  — chưa soát được (không có `goi_chat`, AI hỏng/trả rác ở lượt đầu).
    Mỗi lượt một khoá riêng (`khoa:<lượt>:<hash chữ>`): chữ khác → lượt gọi mới; chạy lại cùng chữ → cùng khoá."""
    goc = " ".join(str(chu or "").split())
    ra: Dict[str, Any] = {"ok": None, "chu": goc, "chu_goc": goc, "sua": False, "loi": [], "so_luot": 0,
                          "goi_y": nghi_sai_kanji(goc, "{0}\n{1}".format(tieu_de, ngu_canh)), "ly_do": ""}
    if not goc:
        ra.update(ok=True, ly_do="không có chữ bìa")
        return ra
    if goi_chat is None:
        ra["ly_do"] = "không có goi_chat"
        return ra
    hien = goc
    for lan in range(max(1, int(so_luot))):
        goi_y = nghi_sai_kanji(hien, "{0}\n{1}".format(tieu_de, ngu_canh))
        dong_goi_y = ""
        if goi_y:
            dong_goi_y = ("Machine check (may be a false alarm — you decide): these words do not appear in the title/"
                          "script, but the same ending appears there with a different kanji: " + "; ".join(
                              "「{0}」 (source has: {1})".format(g["sai"], g["goi_y"]) for g in goi_y) + "\n")
        du = _goi_json(goi_chat, LOI_NHAC_SOAT.format(
            tieng=_tieng(ngon_ngu), tieu_de=tieu_de or "", ngu_canh=(ngu_canh or "")[:2500] or "(none)",
            chu=hien, goi_y=dong_goi_y), thang=thang,
            khoa="{0}:{1}:{2}".format(khoa, lan, hashlib.sha1(hien.encode("utf-8")).hexdigest()[:8]))
        ra["so_luot"] = lan + 1
        if du is None or "dung" not in du:
            if lan == 0:
                ra["ly_do"] = "AI soát chữ không trả lời được"
                return ra
            ra.update(ok=False, chu=goc, sua=False, ly_do="soát lại bản sửa không trả lời được — giữ bản gốc, "
                                                          "coi là CHƯA đúng")
            return ra
        loi = [x for x in (du.get("loi") or []) if isinstance(x, dict)]
        if du.get("dung") is True or (str(du.get("dung")).lower() == "true" and not loi):
            ra.update(ok=True, chu=hien, sua=hien != goc,
                      ly_do="đúng" if hien == goc else "đã sửa → soát lại đạt")
            return ra
        ra["loi"] += [{"sai": str(x.get("sai") or ""), "dung": str(x.get("dung") or ""),
                       "ly_do": str(x.get("ly_do") or "")[:120]} for x in loi][:6]
        moi = " ".join(str(du.get("chu_sua") or "").split()).strip("「」\"' ")
        if not moi or chuan_hoa(moi) == chuan_hoa(hien) or abs(len(chuan_hoa(moi)) - len(chuan_hoa(goc))) > \
                LECH_DO_DAI_SUA:
            ra.update(ok=False, chu=goc, sua=False,
                      ly_do="có lỗi nhưng bản sửa hỏng/khác xa bản gốc: 「{0}」".format(moi[:40]))
            return ra
        hien = moi
    ra.update(ok=False, chu=goc, sua=False, ly_do="sửa {0} lượt vẫn còn lỗi — bản cuối 「{1}」".format(
        so_luot, hien[:40]))
    return ra


# ── 2) Đọc MÙ chữ trên ảnh SAU khi vẽ ────────────────────────────────────────


LOI_NHAC_DOC_ANH = """Read the text printed on this YouTube thumbnail EXACTLY as drawn — character by character, \
like an OCR engine. Do NOT correct anything and do NOT guess what was meant: if a character is a wrong, unusual or \
malformed kanji, write the character you actually SEE. Read the main text line by line, top to bottom.

Also report:
- "chu_thua": every OTHER piece of text or letter-like mark besides the main lines (small stray letters, writing on \
props, watermarks, faint ghost text or outlines left from older text, half-erased characters) — empty list if none;
- "ky_tu_hong": true if any character is broken, cut off by the frame, overlapping another, or not a real character;
- "vet_xoa": true if you see a smudged / blurred patch or a ghost outline where older text seems to have been erased.

Return JSON only: {"dong": ["line 1", "line 2"], "chu_thua": [], "ky_tu_hong": false, "vet_xoa": false}"""


def _data_url(duong: str) -> str:
    """Ảnh → data URL; ảnh lớn hơn 1280×720 thì thu về đúng cỡ đăng (đọc đúng cái người xem thấy)."""
    import base64  # noqa: PLC0415
    from PIL import Image, ImageOps  # noqa: PLC0415
    with Image.open(duong) as im:
        im = im.convert("RGB")
        if im.size != (1280, 720):
            im = ImageOps.fit(im, (1280, 720), method=Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def doc_anh(goi_chat: Callable[..., str], duong: str, *, thang: Sequence[str] = THANG_MO_HINH_ANH,
            khoa: str = "doc-bia") -> Optional[Dict[str, Any]]:
    """MỘT lượt đọc mù → `{chu, dong, chu_thua, ky_tu_hong, vet_xoa}`; None khi AI hỏng/không mở được ảnh."""
    try:
        url = _data_url(duong)
    except (OSError, ValueError):
        return None
    du = _goi_json(goi_chat, LOI_NHAC_DOC_ANH, thang=thang, khoa=khoa, anh=[url])
    if du is None or not isinstance(du.get("dong", []), list):
        return None
    dong = [str(x) for x in (du.get("dong") or []) if str(x).strip()]
    thua = [str(x) for x in (du.get("chu_thua") or []) if str(x).strip()]
    return {"chu": " ".join(dong), "dong": dong, "chu_thua": thua,
            "ky_tu_hong": du.get("ky_tu_hong") is True, "vet_xoa": du.get("vet_xoa") is True}


def _phan_xet(doc: Dict[str, Any], chu_mong: str) -> List[str]:
    """Lý do TRƯỢT của MỘT lượt đọc (rỗng = đạt)."""
    ly: List[str] = []
    if not khop_chu(doc.get("chu", ""), chu_mong):
        ly.append("chữ trên ảnh 「{0}」 ≠ chữ đã soát 「{1}」".format(doc.get("chu", "")[:40], chu_mong[:40]))
    thua = chuan_hoa("".join(doc.get("chu_thua") or []))
    if len(thua) >= 2:
        ly.append("chữ thừa / vết chữ cũ trên ảnh: 「{0}」".format("・".join(doc.get("chu_thua") or [])[:40]))
    if doc.get("ky_tu_hong"):
        ly.append("ký tự vỡ / bị cắt / chồng nhau")
    if doc.get("vet_xoa"):
        ly.append("vết xoá chữ cũ (mảng nhoè / bóng chữ cũ)")
    return ly


def kiem_chu_anh(goi_chat: Optional[Callable[..., str]], duong: str, chu_mong: str, *,
                 so_lan: int = SO_LAN_DOC, thang: Sequence[str] = THANG_MO_HINH_ANH,
                 khoa: str = "doc-bia") -> Dict[str, Any]:
    """Chữ TRÊN ẢNH có đúng y `chu_mong` không — `so_lan` lượt đọc mù độc lập, vênh thì thêm một lượt phân xử,
    theo ĐA SỐ. Trả `{dat: True|False|None, ly_do: [...], doc: [lượt…]}`; `dat=None` = chưa kiểm được (< 2 lượt đọc
    thành công) — nơi gọi KHÔNG được coi là đạt."""
    ra: Dict[str, Any] = {"dat": None, "ly_do": [], "doc": [], "chu_mong": chu_mong}
    if goi_chat is None:
        ra["ly_do"] = ["không có goi_chat"]
        return ra
    so_lan = max(2, int(so_lan))
    phieu: List[List[str]] = []
    lan = 0
    # Ngân sách lượt gọi: `so_lan` lượt + một lượt phân xử + một lượt bù cho lượt hỏng mạng.
    while lan < so_lan + 2:
        if len(phieu) >= so_lan + 1:
            break
        if len(phieu) >= so_lan and all(bool(p) == bool(phieu[0]) for p in phieu):
            break  # các phiếu đồng lòng — khỏi phân xử
        d = doc_anh(goi_chat, duong, thang=thang, khoa="{0}:{1}".format(khoa, lan))
        lan += 1
        if d is None:
            continue
        p = _phan_xet(d, chu_mong)
        ra["doc"].append(dict(d, ly_do=p))
        phieu.append(p)
    if len(phieu) < 2:
        ra["ly_do"] = ["AI đọc ảnh không trả lời đủ ({0}/{1} lượt)".format(len(phieu), so_lan)]
        return ra
    truot = [p for p in phieu if p]
    ra["dat"] = len(truot) * 2 < len(phieu)
    if not ra["dat"]:
        gom: List[str] = []
        for p in truot:
            for x in p:
                if x not in gom:
                    gom.append(x)
        ra["ly_do"] = gom[:4]
    return ra


# ── Sổ soát (cache trong 7-thumbnail/) ────────────────────────────────────────


def doc_so(thu_muc_thumb: str) -> Dict[str, Any]:
    try:
        with io.open(os.path.join(thu_muc_thumb, TEP_SOAT), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {"chu": {}, "anh": {}}
    if not isinstance(du, dict):
        return {"chu": {}, "anh": {}}
    du.setdefault("chu", {})
    du.setdefault("anh", {})
    return du


def ghi_so(thu_muc_thumb: str, du: Dict[str, Any]) -> None:
    try:
        os.makedirs(thu_muc_thumb, exist_ok=True)
        duong = os.path.join(thu_muc_thumb, TEP_SOAT)
        tam = duong + ".tmp"
        with io.open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def van_tay_tep(duong: str) -> str:
    """SHA-1 nội dung tệp (16 ký tự đầu) — khoá sổ cho kết quả đọc ảnh: khác một ký tự trên ảnh là khác tệp."""
    h = hashlib.sha1()
    try:
        with open(duong, "rb") as tep:
            for khoi in iter(lambda: tep.read(1 << 16), b""):
                h.update(khoi)
    except OSError:
        return ""
    return h.hexdigest()[:16]


def bay_gio() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")
