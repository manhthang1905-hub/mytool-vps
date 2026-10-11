"""Chờ ENGINE phía máy chủ NGOÀI tiến trình — lượt nhả làn API, điều phối sinh lại sau giờ thăm dò.

═══ VÌ SAO (sự cố thật 10/10/2026) ═══

TTS của cổng ShopAPI sập rồi xếp hàng ~8 giờ: *"Hệ thống không có engine nào phục vụ loại yêu cầu
tts"*, rồi *"Dịch vụ "tts" đang tạm đóng để khắc phục sự cố… KHÔNG bị trừ tiền"*, rồi *"Hàng chờ giọng
nói đang quá dài: yêu cầu này sẽ đứng thứ 24 và ước tính phải chờ khoảng 6 giờ"*. Bốn kênh ngồi ở khâu
giọng, mỗi lời gọi tự đợi thang ~14 phút, ba lượt thử khâu, rồi bị nhặt lại — giữ cả 4 làn API suốt mấy
giờ; hai kênh khác không vào nổi để viết kịch bản.

Luật (tổng quát hoá luật 06/10 "lượt CHỜ KHO CLIP không chiếm làn API"):

1. Khâu gặp engine của cổng KHÔNG phục vụ được lâu — engine sập/"tạm đóng", kho hết hạn mức, hàng chờ
   máy chủ khai ≥ 30 phút, hoặc trục trặc phía máy chủ (nhà máy nghỉ/tạm nghỉ/nghẹt) kéo dài quá một
   lúc chờ NGẮN trong lượt (`GIAY_CHO_NGAN`) — thì ném `su_co.LoiChoEngine`.
2. Khâu ghi dấu `workspace/tu-chay/cho-engine/<engine>/<kênh>.json` (`bao_cho`, giờ thăm dò kế tiếp),
   `core/auto.chay` dừng lượt gọn (không đốt lượt thử khâu), tiến trình THOÁT — không giữ làn, không giữ
   RAM. Không tính là hỏng: không tăng trần tự phục hồi L3, không bị bỏ (`core/tu_chay`).
3. `core/dieu_phoi.trang_thai_kenh`: kênh có dấu mà chưa tới giờ thăm dò → không sinh; tới giờ → sinh
   lại như lượt dở (đúng thứ tự + trần tổng như mọi lượt). Lượt mới thăm dò RẺ trước (`tham_do_nhanh`,
   `GET /v1/me`, không tốn tiền) rồi mới gửi việc; đoạn đã xong vẫn nằm trên đĩa, chỉ làm phần thiếu.
4. Khâu qua được → `xoa` gỡ dấu.

Chất lượng giữ nguyên (luật 07/10/2026 "thà không đăng"): KHÔNG có đường lui giọng khác/giọng kém —
chỉ chờ đúng engine của kênh.

Module này dùng chung cho mọi engine (tts hôm nay; ảnh/nhạc… muốn dùng chỉ cần một `CanhEngine` quanh
lời gọi và `bao_cho`/`xoa` quanh khâu).
"""

from __future__ import annotations

import datetime as _dt
import re
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from . import khe
from . import su_co
from .su_co import LoiChoEngine

__all__ = ["LoiChoEngine", "ENGINE_TTS", "GIAY_CHO_NGAN", "GIAY_CHO_NGAN_KHI_THAM_DO",
           "GIAY_HANG_CHO_TOI_THIEU", "GIO_BAO_CHO_LAU", "uoc_hang_cho_giay", "ly_do_cho_ngay",
           "CanhEngine", "giay_tham_do", "tham_do_nhanh", "bao_cho", "xoa", "dau_cua"]

ENGINE_TTS = "tts"

