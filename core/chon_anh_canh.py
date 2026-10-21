"""Ảnh CẢNH: vẽ N ứng viên → giám khảo nội dung/giọng → chọn tấm tốt nhất → không đạt thì viết lại lời nhắc (17/10/2026).

═══ VÌ SAO ═══

Chủ dự án 17/10/2026, sau khi xem video: nhiều ảnh cảnh trông *"kinh dị"*, không hợp, và **không vẽ đúng nội dung lời
đọc**. Muốn làm y như bìa: vẽ nhiều ứng viên, chấm, chọn tấm hợp nội dung nhất; không tấm nào đủ tốt thì SỬA LỜI NHẮC
rồi vẽ lại. Không trần chi phí — chỉ cần chất lượng. Luật chủ: không bao giờ hạ chất lượng, chỉ thử lại.

Chẩn đoán 17/10 (`workspace/chan-doan/anh-canh-17-10.md`, 150 ảnh thật của 8 kênh): cái hỏng nhiều nhất KHÔNG phải nét
vẽ mà là NỘI DUNG — ảnh đẹp, an toàn nhưng không nói gì về câu đang đọc; và một phần đáng kể có nét rợn (bóng đen
trùm tường, người không mặt, mặt nạ, nứt vỡ, phòng tối) do chính lời nhắc khuôn đòi "motif lan khắp khung, nứt, hắt
bóng lên tường", "phóng đại cảm xúc". Bộ chấm cũ (`core/cham_anh.py`) chỉ so NHÂN VẬT với ảnh tham chiếu, không ai
nhìn xem tấm ảnh có đúng câu đang đọc, có ấm áp hay không.

═══ CÁCH LÀM (một cảnh) ═══

1. Vòng 0: một job ảnh `n = N` (`kenh.yaml: so_ung_vien_canh`, mặc định `SO_UNG_VIEN_MAC_DINH`), lời nhắc gốc + câu giữ
   giọng ấm của kênh (`giong_an_toan`, `style.yaml: tone_guard`) nối cuối MỌI lời nhắc ảnh.
2. MỘT lượt giám khảo nhìn ảnh tham chiếu + cả N ứng viên cùng lúc, có câu đọc + mô tả cảnh + ghi chú phong cách kênh,
   chấm 0–10 năm mục: nội dung, giọng, lỗi vẽ, phong cách, nhân vật (vế nhân vật = luật của `cham_anh`). Điểm một tấm =
   mục THẤP NHẤT (mục tệ nhất chặn trần). Cờ `kinh_di` (bất kỳ nét rợn nào) đánh tấm ấy xuống dưới mọi tấm sạch.
3. Tấm tốt nhất < `NGUONG_DAT` hoặc dính cờ rợn → VIẾT LẠI phần cảnh của lời nhắc theo lý do giám khảo (giữ nghĩa,
   cụ thể, ấm, sát câu đọc, cấm dấu hiệu rợn; đuôi phong cách giữ nguyên) → vẽ N tấm mới → chấm lại. Tối đa
   `SO_VONG_VIET_LAI` vòng. Chọn tấm tốt nhất của MỌI vòng.
4. Vẫn dưới ngưỡng → giữ tấm tốt nhất + ghi CẢNH BÁO (sổ, nhật ký, não). Không chặn dựng, không lùi đường kém hơn.

═══ SỔ — chạy tiếp không vẽ lại ═══

`<lượt>/_chon-anh.json` = {số cảnh: {vòng (lời nhắc, tệp, điểm), tấm chọn, cảnh báo, số ảnh/lượt chấm}} — ghi sau MỖI
vòng, nên lượt đứt giữa cảnh chạy tiếp dùng lại ứng viên + điểm đã có. Ứng viên nằm ở `<lượt>/_ung-vien-anh/<số>/`
(không rắc vào `5-anh/` — thư mục khách mở xem), tấm thua bị xoá khi cảnh đã chốt. Khoá idempotency của job đúc từ
(lời nhắc, tham chiếu, vòng) nên kể cả mất sổ, gửi lại cũng không trả tiền hai lần.

Module này THUẦN: vẽ / chấm / viết lại được truyền vào (`chon_canh`), nên bài kiểm chạy không cần mạng. Nối vào dây
chuyền ở `core/auto_khau._lam_anh_canh_chon`.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["SO_UNG_VIEN_MAC_DINH", "NGUONG_DAT", "anh_uoc_moi_canh", "SO_VONG_VIET_LAI", "TIEU_CHI", "GIONG_AN_TOAN", "TEP_SO",
           "THU_MUC_UV", "so_ung_vien", "giong_an_toan", "ap_giong_an_toan", "tach_than_duoi", "loi_nhac_cham", "ap_kiem_may", "CO_CUNG", "CO_LOAI",
           "doc_cham", "diem_tong", "xep_hang", "can_viet_lai", "ghi_chu_viet_lai", "viet_lai_canh", "SoChon",
           "chon_canh", "tom_tat", "anh_data_url"]

#: Số ứng viên mỗi cảnh khi `kenh.yaml` không khai `so_ung_vien_canh`. 0 = tắt (đường một tấm cũ).
SO_UNG_VIEN_MAC_DINH = 3
TRAN_UNG_VIEN = 6
#: Điểm (thang 10, = mục thấp nhất) từ đây trở lên mới coi là đạt.
#:
#: Hiệu chỉnh 17/10 trên 50 cảnh thật đã chấm bằng thước mù (Claude Max Opus 5.5, chấm lại lần hai tương quan 0,80):
#: giám khảo ví KHÔNG xem lời nhắc cảnh lệch thước mù −1,1 điểm, tương quan 0,40 (Fable 5; Opus 5 0,30; ghép hai mô
#: hình 0,31 — không hơn). Ngưỡng 7 ở đây: tấm qua có điểm mù trung bình 6,6, tấm trượt 4,7 — gần nhất với "7 mù" mà
#: thang điểm nguyên của giám khảo ví cho phép (6 → 5,9). Ví không có mô hình nào mạnh hơn (`/v1/models`: chỉ ba bậc
#: Claude cùng giá).
NGUONG_DAT = 7.0
#: Số vòng viết lại lời nhắc tối đa sau vòng đầu.
SO_VONG_VIET_LAI = 2
#: Số vòng TRUNG BÌNH một cảnh đi qua — cho ước tiền / van ví. Thử thật 17/10 (36 cảnh TL1/TL3, N = 3): 4,75–5,25
#: ảnh/cảnh ≈ 1,6–1,75 vòng.
VONG_TB_UOC = 1.7
TIEU_CHI = ("noi_dung", "giong", "loi", "phong_cach", "nhan_vat")
#: Mô hình giám khảo / viết lại khi đi ví ShopAPI. Cùng giá mọi bậc (`core/bien_tap_content.py`); Fable là bậc mạnh
#: nhất của ví và nhìn ảnh được (đo 17/10: cùng một tấm "bàn nhỏ chồng lên bàn lớn" — Fable gọi đúng tên lỗi).
MO_HINH_CHAM = "claude-fable-5"
TEP_SO = "_chon-anh.json"
THU_MUC_UV = "_ung-vien-anh"
#: Giám khảo chạy trong luồng ảnh — cả trăm cảnh về cùng lúc. Van này giữ số lượt chấm đồng thời vừa phải.
SONG_SONG_CHAM = 12
VAN_CHAM = threading.BoundedSemaphore(SONG_SONG_CHAM)

#: Câu giữ giọng ấm nối cuối MỌI lời nhắc ảnh cảnh. Kênh đặt riêng bằng `style.yaml: tone_guard` ("" = tắt).
#: Câu KHẲNG ĐỊNH đứng trước (máy vẽ theo chữ được gọi tên), phần cấm ngắn và gọi đúng thứ đã gặp trong chẩn đoán.
#: Ánh sáng "giữ đúng nét vẽ của kênh" (thử thật 17/10: "bright soft natural light" kéo TL3 nền trắng cọ đen sang bàn
#: gỗ, nắng thật — lệch phong cách).
GIONG_AN_TOAN = ("warm, calm and reassuring everyday mood, clear even lighting kept in the channel's own drawing style, "
                 "every person has a simple friendly face, nothing eerie or unsettling, no looming dark shadows, no "
                 "faceless, masked or blank-faced figures, no distorted faces, no gloomy dark room, one single "
                 "continuous picture with no panels, no arrows or marks drawn over the picture, no letters or numbers "
                 "anywhere")

_KHOA_SO = threading.Lock()


def _bam(*phan: Any) -> str:
    return hashlib.sha1("|".join(str(p) for p in phan).encode("utf-8")).hexdigest()[:12]


def so_ung_vien(kenh: Any) -> int:
    """`kenh.so_ung_vien_canh` kẹp 0..TRAN_UNG_VIEN; đồ giả không có thuộc tính → 0 (đường cũ)."""
    try:
        return max(0, min(TRAN_UNG_VIEN, int(getattr(kenh, "so_ung_vien_canh", 0) or 0)))
    except (TypeError, ValueError):
        return 0


def anh_uoc_moi_canh(n: int) -> float:
    """Số ảnh ƯỚC mỗi cảnh: `n` ứng viên × số vòng trung bình; tắt (n = 0) → 1 tấm."""
    return float(n) * VONG_TB_UOC if int(n or 0) > 0 else 1.0


def giong_an_toan(style: Any) -> str:
    """Câu giữ giọng của kênh: `style.yaml: tone_guard` nếu có khai (kể cả rỗng = tắt), không thì `GIONG_AN_TOAN`."""
    st = style if isinstance(style, dict) else {}
    if "tone_guard" in st:
        return " ".join(str(st.get("tone_guard") or "").split())
    return GIONG_AN_TOAN


def ap_giong_an_toan(prompt: str, cau: str) -> str:
    """Nối `cau` vào cuối lời nhắc ĐÚNG một lần (đã có thì thôi)."""
    p = str(prompt or "").strip()
    c = " ".join(str(cau or "").split()).strip(" ,.")
    if not p or not c or c.lower() in p.lower():
        return p
    return "{0}, {1}".format(p.rstrip(" ,.;"), c)


def tach_than_duoi(prompt: str, style: Any = None, them: Sequence[str] = ()) -> Tuple[str, str]:
    """Tách lời nhắc ảnh thành (THÂN cảnh do AI viết, ĐUÔI phong cách do mã ghép).

    Đuôi bắt đầu ở chỗ sớm nhất xuất hiện một trong: 40 ký tự đầu của `image_style`, `reference_lock`, câu giữ giọng,
    hoặc các mốc `them` (đuôi nối cảnh…). Không thấy mốc → cả chuỗi là thân."""
    p = str(prompt or "")
    st = style if isinstance(style, dict) else {}
    moc = [str(st.get(k) or "").strip()[:40] for k in ("image_style", "reference_lock")]
    moc += [giong_an_toan(st)[:40]] + [str(m or "").strip()[:40] for m in them]
    vi_tri = [p.find(m) for m in moc if len(m) >= 12 and p.find(m) > 20]
    if not vi_tri:
        return p.strip(), ""
    i = min(vi_tri)
    return p[:i].rstrip(" ,;"), p[i:].strip()


def anh_data_url(duong: str, rong: int = 768, nhan: str = "") -> str:
    """Ảnh → data URL JPEG bề ngang `rong` (giữ tỉ lệ). Không có PIL/ảnh hỏng → đọc thô.

    `nhan` ("1", "REF"…) được VẼ vào góc trên trái: thử thật 17/10 (TL6 cảnh 4) giám khảo chấm 10 điểm lỗi cho một tấm
    lưới 12 ô — nhãn ngay trên ảnh để nó không lẫn tấm nào là tấm nào."""
    try:
        from PIL import Image, ImageDraw  # noqa: PLC0415
        im = Image.open(duong).convert("RGB")
        if im.size[0] > rong:
            im = im.resize((rong, max(1, round(im.size[1] * rong / im.size[0]))), Image.LANCZOS)
        if nhan:
            ve = ImageDraw.Draw(im)
            co = max(18, im.size[1] // 9)
            try:
                from PIL import ImageFont  # noqa: PLC0415
                f = ImageFont.truetype("arial.ttf", co)
            except Exception:  # noqa: BLE001
                f = None
            ve.rectangle((0, 0, int(co * (0.75 * len(nhan) + 0.6)), int(co * 1.3)), fill=(220, 20, 60))
            ve.text((int(co * 0.3), int(co * 0.1)), nhan, fill=(255, 255, 255), font=f)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=86)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:  # noqa: BLE001
        with open(duong, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


# ═══ GIÁM KHẢO ═══

LOI_NHAC_CHAM = """You are the art director of a Japanese YouTube channel of WARM, CALM self-understanding psychology
for adults. The viewer comes to feel understood and at ease: a picture that feels creepy, sinister or scary is a failure
even when it is clever, and a pretty picture that does not show what is being said is also a failure.
{ta_anh} Every image carries its label in a red box at the top-left corner ("REF", or the candidate number) — that box
is ours, ignore it.
Narration line read while this scene is on screen (Japanese): 「{loi_doc}」
Who should appear (ONLY for the nhan_vat check — never judge noi_dung by this): {mo_ta}
Channel style: {phong_cach}{nghi}

