"""Dồn cụm thắng, tạm bỏ cụm thua có hạn; chỉnh tỉ trọng công thức; bật tự học khi đủ điều kiện.

Chỉ đọc số của CHÍNH kênh, nhãn THƯỚC CHUNG `core.thuoc_thang` (thắng / trung bình / trượt — phân vị hiển thị so
video của chính kênh cùng tuổi, phán ở ≥ 96h; không bao giờ ở 48h). Thực đơn:
  * chỉ đạo "ưu tiên cụm X" (≥ 2 thắng, tỉ lệ ≥ 50%);
  * "tạm bỏ cụm Y 3 tuần" CHỈ khi ≥ `N_BO_TOI_THIEU` (6) video đã phán VÀ P(cụm kém hơn nền của kênh) >
    `P_BO` (0,9) — Beta(1 + điểm, 1 + n − điểm), thắng 1 · trung bình ½ · trượt 0 (`thuoc_thang.xac_suat_kem_hon`).
    12/10/2026 (`workspace/chan-doan/nao-vong-hoc-2026-10-12.md`): luật cũ "n ≥ 3 và 0 thắng @48h" đề xuất bỏ
    tep-tuoi-tac của TL2 (chứa vidGiaa9179 30.283 hiển thị) — 0/7 ở nền ~15% có khả năng ~32% là ngẫu nhiên;
  * `luat_chon_tuan` gộp ≤ 3 câu trên (khoá phụ cho `luat_chon`);
  * `chien_luoc` theo `ti_trong_goi_y` của `nghien-cuu/chien-luoc.json` (kẹp bước ±0,2);
  * `chien_luoc_tu_hoc` false → true khi đủ cả ba điều kiện `docs/kien-thuc/chien-luoc.md` mục 5.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .du_lieu import chu_so, trung_vi, video_sau

TEN = "dan_cum"
MO_TA = "Dồn cụm thắng / tạm bỏ cụm chắc chắn kém của chính kênh (thước chung); tỉ trọng công thức; bật tự học"
NHIP = "tuan"
CHI_SO_CHINH = "ti_le_thang_28n"
N_TOI_THIEU = 3
#: Cấm cụm: cần ≥ ngần này video ĐÃ PHÁN trong cụm, và P(cụm kém hơn nền) > `P_BO`.
N_BO_TOI_THIEU = 6
P_BO = 0.9
BO_TUAN = 3
_NHAN = ("thang", "trung_binh", "truot")


def _tin_cay(n: int) -> str:
    return "thap" if n < 3 else "vua" if n < 6 else "cao"


def _nhan(v: Dict[str, Any]) -> str:
    """Nhãn ba mức của video (thước chung); bảng số cũ chỉ có `ket_luan` hai mức thì lùi về đó."""
    n = v.get("nhan")
    if n in _NHAN:
        return n
    return v.get("ket_luan") if v.get("ket_luan") in ("thang", "truot") else ""


def _da_ket_luan(bs: Any) -> List[Dict[str, Any]]:
    return [v for v in bs.video if _nhan(v)]


def bang_cum(bs: Any) -> Dict[str, Dict[str, Any]]:
    """{cụm: {n, thang, trung_binh, truot, nhan[], hien_thi_tv (ở tuổi phán), phan_vi_tv, gan[]}} trên video đã
    phán (mới → cũ)."""
    ra: Dict[str, Dict[str, Any]] = {}
    for v in _da_ket_luan(bs):
        k = _nhan(v)
        for c in v.get("cum") or ["(chưa có cụm)"]:
            o = ra.setdefault(c, {"n": 0, "thang": 0, "trung_binh": 0, "truot": 0, "nhan": [], "imp": [],
                                  "pv": [], "gan": [], "id": []})
            o["n"] += 1
            o[k] += 1
            o["nhan"].append(k)
            o["id"].append(v.get("id"))
            o["imp"].append(v.get("hien_thi_do"))
            o["pv"].append(v.get("phan_vi"))
            o["gan"].append({"thang": "T", "trung_binh": "~"}.get(k, "x"))
    for o in ra.values():
        o["hien_thi_tv"], o["phan_vi_tv"] = trung_vi(o.pop("imp")), trung_vi(o.pop("pv"))
    return ra


def ap_dung(bs: Any) -> float:
    """Cần ≥ 3 video đã có kết luận (thước chung)."""
    return 1.0 if len(_da_ket_luan(bs)) >= N_TOI_THIEU else 0.0


def _ti_le_thang(bs: Any) -> Dict[str, Any]:
    ds = _da_ket_luan(bs)
    return {"gia_tri": round(sum(1 for v in ds if _nhan(v) == "thang") / len(ds), 3) if ds else None,
            "n": len(ds)}


def p_kem_hon(bs: Any, cum: str, bang: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[float]:
    """P(tỉ lệ "tốt" của cụm < của phần còn lại của kênh) — None khi một bên không có video đã phán."""
    from .. import thuoc_thang  # noqa: PLC0415

    bang = bang if bang is not None else bang_cum(bs)
    o = bang.get(cum)
    if not o:
        return None
    trong = {x for x in o["id"] if x}
    nen = [_nhan(v) for v in _da_ket_luan(bs) if v.get("id") not in trong]
    return thuoc_thang.xac_suat_kem_hon(o["nhan"], nen)


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """Bảng thắng/trung bình/trượt theo cụm (thước chung) + kết quả công thức."""
    ra = []
    bang = bang_cum(bs)
    for c, o in sorted(bang.items(), key=lambda kv: (-kv[1]["thang"], -kv[1]["n"])):
        p = p_kem_hon(bs, c, bang) if not c.startswith("(") else None
        ra.append({"cau": "cụm {0}: {1}/{2} thắng, {3} trung bình, {4} trượt (phán ≥96h theo phân vị cùng tuổi; "
                          "gần nhất {5}); trung vị {6} hiển thị lúc phán, phân vị {7}{8}.".format(
                              bs.cum(c), o["thang"], o["n"], o["trung_binh"], o["truot"], "".join(o["gan"][:5]),
                              chu_so(o["hien_thi_tv"]), chu_so(o["phan_vi_tv"]),
                              "; P(kém hơn nền) {0:.2f}".format(p) if p is not None else ""),
                   "n": o["n"], "tin_cay": _tin_cay(o["n"]), "cum": c, "thang": o["thang"],
                   "p_kem": p})
    for ct, o in sorted((bs.cong_thuc or {}).items()):
        ra.append({"cau": "công thức {0} (28 ngày): {1} video, {2}/{3} thắng, {4} chờ.".format(
            ct, o.get("lam"), o.get("thang"), o.get("n"), o.get("cho")), "n": int(o.get("n") or 0),
            "tin_cay": _tin_cay(int(o.get("n") or 0))})
    tl = bs.chien_luoc_tep or {}
    if tl.get("ti_trong_goi_y"):
        ra.append({"cau": "tỉ trọng đang dùng {0} → gợi ý {1} ({2}).".format(
            tl.get("ti_trong_hien_tai"), tl.get("ti_trong_goi_y"), tl.get("ly_do_goi_y")), "n": 0, "tin_cay": "thap"})
    return ra


def _du_tu_hoc(bs: Any, hien: Dict[str, float], goi_y: Dict[str, float]) -> str:
    """Rỗng nếu đủ cả ba điều kiện bật tự học; không thì lý do."""
    if len(hien) < 2:
        return "cần ≥ 2 công thức"
    kq = bs.cong_thuc or {}
    n = {t: int((kq.get(t) or {}).get("n") or 0) for t in hien}
    if sum(n.values()) < 6 or min(n.values()) < 3:
        return "cần tổng n ≥ 6 và mỗi công thức ≥ 3 kết luận (đang {0})".format(n)
    truoc = (bs.trang_thai or {}).get("goi_y_ti_trong_truoc") or {}
    if not truoc or set(truoc) != set(goi_y) or max(abs(float(truoc[t]) - goi_y[t]) for t in goi_y) > 0.1:
        return "tỉ trọng gợi ý chưa ổn định qua 2 lần ghi"
    return ""


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chỉ đạo dồn/tạm bỏ, `luat_chon_tuan`, `chien_luoc`, `chien_luoc_tu_hoc`."""
    from .gioi_han import KHOA_DUOC_DOI, chu_ti_trong, ti_trong  # noqa: PLC0415

    nen = _ti_le_thang(bs)
    chung = {"chi_so": CHI_SO_CHINH, "nen": nen, "co_mau": 4, "han_ngay": 21, "tut_pct": 30}
    ra: List[Dict[str, Any]] = []
    cau: List[str] = []
    for q in qs:
        c, n, t = q.get("cum"), q["n"], q.get("thang", 0)
        if not c or c.startswith("("):
            continue
        if t >= 2 and t / n >= 0.5:
            nd = "Ưu tiên nguồn thuộc cụm {0}: {1}/{2} video thắng (thước chung, phán ≥96h) trên chính kênh.".format(
                bs.cum(c), t, n)
            ra.append({"loai": "chi_dao", "viec": "don_cum", "noi_dung": nd, "han_ngay": 7,
                       "gia_thuyet": "Dồn cụm thắng nâng tỉ lệ thắng 28 ngày.", "chi_so": CHI_SO_CHINH})
            cau.append(nd)
        elif n >= N_BO_TOI_THIEU and (q.get("p_kem") or 0.0) > P_BO:
            nd = ("Tạm bỏ cụm {0} {1} tuần: {2}/{3} video thắng, P(kém hơn phần còn lại của kênh) {4:.2f} > {5:g} "
                  "(thước chung, phán ≥96h).").format(bs.cum(c), BO_TUAN, t, n, q["p_kem"], P_BO)
            ra.append({"loai": "chi_dao", "viec": "bo_cum", "noi_dung": nd, "han_ngay": 7 * BO_TUAN,
                       "gia_thuyet": "Bỏ cụm thua giải phóng lượt cho cụm có cửa.", "chi_so": CHI_SO_CHINH})
            cau.append(nd)
    if cau:
        ra.append(dict(chung, loai="tham_so", viec="luat_chon_tuan", khoa="luat_chon_tuan",
                       gia_tri=" | ".join(cau[:3]),
                       gia_thuyet="Luật chọn tuần theo bảng cụm của kênh nâng tỉ lệ thắng 28 ngày."))
    hien = ti_trong(bs.cai.get("chien_luoc"))
    goi_y = {str(k): float(v) for k, v in ((bs.chien_luoc_tep or {}).get("ti_trong_goi_y") or {}).items()}
    if len(hien) >= 2 and set(goi_y) == set(hien):
        buoc = KHOA_DUOC_DOI["chien_luoc"]["buoc"]
        moi = {t: hien[t] + max(-buoc, min(buoc, goi_y[t] - hien[t])) for t in hien}
        if max(abs(moi[t] - hien[t]) for t in hien) >= 0.05:
            ra.append(dict(chung, loai="tham_so", viec="ti_trong", khoa="chien_luoc", gia_tri=chu_ti_trong(moi),
                           gia_thuyet="Dồn tỉ trọng theo tỉ lệ thắng thật của công thức ({0}).".format(
                               (bs.chien_luoc_tep or {}).get("ly_do_goi_y"))))
        ly = _du_tu_hoc(bs, hien, goi_y)
        if not ly and str(bs.cai.get("chien_luoc_tu_hoc", "")).lower() != "true":
            ra.append(dict(chung, loai="tham_so", viec="tu_hoc", khoa="chien_luoc_tu_hoc", gia_tri=True,
                           gia_thuyet="Tự học tỉ trọng giữ hoặc nâng tỉ lệ thắng 28 ngày."))
    return ra


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tỉ lệ thắng (thước chung) của video đăng sau khi áp so với nền."""
    ds = [v for v in video_sau(bs, tn["bat_dau"], id_tn=tn.get("id", "")) if _nhan(v)]
    nen = (tn.get("nen") or {}).get("gia_tri")
    s = {"nen": nen, "n": len(ds), "moi": round(sum(1 for v in ds if _nhan(v) == "thang") / len(ds), 3)
         if ds else None}
    if len(ds) < int(tn.get("co_mau") or 1) or nen is None:
        return {"ket": "chua_du", "so": s}
    moi = s["moi"]
    ket = ("mo_rong" if moi >= nen + 0.25 else "giu" if moi >= nen + 0.1 or (nen == 0 and moi > 0) else "bo")
    return {"ket": ket, "so": s}
