"""Sổ thí nghiệm + nhật ký của giám đốc kênh — `CHANNEL/<k>/giam-doc/`.

    thi-nghiem.json   {"thi_nghiem": [mục…]}
    nhat-ky.jsonl     mỗi dòng {luc, viec, truoc, sau, ly_do_llm, so_lieu}
    trang-thai.json   {da_ghi: {khoá: {gia_tri, luc}}, chu_giu: {khoá: hạn}, ngay_chay, ngay_tuan, …}

Mục thí nghiệm: id, viec, gia_thuyet, bien{loai,khoa,cu,moi}, chi_so, nen{gia_tri,n,tu_video},
co_mau, bat_dau, han, gia_han, trang_thai ("mo" | giu | bo | mo_rong | quay_lui | chua_du), video[],
ket_luan, ly_do_llm, quay_lui_khi{tut_pct}.

Luật hết hạn: tới hạn mà chưa đủ `co_mau` video qua 52h → gia hạn MỘT lần (bằng thời lượng cũ);
lần thứ hai → `chua_du` (nơi gọi trả giá trị cũ qua `gioi_han.quay_lui`).
Mọi lần ghi là nguyên tử (tệp tạm rồi `os.replace`).
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
from typing import Any, Dict, List, Optional

from .du_lieu import thu_muc_giam_doc

TEP_THI_NGHIEM = "thi-nghiem.json"
TEP_NHAT_KY = "nhat-ky.jsonl"
TEP_TRANG_THAI = "trang-thai.json"
TRANG_THAI_CUOI = ("giu", "bo", "mo_rong", "quay_lui", "chua_du")


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=2, default=str)
        tep.write("\n")
    os.replace(tam, duong)


def _doc_json(duong: str, mac_dinh: Any) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, type(mac_dinh)) else mac_dinh
    except (OSError, ValueError):
        return mac_dinh


def _luc(bay_gio: Optional[_dt.datetime]) -> str:
    return (bay_gio or _dt.datetime.now()).replace(microsecond=0).isoformat()


# ── đọc ────────────────────────────────────────────────────────────────────

def doc(goc: str, ma: str) -> List[Dict[str, Any]]:
    """Mọi thí nghiệm của kênh (cũ → mới)."""
    du = _doc_json(os.path.join(thu_muc_giam_doc(goc, ma), TEP_THI_NGHIEM), {})
    return [t for t in du.get("thi_nghiem") or [] if isinstance(t, dict)]


def doc_nhat_ky(goc: str, ma: str, *, so_dong: int = 500) -> List[Dict[str, Any]]:
    """`so_dong` dòng cuối của nhật ký (dòng hỏng bỏ qua)."""
    ra: List[Dict[str, Any]] = []
    try:
        with io.open(os.path.join(thu_muc_giam_doc(goc, ma), TEP_NHAT_KY), encoding="utf-8") as tep:
            dong = tep.readlines()[-so_dong:]
    except OSError:
        return ra
    for d in dong:
        try:
            x = json.loads(d)
        except ValueError:
            continue
        if isinstance(x, dict):
            ra.append(x)
    return ra


def doc_trang_thai(goc: str, ma: str) -> Dict[str, Any]:
    """`giam-doc/trang-thai.json` ({} khi chưa có)."""
    return _doc_json(os.path.join(thu_muc_giam_doc(goc, ma), TEP_TRANG_THAI), {})


def doc_so(goc: str, ma: str) -> Dict[str, Any]:
    """Cả sổ một lần: {thi_nghiem, nhat_ky, trang_thai} — thứ `gioi_han.kiem` cần."""
    return {"thi_nghiem": doc(goc, ma), "nhat_ky": doc_nhat_ky(goc, ma), "trang_thai": doc_trang_thai(goc, ma)}


def dang_mo(so_hoac_ds: Any, chi_so: str = "") -> List[Dict[str, Any]]:
    """Thí nghiệm đang mở (lọc theo `chi_so` nếu có). Nhận sổ (`doc_so`) hoặc danh sách."""
    ds = so_hoac_ds.get("thi_nghiem", []) if isinstance(so_hoac_ds, dict) else so_hoac_ds
    return [t for t in ds if t.get("trang_thai") == "mo" and (not chi_so or t.get("chi_so") == chi_so)]


def het_han(so_hoac_ds: Any, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Thí nghiệm đang mở đã quá hạn."""
    bay = _luc(bay_gio)
    return [t for t in dang_mo(so_hoac_ds) if str(t.get("han") or "") and str(t["han"]) <= bay]


# ── ghi ────────────────────────────────────────────────────────────────────

def _ghi_ds(goc: str, ma: str, ds: List[Dict[str, Any]]) -> None:
    _ghi_json(os.path.join(thu_muc_giam_doc(goc, ma), TEP_THI_NGHIEM), {"kenh": ma, "thi_nghiem": ds})


