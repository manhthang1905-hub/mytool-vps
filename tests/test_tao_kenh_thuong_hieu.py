"""Test phần thuần của vm/tao_kenh_thuong_hieu.py — không mở Chrome."""
import time

from vm import tao_kenh_thuong_hieu as tk

# Email GIẢ ghép lúc chạy (không có literal Gmail trong mã).
EMAIL_GIA = "kenh" + "@gmail.com"


def test_tim_email_va_uc():
    assert tk.tim_email_trong_chu("Xin chào " + EMAIL_GIA + " đang đăng nhập") == EMAIL_GIA
    assert tk.tim_email_trong_chu("không có gì") == ""
    assert tk.tim_uc_trong_url("https://www.youtube.com/channel/UCabcdefghijklmnopqrstu") == "UCabcdefghijklmnopqrstu"
    assert tk.tim_uc_trong_url("https://www.youtube.com/") == ""


def test_dang_nhap_lai_bi_nhan_dien():
    assert tk.dang_bi_chan_dang_nhap("https://accounts.google.com/v3/signin/identifier")
    assert not tk.dang_bi_chan_dang_nhap("https://www.youtube.com/account")


def test_ten_co_trong_danh_sach_bo_khoang_trang():
    assert tk.ten_co_trong_trang("架空の夜話チャンネル", "Kênh:  架空の夜話チャンネル   \n khác")
    assert not tk.ten_co_trong_trang("架空の夜話チャンネル", "kênh khác hoàn toàn")
    assert not tk.ten_co_trong_trang("", "bất kỳ")


def test_chan_trong_khung_cam(monkeypatch):
    monkeypatch.setattr(tk, "khung_cam_hien_tai", lambda luc=None: "khung cấm 02:00–07:00")
    duoc, ma, ly = tk.quyet_dinh_truoc_khi_chay("Ten", EMAIL_GIA, "ok", False)
    assert (duoc, ma) == (False, "hoan")


def test_thieu_tai_khoan_hoac_chua_xac_minh_thi_khong_lam(monkeypatch):
    monkeypatch.setattr(tk, "khung_cam_hien_tai", lambda luc=None: "")
    assert tk.quyet_dinh_truoc_khi_chay("Ten", "", "ok", False)[1] == "hong"
    assert tk.quyet_dinh_truoc_khi_chay("Ten", EMAIL_GIA, "chua_xac_minh", False)[1] == "hong"
    assert tk.quyet_dinh_truoc_khi_chay("", EMAIL_GIA, "ok", False)[1] == "hong"


def test_chrome_dang_mo_thi_hoan(monkeypatch):
    monkeypatch.setattr(tk, "khung_cam_hien_tai", lambda luc=None: "")
    assert tk.quyet_dinh_truoc_khi_chay("Ten", EMAIL_GIA, "ok", True) == (False, "hoan", "Chrome kênh đang mở — đóng rồi làm tiếp")


def test_du_dieu_kien_thi_duoc_chay(monkeypatch):
    monkeypatch.setattr(tk, "khung_cam_hien_tai", lambda luc=None: "")
    assert tk.quyet_dinh_truoc_khi_chay("Ten", EMAIL_GIA, "ok", False)[0] is True
