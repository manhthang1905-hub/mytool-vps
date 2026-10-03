"""Chọn ảnh bìa bằng giám khảo AI — Việc 4 của
`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

═══ VÌ SAO CÓ TỆP NÀY ═══

Khâu ảnh bìa (`core/auto_khau._khau_thumbnail`) sinh `so_thumbnail` tấm
(`thumb_001.png`…) nhưng chưa từng ai CHỌN — `ban_giao_dang._tim_thumb` luôn
rơi về tấm đầu (`thumb_001`), nên trục học `thumbnail_ctr` không có biến
thiên: kênh nào cũng "chọn" đúng `portrait_main` mãi mãi, không phải vì nó
thắng mà vì nó đứng đầu danh sách.

`chon()` nhờ một giám khảo AI NHÌN ẢNH (không chỉ đọc lời nhắc) chấm từng tấm
so với: ảnh bìa đang thắng thật của kênh (nếu có, `core/khuon_bia.py`), vài
ảnh đã đăng gần đây (tránh lặp bố cục), tiêu đề/chữ bìa mong đợi. Tổng điểm
tính Ở MÁY theo trọng số cố định (không để AI tự cộng — dễ lệch), rồi xuất
`CHON-thumb_00N.jpg` mà `ban_giao_dang._tim_thumb` đã ưu tiên từ trước.

Không được phép CHẶN sản xuất: giám khảo hỏng (mạng rớt, JSON vỡ, quá tải)
thì rơi qua đường lùi 3 nấc (`_chon_duong_lui`), luôn ra một `CHON-*.jpg`.

`_kiem_loai` cũng LOẠI THẲNG ảnh có chữ đọc ra (`chu_doc_ra`) dài hơn `bia_toi_da_ky_tu`
(mặc định 14, không tính dấu câu/khoảng trắng) — thêm 29/09/2026, insight tâm lý Nhật
29/09/2026: khán giả thật 55+ (61%), 30% giờ xem trên TV, và 6/9 bìa gần đây của TL1-3 đã
vượt mốc này. Mọi ứng viên cùng bị loại thì vẫn phải ra MỘT tấm (không chặn sản xuất) —
`chon()` chọn tấm ÍT CHỮ NHẤT trong số đó và ghi cảnh báo (`ket_qua["chon"]["canh_bao"]`).
"""

from __future__ import annotations

import glob
import io
import json
import os
import random
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageOps

__all__ = ["UngVienBia", "chon", "duong_tep_chon_bia", "doc_chon_bia"]

TEN_TEP_KET_QUA = "chon-bia.json"

#: Trọng số CỐ ĐỊNH — mục "Ra JSON mỗi ảnh" bản thiết kế Việc 4. Tổng = 1.0.
#:
#: 30/09/2026 (bìa bám khuôn / chuẩn ngách, `core/bia_theo_khuon.py`): nghiên cứu 493
#: bìa đối thủ cho thấy GIỐNG khuôn không làm nên CTR (C432 cùng khuôn aV4 chỉ 4,04%),
#: nên `bam_khuon_thang` hạ 0,20 → 0,05 (bìa thắng giờ là CHUẨN SO SÁNH sức bấm, không
#: bắt giống); thêm `dung_chuan_ngach` 0,15 (chữ trần viền dày, vàng/trắng + từ khoá đỏ,
#: chữ 40–55% khung, tầng ≥18%/tầng chính ≥25%, không trống lớn, nền ấm/đủ tương phản).
#: Kênh không có khuôn / ngách không có chuẩn thì trọng số tương ứng CHIA LẠI như cũ.
TRONG_SO = {
    "suc_hut_click": 0.25, "bam_khuon_thang": 0.05, "doc_duoc_co_nho": 0.20,
    "hop_noi_dung": 0.15, "tuong_phan": 0.05, "cam_xuc": 0.10, "khac_video_gan_day": 0.05,
    "dung_chuan_ngach": 0.15,
}

#: Điểm số liệu cũ quá ngần này ngày thì hạ trọng số `bam_khuon_thang` một nửa
#: — khuôn từng thắng nhưng đo đã lâu, độ tin cậy giảm.
NGUONG_NGAY_KHUON_CU = 14

#: Số ký tự ĐỌC ĐƯỢC tối đa trên một ảnh bìa (đếm bằng `_chuan_hoa_chu` — không tính dấu câu/
#: khoảng trắng) trước khi bị LOẠI THẲNG — insight tâm lý Nhật 29/09/2026, mục 6 và "3 việc nên
#: làm ngay" #3: khán giả thật 55+ (61%), 30% giờ xem trên TV, và 6/9 bìa gần đây của TL1-3 đã
#: vượt mốc này (có bìa dán nguyên tiêu đề 43 ký tự). Gọi `chon()` với `bia_toi_da_ky_tu=` để
#: ghi đè theo kênh — nối vào cấu hình kênh (`kenh.yaml`) là việc của người gọi
#: (`core/auto_khau.py`, ngoài phạm vi sở hữu của tệp này), mặc định vẫn là hằng số dưới đây.
#: 30/09/2026 — điều phối nới 14 → 20 (mỗi tầng ≤12, tổng ≤20; bìa thắng aV4 = 8 + 10 = 18;
#: trung vị 493 bìa ngách = 17). Luật 14 cũ loại MỌI ứng viên ở 11/12 gói gần nhất, nên
#: bộ chọn chỉ còn "chọn tấm ít chữ nhất" — không còn là chọn.
NGUONG_KY_TU_BIA_MAC_DINH = 20

