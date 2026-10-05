"""Giữ đĩa VPS sống một năm — MỘT nhịp dọn, gọi từ gác tổng (06/10/2026).

═══ LUẬT (nói trong hai câu) ═══

Video đã lên YouTube (sổ `vm/logs/so-video-id.json` xác nhận) quá
`don_dep.NGAY_SAU_CONG_KHAI` ngày thì xoá file nặng của nó, giữ srt/json/bìa đã chọn;
ổ trống dưới `don_dep_mo_rong.NGUONG_O_GB` GB thì không bắt đầu dựng video mới và
báo động. Thêm: tệp `*.log` nào vượt `GIOI_HAN_LOG_BYTE` thì xoay vòng, giữ
`SO_BAN_LOG_GIU` bản nén.

═══ TỆP NÀY KHÔNG VIẾT LẠI LUẬT NÀO ═══

* Xoá file nặng: `core/don_dep.don_theo_cai_dat` (vẫn sau cờ `tu_don` của từng kênh).
  Trước đây nó chỉ chạy cuối lượt `tu_chay --tat-ca` — máy ngừng sản xuất (van ổ
  chặn, ví cạn) là ngừng luôn dọn. Gọi thêm từ gác tổng (lịch 15') để dọn không
  phụ thuộc sản xuất.
* Van ổ: `core/dieu_phoi` → `don_dep_mo_rong.van_o` (không mở lượt mới). Báo
  động: `core/gac_tong._kiem_dia_day` (cùng ngưỡng, nhắc lại mỗi 24h).
* Mới ở đây chỉ có xoay `*.log`.

═══ XOAY LOG ═══

Chỉ `*.log` (không `*.jsonl`: ở kho này `.jsonl` là SỔ dữ liệu mà tự học đọc trọn
— `bai-hoc.jsonl`, `hoi-dong.jsonl`, sổ thí nghiệm). Đổi tên `x.log` → nén thành
`x.log.1.gz` (đẩy `.1.gz`→`.2.gz`…). Tệp đang bị tiến trình khác giữ thì Windows
không cho đổi tên → bỏ qua, nhịp sau thử lại; nơi ghi mở lại tệp sẽ tạo `x.log`
mới, nơi đọc đuôi vẫn đọc đúng tệp hiện hành. Không bao giờ đi vào `PROJECTS/`,
`.git`, `.claude`, thư mục LevelDB (có tệp `CURRENT`) hay ra ngoài thư mục gốc.

Lệnh: `python -m core.don_dia --thu` (chỉ tính, không xoá) · `--that` (dọn thật).
"""

from __future__ import annotations

import datetime
import gzip
import json
import os
import shutil
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import don_dep, don_dep_mo_rong, ghi_dia
from .kenh import doc_kenh, liet_ke_kenh

__all__ = ["GIOI_HAN_LOG_BYTE", "SO_BAN_LOG_GIU", "NHIP_GIO",
           "ung_vien_xoay_log", "xoay_log", "chay", "nhip"]

#: `*.log` vượt cỡ này thì xoay. Lớn hơn trần tự xoay của các log đã tự lo
#: (`tu-chay.log` 5 MB, `dieu-phoi-<k>.log` 5 MB) để không giành việc của chúng.
GIOI_HAN_LOG_BYTE = 10 * 1024 * 1024
SO_BAN_LOG_GIU = 3
#: Gác tổng chạy mỗi 15' — nhịp dọn thật chỉ mỗi ngần này giờ.
NHIP_GIO = 3.0

_BO_QUA_THU_MUC = frozenset({"PROJECTS", ".git", ".claude", "node_modules", "__pycache__",
                             ".pytest_cache", "models", "runtime"})
_DUOI_TAM = ".dang-xoay"


def _tep_nhip(goc: str) -> str:
    return os.path.join(goc, "workspace", "don-dia", "lan-cuoi.json")


def _gb(so_byte: float) -> str:
    return "{0:.2f} GB".format(so_byte / 1024 ** 3)


# ── Xoay log ─────────────────────────────────────────────────────────────────


