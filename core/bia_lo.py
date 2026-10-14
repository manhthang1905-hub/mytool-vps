"""Bìa LÔ — "vẽ vài chục cái rồi chọn cái tốt nhất" (14/10/2026).

═══ VÌ SAO ═══

Chủ kênh soi bìa TL4-T7 v2.199.0 (chữ đã đúng kiểu bìa thắng): *"chưa đạt đâu — các video win nó rất thu hút, ngoài
text thì nó thể hiện nội dung và gây tò mò"*, *"hoặc là thumbnail cho nó vẽ vài chục cái rồi chọn cái tốt nhất"*.
Bìa thắng thật của kênh (`workspace/bia-tl4/thang/`) đều có MỘT bức tranh nói đúng luận điểm của video kèm MANH MỐI
gây tò mò — gợi câu trả lời mà không nói ra: đống túi hiệu/đồng hồ/điện thoại và nhân vật bỏ đi ("người giàu KHÔNG
mua gì?"), bong bóng nghĩ có bộ não phát sáng trên nhân vật lo lắng ("độc thoại = thông minh?"), nhân vật một mình
thư thái còn cả nhóm tụ tập sau khung cửa ("『これ』 là gì?"). Vẽ 3 tấm thì hên xui, nên:

1. ĐẠO DIỄN (LLM qua `goi_van_ban` — Claude Max, tự lùi ShopAPI): tiêu đề + chữ bìa + đầu kịch bản + mục lục + mẫu
   bìa thắng → 6–8 Ý TƯỞNG KHÁC HẲN NHAU {y, manh_moi, doi_lap, canh, mat, tu_the} (+ cách chia chữ bìa).
2. VẼ HÀNG LOẠT: mỗi ý 3–4 ảnh nền (ShopAPI ~100₫/ảnh, tham chiếu = 2–3 bìa thắng thật + nv1.png), ≤ 4 job song
   song, khoá idempotency theo lời nhắc, trần `TRAN_ANH` ảnh/video; ảnh đã có trên đĩa không vẽ lại.
3. BỐ CỤC + LỌC CỨNG (máy): chữ vẽ bằng bộ vẽ hộp v2.199.0; đo ĐẦU nhân vật (`tim_dau`) + bản đồ chủ thể trên nền
   sạch — hộp chữ đè đầu/mặt hay manh mối thì co/dời cột chữ (`CACH_BO_CUC`), vẫn đè thì LOẠI; cổng đọc được
   `do_bia.cham_tep`.
4. GIÁM KHẢO (LLM nhìn ảnh, mô hình mạnh nhất): vòng 1 nhóm ≤ 6 tấm cạnh 2 bìa thắng thật, chấm 1–10 năm mục; tấm
   lọt top được đọc MÙ nền sạch (`soat_bia.doc_anh`) — có chữ/số lạc thì LOẠI; vòng 2 xếp hạng ~6 tấm đứng cạnh nhau
   ở cỡ điện thoại. Ra top 3 + điểm + lý do (`xep-hang.json`) và tờ liên `to-lien.jpg` cho người duyệt.

Dùng: python -X utf8 -m core.bia_lo --kenh TL4-T7 --luot 0001 [--so-y 7 --moi-y 4] [--ra <thư mục>]
      [--chu "同じ車に長く|*乗る人の|ほとんどが"] (tầng "*" = dòng CỰC TO, "^" tách đuôi nhỏ) [--mau <bìa thắng>]
Khâu ảnh bìa dây chuyền đi đường này khi `kenh.yaml: bia_lo: true` (`auto_khau._bia_lo_luot`).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import bia_theo_khuon as btk

__all__ = ["dao_dien", "doc_y_tuong", "doc_chu_bia", "loi_nhac_anh", "sinh_hang_loat", "tim_dau", "dung_bia",
           "cham", "to_lien", "chay", "xuat_goi", "main"]

SO_Y_MAC_DINH, MOI_Y_MAC_DINH, SO_Y_TOI_DA = 7, 4, 8
#: Trần chi phí MỘT video: ảnh nền (100₫/ảnh) và lượt LLM giám khảo (vòng 1 + vòng 2) + lượt đọc mù nền sạch.
TRAN_ANH = 32
TRAN_GOI_CHAM = 12
TRAN_DOC_CHU = 8
SONG_SONG_ANH = 4
SONG_SONG_CHAM = 3
NHOM_CHAM, SO_VONG_2, SO_TOP = 6, 6, 3
#: Mô hình chấm khi lùi ví ShopAPI (đường Claude Max tự đi thang Opus 5.5 → …).
MO_HINH_CHAM = "claude-opus-5"
TRONG_SO = {"to_mo": 0.30, "noi_dung": 0.25, "ro_120": 0.20, "phong_cach": 0.15, "cam_xuc": 0.10}
#: Hộp chữ được chạm tối đa ngần này phần hộp ĐẦU nhân vật / phần CHỦ THỂ (manh mối) của nền sạch.
CHE_DAU_TOI_DA, CHE_MANH_MOI_TOI_DA = 0.02, 0.20
#: Các cách đặt cột chữ thử lần lượt (thu cỡ cả cột, vị trí dọc) — cách đầu là bố cục chuẩn.
CACH_BO_CUC = ((1.0, 0.5), (1.0, 0.3), (1.0, 0.7), (0.86, 0.5), (0.86, 0.25), (0.86, 0.75), (0.76, 0.5))
#: Khuôn hộp chữ khi kênh chưa có khuôn kiểu hộp đo từ bìa thật: hộp đỏ sẫm chữ trắng, cột trái, nhân vật phải.
KHUON_HOP_MAC_DINH: Dict[str, Any] = {"nhan_vat": {"vi_tri": "phai"}, "chu": {"tang": [
    {"vi_tri": v, "mau": ["#FFFFFF"], "khoi_nen": True, "mau_khoi": "#BE392B", "canh": "trai"}
    for v in ("tren", "giua", "duoi")]}}

#: Mẫu ý tưởng (few-shot) — tả tay từ 7 bìa thắng thật TL4-T7 (100k–300k hiển thị) ngày 14/10/2026.
MAU_THANG = """- 「お金持ちほど|買わない物|ほとんどが」: a heap of luxury bags, gold watches, smartphones and gold bars on the \
floor while the figure calmly walks away toward a bright doorway — you see WHAT the rich skip, never WHY.
- 「『これ』を一人でしているなら|あなたのIQは|非常に高い(かも)」: the figure sits alone on a rug with closed eyes and a cup \
of tea, content, while through a lit doorway behind it a faded group chats at a table — "what is これ?".
- 「実は独り言が|多い人は」: a worried figure shrugs under a big glowing blue thought bubble holding a bright brain — hints \
"talking to yourself = smart?" without saying it.
- 「富裕層が|掃除に|執着する本当の理由」: close-up of the figure's serious, determined frown while it wipes a marble \
counter with a cloth — why would a rich person clean by himself?
- 「お金持ちほど|買わない物|ほとんどが」 (2nd winner): the figure raises a palm "no" with a knowing side-eye, holding an \
old wallet, next to a shopping basket overflowing with phones, sneakers, perfume and a watch that faded excited \
people reach for.
- 「高級ブランドに|興味がない|人々の|本当の正体」: the small figure stands still and smiles in the middle of a luxury mall \
while shoppers with bags rush past.
- 「「この人、ズレてる」|低IQの人の|思考の癖」: a sad figure stands apart while faded silhouettes whisper behind it under \
an empty speech bubble."""

LOI_NHAC_DAO_DIEN = """You are the thumbnail CONCEPT DIRECTOR of a Japanese psychology YouTube channel. Its winning \
thumbnails (100k-300k impressions) all work the same way: big deep-red text boxes on the left carry the hook, and on \
the right the channel's plain white round-headed character acts out the video's CORE CLAIM in one concrete picture \
that holds a CURIOSITY CLUE — something the viewer recognises instantly that hints at the surprising answer without \
giving it away, so they must click. How the real winners did it:
{mau}

