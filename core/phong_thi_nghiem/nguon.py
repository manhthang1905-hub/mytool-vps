"""Đọc đĩa cho phòng thí nghiệm — "thế giới" của MỘT kênh tại MỘT mốc (hiện tại, hoặc hết một ngày trong quá khứ).

Chỉ đọc, không mạng, không AI. Mỗi nguồn hỏng → rỗng + một dòng `ghi_chu`, không ném lỗi.

═══ TRẠNG THÁI "HẾT NGÀY X" (chạy ngược) ═══

`nghien-cuu/sao-luu/content-<Y>.csv` (và `doi-thu-<Y>.csv`) là bản chép sổ NGAY TRƯỚC lần ghi đầu tiên của ngày Y
(`doi_thu_kenh._sao_luu_hom_nay`) = trạng thái sổ sau lần ghi cuối cùng trước Y. Vậy "sổ lúc hết ngày X" = bản sao
lưu có ngày Y nhỏ nhất mà Y > X; không có → sổ hiện tại. Bảng V7 của ngày X = `cham-v7-X.csv` (ghi trong ngày X), thiếu
thì bảng gần nhất ≤ X trong 3 ngày. Trang chủ: dòng `Lúc quét` ≤ hết X. Bảng đề xuất Studio: bản chụp có
`captured_at` ≤ hết X. Nhãn thắng của video mình: chuỗi số cắt ở hết X. Không thông tin nào của tương lai lọt vào.
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import _chung as c

#: Bảng V7 cũ nhất còn dùng được cho một ngày (ngày trước đó, tối đa ngần này ngày).
LUI_BANG_V7 = 3
_RE_NGAY = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class TheGioi:
    """Mọi thứ phòng thí nghiệm cần để dựng vũ trụ ứng viên + kho đặc trưng của một kênh ở một mốc."""
    kenh: str
    ngay: str
    moc: float
    che_do: str = "that"                                     # "that" (hằng ngày) | "nguoc" (chạy ngược lịch sử)
    sach: List[Dict[str, str]] = field(default_factory=list)       # sổ content (content.csv) — video đối thủ
    danh_ba: List[Dict[str, str]] = field(default_factory=list)    # sổ đối thủ (doi-thu.csv)
    kenh_ai: Dict[str, str] = field(default_factory=dict)          # link kênh (thường) → giu | bo | nghi
    ai_nho: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # bộ nhớ thẩm định AI của V7
    trang_chu: List[Dict[str, str]] = field(default_factory=list)  # trang chủ máy ảo của kênh (≤ mốc)
    pool: List[Dict[str, Any]] = field(default_factory=list)       # dòng bảng đề xuất Studio của video mình
    video_minh: List[Dict[str, Any]] = field(default_factory=list)  # video mình: ma, tieu_de, nhan, nong, nguon_td
    ma_cua_nhom: Set[str] = field(default_factory=set)             # mã video CỦA TA (mọi kênh trong nhóm)
    da_lam: Dict[str, str] = field(default_factory=dict)           # mã nguồn → ngày làm ("" = lâu rồi/không rõ)
    anh_em: List[str] = field(default_factory=list)                # kênh cùng nhóm (kể cả chính nó)
    v7: Dict[str, Dict[str, Any]] = field(default_factory=dict)    # mã → {diem, hang}
    v7_nguon: str = ""
    vph: Dict[str, Dict[str, Any]] = field(default_factory=dict)   # mã → {diem, hang} (VPH thật, chỉ chạy hằng ngày)
    tuyen: List[str] = field(default_factory=list)
    cum_cua: Optional[Callable[[str], List[str]]] = None
    nhan_y: Optional[Callable[[str], str]] = None
    vung_ai: Dict[str, str] = field(default_factory=dict)
    ban_do_vung: Dict[str, Any] = field(default_factory=dict)
    thi_truong: Dict[str, Dict[str, float]] = field(default_factory=dict)
    lich_su_view: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)
    luc_quet_sach: Optional[float] = None
    ghi_chu: List[str] = field(default_factory=list)
    #: Radar đột biến thị trường của nhóm (`core/radar_dot_bien.dac_trung_cho_kenh`): mã → radar_boi/muc/cua_minh/tuoi.
    radar: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ── sổ content / sổ đối thủ theo ngày ───────────────────────────────────────

def ban_sao_luu(goc: str, kenh: str, tien_to: str) -> List[Tuple[str, str]]:
    """`[(ngày, đường)]` các bản `sao-luu/<tien_to>-<ngày>.csv`, cũ trước."""
    ra = []
    for p in glob.glob(os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "sao-luu", tien_to + "-*.csv")):
        m = _RE_NGAY.search(os.path.basename(p))
        if m:
            ra.append((m.group(1), p))
    return sorted(ra)


def tep_het_ngay(goc: str, kenh: str, tien_to: str, ngay: str) -> str:
    """Tệp mang trạng thái sổ lúc HẾT ngày `ngay` (xem đầu tệp): bản sao lưu ngày nhỏ nhất > `ngay`, không có → sổ
    hiện tại."""
    for d, p in ban_sao_luu(goc, kenh, tien_to):
        if d > ngay:
            return p
    return os.path.join(c.thu_muc_nghien_cuu(goc, kenh), tien_to + ".csv")


def ngay_co_so_lieu(goc: str, kenh: str) -> List[str]:
    """Các ngày X dựng được "sổ lúc hết X": (ngày bản sao lưu − 1) và ngày ghi cuối của sổ hiện tại."""
    ra = set()
    for d, _p in ban_sao_luu(goc, kenh, "content"):
        ra.add(c.cong_ngay(d, -1))
    p = os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "content.csv")
    try:
        ra.add(_dt.date.fromtimestamp(os.path.getmtime(p)).isoformat())
    except OSError:
        pass
    return sorted(x for x in ra if x)


def luc_quet_kenh(danh_ba: Sequence[Dict[str, str]]) -> Dict[str, float]:
    """`{tên kênh: epoch lần quét content gần nhất}` từ cột `Quét lúc` của sổ đối thủ."""
    ra: Dict[str, float] = {}
    for r in danh_ba:
        t = c.epoch_luc(r.get("Quét lúc"))
        ten = str(r.get("Kênh") or "").strip()
        if ten and t is not None and t > ra.get(ten, 0.0):
            ra[ten] = t
    return ra


# ── phán quyết ngách AI (kho chung nhóm `kenh-ai.json`) ─────────────────────

def doc_kenh_ai(goc: str, kenh: str) -> Dict[str, str]:
    """`{link kênh viết thường: giu | bo | nghi}`."""
    try:
        from .. import nghien_cuu_chung as ncc  # noqa: PLC0415

        p = ncc.duong_kenh_ai(goc, kenh)
    except Exception:  # noqa: BLE001
        return {}
    du = c.doc_json(p, {}) or {}
    ra: Dict[str, str] = {}
    if not isinstance(du, dict):
        return ra
    doi = {"doi_thu": "giu", "gan": "nghi", "khong": "bo"}
    for k, v in du.items():
        if not isinstance(v, dict):
            continue
        x = str(v.get("kiem_ngach") or "").strip().lower() or doi.get(str(v.get("ket") or "").strip().lower(), "")
        if x in ("giu", "bo", "nghi"):
            ra[str(k).strip().lower()] = x
    return ra


# ── trang chủ máy ảo ────────────────────────────────────────────────────────

def doc_trang_chu(goc: str, kenh: str) -> List[Dict[str, str]]:
    """Dòng `trang-chu.csv` CỦA KÊNH (máy ảo của tệp khán giả kênh), bỏ trùng (lúc quét, mã)."""
    thay: Set[Tuple[str, str]] = set()
    ra = []
    for r in c.doc_csv(os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "trang-chu.csv")):
        k = (str(r.get("Lúc quét") or "")[:16], str(r.get("Mã video") or ""))
        if not k[1] or k in thay:
            continue
        thay.add(k)
        ra.append(r)
    return ra


def loc_trang_chu(rows: Sequence[Dict[str, str]], ngay: str) -> List[Dict[str, str]]:
    het = ngay + " 99"
    return [r for r in rows if str(r.get("Lúc quét") or "")[:16] <= het]


# ── video của ta + nhãn thước chung tại một mốc ─────────────────────────────

def video_minh_cua_kenh(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{mã: {ma, tieu_de, dang, chuoi}}` — cùng tập `thuoc_thang.chuoi_kenh` (lọc `ngay_bat_dau`)."""
    from .. import thuoc_thang as tt  # noqa: PLC0415

    try:
        chuoi = tt.chuoi_kenh(goc, kenh)
    except Exception:  # noqa: BLE001
        return {}
    ra: Dict[str, Dict[str, Any]] = {}
    goc_cs = os.path.join(goc, "CHANNEL", kenh, "chi-so")
    for ma, ch in chuoi.items():
        td = ""
        for p in sorted(glob.glob(os.path.join(goc_cs, ma, "*", "_thong-tin.json"))):
            du = c.doc_json(p, {}) or {}
            td = str(du.get("tieu_de") or "") if isinstance(du, dict) else ""
            if td:
                break
        ra[ma] = {"ma": ma, "tieu_de": td, "dang": ch.dang, "chuoi": ch}
    return ra


