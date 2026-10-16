"""CỔNG CHỮ ĐÚNG — không tấm bìa nào sai chữ được rời máy (16/10/2026).

═══ VÌ SAO ═══

TL1-T7 sụp từ 07/10 (hiển thị 370–1.900/video, CTR 1,3–3,4%). Soi bìa THẬT trên YouTube: bìa 0021 in 「意かれない／無意識に
意きつける」 (đúng: 惹), bìa 0026 in 「本当に地頭がいい人の 変わった 変わった」 (chữ bìa: 「…変わったクセ10選」 — mô hình ảnh tự
vẽ chữ và vẽ hỏng). Cả hai qua giám khảo với điểm thấp; không bước nào bắt buộc CHỮ TRÊN ẢNH phải trùng CHỮ ĐÃ SOÁT. Chủ
dự án 16/10: *"việc bìa bị sai chữ là tối kỵ"* — chấm chặt, không dung sai.

═══ BA LỚP ═══

1. CHỮ BÌA đúng trước khi vẽ (`soat_chat`, `chot_chu`): biên tập viên LLM soát (`soat_bia.soat_chu`: kanji sai / đồng âm
   / giống hình, chữ thừa/thiếu/lặp, câu không tự nhiên → bản sửa + danh sách lỗi), rồi MÁY kiểm: mọi kanji (và cụm
   kanji+kana) không có trong tiêu đề/kịch bản phải được biên tập viên XÁC NHẬN từng mục (`can_xac_nhan`). Không sửa
   được → viết lại chữ bìa (`viet_lai`) rồi soát lại từ đầu.
   16/10/2026 (TL3-T7-0017: chữ bìa hồ sơ là chữ bìa ĐỐI THỦ chép nguyên văn từ `0-bia-doi-thu.txt`, lạc đề video) —
   thêm hai kiểm TRƯỚC khi vẽ, trượt = viết lại: (a) KHÔNG CHÉP (`kiem_chep`): trùng tuyệt đối / chứa trọn / `do_trung`
   cửa sổ 3 ký tự > `NGUONG_CHEP_BIA` so chữ bìa đối thủ (`chu_bia_doi_thu`); (b) ĐÚNG CHỦ ĐỀ (`kiem_chu_de`): LLM xét
   chữ với tiêu đề + kịch bản, trả có/không + lý do (AI hỏng → None: giữ, thử lại).
2. ẢNH đạt/trượt, không phải điểm (`kiem_anh`): HAI lượt đọc mù ĐỘC LẬP (hai mô hình đứng đầu khác nhau qua phễu chung
   `goi_van_ban`) chép chữ TRÊN ẢNH đúng như vẽ; sau NFKC + bỏ khoảng trắng/xuống dòng/dấu câu, MỖI lượt phải BẰNG
   ĐÚNG chữ đã soát — thiếu, thừa, lặp, khác một ký tự, chữ lạc, ký tự vỡ, vết xoá → TRƯỢT. Hai lượt vênh nhau → TRƯỢT.
   Lượt AI hỏng → CHƯA kiểm (None) — nơi gọi giữ bìa, thử lại; KHÔNG BAO GIỜ coi là đạt.
3. DẤU (`ghi_dau`/`kiem_dau`): tệp đạt được đóng dấu vào báo cáo cạnh ảnh `<tên>.do-bia.json` →
   `chu_khop: {ok, sha1, chu, luc, doc, soat}` (+ `chu_khop_ds` theo sha1 — `CHON-thumb_N.jpg` và `thumb_N.*` dùng chung
   một báo cáo). MỌI cửa ra YouTube (`vm/may_dang_dom.py` lúc đăng + `--sua-video`, `do_bia.xep_doi_bia`, máy A/B
   `core/studio_may.py` + `vm/studio_may_dom.py`) từ chối tệp không có dấu hợp lệ trùng sha1 của chính tệp đó.

Bản chép/xuất lại DO MÃ làm (`chon_bia._xuat_jpg`, bản tải lên chuẩn) mang theo dấu (`chuyen_dau`: cùng sha1, hoặc
vân tay ảnh gần như trùng). Hết tấm có dấu → bìa dự phòng chữ VẼ BẰNG MÃ trên nền sạch (`ve_bia_ma`, `bia_ma_du_phong`)
rồi cũng đọc lại hai lượt mới được dấu. Mọi kết quả ghi não bộ phận "bia".

    python -X utf8 -m core.cong_chu dau <tệp> --chu "<chữ bìa>" [--kenh K --ma K-0001]   # soát chữ + đọc 2 lượt + dấu
    python -X utf8 -m core.cong_chu kiem <tệp>                                          # chỉ đọc dấu (không gọi AI)
    python -X utf8 -m core.cong_chu dau-goi [--kenh K]     # gói chờ đăng chưa có dấu → dấu / bìa dự phòng / giữ (skill S05)
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

__all__ = ["chuan", "khop", "can_xac_nhan", "soat_chat", "viet_lai", "chot_chu", "xet_doc", "kiem_anh", "ghi_dau",
           "chu_bia_doi_thu", "kiem_chep", "kiem_chu_de", "viet_chu_bia_rieng",
           "doc_dau", "kiem_dau", "chuyen_dau", "xac_minh", "bao_dam_ma", "ve_bia_ma", "tim_nen_sach",
           "bia_ma_du_phong", "ghi_nao", "tom_tat_dau", "ChuKhongKhop", "anh_goi", "goi_cho_dang", "dau_goi",
           "dau_cac_goi"]

#: Phiên bản luật cổng — kết quả soát/dấu của luật cũ (khớp lỏng ≤2 ký tự thừa, đa số phiếu) không được dùng lại.
PHIEN_BAN = 2
#: Phiên bản luật SOÁT CHỮ (chỉ sổ soát `soat-bia.json`, không đụng dấu ảnh): 3 = thêm kiểm chép chữ bìa đối thủ + kiểm
#: đúng chủ đề (16/10/2026) — kết quả soát luật cũ soát lại.
PHIEN_SOAT = 3
#: Chữ bìa CHÉP chữ bìa đối thủ (16/10/2026 — TL3-T7-0017 in nguyên chữ bìa đối thủ, lạc đề với video): tỉ lệ cửa sổ
#: `N_CHEP_BIA` ký tự (`do_doc_dao.do_trung`) trên ngưỡng này, hoặc trùng / chứa trọn → trượt, viết lại.
NGUONG_CHEP_BIA = 0.6
N_CHEP_BIA = 3
#: Chữ đọc từ ảnh bìa đối thủ (`auto_khau`, từ 16/10/2026) và tả bố cục bìa đối thủ (có trích từng dòng chữ).
TEP_CHU_BIA_DOI_THU = "0-chu-bia-doi-thu.txt"
TEP_BIA_DOI_THU = "0-bia-doi-thu.txt"
SO_LAN_DOC = 2
#: Hai lượt đọc ĐỘC LẬP: mô hình đứng đầu khác nhau (lượt hỏng thì lùi bậc sau của chính thang đó).
THANG_DOC = (("claude-opus-5", "claude-fable-5", "claude-sonnet-5"),
             ("claude-fable-5", "claude-opus-5", "claude-sonnet-5"))
#: Bản xuất lại do mã (jpg nén lại / cắt về 1280×720) mang dấu khi vân tay ảnh lệch dưới ngần này (cùng bức).
LECH_VAN_TAY_CHUYEN = 4.0
SO_DAU_GIU = 12
SO_LAN_VIET_LAI = 2
SO_NEN_DU_PHONG = 3
#: Chữ viết lại: khung số ký tự (đếm sau `chuan`).
CHU_MOI_TOI_THIEU, CHU_MOI_TOI_DA = 8, 18

_KANJI = "一-鿿㐀-䶿々〆"
_RE_KANJI = re.compile("[" + _KANJI + "]")
_RE_TU_KANJI_KANA = re.compile("([" + _KANJI + "]+)([ぁ-ゟ]{2,})")
_RE_CHU_THAT = re.compile(r"[0-9A-Za-z$%¥€£぀-ヿ㐀-鿿가-힯]")


class ChuKhongKhop(RuntimeError):
    """Bộ vẽ không bảo đảm vẽ đúng chữ đã soát (chữ bị cắt / phông thiếu nét) — lô bìa không được làm."""


#: Ký tự trông như nhau mà NFKC không gộp: vòng tròn che chữ 「◯◯歳」 (ký hiệu — bị bỏ) ↔ 「〇〇歳」 (chữ số — giữ).
_TUONG_DUONG = str.maketrans({"◯": "〇", "○": "〇", "⭕": "〇"})


def chuan(chu: Any) -> str:
    """NFKC + bỏ khoảng trắng, xuống dòng, dấu câu, ký hiệu (cùng phép với `soat_bia.chuan_hoa`); ◯/○ = 〇."""
    from .soat_bia import chuan_hoa  # noqa: PLC0415
    return chuan_hoa(str(chu or "").translate(_TUONG_DUONG))


def khop(doc: Any, mong: Any) -> bool:
    """KHỚP TUYỆT ĐỐI: sau `chuan` hai chuỗi bằng nhau từng ký tự (không dung sai thừa/thiếu/lặp)."""
    return chuan(doc) == chuan(mong)


def sha1_tep(duong: str) -> str:
    h = hashlib.sha1()  # noqa: S324 — nhận diện tệp, không mật mã
    try:
        with open(duong, "rb") as tep:
            for khoi in iter(lambda: tep.read(1 << 16), b""):
                h.update(khoi)
    except OSError:
        return ""
    return h.hexdigest()


def _luc() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


# ── 1) Chữ bìa đúng TRƯỚC khi vẽ ─────────────────────────────────────────────


def can_xac_nhan(chu: str, nguon: str) -> List[str]:
    """Mục MÁY bắt phải được biên tập viên xác nhận: mọi KANJI không có trong tiêu đề/kịch bản, và mọi cụm KANJI+KANA
    (≥ 2 kana) mà "kanji cuối + 2 kana đầu" không có trong nguồn (「意かれない」 khi nguồn chỉ có 惹きつける — từng
    kanji 意 lại có trong 無意識)."""
    s, n = unicodedata.normalize("NFKC", str(chu or "")), unicodedata.normalize("NFKC", str(nguon or ""))
    ra: List[str] = []
    for c in s:
        if _RE_KANJI.match(c) and c not in n and c not in ra:
            ra.append(c)
    for m in _RE_TU_KANJI_KANA.finditer(s):
        tu, kanji, duoi = m.group(0), m.group(1), m.group(2)
        if tu not in n and (kanji[-1] + duoi[:2]) not in n and tu not in ra:
            ra.append(tu)
    return ra


LOI_NHAC_XAC_NHAN = """You are a meticulous NATIVE {tieng} proofreader. This text will be printed HUGE on a YouTube \
thumbnail; one wrong character is unacceptable.

