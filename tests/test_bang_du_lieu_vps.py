from __future__ import annotations

import csv
import datetime as dt
import os

import pytest

from core import bang_du_lieu_vps as dl


def _ghi(duong, cot, hang):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(cot)
        w.writerows(hang)


def test_doc_kho_content_chi_giu_cot_can_thiet(tmp_path):
    nc = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    duong = nc / "content.csv"
    _ghi(str(duong), ["Tiêu đề video", "Tiêu đề (Việt)", "View", "Mô tả", "Link video"],
         [["gốc", "tiếng Việt", "1234", "x" * 10000, "https://youtu.be/abcdefghijk"]])
    bo = dl.doc_bo_du_lieu(str(tmp_path), "K1", dl.CONTENT)
    assert len(bo["hang"]) == 1
    assert bo["hang"][0]["Tiêu đề hiển thị"] == "tiếng Việt"
    assert "Mô tả" not in bo["hang"][0]
    assert "10000" not in bo["hang"][0]["_tim"]


def test_danh_dau_xong_bang_doc_lai_hien_ngay(tmp_path):
    from core.da_lam import ghi_da_lam_tay

    nc = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    _ghi(str(nc / "content.csv"), ["Tiêu đề video", "Link video", "Đã làm"],
         [["nguồn", "https://youtu.be/abcdefghijk", ""]])
    assert ghi_da_lam_tay(str(tmp_path), "K1", "https://youtu.be/abcdefghijk", "tay")
    bo = dl.doc_bo_du_lieu(str(tmp_path), "K1", dl.CONTENT)
    assert bo["hang"][0]["Đã làm"] == "tay"


def test_doc_v7_lay_ban_moi_nhat(tmp_path):
    nc = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    cu = nc / "cham-v7-2026-09-24.csv"
    moi = nc / "cham-v7-2026-09-25.csv"
    _ghi(str(cu), ["Điểm", "Tiêu đề"], [["10", "cũ"]])
    _ghi(str(moi), ["Điểm", "Tiêu đề"], [["90", "mới"]])
    os.utime(cu, (1, 1))
    os.utime(moi, (2, 2))
    bo = dl.doc_bo_du_lieu(str(tmp_path), "K1", dl.V7)
    assert bo["hang"][0]["Tiêu đề hiển thị"] == "mới"


def test_cac_bo_loc_nhanh_dung_cau_hoi_quan_ly():
    assert dl.hop_loc_nhanh(dl.V7, "qua", {"Loại": "Nên làm"})
    assert not dl.hop_loc_nhanh(dl.V7, "qua", {"Loại": "Bỏ"})
    assert dl.hop_loc_nhanh(dl.CONTENT, "manh", {"Điểm": "85", "Đã làm": ""})
    assert not dl.hop_loc_nhanh(dl.CONTENT, "manh", {"Điểm": "85", "Đã làm": "0001"})
    assert dl.hop_loc_nhanh(dl.DOI_THU, "vuot5", {"Vượt quy mô": "5.2"})
    assert not dl.hop_loc_nhanh(dl.DOI_THU, "vuot5", {"Vượt quy mô": "4.9"})
    assert dl.hop_loc_nhanh(dl.CONTENT, "moi7", {"Lần đầu thấy": "2026-09-21"},
                            hom_nay=dt.date(2026, 9, 25))


def test_link_theo_tung_bo_du_lieu():
    assert dl.link_cua_dong(dl.CONTENT, {"Link video": "video"}) == "video"
    assert dl.link_cua_dong(dl.DOI_THU, {"Link kênh": "kenh"}) == "kenh"


def test_sua_ghi_chu_content_ghi_ben_vao_csv(tmp_path):
    nc = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    duong = nc / "content.csv"
    link = "https://youtu.be/abcdefghijk"
    _ghi(str(duong), ["Tiêu đề video", "Link video"], [["nguồn", link]])
    bo = dl.doc_bo_du_lieu(str(tmp_path), "K1", dl.CONTENT)
    dl.sua_o_quan_ly(str(tmp_path), "K1", dl.CONTENT, bo["hang"][0], "Ghi chú", "  ưu tiên   tuần tới ")
    doc = dl.doc_bo_du_lieu(str(tmp_path), "K1", dl.CONTENT)
    assert doc["hang"][0]["Ghi chú"] == "ưu tiên tuần tới"


def test_sua_trang_thai_doi_thu_khong_lam_mat_cot_cu(tmp_path):
    nc = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    duong = nc / "doi-thu.csv"
    link = "https://youtube.com/@doi-thu"
    _ghi(str(duong), ["Kênh", "Link kênh", "Cột riêng"], [["A", link, "giữ nguyên"]])
    bo = dl.doc_bo_du_lieu(str(tmp_path), "K1", dl.DOI_THU)
    dl.sua_o_quan_ly(str(tmp_path), "K1", dl.DOI_THU, bo["hang"][0], "Trạng thái", "Bỏ")
    with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
        hang = list(csv.DictReader(tep))
    assert hang[0]["Trạng thái"] == "Bỏ"
    assert hang[0]["Cột riêng"] == "giữ nguyên"


def test_khong_cho_sua_so_lieu_may_sinh(tmp_path):
    with pytest.raises(ValueError, match="không thể sửa"):
        dl.sua_o_quan_ly(str(tmp_path), "K1", dl.DOI_THU,
                         {"Link kênh": "x"}, "Subs", "999")
