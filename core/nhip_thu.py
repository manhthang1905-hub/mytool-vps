"""THỬ NHỊP ĐĂNG có rào (22/10/2026).

Chủ cho TL2/TL3/TL4 lên 2 video/ngày để dùng công suất dư — nhưng chính chủ từng thấy (01/10) "đăng dày view lẹt đẹt".
Nên mỗi lần nâng nhịp là một THỬ NGHIỆM:

* `bat_dau(goc, kenh, nhip, video_moi_ngay)`: cất giá trị cũ của kenh.yaml (`nhip_dang`, `video_moi_ngay`,
  `video_toi_da_ngay`), chụp MỐC = lượt xem hiện tại các video đăng 8 ngày TRƯỚC thử nghiệm, rồi ghi nhịp mới.
* `danh_gia(goc)` (gọi mỗi ngày từ `core/tu_kiem`): thử nghiệm đủ `NGAY_THU` + 2 ngày → so trung vị lượt xem các video
  đăng TRONG thử nghiệm (đo hôm nay, tuổi ~2–9 ngày) với trung vị MỐC (đo lúc bắt đầu, tuổi ~1–8 ngày). Tụt quá
  `NGUONG_TUT` → TỰ TRẢ nhịp cũ + sự kiện não «tang-truong»; không tụt → giữ (ghi `dat`).

Sổ: `workspace/nhip-thu.json`. Không mạng, không LLM.

    python -m core.nhip_thu bat-dau TL2-T7 "05:00, 20:00" 2
    python -m core.nhip_thu xem
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Optional

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP = ("workspace", "nhip-thu.json")
NGAY_THU = 7
NGAY_MOC = 8
NGUONG_TUT = 0.75          # trung vị trong thử nghiệm < 75% mốc → trả nhịp cũ
SO_VIDEO_TOI_THIEU = 3
KHOA = ("nhip_dang", "video_moi_ngay", "video_toi_da_ngay")


def _duong(goc: str) -> str:
    return os.path.join(goc, *TEP)


def doc(goc: str) -> Dict[str, Any]:
    try:
        with open(_duong(goc), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi(goc: str, d: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_duong(goc)), exist_ok=True)
    tam = _duong(goc) + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tam, _duong(goc))


def _so(x: Any) -> float:
    s = "".join(c for c in str(x or "") if c.isdigit() or c == ".")
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _ngay(x: Any) -> Optional[_dt.date]:
    s = str(x or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def luot_xem(goc: str, kenh: str, tu: _dt.date, den: _dt.date) -> Dict[str, float]:
    """{video_id: lượt xem hiện tại} các video kênh đăng trong [tu, den) — từ `chi-so/bang-tom-tat.csv`."""
    p = os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv")
    ra: Dict[str, float] = {}
    try:
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                d = _ngay(r.get("Ngày đăng"))
                vid = str(r.get("Mã video") or "").strip()
                if vid and d and tu <= d < den:
                    ra[vid] = _so(r.get("Lượt xem"))
    except OSError:
        pass
    return ra


def _kenh_yaml(goc: str, kenh: str) -> Dict[str, Any]:
    from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
    return doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}


def bat_dau(goc: str, kenh: str, nhip: str, video_moi_ngay: int, bay_gio: Optional[_dt.date] = None) -> Dict[str, Any]:
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415

    hom = bay_gio or _dt.date.today()
    y = _kenh_yaml(goc, kenh)
    so = doc(goc)
    cu = so.get(kenh) if isinstance(so.get(kenh), dict) and so[kenh].get("trang_thai") == "dang_thu" else None
    luu = (cu or {}).get("cu") or {k: y.get(k) for k in KHOA}
    moc = luot_xem(goc, kenh, hom - _dt.timedelta(days=NGAY_MOC), hom)
    so[kenh] = {"trang_thai": "dang_thu", "bat_dau": hom.isoformat(), "nhip_moi": nhip,
                "video_moi_ngay": int(video_moi_ngay), "cu": luu, "moc": moc,
                "moc_trung_vi": statistics.median(moc.values()) if moc else None}
    _ghi(goc, so)
    ghi_cai_kenh(goc, kenh, nhip_dang=nhip, video_moi_ngay=int(video_moi_ngay),
                 video_toi_da_ngay=int(video_moi_ngay) + 1)
    return so[kenh]


def _tra_cu(goc: str, kenh: str, cu: Dict[str, Any]) -> None:
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415

    ghi_cai_kenh(goc, kenh, nhip_dang=cu.get("nhip_dang") or "",
                 video_moi_ngay=int(cu.get("video_moi_ngay") or 1),
                 video_toi_da_ngay=int(cu.get("video_toi_da_ngay") or 0))


def _bao_nao(goc: str, kenh: str, noi_dung: str) -> None:
    try:
        from . import nao_bo_phan as nbp  # noqa: PLC0415
        nbp.ghi(goc, "tang-truong", "ket_qua", noi_dung=noi_dung, khoa="nhip-thu:{0}".format(kenh), kenh=kenh)
    except Exception:  # noqa: BLE001 — não hỏng không chặn quyết định
        pass


def danh_gia(goc: str, bay_gio: Optional[_dt.date] = None) -> List[Dict[str, Any]]:
    """Đánh giá các thử nghiệm đã đủ ngày. Trả [{kenh, ket, ti_le, n, ly_do}] cho tự kiểm / báo cáo."""
    hom = bay_gio or _dt.date.today()
    so = doc(goc)
    ra: List[Dict[str, Any]] = []
    doi = False
    for kenh, m in so.items():
        if not isinstance(m, dict) or m.get("trang_thai") != "dang_thu":
            continue
        bd = _ngay(m.get("bat_dau"))
        if not bd or (hom - bd).days < NGAY_THU + 2:
            ra.append({"kenh": kenh, "ket": "dang_thu", "ly_do": "thử từ {0}, đánh giá sau {1} ngày".format(
                bd, NGAY_THU + 2)})
            continue
        thu = luot_xem(goc, kenh, bd, bd + _dt.timedelta(days=NGAY_THU))
        moc = m.get("moc_trung_vi")
        if len(thu) < SO_VIDEO_TOI_THIEU or not moc:
            m.update(trang_thai="dat", ket_luan="không đủ số liệu ({0} video, mốc {1}) — giữ nhịp mới".format(
                len(thu), moc), luc_ket=hom.isoformat())
            ra.append({"kenh": kenh, "ket": "dat", "ly_do": m["ket_luan"]})
            doi = True
            continue
        tv = statistics.median(thu.values())
        ti = tv / moc if moc else 1.0
        m.update(luc_ket=hom.isoformat(), trung_vi_thu=tv, ti_le=round(ti, 3), so_video_thu=len(thu))
        if ti < NGUONG_TUT:
            _tra_cu(goc, kenh, m.get("cu") or {})
            m.update(trang_thai="tra_lai", ket_luan="trung vị {0:.0f} < {1:.0%} mốc {2:.0f} → trả nhịp cũ".format(
                tv, NGUONG_TUT, moc))
            _bao_nao(goc, kenh, "bài học: nâng {0} lên {1} video/ngày làm lượt xem mỗi video tụt còn {2:.0%} — trả nhịp "
                     "cũ".format(kenh, m.get("video_moi_ngay"), ti))
        else:
            m.update(trang_thai="dat", ket_luan="trung vị {0:.0f} = {1:.0%} mốc {2:.0f} → giữ nhịp mới".format(tv, ti, moc))
            _bao_nao(goc, kenh, "bài học: {0} đăng {1} video/ngày giữ được lượt xem mỗi video ({2:.0%} mốc)".format(
                kenh, m.get("video_moi_ngay"), ti))
        ra.append({"kenh": kenh, "ket": m["trang_thai"], "ti_le": m["ti_le"], "n": len(thu), "ly_do": m["ket_luan"]})
        doi = True
    if doi:
        _ghi(goc, so)
    return ra


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    a = list(sys.argv[1:] if argv is None else argv)
    if a[:1] == ["bat-dau"] and len(a) >= 4:
        print(json.dumps(bat_dau(GOC, a[1], a[2], int(a[3])), ensure_ascii=False, indent=1)[:1500])
    elif a[:1] == ["danh-gia"]:
        print(json.dumps(danh_gia(GOC), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(doc(GOC), ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
