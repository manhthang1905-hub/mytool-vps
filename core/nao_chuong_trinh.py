"""CHƯƠNG TRÌNH HÔM NAY CỦA BỘ NÃO — mã TÍNH số, não SUY NGHĨ và QUYẾT (12/10/2026).

═══ VÌ SAO ═══ (`workspace/chan-doan/nao-vong-hoc-2026-10-12.md` mục 4, 5 #11, mục 6)

Mục "VIỆC BẮT BUỘC" cũ (`core.nao_goi_y`) biến não thành người bấm lệnh: 100% hành động từ 06/10 là chép lại lệnh
máy in sẵn (cộng/trừ bài học bằng MỘT video, đề cử nguồn), trong khi việc giá trị cao chưa làm lần nào: phân bổ danh
mục kênh, kênh chết, nhân bản video đang nổ, săn khoảng trống chủ đề, A/B bao bì, giữ chân theo đoạn. Tệp này tính sẵn
ĐÚNG chương trình mục 6; não đọc, phản biện, quyết — mỗi hành động ghi cỡ mẫu (n) và ngày kiểm; n < 3 không hành động.

    (a) DANH MỤC KÊNH      view/ngày 7 ngày + xu hướng, hiển thị @48h/@96h so đường cong CỦA CHÍNH kênh, % bàn giao
                           7 ngày (máy này), YPP bằng sub TRỌN ĐỜI, cờ "không được phát" (`core.kenh_khong_phat`).
    (b) RADAR NỔ           video 24–72h có độ dốc hiển thị > phân vị 80 của chính kênh → 1–2 nguồn CÙNG chủ ngữ hẹp,
                           lệnh `uu-tien-nguon --radar <video>` (ép chọn, không tính hạn mức ngày, phải vào sản xuất
                           trong 48 giờ — quá hạn tự đóng không tính điểm).
    (c) SĂN KHOẢNG TRỐNG   (mỗi tuần) vùng đề tài theo NGHĨA có thị trường lớn + đang lên mà cả danh mục chưa có video
                           → kênh chủ vùng (`core.chu_quyen_vung`) + nguồn đối thủ đang tăng.
    (d) BAO BÌ A/B         video mới của kênh được phát → đề nghị "Thử nghiệm và so sánh" bìa của Studio (chủ làm);
                           luật đổi tiêu đề sau đăng (`core.giam_doc.cuu_ctr`): chỉ dưới CTR của chính kênh, không bao
                           giờ cho kênh > 50% traffic đề xuất.
    (e) GIỮ CHÂN THEO ĐOẠN đường giữ chân (`retention.xlsx`) × mốc đoạn trong hồ sơ video (`phan.danh_sach`) so với
                           KÊNH MẪU (kênh nhiều view nhất có ≥ 5 đường giữ chân; `workspace/cai-dat.json: nao_kenh_mau`).

Chỉ ĐỌC đĩa (ngoại lệ: `nao/san-khoang-trong.json` — nhớ lượt săn tuần), không gọi mạng/AI. Mỗi phần, mỗi kênh bọc
try riêng: hỏng phần nào chỉ phần đó in một dòng lỗi.

    python -m core.nao_chuong_trinh          # in chương trình (gốc dữ liệu: MYTOOL_GOC)
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import math
import os
import re
import statistics
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

GOC_MAC_DINH = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

N_TOI_THIEU = 3                 # "n < 3 đừng hành động"
#: Radar nổ.
PV_RADAR = 80.0
N_THAM_CHIEU_RADAR = 5
TANG_TOI_THIEU_RADAR = 500.0    # hiển thị tăng thêm trong 24–72h tối thiểu (chặn nhiễu kênh nhỏ)
TUOI_RADAR = (24.0, 96.0)       # video đang ở tuổi này mới lên radar
GIO_RADAR_SAN_XUAT = 48         # nguồn radar phải vào sản xuất trong ngần này giờ
SO_NGUON_RADAR = 2
#: Săn khoảng trống.
THI_TRUONG_KHOANG_TRONG = 1_000_000.0
THI_PHAN_KHOANG_TRONG = 0.05    # % — dưới mức này coi như danh mục "chưa có"
TEP_SAN = os.path.join("nao", "san-khoang-trong.json")
#: Bao bì.
NGAY_VIDEO_MOI = 3
#: Giữ chân.
N_GIU_CHAN_MAU = 5
SO_VIDEO_GIU_CHAN = 10


# ── tiện ích ────────────────────────────────────────────────────────────────

def _f(x: Any, le: int = 0) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "?"
    if not math.isfinite(v):
        return "?"
    return ("{0:,.%df}" % le).format(v).replace(",", "X").replace(".", ",").replace("X", ".")


def _nho(chu: Any, n: int = 40) -> str:
    s = " ".join(str(chu or "").split()).replace('"', "'")
    return s if len(s) <= n else s[:n - 1] + "…"


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _doc_csv(p: str) -> List[Dict[str, str]]:
    try:
        csv.field_size_limit(10_000_000)
        with io.open(p, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (OSError, csv.Error):
        return []


def _so(x: Any) -> Optional[float]:
    try:
        s = str(x if x is not None else "").strip().replace("%", "").replace(",", "")
        return float(s) if s else None
    except ValueError:
        return None


def _phan_vi(gia_tri: float, mau: Sequence[float]) -> Optional[float]:
    if not mau:
        return None
    duoi = sum(1.0 for x in mau if x < gia_tri) + 0.5 * sum(1.0 for x in mau if x == gia_tri)
    return 100.0 * duoi / len(mau)


def _phan_vi_cua(mau: Sequence[float], p: float) -> Optional[float]:
    xs = sorted(mau)
    if not xs:
        return None
    vt = (len(xs) - 1) * p / 100.0
    i = int(math.floor(vt))
    j = min(len(xs) - 1, i + 1)
    return xs[i] + (xs[j] - xs[i]) * (vt - i)


def _video_kenh(goc: str, kenh: str, bay_gio: _dt.datetime) -> Tuple[List[Any], Callable[[str], List[str]]]:
    """`(VideoMinh của kênh — cùng tập + nhãn thước chung V7 dùng, hàm tiêu đề → cụm)`."""
    from . import cong_thuc_v7 as v7  # noqa: PLC0415

    ch, _ = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    try:
        bg = bay_gio.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        bg = None
    return v7.video_cua_kenh(goc, kenh, ch, bg), (lambda td: list(v7.cum_cua_tieu_de(td, ch) or []))


def _gia_tai(vm: Any, t: float) -> Optional[float]:
    from . import thuoc_thang  # noqa: PLC0415

    c = getattr(vm, "chuoi", None)
    if c is None:
        return None
    k = thuoc_thang.khoang_tai(c.diem, t)
    return None if k is None else float(k[1])


def _dang_epoch(vm: Any) -> Optional[float]:
    c = getattr(vm, "chuoi", None)
    return getattr(c, "dang", None) if c is not None else None


# ═══ (a) DANH MỤC KÊNH ═══════════════════════════════════════════════════════

#: Ghi tệp trạng thái khi tính cờ "không được phát" (chạy thử `--thu` → False).
_GHI = [True]


def dang_dung(goc: str, kenh: str) -> bool:
    """Kênh đang bị dừng vì không được YouTube phát (`core.kenh_khong_phat`, tính lại nếu cần)."""
    try:
        from . import kenh_khong_phat  # noqa: PLC0415

        return bool(kenh_khong_phat.dang_dung(goc, kenh, tinh=True, ghi=_GHI[0])[0])
    except Exception:  # noqa: BLE001
        return False


def _ban_giao_7_ngay(goc: str, kenh: str, bay_gio: _dt.datetime) -> int:
    try:
        from . import tu_chay  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return 0
    n = 0
    for i in range(7):
        ngay = (bay_gio.date() - _dt.timedelta(days=i)).isoformat()
        for r in tu_chay._doc_bao_cao_ngay(goc, kenh, ngay).get("runs") or []:  # noqa: SLF001
            if (r.get("ban_giao") or {}).get("da_ban_giao"):
                n += 1
    return n


def duong_cong(vs: Sequence[Any], t: float, so: int = 10) -> Tuple[Optional[float], int]:
    """`(trung vị hiển thị ở tuổi t, n)` của tối đa `so` video MỚI NHẤT có số ở tuổi đó (đường cong của chính kênh)."""
    gia = []
    for vm in sorted(vs, key=lambda v: -(_dang_epoch(v) or 0.0)):
        g = _gia_tai(vm, t)
        if g is not None:
            gia.append(g)
            if len(gia) >= so:
                break
    return (statistics.median(gia) if gia else None), len(gia)


def danh_muc(goc: str, kenh_ds: Sequence[str], bay_gio: _dt.datetime) -> Dict[str, Dict[str, Any]]:
    """`{kênh: {view, cong48, cong96, moi48, ban_giao, ypp, khong_phat, loi}}` — số thô cho bảng danh mục."""
    from . import chi_so_kenh, kenh_khong_phat, ypp  # noqa: PLC0415

    ra: Dict[str, Dict[str, Any]] = {}
    for k in kenh_ds:
        d: Dict[str, Any] = {"loi": []}
        for ten, ham in (("view", lambda: chi_so_kenh.view_ngay(goc, k)),
                         ("ypp", lambda: ypp.du_bao(goc, k, bay_gio)),
                         ("khong_phat", lambda: dict(kenh_khong_phat.tom_tat(goc, k), dung=dang_dung(goc, k))),
                         ("ban_giao", lambda: _ban_giao_7_ngay(goc, k, bay_gio))):
            try:
                d[ten] = ham()
            except Exception as loi:  # noqa: BLE001
                d["loi"].append("{0}: {1}".format(ten, str(loi)[:60]))
        try:
            vs, _cc = _video_kenh(goc, k, bay_gio)
            d["cong48"], d["cong96"] = duong_cong(vs, 48.0), duong_cong(vs, 96.0)
            moi = sorted((v for v in vs if _gia_tai(v, 48.0) is not None), key=lambda v: -(_dang_epoch(v) or 0.0))
            if moi:
                v0 = moi[0]
                g = _gia_tai(v0, 48.0)
                mau = [x for x in (_gia_tai(v, 48.0) for v in moi[1:11]) if x is not None]
                d["moi48"] = {"ma": v0.ma, "gia": g, "pv": _phan_vi(g, mau) if len(mau) >= N_TOI_THIEU else None,
                              "n": len(mau)}
        except Exception as loi:  # noqa: BLE001
            d["loi"].append("đường cong: {0}".format(str(loi)[:60]))
        ra[k] = d
    return ra


def dong_danh_muc(goc: str, kenh_ds: Sequence[str], bay_gio: _dt.datetime) -> List[str]:
    dm = danh_muc(goc, kenh_ds, bay_gio)
    tong_view = sum(float((d.get("view") or {}).get("tb7") or 0.0) for d in dm.values())
    tong_bg = sum(int(d.get("ban_giao") or 0) for d in dm.values())
    ra = ["  (view/ngày = trung bình 7 ngày Studio đã chốt; xu hướng = so 7 ngày trước; @48h/@96h = trung vị hiển thị "
          "≤ 10 video mới nhất của CHÍNH kênh ở tuổi đó; bàn giao = gói làm xong 7 ngày trên máy này)"]
    dung_ds = []
    for k in kenh_ds:
        d = dm.get(k) or {}
        v = d.get("view") or {}
        y = d.get("ypp") or {}
        kp = d.get("khong_phat") or {}
        xu = v.get("xu_huong")
        c48, n48 = d.get("cong48") or (None, 0)
        c96, n96 = d.get("cong96") or (None, 0)
        m48 = d.get("moi48") or {}
        bg = int(d.get("ban_giao") or 0)
        if kp.get("dung"):
            dung_ds.append(k)
        ra.append("- {0}{1}: view/ngày {2} ({3}, chốt {4}) · {5}% view danh mục · bàn giao 7 ngày {6} ({7}% khe)".format(
            k, " [KHÔNG ĐƯỢC PHÁT — đang dừng]" if kp.get("dung") else "", _f(v.get("tb7")),
            "xu hướng ×{0}".format(_f(xu, 2)) if xu is not None else "chưa đủ 14 ngày",
            str(v.get("ngay_cuoi") or "?")[5:], _f(100.0 * float(v.get("tb7") or 0) / tong_view, 1) if tong_view else "?",
            bg, _f(100.0 * bg / tong_bg) if tong_bg else "?"))
        ra.append("    hiển thị @48h trung vị {0} (n {1}), @96h {2} (n {3}); video mới nhất {4} @48h {5}{6}".format(
            _f(c48), n48, _f(c96), n96, m48.get("ma") or "?", _f(m48.get("gia")),
            " = phân vị {0} kênh (n {1})".format(_f(m48.get("pv")), m48.get("n")) if m48.get("pv") is not None
            else " (n tham chiếu < 3 — chưa so)" if m48 else ""))
        try:
            from . import ypp as _ypp  # noqa: PLC0415

            eta = {"dat": "ĐÃ ĐỦ — nộp đơn", "cham": "không tăng", "chua_du_so": "chưa đủ số"}.get(y.get("trang_thai"))
            if eta is None and float(y.get("ngay_toi") or 0) > 730:
                eta = "tốc độ hiện tại > 2 năm — chưa có đường tới YPP"
            if eta is None:
                eta = "ETA {0} (~{1} ngày; thiếu {2})".format(
                    y.get("ngay_du_kien") or "?", _f(y.get("ngay_toi")),
                    "sub" if (y.get("ngay_dk") or 0) >= (y.get("ngay_gio") or 0) else "giờ xem")
            ra.append("    YPP: {0} (+{1}/ngày) · {2} (+{3}/ngày) · {4}".format(
                _ypp.nhan_sub(y), _f(y.get("toc_dk"), 1), _ypp.nhan_gio(y), _f(y.get("toc_gio"), 0), eta))
        except Exception:  # noqa: BLE001
            pass
        if d.get("loi"):
            ra.append("    (thiếu số: {0})".format("; ".join(d["loi"])[:160]))
    if dung_ds:
        bg_dung = sum(int((dm.get(k) or {}).get("ban_giao") or 0) for k in dung_ds)
        ra.append("  → Kênh đang dừng vì không được phát: {0} — chiếm {1}/{2} bàn giao 7 ngày qua ({3}%); đã báo chủ "
                  "kiểm Studio; lượt dở xếp sau, kho clip dồn cho kênh sống. Bạn quyết: đề xuất chủ dồn khe/hạn mức "
                  "(`de-xuat`) nếu kênh sống thiếu khe.".format(", ".join(dung_ds), bg_dung, tong_bg,
                                                               _f(100.0 * bg_dung / tong_bg) if tong_bg else "?"))
    return ra


# ═══ (b) RADAR NỔ ════════════════════════════════════════════════════════════

def doc_24_72(vm: Any, tuoi_nay: Optional[float] = None) -> Optional[Tuple[float, float, float]]:
    """`(độ dốc hiển thị/giờ, hiển thị tăng thêm, tuổi cuối)` từ 24h tới bản chụp muộn nhất ≤ 72h (video đã qua
    72h: nội suy ở đúng 72h). None khi thiếu số ở ~24h hoặc đoạn đo < 6 giờ."""
    c = getattr(vm, "chuoi", None)
    if c is None:
        return None
    g24 = _gia_tai(vm, 24.0)
    if g24 is None:
        return None
    pts = [d for d in c.diem if d.hien_thi is not None and 24.0 < d.tuoi <= 72.0]
    if (tuoi_nay or 0.0) >= 72.0 or (pts and max(d.tuoi for d in pts) >= 70.0):
        g72 = _gia_tai(vm, 72.0)
        if g72 is not None:
            return (g72 - g24) / 48.0, g72 - g24, 72.0
    if not pts:
        return None
    d = max(pts, key=lambda x: x.tuoi)
    if d.tuoi - 24.0 < 6.0:
        return None
    return (float(d.hien_thi) - g24) / (d.tuoi - 24.0), float(d.hien_thi) - g24, d.tuoi


def radar_kenh(goc: str, kenh: str, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """`{video: [{ma, tieu_de, cum, doc, tang, tuoi, pv, p80, n}], n_tham_chieu, p80, ly_do}` — video tuổi 24–96h có
    độ dốc 24–72h > phân vị 80 của các video KHÁC của chính kênh (n ≥ 5) và tăng ≥ `TANG_TOI_THIEU_RADAR`."""
    bay_gio = bay_gio or _dt.datetime.now()
    now = bay_gio.timestamp()
    vs, cum_cua = _video_kenh(goc, kenh, bay_gio)
    ra: Dict[str, Any] = {"video": [], "n_tham_chieu": 0, "p80": None, "ly_do": "", "cum_cua": cum_cua}
    doc: Dict[str, Tuple[float, float, float]] = {}
    tuoi: Dict[str, Optional[float]] = {}
    for vm in vs:
        dg = _dang_epoch(vm)
        tuoi[vm.ma] = (now - dg) / 3600.0 if dg else vm.tuoi_gio
        x = doc_24_72(vm, tuoi[vm.ma])
        if x is not None:
            doc[vm.ma] = x
    for vm in vs:
        t = tuoi.get(vm.ma)
        if vm.ma not in doc or t is None or not (TUOI_RADAR[0] <= t <= TUOI_RADAR[1]):
            continue
        mau = [doc[m][0] for m in doc if m != vm.ma and (tuoi.get(m) or 0) >= 72.0]
        if len(mau) < N_THAM_CHIEU_RADAR:
            ra["ly_do"] = "chưa đủ {0} video tham chiếu có số 24–72h (mới {1})".format(N_THAM_CHIEU_RADAR, len(mau))
            continue
        p80 = _phan_vi_cua(mau, PV_RADAR)
        dc, tang, tc = doc[vm.ma]
        ra["n_tham_chieu"], ra["p80"] = len(mau), p80
        if p80 is not None and dc > p80 and tang >= TANG_TOI_THIEU_RADAR:
            ra["video"].append({"ma": vm.ma, "tieu_de": vm.tieu_de, "cum": list(vm.cum or []), "doc": dc,
                                "tang": tang, "tuoi_do": tc, "tuoi": t, "pv": _phan_vi(dc, mau), "p80": p80,
                                "n": len(mau)})
    ra["video"].sort(key=lambda x: -x["doc"])
    return ra


def la_radar(goc: str, kenh: str, video_id: str, bay_gio: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """CLI `uu-tien-nguon --radar` kiểm bằng mã: video có đang trên radar nổ của kênh không. `(có?, lý do)`."""
    try:
        r = radar_kenh(goc, kenh, bay_gio)
    except Exception as loi:  # noqa: BLE001
        return False, "không tính được radar: {0}".format(str(loi)[:100])
    for v in r["video"]:
        if v["ma"] == video_id:
            return True, "độ dốc {0}/giờ > phân vị 80 kênh {1}/giờ (n {2})".format(_f(v["doc"]), _f(v["p80"]), v["n"])
    return False, "video {0} không nằm trên radar nổ của {1} hôm nay ({2})".format(
        video_id, kenh, r.get("ly_do") or "độ dốc 24–72h không vượt phân vị 80 của kênh")


def _radar_da_ep(goc: str, kenh: str, video_id: str) -> List[str]:
    try:
        from . import nao  # noqa: PLC0415

        return [str(d.get("id")) for d in nao.doc_hanh_dong(goc)
                if d.get("lenh") == "uu-tien-nguon" and d.get("trang_thai") != "huy"
                and (d.get("tham_so") or {}).get("kenh") == kenh and (d.get("tham_so") or {}).get("radar") == video_id]
    except Exception:  # noqa: BLE001
        return []


def dong_radar(goc: str, kenh_ds: Sequence[str], bay_gio: _dt.datetime) -> List[str]:
    from . import nao_goi_y  # noqa: PLC0415

    ra: List[str] = []
    im: List[str] = []
    for k in kenh_ds:
        try:
            if dang_dung(goc, k):
                continue
            r = radar_kenh(goc, k, bay_gio)
        except Exception as loi:  # noqa: BLE001
            im.append("{0}: lỗi {1}".format(k, str(loi)[:60]))
            continue
        if not r["video"]:
            im.append("{0} ({1})".format(k, r.get("ly_do") or "không video nào vượt P80, n {0}".format(r["n_tham_chieu"])))
            continue
        kiem = nao_goi_y._kiem_ngay(goc, k, bay_gio)  # noqa: SLF001
        for v in r["video"][:2]:
            da = _radar_da_ep(goc, k, v["ma"])
            ra.append("- [RADAR] {0} {1} «{2}» cụm {3}: +{4} hiển thị trong {5:.0f}h = {6}/giờ > P80 kênh {7}/giờ "
                      "(phân vị {8}, n {9}){10}".format(
                          k, v["ma"], _nho(v["tieu_de"], 30), ",".join(v["cum"]) or "?", _f(v["tang"]),
                          v["tuoi_do"] - 24.0, _f(v["doc"]), _f(v["p80"]), _f(v["pv"]), v["n"],
                          " — ĐÃ ép: " + ", ".join(da) if da else ""))
            if len(da) >= SO_NGUON_RADAR:
                continue
            try:
                nguon = nao_goi_y.nguon_nhan_ban(goc, k, v["tieu_de"], v["cum"], r["cum_cua"], bay_gio,
                                                 SO_NGUON_RADAR - len(da))
            except Exception:  # noqa: BLE001
                nguon = []
            hep = [u for u in nguon if u["cap_chung"] >= nao_goi_y.SO_CAP_TRUNG_TOI_THIEU]
            if not nguon:
                ra.append("    (không có nguồn cùng cụm chưa làm trong content.csv — tự tìm ở ĐỐI THỦ ĐANG NỔ, hoặc ghi "
                          "lý do bỏ qua)")
            for u in (hep or nguon):
                ly = "RADAR {0}: +{1} hiển thị 24–{2:.0f}h = {3}/giờ > P80 kênh {4}/giờ (n {5}); nguồn {6} {7} view " \
                     "+{8}/ngày, trùng chữ {9}".format(v["ma"], _f(v["tang"]), v["tuoi_do"], _f(v["doc"]),
                                                      _f(v["p80"]), v["n"], u["ma"], _f(u["view"]), _f(u["tang_ngay"]),
                                                      u["cap_chung"])
                du = ("video làm từ nguồn này đạt phân vị ≥ 50 hiển thị @96h so kênh {0} (thước chung, n tham chiếu "
                      "{1})").format(k, v["n"])
                ra.append("    nguồn: {0} | {1} | {2} view +{3}/ngày | trùng chữ {4}{5}".format(
                    _nho(u["kenh_nguon"], 16), _nho(u["tieu_de"], 34), _f(u["view"]), _f(u["tang_ngay"]),
                    u["cap_chung"], "" if u in hep else " (chỉ cùng cụm, không cùng chủ ngữ hẹp)"))
                ra.append('      $ python -m core.nao uu-tien-nguon --kenh {0} --link {1} --radar {2} --ly-do "{3}" '
                          '--du-doan "{4}" --kiem-ngay {5}'.format(k, u["link"], v["ma"], ly, du, kiem))
    if not ra:
        ra.append("- không video nào đang nổ sớm (độ dốc 24–72h > phân vị 80 của chính kênh)")
    if im:
        ra.append("  (không radar: {0})".format("; ".join(im))[:400])
    ra.append("  Luật: `--radar` = ép chọn (biên tập chỉ phủ quyết), KHÔNG tính 3 hành động/ngày, tối đa {0} nguồn mỗi "
              "video; phải vào sản xuất trong {1} giờ, quá hạn tự đóng không tính điểm.".format(SO_NGUON_RADAR,
                                                                                               GIO_RADAR_SAN_XUAT))
    return ra


def dong_thang(goc: str, kenh_ds: Sequence[str], bay_gio: _dt.datetime) -> List[str]:
    """Video THẮNG đã phán (≥ 96h) / ĐANG NÓNG (thước chung) chưa có đề cử nhân bản (`nao_goi_y.dong_bat_buoc`) —
    tham khảo cạnh radar, KHÔNG bắt buộc (lệnh này TÍNH vào 3 hành động/ngày)."""
    from . import nao_goi_y  # noqa: PLC0415

    song = [k for k in kenh_ds if not dang_dung(goc, k)]
    ds = [x for x in nao_goi_y.dong_bat_buoc(goc, song, bay_gio) if "(không có video" not in x]
    return (["  Video thắng / đang nóng chưa nhân bản (tính hạn mức ngày):"] + ds) if ds else []


# ═══ (c) SĂN KHOẢNG TRỐNG (tuần) ════════════════════════════════════════════

def _lich_su_chien_truong(goc: str) -> List[Dict[str, Any]]:
    try:
        with io.open(os.path.join(goc, "workspace", "chien-truong", "lich-su.jsonl"), encoding="utf-8") as tep:
            ds = [json.loads(x) for x in tep.read().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []
    return [d for d in ds if isinstance(d, dict)]


def _vung_dict(d: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    v = d.get("vung")
    if isinstance(v, dict):
        return {str(k): {"dich": float((x or {}).get("dich") or 0), "ta": float((x or {}).get("ta") or 0),
                         "thi_phan": float((x or {}).get("thi_phan") or 0)} for k, x in v.items()}
    if isinstance(v, list):
        return {str(x.get("ma")): {"dich": float(x.get("dich") or 0), "ta": float(x.get("ta") or 0),
                                   "thi_phan": float(x.get("thi_phan") or 0)} for x in v if isinstance(x, dict)}
    return {}


def khoang_trong(goc: str, bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Vùng đề tài (theo nghĩa, `chien_truong`) thị trường ≥ `THI_TRUONG_KHOANG_TRONG` view đối thủ 28 ngày, danh mục
    gần như chưa có (thị phần < `THI_PHAN_KHOANG_TRONG`%), xếp theo ĐÀ (đổi thị trường 7 ngày) rồi cỡ. Mỗi mục:
    `{vung, dich, da_7, ta, chu, chu_nguon}` — chủ = bản đồ chủ quyền vùng (đã ghi), không có thì kênh được phát mà
    `chu_quyen_vung.chon_chu` đề xuất (máy, không AI)."""
    ls = _lich_su_chien_truong(goc)
    if not ls:
        return []
    moi = _vung_dict(ls[-1])
    ngay_moi = str(ls[-1].get("ngay") or "")
    cu: Dict[str, Dict[str, float]] = {}
    try:
        d0 = _dt.date.fromisoformat(ngay_moi) - _dt.timedelta(days=7)
        truoc = [x for x in ls[:-1] if str(x.get("ngay") or "") <= d0.isoformat()] or ls[:1]
        cu = _vung_dict(truoc[-1]) if truoc else {}
    except ValueError:
        pass
    ra = []
    for v, x in moi.items():
        if v in ("", "khac") or x["dich"] < THI_TRUONG_KHOANG_TRONG or x["thi_phan"] >= THI_PHAN_KHOANG_TRONG:
            continue
        ra.append({"vung": v, "dich": x["dich"], "da_7": x["dich"] - (cu.get(v) or {}).get("dich", x["dich"]),
                   "ta": x["ta"], "chu": "", "chu_nguon": ""})
    if not ra:
        return []
    try:
        from . import chu_quyen_vung  # noqa: PLC0415

        bd = chu_quyen_vung.doc(goc)
        song = bd.get("kenh_duoc_phat") or {}
        de = None
        for m in ra:
            o = chu_quyen_vung.chu_cua(bd, m["vung"])
            if o.get("chu") and song.get(o["chu"], True):
                m["chu"], m["chu_nguon"] = o["chu"], "bản đồ chủ quyền ({0})".format(o.get("ly_do") or "")[:110]
                continue
            if de is None:
                de = chu_quyen_vung.de_xuat(goc, thi_truong={x["vung"]: x["dich"] for x in ra}, bay_gio=bay_gio)
            o = chu_quyen_vung.chu_cua(de, m["vung"])
            if o.get("chu"):
                m["chu"], m["chu_nguon"] = o["chu"], "máy đề xuất ({0})".format(o.get("ly_do") or "")[:110]
    except Exception:  # noqa: BLE001
        pass
    ra.sort(key=lambda m: (-(m["da_7"] > 0), -m["da_7"], -m["dich"]))
    return ra


