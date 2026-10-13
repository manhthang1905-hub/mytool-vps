"""**RADAR ĐỘT BIẾN THỊ TRƯỜNG** — video ĐỐI THỦ đang nổ ở tuổi thật, so với chính kênh của nó, và đẩy NGAY cho
kênh ta hợp nhất (12/10/2026).

Chủ dự án, 12/10/2026: *"dữ liệu đối thủ khi gộp all các kênh vào sẽ có 1 danh sách toàn diện — việc theo dõi đối
thủ sẽ ok — để phát hiện ra content đột biến … giúp tao đạt mục tiêu để các kênh nổ view, kiếm tiền".*

`nao_chuong_trinh.radar_kenh` soi video CỦA TA. Tệp này soi THỊ TRƯỜNG: mọi video đối thủ của cả nhóm (hợp các sổ
content `CHANNEL/<k>/nghien-cuu/content.csv`, khoá mã video), nối với sổ đối thủ chung (`core/so_doi_thu_chung.py`).

═══ ĐO ═══ (mỗi video dài ≥ 4 phút, tuổi 6 giờ – 7 ngày, kênh đúng ngách)

    tuổi thật   = lúc quan sát (Quét lúc của kênh ở sổ đối thủ) − ngày đăng (12:00 UTC, như `cong_thuc_vph`)
    kỳ vọng     = nền kênh × đường cong(tuổi)
                  nền kênh = trung vị view các video dài ≥ 14 ngày tuổi (30 video gần nhất, n ≥ 5)
                  đường cong = view-tại-tuổi ÷ nền, trung vị theo ô tuổi (6–18h, 18–30h, … 2 tuần): của CHÍNH kênh khi
                  có ≥ 5 video quan sát ở ô ấy, không thì của cả ngách (mọi kênh đối thủ) — số quan sát lấy từ ảnh chụp
                  kho phòng thí nghiệm (`kho-<ngày>.csv.gz`, mỗi ngày một lần) + sổ quan sát riêng của radar
                  (`quan-sat.json`, mỗi lượt nghiên cứu một lần)
    gấp         = view ÷ kỳ vọng            mức: ≥ 3× đột biến · ≥ 8× nổ · ≥ 20× siêu nổ
    tốc độ      = view/giờ cả đời; tốc độ gần = Δview/Δgiờ giữa hai lần quan sát ≥ 3 giờ; tăng tốc = gần ÷ cả đời
    hiện diện   = trang chủ máy ảo kênh ta (7 ngày) + pool "video đề xuất" Studio của video ta (ảnh chụp kho)

═══ GÁN KÊNH ═══ (chỉ kênh ta còn được phát — `kenh_khong_phat`; bỏ bản thử A/B `-vN`)

    1. chủ vùng đề tài (`chu_quyen_vung`, vùng = AI chia vùng `vung-ai.json` → nhãn của kho → AI radar)
    2. AI radar đọc NGHĨA: tệp khán giả kênh nào sẽ coi đề tài này là của mình (đệm `ai-nhan.json`)
    3. kênh mà nhãn tuyến của nó trên video này đúng tuyến đang đánh
    4. kênh có khán giả đã gặp video (trang chủ / pool)
Video đã được kênh nào trong nhóm làm / giữ nguồn → "đã làm bởi …" (không gán).

═══ HÀNH ĐỘNG ═══

* Mọi lượt: bảng xếp hạng `CHANNEL/_NHOM/<nhóm>/radar/radar-moi-nhat.json` (+ `radar-<ngày>.json`), giả thuyết
  phòng thí nghiệm H-RADAR đọc đặc trưng `radar_*` (`phong_thi_nghiem.dac_trung`). Kênh nguồn tầng 1–2 của sổ chung
  (`so_doi_thu_chung.phan_tang`) được cộng điểm xếp hạng (`DIEM_TANG`) → AI đọc nghĩa / ép chọn xét trước; video nổ
  (mức ≥ 2) không bao giờ bị cắt khỏi bảng, và kéo kênh tầng 3 lên tầng 2 ở lần gộp sổ chung ngay sau lượt radar.
* CỰC MẠNH (mặc định ≥ 10× trong ≤ 72 giờ, ≥ 3.000 view, dài 8–40 phút, video đúng ngách, kênh hợp tệp, chưa kênh
  anh em nào làm/giữ/được đề cử): ÉP CHỌN cho kênh được gán qua đường ép chọn của bộ não
  (`nao.tao_ep_chon_radar` → `uu-tien-nguon` có `radar_thi_truong`, phải vào sản xuất ≤ 48 giờ). Trần: 1 / kênh /
  ngày. Ghi công phòng thí nghiệm cho H-RADAR (`chia_khe.chot_nguon`). Mọi quyết định (ép / bỏ vì …) ghi kèm số vào
  `radar/quyet-dinh.jsonl`.
* `nap_vao_so`: lượt nghiên cứu của kênh được gán chép dòng video ấy (cột trung tính, tuyến để trống) vào
  `content.csv` của kênh nếu thiếu — V7 và phòng thí nghiệm của kênh thấy nó.

Cấu hình: `CAU_HINH_MAC_DINH`, sửa được ở `workspace/radar-dot-bien.json` (cùng khoá). `MYTOOL_RADAR_EP=0` tắt ép chọn.

    python -m core.radar_dot_bien [--goc <cây>] [--nhom <nhóm>] [--ghi] [--ai] [--ep]     # mặc định CHẠY THỬ, không ghi

Không mạng (AI chỉ khi `dung_ai` và ví cho phép), không Qt. Mọi lỗi bọc lại — radar không bao giờ chặn nghiên cứu.
"""

from __future__ import annotations

import bisect
import csv
import datetime as _dt
import glob
import gzip
import io
import json
import math
import os
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

__all__ = ["CAU_HINH_MAC_DINH", "cau_hinh", "chay", "chay_an_toan", "chay_neu_cu", "nap_vao_so", "doc_moi_nhat",
           "dac_trung_cho_kenh", "truc_quan", "truc_quan_nho", "dong_cho_nao", "la_dot_bien", "muc_cua",
           "ky_vong_tai", "DuongCong"]

THU_MUC = "radar"
TEP_MOI = "radar-moi-nhat.json"
TEP_QUAN_SAT = "quan-sat.json"
TEP_AI = "ai-nhan.json"
TEP_QUYET = "quyet-dinh.jsonl"
TEP_CAU_HINH = os.path.join("workspace", "radar-dot-bien.json")
GIU_NGAY_BAN = 60
GIA_THUYET = "H-RADAR"

CAU_HINH_MAC_DINH: Dict[str, Any] = {
    "muc": [3.0, 8.0, 20.0],             # gấp × kỳ vọng: đột biến / nổ / siêu nổ
    "tuoi_toi_thieu_gio": 6.0,
    "tuoi_toi_da_gio": 168.0,
    "cua_so_gio": [24.0, 72.0],          # cửa sổ "đột biến sớm" (hiển thị riêng)
    "view_toi_thieu": 1000,
    "giay_toi_thieu": 240,
    "nen_tuoi_ngay": 14.0,               # video ≥ ngần này ngày tuổi làm nền kênh
    "nen_so_video": 30,
    "nen_n_toi_thieu": 5,
    "duong_rieng_n": 5,                  # ≥ ngần này video quan sát ở một ô tuổi → đường cong riêng của kênh
    "so_dong": 200,
    "ep_bat": True,
    "ep_boi": 10.0,
    "ep_tuoi_gio": 72.0,
    "ep_view_toi_thieu": 3000,
    "ep_phut": [8.0, 40.0],
    "ep_moi_kenh_ngay": 1,
    "ep_moi_luot": 10,
    "ai_bat": True,
    "ai_toi_da": 40,
    "ai_mo_hinh": "claude-fable-5",
    "ai_han_ngay": 14,
    "nap_so_toi_da": 20,
    "gio_chay_lai": 2.0,
}