def ung_vien_xoay_log(goc: str, *, gioi_han: int = GIOI_HAN_LOG_BYTE) -> List[Dict[str, Any]]:
    """`*.log` dưới `goc` vượt `gioi_han` (chỉ đọc). Kèm tệp `.dang-xoay` rớt lại."""
    ra: List[Dict[str, Any]] = []
    for cha, thu, tep in os.walk(goc):
        thu[:] = [t for t in thu if t not in _BO_QUA_THU_MUC and not t.startswith(".git")
                  and not don_dep._la_lien_ket(os.path.join(cha, t))]  # noqa: SLF001
        if "CURRENT" in tep:  # LevelDB (log là dữ liệu, không phải nhật ký)
            thu[:] = []
            continue
        for t in tep:
            if not (t.endswith(".log") or t.endswith(".log" + _DUOI_TAM)):
                continue
            p = os.path.join(cha, t)
            if don_dep._la_lien_ket(p):  # noqa: SLF001
                continue
            try:
                co = os.path.getsize(p)
            except OSError:
                continue
            if co > gioi_han or t.endswith(_DUOI_TAM):
                ra.append({"duong": p, "bytes": co})
    return ra


def xoay_log(duong: str, *, giu: int = SO_BAN_LOG_GIU) -> bool:
    """Xoay MỘT log. `True` nếu đã xoay; tệp đang bị giữ/lỗi → `False`, không ném."""
    goc_log = duong[:-len(_DUOI_TAM)] if duong.endswith(_DUOI_TAM) else duong
    tam = goc_log + _DUOI_TAM
    try:
        if duong != tam:
            if os.path.exists(tam):
                return False  # lần trước nén dở — chờ lượt sau xử lý tệp tạm trước
            os.replace(goc_log, tam)  # Windows: tệp đang mở bởi nơi khác → PermissionError
        for i in range(giu, 1, -1):
            cu = "{0}.{1}.gz".format(goc_log, i - 1)
            if os.path.exists(cu):
                os.replace(cu, "{0}.{1}.gz".format(goc_log, i))
        nen = goc_log + ".1.gz"
        with open(tam, "rb") as vao, gzip.open(nen + ".tmp", "wb") as ra:
            shutil.copyfileobj(vao, ra)
        os.replace(nen + ".tmp", nen)
        os.remove(tam)
        return True
    except OSError:
        return False


# ── Một nhịp ─────────────────────────────────────────────────────────────────


def chay(goc: str, *, thu: bool = True,
         danh_sach_kenh: Optional[Sequence[str]] = None,
         con_trong_gb_fn: Optional[Callable[[str], Optional[float]]] = None) -> Dict[str, Any]:
    """Một nhịp dọn. `thu=True`: chỉ tính sẽ giải phóng bao nhiêu, không xoá gì."""
    ds = list(danh_sach_kenh) if danh_sach_kenh is not None else liet_ke_kenh(goc)
    con_gb = (con_trong_gb_fn or don_dep._con_trong_gb)(goc)  # noqa: SLF001
    video: Dict[str, Any] = {}
    for ma in ds:
        try:
            if thu:
                if not doc_kenh(goc, ma).tu_don:
                    video[ma] = {"chay": False, "bytes": 0, "so_goi": 0, "ly_do": "chưa bật tu_don"}
                    continue
                kq = don_dep.don(goc, ma, thuc_hien=False)
                video[ma] = {"chay": True, "bytes": int(kq["tong_bytes"]), "so_goi": len(kq["ung_vien"])}
            else:
                kq = don_dep.don_theo_cai_dat(goc, ma)
                da = kq.get("da_don") or []
                video[ma] = {"chay": bool(kq.get("chay")), "so_goi": len(da),
                             "bytes": sum(int(u.get("bytes") or 0) for u in da),
                             "ly_do": kq.get("ly_do") or ""}
        except Exception as loi:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
            video[ma] = {"chay": False, "bytes": 0, "so_goi": 0, "ly_do": "lỗi: {0}".format(str(loi)[:150])}

    logs = ung_vien_xoay_log(goc)
    da_xoay = [] if thu else [u["duong"] for u in logs if xoay_log(u["duong"])]
    return {
        "thu": thu,
        "con_trong_gb": con_gb,
        "van_o": don_dep_mo_rong.van_o(goc, con_gb),
        "ngay_sau_cong_khai": don_dep.NGAY_SAU_CONG_KHAI,
        "nguong_o_gb": don_dep_mo_rong.NGUONG_O_GB,
        "video": video,
        "video_bytes": sum(v["bytes"] for v in video.values()),
        "log": logs,
        "log_bytes": sum(u["bytes"] for u in logs),
        "log_da_xoay": da_xoay,
    }


