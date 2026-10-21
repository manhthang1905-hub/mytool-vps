"""Cộng sự — nguồn **top 5 theo đà 48 giờ** của mỗi kênh (chủ 21/10/2026, chạy tự động hoàn toàn).

Chủ: *"chưa video nào đạt 20k/48h thì ít nhất kênh nào cũng có 5 video nhiều view nhất — dùng 5 video đó kéo các kênh
khác"* → sửa ngay sau: *"đang có nhiều view trong 48h là ok top 5 đó"*. Vậy xếp theo LƯỢT XEM TĂNG TRONG 48 GIỜ QUA (đà
hiện tại), video tuổi nào cũng được; KHÔNG bao giờ lùi về tổng trọn đời.

Ba nguồn số tăng 48 giờ, ưu tiên từ trên xuống (một video lấy nguồn tốt nhất có):
1. `the_studio`  — thẻ thời gian thực «48 giờ qua» của Studio (gói `get_cards` của quét ngày): số CHÍNH XÁC, chỉ top 3.
2. `moc_studio`  — mốc chụp từng video của quét ngày (`chi-so/<video>/<N>h/tong-quan.json`, mỗi ngày một mốc, tới
                   ~31 ngày tuổi): hiệu lượt xem mốc mới nhất (≤ 36 giờ trước) và mốc cách nó gần 48 giờ nhất.
3. `mau_cong_khai` — sổ mẫu lượt xem CÔNG KHAI tự lấy (`workspace/cong-su/mau-view.json`): mỗi kênh một lượt tab
                   Video công khai (một trang ~27 video; số < 1万 là chính xác) + trang xem cho video ≥ 1万 (tab chỉ
                   ghi tròn «1.5万»), mỗi `gio_lay_mau` giờ. Hiệu hai mẫu cách ≥ 20 giờ, quy về 48 giờ.
Khoảng đo khác 48 giờ thì quy tỉ lệ về 48 giờ và ghi `quy_doi`. Video mới có MỘT mẫu → `cho_mau` (đợi mẫu sau).
Video < 48 giờ tuổi: mọi lượt xem đều nằm trong 48 giờ.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

TEP_MAU = "mau-view.json"
TEP_TOP = "top5.json"
NGAY_GIU_MAU = 14
_RE_MOC = re.compile(r"^(\d+)h$")


def _cs():
    from core import cong_su  # noqa: PLC0415
    return cong_su


# ── phân tích tab Video công khai (thuần) ───────────────────────────────────

_RE_SO_VIEW = re.compile(r"^([\d.,]+)\s*(万|億|K|M|B)?\s*(?:回視聴|views?|lượt xem)$", re.I)


def so_view_chu(chu: str) -> Tuple[Optional[int], bool]:
    """`"8,502回視聴"` → (8502, False) · `"1.5万回視聴"` → (15000, True=tròn số) · `"1.2K views"` → (1200, True)."""
    m = _RE_SO_VIEW.match(str(chu or "").strip())
    if not m:
        return None, False
    so, don = m.group(1).replace(",", ""), (m.group(2) or "")
    try:
        x = float(so)
    except ValueError:
        return None, False
    he = {"": 1, "万": 10_000, "億": 100_000_000, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[don.lower()]
    return int(round(x * he)), bool(don)


def doc_tab_video(html: str) -> List[Dict[str, Any]]:
    """[{video_id, view, tron}] từ HTML tab Video công khai của kênh (khối `lockupViewModel`)."""
    ra, thay = [], set()
    vi_tri = [m.start() for m in re.finditer(r'"lockupViewModel"\s*:\s*\{', html)]
    for i, dau in enumerate(vi_tri):
        doan = html[dau: vi_tri[i + 1] if i + 1 < len(vi_tri) else dau + 30000]
        m = re.search(r'"contentId"\s*:\s*"([A-Za-z0-9_-]{11})"', doan)
        if not m or m.group(1) in thay:
            continue
        nhan = re.findall(r'"accessibilityLabel"\s*:\s*"([^"]{1,40})"', doan)
        view, tron = None, False
        for n in nhan:
            view, tron = so_view_chu(n)
            if view is not None:
                break
        if view is None:
            continue
        thay.add(m.group(1))
        ra.append({"video_id": m.group(1), "view": view, "tron": tron})
    return ra


# ── sổ mẫu công khai ────────────────────────────────────────────────────────

def doc_mau(goc: str) -> Dict[str, Any]:
    d = _cs()._doc_json(os.path.join(_cs().thu_muc(goc), TEP_MAU))
    return d if isinstance(d, dict) else {"video": {}, "kenh": {}}


def lay_mau(goc: str, kenh: str, uc: str, bay: _dt.datetime, tai=None, so: Optional[Dict[str, Any]] = None,
            toi_da_trang_xem: int = 8) -> Dict[str, Any]:
    """MỘT lượt mẫu của một kênh vào `so` (chưa ghi đĩa): tab Video công khai + trang xem cho video số tròn."""
    cs = _cs()
    so = so if so is not None else doc_mau(goc)
    ma, du = (tai or cs.tai_that)("https://www.youtube.com/channel/{0}/videos".format(uc))
    if ma != 200 or not du:
        return {"kenh": kenh, "ma": ma, "so_video": 0}
    ds = doc_tab_video(du.decode("utf-8", "replace"))
    luc = cs._luc(bay)
    xem = 0
    for x in sorted(ds, key=lambda y: -y["view"]):
        view = x["view"]
        if x["tron"] and xem < toi_da_trang_xem:
            r = cs.view_cong_khai(x["video_id"], tai)
            xem += 1
            if r.get("view") is not None:
                view = int(r["view"])
            else:
                continue                      # không chép số tròn làm mẫu (hiệu hai số tròn là nhiễu)
        elif x["tron"]:
            continue
        v = so.setdefault("video", {}).setdefault(x["video_id"], {"kenh": kenh, "mau": []})
        v["kenh"] = kenh
        v["mau"].append([luc, int(view)])
        han = (bay - _dt.timedelta(days=NGAY_GIU_MAU)).strftime("%Y-%m-%d %H:%M:%S")
        v["mau"] = [m for m in v["mau"] if m[0] >= han][-60:]
    so.setdefault("kenh", {})[kenh] = {"luc": luc, "so_video": len(ds), "trang_xem": xem}
    return {"kenh": kenh, "ma": ma, "so_video": len(ds), "trang_xem": xem}


def can_lay_mau(so: Dict[str, Any], kenh: str, bay: _dt.datetime, gio: float) -> bool:
    t = _cs()._doc_luc(((so.get("kenh") or {}).get(kenh) or {}).get("luc"))
    return t is None or (bay - t).total_seconds() >= gio * 3600 - 300


def tang_tu_chuoi(chuoi: Sequence[Tuple[_dt.datetime, float]], bay: _dt.datetime, tuoi_gio: Optional[float] = None,
                  moi_nhat_toi_da_gio: float = 36.0, khoang_min: float = 20.0) -> Optional[Dict[str, Any]]:
    """Lượt xem tăng 48 giờ từ chuỗi (lúc, tổng lượt xem) — thuần. Điểm mới nhất phải ≤ `moi_nhat_toi_da_gio` giờ trước;
    điểm so là điểm cách nó gần 48 giờ nhất (≥ `khoang_min` giờ); khác 48 giờ thì quy tỉ lệ. Video < 48 giờ tuổi → cả
    tổng. None khi chưa đủ (một điểm)."""
    ds = sorted((t, float(v)) for t, v in chuoi if t is not None and v is not None)
    if not ds:
        return None
    t1, v1 = ds[-1]
    if (bay - t1).total_seconds() / 3600.0 > moi_nhat_toi_da_gio:
        return None
    if tuoi_gio is not None and tuoi_gio <= 48:
        return {"tang": int(v1), "khoang_gio": round(tuoi_gio, 1), "quy_doi": False, "view": int(v1)}
    ung = [(abs((t1 - t).total_seconds() / 3600.0 - 48), t, v) for t, v in ds[:-1]
           if (t1 - t).total_seconds() / 3600.0 >= khoang_min]
    if not ung:
        return None
    _l, t0, v0 = min(ung)
    gio = (t1 - t0).total_seconds() / 3600.0
    tang = max(0.0, v1 - v0) * (48.0 / gio)
    return {"tang": int(round(tang)), "khoang_gio": round(gio, 1), "quy_doi": abs(gio - 48) > 6, "view": int(v1)}


# ── ba nguồn ────────────────────────────────────────────────────────────────

def tang_the_studio(goc: str, kenh: str, bay: _dt.datetime, tuoi_toi_da_gio: float = 36.0) -> Dict[str, int]:
    """{video_id: lượt xem 48 giờ qua} của thẻ thời gian thực Studio (chỉ top 3; cũ > 36 giờ → {})."""
    vm = os.path.join(goc, "vm")
    ma_vm = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm")
    for p in (ma_vm,):
        if p not in sys.path:
            sys.path.append(p)
    try:
        import may_dang_dom  # noqa: PLC0415 — chỉ thư viện chuẩn
        v, luc = may_dang_dom.doc_view_48h_kem_luc(os.path.join(goc, "CHANNEL", kenh, "chi-so"))
    except Exception:  # noqa: BLE001
        return {}
    del vm
    if not luc or (bay.timestamp() - float(luc)) / 3600.0 > tuoi_toi_da_gio:
        return {}
    return {str(k): int(x) for k, x in (v or {}).items()}


def chuoi_moc_studio(goc: str, kenh: str, vid: str) -> List[Tuple[_dt.datetime, float, int]]:
    """[(lúc chụp, lượt xem, giờ tuổi)] từ các mốc `<N>h/tong-quan.json` của video (lúc chụp = mtime thư mục mốc)."""
    goc_v = os.path.join(goc, "CHANNEL", kenh, "chi-so", vid)
    ra = []
    try:
        ten = os.listdir(goc_v)
    except OSError:
        return ra
    for t in ten:
        m = _RE_MOC.match(t)
        if not m:
            continue
        p = os.path.join(goc_v, t)
        tq = _cs()._doc_json(os.path.join(p, "tong-quan.json"))
        v = (tq or {}).get("views") if isinstance(tq, dict) else None
        if v is None:
            continue
        try:
            luc = _dt.datetime.fromtimestamp(os.path.getmtime(p))
        except OSError:
            continue
        ra.append((luc, float(v), int(m.group(1))))
    return sorted(ra)


def tang_48h_kenh(goc: str, kenh: str, bay: _dt.datetime, mau: Optional[Dict[str, Any]] = None
                  ) -> Dict[str, Dict[str, Any]]:
    """{video_id: {tang, nguon, khoang_gio, quy_doi, view}} — mọi video của kênh đo được; video chỉ có MỘT mẫu →
    {nguon: "cho_mau"} (không có `tang`)."""
    cs = _cs()
    mau = mau if mau is not None else doc_mau(goc)
    ra: Dict[str, Dict[str, Any]] = {}
    for vid, x in tang_the_studio(goc, kenh, bay).items():
        ra[vid] = {"tang": x, "nguon": "the_studio", "khoang_gio": 48.0, "quy_doi": False, "view": None}
    vids = set(cs.bang_tom_tat(goc, kenh))
    vids |= {v for v, d in (mau.get("video") or {}).items() if d.get("kenh") == kenh}
    for vid in vids:
        if vid in ra or not cs._RE_VID.match(vid):
            continue
        moc = chuoi_moc_studio(goc, kenh, vid)
        r = None
        if moc:
            r = tang_tu_chuoi([(t, v) for t, v, _g in moc], bay, tuoi_gio=moc[-1][2] if moc[-1][2] <= 48 else None)
            if r:
                r["nguon"] = "moc_studio"
        if r is None:
            ch = [(cs._doc_luc(a), b) for a, b in ((mau.get("video") or {}).get(vid) or {}).get("mau") or []]
            r = tang_tu_chuoi(ch, bay)
            if r:
                r["nguon"] = "mau_cong_khai"
            elif ch:
                r = {"nguon": "cho_mau", "view": int(ch[-1][1])}
        if r:
            ra[vid] = r
    return ra


def top5(goc: str, bay: _dt.datetime, kenh_ds: Sequence[str], san: float = 300, so_luong: int = 5,
         mau: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """{kenh: {top: [{video_id, tang, nguon, ...}], du: số video đạt sàn, cho_mau: n, do_duoc: n}, phan_bo: [...]}."""
    mau = mau if mau is not None else doc_mau(goc)
    ra: Dict[str, Any] = {"luc": _cs()._luc(bay), "san": san, "kenh": {}, "phan_bo": []}
    for k in kenh_ds:
        t = tang_48h_kenh(goc, k, bay, mau)
        do = [dict(x, video_id=v) for v, x in t.items() if x.get("tang") is not None]
        do.sort(key=lambda x: -x["tang"])
        dat = [x for x in do if x["tang"] >= san]
        ra["kenh"][k] = {"top": dat[:so_luong], "du": len(dat), "do_duoc": len(do),
                         "cho_mau": sum(1 for x in t.values() if x.get("nguon") == "cho_mau"),
                         "cao_nhat": do[:so_luong]}
        ra["phan_bo"] += [x["tang"] for x in do]
    ra["phan_bo"].sort(reverse=True)
    return ra
