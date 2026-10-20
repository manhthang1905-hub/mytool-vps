"""HÀM GIÁ TRỊ ĐỀ TÀI + TIÊU ĐỀ (G2 bản 1, 20/10/2026) — đoán «độ nổ» học từ KẾT QUẢ THẬT của video đối thủ.

═══ VÌ SAO ═══ `docs/KE-HOACH-TU-HOC-KIEU-CO-VUA.md` (G2): mọi giám khảo LLM đo 20/10 gần như không dự báo (bìa −0,39,
hook 0,12, kịch bản 0,15, tiêu đề gộp 0,24 — `core/hieu_chuan`). Hàm giá trị phải HỌC TỪ SỐ: hàng chục nghìn «ván»
đối thủ đã có kết quả nằm sẵn trên đĩa (`CHANNEL/_NHOM/*/nghien-cuu/kenh-do.json` + `CHANNEL/<k>/nghien-cuu/content.csv`).
Không gọi LLM, không mạng, không tiền — chỉ numpy.

═══ NHÃN (`tinh_nhan`) ═══ Mỗi video đối thủ (bỏ trùng theo mã video, bỏ kênh ta), tuổi ≥ `TUOI_MIN` ngày lúc chụp;
nhóm = (kênh, ngày chụp):
  lv      = log(1 + lượt xem)
  tuổi    → nhóm tuổi `NHOM_TUOI`; hiệu ứng nhóm tuổi ước TRONG nhóm (hiệu ứng cố định nhóm + nhóm tuổi, lặp trung bình)
  adj     = lv − hiệu ứng nhóm tuổi
  y_no    = adj − trung vị adj của `SO_LANG_GIENG` video KHÁC cùng kênh đăng gần nhất (nhóm cần ≥ `SO_KENH_MIN` + 1
            video) = log(view / view trung vị của kênh cùng thời, cùng tuổi) — «độ nổ so chính kênh», không phải quy mô
            kênh; kênh đang lớn / đang tụt không làm lệch nhãn
  y_toc   = log((view + 1) / tuổi ngày) — tốc độ tuyệt đối (chỉ để so: lẫn quy mô kênh, đo 20/10 không chuyển được)
  nổ      = y_no ≥ log 3 (gấp 3 trung vị kênh)

═══ ĐẶC TRƯNG (`dac_trung`) ═══ chữ tiêu đề (NFKC, chữ thường) → n-gram ký tự 1–3 (tiếng Nhật không có dấu cách) băm
vào `D_BAM` ô (băm cố định, không phụ thuộc tiến trình), chuẩn 1/√số n-gram; cộng cấu trúc: độ dài, 【】, số, ？！,
「」, ｜, kiểu tiêu đề (`tu_hoc.nhan_tieu_de_regex`), vùng đề tài chiến trường (`chien_truong._cum` + vùng AI theo link),
thời lượng, thứ trong tuần, log người đăng ký (BIẾN KIỂM SOÁT — để mô hình học hiệu ứng NỘI DUNG, không học quy mô).
Mô hình nhúng câu (onnx) chưa dùng: máy chỉ IPv6 không tải được tệp mô hình từ HuggingFace (20/10).

═══ MÔ HÌNH ═══ ridge (numpy, gradient liên hợp trên ma trận thưa), λ chọn trên lát thẩm định; chia THEO THỜI GIAN:
học trên video cũ, giữ lại `TI_LE_GIU` video MỚI NHẤT để kiểm. Mô hình dùng = bản học trên phần cũ (số kiểm trung
thực); tệp `workspace/gia-tri/mo-hinh-<lúc>.npz` (không lên kho), con trỏ `hien-hanh.json`. Lần học mới KÉM bản đang
dùng trên cùng tập giữ lại → giữ bản cũ.

═══ KIỂM ═══ Spearman trên tập giữ lại, «lift» top 10% (tỉ lệ video nổ thật trong 10% điểm cao nhất ÷ tỉ lệ nền), so
mốc đơn giản (độ phổ biến vùng; chỉ độ dài tiêu đề); CHUYỂN GIAO sang video của ta (`kiem_kenh_ta`): Spearman điểm ↔
lượt xem so trung vị kênh cùng tuổi, ↔ CTR (≥ 1.000 hiển thị, √hiển thị), ↔ phân vị thước chung, và đối đầu giám khảo
tiêu đề LLM trên CÙNG tập video. Bộ chấm `gia_tri_tieu_de` / `gia_tri_de_tai` được D22 (`core/hieu_chuan`) đo hằng tuần.

═══ SỐ ĐO 20/10/2026 (bản 1) ═══ 82.838 video / 2.108 kênh; giữ lại 16.862 video đăng từ 22/09: rho 0,084, lift top
10% ×1,69 (27,5% nổ so nền 16,3%); mốc vùng 0,032, mốc độ dài −0,008. Video ta: lượt xem so trung vị kênh rho 0,20
(n 112), CTR rho_w 0,145 (n 86), phân vị thước chung 0,30 (n 86); đối đầu giám khảo LLM — CTR (n 44) mô hình 0,11 vs
LLM 0,24, phân vị (n 66) mô hình 0,20 vs LLM −0,03. CHƯA qua cổng (rho giữ lại < 0,3) → chưa nối vào nơi chọn; D22 đo
tiếp hằng tuần.

Dùng:  python -X utf8 -m core.gia_tri huan-luyen [--thu] [--goc G]    (--thu: học + in số, không ghi mô hình)
       python -X utf8 -m core.gia_tri du-doan "<tiêu đề>" [--goc G]
       python -X utf8 -m core.gia_tri kiem-ta [--goc G]                (chuyển giao sang video của ta, chỉ đọc)
"""

from __future__ import annotations

import csv
import datetime as _dt
import glob
import io
import json
import math
import os
import re
import sys
import time
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

for _bien in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # máy đang sản xuất: một luồng
    os.environ.setdefault(_bien, "1")

import numpy as np  # noqa: E402

THU_MUC = ("workspace", "gia-tri")
TEP_HIEN_HANH = "hien-hanh.json"
PHIEN_BAN = 1
TUOI_MIN = 7
SO_KENH_MIN = 5
SO_LANG_GIENG = 10
NHOM_TUOI = (7, 14, 30, 60, 120, 365)
NGUONG_NO = math.log(3.0)
D_BAM = 1 << 18
NGRAM = (1, 2, 3)
TI_LE_GIU = 0.2
TI_LE_THAM_DINH = 0.15
LAMBDA_THU = (30.0, 10.0, 3.0)          # giảm dần — lần sau khởi động từ nghiệm lần trước (hội tụ nhanh hơn)
SO_VONG_CG = 60                          # đo 20/10: xếp hạng ổn định từ ~40 vòng; mỗi vòng ~0,3 giây trên VPS
LAMBDA_CAU_TRUC = 1.0
GIU_TOI_DA = 4
#: Nhãn học. Đo 20/10 (giữ lại 16.862 video): học y_toc (tốc độ tuyệt đối, lẫn quy mô kênh) → rho với độ nổ 0,03, lift
#: top 10% ×0,67 — tệ hơn ngẫu nhiên; học y_no → rho 0,08, lift ×1,6. Chỉ học y_no.
NHAN_HOC = ("y_no",)
#: Cổng nối vào sản xuất (đề bài 20/10): held-out rho ≥ 0,3 VÀ trên video của ta rho > giám khảo LLM với n ≥ 20.
RHO_GIU_LAI_TOI_THIEU = 0.3
N_TA_TOI_THIEU = 20
KIEU_TD = ("cau_hoi", "canh_bao", "bi_mat", "doi_lap", "dac_diem_nguoi", "so_dem", "khac")
_RE_VID = re.compile(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})")


