"""HỒ SƠ THIẾT LẬP KÊNH YouTube (03/10/2026) — phần 1, KHÔNG mạng trình duyệt.

`CHANNEL/<K>/thiet-lap/ho-so.json` + ảnh cùng thư mục là NGUỒN SỰ THẬT để `vm/thiet_lap_kenh_dom.py`
điền vào Studio (tên, handle, mô tả, từ khoá, quốc gia, mặc định tải lên, danh sách phát, logo, banner,
hình mờ). Kênh nào chưa có `CHANNEL/<K>` thì dùng bản nháp `workspace/chuan-bi-<K>/CHANNEL/<K>/thiet-lap/`.

Nguồn dựng hồ sơ:
  (a) bộ có sẵn `workspace/thiet-lap-kenh-moi/` (HUONG-DAN-THIET-LAP.md + logo/banner/watermark) — 4 kênh
      TL4-T7-K2, TL5-T7, TL6-T7, TL6-T7-K2: đọc phương án ★ khuyên dùng, chép ảnh;
  (b) kênh khác: LLM ShopAPI viết chữ theo kenh.yaml, cổng ảnh ShopAPI vẽ nền, PIL cắt/đặt kích thước;
      CHỮ tên kênh trên banner do MÃ vẽ (không để AI vẽ chữ), nằm trong vùng an toàn 1546×423 ở giữa.

Chạy:  python -m core.thiet_lap_kenh tao <K> [--lam-lai muc,muc|tat-ca] [--thu]
       python -m core.thiet_lap_kenh xem <K>
Không ghi đè mục đã có, trừ `--lam-lai`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

GOC_TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_HO_SO = "ho-so.json"
THU_MUC_BO_SAN = os.path.join("workspace", "thiet-lap-kenh-moi")
TEP_HUONG_DAN = "HUONG-DAN-THIET-LAP.md"

# ── Luật cứng của YouTube / của tool (test canh) ────────────────────────────
GIOI_HAN_TEN = 50
GIOI_HAN_MO_TA = 1000
MO_TA_TOI_THIEU = 300
GIOI_HAN_TU_KHOA = 500
HANDLE_MIN, HANDLE_MAX = 3, 30
GIOI_HAN_TEN_DS_PHAT = 150
GIOI_HAN_MO_TA_DS_PHAT = 5000
KICH_THUOC = {"logo": (800, 800), "banner": (2560, 1440), "hinh_mo": (150, 150)}
VUNG_AN_TOAN = (1546, 423)          # vùng an toàn của banner (mọi thiết bị đều thấy), nằm GIỮA
TRUONG_BAT_BUOC = ("ten", "handle", "mo_ta", "tu_khoa", "quoc_gia", "danh_sach_phat", "mac_dinh_tai_len",
                   "logo", "banner", "hinh_mo")
MUC_LAM_LAI = ("ten", "handle", "mo_ta", "tu_khoa", "quoc_gia", "danh_sach_phat", "mac_dinh_tai_len",
               "logo", "banner", "hinh_mo")
KHAU_HIEU_TOI_DA = 3

#: Danh mục video mặc định: khoá → tên ở các thứ tiếng Studio (so không phân biệt hoa/thường).
DANH_MUC = {
    "education": ("Education", "教育", "Giáo dục", "Educación", "Éducation", "Bildung", "教育"),
    "people": ("People & Blogs", "ブログ", "Mọi người và blog", "Con người & Blog", "Personas y blogs", "Personnes et blogs",
               "Menschen & Blogs", "人物和博客", "ピープル&ブログ", "ピープルとブログ"),
    "entertainment": ("Entertainment", "エンターテインメント", "Giải trí"),
    "howto": ("Howto & Style", "ハウツーとスタイル", "Hướng dẫn và phong cách", "Hướng dẫn & phong cách", "ハウツー&スタイル"),
    "science": ("Science & Technology", "科学と技術", "Khoa học và công nghệ", "Khoa học & công nghệ", "科学とテクノロジー"),
}
#: Mã ngôn ngữ → tên tiếng (Studio hiện theo ngôn ngữ giao diện).
NGON_NGU = {
    "ja": ("Japanese", "日本語", "Tiếng Nhật", "japonés", "japonais", "Japanisch"),
    "vi": ("Vietnamese", "Tiếng Việt", "ベトナム語", "vietnamita", "vietnamien"),
    "en": ("English", "英語", "Tiếng Anh", "inglés", "anglais", "Englisch", "English (United States)"),
    "ko": ("Korean", "韓国語", "Tiếng Hàn", "coreano", "coréen"),
    "es": ("Spanish", "スペイン語", "Tiếng Tây Ban Nha", "español", "espagnol"),
    "pt": ("Portuguese", "ポルトガル語", "Tiếng Bồ Đào Nha", "português"),
    "de": ("German", "ドイツ語", "Tiếng Đức", "Deutsch"),
    "fr": ("French", "フランス語", "Tiếng Pháp", "français"),
    "th": ("Thai", "タイ語", "Tiếng Thái"),
    "id": ("Indonesian", "インドネシア語", "Tiếng Indonesia"),
    "zh": ("Chinese", "中国語", "Tiếng Trung"),
}
QUOC_GIA = {
    "JP": ("Japan", "日本", "Nhật Bản", "Japón", "Japon"),
    "VN": ("Vietnam", "ベトナム", "Việt Nam", "Viet Nam"),
    "US": ("United States", "アメリカ合衆国", "Hoa Kỳ", "Estados Unidos", "États-Unis"),
    "KR": ("South Korea", "韓国", "Hàn Quốc", "Corea del Sur"),
    "TW": ("Taiwan", "台湾", "Đài Loan"),
    "TH": ("Thailand", "タイ", "Thái Lan"),
    "ID": ("Indonesia", "インドネシア"),
    "BR": ("Brazil", "ブラジル", "Brasil"),
    "ES": ("Spain", "スペイン", "Tây Ban Nha", "España"),
    "DE": ("Germany", "ドイツ", "Đức", "Deutschland"),
    "FR": ("France", "フランス", "Pháp"),
    "GB": ("United Kingdom", "イギリス", "Vương quốc Anh"),
}


# ═══════════════════════════ ĐƯỜNG DẪN ═══════════════════════════════════════
def thu_muc_thiet_lap(kenh: str, goc: str = GOC_TOOL) -> str:
    """`CHANNEL/<K>/thiet-lap` nếu kênh đã vào CHANNEL, không thì bản nháp `workspace/chuan-bi-<K>/...`."""
    if os.path.isdir(os.path.join(goc, "CHANNEL", kenh)) or not os.path.isdir(
            os.path.join(goc, "workspace", "chuan-bi-" + kenh, "CHANNEL", kenh)):
        return os.path.join(goc, "CHANNEL", kenh, "thiet-lap")
    return os.path.join(goc, "workspace", "chuan-bi-" + kenh, "CHANNEL", kenh, "thiet-lap")


def thu_muc_kenh(kenh: str, goc: str = GOC_TOOL) -> str:
    return os.path.dirname(thu_muc_thiet_lap(kenh, goc))


def doc_ho_so(kenh: str, goc: str = GOC_TOOL) -> Dict[str, Any]:
    try:
        with open(os.path.join(thu_muc_thiet_lap(kenh, goc), TEP_HO_SO), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_ho_so(kenh: str, ho_so: Dict[str, Any], goc: str = GOC_TOOL) -> str:
    thu_muc = thu_muc_thiet_lap(kenh, goc)
    os.makedirs(thu_muc, exist_ok=True)
    d = os.path.join(thu_muc, TEP_HO_SO)
    with open(d + ".tam", "w", encoding="utf-8") as tep:
        json.dump(ho_so, tep, ensure_ascii=False, indent=2)
    os.replace(d + ".tam", d)
    return d


def duong_anh(ho_so: Dict[str, Any], muc: str, thu_muc: str) -> str:
    ten = str((ho_so or {}).get(muc) or "")
    return os.path.join(thu_muc, ten) if ten else ""


# ═══════════════════════════ HÀM THUẦN (có test) ═════════════════════════════
def chuan_chu(s: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def vung_an_toan(rong: int = 2560, cao: int = 1440) -> Tuple[int, int, int, int]:
    """(x0, y0, x1, y1) của vùng an toàn 1546×423 ở GIỮA banner."""
    w, h = VUNG_AN_TOAN
    x0, y0 = (rong - w) // 2, (cao - h) // 2
    return x0, y0, x0 + w, y0 + h


def tu_khoa_chuoi(tu_khoa: Any) -> str:
    """Danh sách từ khoá → chuỗi "a, b, c" (YouTube nhận phân cách phẩy)."""
    if isinstance(tu_khoa, str):
        ds = [t for t in re.split(r"[,、，\n]+", tu_khoa)]
    else:
        ds = list(tu_khoa or [])
    return ", ".join(chuan_chu(t) for t in ds if chuan_chu(t))


def ten_danh_muc(khoa: str) -> Tuple[str, ...]:
    return DANH_MUC.get(str(khoa or "").lower(), ())


def ten_ngon_ngu(ma: str) -> Tuple[str, ...]:
    return NGON_NGU.get(str(ma or "").lower().split("-")[0], ())


def ten_quoc_gia(ma: str) -> Tuple[str, ...]:
    return QUOC_GIA.get(str(ma or "").upper(), ())


def handle_hop_le(handle: str) -> bool:
    h = str(handle or "").lstrip("@")
    return HANDLE_MIN <= len(h) <= HANDLE_MAX and bool(re.match(r"^[A-Za-z0-9_.\-]+$", h))


def chuan_handle(handle: str) -> str:
    return "@" + str(handle or "").strip().lstrip("@")


def kich_thuoc_anh(duong: str) -> Tuple[int, int]:
    from PIL import Image  # noqa: PLC0415

    with Image.open(duong) as im:
        return im.size


def kiem_ho_so(ho_so: Dict[str, Any], thu_muc: str = "", kiem_anh: bool = True) -> List[str]:
    """Danh sách lỗi của hồ sơ ([] = đủ + đúng luật)."""
    loi: List[str] = []
    hs = ho_so or {}
    for k in TRUONG_BAT_BUOC:
        if not hs.get(k):
            loi.append("thiếu {0}".format(k))
    ten = chuan_chu(hs.get("ten"))
    if ten and len(ten) > GIOI_HAN_TEN:
        loi.append("tên dài {0} > {1} ký tự".format(len(ten), GIOI_HAN_TEN))
    if hs.get("handle") and not handle_hop_le(hs["handle"]):
        loi.append("handle không hợp lệ ({0}–{1} ký tự chữ/số/_/./-): {2}".format(HANDLE_MIN, HANDLE_MAX, hs["handle"]))
    mo_ta = str(hs.get("mo_ta") or "")
    if mo_ta:
        if len(mo_ta) > GIOI_HAN_MO_TA:
            loi.append("mô tả dài {0} > {1} ký tự".format(len(mo_ta), GIOI_HAN_MO_TA))
        if len(mo_ta) < MO_TA_TOI_THIEU:
            loi.append("mô tả ngắn {0} < {1} ký tự".format(len(mo_ta), MO_TA_TOI_THIEU))
        chinh = chuan_chu(hs.get("tu_khoa_chinh"))
        if chinh and chinh.lower() not in chuan_chu(mo_ta[:160]).lower():
            loi.append("câu đầu của mô tả không chứa từ khoá chính «{0}»".format(chinh))
    tk = tu_khoa_chuoi(hs.get("tu_khoa"))
    if len(tk) > GIOI_HAN_TU_KHOA:
        loi.append("từ khoá dài {0} > {1} ký tự".format(len(tk), GIOI_HAN_TU_KHOA))
    if hs.get("quoc_gia") and not re.match(r"^[A-Za-z]{2}$", str(hs["quoc_gia"])):
        loi.append("quốc gia phải là mã 2 chữ (vd JP)")
    for i, d in enumerate(hs.get("danh_sach_phat") or [], 1):
        if not isinstance(d, dict) or not chuan_chu(d.get("ten")):
            loi.append("danh sách phát #{0} thiếu tên".format(i))
        elif len(chuan_chu(d["ten"])) > GIOI_HAN_TEN_DS_PHAT or len(str(d.get("mo_ta") or "")) > GIOI_HAN_MO_TA_DS_PHAT:
            loi.append("danh sách phát #{0} quá dài".format(i))
    mdtl = hs.get("mac_dinh_tai_len")
    if isinstance(mdtl, dict):
        for k in ("ngon_ngu", "danh_muc"):
            if not mdtl.get(k):
                loi.append("mac_dinh_tai_len thiếu {0}".format(k))
        if mdtl.get("danh_muc") and not ten_danh_muc(mdtl["danh_muc"]):
            loi.append("danh_muc «{0}» không biết (một trong {1})".format(mdtl["danh_muc"], "/".join(DANH_MUC)))
        if len(tu_khoa_chuoi(mdtl.get("the"))) > 500:
            loi.append("thẻ mặc định dài quá 500 ký tự")
    elif mdtl:
        loi.append("mac_dinh_tai_len phải là object")
    if kiem_anh and thu_muc:
        for muc, (w, h) in KICH_THUOC.items():
            d = duong_anh(hs, muc, thu_muc)
            if not d:
                continue
            if not os.path.isfile(d):
                loi.append("không có tệp ảnh {0}: {1}".format(muc, os.path.basename(d)))
                continue
            try:
                kt = kich_thuoc_anh(d)
            except Exception:  # noqa: BLE001
                loi.append("ảnh {0} không đọc được".format(muc))
                continue
            if kt != (w, h):
                loi.append("ảnh {0} {1}×{2}, cần {3}×{4}".format(muc, kt[0], kt[1], w, h))
        d = duong_anh(hs, "hinh_mo", thu_muc)
        if d and os.path.isfile(d) and not d.lower().endswith(".png"):
            loi.append("hình mờ phải là PNG")
    kh = hs.get("banner_chu")
    if kh is not None and (not isinstance(kh, list) or len(kh) > KHAU_HIEU_TOI_DA):
        loi.append("banner_chu phải là danh sách ≤ {0} dòng".format(KHAU_HIEU_TOI_DA))
    return loi


# ═══════════════════════════ ẢNH BẰNG PIL ════════════════════════════════════
def _font(goc: str = GOC_TOOL) -> str:
    try:
        from .bia_theo_khuon import _tim_font  # noqa: PLC0415
        return _tim_font(goc)
    except Exception:  # noqa: BLE001
        return ""


def anh_logo_tu_nguon(nguon: str, dich: str) -> str:
    from PIL import Image, ImageOps  # noqa: PLC0415

    with Image.open(nguon) as im:
        ImageOps.fit(im.convert("RGB"), KICH_THUOC["logo"], Image.LANCZOS, centering=(0.5, 0.45)).save(dich, "PNG")
    return dich


def anh_hinh_mo_tu_logo(logo: str, dich: str) -> str:
    """150×150 PNG nền trong: logo cắt tròn (hình mờ chỉ hiện nhỏ ở góc video)."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    kt = KICH_THUOC["hinh_mo"]
    with Image.open(logo) as im:
        a = im.convert("RGBA").resize(kt, Image.LANCZOS)
    mat = Image.new("L", (kt[0] * 4, kt[1] * 4), 0)
    ImageDraw.Draw(mat).ellipse((0, 0, kt[0] * 4 - 1, kt[1] * 4 - 1), fill=255)
    a.putalpha(mat.resize(kt, Image.LANCZOS))
    a.save(dich, "PNG")
    return dich


