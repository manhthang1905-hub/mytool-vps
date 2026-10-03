"""Giám đốc kênh — tầng tự quyết sau khi đăng: đọc số → quyết → áp có giới hạn → đo → giữ / bỏ / mở rộng.

Thiết kế: `workspace/THIET-KE-GIAM-DOC.md`; kiến thức: `docs/kien-thuc/giam-doc.md`.

Mỗi tệp `core/giam_doc/<ten>.py` KHÔNG bắt đầu bằng `_` và không thuộc `_KHONG_PHAI_VIEC` là MỘT việc
(plugin: `TEN`, `MO_TA`, `NHIP`, `CHI_SO_CHINH`, `ap_dung`, `quan_sat`, `de_xuat`, `ket_luan`), tự phát hiện
bằng `pkgutil.iter_modules` (khuôn sổ đăng ký của `core/chien_luoc`). Thêm việc: chép `_mau.py`.

    so_dang_ky()                                         {TEN: module}
    chay_kenh(goc, ma, *, che_do, goi_chat, tuan)        một lượt của một kênh → KetQua
    nhip(goc, *, thu, bay_gio)                           gác tổng gọi: có việc thì sinh tiến trình tách rời
    kiem_ket(goc, *, bay_gio, ghi)                       gác tổng: kênh đến hạn ≥ 6 giờ chưa chạy (`giam_doc_ket`)
    viec_cua_ban_kenh(goc, ma)                           "Việc của bạn" của báo cáo cuối (bảng điều khiển, gác tổng)
    phan_loai_viec · ghi_viec_may                        nguoi / cho_so / may — chỉ "nguoi" mới báo chủ (`_tu_dong`)
    tu_nang_ha_quyen(goc)                                hằng ngày: goi_y ⇄ tu_ap theo `do-chinh-xac.json`
    kham_nghiem.chay · tong.hop_tuan                     khám nghiệm video (trong chay_kenh) · tổng giám đốc (thứ Hai)
    doc_chi_dao(goc, ma)                                 chỉ đạo còn hạn (biên tập viên đọc)

Khoá kenh.yaml: `giam_doc: tat | goi_y | tu_ap` (mặc định `tat`), `giam_doc_studio: false`,
`giam_doc_khong_dung: "phut_muc_tieu, …"`, `giam_doc_cho_phep_ab: false`.
"""

from __future__ import annotations

import datetime as _dt
import importlib
import io
import json
import logging
import os
import pkgutil
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional

from . import gioi_han, so_thi_nghiem as stn
from .du_lieu import BangSo, tom_tat
from .gioi_han import doc_chi_dao  # noqa: F401 — cửa công khai cho biên tập viên (Agent B)
from ._tu_dong import (  # noqa: F401 — tự động hoá "Việc của bạn" + quyền theo thành tích (04/10/2026)
    doc_viec_cho_nao, ghi_viec_may, la_viec_suc_khoe, phan_loai_viec, tu_nang_ha_quyen)

_log = logging.getLogger(__name__)

_KHONG_PHAI_VIEC = {"du_lieu", "so_thi_nghiem", "gioi_han", "quan_ly", "bao_cao", "kham_nghiem", "tong", "hoi_dong",
                    "__main__"}
_THU_TU_GOC = ("suc_khoe", "cuu_ctr", "dan_cum", "muc_tieu_ypp", "do_dai")
THU_MUC_KHOA = os.path.join("workspace", "giam-doc")
KHOA_QUA_HAN_GIAY = 3 * 3600
_SO: Optional[Dict[str, ModuleType]] = None


def so_dang_ky(tai_lai: bool = False) -> Dict[str, ModuleType]:
    """`{TEN: module}` của mọi việc nạp được (nhớ sau lần đầu). Tệp hỏng → log + bỏ qua."""
    global _SO
    if _SO is not None and not tai_lai:
        return _SO
    tim: Dict[str, ModuleType] = {}
    for mi in pkgutil.iter_modules(__path__):
        if mi.name.startswith("_") or mi.name in _KHONG_PHAI_VIEC:
            continue
        try:
            m = importlib.import_module("{0}.{1}".format(__name__, mi.name))
        except Exception as loi:  # noqa: BLE001 — một việc hỏng không kéo đổ giám đốc
            _log.warning("giam_doc: bỏ qua việc %s (nhập hỏng: %s)", mi.name, loi)
            continue
        if not getattr(m, "TEN", "") or not all(callable(getattr(m, f, None))
                                               for f in ("ap_dung", "quan_sat", "de_xuat", "ket_luan")):
            _log.warning("giam_doc: %s thiếu TEN/ap_dung/quan_sat/de_xuat/ket_luan — bỏ qua", mi.name)
            continue
        tim[m.TEN] = m
    thu_tu = [t for t in _THU_TU_GOC if t in tim] + sorted(t for t in tim if t not in _THU_TU_GOC)
    _SO = {t: tim[t] for t in thu_tu}
    return _SO


