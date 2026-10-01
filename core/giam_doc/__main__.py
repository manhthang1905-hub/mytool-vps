"""CLI giám đốc kênh.

    python -m core.giam_doc --kenh TL3-T7 --thu          in bảng số / quan sát / đề xuất — 0 đồng, không ghi
    python -m core.giam_doc --kenh TL3-T7 --llm          như --thu + MỘT lượt LLM thật (qua ví) — vẫn không ghi
    python -m core.giam_doc --kenh TL3-T7 --llm --tuan   lượt tuần
    python -m core.giam_doc --chay                       lượt thật cho mọi kênh đến hạn (do `nhip` sinh ra)
    python -m core.giam_doc --nhip                       xem kênh nào đến hạn (không sinh tiến trình)
    python -m core.giam_doc --kham <vid>                 hồ sơ + lời nhắc khám nghiệm một video — 0 đồng, không ghi
    python -m core.giam_doc --kham <vid> --llm           khám thật (1 lượt LLM) và GHI bản khám + bài học
    python -m core.giam_doc --tong --thu | --llm         họp tổng giám đốc: bảng công ty + thực đơn khe (không ghi)
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
    p.add_argument("--kham", action="append", default=[], help="khám nghiệm video (mã YouTube, lặp được)")
    p.add_argument("--tong", action="store_true", help="tổng giám đốc (cần --thu hoặc --llm)")
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
    if a.kham:
        return _ra(a.ra, "\n\n".join(_kham(goc, vid, kenh, a.llm) for x in a.kham for vid in x.split(",") if vid.strip()))
    if a.tong:
        from . import tong  # noqa: PLC0415

        if not (a.thu or a.llm):
            p.error("--tong cần --thu hoặc --llm")
        kq = tong.hop_tuan(goc, quan_ly.goi_chat_that(goc, print) if a.llm else None, thu=True, ghi=print)
        return _ra(a.ra, tong.chu_bao_cao(kq) + "\n\n=== LỜI NHẮC ===\n" + kq["loi_nhac"])
    if not kenh or not (a.thu or a.llm):
        p.error("cần --kenh và --thu hoặc --llm")
    ra: List[str] = []
    for ma in kenh:
        goi = quan_ly.goi_chat_that(goc, print) if a.llm else None
        if a.llm and goi is None:
            print("{0}: van ví đang chặn — không gọi LLM".format(ma))
        kq = chay_kenh(goc, ma, che_do="thu", goi_chat=goi, tuan=a.tuan)
        ra.append(bao_cao.in_ket_qua(kq, ca_loi_nhac=a.llm))
    return _ra(a.ra, "\n".join(ra))


def _ra(duong: str, chu: str) -> int:
    if duong:
        os.makedirs(os.path.dirname(os.path.abspath(duong)), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as tep:
            tep.write(chu)
        print("đã ghi {0} ({1} ký tự)".format(duong, len(chu)))
    else:
        print(chu)
    return 0


def _kham(goc: str, vid: str, kenh: List[str], llm: bool) -> str:
    """Khám một video theo lệnh của chủ: mốc muộn nhất có bản chụp (không có thì bản chụp mới nhất)."""
    import glob  # noqa: PLC0415
    import json  # noqa: PLC0415

    from . import kham_nghiem as kn, quan_ly  # noqa: PLC0415
    from .du_lieu import moi_nhat, tom_tat  # noqa: PLC0415

    vid = vid.strip()
    ma = next((k for k in kenh if os.path.isdir(os.path.join(goc, "CHANNEL", k, "chi-so", vid))), "") or next(
        (os.path.basename(os.path.dirname(os.path.dirname(d)))
         for d in glob.glob(os.path.join(goc, "CHANNEL", "*", "chi-so", vid))), "")
    if not ma:
        return "{0}: không thấy chi-so của video ở kênh nào".format(vid)
    bs = tom_tat(goc, ma)
    v = bs.video_theo_id(vid)
    if v is None or not v.get("chup"):
        return "{0}/{1}: video chưa có bản chụp số".format(ma, vid)
    m = kn.moc_cua(v)
    moc, b = m if m else ("7d" if (v.get("tuoi_gio") or 0) >= 144 else "48h", moi_nhat(v))
    if not llm:
        hs = kn.ho_so_kham(goc, ma, bs, v, moc, ban_chup=b)
        return "=== KHÁM {0}/{1} @{2} (bản chụp {3}) — THỬ, không gọi AI ===\n{4}".format(
            ma, vid, moc, hs["ban_chup"], kn.loi_nhac(hs, bs.muc_tieu, ma))
    goi = quan_ly.goi_chat_that(goc, print)
    if goi is None:
        return "{0}: van ví đang chặn — không gọi LLM".format(vid)
    if moc == "7d":
        try:
            kn.binh_luan_that(goc, ma, vid, str(bs.cai.get("ngon_ngu") or ""))
        except Exception as loi:  # noqa: BLE001
            print("  không lấy được bình luận: {0}".format(loi))
    ban = kn.kham_mot(goc, ma, bs, v, moc, goi, ban_chup=b, ghi=print)
    k = ban.get("ket") or {}
    return "\n".join([
        "=== KHÁM {0}/{1} @{2} (bản chụp {3}) · {4} · bài học {5} ===".format(
            ma, vid, moc, ban["ho_so"]["ban_chup"], ban.get("mo_hinh") or "—", "BÓNG" if ban["bong"] else "thật"),
        "tiêu đề: " + str(v.get("tieu_de") or ""),
        "chẩn đoán: " + str(k.get("chan_doan") or ban.get("loi")),
        "cổng hỏng: {0} · vì sao: {1}".format(k.get("cong_hong"), k.get("vi_sao")),
        "dự đoán lệch: " + str(k.get("du_doan_lech") or "—"),
        "nhãn: " + json.dumps(ban.get("nhan") or {}, ensure_ascii=False),
        "bài học: " + json.dumps(k.get("bai_hoc"), ensure_ascii=False),
        "số dẫn: " + json.dumps(k.get("so_dan") or [], ensure_ascii=False),
    ])


if __name__ == "__main__":
    sys.exit(main())
