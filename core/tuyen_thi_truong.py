"""**Ngách có bao nhiêu TUYẾN** — học từ content THẬT của đối thủ (22/10/2026, VPS thứ hai: ngách TRUYỆN KỂ).

Chủ dự án: *"từ content đối thủ phân tích ra ngách có bao nhiêu tuyến → từ đó tạo kênh phát triển, chiếm lĩnh ngách"*.
VPS đầu làm việc này bằng tay (script trong workspace, 01/10/2026: 146 kênh đối thủ, 7 tệp, luật "nguồn nổ/tháng ÷ 15").
Module này là bản TỔNG QUÁT, chạy được trên máy mới, theo nghĩa (LLM) chứ không theo từ khoá:

1. **Gom** video DÀI của đối thủ đang theo dõi trong `CHANNEL/<k>/nghien-cuu/content.csv` của mọi kênh trong nhóm
   (khử trùng theo link), trung vị view từng kênh nguồn → hệ số vượt `r = view ÷ trung vị kênh`.
2. **Đề xuất tuyến** (1 lượt LLM, nhớ đệm): đọc ~300 tiêu đề (nổ nhất + rải đều) + hồ sơ ngách → 4–10 TUYẾN theo
   NGHĨA (một tệp khán giả / một lời hứa khác nhau rõ), mỗi tuyến: mã, tên, mô tả, insight, từ khoá nhận biết.
3. **Gán** từng tiêu đề vào một tuyến (lô 60, nhớ đệm theo mã video — chạy lại chỉ hỏi tiêu đề mới).
4. **Đo** mỗi tuyến bằng mã: số video, số kênh nguồn, NGUỒN NỔ/THÁNG (video ≤ 60 ngày có r ≥ `HE_SO_NO`, ÷ 2), lượt
   xem/tháng (≤ 30 ngày), đà (30 ngày gần ÷ 30 ngày trước) → `toi_da` kênh = nguồn nổ/tháng ÷ `NHIP_THANG` (luật số
   kênh của tổng giám đốc, `core/giam_doc/tong.py`).
5. **Ghi**: `CHANNEL/_NHOM/<nhóm>/tuyen-thi-truong/` (nhớ đệm + `ket-qua.json`), `workspace/chuan-bi-kenh-moi/
   thi-truong.json` (đúng định dạng `mo_kenh.de_xuat` / `giam_doc.tong` đọc — máy tự mở thêm kênh về sau), và — khi
   `ghi_ho_so` — thay `tep_khan_gia` của `ngach.yaml` bằng các tuyến đo được (mã ổn định giữa các lần chạy).
6. **Chia kênh** (`phan_kenh`, thuần): N kênh → tuyến theo danh mục đầu tư: mỗi tuyến có thị trường nhận TỐI ĐA
   `toi_da` kênh, kênh thứ nhất của mọi tuyến trước kênh thứ hai của bất kỳ tuyến nào (phủ ngách, không ăn view nhau).

    python -m core.tuyen_thi_truong chay --nhom <nhóm> [--ghi-ho-so] [--lam-lai]   # LLM qua ví ShopAPI
    python -m core.tuyen_thi_truong xem --nhom <nhóm>                               # chỉ đọc kết quả

Không Qt, không Chrome. LLM đi ví ShopAPI (`core.khoi_tao_ngach.goi_tu_client`).
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import io
import json
import math
import os
import random
import re
import statistics
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MO_HINH = "claude-fable-5"
THU_MUC = "tuyen-thi-truong"
TEP_THI_TRUONG = os.path.join("workspace", "chuan-bi-kenh-moi", "thi-truong.json")
DAU_NGUON = "tuyen_thi_truong"          # chữ đầu khoá "nguon" — tệp thị trường do module này ghi (được ghi đè)
GIAY_DAI = 240                           # video ≥ 4 phút (hoặc thiếu số) mới là khổ remake
HE_SO_NO = 5.0                           # nổ = view ≥ 5 × trung vị kênh nguồn (bản tay 01/10)
NGAY_NO = 60                             # cửa sổ đếm nguồn nổ (÷ 2 → mỗi tháng)
SO_TIEU_DE_DE_XUAT = 300
LO_GAN = 60
TUYEN_TOI_THIEU, TUYEN_TOI_DA = 4, 10
KHAC = "khac"


# ── tiện ích ────────────────────────────────────────────────────────────────────────────────────

def _so(x: Any) -> float:
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _giay(chu: Any) -> int:
    phan = [p for p in str(chu or "").strip().split(":") if p.strip().isdigit()]
    s = 0
    for p in phan:
        s = s * 60 + int(p)
    return s


def _ngay(chu: Any) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(chu or "").strip()[:10])
    except ValueError:
        return None


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with io.open(duong, encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep))
    except OSError:
        return []


def _doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def slug(chu: str, toi_da: int = 40) -> str:
    from .khoi_tao_ngach import slug as _s  # noqa: PLC0415
    return _s(chu, toi_da)


def _ma_video(link: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([0-9A-Za-z_-]{11})", str(link or ""))
    return m.group(1) if m else ""


def thu_muc(goc: str, nhom: str) -> str:
    from .ho_so_ngach import duong_ngach_yaml  # noqa: PLC0415
    return os.path.join(os.path.dirname(duong_ngach_yaml(goc, nhom)), THU_MUC)


# ── 1) gom ───────────────────────────────────────────────────────────────────────────────────────

def kenh_cua_nhom(goc: str, nhom: str) -> List[str]:
    from .ho_so_ngach import nhom_cua_kenh  # noqa: PLC0415
    try:
        ds = sorted(os.listdir(os.path.join(goc, "CHANNEL")))
    except OSError:
        return []
    return [m for m in ds if not m.startswith("_") and nhom_cua_kenh(goc, m) == nhom]


def gom(goc: str, nhom: str, *, bay_gio: Optional[_dt.date] = None) -> List[Dict[str, Any]]:
    """Video dài của đối thủ ĐANG THEO DÕI (sổ trống trạng thái → nhận hết) từ content.csv mọi kênh trong nhóm.
    Mỗi video: {id, kenh, tieu_de, view, ngay, tuoi, tang, r}. `r` = view ÷ trung vị kênh nguồn (kênh < 3 video → 0)."""
    hom = bay_gio or _dt.date.today()
    theo_doi, bo = set(), set()
    for k in kenh_cua_nhom(goc, nhom):
        for r in _doc_csv(os.path.join(goc, "CHANNEL", k, "nghien-cuu", "doi-thu.csv")):
            ten = (r.get("Kênh") or "").strip()
            tt = (r.get("Trạng thái") or "").strip()
            if ten:
                (theo_doi if tt in ("theo dõi", "") else bo).add(ten)
    thay: Dict[str, Dict[str, Any]] = {}
    for k in kenh_cua_nhom(goc, nhom):
        for r in _doc_csv(os.path.join(goc, "CHANNEL", k, "nghien-cuu", "content.csv")):
            vid = _ma_video(r.get("Link video"))
            ten = (r.get("Kênh") or "").strip()
            td = (r.get("Tiêu đề video") or "").strip()
            if not vid or not td or vid in thay or (ten in bo and ten not in theo_doi):
                continue
            dai = _giay(r.get("Thời lượng"))
            if dai and dai < GIAY_DAI:
                continue
            ngay = _ngay(r.get("Ngày đăng"))
            thay[vid] = {"id": vid, "kenh": ten, "tieu_de": td[:200], "view": _so(r.get("View")),
                         "ngay": ngay.isoformat() if ngay else "", "tuoi": (hom - ngay).days if ngay else None,
                         "tang": _so(r.get("Tăng/ngày"))}
    theo_kenh: Dict[str, List[float]] = {}
    for v in thay.values():
        theo_kenh.setdefault(v["kenh"], []).append(v["view"])
    tv = {k: statistics.median(x) for k, x in theo_kenh.items() if len(x) >= 3 and statistics.median(x) > 0}
    for v in thay.values():
        v["r"] = round(v["view"] / tv[v["kenh"]], 2) if v["kenh"] in tv else 0.0
    return sorted(thay.values(), key=lambda v: (-v["r"], -v["view"], v["id"]))


def mau_de_xuat(video: Sequence[Dict[str, Any]], n: int = SO_TIEU_DE_DE_XUAT, seed: int = 7) -> List[Dict[str, Any]]:
    """Một nửa nổ nhất (r cao), một nửa rải đều phần còn lại — tuyến nhỏ mà đều vẫn lộ ra. Xác định (seed cố định)."""
    nua = n // 2
    dau = list(video[:nua])
    con = list(video[nua:])
    random.Random(seed).shuffle(con)
    return dau + con[:n - len(dau)]


# ── 2) đề xuất tuyến (LLM) ─────────────────────────────────────────────────────────────────────

DE_BAI_TUYEN = """Bạn là chiến lược gia của một NHÓM kênh YouTube làm theo lối REMAKE (xem video đối thủ đã thắng rồi viết
lại kịch bản). Nhóm sẽ mở NHIỀU kênh trong cùng ngách, mỗi kênh đánh MỘT TUYẾN để phủ ngách mà không ăn view nhau.