STEP 1 — before looking at the candidates, write "khoanh_khac": the concrete, literal moment this line describes, as
WHO is doing WHAT, WHERE, with WHICH key object the line names (for an abstract line: the everyday moment where people
live it). At most 25 words.

STEP 2 — for each candidate write "ta": what it actually shows, at most 12 words. Then score it 0-10. Be a STRICT
reviewer: 8 or more means you would publish it unchanged.
- noi_dung: does it show the moment of STEP 1? 8+ only when the who, the action AND the key object are all visible
  and a viewer who sees ONLY the picture could guess the line. The right person but the action or the key object
  missing = 5 at most. A calm character with a prop or a room the line does not mention = 3 at most. Unrelated = 0.
- giong: tone. 10 = warm, calm, safe. Lower for anything horror-like: creepy, sinister, menacing, oppressive darkness,
  looming shadows or silhouettes, faceless or blank-faced figures (also faceless people in the background), masks,
  distorted or melting faces, huge or empty staring eyes, a face filling the frame in extreme close-up, dark low-key
  rooms or night palettes, twins/doubles/reflections of the character, monsters, cracked or broken bodies, gore.
- loi: drawing defects. Inspect closely: count the arms, legs and hands of every figure. A limb missing, detached,
  doubled, see-through or passing through furniture, furniture stacked or merged, a head cut off by the frame, a
  melted face = 4 at most. 10 = clean.
