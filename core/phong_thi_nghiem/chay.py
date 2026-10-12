"""Chạy phòng thí nghiệm: HẰNG NGÀY (sau bước chấm V7 của nghiên cứu) và NGƯỢC lịch sử (gieo bảng xếp hạng).

Hằng ngày (`chay_ngay`): dựng thế giới hiện tại → vũ trụ → kho đặc trưng (ghi `kho-<hôm nay>.csv.gz`) → chấm MỌI
giả thuyết chưa bị loại → nhật ký bóng (lần đầu trong ngày thắng) → tính lại bảng xếp hạng khi bảng cũ hơn
`GIO_DANH_GIA_LAI` giờ. Tắt: kenh.yaml `phong_thi_nghiem: false` hoặc biến môi trường `MYTOOL_PHONG_THI_NGHIEM=0`.
`chay_ngay_an_toan` bọc mọi lỗi — phòng thí nghiệm KHÔNG BAO GIỜ chặn sản xuất.

Ngược (`chay_nguoc`): mỗi kênh, mỗi ngày X còn dựng được "hết ngày X" từ sao lưu (`nguon` đầu tệp), chấm mọi giả
thuyết (trừ H-AI) → nhật ký `che_do = "nguoc"` → bảng xếp hạng → báo cáo `workspace/chan-doan/
phong-thi-nghiem-backtest-<ngày>.md`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import gzip
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import _chung as c
from . import dac_trung, gia_thuyet, nhat_ky, nguon, vu_tru

GIO_DANH_GIA_LAI = 20.0
#: Ảnh chụp kho ~200–600 KB/kênh/ngày → giữ 120 ngày (~0,5 GB cho 8 kênh). Nhật ký bóng (nhỏ) giữ mãi.
GIU_NGAY = 120
NGAY_LICH_SU_VIEW = 8
_TAT = ("0", "false", "tat", "tắt", "no", "off")


def bat(goc: str, kenh: str) -> bool:
    """Phòng thí nghiệm bật cho kênh? Mặc định BẬT; kenh.yaml `phong_thi_nghiem: false` hoặc env tắt."""
    if str(os.environ.get("MYTOOL_PHONG_THI_NGHIEM", "")).strip().lower() in _TAT:
        return False
    gt = c.doc_yaml_kenh(goc, kenh).get("phong_thi_nghiem")
    if gt is None or gt == "":
        return True
    if isinstance(gt, bool):
        return gt
    return str(gt).strip().lower() not in _TAT


def _ghi_log(log: Optional[Callable[[str], None]], m: str) -> None:
    if log is not None:
        try:
            log(m)
        except Exception:  # noqa: BLE001
            pass


def lich_su_view(goc: str, kenh: str, ngay: str, so_ngay: int = NGAY_LICH_SU_VIEW) -> Dict[str, List[Tuple[float, float]]]:
    """`{mã: [(giờ quét, view)]}` từ ảnh chụp kho của `so_ngay` ngày TRƯỚC `ngay` (đà tăng ~3 ngày)."""
    ra: Dict[str, List[Tuple[float, float]]] = {}
    tu = c.cong_ngay(ngay, -so_ngay)
    for d in dac_trung.ngay_co_kho(goc, kenh):
        if not (tu <= d < ngay):
            continue
        try:
            with gzip.open(dac_trung.duong_kho(goc, kenh, d), "rt", encoding="utf-8", newline="") as tep:
                for r in csv.DictReader(tep):
                    t, v = c.so(r.get("luc")), c.so(r.get("view"))
                    if r.get("ma") and t is not None and v is not None:
                        ra.setdefault(r["ma"], []).append((t, v))
        except (OSError, ValueError, EOFError, csv.Error):
            continue
    return ra


def ghi_vu_tru(goc: str, kenh: str, ngay: str, vt: vu_tru.VuTru, che_do: str) -> str:
    """`vu-tru-<ngày>.json`: thống kê vũ trụ + kênh "theo dõi" mà luật đối thủ thật loại (để tra)."""
    loai = sorted(({"kenh": ten, "ly_do": o["ly_do"], "view_tv": o.get("view_tv"), "ngach": o.get("ngach"),
                    "cach_dang": o.get("cach_dang")}
                   for ten, o in vt.kenh.items() if not o["ok"] and o.get("trang_thai") == vu_tru.THEO_DOI),
                  key=lambda x: (x["ly_do"], x["kenh"]))
    return c.ghi_json(os.path.join(c.thu_muc_kenh(goc, kenh), "vu-tru-{0}.json".format(ngay)),
                      {"ngay": ngay, "luc": c.luc_iso(), "che_do": che_do, "thong_ke": vt.thong_ke,
                       "kenh_theo_doi_bi_loai": loai})


def don_cu(goc: str, kenh: str, giu_ngay: int = GIU_NGAY) -> int:
    """Xoá ảnh chụp kho / vũ trụ / AI / mẫu nền tầng 1 cũ hơn `giu_ngay` ngày của CHÍNH phòng thí nghiệm (nhật ký bóng
    giữ mãi)."""
    moc = c.cong_ngay(c.hom_nay(), -giu_ngay)
    so = 0
    try:
        ten = os.listdir(c.thu_muc_kenh(goc, kenh))
    except OSError:
        return 0
    for t in ten:
        for tien in ("kho-", "vu-tru-", "ai-", "nen-"):
            if t.startswith(tien):
                d = t[len(tien):len(tien) + 10]
                if len(d) == 10 and d < moc:
                    try:
                        os.remove(os.path.join(c.thu_muc_kenh(goc, kenh), t))
                        so += 1
                    except OSError:
                        pass
    return so


SO_GIU_TIEU_DE = 50
#: Sổ đối thủ quét lần cuối cũ hơn ngần này ngày trước mốc → dữ liệu đứng im (kênh sản xuất ở máy khác, sổ chép
#: về một lần) — không ghi nhật ký ngày ấy (không có gì mới để đo, chỉ tốn đĩa và làm nhiễu tầng 1).
NGAY_SO_CU = 4


def so_cu(tg: nguon.TheGioi) -> str:
    """Lý do bỏ ngày khi sổ đối thủ đứng im quá `NGAY_SO_CU` ngày trước mốc; "" = dùng được."""
    ds = list(nguon.luc_quet_kenh(tg.danh_ba).values()) + ([tg.luc_quet_sach] if tg.luc_quet_sach else [])
    if not ds:
        return ""
    cach = (tg.moc - max(ds)) / c.NGAY_GIAY
    return "sổ đối thủ quét lần cuối {0:.0f} ngày trước mốc".format(cach) if cach > NGAY_SO_CU else ""


def danh_dau_du(kho: Sequence[Dict[str, Any]], reg: Sequence[Dict[str, Any]]) -> None:
    """Đánh dấu `_du` cho dòng nằm trong top-`SO_GIU_TIEU_DE` của ít nhất một giả thuyết (ảnh chụp chỉ giữ tiêu đề
    của các dòng này)."""
    for gt in reg:
        if gt["loai"] == gia_thuyet.LOAI_LLM:
            continue
        top, _n = gia_thuyet.xep_hang(gt, kho, SO_GIU_TIEU_DE)
        for d, _x in top:
            d["_du"] = True


def cham_ngay(tg: nguon.TheGioi, kho: Sequence[Dict[str, Any]], reg: Sequence[Dict[str, Any]], k: int,
              da: Set[Tuple[str, int]], *, n_vu_tru: int, ket_ai: Optional[Dict[str, float]] = None,
              luc: Optional[float] = None) -> List[Dict[str, Any]]:
    """Dòng nhật ký bóng cho mọi giả thuyết chưa loại, chưa ghi (`da`). H-AI chỉ khi có `ket_ai`."""
    ra = []
    for gt in reg:
        if gt["trang_thai"] == gia_thuyet.LOAI or (gt["id"], gt["phien_ban"]) in da:
            continue
        if gt["loai"] == gia_thuyet.LOAI_LLM and not ket_ai:
            continue
        top, n_du = gia_thuyet.xep_hang(gt, kho, k, ket_ai=ket_ai)
        ghi = ""
        if gt["loai"] == gia_thuyet.LOAI_DUNG_SAN and n_du == 0:
            if "v7" in str(gt["tham_so"].get("cot")):
                ghi = "bảng V7 không có ứng viên trong vũ trụ ({0})".format(tg.v7_nguon or "không có bảng")
            else:
                ghi = "VPH không có ứng viên trong vũ trụ"
        ra.append(nhat_ky.dong(tg.ngay, tg.kenh, gt, top, n_du=n_du, n_vu_tru=n_vu_tru, k=k, che_do=tg.che_do,
                               luc=luc, ghi=ghi))
    return ra


def chay_ngay(goc: str, kenh: str, *, kq_v7: Any = None, dung_ai: bool = False,
              goi_ai: Optional[Callable[..., str]] = None, log: Optional[Callable[[str], None]] = None,
              ngay: Optional[str] = None, danh_gia_lai: bool = True,
              bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Một lượt hằng ngày cho một kênh (xem đầu tệp). Trả tóm tắt. CÓ THỂ ném lỗi — nơi gọi sản xuất dùng
    `chay_ngay_an_toan`. `bay_gio` (epoch) chỉ để bài kiểm cố định mốc."""
    t0 = time.time()
    ngay = ngay or c.hom_nay()
    if not bat(goc, kenh):
        return {"kenh": kenh, "bo_qua": "tắt (kenh.yaml phong_thi_nghiem / MYTOOL_PHONG_THI_NGHIEM)"}
    reg, k = gia_thuyet.nap(goc)
    da = nhat_ky.da_co(goc, kenh, ngay)
    # H-AI chỉ "còn thiếu" khi lượt này được gọi AI — không thì lượt nghiên cứu thứ hai trong ngày cũng không dựng lại.
    can = [g for g in reg if g["trang_thai"] != gia_thuyet.LOAI and (g["id"], g["phien_ban"]) not in da
           and (g["loai"] != gia_thuyet.LOAI_LLM or dung_ai)]
    if not can:
        return {"kenh": kenh, "bo_qua": "đã ghi đủ nhật ký hôm nay"}
    nk = nguon.NguonKenh(goc, kenh)
    if kq_v7 is not None:
        v7, v7_nguon = nguon.v7_tu_ket_qua(kq_v7), "that"
    else:
        v7, d = nguon.bang_v7_ngay(goc, kenh, ngay)
        v7_nguon = ("bang:" + d) if d else ""
    vph = nguon.vph_hien_tai(goc, kenh)
    tg = nguon.dung_the_gioi(nk, ngay, che_do="that", moc=bay_gio or time.time(), v7=v7, v7_nguon=v7_nguon, vph=vph,
                             lich_su_view=lich_su_view(goc, kenh, ngay))
    cu = so_cu(tg)
    if cu:
        return {"kenh": kenh, "bo_qua": cu}
    vt = vu_tru.dung(tg)
    kho = dac_trung.dung_kho(tg, vt)
    if not da:
        danh_dau_du(kho, reg)
        dac_trung.ghi_kho(goc, kenh, ngay, kho)
        ghi_vu_tru(goc, kenh, ngay, vt, "that")
    ket_ai = None
    gt_ai = next((g for g in can if g["loai"] == gia_thuyet.LOAI_LLM), None)
    dong_moi = cham_ngay(tg, kho, can, k, set(), n_vu_tru=len(kho))
    if gt_ai is not None and dung_ai and kho:
        from . import ai  # noqa: PLC0415

        top_khac = {x["gt"]: [i["ma"] for i in x["top"]] for x in dong_moi}
        ket_ai = ai.chay(goc, kenh, ngay, kho, gt_ai, top_khac, tg.video_minh, goi=goi_ai, log=log) or None
        if ket_ai:
            dong_moi += cham_ngay(tg, kho, [gt_ai], k, set(), n_vu_tru=len(kho), ket_ai=ket_ai)
    so = nhat_ky.ghi(goc, dong_moi)
    don_cu(goc, kenh)
    tom = {"kenh": kenh, "ngay": ngay, "n_vu_tru": len(kho), "ghi": so,
           "gia_thuyet": {x["gt"]: x["n_du"] for x in dong_moi}, "giay": round(time.time() - t0, 1),
           "thong_ke": vt.thong_ke}
    _ghi_log(log, "  phòng thí nghiệm: vũ trụ {0} ứng viên (sổ {1}, kênh đối thủ thật {2}/{3}) · ghi {4} giả thuyết "
                  "({5}) · {6:.0f} giây".format(len(kho), vt.thong_ke.get("n_sach"), vt.thong_ke.get("kenh_dat"),
                                               vt.thong_ke.get("kenh_so"), so,
                                               ", ".join("{0} {1}".format(g, n) for g, n in tom["gia_thuyet"].items()),
                                               tom["giay"]))
    if danh_gia_lai:
        try:
            from . import danh_gia  # noqa: PLC0415

            cu = danh_gia.doc_bang(goc).get("luc")
            tuoi = (time.time() - time.mktime(_dt.datetime.strptime(cu, "%Y-%m-%dT%H:%M:%S").timetuple())) / 3600.0 \
                if cu else 1e9
            if tuoi >= GIO_DANH_GIA_LAI:
                danh_gia.chay(goc, log=log)
                tom["danh_gia"] = True
        except Exception as loi:  # noqa: BLE001
            _ghi_log(log, "  phòng thí nghiệm: tính bảng xếp hạng hỏng, để lượt sau: {0}".format(str(loi)[:120]))
    return tom