# ── tiện ích ────────────────────────────────────────────────────────────────


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(p: str, du: Any) -> None:
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with io.open(p + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def _so(x: Any) -> Optional[float]:
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(str(x).replace(",", "").strip())
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _ngay(x: Any) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(x or "").strip()[:10])
    except ValueError:
        return None


def _giay(x: Any) -> Optional[float]:
    """"10:41" / "1:02:33" / 641 → giây."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x) if x > 0 else None
    p = str(x or "").strip().split(":")
    try:
        so = [int(a) for a in p]
    except ValueError:
        return None
    g = 0
    for a in so:
        g = g * 60 + a
    return float(g) if g > 0 else None


def thu_muc(goc: str) -> str:
    return os.path.join(goc, *THU_MUC)


def hang(x: np.ndarray) -> np.ndarray:
    """Hạng trung bình khi hoà (0..n−1)."""
    x = np.asarray(x, dtype=np.float64)
    thu = np.argsort(x, kind="mergesort")
    r = np.empty(len(x), dtype=np.float64)
    r[thu] = np.arange(len(x), dtype=np.float64)
    _u, inv, dem = np.unique(x, return_inverse=True, return_counts=True)
    if len(_u) < len(x):
        tong = np.bincount(inv, weights=r)
        r = (tong / dem)[inv]
    return r


def spearman(a: Sequence[float], b: Sequence[float], w: Optional[Sequence[float]] = None) -> Optional[float]:
    """Spearman (có trọng số tuỳ chọn: Pearson có trọng số trên hạng). < 4 cặp hoặc một phía không đổi → None."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if len(a) < 4 or len(a) != len(b):
        return None
    ra, rb = hang(a), hang(b)
    ww = np.ones(len(a)) if w is None else np.clip(np.asarray(w, dtype=np.float64), 0, None)
    if ww.sum() <= 0:
        return None
    ma, mb = np.average(ra, weights=ww), np.average(rb, weights=ww)
    sa = math.sqrt(float(np.sum(ww * (ra - ma) ** 2)))
    sb = math.sqrt(float(np.sum(ww * (rb - mb) ** 2)))
    if sa <= 1e-12 or sb <= 1e-12:
        return None
    return round(float(np.sum(ww * (ra - ma) * (rb - mb)) / (sa * sb)), 3)


def lift_top(y: np.ndarray, p: np.ndarray, ti_le: float = 0.1, nguong: float = NGUONG_NO) -> Dict[str, Any]:
    """Tỉ lệ video nổ thật (y ≥ nguong) trong `ti_le` điểm dự đoán cao nhất, so tỉ lệ nền."""
    y, p = np.asarray(y), np.asarray(p)
    if len(y) < 10:
        return {"n": int(len(y)), "nen": None, "top": None, "lift": None}
    k = max(1, int(round(len(y) * ti_le)))
    top = np.argsort(-p, kind="mergesort")[:k]
    nen = float(np.mean(y >= nguong))
    t = float(np.mean(y[top] >= nguong))
    return {"n": int(len(y)), "nen": round(nen, 4), "top": round(t, 4), "lift": round(t / nen, 2) if nen > 0 else None}


# ── 1) Dữ liệu ──────────────────────────────────────────────────────────────


def ten_kenh_ta(goc: str) -> set:
    """Tên hiển thị các kênh ta (để bỏ khỏi dữ liệu đối thủ)."""
    ra = set()
    for p in glob.glob(os.path.join(goc, "CHANNEL", "*", "thiet-lap", "ho-so.json")):
        t = (_doc_json(p) or {}).get("ten")
        if t:
            ra.add(str(t))
    for p in glob.glob(os.path.join(goc, "CHANNEL", "*", "kenh.yaml")):
        try:
            with io.open(p, encoding="utf-8") as tep:
                for d in tep:
                    if d.startswith("ten:"):
                        t = d.split(":", 1)[1].strip().strip('"').split(" — ")[0].strip()
                        if t:
                            ra.add(t)
                        break
        except OSError:
            continue
    return ra


def doc_video(goc: str, bo_ten: Optional[set] = None) -> List[Dict[str, Any]]:
    """Video đối thủ bỏ trùng theo mã: `{vid, kenh, ten_kenh, tieu_de, dang, chup, view, dai, subs, nguon}`.
    Ưu tiên `kenh-do.json` (có NGÀY CHỤP thật, bản mới nhất); `content.csv` chỉ thêm video chưa có (ngày chụp = ngày
    sửa tệp — xấp xỉ)."""
    bo_ten = ten_kenh_ta(goc) if bo_ten is None else bo_ten
    ra: Dict[str, Dict[str, Any]] = {}
    ten_id: Dict[str, str] = {}
    subs_ten: Dict[str, float] = {}
    for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", "_NHOM", "*", "nghien-cuu", "kenh-do.json"))):
        du = _doc_json(p)
        if not isinstance(du, dict):
            continue
        for v in du.values():
            if not isinstance(v, dict):
                continue
            ch = v.get("ch") or {}
            chup = _ngay(v.get("ngay"))
            ten = str(ch.get("name") or "")
            if not chup or not ten or ten in bo_ten:
                continue
            cid = str(ch.get("channel_id") or ("ten:" + ten))
            subs = _so(ch.get("subscribers"))
            ten_id[ten] = cid
            if subs is not None:
                subs_ten[ten] = subs
            for x in ch.get("videos") or []:
                if not isinstance(x, dict):
                    continue
                vid, dang, view = str(x.get("video_id") or ""), _ngay(x.get("upload_date")), _so(x.get("views"))
                td = str(x.get("title") or "").strip()
                if not vid or not dang or view is None or not td:
                    continue
                cu = ra.get(vid)
                if cu and cu["chup"] >= chup:
                    continue
                ra[vid] = {"vid": vid, "kenh": cid, "ten_kenh": ten, "tieu_de": td, "dang": dang, "chup": chup,
                           "view": view, "dai": _giay(x.get("duration_s")), "subs": subs, "nguon": "kenh-do"}
    for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", "*", "nghien-cuu", "content.csv"))):
        if os.path.basename(os.path.dirname(os.path.dirname(p))).startswith("_"):
            continue
        try:
            chup = _dt.date.fromtimestamp(os.path.getmtime(p))
            with io.open(p, encoding="utf-8-sig", errors="replace", newline="") as tep:
                hang_ = list(csv.DictReader(tep))
        except OSError:
            continue
        for r in hang_:
            m = _RE_VID.search(str(r.get("Link video") or ""))
            ten = str(r.get("Kênh") or "")
            if not m or not ten or ten in bo_ten:
                continue
            vid = m.group(1)
            cu = ra.get(vid)
            if cu and cu["nguon"] == "kenh-do":
                continue
            dang, view = _ngay(r.get("Ngày đăng")), _so(r.get("View"))
            td = str(r.get("Tiêu đề video") or "").strip()
            if not dang or view is None or not td:
                continue
            if cu and cu["view"] >= view:
                continue
            ra[vid] = {"vid": vid, "kenh": ten_id.get(ten, "ten:" + ten), "ten_kenh": ten, "tieu_de": td, "dang": dang,
                       "chup": chup, "view": view, "dai": _giay(r.get("Thời lượng")), "subs": subs_ten.get(ten),
                       "nguon": "content"}
    return list(ra.values())


