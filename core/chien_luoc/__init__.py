"""Bộ máy chiến lược chọn nguồn — sổ đăng ký công thức + bộ điều phối.

Mỗi tệp `core/chien_luoc/<ten>.py` KHÔNG bắt đầu bằng `_` là MỘT công thức (hợp đồng: `TEN`, `MO_TA`,
`LUI_KHI_RONG`, `ap_dung(nc) -> 0..1`, `cham(nc) -> list[dòng chuẩn]`), tự phát hiện bằng
`pkgutil.iter_modules`. Tệp nhập hỏng → log + bỏ qua, không kéo đổ cả bộ chọn nguồn.
Thêm công thức: chép `_mau.py` — xem `docs/CHIEN-LUOC.md`.

kenh.yaml (phẳng — `kenh.doc_yaml` tối giản không đọc khoá lồng):

    chien_luoc: "vph:0.7, v7:0.3"   # hoặc "tu_dong"; KHÔNG khai → luật cũ `cong_thuc_chon`, y hệt trước
    chien_luoc_tham_do: 20          # % lượt thăm dò (mặc định 20)
    chien_luoc_tu_hoc: false        # true → dồn tỉ trọng theo kết quả thật (cần ≥ 6 video đã đo)

Tất định: cùng đĩa + cùng ngày + cùng số lượt đã mở → cùng bảng, để trạm `/loi-thoai/can-lay` và
vòng chọn nguồn thấy MỘT bảng (không dùng số ngẫu nhiên, không dùng `hash()` của Python — hàm ấy
đổi hạt giống mỗi tiến trình).
"""

from __future__ import annotations

import hashlib
import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

#: Module trong gói không phải công thức.
_KHONG_PHAI_CONG_THUC = {"ngu_canh", "bai_hoc", "ket_qua", "__main__"}
#: Thứ tự hiển thị các công thức gốc (giữ đúng thứ tự `tu_chay.CONG_THUC_NGUON` cũ).
_THU_TU_GOC = ("v7", "vph", "mot_nut")
KHOA_CHIEN_LUOC = "chien_luoc"
KHOA_THAM_DO = "chien_luoc_tham_do"
KHOA_TU_HOC = "chien_luoc_tu_hoc"
THAM_DO_MAC_DINH = 20
TU_DONG_TRONG_SO = (0.8, 0.2)
TU_HOC_KEP = (0.1, 0.9)
TU_HOC_N_TOI_THIEU = 6
THAM_DO_SO_NGAY = 14

_SO: Optional[Dict[str, ModuleType]] = None


def so_dang_ky(tai_lai: bool = False) -> Dict[str, ModuleType]:
    """`{TEN: module}` của mọi công thức nạp được (nhớ sau lần đầu)."""
    global _SO
    if _SO is not None and not tai_lai:
        return _SO
    tim: Dict[str, ModuleType] = {}
    for mi in pkgutil.iter_modules(__path__):
        if mi.name.startswith("_") or mi.name in _KHONG_PHAI_CONG_THUC:
            continue
        try:
            m = importlib.import_module("{0}.{1}".format(__name__, mi.name))
        except Exception as loi:  # noqa: BLE001 — một tệp hỏng không được kéo đổ bộ chọn nguồn
            _log.warning("chien_luoc: bỏ qua công thức %s (nhập hỏng: %s)", mi.name, loi)
            continue
        ten = str(getattr(m, "TEN", "") or "")
        if not ten or not callable(getattr(m, "cham", None)) or not callable(getattr(m, "ap_dung", None)):
            _log.warning("chien_luoc: %s thiếu TEN/cham/ap_dung — bỏ qua", mi.name)
            continue
        tim[ten] = m
    thu_tu = [t for t in _THU_TU_GOC if t in tim] + sorted(t for t in tim if t not in _THU_TU_GOC)
    _SO = {t: tim[t] for t in thu_tu}
    return _SO


def mo_ta_cong_thuc() -> Dict[str, str]:
    """`{TEN: MO_TA}` — nguồn của `tu_chay.CONG_THUC_NGUON`."""
    return {t: str(getattr(m, "MO_TA", "") or t) for t, m in so_dang_ky().items()}


