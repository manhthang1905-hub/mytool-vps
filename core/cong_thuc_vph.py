"""Công thức VPH — chọn content theo SỰ ĐỘT BIẾN của video đối thủ (view/giờ).

Chủ dự án, 29/09/2026: *"V7 đúng cho kênh ĐANG LÊN có chỉ số. 3 kênh mới tạm thời CHƯA cần chạy
V7 — trước mắt chạy theo TREND: quét trang chủ → ra đối thủ → theo dõi content có SỰ ĐỘT BIẾN →
chọn video đột biến để làm = CÔNG THỨC VPH. Sẽ có NHIỀU công thức, nhiều cách đánh."*

═══ LÀM TIẾP MỘT NÚT, KHÔNG LÀM TRÙNG ═══

Một nút (`core/mot_nut.py` + `core/cham_diem_content.py`) đã có ba thước "đột biến":
MỚI (≤ 7 ngày, đúng tuyến), BỨT (`Tăng/ngày` ÷ tốc độ cả đời, chỉ video ≥ 7 ngày) và VƯỢT
(view ÷ trung vị view của kênh). Cả ba thiếu đúng thứ trả lời "video này có đang NỔ so với
video CÙNG TUỔI không": VƯỢT so video 2 ngày tuổi với video 2 năm tuổi của cùng kênh (video
trẻ luôn thua), BỨT bỏ trắng video dưới 7 ngày — đúng khoảng tuổi đáng làm nhất.

Công thức này đo:

    VPH           view ÷ giờ tuổi (tuổi tính tới lúc quét). Video > 72 giờ mà đã có hai lượt
                  quét (`Tăng/ngày` > 0) thì lấy VPH GIỮA HAI LƯỢT QUÉT (`Tăng/ngày` ÷ 24) —
                  tốc độ hôm nay, bắt được cả video cũ vừa được moi lên.
    ĐỘT BIẾN      VPH ÷ trung vị VPH của CHÍNH kênh đó, cùng dải tuổi video; và ÷ trung vị VPH
                  của cả ngách (kho nghiên cứu của CẢ NHÓM, bỏ trùng) cùng dải tuổi. Trung bình
                  nhân hai tỉ số. Kênh nhỏ đột biến = tín hiệu mạnh: chia cho chính kênh nên
                  cỡ kênh không quan trọng.
    TRẺ           ≤ 72 giờ nặng nhất, rồi ≤ 7 ngày, ≤ 30 ngày; video cũ chỉ còn nửa trọng số
                  trừ khi đang BỨT (tốc độ hôm nay ≥ 1,5 × tốc độ cả đời).
    TÍN HIỆU PHỤ  số ngày video hiện trên trang chủ máy ảo (cả nhóm), số lần kênh của nó hiện
                  trên trang chủ, và có nằm trong "khán giả của bạn cũng xem" không.

    Điểm = 100 × (0,5·hạng(đột biến × trẻ) + 0,2·hạng(VPH) + 0,15·hạng(trẻ) + 0,15·hạng(phụ))

"hạng" là thứ hạng phần trăm trong chính lô (`cham_diem_content.hang_phan_tram`) — cùng lý do
như Một nút: không phải bịa hằng số chia. Thước nào cả lô bằng 0 thì chia lại trọng số.

Lọc TRƯỚC khi chấm, y như bảng Một nút: kênh nguồn phải "theo dõi", chưa làm, không dính từ
loại trừ / mốc tuổi, ĐÚNG TUYẾN đang đánh, dài 8–40 phút, view ≥ sàn. Chống trùng tiêu đề,
kiểm trùng ý, giữ nguồn, loại nguồn cả nhóm đã làm: `core/tu_chay.py` làm chung cho MỌI công
thức, không làm lại ở đây.

Ngưỡng nằm trong `nghien-cuu/cong-thuc-vph.json` (không có thì dùng mặc định dưới, KHÔNG tự
ghi tệp). Không gọi mạng, không tốn ví, không import Qt: chỉ đọc tệp trên đĩa.

═══ ĐỘ THÔ CỦA SỐ ═══

`Ngày đăng` chỉ có NGÀY, không có giờ → tuổi lấy mốc giữa ngày (12:00 UTC), sàn 6 giờ. Với
video vài chục giờ tuổi, sai số ±12 giờ là đáng kể — nên "đột biến" so video với video CÙNG
dải tuổi (cùng chịu một kiểu sai số), không so với một con số tuyệt đối.
Chuỗi quét: sổ `content.csv` giữ View và `View lần trước`/`Tăng/ngày` của hai lượt quét gần
nhất (đã lọc nhiễu làm tròn, xem `doi_thu_kenh._bac_lam_tron`). Bản sao lưu `sao-luu/` không
mang giờ quét nên không dùng làm chuỗi. Kho `quet-kenh/` của nhóm chỉ giữ 10 giờ.
"""

