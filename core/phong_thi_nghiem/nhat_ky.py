"""NHẬT KÝ BÓNG — top-K của MỌI giả thuyết, mỗi kênh, mỗi ngày (chỉ nối, có ngày).

`workspace/phong-thi-nghiem/nhat-ky-bong-<YYYY-MM>.jsonl`, một dòng = một (ngày, kênh, giả thuyết, phiên bản):

    {"ngay": "2026-10-11", "kenh": "<kênh>", "gt": "H-DOT-BIEN", "pb": 1, "che_do": "that" | "nguoc",
     "luc": "2026-10-11T09:12:00", "k": 10, "n_du": 37, "n_vu_tru": 1520,
     "top": [{"ma": "<mã nguồn>", "d": 3.41, "v": 51000, "tv": 630, "t": 1791000000, "kn": "<kênh nguồn>",
              "td": "<60 ký tự đầu tiêu đề>"}, ...]}

`ngay` = thông tin TỚI HẾT ngày ấy. `che_do = "nguoc"` = dòng dựng lại từ lịch sử (chạy ngược). Một (ngày, kênh, gt,
pb) chỉ ghi MỘT lần — lần đầu thắng; không bao giờ sửa dòng cũ. Dòng `v`/`t`/`tv` là số lúc ghi (view, giờ quét, trung vị
kênh nguồn) — tầng đo thị trường so với số về sau mà không cần ảnh chụp kho.
"""

from __future__ import annotations

import glob
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import _chung as c


def duong_thang(goc: str, ngay: str) -> str:
    return os.path.join(c.thu_muc_chung(goc), "{0}{1}.jsonl".format(c.TIEN_TO_NHAT_KY, str(ngay)[:7]))


def doc(goc: str, *, tu: str = "", den: str = "", kenh: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Mọi dòng nhật ký (ngày trong [tu, den] nếu có), cũ trước."""
    ra = []
    for p in sorted(glob.glob(os.path.join(c.thu_muc_chung(goc), c.TIEN_TO_NHAT_KY + "*.jsonl"))):
        thang = os.path.basename(p)[len(c.TIEN_TO_NHAT_KY):len(c.TIEN_TO_NHAT_KY) + 7]
        if tu and thang < tu[:7]:
            continue
        if den and thang > den[:7]:
            continue
        for x in c.doc_jsonl(p):
            n = str(x.get("ngay") or "")
            if not n or (tu and n < tu) or (den and n > den):
                continue
            if kenh and x.get("kenh") not in kenh:
                continue
            ra.append(x)
    ra.sort(key=lambda x: (x.get("ngay", ""), x.get("kenh", ""), x.get("gt", ""), int(x.get("pb") or 1)))
    return ra


def moi_nhat(goc: str, kenh: str, gt: str, *, den: str = "", lui: int = 3) -> Optional[Dict[str, Any]]:
    """Dòng nhật ký MUỘN NHẤT của (kênh, giả thuyết) trong `lui` ngày tới `den` (mặc định hôm nay) — đợt 2 lấy top-K
    của giả thuyết được chọn cho khe từ đây. Không có → None."""
    den = den or c.hom_nay()
    tu = c.cong_ngay(den, -lui)
    ds = [x for x in doc(goc, tu=tu, den=den, kenh=[kenh]) if x.get("gt") == gt]
    return max(ds, key=lambda x: (x.get("ngay", ""), int(x.get("pb") or 1))) if ds else None


def da_co(goc: str, kenh: str, ngay: str) -> Set[Tuple[str, int]]:
    """`{(gt, pb)}` đã có dòng cho (kênh, ngày)."""
    return {(str(x.get("gt")), int(x.get("pb") or 1)) for x in c.doc_jsonl(duong_thang(goc, ngay))
            if x.get("kenh") == kenh and x.get("ngay") == ngay}


def dong(ngay: str, kenh: str, gt: Dict[str, Any], top: Sequence[Tuple[Dict[str, Any], float]], *, n_du: int,
         n_vu_tru: int, k: int, che_do: str, luc: Optional[float] = None, ghi: str = "") -> Dict[str, Any]:
    ra = {"ngay": ngay, "kenh": kenh, "gt": gt["id"], "pb": int(gt.get("phien_ban") or 1), "che_do": che_do,
          "luc": c.luc_iso(luc), "k": int(k), "n_du": int(n_du), "n_vu_tru": int(n_vu_tru),
          "top": [{"ma": d.get("ma"), "d": round(float(x), 4), "v": d.get("view"), "tv": d.get("view_tv"),
                   "t": d.get("luc"), "kn": d.get("kenh_nguon", ""), "td": str(d.get("tieu_de") or "")[:60]}
                  for d, x in top]}
    if ghi:
        ra["ghi"] = ghi
    return ra


def ghi(goc: str, dong_moi: Iterable[Dict[str, Any]]) -> int:
    """Nối các dòng CHƯA có (theo (ngày, kênh, gt, pb)) vào sổ tháng. Trả số dòng đã ghi."""
    theo_thang: Dict[str, List[Dict[str, Any]]] = {}
    for d in dong_moi:
        theo_thang.setdefault(duong_thang(goc, d["ngay"]), []).append(d)
    so = 0
    for p, ds in theo_thang.items():
        co = {(x.get("ngay"), x.get("kenh"), x.get("gt"), int(x.get("pb") or 1)) for x in c.doc_jsonl(p)}
        moi = []
        for d in ds:
            k = (d["ngay"], d["kenh"], d["gt"], int(d.get("pb") or 1))
            if k in co:
                continue
            co.add(k)
            moi.append(d)
        so += c.them_dong(p, moi)
    return so