- phong_cach: same drawing style and palette as the channel style{va_tham_chieu}, including the channel's own rules in
  the style note (colours allowed, how many props, how much setting, the background).
- nhan_vat: {nhan_vat}
HARD FAILURES — set the flag true (the candidate is then rejected whatever its scores):
- "chu": any readable or garbled letters, numbers, words or symbols anywhere (signs, screens, papers, books, labels);
- "danh_dau": arrows, crosses, circles, ticks or other annotation marks drawn OVER the picture;
- "luoi": the picture is made of several panels, a grid, a collage, a split frame or a storyboard;
- "dau": a watermark, logo or sparkle/star mark in a corner{co_nv}.
Set "kinh_di": true when ANY horror or creepy element is present, however small. Keep every text field short.
Return JSON only: {{"khoanh_khac": "<STEP 1>", "ung_vien": [{{"so": 1, "ta": "<what it shows>", "noi_dung": 0,
"giong": 0, "loi": 0, "phong_cach": 0, "nhan_vat": null, "chu": false, "danh_dau": false, "luoi": false, "dau": false,
"khac_nhan_vat": false, "kinh_di": false, "dau_hieu": ["<creepy element>"], "loi_ve": ["<defect>"], "ly_do": "<one short sentence>"}}],
"sua": "<when no candidate is good: what the image prompt must change, one or two short sentences; else empty>"}}"""

#: Cờ lỗi CỨNG giám khảo trả. Tên cờ → nhãn đọc.
CO_CUNG = {"chu": "chữ/số trong ảnh", "danh_dau": "mũi tên/dấu vẽ chồng", "luoi": "ảnh chia ô/lưới",
           "dau": "dấu sao/logo góc ảnh", "khac_nhan_vat": "nhân vật chính không phải nhân vật tham chiếu"}
#: Cờ nào thật sự loại tấm (điểm 0). `dau` KHÔNG loại: dấu sao do nhà cung cấp dán SAU khi vẽ, giống nhau ở mọi ứng
#: viên — chọn tấm khác không chữa được, việc ấy là của `core/xoa_dau_anh` (giám khảo xem ảnh ĐÃ gỡ dấu; cờ còn bật là
#: số đo bước gỡ hụt, ghi vào sổ).
#: `khac_nhan_vat` (21/10/2026): nhân vật chính là một hình KHÁC ảnh tham chiếu. Chủ bắt kênh mới vẽ linh vật đầu mochi
#: của kênh gốc dù ảnh tham chiếu là người thật: lời nhắc + ghi chú phong cách còn tả nhân vật cũ, nên giám khảo chấm vế
#: nhân vật 10/10 theo CHỮ. Ảnh tham chiếu là sự thật; tấm vẽ nhân vật khác bị loại, vòng sau viết lại lời nhắc.
CO_LOAI = ("chu", "danh_dau", "luoi", "khac_nhan_vat")
_NGHI = {"mui_ten_do": "has a large pure-red mark (maybe an arrow or annotation drawn over the picture)",
         "luoi": "may be split into panels (long straight lines across the whole frame)"}

_NHAN_VAT_CO = ("the first {k} image(s) are the character reference(s). Judge (a) HEADCOUNT — every character the "
                "description names is there exactly once; (b) DESIGN — each one has the same design as its reference "
                "(face, proportions, clothing, colours; ignore pose and expression); (c) WHO DOES WHAT — a posture the "
                "description gives one named character did not land on another. 10 = all three hold; 5 = clearly "
                "redrawn; 2 = a named character missing, doubled or swapped. null when the description names nobody. "
                "The REF image(s) are the ONLY truth for how the main character looks: when the channel style note or "
                "the description describes the character differently, ignore the text and follow the REF. A candidate "
                "whose main character is a different figure from the REF (a mascot or round-headed figure instead of a "
                "person or the reverse, other hair, other age or gender, clothing of a different colour) = 2 at most.")
_NHAN_VAT_KHONG = "null (no character reference for this scene)."


def loi_nhac_cham(*, loi_doc: str, mo_ta: str, phong_cach: str, so_tham_chieu: int, so_ung_vien: int,
                  nghi: Optional[Dict[int, Sequence[str]]] = None) -> str:
    """`nghi` = {số tấm: [mã nghi của `core.kiem_anh_cung`]} — phép đo máy báo trước để giám khảo nhìn kỹ đúng chỗ."""
    k, n = int(so_tham_chieu), int(so_ung_vien)
    dong = ["candidate {0} {1}".format(so, _NGHI[m]) for so, ds in sorted((nghi or {}).items()) for m in ds
            if m in _NGHI]
    ta = ("The first {0} image(s) are REFERENCE designs. The last {1} images are CANDIDATES for ONE scene, numbered "
          "1..{1} in order.".format(k, n) if k else
          "The {0} images are CANDIDATES for ONE scene, numbered 1..{0} in order.".format(n))
    return LOI_NHAC_CHAM.format(
        ta_anh=ta, loi_doc=" ".join(str(loi_doc or "").split())[:400] or "(none)",
        mo_ta=" ".join(str(mo_ta or "").split())[:900] or "(none)",
        phong_cach=" ".join(str(phong_cach or "").split())[:600] or "(none)",
        va_tham_chieu=" and the reference images" if k else "",
        nhan_vat=_NHAN_VAT_CO.format(k=k) if k else _NHAN_VAT_KHONG,
        co_nv=(";\n- \"khac_nhan_vat\": the main character is visibly a DIFFERENT figure from the REF image (judge "
               "by the picture, never by the text; a scene that shows only other people is not this flag)") if k else "",
        nghi=("\nMachine check — look closely: " + "; ".join(dong) + ".") if dong else "")


def _diem(v: Any) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        return max(0.0, min(10.0, float(v)))
    except (TypeError, ValueError):
        return None


def _ds_chu(v: Any, tran: int = 6) -> List[str]:
    ds = v if isinstance(v, list) else ([v] if v else [])
    return [str(x).strip()[:80] for x in ds if str(x or "").strip()
            and str(x).strip().lower() not in ("none", "no", "n/a", "-", "[]", "false", "null")][:tran]


def _co(v: Any) -> bool:
    return v is True or str(v).strip().lower() in ("true", "yes", "1")


def doc_cham(du: Any, n: int) -> Dict[int, Dict[str, Any]]:
    """JSON giám khảo → {số tấm 1..n: {diem{mục}, tong, kinh_di, dau_hieu, loi_ve, ly_do}}.

    Tấm thiếu một trong bốn mục bắt buộc (nội dung, giọng, lỗi, phong cách) thì bỏ — chấm thiếu không được thắng.
    `nhan_vat` null = không có gì để so (không tính)."""
    ra: Dict[int, Dict[str, Any]] = {}
    ds = du.get("ung_vien") if isinstance(du, dict) else du
    for x in ds if isinstance(ds, list) else []:
        if not isinstance(x, dict):
            continue
        try:
            so = int(x.get("so"))
        except (TypeError, ValueError):
            continue
        diem = {k: _diem(x.get(k)) for k in TIEU_CHI}
        if not 1 <= so <= n or any(diem[k] is None for k in TIEU_CHI[:4]):
            continue
        dau = _ds_chu(x.get("dau_hieu"))
        muc = {"diem": diem, "kinh_di": _co(x.get("kinh_di")), "dau_hieu": dau, "loi_ve": _ds_chu(x.get("loi_ve")),
               "ly_do": " ".join(str(x.get("ly_do") or "").split())[:240],
               "ta": " ".join(str(x.get("ta") or "").split())[:120],
               "co": [c for c in CO_CUNG if _co(x.get(c))]}
        muc["tong"] = diem_tong(muc)
        ra[so] = muc
    if isinstance(du, dict) and ra:
        sua = " ".join(str(du.get("sua") or "").split())[:300]
        kk = " ".join(str(du.get("khoanh_khac") or "").split())[:200]
        for m in ra.values():
            m["sua"], m["khoanh_khac"] = sua, kk
    return ra


def diem_tong(muc: Dict[str, Any]) -> float:
    """Điểm một tấm = mục THẤP NHẤT (mục tệ nhất chặn trần). Dính cờ loại (`CO_LOAI` — của giám khảo hay của phép đo
    máy `core.kiem_anh_cung`) → 0. Không có mục nào → 0."""
    if any(c in CO_LOAI for c in muc.get("co") or []):
        return 0.0
    cac = [v for v in (muc.get("diem") or {}).values() if v is not None]
    return round(min(cac), 1) if cac else 0.0


def ap_kiem_may(kq: Dict[int, Dict[str, Any]], may: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Gộp lỗi CHẮC của phép đo máy (`kiem_anh_cung.kiem`, theo số tấm) vào điểm giám khảo: thêm cờ, tính lại `tong`."""
    ten = {"mui_ten_do": "danh_dau", "luoi": "luoi"}
    for so, m in kq.items():
        them = [ten[x] for x in ((may.get(so) or {}).get("loi") or []) if x in ten]
        if them:
            m["co"] = sorted(set(list(m.get("co") or []) + them))
            m["may"] = list((may.get(so) or {}).get("loi") or [])
            m["tong"] = diem_tong(m)
    return kq