from __future__ import annotations

import copy
import datetime as _dt
import io
import json
import math
import os
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from .cham_diem_content import hang_phan_tram

__all__ = ["TEN", "CAU_HINH_MAC_DINH", "TEP_CAU_HINH", "DongVPH", "KetQuaVPH", "nap_cau_hinh",
           "cham", "ung_vien_chon_nguon"]

TEN = "vph"
TEP_CAU_HINH = "cong-thuc-vph.json"

CAU_HINH_MAC_DINH: Dict = {
    #: Dải tuổi (giờ) để so "cùng tuổi". Cận trên, dải cuối không trần.
    "dai_tuoi_gio": [72, 168, 720, 4320],
    #: Dưới ngần này video trong dải thì gộp dải kề bên; vẫn thiếu thì bỏ tỉ số đó.
    "so_video_moc": 3,
    "san_view": 3000,
    #: Chỉ nhận ứng viên có đột biến ≥ ngưỡng (≈ nhanh gấp đôi video cùng tuổi).
    "nguong_dot_bien": 2.0,
    "tran_dot_bien": 50.0,
    #: Video > 30 ngày CHỈ được nhận khi đang BỨT (tốc độ hôm nay ≥ `nguong_but` × tốc độ cả
    #: đời) — video cũ từng nổ mà nay đứng yên là việc của thước VƯỢT (Một nút), không phải VPH.
    "he_so_tre": {"72": 1.0, "168": 0.8, "720": 0.5, "cu_dang_but": 0.45},
    "nguong_but": 1.5,
    "khuon_phut": [8, 40],
    "trang_chu_ngay": 14,
    #: Kênh nguồn có ≥ `ngach_so_video` tiêu đề trong sổ mà dưới `ngach_san` chạm từ ngách → lạc.
    "ngach_so_video": 8,
    "ngach_san": 0.25,
    "trong_so": {"dot_bien": 0.5, "vph": 0.2, "tre": 0.15, "phu": 0.15},
}


def _tron(goc: Dict, them: Dict) -> Dict:
    ra = copy.deepcopy(goc)
    for k, v in (them or {}).items():
        ra[k] = _tron(ra[k], v) if isinstance(v, dict) and isinstance(ra.get(k), dict) else v
    return ra


def nap_cau_hinh(goc: str, kenh: str) -> Dict:
    """Cấu hình VPH của kênh — tệp khách sửa trộn lên mặc định. Không có tệp thì mặc định."""
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_CAU_HINH)
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return _tron(CAU_HINH_MAC_DINH, json.load(tep))
    except (OSError, ValueError):
        return copy.deepcopy(CAU_HINH_MAC_DINH)


@dataclass
class DongVPH:
    ma: str
    link: str
    tieu_de: str
    kenh: str = ""
    view: float = 0.0
    ngay: str = ""
    tuyen: str = ""
    tuoi_gio: float = 0.0
    vph: float = 0.0
    vph_doi: float = 0.0
    vph_gan: Optional[float] = None
    ty_kenh: Optional[float] = None
    ty_ngach: Optional[float] = None
    dot_bien: float = 0.0
    he_tre: float = 0.0
    trang_chu_ngay: int = 0
    trang_chu_kenh: int = 0
    cung_xem: bool = False
    cum: List[str] = field(default_factory=list)
    diem: int = 0
    ly_do: List[str] = field(default_factory=list)


