"""core/gac_tong.py — không mạng, không gọi `schtasks`/socket thật (seam
`chay_lenh`/`kiem_cong` mock được); phần lớn bài kiểm dựng ẢNH CHỤP tay
(đúng tinh thần `kiem_su_co` là hàm THUẦN, xem docstring module)."""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os

import pytest

from core import bao_dong, gac_tong, ke_hoach_dang

BAY_GIO = _dt.datetime(2026, 9, 29, 15, 30)
LUC_ISO = BAY_GIO.isoformat(timespec="seconds")


def _anh(kenh=None, may=None):
    return {
        "luc": LUC_ISO,
        "goc": "/khong-dung-toi",
        "kenh": kenh or {},
        "may": may or {
            "dia": {"con_gb": 40.0},
            "cong_8765_tram": True,
            "cong_8767_agent": False,
            "schtasks_tu_chay": {"da_dang_ky": True, "ket_qua_cuoi": "chạy xong, không kênh nào lỗi (mã 0)"},
            "schtasks_canh_tram": {"da_dang_ky": True, "ket_qua_cuoi": "trạm 8765 có người phục vụ (mã 0)"},
            "khoa_may": {"co": False, "tuoi_giay": None, "pid": None, "con_song": None},
        },
    }


def _snap(tu_chay=True, ke_hoach=None, runs_hom_nay=None, chi_so_tuoi_gio=1.0):
    return {
        "tu_chay": tu_chay,
        "ke_hoach": ke_hoach or [],
        "runs_hom_nay": runs_hom_nay or [],
        "nhat_ky_hom_nay": [],
        "kiem_dom": None,
        "chi_so_tuoi_gio": chi_so_tuoi_gio,
    }


def _dong_da_dang(gio_truoc):
    hen = BAY_GIO - _dt.timedelta(hours=gio_truoc)
    return {"_loai": "da_dang", "Ngày đăng": hen.strftime("%d/%m/%Y"),
            "Giờ đăng": hen.strftime("%H:%M"), "Tiêu đề": "video cũ",
            "_gio_con_lai": None, "_da_tai": True, "_lan_tai_moi_hom_nay": 0}


def _dong_sap_dang(gio_toi, *, da_tai=False, lan=0):
    hen = BAY_GIO + _dt.timedelta(hours=gio_toi)
    return {"_loai": "sap_dang", "Ngày đăng": hen.strftime("%d/%m/%Y"),
            "Giờ đăng": hen.strftime("%H:%M"), "Tiêu đề": "video sắp đăng",
            "_gio_con_lai": gio_toi, "_da_tai": da_tai, "_lan_tai_moi_hom_nay": lan}


# ═══════════════════════════════════════════════════════════════════════════
# _ghep_ngay_gio
# ═══════════════════════════════════════════════════════════════════════════


class TestGhepNgayGio:
    def test_dung_dinh_dang(self):
        kq = gac_tong._ghep_ngay_gio("29/09/2026", "20:00")
        assert kq == _dt.datetime(2026, 9, 29, 20, 0)

    def test_rong_thi_none(self):
        assert gac_tong._ghep_ngay_gio("", "20:00") is None

    def test_sai_dinh_dang_thi_none(self):
        assert gac_tong._ghep_ngay_gio("hôm nay", "20:00") is None

    def test_thieu_gio_thi_00_00(self):
        kq = gac_tong._ghep_ngay_gio("29/09/2026", "")
        assert kq == _dt.datetime(2026, 9, 29, 0, 0)


# ═══════════════════════════════════════════════════════════════════════════
# kiem_su_co — hàm thuần, ảnh chụp dựng tay
# ═══════════════════════════════════════════════════════════════════════════


