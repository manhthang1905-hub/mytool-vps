"""CHIA KHE SẢN XUẤT theo phòng thí nghiệm (đợt 2, 12/10/2026) — thay tỉ trọng cố định kenh.yaml `chien_luoc`.

Mỗi khe (một lượt chọn nguồn của kênh) chọn MỘT giả thuyết bằng THOMPSON PHÂN TẦNG trên bảng xếp hạng:

    μ_h ~ Beta(a_h, b_h)                          mức danh mục (κ₀·nền + w₁·tầng 1 + mọi phán quyết thật của h)
    θ_kh ~ Beta(κ₁μ_h + điểm_kh, κ₁(1 − μ_h) + n_kh − điểm_kh)      kênh co về danh mục (`danh_gia.rut_hai_bac`)

lượt rút cao nhất thắng khe; với xác suất `KHAM_PHA` (15%) khe đi cho một giả thuyết KHÔNG dẫn đầu (chọn đều) — sàn
khám phá. Phần thưởng = phán quyết thước chung ≥ 96h (tầng 2: ghi công bóng + ghi công CHÍNH XÁC của khe).

Ai được nhận khe ở kênh k (`du_dieu_kien`, vai từ `luat.vai_kenh`):
* chưa bị loại (sổ giả thuyết `loai` = toàn danh mục; vai `loai` = ở kênh này);
* giả thuyết MỚI (`bong`): vai `thu` (≥ 7 ngày bóng ở kênh + qua sàn tầng 1) và chưa dùng `KHE_THU_TUAN` (1) khe trong
  7 ngày ở kênh (đếm lượt có `nguon.gia_thuyet` trong sổ `tu-chay/`);
* có bảng ứng viên hôm nay (H-V7/H-VPH = bảng công thức sống V7/VPH; giả thuyết dạng trọng số / AI = ảnh chụp kho của
  ngày (≤ `NGAY_KHO_LUI` ngày) chấm bằng bộ chấm của nó, qua `nc.loc` + cổng CỨNG của V7).

Bảng của giả thuyết thắng khe đứng ĐẦU (cả bảng), sau đó bảng các giả thuyết đủ điều kiện khác theo hậu nghiệm kênh
giảm dần (lùi khi bảng đầu bị phủ quyết hết), cuối cùng dòng không thuộc giả thuyết nào (vd. Một nút khi VPH rỗng) —
rồi mọi cổng sẵn có chạy như cũ (chủ quyền vùng, ép chọn của não, biên tập chỉ phủ quyết, cổng chất lượng, trùng ý,
giữ nguồn nhóm). Dòng mang `gia_thuyet` (bảng đã ra nó), `gia_thuyet_khe` (giả thuyết thắng khe), `ptn` (phiên bản,
cách chọn, lượt rút) → vào sổ lượt `tu-chay/<ngày>.json` qua `run.nguon` (`chot_nguon` bỏ ghi công khi não ép chọn).

Tất định: hạt giống = kênh | ngày | số lượt đã mở hôm nay (như thăm dò của `chien_luoc`) → trạm `/loi-thoai/can-lay` và
vòng chọn nguồn thấy MỘT bảng.

Bật/tắt (`bat`): biến môi trường `MYTOOL_PTN_CHIA_KHE=0` tắt hết · kenh.yaml `phong_thi_nghiem_chia_khe: true|false`
· `workspace/phong-thi-nghiem/chia-khe.json` `{"kenh": {"<kênh>": true}, "mac_dinh": false}` · mặc định trong mã
`KENH_MAC_DINH`. Phòng thí nghiệm tắt (`chay.bat`) → tắt. Kênh chưa có số trong bảng xếp hạng / không giả thuyết nào
đủ điều kiện / lỗi → luật cũ (tỉ trọng kenh.yaml), có log.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import random
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import _chung as c

KHOA_KENH = "phong_thi_nghiem_chia_khe"
BIEN_MOI_TRUONG = "MYTOOL_PTN_CHIA_KHE"
KENH_MAC_DINH = ("TL1-T7", "TL2-T7", "TL3-T7", "TL6-T7")
TEP_CAU_HINH = "chia-khe.json"
KHAM_PHA = 0.15
KHE_THU_TUAN = 1
NGAY_TUAN = 7
NGAY_KHO_LUI = 2
SO_DONG_KHE = 30
GT_CONG_THUC = {"H-V7": "v7", "H-VPH": "vph"}
CONG_MEM = ("nguồn quá nhỏ", "kênh nguồn quá yếu", "bảng đề xuất", "không có trong bảng đề xuất", "cổng bảng đề xuất")
_TAT = ("0", "false", "tat", "tắt", "no", "off", "khong", "không")


def _bool(x: Any) -> Optional[bool]:
    if x is None or x == "":
        return None
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() not in _TAT


def bat(goc: str, kenh: str) -> Tuple[bool, str]:
    """`(bật?, vì sao)` — xem đầu tệp."""
    try:
        from .chay import bat as lab_bat  # noqa: PLC0415

        if not lab_bat(goc, kenh):
            return False, "phòng thí nghiệm tắt"
    except Exception:  # noqa: BLE001
        return False, "không đọc được cờ phòng thí nghiệm"
    if str(os.environ.get(BIEN_MOI_TRUONG, "")).strip().lower() in _TAT:
        return False, "biến môi trường {0}".format(BIEN_MOI_TRUONG)
    y = _bool(c.doc_yaml_kenh(goc, kenh).get(KHOA_KENH))
    if y is not None:
        return y, "kenh.yaml {0}".format(KHOA_KENH)
    cfg = c.doc_json(os.path.join(c.thu_muc_chung(goc), TEP_CAU_HINH), {}) or {}
    if isinstance(cfg, dict):
        x = _bool((cfg.get("kenh") or {}).get(kenh)) if isinstance(cfg.get("kenh"), dict) else None
        if x is not None:
            return x, "workspace/phong-thi-nghiem/{0}".format(TEP_CAU_HINH)
        x = _bool(cfg.get("mac_dinh"))
        if x is not None:
            return x, "workspace/phong-thi-nghiem/{0} (mặc định)".format(TEP_CAU_HINH)
    return kenh in KENH_MAC_DINH, "mặc định trong mã"


def cong_thuc_cua(g: Dict[str, Any]) -> str:
    """Công thức sản xuất SỐNG mà giả thuyết dùng làm bảng ("v7"/"vph"); "" = bảng dựng từ ảnh chụp kho."""
    if g.get("id") in GT_CONG_THUC:
        return GT_CONG_THUC[g["id"]]
    if g.get("loai") == "dung_san":
        cot = str((g.get("tham_so") or {}).get("cot") or "")
        for ct in ("v7", "vph"):
            if cot.startswith(ct + "_"):
                return ct
    return ""


# ── sổ lượt: khe đã dùng ────────────────────────────────────────────────────

def so_khe(goc: str, kenh: str, ngay: str, so_ngay: int = NGAY_TUAN) -> Dict[str, int]:
    """`{giả thuyết: số lượt}` trong `so_ngay` ngày tới `ngay` (gồm `ngay`) — lượt có `nguon.gia_thuyet`, không bị bỏ."""
    ra: Dict[str, int] = {}
    for i in range(so_ngay):
        d = c.cong_ngay(ngay, -i)
        du = c.doc_json(os.path.join(goc, "CHANNEL", kenh, "tu-chay", d + ".json"), {}) or {}
        for run in (du.get("runs") or []) if isinstance(du, dict) else []:
            ng = (run or {}).get("nguon") if isinstance(run, dict) else None
            if not isinstance(ng, dict) or run.get("bo"):
                continue
            g = str(ng.get("gia_thuyet") or "")
            if g:
                ra[g] = ra.get(g, 0) + 1
    return ra


# ── ai được nhận khe ────────────────────────────────────────────────────────

def du_dieu_kien(goc: str, kenh: str, bang: Dict[str, Any], *, ngay: str,
                 khe: Optional[Dict[str, int]] = None) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    """`(đủ điều kiện, vai {gt: vai}, bị chặn {gt: lý do})` — xem đầu tệp (chưa xét "có bảng hôm nay")."""
    from . import luat  # noqa: PLC0415

    vai = luat.vai_kenh(bang, kenh)
    khe = khe if khe is not None else so_khe(goc, kenh, ngay)
    du: List[str] = []
    chan: Dict[str, str] = {}
    for gt, o in sorted((bang.get("gia_thuyet") or {}).items()):
        tt = (o or {}).get("trang_thai")
        v, ly = vai.get(gt, ("", "chưa có số ở kênh"))
        if tt == "loai":
            chan[gt] = "đã loại (toàn danh mục)"
            continue
        if v == luat.LOAI:
            chan[gt] = "loại ở kênh: " + ly
            continue
        if tt == "bong" and str((o or {}).get("khoa_chu_den") or "") > str(ngay or ""):
            # 22/10/2026 — chủ chốt: tạm chỉ chạy thật 4 giả thuyết mạnh (dồn khe để học nhanh), số còn lại CHẠY BÓNG
            # tới ngày khoá — luật tự động không được mở thử trước ngày ấy.
            chan[gt] = "chủ cho chạy bóng tới {0}".format((o or {}).get("khoa_chu_den"))
            continue
        if tt == "bong":
            if v not in (luat.THU, luat.DAN_DAU):
                chan[gt] = "giả thuyết mới chưa được thử: " + (ly or "chưa có số")
                continue
            if khe.get(gt, 0) >= KHE_THU_TUAN:
                chan[gt] = "đã dùng {0}/{1} khe thử trong 7 ngày".format(khe.get(gt, 0), KHE_THU_TUAN)
                continue
        du.append(gt)
    return du, {g: v[0] for g, v in vai.items()}, chan


def _rng(hat: str) -> random.Random:
    return random.Random(int(hashlib.sha1(hat.encode("utf-8")).hexdigest()[:12], 16))


def phan_bo(goc: str, kenh: str, *, ngay: str, so_luot: int = 0, bang: Optional[Dict[str, Any]] = None,
            du: Optional[Sequence[str]] = None, vai: Optional[Dict[str, str]] = None,
            chan: Optional[Dict[str, str]] = None, rng: Optional[random.Random] = None,
            kham_pha: Optional[float] = None) -> Dict[str, Any]:
    """Chọn giả thuyết cho MỘT khe (xem đầu tệp). `du` = giả thuyết đủ điều kiện VÀ có bảng hôm nay (None = tự tính
    `du_dieu_kien`, coi như giả thuyết nào cũng có bảng). Trả
    `{gia_thuyet, cach: thompson|kham_pha|duy_nhat|khong_co, dan_dau, rut, thu_tu, du, chan, p_tot_nhat, tb, ly_do}`."""
    from .danh_gia import doc_bang, rut_hai_bac  # noqa: PLC0415

    bang = bang if bang is not None else doc_bang(goc)
    kham_pha = KHAM_PHA if kham_pha is None else float(kham_pha)
    t2 = bang.get("tang2") or {}
    m = (t2.get("theo_kenh") or {}).get(kenh) or {}
    ch = t2.get("chung") or {}
    chan = dict(chan or {})
    if du is None:
        du, vai, chan2 = du_dieu_kien(goc, kenh, bang, ngay=ngay)
        chan.update(chan2)
    vai = vai or {}
    du = [g for g in du if g in ch and "a" in ch[g]]
    rong = {"gia_thuyet": "", "cach": "khong_co", "dan_dau": "", "rut": {}, "thu_tu": [], "du": [], "chan": chan,
            "p_tot_nhat": {}, "tb": {}}
    if not m or not du:
        rong["ly_do"] = "kênh chưa có số trong bảng xếp hạng" if not m else "không giả thuyết nào đủ điều kiện"
        return rong
    p = {g: float((m.get(g) or {}).get("p_tot_nhat") or 0.0) for g in du}
    tb = {g: float((m.get(g) or {}).get("tb") or ch[g].get("tb") or 0.0) for g in du}
    dan = [g for g in du if vai.get(g) == "dan_dau"]
    dan_dau = dan[0] if dan else max(du, key=lambda g: (p[g], tb[g], g))
    r = rng or _rng("khe:{0}:{1}:{2}".format(kenh, ngay, int(so_luot or 0)))
    rut = {g: rut_hai_bac(r, (float(ch[g]["a"]), float(ch[g]["b"])), float((m.get(g) or {}).get("diem") or 0),
                          float((m.get(g) or {}).get("n") or 0)) for g in du}
    if len(du) == 1:
        g, cach, ly = du[0], "duy_nhat", "chỉ {0} đủ điều kiện".format(du[0])
    elif r.random() < kham_pha:
        khac = [x for x in du if x != dan_dau]
        g = khac[int(r.random() * len(khac)) % len(khac)]
        cach, ly = "kham_pha", "sàn khám phá {0:.0%}: khe cho giả thuyết không dẫn đầu".format(kham_pha)
    else:
        g = max(du, key=lambda x: (rut[x], x))
        cach, ly = "thompson", "Thompson phân tầng: lượt rút cao nhất ({0:.3f})".format(rut[g])
    thu_tu = [g] + sorted((x for x in du if x != g), key=lambda x: (-tb[x], x))
    return {"gia_thuyet": g, "cach": cach, "dan_dau": dan_dau, "rut": {x: round(v, 3) for x, v in rut.items()},
            "thu_tu": thu_tu, "du": list(du), "chan": chan, "p_tot_nhat": p, "tb": tb, "ly_do": ly}


def mo_phong(goc: str, kenh: str, *, ngay: str, bang: Optional[Dict[str, Any]] = None, so_lan: int = 2000,
             du: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Tỉ phần khe DỰ KIẾN (mô phỏng `so_lan` khe với hạt giống khác nhau; không tính trần tuần) — cho bảng trực quan
    và báo cáo. Trả `{"ti_le": {gt: phần}, "du": [...], "chan": {...}}`."""
    from .danh_gia import doc_bang  # noqa: PLC0415

    bang = bang if bang is not None else doc_bang(goc)
    vai: Dict[str, str] = {}
    chan: Dict[str, str] = {}
    if du is None:
        du, vai, chan = du_dieu_kien(goc, kenh, bang, ngay=ngay)
    dem: Dict[str, int] = {}
    r = _rng("mo-phong:{0}:{1}".format(kenh, ngay))
    for _ in range(so_lan):
        kq = phan_bo(goc, kenh, ngay=ngay, bang=bang, du=du, vai=vai, chan=chan, rng=r)
        if kq["gia_thuyet"]:
            dem[kq["gia_thuyet"]] = dem.get(kq["gia_thuyet"], 0) + 1
    tong = float(sum(dem.values()) or 1)
    return {"ti_le": {g: round(dem.get(g, 0) / tong, 3) for g in du}, "du": list(du), "chan": chan}