The winners reuse FIVE clue patterns — build your concepts from them:
  P1 THE LIST ITSELF: when the video lists N things/traits/habits, draw those concrete things as a tempting heap or a \
ring of small glowing icons around the character, and show the character's telling reaction (walks away, refuses, \
proudly owns them) — the viewer wonders "which ones? how many do I have?".
  P2 ALONE vs CROWD: the character calm/content on its own while a faded group does the common thing behind it.
  P3 INSIDE THE HEAD: a big glowing thought bubble or a see-through head revealing the hidden thing (a bright brain, a \
treasure, a memory) — the answer is hinted, not said.
  P4 STRONG FACE + ODD ACT: a close-up, very expressive face doing something surprising for its status or situation.
  P5 JUDGED: faded silhouettes whisper or point while the character reacts.
At least TWO concepts must use P1 or P3. Avoid the OBVIOUS reading of the title (e.g. "people who keep a car long love \
their car"): use the SURPRISING angle the script reveals (hidden money sense, hidden intelligence, a secret habit, \
what others misjudge) — that is where curiosity comes from.

New video — title: {tieu_de}
Hook text on the boxes: {chu_bia}
Chapters: {muc_luc}
Script (opening):
{kich_ban}

Task 1 — "chu": 2-3 alternative markings of the hook, best first. Each copies the hook text EXACTLY and only INSERTS \
marks: "|" between lines (2-4 lines at natural phrase breaks, never starting a line with a particle), "[ ]" around the \
ONE huge line, and optionally "( )" around a soft ending of the huge line such as かも / なのか / だった (drawn small). \
The huge line is the PAYOFF keyword (at most 5 characters), never the opening context words.
Task 2 — "y_tuong": {so_y} DISTINCT concepts — different claim angles and different clue objects, never small \
variations of one idea. Each concept:
  "y": the claim the picture shows (one short English sentence),
  "manh_moi": the curiosity clue — the concrete object or situation that hints at the answer without stating it,
  "doi_lap": the contrast or foil that makes the clue pop (faded silhouettes of other people doing the common or \
opposite thing, a before/after, a doorway onto another scene...),
  "canh": ONE English sentence (at most 45 words) for the image model describing the scene itself (the character, \
the clue, the contrast, the place) — do not describe the empty left side or the layout, that is handled separately,
  "mat": the character's big, readable facial expression,
  "tu_the": its pose.
Rules: concrete and recognisable at 120 px wide — one main clue object, drawn big, no clutter; everyday JAPANESE life \
(apartment, small car, station, convenience store, office, park); bright warm daylight, never dark or gloomy; the \
character and the clue stay on the RIGHT side of the picture, the left side stays plain for the text boxes; NOTHING \
in the picture may carry writing — no letters, numbers, price tags, signs, labels, receipts, contracts, documents, \
books with titles, screens with content, banknotes or medals: pick objects recognisable by SHAPE (coins, piggy bank, \
glowing brain, keys, cup, car, plain shopping bags...). Never put the hook text or any word into "canh".
Return JSON only: {{"chu": ["...", "..."], "y_tuong": [{{"y": "...", "manh_moi": "...", "doi_lap": "...", "canh": \
"...", "mat": "...", "tu_the": "..."}}]}}"""

_SUA_DAO_DIEN = ("\n\nYour previous answer gave only {0} usable concepts (each needs non-empty English y, manh_moi, "
                 "canh, mat; no Japanese words in canh). Return the same JSON with {1} good concepts.")

LOI_NHAC_CHAM_1 = """You are the strict art director of a Japanese psychology YouTube channel. The first {k} images \
are this channel's REAL winning thumbnails (100k-300k impressions) — they are the bar. The next {n} images are \
thumbnail candidates for a NEW video, numbered 1 to {n} in the order shown.

New video — title: {tieu_de}
Hook text in the red boxes: {chu_bia}
Opening of the script (what the video claims): {mo_dau}

