# -*- coding: utf-8 -*-
"""core/ben_bi.py — "Bền bỉ": những mảnh TỰ PHỤC HỒI dùng chung cho người gác
tổng (`core.gac_tong`), bộ điều phối (`tu_chay.py --dieu-phoi`) — kiểm toán
"chạy 365 ngày không người, không chết im lặng" (06/10/2026).

Mỗi mảnh trả lời đúng 3 câu của CLAUDE.md mục 6 (tự thử lại thế nào / kẹt thì
có bị phát hiện không / việc người phải làm có hiện ra không):

1. :func:`don_khoa_chet_an_toan` — dọn tệp khoá `{pid, bat_dau}` trỏ PID đã
   chết, NHƯNG chỉ khi (a) nội dung tệp NGAY LÚC XOÁ vẫn đúng PID/mốc đã thấy
   lúc chụp, (b) PID vẫn chết, (c) khoá đã đủ tuổi. Bản cũ trong `gac_tong.
   tu_sua` xoá theo ẢNH CHỤP đầu lượt — giữa lúc chụp và lúc xoá (gác tổng
   còn chạy chốt ví, QA kiểm lại gói bằng FFmpeg… có khi vài phút) một tiến
   trình MỚI có thể đã giành khoá; xoá theo ảnh cũ là xoá khoá của người đang
   sống → hai việc nặng chạy song song (đúng thứ khe "nang" sinh ra để chặn).
   Xoá bằng "đổi tên nguyên tử rồi đọc lại": lỡ cuỗm khoá người sống thì trả
   lại chỗ cũ.
2. :func:`ghi_nhip` / :func:`ghi_loi_vong` / :func:`hen_gio_tu_thoat` — nhịp
   tim + sổ "sập vòng" + hạn giờ cứng cho một lượt lịch. Lịch Windows đặt
   `MultipleInstancesPolicy=IgnoreNew` và hạn chạy mặc định 72 giờ: MỘT lượt
   gác tổng treo (git/PowerShell/mạng) là mọi lượt 15' sau bị BỎ QUA suốt 3
   ngày, không ai biết. Hạn giờ cứng tự thoát để lượt sau chạy được.
3. :func:`kiem_khong_san_xuat` — "cả máy 36 giờ không làm ra gói video nào
   mới" (một trong hai điều kiện THẬT SỰ mất tiền; điều kiện kia — kênh 48 giờ
   không có video mới — là `gac_tong._kiem_khong_video_moi`).
4. :func:`hoi_sinh_may_nen` — agent `vm/agent.py` chỉ được giao diện Qt nuôi
   (`core.giam_sat_vm`). Giao diện chết (sập, ai đó đóng, khởi động lại máy
   mà giao diện mở hỏng) là agent chết theo mà không ai mở lại: không tải lên,
   không đăng. Gác tổng (chạy riêng bằng lịch) mở lại giao diện; vẫn không
   lên thì mở thẳng agent.
5. :func:`canh_gac_tong` — "ai gác người gác": bộ điều phối (lịch riêng, 10')
   thấy nhịp tim gác tổng cũ > 60' thì đăng ký lại lịch gác tổng nếu mất và
   báo động.

Không gọi mạng (trừ `core.bao_dong`, vốn tự nuốt lỗi), không tốn ví. Mọi hàm
nhận seam để test bằng tmp_path, không chạm tiến trình/cổng thật.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

__all__ = [
    "TUOI_KHOA_CHET_TOI_THIEU_GIAY", "NGUONG_KHONG_SAN_XUAT_GIO", "NGUONG_LAP_BAO_TIEN_GIO",
    "NGUONG_NHIP_AGENT_CHET_PHUT", "NHIP_HOI_SINH_PHUT", "NGUONG_GAC_TONG_IM_PHUT",
    "don_khoa_chet_an_toan", "cho_lui_dan",
    "duong_nhip", "ghi_nhip", "doc_nhip", "ghi_loi_vong", "xoa_loi_vong", "hen_gio_tu_thoat",
    "kiem_khong_san_xuat", "kiem_agent_sap", "hoi_sinh_may_nen", "canh_gac_tong",
]

#: Khoá trỏ PID chết phải "già" ít nhất chừng này mới được gác tổng dọn. Không
#: mất gì khi đợi: người THẬT SỰ cần khe (`core.khe._khe_trong`) tự giành lại
#: khoá PID chết ngay lúc xin — gác tổng chỉ dọn cho gọn khi không ai xin.
TUOI_KHOA_CHET_TOI_THIEU_GIAY = 10 * 60.0

#: "Cả máy không làm ra gói video mới nào" quá ngần này giờ → báo KHẨN. Lịch
#: 1 video/kênh/ngày: 36 giờ = đã lỡ trọn một ngày mà nửa ngày sau vẫn chưa có.
NGUONG_KHONG_SAN_XUAT_GIO = 36.0

#: Hai cảnh báo "mất tiền" nhắc lại tối đa 1 lần/ngày (không dồn mỗi 15').
NGUONG_LAP_BAO_TIEN_GIO = 24.0

#: Nhịp tim agent cũ quá ngần này VÀ tiến trình đã chết VÀ cổng 8767 trống →
#: agent chết hẳn (khác `gac_tong.tu_sua_agent_treo`: agent sống mà đứng im).
NGUONG_NHIP_AGENT_CHET_PHUT = 20.0

#: Mỗi kiểu hồi sinh (mở giao diện / mở agent) thử tối đa 1 lần / chừng này phút.
NHIP_HOI_SINH_PHUT = 30.0

#: Nhịp tim gác tổng cũ quá ngần này (4 lượt 15' liền không xong) → báo.
NGUONG_GAC_TONG_IM_PHUT = 60.0

#: Số lượt sập LIỀN của một vòng lịch trước khi báo ra ngoài (1 lần sập lẻ có
#: thể do đĩa/antivirus thoáng qua — lượt sau tự chạy lại, chỉ ghi sổ).
SO_LAN_SAP_THI_BAO = 2

MUC_KHAN = "khan"
MUC_THUONG = "thuong"
MUC_NHAC = "nhac"


# ═══ tiện ích nhỏ ═══════════════════════════════════════════════════════════


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> bool:
    """Ghi NGUYÊN TỬ (`.tmp` + `os.replace`). Lỗi đĩa → False, không ném."""
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = "{0}.{1}.tmp".format(duong, os.getpid())
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
        return True
    except OSError:
        return False


def _su_co(loai: str, muc: str, chuyen_gi: str, *, kenh: str = "", can_lam_gi: str = "",
           neu_khong_lam: str = "", dedupe_khoa: str = "", lap_gio: Optional[float] = None) -> Dict[str, Any]:
    """Cùng hình dạng `core.gac_tong._su_co` (không import để khỏi vòng nhập)."""
    sc: Dict[str, Any] = {"loai": loai, "kenh": kenh, "muc": muc, "chuyen_gi": chuyen_gi,
                          "can_lam_gi": can_lam_gi, "neu_khong_lam": neu_khong_lam,
                          "dedupe_khoa": dedupe_khoa}
    if lap_gio is not None:
        sc["lap_gio"] = float(lap_gio)
    return sc


def _ghi_dong_loi_chay_max(goc: str, bay_gio: _dt.datetime, muc: str, chuyen_gi: str) -> None:
    """Một dòng vào `workspace/loi-chay-max.md` — cùng khuôn `gac_tong._ghi_loi_chay_max_md`."""
    duong = os.path.join(goc, "workspace", "loi-chay-max.md")
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write("- [{0}] **{1}** — {2}\n".format(bay_gio.strftime("%Y-%m-%d %H:%M"), muc, chuyen_gi))
    except OSError:
        pass


def _pid_con_song_mac_dinh(pid: int) -> bool:
    from . import khe  # noqa: PLC0415 — khe thuần thư viện chuẩn, nạp muộn cho test nhẹ
    return khe.pid_con_song(int(pid))


def cho_lui_dan(so_lan: int, *, co_so_giay: float = 30.0, tran_giay: float = 900.0) -> float:
    """Chờ lùi dần theo cấp số nhân: lần 1 → `co_so_giay`, mỗi lần sau ×2, kẹp `tran_giay`."""
    n = max(1, int(so_lan))
    return float(min(tran_giay, co_so_giay * (2 ** min(n - 1, 20))))


# ═══ 1. Dọn khoá chết AN TOÀN ═══════════════════════════════════════════════


def _pid_moc(du: Any) -> Tuple[int, Optional[float]]:
    if not isinstance(du, dict):
        return 0, None
    try:
        pid = int(du.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    try:
        moc = float(du.get("bat_dau")) if du.get("bat_dau") is not None else None
    except (TypeError, ValueError):
        moc = None
    return pid, moc


def don_khoa_chet_an_toan(
    duong: str,
    *,
    pid_thay: int,
    bat_dau_thay: Optional[float] = None,
    bay_gio: Optional[float] = None,
    tuoi_toi_thieu_giay: float = TUOI_KHOA_CHET_TOI_THIEU_GIAY,
    pid_con_song: Optional[Callable[[int], bool]] = None,
) -> Tuple[bool, str]:
    """Xoá tệp khoá `duong` NẾU VÀ CHỈ NẾU nó vẫn là đúng khoá chết đã thấy.

    `(True, "")` = đã xoá; `(False, lý do)` = không xoá (vẫn an toàn — người xin
    khe thật sẽ tự giành lại khoá PID chết qua `core.khe`). Không bao giờ ném.
    """
    con_song = pid_con_song or _pid_con_song_mac_dinh
    luc = time.time() if bay_gio is None else float(bay_gio)
    du = _doc_json(duong)
    if du is None:
        return False, "khoá không còn (đã có người dọn/nhả)"
    pid, moc = _pid_moc(du)
    if not pid or pid != int(pid_thay or 0):
        return False, "khoá đã đổi chủ (PID {0})".format(pid)
    if bat_dau_thay is not None and (moc is None or abs(moc - float(bat_dau_thay)) > 1.0):
        return False, "khoá đã được giữ lại bởi lượt mới"
    if moc is None:
        try:
            moc = os.path.getmtime(duong)
        except OSError:
            return False, "không đọc được tuổi khoá"
    tuoi = luc - moc
    if tuoi < tuoi_toi_thieu_giay:
        return False, "khoá mới {0:.0f} giây — chưa đủ {1:.0f} giây".format(tuoi, tuoi_toi_thieu_giay)
    try:
        if con_song(pid):
            return False, "PID {0} còn sống".format(pid)
    except Exception:  # noqa: BLE001 — không biết chắc thì coi như còn sống
        return False, "không kiểm được PID {0}".format(pid)
    tam = "{0}.chet-{1}-{2}".format(duong, pid, os.getpid())
    try:
        os.replace(duong, tam)
    except FileNotFoundError:
        return False, "khoá vừa được nhả"
    except OSError as loi:
        return False, "không đổi tên được khoá: {0}".format(loi)
    du2 = _doc_json(tam)
    pid2, moc2 = _pid_moc(du2)
    if pid2 != pid or (moc is not None and moc2 is not None and abs(moc2 - moc) > 1.0):
        # Lỡ cuỗm khoá của một lượt VỪA giành (giữa lần đọc và lần đổi tên) — trả lại.
        try:
            os.rename(tam, duong)
        except OSError:
            pass
        return False, "khoá vừa đổi chủ lúc dọn — đã trả lại"
    for _lan in range(5):
        try:
            os.remove(tam)
            break
        except FileNotFoundError:
            break
        except OSError:
            time.sleep(0.1)
    return True, ""


# ═══ 2. Nhịp tim + sổ sập vòng + hạn giờ cứng ═══════════════════════════════


def duong_nhip(goc: str, ten: str) -> str:
    """`workspace/gac-tong/nhip.json` cho gác tổng; `workspace/ben-bi/nhip-<ten>.json` cho vòng khác."""
    if ten == "gac_tong":
        return os.path.join(goc, "workspace", "gac-tong", "nhip.json")
    return os.path.join(goc, "workspace", "ben-bi", "nhip-{0}.json".format(ten))


def ghi_nhip(goc: str, ten: str, buoc: str, *, bay_gio: Optional[float] = None, **them: Any) -> None:
    luc = time.time() if bay_gio is None else float(bay_gio)
    du = _doc_json(duong_nhip(goc, ten))
    du = du if isinstance(du, dict) else {}
    du.update({"pid": os.getpid(), "luc": luc, "buoc": str(buoc)[:160]})
    if buoc == "xong":
        du["luc_xong"] = luc
    du.update(them)
    _ghi_json(duong_nhip(goc, ten), du)


def doc_nhip(goc: str, ten: str) -> Dict[str, Any]:
    du = _doc_json(duong_nhip(goc, ten))
    return du if isinstance(du, dict) else {}


def _duong_loi_vong(goc: str) -> str:
    return os.path.join(goc, "workspace", "ben-bi", "loi-vong.json")


def ghi_loi_vong(goc: str, ten: str, loi: BaseException, *, bay_gio: Optional[_dt.datetime] = None,
                 gui: Optional[Callable[..., bool]] = None, nguong_bao: int = SO_LAN_SAP_THI_BAO) -> int:
    """Ghi một lần "vòng `ten` sập" (đếm lần LIỀN), trả số lần liền. Từ lần
    `nguong_bao` trở đi: ghi `loi-chay-max.md` + báo khẩn (`core.bao_dong`
    tự chống lặp 24 giờ theo `loai`). Không bao giờ ném."""
    try:
        bay_gio = bay_gio or _dt.datetime.now()
        so = _doc_json(_duong_loi_vong(goc))
        so = so if isinstance(so, dict) else {}
        cu = so.get(ten) if isinstance(so.get(ten), dict) else {}
        n = int(cu.get("so_lan") or 0) + 1
        chu_loi = "{0}: {1}".format(type(loi).__name__, str(loi)[:300])
        so[ten] = {"so_lan": n, "loi": chu_loi, "luc": bay_gio.isoformat(timespec="seconds"),
                   "tu_luc": cu.get("tu_luc") or bay_gio.isoformat(timespec="seconds")}
        _ghi_json(_duong_loi_vong(goc), so)
        if n >= nguong_bao:
            chuyen = "Vòng tự động “{0}” đã sập {1} lượt liền ({2}).".format(ten, n, chu_loi[:200])
            if n == nguong_bao or n % 24 == 0:
                _ghi_dong_loi_chay_max(goc, bay_gio, MUC_KHAN, chuyen)
            try:
                if gui is None:
                    from . import bao_dong  # noqa: PLC0415
                    gui = bao_dong.bao_dong_khan
                gui("vong_sap:" + ten, chuyen,
                    "Báo người quản trị tool xem workspace/ben-bi/loi-vong.json và nhật ký.",
                    "Máy không tự canh/tự sửa được nữa — sự cố khác sẽ không ai thấy.",
                    goc=goc, bay_gio=bay_gio.timestamp())
            except Exception:  # noqa: BLE001
                pass
        return n
    except Exception:  # noqa: BLE001 — hàm ghi lỗi không được ném thêm
        return 0


def xoa_loi_vong(goc: str, ten: str) -> None:
    """Vòng `ten` vừa chạy trọn — đặt lại bộ đếm sập liền."""
    so = _doc_json(_duong_loi_vong(goc))
    if isinstance(so, dict) and ten in so:
        so.pop(ten, None)
        _ghi_json(_duong_loi_vong(goc), so)


def hen_gio_tu_thoat(goc: str, ten: str, giay: float, *,
                     thoat: Optional[Callable[[int], Any]] = None) -> threading.Timer:
    """Hạn giờ CỨNG cho một lượt lịch: quá `giay` thì ghi sổ rồi `os._exit(3)`.

    Daemon timer — lượt xong sớm thì tiến trình thoát, timer chết theo. Gọi
    `.cancel()` nếu muốn huỷ."""
    thoat = thoat or os._exit  # noqa: SLF001

    def _het_gio() -> None:
        try:
            bay_gio = _dt.datetime.now()
            chuyen = "Lượt “{0}” chạy quá {1:.0f} phút — tự thoát để lượt lịch sau chạy được.".format(
                ten, giay / 60.0)
            ghi_nhip(goc, ten, "het_gio")
            _ghi_dong_loi_chay_max(goc, bay_gio, MUC_THUONG, chuyen)
            ghi_loi_vong(goc, ten, TimeoutError(chuyen), bay_gio=bay_gio)
        finally:
            thoat(3)

    t = threading.Timer(float(giay), _het_gio)
    t.daemon = True
    t.start()
    return t


# ═══ 3. "Cả máy 36 giờ không làm ra gói mới" ═════════════════════════════════


def _duong_san_xuat_cuoi(goc: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "san-xuat-cuoi.json")


def _ma_goi_cua_anh(anh: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """(có kênh nào bật tự chạy không, danh sách "<kênh>/<mã gói>" của các kênh bật)."""
    co_bat = False
    ds: List[str] = []
    for ma, snap in sorted((anh.get("kenh") or {}).items()):
        if not isinstance(snap, dict) or not snap.get("tu_chay"):
            continue
        co_bat = True
        for d in snap.get("ke_hoach") or []:
            ma_goi = str((d or {}).get("Mã gói") or "").strip()
            if ma_goi:
                ds.append("{0}/{1}".format(ma, ma_goi))
    return co_bat, ds


def kiem_khong_san_xuat(goc: str, anh: Dict[str, Any], *, bay_gio: Optional[_dt.datetime] = None,
                        ghi_dia: bool = True, nguong_gio: float = NGUONG_KHONG_SAN_XUAT_GIO,
                        giu_toi_da: int = 5000) -> List[Dict[str, Any]]:
    """Sự cố "cả máy `nguong_gio` giờ không có gói mới nào" (rỗng nếu ổn).

    Tín hiệu: một "Mã gói" MỚI xuất hiện trong `ke-hoach.csv` của bất kỳ kênh
    tự chạy nào = sản xuất vừa bàn giao xong một video. Sổ `workspace/gac-tong/
    san-xuat-cuoi.json` nhớ các mã đã thấy + mốc lần cuối thấy mã mới. Lần đầu
    (chưa có sổ) hoặc chưa kênh nào bật tự chạy → đặt mốc = bây giờ, không báo.
    """
    try:
        bay_gio = bay_gio or _dt.datetime.now()
        luc = bay_gio.timestamp()
        co_bat, ma_goi = _ma_goi_cua_anh(anh)
        so = _doc_json(_duong_san_xuat_cuoi(goc))
        so = so if isinstance(so, dict) else None
        if so is None or not co_bat:
            if ghi_dia:
                _ghi_json(_duong_san_xuat_cuoi(goc), {"luc_moi": luc, "da_thay": ma_goi[-giu_toi_da:]})
            return []
        da_thay = [str(m) for m in (so.get("da_thay") or [])]
        tap = set(da_thay)
        moi = [m for m in ma_goi if m not in tap]
        try:
            luc_moi = float(so.get("luc_moi") or luc)
        except (TypeError, ValueError):
            luc_moi = luc
        if moi:
            luc_moi = luc
            da_thay = (da_thay + moi)[-giu_toi_da:]
        if ghi_dia and (moi or "luc_moi" not in so):
            _ghi_json(_duong_san_xuat_cuoi(goc), {"luc_moi": luc_moi, "da_thay": da_thay})
        gio = (luc - luc_moi) / 3600.0
        if gio <= nguong_gio:
            return []
        tu = _dt.datetime.fromtimestamp(luc_moi).strftime("%d/%m %H:%M")
        return [_su_co(
            "khong_san_xuat", MUC_KHAN,
            "Cả máy đã {0:.0f} giờ không làm ra video mới nào (gói mới gần nhất lúc {1}).".format(gio, tu),
            can_lam_gi="Mở tool xem ví ShopAPI còn tiền không, và nhật ký sản xuất (workspace/tu-chay/tu-chay.log).",
            neu_khong_lam="Mọi kênh hết video để đăng — mất view và tiền mỗi ngày.",
            dedupe_khoa="khong_san_xuat:{0:.0f}".format(luc_moi), lap_gio=NGUONG_LAP_BAO_TIEN_GIO)]
    except Exception:  # noqa: BLE001 — kiểm hỏng không được làm sập gác tổng
        return []


# ═══ 4. Hồi sinh máy nền (giao diện + agent) ════════════════════════════════


def _duong_hoi_sinh(goc: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "hoi-sinh.json")


def kiem_agent_sap(goc: str, thu_muc_vm: str, *, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """`vm/logs/agent-sap.json` (agent tự ghi khi vòng chính sập, xem `vm/agent.py::chay_ben`):
    sập ≥ 3 lần trong giờ qua → báo khẩn (lọc lặp 6 giờ)."""
    bay_gio = bay_gio or _dt.datetime.now()
    du = _doc_json(os.path.join(thu_muc_vm, "logs", "agent-sap.json"))
    if not isinstance(du, dict):
        return []
    try:
        n = int(du.get("so_lan") or 0)
        luc = float(du.get("luc") or 0)
    except (TypeError, ValueError):
        return []
    if n < 3 or bay_gio.timestamp() - luc > 3600:
        return []
    return [_su_co(
        "agent_sap_lap", MUC_KHAN,
        "Máy nền đăng video (agent) sập lặp {0} lần: {1}".format(n, str(du.get("loi") or "?")[:200]),
        can_lam_gi="Báo người quản trị tool xem vm/agent.log.",
        neu_khong_lam="Video làm xong không được tải lên YouTube.",
        dedupe_khoa="agent_sap:{0}".format(str(du.get("tu_luc") or "")), lap_gio=6.0)]


def _giao_dien_dang_chay_mac_dinh(goc: str) -> bool:
    from . import dong_bo_git as dbg  # noqa: PLC0415
    return bool(dbg._tim(dbg._tien_trinh_python(), goc, dbg.TEP_GIAO_DIEN))  # noqa: SLF001


def _cong_nghe_mac_dinh(cong: int) -> bool:
    from . import dong_bo_git as dbg  # noqa: PLC0415
    return dbg._cong_nghe(int(cong))  # noqa: SLF001


def _mo_giao_dien_mac_dinh(goc: str) -> bool:
    from . import dong_bo_git as dbg  # noqa: PLC0415
    return dbg._mo_giao_dien(goc)  # noqa: SLF001


def _dang_cap_nhat_mac_dinh(goc: str) -> bool:
    from . import cap_nhat_git  # noqa: PLC0415
    return bool(cap_nhat_git.dang_cap_nhat(goc))


def _mo_agent_mac_dinh(thu_muc_vm: str) -> bool:
    """Mở `vm/agent.py` tách rời — đúng dòng lệnh `core.giam_sat_vm._mo_that`
    (agent tự giữ khoá một-mình cổng 8767 nên mở thừa cũng không chạy đôi)."""
    from .giam_sat_vm import _tim_python  # noqa: PLC0415
    from .tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415

    tep = os.path.join(thu_muc_vm, "agent.py")
    if not os.path.isfile(tep):
        return False
    co = 0
    if os.name == "nt":
        for ten in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP"):
            co |= getattr(subprocess, ten, 0)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        os.makedirs(os.path.join(thu_muc_vm, "logs"), exist_ok=True)
        log = open(os.path.join(thu_muc_vm, "logs", "agent-gui.log"), "a", encoding="utf-8", errors="replace")
    except OSError:
        return False
    try:
        for co_thu in ((co | CO_TACH_KHOI_JOB), co):
            try:
                subprocess.Popen([_tim_python(), "-u", "-X", "utf8", tep], cwd=thu_muc_vm,  # noqa: S603
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 env=env, creationflags=co_thu, close_fds=True)
                return True
            except OSError:
                continue
        return False
    finally:
        log.close()


def hoi_sinh_may_nen(
    goc: str,
    thu_muc_vm: str,
    *,
    bay_gio: Optional[_dt.datetime] = None,
    ghi_dia: bool = True,
    pid_con_song: Optional[Callable[[int], bool]] = None,
    cong_nghe: Optional[Callable[[int], bool]] = None,
    giao_dien_dang_chay: Optional[Callable[[str], bool]] = None,
    mo_giao_dien: Optional[Callable[[str], bool]] = None,
    mo_agent: Optional[Callable[[str], bool]] = None,
    dang_cap_nhat: Optional[Callable[[str], bool]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Agent chết HẲN (nhịp tim cũ > `NGUONG_NHIP_AGENT_CHET_PHUT`, PID chết, cổng
    8767 trống) → (1) giao diện không chạy: mở lại giao diện (nó tự nuôi agent);
    (2) giao diện đang chạy, hoặc đã mở lại mà ≥ 10' agent vẫn chết: mở thẳng
    agent. Mỗi kiểu tối đa 1 lần / `NHIP_HOI_SINH_PHUT`. Đang có lượt cập nhật
    (nó tự khởi động lại mọi thứ) → không làm gì.

    Trả `(hành động, sự cố)`. Chết > 60' dù đã thử → sự cố KHẨN (lọc lặp 6 giờ).
    Chưa từng có nhịp tim (máy không chạy agent) → không làm gì."""
    try:
        bay_gio = bay_gio or _dt.datetime.now()
        luc = bay_gio.timestamp()
        nhip = _doc_json(os.path.join(thu_muc_vm, "logs", "nhip-tim.json"))
        if not isinstance(nhip, dict):
            return [], []
        try:
            pid, luc_nhip = int(nhip.get("pid") or 0), float(nhip.get("luc") or 0)
        except (TypeError, ValueError):
            return [], []
        tuoi_phut = (luc - luc_nhip) / 60.0
        if tuoi_phut <= NGUONG_NHIP_AGENT_CHET_PHUT:
            return [], []
        if (pid_con_song or _pid_con_song_mac_dinh)(pid):
            return [], []  # sống mà đứng im: việc của gac_tong.tu_sua_agent_treo
        if (cong_nghe or _cong_nghe_mac_dinh)(8767):
            return [], []  # một agent khác (PID mới chưa kịp ghi nhịp) đang giữ khoá
        if (dang_cap_nhat or _dang_cap_nhat_mac_dinh)(goc):
            return [], []
        so = _doc_json(_duong_hoi_sinh(goc))
        so = so if isinstance(so, dict) else {}

        def _phut_tu(khoa: str) -> float:
            try:
                return (luc - float(so.get(khoa) or 0)) / 60.0
            except (TypeError, ValueError):
                return 1e9

        hanh_dong: List[Dict[str, Any]] = []
        gd_song = (giao_dien_dang_chay or _giao_dien_dang_chay_mac_dinh)(goc)
        if not gd_song and _phut_tu("luc_mo_gd") >= NHIP_HOI_SINH_PHUT:
            ok = (mo_giao_dien or _mo_giao_dien_mac_dinh)(goc) if ghi_dia else False
            so["luc_mo_gd"] = luc
            hanh_dong.append({"loai": "mo_lai_giao_dien", "kenh": "", "thuc_hien": bool(ok),
                              "chuyen_gi": "Agent đăng video chết {0:.0f} phút và giao diện không chạy — "
                                           "đã mở lại giao diện{1}.".format(tuoi_phut, "" if ok else " (HỎNG)")})
        elif (gd_song or _phut_tu("luc_mo_gd") >= 10.0) and _phut_tu("luc_mo_agent") >= NHIP_HOI_SINH_PHUT:
            ok = (mo_agent or _mo_agent_mac_dinh)(thu_muc_vm) if ghi_dia else False
            so["luc_mo_agent"] = luc
            hanh_dong.append({"loai": "mo_lai_agent", "kenh": "", "thuc_hien": bool(ok),
                              "chuyen_gi": "Agent đăng video chết {0:.0f} phút — đã mở thẳng agent{1}.".format(
                                  tuoi_phut, "" if ok else " (HỎNG)")})
        if hanh_dong and ghi_dia:
            _ghi_json(_duong_hoi_sinh(goc), so)
        su_co: List[Dict[str, Any]] = []
        if tuoi_phut > 60.0:
            su_co.append(_su_co(
                "may_nen_chet", MUC_KHAN,
                "Máy nền đăng video (agent) đã chết {0:.0f} phút, máy tự mở lại chưa được.".format(tuoi_phut),
                can_lam_gi="Đăng nhập máy, mở MyTool (CHAY-GON.vbs) hoặc khởi động lại máy.",
                neu_khong_lam="Video làm xong không được tải lên YouTube, mất ngày đăng.",
                dedupe_khoa="may_nen_chet:{0:.0f}".format(luc_nhip), lap_gio=6.0))
        return hanh_dong, su_co
    except Exception:  # noqa: BLE001 — hồi sinh hỏng không được làm sập gác tổng
        return [], []


