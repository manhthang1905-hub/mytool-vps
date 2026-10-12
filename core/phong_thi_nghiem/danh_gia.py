"""ĐO giả thuyết — tầng 1 (thị trường) + tầng 2 (cầu nối, ghi công bóng) → bảng xếp hạng có khoảng tin.

═══ TẦNG 1 — THỊ TRƯỜNG (nhanh, n lớn) ═══
Mỗi dòng nhật ký bóng (ngày D) ghi top-K kèm view `v`, giờ quét `t`, trung vị kênh nguồn `tv`. Ở +3 / +7 ngày (dung
sai ±1,5 / ±2,5 ngày) tra view của chính video đó trong các ảnh chụp kho về sau (của MỌI kênh — cùng video đối thủ
nằm trong sổ nhiều kênh). "Đang lên" = view TĂNG THÊM ≥ `NGUONG_TANG_TT` × trung vị kênh nguồn trong khoảng ấy (video
kiếm thêm ít nhất một "video thường" của chính kênh nó); "nổ" (`7n_no`) = thêm ≥ 5 × trung vị trong 7 ngày. Mức nền
= tỉ lệ ấy trên CẢ vũ trụ ứng viên của (kênh, D) —
`nang` = tỉ lệ top-K − mức nền cùng (kênh, D). Gộp toàn danh mục: bỏ trùng (D, mã) giữa các kênh.

═══ TẦNG 2 — CẦU NỐI (ghi công bóng) ═══
Mỗi video kênh ta đã làm từ nguồn S vào ngày D (sổ `tu-chay`, bỏ lượt bị bỏ): lấy nhật ký MUỘN NHẤT của (kênh, giả
thuyết) trong [D − `LUI_NHAT_KY`, D − 1] (nhật ký ngày D có thể đã thấy lựa chọn — không dùng). S nằm trong top-K
→ giả thuyết được ghi kết quả thật của video theo thước chung (`thuoc_thang`: thắng 1, trung bình 0,5, trượt 0);
không nằm → ghi vào nhóm "ngoài top" (để so). Một video cho dữ liệu nhiều giả thuyết cùng lúc.

Hậu nghiệm Beta, CO VỀ CHUNG (phân tầng 3 mức): tỉ lệ nền toàn danh mục g = Beta(1 + điểm, 1 + n − điểm) mọi video
đã phán; giả thuyết h: μ_h = (κ₀·g + Σ_k điểm_kh)/(κ₀ + Σ_k n_kh); (kênh k × h): Beta(κ₁·μ_h + điểm_kh,
κ₁·(1 − μ_h) + n_kh − điểm_kh). P(tốt nhất) = Monte Carlo `N_MC` lượt (hạt giống tất định theo kênh). Nhãn thắng là
phân vị CỦA CHÍNH kênh nên tỉ lệ các kênh so được với nhau — riêng kênh chưa được YouTube phát thì mọi video trượt.

Mọi bảng in kèm n và khoảng tin 90%. Không bao giờ phán bằng 1–2 video.

═══ ĐỢT 2 (12/10/2026) ═══
* TẦNG 1 CÔNG BẰNG (`tang_thi_truong_cong_bang`, thay bản cũ trong bảng xếp hạng — bản cũ giữ để so): mỗi ứng viên
  tính MỘT lần cho mỗi giả thuyết — ngày ĐẦU TIÊN nó vào top-K (bản cũ đếm một video nằm top 10 ngày thành 10 lần, mỗi
  lần đo từ một ngày nó đã nổ sẵn); kết quả chính = NỔ +7 ngày (`7n_no`, kiếm thêm ≥ 5 × trung vị kênh nguồn) — không
  là cổng của giả thuyết nào (cổng đọc TRẠNG THÁI lúc chấm: gấp, độ dài, pool…, không đọc tương lai). Ba mức nền =
  "rút ngẫu nhiên": (a) từ CÙNG vũ trụ đã lọc của (kênh, ngày) — `nen`/`nang`; (b) cùng vũ trụ nhưng CÙNG Ô gấp ×
  tuổi × đà (còn tăng/ngày) với chính video được chọn — `nen_tang`/`nang_tang` (gỡ phần "chọn video đã to, còn trẻ,
  đang tăng thì dĩ nhiên còn tăng" khỏi H-POOL/H-DOT-BIEN — đây là số dùng làm tiên nghiệm và sàn; ô thưa < `N_O_TANG`
  dòng lùi về gấp × đà, rồi gấp, rồi cả vũ trụ); (c) từ tập QUA CỔNG của chính giả thuyết hôm ấy —
  `nen_cong`/`nang_cong` (xếp hạng có thêm gì so với cổng). Mẫu nền + tập qua cổng của mỗi (kênh, ngày) nhớ ở
  `CHANNEL/<k>/phong-thi-nghiem/nen-<ngày>.json` (ảnh chụp kho cố định → tính một lần).
* TẦNG 2: thêm GHI CÔNG CHÍNH XÁC — lượt sản xuất mà khe được phòng thí nghiệm chia cho giả thuyết h (sổ lượt
  `nguon.gia_thuyet`, `chia_khe`) ghi kết quả cho đúng h dù nhật ký bóng hôm trước không có nguồn ấy trong top; đếm
  `n_chinh_xac`, `thang`.
* HẬU NGHIỆM PHÂN TẦNG + tầng 1 làm tiên nghiệm YẾU: μ_h = (κ₀·g + w₁·m₁_h + Σ điểm)/(κ₀ + w₁ + Σ n), với m₁_h = g +
  `DELTA_TANG1`·tanh(nâng_tầng_h / `THANG_TANG1`) và w₁ = `KAPPA_TANG1` (= 1 video giả — nhỏ, khai rõ). P(tốt nhất) theo
  kênh rút HAI BẬC: μ_h ~ Beta(mức danh mục), rồi θ_kh ~ Beta(κ₁μ_h + điểm, κ₁(1 − μ_h) + n − điểm) — kênh co về danh
  mục và độ bất định của danh mục truyền xuống kênh (cùng cách `chia_khe` rút Thompson).
"""

from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import io
import json
import math
import os
import random
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import _chung as c

KAPPA_CHUNG = 2.0
KAPPA_KENH = 4.0
N_MC = 4000
LUI_NHAT_KY = 3
#: Cửa sổ tầng 1: `{tên: (số ngày, dung sai ngày, ngưỡng × trung vị kênh nguồn)}` — "3n"/"7n" = còn được đẩy (kiếm
#: thêm ≥ 1 "video thường" của kênh nó), "7n_no" = NỔ (kiếm thêm ≥ 5 video thường trong 7 ngày).
CUA_SO_TT: Dict[str, Tuple[float, float, float]] = {"3n": (3.0, 1.5, 1.0), "7n": (7.0, 2.5, 1.0),
                                                    "7n_no": (7.0, 2.5, 5.0)}