Video title: {tieu_de}
Script excerpt (context for the intended meaning):
{ngu_canh}

THUMBNAIL TEXT (a space only marks a line break): 「{chu}」

A machine check flagged these characters / words because they do NOT appear anywhere in the title or the script: {muc}
For EACH flagged item decide whether it is exactly the right character / word for the intended meaning — not a \
homophone, not a look-alike kanji (e.g. 意 written instead of 惹 in 惹きつける / 惹かれる), not a typo.
"dung" is true only if EVERY flagged item is correct.
If any item is wrong, "chu_sua" is the full corrected text (smallest change, same length ±2, keep the space at the same \
line break); otherwise "chu_sua" is "".
Return JSON only: {{"dung": true|false, "xac_nhan": [{{"muc": "...", "dung": true|false, "ly_do": "short"}}], \
"chu_sua": ""}}"""


def _tieng(ngon_ngu: str) -> str:
    from .soat_bia import _tieng as t  # noqa: PLC0415
    return t(ngon_ngu)


def _doc_tep(duong: str) -> str:
    try:
        with io.open(duong, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


_RE_TRICH = re.compile(r"['‘\"“「『]([^'’\"”」』\n]{2,40})['’\"”」』]")
_RE_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")


def chu_bia_doi_thu(thu_muc_luot: str) -> List[str]:
    """Chữ trên bìa ĐỐI THỦ của một lượt: `0-chu-bia-doi-thu.txt` (chữ đọc từ ảnh, ghi từ 16/10/2026) + các dòng chữ
    trích trong ngoặc của `0-bia-doi-thu.txt` (tả bố cục — mục TEXT PLACEMENT chép nguyên văn từng dòng chữ), từng dòng
    và cả khối ghép. Không có → []."""
    if not thu_muc_luot:
        return []
    ra: List[str] = []
    t = " ".join(_doc_tep(os.path.join(thu_muc_luot, TEP_CHU_BIA_DOI_THU)).split())
    if t:
        ra.append(t)
    dong = [x.strip() for x in _RE_TRICH.findall(_doc_tep(os.path.join(thu_muc_luot, TEP_BIA_DOI_THU)))
            if len(_RE_CJK.findall(x)) >= 2]
    dong = list(dict.fromkeys(dong))
    if dong:
        ra.append(" ".join(dong))
        ra += dong
    return list(dict.fromkeys(x for x in ra if chuan(x)))


def kiem_chep(chu: str, doi_thu: Sequence[str] = (), *, nguong: float = NGUONG_CHEP_BIA, n: int = N_CHEP_BIA) -> str:
    """'' = chữ KHÔNG chép chữ bìa đối thủ; khác → lý do. Trượt khi trùng tuyệt đối, chứa trọn (≥ 6 ký tự), hoặc tỉ lệ
    cửa sổ `n` ký tự có y nguyên trong chữ đối thủ (`do_doc_dao.do_trung`) > `nguong`."""
    a = chuan(chu)
    ds = [x for x in (doi_thu or ()) if chuan(x)]
    if len(a) < 2 or not ds:
        return ""
    for x in ds:
        b = chuan(x)
        if a == b or (len(a) >= 6 and a in b):
            return "chữ bìa 「{0}」 trùng nguyên văn chữ bìa đối thủ 「{1}」".format(str(chu)[:30], str(x)[:30])
    from .do_doc_dao import do_trung  # noqa: PLC0415
    ti = max(do_trung(chu, x, n=n)["ti_le"] for x in ds)
    if ti > nguong:
        return "chữ bìa 「{0}」 chép chữ bìa đối thủ ({1:.0%} chuỗi {2} ký tự trùng, ngưỡng {3:.0%})".format(
            str(chu)[:30], ti, n, nguong)
    return ""


LOI_NHAC_CHU_DE = """You check that the {loai} of a {tieng} psychology YouTube video matches THIS video.

Video title: {tieu_de}
Script excerpt (what the video really says):
{ngu_canh}

{LOAI} TO CHECK: 「{chu}」

