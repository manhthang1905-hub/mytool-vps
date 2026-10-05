"""ĐƯỜNG TỚI KIẾM TIỀN (YouTube Partner Program) — dự báo từ chỉ số Studio đã chụp hằng ngày.

Đọc CHANNEL/<k>/chi-so/kenh-theo-ngay.csv (cột: Lúc chụp, Lượt xem, Giờ xem, Đăng ký, Lượt hiển thị, Tỷ lệ bấm).
Mỗi dòng là tổng của CỬA SỔ 28 NGÀY trượt ở lúc chụp (Đăng ký = người đăng ký mới trong cửa sổ ≈ tổng với kênh trẻ).

Dùng:  python -m core.ypp              bảng mọi kênh (kênh khai trong vm/cai-dat-tool.json)
       python -m core.ypp --canh-bao   ghi cảnh báo kênh vừa "gần"/"đạt" vào workspace/loi-chay-max.md (chỉ nối thêm)

LƯU Ý QUAN TRỌNG: YPP đòi 4.000 giờ xem CÔNG KHAI trong 365 ngày (hoặc 3 triệu lượt Shorts/90 ngày) và 1.000 đăng ký.
Ta chỉ thấy cửa sổ 28 ngày, nên giờ xem 28 ngày là CẬN DƯỚI của số giờ 365 ngày (kênh còn trẻ <28 ngày thì gần bằng nhau).
Dự báo "ngày tới 4.000 giờ" vì thế là ước lượng THẬN TRỌNG (thực tế có thể tới sớm hơn). Studio mới là nguồn quyết định cuối.
Tốc độ tăng = trung vị của ≤7 chênh lệch/ngày gần nhất (bỏ chênh âm và ngoại lai >5× trung vị) — chịu được một lần chụp lỗi.
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import statistics
from typing import Dict, List, Optional

NGUONG_GIO = 4000.0
NGUONG_DANG_KY = 1000
NGAY_GAN = 14
TOI_THIEU_MAU = 3
TEP_CANH_BAO = os.path.join("workspace", "loi-chay-max.md")
THU_MUC_NEN = os.path.join("workspace", "ypp")


def _so(v) -> Optional[float]:
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _doc_chup(goc: str, kenh: str) -> List[dict]:
    """[{luc, gio, dk}] theo thời gian; bỏ dòng hỏng; cùng phút → lấy dòng sau."""
    duong = os.path.join(goc, "CHANNEL", kenh, "chi-so", "kenh-theo-ngay.csv")
    ra: Dict[_dt.datetime, dict] = {}
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            for d in csv.DictReader(tep):
                try:
                    luc = _dt.datetime.strptime((d.get("Lúc chụp") or "").strip(), "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                gio, dk = _so(d.get("Giờ xem")), _so(d.get("Đăng ký"))
                if gio is None or dk is None:
                    continue
                ra[luc] = {"luc": luc, "gio": gio, "dk": dk}
    except OSError:
        return []
    return [ra[k] for k in sorted(ra)]


def _toc_do(chup: List[dict], khoa: str) -> float:
    """Mức tăng/ngày: trung vị ≤7 chênh lệch/ngày gần nhất, bỏ âm và ngoại lai."""
    ds = []
    for a, b in zip(chup, chup[1:]):
        ngay = (b["luc"] - a["luc"]).total_seconds() / 86400.0
        if ngay < 0.05:
            continue
        ds.append((b[khoa] - a[khoa]) / ngay)
    ds = [x for x in ds[-7:] if x >= 0]
    if not ds:
        return 0.0
    tv = statistics.median(ds)
    if tv > 0:
        ds = [x for x in ds if x <= 5 * tv] or ds
        tv = statistics.median(ds)
    return tv


def _eta(hien: float, nguong: float, toc: float) -> Optional[float]:
    if hien >= nguong:
        return 0.0
    return None if toc <= 0 else (nguong - hien) / toc


def du_bao(goc: str, kenh: str, bay_gio: Optional[_dt.datetime] = None) -> dict:
    """Dự báo YPP một kênh. Khoá: kenh, so_mau, gio, dang_ky, toc_gio, toc_dk, ngay_gio, ngay_dk, ngay_toi, ngay_du_kien, trang_thai.
    trang_thai: dat | gan (≤14 ngày) | dang_len | cham (không tăng) | chua_du_so (<3 lần chụp).
    Giờ xem là cửa sổ 28 ngày = cận dưới của yêu cầu 365 ngày (xem đầu tệp)."""
    chup = _doc_chup(goc, kenh)
    r = {"kenh": kenh, "so_mau": len(chup), "gio": None, "dang_ky": None, "toc_gio": 0.0, "toc_dk": 0.0,
         "ngay_gio": None, "ngay_dk": None, "ngay_toi": None, "ngay_du_kien": None, "trang_thai": "chua_du_so"}
    if chup:
        r["gio"], r["dang_ky"] = chup[-1]["gio"], int(chup[-1]["dk"])
    if len(chup) < TOI_THIEU_MAU:
        return r
    r["toc_gio"], r["toc_dk"] = _toc_do(chup, "gio"), _toc_do(chup, "dk")
    r["ngay_gio"] = _eta(r["gio"], NGUONG_GIO, r["toc_gio"])
    r["ngay_dk"] = _eta(r["dang_ky"], NGUONG_DANG_KY, r["toc_dk"])
    if r["ngay_gio"] == 0 and r["ngay_dk"] == 0:
        r["trang_thai"] = "dat"
        r["ngay_toi"] = 0.0
        return r
    if r["ngay_gio"] is None or r["ngay_dk"] is None:
        r["trang_thai"] = "cham"
        return r
    toi = max(r["ngay_gio"], r["ngay_dk"])
    r["ngay_toi"] = toi
    r["ngay_du_kien"] = ((bay_gio or _dt.datetime.now()) + _dt.timedelta(days=toi)).strftime("%Y-%m-%d")
    r["trang_thai"] = "gan" if toi <= NGAY_GAN else "dang_len"
    return r


def cac_kenh(goc: str) -> List[str]:
    try:
        with open(os.path.join(goc, "vm", "cai-dat-tool.json"), "r", encoding="utf-8") as tep:
            ds = sorted(((json.load(tep) or {}).get("kenh") or {}).keys())
        if ds:
            return ds
    except (OSError, ValueError):
        pass
    try:
        return sorted(x for x in os.listdir(os.path.join(goc, "CHANNEL"))
                      if os.path.isfile(os.path.join(goc, "CHANNEL", x, "chi-so", "kenh-theo-ngay.csv")))
    except OSError:
        return []


def _van_ban(r: dict) -> str:
    if r["trang_thai"] == "dat":
        return "ĐÃ ĐỦ điều kiện YPP theo số 28 ngày ({0:.0f} giờ, {1} đăng ký) — vào Studio → Kiếm tiền để nộp đơn.".format(r["gio"], r["dang_ky"])
    return "sắp đủ điều kiện YPP: {0:.0f}/4000 giờ, {1}/1000 đăng ký, dự kiến ~{2} (còn ~{3:.0f} ngày; cận dưới theo cửa sổ 28 ngày).".format(
        r["gio"], r["dang_ky"], r["ngay_du_kien"], r["ngay_toi"])


def _nen(goc: str, nen: Optional[str]) -> str:
    return nen or os.path.join(goc, THU_MUC_NEN)


def _doc_nho(nen: str) -> Dict[str, str]:
    try:
        with open(os.path.join(nen, "da-bao.json"), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _tinh_canh_bao(goc: str, nen: Optional[str], bay_gio: Optional[_dt.datetime]):
    bg = bay_gio or _dt.datetime.now()
    nho, moi, dong = _doc_nho(_nen(goc, nen)), {}, []
    for kenh in cac_kenh(goc):
        r = du_bao(goc, kenh, bg)
        tt = r["trang_thai"]
        if tt in ("gan", "dat") and nho.get(kenh) != tt and not (tt == "gan" and nho.get(kenh) == "dat"):
            muc = "khan" if tt == "dat" else "thuong"
            dong.append("- [{0}] **{1}** · kênh {2} — {3}".format(bg.strftime("%Y-%m-%d %H:%M"), muc, kenh, _van_ban(r)))
            moi[kenh] = tt
    return dong, {**nho, **moi}


def canh_bao(goc: str, nen: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Dòng cảnh báo cho kênh MỚI "gan"/"dat" (chưa báo mức đó). Thuần đọc — chỉ ghi_canh_bao mới ghi trạng thái."""
    return _tinh_canh_bao(goc, nen, bay_gio)[0]


