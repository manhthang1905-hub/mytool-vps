"""Dòng lệnh não bộ phận — xem `core/nao_bo_phan/__init__.py`."""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

from ._chung import BO_PHAN, BO_PHAN_TOI_DA_DEM, DA_HET, DANG, GOC, TAI_PHAT, TAM_LANG, doc_chu, duong_vault


def in_tom_tat(tk: Dict[str, Any]) -> List[str]:
    """Tóm tắt một lượt gom: mỗi bộ phận một dòng (sự kiện mới theo loại · nơ-ron lỗi theo trạng thái · bài học)."""
    d = ["GOM NÃO BỘ PHẬN — {0} giây · ghi {1} tệp · chỉ mục {2}{3}".format(
        tk.get("giay"), tk.get("ghi_tep", 0), tk.get("chi_muc") or {},
        " · ký lại {0}".format(tk["ky_lai"]) if tk.get("ky_lai") else "")]
    for bp, ten in BO_PHAN.items():
        them = tk.get("them", {}).get(bp) or {}
        nr = tk.get("no_ron", {}).get(bp) or {}
        d.append("  {0:<16} +{1:<5} ({2}) · lỗi: {3} đang, {4} tái phát, {5} lặng, {6} hết · {7} cảnh báo · "
                 "{8} bài học".format(
                     bp, sum(them.values()), ", ".join("{0} {1}".format(k, v) for k, v in sorted(them.items())) or "-",
                     nr.get(DANG, 0), nr.get(TAI_PHAT, 0), nr.get(TAM_LANG, 0), nr.get(DA_HET, 0),
                     nr.get("canh_bao", 0), nr.get("bai_hoc", 0)))
    d.append("  nguồn: " + (" · ".join("{0} +{1}".format(k, v) for k, v in sorted((tk.get("them_nguon") or {}).items()))
                            or "(không có sự kiện mới)"))
    d.append("  tệp đã xét: " + " · ".join("{0} {1}".format(k, v) for k, v in sorted((tk.get("tep") or {}).items())))
    cb = dict(tk.get("canh_bao") or {})
    if tk.get("canh_bao_bai_hoc"):
        cb["bai-hoc"] = tk["canh_bao_bai_hoc"]
    if cb:
        d.append("  CẢNH BÁO (tệp/dòng đọc hỏng, đã bỏ qua): " + " · ".join("{0} {1}".format(k, v)
                                                                          for k, v in sorted(cb.items())))
    return d