def loc_chung(nc: Any, ds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bộ lọc chung (loai_tru + trùng tiêu đề) — `nc.loc`, để ngỏ tên cho công thức ngoài gói."""
    return nc.loc(ds)


def _ap_dung(m: ModuleType, nc: Any) -> float:
    try:
        return max(0.0, min(1.0, float(m.ap_dung(nc) or 0)))
    except Exception as loi:  # noqa: BLE001
        nc.ghi("  (công thức {0}: ap_dung hỏng — {1}; coi như 0)".format(
            getattr(m, "TEN", "?"), str(loi)[:100]))
        return 0.0


# ── kế hoạch ────────────────────────────────────────────────────────────────

@dataclass
class KeHoach:
    trong_so: Dict[str, float]
    ly_do: str = ""
    #: True = kênh KHÔNG khai `chien_luoc` → một công thức theo luật cũ, bảng y hệt trước.
    cu: bool = True
    tham_do: str = ""
    ghi_chu: List[str] = field(default_factory=list)


def _phan_tich(chuoi: str) -> List[Tuple[str, float]]:
    ra: List[Tuple[str, float]] = []
    for manh in chuoi.replace(";", ",").split(","):
        manh = manh.strip()
        if not manh:
            continue
        ten, _, w = manh.partition(":")
        try:
            ts = float(w) if w.strip() else 1.0
        except ValueError:
            ts = -1.0
        ra.append((ten.strip().lower(), ts))
    return ra


def _chuan_hoa(ts: Dict[str, float]) -> Dict[str, float]:
    tong = sum(ts.values())
    return {k: v / tong for k, v in ts.items()} if tong > 0 else {}


def _so_tham_do(nc: Any) -> int:
    """0..99 tất định theo kênh | ngày | số lượt đã mở hôm nay."""
    khoa = "{0}|{1}|{2}".format(nc.ma_kenh, nc.bay_gio.date().isoformat(), nc.so_luot_hom_nay)
    return int(hashlib.sha1(khoa.encode("utf-8")).hexdigest(), 16) % 100


def ke_hoach(nc: Any, *, tham_do: Optional[bool] = None) -> KeHoach:
    """Tỉ trọng các công thức cho lượt này. `tham_do=False` ép lượt KHAI THÁC (nơi gọi lùi khi lượt thăm
    dò không có nguồn qua cổng), `None` = tự tính."""
    from .. import tu_chay  # noqa: PLC0415 — nhập muộn: tu_chay nạp gói này lúc khởi động

    so = so_dang_ky()
    cau = str(nc.cai(KHOA_CHIEN_LUOC, "") or "").strip()
    if not cau:
        ten, ly = tu_chay.chon_cong_thuc(nc.goc, nc.ma_kenh, nc.co_v7)
        return KeHoach({ten: 1.0}, ly, cu=True)

    ghi_chu: List[str] = []
    ts: Dict[str, float] = {}
    if cau.lower() == "tu_dong":
        diem = sorted(((_ap_dung(m, nc), t) for t, m in so.items()), key=lambda x: (-x[0], x[1]))
        if diem and diem[0][0] > 0:
            ts[diem[0][1]] = TU_DONG_TRONG_SO[0]
            if len(diem) > 1 and diem[1][0] > 0:
                ts[diem[1][1]] = TU_DONG_TRONG_SO[1]
        ly = "tu_dong theo giai đoạn “{0}”".format(nc.giai_doan)
    else:
        for ten, w in _phan_tich(cau):
            if ten not in so:
                ghi_chu.append("bỏ “{0}” (không có công thức tên này)".format(ten))
            elif w <= 0:
                ghi_chu.append("bỏ “{0}” (tỉ trọng không hợp lệ)".format(ten))
            elif _ap_dung(so[ten], nc) <= 0:
                ghi_chu.append("bỏ “{0}” (chưa dùng được cho kênh này)".format(ten))
            else:
                ts[ten] = ts.get(ten, 0.0) + w
        ly = "kenh.yaml {0}: {1}".format(KHOA_CHIEN_LUOC, cau)
    ts = _chuan_hoa(ts)
    if not ts:
        ten, ly_cu = tu_chay.chon_cong_thuc(nc.goc, nc.ma_kenh, nc.co_v7)
        ghi_chu.append("chiến lược “{0}” không còn công thức dùng được — luật cũ".format(cau))
        return KeHoach({ten: 1.0}, ly_cu, cu=True, ghi_chu=ghi_chu)

    if nc.cai(KHOA_TU_HOC, False) is True and len(ts) >= 2:
        kq = nc.ket_qua_cong_thuc
        n_tong = sum(int((kq.get(t) or {}).get("n") or 0) for t in ts)
        if n_tong >= TU_HOC_N_TOI_THIEU:
            he = {t: (int((kq.get(t) or {}).get("thang") or 0) + 1) / (int((kq.get(t) or {}).get("n") or 0) + 2)
                  for t in ts}
            tb = sum(he.values()) / len(he)
            ts = _chuan_hoa({t: min(TU_HOC_KEP[1], max(TU_HOC_KEP[0], w * he[t] / tb)) for t, w in ts.items()})
            ghi_chu.append("tự học trên {0} video đã đo".format(n_tong))

    kh = KeHoach(ts, ly, cu=False, ghi_chu=ghi_chu)
    if len(ts) >= 2 and tham_do is not False:
        try:
            ty_le = int(float(nc.cai(KHOA_THAM_DO, THAM_DO_MAC_DINH)))
        except (TypeError, ValueError):
            ty_le = THAM_DO_MAC_DINH
        if tham_do is True or _so_tham_do(nc) < ty_le:
            # Số video mỗi công thức đã RA trong 14 ngày (`ket_qua.thong_ke` → `lam`: nối sổ lượt với
            # hồ sơ video, tính cả video chưa đủ 48h — để công thức vừa được thăm dò hôm qua không bị
            # chọn lại chỉ vì chưa có kết luận). Bảng kết quả cũ chỉ có `n` thì dùng `n`.
            kq14 = nc.ket_qua(THAM_DO_SO_NGAY)
            thu_tu = list(ts)

            def _so_video(t: str) -> int:
                o = kq14.get(t) or {}
                return int(o.get("lam", o.get("n")) or 0)

            kh.tham_do = min(ts, key=lambda t: (_so_video(t), ts[t], thu_tu.index(t)))
    return kh


# ── xếp hạng ────────────────────────────────────────────────────────────────

def _bang(nc: Any, ten: str, cam: Tuple[str, ...] = ()) -> Tuple[List[Dict[str, Any]], str]:
    """Bảng của một công thức (qua `nc.loc`), rỗng thì theo `LUI_KHI_RONG` — không lùi vào công thức
    trong `cam` (đã có mặt trong kế hoạch, hoặc đã thử). Trả `(bảng, tên công thức đã ra bảng)`."""
    so = so_dang_ky()
    m = so.get(ten)
    if m is None:
        nc.ghi("  (không nạp được công thức “{0}” — dùng bảng Một nút)".format(ten))
        m = so.get("mot_nut")
        if m is None or "mot_nut" in cam:
            return [], ten
        ten = "mot_nut"
    try:
        ds = nc.loc(m.cham(nc) or [])
    except Exception as loi:  # noqa: BLE001 — một công thức hỏng không được đứng kênh
        nc.ghi("  (công thức {0} hỏng: {1})".format(ten, str(loi)[:120]))
        ds = []
    lui = str(getattr(m, "LUI_KHI_RONG", "") or "")
    if ds or not lui or lui == ten or lui in cam:
        return ds, ten
    return _bang(nc, lui, cam + (ten,))


def _tron(bang: Dict[str, List[Dict[str, Any]]], ts: Dict[str, float],
          da: set) -> List[Dict[str, Any]]:
    """Vòng xoay có trọng số (smooth weighted round-robin) trên THỨ HẠNG; bỏ dòng có mã đã ra."""
    con = [t for t in ts if bang.get(t)]
    vi_tri = {t: 0 for t in con}
    hien = {t: 0.0 for t in con}
    ra: List[Dict[str, Any]] = []
    while con:
        for t in con:
            hien[t] += ts[t]
        t = max(con, key=lambda x: (hien[x], -con.index(x)))
        hien[t] -= sum(ts[x] for x in con)
        ds = bang[t]
        while vi_tri[t] < len(ds) and ds[vi_tri[t]]["ma"] in da:
            vi_tri[t] += 1
        if vi_tri[t] < len(ds):
            d = ds[vi_tri[t]]
            vi_tri[t] += 1
            da.add(d["ma"])
            ra.append(d)
        if vi_tri[t] >= len(ds):
            con.remove(t)
    return ra


def xep_hang(nc: Any, *, tham_do: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Bảng ứng viên cuối cùng của lượt, mạnh nhất trước.

    * Không khai `chien_luoc`: một công thức theo `tu_chay.chon_cong_thuc`, bảng Y HỆT trước (không
      thêm khoá nào — golden `tests/test_chien_luoc_golden.py` canh từng byte).
    * Có khai: chạy từng công thức, trộn theo thứ hạng (vòng xoay có trọng số), khử trùng theo `ma`
      (`tin_hieu.cong_thuc_khac` = các công thức khác cũng chọn dòng đó), gắn `cong_thuc`/`tham_do`.
      Lượt thăm dò: bảng công thức thăm dò đứng trước, các bảng khác trộn nối sau. Kênh giai đoạn
      `moi`: trong bảng thăm dò, ứng viên thuộc CỤM KÊNH CHƯA THỬ lần nào đứng trước
      (`tin_hieu.cum_chua_thu`) — kênh non tự thăm dò trên chính nó thay vì mượn nhóm.
    """
    kh = ke_hoach(nc, tham_do=tham_do)
    for g in kh.ghi_chu:
        nc.ghi("  chiến lược: {0}.".format(g))
    if kh.cu:
        ten = next(iter(kh.trong_so))
        nc.ghi("  đang dùng công thức {0} vì {1}.".format(ten.upper(), kh.ly_do))
        return _bang(nc, ten)[0]

    ts = kh.trong_so
    nc.ghi("  đang dùng chiến lược {0} ({1}){2}.".format(
        " + ".join("{0} {1:.0%}".format(t.upper(), w) for t, w in ts.items()), kh.ly_do,
        " — lượt THĂM DÒ: bảng {0} đứng trước".format(kh.tham_do.upper()) if kh.tham_do else ""))
    bang: Dict[str, List[Dict[str, Any]]] = {}
    cam = tuple(ts)
    for ten in ts:
        ds, ten_that = _bang(nc, ten, tuple(x for x in cam if x != ten))
        bang[ten] = [dict(d, cong_thuc=ten_that, tham_do=(ten == kh.tham_do),
                          tin_hieu=dict(d.get("tin_hieu") or {})) for d in ds]
    co_ma: Dict[str, List[str]] = {}
    for ten in ts:
        for d in bang[ten]:
            if ten not in co_ma.setdefault(d["ma"], []):
                co_ma[d["ma"]].append(ten)
    for ten in ts:
        for d in bang[ten]:
            khac = [t for t in co_ma[d["ma"]] if t != ten]
            if khac:
                d["tin_hieu"]["cong_thuc_khac"] = khac

    if kh.tham_do and nc.giai_doan == "moi":
        bang[kh.tham_do] = _uu_tien_cum_chua_thu(nc, bang[kh.tham_do])

    da: set = set()
    if kh.tham_do:
        ra = []
        for d in bang[kh.tham_do]:
            if d["ma"] not in da:
                da.add(d["ma"])
                ra.append(d)
        ra += _tron({t: b for t, b in bang.items() if t != kh.tham_do},
                    {t: w for t, w in ts.items() if t != kh.tham_do}, da)
    else:
        ra = _tron(bang, ts, da)
    ra = nc.loc(ra)  # khử trùng TIÊU ĐỀ giữa các bảng (mã khác, cùng bài)
    nc.ghi("  chiến lược: {0} ứng viên sau trộn ({1}).".format(
        len(ra), ", ".join("{0} {1}".format(t, len(bang[t])) for t in ts)))
    return ra


def _uu_tien_cum_chua_thu(nc: Any, ds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gắn `tin_hieu.cum_chua_thu` (cụm của dòng mà kênh CHƯA làm lần nào) rồi đưa các dòng ấy lên trước,
    giữ thứ tự công thức trong từng nhóm. Cụm theo bộ nhận cụm V7 của kênh (nhãn AI theo nghĩa trước)."""
    try:
        da_thu = nc.cum_da_thu
    except Exception:  # noqa: BLE001
        return ds
    moi: List[Dict[str, Any]] = []
    cu: List[Dict[str, Any]] = []
    for d in ds:
        cum = [str(c) for c in (d.get("cum") or [])] or nc.cum_cua(str(d.get("tieu_de") or ""))
        chua = [c for c in cum if c not in da_thu]
        if chua:
            d["tin_hieu"]["cum_chua_thu"] = chua
            moi.append(d)
        else:
            cu.append(d)
    if moi:
        nc.ghi("  chiến lược: kênh mới — {0} ứng viên thuộc cụm CHƯA THỬ đứng đầu bảng thăm dò.".format(len(moi)))
    return moi + cu
