"""Ngôn ngữ TÀI KHOẢN theo quốc gia của ngách (04/10/2026): đích đọc từ `kenh.yaml`
(`ngon_ngu_tai_khoan_dich`), triển khai dần (không khai = giữ `vi`), mẫu ngày/giờ/nút của Studio tiếng Nhật.
Không Chrome, không mạng."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))          # vm/cdp_studio.py phải thắng cdp_studio.py ở gốc (cùng quy ước test_vm_may_dang_dom)
if str(GOC) not in sys.path:
    sys.path.append(str(GOC))

import may_dang_dom as mdd  # noqa: E402
import thiet_lap_kenh_dom as t  # noqa: E402


def _kenh(tmp_path, ten, yaml_text, ho_so=None):
    d = tmp_path / "CHANNEL" / ten
    d.mkdir(parents=True)
    (d / "kenh.yaml").write_text(yaml_text, encoding="utf-8")
    if ho_so is not None:
        (d / "thiet-lap").mkdir()
        (d / "thiet-lap" / "ho-so.json").write_text(json.dumps(ho_so), encoding="utf-8")
    return str(tmp_path)


def test_khong_khai_giu_tieng_viet(tmp_path):
    goc = _kenh(tmp_path, "A", 'ma: "A"\nngon_ngu: "ja"\n')
    assert t.ngon_ngu_dich_kenh("A", goc) == ("vi", "")


def test_khai_ja_thanh_dich_nhat(tmp_path):
    goc = _kenh(tmp_path, "B", 'ngon_ngu_tai_khoan_dich: "ja"\n', {"quoc_gia": "JP"})
    assert t.ngon_ngu_dich_kenh("B", goc) == ("ja", "")
    goc2 = _kenh(tmp_path / "x", "B", 'ngon_ngu_tai_khoan_dich: "ja"\n')      # chưa có hồ sơ → không có quốc gia để lệch
    assert t.ngon_ngu_dich_kenh("B", goc2)[0] == "ja"


def test_lech_quoc_gia_ho_so_roi_ve_vi(tmp_path):
    goc = _kenh(tmp_path, "C", 'ngon_ngu_tai_khoan_dich: "ja"\n', {"quoc_gia": "VN"})
    ma, ly = t.ngon_ngu_dich_kenh("C", goc)
    assert ma == "vi" and "LỆCH" in ly


def test_ma_la_khong_co_trong_bang():
    ma, ly = t.chon_ngon_ngu_dich("xx")
    assert ma == "vi" and "chưa có trong bảng" in ly
    assert t.chon_ngon_ngu_dich("ja-JP", "JP") == ("ja", "")
    assert t.chon_ngon_ngu_dich("") == ("vi", "")


def test_nhan_ra_studio_tieng_nhat():
    assert t.la_ngon_ngu_dich("ja", "ja-JP", "")
    assert t.la_ngon_ngu_dich("ja", "", "チャンネル ダッシュボード コンテンツ アナリティクス")
    assert not t.la_ngon_ngu_dich("ja", "vi-VN", "Trang tổng quan của kênh Nội dung")
    assert not t.la_ngon_ngu_dich("ja", "ko-KR", "콘텐츠")
    assert not t.la_ngon_ngu_dich("ja", "", "コンテンツ")                        # 1 chữ không đủ
    assert t.la_ngon_ngu_dich("vi", "vi-VN", "") and not t.la_ngon_ngu_dich("vi", "ja-JP", "コンテンツ")
    assert t.la_tieng_viet("vi-VN", "")                                          # hàm cũ còn nguyên


def test_nhan_muc_ngon_ngu_trong_danh_sach():
    import re
    for ma, nhan in (("ja", " 日本語"), ("ja", "日本語 (Tiếng Nhật)"), ("ja", "Tiếng Nhật"), ("vi", " Tiếng Việt"), ("en", "English (United States)")):
        assert re.search(t.NGON_NGU_DICH[ma]["re_chon"], nhan, re.I), (ma, nhan)
    assert not re.search(t.NGON_NGU_DICH["ja"]["re_chon"], "Tiếng Việt", re.I)


def test_khac_biet_noi_ten_ngon_ngu_dich():
    hs = {"ten": "x", "handle": "@x"}
    kh = t.khac_biet(hs, {"ngon_ngu_vi": False, "ngon_ngu_dich_ten": "日本語"}, {"muc": {}}, {})
    assert kh["ngon_ngu"]["khac"] is True and kh["ngon_ngu"]["mong"] == "日本語" and "日本語" in kh["ngon_ngu"]["hien"]
    kh = t.khac_biet(hs, {"ngon_ngu_vi": True}, {"muc": {}}, {})                 # không có tên đích → như cũ
    assert kh["ngon_ngu"]["khac"] is False and kh["ngon_ngu"]["mong"] == "tiếng Việt"


def test_mau_ngay_nhat():
    d = date(2026, 10, 5)
    mau = mdd.mau_ngay_thu({"dinh_dang_ngay": ["{d} thg {m}, {Y}", "{dd}/{mm}/{Y}"]})
    assert "{Y}/{m}/{d}" in mau and "{Y}年{m}月{d}日" in mau
    assert mdd.dinh_dang_ngay(d, "{Y}/{mm}/{dd}") == "2026/10/05"
    assert mdd.dinh_dang_ngay(d, "{Y}/{m}/{d}") == "2026/10/5"
    assert mdd.phan_tich_ngay("2026/10/05")[0] == d and mdd.phan_tich_ngay("2026年10月5日")[0] == d
    assert mdd.phan_tich_gio("5:00") == (5, 0)
    assert mdd.phan_tich_ngay_gio("2026/10/05 5:00").hour == 5


def test_bo_chon_co_mau_ngay_nhat_va_ten_ngon_ngu_nhieu_ten():
    bo = json.loads((VM / "studio-selectors.json").read_text(encoding="utf-8"))
    assert "{Y}/{m}/{d}" in bo["dinh_dang_ngay"] and "{Y}/{mm}/{dd}" in bo["dinh_dang_ngay"]
    assert "日本語" in bo["ngon_ngu_video"]["ja"]
    assert "予約済み" in bo["chu_trang_thai"]["da_len_lich"]
    assert mdd.phan_tich_trang_thai("予約済み 2026/10/05 5:00")[0] == "da_len_lich"


def test_nut_chinh_sua_da_ngon_ngu():
    assert mdd.nut_la_chinh_sua("Chỉnh sửa") and mdd.nut_la_chinh_sua("編集") and mdd.nut_la_chinh_sua("Edit")
    assert not mdd.nut_la_chinh_sua("追加") and not mdd.nut_la_chinh_sua(None)
