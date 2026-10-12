"""Dòng lệnh phòng thí nghiệm — xem `core/phong_thi_nghiem/__init__.py`."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.phong_thi_nghiem", description="Phòng thí nghiệm chọn content.")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    p.add_argument("--kenh", action="append", default=[])
    p.add_argument("--ngay", action="store_true", help="lượt hằng ngày (mọi kênh hoặc --kenh)")
    p.add_argument("--ai", action="store_true", help="cho phép H-AI gọi AI qua ví (mặc định KHÔNG)")
    p.add_argument("--nguoc", action="store_true", help="chạy ngược lịch sử + báo cáo")
    p.add_argument("--tu", default="")
    p.add_argument("--den", default="")
    p.add_argument("--danh-gia", action="store_true", help="chỉ tính lại bảng xếp hạng")
    p.add_argument("--khe", action="store_true", help="in giả thuyết khung Thompson chọn cho một khe (không áp)")
    p.add_argument("--ghi-vao", default="", help="gốc RIÊNG để ghi dữ liệu phòng thí nghiệm (chạy thử; đọc vẫn từ --goc)")
    a = p.parse_args(argv)
    if a.ghi_vao:
        from ._chung import BIEN_GOC_GHI  # noqa: PLC0415

        os.environ[BIEN_GOC_GHI] = os.path.abspath(a.ghi_vao)
    from . import danh_gia  # noqa: PLC0415

    kenh_ds = a.kenh or danh_gia.kenh_phong_thi_nghiem(a.goc)
    if a.ngay:
        from .chay import chay_ngay_an_toan  # noqa: PLC0415

        for k in kenh_ds:
            r = chay_ngay_an_toan(a.goc, k, dung_ai=a.ai, log=print, danh_gia_lai=False)
            print(json.dumps({x: r.get(x) for x in ("kenh", "ngay", "n_vu_tru", "ghi", "gia_thuyet", "bo_qua", "loi")
                              if r.get(x) is not None}, ensure_ascii=False))
        danh_gia.chay(a.goc, kenh_ds=kenh_ds, log=print)
    if a.nguoc:
        from .chay import chay_nguoc  # noqa: PLC0415

        r = chay_nguoc(a.goc, kenh_ds, tu=a.tu, den=a.den, log=print)
        print("Báo cáo:", r.get("bao_cao"))
    if a.danh_gia and not (a.ngay or a.nguoc):
        b = danh_gia.chay(a.goc, kenh_ds=kenh_ds, log=print)
        for gt, o in sorted(((b.get("tang2") or {}).get("chung") or {}).items()):
            print("{0:<15} n={1:<3} điểm={2:<5} TB={3} CI90={4} P(tốt nhất)={5}".format(
                gt, o.get("n"), o.get("diem"), o.get("tb"), o.get("ci90"), o.get("p_tot_nhat")))
    if a.khe:
        for k in kenh_ds:
            r = danh_gia.chon_gia_thuyet_cho_khe(a.goc, k)
            print(k, r.get("gia_thuyet"), r.get("cach"), r.get("ly_do"))
    if not (a.ngay or a.nguoc or a.danh_gia or a.khe):
        p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