def _cat_chuoi(ch: Any, moc: float) -> Any:
    from .. import thuoc_thang as tt  # noqa: PLC0415

    giu = []
    for d in ch.diem:
        luc = d.luc if d.luc is not None else ((ch.dang + d.tuoi * 3600.0) if ch.dang is not None else None)
        if luc is None or luc <= moc:
            giu.append(d)
    return tt.Chuoi(ma=ch.ma, dang=ch.dang, diem=giu, bo=ch.bo)


def nhan_tai_moc(vm: Dict[str, Dict[str, Any]], moc: Optional[float]) -> Dict[str, Any]:
    """`{mã: thuoc_thang.KetQua}` theo số đã chụp TỚI `moc` (None = hiện tại). Video đăng sau mốc bị bỏ."""
    from .. import thuoc_thang as tt  # noqa: PLC0415

    if not vm:
        return {}
    if moc is None:
        return tt.danh_gia({m: v["chuoi"] for m, v in vm.items()}, bay_gio=_dt.datetime.utcnow())
    chuoi = {}
    for m, v in vm.items():
        ch = v["chuoi"]
        if ch.dang is not None and ch.dang > moc:
            continue
        chuoi[m] = _cat_chuoi(ch, moc)
    return tt.danh_gia(chuoi, bay_gio=_dt.datetime.utcfromtimestamp(moc)) if chuoi else {}


