"""THƯỚC THẮNG — MỘT định nghĩa "video thắng" cho MỌI bộ phận (12/10/2026).

═══ VÌ SAO (`workspace/chan-doan/{nao-vong-hoc,view-giam,v7-chon-content}-2026-10-12.md`) ═══

Trước bản này "thắng" được phán ở mốc 48h với ngưỡng max(6.000, 3 × trung vị 48h). Kênh của ta lại nổ MUỘN,
ngày 3–5, từ Trang chủ: 9/19 video cuối cùng > 10.000 hiển thị còn dưới 6.000 lúc 48h; video lớn nhất TL1
(vidGia685d6, 2.303 @46h → 28.624 @94h) bị nhãn TRƯỢT. Thêm: bản chụp muộn thường rỗng (chỉ ~17% bản > 120h có
số), nhãn thư mục ≠ tuổi thật (báo thức dồn chùm), cửa sổ `ket_muon` bắt đầu ở 96h nên số 94h bị bỏ. Mỗi bộ phận
(V7, tự học, giám đốc, bộ não) lại phán theo một kiểu → chọi nhau trên cùng một cụm.

═══ ĐỊNH NGHĨA (mọi nơi gọi hàm này, không tự chế) ═══

1. CHUỖI SỐ của một video (`doc_chuoi`): mọi thư mục chụp (`<n>h`, `tay-*`; bỏ `kenh-*`) có `impressions` hoặc
   `views` (bản rỗng bỏ). TUỔI THẬT = `captured_at` trong gói raw − giờ đăng của video (`_thong-tin.json` của BẤT
   KỲ thư mục nào) — không tin nhãn thư mục; chỉ lùi về nhãn `<n>h` khi gói không có `captured_at`. Làm sạch
   (`lam_sach`): bộ số trùng hệt nhau là một bản chụp chép nhiều nơi → giữ một (số lớn mà "đứng im" ≥ 12h là bản
   cũ chép lại → giữ bản SỚM; số nhỏ đứng im là video không được phát → giữ bản MUỘN); số cộng dồn không thể
   giảm → bản thấp hơn 90% đỉnh của bản trẻ hơn là bản hỏng (đọc 0 ở "49h" sau 6.899 ở 25h) → bỏ.
2. PHÂN VỊ THEO TUỔI (`phan_vi`): hiển thị (không có thì lượt xem) của video ở tuổi t so với các video KHÁC của
   CHÍNH kênh ở CÙNG tuổi t — mỗi video tham chiếu nội suy giữa hai bản chụp kề t (có bản trong [0,6t; 1,6t]
   mới được dùng); cận dưới/trên của số cộng dồn quyết khi nội suy không cần. Tham chiếu = tối đa
   `SO_THAM_CHIEU` video GẦN NHẤT theo giờ đăng (trước lẫn sau — chỉ so với video cũ thì kênh đang lớn thổi phồng
   nhãn thắng), nhưng CHỈ dùng bản chụp chụp TỚI lúc chốt của video đang xét (`moc_chot` = giờ đăng + 168h): số
   về sau của video khác không đổi được nhãn cũ → nhãn không trôi theo ngày, không cần sổ "đóng băng". Dưới
   `SO_THAM_CHIEU_TOI_THIEU` tham chiếu (vài video đầu đời kênh) thì phán bằng sàn tuyệt đối.
3. GIAI ĐOẠN: < 24h "non"; 24–72h (hoặc tới 96h khi video chưa qua 96h) chỉ là TÍN HIỆU SỚM (`som_phan_vi`),
   nhãn `chua_du` — KHÔNG BAO GIỜ phán ở 48h. PHÁN QUYẾT từ bản chụp hợp lệ MUỘN NHẤT trong [96h, 168h]; không
   có thì bản SỚM NHẤT sau 168h; không có nữa mà video đã qua 96h thì bản muộn nhất trong [72h, 96h) (độ tin
   thấp hơn, `phan_quyet_lui`). CHỐT: bản chụp sau 168h không bao giờ đè bản trong [96h, 168h] → nhãn đông cứng
   từ tuổi 168h.
4. NHÃN: `thang` = phân vị ≥ `PV_THANG` (top 25% của chính kênh cùng tuổi) và ≥ `SAN_THANG` hiển thị, hoặc ≥
   `THANG_TUYET_DOI` bất kể phân vị · `truot` = phân vị < `PV_TRUOT` hoặc < `SAN_PHAN_PHOI` hiển thị (không được
   phát) · còn lại `trung_binh` · chưa phán được `chua_du`. Kênh chưa có tham chiếu: chỉ sàn tuyệt đối.

`danh_gia()` là hàm THUẦN (test dựng chuỗi giả); `danh_gia_kenh()` đọc `CHANNEL/<k>/chi-so/` (lọc `ngay_bat_dau`
như `cong_thuc_v7.video_cua_kenh`). Không mạng, không Qt, chỉ đọc đĩa.

    python -m core.thuoc_thang [--kenh TL1-T7] [--goc <thư mục gốc>]   # in nhãn mọi video (chỉ đọc)
    python -m core.thuoc_thang --ghi                                   # + chấm lại lịch sử qua đường mã thường ngày
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

#: Tăng khi đổi định nghĩa — nhãn đã ghi (ván tự học, sổ dự đoán) mang số phiên bản cũ thì được chấm lại.
PHIEN_BAN = 1

GIO_SOM = (24.0, 72.0)
GIO_PHAN_QUYET = 96.0
GIO_PHAN_QUYET_LUI = 72.0
GIO_CHOT = 168.0

PV_THANG = 75.0
PV_TRUOT = 40.0
#: Tín hiệu sớm "đang nóng" (để V7/bộ não nhân bản khi còn nóng — KHÔNG phải nhãn thắng): phân vị sớm ≥ ngần này
#: và ≥ `SAN[...]["nong"]`.
PV_NONG = 90.0

#: Sàn tuyệt đối theo đại lượng: thắng cần ≥ `thang`; < `phan_phoi` = YouTube không phát (trượt dù phân vị cao —
#: kênh chết 0–24 hiển thị/video không có "top 25%"); ≥ `tuyet_doi` = thắng bất kể phân vị; kênh chưa có tham
#: chiếu thắng khi ≥ `khong_tham_chieu`; `nong` = sàn của tín hiệu nóng.
SAN: Dict[str, Dict[str, float]] = {
    "hien_thi": {"thang": 2000.0, "phan_phoi": 300.0, "tuyet_doi": 20000.0, "khong_tham_chieu": 5000.0,
                 "nong": 2500.0},
    "xem": {"thang": 300.0, "phan_phoi": 30.0, "tuyet_doi": 3000.0, "khong_tham_chieu": 750.0, "nong": 400.0},
}
SAN_THANG = SAN["hien_thi"]["thang"]
SAN_PHAN_PHOI = SAN["hien_thi"]["phan_phoi"]
THANG_TUYET_DOI = SAN["hien_thi"]["tuyet_doi"]

SO_THAM_CHIEU = 20
SO_THAM_CHIEU_TOI_THIEU = 4
#: Video tham chiếu chỉ được so ở tuổi t khi có bản chụp trong [0,6t; 1,6t] — xa hơn thì đường cong không còn
#: nói gì về tuổi t.
CUA_SO_THAM_CHIEU = (0.6, 1.6)
#: Số cộng dồn không giảm: bản thấp hơn `TI_LE_TUT` × đỉnh trước đó (trừ thêm `TUT_TOI_THIEU`) là bản hỏng.
TI_LE_TUT = 0.9
TUT_TOI_THIEU = 20.0
#: Bộ số trùng hệt nhau mà ≥ ngần này lượt và cách nhau ≥ `GIO_DUNG_IM` giờ = bản cũ chép lại (giữ bản sớm).
SO_DUNG_IM = 500.0
GIO_DUNG_IM = 12.0

THANG, TRUNG_BINH, TRUOT, CHUA_DU = "thang", "trung_binh", "truot", "chua_du"
DA_PHAN = (THANG, TRUNG_BINH, TRUOT)
#: Điểm một nhãn khi đếm tỉ lệ (Beta với số lẻ): trung bình = nửa thắng nửa trượt.
DIEM_NHAN = {THANG: 1.0, TRUNG_BINH: 0.5, TRUOT: 0.0}
TEN_NHAN = {THANG: "THẮNG", TRUNG_BINH: "trung bình", TRUOT: "trượt", CHUA_DU: "chờ"}
#: Mô tả một dòng — đưa vào lời nhắc/ báo cáo để người đọc (và LLM) biết "thắng" nghĩa là gì.
MO_TA = ("thắng = top {0:g}% hiển thị của CHÍNH kênh ở CÙNG tuổi (và ≥ {1:,.0f}), phán ở ≥ {2:g}h (chốt từ {3:g}h); "
         "trượt = dưới phân vị {4:g} hoặc < {5:,.0f} hiển thị; 24–72h chỉ là tín hiệu sớm"
         ).format(100 - PV_THANG, SAN_THANG, GIO_PHAN_QUYET, GIO_CHOT, PV_TRUOT, SAN_PHAN_PHOI).replace(",", ".")


@dataclass(frozen=True)
class Diem:
    """Một bản chụp đã đọc: tuổi (giờ), hiển thị, lượt xem, CTR; `tuoi_that` = tuổi từ `captured_at`; `luc` = giờ
    chụp thật (epoch UTC giây; None = suy từ giờ đăng + tuổi)."""
    tuoi: float
    hien_thi: Optional[float]
    xem: Optional[float]
    ctr: Optional[float] = None
    tuoi_that: bool = True
    thu_muc: str = ""
    luc: Optional[float] = None


@dataclass
class Chuoi:
    """Chuỗi số đã làm sạch của một video. `dang` = giờ đăng (epoch UTC giây) hoặc None; `bo` = số bản bỏ."""
    ma: str
    dang: Optional[float] = None
    diem: List[Diem] = field(default_factory=list)
    bo: int = 0


@dataclass
class KetQua:
    """Kết quả của MỘT video theo thước chung."""
    ma: str
    nhan: str = CHUA_DU
    phan_vi: Optional[float] = None       # phân vị ở tuổi phán (hoặc tuổi tín hiệu sớm khi chưa phán)
    tuoi: Optional[float] = None          # tuổi (giờ) của bản chụp dùng
    gia_tri: Optional[float] = None       # hiển thị (hoặc lượt xem) ở tuổi đó
    chi_so: str = "hien_thi"
    do_tin: float = 0.0
    giai_doan: str = "khong_so"           # phan_quyet | phan_quyet_lui | som | non | khong_so
    chot: bool = False                    # đã có bản chụp ≥ 96h → nhãn chỉ đổi tới 168h, sau đó đông cứng
    nong: bool = False                    # tín hiệu sớm "đang nóng" (phân vị ≥ PV_NONG và ≥ sàn nóng)
    som_phan_vi: Optional[float] = None
    som_tuoi: Optional[float] = None
    som_gia_tri: Optional[float] = None
    n_tham_chieu: int = 0
    ly_do: str = ""
    phien_ban: int = PHIEN_BAN

    @property
    def da_phan(self) -> bool:
        return self.nhan in DA_PHAN

    @property
    def thang(self) -> bool:
        return self.nhan == THANG

    def gon(self) -> Dict[str, Any]:
        """Dạng dict ngắn (ghi sổ / JSON)."""
        d = asdict(self)
        for k in ("phan_vi", "som_phan_vi"):
            if d.get(k) is not None:
                d[k] = round(float(d[k]), 1)
        for k in ("tuoi", "som_tuoi"):
            if d.get(k) is not None:
                d[k] = round(float(d[k]), 1)
        return d


# ── đọc đĩa ─────────────────────────────────────────────────────────────────

def _so(x: Any) -> Optional[float]:
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


_RE_MOC = re.compile(r"(\d+)h")
_BO_NHO: Dict[str, Tuple[Tuple, Chuoi]] = {}
_BO_NHO_TOI_DA = 6000


def _dau_thu_muc(thu_muc_video: str, con: List[str]) -> Tuple:
    """Dấu vân tay rẻ của thư mục video (tên con + mtime tong-quan.json + mtime raw/) — đổi thì đọc lại."""
    ra = []
    for c in con:
        p = os.path.join(thu_muc_video, c)
        try:
            a = os.stat(os.path.join(p, "tong-quan.json")).st_mtime_ns
        except OSError:
            a = 0
        try:
            b = os.stat(os.path.join(p, "raw")).st_mtime_ns
        except OSError:
            b = 0
        ra.append((c, a, b))
    return tuple(ra)


def doc_chuoi(thu_muc_video: str, ma: str = "") -> Chuoi:
    """Chuỗi số đã làm sạch của MỘT video từ `chi-so/<mã>/` (xem mục 1 đầu tệp). Thư mục hỏng → chuỗi rỗng."""
    from .chi_so_ytb import gom as _gom  # noqa: PLC0415 — gom nạp kho_raw, nạp muộn

    ma = ma or os.path.basename(os.path.normpath(thu_muc_video))
    try:
        con = sorted(c for c in os.listdir(thu_muc_video)
                     if not c.startswith("kenh") and os.path.isdir(os.path.join(thu_muc_video, c)))
    except OSError:
        return Chuoi(ma=ma)
    dau = _dau_thu_muc(thu_muc_video, con)
    cu = _BO_NHO.get(thu_muc_video)
    if cu is not None and cu[0] == dau:
        return cu[1]
    try:
        dang = _gom.dang_that_cua_video(thu_muc_video)
    except Exception:  # noqa: BLE001
        dang = None
    tho: List[Diem] = []
    for c in con:
        duong = os.path.join(thu_muc_video, c)
        tq = _doc_json(os.path.join(duong, "tong-quan.json"))
        if not isinstance(tq, dict):
            continue
        imp, xem = _so(tq.get("impressions")), _so(tq.get("views"))
        if imp is None and xem is None:
            continue
        try:
            cap = _gom._captured_at_that(duong)  # noqa: SLF001 — epoch UTC trong gói, không suy từ mtime
        except Exception:  # noqa: BLE001
            cap = None
        tuoi: Optional[float] = None
        that = False
        if cap is not None and dang is not None:
            tuoi, that = (cap - dang) / 3600.0, True
        else:
            m = _RE_MOC.fullmatch(c)
            if m:
                tuoi = float(m.group(1))
        if tuoi is None or tuoi < -1.0:
            continue
        tho.append(Diem(tuoi=round(max(0.0, tuoi), 2), hien_thi=imp, xem=xem, ctr=_so(tq.get("ctr")),
                        tuoi_that=that, thu_muc=c, luc=cap if that else None))
    sach, bo = lam_sach(tho)
    ra = Chuoi(ma=ma, dang=dang, diem=sach, bo=bo)
    if len(_BO_NHO) >= _BO_NHO_TOI_DA:
        _BO_NHO.clear()
    _BO_NHO[thu_muc_video] = (dau, ra)
    return ra


def lam_sach(tho: Iterable[Diem]) -> Tuple[List[Diem], int]:
    """`(chuỗi sạch theo tuổi tăng, số bản bỏ)` — bỏ bản trùng và bản hỏng (xem mục 1 đầu tệp)."""
    tho = list(tho)
    # Bản tuổi THẬT có thì bỏ bản chỉ có nhãn thư mục mang cùng bộ số (nhãn là thứ đã chứng minh sai).
    nhom: Dict[Tuple, List[Diem]] = {}
    for d in tho:
        nhom.setdefault((d.hien_thi, d.xem, d.ctr), []).append(d)
    giu: List[Diem] = []
    for ds in nhom.values():
        that = [d for d in ds if d.tuoi_that] or ds
        that.sort(key=lambda d: d.tuoi)
        so_lon = max((x for x in (that[0].hien_thi, that[0].xem) if x is not None), default=0.0)
        if len(that) > 1 and so_lon >= SO_DUNG_IM and that[-1].tuoi - that[0].tuoi >= GIO_DUNG_IM:
            giu.append(that[0])     # số lớn mà đứng im nửa ngày: bản cũ chép sang thư mục muộn
        else:
            giu.append(that[-1])    # cùng một lần chụp (cùng tuổi) hoặc video thật sự không nhích
    giu.sort(key=lambda d: (d.tuoi, d.hien_thi or 0.0, d.xem or 0.0))
    # Lượt 1: chỉ bản TUỔI THẬT — số cộng dồn không giảm (bản thấp hơn đỉnh trước đó là bản hỏng).
    that = _don_dieu([d for d in giu if d.tuoi_that])
    if not that:
        ra = _don_dieu(giu)
        return ra, len(tho) - len(ra)
    # Lượt 2: bản chỉ có nhãn thư mục (gói cũ không `captured_at`) chỉ được chen vào khi KHỚP thứ tự với các bản
    # tuổi thật kề nó — nhãn là thứ đã chứng minh sai, không được làm rơi một bản tuổi thật.
    ra = list(that)
    for d in (x for x in giu if not x.tuoi_that):
        truoc = [x for x in ra if x.tuoi <= d.tuoi]
        sau = [x for x in ra if x.tuoi > d.tuoi]
        if all(_khong_giam(a, d) for a in truoc) and all(_khong_giam(d, b) for b in sau):
            ra.append(d)
    ra.sort(key=lambda d: (d.tuoi, d.hien_thi or 0.0, d.xem or 0.0))
    return ra, len(tho) - len(ra)


def _khong_giam(a: Diem, b: Diem) -> bool:
    """Bản `b` (muộn hơn) không thấp hơn `a` quá dung sai, cho cả hiển thị lẫn lượt xem."""
    for x, y in ((a.hien_thi, b.hien_thi), (a.xem, b.xem)):
        if x is not None and y is not None and y < x * TI_LE_TUT - TUT_TOI_THIEU:
            return False
    return True


def _don_dieu(ds: Sequence[Diem]) -> List[Diem]:
    """Giữ các bản không thấp hơn đỉnh của các bản trẻ hơn (dung sai `TI_LE_TUT`, `TUT_TOI_THIEU`)."""
    ra: List[Diem] = []
    dinh_imp = dinh_xem = None
    for d in ds:
        if ((d.hien_thi is not None and dinh_imp is not None and d.hien_thi < dinh_imp * TI_LE_TUT - TUT_TOI_THIEU)
                or (d.xem is not None and dinh_xem is not None and d.xem < dinh_xem * TI_LE_TUT - TUT_TOI_THIEU)):
            continue
        ra.append(d)
        if d.hien_thi is not None:
            dinh_imp = d.hien_thi if dinh_imp is None else max(dinh_imp, d.hien_thi)
        if d.xem is not None:
            dinh_xem = d.xem if dinh_xem is None else max(dinh_xem, d.xem)
    return ra


# ── phân vị theo tuổi ───────────────────────────────────────────────────────

def _luc(x: Chuoi, d: Diem) -> Optional[float]:
    """Giờ chụp (epoch) của bản `d` thuộc video `x`: `captured_at` nếu có, không thì giờ đăng + tuổi."""
    if d.luc is not None:
        return d.luc
    return x.dang + d.tuoi * 3600.0 if x.dang is not None else None


def khoang_tai(diem: Sequence[Diem], t: float, chi_so: str = "hien_thi", *, den: Optional[float] = None,
               dang: Optional[float] = None) -> Optional[Tuple[float, float, float]]:
    """`(cận dưới, ước, cận trên)` của đại lượng ở tuổi `t` từ chuỗi một video; None nếu không có bản chụp nào
    trong [0,6t; 1,6t]. Ước = nội suy thẳng giữa hai bản kề t (một phía thì lấy bản đó). `den` (epoch): chỉ dùng
    bản chụp chụp TỚI lúc đó (`dang` = giờ đăng của video này, để suy giờ chụp khi bản không mang `luc`)."""
    if den is not None:
        x = Chuoi(ma="", dang=dang)
        diem = [d for d in diem if (_luc(x, d) is None or _luc(x, d) <= den)]
    pts = [(d.tuoi, getattr(d, chi_so)) for d in diem if getattr(d, chi_so) is not None]
    lo_w, hi_w = CUA_SO_THAM_CHIEU[0] * t, CUA_SO_THAM_CHIEU[1] * t
    if not pts or not any(lo_w <= a <= hi_w for a, _v in pts):
        return None
    truoc = [p for p in pts if p[0] <= t]
    sau = [p for p in pts if p[0] >= t]
    b = max(truoc, key=lambda p: (p[0], p[1])) if truoc else None
    a = min(sau, key=lambda p: (p[0], -p[1])) if sau else None
    lo = float(b[1]) if b else 0.0
    hi = float(a[1]) if a else math.inf
    if b and a:
        uoc = float(a[1]) if a[0] == b[0] else b[1] + (a[1] - b[1]) * (t - b[0]) / (a[0] - b[0])
    else:
        uoc = float((b or a)[1])
    return lo, float(uoc), hi


def phan_vi(gia_tri: float, khoang: Sequence[Tuple[float, float, float]]) -> Tuple[Optional[float], int]:
    """`(phân vị 0–100 của gia_tri trong các khoảng tham chiếu, số tham chiếu mập mờ)`. Cận quyết khi được (cận
    trên < giá trị → chắc dưới; cận dưới > giá trị → chắc trên), không thì so số ước; bằng nhau tính nửa."""
    if not khoang:
        return None, 0
    duoi = 0.0
    mo_ho = 0
    for lo, uoc, hi in khoang:
        if hi < gia_tri:
            duoi += 1.0
        elif lo > gia_tri:
            pass
        else:
            mo_ho += 1 if (hi != lo) else 0
            duoi += 1.0 if uoc < gia_tri else (0.5 if uoc == gia_tri else 0.0)
    return 100.0 * duoi / len(khoang), mo_ho


def moc_chot(c: Chuoi, tuoi_ban: Optional[float] = None) -> Optional[float]:
    """Lúc (epoch) nhãn của video `c` đông cứng = giờ đăng + max(`GIO_CHOT`, tuổi bản chụp phán). Số của video
    KHÁC chụp sau lúc này không được dùng để chấm `c` → nhãn không trôi sau 168h. Không biết giờ đăng → None."""
    if c.dang is None:
        return None
    return c.dang + max(GIO_CHOT, float(tuoi_ban or 0.0)) * 3600.0


def _tham_chieu(ma: str, chuoi: Dict[str, Chuoi], t: float, chi_so: str,
                den: Optional[float] = None) -> List[Tuple[float, float, float]]:
    """Khoảng ở tuổi t của tối đa `SO_THAM_CHIEU` video tham chiếu GẦN NHẤT theo giờ đăng (cả trước lẫn sau —
    kênh đang lớn thì so với chỉ video cũ sẽ thổi phồng nhãn thắng), chỉ dùng bản chụp chụp tới `den`
    (`moc_chot` của video đang chấm — video đăng sau chưa tới tuổi t lúc đó thì tự rơi khỏi tham chiếu)."""
    c = chuoi[ma]
    khac = [x for m, x in chuoi.items() if m != ma]
    if c.dang is None:
        khac.sort(key=lambda x: (x.dang is None, -(x.dang or 0.0), x.ma))
    else:
        khac.sort(key=lambda x: (x.dang is None, abs((x.dang or 0.0) - c.dang), x.ma))
    ra = []
    for x in khac:
        k = khoang_tai(x.diem, t, chi_so, den=den, dang=x.dang)
        if k is not None:
            ra.append(k)
            if len(ra) >= SO_THAM_CHIEU:
                break
    return ra


def _chon_ban(pts: Sequence[Diem], tuoi_nay: Optional[float]) -> Tuple[Optional[Diem], str]:
    """Bản chụp để PHÁN (mục 3 đầu tệp) → `(bản, giai đoạn)`; chưa phán được → `(None, "")`."""
    giua = [d for d in pts if GIO_PHAN_QUYET <= d.tuoi <= GIO_CHOT]
    if giua:
        return max(giua, key=lambda d: d.tuoi), "phan_quyet"
    sau = [d for d in pts if d.tuoi > GIO_CHOT]
    if sau:
        return min(sau, key=lambda d: d.tuoi), "phan_quyet"
    lui = [d for d in pts if GIO_PHAN_QUYET_LUI <= d.tuoi < GIO_PHAN_QUYET]
    if lui and (tuoi_nay or 0.0) >= GIO_PHAN_QUYET:
        return max(lui, key=lambda d: d.tuoi), "phan_quyet_lui"
    return None, ""


def _nhan(gia_tri: float, pv: Optional[float], chi_so: str, n: int = SO_THAM_CHIEU) -> str:
    """Nhãn từ giá trị + phân vị. Dưới `SO_THAM_CHIEU_TOI_THIEU` video tham chiếu thì phân vị chỉ là 0/50/100 của
    1–3 video → phán bằng SÀN TUYỆT ĐỐI (kênh mới, vài video đầu đời kênh)."""
    s = SAN.get(chi_so) or SAN["hien_thi"]
    if pv is None or n < SO_THAM_CHIEU_TOI_THIEU:
        if gia_tri >= s["khong_tham_chieu"]:
            return THANG
        return TRUOT if gia_tri < s["phan_phoi"] else TRUNG_BINH
    if gia_tri >= s["tuyet_doi"] or (pv >= PV_THANG and gia_tri >= s["thang"]):
        return THANG
    if pv < PV_TRUOT or gia_tri < s["phan_phoi"]:
        return TRUOT
    return TRUNG_BINH


def _do_tin(giai_doan: str, n: int, mo_ho: int, that: bool) -> float:
    he = {"phan_quyet": 1.0, "phan_quyet_lui": 0.75, "som": 0.4, "non": 0.2}.get(giai_doan, 0.0)
    he *= min(1.0, n / 8.0) if n else 0.3
    he *= 1.0 if that else 0.7
    he *= (1.0 - 0.5 * mo_ho / n) if n else 1.0
    return round(he, 2)


def _f(x: Optional[float]) -> str:
    return "?" if x is None else "{0:,.0f}".format(x).replace(",", ".")


def danh_gia_mot(ma: str, chuoi: Dict[str, Chuoi], tuoi_nay: Optional[float] = None) -> KetQua:
    """Kết quả của video `ma` so với các video khác trong `chuoi` (cùng kênh). `tuoi_nay` = tuổi HIỆN TẠI (giờ)
    của video — None thì lấy tuổi bản chụp muộn nhất."""
    c = chuoi[ma]
    chi_so = "hien_thi" if any(d.hien_thi is not None for d in c.diem) else "xem"
    pts = [d for d in c.diem if getattr(d, chi_so) is not None]
    kq = KetQua(ma=ma, chi_so=chi_so)
    if not pts:
        kq.ly_do = "chưa có bản chụp nào có số"
        return kq
    if tuoi_nay is None:
        tuoi_nay = max(d.tuoi for d in pts)
    ban, gd = _chon_ban(pts, tuoi_nay)
    den = moc_chot(c, ban.tuoi if ban is not None else None)
    # Tín hiệu sớm: bản muộn nhất trong [24h, 72h) — hoặc tới 96h khi chưa phán được (video còn non).
    tran_som = GIO_SOM[1] if ban is not None else GIO_PHAN_QUYET
    som = [d for d in pts if GIO_SOM[0] <= d.tuoi < tran_som]
    if som:
        ds = max(som, key=lambda d: d.tuoi)
        tc_s = _tham_chieu(ma, chuoi, ds.tuoi, chi_so, den)
        pv_s, _mh = phan_vi(getattr(ds, chi_so), tc_s)
        kq.som_phan_vi, kq.som_tuoi, kq.som_gia_tri = pv_s, ds.tuoi, getattr(ds, chi_so)
        s = SAN.get(chi_so) or SAN["hien_thi"]
        kq.nong = bool(kq.som_gia_tri >= s["nong"] and (
            (pv_s is not None and pv_s >= PV_NONG and len(tc_s) >= SO_THAM_CHIEU_TOI_THIEU)
            or kq.som_gia_tri >= s["khong_tham_chieu"] and len(tc_s) < SO_THAM_CHIEU_TOI_THIEU))
    if ban is None:
        moi = max(pts, key=lambda d: d.tuoi)
        kq.giai_doan = "som" if moi.tuoi >= GIO_SOM[0] else "non"
        kq.tuoi, kq.gia_tri = moi.tuoi, getattr(moi, chi_so)
        tc = _tham_chieu(ma, chuoi, moi.tuoi, chi_so, den)
        kq.phan_vi, mo_ho = phan_vi(kq.gia_tri, tc)
        kq.n_tham_chieu = len(tc)
        kq.do_tin = _do_tin(kq.giai_doan, len(tc), mo_ho, moi.tuoi_that)
        kq.ly_do = "chưa đủ tuổi phán: bản có số muộn nhất @{0:.0f}h ({1}) — {2}".format(
            moi.tuoi, _f(kq.gia_tri), "tín hiệu sớm" if kq.giai_doan == "som" else "còn non")
        return kq
    v = float(getattr(ban, chi_so))
    tc = _tham_chieu(ma, chuoi, ban.tuoi, chi_so, den)
    pv, mo_ho = phan_vi(v, tc)
    kq.nhan = _nhan(v, pv, chi_so, len(tc))
    kq.phan_vi, kq.tuoi, kq.gia_tri, kq.giai_doan = pv, ban.tuoi, v, gd
    kq.chot = gd == "phan_quyet"
    kq.n_tham_chieu = len(tc)
    kq.do_tin = _do_tin(gd, len(tc), mo_ho, ban.tuoi_that)
    kq.ly_do = "{0} @{1:.0f}h: {2} {3} = phân vị {4} so {5} video kênh cùng tuổi{6}{7}".format(
        TEN_NHAN[kq.nhan], ban.tuoi, _f(v), "hiển thị" if chi_so == "hien_thi" else "lượt xem",
        "?" if pv is None else "{0:.0f}".format(pv), len(tc),
        " (ít tham chiếu → phán theo sàn tuyệt đối)" if len(tc) < SO_THAM_CHIEU_TOI_THIEU else "",
        "" if ban.tuoi_that else " (tuổi theo nhãn thư mục)")
    return kq


def danh_gia(chuoi: Dict[str, Chuoi], *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, KetQua]:
    """`{mã: KetQua}` cho mọi video trong `chuoi` (các video của MỘT kênh). Hàm thuần. `bay_gio` (giờ UTC không
    múi, như `cong_thuc_v7`) để biết tuổi hiện tại của video; None = tuổi bản chụp muộn nhất."""
    ra: Dict[str, KetQua] = {}
    bg = (bay_gio.replace(tzinfo=_dt.timezone.utc).timestamp() if bay_gio is not None else None)
    for ma, c in chuoi.items():
        tuoi_nay = (bg - c.dang) / 3600.0 if (bg is not None and c.dang is not None) else None
        ra[ma] = danh_gia_mot(ma, chuoi, tuoi_nay)
    return ra


def muc_thang(chuoi: Dict[str, Chuoi], tuoi: float = GIO_PHAN_QUYET, chi_so: str = "hien_thi") -> Optional[float]:
    """Hiển thị cần có ở tuổi `tuoi` để vào top `100 − PV_THANG`% của kênh (≥ sàn thắng) — để HIỂN THỊ cho người
    đọc/LLM ("thắng ≈ ≥ X hiển thị lúc ~4 ngày"). Dùng `SO_THAM_CHIEU` video mới nhất có số ở tuổi đó; < 4 → None."""
    ds = sorted(chuoi.values(), key=lambda x: -(x.dang or 0.0))
    uoc = []
    for x in ds:
        k = khoang_tai(x.diem, tuoi, chi_so)
        if k is not None:
            uoc.append(k[1])
            if len(uoc) >= SO_THAM_CHIEU:
                break
    if len(uoc) < SO_THAM_CHIEU_TOI_THIEU:
        return None
    uoc.sort()
    vt = (len(uoc) - 1) * PV_THANG / 100.0
    i = int(math.floor(vt))
    j = min(len(uoc) - 1, i + 1)
    muc = uoc[i] + (uoc[j] - uoc[i]) * (vt - i)
    return max((SAN.get(chi_so) or SAN["hien_thi"])["thang"], muc)


def chuoi_ho_so(hs: Dict[str, Any], ma: str = "") -> Chuoi:
    """Chuỗi số dựng từ các mốc của HỒ SƠ video (`chi_so.<mốc>` có `moc_gio_that` = tuổi thật lúc chụp) — đường
    lùi khi video không có thư mục `chi-so/` (vd. mã bắt đầu bằng "-" bị cắt tên thư mục). Mốc thiếu tuổi thật thì
    bỏ (không đoán)."""
    tho = []
    for ten, gt in ((hs or {}).get("chi_so") or {}).items():
        if not isinstance(gt, dict):
            continue
        imp, xem, g = _so(gt.get("impressions")), _so(gt.get("views")), _so(gt.get("moc_gio_that"))
        if g is None or (imp is None and xem is None):
            continue
        tho.append(Diem(tuoi=float(g), hien_thi=imp, xem=xem, ctr=_so(gt.get("ctr")), tuoi_that=True,
                        thu_muc=str(ten)))
    sach, bo = lam_sach(tho)
    return Chuoi(ma=ma or str((hs or {}).get("video_id") or ""), dang=None, diem=sach, bo=bo)


def danh_gia_them(c: Chuoi, chuoi: Dict[str, Chuoi], tuoi_nay: Optional[float] = None) -> KetQua:
    """Chấm MỘT chuỗi ngoài danh sách (`chuoi_ho_so`) so với các video của kênh — KHÔNG làm đổi nhãn video nào khác
    (mỗi video của kênh đã có nhãn riêng, tính trên đúng tập của nó)."""
    khoa = "\x00them:" + (c.ma or "?")
    kq = danh_gia_mot(khoa, dict(chuoi, **{khoa: c}), tuoi_nay)
    kq.ma = c.ma
    return kq


def tuoi_ho_so(hs: Dict[str, Any], ngay_du_phong: str = "", bay_gio: Optional[float] = None) -> Optional[float]:
    """Tuổi hiện tại (giờ, theo NGÀY) của video hồ sơ — lịch đăng `dd/mm/yyyy`, `ngay_dang` ISO, không thì
    `ngay_du_phong` (ngày ghi ván); không biết → None."""
    import time as _time  # noqa: PLC0415

    nd = ""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str((hs or {}).get("lich_dang") or ""))
    if m:
        nd = "{0}-{1:02d}-{2:02d}".format(m.group(3), int(m.group(2)), int(m.group(1)))
    else:
        for x in ((hs or {}).get("ngay_dang"), ngay_du_phong):
            if re.match(r"\d{4}-\d\d-\d\d", str(x or "")):
                nd = str(x)[:10]
                break
    if not nd:
        return None
    try:
        return max(0.0, ((bay_gio or _time.time()) - _time.mktime(_time.strptime(nd, "%Y-%m-%d"))) / 3600.0)
    except (ValueError, OverflowError):
        return None


# ── so cụm với nền (giám đốc kênh: chỉ cấm cụm khi chắc chắn kém) ──────────

def _beta_ln(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def xac_suat_kem_hon(cum: Iterable[str], nen: Iterable[str], buoc: int = 400) -> Optional[float]:
    """P(tỉ lệ "tốt" của cụm < của nền) với Beta(1 + điểm, 1 + n − điểm) mỗi bên, điểm = `DIEM_NHAN` (thắng 1,
    trung bình 0,5, trượt 0). Tích phân số trên lưới (tất định). Một bên không có nhãn → None."""
    def tham(ds: Iterable[str]) -> Optional[Tuple[float, float]]:
        xs = [DIEM_NHAN[x] for x in ds if x in DIEM_NHAN]
        if not xs:
            return None
        s = sum(xs)
        return 1.0 + s, 1.0 + len(xs) - s
    p1, p2 = tham(cum), tham(nen)
    if p1 is None or p2 is None:
        return None
    (a1, b1), (a2, b2) = p1, p2
    h = 1.0 / buoc
    ln1, ln2 = _beta_ln(a1, b1), _beta_ln(a2, b2)
    cdf1 = 0.0
    tong = 0.0
    for i in range(buoc):
        x = (i + 0.5) * h
        f1 = math.exp((a1 - 1) * math.log(x) + (b1 - 1) * math.log(1 - x) - ln1) * h
        f2 = math.exp((a2 - 1) * math.log(x) + (b2 - 1) * math.log(1 - x) - ln2) * h
        tong += f2 * (cdf1 + 0.5 * f1)
        cdf1 += f1
    return max(0.0, min(1.0, tong))


# ── đọc cả kênh ─────────────────────────────────────────────────────────────

def chuoi_kenh(goc: str, kenh: str) -> Dict[str, Chuoi]:
    """`{mã video: Chuoi}` của mọi video trong `CHANNEL/<k>/chi-so/` — CÙNG tập `cong_thuc_v7.video_cua_kenh`
    (tên thư mục 11 ký tự, lọc `ngay_bat_dau` của kenh.yaml)."""
    from .chi_so_ytb import loc_video as _loc  # noqa: PLC0415
    from .kenh import duong_kenh  # noqa: PLC0415

    thu_muc = os.path.join(duong_kenh(goc, kenh), "chi-so")
    moc = _loc.moc_cua_thu_muc(duong_kenh(goc, kenh))
    ra: Dict[str, Chuoi] = {}
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return ra
    for ma in ten:
        duong = os.path.join(thu_muc, ma)
        if len(ma) != 11 or not os.path.isdir(duong):
            continue
        if moc and not _loc.trong_pham_vi(moc, _loc.ngay_dang_cua_video(duong)):
            continue
        ra[ma] = doc_chuoi(duong, ma)
    return ra


def danh_gia_kenh(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, KetQua]:
    """`{mã video: KetQua}` của một kênh (đọc đĩa). `bay_gio` giờ UTC không múi; None = bây giờ."""
    return danh_gia(chuoi_kenh(goc, kenh), bay_gio=bay_gio or _dt.datetime.utcnow())


def dem_nhan(ket: Dict[str, KetQua]) -> Dict[str, int]:
    """Đếm nhãn: `{thang, trung_binh, truot, chua_du}`."""
    ra = {THANG: 0, TRUNG_BINH: 0, TRUOT: 0, CHUA_DU: 0}
    for k in ket.values():
        ra[k.nhan] = ra.get(k.nhan, 0) + 1
    return ra


def ghi_lai(goc: str, kenh: str, *, log: Any = None) -> Dict[str, Any]:
    """CHẤM LẠI lịch sử của một kênh theo thước chung — QUA ĐÚNG ĐƯỜNG MÃ THƯỜNG NGÀY (không sửa tay tệp nào):
    `tu_hoc.cham_van` (ván: `ket`, bỏ nhãn 48h đời trước) + `ghi_bang_diem_md`, `chien_luoc.ket_qua.ghi_tep`
    (thống kê công thức), sổ dự đoán giám đốc `so_thi_nghiem.cham_du_doan` + `hoi_dong.do_chinh_xac` (quyền tự áp
    tính lại trên nhãn mới). Vòng học / lượt giám đốc kế tiếp cũng tự làm đúng việc này; hàm này để chạy NGAY một lần.
    Trả `{tu_hoc, du_doan, do_chinh_xac, loi}`; mỗi bước hỏng thì ghi `loi`, bước khác vẫn chạy."""
    ra: Dict[str, Any] = {"kenh": kenh, "loi": []}

    def buoc(ten: str, f: Any) -> None:
        try:
            ra[ten] = f()
        except Exception as loi:  # noqa: BLE001 — một bước hỏng không chặn bước khác
            ra["loi"].append("{0}: {1}: {2}".format(ten, type(loi).__name__, str(loi)[:160]))

    from . import tu_hoc  # noqa: PLC0415

    buoc("tu_hoc", lambda: tu_hoc.cham_van(goc, kenh))
    buoc("bang_diem", lambda: tu_hoc.ghi_bang_diem_md(goc, kenh))

    def _chien_luoc() -> str:
        from .chien_luoc import ket_qua  # noqa: PLC0415

        return ket_qua.ghi_tep(goc, kenh, log=log)

    buoc("chien_luoc", _chien_luoc)

    def _giam_doc() -> Dict[str, Any]:
        from .giam_doc import du_lieu, hoi_dong  # noqa: PLC0415
        from .giam_doc import so_thi_nghiem as stn  # noqa: PLC0415

        bs = du_lieu.tom_tat(goc, kenh)
        tc = stn.cham_du_doan(goc, kenh, {v["id"]: v.get("ket_luan") or "" for v in bs.video})
        dcx = hoi_dong.do_chinh_xac(goc, kenh)
        return {"cham_du_doan": tc, "quyen_du_doan": ((dcx.get("loai") or {}).get("du_doan") or {}).get("quyen")}

    buoc("giam_doc", _giam_doc)
    return ra


def main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.thuoc_thang", description="Nhãn thắng theo thước chung.")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p.add_argument("--kenh", action="append", default=[])
    p.add_argument("--ghi", action="store_true",
                   help="chấm lại lịch sử (ván tự học, sổ dự đoán, độ chính xác) qua đường mã thường ngày")
    a = p.parse_args(argv)
    kenh_ds = a.kenh
    if not kenh_ds:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        kenh_ds = list(liet_ke_kenh(a.goc))
    print("Thước thắng v{0}: {1}".format(PHIEN_BAN, MO_TA))
    for k in kenh_ds:
        kq = danh_gia_kenh(a.goc, k)
        if not kq:
            continue
        print("\n== {0}: {1}".format(k, dem_nhan(kq)))
        for ma, x in sorted(kq.items(), key=lambda kv: -(kv[1].phan_vi or -1)):
            print("  {0} {1:10s} pv {2:>5} @{3:>5}h {4:>8} tin {5:.2f} {6}{7}".format(
                ma, x.nhan, "?" if x.phan_vi is None else "{0:.0f}".format(x.phan_vi),
                "?" if x.tuoi is None else "{0:.0f}".format(x.tuoi), _f(x.gia_tri), x.do_tin, x.giai_doan,
                " NÓNG" if x.nong else ""))
        if a.ghi:
            r = ghi_lai(a.goc, k)
            print("  → chấm lại: tự học {0} · dự đoán giám đốc {1}{2}".format(
                {kk: (r.get("tu_hoc") or {}).get(kk) for kk in ("ket", "thang", "da_phan", "xoa_cu", "dung")},
                (r.get("giam_doc") or {}).get("cham_du_doan"), " · LỖI " + "; ".join(r["loi"]) if r["loi"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