@dataclass
class KetQuaVPH:
    ung_vien: List[DongVPH]
    canh_bao: List[str]
    ghi_chu: List[str]
    so_dong_kho: int = 0


# ── Đọc kho ──────────────────────────────────────────────────────────────────

def _so(x) -> float:
    chu = str(x if x is not None else "").strip().replace(",", "")
    try:
        return float(chu) if chu else 0.0
    except ValueError:
        return 0.0


def _phut(t: str) -> Optional[float]:
    phan = str(t or "").strip().split(":")
    if not phan or not all(p.isdigit() for p in phan):
        return None
    giay = 0
    for p in phan:
        giay = giay * 60 + int(p)
    return giay / 60.0


def _quet_luc(goc: str, kenh: str) -> Optional[_dt.datetime]:
    """Giờ quét content gần nhất của kênh (`cai-dat.json: quet_luc`, UTC), không có → None."""
    try:
        with io.open(os.path.join(so.thu_muc_nghien_cuu(goc, kenh), so.TEP_CAI), encoding="utf-8") as tep:
            ts = float((json.load(tep) or {}).get("quet_luc") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return _dt.datetime.utcfromtimestamp(ts) if ts > 0 else None


def _tuoi_gio(ngay: str, luc: _dt.datetime) -> Optional[float]:
    try:
        d = _dt.date.fromisoformat(str(ngay or "")[:10])
    except ValueError:
        return None
    dang = _dt.datetime(d.year, d.month, d.day, 12, 0)
    return max(6.0, (luc - dang).total_seconds() / 3600.0)


def _thanh_vien(goc: str, kenh: str) -> List[str]:
    try:
        from . import nhom_kenh  # noqa: PLC0415 — nhom_kenh nhập nhiều module, nhập muộn
        return nhom_kenh.thanh_vien(goc, kenh) or [kenh]
    except Exception:  # noqa: BLE001
        return [kenh]


def _kho_nhom(goc: str, kenh: str, bay_gio: _dt.datetime) -> Dict[str, Dict]:
    """`{link: {view, tang, ngay, kenh, luc}}` — sổ content của CẢ NHÓM, bỏ trùng theo link,
    giữ dòng của lượt quét MỚI nhất (view mới nhất)."""
    ra: Dict[str, Dict] = {}
    for k in _thanh_vien(goc, kenh):
        try:
            cot, hang = so.doc_bang(goc, k)
        except Exception:  # noqa: BLE001 — một sổ hỏng không làm hỏng cả kho
            continue
        o = {c: i for i, c in enumerate(cot)}
        if so.COT_LINK not in o:
            continue
        luc = _quet_luc(goc, k) or bay_gio

        def o_(d, ten):
            i = o.get(ten)
            return str(d[i]).strip() if i is not None and i < len(d) else ""
        for d in hang:
            link = o_(d, so.COT_LINK)
            view = _so(o_(d, "View"))
            if not link or view <= 0:
                continue
            cu = ra.get(link)
            if cu is not None and cu["luc"] >= luc:
                continue
            ra[link] = {"view": view, "tang": _so(o_(d, so.COT_TANG)), "ngay": o_(d, "Ngày đăng"),
                        "kenh": o_(d, "Kênh"), "luc": luc,
                        "view_truoc": _so(o_(d, so.COT_VIEW_TRUOC))}
    return ra


#: Bậc làm tròn MẶC ĐỊNH (YouTube tiếng Nhật, 「5.9万」「13.5万」): `(view dưới ngưỡng, bậc)`,
#: dòng cuối `None` = mọi view còn lại. < 1万 gần đúng từng view (bậc 10), 1万–100万 bậc 1.000
#: (sổ TL1 có 135.000 → 140.000), ≥ 100万 bậc 10.000. Thị trường khác khai trong ngach.yaml
#: `thi_truong.bac_lam_tron_view` (vd "1.2K"/"13K"/"1.2M" của tiếng Anh/Việt).
BAC_LAM_TRON_JP: Tuple[Tuple[Optional[float], float], ...] = ((10_000, 10.0), (1_000_000, 1_000.0), (None, 10_000.0))


def bac_lam_tron_tu_ngach(ho_so) -> Optional[Tuple[Tuple[Optional[float], float], ...]]:
    """`thi_truong.bac_lam_tron_view` của hồ sơ ngách → bảng bậc; không khai/hỏng → `None`
    (= `BAC_LAM_TRON_JP`). Dạng YAML: `[{duoi: 10000, bac: 10}, …, {bac: 10000}]`."""
    tho = ((getattr(ho_so, "thi_truong", None) or {}) if ho_so is not None else {}).get("bac_lam_tron_view")
    if not isinstance(tho, list) or not tho:
        return None
    ra: List[Tuple[Optional[float], float]] = []
    try:
        for d in tho:
            duoi = d.get("duoi")
            ra.append((None if duoi in (None, "") else float(duoi), float(d["bac"])))
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return tuple(ra)


def _bac_hien_thi(view: float, bac: Optional[Sequence[Tuple[Optional[float], float]]] = None) -> float:
    """Bậc làm tròn lượt xem YouTube HIỂN THỊ ở thị trường của kênh (`bac`; `None` = tiếng Nhật)."""
    bang = bac or BAC_LAM_TRON_JP
    for duoi, b in bang:
        if duoi is None or view < duoi:
            return float(b)
    return float(bang[-1][1])


def _bac_hien_thi_jp(view: float) -> float:
    """Giữ tên cũ cho nơi gọi/bài kiểm cũ — bậc làm tròn YouTube tiếng Nhật (`BAC_LAM_TRON_JP`)."""
    return _bac_hien_thi(view, None)


def _dai(tuoi: float, moc: Sequence[float]) -> int:
    for i, m in enumerate(moc):
        if tuoi <= m:
            return i
    return len(moc)


def _trung_vi_theo_dai(gia: Dict[int, List[float]], dai: int, can: int, so_dai: int) -> Optional[float]:
    """Trung vị ở đúng dải; thiếu mẫu thì gộp dải kề (±1); vẫn thiếu → None."""
    ds = list(gia.get(dai, []))
    if len(ds) >= can:
        return statistics.median(ds)
    for ke in (dai - 1, dai + 1):
        if 0 <= ke <= so_dai:
            ds += gia.get(ke, [])
    return statistics.median(ds) if len(ds) >= can else None


def _trang_chu(goc: str, kenh: str, bay_gio: _dt.datetime, ngay: int) -> Tuple[Dict[str, int], Dict[str, int]]:
    """`({mã video: số ngày hiện trên trang chủ}, {tên kênh: số dòng})` trong `ngay` ngày gần nhất,
    trang chủ máy ảo của CẢ NHÓM (bỏ trùng lượt quét — `cong_thuc_v7._dong_trang_chu`)."""
    from . import cong_thuc_v7 as v7  # noqa: PLC0415

    moc = bay_gio.date()
    ngay_video: Dict[str, set] = {}
    dem_kenh: Dict[str, int] = {}
    for r in v7._dong_trang_chu(goc, kenh):
        try:
            d = _dt.date.fromisoformat(str(r.get("Lúc quét") or "")[:10])
        except ValueError:
            continue
        if not 0 <= (moc - d).days < ngay:
            continue
        ma = str(r.get("Mã video") or "")
        if ma:
            ngay_video.setdefault(ma, set()).add(d)
        ten = str(r.get("Kênh") or "").strip()
        if ten:
            dem_kenh[ten] = dem_kenh.get(ten, 0) + 1
    return {m: len(s) for m, s in ngay_video.items()}, dem_kenh


def _cung_xem(goc: str, kenh: str) -> set:
    """Mã video + mã kênh trong "khán giả của bạn cũng xem" (kho nhóm)."""
    ra: set = set()
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415
        kho = ncc.khan_gia_cung_xem_doc(goc, kenh)
    except Exception:  # noqa: BLE001
        return ra
    for ban in (kho or {}).values():
        if not isinstance(ban, dict):
            continue
        for v in ban.get("video_dang_xem") or []:
            if isinstance(v, dict):
                ra.update(str(v.get(k) or "") for k in ("video_id", "channel_id"))
        ra.update(str(c) for c in (ban.get("kenh_canh_tranh") or []) if c)
    ra.discard("")
    return ra


# ── Chấm ─────────────────────────────────────────────────────────────────────

def cham(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> KetQuaVPH:
    """Chấm đột biến VPH cho sổ content của `kenh` (mốc so sánh: kho cả nhóm)."""
    from . import cong_thuc_v7 as v7  # noqa: PLC0415 — dùng chung bộ nhận cụm để hiển thị
    from . import mot_nut  # noqa: PLC0415
    from . import tuyen_con  # noqa: PLC0415
    from .phan_tuyen import DAU_MOC_TUOI, MA_TRUNG_NIEN, TU_LOAI_TRU, _dinh_tu_loai_tru  # noqa: PLC0415
    from .phan_tuyen import cho_phep_tep_gia  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.utcnow()
    ch = nap_cau_hinh(goc, kenh)
    # 30/09/2026 — B8: hằng "Nhật" còn sót → theo hồ sơ ngách của nhóm (bậc làm tròn view, từ loại
    # trừ, mốc tuổi). Nhóm tam-ly-nhat khai đúng các hằng cũ; kênh không nhóm → hằng cũ.
    try:
        from .ho_so_ngach import doc_ngach  # noqa: PLC0415

        hs = doc_ngach(goc, kenh)
    except Exception:  # noqa: BLE001
        hs = None
    bac_view = bac_lam_tron_tu_ngach(hs)
    tu_loai_tru_hl = list(getattr(hs, "tu_loai_tru", None) or []) or list(TU_LOAI_TRU)
    moc_tuoi_hl = list(getattr(hs, "tu_tuoi", None) or []) or list(DAU_MOC_TUOI)
    canh_bao: List[str] = []
    ghi_chu: List[str] = []
    kho = _kho_nhom(goc, kenh, bay_gio)
    if not kho:
        return KetQuaVPH([], ["Sổ content (cả nhóm) đang trống — chưa có gì để đo đột biến."], [], 0)

    moc = [float(x) for x in ch["dai_tuoi_gio"]]
    so_dai = len(moc)
    theo_kenh: Dict[str, Dict[int, List[float]]] = {}
    ngach: Dict[int, List[float]] = {}
    for r in kho.values():
        t = _tuoi_gio(r["ngay"], r["luc"])
        if t is None:
            continue
        r["tuoi"] = t
        r["vph_doi"] = r["view"] / t
        dai = _dai(t, moc)
        theo_kenh.setdefault(r["kenh"], {}).setdefault(dai, []).append(r["vph_doi"])
        ngach.setdefault(dai, []).append(r["vph_doi"])

    tuyen = mot_nut.tuyen_dang_danh(goc, kenh)
    bo_qua_zats = tuyen_con.MA_TO_MO in tuyen
    # 30/09/2026 — kênh nhắm tệp NGƯỜI GIÀ (kenh.yaml `cho_phep_tep_gia: true`, kênh 5) cũng giữ
    # mốc tuổi: 60代/老後… chính là nhân vật chính của tệp ấy. Kênh không khai → như cũ.
    giu_moc_tuoi = MA_TRUNG_NIEN in tuyen or cho_phep_tep_gia(goc, kenh)
    try:
        ch_v7, _ = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    except Exception:  # noqa: BLE001
        ch_v7 = v7.CAU_HINH_MAC_DINH
    v7.nap_phan_cum(goc, kenh, ch_v7)  # cụm theo NGHĨA (AI) nếu đã phân, không thì từ khoá
    c2, h2 = db.doc(goc, kenh)
    o2 = db.chi_so_cot(list(c2))
    trang_thai = ({str(h[o2["Kênh"]]).strip(): str(h[o2["Trạng thái"]]).strip() for h in h2}
                  if "Kênh" in o2 and "Trạng thái" in o2 else {})
    tc_video, tc_kenh = _trang_chu(goc, kenh, bay_gio, int(ch.get("trang_chu_ngay", 14) or 14))
    cung = _cung_xem(goc, kenh)

    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}

    def o_(d, ten):
        i = o.get(ten)
        return str(d[i]).strip() if i is not None and i < len(d) else ""

    # Ngách của KÊNH NGUỒN — cùng phán đoán V7 dùng (AI đã đọc catalogue thì theo AI, chưa thì
    # đếm từ khoá trên catalogue kênh ấy trong sổ). Không có lớp này thì một kênh tin tức lỡ gắn
    # nhãn tuyến đúng vẫn lên đầu bảng chỉ vì bản tin bão đang nổ.
    try:
        nho_ai = v7.doc_bo_nho(goc, kenh, ch_v7)
    except Exception:  # noqa: BLE001
        nho_ai = {}
    td_theo_kenh: Dict[str, List[str]] = {}
    for d in hang:
        k_, t_ = o_(d, "Kênh"), o_(d, "Tiêu đề video")
        if k_ and t_:
            td_theo_kenh.setdefault(k_, []).append(t_)
    lac_ngach: Dict[str, bool] = {}
    for ten_k, ds_td in td_theo_kenh.items():
        ket_k = nho_ai.get("kenh:" + ten_k)
        if isinstance(ket_k, dict) and ket_k.get("ngach") in ("dung", "gan", "lac"):
            lac_ngach[ten_k] = ket_k["ngach"] == "lac"
        elif len(ds_td) >= int(ch.get("ngach_so_video", 8) or 8):
            # Nới hơn V7 (V7 cần ≥ 60% tiêu đề chạm từ ngách): VPH chỉ gạt kênh RÕ LÀ nghề khác
            # (tin tức, giải trí…) — dưới `ngach_san` tiêu đề chạm từ ngách tâm lý.
            tu = (ch_v7.get("ngach") or {}).get("tu") or []
            dung = sum(1 for t in ds_td if any(w in t for w in tu))
            lac_ngach[ten_k] = dung / float(len(ds_td)) < float(ch.get("ngach_san", 0.25))

    # 30/09/2026 — `Tăng/ngày` BẬC LÀM TRÒN đội lốt tốc độ: đo trên sổ TL1 cùng lúc 3 video khác
    # kênh cùng ra đúng 2.089/ngày (+10.000 view ÷ 4,79 ngày: bậc 万 của YouTube JP), nên VPH "hôm
    # nay" của chúng bằng hệt nhau (86,8) và thước VPH/BỨT xếp hạng theo nhiễu. Một giá trị Tăng/ngày
    # lặp ở ≥ `tang_lap_toi_da` video KHÁC NHAU, hoặc chênh view chưa tới 3 bậc hiển thị JP, là nhiễu
    # → không dùng tốc độ giữa hai lượt quét (lùi về VPH cả đời).
    dem_tang: Dict[float, int] = {}
    for r in kho.values():
        if r["tang"] > 0:
            dem_tang[round(r["tang"], 1)] = dem_tang.get(round(r["tang"], 1), 0) + 1
    tang_lap = int(ch.get("tang_lap_toi_da", 3) or 3)

    def _tang_tin_duoc(r: Dict) -> bool:
        if r["tang"] <= 0 or r["view_truoc"] <= 0:
            return False
        if dem_tang.get(round(r["tang"], 1), 0) >= tang_lap:
            return False
        return (r["view"] - r["view_truoc"]) >= 3 * _bac_hien_thi(r["view"], bac_view)

    kh = ch["khuon_phut"]
    can = int(ch.get("so_video_moc", 3) or 3)
    tran = float(ch.get("tran_dot_bien", 50) or 50)
    hs = ch["he_so_tre"]
    dem_loai: Dict[str, int] = {}

    def bo(ly):
        dem_loai[ly] = dem_loai.get(ly, 0) + 1

    ung: List[DongVPH] = []
    thay: set = set()
    for d in hang:
        link = o_(d, so.COT_LINK)
        ma = so.ma_video(link) or ""
        td = o_(d, "Tiêu đề video")
        if not ma or not td or ma in thay:
            continue
        thay.add(ma)
        ten_kenh = o_(d, "Kênh")
        if trang_thai.get(ten_kenh, db.THEO_DOI) != db.THEO_DOI:
            bo("kênh không theo dõi")
            continue
        if o_(d, so.COT_DA_LAM):
            bo("đã làm")
            continue
        if lac_ngach.get(ten_kenh):
            bo("kênh nguồn lạc ngách")
            continue
        if _dinh_tu_loai_tru(td, bo_qua_zatsugaku=bo_qua_zats, tu_loai_tru=tu_loai_tru_hl) or (
                not giu_moc_tuoi and any(m in td for m in moc_tuoi_hl)):
            bo("từ loại trừ / mốc tuổi")
            continue
        nhan = o_(d, so.COT_TUYEN)
        if nhan not in tuyen:
            bo("không đúng tuyến")
            continue
        phut = _phut(o_(d, "Thời lượng"))
        if phut is not None and not (kh[0] <= phut <= kh[1]):
            bo("độ dài ngoài khuôn")
            continue
        r = kho.get(link)
        if r is None or "tuoi" not in r:
            bo("thiếu ngày đăng")
            continue
        if r["view"] < float(ch.get("san_view", 0) or 0):
            bo("view dưới sàn")
            continue
        t = r["tuoi"]
        dong = DongVPH(ma=ma, link=link, tieu_de=td, kenh=ten_kenh, view=r["view"], ngay=r["ngay"][:10],
                       tuyen=nhan, tuoi_gio=round(t, 1), vph_doi=r["vph_doi"])
        # VPH hôm nay: video > 72 giờ đã có hai lượt quét → tốc độ GIỮA HAI LƯỢT.
        if t > moc[0] and _tang_tin_duoc(r):
            dong.vph_gan = r["tang"] / 24.0
        dong.vph = dong.vph_gan if dong.vph_gan is not None else dong.vph_doi
        dang_but = dong.vph_gan is not None and dong.vph_doi > 0 and \
            dong.vph_gan / dong.vph_doi >= float(ch.get("nguong_but", 1.5))
        if t <= 72:
            dong.he_tre = float(hs["72"])
        elif t <= 168:
            dong.he_tre = float(hs["168"])
        elif t <= 720:
            dong.he_tre = float(hs["720"])
        elif dang_but:
            dong.he_tre = float(hs["cu_dang_but"])
        else:
            bo("video cũ không bứt")
            continue
        dai = _dai(t, moc)
        m_kenh = _trung_vi_theo_dai(theo_kenh.get(ten_kenh, {}), dai, can, so_dai)
        m_ngach = _trung_vi_theo_dai(ngach, dai, can, so_dai)
        # So CÙNG THƯỚC: VPH cả đời của video này ÷ VPH cả đời của video cùng tuổi. Tốc độ hôm
        # nay (giữa hai lượt quét) đi vào thước BỨT và thước VPH, không trộn vào tỉ số này.
        dong.ty_kenh = min(tran, dong.vph_doi / m_kenh) if m_kenh else None
        dong.ty_ngach = min(tran, dong.vph_doi / m_ngach) if m_ngach else None
        ty = [x for x in (dong.ty_kenh, dong.ty_ngach) if x]
        dong.dot_bien = round(math.sqrt(ty[0] * ty[1]) if len(ty) == 2 else (ty[0] if ty else 0.0), 2)
        if dang_but and t > 720:
            # Video cũ vừa được thuật toán moi lên: đột biến của nó LÀ tỉ số bứt (trần 6 như Một nút).
            dong.dot_bien = max(dong.dot_bien, round(min(6.0, dong.vph_gan / dong.vph_doi), 2))
        if dong.dot_bien < float(ch.get("nguong_dot_bien", 0) or 0):
            bo("chưa đột biến")
            continue
        dong.trang_chu_ngay = int(tc_video.get(ma, 0))
        dong.trang_chu_kenh = int(tc_kenh.get(ten_kenh, 0))
        dong.cung_xem = ma in cung
        dong.cum = v7.cum_cua_tieu_de(td, ch_v7)
        dong.ly_do.append("{0:,.0f} view/giờ{1} · tuổi {2}".format(
            dong.vph, " (giữa hai lượt quét)" if dong.vph_gan is not None else "",
            "{0:.0f} giờ".format(t) if t < 72 else "{0:.1f} ngày".format(t / 24)).replace(",", "."))
        phan = []
        if dong.ty_kenh:
            phan.append("×{0:.1f} video cùng tuổi của kênh".format(dong.ty_kenh))
        if dong.ty_ngach:
            phan.append("×{0:.1f} cùng tuổi cả ngách".format(dong.ty_ngach))
        dong.ly_do.append("đột biến " + ", ".join(phan))
        if dang_but:
            dong.ly_do.append("video cũ đang bứt (hôm nay ×{0:.1f} tốc độ cả đời)".format(
                dong.vph_gan / dong.vph_doi))
        if dong.trang_chu_ngay:
            dong.ly_do.append("hiện {0} ngày trên trang chủ máy ảo".format(dong.trang_chu_ngay))
        if dong.cung_xem:
            dong.ly_do.append("khán giả của kênh cũng xem")
        ung.append(dong)

    if ung:
        ts = dict(ch["trong_so"])
        thuoc = {
            "dot_bien": hang_phan_tram([math.log(1 + d.dot_bien * d.he_tre) for d in ung]),
            "vph": hang_phan_tram([math.log(1 + d.vph) for d in ung]),
            "tre": hang_phan_tram([d.he_tre for d in ung]),
            "phu": hang_phan_tram([math.log1p(d.trang_chu_ngay) + 0.3 * math.log1p(d.trang_chu_kenh)
                                   + (1.0 if d.cung_xem else 0.0) for d in ung]),
        }
        co = {t: any(v) for t, v in thuoc.items()}
        tong = sum(float(ts.get(t, 0)) for t, v in co.items() if v)
        for i, d in enumerate(ung):
            if tong <= 0:
                d.diem = 0
                continue
            d.diem = int(round(100.0 * sum(float(ts.get(t, 0)) * thuoc[t][i] for t in thuoc if co[t]) / tong))
        ung.sort(key=lambda d: (-d.diem, -d.dot_bien, -d.vph))
    ghi_chu.append("VPH: kho {0} video (cả nhóm, bỏ trùng) · {1} ứng viên đột biến ≥ ×{2:g} · bỏ: {3}.".format(
        len(kho), len(ung), float(ch.get("nguong_dot_bien", 0)),
        ", ".join("{0} {1}".format(v, k) for k, v in sorted(dem_loai.items(), key=lambda x: -x[1])) or "—"))
    if not ung:
        canh_bao.append("VPH: không có video nào đột biến ≥ ×{0:g} trong tuyến đang đánh.".format(
            float(ch.get("nguong_dot_bien", 0))))
    return KetQuaVPH(ung_vien=ung, canh_bao=canh_bao, ghi_chu=ghi_chu, so_dong_kho=len(kho))


def ung_vien_chon_nguon(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> List[Dict]:
    """Bảng ứng viên theo ĐỊNH DẠNG CHUNG của mọi công thức chọn nguồn (`core/tu_chay.py`)."""
    kq = cham(goc, kenh, bay_gio=bay_gio)
    return [{"nguon": TEN, "ma": d.ma, "link": d.link, "tieu_de": d.tieu_de, "kenh": d.kenh,
             "diem": d.diem, "loai": "VPH", "view": d.view, "vph": round(d.vph, 1),
             "dot_bien": d.dot_bien, "tuoi_gio": d.tuoi_gio, "cum": list(d.cum), "tuyen": d.tuyen,
             "ly_do": list(d.ly_do)} for d in kq.ung_vien]
