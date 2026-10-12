"""Báo cáo: `workspace/chan-doan/phong-thi-nghiem-backtest-<ngày>.md` (chạy ngược) / `phong-thi-nghiem-dot-2-<ngày>.md`
(`--danh-gia --bao-cao`) — đọc bảng xếp hạng + thống kê vũ trụ + chia khe + sổ quyết định."""

from __future__ import annotations

import glob
import os
from typing import Any, Dict, List, Optional, Sequence

from . import _chung as c


def _pt(x: Optional[float]) -> str:
    return "—" if x is None else "{0:.0f}%".format(100.0 * x)


def _ci(ci: Optional[Sequence[float]]) -> str:
    if not ci:
        return ""
    return "[{0:.0f}–{1:.0f}%]".format(100.0 * ci[0], 100.0 * ci[1])


def _so(x: Any) -> str:
    try:
        return "{0:,.0f}".format(float(x)).replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def vu_tru_kenh(goc: str, kenh: str, den: str) -> List[Dict[str, Any]]:
    ra = []
    for p in sorted(glob.glob(os.path.join(c.thu_muc_kenh(goc, kenh), "vu-tru-*.json"))):
        du = c.doc_json(p, {}) or {}
        if isinstance(du, dict) and du.get("ngay") and du["ngay"] <= den:
            ra.append(du)
    return ra


def _nang(x: Optional[float]) -> str:
    return "—" if x is None else "{0:+.0f}".format(100.0 * float(x))


def _phan_vu_tru(goc: str, kenh_ds: Sequence[str], den: str) -> List[str]:
    d: List[str] = []
    d.append("| Kênh | Ngày | Sổ | Kênh đối thủ thật / theo dõi / cả sổ | Sàn cỡ kênh | Bỏ: kênh | Bỏ: video | Vũ trụ | "
             "đối thủ · pool · trang chủ | TB vũ trụ (ngày) |")
    d.append("|---|---|---|---|---|---|---|---|---|---|")
    bo_kenh_ly = ("sổ: kênh bỏ", "sổ: kênh hết", "AI: lạc ngách", "không đăng video dài", "kênh quá nhỏ",
                  "chưa có bằng chứng khán giả", "kênh ngoài sổ đối thủ")
    for k in kenh_ds:
        ds = vu_tru_kenh(goc, k, den)
        if not ds:
            d.append("| {0} | — | — | — | — | — | — | — | — | — |".format(k))
            continue
        x = ds[-1]
        tk = x.get("thong_ke") or {}
        vb = tk.get("video_bo") or {}
        bk = sum(v for ly, v in vb.items() if ly.startswith(bo_kenh_ly))
        bv = sum(v for ly, v in vb.items() if not ly.startswith(bo_kenh_ly))
        tn = tk.get("theo_nguon") or {}
        tb = sum(float((y.get("thong_ke") or {}).get("n_vu_tru") or 0) for y in ds) / len(ds)
        d.append("| {0} | {1} | {2} | {3} / {4} / {5} | {6} | {7} | {8} | **{9}** | {10} · {11} · {12} | {13} ({14}) |"
                 .format(k, x["ngay"], _so(tk.get("n_sach")), tk.get("kenh_dat", 0), tk.get("kenh_theo_doi", "?"),
                         tk.get("kenh_so", 0), _so(tk.get("san_kenh")), _so(bk), _so(bv), _so(tk.get("n_vu_tru")),
                         _so(tn.get("doi_thu", 0)), _so(tn.get("pool", 0)), _so(tn.get("trang_chu", 0)), _so(tb),
                         len(ds)))
    return d


