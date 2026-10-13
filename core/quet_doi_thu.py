"""**Quét content đối thủ không cần giao diện** — cùng một đường với nút "Quét đối thủ".

Nút ấy (ui_qt/trang_phan_tich._bat_dau_quet → _xong) làm bốn việc: lấy dữ liệu bằng yt-dlp →
GỘP vào `content.csv` (nối, giữ lịch sử view để tính "Tăng/ngày") → nuôi danh bạ (subs, dài,
view trung vị) → ghi mốc `quet_luc`. Bốn việc ấy nằm rải trong lớp Qt nên không gọi được từ
"một nút", từ dòng lệnh, hay từ lịch. Gom về đây; giao diện gọi lại hàm này.

13/10/2026 — quét theo TẦNG đối thủ (`so_doi_thu_chung.loc_quet`): mỗi kênh đối thủ một nhịp, nên lượt quét ghi thêm
mốc quét TỪNG kênh (`cai-dat.json` → `quet_kenh`) và `Tăng/ngày` của kênh lâu chưa quét chia cho đúng khoảng của nó.

Không import Qt. `lay` tách ra để test dựng dữ liệu giả không cần mạng.
"""

from __future__ import annotations

import statistics
import threading
import time
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so

__all__ = ["quet", "moc_quet_kenh", "GIU_MOC_KENH_NGAY"]


def _trung_vi(ds: Iterable[int]) -> int:
    ds = [int(x) for x in ds if x and int(x) > 0]
    return int(statistics.median(ds)) if ds else 0