def _nguon_vung(goc: str, kenh: str, vung: str, toi_da: int = 2) -> List[Dict[str, Any]]:
    """Video đối thủ thuộc vùng (`workspace/chien-truong/vung-ai.json`, AI gán theo nghĩa) trong `content.csv` của
    kênh, chưa làm — xếp tăng/ngày."""
    va = _doc_json(os.path.join(goc, "workspace", "chien-truong", "vung-ai.json")) or {}
    theo = va.get("video") if isinstance(va, dict) else {}
    if not isinstance(theo, dict):
        return []
    from . import nao_goi_y  # noqa: PLC0415

    trong = {nao_goi_y._ma_video(l) for l, v in theo.items() if v == vung}  # noqa: SLF001
    trong.discard("")
    da = nao_goi_y._da_lam_ca_nhom(goc, kenh) | nao_goi_y._video_cua_minh(goc, kenh)  # noqa: SLF001
    ra = []
    for r in _doc_csv(os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "content.csv")):
        link = str(r.get("Link video") or "").strip()
        ma = nao_goi_y._ma_video(link)  # noqa: SLF001
        if not ma or ma not in trong or ma in da or str(r.get("Đã làm") or "").strip():
            continue
        ra.append({"link": link, "ma": ma, "tieu_de": str(r.get("Tiêu đề video") or ""),
                   "tang_ngay": _so(r.get("Tăng/ngày")) or 0.0, "view": _so(r.get("View")) or 0.0})
    ra.sort(key=lambda u: (-u["tang_ngay"], -u["view"]))
    return ra[:toi_da]


