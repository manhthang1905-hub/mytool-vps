"""Nhường phiên kênh (`vm/agent.py`) — sản xuất không được bỏ đói agent.

═══ VÌ SAO CÓ TỆP NÀY (chẩn đoán 28/09/2026) ═══

`tu_chay.py --tat-ca` (sản xuất) và phiên kênh của `vm/agent.py` (quét Studio
— NGUỒN DỮ LIỆU của cả vòng học — và đăng theo lịch) dùng CHUNG một khoá máy
(`.khoa-may`/`giu_khoa_may_chung`). Kịch bản xấu đo thật 28/09/2026: sản xuất
mở một lượt MỚI (một video có thể mất NHIỀU GIỜ) đúng lúc một kênh có phiên
đến hạn (quét Studio, hoặc ĐĂNG THEO LỊCH đã hẹn giờ) — khoá bị giữ suốt thời
gian đó, phiên kênh không bao giờ chen được vào (`vm.agent.chay_hang_doi_phien`
mỗi nhịp tim chỉ thử MỘT kênh, xem chẩn đoán "việc C" cùng ngày), lỡ mất giờ
đăng đã hẹn hoặc để kho dữ liệu học khô cạn.

Sửa ở TẦNG SẢN XUẤT (không đợi sửa xong hàng đợi phiên bên `vm/`, việc đó là
việc riêng — xem `vm/agent.py chay_hang_doi_phien`): trước khi
`core.tu_chay` mở một lượt sản xuất MỚI (chưa hề bắt tay vào làm — phân biệt
với một lượt ĐANG DỞ đã trót đổ tiền vào, xem `core.tu_chay._chay_mot_ngay_trong_khoa`),
kiểm xem có kênh nào đang chờ tới lượt phiên hôm nay không; có thì NHƯỜNG —
tự thoát sớm, không giành khoá, để nhịp tim tiếp theo của `vm/agent.py` (chạy
mỗi 30 giây) có cơ hội chen vào.

═══ ĐỌC LẠI ĐÚNG NGUỒN `vm/agent.py` DÙNG, KHÔNG GỌI TRẠM ═══

`vm.agent._muc_tieu_phien_hom_nay` tính "giờ mục tiêu phiên hôm nay" của một
kênh bằng MỘT lượt gọi trạm cục bộ (`GET /ke-hoach`, mỗi ngày một lần) rồi CẤT
vào `vm/trang-thai.json` (khoá `phien_muc_tieu@<kênh>@<ngày>`); nhịp tim sau
chỉ đọc lại mốc đã cất (`vm.agent.den_gio_phien`). Mô-đun này đi ĐÚNG đường
đọc lại đó — KHÔNG tự gọi trạm, KHÔNG import `vm/agent.py` (tệp đó nặng, kéo
theo PyAutoGUI/Chrome DevTools — không phù hợp cho tiến trình sản xuất). Kênh
chưa có mốc hôm nay (agent chưa kịp tính, hoặc máy này không chạy `vm/`) thì
coi là "chưa biết" — KHÔNG chặn sản xuất vì một thứ không chắc (an toàn hơn:
thà bỏ sót một lần nhường còn hơn treo sản xuất vì đoán bừa).

═══ TRẦN AN TOÀN: AGENT CHẾT/TREO KHÔNG ĐƯỢC PHÉP TREO LUÔN SẢN XUẤT ═══

Một kênh "đến hạn" mà chờ quá `TRAN_GIO_CHO_PHIEN_MAC_DINH` (mặc định 6 giờ)
vẫn chưa thấy `phien_cuoi@<kênh>` nhích lên hôm nay thì coi như agent đã
chết/treo — thôi nhường, để sản xuất chạy bình thường (kèm cảnh báo nơi gọi
tự ghi), tránh một agent hỏng làm đứng luôn cả dây chuyền sản xuất.

Không mạng, không Qt — chỉ đọc `vm/config.json` + `vm/trang-thai.json`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["TRAN_GIO_CHO_PHIEN_MAC_DINH", "doc_cau_hinh_vm", "doc_trang_thai_vm",
           "danh_sach_kenh_vm", "kenh_phien_can_nhuong"]

#: Kênh "đến hạn" mà chờ quá ngần này GIỜ vẫn chưa chạy thì coi như agent đã
#: chết/treo — thôi nhường (xem "TRẦN AN TOÀN" ở đầu tệp).
TRAN_GIO_CHO_PHIEN_MAC_DINH = 6.0


def _duong_vm(goc: str) -> str:
    return os.path.join(goc, "vm")


def doc_cau_hinh_vm(goc: str) -> Dict[str, Any]:
    """`vm/config.json` — rỗng nếu máy này không có `vm/` (không chạy phiên
    kênh nào) hay tệp hỏng. Không phải lỗi — nhiều máy dev/test không có `vm/`."""
    try:
        with open(os.path.join(_duong_vm(goc), "config.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def doc_trang_thai_vm(goc: str, cau_hinh: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """`vm/trang-thai.json` (hay đúng `thu_muc_du_lieu` nếu cấu hình có đổi
    chỗ) — đúng tệp `vm.agent._doc_trang_thai` đọc. Rỗng nếu thiếu/hỏng."""
    cau_hinh = cau_hinh if cau_hinh is not None else doc_cau_hinh_vm(goc)
    thu_muc_rieng = str(cau_hinh.get("thu_muc_du_lieu") or "").strip()
    thu_muc = thu_muc_rieng if thu_muc_rieng else _duong_vm(goc)
    try:
        with open(os.path.join(thu_muc, "trang-thai.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def danh_sach_kenh_vm(cau_hinh: Dict[str, Any]) -> List[str]:
    """Mọi kênh máy này phục vụ qua `vm/agent.py` — cùng luật
    `vm.agent.danh_sach_kenh` (`cac_kenh` bộ nhiều-kênh thắng nếu có, không
    thì kênh đơn `kenh`)."""
    nhieu = [str(k).strip() for k in (cau_hinh.get("cac_kenh") or []) if str(k).strip()]
    if nhieu:
        return list(dict.fromkeys(nhieu))
    don = str(cau_hinh.get("kenh") or "").strip()
    return [don] if don else []


def _phan_tich_hh_mm(chuoi: str) -> Optional[Tuple[int, int]]:
    try:
        gio_str, phut_str = str(chuoi).strip().split(":")
        gio, phut = int(gio_str), int(phut_str)
    except (ValueError, AttributeError, TypeError):
        return None
    if not (0 <= gio <= 23 and 0 <= phut <= 59):
        return None
    return gio, phut


def kenh_phien_can_nhuong(
    goc: str, *, bay_gio: Optional[_dt.datetime] = None,
    tran_gio_cho: float = TRAN_GIO_CHO_PHIEN_MAC_DINH,
) -> Tuple[List[str], List[str]]:
    """`(kênh đến hạn còn ĐÁNG nhường, kênh đến hạn đã QUÁ TRẦN chờ)`.

    Một kênh được coi là "đến hạn mà chưa chạy hôm nay" khi:

    1. `vm/trang-thai.json` có mốc `phien_muc_tieu@<kênh>@<hôm nay>` (agent đã
       tính giờ mục tiêu của hôm nay — thiếu mốc này thì BỎ QUA kênh đó, coi
       như "chưa biết", không chặn sản xuất vì một thứ không chắc).
    2. `phien_cuoi@<kênh>` KHÁC hôm nay (chưa chạy phiên nào hôm nay).
    3. Giờ hiện tại (`bay_gio`) đã qua mốc mục tiêu đó.

    Kênh thoả cả ba mà đã q hạn dưới `tran_gio_cho` giờ thì xếp vào phần tử
    ĐẦU (còn đáng chờ — nơi gọi nên NHƯỜNG); quá `tran_gio_cho` giờ thì xếp
    vào phần tử SAU (agent có thể đã chết/treo — nơi gọi tự quyết định cảnh
    báo rồi vẫn chạy sản xuất bình thường, xem "TRẦN AN TOÀN" đầu tệp).

    Không mạng — chỉ đọc hai tệp JSON. Không tìm được `vm/` (máy này không
    chạy phiên kênh nào) thì trả `([], [])` — không có gì để nhường.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    cau_hinh = doc_cau_hinh_vm(goc)
    if not cau_hinh:
        return [], []
    trang_thai = doc_trang_thai_vm(goc, cau_hinh)
    if not trang_thai:
        return [], []
    hom_nay = bay_gio.strftime("%Y-%m-%d")

    can_cho: List[str] = []
    qua_tran: List[str] = []
    for kenh in danh_sach_kenh_vm(cau_hinh):
        if str(trang_thai.get("phien_cuoi@" + kenh) or "") == hom_nay:
            continue  # đã chạy phiên hôm nay rồi — không còn "đến hạn"
        muc_tieu = trang_thai.get("phien_muc_tieu@{0}@{1}".format(kenh, hom_nay))
        if not isinstance(muc_tieu, str) or not muc_tieu:
            continue  # agent chưa tính mốc hôm nay — chưa biết, không chặn
        gio_phut = _phan_tich_hh_mm(muc_tieu)
        if gio_phut is None:
            continue
        moc = bay_gio.replace(hour=gio_phut[0], minute=gio_phut[1], second=0, microsecond=0)
        if bay_gio < moc:
            continue  # chưa tới giờ mục tiêu — chưa "đến hạn"
        gio_da_qua = (bay_gio - moc).total_seconds() / 3600.0
        if tran_gio_cho > 0 and gio_da_qua >= tran_gio_cho:
            qua_tran.append(kenh)
        else:
            can_cho.append(kenh)
    return can_cho, qua_tran
