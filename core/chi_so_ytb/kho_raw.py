"""Kho gói raw chỉ số — đọc `.json` hay `.json.gz` như nhau, nén gói cũ (06/10/2026).

═══ VÌ SAO ═══

`CHANNEL/<kênh>/chi-so/<video>/<mốc>/raw/*.json` là phản hồi Studio nguyên văn, KHÔNG
được xoá: `cong_thuc_v7` còn đọc lại bảng pool (`*join*.json`: kênh nguồn, tiêu đề, số
thật từng video đề xuất), `tu_nhan_da_dang` đọc lại mọi `get_creator_videos`, và
`giai_ma` giải lại cả mốc khi gói mới về — bản tóm `tong-quan.json` không giữ đủ mấy
thứ ấy. Đo 06/10/2026: ~90 MB/ngày ≈ 33 GB/năm, ổ còn ~29 GB. gzip trên mẫu 500 tệp
thật: 5,1× (lzma 6,7× nhưng nén chậm 20× — không đáng).

═══ LUẬT ═══

Gói raw cũ hơn `NGAY_CU` ngày thì nén thành `<tên>.gz` (giữ nguyên mtime — `luc_chup`
lùi về mtime với gói cũ, `_giai_ma_con_thieu` so mtime raw với `tong-quan.json`). Mọi
nơi đọc raw đi qua `liet_ke` + `mo_doc` nên không thấy khác gì.

Nén nguyên tử: ghi `<tên>.gz.tam` → đọc lại so từng byte → đặt mtime → `os.replace`
→ xoá bản gốc. Hỏng ở bất kỳ bước nào thì bản gốc còn nguyên; còn cả hai bản (xoá
gốc bị Windows chặn) thì `liet_ke` lấy bản gốc, lượt sau nén lại.
"""

from __future__ import annotations

import fnmatch
import glob
import gzip
import io
import json
import os
import time
from typing import IO, Any, Dict, List, Optional

__all__ = ["NGAY_CU", "DUOI_GZ", "ten_goc", "mo_doc", "doc_json", "liet_ke", "nen_mot", "nen_cu"]

NGAY_CU = 7
DUOI_GZ = ".gz"
_DUOI_TAM = ".tam"


def ten_goc(duong: str) -> str:
    """Tên như lúc tiện ích ghi: bỏ đuôi `.gz` nếu có."""
    return duong[:-len(DUOI_GZ)] if duong.endswith(DUOI_GZ) else duong


def mo_doc(duong: str, errors: str = "strict") -> IO[str]:
    """Mở đọc chữ utf-8 — `.gz` hay không đều được. `errors` như `io.open`.

    Truyền tên gốc (`x.json`) mà chỉ còn `x.json.gz` thì mở bản nén."""
    if not duong.endswith(DUOI_GZ) and not os.path.exists(duong) and os.path.exists(duong + DUOI_GZ):
        duong += DUOI_GZ
    if duong.endswith(DUOI_GZ):
        return gzip.open(duong, "rt", encoding="utf-8", errors=errors)
    return io.open(duong, "r", encoding="utf-8", errors=errors)


def doc_json(duong: str) -> Any:
    """`json.load` qua `mo_doc`. Bản `.gz` cụt (EOFError) báo thành OSError — mọi nơi
    gọi vốn bắt `(OSError, ValueError)` cho tệp hỏng."""
    try:
        with mo_doc(duong) as f:
            return json.load(f)
    except EOFError as loi:
        raise OSError("bản nén cụt: {0} ({1})".format(duong, loi)) from loi