def chay_ngay_an_toan(goc: str, kenh: str, **kw: Any) -> Dict[str, Any]:
    """`chay_ngay` không bao giờ ném lỗi (nơi gọi là bước nghiên cứu của sản xuất)."""
    log = kw.get("log")
    try:
        return chay_ngay(goc, kenh, **kw)
    except Exception as loi:  # noqa: BLE001
        _ghi_log(log, "  phòng thí nghiệm hỏng, bỏ qua (sản xuất không bị ảnh hưởng): {0}: {1}".format(
            type(loi).__name__, str(loi)[:160]))
        try:
            from .. import tu_hoc  # noqa: PLC0415

            tu_hoc.canh_bao(goc, "phong_thi_nghiem", loi, kenh)
        except Exception:  # noqa: BLE001
            pass
        return {"kenh": kenh, "loi": "{0}: {1}".format(type(loi).__name__, str(loi)[:200])}


# ── chạy ngược ──────────────────────────────────────────────────────────────

def ngay_nguoc(goc: str, kenh: str, tu: str, den: str) -> List[str]:
    """Các ngày X ∈ [tu, den] dựng được "hết ngày X" của kênh: từ (bản sao lưu sớm nhất − 1); không có sao lưu → chỉ
    ngày ghi cuối của sổ hiện tại."""
    bs = nguon.ban_sao_luu(goc, kenh, "content")
    if bs:
        dau = c.cong_ngay(bs[0][0], -1)
    else:
        ds = nguon.ngay_co_so_lieu(goc, kenh)
        if not ds:
            return []
        dau = ds[-1]
    dau = max(dau, tu) if tu else dau
    ra = []
    d = dau
    while d and d <= den:
        ra.append(d)
        d = c.cong_ngay(d, 1)
    return ra


