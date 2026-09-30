"""core/uu_tien.py — tính mức ưu tiên P0..P4 cho khe tài nguyên (`core/khe.py`).

═══ MODULE THUẦN — CHƯA NỐI VÀO LUỒNG SỐNG ═══

Việc 1.3a của `workspace/LO-TRINH-PHAT-HANH-V3.md` (Đợt 1). Chỉ có hàm thuần
(không đĩa, không mạng, không Qt) — mọi thông tin thời gian đều do nơi gọi tự
đo và truyền vào, để bài kiểm không phải giả đồng hồ hệ thống. Cách nối (nơi
nào tính rồi truyền `uu_tien=` cho `core.khe.giu`) ghi ở
`workspace/ban-va/2026-09-29-dot1-khe-uu-tien/GHI-CHU.md`.

═══ THANG P0..P4 (chốt ở "Luật điều phối" trong lộ trình) ═══

    P0  VIEC_TAI_LEN — còn CHƯA TỚI `bien_xu_ly_gio` (mặc định 12h) tới khe
        công khai đã chọn cho video này.
    P1  VIEC_TAI_LEN — còn > bien nhưng < 24h tới khe công khai.
        HOẶC VIEC_QUET — phiên quét NGÀY HÔM NAY CHƯA CHẠY, và đã QUA giờ hẹn
        `gio_quet`.
    P2  VIEC_DUNG / VIEC_PHU_DE — theo khe công khai TRỐNG SỚM NHẤT của CẢ
        KÊNH (không phải video cụ thể): còn < 24h thì P2; xa hơn hoặc không
        biết thì P4. Không bao giờ vượt lên P0/P1 — hai mức đó dành riêng cho
        chính việc TẢI LÊN, dựng/phụ đề chỉ là bước chuẩn bị cho nó.
    P3  VIEC_TAI_LEN — còn >= 24h tới khe công khai (hoặc không biết còn bao
        lâu — an toàn hơn là lỡ giành chỗ của một việc thật sự gấp).
    P4  VIEC_NEN, VIEC_QUET (đã chạy hôm nay hoặc chưa tới giờ hẹn), hay bất
        kỳ `viec` lạ nào — mặc định KHÔNG gấp.

Số CÀNG NHỎ CÀNG GẤP (khớp `core/khe.py`: khoá sắp xếp hàng chờ dùng trực
tiếp số này, nhỏ nhất đứng đầu).

═══ LÃO HOÁ ═══

Việc chờ càng lâu càng cần được ưu tiên hơn — mỗi 2 giờ ĐÃ CHỜ (không phải
quãng còn lại tới hạn) thì +1 bậc (số P giảm 1), sàn ở P0. `tinh_uu_tien()` áp
lão hoá lên trên kết quả `uu_tien_co_ban()`.
"""

from __future__ import annotations

from typing import Optional

__all__ = [
    "P0", "P1", "P2", "P3", "P4",
    "VIEC_TAI_LEN", "VIEC_QUET", "VIEC_DUNG", "VIEC_PHU_DE", "VIEC_NEN",
    "BIEN_XU_LY_GIO_MAC_DINH", "NGUONG_24H_GIO", "LAO_HOA_MOI_GIO",
    "uu_tien_co_ban", "lao_hoa", "tinh_uu_tien",
]

P0, P1, P2, P3, P4 = 0, 1, 2, 3, 4

#: Tên việc nhận biết được — `viec` lạ (không khớp cái nào) luôn rơi về P4.
VIEC_TAI_LEN = "tai_len"
VIEC_QUET = "quet"
VIEC_DUNG = "dung"
VIEC_PHU_DE = "phu_de"
VIEC_NEN = "nen"

#: `bien_xu_ly_gio` mặc định — khớp khoá cấu hình cùng tên trong lộ trình
#: (Đợt 2 mục 2.2, `core/xep_lich.py`, chưa tồn tại — module này chỉ dùng số
#: mặc định làm chỗ dựa khi nơi gọi chưa truyền).
BIEN_XU_LY_GIO_MAC_DINH = 12.0

#: Ngưỡng phân biệt P1/P3 cho việc tải lên, và P2/P4 cho dựng/phụ đề.
NGUONG_24H_GIO = 24.0

#: Lão hoá: +1 bậc ưu tiên (số P giảm 1) mỗi ngần này giờ ĐÃ CHỜ.
LAO_HOA_MOI_GIO = 2.0


