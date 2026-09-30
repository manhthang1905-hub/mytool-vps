"""Nút "Bài học sản xuất" trong tab Công thức V7 (`ui_qt/trang_cong_thuc_v7.py`) — Bước 3
của `workspace/THIET-KE-BAI-HOC-SAN-XUAT.md`.

Chạy nền qua `app.run_bg` (đúng nếp sẵn có của tab), xong tự mở tệp `.md` — bài kiểm chặn
`QDesktopServices.openUrl` để không thật sự bật trình soạn thảo trên máy chạy test, đúng
khuôn `tests/test_tai_khoan_lay_khoa.py`.

Dùng lại `_AppGia`/`dung_kenh` của `test_trang_quyet_dinh_v7.py` (kênh giả hình dạng
TL4-T7 ngày 17/09) cho ca "chưa đủ dữ liệu" (kênh đó không có CTR/AVD, chỉ có hiển thị) —
và tự dựng thêm một kênh nhỏ CÓ đủ CTR/AVD cho ca "có bài học thật". Không mạng, không Qt
thật (offscreen).
"""

from __future__ import annotations

import io
import json
import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from test_trang_quyet_dinh_v7 import KENH, _AppGia, trang  # noqa: E402,F401 — tests/ nằm sẵn trong sys.path


def _ghi_video_du_ctr(goc, kenh, ma, moc_gio, tieu_de, ngay_dang, ctr, avd_pct, thoi_luong_giay):
    from core.kenh import duong_kenh  # noqa: PLC0415

    thu_muc = os.path.join(duong_kenh(goc, kenh), "chi-so", ma, "{0}h".format(moc_gio))
    os.makedirs(thu_muc, exist_ok=True)
    with io.open(os.path.join(thu_muc, "_thong-tin.json"), "w", encoding="utf-8") as tep:
        json.dump({"tieu_de": tieu_de, "thoi_luong": thoi_luong_giay, "gio": moc_gio,
                   "ngay_dang": ngay_dang}, tep, ensure_ascii=False)
    with io.open(os.path.join(thu_muc, "tong-quan.json"), "w", encoding="utf-8") as tep:
        json.dump({"video_id": ma, "gio_sau_dang": moc_gio, "thoi_luong_giay": thoi_luong_giay,
                   "impressions": 5000, "ctr": ctr, "avd_pct": avd_pct}, tep, ensure_ascii=False)


def test_nut_bai_hoc_co_mat_canh_cau_hinh_va_bao_cao(trang):
    t, _app, _goc = trang
    assert hasattr(t, "_nut_bai_hoc")
    assert t._nut_bai_hoc.text() == "Bài học sản xuất"
    assert t._nut_bai_hoc.isEnabled()


def test_chua_chon_kenh_thi_nhac_khong_chay_nen(trang):
    t, app, _goc = trang
    t._chon_kenh.setEditText("")
    t._bai_hoc_san_xuat()
    assert app.thong_bao and app.thong_bao[-1][0] == "Chưa chọn kênh"


def test_bam_nut_chua_du_du_lieu_van_mo_file_khong_loi(trang, monkeypatch):
    """Kênh giả của `dung_kenh` chỉ có hiển thị (impressions), không có CTR/AVD — đúng ca
    "chưa đủ dữ liệu". Nút vẫn phải chạy xong, mở tệp, không rơi vào `on_err`."""
    from PyQt5.QtGui import QDesktopServices

    t, app, goc = trang
    da_mo = []
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: da_mo.append(url.toLocalFile())))

    t._bai_hoc_san_xuat()

    assert not [x for x in app.thong_bao if x[0] == "loi"], app.thong_bao
    assert not t._dang_chay_bai_hoc
    assert t._nut_bai_hoc.isEnabled()
    assert da_mo and da_mo[0].endswith("BAI-HOC-SAN-XUAT.md")
    assert os.path.isfile(da_mo[0])
    assert "Đã cập nhật bài học sản xuất" in t._trang_thai.text()
    noi_dung = io.open(da_mo[0], encoding="utf-8").read()
    assert "chưa đủ dữ liệu" in noi_dung.lower()


def test_bam_nut_co_du_lieu_ra_dung_ba_muc(trang, monkeypatch):
    """Dựng thêm 6 video CÓ CTR/AVD, cùng một cụm chủ đề thật (từ khoá "一人" → mot-minh),
    để nút thật sự có bài học `cao` mà in ra."""
    from PyQt5.QtGui import QDesktopServices

    t, app, goc = trang
    ngay = "2026-08-20T09:00:00.000Z"  # đủ xa so BAY_GIO ngầm định (bây giờ thật) → đủ 7 ngày
    for i in range(6):
        _ghi_video_du_ctr(goc, KENH, "MDVID{0:06d}".format(i), 336,
                          "ずっと一人でいる人にしかわからないこと その{0}".format(i),
                          ngay, ctr=4.0 + i * 0.5, avd_pct=30.0 + i, thoi_luong_giay=800)

    da_mo = []
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: da_mo.append(url.toLocalFile())))
    t._bai_hoc_san_xuat()

    assert not [x for x in app.thong_bao if x[0] == "loi"], app.thong_bao
    assert da_mo, "phải mở file khi xong"
    noi_dung = io.open(da_mo[0], encoding="utf-8").read()
    assert "## 1. LUẬT ĐANG DÙNG" in noi_dung
    assert "mot-minh" in noi_dung and "CAO" in noi_dung


def test_loi_khi_dang_chay_thi_khong_bam_lai_duoc(trang):
    t, _app, _goc = trang
    t._dang_chay_bai_hoc = True
    t._nut_bai_hoc.setEnabled(False)
    t._bai_hoc_san_xuat()  # phải im lặng bỏ qua, không chạy chồng
    assert t._dang_chay_bai_hoc is True
