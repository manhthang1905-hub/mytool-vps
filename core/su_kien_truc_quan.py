"""CHIẾN BÁO cho Trung tâm trực quan (06/10/2026) — dòng sự kiện kiểu game, dựng từ tệp đã có trên đĩa. CHỈ ĐỌC.

Nguồn (mỗi nguồn bọc try riêng — một nguồn hỏng chỉ ghi vào `loi_nguon`, không làm vỡ cả trang):
  * `vm/logs/so-video-id.json`     → video ta đã tới giờ lên sóng = «tấn công» (tiêu đề từ kế hoạch đăng của kênh)
  * `nao/hanh-dong.json`           → bộ não ra lệnh / chấm thắng-thua (qua `nao_truc_quan.doc_hanh_dong`)
  * `workspace/loi-chay-max.md`    → sự cố sản xuất (bỏ mục **nhac**)
  * `workspace/tu-chay/tu-chay.log` + `workspace/tu-chay/cho-clip/*.json` → «kho đạn» (kho clip của cổng cạn từ lúc nào,
    kênh nào đang chờ tới hạn nào)

Sự kiện đối thủ nổ / thị phần đổi theo ngày thì trang tự suy từ `/chien-truong.json` + `/chien-truong-lich-su.json`.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

GOC = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SO_NGAY = 14             # chỉ lấy sự kiện trong ngần này ngày
TOI_DA = 120             # tối đa số sự kiện trả về (mới → cũ)
TUOI_CHO_CLIP = 45 * 60  # dấu chờ clip không làm tươi quá ngần này giây → coi như đã thôi chờ
NHO_DEM_GIAY = 300.0
_DAU_HET_CLIP = ("kho clip của cổng hết hạn mức", "engine clip hết hạn mức", "engine_unavailable")


def _che(chu: Any) -> str:
    try:
        from core import nao_truc_quan  # noqa: PLC0415
        return nao_truc_quan.che(chu)
    except Exception:  # noqa: BLE001
        return str(chu or "")


def _json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _duoi(duong: str, so_byte: int = 600_000) -> List[str]:
    """Các dòng cuối tệp (đọc tối đa `so_byte` byte cuối — log có thể vài MB)."""
    try:
        with open(duong, "rb") as tep:
            tep.seek(0, os.SEEK_END)
            n = tep.tell()
            tep.seek(max(0, n - so_byte))
            du = tep.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    dong = du.splitlines()
    return dong[1:] if n > so_byte else dong


def cac_kenh(goc: str) -> List[str]:
    d = _json(os.path.join(goc, "vm", "cai-dat-tool.json"))
    return sorted(((d or {}).get("kenh") or {}).keys()) if isinstance(d, dict) else []


def _tieu_de_ke_hoach(goc: str, kenh: str) -> Dict[str, str]:
    """Mã gói → tiêu đề, theo kế hoạch đăng của kênh."""
    try:
        from core import ke_hoach_dang  # noqa: PLC0415
        cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    except Exception:  # noqa: BLE001
        return {}
    if not cot or "Mã gói" not in cot or "Tiêu đề" not in cot:
        return {}
    im, it = cot.index("Mã gói"), cot.index("Tiêu đề")
    return {r[im].strip(): r[it].strip() for r in hang if len(r) > max(im, it) and r[im].strip()}


def tan_cong(goc: str, bay: _dt.datetime, phan_cum: Optional[Callable[[str], str]] = None) -> List[Dict[str, Any]]:
    """Video ta đã tới giờ lên sóng (lịch ≤ bây giờ, trong SO_NGAY ngày) — mỗi video là một đợt tấn công."""
    so = _json(os.path.join(goc, "vm", "logs", "so-video-id.json"))
    if not isinstance(so, dict):
        return []
    moc = bay - _dt.timedelta(days=SO_NGAY)
    tieu_de: Dict[str, Dict[str, str]] = {}
    ra = []
    for khoa, v in so.items():
        if not isinstance(v, dict) or "/" not in str(khoa):
            continue
        kenh, ma = str(khoa).split("/", 1)
        try:
            luc = _dt.datetime.strptime(str(v.get("lich") or ""), "%d/%m/%Y %H:%M")
        except ValueError:
            continue
        if not (moc <= luc <= bay) or not v.get("video_id"):
            continue
        if kenh not in tieu_de:
            tieu_de[kenh] = _tieu_de_ke_hoach(goc, kenh)
        td = tieu_de[kenh].get(ma, "")
        cum = ""
        if phan_cum and td:
            try:
                cum = phan_cum(td) or ""
            except Exception:  # noqa: BLE001
                cum = ""
        ra.append({"luc": luc.strftime("%Y-%m-%d %H:%M"), "loai": "tan_cong", "kenh": kenh, "ma": ma,
                   "tieu_de": _che(td)[:120], "cum": cum, "link": "https://www.youtube.com/watch?v=" + str(v["video_id"])})
    return ra


def lenh_nao(goc: str, bay: _dt.datetime) -> List[Dict[str, Any]]:
    """Bộ não ra lệnh (lúc ghi) và chấm thắng/thua (lúc chấm)."""
    from core import nao_truc_quan  # noqa: PLC0415
    moc = (bay - _dt.timedelta(days=SO_NGAY)).strftime("%Y-%m-%d")
    ra = []
    for d in nao_truc_quan.doc_hanh_dong(goc, bay.strftime("%Y-%m-%d")):
        luc = str(d.get("luc") or "").replace("T", " ")[:16]
        if luc[:10] >= moc:
            ra.append({"luc": luc, "loai": "lenh_nao", "kenh": d.get("kenh") or "", "ma": d.get("id") or "",
                       "lenh": d.get("lenh") or "", "tieu_de": _che(d.get("noi_dung"))[:140],
                       "chi_tiet": _che(d.get("du_doan"))[:180]})
        cl = str(d.get("cham_luc") or "").replace("T", " ")[:16]
        if d.get("cham") in ("dung", "sai") and cl[:10] >= moc:
            ra.append({"luc": cl, "loai": "cham_nao", "kenh": d.get("kenh") or "", "ma": d.get("id") or "",
                       "ket": d["cham"], "tieu_de": _che(d.get("du_doan"))[:140], "chi_tiet": _che(d.get("ghi_chu_cham"))[:180]})
    return ra


def su_co(goc: str, bay: _dt.datetime, kenh: List[str]) -> List[Dict[str, Any]]:
    """Sự cố sản xuất từ sổ lỗi (bỏ mục nhắc); gắn kênh nếu dòng có nhắc mã kênh."""
    moc = (bay - _dt.timedelta(days=SO_NGAY)).strftime("%Y-%m-%d %H:%M")
    mau = re.compile(r"^- \[(\d{4}-\d\d-\d\d \d\d:\d\d)\]\s*(?:\*\*(\w+)\*\*\s*[—-]\s*)?(.*)$")
    ra = []
    for dong in _duoi(os.path.join(goc, "workspace", "loi-chay-max.md"), 300_000):
        m = mau.match(dong.strip())
        if not m or m.group(1) < moc or (m.group(2) or "") == "nhac":
            continue
        chu = m.group(3)
        k = next((x for x in sorted(kenh, key=len, reverse=True) if x in chu), "")
        ra.append({"luc": m.group(1), "loai": "su_co", "muc": m.group(2) or "", "kenh": k, "tieu_de": _che(chu)[:200]})
    return ra


def kho_clip(goc: str, bay: _dt.datetime) -> Dict[str, Any]:
    """Kho đạn: lần đầu hôm nay cổng báo hết hạn mức clip, lần cuối, và các kênh đang đứng chờ (dấu còn tươi)."""
    hom = bay.strftime("%Y-%m-%d")
    dau = cuoi = ""
    dong_cuoi = ""
    for dong in _duoi(os.path.join(goc, "workspace", "tu-chay", "tu-chay.log")):
        if not dong.startswith("[" + hom) or not any(x in dong for x in _DAU_HET_CLIP):
            continue
        luc = dong[1:20]
        dau = dau or luc
        cuoi, dong_cuoi = luc, dong[22:]
    cho = []
    thu = os.path.join(goc, "workspace", "tu-chay", "cho-clip")
    try:
        tep = sorted(x for x in os.listdir(thu) if x.endswith(".json"))
    except OSError:
        tep = []
    for t in tep:
        d = _json(os.path.join(thu, t))
        if not isinstance(d, dict):
            continue
        try:
            tuoi = bay.timestamp() - float(d.get("luc") or 0)
        except (TypeError, ValueError):
            continue
        if 0 <= tuoi <= TUOI_CHO_CLIP:
            cho.append({"kenh": str(d.get("kenh") or t[:-5]), "han": str(d.get("han") or "")[:16].replace("T", " "),
                        "tu": str(d.get("tu") or "")[:16].replace("T", " ")})
    return {"can": bool(cuoi) or bool(cho), "tu": dau, "cuoi": cuoi, "dong": _che(dong_cuoi)[:200], "kenh_cho": cho}


def _phan_cum_mac_dinh(goc: str) -> Optional[Callable[[str], str]]:
    """Gán đề tài (vùng chiến trường) cho tiêu đề — cùng bộ cụm `core.chien_truong` dùng. Không có → None."""
    try:
        from core import chien_truong  # noqa: PLC0415
        if os.path.realpath(chien_truong.GOC) != os.path.realpath(goc):
            return None
        v7, ch, _ten = chien_truong._bo_cum(cac_kenh(goc))  # noqa: SLF001
        return lambda td: chien_truong._cum(v7, ch, td)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return None


def tinh(goc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None,
         phan_cum: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    goc = goc or GOC
    bay = bay_gio or _dt.datetime.now()
    kenh = cac_kenh(goc)
    if phan_cum is None:
        phan_cum = _phan_cum_mac_dinh(goc)
    ds: List[Dict[str, Any]] = []
    loi: Dict[str, str] = {}
    for ten, ham in (("tan_cong", lambda: tan_cong(goc, bay, phan_cum)), ("lenh_nao", lambda: lenh_nao(goc, bay)),
                     ("su_co", lambda: su_co(goc, bay, kenh))):
        try:
            ds.extend(ham())
        except Exception as e:  # noqa: BLE001
            loi[ten] = "{0}: {1}".format(type(e).__name__, str(e)[:120])
    try:
        kho = kho_clip(goc, bay)
    except Exception as e:  # noqa: BLE001
        kho, loi["kho_clip"] = {}, "{0}: {1}".format(type(e).__name__, str(e)[:120])
    if kho.get("tu"):
        ds.append({"luc": kho["tu"][:16], "loai": "het_clip", "kenh": "", "tieu_de": "Kho clip của cổng cạn hạn mức hôm nay",
                   "chi_tiet": kho.get("dong", "")})
    ds.sort(key=lambda x: (x.get("luc") or "", x.get("loai") or ""), reverse=True)
    return {"luc": bay.strftime("%Y-%m-%d %H:%M:%S"), "kenh": kenh, "su_kien": ds[:TOI_DA], "kho_clip": kho, "loi_nguon": loi}


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None}
_KHOA = threading.Lock()


def tinh_nho(han: float = NHO_DEM_GIAY) -> Dict[str, Any]:
    with _KHOA:
        if _NHO["du"] is None or time.time() - _NHO["luc"] > han:
            _NHO["du"], _NHO["luc"] = tinh(), time.time()
        return _NHO["du"]


if __name__ == "__main__":
    print(json.dumps(tinh(), ensure_ascii=False, indent=1)[:5000])