def _tu_gio_con_lai(gio_con_lai: Optional[float], bien_xu_ly_gio: float,
                    muc_gan: int, muc_trong_24h: int, muc_xa: int) -> int:
    """Quy đổi "còn bao nhiêu giờ tới khe công khai" -> một trong ba mức.

    Không biết còn bao lâu (`gio_con_lai is None`) thì coi như XA — an toàn
    hơn hẳn giành chỗ ẩu của một việc chưa chắc đã gấp.
    """
    if gio_con_lai is None:
        return muc_xa
    if gio_con_lai < bien_xu_ly_gio:
        return muc_gan
    if gio_con_lai < NGUONG_24H_GIO:
        return muc_trong_24h
    return muc_xa


def uu_tien_co_ban(viec: str, *,
                   gio_con_lai: Optional[float] = None,
                   da_chay_hom_nay: Optional[bool] = None,
                   da_qua_gio_quet: Optional[bool] = None,
                   bien_xu_ly_gio: float = BIEN_XU_LY_GIO_MAC_DINH) -> int:
    """Ưu tiên P0..P4 CHƯA lão hoá, theo loại `viec`.

    `viec="tai_len"` — cần `gio_con_lai` (số giờ tới khe công khai ĐÃ CHỌN
    cho đúng video này): < `bien_xu_ly_gio` -> P0; < 24h -> P1; còn lại (kể cả
    không biết) -> P3.

    `viec="quet"` — cần `da_chay_hom_nay` (phiên quét ngày của kênh đã chạy
    chưa) và `da_qua_gio_quet` (đã qua giờ hẹn `gio_quet` chưa). CHƯA chạy VÀ
    đã qua giờ hẹn -> P1; mọi trường hợp khác (đã chạy rồi, hoặc chưa tới giờ)
    -> P4. Thiếu một trong hai cờ thì coi như "chưa đủ điều kiện gấp" -> P4
    (an toàn — không tự suy đoán khi thiếu dữ liệu).

    `viec="dung"`/`"phu_de"` — cần `gio_con_lai` = số giờ tới khe công khai
    TRỐNG SỚM NHẤT của cả kênh (không phải của video này): < 24h -> P2; xa
    hơn hoặc không biết -> P4. Không bao giờ chạm P0/P1 (dành riêng cho chính
    việc tải lên).

    `viec` khác (kể cả `"nen"`) -> luôn P4.
    """
    if viec == VIEC_TAI_LEN:
        return _tu_gio_con_lai(gio_con_lai, bien_xu_ly_gio,
                               muc_gan=P0, muc_trong_24h=P1, muc_xa=P3)
    if viec == VIEC_QUET:
        if da_chay_hom_nay is False and da_qua_gio_quet is True:
            return P1
        return P4
    if viec in (VIEC_DUNG, VIEC_PHU_DE):
        return _tu_gio_con_lai(gio_con_lai, NGUONG_24H_GIO,
                               muc_gan=P2, muc_trong_24h=P2, muc_xa=P4)
    return P4


def lao_hoa(muc: int, gio_da_cho: float) -> int:
    """+1 bậc (số P giảm 1) mỗi `LAO_HOA_MOI_GIO` giờ ĐÃ CHỜ, sàn ở P0.

    `gio_da_cho` <= 0 (chưa chờ, hoặc số âm gõ nhầm) thì trả nguyên `muc`.
    """
    if gio_da_cho is None or gio_da_cho <= 0:
        return max(P0, min(P4, int(muc)))
    buoc = int(gio_da_cho // LAO_HOA_MOI_GIO)
    return max(P0, min(P4, int(muc) - buoc))


def tinh_uu_tien(viec: str, *,
                 gio_con_lai: Optional[float] = None,
                 da_chay_hom_nay: Optional[bool] = None,
                 da_qua_gio_quet: Optional[bool] = None,
                 bien_xu_ly_gio: float = BIEN_XU_LY_GIO_MAC_DINH,
                 gio_da_cho: float = 0.0) -> int:
    """`uu_tien_co_ban()` rồi áp `lao_hoa()` — hàm một cửa cho nơi gọi."""
    co_ban = uu_tien_co_ban(viec, gio_con_lai=gio_con_lai,
                            da_chay_hom_nay=da_chay_hom_nay,
                            da_qua_gio_quet=da_qua_gio_quet,
                            bien_xu_ly_gio=bien_xu_ly_gio)
    return lao_hoa(co_ban, gio_da_cho)
