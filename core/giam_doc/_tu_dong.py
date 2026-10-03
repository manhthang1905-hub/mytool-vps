"""Tự động hoá phần "Việc của bạn" của giám đốc kênh (04/10/2026 — chủ dự án: "mọi thứ auto 100%").

Người CHỈ làm việc máy không làm được (đăng nhập Chrome/Google, 2FA, nạp ShopAPI, bản quyền Windows, thuê VPS).

    phan_loai_viec(chu)                        "nguoi" | "cho_so" | "may"
    ghi_viec_may(goc, ma, viec, loai)          "may" → hàng đợi `nao/viec-tu-giam-doc.json` cho bộ não;
                                               "cho_so" → nhật ký giám đốc 1 lần. Trả True nếu là việc MỚI
    doc_viec_cho_nao(goc, bay_gio)             mục còn hạn của hàng đợi (`core.nao xem` in)
    quyen_kenh(goc, ma)                        kênh nên ở `goi_y` hay `tu_ap` theo `do-chinh-xac.json`
    tu_nang_ha_quyen(goc, …)                   hằng ngày: đủ ngưỡng → `tu_ap`; tụt → lùi `goi_y` (ghi kenh.yaml)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

TEP_HANG_DOI = os.path.join("nao", "viec-tu-giam-doc.json")
HAN_MUC_NGAY = 9              # > VIEC_CUA_BAN_CON_NGAY (8): hết hạn rồi báo cáo cũ cũng đã bỏ → không lặp lại
HAN_NHO_NGAY = 10
TOI_DA_MUC = 60

#: Câu CODE tự viết (không phải lời LLM) — chỉ người làm được.
_NGUOI_TIEN_TO = ("Quyết định lớn chờ bạn duyệt:", "Đổi tiêu đề video ")
#: Việc chỉ người làm được dù LLM viết tự do.
_RE_NGUOI = re.compile(r"đăng nhập|nạp tiền|nạp thêm|xác minh|2fa|điện thoại|bản quyền windows|thuê vps|gia hạn vps|captcha",
                       re.IGNORECASE)
#: Nhắc "chờ N video qua 48h…", "Đợi…" — máy tự đợi.
_RE_CHO_SO = re.compile(r"^\s*(?:đang\s+)?(?:chờ|đợi)\b", re.IGNORECASE)


def phan_loai_viec(chu: Any) -> str:
    """"nguoi" (chỉ người làm được) | "cho_so" (máy tự đợi số) | "may" (máy/bộ não tự xem)."""
    from .suc_khoe import VIEC_CUA_BAN  # noqa: PLC0415

    s = " ".join(str(chu or "").split())
    if s.startswith(_NGUOI_TIEN_TO) or s == " ".join(VIEC_CUA_BAN.split()):
        return "nguoi"
    if _RE_CHO_SO.match(s):
        return "cho_so"
    if _RE_NGUOI.search(s):
        return "nguoi"
    return "may"


def la_viec_suc_khoe(chu: Any) -> bool:
    """Cảnh báo chính sách thật (cò sức khoẻ) — chỉ báo người 1 lần/ngày."""
    from .suc_khoe import VIEC_CUA_BAN  # noqa: PLC0415

    return " ".join(str(chu or "").split()) == " ".join(VIEC_CUA_BAN.split())


# ── hàng đợi cho bộ não ─────────────────────────────────────────────────────

def _duong(goc: str) -> str:
    return os.path.join(goc, TEP_HANG_DOI)


def _doc(goc: str) -> Dict[str, Any]:
    try:
        with io.open(_duong(goc), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {"muc": [], "da_thay": {}}
    if not isinstance(du, dict):
        return {"muc": [], "da_thay": {}}
    du["muc"] = [m for m in du.get("muc") or [] if isinstance(m, dict)]
    du["da_thay"] = du.get("da_thay") if isinstance(du.get("da_thay"), dict) else {}
    return du


def _ghi(goc: str, du: Dict[str, Any]) -> None:
    duong = _duong(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
        tep.write("\n")
    os.replace(tam, duong)


def _tuoi_ngay(luc: Any, bay_gio: _dt.datetime) -> Optional[float]:
    try:
        return (bay_gio - _dt.datetime.fromisoformat(str(luc)[:19])).total_seconds() / 86400.0
    except ValueError:
        return None


def ghi_viec_may(goc: str, ma: str, viec: str, loai: str, *, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Một dòng "Việc của bạn" mà máy lo được. Cùng nội dung chỉ tính MỘT lần (nhớ `HAN_NHO_NGAY` ngày).
    "may" → hàng đợi bộ não; "cho_so" → nhật ký giám đốc kênh (1 lần). Trả True nếu việc MỚI."""
    bay_gio = bay_gio or _dt.datetime.now()
    khoa = hashlib.sha1("{0}|{1}".format(ma, viec).encode("utf-8")).hexdigest()[:12]
    du = _doc(goc)
    du["da_thay"] = {k: v for k, v in du["da_thay"].items()
                     if (_tuoi_ngay(v, bay_gio) if _tuoi_ngay(v, bay_gio) is not None else 99) <= HAN_NHO_NGAY}
    moi = khoa not in du["da_thay"]
    if moi:
        du["da_thay"][khoa] = bay_gio.isoformat(timespec="seconds")
        if loai == "may":
            du["muc"].append({"id": khoa, "kenh": ma, "viec": str(viec)[:400], "luc": du["da_thay"][khoa]})
        else:
            try:
                from . import so_thi_nghiem as stn  # noqa: PLC0415

                stn.ghi_nhat_ky(goc, ma, viec="cho_so", ly_do_llm=str(viec)[:300], bay_gio=bay_gio)
            except Exception:  # noqa: BLE001 — không ghi được nhật ký thì thôi, không báo người
                pass
    truoc = len(du["muc"])
    du["muc"] = [m for m in du["muc"] if (_tuoi_ngay(m.get("luc"), bay_gio) or 0) <= HAN_MUC_NGAY][-TOI_DA_MUC:]
    if moi or len(du["muc"]) != truoc:
        _ghi(goc, du)
    return moi


