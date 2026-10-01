"""Xếp lịch đăng NHIỀU KHE/NGÀY + KHO ĐỆM (Đợt 2.2 + 2.5, bản gọn — 29/09/2026).

═══ VÌ SAO CÓ TỆP NÀY ═══

Chủ dự án 29/09/2026: "máy này phải chạy được nhiều kênh nhất và mỗi kênh đăng
nhiều video nhất". Trước tệp này mỗi kênh chỉ có MỘT giờ đăng (`gio_dang`) và
cửa sản xuất `core.tu_chay._cua_so_san_xuat` CHẶN CỨNG khi còn một gói chờ đăng
— tối đa một video/ngày, và máy đứng chờ mỗi lần tải lên.

Kênh khai `nhip_dang` (danh sách giờ trong ngày, vd `"12:00, 20:00"` hay
`["12:00", "20:00"]`) trong `kenh.yaml` cùng `tu_duyet: true` thì bật chế độ mới:

* **Xếp lịch:** gói QA đạt được gán vào KHE TRỐNG SỚM NHẤT ≥ bây giờ +
  `bien_xu_ly_gio` (mặc định 12 giờ — đủ để máy đăng tải lên + YouTube xử lý
  HD trước giờ công khai), không trùng khe đã có của kênh.
* **Kho đệm** thay cửa chặn cứng: sản xuất tiếp khi
  (khe tương lai đã có video + gói QA đạt chưa có lịch/đã lỡ lịch) <
  `kho_dem_ngay` × số khe/ngày.
* **Xếp lại gói lỡ lịch:** gói "Sẵn sàng" chưa tải (Trạng thái đăng trống, không
  có Video ID ở kế hoạch lẫn sổ máy đăng) mà lịch đã trôi qua → dời sang khe
  trống sớm nhất, không để nằm chết trong DONE.

Kênh KHÔNG khai `nhip_dang` → hành vi CŨ y nguyên (một `gio_dang`, cửa chặn
cứng, biên 60 phút) — tương thích mọi kênh/bài kiểm có sẵn.

═══ NHỊP NGÀY `chu_ky_dang_ngay` (01/10/2026 — giãn lịch đăng) ═══

Chủ dự án 01/10: "đăng nhiều video mỗi ngày không tốt, view lẹt đẹt; nên 2 ngày 1
video hoặc 3 ngày 1 video" (TL4 thắng ở nhịp 1/2 ngày; kênh đối thủ đăng thưa
có trung vị view ≈5× kênh đăng dày). Kênh có `chu_ky_dang_ngay` N ≥ 2:

* **Khe:** hai video công khai của cùng kênh cách nhau ≥ N NGÀY LỊCH — tính cả
  video đã đăng / đã hẹn giờ trên YouTube (dòng kế hoạch có lịch + sổ máy đăng
  `vm/logs/so-video-id.json`), không chỉ khe trống.
* **Kho đệm:** `kho_dem_ngay` là số NGÀY → số video cần = ⌈ngày ÷ N⌉ (4 ngày ở
  nhịp 2 ngày = 2 video), không còn × số khe/ngày.
* **Xếp lại theo nhịp:** gói "Sẵn sàng" CHƯA tải lên (không Video ID) được xếp
  lại vào khe hợp nhịp, gói điểm chất lượng cao hơn đăng trước (`diem_goi`:
  điểm biên tập của nguồn ở sổ lượt `tu-chay/*.json`, rồi điểm tiêu đề / kịch
  bản / bìa ở hồ sơ video).

N = 1 (mặc định) → hành vi cũ y nguyên (nhiều khe/ngày theo `nhip_dang`).

Không mạng, không Qt. Chỉ đọc/ghi kế hoạch qua `core.ke_hoach_dang`.
"""

from __future__ import annotations

import datetime as _dt
import glob
import json
import math
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from . import ke_hoach_dang