# ── bảng ứng viên của giả thuyết dạng trọng số / AI (ảnh chụp kho) ──────────

_NHO_KHO: Dict[Tuple[str, str, str], Tuple[float, List[Dict[str, Any]]]] = {}
_NHO_TD: Dict[str, Tuple[float, Dict[str, Tuple[str, str]]]] = {}


def kho_gan_nhat(goc: str, kenh: str, ngay: str, lui: int = NGAY_KHO_LUI) -> Tuple[str, List[Dict[str, Any]]]:
    """`(ngày, dòng kho)` — ảnh chụp kho của `ngay`, lùi tối đa `lui` ngày; nhớ trong tiến trình (theo giờ sửa tệp)."""
    from . import dac_trung  # noqa: PLC0415

    for i in range(lui + 1):
        d = c.cong_ngay(ngay, -i)
        p = dac_trung.duong_kho(goc, kenh, d)
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        khoa = (c.goc_ghi(goc), kenh, d)
        nho = _NHO_KHO.get(khoa)
        if nho and nho[0] == mt:
            return d, nho[1]
        kho = dac_trung.doc_kho(goc, kenh, d)
        if len(_NHO_KHO) >= 6:
            _NHO_KHO.clear()
        _NHO_KHO[khoa] = (mt, kho)
        return d, kho
    return "", []