def anh_banner_tu_nguon(nguon: str, dich: str, dong_chu: Sequence[str] = (), goc: str = GOC_TOOL) -> str:
    """Ảnh nền → 2560×1440, rồi MÃ vẽ chữ (≤3 dòng, chữ trắng viền đen) nằm GỌN trong vùng an toàn 1546×423."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: PLC0415

    rong, cao = KICH_THUOC["banner"]
    with Image.open(nguon) as im:
        nen = ImageOps.fit(im.convert("RGB"), (rong, cao), Image.LANCZOS)
    dong = [chuan_chu(d) for d in dong_chu if chuan_chu(d)][:KHAU_HIEU_TOI_DA]
    if dong:
        x0, y0, x1, y1 = vung_an_toan(rong, cao)
        fp = _font(goc)
        ve = ImageDraw.Draw(nen)
        le = 24
        rong_hop, cao_hop = (x1 - x0) - 2 * le, (y1 - y0) - 2 * le
        co = [int(cao_hop * 0.5) if i == 0 else int(cao_hop * 0.2) for i in range(len(dong))]
        while True:
            fonts = [ImageFont.truetype(fp, c) if fp else ImageFont.load_default() for c in co]
            cao_dong = [int(c * 1.2) for c in co]
            if all(ve.textlength(d, font=f) <= rong_hop for d, f in zip(dong, fonts)) and sum(cao_dong) <= cao_hop:
                break
            co = [max(10, int(c * 0.92)) for c in co]
            if max(co) <= 10:
                break
        y = y0 + le + (cao_hop - sum(cao_dong)) // 2
        for d, f, ch in zip(dong, fonts, cao_dong):
            w = ve.textlength(d, font=f)
            ve.text((x0 + (x1 - x0 - w) / 2, y), d, font=f, fill=(255, 255, 255), stroke_width=max(3, f.size // 14) if fp else 0,
                    stroke_fill=(0, 0, 0))
            y += ch
    nen.save(dich, "PNG")
    return dich


def hop_chu_banner(dich: str, dong_chu: Sequence[str], goc: str = GOC_TOOL) -> Tuple[int, int, int, int]:
    """Hộp bao của chữ sẽ vẽ (để test): đo lại như `anh_banner_tu_nguon`."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    x0, y0, x1, y1 = vung_an_toan(*KICH_THUOC["banner"])
    ve = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    fp = _font(goc)
    dong = [chuan_chu(d) for d in dong_chu if chuan_chu(d)][:KHAU_HIEU_TOI_DA]
    if not dong or not fp:
        return x0, y0, x0, y0
    f = ImageFont.truetype(fp, 40)
    return x0, y0, x0 + int(max(ve.textlength(d, font=f) for d in dong)), y0 + 48 * len(dong)


