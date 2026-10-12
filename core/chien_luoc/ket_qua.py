"""Kết quả theo công thức — mục 3c `workspace/THIET-KE-CHIEN-LUOC.md` (B4, 30/09/2026).

    thong_ke(goc, ma_kenh, ngay=28) -> {cong_thuc: {n, thang, truot, cho, lam, tham_do,
                                                     ctr_trang_chu_tv, sub_1k, avd_giay_tv, goi[]}}

Nối SỔ LƯỢT `CHANNEL/<k>/tu-chay/*.json` (công thức = `run.nguon.cong_thuc`, lùi về
`run.nguon.nguon` — sổ cũ trước bộ máy chiến lược đã ghi sẵn nhãn này, nên thống kê chạy NGƯỢC
được cho video cũ) qua mã gói với HỒ SƠ VIDEO (`ho-so-video/<mã gói>.json`: `video_id`, mốc
48h/72h), rồi với danh sách video của kênh theo V7.

═══ "THẮNG" ĐO THEO CHÍNH KÊNH — THƯỚC CHUNG `core.thuoc_thang` (12/10/2026) ═══

Kết luận lấy nhãn `VideoMinh.nhan_thang` của `cong_thuc_v7.video_cua_kenh` (= `thuoc_thang`): phân vị hiển thị
so video của CHÍNH kênh ở CÙNG tuổi, phán từ ≥ 96h (chốt 168h), không bao giờ ở 48h. "thang" = nhãn thắng;
"truot" = đã phán mà KHÔNG thắng (trung bình hoặc trượt — `ket_luan_3` trả đủ ba mức); "" = chưa phán. Bỏ hẳn
đường lùi "so mốc 48h/72h của hồ sơ với ngưỡng 48h" (chính nó gắn TRƯỢT cho video nổ ngày 3–5).
`nguong_thang_48h` trả kèm ở `video_kenh` chỉ còn là MỨC THAM KHẢO để in.

Nghĩa các số:
  * `lam`  — số gói (video) công thức này đã ra trong cửa sổ `ngay` (theo ngày của tệp sổ; lượt
    đã đánh dấu `bo` không tính);
  * `n`    — số video ĐÃ CÓ KẾT LUẬN = `thang + truot`; `cho` = chưa phán (thước chung, < 96h hoặc thiếu số);
  * `ctr_trang_chu_tv` — trung vị CTR "Browse features" @48h; `avd_giay_tv` — trung vị AVD (giây)
    ở mốc 48h (lùi 72h); `sub_1k` — tổng sub / tổng view × 1000 (bảng tóm tắt, trọn đời video),
    tất cả chỉ trên video đã có kết luận (so cùng tuổi).

Chỉ đọc đĩa, 0 đồng, không gọi mạng. Hỏng chỗ nào thì chỗ đó rỗng, không ném lỗi ra nơi gọi.
`ghi_tep()` (vòng học bước 5) ghi `nghien-cuu/chien-luoc.json`: thống kê + tỉ trọng GỢI Ý —
chưa áp; áp tự động là việc của `kenh.yaml: chien_luoc_tu_hoc: true` trong `ke_hoach`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import glob
import io
import json
import os
import statistics
from typing import Any, Callable, Dict, List, Optional, Tuple

TEP_CHIEN_LUOC = "chien-luoc.json"
NGAY_MAC_DINH = 28


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _so(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _tv(ds: List[float], so_le: int = 2) -> Optional[float]:
    return round(statistics.median(ds), so_le) if ds else None


# ── video của kênh theo V7 ───────────────────────────────────────────────────

def _nguong_thang(ds: List[Any], ch: Dict[str, Any]) -> float:
    """Ngưỡng hiển thị 48h của `cong_thuc_v7._danh_dau_thang` — GỌI CHUNG `nguong_thang_48h` (01/10/2026,
    trước đây chép công thức; kênh ít video có số 48h giờ dùng ngưỡng ngách trộn dần), dùng cho video
    có mốc trong hồ sơ mà danh sách V7 chưa đo được."""
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415

    return v7.nguong_thang_48h(ds, ch)


def video_kenh(goc: str, ma_kenh: str) -> Tuple[Dict[str, Any], Optional[float]]:
    """`({video_id: VideoMinh}, ngưỡng thắng 48h)` — `(rỗng, None)` khi đọc hỏng."""
    try:
        from .. import cong_thuc_v7 as v7  # noqa: PLC0415

        ch, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
        ds = v7.video_cua_kenh(goc, ma_kenh, ch)
        return {v.ma: v for v in ds}, _nguong_thang(ds, ch)
    except Exception:  # noqa: BLE001
        return {}, None


def _moc_ho_so(hs: Dict[str, Any]) -> Dict[str, Any]:
    cs = hs.get("chi_so") or {}
    for moc in ("48h", "72h"):
        if isinstance(cs.get(moc), dict) and cs[moc]:
            return cs[moc]
    return {}


def ket_thuoc(vm: Any, hs: Optional[Dict[str, Any]] = None,
              vm_theo_id: Optional[Dict[str, Any]] = None, ngay_du_phong: str = "") -> Any:
    """`thuoc_thang.KetQua` của một video: nhãn V7 (`VideoMinh.ket`) nếu video có trong `chi-so/`; không thì —
    khi có `vm_theo_id` (cả danh sách V7 của kênh) — chuỗi dựng từ mốc của HỒ SƠ (`moc_gio_that`) chấm so với cùng
    tập video kênh (`thuoc_thang.danh_gia_them`, không làm đổi nhãn video khác). Không có gì → None."""
    k = getattr(vm, "ket", None) if vm is not None else None
    if k is not None or vm_theo_id is None or not (hs or {}).get("chi_so"):
        return k
    from .. import thuoc_thang  # noqa: PLC0415

    c = thuoc_thang.chuoi_ho_so(hs, str((hs or {}).get("video_id") or (hs or {}).get("ma_goi") or ""))
    if not c.diem:
        return None
    chuoi = {vid: v.chuoi for vid, v in vm_theo_id.items() if isinstance(getattr(v, "chuoi", None), thuoc_thang.Chuoi)}
    return thuoc_thang.danh_gia_them(c, chuoi, thuoc_thang.tuoi_ho_so(hs, ngay_du_phong))


def ket_luan_3(vm: Any, hs: Optional[Dict[str, Any]] = None, vm_theo_id: Optional[Dict[str, Any]] = None) -> str:
    """"thang" | "trung_binh" | "truot" | "" (chưa phán) — nhãn thước chung của video (`VideoMinh.nhan_thang`;
    video ngoài `chi-so/` mà có `vm_theo_id` thì chấm từ hồ sơ, xem `ket_thuoc`)."""
    nhan = str(getattr(vm, "nhan_thang", "") or "") if vm is not None else ""
    if not nhan and vm is None and vm_theo_id is not None:
        k = ket_thuoc(None, hs, vm_theo_id)
        nhan = str(getattr(k, "nhan", "") or "") if k is not None else ""
    return nhan if nhan in ("thang", "trung_binh", "truot") else ""


def ket_luan(vm: Any, hs: Dict[str, Any], nguong: Optional[float], *,
             vm_theo_id: Optional[Dict[str, Any]] = None) -> str:
    """"thang" | "truot" | "" (chưa kết luận) — thước chung (`ket_luan_3`), hai mức: trung bình tính là "truot"
    (đã phán, KHÔNG thắng). `nguong` giữ cho chữ ký cũ: không còn phán bằng ngưỡng 48h."""
    k = ket_luan_3(vm, hs, vm_theo_id)
    return "" if not k else ("thang" if k == "thang" else "truot")


def _sub_theo_video(goc: str, ma_kenh: str) -> Dict[str, Tuple[float, float]]:
    """`{video_id: (đăng ký, lượt xem)}` từ `chi-so/bang-tom-tat.csv` (cùng nguồn biên tập viên).

    12/10/2026: cặp (sub, view) lấy từ CÙNG một bản chụp có số đăng ký (`chuyen_doi_sub.cap_sub_xem`). Video chưa
    đo được sub thì VẮNG MẶT, không còn đọc thành (0, view mới nhất). Lỗi cũ ấy làm một kênh hiện "sub/1k ≈ 0,0"."""
    try:
        from ..kenh import duong_kenh  # noqa: PLC0415
        from ..chuyen_doi_sub import cap_sub_xem  # noqa: PLC0415

        duong = os.path.join(duong_kenh(goc, ma_kenh), "chi-so", "bang-tom-tat.csv")
        with io.open(duong, encoding="utf-8-sig", newline="") as tep:
            hang = list(csv.DictReader(tep))
    except Exception:  # noqa: BLE001 — chưa có bảng / hỏng → không có số sub
        return {}
    ra: Dict[str, Tuple[float, float]] = {}
    for d in hang:
        vid = str(d.get("Mã video") or "").strip()
        cap = cap_sub_xem(d) if vid else None
        if cap:
            ra[vid] = (float(cap[0]), float(cap[1]))
    return ra


def _ctr_trang_chu(goc: str, ma_kenh: str, vid: str) -> Optional[float]:
    if not vid:
        return None
    try:
        from ..bai_hoc_san_xuat import _doc_ctr_browse_48h  # noqa: PLC0415
        from ..kenh import duong_kenh  # noqa: PLC0415

        return _doc_ctr_browse_48h(os.path.join(duong_kenh(goc, ma_kenh), "chi-so"), vid)
    except Exception:  # noqa: BLE001
        return None


def ho_so_theo_goi(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Any]]:
    try:
        from ..kenh import duong_kenh  # noqa: PLC0415

        tep = glob.glob(os.path.join(duong_kenh(goc, ma_kenh), "ho-so-video", "*.json"))
    except Exception:  # noqa: BLE001
        return {}
    ra: Dict[str, Dict[str, Any]] = {}
    for duong in sorted(tep):
        du = _doc_json(duong)
        if isinstance(du, dict):
            ra[str(du.get("ma_goi") or os.path.splitext(os.path.basename(duong))[0])] = du
    return ra


# ── thống kê ────────────────────────────────────────────────────────────────

def _o_rong() -> Dict[str, Any]:
    return {"n": 0, "thang": 0, "truot": 0, "cho": 0, "lam": 0, "tham_do": 0,
            "ctr_trang_chu_tv": None, "sub_1k": None, "avd_giay_tv": None, "goi": []}


def thong_ke(goc: str, ma_kenh: str, ngay: int = NGAY_MAC_DINH, *,
             bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Dict[str, Any]]:
    """Thống kê theo công thức trong `ngay` ngày gần nhất (`ngay` ≤ 0 → toàn bộ sổ). Không ném lỗi."""
    try:
        from .. import ho_so_video  # noqa: PLC0415

        so_luot = ho_so_video.nguon_cua_goi(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return {}
    bay_gio = bay_gio or _dt.datetime.now()
    tu = (bay_gio.date() - _dt.timedelta(days=int(ngay))).isoformat() if ngay and ngay > 0 else ""
    ho_so = ho_so_theo_goi(goc, ma_kenh)
    vm_theo_id: Optional[Dict[str, Any]] = None
    nguong: Optional[float] = None
    sub: Optional[Dict[str, Tuple[float, float]]] = None
    ra: Dict[str, Dict[str, Any]] = {}
    gom: Dict[str, Dict[str, List[float]]] = {}
    for ma_goi in sorted(so_luot):
        g = so_luot[ma_goi]
        ct = str(g.get("cong_thuc") or "")
        if not ct or g.get("bo") or (tu and str(g.get("ngay") or "") < tu):
            continue  # không biết công thức (dòng lùi trang-thai.json) / lượt đã bỏ (không ra video)
        o = ra.setdefault(ct, _o_rong())
        o["lam"] += 1
        o["tham_do"] += 1 if g.get("tham_do") else 0
        o["goi"].append(ma_goi)
        hs = ho_so.get(ma_goi) or {}
        vid = str(hs.get("video_id") or "")
        if vm_theo_id is None:  # đọc danh sách V7 lười — kênh chưa làm video nào thì khỏi đọc
            vm_theo_id, nguong = video_kenh(goc, ma_kenh)
        kl = ket_luan(vm_theo_id.get(vid) if vid else None, hs, nguong, vm_theo_id=vm_theo_id) if (vid or hs) else ""
        if not kl:
            o["cho"] += 1
            continue
        o[kl] += 1
        o["n"] += 1
        tg = gom.setdefault(ct, {"ctr": [], "avd": [], "sub": [], "view": []})
        ctr = _ctr_trang_chu(goc, ma_kenh, vid)
        if ctr is not None:
            tg["ctr"].append(ctr)
        avd = _so(_moc_ho_so(hs).get("avd_giay"))
        if avd is not None:
            tg["avd"].append(avd)
        if sub is None:
            sub = _sub_theo_video(goc, ma_kenh)
        su, vw = sub.get(vid, (0.0, 0.0))
        if vw > 0:
            tg["sub"].append(su)
            tg["view"].append(vw)
    for ct, tg in gom.items():
        ra[ct]["ctr_trang_chu_tv"] = _tv(tg["ctr"])
        ra[ct]["avd_giay_tv"] = _tv(tg["avd"], 0)
        ra[ct]["sub_1k"] = round(1000.0 * sum(tg["sub"]) / sum(tg["view"]), 2) if sum(tg["view"]) else None
    return ra


# ── tỉ trọng gợi ý + tệp nghien-cuu/chien-luoc.json ─────────────────────────

def goi_y_ti_trong(tk: Dict[str, Dict[str, Any]], hien_tai: Dict[str, float]) -> Tuple[Dict[str, float], str]:
    """Cùng luật tự học của `chien_luoc.ke_hoach` (w × (thắng+1)/(n+2) ÷ trung bình, kẹp, chuẩn hoá,
    chỉ khi tổng n ≥ `TU_HOC_N_TOI_THIEU`) — nhưng CHỈ ĐỂ GHI GỢI Ý, không áp."""
    from . import TU_HOC_KEP, TU_HOC_N_TOI_THIEU  # noqa: PLC0415

    ts = {t: float(w) for t, w in hien_tai.items() if w > 0}
    tong = sum(ts.values())
    if not ts or tong <= 0:
        return {}, "chưa có công thức nào để gợi ý"
    ts = {t: w / tong for t, w in ts.items()}
    if len(ts) < 2:
        return {t: round(w, 3) for t, w in ts.items()}, "một công thức — không có gì để dồn"
    n_tong = sum(int((tk.get(t) or {}).get("n") or 0) for t in ts)
    if n_tong < TU_HOC_N_TOI_THIEU:
        return ({t: round(w, 3) for t, w in ts.items()},
                "giữ nguyên — mới {0}/{1} video đã có kết luận".format(n_tong, TU_HOC_N_TOI_THIEU))
    he = {t: (int((tk.get(t) or {}).get("thang") or 0) + 1) / (int((tk.get(t) or {}).get("n") or 0) + 2)
          for t in ts}
    tb = sum(he.values()) / len(he)
    moi = {t: min(TU_HOC_KEP[1], max(TU_HOC_KEP[0], w * he[t] / tb)) for t, w in ts.items()}
    tong = sum(moi.values())
    return ({t: round(w / tong, 3) for t, w in moi.items()},
            "dồn theo tỉ lệ thắng trên {0} video đã có kết luận".format(n_tong))


def _ti_trong_hien_tai(goc: str, ma_kenh: str, tk: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, float], str]:
    """Tỉ trọng đang khai (`kenh.yaml: chien_luoc`), hoặc — chưa khai / `tu_dong` — chia đều cho các
    công thức ĐÃ có lượt trong sổ và có trong sổ đăng ký."""
    from . import KHOA_CHIEN_LUOC, _phan_tich, so_dang_ky  # noqa: PLC0415

    try:
        from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        cau = str((doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)) or {})
                  .get(KHOA_CHIEN_LUOC) or "").strip()
    except Exception:  # noqa: BLE001
        cau = ""
    so = so_dang_ky()
    if cau and cau.lower() != "tu_dong":
        ts: Dict[str, float] = {}
        for ten, w in _phan_tich(cau):
            if ten in so and w > 0:
                ts[ten] = ts.get(ten, 0.0) + w
        if ts:
            return ts, "kenh.yaml {0}: {1}".format(KHOA_CHIEN_LUOC, cau)
    co = [t for t in tk if t in so]
    return ({t: 1.0 for t in co},
            "chưa khai {0} — chia đều các công thức đã có lượt".format(KHOA_CHIEN_LUOC) if not cau
            else "{0}: tu_dong — chia đều các công thức đã có lượt".format(KHOA_CHIEN_LUOC))


def duong_tep(goc: str, ma_kenh: str) -> str:
    from ..doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    return os.path.join(thu_muc_nghien_cuu(goc, ma_kenh), TEP_CHIEN_LUOC)


def dong_tom_tat(tk: Dict[str, Dict[str, Any]]) -> str:
    if not tk:
        return "chưa có lượt nào ghi công thức"
    return " · ".join("{0} {1} lượt/{2} kết luận/{3} thắng".format(t, o["lam"], o["n"], o["thang"])
                      for t, o in sorted(tk.items(), key=lambda kv: (-kv[1]["lam"], kv[0])))


def ghi_tep(goc: str, ma_kenh: str, *, bay_gio: Optional[_dt.datetime] = None,
            log: Optional[Callable[[str], None]] = None) -> str:
    """Ghi `nghien-cuu/chien-luoc.json` (nguyên tử) + 1 dòng log. Trả đường tệp. Lỗi ghi đĩa nổi lên
    cho nơi gọi (`vong_hoc` bọc try riêng)."""
    bay_gio = bay_gio or _dt.datetime.now()
    tk = thong_ke(goc, ma_kenh, NGAY_MAC_DINH, bay_gio=bay_gio)
    tk_het = thong_ke(goc, ma_kenh, 0, bay_gio=bay_gio)
    hien_tai, nguon_ts = _ti_trong_hien_tai(goc, ma_kenh, tk)
    goi_y, ly_do = goi_y_ti_trong(tk, hien_tai)
    _vm, nguong = video_kenh(goc, ma_kenh) if tk_het else ({}, None)
    from .. import thuoc_thang  # noqa: PLC0415
    try:
        from .. import cong_thuc_v7 as v7  # noqa: PLC0415

        muc = v7.muc_thang_kenh(list(_vm.values())) if _vm else None
    except Exception:  # noqa: BLE001
        muc = None
    du = {
        "kenh": ma_kenh, "cap_nhat_luc": bay_gio.replace(microsecond=0).isoformat(),
        "cua_so_ngay": NGAY_MAC_DINH,
        "cach_do_thang": "core.thuoc_thang v{0}: {1}".format(thuoc_thang.PHIEN_BAN, thuoc_thang.MO_TA),
        "muc_thang_96h": round(muc) if muc is not None else None,
        "nguong_thang_48h": round(nguong) if nguong is not None else None,
        "thong_ke": tk, "thong_ke_toan_bo": tk_het,
        "ti_trong_hien_tai": {t: round(w / sum(hien_tai.values()), 3) for t, w in hien_tai.items()}
        if hien_tai else {},
        "nguon_ti_trong": nguon_ts,
        "ti_trong_goi_y": goi_y, "ly_do_goi_y": ly_do,
        "da_ap": False,
        "ghi_chu": "Chỉ là GỢI Ý. Muốn tự dồn tỉ trọng: kenh.yaml chien_luoc_tu_hoc: true.",
    }
    duong = duong_tep(goc, ma_kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)
    if log is not None:
        log("  0) [vòng học] chiến lược ({0} ngày): {1} — gợi ý (chưa áp): {2} ({3}).".format(
            NGAY_MAC_DINH, dong_tom_tat(tk),
            ", ".join("{0} {1:.0%}".format(t, w) for t, w in goi_y.items()) or "—", ly_do))
    return duong
