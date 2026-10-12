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
    p.add_argument("--danh-gia", action="store_true", help="chỉ tính lại bảng xếp hạng (+ luật quyết)")
    p.add_argument("--so-sanh-cu", action="store_true", help="--danh-gia: tính thêm tầng 1 cách đo đợt 1 để so")
    p.add_argument("--bao-cao", action="store_true", help="--danh-gia: ghi báo cáo đợt 2 vào workspace/chan-doan/")
    p.add_argument("--khe", action="store_true", help="in chia khe (Thompson phân tầng) cho một khe + tỉ phần dự kiến "
                                                      "(không áp)")
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
        b = danh_gia.chay(a.goc, kenh_ds=kenh_ds, log=print, so_sanh_cu=a.so_sanh_cu)
        for gt, o in sorted(((b.get("tang2") or {}).get("chung") or {}).items()):
            print("{0:<15} n={1:<3} điểm={2:<5} TB={3} CI90={4} P(tốt nhất)={5}".format(
                gt, o.get("n"), o.get("diem"), o.get("tb"), o.get("ci90"), o.get("p_tot_nhat")))
        if a.bao_cao:
            from . import bao_cao  # noqa: PLC0415

            print("Báo cáo:", bao_cao.ghi_dot_2(a.goc, b, kenh_ds=kenh_ds))
    if a.khe:
        from . import chia_khe  # noqa: PLC0415
        from ._chung import hom_nay  # noqa: PLC0415

        b = danh_gia.doc_bang(a.goc)
        for k in kenh_ds:
            tt = chia_khe.tom_tat_kenh(a.goc, k, ngay=hom_nay(), bang=b)
            r = chia_khe.rut_vi_du(a.goc, k, ngay=hom_nay(), bang=b)
            print(json.dumps({"kenh": k, "bat": tt["bat"], "vi_sao": tt["vi_sao"], "khe_vi_du": r.get("gia_thuyet"),
                              "cach": r.get("cach"), "rut": r.get("rut"), "thu_tu": r.get("thu_tu"),
                              "ti_le_khe": tt["ti_le_khe"], "chan": tt["chan"]}, ensure_ascii=False))
    if not (a.ngay or a.nguoc or a.danh_gia or a.khe):
        p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