# ═══════════════════════════ NGUỒN (a): BỘ CÓ SẴN ═════════════════════════════
def _gon(s: Any) -> str:
    """Gộp khoảng trắng, GIỮ NGUYÊN ký tự (không NFKC) — tên danh sách phát phải đúng từng chữ như người soạn."""
    return " ".join(str(s or "").split())


def _doc_van_ban(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def _muc_kenh(md: str, kenh: str) -> str:
    m = re.search(r"(?m)^## \d+\. {0} — .*$".format(re.escape(kenh)), md)
    if not m:
        return ""
    sau = re.search(r"(?m)^## \d+\. ", md[m.end():])
    return md[m.start(): m.end() + (sau.start() if sau else len(md))]


def _khoi_ma(muc: str, buoc: str, thu: int = 0) -> str:
    m = re.search(r"(?m)^### {0}\b.*$".format(re.escape(buoc)), muc)
    if not m:
        return ""
    khoi = re.findall(r"```[^\n]*\n(.*?)```", muc[m.end():].split("\n### ", 1)[0], flags=re.S)
    return khoi[thu].strip("\n") if len(khoi) > thu else ""


def doc_bo_san(kenh: str, goc: str = GOC_TOOL) -> Dict[str, Any]:
    """Đọc phương án ★ trong HUONG-DAN-THIET-LAP.md. {} nếu kênh không có trong bộ."""
    thu_muc = os.path.join(goc, THU_MUC_BO_SAN)
    muc = _muc_kenh(_doc_van_ban(os.path.join(thu_muc, TEP_HUONG_DAN)), kenh)
    if not muc:
        return {}
    ten = _khoi_ma(muc, "Bước 1", 0).strip()
    handle = _khoi_ma(muc, "Bước 1", 1).strip()
    mo_ta = _khoi_ma(muc, "Bước 2").strip()
    tu_khoa = [_gon(t) for t in _khoi_ma(muc, "Bước 6").split(",") if _gon(t)]
    ds = []
    m7 = re.search(r"(?m)^### Bước 7\b.*$", muc)
    if m7:
        for m in re.finditer(r"(?m)^\d+\. \*\*(.+?)\*\*[ \t]*\n[ \t]+(.+)$", muc[m7.end():].split("\n### ", 1)[0]):
            ds.append({"ten": _gon(m.group(1)), "mo_ta": _gon(m.group(2))})
    chu_banner = []
    m = re.search(r"Chữ trên banner \(code vẽ\): (.+)", muc)
    if m:
        chu_banner = [_gon(x) for x in m.group(1).split("·") if _gon(x)]
    anh = {m_: os.path.join(thu_muc, kenh, t) for m_, t in (("logo", "logo.png"), ("banner", "banner.png"),
                                                              ("hinh_mo", "watermark.png"))}
    if not (ten and handle and mo_ta):
        return {}
    return {"ten": ten, "handle": chuan_handle(handle), "mo_ta": mo_ta, "tu_khoa": tu_khoa, "danh_sach_phat": ds,
            "banner_chu": chu_banner, "anh": anh}


# ═══════════════════════════ NGUỒN (b): LLM + CỔNG ẢNH ═══════════════════════
def _yaml_kenh(kenh: str, goc: str) -> Dict[str, Any]:
    from .kenh import doc_yaml  # noqa: PLC0415

    return doc_yaml(os.path.join(thu_muc_kenh(kenh, goc), "kenh.yaml")) or {}


def _kenh_cung_tuyen(kenh: str, kh: Dict[str, Any], goc: str) -> List[Dict[str, Any]]:
    """Hồ sơ của kênh khác CÙNG nhóm/tệp (mẫu thắng/đã làm), để LLM bắt nhịp."""
    ra: List[Dict[str, Any]] = []
    try:
        for k in sorted(os.listdir(os.path.join(goc, "CHANNEL"))):
            if k == kenh or k.startswith("_"):
                continue
            ky = _yaml_kenh(k, goc)
            if str(ky.get("nhom") or "x") != str(kh.get("nhom") or "y"):
                continue
            hs = doc_ho_so(k, goc)
            if hs.get("mo_ta"):
                ra.append({"kenh": k, "ten": hs.get("ten"), "mo_ta": hs.get("mo_ta"), "tu_khoa": hs.get("tu_khoa")})
    except OSError:
        pass
    return ra[:2]


def loi_nhac_ho_so(kenh: str, kh: Dict[str, Any], mau: List[Dict[str, Any]]) -> str:
    ngon_ngu = str(kh.get("ngon_ngu") or "en")
    ds_phat = [x.strip() for x in str(kh.get("danh_sach_phat_kenh") or "").split("|") if x.strip()]
    vd = "\n".join("- {0}: {1}\n  {2}".format(m.get("ten"), chuan_chu(m.get("mo_ta"))[:300], m.get("tu_khoa")) for m in mau)
    return (
        "You write the YouTube channel setup text for a NEW channel. Reply with ONE JSON object only, no markdown.\n"
        "CHANNEL FACTS\n- code: {ma}\n- working title (may be a placeholder): {ten}\n- language of the channel text: {lg}\n"
        "- audience / niche id: {tep}\n- group: {nhom}\n- voice and tone: {giong}\n- selection rule (what the channel is about): {luat}\n"
        "- planned playlists (keep these names exactly if present): {pl}\n"
        "{vd_}\n"
        "WRITE (all text in language '{lg}'):\n"
        '"ten": channel name <= 40 chars, memorable, not copying a competitor,\n'
        '"handle": ascii only, lowercase, letters/digits/hyphen, 3-24 chars, no @,\n'
        '"tu_khoa_chinh": the ONE main keyword of the niche (must appear in the first sentence of mo_ta),\n'
        '"mo_ta": channel description 600-900 chars: first sentence contains the main keyword and the viewer promise, '
        "then what the channel covers, who it is for, upload rhythm, an invitation to subscribe; natural prose, NO keyword stuffing, "
        "no claims of medical/financial advice, line breaks allowed,\n"
        '"tu_khoa": 8-15 keywords/phrases as a JSON array (total <= 450 chars), the search terms the audience uses,\n'
        '"danh_sach_phat": array of {{"ten": <=60 chars, "mo_ta": <=160 chars}} (3-6 items),\n'
        '"banner_chu": array of 2-3 short lines for the banner (name, a one-line promise, upload rhythm), each <= 18 chars for CJK or <= 32 chars otherwise.\n'
    ).format(ma=kenh, ten=kh.get("ten") or "", lg=ngon_ngu, tep=kh.get("tep") or "", nhom=kh.get("nhom") or "",
             giong=str(kh.get("giong_van") or "")[:300], luat=str(kh.get("luat_chon") or "")[:900],
             pl=" | ".join(ds_phat) or "(none)", vd_=("EXAMPLES from sibling channels (match their care, not their wording):\n" + vd) if vd else "")


def _bat_json(chu: str) -> Dict[str, Any]:
    chu = re.sub(r"^```(?:json)?|```$", "", str(chu or "").strip(), flags=re.M).strip()
    a, b = chu.find("{"), chu.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("LLM không trả JSON")
    du = json.loads(chu[a:b + 1])
    if not isinstance(du, dict):
        raise ValueError("LLM không trả object")
    return du


def chuan_hoa_tu_llm(du: Dict[str, Any], kh: Dict[str, Any]) -> Dict[str, Any]:
    """Làm sạch trả lời của LLM thành các trường hồ sơ (cắt tỉa theo luật; không đủ thì để rỗng cho kiểm báo)."""
    ds_phat = [{"ten": chuan_chu(d.get("ten"))[:GIOI_HAN_TEN_DS_PHAT], "mo_ta": chuan_chu(d.get("mo_ta"))[:300]}
               for d in (du.get("danh_sach_phat") or []) if isinstance(d, dict) and chuan_chu(d.get("ten"))]
    tk, tong = [], 0
    for t in (du.get("tu_khoa") if isinstance(du.get("tu_khoa"), list) else re.split(r"[,、]", str(du.get("tu_khoa") or ""))):
        t = chuan_chu(t)
        if t and t not in tk and tong + len(t) + 2 <= GIOI_HAN_TU_KHOA - 20:
            tk.append(t)
            tong += len(t) + 2
    handle = re.sub(r"[^a-z0-9\-]", "", str(du.get("handle") or "").lower().lstrip("@"))[:24]
    # 04/10/2026 (chủ dự án): danh mục MỌI kênh = Giáo dục (mặc định tải lên → video sau cũng Giáo dục). Không để LLM
    # chọn; kênh nào cần khác thì khai `danh_muc` trong kenh.yaml.
    dm = str(kh.get("danh_muc") or "education").lower()
    return {"ten": chuan_chu(du.get("ten"))[:GIOI_HAN_TEN], "handle": ("@" + handle) if handle else "",
            "mo_ta": str(du.get("mo_ta") or "").replace("\r\n", "\n").strip()[:GIOI_HAN_MO_TA],
            "tu_khoa": tk, "tu_khoa_chinh": chuan_chu(du.get("tu_khoa_chinh")), "danh_sach_phat": ds_phat,
            "danh_muc": dm if dm in DANH_MUC else "education",
            "banner_chu": [chuan_chu(x) for x in (du.get("banner_chu") or []) if chuan_chu(x)][:KHAU_HIEU_TOI_DA]}


def sinh_bang_llm(kenh: str, goc: str, goi: Callable[..., str]) -> Dict[str, Any]:
    kh = _yaml_kenh(kenh, goc)
    ask = loi_nhac_ho_so(kenh, kh, _kenh_cung_tuyen(kenh, kh, goc))
    loi = ""
    for _ in range(2):
        tra = goi(ask + (("\nPREVIOUS ANSWER WAS REJECTED: " + loi) if loi else ""))
        try:
            hs = chuan_hoa_tu_llm(_bat_json(tra), kh)
        except (ValueError, TypeError) as e:
            loi = str(e)
            continue
        sai = kiem_ho_so(dict(hs, quoc_gia="XX", logo="x", banner="x", hinh_mo="x",
                              mac_dinh_tai_len={"ngon_ngu": "x", "danh_muc": hs["danh_muc"]}), kiem_anh=False)
        if not sai:
            return hs
        loi = "; ".join(sai)
    raise RuntimeError("LLM viết hồ sơ kênh chưa đạt luật: {0}".format(loi))


def _loi_nhac_anh(muc: str, st: Dict[str, Any], hs: Dict[str, Any]) -> str:
    kieu = str(st.get("image_style") or "")
    khoa = str(st.get("reference_lock") or "")
    if muc == "logo":
        return ("{0}. Square YouTube profile icon: a close-up of the attached reference character's face and shoulders, centered, "
                "filling about 75 percent of the frame, simple solid warm background, bold clean shapes readable at 48 pixels. "
                "{1} No text, no letters, no watermark.").format(kieu, khoa)
    return ("{0}. Ultra-wide cinematic YouTube channel banner artwork for a channel about: {1}. The attached reference character and one key "
            "prop sit CENTERED in the middle band of the image (middle 55 percent of the width, middle third of the height); the left and "
            "right thirds are calm extended scenery with nothing important; soft low-contrast area for a headline in the centre. "
            "{2} No text, no letters, no watermark.").format(kieu, hs.get("tu_khoa_chinh") or hs.get("ten") or "", khoa)


def tao_anh_that(client: Any) -> Callable[..., str]:
    """`tao(prompt, dich, tham_chieu=[duong…]) -> duong` qua cổng ảnh ShopAPI (cùng đường với nhân vật/bìa của tool)."""
    from . import anh_len  # noqa: PLC0415
    from .khoi_tao_ngach import _tao_anh_nv  # noqa: PLC0415,SLF001
    import hashlib  # noqa: PLC0415

    def tao(prompt: str, dich: str, tham_chieu: Sequence[str] = ()) -> str:
        khoa = "thiet-lap-kenh:" + hashlib.sha1((prompt + "|" + ",".join(tham_chieu)).encode("utf-8")).hexdigest()[:16]
        if not tham_chieu:
            return _tao_anh_nv(client, prompt, dich, khoa)
        url = [anh_len.tai_len(client, p) for p in tham_chieu]
        job = client.images.create_and_wait(prompt=prompt, n=1, aspect_ratio="16:9", idempotency_key=khoa, timeout=900,
                                            reference_images=[u for u in url if u] or None)
        ma = str((job or {}).get("id") or (job or {}).get("job_id") or "")
        goc_url = str(getattr(client, "base_url", "") or "https://api.shopapi.vn").rstrip("/")
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        with client._http.stream("GET", "{0}/v1/jobs/{1}/download".format(goc_url, ma),  # noqa: SLF001
                                 headers=client._build_headers(accept="*/*")) as ph:  # noqa: SLF001
            if ph.status_code >= 400:
                ph.read()
                raise RuntimeError("tải ảnh hỏng ({0})".format(ph.status_code))
            with open(dich + ".tam", "wb") as tep:
                for khuc in ph.iter_bytes(1 << 16):
                    tep.write(khuc)
        os.replace(dich + ".tam", dich)
        return dich

    return tao


def tao_goi_llm() -> Callable[..., str]:
    """`goi(loi_nhac) -> str` qua ví ShopAPI của tool (cùng cách mọi khâu LLM khác)."""
    from .api import build_client  # noqa: PLC0415
    from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415
    from .goi_van_ban import goi_van_ban, tin_nhan_viet  # noqa: PLC0415

    cfg = load_config(os.path.join(GOC_TOOL, CONFIG_FILENAME))
    if cfg.problem:
        raise RuntimeError("không đọc được cấu hình ShopAPI: " + str(cfg.problem)[:100])
    client = build_client(cfg)
    goi = (lambda p, **kw: goi_van_ban(client, tin_nhan_viet(p), mo_hinh="claude-sonnet-5", toi_da_token=4096))
    goi.client = client  # type: ignore[attr-defined]
    return goi


# ═══════════════════════════ TẠO HỒ SƠ ═══════════════════════════════════════
def _ds_phat_tu_yaml(kh: Dict[str, Any]) -> List[Dict[str, str]]:
    return [{"ten": chuan_chu(x), "mo_ta": ""} for x in str(kh.get("danh_sach_phat_kenh") or "").split("|") if chuan_chu(x)]


def _muc_can_lam(hs: Dict[str, Any], thu_muc: str, lam_lai: Sequence[str]) -> List[str]:
    ra = []
    for m in MUC_LAM_LAI:
        if m in lam_lai or not hs.get(m):
            ra.append(m)
        elif m in KICH_THUOC and not os.path.isfile(duong_anh(hs, m, thu_muc)):
            ra.append(m)
    return ra


def tao(kenh: str, goc: str = GOC_TOOL, lam_lai: Sequence[str] = (), *, goi: Optional[Callable[..., str]] = None,
        tao_anh: Optional[Callable[..., str]] = None, log: Callable[[str], None] = print,
        thu: bool = False) -> Dict[str, Any]:
    """Tạo/hoàn thiện hồ sơ của `kenh`. Chỉ làm mục thiếu (hoặc có trong `lam_lai`). Trả hồ sơ đã ghi."""
    lam_lai = list(MUC_LAM_LAI) if "tat-ca" in lam_lai else [m for m in lam_lai if m in MUC_LAM_LAI]
    thu_muc = thu_muc_thiet_lap(kenh, goc)
    hs = doc_ho_so(kenh, goc)
    kh = _yaml_kenh(kenh, goc)
    can = _muc_can_lam(hs, thu_muc, lam_lai)
    if not kh and not doc_bo_san(kenh, goc):
        raise RuntimeError("không thấy kenh.yaml của {0}".format(kenh))
    log("hồ sơ {0}: cần làm {1}".format(kenh, ", ".join(can) or "(đã đủ)"))
    if thu:
        return hs
    os.makedirs(thu_muc, exist_ok=True)
    bo = doc_bo_san(kenh, goc)
    llm: Dict[str, Any] = {}
    tu_bo: set = set()
    if bo:
        hs["nguon"] = hs.get("nguon") or "bo-san"
        for k in ("ten", "handle", "mo_ta", "tu_khoa", "danh_sach_phat"):
            if k in can and bo.get(k):
                hs[k] = bo[k]
                tu_bo.add(k)
        if not hs.get("tu_khoa_chinh") and bo.get("tu_khoa"):
            hs["tu_khoa_chinh"] = bo["tu_khoa"][0]
        if "banner_chu" not in hs and bo.get("banner_chu"):
            hs["banner_chu"] = bo["banner_chu"]
    needs_llm = [m for m in ("ten", "handle", "mo_ta", "tu_khoa", "danh_sach_phat") if m in can and m not in tu_bo]
    if needs_llm:
        if goi is None:
            goi = tao_goi_llm()
        llm = sinh_bang_llm(kenh, goc, goi)
        hs["nguon"] = hs.get("nguon") or "llm"
        for k in needs_llm:
            hs[k] = llm[k]
        for k in ("tu_khoa_chinh", "banner_chu"):
            if llm.get(k) and (k not in hs or k in lam_lai or "mo_ta" in needs_llm):
                hs[k] = llm[k]
        if "danh_muc" in llm:
            hs["_danh_muc_goi_y"] = llm["danh_muc"]
    if "danh_sach_phat" in can and not hs.get("danh_sach_phat"):
        hs["danh_sach_phat"] = _ds_phat_tu_yaml(kh)
    elif hs.get("danh_sach_phat") and kh.get("danh_sach_phat_kenh"):
        # tên danh sách phát trong kenh.yaml là thứ tool khớp theo nghĩa: bổ sung cái còn thiếu
        co = {chuan_chu(d.get("ten")) for d in hs["danh_sach_phat"]}
        for d in _ds_phat_tu_yaml(kh):
            if chuan_chu(d["ten"]) not in co and "danh_sach_phat" in can:
                hs["danh_sach_phat"].append(d)
    if "quoc_gia" in can:
        hs["quoc_gia"] = str(kh.get("quoc_gia") or ({"ja": "JP", "vi": "VN", "ko": "KR", "th": "TH", "id": "ID", "pt": "BR",
                                                       "es": "ES", "de": "DE", "fr": "FR", "en": "US"}.get(
            str(kh.get("ngon_ngu") or "").lower().split("-")[0], "US"))).upper()
    if "mac_dinh_tai_len" in can:
        tk = hs.get("tu_khoa") or []
        hs["mac_dinh_tai_len"] = {"ngon_ngu": str(kh.get("ngon_ngu") or "en").lower().split("-")[0],
                                  "danh_muc": hs.pop("_danh_muc_goi_y", None) or "education",
                                  "the": list(tk)[:12]}
    hs.pop("_danh_muc_goi_y", None)
    # ── ảnh ──
    st = {}
    try:
        from .kenh import doc_yaml  # noqa: PLC0415
        st = doc_yaml(os.path.join(thu_muc_kenh(kenh, goc), "style.yaml")) or {}
    except Exception:  # noqa: BLE001
        pass
    nv = os.path.join(thu_muc_kenh(kenh, goc), "nv", "nv1.png")
    for muc, ten_tep in (("logo", "logo.png"), ("banner", "banner.png"), ("hinh_mo", "hinh-mo.png")):
        if muc not in can:
            continue
        dich = os.path.join(thu_muc, ten_tep)
        nguon_anh = (bo.get("anh") or {}).get({"hinh_mo": "hinh_mo"}.get(muc, muc), "") if bo else ""
        if nguon_anh and os.path.isfile(nguon_anh):
            if muc == "hinh_mo":
                _chep_hinh_mo(nguon_anh, dich)
            else:
                _chep_anh_dung_co(nguon_anh, dich, KICH_THUOC[muc])
        elif muc == "hinh_mo":
            lg = os.path.join(thu_muc, "logo.png")
            if not os.path.isfile(lg):
                raise RuntimeError("chưa có logo để cắt hình mờ")
            anh_hinh_mo_tu_logo(lg, dich)
        else:
            if tao_anh is None:
                tao_anh = tao_anh_that(getattr(goi, "client", None) or tao_goi_llm().client)
            tc = [nv] if os.path.isfile(nv) else []
            tho = os.path.join(thu_muc, "_nen-" + muc + ".png")
            tao_anh(_loi_nhac_anh(muc, st, hs), tho, tc)
            if muc == "logo":
                anh_logo_tu_nguon(tho, dich)
            else:
                anh_banner_tu_nguon(tho, dich, hs.get("banner_chu") or [hs.get("ten", "")], goc)
        hs[muc] = ten_tep
        log("  ảnh {0} → {1}".format(muc, ten_tep))
    hs["ngay_tao"] = hs.get("ngay_tao") or __import__("time").strftime("%Y-%m-%d")
    ghi_ho_so(kenh, hs, goc)
    loi = kiem_ho_so(hs, thu_muc)
    if loi:
        log("  CHƯA ĐẠT luật: " + "; ".join(loi))
    return hs


def _chep_anh_dung_co(nguon: str, dich: str, kt: Tuple[int, int]) -> None:
    from PIL import Image, ImageOps  # noqa: PLC0415

    with Image.open(nguon) as im:
        if im.size == kt and nguon.lower().endswith(".png"):
            shutil.copyfile(nguon, dich)
        else:
            ImageOps.fit(im.convert("RGB"), kt, Image.LANCZOS).save(dich, "PNG")


def _chep_hinh_mo(nguon: str, dich: str) -> None:
    from PIL import Image  # noqa: PLC0415

    with Image.open(nguon) as im:
        if im.size == KICH_THUOC["hinh_mo"]:
            shutil.copyfile(nguon, dich)
        else:
            im.convert("RGBA").resize(KICH_THUOC["hinh_mo"], Image.LANCZOS).save(dich, "PNG")


# ═══════════════════════════ CLI ═════════════════════════════════════════════
def xem(kenh: str, goc: str = GOC_TOOL, ra: Callable[[str], None] = print) -> int:
    hs = doc_ho_so(kenh, goc)
    if not hs:
        ra("chưa có hồ sơ của {0} ({1})".format(kenh, thu_muc_thiet_lap(kenh, goc)))
        return 1
    thu_muc = thu_muc_thiet_lap(kenh, goc)
    ra("── Hồ sơ {0} ({1}) ──".format(kenh, thu_muc))
    ra("tên: {0}   handle: {1}   quốc gia: {2}   nguồn: {3}".format(hs.get("ten"), hs.get("handle"), hs.get("quoc_gia"), hs.get("nguon")))
    ra("mô tả ({0} ký tự): {1}…".format(len(hs.get("mo_ta") or ""), chuan_chu(hs.get("mo_ta"))[:90]))
    ra("từ khoá ({0} ký tự): {1}".format(len(tu_khoa_chuoi(hs.get("tu_khoa"))), tu_khoa_chuoi(hs.get("tu_khoa"))[:140]))
    ra("mặc định tải lên: {0}".format(json.dumps(hs.get("mac_dinh_tai_len"), ensure_ascii=False)[:200]))
    for d in hs.get("danh_sach_phat") or []:
        ra("  danh sách phát: {0}".format(d.get("ten")))
    for muc in KICH_THUOC:
        d = duong_anh(hs, muc, thu_muc)
        kt = kich_thuoc_anh(d) if d and os.path.isfile(d) else None
        ra("ảnh {0}: {1} {2}".format(muc, hs.get(muc), "{0}×{1}".format(*kt) if kt else "THIẾU"))
    loi = kiem_ho_so(hs, thu_muc)
    ra("kiểm: " + ("ĐẠT" if not loi else "; ".join(loi)))
    return 0 if not loi else 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(prog="python -m core.thiet_lap_kenh", description="Hồ sơ thiết lập kênh YouTube.")
    sub = ap.add_subparsers(dest="lenh", required=True)
    t = sub.add_parser("tao", help="tạo/hoàn thiện hồ sơ (không ghi đè mục đã có)")
    t.add_argument("kenh")
    t.add_argument("--lam-lai", default="", help="mục làm lại, cách nhau bằng phẩy: " + ",".join(MUC_LAM_LAI) + " | tat-ca")
    t.add_argument("--thu", action="store_true", help="chỉ báo cần làm gì")
    x = sub.add_parser("xem", help="in hồ sơ + kiểm luật")
    x.add_argument("kenh")
    a = ap.parse_args(argv)
    if a.lenh == "xem":
        return xem(a.kenh)
    try:
        hs = tao(a.kenh, lam_lai=[m.strip() for m in a.lam_lai.split(",") if m.strip()], thu=a.thu)
    except Exception as loi:  # noqa: BLE001
        print("LỖI: {0}".format(str(loi)[:300]))
        return 1
    return 0 if a.thu or not kiem_ho_so(hs, thu_muc_thiet_lap(a.kenh)) else 2


if __name__ == "__main__":
    sys.exit(main())