# ── sổ lượt sản xuất ────────────────────────────────────────────────────────

def luot_san_xuat(goc: str, kenh: str) -> List[Dict[str, Any]]:
    """`[{ma_goi, ma (nguồn), ngay, bo, video_id, cong_thuc, tieu_de, gia_thuyet, ptn_pb}]` — sổ `tu-chay/*.json` nối
    hồ sơ video (`gia_thuyet` = khe phòng thí nghiệm chia cho giả thuyết nào, đợt 2)."""
    try:
        from .. import ho_so_video  # noqa: PLC0415
        from ..chien_luoc import ket_qua  # noqa: PLC0415

        so_luot = ho_so_video.nguon_cua_goi(goc, kenh)
        hs = ket_qua.ho_so_theo_goi(goc, kenh)
    except Exception:  # noqa: BLE001
        return []
    ra = []
    for ma_goi, g in so_luot.items():
        h = hs.get(ma_goi) or {}
        ra.append({"ma_goi": ma_goi, "ma": str(g.get("ma") or ""), "ngay": str(g.get("ngay") or ""),
                   "bo": bool(g.get("bo")), "video_id": str(h.get("video_id") or ""),
                   "cong_thuc": str(g.get("cong_thuc") or ""), "tieu_de": str(g.get("tieu_de") or ""),
                   "gia_thuyet": str(g.get("gia_thuyet") or ""), "ptn_pb": g.get("ptn_pb"), "ho_so": h})
    return ra


def da_lam_nhom(goc: str, kenh: str, anh_em: Sequence[str]) -> Dict[str, str]:
    """`{mã nguồn: ngày làm sớm nhất}` của CẢ NHÓM ("" = không rõ ngày → coi như làm từ lâu)."""
    co_ngay: Dict[str, str] = {}
    khong_ngay: Set[str] = set()
    for k in anh_em or [kenh]:
        for r in luot_san_xuat(goc, k):
            if not r["ma"]:
                continue
            if r["ngay"]:
                co_ngay[r["ma"]] = min(co_ngay.get(r["ma"], r["ngay"]), r["ngay"])
            else:
                khong_ngay.add(r["ma"])
        try:
            from ..da_lam import doc_ma_da_lam  # noqa: PLC0415

            khong_ngay.update(doc_ma_da_lam(goc, k))
        except Exception:  # noqa: BLE001
            pass
    ra = {m: "" for m in khong_ngay}
    ra.update(co_ngay)
    return ra