class TestKhongVideoMoi:
    def test_tu_chay_tat_thi_khong_kiem(self):
        anh = _anh({"K1": _snap(tu_chay=False, ke_hoach=[])})
        ds = gac_tong.kiem_su_co(anh)
        assert not any(s["loai"] == "khong_video_moi" for s in ds)

    def test_chua_tung_dang_thi_bao(self):
        anh = _anh({"K1": _snap(tu_chay=True, ke_hoach=[])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khong_video_moi"]
        assert len(ds) == 1
        assert ds[0]["muc"] == bao_dong.MUC_KHAN
        assert ds[0]["kenh"] == "K1"

    def test_video_gan_day_thi_khong_bao(self):
        anh = _anh({"K1": _snap(tu_chay=True, ke_hoach=[_dong_da_dang(2)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khong_video_moi"]
        assert ds == []

    def test_qua_nguong_thi_bao(self):
        anh = _anh({"K1": _snap(tu_chay=True,
                                ke_hoach=[_dong_da_dang(gac_tong.NGUONG_KHONG_VIDEO_MOI_GIO + 1)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khong_video_moi"]
        assert len(ds) == 1

    def test_duoi_nguong_thi_khong_bao(self):
        anh = _anh({"K1": _snap(tu_chay=True,
                                ke_hoach=[_dong_da_dang(gac_tong.NGUONG_KHONG_VIDEO_MOI_GIO - 1)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khong_video_moi"]
        assert ds == []


class TestHenLichChuaTai:
    def test_trong_han_chua_tai_thi_bao(self):
        anh = _anh({"K1": _snap(ke_hoach=[_dong_sap_dang(5, da_tai=False)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "hen_lich_chua_tai"]
        assert len(ds) == 1
        assert "còn" in ds[0]["chuyen_gi"]

    def test_da_tai_roi_thi_khong_bao(self):
        anh = _anh({"K1": _snap(ke_hoach=[_dong_sap_dang(5, da_tai=True)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "hen_lich_chua_tai"]
        assert ds == []

    def test_con_xa_hon_12h_thi_khong_bao(self):
        anh = _anh({"K1": _snap(ke_hoach=[_dong_sap_dang(20, da_tai=False)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "hen_lich_chua_tai"]
        assert ds == []

    def test_qua_gio_hen_thi_bao_qua_han(self):
        anh = _anh({"K1": _snap(ke_hoach=[_dong_sap_dang(-3, da_tai=False)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "hen_lich_chua_tai"]
        assert len(ds) == 1
        assert "QUÁ" in ds[0]["chuyen_gi"]

    def test_khac_loai_cho_duyet_khong_bi_kiem(self):
        dong = {"_loai": "cho_duyet", "_gio_con_lai": None, "_da_tai": False,
                "_lan_tai_moi_hom_nay": 0, "Tiêu đề": "x"}
        anh = _anh({"K1": _snap(ke_hoach=[dong])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "hen_lich_chua_tai"]
        assert ds == []


class TestTaiLenLoiLap:
    def test_duoi_nguong_khong_bao(self):
        anh = _anh({"K1": _snap(ke_hoach=[_dong_sap_dang(5, lan=gac_tong.NGUONG_TAI_LEN_LAP_LAI - 1)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tai_len_loi_lap"]
        assert ds == []

    def test_dat_nguong_thi_bao(self):
        anh = _anh({"K1": _snap(ke_hoach=[_dong_sap_dang(5, lan=gac_tong.NGUONG_TAI_LEN_LAP_LAI)])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tai_len_loi_lap"]
        assert len(ds) == 1
        assert ds[0]["kenh"] == "K1"


class TestStudioCu:
    def test_tu_chay_bat_va_cu_thi_bao_muc_thuong(self):
        anh = _anh({"K1": _snap(tu_chay=True, chi_so_tuoi_gio=gac_tong.NGUONG_STUDIO_CU_GIO + 1)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "so_lieu_studio_cu"]
        assert len(ds) == 1
        assert ds[0]["muc"] == bao_dong.MUC_THUONG

    def test_tu_chay_tat_thi_khong_bao_du_cu(self):
        anh = _anh({"K1": _snap(tu_chay=False, chi_so_tuoi_gio=1000.0)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "so_lieu_studio_cu"]
        assert ds == []

    def test_khong_ro_tuoi_thi_khong_bao(self):
        anh = _anh({"K1": _snap(tu_chay=True, chi_so_tuoi_gio=None)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "so_lieu_studio_cu"]
        assert ds == []


class TestDiaDay:
    def test_duoi_nguong_van_o_thi_bao_mot_lan_moi_ngay(self):
        anh = _anh(may={"dia": {"con_gb": 9.0}, "cong_8765_tram": True,
                        "cong_8767_agent": False,
                        "schtasks_tu_chay": {}, "schtasks_canh_tram": {},
                        "khoa_may": {"co": False}})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "dia_day"]
        assert len(ds) == 1
        assert ds[0]["muc"] == bao_dong.MUC_KHAN
        assert ds[0]["dedupe_khoa"] == "dia_day" and ds[0]["lap_gio"] == 24.0

    def test_nguong_bao_dong_trung_van_o(self):
        from core import don_dep_mo_rong
        assert gac_tong.NGUONG_DIA_GB == don_dep_mo_rong.NGUONG_O_GB

    def test_tren_15gb_thi_khong_bao(self):
        anh = _anh()  # mặc định 40 GB
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "dia_day"]
        assert ds == []


class TestTramChet:
    def test_cong_8765_chet_thi_bao(self):
        anh = _anh(may={"dia": {"con_gb": 40.0}, "cong_8765_tram": False,
                        "cong_8767_agent": False,
                        "schtasks_tu_chay": {}, "schtasks_canh_tram": {},
                        "khoa_may": {"co": False}})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tram_chet"]
        assert len(ds) == 1
        assert ds[0]["muc"] == bao_dong.MUC_KHAN

    def test_cong_8765_song_thi_khong_bao(self):
        ds = [s for s in gac_tong.kiem_su_co(_anh()) if s["loai"] == "tram_chet"]
        assert ds == []


class TestKhoaMayQuaLau:
    def test_khong_co_khoa_thi_khong_bao(self):
        ds = [s for s in gac_tong.kiem_su_co(_anh()) if s["loai"] == "khoa_may_qua_lau"]
        assert ds == []

    def test_moi_duoi_nguong_thi_khong_bao(self):
        anh = _anh(may={"dia": {"con_gb": 40.0}, "cong_8765_tram": True,
                        "cong_8767_agent": False,
                        "schtasks_tu_chay": {}, "schtasks_canh_tram": {},
                        "khoa_may": {"co": True, "tuoi_giay": gac_tong.NGUONG_CANH_BAO_KHOA_GIAY - 60,
                                    "pid": 111, "con_song": True}})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khoa_may_qua_lau"]
        assert ds == []

    def test_qua_nguong_con_song_thi_bao_doi_nguoi(self):
        anh = _anh(may={"dia": {"con_gb": 40.0}, "cong_8765_tram": True,
                        "cong_8767_agent": False,
                        "schtasks_tu_chay": {}, "schtasks_canh_tram": {},
                        "khoa_may": {"co": True, "tuoi_giay": gac_tong.NGUONG_CANH_BAO_KHOA_GIAY + 60,
                                    "pid": 111, "con_song": True}})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khoa_may_qua_lau"]
        assert len(ds) == 1
        assert "sống" in ds[0]["chuyen_gi"]

    def test_qua_nguong_da_chet_thi_bao_khoi_dong_lai(self):
        anh = _anh(may={"dia": {"con_gb": 40.0}, "cong_8765_tram": True,
                        "cong_8767_agent": False,
                        "schtasks_tu_chay": {}, "schtasks_canh_tram": {},
                        "khoa_may": {"co": True, "tuoi_giay": gac_tong.NGUONG_CANH_BAO_KHOA_GIAY + 60,
                                    "pid": 111, "con_song": False}})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khoa_may_qua_lau"]
        assert len(ds) == 1
        assert "CHẾT" in ds[0]["chuyen_gi"]


# ═══════════════════════════════════════════════════════════════════════════
# xep_trang_thai_kenh
# ═══════════════════════════════════════════════════════════════════════════


class TestXepTrangThaiKenh:
    def test_tu_chay_tat_thi_xong(self):
        kq = gac_tong.xep_trang_thai_kenh(_snap(tu_chay=False), [])
        assert kq["trang_thai"] == gac_tong.TRANG_THAI_XONG

    def test_co_su_co_khan_thi_cho_nguoi(self):
        su_co = [{"loai": "x", "kenh": "K1", "muc": bao_dong.MUC_KHAN, "chuyen_gi": "lỗi rồi"}]
        kq = gac_tong.xep_trang_thai_kenh(_snap(tu_chay=True), su_co)
        assert kq["trang_thai"] == gac_tong.TRANG_THAI_CHO_NGUOI
        assert kq["ly_do"] == "lỗi rồi"

    def test_run_cuoi_ok_thi_xong(self):
        snap = _snap(tu_chay=True, runs_hom_nay=[{"ok": True, "cho_nguoi": False, "tom_tat": "xong 8/8"}])
        kq = gac_tong.xep_trang_thai_kenh(snap, [])
        assert kq["trang_thai"] == gac_tong.TRANG_THAI_XONG

    def test_run_cuoi_cho_nguoi_thi_cho_nguoi(self):
        snap = _snap(tu_chay=True, runs_hom_nay=[{"ok": False, "cho_nguoi": True, "loi": "hết tiền"}])
        kq = gac_tong.xep_trang_thai_kenh(snap, [])
        assert kq["trang_thai"] == gac_tong.TRANG_THAI_CHO_NGUOI

    def test_run_cuoi_loi_tam_thoi_thi_tu_cho(self):
        snap = _snap(tu_chay=True, runs_hom_nay=[{"ok": False, "cho_nguoi": False, "loi": "máy chủ bận"}])
        kq = gac_tong.xep_trang_thai_kenh(snap, [])
        assert kq["trang_thai"] == gac_tong.TRANG_THAI_TU_CHO

    def test_chua_co_run_nao_thi_dang_chay(self):
        snap = _snap(tu_chay=True, runs_hom_nay=[])
        kq = gac_tong.xep_trang_thai_kenh(snap, [])
        assert kq["trang_thai"] == gac_tong.TRANG_THAI_DANG_CHAY


# ═══════════════════════════════════════════════════════════════════════════
# bao_cao_su_co — ghi đĩa + gọi bao_dong (seam)
# ═══════════════════════════════════════════════════════════════════════════


class TestBaoCaoSuCo:
    def test_thu_khong_ghi_dia_khong_goi_bao_dong(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh({"K1": _snap(tu_chay=True, ke_hoach=[])})
        ds = gac_tong.kiem_su_co(anh)
        goi = []
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO,
                               gui_khan=lambda *a, **k: goi.append((a, k)) or True,
                               gui_thuong=lambda *a, **k: goi.append((a, k)) or True,
                               ghi_dia=False)
        assert goi == []
        assert not os.path.exists(gac_tong.duong_tinh_trang(goc))
        assert not os.path.exists(gac_tong.duong_nhat_ky_ngay(goc, "2026-09-29"))

    def test_ghi_dia_thi_co_jsonl_va_tinh_trang(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh({"K1": _snap(tu_chay=True, ke_hoach=[])})
        ds = gac_tong.kiem_su_co(anh)
        assert ds  # channel chưa từng đăng -> có ít nhất một sự cố
        goi_khan = []
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO,
                               gui_khan=lambda *a, **k: goi_khan.append((a, k)) or True,
                               gui_thuong=lambda *a, **k: True,
                               ghi_dia=True)
        assert goi_khan  # sự cố khan -> gui_khan được gọi

        with open(gac_tong.duong_tinh_trang(goc), "r", encoding="utf-8") as tep:
            tt = json.load(tep)
        assert tt["kenh"]["K1"]["trang_thai"] == gac_tong.TRANG_THAI_CHO_NGUOI
        assert tt["so_su_co"] == len(ds)

        with open(gac_tong.duong_nhat_ky_ngay(goc, "2026-09-29"), "r", encoding="utf-8") as tep:
            dong = [json.loads(d) for d in tep if d.strip()]
        assert len(dong) == len(ds)

    def test_khong_su_co_thi_khong_ghi_jsonl(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh({})
        gac_tong.bao_cao_su_co(goc, anh, [], bay_gio=BAY_GIO, ghi_dia=True)
        assert not os.path.exists(gac_tong.duong_nhat_ky_ngay(goc, "2026-09-29"))
        assert os.path.exists(gac_tong.duong_tinh_trang(goc))

    def test_mot_tin_gui_hong_khong_chan_tin_sau(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh({
            "K1": _snap(tu_chay=True, ke_hoach=[]),
            "K2": _snap(tu_chay=True, ke_hoach=[]),
        })
        ds = gac_tong.kiem_su_co(anh)
        assert len(ds) == 2

        def _hong(*a, **k):
            raise RuntimeError("mạng lỗi")

        # Không ném ra ngoài — bao_cao_su_co nuốt lỗi gửi tin, vẫn ghi đĩa đủ.
        ket_qua = gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO,
                                         gui_khan=_hong, ghi_dia=True)
        assert ket_qua["so_da_bao"] == 0
        assert ket_qua["so_su_co"] == 2


class TestLocLapSuCo:
    """Vá 30/09/2026 — TL3-T7 bị ghi "khan" vào `loi-chay-max.md` mỗi 15'
    (lịch `--mot-luot`) dù `vm/logs/kiem-dom/TL3-T7.json` là CÙNG một kết quả
    kiểm cũ. `_su_co(..., dedupe_khoa=...)` cho `_kiem_may_dang_khong_nhan_dien`
    một khoá nội dung — `bao_cao_su_co` chỉ ghi/gửi lại khi khoá đổi (kết quả
    kiểm MỚI) hoặc đã đủ `NGUONG_LAP_BAO_GIO` giờ kể từ lần báo trước."""

    def _anh_hong(self):
        return _anh({"K1": _snap_khau(
            kiem_dom={"ok": False, "hong_ten": ["danh sách thẻ đã có"], "ngay": "29/09 08:18"})})

    def test_cung_ket_qua_15_phut_sau_khong_bao_lai(self, tmp_path):
        goc = str(tmp_path)
        anh = self._anh_hong()
        ds = gac_tong.kiem_su_co(anh)
        goi = []
        gui = lambda loai, *a, **k: goi.append(loai) or True
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO, gui_khan=gui, ghi_dia=True)
        assert goi.count("tai_len_hong") == 1  # lượt đầu — báo

        muoi_lam_phut_sau = BAY_GIO + _dt.timedelta(minutes=15)
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=muoi_lam_phut_sau, gui_khan=gui, ghi_dia=True)
        assert goi.count("tai_len_hong") == 1  # cùng kết quả cũ, mới 15' — KHÔNG báo lại

        with open(gac_tong.duong_loi_chay_max(goc), "r", encoding="utf-8") as tep:
            dong_su_co = [d for d in tep.readlines()
                         if d.startswith("- [") and "tải lên có thể hỏng" in d]
        assert len(dong_su_co) == 1  # chỉ MỘT dòng — lượt 15' sau không ghi thêm

    def test_ket_qua_kiem_moi_thi_bao_ngay(self, tmp_path):
        goc = str(tmp_path)
        anh_cu = self._anh_hong()
        ds_cu = gac_tong.kiem_su_co(anh_cu)
        goi = []
        gui = lambda loai, *a, **k: goi.append(loai) or True
        gac_tong.bao_cao_su_co(goc, anh_cu, ds_cu, bay_gio=BAY_GIO, gui_khan=gui, ghi_dia=True)
        assert goi.count("tai_len_hong") == 1

        anh_moi = _anh({"K1": _snap_khau(
            kiem_dom={"ok": False, "hong_ten": ["ô tiêu đề"], "ngay": "30/09 09:00"})})
        ds_moi = gac_tong.kiem_su_co(anh_moi)
        muoi_lam_phut_sau = BAY_GIO + _dt.timedelta(minutes=15)
        gac_tong.bao_cao_su_co(goc, anh_moi, ds_moi, bay_gio=muoi_lam_phut_sau, gui_khan=gui,
                               ghi_dia=True)
        assert goi.count("tai_len_hong") == 2  # kết quả kiểm MỚI (hong_ten/ngay đổi) — báo ngay

    def test_qua_nguong_gio_van_bao_lai_khong_chet_im_lang(self, tmp_path):
        goc = str(tmp_path)
        anh = self._anh_hong()
        ds = gac_tong.kiem_su_co(anh)
        goi = []
        gui = lambda loai, *a, **k: goi.append(loai) or True
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO, gui_khan=gui, ghi_dia=True)
        assert goi.count("tai_len_hong") == 1

        qua_nguong = BAY_GIO + _dt.timedelta(hours=gac_tong.NGUONG_LAP_BAO_GIO + 0.1)
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=qua_nguong, gui_khan=gui, ghi_dia=True)
        assert goi.count("tai_len_hong") == 2  # lỗi vẫn còn sau nhiều giờ — vẫn phải báo, không im lặng

    def test_trang_thai_kenh_van_cho_nguoi_du_bi_loc(self, tmp_path):
        """Lọc chỉ bớt GHI/GỬI lặp — trạng thái kênh (dashboard) vẫn phải thấy
        "CHỜ NGƯỜI" liên tục trong lúc sự cố còn đó, không được coi là đã hết
        chỉ vì không ghi log lượt này."""
        goc = str(tmp_path)
        anh = self._anh_hong()
        ds = gac_tong.kiem_su_co(anh)
        gui = lambda *a, **k: True
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO, gui_khan=gui, ghi_dia=True)
        muoi_lam_phut_sau = BAY_GIO + _dt.timedelta(minutes=15)
        kq = gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=muoi_lam_phut_sau, gui_khan=gui,
                                    ghi_dia=True)
        assert kq["trang_thai_kenh"]["K1"]["trang_thai"] == gac_tong.TRANG_THAI_CHO_NGUOI


# ═══════════════════════════════════════════════════════════════════════════
# ban_tin_ngay
# ═══════════════════════════════════════════════════════════════════════════


class TestBanTinNgay:
    def test_mot_dong_moi_kenh(self):
        anh = _anh({
            "K1": _snap(tu_chay=True, ke_hoach=[_dong_da_dang(2)]),
            "K2": _snap(tu_chay=False, ke_hoach=[]),
        })
        chu = gac_tong.ban_tin_ngay("/khong-dung", anh, bay_gio=BAY_GIO)
        assert "K1: ĐANG CHẠY" in chu or "K1: XONG" in chu
        assert "K1" in chu and "K2" in chu
        assert "video mới: có" in chu  # K1 có video đăng 2 giờ trước
        assert "trạm 8765 sống" in chu

    def test_them_vi_va_license_khi_duoc_truyen(self):
        anh = _anh({})
        chu = gac_tong.ban_tin_ngay("/khong-dung", anh, bay_gio=BAY_GIO,
                                    so_du_vnd=1_500_000, so_ngay_license_con_lai=176)
        assert "Ví" in chu
        assert "176 ngày" in chu

    def test_khong_truyen_thi_khong_co_dong_vi(self):
        anh = _anh({})
        chu = gac_tong.ban_tin_ngay("/khong-dung", anh, bay_gio=BAY_GIO)
        assert "Ví" not in chu


# ═══════════════════════════════════════════════════════════════════════════
# chup_trang_thai — tích hợp trên tmp_path thật, KHÔNG gọi schtasks/socket thật
# ═══════════════════════════════════════════════════════════════════════════


def _kenh_that(goc, ma, *, tu_chay=True):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("ma: {0}\nten: {0}\ntu_chay: {1}\n".format(ma, "true" if tu_chay else "false"))
    return thu_muc


def _ghi_ke_hoach_that(goc, ma, hang):
    duong = ke_hoach_dang.duong_ke_hoach(goc, ma)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(ke_hoach_dang.COT)
    for h in hang:
        w.writerow([h.get(c, "") for c in ke_hoach_dang.COT])
    with open(duong, "w", encoding="utf-8", newline="") as tep:
        tep.write(buf.getvalue())


def _chay_lenh_gia(lenh):
    return 0, "\"TaskName\",\"Next Run Time\"\r\n\"\\ShopAPI-TuChay\",\"N/A\"\r\n"


def _kiem_cong_gia(cong):
    return cong == 8765


class TestChupTrangThaiTichHop:
    def test_khong_ghi_gi_ra_dia(self, tmp_path):
        goc = str(tmp_path)
        _kenh_that(goc, "K1")
        truoc = sorted(str(p) for p in tmp_path.rglob("*"))
        gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh_gia,
                                 kiem_cong=_kiem_cong_gia)
        sau = sorted(str(p) for p in tmp_path.rglob("*"))
        assert truoc == sau

    def test_khong_dung_schtasks_socket_that(self, tmp_path):
        goc = str(tmp_path)
        _kenh_that(goc, "K1")
        goi_lenh = []

        def _chay_lenh(lenh):
            goi_lenh.append(lenh)
            return _chay_lenh_gia(lenh)

        goi_cong = []

        def _kiem_cong(cong):
            goi_cong.append(cong)
            return False

        gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh, kiem_cong=_kiem_cong)
        assert goi_lenh  # có gọi qua seam, không gọi subprocess thật trực tiếp
        assert set(goi_cong) == {8765, 8767}

    def test_doc_dung_co_tu_chay_va_ke_hoach(self, tmp_path):
        goc = str(tmp_path)
        _kenh_that(goc, "K1", tu_chay=True)
        _ghi_ke_hoach_that(goc, "K1", [
            {"Mã gói": "K1-0001", "Ngày đăng": "27/09/2026", "Giờ đăng": "20:00",
             "Tiêu đề": "video cũ", "Sẵn sàng": "x", "Trạng thái đăng": "ĐÃ ĐĂNG"},
            {"Mã gói": "K1-0002", "Ngày đăng": "29/09/2026", "Giờ đăng": "20:00",
             "Tiêu đề": "video sắp đăng", "Sẵn sàng": "x", "Trạng thái đăng": ""},
        ])
        anh = gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh_gia,
                                       kiem_cong=_kiem_cong_gia)
        snap = anh["kenh"]["K1"]
        assert snap["tu_chay"] is True
        loai = {d["Mã gói"]: d["_loai"] for d in snap["ke_hoach"]}
        assert loai["K1-0001"] == "da_dang"
        assert loai["K1-0002"] == "sap_dang"

    def test_khoa_may_cu_va_pid_chet_duoc_doc_dung(self, tmp_path):
        goc = str(tmp_path)
        _kenh_that(goc, "K1")
        duong_khoa = os.path.join(goc, "workspace", "tu-chay", ".khoa-may")
        os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
        bat_dau = BAY_GIO.timestamp() - gac_tong.NGUONG_CANH_BAO_KHOA_GIAY - 3600
        with open(duong_khoa, "w", encoding="utf-8") as tep:
            json.dump({"pid": 999_999_999, "bat_dau": bat_dau}, tep)

        anh = gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh_gia,
                                       kiem_cong=_kiem_cong_gia)
        khoa = anh["may"]["khoa_may"]
        assert khoa["co"] is True
        assert khoa["con_song"] is False  # PID giả không tồn tại
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khoa_may_qua_lau"]
        assert len(ds) == 1
        assert "CHẾT" in ds[0]["chuyen_gi"]

    def test_may_co_du_truong_moi_29_09(self, tmp_path):
        """`may` giờ có thêm `ram`/`khe`/`lan_api`/`so_tien_trinh_tu_chay`/
        `chi_tieu_hom_qua_vnd` (chế độ chạy max, xem GHI-CHU bản vá)."""
        goc = str(tmp_path)
        _kenh_that(goc, "K1")
        anh = gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh_gia,
                                       kiem_cong=_kiem_cong_gia)
        may = anh["may"]
        assert "trong_gb" in may["ram"] and "tong_gb" in may["ram"]
        assert set(may["khe"].keys()) == {"nang", "api", "cho"}
        assert isinstance(may["lan_api"], int) and 1 <= may["lan_api"] <= 4
        # `_chay_lenh_gia` trả CSV của schtasks bất kể lệnh gọi — không có PID
        # số nào để đếm, nên đếm ra 0 (không phải None: seam có phản hồi).
        assert may["so_tien_trinh_tu_chay"] == 0
        assert may["chi_tieu_hom_qua_vnd"] is None  # chưa có sổ core.chi_phi

    def test_dung_may_dang_dom_doc_dung_tu_may_ao_json(self, tmp_path):
        goc = str(tmp_path)
        _kenh_that(goc, "K1")
        os.makedirs(os.path.join(goc, "CHANNEL", "K1"), exist_ok=True)
        with open(os.path.join(goc, "CHANNEL", "K1", "may-ao.json"), "w", encoding="utf-8") as tep:
            json.dump({"tu_dang": True, "cach_dang": "dom"}, tep)
        anh = gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh_gia,
                                       kiem_cong=_kiem_cong_gia)
        assert anh["kenh"]["K1"]["dung_may_dang_dom"] is True

    def test_khong_dung_may_dang_dom_khi_tu_dang_tat(self, tmp_path):
        goc = str(tmp_path)
        _kenh_that(goc, "K1")
        os.makedirs(os.path.join(goc, "CHANNEL", "K1"), exist_ok=True)
        with open(os.path.join(goc, "CHANNEL", "K1", "may-ao.json"), "w", encoding="utf-8") as tep:
            json.dump({"tu_dang": False, "cach_dang": "anh"}, tep)
        anh = gac_tong.chup_trang_thai(goc, bay_gio=BAY_GIO, chay_lenh=_chay_lenh_gia,
                                       kiem_cong=_kiem_cong_gia)
        assert anh["kenh"]["K1"]["dung_may_dang_dom"] is False


# ═══════════════════════════════════════════════════════════════════════════
# Kiểm thêm 29/09/2026 (tối) — "chế độ chạy max"
# ═══════════════════════════════════════════════════════════════════════════


def _snap_khau(bao_cao_tuoi_phut=None, runs_hom_nay=None, kiem_dom=None,
               dung_may_dang_dom=True):
    s = _snap(tu_chay=True, runs_hom_nay=runs_hom_nay)
    s["bao_cao_tuoi_phut"] = bao_cao_tuoi_phut
    s["kiem_dom"] = kiem_dom
    s["dung_may_dang_dom"] = dung_may_dang_dom
    return s


class TestKhauDungQuaLau:
    def test_khong_ai_giu_khe_nang_thi_khong_bao(self):
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=999)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khau_dung_qua_lau"]
        assert ds == []

    def test_khe_nang_giu_kenh_khac_thi_khong_bao(self):
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K2", "viec": "san_xuat", "pid": 1}, "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=999)}, may=may)
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khau_dung_qua_lau"]
        assert ds == []

    def test_duoi_nguong_thi_khong_bao(self):
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 1}, "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_KHAU_DUNG_PHUT - 1)}, may=may)
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khau_dung_qua_lau"]
        assert ds == []

    def test_qua_nguong_dung_kenh_thi_bao(self):
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 1}, "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_KHAU_DUNG_PHUT + 1)}, may=may)
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khau_dung_qua_lau"]
        assert len(ds) == 1
        assert ds[0]["kenh"] == "K1"
        assert "dung_video" in ds[0]["chuyen_gi"]


# ═══════════════════════════════════════════════════════════════════════════
# `_moc_hoat_dong_tuoi_phut` tích hợp trên tmp_path thật — sự cố báo giả
# TL3-T7 29/09/2026 23:18 ("đứng 296 phút" trong khi tu-chay.log vừa có dòng
# lúc 23:14) và ca TREO THẬT (không nguồn nào có dấu vết gần đây + CPU đứng
# yên đủ hai lần theo dõi cách nhau 120').
# ═══════════════════════════════════════════════════════════════════════════


def _ghi_khoa_nang_that(goc, ma, *, viec="dung", pid=None, bat_dau=None):
    duong = gac_tong.khe.duong_khoa_nang(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump({"pid": pid or os.getpid(), "tid": 1, "nguon": "khe",
                   "loai": "nang", "viec": viec, "kenh": ma, "uu_tien": 2,
                   "bat_dau": bat_dau or BAY_GIO.timestamp(), "han_giay": None}, tep)


def _ghi_tu_chay_log_that(goc, dong_list):
    """`dong_list`: `[(datetime, ma_kenh, noi_dung), ...]` — đúng khuôn dòng
    thật `core.tu_chay._ghi_dong_log` + nhãn kênh gắn ở CLI gốc `tu_chay.py`."""
    duong = gac_tong.tu_chay.duong_log_tat_ca(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        for luc, ma, noi_dung in dong_list:
            tep.write("[{0}] [{1}] {2}\n".format(
                luc.strftime("%Y-%m-%d %H:%M:%S"), ma, noi_dung))


def _chay_lenh_cpu_co_dinh(cpu_giay):
    """Seam `chay_lenh` giả: trả một số CPU-giây CỐ ĐỊNH cho lệnh PowerShell
    đo CPU (`_cpu_giay_tien_trinh`), còn lại vẫn dùng `_chay_lenh_gia` (CSV
    schtasks giả) — để `chup_trang_thai` đọc được cả hai qua CÙNG một seam."""
    def _fn(lenh):
        if any("TotalProcessorTime" in str(x) for x in (lenh or [])):
            return 0, str(cpu_giay)
        return _chay_lenh_gia(lenh)
    return _fn


def _ghi_bao_cao_ngay_that(goc, ma, ngay_str, *, mtime_epoch):
    duong = gac_tong.tu_chay.duong_bao_cao_ngay(goc, ma, ngay_str)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump({"ngay": ngay_str, "kenh": ma, "runs": [], "nhat_ky": []}, tep)
    os.utime(duong, (mtime_epoch, mtime_epoch))


class TestMocHoatDongTichHop:
    def test_ca_that_tl3_khong_bao_gia_khong_bi_dung(self, tmp_path):
        """Tái hiện ĐÚNG ca TL3-T7 29/09/2026 23:18: tệp báo cáo ngày đứng
        yên từ nhiều giờ trước (chỉ ghi lại ở CUỐI cả lượt — bình thường giữa
        một lượt dài), nhưng `tu-chay.log` VỪA có dòng thật lúc 23:14 (khâu
        clip vừa bàn giao cho khâu dựng). KHÔNG được báo `khau_dung_qua_lau`,
        càng không được `tu_sua` dừng."""
        goc = str(tmp_path)
        ma = "TL3-T7"
        _kenh_that(goc, ma, tu_chay=True)
        bay_gio = _dt.datetime(2026, 9, 29, 23, 18, 0)

        _ghi_bao_cao_ngay_that(goc, ma, bay_gio.strftime("%Y-%m-%d"),
                               mtime_epoch=(bay_gio - _dt.timedelta(hours=5)).timestamp())
        _ghi_tu_chay_log_that(goc, [
            (bay_gio - _dt.timedelta(minutes=4), ma,
             "    clip: 179/179 đã có sẵn từ khâu ảnh — không làm lại."),
        ])
        _ghi_khoa_nang_that(goc, ma, viec="dung")

        anh = gac_tong.chup_trang_thai(goc, bay_gio=bay_gio, chay_lenh=_chay_lenh_gia,
                                       kiem_cong=_kiem_cong_gia)
        tuoi = anh["kenh"][ma]["bao_cao_tuoi_phut"]
        assert tuoi is not None and tuoi < 10  # ~4 phút — KHÔNG PHẢI 296

        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "khau_dung_qua_lau"]
        assert ds == []  # không báo giả

        goi = []
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=bay_gio, ghi_dia=True,
                                    giet=lambda pid: goi.append(pid) or True)
        assert hanh_dong == []
        assert not goi  # không dừng lượt đang dựng thật

    def test_ca_treo_that_bi_dung_sau_du_bang_chung(self, tmp_path):
        """Ca TREO THẬT: không nguồn nào có dấu vết gần đây (báo cáo ngày cũ
        6 tiếng, không `tu-chay.log`/`PROJECTS/AUTO/<k>`/nhật ký khe nào mới),
        CPU đứng yên suốt HAI lần theo dõi cách nhau đủ 120' — mới bị dừng.

        Giờ bắt đầu chọn giữa trưa (không phải 23:18 như ca TL3-T7) để hai
        lần theo dõi cách nhau 120' KHÔNG băng qua nửa đêm — `bao_cao_tuoi_phut`
        tra tệp báo cáo ngày theo `bay_gio.strftime("%Y-%m-%d")`, băng ngày sẽ
        đổi sang tra tệp của NGÀY MỚI (không tồn tại trong bài kiểm này) và
        làm sai lệch phép đo — cùng giới hạn đã có ở bản gốc, ngoài phạm vi
        vá lần này."""
        goc = str(tmp_path)
        ma = "TLX-T7"
        _kenh_that(goc, ma, tu_chay=True)
        bay_gio_1 = _dt.datetime(2026, 9, 29, 12, 0, 0)

        _ghi_bao_cao_ngay_that(goc, ma, bay_gio_1.strftime("%Y-%m-%d"),
                               mtime_epoch=(bay_gio_1 - _dt.timedelta(hours=6)).timestamp())
        _ghi_khoa_nang_that(goc, ma, viec="dung")
        chay_lenh_cpu = _chay_lenh_cpu_co_dinh(500.0)

        anh_1 = gac_tong.chup_trang_thai(goc, bay_gio=bay_gio_1, chay_lenh=chay_lenh_cpu,
                                         kiem_cong=_kiem_cong_gia)
        assert anh_1["kenh"][ma]["bao_cao_tuoi_phut"] > gac_tong.NGUONG_TU_DUNG_KHAU_PHUT

        goi = []
        giet = lambda pid: goi.append(pid) or True
        hanh_dong_1 = gac_tong.tu_sua(goc, anh_1, bay_gio=bay_gio_1, ghi_dia=True, giet=giet)
        assert hanh_dong_1 == []  # lần đầu: mới ghi nhận nghi ngờ, chưa đủ bằng chứng
        assert not goi

        bay_gio_2 = bay_gio_1 + _dt.timedelta(minutes=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT)
        anh_2 = gac_tong.chup_trang_thai(goc, bay_gio=bay_gio_2, chay_lenh=chay_lenh_cpu,
                                         kiem_cong=_kiem_cong_gia)
        hanh_dong_2 = gac_tong.tu_sua(goc, anh_2, bay_gio=bay_gio_2, ghi_dia=True, giet=giet)
        assert len(hanh_dong_2) == 1 and hanh_dong_2[0]["loai"] == "dung_tu_chay_treo"
        assert goi == [os.getpid()]


class TestLoiLapCungKhau:
    def _run(self, ok=False, cho_nguoi=False, buoc_loi="san_xuat"):
        return {"ok": ok, "cho_nguoi": cho_nguoi, "buoc_loi": buoc_loi}

    def test_duoi_3_lot_thi_khong_bao(self):
        anh = _anh({"K1": _snap_khau(runs_hom_nay=[self._run(), self._run()])})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "loi_lap_cung_khau"]
        assert ds == []

    def test_3_lot_cung_buoc_thi_bao(self):
        anh = _anh({"K1": _snap_khau(runs_hom_nay=[self._run()] * 3)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "loi_lap_cung_khau"]
        assert len(ds) == 1
        assert "san_xuat" in ds[0]["chuyen_gi"]

    def test_3_lot_khac_buoc_thi_khong_bao(self):
        runs = [self._run(buoc_loi="san_xuat"), self._run(buoc_loi="ban_giao"),
                self._run(buoc_loi="san_xuat")]
        anh = _anh({"K1": _snap_khau(runs_hom_nay=runs)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "loi_lap_cung_khau"]
        assert ds == []

    def test_lan_cuoi_ok_thi_khong_bao(self):
        runs = [self._run(), self._run(), self._run(ok=True)]
        anh = _anh({"K1": _snap_khau(runs_hom_nay=runs)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "loi_lap_cung_khau"]
        assert ds == []


class TestMayDangKhongNhanDien:
    def test_khong_co_kiem_dom_thi_khong_bao(self):
        anh = _anh({"K1": _snap_khau()})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tai_len_hong"]
        assert ds == []

    def test_kiem_dom_ok_thi_khong_bao(self):
        anh = _anh({"K1": _snap_khau(kiem_dom={"ok": True})})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tai_len_hong"]
        assert ds == []

    def test_kiem_dom_hong_thi_bao(self):
        anh = _anh({"K1": _snap_khau(kiem_dom={"ok": False, "hong_ten": ["Xuất bản"], "ngay": "29/09"})})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tai_len_hong"]
        assert len(ds) == 1
        assert "Xuất bản" in ds[0]["chuyen_gi"]

    def test_khong_dung_may_dang_dom_thi_khong_bao_du_kiem_dom_hong(self):
        """Chẩn đoán thật 29/09/2026 (TL4-T7: tu_dang=false, cach_dang="anh")
        — kênh KHÔNG dùng máy đăng DOM thì kết quả kiểm DOM không liên quan,
        báo sẽ là báo giả. Cùng guard `bang_dieu_khien.viec_cua_ban` mục 10."""
        anh = _anh({"K1": _snap_khau(
            kiem_dom={"ok": False, "hong_ten": ["Xuất bản"], "ngay": "29/09"},
            dung_may_dang_dom=False)})
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "tai_len_hong"]
        assert ds == []


class TestChoKheQuaLau:
    def _may(self, cho):
        may = dict(_anh()["may"])
        may["khe"] = {"nang": None, "api": [], "cho": cho}
        return may

    def test_khong_ai_cho_thi_khong_bao(self):
        anh = _anh(may=self._may([]))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "cho_khe_qua_lau"]
        assert ds == []

    def test_duoi_nguong_thi_khong_bao(self):
        luc_xin = BAY_GIO.timestamp() - (gac_tong.NGUONG_CHO_KHE_PHUT - 1) * 60
        anh = _anh(may=self._may([{"pid": 1, "viec": "san_xuat", "kenh": "K1", "luc_xin": luc_xin}]))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "cho_khe_qua_lau"]
        assert ds == []

    def test_qua_nguong_thi_bao(self):
        luc_xin = BAY_GIO.timestamp() - (gac_tong.NGUONG_CHO_KHE_PHUT + 1) * 60
        anh = _anh(may=self._may([{"pid": 1, "viec": "san_xuat", "kenh": "K1", "luc_xin": luc_xin}]))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "cho_khe_qua_lau"]
        assert len(ds) == 1
        assert ds[0]["kenh"] == "K1"


class TestRamThap:
    def _may(self, trong_gb):
        may = dict(_anh()["may"])
        may["ram"] = {"trong_gb": trong_gb, "tong_gb": 16.0}
        return may

    def test_du_ram_thi_khong_bao(self):
        anh = _anh(may=self._may(8.0))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "ram_thap"]
        assert ds == []

    def test_thieu_ram_thi_bao(self):
        anh = _anh(may=self._may(gac_tong.NGUONG_RAM_TRONG_GB - 0.1))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "ram_thap"]
        assert len(ds) == 1

    def test_khong_ro_ram_thi_khong_bao(self):
        anh = _anh(may=self._may(None))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "ram_thap"]
        assert ds == []


class TestKhoaMayPidChet:
    def test_pid_con_song_thi_khong_bao(self):
        may = dict(_anh()["may"])
        may["khoa_may"] = {"co": True, "tuoi_giay": 60.0, "pid": 111, "con_song": True}
        ds = [s for s in gac_tong.kiem_su_co(_anh(may=may)) if s["loai"] == "khoa_may_pid_chet"]
        assert ds == []

    def test_pid_chet_thi_bao_ngay_du_moi(self):
        """Khác `khoa_may_qua_lau` (đợi 6 giờ) — PID chết thì báo NGAY."""
        may = dict(_anh()["may"])
        may["khoa_may"] = {"co": True, "tuoi_giay": 30.0, "pid": 111, "con_song": False}
        ds = [s for s in gac_tong.kiem_su_co(_anh(may=may)) if s["loai"] == "khoa_may_pid_chet"]
        assert len(ds) == 1
        assert "111" in ds[0]["chuyen_gi"]


class TestQuaNhieuTuChay:
    def _may(self, so, lan_api):
        may = dict(_anh()["may"])
        may["so_tien_trinh_tu_chay"] = so
        may["lan_api"] = lan_api
        return may

    def test_trong_tran_thi_khong_bao(self):
        anh = _anh(may=self._may(2, 2))  # tran = lan_api + 1 = 3
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "qua_nhieu_tu_chay"]
        assert ds == []

    def test_vuot_tran_thi_bao(self):
        anh = _anh(may=self._may(4, 2))  # tran = 3, so = 4
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "qua_nhieu_tu_chay"]
        assert len(ds) == 1

    def test_khong_dem_duoc_thi_khong_bao(self):
        anh = _anh(may=self._may(None, 2))
        ds = [s for s in gac_tong.kiem_su_co(anh) if s["loai"] == "qua_nhieu_tu_chay"]
        assert ds == []


class TestViSapCan:
    def test_khong_truyen_so_du_thi_khong_kiem(self):
        may = dict(_anh()["may"])
        may["chi_tieu_hom_qua_vnd"] = 200_000.0
        ds = [s for s in gac_tong.kiem_su_co(_anh(may=may)) if s["loai"] == "vi_sap_can"]
        assert ds == []

    def test_khong_co_so_chi_tieu_thi_khong_bao(self):
        may = dict(_anh()["may"])
        may["chi_tieu_hom_qua_vnd"] = None
        ds = [s for s in gac_tong.kiem_su_co(_anh(may=may), so_du_vnd=100_000.0)
             if s["loai"] == "vi_sap_can"]
        assert ds == []

    def test_du_ngay_thi_khong_bao(self):
        may = dict(_anh()["may"])
        may["chi_tieu_hom_qua_vnd"] = 100_000.0
        ds = [s for s in gac_tong.kiem_su_co(_anh(may=may), so_du_vnd=1_000_000.0)
             if s["loai"] == "vi_sap_can"]
        assert ds == []

    def test_thieu_ngay_thi_bao(self):
        may = dict(_anh()["may"])
        may["chi_tieu_hom_qua_vnd"] = 100_000.0
        ds = [s for s in gac_tong.kiem_su_co(_anh(may=may), so_du_vnd=200_000.0)
             if s["loai"] == "vi_sap_can"]
        assert len(ds) == 1


# ═══════════════════════════════════════════════════════════════════════════
# tu_sua — hai ca TỰ SỬA an toàn
# ═══════════════════════════════════════════════════════════════════════════


class TestTuSua:
    def test_khong_co_gi_de_sua_thi_rong(self):
        assert gac_tong.tu_sua("/khong-dung-toi", _anh(), ghi_dia=False) == []

    @staticmethod
    def _ghi_khoa(goc, pid, bat_dau):
        duong = gac_tong.khe.duong_khoa_nang(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"pid": pid, "bat_dau": bat_dau}, tep)
        return duong

    def test_khoa_may_pid_chet_du_tuoi_thi_xoa(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        bat_dau = BAY_GIO.timestamp() - 3600
        duong = self._ghi_khoa(goc, 111, bat_dau)
        may = dict(_anh()["may"])
        may["khoa_may"] = {"co": True, "tuoi_giay": 3600.0, "pid": 111, "con_song": False, "bat_dau": bat_dau}
        monkeypatch.setattr(gac_tong.khe, "pid_con_song", lambda pid: False)
        hanh_dong = gac_tong.tu_sua(goc, _anh(may=may), bay_gio=BAY_GIO, ghi_dia=True)
        assert len(hanh_dong) == 1 and hanh_dong[0]["loai"] == "don_khoa_may_chet"
        assert not os.path.exists(duong)
        duong_jsonl = gac_tong.duong_nhat_ky_ngay(goc, BAY_GIO.strftime("%Y-%m-%d"))
        assert os.path.isfile(duong_jsonl)
        assert os.path.isfile(gac_tong.duong_loi_chay_max(goc))

    def test_khoa_moi_chua_du_tuoi_thi_chua_xoa(self, tmp_path, monkeypatch):
        """VÁ 06/10: PID chết mà khoá mới 30 giây — chưa dọn (người xin khe thật tự giành)."""
        goc = str(tmp_path)
        bat_dau = BAY_GIO.timestamp() - 30
        duong = self._ghi_khoa(goc, 111, bat_dau)
        may = dict(_anh()["may"])
        may["khoa_may"] = {"co": True, "tuoi_giay": 30.0, "pid": 111, "con_song": False, "bat_dau": bat_dau}
        monkeypatch.setattr(gac_tong.khe, "pid_con_song", lambda pid: False)
        assert gac_tong.tu_sua(goc, _anh(may=may), bay_gio=BAY_GIO, ghi_dia=True) == []
        assert os.path.exists(duong)

    def test_khoa_da_doi_chu_sau_anh_chup_thi_khong_xoa(self, tmp_path, monkeypatch):
        """Ảnh chụp thấy PID 111 chết, nhưng TỚI LÚC XOÁ khoá đã thuộc PID 222 đang sống."""
        goc = str(tmp_path)
        duong = self._ghi_khoa(goc, 222, BAY_GIO.timestamp() - 5)
        may = dict(_anh()["may"])
        may["khoa_may"] = {"co": True, "tuoi_giay": 3600.0, "pid": 111, "con_song": False,
                           "bat_dau": BAY_GIO.timestamp() - 3600}
        monkeypatch.setattr(gac_tong.khe, "pid_con_song", lambda pid: pid == 222)
        assert gac_tong.tu_sua(goc, _anh(may=may), bay_gio=BAY_GIO, ghi_dia=True) == []
        with open(duong, encoding="utf-8") as tep:
            assert json.load(tep)["pid"] == 222

    def test_thu_khong_that_su_xoa(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        bat_dau = BAY_GIO.timestamp() - 3600
        duong = self._ghi_khoa(goc, 111, bat_dau)
        may = dict(_anh()["may"])
        may["khoa_may"] = {"co": True, "tuoi_giay": 3600.0, "pid": 111, "con_song": False, "bat_dau": bat_dau}
        hanh_dong = gac_tong.tu_sua(goc, _anh(may=may), bay_gio=BAY_GIO, ghi_dia=False)
        assert len(hanh_dong) == 1
        assert hanh_dong[0]["thuc_hien"] is False
        assert os.path.exists(duong)  # --thu: KHÔNG xoá thật
        assert not os.path.isfile(gac_tong.duong_nhat_ky_ngay(goc, BAY_GIO.strftime("%Y-%m-%d")))

    def test_dang_tai_len_thi_khong_bao_gio_giet(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "tai_len", "pid": 222}, "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 999)}, may=may)
        goi = []
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=BAY_GIO, ghi_dia=True, giet=lambda pid: goi.append(pid))
        assert hanh_dong == []
        assert not goi

    def test_treo_qua_lau_lan_dau_chi_ghi_nghi_ngo_chua_giet(self, tmp_path):
        """VÁ 29/09/2026 (sự cố báo giả TL3-T7): MỘT tín hiệu "tuổi > 120'"
        không còn đủ — lần đầu nghi ngờ chỉ GHI LẠI mốc theo dõi, chưa dừng gì."""
        goc = str(tmp_path)
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222, "cpu_giay": 500.0},
                     "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 1)}, may=may)
        goi = []
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=BAY_GIO, ghi_dia=True,
                                    giet=lambda pid: goi.append(pid) or True)
        assert hanh_dong == []
        assert not goi
        assert os.path.isfile(gac_tong._duong_nghi_treo(goc))  # noqa: SLF001 — kiểm tra tệp theo dõi

    def test_treo_qua_lau_khong_giu_tai_len_thi_dung_sau_khi_du_bang_chung(self, tmp_path):
        """Lần HAI, cách lần đầu đủ `NGUONG_TU_DUNG_KHAU_PHUT` phút, CPU vẫn
        đứng yên (cùng PID) — ĐỦ bằng chứng, mới thật sự dừng."""
        goc = str(tmp_path)
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222, "cpu_giay": 500.0},
                     "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 1)}, may=may)
        goi = []
        giet = lambda pid: goi.append(pid) or True

        gac_tong.tu_sua(goc, anh, bay_gio=BAY_GIO, ghi_dia=True, giet=giet)
        assert not goi  # lần đầu: chỉ ghi nhận nghi ngờ

        bay_gio_2 = BAY_GIO + _dt.timedelta(minutes=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT)
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=bay_gio_2, ghi_dia=True, giet=giet)
        assert len(hanh_dong) == 1 and hanh_dong[0]["loai"] == "dung_tu_chay_treo"
        assert goi == [222]

    def test_cpu_con_nhich_thi_khong_bao_gio_giet(self, tmp_path):
        """CPU vừa nhích giữa hai lần theo dõi = còn sống thật — đặt lại mốc,
        KHÔNG bao giờ dừng dù `tuoi_phut` vẫn báo vượt ngưỡng."""
        goc = str(tmp_path)
        may1 = dict(_anh()["may"])
        may1["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222, "cpu_giay": 500.0},
                      "api": [], "cho": []}
        anh1 = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 1)}, may=may1)
        goi = []
        giet = lambda pid: goi.append(pid) or True
        gac_tong.tu_sua(goc, anh1, bay_gio=BAY_GIO, ghi_dia=True, giet=giet)

        bay_gio_2 = BAY_GIO + _dt.timedelta(minutes=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT)
        may2 = dict(_anh()["may"])
        may2["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222, "cpu_giay": 560.0},
                      "api": [], "cho": []}
        anh2 = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 1)}, may=may2)
        hanh_dong = gac_tong.tu_sua(goc, anh2, bay_gio=bay_gio_2, ghi_dia=True, giet=giet)
        assert hanh_dong == []
        assert not goi

        # Lần BA, đủ 120' NỮA kể từ mốc vừa đặt lại, CPU đứng yên — giờ mới dừng.
        bay_gio_3 = bay_gio_2 + _dt.timedelta(minutes=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT)
        hanh_dong_3 = gac_tong.tu_sua(goc, anh2, bay_gio=bay_gio_3, ghi_dia=True, giet=giet)
        assert len(hanh_dong_3) == 1
        assert goi == [222]

    def test_khong_do_duoc_cpu_thi_khong_bao_gio_giet(self, tmp_path):
        """`cpu_giay=None` (PowerShell lỗi/không đo được) = CHƯA đủ bằng
        chứng — không bao giờ tự dừng, dù chờ rất lâu."""
        goc = str(tmp_path)
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222, "cpu_giay": None},
                     "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 1)}, may=may)
        goi = []
        giet = lambda pid: goi.append(pid) or True
        gac_tong.tu_sua(goc, anh, bay_gio=BAY_GIO, ghi_dia=True, giet=giet)

        bay_gio_2 = BAY_GIO + _dt.timedelta(minutes=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT * 3)
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=bay_gio_2, ghi_dia=True, giet=giet)
        assert hanh_dong == []
        assert not goi

    def test_thu_khong_ghi_nghi_ngo_moi_nhung_van_bao_neu_da_du_bang_chung_tu_truoc(self, tmp_path):
        """`--thu` (ghi_dia=False) không tự ghi mốc theo dõi mới, nhưng NẾU
        một lần chạy THẬT trước đó đã tích đủ bằng chứng thì `--thu` vẫn phải
        cho thấy đúng hành động sẽ xảy ra (không giấu người xem)."""
        goc = str(tmp_path)
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222, "cpu_giay": 500.0},
                     "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT + 1)}, may=may)
        gac_tong.tu_sua(goc, anh, bay_gio=BAY_GIO, ghi_dia=True, giet=lambda pid: True)  # ghi mốc thật

        bay_gio_2 = BAY_GIO + _dt.timedelta(minutes=gac_tong.NGUONG_TU_DUNG_KHAU_PHUT)
        goi = []
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=bay_gio_2, ghi_dia=False,
                                    giet=lambda pid: goi.append(pid) or True)
        assert len(hanh_dong) == 1 and hanh_dong[0]["thuc_hien"] is False
        assert not goi  # --thu: KHÔNG giết thật

    def test_treo_chua_qua_nguong_tu_dung_thi_khong_giet(self, tmp_path):
        """Cảnh báo ở 90' (`NGUONG_KHAU_DUNG_PHUT`) nhưng CHƯA đủ 120' để
        tự dừng (`NGUONG_TU_DUNG_KHAU_PHUT`) — chỉ báo, không hành động."""
        goc = str(tmp_path)
        may = dict(_anh()["may"])
        may["khe"] = {"nang": {"kenh": "K1", "viec": "dung_video", "pid": 222}, "api": [], "cho": []}
        anh = _anh({"K1": _snap_khau(bao_cao_tuoi_phut=gac_tong.NGUONG_KHAU_DUNG_PHUT + 1)}, may=may)
        goi = []
        hanh_dong = gac_tong.tu_sua(goc, anh, bay_gio=BAY_GIO, ghi_dia=True, giet=lambda pid: goi.append(pid))
        assert hanh_dong == []
        assert not goi


