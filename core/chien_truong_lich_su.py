"""Lịch sử chiến trường: mỗi ngày một ảnh chụp gọn (JSONL) để xem CUỘC CHIẾN THEO THỜI GIAN.

File: <goc>/workspace/chien-truong/lich-su.jsonl — mỗi dòng một ngày; chụp lại cùng ngày thì THAY dòng cũ (ghi qua file tạm + os.replace).
Chỉ ghi đĩa, không mạng.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List


def duong_dan(goc: str) -> str:
    return os.path.join(goc, "workspace", "chien-truong", "lich-su.jsonl")


def _doc_dong(goc: str) -> List[Dict[str, Any]]:
    ra: List[Dict[str, Any]] = []
    try:
        with open(duong_dan(goc), "r", encoding="utf-8") as tep:
            for d in tep:
                d = d.strip()
                if not d:
                    continue
                try:
                    x = json.loads(d)
                except ValueError:
                    continue
                if isinstance(x, dict) and x.get("ngay"):
                    ra.append(x)
    except OSError:
        pass
    return ra


def tao_anh_chup(du: Dict[str, Any], ngay: str = "") -> Dict[str, Any]:
    """Rút gọn đầu ra chien_truong.tinh() thành một dòng lịch sử."""
    t = du.get("tong") or {}
    return {
        "ngay": ngay or _dt.date.today().isoformat(),
        "tong": {"dich": t.get("dich", 0), "ta": t.get("ta", 0), "thi_phan": t.get("thi_phan", 0)},
        "vung": {z["ma"]: {"dich": z.get("dich", 0), "ta": z.get("ta", 0), "thi_phan": z.get("thi_phan", 0)}
                 for z in (du.get("vung") or [])},
        "dich_top": [{"kenh": b.get("kenh"), "view": b.get("view", 0), "thi_phan": b.get("thi_phan", 0)}
                     for b in (du.get("dich_top") or [])[:10]],
        "quan": {q["ma"]: {"gio_xem": q.get("gio_xem", 0), "dang_ky": q.get("dang_ky", 0), "view_28": q.get("view_28", 0)}
                 for q in (du.get("quan") or [])},
    }


def co_anh_hom_nay(goc: str, ngay: str) -> bool:
    return any(x.get("ngay") == ngay for x in _doc_dong(goc)[-3:])


def ghi_anh_chup(goc: str, du: Dict[str, Any], ngay: str = "") -> Dict[str, Any]:
    """Ghi ảnh chụp của ngày `ngay` (mặc định hôm nay); đã có dòng cùng ngày thì thay. Trả về dòng đã ghi."""
    anh = tao_anh_chup(du, ngay)
    dong = [x for x in _doc_dong(goc) if x.get("ngay") != anh["ngay"]]
    dong.append(anh)
    dong.sort(key=lambda x: str(x.get("ngay")))
    p = duong_dan(goc)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        for x in dong:
            tep.write(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tam, p)
    return anh


def doc_lich_su(goc: str, so_ngay: int = 60) -> List[Dict[str, Any]]:
    """Các ảnh chụp trong `so_ngay` ngày gần nhất (cũ → mới)."""
    dong = _doc_dong(goc)
    if not dong:
        return []
    moc = (_dt.date.today() - _dt.timedelta(days=so_ngay)).isoformat()
    return [x for x in dong if str(x.get("ngay")) >= moc]


def chuoi_gon(goc: str, so_ngay: int = 30) -> List[Dict[str, Any]]:
    """Chuỗi cho biểu đồ: ngày, thị phần ta, ta, địch, thị phần đối thủ số 1."""
    ra = []
    for x in doc_lich_su(goc, so_ngay):
        t = x.get("tong") or {}
        top = (x.get("dich_top") or [{}])[0]
        ra.append({"ngay": x["ngay"], "thi_phan": t.get("thi_phan", 0), "ta": t.get("ta", 0), "dich": t.get("dich", 0),
                   "top_thi_phan": top.get("thi_phan", 0), "top_kenh": top.get("kenh") or ""})
    return ra