def tieu_de_day_du(goc: str, kenh: str) -> Dict[str, Tuple[str, str]]:
    """`{mã: (tiêu đề đầy đủ, kênh nguồn)}` từ sổ content của kênh (ảnh chụp kho chỉ giữ 80 ký tự)."""
    p = os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "content.csv")
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return {}
    nho = _NHO_TD.get(p)
    if nho and nho[0] == mt:
        return nho[1]
    ra: Dict[str, Tuple[str, str]] = {}
    try:
        with io.open(p, encoding="utf-8-sig", newline="") as tep:
            for r in csv.DictReader(tep):
                mm = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", str(r.get("Link video") or ""))
                if mm:
                    ra.setdefault(mm.group(1), (str(r.get("Tiêu đề video") or ""), str(r.get("Kênh") or "").strip()))
    except (OSError, ValueError, csv.Error):
        return {}
    _NHO_TD[p] = (mt, ra)
    return ra


def _ket_ai(goc: str, kenh: str, ngay: str) -> Dict[str, float]:
    from . import ai  # noqa: PLC0415

    du = c.doc_json(ai.duong(goc, kenh, ngay), {}) or {}
    ket = du.get("ket") if isinstance(du, dict) else None
    return {str(m): float(x) for m, x in (ket or {}).items() if c.so(x) is not None}


