"""Bảng số của giám đốc kênh — `tom_tat(goc, ma) -> BangSo`.

CHỈ ĐỌC ĐĨA, 0 đồng, không gọi mạng. Tái dùng các bộ đọc sẵn có, không viết lại:

  * video + ngưỡng thắng ..... `chien_luoc.ket_qua.video_kenh` (→ `cong_thuc_v7.video_cua_kenh`, đã lọc
                               `ngay_bat_dau` qua `loc_video`), kết luận `ket_qua.ket_luan`
  * bản chụp từng mốc ........ `chi-so/<vid>/<N>h/tong-quan.json` + `traffic-type.csv` (dòng Browse),
                               tuổi thật `chi_so_ytb.gom.tuoi_that_gio`
  * sub trọn đời / video ..... `ket_qua._sub_theo_video` (`bang-tom-tat.csv`)
  * số kênh trọn đời ......... `kenh-theo-ngay.csv` (cộng dồn — hiệu hai dòng = số trong khoảng)
  * nguồn / công thức ........ `ho_so_video.nguon_cua_goi` + `ho-so-video/*.json`
  * kết quả công thức ........ `ket_qua.thong_ke`, tệp `nghien-cuu/chien-luoc.json`
  * bài học .................. `chien_luoc.bai_hoc.doc`
  * mục tiêu / YPP ........... `NguCanh.muc_tieu()` (bản gọn của biên tập viên nếu có), `muc_tieu_ypp`
  * biên tập cuối ............ `nghien-cuu/bien-tap/<ngày>.json` (`nhan_dinh`)
  * sổ của giám đốc .......... `giam-doc/trang-thai.json`, `giam-doc/thi-nghiem.json`

Hỏng nguồn nào thì trường đó rỗng và `ghi_chu` ghi một dòng — không ném lỗi ra nơi gọi.
"""

from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

THU_MUC = "giam-doc"
_RE_MOC = re.compile(r"(\d+)h")


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def so(x: Any) -> Optional[float]:
    """Số từ chuỗi Studio ("1.709", "4,04%", "") — None khi không đọc được."""
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def chu_so(x: Any, le: int = 0, duoi: str = "") -> str:
    """Số → chữ kiểu Việt (chấm nghìn, phẩy thập phân); None → "?"."""
    if x is None:
        return "?"
    try:
        return "{0:,.{1}f}".format(float(x), le).replace(",", "_").replace(".", ",").replace("_", ".") + duoi
    except (TypeError, ValueError):
        return str(x)


def trung_vi(xs: List[float]) -> Optional[float]:
    """Trung vị, None khi rỗng."""
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def thu_muc_kenh(goc: str, ma: str) -> str:
    """`CHANNEL/<ma>`."""
    from ..kenh import duong_kenh  # noqa: PLC0415

    return duong_kenh(goc, ma)


def thu_muc_giam_doc(goc: str, ma: str) -> str:
    """`CHANNEL/<ma>/giam-doc` — sổ riêng của giám đốc kênh này."""
    return os.path.join(thu_muc_kenh(goc, ma), THU_MUC)


@dataclass
class BangSo:
    """Mọi số giám đốc cần cho một kênh, đọc một lần. `video` mới → cũ."""
    goc: str
    ma_kenh: str
    bay_gio: _dt.datetime
    cai: Dict[str, Any] = field(default_factory=dict)          # kenh.yaml
    muc_tieu: str = ""
    giai_doan: str = ""
    ypp: Dict[str, Any] = field(default_factory=dict)          # muc_tieu_ypp: rang_buoc, sub, gio_xem, thieu_*
    thi_truong: Dict[str, Any] = field(default_factory=dict)
    ctr_muc_tieu: Optional[float] = None
    nhan_ctr_muc_tieu: str = ""
    nguong_thang_48h: Optional[float] = None
    video: List[Dict[str, Any]] = field(default_factory=list)
    kenh_ngay: List[Dict[str, Any]] = field(default_factory=list)  # cộng dồn trọn đời, cũ → mới
    cong_thuc: Dict[str, Any] = field(default_factory=dict)        # ket_qua.thong_ke 28 ngày
    chien_luoc_tep: Dict[str, Any] = field(default_factory=dict)
    bai_hoc: List[Dict[str, Any]] = field(default_factory=list)
    luat_chon: List[str] = field(default_factory=list)
    ten_cum: Dict[str, str] = field(default_factory=dict)          # mã cụm → tên người đọc (V7)
    bien_tap_cuoi: Dict[str, Any] = field(default_factory=dict)
    trang_thai: Dict[str, Any] = field(default_factory=dict)       # giam-doc/trang-thai.json
    ghi_chu: List[str] = field(default_factory=list)

    @property
    def n_48h(self) -> int:
        """Số video có số hiển thị 48h — ngưỡng thắng tính từ chừng này video (< 5 = ngưỡng chưa vững)."""
        return sum(1 for v in self.video if v.get("hien_thi_48h") is not None)

    @property
    def phut_muc_tieu(self) -> Optional[float]:
        """`phut_muc_tieu` đang dùng (kenh.yaml > thị trường)."""
        return so(self.cai.get("phut_muc_tieu", self.thi_truong.get("phut_muc_tieu")))

    def video_theo_id(self, vid: str) -> Optional[Dict[str, Any]]:
        """Một video của kênh theo mã YouTube."""
        return next((v for v in self.video if v["id"] == vid), None)

    def cum(self, ma: str) -> str:
        """“Tên cụm” (mã) cho câu người đọc."""
        ten = self.ten_cum.get(ma)
        return "“{0}” ({1})".format(ten, ma) if ten else ma


