"""core/tu_dang_nhap.py — KHÔNG đụng registry/ctypes/LSA thật. Mọi bài kiểm
tiêm seam (`doc_dang_ky`/`co_lsa`/`luu_lsa`/`ghi_dang_ky`) giả — đúng khuôn
`chay_lenh` của `core.lich_tu_chay`. `dat_tu_dang_nhap` KHÔNG được gọi bằng
đối tượng thật ở bất kỳ bài nào (xem docstring đầu `core/tu_dang_nhap.py`:
"CHỈ viết + test mock, KHÔNG chạy thật")."""

from __future__ import annotations

import os

import pytest

from core import tu_dang_nhap as tdn


def _dk(auto=True, user="Administrator", domain="", mat_khau_tran=False):
    return {"auto_admin_logon": auto, "default_username": user,
            "default_domain": domain, "co_mat_khau_tran": mat_khau_tran}


class TestDocTrangThai:
    def test_tat_thi_phuong_thuc_tat(self):
        kq = tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(auto=False),
                                co_lsa=lambda ten: pytest.fail("không được hỏi LSA khi đã tắt"))
        assert kq["phuong_thuc"] == "tat"
        assert kq["auto_admin_logon"] is False

    def test_co_lsa_secret_thi_dung_dich(self):
        kq = tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(mat_khau_tran=False),
                                co_lsa=lambda ten: True)
        assert kq["phuong_thuc"] == "lsa_secret"
        assert kq["co_lsa_secret"] is True

    def test_mat_khau_tran_thi_canh_bao(self):
        kq = tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(mat_khau_tran=True),
                                co_lsa=lambda ten: False)
        assert kq["phuong_thuc"] == "mat_khau_tran_dang_ky"

    def test_khong_lsa_khong_mat_khau_tran_thi_thieu_mat_khau(self):
        kq = tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(mat_khau_tran=False),
                                co_lsa=lambda ten: False)
        assert kq["phuong_thuc"] == "thieu_mat_khau"

    def test_khong_doc_duoc_lsa_thi_khong_ro(self):
        kq = tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(mat_khau_tran=False),
                                co_lsa=lambda ten: None)
        assert kq["phuong_thuc"] == "khong_ro"

    def test_dung_ten_khoa_lsa(self):
        ten_hoi = []
        tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(),
                           co_lsa=lambda ten: ten_hoi.append(ten) or True)
        assert ten_hoi == [tdn.TEN_LSA_SECRET] == ["DefaultPassword"]

    def test_khong_bao_gio_tra_ve_gia_tri_mat_khau(self):
        """Kết quả không được có bất kỳ khoá nào mang chữ "mat_khau" TRỪ hai
        cờ bool đã định nghĩa — chống một bản sửa sau vô tình nhét giá trị
        thật vào dict trả về."""
        kq = tdn.doc_trang_thai(doc_dang_ky=lambda: _dk(mat_khau_tran=True),
                                co_lsa=lambda ten: True)
        cac_khoa_mat_khau = {"co_mat_khau_tran_dang_ky", "co_lsa_secret"}
        for khoa, gia_tri in kq.items():
            if "mat_khau" in khoa or "password" in khoa.lower():
                assert khoa in cac_khoa_mat_khau
                assert isinstance(gia_tri, (bool, type(None)))