def bang_san_xuat(goc: str, kenh: str, g: Dict[str, Any], *, ngay: str,
                  n: int = SO_DONG_KHE * 2) -> Tuple[List[Dict[str, Any]], str]:
    """`(dòng chuẩn, ngày ảnh chụp)` — bảng của một giả thuyết dạng trọng số / AI trên ảnh chụp kho gần nhất, mạnh nhất
    trước (dòng chuẩn `chien_luoc/ngu_canh.py`; `nguon`/`cong_thuc` = "ptn")."""
    from . import gia_thuyet as gtm  # noqa: PLC0415

    d_kho, kho = kho_gan_nhat(goc, kenh, ngay)
    if not kho:
        return [], ""
    ket_ai = _ket_ai(goc, kenh, d_kho) if g.get("loai") == gtm.LOAI_LLM else None
    if g.get("loai") == gtm.LOAI_LLM and not ket_ai:
        return [], d_kho
    top, _n = gtm.xep_hang(g, kho, n, ket_ai=ket_ai)
    td = tieu_de_day_du(goc, kenh)
    ra = []
    for i, (d, x) in enumerate(top, 1):
        ma = str(d.get("ma") or "")
        if not ma:
            continue
        tieu, kn = td.get(ma, ("", ""))
        vuot, ph, tuoi = d.get("vuot"), d.get("dai_phut"), d.get("tuoi_ngay")
        ra.append({
            "nguon": "ptn", "cong_thuc": "ptn", "tham_do": False, "ma": ma,
            "link": "https://www.youtube.com/watch?v=" + ma, "tieu_de": tieu or str(d.get("tieu_de") or ""),
            "kenh": kn or str(d.get("kenh_nguon") or ""), "diem": round(float(x), 4),
            "loai": "PTN {0}".format(g.get("id")), "view": float(d.get("view") or 0), "vph": d.get("vph_doi"),
            "dot_bien": vuot, "tuoi_gio": (round(float(tuoi) * 24.0, 1) if tuoi is not None else None),
            "cum": [x for x in str(d.get("cum") or "").split("|") if x], "tuyen": str(d.get("tuyen_nhan") or ""),
            "vuot": vuot, "dai_giay": (round(float(ph) * 60.0) if ph is not None else None), "hang_gt": i,
            "tin_hieu": {}, "ly_do": ["Phòng thí nghiệm {0} hạng {1} (điểm {2:.2f}; gấp {3} × trung vị kênh nguồn; "
                                      "{4} phút; nguồn {5}; kho {6})".format(
                                          g.get("id"), i, float(x), "—" if vuot is None else "{0:.1f}".format(vuot),
                                          "—" if ph is None else "{0:.0f}".format(ph), d.get("nguon") or "—", d_kho)]})
    return ra, d_kho