def chay_viec(bs: BangSo, nhip: Optional[str] = None) -> List[Dict[str, Any]]:
    """Chạy từng việc (lọc theo `nhip`; None = mọi việc): ap_dung → quan_sat → de_xuat. Không ném lỗi."""
    ra = []
    for ten, m in so_dang_ky().items():
        if nhip and getattr(m, "NHIP", "tuan") != nhip:
            continue
        o = {"ten": ten, "nhip": getattr(m, "NHIP", "tuan"), "ap_dung": 0.0, "quan_sat": [], "de_xuat": [], "loi": ""}
        try:
            o["ap_dung"] = max(0.0, min(1.0, float(m.ap_dung(bs) or 0)))
            if o["ap_dung"] > 0:
                o["quan_sat"] = list(m.quan_sat(bs) or [])
                o["de_xuat"] = [dict(d, plugin=ten) for d in m.de_xuat(bs, o["quan_sat"]) or []]
        except Exception as loi:  # noqa: BLE001 — một việc hỏng không kéo đổ lượt
            o["loi"] = "{0}: {1}".format(type(loi).__name__, str(loi)[:160])
        ra.append(o)
    return ra


@dataclass
class KetQua:
    """Một lượt của một kênh — đủ để in (`bao_cao.in_ket_qua`) và ghi báo cáo."""
    bs: BangSo
    che_do: str
    tuan: bool = False
    viec: List[Dict[str, Any]] = field(default_factory=list)
    thuc_don: List[Dict[str, Any]] = field(default_factory=list)
    thi_nghiem: List[Dict[str, Any]] = field(default_factory=list)
    bao_dong: bool = False
    quyet_dinh: Any = None
    viec_cua_ban: List[str] = field(default_factory=list)
    da_lam: List[Dict[str, Any]] = field(default_factory=list)
    se_lam: List[Dict[str, Any]] = field(default_factory=list)   # chế độ gợi ý: việc ĐÃ CHỌN mà không áp
    tu_cham: Dict[str, Any] = field(default_factory=dict)        # {tong, dung, moi, cho} dự đoán thắng/trượt
    kham: List[Dict[str, Any]] = field(default_factory=list)     # khám nghiệm video của lượt (`kham_nghiem.chay`)
    cuu_ctr: List[Dict[str, Any]] = field(default_factory=list)  # đề xuất đổi tiêu đề của hội đồng (`cuu_ctr.xu_ly`)