def _tuan(bay_gio: _dt.datetime) -> str:
    y, w, _d = bay_gio.isocalendar()
    return "{0}-W{1:02d}".format(y, w)


def dong_khoang_trong(goc: str, bay_gio: _dt.datetime, ghi: bool = True) -> List[str]:
    """Mỗi tuần một lượt săn ĐẦY ĐỦ (ngày đầu tiên `xem` chạy trong tuần — nhớ ở `nao/san-khoang-trong.json`); các
    ngày khác in một dòng tóm tắt."""
    from . import nao_goi_y  # noqa: PLC0415

    p = os.path.join(goc, TEP_SAN)
    nho = _doc_json(p) or {}
    tuan = _tuan(bay_gio)
    hom = bay_gio.date().isoformat()
    if nho.get("tuan") == tuan and nho.get("ngay") != hom:
        return ["- tuần {0} đã săn ngày {1}: {2} — săn lại tuần sau (chi tiết: {3})".format(
            tuan, nho.get("ngay"), nho.get("tom_tat") or "?", TEP_SAN.replace("\\", "/"))]
    ds = khoang_trong(goc, bay_gio)
    ra = ["- TUẦN {0} — vùng thị trường ≥ {1} view đối thủ/28 ngày mà danh mục < {2}% thị phần (đà = đổi thị trường "
          "7 ngày):".format(tuan, _f(THI_TRUONG_KHOANG_TRONG), _f(THI_PHAN_KHOANG_TRONG, 2))]
    tom = []
    for m in ds[:5]:
        ra.append("  · {0}: thị trường {1} (đà {2}{3}) · ta {4} · chủ: {5}".format(
            m["vung"], _f(m["dich"]), "+" if m["da_7"] >= 0 else "", _f(m["da_7"]), _f(m["ta"]),
            "{0} — {1}".format(m["chu"], m["chu_nguon"]) if m["chu"] else "chưa có kênh được phát hợp tệp"))
        tom.append("{0}→{1}".format(m["vung"], m["chu"] or "?"))
        if not m["chu"]:
            continue
        try:
            nguon = _nguon_vung(goc, m["chu"], m["vung"])
        except Exception:  # noqa: BLE001
            nguon = []
        kiem = nao_goi_y._kiem_ngay(goc, m["chu"], bay_gio)  # noqa: SLF001
        for u in nguon[:1]:
            ra.append("      nguồn: {0} | {1} view +{2}/ngày".format(_nho(u["tieu_de"], 40), _f(u["view"]),
                                                                    _f(u["tang_ngay"])))
            ra.append('      $ python -m core.nao uu-tien-nguon --kenh {0} --link {1} --ly-do "KHOẢNG TRỐNG {2}: thị '
                      'trường {3} view/28 ngày, đà 7 ngày {4}, danh mục {5}; nguồn +{6}/ngày" --du-doan "video đầu '
                      'tiên của {0} trong vùng {2} đạt phân vị ≥ 50 hiển thị @96h so kênh (thước chung)" '
                      '--kiem-ngay {7}'.format(m["chu"], u["link"], m["vung"], _f(m["dich"]), _f(m["da_7"]),
                                               _f(m["ta"]), _f(u["tang_ngay"]), kiem))
        if not nguon:
            ra.append("      (content.csv của {0} chưa có video đối thủ thuộc vùng này — `de-xuat` mở rộng quét đối "
                      "thủ vùng {1}, hoặc ghi lý do bỏ)".format(m["chu"], m["vung"]))
    if not ds:
        ra.append("  (không vùng nào đủ lớn mà danh mục bỏ trống — hoặc chưa có lịch sử chiến trường)")
    ra.append("  Bạn quyết: ≤ 1–2 vùng/tuần, giao ĐÚNG kênh chủ (không giao một vùng cho 2 kênh); n video thắng trong "
              "vùng = 0 nên dự đoán phải khiêm tốn (phân vị ≥ 50 @96h).")
    if not ghi:
        return ra
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as tep:
            json.dump({"tuan": tuan, "ngay": hom, "tom_tat": ", ".join(tom)[:300] or "không có vùng trống",
                       "vung": ds[:10]}, tep, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return ra


# ═══ (d) BAO BÌ A/B ══════════════════════════════════════════════════════════

def dong_bao_bi(goc: str, kenh_ds: Sequence[str], bay_gio: _dt.datetime) -> List[str]:
    from .giam_doc import cuu_ctr  # noqa: PLC0415

    ra: List[str] = []
    moi: List[str] = []
    cam: List[str] = []
    ctr_moi: List[float] = []
    han = (bay_gio.date() - _dt.timedelta(days=NGAY_VIDEO_MOI)).isoformat()
    for k in kenh_ds:
        try:
            if dang_dung(goc, k):
                continue
            dx = cuu_ctr.pct_de_xuat_kenh(goc, k)
            if dx is not None and dx > cuu_ctr.NGUONG_DE_XUAT:
                cam.append("{0} ({1}% đề xuất)".format(k, _f(dx)))
            from . import ho_so_video  # noqa: PLC0415
            from .chien_luoc import ket_qua  # noqa: PLC0415

            goi = {str(h.get("video_id")): g for g, h in ket_qua.ho_so_theo_goi(goc, k).items() if h.get("video_id")}
            for r in _doc_csv(os.path.join(goc, "CHANNEL", k, "chi-so", "bang-tom-tat.csv")):
                vid, nd = str(r.get("Mã video") or ""), str(r.get("Ngày đăng") or "")[:10]
                if not vid or nd < han:
                    continue
                g = goi.get(vid, "")
                b2 = ho_so_video.duong_bia_2_ho_so(goc, k, g) if g else ""
                c = _so(r.get("Tỷ lệ bấm"))
                if c is not None and (_so(r.get("Lượt hiển thị")) or 0) >= 300:
                    ctr_moi.append(c)
                moi.append("  · {0} {1} ({2}) «{3}» CTR {4}{5}".format(
                    k, vid, nd[5:], _nho(r.get("Tiêu đề"), 28), r.get("Tỷ lệ bấm") or "?",
                    " · bìa hạng nhì có sẵn: CHANNEL/{0}/ho-so-video/anh/{1}-bia-2.jpg".format(k, g)
                    if b2 and os.path.isfile(b2) else ""))
        except Exception as loi:  # noqa: BLE001
            ra.append("  ({0}: lỗi {1})".format(k, str(loi)[:60]))
    if moi:
        ra.append("- Video ≤ {0} ngày của kênh được phát → đề nghị chủ bật Studio \"Thử nghiệm và so sánh\" (A/B bìa, "
                  "Studio tự chọn bìa thắng theo thời gian xem) thay cho sửa tuần tự:".format(NGAY_VIDEO_MOI))
        ra += moi[:10]
        ra.append('      $ python -m core.nao de-xuat "Bật Thử nghiệm và so sánh (bìa) trong Studio cho: {0}" --du-doan '
                  '"CTR 48h của video có A/B cao hơn trung vị CTR kênh" --kiem-ngay {1} --ly-do "lứa video mới: CTR trung vị '
                  '{2}% (n {3} video ≥ 300 hiển thị); A/B song song đo được trong 1–2 tuần"'.format(
                      ", ".join(x.split()[2] for x in moi[:6]),
                      (bay_gio.date() + _dt.timedelta(days=7)).isoformat(),
                      _f(statistics.median(ctr_moi), 1) if ctr_moi else "?", len(ctr_moi)))
    else:
        ra.append("- không có video mới (≤ {0} ngày) của kênh được phát".format(NGAY_VIDEO_MOI))
    ra.append("- Đổi tiêu đề sau đăng (giám đốc, `cuu_ctr`): CHỈ video dưới CTR của chính kênh (≥ {0} video so) — "
              "KHÔNG BAO GIỜ cho kênh > {1:.0f}% traffic đề xuất{2}. Mã đã chặn; đừng đề xuất ngược luật.".format(
                  cuu_ctr.N_CTR_RIENG, cuu_ctr.NGUONG_DE_XUAT, ": " + ", ".join(cam) if cam else ""))
    return ra


# ═══ (e) GIỮ CHÂN THEO ĐOẠN ═════════════════════════════════════════════════

def _dau(x: float) -> str:
    return ("+" if x >= 0 else "−") + _f(abs(x), 1)


def _giu_tai(r: Sequence[float], dai: float, giay: float) -> Optional[float]:
    if not r or not dai or giay >= dai or giay < 0:
        return None
    return float(r[min(len(r) - 1, int(giay / dai * len(r)))])


def giu_chan_kenh(goc: str, kenh: str, toi_da: int = SO_VIDEO_GIU_CHAN) -> List[Dict[str, Any]]:
    """Mỗi video (mới nhất trước, ≤ `toi_da`) có đường giữ chân: `{ma, r, dai, doan[(bắt đầu, hết lời)]}`."""
    from .chien_luoc import bai_hoc, ket_qua  # noqa: PLC0415

    thu = os.path.join(goc, "CHANNEL", kenh, "chi-so")
    hs = {str(h.get("video_id")): h for h in ket_qua.ho_so_theo_goi(goc, kenh).values() if h.get("video_id")}
    try:
        ten = [x for x in os.listdir(thu) if len(x) == 11 and os.path.isdir(os.path.join(thu, x))]
    except OSError:
        return []
    ten.sort(key=lambda x: -os.path.getmtime(os.path.join(thu, x)))
    ra = []
    for ma in ten:
        r, dai = bai_hoc._duong_giu_chan(os.path.join(thu, ma))  # noqa: SLF001
        if not r or not dai:
            continue
        doan = []
        for p in (((hs.get(ma) or {}).get("phan") or {}).get("danh_sach") or []):
            b, h = _so(p.get("bat_dau")), _so(p.get("het_loi"))
            if b is not None and h is not None and h > b:
                doan.append((b, h))
        ra.append({"ma": ma, "r": r, "dai": float(dai), "doan": doan})
        if len(ra) >= toi_da:
            break
    return ra


def _kenh_mau(goc: str, kenh_ds: Sequence[str], giu: Dict[str, List[Dict[str, Any]]]) -> str:
    """Kênh mẫu giữ chân: `workspace/cai-dat.json: nao_kenh_mau`, không thì kênh NHIỀU GIỜ XEM nhất (≤ 365 ngày,
    `core.ypp`) có ≥ `N_GIU_CHAN_MAU` đường giữ chân — kênh đã chứng minh giữ được người xem."""
    cai = _doc_json(os.path.join(goc, "workspace", "cai-dat.json")) or {}
    tay = str((cai or {}).get("nao_kenh_mau") or "").strip() if isinstance(cai, dict) else ""
    if tay and tay in giu:
        return tay
    try:
        from . import ypp  # noqa: PLC0415

        ung = [(float(ypp.du_bao(goc, k).get("gio") or 0.0), k) for k in kenh_ds
               if len(giu.get(k) or []) >= N_GIU_CHAN_MAU]
    except Exception:  # noqa: BLE001
        ung = []
    return max(ung)[1] if ung else ""


def dong_giu_chan(goc: str, kenh_ds: Sequence[str], bay_gio: _dt.datetime) -> List[str]:
    giu: Dict[str, List[Dict[str, Any]]] = {}
    for k in kenh_ds:
        try:
            giu[k] = giu_chan_kenh(goc, k)
        except Exception:  # noqa: BLE001
            giu[k] = []
    mau = _kenh_mau(goc, kenh_ds, giu)
    if not mau:
        return ["- chưa kênh nào có ≥ {0} đường giữ chân để làm kênh mẫu".format(N_GIU_CHAN_MAU)]

    def tv(ds: List[Dict[str, Any]], giay: float) -> Tuple[Optional[float], int]:
        xs = [x for x in (_giu_tai(v["r"], v["dai"], giay) for v in ds) if x is not None]
        return (statistics.median(xs) if xs else None), len(xs)

    m30, nm = tv(giu[mau], 30.0)
    m120, _n = tv(giu[mau], 120.0)
    ra = ["- Kênh mẫu {0} (n {1}): còn {2}% ở 0:30, {3}% ở 2:00 (trung vị; nguồn retention.xlsx muộn nhất mỗi "
          "video)".format(mau, nm, _f(m30), _f(m120))]
    for k in kenh_ds:
        if k == mau:
            continue
        ds = giu.get(k) or []
        if len(ds) < N_TOI_THIEU:
            if ds:
                ra.append("  · {0}: n {1} < {2} — chưa so".format(k, len(ds), N_TOI_THIEU))
            continue
        a30, n30 = tv(ds, 30.0)
        a120, _n = tv(ds, 120.0)
        mo = [v["doan"][0][1] for v in ds if v["doan"]]
        dong = "  · {0} (n {1}): 0:30 {2}% ({3} điểm so mẫu) · 2:00 {4}% ({5})".format(
            k, n30, _f(a30), _dau((a30 or 0) - (m30 or 0)), _f(a120), _dau((a120 or 0) - (m120 or 0)))
        if len(mo) >= N_TOI_THIEU:
            t_mo = statistics.median(mo)
            giu_mo = statistics.median([x for x in (_giu_tai(v["r"], v["dai"], v["doan"][0][1]) for v in ds
                                                    if v["doan"]) if x is not None] or [0.0])
            mau_mo, _nn = tv(giu[mau], t_mo)
            # Đoạn lệch mẫu nặng nhất: điểm % MẤT trong đoạn (bắt đầu → hết lời) trừ điểm % kênh mẫu mất trong ĐÚNG
            # cửa sổ giây đó (đường mẫu = trung vị các video mẫu), quy về mỗi phút; trung vị theo số thứ tự đoạn.
            theo: Dict[int, List[float]] = {}
            for v in ds:
                for i, (b, h) in enumerate(v["doan"][:8]):
                    x0, x1 = _giu_tai(v["r"], v["dai"], b), _giu_tai(v["r"], v["dai"], h)
                    y0, y1 = tv(giu[mau], b)[0], tv(giu[mau], h)[0]
                    if None not in (x0, x1, y0, y1) and h - b >= 20:
                        theo.setdefault(i + 1, []).append(((x0 - x1) - (y0 - y1)) / ((h - b) / 60.0))
            nang = max(((statistics.median(x), i, len(x)) for i, x in theo.items() if len(x) >= N_TOI_THIEU),
                       default=None)
            dong += " · mở đầu trung vị {0}s, còn {1}% lúc hết mở đầu (mẫu ở {0}s: {2}%){3}".format(
                _f(t_mo), _f(giu_mo), _f(mau_mo),
                " · đoạn lệch mẫu nặng nhất: đoạn {0} mất thêm {1} điểm/phút so mẫu cùng giây (n {2})".format(
                    nang[1], _f(nang[0], 1), nang[2]) if nang and nang[0] > 0 else "")
        else:
            dong += " · chưa đủ {0} video có mốc đoạn (hồ sơ phan.danh_sach)".format(N_TOI_THIEU)
        ra.append(dong)
    ra.append("  Bạn quyết: tối đa MỘT thay đổi kịch bản/tuần qua `thu --truc hook` (mở đầu ngắn hơn / vào ý chính "
              "sớm hơn) cho kênh lệch mẫu nhiều nhất; chấm sau ≥ 3 video, so cùng mốc giây.")
    return ra


# ═══ GỘP ═════════════════════════════════════════════════════════════════════

def chuong_trinh(goc: str, kenh_ds: Optional[Sequence[str]] = None,
                 bay_gio: Optional[_dt.datetime] = None, ghi: bool = True) -> List[str]:
    """Mọi dòng của mục chương trình trong `nao xem` (mỗi phần bọc try riêng). `ghi=False`: không ghi cả tệp nhớ
    lượt săn tuần (chạy thử trên dữ liệu thật)."""
    bay_gio = bay_gio or _dt.datetime.now()
    _GHI[0] = bool(ghi)
    if kenh_ds is None:
        try:
            from .kenh import liet_ke_kenh  # noqa: PLC0415

            kenh_ds = [k for k in liet_ke_kenh(goc) if not re.search(r"-v\d+$", k)]
        except Exception:  # noqa: BLE001
            kenh_ds = []
    kenh_ds = list(kenh_ds)
    ra = ["Luật chung: mỗi hành động ghi cỡ mẫu (n) + ngày kiểm trong --ly-do/--kiem-ngay; n < {0} thì nói rõ \"chưa "
          "chắc\" và KHÔNG hành động; \"giữ nguyên\" có lý do là quyết định tốt.".format(N_TOI_THIEU)]
    for ten, ham in (("(a) DANH MỤC KÊNH — chia khe/hạn mức (đụng nhịp đăng thì `de-xuat` cho chủ)",
                      lambda: dong_danh_muc(goc, kenh_ds, bay_gio)),
                     ("(b) RADAR NỔ — nhân bản video đang nổ sớm (vào sản xuất ≤ 48h)",
                      lambda: dong_radar(goc, kenh_ds, bay_gio) + dong_thang(goc, kenh_ds, bay_gio)),
                     ("(c) SĂN KHOẢNG TRỐNG CHỦ ĐỀ (mỗi tuần)", lambda: dong_khoang_trong(goc, bay_gio, ghi)),
                     ("(d) BAO BÌ A/B", lambda: dong_bao_bi(goc, kenh_ds, bay_gio)),
                     ("(e) GIỮ CHÂN THEO ĐOẠN so kênh mẫu", lambda: dong_giu_chan(goc, kenh_ds, bay_gio))):
        ra.append("")
        ra.append("-- " + ten + " --")
        try:
            ra.extend(ham())
        except Exception as loi:  # noqa: BLE001
            ra.append("  (lỗi tính phần này: {0}: {1})".format(type(loi).__name__, str(loi)[:120]))
    return ra


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    thu = "--thu" in (sys.argv[1:] if argv is None else argv)
    print("\n".join(["CHƯƠNG TRÌNH HÔM NAY (gốc: {0}{1})".format(GOC_MAC_DINH, ", chạy thử — không ghi" if thu else "")]
                    + chuong_trinh(GOC_MAC_DINH, ghi=not thu)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
