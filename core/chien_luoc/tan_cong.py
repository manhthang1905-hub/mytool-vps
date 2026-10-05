"""Lệnh tấn công của CHIẾN TRƯỜNG → trọng số MỀM khi chọn content (06/10/2026).

Trước đây `core/chien_truong.de_xuat_tan_cong` ("kênh X nên đánh vùng Y") chỉ in ra báo cáo ngày và trang trực
quan — bộ chọn nguồn không đọc nó, nên "lệnh" không bao giờ thành video. Giờ:

    chien_truong.tinh()  ──ghi──▶  workspace/chien-truong/tan-cong.json   {ngay, kenh: {mã kênh: [{ma, ten, diem}]}}
    chien_luoc.xep_hang  ──đọc──▶  ap_he_so(nc, bang): ứng viên thuộc vùng được lệnh × (1 + 0,30 × điểm/100)

Luật:
  * MỀM, có trần: hệ số ∈ [1; 1 + `TRAN`] (≤ +30%), nhân vào điểm sau hệ số cụm của tự học — chỉ nắn thứ hạng,
    không ép chọn, không loại ứng viên nào (lệnh của chiến trường là giả thuyết thị trường, Thompson vẫn là trọng tài);
  * vùng của ứng viên = nhãn cụm tự học (`tu_hoc.nhan_cum`, cùng bộ cụm V7 mà chiến trường dùng), lùi về vùng AI
    theo link (`workspace/chien-truong/vung-ai.json`, `core/chien_truong_ai`) cho video "đề tài khác";
  * tệp cũ hơn `NGAY_TOI_DA` ngày (báo cáo ngày không chạy) → không áp gì (mục "Tín hiệu học" báo tệp cũ).

Không mạng, không tiền; chỉ đọc/ghi đĩa. Không có mã kênh/ngách nào viết cứng — máy khác chủ đề khác tự đúng.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
from typing import Any, Dict, List, Optional, Tuple

TEP = os.path.join("workspace", "chien-truong", "tan-cong.json")
TEP_VUNG_AI = os.path.join("workspace", "chien-truong", "vung-ai.json")
TRAN = 0.30
NGAY_TOI_DA = 3


def duong(goc: str) -> str:
    return os.path.join(goc, TEP)


def ghi(goc: str, du: Dict[str, Any], ngay: str = "") -> Dict[str, Any]:
    """Ghi lệnh tấn công từ đầu ra `chien_truong.tinh()` (`de_xuat_tan_cong`). Trả nội dung đã ghi."""
    ra = {"ngay": ngay or _dt.date.today().isoformat(), "luc": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
          "kenh": {str(x.get("kenh")): [{"ma": str(v.get("ma") or ""), "ten": str(v.get("ten") or ""),
                                         "diem": float(v.get("diem") or v.get("co_hoi") or 0)}
                                        for v in (x.get("vung") or []) if v.get("ma")]
                   for x in (du.get("de_xuat_tan_cong") or []) if x.get("kenh")}}
    p = duong(goc)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(json.dumps(ra, ensure_ascii=False, indent=1) + "\n")
    os.replace(tam, p)
    return ra


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def tuoi_ngay(goc: str, bay_gio: Optional[_dt.datetime] = None) -> Optional[int]:
    """Số ngày từ lần ghi lệnh cuối (None = chưa có tệp / hỏng)."""
    du = _doc_json(duong(goc))
    try:
        ngay = _dt.date.fromisoformat(str((du or {}).get("ngay") or "")[:10])
    except ValueError:
        return None
    return ((bay_gio or _dt.datetime.now()).date() - ngay).days


def lenh_cua_kenh(goc: str, ma_kenh: str, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Dict[str, Any]]:
    """`{mã vùng: {ten, diem}}` được lệnh cho kênh — {} khi chưa có tệp, tệp cũ quá `NGAY_TOI_DA` ngày, hoặc kênh
    không có lệnh."""
    tuoi = tuoi_ngay(goc, bay_gio)
    if tuoi is None or tuoi > NGAY_TOI_DA or tuoi < -1:
        return {}
    ds = ((_doc_json(duong(goc)) or {}).get("kenh") or {}).get(ma_kenh) or []
    return {str(v["ma"]): v for v in ds if isinstance(v, dict) and v.get("ma")}


def he_so(diem: Any) -> float:
    """1 + `TRAN` × điểm/100, kẹp trong [1; 1 + TRAN]."""
    try:
        x = float(diem or 0) / 100.0
    except (TypeError, ValueError):
        x = 0.0
    return round(1.0 + TRAN * max(0.0, min(1.0, x)), 3)


def _vung_ai(goc: str) -> Dict[str, str]:
    du = _doc_json(os.path.join(goc, TEP_VUNG_AI)) or {}
    v = du.get("video") if isinstance(du, dict) else None
    return {str(k): str(x) for k, x in v.items()} if isinstance(v, dict) else {}


def vung_cua(d: Dict[str, Any], cum_cua: Any, vung_ai: Dict[str, str]) -> str:
    from .. import tu_hoc  # noqa: PLC0415

    return tu_hoc.nhan_cum(d, cum_cua) or vung_ai.get(str(d.get("link") or ""), "")


def ap_he_so(nc: Any, bang: Dict[str, List[Dict[str, Any]]]) -> Tuple[int, int]:
    """Nhân điểm ứng viên thuộc vùng được lệnh với `he_so(diem vùng)` rồi xếp lại từng bảng. Ghi `he_so_tan_cong`,
    `tin_hieu.tan_cong`, một dòng `ly_do`. Trả `(số ứng viên được nắn, số vùng được lệnh)`."""
    lenh = lenh_cua_kenh(nc.goc, nc.ma_kenh, getattr(nc, "bay_gio", None))
    if not lenh:
        return 0, 0
    vung_ai = _vung_ai(nc.goc)
    n = 0
    for ds in bang.values():
        doi = False
        for d in ds:
            vung = vung_cua(d, nc.cum_cua, vung_ai)
            if vung not in lenh:
                continue
            he = he_so(lenh[vung].get("diem"))
            try:
                d["diem"] = round(float(d.get("diem") or 0) * he, 2)
            except (TypeError, ValueError):
                continue
            d["he_so_tan_cong"] = he
            d.setdefault("tin_hieu", {})["tan_cong"] = vung
            d["ly_do"] = list(d.get("ly_do") or []) + ["chiến trường: lệnh tấn công vùng “{0}” ×{1:.2f}".format(
                lenh[vung].get("ten") or vung, he)]
            n += 1
            doi = True
        if doi:
            ds.sort(key=lambda d: -float(d.get("diem") or 0) if isinstance(d.get("diem"), (int, float)) else 0)
    if n:
        nc.ghi("  chiến trường: {0} ứng viên thuộc vùng được lệnh ({1}) — nắn điểm ≤ +{2:.0%}.".format(
            n, ", ".join(sorted(lenh)), TRAN))
    return n, len(lenh)