def _tu_mac_dinh(goc: str, kenh_ds: Sequence[str]) -> str:
    ds = []
    for k in kenh_ds:
        try:
            ten = os.listdir(os.path.join(goc, "CHANNEL", k, "tu-chay"))
        except OSError:
            continue
        ds += [p[:10] for p in ten if p.endswith(".json") and len(p) == 15]
    return c.cong_ngay(min(ds), -2) if ds else c.cong_ngay(c.hom_nay(), -30)


def chay_nguoc(goc: str, kenh_ds: Optional[Sequence[str]] = None, *, tu: str = "", den: str = "",
               log: Optional[Callable[[str], None]] = None, bao_cao: bool = True,
               ghi_de_kho: bool = False) -> Dict[str, Any]:
    """Chạy ngược lịch sử (xem đầu tệp). Trả `{kenh: {ngay: số dòng}, bang, bao_cao}`."""
    from . import danh_gia  # noqa: PLC0415

    kenh_ds = list(kenh_ds or danh_gia.kenh_phong_thi_nghiem(goc))
    den = den or c.cong_ngay(c.hom_nay(), -1)
    tu = tu or _tu_mac_dinh(goc, kenh_ds)
    reg, k = gia_thuyet.nap(goc)
    vung = nguon.doc_vung(goc)
    ls_tt = nguon.lich_su_thi_truong(goc)
    ra: Dict[str, Any] = {"kenh": {}, "thong_ke": {}}
    for kenh in kenh_ds:
        nk = nguon.NguonKenh(goc, kenh)
        ra["kenh"][kenh] = {}
        for ngay in ngay_nguoc(goc, kenh, tu, den):
            t0 = time.time()
            da = nhat_ky.da_co(goc, kenh, ngay)
            can = [g for g in reg if g["trang_thai"] != gia_thuyet.LOAI and g["loai"] != gia_thuyet.LOAI_LLM
                   and (g["id"], g["phien_ban"]) not in da]
            if not can and not ghi_de_kho:
                continue
            try:
                tg = nguon.dung_the_gioi(nk, ngay, che_do="nguoc", vung=vung, lich_su=ls_tt,
                                         lich_su_view=lich_su_view(goc, kenh, ngay))
                cu = so_cu(tg)
                if cu:
                    _ghi_log(log, "{0} {1}: bỏ — {2}".format(kenh, ngay, cu))
                    continue
                vt = vu_tru.dung(tg)
                kho = dac_trung.dung_kho(tg, vt)
            except Exception as loi:  # noqa: BLE001
                _ghi_log(log, "{0} {1}: hỏng {2}: {3}".format(kenh, ngay, type(loi).__name__, str(loi)[:160]))
                continue
            if ghi_de_kho or not os.path.isfile(dac_trung.duong_kho(goc, kenh, ngay)):
                danh_dau_du(kho, reg)
                dac_trung.ghi_kho(goc, kenh, ngay, kho)
                ghi_vu_tru(goc, kenh, ngay, vt, "nguoc")
            dong_moi = cham_ngay(tg, kho, can, k, set(), n_vu_tru=len(kho), luc=tg.moc)
            so = nhat_ky.ghi(goc, dong_moi)
            ra["kenh"][kenh][ngay] = so
            ra["thong_ke"].setdefault(kenh, {})[ngay] = vt.thong_ke
            _ghi_log(log, "{0} {1}: vũ trụ {2} (sổ {3}, kênh thật {4}/{5}), V7 {6}, ghi {7} · {8:.1f}s".format(
                kenh, ngay, len(kho), vt.thong_ke.get("n_sach"), vt.thong_ke.get("kenh_dat"),
                vt.thong_ke.get("kenh_so"), tg.v7_nguon or "—", so, time.time() - t0))
    bang = danh_gia.chay(goc, kenh_ds=kenh_ds, log=log, so_sanh_cu=bao_cao)
    ra["bang"] = bang
    if bao_cao:
        from . import bao_cao as bc  # noqa: PLC0415

        ra["bao_cao"] = bc.ghi(goc, bang, kenh_ds=kenh_ds, tu=tu, den=den)
    return ra
