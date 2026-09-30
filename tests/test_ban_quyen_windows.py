"""core/ban_quyen_windows.py — không gọi cscript/slmgr thật (mock `chay_lenh`,
cùng khuôn seam của `core.lich_tu_chay`); không mạng."""

from __future__ import annotations

import datetime as _dt

from core import ban_quyen_windows as bqw

#: Giờ giả AN TOÀN — trùng `tests/test_an_toan_khoi_dong.py` (ngoài mọi khung
#: giờ tránh) để `nen_rearm` gọi `an_toan_khoi_dong.kiem_tra` trên `tmp_path`
#: rỗng luôn trả `duoc=True`.
BAY_GIO_AN_TOAN = _dt.datetime(2026, 9, 29, 15, 30)

#: Nguyên văn `cscript //nologo slmgr.vbs /xpr` đo THẬT trên máy này 29/09/2026.
XPR_THAT = (
    "Windows(R), ServerStandardEval edition:\n"
    "    Timebased activation will expire 3/24/2027 2:35:57 AM\n"
)

#: Nguyên văn `/dlv` (rút gọn, giữ đúng hai dòng cần đọc) đo THẬT cùng ngày —
#: khớp kiểm toán 26/09: "hết hạn 24/03/2027, còn 2 lượt rearm".
DLV_THAT = (
    "Software licensing service version: 10.0.17763.737\n"
    "Name: Windows(R), ServerStandardEval edition\n"
    "License Status: Licensed\n"
    "Timebased activation expiration: 252828 minute(s) (176 day(s))\n"
    "Remaining Windows rearm count: 2\n"
    "Remaining SKU rearm count: 2\n"
)

XPR_VINH_VIEN = "The machine is permanently activated.\n"

#: Câu Anh xen số ngày còn lại đúng mẫu — dùng để dựng ca "còn 5 ngày, còn 1 rearm".
DLV_SAP_HET = (
    "Timebased activation expiration: 7200 minute(s) (5 day(s))\n"
    "Remaining Windows rearm count: 1\n"
)

DLV_HET_REARM = (
    "Timebased activation expiration: 1440 minute(s) (1 day(s))\n"
    "Remaining Windows rearm count: 0\n"
)


def _lenh_gia(ra_xpr: str = "", ra_dlv: str = ""):
    goi = []

    def chay_lenh(lenh):
        goi.append(list(lenh))
        if lenh[-1] == "/xpr":
            return 0, ra_xpr
        if lenh[-1] == "/dlv":
            return 0, ra_dlv
        return 1, "lệnh lạ"

    return chay_lenh, goi


class TestKhongDungWscript:
    def test_doc_xpr_chi_goi_cscript_nologo(self, monkeypatch):
        chay_lenh, goi = _lenh_gia(ra_xpr=XPR_THAT)
        bqw.doc_xpr(chay_lenh=chay_lenh)
        assert len(goi) == 1
        lenh = goi[0]
        assert lenh[0] == "cscript"
        assert lenh[1] == "//nologo"
        assert "wscript" not in " ".join(lenh).lower()
        assert lenh[-1] == "/xpr"
        assert lenh[2].lower().endswith("slmgr.vbs")

    def test_doc_dlv_chi_goi_cscript_nologo(self, monkeypatch):
        chay_lenh, goi = _lenh_gia(ra_dlv=DLV_THAT)
        bqw.doc_dlv(chay_lenh=chay_lenh)
        assert goi[0][0] == "cscript"
        assert goi[0][-1] == "/dlv"


class TestPhanTichXpr:
    def test_ngay_het_han_that(self):
        kq = bqw.phan_tich_xpr(XPR_THAT)
        assert kq["vinh_vien"] is False
        assert kq["het_han"] == _dt.date(2027, 3, 24)

    def test_vinh_vien(self):
        kq = bqw.phan_tich_xpr(XPR_VINH_VIEN)
        assert kq["vinh_vien"] is True
        assert kq["het_han"] is None

    def test_khong_khop_thi_khong_nem_loi(self):
        kq = bqw.phan_tich_xpr("một dòng bất kỳ, không liên quan")
        assert kq["vinh_vien"] is False
        assert kq["het_han"] is None


class TestPhanTichDlv:
    def test_so_ngay_va_rearm_that(self):
        kq = bqw.phan_tich_dlv(DLV_THAT)
        assert kq["so_ngay_con_lai"] == 176
        assert kq["rearm_con_lai"] == 2
        assert kq["vinh_vien"] is False

    def test_khong_khop_thi_none_khong_nem_loi(self):
        kq = bqw.phan_tich_dlv("dữ liệu lạ hoàn toàn")
        assert kq["so_ngay_con_lai"] is None
        assert kq["rearm_con_lai"] is None

    def test_lay_dung_windows_rearm_khong_lay_sku(self):
        text = ("Remaining SKU rearm count: 9\n"
                "Remaining Windows rearm count: 2\n")
        kq = bqw.phan_tich_dlv(text)
        assert kq["rearm_con_lai"] == 2