def ghi_dot_2(goc: str, bang: Dict[str, Any], *, kenh_ds: Sequence[str], tu: str = "", den: str = "",
              ngay: Optional[str] = None, ten: str = "phong-thi-nghiem-dot-2") -> str:
    """Báo cáo đợt 2: tầng 1 CÔNG BẰNG (so trước/sau khi có `bang["tang1_cu"]`), tầng 2 (ghi công bóng + chính xác),
    chia khe dự kiến từng kênh, luật quyết đã ghi — `workspace/chan-doan/<ten>-<ngày>.md`."""
    from . import chia_khe  # noqa: PLC0415

    ngay = ngay or c.hom_nay()
    den = den or ngay
    gts = sorted((bang.get("gia_thuyet") or {}).keys())
    con = [g for g in gts if (bang["gia_thuyet"][g] or {}).get("trang_thai") != "loai"]
    t1 = bang.get("tang1") or {}
    cu = bang.get("tang1_cu") or {}
    t2 = bang.get("tang2") or {}
    ts = bang.get("tham_so") or {}
    tn = bang.get("tien_nghiem_tang1") or {}
    ch1, ch2 = t1.get("chung") or {}, t2.get("chung") or {}
    kq = ts.get("kq_chinh", "7n_no")
    d: List[str] = ["# Phòng thí nghiệm chọn content — đợt 2: tầng 1 công bằng, chia khe Thompson, luật quyết ({0})"
                    .format(ngay), ""]
    d.append("Đợt 2 của `workspace/chan-doan/ke-hoach-phong-thi-nghiem-content.md`. Mã: `core/phong_thi_nghiem/` "
             "(`danh_gia` đo, `chia_khe` chia khe sản xuất, `luat` thăng/loại). Bảng máy đọc: `workspace/phong-thi-nghiem/"
             "bang-xep-hang.json`; sổ quyết định `quyet-dinh.jsonl`. Nhật ký bóng: {0} dòng{1}.".format(
                 bang.get("so_nhat_ky", 0), " ({0} → {1})".format(tu, den) if tu else ""))
    d.append("")
    d.append("**Đọc trước.** Tầng 2 vẫn là vài chục video đã phán; mọi ô in n và khoảng tin 90%; luật quyết cần n ≥ {0} "
             "(dẫn đầu P ≥ {1:.0%}, loại P < {2:.0%} và chỉ khi thua một giả thuyết cũng đã đo n ≥ {0}); không bao giờ "
             "hành động khi n ≤ 2.".format(ts.get("n_quyet", 8), ts.get("p_dan_dau", 0.8), ts.get("p_loai", 0.05)))
    d.append("")
    d.append("## 0. Bảng xếp hạng gộp (toàn danh mục)")
    d.append("")
    d.append("| Giả thuyết | Sổ | Tầng 1 công bằng: n lần đầu · NỔ +7n [CI90] | nâng vs rút ngẫu nhiên: vũ trụ / cùng "
             "tầng / cổng | tiên nghiệm m₁ (w) | Tầng 2: n (chính xác) · thắng · điểm | hậu nghiệm [CI90] | P(tốt nhất) |")
    d.append("|---|---|---|---|---|---|---|---|")
    for g in sorted(con, key=lambda x: (-(float((ch2.get(x) or {}).get("p_tot_nhat") or -1)), x)):
        z = (ch1.get(g) or {}).get(kq) or {}
        o = ch2.get(g) or {}
        m = tn.get(g) or {}
        d.append("| {0} | {1} | {2} · {3} {4} | {5} / {6} / {7} | {8} ({9:g}) | {10} ({11}) · {12} · {13} | {14} {15} | "
                 "{16} |".format(
                     g, (bang["gia_thuyet"][g] or {}).get("trang_thai", ""), z.get("n", 0), _pt(z.get("ti_le")),
                     _ci(z.get("ci90")) if z.get("n") else "", _nang(z.get("nang")), _nang(z.get("nang_tang")),
                     _nang(z.get("nang_cong")), _pt(m.get("m")), float(m.get("w") or 0), o.get("n", 0),
                     o.get("n_chinh_xac", 0), o.get("thang", 0), o.get("diem", 0), _pt(o.get("tb")), _ci(o.get("ci90")),
                     _pt(o.get("p_tot_nhat")) if o.get("co_nhat_ky", True) else "chưa chạy bóng"))
    d.append("")
    d.append("## 1. Tầng 1 — TRƯỚC / SAU khi sửa cho công bằng")
    d.append("")
    d.append("TRƯỚC (đợt 1): mỗi ngày một video nằm trong top-10 là một lần đếm (video nằm top 10 ngày = 10 lần, đo từ "
             "những ngày nó đã nổ sẵn), kết quả \"đang lên\" (+1 × trung vị kênh nguồn) và nền = cả vũ trụ — H-POOL/"
             "H-DOT-BIEN chọn video ĐÃ to và còn tăng nên gần như tự thắng. SAU: mỗi video tính MỘT lần — ngày ĐẦU tiên "
             "vào top; kết quả chính NỔ +7 ngày (kiếm thêm ≥ 5 × trung vị kênh nguồn — không là cổng của giả thuyết nào); "
             "so với rút ngẫu nhiên (a) cùng vũ trụ đã lọc, (b) cùng vũ trụ CÙNG Ô gấp × tuổi × đà (còn tăng/ngày) với video "
             "được chọn — số dùng làm tiên nghiệm và sàn —, (c) từ tập qua cổng của chính giả thuyết (thứ hạng thêm được gì).")
    d.append("")
    d.append("| Giả thuyết | TRƯỚC: n (đếm lặp) | đang lên +3n · nâng | NỔ +7n · nâng | SAU: n lần đầu (bỏ lặp) | NỔ +7n "
             "[CI90] | rút ngẫu nhiên vũ trụ → nâng | cùng tầng → nâng | qua cổng → nâng | đang lên +3n: nâng cùng tầng |")
    d.append("|---|---|---|---|---|---|---|---|---|---|")
    for g in con:
        a0 = ((cu.get("chung") or {}).get(g) or {}).get("3n") or {}
        z0 = ((cu.get("chung") or {}).get(g) or {}).get("7n_no") or {}
        z = (ch1.get(g) or {}).get(kq) or {}
        a = (ch1.get(g) or {}).get("3n") or {}
        d.append("| {0} | {1} | {2} · {3} | {4} · {5} | {6} ({7}) | {8} {9} | {10} → {11} | {12} → {13} | {14} → {15} | "
                 "{16} |".format(
                     g, a0.get("n", "—") if cu else "—", _pt(a0.get("ti_le")), _nang(a0.get("nang")), _pt(z0.get("ti_le")),
                     _nang(z0.get("nang")), z.get("n", 0), (ch1.get(g) or {}).get("n_lap_bo", 0), _pt(z.get("ti_le")),
                     _ci(z.get("ci90")) if z.get("n") else "", _pt(z.get("nen")), _nang(z.get("nang")),
                     _pt(z.get("nen_tang")), _nang(z.get("nang_tang")), _pt(z.get("nen_cong")), _nang(z.get("nang_cong")),
                     _nang(a.get("nang_tang"))))
    d.append("")
    tk1 = t1.get("theo_kenh") or {}
    if tk1:
        d.append("Theo kênh (NỔ +7n công bằng: tỉ lệ · n · nâng cùng tầng):")
        d.append("")
        d.append("| Giả thuyết | " + " | ".join(kenh_ds) + " |")
        d.append("|---|" + "---|" * len(kenh_ds))
        for g in con:
            o = []
            for k in kenh_ds:
                z = ((tk1.get(k) or {}).get(g) or {}).get(kq) or {}
                o.append("{0} · {1} · {2}".format(_pt(z.get("ti_le")), z.get("n", 0), _nang(z.get("nang_tang")))
                         if z.get("n") else "—")
            d.append("| {0} | {1} |".format(g, " | ".join(o)))
        d.append("")
    d.append("## 2. Tầng 2 — kết quả THẬT (ghi công bóng + ghi công chính xác của khe phòng thí nghiệm)")
    d.append("")
    nen = t2.get("nen_kenh") or {}
    d.append("Nền danh mục: điểm TB {0} trên {1} video đã phán. Hậu nghiệm phân tầng: danh mục κ₀={2:g} quanh nền + "
             "tầng 1 w₁={3:g}; kênh κ₁={4:g} quanh danh mục; P(tốt nhất) kênh rút hai bậc.".format(
                 _pt(t2.get("g")), t2.get("n_nen", 0), ts.get("kappa_chung", 2), ts.get("kappa_tang1", 1),
                 ts.get("kappa_kenh", 4)))
    d.append("")
    tk2 = t2.get("theo_kenh") or {}
    vai_cu = (bang.get("quyet_dinh") or {}).get("kenh") or {}
    for k in kenh_ds:
        m = tk2.get(k) or {}
        nk = nen.get(k) or {}
        if not nk.get("n") and not nk.get("cho"):
            continue
        d.append("**{0}** — {1} video đã phán (điểm TB {2}), {3} chờ phán:".format(
            k, nk.get("n", 0), _pt((nk.get("diem", 0) / nk["n"]) if nk.get("n") else None), nk.get("cho", 0)))
        d.append("")
        d.append("| Giả thuyết | n (chính xác) | thắng | điểm | hậu nghiệm [CI90] | P(tốt nhất) | ngoài top: n · tỉ lệ | chờ | "
                 "vai |")
        d.append("|---|---|---|---|---|---|---|---|---|")
        for g in sorted(con, key=lambda x: -float((m.get(x) or {}).get("p_tot_nhat") or 0)):
            o = m.get(g) or {}
            d.append("| {0} | {1} ({2}) | {3} | {4} | {5} {6} | {7} | {8} · {9} | {10} | {11} |".format(
                g, o.get("n", 0), o.get("n_chinh_xac", 0), o.get("thang", 0), o.get("diem", 0), _pt(o.get("tb")),
                _ci(o.get("ci90")), _pt(o.get("p_tot_nhat")), o.get("n_ngoai", 0), _pt(o.get("ti_le_ngoai")),
                o.get("cho", 0), (vai_cu.get(k) or {}).get(g) or "—"))
        d.append("")
    d.append("## 3. Chia khe sản xuất (Thompson phân tầng, sàn khám phá {0:.0%}, giả thuyết mới ≤ {1} khe/kênh/tuần)"
             .format(chia_khe.KHAM_PHA, chia_khe.KHE_THU_TUAN))
    d.append("")
    for k in kenh_ds:
        try:
            tt = chia_khe.tom_tat_kenh(goc, k, ngay=ngay, bang=bang)
        except Exception as loi:  # noqa: BLE001
            d.append("- {0}: (lỗi {1})".format(k, str(loi)[:80]))
            continue
        tl = tt.get("ti_le_khe") or {}
        d.append("- **{0}** — chia khe {1} ({2}). Tỉ phần khe dự kiến: {3}. Không nhận khe: {4}.".format(
            k, "BẬT" if tt["bat"] else "tắt", tt["vi_sao"],
            ", ".join("{0} {1:.0%}".format(g, x) for g, x in sorted(tl.items(), key=lambda kv: -kv[1])) or "—",
            "; ".join("{0} ({1})".format(g, ly[:170]) for g, ly in sorted((tt.get("chan") or {}).items())) or "—"))
    d.append("")
    d.append("## 4. Luật quyết — quyết định ghi ở lần tính này")
    d.append("")
    moi = (bang.get("quyet_dinh") or {}).get("moi") or []
    if not moi:
        d.append("(không có thay đổi vai nào)")
    for x in moi:
        d.append("- {0} **{1}**{2}: n = {3}, P(tốt nhất) {4} — {5}".format(
            x.get("ten"), x.get("gt"), " @ " + x["kenh"] if x.get("kenh") else " (toàn danh mục)", x.get("n"),
            _pt(x.get("p_tot_nhat")), x.get("ly_do")))
    d.append("")
    d.append("## 5. Vũ trụ ứng viên (ngày gần nhất của mỗi kênh)")
    d.append("")
    d += _phan_vu_tru(goc, kenh_ds, den)
    d.append("")
    d.append("## 6. Đọc kết quả, nghi ngờ")
    d.append("")
    tot = sorted([g for g in con if ((ch1.get(g) or {}).get(kq) or {}).get("n")],
                 key=lambda x: -float(((ch1.get(x) or {}).get(kq) or {}).get("nang_tang") or -9))
    if tot:
        z = (ch1.get(tot[0]) or {}).get(kq) or {}
        d.append("- Tầng 1 công bằng: nâng cùng tầng cao nhất **{0}** (nổ +7n {1} vs {2} của rút ngẫu nhiên cùng tầng, "
                 "n = {3}).".format(tot[0], _pt(z.get("ti_le")), _pt(z.get("nen_tang")), z.get("n")))
    d.append("- Tầng 1 vẫn là đo THỊ TRƯỜNG (video đối thủ còn được đẩy không), không phải video của ta thắng; nó chỉ là "
             "tiên nghiệm yếu (w₁ = {0:g} video giả) và sàn mở thử.".format(ts.get("kappa_tang1", 1)))
    d.append("- Ô gấp × tuổi × đà khử phần \"to sẵn, trẻ, đang tăng thì còn tăng\", nhưng không khử được mọi tương quan "
             "(vd. kênh nguồn đang lên, video đang được trang chủ đẩy) — nâng còn lại có thể vẫn chứa một phần đà.")
    d.append("- Tầng 2 vẫn thiên lệch chọn mẫu (chỉ thấy nguồn đã sản xuất); ghi công CHÍNH XÁC từ khe chia sẽ dần sửa.")
    d.append("")
    p = os.path.join(c.goc_ghi(goc), "workspace", "chan-doan", "{0}-{1}.md".format(ten, ngay))
    return c.ghi_nguyen_tu(p, "\n".join(d) + "\n")