def _thuc_don(bs: BangSo, viec: List[Dict[str, Any]], so_: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gắn id d1…, giá trị cũ, kết quả `gioi_han.kiem` cho mọi đề xuất."""
    ra = []
    for v in viec:
        for d in v["de_xuat"]:
            d = dict(d, id="d{0}".format(len(ra) + 1))
            if d["loai"] == "tham_so":
                d["gia_tri_cu"] = gioi_han.gia_tri_hien_tai(bs, str(d.get("khoa")))
            d["duoc"], d["ly_do_kiem"] = gioi_han.kiem(d, so_, bs)
            ra.append(d)
    return ra


def _gom_goi_y(bs: BangSo) -> Dict[str, Any]:
    """Nhớ `ti_trong_goi_y` của mỗi lần ghi `chien-luoc.json` (điều kiện ổn định để bật tự học)."""
    tep = bs.chien_luoc_tep or {}
    luc, gy = tep.get("cap_nhat_luc"), tep.get("ti_trong_goi_y")
    if not luc or not gy or luc == bs.trang_thai.get("goi_y_luc"):
        return {}
    return {"goi_y_luc": luc, "goi_y_ti_trong": gy, "goi_y_ti_trong_truoc": bs.trang_thai.get("goi_y_ti_trong") or {}}


def chay_kenh(goc: str, ma: str, *, che_do: Optional[str] = None, goi_chat: Optional[Callable[..., str]] = None,
              tuan: bool = False, bay_gio: Optional[_dt.datetime] = None,
              ghi: Optional[Callable[[str], None]] = None) -> KetQua:
    """Một lượt của kênh `ma`.

    `che_do="thu"`: chỉ tính và (nếu có `goi_chat`) hỏi LLM — KHÔNG ghi gì. Không truyền thì đọc
    `giam_doc` của kenh.yaml: `tat` → không làm gì; `goi_y` → ghi sổ + báo cáo (chế độ bóng, không đổi
    kenh.yaml); `tu_ap` → áp các lựa chọn qua `gioi_han`. `tuan=True` chạy mọi việc (không chỉ việc ngày)."""
    from . import bao_cao, quan_ly, suc_khoe  # noqa: PLC0415

    bs = tom_tat(goc, ma, bay_gio=bay_gio)
    cd = che_do or gioi_han.che_do(bs)
    kq = KetQua(bs=bs, che_do=cd, tuan=tuan)
    if cd == "tat":
        return kq
    viet = cd != "thu"
    if viet:
        sua = gioi_han.chu_da_sua(goc, ma, bs)
        kq.da_lam += [{"viec": "chu_sua", "khoa": k} for k in sua]
    so_ = stn.doc_so(goc, ma)
    kq.viec = chay_viec(bs, None if (tuan or cd == "thu") else "ngay")
    qs_sk = next((v["quan_sat"] for v in kq.viec if v["ten"] == suc_khoe.TEN), [])
    kq.bao_dong = suc_khoe.bao_dong(qs_sk)
    kq.viec_cua_ban += [q["viec_cua_ban"] for q in qs_sk if q.get("viec_cua_ban")]
    kq.thuc_don = _thuc_don(bs, kq.viec, so_)
    kq.viec_cua_ban += ["Gợi ý (chỉ chủ đổi được): " + d["gia_thuyet"] for d in kq.thuc_don
                        if not d["duoc"] and "ngoài tầm" in str(d["ly_do_kiem"])]

    # thí nghiệm đang mở: kết luận số của việc + cò quay lui (luật cứng, không cần LLM)
    so_viec = so_dang_ky()
    for tn in stn.dang_mo(so_):
        m = so_viec.get(str(tn.get("viec")))
        try:
            kl = m.ket_luan(bs, tn) if m else None
        except Exception:  # noqa: BLE001
            kl = None
        tn = dict(tn, _ket_luan_so=kl or {}, _quay_lui=gioi_han.ly_do_quay_lui(
            bs, tn, bao_dong=kq.bao_dong, ket_luan=kl))
        kq.thi_nghiem.append(tn)
    if viet:
        for tn in kq.thi_nghiem:
            if tn["_quay_lui"]:
                kq.da_lam.append(gioi_han.quay_lui(goc, ma, tn, ly_do=tn["_quay_lui"], bay_gio=bs.bay_gio))
            elif tn in stn.het_han(kq.thi_nghiem, bs.bay_gio) and (tn["_ket_luan_so"] or {}).get("ket", "chua_du") == "chua_du":
                if stn.xu_ly_het_han(goc, ma, tn, bay_gio=bs.bay_gio) == "chua_du":
                    kq.da_lam.append(gioi_han.quay_lui(goc, ma, tn, ly_do="hết hạn, chưa đủ mẫu",
                                                       trang_thai="chua_du", bay_gio=bs.bay_gio))
        con_mo = {t["id"] for t in stn.dang_mo(stn.doc(goc, ma))}
        kq.thi_nghiem = [t for t in kq.thi_nghiem if t["id"] in con_mo]

    from . import cuu_ctr  # noqa: PLC0415

    studio = cuu_ctr.bat_studio(bs)
    if not kq.bao_dong and goi_chat is not None:
        qs = {v["ten"]: v["quan_sat"] for v in kq.viec if v["quan_sat"]}
        # `giam_doc_studio: true`: việc Studio đi HỘI ĐỒNG RIÊNG (`cuu_ctr.xu_ly`), không qua thực đơn chung
        kq.quyet_dinh = quan_ly.nghi(bs, qs, [d for d in kq.thuc_don if d["duoc"] and not (
            studio and d["loai"] == "viec_studio")], kq.thi_nghiem,
            gioi_han.ngan_sach(so_, bs.bay_gio), goi_chat, tuan=tuan, ghi=ghi, luu=viet)
        if studio:
            try:
                kq.cuu_ctr = cuu_ctr.xu_ly(goc, ma, bs, kq.thuc_don, goi_chat, viet=viet, ghi=ghi)
            except Exception as loi:  # noqa: BLE001 — cứu CTR hỏng không chặn lượt giám đốc
                _log.warning("giam_doc: cứu CTR %s hỏng: %s", ma, loi)
            if viet:
                kq.da_lam += [{"viec": "cuu_ctr", "video_id": m["video_id"], "trang_thai": m["trang_thai"],
                               "cu": m["tieu_de_cu"], "moi": m["tieu_de_moi"], "do_tin": m.get("do_tin")}
                              for m in kq.cuu_ctr]
    if not viet:
        return kq

    qd = kq.quyet_dinh
    # TỰ CHẤM (mọi chế độ có ghi): dự đoán thắng/trượt cũ nào mà video nay đã có kết luận
    kq.tu_cham = stn.cham_du_doan(goc, ma, {v["id"]: v.get("ket_luan") or "" for v in bs.video}, bay_gio=bs.bay_gio)
    if qd is not None and not qd.loi and qd.du_doan:
        kq.tu_cham["moi_doan"] = stn.ghi_du_doan(goc, ma, qd.du_doan, bay_gio=bs.bay_gio)
    if goi_chat is not None and not kq.bao_dong:  # KHÁM NGHIỆM video qua mốc 48h / 7 ngày (≤ 4 video/lượt)
        from . import kham_nghiem  # noqa: PLC0415

        try:
            kq.kham = kham_nghiem.chay(goc, ma, bs, goi_chat, ghi=ghi, lay_binh_luan=kham_nghiem.binh_luan_that
                                       if getattr(goi_chat, "that", False) else None)
        except Exception as loi:  # noqa: BLE001 — khám hỏng không chặn lượt giám đốc
            _log.warning("giam_doc: khám nghiệm %s hỏng: %s", ma, loi)
    if qd is not None and not qd.loi:
        for k in qd.ket_luan if cd == "tu_ap" else []:
            tn = next((t for t in kq.thi_nghiem if t["id"] == k["id"]), None)
            if tn is None or k["ket"] == "chua_du":
                continue
            if k["ket"] == "bo":
                kq.da_lam.append(gioi_han.quay_lui(goc, ma, tn, ly_do=k["ly_do"], trang_thai="bo", bay_gio=bs.bay_gio))
            else:
                stn.dong(goc, ma, tn["id"], k["ket"], tn.get("_ket_luan_so"), ly_do=k["ly_do"], bay_gio=bs.bay_gio)
                kq.da_lam.append({"viec": "ket_luan", "id": tn["id"], "ket": k["ket"]})
        from . import hoi_dong  # noqa: PLC0415

        for d in qd.chon:
            if d["loai"] == "viec_studio":
                kq.viec_cua_ban.append("Đổi tiêu đề video {0} “{1}” thành “{2}” ({3}).".format(
                    d["video_id"], (d.get("tieu_de_cu") or "")[:40], d.get("noi_dung"), d.get("ly_do_llm")))
                continue
            # quyền tự áp theo thành tích (`hoi_dong.do_chinh_xac`): đổi chiến lược lớn → chủ duyệt; đổi chuẩn
            # chỉ tự áp khi loại "doi_chuan" đã ≥ 70% đúng trên n ≥ 10 — chưa thì như gợi ý
            lon = hoi_dong.la_quyet_lon(d)
            if cd == "tu_ap" and lon:
                kq.viec_cua_ban.append("Quyết định lớn chờ bạn duyệt: {0} “{1}” → “{2}” ({3}).".format(
                    d.get("khoa"), _gon_chu(d.get("gia_tri_cu"), 80), _gon_chu(d.get("gia_tri"), 80),
                    _gon_chu(d.get("ly_do_llm"), 160)))
            if cd != "tu_ap" or lon or (d["loai"] == "tham_so" and hoi_dong.quyen(goc, ma, "doi_chuan") != "tu_ap"):
                stn.ghi_nhat_ky(goc, ma, viec="goi_y", sau=d.get("gia_tri") or d.get("noi_dung"), khoa=d.get("khoa"),
                                ly_do_llm=d.get("ly_do_llm"), bay_gio=bs.bay_gio)
                kq.se_lam.append({"id": d.get("id"), "loai": d.get("loai"), "khoa": d.get("khoa"),
                                  "cu": d.get("gia_tri_cu"), "moi": d.get("gia_tri") or d.get("noi_dung"),
                                  "gia_thuyet": d.get("gia_thuyet"), "ly_do_llm": d.get("ly_do_llm")})
                continue
            duoc, ly = gioi_han.kiem(d, stn.doc_so(goc, ma), bs)  # soát lại với sổ mới nhất
            kq.da_lam.append(gioi_han.ap(goc, ma, d, bs, ly_do_llm=d.get("ly_do_llm", ""), bay_gio=bs.bay_gio)
                             if duoc else {"ket": "tu_choi", "id": d["id"], "ly_do": ly})
    # một dòng nhật ký MỖI lượt (kể cả lượt không chọn gì) — để biết giám đốc có chạy và nghĩ gì
    stn.ghi_nhat_ky(goc, ma, viec="luot", sau={"che_do": cd, "tuan": tuan, "thuc_don": len(kq.thuc_don),
                                                "chon": len(qd.chon) if qd is not None and not qd.loi else 0,
                                                "du_doan_moi": int(kq.tu_cham.get("moi_doan") or 0),
                                                "kham": sum(1 for x in kq.kham if x.get("ket")),
                                                "bao_dong": kq.bao_dong, "mo_hinh": qd.mo_hinh if qd is not None else ""},
                    ly_do_llm=(qd.chan_doan if qd is not None and not qd.loi else (qd.loi if qd is not None else
                               "không gọi AI (van ví chặn / chế độ thử)"))[:400], bay_gio=bs.bay_gio)
    stn.ghi_trang_thai(goc, ma, ngay_chay=bs.bay_gio.date().isoformat(), luc_chay=bs.bay_gio.isoformat(timespec="seconds"),
                       bao_dong=kq.bao_dong, loi_llm=(qd.loi if qd is not None else ""),
                       **({"ngay_tuan": bs.bay_gio.date().isoformat()} if tuan else {}), **_gom_goi_y(bs))
    bao_cao.ghi_tuan(goc, ma, kq)
    try:  # sổ độ chính xác (đọc dự đoán + kết quả có sẵn) — bảng điều khiển đọc tệp này
        from . import hoi_dong  # noqa: PLC0415

        hoi_dong.do_chinh_xac(goc, ma)
    except Exception as loi:  # noqa: BLE001
        _log.warning("giam_doc: sổ độ chính xác %s hỏng: %s", ma, loi)
    return kq


def _gon_chu(x: Any, n: int) -> str:
    s = " ".join(str(x if x is not None else "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ── nhịp (gác tổng gọi) ────────────────────────────────────────────────────

def _kenh_bat(goc: str) -> List[str]:
    """Mã các kênh có `giam_doc` khác `tat`."""
    from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    ra = []
    try:
        ten = sorted(os.listdir(duong_kenh(goc)))
    except OSError:
        return ra
    for ma in ten:
        if ma.startswith("_"):
            continue
        cai = doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}
        if str(cai.get("giam_doc") or "tat").strip().lower() in ("goi_y", "tu_ap"):
            ra.append(ma)
    return ra


def viec_den_han(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """[{ma, tuan}] kênh chưa chạy hôm nay (thứ Hai chưa chạy tuần → tuan=True); bỏ kênh sắp tới phiên."""
    from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    hom_nay = bay_gio.date().isoformat()
    ra = []
    for ma in _kenh_bat(goc):
        tt = stn.doc_trang_thai(goc, ma)
        tuan = bay_gio.weekday() == 0 and tt.get("ngay_tuan") != hom_nay
        if tt.get("ngay_chay") == hom_nay and not tuan:
            continue
        bs = BangSo(goc=goc, ma_kenh=ma, bay_gio=bay_gio,
                    cai=dict(doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}))
        if gioi_han.gan_phien(bs, bay_gio):
            continue
        ra.append({"ma": ma, "tuan": tuan})
    return ra


def _duong_khoa(goc: str) -> str:
    return os.path.join(goc, THU_MUC_KHOA, ".khoa")


def dang_giu_khoa(goc: str) -> Dict[str, Any]:
    """{pid, bat_dau} của lượt đang chạy; {} nếu không có / khoá quá 3 giờ / tiến trình chết."""
    try:
        with io.open(_duong_khoa(goc), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {}
    if not isinstance(du, dict) or time.time() - float(du.get("bat_dau") or 0) > KHOA_QUA_HAN_GIAY:
        return {}
    try:
        from ..tien_trinh_con import con_song  # noqa: PLC0415

        return du if du.get("pid") == os.getpid() or con_song(int(du.get("pid") or 0)) else {}
    except Exception:  # noqa: BLE001
        return du


def _sinh(goc: str) -> int:
    """`python -m core.giam_doc --chay` tách rời (cùng cách `cap_nhat_git.sinh_tien_trinh`)."""
    import subprocess  # noqa: PLC0415

    from ..cap_nhat_git import _TRUNG_GIAN, _python_nen  # noqa: PLC0415

    os.makedirs(os.path.join(goc, THU_MUC_KHOA), exist_ok=True)
    co = 0
    for ten in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP"):
        co |= getattr(subprocess, ten, 0)
    try:
        from ..tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        CO_TACH_KHOI_JOB = 0  # noqa: N806
    lenh = [_python_nen(), "-X", "utf8", "-m", "core.giam_doc", "--chay"]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for co_thu in (co | CO_TACH_KHOI_JOB, co):
        a = json.dumps({"lenh": lenh, "cwd": goc, "co": co_thu,
                        "log": os.path.join(goc, THU_MUC_KHOA, "tien-trinh.log")})
        try:
            return subprocess.Popen([_python_nen(), "-c", _TRUNG_GIAN, a], cwd=goc, creationflags=co_thu,  # noqa: S603
                                    close_fds=True, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
        except OSError:
            continue
    return 0


def nhip(goc: str, *, thu: bool = False, bay_gio: Optional[_dt.datetime] = None,
         sinh: Optional[Callable[[str], int]] = None) -> Dict[str, Any]:
    """Gác tổng gọi mỗi nhịp: chỉ QUYẾT có việc hay không; có thì sinh tiến trình tách rời (không chạy
    trong tiến trình gác tổng). `thu=True`: chỉ trả danh sách, không sinh.

    Mỗi nhịp (trừ thử) còn hai việc nhẹ, 0 đồng: `cuu_ctr.dong_bo` (hàng sửa Studio ↔ sổ duyệt ↔ đo trước/
    sau) và `lam_moi_gio_online` (giải mã giờ khán giả online từ lượt quét kênh mới)."""
    if not thu:
        from . import cuu_ctr  # noqa: PLC0415

        for ten, f in (("cứu CTR", lambda: cuu_ctr.dong_bo(goc)), ("giờ online", lambda: lam_moi_gio_online(goc))):
            try:
                f()
            except Exception as loi:  # noqa: BLE001 — việc phụ của nhịp, hỏng không chặn giám đốc
                _log.warning("giam_doc.nhip: %s hỏng: %s", ten, loi)
    viec = viec_den_han(goc, bay_gio)
    if not viec:
        from . import tong  # noqa: PLC0415

        if not tong.den_han(goc, bay_gio):
            return {"viec": [], "pid": 0, "ly_do": "không kênh nào đến hạn"}
    if dang_giu_khoa(goc):
        return {"viec": viec, "pid": 0, "ly_do": "đang có lượt giám đốc chạy"}
    if thu:
        return {"viec": viec, "pid": 0, "ly_do": "chế độ thử — không sinh tiến trình"}
    pid = (sinh or _sinh)(goc)
    return {"viec": viec, "pid": pid, "ly_do": "đã sinh tiến trình {0}".format(pid) if pid else "không sinh được"}


TEP_GIO_ONLINE_DA_QUET = "gio-online-da-quet.json"


def lam_moi_gio_online(goc: str) -> Dict[str, Any]:
    """Giải mã giờ khán giả online (`audienceOnlineCardData`, tiện ích chụp ở tab-build_audience của lượt
    quét kênh — `chi-so/kenh/kenh-<ngày>/raw/`) → `chi-so/gio-online.json` qua `giai_ma.cap_nhat_gio_online`.
    Chỉ đọc lại khi có thư mục quét kênh mới (dấu ở `workspace/giam-doc/gio-online-da-quet.json`). Kênh mới
    (Studio trả mảng toàn số 0) thì chưa có tệp — đúng, không đoán. Trả {mã kênh: "ghi" | "chưa có số"}."""
    import glob  # noqa: PLC0415

    from ..chi_so_ytb import giai_ma  # noqa: PLC0415
    from ..kenh import duong_kenh  # noqa: PLC0415

    duong_dau = os.path.join(goc, THU_MUC_KHOA, TEP_GIO_ONLINE_DA_QUET)
    try:
        with io.open(duong_dau, encoding="utf-8") as tep:
            dau = json.load(tep)
        dau = dau if isinstance(dau, dict) else {}
    except (OSError, ValueError):
        dau = {}
    ra: Dict[str, Any] = {}
    try:
        ten = sorted(os.listdir(duong_kenh(goc)))
    except OSError:
        return ra
    moi = dict(dau)
    for ma in ten:
        kenh_dir = os.path.join(duong_kenh(goc, ma), "chi-so")
        raws = sorted(glob.glob(os.path.join(kenh_dir, "kenh", "kenh-*", "raw")), reverse=True)[:5]
        if ma.startswith("_") or not raws:
            continue
        try:
            nhan = "{0}|{1:.0f}".format(os.path.basename(os.path.dirname(raws[0])), os.path.getmtime(raws[0]))
        except OSError:
            continue
        if dau.get(ma) == nhan:
            continue
        ra[ma] = "chưa có số"
        for raw in raws:
            if giai_ma.cap_nhat_gio_online(raw, kenh_dir) is not None:
                ra[ma] = "ghi"
                break
        moi[ma] = nhan
    if moi != dau:
        os.makedirs(os.path.dirname(duong_dau), exist_ok=True)
        with io.open(duong_dau + ".tam", "w", encoding="utf-8") as tep:
            json.dump(moi, tep, ensure_ascii=False, indent=1)
        os.replace(duong_dau + ".tam", duong_dau)
    return ra


def goi_y_gio_dang(goc: str, ma: str) -> str:
    """Một dòng "giờ khán giả online → gợi ý khe đăng" (`xep_lich.goi_y_khe`) cho lời nhắc giám đốc / tổng
    giám đốc; "" khi kênh chưa có `gio-online.json` (lời nhắc y hệt như cũ). CHỈ GỢI Ý — nhịp đăng là quyền chủ."""
    try:
        from ..xep_lich import goi_y_khe  # noqa: PLC0415

        g = goi_y_khe(goc, ma)
    except Exception:  # noqa: BLE001
        return ""
    if not g.get("khe_de_xuat"):
        return ""
    d_vps, d_jst = g.get("dinh_online_vps") or {}, g.get("dinh_online_jst") or {}
    return ("Giờ khán giả online (Studio, {0}): đỉnh {1:02d}:00 giờ VPS ({2:02d}:00 JST) — gợi ý khe đăng {3} "
            "(đợt thử trang chủ ~12h sau đăng rơi vào giờ đông). Chỉ gợi ý cho chủ (nhip_dang ngoài tầm).").format(
                str(g.get("cap_nhat_gio_online") or "")[:10], int(d_vps.get("gio") or 0), int(d_jst.get("gio") or 0),
                ", ".join(g["khe_de_xuat"]))


KET_SAU_GIO = 6.0
TEP_DEN_HAN = "den-han.json"
VIEC_CUA_BAN_CON_NGAY = 8


def _chua_chay(goc: str, ma: str, bay_gio: _dt.datetime) -> bool:
    """Kênh bật mà hôm nay chưa có lượt (thứ Hai: chưa có lượt tuần) — KHÔNG tính tránh phiên."""
    tt = stn.doc_trang_thai(goc, ma)
    hom_nay = bay_gio.date().isoformat()
    return tt.get("ngay_chay") != hom_nay or (bay_gio.weekday() == 0 and tt.get("ngay_tuan") != hom_nay)


def kiem_ket(goc: str, *, bay_gio: Optional[_dt.datetime] = None, ghi: bool = True) -> List[Dict[str, Any]]:
    """Gác tổng gọi: kênh bật giám đốc mà đến hạn liền ≥ `KET_SAU_GIO` giờ chưa chạy được → [{ma, gio, ly_do}].
    Nhớ lúc THẤY đến hạn lần đầu ở `workspace/giam-doc/den-han.json` (`ghi=False`: chỉ đọc)."""
    bay_gio = bay_gio or _dt.datetime.now()
    duong = os.path.join(goc, THU_MUC_KHOA, TEP_DEN_HAN)
    try:
        with io.open(duong, encoding="utf-8") as tep:
            cu = json.load(tep)
        cu = cu if isinstance(cu, dict) else {}
    except (OSError, ValueError):
        cu = {}
    moi: Dict[str, str] = {}
    ra = []
    for ma in _kenh_bat(goc):
        if not _chua_chay(goc, ma, bay_gio):
            continue
        tu = str(cu.get(ma) or "") or bay_gio.replace(microsecond=0).isoformat()
        moi[ma] = tu
        try:
            gio = (bay_gio - _dt.datetime.fromisoformat(tu[:19])).total_seconds() / 3600.0
        except ValueError:
            gio = 0.0
        if gio >= KET_SAU_GIO:
            tt = stn.doc_trang_thai(goc, ma)
            ly = "lượt cuối {0}".format(str(tt.get("luc_chay") or "chưa có")[:16].replace("T", " "))
            if dang_giu_khoa(goc):
                ly += "; khoá lượt đang giữ từ {0:%H:%M}".format(
                    _dt.datetime.fromtimestamp(float(dang_giu_khoa(goc).get("bat_dau") or 0)))
            ra.append({"ma": ma, "gio": round(gio, 1), "ly_do": ly})
    if ghi and moi != cu:
        try:
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
                json.dump(moi, tep, ensure_ascii=False, indent=1)
            os.replace(duong + ".tam", duong)
        except OSError:
            pass
    return ra


def viec_cua_ban_kenh(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """"Việc của bạn" trong báo cáo cuối của giám đốc kênh `ma` (≤ 8 ngày tuổi, kênh còn bật)."""
    from .bao_cao import TEP_BAO_CAO_JSON  # noqa: PLC0415
    from .du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    if ma not in _kenh_bat(goc):
        return []
    try:
        with io.open(os.path.join(thu_muc_giam_doc(goc, ma), TEP_BAO_CAO_JSON), encoding="utf-8") as tep:
            bc = json.load(tep)
    except (OSError, ValueError):
        return []
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        if (bay_gio - _dt.datetime.fromisoformat(str(bc.get("luc"))[:19])).days > VIEC_CUA_BAN_CON_NGAY:
            return []
    except ValueError:
        return []
    return [str(x) for x in bc.get("viec_cua_ban") or [] if str(x).strip()]


def chay_het(goc: str, *, ghi: Optional[Callable[[str], None]] = None) -> List[KetQua]:
    """Thân `--chay`: giữ khoá, chạy mọi kênh đến hạn (LLM qua ví), nhả khoá. Một kênh hỏng không chặn kênh khác."""
    from . import quan_ly  # noqa: PLC0415

    if dang_giu_khoa(goc):
        return []
    duong = _duong_khoa(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    ra = []
    try:
        try:  # quyền theo thành tích: đủ ngưỡng thì tự nâng, tụt thì tự lùi (ghi kenh.yaml + nhật ký có số)
            for d in tu_nang_ha_quyen(goc):
                _log.info("giam_doc: %s %s → %s (%s)", d["ma"], d["truoc"], d["sau"], d["ly_do"])
        except Exception as loi:  # noqa: BLE001 — không chặn lượt giám đốc
            _log.warning("giam_doc: tự nâng/hạ quyền hỏng: %s", loi)
        for v in viec_den_han(goc):
            try:
                ra.append(chay_kenh(goc, v["ma"], goi_chat=quan_ly.goi_chat_that(goc, ghi), tuan=v["tuan"], ghi=ghi))
            except Exception as loi:  # noqa: BLE001 — kênh hỏng: ghi lại, mai thử lại (không lặp cả ngày)
                bay = _dt.datetime.now()
                stn.ghi_trang_thai(goc, v["ma"], loi_cuoi="{0}: {1}".format(type(loi).__name__, str(loi)[:200]),
                                   loi_luc=bay.isoformat(timespec="seconds"), ngay_chay=bay.date().isoformat(),
                                   **({"ngay_tuan": bay.date().isoformat()} if v["tuan"] else {}))
        from . import tong  # noqa: PLC0415 — thứ Hai, sau lượt tuần của mọi giám đốc kênh: họp công ty

        if tong.den_han(goc):
            try:
                tong.hop_tuan(goc, quan_ly.goi_chat_that(goc, ghi), ghi=ghi)
            except Exception as loi:  # noqa: BLE001
                _log.warning("giam_doc: tổng giám đốc hỏng: %s", loi)
    finally:
        try:
            os.remove(duong)
        except OSError:
            pass
    return ra
