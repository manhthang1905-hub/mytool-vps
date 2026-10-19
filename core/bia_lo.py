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

═══ 14/10/2026 — MỖI KÊNH VẼ THEO KIỂU CHỮ THẮNG CỦA CHÍNH NÓ ═══

Bản đầu chỉ vẽ kiểu HỘP chữ (TL4: hộp đỏ sẫm, M PLUS Rounded Black). Bìa thắng thật của TL2/TL3 lại là chữ TRẦN cực
lớn viền đen dày (trắng + từ khoá đỏ/vàng; TL3 nền tím) — áp kiểu hộp lên chúng là lặp lại lời chê "form thumb khác".
Giờ `ho_so_kieu` đọc khuôn kênh (`khuon_bia.doc_khuon`): tầng có hộp → đường hộp cũ y nguyên; tầng chữ trần → bộ vẽ
chữ trần của khuôn (`bia_theo_khuon.ve_chu_len_anh`: màu/viền/tô từ khoá của khuôn, một dòng cực to, cột chữ hoặc dải
trên–dưới né đầu nhân vật + manh mối). Mẫu tả bìa thắng (few-shot của đạo diễn) là của TỪNG kênh: một lượt AI nhìn 5–7
bìa thật nhiều hiển thị nhất, lưu `CHANNEL/<kênh>/nghien-cuu/mau-bia-thang.json`, làm lại khi khuôn đổi. Ảnh tham chiếu
phong cách + giám khảo dùng bìa thắng thật CỦA kênh đó (bìa khuôn trước), nhân vật theo `style.yaml` + `nv/nv1.png`.

═══ 18/10/2026 — CHÉP ĐÚNG BỐ CỤC CHỮ CỦA BÌA THẮNG, KHÔNG CHỈ MÀU ═══

Chủ soi TL2: "thumb giờ kém thế, thật sự quá tệ". Bìa thắng = khối chữ 4–5 dòng chiếm ~nửa khung, từ khoá ĐỎ cực to;
bìa lô ra 2–3 dòng nhỏ, từ khoá tí hon ở đáy. Giờ: `bo_cuc_thang` đo bìa thắng (AI ước hộp từng dòng, máy đo lại bề
ngang trên điểm ảnh) → MỤC TIÊU cứng (số dòng, diện tích chữ, cao dòng chính, thứ bậc, viền, bên nhân vật) cho
`doc_chu_bia_tran` + bộ vẽ; CỔNG BỐ CỤC `kiem_bo_cuc` loại tấm chữ kém xa bìa thắng / khối chữ hở; giám khảo nhìn tờ CỠ
ĐIỆN THOẠI có hàng bìa thắng (`to_dien_thoai`, mục `bam_nhu_thang`, điểm yếu trừ điểm, nền nhạt đo máy `soi_yeu`).

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
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import bia_theo_khuon as btk

__all__ = ["dao_dien", "doc_y_tuong", "doc_chu_bia", "doc_chu_bia_tran", "loi_nhac_anh", "sinh_hang_loat", "tim_dau",
           "dung_bia", "cham", "to_lien", "chay", "xuat_goi", "main", "kieu_chu", "ho_so_kieu", "mau_thang",
           "bia_thang", "mau_dau_nv"]

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
TRONG_SO = {"bam_nhu_thang": 0.25, "to_mo": 0.22, "noi_dung": 0.18, "ro_120": 0.15, "phong_cach": 0.12,
            "cam_xuc": 0.08}
#: Hộp chữ được chạm tối đa ngần này phần hộp ĐẦU nhân vật / phần CHỦ THỂ (manh mối) của nền sạch.
CHE_DAU_TOI_DA, CHE_MANH_MOI_TOI_DA = 0.02, 0.20
#: Các cách đặt cột chữ thử lần lượt (thu cỡ cả cột, vị trí dọc) — cách đầu là bố cục chuẩn.
CACH_BO_CUC = ((1.0, 0.5), (1.0, 0.3), (1.0, 0.7), (0.86, 0.5), (0.86, 0.25), (0.86, 0.75), (0.76, 0.5))
#: Khuôn hộp chữ khi kênh chưa có khuôn kiểu hộp đo từ bìa thật: hộp đỏ sẫm chữ trắng, cột trái, nhân vật phải.
KHUON_HOP_MAC_DINH: Dict[str, Any] = {"nhan_vat": {"vi_tri": "phai"}, "chu": {"tang": [
    {"vi_tri": v, "mau": ["#FFFFFF"], "khoi_nen": True, "mau_khoi": "#BE392B", "canh": "trai"}
    for v in ("tren", "giua", "duoi")]}}

# ── Kiểu chữ TRẦN (khuôn chữ trần của kênh — TL2/TL3 14/10/2026) ──
#: Dòng không phải dòng cực to: hộp dòng ≤ ngần này % khung (nét chữ ~15%) — dòng cực to giữ trần 30% của bộ vẽ.
TRAN_CO_VUA_PCT = 19.0
#: Dòng cực to tối đa ngần này ký tự: dải ngang cả khung (nhân vật giữa) / cột chữ nửa khung.
TRAN_TO_TOI_DA = {"dai": 10, "cot": 6}
#: Các cách đặt chữ thử lần lượt (cách, thu cỡ cả bìa, trần % khung của dòng dải TRÊN — 0 = giữ). Dải trên–dưới:
#: "dai" = dòng đầu ở dải trên; "duoi" = mọi dòng dồn dải dưới (đầu nhân vật cao — bìa thắng TL3 cũng để chữ đè thân).
#: Cột: bề ngang cột chữ / khung. Thu cỡ cả bìa là cách CUỐI — nó làm mất dòng cực to.
CACH_BO_CUC_TRAN = {"dai": (("dai", 1.0, 0), ("dai", 1.0, 14.0), ("duoi", 1.0, 0), ("dai", 0.88, 0),
                            ("dai", 0.88, 12.0), ("duoi", 0.88, 0)),
                    "cot": ((0.60, 1.0, 0), (0.56, 1.0, 0), (0.52, 1.0, 0), (0.48, 1.0, 0), (0.48, 0.9, 0),
                            (0.44, 0.85, 0))}
#: Chữ trần chỉ là nét chữ (hộp dòng gồm cả khe giữa chữ) → được chạm phần chủ thể nhiều hơn hộp đặc.
CHE_MANH_MOI_TRAN = 0.30
#: Chữ trần được chạm ĐỈNH đầu (ngần này phần trên của hộp đầu — bìa thắng TL3 để dòng trên đè đỉnh đầu), không chạm mặt.
DINH_DAU_TRAN = 0.25
#: Đổi cách vẽ chữ trần → đổi số này để lô cũ vẽ + chấm lại (nền giữ nguyên, không trả tiền ảnh lần hai).
PHIEN_BAN_VE_TRAN = 3
#: Kiểu `do_bia` đúng bìa thắng chữ trần (chữ trắng/đỏ/vàng viền ĐEN dày) — thử trước mọi kiểu đổi màu theo nền.
UU_TIEN_VIEN_DEN = ("trang_vien_den_day", "trang_vien_den", "trang_vien_den_rat_day")
UU_TIEN_VIEN_TRANG = ("toi_vien_trang_day", "toi_tren_sang")
MAU_DO_MAC_DINH, MAU_VANG_MAC_DINH = "#E8202A", "#FFD400"

# ── Mẫu tả bìa thắng THEO KÊNH (cache) ──
TEP_MAU_THANG = "mau-bia-thang.json"
PHIEN_BAN_MAU = 1
SO_BIA_THANG, SO_BIA_THANG_TOI_THIEU = 7, 5
#: Bìa thắng làm ảnh tham chiếu phong cách + mẫu so của giám khảo (kiểu chữ trần): bìa khuôn + 1 bìa cùng kiểu.
SO_MAU_TRAN = 2
#: Bìa thắng giám khảo đặt CẠNH ứng viên trên tờ cỡ điện thoại (18/10/2026).
SO_BIA_SO = 3
#: Bìa cùng kiểu lệch độ sáng trung bình (0..1) với bìa khuôn quá ngần này thì xếp sau.
LECH_SANG_MAU = 0.18

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
thumbnails{bang_chung} all work the same way: {hinh}, and {vi_tri_nv} {nhan_vat_cau} acts out the video's CORE CLAIM \
in one concrete picture that holds a CURIOSITY CLUE — something the viewer recognises instantly that hints at the \
surprising answer without giving it away, so they must click.{hinh_them} How the real winners did it:
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
Hook text {o_hook}: {chu_bia}
Chapters: {muc_luc}
Script (opening):
{kich_ban}

{luat_danh_dau}
Task 2 — "y_tuong": {so_y} DISTINCT concepts — different claim angles and different clue objects, never small \
variations of one idea. Each concept:
  "y": the claim the picture shows (one short English sentence),
  "manh_moi": the curiosity clue — the concrete object or situation that hints at the answer without stating it,
  "doi_lap": the contrast or foil that makes the clue pop (faded silhouettes of other people doing the common or \
opposite thing, a before/after, a doorway onto another scene...),
  "canh": ONE English sentence (at most 45 words) for the image model describing the scene itself (the character, \
the clue, the contrast, the place) — do not describe {vung_trong} or the layout, that is handled separately,
  "mat": the character's big, readable facial expression,
  "tu_the": its pose.
Rules: {luat_nv} Concrete and recognisable at 120 px wide — one main clue object, drawn big, no clutter; \
{luat_canh}; NOTHING \
in the picture may carry writing — no letters, numbers, price tags, signs, labels, receipts, contracts, documents, \
books with titles, screens with content, banknotes or medals: pick objects recognisable by SHAPE (coins, piggy bank, \
glowing brain, keys, cup, car, plain shopping bags...). Never put the hook text or any word into "canh".
Return JSON only: {{"chu": ["...", "..."], "y_tuong": [{{"y": "...", "manh_moi": "...", "doi_lap": "...", "canh": \
"...", "mat": "...", "tu_the": "..."}}]}}"""

#: Đổi lời nhắc đạo diễn → đổi số này (ý tưởng cũ trên đĩa được viết lại). 2 = luật nhân vật kênh (19/10/2026).
PHIEN_BAN_DAO_DIEN = 2

_SUA_DAO_DIEN = ("\n\nYour previous answer gave only {0} usable concepts (each needs non-empty English y, manh_moi, "
                 "canh, mat; no Japanese words in canh). Return the same JSON with {1} good concepts.")

#: Phần lời nhắc đạo diễn / giám khảo theo KIỂU chữ của kênh. Kiểu hộp = đúng nguyên văn bản v2.200.0 (TL4).
LOI_DAO_DIEN_HOP: Dict[str, str] = {
    "bang_chung": " (100k-300k impressions)", "hinh": "big deep-red text boxes on the left carry the hook",
    "vi_tri_nv": "on the right", "nhan_vat_cau": "the channel's plain white round-headed character", "hinh_them": "",
    "o_hook": "on the boxes", "vung_trong": "the empty left side",
    "luat_danh_dau": 'Task 1 — "chu": 2-3 alternative markings of the hook, best first. Each copies the hook text '
                     'EXACTLY and only INSERTS marks: "|" between lines (2-4 lines at natural phrase breaks, never '
                     'starting a line with a particle), "[ ]" around the ONE huge line, and optionally "( )" around a '
                     'soft ending of the huge line such as かも / なのか / だった (drawn small). The huge line is the '
                     'PAYOFF keyword (at most 5 characters), never the opening context words.',
    "luat_canh": "everyday JAPANESE life (apartment, small car, station, convenience store, office, park); bright warm "
                 "daylight, never dark or gloomy; the character and the clue stay on the RIGHT side of the picture, the "
                 "left side stays plain for the text boxes",
    # giám khảo
    "o_chu": "in the red boxes", "chu_ten": "text boxes", "ngoai_chu": "the red boxes",
    "phong_cach_ta": "bright warm clean illustration, the same plain white round-headed character, polished"}
LUAT_DANH_DAU_TRAN = ('Task 1 — "chu": 2-3 alternative markings of the hook, best first. Each copies the hook text '
                      'EXACTLY and only INSERTS marks: "|" between lines ({so_dong} lines at natural phrase breaks, '
                      'never starting a line with a particle), "[ ]" around the ONE biggest line — the PAYOFF (at most '
                      '{to_toi_da} characters), never the opening context words — "< >" around the ONE keyword painted '
                      'RED and optionally "{{ }}" around one more word painted YELLOW, the way the winners colour their '
                      'keywords; everything unmarked is drawn white.')
_CHO_CHU_TRAN = {"trai": "on the left half", "phai": "on the right half",
                 "dai": "in a line across the top and a bigger line across the bottom"}
_NV_TRAN = {"trai": "on the right", "phai": "on the left", "dai": "in the centre"}
_BO_CUC_LUAT_TRAN = {
    "trai": "the character and the clue stay on the RIGHT side of the picture, the left half stays calm for the huge "
            "lettering",
    "phai": "the character and the clue stay on the LEFT side of the picture, the right half stays calm for the huge "
            "lettering",
    "dai": "the character and the clue stay BIG in the CENTRE with the head in the middle of the frame; the top quarter "
           "and the bottom third stay calm for the huge lettering"}
_VUNG_TRONG_TRAN = {"trai": "the empty left half", "phai": "the empty right half",
                    "dai": "the empty top and bottom bands"}

LOI_NHAC_CHAM_1 = """You are the strict art director of a Japanese psychology YouTube channel. The first {k} images \
are this channel's REAL winning thumbnails{bang_chung} — they are the bar.{nv_cau} The next {n} images are \
thumbnail candidates for a NEW video, numbered 1 to {n} in the order shown. The LAST image is a phone-feed sheet: the \
top row repeats the winners (labelled W1, W2…), below them the same candidates at the size a viewer sees them in the \
YouTube home feed, each numbered at its top-left corner.

New video — title: {tieu_de}
Hook text {o_chu}: {chu_bia}
Opening of the script (what the video claims): {mo_dau}