def in_ngu(kq: Dict[str, Any]) -> List[str]:
    """Tóm tắt một đêm ngủ: mỗi bộ phận một khối (bảng số, lệnh đề xuất / áp / bỏ + lý do, bài chạm tới)."""
    d = ["NGỦ NÃO BỘ PHẬN — {0} giây · {1} bộ phận{2}".format(kq.get("giay"), len(kq.get("bo_phan") or []),
                                                          " · BỎ QUA: " + kq["bo_qua"] if kq.get("bo_qua") else "")]
    for x in kq.get("bo_phan") or []:
        if x.get("loi"):
            d.append("  {0}: HỎNG ({1} sự kiện mới, mốc không dời — đêm sau ngủ lại): {2}".format(
                x["bo_phan"], x.get("su_kien_moi"), x["loi"]))
            continue
        d.append("  {0}: {1} sự kiện mới · bảng số {2} ký tự · lời nhắc {3} ký tự · {4} giây · token {5}/{6} · "
                 "lệnh {7}: áp {8}, bỏ {9}".format(x["bo_phan"], x["su_kien_moi"], x["ky_tu_to_so"],
                                                   x["ky_tu_loi_nhac"], x["giay"], x["token_vao"], x["token_ra"],
                                                   x["de_xuat"], len(x["ap"]), len(x["bo"])))
        d += ["    áp {0} {1}".format(l["lenh"], l.get("id", "")) for l in x["ap"]]
        d += ["    bỏ {0}: {1}".format(l.get("lenh") if isinstance(l, dict) else "?", ly) for l, ly in x["bo"]]
        d += ["    · [{0} α{1:g} β{2:g}{3}] {4}".format(b["trang_thai"], float(b["alpha"] or 1), float(b["beta"] or 1),
                                                     " · vào lời nhắc" if b.get("vao_loi_nhac") else "", b["cau"])
              for b in x.get("bai") or []]
    if kq.get("soat"):
        d.append("  soát tuần: " + " · ".join("{0} {1}".format(k, v) for k, v in sorted(kq["soat"].items())))
    return d


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.nao_bo_phan", description="Não bộ phận (đợt 2).")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or GOC, help="gốc tool để ĐỌC dữ liệu")
    p.add_argument("--ra", default="", help="gốc để GHI nao/bo-phan.db + vault (mặc định = --goc)")
    s = p.add_subparsers(dest="lenh", required=True)
    s.add_parser("gom", help="gom sự kiện + dựng nơ-ron, sổ tay, chỉ mục")
    x = s.add_parser("xem", help="lỗi đang tăng mọi bộ phận / sổ tay một bộ phận")
    x.add_argument("--bo-phan", default="", choices=[""] + list(BO_PHAN))
    n = s.add_parser("nho", help="truy xuất nơ-ron cho một ngữ cảnh")
    n.add_argument("--bo-phan", required=True, choices=list(BO_PHAN))
    n.add_argument("-k", type=int, default=5)
    n.add_argument("ngu_canh")
    g = s.add_parser("ngu", help="giấc ngủ đêm: bảng số → Claude Max → lệnh sửa sổ bài học (đã kiểm) + soát tuần")
    g.add_argument("--bo-phan", action="append", default=[], choices=list(BO_PHAN), help="chỉ bộ phận này (lặp được)")
    g.add_argument("--toi-da", type=int, default=BO_PHAN_TOI_DA_DEM, help="trần số bộ phận (= số lượt gọi LLM)")
    g.add_argument("--soat", action="store_true", help="soát tuần ngay (mặc định: Chủ nhật)")
    s.add_parser("ky-lai", help="tính lại chữ ký mọi sự kiện theo luật hiện hành rồi dựng lại vault")
    s.add_parser("dung-lai-chi-muc", help="dựng lại chỉ mục SQLite từ vault markdown")
    a = p.parse_args(argv)
    ra = a.ra or a.goc
    if a.lenh == "gom":
        from .bo_gom import gom  # noqa: PLC0415

        print("\n".join(in_tom_tat(gom(a.goc, ra))))
    elif a.lenh == "xem":
        from .truy_xuat import dong_bo_phan, dong_loi, loi_dang_tang  # noqa: PLC0415

        if a.bo_phan:
            print(doc_chu(os.path.join(duong_vault(ra), a.bo_phan, "so-tay.md")) or "(chưa có sổ tay — chạy `gom`)")
        else:
            ds = loi_dang_tang(ra, 10)
            print("NÃO BỘ PHẬN — lỗi đang tăng (sự cố khác nhau 48h so với 5 ngày trước; cảnh báo không tính)")
            print("\n".join("  " + dong_loi(x, 160) for x in ds) or "  (không có — hoặc chưa chạy `gom`)")
            print("\n".join(dong_bo_phan(ra)))
    elif a.lenh == "nho":
        from .truy_xuat import nho  # noqa: PLC0415

        t0 = time.perf_counter()
        ds = nho(ra, a.bo_phan, a.ngu_canh, a.k)
        print("{0} nơ-ron · {1:.1f} ms".format(len(ds), (time.perf_counter() - t0) * 1000))
        for x in ds:
            print("  {0:.4f} [{1}/{2}] {3}\n         {4}".format(x["diem"], x["loai"], x["trang_thai"], x["cau"][:150],
                                                              x["duong"]))
    elif a.lenh == "ngu":
        from .ngu import ngu  # noqa: PLC0415

        print("\n".join(in_ngu(ngu(a.goc, ra, chi=a.bo_phan, toi_da=a.toi_da, soat_tuan=True if a.soat else None))))
    elif a.lenh == "ky-lai":
        from . import kho, no_ron  # noqa: PLC0415
        from ._chung import cac_kenh  # noqa: PLC0415
        from .bo_gom import ky_lai  # noqa: PLC0415

        con = kho.mo(ra, cho=5.0)
        try:
            print("ký lại:", ky_lai(con, cac_kenh(a.goc)))
            no_ron.dung_vault(con, a.goc, ra, time.time())
        finally:
            con.close()
    else:
        from .no_ron import dung_lai_chi_muc  # noqa: PLC0415

        print("đã dựng lại chỉ mục:", dung_lai_chi_muc(ra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
