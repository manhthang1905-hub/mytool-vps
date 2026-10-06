"""Clip TỪ ẢNH cảnh (Ken Burns) — đường lùi khi engine clip hết hạn mức.

═══ LUẬT (06/10/2026) ═══

Clip engine báo hết hạn mức/không khả dụng mà đã tới hạn chót (giờ đăng của gói
trừ `han_clip_truoc_gio_dang` giờ, mặc định 6) thì cảnh nào thiếu clip được dựng
từ chính ảnh cảnh đó bằng chuyển động máy nhẹ, đúng độ dài cảnh. Trước hạn chót
thì vẫn chờ engine.

═══ VÌ SAO ═══

06/10/2026 08:08 cổng trả mọi job clip `503 engine_unavailable` *"Kho tài khoản
video đã dùng hết hạn mức credit hôm nay…"*. Bốn kênh đang làm video đăng 05:00
hôm sau có 0–41 clip trên ~90–155 cảnh. Khâu dựng chịu thiếu vài clip (cảnh
trước giữ hình), nhưng thiếu cả trăm là video đứng hình hàng phút — hoặc
"chưa có clip nào, không dựng được". Ảnh cảnh thì đã có đủ, đã trả tiền.

═══ CÁCH DỰNG ═══

* Khổ và nhịp khung đọc từ một clip THẬT của chính gói (đo 06/10: 1280×720,
  24 hình/giây, H.264 High yuv420p, AAC 48 kHz) — không có thì lấy đúng số ấy.
  Cùng khổ + cùng nhịp thì đường dựng "một lần nén" vẫn nhận (`_dieu_kien_mot_lan`).
* Ảnh được phủ kín khung (phóng rồi cắt, không viền đen), phóng ×2 trước khi
  `zoompan` để chuyển động không giật theo từng điểm ảnh.
* Kiểu chuyển động chọn theo số cảnh (`so_canh % 4`): đẩy vào, lia phải, đẩy vào,
  lia trái — xen kẽ, cố định (chạy lại ra đúng clip ấy).
* Có rãnh tiếng câm như clip thật — đường dựng nào cũng đọc được.

Không mạng, không Qt. FFmpeg đi qua hàm bơm được (`chay`).
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import re
import subprocess
import time
from typing import Any, Callable, ContextManager, Dict, List, Optional, Sequence, Tuple

__all__ = ["tao", "khuon_clip", "han_chot", "gio_truoc", "giay_canh", "bu_canh_thieu",
           "doc_danh_dau", "TEP_DANH_DAU", "KHUON_MAC_DINH", "GIAY_THAM_DO", "HAN_MAC_DINH_GIO"]

#: Khổ/nhịp của clip engine thật (đo 06/10/2026 trên `6-clip/*.mp4`).
KHUON_MAC_DINH = (1280, 720, 24)
#: Danh sách cảnh dựng từ ảnh của một gói — `6-clip/tu-anh.json`.
TEP_DANH_DAU = "tu-anh.json"
#: Chờ engine: thăm dò một lần mỗi ngần này giây (trước hạn chót).
GIAY_THAM_DO = 20 * 60
#: `kenh.yaml: han_clip_truoc_gio_dang` khi không khai.
HAN_MAC_DINH_GIO = 6.0
#: Phóng ảnh lên ngần này lần trước `zoompan` (chống giật theo điểm ảnh).
_PHONG = 2
#: Đẩy vào tới 1,08; lia ở mức phóng 1,08 — "chuyển động máy nhẹ".
_ZOOM = 0.08

_RE_KHO = re.compile(r"Video:.*?\b(\d{2,5})x(\d{2,5})\b")
_RE_FPS = re.compile(r"Video:.*?(\d+(?:\.\d+)?) fps")


def _co_tao() -> int:
    """Ẩn cửa sổ + hạ ưu tiên FFmpeg (cùng lý do `auto_khau._co_tao_ffmpeg`)."""
    return (getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))


def _loc(kieu: int, n: int, rong: int, cao: int, fps: int) -> str:
    """Chuỗi lọc: phủ kín khung → phóng ×2 → zoompan `n` khung → yuv420p."""
    rp, cp = rong * _PHONG, cao * _PHONG
    phu = ("scale={0}:{1}:force_original_aspect_ratio=increase,crop={0}:{1},setsar=1"
           .format(rp, cp))
    tien = "on/{0}".format(max(1, n - 1))          # 0 → 1 suốt clip
    if kieu % 2 == 0:       # đẩy vào giữa khung
        z = "1+{0}*{1}".format(_ZOOM, tien)
        x = "iw/2-(iw/zoom/2)"
    else:                   # lia ngang ở mức phóng cố định
        z = "{0}".format(1 + _ZOOM)
        x = ("(iw-iw/zoom)*{0}" if kieu % 4 == 1 else "(iw-iw/zoom)*(1-{0})").format(tien)
    y = "ih/2-(ih/zoom/2)"
    zp = "zoompan=z='{0}':x='{1}':y='{2}':d={3}:s={4}x{5}:fps={6}".format(
        z, x, y, n, rong, cao, fps)
    # Ảnh cảnh là JPEG (dải màu ĐẦY, yuvj420p); clip engine là yuv420p dải TV —
    # ép về dải TV để ghép chung không lệch sáng/tối giữa hai loại clip.
    return "{0},{1},scale=out_range=tv,format=yuv420p,setsar=1".format(phu, zp)


def tao(anh: str, ra_mp4: str, giay: float, ffmpeg: str, *, kieu: int = 0,
        khuon: Tuple[int, int, int] = KHUON_MAC_DINH,
        chay: Callable[..., Any] = subprocess.run) -> str:
    """Dựng `ra_mp4` dài `giay` giây từ ảnh `anh`. Trả `ra_mp4`.

    Ghi ra tệp tạm rồi `os.replace` — hỏng giữa chừng không để lại `<n>.mp4` dở
    (khâu dựng sẽ tưởng là clip thật)."""
    rong, cao, fps = (int(khuon[0]), int(khuon[1]), int(khuon[2]))
    n = max(1, int(round(max(0.1, float(giay)) * fps)))
    tam = ra_mp4 + ".tam.mp4"
    os.makedirs(os.path.dirname(os.path.abspath(ra_mp4)) or ".", exist_ok=True)
    lenh = [ffmpeg, "-y", "-hide_banner", "-nostats", "-loglevel", "error",
            "-i", anh,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex", "[0:v]{0}[v]".format(_loc(kieu, n, rong, cao, fps)),
            "-map", "[v]", "-map", "1:a",
            "-frames:v", str(n), "-t", "{0:.3f}".format(n / float(fps)),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-profile:v", "high",
            "-pix_fmt", "yuv420p", "-color_range", "tv", "-r", str(fps),
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", tam]
    ket = chay(lenh, capture_output=True, text=True, encoding="utf-8", errors="replace",
               creationflags=_co_tao())
    if getattr(ket, "returncode", 1) != 0 or not os.path.isfile(tam):
        try:
            os.remove(tam)
        except OSError:
            pass
        raise RuntimeError("dựng clip từ ảnh hỏng: {0}".format(
            str(getattr(ket, "stderr", "") or "")[-300:]))
    os.replace(tam, ra_mp4)
    return ra_mp4


def khuon_clip(ffmpeg: str, thu_muc_clip: str, bo_qua: Sequence[int] = (),
               chay: Callable[..., Any] = subprocess.run) -> Tuple[int, int, int]:
    """(rộng, cao, hình/giây) của MỘT clip thật trong gói; không có → `KHUON_MAC_DINH`."""
    bo = {"{0}.mp4".format(int(x)) for x in bo_qua}
    try:
        ten = sorted((t for t in os.listdir(thu_muc_clip)
                      if re.fullmatch(r"\d+\.mp4", t) and t not in bo),
                     key=lambda t: int(t[:-4]))
    except OSError:
        ten = []
    for t in ten[:3]:
        try:
            tho = chay([ffmpeg, "-hide_banner", "-i", os.path.join(thu_muc_clip, t)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60, creationflags=_co_tao())
        except (OSError, subprocess.SubprocessError):
            continue
        chu = str(getattr(tho, "stderr", "") or "")
        k, f = _RE_KHO.search(chu), _RE_FPS.search(chu)
        if k and f:
            fps = int(round(float(f.group(1))))
            if fps > 0:
                return int(k.group(1)), int(k.group(2)), fps
    return KHUON_MAC_DINH


# ── Hạn chót ────────────────────────────────────────────────────────────────


def gio_truoc(kenh: Any) -> float:
    """`han_clip_truoc_gio_dang` của kênh (giờ, ≥ 0); thiếu/hỏng → 6."""
    try:
        v = getattr(kenh, "han_clip_truoc_gio_dang", HAN_MAC_DINH_GIO)
        return max(0.0, float(HAN_MAC_DINH_GIO if v is None else v))
    except (TypeError, ValueError):
        return HAN_MAC_DINH_GIO


def han_chot(goc: str, kenh: Any, *, bay_gio: Optional[_dt.datetime] = None
             ) -> Tuple[Optional[_dt.datetime], Optional[_dt.datetime]]:
    """(hạn chót, giờ đăng) của gói đang sản xuất; kênh không có giờ đăng → (None, None).

    Giờ đăng = khe công khai trống SỚM NHẤT của kênh tính từ bây giờ (biên 0) —
    cùng cách `dieu_phoi.uu_tien_khau` tính độ gấp. Biên 0 thì khe chỉ dời khi
    nó đã TRÔI QUA, nên hạn chót (khe − N giờ) luôn tới trước khi khe dời."""
    from . import xep_lich  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    try:
        ngay, gio = xep_lich.khe_trong_som_nhat(goc, str(getattr(kenh, "ma", "") or ""), kenh,
                                                bay_gio=bay_gio, bien_gio=0)
    except Exception:  # noqa: BLE001 — đọc lịch hỏng thì coi như không có hạn
        return None, None
    if not ngay:
        return None, None
    try:
        moc = _dt.datetime.strptime(ngay + " " + gio, "%d/%m/%Y %H:%M")
    except ValueError:
        return None, None
    return moc - _dt.timedelta(hours=gio_truoc(kenh)), moc


# ── Độ dài cảnh ─────────────────────────────────────────────────────────────


def _giay(t: Any) -> Optional[float]:
    try:
        h, m, s = str(t).strip().replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, AttributeError):
        return None


def giay_canh(canh: Sequence[Dict[str, Any]], i: int) -> float:
    """Độ dài cảnh `i` TRÊN DÒNG THỜI GIAN — đúng khoảng khâu dựng cấp cho nó:
    từ `srt_start` của nó tới `srt_start` cảnh sau (cảnh cuối: tới `srt_end`).
    Không đọc được mốc thì lấy `duration`. Tối thiểu 1 giây."""
    c = canh[i]
    dau = _giay(c.get("srt_start"))
    sau = _giay(canh[i + 1].get("srt_start")) if i + 1 < len(canh) else _giay(c.get("srt_end"))
    if dau is not None and sau is not None and sau > dau:
        return max(1.0, sau - dau)
    try:
        return max(1.0, float(c.get("duration") or 0))
    except (TypeError, ValueError):
        return 1.0


# ── Bù cảnh thiếu ───────────────────────────────────────────────────────────


def doc_danh_dau(thu_muc_clip: str) -> Dict[str, Any]:
    try:
        with open(os.path.join(thu_muc_clip, TEP_DANH_DAU), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_danh_dau(thu_muc_clip: str, moi: List[int], tong: int, ly_do: str,
                  han: Optional[_dt.datetime]) -> Dict[str, Any]:
    cu = doc_danh_dau(thu_muc_clip)
    canh = sorted({int(x) for x in (cu.get("canh") or [])} | set(moi))
    du = {"canh": canh, "tong": int(tong), "ly_do": str(ly_do)[:300],
          "luc": _dt.datetime.now().replace(microsecond=0).isoformat(),
          "han_chot": han.replace(microsecond=0).isoformat() if han else ""}
    duong = os.path.join(thu_muc_clip, TEP_DANH_DAU)
    with open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)
    return du


def bu_canh_thieu(thu_muc_luot: str, canh: Sequence[Dict[str, Any]], ffmpeg: str, *,
                  ly_do: str, ghi: Callable[[str], None],
                  kiem_dung: Callable[[], None] = lambda: None,
                  han: Optional[_dt.datetime] = None, gio_dang: Optional[_dt.datetime] = None,
                  giu_khe: Optional[Callable[[], ContextManager[Any]]] = None,
                  chay: Callable[..., Any] = subprocess.run) -> List[int]:
    """Dựng clip từ ảnh cho MỌI cảnh chưa có `6-clip/<n>.mp4` mà có `5-anh/<n>.png`.

    Giữ khe máy nặng (`giu_khe`) suốt lúc chạy FFmpeg; ghi `6-clip/tu-anh.json`
    và MỘT dòng nhật ký. Trả danh sách số cảnh vừa dựng."""
    canh = list(canh)
    thu_muc_anh = os.path.join(thu_muc_luot, "5-anh")
    thu_muc_clip = os.path.join(thu_muc_luot, "6-clip")
    os.makedirs(thu_muc_clip, exist_ok=True)
    viec = []
    for i, c in enumerate(canh):
        so = int(c["scene_id"])
        if os.path.exists(os.path.join(thu_muc_clip, "{0}.mp4".format(so))):
            continue
        anh = os.path.join(thu_muc_anh, "{0}.png".format(so))
        if os.path.isfile(anh):
            viec.append((so, anh, giay_canh(canh, i)))
    if not viec:
        return []
    da_lam: List[int] = []
    bat_dau = time.time()
    with (giu_khe() if giu_khe is not None else contextlib.nullcontext()):
        khuon = khuon_clip(ffmpeg, thu_muc_clip, bo_qua=doc_danh_dau(thu_muc_clip).get("canh") or (),
                           chay=chay)
        for so, anh, giay in viec:
            kiem_dung()
            try:
                tao(anh, os.path.join(thu_muc_clip, "{0}.mp4".format(so)), giay, ffmpeg,
                    kieu=so % 4, khuon=khuon, chay=chay)
            except Exception as loi:  # noqa: BLE001 — một cảnh hỏng không chặn cả gói
                ghi("    cảnh {0}: dựng clip từ ảnh hỏng ({1}) — để trống, cảnh trước giữ "
                    "hình.".format(so, str(loi)[:120]))
                continue
            da_lam.append(so)
    if da_lam:
        du = _ghi_danh_dau(thu_muc_clip, da_lam, len(canh), ly_do, han)
        ghi("  [CLIP TỪ ẢNH] {0} — đã tới hạn chót {1}{2}: dựng {3} cảnh thiếu từ ảnh "
            "(chuyển động máy nhẹ, {4}×{5}/{6}fps) trong {7:.0f} giây; tổng {8}/{9} cảnh "
            "của video là clip từ ảnh.".format(
                str(ly_do)[:120], han.strftime("%d/%m %H:%M") if han else "?",
                " (giờ đăng {0})".format(gio_dang.strftime("%d/%m %H:%M")) if gio_dang else "",
                len(da_lam), khuon[0], khuon[1], khuon[2], time.time() - bat_dau,
                len(du["canh"]), len(canh)))
    return da_lam