def _tb(muc: Dict[str, Any]) -> float:
    cac = [v for v in (muc.get("diem") or {}).values() if v is not None]
    return sum(cac) / len(cac) if cac else 0.0


def xep_hang(ung_vien: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tấm tốt nhất trước: sạch (không cờ rợn) > điểm tổng > trung bình các mục > vòng sớm hơn. Tấm chưa chấm cuối."""
    return sorted(ung_vien, key=lambda u: (u.get("cham") is None, bool((u.get("cham") or {}).get("kinh_di")),
                                           -float((u.get("cham") or {}).get("tong") or 0),
                                           -_tb(u.get("cham") or {}), int(u.get("vong") or 0), int(u.get("so") or 0)))


def can_viet_lai(tot: Optional[Dict[str, Any]], nguong: float = NGUONG_DAT) -> bool:
    """Tấm tốt nhất chưa đạt (dưới ngưỡng) hoặc dính cờ rợn → phải viết lại lời nhắc."""
    cham = (tot or {}).get("cham")
    if not cham:
        return False
    return bool(cham.get("kinh_di")) or float(cham.get("tong") or 0) < float(nguong)


def ghi_chu_viet_lai(ung_vien: Sequence[Dict[str, Any]], toi_da: int = 4) -> str:
    """Lý do giám khảo (tấm đã chấm của vòng vừa rồi) gom thành ghi chú cho người viết lại."""
    dong: List[str] = []
    sua = ""
    for u in xep_hang([x for x in ung_vien if x.get("cham")])[:toi_da]:
        c = u["cham"]
        d = c.get("diem") or {}
        thap = sorted(((k, v) for k, v in d.items() if v is not None), key=lambda kv: kv[1])[:2]
        phan = ["candidate {0}: {1}/10".format(u.get("so"), c.get("tong"))]
        phan.append("weakest " + ", ".join("{0}={1:g}".format(k, v) for k, v in thap))
        if c.get("kinh_di"):
            phan.append("CREEPY: " + (", ".join(c.get("dau_hieu") or []) or "yes"))
        if c.get("co"):
            phan.append("REJECTED for: " + ", ".join(
                {"chu": "letters/text in the picture", "danh_dau": "arrows/marks drawn over it",
                 "luoi": "split into panels", "dau": "corner watermark",
                 "khac_nhan_vat": "the main character is NOT the reference character - keep the words `the "
                                  "reference character` and never describe its look"}.get(x, x) for x in c["co"]))
        if c.get("loi_ve"):
            phan.append("defects: " + ", ".join(c["loi_ve"][:3]))
        if c.get("ly_do"):
            phan.append(c["ly_do"])
        dong.append("- " + "; ".join(phan))
        sua = sua or str(c.get("sua") or "")
    kk = next((str(u["cham"].get("khoanh_khac")) for u in ung_vien if (u.get("cham") or {}).get("khoanh_khac")), "")
    if kk:
        dong.append("- the moment the picture must show: " + kk)
    if sua:
        dong.append("- director's fix: " + sua)
    return "\n".join(dong)


# ═══ VIẾT LẠI LỜI NHẮC ═══

LOI_NHAC_VIET_LAI = """You rewrite ONE scene image prompt for a WARM, CALM Japanese self-understanding psychology video
for adults. The art director rejected the pictures drawn from the current prompt. Their notes:
{ghi_chu}

Narration line read while this scene is on screen (Japanese): 「{loi_doc}」
Current scene prompt:
{than}

Write a better scene prompt:
- show the line's literal moment (the director's "moment the picture must show" when given): right after the camera
  shot name WHO, doing WHAT, with WHICH key object the line names, then WHERE. When the line is abstract, show the
  everyday situation where people feel it, never a symbolic or surreal metaphor;