def ma_video_nhom(goc: str, anh_em: Sequence[str]) -> Set[str]:
    """Mã video CỦA TA (thư mục `chi-so/` + hồ sơ) của mọi kênh trong nhóm."""
    ra: Set[str] = set()
    for k in anh_em:
        try:
            for ten in os.listdir(os.path.join(goc, "CHANNEL", k, "chi-so")):
                if len(ten) == 11:
                    ra.add(ten)
        except OSError:
            pass
        for p in glob.glob(os.path.join(goc, "CHANNEL", k, "ho-so-video", "*.json")):
            du = c.doc_json(p, {}) or {}
            if isinstance(du, dict) and du.get("video_id"):
                ra.add(str(du["video_id"]))
    return ra


# ── bảng đề xuất Studio (pool) có giờ chụp ──────────────────────────────────

def bang_de_xuat_kenh(goc: str, kenh: str) -> List[Tuple[str, float, Dict[str, Any]]]:
    """`[(mã video mình, giờ chụp epoch, bảng)]` — MỌI bản chụp bảng "video đề xuất" (YT_RELATED) của mọi video mình
    (`cong_thuc_v7._bang_raw/_bang_csv`). Giờ chụp = `captured_at` của gói; không có → mtime thư mục (dữ liệu cũ)."""
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415
    from ..chi_so_ytb import gom  # noqa: PLC0415

    ra = []
    goc_cs = os.path.join(goc, "CHANNEL", kenh, "chi-so")
    try:
        ten_vid = sorted(os.listdir(goc_cs))
    except OSError:
        return ra
    for vid in ten_vid:
        pv = os.path.join(goc_cs, vid)
        if len(vid) != 11 or not os.path.isdir(pv):
            continue
        for moc in sorted(os.listdir(pv)):
            pm = os.path.join(pv, moc)
            if moc.startswith("kenh") or not os.path.isdir(pm):
                continue
            bang = []
            try:
                for f in v7._raw_join(pm):  # noqa: SLF001 — dùng đúng bộ đọc của V7
                    try:
                        b = v7._bang_raw(f)  # noqa: SLF001
                    except Exception:  # noqa: BLE001
                        b = None
                    if b:
                        bang.append(b)
                f_csv = os.path.join(pm, "traffic-related.csv")
                if os.path.isfile(f_csv):
                    try:
                        b = v7._bang_csv(f_csv)  # noqa: SLF001
                    except Exception:  # noqa: BLE001
                        b = None
                    if b:
                        bang.append(b)
            except Exception:  # noqa: BLE001
                continue
            bang = [b for b in bang if b.get("bam") and b.get("avd")]
            if not bang:
                continue
            try:
                cap = gom._captured_at_that(pm)  # noqa: SLF001
            except Exception:  # noqa: BLE001
                cap = None
            if cap is None:
                try:
                    cap = os.path.getmtime(pm)
                except OSError:
                    continue
            ra.append((vid, float(cap), max(bang, key=lambda b: (b["hien_thi"], b["xem"], len(b["dong"])))))
    return ra


def pool_tai_moc(bang: Sequence[Tuple[str, float, Dict[str, Any]]], moc: float, thang: Set[str],
                 ma_cua_nhom: Set[str]) -> List[Dict[str, Any]]:
    """Dòng pool tại mốc: mỗi video mình lấy bản chụp MUỘN NHẤT có giờ chụp ≤ `moc`; bỏ dòng là video của ta."""
    moi: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    for vid, cap, b in bang:
        if cap > moc:
            continue
        cu = moi.get(vid)
        if cu is None or cap > cu[0]:
            moi[vid] = (cap, b)
    ra = []
    for vid, (_cap, b) in moi.items():
        for r in b.get("dong") or []:
            ma = str(r.get("ma") or "")
            if not ma or ma in ma_cua_nhom:
                continue
            ra.append({"ma": ma, "tieu_de": str(r.get("tieu_de") or ""), "hien_thi": float(r.get("hien_thi") or 0),
                       "bam": r.get("bam"), "xem": float(r.get("xem") or 0), "avd": r.get("avd"),
                       "bam_tb": b.get("bam"), "avd_tb": b.get("avd"), "video_minh": vid, "thang": vid in thang})
    return ra