__all__ = ["BIEN_XU_LY_GIO_MAC_DINH", "KHO_DEM_NGAY_MAC_DINH", "chuan_hoa_nhip",
           "khe_cua_kenh", "che_do_nhieu_khe", "khe_da_dung", "khe_trong_som_nhat",
           "dem_kho_dem", "xep_lai_goi_lo_lich", "tran_video_ngay", "goi_y_khe",
           "SOM_HON_DINH_GIO_MAC_DINH", "chu_ky_ngay", "moc_da_co", "hop_nhip", "diem_goi",
           "so_video_kho_can"]

#: Biên tối thiểu giữa lúc xếp lịch và giờ công khai (giờ). Lộ trình v3 mục 6.
BIEN_XU_LY_GIO_MAC_DINH = 12.0
#: Kho đệm mặc định (ngày). Lộ trình v3 mục 6.
KHO_DEM_NGAY_MAC_DINH = 3
#: Gói lỡ lịch quá ngần này phút mới bị dời — chừa chỗ cho phiên kênh đang tải
#: sát giờ (máy đăng tự dời +15' khi giờ đã qua lúc đang dở).
PHUT_LO_LICH_TOI_THIEU = 30

#: `goi_y_khe`: đăng SỚM HƠN đỉnh khán giả online chừng này giờ, để đợt quét
#: trang chủ đầu tiên của YouTube (tới ở GIỜ TUỔI 12–13 sau khi đăng — đo
#: nhiều lần ở `CHANNEL/TL4-T7/CLAUDE.md` dòng 46 và `NHAT-KY-KENH.md`) rơi
#: đúng lúc khán giả đông nhất, chứ không phải rơi vào lúc vừa đăng.
#:
#: ⚠ Số 1–2 giờ trong yêu cầu ban đầu (29/09/2026) tự mâu thuẫn với chính lý
#: do đi kèm nó ("để đợt thử trang chủ rơi đúng đỉnh"): insight #7 tự tính
#: — đăng 22h JST thì đợt thử (+12–13h) rơi 10–11h JST; đăng 07–09h JST thì
#: rơi 20–21h JST, ĐÚNG ĐỈNH — tức độ lệch đúng phải là ~12–13 GIỜ, không
#: phải 1–2 giờ. Đã sửa hằng số này theo đúng cơ chế đã đo, không theo con
#: số 1–2h gõ nhầm trong yêu cầu; xem NHAT-KY-PHAT-TRIEN.md ngày sửa để đối
#: chiếu. Muốn dùng lại đúng nghĩa đen "trước đỉnh 1–2h" thì truyền
#: `som_hon_gio=1.5` khi gọi `goi_y_khe`.
SOM_HON_DINH_GIO_MAC_DINH = 12.5

_MAU_GIO = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")


