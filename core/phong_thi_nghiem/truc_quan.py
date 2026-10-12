"""Dữ liệu tab «Phòng thí nghiệm» của trung tâm trực quan (8790, `core/truc_quan.py` → `/phong-thi-nghiem.json`).

Chỉ ĐỌC: bảng xếp hạng, sổ giả thuyết, nhật ký bóng (top-3 mới nhất mỗi giả thuyết), sổ quyết định, lịch sử bảng, sổ
lượt (khe đã dùng). Mỗi phần bọc riêng — hỏng phần nào chỉ phần đó rỗng + `loi`. Nhớ đệm 5 phút.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

from . import _chung as c

NGAY_QUYET_DINH = 40


def _o_tang1(o: Dict[str, Any], kq: str) -> Dict[str, Any]:
    z = (o or {}).get(kq) or {}
    return {"n": z.get("n"), "ti_le": z.get("ti_le"), "ci90": z.get("ci90"), "nen": z.get("nen"), "nang": z.get("nang"),
            "nen_tang": z.get("nen_tang"), "nang_tang": z.get("nang_tang"), "nang_cong": z.get("nang_cong")}


def _dong(gt: str, o: Dict[str, Any]) -> Dict[str, Any]:
    n = int(o.get("n") or 0)
    return {"gt": gt, "n": n, "n_chinh_xac": int(o.get("n_chinh_xac") or 0), "thang": int(o.get("thang") or 0),
            "diem": o.get("diem"), "ti_le": round(float(o.get("diem") or 0) / n, 3) if n else None, "tb": o.get("tb"),
            "ci90": o.get("ci90"), "p": o.get("p_tot_nhat"), "cho": int(o.get("cho") or 0),
            "co_nhat_ky": o.get("co_nhat_ky", True)}


def _bong_moi_nhat(goc: str, ngay: str) -> Dict[str, Dict[str, Any]]:
    """`{kênh: {"ngay": d, "gt": {gt: [top-3]}}}` — dòng nhật ký bóng MỚI NHẤT (≤ 3 ngày) của mỗi (kênh, giả thuyết)."""
    from . import nhat_ky  # noqa: PLC0415

    ra: Dict[str, Dict[str, Any]] = {}
    for x in nhat_ky.doc(goc, tu=c.cong_ngay(ngay, -3), den=ngay):
        k, gt = x.get("kenh", ""), x.get("gt", "")
        o = ra.setdefault(k, {"ngay": "", "gt": {}})
        cu = o["gt"].get(gt)
        if cu is not None and cu["ngay"] > x.get("ngay", ""):
            continue
        top = []
        for it in (x.get("top") or [])[:3]:
            v, tv = c.so(it.get("v")), c.so(it.get("tv"))
            top.append({"ma": it.get("ma"), "td": it.get("td") or "", "kn": it.get("kn") or "", "v": v,
                        "gap": round(v / tv, 1) if (v and tv) else None, "d": it.get("d"),
                        "link": "https://www.youtube.com/watch?v={0}".format(it.get("ma"))})
        o["gt"][gt] = {"ngay": x.get("ngay", ""), "n_du": x.get("n_du"), "che_do": x.get("che_do"), "top": top}
        o["ngay"] = max(o["ngay"], x.get("ngay", ""))
    return ra


def tinh(goc: str) -> Dict[str, Any]:
    from . import chia_khe, danh_gia, luat  # noqa: PLC0415

    hom = c.hom_nay()
    bang = danh_gia.doc_bang(goc)
    ts = bang.get("tham_so") or {}
    kq = ts.get("kq_chinh", danh_gia.KQ_CHINH)
    t1, t2 = bang.get("tang1") or {}, bang.get("tang2") or {}
    gts = bang.get("gia_thuyet") or {}
    tn = bang.get("tien_nghiem_tang1") or {}
    ra: Dict[str, Any] = {
        "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "hom_nay": hom, "bang_luc": bang.get("luc"),
        "co_bang": bool(bang), "kq_chinh": kq, "so_nhat_ky": bang.get("so_nhat_ky", 0),
        "tham_so": {"p_dan_dau": luat.P_DAN_DAU, "p_loai": luat.P_LOAI, "n_quyet": luat.N_QUYET,
                    "ngay_bong": luat.NGAY_BONG, "kham_pha": chia_khe.KHAM_PHA, "khe_thu_tuan": chia_khe.KHE_THU_TUAN,
                    "kappa_tang1": ts.get("kappa_tang1"), "kappa_chung": ts.get("kappa_chung"),
                    "kappa_kenh": ts.get("kappa_kenh")},
        "nen": {"g": t2.get("g"), "n": t2.get("n_nen")},
        "gia_thuyet": {g: {x: (o or {}).get(x) for x in ("mo_ta", "trang_thai", "loai", "tao_boi", "tao_luc",
                                                         "phien_ban")} for g, o in gts.items()},
    }
    ch2 = t2.get("chung") or {}
    ra["chung"] = sorted(({**_dong(g, o), "tang1": _o_tang1((t1.get("chung") or {}).get(g) or {}, kq),
                           "m1": (tn.get(g) or {}).get("m"), "w1": (tn.get(g) or {}).get("w")}
                          for g, o in ch2.items()), key=lambda r: (-(r["p"] or -1), r["gt"]))
    lich = []
    try:
        lich = danh_gia.doc_lich_su(goc)
    except Exception:  # noqa: BLE001
        pass
    truoc = next((x for x in reversed(lich) if x.get("ngay") and x["ngay"] < (bang.get("ngay") or hom)), None)
    try:
        bong = _bong_moi_nhat(goc, hom)
    except Exception as loi:  # noqa: BLE001
        bong, ra["loi_bong"] = {}, str(loi)[:200]
    kenh_ds = list(bang.get("kenh") or [])
    ds_kenh: List[Dict[str, Any]] = []
    for k in kenh_ds:
        m = (t2.get("theo_kenh") or {}).get(k) or {}
        nk = (t2.get("nen_kenh") or {}).get(k) or {}
        o: Dict[str, Any] = {"ma": k, "n_phan": nk.get("n", 0), "cho": nk.get("cho", 0),
                             "diem_tb": round(float(nk.get("diem") or 0) / nk["n"], 3) if nk.get("n") else None}
        try:
            tt = chia_khe.tom_tat_kenh(goc, k, ngay=hom, bang=bang)
        except Exception as loi:  # noqa: BLE001
            tt = {"bat": False, "vi_sao": "lỗi: {0}".format(str(loi)[:120]), "vai": {}, "chan": {}, "khe_7_ngay": {},
                  "ti_le_khe": {}}
        o.update(chia_khe=tt["bat"], vi_sao=tt["vi_sao"])
        tk1 = (t1.get("theo_kenh") or {}).get(k) or {}
        tr = ((truoc or {}).get("kenh") or {}).get(k) or {}
        dong = []
        for g, x in m.items():
            r = _dong(g, x)
            cell = tk1.get(g) or {}
            r["tang1"] = _o_tang1(cell if ((cell.get(kq) or {}).get("n") or 0) >= danh_gia.N_TANG1_TOI_THIEU
                                  else ((t1.get("chung") or {}).get(g) or {}), kq)
            r["tang1_pham_vi"] = "kênh" if ((cell.get(kq) or {}).get("n") or 0) >= danh_gia.N_TANG1_TOI_THIEU \
                else "danh mục"
            r["vai"] = (tt.get("vai") or {}).get(g) or ""
            r["trang_thai"] = (gts.get(g) or {}).get("trang_thai", "")
            r["chan"] = (tt.get("chan") or {}).get(g, "")
            r["khe_7_ngay"] = (tt.get("khe_7_ngay") or {}).get(g, 0)
            r["ti_le_khe"] = (tt.get("ti_le_khe") or {}).get(g)
            p0 = tr.get(g) or [None, None, None, None]
            r["delta_p"] = round(float(r["p"]) - float(p0[3]), 3) if (r["p"] is not None and len(p0) > 3
                                                                      and p0[3] is not None) else None
            r["delta_n"] = (r["n"] - int(p0[0] or 0)) if p0 and p0[0] is not None else None
            dong.append(r)
        o["bang"] = sorted(dong, key=lambda r: (-(r["p"] or -1), r["gt"]))
        b = bong.get(k) or {}
        o["bong"] = {"ngay": b.get("ngay", ""), "gt": b.get("gt") or {}}
        ds_kenh.append(o)
    ra["kenh"] = ds_kenh
    ra["so_sanh"] = (truoc or {}).get("ngay")
    try:
        qd = luat.doc_quyet_dinh(goc, NGAY_QUYET_DINH)
        ra["quyet_dinh"] = list(reversed(qd))
    except Exception as loi:  # noqa: BLE001
        ra["quyet_dinh"] = {"loi": str(loi)[:200]}
    return ra


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None, "goc": ""}
_KHOA = threading.Lock()


def tinh_nho(goc: str, han: float = 300.0) -> Dict[str, Any]:
    with _KHOA:
        if _NHO["du"] is None or _NHO["goc"] != goc or time.time() - _NHO["luc"] > han:
            _NHO["du"], _NHO["luc"], _NHO["goc"] = tinh(goc), time.time(), goc
        return _NHO["du"]


def tinh_an_toan(goc: str) -> Dict[str, Any]:
    try:
        return tinh_nho(goc)
    except Exception as loi:  # noqa: BLE001
        return {"loi": "{0}: {1}".format(type(loi).__name__, str(loi)[:200])}


__all__ = ["tinh", "tinh_nho", "tinh_an_toan"]