#: Trục trặc phía máy chủ (nhà máy nghỉ / tạm nghỉ / nghẹt) liên tục quá ngần này giây trong MỘT
#: khâu (đếm từ lỗi đầu, mọi luồng chung, có lời gọi thành công là đếm lại) → chờ ngoài tiến trình.
GIAY_CHO_NGAN = 5 * 60.0
#: Lượt vừa được sinh lại ĐỂ THĂM DÒ (đã có dấu chờ) — đã biết engine vừa hỏng, đừng giữ làn 5 phút nữa.
GIAY_CHO_NGAN_KHI_THAM_DO = 60.0
#: Máy chủ khai hàng chờ dài ít nhất ngần này giây → chờ ngoài tiến trình NGAY.
GIAY_HANG_CHO_TOI_THIEU = 30 * 60.0
#: Giờ thăm dò kế tiếp theo số lần đã chờ liền (lần 1–4: 30 phút; sau đó 60 phút).
NHIP_THAM_DO_GIAY = (30 * 60.0, 30 * 60.0, 30 * 60.0, 30 * 60.0, 60 * 60.0)
#: Hàng chờ máy chủ khai dài thì giãn tới một nửa ước tính, nhưng không quá ngần này.
TRAN_THAM_DO_GIAY = 2 * 3600.0
#: Chờ liền ngần này giờ thì báo người MỘT lần (mức nhắc) — tool vẫn tự chờ tiếp.
GIO_BAO_CHO_LAU = 6.0

#: Câu máy chủ nói thẳng engine đã sập/đóng — không cần chờ ngắn trong lượt.
_DAU_ENGINE_SAP = ("tạm đóng", "không có engine nào", "no engine available", "no engine serving",
                   "service is closed", "temporarily closed")

#: "…ước tính phải chờ khoảng 17 giờ 47 phút", "…khoảng 6 giờ 4 phút", "…khoảng 45 phút".
_MAU_HANG_CHO = re.compile(
    r"(?:chờ|cho)\s+khoảng\s*(?:(\d+)\s*giờ)?\s*(?:(\d+)\s*ph)?", re.IGNORECASE)

#: Loại sự cố phía máy chủ được chờ NGẮN trong lượt rồi mới chuyển ra chờ ngoài.
_LOAI_CHO_NGAN = (su_co.NHA_MAY_NGHI, su_co.TAM_NGHI, su_co.CHAM_LAI)


def _gio() -> float:
    return time.time()


def uoc_hang_cho_giay(chu: str) -> Optional[float]:
    """Ước tính hàng chờ (giây) máy chủ khai trong câu lỗi, `None` nếu không có."""
    for m in _MAU_HANG_CHO.finditer(str(chu or "")):
        gio, phut = m.group(1), m.group(2)
        if gio is None and phut is None:
            continue
        return float(int(gio or 0) * 3600 + int(phut or 0) * 60)
    return None


def ly_do_cho_ngay(loi: BaseException) -> Tuple[str, Optional[float]]:
    """(lý do, ước hàng chờ giây) nếu lỗi này nghĩa là engine phía máy chủ sẽ KHÔNG phục vụ được
    trong một lúc lâu — chờ ngoài tiến trình NGAY; ("", None) nếu không."""
    if isinstance(loi, LoiChoEngine):
        return loi.ly_do, loi.uoc_giay
    loai = su_co.phan_loai(loi)
    if loai in (su_co.HET_TIEN, su_co.NOI_DUNG, su_co.KHOA_LECH):
        return "", None   # ví/nội dung/khoá — không phải engine; đường riêng của chúng xử
    chu = str(loi)
    thuong = chu.lower()
    uoc = uoc_hang_cho_giay(chu)
    if loai == su_co.HET_HAN_MUC:
        return chu[:300], uoc
    if any(d in thuong for d in _DAU_ENGINE_SAP):
        return chu[:300], uoc
    if uoc is not None and uoc >= GIAY_HANG_CHO_TOI_THIEU:
        return chu[:300], uoc
    return "", None