#: Kém hạng nhất không quá ngần này % thì được xét khám phá.
NGUONG_KHAM_PHA_PCT = 3.0

#: Kênh CHƯA có khuôn riêng (`không co_khuon_thang`) → nới ngưỡng khám phá rộng
#: hơn nhiều so với `NGUONG_KHAM_PHA_PCT` — mục tiêu là XOAY ĐỦ VÒNG các kiểu
#: KIEU_THUMB ít dùng nhất trong ~6-9 video để có đủ biến thiên CTR theo kiểu
#: (thăm dò CÓ CHỦ ĐÍCH, không phải ngẫu nhiên) — thêm 30/09/2026, Việc 4b.
NGUONG_KHAM_PHA_PCT_CHUA_CO_KHUON_RIENG = 20.0

#: Ảnh xuất ra — trần dung lượng và kích thước chuẩn YouTube.
KICH_THUOC_XUAT = (1280, 720)
TRAN_DUNG_LUONG = 2 * 1024 * 1024

_CHU_A_G = "ABCDEFG"
_RE_THUMB_SO = re.compile(r"thumb_(\d+)\.", re.IGNORECASE)


@dataclass
class UngVienBia:
    so: int
    duong: str
    kieu: str = ""


@dataclass
class _KetQuaCham:
    so: int
    diem: Dict[str, float] = field(default_factory=dict)
    chu_doc_ra: str = ""
    loi_nang: List[str] = field(default_factory=list)
    ly_do: str = ""
    tong: float = 0.0
    loai: str = ""  # lý do bị loại thẳng, rỗng = không loại


def duong_tep_chon_bia(thu_muc_thumb: str) -> str:
    return os.path.join(thu_muc_thumb, TEN_TEP_KET_QUA)


