"""GỢI Ý BẮT BUỘC CHO BỘ NÃO — mã TÍNH SẴN những việc bộ não hay bỏ sót (06/10/2026).

Phiên 05/10: bộ não (1) thấy bài học "tránh nhãn 雑学" bị video 【雑学】 10.202 hiển thị bác bỏ mà KHÔNG chạy
`bai-hoc tru`; (2) thấy video THẮNG LỚN của TL2 (年金, CTR 9,47%, 8.497 hiển thị lúc 35h, ngưỡng thắng 6.000) mà không
`uu-tien-nguon` để nhân bản khi còn nóng. Cả hai đều là việc ĐỦ RÕ để máy tính, không cần "tư duy": nên `xem`
in sẵn thành mục "VIỆC BẮT BUỘC XEM HÔM NAY" kèm lệnh chạy được.

Tệp này CHỈ ĐỌC (không ghi gì vào `CHANNEL/`, `nao/`), không gọi mạng/AI.

    python -m core.nao_goi_y          # in mục này; gốc dữ liệu đổi được bằng biến môi trường MYTOOL_GOC

═══ QUY TẮC (bảo thủ — thà thiếu còn hơn gợi ý bừa) ═══

* "Video thắng lớn": video của kênh đăng ≤ `NGAY_GAN_DAY` ngày, hiển thị ở MỐC MỚI NHẤT (`chi-so/bang-tom-tat.csv`)
  ≥ `HE_SO_THANG_LON` × ngưỡng thắng 48h của kênh (`cong_thuc_v7.nguong_thang_48h` — cùng công thức mọi nơi).
  Số hiển thị cộng dồn chỉ tăng, nên vượt ngưỡng ở mốc sớm thì chắc chắn vượt ở 48h.
* Nguồn nhân bản: video đối thủ trong `nghien-cuu/content.csv` CÙNG CỤM (`cum_cua_tieu_de`) với video thắng, chưa ai
  trong nhóm kênh làm, không phải video của chính mình (`nhom_kenh.video_da_lam_ca_nhom` + cột "Đã làm"), chưa được đề cử. Xếp: trùng ≥ 2 cặp chữ
  Hán/Katakana với tiêu đề thắng trước (cùng chủ đề hẹp, vd 年金), rồi tăng/ngày, rồi view.
* Bài học bị bác bỏ / xác nhận: chỉ xét các đặc điểm MÃ NHẬN ĐƯỢC chắc chắn từ tiêu đề / cụm của video thắng:
  trục `cum` (cụm của video thắng chứa mã cụm của bài), trục `tieu_de` với nhãn ngoặc 【…】 nêu trong câu bài học
  hoặc kiểu `so_dem`/`cau_hoi`/`hai_ve`. Hướng "-" (bài bảo tránh X) mà video thắng có X → gợi ý `tru`; hướng "+" mà
  video thắng có X → gợi ý `cong`. Trục khác (hook, bìa, giữ chân…) máy không nhận ra từ tiêu đề → KHÔNG gợi ý.
* Không gợi ý lại việc đã làm: đã có hành động của não nhắc video_id của video thắng (đề cử), hay bài học đã có
  `bai-hoc` cùng id nhắc video_id đó.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

GOC_MAC_DINH = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NGAY_GAN_DAY = 10            # chỉ xét video đăng trong ngần này ngày
HE_SO_THANG_LON = 1.0        # hiển thị mốc mới nhất ≥ hệ số × ngưỡng thắng 48h của kênh
HE_SO_RAT_LON = 1.4          # nhãn "RẤT LỚN" khi ≥ hệ số này
NGAY_NGUON_TOI_DA = 120      # video đối thủ đăng quá ngần này ngày thì không nhân bản
VIEW_NGUON_TOI_THIEU = 5000
SO_NGUON_TOI_DA = 3
SO_CAP_TRUNG_TOI_THIEU = 2   # số cặp chữ chung để coi là "cùng chủ đề hẹp"
NGAY_KIEM_TOI_DA = 30        # khớp `nao.TOI_DA_NGAY_KIEM`

_RE_NHAN = re.compile(r"【([^】]{1,12})】")
_RE_TU_LOI = re.compile(r"[一-鿿々゠-ヿ]{2,}")


def _so(x: Any) -> Optional[float]:
    s = str(x if x is not None else "").strip().replace("%", "").replace(" ", "")
    if not s:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    s = s.replace(",", ".") if re.fullmatch(r"\d+,\d+", s) else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _ngay(chu: Any) -> Optional[_dt.date]:
    try:
        return _dt.datetime.strptime(str(chu or "").strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        csv.field_size_limit(10_000_000)
        with io.open(duong, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (OSError, csv.Error):
        return []


def _nho(chu: Any, n: int = 60) -> str:
    s = " ".join(str(chu or "").split()).replace('"', "'")
    return s if len(s) <= n else s[:n - 1] + "…"


def _f(x: Any) -> str:
    v = _so(x)
    return "?" if v is None else "{0:,.0f}".format(v).replace(",", ".")


# ── ngưỡng + cụm của kênh (tách riêng để test thay được) ─────────────────────

def _nguong_kenh(goc: str, kenh: str, bay_gio: _dt.datetime) -> Tuple[float, Callable[[str], List[str]], Dict[str, List[str]]]:
    """`(ngưỡng thắng 48h, hàm tiêu đề→cụm, {mã video: cụm})` của kênh — cùng công thức V7 mọi nơi.
    Không ghi gì ra đĩa (`ghi_neu_thieu=False`). Ném lỗi nếu không tính được (nơi gọi bắt)."""
    from . import cong_thuc_v7 as v7  # noqa: PLC0415

    ch, _ = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    ds = v7.video_cua_kenh(goc, kenh, ch, bay_gio)
    nguong = float(v7.nguong_thang_48h(ds, ch))
    cum_video = {v.ma: list(v.cum or []) for v in ds}
    return nguong, (lambda td: list(v7.cum_cua_tieu_de(td, ch) or [])), cum_video


def _kiem_ngay(goc: str, kenh: str, bay_gio: _dt.datetime) -> str:
    """Ngày kiểm hợp lệ theo `nao.tao_hanh_dong`: SAU hôm nay, ≥ khe đăng trống kế + 2 ngày, ≤ hôm nay + 30."""
    hom = bay_gio.date()
    som = hom + _dt.timedelta(days=7)
    try:
        from . import kenh as _k, xep_lich  # noqa: PLC0415

        ngay_k, _g = xep_lich.khe_trong_som_nhat(goc, kenh, _k.doc_kenh(goc, kenh), bay_gio=bay_gio)
        if ngay_k:
            som = _dt.datetime.strptime(ngay_k, "%d/%m/%Y").date() + _dt.timedelta(days=2)
    except Exception:  # noqa: BLE001
        pass
    som = max(som, hom + _dt.timedelta(days=1))
    return min(som, hom + _dt.timedelta(days=NGAY_KIEM_TOI_DA)).isoformat()


# ── hành động đã có (để không gợi ý lại) ─────────────────────────────────────

def _hanh_dong_nhac(goc: str, lenh: str, video_id: str, kenh: str, noi_dung_id: str = "") -> str:
    """Id hành động `lenh` của kênh đã nhắc `video_id` trong lý do (mọi trạng thái trừ huỷ), hoặc ""."""
    try:
        from . import nao  # noqa: PLC0415

        for d in nao.doc_hanh_dong(goc):
            ts = d.get("tham_so") or {}
            if d.get("lenh") != lenh or d.get("trang_thai") == "huy" or ts.get("kenh") != kenh:
                continue
            if noi_dung_id and ts.get("noi_dung") != noi_dung_id:
                continue
            if video_id and video_id in str(d.get("ly_do") or ""):
                return str(d.get("id") or "")
    except Exception:  # noqa: BLE001
        pass
    return ""


# ═══ (a) VIDEO THẮNG LỚN + NGUỒN NHÂN BẢN ════════════════════════════════════

def _cap_chu(tieu_de: str) -> set:
    """Các cặp ký tự liền nhau trong chuỗi chữ Hán/Katakana của tiêu đề (bỏ nhãn 【…】) — dấu vết chủ đề hẹp."""
    td = _RE_NHAN.sub(" ", tieu_de or "")
    ra = set()
    for tu in _RE_TU_LOI.findall(td):
        ra.update(tu[i:i + 2] for i in range(len(tu) - 1))
    return ra


def _ma_video(link: str) -> str:
    try:
        from .doi_thu_kenh import ma_video  # noqa: PLC0415

        return ma_video(link) or ""
    except Exception:  # noqa: BLE001
        m = re.search(r"(?:[?&]v=|youtu\.be/|/shorts/)([\w-]{11})", link or "")
        return m.group(1) if m else ""


def _da_lam_ca_nhom(goc: str, kenh: str) -> set:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        return set(nhom_kenh.video_da_lam_ca_nhom(goc, kenh))
    except Exception:  # noqa: BLE001
        try:
            from . import da_lam  # noqa: PLC0415

            return set(da_lam.doc_ma_da_lam(goc, kenh))
        except Exception:  # noqa: BLE001
            return set()


def _video_cua_minh(goc: str, kenh: str) -> set:
    """Mã video ĐÃ ĐĂNG của kênh và các kênh anh em (bảng tóm tắt Studio) — `content.csv` có thể chứa chính video của mình
    (đối thủ chép lại / quét nhầm), không bao giờ là nguồn để nhân bản."""
    ra = set()
    try:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        ds = list(liet_ke_kenh(goc))
    except Exception:  # noqa: BLE001
        ds = []
    for k in set(ds) | {kenh}:
        for r in _doc_csv(os.path.join(goc, "CHANNEL", k, "chi-so", "bang-tom-tat.csv")):
            if r.get("Mã video"):
                ra.add(str(r["Mã video"]).strip())
    return ra


def nguon_nhan_ban(goc: str, kenh: str, tieu_de: str, cum: List[str], cum_cua: Callable[[str], List[str]],
                   bay_gio: Optional[_dt.datetime] = None, toi_da: int = SO_NGUON_TOI_DA) -> List[Dict[str, Any]]:
    """Ứng viên nguồn để nhân bản một video thắng: video đối thủ trong `content.csv` cùng cụm, chưa ai trong nhóm làm,
    chưa được đề cử; xếp (trùng chủ đề hẹp trước) → tăng/ngày → view. Trả `[{link, ma, tieu_de, kenh_nguon, view,
    tang_ngay, ngay_dang, cap_chung}]`. Không có cụm (`cum` rỗng) thì chỉ nhận ứng viên trùng chủ đề hẹp."""
    bay_gio = bay_gio or _dt.datetime.now()
    hom = bay_gio.date()
    da = _da_lam_ca_nhom(goc, kenh) | _video_cua_minh(goc, kenh)
    de_cu = set()
    try:
        from . import nao  # noqa: PLC0415

        de_cu = {nao._khoa_link((d.get("tham_so") or {}).get("link")) for d in nao._de_cu_mo(goc, kenh)}
    except Exception:  # noqa: BLE001
        pass
    cap_thang = _cap_chu(tieu_de)
    tap_cum = set(cum or [])
    ung: List[Dict[str, Any]] = []
    for r in _doc_csv(os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "content.csv")):
        link = str(r.get("Link video") or "").strip()
        ma = _ma_video(link)
        td = str(r.get("Tiêu đề video") or "").strip()
        if not ma or not td or str(r.get("Đã làm") or "").strip() or ma in da or ma in de_cu:
            continue
        nd = _ngay(r.get("Ngày đăng"))
        view = _so(r.get("View")) or 0.0
        if nd is None or (hom - nd).days > NGAY_NGUON_TOI_DA or view < VIEW_NGUON_TOI_THIEU:
            continue
        chung = len(cap_thang & _cap_chu(td))
        if tap_cum:
            try:
                cung_cum = bool(tap_cum & set(cum_cua(td)))
            except Exception:  # noqa: BLE001
                cung_cum = False
            if not cung_cum:
                continue
        elif chung < SO_CAP_TRUNG_TOI_THIEU:
            continue
        ung.append({"link": link, "ma": ma, "tieu_de": td, "kenh_nguon": str(r.get("Kênh") or "").strip(), "view": view,
                    "tang_ngay": _so(r.get("Tăng/ngày")) or 0.0, "ngay_dang": str(r.get("Ngày đăng") or "")[:10],
                    "cap_chung": chung})
    ung.sort(key=lambda u: (-(u["cap_chung"] >= SO_CAP_TRUNG_TOI_THIEU), -u["tang_ngay"], -u["view"]))
    return ung[:toi_da]


def _video_thang_tho(goc: str, kenh: str, bay_gio: _dt.datetime, ngay: int, he_so: float) -> Tuple[List[Dict[str, Any]], float,
                                                                                               Callable[[str], List[str]]]:
    """Video đăng ≤ `ngay` ngày có hiển thị mốc mới nhất ≥ `he_so` × ngưỡng, từ `chi-so/bang-tom-tat.csv`."""
    nguong, cum_cua, cum_video = _nguong_kenh(goc, kenh, bay_gio)
    han = bay_gio.date() - _dt.timedelta(days=ngay)
    ra: List[Dict[str, Any]] = []
    for r in _doc_csv(os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv")):
        ma, nd = str(r.get("Mã video") or "").strip(), _ngay(r.get("Ngày đăng"))
        hien_thi = _so(r.get("Lượt hiển thị"))
        if not ma or nd is None or nd < han or hien_thi is None or nguong <= 0:
            continue
        ti_so = hien_thi / nguong
        if ti_so < he_so:
            continue
        td = str(r.get("Tiêu đề") or "").strip()
        cum = cum_video.get(ma)
        if not cum:
            try:
                cum = cum_cua(td)
            except Exception:  # noqa: BLE001
                cum = []
        ra.append({"kenh": kenh, "video_id": ma, "tieu_de": td, "ngay_dang": nd.isoformat(), "cum": list(cum or []),
                   "hien_thi": hien_thi, "ctr": str(r.get("Tỷ lệ bấm") or ""), "xem": _so(r.get("Lượt xem")),
                   "moc": str(r.get("Mốc mới nhất") or ""), "nguong": nguong, "ti_so": round(ti_so, 2)})
    ra.sort(key=lambda v: -v["ti_so"])
    return ra, nguong, cum_cua


def _lenh_nguon(kenh: str, u: Dict[str, Any], v: Dict[str, Any], kiem_ngay: str) -> str:
    ly_do = "{0} ({1}) thắng lớn: {2} hiển thị @{3} = {4:.2f}x ngưỡng {5}, CTR {6}; nguồn {7} {8} view +{9}/ngày cùng cụm".format(
        v["video_id"], _nho(v["tieu_de"], 24), _f(v["hien_thi"]), v["moc"] or "?", v["ti_so"], _f(v["nguong"]), v["ctr"] or "?",
        u["ma"], _f(u["view"]), _f(u["tang_ngay"]))
    du_doan = "video kế của {0} làm từ nguồn này có hiển thị 48h >= {1} (ngưỡng thắng của kênh)".format(kenh, _f(v["nguong"]))
    return 'python -m core.nao uu-tien-nguon --kenh {0} --link {1} --ly-do "{2}" --du-doan "{3}" --kiem-ngay {4}'.format(
        kenh, u["link"], ly_do.replace('"', "'"), du_doan, kiem_ngay)


def video_thang_lon(goc: str, kenh: str, bay_gio: Optional[_dt.datetime] = None, *, ngay: int = NGAY_GAN_DAY,
                    he_so: float = HE_SO_THANG_LON, toi_da_nguon: int = SO_NGUON_TOI_DA) -> List[Dict[str, Any]]:
    """Video của kênh đăng ≤ `ngay` ngày mà hiển thị ở mốc mới nhất ≥ `he_so` × ngưỡng thắng 48h của kênh.

    Mỗi phần tử: `{kenh, video_id, tieu_de, ngay_dang, cum, hien_thi, ctr, moc, nguong, ti_so, da_xu_ly, nguon, kiem_ngay}`.
    `nguon` = ứng viên nhân bản (xem `nguon_nhan_ban`) kèm `lenh` = lệnh `uu-tien-nguon` chạy được ngay;
    `da_xu_ly` = id hành động của não đã nhắc video này (rỗng nếu chưa). Hỏng → []."""
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        vs, _ng, cum_cua = _video_thang_tho(goc, kenh, bay_gio, ngay, he_so)
    except Exception:  # noqa: BLE001
        return []
    kiem = _kiem_ngay(goc, kenh, bay_gio) if vs else ""
    for v in vs:
        v["da_xu_ly"] = _hanh_dong_nhac(goc, "uu-tien-nguon", v["video_id"], kenh)
        v["kiem_ngay"] = kiem
        v["nguon"] = []
        if v["da_xu_ly"]:
            continue
        for u in nguon_nhan_ban(goc, kenh, v["tieu_de"], v["cum"], cum_cua, bay_gio, toi_da_nguon):
            u["lenh"] = _lenh_nguon(kenh, u, v, kiem)
            v["nguon"].append(u)
    return vs


# ═══ (b) BÀI HỌC BỊ BÁC BỎ / ĐƯỢC XÁC NHẬN ═══════════════════════════════════

def _co_dac_diem(b: Dict[str, Any], v: Dict[str, Any]) -> str:
    """Mô tả (chữ) đặc điểm của bài `b` mà video thắng `v` CÓ, hoặc "" nếu không chắc / không nhận ra bằng mã."""
    truc, gt, cum_bai = str(b.get("truc") or ""), str(b.get("gia_tri") or ""), str(b.get("cum") or "")
    td, cum_v = v.get("tieu_de") or "", set(v.get("cum") or [])
    if truc == "cum":
        ma = gt or cum_bai
        return "thuộc cụm {0}".format(ma) if ma and ma in cum_v else ""
    if truc not in ("tieu_de", "tu_do"):
        return ""
    if cum_bai and cum_bai not in cum_v and truc == "tieu_de":
        return ""   # bài nói riêng cho một cụm mà video thắng không thuộc cụm đó
    for nhan in _RE_NHAN.findall(str(b.get("cau") or "")):
        if "【{0}】".format(nhan) in td:
            return "tiêu đề mang nhãn 【{0}】".format(nhan)
    if truc == "tieu_de":
        try:
            from . import tu_hoc  # noqa: PLC0415

            if gt == "so_dem" and tu_hoc._RE_SO.search(td):
                return "tiêu đề có số đếm"
            if gt == "cau_hoi" and tu_hoc._RE_HOI.search(td):
                return "tiêu đề dạng câu hỏi"
        except Exception:  # noqa: BLE001
            pass
        if gt == "hai_ve" and re.search(r"[｜|]", _RE_NHAN.sub("", td)):
            return "tiêu đề hai vế (｜)"
    return ""


def bai_hoc_bi_bac_bo(goc: str, kenh: str, bay_gio: Optional[_dt.datetime] = None, *, ngay: int = NGAY_GAN_DAY,
                      he_so: float = HE_SO_THANG_LON, thang: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Bài học trong sổ kênh mà video THẮNG gần đây bác bỏ (`tru`) hoặc xác nhận (`cong`).

    Bài hướng "-" (tránh X) mà video thắng CÓ X → `tru`; bài hướng "+" (nên X) mà video thắng có X → `cong`.
    "Có X" chỉ xét những gì mã nhận chắc từ tiêu đề/cụm (xem `_co_dac_diem`). Bỏ qua bài đã gạch (`bo`) và bài đã có
    `bai-hoc` cùng id nhắc video_id đó. `thang` = danh sách video thắng đã tính sẵn (không có thì tự tính). Hỏng → [].
    Trả `[{id, loai, video_id, dac_diem, bai, lenh}]`."""
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        from .giam_doc import kham_nghiem as kn  # noqa: PLC0415

        if thang is None:
            thang = _video_thang_tho(goc, kenh, bay_gio, ngay, he_so)[0]
        ra: List[Dict[str, Any]] = []
        for b in kn.doc_bai_hoc(goc, kenh, bay_gio=bay_gio):
            if b.get("trang_thai") == "bo" or b.get("huong") not in ("+", "-"):
                continue
            da_co = {str(x.get("video_id")) for x in b.get("bang_chung") or []}
            for v in thang:
                if v["video_id"] in da_co:
                    continue
                dd = _co_dac_diem(b, v)
                if not dd:
                    continue
                loai = "tru" if b["huong"] == "-" else "cong"
                if _hanh_dong_nhac(goc, "bai-hoc", v["video_id"], kenh, noi_dung_id=b["id"]):
                    continue
                ly = "{0} {1} hiển thị @{2} = {3:.2f}x ngưỡng {4}, CTR {5}: {6} — {7} bài \"{8}\"".format(
                    v["video_id"], _nho(v["tieu_de"], 20), v["moc"] or "?", v["ti_so"], _f(v["nguong"]), v["ctr"] or "?", dd,
                    "bác bỏ" if loai == "tru" else "xác nhận", _nho(b.get("cau"), 50))
                ra.append({"kenh": kenh, "id": b["id"], "loai": loai, "video_id": v["video_id"], "dac_diem": dd,
                           "bai": str(b.get("cau") or ""),
                           "lenh": 'python -m core.nao bai-hoc --kenh {0} {1} {2} --ly-do "{3}"'.format(
                               kenh, loai, b["id"], ly.replace('"', "'"))})
                break   # một bài chỉ cần MỘT video làm bằng chứng mỗi lượt
        return ra
    except Exception:  # noqa: BLE001
        return []


