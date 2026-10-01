"""CLI giám đốc kênh.

    python -m core.giam_doc --kenh TL3-T7 --thu          in bảng số / quan sát / đề xuất — 0 đồng, không ghi
    python -m core.giam_doc --kenh TL3-T7 --llm          như --thu + MỘT lượt LLM thật (qua ví) — vẫn không ghi
    python -m core.giam_doc --kenh TL3-T7 --llm --tuan   lượt tuần
    python -m core.giam_doc --chay                       lượt thật cho mọi kênh đến hạn (do `nhip` sinh ra)
    python -m core.giam_doc --nhip                       xem kênh nào đến hạn (không sinh tiến trình)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    """Điểm vào dòng lệnh."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="python -m core.giam_doc", description="Giám đốc kênh")
    p.add_argument("--kenh", action="append", default=[], help="mã kênh (lặp được, hoặc 'A,B')")
    p.add_argument("--thu", action="store_true", help="chỉ tính và in — không LLM, không ghi")
    p.add_argument("--llm", action="store_true", help="gọi LLM thật một lượt — không ghi")
    p.add_argument("--tuan", action="store_true", help="lượt tuần")
    p.add_argument("--chay", action="store_true", help="lượt thật cho các kênh đến hạn")
    p.add_argument("--nhip", action="store_true", help="xem kênh nào đến hạn")
    p.add_argument("--ra", default="", help="ghi bản in vào tệp này (thay vì chỉ in ra màn hình)")
    a = p.parse_args(argv)
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from . import bao_cao, chay_het, chay_kenh, nhip, quan_ly  # noqa: PLC0415

    if a.nhip:
        print(nhip(goc, thu=True))
        return 0
    if a.chay:
        kq = chay_het(goc, ghi=print)
        print("giám đốc: đã chạy {0} kênh".format(len(kq)))
        return 0
    kenh = [k.strip() for x in a.kenh for k in x.split(",") if k.strip()]
    if not kenh or not (a.thu or a.llm):
        p.error("cần --kenh và --thu hoặc --llm")
    ra: List[str] = []
    for ma in kenh:
        goi = quan_ly.goi_chat_that(goc, print) if a.llm else None
        if a.llm and goi is None:
            print("{0}: van ví đang chặn — không gọi LLM".format(ma))
        kq = chay_kenh(goc, ma, che_do="thu", goi_chat=goi, tuan=a.tuan)
        ra.append(bao_cao.in_ket_qua(kq, ca_loi_nhac=a.llm))
    chu = "\n".join(ra)
    if a.ra:
        os.makedirs(os.path.dirname(os.path.abspath(a.ra)), exist_ok=True)
        with open(a.ra, "w", encoding="utf-8") as tep:
            tep.write(chu)
        print("đã ghi {0} ({1} ký tự)".format(a.ra, len(chu)))
    else:
        print(chu)
    return 0


if __name__ == "__main__":
    sys.exit(main())