NGÁCH: {ngach}
TIẾNG / THỊ TRƯỜNG: {tieng} · {quoc_gia}
KHÁN GIẢ: {khan_gia}

Dưới đây là {n} tiêu đề video THẬT của đối thủ (số đầu dòng = hệ số vượt trung vị kênh; ≥ 5 là video nổ):
{ds}

Hãy chia ngách thành {a}–{b} TUYẾN theo NGHĨA (không theo từ khoá): mỗi tuyến là một nhóm người xem / một lời hứa / một
kiểu câu chuyện khác nhau RÕ, đủ lớn để một kênh sống bằng nó, và hai tuyến không giành cùng một video. Tiêu đề không
thuộc ngách thì bỏ qua (đừng lập tuyến cho chúng).

Trả về DUY NHẤT một JSON:
{{"tuyen": [{{"ma": "chu-thuong-khong-dau-co-gach", "ten": "tên tuyến tiếng Việt", "ten_ngan": "≤ 3 chữ",
  "mo_ta": "người xem là ai, video kể/hứa gì (tiếng Việt, ≤ 60 chữ)", "insight": "câu người xem thầm nghĩ khi bấm",
  "tu_khoa": "vài cụm {tieng} hay gặp trong tiêu đề tuyến này", "vi_du": ["2-3 tiêu đề mẫu chép từ danh sách"]}}]}}"""

DE_BAI_GAN = """Gán mỗi tiêu đề video YouTube dưới đây vào ĐÚNG MỘT tuyến theo NGHĨA (không theo từ khoá).
NGÁCH: {ngach}
CÁC TUYẾN:
{tuyen}
- "{khac}" = thuộc ngách nhưng không hợp tuyến nào · "lac" = không thuộc ngách.