- one single continuous picture: no panels or split frame, no arrows or marks drawn over it, no letters, numbers,
  signs or screens with writing;
- warm, calm and safe: soft natural light, friendly relaxed faces. Never horror: no looming shadows or silhouettes, no
  dark rooms, no masks, no blank or faceless figures, no doubles or reflections of the character, no cracks spreading,
  no flood or swallowing shapes, no eyes in the dark, no distorted bodies;
- keep the words `the reference character` for the main character and never describe its face, body, clothes or
  colours; keep other people as they are named;
- open with the camera shot (`Close-up of…`, `Medium shot of…`, `Wide shot of…`); one continuous picture; nothing that
  carries writing (no screens with messages, no signs, no labels, no open pages);
- keep a `with <colour> accent` phrase if the current prompt has one; about the same length or shorter.
Return ONLY the new scene prompt as one paragraph, no commentary."""


def viet_lai_canh(goi: Optional[Callable[[str], str]], than: str, *, loi_doc: str, ghi_chu: str) -> str:
    """Viết lại THÂN cảnh theo lý do giám khảo. Trả thân mới, hoặc "" khi AI hỏng / trả rác / không đổi gì.

    Rào: dài 40..max(900, 2× bản cũ) ký tự; bản cũ có `the reference character` thì bản mới phải giữ."""
    cu = str(than or "").strip()
    if goi is None or not cu:
        return ""
    try:
        tra = str(goi(LOI_NHAC_VIET_LAI.format(ghi_chu=ghi_chu or "- (no notes)", than=cu,
                                               loi_doc=" ".join(str(loi_doc or "").split())[:400])) or "")
    except Exception:  # noqa: BLE001 — viết lại hỏng: vòng sau vẽ lại bằng bản cũ (khoá mới)
        return ""
    tra = re.sub(r"^\s*(?:new\s+)?(?:scene\s+)?prompt\s*:\s*", "", tra.strip(), flags=re.I).strip("`\"' \n")
    tra = " ".join(tra.split())
    if not (40 <= len(tra) <= max(900, 2 * len(cu))) or tra == cu:
        return ""
    if "reference character" in cu.lower() and "reference character" not in tra.lower():
        return ""
    return tra


# ═══ SỔ ═══

class SoChon:
    """`<lượt>/_chon-anh.json` — một khoá cho mọi luồng ảnh của lượt; ghi tệp tạm rồi đổi tên."""

    def __init__(self, thu_muc_luot: str) -> None:
        self.duong = os.path.join(thu_muc_luot, TEP_SO)

    def _doc(self) -> Dict[str, Any]:
        try:
            with open(self.duong, "r", encoding="utf-8") as f:
                du = json.load(f)
            return du if isinstance(du, dict) else {}
        except (OSError, ValueError):
            return {}

    def lay(self, so_canh: Any) -> Dict[str, Any]:
        with _KHOA_SO:
            return dict(self._doc().get(str(so_canh)) or {})

    def dat(self, so_canh: Any, muc: Dict[str, Any]) -> None:
        with _KHOA_SO:
            du = self._doc()
            du[str(so_canh)] = muc
            tam = self.duong + ".tmp"
            try:
                with open(tam, "w", encoding="utf-8") as f:
                    json.dump(du, f, ensure_ascii=False, indent=1)
                os.replace(tam, self.duong)
            except OSError:  # sổ hỏng không làm hỏng ảnh — lần sau chỉ mất phần dùng lại
                pass

    def tat_ca(self) -> Dict[str, Any]:
        with _KHOA_SO:
            return self._doc()


def _la_dung(loi: BaseException) -> bool:
    """Người bấm Dừng (`core.auto.Cancelled`) — phải ném lên, không được nuốt thành "vòng hỏng"."""
    return type(loi).__name__ == "Cancelled"


def _vong_dung_lai(cu: Dict[str, Any], vong: int, bam: str) -> Optional[Dict[str, Any]]:
    """Vòng `vong` đã làm ở lượt trước với CÙNG lời nhắc và tệp còn đủ → dùng lại."""
    for v in cu.get("vong") or []:
        if int(v.get("vong", -1)) == vong and v.get("bam") == bam:
            tep = [t for t in v.get("tep") or [] if t and os.path.isfile(t)]
            if tep and len(tep) == len(v.get("tep") or []):
                return v
    return None


def chon_canh(*, so_canh: int, prompt: str, loi_doc: str, ve: Callable[[str, int], Any],
              cham: Callable[[List[str], str], Optional[Dict[int, Dict[str, Any]]]],
              viet_lai: Optional[Callable[[str, str], str]] = None, so: Optional[SoChon] = None,
              nguong: float = NGUONG_DAT, so_vong: int = SO_VONG_VIET_LAI, ghi: Callable[[str], None] = print,
              kiem_dung: Optional[Callable[[], None]] = None,
              kiem_cuoi: Optional[Callable[[List[str], str], Dict[str, Any]]] = None,
              nguong_cuoi: float = 7.0) -> Dict[str, Any]:
    """Chọn ảnh tốt nhất cho MỘT cảnh. Trả bản ghi của cảnh (cũng là thứ ghi vào sổ):

        {"prompt_goc", "bam_goc", "vong": [{vong, prompt, bam, tep, cham{so: …}}], "chon": {tep, vong, so, tong,
         kinh_di, prompt}, "canh_bao": str, "so_anh": int, "so_cham": int, "xong": True}

    `ve(prompt, vong)` vẽ N ứng viên → danh sách tệp, hoặc (tệp, lời nhắc thật đã dùng) (ném lỗi = vòng ấy hỏng). `cham(tệp, prompt)` → {số tấm: mục}
    như `doc_cham` (None/{} = không chấm được). `viet_lai(prompt, ghi_chú)` → lời nhắc mới ("" = không đổi được).
    Vòng 0 hỏng thì NÉM (nơi gọi lo như mọi lỗi tạo ảnh); vòng sau hỏng thì giữ tấm tốt nhất đã có.

    `kiem_cuoi(tệp top-3, khoảnh khắc)` (Claude Max kiểm cuối, `core/kiem_max_anh.py`): gọi khi ví đã hài lòng (hoặc
    hết vòng) → {"ok", "tot" (chỉ số trong top-3), "tong" (thang mù), "ung_vien", "sua"} hoặc {"ok": False, "ly_do"}.
    Max < `nguong_cuoi` mà còn vòng → viết lại rồi Max kiểm lại; Max không dùng được → giữ lựa chọn của ví, ghi
    `max_bo_qua`. Tấm chọn cuối: tấm Max chấm cao nhất (Max là trọng tài) nếu có, không thì xếp hạng của ví."""
    bam_goc = _bam(prompt)
    cu = so.lay(so_canh) if so is not None else {}
    if cu.get("bam_goc") != bam_goc and cu.get("bam_chon") != bam_goc:
        cu = {}
    ghi_lai = {"prompt_goc": prompt, "bam_goc": bam_goc, "vong": [], "so_anh": int(cu.get("so_anh") or 0),
               "so_cham": int(cu.get("so_cham") or 0), "luc": time.time()}
    ung_vien: List[Dict[str, Any]] = []
    hien = prompt
    canh_bao = ""
    for vong in range(max(0, int(so_vong)) + 1):
        if kiem_dung is not None:
            kiem_dung()
        bam = _bam(hien)
        v = _vong_dung_lai(cu, vong, bam)
        if v is None:
            try:
                ra = ve(hien, vong)
                ra, dung = (ra if isinstance(ra, tuple) else (ra, hien))
                tep = [t for t in (ra or []) if t and os.path.isfile(t)]
            except Exception as loi:  # noqa: BLE001
                if vong == 0 or not ung_vien or _la_dung(loi):
                    raise
                canh_bao = "vòng {0} không vẽ được ({1}) — giữ tấm tốt nhất đã có".format(vong, str(loi)[:100])
                break
            if not tep:
                if vong == 0 or not ung_vien:
                    raise RuntimeError("ảnh cảnh {0}: máy vẽ không trả ứng viên nào".format(so_canh))
                canh_bao = "vòng {0} không ra ứng viên nào — giữ tấm tốt nhất đã có".format(vong)
                break
            # `prompt` = bản ĐƯA vào vòng (khớp sổ khi chạy tiếp); `dung` = bản THẬT đã vẽ (bộ lọc chặn → bản lành).
            v = {"vong": vong, "prompt": hien, "dung": str(dung or hien), "bam": bam, "tep": tep, "cham": None}
            ghi_lai["so_anh"] += len(tep)
        else:
            ghi("    ảnh cảnh {0}: vòng {1} có sẵn từ lượt trước — dùng lại.".format(so_canh, vong))
        hien = str(v.get("dung") or v.get("prompt") or hien)
        if not v.get("cham"):
            kq = None
            try:
                kq = cham(list(v["tep"]), hien)
            except Exception as loi:  # noqa: BLE001 — chấm hỏng không chặn ảnh
                if _la_dung(loi):
                    raise
                ghi("    ảnh cảnh {0}: giám khảo hỏng ({1}).".format(so_canh, str(loi)[:100]))
            ghi_lai["so_cham"] += 1
            v["cham"] = {str(k): m for k, m in (kq or {}).items()} or None
        ghi_lai["vong"].append(v)
        if so is not None:
            so.dat(so_canh, ghi_lai)
        for i, t in enumerate(v["tep"], 1):
            ung_vien.append({"tep": t, "vong": vong, "so": i, "prompt": hien,
                             "cham": (v.get("cham") or {}).get(str(i))})
        tot = xep_hang(ung_vien)[0]
        if not any(u.get("cham") for u in ung_vien):
            canh_bao = "giám khảo không chấm được — giữ ứng viên đầu"
            break
        can = can_viet_lai(tot, nguong)
        het_vong = vong >= int(so_vong)
        ghi_chu_max = ""
        if (not can or het_vong) and kiem_cuoi is not None and not ghi_lai.get("max_bo_qua"):
            km = _kiem_cuoi(kiem_cuoi, ung_vien, cu, ghi_lai, ghi, so_canh)
            if km.get("ok"):
                if float(km.get("tong") or 0) >= float(nguong_cuoi) and not km.get("horror"):
                    can = False
                else:
                    can = True
                    ghi_chu_max = "- final reviewer: best candidate only {0}/10 on the strict scale{1}{2}".format(
                        km.get("tong"), "; " + str(km.get("ly_do")) if km.get("ly_do") else "",
                        "; fix: " + str(km.get("sua")) if km.get("sua") else "")
            else:
                ghi_lai["max_bo_qua"] = str(km.get("ly_do") or "Claude Max không dùng được")
        if not can:
            break
        if het_vong:
            c = tot.get("cham") or {}
            mx = _tot_theo_max(ung_vien)
            canh_bao = "sau {0} vòng viết lại vẫn {1}/10{2}{3} — giữ tấm tốt nhất".format(
                so_vong, c.get("tong"), " (dính nét rợn: {0})".format(", ".join(c.get("dau_hieu") or []) or "có")
                if c.get("kinh_di") else "", " (Claude Max {0}/10)".format(mx["max"]["tong"]) if mx else "")
            break
        ghi_chu = ghi_chu_viet_lai([u for u in ung_vien if u["vong"] == vong])
        if ghi_chu_max:
            ghi_chu = ghi_chu + "\n" + ghi_chu_max
        # Chạy tiếp: vòng sau đã viết lại ở lượt trước (từ đúng vòng này) → dùng lại bản ấy, khỏi gọi AI lần hai.
        sau = [x for x in cu.get("vong") or [] if int(x.get("vong", -1)) == vong + 1 and x.get("prompt")]
        moi = str(sau[0]["prompt"]) if sau and _vong_dung_lai(cu, vong, bam) is not None else ""
        if not moi and viet_lai is not None:
            try:
                moi = str(viet_lai(hien, ghi_chu) or "").strip()
            except Exception as loi:  # noqa: BLE001
                if _la_dung(loi):
                    raise
                ghi("    ảnh cảnh {0}: viết lại lời nhắc hỏng ({1}).".format(so_canh, str(loi)[:100]))
        c = tot.get("cham") or {}
        ghi("    ảnh cảnh {0}: tốt nhất {1}/10{2} — {3}, vẽ vòng {4}…".format(
            so_canh, c.get("tong"), " (nét rợn)" if c.get("kinh_di") else "",
            "viết lại lời nhắc" if moi and moi != hien else "giữ lời nhắc", vong + 1))
        if moi:
            hien = moi
    mx = _tot_theo_max(ung_vien)
    tot = mx or xep_hang(ung_vien)[0]
    c = tot.get("cham") or {}
    ghi_lai["chon"] = {"tep": tot["tep"], "vong": tot["vong"], "so": tot["so"], "prompt": tot["prompt"],
                       "tong": c.get("tong"), "kinh_di": bool(c.get("kinh_di")), "diem": c.get("diem"),
                       "ly_do": c.get("ly_do", ""), "boi": "max" if mx else "vi",
                       "max_tong": (mx or {}).get("max", {}).get("tong"),
                       "max_doi": bool(mx) and mx["tep"] != xep_hang(ung_vien)[0]["tep"]}
    ghi_lai["bam_chon"] = _bam(tot["prompt"])
    ghi_lai["canh_bao"] = canh_bao
    ghi_lai["xong"] = True
    if so is not None:
        so.dat(so_canh, ghi_lai)
    return ghi_lai


def _tot_theo_max(ung_vien: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Tấm Claude Max chấm cao nhất (sạch trước, rồi điểm, rồi xếp hạng ví); không tấm nào có điểm Max → None."""
    co = [u for u in ung_vien if u.get("max")]
    if not co:
        return None
    hang = {id(u): i for i, u in enumerate(xep_hang(list(ung_vien)))}
    return sorted(co, key=lambda u: (bool(u["max"].get("horror")), -float(u["max"].get("tong") or 0),
                                     hang.get(id(u), 99)))[0]