# ═══ 5. Ai gác người gác — gọi từ bộ điều phối ═════════════════════════════


def _duong_canh_gac(goc: str) -> str:
    return os.path.join(goc, "workspace", "ben-bi", "canh-gac-tong.json")


def canh_gac_tong(
    goc: str,
    *,
    bay_gio: Optional[_dt.datetime] = None,
    trang_thai_lich: Optional[Callable[[str], Dict[str, Any]]] = None,
    dang_ky_lich: Optional[Callable[[str], Any]] = None,
    gui: Optional[Callable[..., bool]] = None,
) -> str:
    """Nhịp tim gác tổng (`workspace/gac-tong/nhip.json`) cũ > `NGUONG_GAC_TONG_IM_PHUT`
    → lịch mất thì đăng ký lại (tối đa 1 lần/6 giờ) + báo khẩn (`bao_dong` tự lọc lặp
    24 giờ) + ghi `loi-chay-max.md` (tối đa 1 lần/6 giờ). Chưa từng có nhịp tim (bản
    cũ / máy chưa cài gác tổng) → không làm gì. Trả một câu tóm tắt (rỗng = ổn)."""
    try:
        bay_gio = bay_gio or _dt.datetime.now()
        luc = bay_gio.timestamp()
        nhip = doc_nhip(goc, "gac_tong")
        if not nhip:
            return ""
        try:
            moc = float(nhip.get("luc_xong") or nhip.get("luc") or 0)
        except (TypeError, ValueError):
            return ""
        phut = (luc - moc) / 60.0
        if phut <= NGUONG_GAC_TONG_IM_PHUT:
            return ""
        so = _doc_json(_duong_canh_gac(goc))
        so = so if isinstance(so, dict) else {}
        cau = ["gác tổng im {0:.0f} phút".format(phut)]
        if (luc - float(so.get("luc_dang_ky") or 0)) >= 6 * 3600:
            from . import lich_tu_chay  # noqa: PLC0415
            tt = (trang_thai_lich or lich_tu_chay.trang_thai_gac_tong)(goc)
            if not (tt or {}).get("da_dang_ky"):
                kq = (dang_ky_lich or lich_tu_chay.dang_ky_gac_tong)(goc)
                so["luc_dang_ky"] = luc
                ok = bool(kq[0]) if isinstance(kq, tuple) else bool(kq)
                cau.append("lịch gác tổng bị mất — đăng ký lại {0}".format("OK" if ok else "HỎNG"))
        chuyen = "Người gác tổng đã {0:.0f} phút không chạy xong lượt nào (bước cuối: {1}).".format(
            phut, str(nhip.get("buoc") or "?")[:80])
        if (luc - float(so.get("luc_ghi") or 0)) >= 6 * 3600:
            _ghi_dong_loi_chay_max(goc, bay_gio, MUC_KHAN, chuyen)
            so["luc_ghi"] = luc
        try:
            if gui is None:
                from . import bao_dong  # noqa: PLC0415
                gui = bao_dong.bao_dong_khan
            gui("gac_tong_im", chuyen,
                "Mở Task Scheduler xem lịch ShopAPI-GacTong, hoặc khởi động lại máy.",
                "Mọi sự cố khác (kênh không đăng, đĩa đầy, ví cạn) sẽ không còn ai báo.",
                goc=goc, bay_gio=luc)
        except Exception:  # noqa: BLE001
            pass
        _ghi_json(_duong_canh_gac(goc), so)
        return "; ".join(cau)
    except Exception:  # noqa: BLE001 — canh hỏng không được làm hỏng nhịp điều phối
        return ""


def gop(*ds: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Nối nhiều danh sách sự cố (tiện cho nơi gọi)."""
    ra: List[Dict[str, Any]] = []
    for d in ds:
        ra.extend(d or [])
    return ra