class TestDocGiayPhep:
    def test_gop_ca_hai_lenh(self):
        chay_lenh, goi = _lenh_gia(ra_xpr=XPR_THAT, ra_dlv=DLV_THAT)
        kq = bqw.doc_giay_phep(chay_lenh=chay_lenh)
        assert kq["het_han"] == _dt.date(2027, 3, 24)
        assert kq["so_ngay_con_lai"] == 176
        assert kq["rearm_con_lai"] == 2
        assert len(goi) == 2  # đúng MỘT lần /xpr, MỘT lần /dlv


class TestDanhGia:
    def test_con_176_ngay_thi_binh_thuong(self):
        thong_tin = {"vinh_vien": False, "so_ngay_con_lai": 176, "rearm_con_lai": 2}
        assert bqw.danh_gia(thong_tin)["muc"] == bqw.MUC_BINH_THUONG

    def test_con_25_ngay_thi_nhac_30(self):
        assert bqw.danh_gia({"vinh_vien": False, "so_ngay_con_lai": 25})["muc"] == bqw.MUC_NHAC_30

    def test_con_10_ngay_thi_nhac_14(self):
        assert bqw.danh_gia({"vinh_vien": False, "so_ngay_con_lai": 10})["muc"] == bqw.MUC_NHAC_14

    def test_con_5_ngay_thi_khan_7(self):
        assert bqw.danh_gia({"vinh_vien": False, "so_ngay_con_lai": 5})["muc"] == bqw.MUC_KHAN_7

    def test_vinh_vien_thi_binh_thuong(self):
        assert bqw.danh_gia({"vinh_vien": True, "so_ngay_con_lai": None})["muc"] == bqw.MUC_BINH_THUONG

    def test_khong_doc_duoc_thi_khong_ro(self):
        assert bqw.danh_gia({"vinh_vien": False, "so_ngay_con_lai": None})["muc"] == bqw.MUC_KHONG_RO


class TestNenRearm:
    def test_con_176_ngay_khong_de_xuat(self, tmp_path):
        thong_tin = {"vinh_vien": False, "so_ngay_con_lai": 176, "rearm_con_lai": 2}
        kq = bqw.nen_rearm(thong_tin, str(tmp_path), bay_gio=BAY_GIO_AN_TOAN)
        assert kq["de_xuat"] is False
        assert kq["trong_han"] is False

    def test_con_5_ngay_con_rearm_va_an_toan_thi_de_xuat(self, tmp_path):
        thong_tin = {"vinh_vien": False, "so_ngay_con_lai": 5, "rearm_con_lai": 1}
        kq = bqw.nen_rearm(thong_tin, str(tmp_path), bay_gio=BAY_GIO_AN_TOAN)
        assert kq["trong_han"] is True
        assert kq["con_rearm"] is True
        assert kq["de_xuat"] is True
        assert kq["an_toan"]["duoc"] is True

    def test_het_rearm_thi_khong_bao_gio_de_xuat(self, tmp_path):
        thong_tin = {"vinh_vien": False, "so_ngay_con_lai": 5, "rearm_con_lai": 0}
        kq = bqw.nen_rearm(thong_tin, str(tmp_path), bay_gio=BAY_GIO_AN_TOAN)
        assert kq["con_rearm"] is False
        assert kq["de_xuat"] is False

    def test_vinh_vien_thi_khong_bao_gio_de_xuat(self, tmp_path):
        thong_tin = {"vinh_vien": True, "so_ngay_con_lai": None, "rearm_con_lai": 2}
        kq = bqw.nen_rearm(thong_tin, str(tmp_path), bay_gio=BAY_GIO_AN_TOAN)
        assert kq["de_xuat"] is False

    def test_khong_an_toan_thi_khong_de_xuat_du_du_dieu_kien(self, tmp_path):
        """Đang tải dở một video (`vm/logs/dang-dodang.json`) → không an toàn
        để khởi động lại, dù còn rearm và đã sát hạn ngày."""
        import json
        import os

        duong = os.path.join(str(tmp_path), "vm", "logs", "dang-dodang.json")
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"kenh": "TL1-T7"}, tep)

        thong_tin = {"vinh_vien": False, "so_ngay_con_lai": 5, "rearm_con_lai": 1}
        kq = bqw.nen_rearm(thong_tin, str(tmp_path), bay_gio=BAY_GIO_AN_TOAN)
        assert kq["trong_han"] is True
        assert kq["con_rearm"] is True
        assert kq["an_toan"]["duoc"] is False
        assert kq["de_xuat"] is False

    def test_khong_tu_goi_lenh_he_thong_nao(self, tmp_path, monkeypatch):
        """`nen_rearm` KHÔNG được tự rearm/khởi động lại — không có lời gọi
        `subprocess`/`os.system` nào bên trong (chỉ tính toán + đọc đĩa)."""
        import subprocess as _sp

        def _cam(*a, **k):
            raise AssertionError("nen_rearm không được gọi subprocess")

        monkeypatch.setattr(_sp, "run", _cam)
        monkeypatch.setattr(_sp, "Popen", _cam)
        thong_tin = {"vinh_vien": False, "so_ngay_con_lai": 5, "rearm_con_lai": 1}
        bqw.nen_rearm(thong_tin, str(tmp_path), bay_gio=BAY_GIO_AN_TOAN)
