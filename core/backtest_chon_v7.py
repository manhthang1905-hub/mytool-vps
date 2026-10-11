"""BACKTEST CHỈ ĐỌC luật chọn V7 phiên bản 5 (12/10/2026) so với luật cũ, trên lịch sử thật của máy.

    python -m core.backtest_chon_v7 [--goc <thư mục gốc>] [--kenh K ...]

KHÔNG GHI gì vào cây sống: chạy trong tiến trình riêng, vá trong bộ nhớ `cong_thuc_v7.nap_cau_hinh` (không ghi cấu
hình), nhật ký lọc `chi-so`, và cổng "đã làm" (để nguồn của video đã làm được chấm lại). KHÔNG import file này từ mã
sản xuất (chỉ chạy như lệnh).

A) PHẢN THỰC HÔM NAY: nguồn của mỗi video đã làm bị luật cũ / luật mới loại ở cổng nào, hay được chấm bao nhiêu điểm
   → so với kết quả thật (hiển thị lớn nhất đã chụp; "hit" ≥ 5.000 như chẩn đoán).
B) THEO NGÀY: báo cáo V7 của ngày TRƯỚC ngày chọn (`cham-v7-<D-1>.csv`), chấm lại theo trọng số mới (dựng từ cột báo
   cáo), bỏ nguồn nhóm đã làm trước ngày chọn → nguồn thật sự được chọn nằm trong top luật mới không; luật mới sẽ chọn
   nguồn nào (top-1) và kết cục khi nhóm có làm nguồn ấy. Dòng bị cổng loại ngày ấy KHÔNG có trong báo cáo, nên phần B
   đánh giá THẤP luật mới (không thấy các nguồn luật mới nhận thêm) — phần A bù chỗ đó.
Giới hạn: n nhỏ; chỉ thấy kết quả của nguồn đã sản xuất (thiên lệch chọn mẫu); hạng phản thực là hạng HÔM NAY.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import math
import os
import re
import statistics
import sys
from typing import Any, Dict, List, Optional

HIT = 5000


def _f(x: Any) -> str:
    return "?" if x is None else "{0:,.0f}".format(x).replace(",", ".")


def fisher(a: int, b: int, c: int, d: int) -> float:
    """P(X ≥ a) một phía cho bảng [[a, b], [c, d]] (siêu bội)."""
    n1, n2, k = a + b, c + d, a + c

    def comb(x: int, y: int) -> int:
        return math.comb(x, y) if 0 <= y <= x else 0
    tong = comb(n1 + n2, k)
    return sum(comb(n1, i) * comb(n2, k - i) for i in range(a, min(n1, k) + 1)) / tong if tong else 1.0


def spearman(x: List[float], y: List[float]) -> Optional[float]:
    def hang(a: List[float]) -> List[float]:
        o = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and a[o[j + 1]] == a[o[i]]:
                j += 1
            for t in range(i, j + 1):
                r[o[t]] = (i + j) / 2.0
            i = j + 1
        return r
    if len(x) < 3:
        return None
    rx, ry = hang(x), hang(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    tu = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    mau = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return tu / mau if mau else None


def nhom(ds: List[Dict[str, Any]], ten: str) -> str:
    hs = [r["hien_thi"] or 0 for r in ds]
    n = len(ds)
    hit = sum(1 for h in hs if h >= HIT)
    return "{0:<46} n={1:>3}  hit≥5k {2:>2} ({3:>3.0%})  ≥10k {4:>2}  trung vị {5:>7}".format(
        ten, n, hit, hit / n if n else 0, sum(1 for h in hs if h >= 10000), _f(statistics.median(hs) if hs else 0))


def _so(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _phut(t: Any) -> Optional[float]:
    try:
        g = 0
        for x in str(t or "").split(":"):
            g = g * 60 + int(x)
        return g / 60.0
    except ValueError:
        return None


def diem_moi_tu_dong(r: Dict[str, str]) -> float:
    """Điểm phiên bản 5 dựng lại từ cột báo cáo CŨ (trọng số cũ 30/25/20/15/10, khuôn 0,5/0,2): Nổ × 1,5 (trừ kênh yếu
    giữ 5), Đang lên 0, độ dài 12–21 → 9 (8–30 → 2,25), dạng chân dung 5 → 6 (khác 2 → 2,25), giữ khoản trừ AI."""
    cum, pool, no, len_, khuon, xh = (_so(r.get(c)) or 0.0 for c in ("Cụm", "Bảng đề xuất", "Nổ", "Đang lên",
                                                                         "Khuôn", "Xu hướng"))
    diem = _so(r.get("Điểm")) or 0.0
    tru = min(0.0, diem - max(0.0, min(100.0, cum + pool + no + len_ + khuon + xh)))
    yeu = "(kênh yếu)" in str(r.get("Lý do") or "")
    no_moi = no * 1.5 + (2.5 if yeu and no > 0 else 0.0)
    ph = _phut(r.get("Dài"))
    dai_cu = 5.0 if ph is not None and 12 <= ph <= 21 else 2.0 if ph is not None and 8 <= ph <= 30 else 0.0
    dang_cu = max(0.0, khuon - dai_cu)
    dang_moi = 6.0 if dang_cu >= 4.5 else 2.25 if dang_cu >= 1.5 else 0.0
    dai_moi = 9.0 if dai_cu == 5.0 else 2.25 if dai_cu == 2.0 else 0.0
    return max(0.0, min(100.0, cum + pool + no_moi + dai_moi + dang_moi + xh)) + tru


def _va_bo_nho(v7: Any) -> Any:
    from . import doi_thu_kenh as so  # noqa: PLC0415
    from .chi_so_ytb import loc_video  # noqa: PLC0415

    goc_nap = v7.nap_cau_hinh

    def nap(goc: str, kenh: str, *, ghi_neu_thieu: bool = True) -> Any:
        return goc_nap(goc, kenh, ghi_neu_thieu=False)

    v7.nap_cau_hinh = nap
    v7.doc_ma_da_lam = lambda *_a, **_k: {}
    so.COT_DA_LAM = "<<khong-co-cot>>"
    loc_video.but_nhat_ky = lambda *_a, **_k: (lambda _d: None)
    return v7._cho_nang_cap  # noqa: SLF001


def ket_cuc(goc: str, k: str) -> Dict[str, Dict[str, Any]]:
    from . import ho_so_video  # noqa: PLC0415
    from .chien_luoc import ket_qua  # noqa: PLC0415

    vm, _ = ket_qua.video_kenh(goc, k)
    hs = ket_qua.ho_so_theo_goi(goc, k)
    ra: Dict[str, Dict[str, Any]] = {}
    for ma_goi, g in ho_so_video.nguon_cua_goi(goc, k).items():
        if g.get("bo"):
            continue
        v = vm.get(str((hs.get(ma_goi) or {}).get("video_id") or ""))
        if v is None:
            continue
        gia = max((d.hien_thi or 0.0) for d in v.chuoi.diem) if getattr(v, "chuoi", None) and v.chuoi.diem else None
        ra[ma_goi] = {"nguon": str(g.get("ma") or ""), "ngay": g.get("ngay") or "", "nhan": v.nhan_thang,
                      "hien_thi": gia, "kenh": k, "ma_goi": ma_goi}
    return ra


def phan_a(goc: str, kenh_ds: List[str], phan_phoi: List[str]) -> List[Dict[str, Any]]:
    from . import cong_thuc_v7 as v7  # noqa: PLC0415

    cho_goc = _va_bo_nho(v7)

    def cham(k: str, moi: bool) -> Any:
        v7._cho_nang_cap = (lambda *a, **kw: True) if moi else (lambda *a, **kw: False)  # noqa: SLF001
        try:
            kq = v7.cham(goc, k)
        finally:
            v7._cho_nang_cap = cho_goc  # noqa: SLF001
        return {d.ma: (i + 1, d) for i, d in enumerate(kq.ung_vien)}, {d.ma: d.bi_loai for d in kq.bi_loai}

    print("=== A. Phản thực hôm nay (cổng đã làm tắt) — nguồn của video đã làm ===")
    tat_ca: List[Dict[str, Any]] = []
    for k in kenh_ds:
        kc = ket_cuc(goc, k)
        h_cu, l_cu = cham(k, False)
        h_moi, l_moi = cham(k, True)
        for r in kc.values():
            m = r["nguon"]
            tat_ca.append(dict(r, cu=("loai:" + l_cu[m]) if m in l_cu else (h_cu[m][0] if m in h_cu else None),
                               moi=("loai:" + l_moi[m]) if m in l_moi else (h_moi[m][0] if m in h_moi else None),
                               diem_moi=h_moi[m][1].diem if m in h_moi else None,
                               diem_cu=h_cu[m][1].diem if m in h_cu else None,
                               vuot=h_moi[m][1].vuot if m in h_moi else None))
    co_so = [r for r in tat_ca if r["hien_thi"] is not None]
    for ten, tap in (("{0} kênh".format(len(kenh_ds)), co_so),
                     ("{0} kênh có phân phối".format(len(phan_phoi)), [r for r in co_so if r["kenh"] in phan_phoi])):
        print("-- " + ten)
        print(nhom(tap, "mọi video có số"))
        print(nhom([r for r in tap if isinstance(r["cu"], str)], "LUẬT CŨ loại ở cổng"))
        print(nhom([r for r in tap if isinstance(r["moi"], str)], "LUẬT MỚI loại ở cổng"))
        nhan = [r for r in tap if isinstance(r["cu"], str) and not isinstance(r["moi"], str)]
        con = [r for r in tap if isinstance(r["moi"], str)]
        print(nhom(nhan, "luật cũ loại → luật mới NHẬN"))
        a = sum(1 for r in nhan if (r["hien_thi"] or 0) >= HIT)
        b = sum(1 for r in con if (r["hien_thi"] or 0) >= HIT)
        print("   Fisher một phía (mới nhận vs luật mới vẫn loại): p = {0:.3f}".format(
            fisher(a, len(nhan) - a, b, len(con) - b)))
        sc = [r for r in tap if r["diem_moi"] is not None]
        sc2 = [r for r in tap if r["diem_cu"] is not None]
        rho = spearman([r["diem_moi"] for r in sc], [math.log1p(r["hien_thi"]) for r in sc])
        rho2 = spearman([r["diem_cu"] for r in sc2], [math.log1p(r["hien_thi"]) for r in sc2])
        print("   Spearman điểm ↔ log hiển thị: luật cũ ρ={0} (n={1}) · luật mới ρ={2} (n={3})".format(
            None if rho2 is None else round(rho2, 2), len(sc2), None if rho is None else round(rho, 2), len(sc)))
        if sc:
            tv = statistics.median([r["diem_moi"] for r in sc])
            print(nhom([r for r in sc if r["diem_moi"] >= tv], "   điểm mới ≥ trung vị ({0:g})".format(tv)))
            print(nhom([r for r in sc if r["diem_moi"] < tv], "   điểm mới < trung vị"))
            print(nhom([r for r in sc if (r["vuot"] or 0) >= 8], "   gấp ≥ 8×"))
            print(nhom([r for r in sc if (r["vuot"] or 0) < 8], "   gấp < 8×"))
    for ten_lo, chon in (("luật cũ loại → luật mới nhận, theo lý do CŨ",
                          lambda r: isinstance(r["cu"], str) and not isinstance(r["moi"], str)),
                         ("luật mới vẫn loại, theo lý do", lambda r: isinstance(r["moi"], str))):
        print("-- " + ten_lo + ":")
        lo: Dict[str, List[Dict[str, Any]]] = {}
        for r in co_so:
            if chon(r):
                ly = r["cu"] if not isinstance(r["moi"], str) else r["moi"]
                lo.setdefault(re.sub(r"\(.*", "", ly[5:]).strip(), []).append(r)
        for k, ds in sorted(lo.items(), key=lambda kv: -len(kv[1])):
            print(nhom(ds, "   " + k[:42]))
    return tat_ca


def _bao_cao(goc: str, k: str, ngay: str) -> Optional[List[Dict[str, str]]]:
    p = os.path.join(goc, "CHANNEL", k, "nghien-cuu", "cham-v7-{0}.csv".format(ngay))
    try:
        with io.open(p, encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep))
    except OSError:
        return None


def phan_b(goc: str, kenh_ds: List[str], phan_phoi: List[str], tat_ca: List[Dict[str, Any]]) -> None:
    from . import doi_thu_kenh as so  # noqa: PLC0415
    from . import ho_so_video  # noqa: PLC0415

    print("\n=== B. Theo ngày: báo cáo V7 hôm trước, chấm lại theo trọng số mới ===")
    theo_nguon = {}
    for r in tat_ca:
        theo_nguon.setdefault(r["nguon"], r)
    da_lam_luc: Dict[str, str] = {}
    for k in kenh_ds:
        for g in ho_so_video.nguon_cua_goi(goc, k).values():
            if g.get("ma") and g.get("ngay"):
                da_lam_luc[g["ma"]] = min(da_lam_luc.get(g["ma"], "9"), g["ngay"])
    dong: List[Dict[str, Any]] = []
    dem = {"cu": 0, "moi": 0, "tong": 0}
    chon_moi = []
    for r in tat_ca:
        if not r["ngay"]:
            continue
        d = dt.date.fromisoformat(r["ngay"])
        bc = None
        for lui in range(1, 4):
            bc = _bao_cao(goc, r["kenh"], (d - dt.timedelta(days=lui)).isoformat())
            if bc:
                break
        if not bc:
            continue
        hang_cu = {so.ma_video(x.get("Link") or ""): int(x["Hạng"]) for x in bc}
        moi = [x for x in sorted(bc, key=lambda x: -diem_moi_tu_dong(x))
               if da_lam_luc.get(so.ma_video(x.get("Link") or "") or "", "9") >= r["ngay"]]
        hang_moi = {so.ma_video(x.get("Link") or ""): i + 1 for i, x in enumerate(moi)}
        top = [x for x in moi[:10] if diem_moi_tu_dong(x) >= 20 and (_so(x.get("Gấp")) or 99) >= 3]
        dem["tong"] += 1
        dem["moi"] += 1 if top else 0
        dem["cu"] += 1 if any(x.get("Loại") in ("Làm ngay", "Nên làm") for x in bc) else 0
        dong.append(dict(r, hang_cu=hang_cu.get(r["nguon"]), hang_moi=hang_moi.get(r["nguon"]),
                         top_moi=r["nguon"] in {so.ma_video(x.get("Link") or "") for x in top}))
        if top:
            m1 = so.ma_video(top[0].get("Link") or "")
            chon_moi.append((r, m1, theo_nguon.get(m1), diem_moi_tu_dong(top[0]), top[0].get("Tiêu đề", "")[:40]))
    print("Lượt có báo cáo hôm trước: {0}; lượt có ≥ 1 ứng viên V7 đủ điều kiện: luật cũ (≥ 60) {1} · luật mới "
          "(top-10 + sàn) {2}".format(dem["tong"], dem["cu"], dem["moi"]))
    co = [x for x in dong if x["hien_thi"] is not None]
    for ten, tap in (("{0} kênh".format(len(kenh_ds)), co),
                     ("{0} kênh có phân phối".format(len(phan_phoi)), [x for x in co if x["kenh"] in phan_phoi])):
        print("-- " + ten)
        print(nhom([x for x in tap if x["hang_cu"] and x["hang_cu"] <= 10], "nguồn đã chọn: hạng CŨ 1–10"))
        print(nhom([x for x in tap if x["hang_cu"] and x["hang_cu"] > 10], "nguồn đã chọn: hạng CŨ > 10"))
        print(nhom([x for x in tap if x["top_moi"]], "nguồn đã chọn: ĐỦ ĐIỀU KIỆN luật mới"))
        print(nhom([x for x in tap if x["hang_moi"] and not x["top_moi"]], "nguồn đã chọn: trong bảng, ngoài top mới"))
        print(nhom([x for x in tap if not x["hang_moi"]], "nguồn đã chọn: không có trong bảng hôm trước"))
    trung = [c for c in chon_moi if c[1] == c[0]["nguon"]]
    biet = [c for c in chon_moi if c[2] is not None and c[1] != c[0]["nguon"]]
    print("-- luật mới sẽ chọn (top-1 chưa làm) trên {0} lượt: trùng đúng nguồn đã chọn {1}; khác nguồn mà nhóm có "
          "làm nguồn ấy (biết kết cục) {2}".format(len(chon_moi), len(trung), len(biet)))
    for r, _m1, kq, dm, td in biet:
        print("     {0} {1}: chọn thật {2} → {3} hiển thị | luật mới chọn “{4}” ({5:.0f} điểm) → làm ở {6}: {7}".format(
            r["kenh"], r["ngay"], r["ma_goi"], _f(r["hien_thi"]), td, dm, kq["ma_goi"], _f(kq["hien_thi"])))


def main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.backtest_chon_v7")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p.add_argument("--kenh", action="append", default=[])
    p.add_argument("--phan-phoi", action="append", default=[],
                   help="kênh đã được YouTube phát (nhóm so riêng); mặc định = kênh có trung vị hiển thị ≥ 300")
    a = p.parse_args(argv)
    os.environ["MYTOOL_CHIEN_TRUONG_GHI"] = "0"
    from . import chu_quyen_vung  # noqa: PLC0415

    kenh_ds = a.kenh or [k for k in chu_quyen_vung.cac_kenh(a.goc)]
    if not a.phan_phoi:
        _tk, song, _t = chu_quyen_vung.thong_ke(a.goc, kenh_ds)
        phan_phoi = [k for k in kenh_ds if song.get(k)]
    else:
        phan_phoi = a.phan_phoi
    tat_ca = phan_a(a.goc, kenh_ds, phan_phoi)
    phan_b(a.goc, kenh_ds, phan_phoi, tat_ca)
    return 0


if __name__ == "__main__":
    sys.exit(main())