# ── bản chụp của một video ──────────────────────────────────────────────────

def _dong_browse(thu_muc_moc: str) -> Dict[str, Optional[float]]:
    """Dòng "Browse features" của `traffic-type.csv` → hiển thị + CTR trang chủ."""
    from ..chi_so_ytb.gom import doc_csv  # noqa: PLC0415

    for dong in doc_csv(os.path.join(thu_muc_moc, "traffic-type.csv")):
        if dong and dong[0].strip() == "Browse features" and len(dong) > 2:
            return {"hien_thi_browse": so(dong[1]), "ctr_browse": so(dong[2])}
    return {}


def doc_ban_chup(thu_muc_video: str) -> List[Dict[str, Any]]:
    """Mọi bản chụp `<N>h/` của một video, theo tuổi tăng dần. Tuổi = tuổi THẬT lúc chụp (lùi về nhãn
    thư mục khi gói chưa có `captured_at`). Mỗi bản: tuoi, hien_thi, ctr, xem, sub, gio_xem, avd_giay,
    avd_pct, pct_browse, pct_de_xuat, ctr_browse, gx_1k (giờ xem / 1.000 hiển thị)."""
    from ..chi_so_ytb.gom import tuoi_that_gio  # noqa: PLC0415

    ra: List[Dict[str, Any]] = []
    try:
        ten = os.listdir(thu_muc_video)
    except OSError:
        return ra
    for con in ten:
        m = _RE_MOC.fullmatch(con)
        if not m:
            continue
        duong = os.path.join(thu_muc_video, con)
        tq = _doc_json(os.path.join(duong, "tong-quan.json")) or {}
        imp = so(tq.get("impressions"))
        if imp is None:
            continue
        try:
            tuoi = tuoi_that_gio(duong)
        except Exception:  # noqa: BLE001
            tuoi = None
        tr = tq.get("traffic_chuan") or tq.get("traffic") or {}
        gio = so(tq.get("watch_hours"))
        b = {"moc": con, "tuoi": round(float(tuoi if tuoi is not None else int(m.group(1))), 1),
             "hien_thi": imp, "ctr": so(tq.get("ctr")), "xem": so(tq.get("views")),
             "sub": so(tq.get("subs")), "gio_xem": gio, "avd_giay": so(tq.get("avd_giay")),
             "avd_pct": so(tq.get("avd_pct")), "dai_giay": so(tq.get("thoi_luong_giay")),
             "pct_browse": so(tr.get("browse")) if isinstance(tr, dict) else None,
             "pct_de_xuat": so(tr.get("related")) if isinstance(tr, dict) else None,
             "gx_1k": round(1000.0 * gio / imp, 2) if gio is not None and imp else None}
        b.update(_dong_browse(duong))
        ra.append(b)
    ra.sort(key=lambda x: x["tuoi"])
    return ra


def ban_chup_gan(v: Dict[str, Any], gio: float, lo: float, hi: float) -> Optional[Dict[str, Any]]:
    """Bản chụp có tuổi trong [lo, hi] gần `gio` nhất, None nếu không có."""
    ds = [b for b in v.get("chup") or [] if lo <= b["tuoi"] <= hi]
    return min(ds, key=lambda b: abs(b["tuoi"] - gio)) if ds else None