def mo(goc: str, ma: str, *, viec: str, gia_thuyet: str, bien: Dict[str, Any], chi_so: str,
       nen: Dict[str, Any], co_mau: int, han_ngay: int, ly_do_llm: str = "", tut_pct: float = 20.0,
       bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Mở một thí nghiệm mới; trả mục vừa ghi."""
    bay_gio = bay_gio or _dt.datetime.now()
    ds = doc(goc, ma)
    goc_id = "{0}-{1}".format(bay_gio.strftime("%Y%m%d"), viec)
    so_thu = sum(1 for t in ds if str(t.get("id", "")).startswith(goc_id)) + 1
    tn = {"id": "{0}-{1}".format(goc_id, so_thu), "viec": viec, "gia_thuyet": gia_thuyet, "bien": dict(bien),
          "chi_so": chi_so, "nen": dict(nen), "co_mau": int(co_mau), "bat_dau": _luc(bay_gio),
          "han": _luc(bay_gio + _dt.timedelta(days=int(han_ngay))), "han_ngay": int(han_ngay), "gia_han": 0,
          "trang_thai": "mo", "video": [], "ket_luan": {}, "ly_do_llm": ly_do_llm,
          "quay_lui_khi": {"tut_pct": float(tut_pct)}}
    ds.append(tn)
    _ghi_ds(goc, ma, ds)
    return tn


def cap_nhat(goc: str, ma: str, id_tn: str, **thay: Any) -> Optional[Dict[str, Any]]:
    """Ghi đè vài trường của một thí nghiệm; `video` thì CỘNG thêm (không trùng)."""
    ds = doc(goc, ma)
    for t in ds:
        if t.get("id") == id_tn:
            for k, v in thay.items():
                if k == "video":
                    t["video"] = list(dict.fromkeys(list(t.get("video") or []) + list(v or [])))
                else:
                    t[k] = v
            _ghi_ds(goc, ma, ds)
            return t
    return None


def dong(goc: str, ma: str, id_tn: str, trang_thai: str, ket_luan: Optional[Dict[str, Any]] = None, *,
         ly_do: str = "", bay_gio: Optional[_dt.datetime] = None) -> Optional[Dict[str, Any]]:
    """Đóng thí nghiệm với trạng thái cuối (`TRANG_THAI_CUOI`)."""
    if trang_thai not in TRANG_THAI_CUOI:
        raise ValueError("trạng thái cuối không hợp lệ: {0}".format(trang_thai))
    return cap_nhat(goc, ma, id_tn, trang_thai=trang_thai, dong_luc=_luc(bay_gio),
                    ket_luan=dict(ket_luan or {}, ly_do=ly_do))


def xu_ly_het_han(goc: str, ma: str, tn: Dict[str, Any], *,
                  bay_gio: Optional[_dt.datetime] = None) -> str:
    """Thí nghiệm tới hạn chưa đủ mẫu: lần đầu gia hạn → "gia_han"; lần hai đóng "chua_du" → "chua_du"
    (nơi gọi trả giá trị cũ)."""
    bay_gio = bay_gio or _dt.datetime.now()
    if int(tn.get("gia_han") or 0) < 1:
        cap_nhat(goc, ma, tn["id"], gia_han=1,
                 han=_luc(bay_gio + _dt.timedelta(days=int(tn.get("han_ngay") or 14))))
        return "gia_han"
    dong(goc, ma, tn["id"], "chua_du", ly_do="hết hạn hai lần mà chưa đủ {0} video qua 52h".format(
        tn.get("co_mau")), bay_gio=bay_gio)
    return "chua_du"


def ghi_nhat_ky(goc: str, ma: str, *, viec: str, truoc: Any = None, sau: Any = None, ly_do_llm: str = "",
                so_lieu: Any = None, bay_gio: Optional[_dt.datetime] = None, **them: Any) -> Dict[str, Any]:
    """Nối một dòng vào `nhat-ky.jsonl`."""
    dong_ = dict({"luc": _luc(bay_gio), "viec": viec, "truoc": truoc, "sau": sau, "ly_do_llm": ly_do_llm,
                  "so_lieu": so_lieu}, **them)
    duong = os.path.join(thu_muc_giam_doc(goc, ma), TEP_NHAT_KY)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "a", encoding="utf-8") as tep:
        tep.write(json.dumps(dong_, ensure_ascii=False, default=str) + "\n")
    return dong_


def ghi_trang_thai(goc: str, ma: str, **thay: Any) -> Dict[str, Any]:
    """Gộp `thay` vào `trang-thai.json` (khoá con dict thì gộp nông)."""
    tt = doc_trang_thai(goc, ma)
    for k, v in thay.items():
        if isinstance(v, dict) and isinstance(tt.get(k), dict):
            tt[k] = dict(tt[k], **v)
        else:
            tt[k] = v
    _ghi_json(os.path.join(thu_muc_giam_doc(goc, ma), TEP_TRANG_THAI), tt)
    return tt
