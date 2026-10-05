"""CHIẾN TRƯỜNG (06/10/2026) — YouTube là trận chiếm thị phần: số liệu cho bản đồ trận đánh của trang trực quan.

Lãnh thổ = CỤM ĐỀ TÀI của ngách (đúng bộ cụm vòng tự học dùng — `cong_thuc_v7.cum_cua_tieu_de`, gộp mọi kênh ta).
Đất mỗi vùng = lượt xem video ĐỐI THỦ đăng trong N ngày gần đây (kho `nghien-cuu/content.csv` của các kênh ta,
gộp, bỏ trùng); phần của ta = lượt xem video của ta trong vùng (`chi-so/bang-tom-tat.csv`). Thị phần = ta / (ta + địch).
Điểm nóng = video đối thủ mới đang tăng nhanh nhất (Tăng/ngày). Quân ta = 7 kênh: sức (giờ xem, người đăng ký 28 ngày),
mặt trận đang đánh (cụm các video gần nhất + video ngày mai). Chỉ ĐỌC đĩa, không mạng, không tiền.
"""
from __future__ import annotations

import copy
import csv
import datetime as _dt
import io
import json
import os
import sys
from typing import Any, Dict, List

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NGAY = 28
NGAY_NONG = 14
KHAC = "khac"


def _so(x) -> float:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip() or 0)
    except ValueError:
        return 0.0


def _ngay(x):
    try:
        return _dt.date.fromisoformat(str(x).strip()[:10])
    except ValueError:
        return None


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with io.open(duong, "r", encoding="utf-8-sig", errors="replace", newline="") as tep:
            return list(csv.DictReader(tep))
    except OSError:
        return []


def _cac_kenh() -> List[str]:
    try:
        with open(os.path.join(GOC, "vm", "cai-dat-tool.json"), "r", encoding="utf-8") as tep:
            return sorted((json.load(tep).get("kenh") or {}).keys())
    except (OSError, ValueError):
        return []


def _bo_cum(cac_kenh: List[str]):
    """Gộp bộ cụm của mọi kênh ta → một cấu hình v7 dùng chung cho cả chiến trường."""
    if GOC not in sys.path:
        sys.path.insert(0, GOC)
    from core import cong_thuc_v7 as v7  # noqa: PLC0415
    gop: Dict[str, Dict] = {}
    for k in cac_kenh:
        try:
            ch, _ = v7.nap_cau_hinh(GOC, k, ghi_neu_thieu=False)
        except Exception:  # noqa: BLE001
            continue
        for ma, c in (ch.get("cum") or {}).items():
            if ma not in gop:
                gop[ma] = copy.deepcopy(c)
            else:
                gop[ma]["tu"] = sorted(set(gop[ma].get("tu") or []) | set(c.get("tu") or []))
    ch = copy.deepcopy(v7.CAU_HINH_MAC_DINH)
    ch["cum"] = gop
    return v7, ch, {ma: str(c.get("ten") or ma) for ma, c in gop.items()}


def _cum(v7, ch, tieu_de: str) -> str:
    try:
        ds = v7.cum_cua_tieu_de(tieu_de, ch)
    except Exception:  # noqa: BLE001
        ds = []
    return ds[0] if ds else KHAC


def _ten_kenh(kenh: str) -> str:
    try:
        from core import truc_quan  # noqa: PLC0415
        return truc_quan._ten_kenh(kenh)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return ""


def _video_dich(cac: List[str], v7, ch, tu: _dt.date):
    """Video của ĐỐI THỦ THẬT (danh bạ «theo dõi» — kho content.csv lẫn kênh trang chủ ngoài ngách), gộp + bỏ trùng,
    kèm LƯỢT XEM/THÁNG ước TỐI THIỂU: có tốc độ đo được → tăng/ngày × 30 (cả video cũ còn ăn view); mới đăng trong
    cửa sổ → toàn bộ lượt xem; video cũ chưa đo tốc độ → bỏ (không đoán)."""
    dich_that = {r.get("Kênh") for k in cac for r in _doc_csv(os.path.join(GOC, "CHANNEL", k, "nghien-cuu", "doi-thu.csv"))
                 if r.get("Trạng thái") == "theo dõi"} - {None, ""}
    ta_ten = {_ten_kenh(k) for k in cac} - {""}
    thay = set()
    for k in cac:
        for r in _doc_csv(os.path.join(GOC, "CHANNEL", k, "nghien-cuu", "content.csv")):
            link = r.get("Link video") or ""
            if not link or link in thay:
                continue
            thay.add(link)
            d = _ngay(r.get("Ngày đăng"))
            if not d or r.get("Kênh") in ta_ten or r.get("Kênh") not in dich_that:
                continue
            v, tang = _so(r.get("View")), _so(r.get("Tăng/ngày"))
            thang = tang * 30 if tang > 0 else (v if d >= tu else 0.0)
            if thang <= 0:
                continue
            td = r.get("Tiêu đề video") or ""
            yield {"link": link, "kenh": r.get("Kênh") or "?", "tieu_de": td, "tieu_de_viet": r.get("Tiêu đề (Việt)") or td,
                   "ngay": d, "view": v, "tang": tang, "thang": thang, "cum": _cum(v7, ch, td)}