#: Ô tuổi (giờ) — cạnh trái của mỗi ô; tâm ô dùng để nội suy theo log(tuổi).
CANH_O = (6.0, 18.0, 30.0, 42.0, 54.0, 66.0, 84.0, 108.0, 132.0, 156.0, 204.0, 288.0, 400.0)
TAM_O = (12.0, 24.0, 36.0, 48.0, 60.0, 75.0, 96.0, 120.0, 144.0, 180.0, 246.0, 344.0)
#: Đường cong ngách DỰ PHÒNG (view-tại-tuổi ÷ nền) khi chưa đủ quan sát — chỉ dùng tới khi số thật có (n ≥ 15/ô).
DUONG_DU_PHONG = (0.22, 0.36, 0.45, 0.52, 0.58, 0.63, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
N_O_NGACH = 15
TEN_MUC = {0: "", 1: "đột biến", 2: "nổ", 3: "siêu nổ"}
#: Trần của "gấp" khi XẾP HẠNG (không đổi mức): kênh nền 15 view ra video 4.000 view là ×270 — tín hiệu thật nhưng
#: không mạnh hơn video ×170 ở 62.000 view; phần còn lại do log10(view) phân xử.
TRAN_BOI_DIEM = 200.0
#: Cộng điểm xếp hạng theo TẦNG của kênh nguồn ở sổ đối thủ chung (13/10/2026, `so_doi_thu_chung.phan_tang`): lõi /
#: đang lên lên trước khi ngang ngửa — nhưng chỉ là một phần nhỏ của điểm (log gấp ~1–5): video nổ thật của kênh tầng 3
#: vẫn vượt video nhàng nhàng của tầng 1, và dòng mức ≥ 2 không bao giờ bị cắt khỏi bảng (`so_dong`). Kênh tầng 3 có
#: video nổ → lần gộp sổ chung sau lên tầng 2 (tín hiệu `dot_bien`).
DIEM_TANG = {"1": 0.3, "2": 0.15}


# ── tiện ích ────────────────────────────────────────────────────────────────

def _so(x: Any) -> Optional[float]:
    try:
        from .phong_thi_nghiem._chung import so  # noqa: PLC0415

        return so(x)
    except Exception:  # noqa: BLE001
        try:
            return float(str(x).replace(",", ""))
        except (TypeError, ValueError):
            return None


def _phut(x: Any) -> Optional[float]:
    phan = [p.strip() for p in str(x or "").strip().split(":")]
    if not phan or not all(p.isdigit() for p in phan):
        return None
    g = 0
    for p in phan:
        g = g * 60 + int(p)
    return g / 60.0


def _ep_ngay_dang(chu: Any) -> Optional[float]:
    try:
        d = _dt.date.fromisoformat(str(chu or "").strip()[:10])
    except ValueError:
        return None
    return _dt.datetime(d.year, d.month, d.day, 12, 0, tzinfo=_dt.timezone.utc).timestamp()


def _ep_luc(chu: Any) -> Optional[float]:
    s = str(chu or "").strip().replace("T", " ")
    for dang, dai in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
        try:
            return time.mktime(_dt.datetime.strptime(s[:dai], dang).timetuple())
        except ValueError:
            continue
    return None


def _trung_vi(xs: Sequence[float]) -> Optional[float]:
    ds = sorted(x for x in xs if x is not None)
    if not ds:
        return None
    n = len(ds)
    return ds[n // 2] if n % 2 else (ds[n // 2 - 1] + ds[n // 2]) / 2.0


def _doc_json(p: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(p: str, du: Any) -> None:
    from .so_doi_thu_chung import ghi_json_gon  # noqa: PLC0415

    ghi_json_gon(p, du)


def _ma_video(link: str) -> str:
    try:
        from .doi_thu_kenh import ma_video  # noqa: PLC0415

        return ma_video(link)
    except Exception:  # noqa: BLE001
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", str(link or ""))
        return m.group(1) if m else ""


def _f(x: Any, le: int = 0) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "?"
    if not math.isfinite(v):
        return "?"
    return ("{0:,.%df}" % le).format(v).replace(",", "X").replace(".", ",").replace("X", ".")


def cau_hinh(goc: str) -> Dict[str, Any]:
    ra = dict(CAU_HINH_MAC_DINH)
    du = _doc_json(os.path.join(goc, TEP_CAU_HINH), {}) or {}
    if isinstance(du, dict):
        for k, v in du.items():
            if k in ra and v is not None:
                ra[k] = v
    if str(os.environ.get("MYTOOL_RADAR_EP", "")).strip().lower() in ("0", "false", "tat", "tắt", "off", "no"):
        ra["ep_bat"] = False
    return ra


def muc_cua(boi: Optional[float], nguong: Sequence[float] = (3.0, 8.0, 20.0)) -> int:
    """Mức đột biến: 0 · 1 (≥ ngưỡng 1) · 2 · 3.

    >>> [muc_cua(x) for x in (None, 2.9, 3, 8.5, 25)]
    [0, 0, 1, 2, 3]
    """
    if boi is None:
        return 0
    n = 0
    for i, ng in enumerate(nguong):
        if boi >= float(ng):
            n = i + 1
    return n


def thu_muc(goc: str, nhom: str) -> str:
    from . import nhom_kenh  # noqa: PLC0415

    return os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), THU_MUC)


def _o_tuoi(gio: float) -> int:
    """Chỉ số ô tuổi (−1 = ngoài các ô)."""
    if gio < CANH_O[0] or gio >= CANH_O[-1]:
        return -1
    return bisect.bisect_right(CANH_O, gio) - 1


# ── đường cong kỳ vọng ──────────────────────────────────────────────────────

class DuongCong:
    """Đường cong view-tại-tuổi ÷ nền kênh: của ngách (`ngach[i]`) + của từng kênh (`rieng[kênh][i]`, có n)."""

    def __init__(self, ngach: Sequence[float], rieng: Dict[str, Dict[int, Tuple[float, int]]],
                 n_ngach: Sequence[int], n_rieng_toi_thieu: int = 5) -> None:
        self.ngach = list(ngach)
        self.n_ngach = list(n_ngach)
        self.rieng = rieng
        self.n_min = int(n_rieng_toi_thieu)

    def he_so(self, kenh: str, gio: float) -> Tuple[float, str]:
        """`(view-tại-tuổi ÷ nền, nguồn "kênh n=…" | "ngách")` — nội suy log(tuổi) giữa hai tâm ô."""
        r = self.rieng.get(kenh) or {}

        def tai(i: int) -> Tuple[float, bool]:
            x = r.get(i)
            if x is not None and x[1] >= self.n_min:
                return x[0], True
            return self.ngach[i], False
        g = max(TAM_O[0], min(TAM_O[-1], gio))
        j = bisect.bisect_right(TAM_O, g) - 1
        j = max(0, min(len(TAM_O) - 2, j))
        a, ra_ = tai(j)
        b, rb = tai(j + 1)
        t = (math.log(g) - math.log(TAM_O[j])) / (math.log(TAM_O[j + 1]) - math.log(TAM_O[j]))
        t = max(0.0, min(1.0, t))
        hs = math.exp(math.log(max(a, 1e-3)) * (1 - t) + math.log(max(b, 1e-3)) * t)
        if ra_ or rb:
            n = max((r.get(j) or (0, 0))[1], (r.get(j + 1) or (0, 0))[1])
            return hs, "kênh n={0}".format(n)
        return hs, "ngách"


def ky_vong_tai(duong: DuongCong, kenh: str, nen: float, gio: float) -> Tuple[float, str]:
    hs, nguon = duong.he_so(kenh, gio)
    return nen * hs, nguon


def _don_dieu(xs: List[float]) -> List[float]:
    """Đường cong không giảm theo tuổi (view tích luỹ không giảm) — chạy max."""
    ra: List[float] = []
    m = 0.0
    for x in xs:
        m = max(m, x)
        ra.append(m)
    return ra


def dung_duong_cong(quan_sat: Dict[str, Dict[str, Any]], nen: Dict[str, float], *,
                    n_rieng: int = 5) -> DuongCong:
    """Từ mọi quan sát `{mã: {"k": kênh, "d": ngày đăng, "o": [[giờ epoch, view], …]}}` và nền kênh → đường cong.
    Mỗi video mỗi ô một điểm (quan sát gần tâm ô nhất)."""
    theo_o: Dict[int, List[float]] = {}
    theo_kenh: Dict[str, Dict[int, List[float]]] = {}
    for ma, v in quan_sat.items():
        k = str(v.get("k") or "")
        b = nen.get(k)
        t0 = _ep_ngay_dang(v.get("d"))
        if not b or b <= 0 or t0 is None:
            continue
        tot: Dict[int, Tuple[float, float]] = {}
        for t, view in v.get("o") or []:
            try:
                gio = (float(t) - t0) / 3600.0
                view = float(view)
            except (TypeError, ValueError):
                continue
            i = _o_tuoi(gio)
            if i < 0 or view < 0:
                continue
            cach = abs(math.log(max(gio, 1.0) / TAM_O[i]))
            if i not in tot or cach < tot[i][0]:
                tot[i] = (cach, view / b)
        for i, (_c, r) in tot.items():
            theo_o.setdefault(i, []).append(r)
            theo_kenh.setdefault(k, {}).setdefault(i, []).append(r)
    ngach, n_ngach = [], []
    for i in range(len(TAM_O)):
        ds = theo_o.get(i) or []
        n_ngach.append(len(ds))
        ngach.append(_trung_vi(ds) if len(ds) >= N_O_NGACH else DUONG_DU_PHONG[i])
    ngach = _don_dieu([max(0.02, min(1.5, x)) for x in ngach])
    rieng: Dict[str, Dict[int, Tuple[float, int]]] = {}
    for k, o in theo_kenh.items():
        rieng[k] = {i: (max(0.02, min(3.0, _trung_vi(ds) or 0.02)), len(ds)) for i, ds in o.items()}
    return DuongCong(ngach, rieng, n_ngach, n_rieng)


# ── đọc dữ liệu nhóm ────────────────────────────────────────────────────────

def _csv_dong(p: str) -> List[Dict[str, str]]:
    try:
        csv.field_size_limit(10_000_000)
        with io.open(p, encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except (OSError, ValueError, csv.Error):
        return []


def _nc(goc: str, kenh: str) -> str:
    return os.path.join(goc, "CHANNEL", kenh, "nghien-cuu")


def _quet_luc_kenh(goc: str, kenh: str) -> Tuple[Dict[str, float], Optional[float]]:
    """`({tên kênh đối thủ: epoch Quét lúc}, quét sổ content gần nhất)` của sổ riêng `kenh`."""
    ra: Dict[str, float] = {}
    for r in _csv_dong(os.path.join(_nc(goc, kenh), "doi-thu.csv")):
        t = _ep_luc(r.get("Quét lúc"))
        ten = str(r.get("Kênh") or "").strip()
        if ten and t is not None and t > ra.get(ten, 0.0):
            ra[ten] = t
    cai = _doc_json(os.path.join(_nc(goc, kenh), "cai-dat.json"), {}) or {}
    try:
        q = float(cai.get("quet_luc") or 0) or None
    except (TypeError, ValueError):
        q = None
    return ra, q


def hop_content(goc: str, thanh_vien: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """Hợp sổ content mọi kênh ta → `{mã: {...}}` (một dòng mỗi video; quan sát có view lớn nhất = mới nhất)."""
    ra: Dict[str, Dict[str, Any]] = {}
    for m in thanh_vien:
        p = os.path.join(_nc(goc, m), "content.csv")
        rows = _csv_dong(p)
        if not rows:
            continue
        ql, q_so = _quet_luc_kenh(goc, m)
        try:
            mt = os.path.getmtime(p)
        except OSError:
            mt = time.time()
        for r in rows:
            ma = _ma_video(str(r.get("Link video") or ""))
            if not ma:
                continue
            ten = str(r.get("Kênh") or "").strip()
            view = _so(r.get("View"))
            luc = ql.get(ten) or q_so or mt
            o = ra.get(ma)
            if o is None:
                o = ra[ma] = {"ma": ma, "kenh_nguon": ten, "tieu_de": str(r.get("Tiêu đề video") or ""),
                              "tieu_de_viet": str(r.get("Tiêu đề (Việt)") or ""),
                              "link": str(r.get("Link video") or ""), "ngay_dang": str(r.get("Ngày đăng") or "")[:10],
                              "dai_phut": _phut(r.get("Thời lượng")), "view": view, "luc": luc,
                              "tang_ngay": _so(r.get("Tăng/ngày")), "lan_dau": str(r.get("Lần đầu thấy") or "")[:10],
                              "mo_ta": str(r.get("Mô tả") or "")[:300], "co_o": {}, "nguon_kenh": m}
            elif view is not None and (o["view"] is None or view > o["view"] or (view == o["view"] and luc > o["luc"])):
                o.update(view=view, luc=luc, tang_ngay=_so(r.get("Tăng/ngày")), nguon_kenh=m)
                if ten:
                    o["kenh_nguon"] = ten
            # Ngày đăng của yt-dlp là XẤP XỈ ("3 ngày trước" lúc quét) — hai lần quét có thể lệch một ngày. Lấy ngày SỚM
            # nhất từng thấy: tuổi dài hơn → kỳ vọng cao hơn → không thổi phồng độ gấp.
            nd = str(r.get("Ngày đăng") or "")[:10]
            if len(nd) == 10 and (not o["ngay_dang"] or nd < o["ngay_dang"]):
                o["ngay_dang"] = nd
            o["co_o"][m] = {"tuyen": str(r.get("Tuyến / Kênh") or "").strip(),
                            "da_lam": bool(str(r.get("Đã làm") or "").strip())}
    return ra


def _trang_chu(goc: str, thanh_vien: Sequence[str], bay_gio: float, ngay: int = 7) -> Dict[str, Dict[str, Set[str]]]:
    """`{mã: {"kenh_ta": {...}, "ngay": {...}}}` — video hiện trên trang chủ máy ảo của kênh ta trong `ngay` ngày."""
    tu = _dt.datetime.fromtimestamp(bay_gio - ngay * 86400).strftime("%Y-%m-%d")
    ra: Dict[str, Dict[str, Set[str]]] = {}
    for m in thanh_vien:
        for r in _csv_dong(os.path.join(_nc(goc, m), "trang-chu.csv")):
            lq = str(r.get("Lúc quét") or "")[:10]
            ma = str(r.get("Mã video") or "")
            if not ma or lq < tu or str(r.get("Short") or "").strip():
                continue
            o = ra.setdefault(ma, {"kenh_ta": set(), "ngay": set()})
            o["kenh_ta"].add(m)
            o["ngay"].add(lq)
    return ra


def _kho_gan_nhat(goc: str, kenh: str, bay_gio: float, lui: int = 2) -> List[Dict[str, str]]:
    for i in range(lui + 1):
        d = _dt.date.fromtimestamp(bay_gio - i * 86400).isoformat()
        p = os.path.join(goc, "CHANNEL", kenh, "phong-thi-nghiem", "kho-{0}.csv.gz".format(d))
        if os.path.isfile(p):
            try:
                with gzip.open(p, "rt", encoding="utf-8", newline="") as tep:
                    return [dict(r) for r in csv.DictReader(tep)]
            except (OSError, ValueError, EOFError, csv.Error):
                return []
    return []


def _nhan_kho(goc: str, thanh_vien: Sequence[str], bay_gio: float) -> Dict[str, Dict[str, Any]]:
    """`{mã: {"pool": {kênh ta}, "pool_xem", "vung": {kênh ta: vùng}, "nhan": {kênh ta: nhãn/cụm}}}` từ ảnh chụp kho."""
    ra: Dict[str, Dict[str, Any]] = {}
    for m in thanh_vien:
        for r in _kho_gan_nhat(goc, m, bay_gio):
            ma = str(r.get("ma") or "")
            if not ma:
                continue
            o = ra.setdefault(ma, {"pool": set(), "pool_xem": 0.0, "vung": {}, "nhan": {}})
            if (_so(r.get("trong_pool")) or 0) > 0:
                o["pool"].add(m)
                o["pool_xem"] += float(_so(r.get("pool_xem")) or 0)
            if r.get("vung"):
                o["vung"][m] = str(r["vung"])
            nh = str(r.get("nhan_y") or "").strip()
            if not nh or nh == "khac":
                nh = str(r.get("cum") or "").split("|")[0].strip()
            if nh:
                o["nhan"][m] = nh
    return ra


def _vung_ai(goc: str) -> Dict[str, str]:
    try:
        from .chu_quyen_vung import _vung_ai as va  # noqa: PLC0415

        return va(goc)
    except Exception:  # noqa: BLE001
        return {}


def _ten_vung(goc: str, thanh_vien: Sequence[str]) -> Dict[str, str]:
    try:
        from .chu_quyen_vung import _ten_vung as tv  # noqa: PLC0415

        return tv(goc, thanh_vien)
    except Exception:  # noqa: BLE001
        return {}


def _ban_do(goc: str) -> Dict[str, Any]:
    try:
        from . import chu_quyen_vung  # noqa: PLC0415

        return chu_quyen_vung.doc(goc)
    except Exception:  # noqa: BLE001
        return {}


def _song(goc: str, kenh: str) -> Tuple[bool, str]:
    """`(còn được phát & sản xuất được?, lý do nếu không)`."""
    if re.search(r"-v\d+$", kenh):
        return False, "bản thử A/B"
    try:
        from . import kenh_khong_phat  # noqa: PLC0415

        dung, ly = kenh_khong_phat.dang_dung(goc, kenh)
        if dung:
            return False, "không được YouTube phát"
    except Exception:  # noqa: BLE001
        pass
    return True, ""


def _tu_chay(goc: str, kenh: str) -> bool:
    try:
        from .kenh import doc_kenh  # noqa: PLC0415

        return bool(getattr(doc_kenh(goc, kenh), "tu_chay", False))
    except Exception:  # noqa: BLE001
        return False


def _tuyen(goc: str, kenh: str) -> List[str]:
    try:
        from .mot_nut import tuyen_dang_danh  # noqa: PLC0415

        return list(tuyen_dang_danh(goc, kenh) or [])
    except Exception:  # noqa: BLE001
        return []


def _da_lam_va_giu(goc: str, thanh_vien: Sequence[str]) -> Tuple[Dict[str, str], Dict[str, str], Set[str]]:
    """`({mã nguồn: kênh đã làm}, {mã nguồn: kênh đang giữ}, mã video CỦA TA)`."""
    lam: Dict[str, str] = {}
    try:
        from .da_lam import doc_ma_da_lam  # noqa: PLC0415
        from .phong_thi_nghiem.nguon import luot_san_xuat  # noqa: PLC0415

        for k in thanh_vien:
            for r in luot_san_xuat(goc, k):
                if r.get("ma") and not r.get("bo"):
                    lam.setdefault(r["ma"], k)
            for ma in doc_ma_da_lam(goc, k):
                lam.setdefault(ma, k)
    except Exception:  # noqa: BLE001
        pass
    giu: Dict[str, str] = {}
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        if thanh_vien:
            d = os.path.join(ncc.thu_muc(goc, thanh_vien[0]), "giu-nguon")
            for t in os.listdir(d):
                x = _doc_json(os.path.join(d, t), {}) or {}
                if isinstance(x, dict) and x.get("kenh") and time.time() - float(x.get("luc") or 0) < 7 * 86400:
                    giu[str(x.get("ma") or t[:-5])] = str(x["kenh"])
    except (OSError, Exception):  # noqa: BLE001
        pass
    cua_ta: Set[str] = set()
    try:
        from .phong_thi_nghiem.nguon import ma_video_nhom  # noqa: PLC0415

        cua_ta = ma_video_nhom(goc, thanh_vien)
    except Exception:  # noqa: BLE001
        pass
    return lam, giu, cua_ta


def _de_cu_mo(goc: str) -> List[Dict[str, Any]]:
    try:
        from . import nao  # noqa: PLC0415

        return [d for d in nao.doc_hanh_dong(goc) if d.get("lenh") == "uu-tien-nguon"]
    except Exception:  # noqa: BLE001
        return []


# ── sổ quan sát ─────────────────────────────────────────────────────────────

def _nap_quan_sat(goc: str, nhom: str, thanh_vien: Sequence[str], hop: Dict[str, Dict[str, Any]],
                  bay_gio: float) -> Dict[str, Any]:
    """Sổ quan sát `{"v": {mã: {k, d, o}}, "kho_nap": {kênh: [ngày]}}`: nạp ảnh chụp kho chưa nạp + quan sát của lượt
    này; bỏ video đăng > 40 ngày trước."""
    p = os.path.join(thu_muc(goc, nhom), TEP_QUAN_SAT)
    du = _doc_json(p, {}) or {}
    if not isinstance(du, dict):
        du = {}
    v: Dict[str, Dict[str, Any]] = du.get("v") if isinstance(du.get("v"), dict) else {}
    kho_nap: Dict[str, List[str]] = du.get("kho_nap") if isinstance(du.get("kho_nap"), dict) else {}
    moc_bo = _dt.date.fromtimestamp(bay_gio - 40 * 86400).isoformat()

    def them(ma: str, k: str, d: str, t: float, view: float) -> None:
        if not ma or not d or d < moc_bo or view is None or t is None:
            return
        o = v.setdefault(ma, {"k": k, "d": d, "o": []})
        if k:
            o["k"] = k
        if d < str(o.get("d") or "9999"):
            o["d"] = d            # ngày đăng sớm nhất từng thấy (xem `hop_content`)
        ds = o["o"]
        for x in ds:
            if abs(float(x[0]) - t) < 3600:
                if view > float(x[1]):
                    x[1] = view
                return
        ds.append([round(t), view])
        ds.sort(key=lambda x: x[0])
        if len(ds) > 40:
            del ds[:-40]
    for m in thanh_vien:
        da = set(kho_nap.get(m) or [])
        for f in sorted(glob.glob(os.path.join(goc, "CHANNEL", m, "phong-thi-nghiem", "kho-*.csv.gz"))):
            ngay = os.path.basename(f)[4:14]
            if ngay in da or ngay >= _dt.date.fromtimestamp(bay_gio).isoformat() or ngay < moc_bo:
                continue
            try:
                with gzip.open(f, "rt", encoding="utf-8", newline="") as tep:
                    for r in csv.DictReader(tep):
                        if "doi_thu" not in str(r.get("nguon") or ""):
                            continue
                        them(str(r.get("ma") or ""), str(r.get("kenh_nguon") or ""), str(r.get("ngay_dang") or "")[:10],
                             _so(r.get("luc")), _so(r.get("view")))
            except (OSError, ValueError, EOFError, csv.Error):
                continue
            da.add(ngay)
        kho_nap[m] = sorted(da)[-200:]
    for ma, o in hop.items():
        if o.get("view") is not None and o.get("luc"):
            them(ma, o.get("kenh_nguon", ""), o.get("ngay_dang", ""), float(o["luc"]), float(o["view"]))
    for ma in [m for m, o in v.items() if str(o.get("d") or "") < moc_bo]:
        del v[ma]
    return {"v": v, "kho_nap": kho_nap}


# ── AI đọc nghĩa (vùng, đúng ngách, kênh hợp tệp) ───────────────────────────

def _mo_ta_tep(goc: str, kenh: str) -> str:
    try:
        from . import tuyen_noi_dung as tn  # noqa: PLC0415

        cot, hang = tn.doc(goc, kenh)
        o = {c: i for i, c in enumerate(cot)}
        ds = []
        for h in hang:
            def g(t: str) -> str:
                i = o.get(t)
                return str(h[i]).strip() if i is not None and i < len(h) else ""
            if g("Trạng thái") == "đang đánh":
                ds.append("{0} — {1}".format(g("Tên tuyến") or g("Mã"), (g("Mô tả") or g("Insight"))[:220]))
        if ds:
            return "; ".join(ds)[:400]
    except Exception:  # noqa: BLE001
        pass
    try:
        from .nhom_kenh import tep_cua_kenh  # noqa: PLC0415

        return tep_cua_kenh(goc, kenh).replace("-", " ")
    except Exception:  # noqa: BLE001
        return ""


def de_bai_ai(mo_ta_ngach: str, kenh_ta: Dict[str, str], vung: Dict[str, str], ds: Sequence[Dict[str, Any]]) -> str:
    v = "\n".join("- {0}: {1}".format(m, t) for m, t in sorted(vung.items()))
    k = "\n".join("- {0}: {1}".format(m, t) for m, t in kenh_ta.items())
    x = "\n".join("{0}. [{1}] {2} — {3}".format(i + 1, (d.get("kenh_nguon") or "")[:30], d.get("tieu_de") or "",
                                               (d.get("mo_ta") or "")[:160].replace("\n", " "))
                  for i, d in enumerate(ds))
    return ("Bạn là biên tập viên chọn đề tài cho một nhóm kênh YouTube cùng ngách{0}.\nCác kênh CỦA TA — mỗi kênh "
            "đánh MỘT tệp khán giả:\n{1}\n\nVùng đề tài đang có (mã: tên):\n{2}\n\nDưới đây là video ĐỐI THỦ đang "
            "nổ view. Với MỖI video đọc NGHĨA (không khớp chữ): (1) có đúng ngách không; (2) thuộc vùng nào (mã có "
            "sẵn, hoặc \"moi-<slug>\" nếu không vùng nào hợp); (3) kênh ta nào mà khán giả sẽ coi đề tài này là CỦA "
            "MÌNH (mã kênh trong danh sách, hoặc \"\" nếu không kênh nào hợp).\n\n{3}\n\nTrả về DUY NHẤT một JSON: "
            "{{\"1\": {{\"ngach\": \"dung\"|\"lech\", \"vung\": \"<mã>\", \"kenh\": \"<mã kênh>\", \"do_tin\": 0-100, "
            "\"ly_do\": \"≤ 20 chữ tiếng Việt\"}}, …}} đủ mọi số.").format(
        (" — " + mo_ta_ngach) if mo_ta_ngach else "", k, v, x)


def _hoi_ai(goc: str, nhom: str, thanh_vien: Sequence[str], ds: Sequence[Dict[str, Any]], ch: Dict[str, Any],
            goi: Optional[Callable[..., str]], log: Callable[[str], None]) -> Dict[str, Dict[str, Any]]:
    """Nhãn AI (đệm `ai-nhan.json`, `ai_han_ngay` ngày) cho các dòng `ds` chưa có nhãn. `goi` None → chỉ đọc đệm."""
    p = os.path.join(thu_muc(goc, nhom), TEP_AI)
    nho = _doc_json(p, {}) or {}
    nho = nho if isinstance(nho, dict) else {}
    han = (_dt.date.today() - _dt.timedelta(days=int(ch.get("ai_han_ngay") or 14))).isoformat()
    con = {m: x for m, x in nho.items() if isinstance(x, dict) and str(x.get("ngay") or "") >= han}
    can = [d for d in ds if d["ma"] not in con][:int(ch.get("ai_toi_da") or 0)]
    if not can or goi is None:
        return con
    try:
        from .chien_truong import mo_ta_ngach  # noqa: PLC0415

        n = mo_ta_ngach()
        ngach = "\"{0}\"{1}".format(n.get("ten") or "", " (ngôn ngữ {0})".format(n["ngon_ngu"]) if n.get("ngon_ngu")
                                    else "")
    except Exception:  # noqa: BLE001
        ngach = ""
    song = [k for k in thanh_vien if _song(goc, k)[0]]
    kenh_ta = {k: _mo_ta_tep(goc, k) for k in song}
    vung = _ten_vung(goc, thanh_vien)
    vung.pop("khac", None)
    try:
        from .goi_van_ban import loc_json  # noqa: PLC0415

        tho = goi(de_bai_ai(ngach, kenh_ta, vung, can), mo_hinh=str(ch.get("ai_mo_hinh") or "claude-fable-5"),
                  khoa="radar-dot-bien-{0}-{1}".format(_dt.date.today().isoformat(), len(can)), toi_da_token=6000)
        kq = loc_json(tho)
    except Exception as loi:  # noqa: BLE001
        log("  radar: AI đọc nghĩa hỏng ({0}) — dùng nhãn sẵn có.".format(str(loi)[:100]))
        return con
    if not isinstance(kq, dict):
        return con
    moi = {}
    for so_, x in kq.items():
        try:
            d = can[int(so_) - 1]
        except (ValueError, IndexError):
            continue
        if not isinstance(x, dict):
            continue
        kenh = str(x.get("kenh") or "")
        moi[d["ma"]] = {"ngach": "lech" if str(x.get("ngach") or "").lower() == "lech" else "dung",
                        "vung": str(x.get("vung") or "")[:40], "kenh": kenh if kenh in song else "",
                        "do_tin": int(_so(x.get("do_tin")) or 0), "ly_do": str(x.get("ly_do") or "")[:120],
                        "ngay": _dt.date.today().isoformat()}
    if moi:
        con.update(moi)
        try:
            from .nghien_cuu_chung import ghi_json_gop  # noqa: PLC0415

            ghi_json_gop(p, moi)
        except OSError:
            pass
        log("  radar: AI đọc nghĩa {0} video đang nổ (vùng · đúng ngách · kênh hợp tệp).".format(len(moi)))
    return con


# ── tính radar ──────────────────────────────────────────────────────────────

def _nen_kenh(hop: Dict[str, Dict[str, Any]], ch: Dict[str, Any]) -> Dict[str, float]:
    """`{tên kênh đối thủ: trung vị view video dài ≥ nen_tuoi_ngay ngày}` (30 video gần nhất, n ≥ 5)."""
    theo: Dict[str, List[Tuple[str, float]]] = {}
    g_min = float(ch.get("giay_toi_thieu") or 240) / 60.0
    nay = time.time()
    for o in hop.values():
        t0 = _ep_ngay_dang(o.get("ngay_dang"))
        if t0 is None or o.get("view") is None:
            continue
        if o.get("dai_phut") is not None and o["dai_phut"] < g_min:
            continue
        if (float(o.get("luc") or nay) - t0) / 86400.0 < float(ch.get("nen_tuoi_ngay") or 14):
            continue
        theo.setdefault(o["kenh_nguon"], []).append((o["ngay_dang"], float(o["view"])))
    ra = {}
    for k, ds in theo.items():
        ds.sort(reverse=True)
        ds = ds[:int(ch.get("nen_so_video") or 30)]
        if len(ds) >= int(ch.get("nen_n_toi_thieu") or 5):
            ra[k] = max(1.0, _trung_vi([x[1] for x in ds]) or 1.0)
    return ra


#: Hai kênh trùng TÊN (sổ content nối với danh bạ bằng tên; sổ thật 13/10 có 12 cặp, vd. một kênh theo dõi + một kênh
#: đã bỏ): dòng tầng cao hơn / đang theo dõi thắng — không thì video của kênh theo dõi bị gạt "kênh lạc ngách".
_HANG_TEN = {"1": 0, "2": 1, "3": 2}


def _theo_ten(so_chung: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    ra: Dict[str, Dict[str, Any]] = {}

    def hang(e: Dict[str, Any]) -> Tuple[int, int]:
        return _HANG_TEN.get(str(e.get("tang") or ""), 3), 0 if e.get("trang_thai") == "theo dõi" else 1
    for e in (so_chung.get("kenh") or {}).values():
        for t in [e.get("ten")] + list(e.get("ten_khac") or []):
            if t:
                t = str(t).strip()
                if t not in ra or hang(e) < hang(ra[t]):
                    ra[t] = e
    return ra


def _vung_video(ma: str, link: str, vung_ai: Dict[str, str], kho: Dict[str, Any], ai: Dict[str, Any]) -> Tuple[str, str]:
    """`(vùng, nguồn)` — AI chia vùng của chiến trường → nhãn kho (đa số) → AI radar."""
    v = vung_ai.get(link) or vung_ai.get(ma)
    if v:
        return v, "chiến trường AI"
    ds = list(((kho or {}).get("vung") or {}).values())
    if ds:
        dem: Dict[str, int] = {}
        for x in ds:
            dem[x] = dem.get(x, 0) + 1
        return max(dem.items(), key=lambda kv: kv[1])[0], "nhãn kho"
    if (ai or {}).get("vung"):
        return str(ai["vung"]), "AI radar"
    return "", ""


def tinh(goc: str, nhom: str, *, bay_gio: Optional[float] = None, ch: Optional[Dict[str, Any]] = None,
         goi: Optional[Callable[..., str]] = None, log: Optional[Callable[[str], None]] = None,
         ghi_quan_sat: bool = True) -> Dict[str, Any]:
    """Tính bảng radar của nhóm (không ép chọn). Trả `{"luc", "nhom", "thong_ke", "duong_cong", "dong": [...]}`."""
    from . import so_doi_thu_chung as sdc  # noqa: PLC0415

    def ghi(m: str) -> None:
        if log is not None:
            log(m)
    t_bd = time.time()
    bay_gio = bay_gio or time.time()
    ch = ch or cau_hinh(goc)
    tv = sdc.thanh_vien_nhom(goc, nhom)
    so_chung = sdc.doc(goc, nhom) or sdc.gop(goc, nhom, thanh_vien=tv, ghi=False)
    theo_ten = _theo_ten(so_chung)
    hop = hop_content(goc, tv)
    qs = _nap_quan_sat(goc, nhom, tv, hop, bay_gio)
    nen = _nen_kenh(hop, ch)
    duong = dung_duong_cong(qs["v"], nen, n_rieng=int(ch.get("duong_rieng_n") or 5))
    tc = _trang_chu(goc, tv, bay_gio)
    kho = _nhan_kho(goc, tv, bay_gio)
    vung_ai = _vung_ai(goc)
    ban_do = _ban_do(goc)
    ten_vung = _ten_vung(goc, tv)
    lam, giu, cua_ta = _da_lam_va_giu(goc, tv)
    song = {k: _song(goc, k) for k in tv}
    tuyen = {k: _tuyen(goc, k) for k in tv}
    g_min = float(ch.get("giay_toi_thieu") or 240) / 60.0
    t_min, t_max = float(ch.get("tuoi_toi_thieu_gio") or 6), float(ch.get("tuoi_toi_da_gio") or 168)
    nguong = [float(x) for x in (ch.get("muc") or [3, 8, 20])]
    dem = {"video": len(hop), "trong_tuoi": 0, "co_nen": 0, "kenh_nen": len(nen), "bo_kenh_lac": 0}
    dong: List[Dict[str, Any]] = []
    for ma, o in hop.items():
        t0 = _ep_ngay_dang(o.get("ngay_dang"))
        if t0 is None or o.get("view") is None or ma in cua_ta:
            continue
        gio = (float(o["luc"]) - t0) / 3600.0
        if not (t_min <= gio <= t_max):
            continue
        if o.get("dai_phut") is not None and o["dai_phut"] < g_min:
            continue
        dem["trong_tuoi"] += 1
        e = theo_ten.get(o["kenh_nguon"]) or {}
        ngach = (e.get("ngach") or {}).get("ket")
        song_k = (e.get("song") or {}).get("ket")
        if ngach == "bo" or song_k in ("chet", "lech_tieng"):
            dem["bo_kenh_lac"] += 1
            continue
        b = nen.get(o["kenh_nguon"])
        nguon_nen = "kênh"
        if not b:
            b = _so((e.get("so") or {}).get("View TV"))
            nguon_nen = "sổ đối thủ (View TV)"
        if not b or b <= 0:
            continue
        dem["co_nen"] += 1
        kv, nguon_kv = ky_vong_tai(duong, o["kenh_nguon"], float(b), max(gio, 1.0))
        boi = float(o["view"]) / max(kv, 1.0)
        muc = muc_cua(boi, nguong)
        if muc < 1 or float(o["view"]) < float(ch.get("view_toi_thieu") or 0):
            continue
        toc = float(o["view"]) / max(gio, 1.0)
        toc_gan = None
        obs = sorted((qs["v"].get(ma) or {}).get("o") or [], key=lambda x: x[0])
        for t, v in reversed(obs):
            if float(o["luc"]) - float(t) >= 3 * 3600 and float(o["view"]) >= float(v):
                toc_gan = (float(o["view"]) - float(v)) / ((float(o["luc"]) - float(t)) / 3600.0)
                break
        t_c = tc.get(ma) or {}
        k_o = kho.get(ma) or {}
        dong.append({
            "ma": ma, "link": o.get("link") or "https://www.youtube.com/watch?v=" + ma, "tieu_de": o.get("tieu_de", ""),
            "tieu_de_viet": o.get("tieu_de_viet", ""), "kenh_nguon": o["kenh_nguon"],
            "kenh_khoa": e.get("khoa", ""), "kenh_ngach": ngach or "?", "kenh_trang_thai": e.get("trang_thai", ""),
            "kenh_ban_dua": bool(e.get("ban_dua")), "kenh_tang": str(e.get("tang") or ""),
            "kenh_ai": (e.get("so") or {}).get("AI", ""), "kenh_subs": _so((e.get("so") or {}).get("Subs")),
            "view": float(o["view"]), "ngay_dang": o.get("ngay_dang", ""), "dai_phut": o.get("dai_phut"),
            "tuoi_gio": round(gio, 1), "nen": round(float(b), 1), "nen_nguon": nguon_nen,
            "ky_vong": round(kv, 1), "ky_vong_nguon": nguon_kv, "boi": round(boi, 2), "muc": muc,
            "ten_muc": TEN_MUC.get(muc, ""), "trong_cua_so": bool(ch["cua_so_gio"][0] <= gio <= ch["cua_so_gio"][1]),
            "toc_do": round(toc, 1), "toc_do_gan": round(toc_gan, 1) if toc_gan is not None else None,
            "tang_toc": round(toc_gan / toc, 2) if (toc_gan is not None and toc > 0) else None,
            "tang_ngay": o.get("tang_ngay"),
            "trang_chu": sorted(t_c.get("kenh_ta") or []), "trang_chu_ngay": len(t_c.get("ngay") or []),
            "pool": sorted(k_o.get("pool") or []), "pool_xem": round(float(k_o.get("pool_xem") or 0), 1),
            "nhan_kho": dict(k_o.get("nhan") or {}), "vung_kho": dict(k_o.get("vung") or {}),
            "co_o": o.get("co_o") or {}, "mo_ta": o.get("mo_ta", ""), "luc_quan_sat": o.get("luc"),
        })
    # điểm xếp hạng: log(gấp, trần ×200 — kênh nền vài chục view thổi phồng tỉ số) × độ tươi + cỡ thị trường
    # (log10 view) + hiện diện ở khán giả ta + đang tăng tốc + tầng kênh nguồn (`DIEM_TANG`)
    for d in dong:
        g = d["tuoi_gio"]
        tuoi_he = 1.0 if g <= 72 else (0.75 if g <= 120 else 0.55)
        d["diem"] = round(math.log(max(min(d["boi"], TRAN_BOI_DIEM), 1.0)) * tuoi_he
                          + 0.35 * math.log10(max(d["view"], 1.0)) + 0.15 * math.log1p(d["trang_chu_ngay"])
                          + (0.15 if d["pool"] else 0.0) + (0.1 if (d.get("tang_toc") or 0) >= 1.0 else 0.0)
                          + DIEM_TANG.get(d.get("kenh_tang") or "", 0.0), 4)
    dong.sort(key=lambda d: (-d["diem"], -d["boi"], d["ma"]))
    so_dong = max(1, int(ch.get("so_dong") or 60))
    # cắt bảng theo `so_dong` nhưng KHÔNG bỏ video nổ (mức ≥ 2) nào — kể cả của kênh tầng 3
    dong = dong[:so_dong] + [d for d in dong[so_dong:] if d["muc"] >= 2]
    # nhãn AI (đệm; gọi mới chỉ khi có `goi`) — trước khi gán kênh
    ai = _hoi_ai(goc, nhom, tv, dong, ch, goi if ch.get("ai_bat") else None, ghi)
    for d in dong:
        x = ai.get(d["ma"]) or {}
        vung, nguon_v = _vung_video(d["ma"], d["link"], vung_ai, {"vung": d["vung_kho"]}, x)
        d["vung"], d["vung_nguon"] = vung, nguon_v
        d["ten_vung"] = ten_vung.get(vung, vung)
        nh = list(d["nhan_kho"].values())
        d["cum"] = max(set(nh), key=nh.count) if nh else (vung or "")
        d["ai"] = x
        d["dung_ngach"] = not (vung == "ngoai-ngach" or x.get("ngach") == "lech")
        _gan(d, ban_do, song, tuyen, lam, giu, x)
    ghi("  radar đột biến: {0} video nhóm · {1} trong tuổi 6h–7 ngày · {2} có nền kênh ({3} kênh) → {4} đột biến "
        "(nổ {5}, siêu nổ {6}) · {7:.1f}s".format(
            dem["video"], dem["trong_tuoi"], dem["co_nen"], dem["kenh_nen"], len(dong),
            sum(1 for d in dong if d["muc"] >= 2), sum(1 for d in dong if d["muc"] >= 3), time.time() - t_bd))
    if ghi_quan_sat:
        try:
            _ghi_json(os.path.join(thu_muc(goc, nhom), TEP_QUAN_SAT), qs)
        except OSError:
            pass
    return {"luc": _dt.datetime.fromtimestamp(bay_gio).strftime("%Y-%m-%dT%H:%M:%S"), "nhom": nhom,
            "thanh_vien": tv, "thong_ke": dem, "cau_hinh": {k: ch[k] for k in ("muc", "ep_boi", "ep_tuoi_gio",
                                                                              "ep_view_toi_thieu", "ep_moi_kenh_ngay")},
            "duong_cong": {"tam_gio": list(TAM_O), "ngach": [round(x, 3) for x in duong.ngach],
                           "n": duong.n_ngach, "kenh_rieng": sum(1 for k, r in duong.rieng.items()
                                                                 if any(n >= duong.n_min for _x, n in r.values()))},
            "song": {k: {"song": s[0], "ly_do": s[1], "tu_chay": _tu_chay(goc, k)} for k, s in song.items()},
            "dong": dong}


def _gan(d: Dict[str, Any], ban_do: Dict[str, Any], song: Dict[str, Tuple[bool, str]],
         tuyen: Dict[str, List[str]], lam: Dict[str, str], giu: Dict[str, str], ai: Dict[str, Any]) -> None:
    """Gán kênh ta hợp nhất (xem đầu tệp) → `gan`, `ly_do_gan`, `hop_tep` (đủ chắc để ép), `da_lam_boi`."""
    d["gan"], d["ly_do_gan"], d["hop_tep"], d["da_lam_boi"] = "", "", False, ""
    if d["ma"] in lam:
        d["da_lam_boi"] = lam[d["ma"]]
        d["ly_do_gan"] = "đã làm bởi {0}".format(lam[d["ma"]])
        return
    if d["ma"] in giu:
        d["da_lam_boi"] = giu[d["ma"]]
        d["ly_do_gan"] = "{0} đang giữ nguồn".format(giu[d["ma"]])
        return
    con = [k for k, s in song.items() if s[0]]
    m = ((ban_do.get("vung") or {}).get(d.get("vung") or "") or {}) if d.get("vung") else {}
    chu = str(m.get("chu") or "")
    if chu and not m.get("nhuong"):
        if chu in con:
            d["gan"], d["ly_do_gan"], d["hop_tep"] = chu, "chủ vùng “{0}”".format(d.get("ten_vung") or d["vung"]), True
            return
        d["ly_do_gan"] = "chủ vùng {0} {1} — ".format(chu, (song.get(chu) or (False, "không trong nhóm"))[1] or "không sống")
    k_ai = str(ai.get("kenh") or "")
    if k_ai in con:
        d["gan"] = k_ai
        d["ly_do_gan"] += "AI: tệp {0} hợp ({1})".format(k_ai, (ai.get("ly_do") or "")[:60])
        d["hop_tep"] = int(ai.get("do_tin") or 0) >= 60
        return
    # Nhãn tuyến (≈ tệp khán giả) mà AI gán tuyến của TỪNG kênh ta đặt cho video — cùng một bộ mã tệp của ngách
    # (`tuyen.csv`): nhãn L bỏ phiếu cho kênh đang đánh tuyến L.
    phieu: Dict[str, int] = {}
    n_nhan = 0
    for x in (d.get("co_o") or {}).values():
        lab = str((x or {}).get("tuyen") or "").strip()
        if not lab or lab == "khac":
            continue
        n_nhan += 1
        for k in con:
            if lab in set(tuyen.get(k) or []):
                phieu[k] = phieu.get(k, 0) + 1
    if phieu:
        thay_ = set(d.get("trang_chu") or []) | set(d.get("pool") or [])
        k = max(phieu, key=lambda x: (phieu[x], x in thay_, x))
        d["gan"] = k
        d["ly_do_gan"] += "nhãn tuyến: {0}/{1} kênh ta xếp video vào tệp của {2}".format(phieu[k], n_nhan, k)
        d["hop_tep"] = True
        return
    thay = [k for k in con if k in set(d.get("trang_chu") or []) | set(d.get("pool") or [])]
    if thay:
        k = max(thay, key=lambda x: ((x in (d.get("pool") or [])), (x in (d.get("trang_chu") or []))))
        d["gan"] = k
        d["ly_do_gan"] += "khán giả {0} đã gặp video ({1})".format(
            k, "pool" if k in (d.get("pool") or []) else "trang chủ")
        return
    for k in (m.get("chia_se") or []):
        if k in con:
            d["gan"], d["ly_do_gan"] = k, d["ly_do_gan"] + "vùng chia sẻ cho {0}".format(k)
            return
    d["ly_do_gan"] += "chưa có kênh hợp"


# ── ép chọn ─────────────────────────────────────────────────────────────────

def _trang_thai_hanh_dong(goc: str) -> Dict[str, Dict[str, Any]]:
    """`{mã video: hành động uu-tien-nguon mới nhất có link ấy}`."""
    ra: Dict[str, Dict[str, Any]] = {}
    for d in _de_cu_mo(goc):
        ma = _ma_video(str((d.get("tham_so") or {}).get("link") or ""))
        if ma and (ma not in ra or str(d.get("luc") or "") > str(ra[ma].get("luc") or "")):
            ra[ma] = d
    return ra


def _ep_hom_nay(goc: str, kenh: str, hom: str) -> int:
    return sum(1 for d in _de_cu_mo(goc) if (d.get("tham_so") or {}).get("radar_thi_truong")
               and (d.get("tham_so") or {}).get("kenh") == kenh and str(d.get("luc") or "")[:10] == hom
               and d.get("trang_thai") != "huy")


def _he_so_ngach(kq: Dict[str, Any], gio: float) -> float:
    """Phần view một video thường đạt ở tuổi `gio` so với lúc bão hoà (đường cong NGÁCH của lượt radar)."""
    dc = kq.get("duong_cong") or {}
    ng = list(dc.get("ngach") or DUONG_DU_PHONG)
    if len(ng) != len(TAM_O):
        ng = list(DUONG_DU_PHONG)
    return DuongCong(ng, {}, [0] * len(TAM_O)).he_so("", max(gio, 1.0))[0]


def _san_v7(goc: str, kenh: str) -> Dict[str, Any]:
    """Sàn nguồn mà kênh ta TỰ khai trong cấu hình V7 (`no.san_view`, `no.loai_kenh_yeu`, `no.kenh_yeu_duoi`)."""
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        c, _ = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
        return dict((c or {}).get("no") or {})
    except Exception:  # noqa: BLE001
        return {}


def _vuong_san_v7(goc: str, d: Dict[str, Any], kq: Dict[str, Any], cache: Dict[str, Dict[str, Any]]) -> str:
    """Luật nguồn kênh được gán TỰ khai trong V7 — ép chọn của máy không vượt (khác ép chọn của não):
    `loai_kenh_yeu` + nền kênh nguồn < `kenh_yeu_duoi` → bỏ; view < `san_view` × đường cong ngách ở tuổi video (sàn V7
    tính trên view bão hoà, video 2 ngày tuổi mới đạt ~½) → bỏ. "" = qua."""
    k = d.get("gan") or ""
    if k not in cache:
        cache[k] = _san_v7(goc, k)
    no = cache[k]
    try:
        if no.get("loai_kenh_yeu") and float(d.get("nen") or 0) < float(no.get("kenh_yeu_duoi") or 0):
            return "kênh nguồn yếu theo luật V7 của {0} (nền {1} < {2})".format(k, _f(d.get("nen")),
                                                                              _f(no.get("kenh_yeu_duoi")))
        san = float(no.get("san_view") or 0) * _he_so_ngach(kq, float(d.get("tuoi_gio") or 0))
        if san and float(d.get("view") or 0) < san:
            return "view {0} < sàn V7 của {1} ở tuổi {2}h ({3} = {4} × đường cong)".format(
                _f(d.get("view")), k, _f(d.get("tuoi_gio")), _f(san), _f(no.get("san_view")))
    except (TypeError, ValueError):
        return ""
    return ""


def quyet_ep(goc: str, kq: Dict[str, Any], *, ch: Optional[Dict[str, Any]] = None, ghi: bool = True,
             bay_gio: Optional[float] = None, log: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Duyệt các dòng NỔ (mức ≥ 2) → ép chọn hoặc ghi lý do bỏ (luật ở đầu tệp). Trả mọi quyết định (đã ghi sổ
    `quyet-dinh.jsonl` khi `ghi`). `ghi=False` → chỉ nói SẼ làm gì (hành động không tạo)."""
    ch = ch or cau_hinh(goc)
    bay_gio = bay_gio or time.time()
    hom = _dt.date.fromtimestamp(bay_gio).isoformat()
    hd = _trang_thai_hanh_dong(goc)
    da_ep_luot: Dict[str, int] = {}
    so_luot = 0
    san_cache: Dict[str, Dict[str, Any]] = {}
    ra: List[Dict[str, Any]] = []
    ph = ch.get("ep_phut") or [8.0, 40.0]
    for d in kq.get("dong") or []:
        # Ứng viên ép chọn = đã vượt ngưỡng "cực mạnh" (độ gấp + còn trong cửa sổ tuổi); dòng khác chỉ theo dõi.
        if d["muc"] < 2 or d["boi"] < float(ch["ep_boi"]) or d["tuoi_gio"] > float(ch["ep_tuoi_gio"]):
            continue
        q = {"luc": _dt.datetime.fromtimestamp(bay_gio).strftime("%Y-%m-%dT%H:%M:%S"), "ma": d["ma"],
             "kenh_nguon": d["kenh_nguon"], "view": d["view"], "ky_vong": d["ky_vong"], "boi": d["boi"],
             "muc": d["muc"], "tuoi_gio": d["tuoi_gio"], "gan": d.get("gan", ""), "ly_do_gan": d.get("ly_do_gan", ""),
             "vung": d.get("vung", ""), "quyet": "bo", "vi_sao": ""}
        cu = hd.get(d["ma"])
        ly = ""
        if not ch.get("ep_bat"):
            ly = "ép chọn đang tắt"
        elif d["view"] < float(ch["ep_view_toi_thieu"]):
            ly = "view {0} < {1}".format(_f(d["view"]), _f(ch["ep_view_toi_thieu"]))
        elif d.get("dai_phut") is None or not (float(ph[0]) <= d["dai_phut"] <= float(ph[1])):
            ly = "dài {0} phút ngoài khuôn {1}–{2}".format(_f(d.get("dai_phut"), 1), ph[0], ph[1])
        elif not d.get("dung_ngach", True):
            ly = "video lạc ngách ({0})".format(d.get("vung") or (d.get("ai") or {}).get("ly_do") or "AI")
        elif d.get("kenh_ngach") != "giu" and not d.get("kenh_ban_dua"):
            ly = "kênh nguồn chưa được AI xác nhận đúng ngách ({0})".format(d.get("kenh_ngach") or "?")
        elif d.get("da_lam_boi"):
            ly = d.get("ly_do_gan") or "đã làm"
        elif cu is not None and cu.get("trang_thai") in ("mo", "xong") and not cu.get("khong_tinh"):
            ly = "đã có đề cử {0} cho {1} ({2})".format(cu.get("id"), (cu.get("tham_so") or {}).get("kenh"),
                                                         cu.get("trang_thai"))
        elif not d.get("gan"):
            ly = "không kênh ta nào hợp/sống ({0})".format(d.get("ly_do_gan") or "")
        elif not d.get("hop_tep"):
            ly = "kênh {0} chỉ gặp video qua trang chủ/pool — chưa chắc hợp tệp".format(d["gan"])
        elif not (kq.get("song") or {}).get(d["gan"], {}).get("tu_chay", True):
            ly = "kênh {0} đang tắt tự chạy".format(d["gan"])
        elif _vuong_san_v7(goc, d, kq, san_cache):   # (nhớ cấu hình V7 theo kênh — gọi hai lần không đọc lại đĩa)
            ly = _vuong_san_v7(goc, d, kq, san_cache)
        elif _ep_hom_nay(goc, d["gan"], hom) + da_ep_luot.get(d["gan"], 0) >= int(ch["ep_moi_kenh_ngay"]):
            ly = "{0} đã có {1} ép chọn radar hôm nay (trần {2})".format(d["gan"], ch["ep_moi_kenh_ngay"],
                                                                         ch["ep_moi_kenh_ngay"])
            q["cho"] = True   # vướng trần — lượt/ngày sau xét lại (còn trong cửa sổ tuổi thì vẫn ép được)
        elif so_luot >= int(ch["ep_moi_luot"]):
            ly = "đủ {0} ép chọn trong lượt này".format(ch["ep_moi_luot"])
            q["cho"] = True
        if ly:
            q["vi_sao"] = ly
            ra.append(q)
            continue
        so_lieu = {k: d.get(k) for k in ("view", "ky_vong", "ky_vong_nguon", "nen", "boi", "muc", "tuoi_gio",
                                          "toc_do", "toc_do_gan", "trang_chu", "pool", "vung", "cum")}
        ly_do = ("RADAR THỊ TRƯỜNG: «{0}» ({1}) {2} view ở {3}h = ×{4} kỳ vọng {5} ({6}, nền {7}) — {8}; gán {9}: {10}"
                 .format(d["tieu_de"][:60], d["kenh_nguon"][:24], _f(d["view"]), _f(d["tuoi_gio"]), _f(d["boi"], 1),
                         _f(d["ky_vong"]), d["ky_vong_nguon"], _f(d["nen"]), d["ten_muc"], d["gan"], d["ly_do_gan"]))
        du_doan = ("video {0} làm từ nguồn này đạt phân vị ≥ 50 hiển thị @96h so kênh (thước chung)").format(d["gan"])
        nguon_dong = {"ma": d["ma"], "link": d["link"], "tieu_de": d["tieu_de"], "kenh": d["kenh_nguon"],
                      "view": d["view"], "dai_giay": round(float(d["dai_phut"]) * 60) if d.get("dai_phut") else None,
                      "ngay_dang": d["ngay_dang"], "cum": [x for x in [d.get("cum")] if x], "boi": d["boi"],
                      "muc": d["muc"], "tuoi_gio": d["tuoi_gio"]}
        if not ghi:
            q.update(quyet="se_ep", vi_sao="(chạy thử) sẽ ép chọn cho " + d["gan"])
            da_ep_luot[d["gan"]] = da_ep_luot.get(d["gan"], 0) + 1
            so_luot += 1
            ra.append(q)
            continue
        try:
            from . import nao  # noqa: PLC0415

            x = nao.tao_ep_chon_radar(goc, d["gan"], d["link"], d["ma"], ly_do=ly_do, du_doan=du_doan,
                                      so_lieu=so_lieu, nguon_dong=nguon_dong,
                                      toi_da_ngay=int(ch["ep_moi_kenh_ngay"]))
            q.update(quyet="ep_chon", hanh_dong=x.get("id"), vi_sao="ép chọn cho {0} ({1})".format(
                d["gan"], d["ly_do_gan"]))
            da_ep_luot[d["gan"]] = da_ep_luot.get(d["gan"], 0) + 1
            so_luot += 1
            if log is not None:
                log("  radar: ÉP CHỌN {0} cho {1} — ×{2} kỳ vọng ở {3}h ({4} view) · đề cử {5}".format(
                    d["ma"], d["gan"], _f(d["boi"], 1), _f(d["tuoi_gio"]), _f(d["view"]), x.get("id")))
        except Exception as loi:  # noqa: BLE001 — một đề cử hỏng không giết lượt
            q["vi_sao"] = "não từ chối: {0}".format(str(loi)[:160])
        ra.append(q)
    if ghi and ra:
        try:
            from .phong_thi_nghiem._chung import them_dong  # noqa: PLC0415

            them_dong(os.path.join(thu_muc(goc, kq["nhom"]), TEP_QUYET), ra)
        except OSError:
            pass
    return ra


# ── chạy ────────────────────────────────────────────────────────────────────

def chay(goc: str, nhom: str, *, dung_ai: bool = False, ep: bool = True, ghi: bool = True,
         goi: Optional[Callable[..., str]] = None, log: Optional[Callable[[str], None]] = None,
         bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Một lượt radar cho nhóm: tính → (ép chọn) → ghi `radar-moi-nhat.json`/`radar-<ngày>.json` + liên quan vào sổ
    chung. `dung_ai` + ví cho phép → AI đọc nghĩa top. `ghi=False` → không ghi gì (chạy thử)."""
    ch = cau_hinh(goc)
    if dung_ai and goi is None:
        try:
            from . import cum_y_nghia  # noqa: PLC0415

            goi = cum_y_nghia.goi_vi(goc, log)
        except Exception:  # noqa: BLE001
            goi = None
    kq = tinh(goc, nhom, bay_gio=bay_gio, ch=ch, goi=goi if dung_ai else None, log=log, ghi_quan_sat=ghi)
    kq["quyet_dinh"] = quyet_ep(goc, kq, ch=ch, ghi=ghi and ep, bay_gio=bay_gio, log=log) if (ep or not ghi) else []
    for d in kq.get("dong") or []:   # bảng lưu gọn: mô tả chỉ để AI đọc; nhãn từng kênh rút về {kênh: tuyến}
        d.pop("mo_ta", None)
        d.pop("nhan_kho", None)
        d.pop("vung_kho", None)
        d["co_o"] = {m: str((x or {}).get("tuyen") or "") for m, x in (d.get("co_o") or {}).items()}
    if ghi:
        d = thu_muc(goc, nhom)
        os.makedirs(d, exist_ok=True)
        _ghi_json(os.path.join(d, TEP_MOI), kq)
        _ghi_json(os.path.join(d, "radar-{0}.json".format(kq["luc"][:10])), kq)
        _don_cu(d)
        try:
            _cap_nhat_lien_quan(goc, nhom, kq)
        except Exception:  # noqa: BLE001
            pass
    return kq


def _don_cu(d: str) -> None:
    moc = (_dt.date.today() - _dt.timedelta(days=GIU_NGAY_BAN)).isoformat()
    for p in glob.glob(os.path.join(d, "radar-20*.json")):
        if os.path.basename(p)[6:16] < moc:
            try:
                os.remove(p)
            except OSError:
                pass


def _cap_nhat_lien_quan(goc: str, nhom: str, kq: Dict[str, Any]) -> None:
    """Liên quan theo kênh ta của mỗi kênh đối thủ (sổ chung `lien_quan`): trang chủ (dòng 28 ngày), pool (video),
    tệp khớp (% dòng content nhãn tuyến đang đánh), số dòng content."""
    from . import so_doi_thu_chung as sdc  # noqa: PLC0415

    tv = kq.get("thanh_vien") or sdc.thanh_vien_nhom(goc, nhom)
    so_chung = sdc.doc(goc, nhom)
    if not so_chung:
        return
    theo_ten = _theo_ten(so_chung)
    tuyen = {k: set(_tuyen(goc, k)) for k in tv}
    lq: Dict[str, Dict[str, Dict[str, Any]]] = {}
    tu = (_dt.date.today() - _dt.timedelta(days=28)).isoformat()
    for m in tv:
        for r in _csv_dong(os.path.join(_nc(goc, m), "trang-chu.csv")):
            if str(r.get("Lúc quét") or "")[:10] < tu or str(r.get("Short") or "").strip():
                continue
            e = theo_ten.get(str(r.get("Kênh") or "").strip())
            if e:
                o = lq.setdefault(e["khoa"], {}).setdefault(m, {"tc": 0, "pool": 0, "khop_tep": None, "n_content": 0})
                o["tc"] += 1
        dem: Dict[str, List[int]] = {}
        for r in _csv_dong(os.path.join(_nc(goc, m), "content.csv")):
            e = theo_ten.get(str(r.get("Kênh") or "").strip())
            if not e:
                continue
            x = dem.setdefault(e["khoa"], [0, 0, 0])
            x[0] += 1
            nh = str(r.get("Tuyến / Kênh") or "").strip()
            if nh:
                x[1] += 1
                if nh in tuyen.get(m, set()):
                    x[2] += 1
        for k, (n, co_nhan, khop) in dem.items():
            o = lq.setdefault(k, {}).setdefault(m, {"tc": 0, "pool": 0, "khop_tep": None, "n_content": 0})
            o["n_content"] = n
            o["khop_tep"] = round(100.0 * khop / co_nhan, 1) if co_nhan else None
        for r in _kho_gan_nhat(goc, m, time.time()):
            if (_so(r.get("trong_pool")) or 0) > 0:
                e = theo_ten.get(str(r.get("kenh_nguon") or "").strip())
                if e:
                    o = lq.setdefault(e["khoa"], {}).setdefault(m, {"tc": 0, "pool": 0, "khop_tep": None,
                                                                    "n_content": 0})
                    o["pool"] += 1
    sdc.gop(goc, nhom, thanh_vien=tv, lien_quan=lq)


def chay_an_toan(goc: str, nhom: str, **kw: Any) -> Dict[str, Any]:
    """`chay` không bao giờ ném lỗi (nơi gọi là lượt nghiên cứu)."""
    log = kw.get("log")
    try:
        return chay(goc, nhom, **kw)
    except Exception as loi:  # noqa: BLE001
        if log is not None:
            try:
                log("  radar đột biến hỏng, bỏ qua (nghiên cứu không bị ảnh hưởng): {0}: {1}".format(
                    type(loi).__name__, str(loi)[:160]))
            except Exception:  # noqa: BLE001
                pass
        try:
            from . import tu_hoc  # noqa: PLC0415

            tu_hoc.canh_bao(goc, "radar_dot_bien", loi, "")
        except Exception:  # noqa: BLE001
            pass
        return {"loi": "{0}: {1}".format(type(loi).__name__, str(loi)[:200])}


#: > 0 khi lượt nghiên cứu NHÓM đang chạy chuỗi cho từng kênh (`hoan`) — radar đợi chạy một lần ở cuối lượt.
_HOAN = [0]


class hoan:
    """`with radar_dot_bien.hoan(): …` — trong khối, `chay_neu_cu` không chạy (lượt nhóm tự chạy radar ở cuối)."""

    def __enter__(self) -> "hoan":
        _HOAN[0] += 1
        return self

    def __exit__(self, *_a: Any) -> None:
        _HOAN[0] = max(0, _HOAN[0] - 1)


def chay_neu_cu(goc: str, kenh: str, *, dung_ai: bool = False, ep: bool = True,
                log: Optional[Callable[[str], None]] = None, gio: Optional[float] = None) -> Dict[str, Any]:
    """Chạy radar cho nhóm của `kenh` nếu bảng mới nhất cũ hơn `gio` (mặc định `gio_chay_lai`). Không nhóm → {}.
    `ep=False` → chỉ bảng xếp hạng, không ép chọn (lượt một nút lẻ không ví / chạy thử)."""
    try:
        from .so_doi_thu_chung import nhom_cua  # noqa: PLC0415

        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return {}
        if _HOAN[0] > 0:
            return {"bo_qua": "lượt nghiên cứu nhóm chạy radar ở cuối"}
        gio = float(gio if gio is not None else cau_hinh(goc).get("gio_chay_lai") or 2.0)
        p = os.path.join(thu_muc(goc, nhom), TEP_MOI)
        if os.path.isfile(p) and time.time() - os.path.getmtime(p) < gio * 3600:
            return {"bo_qua": "radar vừa chạy < {0:g} giờ".format(gio)}
        return chay_an_toan(goc, nhom, dung_ai=dung_ai, ep=ep, log=log)
    except Exception:  # noqa: BLE001
        return {}


def doc_moi_nhat(goc: str, nhom: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(thu_muc(goc, nhom), TEP_MOI), {}) or {}
    return du if isinstance(du, dict) else {}


def la_dot_bien(goc: str, kenh: str, ma: str) -> Tuple[bool, str]:
    """Video `ma` có trên radar thị trường (mức ≥ 2) của nhóm `kenh` không — `(có?, lý do)`."""
    from .so_doi_thu_chung import nhom_cua  # noqa: PLC0415

    kq = doc_moi_nhat(goc, nhom_cua(goc, kenh))
    for d in kq.get("dong") or []:
        if d.get("ma") == ma:
            return d.get("muc", 0) >= 2, "×{0} kỳ vọng ở {1}h".format(_f(d.get("boi"), 1), _f(d.get("tuoi_gio")))
    return False, "không có trên radar thị trường mới nhất"


def dac_trung_cho_kenh(goc: str, kenh: str, ngay: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """`{mã: {radar_boi, radar_muc, radar_cua_minh, radar_tuoi_gio}}` cho kho đặc trưng phòng thí nghiệm của `kenh`:
    bảng radar mới nhất ≤ 36 giờ của nhóm, hoặc bảng của đúng ngày `ngay` (chạy ngược). Hỏng → {}."""
    try:
        from .so_doi_thu_chung import nhom_cua  # noqa: PLC0415

        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return {}
        if ngay:
            kq = _doc_json(os.path.join(thu_muc(goc, nhom), "radar-{0}.json".format(ngay)), {}) or {}
        else:
            p = os.path.join(thu_muc(goc, nhom), TEP_MOI)
            if not os.path.isfile(p) or time.time() - os.path.getmtime(p) > 36 * 3600:
                return {}
            kq = doc_moi_nhat(goc, nhom)
    except Exception:  # noqa: BLE001
        return {}
    ra = {}
    for d in kq.get("dong") or []:
        ra[str(d.get("ma") or "")] = {"radar_boi": d.get("boi"), "radar_muc": float(d.get("muc") or 0),
                                      "radar_cua_minh": 1.0 if d.get("gan") == kenh else 0.0,
                                      "radar_tuoi_gio": d.get("tuoi_gio")}
    return ra


# ── nạp video radar vào sổ content của kênh được gán ───────────────────────

def nap_vao_so(goc: str, kenh: str, *, log: Optional[Callable[[str], None]] = None, ghi: bool = True) -> int:
    """Dòng radar gán cho `kenh` (mức ≥ 1, chưa làm) mà `content.csv` của kênh chưa có → chép dòng nguyên văn từ sổ
    của kênh anh em (cột trung tính; `Tuyến / Kênh`, `Đã làm`, `Ghi chú` để trống). Trả số dòng thêm. Hỏng → 0."""
    try:
        from . import doi_thu_kenh as so  # noqa: PLC0415
        from .so_doi_thu_chung import nhom_cua  # noqa: PLC0415

        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return 0
        kq = doc_moi_nhat(goc, nhom)
        can = [d for d in kq.get("dong") or [] if d.get("gan") == kenh and d.get("muc", 0) >= 1
               and not d.get("da_lam_boi")][:int(cau_hinh(goc).get("nap_so_toi_da") or 20)]
        if not can:
            return 0
        cot, hang = so.doc_bang(goc, kenh)
        o = {c: i for i, c in enumerate(cot)}
        co = {so.ma_video(str(h[o[so.COT_LINK]])) for h in hang if o.get(so.COT_LINK) is not None
              and o[so.COT_LINK] < len(h)}
        thieu = [d for d in can if d["ma"] not in co]
        if not thieu:
            return 0
        them = []
        nguon_cache: Dict[str, Tuple[List[str], Dict[str, List[str]]]] = {}
        for d in thieu:
            src = next((m for m in (d.get("co_o") or {}) if m != kenh), "")
            if not src:
                continue
            if src not in nguon_cache:
                c2, h2 = so.doc_bang(goc, src)
                o2 = {c: i for i, c in enumerate(c2)}
                nguon_cache[src] = (c2, {so.ma_video(str(h[o2[so.COT_LINK]])): h for h in h2
                                         if o2.get(so.COT_LINK) is not None and o2[so.COT_LINK] < len(h)})
            c2, theo_ma = nguon_cache[src]
            h = theo_ma.get(d["ma"])
            if h is None:
                continue
            moi = [""] * len(cot)
            for i, c in enumerate(c2):
                if c in o and c not in (so.COT_TUYEN, so.COT_DA_LAM, so.COT_GHI_CHU, so.COT_CHU_DE) and i < len(h):
                    moi[o[c]] = h[i]
            if so.COT_LAN_DAU in o:
                moi[o[so.COT_LAN_DAU]] = _dt.date.today().isoformat()
            them.append(moi)
        if them and ghi:
            so.luu_bang(goc, kenh, cot, list(hang) + them)
            if log is not None:
                log("  radar: thêm {0} video đối thủ đang nổ (gán cho {1}) vào sổ content của kênh.".format(
                    len(them), kenh))
        return len(them)
    except Exception as loi:  # noqa: BLE001
        if log is not None:
            log("  radar: nạp vào sổ content hỏng ({0}) — bỏ qua.".format(str(loi)[:100]))
        return 0


# ── trực quan (8790) + bộ não ───────────────────────────────────────────────

def _trang_thai_dong(d: Dict[str, Any], hd: Dict[str, Dict[str, Any]], qd: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """`(mã trạng thái, chữ)` cho một dòng radar: ep_chon / dang_lam / da_lam / bo / theo_doi."""
    h = hd.get(d.get("ma") or "")
    if h is not None and (h.get("tham_so") or {}).get("radar_thi_truong"):
        ts = h.get("tham_so") or {}
        if h.get("trang_thai") == "mo":
            if ts.get("chon_luc"):
                return "dang_lam", "đang làm ({0}, chọn {1})".format(ts.get("kenh"), str(ts["chon_luc"])[5:16])
            return "ep_chon", "đã ép chọn cho {0} ({1}, hạn {2})".format(ts.get("kenh"), h.get("id"),
                                                                         str(ts.get("han_san_xuat") or "")[5:16])
        if h.get("trang_thai") == "xong" and not h.get("khong_tinh"):
            return "da_lam", "đã bàn giao ({0})".format(", ".join(ts.get("goi") or []) or ts.get("kenh"))
        return "bo", "bỏ: {0}".format(str(h.get("ghi_chu_cham") or h.get("trang_thai"))[:100])
    if d.get("da_lam_boi"):
        return "da_lam", d.get("ly_do_gan") or "đã làm"
    q = qd.get(d.get("ma") or "")
    if q is not None and q.get("quyet") == "bo" and q.get("vi_sao"):
        if q.get("cho"):
            return "cho", "chờ lượt sau: " + str(q["vi_sao"])[:110]
        return "bo", "bỏ vì " + str(q["vi_sao"])[:110]
    if q is not None and q.get("quyet") == "se_ep":
        return "cho", str(q.get("vi_sao") or "")[:110]
    return "theo_doi", "theo dõi" + (" — gán " + d["gan"] if d.get("gan") else "")


def truc_quan(goc: str) -> Dict[str, Any]:
    """Dữ liệu panel «Radar đột biến» (tab Phòng thí nghiệm, 8790) — mọi nhóm trên máy."""
    from .kenh import liet_ke_kenh  # noqa: PLC0415
    from .so_doi_thu_chung import doc as doc_so, nhom_cua  # noqa: PLC0415

    nhom_ds = sorted({nhom_cua(goc, k) for k in liet_ke_kenh(goc)} - {""})
    hd = _trang_thai_hanh_dong(goc)
    ra: Dict[str, Any] = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "nhom": []}
    for n in nhom_ds:
        kq = doc_moi_nhat(goc, n)
        if not kq:
            ra["nhom"].append({"nhom": n, "co": False})
            continue
        qd: Dict[str, Dict[str, Any]] = {}
        for x in (kq.get("quyet_dinh") or []):
            qd[str(x.get("ma") or "")] = x
        dong = []
        for d in (kq.get("dong") or [])[:30]:
            ma_tt, chu_tt = _trang_thai_dong(d, hd, qd)
            x = {k: d.get(k) for k in ("ma", "link", "tieu_de", "tieu_de_viet", "kenh_nguon", "view", "boi",
                                       "muc", "ten_muc", "tuoi_gio", "ky_vong", "ky_vong_nguon", "toc_do",
                                       "toc_do_gan", "tang_toc", "trong_cua_so", "cum", "vung", "ten_vung",
                                       "gan", "ly_do_gan", "trang_chu", "pool", "dai_phut", "kenh_ai", "kenh_tang")}
            x.update(trang_thai=ma_tt, trang_thai_chu=chu_tt)
            dong.append(x)
        tk = kq.get("thong_ke") or {}
        so = doc_so(goc, n)
        ra["nhom"].append({
            "nhom": n, "co": True, "luc": kq.get("luc"), "thong_ke": tk, "duong_cong": kq.get("duong_cong") or {},
            "cau_hinh": kq.get("cau_hinh") or {}, "dong": dong,
            "dem_muc": {str(m): sum(1 for d in kq.get("dong") or [] if d.get("muc") == m) for m in (1, 2, 3)},
            "ep_hom_nay": sum(1 for x in hd.values() if (x.get("tham_so") or {}).get("radar_thi_truong")
                              and str(x.get("luc") or "")[:10] == time.strftime("%Y-%m-%d")),
            "so_doi_thu": (so.get("thong_ke") or {}) if so else {}})
    return ra


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None}


def truc_quan_nho(goc: str, han: float = 300.0) -> Dict[str, Any]:
    try:
        if _NHO["du"] is None or time.time() - _NHO["luc"] > han or _NHO.get("goc") != goc:
            _NHO.update(du=truc_quan(goc), luc=time.time(), goc=goc)
        return _NHO["du"]
    except Exception as loi:  # noqa: BLE001
        return {"loi": "{0}: {1}".format(type(loi).__name__, str(loi)[:200])}


def dong_cho_nao(goc: str, bay_gio: Optional[_dt.datetime] = None, toi_da: int = 10) -> List[str]:
    """Mục (f) của chương trình bộ não: top video đối thủ đang nổ (đọc bảng radar mới nhất; không tính lại)."""
    du = truc_quan(goc)
    ch = cau_hinh(goc)
    ra: List[str] = []
    for n in du.get("nhom") or []:
        if not n.get("co"):
            ra.append("- nhóm {0}: radar chưa chạy (chạy ở lượt nghiên cứu nhóm kế tiếp)".format(n["nhom"]))
            continue
        tk = n.get("thong_ke") or {}
        ra.append("- nhóm {0} (bảng {1}): {2} video đối thủ, {3} có nền kênh → đột biến {4} · nổ {5} · siêu nổ {6}; "
                  "ép chọn radar hôm nay {7}".format(n["nhom"], str(n.get("luc") or "")[5:16], _f(tk.get("video")),
                                                     _f(tk.get("co_nen")), n["dem_muc"].get("1", 0),
                                                     n["dem_muc"].get("2", 0), n["dem_muc"].get("3", 0),
                                                     n.get("ep_hom_nay", 0)))
        for d in (n.get("dong") or [])[:toi_da]:
            ra.append("  · ×{0} {1} «{2}» {3} ({4} view, {5}h, {6}) vùng {7} → {8} [{9}]".format(
                _f(d.get("boi"), 1), d.get("ma"), str(d.get("tieu_de") or "")[:34], str(d.get("kenh_nguon") or "")[:16],
                _f(d.get("view")), _f(d.get("tuoi_gio")), d.get("ten_muc") or "", d.get("ten_vung") or d.get("vung") or "?",
                d.get("gan") or "—", d.get("trang_thai_chu") or ""))
    if ra:
        ra.append("  Luật: ≥ {0}× trong ≤ {1}h + hợp tệp + chưa ai làm → MÁY tự ép chọn ({2}/kênh/ngày, ghi công "
                  "H-RADAR). Mức nổ khác: bạn tự cân `uu-tien-nguon` (tính hạn mức ngày).".format(
                      _f(ch.get("ep_boi")), _f(ch.get("ep_tuoi_gio")), _f(ch.get("ep_moi_kenh_ngay"))))
    return ra


# ── dòng lệnh ───────────────────────────────────────────────────────────────

def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.radar_dot_bien")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p.add_argument("--nhom", default="")
    p.add_argument("--ghi", action="store_true", help="ghi bảng radar (mặc định chạy thử, không ghi gì)")
    p.add_argument("--ai", action="store_true", help="AI đọc nghĩa top video (tốn ví)")
    p.add_argument("--ep", action="store_true", help="cho phép ép chọn (cần --ghi)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(list(argv) if argv is not None else None)
    from .so_doi_thu_chung import nhom_cua  # noqa: PLC0415
    from .kenh import liet_ke_kenh  # noqa: PLC0415

    nhom = a.nhom or next((nhom_cua(a.goc, k) for k in liet_ke_kenh(a.goc) if nhom_cua(a.goc, k)), "")
    if not nhom:
        print("không có nhóm kênh nào")
        return 1
    kq = chay(a.goc, nhom, dung_ai=a.ai, ep=bool(a.ep), ghi=bool(a.ghi), log=print)
    if a.json:
        print(json.dumps(kq, ensure_ascii=False, indent=1)[:20000])
        return 0
    print("đường cong ngách (view-tại-tuổi ÷ nền):", dict(zip([int(x) for x in TAM_O], kq["duong_cong"]["ngach"])),
          "n/ô:", kq["duong_cong"]["n"], "· kênh có đường riêng:", kq["duong_cong"]["kenh_rieng"])
    for i, d in enumerate(kq["dong"][:25], 1):
        print("{0:2d}. ×{1:>6} {2} {3:>8} view {4:>5}h  {5} | kỳ vọng {6} ({7}) | vùng {8} | → {9} ({10})".format(
            i, _f(d["boi"], 1), d["ma"], _f(d["view"]), _f(d["tuoi_gio"]), d["ten_muc"], _f(d["ky_vong"]),
            d["ky_vong_nguon"], d.get("ten_vung") or d.get("vung") or "?", d.get("gan") or "—", d.get("ly_do_gan")))
    for q in kq.get("quyet_dinh") or []:
        print("  quyết: {0} {1} → {2}: {3}".format(q["ma"], q.get("gan") or "—", q["quyet"], q["vi_sao"]))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
