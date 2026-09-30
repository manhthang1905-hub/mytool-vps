"""`core/ke_hoach_dang.py` — kế hoạch đăng video (nguồn thay trang tính).

Việc C, 29/09/2026 (`workspace/THIET-KE-MAY-DANG-DOM.md` mục 10): sửa lỗi
`doc_bang` dùng `csv.reader(chu.splitlines())` cắt đứt xuống dòng THẬT bên
trong ô Mô tả (khối 📌目次 để YouTube nhận chương) mỗi lần `danh_dau` ghi lại
kế hoạch — và thêm cột "Video ID" cuối `COT` cho máy đăng DOM.
"""

from __future__ import annotations

import os

from core import ke_hoach_dang as kh


def test_xuong_dong_trong_mo_ta_giu_nguyen_qua_doc_ghi(tmp_path):
    """Lỗi thật 29/09/2026: `csv.reader(chu.splitlines())` cắt chuỗi thành
    từng DÒNG trước khi đưa cho `csv.reader` — xoá mất xuống dòng bên trong
    một ô đã bọc ngoặc kép. `io.StringIO` phải giữ nguyên."""
    goc = str(tmp_path)
    mo_ta = "Dòng mở đầu.\n\n📌目次\n00:00 Mở đầu\n01:23 Phần 1\n\nCảm ơn đã xem!"
    hang = [["TL1-T7-0007", "30/09/2026", "20:00", "Tiêu đề", mo_ta, "seo",
            "", "", "", "", "x", "", ""]]
    kh.luu_bang(goc, "TL1-T7", hang, kh.COT)

    cot, hang2 = kh.doc_bang(goc, "TL1-T7")
    o_mo_ta = cot.index("Mô tả")
    assert hang2[0][o_mo_ta] == mo_ta
    assert hang2[0][o_mo_ta].count("\n") == mo_ta.count("\n")


def test_xuong_dong_song_qua_nhieu_lan_danh_dau(tmp_path):
    """Đúng kịch bản hỏng thật: ghi kế hoạch MỘT lần, rồi `danh_dau` (máy ảo
    báo về) ghi LẠI nhiều lần — xuống dòng của Mô tả không được rụng dần."""
    goc = str(tmp_path)
    mo_ta = "Mở đầu\n\n📌目次\n00:00 A\n05:00 B\n\nKết"
    hang = [["TL1-T7-0007", "30/09/2026", "20:00", "Tiêu đề", mo_ta, "seo",
            "", "", "", "", "x", "", ""]]
    kh.luu_bang(goc, "TL1-T7", hang, kh.COT)

    for _ in range(3):
        kh.danh_dau(goc, "TL1-T7", "TL1-T7-0007", "ĐANG ĐĂNG · nháp abc")

    cot, hang2 = kh.doc_bang(goc, "TL1-T7")
    assert hang2[0][cot.index("Mô tả")] == mo_ta, \
        "mô tả không được đổi/mất xuống dòng chỉ vì danh_dau ghi lại nhiều lần"


def test_cot_video_id_o_cuoi_cot_mac_dinh():
    assert kh.COT[-1] == "Video ID"
    assert kh.COT[:-1] == ("Mã gói", "Ngày đăng", "Giờ đăng", "Tiêu đề", "Mô tả",
                           "Thẻ SEO", "Link card 1", "Link card 2", "Link card 3",
                           "Link card 4", "Sẵn sàng", "Trạng thái đăng", "Ghi chú")


def test_danh_dau_ghi_video_id(tmp_path):
    goc = str(tmp_path)
    hang = [["TL1-T7-0007", "30/09/2026", "20:00", "T", "M", "seo",
            "", "", "", "", "x", "", ""]]
    kh.luu_bang(goc, "TL1-T7", hang, kh.COT)

    ok = kh.danh_dau(goc, "TL1-T7", "TL1-T7-0007", "ĐÃ ĐĂNG", video_id="abcDEF123")
    assert ok is True

    cot, hang2 = kh.doc_bang(goc, "TL1-T7")
    assert "Video ID" in cot
    dong = hang2[0]
    assert dong[cot.index("Trạng thái đăng")] == "ĐÃ ĐĂNG"
    assert dong[cot.index("Video ID")] == "abcDEF123"


def test_danh_dau_nang_cap_ke_hoach_cu_chua_co_cot_video_id(tmp_path):
    """Kế hoạch trên đĩa được ghi TRƯỚC khi cột "Video ID" ra đời (13 cột cũ)
    — `danh_dau(..., video_id=...)` phải tự thêm cột, không đòi ai mở Excel
    sửa tay trước."""
    goc = str(tmp_path)
    cot_cu = ("Mã gói", "Ngày đăng", "Giờ đăng", "Tiêu đề", "Mô tả", "Thẻ SEO",
              "Link card 1", "Link card 2", "Link card 3", "Link card 4",
              "Sẵn sàng", "Trạng thái đăng", "Ghi chú")
    hang = [["TL1-T7-0007", "30/09/2026", "20:00", "T", "M", "seo",
            "", "", "", "", "x", "", ""]]
    kh.luu_bang(goc, "TL1-T7", hang, cot_cu)

    ok = kh.danh_dau(goc, "TL1-T7", "TL1-T7-0007", "ĐÃ ĐĂNG", video_id="xyz789")
    assert ok is True
    cot, hang2 = kh.doc_bang(goc, "TL1-T7")
    assert cot[-1] == "Video ID"
    assert hang2[0][cot.index("Video ID")] == "xyz789"


def test_danh_dau_khong_video_id_khong_dung_cot_moi(tmp_path):
    """`may_dang.py` (đường ảnh) gọi `danh_dau` KHÔNG kèm `video_id` — kế
    hoạch cũ (13 cột) không bị đổi khuôn chỉ vì một lượt báo không liên quan
    tới videoId."""
    goc = str(tmp_path)
    cot_cu = list(kh.COT[:-1])
    hang = [["TL1-T7-0007", "30/09/2026", "20:00", "T", "M", "seo",
            "", "", "", "", "x", "", ""]]
    kh.luu_bang(goc, "TL1-T7", hang, cot_cu)

    ok = kh.danh_dau(goc, "TL1-T7", "TL1-T7-0007", "ĐÃ ĐĂNG")
    assert ok is True
    cot, hang2 = kh.doc_bang(goc, "TL1-T7")
    assert "Video ID" not in cot
    assert hang2[0][cot.index("Trạng thái đăng")] == "ĐÃ ĐĂNG"


def test_danh_dau_khong_thay_ma_thi_false(tmp_path):
    goc = str(tmp_path)
    kh.luu_bang(goc, "TL1-T7", [], kh.COT)
    assert kh.danh_dau(goc, "TL1-T7", "TL1-T7-9999", "ĐÃ ĐĂNG") is False
