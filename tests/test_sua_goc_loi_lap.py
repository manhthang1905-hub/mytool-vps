"""Sửa GỐC các lỗi lặp lại 13–18/10/2026 (`workspace/chan-doan/loi-lap-lai-17-10.md`) — dữ liệu dựng tay."""
import datetime as _dt
import json
import os
import sys

from core import tu_chay


def test_clip_het_moi_dot_cuu_khong_duoc_mien_tran_l3():
    run = {"san_xuat": {"loi_dung": "Dừng ở “Tạo clip từng cảnh”: cảnh 138 không làm được clip thật — cần người xem "
                                    "(lỗi cuối: cảnh 138: máy chủ nhận việc rồi bỏ đó 2 lần … máy chủ vẫn chưa trả "
                                    "kết quả)"}}
    assert tu_chay._dung_vi_phia_shopapi(run) is False


def test_cho_dot_cuu_moi_van_la_cho_phia_may_chu():
    run = {"san_xuat": {"loi_dung": "cảnh 138 chờ đợt cứu mới sau 2.0 giờ (…); máy chủ vẫn chưa trả kết quả cho cảnh "
                                    "này — lượt tự chạy tiếp"}}
    assert tu_chay._dung_vi_phia_shopapi(run) is True


def test_s03_nhan_viec_sua_doi_khe_dem(tmp_path, monkeypatch):
    """TL6-T7-0004: đổi tiêu đề chờ khe đêm 166 giờ → S03 làm như việc gấp (kể cả gần 02:00)."""
    from core import ky_nang as kn
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "vm", "logs"))
    with open(os.path.join(goc, "vm", "logs", "hang-sua.json"), "w", encoding="utf-8") as f:
        json.dump({"viec": [{"id": "s:tieu_de", "buoc": "tieu_de", "kenh": "TL6-T7", "ma_goi": "TL6-T7-0004",
                             "video_id": "vidGia924dd", "tieu_de": "x", "trang_thai": "cho",
                             "them_luc": "2026-10-12T01:17:07"},
                            {"id": "m:tieu_de", "buoc": "tieu_de", "kenh": "TL6-T7", "ma_goi": "TL6-T7-0009",
                             "video_id": "AAAAAAAAAAA", "tieu_de": "y", "trang_thai": "cho",
                             "them_luc": "2026-10-18T20:00:00"}]}, f)
    bay = _dt.datetime(2026, 10, 18, 23, 30)
    monkeypatch.setattr(kn, "_gio", lambda: bay)
    monkeypatch.setattr(kn, "_san_sang_dom", lambda g, k: "")
    monkeypatch.setattr(kn, "_nhuong_phien", lambda g, b: "")
    gap = kn._bia_gap(goc, "TL6-T7", bay)
    assert [v["video_id"] for v in gap] == ["vidGia924dd"] and gap[0]["doi"]
    assert kn.d_bia_gap(goc, "TL6-T7")[0] is True


def test_goi_giu_vi_bia_khong_lam_thiet_lap_nhuong_mai(monkeypatch):
    """TL4-T7-K2: gói giữ vì bìa thiếu dấu cổng chữ không được tính là "gói chờ tải lên" (thiết lập nhường 64 lần)."""
    from core import cong_chu
    vm = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm")
    if vm not in sys.path:
        sys.path.insert(0, vm)
    import nuoi_trang_chu as n
    monkeypatch.setattr(cong_chu, "goi_cho_dang", lambda g, k: [{"ma": "K-0001", "anh": "a.jpg"},
                                                                {"ma": "K-0002", "anh": "b.jpg"},
                                                                {"ma": "K-0003", "anh": ""}])
    monkeypatch.setattr(cong_chu, "kiem_dau", lambda p: "" if p == "b.jpg" else "chưa có dấu")
    assert n.goi_giu_vi_bia("K") == {"K-0001", "K-0003"}
