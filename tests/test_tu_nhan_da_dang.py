"""Tự nhận video đã đăng qua đối chiếu Studio (`core/tu_nhan_da_dang.py`).

Việc A, chẩn đoán 28/09/2026: chủ kênh đăng TAY trên YouTube, không qua tool
— không mạng, không tốn ví (chỉ đọc `chi-so/`, và khi `thuc_hien=True` ghi
`ke-hoach.csv` giả trong `tmp_path`, đúng luật 3 CLAUDE.md).
"""

from __future__ import annotations

import json
import os

from core import ban_giao_dang, ke_hoach_dang
from core.tu_nhan_da_dang import (chuan_hoa_tieu_de, doc_video_cong_khai_tren_kenh,
                                  tu_nhan_video_da_dang)


def _ghi_quet(goc, ma_kenh, ten_thu_muc, videos, ten_tep="get_creator_videos_alt_json_1.json"):
    thu_muc = os.path.join(goc, "CHANNEL", ma_kenh, "chi-so", "kenh", ten_thu_muc, "raw")
    os.makedirs(thu_muc, exist_ok=True)
    du = {"response": {"videos": videos}}
    with open(os.path.join(thu_muc, ten_tep), "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)


def _video(video_id, title, *, privacy="VIDEO_PRIVACY_PUBLIC", time_published=None):
    v = {"videoId": video_id, "title": title, "privacy": privacy}
    if time_published is not None:
        v["timePublishedSeconds"] = str(int(time_published))
    return v


def _ghi_ke_hoach(goc, ma_kenh, hang_dict_list):
    cot = list(ke_hoach_dang.COT)
    hang = []
    for d in hang_dict_list:
        dong = {ten: "" for ten in cot}
        dong.update(d)
        hang.append([dong[ten] for ten in cot])
    ke_hoach_dang.luu_bang(goc, ma_kenh, hang, cot)


# ── chuan_hoa_tieu_de ────────────────────────────────────────────────────────


def test_chuan_hoa_gop_full_width_half_width():
    a = chuan_hoa_tieu_de("【雑学】Test！ Video？")
    b = chuan_hoa_tieu_de("【雑学】Test! Video?")
    assert a == b


def test_chuan_hoa_gop_khoang_trang_thua():
    assert chuan_hoa_tieu_de("  Xin   chào   thế giới  ") == "xin chào thế giới"


def test_chuan_hoa_bo_dau_cau_van_giong_gan_tuyet_doi():
    """Dấu ngoặc CJK (「」) đổi thành khoảng trắng (không xoá trắng — tránh
    dính hai từ liền nhau ở tiếng Latin) nên chuỗi sau chuẩn hoá không hệt
    100% với bản không dấu ngoặc, nhưng độ giống (đúng thứ `tu_nhan_video_da_dang`
    dùng để khớp) vẫn rất cao — dấu câu không được phép lấn át nội dung."""
    from difflib import SequenceMatcher
    a = chuan_hoa_tieu_de("賢い人ほど「片付け」だけは自分でやる理由")
    b = chuan_hoa_tieu_de("賢い人ほど片付けだけは自分でやる理由")
    assert SequenceMatcher(None, a, b).ratio() >= 0.9


# ── doc_video_cong_khai_tren_kenh ────────────────────────────────────────────


def test_doc_video_bo_qua_ban_ghi_khong_co_title(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260925",
             [{"videoId": "abc", "permissions": {}}])  # mask hẹp, không title
    assert doc_video_cong_khai_tren_kenh(goc, "K1") == {}


def test_doc_video_bo_qua_video_rieng_tu(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260925",
             [_video("priv1", "Video riêng tư", privacy="VIDEO_PRIVACY_PRIVATE")])
    assert doc_video_cong_khai_tren_kenh(goc, "K1") == {}


def test_doc_video_lay_dung_video_cong_khai(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260925",
             [_video("pub1", "Video công khai", time_published=1790000000)])
    ra = doc_video_cong_khai_tren_kenh(goc, "K1")
    assert set(ra) == {"pub1"}
    assert ra["pub1"]["tieu_de"] == "Video công khai"
    assert ra["pub1"]["cong_khai_luc"] == 1790000000.0


def test_doc_video_ban_ghi_moi_nhat_thang(tmp_path):
    """Cùng videoId xuất hiện ở hai lượt quét khác ngày — giữ bản ở lượt quét
    MỚI NHẤT theo NGÀY trong tên thư mục, không theo bảng chữ cái (tránh
    "kenh-" luôn thắng "tay-" dù ngày cũ hơn)."""
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260920", [_video("v1", "Tiêu đề CŨ")])
    _ghi_quet(goc, "K1", "tay-20260927", [_video("v1", "Tiêu đề MỚI (chủ kênh sửa lại)")])
    ra = doc_video_cong_khai_tren_kenh(goc, "K1")
    assert ra["v1"]["tieu_de"] == "Tiêu đề MỚI (chủ kênh sửa lại)"


def test_doc_video_khong_co_thu_muc_quet_thi_rong(tmp_path):
    assert doc_video_cong_khai_tren_kenh(str(tmp_path), "K1") == {}


# ── tu_nhan_video_da_dang ────────────────────────────────────────────────────


def test_tu_nhan_khop_mo_dung_mot_ung_vien_thi_danh_dau(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927",
             [_video("vid1", "賢い人ほど「片付け」だけは自分でやる理由",
                     time_published=1790304322)])
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "賢い人ほど片付けだけは自分でやる理由",
         "Sẵn sàng": "x"},
    ])

    ket = tu_nhan_video_da_dang(goc, "K1", thuc_hien=True)
    assert len(ket) == 1
    assert ket[0]["ma_goi"] == "K1-0001"
    assert ket[0]["video_id"] == "vid1"
    assert ket[0]["da_danh_dau"] is True

    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    o_tt = cot.index("Trạng thái đăng")
    o_ghichu = cot.index("Ghi chú")
    assert hang[0][o_tt] == ban_giao_dang.TRANG_THAI_DANG_TAY
    assert "tự nhận từ Studio vid1" in hang[0][o_ghichu]
    # Ngày đăng lấy từ mốc CÔNG KHAI THẬT (timePublishedSeconds), không phải
    # giờ chạy hàm.
    import datetime as _dt
    moc_that = _dt.datetime.fromtimestamp(1790304322)
    o_ngay = cot.index("Ngày đăng")
    assert hang[0][o_ngay] == moc_that.strftime("%d/%m/%Y")