def _gio_hop_le(chuoi: Any) -> str:
    """`"8:05"` → `"08:05"`; sai dạng → `""`. PyYAML 1.1 đọc `12:00` KHÔNG bọc
    nháy thành số 720 (hệ lục thập phân) — nhận luôn số nguyên phút đó."""
    if isinstance(chuoi, bool):
        return ""
    if isinstance(chuoi, int):
        if 0 <= chuoi < 24 * 60:
            return "{0:02d}:{1:02d}".format(chuoi // 60, chuoi % 60)
        return ""
    m = _MAU_GIO.match(str(chuoi or ""))
    if not m:
        return ""
    gio, phut = int(m.group(1)), int(m.group(2))
    if not (0 <= gio <= 23 and 0 <= phut <= 59):
        return ""
    return "{0:02d}:{1:02d}".format(gio, phut)


def chuan_hoa_nhip(gia_tri: Any) -> List[str]:
    """`kenh.yaml: nhip_dang` → danh sách `"HH:MM"` đã sắp, bỏ trùng/sai dạng.

    Nhận danh sách YAML, chuỗi `"12:00, 20:00"`, chuỗi `"[\"12:00\",\"20:00\"]"`
    (bộ đọc YAML tối giản), hay số phút (PyYAML đọc `12:00` trần)."""
    if gia_tri is None:
        return []
    if isinstance(gia_tri, bool):
        return []
    if isinstance(gia_tri, (list, tuple)):
        tho: Iterable[Any] = gia_tri
    elif isinstance(gia_tri, int):
        tho = [gia_tri]
    else:
        chu = str(gia_tri).strip().strip("[]")
        tho = [x.strip().strip("'\"") for x in re.split(r"[,;\s]+", chu) if x.strip()]
    ra = sorted({g for g in (_gio_hop_le(x) for x in tho) if g})
    return ra


def khe_cua_kenh(kenh: Any) -> List[str]:
    """Các giờ đăng trong ngày của kênh: `nhip_dang` nếu khai, không thì
    `[gio_dang]` (hành vi cũ), không có cả hai thì rỗng."""
    nhip = list(getattr(kenh, "nhip_dang", None) or [])
    if nhip:
        return nhip
    g = _gio_hop_le(getattr(kenh, "gio_dang", "") or "")
    return [g] if g else []


def che_do_nhieu_khe(kenh: Any) -> bool:
    """Bật chế độ xếp lịch nhiều khe + kho đệm: `tu_duyet: true` VÀ khai
    `nhip_dang`. Thiếu một trong hai → đường cũ nguyên vẹn."""
    return bool(getattr(kenh, "tu_duyet", False)) and bool(getattr(kenh, "nhip_dang", None))


def tran_video_ngay(kenh: Any) -> int:
    """Trần số lượt sản xuất MỖI NGÀY của kênh: `video_toi_da_ngay` nếu khai
    (> 0), không thì `video_moi_ngay` (mặc định 1, như cũ)."""
    toi_da = int(getattr(kenh, "video_toi_da_ngay", 0) or 0)
    if toi_da > 0:
        return toi_da
    return max(1, int(getattr(kenh, "video_moi_ngay", 1) or 1))


def chu_ky_ngay(kenh: Any) -> int:
    """`chu_ky_dang_ngay` của kênh (≥ 1): N ngày một video. 1 = đường cũ (nhiều khe/ngày)."""
    try:
        return max(1, int(getattr(kenh, "chu_ky_dang_ngay", 1) or 1))
    except (TypeError, ValueError):
        return 1


def so_video_kho_can(kenh: Any, kho_ngay: int) -> int:
    """Số video kho đệm cần cho `kho_ngay` ngày ở nhịp hiện tại: N ≥ 2 → ⌈ngày ÷ N⌉
    (một khe hợp nhịp mỗi N ngày); N = 1 → ngày × số khe/ngày (như cũ)."""
    n = chu_ky_ngay(kenh)
    if n >= 2:
        return max(1, int(math.ceil(float(kho_ngay) / n)))
    return int(kho_ngay) * len(khe_cua_kenh(kenh))


def hop_nhip(moc: _dt.datetime, da_co: Iterable[_dt.datetime], chu_ky: int) -> bool:
    """`moc` cách MỌI mốc công khai đã có của kênh ≥ `chu_ky` ngày lịch (chu_ky ≤ 1: luôn hợp)."""
    if chu_ky <= 1:
        return True
    return all(abs((moc.date() - m.date()).days) >= chu_ky for m in da_co)


def moc_da_co(goc: str, ma_kenh: str, *, so_video_id: Optional[Dict[str, Any]] = None,
              bo_ma: Iterable[str] = ()) -> List[_dt.datetime]:
    """Mọi mốc công khai ĐÃ CÓ của kênh: dòng kế hoạch có Ngày+Giờ (mọi trạng thái — đã đăng, đã hẹn,
    chờ tải) + `lich` của sổ máy đăng (video đã hẹn giờ / đã đăng trên YouTube). `bo_ma`: mã gói không
    tính (gói đang được xếp lại)."""
    bo = set(bo_ma or ())
    so = doc_so_video_id(goc) if so_video_id is None else so_video_id
    ra: List[_dt.datetime] = []
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    bo_ke_hoach = set()
    for d in _dong(cot, hang):
        ma = d.get("Mã gói", "")
        if ma in bo:
            continue
        tt = d.get("Trạng thái đăng", "")
        if not d.get("Sẵn sàng") and not tt:
            continue    # dòng nháp/bỏ (không Sẵn sàng, chưa từng đăng) không chiếm nhịp
        if tt.lower().startswith("bỏ") or "KHÔNG ĐĂNG" in tt.upper():
            continue
        moc = _moc(d.get("Ngày đăng", ""), d.get("Giờ đăng", ""))
        if moc is not None:
            ra.append(moc)
            bo_ke_hoach.add(ma)
    for k, m in (so or {}).items():
        if not isinstance(m, dict) or not str(k).startswith(ma_kenh + "/"):
            continue
        ma = str(k).split("/", 1)[-1]
        if ma in bo or not m.get("video_id"):
            continue
        if m.get("trang_thai") in ("nhap", "dang-tai", "loi-tai", "tai-hong"):
            continue
        chu = str(m.get("lich") or "").strip().split(" ")
        moc = _moc(chu[0], chu[1]) if len(chu) == 2 else None
        if moc is not None and moc not in ra:
            ra.append(moc)
    return ra


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def diem_goi(goc: str, ma_kenh: str, ma_goi: str) -> Tuple[float, float]:
    """Điểm chất lượng DỰ ĐOÁN của một gói (cao = đăng trước): (điểm chính, điểm phụ).

    Chính: phán quyết biên tập của nguồn (`nguon.bien_tap` ở sổ lượt `CHANNEL/<k>/tu-chay/*.json` — điểm
    0–100, +3 nếu hạng TỐT, +2 nếu dự đoán "thắng"); thiếu thì điểm công thức của nguồn. Phụ: điểm tiêu đề
    + kịch bản + mở đầu đã chọn (0–10 mỗi thứ) + bìa (giám khảo 0–100 ÷ 10) ở hồ sơ video. Không có gì → 0."""
    chinh = 0.0
    for duong in sorted(glob.glob(os.path.join(goc, "CHANNEL", ma_kenh, "tu-chay", "*.json")), reverse=True)[:45]:
        du = _doc_json(duong)
        for r in ((du or {}).get("runs") or []) if isinstance(du, dict) else []:
            if not isinstance(r, dict) or str((r.get("ban_giao") or {}).get("ma_goi") or "") != ma_goi:
                continue
            nguon = r.get("nguon") or {}
            bt = nguon.get("bien_tap") if isinstance(nguon.get("bien_tap"), dict) else {}
            try:
                chinh = float(bt.get("diem") if bt.get("diem") is not None else nguon.get("diem") or 0)
            except (TypeError, ValueError):
                chinh = 0.0
            if str(bt.get("hang") or "").upper() == "TOT":
                chinh += 3.0
            if "thắng" in str((bt.get("du_doan") or {}).get("ket_cuc") or ""):
                chinh += 2.0
            break
        if chinh:
            break
    phu = 0.0
    hs = _doc_json(os.path.join(goc, "CHANNEL", ma_kenh, "ho-so-video", ma_goi + ".json"))
    if isinstance(hs, dict):
        def _so(x: Any) -> float:
            try:
                return float(x or 0)
            except (TypeError, ValueError):
                return 0.0
        tc = hs.get("tieu_de_cham") if isinstance(hs.get("tieu_de_cham"), dict) else {}
        diem_td = tc.get("diem") if isinstance(tc.get("diem"), dict) else {}
        phu += max([_so(v) for v in diem_td.values()] or [0.0])
        kb = hs.get("kich_ban") if isinstance(hs.get("kich_ban"), dict) else {}
        phu += _so((kb.get("diem") or {}).get(kb.get("ban_chon")) if isinstance(kb.get("diem"), dict) else 0)
        phu += _so((kb.get("hook_diem") or {}).get(kb.get("hook_chon")) if isinstance(kb.get("hook_diem"), dict) else 0)
        th = hs.get("thumbnail") if isinstance(hs.get("thumbnail"), dict) else {}
        phu += _so(th.get("diem_giam_khao")) / 10.0
    return chinh, phu


def _moc(ngay: str, gio: str) -> Optional[_dt.datetime]:
    try:
        d = _dt.datetime.strptime(str(ngay or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None
    g = _gio_hop_le(gio)
    if not g:
        return None
    return _dt.datetime.combine(d, _dt.datetime.strptime(g, "%H:%M").time())


def _dong(cot: List[str], hang: List[List[str]]) -> List[Dict[str, str]]:
    ra = []
    for d in hang:
        ra.append({ten: (str(d[i]).strip() if i < len(d) and d[i] is not None else "")
                   for i, ten in enumerate(cot)})
    return ra


def khe_da_dung(goc: str, ma_kenh: str) -> Set[Tuple[str, str]]:
    """Mọi cặp (Ngày đăng, Giờ đăng) đã có trong kế hoạch của kênh — BẤT KỂ
    trạng thái (đã đăng, đang chờ, đăng tay…): một khe đã có video thì không
    gán thêm video thứ hai vào đó."""
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    ra: Set[Tuple[str, str]] = set()
    for d in _dong(cot, hang):
        ngay, gio = d.get("Ngày đăng", ""), _gio_hop_le(d.get("Giờ đăng", ""))
        if ngay and gio:
            ra.add((ngay, gio))
    return ra


def khe_trong_som_nhat(goc: str, ma_kenh: str, kenh: Any, *,
                       bay_gio: Optional[_dt.datetime] = None,
                       bien_gio: Optional[float] = None,
                       toi_da_ngay: int = 60,
                       da_dung: Optional[Set[Tuple[str, str]]] = None,
                       da_co: Optional[List[_dt.datetime]] = None) -> Tuple[str, str]:
    """`(dd/mm/YYYY, HH:MM)` của khe trống sớm nhất ≥ bây giờ + biên; không
    có khe (kênh không khai giờ) hoặc hết `toi_da_ngay` ngày → `("", "")`.

    01/10/2026: kênh `chu_ky_dang_ngay` N ≥ 2 → khe còn phải cách MỌI mốc công khai đã có
    (`da_co`, mặc định `moc_da_co`: kế hoạch + sổ máy đăng) ≥ N ngày lịch."""
    khe = khe_cua_kenh(kenh)
    if not khe:
        return "", ""
    bay_gio = bay_gio or _dt.datetime.now()
    if bien_gio is None:
        bien_gio = float(getattr(kenh, "bien_xu_ly_gio", BIEN_XU_LY_GIO_MAC_DINH)
                         or BIEN_XU_LY_GIO_MAC_DINH)
    som_nhat = bay_gio + _dt.timedelta(hours=max(0.0, float(bien_gio)))
    dung = khe_da_dung(goc, ma_kenh) if da_dung is None else da_dung
    n = chu_ky_ngay(kenh)
    if n >= 2 and da_co is None:
        da_co = moc_da_co(goc, ma_kenh)
    ngay = som_nhat.date()
    for _i in range(max(1, int(toi_da_ngay))):
        chuoi = ngay.strftime("%d/%m/%Y")
        for gio in khe:
            moc = _moc(chuoi, gio)
            if moc is None or moc < som_nhat:
                continue
            if (chuoi, gio) not in dung and hop_nhip(moc, da_co or [], n):
                return chuoi, gio
        ngay = ngay + _dt.timedelta(days=1)
    return "", ""


def _co_video_id(dong: Dict[str, str], ma_kenh: str, so_video_id: Dict[str, Any]) -> bool:
    if dong.get("Video ID"):
        return True
    ma = dong.get("Mã gói", "")
    muc = (so_video_id or {}).get("{0}/{1}".format(ma_kenh, ma)) or {}
    return bool(isinstance(muc, dict) and muc.get("video_id"))


def doc_so_video_id(goc: str) -> Dict[str, Any]:
    """Sổ `vm/logs/so-video-id.json` của máy đăng DOM (rỗng nếu không có)."""
    try:
        with open(os.path.join(goc, "vm", "logs", "so-video-id.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def dem_kho_dem(goc: str, ma_kenh: str, kenh: Any, *,
                bay_gio: Optional[_dt.datetime] = None,
                bo_qua: Iterable[str] = ()) -> Dict[str, Any]:
    """Kho đệm của kênh lúc `bay_gio`.

    * `khe_tuong_lai`: mã gói có lịch (Ngày+Giờ) SAU bây giờ — bất kể đã tải
      lên hay chưa (đã tải = YouTube giữ lịch hẹn; chưa tải = máy đăng sẽ tải).
    * `goi_cho`: gói "Sẵn sàng", chưa "ĐÃ ĐĂNG", KHÔNG có lịch tương lai (chưa
      xếp, hoặc lỡ lịch chờ xếp lại) — hàng tồn chưa có chỗ.
    * `bo_qua`: mã gói không tính (gói chờ quá hạn `cho_dang_toi_da_ngay`).
    """
    bay_gio = bay_gio or _dt.datetime.now()
    bo = set(bo_qua or ())
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    tuong_lai: List[str] = []
    cho: List[str] = []
    moc_tuong_lai: List[_dt.datetime] = []
    for d in _dong(cot, hang):
        ma = d.get("Mã gói", "")
        if not ma or ma in bo:
            continue
        moc = _moc(d.get("Ngày đăng", ""), d.get("Giờ đăng", ""))
        if moc is not None and moc > bay_gio:
            tuong_lai.append(ma)
            moc_tuong_lai.append(moc)
            continue
        if d.get("Sẵn sàng") and "ĐÃ ĐĂNG" not in d.get("Trạng thái đăng", "").upper():
            cho.append(ma)
    so_khe = len(khe_cua_kenh(kenh))
    kho_ngay = int(getattr(kenh, "kho_dem_ngay", KHO_DEM_NGAY_MAC_DINH) or 0)
    if kho_ngay <= 0:
        kho_ngay = KHO_DEM_NGAY_MAC_DINH
    # 01/10/2026: `kho_dem_ngay` là NGÀY — số video cần tính theo nhịp (`so_video_kho_can`):
    # 4 ngày ở nhịp 2 ngày/video = 2 video, không phải 4 × số khe/ngày.
    return {"khe_tuong_lai": tuong_lai, "goi_cho": cho,
            "kho": len(tuong_lai) + len(cho), "can": so_video_kho_can(kenh, kho_ngay),
            "so_khe_ngay": so_khe, "kho_dem_ngay": kho_ngay, "chu_ky_dang_ngay": chu_ky_ngay(kenh),
            "moc_tuong_lai_som_nhat": (min(moc_tuong_lai).isoformat(timespec="minutes")
                                       if moc_tuong_lai else "")}


def xep_lai_goi_lo_lich(goc: str, ma_kenh: str, kenh: Any, *,
                        bay_gio: Optional[_dt.datetime] = None,
                        so_video_id: Optional[Dict[str, Any]] = None,
                        co_dang_do: Optional[bool] = None) -> List[Tuple[str, str, str]]:
    """Dời gói "Sẵn sàng" CHƯA TẢI mà lịch đã trôi qua sang khe trống sớm nhất.

    Chỉ đụng dòng: Sẵn sàng có chữ, Trạng thái đăng TRỐNG (không "ĐANG ĐĂNG",
    "LỆCH LỊCH", "ĐÃ ĐĂNG"…), không Video ID (kế hoạch lẫn sổ máy đăng), lịch
    cũ < bây giờ − 30'. Máy đăng đang dở (`vm/logs/dang-dodang.json`) → không
    làm gì. Trả `[(mã, lịch cũ, lịch mới)]`. Ghi nguyên tử một lần.
    """
    if not che_do_nhieu_khe(kenh):
        return []
    bay_gio = bay_gio or _dt.datetime.now()
    if co_dang_do is None:
        co_dang_do = os.path.exists(os.path.join(goc, "vm", "logs", "dang-dodang.json"))
    if co_dang_do:
        return []
    so = doc_so_video_id(goc) if so_video_id is None else so_video_id
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    if "Ngày đăng" not in cot or "Giờ đăng" not in cot:
        return []
    i_ngay, i_gio = cot.index("Ngày đăng"), cot.index("Giờ đăng")
    if chu_ky_ngay(kenh) >= 2:
        doi = _xep_lai_theo_nhip(goc, ma_kenh, kenh, cot, hang, bay_gio, so)
        if doi:
            ke_hoach_dang.luu_bang(goc, ma_kenh, hang, cot)
        return doi
    dung = khe_da_dung(goc, ma_kenh)
    han = bay_gio - _dt.timedelta(minutes=PHUT_LO_LICH_TOI_THIEU)
    doi: List[Tuple[str, str, str]] = []
    for d_tho, d in zip(hang, _dong(cot, hang)):
        if not d.get("Sẵn sàng") or d.get("Trạng thái đăng"):
            continue
        if _co_video_id(d, ma_kenh, so):
            continue
        moc = _moc(d.get("Ngày đăng", ""), d.get("Giờ đăng", ""))
        if moc is None or moc >= han:
            continue
        ngay_moi, gio_moi = khe_trong_som_nhat(goc, ma_kenh, kenh, bay_gio=bay_gio, da_dung=dung)
        if not ngay_moi:
            continue
        while len(d_tho) <= max(i_ngay, i_gio):
            d_tho.append("")
        cu = "{0} {1}".format(d.get("Ngày đăng", ""), d.get("Giờ đăng", ""))
        d_tho[i_ngay], d_tho[i_gio] = ngay_moi, gio_moi
        dung.add((ngay_moi, gio_moi))
        doi.append((d.get("Mã gói", ""), cu, "{0} {1}".format(ngay_moi, gio_moi)))
    if doi:
        ke_hoach_dang.luu_bang(goc, ma_kenh, hang, cot)
    return doi


def _xep_lai_theo_nhip(goc: str, ma_kenh: str, kenh: Any, cot: List[str], hang: List[List[str]],
                       bay_gio: _dt.datetime, so: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """Nhịp N ≥ 2 ngày (01/10/2026): xếp lại MỌI gói "Sẵn sàng" chưa tải lên (Trạng thái đăng trống,
    không Video ID ở kế hoạch lẫn sổ) — chưa có lịch, lỡ lịch, hoặc lịch còn xa hơn biên xử lý — vào các
    khe hợp nhịp, gói điểm cao (`diem_goi`) lấy khe sớm trước. Gói hẹn trong (bây giờ − 30', bây giờ +
    biên) đứng yên (máy đăng có thể đang tải). Sửa `hang` tại chỗ; trả [(mã, lịch cũ, lịch mới)]."""
    i_ngay, i_gio = cot.index("Ngày đăng"), cot.index("Giờ đăng")
    bien = float(getattr(kenh, "bien_xu_ly_gio", BIEN_XU_LY_GIO_MAC_DINH) or BIEN_XU_LY_GIO_MAC_DINH)
    tu = bay_gio - _dt.timedelta(minutes=PHUT_LO_LICH_TOI_THIEU)
    den = bay_gio + _dt.timedelta(hours=bien)
    dong = _dong(cot, hang)
    xep: List[Tuple[List[str], Dict[str, str]]] = []
    for d_tho, d in zip(hang, dong):
        if not d.get("Sẵn sàng") or d.get("Trạng thái đăng") or not d.get("Mã gói"):
            continue
        if _co_video_id(d, ma_kenh, so):
            continue
        moc = _moc(d.get("Ngày đăng", ""), d.get("Giờ đăng", ""))
        if moc is not None and tu <= moc < den:
            continue
        xep.append((d_tho, d))
    if not xep:
        return []
    ma_xep = [d["Mã gói"] for _t, d in xep]
    da_co = moc_da_co(goc, ma_kenh, so_video_id=so, bo_ma=ma_xep)
    dung: Set[Tuple[str, str]] = set()
    for d in dong:
        if d.get("Mã gói") in ma_xep:
            continue
        g = _gio_hop_le(d.get("Giờ đăng", ""))
        if d.get("Ngày đăng") and g:
            dung.add((d["Ngày đăng"], g))
    diem = {ma: diem_goi(goc, ma_kenh, ma) for ma in ma_xep}
    xep.sort(key=lambda x: (-diem[x[1]["Mã gói"]][0], -diem[x[1]["Mã gói"]][1], x[1]["Mã gói"]))
    doi: List[Tuple[str, str, str]] = []
    for d_tho, d in xep:
        ngay_moi, gio_moi = khe_trong_som_nhat(goc, ma_kenh, kenh, bay_gio=bay_gio, da_dung=dung, da_co=da_co)
        if not ngay_moi:
            continue
        dung.add((ngay_moi, gio_moi))
        moc_moi = _moc(ngay_moi, gio_moi)
        if moc_moi is not None:
            da_co.append(moc_moi)
        cu = "{0} {1}".format(d.get("Ngày đăng", ""), d.get("Giờ đăng", "")).strip()
        if (d.get("Ngày đăng", ""), _gio_hop_le(d.get("Giờ đăng", ""))) == (ngay_moi, gio_moi):
            continue
        while len(d_tho) <= max(i_ngay, i_gio):
            d_tho.append("")
        d_tho[i_ngay], d_tho[i_gio] = ngay_moi, gio_moi
        doi.append((d.get("Mã gói", ""), cu, "{0} {1}".format(ngay_moi, gio_moi)))
    return doi


def goi_y_khe(goc: str, ma_kenh: str, *,
             som_hon_gio: float = SOM_HON_DINH_GIO_MAC_DINH,
             so_khe: int = 2, kenh: Any = None) -> Dict[str, Any]:
    """Gợi ý khe đăng từ đỉnh khán giả online (`chi-so/gio-online.json`, do
    `chi_so_ytb.giai_ma.cap_nhat_gio_online` ghi — insight #7 29/09/2026).

    CHỈ TRẢ GỢI Ý bằng chuỗi `"HH:MM"` (giờ VPS, cùng đơn vị `nhip_dang` của
    `kenh.yaml`) — KHÔNG đụng `nhip_dang`, không ghi tệp nào. Khách/AI tự
    quyết định có đưa vào `nhip_dang` hay không; nơi gọi (báo cáo công suất,
    Bảng điều khiển…) tự quyết định có hiển thị hay không.

    Đề xuất là các giờ TRÒN, cách nhau, đứng TRƯỚC đỉnh khoảng `som_hon_gio`
    tới `som_hon_gio + so_khe - 1` giờ — để đợt thử trang chủ (~giờ 12–13 sau
    khi đăng) rơi đúng lúc khán giả đông nhất, không phải LÚC ĐĂNG mới đông.

    Trả rỗng (`khe_de_xuat: []`) kèm `ly_do` khi kênh chưa có `gio-online.json`
    hoặc dữ liệu còn toàn số 0 (kênh mới, Studio chưa đủ 28 ngày) — nói thật
    lúc thiếu số, không đoán liều.
    """
    duong = os.path.join(goc, "CHANNEL", ma_kenh, "chi-so", "gio-online.json")
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {"khe_de_xuat": [], "ly_do": "chưa có core/chi_so_ytb/giai_ma.py::gio-online.json — "
                                             "kênh chưa quét tab-build_audience, hoặc chưa giải mã."}
    dinh_vps = ((du or {}).get("dinh") or {}).get("vps") or {}
    gio_dinh = dinh_vps.get("gio")
    if not isinstance(du, dict) or gio_dinh is None:
        return {"khe_de_xuat": [], "ly_do": "gio-online.json không có đỉnh giờ VPS hợp lệ."}
    so_khe = max(1, int(so_khe))
    # 01/10/2026: kênh đăng thưa (`chu_ky_dang_ngay` ≥ 2) chỉ có MỘT video mỗi N ngày → gợi ý MỘT khe.
    n = chu_ky_ngay(kenh) if kenh is not None else 1
    if n >= 2:
        so_khe = 1
    de_xuat = sorted({"{0:02d}:00".format(int(gio_dinh - som_hon_gio - i) % 24)
                      for i in range(so_khe)})
    return {
        "khe_de_xuat": de_xuat,
        "dinh_online_vps": dinh_vps,
        "dinh_online_jst": ((du.get("dinh") or {}).get("jst") or {}),
        "cap_nhat_gio_online": du.get("cap_nhat", ""),
        "chu_ky_dang_ngay": n,
        "ly_do": ("đăng trước đỉnh khán giả online {0:.1f}-{1:.1f} giờ để đợt thử trang chủ "
                  "(~12-13h sau khi đăng) rơi đúng lúc đông nhất — chỉ gợi ý, không tự đổi nhip_dang."
                  .format(som_hon_gio, som_hon_gio + so_khe - 1)
                  + (" Nhịp hiện tại 1 video / {0} ngày — một khe là đủ.".format(n) if n >= 2 else "")),
    }
