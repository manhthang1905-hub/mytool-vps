"""Sức khoẻ kênh = PHANH. Chạy TRƯỚC mọi việc; báo động thì giám đốc đóng băng, quay lui thay đổi
và báo chủ xem Studio (cảnh báo chính sách / nội dung dùng lại).

Ba cò (bất kỳ cò nào):
  1. hiển thị 7 ngày / trung vị ngày của 14 ngày trước < 0,65 trong khi vẫn đăng đều — TRỪ KHI video mới
     vẫn khoẻ (trung vị 48h của 3 video mới nhất ≥ trung vị kênh): đó là nhịp nguội tự nhiên sau một
     video nổ, không phải kênh bị phạt → chỉ "cảnh báo";
  2. ≥ 3 video mới nhất (có số 48h) đều dưới 30% trung vị hiển thị 48h của kênh;
  3. CTR @48h của 3 video mới nhất đều dưới 70% trung vị CTR các video trước (mọi video cùng tụt).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from .du_lieu import ban_chup_gan, chu_so, moc_cuoi_kenh, so_video_dang, trong_khoang, trung_vi

TEN = "suc_khoe"
MO_TA = "Canh sức khoẻ kênh (hiển thị sụp, video mới chết liên tiếp, CTR cùng tụt) — phanh của giám đốc"
NHIP = "ngay"
CHI_SO_CHINH = ""
NGUONG_HIEN_THI = 0.65
NGUONG_VIDEO_YEU = 0.30
SO_VIDEO_GAN = 3
NGUONG_CTR = 0.70
VIEC_CUA_BAN = ("Mở YouTube Studio xem kênh có cảnh báo chính sách, gậy, hay \"nội dung dùng lại\" không — "
                "giám đốc đã đóng băng mọi thay đổi tự động cho tới khi số hồi lại.")


def _tin_cay(n: int) -> str:
    return "thap" if n < 3 else "vua" if n < 6 else "cao"


def ap_dung(bs: Any) -> float:
    """Cần số kênh theo ngày hoặc ≥ 3 video có số."""
    return 1.0 if bs.kenh_ngay or len(bs.video) >= 3 else 0.0


def _co_hien_thi(bs: Any) -> Dict[str, Any]:
    cuoi = moc_cuoi_kenh(bs)
    if cuoi is None:
        return {"cau": "Chưa có số hiển thị cấp kênh (kenh-theo-ngay.csv).", "n": 0, "tin_cay": "thap"}
    if (bs.bay_gio - cuoi).days > 3:
        return {"cau": "Số kênh cũ {0} ngày (chụp cuối {1:%d/%m}) — chưa phán hiển thị.".format(
            (bs.bay_gio - cuoi).days, cuoi), "n": 0, "tin_cay": "thap"}
    mot = _dt.timedelta(days=1)
    h7 = trong_khoang(bs, "hien_thi", cuoi - 7 * mot, cuoi)
    ngay = [trong_khoang(bs, "hien_thi", cuoi - (8 + i) * mot, cuoi - (7 + i) * mot) for i in range(14)]
    if h7 is None or any(x is None for x in ngay):
        return {"cau": "Chưa đủ 21 ngày số kênh để so hiển thị 7 ngày với 14 ngày trước.",
                "n": len(bs.kenh_ngay), "tin_cay": "thap"}
    tv = trung_vi(ngay)
    ti = (h7 / 7.0) / tv if tv else None
    d7 = so_video_dang(bs, cuoi - 7 * mot, cuoi)
    d14 = so_video_dang(bs, cuoi - 21 * mot, cuoi - 7 * mot)
    deu = d7 > 0 and d7 / 7.0 >= 0.5 * d14 / 14.0
    return {"cau": "Hiển thị kênh 7 ngày qua {0} (≈{1}/ngày) = {2} trung vị/ngày của 14 ngày trước ({3}); "
                   "đăng {4} video/7 ngày, {5} video/14 ngày trước.".format(
                       chu_so(h7), chu_so(h7 / 7.0), "{0:.0%}".format(ti) if ti is not None else "?",
                       chu_so(tv), d7, d14),
            "n": 21, "tin_cay": "vua", "bao_dong": ti is not None and ti < NGUONG_HIEN_THI and deu}


def _co_video_yeu(bs: Any) -> Optional[Dict[str, Any]]:
    co48 = [v for v in bs.video if v.get("hien_thi_48h") is not None]
    if len(co48) < SO_VIDEO_GAN + 2:
        return None
    tv = trung_vi([v["hien_thi_48h"] for v in co48])
    gan = co48[:SO_VIDEO_GAN]
    ti = [v["hien_thi_48h"] / tv for v in gan] if tv else []
    return {"cau": "{0} video mới nhất có số 48h: {1} hiển thị = {2} trung vị 48h của kênh ({3}, n={4}).".format(
        SO_VIDEO_GAN, " / ".join(chu_so(v["hien_thi_48h"]) for v in gan),
        " / ".join("{0:.0%}".format(x) for x in ti), chu_so(tv), len(co48)),
        "n": len(co48), "tin_cay": _tin_cay(len(co48)), "bao_dong": bool(ti) and all(x < NGUONG_VIDEO_YEU for x in ti),
        "khoe": bool(ti) and trung_vi(ti) >= 1.0}


def _co_ctr(bs: Any) -> Optional[Dict[str, Any]]:
    ds = []
    for v in bs.video:
        b = ban_chup_gan(v, 48.0, 36.0, 60.0)
        if b and b.get("ctr") is not None:
            ds.append(b["ctr"])
    if len(ds) < SO_VIDEO_GAN + 4:
        return None
    tv = trung_vi(ds[SO_VIDEO_GAN:])
    gan = ds[:SO_VIDEO_GAN]
    return {"cau": "CTR @48h {0} video mới nhất: {1} — trung vị {2} video trước {3}.".format(
        SO_VIDEO_GAN, " / ".join(chu_so(c, 1, "%") for c in gan), len(ds) - SO_VIDEO_GAN, chu_so(tv, 1, "%")),
        "n": len(ds), "tin_cay": _tin_cay(len(ds)), "bao_dong": bool(tv) and all(c < NGUONG_CTR * tv for c in gan)}


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """Ba cò; mục nào `bao_dong` thì kèm `viec_cua_ban`."""
    h, v, c = _co_hien_thi(bs), _co_video_yeu(bs), _co_ctr(bs)
    if h.get("bao_dong") and v and v.get("khoe"):
        h["bao_dong"] = False
        h["cau"] = "CẢNH BÁO (không phanh) — " + h["cau"] + " Video mới vẫn khoẻ → nhịp nguội sau video nổ."
    ra = [q for q in (h, v, c) if q]
    for q in ra:
        if q.get("bao_dong"):
            q["cau"] = "BÁO ĐỘNG — " + q["cau"]
            q["viec_cua_ban"] = VIEC_CUA_BAN
    return ra


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Phanh không có thực đơn — báo động do vòng quyết định xử lý (đóng băng + quay lui)."""
    return []


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Không mở thí nghiệm."""
    return None


def bao_dong(qs: List[Dict[str, Any]]) -> bool:
    """Có cò nào báo động không."""
    return any(q.get("bao_dong") for q in qs)