def doc_chon_bia(thu_muc_thumb: str) -> Optional[Dict[str, Any]]:
    try:
        with io.open(duong_tep_chon_bia(thu_muc_thumb), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return None
    return du if isinstance(du, dict) else None


def _ghi_json(duong: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)


def _ung_vien_trong_thu_muc(thu_muc_thumb: str, ten_kieu_theo_so: Dict[int, str]) -> List[UngVienBia]:
    ra: List[UngVienBia] = []
    try:
        ten = sorted(os.listdir(thu_muc_thumb))
    except OSError:
        return ra
    for t in ten:
        if t.upper().startswith("CHON-"):
            continue
        if os.path.splitext(t)[1].lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        m = _RE_THUMB_SO.match(t)
        if not m:
            continue
        so = int(m.group(1))
        ra.append(UngVienBia(so=so, duong=os.path.join(thu_muc_thumb, t),
                             kieu=ten_kieu_theo_so.get(so, "")))
    ra.sort(key=lambda u: u.so)
    return ra


def _da_co_chon_cua_nguoi(thu_muc_thumb: str) -> str:
    """Tên tệp `CHON-*` đã có sẵn (người tự chọn tay) — rỗng nếu chưa ai chọn."""
    try:
        ten = sorted(os.listdir(thu_muc_thumb))
    except OSError:
        return ""
    for t in ten:
        if t.upper().startswith("CHON-") and os.path.splitext(t)[1].lower() in (
                ".jpg", ".jpeg", ".png", ".webp"):
            return t
    return ""


# ── Dựng tấm ghép cỡ điện thoại (nhãn A-G) ────────────────────────────────────


def _tam_ghep(ung_vien: Sequence[UngVienBia], nhan_theo_so: Dict[int, str],
             o: Tuple[int, int] = (168, 94), cot: int = 3) -> Optional[bytes]:
    """Ghép mọi ứng viên thành MỘT ảnh 3×n ô `o`, mỗi ô đóng khung nhãn A-G ở
    góc trên trái — giám khảo nhìn một tấm là thấy hết, đúng như người chọn
    thật nhìn trên MÀN HÌNH ĐIỆN THOẠI (ảnh bìa cỡ thật rất nhỏ trên đó)."""
    anh_mo: List[Tuple[str, Image.Image]] = []
    for u in ung_vien:
        try:
            anh_mo.append((nhan_theo_so.get(u.so, "?"), Image.open(u.duong).convert("RGB")))
        except (OSError, ValueError):
            continue
    if not anh_mo:
        return None
    hang = (len(anh_mo) + cot - 1) // cot
    dem = 6
    rong, cao = o
    tam = Image.new("RGB", (cot * rong + (cot + 1) * dem, hang * cao + (hang + 1) * dem), "white")
    ve = ImageDraw.Draw(tam)
    for i, (nhan, im) in enumerate(anh_mo):
        r, h = i % cot, i // cot
        x = dem + r * (rong + dem)
        y = dem + h * (cao + dem)
        tam.paste(ImageOps.fit(im, (rong, cao)), (x, y))
        ve.rectangle([x, y, x + 20, y + 16], fill=(255, 221, 0))
        ve.text((x + 5, y + 2), nhan, fill=(0, 0, 0))
    buf = io.BytesIO()
    tam.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _data_url_bytes(du_lieu: bytes, media: str = "image/jpeg") -> str:
    import base64  # noqa: PLC0415
    return "data:{0};base64,{1}".format(media, base64.b64encode(du_lieu).decode())


def _data_url_tep(duong: str) -> str:
    from .cham_anh import data_url  # noqa: PLC0415
    return data_url(duong)


# ── Lời nhắc giám khảo ─────────────────────────────────────────────────────


_LOI_NHAC_GIAM_KHAO = """You are judging YouTube thumbnail candidates for a channel, as a viewer \
scrolling on a PHONE — thumbnails are shown TINY, so only what reads at a glance matters.

IMAGE 1 is a grid of every candidate, each tile labelled A-G in its top-left corner. This is the \
main thing you are judging — look at it the way a phone viewer would, from a normal scrolling \
distance, not zoomed in.
{anh_them}

Video title: {tieu_de}
Expected thumbnail text (must appear, verbatim if the channel copies a competitor): {chu_bia}
Video opening (for context, judge whether the thumbnail's implied promise matches this content): \
{mo_dau}
{khuon_thang_khoi}
{chuan_ngach_khoi}
{gan_day_khoi}

For EACH labelled tile (use exactly the labels you see, one entry per tile), score 0-10 on:
- suc_hut_click: would a scrolling phone viewer stop and tap this over neighbouring videos?
- doc_duoc_co_nho: is the text readable and memorable at THUMBNAIL SIZE (tiny, blurry edges)?
- tuong_phan: contrast between subject/text and background — does it pop out of a feed?
- cam_xuc: does the expression/composition carry a clear, single emotion? The character must be BIG — at \
least ~30% of the frame height with a face whose expression reads at phone size; a tiny figure lost in the \
scene (under ~20% of the frame height) scores 3 or less.
- hop_noi_dung: does the promise implied by the text/image actually match the video content \
described above? Penalise a thumbnail that implies something the video does not deliver.
- bam_khuon_thang: 0 if no winning template was given above; otherwise how closely this tile \
matches that template's layout/colour/text placement (NOT literal wording).
- dung_chuan_ngach: 0 if no niche standard was given above; otherwise how fully the tile meets it \
(bare outlined text, yellow/white with a red key word, text covering ~40-55% of the frame, every \
text tier at least ~18% of the frame height and the main tier at least ~25%, no big empty areas, \
a warm or high-contrast background — never pale grey; an expressive character at least ~30% of the frame \
height).
- khac_video_gan_day: does this avoid repeating the layout of the recent thumbnails shown?

Also report per tile: "chu_doc_ra" (the text you can actually read on it, empty if none), and \
"loi_nang" — a list of strings from this fixed set ONLY, whichever apply: "sai_chu" (readable \
text does not match the expected text above), "chu_vo" (text broken/overlapping/unreadable), \
"nhan_vat_di_dang" (a character/face is deformed or has extra/missing limbs), "anh_that" (a REAL \
person, a photograph or a photo-realistic human/face anywhere in the tile, even in the background — the \
channel only uses drawn illustration).

Return JSON only:
{{"cac_anh": [{{"nhan": "A", "diem": {{"suc_hut_click": 0, "doc_duoc_co_nho": 0, "tuong_phan": 0, \
"cam_xuc": 0, "hop_noi_dung": 0, "bam_khuon_thang": 0, "khac_video_gan_day": 0, \
"dung_chuan_ngach": 0}}, \
"chu_doc_ra": "", "loi_nang": [], "ly_do": "one short sentence"}}, ...]}}"""


def _dung_loi_nhac(tieu_de: str, chu_bia: str, mo_dau: str, khuon_thang: Optional[Dict[str, Any]],
                   co_anh_gan_day: bool, chuan_ngach_khoi: str = "") -> str:
    khuon_khoi = ""
    if khuon_thang and khuon_thang.get("khuon_chu"):
        kc = khuon_thang["khuon_chu"]
        # 30/09/2026 — bìa thắng là CHUẨN SO SÁNH SỨC BẤM (ảnh THẬT trên YouTube).
        khuon_khoi = ("IMAGE 2 is the channel's CURRENT winning thumbnail, as live on YouTube (real "
                     "CTR {0:.2f}% on {4:.0f} impressions). Use it as the BENCHMARK: prefer the tile "
                     "whose click-pull on a TV / phone home feed comes closest to it (score "
                     "suc_hut_click against it). Resemblance is not required. Its template: "
                     "bo_cuc={1}; mau_sac={2}; vi_tri_chu={3}.".format(
                         khuon_thang.get("ctr") or 0.0, kc.get("bo_cuc", ""),
                         kc.get("mau_sac", ""), kc.get("vi_tri_chu", ""),
                         float(khuon_thang.get("imp") or 0)))
        if khuon_thang.get("chi_hoc_bo_cuc"):
            khuon_khoi += (" NOTE: that video's high CTR came with LOW retention — when scoring "
                          "hop_noi_dung, do not reward candidates for copying its IMPLIED PROMISE, "
                          "only its layout/colour.")
    gan_day_khoi = ("The following image(s) are thumbnails this channel used RECENTLY — avoid "
                    "rewarding a layout that repeats them." if co_anh_gan_day else "")
    anh_them = "IMAGE 2 is the winning template above." if khuon_khoi else ""
    return _LOI_NHAC_GIAM_KHAO.format(
        anh_them=anh_them, tieu_de=tieu_de or "", chu_bia=chu_bia or "",
        mo_dau=(mo_dau or "")[:600], khuon_thang_khoi=khuon_khoi,
        chuan_ngach_khoi=chuan_ngach_khoi or "", gan_day_khoi=gan_day_khoi)


# ── Một lượt chấm (giám khảo nhìn ảnh) ────────────────────────────────────────


def _mot_luot_cham(goi_chat: Callable[..., str], ung_vien: Sequence[UngVienBia],
                   *, tieu_de: str, chu_bia: str, mo_dau: str,
                   khuon_thang: Optional[Dict[str, Any]], anh_gan_day: Sequence[str],
                   mo_hinh: str, khoa: str, rng: random.Random,
                   chuan_ngach_khoi: str = "") -> Dict[int, _KetQuaCham]:
    """Một lượt chấm — nhãn A-G GÁN NGẪU NHIÊN cho từng ứng viên (đảo lộn thứ
    tự vị trí thật), trả `{so_ứng_viên: _KetQuaCham}`."""
    thu_tu = list(ung_vien)
    rng.shuffle(thu_tu)
    nhan_theo_so = {u.so: _CHU_A_G[i] for i, u in enumerate(thu_tu)}
    so_theo_nhan = {nhan: so for so, nhan in nhan_theo_so.items()}

    anh_ghep = _tam_ghep(ung_vien, nhan_theo_so)
    if not anh_ghep:
        return {}
    cac_anh_data_url = [_data_url_bytes(anh_ghep)]
    if khuon_thang and khuon_thang.get("tep") and os.path.isfile(khuon_thang["tep"]):
        cac_anh_data_url.append(_data_url_tep(khuon_thang["tep"]))
    for d in anh_gan_day[:3]:
        if os.path.isfile(d):
            cac_anh_data_url.append(_data_url_tep(d))

    loi_nhac = _dung_loi_nhac(tieu_de, chu_bia, mo_dau, khuon_thang, bool(anh_gan_day),
                              chuan_ngach_khoi)
    tra_loi = goi_chat(loi_nhac, mo_hinh=mo_hinh, khoa=khoa, toi_da_token=2000,
                       anh=cac_anh_data_url)
    from .goi_van_ban import loc_json  # noqa: PLC0415
    du = loc_json(str(tra_loi or ""))
    cac_anh = du.get("cac_anh") if isinstance(du, dict) else None
    ra: Dict[int, _KetQuaCham] = {}
    for m in (cac_anh or []):
        if not isinstance(m, dict):
            continue
        nhan = str(m.get("nhan") or "").strip().upper()[:1]
        so = so_theo_nhan.get(nhan)
        if so is None:
            continue
        diem_tho = m.get("diem") if isinstance(m.get("diem"), dict) else {}
        diem = {}
        for khoa_diem in TRONG_SO:
            try:
                diem[khoa_diem] = max(0.0, min(10.0, float(diem_tho.get(khoa_diem, 0))))
            except (TypeError, ValueError):
                diem[khoa_diem] = 0.0
        ra[so] = _KetQuaCham(
            so=so, diem=diem, chu_doc_ra=str(m.get("chu_doc_ra") or "").strip(),
            loi_nang=[str(x) for x in (m.get("loi_nang") or []) if x],
            ly_do=str(m.get("ly_do") or "").strip()[:300])
    return ra


# ── Tổng điểm + luật loại ────────────────────────────────────────────────────


def _chuan_hoa_chu(chu: str) -> str:
    return re.sub(r"[\s\W_]+", "", (chu or "").lower())


def _tong_diem(diem: Dict[str, float], *, co_khuon_thang: bool, khuon_cu: bool,
               co_chuan_ngach: bool = False) -> float:
    trong_so = dict(TRONG_SO)
    if khuon_cu:
        trong_so["bam_khuon_thang"] /= 2.0
    bo_di = ([] if co_khuon_thang else ["bam_khuon_thang"]) + ([] if co_chuan_ngach else ["dung_chuan_ngach"])
    for khoa_bo in bo_di:
        bo = trong_so.pop(khoa_bo)
        tong_con_lai = sum(trong_so.values())
        if tong_con_lai > 0:
            for k in trong_so:
                trong_so[k] += bo * (trong_so[k] / tong_con_lai)
    return sum(diem.get(k, 0.0) * w for k, w in trong_so.items()) / 10.0 * 100.0


def _dung_chinh_ta(chu_doc_ra: str, chu_mong: str) -> bool:
    """Máy so chính tả: chữ dự kiến (bỏ dấu câu/khoảng trắng) phải nằm TRỌN trong chữ
    giám khảo đọc ra, thừa tối đa 1 ký tự (chữ lạc trên đạo cụ, ký tự lặp 「使使う」…)."""
    doc, mong = _chuan_hoa_chu(chu_doc_ra), _chuan_hoa_chu(chu_mong)
    if not mong:
        return True
    return mong in doc and len(doc) - len(mong) <= 1


def _kiem_loai(ket: _KetQuaCham, *, chu_bia_mong_doi: str, doi_chieu_chu: bool,
               toi_da_ky_tu: int = NGUONG_KY_TU_BIA_MAC_DINH) -> str:
    """Lý do LOẠI THẲNG một ứng viên — rỗng nếu hợp lệ.

    Luật chữ quá dài (thêm 29/09/2026) áp dụng KHÔNG ĐIỀU KIỆN, khác luật "sai chữ" bên dưới
    (chỉ bật khi `doi_chieu_chu`/`chu_bia_co_dinh`): độ dài chữ là chuyện ĐỌC ĐƯỢC trên màn
    hình TV/điện thoại của khán giả 55+, không phải chuyện khớp/không khớp với một chữ bìa
    mong đợi cụ thể — bìa nào cũng phải qua được ngưỡng này bất kể kênh có cố định chữ hay không.
    """
    loi = set(ket.loi_nang)
    if "chu_vo" in loi:
        return "chữ vỡ"
    if "nhan_vat_di_dang" in loi:
        return "nhân vật dị dạng"
    if "anh_that" in loi:  # 01/10/2026: TL3-0015 — người chụp kiểu ảnh thật ở nền, lạc phong cách kênh
        return "người thật / ảnh chụp"
    if toi_da_ky_tu and ket.chu_doc_ra:
        so_ky_tu = len(_chuan_hoa_chu(ket.chu_doc_ra))
        if so_ky_tu > toi_da_ky_tu:
            return "chữ quá dài ({0} > {1} ký tự)".format(so_ky_tu, toi_da_ky_tu)
    if doi_chieu_chu and chu_bia_mong_doi and ket.chu_doc_ra:
        if "sai_chu" in loi or (_chuan_hoa_chu(ket.chu_doc_ra) != _chuan_hoa_chu(chu_bia_mong_doi)
                                and _chuan_hoa_chu(chu_bia_mong_doi) not in _chuan_hoa_chu(ket.chu_doc_ra)):
            return "sai chữ"
    return ""


# ── Xuất jpg ≤2MB 1280×720 ────────────────────────────────────────────────────


def _xuat_jpg(nguon: str, dich: str) -> bool:
    try:
        im = Image.open(nguon).convert("RGB")
    except (OSError, ValueError):
        return False
    im = ImageOps.fit(im, KICH_THUOC_XUAT, method=Image.LANCZOS)
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    tam = dich + ".tmp"
    chat_luong = 92
    while chat_luong >= 40:
        im.save(tam, format="JPEG", quality=chat_luong)
        if os.path.getsize(tam) < TRAN_DUNG_LUONG or chat_luong <= 40:
            break
        chat_luong -= 8
    os.replace(tam, dich)
    return True


# ── Đường lùi (API hỏng) ──────────────────────────────────────────────────────


def _chon_duong_lui(goc: str, kenh: str, ung_vien: Sequence[UngVienBia],
                    khuon_thang: Optional[Dict[str, Any]]) -> Tuple[UngVienBia, str]:
    """3 nấc, KHÔNG BAO GIỜ ném lỗi — luôn trả về một ứng viên.

    1) Bài học `thumbnail_ctr` độ tin cậy ≥ "vừa" → kiểu CTR cao nhất kiểu đó.
    2) Không có/độ tin cậy thấp → kiểu `khuon_thang` nếu có trong ứng viên.
    3) Không có nốt → luật Pillow thô ở cỡ 168×94 (độ lệch chuẩn sáng + bão
       hoà + mật độ cạnh — ưu tiên tấm "nổi" nhất khi thu nhỏ).
    """
    try:
        from . import bai_hoc_san_xuat as _bh  # noqa: PLC0415
        for bh in _bh.doc_bai_hoc(goc, kenh):
            if bh.truc == "thumbnail_ctr" and bh.cum == "" and bh.do_tin_cay in ("vua", "cao"):
                kieu_thang = bh.quan_sat.split(":", 1)[0].strip()
                for u in ung_vien:
                    if u.kieu == kieu_thang:
                        return u, "đường lùi 1 — bài học sản xuất: kiểu {0} CTR cao nhất".format(kieu_thang)
    except Exception:  # noqa: BLE001
        pass

    if khuon_thang:
        for u in ung_vien:
            if u.kieu == "khuon_thang":
                return u, "đường lùi 2 — dùng đúng kiểu khuôn ảnh thắng"

    def _diem_tho(u: UngVienBia) -> float:
        try:
            im = ImageOps.fit(Image.open(u.duong).convert("HSV"), (168, 94))
            *_, v = im.split()
            gia_tri = list(v.getdata())
            do_lech = statistics.pstdev(gia_tri) if len(gia_tri) > 1 else 0.0
            h, s, _v2 = im.split()
            do_bao_hoa = statistics.mean(list(s.getdata()))
            return do_lech + do_bao_hoa * 0.3
        except Exception:  # noqa: BLE001
            return 0.0

    best = max(ung_vien, key=_diem_tho)
    return best, "đường lùi 3 — luật Pillow thô (tương phản/bão hoà cao nhất khi thu nhỏ)"


# ── API chính ─────────────────────────────────────────────────────────────────


def chon(goc: str, kenh: str, thu_muc_thumb: str, *, ten_kieu_theo_so: Dict[int, str],
         tieu_de: str = "", chu_bia: str = "", chu_bia_co_dinh: bool = False,
         mo_dau_kich_ban: str = "", ma_goi: str = "",
         goi_chat: Optional[Callable[..., str]] = None,
         so_luot_cham: int = 2, mo_hinh: str = "", kham_pha_bat: bool = True,
         khoa: str = "", log: Optional[Callable[[str], None]] = None,
         seed: Optional[int] = None,
         bia_toi_da_ky_tu: int = NGUONG_KY_TU_BIA_MAC_DINH,
         nhom_theo_so: Optional[Dict[int, str]] = None,
         chu_theo_so: Optional[Dict[int, str]] = None,
         nhom_uu_tien: Optional[str] = None,
         chuan_ngach_khoi: str = "",
         luot_tham_do: bool = False) -> Optional[Dict[str, Any]]:
    """Chọn MỘT ảnh bìa trong `thu_muc_thumb`, xuất `CHON-thumb_00N.jpg` +
    `chon-bia.json`. Trả bản ghi lựa chọn, hoặc `None` khi không có ứng viên
    nào (thư mục trống). KHÔNG BAO GIỜ ném lỗi ra ngoài.

    Đã có `CHON-*` sẵn (người tự chọn tay) → GIỮ NGUYÊN, không chấm lại, trả
    bản ghi tối giản đánh dấu `chon_boi: "nguoi"`.

    30/09/2026 (`core/bia_theo_khuon.py`): `nhom_theo_so` (khuon | chuan_ngach |
    tham_do), `chu_theo_so` (chữ bìa DỰ KIẾN của từng tấm — máy so chính tả: tấm
    nào mọi lượt chấm đều đọc ra chữ khác thì LOẠI "sai chính tả"), `nhom_uu_tien`
    (nhóm A/B tất định của video này — chọn tấm tốt nhất TRONG nhóm; cả nhóm hỏng
    thì lấy tấm tốt nhất còn lại), `chuan_ngach_khoi` (chuẩn ngách cho giám khảo).
    """
    nhom_theo_so = dict(nhom_theo_so or {})
    chu_theo_so = dict(chu_theo_so or {})
    def ghi(dong: str) -> None:
        if log is not None:
            log(dong)

    da_co = _da_co_chon_cua_nguoi(thu_muc_thumb)
    if da_co:
        return {"so": None, "tep": da_co, "chon_boi": "nguoi", "ly_do": "đã có CHON- sẵn — giữ nguyên"}

    ung_vien = _ung_vien_trong_thu_muc(thu_muc_thumb, ten_kieu_theo_so)
    if not ung_vien:
        return None

    # Đọc TRƯỚC vòng `try` chính: nhánh lùi (`except` bên dưới) cũng cần biến
    # này, và phải LUÔN có giá trị (kể cả khi đọc khuôn hỏng) chứ không được
    # phụ thuộc việc vòng `try` chạy tới đâu mới gán.
    khuon_thang: Optional[Dict[str, Any]] = None
    try:
        from . import khuon_bia  # noqa: PLC0415
        khuon_thang = khuon_bia.doc_khuon(goc, kenh)
        if khuon_thang and khuon_thang.get("het_hieu_luc"):
            khuon_thang = None
    except Exception:  # noqa: BLE001
        khuon_thang = None

    try:
        anh_gan_day = _anh_da_dang_gan_day(goc, kenh, loai_tru_ma_goi=ma_goi)

        if goi_chat is None:
            raise RuntimeError("không có goi_chat — dùng đường lùi")

        rng = random.Random(seed)
        theo_so: Dict[int, List[_KetQuaCham]] = {u.so: [] for u in ung_vien}
        for lan in range(max(1, so_luot_cham)):
            ket_lan = _mot_luot_cham(
                goi_chat, ung_vien, tieu_de=tieu_de, chu_bia=chu_bia, mo_dau=mo_dau_kich_ban,
                khuon_thang=khuon_thang, anh_gan_day=anh_gan_day, mo_hinh=mo_hinh,
                khoa="{0}:{1}".format(khoa or "chon-bia", lan), rng=rng,
                chuan_ngach_khoi=chuan_ngach_khoi)
            for so, k in ket_lan.items():
                theo_so.setdefault(so, []).append(k)

        khuon_cu = False
        if khuon_thang and khuon_thang.get("ngay_so_lieu"):
            try:
                import datetime as _dt  # noqa: PLC0415
                ngay = _dt.date.fromisoformat(str(khuon_thang["ngay_so_lieu"])[:10])
                khuon_cu = (_dt.date.today() - ngay).days > NGUONG_NGAY_KHUON_CU
            except ValueError:
                pass

        ung_cu_vien: List[_KetQuaCham] = []
        for u in ung_vien:
            lan_cham = theo_so.get(u.so) or []
            if not lan_cham:
                continue
            diem_tb = {k: statistics.mean(k_.diem.get(k, 0.0) for k_ in lan_cham) for k in TRONG_SO}
            tong = _tong_diem(diem_tb, co_khuon_thang=bool(khuon_thang), khuon_cu=khuon_cu,
                              co_chuan_ngach=bool(chuan_ngach_khoi))
            loai = ""
            chu_tam = chu_theo_so.get(u.so, "")
            for k_ in lan_cham:
                loai = _kiem_loai(k_, chu_bia_mong_doi=chu_tam or chu_bia,
                                  doi_chieu_chu=chu_bia_co_dinh and not chu_tam,
                                  toi_da_ky_tu=bia_toi_da_ky_tu)
                if loai:
                    break
            if not loai and chu_tam and all(not _dung_chinh_ta(k_.chu_doc_ra, chu_tam) for k_ in lan_cham):
                loai = "sai chính tả (máy so với chữ dự kiến: {0})".format(chu_tam)
            ung_cu_vien.append(_KetQuaCham(
                so=u.so, diem=diem_tb, tong=tong, loai=loai,
                chu_doc_ra=lan_cham[0].chu_doc_ra,
                ly_do="; ".join(sorted({k_.ly_do for k_ in lan_cham if k_.ly_do}))[:400]))

        if not ung_cu_vien:
            raise RuntimeError("giám khảo không trả điểm cho ứng viên nào")

        canh_bao = ""
        he_tu_hoc: Dict[str, Any] = {}
        if all(k.loai for k in ung_cu_vien):
            # Mọi ứng viên đều bị loại (chữ quá dài/sai/vỡ/nhân vật dị dạng) — luật "không
            # chặn sản xuất" vẫn buộc phải ra MỘT tấm. Chọn tấm ÍT CHỮ NHẤT thay vì tấm điểm
            # giám khảo cao nhất: điểm cao có thể đến từ một tấm dán nguyên tiêu đề (đã thấy
            # thật ở TL1-0007, 43 ký tự) — giữa các phương án xấu, tấm ít chữ còn có cơ đọc
            # được trên TV/điện thoại. Ghi CẢNH BÁO ra log + JSON, không ném lỗi.
            hop_le = sorted(ung_cu_vien, key=lambda k: len(_chuan_hoa_chu(k.chu_doc_ra)))
            thang = hop_le[0]
            chon_boi = "ai"
            so_ky_tu_thang = len(_chuan_hoa_chu(thang.chu_doc_ra))
            canh_bao = ("mọi ứng viên đều bị loại ({0}) — chọn tấm ÍT CHỮ NHẤT ({1} ký tự) làm "
                       "phương án dự phòng, không chặn sản xuất").format(thang.loai, so_ky_tu_thang)
            ly_do_chon = canh_bao
            ghi("  (!) ảnh bìa: MỌI ứng viên đều bị loại ({0}) — chọn tấm ít chữ nhất ({1} ký tự) "
               "làm dự phòng.".format(thang.loai, so_ky_tu_thang))
        else:
            hop_le = [k for k in ung_cu_vien if not k.loai]
            hop_le.sort(key=lambda k: -k.tong)
            # Tự học (đợt 2): nhân điểm với 0,9 + 0,2 × Thompson của KIỂU bìa rồi xếp lại. Chỉ nắn thứ tự hạng
            # (A/B nhóm khuôn ở dưới vẫn chạy y cũ); trục chưa có ván kết luận thì không làm gì.
            try:
                from . import tu_hoc  # noqa: PLC0415

                kieu_ds = [ten_kieu_theo_so.get(k_.so, "") for k_ in hop_le]
                he = tu_hoc.he_so_chon(goc, kenh, "kieu_bia", kieu_ds, "kb|{0}|{1}".format(kenh, ma_goi))
                if he:
                    sau = sorted(hop_le, key=lambda k_: -k_.tong * he.get(ten_kieu_theo_so.get(k_.so, ""), 1.0))
                    he_tu_hoc = {"truc": "kieu_bia", "he_so": he, "doi_hang": sau[0].so != hop_le[0].so,
                                 "diem_sau": {str(k_.so): round(k_.tong * he.get(ten_kieu_theo_so.get(k_.so, ""), 1.0), 2)
                                              for k_ in hop_le}}
                    hop_le = sau
            except Exception:  # noqa: BLE001 — học hỏng không được làm hỏng chọn bìa
                he_tu_hoc = {}
            thang = hop_le[0]
            chon_boi = "ai"
            ly_do_chon = thang.ly_do or "điểm tổng cao nhất"
            if nhom_uu_tien:
                trong_nhom = [k for k in hop_le if nhom_theo_so.get(k.so) == nhom_uu_tien]
                if trong_nhom:
                    thang = trong_nhom[0]
                    ly_do_chon = "nhóm {0} (A/B{1}) — {2}".format(
                        nhom_uu_tien, ", lượt thăm dò" if luot_tham_do else "", thang.ly_do or "điểm cao nhất nhóm")
                else:
                    ly_do_chon = ("nhóm {0} không còn tấm hợp lệ (sai chữ/chữ vỡ/nhân vật hỏng) — lấy "
                                 "tấm tốt nhất còn lại: {1}").format(nhom_uu_tien, thang.ly_do or "")

            if kham_pha_bat and len(hop_le) >= 2 and not nhom_uu_tien:
                nhi = hop_le[1]
                nguong_kham_pha = (NGUONG_KHAM_PHA_PCT if khuon_thang
                                  else NGUONG_KHAM_PHA_PCT_CHUA_CO_KHUON_RIENG)
                if thang.tong - nhi.tong <= nguong_kham_pha:
                    kieu_thang = ten_kieu_theo_so.get(thang.so, "")
                    kieu_nhi = ten_kieu_theo_so.get(nhi.so, "")
                    if kieu_nhi and kieu_nhi != kieu_thang and _kieu_it_dung_hon(
                            goc, kenh, kieu_nhi, kieu_thang):
                        thang = nhi
                        chon_boi = "kham_pha"
                        if khuon_thang:
                            ly_do_chon = ("khám phá — kiểu {0} ít dùng hơn, kém hạng nhất "
                                         "{1:.1f} điểm").format(kieu_nhi, hop_le[0].tong - nhi.tong)
                        else:
                            ly_do_chon = ("khám phá có chủ đích — kênh chưa có khuôn riêng, thử "
                                         "kiểu {0} (ít dùng hơn, kém hạng nhất {1:.1f} điểm)").format(
                                kieu_nhi, hop_le[0].tong - nhi.tong)

        u_thang = next(u for u in ung_vien if u.so == thang.so)
        tep_dich = os.path.join(thu_muc_thumb, "CHON-thumb_{0:03d}.jpg".format(thang.so))
        if not _xuat_jpg(u_thang.duong, tep_dich):
            raise RuntimeError("xuất jpg hỏng")

        ket_qua = {
            "chon": {"so": thang.so, "kieu": u_thang.kieu, "tong_diem": round(thang.tong, 1),
                    "chon_boi": chon_boi, "ly_do": ly_do_chon, "chu_doc_ra": thang.chu_doc_ra,
                    "tep": os.path.basename(tep_dich), "canh_bao": canh_bao,
                    "nhom": nhom_theo_so.get(thang.so, ""),
                    "theo_khuon": nhom_theo_so.get(thang.so) == "khuon",
                    "tham_do": nhom_theo_so.get(thang.so, "tham_do" if not nhom_theo_so else "") == "tham_do",
                    "nhom_uu_tien": nhom_uu_tien or "", "luot_tham_do": bool(luot_tham_do),
                    "he_so_tu_hoc": he_tu_hoc},
            "ung_vien": [{"so": k.so, "kieu": ten_kieu_theo_so.get(k.so, ""),
                         "nhom": nhom_theo_so.get(k.so, ""),
                         "tong_diem": round(k.tong, 1), "diem": {a: round(b, 1) for a, b in k.diem.items()},
                         "loai": k.loai, "ly_do": k.ly_do} for k in ung_cu_vien],
            "so_luot_cham": so_luot_cham, "co_khuon_thang": bool(khuon_thang),
        }
        _ghi_json(duong_tep_chon_bia(thu_muc_thumb), ket_qua)
        ghi("  ảnh bìa: giám khảo AI chọn tấm {0} ({1}, {2:.1f} điểm) — {3}".format(
            thang.so, u_thang.kieu, thang.tong, ly_do_chon))
        return ket_qua["chon"]
    except Exception as loi:  # noqa: BLE001 — KHÔNG BAO GIỜ chặn khâu ảnh bìa
        ghi("  (giám khảo ảnh bìa hỏng: {0}) — dùng đường lùi.".format(str(loi)[:150]))
        u_lui, ly_do = _chon_duong_lui(goc, kenh, ung_vien, khuon_thang)
        tep_dich = os.path.join(thu_muc_thumb, "CHON-thumb_{0:03d}.jpg".format(u_lui.so))
        if not _xuat_jpg(u_lui.duong, tep_dich):
            return None
        ghi("  ảnh bìa: {0} — tấm {1} ({2}).".format(ly_do, u_lui.so, u_lui.kieu))
        ket_qua_lui = {"so": u_lui.so, "kieu": u_lui.kieu, "tong_diem": None,
                       "chon_boi": "luat", "ly_do": ly_do, "tep": os.path.basename(tep_dich),
                       "nhom": nhom_theo_so.get(u_lui.so, ""),
                       "theo_khuon": nhom_theo_so.get(u_lui.so) == "khuon",
                       "tham_do": nhom_theo_so.get(u_lui.so) == "tham_do"}
        _ghi_json(duong_tep_chon_bia(thu_muc_thumb), {"chon": ket_qua_lui, "ung_vien": [],
                                                       "loi": str(loi)[:300]})
        return ket_qua_lui


def _anh_da_dang_gan_day(goc: str, kenh: str, *, loai_tru_ma_goi: str = "", toi_da: int = 3) -> List[str]:
    """2-3 ảnh bìa ĐÃ DÙNG gần đây nhất của kênh (`ho-so-video/anh/<ma_goi>.jpg`)
    — tránh giám khảo khen một bố cục vừa lặp lại tuần trước."""
    try:
        from . import ho_so_video  # noqa: PLC0415
        thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
        ten_tep = sorted((t for t in os.listdir(thu_muc) if t.endswith(".json")), reverse=True)
    except OSError:
        return []
    ra: List[str] = []
    for ten in ten_tep:
        ma_goi = ten[:-len(".json")]
        if ma_goi == loai_tru_ma_goi:
            continue
        duong = os.path.join(thu_muc, "anh", "{0}.jpg".format(ma_goi))
        if os.path.isfile(duong):
            ra.append(duong)
        if len(ra) >= toi_da:
            break
    return ra


def _kieu_it_dung_hon(goc: str, kenh: str, kieu_a: str, kieu_b: str, *, so_ho_so_gan_day: int = 10) -> bool:
    """`kieu_a` xuất hiện ÍT LẦN HƠN `kieu_b` trong `so_ho_so_gan_day` hồ sơ gần
    nhất của kênh — đọc trực tiếp `thumbnail.kieu` mỗi hồ sơ (Việc 3)."""
    try:
        from . import ho_so_video  # noqa: PLC0415
        thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
        ten_tep = sorted((t for t in os.listdir(thu_muc) if t.endswith(".json")), reverse=True)
    except OSError:
        return False
    dem = {kieu_a: 0, kieu_b: 0}
    for ten in ten_tep[:so_ho_so_gan_day]:
        ho_so = ho_so_video.doc_ho_so(goc, kenh, ten[:-len(".json")])
        if not isinstance(ho_so, dict):
            continue
        kieu = (ho_so.get("thumbnail") or {}).get("kieu") if isinstance(ho_so.get("thumbnail"), dict) else ""
        if kieu in dem:
            dem[kieu] += 1
    return dem[kieu_a] < dem[kieu_b]