"hop" is true only if the text is about the SAME topic as this video (its main subject, and a promise the video keeps).
It is false if it talks about a different subject, promises something the video does not cover, or reads like text \
copied from another video. Do NOT judge style, spelling, length or hook strength.
Return JSON only: {{"hop": true|false, "ly_do": "one short reason"}}"""


def kiem_chu_de(goi: Optional[Callable[..., str]], chu: str, *, tieu_de: str = "", ngu_canh: str = "",
                ngon_ngu: str = "ja", loai: str = "bia", thang: Sequence[str] = (), khoa: str = "chu-de"
                ) -> Dict[str, Any]:
    """LLM xét chữ (bìa / tiêu đề) có ĐÚNG CHỦ ĐỀ video không → `{hop: True|False|None, ly_do}`. Không có tiêu đề lẫn
    kịch bản → True (không có gì để so; ghi lý do). AI hỏng / trả lạc → None (nơi gọi giữ, thử lại)."""
    if not (str(tieu_de or "").strip() or str(ngu_canh or "").strip()):
        return {"hop": True, "ly_do": "không có tiêu đề / kịch bản để so chủ đề"}
    if goi is None:
        return {"hop": None, "ly_do": "không có hàm gọi AI"}
    from . import soat_bia  # noqa: PLC0415
    ten = "YouTube title" if loai == "tieu_de" else "thumbnail text"
    du = soat_bia._goi_json(goi, LOI_NHAC_CHU_DE.format(  # noqa: SLF001
        loai=ten, LOAI=ten.upper(), tieng=_tieng(ngon_ngu), tieu_de=tieu_de or "(none)",
        ngu_canh=(ngu_canh or "")[:2500] or "(none)", chu=" ".join(str(chu or "").split())),
        thang=tuple(thang) or soat_bia.THANG_MO_HINH_CHU, toi_da_token=400,
        khoa="{0}:{1}".format(khoa, hashlib.sha1(chuan(chu).encode("utf-8")).hexdigest()[:8]))
    h = (du or {}).get("hop")
    hop = h if isinstance(h, bool) else {"true": True, "false": False}.get(str(h).strip().lower())
    return {"hop": hop, "ly_do": " ".join(str((du or {}).get("ly_do") or ("AI xét chủ đề không trả lời" if hop is None
                                                                          else "")).split())[:200]}


def soat_chat(goi: Optional[Callable[..., str]], chu: str, *, tieu_de: str = "", ngu_canh: str = "",
              ngon_ngu: str = "ja", khoa: str = "soat-bia", thang: Sequence[str] = (), so_vong: int = 2,
              doi_thu: Sequence[str] = (), chu_de: bool = True, loai: str = "bia") -> Dict[str, Any]:
    """Soát CHẶT chữ bìa (`loai="tieu_de"`: một tiêu đề — cùng luật): (1) KHÔNG CHÉP chữ đối thủ (`kiem_chep` với
    `doi_thu`, không gọi AI); (2) chính tả `_soat_chinh_ta`; (3) ĐÚNG CHỦ ĐỀ (`kiem_chu_de`, `chu_de=False` bỏ). Trả như
    `soat_bia.soat_chu` + `{phien, can_xac_nhan, xac_nhan, chep_doi_thu, chu_de, viet_lai_vi}`: `ok` True = chữ (`chu`,
    có thể đã sửa) đúng; False = sai mà không sửa được (nơi gọi viết lại — lý do ở `viet_lai_vi`); None = chưa soát
    được (AI hỏng — nơi gọi giữ, thử lại)."""
    goc_chu = " ".join(str(chu or "").split())
    ly = kiem_chep(goc_chu, doi_thu)
    if ly:
        return {"ok": False, "chu": goc_chu, "chu_goc": goc_chu, "sua": False, "loi": [], "goi_y": [], "so_luot": 0,
                "ly_do": ly, "phien": PHIEN_SOAT, "can_xac_nhan": [], "xac_nhan": [], "chep_doi_thu": True,
                "viet_lai_vi": ly + " — viết chữ RIÊNG của video, không dùng lại chữ bìa đối thủ"}
    r = _soat_chinh_ta(goi, goc_chu, tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, khoa=khoa, thang=thang,
                       so_vong=so_vong)
    r["phien"] = PHIEN_SOAT
    if r.get("ok") is not True:
        return r
    if r.get("sua"):
        ly = kiem_chep(r["chu"], doi_thu)
        if ly:
            r.update(ok=False, sua=False, chu=r.get("chu_goc") or goc_chu, ly_do=ly, chep_doi_thu=True,
                     viet_lai_vi=ly)
            return r
    if not chu_de or not chuan(r.get("chu")):
        return r
    c = kiem_chu_de(goi, r["chu"], tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, loai=loai, thang=thang,
                    khoa=khoa + ":chu-de")
    r["chu_de"] = c
    if c["hop"] is None:
        r.update(ok=None, ly_do="chưa xét được chữ có đúng chủ đề video không: " + c["ly_do"])
    elif c["hop"] is False:
        ly = "chữ 「{0}」 không đúng chủ đề video: {1}".format(str(r["chu"])[:30], c["ly_do"])
        r.update(ok=False, sua=False, chu=r.get("chu_goc") or goc_chu, ly_do=ly,
                 viet_lai_vi=ly + " — viết chữ đúng chủ đề tiêu đề + kịch bản")
    return r


def _soat_chinh_ta(goi: Optional[Callable[..., str]], chu: str, *, tieu_de: str = "", ngu_canh: str = "",
                   ngon_ngu: str = "ja", khoa: str = "soat-bia", thang: Sequence[str] = (), so_vong: int = 2
                   ) -> Dict[str, Any]:
    """Soát CHÍNH TẢ chặt: `soat_bia.soat_chu` (biên tập viên LLM soát + sửa ít nhất + soát lại bản sửa), rồi mọi mục
    `can_xac_nhan` phải được xác nhận ĐÚNG; mục bị bác → bản sửa của biên tập viên đi soát lại từ đầu (≤ `so_vong`)."""
    from . import soat_bia  # noqa: PLC0415
    thang = tuple(thang) or soat_bia.THANG_MO_HINH_CHU
    nguon = "{0}\n{1}".format(tieu_de or "", ngu_canh or "")
    r = soat_bia.soat_chu(goi, chu, tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, thang=thang, khoa=khoa)
    r.update(phien=PHIEN_BAN, can_xac_nhan=[], xac_nhan=[])
    goc_dai = len(chuan(r.get("chu_goc") or chu))
    for vong in range(max(1, int(so_vong))):
        if r.get("ok") is not True:
            return r
        muc = can_xac_nhan(r["chu"], nguon)
        r["can_xac_nhan"] = muc
        if not muc:
            return r
        du = soat_bia._goi_json(goi, LOI_NHAC_XAC_NHAN.format(  # noqa: SLF001
            tieng=_tieng(ngon_ngu), tieu_de=tieu_de or "", ngu_canh=(ngu_canh or "")[:2500] or "(none)",
            chu=r["chu"], muc="、".join("「{0}」".format(x) for x in muc)), thang=thang,
            khoa="{0}:xn{1}:{2}".format(khoa, vong, hashlib.sha1(r["chu"].encode("utf-8")).hexdigest()[:8]))
        if du is None or "dung" not in du:
            r.update(ok=None, ly_do="AI xác nhận kanji không trả lời — chưa soát xong")
            return r
        bac = [x for x in (du.get("xac_nhan") or []) if isinstance(x, dict) and x.get("dung") is False]
        if du.get("dung") is True and not bac:
            r["xac_nhan"] = muc
            return r
        r["loi"] = list(r.get("loi") or []) + [{"sai": str(x.get("muc") or ""), "dung": "", "ly_do": str(
            x.get("ly_do") or "")[:120]} for x in bac][:6]
        moi = " ".join(str(du.get("chu_sua") or "").split()).strip("「」\"' ")
        if not moi or chuan(moi) == chuan(r["chu"]) or abs(len(chuan(moi)) - goc_dai) > 3:
            r.update(ok=False, sua=False, chu=r.get("chu_goc") or chu,
                     ly_do="kanji không có trong tiêu đề/kịch bản bị bác ({0}) mà không có bản sửa dùng được".format(
                         "、".join(muc)[:60]))
            return r
        r2 = soat_bia.soat_chu(goi, moi, tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, thang=thang,
                               khoa=khoa + ":xs{0}".format(vong))
        if r2.get("ok") is not True:
            r.update(ok=r2.get("ok"), sua=False, chu=r.get("chu_goc") or chu,
                     ly_do="bản sửa kanji 「{0}」 soát lại không đạt: {1}".format(moi[:30], r2.get("ly_do")))
            return r
        r.update(chu=r2["chu"], sua=True, ly_do="đã sửa kanji → soát lại")
    r.update(ok=False, sua=False, chu=r.get("chu_goc") or chu, ly_do="sửa {0} vòng vẫn còn kanji bị bác".format(so_vong))
    return r


LOI_NHAC_VIET_LAI = """You write the text printed HUGE on a YouTube thumbnail of a {tieng} psychology video.

