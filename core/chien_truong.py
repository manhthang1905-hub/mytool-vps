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
import math
import os
import sys
from typing import Any, Dict, List

GOC = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def _chan_de(z: Dict[str, Any]) -> float:
    """Thế chân của ta trong vùng, 0..1: chưa có video = 0,5 (đất trống, trung tính); đã cắm cờ = ~1 (lợi thế cùng tệp
    khán giả); càng chiếm nhiều thì còn ít chỗ để tăng → giảm dần tới 0,1 khi ta ≥ 50%."""
    if not z.get("so_ta"):
        return 0.5
    return max(0.1, 1.0 - 0.9 * min(1.0, float(z.get("thi_phan") or 0) / 50.0))


def tinh_co_hoi(ds: List[Dict[str, Any]]) -> None:
    """Gắn `co_hoi` (0–100) + `co_hoi_chi_tiet` vào từng vùng (sửa tại chỗ). CÔNG THỨC:
        co_hoi = 100 × (0,35·cau + 0,25·da + 0,20·yeu + 0,20·chan)
      cau  = log(1+địch) / log(1+địch lớn nhất)        — cầu: vùng càng nhiều lượt xem càng đáng đánh (thang log)
      da   = log(1+Σ tăng/ngày) / log(1+max)           — đà: tổng tốc độ tăng của video đối thủ trong vùng
      yeu  = 1 − (view kênh dẫn đầu / địch)            — địch dẫn đầu càng yếu/phân tán càng dễ chen vào
      chan = _chan_de(vùng)                            — thế chân của ta (xem trên)
    Các thành phần đều tăng theo cầu/đà/độ phân tán nên co_hoi đơn điệu theo từng yếu tố khi giữ các yếu tố khác."""
    that = [z for z in ds if z.get("ma") != KHAC] or ds      # «Đề tài khác» là bãi gom, không làm thước đo
    # 06/10: cầu/đà = (giá trị / lớn nhất)^0,35 — thang log cũ dồn mọi vùng về 85–90; xếp hạng % thì 2 vùng gần bằng nhau
    # lệch nhau cả 35 điểm. Thang mũ: gần bằng → gần bằng điểm; nhỏ hơn 100 lần → ~0,2.
    mx_dich = max([float(z.get("dich") or 0) for z in that] + [1.0])
    mx_da = max([max(0.0, float(z.get("nong") or 0)) for z in that] + [1.0])
    for z in ds:
        dich = float(z.get("dich") or 0)
        cau = min(1.0, (max(0.0, dich) / mx_dich) ** 0.35)
        da = min(1.0, (max(0.0, float(z.get("nong") or 0)) / mx_da) ** 0.35)
        dm = z.get("dich_manh") or []
        yeu = 1.0 - min(1.0, float(dm[0]["view"]) / dich) if dm and dich > 0 else 0.0
        chan = _chan_de(z)
        z["co_hoi"] = round(100.0 * (0.35 * cau + 0.25 * da + 0.20 * yeu + 0.20 * chan), 1)
        z["co_hoi_chi_tiet"] = {"cau": round(cau, 2), "da": round(da, 2), "yeu": round(yeu, 2), "chan": round(chan, 2)}


def de_xuat_tan_cong(ds: List[Dict[str, Any]], quan: List[Dict[str, Any]], so_vung: int = 2) -> List[Dict[str, Any]]:
    """Mỗi kênh ta đang sản xuất (có video) → top `so_vung` vùng theo co_hoi, ưu tiên vùng kênh đó (+12) hoặc kênh anh em (+6)
    đã có video (cùng tệp khán giả). Bỏ vùng «khac»."""
    ra = []
    for q in quan:
        if not q.get("so_video"):
            continue
        ung = []
        for z in ds:
            if z["ma"] == KHAC or "co_hoi" not in z:
                continue
            own = q["ma"] in (z.get("ta_kenh") or [])
            anh_em = bool(z.get("ta_kenh")) and not own
            diem = z["co_hoi"] + (12 if own else 6 if anh_em else 0)
            cd = z.get("co_hoi_chi_tiet") or {}
            dm = (z.get("dich_manh") or [{}])[0]
            ly = "cầu {0}, địch dẫn đầu {1} giữ {2}%".format(
                _gon(z["dich"]), dm.get("kenh") or "—", round(100 * (1 - cd.get("yeu", 0))))
            ly += "; kênh này đã có video ở đây" if own else ("; kênh anh em đã có mặt" if anh_em else "; đất trống, chưa ai của ta")
            if z.get("nong"):
                ly += "; đà +{0}/ngày".format(_gon(z["nong"]))
            ung.append({"ma": z["ma"], "ten": z["ten"], "co_hoi": z["co_hoi"], "diem": round(diem, 1),
                        "thi_phan": z.get("thi_phan", 0), "ly_do": ly})
        ung.sort(key=lambda x: -x["diem"])
        ra.append({"kenh": q["ma"], "ten": q.get("ten", ""), "vung": ung[:so_vung]})
    return ra


def _gon(n) -> str:
    n = float(n or 0)
    return "%.1ftr" % (n / 1e6) if n >= 1e6 else ("%dN" % round(n / 1e3) if n >= 1e4 else "%d" % round(n))


def _lich_su_gon(hom: _dt.date, du: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ghi ảnh chụp ngày (tối đa 1 lần/ngày; tắt bằng MYTOOL_CHIEN_TRUONG_GHI=0) và trả 30 ngày gần nhất cho biểu đồ."""
    try:
        from core import chien_truong_lich_su as ls  # noqa: PLC0415
        ngay = hom.isoformat()
        if os.environ.get("MYTOOL_CHIEN_TRUONG_GHI", "1") != "0" and not ls.co_anh_hom_nay(GOC, ngay):
            ls.ghi_anh_chup(GOC, du, ngay)
        return ls.chuoi_gon(GOC, 30)
    except Exception:  # noqa: BLE001
        return []


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
    tinh_co_hoi(ds)
    ra = {
        "luc": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "cua_so_ngay": NGAY, "ngach": "Tâm lý Nhật",
        "cach_do": "lượt xem/tháng ước TỐI THIỂU: video có tốc độ đo được = tăng/ngày×30; video mới trong cửa sổ = toàn bộ "
                   "lượt xem; video cũ chưa đo = 0. Phe ta = lượt xem 28 ngày thật từ Studio.",
        "tong": {"dich": tong_dich, "ta": tong_ta, "thi_phan": round(100.0 * tong_ta / (tong_dich + tong_ta), 3) if (tong_dich + tong_ta) else 0,
                 "so_vung": len(ds), "vung_ta_dan": sum(1 for z in ds if z["thi_phan"] >= 50),
                 "so_video_dt": sum(z["so_dt"] for z in ds), "so_kenh_dt": len({k for z in vung.values() for k in z["kenh_dich"]})},
        "vung": ds, "nong": nong[:8], "quan": quan, "dich_top": dich_top,
    }
    ra["de_xuat_tan_cong"] = de_xuat_tan_cong(ds, quan)
    ra["lich_su"] = _lich_su_gon(hom, ra)
    return ra


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
    print("— cơ hội —")
    for z in sorted(d["vung"], key=lambda z: -z["co_hoi"])[:6]:
        print("{0:<28} co_hoi {1:>5} {2}".format(z["ten"][:28], z["co_hoi"], z["co_hoi_chi_tiet"]))
    for x in d["de_xuat_tan_cong"]:
        print(x["kenh"], "→", " | ".join("%s (%s)" % (v["ten"], v["co_hoi"]) for v in x["vung"]))
    print("lich_su:", len(d["lich_su"]), "điểm")
