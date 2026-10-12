"""KHO ĐẶC TRƯNG chung của mọi giả thuyết — một dòng mỗi ứng viên, mọi đặc trưng các bộ chấm cần.

Đặc trưng GỐC (ghi vào ảnh chụp ngày `CHANNEL/<k>/phong-thi-nghiem/kho-<ngày>.csv.gz`, cột `COT_KHO`):

  nguồn & số     nguon (doi_thu|pool|trang_chu), kenh_nguon, view, luc (giờ quét epoch), ngay_dang, tuoi_ngay,
                 dai_phut, tang_ngay (Tăng/ngày của sổ), vph_doi (view/giờ cả đời)
  so kênh nguồn  view_tv (trung vị view/kênh), vuot (= view / view_tv), kenh_ai (1 làm bằng AI / 0 người thật),
                 kenh_subs, kenh_ngach (giu|nghi|?), kenh_cach_dang (ngày từ video dài mới nhất), kenh_ro
  bộ chấm có sẵn v7_diem, v7_hang (bảng V7 của ngày, điểm phiên bản 5), vph_diem, vph_hang (VPH thật khi chạy hằng
                 ngày; chạy ngược = bản xấp xỉ `vph_xap_xi`), vph_nguon
  nghĩa          cum (cụm V7: AI đã phân / từ khoá), nhan_y (nhãn theo nghĩa `cum_y_nghia`), vung (vùng đề tài),
                 vung_chu, vung_cua_minh, vung_cua_anh_em, vung_thi_truong (view đối thủ 28 ngày), vung_thi_phan (%
                 của ta), vung_tang (log2 thị trường so ~7 ngày trước)
  pool           trong_pool, pool_xem, pool_hien_thi, pool_so_video, pool_diem (cầu nối: bấm thật/kỳ vọng × xem có
                 trọng số AVD), pool_thang_xem (lượt xem từ bảng của video THẮNG), pool_cum_xem (lượt xem pool cùng
                 cụm), pool_kenh_xem (lượt xem pool từ cùng kênh nguồn)
  trang chủ      tc_ngay (số ngày hiện trong 14 ngày), tc_lan, tc_kenh (số dòng của kênh nguồn trong 14 ngày),
                 tc_cach_ngay (ngày từ lần thấy cuối)
  giống thắng    thang_cum (cùng cụm với video THẮNG của kênh), giong_thang_chu (bigram Jaccard tiêu đề với video
                 thắng/nguồn của nó), giong_thang_ai (AI V7: % trùng đề tài khi video trùng là video thắng),
                 giong_minh_chu (giống nhất với MỌI video/nguồn đã làm — chống làm lại y hệt), co_thang (kênh có thắng)
  đà            da_tang_3n (view tăng/ngày ~3 ngày qua ÷ trung vị kênh, từ ảnh chụp trước)

Đặc trưng DẪN XUẤT (`mo_rong`, tính lại khi đọc ảnh chụp — không ghi): log_vuot, log_view, dai_tot (12–21 phút),
dai_tam (8–30), tang_duong, log_pool_*, log_thi_truong, vung_chua_chu, co_doi_thu/co_pool/co_trang_chu, tre_*.

Hàm thuần trên `TheGioi` + `VuTru`. Không mạng, không AI.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import _chung as c
from .nguon import TheGioi
from .vu_tru import NGUON_DOI_THU, NGUON_POOL, NGUON_TRANG_CHU, NGAY_TRANG_CHU, VuTru

#: Hằng số làm mượt của điểm cầu nối pool (như `cong_thuc_v7` khối `pool.k`).
K_POOL = 10.0
#: VPH xấp xỉ (cùng hằng `cong_thuc_vph.CAU_HINH_MAC_DINH`).
VPH_DAI = (72.0, 168.0, 720.0, 4320.0)
VPH_HE_TRE = {"72": 1.0, "168": 0.8, "720": 0.5, "cu_dang_but": 0.45}
VPH_SAN_VIEW = 3000.0
VPH_NGUONG = 2.0
VPH_TRAN = 50.0
VPH_KHUON = (8.0, 40.0)
VPH_TRONG_SO = {"dot_bien": 0.5, "vph": 0.2, "tre": 0.15, "phu": 0.15}

COT_KHO = [
    "ma", "kenh_nguon", "tieu_de", "nguon", "view", "luc", "ngay_dang", "tuoi_ngay", "dai_phut", "tang_ngay",
    "vph_doi", "view_tv", "vuot", "kenh_ai", "kenh_subs", "kenh_ngach", "kenh_cach_dang", "kenh_ro",
    "v7_diem", "v7_hang", "vph_diem", "vph_hang", "vph_nguon", "cum", "nhan_y", "vung", "vung_chu",
    "vung_cua_minh", "vung_cua_anh_em", "vung_thi_truong", "vung_thi_phan", "vung_tang",
    "trong_pool", "pool_xem", "pool_hien_thi", "pool_so_video", "pool_diem", "pool_thang_xem", "pool_cum_xem",
    "pool_kenh_xem", "tc_ngay", "tc_lan", "tc_kenh", "tc_cach_ngay", "thang_cum", "giong_thang_chu",
    "giong_thang_ai", "giong_minh_chu", "co_thang", "da_tang_3n", "tuyen_nhan",
]
#: Cột chữ (còn lại là số; đọc lại ảnh chụp thì đổi về float/None). `tieu_de_viet`/`mo_ta` chỉ có trong bộ nhớ
#: (H-AI đọc) — không ghi vào ảnh chụp cho nhẹ đĩa (~6.000 dòng/kênh/ngày).
COT_CHU = {"ma", "kenh_nguon", "tieu_de", "nguon", "ngay_dang", "kenh_ngach", "vph_nguon", "cum", "nhan_y", "vung",
           "vung_chu", "tuyen_nhan", "tieu_de_viet", "mo_ta"}
DAI_TIEU_DE_GHI = 80


# ── tiêu đề → tập bigram (so giống nhanh) ───────────────────────────────────

_RE_NGOAC = re.compile(r"【[^】]*】|\[[^\]]*\]|［[^］]*］|#\S+")
_RE_BO = re.compile(r"[\s\W_]+", re.UNICODE)


def bigram(td: str) -> Set[str]:
    s = unicodedata.normalize("NFKC", _RE_NGOAC.sub(" ", str(td or ""))).lower()
    s = _RE_BO.sub("", s)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else ({s} if s else set())


def giong(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


# ── VPH xấp xỉ trên ảnh chụp sổ ────────────────────────────────────────────

def _dai(t: float) -> int:
    for i, m in enumerate(VPH_DAI):
        if t <= m:
            return i
    return len(VPH_DAI)


def _trung_vi_dai(gia: Dict[int, List[float]], dai: int, can: int = 3) -> Optional[float]:
    ds = list(gia.get(dai, []))
    if len(ds) >= can:
        return c.trung_vi(ds)
    for ke in (dai - 1, dai + 1):
        ds += gia.get(ke, [])
    return c.trung_vi(ds) if len(ds) >= can else None


def _hang_pt(xs: Sequence[float]) -> List[float]:
    try:
        from ..cham_diem_content import hang_phan_tram  # noqa: PLC0415

        return list(hang_phan_tram(list(xs)))
    except Exception:  # noqa: BLE001
        n = len(xs)
        if n <= 1:
            return [0.0] * n
        o = sorted(range(n), key=lambda i: xs[i])
        r = [0.0] * n
        for vt, i in enumerate(o):
            r[i] = vt / (n - 1.0)
        return r


def vph_xap_xi(tg: TheGioi, dong: Sequence[Dict[str, Any]]) -> Dict[str, Tuple[float, int]]:
    """`{mã: (điểm 0–100, hạng)}` — CÔNG THỨC VPH (`core/cong_thuc_vph.py`) dựng lại trên ảnh chụp sổ của ngày (chạy
    ngược không có bảng VPH lưu lại). Bỏ phần "khán giả cũng xem" và tuyến chưa gán (VPH thật cũng bỏ dòng chưa gán
    tuyến). Sai số: tuổi theo NGÀY đăng (giữa ngày), giờ quét theo `Quét lúc` của kênh."""
    from .nguon import luc_quet_kenh  # noqa: PLC0415

    luc_k = luc_quet_kenh(tg.danh_ba)
    theo_kenh: Dict[str, Dict[int, List[float]]] = {}
    ngach: Dict[int, List[float]] = {}
    for r in tg.sach:
        v = c.so(r.get("View"))
        t0 = c.epoch_ngay_dang(r.get("Ngày đăng"))
        ten = str(r.get("Kênh") or "").strip()
        if not v or t0 is None:
            continue
        luc = luc_k.get(ten) or tg.luc_quet_sach or tg.moc
        tuoi = max(6.0, (luc - t0) / 3600.0)
        d = _dai(tuoi)
        theo_kenh.setdefault(ten, {}).setdefault(d, []).append(v / tuoi)
        ngach.setdefault(d, []).append(v / tuoi)
    tuyen = set(tg.tuyen or [])
    ung = []
    for u in dong:
        if NGUON_DOI_THU not in u["nguon"] or not u.get("view") or not u.get("ngay_dang"):
            continue
        if tuyen and u.get("tuyen_nhan") not in tuyen:
            continue
        ph = u.get("dai_phut")
        if ph is not None and not (VPH_KHUON[0] <= ph <= VPH_KHUON[1]):
            continue
        if u["view"] < VPH_SAN_VIEW:
            continue
        t0 = c.epoch_ngay_dang(u["ngay_dang"])
        if t0 is None:
            continue
        tuoi = max(6.0, (u["luc"] - t0) / 3600.0)
        vph_doi = u["view"] / tuoi
        vph_gan = None
        if tuoi > VPH_DAI[0] and (u.get("tang_ngay") or 0) > 0 and (u.get("view_truoc") or 0) > 0:
            vph_gan = float(u["tang_ngay"]) / 24.0
        vph = vph_gan if vph_gan is not None else vph_doi
        but = vph_gan is not None and vph_doi > 0 and vph_gan / vph_doi >= 1.5
        if tuoi <= 72:
            he = VPH_HE_TRE["72"]
        elif tuoi <= 168:
            he = VPH_HE_TRE["168"]
        elif tuoi <= 720:
            he = VPH_HE_TRE["720"]
        elif but:
            he = VPH_HE_TRE["cu_dang_but"]
        else:
            continue
        d = _dai(tuoi)
        mk = _trung_vi_dai(theo_kenh.get(u["kenh_nguon"], {}), d)
        mn = _trung_vi_dai(ngach, d)
        ty = [x for x in ((min(VPH_TRAN, vph_doi / mk) if mk else None), (min(VPH_TRAN, vph_doi / mn) if mn else None))
              if x]
        db = math.sqrt(ty[0] * ty[1]) if len(ty) == 2 else (ty[0] if ty else 0.0)
        if but and tuoi > 720:
            db = max(db, min(6.0, vph_gan / vph_doi))
        if db < VPH_NGUONG:
            continue
        ung.append((u["ma"], db, he, vph, u.get("_tc_ngay", 0), u.get("_tc_kenh", 0)))
    if not ung:
        return {}
    thuoc = {"dot_bien": _hang_pt([math.log(1 + x[1] * x[2]) for x in ung]),
             "vph": _hang_pt([math.log1p(x[3]) for x in ung]),
             "tre": _hang_pt([x[2] for x in ung]),
             "phu": _hang_pt([math.log1p(x[4]) + 0.3 * math.log1p(x[5]) for x in ung])}
    co = {t: any(v) for t, v in thuoc.items()}
    tong = sum(VPH_TRONG_SO[t] for t, v in co.items() if v)
    diem = []
    for i, x in enumerate(ung):
        d = 100.0 * sum(VPH_TRONG_SO[t] * thuoc[t][i] for t in thuoc if co[t]) / tong if tong > 0 else 0.0
        diem.append((x[0], round(d, 1), x[1], x[3]))
    diem.sort(key=lambda y: (-y[1], -y[2], -y[3], y[0]))
    return {m: (d, i + 1) for i, (m, d, _db, _v) in enumerate(diem)}


# ── dựng kho ────────────────────────────────────────────────────────────────

def _vung_cua(nhan: str, link_ma: str, vung_ai: Dict[str, str]) -> str:
    try:
        from ..chu_quyen_vung import vung_cua_nhan  # noqa: PLC0415

        return vung_cua_nhan(nhan, "https://www.youtube.com/watch?v=" + link_ma if link_ma else "", vung_ai)
    except Exception:  # noqa: BLE001
        return str(nhan or "") if nhan and nhan != "khac" else ""


def _view_truoc(ls: Sequence[Tuple[float, float]], luc: float) -> Optional[Tuple[float, float]]:
    """Bản quan sát ~3 ngày trước `luc` (trong [luc − 6 ngày, luc − 1,5 ngày]) gần 3 ngày nhất."""
    ds = [(t, v) for t, v in ls if luc - 6 * c.NGAY_GIAY <= t <= luc - 1.5 * c.NGAY_GIAY]
    if not ds:
        return None
    return min(ds, key=lambda x: abs((luc - x[0]) - 3 * c.NGAY_GIAY))


def dung_kho(tg: TheGioi, vt: VuTru) -> List[Dict[str, Any]]:
    """Kho đặc trưng của vũ trụ `vt` (xem đầu tệp). Mỗi dòng là dict số/chữ (đã có cả đặc trưng dẫn xuất)."""
    cum_cua: Callable[[str], List[str]] = tg.cum_cua or (lambda _td: [])
    nhan_y: Callable[[str], str] = tg.nhan_y or (lambda _td: "")
    nho_cum: Dict[str, List[str]] = {}

    def cum(td: str) -> List[str]:
        if td not in nho_cum:
            try:
                nho_cum[td] = [x for x in (cum_cua(td) or []) if x]
            except Exception:  # noqa: BLE001
                nho_cum[td] = []
        return nho_cum[td]

    # ── pool ──
    sach_kenh = {}
    for r in tg.sach:
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", str(r.get("Link video") or ""))
        if m:
            sach_kenh.setdefault(m.group(1), str(r.get("Kênh") or "").strip())
    p_ag: Dict[str, List[float]] = {}
    p_vid: Dict[str, Set[str]] = {}
    p_thang: Dict[str, float] = {}
    p_cum: Dict[str, float] = {}
    p_kenh: Dict[str, float] = {}
    for p in tg.pool:
        g = p_ag.setdefault(p["ma"], [0.0, 0.0, 0.0, 0.0, 0.0])
        ht, xem = float(p.get("hien_thi") or 0), float(p.get("xem") or 0)
        if ht and p.get("bam") is not None and p.get("bam_tb") is not None:
            g[0] += ht * float(p["bam"]) / 100.0
            g[1] += ht * float(p["bam_tb"]) / 100.0
        if xem and p.get("avd") is not None and p.get("avd_tb"):
            g[2] += xem * float(p["avd"]) / float(p["avd_tb"])
            g[3] += xem
        g[4] += ht
        p_vid.setdefault(p["ma"], set()).add(p.get("video_minh", ""))
        if p.get("thang"):
            p_thang[p["ma"]] = p_thang.get(p["ma"], 0.0) + xem
        ny_p = nhan_y(p.get("tieu_de", ""))
        for cm_p in set(cum(p.get("tieu_de", ""))) | ({ny_p} if ny_p and ny_p != "khac" else set()):
            p_cum[cm_p] = p_cum.get(cm_p, 0.0) + xem
        k = sach_kenh.get(p["ma"])
        if k:
            p_kenh[k] = p_kenh.get(k, 0.0) + xem
    # ── trang chủ (14 ngày) ──
    tu_tc = c.cong_ngay(tg.ngay, -(NGAY_TRANG_CHU - 1))
    het = tg.ngay + " 99"
    tc_ngay: Dict[str, Set[str]] = {}
    tc_lan: Dict[str, int] = {}
    tc_kenh: Dict[str, int] = {}
    tc_cuoi: Dict[str, str] = {}
    for r in tg.trang_chu:
        lq = str(r.get("Lúc quét") or "")[:16]
        if not lq or lq > het or lq[:10] < tu_tc or str(r.get("Short") or "").strip():
            continue
        ma = str(r.get("Mã video") or "")
        if ma:
            tc_ngay.setdefault(ma, set()).add(lq[:10])
            tc_lan[ma] = tc_lan.get(ma, 0) + 1
            tc_cuoi[ma] = max(tc_cuoi.get(ma, ""), lq[:10])
        ten = str(r.get("Kênh") or "").strip()
        if ten:
            tc_kenh[ten] = tc_kenh.get(ten, 0) + 1
    # ── video mình: thắng / mọi video ──
    thang = [v for v in tg.video_minh if v.get("nhan") == "thang" or v.get("nong")]
    thang_bg = [bigram(t) for v in thang for t in (v.get("tieu_de"), v.get("nguon_td")) if t]
    thang_cum: Set[str] = set()
    for v in thang:
        for t in (v.get("tieu_de"), v.get("nguon_td")):
            if t:
                thang_cum.update(cum(t))
                ny = nhan_y(t)
                if ny and ny != "khac":
                    thang_cum.add(ny)
    minh_bg = [bigram(t) for v in tg.video_minh for t in (v.get("tieu_de"), v.get("nguon_td")) if t]
    thang_ma = {v["ma"] for v in thang}
    # ── vùng ──
    vung_map = (tg.ban_do_vung or {}).get("vung") or {}
    anh_em = set(tg.anh_em or []) - {tg.kenh}
    # Lượt đầu: đặc trưng thô của từng ứng viên (VPH xấp xỉ cần tc_*).
    for u in vt.ung_vien:
        u["_tc_ngay"] = len(tc_ngay.get(u["ma"], ()))
        u["_tc_kenh"] = tc_kenh.get(u.get("kenh_nguon", ""), 0)
    vph_xx = vph_xap_xi(tg, vt.ung_vien) if not tg.vph else {}
    ra: List[Dict[str, Any]] = []
    for u in vt.ung_vien:
        ma, td = u["ma"], u.get("tieu_de", "")
        o = vt.kenh.get(u.get("kenh_nguon", "")) or {}
        tv = o.get("view_tv")
        view = u.get("view")
        t0 = c.epoch_ngay_dang(u.get("ngay_dang"))
        tuoi = ((u.get("luc") or tg.moc) - t0) / c.NGAY_GIAY if t0 is not None else None
        d: Dict[str, Any] = {
            "ma": ma, "kenh_nguon": u.get("kenh_nguon", ""), "tieu_de": td, "nguon": "|".join(sorted(u["nguon"])),
            "view": view, "luc": round(float(u.get("luc") or tg.moc), 0), "ngay_dang": u.get("ngay_dang", ""),
            "tuoi_ngay": c.lam_tron(tuoi, 2), "dai_phut": c.lam_tron(u.get("dai_phut"), 2),
            "tang_ngay": u.get("tang_ngay"),
            "vph_doi": c.lam_tron(view / max(6.0, tuoi * 24.0), 2) if (view and tuoi is not None) else None,
            "view_tv": tv, "vuot": c.lam_tron(view / tv, 3) if (view and tv) else None,
            "kenh_ai": 1.0 if o.get("ai") == "có" else (0.0 if o.get("ai") == "không" else None),
            "kenh_subs": o.get("subs"), "kenh_ngach": o.get("ngach", "") if o else "",
            "kenh_cach_dang": o.get("cach_dang"), "kenh_ro": float(u.get("kenh_ro", 1)),
            "tuyen_nhan": u.get("tuyen_nhan", ""), "tieu_de_viet": u.get("tieu_de_viet", ""),
            "mo_ta": u.get("mo_ta", ""),
        }
        v7 = tg.v7.get(ma)
        d["v7_diem"] = v7.get("diem") if v7 else None
        d["v7_hang"] = v7.get("hang") if v7 else None
        if tg.vph:
            x = tg.vph.get(ma)
            d["vph_diem"], d["vph_hang"], d["vph_nguon"] = (x["diem"], x["hang"], "that") if x else (None, None, "")
        else:
            x2 = vph_xx.get(ma)
            d["vph_diem"], d["vph_hang"], d["vph_nguon"] = (x2[0], x2[1], "xap_xi") if x2 else (None, None, "")
        cm = cum(td)
        ny = nhan_y(td)
        d["cum"] = "|".join(cm)
        d["nhan_y"] = ny
        vung = _vung_cua(ny or (cm[0] if cm else ""), ma, tg.vung_ai)
        m = vung_map.get(vung) if vung else None
        m = m if isinstance(m, dict) else {}
        chu = str(m.get("chu") or "")
        chia = list(m.get("chia_se") or [])
        nhuong = bool(m.get("nhuong"))
        tt_v = tg.thi_truong.get(vung) or {}
        d.update(vung=vung, vung_chu=chu, vung_cua_minh=1.0 if chu and chu == tg.kenh else 0.0,
                 vung_cua_anh_em=1.0 if (chu in anh_em and tg.kenh not in chia and not nhuong) else 0.0,
                 vung_thi_truong=tt_v.get("dich"), vung_thi_phan=tt_v.get("thi_phan"), vung_tang=tt_v.get("tang"))
        g = p_ag.get(ma)
        if g:
            b = (g[0] + K_POOL) / (g[1] + K_POOL)
            x = (g[2] + K_POOL) / (g[3] + K_POOL)
            d.update(trong_pool=1.0, pool_xem=g[3], pool_hien_thi=g[4], pool_so_video=float(len(p_vid.get(ma, ()))),
                     pool_diem=round(b * x, 3) if g[3] >= 1 else None, pool_thang_xem=p_thang.get(ma, 0.0))
        else:
            d.update(trong_pool=0.0, pool_xem=0.0, pool_hien_thi=0.0, pool_so_video=0.0, pool_diem=None,
                     pool_thang_xem=0.0)
        nhom_cum = list(cm) + ([ny] if ny and ny != "khac" else [])
        d["pool_cum_xem"] = max([p_cum.get(x, 0.0) for x in nhom_cum] or [0.0])
        d["pool_kenh_xem"] = p_kenh.get(u.get("kenh_nguon", ""), 0.0)
        d["tc_ngay"] = float(len(tc_ngay.get(ma, ())))
        d["tc_lan"] = float(tc_lan.get(ma, 0))
        d["tc_kenh"] = float(tc_kenh.get(u.get("kenh_nguon", ""), 0))
        d["tc_cach_ngay"] = ((c.ngay_cua(tg.ngay) - c.ngay_cua(tc_cuoi[ma])).days if ma in tc_cuoi else None)
        bg = bigram(td)
        d["thang_cum"] = 1.0 if (thang_cum and set(nhom_cum) & thang_cum) else 0.0
        d["giong_thang_chu"] = round(max([giong(bg, x) for x in thang_bg] or [0.0]), 3)
        ai = tg.ai_nho.get(ma) if isinstance(tg.ai_nho, dict) else None
        d["giong_thang_ai"] = float(ai.get("trung") or 0) if (isinstance(ai, dict) and ai.get("trung_voi") in thang_ma) \
            else 0.0
        d["giong_minh_chu"] = round(max([giong(bg, x) for x in minh_bg] or [0.0]), 3)
        d["co_thang"] = 1.0 if thang else 0.0
        ls = tg.lich_su_view.get(ma)
        d["da_tang_3n"] = None
        if ls and view and tv:
            tr = _view_truoc(ls, d["luc"])
            if tr is not None and d["luc"] > tr[0]:
                d["da_tang_3n"] = round((view - tr[1]) / ((d["luc"] - tr[0]) / c.NGAY_GIAY) / tv, 3)
        ra.append(mo_rong(d))
    for u in vt.ung_vien:
        u.pop("_tc_ngay", None)
        u.pop("_tc_kenh", None)
    return ra


def _log(x: Any) -> Optional[float]:
    try:
        return math.log(float(x)) if x is not None and float(x) > 0 else None
    except (TypeError, ValueError):
        return None


def mo_rong(d: Dict[str, Any]) -> Dict[str, Any]:
    """Thêm đặc trưng DẪN XUẤT (tại chỗ) — xem đầu tệp."""
    ph = d.get("dai_phut")
    nguon = str(d.get("nguon") or "")
    tuoi = d.get("tuoi_ngay")
    d["log_vuot"] = _log(d.get("vuot"))
    d["log_view"] = _log(d.get("view"))
    d["dai_tot"] = 1.0 if (ph is not None and 12 <= ph <= 21) else 0.0
    d["dai_tam"] = 1.0 if (ph is not None and 8 <= ph <= 30) else 0.0
    d["tang_duong"] = 1.0 if (d.get("tang_ngay") or 0) > 0 else 0.0
    d["log_pool_xem"] = math.log1p(float(d.get("pool_xem") or 0))
    d["log_pool_cum_xem"] = math.log1p(float(d.get("pool_cum_xem") or 0))
    d["log_pool_thang_xem"] = math.log1p(float(d.get("pool_thang_xem") or 0))
    d["log_pool_kenh_xem"] = math.log1p(float(d.get("pool_kenh_xem") or 0))
    d["log_thi_truong"] = _log(d.get("vung_thi_truong"))
    d["log_tc"] = math.log1p(float(d.get("tc_ngay") or 0))
    d["vung_chua_chu"] = 1.0 if (d.get("vung") and not d.get("vung_chu")) else 0.0
    d["co_doi_thu"] = 1.0 if NGUON_DOI_THU in nguon else 0.0
    d["co_pool"] = 1.0 if NGUON_POOL in nguon else 0.0
    d["co_trang_chu"] = 1.0 if NGUON_TRANG_CHU in nguon else 0.0
    d["tre_3n"] = 1.0 if (tuoi is not None and tuoi <= 3) else 0.0
    d["tre_7n"] = 1.0 if (tuoi is not None and tuoi <= 7) else 0.0
    d["tre_30n"] = 1.0 if (tuoi is not None and tuoi <= 30) else 0.0
    return d


# ── ảnh chụp ngày ───────────────────────────────────────────────────────────

def duong_kho(goc: str, kenh: str, ngay: str) -> str:
    return os.path.join(c.thu_muc_kenh(goc, kenh), "kho-{0}.csv.gz".format(ngay))


def _gon(x: Any) -> Any:
    if isinstance(x, float):
        if x == int(x) and abs(x) < 1e15:
            return int(x)
        return float(format(x, ".{0}g".format(4))) if abs(x) < 1e4 else round(x, 1)
    return x


def ghi_kho(goc: str, kenh: str, ngay: str, kho: Iterable[Dict[str, Any]]) -> str:
    def gon(d: Dict[str, Any]) -> Dict[str, Any]:
        r = {k: _gon(d.get(k)) for k in COT_KHO}
        # Tiêu đề chỉ giữ cho dòng ĐỦ ĐIỀU KIỆN của ít nhất một giả thuyết (`_du` do nơi gọi đánh dấu) — phần còn
        # lại chỉ cần số (mức nền tầng 1); tiêu đề tra lại được trong sổ content.
        r["tieu_de"] = str(d.get("tieu_de") or "")[:DAI_TIEU_DE_GHI] if d.get("_du") else ""
        return r
    return c.ghi_csv_gz(duong_kho(goc, kenh, ngay), COT_KHO, (gon(d) for d in kho))


def doc_kho(goc: str, kenh: str, ngay: str) -> List[Dict[str, Any]]:
    """Ảnh chụp kho của một ngày (số đổi về float/None, có cả đặc trưng dẫn xuất); không có → []."""
    ra = []
    for r in c.doc_csv_gz(duong_kho(goc, kenh, ngay)):
        d: Dict[str, Any] = {}
        for k, v in r.items():
            d[k] = (v or "") if k in COT_CHU else c.so(v)
        ra.append(mo_rong(d))
    return ra


def ngay_co_kho(goc: str, kenh: str) -> List[str]:
    try:
        ten = os.listdir(c.thu_muc_kenh(goc, kenh))
    except OSError:
        return []
    return sorted(t[4:14] for t in ten if t.startswith("kho-") and t.endswith(".csv.gz"))