def liet_ke(thu_muc: str, mau: str = "*") -> List[str]:
    """Đường dẫn THẬT của các gói trong `thu_muc` khớp `mau` (so trên tên gốc), xếp
    theo tên gốc — cùng thứ tự `sorted(glob(mau))` cũ. Có cả `x` lẫn `x.gz` thì lấy `x`."""
    theo_ten: Dict[str, str] = {}
    try:
        muc = list(os.scandir(thu_muc))
    except OSError:
        return []
    for e in muc:
        if e.name.endswith(_DUOI_TAM) or not e.is_file():
            continue
        if not fnmatch.fnmatch(ten_goc(e.name), mau):
            continue
        p = os.path.join(thu_muc, e.name)
        goc = ten_goc(p)
        if goc not in theo_ten or not p.endswith(DUOI_GZ):
            theo_ten[goc] = p
    return [theo_ten[k] for k in sorted(theo_ten)]


def nen_mot(duong: str) -> int:
    """Nén một gói. Trả số byte đã gỡ khỏi đĩa (0 nếu không làm gì). Không ném OSError."""
    if duong.endswith(DUOI_GZ) or duong.endswith(_DUOI_TAM):
        return 0
    nen = duong + DUOI_GZ
    tam = nen + _DUOI_TAM
    try:
        st = os.stat(duong)
        with open(duong, "rb") as f:
            goc = f.read()
        # Không ghi tên tệp vào đầu gz (tên `.tam` vô nghĩa) — cỡ khớp đúng ước tính `--thu`.
        with open(tam, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f,
                                                 compresslevel=6, mtime=int(st.st_mtime)) as ra:
            ra.write(goc)
        with gzip.open(tam, "rb") as vao:
            if vao.read() != goc:
                raise OSError("đọc lại bản nén không khớp: " + duong)
        os.utime(tam, ns=(st.st_atime_ns, st.st_mtime_ns))
        sau = os.path.getsize(tam)
        os.replace(tam, nen)
    except OSError:
        try:
            os.remove(tam)
        except OSError:
            pass
        return 0
    try:
        os.remove(duong)
    except OSError:
        return 0  # còn cả hai bản — liet_ke lấy bản gốc, lượt sau thử lại
    return max(0, st.st_size - sau)


def nen_cu(goc: str, ngay_cu: float = NGAY_CU, *, thu: bool = False,
           bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Nén mọi gói trong `<goc>/CHANNEL/*/chi-so/**/raw/` cũ hơn `ngay_cu` ngày.

    `thu=True`: chỉ đếm + nén thử trong RAM để báo đúng sẽ còn bao nhiêu, không ghi gì.
    Trả `{"so_tep", "bytes_truoc", "bytes_sau", "theo_kenh": {kenh: {...}}}`."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    han = bay_gio - ngay_cu * 86400
    theo_kenh: Dict[str, Dict[str, int]] = {}
    for cs in sorted(glob.glob(os.path.join(glob.escape(goc), "CHANNEL", "*", "chi-so"))):
        kenh = os.path.basename(os.path.dirname(cs))
        dem = {"so_tep": 0, "bytes_truoc": 0, "bytes_sau": 0}
        for cha, thu_con, tep in os.walk(cs):
            if os.path.basename(cha) != "raw":
                continue
            for t in sorted(tep):
                p = os.path.join(cha, t)
                if t.endswith(DUOI_GZ) or t.endswith(_DUOI_TAM) or os.path.islink(p):
                    continue
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_mtime >= han:
                    continue
                if thu:
                    try:
                        with open(p, "rb") as f:
                            sau = len(gzip.compress(f.read(), 6))
                    except OSError:
                        continue
                    giam = st.st_size - sau
                else:
                    giam = nen_mot(p)
                    if not giam and os.path.exists(p):
                        continue
                dem["so_tep"] += 1
                dem["bytes_truoc"] += st.st_size
                dem["bytes_sau"] += st.st_size - giam
        if dem["so_tep"]:
            theo_kenh[kenh] = dem
    tong = {k: sum(d[k] for d in theo_kenh.values()) for k in ("so_tep", "bytes_truoc", "bytes_sau")}
    tong["theo_kenh"] = theo_kenh
    return tong
