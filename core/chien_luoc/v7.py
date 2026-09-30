"""Công thức V7 — cụm đang thắng + bảng đề xuất của CHÍNH kênh (kênh đã có chỉ số).

Thân nhánh V7 cũ của `tu_chay.ung_vien_xep_hang`, dời nguyên văn: chỉ nhận `loai` "Làm ngay" /
"Nên làm" và dòng không bị loại ở cổng nào; lọc chung (`nc.loc`); rồi cộng điểm anh em trong nhóm
(`tu_chay._cong_diem_anh_em_an_toan`, chạy SAU lọc vì trần "tự thắng" tính trên bảng đã lọc).

Hỏng hay rỗng thì trả `[]` và KHÔNG lùi (`LUI_KHI_RONG = ""`): kênh đã có V7 thì bảng Một nút không
mang phán đoán của V7 (cụm đang thắng, bảng đề xuất, nguồn nổ thật…).
"""

from __future__ import annotations

from typing import Any, Dict, List

TEN = "v7"
MO_TA = "Công thức V7 — cụm đang thắng + bảng đề xuất của kênh (kênh đang lên, có chỉ số)"
LUI_KHI_RONG = ""


def ap_dung(nc: Any) -> float:
    if not nc.co_v7:
        return 0.0
    return {"dang_len": 1.0, "kiem_tien": 0.8}.get(nc.giai_doan, 1.0)


def cham(nc: Any) -> List[Dict[str, Any]]:
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415
    from .. import doi_thu_kenh as so  # noqa: PLC0415
    from .. import tu_chay  # noqa: PLC0415 — nhập muộn: tu_chay nhập gói này lúc nạp

    try:
        kq = (nc.cham_v7 or v7.cham)(nc.goc, nc.ma_kenh)
    except Exception as loi:  # noqa: BLE001
        nc.ghi("  Công thức V7 hỏng ({0}) — không có nguồn hôm nay (kênh đã có cấu hình V7, "
               "không rơi về bảng Một nút vì bảng đó không mang phán đoán của V7).".format(
                   str(loi)[:120]))
        return []
    ra: List[Dict[str, Any]] = []
    for d in getattr(kq, "ung_vien", None) or []:
        if getattr(d, "bi_loai", ""):
            continue
        if str(getattr(d, "loai", "")) not in (v7.LAM_NGAY, v7.NEN_LAM):
            continue
        ma = str(getattr(d, "ma", "") or so.ma_video(str(getattr(d, "link", "") or "")))
        ra.append({"nguon": "v7", "ma": ma, "link": str(getattr(d, "link", "") or ""),
                   "tieu_de": str(getattr(d, "tieu_de", "") or ""),
                   "kenh": str(getattr(d, "kenh", "") or ""),
                   "diem": getattr(d, "diem", 0), "loai": str(getattr(d, "loai", "") or ""),
                   # Điểm cụm CỦA CHÍNH KÊNH MÌNH — để `cong_diem_anh_em` biết ứng viên nào TỰ THẮNG.
                   "diem_cum": float(getattr(d, "diem_cum", 0) or 0),
                   # Kênh anh em đã cho điểm cụm THỪA HƯỞNG — `cong_diem_anh_em` bỏ qua dòng này.
                   "thua_huong": str(getattr(d, "thua_huong", "") or ""),
                   "cum": list(getattr(d, "cum", None) or []),
                   "view": float(getattr(d, "view", 0) or 0),
                   "ly_do": list(getattr(d, "ly_do", None) or [])})
    ra = nc.loc(ra)
    if not ra:
        nc.ghi("  Công thức V7: không có ứng viên nào đạt “{0}” trở lên — không có nguồn hôm nay "
               "(kênh đã có cấu hình V7, không rơi về bảng Một nút).".format(v7.NEN_LAM))
    return tu_chay._cong_diem_anh_em_an_toan(nc.goc, nc.ma_kenh, ra, True, nc.ghi)