def _phut_giay(giay: int) -> str:
    return "{0}:{1:02d}".format(giay // 60, giay % 60) if giay > 0 else ""


#: Mốc quét content TỪNG kênh đối thủ của sổ (`cai-dat.json` → `quet_kenh` = {khoá link: epoch}, 13/10/2026) — CHỈ
#: lượt quét content ghi (Quét lúc của danh bạ còn bị `chot` ghi khi chấm hộp thư mà không lấy content). Quét theo
#: tầng đối thủ (`so_doi_thu_chung.loc_quet`) đọc mốc này để biết kênh nào tới hạn. Giữ ngần này ngày.
GIU_MOC_KENH_NGAY = 60


def _khoa_kenh(ch: object) -> List[str]:
    """Mọi khoá link của một ảnh chụp kênh: link đưa vào lượt quét, link yt-dlp trả về, `/channel/UC…`."""
    cid = str(getattr(ch, "channel_id", "") or "")
    ks = [db.khoa(str(x or "")) for x in (getattr(ch, "input_url", ""), getattr(ch, "channel_url", ""),
                                          ("https://www.youtube.com/channel/" + cid) if cid else "")]
    return list(dict.fromkeys(k for k in ks if k))


def _doc_moc(cai: Dict) -> Dict[str, float]:
    m = (cai or {}).get("quet_kenh")
    ra: Dict[str, float] = {}
    if isinstance(m, dict):
        for k, v in m.items():
            try:
                ra[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
    return ra


def moc_quet_kenh(goc: str, kenh: str) -> Dict[str, float]:
    """`{khoá link (`danh_ba_doi_thu.khoa`): epoch lần quét content gần nhất của kênh đối thủ ấy}` của sổ `kenh`."""
    return _doc_moc(so.doc_cai(goc, kenh))


def _ngay_cach_theo_link(goc: str, kenh: str, ket: object, moi: Sequence[Sequence[str]],
                         moc: Dict[str, float], ngay_ca_so: float) -> Dict[str, float]:
    """`{Link video: số ngày từ lần quét content TRƯỚC của chính kênh đăng nó}` — chỉ kênh mà khoảng ấy DÀI hơn khoảng
    của cả sổ (`ngay_ca_so`): quét theo tầng đối thủ (13/10/2026) cho kênh tầng 3 tuần/lần, chia Δview cho 1 ngày của cả
    sổ là thổi `Tăng/ngày` lên 7×. Mốc: `quet_kenh` của sổ, thiếu thì Quét lúc của dòng danh bạ (đọc TRƯỚC khi lượt này
    ghi đè). Khoảng ngắn hơn của cả sổ thì không tin (Quét lúc vừa bị lượt chấm ghi) — giữ khoảng cả sổ như cũ."""
    import datetime as _dt  # noqa: PLC0415

    luc: Dict[str, float] = dict(moc)
    cot, hang = db.doc(goc, kenh)
    o = db.chi_so_cot(list(cot))
    i_l, i_q = o.get("Link kênh"), o.get("Quét lúc")
    if i_l is not None and i_q is not None:
        for d in hang:
            if i_l >= len(d) or i_q >= len(d):
                continue
            k = db.khoa(d[i_l])
            if not k or k in moc:
                continue
            try:
                t = time.mktime(_dt.datetime.strptime(str(d[i_q]).strip()[:16], "%Y-%m-%d %H:%M").timetuple())
            except ValueError:
                continue
            if t > luc.get(k, 0.0):
                luc[k] = t
    bay_gio = time.time()
    theo_ten: Dict[str, float] = {}
    for ins in getattr(ket, "insights", []) or []:
        k = ins.channel
        ts = [luc[x] for x in _khoa_kenh(k) if luc.get(x)]
        ten = str(getattr(k, "display_name", "") or "").strip()
        if ts and ten:
            ngay = max(0.0, (bay_gio - max(ts)) / 86400.0)
            if ngay > ngay_ca_so + 0.25:
                theo_ten[ten] = ngay
    if not theo_ten:
        return {}
    from .doi_thu import COT_VIDEO  # noqa: PLC0415

    i_k, i_v = COT_VIDEO.index("Kênh"), COT_VIDEO.index("Link video")
    ra: Dict[str, float] = {}
    for d in moi:
        ten = str(d[i_k]).strip() if i_k < len(d) else ""
        if ten in theo_ten and i_v < len(d):
            ra[str(d[i_v]).strip()] = theo_ten[ten]
    return ra


def quet(goc: str, kenh: str, links: Sequence[str], *, so_video: int = 60, lang: str = "",
         lay: Optional[Callable[..., object]] = None,
         cancel: Optional[threading.Event] = None,
         on_log: Optional[Callable[[str], None]] = None) -> Dict[str, int]:
    """Quét `links` (mỗi phần tử một link kênh) → gộp vào sổ content + danh bạ.

    Trả `{"kenh", "video", "dong_truoc", "dong_sau"}`. Không có link → không đụng sổ.
    """
    def log(m):
        if on_log is not None:
            on_log(m)

    links = [str(l).strip() for l in links if str(l).strip()]
    dem = {"kenh": 0, "video": 0, "dong_truoc": 0, "dong_sau": 0}
    if not links:
        return dem
    if lay is None:
        from .doi_thu import lay_du_lieu  # noqa: PLC0415 — yt-dlp chỉ nạp khi cần

        lay = lay_du_lieu
    ket = lay("\n".join(links), so_video=so_video, mo_rong=False, chi_tiet=False, cancel=cancel,
              lang=lang, on_log=on_log)
    moi = ket.bang_video()
    dem["video"] = len(moi)
    dem["kenh"] = len(getattr(ket, "insights", []) or [])
    if not moi:
        log("  quét đối thủ: không lấy được video nào")
        return dem
    cot, cu = so.doc_bang(goc, kenh)
    dem["dong_truoc"] = len(cu)
    ngay_cach = 0.0
    cai = so.doc_cai(goc, kenh)
    truoc = cai.get("quet_luc")
    try:
        if truoc:
            ngay_cach = max(0.0, (time.time() - float(truoc)) / 86400.0)
    except (TypeError, ValueError):
        pass
    moc = _doc_moc(cai)
    try:
        ngay_link = _ngay_cach_theo_link(goc, kenh, ket, moi, moc, ngay_cach)
    except Exception:  # noqa: BLE001 — thiếu thì dùng mốc của cả sổ như cũ
        ngay_link = {}
    gop = so.gop_bang(cot, cu, moi, ngay_cach_nhau=ngay_cach, ngay_cach_theo_link=ngay_link or None)
    # Nuôi danh bạ trước, sổ content sau — cùng thứ tự với giao diện. Danh bạ hỏng không
    # giết lượt quét: sổ content là thứ chính.
    try:
        ban_ghi = []
        for ins in getattr(ket, "insights", []) or []:
            k = ins.channel
            ban_ghi.append(db.BanGhi(
                ten=k.display_name, link=k.channel_url, subs=k.subscribers, so_video=len(k.videos),
                dai_tv=_phut_giay(_trung_vi(v.duration_s for v in k.videos)),
                view_tv=_trung_vi(v.views for v in k.videos),
                vuot_quy_mo=float(getattr(ins, "best_ratio", 0.0) or 0.0)))
        if ban_ghi:
            c2, h2 = db.doc(goc, kenh)
            db.luu(goc, kenh, c2, db.gop_cham(c2, h2, ban_ghi))
    except Exception as loi:  # noqa: BLE001
        log("  không cập nhật được danh bạ: {0}".format(loi))
    so.luu_bang(goc, kenh, cot, gop)
    bay_gio = time.time()
    for ins in getattr(ket, "insights", []) or []:
        for k in _khoa_kenh(ins.channel):
            moc[k] = bay_gio
    moc = {k: round(v) for k, v in moc.items() if bay_gio - v < GIU_MOC_KENH_NGAY * 86400}
    so.luu_cai(goc, kenh, quet_luc=bay_gio, quet_kenh=moc)
    dem["dong_sau"] = len(gop)
    log("  quét đối thủ: {0} kênh · {1} video · sổ {2} → {3} dòng".format(
        dem["kenh"], dem["video"], dem["dong_truoc"], dem["dong_sau"]))
    return dem