def _kiem_cuoi(kiem_cuoi, ung_vien: List[Dict[str, Any]], cu: Dict[str, Any], ghi_lai: Dict[str, Any],
               ghi: Callable[[str], None], so_canh: int) -> Dict[str, Any]:
    """Gửi top-3 của ví cho Claude Max (dùng lại kết quả lượt trước nếu cùng bộ tệp), gắn điểm Max vào ứng viên."""
    top = [u for u in xep_hang(list(ung_vien)) if u.get("cham")][:3]
    tep = [u["tep"] for u in top]
    km = next((dict(x["kq"]) for x in cu.get("max") or [] if x.get("tep") == tep and (x.get("kq") or {}).get("ok")),
              None)
    if km is None:
        kk = next((str(u["cham"].get("khoanh_khac")) for u in top if u["cham"].get("khoanh_khac")), "")
        try:
            km = dict(kiem_cuoi(tep, kk) or {})
        except Exception as loi:  # noqa: BLE001 — Max hỏng: giữ lựa chọn của ví
            if _la_dung(loi):
                raise
            km = {"ok": False, "ly_do": "Claude Max lỗi ({0})".format(str(loi)[:100])}
    ghi_lai.setdefault("max", []).append({"tep": tep, "kq": km})
    if not km.get("ok"):
        ghi("    ảnh cảnh {0}: không kiểm cuối được bằng Claude Max ({1}) — giữ lựa chọn của ví.".format(
            so_canh, str(km.get("ly_do") or "")[:100]))
        return km
    for i, m in (km.get("ung_vien") or {}).items():
        if 0 <= int(i) < len(top):
            top[int(i)]["max"] = dict(m)
    tot = top[int(km.get("tot") or 0)] if 0 <= int(km.get("tot") or 0) < len(top) else top[0]
    km["ly_do"] = (tot.get("max") or {}).get("ly_do", "")
    ghi("    ảnh cảnh {0}: Claude Max chấm {1}/10 (tấm {2} vòng {3}){4}.".format(
        so_canh, km.get("tong"), tot["so"], tot["vong"], " — ĐỔI so với ví" if tot is not top[0] else ""))
    return km