Score EVERY candidate from 1 to 10 on:
- "noi_dung": the picture shows THIS video's core claim (not a generic scene);
- "to_mo": it holds a curiosity clue that hints at the surprising answer without giving it away, so a viewer must \
click — the trick every winner uses;
- "ro_120": it reads instantly when shrunk to about 120 px on a phone: one big clear subject and clue, no clutter, the \
text boxes do not hide the character's face or the clue;
- "cam_xuc": the character's face shows a strong, readable emotion that fits the story;
- "phong_cach": it looks as good as the winners (bright warm clean illustration, the same plain white round-headed \
character, polished).
"loi": hard defects you can SEE, else []: "stray text" (any letters, numbers, symbols or price tags in the picture \
outside the red boxes), "deformed character", "face covered", "panel split" (a visible seam or dividing line — the \
picture looks like two panels), "photo people".
Be comparative and strict: 9-10 only if it is as strong as the winners; an average candidate is 5-6.
Return JSON only: {{"ung_vien": [{{"so": 1, "noi_dung": 0, "to_mo": 0, "ro_120": 0, "cam_xuc": 0, "phong_cach": 0, \
"loi": [], "ly_do": "one short line IN VIETNAMESE: what works and what is missing"}}]}} — one item per candidate."""

LOI_NHAC_CHAM_2 = """The first {k} images are this Japanese psychology channel's REAL winning thumbnails. The LAST \
image is a sheet of {n} thumbnail candidates for a new video, each numbered at its top-left corner, shown at \
phone-feed size.
New video — title: {tieu_de}; hook text: {chu_bia}
Rank ALL {n} candidates, best first: which one would a Japanese viewer scrolling the YouTube home feed most want to \
click, because the picture shows the video's claim with a curiosity clue that hints at the answer without giving it \
away, reads instantly at this size, carries a strong emotion and looks as good as the winners?
Return JSON only: {{"xep_hang": [best number, ..., worst number], "ly_do": {{"<number>": "one short line IN \
VIETNAMESE"}}}}"""

_RE_CJK = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
_RE_CHU_LA = re.compile(r"[0-9A-Za-z$%¥€£぀-ヿ㐀-鿿]")


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with io.open(duong + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tmp", duong)


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _bam(*phan: Any) -> str:
    return hashlib.sha256("|".join(str(p) for p in phan).encode("utf-8")).hexdigest()[:10]


def _json(tho: Any) -> Any:
    from .goi_van_ban import loc_json  # noqa: PLC0415
    try:
        return loc_json(str(tho or ""))
    except ValueError:
        return None


# ── 1) Đạo diễn ý tưởng ──────────────────────────────────────────────────────


def doc_y_tuong(du: Any, toi_da: int = SO_Y_TOI_DA) -> List[Dict[str, str]]:
    """JSON đạo diễn → các ý tưởng SẠCH: đủ `y`/`manh_moi`/`canh`/`mat`, `canh` tiếng Anh (có chữ Nhật = mô hình ảnh
    dễ vẽ chữ → bỏ), không trùng cảnh; cắt dài; tối đa `toi_da` (≤ `SO_Y_TOI_DA`)."""
    ds = du.get("y_tuong") if isinstance(du, dict) else du
    ra: List[Dict[str, str]] = []
    da: set = set()
    for x in ds if isinstance(ds, list) else []:
        if not isinstance(x, dict):
            continue
        y = {k: " ".join(str(x.get(k) or "").split())[:n] for k, n in
             (("y", 200), ("manh_moi", 240), ("doi_lap", 240), ("canh", 420), ("mat", 120), ("tu_the", 120))}
        khoa = y["canh"].lower()[:80]
        if not all(y[k] for k in ("y", "manh_moi", "canh", "mat")) or _RE_CJK.search(y["canh"]) or khoa in da:
            continue
        da.add(khoa)
        ra.append(y)
    return ra[:max(1, min(int(toi_da), SO_Y_TOI_DA))]


def dao_dien(goi: Callable[..., str], *, tieu_de: str, chu_bia: str, kich_ban: str = "", muc_luc: Sequence[str] = (),
             so_y: int = SO_Y_MAC_DINH, khoa: str = "bia-lo") -> Dict[str, Any]:
    """MỘT lượt LLM (+ một lượt sửa khi < 3 ý dùng được) → `{"y_tuong": [...], "chu": [cách chia chữ bìa]}`."""
    so_y = max(1, min(int(so_y), SO_Y_TOI_DA))
    loi_nhac = LOI_NHAC_DAO_DIEN.format(mau=MAU_THANG, tieu_de=tieu_de, chu_bia=chu_bia, so_y=so_y,
                                        muc_luc=" / ".join(str(m) for m in muc_luc)[:900] or "(none)",
                                        kich_ban=str(kich_ban or "")[:4000] or "(none)")
    du = _json(goi(loi_nhac, khoa=khoa + ":dao-dien", toi_da_token=6000, mo_hinh=MO_HINH_CHAM))
    ys = doc_y_tuong(du, so_y)
    if len(ys) < min(3, so_y):
        du2 = _json(goi(loi_nhac + _SUA_DAO_DIEN.format(len(ys), so_y), khoa=khoa + ":dao-dien:sua",
                        toi_da_token=6000, mo_hinh=MO_HINH_CHAM))
        if len(doc_y_tuong(du2, so_y)) > len(ys):
            du, ys = du2, doc_y_tuong(du2, so_y)
    chu = (du or {}).get("chu") if isinstance(du, dict) else None
    return {"y_tuong": ys, "chu": [c for c in (chu if isinstance(chu, list) else [chu]) if isinstance(c, str)][:3]}


def doc_chu_bia(chu: str, kc: Dict[str, Any], *, cach_ai: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """Chữ bìa → tầng chữ kiểu HỘP đã bố trí. `chu` có dấu ("a|*b|c^d": "|" xuống dòng, "*" dòng CỰC TO, "^" tách đuôi
    nhỏ) thì theo đúng dấu; chữ trơn thì theo cách chia AI (`cach_ai`, phải giữ trọn chữ), không có thì chia máy."""
    s = str(chu or "").strip()
    if "|" in s or s.startswith("*"):
        dau = "|".join(("[" + p[1:].replace("^", "(") + (")" if "^" in p else "") + "]") if p.startswith("*")
                       else p.replace("^", "") for p in (x.strip() for x in s.split("|")) if p)
        tang = btk._doc_chu_danh_dau(dau)  # noqa: SLF001
        if sum(1 for t in tang if t.get("to")) != 1:
            tang = btk.chuan_thu_bac(tang)
    else:
        cac = btk._cac_tang_ai({"chu": list(cach_ai)}, s, True) if cach_ai else []  # noqa: SLF001
        tang = btk.chon_tang_hop(cac, s) if cac else btk.tach_chu_mac_dinh(s, kc)
    for i, t in enumerate(tang):
        t["vi_tri"] = "tren" if i == 0 else ("duoi" if i == len(tang) - 1 else "giua")
    return btk.bo_tri_chu("khuon", btk.gan_kieu_khuon(tang, kc), kc)


def chu_tron(chu: str) -> str:
    """Chữ bìa bỏ dấu đánh dấu ("同じ車に長く|*乗る人の|ほとんどが" → "同じ車に長く乗る人のほとんどが")."""
    return re.sub(r"[|*^\[\]()]", "", str(chu or "")).strip()


# ── 2) Vẽ hàng loạt ──────────────────────────────────────────────────────────


def loi_nhac_anh(y: Dict[str, str], kc: Dict[str, Any], nen: str = "") -> str:
    """Ý tưởng → lời nhắc ảnh NỀN (không chữ) theo `btk.loi_nhac_hop_chu` (nét bìa thắng, nhân vật kênh, phía chữ
    trống), cảnh = `canh` + manh mối vẽ to rõ + đối lập."""
    canh = "{0} The curiosity clue, drawn big, clear and instantly recognisable: {1}{2}".format(
        y["canh"].rstrip("."), y["manh_moi"].rstrip("."), (". Contrast: " + y["doi_lap"].rstrip(".")) if y.get(
            "doi_lap") else "")
    return btk.loi_nhac_hop_chu(kc, bien_the={"canh": canh, "net_mat": y.get("mat", ""), "tu_the": y.get("tu_the", "")},
                                nen=nen) + " " + LIEN_MACH


#: 14/10/2026 (lô thật TL4-T7-0001: giám khảo loại 8/20 nền vì "panel split" — nửa trái là một tấm phẳng có mép dọc).
LIEN_MACH = ("The background is ONE continuous scene across the whole width: the empty part is simply the same wall, "
             "floor and light continuing, softly out of focus — never a separate flat panel, block of colour or "
             "vertical edge.")


def sinh_hang_loat(ve: Callable[[str, int, str, List[str]], List[str]], ds_y: Sequence[Dict[str, str]], moi_y: int,
                   thu_muc: str, *, kc: Dict[str, Any], nen: str = "", tran: int = TRAN_ANH,
                   song_song: int = SONG_SONG_ANH, khoa: str = "bia-lo", log: Callable[[str], None] = print,
                   dem: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Mỗi ý `moi_y` ảnh nền (MỘT job n ảnh / ý), tổng ≤ `tran`, ≤ `song_song` (≤ 4) job cùng lúc. `ve(lời nhắc, n,
    khoá, [đích…]) -> [tệp đã có]`. Nền đã có trên đĩa thì không gọi lại (chạy tiếp không trả tiền lần hai); khoá =
    băm lời nhắc nên cùng việc → cùng job. Trả ứng viên `{ma, y, bien, nen}`; `dem["anh"]` += số ảnh đặt mới."""
    os.makedirs(thu_muc, exist_ok=True)
    dem = dem if dem is not None else {}
    viec, con = [], max(0, int(tran))
    for i, y in enumerate(ds_y, 1):
        n = min(max(1, int(moi_y)), 8, con)
        if n <= 0:
            log("  bìa lô: chạm trần {0} ảnh — bỏ ý {1} trở đi".format(tran, i))
            break
        con -= n
        ln = loi_nhac_anh(y, kc, nen)
        viec.append((i, ln, [os.path.join(thu_muc, "y{0:02d}-{1}-nen.png".format(i, j)) for j in range(1, n + 1)]))
    khoa_dem = threading.Lock()

    def mot(v) -> None:
        i, ln, dich = v
        # Job đã giao (dù nhà cung cấp trả THIẾU ảnh — lô thật 14/10: 2–3/4) thì không đặt lại: đặt lại là trả tiền lần hai.
        if any(os.path.isfile(d) for d in dich):
            return
        try:
            with khoa_dem:
                dem["anh"] = dem.get("anh", 0) + len(dich)
            co = ve(ln, len(dich), "{0}:y{1}:{2}".format(khoa, i, _bam(ln, len(dich))), dich)
            for d in co:
                _chuan_nen(d)
            log("  bìa lô: ý {0} — {1}/{2} ảnh".format(i, len(co), len(dich)))
        except Exception as loi:  # noqa: BLE001 — một ý hỏng không giết cả lô
            log("  (bìa lô: ý {0} vẽ hỏng: {1})".format(i, str(loi)[:160]))
    with ThreadPoolExecutor(max_workers=max(1, min(int(song_song), SONG_SONG_ANH))) as ex:
        list(ex.map(mot, viec))
    return [{"ma": os.path.basename(d)[:-8], "y": i, "bien": j, "nen": d}
            for i, _ln, dich in viec for j, d in enumerate(dich, 1) if os.path.isfile(d)]