NGUONG_TANG_TT = 1.0
NGAY_TANG_1 = 60
#: Luật quyết (áp ở `luat.py`): dẫn đầu P ≥ 0,8 với n ≥ 8; loại P < 0,05 với n ≥ 8.
P_DAN_DAU, P_LOAI, N_QUYET = 0.8, 0.05, 8
KHAM_PHA = 0.15
DIEM_NHAN = {"thang": 1.0, "trung_binh": 0.5, "truot": 0.0}
#: Tầng 1 công bằng — kết quả chính (nổ +7 ngày), mẫu tập qua cổng mỗi (kênh, ngày, giả thuyết), tầng gấp/tuổi.
KQ_CHINH = "7n_no"
MAU_CONG = 400
TANG_VUOT = (1.0, 2.0, 3.0, 5.0, 8.0, 15.0, 30.0)
TANG_TUOI = (3.0, 7.0, 30.0)
#: Ô (gấp × tuổi × đà) của một (kênh, ngày) cần ≥ ngần này dòng có kết quả, không thì lùi về gấp × đà, gấp, cả vũ trụ.
N_O_TANG = 8
#: Tiên nghiệm tầng 1 (yếu, khai rõ): trọng số = KAPPA_TANG1 video giả; nâng tầng → lệch tối đa ±DELTA_TANG1 quanh g.
KAPPA_TANG1 = 1.0
DELTA_TANG1 = 0.15
THANG_TANG1 = 0.10
N_TANG1_TOI_THIEU = 30


# ── Beta ────────────────────────────────────────────────────────────────────

def _betacf(a: float, b: float, x: float) -> float:
    """Phân số liên tục của hàm beta không đầy đủ (Lentz, như Numerical Recipes `betacf`)."""
    nho = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    cc = 1.0
    d = 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) >= nho else nho)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)),
                   -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) >= nho else nho)
            cc = 1.0 + aa / cc
            cc = cc if abs(cc) >= nho else nho
            de = d * cc
            h *= de
        if abs(de - 1.0) < 3e-14:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Hàm beta không đầy đủ chuẩn hoá I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(ln) * _betacf(a, b, x) / a
    return 1.0 - math.exp(ln) * _betacf(b, a, 1.0 - x) / b


