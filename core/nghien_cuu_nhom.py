"""**Nghiên cứu NHÓM + giữ nguồn** — nghiên cứu TẬP TRUNG một chỗ cho cả nhóm kênh,
và không để hai kênh anh em cùng giành một video nguồn.

═══ VÌ SAO (kiểm toán 29/09/2026) ═══

Trước đây MỖI lượt sản xuất của MỖI kênh chạy lại trọn chuỗi "một nút" (trang
chủ → chốt hộp thư → quét content đối thủ → gán tuyến → chấm): 20–50 phút, hàng
chục lượt AI. 17:13 hôm 29/09 cả ba lượt TL1/TL2/TL3 cùng đứng ở bước nghiên cứu
hơn 50 phút, trên CÙNG một bộ đối thủ.

═══ LUẬT ═══

1. **Còn tươi thì không nghiên cứu.** Kênh có `nhom`: lượt sản xuất chỉ nghiên
   cứu khi lần nghiên cứu gần nhất của kênh (mốc `bao-cao-mot-nut.md`, `mot_nut`
   ghi ở cuối mỗi chuỗi) cũ hơn `nghien_cuu_moi_gio` giờ (`workspace/cai-dat.json`,
   mặc định 12, kẹp 2..48) — hoặc lượt chọn nguồn trước đã báo kho ứng viên dưới
   `NGUONG_UNG_VIEN` (khi đó sớm nhất `GIO_TOI_THIEU_KHI_THIEU` giờ sau lần trước).
2. **Một lần cho cả nhóm.** Cần nghiên cứu thì giành khoá nhóm O_EXCL
   (`CHANNEL/_NHOM/<nhóm>/nghien-cuu/.khoa`) rồi chạy chuỗi cho CHÍNH kênh này
   và cho mọi kênh anh em đang bật `tu_chay` cũng đã cũ MÀ đang rảnh (giành được
   khoá kênh của nó — kênh anh em đang có lượt chạy thì không đụng). Nhờ bộ đệm
   chung (`nghien_cuu_chung`) kênh thứ hai, ba gần như không gọi mạng/AI; phần
   theo TỆP khán giả (gán tuyến, chấm V7) vẫn riêng từng kênh.
3. **Khoá bận** (lượt khác đang nghiên cứu cho nhóm): dữ liệu còn dưới
   `GIO_DUNG_DU_LIEU_CU` (24) giờ → chọn nguồn luôn từ dữ liệu sẵn có; cũ hơn →
   lượt này dừng, đợi lượt sau. Không tự nghiên cứu riêng.
4. **Giữ nguồn** (`giu-nguon/<mã>.json`, O_EXCL): chọn xong một nguồn thì giành
   nó cho kênh mình; nguồn kênh anh em đã giành bị loại khỏi vòng chọn của kênh
   khác. Nhả khi lượt bị bỏ; bản giữ > 7 ngày mà thư mục lượt không còn = rác.

Kênh không khai `nhom` → không có gì ở đây chạy: nghiên cứu mỗi lượt như cũ.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import nghien_cuu_chung as ncc

__all__ = ["can_nghien_cuu", "chay_nhom", "tuoi_gio", "danh_dau_thieu", "moi_gio",
           "giu_nguon", "nguon_da_giu_boi_kenh_khac", "nha_nguon",
           "NGUONG_UNG_VIEN", "GIO_DUNG_DU_LIEU_CU"]

TEP_KHOA = ".khoa"
TEP_TRANG_THAI = "lan-nghien-cuu.json"
THU_MUC_GIU = "giu-nguon"
MOI_GIO_MAC_DINH = 12.0
NGUONG_UNG_VIEN = 5
GIO_TOI_THIEU_KHI_THIEU = 2.0
GIO_DUNG_DU_LIEU_CU = 24.0
#: Khoá nhóm cũ hơn ngần này coi như chết (chuỗi dài nhất đo được ~50').
KHOA_CU_GIAY = 4 * 3600
GIU_NGUON_RAC_NGAY = 7


def _pid_song(pid: int) -> bool:
    from . import khe  # noqa: PLC0415

    return khe.pid_con_song(pid)


def moi_gio(goc: str) -> float:
    try:
        with open(os.path.join(goc, "workspace", "cai-dat.json"), encoding="utf-8") as tep:
            v = float((json.load(tep) or {}).get("nghien_cuu_moi_gio") or MOI_GIO_MAC_DINH)
    except (OSError, ValueError, TypeError, AttributeError):
        v = MOI_GIO_MAC_DINH
    return max(2.0, min(48.0, v))


def _moc_nghien_cuu(goc: str, ma_kenh: str) -> Optional[float]:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415
    from .mot_nut import TEP_BAO_CAO  # noqa: PLC0415

    try:
        return os.path.getmtime(os.path.join(thu_muc_nghien_cuu(goc, ma_kenh), TEP_BAO_CAO))
    except OSError:
        return None


def tuoi_gio(goc: str, ma_kenh: str, *, bay_gio: Optional[float] = None) -> Optional[float]:
    """Số giờ từ lần nghiên cứu (một nút) gần nhất của kênh; chưa từng → None."""
    moc = _moc_nghien_cuu(goc, ma_kenh)
    if moc is None:
        return None
    return max(0.0, ((bay_gio or time.time()) - moc) / 3600.0)


def _duong_trang_thai(goc: str, ma_kenh: str) -> str:
    return os.path.join(ncc.thu_muc(goc, ma_kenh), TEP_TRANG_THAI)


def danh_dau_thieu(goc: str, ma_kenh: str, so_ung_vien: int) -> None:
    """Lượt chọn nguồn thấy kho ứng viên (sau khi loại nguồn đã làm/đã giữ) dưới
    ngưỡng → lượt sau nghiên cứu lại dù chưa hết `nghien_cuu_moi_gio`."""
    try:
        ncc.ghi_json_gop(_duong_trang_thai(goc, ma_kenh),
                         {"thieu@" + ma_kenh: {"luc": time.time(), "so": int(so_ung_vien)}})
    except OSError:
        pass


def can_nghien_cuu(goc: str, ma_kenh: str, *,
                   bay_gio: Optional[float] = None) -> Tuple[bool, str, Optional[float]]:
    """(cần nghiên cứu?, lý do một câu, tuổi dữ liệu theo giờ hoặc None)."""
    tuoi = tuoi_gio(goc, ma_kenh, bay_gio=bay_gio)
    han = moi_gio(goc)
    if tuoi is None:
        return True, "kênh chưa có lần nghiên cứu nào", None
    if tuoi >= han:
        return True, "dữ liệu {0:.1f} giờ ≥ {1:.0f} giờ".format(tuoi, han), tuoi
    tt = ncc.doc_json(_duong_trang_thai(goc, ma_kenh), {})
    thieu = tt.get("thieu@" + ma_kenh) if isinstance(tt, dict) else None
    moc = _moc_nghien_cuu(goc, ma_kenh) or 0
    if isinstance(thieu, dict) and float(thieu.get("luc") or 0) > moc \
            and tuoi >= GIO_TOI_THIEU_KHI_THIEU:
        return True, "kho ứng viên còn {0} (< {1})".format(thieu.get("so"), NGUONG_UNG_VIEN), tuoi
    return False, "dữ liệu nhóm còn tươi ({0:.1f} giờ < {1:.0f} giờ)".format(tuoi, han), tuoi


# ── khoá nhóm ────────────────────────────────────────────────────────────────


def _duong_khoa(goc: str, ma_kenh: str) -> str:
    return os.path.join(ncc.thu_muc(goc, ma_kenh), TEP_KHOA)


def _giu_khoa_nhom(goc: str, ma_kenh: str) -> Tuple[bool, Dict[str, Any]]:
    duong = _duong_khoa(goc, ma_kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _lan in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            cu = ncc.doc_json(duong, {})
            pid = int((cu or {}).get("pid") or 0) if isinstance(cu, dict) else 0
            luc = float((cu or {}).get("luc") or 0) if isinstance(cu, dict) else 0
            if pid and time.time() - luc < KHOA_CU_GIAY and _pid_song(pid):
                return False, cu
            try:
                os.remove(duong)
            except OSError:
                pass
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "luc": time.time(), "kenh": ma_kenh}, tep)
        return True, {}
    return False, {}


def _nha_khoa_nhom(goc: str, ma_kenh: str) -> None:
    duong = _duong_khoa(goc, ma_kenh)
    cu = ncc.doc_json(duong, {})
    if isinstance(cu, dict) and int(cu.get("pid") or 0) == os.getpid():
        try:
            os.remove(duong)
        except OSError:
            pass


def _anh_em_can(goc: str, ma_kenh: str) -> List[str]:
    """Kênh anh em cùng nhóm, đang bật `tu_chay`, dữ liệu cũ."""
    try:
        from . import nhom_kenh  # noqa: PLC0415
        from .tu_chay import kenh_tu_chay  # noqa: PLC0415

        bat = set(kenh_tu_chay(goc))
        ra = []
        for ma in nhom_kenh.thanh_vien(goc, ma_kenh):
            if ma != ma_kenh and ma in bat and can_nghien_cuu(goc, ma)[0]:
                ra.append(ma)
        return ra
    except Exception:  # noqa: BLE001 — đọc nhóm hỏng thì chỉ nghiên cứu kênh mình
        return []


def chay_nhom(goc: str, ma_kenh: str, *, client: Any, chay_mot_nut: Callable[..., Any],
              on_log: Callable[[str], None], cancel: Any = None,
              co_danh_ba: Optional[Callable[[str], bool]] = None) -> Dict[str, Any]:
    """Nghiên cứu cho `ma_kenh` + anh em rảnh đã cũ, dưới khoá nhóm.

    Trả `{"ban": True, "giu": {...}}` khi lượt khác đang nghiên cứu cho nhóm, hoặc
    `{"ban": False, "phut": {kênh: phút}, "loi": {kênh: lỗi}}`. Lỗi của CHÍNH
    `ma_kenh` nằm ở `loi[ma_kenh]` (nơi gọi quyết định dừng lượt)."""
    from . import tu_chay  # noqa: PLC0415

    ok, giu = _giu_khoa_nhom(goc, ma_kenh)
    if not ok:
        return {"ban": True, "giu": giu}
    ra: Dict[str, Any] = {"ban": False, "phut": {}, "loi": {}}
    try:
        danh_sach = [ma_kenh] + _anh_em_can(goc, ma_kenh)
        if len(danh_sach) > 1:
            on_log("  [NGHIÊN CỨU NHÓM] làm luôn cho kênh anh em đã cũ: {0}".format(
                ", ".join(danh_sach[1:])))
        for ma in danh_sach:
            if cancel is not None and getattr(cancel, "is_set", lambda: False)():
                break
            giu_kenh = ma != ma_kenh
            if giu_kenh:
                ok_k, ly_do_k = tu_chay._giu_khoa(goc, ma)  # noqa: SLF001
                if not ok_k:
                    on_log("  [NGHIÊN CỨU NHÓM] bỏ qua {0}: {1}.".format(ma, ly_do_k))
                    continue
            bat_dau = time.time()
            tien_to = "" if ma == ma_kenh else "[{0}] ".format(ma)
            try:
                c = client
                if c is not None and co_danh_ba is not None and not co_danh_ba(ma):
                    c = None
                chay_mot_nut(goc, ma, client=c, on_log=lambda d, t=tien_to: on_log(t + str(d)),
                             cancel=cancel)
            except Exception as loi:  # noqa: BLE001 — một kênh hỏng không kéo cả nhóm
                ra["loi"][ma] = str(loi)[:400]
                on_log("  [NGHIÊN CỨU NHÓM] {0} hỏng: {1}".format(ma, str(loi)[:200]))
            finally:
                if giu_kenh:
                    tu_chay._nha_khoa(goc, ma)  # noqa: SLF001
            phut = (time.time() - bat_dau) / 60.0
            ra["phut"][ma] = round(phut, 1)
            on_log("  [NGHIÊN CỨU NHÓM] {0} xong trong {1:.1f} phút.".format(ma, phut))
        try:
            ncc.ghi_json_gop(_duong_trang_thai(goc, ma_kenh), {
                "lan_cuoi": {"luc": _dt.datetime.now().isoformat(timespec="seconds"),
                             "boi": ma_kenh, "phut": ra["phut"], "loi": ra["loi"]}})
        except OSError:
            pass
    finally:
        _nha_khoa_nhom(goc, ma_kenh)
    return ra


# ── giữ nguồn (G4) ───────────────────────────────────────────────────────────


def _duong_giu(goc: str, ma_kenh: str, ma_nguon: str) -> str:
    an_toan = "".join(ch for ch in str(ma_nguon) if ch.isalnum() or ch in "-_")[:40]
    return os.path.join(ncc.thu_muc(goc, ma_kenh), THU_MUC_GIU, an_toan + ".json")


def _giu_la_rac(goc: str, giu: Dict[str, Any]) -> bool:
    try:
        luc = float(giu.get("luc") or 0)
    except (TypeError, ValueError):
        luc = 0
    if time.time() - luc < GIU_NGUON_RAC_NGAY * 86400:
        return False
    try:
        from .auto import duong_luot  # noqa: PLC0415

        return not os.path.isdir(duong_luot(goc, str(giu.get("kenh") or ""),
                                            str(giu.get("ma_luot") or "")))
    except Exception:  # noqa: BLE001
        return True


def nguon_da_giu_boi_kenh_khac(goc: str, ma_kenh: str) -> Dict[str, str]:
    """`{mã nguồn: kênh giữ}` — nguồn kênh ANH EM đã giành (bỏ bản rác)."""
    if not ncc.nhom_cua(goc, ma_kenh):
        return {}
    thu_muc = os.path.join(ncc.thu_muc(goc, ma_kenh), THU_MUC_GIU)
    ra: Dict[str, str] = {}
    try:
        ten = os.listdir(thu_muc)
    except OSError:
        return ra
    for t in ten:
        if not t.endswith(".json"):
            continue
        giu = ncc.doc_json(os.path.join(thu_muc, t), {})
        if not isinstance(giu, dict):
            continue
        kenh = str(giu.get("kenh") or "")
        if kenh and kenh != ma_kenh and not _giu_la_rac(goc, giu):
            ra[str(giu.get("ma") or t[:-5])] = kenh
    return ra


def giu_nguon(goc: str, ma_kenh: str, ma_nguon: str, *, ma_luot: str = "") -> Tuple[bool, str]:
    """Giành nguồn cho kênh (O_EXCL). (được?, kênh đang giữ nếu không được).
    Kênh không nhóm → luôn được. Bản giữ của chính kênh mình / bản rác → giành lại."""
    if not ma_nguon or not ncc.nhom_cua(goc, ma_kenh):
        return True, ""
    duong = _duong_giu(goc, ma_kenh, ma_nguon)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _lan in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            giu = ncc.doc_json(duong, {})
            kenh = str(giu.get("kenh") or "") if isinstance(giu, dict) else ""
            if kenh and kenh != ma_kenh and not _giu_la_rac(goc, giu):
                return False, kenh
            try:
                os.remove(duong)
            except OSError:
                pass
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            json.dump({"ma": ma_nguon, "kenh": ma_kenh, "ma_luot": ma_luot, "luc": time.time(),
                       "pid": os.getpid()}, tep, ensure_ascii=False)
        return True, ""
    return False, "?"


def nha_nguon(goc: str, ma_kenh: str, ma_nguon: str) -> None:
    """Nhả nguồn (lượt bị bỏ) — chỉ khi đúng kênh mình đang giữ."""
    if not ma_nguon or not ncc.nhom_cua(goc, ma_kenh):
        return
    duong = _duong_giu(goc, ma_kenh, ma_nguon)
    giu = ncc.doc_json(duong, {})
    if isinstance(giu, dict) and str(giu.get("kenh") or "") == ma_kenh:
        try:
            os.remove(duong)
        except OSError:
            pass
