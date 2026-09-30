"""Bộ điều phối sản xuất SONG SONG nhiều kênh (Đợt 1.3b + 1.4 + 1.5, bản gọn — 29/09/2026).

═══ VÌ SAO ═══

Trước tệp này `tu_chay.py --tat-ca` chạy các kênh LẦN LƯỢT và giữ `.khoa-may`
SUỐT cả lượt (đo 27–28/09: một video 9 giờ, 87% là chờ máy chủ vẽ ảnh). Cả máy
ra ~1 video/ngày dù CPU/RAM gần như rảnh trong lúc chờ máy chủ.

Luật điều phối (lộ trình v3, chủ dự án chốt):

* lớp **A — API** (kịch bản, bảng cảnh, ảnh, clip, thumbnail, nghiên cứu…):
  chạy SONG SONG theo N làn (`core.khe` lớp "api", `workspace/cai-dat.json:
  lan_api`, khởi đầu 2). Mỗi lượt sản xuất = một tiến trình tách rời
  `tu_chay.py --kenh X --tu-dieu-phoi`, giữ khoá kênh + MỘT làn suốt lượt.
* lớp **B — máy nặng** (phụ đề Whisper, dựng FFmpeg, đoạn nối mp3 của giọng
  đọc, QA + chép gói, kho nhạc/vòng học) và lớp **C — trình duyệt** (agent: phiên
  quét, tải lên, --kiem-dom) giữ CHUNG khe loại trừ "nang" (`.khoa-may`, đúng
  đường cũ) — chỉ quanh ĐÚNG khâu đó, không cả lượt.
* ưu tiên khe theo `core.uu_tien` (tải lên sắp tới hạn > quét ngày > dựng > nền).
* CLAUDE.md luật 4–5 khi >1 lượt song song: tổng `GET /v1/jobs` toàn máy ≤ 1/30s
  (`core.so_job_chung`, cắm vào `SoTheoDoi._mot_luot`), tải kết quả về ≤ 6 luồng
  toàn máy + tạm dừng khi đang tải lên YouTube (`core.bang_thong`).

═══ BẬT/TẮT ═══

Chỉ chạy khi máy ở chế độ VPS (`vps.json`) VÀ `workspace/cai-dat.json` có
`"dieu_phoi": true`. Tắt → mọi hàm ở đây là KHÔNG LÀM GÌ, `tu_chay.py` chạy y
như trước (giữ `.khoa-may` cả lượt, `--tat-ca` lần lượt).

═══ VÌ SAO CẮM MÓC (monkeypatch) THAY VÌ SỬA `core/auto_khau.py` ═══

`core/auto_khau.py` (8.000+ dòng) đang có bản nháp Đợt 4 của một agent khác
(`workspace/nhap-dot4-ngach/core/auto_khau.py`). Sửa thẳng tệp đó thì hai bản
nháp đá nhau. `cai_moc_tien_trinh()` thay ba hàm của `auto_khau` NGAY TRONG
TIẾN TRÌNH LƯỢT ĐIỀU PHỐI (không ảnh hưởng giao diện, không ảnh hưởng chế độ
tắt): `SoTheoDoi._mot_luot` → hỏi qua sổ chung; `_tai_ket_qua_mot_lan` → xin
suất băng thông; `_noi_mp3` → giữ khe nang. Khi gộp Đợt 4 xong có thể đưa ba
móc này vào hẳn `auto_khau.py` (ghi ở GHI-CHU bản vá 2026-09-29-full-cong-suat).
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from . import khe
from . import uu_tien as uu_tien_mod

__all__ = ["bat", "doc_cai", "ghi_cai", "giu_nang", "boc_khau_nang", "cai_moc_tien_trinh",
           "nhip", "sinh_tien_trinh", "trang_thai_kenh", "bao_tri_kenh", "thu_nang", "uu_tien_khau",
           "ghi_so_ngay_luot", "LAN_API_KHOI_DAU", "TRAN_CHO_KHOA_GIAY", "MA_THOAT_HET_GIO"]

#: Làn API khởi đầu khi bật điều phối lần đầu (lộ trình: "khởi đầu 2 để đo").
LAN_API_KHOI_DAU = 2
#: Trần chờ khoá (làn API / khoá máy cũ) trước khi thoát mã 3 (lộ trình 1.4).
TRAN_CHO_KHOA_GIAY = 50 * 60
MA_THOAT_HET_GIO = 3
#: Van RAM: dưới ngần này KHÔNG sinh lượt mới (khớp `tu_chay.RAM_TRONG_TOI_THIEU_GB`).
RAM_TOI_THIEU_GB = 3.0
#: Máy NGHẸT: RAM trống dưới ngần này lúc đang có lượt chạy → tự hạ `lan_api` về 1.
RAM_NGHET_GB = 2.0
#: Không sinh lại CÙNG kênh sớm hơn ngần này phút, trừ khi lượt trước đã bàn
#: giao được video — lượt hỏng/thiếu nguồn không được đốt ví nghiên cứu mỗi 10'.
PHUT_GIAN_CACH_SINH_LAI = 55
#: Lượt DỞ (đã trót đổ tiền) được sinh lại sớm hơn — nhưng không dồn mỗi 10' vì
#: mỗi lần nhặt lại tính vào trần tự phục hồi L3 (3 lần) của `core.tu_chay`.
PHUT_GIAN_CACH_LUOT_DO = 20
#: Trần giữ khe "nang" (giây) theo việc — vượt thì chỉ GHI NHẬT KÝ, không giết.
HAN_GIU_NANG = {"dung": 120 * 60, "phu_de": 30 * 60, "giong_doc": 10 * 60,
                "qa_chep": 10 * 60, "nen": 10 * 60}
#: Khâu lớp B trong bảng việc `core.auto` → tên việc của khe.
KHAU_LOP_B = {"phu-de": "phu_de", "dung": "dung"}


# ── cài đặt ─────────────────────────────────────────────────────────────────


def _duong_cai(goc: str) -> str:
    return os.path.join(goc, "workspace", "cai-dat.json")


def doc_cai(goc: str) -> Dict[str, Any]:
    """`workspace/cai-dat.json` NGUYÊN VĂN (mọi khoá, kể cả khoá `core.cai_dat` chưa biết)."""
    try:
        with open(_duong_cai(goc), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_cai(goc: str, **thay: Any) -> None:
    """Gộp `thay` vào `cai-dat.json` — GIỮ mọi khoá khác, ghi nguyên tử."""
    du = doc_cai(goc)
    du.update(thay)
    duong = _duong_cai(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".dieu-phoi.tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=2)
    os.replace(tam, duong)


def bat(goc: str) -> bool:
    """Điều phối có đang BẬT không: máy VPS + `cai-dat.json: dieu_phoi: true`."""
    if not os.path.isfile(os.path.join(goc, "vps.json")):
        return False
    return doc_cai(goc).get("dieu_phoi") is True


# ── khe nang quanh khâu lớp B ───────────────────────────────────────────────


def _cau_huy(cancel: Optional[threading.Event]) -> Tuple[threading.Event, threading.Event]:
    """Event cho khe + Event "xong" — khe tỉnh ngay khi nút Dừng (`cancel`) bật,
    nhưng vượt trần giữ của khe KHÔNG bật `cancel` (chỉ ghi nhật ký)."""
    huy_khe = threading.Event()
    xong = threading.Event()
    if cancel is None:
        return huy_khe, xong

    def _canh() -> None:
        while not xong.is_set():
            if cancel.wait(1.0):
                huy_khe.set()
                return

    threading.Thread(target=_canh, daemon=True, name="dieu-phoi-cau-huy").start()
    return huy_khe, xong


def _minh_dang_giu_ca_may(goc: str) -> bool:
    """Chính tiến trình này đang giữ `.khoa-may` theo lối CŨ (cả lượt) — ví dụ
    lượt `--tat-ca` khởi động TRƯỚC khi điều phối được bật. Khi đó khe "nang"
    coi như đã có trong tay: xin thêm lần nữa là TỰ KHOÁ CHẾT (khe thấy PID
    người giữ còn sống — chính mình — và chờ mãi)."""
    try:
        with open(khe.duong_khoa_nang(goc), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        # khoá do chính `core.khe` tạo (mang "nguon": "khe") KHÔNG tính — đó là
        # khe đang giữ thật, xin thêm phải xếp hàng như mọi việc khác.
        return (int((du or {}).get("pid") or 0) == os.getpid()
                and (du or {}).get("nguon") != "khe")
    except (OSError, ValueError, TypeError, AttributeError):
        return False


@contextlib.contextmanager
def giu_nang(goc: str, viec: str, *, kenh: str = "", uu_tien: float = uu_tien_mod.P4,
             cancel: Optional[threading.Event] = None,
             ghi: Optional[Callable[[str], None]] = None) -> Iterator[Optional[threading.Event]]:
    """Giữ khe "nang" quanh MỘT khâu lớp B. Điều phối tắt → không làm gì.

    Xếp hàng theo `uu_tien` (số nhỏ = gấp). Bấm Dừng lúc đang xếp hàng → ném
    `core.auto.Cancelled` (đúng lối nút Dừng của dây chuyền)."""
    if not bat(goc) or _minh_dang_giu_ca_may(goc):
        yield None
        return
    huy_khe, xong = _cau_huy(cancel)
    bat_dau = time.time()

    def _bao_cho() -> None:
        # (vá 29/09/2026 sau sự cố tự khoá chết 18:36→19:53) — "đang chờ AI, việc
        # gì, từ mấy giờ" sau 20 giây rồi MỖI 5 PHÚT, không im lặng vô hạn; đọc
        # được cả khoá định dạng cũ `{pid, bat_dau}` (trước in "đang bận: ?").
        cho = 20.0
        while not xong.wait(cho):
            cho = 300.0
            if ghi is None:
                continue
            try:
                ai = khe.trang_thai(goc).get("nang")
                ghi("  [KHE] chờ khe máy nặng cho {0} ({1:.0f}' rồi) — đang giữ: {2}".format(
                    viec, (time.time() - bat_dau) / 60.0, khe.mo_ta_nguoi_giu(ai)))
            except Exception:  # noqa: BLE001
                pass

    threading.Thread(target=_bao_cho, daemon=True, name="dieu-phoi-bao-cho").start()
    try:
        with khe.giu(goc, khe.LOP_NANG, viec=viec, kenh=kenh, uu_tien=uu_tien,
                     han_giay=HAN_GIU_NANG.get(viec), huy=huy_khe,
                     cho_toi_da=PHUT_CHO_NANG_TOI_DA * 60) as h:
            xong.set()
            cho = (time.time() - bat_dau) / 60.0
            if ghi is not None and cho >= 1.0:
                ghi("  [KHE] được khe máy nặng cho {0} sau {1:.0f} phút chờ.".format(viec, cho))
            yield h
    except khe.KheDaHuy:
        from .auto import Cancelled  # noqa: PLC0415

        raise Cancelled()
    except khe.KheHetGio:
        if ghi is not None:
            try:
                ghi("  [KHE] chờ khe máy nặng cho {0} quá {1} phút — khâu này dừng, lượt sau chạy "
                    "tiếp (đang giữ: {2}).".format(viec, PHUT_CHO_NANG_TOI_DA,
                                                   khe.mo_ta_nguoi_giu(khe.trang_thai(goc).get("nang"))))
            except Exception:  # noqa: BLE001
                pass
        raise
    finally:
        xong.set()


#: Trần chờ khe "nang" (29/09/2026): hết trần → `KheHetGio`, khâu hỏng, lượt kế
#: nhặt lại chạy tiếp — không bao giờ đứng im vô hạn. Dài nhất hợp lệ: 3 kênh
#: xếp hàng dựng (~30'/kênh) + phụ đề.
PHUT_CHO_NANG_TOI_DA = 120


@contextlib.contextmanager
def thu_nang(goc: str, viec: str, *, kenh: str = "") -> Iterator[bool]:
    """Thử giữ khe "nang" MỘT LẦN (không xếp hàng) cho việc NỀN bỏ qua được
    (vòng học/kho nhạc): yield True nếu được (hoặc điều phối tắt), False nếu
    khe đang bận — nơi gọi bỏ qua lượt này, không để làn API ngồi chờ dựng."""
    if not bat(goc) or _minh_dang_giu_ca_may(goc):
        yield True
        return
    phien = khe.thu_giu(goc, khe.LOP_NANG, viec=viec, kenh=kenh, uu_tien=uu_tien_mod.P4,
                        han_giay=HAN_GIU_NANG.get(viec))
    if phien is None:
        yield False
        return
    try:
        yield True
    finally:
        phien.nha()


def uu_tien_khau(goc: str, ma_kenh: str, viec: str,
                 bay_gio: Optional[_dt.datetime] = None) -> int:
    """P2 nếu khe công khai trống sớm nhất của kênh còn < 24h, không thì P4."""
    try:
        from . import xep_lich  # noqa: PLC0415
        from .kenh import doc_kenh  # noqa: PLC0415

        bay_gio = bay_gio or _dt.datetime.now()
        k = doc_kenh(goc, ma_kenh)
        ngay, gio = xep_lich.khe_trong_som_nhat(goc, ma_kenh, k, bay_gio=bay_gio, bien_gio=0)
        gio_con = None
        if ngay:
            moc = _dt.datetime.strptime(ngay + " " + gio, "%d/%m/%Y %H:%M")
            gio_con = (moc - bay_gio).total_seconds() / 3600.0
        ten = uu_tien_mod.VIEC_PHU_DE if viec == "phu_de" else uu_tien_mod.VIEC_DUNG
        return uu_tien_mod.tinh_uu_tien(ten, gio_con_lai=gio_con)
    except Exception:  # noqa: BLE001 — tính ưu tiên hỏng thì coi như không gấp
        return uu_tien_mod.P4


def boc_khau_nang(viec: Dict[str, Callable[..., Any]], *, goc: str, kenh: str,
                  cancel: Optional[threading.Event] = None,
                  ghi: Optional[Callable[[str], None]] = None) -> Dict[str, Callable[..., Any]]:
    """Bọc khâu lớp B (`KHAU_LOP_B`) của bảng việc `core.auto` bằng khe "nang".
    Sửa tại chỗ + trả lại chính bảng; giữ nguyên thuộc tính hàm gốc."""
    if not bat(goc):
        return viec

    def boc_mot(ma: str, ten_viec: str, lam: Callable[..., Any]) -> Callable[..., Any]:
        def boc(luot, tt):
            with giu_nang(goc, ten_viec, kenh=kenh, uu_tien=uu_tien_khau(goc, kenh, ten_viec),
                          cancel=cancel, ghi=ghi):
                return lam(luot, tt)

        boc.__name__ = getattr(lam, "__name__", "boc_" + ma)
        boc.__dict__.update(getattr(lam, "__dict__", {}) or {})
        return boc

    for ma, ten_viec in KHAU_LOP_B.items():
        lam = viec.get(ma)
        if lam is not None:
            viec[ma] = boc_mot(ma, ten_viec, lam)
    return viec


# ── móc trong tiến trình lượt điều phối (so_job_chung, bang_thong, _noi_mp3) ─


_MOC = {"da_cai": False}


class _ClientSoChung:
    """Bọc `client` cho `so_job_chung.lay`: xin van nhịp như `SoTheoDoi`, đổi
    trang SDK về dict thuần JSON được (đệm ghi ra đĩa)."""

    def __init__(self, bc: Any, ak: Any) -> None:
        self._bc = bc
        self._ak = ak
        self.jobs = self

    def list(self, **kw: Any) -> Dict[str, Any]:  # noqa: A003 — đúng tên SDK
        self._ak.xin_nhip(self._bc.on_log, ngu=self._bc.ngu)
        trang = self._ak._goi_dict(self._bc.client.jobs.list(**kw))  # noqa: SLF001
        trang = dict(trang)
        trang["data"] = [self._ak._goi_dict(m) for m in (trang.get("data") or [])]  # noqa: SLF001
        return json.loads(json.dumps(trang, default=str))


def cai_moc_tien_trinh(goc: str, *, kenh: str = "",
                       cancel: Optional[threading.Event] = None,
                       ghi: Optional[Callable[[str], None]] = None) -> bool:
    """Cắm ba móc vào `core.auto_khau` cho TIẾN TRÌNH NÀY. Gọi một lần, trước
    sản xuất, chỉ ở lượt điều phối. Trả True nếu vừa cắm."""
    if _MOC["da_cai"] or not bat(goc):
        return False
    from . import auto_khau as ak  # noqa: PLC0415
    from . import bang_thong, so_job_chung  # noqa: PLC0415

    # 1) sổ job TOÀN MÁY — một tiến trình hỏi, mọi tiến trình đọc đệm.
    def _mot_luot_chung(self) -> None:
        if not self.hoi_ca_luot:
            return
        con = set(self._con_cho())
        if not con:
            return
        try:
            dem = so_job_chung.lay(goc, _ClientSoChung(self._bc, ak),
                                   so_moi_trang=ak.SO_MOI_TRANG,
                                   so_trang_toi_da=ak.TRANG_MOI_LUOT, cho_toi_da=20.0)
            for ma, goi in (dem.get("jobs") or {}).items():
                if ma in con:
                    self._nhan(ma, dict(goi))
        except Exception as loi:  # noqa: BLE001 — cùng lưới an toàn của bản gốc
            self._hong_lien += 1
            if self._hong_lien >= 2:
                self.hoi_ca_luot = False
                self._bc.ghi("  (sổ job chung hỏng — quay về hỏi từng cái: {0})".format(
                    str(loi)[:70]))
            return
        self._hong_lien = 0

    ak.SoTheoDoi._mot_luot = _mot_luot_chung  # type: ignore[assignment]

    # 2) suất tải kết quả về (≤ tran_bang_thong toàn máy, dừng khi đang tải lên).
    tai_goc = ak._tai_ket_qua_mot_lan  # noqa: SLF001

    def _tai_co_suat(bc, goi, chi_so, dich):
        with bang_thong.giu(goc, huy=None, cho_toi_da=45 * 60):
            return tai_goc(bc, goi, chi_so, dich)

    ak._tai_ket_qua_mot_lan = _tai_co_suat  # noqa: SLF001

    # 3) đoạn nối mp3 cục bộ của giọng đọc — khe nang.
    noi_goc = ak._noi_mp3  # noqa: SLF001

    def _noi_co_khe(bc, manh, dich, nghi=None):
        with giu_nang(goc, "giong_doc", kenh=kenh, uu_tien=uu_tien_mod.P2,
                      cancel=cancel, ghi=ghi):
            return noi_goc(bc, manh, dich, nghi=nghi)

    ak._noi_mp3 = _noi_co_khe  # noqa: SLF001
    _MOC["da_cai"] = True
    if ghi is not None:
        ghi("  [ĐIỀU PHỐI] lượt chạy song song — sổ job chung, suất tải về chung, khe máy nặng cho phụ đề/dựng/nối giọng/QA.")
    return True


# ── trạng thái kênh ────────────────────────────────────────────────────────


def _duong_trang_thai(goc: str) -> str:
    return os.path.join(goc, "workspace", "khe", "dieu-phoi.json")


def _doc_json(duong: str) -> Dict[str, Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_json(duong: str, du: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = "{0}.{1}.tam".format(duong, os.getpid())
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def _khoa_kenh_song(goc: str, ma: str) -> Optional[Dict[str, Any]]:
    from .kenh import duong_kenh  # noqa: PLC0415

    du = _doc_json(os.path.join(duong_kenh(goc, ma), "tu-chay", ".khoa"))
    try:
        pid = int(du.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    if pid and khe.pid_con_song(pid):
        return du
    return None


def _dem_ban_giao_hom_nay(goc: str, ma: str, ngay_str: str) -> int:
    from . import tu_chay  # noqa: PLC0415

    bc = tu_chay._doc_bao_cao_ngay(goc, ma, ngay_str)  # noqa: SLF001
    return sum(1 for r in bc.get("runs") or [] if (r.get("ban_giao") or {}).get("da_ban_giao"))


def _co_luot_do(goc: str, ma: str, hom_nay: _dt.date) -> bool:
    """Có lượt dở trong sổ 7 ngày (chỉ ĐỌC — không nhận nuôi như `_tim_run_chua_xong`)."""
    from . import auto, tu_chay  # noqa: PLC0415

    for i in range(tu_chay.SO_NGAY_QUET_LUOT_CHUA_XONG):
        ngay_str = (hom_nay - _dt.timedelta(days=i)).isoformat()
        for r in tu_chay._doc_bao_cao_ngay(goc, ma, ngay_str).get("runs") or []:  # noqa: SLF001
            if r.get("bo") or r.get("tham_chieu_ma_luot") or not r.get("ma_luot"):
                continue
            if not (r.get("san_xuat") or {}).get("da_chay"):
                continue  # lượt chưa từng chạy phải qua cửa như lượt mới
            luot = auto.doc_luot(auto.duong_luot(goc, ma, str(r["ma_luot"])))
            if luot is None or not tu_chay._coi_nhu_da_xong(luot):  # noqa: SLF001
                return True
    return False


def _chi_hom_nay(goc: str, ma: str, ngay_str: str) -> Tuple[int, int]:
    """(số lượt trong sổ hôm nay, tổng ước chi đã sản xuất hôm nay — đồng)."""
    from . import tu_chay  # noqa: PLC0415

    bc = tu_chay._doc_bao_cao_ngay(goc, ma, ngay_str)  # noqa: SLF001
    runs = bc.get("runs") or []
    tien = sum(int((r.get("ngan_sach") or {}).get("uoc_tinh_vnd") or 0)
               for r in runs if (r.get("san_xuat") or {}).get("da_chay"))
    return len(runs), tien


def _chi_thang(goc: str, ma: str, hom_nay: _dt.date) -> int:
    tong = 0
    d = hom_nay.replace(day=1)
    while d <= hom_nay:
        tong += _chi_hom_nay(goc, ma, d.isoformat())[1]
        d += _dt.timedelta(days=1)
    return tong


def trang_thai_kenh(goc: str, ma: str, *, bay_gio: Optional[_dt.datetime] = None
                    ) -> Dict[str, Any]:
    """Một kênh có nên được sinh lượt sản xuất bây giờ không (CHỈ ĐỌC).

    Trả `{"ma", "chay": bool, "diem": số (nhỏ = cần trước), "ly_do": câu,
    "kho": ..., "uoc_vnd": ...}`."""
    from . import tu_chay, xep_lich  # noqa: PLC0415
    from .kenh import doc_kenh  # noqa: PLC0415
    from .money import micro_to_vnd  # noqa: PLC0415
    from .pricing import DEFAULT_PRICES  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    ngay_str = bay_gio.date().isoformat()
    ra: Dict[str, Any] = {"ma": ma, "chay": False, "diem": 0.0, "ly_do": ""}
    try:
        k = doc_kenh(goc, ma)
    except Exception as loi:  # noqa: BLE001
        ra["ly_do"] = "không đọc được kênh: {0}".format(str(loi)[:80])
        return ra
    if not k.tu_chay:
        ra["ly_do"] = "tu_chay tắt"
        return ra
    dang = _khoa_kenh_song(goc, ma)
    if dang is not None:
        ra.update(dang_chay=True, pid=dang.get("pid"),
                  ly_do="đang chạy (PID {0})".format(dang.get("pid")))
        return ra
    so_luot, da_chi = _chi_hom_nay(goc, ma, ngay_str)
    try:
        uoc = int(micro_to_vnd(tu_chay._uoc_chi_phi_micro(k, DEFAULT_PRICES)))  # noqa: SLF001
    except Exception:  # noqa: BLE001
        uoc = 0
    ra.update(uoc_vnd=uoc, da_chi_hom_nay=da_chi, so_luot_hom_nay=so_luot)
    if _co_luot_do(goc, ma, bay_gio.date()):
        ra.update(chay=True, diem=-1000.0, ly_do="lượt dở — chạy tiếp")
        return ra
    if so_luot >= xep_lich.tran_video_ngay(k):
        ra["ly_do"] = "đã đủ {0} lượt hôm nay".format(so_luot)
        return ra
    han = int(k.ngan_sach_ngay or 0)
    if han <= 0 or da_chi + uoc > han:
        ra["ly_do"] = "ngân sách ngày {0}/{1}".format(da_chi, han)
        return ra
    try:
        mo, ly_do, tt = tu_chay._cua_so_san_xuat(goc, ma, k, bay_gio=bay_gio)  # noqa: SLF001
    except Exception as loi:  # noqa: BLE001
        ra["ly_do"] = "cửa sản xuất hỏng: {0}".format(str(loi)[:80])
        return ra
    ra["kho"] = {x: tt.get(x) for x in ("kho_dem", "kho_dem_can", "so_video_dang_cho")}
    if not mo:
        ra["ly_do"] = ly_do
        return ra
    thieu = (int(tt.get("kho_dem_can") or 0) - int(tt.get("kho_dem") or 0)
             if tt.get("che_do") == "kho_dem" else 1)
    ra.update(chay=True, diem=-float(thieu), ly_do="thiếu kho đệm {0}".format(thieu))
    return ra


# ── sinh lượt ──────────────────────────────────────────────────────────────


def _pythonw(goc: str) -> str:
    try:
        from .loi_tat import _pythonw_cho  # noqa: PLC0415

        return _pythonw_cho(goc)
    except Exception:  # noqa: BLE001
        return sys.executable or "pythonw"


def sinh_tien_trinh(goc: str, ma: str, *, popen: Optional[Callable[..., Any]] = None) -> int:
    """Mở `tu_chay.py --kenh <ma> --tu-dieu-phoi` TÁCH RỜI (sống tiếp khi lịch
    Windows thoát). Nhật ký tiến trình: `workspace/tu-chay/dieu-phoi-<ma>.log`."""
    lenh = [_pythonw(goc), os.path.join(goc, "tu_chay.py"), "--kenh", ma, "--tu-dieu-phoi"]
    nhat_ky = os.path.join(goc, "workspace", "tu-chay", "dieu-phoi-{0}.log".format(ma))
    os.makedirs(os.path.dirname(nhat_ky), exist_ok=True)
    try:
        if os.path.getsize(nhat_ky) > 5 * 1024 * 1024:
            os.remove(nhat_ky)
    except OSError:
        pass
    co = 0
    if os.name == "nt":
        co = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED | NEW_GROUP | NO_WINDOW
    moi_truong = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    mo = popen or subprocess.Popen
    with open(nhat_ky, "a", encoding="utf-8") as tep:
        tep.write("\n[{0}] điều phối sinh lượt kênh {1}\n".format(
            time.strftime("%Y-%m-%d %H:%M:%S"), ma))
        tep.flush()
        for them in ((0x01000000,) if os.name == "nt" else ()) + (0,):  # BREAKAWAY nếu job cho
            try:
                p = mo(lenh, cwd=goc, stdout=tep, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL, creationflags=co | them, env=moi_truong,
                       close_fds=True)
                return int(getattr(p, "pid", 0) or 0)
            except OSError:
                if them == 0:
                    raise
    return 0


def _khoa_nhip(goc: str) -> Optional[str]:
    duong = os.path.join(goc, "workspace", "khe", "dieu-phoi.lock")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _lan in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as tep:
                json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
            return duong
        except FileExistsError:
            du = _doc_json(duong)
            try:
                pid = int(du.get("pid") or 0)
            except (TypeError, ValueError):
                pid = 0
            tuoi = time.time() - float(du.get("bat_dau") or 0)
            if pid and khe.pid_con_song(pid) and tuoi < 600:
                return None
            khe.xoa_tep_ben_vung(duong)
    return None


def _dang_giu_api(goc: str) -> int:
    return sum(1 for x in (khe.trang_thai(goc).get("api") or []) if x)


def _ghi_log(goc: str, dong: str) -> None:
    try:
        from .tu_chay import bo_log_tat_ca  # noqa: PLC0415

        bo_log_tat_ca(goc, in_console=False)("[ĐIỀU PHỐI] " + dong)
    except Exception:  # noqa: BLE001
        pass


def nhip(goc: str, *, bay_gio: Optional[_dt.datetime] = None,
         sinh: Optional[Callable[[str, str], int]] = None,
         ram: Optional[float] = None, dia_gb: Optional[float] = None,
         log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """MỘT nhịp điều phối (lịch `ShopAPI-DieuPhoi` mỗi 10', và cuối `--tat-ca`).

    Đọc kho đệm/lượt dở từng kênh, còn làn API trống + RAM ≥ 3GB + đĩa + ngân
    sách (kênh và máy) → sinh lượt cho kênh cần nhất. Trả bản tóm tắt nhịp
    (cũng ghi `workspace/khe/dieu-phoi.json`)."""
    ghi = log or (lambda d: _ghi_log(goc, d))
    if not bat(goc):
        return {"bat": False}
    khoa = _khoa_nhip(goc)
    if khoa is None:
        return {"bat": True, "bo_qua": "nhịp khác đang chạy"}
    try:
        return _nhip_trong_khoa(goc, bay_gio=bay_gio or _dt.datetime.now(),
                                sinh=sinh or sinh_tien_trinh, ram=ram, dia_gb=dia_gb, ghi=ghi)
    finally:
        khe.xoa_tep_ben_vung(khoa)


def _nhip_trong_khoa(goc: str, *, bay_gio: _dt.datetime, sinh: Callable[[str, str], int],
                     ram: Optional[float], dia_gb: Optional[float],
                     ghi: Callable[[str], None]) -> Dict[str, Any]:
    from . import tu_chay  # noqa: PLC0415
    from .kenh import doc_kenh  # noqa: PLC0415

    cai = doc_cai(goc)
    trang = _doc_json(_duong_trang_thai(goc))
    sinh_cu: Dict[str, Any] = dict(trang.get("sinh") or {})
    ngay_str = bay_gio.date().isoformat()
    ram_trong = ram if ram is not None else khe.ram_gb()[0]
    lan = khe.so_lan_api(goc)
    danh_sach = tu_chay.kenh_tu_chay(goc)
    cac = [trang_thai_kenh(goc, ma, bay_gio=bay_gio) for ma in danh_sach]
    so_dang = sum(1 for c in cac if c.get("dang_chay"))
    # lượt vừa sinh nhưng chưa kịp giữ khoá kênh (khởi động Python mất vài giây)
    for ma, m in sinh_cu.items():
        if not any(c["ma"] == ma and c.get("dang_chay") for c in cac):
            if khe.pid_con_song(int(m.get("pid") or 0)) and time.time() - float(m.get("luc") or 0) < 300:
                so_dang += 1
                for c in cac:
                    if c["ma"] == ma:
                        c.update(chay=False, ly_do="vừa sinh, đang khởi động")
    ra: Dict[str, Any] = {"bat": True, "luc": bay_gio.isoformat(timespec="seconds"),
                          "ram_trong_gb": ram_trong, "lan_api": lan, "so_dang": so_dang,
                          "dang_giu_api": _dang_giu_api(goc), "kenh": cac, "sinh_moi": []}

    # van máy nghẹt → hạ làn API về 1 (ghi rõ)
    if ram_trong is not None and ram_trong < RAM_NGHET_GB and so_dang >= 1 and lan > 1:
        ghi_cai(goc, lan_api=1)
        ghi("⚠ MÁY NGHẸT: RAM trống {0:.1f} GB < {1:.0f} GB khi đang có {2} lượt — tự hạ lan_api {3} → 1."
            .format(ram_trong, RAM_NGHET_GB, so_dang, lan))
        try:
            from . import bao_dong  # noqa: PLC0415

            bao_dong.bao_dong("dieu_phoi_nghet", "Máy nghẹt RAM — tự hạ số lượt song song về 1.",
                              "RAM trống {0:.1f} GB khi đang chạy {1} lượt sản xuất.".format(
                                  ram_trong, so_dang), goc=goc, muc=bao_dong.MUC_NHAC)
        except Exception:  # noqa: BLE001
            pass
        lan = 1
        ra["lan_api"] = 1
        ra["ha_lan"] = True

    trong = max(0, lan - max(so_dang, ra["dang_giu_api"]))
    ra["lan_trong"] = trong
    chan = ""
    if trong <= 0:
        chan = "hết làn API ({0}/{1} đang chạy)".format(so_dang, lan)
    elif ram_trong is not None and ram_trong < RAM_TOI_THIEU_GB:
        chan = "RAM trống {0:.1f} GB < {1:.0f} GB".format(ram_trong, RAM_TOI_THIEU_GB)
    else:
        con_gb = dia_gb if dia_gb is not None else tu_chay._dung_luong_trong_gb(goc)  # noqa: SLF001
        can_gb = 0.0
        for c in cac:
            if c.get("chay"):
                try:
                    can_gb = max(can_gb, tu_chay._uoc_dung_luong_video_gb(doc_kenh(goc, c["ma"])))  # noqa: SLF001
                except Exception:  # noqa: BLE001
                    pass
        du_dia, ly_do_dia = tu_chay._kiem_dia(con_gb, can_gb or 3.0)  # noqa: SLF001
        if not du_dia:
            chan = "đĩa: " + ly_do_dia
    if not chan:
        # trần MÁY (Bước D): video/ngày, ngân sách ngày, ngân sách tháng
        tong_luot = sum(int(c.get("so_luot_hom_nay") or 0) for c in cac)
        tong_chi = sum(int(c.get("da_chi_hom_nay") or 0) for c in cac)
        v_may = int(cai.get("video_toi_da_ngay_may") or 0)
        ns_may = int(cai.get("ngan_sach_ngay_may") or 0)
        nst_may = int(cai.get("ngan_sach_thang_may") or 0)
        if v_may > 0 and tong_luot >= v_may:
            chan = "trần máy {0} lượt/ngày".format(v_may)
        elif ns_may > 0 and tong_chi >= ns_may:
            chan = "trần ngân sách ngày máy {0}/{1}".format(tong_chi, ns_may)
        elif nst_may > 0:
            thang = sum(_chi_thang(goc, ma, bay_gio.date()) for ma in danh_sach)
            ra["chi_thang"] = thang
            if thang >= nst_may:
                chan = "trần ngân sách tháng máy {0}/{1}".format(thang, nst_may)
    ung_vien = sorted((c for c in cac if c.get("chay")), key=lambda c: (c["diem"], c["ma"]))
    # Van VÍ (30/09/2026, `core/van_vi.py`): ví < ước 1 video x 1,5 → không sinh lượt
    # MỚI; lượt đang dở (điểm <= -1000) vẫn được sinh để làm nốt nếu ví ≥ ước 1
    # video. Không đọc được số dư → không chặn. Ví được nạp thì nhịp sau tự mở lại.
    if not chan and ung_vien:
        try:
            from . import van_vi  # noqa: PLC0415

            duoc_moi, ly_vi, _dg = van_vi.cho_phep_mo_luot(goc, None, dang_do=False)
            if not duoc_moi:
                duoc_do, _ly_do_vi, _dg2 = van_vi.cho_phep_mo_luot(goc, None, dang_do=True)
                ung_vien = [c for c in ung_vien if duoc_do and c["diem"] <= -1000]
                if not ung_vien:
                    chan = "ví: " + ly_vi
        except Exception:  # noqa: BLE001 — van hỏng không được chặn cả điều phối
            pass
    # giãn cách: không sinh lại cùng kênh < 55' trừ khi lượt trước đã bàn giao được video
    loc: List[Dict[str, Any]] = []
    for c in ung_vien:
        m = sinh_cu.get(c["ma"]) or {}
        tu_luc = time.time() - float(m.get("luc") or 0)
        gian_cach = (PHUT_GIAN_CACH_LUOT_DO if c["diem"] <= -1000 else PHUT_GIAN_CACH_SINH_LAI) * 60
        if m and tu_luc < gian_cach:
            if _dem_ban_giao_hom_nay(goc, c["ma"], ngay_str) <= int(m.get("ban_giao") or 0):
                c["ly_do"] = "vừa chạy {0:.0f}' trước chưa ra video — giãn cách".format(tu_luc / 60)
                continue
        loc.append(c)
    ra["chan"] = chan
    if not chan:
        for c in loc[:trong]:
            try:
                pid = sinh(goc, c["ma"])
            except Exception as loi:  # noqa: BLE001
                ghi("sinh lượt {0} hỏng: {1}".format(c["ma"], str(loi)[:150]))
                continue
            sinh_cu[c["ma"]] = {"pid": pid, "luc": time.time(),
                                "ban_giao": _dem_ban_giao_hom_nay(goc, c["ma"], ngay_str)}
            ra["sinh_moi"].append({"kenh": c["ma"], "pid": pid, "ly_do": c["ly_do"]})
            ghi("sinh lượt {0} (PID {1}) — {2}; làn {3}/{4}, RAM trống {5}.".format(
                c["ma"], pid, c["ly_do"], so_dang + len(ra["sinh_moi"]), lan,
                "?" if ram_trong is None else "{0:.1f} GB".format(ram_trong)))
    if not ra["sinh_moi"]:
        tom = "; ".join("{0}: {1}".format(c["ma"], c.get("ly_do") or "-") for c in cac)
        # Log gọn (29/09/2026): chỉ in khi trạng thái (lý do chặn + từng kênh) ĐỔI
        # — trước đây nhịp 10' in lại y một câu "hết làn API" suốt nhiều giờ.
        dau = chan + "|" + tom
        if dau != trang.get("dau_cuoi"):
            ghi("không sinh lượt mới{0} — {1}".format((" (" + chan + ")") if chan else "", tom))
        ra["tom_cuoi"] = tom
        ra["dau_cuoi"] = dau
    ra["sinh"] = {ma: m for ma, m in sinh_cu.items()
                  if time.time() - float(m.get("luc") or 0) < 2 * 86400}
    try:
        _ghi_json(_duong_trang_thai(goc), ra)
    except OSError:
        pass
    # Bước D: công suất 24h (khe nặng %, làn API, còn dư) cho Bảng điều khiển.
    try:
        from . import cong_suat  # noqa: PLC0415

        cong_suat.ghi_hien_tai(goc)
    except Exception:  # noqa: BLE001 — phần phụ
        pass
    return ra


# ── --tat-ca ở chế độ điều phối: bảo trì + trạng thái, KHÔNG sản xuất ─────


def bao_tri_kenh(goc: str, ma: str, *, on_log: Optional[Callable[[str], None]] = None,
                 bay_gio: Optional[_dt.datetime] = None, **_bo: Any) -> Dict[str, Any]:
    """Thay `chay_mot_ngay` trong `--tat-ca` khi điều phối BẬT: việc rẻ, chỉ đĩa
    (tự nhận video đã đăng, xếp lại gói lỡ lịch) khi kênh không có lượt đang
    chạy; trả một dòng trạng thái cho sổ ngày. Sản xuất do `nhip()` sinh."""
    from . import tu_chay, tu_nhan_da_dang, xep_lich  # noqa: PLC0415
    from .kenh import doc_kenh  # noqa: PLC0415

    log = on_log or (lambda _d: None)
    tt = trang_thai_kenh(goc, ma, bay_gio=bay_gio)
    if not tt.get("dang_chay"):
        ok_khoa, _ly = tu_chay._giu_khoa(goc, ma)  # noqa: SLF001
        if ok_khoa:
            try:
                try:
                    tu_nhan_da_dang.tu_nhan_video_da_dang(goc, ma, bay_gio=bay_gio, on_log=log)
                except Exception as loi:  # noqa: BLE001
                    log("  ({0}: tự nhận đã đăng hỏng: {1})".format(ma, str(loi)[:120]))
                try:
                    k = doc_kenh(goc, ma)
                    for ma_goi, cu, moi in xep_lich.xep_lai_goi_lo_lich(goc, ma, k, bay_gio=bay_gio):
                        log("[XẾP LẠI LỊCH] {0}: lỡ lịch {1} (chưa tải lên) — dời sang {2}."
                            .format(ma_goi, cu, moi))
                except Exception as loi:  # noqa: BLE001
                    log("  ({0}: xếp lại lịch hỏng: {1})".format(ma, str(loi)[:120]))
            finally:
                tu_chay._nha_khoa(goc, ma)  # noqa: SLF001
    if tt.get("dang_chay"):
        chu = "đang sản xuất ở lượt tách rời (PID {0})".format(tt.get("pid"))
    elif tt.get("chay"):
        chu = "chờ làn điều phối — {0}".format(tt.get("ly_do"))
    else:
        chu = tt.get("ly_do") or "không có việc"
    return {"kenh": ma, "ok": True, "cho_nguoi": False,
            "tom_tat": "{0}: [điều phối] {1}".format(ma, chu), "loi": "", "nhat_ky": []}


def ghi_so_ngay_luot(goc: str, ket_qua: List[Dict[str, Any]], *, tong_uoc_vnd: int = 0) -> None:
    """Lượt tách rời xong → nối một lượt vào sổ ngày dùng chung (có khoá ngắn,
    hai lượt cùng xong không mất dòng của nhau)."""
    from . import tu_chay  # noqa: PLC0415

    duong = os.path.join(goc, "workspace", "tu-chay", ".so-ngay.lock")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _lan in range(60):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(duong) > 120:
                    khe.xoa_tep_ben_vung(duong)
                    continue
            except OSError:
                continue
            time.sleep(0.5)
    try:
        ngay = _dt.date.today()
        tu_chay.ghi_bao_cao_tat_ca(goc, ngay.isoformat(), {
            "luc": _dt.datetime.now().isoformat(timespec="seconds"), "che_do": "that · điều phối",
            "ket_qua": ket_qua, "tong_uoc_vnd": int(tong_uoc_vnd or 0),
            "dia_con_trong_gb": tu_chay._dung_luong_trong_gb(goc)})  # noqa: SLF001
    finally:
        khe.xoa_tep_ben_vung(duong)