def video_khac(bay_gio: _dt.date = None) -> List[Dict[str, Any]]:
    """Video đối thủ bộ cụm từ khoá KHÔNG nhận («Đề tài khác»), nhiều lượt xem/tháng nhất trước — đầu vào AI chia vùng."""
    hom = bay_gio or _dt.date.today()
    cac = _cac_kenh()
    v7, ch, _ten = _bo_cum(cac)
    ds = [x for x in _video_dich(cac, v7, ch, hom - _dt.timedelta(days=NGAY)) if x["cum"] == KHAC]
    return sorted(ds, key=lambda x: -x["thang"])


def ten_vung_tu_khoa() -> Dict[str, str]:
    return _bo_cum(_cac_kenh())[2]


def tinh(bay_gio: _dt.date = None) -> Dict[str, Any]:
    hom = bay_gio or _dt.date.today()
    tu = hom - _dt.timedelta(days=NGAY)
    tu_nong = hom - _dt.timedelta(days=NGAY_NONG)
    cac = _cac_kenh()
    v7, ch, ten_cum = _bo_cum(cac)
    ten_cum[KHAC] = "Đề tài khác"
    try:
        from core import chien_truong_ai  # noqa: PLC0415
        ai = chien_truong_ai.doc()
    except Exception:  # noqa: BLE001
        ai = {}
    ai_video = ai.get("video") or {}
    ten_cum.update(ai.get("vung_moi") or {})
    vung: Dict[str, Dict[str, Any]] = {m: {"ma": m, "ten": t, "dich": 0.0, "ta": 0.0, "so_dt": 0, "so_ta": 0,
                                           "nong": 0.0, "kenh_dich": {}, "kenh_ta": {}} for m, t in ten_cum.items()}
    nong = []
    for x in _video_dich(cac, v7, ch, tu):
        m = x["cum"]
        if m == KHAC and x["link"] in ai_video:          # AI chia vùng theo NGHĨA (core/chien_truong_ai)
            m = ai_video[x["link"]]
            if m == "ngoai-ngach":
                continue
            if m not in vung:
                vung[m] = {"ma": m, "ten": ten_cum.get(m, m), "dich": 0.0, "ta": 0.0, "so_dt": 0, "so_ta": 0,
                           "nong": 0.0, "kenh_dich": {}, "kenh_ta": {}}
        z, v, kd = vung[m], x["thang"], x["kenh"]
        z["dich"] += v
        z["so_dt"] += 1
        z["nong"] += x["tang"]
        z["kenh_dich"][kd] = z["kenh_dich"].get(kd, 0.0) + v
        if x["ngay"] >= tu_nong and x["tang"] > 0:
            nong.append({"kenh": kd, "tieu_de": x["tieu_de_viet"][:90], "tieu_de_goc": x["tieu_de"][:90], "view": x["view"],
                         "tang": x["tang"], "cum": m, "ngay": str(x["ngay"]), "link": x["link"]})
    # ── phe ta ──
    quan = []
    for k in cac:
        rows = _doc_csv(os.path.join(GOC, "CHANNEL", k, "chi-so", "bang-tom-tat.csv"))
        mat_tran: Dict[str, int] = {}
        tot = None
        for r in rows:
            d = _ngay(r.get("Ngày đăng"))
            m = _cum(v7, ch, r.get("Tiêu đề") or "")
            mat_tran[m] = mat_tran.get(m, 0) + 1
            if not d or d < tu:
                continue
            v = _so(r.get("Lượt xem"))
            vung[m]["ta"] += v
            vung[m]["so_ta"] += 1
            vung[m]["kenh_ta"][k] = vung[m]["kenh_ta"].get(k, 0.0) + v
            ht = _so(r.get("Lượt hiển thị"))
            if tot is None or ht > tot["hien_thi"]:
                tot = {"tieu_de": (r.get("Tiêu đề") or "")[:80], "hien_thi": ht, "ctr": r.get("Tỷ lệ bấm"), "view": v, "ngay": str(d)}
        kn = _doc_csv(os.path.join(GOC, "CHANNEL", k, "chi-so", "kenh-theo-ngay.csv"))
        cuoi = kn[-1] if kn else {}
        truoc = kn[-2] if len(kn) > 1 else {}
        try:
            from core import truc_quan  # noqa: PLC0415
            mai = truc_quan._video_mai(k, tu_ngay=hom)  # noqa: SLF001 — video lên sóng SỚM NHẤT từ hôm nay
        except Exception:  # noqa: BLE001
            mai = {}
        cum_mai = _cum(v7, ch, mai.get("tieu_de") or "") if mai.get("co") else ""
        quan.append({
            "ma": k, "ten": _ten_kenh(k), "gio_xem": _so(cuoi.get("Giờ xem")), "dang_ky": _so(cuoi.get("Đăng ký")),
            "view_28": _so(cuoi.get("Lượt xem")), "gio_tang": _so(cuoi.get("Giờ xem")) - _so(truoc.get("Giờ xem")),
            "luc_so": cuoi.get("Lúc chụp") or "", "mat_tran": sorted(mat_tran, key=lambda x: -mat_tran[x])[:3],
            "tan_cong": cum_mai, "video_mai": (mai.get("tieu_de") or "")[:80], "ngay_mai": mai.get("ngay") or "",
            "da_hen": bool(mai.get("da_hen")), "tot_nhat": tot, "so_video": len(rows),
        })
    # ── tổng hợp ──
    ds = []
    for z in vung.values():
        if z["dich"] <= 0 and z["ta"] <= 0:
            continue
        top = sorted(z["kenh_dich"].items(), key=lambda x: -x[1])[:3]
        tong = z["dich"] + z["ta"]
        ds.append({"ma": z["ma"], "ten": z["ten"], "dich": round(z["dich"]), "ta": round(z["ta"]),
                   "thi_phan": round(100.0 * z["ta"] / tong, 2) if tong else 0.0, "so_dt": z["so_dt"], "so_ta": z["so_ta"],
                   "nong": round(z["nong"]), "dich_manh": [{"kenh": a, "view": round(b)} for a, b in top],
                   "ta_kenh": sorted(z["kenh_ta"], key=lambda x: -z["kenh_ta"][x])})
    ds.sort(key=lambda z: -(z["dich"] + z["ta"]))
    bxh: Dict[str, Dict[str, Any]] = {}
    for z in vung.values():
        for kd, v in z["kenh_dich"].items():
            b = bxh.setdefault(kd, {"kenh": kd, "view": 0.0, "vung": {}})
            b["view"] += v
            b["vung"][z["ten"]] = b["vung"].get(z["ten"], 0.0) + v
    dich_top = [{"kenh": b["kenh"], "view": round(b["view"]),
                 "vung_chinh": sorted(b["vung"], key=lambda x: -b["vung"][x])[:2]}
                for b in sorted(bxh.values(), key=lambda b: -b["view"])[:10]]
    tong_dich = sum(z["dich"] for z in ds)
    tong_ta = sum(q["view_28"] for q in quan)          # phe ta: lượt xem 28 ngày THẬT từ Studio (mọi kênh ta)
    for b in dich_top:
        b["thi_phan"] = round(100.0 * b["view"] / (tong_dich + tong_ta), 2) if (tong_dich + tong_ta) else 0.0
    nong.sort(key=lambda x: -x["tang"])
    for q in quan:
        q["tan_cong_ten"] = ten_cum.get(q["tan_cong"], "") if q["tan_cong"] else ""
        q["mat_tran_ten"] = [ten_cum.get(m, m) for m in q["mat_tran"]]
    return {
        "luc": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "cua_so_ngay": NGAY, "ngach": "Tâm lý Nhật",
        "cach_do": "lượt xem/tháng ước TỐI THIỂU: video có tốc độ đo được = tăng/ngày×30; video mới trong cửa sổ = toàn bộ "
                   "lượt xem; video cũ chưa đo = 0. Phe ta = lượt xem 28 ngày thật từ Studio.",
        "tong": {"dich": tong_dich, "ta": tong_ta, "thi_phan": round(100.0 * tong_ta / (tong_dich + tong_ta), 3) if (tong_dich + tong_ta) else 0,
                 "so_vung": len(ds), "vung_ta_dan": sum(1 for z in ds if z["thi_phan"] >= 50),
                 "so_video_dt": sum(z["so_dt"] for z in ds), "so_kenh_dt": len({k for z in vung.values() for k in z["kenh_dich"]})},
        "vung": ds, "nong": nong[:8], "quan": quan, "dich_top": dich_top,
    }


if __name__ == "__main__":
    import time as _t
    t0 = _t.time()
    d = tinh()
    print(json.dumps({k: d[k] for k in ("tong", "luc")}, ensure_ascii=False), "| %.1fs" % (_t.time() - t0))
    for z in d["vung"][:14]:
        print("{0:<28} địch {1:>12,.0f} | ta {2:>9,.0f} | {3:>5}% | {4}".format(z["ten"][:28], z["dich"], z["ta"], z["thi_phan"],
                                                                         ", ".join(x["kenh"] for x in z["dich_manh"])[:60]))
    for q in d["quan"]:
        print(q["ma"], q["gio_xem"], q["dang_ky"], q["mat_tran_ten"], "→", q["tan_cong_ten"])