def ghi_canh_bao(goc: str, nen: Optional[str] = None, tep: Optional[str] = None,
                 bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Nối dòng cảnh báo vào cuối workspace/loi-chay-max.md (không viết lại), rồi ghi trạng thái đã báo."""
    dong, nho = _tinh_canh_bao(goc, nen, bay_gio)
    if not dong:
        return []
    duong = tep or os.path.join(goc, TEP_CANH_BAO)
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    dau = ""
    if os.path.isfile(duong) and os.path.getsize(duong):
        with open(duong, "rb") as f:
            f.seek(-1, os.SEEK_END)
            dau = "" if f.read(1) == b"\n" else "\n"
    with open(duong, "a", encoding="utf-8", newline="\n") as f:
        f.write(dau + "\n".join(dong) + "\n")
    thu_muc = _nen(goc, nen)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "da-bao.json"), "w", encoding="utf-8") as f:
        json.dump(nho, f, ensure_ascii=False, indent=1)
    return dong


def _goc_mac_dinh() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="core.ypp", description="Đường tới kiếm tiền (YPP)")
    ap.add_argument("--goc", default=_goc_mac_dinh())
    ap.add_argument("--canh-bao", action="store_true", help="ghi cảnh báo vào workspace/loi-chay-max.md")
    a = ap.parse_args(argv)
    if a.canh_bao:
        ds = ghi_canh_bao(a.goc)
        print("\n".join(ds) if ds else "không có cảnh báo mới")
        return 0
    print("{0:<14} {1:>8} {2:>6} {3:>8} {4:>7} {5:>8} {6:>8}  {7:<10} {8}".format(
        "kênh", "giờ/4000", "đăng", "giờ/ngày", "đk/ngày", "ngày-giờ", "ngày-đk", "trạng thái", "dự kiến"))
    for k in cac_kenh(a.goc):
        r = du_bao(a.goc, k)

        def f(v, m="{0:.0f}"):
            return "-" if v is None else m.format(v)
        print("{0:<14} {1:>8} {2:>6} {3:>8} {4:>7} {5:>8} {6:>8}  {7:<10} {8}".format(
            k, f(r["gio"], "{0:.1f}"), f(r["dang_ky"]), "{0:.2f}".format(r["toc_gio"]), "{0:.2f}".format(r["toc_dk"]),
            f(r["ngay_gio"]), f(r["ngay_dk"]), r["trang_thai"], r["ngay_du_kien"] or "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