# ── bảng V7 theo ngày ───────────────────────────────────────────────────────

def _diem_v5_tu_dong_cu(r: Dict[str, str]) -> float:
    """Điểm V7 phiên bản 5 dựng lại từ cột báo cáo CŨ (trọng số 30/25/20/15/10, khuôn 0,5/0,2) — CÙNG công thức
    `core/backtest_chon_v7.diem_moi_tu_dong` (tệp ấy chỉ chạy như lệnh, không nhập từ mã khác): Nổ × 1,5 (kênh yếu
    giữ 5), Đang lên 0, độ dài 12–21 → 9 (8–30 → 2,25), dạng chân dung 5 → 6 (khác 2 → 2,25), giữ khoản trừ AI."""
    cum, pool, no, len_, khuon, xh = (c.so(r.get(k)) or 0.0 for k in ("Cụm", "Bảng đề xuất", "Nổ", "Đang lên",
                                                                       "Khuôn", "Xu hướng"))
    diem = c.so(r.get("Điểm")) or 0.0
    tru = min(0.0, diem - max(0.0, min(100.0, cum + pool + no + len_ + khuon + xh)))
    yeu = "(kênh yếu)" in str(r.get("Lý do") or "")
    no_moi = no * 1.5 + (2.5 if yeu and no > 0 else 0.0)
    ph = c.phut(r.get("Dài"))
    dai_cu = 5.0 if ph is not None and 12 <= ph <= 21 else 2.0 if ph is not None and 8 <= ph <= 30 else 0.0
    dang_cu = max(0.0, khuon - dai_cu)
    dang_moi = 6.0 if dang_cu >= 4.5 else 2.25 if dang_cu >= 1.5 else 0.0
    dai_moi = 9.0 if dai_cu == 5.0 else 2.25 if dai_cu == 2.0 else 0.0
    return max(0.0, min(100.0, cum + pool + no_moi + dai_moi + dang_moi + xh)) + tru


def la_bang_v5(rows: Sequence[Dict[str, str]]) -> bool:
    """Bảng V7 đã chấm theo trọng số phiên bản 5 (Nổ trần 30, Khuôn trần 15, Đang lên 0) hay bảng cũ."""
    if not rows:
        return True
    no = max((c.so(r.get("Nổ")) or 0.0) for r in rows)
    kh = max((c.so(r.get("Khuôn")) or 0.0) for r in rows)
    ln = max((c.so(r.get("Đang lên")) or 0.0) for r in rows)
    return no > 20.5 or kh > 10.5 or ln <= 0.0


def bang_v7_ngay(goc: str, kenh: str, ngay: str, lui: int = LUI_BANG_V7) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """`({mã: {diem, hang, diem_goc}}, ngày của bảng)` — bảng `cham-v7-<ngày>.csv` ≤ `ngay` (lùi tối đa `lui` ngày),
    điểm theo phiên bản 5 (bảng cũ thì dựng lại), xếp lại theo điểm v5."""
    from ..doi_thu_kenh import ma_video  # noqa: PLC0415

    for i in range(0, lui + 1):
        d = c.cong_ngay(ngay, -i)
        rows = c.doc_csv(os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "cham-v7-{0}.csv".format(d)))
        if not rows:
            continue
        v5 = la_bang_v5(rows)
        ds = []
        for r in rows:
            ma = ma_video(str(r.get("Link") or ""))
            if not ma:
                continue
            goc_d = c.so(r.get("Điểm")) or 0.0
            ds.append((ma, goc_d if v5 else _diem_v5_tu_dong_cu(r), goc_d, c.so(r.get("Hạng")) or 9999))
        ds.sort(key=lambda x: (-x[1], x[3]))
        return ({ma: {"diem": round(dv5, 2), "hang": i + 1, "diem_goc": dg}
                 for i, (ma, dv5, dg, _h) in enumerate(ds)}, d)
    return {}, ""


def v7_tu_ket_qua(kq: Any) -> Dict[str, Dict[str, Any]]:
    """Bảng V7 của lượt chấm vừa chạy (`cong_thuc_v7.KetQua`) → `{mã: {diem, hang}}`."""
    ra = {}
    for i, d in enumerate(getattr(kq, "ung_vien", None) or []):
        ma = str(getattr(d, "ma", "") or "")
        if ma and not getattr(d, "bi_loai", ""):
            ra.setdefault(ma, {"diem": float(getattr(d, "diem", 0) or 0), "hang": i + 1})
    return ra