def _nen_lang_gieng(v: np.ndarray, k: int = SO_LANG_GIENG) -> np.ndarray:
    """`v` đã xếp theo ngày đăng: nền của mỗi video = trung vị `k` video KHÁC đăng gần nó nhất (nửa trước, nửa sau;
    sát mép thì lấy thêm phía còn lại)."""
    n = len(v)
    ra = np.empty(n)
    for p in range(n):
        lo = max(0, p - k // 2)
        hi = min(n, lo + k + 1)
        lo = max(0, hi - k - 1)
        ra[p] = float(np.median(np.concatenate([v[lo:p], v[p + 1:hi]])))
    return ra


def tinh_nhan(ds: Sequence[Dict[str, Any]], tuoi_min: int = TUOI_MIN, so_kenh_min: int = SO_KENH_MIN
              ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Gắn `tuoi`, `y_no`, `y_toc` (xem đầu tệp). Nhóm = (kênh, ngày chụp): mọi video một nhóm chụp cùng lúc nên so
    được với nhau. Nền = trung vị `SO_LANG_GIENG` video cùng kênh đăng GẦN nhất (kênh đang lớn / đang tụt không làm
    lệch nhãn), sau khi trừ hiệu ứng nhóm tuổi (ước trong nhóm). Trả (video đủ điều kiện, thông tin)."""
    co = [x for x in ds if (x["chup"] - x["dang"]).days >= tuoi_min]
    if not co:
        return [], {"n": 0}
    tuoi = np.array([(x["chup"] - x["dang"]).days for x in co], dtype=np.float64)
    lv = np.log1p(np.array([max(0.0, x["view"]) for x in co], dtype=np.float64))
    ma_nhom: Dict[Tuple[str, Any], int] = {}
    k = np.array([ma_nhom.setdefault((x["kenh"], x["chup"]), len(ma_nhom)) for x in co])
    b = np.searchsorted(np.array(NHOM_TUOI[1:]), tuoi, side="right")
    nb, nk = len(NHOM_TUOI), len(ma_nhom)
    dem_k = np.bincount(k, minlength=nk).astype(np.float64)
    dem_b = np.maximum(np.bincount(b, minlength=nb), 1).astype(np.float64)
    a = np.zeros(nb)
    for _ in range(25):
        c = np.bincount(k, weights=lv - a[b], minlength=nk) / np.maximum(dem_k, 1)
        a = np.bincount(b, weights=lv - c[k], minlength=nb) / dem_b
        a -= a[0]
    adj = lv - a[b]
    nen = np.full(len(co), np.nan)
    thu = np.lexsort((np.array([x["dang"].toordinal() for x in co]), k))
    ranh = np.flatnonzero(np.diff(k[thu])) + 1
    for nhom in np.split(thu, ranh):
        if len(nhom) >= so_kenh_min + 1:
            nen[nhom] = _nen_lang_gieng(adj[nhom])
    ra = []
    for i, x in enumerate(co):
        if not math.isfinite(nen[i]):
            continue
        ra.append(dict(x, tuoi=float(tuoi[i]), y_no=float(adj[i] - nen[i]),
                       y_toc=float(math.log((max(0.0, x["view"]) + 1.0) / tuoi[i]))))
    return ra, {"n_vao": len(ds), "n_du_tuoi": len(co), "n": len(ra), "n_kenh": int(len({x["kenh"] for x in ra})),
                "hieu_ung_tuoi": {str(NHOM_TUOI[i]): round(float(a[i]), 3) for i in range(nb)},
                "ti_le_no": round(float(np.mean([x["y_no"] >= NGUONG_NO for x in ra])), 4) if ra else None}


# ── 2) Đặc trưng ────────────────────────────────────────────────────────────


def chuan_chu(t: Any) -> str:
    return unicodedata.normalize("NFKC", str(t or "")).lower().strip()


_NHAN_TD: List[Optional[Callable[[str], str]]] = []


def _nhan_td(t: str) -> str:
    if not _NHAN_TD:
        try:
            from core.tu_hoc import nhan_tieu_de_regex  # noqa: PLC0415
            _NHAN_TD.append(nhan_tieu_de_regex)
        except Exception:  # noqa: BLE001
            _NHAN_TD.append(None)
    f = _NHAN_TD[0]
    return f(t) if f else "khac"


def bam_ngram(chu: Sequence[str], d: int = D_BAM, ngram: Sequence[int] = NGRAM
              ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """n-gram ký tự của từng chữ (đã chuẩn) → (hàng, cột, giá trị) thưa (int64 — bincount không phải đổi kiểu);
    giá trị 1/√(số n-gram của dòng).
    Băm cố định (mã điểm Unicode, nhân/trộn uint64) — cùng chữ cùng ô ở mọi máy, mọi tiến trình."""
    n = len(chu)
    if n == 0:
        z = np.zeros(0, dtype=np.int64)
        return z, z.copy(), np.zeros(0)
    s = "".join(t.replace("\x00", " ") + "\x00" for t in chu)
    a = np.frombuffer(s.encode("utf-32-le"), dtype=np.uint32).astype(np.uint64)
    tach = a == 0
    dong = np.concatenate(([0], np.cumsum(tach)[:-1])).astype(np.int64)
    L = len(a)
    hang_: List[np.ndarray] = []
    cot: List[np.ndarray] = []
    with np.errstate(over="ignore"):
        for g in ngram:
            if L < g:
                continue
            p = np.arange(L - g + 1)
            ok = ~tach[p]
            h = a[p].copy()
            for j in range(1, g):
                ok &= ~tach[p + j]
                h = h * np.uint64(1000003) + a[p + j]
            h = h + np.uint64(g) * np.uint64(0x9E3779B97F4A7C15)
            h ^= h >> np.uint64(31)
            h *= np.uint64(0xBF58476D1CE4E5B9)
            h ^= h >> np.uint64(29)
            hang_.append(dong[p][ok])
            cot.append((h[ok] % np.uint64(d)).astype(np.int64))
    if not hang_:
        z = np.zeros(0, dtype=np.int64)
        return z, z.copy(), np.zeros(0)
    r, c = np.concatenate(hang_), np.concatenate(cot)      # n-gram lặp trong dòng = đếm (tf), không cần bỏ trùng
    dem = np.bincount(r, minlength=n).astype(np.float64)
    v = (1.0 / np.sqrt(np.maximum(dem, 1)))[r]
    return r, c, v


def ten_cau_truc(vung: Sequence[str]) -> List[str]:
    return (["do_dai", "do_dai_2", "ngoac", "ngoac_dau", "co_so", "so_nhom", "hoi", "cam", "trich", "ke_doc"]
            + ["kieu:" + x for x in KIEU_TD] + ["vung:" + x for x in vung]
            + ["dai_log", "dai_thieu", "dai<8", "dai8-15", "dai15-30", "dai30-60", "dai60+"]
            + ["thu:%d" % i for i in range(7)] + ["thu_thieu", "subs_log", "subs_thieu"])


_RE_SO_NHOM = re.compile(r"\d+")


def cau_truc(x: Dict[str, Any], vung_ds: Sequence[str]) -> List[float]:
    """Một dòng đặc trưng cấu trúc (thứ tự = `ten_cau_truc(vung_ds)`). `x`: tieu_de, [vung, dai, dang, subs]."""
    t = unicodedata.normalize("NFKC", str(x.get("tieu_de") or ""))
    n = len(t)
    kieu = _nhan_td(t)
    vg = x.get("vung")
    dai = _so(x.get("dai"))
    dang = x.get("dang")
    subs = _so(x.get("subs"))
    so = _RE_SO_NHOM.findall(t)
    ra = [n / 50.0, (n / 50.0) ** 2, float(t.count("【")), float(t.startswith("【")), float(bool(so)),
          float(min(3, len(so))), float("?" in t), float("!" in t), float(("「" in t) or ("『" in t)),
          float(t.count("|") + t.count("│"))]
    ra += [float(kieu == k) for k in KIEU_TD]
    ra += [float(vg == v) for v in vung_ds]
    if dai and dai > 0:
        ph = dai / 60.0
        ra += [math.log(ph), 0.0, float(ph < 8), float(8 <= ph < 15), float(15 <= ph < 30), float(30 <= ph < 60),
               float(ph >= 60)]
    else:
        ra += [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    if isinstance(dang, _dt.date):
        ra += [float(dang.weekday() == i) for i in range(7)] + [0.0]
    else:
        ra += [0.0] * 7 + [1.0]
    ra += [math.log10(subs + 1.0), 0.0] if subs is not None and subs >= 0 else [0.0, 1.0]
    return ra


_DEM_VUNG: Dict[str, Any] = {}


def ham_vung(goc: str) -> Optional[Callable[[str, str], str]]:
    """Bộ gán vùng đề tài của chiến trường (`core/chien_truong`: cụm từ khoá gộp mọi kênh ta, «khac» → vùng AI theo
    link nếu có). Gốc khác gốc của chien_truong (test) hoặc lỗi → None (không dùng đặc trưng vùng)."""
    key = os.path.realpath(goc)
    if key in _DEM_VUNG:
        return _DEM_VUNG[key]
    f = None
    try:
        from core import chien_truong as ct  # noqa: PLC0415
        if os.path.realpath(ct.GOC) == key:
            v7, ch, _ten = ct._bo_cum(ct._cac_kenh())  # noqa: SLF001
            try:
                from core import chien_truong_ai  # noqa: PLC0415
                ai = chien_truong_ai.doc().get("video") or {}
            except Exception:  # noqa: BLE001
                ai = {}

            def f(td: str, link: str = "") -> str:
                m = ct._cum(v7, ch, td)  # noqa: SLF001
                if m == ct.KHAC and link and link in ai and ai[link] != "ngoai-ngach":
                    m = ai[link]
                return m
    except Exception:  # noqa: BLE001
        f = None
    _DEM_VUNG[key] = f
    return f


class MaTran:
    """X = [thưa (băm n-gram) | đặc (cấu trúc, đã chuẩn hoá)] — nhân X·w và Xᵀ·r bằng bincount (không cần scipy)."""

    def __init__(self, r: np.ndarray, c: np.ndarray, v: np.ndarray, n: int, d: int, dac: np.ndarray):
        self.r, self.c, self.v, self.n, self.d, self.dac = r, c, v.astype(np.float64), n, d, dac

    @property
    def so_cot(self) -> int:
        return self.d + self.dac.shape[1]

    def nhan(self, w: np.ndarray) -> np.ndarray:
        ra = np.bincount(self.r, weights=self.v * w[self.c], minlength=self.n) if len(self.r) else np.zeros(self.n)
        return ra + self.dac @ w[self.d:]

    def nhan_t(self, y: np.ndarray) -> np.ndarray:
        s = np.bincount(self.c, weights=self.v * y[self.r], minlength=self.d) if len(self.r) else np.zeros(self.d)
        return np.concatenate([s, self.dac.T @ y])

    def con(self, idx: np.ndarray) -> "MaTran":
        """Ma trận con theo các dòng `idx` (đánh lại số dòng 0..len−1)."""
        moi = np.full(self.n, -1, dtype=np.int64)
        moi[idx] = np.arange(len(idx))
        m = moi[self.r] >= 0
        return MaTran(moi[self.r[m]], self.c[m], self.v[m], len(idx), self.d, self.dac[idx])


def ridge(X: MaTran, y: np.ndarray, lam: np.ndarray, w0: Optional[np.ndarray] = None, so_vong: int = SO_VONG_CG,
          tol: float = 1e-4) -> np.ndarray:
    """(XᵀX + diag λ) w = Xᵀy — gradient liên hợp."""
    b = X.nhan_t(y)
    w = np.zeros(X.so_cot) if w0 is None else w0.copy()
    r = b - (X.nhan_t(X.nhan(w)) + lam * w)
    p = r.copy()
    rs = float(r @ r)
    chuan_b = math.sqrt(float(b @ b)) or 1.0
    for _ in range(so_vong):
        if math.sqrt(rs) <= tol * chuan_b:
            break
        Ap = X.nhan_t(X.nhan(p)) + lam * p
        alpha = rs / float(p @ Ap)
        w += alpha * p
        r -= alpha * Ap
        rs_moi = float(r @ r)
        p = r + (rs_moi / rs) * p
        rs = rs_moi
    return w


def dac_tho(ds: Sequence[Dict[str, Any]], vung_ds: Sequence[str]) -> np.ndarray:
    """Cột cấu trúc CHƯA chuẩn hoá (n × len(ten_cau_truc))."""
    return np.array([cau_truc(x, vung_ds) for x in ds], dtype=np.float64).reshape(len(ds), len(ten_cau_truc(vung_ds)))


def ma_tran(ds: Sequence[Dict[str, Any]], tho: np.ndarray, tb: np.ndarray, lc: np.ndarray, d: int = D_BAM) -> MaTran:
    """Ma trận đặc trưng: n-gram băm + cấu trúc chuẩn hoá (tb, lc) + cột hằng số 1 cuối."""
    r, c, v = bam_ngram([chuan_chu(x.get("tieu_de")) for x in ds], d)
    dac = np.hstack([(tho - tb) / lc, np.ones((len(ds), 1))])
    return MaTran(r, c, v, len(ds), d, dac)


def chuan_hoa(tho: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    tb = tho.mean(axis=0) if len(tho) else np.zeros(tho.shape[1])
    lc = tho.std(axis=0) if len(tho) else np.ones(tho.shape[1])
    return tb, np.where(lc > 1e-9, lc, 1.0)


def _lam_vec(X: MaTran, lam_thua: float) -> np.ndarray:
    lam = np.full(X.so_cot, float(lam_thua))
    lam[X.d:] = LAMBDA_CAU_TRUC
    lam[-1] = 1e-6
    return lam


# ── 3) Học + kiểm ───────────────────────────────────────────────────────────


def chia_thoi_gian(ds: Sequence[Dict[str, Any]], ti_le: float = TI_LE_GIU) -> Tuple[np.ndarray, np.ndarray, str]:
    """(chỉ số học, chỉ số giữ lại, mốc ngày): giữ lại = video đăng MỚI NHẤT (~`ti_le`)."""
    dang = np.array([x["dang"].toordinal() for x in ds])
    if len(ds) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), ""
    moc = np.quantile(dang, 1.0 - ti_le)
    hoc, giu = np.flatnonzero(dang < moc), np.flatnonzero(dang >= moc)
    return hoc, giu, _dt.date.fromordinal(int(moc)).isoformat()


def _do(y: np.ndarray, p: np.ndarray) -> Dict[str, Any]:
    return {"rho": spearman(p, y), "lift_10": lift_top(y, p)}


def moc_don_gian(ds: Sequence[Dict[str, Any]], hoc: np.ndarray, giu: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """Mốc so sánh: (1) độ phổ biến vùng = trung bình y của vùng trên tập học; (2) chỉ độ dài tiêu đề (ridge 2 biến)."""
    vung = [str(x.get("vung") or "khac") for x in ds]
    tong: Dict[str, List[float]] = {}
    for i in hoc:
        tong.setdefault(vung[i], []).append(float(y[i]))
    tb_chung = float(np.mean(y[hoc])) if len(hoc) else 0.0
    p_vung = np.array([float(np.mean(tong[vung[i]])) if vung[i] in tong else tb_chung for i in giu])
    L = np.array([len(unicodedata.normalize("NFKC", str(x.get("tieu_de") or ""))) / 50.0 for x in ds])
    A = np.stack([np.ones(len(ds)), L, L ** 2], axis=1)
    he = np.linalg.lstsq(A[hoc], y[hoc], rcond=None)[0] if len(hoc) >= 3 else np.zeros(3)
    return {"vung": _do(y[giu], p_vung), "do_dai": _do(y[giu], A[giu] @ he)}


def huan_luyen_mo_hinh(ds: Sequence[Dict[str, Any]], ten_y: str = "y_no", lam_thu: Sequence[float] = LAMBDA_THU,
                       d: int = D_BAM, in_ra: Callable[[str], None] = lambda *_a: None) -> Dict[str, Any]:
    """Học ridge trên phần CŨ, chọn λ trên lát thẩm định (cuối phần cũ), kiểm trên phần giữ lại (MỚI). Trả mô hình
    (trọng số + chuẩn hoá + từ điển vùng) và số kiểm."""
    t0 = time.time()
    ds = list(ds)
    y = np.array([x[ten_y] for x in ds], dtype=np.float64)
    y_no = np.array([x["y_no"] for x in ds], dtype=np.float64)
    hoc, giu, moc = chia_thoi_gian(ds)
    vung_ds = sorted({str(ds[i].get("vung")) for i in hoc if ds[i].get("vung")})
    tho = dac_tho(ds, vung_ds)
    tb, lc = chuan_hoa(tho[hoc])          # chuẩn hoá theo tập học
    X_all = ma_tran(ds, tho, tb, lc, d)
    # lát thẩm định trong phần học
    th = hoc[np.argsort([ds[i]["dang"].toordinal() for i in hoc], kind="mergesort")]
    cat = int(len(th) * (1 - TI_LE_THAM_DINH))
    h2, td = th[:cat], th[cat:]
    Xh2, Xtd = X_all.con(h2), X_all.con(td)
    tot, w = None, None
    thu_lam = []
    for lam in lam_thu:
        w = ridge(Xh2, y[h2], _lam_vec(Xh2, lam), w0=w)
        rho = spearman(Xtd.nhan(w), y[td]) or -1.0
        thu_lam.append({"lam": lam, "rho_tham_dinh": rho})
        in_ra("  λ={0:<6} rho thẩm định {1} · {2:.0f}s".format(lam, rho, time.time() - t0))
        if tot is None or rho > tot[1]:
            tot = (lam, rho, w)
    lam = tot[0] if tot else LAMBDA_THU[0]
    Xh = X_all.con(hoc)
    w = ridge(Xh, y[hoc], _lam_vec(Xh, lam), w0=tot[2] if tot else None)
    Xg = X_all.con(giu)
    p = Xg.nhan(w)
    kq = {"n_hoc": int(len(hoc)), "n_giu": int(len(giu)), "moc_giu": moc, "lam": lam, "thu_lam": thu_lam,
          "rho_giu": spearman(p, y[giu]), "rho_giu_y_no": spearman(p, y_no[giu]), "lift_10": lift_top(y_no[giu], p),
          "giay": round(time.time() - t0, 1)}
    return {"w": w.astype(np.float32), "tb": tb, "lc": lc, "vung": vung_ds, "d": d, "ngram": list(NGRAM),
            "nhan": ten_y, "kiem": kq, "moc_du_lieu": moc, "p_giu": p, "giu": giu}


def du_doan_mh(mh: Dict[str, Any], ds: Sequence[Dict[str, Any]]) -> np.ndarray:
    """Điểm của mô hình cho các dòng `{tieu_de, [vung, dai, dang, subs]}` (log tỉ lệ so trung vị kênh)."""
    if not ds:
        return np.zeros(0)
    X = ma_tran(ds, dac_tho(ds, mh["vung"]), np.asarray(mh["tb"]), np.asarray(mh["lc"]), int(mh["d"]))
    return X.nhan(np.asarray(mh["w"], dtype=np.float64))


# ── 4) Lưu / nạp ────────────────────────────────────────────────────────────


def duong_hien_hanh(goc: str) -> str:
    return os.path.join(thu_muc(goc), TEP_HIEN_HANH)


def luu(goc: str, mh: Dict[str, Any], meta: Dict[str, Any]) -> str:
    os.makedirs(thu_muc(goc), exist_ok=True)
    ten = "mo-hinh-{0}.npz".format(time.strftime("%Y%m%d-%H%M%S"))
    p = os.path.join(thu_muc(goc), ten)
    with open(p + ".tmp", "wb") as tep:
        np.savez_compressed(tep, w=np.asarray(mh["w"], dtype=np.float32), tb=np.asarray(mh["tb"]),
                            lc=np.asarray(mh["lc"]), meta=np.array(json.dumps(
                                {"vung": mh["vung"], "d": mh["d"], "ngram": mh["ngram"], "nhan": mh["nhan"],
                                 "moc_du_lieu": mh["moc_du_lieu"], "phien_ban": PHIEN_BAN}, ensure_ascii=False)))
    os.replace(p + ".tmp", p)
    _ghi_json(duong_hien_hanh(goc), dict(meta, tep=ten, luc=time.strftime("%Y-%m-%d %H:%M:%S"), phien_ban=PHIEN_BAN))
    ds = sorted(glob.glob(os.path.join(thu_muc(goc), "mo-hinh-*.npz")))
    for cu in ds[:-GIU_TOI_DA]:
        try:
            os.remove(cu)
        except OSError:
            pass
    return p


_DEM_MH: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}


def nap(goc: str) -> Optional[Dict[str, Any]]:
    """Mô hình đang dùng (nhớ đệm theo thời điểm sửa con trỏ). Không có / hỏng → None."""
    p = duong_hien_hanh(goc)
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return None
    cu = _DEM_MH.get(p)
    if cu and cu[0] == mt:
        return cu[1]
    mh = None
    try:
        hh = _doc_json(p) or {}
        with np.load(os.path.join(thu_muc(goc), str(hh.get("tep") or "")), allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            mh = {"w": z["w"].astype(np.float64), "tb": z["tb"], "lc": z["lc"], "vung": meta["vung"], "d": int(meta["d"]),
                  "ngram": meta.get("ngram"), "nhan": meta.get("nhan"), "moc_du_lieu": meta.get("moc_du_lieu"),
                  "hien_hanh": hh}
    except Exception:  # noqa: BLE001
        mh = None
    _DEM_MH[p] = (mt, mh)
    return mh


def du_doan(goc: str, tieu_de: str, *, dai_giay: Optional[float] = None, subs: Optional[float] = None,
            ngay: Optional[_dt.date] = None, link: str = "", mh: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """Điểm giá trị của MỘT tiêu đề/đề tài: log(view dự đoán ÷ view trung vị của kênh cùng tuổi) — so sánh được giữa
    các ứng viên của cùng kênh (0 = như trung vị, log 3 ≈ 1,1 = nổ). Chưa có mô hình → None. Không bao giờ ném lỗi."""
    ra = du_doan_nhieu(goc, [tieu_de], dai_giay=dai_giay, subs=subs, ngay=ngay, link=[link], mh=mh)
    return ra[0] if ra else None


def du_doan_nhieu(goc: str, tieu_de: Sequence[str], *, dai_giay: Optional[float] = None, subs: Optional[float] = None,
                  ngay: Optional[_dt.date] = None, link: Optional[Sequence[str]] = None,
                  mh: Optional[Dict[str, Any]] = None) -> List[Optional[float]]:
    try:
        mh = mh or nap(goc)
        if mh is None or not tieu_de:
            return [None] * len(tieu_de or [])
        fv = ham_vung(goc)
        ds = []
        for i, t in enumerate(tieu_de):
            lk = (link[i] if link and i < len(link) else "") or ""
            ds.append({"tieu_de": str(t or ""), "vung": fv(str(t or ""), lk) if fv else None, "dai": dai_giay,
                       "dang": ngay, "subs": subs})
        return [round(float(x), 4) for x in du_doan_mh(mh, ds)]
    except Exception:  # noqa: BLE001 — hàm giá trị hỏng không bao giờ làm hỏng nơi chọn
        return [None] * len(tieu_de or [])


# ── 5) Chuyển giao sang video của ta ────────────────────────────────────────


def _bang_ta(goc: str, kenh: str, bay: _dt.datetime) -> List[Dict[str, Any]]:
    """Video của ta ≥ 48 giờ (bảng Studio mới nhất, đã lọc video đời trước): tiêu đề, lượt xem, tuổi giờ, hiển thị, CTR."""
    p = os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv")
    try:
        with io.open(p, encoding="utf-8-sig") as tep:
            hang_ = list(csv.DictReader(tep))
    except OSError:
        return []
    try:
        from core.chi_so_ytb import loc_video as _loc  # noqa: PLC0415
        hang_ = _loc.loc_hang_bang(_loc.moc_cua_thu_muc(os.path.dirname(os.path.dirname(p))), hang_)
    except Exception:  # noqa: BLE001
        pass
    from core.bia_du_lieu import _tuoi  # noqa: PLC0415
    ra, thay = [], set()
    for d in hang_:
        vid = str(d.get("Mã video") or "").strip()
        tuoi = _tuoi(d, bay)
        v = _so(str(d.get("Lượt xem") or "").replace("%", ""))
        if not vid or vid in thay or tuoi is None or tuoi < 48 or v is None:
            continue
        thay.add(vid)
        ra.append({"kenh": kenh, "vid": vid, "tieu_de": str(d.get("Tiêu đề") or ""), "view": v, "tuoi_gio": tuoi,
                   "imp": _so(d.get("Lượt hiển thị")) or 0.0, "ctr": _so(str(d.get("Tỷ lệ bấm") or "").replace("%", "")),
                   "dai": _giay(d.get("Dài")), "dang": _ngay(d.get("Ngày đăng"))})
    return ra


def _do_no_ta(ds: List[Dict[str, Any]]) -> None:
    """Gắn `y_no` cho video của ta: log view − β·log tuổi (β gộp trong kênh) − trung vị của chính kênh."""
    if len(ds) < 4:
        return
    lv = np.log1p(np.array([x["view"] for x in ds]))
    la = np.log(np.array([x["tuoi_gio"] for x in ds]))
    k = np.array([x["kenh"] for x in ds])
    lv_c, la_c = lv.copy(), la.copy()
    for kk in set(k.tolist()):
        m = k == kk
        lv_c[m] -= lv[m].mean()
        la_c[m] -= la[m].mean()
    beta = float(la_c @ lv_c / (la_c @ la_c)) if float(la_c @ la_c) > 1e-9 else 0.0
    adj = lv - beta * la
    for kk in set(k.tolist()):
        m = np.flatnonzero(k == kk)
        tv = float(np.median(adj[m]))
        for i in m:
            ds[i]["y_no"] = float(adj[i] - tv)


def kiem_kenh_ta(goc: str, mh: Dict[str, Any], bay: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Điểm mô hình ↔ kết quả THẬT của video ta: (1) lượt xem so trung vị kênh cùng tuổi; (2) CTR ÷ trung vị kênh
    (≥ 1.000 hiển thị, trọng số √hiển thị); (3) phân vị thước chung; (4) ĐỐI ĐẦU giám khảo tiêu đề LLM trên CÙNG tập
    (sổ hiệu chuẩn: tiêu đề được chọn, CTR trước sửa) — cùng công thức D22."""
    bay = bay or _dt.datetime.now()
    from core import hieu_chuan as hc  # noqa: PLC0415
    kenh_ds = hc.kenh_hoc(goc)
    ds: List[Dict[str, Any]] = []
    for k in kenh_ds:
        ds += _bang_ta(goc, k, bay)
    _do_no_ta(ds)
    diem = du_doan_mh(mh, [dict(x, vung=(ham_vung(goc) or (lambda *_a: None))(x["tieu_de"], ""), subs=None)
                           for x in ds]) if ds else np.zeros(0)
    for x, p in zip(ds, diem):
        x["diem"] = float(p)
    ra: Dict[str, Any] = {"kenh": kenh_ds, "n_video": len(ds)}
    co = [x for x in ds if "y_no" in x]
    ra["view"] = {"n": len(co), "rho": spearman([x["diem"] for x in co], [x["y_no"] for x in co])}
    tv_ctr = {k: float(np.median([x["ctr"] for x in ds if x["kenh"] == k and x["ctr"] is not None and x["imp"] >= 1000]
                                 or [float("nan")])) for k in kenh_ds}
    c = [x for x in ds if x["ctr"] is not None and x["imp"] >= 1000 and math.isfinite(tv_ctr.get(x["kenh"], math.nan))
         and tv_ctr[x["kenh"]] > 0]
    ra["ctr"] = {"n": len(c), "rho": spearman([x["diem"] for x in c], [x["ctr"] / tv_ctr[x["kenh"]] for x in c]),
                 "rho_w": spearman([x["diem"] for x in c], [x["ctr"] / tv_ctr[x["kenh"]] for x in c],
                                   [math.sqrt(x["imp"]) for x in c])}
    # (3)(4): hồ sơ video + sổ hiệu chuẩn
    kq = {k: hc.ket_qua_kenh(goc, k, bay, giu=False) for k in kenh_ds}
    pv, doi, doi_pv = [], [], []
    fv = ham_vung(goc) or (lambda *_a: None)
    chuan = {k: {"ctr": hc._tv(x.get("ctr") for x in (kq.get(k) or {}).values())} for k in kenh_ds}  # noqa: SLF001
    for k in kenh_ds:
        for ma, hs in hc.ho_so_kenh(goc, k).items():
            r = (kq.get(k) or {}).get(ma) or {}
            td = str(hs.get("tieu_de") or "")
            if not td:
                continue
            dai = _so(hs.get("thoi_luong_giay"))
            p = float(du_doan_mh(mh, [{"tieu_de": td, "vung": fv(td, ""), "dai": dai}])[0])
            if r.get("pv") is not None:
                pv.append((p, float(r["pv"])))
            tc = hs.get("tieu_de_cham") if isinstance(hs.get("tieu_de_cham"), dict) else {}
            if not (isinstance(tc.get("chon"), int) and isinstance(tc.get("diem"), dict)):
                continue
            g = _so(tc["diem"].get(chr(65 + tc["chon"])))
            if g is None:
                continue
            uv = tc.get("ung_vien") or []
            td_chon = str((uv[tc["chon"]] or {}).get("tieu_de") or td) if 0 <= tc["chon"] < len(uv) else td
            p2 = p if td_chon == td else float(du_doan_mh(mh, [{"tieu_de": td_chon, "vung": fv(td_chon, ""), "dai": dai}])[0])
            if r.get("ctr") is not None and chuan[k]["ctr"]:
                doi.append((g, p2, float(r["ctr"]) / float(chuan[k]["ctr"]), math.sqrt(float(r.get("imp") or 0))))
            if r.get("pv") is not None:
                doi_pv.append((g, p2, float(r["pv"])))
    ra["pv"] = {"n": len(pv), "rho": spearman([a for a, _b in pv], [b for _a, b in pv])}
    ra["doi_dau"] = {"n": len(doi),
                     "llm_rho_w": spearman([a[0] for a in doi], [a[2] for a in doi], [a[3] for a in doi]),
                     "mo_hinh_rho_w": spearman([a[1] for a in doi], [a[2] for a in doi], [a[3] for a in doi]),
                     "llm_rho": spearman([a[0] for a in doi], [a[2] for a in doi]),
                     "mo_hinh_rho": spearman([a[1] for a in doi], [a[2] for a in doi])}
    ra["doi_dau_pv"] = {"n": len(doi_pv), "llm_rho": spearman([a[0] for a in doi_pv], [a[2] for a in doi_pv]),
                        "mo_hinh_rho": spearman([a[1] for a in doi_pv], [a[2] for a in doi_pv])}
    return ra


def dat_cong(kiem: Dict[str, Any], ta: Dict[str, Any]) -> Tuple[bool, str]:
    """Cổng nối vào sản xuất: rho giữ lại ≥ 0,3 VÀ đối đầu trên video ta: mô hình > giám khảo LLM, n ≥ 20."""
    rho = kiem.get("rho_giu_y_no")
    dd = ta.get("doi_dau") or {}
    n, a, b = int(dd.get("n") or 0), dd.get("mo_hinh_rho_w"), dd.get("llm_rho_w")
    if rho is None or rho < RHO_GIU_LAI_TOI_THIEU:
        return False, "rho giữ lại {0} < {1}".format(rho, RHO_GIU_LAI_TOI_THIEU)
    if n < N_TA_TOI_THIEU or a is None or b is None:
        return False, "video ta đối đầu n {0} < {1}".format(n, N_TA_TOI_THIEU)
    if a <= b:
        return False, "trên video ta mô hình {0} ≤ giám khảo LLM {1} (n {2})".format(a, b, n)
    return True, "rho giữ lại {0}; video ta mô hình {1} > LLM {2} (n {3})".format(rho, a, b, n)


# ── 6) Lượt học (kỹ năng D23) ───────────────────────────────────────────────


def tap_hoc(goc: str, in_ra: Callable[[str], None] = lambda *_a: None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    t0 = time.time()
    ds = doc_video(goc)
    nhan, tt = tinh_nhan(ds)
    fv = ham_vung(goc)
    for x in nhan:
        x["vung"] = fv(x["tieu_de"], "https://www.youtube.com/watch?v=" + x["vid"]) if fv else None
    tt["giay_doc"] = round(time.time() - t0, 1)
    tt["n_kenh_do"] = sum(1 for x in nhan if x["nguon"] == "kenh-do")
    in_ra("dữ liệu: {0} video đọc → {1} đủ tuổi ≥ {2} ngày → {3} có trung vị kênh tin được ({4} kênh) · {5}s".format(
        tt.get("n_vao"), tt.get("n_du_tuoi"), TUOI_MIN, tt.get("n"), tt.get("n_kenh"), tt["giay_doc"]))
    return nhan, tt


def co_du_lieu(goc: str) -> bool:
    return bool(glob.glob(os.path.join(goc, "CHANNEL", "_NHOM", "*", "nghien-cuu", "kenh-do.json")) or glob.glob(
        os.path.join(goc, "CHANNEL", "*", "nghien-cuu", "content.csv")))


def can_chay(goc: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """D23: chưa có mô hình hoặc mô hình ≥ 7 ngày; chỉ giờ vắng (01:00–04:59 hoặc 21:00–22:59) và khe nặng rảnh."""
    bay = bay or _dt.datetime.now()
    if not co_du_lieu(goc):
        return False, "chưa có dữ liệu đối thủ"
    hh = _doc_json(duong_hien_hanh(goc)) or {}
    try:
        tuoi = (bay - _dt.datetime.strptime(str(hh.get("luc_hoc") or hh.get("luc") or "")[:19], "%Y-%m-%d %H:%M:%S")).days
    except ValueError:
        tuoi = None
    if tuoi is not None and tuoi < 7:
        return False, "mô hình mới {0} ngày".format(tuoi)
    if not (1 <= bay.hour < 5 or 21 <= bay.hour < 23):
        return False, "chờ giờ vắng (01–05 hoặc 21–23 giờ)"
    try:
        from core import khe  # noqa: PLC0415
        if not khe._khe_trong(khe.duong_khoa_nang(goc)):  # noqa: SLF001
            return False, "khe nặng đang bận"
    except Exception:  # noqa: BLE001
        pass
    return True, "chưa học lần nào" if tuoi is None else "mô hình cũ {0} ngày".format(tuoi)


def _ha_uu_tien() -> None:
    """Tiến trình học chạy ưu tiên THẤP (Windows: BELOW_NORMAL) — không giành CPU của sản xuất."""
    try:
        if os.name == "nt":
            import ctypes  # noqa: PLC0415
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
            k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)
        else:
            os.nice(10)
    except Exception:  # noqa: BLE001
        pass


def chay(goc: str, *, thu: bool = False, in_ra: Callable[[str], None] = print,
         bay: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Một lượt học: dữ liệu → nhãn → học (`NHAN_HOC`) → mốc → chuyển giao sang video ta → giữ bản tốt hơn."""
    bay = bay or _dt.datetime.now()
    ds, tt = tap_hoc(goc, in_ra)
    bc: Dict[str, Any] = {"luc": bay.strftime("%Y-%m-%d %H:%M:%S"), "du_lieu": tt, "mo_hinh": {}}
    if len(ds) < 500:
        bc["loi"] = "quá ít dữ liệu ({0} video)".format(len(ds))
        in_ra(bc["loi"])
        return bc
    tot = None
    for nhan in NHAN_HOC:
        in_ra("học nhãn {0}…".format(nhan))
        mh = huan_luyen_mo_hinh(ds, nhan, in_ra=in_ra)
        y = np.array([x["y_no"] for x in ds])
        moc = moc_don_gian(ds, np.setdiff1d(np.arange(len(ds)), mh["giu"]), mh["giu"], y)
        ta = kiem_kenh_ta(goc, mh, bay)
        bc["mo_hinh"][nhan] = {"kiem": mh["kiem"], "moc": moc, "ta": ta}
        in_ra("  {0}: giữ lại n {1} rho(nhãn) {2} rho(y_no) {3} lift top10% {4} · mốc vùng {5} · mốc độ dài {6}".format(
            nhan, mh["kiem"]["n_giu"], mh["kiem"]["rho_giu"], mh["kiem"]["rho_giu_y_no"], mh["kiem"]["lift_10"],
            moc["vung"]["rho"], moc["do_dai"]["rho"]))
        in_ra("  video ta: view n {0} rho {1} · CTR n {2} rho_w {3} · phân vị n {4} rho {5} · đối đầu LLM (CTR) n {6}: "
              "mô hình {7} vs LLM {8} · đối đầu LLM (phân vị) n {9}: mô hình {10} vs LLM {11}".format(
                  ta["view"]["n"], ta["view"]["rho"], ta["ctr"]["n"], ta["ctr"]["rho_w"], ta["pv"]["n"], ta["pv"]["rho"],
                  ta["doi_dau"]["n"], ta["doi_dau"]["mo_hinh_rho_w"], ta["doi_dau"]["llm_rho_w"], ta["doi_dau_pv"]["n"],
                  ta["doi_dau_pv"]["mo_hinh_rho"], ta["doi_dau_pv"]["llm_rho"]))
        if tot is None or (mh["kiem"]["rho_giu_y_no"] or -1) > (tot[0]["kiem"]["rho_giu_y_no"] or -1):
            tot = (mh, ta)
    mh, ta = tot
    # so bản đang dùng trên CÙNG tập giữ lại (chỉ video đăng sau mốc dữ liệu của bản cũ)
    cu = nap(goc)
    giu = mh["giu"]
    y = np.array([x["y_no"] for x in ds])
    if cu is not None:
        sau = [i for i in giu if ds[i]["dang"].isoformat() >= str(cu.get("moc_du_lieu") or "")]
        if len(sau) >= 200:
            p_cu = du_doan_mh(cu, [ds[i] for i in sau])
            p_moi = du_doan_mh(mh, [ds[i] for i in sau])
            r_cu, r_moi = spearman(p_cu, y[sau]), spearman(p_moi, y[sau])
            bc["so_ban_cu"] = {"n": len(sau), "rho_cu": r_cu, "rho_moi": r_moi, "tep_cu": (cu.get("hien_hanh") or {}).get("tep")}
            in_ra("so bản đang dùng (n {0}): cũ {1} · mới {2}".format(len(sau), r_cu, r_moi))
            if r_cu is not None and (r_moi is None or r_moi < r_cu - 0.005):
                bc["giu_ban_cu"] = True
    ok, ly = dat_cong(mh["kiem"], ta)
    bc["cong"] = {"dat": ok, "ly_do": ly, "nhan": mh["nhan"]}
    in_ra("cổng nối sản xuất: {0} — {1}".format("ĐẠT" if ok else "chưa", ly))
    if not thu:
        if not bc.get("giu_ban_cu"):
            luu(goc, mh, _gon({"luc_hoc": bc["luc"], "nhan": mh["nhan"], "kiem": mh["kiem"], "ta": ta, "cong": bc["cong"],
                               "du_lieu": tt, "so_ban_cu": bc.get("so_ban_cu")}))
        else:
            hh = _doc_json(duong_hien_hanh(goc)) or {}
            _ghi_json(duong_hien_hanh(goc), dict(hh, luc_hoc=bc["luc"], lan_hoc_kem=bc.get("so_ban_cu")))
        _ghi_json(os.path.join(thu_muc(goc), "bao-cao-{0}.json".format(bay.date().isoformat())), _gon(bc))
        _ghi_nao(goc, bc, bay)
    return bc


def _gon(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _gon(v) for k, v in x.items() if not isinstance(v, np.ndarray)}
    if isinstance(x, (list, tuple)):
        return [_gon(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    return x


def _ghi_nao(goc: str, bc: Dict[str, Any], bay: _dt.datetime) -> None:
    try:
        from core import nao_bo_phan as nbp  # noqa: PLC0415
        m = (bc.get("mo_hinh") or {}).get((bc.get("cong") or {}).get("nhan") or "y_no") or {}
        k = m.get("kiem") or {}
        dd = (m.get("ta") or {}).get("doi_dau") or {}
        nbp.ghi(goc, "chon-content", "do", khoa="gia-tri:{0}".format(bay.date().isoformat()), nguon="gia_tri",
                noi_dung="hàm giá trị đề tài+tiêu đề: giữ lại n {0} rho {1}, lift top 10% {2}; video ta đối đầu LLM n {3}: "
                         "mô hình {4} vs LLM {5}; cổng sản xuất: {6}".format(
                             k.get("n_giu"), k.get("rho_giu_y_no"), (k.get("lift_10") or {}).get("lift"), dd.get("n"),
                             dd.get("mo_hinh_rho_w"), dd.get("llm_rho_w"), (bc.get("cong") or {}).get("ly_do")),
                so={"kiem": _gon(k), "doi_dau": dd})
    except Exception:  # noqa: BLE001
        pass


def bao_cao_moi(goc: str) -> Dict[str, Any]:
    ds = sorted(glob.glob(os.path.join(thu_muc(goc), "bao-cao-????-??-??.json")))
    return (_doc_json(ds[-1]) or {}) if ds else {}


def dong_bao_cao(goc: str) -> List[str]:
    """Một dòng báo cáo ngày."""
    hh = _doc_json(duong_hien_hanh(goc)) or {}
    if not hh:
        return ["- Hàm giá trị (G2): chưa học lần nào (kỹ năng D23)"]
    k = hh.get("kiem") or {}
    dd = (hh.get("ta") or {}).get("doi_dau") or {}
    return ["- Hàm giá trị (G2, {0}): giữ lại rho {1}, lift top 10% ×{2}; video ta n {3}: mô hình {4} vs giám khảo LLM "
            "{5} · cổng sản xuất: {6}".format(str(hh.get("luc_hoc") or hh.get("luc") or "")[:10], k.get("rho_giu_y_no"),
                                               (k.get("lift_10") or {}).get("lift"), dd.get("n"), dd.get("mo_hinh_rho_w"),
                                               dd.get("llm_rho_w"), "đạt" if (hh.get("cong") or {}).get("dat") else "chưa")]


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(prog="core.gia_tri", description=__doc__.split("\n")[0])
    ap.add_argument("lenh", choices=("huan-luyen", "du-doan", "kiem-ta"))
    ap.add_argument("chu", nargs="?", default="")
    ap.add_argument("--thu", action="store_true")
    ap.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    if a.lenh == "du-doan":
        print(du_doan(a.goc, a.chu))
        return 0
    if a.lenh == "kiem-ta":
        mh = nap(a.goc)
        if mh is None:
            print("chưa có mô hình")
            return 4
        print(json.dumps(kiem_kenh_ta(a.goc, mh), ensure_ascii=False, indent=1))
        return 0
    _ha_uu_tien()
    bc = chay(a.goc, thu=a.thu)
    return 0 if not bc.get("loi") else 30


if __name__ == "__main__":
    sys.exit(main())
