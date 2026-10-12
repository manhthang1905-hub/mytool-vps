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
"""

from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import io
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
#: Luật quyết (đợt 2 sẽ áp — ở đây chỉ in): dẫn đầu P ≥ 0,8 với n ≥ 8; loại P < 0,05 với n ≥ 8.
P_DAN_DAU, P_LOAI, N_QUYET = 0.8, 0.05, 8
KHAM_PHA = 0.15
DIEM_NHAN = {"thang": 1.0, "trung_binh": 0.5, "truot": 0.0}


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
        tot = None
        for t, v in ds:
            if t <= sau or abs(t - t_muc) > dung_sai:
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
                   "diem": DIEM_NHAN.get(nhan), "cong_thuc": r.get("cong_thuc", "")})
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
    for k, ds in san_xuat.items():
        nk = nen_kenh.setdefault(k, {"n": 0, "diem": 0.0, "cho": 0})
        for r in ds:
            if r["diem"] is None:
                nk["cho"] += 1
            else:
                nk["n"] += 1
                nk["diem"] += r["diem"]
            co_log = False
            for gt in gts:
                ngay_log = top.get((k, gt)) or {}
                dung = None
                for i in range(1, LUI_NHAT_KY + 1):
                    d = c.cong_ngay(r["ngay"], -i)
                    if d in ngay_log:
                        dung = d
                        break
                if dung is None:
                    continue
                co_log = True
                o = theo_kenh.setdefault(k, {}).setdefault(gt, {"n": 0, "diem": 0.0, "n_ngoai": 0, "diem_ngoai": 0.0,
                                                               "cho": 0, "video": []})
                trong = r["ma"] in ngay_log[dung]
                if r["diem"] is None:
                    if trong:
                        o["cho"] += 1
                    continue
                if trong:
                    o["n"] += 1
                    o["diem"] += r["diem"]
                    o["video"].append({"ma_goi": r["ma_goi"], "nhan": r["nhan"], "nhat_ky": dung})
                else:
                    o["n_ngoai"] += 1
                    o["diem_ngoai"] += r["diem"]
            if not co_log:
                khong[k] = khong.get(k, 0) + 1
    return {"theo_kenh": theo_kenh, "nen_kenh": nen_kenh, "khong_nhat_ky": khong,
            "co_nhat_ky": {k: sorted(v) for k, v in co_nk.items()}}


def hau_nghiem(cau_noi: Dict[str, Any], gt_ds: Sequence[str], kenh_ds: Sequence[str]) -> Dict[str, Any]:
    """Beta phân tầng + P(tốt nhất) — xem đầu tệp. Trả `{"g": ..., "chung": {gt: …}, "theo_kenh": {k: {gt: …}}}`.

    P(tốt nhất) chỉ so giữa các giả thuyết CÓ nhật ký bóng (của kênh ấy / ở bất kỳ kênh nào cho mức chung) — giả thuyết
    chưa từng chạy (vd. H-AI khi chưa có ví) không có gì để so, chỉ in hậu nghiệm tiên nghiệm, `p_tot_nhat = None`.
    Khi `cau_noi` không mang `co_nhat_ky` (gọi tay) thì mọi giả thuyết đều được so."""
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
        a, b = KAPPA_CHUNG * g + s, KAPPA_CHUNG * (1 - g) + n - s
        mu[gt] = a / (a + b)
        chung[gt] = {"n": int(n), "diem": round(s, 2), "a": round(a, 3), "b": round(b, 3), "tb": round(mu[gt], 3),
                     "ci90": ci90(a, b)}
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
            m[gt] = {"n": int(n), "diem": round(s, 2), "cho": int(o.get("cho") or 0), "a": round(a, 3),
                     "b": round(b, 3), "tb": round(a / (a + b), 3), "ci90": ci90(a, b),
                     "ti_le_tho": round(s / n, 3) if n else None, "n_ngoai": int(no),
                     "ti_le_ngoai": round(so_ / no, 3) if no else None, "video": o.get("video") or []}
        co_k = set(gt_ds) if co_nk is None else set(co_nk.get(k) or [])
        pk = p_tot_nhat({gt: (m[gt]["a"], m[gt]["b"]) for gt in gt_ds if gt in co_k}, "kenh:" + k)
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


def chay(goc: str, *, kenh_ds: Optional[Sequence[str]] = None, ghi: bool = True,
         log: Any = None) -> Dict[str, Any]:
    """Tính lại bảng xếp hạng (tầng 1 + 2) từ nhật ký bóng, ảnh chụp kho và kết quả sản xuất; ghi
    `workspace/phong-thi-nghiem/bang-xep-hang.json`."""
    from . import gia_thuyet as gtm  # noqa: PLC0415
    from . import nhat_ky  # noqa: PLC0415

    kenh_ds = list(kenh_ds or kenh_phong_thi_nghiem(goc))
    reg, k = gtm.nap(goc, ghi=ghi)
    hien = {g["id"]: g["phien_ban"] for g in reg}
    con = [g["id"] for g in reg if g["trang_thai"] != gtm.LOAI]
    tu1 = c.cong_ngay(c.hom_nay(), -NGAY_TANG_1)
    logs = nhat_ky.doc(goc, kenh=kenh_ds)
    logs_hien = [x for x in logs if hien.get(x.get("gt")) == int(x.get("pb") or 1)]
    t1 = tang_thi_truong(goc, [x for x in logs_hien if x["ngay"] >= tu1], kenh_ds)
    sx = {}
    for kk in kenh_ds:
        try:
            sx[kk] = ket_qua_san_xuat(goc, kk)
        except Exception as loi:  # noqa: BLE001
            sx[kk] = []
            if log:
                log("  phòng thí nghiệm: không đọc được kết quả sản xuất {0}: {1}".format(kk, str(loi)[:100]))
    t2 = tang_cau_noi(sx, logs_hien, {g: hien[g] for g in con})
    hn = hau_nghiem(t2, con, kenh_ds)
    hn["co_nhat_ky"] = t2.get("co_nhat_ky") or {}
    gan = c.cong_ngay(c.hom_nay(), -LUI_NHAT_KY)
    co_gan: Dict[str, List[str]] = {}
    for x in logs_hien:
        if x["ngay"] >= gan and x.get("top"):     # chỉ giả thuyết THẬT SỰ có ứng viên gần đây mới chọn được khe
            co_gan.setdefault(x["kenh"], [])
            if x["gt"] not in co_gan[x["kenh"]]:
                co_gan[x["kenh"]].append(x["gt"])
    bang = {"phien_ban": 1, "luc": c.luc_iso(), "k": k, "kenh": kenh_ds,
            "gia_thuyet": {g["id"]: {"mo_ta": g.get("mo_ta", ""), "trang_thai": g["trang_thai"],
                                     "phien_ban": g["phien_ban"], "loai": g["loai"]} for g in reg},
            "tham_so": {"kappa_chung": KAPPA_CHUNG, "kappa_kenh": KAPPA_KENH, "n_mc": N_MC,
                        "lui_nhat_ky": LUI_NHAT_KY, "cua_so_tt": CUA_SO_TT, "nguong_tang_tt": NGUONG_TANG_TT,
                        "p_dan_dau": P_DAN_DAU, "p_loai": P_LOAI, "n_quyet": N_QUYET, "kham_pha": KHAM_PHA},
            "so_nhat_ky": len(logs_hien), "nhat_ky_gan": co_gan,
            "tang1": t1, "tang2": {"nen_kenh": t2["nen_kenh"], "khong_nhat_ky": t2["khong_nhat_ky"], **hn}}
    if ghi:
        c.ghi_json(duong_bang(goc), bang)
    return bang


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
    """KHUNG cho đợt 2 (CHƯA nối vào sản xuất): chọn giả thuyết cho MỘT khe sản xuất của kênh bằng Thompson sampling
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