Video title: {tieu_de}
Script excerpt:
{ngu_canh}

The previous thumbnail text 「{chu_cu}」 was REJECTED by the proofreader: {ly_do}
Write ONE new thumbnail text with the same curiosity hook: {n_min}-{n_max} characters (spaces and punctuation not \
counted), written as TWO short parts separated by one space, natural {tieng}, every character correct, and use ONLY \
kanji that appear in the title or the script above. Never copy the full title or another video's thumbnail text.
Reply with ONLY one line: THUMB: <text>"""


def viet_lai(goi: Optional[Callable[..., str]], chu_cu: str, *, tieu_de: str = "", ngu_canh: str = "",
             ngon_ngu: str = "ja", ly_do: str = "", khoa: str = "viet-lai-bia", lan: int = 0,
             mo_hinh: str = "claude-opus-5") -> str:
    """MỘT lượt viết lại chữ bìa (khi chữ cũ sai mà không sửa được). Hỏng / ngoài khung → ''."""
    if goi is None:
        return ""
    try:
        tra = goi(LOI_NHAC_VIET_LAI.format(tieng=_tieng(ngon_ngu), tieu_de=tieu_de or "",
                                           ngu_canh=(ngu_canh or "")[:2500] or "(none)", chu_cu=chu_cu,
                                           ly_do=(ly_do or "wrong character")[:200], n_min=CHU_MOI_TOI_THIEU,
                                           n_max=CHU_MOI_TOI_DA),
                  mo_hinh=mo_hinh, khoa="{0}:{1}".format(khoa, lan), toi_da_token=300)
    except Exception as loi:  # noqa: BLE001
        if type(loi).__name__ == "Cancelled":
            raise
        return ""
    m = re.search(r"THUMB\s*[:：]\s*(.+)", str(tra or ""))
    moi = " ".join((m.group(1) if m else "").split()).strip("「」\"' ")
    return moi if CHU_MOI_TOI_THIEU <= len(chuan(moi)) <= CHU_MOI_TOI_DA + 2 else ""


def ly_do_viet_lai(r: Dict[str, Any]) -> str:
    """Lý do đưa cho lượt viết lại: lỗi chép / lạc chủ đề (`viet_lai_vi`) > các lỗi chính tả > `ly_do`."""
    return str(r.get("viet_lai_vi") or "") or "; ".join(
        "{0}→{1}".format(x.get("sai"), x.get("dung")) for x in r.get("loi") or []) or str(r.get("ly_do") or "")


LOI_NHAC_CHU_RIENG = """You write the text printed HUGE on a YouTube thumbnail of a {tieng} psychology video.

Video title: {tieu_de}
Source / script excerpt (what the video covers):
{ngu_canh}

