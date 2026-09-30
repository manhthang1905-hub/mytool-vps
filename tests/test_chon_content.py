from __future__ import annotations

import csv
import datetime as dt
import json
import os

from core import chon_content as cc
from core import doi_thu_kenh as so


KENH = "kenh-a"


def _ghi_so(goc):
    thu = so.thu_muc_nghien_cuu(str(goc), KENH)
    os.makedirs(thu, exist_ok=True)
    cot = so.cot_mac_dinh()
    o = {c: i for i, c in enumerate(cot)}

    def dong(ma, td, kenh, view, tang, ngay):
        r = [""] * len(cot)
        for ten, gt in ((so.COT_LINK, "https://youtu.be/" + ma), ("Tiêu đề video", td),
                        ("Kênh", kenh), ("View", str(view)), (so.COT_TANG, str(tang)),
                        ("Ngày đăng", ngay)):
            r[o[ten]] = gt
        return r

    hang = [
        dong("AAAAAAAAAAA", "Video đang nổ", "Đối thủ 1", 500000, 20000, "2026-08-01"),
        dong("BBBBBBBBBBB", "Video bình thường", "Đối thủ 1", 5000, 20, "2026-08-01"),
        dong("CCCCCCCCCCC", "Nguồn đã làm", "Đối thủ 2", 900000, 30000, "2026-07-01"),
    ]
    with open(os.path.join(thu, so.TEP_BANG), "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(cot)
        w.writerows(hang)
    with open(os.path.join(thu, "da-lam.txt"), "w", encoding="utf-8") as tep:
        tep.write("CCCCCCCCCCC | đã đăng\n")


def test_doi_thu_xep_diem_va_bo_nguon_da_lam(tmp_path):
    _ghi_so(tmp_path)
    ds = cc.ung_vien_doi_thu(str(tmp_path), KENH, hom_nay=dt.date(2026, 9, 25))
    assert [d.ma for d in ds] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert ds[0].diem > ds[1].diem
    assert "view/ngày" in ds[0].ly_do
    assert set(ds[0].thanh_phan) == {"Nhanh", "Lớn", "Bứt", "Vượt"}


def test_moi_kenh_chi_co_mot_lua_chon_va_chot_moi_thay_chot_cu(tmp_path):
    _ghi_so(tmp_path)
    a, b = cc.ung_vien_doi_thu(str(tmp_path), KENH)
    cc.chot(str(tmp_path), KENH, a, luc=dt.datetime(2026, 9, 25, 10, 30))
    cc.chot(str(tmp_path), KENH, b, luc=dt.datetime(2026, 9, 25, 11, 0))
    lua = cc.doc_lua_chon(str(tmp_path), KENH)
    assert lua and lua.ung_vien.ma == "BBBBBBBBBBB"
    assert lua.ngay_chot == "2026-09-25T11:00:00"
    duong = os.path.join(so.thu_muc_nghien_cuu(str(tmp_path), KENH), cc.TEP_LUA_CHON)
    with open(duong, encoding="utf-8") as tep:
        raw = json.load(tep)
    assert isinstance(raw, dict) and "ung_vien" in raw, "không được tích thành danh sách chờ"


def test_san_xuat_nhan_trang_thai_va_co_the_bo_chot(tmp_path):
    _ghi_so(tmp_path)
    a = cc.ung_vien_doi_thu(str(tmp_path), KENH)[0]
    cc.chot(str(tmp_path), KENH, a)
    assert cc.danh_dau_dang_san_xuat(str(tmp_path), KENH)
    assert cc.doc_lua_chon(str(tmp_path), KENH).trang_thai == "đang sản xuất"
    assert cc.bo_chot(str(tmp_path), KENH)
    assert cc.doc_lua_chon(str(tmp_path), KENH) is None


def test_ban_giao_chi_xoa_dung_lua_chon_da_dung(tmp_path):
    _ghi_so(tmp_path)
    a, b = cc.ung_vien_doi_thu(str(tmp_path), KENH)
    cc.chot(str(tmp_path), KENH, a)
    assert not cc.hoan_tat_lua_chon(str(tmp_path), KENH, b.ma)
    assert cc.doc_lua_chon(str(tmp_path), KENH).ung_vien.ma == a.ma
    assert cc.hoan_tat_lua_chon(str(tmp_path), KENH, a.ma)
    assert cc.doc_lua_chon(str(tmp_path), KENH) is None


def test_luong_sai_bi_tu_choi(tmp_path):
    try:
        cc.lay_ung_vien(str(tmp_path), KENH, "khong-co")
    except ValueError as loi:
        assert "không hợp lệ" in str(loi)
    else:
        raise AssertionError("phải từ chối luồng không tồn tại")