def tom_tat(kq: Dict[str, Any]) -> str:
    """Một dòng cho gác tổng / dòng lệnh."""
    con = kq.get("con_trong_gb")
    dau = "Dọn đĩa{0}: ổ còn {1}".format(" (thử)" if kq.get("thu") else "",
                                        "?" if con is None else "{0:.1f} GB".format(con))
    so_goi = sum(v.get("so_goi") or 0 for v in kq["video"].values())
    phan = ["{0} video đã lên {1} {2}".format(so_goi, "sẽ giải phóng" if kq.get("thu") else "đã xoá",
                                              _gb(kq["video_bytes"])),
            "{0} log cần xoay ({1})".format(len(kq["log"]), _gb(kq["log_bytes"]))
            if kq.get("thu") else "{0} log đã xoay".format(len(kq["log_da_xoay"]))]
    if not kq["van_o"].get("duoc_mo_moi", True):
        phan.append("VAN Ổ ĐANG ĐÓNG — không mở video mới")
    return dau + " · " + " · ".join(phan)


def nhip(goc: str, *, bay_gio: Optional[float] = None, nhip_gio: float = NHIP_GIO) -> Optional[Dict[str, Any]]:
    """Gác tổng gọi mỗi lượt: chỉ dọn THẬT khi đã qua `nhip_gio` giờ từ lần trước.

    Trả `None` khi chưa tới nhịp. Ghi mốc TRƯỚC khi dọn — một lần dọn hỏng giữa chừng
    không biến thành vòng dọn lại mỗi 15'."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    tep = _tep_nhip(goc)
    try:
        with open(tep, encoding="utf-8") as f:
            truoc = float((json.load(f) or {}).get("luc") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        truoc = 0.0
    if bay_gio - truoc < nhip_gio * 3600:
        return None
    os.makedirs(os.path.dirname(tep), exist_ok=True)
    ghi_dia.ghi_json(tep, {"luc": bay_gio,
                           "luc_doc": datetime.datetime.fromtimestamp(bay_gio).strftime("%Y-%m-%d %H:%M")})
    return chay(goc, thu=False)


# ── Dòng lệnh ────────────────────────────────────────────────────────────────


def _main(argv: Optional[Sequence[str]] = None) -> int:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    a = list(sys.argv[1:] if argv is None else argv)
    if "--thu" not in a and "--that" not in a:
        print("Dùng: python -m core.don_dia --thu   (chỉ tính, không xoá)")
        print("      python -m core.don_dia --that  (dọn thật, như gác tổng)")
        return 0
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kq = chay(goc, thu="--thu" in a)
    print("Luật: video đã lên YouTube ≥ {0} ngày → xoá file nặng; ổ < {1:g} GB → không dựng "
          "video mới + báo động; *.log > {2} MB → xoay, giữ {3} bản nén.".format(
              kq["ngay_sau_cong_khai"], kq["nguong_o_gb"], GIOI_HAN_LOG_BYTE // 1024 ** 2, SO_BAN_LOG_GIU))
    for ma, v in sorted(kq["video"].items()):
        print("  {0}: {1} gói, {2}{3}".format(ma, v.get("so_goi") or 0, _gb(v.get("bytes") or 0),
                                             " ({0})".format(v["ly_do"]) if v.get("ly_do") else ""))
    for u in kq["log"]:
        print("  log: {0} ({1:.1f} MB)".format(os.path.relpath(u["duong"], goc), u["bytes"] / 1024 ** 2))
    print(tom_tat(kq))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
