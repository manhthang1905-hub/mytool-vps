"""Kiểm thương hiệu kênh (14/10/2026): HÀM THUẦN của `vm/thiet_lap_kenh_dom.py` cho `--kiem-thuong-hieu` /
`--dat-hinh-mo` — đọc ô hình mờ, quyết «thiếu hình mờ», đếm danh sách phát, đọc trailer/video nổi bật, so trang Hồ
sơ trước–sau, khung giờ tròn. Không Chrome, không mạng."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
for _p in (str(GOC), str(VM)):
    if _p not in sys.path:
        sys.path.append(_p)

import thiet_lap_kenh_dom as t  # noqa: E402


def _radio(chon: str):
    ds = [("end-of-video-radio-button", "END", "Cuối video"), ("custom-start-time-radio-button", "START", "Thời gian bắt đầu tùy chỉnh"),
          ("entire-video-radio-button", "ENTIRE", "Toàn bộ video")]
    return [{"id": i, "name": n, "chu": c, "chon": n == chon} for i, n, c in ds]


# ── ô hình mờ ──
def test_hinh_mo_co_va_toan_bo_video():
    hm = t.doc_hinh_mo({"thay_o": True, "nut_xoa": True, "nut_thay": True, "radio": _radio("ENTIRE")})
    assert hm == {"co": True, "thoi_gian": "toan_bo", "nhan": "Toàn bộ video"}


def test_hinh_mo_cuoi_video_doc_theo_name_khi_thieu_id():
    r = [dict(x, id="") for x in _radio("END")]
    assert t.doc_hinh_mo({"thay_o": True, "nut_xoa": True, "radio": r})["thoi_gian"] == "cuoi"


def test_hinh_mo_thieu_khi_chi_co_nut_tai_len():
    hm = t.doc_hinh_mo({"thay_o": True, "nut_xoa": False, "nut_tai_len": True, "radio": []})
    assert hm["co"] is False and hm["thoi_gian"] is None
    assert t.can_dat_hinh_mo(hm) == (True, "thiếu hình mờ")


def test_khong_doc_duoc_o_thi_khong_dat():
    for du in (None, {}, {"thay_o": True}, {"thay_o": True, "nut_xoa": False, "nut_tai_len": False}):
        hm = t.doc_hinh_mo(du)
        assert hm["co"] is None
        ok, ly = t.can_dat_hinh_mo(hm)
        assert ok is False and "không đọc được" in ly


def test_da_co_hinh_mo_thi_khong_lam_gi():
    hm = t.doc_hinh_mo({"thay_o": True, "nut_xoa": True, "radio": _radio("START")})
    assert hm["thoi_gian"] == "tuy_chinh"
    assert t.can_dat_hinh_mo(hm)[0] is False


def test_hai_lua_chon_cung_chon_la_khong_ro():
    r = _radio("END")
    r[2]["chon"] = True
    assert t.doc_hinh_mo({"thay_o": True, "nut_xoa": True, "radio": r})["thoi_gian"] == ""


# ── danh sách phát ──
def test_dem_ds_phat_theo_chu_phan_trang():
    assert t.dem_ds_phat({"hang": 30, "ten": ["a"] * 30, "chan": "Số hàng mỗi trang: 30 1–30 / 45"}) == 45
    assert t.dem_ds_phat({"hang": 3, "ten": ["a", "b", "c"], "chan": "1 – 3 trên tổng số 3"}) == 3
    assert t.dem_ds_phat({"hang": 2, "ten": [], "chan": "1～2/2 件"}) == 2


def test_dem_ds_phat_khong_phan_trang_thi_dem_hang():
    assert t.dem_ds_phat({"hang": 5, "ten": ["a"] * 5, "chan": ""}) == 5


def test_dem_ds_phat_trong_va_khong_doc_duoc():
    assert t.dem_ds_phat({"hang": 0, "ten": [], "chan": "", "trong": True}) == 0
    assert t.dem_ds_phat({"hang": 0, "ten": [], "chan": ""}) is None
    assert t.dem_ds_phat(None) is None


# ── thẻ Trang chủ: trailer / video nổi bật ──
TRANG_CHU_VI = """Tiêu điểm video
Thêm video vào đầu trang chủ của kênh.
Đoạn giới thiệu kênh cho người chưa đăng ký
Giới thiệu sơ lược về kênh cho người xem.
Thêm
Video nổi bật cho người đăng ký quay lại
Làm nổi bật một video để người đăng ký xem.
Video ABC
Thay đổi
Xóa
Mục"""


def test_tieu_diem_trailer_thieu_noi_bat_co():
    td = t.doc_tieu_diem(TRANG_CHU_VI)
    assert td["trailer"]["co"] is False
    assert td["noi_bat"]["co"] is True


def test_tieu_diem_tieng_anh_va_khong_thay():
    en = "Channel trailer for people who haven't subscribed\nAdd\nFeatured video for returning subscribers\nAdd"
    td = t.doc_tieu_diem(en)
    assert td["trailer"]["co"] is False and td["noi_bat"]["co"] is False
    assert t.doc_tieu_diem("") == {"trailer": {"co": None, "dong": []}, "noi_bat": {"co": None, "dong": []}}


#: Studio 14/10 (đo thật): thẻ Trang chủ có công tắc + «Bố cục», không còn khối «Tiêu điểm video».
TRANG_CHU_MOI = """Thẻ Trang chủ
Hiện thẻ Trang chủ của kênh để nêu bật và giới thiệu nội dung cho khán giả của bạn
Bố cục
Thêm phần kênh
Dành cho bạn
Video (22)
Danh sách phát đã tạo (2)"""


def test_tieu_diem_bo_cuc_moi_khong_co_muc_la_khong_co():
    assert {k: v["co"] for k, v in t.doc_tieu_diem(TRANG_CHU_MOI, trang_da_dung=True).items()} == {"trailer": False, "noi_bat": False}
    assert t.doc_tieu_diem(TRANG_CHU_MOI)["trailer"]["co"] is None        # chưa chắc trang đã dựng → không kết luận


def test_tieu_diem_bo_cuc_moi_co_muc_trailer():
    td = t.doc_tieu_diem(TRANG_CHU_MOI + "\nĐoạn giới thiệu kênh\nVideo XYZ", trang_da_dung=True)
    assert td["trailer"]["co"] is True and td["noi_bat"]["co"] is False


# ── trang Hồ sơ trước–sau ──
def _hs(**kw):
    d = {"ten": "霞の心理学", "handle": "@kenh-a", "mo_ta": "dòng 1\n\ndòng 2", "logo": {"co": True, "src": ["https://x/a"]},
         "banner": {"co": True, "src": ["https://x/b"]}, "hinh_mo": {"co": False}}
    d.update(kw)
    return d


def test_lech_ho_so_chi_hinh_mo_doi_la_khong_lech():
    assert t.lech_ho_so(_hs(), _hs(hinh_mo={"co": True}, mo_ta="dòng 1\ndòng 2")) == []


def test_lech_ho_so_bat_ten_mo_ta_logo():
    assert t.lech_ho_so(_hs(), _hs(ten="khác", mo_ta="x", logo={"co": True, "src": ["https://x/c"]})) == ["ten", "mo_ta", "logo"]
    assert t.lech_ho_so(_hs(), None) == ["không đọc được trang Hồ sơ"]


# ── giờ tròn ──
def _luc(gio: int, phut: int, giay: int = 0) -> float:
    return time.mktime((2026, 10, 14, gio, phut, giay, 0, 0, -1))


def test_khung_gio_tron():
    assert t.khung_gio_tron(_luc(18, 10), 8) == ""
    assert t.khung_gio_tron(_luc(18, 46), 8) == ""
    assert t.khung_gio_tron(_luc(18, 48), 8)          # 18:48 + 8 phút chạm :55
    assert t.khung_gio_tron(_luc(18, 57), 0)
    assert t.khung_gio_tron(_luc(19, 3), 0)
    assert t.khung_gio_tron(_luc(19, 5), 0) == ""


# ── sổ kết quả ──
def test_ghi_thuong_hieu_giu_lich_su(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "THU_MUC_SO", str(tmp_path))
    t.ghi_thuong_hieu("K", {"kenh": "K", "luc": "1", "che_do": "kiem", "ket_qua": "xong", "hinh_mo": {"co": False}})
    t.ghi_thuong_hieu("K", {"kenh": "K", "luc": "2", "che_do": "kiem+dat", "ket_qua": "xong", "hinh_mo": {"co": False},
                            "dat_hinh_mo": {"ket": "dat"}})
    du = json.loads((tmp_path / "K.thuong-hieu.json").read_text(encoding="utf-8"))
    assert du["luc"] == "2" and du["dat_hinh_mo"]["ket"] == "dat"
    assert [x["luc"] for x in du["lich_su"]] == ["1"]