def _chuan_nen(duong: str) -> None:
    """Ảnh nền vừa tải: xoá dấu sao nhà cung cấp, đưa về đúng 1280×720 (toạ độ đo đầu = toạ độ vẽ chữ)."""
    from PIL import Image, ImageOps  # noqa: PLC0415
    try:
        from .xoa_dau_anh import xoa_dau_tep  # noqa: PLC0415
        xoa_dau_tep(duong)
    except Exception:  # noqa: BLE001 — dấu còn thì bìa vẫn dùng được
        pass
    with Image.open(duong) as im:
        if im.size == (1280, 720):
            return
        im2 = ImageOps.fit(im.convert("RGB"), (1280, 720), method=Image.LANCZOS)
    im2.save(duong + ".tmp.png", format="PNG")
    os.replace(duong + ".tmp.png", duong)


# ── 3) Bố cục + lọc cứng ─────────────────────────────────────────────────────


def tim_dau(anh) -> List[List[float]]:
    """Các hộp ĐẦU nhân vật (px trên `anh`, lớn trước) — nhân vật kênh là hình tròn TRẮNG viền ĐEN: thành phần liền (4
    hướng, lưới 320×180) trắng ít sắc, gần tròn (rộng/cao 0,75–1,35, lấp ≥ 60% hộp), ≥ 0,4% khung, ≥ 20% vành ngoài là
    nét đen. Đo 14/10 trên 7 nền thật TL4: bắt đúng đầu, không bắt cửa sáng/chữ trắng (vành không đen). Lấy MỌI đầu, không
    chỉ đầu lớn nhất: lô thật 0002 — bóng nhân vật trong GƯƠNG (chính là manh mối) bị hộp chữ che nửa mặt. [] = không
    thấy."""
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    from .do_bia import _gian  # noqa: PLC0415
    W, H = anh.size
    w, h = 320, 180
    a = np.asarray(anh.convert("RGB").resize((w, h), Image.BOX)).astype(np.int16)
    mn, mx = a.min(axis=2), a.max(axis=2)
    trang, den = (mn >= 205) & (mx - mn <= 26), mx <= 120  # nét đen ~1 ô ở lưới nhỏ bị trộn với nền → ≤ 120
    nhan = np.zeros((h, w), dtype=np.int32)
    ra, k = [], 0
    for y0, x0 in zip(*np.nonzero(trang)):
        if nhan[y0, x0]:
            continue
        k += 1
        nhan[y0, x0], ngan, px = k, [(y0, x0)], []
        while ngan:
            y, x = ngan.pop()
            px.append((y, x))
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and trang[yy, xx] and not nhan[yy, xx]:
                    nhan[yy, xx] = k
                    ngan.append((yy, xx))
        ys, xs = np.asarray(px).T
        b0, b1, a0, a1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        bw, bh = a1 - a0, b1 - b0
        if len(px) < 0.004 * w * h or not (0.75 <= bw / float(bh) <= 1.35) or len(px) < 0.6 * bw * bh:
            continue
        c0, c1, d0, d1 = max(0, b0 - 3), min(h, b1 + 3), max(0, a0 - 3), min(w, a1 + 3)
        m = nhan[c0:c1, d0:d1] == k
        vanh = _gian(m, 2) & ~m
        if vanh.any() and float(den[c0:c1, d0:d1][vanh].mean()) >= 0.2:
            ra.append((len(px), [a0 * W / w, b0 * H / h, a1 * W / w, b1 * H / h]))
    return [b for _n, b in sorted(ra, key=lambda x: -x[0])]


def _phan_giao(hop: Sequence[float], cac: Sequence[Sequence[float]]) -> float:
    """Phần diện tích `hop` nằm dưới các hộp `cac` (cộng dồn, ≤ 1)."""
    dt = max(1.0, (hop[2] - hop[0]) * (hop[3] - hop[1]))
    return min(1.0, sum(max(0.0, min(hop[2], b[2]) - max(hop[0], b[0])) * max(0.0, min(hop[3], b[3]) - max(hop[1], b[1]))
                        for b in cac) / dt)


def dung_bia(uv: Dict[str, Any], tang: Sequence[Dict[str, Any]], *, goc: str = "", ngon_ngu: str = "ja"
             ) -> Dict[str, Any]:
    """Vẽ chữ lên nền sạch `uv["nen"]` → `uv["tep"]` (jpg 1280×720 + báo cáo đo) và LỌC CỨNG: hộp chữ không được đè
    đầu nhân vật (> `CHE_DAU_TOI_DA`) hay chủ thể/manh mối (> `CHE_MANH_MOI_TOI_DA`) — thử lần lượt `CACH_BO_CUC` (co,
    dời cột chữ; đầu nhân vật là vùng NÉ của bộ vẽ), hết cách thì loại; rồi cổng đọc được `do_bia.cham_tep` phải
    ĐẠT. `uv["loai"]` = lý do loại ("" = qua)."""
    from PIL import Image  # noqa: PLC0415
    from . import chon_bia, do_bia  # noqa: PLC0415
    anh = Image.open(uv["nen"]).convert("RGB")
    W, H = anh.size
    dau = tim_dau(anh)
    uv.update(dau=[[round(v) for v in d] for d in dau], loai="")
    tranh = [[d[0] - 0.03 * W, d[1] - 0.03 * H, d[2] + 0.03 * W, d[3] + 0.03 * H] for d in dau]
    png = uv["nen"][:-len("-nen.png")] + ".png"
    che_dau = che_mm = 1.0
    for ep, doc in CACH_BO_CUC:
        bc: Dict[str, Any] = {}
        if not btk.ve_chu_len_anh(uv["nen"], png, tang, goc=goc, ngon_ngu=ngon_ngu, anh_nen=anh, bao_cao=bc,
                                  tranh_them=tranh, ep_co=ep, doc=doc):
            uv["loai"] = "không vẽ được chữ (thiếu phông?)"
            return uv
        hop = [h["hop"] for h in bc.get("hop_chu") or []]
        che_dau = max([_phan_giao(d, hop) for d in dau] or [0.0])
        che_mm = float((bc.get("bo_cuc") or {}).get("hop_che_chu_the") or 0.0)
        if che_dau <= CHE_DAU_TOI_DA and che_mm <= CHE_MANH_MOI_TOI_DA:
            break
    uv.update(bo_cuc=[ep, doc], che_dau=round(che_dau, 3), che_manh_moi=round(che_mm, 3),
              tep=png[:-4] + ".jpg")
    chon_bia._xuat_jpg(png, uv["tep"])  # noqa: SLF001
    os.remove(png)
    if che_dau > CHE_DAU_TOI_DA:
        uv["loai"] = "hộp chữ đè đầu nhân vật ({0:.0%})".format(che_dau)
    elif che_mm > CHE_MANH_MOI_TOI_DA:
        uv["loai"] = "hộp chữ che chủ thể/manh mối ({0:.0%})".format(che_mm)
    else:
        kq = do_bia.cham_tep(uv["tep"])
        uv["doc_duoc"] = do_bia.tom_tat(kq)
        if kq.get("dat") is not True:
            uv["loai"] = "cổng đọc được: " + uv["doc_duoc"][:160]
    return uv