def tom_tat(thu_muc_luot: str, nguong: float = NGUONG_DAT) -> Dict[str, Any]:
    """Tóm tắt sổ chọn ảnh của một lượt (hồ sơ video, não, báo cáo). Không có sổ → {}."""
    du = SoChon(thu_muc_luot).tat_ca()
    xong = [m for m in du.values() if isinstance(m, dict) and m.get("xong") and m.get("chon")]
    if not xong:
        return {}
    diem = [float(m["chon"]["tong"]) for m in xong if m["chon"].get("tong") is not None]
    dau = [max(float(x.get("tong") or 0) for x in m["vong"][0]["cham"].values())
           for m in xong if (m.get("vong") or [{}])[0].get("cham")]
    return {"so_canh": len(xong), "diem_tb": round(sum(diem) / len(diem), 2) if diem else None,
            "diem_tb_vong_dau": round(sum(dau) / len(dau), 2) if dau else None,
            "duoi_nguong": sum(1 for d in diem if d < nguong),
            "kinh_di": sum(1 for m in xong if m["chon"].get("kinh_di")),
            "viet_lai": sum(1 for m in xong if len(m.get("vong") or []) > 1),
            "thang_nho_viet_lai": sum(1 for m in xong if int(m["chon"].get("vong") or 0) > 0),
            "canh_bao": sum(1 for m in xong if m.get("canh_bao")),
            "so_anh": sum(int(m.get("so_anh") or 0) for m in xong),
            "so_cham": sum(int(m.get("so_cham") or 0) for m in xong),
            "max_kiem": sum(1 for m in xong if m["chon"].get("boi") == "max"),
            "max_doi": sum(1 for m in xong if m["chon"].get("max_doi")),
            "max_bo_qua": sum(1 for m in xong if m.get("max_bo_qua")),
            "max_tb": (lambda v: round(sum(v) / len(v), 2) if v else None)(
                [float(m["chon"]["max_tong"]) for m in xong if m["chon"].get("max_tong") is not None]),
            "luot_max": sum(len(m.get("max") or []) for m in xong)}