def moc_52(v: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Bản chụp ở giờ 52 (khung phán 48–85h) — mốc so sánh chuẩn của giám đốc."""
    return ban_chup_gan(v, 52.0, 44.0, 85.0)


def ctr_trang_chu(v: Dict[str, Any], lo: float = 36.0, hi: float = 1e9) -> Optional[Dict[str, Any]]:
    """Bản chụp MỚI NHẤT trong [lo, hi] giờ có CTR trang chủ (dòng Browse của traffic-type.csv —
    không phải bản chụp nào cũng có bảng này)."""
    ds = [b for b in v.get("chup") or [] if b.get("ctr_browse") is not None and lo <= b["tuoi"] <= hi]
    return ds[-1] if ds else None


def moi_nhat(v: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Bản chụp mới nhất (tuổi lớn nhất)."""
    ds = v.get("chup") or []
    return ds[-1] if ds else None


def video_sau(bs: "BangSo", tu: Any, *, qua_gio: float = 52.0, id_tn: str = "") -> List[Dict[str, Any]]:
    """Video của TOOL đăng sau mốc `tu` (ISO/datetime) và đã quá `qua_gio` giờ — mẫu đo của một thí
    nghiệm. Video đã gắn `id_tn` trong hồ sơ (`thi_nghiem`: các id cách nhau dấu phẩy — `ho_so_video.tao_ho_so`)
    luôn được tính."""
    if not isinstance(tu, _dt.datetime):
        tu = _dt.datetime.fromisoformat(str(tu)[:19])
    return [v for v in bs.video if v.get("tu_tool") and (v.get("tuoi_gio") or 0) >= qua_gio
            and ((id_tn and id_tn in str(v.get("thi_nghiem") or "").split(","))
                 or (v.get("dang_luc") and v["dang_luc"] >= tu))]


def ket_luan_so(tn: Dict[str, Any], moi: List[float]) -> Dict[str, Any]:
    """So trung vị mẫu mới với nền của thí nghiệm. Chưa đủ `co_mau` → chua_du; ≥ +30% → mo_rong;
    ≥ +10% → giu; còn lại (hoà hoặc tệ hơn) → bo (không chứng minh được tốt hơn thì trả về cũ)."""
    moi = [x for x in moi if x is not None]
    nen = so((tn.get("nen") or {}).get("gia_tri"))
    tv = trung_vi(moi)
    s = {"nen": nen, "moi": round(tv, 3) if tv is not None else None, "n": len(moi)}
    if len(moi) < int(tn.get("co_mau") or 1) or nen is None or tv is None:
        return {"ket": "chua_du", "so": s}
    ti = tv / nen if nen else 1.0
    ket = "mo_rong" if ti >= 1.3 else "giu" if ti >= 1.1 else "bo"
    return {"ket": ket, "so": dict(s, ti_le=round(ti, 2))}


# ── số cấp kênh (kenh-theo-ngay.csv, cộng dồn trọn đời) ─────────────────────

def _doc_kenh_ngay(duong: str) -> List[Dict[str, Any]]:
    from ..chi_so_ytb.gom import doc_csv  # noqa: PLC0415

    hang = doc_csv(duong)
    if not hang:
        return []
    cot = {c.strip(): i for i, c in enumerate(hang[0])}
    ra: List[Dict[str, Any]] = []
    for d in hang[1:]:
        def lay(ten: str) -> Optional[float]:
            i = cot.get(ten)
            return so(d[i]) if i is not None and i < len(d) else None
        try:
            luc = _dt.datetime.strptime(d[cot["Lúc chụp"]].strip()[:16], "%Y-%m-%d %H:%M")
        except (KeyError, IndexError, ValueError):
            continue
        ra.append({"luc": luc, "xem": lay("Lượt xem"), "gio_xem": lay("Giờ xem"), "sub": lay("Đăng ký"),
                   "hien_thi": lay("Lượt hiển thị"), "ctr": lay("Tỷ lệ bấm")})
    ra.sort(key=lambda x: x["luc"])
    return ra


def cong_don(bs: BangSo, khoa: str, luc: _dt.datetime) -> Optional[float]:
    """Số cộng dồn `khoa` của kênh tại `luc` (nội suy thẳng giữa hai dòng); None ngoài vùng có số."""
    ds = [(d["luc"], d[khoa]) for d in bs.kenh_ngay if d.get(khoa) is not None]
    if not ds or luc < ds[0][0] or luc > ds[-1][0] + _dt.timedelta(hours=36):
        return None
    if luc >= ds[-1][0]:
        return ds[-1][1]
    for (t0, v0), (t1, v1) in zip(ds, ds[1:]):
        if t0 <= luc <= t1:
            k = (luc - t0).total_seconds() / max(1.0, (t1 - t0).total_seconds())
            return v0 + (v1 - v0) * k
    return None


def trong_khoang(bs: BangSo, khoa: str, tu: _dt.datetime, den: _dt.datetime) -> Optional[float]:
    """Số `khoa` (hiển thị, giờ xem, sub…) của kênh trong [tu, den]."""
    a, b = cong_don(bs, khoa, tu), cong_don(bs, khoa, den)
    return None if a is None or b is None else max(0.0, b - a)


def so_video_dang(bs: BangSo, tu: _dt.datetime, den: _dt.datetime) -> int:
    """Số video kênh đăng trong [tu, den]."""
    return sum(1 for v in bs.video if v.get("dang_luc") and tu <= v["dang_luc"] <= den)


def moc_cuoi_kenh(bs: BangSo) -> Optional[_dt.datetime]:
    """Lúc chụp mới nhất có số hiển thị cấp kênh."""
    ds = [d["luc"] for d in bs.kenh_ngay if d.get("hien_thi") is not None]
    return ds[-1] if ds else None


# ── dựng bảng ───────────────────────────────────────────────────────────────

def _gio_dia_phuong(chu: str) -> Optional[_dt.datetime]:
    """`ngay_dang` Studio (ISO giờ UTC) → giờ máy, không múi."""
    chu = str(chu or "")
    for dang, n in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            t = _dt.datetime.strptime(chu[:n], dang)
        except ValueError:
            continue
        if n == 10:
            return t
        return t.replace(tzinfo=_dt.timezone.utc).astimezone().replace(tzinfo=None)
    return None


def _video(goc: str, ma: str, bs: BangSo) -> None:
    from ..chien_luoc import ket_qua  # noqa: PLC0415

    vm_theo_id, bs.nguong_thang_48h = ket_qua.video_kenh(goc, ma)
    ho_so_goi = ket_qua.ho_so_theo_goi(goc, ma)
    try:
        from .. import ho_so_video  # noqa: PLC0415

        nguon = ho_so_video.nguon_cua_goi(goc, ma)
    except Exception:  # noqa: BLE001
        nguon = {}
        bs.ghi_chu.append("không đọc được sổ nguồn (ho_so_video.nguon_cua_goi)")
    ho_so_id = {str(h.get("video_id")): (g, h) for g, h in ho_so_goi.items() if h.get("video_id")}
    sub = ket_qua._sub_theo_video(goc, ma)  # noqa: SLF001 — bộ đọc bang-tom-tat.csv có sẵn
    thu_muc = os.path.join(thu_muc_kenh(goc, ma), "chi-so")
    for vid, vm in vm_theo_id.items():
        g, hs = ho_so_id.get(vid, ("", {}))
        n = nguon.get(g) or {}
        chup = doc_ban_chup(os.path.join(thu_muc, vid))
        su, xem = sub.get(vid, (None, None))
        dai = next((b["dai_giay"] for b in reversed(chup) if b.get("dai_giay")), None) or so(hs.get("thoi_luong_giay"))
        bs.video.append({
            "id": vid, "ma_goi": g, "tieu_de": vm.tieu_de or str(hs.get("tieu_de") or ""),
            "ngay_dang": (vm.ngay_dang or "")[:10], "dang_luc": _gio_dia_phuong(vm.ngay_dang),
            "tuoi_gio": round(vm.tuoi_gio, 1) if vm.tuoi_gio is not None else None,
            "dai_giay": dai, "cum": list(vm.cum or []), "cong_thuc": str(n.get("cong_thuc") or ""),
            "tham_do": bool(n.get("tham_do")), "thang": bool(vm.thang),
            "ket_luan": ket_qua.ket_luan(vm, hs, bs.nguong_thang_48h),
            "hien_thi_13h": vm.hien_thi_13h, "hien_thi_48h": vm.hien_thi_48h,
            "sub_tron_doi": su, "xem_tron_doi": xem,
            "sub_1k": round(1000.0 * su / xem, 2) if su is not None and xem else None,
            "chup": chup, "tieu_de_da_cham": list(((hs.get("tieu_de_cham") or {}).get("ung_vien")) or []),
            "lich_su_sua": list(hs.get("lich_su_sua") or []), "thi_nghiem": hs.get("thi_nghiem") or "",
            "tu_tool": bool(g),
        })
    bs.video.sort(key=lambda v: (v.get("dang_luc") or _dt.datetime.min), reverse=True)


def _muc_tieu(goc: str, ma: str, bs: BangSo) -> None:
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415
    from ..chien_luoc import ngu_canh  # noqa: PLC0415

    try:
        ch, _ = v7.nap_cau_hinh(goc, ma, ghi_neu_thieu=False)
        bs.ten_cum = {k: str((o or {}).get("ten") or "") for k, o in (ch.get("cum") or {}).items()
                      if isinstance(o, dict) and o.get("ten")}
        co_v7 = v7.da_co_video_thang(goc, ma, ch=ch)
    except Exception:  # noqa: BLE001
        co_v7 = False
    nc = ngu_canh.dung(goc, ma, co_v7=co_v7, bay_gio=bs.bay_gio)
    bs.giai_doan, bs.thi_truong, bs.luat_chon = nc.giai_doan, dict(nc.thi_truong), list(nc.luat_chon)
    try:
        from .. import bien_tap_content as btc  # noqa: PLC0415

        bs.muc_tieu = btc._muc_tieu_gon(goc, ma, nc)  # noqa: SLF001 — cùng 3 dòng biên tập viên đọc
        bs.ypp = btc.muc_tieu_ypp(goc, ma)
    except Exception:  # noqa: BLE001
        bs.muc_tieu = nc.muc_tieu()
        bs.ypp = {"rang_buoc": "chua_co_so"}
    bs.ctr_muc_tieu, bs.nhan_ctr_muc_tieu = so(bs.thi_truong.get("ctr_trang_chu_muc_tieu")), "mặc định ngách"
    for b in bs.bai_hoc:
        if b.get("truc") == "ctr_trang_chu" and b.get("pham_vi") == "kenh" and int(b.get("n") or 0) >= 3:
            bs.ctr_muc_tieu, bs.nhan_ctr_muc_tieu = so(b.get("muc_tieu")), "bài học kênh, n={0}".format(b["n"])
            break


def _an_toan(bs: BangSo, ten: str, f: Any) -> None:
    try:
        f()
    except Exception as loi:  # noqa: BLE001 — một nguồn hỏng không được làm hỏng cả bảng
        bs.ghi_chu.append("{0}: {1}".format(ten, str(loi)[:120]))


def tom_tat(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None) -> BangSo:
    """Bảng số của kênh `ma`. Chỉ đọc đĩa; không ném lỗi."""
    bs = BangSo(goc=goc, ma_kenh=ma, bay_gio=bay_gio or _dt.datetime.now())
    tm = thu_muc_kenh(goc, ma)

    def _cai() -> None:
        from ..kenh import TEP_KENH, doc_yaml  # noqa: PLC0415

        bs.cai = dict(doc_yaml(os.path.join(tm, TEP_KENH)) or {})

    def _bai_hoc() -> None:
        from ..chien_luoc import bai_hoc  # noqa: PLC0415

        bs.bai_hoc = bai_hoc.doc(goc, ma, tat_ca=True, bay_gio=bs.bay_gio)

    def _cong_thuc() -> None:
        from ..chien_luoc import ket_qua  # noqa: PLC0415

        bs.cong_thuc = ket_qua.thong_ke(goc, ma, bay_gio=bs.bay_gio)
        bs.chien_luoc_tep = _doc_json(ket_qua.duong_tep(goc, ma)) or {}

    def _bien_tap() -> None:
        tep = sorted(glob.glob(os.path.join(tm, "nghien-cuu", "bien-tap", "2*.json")))
        du = _doc_json(tep[-1]) if tep else None
        if isinstance(du, dict):
            bs.bien_tap_cuoi = {"luc": du.get("luc"), "nhan_dinh": str(du.get("nhan_dinh") or "")[:600]}

    _an_toan(bs, "kenh.yaml", _cai)
    _an_toan(bs, "bài học", _bai_hoc)
    _an_toan(bs, "mục tiêu", lambda: _muc_tieu(goc, ma, bs))
    _an_toan(bs, "video", lambda: _video(goc, ma, bs))
    _an_toan(bs, "kenh-theo-ngay", lambda: bs.kenh_ngay.extend(
        _doc_kenh_ngay(os.path.join(tm, "chi-so", "kenh-theo-ngay.csv"))))
    _an_toan(bs, "công thức", _cong_thuc)
    _an_toan(bs, "biên tập", _bien_tap)
    bs.trang_thai = _doc_json(os.path.join(thu_muc_giam_doc(goc, ma), "trang-thai.json")) or {}
    if not bs.video:
        bs.ghi_chu.append("chưa có video nào có số trong chi-so/ (sau ngay_bat_dau)")
    if not bs.kenh_ngay:
        bs.ghi_chu.append("chưa có kenh-theo-ngay.csv")
    return bs
