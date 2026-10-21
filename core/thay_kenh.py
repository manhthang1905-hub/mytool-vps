"""THAY KÊNH KHÔNG ĐƯỢC PHÁT — tự phát hiện "mail hỏng" + tự trả kho + tự dựng kênh thay (20/10/2026, chủ duyệt).

═══ PHÁT HIỆN (hàm thuần `xet_kenh`, số liệu `CHANNEL/<k>/chi-so/bang-tom-tat.csv`) ═══

Kênh HỎNG (YouTube không phân phối tài khoản) khi CÙNG LÚC:
  * ≥ `SO_VIDEO` video có số, mỗi video đăng ≥ `TUOI_GIO` giờ (tính từ CUỐI ngày đăng — cột "Ngày đăng" chỉ có ngày,
    nên tính dè dặt) và bản chụp mới nhất ("Mốc mới nhất") cũng ≥ `TUOI_GIO` giờ;
  * TRUNG VỊ "Lượt hiển thị" của các video đó < `NGUONG_TRUNG_VI`;
  * KHÔNG video nào (kể cả video trẻ) từng > `NGUONG_DINH` hiển thị.
Thiếu/cũ số liệu (bảng tóm tắt sửa lần cuối > `TUOI_SO_LIEU_NGAY` ngày, hoặc < `SO_VIDEO` dòng đủ số) = KHÔNG hỏng.
Hiệu chỉnh 20/10 trên 10 video đầu: kênh hỏng trung vị 11–15, cao nhất ≤ 63; kênh tốt trung vị ≥ 596 → ngưỡng rất an toàn.
(`core/kenh_khong_phat.py` vẫn là lớp CẢNH BÁO sớm; module này là lớp HÀNH ĐỘNG theo luật chủ 20/10.)

═══ THAY (tự động hết, mỗi ngày tối đa MỘT lượt thay mới) ═══

Sổ `workspace/mo-kenh/thay-kenh.json`. Mỗi lượt đi từng bước, chạy lại an toàn (sập giữa chừng thì nhịp sau làm tiếp,
không bao giờ tạo đôi):
  tra_kho      `tra_kho.tra(cũ, thay=mới)` — tắt mọi công tắc + dời Chrome kênh cũ vào kho (bận thì nhịp sau dời).
  chon_chrome  Chrome MỚI trong kho đã đăng nhập (`core/kho_chrome.py`), ghi sổ `kho/_da-dung.json` trước khi dời.
               Kho hết → MỘT việc người "kho hết Chrome mới đã đăng nhập — cần thêm" (kênh cũ vẫn đã trả kho).
  dat_chrome   dời + đổi tên → `<cha>\\<MỚI>\\<MỚI>.exe`. Mã mới = hậu tố kế của cùng dòng (TL5-T7-K2 → TL5-T7-K3).
  giong        21/10: kênh thay DÙNG LẠI giọng của kênh cũ (kênh cũ đã trả kho → giọng rảnh). Kênh cũ không có giọng
               mới cần giọng kho KHÁC MỌI kênh đang chạy — hết thì việc người.
  dang_ky      đăng ký vào luồng mở kênh (`workspace/mo-kenh/trang-thai.json`, loai `thay_kenh_tu_dong`, `giu_nguyen`)
               → `core/mo_kenh` dựng BẢN SAO NGUYÊN kênh cũ (`mo_kenh.nhan_ban_giu_nguyen`, chủ 21/10/2026: lỗi ở tài
               khoản, không ở nội dung — giữ kenh.yaml, style.yaml, prompt/, nv/, giọng, nhịp, hồ sơ thiết lập, bài học
               nội dung; chỉ đổi mã, Chrome, tài khoản, UC/handle; KHÔNG tạo nhân vật/góc mới), `tu_chay: false`.
  thuong_hieu  sau khi chuẩn bị xong: `vm/tao_kenh_thuong_hieu.py` (đọc danh sách kênh của tài khoản trước — không tạo
               trùng; làm sạch tên; chọn kênh mới trong Studio + ghim UC) dưới khoá máy `nang`.
  cho_mo_kenh  `mo_kenh.kich_hoat`: ghép máy đăng (nối ĐUÔI `cac_kenh`, agent nạp nóng) → thiết lập kênh 11/11 → UC ghim
               → bật `tu_chay`/`tu_duyet`/`tu_dang`.
  xong         MỘT tin báo chủ (bao_dong) tóm tắt.
Công tắc: `workspace/cai-dat.json: thay_kenh_tu_dong: false` tắt hẳn; `kenh.yaml: thay_kenh_tu_dong: false` miễn một kênh.
Máy KHÔNG gõ mật khẩu/2FA, không tự đăng nhập Google, không xoá gì trên YouTube.

    python -m core.thay_kenh xet [--goc G]     # CHỈ ĐỌC: kênh nào hỏng theo luật (cả kênh trả kho, để đối chiếu)
    python -m core.thay_kenh chay              # một nhịp (skill D20 gọi mỗi giờ khi có việc)
    python -m core.thay_kenh xem               # sổ các lượt thay
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import re
import subprocess
import sys
import time
from statistics import median
from typing import Any, Callable, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SO_VIDEO = 10
TUOI_GIO = 72.0
NGUONG_TRUNG_VI = 100.0
NGUONG_DINH = 500.0
TUOI_SO_LIEU_NGAY = 3.0
TEP_SO = ("workspace", "mo-kenh", "thay-kenh.json")
TEP_NHAT_KY = ("workspace", "mo-kenh", "nhat-ky.log")
LOAI_MO_KENH = "thay_kenh_tu_dong"
BUOC = ("tra_kho", "chon_chrome", "dat_chrome", "giong", "dang_ky", "thuong_hieu", "cho_mo_kenh", "xong")
#: Tạo kênh thương hiệu cần người (CAPTCHA/đăng nhập lại) → thử lại sau ngần này giờ.
GIO_THU_LAI_CAN_NGUOI = 6.0
HAN_TAO_KENH_GIAY = 25 * 60
MA_XONG, MA_HOAN, MA_LOI = 0, 10, 1
MUC_THIET_LAP = 11

COT_VID, COT_NGAY, COT_MOC, COT_HIEN_THI = "Mã video", "Ngày đăng", "Mốc mới nhất", "Lượt hiển thị"


# ═══════════════════════════ PHÁT HIỆN (thuần) ═══════════════════════════════
def _so(chu: Any) -> Optional[float]:
    s = re.sub(r"[\s,. ]", "", str(chu if chu is not None else "").strip())
    if not s or not re.fullmatch(r"\d+", s):
        return None
    return float(s)


def _ngay(chu: Any) -> Optional[_dt.date]:
    s = str(chu or "").strip()
    for dang in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return _dt.datetime.strptime(s[:10], dang).date()
        except ValueError:
            continue
    return None


def _gio_moc(chu: Any) -> Optional[float]:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*h\s*", str(chu or ""))
    return float(m.group(1)) if m else None


def duong_bang(goc: str, ma: str) -> str:
    return os.path.join(goc, "CHANNEL", ma, "chi-so", "bang-tom-tat.csv")


def doc_bang(goc: str, ma: str) -> Tuple[List[Dict[str, str]], Optional[float]]:
    """(các dòng, mtime) của bảng tóm tắt Studio; ([], None) nếu chưa có."""
    p = duong_bang(goc, ma)
    try:
        mtime = os.path.getmtime(p)
        with io.open(p, encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep)), mtime
    except (OSError, csv.Error, UnicodeDecodeError):
        return [], None


def xet_kenh(dong: List[Dict[str, str]], mtime: Optional[float], bay_gio: _dt.datetime) -> Dict[str, Any]:
    """Luật chủ 20/10. {ket: hong | dat | thieu_so, ly_do, so_video, trung_vi, dinh, tong}. Hàm thuần."""
    if mtime is None or not dong:
        return {"ket": "thieu_so", "ly_do": "chưa có bảng tóm tắt Studio" if mtime is None else "bảng tóm tắt chưa có video",
                "so_video": 0}
    tuoi_ngay = (bay_gio.timestamp() - mtime) / 86400.0
    if tuoi_ngay > TUOI_SO_LIEU_NGAY:
        return {"ket": "thieu_so", "ly_do": "số liệu cũ {0:.1f} ngày (> {1:.0f}) — không kết luận".format(
            tuoi_ngay, TUOI_SO_LIEU_NGAY), "so_video": 0}
    dinh = 0.0
    du: List[float] = []
    for r in dong:
        ht = _so(r.get(COT_HIEN_THI))
        if ht is None:
            continue
        dinh = max(dinh, ht)
        ng, moc = _ngay(r.get(COT_NGAY)), _gio_moc(r.get(COT_MOC))
        if ng is None or moc is None:
            continue
        tuoi = (bay_gio - _dt.datetime.combine(ng + _dt.timedelta(days=1), _dt.time())).total_seconds() / 3600.0
        if tuoi >= TUOI_GIO and moc >= TUOI_GIO:
            du.append(ht)
    ra = {"so_video": len(du), "dinh": dinh, "trung_vi": median(du) if du else None, "tong": sum(du)}
    if len(du) < SO_VIDEO:
        return dict(ra, ket="thieu_so", ly_do="mới {0} video đủ ≥ {1:.0f} giờ có số (cần {2})".format(
            len(du), TUOI_GIO, SO_VIDEO))
    if dinh > NGUONG_DINH:
        return dict(ra, ket="dat", ly_do="có video từng {0:.0f} hiển thị (> {1:.0f}) — được phân phối".format(dinh, NGUONG_DINH))
    if ra["trung_vi"] >= NGUONG_TRUNG_VI:
        return dict(ra, ket="dat", ly_do="trung vị hiển thị {0:.0f} ≥ {1:.0f}".format(ra["trung_vi"], NGUONG_TRUNG_VI))
    return dict(ra, ket="hong", ly_do="{0} video ≥ {1:.0f} giờ: trung vị hiển thị {2:.0f} (< {3:.0f}), cao nhất {4:.0f} "
                "(≤ {5:.0f}) — YouTube không phân phối tài khoản".format(len(du), TUOI_GIO, ra["trung_vi"], NGUONG_TRUNG_VI,
                                                                        dinh, NGUONG_DINH))


# ═══════════════════════════ sổ + tiện ích ═══════════════════════════════════
def _bay_gio(b: Optional[_dt.datetime] = None) -> _dt.datetime:
    return b or _dt.datetime.now()


def _doc_json(duong: str) -> Dict[str, Any]:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def doc_so(goc: str) -> Dict[str, Any]:
    so = _doc_json(os.path.join(goc, *TEP_SO))
    if not isinstance(so.get("luot"), dict):
        so["luot"] = {}
    return so


def luu_so(goc: str, so: Dict[str, Any]) -> None:
    _ghi_json(os.path.join(goc, *TEP_SO), so)


def _nhat_ky(goc: str, dong: str) -> None:
    try:
        p = os.path.join(goc, *TEP_NHAT_KY)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "a", encoding="utf-8") as tep:
            tep.write("{0} [thay-kenh] {1}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def bat(goc: str) -> bool:
    d = _doc_json(os.path.join(goc, "workspace", "cai-dat.json"))
    return str(d.get("thay_kenh_tu_dong", True)).strip().lower() not in ("false", "0", "tat", "no", "off")


def _kenh_yaml(goc: str, ma: str) -> Dict[str, Any]:
    from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    return dict(doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {})


def kenh_may(goc: str) -> List[str]:
    """Kênh máy này VẬN HÀNH (vm/config.json `cac_kenh`), bỏ kênh trả kho. Không đọc được → mọi kênh đang chạy."""
    from .kenh import bo_kenh_tra_kho, liet_ke_kenh  # noqa: PLC0415

    cfg = _doc_json(os.path.join(goc, "vm", "config.json"))
    ds = [str(k).strip() for k in (cfg.get("cac_kenh") or []) if str(k).strip()]
    ds = [k for k in ds if os.path.isfile(os.path.join(goc, "CHANNEL", k, "kenh.yaml"))]
    return bo_kenh_tra_kho(goc, ds) if ds else liet_ke_kenh(goc)


def xet_tat_ca(goc: str, bay_gio: Optional[_dt.datetime] = None, ca_tra_kho: bool = False) -> Dict[str, Dict[str, Any]]:
    """{mã: kết quả `xet_kenh`} cho kênh máy vận hành (`ca_tra_kho=True`: thêm kênh trả kho — chỉ để đối chiếu)."""
    from .kenh import liet_ke_kenh  # noqa: PLC0415

    ds = kenh_may(goc)
    if ca_tra_kho:
        ds = ds + [k for k in liet_ke_kenh(goc, ca_tra_kho=True) if k not in ds and _kenh_yaml(goc, k).get("tra_kho")]
    ra = {}
    for ma in ds:
        dong, mt = doc_bang(goc, ma)
        ra[ma] = xet_kenh(dong, mt, _bay_gio(bay_gio))
    return ra


# ═══════════════════════════ mã mới · giọng · thương hiệu ═════════════════════
def ma_moi(goc: str, cu: str, giu_cho: Optional[List[str]] = None) -> str:
    """Hậu tố kế của cùng dòng: TL5-T7-K2 → TL5-T7-K3 (tránh mọi mã đã có: CHANNEL/, Chrome cạnh MyTool, kho, sổ)."""
    from .mo_kenh import _cac_kenh, ma_nhan_ban  # noqa: PLC0415
    from .tra_kho import thu_muc_kho  # noqa: PLC0415

    cha = os.path.dirname(os.path.abspath(goc))

    def ton_tai(m: str) -> bool:
        return (m in (giu_cho or []) or os.path.exists(os.path.join(goc, "CHANNEL", m))
                or os.path.exists(os.path.join(cha, m)) or os.path.exists(os.path.join(thu_muc_kho(goc), m)))
    return ma_nhan_ban(_cac_kenh(goc) + list(giu_cho or []), cu, ton_tai)


def giong_dang_dung(goc: str, tru: str = "") -> List[str]:
    """voice_id của MỌI kênh đang chạy (không trả kho), trừ `tru`."""
    from .kenh import liet_ke_kenh  # noqa: PLC0415

    ra = []
    for m in liet_ke_kenh(goc):
        if m == tru:
            continue
        v = str(_kenh_yaml(goc, m).get("voice_id") or "").strip()
        if v:
            ra.append(v)
    return ra


def giong_con_trong(goc: str, nhom: str, tru: str = "") -> List[str]:
    """Giọng trong kho giọng ĐÃ DUYỆT của nhóm chưa kênh đang chạy nào dùng."""
    from .mo_kenh import doc_kho_giong  # noqa: PLC0415

    cam = set(giong_dang_dung(goc, tru))
    return [x["voice_id"] for x in doc_kho_giong(goc, nhom, ghi=False) if x.get("voice_id") and x["voice_id"] not in cam]


def _vm(goc: str, *phan: str) -> str:
    return os.path.join(goc, "vm", *phan)


def thuong_hieu_xong(goc: str, ma: str) -> Tuple[bool, str]:
    """Kênh thương hiệu đã tạo/chọn + UC đã ghim (`vm/logs/tao-kenh/<K>.json` + `vm/logs/kenh-uc.json`)."""
    so = _doc_json(_vm(goc, "logs", "tao-kenh", ma + ".json"))
    if so.get("ket_qua") not in ("ok", "da_co"):
        return False, "chưa tạo kênh thương hiệu ({0})".format(so.get("ket_qua") or "chưa chạy")
    uc = str(_doc_json(_vm(goc, "logs", "kenh-uc.json")).get(ma) or "")
    if not uc or (so.get("uc") and uc != so.get("uc")):
        return False, "chưa ghim UC kênh thương hiệu"
    return True, uc


def thiet_lap_du(goc: str, ma: str) -> Tuple[bool, str]:
    """Sổ thiết lập kênh `xong` VÀ đủ `MUC_THIET_LAP` mục đạt."""
    so = _doc_json(_vm(goc, "logs", "thiet-lap-kenh", ma + ".json"))
    muc = so.get("muc") if isinstance(so.get("muc"), dict) else {}
    dat = sum(1 for v in muc.values() if isinstance(v, dict) and v.get("tt") == "dat")
    if so.get("trang_thai") != "xong" or dat < MUC_THIET_LAP:
        return False, "thiết lập kênh {0}/{1} ({2})".format(dat, MUC_THIET_LAP, so.get("trang_thai") or "chưa chạy")
    return True, "{0}/{1}".format(dat, MUC_THIET_LAP)


def _chay_tao_kenh(goc: str, ma: str) -> int:
    """`vm/tao_kenh_thuong_hieu.py --kenh MÃ` dưới khoá máy `nang` (bận → hoãn). Mã thoát của nó (0/10/20/1)."""
    from . import khe  # noqa: PLC0415

    phien = khe.thu_giu(goc, khe.LOP_NANG, "tao-kenh-thuong-hieu", kenh=ma, uu_tien=2, han_giay=HAN_TAO_KENH_GIAY)
    if phien is None:
        return MA_HOAN
    with phien:
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            p = subprocess.run([sys.executable, "-X", "utf8", os.path.join(goc, "vm", "tao_kenh_thuong_hieu.py"), "--kenh", ma],
                               cwd=goc, capture_output=True, timeout=HAN_TAO_KENH_GIAY, creationflags=co,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"), check=False)
            return int(p.returncode)
        except subprocess.TimeoutExpired:
            return MA_LOI


def _dong_bo_ten_ho_so(goc: str, ma: str) -> None:
    """Tên cuối trên YouTube (đã làm sạch lúc tạo) khác tên hồ sơ → hồ sơ theo tên thật (thiết lập kênh không đổi tên
    oan, tốn lượt đổi tên 14 ngày)."""
    so = _doc_json(_vm(goc, "logs", "tao-kenh", ma + ".json"))
    ten = str(so.get("ten") or "").strip()
    if not ten:
        return
    try:
        from . import thiet_lap_kenh as tl  # noqa: PLC0415

        hs = tl.doc_ho_so(ma, goc)
        if hs and str(hs.get("ten") or "").strip() != ten:
            hs["ten"] = ten
            tl.ghi_ho_so(ma, hs, goc)
    except Exception:  # noqa: BLE001 — phụ
        pass


def _bao(goc: str, loai: str, tieu_de: str, chi_tiet: str, kenh: str = "") -> None:
    try:
        from .bao_dong import bao_dong  # noqa: PLC0415

        bao_dong(loai, tieu_de, chi_tiet, goc=goc, kenh=kenh or None)
    except Exception:  # noqa: BLE001
        pass


def _dau_kho(goc: str) -> str:
    """Vân tay kho Chrome (tên + mtime) — kho đổi thì xét lại việc đang chờ người."""
    from .tra_kho import thu_muc_kho  # noqa: PLC0415

    k = thu_muc_kho(goc)
    try:
        return "|".join("{0}:{1:.0f}".format(t, os.path.getmtime(os.path.join(k, t))) for t in sorted(os.listdir(k)))
    except OSError:
        return ""


def _dau_giong(goc: str, nhom: str) -> str:
    from .mo_kenh import duong_kho_giong  # noqa: PLC0415

    try:
        return "{0:.0f}".format(os.path.getmtime(duong_kho_giong(goc, nhom)))
    except OSError:
        return ""


# ═══════════════════════════ MỘT NHỊP ═════════════════════════════════════════
def _cho_nguoi(l: Dict[str, Any], khoa: str, chu: str, goi_y: str, dau: str) -> None:
    l["cho_nguoi"] = {"khoa": khoa, "chu": chu, "goi_y": goi_y, "dau": dau}


def buoc(goc: str, l: Dict[str, Any], so: Dict[str, Any], *, bay_gio: _dt.datetime, log: Callable[[str], None],
         tra: Optional[Callable[..., Any]] = None, quet: Optional[Callable[..., Any]] = None,
         chay_tao_kenh: Optional[Callable[[str, str], int]] = None) -> str:
    """Đi tiếp MỘT bước của lượt `l` (sửa tại chỗ). Trả: 'tiep' (làm bước kế ngay) | 'cho' (đợi bộ máy khác / người)
    | 'hoan' (bận — nhịp sau) | 'loi'."""
    from . import kho_chrome, mo_kenh  # noqa: PLC0415
    from . import tra_kho as tk  # noqa: PLC0415

    cu, moi, b = l["cu"], l["moi"], l.get("buoc")
    l["cap_nhat"] = bay_gio.strftime("%Y-%m-%d %H:%M")
    if b == "tra_kho":
        kq = (tra or tk.tra)(goc, cu, thay=moi, bay_gio=bay_gio)
        l["chrome_cu"] = kq.get("chrome")
        log("{0}: đã trả kho (Chrome: {1} — {2})".format(cu, kq.get("chrome"), kq.get("chrome_ghi_chu")))
        _nhat_ky(goc, "trả kho {0} (thay bởi {1}): Chrome {2}".format(cu, moi, kq.get("chrome")))
        l["buoc"] = "chon_chrome"
        return "tiep"
    if b == "chon_chrome":
        ten = kho_chrome.chrome_cua_kenh(goc, moi)
        if not ten:
            ds = (quet or kho_chrome.quet)(goc)
            so["kho_quet"] = {"luc": l["cap_nhat"], "ds": ds}
            moi_ds = [x for x in ds if x["loai"] == "moi"]
            if not moi_ds:
                _cho_nguoi(l, "thay-kenh:kho-het", "Kho hết Chrome mới đã đăng nhập — cần thêm (đang chờ thay {0} → {1})".format(cu, moi),
                           "→ chép Chrome Portable mới vào {0}\\<tên tuỳ ý>\\ (có <tên>.exe), mở nó, đăng nhập Gmail tay; máy tự "
                           "nhận ở nhịp sau".format(tk.thu_muc_kho(goc)), _dau_kho(goc))
                if not so.get("da_bao_kho_het"):
                    so["da_bao_kho_het"] = l["cap_nhat"]
                    _bao(goc, "kho_chrome_het", "Kho hết Chrome mới đã đăng nhập — cần thêm",
                         "Kênh {0} đã trả kho (không được phân phối); kênh thay {1} chờ một Chrome Portable mới đã đăng "
                         "nhập Gmail trong {2}.".format(cu, moi, tk.thu_muc_kho(goc)))
                return "cho"
            ten = moi_ds[0]["ten"]
            if not kho_chrome.giu(goc, ten, moi):
                return "hoan"
        so.pop("da_bao_kho_het", None)
        l.pop("cho_nguoi", None)
        l["chrome_kho"] = ten
        log("{0}: chọn Chrome kho «{1}»".format(moi, ten))
        l["buoc"] = "dat_chrome"
        return "tiep"
    if b == "dat_chrome":
        tt, gc = kho_chrome.lap_dat(goc, l["chrome_kho"], moi)
        log("{0}: {1} — {2}".format(moi, tt, gc))
        if tt == "hong":
            l["loi"] = gc
            return "loi"
        _nhat_ky(goc, "đặt Chrome {0}: {1}".format(moi, gc))
        l["loi"] = ""
        l["buoc"] = "giong"
        return "tiep"
    if b == "giong":
        nhom = str(_kenh_yaml(goc, cu).get("nhom") or "")
        # 21/10/2026: kênh thay giữ NGUYÊN giọng kênh cũ (kênh cũ đã trả kho nên giọng ấy rảnh)
        con = [v for v in [str(_kenh_yaml(goc, cu).get("voice_id") or "").strip()] if v] or giong_con_trong(goc, nhom, tru=moi)
        if not con:
            _cho_nguoi(l, "thay-kenh:het-giong:{0}".format(moi),
                       "Thay kênh {0}: kho giọng nhóm {1} hết giọng chưa kênh nào dùng".format(moi, nhom or "?"),
                       "→ thêm voice_id ĐÃ DUYỆT (kèm ky_tu_moi_phut đã đo) vào {0}; máy không dùng lại giọng kênh khác".format(
                           mo_kenh.duong_kho_giong(goc, nhom).replace(goc + os.sep, "")), _dau_giong(goc, nhom))
            return "cho"
        l.pop("cho_nguoi", None)
        l["buoc"] = "dang_ky"
        return "tiep"
    if b == "dang_ky":
        st = mo_kenh.doc_trang_thai(goc)
        if moi not in st["kenh"]:
            y = _kenh_yaml(goc, cu)
            st["kenh"][moi] = {"trang_thai": "de_xuat", "tep": str(y.get("tep") or ""), "ten_tep": str(y.get("tep") or ""),
                               "loai": LOAI_MO_KENH, "nhom": str(y.get("nhom") or ""), "kenh_goc": cu,
                               "ly_do": "tự thay kênh không được phân phối {0}: {1}".format(cu, l.get("ly_do") or ""),
                               "ngay_de_xuat": bay_gio.strftime("%Y-%m-%d"), "kiem_cuoi": 0, "loi": "",
                               "tu_dong": True, "giu_nguyen": True, "can_thuong_hieu": True,
                               "chrome_kho": l.get("chrome_kho") or ""}
            mo_kenh.luu_trang_thai(goc, st)
            _nhat_ky(goc, "đăng ký mở kênh thay {0} (khuôn {1})".format(moi, cu))
        l["buoc"] = "thuong_hieu"
        return "cho"
    if b == "thuong_hieu":
        d = mo_kenh.doc_trang_thai(goc)["kenh"].get(moi) or {}
        if d.get("trang_thai") in ("de_xuat", "") or not d.get("ten_goi_y"):
            return "cho"                                             # mo_kenh chưa chuẩn bị xong (góc/tên/hồ sơ)
        ok, _uc = thuong_hieu_xong(goc, moi)
        if not ok:
            ma = (chay_tao_kenh or _chay_tao_kenh)(goc, moi)
            l["tao_kenh_luc"] = l["cap_nhat"]
            l["tao_kenh_ma"] = ma
            ok, ly = thuong_hieu_xong(goc, moi)
            if not ok:
                if ma == MA_HOAN:
                    return "hoan"
                ket = _doc_json(_vm(goc, "logs", "tao-kenh", moi + ".json"))
                if ma == 20 or ket.get("ket_qua") == "can_nguoi":
                    _cho_nguoi(l, "thay-kenh:tao-kenh:{0}".format(moi),
                               "Thay kênh {0}: tạo kênh thương hiệu cần người — {1}".format(moi, str(ket.get("ly_do") or ly)[:120]),
                               "→ mở Chrome {0}, xử lý (đăng nhập lại / CAPTCHA) rồi đóng Chrome; máy thử lại sau {1:.0f} giờ".format(
                                   moi, GIO_THU_LAI_CAN_NGUOI), str(ket.get("luc") or ""))
                    return "cho"
                l["loi"] = "tạo kênh thương hiệu: {0} — {1}".format(ket.get("ket_qua") or ma, str(ket.get("ly_do") or "")[:120])
                return "loi"
        l.pop("cho_nguoi", None)
        l["loi"] = ""
        _dong_bo_ten_ho_so(goc, moi)
        log("{0}: kênh thương hiệu xong + UC đã ghim".format(moi))
        _nhat_ky(goc, "kênh thương hiệu {0} xong, UC ghim".format(moi))
        l["buoc"] = "cho_mo_kenh"
        return "tiep"
    if b == "cho_mo_kenh":
        d = mo_kenh.doc_trang_thai(goc)["kenh"].get(moi) or {}
        if d.get("trang_thai") != "xong":
            return "cho"
        l["buoc"] = "xong"
        l["ngay_xong"] = bay_gio.strftime("%Y-%m-%d")
        ten = str(d.get("ten_goi_y") or "")
        _, uc = thuong_hieu_xong(goc, moi)
        _bao(goc, "thay_kenh_xong", "Đã tự thay kênh {0} → {1}".format(cu, moi),
             "{0} không được phân phối ({1}) → đã trả kho. Kênh thay {2}{3}: Chrome kho «{4}», kênh thương hiệu {5}, "
             "thiết lập 11/11, đã bật tự chạy/tự duyệt/tự đăng.".format(
                 cu, l.get("ly_do") or "", moi, " «{0}»".format(ten) if ten else "", l.get("chrome_kho") or "?", uc or "?"),
             kenh=moi)
        _nhat_ky(goc, "XONG thay {0} → {1}".format(cu, moi))
        log("XONG thay {0} → {1}".format(cu, moi))
        return "cho"
    return "cho"


def _dang_mo(so: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted((l for l in so["luot"].values() if l.get("buoc") != "xong"), key=lambda l: l.get("ngay") or "")


def phat_hien(goc: str, so: Dict[str, Any], bay_gio: _dt.datetime, log: Callable[[str], None]) -> Optional[Dict[str, Any]]:
    """Xét luật mỗi ngày một lần; kênh hỏng (chưa có lượt) → mở MỘT lượt mới nếu hôm nay chưa mở lượt nào."""
    hom = bay_gio.strftime("%Y-%m-%d")
    if so.get("ngay_xet") == hom:
        return None
    ket = xet_tat_ca(goc, bay_gio)
    so["ngay_xet"] = hom
    so["ket_xet"] = {k: {x: v.get(x) for x in ("ket", "ly_do", "so_video", "trung_vi", "dinh")} for k, v in ket.items()}
    dang = {l["cu"] for l in _dang_mo(so)} | {l["moi"] for l in _dang_mo(so)}      # kênh trong lượt đang chạy
    hong = [k for k, v in ket.items() if v["ket"] == "hong" and k not in dang
            and str(_kenh_yaml(goc, k).get("thay_kenh_tu_dong", True)).strip().lower() not in ("false", "0", "tat")]
    for k in hong:
        log("{0}: HỎNG — {1}".format(k, ket[k]["ly_do"]))
    if not hong or so.get("ngay_thay_cuoi") == hom:
        return None
    cu = hong[0]
    moi = ma_moi(goc, cu, [l["moi"] for l in so["luot"].values()])
    l = {"cu": cu, "moi": moi, "buoc": "tra_kho", "ngay": hom, "ly_do": ket[cu]["ly_do"], "loi": ""}
    so["luot"][cu] = l
    so["ngay_thay_cuoi"] = hom
    _nhat_ky(goc, "phát hiện {0} hỏng ({1}) → thay bằng {2}".format(cu, ket[cu]["ly_do"], moi))
    return l


def can_lam(goc: str, bay_gio: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """Điều kiện skill D20 — RẺ (đọc sổ + vài tệp, không mở Chrome): có bước làm được ngay không."""
    if not bat(goc):
        return False, "tắt (workspace/cai-dat.json thay_kenh_tu_dong)"
    bay_gio = _bay_gio(bay_gio)
    try:
        from .tra_kho import chrome_cho_cat  # noqa: PLC0415

        cho_cat = chrome_cho_cat(goc)
    except Exception:  # noqa: BLE001
        cho_cat = []
    if cho_cat:
        return True, "Chrome kênh trả kho chưa dời vào kho: " + ", ".join(cho_cat)
    so = doc_so(goc)
    for l in _dang_mo(so):
        b = l.get("buoc")
        cn = l.get("cho_nguoi") or {}
        if cn:
            if b == "chon_chrome" and cn.get("dau") != _dau_kho(goc):
                return True, "kho Chrome đổi — xét lại (thay {0})".format(l["cu"])
            if b == "giong" and cn.get("dau") != _dau_giong(goc, str(_kenh_yaml(goc, l["cu"]).get("nhom") or "")):
                return True, "kho giọng đổi — xét lại (thay {0})".format(l["cu"])
            if b == "thuong_hieu":
                try:
                    t = _dt.datetime.strptime(str(l.get("tao_kenh_luc") or ""), "%Y-%m-%d %H:%M")
                except ValueError:
                    t = None
                if t is None or (bay_gio - t).total_seconds() >= GIO_THU_LAI_CAN_NGUOI * 3600:
                    return True, "thử lại tạo kênh thương hiệu {0}".format(l["moi"])
            continue
        if b in ("tra_kho", "chon_chrome", "dat_chrome", "giong", "dang_ky"):
            return True, "thay {0} → {1}: bước {2}".format(l["cu"], l["moi"], b)
        if b == "thuong_hieu":
            from .mo_kenh import doc_trang_thai  # noqa: PLC0415

            d = doc_trang_thai(goc)["kenh"].get(l["moi"]) or {}
            if d.get("trang_thai") not in ("de_xuat", "", None) and d.get("ten_goi_y"):
                return True, "tạo kênh thương hiệu {0}".format(l["moi"])
        if b == "cho_mo_kenh":
            from .mo_kenh import doc_trang_thai  # noqa: PLC0415

            if (doc_trang_thai(goc)["kenh"].get(l["moi"]) or {}).get("trang_thai") == "xong":
                return True, "kênh {0} đã chạy — báo chủ".format(l["moi"])
    if so.get("ngay_xet") != bay_gio.strftime("%Y-%m-%d"):
        return True, "xét luật kênh hỏng hôm nay"
    return False, "không có việc thay kênh"


def chay(goc: str, *, bay_gio: Optional[_dt.datetime] = None, log: Callable[[str], None] = print,
         tra: Optional[Callable[..., Any]] = None, quet: Optional[Callable[..., Any]] = None,
         chay_tao_kenh: Optional[Callable[[str, str], int]] = None,
         nhip_chrome: Optional[Callable[[str], Dict[str, Any]]] = None) -> int:
    """MỘT nhịp: dời Chrome kênh trả kho còn sót → xét luật (1 lần/ngày) → đi tiếp mọi lượt tới khi phải chờ.
    Mã thoát: 0 xong · 10 hoãn (bận, nhịp sau) · 1 lỗi."""
    if not bat(goc):
        log("thay kênh tự động: tắt")
        return MA_XONG
    bay_gio = _bay_gio(bay_gio)
    ma_ra = MA_XONG
    try:
        from .tra_kho import nhip_chrome as _nhip  # noqa: PLC0415

        for ma, (tt, gc) in (nhip_chrome or _nhip)(goc).items():
            log("Chrome kênh trả kho {0}: {1} — {2}".format(ma, tt, gc))
            if tt == "hoan":
                ma_ra = MA_HOAN
    except Exception as loi:  # noqa: BLE001
        log("dời Chrome kênh trả kho hỏng: {0}".format(str(loi)[:150]))
    so = doc_so(goc)
    phat_hien(goc, so, bay_gio, log)
    luu_so(goc, so)
    for l in _dang_mo(so):
        for _ in range(len(BUOC) + 1):
            try:
                kq = buoc(goc, l, so, bay_gio=bay_gio, log=log, tra=tra, quet=quet, chay_tao_kenh=chay_tao_kenh)
            except Exception as loi:  # noqa: BLE001 — một lượt hỏng không chặn lượt khác; nhịp sau thử lại
                l["loi"] = "{0}: {1}".format(type(loi).__name__, str(loi)[:200])
                kq = "loi"
            luu_so(goc, so)
            if kq == "hoan" and ma_ra == MA_XONG:
                ma_ra = MA_HOAN
            if kq == "loi":
                log("thay {0} → {1}: LỖI bước {2}: {3}".format(l["cu"], l["moi"], l.get("buoc"), l.get("loi")))
                _nhat_ky(goc, "lỗi bước {0} ({1}→{2}): {3}".format(l.get("buoc"), l["cu"], l["moi"], l.get("loi")))
                ma_ra = MA_LOI
            if kq != "tiep":
                break
    return ma_ra


# ═══════════════════════════ Việc của bạn · xem ═══════════════════════════════
def viec_cua_ban(goc: str) -> List[Dict[str, str]]:
    """Việc CHỈ người làm được (kho hết Chrome đăng nhập, Chrome kho chưa đăng nhập, hết giọng, tạo kênh cần người).
    Mỗi phần tử {khoa, kenh, chu, goi_y}; trùng khoá gộp một."""
    so = doc_so(goc)
    ra: Dict[str, Dict[str, str]] = {}
    for l in _dang_mo(so):
        cn = l.get("cho_nguoi") or {}
        if cn.get("khoa") and cn["khoa"] not in ra:
            ra[cn["khoa"]] = {"khoa": cn["khoa"], "kenh": l["moi"], "chu": cn.get("chu") or "", "goi_y": cn.get("goi_y") or ""}
    for x in ((so.get("kho_quet") or {}).get("ds") or []):
        if x.get("loai") == "chua_dang_nhap":
            k = "kho-chrome:chua-dang-nhap:{0}".format(x.get("ten"))
            ra.setdefault(k, {"khoa": k, "kenh": "", "chu": "Chrome «{0}» trong kho chưa đăng nhập Gmail — máy bỏ qua".format(x.get("ten")),
                              "goi_y": "→ mở {0}.exe trong kho, đăng nhập Gmail bằng tay rồi đóng (máy không tự đăng nhập)".format(x.get("ten"))})
    return list(ra.values())


def tom_tat(goc: str) -> List[str]:
    so = doc_so(goc)
    d = ["Thay kênh tự động: {0} · xét luật lần cuối {1}".format("BẬT" if bat(goc) else "TẮT", so.get("ngay_xet") or "chưa")]
    for k, v in sorted((so.get("ket_xet") or {}).items()):
        d.append("  {0:<11} {1:<9} {2}".format(k, v.get("ket"), v.get("ly_do")))
    for l in so["luot"].values():
        d.append("  lượt {0} → {1}: bước {2}{3}{4}".format(l["cu"], l["moi"], l.get("buoc"),
                                                         " · Chrome kho «{0}»".format(l["chrome_kho"]) if l.get("chrome_kho") else "",
                                                         " · " + (l.get("loi") or (l.get("cho_nguoi") or {}).get("chu") or "")
                                                         if (l.get("loi") or l.get("cho_nguoi")) else ""))
    return d


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    a = list(sys.argv[1:] if argv is None else argv) or ["xem"]
    goc = GOC
    if "--goc" in a:
        i = a.index("--goc")
        goc, a = os.path.abspath(a[i + 1]), a[:i] + a[i + 2:]
    if a[0] == "xet":
        bay = _bay_gio()
        for k, v in xet_tat_ca(goc, bay, ca_tra_kho=True).items():
            print("{0:<11} {1:<9}{2} {3}".format(k, v["ket"], " (trả kho)" if _kenh_yaml(goc, k).get("tra_kho") else "",
                                               v["ly_do"]))
        return 0
    if a[0] == "chay":
        def log(dong: str) -> None:
            print(dong)
        return chay(goc, log=log)
    print("\n".join(tom_tat(goc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