class TestKiemSelfheal:
    def test_khong_co_tep_thi_khong_co(self, tmp_path):
        kq = tdn.kiem_selfheal(duong=str(tmp_path / "khong-ton-tai.ps1"))
        assert kq == {"co_tep": False, "co_mat_khau_tran": None}

    def test_co_tep_khong_mat_khau_thi_bao_khong(self, tmp_path):
        tep = tmp_path / "selfheal.ps1"
        tep.write_text("Set-DisplayResolution -Width 1920 -Height 1080\n", encoding="utf-8")
        kq = tdn.kiem_selfheal(duong=str(tep))
        assert kq["co_tep"] is True
        assert kq["co_mat_khau_tran"] is False

    def test_set_itemproperty_defaultpassword_thi_bao_co(self, tmp_path):
        tep = tmp_path / "selfheal.ps1"
        # Cùng khuôn dòng thật đo được 29/09/2026 (giá trị ở đây là GIẢ).
        tep.write_text(
            "Set-ItemProperty $W -Name DefaultPassword -Value 'gia-lap-khong-phai-that' "
            "-Type String -Force\n", encoding="utf-8")
        kq = tdn.kiem_selfheal(duong=str(tep))
        assert kq["co_tep"] is True
        assert kq["co_mat_khau_tran"] is True

    def test_net_user_thi_bao_co(self, tmp_path):
        tep = tmp_path / "selfheal.ps1"
        tep.write_text("net user Administrator MatKhauGiaLap123!\n", encoding="utf-8")
        kq = tdn.kiem_selfheal(duong=str(tep))
        assert kq["co_mat_khau_tran"] is True

    def test_securestring_khong_tinh_la_chu_tran(self, tmp_path):
        tep = tmp_path / "selfheal.ps1"
        tep.write_text(
            "$securePassword = ConvertTo-SecureString $plainPassword -AsPlainText -Force\n",
            encoding="utf-8")
        kq = tdn.kiem_selfheal(duong=str(tep))
        assert kq["co_mat_khau_tran"] is False

    def test_khong_bao_gio_tra_ve_doan_van_ban_khop(self, tmp_path):
        tep = tmp_path / "selfheal.ps1"
        tep.write_text(
            "Set-ItemProperty $W -Name DefaultPassword -Value 'BiMatKhongDuocLo' -Force\n",
            encoding="utf-8")
        kq = tdn.kiem_selfheal(duong=str(tep))
        van_ban = " ".join(str(v) for v in kq.values())
        assert "BiMatKhongDuocLo" not in van_ban


class TestDatTuDangNhap:
    def test_thieu_user_nem_loi(self):
        with pytest.raises(ValueError):
            tdn.dat_tu_dang_nhap("", "matkhau", luu_lsa=lambda *a: None,
                                 ghi_dang_ky=lambda **k: None)

    def test_thieu_mat_khau_nem_loi(self):
        with pytest.raises(ValueError):
            tdn.dat_tu_dang_nhap("Administrator", "", luu_lsa=lambda *a: None,
                                 ghi_dang_ky=lambda **k: None)

    def test_luu_lsa_truoc_ghi_dang_ky_sau(self):
        thu_tu = []
        tdn.dat_tu_dang_nhap(
            "Administrator", "mat-khau-gia-lap",
            luu_lsa=lambda ten, gt: thu_tu.append(("lsa", ten)),
            ghi_dang_ky=lambda **k: thu_tu.append(("dang_ky", k)))
        assert [b[0] for b in thu_tu] == ["lsa", "dang_ky"]
        assert thu_tu[0][1] == tdn.TEN_LSA_SECRET

    def test_dung_ten_va_mien_duoc_truyen_xuong(self):
        ghi_nhan = {}
        tdn.dat_tu_dang_nhap(
            "Administrator", "x", mien="CONTOSO",
            luu_lsa=lambda ten, gt: None,
            ghi_dang_ky=lambda **k: ghi_nhan.update(k))
        assert ghi_nhan["user"] == "Administrator"
        assert ghi_nhan["domain"] == "CONTOSO"
        assert ghi_nhan["xoa_mat_khau_tran"] is True

    def test_luu_lsa_hong_thi_khong_dung_toi_dang_ky(self):
        """Lưu LSA ném lỗi → KHÔNG được gọi `ghi_dang_ky` (không xoá mật khẩu
        chữ trần cũ khi chưa chắc có mật khẩu mới) — xem docstring "THỨ TỰ GHI"."""
        goi_dang_ky = []

        def _luu_hong(ten, gt):
            raise OSError("giả lập LsaStorePrivateData lỗi")

        with pytest.raises(OSError):
            tdn.dat_tu_dang_nhap(
                "Administrator", "x",
                luu_lsa=_luu_hong,
                ghi_dang_ky=lambda **k: goi_dang_ky.append(k))
        assert goi_dang_ky == []

    def test_khong_bao_gio_dung_ham_that_trong_test(self, monkeypatch):
        """Chốt an toàn: nếu ai đó lỡ gọi thiếu seam, hàm THẬT (đụng
        registry/ctypes) phải bị chặn ngay trong môi trường test, không được
        âm thầm chạy."""
        def _cam(*a, **k):
            raise AssertionError("KHÔNG được gọi hàm LSA/registry thật trong test")

        monkeypatch.setattr(tdn, "_luu_lsa_secret_that", _cam)
        monkeypatch.setattr(tdn, "_ghi_dang_ky_that", _cam)
        # Gọi CÓ truyền seam giả — hàm thật không được đụng tới dù đã patch hỏng.
        tdn.dat_tu_dang_nhap("Administrator", "x",
                             luu_lsa=lambda ten, gt: None,
                             ghi_dang_ky=lambda **k: None)