# ── 4) Giám khảo ─────────────────────────────────────────────────────────────


def _url_anh(nguon: Any, rong: int = 640, cat: bool = True) -> str:
    """Ảnh → data URL JPEG bề ngang `rong` (`cat` = cắt đúng 16:9; tờ liên giữ tỉ lệ)."""
    from PIL import Image, ImageOps  # noqa: PLC0415
    im = (nguon if hasattr(nguon, "size") else Image.open(nguon)).convert("RGB")
    im = ImageOps.fit(im, (rong, rong * 9 // 16), method=Image.LANCZOS) if cat else \
        im.resize((rong, max(1, round(im.size[1] * rong / im.size[0]))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _so(v: Any) -> Optional[float]:
    try:
        return max(1.0, min(10.0, float(v)))
    except (TypeError, ValueError):
        return None


def doc_cham_1(du: Any, n: int) -> Dict[int, Dict[str, Any]]:
    """JSON vòng 1 → {số tấm (1..n): {diem, tong 0–100, loi, ly_do}}; tấm thiếu mục điểm thì bỏ."""
    ra: Dict[int, Dict[str, Any]] = {}
    for x in (du.get("ung_vien") if isinstance(du, dict) else du) or []:
        if not isinstance(x, dict):
            continue
        try:
            so = int(x.get("so"))
        except (TypeError, ValueError):
            continue
        diem = {k: _so(x.get(k)) for k in TRONG_SO}
        if not 1 <= so <= n or None in diem.values():
            continue
        loi = [str(e)[:60] for e in (x.get("loi") if isinstance(x.get("loi"), list) else [x.get("loi")])
               if e and str(e).strip().lower() not in ("none", "no", "n/a", "-", "[]", "false")]
        ra[so] = {"diem": diem, "tong": round(10 * sum(TRONG_SO[k] * v for k, v in diem.items()), 1),
                  "loi": loi, "ly_do": str(x.get("ly_do") or "")[:240]}
    return ra


def doc_cham_2(du: Any, n: int) -> List[int]:
    """JSON vòng 2 → thứ hạng (số tấm 1..n, không trùng, theo thứ tự)."""
    ra: List[int] = []
    for x in (du.get("xep_hang") if isinstance(du, dict) else None) or []:
        try:
            so = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= so <= n and so not in ra:
            ra.append(so)
    return ra


def cham(goi: Callable[..., str], ds: List[Dict[str, Any]], *, mau: Sequence[str], tieu_de: str, chu_bia: str,
         mo_dau: str = "", thu_muc: str = "", khoa: str = "bia-lo", log: Callable[[str], None] = print,
         dem: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Chấm các ứng viên QUA lọc cứng → danh sách xếp hạng (tốt nhất trước; tấm loại/chưa chấm ở cuối).

    Vòng 1: nhóm ≤ `NHOM_CHAM` (xen kẽ ý để mỗi nhóm có nhiều ý), mỗi nhóm một lượt cạnh 2 bìa thắng; `loi` thấy được
    → loại. Đọc mù nền sạch ≤ `TRAN_DOC_CHU` tấm điểm cao nhất (`soat_bia.doc_anh`): có chữ/số → loại. Vòng 2: ≤
    `SO_VONG_2` tấm trên một tờ cỡ điện thoại → thứ hạng. Trần lượt chấm `TRAN_GOI_CHAM` (vòng 1 + vòng 2)."""
    from . import soat_bia  # noqa: PLC0415
    dem = dem if dem is not None else {}
    mau_url = [_url_anh(m) for m in list(mau)[:2]]
    tt = {"tieu_de": tieu_de, "chu_bia": chu_bia, "mo_dau": " ".join(str(mo_dau or "").split())[:700] or "(none)"}
    qua = sorted([u for u in ds if not u.get("loai")], key=lambda u: (u["bien"], u["y"]))
    nhom = [qua[i:i + NHOM_CHAM] for i in range(0, len(qua), NHOM_CHAM)][:max(1, TRAN_GOI_CHAM - 1)]
    khoa_dem = threading.Lock()

    def goi_dem(loi_nhac: str, **kw) -> str:
        with khoa_dem:
            dem["llm"] = dem.get("llm", 0) + 1
        return goi(loi_nhac, **kw)

    def vong_1(i_g) -> None:
        i, g = i_g
        try:
            tho = goi_dem(LOI_NHAC_CHAM_1.format(k=len(mau_url), n=len(g), **tt), khoa="{0}:cham1:{1}".format(
                khoa, _bam(*[u["ma"] for u in g])), toi_da_token=3000, mo_hinh=MO_HINH_CHAM,
                anh=mau_url + [_url_anh(u["tep"]) for u in g])
            kq = doc_cham_1(_json(tho), len(g))
        except Exception as loi:  # noqa: BLE001 — nhóm hỏng: các tấm ấy chưa có điểm
            log("  (bìa lô: chấm nhóm {0} hỏng: {1})".format(i + 1, str(loi)[:160]))
            return
        for so, k in kq.items():
            g[so - 1].update(k)
            if k["loi"]:
                g[so - 1]["loai"] = "giám khảo thấy lỗi: " + ", ".join(k["loi"])
    with ThreadPoolExecutor(max_workers=SONG_SONG_CHAM) as ex:
        list(ex.map(vong_1, enumerate(nhom)))

    def con() -> List[Dict[str, Any]]:
        return sorted([u for u in qua if not u.get("loai") and u.get("tong") is not None], key=lambda u: -u["tong"])

    def doc_mu(u) -> None:
        d = soat_bia.doc_anh(goi_dem, u["nen"], khoa="{0}:doc-nen:{1}".format(khoa, u["ma"]))
        if d is None:
            return
        u["chu_nen"] = " | ".join([d.get("chu") or ""] + list(d.get("chu_thua") or []))[:120]
        la = chu_la(d)
        if la:
            u["loai"] = "chữ/số lạc trên nền: 「{0}」".format(la[:40])
    with ThreadPoolExecutor(max_workers=SONG_SONG_CHAM) as ex:
        list(ex.map(doc_mu, con()[:TRAN_DOC_CHU]))

    top = con()[:SO_VONG_2]
    if len(top) >= 2:
        import tempfile  # noqa: PLC0415
        to = to_lien(top, os.path.join(thu_muc or tempfile.gettempdir(), "_vong-2.jpg"), o=(426, 240), chu=False)
        try:
            tho = goi_dem(LOI_NHAC_CHAM_2.format(k=len(mau_url), n=len(top), **tt), khoa="{0}:cham2:{1}".format(
                khoa, _bam(*[u["ma"] for u in top])), toi_da_token=2000, mo_hinh=MO_HINH_CHAM,
                anh=mau_url + [_url_anh(to, 1280, cat=False)])
            du = _json(tho)
            for h, so in enumerate(doc_cham_2(du, len(top)), 1):
                top[so - 1]["hang_2"] = h
                top[so - 1]["ly_do_2"] = str(((du or {}).get("ly_do") or {}).get(str(so)) or "")[:240]
        except Exception as loi:  # noqa: BLE001 — vòng 2 hỏng: giữ thứ tự vòng 1
            log("  (bìa lô: vòng 2 hỏng: {0} — giữ thứ tự vòng 1)".format(str(loi)[:160]))
    return sorted(ds, key=lambda u: (bool(u.get("loai")), u.get("tong") is None, u.get("hang_2") or 99,
                                     -(u.get("tong") or 0)))


def chu_la(d: Dict[str, Any]) -> str:
    """Chữ/số LẠC thật sự trong kết quả đọc mù nền sạch (`soat_bia.doc_anh`; '' = sạch): các dòng chữ đọc ra, mục
    `chu_thua` NGẮN (bỏ phần tả trong ngoặc) và chữ trong ngoặc kép của câu tả. Lô thật 14/10: AI ghi câu TẢ vào
    `chu_thua` ("Lock-icon-like marks on the car key fob", "✦ (faint sparkle watermark)") — câu tả dài và dấu sao nhà
    cung cấp không tính."""
    ra: List[str] = []
    for i, x in enumerate(list(d.get("dong") or []) + list(d.get("chu_thua") or [])):
        x = re.sub(r"\(.*?\)|（.*?）", "", str(x)).strip()
        if not x or re.search(r"sparkle|watermark|✦|^no\b|^none\b", x, re.I):
            continue
        trich = re.findall(r"[\"“「『](.+?)[\"”」』]", x)
        ra += trich or ([x] if i < len(d.get("dong") or []) or len(x) <= 15 else [])
    return " ".join(s for s in ra if _RE_CHU_LA.search(s)).strip()


def _phong(co: int):
    from PIL import ImageFont  # noqa: PLC0415
    duong = btk._tim_font("", "0123", "ja", kieu="hop")  # noqa: SLF001
    return ImageFont.truetype(duong, max(10, int(co))) if duong else ImageFont.load_default()


def to_lien(ds: Sequence[Dict[str, Any]], dich: str, *, o=(640, 360), cot: int = 3, chu: bool = True) -> str:
    """Tờ liên các tấm (số thứ tự to ở góc; `chu` = dòng điểm nhỏ dưới mỗi tấm) → JPG `dich`."""
    from PIL import Image, ImageDraw, ImageOps  # noqa: PLC0415
    hang, le, cao_chu = max(1, (len(ds) + cot - 1) // cot), 12, (52 if chu else 0)
    to = Image.new("RGB", (cot * o[0] + (cot + 1) * le, hang * (o[1] + cao_chu + le) + le), (24, 24, 28))
    ve, f_so, f_chu = ImageDraw.Draw(to), _phong(o[1] * 0.16), _phong(18)
    for i, u in enumerate(ds):
        x, y = le + (i % cot) * (o[0] + le), le + (i // cot) * (o[1] + cao_chu + le)
        with Image.open(u["tep"]) as im:
            to.paste(ImageOps.fit(im.convert("RGB"), o, method=Image.LANCZOS), (x, y))
        r = int(o[1] * 0.22)
        ve.rounded_rectangle((x + 6, y + 6, x + 6 + r, y + 6 + r), radius=r // 4, fill=(20, 20, 20))
        ve.text((x + 6 + r / 2, y + 6 + r / 2), str(i + 1), font=f_so, fill=(255, 230, 60), anchor="mm")
        if chu:
            d = u.get("diem") or {}
            ve.text((x + 2, y + o[1] + 5), "#{0}   {1}/100   {2}{3}".format(
                i + 1, "{0:.0f}".format(u["tong"]) if u.get("tong") is not None else "?", u.get("ma", ""),
                "   vòng 2: hạng {0}".format(u["hang_2"]) if u.get("hang_2") else ""), font=f_chu, fill=(240, 240, 240))
            ve.text((x + 2, y + o[1] + 28), "tò mò {0:.0f} · nội dung {1:.0f} · rõ {2:.0f} · cảm xúc {3:.0f} · phong "
                    "cách {4:.0f}".format(*[d.get(k) or 0 for k in ("to_mo", "noi_dung", "ro_120", "cam_xuc",
                                                                      "phong_cach")]), font=f_chu, fill=(190, 190, 190))
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    to.save(dich, format="JPEG", quality=90)
    return dich


# ── Cả lô ────────────────────────────────────────────────────────────────────


def _doc_luot(thu_muc_luot: str) -> Dict[str, Any]:
    tieu_de, chu_bia = "", ""
    try:
        with io.open(os.path.join(thu_muc_luot, "1-tieu-de.txt"), encoding="utf-8") as tep:
            for dong in tep:
                if dong.strip().startswith("TITLE:"):
                    tieu_de = dong.split(":", 1)[1].strip()
                elif dong.strip().startswith("THUMB:"):
                    chu_bia = dong.split(":", 1)[1].strip()
    except OSError:
        pass
    try:
        with io.open(os.path.join(thu_muc_luot, "1-kich-ban.txt"), encoding="utf-8") as tep:
            kich_ban = tep.read(4000)
    except OSError:
        kich_ban = ""
    ml = _doc_json(os.path.join(thu_muc_luot, "3-muc-luc.json"))
    nhan = next((v.get("nhan") for v in ml.values() if isinstance(v, dict)), []) if isinstance(ml, dict) else []
    return {"tieu_de": tieu_de, "chu_bia": chu_bia, "kich_ban": kich_ban, "muc_luc": [str(x) for x in nhan or []]}


def mau_cua_kenh(goc: str, kenh: str, mau: Sequence[str] = ()) -> List[str]:
    """2–3 bìa thắng THẬT làm mẫu (sáng/sạch nhất — `btk.chon_anh_mau_phong_cach`): `mau` (tệp/thư mục) > `tep_mau` của
    khuôn kênh > `kenh.yaml: bia_lo_mau` (thư mục)."""
    cac = list(mau)
    if not cac:
        try:
            from . import khuon_bia  # noqa: PLC0415
            k = khuon_bia.doc_khuon(goc, kenh) or {}
            cac = list(k.get("tep_mau") or ([k["tep"]] if k.get("tep") else []))
        except Exception:  # noqa: BLE001
            cac = []
    if not cac:
        try:
            from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
            d = str((doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}).get("bia_lo_mau") or "")
            cac = [os.path.join(goc, d) if d and not os.path.isabs(d) else d] if d else []
        except Exception:  # noqa: BLE001
            cac = []
    tep: List[str] = []
    for c in cac:
        tep += sorted(os.path.join(c, t) for t in os.listdir(c) if t.lower().endswith((".jpg", ".jpeg", ".png"))) \
            if os.path.isdir(c) else [c]
    return btk.chon_anh_mau_phong_cach([t for t in tep if os.path.isfile(t)], toi_da=3)


def chay(goc: str, kenh: str, *, thu_muc_luot: str, ra: str, chu: str = "", so_y: int = SO_Y_MAC_DINH,
         moi_y: int = MOI_Y_MAC_DINH, goi: Callable[..., str], ve: Callable[..., List[str]],
         mau: Sequence[str] = (), log: Callable[[str], None] = print, ngon_ngu: str = "ja", khoa: str = ""
         ) -> Dict[str, Any]:
    """Cả lô cho MỘT lượt → `<ra>/ung-vien/*.jpg`, `<ra>/xep-hang.json`, `<ra>/to-lien.jpg`, `<ra>/top-N.jpg`. Trả bản
    xếp hạng (`top` = ≤ `SO_TOP` tấm qua mọi lọc, tốt nhất trước). Chạy lại: ý tưởng + nền trên đĩa được dùng lại;
    `xep-hang.json` đúng bộ ứng viên + chữ thì trả luôn (không gọi LLM). `khoa` = tiền tố khoá idempotency (lô bìa
    làm lại của dây chuyền đổi tiền tố)."""
    t0 = time.time()
    lu = _doc_luot(thu_muc_luot)
    chu = str(chu or lu["chu_bia"]).strip()
    if not chu:
        raise RuntimeError("bìa lô: không có chữ bìa (THUMB trong 1-tieu-de.txt hoặc --chu)")
    hook = chu_tron(chu)
    try:
        from . import khuon_bia  # noqa: PLC0415
        kc = (khuon_bia.doc_khuon(goc, kenh) or {}).get("khuon_chu") or {}
    except Exception:  # noqa: BLE001
        kc = {}
    kc = kc if btk.kieu_hop(kc) else KHUON_HOP_MAC_DINH
    mau = mau_cua_kenh(goc, kenh, mau)
    if not mau:
        raise RuntimeError("bìa lô: không có bìa thắng thật làm mẫu (khuôn kênh / --mau / kenh.yaml bia_lo_mau)")
    dem: Dict[str, int] = {"anh": 0, "llm": 0}
    khoa = khoa or "bia-lo:{0}:{1}".format(kenh, os.path.basename(os.path.normpath(thu_muc_luot)))

    def goi_dem(loi_nhac: str, **kw) -> str:
        dem["llm"] += 1
        return goi(loi_nhac, **kw)
    tep_y = os.path.join(ra, "y-tuong.json")
    yt = _doc_json(tep_y) or {}
    if not (yt.get("y_tuong") and yt.get("dau_vao") == _bam(lu["tieu_de"], hook, so_y)):
        log("  bìa lô: đạo diễn viết {0} ý tưởng…".format(so_y))
        yt = dict(dao_dien(goi_dem, tieu_de=lu["tieu_de"], chu_bia=hook, kich_ban=lu["kich_ban"],
                           muc_luc=lu["muc_luc"], so_y=so_y, khoa=khoa), dau_vao=_bam(lu["tieu_de"], hook, so_y))
        if not yt["y_tuong"]:
            raise RuntimeError("bìa lô: đạo diễn không ra ý tưởng nào dùng được")
        _ghi_json(tep_y, yt)
    tang = doc_chu_bia(chu, kc, cach_ai=yt.get("chu") or ())
    chu_ve = "".join(btk.chu_cua_tang(t) for t in tang)
    nen = str(btk.cau_hinh_kenh(goc, kenh).get("bia_hop_nen") or "")
    uv = sinh_hang_loat(ve, yt["y_tuong"], moi_y, os.path.join(ra, "ung-vien"), kc=kc, nen=nen, khoa=khoa, log=log,
                        dem=dem)
    if not uv:
        raise RuntimeError("bìa lô: không vẽ được ảnh nền nào")
    van_tay = _bam(chu_ve, *sorted("{0}:{1}".format(u["ma"], os.path.getsize(u["nen"])) for u in uv))
    cu = _doc_json(os.path.join(ra, "xep-hang.json")) or {}
    if cu.get("van_tay") == van_tay and cu.get("top") and all(os.path.isfile(t["tep"]) for t in cu["top"]):
        log("  bìa lô: đã xếp hạng đúng bộ ứng viên này — dùng lại")
        return cu
    for u in uv:
        dung_bia(u, tang, goc=goc, ngon_ngu=ngon_ngu)
    log("  bìa lô: {0}/{1} tấm qua lọc cứng (đầu nhân vật, manh mối, đọc được)".format(
        sum(1 for u in uv if not u["loai"]), len(uv)))
    xh = cham(goi, uv, mau=mau, tieu_de=lu["tieu_de"], chu_bia=chu_ve, mo_dau=lu["kich_ban"][:800], thu_muc=ra,
              khoa=khoa, log=log, dem=dem)
    top = [u for u in xh if not u.get("loai") and u.get("tong") is not None][:SO_TOP]
    for i, u in enumerate(top, 1):
        shutil.copy2(u["tep"], os.path.join(ra, "top-{0}.jpg".format(i)))
    ket = {"kenh": kenh, "luot": os.path.basename(os.path.normpath(thu_muc_luot)), "tieu_de": lu["tieu_de"],
           "chu": chu, "chu_ve": chu_ve, "chu_tang": tang, "mau": mau, "van_tay": van_tay,
           "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "giay": round(time.time() - t0),
           "chi_phi": {"anh_dat_moi": dem["anh"], "vnd_anh_uoc": dem["anh"] * 100, "anh_tong": len(uv),
                       "llm": dem["llm"]},
           "so_qua_loc": sum(1 for u in uv if not u.get("loai")),
           "top": [dict(u, hang=i) for i, u in enumerate(top, 1)], "ung_vien": xh, "y_tuong": yt["y_tuong"],
           "to_lien": to_lien([u for u in xh if not u.get("loai")][:6] or xh[:6], os.path.join(ra, "to-lien.jpg"))}
    _ghi_json(os.path.join(ra, "xep-hang.json"), ket)
    log("  bìa lô: xong — {0} ảnh mới, {1} lượt LLM, top: {2}".format(
        dem["anh"], dem["llm"], ", ".join("{0} {1:.0f}".format(u["ma"], u["tong"]) for u in top) or "(không có)"))
    return ket


def xuat_goi(kq: Dict[str, Any], thu_muc_thumb: str) -> Dict[str, Any]:
    """Top của lô → bộ bìa của lượt trong `7-thumbnail/`: `thumb_00N.jpg` (+ báo cáo đo, nền sạch `znen-thumb_00N.png`
    cho cổng đọc được vẽ lại), `CHON-thumb_001.jpg`, `chon-bia.json` (điểm GIẢM dần theo hạng — hạng nhì thành
    `ho-so-video/anh/<mã>-bia-2.jpg` như cũ, hạng ba là tấm thay thế kế tiếp của cổng chữ), `ke-hoach-bia.json`."""
    from . import chon_bia, do_bia  # noqa: PLC0415
    top = list(kq.get("top") or [])
    if not top:
        raise RuntimeError("bìa lô: không có tấm nào qua mọi lọc")
    uv, muc, truoc = [], [], 101.0
    for i, t in enumerate(top, 1):
        tep = os.path.join(thu_muc_thumb, "thumb_{0:03d}.jpg".format(i))
        chon_bia._xuat_jpg(t["tep"], tep)  # noqa: SLF001
        shutil.copy2(t["nen"], os.path.join(thu_muc_thumb, "znen-thumb_{0:03d}.png".format(i)))
        bc = do_bia.doc_bao_cao(t["tep"])
        if bc:
            do_bia.ghi_bao_cao(tep, {k: v for k, v in bc.items() if k not in ("tep", "van_tay", "luc")})
        truoc = min(float(t["tong"]), truoc - 0.1)
        uv.append({"so": i, "kieu": "bia_lo", "nhom": "khuon", "tong_diem": round(truoc, 1), "diem": t.get("diem"),
                   "loai": "", "ly_do": (t.get("ly_do_2") or t.get("ly_do") or "")[:300], "ma_lo": t["ma"]})
        muc.append({"so": i, "kieu": "bia_lo", "nhom": "khuon", "ve_chu": "ma", "chu_tang": kq.get("chu_tang"),
                    "chu_du_kien": kq.get("chu_ve", "")})
    chon_bia._xuat_jpg(os.path.join(thu_muc_thumb, "thumb_001.jpg"),  # noqa: SLF001
                       os.path.join(thu_muc_thumb, "CHON-thumb_001.jpg"))
    chon = {"so": 1, "kieu": "bia_lo", "tong_diem": uv[0]["tong_diem"], "chon_boi": "ai", "tep": "CHON-thumb_001.jpg",
            "ly_do": "bìa lô (vẽ {0}, chọn {1}): {2}".format(kq["chi_phi"]["anh_tong"], len(top), uv[0]["ly_do"])[:600],
            "nhom": "khuon", "theo_khuon": True, "tham_do": False, "bia_lo": True}
    chon_bia._ghi_json(chon_bia.duong_tep_chon_bia(thu_muc_thumb), {  # noqa: SLF001
        "chon": chon, "ung_vien": uv, "so_luot_cham": 2, "co_khuon_thang": True, "bia_lo": True})
    btk.ghi_ke_hoach(thu_muc_thumb, {"che_do": "bia_lo", "muc": muc, "kieu_khuon": "hop"})
    return chon


# ── Dòng lệnh ────────────────────────────────────────────────────────────────


def _goi_that(goc: str, log: Callable[[str], None]) -> Callable[..., str]:
    """Hàm chữ thật: `goi_van_ban` (Claude Max khi máy bật, tự lùi ví ShopAPI), nhận thêm ảnh data URL."""
    from .goi_van_ban import goi_van_ban, khoi_anh, tin_nhan_viet  # noqa: PLC0415
    from .van_vi import _tao_client  # noqa: PLC0415
    client = _tao_client(goc)

    def goi(loi_nhac: str, mo_hinh: str = "", khoa: str = "", toi_da_token: int = 4000, anh: Any = None) -> str:
        cac = ([anh] if anh else []) if isinstance(anh, str) else [a for a in (anh or []) if a]
        nd: Any = ([{"type": "text", "text": loi_nhac}] + [khoi_anh(a) for a in cac]) if cac else loi_nhac
        return goi_van_ban(client, tin_nhan_viet(nd), mo_hinh=mo_hinh or "claude-sonnet-5",
                           toi_da_token=int(toi_da_token), khoa=khoa, on_log=log, goc=goc)
    return goi


def _ve_that(goc: str, tham_chieu: Sequence[str]) -> Callable[..., List[str]]:
    """Hàm vẽ thật: `client.images.create_and_wait` (n ảnh/job, tham chiếu tải lên MỘT lần), tải kết quả ngay."""
    from .mang_an_toan import tai_bytes  # noqa: PLC0415
    from .van_vi import _tao_client  # noqa: PLC0415
    client = _tao_client(goc)
    if client is None:
        raise SystemExit("không dựng được client ShopAPI (config.json)")
    url: List[str] = []
    khoa_tai = threading.Lock()

    def ve(loi_nhac: str, n: int, khoa: str, cac_dich: List[str]) -> List[str]:
        with khoa_tai:
            if not url:
                url.extend(str(client.uploads.upload_file(p)) for p in tham_chieu)
        job = client.images.create_and_wait(prompt=loi_nhac, n=int(n), aspect_ratio="16:9", reference_images=list(url),
                                            idempotency_key=khoa, timeout=1800)
        outs = job.get("outputs") or ([job.get("output")] if job.get("output") else [])
        ra = []
        for o, d in zip(outs, cac_dich):
            du = tai_bytes(str(o.get("url") if hasattr(o, "get") else o), cho=120)
            with open(d + ".tmp", "wb") as tep:
                tep.write(du)
            os.replace(d + ".tmp", d)
            ra.append(d)
        return ra
    return ve


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.bia_lo", description="Bìa lô: vẽ vài chục rồi chọn.")
    p.add_argument("--kenh", required=True)
    p.add_argument("--luot", required=True, help="mã lượt (vd 0001) hoặc đường thư mục lượt")
    p.add_argument("--so-y", type=int, default=SO_Y_MAC_DINH)
    p.add_argument("--moi-y", type=int, default=MOI_Y_MAC_DINH)
    p.add_argument("--ra", default="", help="thư mục ra (mặc định workspace/bia-lo/<kênh>-<lượt>)")
    p.add_argument("--chu", default="", help='chữ bìa, vd "同じ車に長く|*乗る人の|ほとんどが"')
    p.add_argument("--mau", action="append", default=[], help="bìa thắng thật (tệp/thư mục), lặp được")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    luot = a.luot if os.path.isdir(a.luot) else os.path.join(goc, "PROJECTS", "AUTO", a.kenh, a.luot)
    ma = "{0}-{1}".format(a.kenh, os.path.basename(os.path.normpath(luot)))
    ra = os.path.abspath(a.ra or os.path.join(goc, "workspace", "bia-lo", ma))
    mau = mau_cua_kenh(goc, a.kenh, a.mau)
    nv = os.path.join(goc, "CHANNEL", a.kenh, "nv", "nv1.png")
    kq = chay(goc, a.kenh, thu_muc_luot=luot, ra=ra, chu=a.chu, so_y=a.so_y, moi_y=a.moi_y,
              goi=_goi_that(goc, print), ve=_ve_that(goc, mau + ([nv] if os.path.isfile(nv) else [])), mau=mau)
    for t in kq.get("top") or []:
        print("TOP {0}: {1}  {2}/100  {3}".format(t["hang"], t["tep"], t["tong"], t.get("ly_do_2") or t.get("ly_do")))
    print("tờ liên:", kq.get("to_lien"), "· chi phí:", json.dumps(kq.get("chi_phi"), ensure_ascii=False))
    return 0 if kq.get("top") else 1


if __name__ == "__main__":
    raise SystemExit(main())