# ═══ MỤC CHO `nao xem` ═══════════════════════════════════════════════════════

def dong_bat_buoc(goc: str, kenh_ds: Optional[List[str]] = None, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Các dòng của mục "VIỆC BẮT BUỘC XEM HÔM NAY": lệnh `bai-hoc tru|cong` + `uu-tien-nguon` chạy được ngay.
    Mỗi kênh bọc try riêng. Không có gì → một dòng nói rõ."""
    bay_gio = bay_gio or _dt.datetime.now()
    if kenh_ds is None:
        try:
            from .kenh import liet_ke_kenh  # noqa: PLC0415

            kenh_ds = list(liet_ke_kenh(goc))
        except Exception:  # noqa: BLE001
            kenh_ds = []
    bai: List[str] = []
    thang_dong: List[str] = []
    for k in kenh_ds:
        try:
            vs = video_thang_lon(goc, k, bay_gio)
        except Exception:  # noqa: BLE001
            vs = []
        for b in bai_hoc_bi_bac_bo(goc, k, bay_gio, thang=vs):
            bai.append("  [BÀI HỌC {0}] {1} {2}: {3} — {4} bài \"{5}\"".format(
                "BỊ BÁC BỎ" if b["loai"] == "tru" else "ĐƯỢC XÁC NHẬN", k, b["id"], b["video_id"],
                "bác bỏ" if b["loai"] == "tru" else "xác nhận", _nho(b["bai"], 70)))
            bai.append("      $ " + b["lenh"])
        for v in vs:
            if v["da_xu_ly"]:
                continue
            thang_dong.append("  [THẮNG {0}] {1} {2} {3} | {4} | {5} hiển thị @{6} = {7:.2f}x ngưỡng {8}, CTR {9} | cụm {10}".format(
                "RẤT LỚN" if v["ti_so"] >= HE_SO_RAT_LON else "LỚN", k, v["video_id"], v["ngay_dang"][5:], _nho(v["tieu_de"], 34),
                _f(v["hien_thi"]), v["moc"] or "?", v["ti_so"], _f(v["nguong"]), v["ctr"] or "?", ",".join(v["cum"]) or "?"))
            if not v["nguon"]:
                thang_dong.append("      (không có nguồn cùng cụm chưa làm trong content.csv — tự tìm ở `ĐỐI THỦ ĐANG NỔ`, "
                                  "hoặc ghi rõ vì sao bỏ qua)")
            for i, u in enumerate(v["nguon"]):
                thang_dong.append("      nguồn #{0}: {1} view, +{2}/ngày, {3} | {4} | {5} | trùng chữ {6}".format(
                    i + 1, _f(u["view"]), _f(u["tang_ngay"]), _nho(u["kenh_nguon"], 18), _nho(u["tieu_de"], 36),
                    u["ngay_dang"][5:], u["cap_chung"]))
            if v["nguon"]:
                thang_dong.append("      $ " + v["nguon"][0]["lenh"])
    ra = bai + thang_dong
    return ra or ["  (không có: không bài học nào bị video thắng gần đây bác bỏ/xác nhận, không video thắng lớn chưa xử lý)"]


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    print("\n".join(["VIỆC BẮT BUỘC XEM HÔM NAY (gốc: {0})".format(GOC_MAC_DINH)] + dong_bat_buoc(GOC_MAC_DINH)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
