"""Sức khoẻ đường thu số Studio — đọc `CHANNEL/<k>/chi-so/` xem số liệu có THẬT không, có MỚI không.

═══ VÌ SAO CÓ MODULE NÀY (12/10/2026) ═══

Chẩn đoán `workspace/chan-doan/view-giam-2026-10-12.md` (mục 6) và `nao-vong-hoc-2026-10-12.md`
(mục 3): từ 06/10, 18–39% bản `tong-quan.json` rỗng; bản chụp video > 120h tuổi chỉ 17% có số;
TL2-T7 không có số toàn kênh từ 06/10. Không lớp nào kêu: `bang-tom-tat.csv` được VẼ LẠI mỗi khi
có gói về (kể cả gói rỗng) nên "tuổi số liệu" đo bằng mtime tệp ấy luôn mới; dòng "số liệu Studio
cũ 36–49 giờ" của `ho_so_video` chỉ nằm trong log.

Ở đây đo THẲNG trên bản chụp: bản nào có số (`impressions`/`views` khác None), chụp lúc nào THẬT
(`_thong-tin.json: chup_luc` của tiện ích ≥ 2.10, không có thì `captured_at` trong gói raw — không
bao giờ tin tên thư mục).

Bốn việc, đều chỉ ĐỌC (trừ `va_thu_muc_ma_bi_cat` — đổi tên thư mục, không xoá gì):

* :func:`doc_ban_chup` — từng bản chụp của một video: giờ chụp thật, tuổi thật, có số không.
* :func:`can_chup_bu` — video thiếu số mới → trạm trả cho tiện ích (`GET /chup-bu`) chụp bù đầu
  lượt quét, để mốc 72h/96h/7 ngày/14 ngày có thật cho mọi video.
* :func:`suc_khoe` — tuổi số toàn kênh / số video mới nhất + tỉ lệ video rỗng của lượt quét gần
  nhất → người gác (`core/gac_tong.py`) ghi `workspace/loi-chay-max.md`.
* :func:`va_thu_muc_ma_bi_cat` — trạm cũ cắt '-' đầu mã video (`-vidGiac99a` nằm trong
  `vidGiac99a`, mọi bộ đọc đòi tên 11 ký tự nên bỏ qua) → đổi về đúng tên.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import gom as _gom
from . import loc_video as _loc

__all__ = ["BanChup", "doc_ban_chup", "can_chup_bu", "suc_khoe", "va_thu_muc_ma_bi_cat",
           "MA_VIDEO", "GIO_CU_CHUP_BU", "TUOI_TOI_DA_CHUP_BU_NGAY"]

#: Mã video YouTube: đúng 11 ký tự [A-Za-z0-9_-] — CÓ THỂ bắt đầu/kết thúc bằng '-' hoặc '_'.
MA_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")

#: Video không có bản HỢP LỆ nào trong ngần này giờ thì vào danh sách chụp bù. Lượt quét chạy mỗi
#: ngày một lần (02:10–06:00, giờ kênh trôi tới ~1 giờ) — 20 giờ: lượt hôm qua không tính là "mới",
#: lượt thử lại trong cùng ngày (cách 45 phút) thì không chụp lại thứ vừa có.
GIO_CU_CHUP_BU = 20.0
#: Chỉ chụp bù video ≤ ngần này ngày tuổi — khớp mốc hằng ngày tới ngày 30 của tiện ích.
TUOI_TOI_DA_CHUP_BU_NGAY = 31
#: Video chưa tới ngần này giờ tuổi thì để báo thức mốc dày (6/13/18h…) của tiện ích lo.
TUOI_TOI_THIEU_CHUP_BU_GIO = 20.0
#: Cửa sổ quyết định (giờ tuổi) — thiếu số ở đây thì chụp bù TRƯỚC (vòng học chấm ≥ 96h).
CUA_SO_UU_TIEN_GIO = (60.0, 240.0)
#: Trần số video mỗi lượt chụp bù — giữ lượt quét trong khung chờ của agent.
TOI_DA_CHUP_BU = 40


@dataclass
class BanChup:
    """Một bản chụp `<video>/<nhãn>/` trên đĩa."""
    nhan: str
    thu_muc: str
    luc: Optional[float]            # epoch giây chụp THẬT (None = không biết)
    tuoi_gio: Optional[float]       # tuổi video lúc chụp (giờ, lẻ)
    co_so: bool                     # tong-quan.json có impressions hoặc views
    that: bool                      # có `_thong-tin.json` = lượt chụp thật của tiện ích (không phải gói lạc)
    hop_le_tien_ich: Optional[bool]  # cờ `hop_le` tiện ích ghi (None = tiện ích cũ chưa ghi)
    cho_giai_ma: bool               # có raw mà chưa có tong-quan.json


def _doc_json(p: str):
    try:
        with io.open(p, encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return None


def _iso_sang_epoch(s) -> Optional[float]:
    """ISO UTC của tiện ích (`2026-10-12T02:42:09.123Z`) → epoch giây."""
    try:
        t = _dt.datetime.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError):
        return None
    return t.replace(tzinfo=_dt.timezone.utc).timestamp()


def _co_so(tq: Optional[dict]) -> bool:
    return bool(tq) and (tq.get("impressions") is not None or tq.get("views") is not None)


def _co_so_kenh(tq: Optional[dict]) -> bool:
    """Số TOÀN KÊNH = có lượt xem hoặc giờ xem (hai thứ đường YPP cần). Chỉ có `subs` thì KHÔNG
    tính: gói `tab-build_audience` lạc nhãn của TL2-T7 12/10 mang mỗi số sub (310) — trông như có
    số kênh trong khi bảng YPP vẫn đứng ở 06/10."""
    return bool(tq) and any(tq.get(k) is not None for k in ("views", "watch_hours"))


def doc_ban_chup(thu_muc_video: str, dang_epoch: Optional[float] = None) -> List[BanChup]:
    """Mọi bản chụp của một video. `dang_epoch` (giờ đăng thật) không truyền thì tự đọc."""
    if dang_epoch is None:
        dang_epoch = _gom.dang_that_cua_video(thu_muc_video)
    ra: List[BanChup] = []
    try:
        ten_con = sorted(os.listdir(thu_muc_video))
    except OSError:
        return ra
    for nhan in ten_con:
        snap = os.path.join(thu_muc_video, nhan)
        if not os.path.isdir(snap):
            continue
        tt = _doc_json(os.path.join(snap, "_thong-tin.json"))
        tq = _doc_json(os.path.join(snap, "tong-quan.json"))
        raw = os.path.join(snap, "raw")
        co_raw = os.path.isdir(raw) and bool(os.listdir(raw))
        if tt is None and tq is None and not co_raw:
            continue                                   # chỉ còn ảnh — không phải bản chụp số
        co_so = _co_so(tq)
        # Giờ chụp: `chup_luc` của tiện ích ≥ 2.10 → mtime `_thong-tin.json` (trạm ghi ngay khi lượt
        # chụp xong — rẻ, không mở gói raw) → `captured_at` trong raw (chỉ cho bản có số mà không có
        # `_thong-tin.json`: gói lạc nhãn của đời tiện ích cũ). Người gác gọi hàm này mỗi 15 phút
        # cho mọi kênh, nên không mở hàng nghìn gói raw khi không cần.
        luc = _iso_sang_epoch(tt.get("chup_luc")) if tt else None
        if luc is None and tt is not None:
            try:
                luc = os.path.getmtime(os.path.join(snap, "_thong-tin.json"))
            except OSError:
                luc = None
        if luc is None and co_raw and co_so:
            luc = _gom._captured_at_that(snap)         # noqa: SLF001 — cùng gói, đọc captured_at thật
        tuoi = None
        if tt and tt.get("tuoi_gio_that") is not None:
            try:
                tuoi = float(tt["tuoi_gio_that"])
            except (TypeError, ValueError):
                tuoi = None
        if tuoi is None and luc is not None and dang_epoch is not None:
            tuoi = (luc - dang_epoch) / 3600.0
        hl = (tt or {}).get("hop_le")
        ra.append(BanChup(nhan=nhan, thu_muc=snap, luc=luc, tuoi_gio=tuoi,
                          co_so=co_so, that=tt is not None,
                          hop_le_tien_ich=hl if isinstance(hl, bool) else None,
                          cho_giai_ma=co_raw and tq is None))
    return ra


def _thu_muc_video(kenh_dir: str) -> List[str]:
    try:
        ten = sorted(os.listdir(kenh_dir))
    except OSError:
        return []
    return [os.path.join(kenh_dir, t) for t in ten
            if MA_VIDEO.match(t) and os.path.isdir(os.path.join(kenh_dir, t))]


def can_chup_bu(kenh_dir: str, *, bay_gio: Optional[float] = None, moc: str = "",
                cu_hon_gio: float = GIO_CU_CHUP_BU,
                tuoi_toi_da_ngay: float = TUOI_TOI_DA_CHUP_BU_NGAY,
                toi_da: int = TOI_DA_CHUP_BU) -> List[Dict]:
    """Video (trong phạm vi `moc` = `ngay_bat_dau`) tuổi `TUOI_TOI_THIEU_CHUP_BU_GIO`…`tuoi_toi_da_ngay`
    mà KHÔNG có bản chụp hợp lệ nào trong `cu_hon_gio` giờ qua → `[{video_id, tuoi_gio, ly_do}]`.

    Thứ tự: video CHƯA TỪNG có số → video đang ở cửa sổ quyết định (`CUA_SO_UU_TIEN_GIO`) → còn lại;
    cùng nhóm thì trẻ trước."""
    bay_gio = time.time() if bay_gio is None else float(bay_gio)
    ra = []
    for tm in _thu_muc_video(kenh_dir):
        dang = _gom.dang_that_cua_video(tm)
        if dang is None:
            continue
        tuoi = (bay_gio - dang) / 3600.0
        if tuoi < TUOI_TOI_THIEU_CHUP_BU_GIO or tuoi > tuoi_toi_da_ngay * 24:
            continue
        if moc and not _loc.trong_pham_vi(
                moc, _dt.datetime.fromtimestamp(dang, _dt.timezone.utc).strftime("%Y-%m-%d")):
            continue
        ban = doc_ban_chup(tm, dang)
        luc_so = [b.luc for b in ban if b.co_so and b.luc is not None]
        moi_nhat = max(luc_so) if luc_so else None
        if moi_nhat is not None and bay_gio - moi_nhat < cu_hon_gio * 3600:
            continue
        if moi_nhat is None:
            nhom, ly_do = 0, "chưa bản chụp nào có số"
        else:
            tuoi_so = (moi_nhat - dang) / 3600.0
            nhom = 1 if CUA_SO_UU_TIEN_GIO[0] <= tuoi <= CUA_SO_UU_TIEN_GIO[1] else 2
            ly_do = "bản có số mới nhất ở tuổi {0:.0f}h, cách đây {1:.0f}h".format(
                tuoi_so, (bay_gio - moi_nhat) / 3600.0)
        ra.append((nhom, tuoi, {"video_id": os.path.basename(tm), "tuoi_gio": round(tuoi, 1),
                                "ly_do": ly_do}))
    ra.sort(key=lambda x: (x[0], x[1]))
    return [x[2] for x in ra[:max(0, int(toi_da))]]


def _ngay_dia_phuong(epoch: float) -> str:
    return _dt.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d")


def suc_khoe(kenh_dir: str, *, bay_gio: Optional[float] = None, moc: str = "") -> Dict:
    """Ảnh chụp sức khoẻ số liệu một kênh (chỉ đọc):

    * `kenh_tuoi_gio` — giờ kể từ bản số TOÀN KÊNH (`kenh/*/tong-quan.json` có số) mới nhất;
      `None` khi chưa từng có. `co_thu_muc_kenh` = kênh đã từng có thư mục số toàn kênh.
    * `video_tuoi_gio` — giờ kể từ bản chụp VIDEO hợp lệ mới nhất (giờ chụp thật).
    * `luot_cuoi` — ngày quét gần nhất (ngày địa phương của lượt chụp THẬT mới nhất, có
      `_thong-tin.json`): `tong` video được chụp ngày ấy, `rong` video KHÔNG có bản nào có số ngày
      ấy (chụp lại trong ngày mà ra số thì không tính rỗng), `ti_le_rong`, `video_rong`.
      Bản có raw mà chưa giải mã thì chưa tính (đang chờ trạm giải mã).
    """
    bay_gio = time.time() if bay_gio is None else float(bay_gio)
    ra: Dict = {"kenh_tuoi_gio": None, "kenh_moi_nhat": None, "co_thu_muc_kenh": False,
                "video_tuoi_gio": None, "video_moi_nhat": None, "so_video": 0,
                "luot_cuoi": {"ngay": None, "tong": 0, "rong": 0, "ti_le_rong": None, "video_rong": []}}
    # ── số toàn kênh
    kd = os.path.join(kenh_dir, "kenh")
    if os.path.isdir(kd):
        try:
            cac = sorted(os.listdir(kd), reverse=True)
        except OSError:
            cac = []
        ra["co_thu_muc_kenh"] = any(c.startswith("kenh-") for c in cac)
        moi = None
        # Tên `kenh-YYYYMMDD` / `tay-YYYYMMDD` xếp ngược = mới trước: mỗi loại chỉ cần bản CÓ SỐ đầu
        # tiên (đọc `captured_at` của đúng một thư mục, không quét cả lịch sử).
        da_lay = set()
        for c in cac:
            loai = c.split("-", 1)[0]
            snap = os.path.join(kd, c)
            if loai in da_lay or not os.path.isdir(snap) \
                    or not _co_so_kenh(_doc_json(os.path.join(snap, "tong-quan.json"))):
                continue
            da_lay.add(loai)
            luc = _gom._captured_at_that(snap)         # noqa: SLF001
            if luc is not None and (moi is None or luc > moi):
                moi = luc
        if moi is not None:
            ra["kenh_moi_nhat"] = _dt.datetime.fromtimestamp(moi).isoformat(timespec="minutes")
            ra["kenh_tuoi_gio"] = round((bay_gio - moi) / 3600.0, 1)
    # ── số từng video
    moi_so = None
    theo_ngay: Dict[str, Dict[str, bool]] = {}         # ngày → {video: có bản có số}
    for tm in _thu_muc_video(kenh_dir):
        dang = _gom.dang_that_cua_video(tm)
        if moc and dang is not None and not _loc.trong_pham_vi(
                moc, _dt.datetime.fromtimestamp(dang, _dt.timezone.utc).strftime("%Y-%m-%d")):
            continue
        ra["so_video"] += 1
        vid = os.path.basename(tm)
        for b in doc_ban_chup(tm, dang):
            if b.co_so and b.luc is not None and (moi_so is None or b.luc > moi_so):
                moi_so = b.luc
            if not b.that or b.luc is None:
                continue                               # gói lạc (tay-*, nhãn sai) không phải một lượt chụp
            if b.cho_giai_ma and not b.co_so:
                continue
            ngay = _ngay_dia_phuong(b.luc)
            theo_ngay.setdefault(ngay, {})
            theo_ngay[ngay][vid] = theo_ngay[ngay].get(vid, False) or b.co_so
    if moi_so is not None:
        ra["video_moi_nhat"] = _dt.datetime.fromtimestamp(moi_so).isoformat(timespec="minutes")
        ra["video_tuoi_gio"] = round((bay_gio - moi_so) / 3600.0, 1)
    if theo_ngay:
        ngay = max(theo_ngay)
        bang = theo_ngay[ngay]
        rong = sorted(v for v, co in bang.items() if not co)
        ra["luot_cuoi"] = {"ngay": ngay, "tong": len(bang), "rong": len(rong),
                           "ti_le_rong": round(len(rong) / len(bang), 3) if bang else None,
                           "video_rong": rong}
    return ra


def _ma_that_trong(thu_muc_video: str) -> str:
    """Mã video 11 ký tự mà CÁC BẢN CHỤP bên trong tự khai (`_thong-tin.json: id`,
    `tong-quan.json: video_id`, hay `href` của gói raw)."""
    try:
        con = sorted(os.listdir(thu_muc_video))
    except OSError:
        return ""
    for nhan in con:
        snap = os.path.join(thu_muc_video, nhan)
        for ten, khoa in (("_thong-tin.json", "id"), ("tong-quan.json", "video_id")):
            d = _doc_json(os.path.join(snap, ten)) or {}
            ma = str(d.get(khoa) or "")
            if MA_VIDEO.match(ma):
                return ma
    return ""


def _gop_thu_muc(nguon: str, dich: str) -> None:
    """Dời mọi thứ trong `nguon` sang `dich`; trùng tên thư mục thì gộp đệ quy, trùng TỆP thì GIỮ
    bản ở `dich` và để nguyên bản ở `nguon` (không xoá dữ liệu nào)."""
    os.makedirs(dich, exist_ok=True)
    for ten in os.listdir(nguon):
        a, b = os.path.join(nguon, ten), os.path.join(dich, ten)
        if not os.path.exists(b):
            shutil.move(a, b)
        elif os.path.isdir(a) and os.path.isdir(b):
            _gop_thu_muc(a, b)
    try:
        os.rmdir(nguon)                                 # chỉ xoá khi đã RỖNG
    except OSError:
        pass


def va_thu_muc_ma_bi_cat(kenh_dir: str, ghi=None) -> int:
    """Trạm cũ (`tram.an_toan`: `.strip("-.")`) ghi video `-vidGiac99a` vào thư mục `vidGiac99a` (10 ký
    tự) — `cong_thuc_v7.video_cua_kenh`, `suc_khoe`, `can_chup_bu`… đều đòi tên 11 ký tự nên video ấy
    biến khỏi vòng học (D4 của chẩn đoán 12/10/2026). Đổi tên / gộp về đúng mã mà CHÍNH các bản chụp
    bên trong khai. Trả số thư mục đã sửa. Không xoá dữ liệu nào."""
    n = 0
    try:
        ten = sorted(os.listdir(kenh_dir))
    except OSError:
        return 0
    for t in ten:
        tm = os.path.join(kenh_dir, t)
        if MA_VIDEO.match(t) or t == "kenh" or t.startswith("_") or not os.path.isdir(tm):
            continue
        ma = _ma_that_trong(tm)
        if not ma or ma == t or ma.strip("-.") != t:
            continue
        dich = os.path.join(kenh_dir, ma)
        try:
            if os.path.exists(dich):
                _gop_thu_muc(tm, dich)
            else:
                os.rename(tm, dich)
            n += 1
            if ghi:
                ghi("sửa thư mục video mất dấu: {0} → {1}".format(t, ma))
        except OSError as loi:
            if ghi:
                ghi("không sửa được thư mục {0} → {1}: {2}".format(t, ma, loi))
    return n