class TestLoiChayMaxMd:
    def test_tao_tep_kem_tieu_de_khi_chua_co(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh({"K1": _snap(tu_chay=True, ke_hoach=[])})
        ds = gac_tong.kiem_su_co(anh)
        assert ds  # kênh chưa từng đăng → có ít nhất một sự cố
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO,
                               gui_khan=lambda *a, **k: False, gui_thuong=lambda *a, **k: False)
        duong = gac_tong.duong_loi_chay_max(goc)
        assert os.path.isfile(duong)
        with open(duong, encoding="utf-8") as tep:
            noi_dung = tep.read()
        assert noi_dung.startswith("# Lỗi chạy max")
        assert "K1" in noi_dung

    def test_khong_su_co_thi_khong_tao_tep(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh()  # không kênh nào → không sự cố
        gac_tong.bao_cao_su_co(goc, anh, [], bay_gio=BAY_GIO)
        assert not os.path.isfile(gac_tong.duong_loi_chay_max(goc))


class TestKiemLaiGoiKet:
    def _dung(self, tmp_path, monkeypatch, ket_qua):
        from core import ban_giao_dang, gac_tong
        goc = str(tmp_path)
        monkeypatch.setattr(ban_giao_dang, "liet_ke_goi_ket", lambda g, k: ["K-0001"])
        calls = []

        class P:
            def nha(self): calls.append("nha")
        kl = lambda g, k, toi_da=0: ket_qua  # noqa: E731
        return gac_tong, goc, kl, (lambda *a, **k: P()), calls

    def test_chua_dat_bao_va_debounce(self, tmp_path, monkeypatch):
        import datetime as dt
        gt, goc, kl, tg, calls = self._dung(tmp_path, monkeypatch,
                                            [{"ma": "K-0001", "ket_qua": "chua_dat", "loi": ["x"]}])
        t0 = dt.datetime(2026, 9, 30, 10, 0)
        sc = gt.kiem_lai_goi_ket_dinh_ky(goc, ["K"], bay_gio=t0, kiem_lai=kl, thu_giu=tg)
        assert len(sc) == 1 and sc[0]["dedupe_khoa"] == "qa-ket:K-0001" and calls == ["nha"]
        # 15' sau: không chạy lại QA nhưng vẫn phát sự cố (để bộ lọc lặp 4h xử lý)
        sc = gt.kiem_lai_goi_ket_dinh_ky(goc, ["K"], bay_gio=t0 + dt.timedelta(minutes=15),
                                         kiem_lai=lambda *a, **k: 1 / 0, thu_giu=tg)
        assert len(sc) == 1 and calls == ["nha"]

    def test_khe_ban_thi_khong_danh_dau(self, tmp_path, monkeypatch):
        import datetime as dt
        gt, goc, kl, tg, calls = self._dung(tmp_path, monkeypatch, [])
        gt.kiem_lai_goi_ket_dinh_ky(goc, ["K"], bay_gio=dt.datetime(2026, 9, 30, 10, 0),
                                    kiem_lai=kl, thu_giu=lambda *a, **k: None)
        import json, os
        assert json.load(open(os.path.join(goc, "workspace", "gac-tong", "qa-ket.json")))["luc"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# Kiểm toán 1 năm (06/10/2026): báo MỘT lần, kiểm hỏng không nuốt kiểm khác,
# lượt sập có sổ + nhịp tim
# ═══════════════════════════════════════════════════════════════════════════


class TestBaoMotLan:
    def test_kenh_48h_khong_video_bao_mot_lan_roi_moi_ngay(self, tmp_path):
        goc = str(tmp_path)
        anh = _anh({"K1": _snap(ke_hoach=[_dong_da_dang(60)])})
        ds = gac_tong.kiem_su_co(anh)
        assert [s["loai"] for s in ds] == ["khong_video_moi"]
        gui = []

        def _gui(*a, **k):
            gui.append(a[0])
            return True

        for phut in (0, 15, 30, 60 * 23):
            gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO + _dt.timedelta(minutes=phut),
                                   gui_khan=_gui, gui_thuong=_gui)
        assert gui == ["khong_video_moi"]
        gac_tong.bao_cao_su_co(goc, anh, ds, bay_gio=BAY_GIO + _dt.timedelta(hours=24, minutes=1),
                               gui_khan=_gui, gui_thuong=_gui)
        assert gui == ["khong_video_moi", "khong_video_moi"]

    def test_so_lieu_studio_cu_khong_nhac_moi_gio(self):
        ds = gac_tong.kiem_su_co(_anh({"K1": _snap(ke_hoach=[_dong_da_dang(1)], chi_so_tuoi_gio=100.0)}))
        sc = [s for s in ds if s["loai"] == "so_lieu_studio_cu"][0]
        assert sc["dedupe_khoa"] and sc["lap_gio"] == 24.0


class TestKiemHongKhongNuotKiemKhac:
    def test_mot_kiem_nem_loi_cac_kiem_khac_van_chay(self, monkeypatch):
        def _no(*a, **k):
            raise KeyError("du lieu la")

        monkeypatch.setattr(gac_tong, "_kiem_hen_lich_chua_tai", _no)
        anh = _anh({"K1": _snap(ke_hoach=[_dong_da_dang(60)])})
        anh["may"]["dia"] = {"con_gb": 3.0}
        loai = [s["loai"] for s in gac_tong.kiem_su_co(anh)]
        assert "kiem_hong" in loai and "khong_video_moi" in loai and "dia_day" in loai


class TestLuotSap:
    def test_luot_sap_tra_1_ghi_so_va_nhip(self, tmp_path, monkeypatch):
        from core import ben_bi

        goc = str(tmp_path)

        def _no(g, thu):
            raise RuntimeError("chup hong")

        monkeypatch.setattr(gac_tong, "_mot_luot", _no)
        monkeypatch.setattr(ben_bi, "ghi_loi_vong", lambda g, ten, loi, **k: so.append((g, ten)) or 1)
        so = []
        assert gac_tong._main(["--mot-luot"], goc=goc) == 1
        assert so == [(goc, "gac_tong")]
        assert ben_bi.doc_nhip(goc, "gac_tong")["buoc"].startswith("sap:")

    def test_luot_tron_ghi_nhip_xong(self, tmp_path, monkeypatch):
        from core import ben_bi

        goc = str(tmp_path)
        monkeypatch.setattr(gac_tong, "_mot_luot", lambda g, thu: 0)
        assert gac_tong._main(["--mot-luot"], goc=goc) == 0
        nhip = ben_bi.doc_nhip(goc, "gac_tong")
        assert nhip["buoc"] == "xong" and nhip.get("luc_xong")

    def test_thu_khong_ghi_nhip(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        monkeypatch.setattr(gac_tong, "_mot_luot", lambda g, thu: 0)
        assert gac_tong._main(["--mot-luot", "--thu"], goc=goc) == 0
        assert not os.path.exists(os.path.join(goc, "workspace"))


def test_qua_nhieu_tu_chay_tru_luot_cho_clip():
    """06/10/2026: 7 tiến trình, 3 đang chờ kho clip, 4 làn → không báo; 8 làm thật → báo."""
    from core import gac_tong as g
    may = {"so_tien_trinh_tu_chay": 7, "lan_api": 4, "so_cho_clip": 3, "tran_luot_tong": 7}
    assert g._kiem_qua_nhieu_tu_chay({"may": may}) == []
    assert g._kiem_qua_nhieu_tu_chay({"may": dict(may, so_cho_clip=0)}) == []      # 7 làm lại sau chờ clip: hợp lệ
    assert g._kiem_qua_nhieu_tu_chay({"may": {"so_tien_trinh_tu_chay": 7, "lan_api": 4}})  # ảnh cũ: luật làn
    assert g._kiem_qua_nhieu_tu_chay({"may": dict(may, so_tien_trinh_tu_chay=9, so_cho_clip=5)})  # > trần tổng 8
    assert g._kiem_qua_nhieu_tu_chay({"may": {"so_tien_trinh_tu_chay": 5, "lan_api": 4}}) == []   # ảnh cũ thiếu khoá