def beta_ppf(p: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def ci90(a: float, b: float) -> List[float]:
    return [round(beta_ppf(0.05, a, b), 3), round(beta_ppf(0.95, a, b), 3)]


def _rng(hat: str) -> random.Random:
    return random.Random(int(hashlib.sha1(hat.encode("utf-8")).hexdigest()[:12], 16))


def p_tot_nhat(tham: Dict[str, Tuple[float, float]], hat: str, n: int = N_MC) -> Dict[str, float]:
    """P(θ_h lớn nhất) với θ_h ~ Beta(a_h, b_h) độc lập — Monte Carlo tất định theo `hat`."""
    if not tham:
        return {}
    ten = sorted(tham)
    if len(ten) == 1:
        return {ten[0]: 1.0}
    r = _rng(hat)
    dem = {t: 0 for t in ten}
    for _ in range(n):
        tot, gt = -1.0, ten[0]
        for t in ten:
            a, b = tham[t]
            x = r.betavariate(max(a, 1e-6), max(b, 1e-6))
            if x > tot:
                tot, gt = x, t
        dem[gt] += 1
    return {t: round(dem[t] / float(n), 4) for t in ten}


# ── chỉ số view (từ ảnh chụp kho) ───────────────────────────────────────────

#: Mức nền tầng 1 tính trên MẪU tất định tối đa ngần này dòng mỗi (kênh, ngày) (chọn theo băm mã) — đủ chính xác
#: (±2–4 điểm) mà bộ nhớ chỉ giữ chuỗi view của các mã cần (top-K đã ghi + mẫu nền), không phải cả vũ trụ.
MAU_NEN = 800


def _trong_mau(ma: str, n: int, mau: int = MAU_NEN) -> bool:
    if n <= mau:
        return True
    return int(hashlib.sha1(ma.encode("utf-8")).hexdigest()[:8], 16) / float(0xFFFFFFFF) < mau / float(n)


def _doc_gon(duong: str) -> List[Tuple[str, Optional[float], Optional[float], Optional[float]]]:
    """Ảnh chụp kho → `[(mã, view, giờ quét, trung vị kênh)]` (chỉ 4 cột)."""
    ra = []
    try:
        with gzip.open(duong, "rt", encoding="utf-8", newline="") as tep:
            for r in csv.DictReader(tep):
                ra.append((r.get("ma") or "", c.so(r.get("view")), c.so(r.get("luc")), c.so(r.get("view_tv"))))
    except (OSError, ValueError, EOFError, csv.Error):
        pass
    return ra


class ChiSoView:
    """`{mã: [(giờ quét, view)]}` từ ảnh chụp kho của nhiều kênh + số ghi trong nhật ký. `can` (tập mã) = chỉ giữ chuỗi
    của các mã ấy (None = mọi mã)."""

    def __init__(self, can: Optional[Set[str]] = None) -> None:
        self.obs: Dict[str, List[Tuple[float, float]]] = {}
        self.can = can

    def them(self, ma: str, t: Optional[float], v: Optional[float]) -> None:
        if not ma or t is None or v is None or (self.can is not None and ma not in self.can):
            return
        ds = self.obs.setdefault(ma, [])
        x = (float(t), float(v))
        i = bisect.bisect_left(ds, x)
        if i < len(ds) and abs(ds[i][0] - x[0]) < 1.0 and ds[i][1] == x[1]:
            return
        ds.insert(i, x)

    def nap_tep(self, duong: str) -> List[Dict[str, Any]]:
        """Nạp một ảnh chụp kho; trả các dòng gọn (ma, view, luc, view_tv)."""
        ra = []
        for ma, v, t, tv in _doc_gon(duong):
            self.them(ma, t, v)
            ra.append({"ma": ma, "view": v, "luc": t, "view_tv": tv})
        return ra

    def tim(self, ma: str, t_muc: float, dung_sai: float, sau: float) -> Optional[Tuple[float, float]]:
        ds = self.obs.get(ma) or []
        lo = bisect.bisect_left(ds, (t_muc - dung_sai, -1e300))
        hi = bisect.bisect_right(ds, (t_muc + dung_sai, 1e300))
        tot = None
        for t, v in ds[lo:hi]:
            if t <= sau:
                continue
            if tot is None or abs(t - t_muc) < abs(tot[0] - t_muc):
                tot = (t, v)
        return tot


def ket_qua_tt(idx: ChiSoView, ma: str, v0: Optional[float], t0: Optional[float], tv: Optional[float],
               so_ngay: float, dung_sai: float, nguong: float = NGUONG_TANG_TT) -> Optional[bool]:
    """Video có "đang lên" trong `so_ngay` ngày sau lần quét `t0` không (kiếm thêm ≥ `nguong` × trung vị kênh nguồn);
    chưa có số → None."""
    if not ma or v0 is None or t0 is None or not tv or tv <= 0:
        return None
    ob = idx.tim(ma, t0 + so_ngay * c.NGAY_GIAY, dung_sai * c.NGAY_GIAY, t0 + 0.5 * c.NGAY_GIAY)
    if ob is None:
        return None
    return (ob[1] - v0) >= nguong * tv


def _o_tt() -> Dict[str, Any]:
    return {w: {"n": 0, "hit": 0, "nen_tong": 0.0} for w in CUA_SO_TT}


def _chot_tt(o: Dict[str, Any]) -> Dict[str, Any]:
    ra = {}
    for w, x in o.items():
        n, h = x["n"], x["hit"]
        ra[w] = {"n": n, "hit": h, "ti_le": round(h / n, 3) if n else None, "ci90": ci90(1 + h, 1 + n - h),
                 "nen": round(x["nen_tong"] / n, 3) if n else None,
                 "nang": round(h / n - x["nen_tong"] / n, 3) if n else None}
    return ra


def tang_thi_truong(goc: str, logs: Sequence[Dict[str, Any]], kenh_ds: Sequence[str]) -> Dict[str, Any]:
    """Tầng 1 — `{"chung": {gt: {3n, 7n}}, "theo_kenh": {k: {gt: …}}, "nen": {k: {ngày: {3n: tỉ lệ}}}}`."""
    from .dac_trung import duong_kho, ngay_co_kho  # noqa: PLC0415

    if not logs:
        return {"chung": {}, "theo_kenh": {}, "nen": {}}
    ngay_log = sorted({x["ngay"] for x in logs})
    tu, den = ngay_log[0], c.cong_ngay(ngay_log[-1], 12)
    # Lượt 1: mẫu nền của các (kênh, ngày) có nhật ký + mã top-K → tập mã cần chuỗi view.
    can: Set[str] = {str(it.get("ma") or "") for x in logs for it in (x.get("top") or [])}
    base_rows: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    cap_log = {(x.get("kenh", ""), x.get("ngay", "")) for x in logs}
    for k, d in sorted(cap_log):
        if k not in kenh_ds:
            continue
        ds = _doc_gon(duong_kho(goc, k, d))
        rows = [{"ma": m, "view": v, "luc": t, "view_tv": tv} for m, v, t, tv in ds if m and _trong_mau(m, len(ds))]
        base_rows[(k, d)] = rows
        can.update(r["ma"] for r in rows)
    # Lượt 2: chuỗi view của các mã cần, từ mọi ảnh chụp trong khoảng (mọi kênh — cùng video nằm trong nhiều sổ).
    idx = ChiSoView(can)
    for k in kenh_ds:
        for d in ngay_co_kho(goc, k):
            if tu <= d <= den:
                for m, v, t, _tv in _doc_gon(duong_kho(goc, k, d)):
                    idx.them(m, t, v)
    for x in logs:
        for it in x.get("top") or []:
            idx.them(str(it.get("ma") or ""), c.so(it.get("t")), c.so(it.get("v")))
    nen: Dict[Tuple[str, str], Dict[str, Optional[float]]] = {}

    def nen_cua(k: str, d: str) -> Dict[str, Optional[float]]:
        if (k, d) not in nen:
            o = {}
            rows = base_rows.get((k, d)) or []
            for w, (so_ngay, ds, ng) in CUA_SO_TT.items():
                kq = [ket_qua_tt(idx, r["ma"], r["view"], r["luc"], r["view_tv"], so_ngay, ds, ng) for r in rows]
                kq = [y for y in kq if y is not None]
                o[w] = (sum(1 for y in kq if y) / float(len(kq))) if kq else None
            nen[(k, d)] = o
        return nen[(k, d)]

    theo_kenh: Dict[str, Dict[str, Dict[str, Any]]] = {}
    chung: Dict[str, Dict[str, Any]] = {}
    thay_chung: Set[Tuple[str, str, str, str]] = set()
    for x in logs:
        k, d, gt = x.get("kenh", ""), x.get("ngay", ""), x.get("gt", "")
        oc = theo_kenh.setdefault(k, {}).setdefault(gt, _o_tt())
        og = chung.setdefault(gt, _o_tt())
        nk = nen_cua(k, d)
        for it in x.get("top") or []:
            ma = str(it.get("ma") or "")
            for w, (so_ngay, ds, ng) in CUA_SO_TT.items():
                y = ket_qua_tt(idx, ma, c.so(it.get("v")), c.so(it.get("t")), c.so(it.get("tv")), so_ngay, ds, ng)
                if y is None or nk.get(w) is None:
                    continue
                oc[w]["n"] += 1
                oc[w]["hit"] += 1 if y else 0
                oc[w]["nen_tong"] += nk[w]
                if (gt, w, d, ma) not in thay_chung:
                    thay_chung.add((gt, w, d, ma))
                    og[w]["n"] += 1
                    og[w]["hit"] += 1 if y else 0
                    og[w]["nen_tong"] += nk[w]
    return {"chung": {gt: _chot_tt(o) for gt, o in chung.items()},
            "theo_kenh": {k: {gt: _chot_tt(o) for gt, o in m.items()} for k, m in theo_kenh.items()},
            "nen": {k: {d: {w: (None if v is None else round(v, 3)) for w, v in o.items()}
                        for (k2, d), o in nen.items() if k2 == k} for k in {k for k, _d in nen}}}


# ── tầng 1 CÔNG BẰNG (đợt 2) ────────────────────────────────────────────────

def o_tang(vuot: Optional[float], tuoi: Optional[float], tang: Any = None) -> Tuple[int, int, int]:
    """`(tầng gấp, tầng tuổi, còn tăng)` của một ứng viên (-1 = thiếu số) — ô so "cùng cỡ, cùng tuổi, cùng đà" (đà =
    `Tăng/ngày` của sổ > 0: cổng `tang_duong` của H-POOL; không so cùng đà thì "đang tăng thì còn tăng" lọt vào nâng)."""
    iv = -1 if vuot is None else bisect.bisect_right(TANG_VUOT, float(vuot))
    it = -1 if tuoi is None else bisect.bisect_right(TANG_TUOI, float(tuoi))
    td = -1 if tang is None else (1 if float(tang) > 0 else 0)
    return iv, it, td


def khoa_gt(g: Dict[str, Any]) -> str:
    return "{0}@{1}".format(g.get("id"), int(g.get("phien_ban") or 1))


#: Phiên bản định dạng `nen-<ngày>.json.gz` (2 = thêm tăng/ngày cho ô "cùng đà") — khác thì tính lại.
PHIEN_BAN_NEN = 2


def duong_nen(goc: str, kenh: str, ngay: str) -> str:
    return os.path.join(c.thu_muc_kenh(goc, kenh), "nen-{0}.json.gz".format(ngay))


def _doc_nen(p: str) -> Optional[Dict[str, Any]]:
    try:
        with gzip.open(p, "rt", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) and isinstance(du.get("so"), dict) else None
    except (OSError, ValueError, EOFError):
        return None


def nen_ngay(goc: str, kenh: str, ngay: str, reg: Sequence[Dict[str, Any]], top_ma: Iterable[str]) -> Dict[str, Any]:
    """Mẫu nền + tập qua cổng của (kênh, ngày) cho tầng 1 công bằng — nhớ ở `nen-<ngày>.json.gz` (ảnh chụp kho cố định,
    giả thuyết tách theo phiên bản ⇒ tính MỘT lần; thiếu khoá thì đọc lại ảnh chụp đúng một lần):

        {"pb": PHIEN_BAN_NEN, "so": {mã: [view, giờ quét, trung vị kênh nguồn, gấp, tuổi ngày, tăng/ngày] | null},
         "mau": [mã…] (mẫu nền ≤ MAU_NEN), "cong": {"<gt>@<pb>": {"n": số qua cổng, "mau": [mã…] (≤ MAU_CONG)}}}

    Không có ảnh chụp kho → cái đã nhớ (hoặc {})."""
    from . import dac_trung  # noqa: PLC0415
    from . import gia_thuyet as gtm  # noqa: PLC0415

    p = duong_nen(goc, kenh, ngay)
    cu = _doc_nen(p)
    if cu is not None and cu.get("pb") != PHIEN_BAN_NEN:
        cu = None
    top_ma = {m for m in top_ma if m}
    can = [g for g in reg if g.get("loai") != gtm.LOAI_LLM and g.get("trang_thai") != gtm.LOAI]
    if cu is not None and all(khoa_gt(g) in (cu.get("cong") or {}) for g in can) and top_ma <= set(cu["so"]):
        return cu
    kho = dac_trung.doc_kho(goc, kenh, ngay)
    if not kho:
        return cu or {}
    theo_ma = {str(d.get("ma") or ""): d for d in kho if d.get("ma")}
    so_: Dict[str, Any] = dict((cu or {}).get("so") or {})

    def ghi_so(m: str) -> None:
        if m in so_ and so_[m] is not None:
            return
        d = theo_ma.get(m)
        so_[m] = None if d is None else [d.get("view"), d.get("luc"), d.get("view_tv"), d.get("vuot"),
                                         d.get("tuoi_ngay"), d.get("tang_ngay")]
    n = len(theo_ma)
    mau = [m for m in theo_ma if _trong_mau(m, n)]
    for m in mau:
        ghi_so(m)
    for m in top_ma:
        ghi_so(m)
    cong = dict((cu or {}).get("cong") or {})
    for g in can:
        ds, n_du = gtm.xep_hang(g, kho, max(1, n))
        ma_ds = [str(d.get("ma") or "") for d, _x in ds if d.get("ma")]
        chon = [m for m in ma_ds if _trong_mau(m, len(ma_ds), MAU_CONG)]
        for m in chon:
            ghi_so(m)
        cong[khoa_gt(g)] = {"n": int(n_du), "mau": chon}
    ra = {"pb": PHIEN_BAN_NEN, "ngay": ngay, "n_kho": n, "so": so_, "mau": mau, "cong": cong}
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tam = p + ".tmp"
        with gzip.open(tam, "wt", encoding="utf-8") as tep:
            json.dump(ra, tep, ensure_ascii=False, separators=(",", ":"))
        os.replace(tam, p)
    except OSError:
        pass
    return ra


def _o_cb() -> Dict[str, Any]:
    return {w: {"n": 0, "hit": 0, "nen_tong": 0.0, "tang_tong": 0.0, "cong_tong": 0.0, "n_cong": 0, "cong_hit": 0.0}
            for w in CUA_SO_TT}


def _chot_cb(o: Dict[str, Any], n_lap: int = 0) -> Dict[str, Any]:
    ra: Dict[str, Any] = {}
    for w, x in o.items():
        n, h, nc_ = x["n"], x["hit"], x["n_cong"]
        tl = h / float(n) if n else None
        nen = x["nen_tong"] / n if n else None
        tang = x["tang_tong"] / n if n else None
        cong = x["cong_tong"] / nc_ if nc_ else None
        tl_cong = x["cong_hit"] / nc_ if nc_ else None
        ra[w] = {"n": n, "hit": h, "ti_le": lam(tl), "ci90": ci90(1 + h, 1 + n - h),
                 "nen": lam(nen), "nang": lam(tl - nen) if n else None,
                 "nen_tang": lam(tang), "nang_tang": lam(tl - tang) if n else None,
                 "n_cong": nc_, "nen_cong": lam(cong),
                 "nang_cong": lam(tl_cong - cong) if (nc_ and tl_cong is not None and cong is not None) else None}
    ra["n_lap_bo"] = n_lap
    return ra


def lam(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(float(x), 3)


def tang_thi_truong_cong_bang(goc: str, logs: Sequence[Dict[str, Any]], kenh_ds: Sequence[str],
                              reg: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Tầng 1 CÔNG BẰNG — xem đầu tệp. `{"chung": {gt: {w: …}}, "theo_kenh": {k: {gt: {w: …}}}, "cach": "lan_dau",
    "kq_chinh": "7n_no"}`; mỗi ô: n (lần ĐẦU vào top), hit, ti_le [CI90], nen/nang (rút ngẫu nhiên cùng vũ trụ),
    nen_tang/nang_tang (cùng ô gấp × tuổi × đà), nen_cong/nang_cong (từ tập qua cổng của chính giả thuyết), `n_lap_bo`
    (lần xuất hiện LẶP đã bỏ)."""
    from .dac_trung import duong_kho, ngay_co_kho  # noqa: PLC0415

    rong = {"chung": {}, "theo_kenh": {}, "cach": "lan_dau", "kq_chinh": KQ_CHINH}
    if not logs:
        return rong
    hien = {g["id"]: g for g in reg}
    ds_log = sorted((x for x in logs if x.get("kenh") in kenh_ds),
                    key=lambda x: (x.get("ngay", ""), x.get("kenh", ""), x.get("gt", "")))
    if not ds_log:
        return rong
    # Lần ĐẦU vào top: theo (kênh, gt) và theo gt (cả danh mục — kênh/ngày sớm nhất).
    dau_k: Dict[Tuple[str, str], Dict[str, Tuple[str, Dict[str, Any]]]] = {}
    dau_c: Dict[str, Dict[str, Tuple[str, str, Dict[str, Any]]]] = {}
    lap_k: Dict[Tuple[str, str], int] = {}
    lap_c: Dict[str, int] = {}
    top_ngay: Dict[Tuple[str, str], Set[str]] = {}
    for x in ds_log:
        k, d, gt = x["kenh"], x["ngay"], x.get("gt", "")
        for it in x.get("top") or []:
            ma = str(it.get("ma") or "")
            if not ma:
                continue
            top_ngay.setdefault((k, d), set()).add(ma)
            m = dau_k.setdefault((k, gt), {})
            if ma in m:
                lap_k[(k, gt)] = lap_k.get((k, gt), 0) + 1
            else:
                m[ma] = (d, it)
            mc = dau_c.setdefault(gt, {})
            if ma in mc:
                lap_c[gt] = lap_c.get(gt, 0) + 1
            else:
                mc[ma] = (d, k, it)
    nen: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for (k, d), ma_s in sorted(top_ngay.items()):
        try:
            nen[(k, d)] = nen_ngay(goc, k, d, reg, ma_s)
        except Exception:  # noqa: BLE001 — một ngày hỏng không làm đổ cả bảng
            nen[(k, d)] = {}
    can: Set[str] = {m for v in dau_k.values() for m in v}
    for o in nen.values():
        can.update(o.get("mau") or [])
        for x in (o.get("cong") or {}).values():
            can.update(x.get("mau") or [])
    ngay_log = sorted({x["ngay"] for x in ds_log})
    tu, den = ngay_log[0], c.cong_ngay(ngay_log[-1], 12)
    idx = ChiSoView(can)
    for k in kenh_ds:
        for d in ngay_co_kho(goc, k):
            if tu <= d <= den:
                for m, v, t, _tv in _doc_gon(duong_kho(goc, k, d)):
                    idx.them(m, t, v)
    for x in ds_log:
        for it in x.get("top") or []:
            idx.them(str(it.get("ma") or ""), c.so(it.get("t")), c.so(it.get("v")))

    nho_kq: Dict[Tuple[Any, ...], Optional[bool]] = {}

    def kq_so(so_: Any, w: str) -> Optional[bool]:
        if not so_:
            return None
        khoa = (so_[0], so_[1], so_[2], so_[3], w)
        if khoa not in nho_kq:
            so_ngay, dsai, ng = CUA_SO_TT[w]
            nho_kq[khoa] = ket_qua_tt(idx, so_[0], c.so(so_[1]), c.so(so_[2]), c.so(so_[3]), so_ngay, dsai, ng)
        return nho_kq[khoa]

    # Mức nền mỗi (kênh, ngày, cửa sổ): cả mẫu, theo ô tầng, theo tầng gấp; tập qua cổng theo khoá giả thuyết.
    muc: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def muc_cua(k: str, d: str) -> Dict[str, Any]:
        if (k, d) in muc:
            return muc[(k, d)]
        o = nen.get((k, d)) or {}
        so_ = o.get("so") or {}
        ra: Dict[str, Any] = {}
        for w in CUA_SO_TT:
            tat, o_t, o_d, o_v = [0, 0], {}, {}, {}
            for m in o.get("mau") or []:
                s = so_.get(m)
                y = kq_so([m] + list(s[:3]), w) if s else None
                if y is None:
                    continue
                tat[0] += 1 if y else 0
                tat[1] += 1
                iv, it, td = o_tang(c.so(s[3]), c.so(s[4]), c.so(s[5]) if len(s) > 5 else None)
                for bang_o, khoa in ((o_t, (iv, it, td)), (o_d, (iv, td)), (o_v, iv)):
                    z = bang_o.setdefault(khoa, [0, 0])
                    z[0] += 1 if y else 0
                    z[1] += 1
            cong = {}
            for kg, x in (o.get("cong") or {}).items():
                hh = [kq_so([m] + list(so_[m][:3]), w) for m in x.get("mau") or [] if so_.get(m)]
                hh = [y for y in hh if y is not None]
                cong[kg] = (sum(1 for y in hh if y) / float(len(hh))) if hh else None
            ra[w] = {"vt": (tat[0] / float(tat[1])) if tat[1] else None, "o": o_t, "d": o_d, "v": o_v, "cong": cong}
        muc[(k, d)] = ra
        return ra

    def nen_tang(mm: Dict[str, Any], so_ma: Any) -> Optional[float]:
        if mm["vt"] is None:
            return None
        if so_ma:
            iv, it, td = o_tang(c.so(so_ma[3]), c.so(so_ma[4]), c.so(so_ma[5]) if len(so_ma) > 5 else None)
            for bang_o, khoa in ((mm["o"], (iv, it, td)), (mm["d"], (iv, td)), (mm["v"], iv)):
                z = bang_o.get(khoa)
                if z and z[1] >= N_O_TANG:
                    return z[0] / float(z[1])
        return mm["vt"]

    def cong_vao(o: Dict[str, Any], k: str, d: str, gt: str, it: Dict[str, Any]) -> None:
        g = hien.get(gt)
        so_ma = ((nen.get((k, d)) or {}).get("so") or {}).get(str(it.get("ma") or ""))
        for w, (so_ngay, dsai, ng) in CUA_SO_TT.items():
            y = ket_qua_tt(idx, str(it.get("ma") or ""), c.so(it.get("v")), c.so(it.get("t")), c.so(it.get("tv")),
                           so_ngay, dsai, ng)
            mm = muc_cua(k, d)[w]
            if y is None or mm["vt"] is None:
                continue
            x = o[w]
            x["n"] += 1
            x["hit"] += 1 if y else 0
            x["nen_tong"] += mm["vt"]
            x["tang_tong"] += nen_tang(mm, so_ma)
            cg = mm["cong"].get(khoa_gt(g)) if g else None
            if cg is not None:
                x["n_cong"] += 1
                x["cong_tong"] += cg
                x["cong_hit"] += 1 if y else 0

    theo_kenh: Dict[str, Dict[str, Any]] = {}
    for (k, gt), m in dau_k.items():
        o = _o_cb()
        for ma, (d, it) in m.items():
            cong_vao(o, k, d, gt, it)
        theo_kenh.setdefault(k, {})[gt] = _chot_cb(o, lap_k.get((k, gt), 0))
    chung: Dict[str, Any] = {}
    for gt, m in dau_c.items():
        o = _o_cb()
        for ma, (d, k, it) in m.items():
            cong_vao(o, k, d, gt, it)
        chung[gt] = _chot_cb(o, lap_c.get(gt, 0))
    return {"chung": chung, "theo_kenh": theo_kenh, "cach": "lan_dau", "kq_chinh": KQ_CHINH}


def tien_nghiem_tang1(t1: Dict[str, Any], g: float, gt_ds: Sequence[str]) -> Dict[str, Tuple[float, float]]:
    """`{gt: (m₁, w₁)}` — tầng 1 công bằng (nâng TẦNG của kết quả chính, toàn danh mục) đổi thành tiên nghiệm YẾU của
    tỉ lệ thắng mức danh mục (xem đầu tệp). Thiếu số / n < `N_TANG1_TOI_THIEU` → (g, 0) (không ảnh hưởng)."""
    ra: Dict[str, Tuple[float, float]] = {}
    ch = (t1 or {}).get("chung") or {}
    for gt in gt_ds:
        o = ((ch.get(gt) or {}).get(KQ_CHINH)) or {}
        lift = o.get("nang_tang") if o.get("nang_tang") is not None else o.get("nang")
        if lift is None or int(o.get("n") or 0) < N_TANG1_TOI_THIEU:
            ra[gt] = (g, 0.0)
            continue
        m1 = min(0.98, max(0.02, g + DELTA_TANG1 * math.tanh(float(lift) / THANG_TANG1)))
        ra[gt] = (round(m1, 4), KAPPA_TANG1)
    return ra


# ── tầng 2 ──────────────────────────────────────────────────────────────────

def ket_qua_san_xuat(goc: str, kenh: str) -> List[Dict[str, Any]]:
    """`[{ma_goi, ma, ngay, video_id, nhan, diem}]` — mọi lượt (không bị bỏ) có nguồn + ngày, nhãn thước chung NAY.
    `diem` None = chưa phán."""
    from .. import thuoc_thang as tt  # noqa: PLC0415
    from . import nguon  # noqa: PLC0415

    vm = nguon.video_minh_cua_kenh(goc, kenh)
    try:
        ket = nguon.nhan_tai_moc(vm, None)
    except Exception:  # noqa: BLE001
        ket = {}
    chuoi = {m: v["chuoi"] for m, v in vm.items()}
    ra = []
    for r in nguon.luot_san_xuat(goc, kenh):
        if r["bo"] or not r["ma"] or not r["ngay"]:
            continue
        vid = r["video_id"]
        k = ket.get(vid) if vid else None
        if k is None and vid and (r.get("ho_so") or {}).get("chi_so"):
            try:
                ch = tt.chuoi_ho_so(r["ho_so"], vid)
                if ch.diem:
                    k = tt.danh_gia_them(ch, chuoi, tt.tuoi_ho_so(r["ho_so"], r["ngay"]))
            except Exception:  # noqa: BLE001
                k = None
        nhan = str(getattr(k, "nhan", "") or "") if k is not None else ""
        ra.append({"ma_goi": r["ma_goi"], "ma": r["ma"], "ngay": r["ngay"], "video_id": vid, "nhan": nhan or "chua_du",
                   "diem": DIEM_NHAN.get(nhan), "cong_thuc": r.get("cong_thuc", ""),
                   "gia_thuyet": r.get("gia_thuyet", ""), "ptn_pb": r.get("ptn_pb")})
    return ra


def tang_cau_noi(san_xuat: Dict[str, List[Dict[str, Any]]], logs: Sequence[Dict[str, Any]],
                 gts: Dict[str, int]) -> Dict[str, Any]:
    """Tầng 2 — ghi công bóng (hàm thuần). `san_xuat` = `{kênh: ket_qua_san_xuat}`; `gts` = `{id: phiên bản hiện
    tại}`. Trả `{"theo_kenh": {k: {gt: {n, diem, n_ngoai, diem_ngoai, cho, video: [...]}}}, "nen_kenh": {k: {n, diem}},
    "khong_nhat_ky": {k: n}}`."""
    top: Dict[Tuple[str, str], Dict[str, Set[str]]] = {}
    co_nk: Dict[str, Set[str]] = {}
    for x in logs:
        gt, pb = x.get("gt", ""), int(x.get("pb") or 1)
        if gt not in gts or gts[gt] != pb:
            continue
        top.setdefault((x.get("kenh", ""), gt), {})[x.get("ngay", "")] = {
            str(i.get("ma") or "") for i in (x.get("top") or [])}
        co_nk.setdefault(x.get("kenh", ""), set()).add(gt)
    theo_kenh: Dict[str, Dict[str, Dict[str, Any]]] = {}
    nen_kenh: Dict[str, Dict[str, float]] = {}
    khong: Dict[str, int] = {}

    def o_cua(k: str, gt: str) -> Dict[str, Any]:
        return theo_kenh.setdefault(k, {}).setdefault(gt, {"n": 0, "diem": 0.0, "thang": 0, "n_ngoai": 0,
                                                           "diem_ngoai": 0.0, "cho": 0, "n_chinh_xac": 0,
                                                           "cho_chinh_xac": 0, "video": []})
    for k, ds in san_xuat.items():
        nk = nen_kenh.setdefault(k, {"n": 0, "diem": 0.0, "cho": 0})
        for r in ds:
            if r["diem"] is None:
                nk["cho"] += 1
            else:
                nk["n"] += 1
                nk["diem"] += r["diem"]
            # Khe phòng thí nghiệm chia cho h (sổ lượt `nguon.gia_thuyet`, đúng phiên bản) → ghi công CHÍNH XÁC cho h.
            gt_khe = str(r.get("gia_thuyet") or "")
            try:
                pb = int(r["ptn_pb"]) if r.get("ptn_pb") not in (None, "") else None
            except (TypeError, ValueError):
                pb = None
            if gt_khe and (gt_khe not in gts or (pb is not None and pb != gts[gt_khe])):
                gt_khe = ""
            co_log = bool(gt_khe)
            for gt in gts:
                ngay_log = top.get((k, gt)) or {}
                dung = None
                for i in range(1, LUI_NHAT_KY + 1):
                    d = c.cong_ngay(r["ngay"], -i)
                    if d in ngay_log:
                        dung = d
                        break
                chinh_xac = gt == gt_khe
                if dung is None and not chinh_xac:
                    continue
                co_log = True
                o = o_cua(k, gt)
                trong = chinh_xac or (r["ma"] in ngay_log[dung])
                if r["diem"] is None:
                    if trong:
                        o["cho"] += 1
                        o["cho_chinh_xac"] += 1 if chinh_xac else 0
                    continue
                if trong:
                    o["n"] += 1
                    o["diem"] += r["diem"]
                    o["thang"] += 1 if r.get("nhan") == "thang" else 0
                    o["n_chinh_xac"] += 1 if chinh_xac else 0
                    o["video"].append({"ma_goi": r["ma_goi"], "nhan": r["nhan"], "nhat_ky": dung or "",
                                       "chinh_xac": chinh_xac})
                else:
                    o["n_ngoai"] += 1
                    o["diem_ngoai"] += r["diem"]
            if not co_log:
                khong[k] = khong.get(k, 0) + 1
    return {"theo_kenh": theo_kenh, "nen_kenh": nen_kenh, "khong_nhat_ky": khong,
            "co_nhat_ky": {k: sorted(v) for k, v in co_nk.items()}}


def rut_hai_bac(r: random.Random, muc: Tuple[float, float], s: float, n: float,
                kappa: float = KAPPA_KENH) -> float:
    """Một lượt rút θ_kh phân tầng: μ ~ Beta(mức danh mục), θ ~ Beta(κμ + điểm, κ(1 − μ) + n − điểm)."""
    mu = r.betavariate(max(muc[0], 1e-6), max(muc[1], 1e-6))
    return r.betavariate(max(kappa * mu + s, 1e-6), max(kappa * (1.0 - mu) + n - s, 1e-6))


def p_tot_nhat_hai_bac(muc: Dict[str, Tuple[float, float]], du: Dict[str, Tuple[float, float]], hat: str,
                       n: int = N_MC, kappa: float = KAPPA_KENH) -> Dict[str, float]:
    """P(θ_kh lớn nhất) rút HAI BẬC (`rut_hai_bac`); `muc[h]` = (a, b) mức danh mục, `du[h]` = (điểm, n) của kênh."""
    ten = sorted(t for t in du if t in muc)
    if not ten:
        return {}
    if len(ten) == 1:
        return {ten[0]: 1.0}
    r = _rng(hat)
    dem = {t: 0 for t in ten}
    for _ in range(n):
        tot, gt = -1.0, ten[0]
        for t in ten:
            x = rut_hai_bac(r, muc[t], du[t][0], du[t][1], kappa)
            if x > tot:
                tot, gt = x, t
        dem[gt] += 1
    return {t: round(dem[t] / float(n), 4) for t in ten}


def hau_nghiem(cau_noi: Dict[str, Any], gt_ds: Sequence[str], kenh_ds: Sequence[str],
               tien_nghiem: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict[str, Any]:
    """Beta phân tầng + P(tốt nhất) — xem đầu tệp. Trả `{"g": ..., "chung": {gt: …}, "theo_kenh": {k: {gt: …}}}`.

    `tien_nghiem` = `{gt: (m₁, w₁)}` (tầng 1 công bằng, `tien_nghiem_tang1`) — cộng w₁ video giả tỉ lệ m₁ vào mức danh
    mục của giả thuyết; None/thiếu = không có. P(tốt nhất) chỉ so giữa các giả thuyết CÓ nhật ký bóng (của kênh ấy / ở
    bất kỳ kênh nào cho mức chung) — giả thuyết chưa từng chạy (vd. H-AI khi chưa có ví) không có gì để so, chỉ in hậu
    nghiệm tiên nghiệm, `p_tot_nhat = None`. Khi `cau_noi` không mang `co_nhat_ky` (gọi tay) thì mọi giả thuyết đều được
    so. P(tốt nhất) theo kênh rút hai bậc (`p_tot_nhat_hai_bac`)."""
    co_nk = cau_noi.get("co_nhat_ky")
    co_chung = set(gt_ds) if co_nk is None else {g for ds in co_nk.values() for g in ds}
    nen = cau_noi.get("nen_kenh") or {}
    S = sum(float(x.get("diem") or 0) for x in nen.values())
    N = sum(float(x.get("n") or 0) for x in nen.values())
    g = (S + 1.0) / (N + 2.0)
    tk = cau_noi.get("theo_kenh") or {}
    chung: Dict[str, Dict[str, Any]] = {}
    mu: Dict[str, float] = {}
    for gt in gt_ds:
        s = sum(float((tk.get(k) or {}).get(gt, {}).get("diem") or 0) for k in tk)
        n = sum(float((tk.get(k) or {}).get(gt, {}).get("n") or 0) for k in tk)
        m1, w1 = (tien_nghiem or {}).get(gt) or (g, 0.0)
        a, b = KAPPA_CHUNG * g + w1 * m1 + s, KAPPA_CHUNG * (1 - g) + w1 * (1 - m1) + n - s
        mu[gt] = a / (a + b)
        chung[gt] = {"n": int(n), "diem": round(s, 2),
                     "thang": int(sum(int((tk.get(k) or {}).get(gt, {}).get("thang") or 0) for k in tk)),
                     "n_chinh_xac": int(sum(int((tk.get(k) or {}).get(gt, {}).get("n_chinh_xac") or 0) for k in tk)),
                     "a": round(a, 3), "b": round(b, 3), "tb": round(mu[gt], 3), "ci90": ci90(a, b),
                     "tang1_m": round(m1, 3), "tang1_w": w1}
    pc = p_tot_nhat({gt: (chung[gt]["a"], chung[gt]["b"]) for gt in gt_ds if gt in co_chung}, "chung")
    for gt in gt_ds:
        chung[gt]["p_tot_nhat"] = pc.get(gt)
        chung[gt]["co_nhat_ky"] = gt in co_chung
    theo_kenh: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for k in kenh_ds:
        m: Dict[str, Dict[str, Any]] = {}
        for gt in gt_ds:
            o = (tk.get(k) or {}).get(gt) or {}
            s, n = float(o.get("diem") or 0), float(o.get("n") or 0)
            a, b = KAPPA_KENH * mu[gt] + s, KAPPA_KENH * (1 - mu[gt]) + n - s
            no, so_ = float(o.get("n_ngoai") or 0), float(o.get("diem_ngoai") or 0)
            m[gt] = {"n": int(n), "diem": round(s, 2), "thang": int(o.get("thang") or 0),
                     "n_chinh_xac": int(o.get("n_chinh_xac") or 0), "cho": int(o.get("cho") or 0), "a": round(a, 3),
                     "b": round(b, 3), "tb": round(a / (a + b), 3), "ci90": ci90(a, b),
                     "ti_le_tho": round(s / n, 3) if n else None, "n_ngoai": int(no),
                     "ti_le_ngoai": round(so_ / no, 3) if no else None, "video": o.get("video") or []}
        co_k = set(gt_ds) if co_nk is None else set(co_nk.get(k) or [])
        pk = p_tot_nhat_hai_bac({gt: (chung[gt]["a"], chung[gt]["b"]) for gt in gt_ds},
                                {gt: (float(m[gt]["diem"]), float(m[gt]["n"])) for gt in gt_ds if gt in co_k},
                                "kenh:" + k)
        for gt in gt_ds:
            m[gt]["p_tot_nhat"] = pk.get(gt)
            m[gt]["co_nhat_ky"] = gt in co_k
            m[gt]["luat"] = _luat(m[gt]) if gt in co_k else "chưa chạy bóng"
        theo_kenh[k] = m
    return {"g": round(g, 3), "n_nen": int(N), "chung": chung, "theo_kenh": theo_kenh}


def _luat(o: Dict[str, Any]) -> str:
    """Nhãn luật quyết (CHỈ IN — đợt 2 mới áp): dẫn đầu / loại / chưa đủ n."""
    if o["n"] < N_QUYET:
        return "chưa đủ n ({0}/{1})".format(o["n"], N_QUYET)
    p = o.get("p_tot_nhat") or 0.0
    if p >= P_DAN_DAU:
        return "dẫn đầu"
    if p < P_LOAI:
        return "ứng viên loại"
    return "đang so"


# ── bảng xếp hạng ───────────────────────────────────────────────────────────

def duong_bang(goc: str) -> str:
    return os.path.join(c.thu_muc_chung(goc), c.TEP_BANG_XEP_HANG)


def kenh_phong_thi_nghiem(goc: str) -> List[str]:
    """Kênh phòng thí nghiệm chạy: kênh có nhóm (như chủ quyền vùng), bỏ bản thử `-vN`; không có nhóm → mọi kênh có
    sổ content."""
    try:
        from .. import chu_quyen_vung as cqv  # noqa: PLC0415

        ds = cqv.cac_kenh(goc)
    except Exception:  # noqa: BLE001
        ds = []
    if ds:
        return ds
    try:
        from ..kenh import liet_ke_kenh  # noqa: PLC0415

        return [k for k in liet_ke_kenh(goc)
                if os.path.isfile(os.path.join(c.thu_muc_nghien_cuu(goc, k), "content.csv"))]
    except Exception:  # noqa: BLE001
        return []


def _g_danh_muc(nen_kenh: Dict[str, Any]) -> float:
    S = sum(float(x.get("diem") or 0) for x in nen_kenh.values())
    N = sum(float(x.get("n") or 0) for x in nen_kenh.values())
    return (S + 1.0) / (N + 2.0)


def chay(goc: str, *, kenh_ds: Optional[Sequence[str]] = None, ghi: bool = True,
         log: Any = None, so_sanh_cu: bool = False, ap_luat: bool = True) -> Dict[str, Any]:
    """Tính lại bảng xếp hạng (tầng 1 công bằng + tầng 2 + hậu nghiệm có tiên nghiệm tầng 1) từ nhật ký bóng, ảnh chụp
    kho và kết quả sản xuất; ghi `workspace/phong-thi-nghiem/bang-xep-hang.json`, một dòng lịch sử
    (`lich-su-xep-hang.jsonl`, mỗi ngày một dòng — để báo cáo não in độ thay đổi) rồi áp LUẬT QUYẾT (`luat.ap_dung`:
    dẫn đầu / loại / tốt nghiệp, ghi sổ quyết định). `so_sanh_cu=True` thêm `tang1_cu` (cách đo đợt 1, để so)."""
    from . import gia_thuyet as gtm  # noqa: PLC0415
    from . import nhat_ky  # noqa: PLC0415

    kenh_ds = list(kenh_ds or kenh_phong_thi_nghiem(goc))
    reg, k = gtm.nap(goc, ghi=ghi)
    hien = {g["id"]: g["phien_ban"] for g in reg}
    con = [g["id"] for g in reg if g["trang_thai"] != gtm.LOAI]
    tu1 = c.cong_ngay(c.hom_nay(), -NGAY_TANG_1)
    logs = nhat_ky.doc(goc, kenh=kenh_ds)
    logs_hien = [x for x in logs if hien.get(x.get("gt")) == int(x.get("pb") or 1)]
    logs_1 = [x for x in logs_hien if x["ngay"] >= tu1]
    t1 = tang_thi_truong_cong_bang(goc, logs_1, kenh_ds, reg)
    sx = {}
    for kk in kenh_ds:
        try:
            sx[kk] = ket_qua_san_xuat(goc, kk)
        except Exception as loi:  # noqa: BLE001
            sx[kk] = []
            if log:
                log("  phòng thí nghiệm: không đọc được kết quả sản xuất {0}: {1}".format(kk, str(loi)[:100]))
    t2 = tang_cau_noi(sx, logs_hien, {g: hien[g] for g in con})
    tn = tien_nghiem_tang1(t1, _g_danh_muc(t2["nen_kenh"]), con)
    hn = hau_nghiem(t2, con, kenh_ds, tien_nghiem=tn)
    hn["co_nhat_ky"] = t2.get("co_nhat_ky") or {}
    gan = c.cong_ngay(c.hom_nay(), -LUI_NHAT_KY)
    co_gan: Dict[str, List[str]] = {}
    ngay_bong: Dict[str, Dict[str, int]] = {}
    ngay_bong_set: Dict[Tuple[str, str], Set[str]] = {}
    for x in logs_hien:
        if not x.get("top"):
            continue
        ngay_bong_set.setdefault((x["kenh"], x["gt"]), set()).add(x["ngay"])
        if x["ngay"] >= gan:     # chỉ giả thuyết THẬT SỰ có ứng viên gần đây mới chọn được khe
            co_gan.setdefault(x["kenh"], [])
            if x["gt"] not in co_gan[x["kenh"]]:
                co_gan[x["kenh"]].append(x["gt"])
    for (kk, gt), ds in ngay_bong_set.items():
        ngay_bong.setdefault(kk, {})[gt] = len(ds)
    bang = {"phien_ban": 2, "luc": c.luc_iso(), "ngay": c.hom_nay(), "k": k, "kenh": kenh_ds,
            "gia_thuyet": {g["id"]: {"mo_ta": g.get("mo_ta", ""), "trang_thai": g["trang_thai"],
                                     "phien_ban": g["phien_ban"], "loai": g["loai"],
                                     "tao_boi": g.get("tao_boi", ""), "tao_luc": g.get("tao_luc", "")} for g in reg},
            "tham_so": {"kappa_chung": KAPPA_CHUNG, "kappa_kenh": KAPPA_KENH, "n_mc": N_MC,
                        "lui_nhat_ky": LUI_NHAT_KY, "cua_so_tt": CUA_SO_TT, "nguong_tang_tt": NGUONG_TANG_TT,
                        "p_dan_dau": P_DAN_DAU, "p_loai": P_LOAI, "n_quyet": N_QUYET, "kham_pha": KHAM_PHA,
                        "kq_chinh": KQ_CHINH, "kappa_tang1": KAPPA_TANG1, "delta_tang1": DELTA_TANG1,
                        "thang_tang1": THANG_TANG1, "n_tang1": N_TANG1_TOI_THIEU},
            "so_nhat_ky": len(logs_hien), "nhat_ky_gan": co_gan, "ngay_bong": ngay_bong,
            "tang1": t1, "tien_nghiem_tang1": {gt: {"m": m, "w": w} for gt, (m, w) in tn.items()},
            "tang2": {"nen_kenh": t2["nen_kenh"], "khong_nhat_ky": t2["khong_nhat_ky"], **hn}}
    if so_sanh_cu:
        bang["tang1_cu"] = tang_thi_truong(goc, logs_1, kenh_ds)
    if ap_luat:
        try:
            from . import luat  # noqa: PLC0415

            bang["quyet_dinh"] = luat.ap_dung(goc, bang, ghi=ghi, log=log)
        except Exception as loi:  # noqa: BLE001 — luật hỏng không được làm mất bảng xếp hạng
            if log:
                log("  phòng thí nghiệm: áp luật quyết hỏng: {0}".format(str(loi)[:160]))
    if ghi:
        c.ghi_json(duong_bang(goc), bang)
        try:
            ghi_lich_su(goc, bang)
        except OSError:
            pass
    return bang


TEP_LICH_SU = "lich-su-xep-hang.jsonl"


def tom_bang(bang: Dict[str, Any]) -> Dict[str, Any]:
    """Ảnh gọn của bảng (mỗi kênh × giả thuyết: n, điểm, TB, P(tốt nhất)) — dòng lịch sử."""
    t2 = bang.get("tang2") or {}

    def gon(m: Dict[str, Any]) -> Dict[str, List[Any]]:
        return {gt: [o.get("n"), o.get("diem"), o.get("tb"), o.get("p_tot_nhat")] for gt, o in (m or {}).items()}
    return {"ngay": bang.get("ngay") or str(bang.get("luc") or "")[:10], "luc": bang.get("luc"),
            "chung": gon(t2.get("chung") or {}),
            "kenh": {k: gon(m) for k, m in (t2.get("theo_kenh") or {}).items()}}


def ghi_lich_su(goc: str, bang: Dict[str, Any]) -> None:
    """Một dòng/ngày (lần tính cuối trong ngày THAY dòng cùng ngày — đọc lại, bỏ dòng cùng ngày, ghi đè nguyên tử)."""
    p = os.path.join(c.thu_muc_chung(goc), TEP_LICH_SU)
    moi = tom_bang(bang)
    cu = [x for x in c.doc_jsonl(p) if x.get("ngay") != moi["ngay"]][-120:]
    c.ghi_nguyen_tu(p, "".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in cu + [moi]))


def doc_lich_su(goc: str) -> List[Dict[str, Any]]:
    return c.doc_jsonl(os.path.join(c.thu_muc_chung(goc), TEP_LICH_SU))


def doc_bang(goc: str) -> Dict[str, Any]:
    du = c.doc_json(duong_bang(goc), {}) or {}
    return du if isinstance(du, dict) else {}


def posterior(goc: str, kenh: str, *, bang: Optional[Dict[str, Any]] = None) -> Dict[str, Tuple[float, float]]:
    """`{giả thuyết: (a, b)}` hậu nghiệm Beta của (kênh × giả thuyết) — kênh chưa có trong bảng → mức chung."""
    bang = bang if bang is not None else doc_bang(goc)
    t2 = bang.get("tang2") or {}
    m = (t2.get("theo_kenh") or {}).get(kenh) or t2.get("chung") or {}
    return {gt: (float(o["a"]), float(o["b"])) for gt, o in m.items() if "a" in o and "b" in o}


def chon_gia_thuyet_cho_khe(goc: str, kenh: str, *, rng: Optional[random.Random] = None,
                            kham_pha: float = KHAM_PHA, bang: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """KHUNG đợt 1 (giữ cho bài kiểm cũ / dòng lệnh `--khe`; sản xuất đợt 2 dùng `chia_khe.phan_bo` — rút hai bậc, cửa
    giả thuyết mới, luật quyết): chọn giả thuyết cho MỘT khe sản xuất của kênh bằng Thompson sampling
    trên hậu nghiệm (kênh × giả thuyết), sàn khám phá `kham_pha` cho giả thuyết không dẫn đầu. Chỉ xét giả thuyết chưa
    bị loại và có nhật ký bóng (top không rỗng) của kênh trong `LUI_NHAT_KY` ngày gần nhất — chạy được thật, có ứng
    viên để giao cho khe (`nhat_ky.moi_nhat`). Trả
    `{gia_thuyet, cach: "thompson"|"kham_pha"|"khong_co", dan_dau, rut, p_tot_nhat, ly_do}`."""
    bang = bang if bang is not None else doc_bang(goc)
    hn = posterior(goc, kenh, bang=bang)
    tt = {g: (o or {}).get("trang_thai") for g, o in (bang.get("gia_thuyet") or {}).items()}
    co_loc = "nhat_ky_gan" in bang
    gan = set((bang.get("nhat_ky_gan") or {}).get(kenh) or [])
    du = sorted(g for g in hn if tt.get(g) != "loai" and (not co_loc or g in gan))
    if not du:
        return {"gia_thuyet": "", "cach": "khong_co", "dan_dau": "", "rut": {}, "p_tot_nhat": {},
                "ly_do": "chưa có giả thuyết nào có hậu nghiệm/nhật ký cho kênh này"}
    r = rng or _rng("khe:{0}:{1}".format(kenh, c.luc_iso()))
    m = ((bang.get("tang2") or {}).get("theo_kenh") or {}).get(kenh) or (bang.get("tang2") or {}).get("chung") or {}
    p = {g: float((m.get(g) or {}).get("p_tot_nhat") or 0.0) for g in du}
    dan_dau = max(du, key=lambda g: (p[g], hn[g][0] / (hn[g][0] + hn[g][1]), g))
    rut = {g: r.betavariate(max(hn[g][0], 1e-6), max(hn[g][1], 1e-6)) for g in du}
    if len(du) > 1 and r.random() < kham_pha:
        khac = [g for g in du if g != dan_dau]
        g = khac[int(r.random() * len(khac)) % len(khac)]
        return {"gia_thuyet": g, "cach": "kham_pha", "dan_dau": dan_dau, "rut": rut, "p_tot_nhat": p,
                "ly_do": "khám phá {0:.0%}: chọn giả thuyết không dẫn đầu".format(kham_pha)}
    g = max(du, key=lambda x: (rut[x], x))
    return {"gia_thuyet": g, "cach": "thompson", "dan_dau": dan_dau, "rut": rut, "p_tot_nhat": p,
            "ly_do": "Thompson: lượt rút cao nhất ({0:.3f})".format(rut[g])}
