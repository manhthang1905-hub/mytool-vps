"""ĐƯỜNG TỚI KIẾM TIỀN (YouTube Partner Program) — dự báo từ chỉ số Studio đã chụp hằng ngày.

Đọc CHANNEL/<k>/chi-so/kenh-theo-ngay.csv (cột: Lúc chụp, Lượt xem, Giờ xem, Đăng ký, Lượt hiển thị, Tỷ lệ bấm).
Mỗi dòng là tổng của CỬA SỔ 28 NGÀY trượt ở lúc chụp (Đăng ký = người đăng ký mới trong cửa sổ ≈ tổng với kênh trẻ).

Dùng:  python -m core.ypp              bảng mọi kênh (kênh khai trong vm/cai-dat-tool.json)
       python -m core.ypp --canh-bao   ghi cảnh báo kênh vừa "gần"/"đạt" vào workspace/loi-chay-max.md (chỉ nối thêm)

LƯU Ý QUAN TRỌNG: YPP đòi 4.000 giờ xem CÔNG KHAI trong 365 ngày (hoặc 3 triệu lượt Shorts/90 ngày) và 1.000 đăng ký.
Tổng 28 ngày TRƯỢT là CẬN DƯỚI và tự tụt khi ngày nổ cũ rời cửa sổ (đọc thành "đang giảm" — sai). 12/10/2026: có số
Studio cấp kênh (`core.chi_so_kenh`) thì dùng số TRỌN ĐỜI: sub = thẻ thời gian thực (sub hiện có, tốc độ = hiệu hai số
trọn đời), giờ xem = cộng CHUỖI NGÀY đã chụp (≤ 365 ngày; Studio tính cả video riêng tư/đã xoá — vẫn là ước). Không có
thì lùi về 28 ngày và nhãn ghi rõ "28 ngày trượt" (`nhan_sub`, `nhan_gio`). Studio mới là nguồn quyết định cuối.
Tốc độ 28 ngày = trung vị của ≤7 chênh lệch/ngày gần nhất (bỏ chênh âm và ngoại lai >5× trung vị).
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


def _so_tron_doi(goc: str, kenh: str) -> dict:
    """Sub TRỌN ĐỜI (thẻ thời gian thực Studio) + tốc độ thật (hiệu hai số trọn đời) + giờ xem từ CHUỖI NGÀY đã chụp
    (`core.chi_so_kenh`). Hỏng/không có → các số None (người đọc phải thấy "chưa rõ", không đoán)."""
    ra = {"sub_tron_doi": None, "sub_tron_doi_ngay": "", "toc_dk_tron_doi": None, "gio_365": None,
          "gio_365_tu": "", "toc_gio_ngay": None}
    try:
        from . import chi_so_kenh  # noqa: PLC0415

        s = chi_so_kenh.sub_tron_doi(goc, kenh)
        ra["sub_tron_doi"], ra["sub_tron_doi_ngay"] = s.get("so"), s.get("ngay") or ""
        if s.get("so") is not None:
            ra["toc_dk_tron_doi"] = chi_so_kenh.toc_do_sub(chi_so_kenh.chuoi_sub_tron_doi(goc, kenh))
        g = chi_so_kenh.gio_xem(goc, kenh)
        ra["gio_365"], ra["gio_365_tu"], ra["toc_gio_ngay"] = g.get("gio_365"), g.get("tu") or "", g.get("toc_7")
    except Exception:  # noqa: BLE001
        pass
    return ra


def du_bao(goc: str, kenh: str, bay_gio: Optional[_dt.datetime] = None) -> dict:
    """Dự báo YPP một kênh. Khoá: kenh, so_mau, gio, dang_ky, toc_gio, toc_dk, ngay_gio, ngay_dk, ngay_toi, ngay_du_kien, trang_thai.
    trang_thai: dat | gan (≤14 ngày) | dang_len | cham (không tăng) | chua_du_so (<3 lần chụp).

    12/10/2026 — PHÂN BIỆT TRƯỢT/TRỌN ĐỜI: `dang_ky_28`/`gio_28` = tổng cửa sổ 28 ngày trượt (kenh-theo-ngay.csv);
    `sub_tron_doi` = sub TRỌN ĐỜI Studio (thẻ thời gian thực) — có thì `dang_ky` = số trọn đời (`nguon_sub`
    "tron_doi") và tốc độ = hiệu hai số trọn đời; `gio_365` = giờ xem cộng từ chuỗi ngày đã chụp (≤ 365 ngày) — lớn
    hơn tổng 28 ngày thì `gio` dùng số này (`nguon_gio` "chuoi_ngay"), tốc độ = giờ/ngày 7 ngày chốt gần nhất.
    `truot_giam` = tổng 28 ngày vừa GIẢM so lần chụp trước (ngày cũ rời cửa sổ — KHÔNG phải mất sub/giờ xem)."""
    chup = _doc_chup(goc, kenh)
    r = {"kenh": kenh, "so_mau": len(chup), "gio": None, "dang_ky": None, "toc_gio": 0.0, "toc_dk": 0.0,
         "ngay_gio": None, "ngay_dk": None, "ngay_toi": None, "ngay_du_kien": None, "trang_thai": "chua_du_so",
         "dang_ky_28": None, "gio_28": None, "nguon_sub": "28_ngay", "nguon_gio": "28_ngay", "truot_giam": False}
    if chup:
        r["gio"], r["dang_ky"] = chup[-1]["gio"], int(chup[-1]["dk"])
        r["gio_28"], r["dang_ky_28"] = r["gio"], r["dang_ky"]
    if len(chup) >= 2:
        r["truot_giam"] = chup[-1]["gio"] < chup[-2]["gio"] or chup[-1]["dk"] < chup[-2]["dk"]
    td = _so_tron_doi(goc, kenh)
    r.update(td)
    if td["sub_tron_doi"] is not None:
        r["dang_ky"], r["nguon_sub"] = int(td["sub_tron_doi"]), "tron_doi"
    if td["gio_365"] is not None and (r["gio"] is None or td["gio_365"] > r["gio"]):
        r["gio"], r["nguon_gio"] = float(td["gio_365"]), "chuoi_ngay"
    if len(chup) < TOI_THIEU_MAU and r["nguon_sub"] != "tron_doi":
        return r
    if len(chup) >= TOI_THIEU_MAU:
        r["toc_gio"], r["toc_dk"] = _toc_do(chup, "gio"), _toc_do(chup, "dk")
    if r["nguon_sub"] == "tron_doi" and td["toc_dk_tron_doi"] is not None:
        r["toc_dk"] = float(td["toc_dk_tron_doi"])
    if td["toc_gio_ngay"] is not None:
        # YPP đếm 365 ngày: giờ xem CỘNG THÊM mỗi ngày = giờ xem/ngày thật (chuỗi ngày), không phải hiệu hai tổng
        # 28 ngày trượt (hiệu đó trừ luôn ngày rời cửa sổ).
        r["toc_gio"] = float(td["toc_gio_ngay"])
    if r["gio"] is None or r["dang_ky"] is None:
        return r
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
    """Kênh máy này quản lý — BỎ kênh đã trả kho (20/10/2026: kênh trả kho không tính ở đâu cả)."""
    from .kenh import bo_kenh_tra_kho  # noqa: PLC0415

    try:
        with open(os.path.join(goc, "vm", "cai-dat-tool.json"), "r", encoding="utf-8") as tep:
            ds = sorted(((json.load(tep) or {}).get("kenh") or {}).keys())
        if ds:
            return bo_kenh_tra_kho(goc, ds)
    except (OSError, ValueError):
        pass
    try:
        return bo_kenh_tra_kho(goc, sorted(x for x in os.listdir(os.path.join(goc, "CHANNEL"))
                                           if os.path.isfile(os.path.join(goc, "CHANNEL", x, "chi-so", "kenh-theo-ngay.csv"))))
    except OSError:
        return []


def nhan_sub(r: dict) -> str:
    """"713 sub trọn đời" | "605 sub mới trong 28 ngày (trọn đời: chưa rõ)" — nhãn RÕ nguồn số."""
    if r.get("nguon_sub") == "tron_doi":
        return "{0} sub trọn đời".format(r.get("dang_ky"))
    return "{0} sub mới trong 28 ngày trượt (trọn đời: chưa rõ)".format(r.get("dang_ky"))


def nhan_gio(r: dict) -> str:
    """"7.455 giờ xem (cộng chuỗi ngày từ 31/07)" | "1.973 giờ xem 28 ngày trượt (cận dưới của 365 ngày)"."""
    try:
        g = "{0:,.0f}".format(float(r.get("gio"))).replace(",", ".")
    except (TypeError, ValueError):
        g = "?"
    if r.get("nguon_gio") == "chuoi_ngay":
        tu = str(r.get("gio_365_tu") or "")
        return "{0} giờ xem ≤ 365 ngày (cộng chuỗi ngày Studio từ {1})".format(g, tu[8:10] + "/" + tu[5:7] if tu else "?")
    return "{0} giờ xem 28 ngày trượt (cận dưới của 365 ngày)".format(g)


def _van_ban(r: dict) -> str:
    if r["trang_thai"] == "dat":
        return "ĐÃ ĐỦ điều kiện YPP ({0}, {1}) — vào Studio → Kiếm tiền để nộp đơn.".format(nhan_gio(r), nhan_sub(r))
    return "sắp đủ điều kiện YPP: {0}/4000, {1}/1000, dự kiến ~{2} (còn ~{3:.0f} ngày).".format(
        nhan_gio(r), nhan_sub(r), r["ngay_du_kien"], r["ngay_toi"])


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
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(prog="core.ypp", description="Đường tới kiếm tiền (YPP)")
    ap.add_argument("--goc", default=_goc_mac_dinh())
    ap.add_argument("--canh-bao", action="store_true", help="ghi cảnh báo vào workspace/loi-chay-max.md")
    a = ap.parse_args(argv)
    if a.canh_bao:
        ds = ghi_canh_bao(a.goc)
        print("\n".join(ds) if ds else "không có cảnh báo mới")
        return 0
    print("{0:<14} {1:>8} {2:>6} {3:>8} {4:>7} {5:>8} {6:>8}  {7:<10} {8:<11} {9}".format(
        "kênh", "giờ/4000", "đăng", "giờ/ngày", "đk/ngày", "ngày-giờ", "ngày-đk", "trạng thái", "dự kiến", "nguồn số"))
    for k in cac_kenh(a.goc):
        r = du_bao(a.goc, k)

        def f(v, m="{0:.0f}"):
            return "-" if v is None else m.format(v)
        print("{0:<14} {1:>8} {2:>6} {3:>8} {4:>7} {5:>8} {6:>8}  {7:<10} {8:<11} {9}".format(
            k, f(r["gio"], "{0:.1f}"), f(r["dang_ky"]), "{0:.2f}".format(r["toc_gio"]), "{0:.2f}".format(r["toc_dk"]),
            f(r["ngay_gio"]), f(r["ngay_dk"]), r["trang_thai"], r["ngay_du_kien"] or "-",
            "sub {0}, giờ {1} (28 ngày: {2} giờ, {3} sub)".format(
                "trọn đời" if r.get("nguon_sub") == "tron_doi" else "28 ngày",
                "chuỗi ngày" if r.get("nguon_gio") == "chuoi_ngay" else "28 ngày", f(r.get("gio_28")),
                f(r.get("dang_ky_28")))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