Score EVERY candidate from 1 to 10 on:
- "bam_nhu_thang": side by side with the winners on the phone sheet, would it get clicked AS MUCH as they do? 9-10 only \
if it stands next to them as an equal (as big and bold lettering, as strong a picture); 5 = clearly weaker;
- "noi_dung": the picture shows THIS video's core claim (not a generic scene);
- "to_mo": it holds a curiosity clue that hints at the surprising answer without giving it away, so a viewer must \
click — the trick every winner uses;
- "ro_120": it reads instantly when shrunk to about 120 px on a phone: one big clear subject and clue, no clutter, the \
{chu_ten} do not hide the character's face or the clue;
- "cam_xuc": the character's face shows a strong, readable emotion that fits the story;
- "phong_cach": it looks as good as the winners ({phong_cach_ta}).
"yeu": weaknesses compared with the winners, else []: "pale background" (washed-out, greyish or low-contrast picture), \
"small text" (the lettering is clearly smaller or thinner than the winners'), "weak clue" (a plain scene — the \
character just standing next to an object — with no real curiosity hook).
"loi": hard defects you can SEE, else []: "stray text" (any letters, numbers, symbols or price tags in the picture \
outside {ngoai_chu}), "deformed character", "face covered", "panel split" (a visible seam or dividing line — the \
picture looks like two panels), "photo people".
"nv": is the MAIN character exactly the channel's own character (as in {nv_ref})? "same" | "different" (another \
person, or the figure redesigned: other age, hair, wrinkles, other face or clothes) | "none" (no main character).
"nguoi_khac": the OTHER people in the picture: "none" | "faded" (faded faceless silhouettes or a blurred faceless \
crowd, as in the winners) | "faces" (other people drawn with detailed faces) | "photo".
Be comparative and strict: an average candidate is 5-6.
Return JSON only: {{"ung_vien": [{{"so": 1, "bam_nhu_thang": 0, "noi_dung": 0, "to_mo": 0, "ro_120": 0, "cam_xuc": 0, \
"phong_cach": 0, "nv": "same", "nguoi_khac": "none", "yeu": [], "loi": [], "ly_do": "one short line IN VIETNAMESE: \
what works and what is missing"}}]}} — one item per candidate."""
#: Câu nói ảnh NHÂN VẬT tham chiếu trong lời nhắc chấm vòng 1 (ảnh đứng ngay sau các bìa thắng).
NV_CAU_CHAM = (" Image {so} is the channel's CHARACTER REFERENCE (only the figure): the main character of every "
               "thumbnail must be exactly this figure.")
#: Đổi lời nhắc / ảnh gửi giám khảo → đổi số này (vào khoá lượt chấm: cùng khoá khác nội dung = cổng trả 409).
PHIEN_BAN_CHAM = 2

LOI_NHAC_CHAM_2 = """The image is a phone-feed sheet for a Japanese psychology YouTube channel: the top row shows its \
REAL winning thumbnails (labelled W1, W2…), below them {n} thumbnail candidates for a new video, each numbered at its \
top-left corner, all at the size a viewer sees them in the YouTube home feed.
New video — title: {tieu_de}; hook text: {chu_bia}
Rank ALL {n} candidates, best first: which one would a Japanese viewer scrolling the home feed click AS MUCH as the \
winners — lettering as big and bold, a picture that shows the video's claim with a curiosity clue that hints at the \
answer without giving it away, rich colours (not pale), a strong emotion?
Return JSON only: {{"xep_hang": [best number, ..., worst number], "ly_do": {{"<number>": "one short line IN \
VIETNAMESE"}}}}"""

#: Điểm yếu giám khảo thấy (so bìa thắng) → trừ điểm tổng (0–100); điểm yếu đo bằng MÁY (`soi_yeu`) trừ như nhau.
YEU_TRU = {"pale background": 6.0, "small text": 6.0, "weak clue": 6.0}
#: Nền "nhạt" so bìa thắng của kênh (đo máy, ảnh thu 160×90): độ bão hoà trung bình / độ tương phản (độ lệch chuẩn độ
#: sáng) dưới ngần này × trung vị bìa thắng.
NHAT_BAO_HOA, NHAT_TUONG_PHAN = 0.72, 0.75
#: Tờ cỡ điện thoại của giám khảo: mỗi ô (px) — ~ bề ngang một bìa trong bảng tin YouTube trên điện thoại.
O_DIEN_THOAI = (360, 202)

# ── SÀN CHẤT LƯỢNG trước khi giao (19/10/2026) ──
# Chủ soi TL4-T7-0005 (lên sóng 18/10): qua lô nhưng NHẠT (đơn sắc hồng đào bạc màu — 0/111 tấm lô TL4 đạt màu bìa
# thắng) và nhân vật LỆCH kênh (ông già hói có mặt + đứa trẻ thay nhân vật đầu tròn trắng). Ba sàn cứng, đo trên CHÍNH
# bìa thắng của kênh: màu (bão hoà / tương phản / dải sáng ≥ phân vị `SAN_PHAN_VI` bìa thắng), nhân vật (máy: bộ dò
# đầu bắt được đầu nhân vật kênh khi nó bắt được trên nv1.png + bìa thắng; giám khảo: đúng nhân vật kênh, người phụ chỉ
# là bóng mờ không mặt), điểm "bấm nhiều như bìa thắng" ≥ sàn hiệu chỉnh (`san_bam`). Không tấm nào qua → lô mới
# (dây chuyền, tối đa `SO_LO_SAN_THEM`), vẫn không qua → giữ + báo (thà không đăng).
#: 19/10/2026 (chủ): phân vị 10, đạt khi ≥ 2/3 số đo — phân vị 25 cả 3 số đo loại 70–100% lô TL3/TL5/TL6.
SAN_PHAN_VI = 10.0
#: Sàn điểm `bam_nhu_thang` (1–10) khi chưa hiệu chỉnh; kiểm vàng hiệu chỉnh = điểm giám khảo cho MỘT bìa thắng giấu
#: giữa các ứng viên − `SAN_BAM_DUOI`, kẹp `SAN_BAM_KEP` (`<thư mục bìa thắng>/san-bam.json`).
# Kiểm vàng thật 19/10: bìa thắng giấu bị chấm 2–3 trong lô (giám khảo trừ vì nó không nói đúng video MỚI) — thước
#: lệch thấp, nên sàn không bao giờ dưới 7 ("gần ngang bìa thắng"; 5 = kém hẳn).
SAN_BAM_MAC_DINH, SAN_BAM_DUOI, SAN_BAM_KEP = 7.0, 1.0, (7.0, 8.0)
TEP_SAN_BAM = "san-bam.json"
#: Bộ dò đầu dùng làm sàn nhân vật khi bắt được đầu trên nv1.png và trên ≥ ngần này phần bìa thắng.
TI_LE_DAU_BAT = 0.75
#: Lô bìa mới tối đa khi tấm tốt nhất dưới sàn (luật chủ: "lô mới tới 2 lần, vẫn không thì giữ + báo").
SO_LO_SAN_THEM = 2
_TEN_DO_MAU = {"bao_hoa": "bão hoà", "tuong_phan": "tương phản", "dai_sang": "dải sáng"}
#: Câu khoá nhân vật cho đạo diễn + mô hình ảnh (19/10/2026 — lô TL4-0005: đạo diễn viết "an elderly man", "grandson").
LUAT_NHAN_VAT = ("The channel's character is the ONE main figure of EVERY concept — never recast it as another person "
                 "(an old man, a parent, a child, a couple, a woman…), never change its age or how it looks; other people "
                 "appear only as faded, faceless silhouettes in the background.")

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


# ── 0) Hồ sơ KIỂU bìa thắng của kênh ─────────────────────────────────────────


def kieu_chu(kc: Optional[Dict[str, Any]]) -> str:
    """Kiểu chữ bìa thắng của kênh theo các tầng chữ khuôn đo trên bìa THẬT: "hop" (chữ trong hộp — TL4) | "tran" (chữ
    trần viền dày — TL2/TL3). Khuôn không đo tầng nào → "hop" (khuôn hộp mặc định, như bản đầu)."""
    tang = [t for t in (((kc or {}).get("chu") or {}).get("tang") or []) if isinstance(t, dict)]
    if not tang or btk.kieu_hop(kc) or sum(1 for t in tang if t.get("khoi_nen")) * 2 >= len(tang):
        return "hop"
    return "tran"


def bo_cuc_tran(kc: Optional[Dict[str, Any]]) -> str:
    """Chỗ chữ của khuôn chữ trần: "trai"/"phai" = cột chữ một bên (nhân vật bên kia), "dai" = dải trên + dải dưới
    (nhân vật giữa). Theo vị trí nhân vật đo trên bìa thắng, không có thì theo câu tả vị trí chữ."""
    kc = kc or {}
    vt = str((kc.get("nhan_vat") or {}).get("vi_tri") or "")
    s = str(kc.get("vi_tri_chu") or "").lower()
    tang = {str(t.get("vi_tri") or "") for t in ((kc.get("chu") or {}).get("tang") or []) if isinstance(t, dict)}
    # 16/10/2026 (TL1): chữ hai dải NGANG trên + dưới (khuôn tả "horizontal tiers", "top … bottom") là kiểu dải dù nhân
    # vật lệch một bên — trước đây nhân vật trái → cột chữ phải, sai bố cục bìa thắng.
    if {"tren", "duoi"} <= tang and not re.search(r"\bleft\b|\bright\b", s) and (
            "horizontal" in s or ("top" in s and "bottom" in s)):
        return "dai"
    if vt in ("phai", "trai", "giua"):
        return {"phai": "trai", "trai": "phai", "giua": "dai"}[vt]
    s = str(kc.get("vi_tri_chu") or "").lower()
    return "trai" if "left" in s else "phai" if "right" in s else "dai"


def mau_tran(kc: Optional[Dict[str, Any]]) -> Tuple[str, str, str]:
    """(màu chữ nền, màu ĐỎ từ khoá, màu VÀNG từ khoá) của khuôn chữ trần — đọc từ màu từng đoạn các tầng (AI soi
    từng ký tự lúc dựng khuôn); thiếu màu nào thì màu mặc định của chuẩn ngách."""
    nen, do, vang = "#FFFFFF", "", ""
    tang = [t for t in (((kc or {}).get("chu") or {}).get("tang") or []) if isinstance(t, dict)]
    cac: List[str] = []
    for t in tang:
        cac += [str(p.get("mau") or "") for p in (t.get("phan_mau") or []) if isinstance(p, dict)]
        cac += [str(m) for m in (t.get("mau") or [])]
    for i, m in enumerate(cac):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", m):
            continue
        r, g, b = btk._mau_rgb(m)  # noqa: SLF001
        if min(r, g, b) >= 200:
            nen = m.upper() if i == 0 else nen
        elif not do and r >= 170 and g <= 90 and b <= 90:
            do = m.upper()
        elif not vang and r >= 200 and g >= 170 and b <= 110:
            vang = m.upper()
    return nen, do or MAU_DO_MAC_DINH, vang or MAU_VANG_MAC_DINH


def _uu_tien_vien(kc: Optional[Dict[str, Any]]) -> Tuple[str, ...]:
    """Kiểu `do_bia` của khuôn: chữ sáng viền ĐEN (mặc định, mọi bìa thắng ngách) | chữ tối viền TRẮNG."""
    vien = " ".join(str(t.get("vien") or "") for t in (((kc or {}).get("chu") or {}).get("tang") or [])
                    if isinstance(t, dict)).lower()
    return UU_TIEN_VIEN_TRANG if ("white" in vien and "black" not in vien) else UU_TIEN_VIEN_DEN


def nen_tu_khuon(kc: Optional[Dict[str, Any]]) -> str:
    """Câu tả NỀN của bìa thắng (tiếng Anh, cho mô hình ảnh) từ khuôn: màu chủ đạo, độ sáng, bão hoà, tương phản, hiệu
    ứng. Hiệu ứng dễ thành chữ lạc (UI, mã, số) bỏ đi."""
    kc = kc or {}
    p: List[str] = []
    if kc.get("nen_mau_chu_dao"):
        p.append("{0} background".format(kc["nen_mau_chu_dao"]))
    sang = {"toi": "dark overall", "vua": "medium brightness", "sang": "bright overall"}.get(str(kc.get("nen_do_sang")))
    if sang:
        p.append(sang)
    for k, ten in (("bao_hoa", "saturation"), ("tuong_phan", "contrast")):
        if kc.get(k):
            p.append("{0} {1}".format(btk._MUC_EN.get(str(kc[k]), str(kc[k])), ten))  # noqa: SLF001
    p += [str(x) for x in (kc.get("nen_hieu_ung") or [])
          if x and not re.search(r"\bui\b|text|letter|number|code|digit|screen|hud", str(x), re.I)]
    if kc.get("nen_kieu") == "near_photo":
        p.append("softly lit near-photographic illustrated scene (warm cinematic light, depth, gentle bokeh)")
    return ", ".join(p)


_RE_BO_NV = re.compile(r"background|\bground\b|backdrop|shading|deadpan|(?<!-)\bneutral\b|mouth|relaxed at|standing",
                       re.I)


def _nhan_vat_kenh(goc: str, kenh: str) -> str:
    """Nhân vật kênh theo `style.yaml` (`default_character_lock`, lùi `reference_lock`) — chỉ phần DÁNG/nét vẽ: bỏ các
    vế về nền, bóng, nét mặt/miệng cố định, tư thế đứng (do khuôn và ý tưởng quyết)."""
    try:
        from .kenh import TEP_STYLE, doc_yaml, duong_kenh  # noqa: PLC0415
        st = doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_STYLE)) or {}
    except Exception:  # noqa: BLE001
        st = {}
    tho = str(st.get("default_character_lock") or st.get("reference_lock") or "")
    return ", ".join(x.strip() for x in tho.split(",") if x.strip() and not _RE_BO_NV.search(x))[:400]


def mau_dau_nv(duong: str) -> Optional[Tuple[int, int, int]]:
    """Màu ĐẦU nhân vật kênh đo trên `nv/nv1.png` (nền trơn): None = đầu trắng/nhạt (bộ dò mặc định của `tim_dau`); đầu
    có màu (TL3: cam tô bút lông trong vòng đen) → rgb trung vị phần có màu của 22% trên cùng hình nhân vật."""
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    try:
        im = Image.open(duong).convert("RGB")
    except (OSError, ValueError):
        return None
    im.thumbnail((320, 320))
    a = np.asarray(im).astype(np.int16)
    nen = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
    khac = np.abs(a - nen).max(axis=2) > 40
    ys = np.nonzero(khac.any(axis=1))[0]
    if len(ys) < 5:
        return None
    y0 = int(ys[0])
    y1 = y0 + max(2, int(0.22 * (int(ys[-1]) - y0)))
    xs = np.nonzero(khac[y0:y1].any(axis=0))[0]
    px = a[y0:y1, int(xs[0]):int(xs[-1]) + 1].reshape(-1, 3)
    px = px[px.max(axis=1) > 110]  # bỏ nét đen
    if len(px) < 20:
        return None
    mx, mn = px.max(axis=1), px.min(axis=1)
    mau = px[(mx - mn) >= 0.35 * np.maximum(mx, 1)]
    if len(mau) < 0.3 * len(px):
        return None
    return tuple(int(v) for v in np.median(mau, axis=0))


def _do_sang_tb(duong: str) -> Optional[float]:
    """Độ sáng trung bình (0..1) của ảnh — None khi không mở được."""
    from PIL import Image, ImageStat  # noqa: PLC0415
    try:
        with Image.open(duong) as im:
            return float(ImageStat.Stat(im.convert("L").resize((64, 36))).mean[0]) / 255.0
    except (OSError, ValueError):
        return None


#: Danh sách bìa thắng trong thư mục mẫu (`kenh.yaml: bia_lo_mau`) — `{"bia": [{tep, video_id, imp, ctr}]}`, xếp hạng.
TEP_DS_THANG = "thang.json"


def ten_thu_muc_thang(kenh: str) -> str:
    """Thư mục bìa thắng theo NẾP khi `kenh.yaml` chưa khai `bia_lo_mau` (19/10/2026): `workspace/bia-<mã>/thang`,
    mã = tên kênh chữ thường bỏ đuôi "-T<n>" (TL4-T7 → bia-tl4, TL4-T7-K2 → bia-tl4-k2)."""
    return os.path.join("workspace", "bia-" + re.sub(r"-t\d+(?=-|$)", "", str(kenh or "").lower()), "thang")


def thu_muc_mau(goc: str, kenh: str, mau: Sequence[str] = ()) -> str:
    """Thư mục bìa thắng THẬT do chủ chọn (16/10/2026): thư mục trong `mau` (CLI `--mau DIR`) > `kenh.yaml: bia_lo_mau`
    (đường tương đối theo gốc tool) > thư mục theo nếp `ten_thu_muc_thang` (19/10/2026 — có ảnh mới tính). '' khi
    không có."""
    for m in mau or ():
        if m and os.path.isdir(m):
            return os.path.abspath(m)
        # tệp mẫu lấy từ một thư mục bìa thắng (có `thang.json`) — vd `chay()` nhận danh sách tệp của `mau_cua_kenh`
        if m and os.path.isfile(m) and os.path.isfile(os.path.join(os.path.dirname(m), TEP_DS_THANG)):
            return os.path.abspath(os.path.dirname(m))
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        d = str((doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}).get("bia_lo_mau") or "").strip()
    except Exception:  # noqa: BLE001
        d = ""
    d = os.path.join(goc, d) if d and not os.path.isabs(d) else d
    if d and os.path.isdir(d):
        return os.path.abspath(d)
    nep = os.path.join(goc, ten_thu_muc_thang(kenh))
    return os.path.abspath(nep) if goc and os.path.isdir(nep) and bia_thu_muc(nep) else ""


def bia_thu_muc(thu_muc: str, toi_da: int = SO_BIA_THANG) -> List[Dict[str, Any]]:
    """Bìa của thư mục mẫu theo THỨ HẠNG: `thang.json` (video_id, imp, ctr) nếu có, không thì tên tệp."""
    ds: List[Dict[str, Any]] = []
    du = _doc_json(os.path.join(thu_muc, TEP_DS_THANG))
    for b in (du.get("bia") if isinstance(du, dict) else None) or []:
        tep = os.path.join(thu_muc, str((b or {}).get("tep") or "")) if isinstance(b, dict) else ""
        if tep and os.path.isfile(tep):
            ds.append({"video_id": str(b.get("video_id") or os.path.basename(tep)), "ctr": b.get("ctr"),
                       "imp": b.get("imp"), "tep": tep})
    if not ds:
        try:
            ten = sorted(t for t in os.listdir(thu_muc) if t.lower().endswith((".jpg", ".jpeg", ".png")))
        except OSError:
            ten = []
        ds = [{"video_id": t, "ctr": None, "imp": None, "tep": os.path.join(thu_muc, t)} for t in ten]
    return ds[:toi_da]


def duong_mau_thang(goc: str, kenh: str) -> str:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_MAU_THANG)


def bia_thang(goc: str, kenh: str, khuon: Optional[Dict[str, Any]] = None, *, toi_da: int = SO_BIA_THANG,
              tai_anh: Optional[Callable[[str], Optional[bytes]]] = None) -> List[Dict[str, Any]]:
    """5–7 bìa THẬT nhiều hiển thị nhất của kênh (bìa khuôn đứng đầu): video thật đo trong `chi-so/` (bản chụp muộn
    nhất, ≥ 36h tuổi, ≥ 1.000 hiển thị), CTR ≥ trung vị kênh trước, thiếu thì bù video hiển thị lớn kế tiếp. Ảnh bìa
    trên YouTube tải MỘT lần (`khuon_bia.anh_that`) rồi dùng bản đã lưu."""
    from . import khuon_bia  # noqa: PLC0415
    kh = khuon if khuon is not None else (khuon_bia.doc_khuon(goc, kenh) or {})
    try:
        ds = khuon_bia._ung_vien_that(goc, kenh)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        ds = []
    tv = khuon_bia.trung_vi_ctr_that(ds)
    du = sorted((u for u in ds if u.impressions >= khuon_bia.NGUONG_IMPRESSIONS), key=lambda u: -u.impressions)
    tren = [u for u in du if tv is None or u.ctr >= tv]
    chon = tren + [u for u in du if u not in tren][:max(0, SO_BIA_THANG_TOI_THIEU - len(tren))]
    ra: List[Dict[str, Any]] = []
    if kh.get("video_id") and kh.get("tep") and os.path.isfile(str(kh["tep"])):
        ra.append({"video_id": str(kh["video_id"]), "ctr": kh.get("ctr"), "imp": kh.get("imp"), "tep": str(kh["tep"]),
                   "khuon": True})
    for u in chon:
        if len(ra) >= toi_da or any(b["video_id"] == u.video_id for b in ra):
            continue
        tep = khuon_bia.duong_anh_that(goc, kenh, u.video_id)
        if not os.path.isfile(tep):
            tep = khuon_bia.anh_that(goc, kenh, u.video_id, tai_anh=tai_anh)
        if tep:
            ra.append({"video_id": u.video_id, "ctr": round(u.ctr, 2), "imp": int(u.impressions), "tep": tep})
    return ra[:toi_da]


LOI_NHAC_MAU_THANG = """These {n} images are the REAL best-performing YouTube thumbnails of ONE Japanese psychology \
channel, numbered 1 to {n} in the order shown (image 1 is its proven winning template). They are the bar every new \
thumbnail of this channel must reach. Describe them so a concept director can invent NEW concepts in the same spirit \
and an image model can match their look.

Return JSON only:
{{"bia": [{{"so": 1, "kieu_chu": "bare", "chu": "the cover text exactly as written, with | at each line break", \
"ta": "ONE English sentence: what the picture shows, the curiosity clue in it, and what it hints at without saying \
it"}}],
 "hinh": "2-3 English sentences: what these winners share — text style (colours, outline, boxes or bare letters), \
where the text sits, how big the character is and where, the background look and light, the mood",
 "nen": "ONE English sentence (at most 40 words) describing the background look of image 1 and the winners like it, \
as an instruction for an image model (colours, light, effects, how busy) — no text, no layout"}}
One "bia" item per image. "kieu_chu": "box" when the lines sit on solid coloured boxes or bands, "bare" when the \
letters stand on the picture with only an outline. Example of the "ta" level wanted: "a heap of glittering gadgets on \
the floor while the figure calmly walks away toward a bright door — you see WHAT is skipped, never WHY"."""


def _khoa_mau(khuon: Dict[str, Any]) -> str:
    """Khoá làm mới mẫu tả: khuôn đổi video hoặc bìa thật đổi (sha1) → tả lại."""
    return _bam(khuon.get("video_id") or "", khuon.get("sha1_that") or khuon.get("sha1") or "", PHIEN_BAN_MAU)


def _k(v: Any) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "?"
    return "{0:.0f}k".format(v / 1000.0) if v >= 1000 else "{0:.0f}".format(v)


def doc_mau_thang(du: Any, bia: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """JSON lượt nhìn bìa → `{bia: [{video_id, ctr, imp, tep, kieu_chu "hop"|"tran", chu, ta}], mau (few-shot), hinh,
    nen}`. Mục thiếu tả vẫn giữ trong `bia` (ảnh mẫu) nhưng không vào few-shot."""
    ds = (du.get("bia") if isinstance(du, dict) else None) or []
    theo_so: Dict[int, Dict[str, Any]] = {}
    for x in ds if isinstance(ds, list) else []:
        try:
            so = int(x.get("so"))
        except (AttributeError, TypeError, ValueError):
            continue
        if 1 <= so <= len(bia) and so not in theo_so:
            theo_so[so] = x
    ra: List[Dict[str, Any]] = []
    for i, b in enumerate(bia, 1):
        x = theo_so.get(i) or {}
        kieu = str(x.get("kieu_chu") or "").lower()
        ra.append(dict(b, kieu_chu="hop" if "box" in kieu or "hop" in kieu else "tran" if kieu else "",
                       chu=" ".join(str(x.get("chu") or "").split())[:80],
                       ta=" ".join(str(x.get("ta") or "").split())[:400]))
    mau = "\n".join("- 「{0}」: {1}".format(b["chu"], b["ta"]) for b in ra if b["chu"] and b["ta"])
    return {"bia": ra if mau else [], "mau": mau, "hinh": " ".join(str((du or {}).get("hinh") or "").split())[:900]
            if isinstance(du, dict) else "", "nen": " ".join(str((du or {}).get("nen") or "").split())[:400]
            if isinstance(du, dict) else ""}


def mau_thang(goc: str, kenh: str, khuon: Optional[Dict[str, Any]] = None, *, goi: Optional[Callable[..., str]] = None,
              log: Callable[[str], None] = print, dem: Optional[Dict[str, int]] = None,
              tai_anh: Optional[Callable[[str], Optional[bytes]]] = None, thu_muc: str = "") -> Dict[str, Any]:
    """Mẫu tả bìa thắng CỦA kênh (cache `nghien-cuu/mau-bia-thang.json`). Khớp khuôn hiện tại → trả luôn (`moi`
    True). Khác khuôn / chưa có + có `goi` → MỘT lượt AI nhìn 5–7 bìa thật (`bia_thang`) rồi ghi; không `goi` hoặc
    lượt hỏng → bản cũ (`moi` False) hoặc {}.

    16/10/2026 — `thu_muc` (thư mục bìa thắng chủ chọn, `thu_muc_mau`): tả ĐÚNG các bìa ấy theo thứ hạng; cache nằm
    trong chính thư mục (`<thư mục>/mau-bia-thang.json`), làm lại khi tệp trong thư mục đổi."""
    from . import khuon_bia  # noqa: PLC0415
    kh = khuon if khuon is not None else (khuon_bia.doc_khuon(goc, kenh) or {})
    bia_tm = bia_thu_muc(thu_muc) if thu_muc else []
    duong = os.path.join(thu_muc, TEP_MAU_THANG) if bia_tm else duong_mau_thang(goc, kenh)
    cu = _doc_json(duong)
    cu = cu if isinstance(cu, dict) and cu.get("bia") else {}
    khoa = _bam(*["{0}:{1}".format(os.path.basename(b["tep"]), os.path.getsize(b["tep"])) for b in bia_tm],
                PHIEN_BAN_MAU, "thu-muc") if bia_tm else _khoa_mau(kh)
    if cu and cu.get("khoa") == khoa:
        return dict(cu, moi=True)
    if goi is None or not (bia_tm or kh.get("video_id")):
        return dict(cu, moi=False) if cu else {}
    bia = bia_tm or bia_thang(goc, kenh, kh, tai_anh=tai_anh)
    if not bia:
        return dict(cu, moi=False) if cu else {}
    log("  bìa lô: tả {0} bìa thắng thật của {1} (mẫu few-shot riêng kênh)…".format(len(bia), kenh))
    try:
        if dem is not None:
            dem["llm"] = dem.get("llm", 0) + 1
        du = _json(goi(LOI_NHAC_MAU_THANG.format(n=len(bia)), khoa="bia-lo-mau:{0}:{1}".format(kenh, khoa),
                       toi_da_token=4000, mo_hinh=MO_HINH_CHAM, anh=[_url_anh(b["tep"]) for b in bia]))
    except Exception as loi:  # noqa: BLE001 — tả hỏng: bản cũ / mẫu mặc định, không chặn lô
        log("  (bìa lô: tả bìa thắng hỏng: {0})".format(str(loi)[:160]))
        return dict(cu, moi=False) if cu else {}
    moi = doc_mau_thang(du, bia)
    if not moi["bia"]:
        return dict(cu, moi=False) if cu else {}
    moi.update(khoa=khoa, khuon_video=str(kh.get("video_id") or ""), phien_ban=PHIEN_BAN_MAU,
               luc=time.strftime("%Y-%m-%d %H:%M:%S"))
    _ghi_json(duong, moi)
    return dict(moi, moi=True)


# ── 0b) BỐ CỤC CHỮ của bìa thắng (18/10/2026) ───────────────────────────────
#
# Chủ soi TL2 18/10: "thumb giờ kém thế, thật sự quá tệ". Bìa thắng TL2 (177k hiển thị, CTR 7,39%) là MỘT KHỐI chữ trần
# 4–5 dòng xếp chồng chiếm gần nửa khung, từ khoá ĐỎ cực to, nhân vật bên phải; bìa lô ra 2–3 dòng nhỏ, từ khoá tí hon
# ở đáy, giữa khối hở trống. Bìa lô mới chép đúng MÀU, chưa chép BỐ CỤC CHỮ. Giờ: một lượt AI ĐO từng bìa thắng (dòng,
# hộp từng dòng theo phần khung, màu, nhân vật) → số đo máy tổng hợp có trọng số lượt bấm (`tong_hop_bo_cuc`) thành
# MỤC TIÊU cứng cho bộ vẽ (số dòng, diện tích các dòng, cao dòng chính, thứ bậc dòng chính/dòng vừa, bề cột, bên nhân
# vật) + cổng bố cục tất định (`kiem_bo_cuc`) loại tấm chữ kém xa bìa thắng. `<thư mục mẫu>/bo-cuc.json` (đặt tay)
# thắng mọi số đo.

TEP_BO_CUC_THANG = "bo-cuc-thang.json"
TEP_BO_CUC_TAY = "bo-cuc.json"
#: 6 (19/10/2026): + dải/khối nền sau dòng chữ (`dai`), mật độ nét chữ dòng chính (`mat_do_chu`). 7: đo lại khi hỏng.
PHIEN_BAN_BO_CUC = 7
LAN_DO_BO_CUC = 3
SO_BIA_DO = 4
#: Tấm bị loại khi diện tích các dòng chữ < ngần này × mục tiêu, hoặc dòng chính thấp hơn ngần này × mục tiêu.
HE_SO_DT_TOI_THIEU, HE_SO_CAO_TOI_THIEU = 0.7, 0.7
#: Cột chữ: khe dọc lớn nhất giữa hai dòng liền nhau (phần chiều cao khung) — bìa thắng xếp dòng thành MỘT khối.
KHE_DONG_TOI_DA = 0.12
#: Bề dày viền chữ (phần cỡ chữ) theo số đo bìa thắng.
VIEN_THEO_DO = {"thin": 0.05, "thick": 0.085, "very_thick": 0.11}
_MAU_DO = ("white", "red", "yellow", "black", "other")

LOI_NHAC_DO_BO_CUC = """This is a REAL winning YouTube thumbnail (1280x720) of a Japanese channel. MEASURE its text \
layout precisely. All coordinates are fractions of the frame: x from 0 (left edge) to 1 (right edge), y from 0 (top) \
to 1 (bottom).
"dong": one item per VISUAL text line, top to bottom — "chu" (the line exactly as written), "x0","x1","y0","y1" (the \
box around that line's letters INCLUDING their outline), "mau" (the colour of most of its letters: white | red | \
yellow | black | other), "tu_khoa" (true for the line(s) carrying the main keyword — the biggest or red/yellow one), \
"nen" (a solid or brush-stroke BAND / box painted behind that line's letters: none | red | black | yellow | white | \
other).
"nhan_vat": the main character's box (head and body that are visible) "x0","x1","y0","y1", and "mat": its head box \
[x0, y0, x1, y1].
"vien": the letters' outline: none | thin | thick | very_thick.
Return JSON only: {{"dong": [{{"chu": "", "x0": 0, "x1": 0, "y0": 0, "y1": 0, "mau": "white", "tu_khoa": false, "nen": "none"}}], \
"nhan_vat": {{"x0": 0, "x1": 0, "y0": 0, "y1": 0, "mat": [0, 0, 0, 0]}}, "vien": "thick"}}"""


def _so01(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f > 1.5:  # AI trả px của khung 1280×720 / phần trăm — không đoán: bỏ
        return None
    return max(0.0, min(1.0, f))


def do_hop_dong(hop: Sequence[Sequence[float]], *, W: float = 1.0, H: float = 1.0, nv: Optional[Sequence[float]] = None,
                cao: Sequence[float] = ()) -> Dict[str, Any]:
    """Số đo bố cục từ các hộp dòng chữ (x0, y0, x1, y1 — px trên khung W×H, hoặc phần khung khi W=H=1): `so_dong`,
    `dt_dong_pct` (tổng diện tích hộp dòng / khung), `cao_chinh_pct` (hộp dòng cao nhất), `ti_le_chinh` (dòng chính /
    trung vị dòng khác), `khe_max` (khe dọc lớn nhất giữa hai dòng liền nhau, phần khung), `khoi` (hộp bao), `ben_nv`
    (theo tâm hộp nhân vật `nv`). `cao`: chiều cao từng dòng thay cho chiều cao hộp (tuỳ)."""
    ds = sorted([[float(v) for v in h[:4]] for h in hop if h and h[2] > h[0] and h[3] > h[1]], key=lambda h: h[1])
    if not ds:
        return {"so_dong": 0}
    cc = [(h[3] - h[1]) / H for h in ds] if not cao else [float(c) for c in cao]
    i_chinh = max(range(len(ds)), key=lambda i: cc[i])
    khac = sorted(c for i, c in enumerate(cc) if i != i_chinh)
    tv = khac[len(khac) // 2] if khac else cc[i_chinh]
    khe = [max(0.0, (b[1] - a[3]) / H) for a, b in zip(ds, ds[1:])]
    # diện tích HỢP các hộp (hộp AI/đo của hai dòng kề có thể chồng nhau — không đếm hai lần), lưới 160×90
    luoi = [[False] * 160 for _ in range(90)]
    for h in ds:
        for yy in range(max(0, int(h[1] / H * 90)), min(90, int(round(h[3] / H * 90)))):
            hang = luoi[yy]
            for xx in range(max(0, int(h[0] / W * 160)), min(160, int(round(h[2] / W * 160)))):
                hang[xx] = True
    ra = {"so_dong": len(ds), "dt_dong_pct": round(100.0 * sum(sum(x) for x in luoi) / (160 * 90), 1),
          "cao_chinh_pct": round(100.0 * cc[i_chinh], 1), "ti_le_chinh": round(cc[i_chinh] / max(1e-6, tv), 2),
          "i_chinh": i_chinh, "khe_max": round(max(khe or [0.0]), 3),
          "khoi": [round(v, 3) for v in (min(h[0] for h in ds) / W, min(h[1] for h in ds) / H,
                                         max(h[2] for h in ds) / W, max(h[3] for h in ds) / H)]}
    if nv:
        cx = (float(nv[0]) + float(nv[2])) / 2.0 / W
        ra["ben_nv"] = "trai" if cx < 0.42 else "phai" if cx > 0.58 else "giua"
    return ra


def _doan_dai_nhat(m, gap: int) -> Optional[Tuple[int, int]]:
    """(đầu, cuối+1) của đoạn True NHIỀU điểm nhất trong mảng bool `m` (gộp khe ≤ `gap`)."""
    idx = [i for i, v in enumerate(m) if v]
    if not idx:
        return None
    doan, a, b = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - b <= gap + 1:
            b = i
        else:
            doan.append((a, b))
            a = b = i
    doan.append((a, b))
    a, b = max(doan, key=lambda x: sum(1 for i in range(x[0], x[1] + 1) if m[i]))
    return a, b + 1


def tinh_hop_dong(anh, hop: Sequence[Sequence[float]], tranh: Sequence[Sequence[float]] = ()) -> List[List[float]]:
    """Hộp dòng AI ước (phần khung) → hộp ĐO trên điểm ảnh: trong hộp nới rộng, điểm ảnh MÀU CHỮ (trắng tinh / đỏ /
    vàng) sát nét VIỀN TỐI (chữ trần viền dày của ngách) → dải cột/hàng có chữ. AI nhìn ảnh hay ước bề ngang dòng rộng
    hơn thật ~30% (đo 18/10 trên bìa thắng TL2: 「悠々自適に」 AI 0,01–0,82, thật ~0,01–0,62). Không đo được (ít điểm,
    hộp đo < 15% hộp AI) → giữ hộp AI. `tranh`: hộp (phần khung) bỏ khỏi phép đo — đầu nhân vật trắng viền đen của
    TL2 trông như chữ trắng viền đen."""
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    from .do_bia import _gian  # noqa: PLC0415
    W, H = 640, 360
    a = np.asarray(anh.convert("RGB").resize((W, H), Image.BOX)).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mau = (a.min(axis=2) >= 225) | ((r >= 170) & (g <= 90) & (b <= 90)) | ((r >= 200) & (g >= 170) & (b <= 100))
    vien = _gian(a.max(axis=2) <= 80, 3)
    chu = mau & vien
    for t in tranh or ():
        try:
            chu[max(0, int((t[1] - 0.03) * H)):int((t[3] + 0.03) * H), max(0, int((t[0] - 0.03) * W)):int((t[2] + 0.03) * W)] = False
        except (TypeError, ValueError, IndexError):
            continue
    ra: List[List[float]] = []
    for h in hop:
        x0, y0, x1, y1 = [float(v) for v in h[:4]]
        hh = y1 - y0
        X0, X1 = int(max(0.0, x0 - 0.04) * W), int(min(1.0, x1 + 0.04) * W)
        Y0, Y1 = int(max(0.0, y0) * H), int(min(1.0, y1) * H)  # dọc: AI ước đúng hơn; nới dọc là ăn sang dòng kề
        o = chu[Y0:Y1, X0:X1]
        if o.size == 0 or o.sum() < 40:
            ra.append([x0, y0, x1, y1])
            continue
        cot = _doan_dai_nhat(o.sum(axis=0) >= max(1, int(0.02 * o.shape[0])), int(0.09 * W))
        hang = _doan_dai_nhat(o.sum(axis=1) >= max(1, int(0.01 * o.shape[1])), int(0.02 * H))
        if not cot or not hang:
            ra.append([x0, y0, x1, y1])
            continue
        m = [(X0 + cot[0] - 2) / W, (Y0 + hang[0] - 2) / H, (X0 + cot[1] + 2) / W, (Y0 + hang[1] + 2) / H]
        m = [max(0.0, min(1.0, v)) for v in m]
        if (m[2] - m[0]) * (m[3] - m[1]) < 0.15 * (x1 - x0) * hh:
            ra.append([x0, y0, x1, y1])
            continue
        ra.append([round(v, 3) for v in m])
    return ra


def mau_do_mau(anh, dong: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    """Màu ĐỎ / VÀNG thật của chữ bìa thắng: trung vị các điểm ảnh đỏ tươi / vàng tươi trong hộp các dòng màu ấy →
    {"mau_do": "#RRGGBB", "mau_vang": …} (thiếu điểm → bỏ mục). 18/10/2026: khuôn TL2 ghi đỏ #D00000 — đỏ sẫm chìm vào
    viền đen; bìa thắng thật là đỏ tươi ~#FB0301."""
    import numpy as np  # noqa: PLC0415
    a = np.asarray(anh.convert("RGB").resize((640, 360))).astype(np.int16)
    ra: Dict[str, str] = {}
    for ten, mau, loc in (("mau_do", "red", lambda r, g, b: (r >= 180) & (g <= 80) & (b <= 80)),
                          ("mau_vang", "yellow", lambda r, g, b: (r >= 200) & (g >= 170) & (b <= 100))):
        px = []
        for d in dong:
            if d.get("mau") != mau:
                continue
            x0, y0, x1, y1 = [int(v * s) for v, s in zip(d["hop"], (640, 360, 640, 360))]
            o = a[y0:y1, x0:x1].reshape(-1, 3)
            if o.size:
                px.append(o[loc(o[:, 0], o[:, 1], o[:, 2])])
        px = np.concatenate(px) if px else np.zeros((0, 3))
        if len(px) >= 50:
            r, g, b = (int(v) for v in np.median(px, axis=0))
            ra[ten] = "#{0:02X}{1:02X}{2:02X}".format(r, g, b)
    return ra


def _mat_na_chu(a):
    """Điểm ảnh MÀU CHỮ của ngách (trắng tinh / đỏ tươi / vàng tươi) trên mảng rgb int16."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (a.min(axis=2) >= 225) | ((r >= 170) & (g <= 90) & (b <= 90)) | ((r >= 200) & (g >= 170) & (b <= 100))


def mau_dai_do(anh, hop: Sequence[float], ten: str = "red") -> str:
    """Màu DẢI/KHỐI NỀN sau một dòng chữ (19/10/2026 — bìa thắng TL2: dải cọ đỏ SẪM ~#C21214 sau 「悠々自適に」 chữ đỏ
    TƯƠI): AI đo bố cục nói dòng có dải và màu gì (`ten`: red | black | yellow | white | other); điểm ảnh XÁC NHẬN —
    trong hộp dòng, điểm cùng loại màu ấy mà KHÔNG phải màu chữ chiếm ≥ 15% (đen: 45%) → trung vị của chúng. '' = không xác
    nhận được (không vẽ dải theo lời AI suông)."""
    import numpy as np  # noqa: PLC0415
    W, H = 640, 360
    a = np.asarray(anh.convert("RGB").resize((W, H))).astype(np.int16)
    x0, y0, x1, y1 = int(hop[0] * W), int(hop[1] * H), int(hop[2] * W), int(hop[3] * H)
    o = a[y0:y1, x0:x1].reshape(-1, 3)
    if len(o) < 60:
        return ""
    r, g, b = o[:, 0], o[:, 1], o[:, 2]
    mx, mn = o.max(axis=1), o.min(axis=1)
    chu = (mn >= 225) | ((r >= 230) & (g <= 60) & (b <= 60)) | ((r >= 200) & (g >= 170) & (b <= 100) & (mx - mn > 120))
    loai = {"red": (r >= 110) & (r < 235) & (r - g >= 70) & (r - b >= 70),
            "black": mx <= 70,
            "yellow": (r >= 170) & (g >= 140) & (b <= 90) & (mx - mn > 90),
            "white": mn >= 200}.get(str(ten or "").lower())
    if loai is None:
        return ""
    m = loai & ~chu
    if float(m.mean()) < (0.45 if str(ten).lower() == "black" else 0.15):  # viền đen dày đã chiếm ~1/4 hộp
        return ""
    return "#{0:02X}{1:02X}{2:02X}".format(*(int(v) for v in np.median(o[m], axis=0)))


def mat_do_chu(anh, hop: Sequence[float]) -> Optional[float]:
    """Phần hộp dòng (đo sát nét) là điểm MÀU CHỮ — nét chữ đậm/mảnh (bìa thắng dùng gothic rất đậm)."""
    import numpy as np  # noqa: PLC0415
    W, H = 640, 360
    a = np.asarray(anh.convert("RGB").resize((W, H))).astype(np.int16)
    o = a[int(hop[1] * H):int(hop[3] * H), int(hop[0] * W):int(hop[2] * W)]
    return round(float(_mat_na_chu(o).mean()), 3) if o.size >= 60 else None


def doc_do_bo_cuc(du: Any, anh: Any = None) -> Optional[Dict[str, Any]]:
    """JSON lượt đo MỘT bìa thắng → số đo (`do_hop_dong` + `mau_chinh`, `vien`, `ky_tu_dong`, `dong`). Hộp hỏng (ngoài
    0..1, ngược, dòng < 2% hay > 60% khung) bỏ; không còn dòng nào → None. `anh` (PIL) có thì hộp AI được đo lại trên
    điểm ảnh (`tinh_hop_dong`)."""
    if not isinstance(du, dict):
        return None
    dong = []
    for x in du.get("dong") or []:
        if not isinstance(x, dict):
            continue
        h = [_so01(x.get(k)) for k in ("x0", "y0", "x1", "y1")]
        if None in h or h[2] <= h[0] or not 0.02 <= h[3] - h[1] <= 0.6:
            continue
        mau = str(x.get("mau") or "").strip().lower()
        nen = str(x.get("nen") or "").strip().lower()
        dong.append({"chu": " ".join(str(x.get("chu") or "").split())[:40], "hop": h,
                     "mau": mau if mau in _MAU_DO else "other", "tu_khoa": x.get("tu_khoa") is True,
                     "nen_ai": "" if nen in ("", "none", "no", "false") else nen[:12]})
    if not dong:
        return None
    # Một dòng NHIỀU MÀU (「低IQの人」+「の思考の癖」 cùng hàng) AI hay tách thành hai mục → gộp các mục chồng nhau theo
    # chiều dọc ≥ 60% thành MỘT dòng (hộp hợp, chữ nối, màu của phần rộng hơn).
    dong.sort(key=lambda d: (d["hop"][1], d["hop"][0]))
    gop: List[Dict[str, Any]] = []
    for d in dong:
        if gop:
            p, h = gop[-1]["hop"], d["hop"]
            chung = min(p[3], h[3]) - max(p[1], h[1])
            if chung >= 0.6 * min(p[3] - p[1], h[3] - h[1]):
                rong_p, rong_h = p[2] - p[0], h[2] - h[0]
                trai, phai = (gop[-1], d) if p[0] <= h[0] else (d, gop[-1])
                gop[-1] = {"chu": trai["chu"] + phai["chu"], "hop": [min(p[0], h[0]), min(p[1], h[1]),
                                                                     max(p[2], h[2]), max(p[3], h[3])],
                           "mau": gop[-1]["mau"] if rong_p >= rong_h else d["mau"],
                           "tu_khoa": gop[-1]["tu_khoa"] or d["tu_khoa"],
                           "nen_ai": gop[-1].get("nen_ai") or d.get("nen_ai") or ""}
                continue
        gop.append(d)
    dong = gop
    nv = du.get("nhan_vat") if isinstance(du.get("nhan_vat"), dict) else {}
    mat = [_so01(v) for v in (nv.get("mat") or [])[:4]] if isinstance(nv.get("mat"), list) else []
    if anh is not None:
        try:
            # hộp đầu AI ước thường hụt phía dưới (đo 18/10: đầu TL2 0,08–0,28, AI 0,06–0,16) → nới xuống 1,5× cao
            tr = [[mat[0], mat[1], mat[2], mat[3] + 1.5 * (mat[3] - mat[1])]] if (
                len(mat) == 4 and None not in mat and mat[2] > mat[0] and mat[3] > mat[1]) else []
            for d, h in zip(dong, tinh_hop_dong(anh, [d["hop"] for d in dong], tr)):
                d["hop_ai"], d["hop"] = d["hop"], h
        except Exception:  # noqa: BLE001 — đo điểm ảnh hỏng: giữ hộp AI
            pass
    hnv = [_so01(nv.get(k)) for k in ("x0", "y0", "x1", "y1")]
    ra = do_hop_dong([d["hop"] for d in dong], nv=hnv if None not in hnv and hnv[2] > hnv[0] else None)
    ra["mau_chinh"] = dong[ra["i_chinh"]]["mau"]
    ra["tu_khoa_do"] = any(d["mau"] == "red" and (d["tu_khoa"] or i == ra["i_chinh"]) for i, d in enumerate(dong))
    v = str(du.get("vien") or "").strip().lower()
    ra["vien"] = v if v in VIEN_THEO_DO or v == "none" else "thick"
    if anh is not None:
        ra.update(mau_do_mau(anh, dong))
        # 19/10/2026 — DẢI nền sau dòng từ khoá (AI thấy + điểm ảnh xác nhận) và độ đậm nét dòng chính
        try:
            for d in dong:
                d["dai"] = mau_dai_do(anh, d.get("hop_ai") or d["hop"], d["nen_ai"]) if d.get("nen_ai") else ""
            k = [i for i, d in enumerate(dong) if d["dai"] and (i == ra["i_chinh"] or d["tu_khoa"] or d["mau"] == "red")]
            ra["dai_tu_khoa"] = dong[k[0]]["dai"] if k else ""
            ra["dai_ca"] = sum(1 for d in dong if d["dai"])
            ra["mat_do_chu"] = mat_do_chu(anh, dong[ra["i_chinh"]]["hop"])
        except Exception:  # noqa: BLE001 — đo điểm ảnh hỏng: không có dải/độ đậm
            pass
    dai = sorted(len(re.sub(r"\s+", "", d["chu"])) for d in dong if d["chu"])
    ra["ky_tu_dong"] = dai[len(dai) // 2] if dai else 0
    ra["dong"] = dong
    return ra


def _trung_vi_trong_so(cap: Sequence[Tuple[float, float]]) -> Optional[float]:
    cap = sorted((float(v), max(0.0, float(w))) for v, w in cap if v is not None)
    tong = sum(w for _v, w in cap)
    if not cap or tong <= 0:
        return None
    dem = 0.0
    for v, w in cap:
        dem += w
        if dem >= tong / 2.0:
            return v
    return cap[-1][0]


def tong_hop_bo_cuc(ds: Sequence[Tuple[Dict[str, Any], float]]) -> Dict[str, Any]:
    """Số đo các bìa thắng (kèm trọng số = lượt bấm) → MỤC TIÊU bố cục chữ: trung vị có trọng số của từng số đo; bên
    nhân vật / màu dòng chính / viền theo phiếu có trọng số; `so_dong_min/max` = khoảng số dòng các bìa thắng."""
    ds = [(d, max(1.0, float(w or 1))) for d, w in ds if d and d.get("so_dong")]
    if not ds:
        return {}
    mt: Dict[str, Any] = {}
    # 19/10/2026: DẢI nền sau dòng từ khoá — khi bìa thắng mang ≥ nửa trọng số có dải: màu dải của bìa nặng ký nhất
    co_dai = sorted(((w, d["dai_tu_khoa"]) for d, w in ds if d.get("dai_tu_khoa")), reverse=True)
    if co_dai and sum(w for w, _m in co_dai) * 2 >= sum(w for _d, w in ds):
        mt["dai_tu_khoa"] = co_dai[0][1]
    for k in ("so_dong", "dt_dong_pct", "cao_chinh_pct", "ti_le_chinh", "khe_max", "ky_tu_dong", "mat_do_chu"):
        v = _trung_vi_trong_so([(d.get(k), w) for d, w in ds if isinstance(d.get(k), (int, float))])
        if v is not None:
            mt[k] = round(v, 2) if k != "so_dong" else int(v)
    mt["so_dong_min"] = min(int(d["so_dong"]) for d, _w in ds)
    mt["so_dong_max"] = max(int(d["so_dong"]) for d, _w in ds)
    mt["rong_khoi"] = round(_trung_vi_trong_so([(d["khoi"][2] - d["khoi"][0], w) for d, w in ds]) or 0.0, 3)

    def phieu(k: str) -> str:
        dem: Dict[str, float] = {}
        for d, w in ds:
            if d.get(k):
                dem[str(d[k])] = dem.get(str(d[k]), 0.0) + w
        return max(dem, key=lambda x: dem[x]) if dem else ""
    for k in ("mau_do", "mau_vang"):  # màu của bìa thắng nặng ký nhất có đo được màu ấy
        co = sorted(((w, d[k]) for d, w in ds if d.get(k)), reverse=True)
        if co:
            mt[k] = co[0][1]
    mt.update(ben_nv=phieu("ben_nv"), mau_chinh=phieu("mau_chinh"), vien=phieu("vien") or "thick",
              tu_khoa_do=sum(w for d, w in ds if d.get("tu_khoa_do")) * 2 >= sum(w for _d, w in ds), bia=len(ds))
    return mt


_NV_CUA_BO = {"trai": "phai", "phai": "trai", "dai": "giua"}


def _muc_tieu_theo_bo(do: Sequence[Tuple[Dict[str, Any], float]], bo: str = "") -> Dict[str, Any]:
    """Tổng hợp số đo theo BỐ CỤC lô (`bo` "trai"/"phai"/"dai"): chỉ các bìa thắng cùng bên nhân vật (cột chữ trái ↔
    nhân vật phải…) nếu có, không thì mọi bìa."""
    cung = [(d, w) for d, w in do if bo and d.get("ben_nv") == _NV_CUA_BO.get(bo)]
    return dict(tong_hop_bo_cuc(cung or list(do)), theo_bo=bo if cung else "")


def bo_cuc_thang(goc: str, kenh: str, thu_muc: str, *, goi: Optional[Callable[..., str]] = None,
                 log: Callable[[str], None] = print, dem: Optional[Dict[str, int]] = None, bo: str = "") -> Dict[str, Any]:
    """MỤC TIÊU bố cục chữ của kênh từ thư mục bìa thắng `thu_muc` (`thang.json` xếp theo lượt bấm): `bo-cuc.json`
    (đặt tay, `nguon` "tay") > số đo cache `bo-cuc-thang.json` (khoá theo tệp) > một lượt AI đo mỗi bìa trong
    `SO_BIA_DO` bìa đầu bảng (ví ShopAPI — `goi`). Tổng hợp theo bố cục lô `bo` (`_muc_tieu_theo_bo`). Không có gì
    → {} (bộ vẽ giữ luật cũ). Không ném lỗi."""
    if not thu_muc or not os.path.isdir(thu_muc):
        return {}
    tay = _doc_json(os.path.join(thu_muc, TEP_BO_CUC_TAY))
    if isinstance(tay, dict) and tay.get("so_dong"):
        return dict(tay, nguon="tay")
    bia = bia_thu_muc(thu_muc)[:SO_BIA_DO]
    if not bia:
        return {}
    khoa = _bam(*["{0}:{1}".format(os.path.basename(b["tep"]), os.path.getsize(b["tep"])) for b in bia],
                PHIEN_BAN_BO_CUC)
    duong = os.path.join(thu_muc, TEP_BO_CUC_THANG)
    cu = _doc_json(duong)

    def tu_cache(c: Dict[str, Any], nguon: str) -> Dict[str, Any]:
        do = [(x, float(x.get("trong_so") or 1)) for x in c.get("bia") or [] if isinstance(x, dict)]
        mt = _muc_tieu_theo_bo(do, bo)
        return dict(mt, nguon=nguon) if mt else {}
    if isinstance(cu, dict) and cu.get("khoa") == khoa and (cu.get("bia") or cu.get("khong_do_duoc")):
        return tu_cache(cu, "do")
    if goi is None:
        return tu_cache(cu, "do-cu") if isinstance(cu, dict) and cu.get("bia") else {}
    chi_tiet, tra_loi = [], 0
    for b in bia:
        d, tho = None, None
        # 19/10/2026: bìa thắng nặng ký nhất (TL2 177k) từng rơi khỏi số đo vì MỘT câu trả lời đọc hỏng → mục tiêu
        # lấy từ bìa yếu (chữ 27% thay 51%). Đo hỏng thì đo lại tới `LAN_DO_BO_CUC` lần (khoá mới mỗi lần).
        for lan in range(LAN_DO_BO_CUC):
            try:
                if dem is not None:
                    dem["llm"] = dem.get("llm", 0) + 1
                from PIL import Image  # noqa: PLC0415
                tho = _json(goi(LOI_NHAC_DO_BO_CUC, khoa="bia-lo-bo-cuc{2}:{0}:{1}".format(kenh, _bam(
                    b["tep"], os.path.getsize(b["tep"])), "-v{0}{1}".format(PHIEN_BAN_BO_CUC, ":l{0}".format(lan)
                                                                         if lan else "")),
                    toi_da_token=2500, mo_hinh=MO_HINH_CHAM, anh=[_url_anh(b["tep"], 1280)]))
                tra_loi += 1 if isinstance(tho, dict) else 0
                with Image.open(b["tep"]) as im:
                    d = doc_do_bo_cuc(tho, im.convert("RGB"))
            except Exception as loi:  # noqa: BLE001 — một lần đo hỏng: đo lại
                log("  (bìa lô: đo bố cục {0} hỏng: {1})".format(os.path.basename(b["tep"]), str(loi)[:120]))
                d = None
            if d:
                break
            log("  (bìa lô: đo bố cục {0} không ra số đo — đo lại {1}/{2})".format(
                os.path.basename(b["tep"]), lan + 1, LAN_DO_BO_CUC))
        if d:
            chi_tiet.append(dict({k: v for k, v in d.items() if k != "dong"}, tep=os.path.basename(b["tep"]), tho=tho,
                                 trong_so=round(float(b.get("imp") or 0) * float(b.get("ctr") or 0) / 100.0, 1),
                                 dong=[{"chu": x["chu"], "hop": x["hop"], "mau": x["mau"], "dai": x.get("dai") or ""}
                                       for x in d["dong"]]))
    if not chi_tiet:
        if tra_loi:  # AI trả lời mà không đo được bìa nào: ghi lại để mỗi lô không đo lại (thư mục đổi thì đo lại)
            _ghi_json(duong, {"khoa": khoa, "bia": [], "khong_do_duoc": True, "phien_ban": PHIEN_BAN_BO_CUC,
                              "luc": time.strftime("%Y-%m-%d %H:%M:%S")})
        return {}
    moi = {"khoa": khoa, "bia": chi_tiet, "phien_ban": PHIEN_BAN_BO_CUC, "luc": time.strftime("%Y-%m-%d %H:%M:%S")}
    _ghi_json(duong, moi)
    mt = tu_cache(moi, "do")
    log("  bìa lô: bố cục chữ bìa thắng — {0} dòng, chữ {1}% khung, dòng chính {2}% cao, nhân vật {3}".format(
        mt.get("so_dong"), mt.get("dt_dong_pct"), mt.get("cao_chinh_pct"), mt.get("ben_nv") or "?"))
    return mt


def muc_tieu_theo_chu(mt: Dict[str, Any], chu: str) -> Dict[str, Any]:
    """Mục tiêu bố cục cho chữ bìa CỤ THỂ (19/10/2026 — kiểm vàng TL2: chữ bìa 11 ký tự, bìa thắng ~25 ký tự → 28/28 tấm
    bị cổng bố cục loại vì không thể phủ 70% diện tích chữ bìa thắng): tỉ lệ r = số ký tự / (ký tự mỗi dòng × số dòng
    của bìa thắng); r < 1 → diện tích mục tiêu × √r và chữ to lên `he_co` = min(1,4, 1/√r) lần. Dòng chính vẫn phải
    ≥ 70% dòng chính bìa thắng (cổng không đổi)."""
    if not mt or not mt.get("dt_dong_pct"):
        return mt
    n = len(btk._chuan(chu_tron(chu)))  # noqa: SLF001
    n_thang = float(mt.get("ky_tu_dong") or 5) * float(mt.get("so_dong") or 3)
    r = n / max(1.0, n_thang)
    if not n or r >= 1.0:
        return dict(mt, n_chu=n, n_thang=round(n_thang, 1))
    return dict(mt, dt_goc=mt["dt_dong_pct"], dt_dong_pct=round(float(mt["dt_dong_pct"]) * r ** 0.5, 1),
                he_co=round(min(1.4, 1.0 / r ** 0.5), 2), n_chu=n, n_thang=round(n_thang, 1))


def kiem_bo_cuc(do: Dict[str, Any], mt: Dict[str, Any], *, cot: bool = True) -> List[str]:
    """CỔNG BỐ CỤC tất định: số đo tấm vừa vẽ (`do_hop_dong` trên hộp dòng của bộ vẽ) so MỤC TIÊU bìa thắng `mt` →
    lý do loại ([] = đạt): các dòng chữ chiếm < `HE_SO_DT_TOI_THIEU` × diện tích bìa thắng; dòng chính thấp hơn
    `HE_SO_CAO_TOI_THIEU` × dòng chính bìa thắng; kiểu cột (`cot`) mà khối chữ hở giữa (khe > `KHE_DONG_TOI_DA` và
    > khe bìa thắng). Không có mục tiêu → []."""
    ly: List[str] = []
    if not mt or not do.get("so_dong"):
        return ly
    if mt.get("dt_dong_pct") and do.get("dt_dong_pct", 0) < HE_SO_DT_TOI_THIEU * float(mt["dt_dong_pct"]):
        ly.append("chữ chiếm {0:.0f}% khung < {1:.0f}% (bìa thắng {2:.0f}%)".format(
            do["dt_dong_pct"], HE_SO_DT_TOI_THIEU * float(mt["dt_dong_pct"]), float(mt["dt_dong_pct"])))
    if mt.get("cao_chinh_pct") and do.get("cao_chinh_pct", 0) < HE_SO_CAO_TOI_THIEU * float(mt["cao_chinh_pct"]):
        ly.append("dòng chính cao {0:.0f}% khung < {1:.0f}% (bìa thắng {2:.0f}%)".format(
            do["cao_chinh_pct"], HE_SO_CAO_TOI_THIEU * float(mt["cao_chinh_pct"]), float(mt["cao_chinh_pct"])))
    if cot and do.get("khe_max", 0) > max(KHE_DONG_TOI_DA, float(mt.get("khe_max") or 0) + 0.04):
        ly.append("khối chữ hở giữa (khe {0:.0%} khung)".format(do["khe_max"]))
    return ly


def ho_so_kieu(goc: str, kenh: str, *, goi: Optional[Callable[..., str]] = None, log: Callable[[str], None] = print,
               dem: Optional[Dict[str, int]] = None, mau: Sequence[str] = ()) -> Dict[str, Any]:
    """Hồ sơ KIỂU bìa thắng của kênh cho cả lô: `kieu` ("hop"/"tran", `kieu_chu` của khuôn), `kc` (khuôn vẽ chữ),
    `bo_cuc` (bên/dải chữ), màu chữ trần, `uu_tien` (kiểu `do_bia`), `nhan_vat` (style.yaml), `nv` + `mau_dau`
    (nv1.png), `mau` (few-shot riêng kênh — cache `mau_thang`; lùi `MAU_THANG` cho kiểu hộp), `nen` (nền bìa thắng),
    `bia_mau` (chữ trần: bìa khuôn + bìa cùng kiểu — ảnh tham chiếu + mẫu so của giám khảo). Không ném lỗi.

    16/10/2026 — kênh chữ TRẦN có thư mục bìa thắng chủ chọn (`thu_muc_mau`: `mau` / `kenh.yaml: bia_lo_mau`): mẫu tả
    + ảnh tham chiếu + mẫu so của giám khảo lấy từ ĐÚNG thư mục ấy (theo thứ hạng). `kenh.yaml: bia_lo_kieu` ("tran" |
    "hop") và `bia_lo_bo_cuc` ("dai" | "trai" | "phai") ghi đè kiểu/bố cục chữ đo từ khuôn (khuôn đổi thì kiểu chữ của
    lô vẫn theo lựa chọn của chủ)."""
    from . import khuon_bia  # noqa: PLC0415
    try:
        khuon = khuon_bia.doc_khuon(goc, kenh) or {}
    except Exception:  # noqa: BLE001
        khuon = {}
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh as _dk  # noqa: PLC0415
        cai = doc_yaml(os.path.join(_dk(goc, kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        cai = {}
    kc = khuon.get("khuon_chu") if isinstance(khuon.get("khuon_chu"), dict) else {}
    kieu = kieu_chu(kc)
    if str(cai.get("bia_lo_kieu") or "").strip() in ("hop", "tran"):
        kieu = str(cai["bia_lo_kieu"]).strip()
    # `san_nv` (19/10/2026): lời nhắc ảnh có câu khoá nhân vật kênh + màu đậm (hồ sơ dựng tay của bài kiểm cũ: không)
    hs: Dict[str, Any] = {"kieu": kieu, "khuon_video": str(khuon.get("video_id") or ""), "san_nv": True}
    if kieu == "hop":
        hs["kc"] = kc if btk.kieu_hop(kc) else KHUON_HOP_MAC_DINH
        hs["bo_cuc"] = btk._ben_chu_hop(hs["kc"])  # noqa: SLF001
    else:
        bo_ep = str(cai.get("bia_lo_bo_cuc") or "").strip()
        hs["kc"], hs["uu_tien"] = kc, _uu_tien_vien(kc)
        hs["bo_cuc"] = bo_ep if bo_ep in ("dai", "trai", "phai") else bo_cuc_tran(kc)
        hs["mau_nen"], hs["mau_do"], hs["mau_vang"] = mau_tran(kc)
    # 19/10/2026: thư mục bìa thắng dùng cho MỌI kiểu chữ — lô TL4-0005 (kiểu hộp) lấy ảnh tham chiếu từ khuôn cũ, nền
    # nhạt theo `NEN_HOP_MAC_DINH`, không so với bìa thắng thật của kênh.
    tm = thu_muc_mau(goc, kenh, mau)
    hs["thu_muc_mau"] = tm
    from .kenh import duong_kenh  # noqa: PLC0415
    nv = os.path.join(duong_kenh(goc, kenh), "nv", "nv1.png")
    hs["nv"] = nv if os.path.isfile(nv) else ""
    hs["mau_dau"] = mau_dau_nv(nv) if hs["nv"] else None
    hs["nhan_vat"] = _nhan_vat_kenh(goc, kenh)
    try:
        mt = mau_thang(goc, kenh, khuon, goi=goi, log=log, dem=dem, thu_muc=tm)
    except Exception as loi:  # noqa: BLE001
        log("  (bìa lô: mẫu bìa thắng của kênh hỏng: {0})".format(str(loi)[:160]))
        mt = {}
    co_tang = any(isinstance(t, dict) for t in ((kc.get("chu") or {}).get("tang") or []))
    phieu = [str(b.get("kieu_chu") or "") for b in mt.get("bia") or []]
    if (tm and not co_tang and str(cai.get("bia_lo_kieu") or "").strip() not in ("hop", "tran") and kieu == "hop"
            and phieu.count("tran") * 2 > len(phieu)):
        # 19/10/2026: kênh chưa có khuôn + chưa khai `bia_lo_kieu` — kiểu chữ theo PHIẾU các bìa thắng trong thư mục
        # (mẫu tả: "bare"/"box"), bên chữ theo bên nhân vật ĐO trên bìa thắng — không lùi khuôn hộp mặc định.
        kieu = hs["kieu"] = "tran"
        bo_ep = str(cai.get("bia_lo_bo_cuc") or "").strip()
        if bo_ep not in ("dai", "trai", "phai"):
            try:
                bo_ep = {"phai": "trai", "trai": "phai", "giua": "dai"}.get(str(bo_cuc_thang(
                    goc, kenh, tm, goi=goi, log=log, dem=dem).get("ben_nv") or ""), "trai")
            except Exception:  # noqa: BLE001
                bo_ep = "trai"
        hs.update(kc=kc, uu_tien=_uu_tien_vien(kc), bo_cuc=bo_ep, nguon_kieu="phieu-bia-thang")
        hs["mau_nen"], hs["mau_do"], hs["mau_vang"] = mau_tran(kc)
    if mt.get("mau"):
        hs.update(mau=mt["mau"], nguon_mau="kenh" if mt.get("moi") else "kenh-cu", hinh_them=mt.get("hinh") or "")
    elif kieu == "hop":
        hs.update(mau=MAU_THANG, nguon_mau="mac-dinh-hop", hinh_them="")
    else:
        tang = ((kc.get("chu") or {}).get("tang") or [])
        hs.update(mau="- 「{0}」: {1}".format("|".join(str(t.get("noi_dung") or "") for t in tang if isinstance(t, dict)),
                                              kc.get("diem_hut_mat") or kc.get("bo_cuc") or ""),
                  nguon_mau="khuon", hinh_them="")
    if tm:
        # Thư mục chủ chọn: ảnh tham chiếu + mẫu so = các bìa ĐẦU BẢNG của thư mục (thứ hạng của chủ), mọi kiểu chữ —
        # chữ do mã vẽ; ảnh mẫu dạy nét vẽ / cảnh / nhân vật.
        hs["nen"] = "; ".join(x for x in (mt.get("nen") or "", nen_tu_khuon(kc) if kieu == "tran" else "") if x)
        hs["bia_mau"] = [b["tep"] for b in bia_thu_muc(tm)][:SO_MAU_TRAN]
        hs["bia_so"] = [b["tep"] for b in bia_thu_muc(tm)][:SO_BIA_SO]
        imp = [float(b["imp"]) for b in (mt.get("bia") or bia_thu_muc(tm)) if isinstance(b.get("imp"), (int, float))]
        hs["bang_chung"] = " ({0}-{1} impressions)".format(_k(min(imp)), _k(max(imp))) if imp else ""
    if kieu == "tran" and tm:
        # 18/10/2026: BỐ CỤC CHỮ của bìa thắng (số dòng, diện tích, dòng chính, bên nhân vật) → mục tiêu cứng bộ vẽ.
        try:
            hs["muc_tieu"] = bo_cuc_thang(goc, kenh, tm, goi=goi, log=log, dem=dem, bo=hs["bo_cuc"])
            # màu từ khoá ĐO trên bìa thắng thật thắng màu khuôn ghi (khuôn TL2: đỏ sẫm #D00000, bìa thắng: đỏ tươi)
            for k in ("mau_do", "mau_vang"):
                if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(hs["muc_tieu"].get(k) or "")):
                    hs[k] = hs["muc_tieu"][k]
        except Exception as loi:  # noqa: BLE001 — đo hỏng: bộ vẽ giữ luật cũ
            log("  (bìa lô: bố cục chữ bìa thắng hỏng: {0})".format(str(loi)[:160]))
            hs["muc_tieu"] = {}
    elif kieu == "tran":
        hs["nen"] = "; ".join(x for x in (nen_tu_khuon(kc), mt.get("nen") or "") if x)
        cung = [b for b in mt.get("bia") or [] if b.get("kieu_chu") == "tran" and os.path.isfile(str(b.get("tep")))
                and b.get("video_id") != hs["khuon_video"]]
        tep_khuon = str(khuon.get("tep") or "")
        bia_mau = [tep_khuon] if os.path.isfile(tep_khuon) else []
        # Bìa cùng kiểu có độ sáng GẦN bìa khuôn trước (TL2: khuôn kem sáng — bìa đèn rọi tối làm mô hình ảnh lẫn nền).
        sang_k = _do_sang_tb(tep_khuon) if bia_mau else None
        if sang_k is not None:
            lech = {b["tep"]: abs((_do_sang_tb(b["tep"]) or 0.0) - sang_k) for b in cung}
            # gần (≤ LECH_SANG_MAU) giữ thứ tự hiển thị; xa thì bìa gần độ sáng nhất trước
            cung.sort(key=lambda b: (lech[b["tep"]] > LECH_SANG_MAU, lech[b["tep"]] if lech[b["tep"]] > LECH_SANG_MAU
                                     else 0.0))
        bia_mau += [b["tep"] for b in cung if b["tep"] not in bia_mau]
        hs["bia_mau"] = bia_mau[:SO_MAU_TRAN]
        imp = [float(b["imp"]) for b in mt.get("bia") or [] if isinstance(b.get("imp"), (int, float))]
        hs["bang_chung"] = " ({0}-{1} impressions)".format(_k(min(imp)), _k(max(imp))) if imp else ""
    return hs


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


def loi_theo_kieu(ho_so: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Các mảnh lời nhắc đạo diễn + giám khảo theo kiểu chữ của kênh (`ho_so_kieu`). Không hồ sơ / kiểu hộp → đúng
    nguyên văn kiểu hộp TL4 (`LOI_DAO_DIEN_HOP`)."""
    hs = ho_so or {}
    ra = dict(LOI_DAO_DIEN_HOP)
    if hs.get("kieu") != "tran":
        # 19/10/2026: kiểu hộp của kênh KHÁC TL4 (TL4-K2 mượn khuôn hộp TL4) — nhân vật + bằng chứng của chính kênh
        if hs.get("nhan_vat"):
            ra["nhan_vat_cau"] = "the channel's own character ({0})".format(hs["nhan_vat"])
        if hs.get("bang_chung"):
            ra["bang_chung"] = hs["bang_chung"]
        return ra
    bo = hs.get("bo_cuc") if hs.get("bo_cuc") in _CHO_CHU_TRAN else "dai"
    ten_do, ten_vang = (btk._ten_mau(m).split(" #")[0] for m in (hs.get("mau_do"), hs.get("mau_vang")))  # noqa: SLF001
    mt = hs.get("muc_tieu") or {}
    so_dong = "2-3" if bo == "dai" else "2-4"
    bo_cuc_ta = ""
    if mt.get("so_dong"):
        # 18/10/2026: số dòng + cỡ khối chữ ĐO trên bìa thắng của kênh (`bo_cuc_thang`)
        lo, hi = max(2, int(mt.get("so_dong_min") or 2)), min(5, max(2, int(mt.get("so_dong_max") or 2)))
        so_dong = "{0}-{1}".format(lo, hi) if hi > lo else str(lo)
        bo_cuc_ta = (" The winners stack {0} lines in ONE solid block that fills about {1:.0f}% of the frame; the "
                     "keyword line is about {2:.0f}% of the frame height, clearly bigger than the others{3}.").format(
            so_dong, float(mt.get("dt_dong_pct") or 40), float(mt.get("cao_chinh_pct") or 25),
            ", painted RED" if mt.get("tu_khoa_do") else "") + (
            " The keyword line sits on a {0} brush-stroke band.".format(btk._ten_mau(mt["dai_tu_khoa"]).split(" #")[0])  # noqa: SLF001
            if mt.get("dai_tu_khoa") else "")
    ra.update(
        bang_chung=hs.get("bang_chung") or "",
        hinh="huge BARE lettering with a thick black outline — white, the keyword painted {0} or {1}, no boxes — "
             "carries the hook {2}{3}".format(ten_do, ten_vang, _CHO_CHU_TRAN[bo], bo_cuc_ta),
        vi_tri_nv=_NV_TRAN[bo], nhan_vat_cau="the channel's own character ({0})".format(
            hs.get("nhan_vat") or "the figure of the character reference"),
        hinh_them=(" In short: " + str(hs["hinh_them"]).strip()) if hs.get("hinh_them") else "",
        o_hook="on the thumbnail", vung_trong=_VUNG_TRONG_TRAN[bo],
        luat_danh_dau=LUAT_DANH_DAU_TRAN.format(so_dong=so_dong,
                                                to_toi_da=TRAN_TO_TOI_DA["dai" if bo == "dai" else "cot"]) + (
            " Put the RED keyword INSIDE the biggest line, as the winners do." if mt.get("tu_khoa_do") else ""),
        luat_canh="everyday JAPANESE life (apartment, small car, station, convenience store, office, park) or a simple "
                  "symbolic space; the background look follows the channel's winners — {0}; {1}".format(
                      (hs.get("nen") or "the same background look as the reference thumbnails").rstrip(". "),
                      _BO_CUC_LUAT_TRAN[bo]),
        o_chu="(huge outlined lettering)", chu_ten="letters", ngoai_chu="the hook lettering",
        phong_cach_ta="the same art style, background look and character as the winners, the same huge outlined "
                      "lettering in the same colours, polished")
    return ra


def dao_dien(goi: Callable[..., str], *, tieu_de: str, chu_bia: str, kich_ban: str = "", muc_luc: Sequence[str] = (),
             so_y: int = SO_Y_MAC_DINH, khoa: str = "bia-lo", ho_so: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """MỘT lượt LLM (+ một lượt sửa khi < 3 ý dùng được) → `{"y_tuong": [...], "chu": [cách chia chữ bìa]}`.
    `ho_so` (`ho_so_kieu`): mẫu bìa thắng + kiểu chữ + nhân vật CỦA kênh; không có → kiểu hộp TL4 (`MAU_THANG`)."""
    so_y = max(1, min(int(so_y), SO_Y_TOI_DA))
    lk = loi_theo_kieu(ho_so)
    loi_nhac = LOI_NHAC_DAO_DIEN.format(mau=(ho_so or {}).get("mau") or MAU_THANG, tieu_de=tieu_de, chu_bia=chu_bia,
                                        so_y=so_y, muc_luc=" / ".join(str(m) for m in muc_luc)[:900] or "(none)",
                                        kich_ban=str(kich_ban or "")[:4000] or "(none)", luat_nv=LUAT_NHAN_VAT,
                                        **{k: lk[k] for k in ("bang_chung", "hinh", "vi_tri_nv", "nhan_vat_cau",
                                                              "hinh_them", "o_hook", "vung_trong", "luat_danh_dau",
                                                              "luat_canh")})
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
    """Chữ bìa bỏ dấu đánh dấu ("同じ車に長く|*乗る人の|ほとんどが" → "同じ車に長く乗る人のほとんどが"; cả "< >"/"{ }"
    tô màu của kiểu chữ trần)."""
    return re.sub(r"[|*^\[\]()<>{}]", "", str(chu or "")).strip()


def doc_danh_dau_tran(s: str) -> List[Dict[str, Any]]:
    """Chữ bìa có dấu kiểu TRẦN → dòng `{to, phan_mau: [{chu, vai}]}`: "|" xuống dòng, "[ ]" dòng cực to, "< >" từ khoá
    ĐỎ (`vai` "do"), "{ }" từ VÀNG ("vang"), còn lại "nen" (trắng). Dấu "( )" của kiểu hộp bỏ đi, giữ chữ."""
    s = str(s or "").strip().translate(str.maketrans("［］（）｜＜＞｛｝", "[]()|<>{}")).replace("\n", "|")
    ra: List[Dict[str, Any]] = []
    for dong in s.split("|"):
        dong = dong.strip()
        if not dong:
            continue
        to = "[" in dong and "]" in dong
        phan: List[Dict[str, Any]] = []
        vai, cur = "nen", ""
        for c in re.sub(r"[\[\]()]", "", dong):
            if c in "<>{}":
                if cur:
                    phan.append({"chu": cur, "vai": vai})
                cur, vai = "", ("do" if c == "<" else "vang" if c == "{" else "nen")
                continue
            cur += c
        if cur:
            phan.append({"chu": cur, "vai": vai})
        if phan:
            ra.append(dict({"phan_mau": phan}, **({"to": True} if to else {})))
    return ra


def _to_mau_may(tang: List[Dict[str, Any]]) -> None:
    """Tô màu MÁY khi không có dấu màu nào: dòng cực to ≥ 2 cụm → các cụm đầu đỏ, cụm cuối vàng; 1 cụm → đỏ."""
    for t in tang:
        if not t.get("to"):
            continue
        s = btk.chu_cua_tang(t)
        cum = btk._cum_chu(s)  # noqa: SLF001
        t["phan_mau"] = ([{"chu": "".join(cum[:-1]), "vai": "do"}, {"chu": cum[-1], "vai": "vang"}] if len(cum) >= 2
                         else [{"chu": s, "vai": "do"}])


def so_dong_muc(chu: str, mt: Optional[Dict[str, Any]], bo: str = "trai") -> int:
    """Số dòng MỤC TIÊU cho chữ bìa `chu` theo bố cục bìa thắng `mt`: số ký tự / (ký tự mỗi dòng của bìa thắng × 0,9),
    kẹp trong [so_dong_min, so_dong_max] của bìa thắng (≥ 2, ≤ 5). Không có mục tiêu → 0 (luật cũ)."""
    if not mt or not mt.get("so_dong"):
        return 0
    n = len(btk._chuan(chu_tron(chu)))  # noqa: SLF001
    kt = float(mt.get("ky_tu_dong") or 0) or 5.0
    lo, hi = max(2, int(mt.get("so_dong_min") or 2)), min(5, max(2, int(mt.get("so_dong_max") or mt["so_dong"])))
    return max(lo, min(hi, int(round(n / (kt * 0.9))) if n else lo))


def _co_mau(t: Dict[str, Any], vai: str) -> bool:
    return any(p.get("vai") == vai for p in t.get("phan_mau") or [])


def _tach_tu_khoa_do(tang: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ít dòng hơn mục tiêu: dòng có từ khoá ĐỎ kèm đoạn khác (「お金」+「じゃない」) tách thành dòng từ khoá riêng (cực to,
    như 「悠々自適に」 của bìa thắng TL2) + dòng phần còn lại — mỗi phần ≥ 2 ký tự. Không tách được → giữ nguyên."""
    for i, t in enumerate(tang):
        pm = [p for p in t.get("phan_mau") or [] if p.get("chu")]
        k = next((j for j, p in enumerate(pm) if p.get("vai") == "do"), None)
        if k is not None and len(pm) == 1 and len(btk._chuan(pm[0]["chu"])) >= 4:  # noqa: SLF001
            # cả dòng một đoạn ĐỎ (「お金じゃない」): từ khoá = tiền tố tới hết cụm Hán/Katakana đầu (「お金」), phần sau trắng
            # phần sau phải mở đầu bằng trợ từ/trợ động từ (「お金」+「じゃない」) — không cắt giữa từ: kiểm vàng 19/10
            # tách 「引き受けない」 thành 「引」+「き受けない」
            m = re.match(r"^([぀-ゟ]{0,2}[一-鿿々〆ァ-ヿ0-9０-９]+)((?:じゃ|では|は|が|を|に|で|の|も|と|より|ほど|こそ|"
                         r"って|だ|です|な)(?:.+)?)$", pm[0]["chu"])
            if m and (len(m.group(2)) < 2 or len(m.group(1)) < 2):
                m = None
            if m:
                return tang[:i] + [{"phan_mau": [{"chu": m.group(1), "vai": "do"}], "to": True},
                                   {"phan_mau": [{"chu": m.group(2), "vai": "nen"}]}] + tang[i + 1:]
            continue
        if k is None or len(pm) < 2:
            continue
        # phần đỏ + đuôi ngắn ≤ 1 ký tự dính sau (「悠々自適」+「に」) giữ cùng dòng
        a, b = pm[:k + 1], pm[k + 1:]
        if b and len(btk._chuan(b[0]["chu"])) == 1:  # noqa: SLF001
            a, b = a + b[:1], b[1:]
        if pm[:k]:
            truoc = pm[:k]
            if len(btk._chuan("".join(p["chu"] for p in truoc))) >= 2 and not b:  # noqa: SLF001
                return tang[:i] + [{"phan_mau": truoc}, {"phan_mau": pm[k:], "to": True}] + tang[i + 1:]
            continue
        if b and len(btk._chuan("".join(p["chu"] for p in a))) >= 2 and len(  # noqa: SLF001
                btk._chuan("".join(p["chu"] for p in b))) >= 2:  # noqa: SLF001
            return tang[:i] + [{"phan_mau": a, "to": True}, {"phan_mau": b}] + tang[i + 1:]
    return tang


def doc_chu_bia_tran(chu: str, ho_so: Dict[str, Any], *, cach_ai: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """`_doc_chu_bia_tran` + 19/10/2026: độ ĐẬM nét theo bìa thắng (`_chon_dam` — mục tiêu `mat_do_chu` đo trên bìa
    thắng của kênh)."""
    tang = _doc_chu_bia_tran(chu, ho_so, cach_ai=cach_ai)
    mt = ho_so.get("muc_tieu") or {}
    if mt.get("mat_do_chu"):
        dp = _chon_dam(tang, ho_so)
        if dp:
            tang = [dict(t, dam_pct=dp) for t in tang]
    return tang


#: Các mức "đậm giả" thử (× cỡ chữ) — mặc định của bộ vẽ là 0,022.
DAM_THU = (0.022, 0.032, 0.042, 0.052)


def _ve_thu(t2: List[Dict[str, Any]], ho_so: Dict[str, Any], bo: str, bc: Dict[str, Any]):
    """Vẽ THỬ các tầng trên khung trơn (cột đầu tiên của `cach_bo_cuc_tran`) → ảnh PIL (None khi hỏng); `bc` = báo cáo."""
    import tempfile  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    mt = ho_so.get("muc_tieu") or {}
    rong = cach_bo_cuc_tran(bo, mt)[0][0]
    khung = None if bo == "dai" else ((0.0, 0.0, rong, 1.0) if bo == "trai" else (1.0 - rong, 0.0, 1.0, 1.0))
    dt = float(mt.get("dt_dong_pct") or 0)
    with tempfile.TemporaryDirectory() as tm:
        dich = os.path.join(tm, "thu.png")
        ok = btk.ve_chu_len_anh("", dich, t2, anh_nen=Image.new("RGB", (1280, 720), (150, 120, 90)), bao_cao=bc,
                                khung_chu=khung, cho_khung=False, uu_tien_kieu=ho_so.get("uu_tien") or UU_TIEN_VIEN_DEN,
                                nhan_toi_da=2, dien_tich_muc=(0.92 * dt, 1.15 * dt) if dt else None,
                                doc_khoi=0.5 if any(t.get("khoi") for t in t2) else None)
        if not ok:
            return None
        with Image.open(dich) as im:
            return im.convert("RGB")


def _chon_dam(tang: List[Dict[str, Any]], ho_so: Dict[str, Any]) -> float:
    """Mức "đậm giả" nhỏ nhất trong `DAM_THU` cho nét dòng chính đạt ≥ 95% mật độ nét bìa thắng (`mat_do_chu`, đo
    CÙNG cách: hộp đo sát nét `tinh_hop_dong` + `mat_do_chu`) — không đạt thì mức lớn nhất. 0 = không đo được."""
    mt = ho_so.get("muc_tieu") or {}
    muc = float(mt.get("mat_do_chu") or 0)
    bo = ho_so.get("bo_cuc") if ho_so.get("bo_cuc") in ("trai", "phai", "dai") else "dai"
    i = next((k for k, t in enumerate(tang) if t.get("to")), 0)
    for dp in DAM_THU:
        bc: Dict[str, Any] = {}
        try:
            im = _ve_thu([dict(t, dam_pct=dp) for t in tang], ho_so, bo, bc)
            dong = [d for d in bc.get("dong") or [] if d.get("hop")]
            if im is None or len(dong) != len(tang):
                return 0.0
            h = [v / s for v, s in zip(sorted(dong, key=lambda d: d["hop"][1])[i]["hop"], (1280, 720, 1280, 720))]
            md = mat_do_chu(im, tinh_hop_dong(im, [h])[0])
        except Exception:  # noqa: BLE001
            return 0.0
        if md is not None and md >= 0.95 * muc:
            return dp
    return DAM_THU[-1]


def _doc_chu_bia_tran(chu: str, ho_so: Dict[str, Any], *, cach_ai: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """Chữ bìa → tầng chữ TRẦN đã bố trí cho `bia_theo_khuon.ve_chu_len_anh` theo khuôn chữ trần của kênh.

    Cách chia: `chu` có dấu (cú pháp hộp "a|*b" hoặc trần "a|[<b>]") > cách chia AI giữ TRỌN chữ bìa > chia máy
    (`btk._tach_tang_hop`). Màu: "nen" = màu chữ nền khuôn (trắng), "do"/"vang" = màu từ khoá của khuôn; không dấu màu
    nào → tô máy (`_to_mau_may`). Bố trí: dải (nhân vật giữa) — dòng đầu ở dải trên, các dòng sau từ dải dưới lên; cột —
    các dòng xếp từ trên, dòng cuối từ dưới lên, canh mép phía cột. Dòng cực to là tầng chính (trần 30%), dòng khác ≤
    `TRAN_CO_VUA_PCT`; mọi dòng giữ một dòng (`mot_dong`) — cách chia đã quyết, bộ vẽ không tự xuống dòng.

    18/10/2026 — có MỤC TIÊU bố cục bìa thắng (`ho_so.muc_tieu`, `bo_cuc_thang`): chọn cách chia có số dòng gần
    `so_dong_muc` nhất (rồi dòng cực to ≤ `TRAN_TO_TOI_DA`, rồi thứ tự AI); dòng cực to là dòng mang từ khoá ĐỎ như bìa
    thắng (TL2-T7-0031: AI để 「足りないのは」 cực to còn 「お金」 đỏ tí hon ở đáy); cao dòng chính / dòng vừa / viền theo số
    đo bìa thắng; kiểu cột: MỘT khối dòng xếp từ trên (`khoi`, bộ vẽ đặt khối giữa cột) — không hở giữa."""
    bo = ho_so.get("bo_cuc") if ho_so.get("bo_cuc") in ("trai", "phai", "dai") else "dai"
    mt = ho_so.get("muc_tieu") or {}
    to_toi_da = TRAN_TO_TOI_DA["dai" if bo == "dai" else "cot"]
    s = str(chu or "").strip()
    goc_chu = re.sub(r"\s+", "", btk._cat_theo_tran(chu_tron(s)))  # noqa: SLF001
    n_muc = so_dong_muc(s, mt, bo)
    toi_da_dong = max(4, n_muc, min(5, int(mt.get("so_dong_max") or 0)))
    cac: List[str] = []
    if re.search(r"[|\[<{]", s) or s.startswith("*"):
        cac.append("|".join(("[" + p[1:].replace("^", "") + "]") if p.startswith("*") else p.replace("^", "")
                            for p in (x.strip() for x in s.split("|")) if p))
    cac += [x for x in cach_ai if isinstance(x, str)][:4]
    hop_le: List[List[Dict[str, Any]]] = []
    for x in cac:
        tang = doc_danh_dau_tran(x)
        if (1 <= len(tang) <= toi_da_dong and re.sub(r"\s+", "", "".join(btk.chu_cua_tang(t) for t in tang)) == goc_chu
                and all(len(btk._chuan(btk.chu_cua_tang(t))) <= btk.TRAN_KY_TU_TANG for t in tang)):  # noqa: SLF001
            hop_le.append(tang)

    def dai_to(tang) -> int:
        return max([len(btk._chuan(btk.chu_cua_tang(t))) for t in tang if t.get("to")] or [99])  # noqa: SLF001

    def may() -> List[Dict[str, Any]]:
        return [{"phan_mau": [{"chu": btk.chu_cua_tang(t), "vai": "nen"}], **({"to": True} if t.get("to") else {})}
                for t in btk._tach_tang_hop(btk._cat_theo_tran(chu_tron(s)), toi_da=toi_da_dong)]  # noqa: SLF001
    nguoi = hop_le[0] if hop_le and (re.search(r"[|\[<{]", s) or s.startswith("*")) else None
    if n_muc and not nguoi:
        # 18/10/2026: mọi cách chia (AI, AI tách từ khoá đỏ, máy) vẽ THỬ trên khung trơn → cách gần bìa thắng nhất
        # (diện tích chữ + dòng chính so mục tiêu, số dòng gần mục tiêu). TL2-T7-0029: cách 5 dòng của AI ra chữ bé 20%.
        ung: List[List[Dict[str, Any]]] = []
        for h in hop_le + [may()]:
            for v in (h, _tach_tu_khoa_do([dict(t) for t in h])):
                khoa = json.dumps([[p.get("chu"), p.get("vai")] for t in v for p in t.get("phan_mau") or []]
                                  + [len(v), [i for i, t in enumerate(v) if t.get("to")]], ensure_ascii=False)
                if v and khoa not in {json.dumps(x[1], ensure_ascii=False) for x in []} and \
                        khoa not in [k for k, _v in ung]:
                    ung.append((khoa, v))
        cac_bo = [(_bo_tri_tran([dict(t) for t in v], ho_so, to_toi_da, bo), v) for _k, v in ung]
        # 19/10/2026 (kiểm vàng TL2): cách chia của MÁY tô đỏ dòng cực to bất kể từ khoá — cách giữ dấu màu từ khoá
        # của AI (đạo diễn đọc nghĩa) được ưu tiên khi cùng qua / cùng trượt cổng bố cục.
        diem = []
        for i, (t2, v) in enumerate(cac_bo):
            d = _diem_thu(t2, ho_so, n_muc, bo)
            mau_ai = int(any(p.get("vai") in ("do", "vang") for t in v for p in t.get("phan_mau") or []))
            diem.append(((d[0], mau_ai, d[1]), i))
        return cac_bo[max(diem)[1]][0]
    if n_muc and hop_le:
        tang = nguoi or min(hop_le, key=lambda t: (abs(len(t) - n_muc), dai_to(t) > to_toi_da, hop_le.index(t)))
    else:
        tang = next((t for t in hop_le if dai_to(t) <= to_toi_da), hop_le[0] if hop_le else None)
    if tang is None:
        tang = may()
    if n_muc and len(tang) < n_muc:
        tang = _tach_tu_khoa_do(tang)
    return _bo_tri_tran(tang, ho_so, to_toi_da, bo, giu_to=nguoi is not None)


def _diem_thu(t2: List[Dict[str, Any]], ho_so: Dict[str, Any], n_muc: int, bo: str) -> Tuple[float, ...]:
    """Điểm MỘT cách chia đã bố trí: vẽ thử trên khung trơn (cột đầu tiên của `cach_bo_cuc_tran`, mục tiêu diện tích
    bìa thắng) → (qua cổng bố cục?, diện tích/mục tiêu + dòng chính/mục tiêu − 0,1 × lệch số dòng). Vẽ hỏng → thấp."""
    mt = ho_so.get("muc_tieu") or {}
    dt = float(mt.get("dt_dong_pct") or 0)
    bc: Dict[str, Any] = {}
    if _ve_thu(t2, ho_so, bo, bc) is None:
        return (0, -9.0)
    do = do_hop_dong([d["hop"] for d in bc.get("dong") or [] if d.get("hop")], W=1280, H=720)
    qua = not kiem_bo_cuc(do, mt, cot=bo != "dai")
    s = (min(1.0, do.get("dt_dong_pct", 0) / max(1.0, dt)) if dt else 0.0) + (
        min(1.0, do.get("cao_chinh_pct", 0) / max(1.0, float(mt.get("cao_chinh_pct") or 1))))
    return (int(qua), round(s - 0.1 * abs(len(t2) - n_muc), 3))


def _bo_tri_tran(tang: List[Dict[str, Any]], ho_so: Dict[str, Any], to_toi_da: int, bo: str, *,
                 giu_to: bool = False) -> List[Dict[str, Any]]:
    """Cách chia (dòng `{phan_mau: [{chu, vai}], to}`) → tầng chữ trần đã bố trí (màu, dòng cực to, cỡ, vị trí).
    Có mục tiêu bìa thắng: kiểu DẢI → dòng cực to là dòng DƯỚI (vế trả lời — bìa thắng TL1/TL3 「やさしさではない」,
    「低IQの人の思考の癖」 to hơn dòng trên); kiểu cột → dòng mang từ khoá ĐỎ. `giu_to`: cách chia có dấu của người."""
    mt = ho_so.get("muc_tieu") or {}
    for t in tang:  # khoảng trắng giữa chữ Nhật trong MỘT dòng (AI chèn quanh dấu màu) không vẽ
        for p in t.get("phan_mau") or []:
            p["chu"] = re.sub(r"(?<=[^ -~])\s+|\s+(?=[^ -~])", "", str(p.get("chu") or ""))
    to = [i for i, t in enumerate(tang) if t.get("to")]
    if mt and bo == "dai" and len(tang) > 1 and not giu_to:
        to = [len(tang) - 1]
    elif mt.get("tu_khoa_do") and not giu_to and not (to and _co_mau(tang[to[0]], "do")):
        # bìa thắng: từ khoá ĐỎ nằm trong dòng cực to → dòng mang màu đỏ (đủ ngắn) thành dòng cực to
        do = [i for i, t in enumerate(tang) if _co_mau(t, "do")
              and len(btk._chuan(btk.chu_cua_tang(t))) <= to_toi_da]  # noqa: SLF001
        if do:
            to = [do[0]]
    for i, t in enumerate(tang):
        t.pop("to", None)
        if i == (to[0] if to else btk._chon_dong_to([btk.chu_cua_tang(x) for x in tang])):  # noqa: SLF001
            t["to"] = True
    if not any(p.get("vai") in ("do", "vang") for t in tang for p in t["phan_mau"]):
        _to_mau_may(tang)
    mau = {"nen": ho_so.get("mau_nen") or "#FFFFFF", "do": ho_so.get("mau_do") or MAU_DO_MAC_DINH,
           "vang": ho_so.get("mau_vang") or MAU_VANG_MAC_DINH}
    # 19/10/2026: chữ bìa NGẮN hơn chữ bìa thắng → chữ to hơn theo `he_co` (`muc_tieu_theo_chu`)
    he = float(mt.get("he_co") or 1.0)
    cao_chinh = min(btk.DONG_TOI_DA_PCT / 1.05, float(mt.get("cao_chinh_pct") or 0) * he)
    co_vua = (max(12.0, min(24.0 * he, 1.1 * cao_chinh / max(1.0, float(mt.get("ti_le_chinh") or 1.3))))
              if cao_chinh else TRAN_CO_VUA_PCT)
    vien = VIEN_THEO_DO.get(str(mt.get("vien") or "")) if mt else None
    khoi = bool(mt) and bo != "dai"
    n = len(tang)
    ra: List[Dict[str, Any]] = []
    for i, t in enumerate(tang):
        if bo == "dai":
            vt = "tren" if (i == 0 and n > 1) else "duoi"
        else:
            vt = "tren" if (khoi or i < n - 1 or n == 1) else "duoi"
        t2: Dict[str, Any] = {"vi_tri": vt, "phan_mau": [{"chu": p["chu"], "mau": mau.get(p.get("vai"), mau["nen"])}
                                                         for p in t["phan_mau"] if p.get("chu")],
                              "vung": (0.0, 1.0), "can": {"dai": "giua", "trai": "trai", "phai": "phai"}[bo],
                              "chinh": bool(t.get("to")), "mot_dong": True}
        if t.get("to"):
            t2["to"] = True
            if cao_chinh:
                t2["co_toi_da_pct"] = round(min(btk.DONG_TOI_DA_PCT, 1.05 * cao_chinh), 1)
        else:
            t2["co_toi_da_pct"] = round(co_vua, 1)
        if vien:
            t2["vien_px_pct"] = vien
        if khoi:
            t2["khoi"] = True
        # 19/10/2026: bìa thắng có DẢI nền sau dòng từ khoá (TL2: dải cọ đỏ sẫm) → dòng cực to / dòng mang màu đỏ
        if mt.get("dai_tu_khoa") and (t.get("to") or _co_mau(t, "do")):
            t2["dai"] = mt["dai_tu_khoa"]
        ra.append(t2)
    return ra


# ── 2) Vẽ hàng loạt ──────────────────────────────────────────────────────────


LOI_NHAC_NEN_TRAN = (
    "YouTube thumbnail illustration for a Japanese psychology channel, drawn in EXACTLY the same art style as this "
    "channel's real winning thumbnails (the attached reference images that show big outlined lettering — copy ONLY "
    "their art style, character rendering, palette and light, never their text). Background look of the winners: "
    "{nen}. The main character is the figure from the character reference image (the image that shows only that "
    "figure){nhan_vat}, with a BIG clear expressive face ({mat}){tu_the}. Any other people are faded, featureless "
    "silhouettes drawn in the same style. Scene — one visual metaphor that makes people curious: {canh}. "
    "Composition: {bo_cuc} "
    "Colours are rich and the light has strong contrast, like the winners — never pale, washed-out, faded or greyish. "
    "The picture contains NO writing of any kind: no letters, words, numbers, percentages, labels, price tags, signs, "
    "logos or watermark, and none of these instructions written into the image — any tag, sign or screen is blank. "
    "Aspect ratio 16:9.")
_BO_CUC_NEN_TRAN = {
    "trai": "the character and the scene sit on the RIGHT side of the picture, the character big (head and upper body "
            "at least half the frame height); the LEFT half is a calm, uncluttered continuation of the same background "
            "with no objects, where huge lettering is added later — no panels, no dividing line, no frame. The "
            "character's face stays fully on the right side.",
    "phai": "the character and the scene sit on the LEFT side of the picture, the character big (head and upper body "
            "at least half the frame height); the RIGHT half is a calm, uncluttered continuation of the same background "
            "with no objects, where huge lettering is added later — no panels, no dividing line, no frame. The "
            "character's face stays fully on the left side.",
    "dai": "the character stands BIG in the CENTRE of the picture with its head in the middle of the frame (never in the "
           "top quarter), the clue right beside it; the TOP quarter and the BOTTOM third of the frame are a calm "
           "continuation of the background without important detail, where huge lettering is added later — no bars, "
           "no panels, no frame."}


def _canh_day_du(y: Dict[str, str], cham: str = "") -> str:
    """Cảnh + manh mối + đối lập. `cham` = dấu sau câu cảnh (kiểu hộp giữ nguyên văn cũ — khoá ảnh theo lời nhắc)."""
    return "{0}{3} The curiosity clue, drawn big, clear and instantly recognisable: {1}{2}".format(
        y["canh"].rstrip("."), y["manh_moi"].rstrip("."), (". Contrast: " + y["doi_lap"].rstrip(".")) if y.get(
            "doi_lap") else "", cham)


def loi_nhac_nen_tran(y: Dict[str, str], ho_so: Dict[str, Any]) -> str:
    """Lời nhắc ảnh NỀN (không chữ) cho bìa chữ TRẦN: nét vẽ/bảng màu = bìa thắng thật của kênh (ảnh tham chiếu), nền
    theo khuôn (`ho_so.nen`), nhân vật theo `style.yaml` + nv1.png, cảnh = ý tưởng, chừa trống cột/dải chữ của khuôn."""
    bo = ho_so.get("bo_cuc") if ho_so.get("bo_cuc") in _BO_CUC_NEN_TRAN else "dai"
    nv = str(ho_so.get("nhan_vat") or "").strip()
    return LOI_NHAC_NEN_TRAN.format(
        nen=(ho_so.get("nen") or "the same background look as the reference thumbnails").rstrip("."),
        nhan_vat=(": " + nv) if nv else "", mat=str(y.get("mat") or "a strong, clear emotion").strip(),
        tu_the=(", " + str(y["tu_the"]).strip()) if y.get("tu_the") else "", canh=_canh_day_du(y, ".").rstrip("."),
        bo_cuc=_BO_CUC_NEN_TRAN[bo])


def loi_nhac_anh(y: Dict[str, str], kc: Dict[str, Any], nen: str = "", ho_so: Optional[Dict[str, Any]] = None) -> str:
    """Ý tưởng → lời nhắc ảnh NỀN (không chữ) theo `btk.loi_nhac_hop_chu` (nét bìa thắng, nhân vật kênh, phía chữ
    trống), cảnh = `canh` + manh mối vẽ to rõ + đối lập. Kênh kiểu chữ TRẦN (`ho_so`) → `loi_nhac_nen_tran`."""
    hs = ho_so or {}
    dan = (" " + str(hs["dan"]).strip()) if hs.get("dan") else ""  # lời dặn lô làm lại (lô trước dưới sàn vì gì)
    if hs.get("kieu") == "tran":
        return loi_nhac_nen_tran(y, hs) + " " + LIEN_MACH + (" " + MAU_DAM + " " + NV_ANH if hs.get("san_nv") else "") \
            + dan
    if not hs.get("san_nv"):  # đường cũ (bài kiểm / hồ sơ cũ): đúng nguyên văn
        return btk.loi_nhac_hop_chu(kc, bien_the={"canh": _canh_day_du(y), "net_mat": y.get("mat", ""),
                                                  "tu_the": y.get("tu_the", "")}, nen=nen) + " " + LIEN_MACH + dan
    # 19/10/2026 — kiểu hộp: nhân vật CỦA kênh (style.yaml), nền theo bìa thắng thật + màu đậm như bìa thắng
    return btk.loi_nhac_hop_chu(kc, bien_the={"canh": _canh_day_du(y), "net_mat": y.get("mat", ""),
                                              "tu_the": y.get("tu_the", "")}, nen=nen,
                                nhan_vat=str(hs.get("nhan_vat") or "")) + " " + MAU_DAM + " " + LIEN_MACH + " " + \
        NV_ANH + dan


#: 19/10/2026 — ảnh nền: nhân vật đúng kênh + màu đậm như bìa thắng (TL4-0005 nhạt, nhân vật lệch).
NV_ANH = ("The main character is ALWAYS exactly the figure of the character reference image — never a different "
          "person, never older or younger, no hair, wrinkles or clothes it does not have; nobody else has a detailed "
          "face.")
MAU_DAM = ("Colours are rich and saturated and the light has strong contrast with deep shadows and bright highlights, "
           "like the winners — never pale, washed-out, faded, greyish or a single pastel tint.")
#: 14/10/2026 (lô thật TL4-T7-0001: giám khảo loại 8/20 nền vì "panel split" — nửa trái là một tấm phẳng có mép dọc).
LIEN_MACH = ("The background is ONE continuous scene across the whole width: the empty part is simply the same wall, "
             "floor and light continuing, softly out of focus — never a separate flat panel, block of colour or "
             "vertical edge.")


def sinh_hang_loat(ve: Callable[[str, int, str, List[str]], List[str]], ds_y: Sequence[Dict[str, str]], moi_y: int,
                   thu_muc: str, *, kc: Dict[str, Any], nen: str = "", tran: int = TRAN_ANH,
                   song_song: int = SONG_SONG_ANH, khoa: str = "bia-lo", log: Callable[[str], None] = print,
                   dem: Optional[Dict[str, int]] = None, ho_so: Optional[Dict[str, Any]] = None
                   ) -> List[Dict[str, Any]]:
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
        ln = loi_nhac_anh(y, kc, nen, ho_so=ho_so)
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


def _lap_lo(m):
    """Mặt nạ bool `m` (khung hộp của một thành phần) đã LẤP lỗ — mắt/miệng tối trong đầu không làm hụt độ lấp."""
    import numpy as np  # noqa: PLC0415
    h, w = m.shape
    ngoai = np.zeros_like(m)
    ngan = [(y, x) for y in range(h) for x in (0, w - 1)] + [(y, x) for x in range(w) for y in (0, h - 1)]
    ngan = [(y, x) for y, x in ngan if not m[y, x]]
    for y, x in ngan:
        ngoai[y, x] = True
    while ngan:
        y, x = ngan.pop()
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < h and 0 <= xx < w and not m[yy, xx] and not ngoai[yy, xx]:
                ngoai[yy, xx] = True
                ngan.append((yy, xx))
    return ~ngoai


def tim_dau(anh, mau: Optional[Sequence[int]] = None, *, noi: bool = False) -> List[List[float]]:
    """Các hộp ĐẦU nhân vật (px trên `anh`, lớn trước) — nhân vật kênh là hình tròn TRẮNG viền ĐEN: thành phần liền (4
    hướng, lưới 320×180) trắng ít sắc, gần tròn (rộng/cao 0,75–1,35, lấp ≥ 60% hộp), ≥ 0,4% khung, ≥ 20% vành ngoài là
    nét đen. Đo 14/10 trên 7 nền thật TL4: bắt đúng đầu, không bắt cửa sáng/chữ trắng (vành không đen). Lấy MỌI đầu, không
    chỉ đầu lớn nhất: lô thật 0002 — bóng nhân vật trong GƯƠNG (chính là manh mối) bị hộp chữ che nửa mặt. [] = không
    thấy.

    `mau` (rgb, `mau_dau_nv`): đầu CÓ MÀU (TL3: cam trong vòng đen) — điểm cùng sắc, gần độ đậm/sáng của màu đầu (nền
    phòng ấm nhạt hơn hẳn). `noi` (bìa chữ trần TL2/TL3, 14/10): đầu trắng ÁM ẤM (ánh nắng), viền mảnh mờ đi ở lưới nhỏ —
    trắng nới (≥190, lệch sắc ≤45), độ lấp tính sau khi LẤP lỗ mắt/miệng (0,6–0,95: hình tròn ~0,79, ô chữ nhật bị
    loại), vành "tối" = tối hơn 70% độ sáng đầu. Mặc định giữ y bộ dò đã đo trên nền TL4."""
    import colorsys  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    from .do_bia import _gian  # noqa: PLC0415
    W, H = anh.size
    w, h = 320, 180
    nho = anh.convert("RGB").resize((w, h), Image.BOX)
    a = np.asarray(nho).astype(np.int16)
    mn, mx = a.min(axis=2), a.max(axis=2)
    trang, den = (mn >= 205) & (mx - mn <= 26), mx <= 120  # nét đen ~1 ô ở lưới nhỏ bị trộn với nền → ≤ 120
    if noi:
        trang = (mn >= 190) & (mx - mn <= 45)
    if mau is not None:
        hsv = np.asarray(nho.convert("HSV")).astype(np.int16)
        h0, s0, v0 = (int(round(255 * x)) for x in colorsys.rgb_to_hsv(*[float(v) / 255.0 for v in list(mau)[:3]]))
        dh = np.abs(hsv[..., 0] - h0)
        trang = ((np.minimum(dh, 256 - dh) <= (12 if noi else 14)) & (hsv[..., 1] >= max(90, s0 - 60 if noi else 90))
                 & (hsv[..., 2] >= max(110, v0 - 80 if noi else 110)))
    sang = a.mean(axis=2)
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
        if len(px) < 0.004 * w * h or not (0.75 <= bw / float(bh) <= 1.35):
            continue
        if noi:
            lap = float(_lap_lo(nhan[b0:b1, a0:a1] == k).sum()) / float(bw * bh)
            if not 0.6 <= lap <= 0.95:
                continue
        elif len(px) < 0.6 * bw * bh:
            continue
        c0, c1, d0, d1 = max(0, b0 - 3), min(h, b1 + 3), max(0, a0 - 3), min(w, a1 + 3)
        m = nhan[c0:c1, d0:d1] == k
        vanh = _gian(m, 2) & ~m
        toi = den[c0:c1, d0:d1]
        if noi:
            toi = toi | (sang[c0:c1, d0:d1] <= 0.7 * float(np.median(sang[ys, xs])))
        if vanh.any() and float(toi[vanh].mean()) >= 0.2:
            ra.append((len(px), [a0 * W / w, b0 * H / h, a1 * W / w, b1 * H / h]))
    return [b for _n, b in sorted(ra, key=lambda x: -x[0])]


def _phan_giao(hop: Sequence[float], cac: Sequence[Sequence[float]]) -> float:
    """Phần diện tích `hop` nằm dưới các hộp `cac` (cộng dồn, ≤ 1)."""
    dt = max(1.0, (hop[2] - hop[0]) * (hop[3] - hop[1]))
    return min(1.0, sum(max(0.0, min(hop[2], b[2]) - max(hop[0], b[0])) * max(0.0, min(hop[3], b[3]) - max(hop[1], b[1]))
                        for b in cac) / dt)


def dung_bia(uv: Dict[str, Any], tang: Sequence[Dict[str, Any]], *, goc: str = "", ngon_ngu: str = "ja",
             ho_so: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Vẽ chữ lên nền sạch `uv["nen"]` → `uv["tep"]` (jpg 1280×720 + báo cáo đo) và LỌC CỨNG: hộp chữ không được đè
    đầu nhân vật (> `CHE_DAU_TOI_DA`) hay chủ thể/manh mối (> `CHE_MANH_MOI_TOI_DA`) — thử lần lượt `CACH_BO_CUC` (co,
    dời cột chữ; đầu nhân vật là vùng NÉ của bộ vẽ), hết cách thì loại; rồi cổng đọc được `do_bia.cham_tep` phải
    ĐẠT. `uv["loai"]` = lý do loại ("" = qua). Kênh kiểu chữ TRẦN (`ho_so`) → `_dung_bia_tran`."""
    if (ho_so or {}).get("kieu") == "tran":
        return _dung_bia_tran(uv, tang, ho_so or {}, goc=goc, ngon_ngu=ngon_ngu)
    from PIL import Image  # noqa: PLC0415
    from . import chon_bia, do_bia  # noqa: PLC0415
    anh = Image.open(uv["nen"]).convert("RGB")
    W, H = anh.size
    dau = tim_dau(anh, (ho_so or {}).get("mau_dau"))
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


def ve_dai_len(anh, tang: Sequence[Dict[str, Any]], dong: Sequence[Dict[str, Any]]):
    """Nền + DẢI CỌ (hình bình hành nghiêng, mép phải răng cưa nhẹ) sau các dòng có `dai` (màu hex) — khớp dòng báo cáo
    bộ vẽ theo chữ. Trả ảnh mới (None khi không dòng nào có dải). Dải phủ hộp dòng, lấn trái/phải theo cỡ chữ."""
    from PIL import Image, ImageDraw  # noqa: PLC0415
    can = {btk.chu_cua_tang(t)[:24]: t["dai"] for t in tang if t.get("dai")}
    if not can:
        return None
    lop = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    v = ImageDraw.Draw(lop)
    co = False
    for d in dong:
        mau = can.get(str(d.get("ten") or ""))
        if not mau or not d.get("hop"):
            continue
        x0, y0, x1, y1 = [float(x) for x in d["hop"]]
        h = y1 - y0
        x0, x1, y0, y1 = x0 - 0.10 * h, x1 + 0.25 * h, y0 + 0.08 * h, y1 - 0.02 * h
        lech = 0.12 * h  # nghiêng như vết cọ
        rang = [(x1 + lech * (1 - k / 6.0) + (0.06 * h if k % 2 else -0.04 * h), y0 + (y1 - y0) * k / 6.0)
                for k in range(7)]
        v.polygon([(x0 + lech, y0)] + rang + [(x0, y1)], fill=btk._mau_rgb(mau) + (238,))  # noqa: SLF001
        co = True
    if not co:
        return None
    return Image.alpha_composite(anh.convert("RGBA"), lop).convert("RGB")


def cach_bo_cuc_tran(bo: str, mt: Optional[Dict[str, Any]] = None) -> Tuple[Tuple[Any, ...], ...]:
    """Các cách đặt chữ trần thử lần lượt. Có mục tiêu bìa thắng (kiểu cột): cột rộng như khối chữ bìa thắng (kẹp
    0,52–0,66) trước, rồi hẹp dần — chữ né đầu nhân vật bằng cách THU CỘT, không thu cả bìa trước."""
    if bo == "dai" or not mt or not mt.get("rong_khoi"):
        return CACH_BO_CUC_TRAN["dai" if bo == "dai" else "cot"]
    # 19/10/2026: bề cột = bề khối chữ ĐO trên bìa thắng (TL2: ~2/3 khung) — chỉ kẹp chống số đo lạc
    r0 = max(0.45, min(0.75, float(mt["rong_khoi"])))
    rong = sorted({round(r0, 2)} | {r for r, _e, _t in CACH_BO_CUC_TRAN["cot"] if r < r0}, reverse=True)
    return tuple((r, 1.0, 0) for r in rong) + ((0.48, 0.9, 0), (0.44, 0.85, 0))


def _dung_bia_tran(uv: Dict[str, Any], tang: Sequence[Dict[str, Any]], ho_so: Dict[str, Any], *, goc: str = "",
                   ngon_ngu: str = "ja") -> Dict[str, Any]:
    """`dung_bia` cho kênh kiểu chữ TRẦN: chữ vẽ bằng bộ vẽ chữ trần của khuôn (`btk.ve_chu_len_anh` — màu khuôn, viền
    đen dày ưu tiên `ho_so.uu_tien`, phông rất đậm, KHÔNG khung/dải nền) theo `cach_bo_cuc_tran` (cột chữ hẹp dần /
    thu cỡ) tới khi hộp các dòng không đè đầu nhân vật (> `CHE_DAU_TOI_DA`) và không che quá `CHE_MANH_MOI_TRAN` chủ
    thể; hết cách thì loại; rồi cổng đọc được `do_bia.cham_tep`.

    18/10/2026 — có MỤC TIÊU bố cục bìa thắng (`ho_so.muc_tieu`): bộ vẽ nhắm diện tích chữ của bìa thắng
    (`dien_tich_muc`), cột chữ là MỘT khối giữa cột (`doc_khoi`); mỗi cách đặt còn phải qua CỔNG BỐ CỤC
    (`kiem_bo_cuc`: diện tích chữ, dòng chính, khối không hở) — không cách nào qua thì LOẠI (không giao tấm chữ bé)."""
    from PIL import Image  # noqa: PLC0415
    from . import chon_bia, do_bia  # noqa: PLC0415
    anh = Image.open(uv["nen"]).convert("RGB")
    W, H = anh.size
    dau = tim_dau(anh, ho_so.get("mau_dau"), noi=True)
    mat = [[d[0], d[1] + DINH_DAU_TRAN * (d[3] - d[1]), d[2], d[3]] for d in dau]  # bỏ đỉnh đầu: chỉ giữ vùng mặt
    uv.update(dau=[[round(v) for v in d] for d in dau], loai="")
    try:
        chu_the = do_bia.ban_do_chu_the(do_bia.mang_nen(anh)[0])
    except Exception:  # noqa: BLE001 — không đo được chủ thể: chỉ né đầu
        chu_the = None
    png = uv["nen"][:-len("-nen.png")] + ".png"
    bo = ho_so.get("bo_cuc") if ho_so.get("bo_cuc") in ("trai", "phai", "dai") else "dai"
    mt = ho_so.get("muc_tieu") or {}
    dt = float(mt.get("dt_dong_pct") or 0)
    dt_muc = (0.92 * dt, 1.15 * dt) if dt else None
    khoi = 0.5 if any(t.get("khoi") for t in tang) else None
    che_dau = che_mm = 1.0
    ly_bc: List[str] = []
    do_bc: Dict[str, Any] = {}
    cach: Tuple[Any, ...] = ("dai", 1.0, 0)
    for cach in cach_bo_cuc_tran(bo, mt):
        rong, ep, tran_tren = cach
        khung, t_ve = None, [dict(t) for t in tang]
        if bo != "dai":
            khung = (0.0, 0.0, rong, 1.0) if bo == "trai" else (1.0 - rong, 0.0, 1.0, 1.0)
        elif rong == "duoi":
            t_ve = [dict(t, vi_tri="duoi") for t in t_ve]
        elif tran_tren:
            t_ve = [dict(t, co_toi_da_pct=min(float(t.get("co_toi_da_pct") or 99), tran_tren))
                    if t.get("vi_tri") == "tren" else t for t in t_ve]
        bc: Dict[str, Any] = {}

        def ve(nen_ve, dich_ve: str) -> bool:
            # Phông của chính bộ vẽ chữ trần (gothic rất đậm như bìa thắng); phông bo tròn Black của kiểu hộp làm tắc
            # nét chữ Hán nhiều nét (「標」) khi viền đen dày — lô thật TL3 14/10.
            return btk.ve_chu_len_anh(uv["nen"], dich_ve, t_ve, goc=goc, ngon_ngu=ngon_ngu, anh_nen=nen_ve,
                                      bao_cao=bc, khung_chu=khung, cho_khung=False, ep_co=ep,
                                      uu_tien_kieu=ho_so.get("uu_tien") or UU_TIEN_VIEN_DEN, nhan_toi_da=2,
                                      dien_tich_muc=dt_muc, doc_khoi=khoi)
        # 19/10/2026 — DẢI nền sau dòng từ khoá (đo trên bìa thắng): bố cục chữ không phụ thuộc nền → lượt NHÁP (tệp
        # riêng) lấy hộp các dòng, vẽ dải đúng hộp lên nền, rồi vẽ chữ trên nền có dải (đo độ đọc được trên nền ấy).
        co_dai = any(t.get("dai") for t in t_ve)
        nhap = png[:-4] + ".nhap.png"
        if not ve(anh, nhap if co_dai else png):
            uv["loai"] = "không vẽ được chữ (thiếu phông?)"
            return uv
        if co_dai:
            for t in (nhap, nhap[:-4] + ".do-bia.json"):
                try:
                    os.remove(t)
                except OSError:
                    pass
            dai = ve_dai_len(anh, t_ve, bc.get("dong") or [])
            if not ve(dai if dai is not None else anh, png):
                uv["loai"] = "không vẽ được chữ (thiếu phông?)"
                return uv
        hop = [d["hop"] for d in bc.get("dong") or [] if d.get("hop")]
        che_dau = max([_phan_giao(m, hop) for m in mat] or [0.0])
        che_mm = do_bia.phan_chu_the_bi_che(chu_the, hop, W, H)
        do_bc = do_hop_dong(hop, W=W, H=H)
        ly_bc = kiem_bo_cuc(do_bc, mt, cot=bo != "dai")
        if che_dau <= CHE_DAU_TOI_DA and che_mm <= CHE_MANH_MOI_TRAN and not ly_bc:
            break
    uv.update(bo_cuc=list(cach), che_dau=round(che_dau, 3), che_manh_moi=round(che_mm, 3), tep=png[:-4] + ".jpg",
              kieu_chu="tran", chu_tang=t_ve, bo_cuc_do={k: v for k, v in do_bc.items() if k != "i_chinh"})
    chon_bia._xuat_jpg(png, uv["tep"])  # noqa: SLF001
    os.remove(png)
    if che_dau > CHE_DAU_TOI_DA:
        uv["loai"] = "chữ đè đầu nhân vật ({0:.0%})".format(che_dau)
    elif che_mm > CHE_MANH_MOI_TRAN:
        uv["loai"] = "chữ che chủ thể/manh mối ({0:.0%})".format(che_mm)
    elif ly_bc:
        uv["loai"] = "bố cục chữ kém bìa thắng: " + "; ".join(ly_bc)
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
    """JSON vòng 1 → {số tấm (1..n): {diem, tong 0–100, loi, yeu, ly_do}}; tấm thiếu mục điểm thì bỏ. `tong` = tổng có
    trọng số `TRONG_SO` trừ `YEU_TRU` cho mỗi điểm yếu giám khảo thấy (nền nhạt, chữ nhỏ, manh mối yếu). Câu trả lời
    kiểu cũ (không có `bam_nhu_thang`) vẫn đọc được: trọng số chia lại trên các mục có."""
    ra: Dict[int, Dict[str, Any]] = {}
    for x in (du.get("ung_vien") if isinstance(du, dict) else du) or []:
        if not isinstance(x, dict):
            continue
        try:
            so = int(x.get("so"))
        except (TypeError, ValueError):
            continue
        diem = {k: _so(x.get(k)) for k in TRONG_SO}
        thieu = [k for k, v in diem.items() if v is None]
        if not 1 <= so <= n or [k for k in thieu if k != "bam_nhu_thang"]:
            continue
        diem = {k: v for k, v in diem.items() if v is not None}
        ts = sum(TRONG_SO[k] for k in diem)

        def _ds(v: Any) -> List[str]:
            return [str(e)[:60] for e in (v if isinstance(v, list) else [v])
                    if e and str(e).strip().lower() not in ("none", "no", "n/a", "-", "[]", "false")]
        loi, yeu = _ds(x.get("loi")), [e.lower() for e in _ds(x.get("yeu"))]
        tru = sum(YEU_TRU.get(e, 0.0) for e in set(yeu))
        ra[so] = {"diem": diem, "tong": round(max(0.0, 10 * sum(TRONG_SO[k] * v for k, v in diem.items()) / ts - tru), 1),
                  "loi": loi, "yeu": yeu, "ly_do": str(x.get("ly_do") or "")[:240]}
        # 19/10/2026 — sàn nhân vật: giám khảo so nhân vật chính với ảnh nhân vật kênh; người phụ chỉ là bóng mờ
        for k in ("nv", "nguoi_khac"):
            v = str(x.get(k) or "").strip().lower()
            if v:
                ra[so][k] = v[:20]
    return ra


def lech_nhan_vat(u: Dict[str, Any]) -> str:
    """Lý do SÀN NHÂN VẬT (giám khảo) — '' = đạt / giám khảo không nói: nhân vật chính khác nhân vật kênh hoặc vắng,
    người phụ có mặt chi tiết / ảnh chụp."""
    nv, khac = str(u.get("nv") or ""), str(u.get("nguoi_khac") or "")
    ly = []
    if nv in ("different", "none"):
        ly.append("nhân vật chính " + ("không phải nhân vật kênh" if nv == "different" else "vắng mặt"))
    if khac in ("faces", "photo"):
        ly.append("người phụ " + ("có mặt chi tiết" if khac == "faces" else "là ảnh chụp") + " (bìa thắng: bóng mờ)")
    return "; ".join(ly)


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


def sac_do(tep: Any) -> Tuple[float, float]:
    """(độ bão hoà trung bình 0..1, độ tương phản = độ lệch chuẩn độ sáng 0..1) của ảnh thu 160×90."""
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    im = tep if hasattr(tep, "size") else Image.open(tep)
    nho = im.convert("RGB").resize((160, 90), Image.BOX)
    hsv = np.asarray(nho.convert("HSV")).astype(np.float64) / 255.0
    sang = np.asarray(nho.convert("L")).astype(np.float64) / 255.0
    return float(hsv[..., 1].mean()), float(sang.std())


def soi_yeu(tep: str, thang: Sequence[str]) -> List[str]:
    """Điểm yếu đo bằng MÁY so bìa thắng CỦA kênh: nền nhạt (bão hoà hoặc tương phản < `NHAT_BAO_HOA` /
    `NHAT_TUONG_PHAN` × trung vị bìa thắng) → ["pale background"]. Không đo được → []."""
    try:
        do = [sac_do(t) for t in thang if t and os.path.isfile(t)]
        if not do:
            return []
        bh = sorted(d[0] for d in do)[len(do) // 2]
        tp = sorted(d[1] for d in do)[len(do) // 2]
        b, t = sac_do(tep)
    except (OSError, ValueError):
        return []
    return ["pale background"] if (b < NHAT_BAO_HOA * bh or t < NHAT_TUONG_PHAN * tp) else []


# ── 4b) Sàn chất lượng (19/10/2026) ──────────────────────────────────────────


def do_mau(tep: Any) -> Dict[str, float]:
    """Số đo màu của ảnh thu 160×90: `bao_hoa` (bão hoà TB 0..1), `tuong_phan` (độ lệch chuẩn độ sáng), `dai_sang`
    (phân vị 95 − phân vị 5 độ sáng). Bìa nhạt đơn sắc (TL4-0005: 0,31 / 0,19 / 0,62) thấp cả ba."""
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    im = tep if hasattr(tep, "size") else Image.open(tep)
    nho = im.convert("RGB").resize((160, 90), Image.BOX)
    bh = np.asarray(nho.convert("HSV")).astype(np.float64)[..., 1] / 255.0
    sang = np.asarray(nho.convert("L")).astype(np.float64) / 255.0
    return {"bao_hoa": round(float(bh.mean()), 4), "tuong_phan": round(float(sang.std()), 4),
            "dai_sang": round(float(np.percentile(sang, 95) - np.percentile(sang, 5)), 4)}


def san_mau(thang: Sequence[str]) -> Dict[str, Any]:
    """SÀN MÀU của kênh trên các bìa thắng (≥ 2 bìa; ít hơn → {}): phân vị `SAN_PHAN_VI` từng số đo `do_mau` + `toi_thieu`
    (nhỏ nhất của bìa thắng từng số đo — ngưỡng NHẠT HẲN)."""
    import numpy as np  # noqa: PLC0415
    do = []
    for t in thang or ():
        try:
            if t and os.path.isfile(t):
                do.append(do_mau(t))
        except (OSError, ValueError):
            continue
    if len(do) < 2:
        return {}
    ra: Dict[str, Any] = {k: round(float(np.percentile([d[k] for d in do], SAN_PHAN_VI)), 4) for k in _TEN_DO_MAU}
    ra["toi_thieu"] = {k: round(min(d[k] for d in do), 4) for k in _TEN_DO_MAU}
    return ra


def kiem_mau(tep: Any, san: Dict[str, Any]) -> List[str]:
    """Lý do bìa dưới SÀN MÀU ([] = đạt / không có sàn). 19/10/2026 (chủ: sàn lệch không được chặn sản xuất): ĐẠT khi
    ≥ 2/3 số đo ≥ phân vị `SAN_PHAN_VI` bìa thắng."""
    if not san:
        return []
    try:
        d = do_mau(tep)
    except (OSError, ValueError):
        return ["không đo được màu"]
    duoi = ["{0} {1:.2f} < {2:.2f}".format(_TEN_DO_MAU[k], d[k], float(san[k])) for k in _TEN_DO_MAU
            if k in san and d[k] < float(san[k])]
    return duoi if len(duoi) >= 2 else []


def nhat_han(tep: Any, san: Dict[str, Any]) -> List[str]:
    """Lý do bìa NHẠT HẲN — cả 3 số đo dưới bìa thắng nhạt nhất (TL4-0005: 0,31/0,19/0,62 < 0,31/0,22/0,63) → luôn
    loại, kể cả khi lô phải chọn tấm dưới sàn. [] = không."""
    mn = (san or {}).get("toi_thieu") or {}
    if len(mn) < 3:
        return []
    try:
        d = do_mau(tep)
    except (OSError, ValueError):
        return []
    ly = ["{0} {1:.2f} < {2:.2f}".format(_TEN_DO_MAU[k], d[k], float(mn[k])) for k in _TEN_DO_MAU if d[k] < float(mn[k])]
    return ly if len(ly) == 3 else []


def dau_dung_duoc(nv: str, thang: Sequence[str], mau_dau: Any = None, *, noi: bool = False) -> bool:
    """Bộ dò đầu (`tim_dau`) dùng làm SÀN NHÂN VẬT cho kênh khi nó bắt được đầu trên nv1.png VÀ trên ≥
    `TI_LE_DAU_BAT` bìa thắng — nhân vật người có tóc (TL5, TL6-K2) không bắt được thì chỉ còn giám khảo xét."""
    from PIL import Image  # noqa: PLC0415
    try:
        if not nv or not os.path.isfile(nv) or not tim_dau(Image.open(nv).convert("RGB"), mau_dau, noi=noi):
            return False
        cac = [t for t in thang if t and os.path.isfile(t)]
        if len(cac) < 2:
            return False
        co = sum(1 for t in cac if tim_dau(Image.open(t).convert("RGB"), mau_dau, noi=noi))
    except (OSError, ValueError):
        return False
    return co >= TI_LE_DAU_BAT * len(cac)


def san_bam(thu_muc: str) -> Tuple[float, str]:
    """(sàn điểm `bam_nhu_thang`, nguồn): `<thư mục bìa thắng>/san-bam.json` do kiểm vàng hiệu chỉnh, không có →
    `SAN_BAM_MAC_DINH`."""
    du = _doc_json(os.path.join(thu_muc, TEP_SAN_BAM)) if thu_muc else None
    try:
        return max(SAN_BAM_KEP[0], min(SAN_BAM_KEP[1], float((du or {})["san"]))), "hieu-chinh"
    except (KeyError, TypeError, ValueError):
        return SAN_BAM_MAC_DINH, "mac-dinh"


def hieu_chinh_san_bam(thu_muc: str, diem_thang: float, *, kenh: str = "") -> float:
    """Ghi một điểm giám khảo cho bìa thắng GIẤU (kiểm vàng) → sàn = trung vị các lần − `SAN_BAM_DUOI`, kẹp
    `SAN_BAM_KEP`. Trả sàn mới."""
    du = _doc_json(os.path.join(thu_muc, TEP_SAN_BAM)) or {}
    ls = [float(x) for x in (du.get("diem_thang") or []) if isinstance(x, (int, float))][-9:] + [float(diem_thang)]
    import statistics  # noqa: PLC0415
    tv = float(statistics.median(ls))
    san = max(SAN_BAM_KEP[0], min(SAN_BAM_KEP[1], tv - SAN_BAM_DUOI))
    _ghi_json(os.path.join(thu_muc, TEP_SAN_BAM), {"san": san, "diem_thang": ls, "kenh": kenh,
                                                   "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                   "cach": "trung vị điểm bìa thắng giấu − {0}".format(SAN_BAM_DUOI)})
    return san


def kiem_san(u: Dict[str, Any], san: Dict[str, Any]) -> List[str]:
    """Lý do tấm đã chấm dưới SÀN ĐIỂM (`bam_nhu_thang` < sàn, hoặc giám khảo không chấm mục ấy) — [] = đạt."""
    b = (u.get("diem") or {}).get("bam_nhu_thang")
    if b is None:
        return ["giám khảo không chấm «bấm như bìa thắng»"]
    ly = [u["mau_duoi"]] if u.get("mau_duoi") else []
    s, nguon = san_cua(u, san)
    if float(b) < s:
        ly.append("bấm như bìa thắng {0:.0f} < sàn {1:.0f} ({2})".format(float(b), s, nguon))
    return ly


def san_cua(u: Dict[str, Any], san: Dict[str, Any]) -> Tuple[float, str]:
    """(sàn `bam_nhu_thang` của tấm, nguồn): điểm bìa thắng GIẤU trong cùng nhóm chấm − `SAN_BAM_DUOI` (kẹp
    `SAN_BAM_KEP`) khi có; không thì sàn hiệu chỉnh của kênh / mặc định."""
    if isinstance(u.get("bam_giau"), (int, float)):
        return (max(SAN_BAM_KEP[0], min(SAN_BAM_KEP[1], float(u["bam_giau"]) - SAN_BAM_DUOI)),
                "bìa thắng giấu cùng nhóm {0:.0f}".format(float(u["bam_giau"])))
    return float(san.get("bam") or SAN_BAM_MAC_DINH), str(san.get("nguon_bam") or "mac-dinh")


def to_dien_thoai(thang: Sequence[str], ds: Sequence[Dict[str, Any]], dich: str, *, cot: int = 3) -> str:
    """Tờ CỠ ĐIỆN THOẠI cho giám khảo: hàng đầu là bìa thắng (nhãn W1, W2…), dưới là ứng viên đánh số 1..n — mỗi ô
    `O_DIEN_THOAI` (cỡ một bìa trong bảng tin YouTube trên điện thoại)."""
    from PIL import Image, ImageDraw, ImageOps  # noqa: PLC0415
    o, le = O_DIEN_THOAI, 10
    thang = [t for t in thang if t and os.path.isfile(t)][:cot]
    hang_uv = max(1, (len(ds) + cot - 1) // cot)
    hang = (1 if thang else 0) + hang_uv
    to = Image.new("RGB", (cot * o[0] + (cot + 1) * le, hang * (o[1] + le) + le + (8 if thang else 0)), (18, 18, 20))
    ve, f = ImageDraw.Draw(to), _phong(o[1] * 0.15)
    r = int(o[1] * 0.24)

    def o_so(x: int, y: int, nhan: str, mau) -> None:
        ve.rounded_rectangle((x + 4, y + 4, x + 4 + int(r * (1.5 if len(nhan) > 1 else 1)), y + 4 + r), radius=r // 4,
                             fill=(20, 20, 20))
        ve.text((x + 4 + int(r * (1.5 if len(nhan) > 1 else 1)) / 2, y + 4 + r / 2), nhan, font=f, fill=mau,
                anchor="mm")
    for i, t in enumerate(thang):
        x, y = le + i * (o[0] + le), le
        with Image.open(t) as im:
            to.paste(ImageOps.fit(im.convert("RGB"), o, method=Image.LANCZOS), (x, y))
        o_so(x, y, "W{0}".format(i + 1), (120, 230, 120))
    y0 = le + ((o[1] + le + 8) if thang else 0)
    for i, u in enumerate(ds):
        x, y = le + (i % cot) * (o[0] + le), y0 + (i // cot) * (o[1] + le)
        with Image.open(u["tep"]) as im:
            to.paste(ImageOps.fit(im.convert("RGB"), o, method=Image.LANCZOS), (x, y))
        o_so(x, y, str(i + 1), (255, 230, 60))
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    to.save(dich, format="JPEG", quality=88)
    return dich


def cham(goi: Callable[..., str], ds: List[Dict[str, Any]], *, mau: Sequence[str], tieu_de: str, chu_bia: str,
         mo_dau: str = "", thu_muc: str = "", khoa: str = "bia-lo", log: Callable[[str], None] = print,
         dem: Optional[Dict[str, int]] = None, ho_so: Optional[Dict[str, Any]] = None,
         giau: str = "") -> List[Dict[str, Any]]:
    """Chấm các ứng viên QUA lọc cứng → danh sách xếp hạng (tốt nhất trước; tấm loại/chưa chấm ở cuối).

    Vòng 1: nhóm ≤ `NHOM_CHAM` (xen kẽ ý để mỗi nhóm có nhiều ý), mỗi nhóm một lượt: bìa thắng + từng tấm + TỜ CỠ ĐIỆN
    THOẠI (bìa thắng hàng đầu, ứng viên dưới — `to_dien_thoai`); mục `bam_nhu_thang` ("bấm nhiều như bìa thắng
    không"), điểm yếu (`yeu`) trừ điểm; `loi` thấy được → loại. Điểm yếu đo MÁY (`soi_yeu`: nền nhạt so bìa thắng
    của kênh) trừ như nhau. Đọc mù nền sạch ≤ `TRAN_DOC_CHU` tấm điểm cao nhất (`soat_bia.doc_anh`): có chữ/số → loại.
    Vòng 2: ≤ `SO_VONG_2` tấm trên MỘT tờ cỡ điện thoại có hàng bìa thắng → thứ hạng. Trần lượt chấm `TRAN_GOI_CHAM`.
    `mau` = bìa thắng thật CỦA kênh; `ho_so.bia_so` (≤ `SO_BIA_SO` bìa đầu bảng thư mục bìa thắng) có thì dùng cho
    tờ điện thoại; `ho_so` (`ho_so_kieu`) đổi lời tả kiểu chữ/nhân vật theo kênh.

    19/10/2026 — `giau` (bìa thắng THẬT không nằm trong mẫu/hàng so): chen vào MỌI nhóm vòng 1 như một ứng viên — điểm
    `bam_nhu_thang` giám khảo cho nó trong CÙNG nhóm (`u["bam_giau"]`) là thước sàn của các tấm nhóm ấy (`kiem_san`).
    Kiểm vàng thật 19/10: cùng tấm TL1 được 5 ở lô, 8 ở lượt đối chiếu — điểm giám khảo chỉ so được trong một lượt."""
    from . import soat_bia  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    dem = dem if dem is not None else {}
    mau_url = [_url_anh(m) for m in list(mau)[:2]]
    thang = [t for t in ((ho_so or {}).get("bia_so") or list(mau)) if t and os.path.isfile(t)][:SO_BIA_SO]
    lk = loi_theo_kieu(ho_so)
    tt = {"tieu_de": tieu_de, "chu_bia": chu_bia, "mo_dau": " ".join(str(mo_dau or "").split())[:700] or "(none)",
          "bang_chung": lk["bang_chung"]}
    # 19/10/2026 — ảnh nhân vật kênh (nv1.png) ngay sau bìa thắng: giám khảo xét SÀN NHÂN VẬT (`lech_nhan_vat`).
    nv = str((ho_so or {}).get("nv") or "")
    nv_url = [_url_anh(nv, cat=False)] if nv and os.path.isfile(nv) else []
    tt1 = dict(tt, nv_cau=NV_CAU_CHAM.format(so=len(mau_url) + 1) if nv_url else "",
               nv_ref="the character reference image" if nv_url else "the winners",
               **{k: lk[k] for k in ("o_chu", "chu_ten", "ngoai_chu", "phong_cach_ta")})
    qua = sorted([u for u in ds if not u.get("loai")], key=lambda u: (u["bien"], u["y"]))
    nhom = [qua[i:i + NHOM_CHAM] for i in range(0, len(qua), NHOM_CHAM)][:max(1, TRAN_GOI_CHAM - 1)]
    khoa_dem = threading.Lock()
    tm = thu_muc or tempfile.gettempdir()

    def goi_dem(loi_nhac: str, **kw) -> str:
        with khoa_dem:
            dem["llm"] = dem.get("llm", 0) + 1
        return goi(loi_nhac, **kw)

    co_giau = bool(giau) and os.path.isfile(giau)

    def vong_1(i_g) -> None:
        i, g0 = i_g
        g = list(g0)
        vi_giau = min(2, len(g)) if co_giau else -1  # bìa thắng giấu đứng GIỮA nhóm (không đầu/cuối)
        if co_giau:
            g.insert(vi_giau, {"ma": "giau", "tep": giau, "nen": giau})
        try:
            to = to_dien_thoai(thang, g, os.path.join(tm, "_vong-1-{0}.jpg".format(i + 1)))
            tho = goi_dem(LOI_NHAC_CHAM_1.format(k=len(mau_url), n=len(g), **tt1), khoa="{0}:cham1:{1}".format(
                khoa, _bam(*[u["ma"] for u in g], "dt", PHIEN_BAN_CHAM, os.path.basename(giau or ""))),
                toi_da_token=7000, mo_hinh=MO_HINH_CHAM,  # 7 tấm × lý do tiếng Việt: 3000 bị cắt
                anh=mau_url + nv_url + [_url_anh(u["tep"]) for u in g] + [_url_anh(to, 1100, cat=False)])
            kq = doc_cham_1(_json(tho), len(g))
        except Exception as loi:  # noqa: BLE001 — nhóm hỏng: các tấm ấy chưa có điểm
            log("  (bìa lô: chấm nhóm {0} hỏng: {1})".format(i + 1, str(loi)[:160]))
            return
        bam_giau = ((kq.get(vi_giau + 1) or {}).get("diem") or {}).get("bam_nhu_thang") if co_giau else None
        for so, k in kq.items():
            if so - 1 == vi_giau:
                continue
            u = g[so - 1]
            if bam_giau is not None:
                u["bam_giau"] = bam_giau
            u.update(k)
            may = [e for e in soi_yeu(u["tep"], thang) if e not in u["yeu"]]
            if may:
                u["yeu_may"] = may
                u["tong"] = round(max(0.0, u["tong"] - sum(YEU_TRU.get(e, 0.0) for e in may)), 1)
            if k["loi"]:
                u["loai"] = "giám khảo thấy lỗi: " + ", ".join(k["loi"])
            elif lech_nhan_vat(u):
                u["loai"] = "nhân vật lệch kênh: " + lech_nhan_vat(u)
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
        to = to_dien_thoai(thang, top, os.path.join(tm, "_vong-2.jpg"))
        try:
            tho = goi_dem(LOI_NHAC_CHAM_2.format(n=len(top), **tt), khoa="{0}:cham2:{1}".format(
                khoa, _bam(*[u["ma"] for u in top], "dt")), toi_da_token=2000, mo_hinh=MO_HINH_CHAM,
                anh=[_url_anh(to, 1100, cat=False)])
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


def mau_cua_kenh(goc: str, kenh: str, mau: Sequence[str] = (), ho_so: Optional[Dict[str, Any]] = None) -> List[str]:
    """2–3 bìa thắng THẬT làm mẫu (sáng/sạch nhất — `btk.chon_anh_mau_phong_cach`): `mau` (tệp/thư mục) > `tep_mau` của
    khuôn kênh > `kenh.yaml: bia_lo_mau` (thư mục). Kênh kiểu chữ TRẦN: bìa khuôn + bìa thắng cùng kiểu của chính kênh
    (`ho_so_kieu` → `bia_mau`, đúng thứ tự — bìa khuôn đầu tiên), không lọc theo độ sáng (nền tím TL3 là kiểu thắng)."""
    cac = list(mau)
    hs = ho_so if ho_so is not None else (ho_so_kieu(goc, kenh, log=lambda s: None, mau=cac) if not cac or any(
        os.path.isdir(c) for c in cac) else {})
    # Chữ trần: bìa khuôn + bìa cùng kiểu; có thư mục bìa thắng chủ chọn (16/10/2026) thì các bìa đầu bảng của nó —
    # 19/10/2026: cả kiểu hộp (TL4: lô lấy ảnh tham chiếu của khuôn cũ, không phải bìa thắng thật).
    if hs.get("bia_mau") and (hs.get("kieu") == "tran" or hs.get("thu_muc_mau")) and (
            not cac or hs.get("thu_muc_mau")):
        return [t for t in hs["bia_mau"] if os.path.isfile(t)]
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
    if list(mau) and (ho_so or {}).get("kieu") == "tran":  # chữ trần: giữ thứ tự người gọi (bìa khuôn đầu tiên)
        return [t for t in tep if os.path.isfile(t)][:3]
    return btk.chon_anh_mau_phong_cach([t for t in tep if os.path.isfile(t)], toi_da=3)


def chay(goc: str, kenh: str, *, thu_muc_luot: str, ra: str, chu: str = "", so_y: int = SO_Y_MAC_DINH,
         moi_y: int = MOI_Y_MAC_DINH, goi: Callable[..., str], ve: Callable[..., List[str]],
         mau: Sequence[str] = (), log: Callable[[str], None] = print, ngon_ngu: str = "ja", khoa: str = "",
         dan: str = "", giau: Optional[str] = None) -> Dict[str, Any]:
    """Cả lô cho MỘT lượt → `<ra>/ung-vien/*.jpg`, `<ra>/xep-hang.json`, `<ra>/to-lien.jpg`, `<ra>/top-N.jpg`. Trả bản
    xếp hạng (`top` = ≤ `SO_TOP` tấm qua mọi lọc, tốt nhất trước). Chạy lại: ý tưởng + nền trên đĩa được dùng lại;
    `xep-hang.json` đúng bộ ứng viên + chữ thì trả luôn (không gọi LLM). `khoa` = tiền tố khoá idempotency (lô bìa
    làm lại của dây chuyền đổi tiền tố).

    19/10/2026 — SÀN CHẤT LƯỢNG (`san`): tấm dưới sàn màu bìa thắng / không thấy đầu nhân vật kênh bị loại TRƯỚC giám
    khảo; giám khảo loại tấm nhân vật lệch kênh; `top` chỉ nhận tấm `bam_nhu_thang` ≥ sàn. Không tấm nào qua mà giám
    khảo đã chấm → `san_truot` (lý do, dây chuyền làm lô mới / giữ + báo). `dan`: lời dặn lô làm lại (vào lời nhắc ảnh);
    `giau`: bìa thắng GIẤU khỏi mẫu/tờ so — giám khảo chấm nó TRONG MỖI nhóm như một ứng viên, sàn bấm-như-bìa-thắng
    của nhóm = điểm của nó − 1 (`san_cua`); None = tự chọn (`bia_giau`: thư mục ≥ 3 bìa thắng), "" = không giấu."""
    t0 = time.time()
    lu = _doc_luot(thu_muc_luot)
    chu = str(chu or lu["chu_bia"]).strip()
    if not chu:
        raise RuntimeError("bìa lô: không có chữ bìa (THUMB trong 1-tieu-de.txt hoặc --chu)")
    hook = chu_tron(chu)
    dem: Dict[str, int] = {"anh": 0, "llm": 0}

    def goi_dem(loi_nhac: str, **kw) -> str:
        dem["llm"] += 1
        return goi(loi_nhac, **kw)
    # Kiểu bìa thắng CỦA kênh (khuôn hộp / chữ trần, mẫu tả few-shot riêng kênh — tả lại khi khuôn đổi).
    hs = ho_so_kieu(goc, kenh, goi=goi_dem, log=log, mau=mau)
    kc, tran = hs["kc"], hs["kieu"] == "tran"
    log("  bìa lô: kiểu chữ {0} ({1}), mẫu tả: {2}".format(
        "TRẦN" if tran else "HỘP", hs.get("bo_cuc"), hs.get("nguon_mau")))
    if giau is None:
        giau = bia_giau(str(hs.get("thu_muc_mau") or ""))
    if giau:  # bìa thắng giấu không được làm mẫu / đứng hàng so — nó là một "ứng viên" (thước sàn)
        for k in ("bia_mau", "bia_so"):
            hs[k] = [t for t in hs.get(k) or [] if os.path.abspath(t) != os.path.abspath(giau)]
    if dan:
        hs["dan"] = str(dan).strip()
    mau = [t for t in mau_cua_kenh(goc, kenh, mau, ho_so=hs) if not giau or os.path.abspath(t) != os.path.abspath(giau)]
    if not mau:
        raise RuntimeError("bìa lô: không có bìa thắng thật làm mẫu (khuôn kênh / --mau / kenh.yaml bia_lo_mau)")
    san = san_lo(hs, mau, giau=giau)
    if tran and hs.get("muc_tieu"):
        hs["muc_tieu"] = muc_tieu_theo_chu(hs["muc_tieu"], hook)
    khoa = khoa or "bia-lo:{0}:{1}".format(kenh, os.path.basename(os.path.normpath(thu_muc_luot)))
    tep_y = os.path.join(ra, "y-tuong.json")
    yt = _doc_json(tep_y) or {}
    # Kiểu hộp giữ đúng dấu vào cũ (lô đã làm không phải viết lại ý tưởng); chữ trần thêm kiểu + bố cục + mẫu.
    # 19/10/2026: lời nhắc đạo diễn có luật nhân vật kênh → ý tưởng cũ viết lại (`PHIEN_BAN_DAO_DIEN`).
    dau_vao = _bam(lu["tieu_de"], hook, so_y, *(("tran", hs.get("bo_cuc"), hs.get("mau", "")[:200]) if tran else ()),
                   *((json.dumps(hs["muc_tieu"], sort_keys=True),) if tran and hs.get("muc_tieu") else ()),
                   *(("dd", PHIEN_BAN_DAO_DIEN) if hs.get("san_nv") else ()))
    if not (yt.get("y_tuong") and yt.get("dau_vao") == dau_vao):
        log("  bìa lô: đạo diễn viết {0} ý tưởng…".format(so_y))
        yt = dict(dao_dien(goi_dem, tieu_de=lu["tieu_de"], chu_bia=hook, kich_ban=lu["kich_ban"],
                           muc_luc=lu["muc_luc"], so_y=so_y, khoa=khoa, ho_so=hs), dau_vao=dau_vao)
        if not yt["y_tuong"]:
            raise RuntimeError("bìa lô: đạo diễn không ra ý tưởng nào dùng được")
        _ghi_json(tep_y, yt)
    tang = (doc_chu_bia_tran(chu, hs, cach_ai=yt.get("chu") or ()) if tran
            else doc_chu_bia(chu, kc, cach_ai=yt.get("chu") or ()))
    chu_ve = "".join(btk.chu_cua_tang(t) for t in tang)
    # 18/10/2026 — chữ theo DÒNG (cách nhau một khoảng): cổng chữ soát chữ này — nối liền các dòng/đoạn màu thì biên tập
    # viên đọc thành một câu và "sửa" (TL2-T7-0031 bị loại oan). So ảnh vẫn tuyệt đối (bỏ khoảng trắng).
    chu_dong = " ".join(btk.chu_cua_tang(t) for t in tang)
    # 16/10/2026 — CỔNG CHỮ (`core/cong_chu.py`): chữ do MÃ vẽ nên bộ vẽ phải BẢO ĐẢM in đúng chữ đã soát (không cắt
    # bớt, phông đủ nét). Không bảo đảm được → dừng TRƯỚC khi trả tiền ảnh (dây chuyền làm lô mới / báo người).
    from . import cong_chu  # noqa: PLC0415
    loi_chu = cong_chu.bao_dam_ma(chu_ve, hook, goc=goc, ngon_ngu=ngon_ngu, kieu_phong="" if tran else "hop")
    if loi_chu:
        raise cong_chu.ChuKhongKhop("bìa lô: " + loi_chu)
    # 19/10/2026: nền kiểu hộp theo bìa thắng THẬT của kênh (`ho_so.nen`), không nền nhạt mặc định
    nen = "" if tran else str(btk.cau_hinh_kenh(goc, kenh).get("bia_hop_nen") or hs.get("nen") or "")
    uv = sinh_hang_loat(ve, yt["y_tuong"], moi_y, os.path.join(ra, "ung-vien"), kc=kc, nen=nen, khoa=khoa, log=log,
                        dem=dem, ho_so=hs)
    if not uv:
        raise RuntimeError("bìa lô: không vẽ được ảnh nền nào")
    van_tay = _bam(chu_ve, *sorted("{0}:{1}".format(u["ma"], os.path.getsize(u["nen"])) for u in uv),
                   *(("tran", PHIEN_BAN_VE_TRAN, json.dumps(tang, ensure_ascii=False, sort_keys=True)) if tran else ()),
                   *(("san", json.dumps(san, sort_keys=True)) if hs.get("san_nv") else ()))
    cu = _doc_json(os.path.join(ra, "xep-hang.json")) or {}
    if cu.get("van_tay") == van_tay and cu.get("top") and all(os.path.isfile(t["tep"]) for t in cu["top"]):
        log("  bìa lô: đã xếp hạng đúng bộ ứng viên này — dùng lại")
        return cu
    for u in uv:
        dung_bia(u, tang, goc=goc, ngon_ngu=ngon_ngu, ho_so=hs)
        # Chữ do mã vẽ = chữ đã soát (bảo đảm ở trên): cổng chữ trước giám khảo không cần lượt đọc; dấu đóng ở tấm giao.
        u["chu_khop"] = {"ok": True, "cach": "ma", "chu": chu_dong}
        loc_san(u, san)
    log("  bìa lô: {0}/{1} tấm qua lọc cứng (đầu nhân vật, manh mối, đọc được, sàn màu bìa thắng)".format(
        sum(1 for u in uv if not u["loai"]), len(uv)))
    # Chữ trần: khoá chấm theo vân tay bản vẽ (vẽ lại chữ trên cùng nền → lượt lùi ví ShopAPI không trả lời cũ).
    xh = cham(goi, uv, mau=mau, tieu_de=lu["tieu_de"], chu_bia=chu_ve, mo_dau=lu["kich_ban"][:800], thu_muc=ra,
              khoa=(khoa + ":" + van_tay[:6]) if tran else khoa, log=log, dem=dem, ho_so=hs, giau=giau)
    da_cham = [u for u in xh if not u.get("loai") and u.get("tong") is not None]
    for u in da_cham:
        u["duoi_san"] = kiem_san(u, san)
    top = [u for u in da_cham if not u["duoi_san"]][:SO_TOP]
    san_truot = "" if top else ly_do_san_truot(xh, san)
    # 19/10/2026 (chủ): lô hết lượt mà vẫn dưới sàn → DÙNG tấm bấm-như-bìa-thắng cao nhất (đã qua chữ/nhân vật/lọc
    # cứng), không giữ — `du_phong` cho dây chuyền.
    du_phong = sorted(da_cham, key=lambda u: (-float((u.get("diem") or {}).get("bam_nhu_thang") or 0),
                                              -float(u.get("tong") or 0)))[:SO_TOP] if not top else []
    for i, u in enumerate(top, 1):
        shutil.copy2(u["tep"], os.path.join(ra, "top-{0}.jpg".format(i)))
    ket = {"kenh": kenh, "luot": os.path.basename(os.path.normpath(thu_muc_luot)), "tieu_de": lu["tieu_de"],
           "chu": chu, "chu_ve": chu_ve, "chu_dong": chu_dong, "chu_tang": tang, "mau": mau, "van_tay": van_tay,
           "kieu_chu": hs["kieu"], "bo_cuc": hs.get("bo_cuc"), "nguon_mau": hs.get("nguon_mau"),
           "muc_tieu": hs.get("muc_tieu") or {}, "san": san, "san_truot": san_truot,
           "du_phong": [dict(u, hang=i) for i, u in enumerate(du_phong, 1)],
           "thu_muc_mau": hs.get("thu_muc_mau") or "",
           "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "giay": round(time.time() - t0),
           "chi_phi": {"anh_dat_moi": dem["anh"], "vnd_anh_uoc": dem["anh"] * 100, "anh_tong": len(uv),
                       "llm": dem["llm"]},
           "so_qua_loc": sum(1 for u in uv if not u.get("loai")),
           "top": [dict(u, hang=i) for i, u in enumerate(top, 1)], "ung_vien": xh, "y_tuong": yt["y_tuong"],
           "to_lien": to_lien([u for u in xh if not u.get("loai")][:6] or xh[:6], os.path.join(ra, "to-lien.jpg"))}
    _ghi_json(os.path.join(ra, "xep-hang.json"), ket)
    log("  bìa lô: xong — {0} ảnh mới, {1} lượt LLM, top: {2}{3}".format(
        dem["anh"], dem["llm"], ", ".join("{0} {1:.0f}".format(u["ma"], u["tong"]) for u in top) or "(không có)",
        " — DƯỚI SÀN: " + san_truot if san_truot else ""))
    ghi_nao_san(goc, kenh, ket)
    return ket


# ── Sàn của MỘT lô (19/10/2026) ─────────────────────────────────────────────


def san_lo(hs: Dict[str, Any], mau: Sequence[str], *, giau: str = "") -> Dict[str, Any]:
    """Sàn chất lượng của lô theo bìa thắng của kênh: `mau` (sàn màu trên MỌI bìa trong thư mục bìa thắng, không có
    thư mục thì bìa mẫu), `bam` + `nguon_bam` (`san_bam`), `dau` (`dau_dung_duoc`). Không ném lỗi."""
    tm = str(hs.get("thu_muc_mau") or "")
    thang = [b["tep"] for b in bia_thu_muc(tm, toi_da=99)] if tm else list(mau)
    bam, nguon = san_bam(tm)
    try:
        dau = dau_dung_duoc(str(hs.get("nv") or ""), thang, hs.get("mau_dau"), noi=hs.get("kieu") == "tran")
    except Exception:  # noqa: BLE001 — bộ dò hỏng: chỉ còn giám khảo xét nhân vật
        dau = False
    return {"mau": san_mau(thang), "bam": bam, "nguon_bam": nguon, "dau": bool(dau), "so_bia_thang": len(thang)}


def loc_san(u: Dict[str, Any], san: Dict[str, Any]) -> None:
    """Sàn MÁY trước giám khảo (tấm đã qua lọc cứng): màu dưới sàn bìa thắng → loại; bộ dò đầu dùng được cho kênh mà
    không thấy đầu nhân vật → loại. Ghi số đo vào `u["mau_do"]`."""
    if u.get("loai") or not u.get("tep") or not os.path.isfile(u["tep"]):
        return
    try:
        u["mau_do"] = do_mau(u["tep"])
    except (OSError, ValueError):
        pass
    han = nhat_han(u["tep"], san.get("mau") or {})
    if han:
        u["loai"] = "màu nhạt hẳn (dưới bìa thắng nhạt nhất cả 3 số đo): " + ", ".join(han)
        return
    ly = kiem_mau(u["tep"], san.get("mau") or {})
    if ly:  # dưới sàn màu: vẫn chấm, không vào top khi còn tấm đạt; lô hết lượt thì vẫn có thể được chọn
        u["mau_duoi"] = "màu nhạt hơn bìa thắng: " + ", ".join(ly)
    if san.get("dau"):
        # kiểm vàng thật 19/10 (TL1: 11/28 tấm đúng nhân vật bị loại oan): bộ dò đầu chỉ GHI, giám khảo quyết
        u["dau_may"] = bool(u.get("dau"))


def ly_do_san_truot(xh: Sequence[Dict[str, Any]], san: Dict[str, Any]) -> str:
    """Câu tóm tắt vì sao lô không có tấm nào qua sàn ('' khi giám khảo chưa chấm tấm nào — đó là lỗi AI, thử lại)."""
    da = [u for u in xh if not u.get("loai") and u.get("tong") is not None]
    mau = sum(1 for u in xh if str(u.get("loai") or "").startswith("màu nhạt") or u.get("mau_duoi"))
    nv = sum(1 for u in xh if str(u.get("loai") or "").startswith("nhân vật lệch"))
    if not da and not mau and not nv:
        return ""
    phan = []
    if da:
        tot = max(da, key=lambda u: float((u.get("diem") or {}).get("bam_nhu_thang") or 0))
        phan.append("kém bìa thắng — tấm tốt nhất " + "; ".join(kiem_san(tot, san)))
    if mau:
        phan.append("{0} tấm màu nhạt hơn bìa thắng".format(mau))
    if nv:
        phan.append("{0} tấm nhân vật lệch kênh".format(nv))
    return "; ".join(phan)


def ghi_nao_san(goc: str, kenh: str, ket: Dict[str, Any]) -> None:
    """Não bộ phận "bia": quyết định chọn bìa kèm sàn (chon) hoặc lô dưới sàn (loi). Không ném lỗi."""
    try:
        from . import cong_chu  # noqa: PLC0415
        ma = "{0}-{1}".format(kenh, ket.get("luot") or "")
        san = ket.get("san") or {}
        so = {"san_bam": san.get("bam"), "san_mau": san.get("mau"), "so_qua_loc": ket.get("so_qua_loc"),
              "anh": (ket.get("chi_phi") or {}).get("anh_tong")}
        if ket.get("top"):
            t = ket["top"][0]
            so.update(bam=(t.get("diem") or {}).get("bam_nhu_thang"), mau=t.get("mau_do"), tong=t.get("tong"))
            cong_chu.ghi_nao(goc, "chon", kenh=kenh, ma_goi=ma, so=so, khoa="bia-lo-san:{0}".format(ket.get("van_tay")),
                             noi_dung="bìa lô chọn {0}: bấm như bìa thắng {1} ≥ sàn {2:.0f}, màu ≥ phân vị {3:.0f} bìa "
                                      "thắng, nhân vật đúng kênh".format(t.get("ma"), so["bam"], float(san.get("bam") or 0),
                                                                         SAN_PHAN_VI))
        elif ket.get("san_truot"):
            cong_chu.ghi_nao(goc, "loi", kenh=kenh, ma_goi=ma, so=so, khoa="bia-lo-san:{0}".format(ket.get("van_tay")),
                             noi_dung="bìa lô DƯỚI SÀN, không giao: " + str(ket["san_truot"]))
    except Exception:  # noqa: BLE001
        pass


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
                   "loai": "", "ly_do": (t.get("ly_do_2") or t.get("ly_do") or "")[:300], "ma_lo": t["ma"],
                   "mau_do": t.get("mau_do"), "nv": t.get("nv"), "nguoi_khac": t.get("nguoi_khac")})
        muc.append({"so": i, "kieu": "bia_lo", "nhom": "khuon", "ve_chu": "ma",
                    "chu_tang": t.get("chu_tang") or kq.get("chu_tang"),
                    "chu_du_kien": kq.get("chu_dong") or kq.get("chu_ve", "")})
    chon_bia._xuat_jpg(os.path.join(thu_muc_thumb, "thumb_001.jpg"),  # noqa: SLF001
                       os.path.join(thu_muc_thumb, "CHON-thumb_001.jpg"))
    chon = {"so": 1, "kieu": "bia_lo", "tong_diem": uv[0]["tong_diem"], "chon_boi": "ai", "tep": "CHON-thumb_001.jpg",
            "ly_do": "bìa lô (vẽ {0}, chọn {1}): {2}".format(kq["chi_phi"]["anh_tong"], len(top), uv[0]["ly_do"])[:600],
            "nhom": "khuon", "theo_khuon": True, "tham_do": False, "bia_lo": True}
    # 19/10/2026 — hồ sơ bìa ghi SÀN đã qua (màu / nhân vật / bấm như bìa thắng) để soát lại sau
    san = kq.get("san") or {}
    chon["san"] = {"bam": (top[0].get("diem") or {}).get("bam_nhu_thang"), "san_bam": san.get("bam"),
                   "nguon_bam": san.get("nguon_bam"), "mau": top[0].get("mau_do"), "san_mau": san.get("mau"),
                   "nv": top[0].get("nv"), "nguoi_khac": top[0].get("nguoi_khac"), "dau_may": san.get("dau"),
                   "thu_muc_mau": kq.get("thu_muc_mau") or "", "duoi_san": bool(kq.get("duoi_san")),
                   "ly_do_duoi_san": (top[0].get("duoi_san") or []) if kq.get("duoi_san") else []}
    chon_bia._ghi_json(chon_bia.duong_tep_chon_bia(thu_muc_thumb), {  # noqa: SLF001
        "chon": chon, "ung_vien": uv, "so_luot_cham": 2, "co_khuon_thang": True, "bia_lo": True})
    btk.ghi_ke_hoach(thu_muc_thumb, {"che_do": "bia_lo", "muc": muc, "kieu_khuon": kq.get("kieu_chu") or "hop"})
    return chon


# ── 6) KIỂM VÀNG — hồi quy đầu-cuối sau MỌI thay đổi (19/10/2026) ───────────
#
# Chủ: "sao mà mọi thứ tệ vậy". Mỗi mô-đun bìa được thử riêng, không ai đặt bìa SẮP LÊN SÓNG cạnh bìa thắng của kênh.
# Kiểm vàng: với mã + lời nhắc HIỆN TẠI, vẽ MỘT lô thật / kênh (lượt mới nhất) → tờ so 3 hàng (bìa thắng | 3 bìa đang
# chạy mới nhất | top-3 mới) → CÙNG giám khảo chấm top-3 mới + bìa đang chạy + MỘT bìa thắng GIẤU (hiệu chỉnh sàn
# `bam_nhu_thang`) → đạt / trượt từng kênh. Trượt → bìa mới của kênh bị GIỮ (`vang_chan`, dây chuyền không giao) + báo.
# Đổi mã/lời nhắc/bìa thắng (vân tay `van_tay_vang`) → kỹ năng D19 tự chạy lại; trượt thì thử lại sau `GIO_THU_LAI_VANG`.

TEP_TRANG_THAI_VANG = os.path.join("workspace", "kiem-vang", "trang-thai.json")
#: Mã bìa được theo dõi (vân tay kiểm vàng) — đường tương đối theo thư mục mã của tool.
TEP_MA_VANG = ("core/bia_lo.py", "core/cong_chu.py", "core/do_bia.py", "core/chon_bia.py", "core/bia_theo_khuon.py")
#: Phần ảnh bìa của `core/auto_khau.py` (hàm/lớp cấp cao nhất).
HAM_KHAU_BIA = ("HetBiaDat", "DuoiSanBia", "_khau_thumbnail", "_mot_lo_bia", "_bia_lo_luot", "_giu_bia",
                "_cong_doc_duoc_bia", "_cong_chu_bia", "_loai_tam_giao", "_loi_nhac_vong", "_cat_vong_bia",
                "_so_vong_bia_toi_da")
GIO_THU_LAI_VANG = 24.0
_DUOI_ANH = (".jpg", ".jpeg", ".png", ".webp")


def _khuc_ham(chu: str, ten: str) -> str:
    """Nguồn MỘT hàm/lớp cấp cao nhất `ten` trong mã `chu` ('' khi không có) — tới định nghĩa cấp cao kế tiếp."""
    m = re.search(r"^(?:def|class) {0}\b".format(re.escape(ten)), chu, re.M)
    if not m:
        return ""
    sau = re.search(r"^(?:def|class|@)\S*", chu[m.end():], re.M)
    return chu[m.start():m.end() + (sau.start() if sau else len(chu))]


def van_tay_vang(goc: str, kenh: str) -> str:
    """Vân tay mọi thứ quyết định bìa của kênh: mã bìa (`TEP_MA_VANG` + phần ảnh bìa của auto_khau), `style.yaml`,
    `prompt/8-thumbnail.md`, các khoá `bia_*` của kenh.yaml, thư mục bìa thắng (ảnh + thang.json + bo-cuc.json; tệp
    đệm máy tự ghi như mau-bia-thang.json / san-bam.json không tính). RẺ: chỉ đọc đĩa."""
    h = hashlib.sha1()
    ma = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def them(nhan: str, du: bytes) -> None:
        h.update(nhan.encode("utf-8") + b"\0" + du.replace(b"\r\n", b"\n") + b"\0")

    def doc(p: str) -> bytes:
        try:
            with open(p, "rb") as tep:
                return tep.read()
        except OSError:
            return b""
    for t in TEP_MA_VANG:
        them(t, doc(os.path.join(ma, t)))
    chu = doc(os.path.join(ma, "core", "auto_khau.py")).decode("utf-8", "replace").replace("\r\n", "\n")
    for ten in HAM_KHAU_BIA:
        them("auto_khau:" + ten, _khuc_ham(chu, ten).encode("utf-8"))
    from .kenh import duong_kenh  # noqa: PLC0415
    dk = duong_kenh(goc, kenh)
    them("style", doc(os.path.join(dk, "style.yaml")))
    them("8-thumbnail", doc(os.path.join(dk, "prompt", "8-thumbnail.md")))
    them("kenh-bia", "\n".join(d for d in doc(os.path.join(dk, "kenh.yaml")).decode("utf-8", "replace").splitlines()
                              if d.startswith("bia_")).encode("utf-8"))
    tm = thu_muc_mau(goc, kenh)
    them("thu-muc", os.path.basename(tm).encode("utf-8"))
    if tm:
        for t in sorted(os.listdir(tm)):
            if t.lower().endswith(_DUOI_ANH) or t in (TEP_DS_THANG, TEP_BO_CUC_TAY):
                them("thang:" + t, hashlib.sha1(doc(os.path.join(tm, t))).hexdigest().encode("ascii"))
    return h.hexdigest()[:16]


def doc_vang(goc: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(goc, TEP_TRANG_THAI_VANG))
    return du if isinstance(du, dict) else {}


def _ghi_vang(goc: str, kenh: str, muc: Dict[str, Any]) -> None:
    du = doc_vang(goc)
    du[kenh] = muc
    _ghi_json(os.path.join(goc, TEP_TRANG_THAI_VANG), du)


def kenh_san_xuat(goc: str) -> List[str]:
    """Kênh có lượt sản xuất (PROJECTS/AUTO/<kênh>/<lượt>/1-tieu-de.txt có THUMB) và có CHANNEL/<kênh>/kenh.yaml."""
    ra = []
    goc_p = os.path.join(goc, "PROJECTS", "AUTO")
    try:
        cac = sorted(os.listdir(goc_p))
    except OSError:
        return []
    for k in cac:
        if os.path.isfile(os.path.join(goc, "CHANNEL", k, "kenh.yaml")) and luot_moi_nhat(goc, k):
            ra.append(k)
    return ra


def luot_moi_nhat(goc: str, kenh: str) -> str:
    """Thư mục lượt MỚI NHẤT (mã số lớn nhất) của kênh có chữ bìa (THUMB) — '' khi không có."""
    p = os.path.join(goc, "PROJECTS", "AUTO", kenh)
    try:
        cac = sorted((t for t in os.listdir(p) if t.isdigit()), key=int, reverse=True)
    except OSError:
        return ""
    for t in cac:
        if _doc_luot(os.path.join(p, t)).get("chu_bia"):
            return os.path.join(p, t)
    return ""


def can_kiem_vang(goc: str, kenh: str, *, bay_gio: Optional[float] = None) -> Tuple[bool, str]:
    """(nên chạy kiểm vàng?, lý do) — RẺ, chỉ đọc đĩa: chưa kiểm lần nào / vân tay đổi / lần trước trượt quá
    `GIO_THU_LAI_VANG` giờ."""
    if kenh not in kenh_san_xuat(goc):
        return False, "kênh chưa có lượt sản xuất"
    m = doc_vang(goc).get(kenh) or {}
    if not m:
        return True, "chưa kiểm vàng bìa lần nào"
    vt = van_tay_vang(goc, kenh)
    if m.get("van_tay") != vt:
        return True, "mã / lời nhắc / bìa thắng của bìa đã đổi ({0} → {1})".format(m.get("van_tay"), vt)
    if m.get("dat") is False:
        tuoi = ((bay_gio or time.time()) - float(m.get("ts") or 0)) / 3600.0
        if tuoi >= GIO_THU_LAI_VANG:
            return True, "lần trước trượt {0:.0f} giờ trước — thử lại".format(tuoi)
        return False, "lần trước trượt — thử lại sau {0:.0f} giờ".format(GIO_THU_LAI_VANG - tuoi)
    return False, "đạt {0}".format(str(m.get("luc") or "")[:16])


def giu_theo_vang(goc: str, kenh: str) -> bool:
    """Kiểm vàng TRƯỢT có GIỮ bìa mới của kênh không (19/10/2026 — chủ: sàn lệch không được chặn sản xuất; mặc định
    CHỈ CẢNH BÁO): `kenh.yaml: kiem_vang_giu` (true/false) thắng; không khai thì `cai-dat.json: kiem_vang_giu`
    (mặc định False, ô trên trang Cài đặt)."""
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        v = (doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}).get("kiem_vang_giu")
        if isinstance(v, bool):
            return v
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import cai_dat  # noqa: PLC0415
        return cai_dat.doc(goc).get("kiem_vang_giu") is True
    except Exception:  # noqa: BLE001
        return False


def vang_chan(goc: str, kenh: str) -> str:
    """Lý do GIỮ bìa mới của kênh ('' = không giữ): lần kiểm vàng xong gần nhất TRƯỢT. Giữ tới khi một lần kiểm vàng
    sau ĐẠT (đổi mã/lời nhắc/bìa thắng → D19 kiểm lại trong giờ; không đổi gì → thử lại sau 24 giờ)."""
    m = doc_vang(goc).get(kenh) or {}
    if m.get("dat") is False and giu_theo_vang(goc, kenh):
        return "kiểm vàng bìa {0} trượt: {1} (tờ so: {2})".format(str(m.get("luc") or "")[:16],
                                                                  "; ".join(m.get("ly_do") or [])[:300], m.get("to"))
    return ""


def bia_dang_chay(goc: str, kenh: str, n: int = 3, *, tai: bool = True) -> List[str]:
    """Bìa THẬT của `n` video đăng mới nhất (chi-so/bang-tom-tat.csv, ảnh i.ytimg.com — `khuon_bia.anh_that`)."""
    import csv  # noqa: PLC0415
    from . import khuon_bia  # noqa: PLC0415
    from .kenh import duong_kenh  # noqa: PLC0415
    try:
        with io.open(os.path.join(duong_kenh(goc, kenh), "chi-so", "bang-tom-tat.csv"), encoding="utf-8-sig") as tep:
            dong = list(csv.DictReader(tep))
    except OSError:
        return []
    dong.sort(key=lambda x: str(x.get("Ngày đăng") or ""), reverse=True)
    ra: List[str] = []
    for x in dong:
        vid = str(x.get("Mã video") or "").strip()
        if not vid:
            continue
        p = khuon_bia.duong_anh_that(goc, kenh, vid)
        if not os.path.isfile(p) and tai:
            p = khuon_bia.anh_that(goc, kenh, vid)
        if p and os.path.isfile(p):
            ra.append(p)
        if len(ra) >= n:
            break
    return ra


def to_vang(hang: Sequence[Tuple[str, Sequence[str], Sequence[str]]], dich: str, *, o=(480, 270)) -> str:
    """Tờ so kiểm vàng: mỗi hàng (nhãn, [tệp], [chú thích ô]) — bìa thắng | đang chạy | mới."""
    from PIL import Image, ImageDraw, ImageOps  # noqa: PLC0415
    cot = max([len(t) for _n, t, _c in hang] + [1])
    le, cao_nhan, cao_chu = 10, 34, 26
    to = Image.new("RGB", (cot * o[0] + (cot + 1) * le, len(hang) * (o[1] + cao_nhan + cao_chu + le) + le), (18, 18, 20))
    ve, f_nhan, f_chu = ImageDraw.Draw(to), _phong(24), _phong(18)
    y = le
    for nhan, tep, chu in hang:
        ve.text((le, y + 4), nhan, font=f_nhan, fill=(255, 230, 90))
        y += cao_nhan
        for i, t in enumerate(tep):
            x = le + i * (o[0] + le)
            try:
                with Image.open(t) as im:
                    to.paste(ImageOps.fit(im.convert("RGB"), o, method=Image.LANCZOS), (x, y))
            except (OSError, ValueError):
                continue
            if i < len(chu) and chu[i]:
                ve.text((x + 2, y + o[1] + 3), str(chu[i])[:52], font=f_chu, fill=(235, 235, 235))
        y += o[1] + cao_chu + le
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    to.save(dich, format="JPEG", quality=88)
    return dich


def doi_chieu(goi: Callable[..., str], *, hs: Dict[str, Any], mau: Sequence[str], moi: Sequence[str],
              dang: Sequence[str], giau: str, tieu_de: str, chu_bia: str, mo_dau: str, thu_muc: str,
              khoa: str) -> Dict[str, Dict[str, Any]]:
    """CÙNG giám khảo vòng 1 (`LOI_NHAC_CHAM_1`, tờ cỡ điện thoại có hàng bìa thắng) chấm xen kẽ top-3 MỚI, bìa ĐANG
    CHẠY và bìa thắng GIẤU → {tệp: kết quả `doc_cham_1`}. Hỏng → {}."""
    ds: List[str] = []
    for i in range(max(len(moi), len(dang))):
        ds += ([moi[i]] if i < len(moi) else []) + ([dang[i]] if i < len(dang) else [])
        if i == 0 and giau:
            ds.append(giau)
    uv = [{"ma": "dc{0}".format(i + 1), "tep": t, "nen": t, "y": i, "bien": 1} for i, t in enumerate(ds)]
    if not uv:
        return {}
    lk = loi_theo_kieu(hs)
    nv = str(hs.get("nv") or "")
    nv_url = [_url_anh(nv, cat=False)] if nv and os.path.isfile(nv) else []
    mau_url = [_url_anh(m) for m in list(mau)[:2]]
    thang = [t for t in (hs.get("bia_so") or list(mau)) if t and os.path.isfile(t)][:SO_BIA_SO]
    tt = {"tieu_de": tieu_de, "chu_bia": chu_bia, "mo_dau": " ".join(str(mo_dau or "").split())[:700] or "(none)",
          "bang_chung": lk["bang_chung"], "nv_cau": NV_CAU_CHAM.format(so=len(mau_url) + 1) if nv_url else "",
          "nv_ref": "the character reference image" if nv_url else "the winners",
          **{k: lk[k] for k in ("o_chu", "chu_ten", "ngoai_chu", "phong_cach_ta")}}
    to = to_dien_thoai(thang, uv, os.path.join(thu_muc, "_doi-chieu.jpg"))
    try:
        tho = goi(LOI_NHAC_CHAM_1.format(k=len(mau_url), n=len(uv), **tt),
                  khoa="{0}:doi-chieu:{1}".format(khoa, _bam(*[os.path.getsize(t) for t in ds], PHIEN_BAN_CHAM)),
                  toi_da_token=8000, mo_hinh=MO_HINH_CHAM,  # 19/10: 3500 cắt mất tấm 4-7
                  anh=mau_url + nv_url + [_url_anh(u["tep"]) for u in uv] + [_url_anh(to, 1100, cat=False)])
        kq = doc_cham_1(_json(tho), len(uv))
    except Exception:  # noqa: BLE001
        return {}
    return {uv[so - 1]["tep"]: k for so, k in kq.items()}


def kiem_vang(goc: str, kenh: str, *, goi: Callable[..., str], ve: Callable[..., List[str]], ra: str,
              luot: str = "", log: Callable[[str], None] = print, tai: bool = True) -> Dict[str, Any]:
    """MỘT lần kiểm vàng cho kênh (xem đầu mục). Ghi `workspace/kiem-vang/trang-thai.json[kenh]` = {dat, ly_do,
    van_tay, to, diem, san_bam, …}; trượt → báo người. Trả mục đó. Lô hỏng giữa chừng (AI/mạng) → trượt có lý do."""
    vt = van_tay_vang(goc, kenh)
    t0 = time.strftime("%Y%m%d-%H%M")
    thu = os.path.join(ra, kenh)
    tm = thu_muc_mau(goc, kenh)
    thang = [b["tep"] for b in bia_thu_muc(tm, toi_da=99)] if tm else []
    giau = bia_giau(tm)
    lu = luot if (luot and os.path.isdir(luot)) else luot_moi_nhat(goc, kenh) if not luot else os.path.join(
        goc, "PROJECTS", "AUTO", kenh, luot)
    muc: Dict[str, Any] = {"van_tay": vt, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "ts": time.time(),
                           "luot": os.path.basename(lu or ""), "thu_muc_mau": tm, "giau": os.path.basename(giau)}
    ly: List[str] = []
    kq: Dict[str, Any] = {}
    if not tm:
        ly.append("kênh chưa có thư mục bìa thắng ({0})".format(ten_thu_muc_thang(kenh)))
    elif not lu:
        ly.append("kênh chưa có lượt nào có chữ bìa")
    else:
        try:
            kq = chay(goc, kenh, thu_muc_luot=lu, ra=os.path.join(thu, "{0}-{1}".format(vt[:8], t0)), goi=goi, ve=ve,
                      log=log, giau=giau, khoa="kiem-vang:{0}:{1}:{2}:{3}".format(kenh, muc["luot"], vt[:8], t0))
        except Exception as loi:  # noqa: BLE001 — lô hỏng: kiểm vàng trượt có lý do (không giữ im lặng)
            ly.append("lô không chạy được: {0}".format(str(loi)[:200]))
    moi = [t["tep"] for t in kq.get("top") or []]
    if kq and not moi:
        ly.append("không tấm nào qua mọi cổng + sàn: " + (kq.get("san_truot") or "lọc cứng loại hết"))
        # tờ so vẫn cần hàng MỚI: 3 tấm điểm cao nhất (dù dưới sàn) cho người xem
        moi = [u["tep"] for u in sorted([u for u in kq.get("ung_vien") or [] if u.get("tep") and os.path.isfile(
            u["tep"])], key=lambda u: -(u.get("tong") or 0))][:SO_TOP]
    dang = bia_dang_chay(goc, kenh, tai=tai)
    hs = {}
    if kq:
        try:
            hs = ho_so_kieu(goc, kenh, log=lambda s: None)
            hs["bia_so"] = [t for t in hs.get("bia_so") or [] if os.path.abspath(t) != os.path.abspath(giau or "-")]
        except Exception:  # noqa: BLE001
            hs = {}
    dc = doi_chieu(goi, hs=hs, mau=[t for t in kq.get("mau") or [] if t != giau], moi=moi, dang=dang, giau=giau,
                   tieu_de=kq.get("tieu_de") or "", chu_bia=kq.get("chu_ve") or "", mo_dau="",
                   thu_muc=thu, khoa="kiem-vang:{0}:{1}".format(kenh, vt[:8])) if (kq and moi) else {}

    def bam(t: str) -> Optional[float]:
        return ((dc.get(t) or {}).get("diem") or {}).get("bam_nhu_thang")
    san = float((kq.get("san") or {}).get("bam") or SAN_BAM_MAC_DINH)
    if giau and bam(giau) is not None and tm:
        san = hieu_chinh_san_bam(tm, float(bam(giau)), kenh=kenh)
        muc["diem_giau"] = bam(giau)
    if kq.get("top"):
        b1 = bam(moi[0])
        if b1 is None:
            ly.append("giám khảo đối chiếu không chấm được tấm mới")
        elif b1 < san:
            ly.append("tấm mới tốt nhất bấm như bìa thắng {0:.0f} < sàn {1:.0f} (bìa thắng giấu: {2})".format(
                b1, san, muc.get("diem_giau", "?")))
        if lech_nhan_vat(dc.get(moi[0]) or {}):
            ly.append("tấm mới tốt nhất: " + lech_nhan_vat(dc[moi[0]]))
    muc.update(san_bam=san, diem={"moi": [bam(t) for t in moi], "dang": [bam(t) for t in dang]},
               mau_moi=(kq.get("top") or [{}])[0].get("mau_do") if kq.get("top") else None,
               san_mau=(kq.get("san") or {}).get("mau"), lo=os.path.dirname(moi[0]) if moi else "")
    chu_o = (lambda ds: ["bấm {0}".format(bam(t)) if bam(t) is not None else "" for t in ds])
    hang = [("BÌA THẮNG (giấu: {0})".format(os.path.basename(giau) or "-"), [t for t in thang if t != giau][:4],
             [""] * 4),
            ("ĐANG CHẠY — 3 video mới nhất", dang, chu_o(dang)),
            ("MỚI — top-3 lô kiểm vàng ({0})".format("ĐẠT" if not ly else "TRƯỢT"), moi, chu_o(moi))]
    muc["to"] = to_vang(hang, os.path.join(thu, "to-vang-{0}.jpg".format(t0)))
    muc["dat"], muc["ly_do"] = not ly, ly
    _ghi_vang(goc, kenh, muc)
    try:
        from . import cong_chu  # noqa: PLC0415
        cong_chu.ghi_nao(goc, "ket_qua" if not ly else "loi", kenh=kenh, khoa="kiem-vang:{0}:{1}".format(kenh, t0),
                         so={k: muc.get(k) for k in ("diem", "san_bam", "diem_giau", "van_tay")},
                         noi_dung="kiểm vàng bìa {0}: {1}".format("ĐẠT" if not ly else "TRƯỢT", "; ".join(ly)[:400]))
    except Exception:  # noqa: BLE001
        pass
    giu = giu_theo_vang(goc, kenh)
    muc["che_do"] = "giu" if giu else "canh_bao"
    _ghi_vang(goc, kenh, muc)
    if ly:
        try:
            from . import bao_dong  # noqa: PLC0415
            bao_dong.bao_dong_khan("bia_kiem_vang", "Kiểm vàng bìa kênh {0} TRƯỢT: {1}".format(kenh, "; ".join(ly)[:300]),
                                   "Xem tờ so {0} (bìa thắng | đang chạy | mới).{1}".format(
                                       muc["to"], " Bìa mới của kênh đang bị GIỮ tới khi kiểm vàng đạt." if giu else
                                       " Chế độ chỉ cảnh báo: bìa mới VẪN giao (bật «Kiểm vàng bìa trượt thì giữ bìa» "
                                       "trong Cài đặt để giữ)."),
                                   "Video mới của kênh không được giao." if giu else
                                   "Bìa mới có thể kém bìa thắng của kênh.", goc=goc, kenh=kenh)
        except Exception:  # noqa: BLE001
            pass
        try:
            duong = os.path.join(goc, "workspace", "loi-chay-max.md")
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            with io.open(duong, "a", encoding="utf-8") as tep:
                tep.write("- [{0}] **khan** · kênh {1} — Kiểm vàng bìa kênh {1} TRƯỢT: {2} — {4}, tờ so "
                          "{3}\n".format(time.strftime("%Y-%m-%d %H:%M"), kenh, "; ".join(ly)[:300], muc["to"],
                                         "bìa mới đang GIỮ" if giu else "chỉ cảnh báo, bìa mới vẫn giao"))
        except OSError:
            pass
    log("  kiểm vàng {0}: {1}{2} — tờ so {3}".format(kenh, "ĐẠT" if not ly else "TRƯỢT",
                                                    (" (" + "; ".join(ly) + ")") if ly else "", muc["to"]))
    return muc


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
        # 18/10/2026: khoá phủ cả ẢNH THAM CHIẾU (URL tải lên mỗi lần chạy một khác) — cùng lời nhắc mà tham chiếu
        # mới thì ShopAPI trả 409 "Idempotency-Key đã dùng cho nội dung khác" (lô chạy lại hỏng cả 7 ý).
        job = client.images.create_and_wait(prompt=loi_nhac, n=int(n), aspect_ratio="16:9", reference_images=list(url),
                                            idempotency_key="{0}:{1}".format(khoa, _bam(*url)), timeout=1800)
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


def bia_giau(tm: str) -> str:
    """Bìa thắng GIẤU của kiểm vàng: bìa thứ 4 của thư mục (3 bìa đầu giữ cho hàng so), thư mục 3 bìa thì bìa cuối."""
    thang = [b["tep"] for b in bia_thu_muc(tm, toi_da=99)] if tm else []
    return thang[3] if len(thang) >= 4 else (thang[-1] if len(thang) >= 3 else "")


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.bia_lo", description="Bìa lô: vẽ vài chục rồi chọn.")
    p.add_argument("--kenh", default="", help="mã kênh (bắt buộc khi vẽ lô; kiểm vàng: bỏ trống = mọi kênh sản xuất)")
    p.add_argument("--luot", default="", help="mã lượt (vd 0001) hoặc đường thư mục lượt")
    p.add_argument("--kiem-vang", action="store_true",
                   help="KIỂM VÀNG: một lô thật / kênh bằng mã + lời nhắc hiện tại, tờ so bìa thắng | đang chạy | mới, "
                        "đạt/trượt từng kênh (trượt → giữ bìa mới của kênh + báo)")
    p.add_argument("--so-y", type=int, default=SO_Y_MAC_DINH)
    p.add_argument("--moi-y", type=int, default=MOI_Y_MAC_DINH)
    p.add_argument("--ra", default="", help="thư mục ra (mặc định workspace/bia-lo/<kênh>-<lượt>; kiểm vàng: "
                                            "workspace/kiem-vang/<ngày>)")
    p.add_argument("--chu", default="", help='chữ bìa, vd "同じ車に長く|*乗る人の|ほとんどが"')
    p.add_argument("--mau", action="append", default=[], help="bìa thắng thật (tệp/thư mục), lặp được")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    goi = _goi_that(goc, print)
    if a.kiem_vang:
        ra = os.path.abspath(a.ra or os.path.join(goc, "workspace", "kiem-vang", time.strftime("%Y-%m-%d")))
        dat = True
        for k in ([a.kenh] if a.kenh else kenh_san_xuat(goc)):
            hs = ho_so_kieu(goc, k, goi=goi)
            giau = bia_giau(str(hs.get("thu_muc_mau") or ""))
            mau = [t for t in mau_cua_kenh(goc, k, ho_so=hs) if os.path.abspath(t) != os.path.abspath(giau or "-")]
            nv = os.path.join(goc, "CHANNEL", k, "nv", "nv1.png")
            m = kiem_vang(goc, k, goi=goi, ve=_ve_that(goc, mau + ([nv] if os.path.isfile(nv) else [])), ra=ra,
                          luot=a.luot)
            dat = dat and bool(m.get("dat"))
            print("KIỂM VÀNG {0}: {1} — {2} — tờ so {3}".format(k, "ĐẠT" if m.get("dat") else "TRƯỢT",
                                                               "; ".join(m.get("ly_do") or []) or "ok", m.get("to")))
        return 0 if dat else 1
    if not a.kenh or not a.luot:
        p.error("cần --kenh và --luot (hoặc --kiem-vang)")
    luot = a.luot if os.path.isdir(a.luot) else os.path.join(goc, "PROJECTS", "AUTO", a.kenh, a.luot)
    ma = "{0}-{1}".format(a.kenh, os.path.basename(os.path.normpath(luot)))
    ra = os.path.abspath(a.ra or os.path.join(goc, "workspace", "bia-lo", ma))
    # Mẫu tả bìa thắng của kênh dựng TRƯỚC (một lượt AI khi khuôn đổi) để ảnh tham chiếu là bìa thắng cùng kiểu.
    mau = mau_cua_kenh(goc, a.kenh, a.mau, ho_so=ho_so_kieu(goc, a.kenh, goi=goi, mau=a.mau))
    nv = os.path.join(goc, "CHANNEL", a.kenh, "nv", "nv1.png")
    kq = chay(goc, a.kenh, thu_muc_luot=luot, ra=ra, chu=a.chu, so_y=a.so_y, moi_y=a.moi_y,
              goi=goi, ve=_ve_that(goc, mau + ([nv] if os.path.isfile(nv) else [])), mau=mau)
    for t in kq.get("top") or []:
        print("TOP {0}: {1}  {2}/100  {3}".format(t["hang"], t["tep"], t["tong"], t.get("ly_do_2") or t.get("ly_do")))
    if kq.get("san_truot"):
        print("DƯỚI SÀN:", kq["san_truot"])
    print("tờ liên:", kq.get("to_lien"), "· chi phí:", json.dumps(kq.get("chi_phi"), ensure_ascii=False))
    return 0 if kq.get("top") else 1


if __name__ == "__main__":
    raise SystemExit(main())
