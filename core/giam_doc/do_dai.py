"""Độ dài theo GIỜ XEM / 1.000 HIỂN THỊ @52h (không theo AVD%): video dài hơn giữ % kém hơn nhưng có thể
cho nhiều giờ xem hơn trên mỗi lần được hiển thị — đó mới là thứ YouTube và YPP cần.

Nhóm theo độ dài quanh `phut_muc_tieu` (±1,5 phút): ngắn / vừa / dài. Nhóm khác "vừa" hơn ≥ 15% (n ≥ 2)
→ thí nghiệm `phut_muc_tieu` ±2–3 phút về phía nó, cỡ mẫu 4 video, hạn 28 ngày.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .du_lieu import chu_so, ket_luan_so, moc_52, trung_vi, video_sau

TEN = "do_dai"
MO_TA = "Độ dài theo giờ xem / 1.000 hiển thị @52h → thí nghiệm phut_muc_tieu ±2–3 phút"
NHIP = "tuan"
CHI_SO_CHINH = "gio_xem_1k_hien_thi_52h"
BIEN_VUA = 1.5
HON = 1.15
CO_MAU = 4


def _mau(bs: Any) -> List[Dict[str, Any]]:
    ra = []
    for v in bs.video:
        b = moc_52(v)
        if b and b.get("gx_1k") is not None and v.get("dai_giay"):
            ra.append({"id": v["id"], "phut": v["dai_giay"] / 60.0, "gx_1k": b["gx_1k"], "avd_pct": b.get("avd_pct")})
    return ra


def ap_dung(bs: Any) -> float:
    """Cần ≥ 4 video có số @52h và `phut_muc_tieu` là số."""
    return 1.0 if bs.phut_muc_tieu and len(_mau(bs)) >= CO_MAU else 0.0


def nhom(bs: Any) -> Dict[str, Dict[str, Any]]:
    """{ngan|vua|dai: {n, phut_tv, gx_1k_tv, avd_pct_tv}}."""
    pmt = bs.phut_muc_tieu or 0
    g: Dict[str, List[Dict[str, Any]]] = {"ngan": [], "vua": [], "dai": []}
    for m in _mau(bs):
        g["ngan" if m["phut"] < pmt - BIEN_VUA else "dai" if m["phut"] > pmt + BIEN_VUA else "vua"].append(m)
    return {k: {"n": len(ds), "phut_tv": trung_vi([m["phut"] for m in ds]),
                "gx_1k_tv": trung_vi([m["gx_1k"] for m in ds]),
                "avd_pct_tv": trung_vi([m["avd_pct"] for m in ds])} for k, ds in g.items()}


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """Giờ xem / 1k hiển thị @52h theo nhóm độ dài."""
    ra = []
    for k, o in nhom(bs).items():
        if not o["n"]:
            continue
        ra.append({"cau": "nhóm {0} (trung vị {1} phút, n={2}): {3} giờ xem/1k hiển thị @52h, AVD {4}.".format(
            k, chu_so(o["phut_tv"], 1), o["n"], chu_so(o["gx_1k_tv"], 2), chu_so(o["avd_pct_tv"], 0, "%")),
            "n": o["n"], "tin_cay": "thap" if o["n"] < 3 else "vua", "nhom": k})
    return ra


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Thí nghiệm `phut_muc_tieu` về phía nhóm cho nhiều giờ xem / hiển thị hơn."""
    g = nhom(bs)
    pmt = int(bs.phut_muc_tieu or 0)
    nen_o = g["vua"] if g["vua"]["n"] >= 2 else None
    nen = nen_o["gx_1k_tv"] if nen_o else trung_vi([m["gx_1k"] for m in _mau(bs)])
    if not nen or not pmt:
        return []
    ung = [(k, o) for k, o in g.items() if k != "vua" and o["n"] >= 2 and o["gx_1k_tv"] >= HON * nen]
    if not ung:
        return []
    k, o = max(ung, key=lambda x: x[1]["gx_1k_tv"])
    buoc = 3 if abs(o["phut_tv"] - pmt) >= 3 else 2
    moi = max(10, min(25, pmt + (buoc if k == "dai" else -buoc)))
    if moi == pmt:
        return []
    return [{"loai": "tham_so", "viec": "do_dai", "khoa": "phut_muc_tieu", "gia_tri": moi,
             "gia_thuyet": "Nhóm {0} ({1} phút) cho {2} giờ xem/1k hiển thị so với {3} — đổi {4} → {5} phút "
                           "nâng giờ xem/1k hiển thị @52h.".format(k, chu_so(o["phut_tv"], 1), chu_so(o["gx_1k_tv"], 2),
                                                                    chu_so(nen, 2), pmt, moi),
             "chi_so": CHI_SO_CHINH, "co_mau": CO_MAU, "han_ngay": 28, "tut_pct": 20,
             "nen": {"gia_tri": round(nen, 3), "n": nen_o["n"] if nen_o else len(_mau(bs))}}]


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Trung vị giờ xem/1k hiển thị @52h của video đăng sau khi áp so với nền."""
    ds = [(moc_52(v) or {}).get("gx_1k") for v in video_sau(bs, tn["bat_dau"], id_tn=tn.get("id", ""))]
    return ket_luan_so(tn, [x for x in ds if x is not None])