def doc_viec_cho_nao(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Mục giám đốc nhờ bộ não xem (còn hạn, mới → cũ). Hỏng → []."""
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        ds = [m for m in _doc(goc)["muc"] if (_tuoi_ngay(m.get("luc"), bay_gio) or 0) <= HAN_MUC_NGAY]
    except Exception:  # noqa: BLE001
        return []
    return list(reversed(ds))


# ── quyền tự nâng / hạ theo thành tích ──────────────────────────────────────

def quyen_kenh(goc: str, ma: str, hien_tai: str) -> Dict[str, Any]:
    """Quyền kênh theo `do-chinh-xac.json`, loại "dự đoán thắng/trượt" (thước đo chung của giám đốc).
    `hien_tai` = "goi_y" | "tu_ap". Có hysteresis: đang `tu_ap` chỉ lùi khi n ≥ ngưỡng mà tụt < 55%.
    Trả `{"quyen", "n", "ti_le", "dung", "doi": bool}`."""
    from . import hoi_dong  # noqa: PLC0415

    o = (hoi_dong.do_chinh_xac(goc, ma, ghi=False).get("loai") or {}).get("du_doan") or {}
    n, tl = int(o.get("n") or 0), o.get("ti_le")
    if tl is None or n < hoi_dong.TU_AP_N:
        moi = hien_tai
    elif hien_tai == "tu_ap":
        moi = "goi_y" if tl < hoi_dong.LUI_TI_LE else "tu_ap"
    else:
        moi = "tu_ap" if tl >= hoi_dong.TU_AP_TI_LE else "goi_y"
    return {"quyen": moi, "n": n, "ti_le": tl, "dung": o.get("dung"), "doi": moi != hien_tai}


def tu_nang_ha_quyen(goc: str, *, bay_gio: Optional[_dt.datetime] = None,
                     ghi_cai: Optional[Callable[..., None]] = None,
                     ghi: bool = True) -> List[Dict[str, Any]]:
    """Mỗi ngày: kênh `goi_y` đủ thành tích (≥ 70% đúng, n ≥ 10) → `tu_ap`; kênh `tu_ap` tụt (< 55%) → `goi_y`.
    Không đụng kênh `tat`, kênh có cặp `-v2` (A/B giữ `goi_y`), kênh chủ đặt `giam_doc_cho_phep_ab`.
    Ghi `kenh.yaml` qua `trung_tam.ghi_cai_kenh` + nhật ký giám đốc kèm số. Trả danh sách kênh đã đổi."""
    from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
    from . import so_thi_nghiem as stn  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    if ghi_cai is None:
        def ghi_cai(g: str, m: str, **kv: Any) -> None:
            from ..trung_tam import ghi_cai_kenh  # noqa: PLC0415

            ghi_cai_kenh(g, m, **kv)
    ra: List[Dict[str, Any]] = []
    try:
        ten_kenh = sorted(os.listdir(duong_kenh(goc)))
    except OSError:
        return ra
    for ma in ten_kenh:
        if ma.startswith("_") or ma.lower().endswith(("-v2", "_v2")):
            continue
        cai = doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}
        cd = str(cai.get("giam_doc") or "tat").strip().lower()
        if cd not in ("goi_y", "tu_ap"):
            continue
        if os.path.isdir(duong_kenh(goc, ma + "-v2")):
            if str(cai.get("giam_doc_cho_phep_ab", "")).lower() != "true":
                continue  # cặp A/B: giữ `goi_y`, không tự nâng
        try:
            q = quyen_kenh(goc, ma, cd)
        except Exception:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
            continue
        if not q["doi"]:
            continue
        ly = "{0}: dự đoán thắng/trượt đúng {1}/{2} = {3:.0%} ({4})".format(
            "nâng giam_doc goi_y → tu_ap" if q["quyen"] == "tu_ap" else "lùi giam_doc tu_ap → goi_y",
            q["dung"], q["n"], q["ti_le"] or 0.0,
            "≥ 70% trên n ≥ 10" if q["quyen"] == "tu_ap" else "tụt dưới 55%")
        if ghi:
            ghi_cai(goc, ma, giam_doc=q["quyen"])
            try:
                stn.ghi_nhat_ky(goc, ma, viec="doi_quyen", truoc=cd, sau=q["quyen"], ly_do_llm=ly, bay_gio=bay_gio)
            except Exception:  # noqa: BLE001
                pass
        ra.append({"ma": ma, "truoc": cd, "sau": q["quyen"], "ly_do": ly})
    return ra
