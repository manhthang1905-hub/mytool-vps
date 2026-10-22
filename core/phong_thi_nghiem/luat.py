"""LUẬT QUYẾT của phòng thí nghiệm (kế hoạch mục 4) — áp sau MỖI lần tính bảng xếp hạng, ghi sổ quyết định có số.

Vai của (kênh × giả thuyết), tính lại mỗi lần từ bảng (tầng 2 + tầng 1 công bằng):

* `dan_dau` — P(tốt nhất) ≥ `P_DAN_DAU` (0,8) với n ≥ `N_QUYET` (8) trên kênh. `chia_khe` coi nó là "giả thuyết dẫn đầu"
  khi tính sàn khám phá; Thompson tự dồn phần lớn khe cho nó.
* `loai` — P(tốt nhất) < `P_LOAI` (0,05) với n ≥ 8 trên kênh, VÀ giả thuyết nó thua (P cao nhất của kênh) cũng đã đo
  n ≥ 8. P thấp chỉ là bằng chứng khi thua một giả thuyết ĐÃ ĐO — thua một giả thuyết 1–2 video chỉ là thua độ bất định
  của nó ("không bao giờ phán bằng 1–2 video"). Không nhận khe ở kênh đó (bóng vẫn chạy); số hồi phục → mở lại.
* `thu` — giả thuyết MỚI (`bong` trong sổ): đã chạy bóng ≥ `NGAY_BONG` (7) ngày ở kênh và QUA SÀN tầng 1 (chắc ≥ 80%
  rằng tỉ lệ NỔ +7n hơn rút ngẫu nhiên cùng ô gấp × tuổi × đà, n ≥ `N_TANG1_TOI_THIEU`; số của kênh nếu đủ n, không thì
  của danh mục) → được tối đa 1 khe/kênh/tuần (`chia_khe.KHE_THU_TUAN`).

Toàn danh mục (sửa SỔ GIẢ THUYẾT, dính):

* LOẠI CHUNG — luật `loai` ở mức danh mục → `trang_thai = "loai"` (dừng cả bóng; chỉ chủ / não mở lại bằng tay).
* TỐT NGHIỆP — `bong` có n danh mục ≥ 8 mà không phải ứng viên loại → `song` (hết trần khe của giả thuyết mới).

Chặn cứng: KHÔNG BAO GIỜ hành động khi n ≤ `N_KHONG_BAO_GIO` (2), kể cả khi ai đó hạ `N_QUYET`.

Tệp (`workspace/phong-thi-nghiem/`): `trang-thai.json` (vai hiện tại + ngày bắt đầu), `quyet-dinh.jsonl` (chỉ nối: mỗi
lần vai đổi một dòng — loại, kênh, giả thuyết, n, thắng, điểm, TB, CI90, P(tốt nhất), đối thủ, ngưỡng, lý do).
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import _chung as c

P_DAN_DAU, P_LOAI, N_QUYET = 0.8, 0.05, 8
N_KHONG_BAO_GIO = 2
NGAY_BONG = 7
TEP_TRANG_THAI = "trang-thai.json"
TEP_QUYET_DINH = "quyet-dinh.jsonl"
DAN_DAU, LOAI, THU = "dan_dau", "loai", "thu"
TEN_LOAI = {"dan_dau": "dẫn đầu kênh", "mat_dan_dau": "mất dẫn đầu", "loai_kenh": "loại khỏi kênh",
            "mo_lai_kenh": "mở lại ở kênh", "mo_thu": "mở thử 1 khe/tuần", "dong_thu": "đóng thử",
            "loai_chung": "LOẠI toàn danh mục", "tot_nghiep": "tốt nghiệp (hết trần khe)",
            "de_xuat_moi": "giả thuyết mới (chạy bóng)"}


def duong_trang_thai(goc: str) -> str:
    return os.path.join(c.thu_muc_chung(goc), TEP_TRANG_THAI)


def duong_quyet_dinh(goc: str) -> str:
    return os.path.join(c.thu_muc_chung(goc), TEP_QUYET_DINH)


def doc_trang_thai(goc: str) -> Dict[str, Any]:
    du = c.doc_json(duong_trang_thai(goc), {}) or {}
    return du if isinstance(du, dict) else {}


def doc_quyet_dinh(goc: str, n: int = 0) -> List[Dict[str, Any]]:
    ds = c.doc_jsonl(duong_quyet_dinh(goc))
    return ds[-n:] if n else ds


def ghi_quyet_dinh(goc: str, ds: List[Dict[str, Any]]) -> int:
    return c.them_dong(duong_quyet_dinh(goc), ds)


def _du_n(n: Any, toi_thieu: int = N_QUYET) -> bool:
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return False
    return n > N_KHONG_BAO_GIO and n >= max(toi_thieu, N_KHONG_BAO_GIO + 1)


def _so(o: Dict[str, Any]) -> Dict[str, Any]:
    return {x: o.get(x) for x in ("n", "thang", "diem", "tb", "ci90", "p_tot_nhat", "n_chinh_xac")}


def doi_thu_dan(m: Dict[str, Dict[str, Any]], tru: str = "") -> Tuple[str, Dict[str, Any]]:
    """Giả thuyết P(tốt nhất) cao nhất của một bảng (bỏ `tru`) — "đối thủ" mà luật loại so với."""
    ds = [(float(o.get("p_tot_nhat") or 0), g) for g, o in m.items() if g != tru and o.get("p_tot_nhat") is not None]
    if not ds:
        return "", {}
    _p, g = max(ds)
    return g, m[g]


def vai_theo_bang(m: Dict[str, Dict[str, Any]], gt: str) -> Tuple[str, str]:
    """`(vai, lý do)` của `gt` trong một bảng (kênh hoặc danh mục) theo luật dẫn đầu / loại."""
    o = m.get(gt) or {}
    p = o.get("p_tot_nhat")
    if p is None or not _du_n(o.get("n")):
        return "", ""
    if float(p) >= P_DAN_DAU:
        return DAN_DAU, "P(tốt nhất) {0:.0%} ≥ {1:.0%} với n = {2} ≥ {3}".format(float(p), P_DAN_DAU, o.get("n"),
                                                                             N_QUYET)
    if float(p) < P_LOAI:
        g2, o2 = doi_thu_dan(m, gt)
        if g2 and _du_n(o2.get("n")):
            return LOAI, "P(tốt nhất) {0:.1%} < {1:.0%} với n = {2} ≥ {3}; thua {4} (n = {5}, P {6:.0%})".format(
                float(p), P_LOAI, o.get("n"), N_QUYET, g2, o2.get("n"), float(o2.get("p_tot_nhat") or 0))
    return "", ""


#: Sàn tầng 1: P(tỉ lệ nổ thật của giả thuyết > mức rút ngẫu nhiên cùng tầng) ≥ ngần này (Beta(1 + hit, 1 + n − hit)).
P_SAN_TANG1 = 0.8


def qua_san_tang1(bang: Dict[str, Any], kenh: str, gt: str) -> Tuple[bool, str]:
    """Sàn tầng 1 của giả thuyết mới: CHẮC ≥ `P_SAN_TANG1` rằng tỉ lệ NỔ +7n của nó hơn rút ngẫu nhiên cùng tầng gấp ×
    tuổi, với n ≥ `N_TANG1_TOI_THIEU` — số của kênh nếu đủ n, không thì của danh mục. Trả `(qua, lý do có số)`."""
    from .danh_gia import KQ_CHINH, N_TANG1_TOI_THIEU, betainc  # noqa: PLC0415

    t1 = bang.get("tang1") or {}
    for pham_vi, o in (("kênh", (((t1.get("theo_kenh") or {}).get(kenh) or {}).get(gt) or {}).get(KQ_CHINH) or {}),
                       ("danh mục", ((t1.get("chung") or {}).get(gt) or {}).get(KQ_CHINH) or {})):
        n, h = int(o.get("n") or 0), int(o.get("hit") or 0)
        nen = o.get("nen_tang") if o.get("nen_tang") is not None else o.get("nen")
        if n < N_TANG1_TOI_THIEU or nen is None:
            continue
        p_hon = 1.0 - betainc(1.0 + h, 1.0 + n - h, min(max(float(nen), 1e-9), 1 - 1e-9))
        so = "tầng 1 ({0}): nổ +7n {1:.0%} vs rút ngẫu nhiên cùng tầng {2:.0%} (nâng {3:+.0f} điểm, n = {4}, " \
             "P(hơn) {5:.0%})".format(pham_vi, h / float(n), float(nen), 100 * (h / float(n) - float(nen)), n, p_hon)
        return (p_hon >= P_SAN_TANG1), (so if p_hon >= P_SAN_TANG1 else "chưa qua sàn — " + so)
    return False, "tầng 1 chưa đủ số (n < {0})".format(N_TANG1_TOI_THIEU)


def du_thu(bang: Dict[str, Any], kenh: str, gt: str) -> Tuple[bool, str]:
    """Giả thuyết MỚI được thử ở kênh? ≥ `NGAY_BONG` ngày bóng + qua sàn tầng 1."""
    so_ngay = int(((bang.get("ngay_bong") or {}).get(kenh) or {}).get(gt) or 0)
    if so_ngay < NGAY_BONG:
        return False, "mới chạy bóng {0}/{1} ngày ở kênh".format(so_ngay, NGAY_BONG)
    qua, ly = qua_san_tang1(bang, kenh, gt)
    return qua, "bóng {0} ngày; {1}".format(so_ngay, ly)


def vai_kenh(bang: Dict[str, Any], kenh: str) -> Dict[str, Tuple[str, str]]:
    """`{gt: (vai, lý do)}` của MỘT kênh — `loai` > `dan_dau` > `thu` > ""."""
    t2 = bang.get("tang2") or {}
    m = (t2.get("theo_kenh") or {}).get(kenh) or {}
    tt = {g: (o or {}).get("trang_thai") for g, o in (bang.get("gia_thuyet") or {}).items()}
    ra: Dict[str, Tuple[str, str]] = {}
    for gt in m:
        if tt.get(gt) == "loai":
            continue
        vai, ly = vai_theo_bang(m, gt)
        if not vai and tt.get(gt) == "bong":
            ok, ly2 = du_thu(bang, kenh, gt)
            vai, ly = (THU, ly2) if ok else ("", ly2)
        ra[gt] = (vai, ly)
    return ra


def _dong(loai: str, kenh: str, gt: str, bang: Dict[str, Any], o: Dict[str, Any], ly: str,
          doi: Optional[Tuple[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    pb = ((bang.get("gia_thuyet") or {}).get(gt) or {}).get("phien_ban")
    d = {"luc": c.luc_iso(), "ngay": c.hom_nay(), "loai": loai, "ten": TEN_LOAI.get(loai, loai), "kenh": kenh,
         "gt": gt, "pb": pb, **_so(o), "ly_do": ly,
         "nguong": {"p_dan_dau": P_DAN_DAU, "p_loai": P_LOAI, "n_quyet": N_QUYET, "ngay_bong": NGAY_BONG}}
    if doi and doi[0]:
        d["doi_thu"] = {"gt": doi[0], "n": doi[1].get("n"), "p_tot_nhat": doi[1].get("p_tot_nhat")}
    return d


_DOI = {("", DAN_DAU): "dan_dau", (DAN_DAU, ""): "mat_dan_dau", ("", LOAI): "loai_kenh", (LOAI, ""): "mo_lai_kenh",
        ("", THU): "mo_thu", (THU, ""): "dong_thu", (THU, DAN_DAU): "dan_dau", (DAN_DAU, THU): "mat_dan_dau",
        (THU, LOAI): "loai_kenh", (LOAI, THU): "mo_lai_kenh", (DAN_DAU, LOAI): "loai_kenh",
        (LOAI, DAN_DAU): "dan_dau"}


def ap_dung(goc: str, bang: Dict[str, Any], *, ghi: bool = True,
            log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Tính vai mọi (kênh × giả thuyết) + quyết định toàn danh mục; so với `trang-thai.json` → dòng quyết định cho mỗi
    thay đổi. `ghi=True`: ghi trạng thái, nối sổ quyết định, sửa sổ giả thuyết (loại chung / tốt nghiệp) và `bang`
    tại chỗ. Trả `{"kenh": {k: {gt: vai}}, "chung": {gt: vai}, "moi": [dòng quyết định]}`."""
    from . import gia_thuyet as gtm  # noqa: PLC0415

    t2 = bang.get("tang2") or {}
    cu = doc_trang_thai(goc)
    cu_k = cu.get("kenh") or {}
    moi: List[Dict[str, Any]] = []
    trang: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for kenh in sorted((t2.get("theo_kenh") or {}).keys()):
        m = (t2.get("theo_kenh") or {}).get(kenh) or {}
        v = vai_kenh(bang, kenh)
        trang[kenh] = {}
        try:
            from .chia_khe import bat as _khe_bat  # noqa: PLC0415

            khe_bat = bool(_khe_bat(goc, kenh)[0])
        except Exception:  # noqa: BLE001
            khe_bat = False
        for gt, (vai, ly) in sorted(v.items()):
            truoc = str(((cu_k.get(kenh) or {}).get(gt) or {}).get("vai") or "")
            tu = ((cu_k.get(kenh) or {}).get(gt) or {}).get("tu") if truoc == vai else c.hom_nay()
            trang[kenh][gt] = {"vai": vai, "tu": tu or c.hom_nay(), "ly_do": ly}
            loai = _DOI.get((truoc, vai))
            if loai:
                d = _dong(loai, kenh, gt, bang, m.get(gt) or {}, ly or "số không còn đạt ngưỡng", doi_thu_dan(m, gt))
                d["chia_khe"] = khe_bat
                moi.append(d)
    # Toàn danh mục: loại chung / tốt nghiệp (sửa sổ giả thuyết).
    ch = t2.get("chung") or {}
    reg_tt = {g: (o or {}).get("trang_thai") for g, o in (bang.get("gia_thuyet") or {}).items()}
    # 22/10/2026: giả thuyết chủ khoá chạy bóng tới ngày X — không tốt nghiệp trước ngày đó.
    khoa_chu = {g: str((o or {}).get("khoa_chu_den") or "") for g, o in (bang.get("gia_thuyet") or {}).items()}
    hom = c.hom_nay()
    doi_so: Dict[str, Tuple[str, str]] = {}
    for gt, o in sorted(ch.items()):
        if reg_tt.get(gt) == "loai":
            continue
        if reg_tt.get(gt) == "bong" and khoa_chu.get(gt, "") > hom:
            continue
        vai, ly = vai_theo_bang(ch, gt)
        if vai == LOAI:
            doi_so[gt] = ("loai", ly)
            moi.append(_dong("loai_chung", "", gt, bang, o, ly, doi_thu_dan(ch, gt)))
        elif reg_tt.get(gt) == "bong" and _du_n(o.get("n")) and o.get("p_tot_nhat") is not None:
            ly = "n danh mục = {0} ≥ {1}, không phải ứng viên loại (P(tốt nhất) {2:.0%})".format(
                o.get("n"), N_QUYET, float(o.get("p_tot_nhat") or 0))
            doi_so[gt] = ("song", ly)
            moi.append(_dong("tot_nghiep", "", gt, bang, o, ly))
    ra = {"kenh": {k: {g: x["vai"] for g, x in m.items()} for k, m in trang.items()},
          "chung": {g: v[0] for g, v in doi_so.items()}, "moi": moi}
    if not ghi:
        return ra
    if doi_so:
        try:
            gtm.doi_trang_thai(goc, {g: v for g, v in doi_so.items()})
        except Exception as loi:  # noqa: BLE001
            if log:
                log("  phòng thí nghiệm: không sửa được sổ giả thuyết: {0}".format(str(loi)[:120]))
        for g, (tt, _ly) in doi_so.items():
            if g in (bang.get("gia_thuyet") or {}):
                bang["gia_thuyet"][g]["trang_thai"] = tt
    chung_tt = dict(cu.get("chung") or {})
    chung_tt.update({g: {"trang_thai": v[0], "ly_do": v[1], "tu": c.hom_nay()} for g, v in doi_so.items()})
    c.ghi_json(duong_trang_thai(goc), {"luc": c.luc_iso(), "kenh": trang, "chung": chung_tt})
    if moi:
        ghi_quyet_dinh(goc, moi)
        if log:
            for d in moi:
                log("  phòng thí nghiệm — QUYẾT ĐỊNH: {0} {1}{2}: {3}".format(
                    d["ten"], d["gt"], " @" + d["kenh"] if d["kenh"] else "", d["ly_do"][:160]))
    return ra