A competitor's thumbnail for a similar video says 「{chu_doi_thu}」. Use it ONLY as an example of hook style: do NOT \
reuse its wording, and do NOT take its topic if it differs from the title above.
Write ONE thumbnail text for THIS video: {n_min}-{n_max} characters (spaces and punctuation not counted), two short \
parts separated by one space, natural {tieng}, every character correct, about the same topic as the title, using ONLY \
kanji that appear in the title or the excerpt. Never copy the full title.
Reply with ONLY one line: THUMB: <text>"""


def viet_chu_bia_rieng(goi: Optional[Callable[..., str]], *, tieu_de: str, ngu_canh: str = "", chu_doi_thu: str = "",
                       ngon_ngu: str = "ja", khoa: str = "chu-bia-rieng", mo_hinh: str = "claude-opus-5") -> str:
    """16/10/2026 — gốc lỗi TL3-T7-0017: kênh `nguyen_goc` lấy THẲNG chữ đọc từ bìa đối thủ làm chữ bìa. Nay chữ ấy chỉ
    là mẫu móc câu: MỘT lượt viết chữ bìa RIÊNG theo tiêu đề của video. Hỏng / ngoài khung / vẫn chép đối thủ → ''."""
    if goi is None or not str(tieu_de or "").strip():
        return ""
    try:
        tra = goi(LOI_NHAC_CHU_RIENG.format(tieng=_tieng(ngon_ngu), tieu_de=tieu_de, ngu_canh=(ngu_canh or "")[:2500]
                                            or "(none)", chu_doi_thu=" ".join(str(chu_doi_thu or "").split()) or "-",
                                            n_min=CHU_MOI_TOI_THIEU, n_max=CHU_MOI_TOI_DA),
                  mo_hinh=mo_hinh, khoa=khoa, toi_da_token=300)
    except Exception as loi:  # noqa: BLE001
        if type(loi).__name__ == "Cancelled":
            raise
        return ""
    m = re.search(r"THUMB\s*[:：]\s*(.+)", str(tra or ""))
    moi = " ".join((m.group(1) if m else "").split()).strip("「」\"' ")
    if not CHU_MOI_TOI_THIEU <= len(chuan(moi)) <= CHU_MOI_TOI_DA + 2:
        return ""
    if chu_doi_thu and kiem_chep(moi, [chu_doi_thu]):
        return ""
    return moi


def chot_chu(goi: Optional[Callable[..., str]], chu: str, *, tieu_de: str = "", ngu_canh: str = "",
             ngon_ngu: str = "ja", khoa: str = "soat-bia", thang: Sequence[str] = (),
             so_lan_viet_lai: int = SO_LAN_VIET_LAI, doi_thu: Sequence[str] = ()) -> Dict[str, Any]:
    """`soat_chat`; sai mà không sửa được (chính tả / chép chữ đối thủ / lạc chủ đề) → `viet_lai` + soát lại (≤
    `so_lan_viet_lai`). Trả kết quả soát cuối + `viet_lai` (chữ mới hay không) + `lich_su`. `ok` None = AI hỏng (giữ,
    thử lại)."""
    r = soat_chat(goi, chu, tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, khoa=khoa, thang=thang,
                  doi_thu=doi_thu)
    lich = [{"chu": chu, "ok": r.get("ok"), "ly_do": r.get("ly_do")}]
    for lan in range(max(0, int(so_lan_viet_lai))):
        if r.get("ok") is not False:
            break
        moi = viet_lai(goi, r.get("chu_goc") or chu, tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu,
                       ly_do=ly_do_viet_lai(r), khoa=khoa + ":viet-lai", lan=lan)
        if not moi:
            lich.append({"chu": "", "ok": None, "ly_do": "viết lại hỏng / ngoài khung"})
            continue
        r = soat_chat(goi, moi, tieu_de=tieu_de, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, khoa=khoa + ":vl", thang=thang,
                      doi_thu=doi_thu)
        lich.append({"chu": moi, "ok": r.get("ok"), "ly_do": r.get("ly_do")})
        if r.get("ok") is True:
            r.update(sua=True, viet_lai=True, chu_goc=chu)
    r["lich_su"] = lich
    r.setdefault("viet_lai", False)
    return r


# ── 2) Chữ TRÊN ẢNH: đạt / trượt ─────────────────────────────────────────────


def _chu_lac(chu_thua: Sequence[Any]) -> str:
    """Chữ LẠC thật trong mục `chu_thua` của lượt đọc (bỏ câu tả dài, phần trong ngoặc, dấu sao nhà cung cấp)."""
    ra: List[str] = []
    for x in chu_thua or []:
        x = re.sub(r"\(.*?\)|（.*?）", "", str(x)).strip()
        if not x or re.search(r"sparkle|watermark|✦|^no\b|^none\b", x, re.I):
            continue
        trich = re.findall(r"[\"“「『](.+?)[\"”」』]", x)
        ra += trich or ([x] if len(x) <= 15 else [])
    return " ".join(s for s in ra if _RE_CHU_THAT.search(s)).strip()


def xet_doc(d: Dict[str, Any], mong: str) -> List[str]:
    """Lý do TRƯỢT của MỘT lượt đọc (rỗng = đạt): chữ chính phải BẰNG ĐÚNG chữ đã soát; chữ lạc, ký tự vỡ, vết xoá."""
    ly: List[str] = []
    if not chuan(mong):
        ly.append("không có chữ đã soát để so")
    elif not khop(d.get("chu", ""), mong):
        ly.append("chữ trên ảnh 「{0}」 ≠ chữ đã soát 「{1}」".format(str(d.get("chu", ""))[:40], str(mong)[:40]))
    la = _chu_lac(d.get("chu_thua") or [])
    if la:
        ly.append("chữ thừa trên ảnh: 「{0}」".format(la[:40]))
    if d.get("ky_tu_hong"):
        ly.append("ký tự vỡ / bị cắt / chồng nhau")
    if d.get("vet_xoa"):
        ly.append("vết xoá chữ cũ")
    return ly


def kiem_anh(goi: Optional[Callable[..., str]], tep: str, mong: str, *, khoa: str = "cong-chu",
             so_lan: int = SO_LAN_DOC, thang: Sequence[Sequence[str]] = THANG_DOC) -> Dict[str, Any]:
    """`so_lan` (≥ 2) lượt đọc mù ĐỘC LẬP; MỌI lượt phải khớp tuyệt đối. Một lượt trượt → `ok` False (dừng ngay — hai
    lượt vênh nhau là trượt). Thiếu lượt trả lời (AI hỏng) mà chưa lượt nào trượt → `ok` None (chưa kiểm được).
    Trả `{ok, doc: [lượt…], ly_do, chu}`."""
    from . import soat_bia  # noqa: PLC0415
    ra: Dict[str, Any] = {"ok": None, "doc": [], "ly_do": [], "chu": mong}
    if goi is None:
        ra["ly_do"] = ["không có hàm gọi AI"]
        return ra
    so_lan = max(2, int(so_lan))
    sha = sha1_tep(tep)
    if not sha:
        ra.update(ok=False, ly_do=["không đọc được tệp ảnh"])
        return ra
    for i in range(so_lan):
        d = soat_bia.doc_anh(goi, tep, thang=tuple(thang[i % len(thang)]), khoa="{0}:{1}:{2}".format(khoa, sha[:12], i))
        if d is None:
            ra["ly_do"].append("lượt đọc {0} không trả lời".format(i + 1))
            continue
        p = xet_doc(d, mong)
        ra["doc"].append(dict(d, ly_do=p))
        if p:
            ra.update(ok=False, ly_do=p)
            return ra
    if len(ra["doc"]) >= so_lan:
        ra.update(ok=True, ly_do=[])
    return ra


# ── 3) Dấu ───────────────────────────────────────────────────────────────────


def duong_dau(tep: str) -> str:
    from .do_bia import duong_bao_cao  # noqa: PLC0415
    return duong_bao_cao(tep)


def _doc_json(duong: str) -> Dict[str, Any]:
    try:
        with io.open(duong, encoding="utf-8") as f:
            du = json.load(f)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_dau(tep: str, chu: str, *, doc: Sequence[str] = (), cach: str = "doc2", tu: str = "", soat: bool = True
            ) -> Dict[str, Any]:
    """Đóng dấu ĐẠT cho đúng tệp `tep` (sha1 hiện tại) vào báo cáo cạnh ảnh. Giữ mọi khoá khác của báo cáo."""
    sha = sha1_tep(tep)
    if not sha:
        return {}
    dau = {"ok": True, "sha1": sha, "chu": " ".join(str(chu or "").split()), "chu_chuan": chuan(chu), "luc": _luc(),
           "tep": os.path.basename(tep), "doc": [str(x)[:80] for x in doc][:4], "cach": cach, "soat": bool(soat),
           "phien": PHIEN_BAN}
    if tu:
        dau["tu"] = tu
    duong = duong_dau(tep)
    du = _doc_json(duong)
    ds = du.get("chu_khop_ds") if isinstance(du.get("chu_khop_ds"), dict) else {}
    ds[sha] = dau
    while len(ds) > SO_DAU_GIU:
        ds.pop(next(iter(ds)))
    du.update(chu_khop=dau, chu_khop_ds=ds)
    try:
        os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
        with io.open(duong + ".tmp", "w", encoding="utf-8") as f:
            json.dump(du, f, ensure_ascii=False)
        os.replace(duong + ".tmp", duong)
    except OSError:
        return {}
    return dau


def doc_dau(tep: str) -> Optional[Dict[str, Any]]:
    """Dấu của ĐÚNG tệp này (theo sha1 nội dung) — None khi không có."""
    sha = sha1_tep(tep)
    if not sha:
        return None
    du = _doc_json(duong_dau(tep))
    ds = du.get("chu_khop_ds") if isinstance(du.get("chu_khop_ds"), dict) else {}
    d = ds.get(sha) or (du.get("chu_khop") if isinstance(du.get("chu_khop"), dict) else None)
    return d if isinstance(d, dict) and d.get("sha1") == sha else None


def kiem_dau(tep: str, chu: str = "") -> str:
    """'' = tệp có dấu cổng chữ HỢP LỆ (đạt, đúng sha1 nội dung, luật hiện hành, chữ đã soát; `chu` cho trước thì chữ
    của dấu phải trùng). Khác → lý do (câu người đọc được). Không ném lỗi."""
    if not tep or not os.path.isfile(tep):
        return "không có tệp bìa"
    d = doc_dau(tep)
    if not d:
        return "bìa chưa có dấu cổng chữ (chưa đọc lại chữ trên ảnh, hoặc tệp đã đổi sau khi đọc)"
    if d.get("ok") is not True or int(d.get("phien") or 0) < PHIEN_BAN or d.get("soat") is not True:
        return "dấu cổng chữ không hợp lệ (luật cũ / chưa soát chữ)"
    if not chuan(d.get("chu")):
        return "dấu cổng chữ không ghi chữ"
    if chu and not khop(d.get("chu"), chu):
        return "dấu ghi chữ 「{0}」 khác chữ mong đợi 「{1}」".format(str(d.get("chu"))[:30], str(chu)[:30])
    return ""


def chuyen_dau(nguon: str, dich: str, *, lech_toi_da: float = LECH_VAN_TAY_CHUYEN) -> bool:
    """`dich` là bản DO MÃ chép/xuất lại từ `nguon` (cùng bức): mang dấu của `nguon` sang (cùng sha1, hoặc vân tay
    ảnh lệch < `lech_toi_da`). Nguồn không có dấu hợp lệ / khác bức → False (dich không có dấu)."""
    if kiem_dau(nguon):
        return False
    d = doc_dau(nguon) or {}
    if sha1_tep(nguon) != sha1_tep(dich):
        try:
            from .do_bia import _lech_van_tay, van_tay  # noqa: PLC0415
            if _lech_van_tay(van_tay(nguon), van_tay(dich)) >= lech_toi_da:
                return False
        except Exception:  # noqa: BLE001
            return False
    return bool(ghi_dau(dich, str(d.get("chu") or ""), doc=d.get("doc") or (), cach="chep:" + str(d.get("cach") or ""),
                        tu=str(d.get("sha1") or ""), soat=True))


def tom_tat_dau(tep: str) -> Dict[str, Any]:
    """Khối `thumbnail.chu_khop` của hồ sơ video: dấu của tệp (gọn) hoặc `{ok: False, ly_do}`."""
    ly = kiem_dau(tep)
    if ly:
        return {"ok": False, "ly_do": ly}
    d = doc_dau(tep) or {}
    return {"ok": True, "chu": d.get("chu"), "luc": d.get("luc"), "sha1": str(d.get("sha1") or "")[:16],
            "cach": d.get("cach")}


def ghi_nao(goc: str, loai: str, *, kenh: str = "", ma_goi: str = "", noi_dung: str = "",
            so: Optional[Dict[str, Any]] = None, khoa: str = "") -> bool:
    """Một sự kiện của não bộ phận "bia" (không bao giờ ném lỗi)."""
    if not goc:
        return False
    try:
        from . import nao_bo_phan  # noqa: PLC0415
        return bool(nao_bo_phan.ghi(goc, "bia", loai, kenh=kenh, ma_goi=ma_goi, noi_dung=noi_dung[:600], so=so,
                                    nguon="cong_chu", khoa=khoa))
    except Exception:  # noqa: BLE001
        return False


def xac_minh(goi: Optional[Callable[..., str]], tep: str, chu: str, *, goc: str = "", kenh: str = "",
             ma_goi: str = "", khoa: str = "cong-chu", thang: Sequence[Sequence[str]] = THANG_DOC
             ) -> Dict[str, Any]:
    """Tệp đã có dấu hợp lệ cho `chu` → đạt ngay (không gọi AI). Không thì `kiem_anh`; đạt → `ghi_dau`. Ghi não
    "bia" (đạt = ket_qua, trượt/chưa kiểm = loi). `chu` phải là chữ ĐÃ SOÁT (nơi gọi bảo đảm)."""
    if not kiem_dau(tep, chu):
        return {"ok": True, "da_co": True, "dau": doc_dau(tep), "doc": [], "ly_do": []}
    kq = kiem_anh(goi, tep, chu, khoa=khoa, thang=thang)
    if kq["ok"] is True:
        kq["dau"] = ghi_dau(tep, chu, doc=[x.get("chu") or "" for x in kq["doc"]], cach="doc{0}".format(len(kq["doc"])))
    sha = sha1_tep(tep)
    nhan = {True: "ĐẠT", False: "TRƯỢT", None: "CHƯA KIỂM ĐƯỢC (giữ bìa, thử lại)"}[kq["ok"]]
    ghi_nao(goc, "ket_qua" if kq["ok"] is True else "loi", kenh=kenh, ma_goi=ma_goi,
            noi_dung="cổng chữ bìa {0}: {1} — chữ 「{2}」{3}".format(nhan, os.path.basename(tep), chu[:30],
                                                                    ": " + "; ".join(kq["ly_do"])[:300]
                                                                    if kq["ly_do"] else ""),
            so={"khop": kq["ok"], "so_doc": len(kq["doc"])},
            khoa="cong-chu:{0}:{1}:{2}".format(sha[:16], chuan(chu)[:24], kq["ok"]))
    return kq


# ── Bộ vẽ bằng mã: bảo đảm + bìa dự phòng ───────────────────────────────────


def bao_dam_ma(chu_ve: str, chu_mong: str, *, goc: str = "", ngon_ngu: str = "ja", kieu_phong: str = "") -> str:
    """'' = bộ vẽ chữ bằng mã BẢO ĐẢM in đúng chữ đã soát: chữ sẽ vẽ (nối các tầng) trùng tuyệt đối chữ đã soát và
    phông bộ vẽ chọn có đủ nét mọi ký tự (thiếu nét → ô vuông). Khác → lý do."""
    if not chuan(chu_mong):
        return "không có chữ đã soát"
    if not khop(chu_ve, chu_mong):
        return "chữ bộ vẽ sẽ in 「{0}」 ≠ chữ đã soát 「{1}」".format(str(chu_ve)[:40], str(chu_mong)[:40])
    try:
        from . import bia_theo_khuon as btk  # noqa: PLC0415
        phong = btk._tim_font(goc, chu_ve, ngon_ngu, kieu=kieu_phong)  # noqa: SLF001
        if not phong:
            return "máy không có phông vẽ chữ"
        if not btk._font_du_chu(phong, "".join(c for c in chu_ve if not c.isspace())):  # noqa: SLF001
            return "phông {0} thiếu nét cho chữ bìa".format(os.path.basename(phong))
    except Exception as loi:  # noqa: BLE001
        return "không kiểm được phông: {0}".format(str(loi)[:80])
    return ""


def _tang_tron(chu: str) -> List[Dict[str, Any]]:
    """Chữ đã soát → 1–2 tầng trắng/đỏ cho bộ vẽ, KHÔNG cắt chữ (bộ tách cũ cắt chữ dài hơn 20 ký tự)."""
    from . import bia_theo_khuon as btk  # noqa: PLC0415
    from .do_bia import _chia_tang  # noqa: PLC0415
    s = " ".join(str(chu or "").split())
    tang = _chia_tang(s) if len(chuan(s)) <= btk.TRAN_KY_TU_TONG else []
    if tang and khop("".join(btk.chu_cua_tang(t) for t in tang), s):
        return tang
    k = s.find(" ") if " " in s else max(1, len(s) // 2)
    a, b = s[:k].strip(), s[k:].strip()
    ra = [{"vi_tri": "tren", "phan_mau": [{"chu": a, "mau": "#FFFFFF"}]}] if a else []
    return ra + ([{"vi_tri": "duoi", "phan_mau": [{"chu": b, "mau": "#FFD400"}]}] if b else [])


def ve_bia_ma(nen: str, chu: str, dich: str, *, goc: str = "", ngon_ngu: str = "ja") -> Dict[str, Any]:
    """Vẽ CHỮ ĐÃ SOÁT bằng mã lên nền sạch `nen` → `dich` (jpg 1280×720) + báo cáo đo. Chỉ nhận bản ĐẠT độ đọc được
    và bố cục không hỏng (không khung trước, khung gọn sau). Trả `{tep, bao_cao}` hoặc `{loi}`."""
    from . import bia_theo_khuon as btk, chon_bia, do_bia  # noqa: PLC0415
    tang = _tang_tron(chu)
    ly = bao_dam_ma("".join(btk.chu_cua_tang(t) for t in tang), chu, goc=goc, ngon_ngu=ngon_ngu)
    if ly:
        return {"loi": ly}
    png = os.path.splitext(dich)[0] + ".ve.png"
    bc: Dict[str, Any] = {}
    for cho_khung in (False, True):
        bc = {}
        if not btk.ve_chu_len_anh(nen, png, btk.bo_tri_chu("khuon", tang), goc=goc, ngon_ngu=ngon_ngu, bao_cao=bc,
                                  cho_khung=cho_khung):
            return {"loi": "không vẽ được chữ (thiếu phông / nền hỏng)"}
        if bc.get("dat") is True and do_bia.bo_cuc_dat(bc):
            break
    else:
        _xoa(png)
        _xoa(do_bia.duong_bao_cao(png))
        return {"loi": "bản vẽ chữ không đạt độ đọc được: " + do_bia.tom_tat(bc)[:160]}
    chon_bia._xuat_jpg(png, dich)  # noqa: SLF001
    _xoa(png)
    _xoa(do_bia.duong_bao_cao(png))
    do_bia.ghi_bao_cao(dich, {k: v for k, v in bc.items() if k not in ("tep", "van_tay", "luc")})
    return {"tep": dich, "bao_cao": bc}


def _xoa(duong: str) -> None:
    try:
        os.remove(duong)
    except OSError:
        pass


def tim_nen_sach(thu_muc_thumb: str) -> List[str]:
    """Nền SẠCH (chưa có chữ) để vẽ bìa dự phòng, tốt trước: `znen-thumb_N.png` theo điểm giám khảo (`chon-bia.json`),
    rồi nền các tấm qua lọc của bìa lô (`_lo/xep-hang.json`, theo hạng)."""
    from .chon_bia import doc_chon_bia  # noqa: PLC0415
    diem = {int(u["so"]): float(u.get("tong_diem") or 0) for u in ((doc_chon_bia(thu_muc_thumb) or {}).get(
        "ung_vien") or []) if isinstance(u, dict) and u.get("so") is not None}
    try:
        ten = sorted(os.listdir(thu_muc_thumb))
    except OSError:
        ten = []
    zn = []
    for t in ten:
        m = re.match(r"znen-thumb_(\d+)\.png$", t)
        if m:
            zn.append((-diem.get(int(m.group(1)), 0.0), int(m.group(1)), os.path.join(thu_muc_thumb, t)))
    ra = [p for _d, _s, p in sorted(zn)]
    xh = _doc_json(os.path.join(thu_muc_thumb, "_lo", "xep-hang.json"))
    for u in xh.get("ung_vien") or []:
        p = str((u or {}).get("nen") or "") if isinstance(u, dict) else ""
        if p and not u.get("loai") and os.path.isfile(p) and p not in ra:
            ra.append(p)
    return ra


def bia_ma_du_phong(goi: Optional[Callable[..., str]], thu_muc_thumb: str, chu: str, *, goc: str = "",
                    kenh: str = "", ma_goi: str = "", ngon_ngu: str = "ja", khoa: str = "bia-ma",
                    toi_da: int = SO_NEN_DU_PHONG, so_dau: int = 90, log: Callable[[str], None] = lambda s: None
                    ) -> Dict[str, Any]:
    """Không còn tấm nào có dấu: vẽ CHỮ ĐÃ SOÁT bằng mã lên ≤ `toi_da` nền sạch tốt nhất → `thumb_<so_dau+i>.jpg`, mỗi
    tấm đọc lại hai lượt (`xac_minh`) — tấm đầu đạt được trả `{tep, so, nen}`; `{}` khi không nền nào ra bìa đạt
    (`ok` None trong kết quả khi AI hỏng — nơi gọi giữ, thử lại)."""
    chua = False
    for i, nen in enumerate(tim_nen_sach(thu_muc_thumb)[:max(1, int(toi_da))]):
        so = so_dau + i
        dich = os.path.join(thu_muc_thumb, "thumb_{0:03d}.jpg".format(so))
        v = ve_bia_ma(nen, chu, dich, goc=goc, ngon_ngu=ngon_ngu)
        if v.get("loi"):
            log("  (bìa dự phòng chữ vẽ bằng mã trên {0}: {1})".format(os.path.basename(nen), v["loi"][:120]))
            continue
        kq = xac_minh(goi, dich, chu, goc=goc, kenh=kenh, ma_goi=ma_goi, khoa="{0}:{1}".format(khoa, so))
        if kq["ok"] is True:
            return {"tep": dich, "so": so, "nen": nen}
        chua = chua or kq["ok"] is None
        log("  (bìa dự phòng {0}: {1})".format(os.path.basename(dich), "; ".join(kq["ly_do"])[:160]))
        _xoa(dich)
    return {"chua_kiem": True} if chua else {}


# ── Gói CHỜ ĐĂNG (bàn giao trước 16/10, hoặc dấu mất): đóng dấu / bìa dự phòng / giữ ─────


_DUOI_ANH = (".jpg", ".jpeg", ".png", ".webp")


def anh_goi(thu_muc_goi: str) -> str:
    """Ảnh bìa máy đăng sẽ tải (= `vm/may_dang_dom.tep_goi`): `CHON-*.jpg` trước, không thì ảnh đầu."""
    try:
        ten = sorted(t for t in os.listdir(thu_muc_goi) if os.path.isfile(os.path.join(thu_muc_goi, t)))
    except OSError:
        return ""
    t = next((x for x in ten if x.upper().startswith("CHON-") and x.lower().endswith(".jpg")), "") or next(
        (x for x in ten if os.path.splitext(x)[1].lower() in _DUOI_ANH), "")
    return os.path.join(thu_muc_goi, t) if t else ""


def goi_cho_dang(goc: str, kenh: str) -> List[Dict[str, str]]:
    """Gói của kế hoạch đăng CHƯA đăng (trạng thái không phải ĐÃ ĐĂNG / BỎ) còn thư mục ở DONE: [{ma, goi, anh}]."""
    try:
        from .ke_hoach_dang import doc_bang  # noqa: PLC0415
        from .studio_may import _thu_muc_done  # noqa: PLC0415
        cot, hang = doc_bang(goc, kenh)
        done = _thu_muc_done(goc, kenh)
    except Exception:  # noqa: BLE001
        return []
    i_ma = cot.index("Mã gói") if "Mã gói" in cot else 0
    i_tt = cot.index("Trạng thái đăng") if "Trạng thái đăng" in cot else 11
    ra = []
    for h in hang:
        ma, tt = str(h[i_ma]).strip(), str(h[i_tt] if i_tt < len(h) else "").upper()
        if not ma or "ĐÃ ĐĂNG" in tt or tt.startswith("BỎ"):
            continue
        goi = os.path.join(done, ma)
        if os.path.isdir(goi):
            ra.append({"ma": ma, "goi": goi, "anh": anh_goi(goi)})
    return ra


def _chu_mong_goi(goc: str, kenh: str, ma: str) -> Dict[str, str]:
    """Chữ bìa mong đợi của gói + ngữ cảnh soát: chữ thật sự vẽ của tấm đã chọn (`chon-bia.json` chu_ve, kế hoạch
    `chu_du_kien`) > dòng THUMB của lượt > `chu_bia` hồ sơ. Kèm thư mục 7-thumbnail của lượt (nếu còn)."""
    nc = _ngu_canh(goc, kenh, ma)
    luot = ma[len(kenh) + 1:] if ma.startswith(kenh + "-") else ma
    tm = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "7-thumbnail")
    chon = (_doc_json(os.path.join(tm, "chon-bia.json")).get("chon") or {})
    chu = str(chon.get("chu_ve") or "") if isinstance(chon, dict) else ""
    if not chu and isinstance(chon, dict) and chon.get("so") is not None:
        kh = _doc_json(os.path.join(tm, "ke-hoach-bia.json"))
        chu = next((str(m.get("chu_du_kien") or "") for m in kh.get("muc") or [] if isinstance(m, dict)
                    and str(m.get("so")) == str(chon.get("so"))), "")
    if not chu:
        try:
            with io.open(os.path.join(os.path.dirname(tm), "1-tieu-de.txt"), encoding="utf-8") as f:
                chu = next((d.split(":", 1)[1].strip() for d in f if d.strip().startswith("THUMB:")), "")
        except OSError:
            chu = ""
    if not chu:
        chu = str(_doc_json(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", ma + ".json")).get("chu_bia") or "")
    return dict(nc, chu=chu, thu_muc_thumb=tm if os.path.isdir(tm) else "", doi_thu=chu_bia_doi_thu(os.path.dirname(tm)))


def dau_goi(goi: Optional[Callable[..., str]], goc: str, kenh: str, ma: str, thu_muc_goi: str,
            log: Callable[[str], None] = print) -> Dict[str, Any]:
    """MỘT gói chờ đăng: bìa đã có dấu → xong. Không: soát chữ bìa (sai → viết lại) → đọc bìa hai lượt → dấu; bìa sai
    chữ → bìa dự phòng chữ vẽ bằng mã trên nền sạch của lượt (thay `CHON-*` của gói, bản cũ vào `_bi-loai/`, cập nhật
    hồ sơ). AI hỏng → GIỮ (`ok` None, ghi não) — máy đăng không tải gói không dấu, lượt sau thử lại."""
    anh = anh_goi(thu_muc_goi)
    ra: Dict[str, Any] = {"ma": ma, "anh": os.path.basename(anh), "ok": None, "ly_do": ""}
    if anh and not kiem_dau(anh):
        ra.update(ok=True, ly_do="đã có dấu")
        return ra
    cm = _chu_mong_goi(goc, kenh, ma)
    if not cm["chu"]:
        ra.update(ok=False, ly_do="không biết chữ bìa mong đợi của gói")
    else:
        s = chot_chu(goi, cm["chu"], tieu_de=cm["tieu_de"], ngu_canh=cm["ngu_canh"], khoa="dau-goi:{0}:soat".format(ma),
                     doi_thu=cm.get("doi_thu") or ())
        if s.get("ok") is not True:
            ra.update(ok=s.get("ok"), ly_do="chữ bìa chưa qua soát: " + str(s.get("ly_do") or ""))
        else:
            chu = str(s["chu"])
            kq = xac_minh(goi, anh, chu, goc=goc, kenh=kenh, ma_goi=ma, khoa="dau-goi:" + ma) if anh else {
                "ok": False, "ly_do": ["gói không có ảnh bìa"]}
            ra.update(ok=kq["ok"], ly_do="; ".join(kq.get("ly_do") or []), chu=chu)
            if kq["ok"] is False and cm["thu_muc_thumb"]:
                d = bia_ma_du_phong(goi, cm["thu_muc_thumb"], chu, goc=goc, kenh=kenh, ma_goi=ma,
                                    khoa="dau-goi:{0}:ma".format(ma), log=log)
                if d.get("tep"):
                    _thay_anh_goi(goc, kenh, ma, thu_muc_goi, anh, d["tep"])
                    ra.update(ok=True, ly_do="bìa cũ sai chữ ({0}) → bìa dự phòng chữ vẽ bằng mã {1}".format(
                        ra["ly_do"][:120], os.path.basename(d["tep"])), thay=os.path.basename(d["tep"]))
                elif d.get("chua_kiem"):
                    ra.update(ok=None, ly_do=ra["ly_do"] + " — bìa dự phòng chưa đọc lại được (AI lỗi)")
    if ra["ok"] is not True:
        ghi_nao(goc, "loi", kenh=kenh, ma_goi=ma, noi_dung="GIỮ gói chờ đăng {0}: bìa chưa có dấu cổng chữ — {1}".format(
            ma, ra["ly_do"][:300]), khoa="dau-goi:{0}:{1}:{2}".format(ma, _dt.date.today().isoformat(), ra["ok"]))
    return ra


def _thay_anh_goi(goc: str, kenh: str, ma: str, thu_muc_goi: str, cu: str, moi: str) -> None:
    """Gói nhận bìa dự phòng có dấu: bìa cũ (và mọi CHON-*) vào `_bi-loai/`, chép `CHON-<tên mới>` + dấu, cập nhật bản
    sao bìa của hồ sơ video."""
    import shutil  # noqa: PLC0415
    bo = os.path.join(thu_muc_goi, "_bi-loai")
    os.makedirs(bo, exist_ok=True)
    for t in os.listdir(thu_muc_goi):
        p = os.path.join(thu_muc_goi, t)
        if os.path.isfile(p) and (t.upper().startswith("CHON-") or p == cu) and t.lower().endswith(_DUOI_ANH):
            os.replace(p, os.path.join(bo, t))
    dich = os.path.join(thu_muc_goi, "CHON-" + os.path.basename(moi))
    shutil.copy2(moi, dich + ".tam")
    os.replace(dich + ".tam", dich)
    chuyen_dau(moi, dich)
    try:
        from . import ho_so_video  # noqa: PLC0415
        if ho_so_video.doc_ho_so(goc, kenh, ma):
            ho_so_video._sao_luu_anh_bia(goc, kenh, ma, dich)  # noqa: SLF001
            ho_so_video.cap_nhat_chu_khop(goc, kenh, ma, tom_tat_dau(dich))
    except Exception:  # noqa: BLE001
        pass


def dau_cac_goi(goc: str, kenh: str, goi: Optional[Callable[..., str]] = None,
                log: Callable[[str], None] = print) -> List[Dict[str, Any]]:
    """Mọi gói chờ đăng của kênh chưa có dấu → `dau_goi`."""
    ds = [g for g in goi_cho_dang(goc, kenh) if kiem_dau(g["anh"])]
    if ds and goi is None:
        goi = _goi_that(goc)
    ra = []
    for g in ds:
        r = dau_goi(goi, goc, kenh, g["ma"], g["goi"], log=log)
        log("{0}: {1} — {2}".format(g["ma"], {True: "CÓ DẤU", False: "TRƯỢT (giữ)", None: "GIỮ (AI lỗi)"}[r["ok"]],
                                    r.get("ly_do")))
        ra.append(r)
    return ra


# ── Dòng lệnh ────────────────────────────────────────────────────────────────


def _goi_that(goc: str) -> Callable[..., str]:
    from .bia_lo import _goi_that as g  # noqa: PLC0415
    return g(goc, print)


def _ngu_canh(goc: str, kenh: str, ma: str) -> Dict[str, str]:
    """(tiêu đề, kịch bản) của gói từ thư mục lượt (nếu còn) hoặc hồ sơ video."""
    tieu_de, kb = "", ""
    if kenh and ma:
        luot = ma[len(kenh) + 1:] if ma.startswith(kenh + "-") else ma
        d = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)
        try:
            with io.open(os.path.join(d, "1-tieu-de.txt"), encoding="utf-8") as f:
                for dong in f:
                    if dong.strip().startswith("TITLE:"):
                        tieu_de = dong.split(":", 1)[1].strip()
        except OSError:
            pass
        try:
            with io.open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as f:
                kb = f.read(2500)
        except OSError:
            pass
        for ten in ("8-phu-de.srt", "3-phu-de.srt") if not kb.strip() else ():   # lượt đã dọn kịch bản: lấy phụ đề
            kb = " ".join(x.strip() for x in _doc_tep(os.path.join(d, ten)).splitlines()
                          if x.strip() and not re.match(r"^\d+$|^\d\d:\d\d:\d\d", x.strip()))[:2500]
            if kb:
                break
        if not tieu_de:
            tieu_de = str(_doc_json(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", ma + ".json")).get(
                "tieu_de") or "")
    return {"tieu_de": tieu_de, "ngu_canh": kb}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.cong_chu", description="Cổng chữ đúng của ảnh bìa.")
    p.add_argument("lenh", choices=("dau", "kiem", "dau-goi"))
    p.add_argument("tep", nargs="*")
    p.add_argument("--chu", default="", help="chữ bìa mong đợi (bắt buộc với dau)")
    p.add_argument("--kenh", default="")
    p.add_argument("--ma", default="", help="mã gói (lấy tiêu đề + kịch bản làm ngữ cảnh soát chữ)")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    if a.lenh == "dau-goi":
        kenh = [a.kenh] if a.kenh else sorted(k for k in os.listdir(os.path.join(goc, "CHANNEL"))
                                              if not k.startswith("_") and os.path.isdir(os.path.join(goc, "CHANNEL", k)))
        ra = [r for k in kenh for r in dau_cac_goi(goc, k)]
        return 0 if all(r["ok"] is True for r in ra) else 1
    if a.lenh == "kiem":
        for t in a.tep:
            print("{0}: {1}".format(t, kiem_dau(t) or "CÓ DẤU — " + json.dumps(tom_tat_dau(t), ensure_ascii=False)))
        return 0
    if not a.chu.strip():
        p.error("dau cần --chu")
    goi = _goi_that(goc)
    nc = _ngu_canh(goc, a.kenh, a.ma)
    s = chot_chu(goi, a.chu, tieu_de=nc["tieu_de"], ngu_canh=nc["ngu_canh"], khoa="cong-chu-cli:soat",
                 so_lan_viet_lai=0)
    if s.get("ok") is not True or s.get("sua"):
        print("CHỮ BÌA CHƯA ĐẠT soát chính tả: ok={0} sửa={1} → 「{2}」 ({3})".format(
            s.get("ok"), s.get("sua"), s.get("chu"), s.get("ly_do")))
        return 2
    ma = 0
    for t in a.tep:
        kq = xac_minh(goi, t, a.chu, goc=goc, kenh=a.kenh, ma_goi=a.ma, khoa="cong-chu-cli")
        print("{0}: {1} {2} {3}".format(t, {True: "ĐẠT — đã đóng dấu", False: "TRƯỢT", None: "CHƯA KIỂM ĐƯỢC"}[kq["ok"]],
                                        [x.get("chu") for x in kq.get("doc") or []], "; ".join(kq.get("ly_do") or [])))
        ma = ma or (0 if kq["ok"] is True else 1)
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
