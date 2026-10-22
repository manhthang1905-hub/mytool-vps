"""NHÂN VẬT NHẤT QUÁN (21/10/2026) — chữ tả nhân vật trong style.yaml + prompt/*.md phải là NHÂN VẬT CỦA CHÍNH KÊNH.

═══ VÌ SAO ═══

Chủ 21/10: kênh mở mới bằng cách lấy khuôn kênh gốc (`core/mo_kenh.dung_kenh`) chỉ thay `default_character_*` — mọi
câu khác (`image_style`, `palette`, `thumbnail_style`, `scene_plan_style`, `negative_prompt`, `technical_suffix`, các
đoạn nhân vật trong `prompt/7-canh.md`, `7-ke-hoach.md`, `8-thumbnail.md`…) vẫn tả nhân vật CŨ. Đuôi phong cách do mã
ghép vào MỌI lời nhắc ảnh cảnh (`chia_canh.duoi_anh_phong_cach`) nên máy vẽ nhận ảnh tham chiếu người A + chữ tả nhân
vật B → video đầu của kênh mới vẽ nhầm nhân vật (đầu mochi, áo xanh rêu thay vì áo navy…).

═══ CÁCH LÀM ═══

1. TỪ CŨ (`tu_cu`) do MÃ rút: so `default_character_lock` + `reference_lock` của kênh gốc với lock + prompt nhân vật
   của kênh mới — từ ghép có gạch (`moss-green`), từ riêng (`mochi`, `chestnut`), cặp từ (`dot eyes`, `knit cardigan`)
   có ở kênh gốc mà kênh mới không có. Từ quá chung (màu đơn, bộ phận cơ thể, quần áo chung) bỏ; từ KIỂU VẼ
   (`watercolor`, `painterly`…) chỉ tính khi kiểu vẽ của nhân vật mới khác hẳn.
2. QUÉT (`quet_thu_muc`): khoá style.yaml + đoạn prompt/*.md có từ cũ (khớp theo ranh giới từ — `kimochi` không dính).
3. VIẾT LẠI (`viet_lai_thu_muc`): AI (đi ví ShopAPI — đây là lời nhắc ẢNH, cùng luật với chia cảnh; KHÔNG Claude Max)
   viết lại đúng các khoá/đoạn ấy cho nhân vật mới, giữ nguyên ngách/luật an toàn/bố cục; MÃ kiểm lại — còn từ cũ, mất
   chỗ giữ `<<…>>`, rỗng → hỏi lại một lần → vẫn hỏng thì NÉM (nơi gọi dừng, nhịp sau thử lại, không cần người).
   Khoá nhân vật của chính kênh (`default_character_*`, `engagement_rules`…) không bao giờ bị đụng.
4. Tự kiểm hằng ngày (`kiem_kenh`, nối ở `core/tu_kiem.kiem_nhan_vat`): kênh biết kênh gốc → quét từ cũ; hỏng → tự
   chạy `python -m core.nhan_vat_nhat_quan sua <KÊNH>` (sao lưu trước ở `workspace/sao-luu/nhan-vat/`).

Luồng THAY KÊNH vì tài khoản không được phân phối (`core/thay_kenh`) giữ NGUYÊN nhân vật của kênh cũ → không chạy
bước viết lại (kênh gốc = chính nó, từ cũ rỗng).

    python -X utf8 -m core.nhan_vat_nhat_quan kiem [KÊNH…]     # chỉ đọc: từ cũ còn ở đâu
    python -X utf8 -m core.nhan_vat_nhat_quan sua KÊNH [--goc-kenh MÃ]   # viết lại (ví ShopAPI) + kiểm lại
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import re
import shutil
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Khoá NHÂN VẬT của chính kênh — nguồn sự thật, không bao giờ viết lại.
KHOA_GIU = ("default_character_prompt", "default_character_lock", "engagement_rules", "audience_language",
            "thumb_text_font", "thumb_text_hex", "tone_guard", "aspect_ratio")
#: Khoá HÌNH: một khoá dính từ cũ thì viết lại CẢ NHÓM cho khớp nhau (kiểu vẽ, bảng màu, đuôi kỹ thuật một nhà).
KHOA_HINH = ("style_name", "image_style", "video_style", "thumbnail_style", "scene_plan_style", "palette",
             "negative_prompt", "reference_lock", "technical_suffix")
TEP_STYLE = "style.yaml"
THU_MUC_PROMPT = "prompt"
SO_LUOT = 2
TOKEN_VIET = 8000

#: Hư từ / từ không mang nét nhân vật — không bao giờ thành từ cũ, cũng cắt cặp từ.
_HU = frozenset("""a an the of in on at to with without over under and or no not per every each same one two three
four is are its it his her their very do does don't add any free scene scenes expression expressions style styles
look looks match matching attached reference image exactly redesign twin reflection second figure fixed traits lock
always never wearing wears wear holding sitting standing change keep draw drawn show make both""".split())
#: Màu đơn / bộ phận / đồ mặc chung — một mình không nói lên nhân vật nào (vẫn ghép cặp được: `pink cheeks`).
_MAU = frozenset("""white black dark light grey gray brown cream beige pink blue navy green red yellow orange purple
silver gold pure faint warm""".split())
_THAN = frozenset("""head face eyes eye hair cheeks skin shirt trousers pants shoes sweater cardigan jacket coat skirt
dress glasses""".split())
_CHUNG = _MAU | _THAN | frozenset("""character person people japanese man woman boy girl adult young old older elderly
kind calm soft gentle fine simple small large big tiny round loose neat short long body arms legs hands mouth nose ears
knit knitted clothes clothing collar age years early late mid twenties thirties forties fifties sixties seventies
eighties intelligent thoughtful contemplative relaxed upright posture headed rimmed haired""".split())
#: HỌ kiểu vẽ — từ cũ chỉ khi nhân vật mới nêu một họ kiểu vẽ KHÁC (đổi kiểu vẽ hẳn).
_PHONG = frozenset("""anime vector flat watercolor watercolour pencil painterly ink linework cel brush storybook crayon
pastel minimalist chibi clay pixel 3d 2d nostalgic""".split())
#: Từ nét vẽ chung (viền, vân…) — không bao giờ là từ cũ đơn; cặp có nó theo luật kiểu vẽ.
_VE = frozenset("texture textures outline outlines line lines shading wash washes paper grain stroke strokes".split())
_TU_AGE = re.compile(r"^\d+s?$")


class LoiNhanVat(RuntimeError):
    """Viết lại xong mà vẫn còn chữ tả nhân vật cũ (hoặc AI trả rác) — nơi gọi dừng và thử lại nhịp sau."""


# ═══════════════════════════ từ cũ (thuần) ═══════════════════════════════════
def _chuan(chu: Any) -> str:
    """Chữ thường; `_`/`-` thành khoảng trắng (khoá `mochi_head…` và `pure-white` khớp như chữ thường)."""
    return " ".join(re.sub(r"[_\-]+", " ", str(chu or "").casefold()).split())


def _cac_tu(chu: Any) -> List[str]:
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(chu or "").casefold().replace("_", " "))


def _doan(chu: Any) -> List[List[str]]:
    return [_cac_tu(x) for x in re.split(r"[,;.()—]|\bover\b|\bwith\b|\band\b", str(chu or "").casefold())]


def _co(tu_chuan: str, chu_chuan: str) -> bool:
    return bool(tu_chuan) and re.search(r"(?<![a-z0-9])" + re.escape(tu_chuan) + r"(?![a-z0-9])", chu_chuan) is not None


def _phong_cua(chu: str) -> set:
    return {p for w in _cac_tu(chu) for p in [w] + w.split("-") if p in _PHONG}


def _la_phong(w: str) -> bool:
    return any(p in _PHONG or p in _VE for p in w.split("-"))


def tu_cu(nhan_vat_goc: Sequence[str], nhan_vat_moi: Sequence[str]) -> List[str]:
    """Từ/cụm tả nhân vật CŨ (của kênh gốc) mà nhân vật MỚI không có. Hàm thuần, xếp ổn định.

    `nhan_vat_goc` = [lock, reference_lock] của kênh gốc; `nhan_vat_moi` = [lock, prompt nhân vật…] của kênh mới.
    Hai bên giống nhau (thay kênh giữ nguyên nhân vật) → []."""
    goc = " , ".join(str(x or "") for x in nhan_vat_goc)
    moi = " ".join(str(x or "") for x in nhan_vat_moi)
    moi_c = _chuan(moi)
    if not goc.strip() or _chuan(goc) == moi_c:
        return []
    if nhan_vat_goc and nhan_vat_moi and _chuan(nhan_vat_goc[0]) and _chuan(nhan_vat_goc[0]) == _chuan(nhan_vat_moi[0]):
        return []                                    # cùng lock = cùng nhân vật (kênh thay giữ nguyên)
    doi_phong = bool(_phong_cua(moi) - _phong_cua(goc))

    def dung(t: str) -> bool:
        return not _co(_chuan(t), moi_c)

    def bo(w: str) -> bool:
        return w in _HU or bool(_TU_AGE.match(w))

    ra: set = set()
    for ds in _doan(goc):
        for w in ds:
            phan = w.split("-")
            if bo(w):
                continue
            if _la_phong(w):
                if doi_phong and w not in _VE and dung(w):
                    ra.add(w)
                continue
            if len(phan) > 1:
                if dung(w):
                    ra.add(w)
                # `mustard-yellow` → `mustard`; `moss-green` → `moss` (phần còn lại là màu/từ chung)
                for i, p in enumerate(phan):
                    khac = phan[:i] + phan[i + 1:]
                    if len(p) >= 4 and p not in _CHUNG and not bo(p) and all(x in _CHUNG for x in khac) and dung(p):
                        ra.add(p)
            elif len(w) >= 4 and w not in _CHUNG and dung(w):
                ra.add(w)
        for a, b in zip(ds, ds[1:]):
            if bo(a) or bo(b):
                continue
            if _la_phong(a) or _la_phong(b):
                if not doi_phong:
                    continue
            elif a in _CHUNG and b in _CHUNG and not (a in _MAU and b in _THAN):
                continue
            if dung(a + " " + b):
                ra.add(a + " " + b)
    # cụm đã chứa một từ đơn cũ thì thừa
    don = {t for t in ra if " " not in t}
    ra = {t for t in ra if " " not in t or not any(_co(_chuan(d), _chuan(t)) for d in don)}
    return sorted(ra, key=lambda t: (-len(t), t))


def tim(chu: Any, cac_tu: Iterable[str]) -> List[str]:
    """Từ cũ nào có trong `chu` (ranh giới từ, không phân biệt hoa thường, `_`/`-` = khoảng trắng)."""
    c = _chuan(chu)
    return [t for t in cac_tu if _co(_chuan(t), c)]


# ═══════════════════════════ đọc/ghi tệp kênh ════════════════════════════════
def _doc(duong: str) -> str:
    try:
        with io.open(duong, encoding="utf-8", newline="") as tep:
            return tep.read()
    except OSError:
        return ""


def _ghi(duong: str, chu: str) -> None:
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="") as tep:
        tep.write(chu)
    os.replace(tam, duong)


_RE_KHOA = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):[ \t]*"(.*)"[ \t]*$')


def khoa_style(chu: str) -> Dict[str, str]:
    """{khoá: giá trị} của các dòng `khoa: "…"` (style.yaml của tool là YAML một dòng, nháy kép)."""
    ra: Dict[str, str] = {}
    for d in chu.replace("\r\n", "\n").split("\n"):
        m = _RE_KHOA.match(d)
        if m:
            ra[m.group(1)] = m.group(2)
    return ra


def dat_khoa(chu: str, khoa: str, gia_tri: str) -> str:
    """Thay giá trị dòng `khoa: "…"` — GIỮ mọi dòng khác (cả chú thích). Không thấy khoá → ném (không tự thêm)."""
    gia_tri = " ".join(str(gia_tri).replace('"', "'").replace("\\", "/").split())
    xd = "\r\n" if "\r\n" in chu else "\n"
    dong = chu.replace("\r\n", "\n").split("\n")
    for i, d in enumerate(dong):
        m = _RE_KHOA.match(d)
        if m and m.group(1) == khoa:
            dong[i] = '{0}: "{1}"'.format(khoa, gia_tri)
            return xd.join(dong)
    raise LoiNhanVat("style.yaml không có khoá " + khoa)


def _dau_tep(chu: str) -> Tuple[List[str], List[str]]:
    """(khối chú thích/rỗng đầu tệp, phần còn lại) — theo dòng, đã bỏ \\r."""
    dong = chu.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(dong) and (dong[i].lstrip().startswith("#") or not dong[i].strip()):
        i += 1
    return dong[:i], dong[i:]


def doan_md(chu: str) -> List[str]:
    """Tách prompt .md thành đoạn theo dòng trống (ghép lại bằng "\\n\\n" ra đúng bản cũ, đã bỏ \\r)."""
    return chu.replace("\r\n", "\n").split("\n\n")


def quet_thu_muc(thu_muc: str, cac_tu: Sequence[str]) -> Dict[str, List[str]]:
    """{chỗ: [từ cũ]} — chỗ = `style.yaml:<khoá>`, `style.yaml#dau` (chú thích đầu tệp), `prompt/<tệp>#<số đoạn>`."""
    ra: Dict[str, List[str]] = {}
    if not cac_tu:
        return ra
    cs = _doc(os.path.join(thu_muc, TEP_STYLE))
    for k, v in khoa_style(cs).items():
        if k in KHOA_GIU:
            continue
        h = tim(v, cac_tu)
        if h:
            ra["{0}:{1}".format(TEP_STYLE, k)] = h
    dau, _ = _dau_tep(cs)
    h = tim("\n".join(dau), cac_tu)
    if h:
        ra[TEP_STYLE + "#dau"] = h
    tp = os.path.join(thu_muc, THU_MUC_PROMPT)
    for ten in sorted(os.listdir(tp)) if os.path.isdir(tp) else []:
        if not ten.endswith(".md"):
            continue
        for i, d in enumerate(doan_md(_doc(os.path.join(tp, ten)))):
            h = tim(d, cac_tu)
            if h:
                ra["{0}/{1}#{2}".format(THU_MUC_PROMPT, ten, i)] = h
    return ra


# ═══════════════════════════ viết lại (AI ví + mã kiểm) ══════════════════════
LOI_NHAC = """You fix a YouTube channel's image-style settings after the channel was CLONED from another channel.
The clone kept text that still describes the OLD channel's main character (and its look). Rewrite ONLY the items given
below so they describe the NEW main character and an art style consistent with the NEW character prompt (that prompt
drew the channel's reference image, which is attached to every image request).

NEW MAIN CHARACTER (source of truth — never contradict it)
- character lock: {lock}
- character prompt (also defines the art style): {prompt}

WORDS AND PHRASES OF THE OLD CHARACTER — never write any of them, not even inside a negative like "no …":
{tu}

Rules
- Keep everything that is NOT about the main character's look or the art style exactly as it is: the niche, places,
  props, layout rules, safety and tone rules, text rules, numbers, placeholders like <<NAME>>, markdown and line breaks.
- Other people in the pictures (bystanders, the person the narration warns about, family) are ordinary people drawn in
  the SAME new art style — never mascot or symbolic figures — unless the new character itself is a mascot.
- Style items stay English, one line each, about the same length, no double quotes, no backslashes. `style_name` is
  lowercase snake_case, 3 to 6 words naming the new look. Paragraphs keep their language and their line breaks.
- In the "doan" items, the main character is still called `the reference character` where the old text did.
{them}
ITEMS TO REWRITE (JSON):
{muc}

Return ONE JSON object only: {{"style": {{"<key>": "<new value>"}}, "doan": {{"<id>": "<new paragraph>"}}}} with exactly
the same keys and ids as given."""


def _cho_giu(chu: str) -> List[str]:
    return sorted(re.findall(r"<<[A-Z_]+>>", chu or ""))


def _chon_muc(thu_muc: str, cham: Dict[str, List[str]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Khoá style + đoạn md phải viết lại. Một khoá HÌNH dính → cả nhóm HÌNH."""
    st = khoa_style(_doc(os.path.join(thu_muc, TEP_STYLE)))
    khoa = {c.split(":", 1)[1] for c in cham if c.startswith(TEP_STYLE + ":")}
    if khoa & set(KHOA_HINH):
        khoa |= {k for k in KHOA_HINH if k in st}
    style = {k: st[k] for k in sorted(khoa) if k in st and k not in KHOA_GIU}
    doan: Dict[str, str] = {}
    for c in cham:
        if c.startswith(THU_MUC_PROMPT + "/"):
            ten, so = c[len(THU_MUC_PROMPT) + 1:].rsplit("#", 1)
            ds = doan_md(_doc(os.path.join(thu_muc, THU_MUC_PROMPT, ten)))
            if int(so) < len(ds):
                doan[c] = ds[int(so)]
    return style, doan


def kiem_tra_loi(du: Any, style: Dict[str, str], doan: Dict[str, str], cac_tu: Sequence[str]) -> List[str]:
    """Mã kiểm câu trả lời viết lại. Rỗng = đạt."""
    loi: List[str] = []
    if not isinstance(du, dict):
        return ["không phải JSON object"]
    s = du.get("style") if isinstance(du.get("style"), dict) else {}
    d = du.get("doan") if isinstance(du.get("doan"), dict) else {}
    for k in style:
        v = " ".join(str(s.get(k) or "").split())
        if len(v) < (3 if k == "style_name" else 20):
            loi.append("thiếu/rỗng style.{0}".format(k))
        elif tim(v, cac_tu):
            loi.append("style.{0} còn từ cũ: {1}".format(k, ", ".join(tim(v, cac_tu)[:6])))
    for i, cu in doan.items():
        v = str(d.get(i) or "")
        if len(v.strip()) < 10:
            loi.append("thiếu đoạn " + i)
        elif tim(v, cac_tu):
            loi.append("đoạn {0} còn từ cũ: {1}".format(i, ", ".join(tim(v, cac_tu)[:6])))
        elif _cho_giu(v) != _cho_giu(cu):
            loi.append("đoạn {0} làm mất/đổi chỗ giữ <<…>>".format(i))
    return loi


def _bat_json(chu: str) -> Any:
    """22/10/2026: câu trả lời chứa NGUYÊN VĂN đoạn prompt/*.md — có sẵn ``` bên trong chuỗi JSON → `loc_json` (bóc
    khối ```…```) cắt nhầm giữa chuỗi → "Expecting property name … char 1" (TL7/TL8 hỏng 2/2 lượt). Thử nguyên khối
    { … } trước, rồi mới lùi `loc_json`."""
    from .goi_van_ban import loc_json  # noqa: PLC0415

    tho = str(chu or "").strip()
    a, b = tho.find("{"), tho.rfind("}")
    if 0 <= a < b:
        try:
            return json.loads(tho[a:b + 1], strict=False)
        except ValueError:
            pass
    return loc_json(tho)


def viet_lai_thu_muc(thu_muc: str, cac_tu: Sequence[str], goi: Callable[[str], str], *, lock: str, prompt: str,
                     log: Callable[[str], None] = print, so_luot: int = SO_LUOT) -> Dict[str, Any]:
    """Viết lại MỌI chỗ còn từ cũ trong `thu_muc` (style.yaml + prompt/*.md) rồi ghi. Trả {"sua": [chỗ], "luot": n}.

    Không còn chỗ nào → {"sua": []} (không gọi AI). Hết lượt mà còn từ cũ / AI trả rác → `LoiNhanVat` (KHÔNG ghi gì)."""
    cham = quet_thu_muc(thu_muc, cac_tu)
    if not cham:
        return {"sua": [], "luot": 0}
    style, doan = _chon_muc(thu_muc, cham)
    loi: List[str] = []
    du: Any = None
    for lan in range(max(1, int(so_luot))):
        ask = LOI_NHAC.format(lock=lock, prompt=prompt, tu=", ".join(cac_tu),
                              them=("- THE PREVIOUS ANSWER WAS REJECTED BY CODE CHECKS: " + "; ".join(loi)[:900] + "\n") if loi else "",
                              muc=json.dumps({"style": style, "doan": doan}, ensure_ascii=False, indent=1))
        try:
            du = _bat_json(goi(ask))
        except Exception as e:  # noqa: BLE001 — AI rác/lỗi tạm: lượt sau hỏi lại
            loi = ["không đọc được câu trả lời ({0})".format(str(e)[:80])]
            log("  nhân vật: lượt {0} hỏng — {1}".format(lan + 1, loi[0]))
            continue
        loi = kiem_tra_loi(du, style, doan, cac_tu)
        if not loi:
            break
        log("  nhân vật: lượt {0} bị mã loại — {1}".format(lan + 1, "; ".join(loi)[:200]))
    if loi:
        raise LoiNhanVat("viết lại nhân vật chưa đạt sau {0} lượt: {1}".format(so_luot, "; ".join(loi)[:300]))
    # ghi: style.yaml (khoá + chú thích đầu tệp), từng tệp md
    p_style = os.path.join(thu_muc, TEP_STYLE)
    cs = _doc(p_style)
    for k in style:
        cs = dat_khoa(cs, k, du["style"][k])
    dau, than = _dau_tep(cs)
    if tim("\n".join(dau), cac_tu):
        xd = "\r\n" if "\r\n" in cs else "\n"
        giu = [d for d in dau if not tim(d, cac_tu)]
        giu.append("#  {0}: chữ tả nhân vật/kiểu hình của kênh gốc đã được viết lại cho nhân vật riêng của kênh "
                   "(core/nhan_vat_nhat_quan.py).".format(_dt.date.today().isoformat()))
        cs = xd.join(giu + [""] + than)
    tep_md: Dict[str, Dict[int, str]] = {}
    for i, v in du["doan"].items():
        if i in doan:
            ten, so = i[len(THU_MUC_PROMPT) + 1:].rsplit("#", 1)
            tep_md.setdefault(ten, {})[int(so)] = str(v).replace("\r\n", "\n").strip("\n")
    moi_md: Dict[str, str] = {}
    for ten, thay in tep_md.items():
        p = os.path.join(thu_muc, THU_MUC_PROMPT, ten)
        tho = _doc(p)
        ds = doan_md(tho)
        for so, v in thay.items():
            ds[so] = v
        moi_md[p] = "\n\n".join(ds).replace("\n", "\r\n" if "\r\n" in tho else "\n")
    # kiểm toàn bộ bản MỚI trước khi ghi (một chỗ sót = không ghi gì)
    con = [t for k, v in khoa_style(cs).items() if k not in KHOA_GIU for t in tim(v, cac_tu)]
    con += tim("\n".join(_dau_tep(cs)[0]), cac_tu) + [t for c in moi_md.values() for t in tim(c, cac_tu)]
    if con:
        raise LoiNhanVat("sau khi ghép bản viết lại vẫn còn từ cũ: " + ", ".join(sorted(set(con)))[:200])
    _ghi(p_style, cs)
    for p, c in moi_md.items():
        _ghi(p, c)
    con_lai = quet_thu_muc(thu_muc, cac_tu)
    if con_lai:
        raise LoiNhanVat("còn từ cũ ở: " + ", ".join(sorted(con_lai))[:200])
    return {"sua": sorted(cham), "luot": lan + 1, "khoa": sorted(style), "doan": sorted(doan)}


# ═══════════════════════════ kênh thật ═══════════════════════════════════════
def _yaml(duong: str) -> Dict[str, Any]:
    from .kenh import doc_yaml  # noqa: PLC0415

    try:
        return doc_yaml(duong) or {}
    except Exception:  # noqa: BLE001
        return {}


def kenh_goc_cua(goc: str, ma: str) -> str:
    """Kênh gốc kênh `ma` lấy khuôn: sổ mở kênh (`kenh_goc`) > dòng đầu kenh.yaml ("lấy khuôn … từ X."). "" = không rõ.
    Kênh THAY giữ nguyên nhân vật (`thay_cho`) không có kênh gốc để so."""
    y = _yaml(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"))
    if str(y.get("thay_cho") or "").strip():
        return ""
    try:
        with io.open(os.path.join(goc, "workspace", "mo-kenh", "trang-thai.json"), encoding="utf-8") as tep:
            d = ((json.load(tep) or {}).get("kenh") or {}).get(ma) or {}
        if str(d.get("loai") or "") in ("thay_kenh", "thay_kenh_tu_dong") and d.get("giu_nguyen"):
            return ""
        if d.get("kenh_goc"):
            return str(d["kenh_goc"])
    except (OSError, ValueError):
        pass
    dau = _doc(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"))[:600]
    m = re.search(r"lấy khuôn[^\n]*?từ\s+([A-Za-z0-9][A-Za-z0-9_-]*)", dau)
    return m.group(1) if m else ""


def nhan_vat(st: Dict[str, Any]) -> Tuple[str, str, str]:
    return (str(st.get("default_character_lock") or ""), str(st.get("default_character_prompt") or ""),
            str(st.get("reference_lock") or ""))


def tu_cu_cua(goc: str, ma: str, kenh_goc: str = "") -> List[str]:
    kg = kenh_goc or kenh_goc_cua(goc, ma)
    if not kg or kg == ma:
        return []
    sg = _yaml(os.path.join(goc, "CHANNEL", kg, TEP_STYLE))
    sm = _yaml(os.path.join(goc, "CHANNEL", ma, TEP_STYLE))
    lg, _pg, rg = nhan_vat(sg)
    lm, pm, _rm = nhan_vat(sm)
    if not lg or not lm:
        return []
    return tu_cu([lg, rg], [lm, pm])


def kiem_kenh(goc: str, ma: str) -> Dict[str, Any]:
    """{tt: dat | hong | bo_qua, kenh_goc, tu, cham, ly_do}. Chỉ đọc đĩa."""
    kg = kenh_goc_cua(goc, ma)
    if not kg:
        return {"tt": "bo_qua", "kenh_goc": "", "tu": [], "cham": {}, "ly_do": "không có kênh gốc để so"}
    if not os.path.isfile(os.path.join(goc, "CHANNEL", kg, TEP_STYLE)):
        return {"tt": "bo_qua", "kenh_goc": kg, "tu": [], "cham": {}, "ly_do": "kênh gốc không còn style.yaml"}
    tu = tu_cu_cua(goc, ma, kg)
    cham = quet_thu_muc(os.path.join(goc, "CHANNEL", ma), tu)
    return {"tt": "hong" if cham else "dat", "kenh_goc": kg, "tu": tu, "cham": cham,
            "ly_do": ("{0} chỗ còn tả nhân vật của {1}: {2}".format(len(cham), kg, "; ".join(
                "{0} ({1})".format(c, ", ".join(t[:3])) for c, t in sorted(cham.items())[:6])) if cham
                else "không còn chữ tả nhân vật của {0}".format(kg))}


def goi_vi(goc: str, log: Callable[[str], None] = print) -> Callable[[str], str]:
    """Hàm gọi AI viết chữ đi VÍ ShopAPI (ép `qua_vi` — lời nhắc ảnh, không Claude Max). Van ví chặn → ném."""
    from .giam_doc.quan_ly import vi_cho_phep  # noqa: PLC0415

    ly = vi_cho_phep(goc)
    if ly:
        raise LoiNhanVat("van ví đang chặn: " + ly)
    from .api import build_client  # noqa: PLC0415
    from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415
    from .goi_van_ban import goi_van_ban, tin_nhan_viet  # noqa: PLC0415

    ch = load_config(os.path.join(goc, CONFIG_FILENAME))
    if ch.problem:
        raise LoiNhanVat("tool chưa đăng nhập được ShopAPI: " + str(ch.problem)[:100])
    client = build_client(ch)
    return lambda p: goi_van_ban(client, tin_nhan_viet(p), mo_hinh="claude-sonnet-5", toi_da_token=TOKEN_VIET,
                                 qua_vi=True, goc=goc, on_log=log)


def sua_kenh(goc: str, ma: str, *, kenh_goc: str = "", goi: Optional[Callable[[str], str]] = None,
             log: Callable[[str], None] = print) -> Dict[str, Any]:
    """Sao lưu rồi viết lại chữ tả nhân vật cũ của kênh `ma`. Trả kết quả `viet_lai_thu_muc` + đường sao lưu."""
    kg = kenh_goc or kenh_goc_cua(goc, ma)
    tu = tu_cu_cua(goc, ma, kg)
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    if not tu or not quet_thu_muc(thu_muc, tu):
        return {"sua": [], "luot": 0, "kenh_goc": kg}
    sl = os.path.join(goc, "workspace", "sao-luu", "nhan-vat", "{0}-{1:%Y%m%d-%H%M%S}".format(ma, _dt.datetime.now()))
    os.makedirs(os.path.join(sl, THU_MUC_PROMPT), exist_ok=True)
    shutil.copy2(os.path.join(thu_muc, TEP_STYLE), os.path.join(sl, TEP_STYLE))
    tp = os.path.join(thu_muc, THU_MUC_PROMPT)
    for ten in os.listdir(tp) if os.path.isdir(tp) else []:
        if ten.endswith(".md"):
            shutil.copy2(os.path.join(tp, ten), os.path.join(sl, THU_MUC_PROMPT, ten))
    lm, pm, _r = nhan_vat(_yaml(os.path.join(thu_muc, TEP_STYLE)))
    kq = viet_lai_thu_muc(thu_muc, tu, goi or goi_vi(goc, log), lock=lm, prompt=pm, log=log)
    kq.update(kenh_goc=kg, sao_luu=sl)
    _ghi_nao(goc, ma, "sua", "viết lại chữ tả nhân vật cũ ({0}) ở {1} chỗ: {2}".format(
        kg, len(kq["sua"]), ", ".join(kq["sua"])[:300]))
    return kq


def _ghi_nao(goc: str, ma: str, loai: str, noi_dung: str) -> None:
    try:
        from . import nao_bo_phan  # noqa: PLC0415

        nao_bo_phan.ghi(goc, "anh-clip", loai, kenh=ma, noi_dung=noi_dung, nguon="nhan_vat_nhat_quan",
                        khoa="nhan-vat:{0}:{1}".format(ma, _dt.date.today().isoformat()))
    except Exception:  # noqa: BLE001 — não hỏng không chặn việc sửa
        pass


# ═══════════════════════════ CLI ═════════════════════════════════════════════
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.nhan_vat_nhat_quan")
    ap.add_argument("lenh", choices=("kiem", "sua"))
    ap.add_argument("kenh", nargs="*")
    ap.add_argument("--goc", default=GOC)
    ap.add_argument("--goc-kenh", default="", help="kênh gốc (mặc định: theo sổ mở kênh / dòng đầu kenh.yaml)")
    a = ap.parse_args(argv)
    if a.lenh == "kiem":
        if a.kenh:
            ds = list(a.kenh)
        else:
            from .ky_nang import _cac_kenh  # noqa: PLC0415

            ds = _cac_kenh(a.goc)
        for ma in ds:
            kq = kiem_kenh(a.goc, ma)
            print("{0}: {1} — {2}".format(ma, kq["tt"], kq["ly_do"]))
        return 0
    loi = 0
    for ma in a.kenh:
        try:
            kq = sua_kenh(a.goc, ma, kenh_goc=a.goc_kenh)
            print("{0}: đã viết lại {1} chỗ{2}".format(ma, len(kq["sua"]), " (sao lưu " + kq["sao_luu"] + ")"
                                                          if kq.get("sao_luu") else ""))
        except Exception as e:  # noqa: BLE001
            loi = 1
            print("{0}: CHƯA SỬA ĐƯỢC — {1}".format(ma, str(e)[:300]))
            _ghi_nao(a.goc, ma, "loi", "viết lại chữ tả nhân vật hỏng: {0}".format(str(e)[:300]))
    return loi


if __name__ == "__main__":
    sys.exit(main())