class CanhEngine:
    """Canh MỘT engine trong MỘT khâu (dùng chung cho mọi luồng của mẻ).

    `boc(ham)` bọc lời gọi tạo việc: lỗi → `xet` (có thể ném `LoiChoEngine`), thành công → `tot`.
    `xet(loi)` cũng gọi được trực tiếp cho lỗi đến từ chỗ khác (job hỏng lúc chờ kết quả)."""

    def __init__(self, engine: str, *, cho_ngan: float = GIAY_CHO_NGAN,
                 dong_ho: Optional[Callable[[], float]] = None) -> None:
        self.engine = str(engine or "?")
        self.cho_ngan = float(cho_ngan)
        self._dong_ho = dong_ho or _gio
        self._khoa = threading.Lock()
        self._tu: Optional[float] = None

    def tot(self) -> None:
        with self._khoa:
            self._tu = None

    def xet(self, loi: BaseException) -> None:
        """Ném `LoiChoEngine` nếu `loi` (cộng dồn với lỗi trước) đủ để chờ ngoài; không thì thôi —
        nơi gọi tự ném lại lỗi gốc cho đường thử lại thường."""
        if isinstance(loi, LoiChoEngine):
            raise loi
        ly_do, uoc = ly_do_cho_ngay(loi)
        if ly_do:
            raise LoiChoEngine(self.engine, ly_do, uoc)
        if su_co.phan_loai(loi) not in _LOAI_CHO_NGAN:
            return
        bay_gio = float(self._dong_ho())
        with self._khoa:
            if self._tu is None:
                self._tu = bay_gio
            da = bay_gio - self._tu
        if da >= self.cho_ngan:
            raise LoiChoEngine(self.engine, "máy chủ trục trặc liên tục {0:.0f} phút: {1}".format(
                da / 60.0, str(loi)[:250]), uoc_hang_cho_giay(str(loi)))

    def boc(self, ham: Callable[..., Any]) -> Callable[..., Any]:
        def goi(*a: Any, **kw: Any) -> Any:
            try:
                ra = ham(*a, **kw)
            except Exception as loi:  # noqa: BLE001 — xét rồi ném lại nguyên lỗi
                self.xet(loi)
                raise
            self.tot()
            return ra
        return goi


def giay_tham_do(so_lan: int, uoc_giay: Optional[float] = None) -> float:
    """Bao lâu nữa thì thăm dò lại, sau lần chờ thứ `so_lan` (1 = lần đầu)."""
    i = max(0, min(int(so_lan or 1) - 1, len(NHIP_THAM_DO_GIAY) - 1))
    giay = NHIP_THAM_DO_GIAY[i]
    if uoc_giay:
        giay = max(giay, min(float(uoc_giay) / 2.0, TRAN_THAM_DO_GIAY))
    return giay


def tham_do_nhanh(client: Any, engine: str) -> str:
    """Thăm dò RẺ (`GET /v1/me`, không tốn tiền): máy chủ khai trần job `engine` = 0 → trả lý do
    (nhà máy đang dừng); còn lại (kể cả hỏi không được) → "" (để lời gọi thật quyết)."""
    if client is None or not hasattr(client, "request"):
        return ""
    try:
        tra = client.request("GET", "/v1/me")
        goi = tra.to_dict() if hasattr(tra, "to_dict") else dict(tra)
        han = goi.get("limits") or {}
        cj = han.get("concurrent_jobs") or {}
        if not isinstance(cj, dict) or engine not in cj:
            return ""
        if int(cj.get(engine) or 0) > 0:
            return ""
        ct = ((han.get("concurrent_jobs_detail") or {}).get(engine) or {})
        ly = str(ct.get("reason") or "").strip() if isinstance(ct, dict) else ""
        return "máy chủ khai trần job {0} = 0 (nhà máy đang dừng){1}".format(
            engine, ": " + ly[:200] if ly else "")
    except Exception:  # noqa: BLE001 — thăm dò hỏng thì để lời gọi thật quyết
        return ""