def vph_hien_tai(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """VPH thật của sổ hiện tại (`cong_thuc_vph.cham`) → `{mã: {diem, hang}}`; hỏng → {}."""
    try:
        from .. import cong_thuc_vph  # noqa: PLC0415

        kq = cong_thuc_vph.cham(goc, kenh)
    except Exception:  # noqa: BLE001
        return {}
    return {d.ma: {"diem": float(d.diem), "hang": i + 1} for i, d in enumerate(kq.ung_vien) if d.ma}


# ── vùng đề tài + thị trường ────────────────────────────────────────────────

def doc_vung(goc: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """`(vùng AI theo link/mã, bản đồ chủ quyền)`."""
    try:
        from .. import chu_quyen_vung as cqv  # noqa: PLC0415

        return cqv._vung_ai(goc), cqv.doc(goc)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return {}, {}


def lich_su_thi_truong(goc: str) -> List[Dict[str, Any]]:
    """Ảnh chụp thị trường theo ngày (`workspace/chien-truong/lich-su.jsonl`), cũ trước."""
    ra = []
    for x in c.doc_jsonl(os.path.join(goc, "workspace", "chien-truong", "lich-su.jsonl")):
        if x.get("ngay") and isinstance(x.get("vung"), (dict, list)):
            v = x["vung"]
            if isinstance(v, list):
                v = {str(y.get("ma")): y for y in v if isinstance(y, dict) and y.get("ma")}
            ra.append({"ngay": str(x["ngay"])[:10], "vung": v})
    return sorted(ra, key=lambda x: x["ngay"])


def thi_truong_ngay(lich_su: Sequence[Dict[str, Any]], ngay: str, cach: int = 7) -> Dict[str, Dict[str, float]]:
    """`{vùng: {dich, ta, thi_phan, tang}}` theo ảnh chụp muộn nhất ≤ `ngay` (không có → ảnh sớm nhất); `tang` =
    log2(view đối thủ nay / ~`cach` ngày trước) — 0 khi chưa có ảnh trước."""
    import math  # noqa: PLC0415

    if not lich_su:
        return {}
    truoc = [x for x in lich_su if x["ngay"] <= ngay]
    nay = truoc[-1] if truoc else lich_su[0]
    moc_cu = c.cong_ngay(nay["ngay"], -cach)
    cu_ds = [x for x in lich_su if x["ngay"] <= moc_cu] or [x for x in lich_su if x["ngay"] < nay["ngay"]]
    cu = (cu_ds[-1] if cu_ds else None)
    ra: Dict[str, Dict[str, float]] = {}
    for v, o in (nay["vung"] or {}).items():
        if not isinstance(o, dict):
            continue
        dich = float(o.get("dich") or 0)
        o_cu = ((cu or {}).get("vung") or {}).get(v) if cu else None
        dich_cu = float((o_cu or {}).get("dich") or 0) if isinstance(o_cu, dict) else None
        ra[str(v)] = {"dich": dich, "ta": float(o.get("ta") or 0), "thi_phan": float(o.get("thi_phan") or 0),
                      "tang": round(math.log((dich + 1.0) / (dich_cu + 1.0), 2), 3) if dich_cu is not None else 0.0}
    return ra


# ── bộ nhận cụm của kênh (chỉ đọc) ──────────────────────────────────────────

def bo_cum(goc: str, kenh: str) -> Tuple[Optional[Callable[[str], List[str]]], Optional[Callable[[str], str]],
                                         Dict[str, Dict[str, Any]]]:
    """`(cụm theo V7 — AI đã phân hoặc từ khoá, nhãn theo nghĩa `cum_y_nghia`, bộ nhớ thẩm định AI V7)`."""
    try:
        from .. import cong_thuc_v7 as v7  # noqa: PLC0415

        ch, _ = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
        v7.nap_phan_cum(goc, kenh, ch)
    except Exception:  # noqa: BLE001
        return None, None, {}
    nho: Dict[str, Dict[str, Any]] = {}
    try:
        nho = v7.doc_bo_nho(goc, kenh, ch)
    except Exception:  # noqa: BLE001
        nho = {}
    nhan_y = None
    try:
        from .. import cum_y_nghia  # noqa: PLC0415

        bo = cum_y_nghia.BoNho(goc, kenh, ch=ch)

        def nhan_y(td: str) -> str:
            try:
                return bo.tra(td)
            except Exception:  # noqa: BLE001
                return ""
    except Exception:  # noqa: BLE001
        nhan_y = None

    def cum_cua(td: str) -> List[str]:
        try:
            return list(v7.cum_cua_tieu_de(td, ch) or [])
        except Exception:  # noqa: BLE001
            return []
    return cum_cua, nhan_y, nho


def anh_em_cua(goc: str, kenh: str) -> List[str]:
    try:
        from .. import nhom_kenh  # noqa: PLC0415

        return list(nhom_kenh.thanh_vien(goc, kenh) or [kenh])
    except Exception:  # noqa: BLE001
        return [kenh]


def tuyen_dang_danh(goc: str, kenh: str) -> List[str]:
    try:
        from .. import mot_nut  # noqa: PLC0415

        return list(mot_nut.tuyen_dang_danh(goc, kenh) or [])
    except Exception:  # noqa: BLE001
        return []


# ── bộ đệm cho chạy ngược (đọc một lần mỗi kênh) ────────────────────────────

class NguonKenh:
    """Các nguồn đọc MỘT lần cho một kênh rồi cắt theo mốc từng ngày (chạy ngược nhiều ngày)."""

    def __init__(self, goc: str, kenh: str) -> None:
        self.goc, self.kenh = goc, kenh
        self.anh_em = anh_em_cua(goc, kenh)
        self._trang_chu: Optional[List[Dict[str, str]]] = None
        self._bang: Optional[List[Tuple[str, float, Dict[str, Any]]]] = None
        self._vm: Optional[Dict[str, Dict[str, Any]]] = None
        self._luot: Optional[List[Dict[str, Any]]] = None
        self._da_lam: Optional[Dict[str, str]] = None
        self._ma_nhom: Optional[Set[str]] = None
        self._cum: Optional[Tuple[Any, Any, Dict[str, Dict[str, Any]]]] = None
        self._kenh_ai: Optional[Dict[str, str]] = None
        self._tuyen: Optional[List[str]] = None

    def trang_chu(self) -> List[Dict[str, str]]:
        if self._trang_chu is None:
            self._trang_chu = doc_trang_chu(self.goc, self.kenh)
        return self._trang_chu

    def bang_de_xuat(self) -> List[Tuple[str, float, Dict[str, Any]]]:
        if self._bang is None:
            try:
                self._bang = bang_de_xuat_kenh(self.goc, self.kenh)
            except Exception:  # noqa: BLE001
                self._bang = []
        return self._bang

    def video_minh(self) -> Dict[str, Dict[str, Any]]:
        if self._vm is None:
            self._vm = video_minh_cua_kenh(self.goc, self.kenh)
        return self._vm

    def luot(self) -> List[Dict[str, Any]]:
        if self._luot is None:
            self._luot = luot_san_xuat(self.goc, self.kenh)
        return self._luot

    def da_lam(self) -> Dict[str, str]:
        if self._da_lam is None:
            self._da_lam = da_lam_nhom(self.goc, self.kenh, self.anh_em)
        return self._da_lam

    def ma_nhom(self) -> Set[str]:
        if self._ma_nhom is None:
            self._ma_nhom = ma_video_nhom(self.goc, self.anh_em)
        return self._ma_nhom

    def cum(self) -> Tuple[Any, Any, Dict[str, Dict[str, Any]]]:
        if self._cum is None:
            self._cum = bo_cum(self.goc, self.kenh)
        return self._cum

    def kenh_ai(self) -> Dict[str, str]:
        if self._kenh_ai is None:
            self._kenh_ai = doc_kenh_ai(self.goc, self.kenh)
        return self._kenh_ai

    def tuyen(self) -> List[str]:
        if self._tuyen is None:
            self._tuyen = tuyen_dang_danh(self.goc, self.kenh)
        return self._tuyen

    def nguon_tieu_de(self) -> Dict[str, str]:
        """`{mã video mình: tiêu đề NGUỒN của nó}` (sổ lượt + hồ sơ)."""
        return {r["video_id"]: r["tieu_de"] for r in self.luot() if r.get("video_id") and r.get("tieu_de")}


def dung_the_gioi(nk: NguonKenh, ngay: str, *, che_do: str = "nguoc", moc: Optional[float] = None,
                  sach: Optional[List[Dict[str, str]]] = None, danh_ba: Optional[List[Dict[str, str]]] = None,
                  v7: Optional[Dict[str, Dict[str, Any]]] = None, v7_nguon: str = "",
                  vph: Optional[Dict[str, Dict[str, Any]]] = None,
                  vung: Optional[Tuple[Dict[str, str], Dict[str, Any]]] = None,
                  lich_su: Optional[List[Dict[str, Any]]] = None,
                  lich_su_view: Optional[Dict[str, List[Tuple[float, float]]]] = None) -> TheGioi:
    """Dựng `TheGioi` của kênh lúc HẾT ngày `ngay` (chạy ngược) hoặc lúc `moc` (hằng ngày: sổ hiện tại)."""
    goc, kenh = nk.goc, nk.kenh
    moc = moc if moc is not None else c.moc_cuoi_ngay(ngay)
    tg = TheGioi(kenh=kenh, ngay=ngay, moc=moc, che_do=che_do, anh_em=list(nk.anh_em))
    tg.sach = sach if sach is not None else c.doc_csv(tep_het_ngay(goc, kenh, "content", ngay))
    tg.danh_ba = danh_ba if danh_ba is not None else c.doc_csv(tep_het_ngay(goc, kenh, "doi-thu", ngay))
    if not tg.sach:
        tg.ghi_chu.append("sổ content trống")
    tg.kenh_ai = nk.kenh_ai()
    tg.cum_cua, tg.nhan_y, tg.ai_nho = nk.cum()
    tg.trang_chu = loc_trang_chu(nk.trang_chu(), ngay) if che_do == "nguoc" else list(nk.trang_chu())
    tg.ma_cua_nhom = set(nk.ma_nhom())
    tg.da_lam = dict(nk.da_lam())
    # Video của mình + nhãn thắng tại mốc (chạy ngược: chuỗi cắt ở mốc).
    vm = nk.video_minh()
    tg.ma_cua_nhom |= set(vm)
    try:
        ket = nhan_tai_moc(vm, moc if che_do == "nguoc" else None)
    except Exception as loi:  # noqa: BLE001
        ket = {}
        tg.ghi_chu.append("nhãn thắng hỏng: {0}".format(str(loi)[:80]))
    ntd = nk.nguon_tieu_de()
    for ma, k in ket.items():
        tg.video_minh.append({"ma": ma, "tieu_de": vm.get(ma, {}).get("tieu_de", ""),
                              "nhan": getattr(k, "nhan", ""), "nong": bool(getattr(k, "nong", False)),
                              "nguon_td": ntd.get(ma, "")})
    thang = {v["ma"] for v in tg.video_minh if v["nhan"] == "thang" or v["nong"]}
    tg.pool = pool_tai_moc(nk.bang_de_xuat(), moc, thang, tg.ma_cua_nhom)
    if v7 is None:
        tg.v7, tg.v7_nguon = bang_v7_ngay(goc, kenh, ngay)
        tg.v7_nguon = ("bang:" + tg.v7_nguon) if tg.v7_nguon else ""
    else:
        tg.v7, tg.v7_nguon = v7, v7_nguon
    tg.vph = vph or {}
    tg.tuyen = nk.tuyen()
    tg.vung_ai, tg.ban_do_vung = vung if vung is not None else doc_vung(goc)
    tg.thi_truong = thi_truong_ngay(lich_su if lich_su is not None else lich_su_thi_truong(goc), ngay)
    tg.lich_su_view = lich_su_view or {}
    try:   # radar thị trường: bảng mới nhất (hằng ngày) / bảng của đúng ngày (chạy ngược — không có thì rỗng)
        from .. import radar_dot_bien  # noqa: PLC0415

        tg.radar = radar_dot_bien.dac_trung_cho_kenh(goc, kenh, None if che_do == "that" else ngay)
    except Exception:  # noqa: BLE001
        tg.radar = {}
    try:
        p = os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "cai-dat.json")
        tg.luc_quet_sach = float((c.doc_json(p, {}) or {}).get("quet_luc") or 0) or None
    except (TypeError, ValueError):
        tg.luc_quet_sach = None
    return tg
