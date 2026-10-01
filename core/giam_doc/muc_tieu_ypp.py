"""Chiến lược theo cái YPP đang thiếu (sub hay giờ xem) — chỉ đạo xen cụm + vị trí lời mời đăng ký.

Thiếu SUB → xen cụm có sub/1.000 view cao nhất của CHÍNH kênh; thiếu GIỜ XEM → cụm có giờ xem / 1.000
hiển thị @52h cao nhất. Lời mời đăng ký đặt trước "vách" rơi dốc nhất của kênh (bài học giữ chân).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .du_lieu import chu_so, moc_52, trung_vi

TEN = "muc_tieu_ypp"
MO_TA = "Chọn cụm theo cái YPP đang thiếu (sub hay giờ xem) + vị trí lời mời đăng ký"
NHIP = "tuan"
CHI_SO_CHINH = "sub_1k"
HE_SO_NOI = 1.2
_RE_VACH = re.compile(r"vách rơi dốc nhất thường quanh (\d+:\d{2})")


def _tin_cay(n: int) -> str:
    return "thap" if n < 3 else "vua" if n < 6 else "cao"


def _theo_cum(bs: Any) -> Dict[str, Dict[str, List[float]]]:
    ra: Dict[str, Dict[str, List[float]]] = {}
    for v in bs.video:
        b = moc_52(v) or {}
        for c in v.get("cum") or []:
            o = ra.setdefault(c, {"sub_1k": [], "gx_1k": []})
            if v.get("sub_1k") is not None and (v.get("xem_tron_doi") or 0) >= 200:
                o["sub_1k"].append(v["sub_1k"])
            if b.get("gx_1k") is not None:
                o["gx_1k"].append(b["gx_1k"])
    return ra


def _chi_so_kenh(bs: Any) -> Dict[str, Optional[float]]:
    return {"sub_1k": trung_vi([v["sub_1k"] for v in bs.video
                                if v.get("sub_1k") is not None and (v.get("xem_tron_doi") or 0) >= 200]),
            "gx_1k": trung_vi([(moc_52(v) or {}).get("gx_1k") for v in bs.video])}


def ap_dung(bs: Any) -> float:
    """Kênh chưa đủ YPP và có ≥ 3 video có số sub hoặc giờ xem."""
    if (bs.ypp or {}).get("rang_buoc") not in ("sub", "gio_xem") or bs.giai_doan == "kiem_tien":
        return 0.0
    n = sum(1 for v in bs.video if v.get("sub_1k") is not None or (moc_52(v) or {}).get("gx_1k") is not None)
    return 1.0 if n >= 3 else 0.0


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """Khoảng cách YPP + sub/1k và giờ xem/1k hiển thị theo cụm."""
    y = bs.ypp or {}
    ra = [{"cau": "YPP: {0} sub · {1} giờ xem; thiếu {2} sub · {3} giờ — ràng buộc: {4}.".format(
        chu_so(y.get("sub")), chu_so(y.get("gio_xem")), chu_so(y.get("thieu_sub")), chu_so(y.get("thieu_gio")),
        y.get("rang_buoc")), "n": 0, "tin_cay": "cao", "loai": "ypp"}]
    k = _chi_so_kenh(bs)
    for c, o in sorted(_theo_cum(bs).items()):
        n = max(len(o["sub_1k"]), len(o["gx_1k"]))
        if not n:
            continue
        s, g = trung_vi(o["sub_1k"]), trung_vi(o["gx_1k"])
        ra.append({"cau": "cụm {0}: {1} sub/1k view (n={2}; kênh {3}) · {4} giờ xem/1k hiển thị @52h (n={5}; kênh {6}).".format(
            bs.cum(c), chu_so(s, 1), len(o["sub_1k"]), chu_so(k["sub_1k"], 1), chu_so(g, 1), len(o["gx_1k"]),
            chu_so(k["gx_1k"], 1)),
            "n": n, "tin_cay": _tin_cay(n), "cum": c, "sub_1k": s, "gx_1k": g,
            "n_sub": len(o["sub_1k"]), "n_gx": len(o["gx_1k"])})
    return ra


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chỉ đạo xen cụm kéo đúng thứ đang thiếu; lời mời đăng ký trước vách rơi (khi thiếu sub)."""
    rb = (bs.ypp or {}).get("rang_buoc")
    truc, n_truc, ten = ("sub_1k", "n_sub", "sub/1k view") if rb == "sub" else ("gx_1k", "n_gx", "giờ xem/1k hiển thị")
    k = _chi_so_kenh(bs).get(truc)
    ung = [q for q in qs if q.get("cum") and q.get(truc) is not None and q.get(n_truc, 0) >= 2]
    ra: List[Dict[str, Any]] = []
    if ung and k:
        tot = max(ung, key=lambda q: q[truc])
        if tot[truc] >= HE_SO_NOI * k:
            ra.append({"loai": "chi_dao", "viec": "xen_cum_ypp", "han_ngay": 7, "chi_so": truc,
                       "noi_dung": "Kênh thiếu {0}: cứ 3 video xen ít nhất 1 video cụm {1} ({2} {3} so với kênh {4}, n={5}).".format(
                           "sub" if rb == "sub" else "giờ xem", bs.cum(tot["cum"]), chu_so(tot[truc], 1), ten,
                           chu_so(k, 1), tot[n_truc]),
                       "gia_thuyet": "Xen cụm kéo {0} nâng {1} của kênh.".format("sub" if rb == "sub" else "giờ xem", ten)})
    if rb == "sub":
        vach = next((m.group(1) for b in bs.bai_hoc if b.get("truc") == "giu_chan" and b.get("pham_vi") == "kenh"
                     and not b.get("cum") for m in [_RE_VACH.search(str(b.get("cau") or ""))] if m), "")
        if vach:
            ra.append({"loai": "chi_dao", "viec": "loi_moi_dang_ky", "han_ngay": 14, "chi_so": "sub_1k",
                       "noi_dung": "Đặt một lời mời đăng ký ngắn ngay sau ý giá trị đầu tiên, trước {0} (vách rơi dốc nhất "
                                   "của kênh) — không dồn hết về cuối video.".format(vach),
                       "gia_thuyet": "Mời đăng ký khi người xem còn đông nâng sub/1k view."})
    return ra


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Chỉ đạo không mở thí nghiệm."""
    return None
