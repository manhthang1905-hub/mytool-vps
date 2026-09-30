"""Công thức VPH — video đối thủ ĐỘT BIẾN view/giờ so với video cùng tuổi (bắt trend).

Lớp bọc mỏng quanh `core.cong_thuc_vph.ung_vien_chon_nguon` (thân công thức nằm ở đó). KHÔNG cộng
điểm anh em: VPH chọn theo đột biến của đối thủ, không theo cụm — trộn tín hiệu cụm vào đây là trộn
hai cách đánh vào một bảng. Rỗng thì bộ điều phối lùi về Một nút (`LUI_KHI_RONG`).
"""

from __future__ import annotations

from typing import Any, Dict, List

TEN = "vph"
MO_TA = "Công thức VPH — video đối thủ ĐỘT BIẾN view/giờ so với video cùng tuổi (trend)"
LUI_KHI_RONG = "mot_nut"


def ap_dung(nc: Any) -> float:
    return {"moi": 1.0, "dang_len": 0.4, "kiem_tien": 0.3}.get(nc.giai_doan, 0.4)


def _mac_dinh(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    from .. import cong_thuc_vph  # noqa: PLC0415 — nhập muộn: VPH đọc nhiều sổ

    return cong_thuc_vph.ung_vien_chon_nguon(goc, ma_kenh)


def cham(nc: Any) -> List[Dict[str, Any]]:
    try:
        ds = (nc.cham_vph or _mac_dinh)(nc.goc, nc.ma_kenh) or []
    except Exception as loi:  # noqa: BLE001 — công thức hỏng thì rơi về Một nút, không đứng kênh
        nc.ghi("  Công thức VPH hỏng ({0}) — dùng bảng Một nút.".format(str(loi)[:120]))
        ds = []
    ra = nc.loc(ds)
    if not ra:
        nc.ghi("  VPH: không có ứng viên đột biến chưa làm — dùng bảng Một nút cho lượt này.")
    return ra