TIÊU ĐỀ (số|tiêu đề):
{ds}

Trả về DUY NHẤT một JSON {{"1": "<mã tuyến | {khac} | lac>", ...}} đủ mọi số."""


def _an(chu: Any) -> str:
    return " ".join(str(chu or "").split()).replace("{", "(").replace("}", ")")


def _ngu_canh(goc: str, nhom: str) -> Dict[str, str]:
    from . import ho_so_ngach as hsn  # noqa: PLC0415
    hs = hsn.doc_ngach_nhom(goc, nhom)
    tho = hsn.doc_ngach_tho(goc, nhom) or {}
    ngach = " · ".join(x for x in (hs.mo_ta_ngach, str(tho.get("mo_ta_cho_loc_ai") or "")[:600]) if x) or nhom
    return {"ngach": _an(ngach), "tieng": _an(hsn.ten_tieng(hs.ngon_ngu()) or hs.ngon_ngu() or "?"),
            "quoc_gia": _an((hs.thi_truong or {}).get("quoc_gia") or "?"),
            "khan_gia": _an(hs.khan_gia_mo_ta or str(tho.get("khan_gia_mo_ta") or "") or "(chưa rõ)")}


def chuan_tuyen(du: Any) -> List[Dict[str, Any]]:
    """JSON tuyến của AI → danh sách sạch: mã slug ASCII duy nhất (không số trơn — số là mã tệp cũ của ngách mặc định)."""
    ra: List[Dict[str, Any]] = []
    for d in (du or {}).get("tuyen") or [] if isinstance(du, dict) else []:
        if not isinstance(d, dict) or not str(d.get("ten") or "").strip():
            continue
        ma = slug(str(d.get("ma") or d.get("ten") or ""), 40)
        if not ma or ma.isdigit() or ma in (KHAC, "lac"):
            ma = "tuyen-{0}".format(len(ra) + 1)
        while ma in {x["ma"] for x in ra}:
            ma += "-2"
        ra.append({"ma": ma, "ten": _an(d.get("ten"))[:120], "ten_ngan": _an(d.get("ten_ngan") or d.get("ten"))[:40],
                   "mo_ta": _an(d.get("mo_ta"))[:500], "insight": _an(d.get("insight"))[:300],
                   "tu_khoa": _an(d.get("tu_khoa"))[:300],
                   "vi_du": [_an(x)[:200] for x in (d.get("vi_du") or []) if str(x or "").strip()][:3]})
        if len(ra) >= TUYEN_TOI_DA:
            break
    return ra


def de_xuat_tuyen(goc: str, nhom: str, video: Sequence[Dict[str, Any]], ai: Any, *, lam_lai: bool = False,
                  log: Callable[[str], None] = print) -> List[Dict[str, Any]]:
    """Danh sách tuyến (đã lưu thì dùng lại — mã ổn định giữa các lần đo; `lam_lai` hỏi AI lại)."""
    duong = os.path.join(thu_muc(goc, nhom), "tuyen.json")
    cu = _doc_json(duong, {}) or {}
    if cu.get("tuyen") and not lam_lai:
        return list(cu["tuyen"])
    mau = mau_de_xuat(video)
    if len(mau) < 30:
        raise RuntimeError("mới có {0} video dài của đối thủ — cần ≥ 30 để chia tuyến (chạy Một nút / quét đối thủ "
                           "trước)".format(len(mau)))
    nc = _ngu_canh(goc, nhom)
    ds = "\n".join("{0:.1f}|{1}".format(v["r"], _an(v["tieu_de"])[:150]) for v in mau)
    de = DE_BAI_TUYEN.format(n=len(mau), ds=ds, a=TUYEN_TOI_THIEU, b=TUYEN_TOI_DA, **nc)
    tuyen: List[Dict[str, Any]] = []
    for lan in range(2):
        from .goi_van_ban import loc_json  # noqa: PLC0415
        tra = ai.hoi("tuyen-thi-truong" + ("" if lan == 0 else "-lan2"),
                     de + ("" if lan == 0 else "\n\n(Lần trước JSON hỏng — chỉ trả JSON hợp lệ.)"), toi_da_token=8000,
                     mo_hinh=MO_HINH)
        try:
            tuyen = chuan_tuyen(loc_json(tra))
        except Exception:  # noqa: BLE001
            tuyen = []
        if len(tuyen) >= 2:
            break
    if len(tuyen) < 2:
        raise RuntimeError("AI chưa chia được tuyến (trả < 2 tuyến hợp lệ)")
    _ghi_json(duong, {"nhom": nhom, "luc": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "tuyen": tuyen,
                      "so_tieu_de": len(mau)})
    log("đề xuất {0} tuyến: {1}".format(len(tuyen), " · ".join(t["ten_ngan"] for t in tuyen)))
    return tuyen


def gan(goc: str, nhom: str, video: Sequence[Dict[str, Any]], tuyen: Sequence[Dict[str, Any]], ai: Any, *,
        lo: int = LO_GAN, log: Callable[[str], None] = print) -> Dict[str, str]:
    """{mã video: mã tuyến | khac | lac}. Nhớ đệm `nhan.json` (khoá = mã video + chữ ký bộ tuyến)."""
    from .goi_van_ban import loc_json  # noqa: PLC0415
    ma_tuyen = {t["ma"] for t in tuyen}
    ky = slug("|".join(sorted(ma_tuyen)), 200)[:24]
    duong = os.path.join(thu_muc(goc, nhom), "nhan.json")
    nho = _doc_json(duong, {}) or {}
    if nho.get("_ky") != ky:
        nho = {"_ky": ky}
    nc = _ngu_canh(goc, nhom)
    khoi = "\n".join("- {0}: {1} — {2}".format(t["ma"], t["ten"], t["mo_ta"]) for t in tuyen)
    chua = [v for v in video if v["id"] not in nho]
    for i in range(0, len(chua), lo):
        phan = chua[i:i + lo]
        ds = "\n".join("{0}|{1}".format(j + 1, _an(v["tieu_de"])[:150]) for j, v in enumerate(phan))
        try:
            tra = ai.hoi("gan-tuyen", DE_BAI_GAN.format(ngach=nc["ngach"], tuyen=khoi, ds=ds, khac=KHAC),
                         toi_da_token=3000, mo_hinh="claude-sonnet-5")
            du = loc_json(tra)
        except Exception as loi:  # noqa: BLE001 — lô hỏng: lần sau hỏi lại
            log("  gán tuyến lô {0} hỏng: {1}".format(i // lo + 1, str(loi)[:120]))
            continue
        for j, v in enumerate(phan, 1):
            m = str((du or {}).get(str(j)) or "").strip() if isinstance(du, dict) else ""
            if m in ma_tuyen or m in (KHAC, "lac"):
                nho[v["id"]] = m
        _ghi_json(duong, nho)
    return {k: v for k, v in nho.items() if not k.startswith("_")}


# ── 3) đo (thuần) ─────────────────────────────────────────────────────────────────────────────

def do(video: Sequence[Dict[str, Any]], nhan: Dict[str, str], tuyen: Sequence[Dict[str, Any]],
       nhip_thang: float = 15.0) -> List[Dict[str, Any]]:
    """Số đo từng tuyến (thuần): so_video, so_kenh (kênh ≥ 2 video của tuyến), nguon_no_thang, view_thang, tang_view,
    trang_chu ("len"/"on"/"giam" theo đà view), toi_da (= nguồn nổ/tháng ÷ `nhip_thang`, tối thiểu 1 khi tuyến có ≥ 1
    nguồn nổ/tháng). Xếp theo nguồn nổ giảm dần."""
    ra = []
    for t in tuyen:
        vs = [v for v in video if nhan.get(v["id"]) == t["ma"]]
        dem_kenh: Dict[str, int] = {}
        for v in vs:
            dem_kenh[v["kenh"]] = dem_kenh.get(v["kenh"], 0) + 1
        no = sum(1 for v in vs if v.get("tuoi") is not None and v["tuoi"] <= NGAY_NO and v["r"] >= HE_SO_NO)
        nguon = round(no * 30.0 / NGAY_NO, 1)
        gan30 = sum(v["view"] for v in vs if v.get("tuoi") is not None and v["tuoi"] <= 30)
        truoc = sum(v["view"] for v in vs if v.get("tuoi") is not None and 30 < v["tuoi"] <= 60)
        tang_ngay = sum(v["tang"] for v in vs if v.get("tuoi") is not None and v["tuoi"] > 30)
        view_thang = round(gan30 + tang_ngay * 30)
        tang = round(gan30 / truoc, 2) if truoc > 0 else (None if not gan30 else 2.0)
        xu = "on" if tang is None else ("len" if tang >= 1.1 else ("giam" if tang <= 0.9 else "on"))
        toi_da = int(nguon // nhip_thang) if nguon >= nhip_thang else (1 if nguon >= 1 else 0)
        ra.append(dict(t, so_video=len(vs), so_kenh=sum(1 for n in dem_kenh.values() if n >= 2),
                       nguon_no_thang=nguon, view_thang=view_thang, tang_view=tang, trang_chu=xu, toi_da=toi_da))
    ra.sort(key=lambda d: (-d["nguon_no_thang"], -d["view_thang"], d["ma"]))
    return ra


# ── 4) chia kênh (thuần) ──────────────────────────────────────────────────────────────────────

def phan_kenh(kenh: Sequence[str], so_do: Sequence[Dict[str, Any]], da_co: Optional[Dict[str, str]] = None
              ) -> Dict[str, str]:
    """{kênh: mã tuyến}. Danh mục đầu tư: vòng 1 mỗi tuyến (thị trường có `toi_da` ≥ 1, lớn trước) một kênh; vòng 2+ thêm
    kênh cho tuyến còn sức chứa (`toi_da` > số kênh đã có), lớn trước. Kênh đã có tuyến (`da_co`) giữ nguyên. Thừa kênh
    mà mọi tuyến đã đủ → xoay vòng các tuyến từ lớn nhất (mỗi kênh vẫn khác GÓC — `mo_kenh.chon_goc` lo)."""
    da_co = dict(da_co or {})
    ra = {k: da_co[k] for k in kenh if k in da_co}
    ung = [d for d in so_do if int(d.get("toi_da") or 0) >= 1] or list(so_do[:1])
    if not ung:
        return ra
    dem = {d["ma"]: 0 for d in ung}
    for t in ra.values():
        if t in dem:
            dem[t] += 1
    con = [k for k in kenh if k not in ra]
    tran = max(1, max(int(d.get("toi_da") or 0) for d in ung))
    for vong in range(1, tran + 1):                                  # vòng v: tuyến có sức chứa ≥ v nhận kênh thứ v
        for d in ung:
            if con and dem[d["ma"]] < vong and (vong == 1 or int(d.get("toi_da") or 0) >= vong):
                ra[con.pop(0)] = d["ma"]
                dem[d["ma"]] += 1
    i = 0
    while con:                                                       # thừa kênh: xoay vòng các tuyến lớn nhất
        ra[con.pop(0)] = ung[i % len(ung)]["ma"]
        i += 1
    return ra


# ── 5) ghi ───────────────────────────────────────────────────────────────────────────────────

def ghi_thi_truong(goc: str, nhom: str, so_do: Sequence[Dict[str, Any]], so_video: int, *, ep: bool = False) -> str:
    """`workspace/chuan-bi-kenh-moi/thi-truong.json` (định dạng `mo_kenh.de_xuat`). Tệp đã có mà KHÔNG do module này ghi
    (máy đầu: số tay 01/10) → không đè (trừ `ep`), trả ""."""
    duong = os.path.join(goc, TEP_THI_TRUONG)
    cu = _doc_json(duong, {}) or {}
    if cu.get("tep") and not str(cu.get("nguon") or "").startswith(DAU_NGUON) and not ep:
        return ""
    _ghi_json(duong, {
        "ngay": _dt.date.today().isoformat(),
        "nguon": "{0}: nhóm {1}, {2} video dài của đối thủ (nổ = view ≥ {3:g}× trung vị kênh, đăng ≤ {4} ngày ÷ 2)".format(
            DAU_NGUON, nhom, so_video, HE_SO_NO, NGAY_NO),
        "tep": {d["ma"]: {"ten": d["ten"], "nguon_no_thang": d["nguon_no_thang"], "trang_chu": d["trang_chu"],
                          "he_so_trang_chu": d.get("tang_view"), "view_thang": d["view_thang"], "tang_view": d.get("tang_view"),
                          "so_video": d["so_video"], "so_kenh_nguon": d["so_kenh"]} for d in so_do}})
    return duong


def ghi_ho_so(goc: str, nhom: str, so_do: Sequence[Dict[str, Any]]) -> str:
    """Thay `tep_khan_gia` của `ngach.yaml` bằng các tuyến (giữ mọi khoá khác, giữ phần chú thích đầu tệp)."""
    import yaml  # noqa: PLC0415
    from .ho_so_ngach import duong_ngach_yaml  # noqa: PLC0415
    duong = duong_ngach_yaml(goc, nhom)
    with io.open(duong, encoding="utf-8") as tep:
        tho = tep.read()
    du = yaml.safe_load(tho) or {}
    du["tep_khan_gia"] = [{"ma": d["ma"], "ten": d["ten"], "ten_ngan": d.get("ten_ngan") or d["ten"][:30]} for d in so_do]
    dau = "".join(d for d in tho.splitlines(True) if d.startswith("#"))[:4000]
    dau = dau.split("\n\n")[0] if dau else ""
    moi = (dau + "\n" if dau else "") + "# tep_khan_gia = các TUYẾN đo từ content đối thủ (core/tuyen_thi_truong.py, {0}).\n\n".format(
        _dt.date.today().isoformat()) + yaml.safe_dump(du, allow_unicode=True, sort_keys=False, width=110)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        tep.write(moi)
    os.replace(duong + ".tam", duong)
    return duong


def ghi_tuyen_csv(goc: str, kenh: str, so_do: Sequence[Dict[str, Any]], ma_tuyen: str) -> int:
    """`CHANNEL/<kênh>/nghien-cuu/tuyen.csv` từ các tuyến đo được: tuyến của kênh "đang đánh" (Kênh của tôi = kênh),
    tuyến khác "đang xem". Có cột Mô tả / Insight / Từ khoá nhận biết cho các khâu đọc nghĩa (nuôi trang chủ…)."""
    from . import tuyen_noi_dung as tn  # noqa: PLC0415
    cot = list(tn.COT)
    o = tn.chi_so_cot(cot)
    hang = []
    for d in so_do:
        dong = [""] * len(cot)
        for ten, gt in (("Mã", d["ma"]), ("Tên tuyến", d["ten"]),
                        ("Trạng thái", tn.DANG_DANH if d["ma"] == ma_tuyen else tn.DANG_XEM),
                        ("Kênh của tôi", kenh if d["ma"] == ma_tuyen else ""), ("Insight", d.get("insight") or ""),
                        ("Từ khoá nhận biết", d.get("tu_khoa") or ""), ("Mô tả", d.get("mo_ta") or "")):
            if ten in o:
                dong[o[ten]] = gt
        hang.append(dong)
    tn.luu(goc, kenh, cot, hang)
    return len(hang)


# ── chạy ─────────────────────────────────────────────────────────────────────────────────────

def chay(goc: str, nhom: str, *, ai: Any = None, client: Any = None, ghi_ho_so_ngach: bool = False,
         lam_lai: bool = False, ep_thi_truong: bool = False, log: Callable[[str], None] = print) -> Dict[str, Any]:
    """Gom → đề xuất tuyến (nhớ đệm) → gán (nhớ đệm) → đo → ghi. `ai` = `khoi_tao_ngach.BoGoiAI` (bài kiểm truyền đồ
    giả); None + `client` → ví thật. Trả {tuyen: [số đo], so_video, thi_truong, ho_so}."""
    if ai is None:
        from .khoi_tao_ngach import BoGoiAI, goi_tu_client  # noqa: PLC0415
        if client is None:
            from .api import build_client  # noqa: PLC0415
            from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415
            cfg = load_config(os.path.join(goc, CONFIG_FILENAME))
            if cfg.problem:
                raise RuntimeError("không đọc được cấu hình ShopAPI: {0}".format(str(cfg.problem)[:120]))
            client = build_client(cfg)
        ai = BoGoiAI(goi_tu_client(client, log), os.path.join(thu_muc(goc, nhom), "ai"), log)
    video = gom(goc, nhom)
    log("gom: {0} video dài của đối thủ (nhóm {1}, {2} kênh)".format(len(video), nhom, len(kenh_cua_nhom(goc, nhom))))
    tuyen = de_xuat_tuyen(goc, nhom, video, ai, lam_lai=lam_lai, log=log)
    nhan = gan(goc, nhom, video, tuyen, ai, log=log)
    try:
        from .giam_doc.tong import NHIP_THANG  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        NHIP_THANG = 15.0  # noqa: N806
    so_do = do(video, nhan, tuyen, float(NHIP_THANG))
    kq = {"nhom": nhom, "luc": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "so_video": len(video),
          "da_gan": sum(1 for v in video if v["id"] in nhan), "tuyen": so_do}
    _ghi_json(os.path.join(thu_muc(goc, nhom), "ket-qua.json"), kq)
    kq["thi_truong"] = ghi_thi_truong(goc, nhom, so_do, len(video), ep=ep_thi_truong)
    if ghi_ho_so_ngach:
        kq["ho_so"] = ghi_ho_so(goc, nhom, so_do)
    for d in so_do:
        log("  {0:<28} nổ/tháng {1:>5} · view/tháng {2:>10,} · {3:>4} video · {4:>3} kênh · đà {5} → tối đa {6} kênh".format(
            d["ten_ngan"][:28], d["nguon_no_thang"], int(d["view_thang"]), d["so_video"], d["so_kenh"],
            d["trang_chu"], d["toi_da"]))
    return kq


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.tuyen_thi_truong", description=__doc__.split("\n")[0])
    s = ap.add_subparsers(dest="lenh", required=True)
    c = s.add_parser("chay")
    c.add_argument("--nhom", required=True)
    c.add_argument("--ghi-ho-so", action="store_true", help="thay tep_khan_gia của ngach.yaml bằng các tuyến đo được")
    c.add_argument("--lam-lai", action="store_true", help="AI chia tuyến lại (mã tuyến có thể đổi)")
    c.add_argument("--ep-thi-truong", action="store_true", help="ghi đè thi-truong.json dù không do module này ghi")
    x = s.add_parser("xem")
    x.add_argument("--nhom", required=True)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    if a.lenh == "xem":
        print(json.dumps(_doc_json(os.path.join(thu_muc(GOC, a.nhom), "ket-qua.json"), {}), ensure_ascii=False, indent=1))
        return 0
    try:
        chay(GOC, a.nhom, ghi_ho_so_ngach=a.ghi_ho_so, lam_lai=a.lam_lai, ep_thi_truong=a.ep_thi_truong)
    except Exception as loi:  # noqa: BLE001
        print("LỖI: {0}".format(loi))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
