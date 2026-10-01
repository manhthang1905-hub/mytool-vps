"""Giới hạn an toàn của giám đốc kênh — LUẬT CỨNG. LLM chỉ chọn; mọi thứ nó chọn phải qua `kiem`.

    kiem(de_xuat, so, bs) -> (duoc, ly_do)     biên, bước, ngân sách, nghỉ 14 ngày, chủ giữ, Studio
    ap(goc, ma, de_xuat, bs, …)                ghi kenh.yaml (`trung_tam.ghi_cai_kenh`) / chi-dao.json
    quay_lui(goc, ma, tn, …)                   trả giá trị `cu` của thí nghiệm
    chu_da_sua(goc, ma, bs)                    chủ sửa tay khoá giám đốc đã ghi → `chu_giu` 30 ngày
    ly_do_quay_lui(bs, tn, bao_dong)           3 cò quay lui tự động

Ngoài tầm (chỉ gợi ý trong "Việc của bạn"): `NGOAI_TAM`. Việc Studio: `giam_doc_studio: false` → CHỈ gợi ý;
`true` → `cuu_ctr.xu_ly` (hội đồng → chủ duyệt 3 lần đầu → hàng sửa `vm/logs/hang-sua.json`).
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import so_thi_nghiem as stn
from .du_lieu import BangSo, so, so_video_dang, thu_muc_giam_doc, trong_khoang

#: khoá → luật. `buoc` = bước tối đa mỗi lần đổi (mỗi khoá chỉ đổi 1 lần / 14 ngày nên cũng là / tuần).
KHOA_DUOC_DOI: Dict[str, Dict[str, Any]] = {
    "chien_luoc": {"kieu": "ti_trong", "bien": (0.1, 0.9), "buoc": 0.2},
    "chien_luoc_tham_do": {"kieu": "so", "bien": (10, 35), "buoc": 10, "mac_dinh": 20},
    "chien_luoc_tu_hoc": {"kieu": "bat"},
    "phut_muc_tieu": {"kieu": "so", "bien": (10, 25), "buoc": 3},
    "luat_chon_tuan": {"kieu": "cau", "toi_da_cau": 3},
}
NGOAI_TAM = ("tu_*", "ngan_sach_ngay", "video_toi_da_ngay", "nhip_dang", "so_ban_nhap", "voice_id", "cach_dang")
CHE_DO = ("tat", "goi_y", "tu_ap")
TOI_DA_THAM_SO_TUAN = 2
NGHI_NGAY = 14
CHU_GIU_NGAY = 30
STUDIO_TOI_DA_TUAN = 2
STUDIO_TUOI = (52.0, 120.0)      # tuổi video được cứu (giờ) — cùng `cuu_ctr.TUOI`
TRANH_PHIEN_PHUT = 60
CHI_DAO_TOI_DA_DONG = 5
CHI_DAO_TOI_DA_KY_TU = 200
CHI_DAO_HAN_TOI_DA = 21
TUT_HIEN_THI_QUAY_LUI = 0.35
TEP_CHI_DAO = "chi-dao.json"
_RE_GIO = re.compile(r"(\d{1,2}):(\d{2})")


def _luc(t: _dt.datetime) -> str:
    return t.replace(microsecond=0).isoformat()


def la_ngoai_tam(khoa: str) -> bool:
    """Khoá chỉ chủ được đổi (tiền, nhịp, giọng…)."""
    return khoa.startswith("tu_") or khoa in NGOAI_TAM


def che_do(bs: BangSo) -> str:
    """`giam_doc: tat | goi_y | tu_ap` của kênh. Kênh có cặp `-v2` tối đa `goi_y` trừ khi
    `giam_doc_cho_phep_ab: true`."""
    cd = str(bs.cai.get("giam_doc") or "tat").strip().lower()
    cd = cd if cd in CHE_DO else "tat"
    if cd == "tu_ap" and str(bs.cai.get("giam_doc_cho_phep_ab", "")).lower() != "true":
        cap = os.path.isdir(os.path.join(os.path.dirname(thu_muc_giam_doc(bs.goc, bs.ma_kenh)) + "-v2"))
        if cap or bs.ma_kenh.endswith("-v2"):
            return "goi_y"
    return cd


def khong_dung(bs: BangSo) -> set:
    """Khoá chủ cấm giám đốc chạm: `giam_doc_khong_dung: "phut_muc_tieu, …"`."""
    gt = bs.cai.get("giam_doc_khong_dung") or ""
    ds = gt if isinstance(gt, list) else str(gt).replace(";", ",").split(",")
    return {str(x).strip() for x in ds if str(x).strip()}


# ── giá trị ────────────────────────────────────────────────────────────────

def ti_trong(chuoi: Any) -> Dict[str, float]:
    """"v7:0.5, vph:0.5" hoặc dict → tỉ trọng đã chuẩn hoá (rỗng nếu `tu_dong`/không khai/hỏng)."""
    from ..chien_luoc import _chuan_hoa, _phan_tich  # noqa: PLC0415

    if isinstance(chuoi, dict):
        ts = {str(k).lower(): float(v) for k, v in chuoi.items() if so(v) is not None}
    else:
        chuoi = str(chuoi or "").strip()
        if not chuoi or chuoi.lower() == "tu_dong":
            return {}
        ts = {}
        for ten, w in _phan_tich(chuoi):
            ts[ten] = ts.get(ten, 0.0) + w
    if any(w <= 0 for w in ts.values()):
        return {}
    return _chuan_hoa(ts)


def chu_ti_trong(ts: Dict[str, float]) -> str:
    """Tỉ trọng → chuỗi kenh.yaml."""
    return ", ".join("{0}:{1:g}".format(t, round(w, 2)) for t, w in ts.items())


def cau_luat(gt: Any) -> List[str]:
    """`luat_chon_tuan` (chuỗi "a | b" hoặc list) → list câu."""
    if isinstance(gt, (list, tuple)):
        return [str(x).strip() for x in gt if str(x).strip()]
    return [x.strip() for x in str(gt or "").split("|") if x.strip()]


def gia_tri_hien_tai(bs: BangSo, khoa: str) -> Any:
    """Giá trị đang có của khoá trong kenh.yaml (có mặc định của bộ máy)."""
    gt = bs.cai.get(khoa)
    if khoa == "chien_luoc_tham_do" and gt in (None, ""):
        return KHOA_DUOC_DOI[khoa]["mac_dinh"]
    if khoa == "chien_luoc_tu_hoc":
        return str(gt).strip().lower() == "true"
    return gt


def kiem_gia_tri(khoa: str, cu: Any, moi: Any) -> Tuple[bool, str, Any]:
    """Biên + bước của một thay đổi → (được, lý do, giá trị chuẩn hoá để ghi)."""
    luat = KHOA_DUOC_DOI[khoa]
    kieu = luat["kieu"]
    if kieu == "so":
        c, m = so(cu), so(moi)
        if m is None or m != int(m):
            return False, "giá trị phải là số nguyên", None
        lo, hi = luat["bien"]
        if not lo <= m <= hi:
            return False, "ngoài biên {0}–{1}".format(lo, hi), None
        if c is None:
            return False, "giá trị hiện tại không phải số — chủ đặt tay trước", None
        if m == c:
            return False, "không đổi gì", None
        if abs(m - c) > luat["buoc"]:
            return False, "bước {0:g} vượt ±{1}".format(m - c, luat["buoc"]), None
        return True, "", int(m)
    if kieu == "bat":
        if cu is True:
            return False, "đã bật", None
        if moi is not True and str(moi).lower() != "true":
            return False, "chỉ được bật false → true", None
        return True, "", True
    if kieu == "ti_trong":
        c, m = ti_trong(cu), ti_trong(moi)
        if len(c) < 2:
            return False, "kênh chưa khai chien_luoc ≥ 2 công thức — chủ khai trước", None
        if set(m) != set(c):
            return False, "phải giữ đúng các công thức đang khai ({0})".format(", ".join(c)), None
        lo, hi = luat["bien"]
        for t, w in m.items():
            if not lo - 1e-9 <= w <= hi + 1e-9:
                return False, "{0} {1:.2f} ngoài biên {2}–{3}".format(t, w, lo, hi), None
            if abs(w - c[t]) > luat["buoc"] + 1e-9:
                return False, "{0} đổi {1:+.2f} vượt ±{2}".format(t, w - c[t], luat["buoc"]), None
        if all(abs(m[t] - c[t]) < 0.01 for t in m):
            return False, "không đổi gì", None
        return True, "", chu_ti_trong(m)
    if kieu == "cau":
        ds = cau_luat(moi)
        if not ds or len(ds) > luat["toi_da_cau"]:
            return False, "cần 1–{0} câu".format(luat["toi_da_cau"]), None
        if any(len(x) > CHI_DAO_TOI_DA_KY_TU for x in ds):
            return False, "câu dài quá {0} ký tự".format(CHI_DAO_TOI_DA_KY_TU), None
        if ds == cau_luat(cu):
            return False, "không đổi gì", None
        return True, "", " | ".join(ds)
    return False, "kiểu khoá lạ", None


# ── ngân sách ──────────────────────────────────────────────────────────────

def _tu(bay_gio: _dt.datetime, ngay: int) -> str:
    return _luc(bay_gio - _dt.timedelta(days=ngay))


def ngan_sach(so_: Dict[str, Any], bay_gio: _dt.datetime) -> Dict[str, Any]:
    """Còn được đổi bao nhiêu tuần này: tham số, việc Studio, khoá đang nghỉ, khoá chủ giữ."""
    nk = so_.get("nhat_ky") or []
    tuan = _tu(bay_gio, 7)
    da_doi = [d for d in nk if d.get("viec") == "tham_so" and str(d.get("luc")) >= tuan]
    studio = [d for d in nk if d.get("viec") == "viec_studio" and str(d.get("luc")) >= tuan]
    nghi: Dict[str, str] = {}
    for d in nk:
        if d.get("viec") in ("tham_so", "quay_lui") and d.get("khoa"):
            den = _luc(_dt.datetime.fromisoformat(str(d["luc"])[:19]) + _dt.timedelta(days=NGHI_NGAY))
            if den > _luc(bay_gio):
                nghi[str(d["khoa"])] = max(den, nghi.get(str(d["khoa"]), ""))
    chu_giu = {k: v for k, v in ((so_.get("trang_thai") or {}).get("chu_giu") or {}).items()
               if str(v) > _luc(bay_gio)}
    return {"tham_so_con": max(0, TOI_DA_THAM_SO_TUAN - len(da_doi)),
            "studio_con": max(0, STUDIO_TOI_DA_TUAN - len(studio)), "khoa_nghi": nghi, "chu_giu": chu_giu}


def gan_phien(bs: BangSo, bay_gio: _dt.datetime, phut: int = TRANH_PHIEN_PHUT) -> str:
    """"HH:MM" nếu có giờ đăng (`gio_dang`, `nhip_dang`) trong `phut` phút tới; rỗng nếu không."""
    chu = "{0},{1}".format(bs.cai.get("gio_dang") or "", bs.cai.get("nhip_dang") or "")
    for h, m in _RE_GIO.findall(chu):
        try:
            t = bay_gio.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        except ValueError:
            continue
        for lech in (0, 1):  # giờ đăng ngay sau nửa đêm
            if _dt.timedelta(0) <= t + _dt.timedelta(days=lech) - bay_gio <= _dt.timedelta(minutes=phut):
                return "{0:02d}:{1:02d}".format(int(h), int(m))
    return ""


# ── kiểm ───────────────────────────────────────────────────────────────────

def kiem(de_xuat: Dict[str, Any], so_: Dict[str, Any], bs: BangSo, *,
         bay_gio: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """Một đề xuất có được phép không. Trả (được, lý do). Mọi khoá/giá trị lạ đều bị loại."""
    bay_gio = bay_gio or bs.bay_gio
    loai = de_xuat.get("loai")
    ns = ngan_sach(so_, bay_gio)
    if loai == "tham_so":
        khoa = str(de_xuat.get("khoa") or "")
        if la_ngoai_tam(khoa):
            return False, "khoá {0} ngoài tầm — chỉ chủ đổi".format(khoa)
        if khoa not in KHOA_DUOC_DOI:
            return False, "khoá {0} không nằm trong danh sách được đổi".format(khoa)
        if khoa in khong_dung(bs):
            return False, "chủ cấm giám đốc chạm {0} (giam_doc_khong_dung)".format(khoa)
        if khoa in ns["chu_giu"]:
            return False, "chủ đã sửa tay {0} — giữ tới {1}".format(khoa, ns["chu_giu"][khoa][:10])
        if khoa in ns["khoa_nghi"]:
            return False, "{0} vừa đổi — nghỉ tới {1}".format(khoa, ns["khoa_nghi"][khoa][:10])
        if ns["tham_so_con"] <= 0:
            return False, "hết ngân sách {0} tham số/tuần".format(TOI_DA_THAM_SO_TUAN)
        cs = str(de_xuat.get("chi_so") or "")
        if cs and stn.dang_mo(so_, cs):
            return False, "đã có thí nghiệm mở trên chỉ số {0}".format(cs)
        ok, ly, _gt = kiem_gia_tri(khoa, gia_tri_hien_tai(bs, khoa), de_xuat.get("gia_tri"))
        return ok, ly
    if loai == "chi_dao":
        nd = str(de_xuat.get("noi_dung") or "").strip()
        if not nd:
            return False, "chỉ đạo rỗng"
        if len(nd) > CHI_DAO_TOI_DA_KY_TU:
            return False, "chỉ đạo dài quá {0} ký tự".format(CHI_DAO_TOI_DA_KY_TU)
        han = so(de_xuat.get("han_ngay"))
        if han is None or not 1 <= han <= CHI_DAO_HAN_TOI_DA:
            return False, "hạn chỉ đạo phải 1–{0} ngày".format(CHI_DAO_HAN_TOI_DA)
        return True, ""
    if loai == "viec_studio":
        v = bs.video_theo_id(str(de_xuat.get("video_id") or ""))
        if v is None:
            return False, "không có video này trong số của kênh"
        if v.get("thang"):
            return False, "video đang thắng — không bao giờ đụng"
        if v.get("ket_luan") != "truot":
            return False, "video chưa bị phán trượt"
        if v.get("tuoi_gio") is not None and not STUDIO_TUOI[0] <= float(v["tuoi_gio"]) <= STUDIO_TUOI[1]:
            return False, "video {0:.0f}h tuổi — chỉ cứu video {1:.0f}–{2:.0f}h".format(
                float(v["tuoi_gio"]), STUDIO_TUOI[0], STUDIO_TUOI[1])
        if not v.get("ma_goi"):
            return False, "video không có hồ sơ của tool"
        if v.get("lich_su_sua") or any(d.get("viec") == "viec_studio" and d.get("video_id") == v["id"]
                                       for d in so_.get("nhat_ky") or []):
            return False, "video đã sửa một lần — không sửa lần hai"
        if ns["studio_con"] <= 0:
            return False, "hết {0} lần sửa Studio/tuần".format(STUDIO_TOI_DA_TUAN)
        gio = gan_phien(bs, bay_gio)
        if gio:
            return False, "sắp tới phiên đăng {0} — không sửa trong 60 phút trước phiên".format(gio)
        return True, ""
    return False, "loại đề xuất lạ: {0}".format(loai)


# ── áp / quay lui ──────────────────────────────────────────────────────────

def _ghi_yaml_mac_dinh(goc: str, ma: str, **khoa: Any) -> None:
    from ..trung_tam import ghi_cai_kenh  # noqa: PLC0415

    ghi_cai_kenh(goc, ma, **khoa)


def doc_chi_dao(goc: str, ma: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Chỉ đạo còn hạn của kênh (≤ 5 dòng) — biên tập viên đọc như tiêu chí tuần (tay mềm)."""
    try:
        with io.open(os.path.join(thu_muc_giam_doc(goc, ma), TEP_CHI_DAO), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return []
    bay = _luc(bay_gio or _dt.datetime.now())
    ds = du.get("chi_dao") if isinstance(du, dict) else None
    return [d for d in ds or [] if isinstance(d, dict) and str(d.get("het_han") or "") > bay][-CHI_DAO_TOI_DA_DONG:]


def ap(goc: str, ma: str, de_xuat: Dict[str, Any], bs: BangSo, *, ly_do_llm: str = "",
       bay_gio: Optional[_dt.datetime] = None, ghi_yaml: Optional[Callable[..., None]] = None) -> Dict[str, Any]:
    """Áp MỘT đề xuất đã qua `kiem`. Tham số → kenh.yaml + mở thí nghiệm; chỉ đạo → chi-dao.json;
    việc Studio đợt 1 → chỉ gợi ý (không vào hàng). Trả {"ket", …}."""
    bay_gio = bay_gio or bs.bay_gio
    loai = de_xuat.get("loai")
    if loai == "tham_so":
        khoa = de_xuat["khoa"]
        cu = gia_tri_hien_tai(bs, khoa)
        ok, ly, moi = kiem_gia_tri(khoa, cu, de_xuat.get("gia_tri"))
        if not ok:
            return {"ket": "tu_choi", "ly_do": ly}
        (ghi_yaml or _ghi_yaml_mac_dinh)(goc, ma, **{khoa: moi})
        tn = None
        if de_xuat.get("chi_so") and int(de_xuat.get("co_mau") or 0) > 0:
            tn = stn.mo(goc, ma, viec=str(de_xuat.get("plugin") or de_xuat.get("viec") or khoa), gia_thuyet=str(de_xuat.get("gia_thuyet") or ""),
                        bien={"loai": "tham_so", "khoa": khoa, "cu": cu, "moi": moi}, chi_so=de_xuat["chi_so"],
                        nen=dict(de_xuat.get("nen") or {}), co_mau=int(de_xuat["co_mau"]),
                        han_ngay=int(de_xuat.get("han_ngay") or 21), ly_do_llm=ly_do_llm,
                        tut_pct=float(de_xuat.get("tut_pct") or 20), bay_gio=bay_gio)
        stn.ghi_nhat_ky(goc, ma, viec="tham_so", khoa=khoa, truoc=cu, sau=moi, ly_do_llm=ly_do_llm,
                        so_lieu=de_xuat.get("so_lieu"), thi_nghiem=tn["id"] if tn else "", bay_gio=bay_gio)
        stn.ghi_trang_thai(goc, ma, da_ghi={khoa: {"gia_tri": moi, "luc": _luc(bay_gio)}})
        return {"ket": "da_ap", "khoa": khoa, "truoc": cu, "sau": moi, "thi_nghiem": tn["id"] if tn else ""}
    if loai == "chi_dao":
        ds = doc_chi_dao(goc, ma, bay_gio)
        nd = str(de_xuat.get("noi_dung") or "").strip()[:CHI_DAO_TOI_DA_KY_TU]
        ds = [d for d in ds if d.get("noi_dung") != nd]
        ds.append({"noi_dung": nd, "tu": _luc(bay_gio), "viec": de_xuat.get("viec") or "",
                   "het_han": _luc(bay_gio + _dt.timedelta(days=int(so(de_xuat.get("han_ngay")) or 7)))})
        stn._ghi_json(os.path.join(thu_muc_giam_doc(goc, ma), TEP_CHI_DAO),  # noqa: SLF001
                      {"kenh": ma, "chi_dao": ds[-CHI_DAO_TOI_DA_DONG:]})
        stn.ghi_nhat_ky(goc, ma, viec="chi_dao", sau=nd, ly_do_llm=ly_do_llm, bay_gio=bay_gio)
        return {"ket": "da_ap", "noi_dung": nd}
    if loai == "viec_studio":
        return {"ket": "chi_goi_y", "video_id": de_xuat.get("video_id"), "noi_dung": de_xuat.get("noi_dung")}
    return {"ket": "tu_choi", "ly_do": "loại lạ"}


def quay_lui(goc: str, ma: str, tn: Dict[str, Any], *, ly_do: str, trang_thai: str = "quay_lui",
             bay_gio: Optional[_dt.datetime] = None, ghi_yaml: Optional[Callable[..., None]] = None) -> Dict[str, Any]:
    """Trả khoá của thí nghiệm về giá trị `cu`, đóng thí nghiệm (`quay_lui` hoặc `chua_du`)."""
    bay_gio = bay_gio or _dt.datetime.now()
    bien = tn.get("bien") or {}
    khoa, cu = bien.get("khoa"), bien.get("cu")
    if bien.get("loai") == "tham_so" and khoa in KHOA_DUOC_DOI and cu is not None:
        (ghi_yaml or _ghi_yaml_mac_dinh)(goc, ma, **{khoa: cu})
        stn.ghi_trang_thai(goc, ma, da_ghi={khoa: {"gia_tri": cu, "luc": _luc(bay_gio)}})
    if tn.get("trang_thai") == "mo":
        stn.dong(goc, ma, tn["id"], trang_thai, ly_do=ly_do, bay_gio=bay_gio)
    stn.ghi_nhat_ky(goc, ma, viec="quay_lui", khoa=khoa, truoc=bien.get("moi"), sau=cu, ly_do_llm=ly_do,
                    thi_nghiem=tn.get("id"), bay_gio=bay_gio)
    return {"ket": "da_quay_lui", "khoa": khoa, "sau": cu}


def _bang_nhau(a: Any, b: Any) -> bool:
    if so(a) is not None and so(b) is not None:
        return abs(so(a) - so(b)) < 1e-9
    ta, tb = ti_trong(a), ti_trong(b)
    if ta or tb:
        return ta.keys() == tb.keys() and all(abs(ta[k] - tb[k]) < 0.01 for k in ta)
    return str(a).strip().lower() == str(b).strip().lower()


def chu_da_sua(goc: str, ma: str, bs: BangSo, *, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Khoá giám đốc đã ghi mà kenh.yaml giờ khác → chủ sửa tay: giữ `chu_giu` 30 ngày, quên `da_ghi`."""
    bay_gio = bay_gio or bs.bay_gio
    tt = stn.doc_trang_thai(goc, ma)
    da_ghi = dict(tt.get("da_ghi") or {})
    sua = [k for k, v in da_ghi.items() if not _bang_nhau(gia_tri_hien_tai(bs, k), (v or {}).get("gia_tri"))]
    if sua:
        han = _luc(bay_gio + _dt.timedelta(days=CHU_GIU_NGAY))
        tt["chu_giu"] = dict(tt.get("chu_giu") or {}, **{k: han for k in sua})
        tt["da_ghi"] = {k: v for k, v in da_ghi.items() if k not in sua}
        stn._ghi_json(os.path.join(thu_muc_giam_doc(goc, ma), stn.TEP_TRANG_THAI), tt)  # noqa: SLF001
        for k in sua:
            stn.ghi_nhat_ky(goc, ma, viec="chu_sua", khoa=k, truoc=da_ghi[k].get("gia_tri"),
                            sau=gia_tri_hien_tai(bs, k), bay_gio=bay_gio)
    return sua


def ly_do_quay_lui(bs: BangSo, tn: Dict[str, Any], *, bao_dong: bool = False,
                   ket_luan: Optional[Dict[str, Any]] = None) -> str:
    """Một trong ba cò → câu lý do; rỗng = giữ. `ket_luan` = kết quả `ket_luan` của plugin (có `so`)."""
    if bao_dong:
        return "sức khoẻ kênh báo động"
    bat_dau = _dt.datetime.fromisoformat(str(tn.get("bat_dau"))[:19])
    if (bs.bay_gio - bat_dau).days >= 7:
        nen = trong_khoang(bs, "hien_thi", bat_dau - _dt.timedelta(days=14), bat_dau)
        sau = trong_khoang(bs, "hien_thi", bs.bay_gio - _dt.timedelta(days=7), bs.bay_gio)
        dang_nen = so_video_dang(bs, bat_dau - _dt.timedelta(days=14), bat_dau)
        dang_sau = so_video_dang(bs, bs.bay_gio - _dt.timedelta(days=7), bs.bay_gio)
        if nen and sau is not None and dang_sau / 7.0 >= 0.5 * dang_nen / 14.0:  # không phải do ngừng đăng
            if sau / 7.0 < (1 - TUT_HIEN_THI_QUAY_LUI) * nen / 14.0:
                return "hiển thị kênh 7 ngày tụt {0:.0%} so với nền 14 ngày trước khi áp (vẫn đăng {1} video)".format(
                    1 - (sau / 7.0) / (nen / 14.0), dang_sau)
    s = (ket_luan or {}).get("so") or {}
    nen_gt, moi_gt, n = so(s.get("nen")), so(s.get("moi")), int(s.get("n") or 0)
    tut = float((tn.get("quay_lui_khi") or {}).get("tut_pct") or 20)
    if nen_gt and moi_gt is not None and n >= 3 and moi_gt < nen_gt * (1 - tut / 100.0):
        return "{0} tệ hơn nền {1:.0%} (n={2}, ngưỡng {3:g}%)".format(tn.get("chi_so"), 1 - moi_gt / nen_gt, n, tut)
    return ""