def cong_cung_v7(kq: Any) -> Dict[str, str]:
    """`{mã: lý do}` — dòng bị cổng CỨNG của V7 (đã làm, video của mình, kênh bỏ/hết, nhắm tệp khác, khác chủ đề, độ dài
    ngoài khuôn, kênh lạc ngách…); cổng MỀM (nguồn nhỏ, kênh nguồn yếu, bảng đề xuất) không tính — như ép chọn của não."""
    ra: Dict[str, str] = {}
    for d in list(getattr(kq, "bi_loai", None) or []) + list(getattr(kq, "ung_vien", None) or []):
        ly = str(getattr(d, "bi_loai", "") or "")
        ma = str(getattr(d, "ma", "") or "")
        if ma and ly and not any(x in ly for x in CONG_MEM):
            ra.setdefault(ma, ly)
    return ra


# ── nối vào bộ điều phối `chien_luoc.xep_hang` ──────────────────────────────

def chuan_bi(nc: Any, bang: Dict[str, List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """Gọi TRƯỚC các bước nắn điểm của bộ điều phối: dựng bảng mỗi giả thuyết đủ điều kiện (thêm vào `bang` khoá
    `ptn:<gt>`), chọn giả thuyết cho khe. None = không chia khe được → bộ điều phối dùng luật cũ."""
    from . import danh_gia, gia_thuyet as gtm  # noqa: PLC0415

    goc, kenh = nc.goc, nc.ma_kenh
    ngay = nc.bay_gio.date().isoformat()
    bxh = danh_gia.doc_bang(goc)
    if kenh not in ((bxh.get("tang2") or {}).get("theo_kenh") or {}):
        nc.ghi("  phòng thí nghiệm chia khe: kênh chưa có số trong bảng xếp hạng — dùng tỉ trọng kenh.yaml.")
        return None
    reg = {g["id"]: g for g in gtm.nap(goc, ghi=False)[0]}
    du, vai, chan = du_dieu_kien(goc, kenh, bxh, ngay=ngay)
    cung = cong_cung_v7(getattr(nc, "_kq_v7", None))
    khoa: Dict[str, str] = {}
    for gt in du:
        g = reg.get(gt)
        if g is None:
            chan[gt] = "không có trong sổ giả thuyết"
            continue
        ct = cong_thuc_cua(g)
        if ct:
            if any(d.get("cong_thuc") == ct for d in bang.get(ct) or []):
                khoa[gt] = ct
            else:
                chan[gt] = "bảng {0} hôm nay rỗng".format(ct.upper())
            continue
        try:
            rows, d_kho = bang_san_xuat(goc, kenh, g, ngay=ngay)
        except Exception as loi:  # noqa: BLE001
            chan[gt] = "dựng bảng hỏng: {0}".format(str(loi)[:80])
            continue
        n0 = len(rows)
        sau_loc = nc.loc(rows)
        rows = [d for d in sau_loc if d["ma"] not in cung][:SO_DONG_KHE]
        if rows:
            bang["ptn:" + gt] = rows
            khoa[gt] = "ptn:" + gt
        else:
            chan[gt] = "không còn ứng viên (kho {0}: {1} dòng, {2} trùng/đã làm, {3} vướng cổng cứng V7)".format(
                d_kho or "—", n0, n0 - len(sau_loc), len(sau_loc))
    du_co = [g for g in du if g in khoa]
    kq = phan_bo(goc, kenh, ngay=ngay, so_luot=getattr(nc, "so_luot_hom_nay", 0), bang=bxh, du=du_co, vai=vai,
                 chan=chan)
    if not kq["gia_thuyet"]:
        nc.ghi("  phòng thí nghiệm chia khe: {0} — dùng tỉ trọng kenh.yaml. Bị chặn: {1}.".format(
            kq.get("ly_do"), "; ".join("{0} ({1})".format(g, ly[:70]) for g, ly in sorted(chan.items())) or "—"))
        return None
    kq["khoa"] = khoa
    kq["pb"] = {g: int(reg[g].get("phien_ban") or 1) for g in khoa}
    kq["ngay_bang"] = bxh.get("ngay") or str(bxh.get("luc") or "")[:10]
    nc.ghi("  phòng thí nghiệm chia khe: lượt này → {0} [{1}; {2}] · lượt rút: {3} · dẫn đầu kênh {4} · dự phòng: "
           "{5}{6}.".format(kq["gia_thuyet"], kq["cach"], kq["ly_do"],
                            ", ".join("{0} {1:.2f}".format(g, kq["rut"][g]) for g in sorted(kq["rut"],
                                                                                          key=lambda x: -kq["rut"][x])),
                            kq["dan_dau"], " → ".join(kq["thu_tu"][1:]) or "không",
                            "; không nhận khe: " + "; ".join("{0} ({1})".format(g, ly[:60]) for g, ly in
                                                              sorted(chan.items())) if chan else ""))
    return kq


def tron(nc: Any, bang: Dict[str, List[Dict[str, Any]]], ke: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gọi SAU các bước nắn điểm: bảng giả thuyết thắng khe trước, rồi lần lượt `ke["thu_tu"]`, rồi dòng không thuộc
    giả thuyết nào (công thức dự phòng như Một nút). Gắn `gia_thuyet`/`gia_thuyet_khe`/`ptn`; khử trùng theo mã."""
    ra: List[Dict[str, Any]] = []
    vi_tri: Dict[str, int] = {}
    khoa = ke.get("khoa") or {}
    ct_gt = set(GT_CONG_THUC.values()) | {v for v in khoa.values() if not v.startswith("ptn:")}
    for i, gt in enumerate(ke.get("thu_tu") or []):
        k = khoa.get(gt)
        if not k:
            continue
        ct = "" if k.startswith("ptn:") else k
        for d in bang.get(k) or []:
            if ct and d.get("cong_thuc") != ct:
                continue
            ma = str(d.get("ma") or "")
            if ma in vi_tri:
                ra[vi_tri[ma]].setdefault("gia_thuyet_khac", []).append(gt)
                continue
            moi = dict(d, gia_thuyet=gt, gia_thuyet_khe=ke["gia_thuyet"], tham_do=False,
                       ptn={"pb": (ke.get("pb") or {}).get(gt), "cach": ke.get("cach"), "hang_khe": i + 1,
                            "thu_tu": list(ke.get("thu_tu") or []), "rut": ke.get("rut") or {},
                            "ngay_bang": ke.get("ngay_bang")})
            if i == 0:
                moi["ly_do"] = list(moi.get("ly_do") or []) + ["phòng thí nghiệm: khe này của {0} ({1})".format(
                    gt, ke.get("ly_do") or ke.get("cach"))]
            vi_tri[ma] = len(ra)
            ra.append(moi)
    duoi = 0
    for k, ds in bang.items():
        if k.startswith("ptn:"):
            continue
        for d in ds:
            ma = str(d.get("ma") or "")
            if ma in vi_tri or d.get("cong_thuc") in ct_gt:
                continue
            vi_tri[ma] = len(ra)
            ra.append(dict(d, gia_thuyet="", gia_thuyet_khe=ke["gia_thuyet"], tham_do=False))
            duoi += 1
    dem: Dict[str, int] = {}
    for d in ra:
        dem[d.get("gia_thuyet") or "—"] = dem.get(d.get("gia_thuyet") or "—", 0) + 1
    nc.ghi("  phòng thí nghiệm chia khe: bảng {0} dòng ({1}).".format(
        len(ra), ", ".join("{0} {1}".format(g, dem.get(g, 0)) for g in (ke.get("thu_tu") or []) + (["—"] if duoi else []))))
    return ra


def chot_nguon(nguon: Any) -> None:
    """Chuẩn hoá nguồn ĐÃ CHỌN trước khi vào sổ lượt: bộ não ép chọn / chọn tay → không ghi công chính xác cho giả thuyết
    (giữ `gia_thuyet_bo` để tra). Thêm `ptn_pb` phẳng cho sổ đọc nhanh.

    Ngoại lệ (12/10/2026): nguồn ép chọn của RADAR THỊ TRƯỜNG (`nao.tao_ep_chon_radar`, dòng mang `radar_thi_truong`)
    là một giả thuyết đo được — ghi công CHÍNH XÁC cho `gia_thuyet_radar` (H-RADAR), kể cả khi kênh không chia khe."""
    if isinstance(nguon, dict) and nguon.get("radar_thi_truong") and nguon.get("gia_thuyet_radar"):
        gt = str(nguon.get("gia_thuyet_radar"))
        if nguon.get("gia_thuyet") and nguon.get("gia_thuyet") != gt:
            nguon["gia_thuyet_bo"] = nguon.get("gia_thuyet", "")
        nguon["gia_thuyet"] = gt
        ptn = dict(nguon.get("ptn") or {})
        ptn["ghi_cong"] = "radar thị trường"
        ptn["pb"] = None   # pb rỗng = phiên bản hiện tại của sổ giả thuyết (`danh_gia.tang_cau_noi`)
        nguon["ptn"] = ptn
        nguon["ptn_pb"] = None
        return
    if not isinstance(nguon, dict) or "gia_thuyet_khe" not in nguon:
        return
    if nguon.get("ep_chon") or nguon.get("chon_tay"):
        nguon["gia_thuyet_bo"] = nguon.get("gia_thuyet", "")
        nguon["gia_thuyet"] = ""
        ptn = dict(nguon.get("ptn") or {})
        ptn["khong_ghi_cong"] = "bộ não ép chọn" if nguon.get("ep_chon") else "chọn tay"
        nguon["ptn"] = ptn
    nguon["ptn_pb"] = (nguon.get("ptn") or {}).get("pb")


def tom_tat_kenh(goc: str, kenh: str, *, ngay: str, bang: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Một kênh cho trực quan / báo cáo: bật?, đủ điều kiện, bị chặn, khe đã dùng 7 ngày, tỉ phần khe dự kiến."""
    from .danh_gia import doc_bang  # noqa: PLC0415

    bang = bang if bang is not None else doc_bang(goc)
    on, vi_sao = bat(goc, kenh)
    khe = so_khe(goc, kenh, ngay)
    du, vai, chan = du_dieu_kien(goc, kenh, bang, ngay=ngay, khe=khe)
    mp = mo_phong(goc, kenh, ngay=ngay, bang=bang, du=du, so_lan=1000) if du else {"ti_le": {}}
    return {"bat": on, "vi_sao": vi_sao, "du": du, "vai": vai, "chan": chan, "khe_7_ngay": khe,
            "ti_le_khe": mp.get("ti_le") or {}}


def rut_vi_du(goc: str, kenh: str, *, ngay: str, so_luot: int = 0,
              bang: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Một khe minh hoạ (không áp) — `python -m core.phong_thi_nghiem --khe`."""
    return phan_bo(goc, kenh, ngay=ngay, so_luot=so_luot, bang=bang)


def kenh_bat(goc: str, kenh_ds: Iterable[str]) -> List[str]:
    return [k for k in kenh_ds if bat(goc, k)[0]]


__all__ = ["bat", "phan_bo", "mo_phong", "du_dieu_kien", "chuan_bi", "tron", "chot_nguon", "so_khe",
           "bang_san_xuat", "tom_tat_kenh", "KENH_MAC_DINH", "KHAM_PHA", "KHE_THU_TUAN"]
