"""Dòng lệnh não bộ phận — xem `core/nao_bo_phan/__init__.py`."""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

from ._chung import BO_PHAN, DA_HET, DANG, GOC, TAI_PHAT, TAM_LANG, doc_chu, duong_vault


def in_tom_tat(tk: Dict[str, Any]) -> List[str]:
    """Tóm tắt một lượt gom: mỗi bộ phận một dòng (sự kiện mới theo loại · nơ-ron lỗi theo trạng thái · bài học)."""
    d = ["GOM NÃO BỘ PHẬN — {0} giây · ghi {1} tệp · chỉ mục {2}".format(
        tk.get("giay"), tk.get("ghi_tep", 0), tk.get("chi_muc") or {})]
    for bp, ten in BO_PHAN.items():
        them = tk.get("them", {}).get(bp) or {}
        nr = tk.get("no_ron", {}).get(bp) or {}
        d.append("  {0:<16} +{1:<5} ({2}) · lỗi: {3} đang, {4} tái phát, {5} lặng, {6} hết · {7} bài học".format(
            bp, sum(them.values()), ", ".join("{0} {1}".format(k, v) for k, v in sorted(them.items())) or "-",
            nr.get(DANG, 0), nr.get(TAI_PHAT, 0), nr.get(TAM_LANG, 0), nr.get(DA_HET, 0), nr.get("bai_hoc", 0)))
    d.append("  nguồn: " + (" · ".join("{0} +{1}".format(k, v) for k, v in sorted((tk.get("them_nguon") or {}).items()))
                            or "(không có sự kiện mới)"))
    d.append("  tệp đã xét: " +" · ".join("{0} {1}".format(k, v) for k, v in sorted((tk.get("tep") or {}).items())))
    cb = dict(tk.get("canh_bao") or {})
    if tk.get("canh_bao_bai_hoc"):
        cb["bai-hoc"] = tk["canh_bao_bai_hoc"]
    if cb:
        d.append("  CẢNH BÁO (tệp/dòng đọc hỏng, đã bỏ qua): " + " · ".join("{0} {1}".format(k, v)
                                                                          for k, v in sorted(cb.items())))
    return d


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.nao_bo_phan", description="Não bộ phận (đợt 1, không LLM).")
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
    s.add_parser("dung-lai-chi-muc", help="dựng lại chỉ mục SQLite từ vault markdown")
    a = p.parse_args(argv)
    ra = a.ra or a.goc
    if a.lenh == "gom":
        from .bo_gom import gom  # noqa: PLC0415

        print("\n".join(in_tom_tat(gom(a.goc, ra))))
    elif a.lenh == "xem":
        from .truy_xuat import dong_loi, loi_dang_tang  # noqa: PLC0415

        if a.bo_phan:
            print(doc_chu(os.path.join(duong_vault(ra), a.bo_phan, "so-tay.md")) or "(chưa có sổ tay — chạy `gom`)")
        else:
            ds = loi_dang_tang(ra, 10)
            print("NÃO BỘ PHẬN — lỗi đang tăng (đang xảy ra / tái phát, theo số lần 7 ngày)")
            print("\n".join("  " + dong_loi(x, 160) for x in ds) or "  (không có — hoặc chưa chạy `gom`)")
    elif a.lenh == "nho":
        from .truy_xuat import nho  # noqa: PLC0415

        t0 = time.perf_counter()
        ds = nho(ra, a.bo_phan, a.ngu_canh, a.k)
        print("{0} nơ-ron · {1:.1f} ms".format(len(ds), (time.perf_counter() - t0) * 1000))
        for x in ds:
            print("  {0:.4f} [{1}/{2}] {3}\n         {4}".format(x["diem"], x["loai"], x["trang_thai"], x["cau"][:150],
                                                              x["duong"]))
    else:
        from .no_ron import dung_lai_chi_muc  # noqa: PLC0415

        print("đã dựng lại chỉ mục:", dung_lai_chi_muc(ra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