def test_tu_nhan_chay_kho_khong_ghi_gi(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927", [_video("vid1", "Tiêu đề khớp")])
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "Tiêu đề khớp", "Sẵn sàng": "x"},
    ])

    van_ban_truoc = ke_hoach_dang.doc_van_ban(goc, "K1")
    ket = tu_nhan_video_da_dang(goc, "K1", thuc_hien=False)
    van_ban_sau = ke_hoach_dang.doc_van_ban(goc, "K1")

    assert len(ket) == 1
    assert ket[0]["da_danh_dau"] is False
    assert van_ban_truoc == van_ban_sau  # tuyệt đối không đụng ke-hoach.csv


def test_tu_nhan_hai_video_cung_khop_thi_bo_qua(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927", [
        _video("vid1", "Tiêu đề dùng chung mẫu"),
        _video("vid2", "Tiêu đề dùng chung mẫu"),
    ])
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "Tiêu đề dùng chung mẫu", "Sẵn sàng": "x"},
    ])
    ket = tu_nhan_video_da_dang(goc, "K1", thuc_hien=True)
    assert ket == []
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    assert hang[0][cot.index("Trạng thái đăng")] == ""


def test_tu_nhan_da_dang_roi_thi_bo_qua_em(tmp_path):
    """Đúng ca TL1-T7-0001/0002 (đã được đánh dấu tay từ trước) — không đối
    chiếu lại, không lỗi."""
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927", [_video("vid1", "Video đã đăng rồi")])
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "Video đã đăng rồi", "Sẵn sàng": "",
         "Trạng thái đăng": ban_giao_dang.TRANG_THAI_DANG_TAY},
    ])
    ket = tu_nhan_video_da_dang(goc, "K1", thuc_hien=True)
    assert ket == []


def test_tu_nhan_video_khong_khop_dong_nao_thi_bo_qua_em(tmp_path):
    """Đúng ca TL3 video ve121fec092 (lượt AUTO/TL3-T7/0002) không có trong kế
    hoạch — video lạ trên Studio không khớp dòng nào thì bỏ qua êm, không lỗi."""
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927", [
        _video("la1", "Video không liên quan gì tới kế hoạch"),
    ])
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "Một tiêu đề hoàn toàn khác", "Sẵn sàng": "x"},
    ])
    ket = tu_nhan_video_da_dang(goc, "K1", thuc_hien=True)
    assert ket == []


def test_tu_nhan_bo_qua_dong_chua_san_sang(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927", [_video("vid1", "Chưa qua QA")])
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "Chưa qua QA", "Sẵn sàng": ""},
    ])
    assert tu_nhan_video_da_dang(goc, "K1", thuc_hien=True) == []


def test_tu_nhan_khong_co_luot_quet_nao_thi_rong_khong_loi(tmp_path):
    goc = str(tmp_path)
    _ghi_ke_hoach(goc, "K1", [
        {"Mã gói": "K1-0001", "Tiêu đề": "Bất kỳ", "Sẵn sàng": "x"},
    ])
    assert tu_nhan_video_da_dang(goc, "K1", thuc_hien=True) == []


def test_tu_nhan_khong_co_ke_hoach_thi_rong_khong_loi(tmp_path):
    goc = str(tmp_path)
    _ghi_quet(goc, "K1", "kenh-20260927", [_video("vid1", "Bất kỳ")])
    assert tu_nhan_video_da_dang(goc, "K1", thuc_hien=True) == []