def ghi(goc: str, bang: Dict[str, Any], *, kenh_ds: Sequence[str], tu: str, den: str,
        ngay: Optional[str] = None) -> str:
    """Báo cáo chạy ngược — từ đợt 2 là `ghi_dot_2` (tầng 1 công bằng + chia khe + luật quyết)."""
    return ghi_dot_2(goc, bang, kenh_ds=kenh_ds, tu=tu, den=den, ngay=ngay, ten="phong-thi-nghiem-backtest")


def ghi_dot_1(goc: str, bang: Dict[str, Any], *, kenh_ds: Sequence[str], tu: str, den: str,
              ngay: Optional[str] = None) -> str:
    """Báo cáo đợt 1 (giữ để tra; số tầng 1 đọc theo cách đo cũ)."""
    ngay = ngay or c.hom_nay()
    gts = sorted((bang.get("gia_thuyet") or {}).keys())
    con = [g for g in gts if (bang["gia_thuyet"][g] or {}).get("trang_thai") != "loai"]
    t1 = bang.get("tang1") or {}
    t2 = bang.get("tang2") or {}
    ts = bang.get("tham_so") or {}
    d: List[str] = []
    d.append("# Phòng thí nghiệm chọn content — chạy ngược lịch sử ({0})".format(ngay))
    d.append("")
    d.append("Đợt 1 của `workspace/chan-doan/ke-hoach-phong-thi-nghiem-content.md`: dựng lại vũ trụ ứng viên + kho đặc "
             "trưng cho TỪNG ngày từ {0} đến {1} (sổ sao lưu `sao-luu/`, bảng `cham-v7-<ngày>.csv`, trang chủ, bảng đề "
             "xuất Studio — chỉ thông tin có tới hết ngày đó), chấm {2} giả thuyết, ghi nhật ký bóng `che_do = nguoc`, "
             "rồi đo. Mã: `core/phong_thi_nghiem/`. Bảng đầy đủ (máy đọc): `workspace/phong-thi-nghiem/"
             "bang-xep-hang.json`.".format(tu, den, len(con)))
    d.append("")
    d.append("**Đọc trước — mẫu nhỏ.** Tầng 2 dựa trên vài chục video có kết luận (≥ 96h); mỗi ô in n và khoảng tin "
             "90%. Không giả thuyết nào được phán chỉ bằng bảng này: luật quyết cần n ≥ {0} và P(tốt nhất) ≥ {1:.0%} "
             "(dẫn đầu) hoặc < {2:.0%} (loại). Sản xuất CHƯA đổi gì — đợt 2 mới chia khe theo bảng.".format(
                 ts.get("n_quyet", 8), ts.get("p_dan_dau", 0.8), ts.get("p_loai", 0.05)))
    d.append("")
    # 0. tóm tắt
    ch1 = t1.get("chung") or {}
    ch2 = t2.get("chung") or {}
    d.append("## 0. Bảng xếp hạng gộp (toàn danh mục)")
    d.append("")
    d.append("| Giả thuyết | Trạng thái | Tầng 1: đang lên +3n (n) · nâng | NỔ +7n · nâng | Tầng 2: n trong top | điểm "
             "| hậu nghiệm [CI90] | P(tốt nhất) |")
    d.append("|---|---|---|---|---|---|---|---|")
    for g in sorted(con, key=lambda x: (-(float((ch2.get(x) or {}).get("p_tot_nhat") or -1)), x)):
        a = (ch1.get(g) or {}).get("3n") or {}
        z = (ch1.get(g) or {}).get("7n_no") or {}
        o = ch2.get(g) or {}
        d.append("| {0} | {1} | {2} ({3}) · {4} | {5} · {6} | {7} | {8} | {9} {10} | {11} |".format(
            g, (bang["gia_thuyet"][g] or {}).get("trang_thai", ""), _pt(a.get("ti_le")), a.get("n", 0),
            ("{0:+.0f}".format(100 * a["nang"]) if a.get("nang") is not None else "—"), _pt(z.get("ti_le")),
            ("{0:+.0f}".format(100 * z["nang"]) if z.get("nang") is not None else "—"), o.get("n", 0),
            o.get("diem", 0), _pt(o.get("tb")), _ci(o.get("ci90")),
            _pt(o.get("p_tot_nhat")) if o.get("co_nhat_ky", True) else "chưa chạy bóng"))
    d.append("")
    # 1. vũ trụ
    d.append("## 1. Vũ trụ ứng viên — trước / sau lọc đối thủ thật")
    d.append("")
    d.append("Ngày gần nhất của mỗi kênh. \"Sổ\" = video duy nhất trong sổ content; \"bỏ: kênh\" = video của kênh trượt "
             "luật đối thủ thật (bỏ/hết/lạc ngách/ngừng đăng/quá nhỏ/không bằng chứng khán giả); \"bỏ: video\" = video "
             "của ta, nhóm đã làm, ngắn, cũ đứng im. Trung bình vũ trụ = trên mọi ngày đã dựng.")
    d.append("")
    d.append("| Kênh | Ngày | Sổ | Kênh đối thủ thật / theo dõi / cả sổ | Sàn cỡ kênh | Bỏ: kênh | Bỏ: video | Vũ trụ | "
             "đối thủ · pool · trang chủ | TB vũ trụ (ngày) |")
    d.append("|---|---|---|---|---|---|---|---|---|---|")
    ly_tong: Dict[str, int] = {}
    for k in kenh_ds:
        ds = vu_tru_kenh(goc, k, den)
        if not ds:
            d.append("| {0} | — | — | — | — | — | — | — | — | — |".format(k))
            continue
        x = ds[-1]
        tk = x.get("thong_ke") or {}
        vb = tk.get("video_bo") or {}
        bo_kenh_ly = ("sổ: kênh bỏ", "sổ: kênh hết", "AI: lạc ngách", "không đăng video dài", "kênh quá nhỏ",
                      "chưa có bằng chứng khán giả", "kênh ngoài sổ đối thủ")
        bk = sum(v for ly, v in vb.items() if ly.startswith(bo_kenh_ly))
        bv = sum(v for ly, v in vb.items() if not ly.startswith(bo_kenh_ly))
        for ly, v in vb.items():
            ly_tong[ly] = ly_tong.get(ly, 0) + v
        tn = tk.get("theo_nguon") or {}
        tb = sum(float((y.get("thong_ke") or {}).get("n_vu_tru") or 0) for y in ds) / len(ds)
        d.append("| {0} | {1} | {2} | {3} / {4} / {5} | {6} | {7} | {8} | **{9}** | {10} · {11} · {12} | {13} ({14}) |"
                 .format(k, x["ngay"], _so(tk.get("n_sach")), tk.get("kenh_dat", 0), tk.get("kenh_theo_doi", "?"),
                         tk.get("kenh_so", 0), _so(tk.get("san_kenh")), _so(bk), _so(bv), _so(tk.get("n_vu_tru")),
                         _so(tn.get("doi_thu", 0)), _so(tn.get("pool", 0)), _so(tn.get("trang_chu", 0)), _so(tb),
                         len(ds)))
    if ly_tong:
        d.append("")
        d.append("Lý do bỏ (cộng ngày gần nhất mọi kênh): " + " · ".join(
            "{0} {1}".format(ly, _so(v)) for ly, v in sorted(ly_tong.items(), key=lambda kv: -kv[1])) + ".")
    d.append("")
    # 2. tầng 1
    d.append("## 2. Tầng 1 — thị trường: top-{0} có nhặt đúng video đang lên không".format(bang.get("k", 10)))
    d.append("")
    d.append("\"Đang lên\" = video kiếm thêm ≥ {0:g} × trung vị view của kênh nguồn trong +3 ngày (±1,5) / +7 ngày "
             "(±2,5) kể từ lần quét lúc ghi nhật ký. Nền = tỉ lệ ấy trên CẢ vũ trụ cùng (kênh, ngày); nâng = top − nền. "
             "Gộp danh mục bỏ trùng (ngày, video) giữa kênh. Cần ảnh chụp sau ngày ghi → các ngày cuối chưa có số."
             .format(ts.get("nguong_tang_tt", 1.0)))
    d.append("")
    d.append("| Giả thuyết | n +3n | đang lên +3n [CI90] | nền | nâng | n +7n | đang lên +7n [CI90] | nền | nâng | "
             "NỔ +7n (≥ 5×) [CI90] | nền | nâng |")
    d.append("|---|---|---|---|---|---|---|---|---|---|---|---|")

    def _nang(x: Dict[str, Any]) -> str:
        return "{0:+.0f} điểm".format(100 * x["nang"]) if x.get("nang") is not None else "—"
    for g in con:
        o = ch1.get(g) or {}
        a, b, z = o.get("3n") or {}, o.get("7n") or {}, o.get("7n_no") or {}
        d.append("| {0} | {1} | {2} {3} | {4} | {5} | {6} | {7} {8} | {9} | {10} | {11} {12} | {13} | {14} |".format(
            g, a.get("n", 0), _pt(a.get("ti_le")), _ci(a.get("ci90")) if a.get("n") else "", _pt(a.get("nen")),
            _nang(a), b.get("n", 0), _pt(b.get("ti_le")), _ci(b.get("ci90")) if b.get("n") else "", _pt(b.get("nen")),
            _nang(b), _pt(z.get("ti_le")), _ci(z.get("ci90")) if z.get("n") else "", _pt(z.get("nen")), _nang(z)))
    d.append("")
    tk1 = t1.get("theo_kenh") or {}
    if tk1:
        d.append("Theo kênh (+3 ngày: tỉ lệ đang lên · n):")
        d.append("")
        d.append("| Giả thuyết | " + " | ".join(kenh_ds) + " |")
        d.append("|---|" + "---|" * len(kenh_ds))
        for g in con:
            o = []
            for k in kenh_ds:
                a = ((tk1.get(k) or {}).get(g) or {}).get("3n") or {}
                o.append("{0} · {1}".format(_pt(a.get("ti_le")), a.get("n", 0)) if a.get("n") else "—")
            d.append("| {0} | {1} |".format(g, " | ".join(o)))
        d.append("")
    # 3. tầng 2
    d.append("## 3. Tầng 2 — cầu nối: kết quả THẬT của video ta làm, ghi công cho giả thuyết đã xếp nguồn vào top-{0}"
             .format(bang.get("k", 10)))
    d.append("")
    d.append("Video kênh ta làm từ nguồn S ngày D → nhật ký (kênh, giả thuyết) muộn nhất trong [D−{0}, D−1]; S trong "
             "top → ghi điểm thước chung (thắng 1 · trung bình 0,5 · trượt 0). Hậu nghiệm Beta co về mức của giả thuyết "
             "(κ={1:g}) và mức nền danh mục (κ={2:g}); P(tốt nhất) Monte Carlo {3} lượt. \"Ngoài top\" = video đã phán "
             "mà giả thuyết KHÔNG xếp vào top hôm ấy (để so).".format(
                 ts.get("lui_nhat_ky", 3), ts.get("kappa_kenh", 4), ts.get("kappa_chung", 2), ts.get("n_mc", 4000)))
    d.append("")
    nen = t2.get("nen_kenh") or {}
    d.append("Nền danh mục: điểm TB {0} trên {1} video đã phán (mọi kênh). Video không có nhật ký nào ở D−1…D−3: {2}."
             .format(_pt(t2.get("g")), t2.get("n_nen", 0),
                     ", ".join("{0} {1}".format(k, v) for k, v in sorted((t2.get("khong_nhat_ky") or {}).items()))
                     or "0"))
    d.append("")
    d.append("**Toàn danh mục (gộp kênh):**")
    d.append("")
    d.append("| Giả thuyết | n trong top | điểm | hậu nghiệm TB [CI90] | P(tốt nhất) |")
    d.append("|---|---|---|---|---|")
    ch2 = t2.get("chung") or {}
    for g in sorted(con, key=lambda x: -float((ch2.get(x) or {}).get("p_tot_nhat") or 0)):
        o = ch2.get(g) or {}
        d.append("| {0} | {1} | {2} | {3} {4} | {5} |".format(g, o.get("n", 0), o.get("diem", 0), _pt(o.get("tb")),
                                                             _ci(o.get("ci90")), _pt(o.get("p_tot_nhat"))))
    d.append("")
    tk2 = t2.get("theo_kenh") or {}
    for k in kenh_ds:
        m = tk2.get(k) or {}
        nk = nen.get(k) or {}
        if not nk.get("n") and not nk.get("cho"):
            continue
        d.append("**{0}** — {1} video đã phán (điểm TB {2}), {3} đang chờ phán:".format(
            k, nk.get("n", 0), _pt((nk.get("diem", 0) / nk["n"]) if nk.get("n") else None), nk.get("cho", 0)))
        d.append("")
        d.append("| Giả thuyết | n top | điểm | tỉ lệ thô | hậu nghiệm [CI90] | P(tốt nhất) | ngoài top: n · tỉ lệ | chờ | "
                 "luật |")
        d.append("|---|---|---|---|---|---|---|---|---|")
        for g in sorted(con, key=lambda x: -float((m.get(x) or {}).get("p_tot_nhat") or 0)):
            o = m.get(g) or {}
            d.append("| {0} | {1} | {2} | {3} | {4} {5} | {6} | {7} · {8} | {9} | {10} |".format(
                g, o.get("n", 0), o.get("diem", 0), _pt(o.get("ti_le_tho")), _pt(o.get("tb")), _ci(o.get("ci90")),
                _pt(o.get("p_tot_nhat")), o.get("n_ngoai", 0), _pt(o.get("ti_le_ngoai")), o.get("cho", 0),
                o.get("luat", "")))
        d.append("")
    # 4. đọc
    d.append("## 4. Đọc kết quả, nghi ngờ")
    d.append("")
    tot = sorted(con, key=lambda x: -float((ch2.get(x) or {}).get("p_tot_nhat") or 0))
    if tot and ch2:
        o = ch2.get(tot[0]) or {}
        d.append("- Tầng 2 gộp: dẫn là **{0}** (P(tốt nhất) {1}, n = {2}) — {3}.".format(
            tot[0], _pt(o.get("p_tot_nhat")), o.get("n", 0),
            "CHƯA đủ n để quyết" if (o.get("n") or 0) < ts.get("n_quyet", 8) else "đủ n để xét luật quyết"))
    tot1 = sorted([g for g in con if ((ch1.get(g) or {}).get("3n") or {}).get("n")],
                  key=lambda x: -float(((ch1.get(x) or {}).get("3n") or {}).get("nang") or -9))
    if tot1:
        a = (ch1.get(tot1[0]) or {}).get("3n") or {}
        d.append("- Tầng 1 (+3 ngày): nâng cao nhất **{0}** ({1} so nền {2}, n = {3}).".format(
            tot1[0], _pt(a.get("ti_le")), _pt(a.get("nen")), a.get("n")))
    d.append("- Thiên lệch chọn mẫu ở tầng 2: chỉ thấy kết quả của nguồn sản xuất ĐÃ chọn (phần lớn bằng VPH + biên tập "
             "AI). Giả thuyết trùng nhiều với VPH được nhiều quan sát hơn; giả thuyết hiếm khi trùng (H-KHOANG-TRONG, "
             "H-NHAN-BAN) gần như chỉ có tiên nghiệm — P(tốt nhất) của chúng phản ánh độ bất định, không phải thắng.")
    d.append("- Mọi giả thuyết xem CÙNG một video → các ô không độc lập; so hai giả thuyết bằng P(tốt nhất) là đúng hướng "
             "nhưng đừng cộng n giữa các hàng.")
    d.append("- Chạy ngược: bảng V7 lưu theo ngày chỉ chứa dòng ĐÃ QUA cổng V7 của ngày ấy (cổng cũ chặt hơn bản 5) và "
             "điểm bản 5 được dựng lại từ cột cũ; VPH là bản xấp xỉ trên ảnh chụp sổ (VPH thật không lưu theo ngày). Bản "
             "đồ chủ quyền vùng + nhãn vùng AI + phán quyết ngách AI là bản HIỆN TẠI (mới từ 10–12/10) — rò rỉ nhẹ "
             "vào H-KHOANG-TRONG và luật đối thủ thật. Thị trường vùng chỉ có từ khi chiến trường bắt đầu chụp.")
    d.append("- Tầng 1 đo trên view của ảnh chụp sổ (mỗi kênh quét ~1 lần/ngày, làm tròn view 1.000/10.000 của "
             "YouTube) → video nhỏ dễ bị đọc \"không tăng\".")
    d.append("- Kênh chưa được YouTube phát (0 hiển thị) cho toàn \"trượt\" — kéo mọi giả thuyết xuống như nhau ở kênh "
             "đó; đọc bảng theo kênh có phân phối trước.")
    d.append("")
    p = os.path.join(c.goc_ghi(goc), "workspace", "chan-doan", "phong-thi-nghiem-backtest-{0}.md".format(ngay))
    return c.ghi_nguyen_tu(p, "\n".join(d) + "\n")
