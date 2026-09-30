"""Công suất 24h từ nhật ký khe (`core/cong_suat.py`, Bước D 29/09/2026). tmp_path, không mạng."""

from __future__ import annotations

import json
import os

from core import bang_dieu_khien, cong_suat


def _nk(goc, *muc):
    d = os.path.join(goc, "workspace", "khe")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "nhat-ky.jsonl"), "a", encoding="utf-8") as tep:
        for m in muc:
            tep.write(json.dumps(m) + "\n")


def _luot(goc, kenh, luot, ket_thuc):
    d = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump({"ma_kenh": kenh, "ma_luot": luot,
                   "khau": {"dung": {"trang_thai": "xong", "bat_dau": ket_thuc - 1800,
                                     "ket_thuc": ket_thuc}}}, tep)


def test_ghep_cap_duoc_nha_va_cat_cua_so(tmp_path):
    goc = str(tmp_path)
    T = 1_000_000.0
    _nk(goc,
        {"viec_nk": "duoc", "lop": "nang", "viec": "dung", "pid": 1, "luc": T, "phut_cho": 3},
        {"viec_nk": "nha", "lop": "nang", "viec": "dung", "pid": 1, "luc": T + 1800},
        {"viec_nk": "duoc", "lop": "api", "viec": "san_xuat", "pid": 2, "luc": T - 3600},
        {"viec_nk": "nha", "lop": "api", "viec": "san_xuat", "pid": 2, "luc": T + 3600},
        {"viec_nk": "duoc", "lop": "nang", "viec": "tai_len", "pid": 3, "luc": T + 3000},
        {"viec_nk": "vuot_han", "lop": "nang", "viec": "dung", "pid": 1, "luc": T + 100})
    nk = cong_suat.doc_nhat_ky_khe(goc, T, T + 3600)
    assert nk["phut"]["nang"]["dung"] == 30.0
    assert nk["phut"]["nang"]["tai_len"] == 10.0  # còn đang giữ → tính tới den_luc
    assert nk["phut"]["api"]["san_xuat"] == 60.0  # cắt phần trước cửa sổ
    assert nk["vuot_han"] == 1 and nk["cho_trung_vi_phut"] == 1.5  # trung vị (3, 0)


def test_cong_suat_hien_tai_va_de_xuat(tmp_path):
    goc = str(tmp_path)
    T = 2_000_000.0
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump({"lan_api": 2}, tep)
    # 2 video trong 24h, mỗi video 60' khe nặng + 180' làn API
    for i in range(2):
        b = T - 20 * 3600 + i * 5 * 3600
        _nk(goc, {"viec_nk": "duoc", "lop": "nang", "viec": "dung", "pid": 10 + i, "luc": b},
            {"viec_nk": "nha", "lop": "nang", "viec": "dung", "pid": 10 + i, "luc": b + 3600},
            {"viec_nk": "duoc", "lop": "api", "viec": "san_xuat", "pid": 20 + i, "luc": b},
            {"viec_nk": "nha", "lop": "api", "viec": "san_xuat", "pid": 20 + i, "luc": b + 3 * 3600})
        _luot(goc, "K1", "000{0}".format(i + 1), b + 3 * 3600)
        os.utime(os.path.join(goc, "PROJECTS", "AUTO", "K1", "000{0}".format(i + 1),
                              "trang-thai.json"), (T, T))
    cs = cong_suat.cong_suat_hien_tai(goc, bay_gio=T)
    assert cs["video_ban_giao"] == 2
    assert cs["phut_nang_moi_video"] == 60.0 and cs["phut_api_moi_video"] == 180.0
    assert cs["tran_video_ngay_khe_nang"] == round(1152 / 60.0, 1)
    assert cs["tran_video_ngay_lan_api"] == 16.0  # 2 làn × 1440 / 180
    assert cs["nut_that"] == "làn API"
    assert cs["con_du_video_ngay"] == 14.0 and cs["co_the_them_kenh"] == 7
    assert "thêm 7 kênh" in cs["de_xuat"]
    assert "khe nặng" in cong_suat.cau_mot_dong(cs)


def test_dong_may_them_truong_cong_suat(tmp_path):
    goc = str(tmp_path)
    cong_suat.ghi_hien_tai(goc, {"phan_tram_khe_nang": 12.5, "lan_api": 2,
                                 "lan_api_trung_binh_dang_dung": 1.1, "video_ban_giao": 3,
                                 "con_du_video_ngay": 5.0, "de_xuat": "x"})
    dm = bang_dieu_khien.dong_may(goc, {"kenh": []})
    assert dm["cong_suat"]["phan_tram_khe_nang"] == 12.5
    assert "Công suất 24h" in dm["cong_suat"]["cau"]
    assert set(("vi", "o_dia", "may_nen", "lich")) <= set(dm)
