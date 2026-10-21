"""BÌA THEO DỮ LIỆU (20/10/2026) — bộ bìa thắng + HỌ kiểu chữ của từng kênh tự cập nhật từ số liệu Studio thật.

═══ VÌ SAO ═══

Chủ 20/10: *"thumbnail vẫn chưa đúng. TL2 video hiện tại CTR rất thấp mà kênh rõ ràng có bìa CTR cao. Sao logic không
dựa trên dữ liệu?"* Thư mục bìa thắng (`workspace/bia-<k>/thang/thang.json`) dựng tay MỘT lần ngày 19/10 và LỌC theo
kiểu: chỉ giữ bìa "chữ trần" → loại đúng hai bìa thắng nhì/ba của TL2 (chữ trên DẢI màu, nền tối) vì `kenh.yaml:
bia_lo_kieu: "tran"` ép kiểu. Kiểu bị CẤU HÌNH quyết, không phải dữ liệu; và không gì dựng lại thư mục.

═══ LÀM GÌ (kỹ năng D21, mỗi ngày khi bảng Studio mới) ═══

1. BỘ BÌA THẮNG tự động: từ `chi-so/bang-tom-tat.csv` CỦA kênh — video ≥ 48 giờ, ≥ 3.000 hiển thị, xếp theo LƯỢT
   BẤM (hiển thị × CTR), giữ video CTR ≥ trung vị kênh, tối đa 6 (tối thiểu 3, thiếu thì bù theo lượt bấm). KHÔNG lọc
   kiểu. Ảnh = bìa THẬT đang chạy (i.ytimg.com, `khuon_bia.anh_that`). Mỗi bìa gắn HỌ kiểu chữ ("tran" chữ trần,
   "dai" chữ trên dải màu, "hop" chữ trong hộp) — AI nhìn ảnh MỘT lần/ảnh qua ví ShopAPI, cache theo sha1. Bộ đổi →
   sao lưu thư mục cũ (`<thư mục>-sao-luu/<giờ>/`), bỏ tệp đệm suy từ bìa thắng cũ (`mau-bia-thang.json`,
   `san-bam.json`; `bo-cuc-thang.json` giữ số đo theo sha1 để bìa còn lại không đo lại). Kênh chưa đủ 3 video đạt
   → giữ bộ đang có (mượn kênh gốc) — đủ thì tự chuyển sang bìa của chính mình.
2. HỌ KIỂU THEO DỮ LIỆU: CTR có trọng số lượt bấm của từng họ trên video ≥ 48 giờ, ≥ 1.000 hiển thị của kênh (kể cả bìa
   máy làm, khi đã đo) → `chon_ho` lấy mẫu Thompson (phần lớn là họ tốt nhất, thỉnh thoảng họ khác để kênh vẫn học)
   cho mỗi lượt, ghi sổ `nghien-cuu/bia-so-cai.json`. `kenh.yaml: bia_lo_kieu` chỉ là đường lùi khi chưa có dữ liệu;
   `bia_lo_kieu_ghim: true` thì giữ đúng kiểu chủ ghim.
3. VÒNG PHẢN HỒI CTR: bìa máy làm (hồ sơ video) ở ~48 giờ và ~7 ngày → `nghien-cuu/bia-ket-qua.jsonl` (họ, bố cục,
   điểm giám khảo, hiển thị, CTR). Báo tương quan điểm giám khảo ↔ CTR. 3 bìa máy mới nhất đều < 0,6 × trung vị CTR
   bìa thắng (mỗi tấm ≥ 1.000 hiển thị) → MỘT báo động (chống lặp theo bộ ba video), lượt kế ÉP thử họ khác, một bài
   học vào não bộ phận "bia".

Dùng:  python -X utf8 -m core.bia_du_lieu chay --kenh K [--thu] [--tam DIR] [--khong-ai] [--goc G]
       python -X utf8 -m core.bia_du_lieu tat-ca [--thu] [--tam DIR] [--khong-ai] [--goc G]
       (--thu: CHỈ ĐỌC — không ghi thư mục bìa thắng / sổ / thống kê; ảnh chưa có + cache phân loại vào --tam)
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import math
import os
import random
import re
import shutil
import statistics
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

TUOI_TOI_THIEU = 48.0
IMP_THANG, IMP_THONG_KE = 3000.0, 1000.0
SO_THANG_TOI_DA, SO_THANG_TOI_THIEU = 6, 3
#: Họ kiểu chữ bìa (nhãn AI): chữ trần viền dày | chữ trên DẢI màu rộng | chữ trong HỘP khít từng dòng.
HO = ("tran", "dai", "hop")
#: Xác suất tối thiểu thử họ hạng nhì (ngoài phần khám phá tự nhiên của mẫu Thompson).
EPSILON = 0.1
#: Báo động + ép khám phá: `SO_BIA_TUT` bìa máy mới nhất (mỗi tấm ≥ `IMP_BIA_TUT` hiển thị, ≥ 48 giờ) đều có CTR
#: < `HE_SO_TUT` × trung vị CTR bìa thắng.
HE_SO_TUT, SO_BIA_TUT, IMP_BIA_TUT = 0.6, 3, 1000.0
TUOI_7_NGAY = 168.0
TEP_BANG = "bang-tom-tat.csv"
TEP_THONG_KE = "bia-kieu.json"
TEP_SO_CAI = "bia-so-cai.json"
TEP_KET_QUA = "bia-ket-qua.jsonl"
TEP_PHAN_LOAI = os.path.join("workspace", "bia-kieu", "phan-loai.json")
TEP_DS_THANG = "thang.json"
#: Tệp đệm suy từ bộ bìa thắng — bộ đổi thì bỏ (đã sao lưu) để máy dựng lại theo bộ mới.
TEP_DEM_BO = ("mau-bia-thang.json", "san-bam.json")
TEP_BO_CUC_THANG = "bo-cuc-thang.json"
PHIEN_BAN = 1
PHIEN_BAN_PHAN_LOAI = 1
NHOM_PHAN_LOAI = 6
MO_HINH_PHAN_LOAI = "claude-sonnet-5"
_DUOI_ANH = (".jpg", ".jpeg", ".png", ".webp")
#: Màu dải/hộp theo nhãn AI (khi chưa đo được trên điểm ảnh).
MAU_DAI = {"red": "#B3191E", "green": "#1E6B3A", "yellow": "#E8B400", "black": "#161616", "blue": "#1C4E9C",
           "white": "#F2F2F2", "orange": "#E0650F", "purple": "#5B2A86"}
MAU_DAI_MAC_DINH = "#B3191E"

LOI_NHAC_PHAN_LOAI = """These {n} images are YouTube thumbnails, numbered 1 to {n} in the order shown. For EACH one, \
classify how its big text is drawn:
"kieu": "tran" = the letters stand directly on the picture with only an outline or shadow (one brush stroke behind a \
single keyword line still counts as tran); "dai" = most text lines sit on wide solid colour BANDS or stripes that run \
across a large part of the frame width; "hop" = the text lines sit inside separate tight solid boxes or plates (one box \
per line or phrase); "khac" = no big text, or something else.
"nen": overall brightness of the picture behind the text: "toi" (dark) | "vua" (medium) | "sang" (bright).
"mau_dai": colour of the bands or boxes: red | green | yellow | black | blue | white | orange | purple | other | none.
"ta_nen": ONE English sentence (at most 30 words) describing the background look (colours, light, mood) as an \
instruction for an image model — no text, no layout.
Return JSON only: {{"bia": [{{"so": 1, "kieu": "tran", "nen": "sang", "mau_dai": "none", "ta_nen": "..."}}]}} — one \
item per image."""


# ── tiện ích ────────────────────────────────────────────────────────────────


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with io.open(duong + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tmp", duong)


def sha1_tep(duong: str) -> str:
    h = hashlib.sha1()  # noqa: S324 — nhận diện tệp, không mật mã
    try:
        with open(duong, "rb") as tep:
            for khoi in iter(lambda: tep.read(1 << 16), b""):
                h.update(khoi)
    except OSError:
        return ""
    return h.hexdigest()


def _so(v: Any) -> Optional[float]:
    s = str(v if v is not None else "").strip().replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def luot_bam(r: Dict[str, Any]) -> float:
    return float(r.get("imp") or 0) * float(r.get("ctr") or 0) / 100.0


def _trung_vi(xs: Sequence[float]) -> Optional[float]:
    xs = [float(x) for x in xs if x is not None]
    return round(float(statistics.median(xs)), 3) if xs else None


def thu_muc_nc(goc: str, kenh: str) -> str:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415
    return thu_muc_nghien_cuu(goc, kenh)


def _kenh_yaml(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        return doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        return {}


# ── 1) Bảng Studio của kênh ──────────────────────────────────────────────────


def duong_bang(goc: str, kenh: str) -> str:
    from .kenh import duong_kenh  # noqa: PLC0415
    return os.path.join(duong_kenh(goc, kenh), "chi-so", TEP_BANG)


def _tuoi(d: Dict[str, Any], bay: _dt.datetime) -> Optional[float]:
    """Tuổi video (giờ) ở bản chụp mới nhất: cột "Mốc mới nhất" (`"46h"`), không có thì theo ngày đăng."""
    m = re.search(r"([\d.]+)\s*h", str(d.get("Mốc mới nhất") or ""), re.I)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    try:
        ng = _dt.datetime.strptime(str(d.get("Ngày đăng") or "")[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return max(0.0, (bay - ng).total_seconds() / 3600.0)


def doc_bang(goc: str, kenh: str, bay: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Video ĐÃ ĐĂNG của kênh (bản chụp mới nhất): `[{video_id, ngay, tuoi, imp, ctr, tieu_de}]` — đã lọc video đời
    trước (`chi_so_ytb.loc_video`, mốc `ngay_bat_dau` của kênh). Không có bảng → []."""
    bay = bay or _dt.datetime.now()
    p = duong_bang(goc, kenh)
    try:
        with io.open(p, encoding="utf-8-sig") as tep:
            hang = list(csv.DictReader(tep))
    except OSError:
        return []
    try:
        from .chi_so_ytb import loc_video as _loc  # noqa: PLC0415
        hang = _loc.loc_hang_bang(_loc.moc_cua_thu_muc(os.path.dirname(os.path.dirname(p))), hang)
    except Exception:  # noqa: BLE001 — lọc hỏng: bảng thô
        pass
    ra: List[Dict[str, Any]] = []
    da: set = set()
    for d in hang:
        vid = str(d.get("Mã video") or "").strip()
        if not vid or vid in da:
            continue
        da.add(vid)
        ra.append({"video_id": vid, "ngay": str(d.get("Ngày đăng") or "")[:10], "tuoi": _tuoi(d, bay),
                   "imp": _so(d.get("Lượt hiển thị")) or 0.0, "ctr": _so(d.get("Tỷ lệ bấm")) or 0.0,
                   "tieu_de": " ".join(str(d.get("Tiêu đề") or "").split())[:120]})
    return ra


