"""Nhường phiên kênh (`core/nhuong_phien_kenh.py`) — sản xuất không bỏ đói
`vm/agent.py`.

Chẩn đoán 28/09/2026: không mạng, chỉ dựng `vm/config.json` + `vm/trang-thai.json`
giả trong `tmp_path` (đúng luật 3 CLAUDE.md).
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from core.nhuong_phien_kenh import (TRAN_GIO_CHO_PHIEN_MAC_DINH, danh_sach_kenh_vm,
                                    doc_cau_hinh_vm, doc_trang_thai_vm,
                                    kenh_phien_can_nhuong)


def _ghi_vm_config(goc, **cai):
    thu_muc = os.path.join(goc, "vm")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "config.json"), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


def _ghi_vm_trang_thai(goc, **cai):
    thu_muc = os.path.join(goc, "vm")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


# ── doc_cau_hinh_vm / doc_trang_thai_vm / danh_sach_kenh_vm ─────────────────


def test_doc_cau_hinh_vm_khong_co_vm_thi_rong(tmp_path):
    assert doc_cau_hinh_vm(str(tmp_path)) == {}


def test_danh_sach_kenh_vm_uu_tien_cac_kenh():
    assert danh_sach_kenh_vm({"cac_kenh": ["TL1-T7", "TL2-T7", "TL1-T7"]}) == ["TL1-T7", "TL2-T7"]


def test_danh_sach_kenh_vm_ve_kenh_don_khi_khong_co_cac_kenh():
    assert danh_sach_kenh_vm({"kenh": "TL4-T7"}) == ["TL4-T7"]
    assert danh_sach_kenh_vm({}) == []


# ── kenh_phien_can_nhuong ────────────────────────────────────────────────────


def test_khong_co_vm_thi_khong_can_nhuong(tmp_path):
    can_cho, qua_tran = kenh_phien_can_nhuong(str(tmp_path))
    assert can_cho == [] and qua_tran == []


def test_kenh_den_han_chua_chay_thi_can_nhuong(tmp_path):
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-27",  # chưa chạy hôm nay
        "phien_muc_tieu@TL1-T7@2026-09-28": "07:30",
    })
    can_cho, qua_tran = kenh_phien_can_nhuong(
        goc, bay_gio=_dt.datetime(2026, 9, 28, 10, 0))  # đã qua 07:30, mới quá hạn 2,5 giờ
    assert can_cho == ["TL1-T7"]
    assert qua_tran == []


def test_kenh_da_chay_hom_nay_thi_khong_can_nhuong(tmp_path):
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-28",  # đã chạy hôm nay rồi
        "phien_muc_tieu@TL1-T7@2026-09-28": "07:30",
    })
    can_cho, qua_tran = kenh_phien_can_nhuong(goc, bay_gio=_dt.datetime(2026, 9, 28, 10, 0))
    assert can_cho == [] and qua_tran == []


def test_chua_toi_gio_muc_tieu_thi_chua_can_nhuong(tmp_path):
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-27",
        "phien_muc_tieu@TL1-T7@2026-09-28": "07:30",
    })
    can_cho, qua_tran = kenh_phien_can_nhuong(goc, bay_gio=_dt.datetime(2026, 9, 28, 6, 0))
    assert can_cho == [] and qua_tran == []


def test_chua_co_moc_muc_tieu_hom_nay_thi_chua_biet_khong_chan(tmp_path):
    """Agent chưa kịp tính giờ mục tiêu hôm nay (chưa gọi `/ke-hoach` lần nào)
    — coi như CHƯA BIẾT, không chặn sản xuất vì một thứ không chắc."""
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{"phien_cuoi@TL1-T7": "2026-09-27"})
    can_cho, qua_tran = kenh_phien_can_nhuong(goc, bay_gio=_dt.datetime(2026, 9, 28, 10, 0))
    assert can_cho == [] and qua_tran == []


def test_qua_tran_gio_cho_thi_thoi_nhuong(tmp_path):
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-27",
        "phien_muc_tieu@TL1-T7@2026-09-28": "07:30",
    })
    # 07:30 + 6 giờ = 13:30; bay_gio 14:00 -> đã quá trần mặc định.
    can_cho, qua_tran = kenh_phien_can_nhuong(goc, bay_gio=_dt.datetime(2026, 9, 28, 14, 0))
    assert can_cho == []
    assert qua_tran == ["TL1-T7"]


def test_tran_gio_cho_tuy_chinh_duoc(tmp_path):
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-27",
        "phien_muc_tieu@TL1-T7@2026-09-28": "07:30",
    })
    can_cho, qua_tran = kenh_phien_can_nhuong(
        goc, bay_gio=_dt.datetime(2026, 9, 28, 9, 0), tran_gio_cho=1.0)
    assert can_cho == []
    assert qua_tran == ["TL1-T7"]


def test_nhieu_kenh_tron_lan_can_cho_va_qua_tran(tmp_path):
    """Trần giờ chờ tính theo GIỜ MỤC TIÊU của TỪNG kênh — hai kênh khác giờ
    mục tiêu (dù cùng chưa chạy hôm nay) có thể rơi vào hai nhóm khác nhau
    tại CÙNG một `bay_gio`."""
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7", "TL2-T7", "TL3-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-28",  # đã chạy hôm nay -> không cần xét
        "phien_muc_tieu@TL1-T7@2026-09-28": "07:30",
        "phien_cuoi@TL2-T7": "2026-09-27",  # mục tiêu 10:00, bay_gio 15:00 -> mới quá 5 giờ
        "phien_muc_tieu@TL2-T7@2026-09-28": "10:00",
        "phien_cuoi@TL3-T7": "2026-09-27",  # mục tiêu 06:00, bay_gio 15:00 -> đã quá 9 giờ
        "phien_muc_tieu@TL3-T7@2026-09-28": "06:00",
    })
    can_cho, qua_tran = kenh_phien_can_nhuong(goc, bay_gio=_dt.datetime(2026, 9, 28, 15, 0))
    assert can_cho == ["TL2-T7"]
    assert qua_tran == ["TL3-T7"]


def test_khoa_gio_muc_tieu_sai_dang_thi_bo_qua_khong_loi(tmp_path):
    goc = str(tmp_path)
    _ghi_vm_config(goc, cac_kenh=["TL1-T7"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@TL1-T7": "2026-09-27",
        "phien_muc_tieu@TL1-T7@2026-09-28": "không phải giờ hợp lệ",
    })
    can_cho, qua_tran = kenh_phien_can_nhuong(goc, bay_gio=_dt.datetime(2026, 9, 28, 10, 0))
    assert can_cho == [] and qua_tran == []