def dau_cua(goc: str, engine: str, kenh: str) -> Dict[str, Any]:
    """Dấu chờ `engine` của kênh (rỗng nếu không có, hay thiếu gốc/mã kênh)."""
    if not goc or not kenh:
        return {}
    return dict(khe.doc_cho_engine(goc, engine).get(str(kenh or "")) or {})


def bao_cho(goc: str, kenh: str, loi: LoiChoEngine, *, ma_luot: str = "", khau: str = "",
            ghi: Optional[Callable[[str], None]] = None,
            bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Ghi/làm mới dấu chờ engine cho lượt `ma_luot` của kênh, một dòng nhật ký, báo người một lần
    nếu đã chờ liền ≥ `GIO_BAO_CHO_LAU`. Trả dấu vừa ghi. Không ném lỗi."""
    bay_gio = _gio() if bay_gio is None else float(bay_gio)
    engine = loi.engine
    if not goc or not kenh:
        return {}
    cu = dau_cua(goc, engine, kenh)
    cung_luot = bool(cu) and str(cu.get("ma_luot") or "") == str(ma_luot or "")
    so_lan = int(cu.get("so_lan") or 0) + 1 if cung_luot else 1
    try:
        tu_luc = float(cu.get("tu_luc") or bay_gio) if cung_luot else bay_gio
    except (TypeError, ValueError):
        tu_luc = bay_gio
    giay = giay_tham_do(so_lan, loi.uoc_giay)
    tham = bay_gio + giay
    iso = lambda t: _dt.datetime.fromtimestamp(t).isoformat(timespec="seconds")  # noqa: E731
    da_bao = bool(cu.get("da_bao")) if cung_luot else False
    du = {"ma_luot": str(ma_luot or ""), "khau": str(khau or ""), "ly_do": loi.ly_do[:400],
          "tu": iso(tu_luc), "tu_luc": tu_luc, "tham_do": iso(tham), "tham_do_luc": tham,
          "so_lan": so_lan, "uoc_hang_cho_giay": loi.uoc_giay, "da_bao": da_bao}
    gio_cho = (bay_gio - tu_luc) / 3600.0
    if not da_bao and gio_cho >= GIO_BAO_CHO_LAU:
        du["da_bao"] = True
        _bao_cho_lau(goc, kenh, engine, gio_cho, loi.ly_do)
    khe.ghi_cho_engine(goc, engine, kenh, du)
    if ghi is not None:
        try:
            ghi("  [CHỜ ENGINE] engine {0} của cổng chưa phục vụ được ({1}) — lưu tiến độ, NHẢ LÀN, "
                "thoát; điều phối thăm dò lại lúc {2} (lần chờ {3}, đã chờ {4:.1f} giờ). Không đổi "
                "giọng/engine khác, không tính là hỏng.".format(
                    engine, loi.ly_do[:160], _dt.datetime.fromtimestamp(tham).strftime("%d/%m %H:%M"),
                    so_lan, gio_cho))
        except Exception:  # noqa: BLE001
            pass
    return du


def _bao_cho_lau(goc: str, kenh: str, engine: str, gio: float, ly_do: str) -> None:
    try:
        from . import bao_dong  # noqa: PLC0415

        bao_dong.bao_dong(
            "cho_engine_lau",
            "Kênh {0}: engine {1} của cổng chưa phục vụ được đã {2:.0f} giờ.".format(kenh, engine, gio),
            "Tool tự thăm dò và làm nốt khi engine có lại; lượt không giữ làn (kênh khác vẫn chạy), "
            "video ra muộn hơn lịch, không đổi giọng/engine khác. Câu máy chủ: {0}".format(ly_do[:200]),
            goc=goc, kenh=kenh, muc=bao_dong.MUC_NHAC)
    except Exception:  # noqa: BLE001
        pass


def xoa(goc: str, engine: str, kenh: str) -> None:
    """Khâu đã qua được engine — gỡ dấu chờ (không có thì thôi)."""
    if not goc or not kenh:
        return
    khe.xoa_cho_engine(goc, engine, kenh)