def co_so(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Video đủ chín để đo bìa: ≥ 48 giờ, ≥ 1.000 hiển thị."""
    return [r for r in rows if (r.get("tuoi") or 0) >= TUOI_TOI_THIEU and float(r.get("imp") or 0) >= IMP_THONG_KE]


def chon_thang(rows: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """(bìa thắng xếp theo lượt bấm, trung vị CTR kênh): video ≥ 48 giờ, ≥ 3.000 hiển thị, CTR ≥ trung vị (video
    ≥ 48 giờ, ≥ 1.000 hiển thị), tối đa `SO_THANG_TOI_DA`; thiếu `SO_THANG_TOI_THIEU` thì bù theo lượt bấm."""
    cs = co_so(rows)
    tv = _trung_vi([r["ctr"] for r in cs])
    du = sorted((r for r in cs if float(r["imp"]) >= IMP_THANG), key=lambda r: -luot_bam(r))
    tren = [r for r in du if tv is None or r["ctr"] >= tv]
    chon = tren[:SO_THANG_TOI_DA]
    if len(chon) < SO_THANG_TOI_THIEU:
        chon += [r for r in du if r not in chon][:SO_THANG_TOI_THIEU - len(chon)]
    chon.sort(key=lambda r: -luot_bam(r))
    return chon, tv


# ── 2) Ảnh bìa thật + nhãn họ kiểu chữ ───────────────────────────────────────


def tai_bia(goc: str, kenh: str, vid: str, *, tam: str = "",
            tai_anh: Optional[Callable[[str], Optional[bytes]]] = None) -> str:
    """Bìa THẬT đang chạy của video. Chạy thật: tải lại (`khuon_bia.anh_that` — chủ có thể đã đổi bìa). Chạy thử
    (`tam`): dùng bản đã lưu của kênh nếu có (chỉ đọc), không thì tải vào `tam`."""
    from . import khuon_bia  # noqa: PLC0415
    if not tam:
        return khuon_bia.anh_that(goc, kenh, vid, tai_anh=tai_anh)
    p = khuon_bia.duong_anh_that(goc, kenh, vid)
    if os.path.isfile(p):
        return p
    dich = os.path.join(tam, "anh", kenh, "{0}.jpg".format(vid))
    if os.path.isfile(dich):
        return dich
    tai = tai_anh or khuon_bia._tai_url  # noqa: SLF001
    for co in ("maxresdefault", "hqdefault"):
        du = tai("https://i.ytimg.com/vi/{0}/{1}.jpg".format(vid, co))
        if du:
            os.makedirs(os.path.dirname(dich), exist_ok=True)
            with open(dich, "wb") as tep:
                tep.write(du)
            return dich
    return ""


def doc_phan_loai(du: Any, n: int) -> Dict[int, Dict[str, str]]:
    ds = (du.get("bia") if isinstance(du, dict) else du) or []
    ra: Dict[int, Dict[str, str]] = {}
    for x in ds if isinstance(ds, list) else []:
        try:
            so = int(x.get("so"))
        except (AttributeError, TypeError, ValueError):
            continue
        k = str(x.get("kieu") or "").strip().lower()
        if not 1 <= so <= n or so in ra or k not in HO + ("khac",):
            continue
        nen = str(x.get("nen") or "").strip().lower()
        md = str(x.get("mau_dai") or "").strip().lower()
        ra[so] = {"kieu": k, "nen": nen if nen in ("toi", "vua", "sang") else "",
                  "mau_dai": md if md in MAU_DAI else "", "ta_nen": " ".join(str(x.get("ta_nen") or "").split())[:240]}
    return ra


def phan_loai(teps: Sequence[str], *, goi: Optional[Callable[..., str]], cache: str,
              log: Callable[[str], None] = print, cache_doc: Sequence[str] = ()) -> Dict[str, Dict[str, Any]]:
    """Nhãn họ kiểu chữ của từng ảnh `{tep: {kieu, nen, mau_dai, ta_nen, sha1}}` — cache theo sha1 (`cache`, cùng cho
    mọi kênh; `cache_doc` = cache chỉ đọc thêm, cho chạy thử). Ảnh chưa có nhãn + có `goi` → AI nhìn theo nhóm
    `NHOM_PHAN_LOAI` ảnh / lượt, ép ví ShopAPI (`goi_van_ban.qua_vi`). Không `goi` / lượt hỏng → ảnh ấy không nhãn."""
    kho = _doc_json(cache)
    anh: Dict[str, Any] = dict((kho or {}).get("anh") or {}) if isinstance(kho, dict) else {}
    for c in cache_doc:
        du = _doc_json(c)
        for s, v in ((du or {}).get("anh") or {}).items() if isinstance(du, dict) else ():
            anh.setdefault(s, v)
    sha = {t: sha1_tep(t) for t in teps if t and os.path.isfile(t)}
    thieu = list({s: t for t, s in sha.items() if s and s not in anh}.values())
    if goi is not None and thieu:
        from .bia_lo import _json, _url_anh  # noqa: PLC0415
        from .goi_van_ban import qua_vi  # noqa: PLC0415
        moi = 0
        for i in range(0, len(thieu), NHOM_PHAN_LOAI):
            g = thieu[i:i + NHOM_PHAN_LOAI]
            try:
                with qua_vi():
                    tho = goi(LOI_NHAC_PHAN_LOAI.format(n=len(g)), khoa="bia-kieu-v{0}:{1}".format(
                        PHIEN_BAN_PHAN_LOAI, hashlib.sha1("|".join(sha[t] for t in g).encode()).hexdigest()[:16]),
                        toi_da_token=1800, mo_hinh=MO_HINH_PHAN_LOAI, anh=[_url_anh(t, 512) for t in g])
                kq = doc_phan_loai(_json(tho), len(g))
            except Exception as loi:  # noqa: BLE001 — một nhóm hỏng: ảnh ấy chưa nhãn, lần sau thử lại
                log("  (bìa dữ liệu: phân loại kiểu chữ hỏng: {0})".format(str(loi)[:160]))
                continue
            for j, t in enumerate(g, 1):
                if j in kq:
                    anh[sha[t]] = dict(kq[j], luc=time.strftime("%Y-%m-%d %H:%M:%S"), phien_ban=PHIEN_BAN_PHAN_LOAI)
                    moi += 1
        if moi:
            _ghi_json(cache, {"phien_ban": PHIEN_BAN_PHAN_LOAI, "anh": anh})
    return {t: dict(anh.get(s) or {}, sha1=s) for t, s in sha.items()}


# ── 3) Thống kê họ kiểu chữ + chọn họ cho một lượt ───────────────────────────


def thong_ke_ho(cs: Sequence[Dict[str, Any]], nhan: Dict[str, Dict[str, Any]],
                may: Sequence[str] = ()) -> Dict[str, Dict[str, Any]]:
    """CTR có trọng số lượt bấm (Σ lượt bấm / Σ hiển thị) của từng họ trên video đủ chín `cs` (nhãn theo video_id)."""
    ho: Dict[str, Dict[str, Any]] = {}
    for r in cs:
        k = str((nhan.get(r["video_id"]) or {}).get("kieu") or "")
        if k not in HO:
            continue
        h = ho.setdefault(k, {"n": 0, "imp": 0.0, "bam": 0.0, "may": 0, "ctr_ds": []})
        h["n"] += 1
        h["imp"] += float(r["imp"])
        h["bam"] += luot_bam(r)
        h["may"] += 1 if r["video_id"] in may else 0
        h["ctr_ds"].append(round(float(r["ctr"]), 2))
    for h in ho.values():
        h["ctr"] = round(100.0 * h["bam"] / h["imp"], 3) if h["imp"] else None
        h["imp"], h["bam"] = round(h["imp"]), round(h["bam"])
    return ho


def hau_nghiem(tk: Dict[str, Any], co: Sequence[str]) -> Dict[str, Tuple[float, float]]:
    """(trung bình, độ lệch) hậu nghiệm CTR của từng họ: co về trung vị kênh như MỘT video tiên nghiệm; độ lệch = độ
    lệch CTR giữa các video của kênh / √(n + 1). Số video `n` tính theo HIỂN THỊ (Σ hiển thị của họ / trung vị hiển
    thị một video của kênh, không quá số video): vài video ít hiển thị (CTR ít hiển thị thường cao ảo) không lật kiểu
    chữ của cả kênh."""
    m0 = float(tk.get("trung_vi_ctr") or 0.0)
    s0 = max(0.5, float(tk.get("do_lech_ctr") or 0.0))
    tv_imp = float(tk.get("trung_vi_imp") or 0.0)
    ra = {}
    ab = tk.get("ab") if isinstance(tk.get("ab"), dict) else {}
    for h in co:
        x = (tk.get("ho") or {}).get(h) or {}
        n = float(x.get("n") or 0)
        if n and tv_imp > 0:
            n = min(n, float(x.get("imp") or 0) / tv_imp)
        xb = float(x.get("ctr") or m0) if n else m0
        # 21/10/2026 (G4): cặp thắng/thua THẬT từ Thử nghiệm A/B 3 bìa (`core.bia_ab.thong_ke_ho_ab`, chỉ cặp khác
        # họ) dịch trung bình — tối đa ±½ độ lệch CTR kênh khi đủ `bia_ab.N_AB_DU` cặp.
        dich = 0.0
        if ab:
            try:
                from .bia_ab import dich_hau_nghiem  # noqa: PLC0415
                dich = dich_hau_nghiem(ab, h, s0)
            except Exception:  # noqa: BLE001
                dich = 0.0
        ra[h] = ((n * xb + m0) / (n + 1.0) + dich, s0 / math.sqrt(n + 1.0))
    return ra


#: Họ có bằng chứng dưới ngần này "video quy đổi theo hiển thị" chỉ được thử ở nhánh khám phá ε, không vào Thompson
#: (20/10: TL3 họ "hop" chỉ 4 video ít hiển thị mà Thompson cho 53% số bìa của kênh mạnh nhất).
N_TOI_THIEU_THOMPSON = 2.0


def n_quy_doi(tk: Dict[str, Any], h: str) -> float:
    """Số video của họ `h` quy đổi theo hiển thị (như `hau_nghiem`)."""
    x = (tk.get("ho") or {}).get(h) or {}
    n = float(x.get("n") or 0)
    tv_imp = float(tk.get("trung_vi_imp") or 0.0)
    return min(n, float(x.get("imp") or 0) / tv_imp) if n and tv_imp > 0 else n


def duong_thong_ke(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nc(goc, kenh), TEP_THONG_KE)


def doc_thong_ke(goc: str, kenh: str) -> Dict[str, Any]:
    du = _doc_json(duong_thong_ke(goc, kenh))
    return du if isinstance(du, dict) else {}


def duong_so_cai(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nc(goc, kenh), TEP_SO_CAI)


def doc_so_cai(goc: str, kenh: str) -> Dict[str, Any]:
    du = _doc_json(duong_so_cai(goc, kenh))
    return du if isinstance(du, dict) else {}


def ghi_so_cai(goc: str, kenh: str, luot: str, muc: Dict[str, Any]) -> None:
    """Gộp `muc` vào dòng sổ của lượt `luot` (mã lượt, vd "0031"). Không ném lỗi."""
    try:
        sc = doc_so_cai(goc, kenh)
        sc[luot] = dict(sc.get(luot) or {}, **muc)
        _ghi_json(duong_so_cai(goc, kenh), sc)
    except Exception:  # noqa: BLE001
        pass


def ho_trong_thu_muc(tm: str) -> List[str]:
    """Các họ có ≥ 1 bìa thắng trong thư mục (theo nhãn `thang.json`) — chỉ họ có ảnh tham chiếu mới vẽ được."""
    du = _doc_json(os.path.join(tm, TEP_DS_THANG)) if tm else None
    ds = [str((b or {}).get("kieu") or "") for b in ((du or {}).get("bia") or []) if isinstance(b, dict)] \
        if isinstance(du, dict) else []
    return [h for h in HO if h in ds]


def chon_ho(goc: str, kenh: str, *, co: Sequence[str], luot: str = "", ghi: bool = False,
            cai: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Họ kiểu chữ cho một lượt → `{ho, cach, ly_do}` ({} = chưa có dữ liệu: dùng `kenh.yaml: bia_lo_kieu`).

    Thứ tự: `bia_lo_kieu_ghim: true` (chủ ghim) > sổ của lượt (`bia-so-cai.json` — hai lần gọi của một lượt, lô làm
    lại, đều cùng họ) > ÉP khám phá (bìa máy tụt, `ep_doi_kieu`, một lượt) > mẫu Thompson trên CTR hậu nghiệm từng họ
    (hạt giống = kênh + lượt; xác suất `EPSILON` lấy họ hạng nhì). Không có `luot` → họ tốt nhất (tất định)."""
    cai = cai if cai is not None else _kenh_yaml(goc, kenh)
    k_cai = str(cai.get("bia_lo_kieu") or "").strip()
    if cai.get("bia_lo_kieu_ghim") is True and k_cai in HO:
        return {"ho": k_cai, "cach": "ghim", "ly_do": "kenh.yaml ghim bia_lo_kieu"}
    co = [h for h in dict.fromkeys(co or ()) if h in HO]
    tk = doc_thong_ke(goc, kenh)
    if not co or not tk or not any(int(((tk.get("ho") or {}).get(h) or {}).get("n") or 0) for h in co):
        return {}
    khoa = os.path.basename(os.path.normpath(luot)) if luot else ""
    cu = (doc_so_cai(goc, kenh).get(khoa) or {}) if khoa else {}
    if cu.get("ho") in co and cu.get("cach"):
        return {"ho": cu["ho"], "cach": cu["cach"], "ly_do": cu.get("ly_do") or "đã chọn cho lượt này"}
    hn = hau_nghiem(tk, co)
    xep = sorted(co, key=lambda h: -hn[h][0])
    ep = tk.get("ep_doi_kieu") if isinstance(tk.get("ep_doi_kieu"), dict) else {}
    khac = [h for h in xep if h != ep.get("tranh")] if ep.get("tranh") else []
    if ep.get("tranh") and khac and (not ep.get("da_dung") or ep.get("da_dung") == khoa):
        kq = {"ho": khac[0], "cach": "kham-pha-ep",
              "ly_do": "3 bìa máy họ {0} CTR < {1:.0%} trung vị bìa thắng → thử họ khác".format(ep["tranh"], HE_SO_TUT)}
        if ghi and khoa:
            try:
                tk["ep_doi_kieu"] = dict(ep, da_dung=khoa)
                _ghi_json(duong_thong_ke(goc, kenh), tk)
            except OSError:
                pass
    elif not khoa or len(xep) == 1:
        kq = {"ho": xep[0], "cach": "tot-nhat", "ly_do": "CTR hậu nghiệm cao nhất ({0:.2f}%)".format(hn[xep[0]][0])}
    else:
        rng = random.Random(int(hashlib.sha1("{0}|{1}".format(kenh, khoa).encode("utf-8")).hexdigest()[:12], 16))
        if rng.random() < EPSILON:
            kq = {"ho": xep[1], "cach": "kham-pha", "ly_do": "thử họ hạng nhì (ε={0})".format(EPSILON)}
        else:
            du_bc = [x for x in xep if n_quy_doi(tk, x) >= N_TOI_THIEU_THOMPSON] or xep
            rut = {h: rng.gauss(*hn[h]) for h in du_bc}
            h = max(du_bc, key=lambda x: rut[x])
            kq = {"ho": h, "cach": "thompson", "ly_do": "mẫu Thompson: " + ", ".join(
                "{0} {1:.2f}%".format(x, rut[x]) for x in du_bc)}
    kq["hau_nghiem"] = {h: [round(hn[h][0], 3), round(hn[h][1], 3)] for h in xep}
    if ghi and khoa:
        ghi_so_cai(goc, kenh, khoa, {"ho": kq["ho"], "cach": kq["cach"], "ly_do": kq["ly_do"],
                                     "luc_chon": time.strftime("%Y-%m-%d %H:%M:%S")})
    return kq


def ho_phu(goc: str, kenh: str, *, co: Sequence[str], ho_chinh: str, kieu: str = "tran",
           cai: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """21/10/2026 (G4 — mỗi ván A/B dạy cả HỌ): họ HẠNG NHÌ cho bộ bìa phụ của lô → `{ho, ly_do}` ({} = không vẽ phụ).
    Chỉ khi thư mục bìa thắng có ≥ 2 họ (`co` = `ho_trong_thu_muc`) và chủ không ghim kiểu (`bia_lo_kieu_ghim`). Tất
    định (không rút ngẫu nhiên — họ của LÔ vẫn là bản ghi `chon_ho` của lượt): họ khác `ho_chinh` có CTR hậu nghiệm
    cao nhất; chưa có thống kê → họ khác đầu tiên của thư mục (thứ tự `HO`). Kênh vẽ kiểu hộp:
    "dai"/"hop" cùng nhà (cùng bộ vẽ) → không tính là họ khác."""
    cai = cai if cai is not None else _kenh_yaml(goc, kenh)
    if cai.get("bia_lo_kieu_ghim") is True:
        return {}
    co = [h for h in dict.fromkeys(co or ()) if h in HO]
    if len(co) < 2:
        return {}
    cung_nha = (lambda a, b: kieu == "hop" and {a, b} <= {"dai", "hop"})
    khac = [h for h in co if h != ho_chinh and not cung_nha(h, ho_chinh)]
    if not khac:
        return {}
    tk = doc_thong_ke(goc, kenh)
    if tk and any(int(((tk.get("ho") or {}).get(h) or {}).get("n") or 0) for h in co):
        hn = hau_nghiem(tk, khac)
        h = max(khac, key=lambda x: (hn[x][0], -HO.index(x)))
        return {"ho": h, "ly_do": "họ hạng nhì theo CTR hậu nghiệm ({0:.2f}%) — bìa phụ cho A/B".format(hn[h][0])}
    return {"ho": khac[0], "ly_do": "thư mục bìa thắng có họ {0} — bìa phụ cho A/B (chưa có thống kê CTR)".format(
        khac[0])}


# ── 4) Vòng phản hồi CTR ─────────────────────────────────────────────────────


def video_may(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """Video MÁY làm (hồ sơ video có video_id): `{video_id: {luot, ma_goi, ngay_ho_so, chi_so, thumb, doi_bia}}`."""
    from .ho_so_video import duong_thu_muc_ho_so  # noqa: PLC0415
    tm = duong_thu_muc_ho_so(goc, kenh)
    ra: Dict[str, Dict[str, Any]] = {}
    try:
        ten = sorted(t for t in os.listdir(tm) if t.endswith(".json"))
    except OSError:
        return ra
    for t in ten:
        d = _doc_json(os.path.join(tm, t))
        if not isinstance(d, dict) or not d.get("video_id"):
            continue
        ma = t[:-5]
        ra[str(d["video_id"])] = {
            "luot": str(d.get("luot") or ma.rsplit("-", 1)[-1]), "ma_goi": ma,
            "chi_so": d.get("chi_so") if isinstance(d.get("chi_so"), dict) else {},
            "thumb": d.get("thumbnail") if isinstance(d.get("thumbnail"), dict) else {},
            "doi_bia": any(isinstance(x, dict) and x.get("loai") == "bia" for x in d.get("lich_su_sua") or [])}
    return ra


def duong_ket_qua(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nc(goc, kenh), TEP_KET_QUA)


def doc_ket_qua(goc: str, kenh: str) -> List[Dict[str, Any]]:
    try:
        with io.open(duong_ket_qua(goc, kenh), encoding="utf-8") as tep:
            dong = tep.readlines()
    except OSError:
        return []
    ra = []
    for d in dong:
        try:
            x = json.loads(d)
        except ValueError:
            continue
        if isinstance(x, dict):
            ra.append(x)
    return ra


def dong_ket_qua_moi(rows: Sequence[Dict[str, Any]], may: Dict[str, Dict[str, Any]], nhan: Dict[str, Dict[str, Any]],
                     so_cai: Dict[str, Any], cu: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dòng phản hồi CHƯA ghi cho bìa máy làm: mốc "48h" (số đo 48h của hồ sơ video nếu có, không thì bảng Studio khi
    video < 7 ngày) và mốc "7d" (bảng Studio khi video ≥ 7 ngày). Mỗi (video, mốc) một lần."""
    da = {(x.get("video_id"), x.get("moc")) for x in cu}
    ra: List[Dict[str, Any]] = []
    for r in rows:
        m = may.get(r["video_id"])
        tuoi = float(r.get("tuoi") or 0)
        if not m or tuoi < TUOI_TOI_THIEU:
            continue
        sc = so_cai.get(m["luot"]) or {}
        top = (sc.get("top") or [{}])[0] if sc.get("top") else {}
        chung = {"video_id": r["video_id"], "luot": m["luot"], "ngay": r["ngay"],
                 "kieu": str((nhan.get(r["video_id"]) or {}).get("kieu") or ""), "kieu_chon": sc.get("ho") or "",
                 "cach": sc.get("cach") or "", "bo_cuc": sc.get("bo_cuc") or "", "diem": top.get("diem") or {},
                 "tong": top.get("tong") if top else m["thumb"].get("diem_giam_khao"),
                 "nguon_diem": "so-cai" if top else ("ho-so" if m["thumb"].get("diem_giam_khao") is not None else ""),
                 "doi_bia": bool(m["doi_bia"]) or bool(sc.get("ho") and (nhan.get(r["video_id"]) or {}).get("kieu")
                                                     and sc.get("ho") != nhan[r["video_id"]].get("kieu")),
                 "luc": time.strftime("%Y-%m-%d %H:%M:%S")}
        if (r["video_id"], "48h") not in da:
            c48 = (m["chi_so"] or {}).get("48h") or {}
            if c48.get("impressions") is not None and c48.get("ctr") is not None:
                ra.append(dict(chung, moc="48h", tuoi=c48.get("moc_gio_that"), imp=float(c48["impressions"]),
                               ctr=float(c48["ctr"]), nguon_so="ho-so"))
            elif tuoi < TUOI_7_NGAY:
                ra.append(dict(chung, moc="48h", tuoi=tuoi, imp=r["imp"], ctr=r["ctr"], nguon_so="studio"))
        if tuoi >= TUOI_7_NGAY and (r["video_id"], "7d") not in da:
            ra.append(dict(chung, moc="7d", tuoi=tuoi, imp=r["imp"], ctr=r["ctr"], nguon_so="studio"))
    return ra


def _hang(xs: Sequence[float]) -> List[float]:
    thu = sorted(range(len(xs)), key=lambda i: xs[i])
    h = [0.0] * len(xs)
    i = 0
    while i < len(thu):
        j = i
        while j + 1 < len(thu) and xs[thu[j + 1]] == xs[thu[i]]:
            j += 1
        for k in range(i, j + 1):
            h[thu[k]] = (i + j) / 2.0
        i = j + 1
    return h


def spearman(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    if len(a) < 4 or len(a) != len(b):
        return None
    ra, rb = _hang(a), _hang(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    sa = math.sqrt(sum((x - ma) ** 2 for x in ra))
    sb = math.sqrt(sum((x - mb) ** 2 for x in rb))
    if not sa or not sb:
        return None
    return round(sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (sa * sb), 3)


def tuong_quan(kq: Sequence[Dict[str, Any]], moc: str = "48h") -> Dict[str, Any]:
    """Tương quan hạng (Spearman) điểm giám khảo ↔ CTR trên các bìa máy đã đo ở `moc` (≥ 1.000 hiển thị)."""
    ds = [x for x in kq if x.get("moc") == moc and float(x.get("imp") or 0) >= IMP_BIA_TUT]
    ra: Dict[str, Any] = {"moc": moc}
    for ten, lay in (("bam_nhu_thang", lambda x: (x.get("diem") or {}).get("bam_nhu_thang")),
                     ("tong", lambda x: x.get("tong"))):
        cap = [(float(lay(x)), float(x["ctr"])) for x in ds if isinstance(lay(x), (int, float))]
        ra[ten] = {"n": len(cap), "rho": spearman([c[0] for c in cap], [c[1] for c in cap])}
    return ra


def kiem_tut(rows: Sequence[Dict[str, Any]], may: Dict[str, Any], nhan: Dict[str, Dict[str, Any]],
             tv_thang: Optional[float]) -> Optional[Dict[str, Any]]:
    """`SO_BIA_TUT` bìa máy mới nhất (≥ 48 giờ, ≥ `IMP_BIA_TUT` hiển thị) đều có CTR < `HE_SO_TUT` × trung vị CTR bìa
    thắng → {khoa (bộ ba video), video, nguong, tranh (họ chiếm đa số)}; không → None."""
    if not tv_thang:
        return None
    ds = sorted((r for r in rows if r["video_id"] in may and (r.get("tuoi") or 0) >= TUOI_TOI_THIEU
                 and float(r["imp"]) >= IMP_BIA_TUT), key=lambda r: r["ngay"], reverse=True)[:SO_BIA_TUT]
    nguong = HE_SO_TUT * float(tv_thang)
    if len(ds) < SO_BIA_TUT or any(float(r["ctr"]) >= nguong for r in ds):
        return None
    ho = [str((nhan.get(r["video_id"]) or {}).get("kieu") or "") for r in ds]
    ho = [h for h in ho if h in HO]
    return {"khoa": "|".join(sorted(r["video_id"] for r in ds)), "nguong": round(nguong, 2),
            "video": [{"video_id": r["video_id"], "ctr": r["ctr"], "imp": r["imp"],
                       "kieu": (nhan.get(r["video_id"]) or {}).get("kieu") or ""} for r in ds],
            "tranh": max(set(ho), key=ho.count) if ho else ""}


# ── 5) Thư mục bìa thắng ─────────────────────────────────────────────────────


def _duong_mau_kenh(goc: str, kenh: str, cai: Optional[Dict[str, Any]] = None) -> str:
    """Thư mục bìa thắng RIÊNG của kênh: `kenh.yaml: bia_lo_mau` (tương đối theo gốc) hoặc thư mục theo nếp — không
    lùi sang thư mục kênh gốc như `bia_lo.thu_muc_mau` (ghi vào đó là ghi đè bìa thắng của kênh khác)."""
    from .bia_lo import ten_thu_muc_thang  # noqa: PLC0415
    cai = cai if cai is not None else _kenh_yaml(goc, kenh)
    d = str(cai.get("bia_lo_mau") or "").strip()
    d = os.path.join(goc, d) if d and not os.path.isabs(d) else d
    return os.path.abspath(d or os.path.join(goc, ten_thu_muc_thang(kenh)))


def thu_muc_dich(goc: str, kenh: str) -> Tuple[str, str]:
    """(thư mục bìa thắng của kênh, lý do KHÔNG được ghi — '' = ghi được)."""
    p = _duong_mau_kenh(goc, kenh)
    try:
        from .kenh import liet_ke_kenh  # noqa: PLC0415
        for k in liet_ke_kenh(goc):
            if k != kenh and os.path.normcase(_duong_mau_kenh(goc, k)) == os.path.normcase(p):
                return p, "thư mục dùng chung với kênh {0} — không ghi đè".format(k)
    except Exception:  # noqa: BLE001
        pass
    return p, ""


def doc_thu_muc(tm: str) -> List[Dict[str, Any]]:
    du = _doc_json(os.path.join(tm, TEP_DS_THANG)) if tm else None
    ra = []
    for b in ((du or {}).get("bia") or []) if isinstance(du, dict) else []:
        if isinstance(b, dict) and b.get("tep") and os.path.isfile(os.path.join(tm, str(b["tep"]))):
            ra.append(dict(b, _duong=os.path.join(tm, str(b["tep"]))))
    return ra


def _muc_thang(i: int, r: Dict[str, Any], tep: str, nh: Dict[str, Any]) -> Dict[str, Any]:
    return {"tep": "{0}-{1}{2}".format(i, re.sub(r"[^A-Za-z0-9_-]", "_", r["video_id"]), os.path.splitext(tep)[1]
                                       or ".jpg"),
            "video_id": r["video_id"], "ngay": r["ngay"], "imp": int(r["imp"]), "ctr": round(float(r["ctr"]), 2),
            "luot_bam": round(luot_bam(r)), "tuoi": r.get("tuoi"), "tieu_de": r.get("tieu_de") or "",
            "kieu": nh.get("kieu") or "", "nen": nh.get("nen") or "", "mau_dai": nh.get("mau_dai") or "",
            "ta_nen": nh.get("ta_nen") or "", "sha1": nh.get("sha1") or sha1_tep(tep)}


def ghi_thu_muc(tm: str, kenh: str, bia: Sequence[Tuple[Dict[str, Any], str, Dict[str, Any]]], *, tv: Optional[float],
                log: Callable[[str], None] = print) -> str:
    """Ghi bộ bìa thắng `bia` [(dòng bảng, tệp ảnh thật, nhãn)] vào `tm`. Cùng video + cùng ảnh (sha1) như bộ đang có →
    chỉ cập nhật số liệu/nhãn ("cap-nhat"/"giu"). Khác → sao lưu cả thư mục cũ, bỏ ảnh + tệp đệm cũ, chép ảnh mới,
    số đo bố cục cũ giữ theo sha1 ("doi")."""
    cu = doc_thu_muc(tm)
    moi = [_muc_thang(i, r, tep, nh) for i, (r, tep, nh) in enumerate(bia, 1)]
    cu_sha = [(b.get("video_id"), b.get("sha1") or sha1_tep(b["_duong"])) for b in cu]
    nguon = "dữ liệu Studio (core/bia_du_lieu) {0}: video ≥ 48 giờ, ≥ 3.000 hiển thị, CTR ≥ trung vị kênh{1}, xếp " \
            "theo lượt bấm; ảnh bìa THẬT i.ytimg.com; KHÔNG lọc kiểu".format(
                time.strftime("%Y-%m-%d"), " ({0}%)".format(tv) if tv is not None else "")
    if cu_sha == [(m["video_id"], m["sha1"]) for m in moi]:
        for m, b in zip(moi, cu):
            m["tep"] = b["tep"]
        du = {"kenh": kenh, "tu_dong": True, "phien_ban": PHIEN_BAN, "nguon": nguon, "trung_vi_ctr": tv, "bia": moi}
        cu_du = _doc_json(os.path.join(tm, TEP_DS_THANG)) or {}
        if {k: v for k, v in cu_du.items() if k != "luc"} == du:
            return "giu"
        _ghi_json(os.path.join(tm, TEP_DS_THANG), dict(du, luc=time.strftime("%Y-%m-%d %H:%M:%S")))
        return "cap-nhat"
    if os.path.isdir(tm) and os.listdir(tm):
        sl = os.path.join(os.path.dirname(tm), os.path.basename(tm) + "-sao-luu", time.strftime("%Y%m%d-%H%M%S"))
        shutil.copytree(tm, sl)
        log("  bìa dữ liệu: sao lưu thư mục cũ → {0}".format(sl))
    os.makedirs(tm, exist_ok=True)
    # số đo bố cục cũ: gắn sha1 ảnh của từng mục (ảnh cũ còn trên đĩa) — `bia_lo.bo_cuc_thang` dùng lại theo sha1
    bc = _doc_json(os.path.join(tm, TEP_BO_CUC_THANG))
    if isinstance(bc, dict):
        for x in bc.get("bia") or []:
            if isinstance(x, dict) and x.get("tep") and not x.get("sha1"):
                x["sha1"] = sha1_tep(os.path.join(tm, str(x["tep"])))
        bc["khoa"] = "cu:" + str(bc.get("khoa") or "")
        _ghi_json(os.path.join(tm, TEP_BO_CUC_THANG), bc)
    for t in os.listdir(tm):
        if t.lower().endswith(_DUOI_ANH) or t in TEP_DEM_BO:
            try:
                os.remove(os.path.join(tm, t))
            except OSError:
                pass
    for m, (_r, tep, _nh) in zip(moi, bia):
        shutil.copy2(tep, os.path.join(tm, m["tep"]))
    _ghi_json(os.path.join(tm, TEP_DS_THANG), {"kenh": kenh, "tu_dong": True, "phien_ban": PHIEN_BAN, "nguon": nguon,
                                               "trung_vi_ctr": tv, "bia": moi,
                                               "luc": time.strftime("%Y-%m-%d %H:%M:%S")})
    return "doi"


def gan_nhan_thu_muc(tm: str, nhan: Dict[str, Dict[str, Any]]) -> bool:
    """Bộ đang có (mượn) giữ nguyên ảnh — chỉ gắn nhãn họ còn thiếu vào `thang.json` (ảnh tham chiếu theo họ)."""
    du = _doc_json(os.path.join(tm, TEP_DS_THANG))
    if not isinstance(du, dict) or not isinstance(du.get("bia"), list):
        return False
    doi = False
    for b in du["bia"]:
        p = os.path.join(tm, str((b or {}).get("tep") or ""))
        nh = nhan.get(p) or {}
        if isinstance(b, dict) and nh.get("kieu") and b.get("kieu") != nh["kieu"]:
            b.update(kieu=nh["kieu"], nen=nh.get("nen") or "", mau_dai=nh.get("mau_dai") or "",
                     ta_nen=nh.get("ta_nen") or "", sha1=nh.get("sha1") or "")
            doi = True
    if doi:
        _ghi_json(os.path.join(tm, TEP_DS_THANG), du)
    return doi


# ── 6) Một lượt cho MỘT kênh ─────────────────────────────────────────────────


def can_chay(goc: str, kenh: str) -> Tuple[bool, str]:
    """Điều kiện kỹ năng D21 (RẺ, chỉ đọc đĩa): có bảng Studio và bảng mới hơn lần dựng trước."""
    p = duong_bang(goc, kenh)
    if not os.path.isfile(p):
        return False, "kênh chưa có bảng Studio (chi-so/bang-tom-tat.csv)"
    tk = doc_thong_ke(goc, kenh)
    if not tk:
        return True, "chưa dựng bộ bìa thắng theo dữ liệu lần nào"
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return False, "không đọc được bảng Studio"
    if mt > float(tk.get("luc_bang") or 0) + 1:
        return True, "bảng Studio mới ({0})".format(time.strftime("%d/%m %H:%M", time.localtime(mt)))
    return False, "đã dựng theo bảng Studio hiện tại ({0})".format(str(tk.get("luc") or "")[:16])


def chay_kenh(goc: str, kenh: str, *, thu: bool = False, goi: Optional[Callable[..., str]] = None,
              tai_anh: Optional[Callable[[str], Optional[bytes]]] = None, tam: str = "",
              log: Callable[[str], None] = print, bay: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Một lượt D21 cho kênh → báo cáo. `thu=True`: không ghi gì ngoài `tam` (ảnh tải thêm + cache phân loại)."""
    from . import bia_lo  # noqa: PLC0415
    bay = bay or _dt.datetime.now()
    if thu and not tam:
        import tempfile  # noqa: PLC0415
        tam = tempfile.mkdtemp(prefix="bia-du-lieu-")
    rows = doc_bang(goc, kenh, bay)
    cs = co_so(rows)
    chon, tv = chon_thang(rows)
    may = video_may(goc, kenh)
    tm, ly_khong_ghi = thu_muc_dich(goc, kenh)
    tm_dang = bia_lo.thu_muc_mau(goc, kenh) or ""
    cu = doc_thu_muc(tm_dang) if tm_dang else []
    bc: Dict[str, Any] = {"kenh": kenh, "thu": thu, "so_video": len(rows), "so_du_chin": len(cs), "trung_vi_ctr": tv,
                          "thu_muc": tm, "thu_muc_dang": tm_dang, "cu": [{k: b.get(k) for k in ("video_id", "imp", "ctr",
                                                                                                "kieu", "tep")} for b in cu]}
    # ảnh bìa thật: video đủ chín (thống kê họ) + bìa thắng; ảnh bộ đang có (nhãn cho họ của bộ mượn)
    tep: Dict[str, str] = {}
    for r in sorted(cs, key=lambda r: -luot_bam(r)):
        try:
            p = tai_bia(goc, kenh, r["video_id"], tam=tam if thu else "", tai_anh=tai_anh)
        except Exception as loi:  # noqa: BLE001
            log("  (bìa dữ liệu: tải bìa {0} hỏng: {1})".format(r["video_id"], str(loi)[:100]))
            p = ""
        if p:
            tep[r["video_id"]] = p
    cache = os.path.join(tam, "phan-loai.json") if thu else os.path.join(goc, TEP_PHAN_LOAI)
    nh_tep = phan_loai(list(tep.values()) + [b["_duong"] for b in cu], goi=goi, cache=cache, log=log,
                       cache_doc=[os.path.join(goc, TEP_PHAN_LOAI)] if thu else ())
    nhan = {vid: nh_tep.get(p) or {} for vid, p in tep.items()}
    ho = thong_ke_ho(cs, nhan, may=list(may))
    rieng = [r for r in chon if r["video_id"] in tep]
    bc.update(thang=[dict({k: r[k] for k in ("video_id", "ngay", "imp", "ctr")}, luot_bam=round(luot_bam(r)),
                          kieu=(nhan.get(r["video_id"]) or {}).get("kieu") or "?") for r in rieng],
              ho=ho, nguon_thang="rieng" if len(rieng) >= SO_THANG_TOI_THIEU else "giu-bo-dang-co")
    ctr_cs = [float(r["ctr"]) for r in cs]
    tk = {"kenh": kenh, "phien_ban": PHIEN_BAN, "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
          "luc_bang": os.path.getmtime(duong_bang(goc, kenh)) if os.path.isfile(duong_bang(goc, kenh)) else 0,
          "trung_vi_ctr": tv, "do_lech_ctr": round(statistics.pstdev(ctr_cs), 3) if len(ctr_cs) > 1 else None,
          "trung_vi_imp": _trung_vi([float(r["imp"]) for r in cs]),
          "ho": ho, "nguon_thang": bc["nguon_thang"], "thang": bc["thang"],
          "nhan_video": {vid: (nhan.get(vid) or {}).get("kieu") or "" for vid in tep}}
    # vòng phản hồi
    sc = doc_so_cai(goc, kenh)
    kq_cu = doc_ket_qua(goc, kenh)
    kq_moi = dong_ket_qua_moi(rows, may, nhan, sc, kq_cu)
    tq = tuong_quan(list(kq_cu) + kq_moi)
    tv_thang = _trung_vi([r["ctr"] for r in rieng]) if len(rieng) >= SO_THANG_TOI_THIEU else _trung_vi(
        [b.get("ctr") for b in cu if isinstance(b.get("ctr"), (int, float))])
    tut = kiem_tut(rows, may, nhan, tv_thang)
    cu_tk = doc_thong_ke(goc, kenh)
    tk.update(tuong_quan=tq, tv_thang=tv_thang, tut=tut, canh_bao=cu_tk.get("canh_bao") or {},
              ep_doi_kieu=cu_tk.get("ep_doi_kieu") or None)
    try:    # 21/10/2026 (G4): bằng chứng A/B 3 bìa theo họ kiểu chữ → `hau_nghiem`
        from .bia_ab import thong_ke_ho_ab  # noqa: PLC0415
        tk["ab"] = thong_ke_ho_ab(goc, kenh)
    except Exception:  # noqa: BLE001
        tk["ab"] = {}
    bc["ab"] = tk["ab"]
    bc.update(ket_qua_moi=len(kq_moi), tuong_quan=tq, tut=tut, tv_thang=tv_thang,
              bia_may=[{"video_id": r["video_id"], "ngay": r["ngay"], "imp": r["imp"], "ctr": r["ctr"],
                        "tuoi": r.get("tuoi"), "kieu": (nhan.get(r["video_id"]) or {}).get("kieu") or "?"}
                       for r in sorted((r for r in rows if r["video_id"] in may), key=lambda r: r["ngay"],
                                       reverse=True)[:6]])
    moi_canh_bao = bool(tut) and (tk["canh_bao"] or {}).get("khoa") != tut["khoa"]
    bc["canh_bao_moi"] = moi_canh_bao
    if thu:
        bc["ghi_thu_muc"] = "thử — không ghi" + ("" if not ly_khong_ghi else " ({0})".format(ly_khong_ghi))
        return bc
    # ── ghi (chạy thật) ──
    if len(rieng) >= SO_THANG_TOI_THIEU and not ly_khong_ghi:
        bc["ghi_thu_muc"] = ghi_thu_muc(tm, kenh, [(r, tep[r["video_id"]], nhan.get(r["video_id"]) or {})
                                                  for r in rieng], tv=tv, log=log)
    else:
        bc["ghi_thu_muc"] = ly_khong_ghi or "giữ bộ đang có (chưa đủ {0} video đạt của chính kênh)".format(
            SO_THANG_TOI_THIEU)
        if tm_dang and os.path.normcase(os.path.abspath(tm_dang)) == os.path.normcase(tm) and gan_nhan_thu_muc(
                tm_dang, nh_tep):
            bc["ghi_thu_muc"] += "; gắn nhãn họ cho bộ đang có"
    if kq_moi:
        os.makedirs(os.path.dirname(duong_ket_qua(goc, kenh)), exist_ok=True)
        with io.open(duong_ket_qua(goc, kenh), "a", encoding="utf-8") as f:
            for x in kq_moi:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    if moi_canh_bao:
        tk["canh_bao"] = {"khoa": tut["khoa"], "luc": tk["luc"]}
        tk["ep_doi_kieu"] = {"tranh": tut["tranh"], "khoa": tut["khoa"], "luc": tk["luc"]} if tut["tranh"] else None
        chu = "3 bìa máy mới nhất kênh {0} CTR {1} < {2}% (0,6 × trung vị bìa thắng {3}%){4}".format(
            kenh, ", ".join("{0}%".format(v["ctr"]) for v in tut["video"]), tut["nguong"], tv_thang,
            " — lượt kế thử họ khác «{0}»".format(tut["tranh"]) if tut["tranh"] else "")
        try:
            from . import bao_dong  # noqa: PLC0415
            bao_dong.bao_dong("bia_ctr_thap", "Bìa máy làm tụt CTR — kênh {0}".format(kenh), chu, goc=goc, kenh=kenh)
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import nao_bo_phan  # noqa: PLC0415
            nao_bo_phan.ghi(goc, "bia", "ket_qua", kenh=kenh, nguon="bia_du_lieu", khoa="bia-ctr-thap:" + tut["khoa"],
                            so={"tut": tut, "tv_thang": tv_thang, "ho": {h: x.get("ctr") for h, x in ho.items()}},
                            noi_dung="bài học: " + chu)
        except Exception:  # noqa: BLE001
            pass
    _ghi_json(duong_thong_ke(goc, kenh), tk)
    return bc


def in_bao_cao(bc: Dict[str, Any], in_ra: Callable[[str], None] = print) -> None:
    in_ra("== {0}{1}: {2} video, {3} đủ chín (≥48h, ≥1k hiển thị), trung vị CTR {4}%".format(
        bc["kenh"], " (THỬ)" if bc.get("thu") else "", bc["so_video"], bc["so_du_chin"], bc.get("trung_vi_ctr")))
    in_ra("  thư mục bìa thắng đang dùng: {0}".format(bc.get("thu_muc_dang") or "(không có)"))
    for b in bc.get("cu") or []:
        in_ra("    cũ  {0:<12} imp {1:>7} CTR {2:>5}% họ {3}".format(str(b.get("video_id"))[:12], str(b.get("imp")),
                                                                  str(b.get("ctr")), b.get("kieu") or "-"))
    in_ra("  bộ bìa thắng MỚI theo dữ liệu ({0}):".format(bc.get("nguon_thang")))
    for b in bc.get("thang") or []:
        in_ra("    mới {0:<12} imp {1:>7} CTR {2:>5}% bấm {3:>6} họ {4}".format(
            b["video_id"][:12], int(b["imp"]), b["ctr"], b["luot_bam"], b["kieu"]))
    for h, x in sorted((bc.get("ho") or {}).items(), key=lambda kv: -(kv[1].get("ctr") or 0)):
        in_ra("  họ {0:<4}: {1} video ({2} của máy), {3} hiển thị, CTR có trọng số {4}%".format(
            h, x["n"], x["may"], x["imp"], x["ctr"]))
    for b in bc.get("bia_may") or []:
        in_ra("    bìa máy {0} {1:<12} imp {2:>6} CTR {3:>5}% tuổi {4}h họ {5}".format(
            b["ngay"], b["video_id"][:12], int(b["imp"]), b["ctr"], b.get("tuoi"), b["kieu"]))
    tq = bc.get("tuong_quan") or {}
    in_ra("  tương quan điểm giám khảo ↔ CTR 48h: bấm-như-thắng rho={0} (n={1}), tổng rho={2} (n={3})".format(
        (tq.get("bam_nhu_thang") or {}).get("rho"), (tq.get("bam_nhu_thang") or {}).get("n"),
        (tq.get("tong") or {}).get("rho"), (tq.get("tong") or {}).get("n")))
    if bc.get("tut"):
        in_ra("  (!) TỤT: {0} bìa máy mới nhất < {1}% (tránh họ «{2}»){3}".format(
            SO_BIA_TUT, bc["tut"]["nguong"], bc["tut"]["tranh"], " — báo động mới" if bc.get("canh_bao_moi") else ""))
    in_ra("  ghi: {0}".format(bc.get("ghi_thu_muc")))


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.bia_du_lieu", description="Bìa thắng theo dữ liệu (D21).")
    p.add_argument("lenh", choices=("chay", "tat-ca"))
    p.add_argument("--kenh", default="")
    p.add_argument("--thu", action="store_true", help="chỉ đọc: không ghi thư mục bìa thắng / sổ / thống kê")
    p.add_argument("--tam", default="", help="thư mục tạm của chạy thử (ảnh tải thêm + cache phân loại)")
    p.add_argument("--khong-ai", action="store_true", help="không gọi AI phân loại (ảnh chưa có nhãn bỏ trống)")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    if a.lenh == "chay" and not a.kenh:
        p.error("cần --kenh")
    goi = None
    if not a.khong_ai:
        from .bia_lo import _goi_that  # noqa: PLC0415
        goi = _goi_that(goc, print)
    if a.lenh == "chay":
        cac = [a.kenh]
    else:
        from .kenh import liet_ke_kenh  # noqa: PLC0415
        cac = [k for k in liet_ke_kenh(goc) if os.path.isfile(duong_bang(goc, k))]
    loi = 0
    for k in cac:
        try:
            in_bao_cao(chay_kenh(goc, k, thu=a.thu, goi=goi, tam=os.path.abspath(a.tam) if a.tam else ""))
        except Exception as e:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
            loi += 1
            print("== {0}: HỎNG {1}".format(k, str(e)[:300]))
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(main())
