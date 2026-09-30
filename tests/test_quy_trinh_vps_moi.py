from __future__ import annotations

import datetime as dt
import os

import pytest

pytest.importorskip("PyQt5.QtWidgets")


class _App:
    def __init__(self, goc):
        self.base_dir = str(goc)
        self.loi = []
        self.thong_bao = []

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except BaseException as loi:
            return on_err(loi) if on_err else None
        return on_ok(ket) if on_ok else ket

    def show_error(self, loi):
        self.loi.append(str(loi))

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _kenh(goc, ma="K1"):
    thu = goc / "CHANNEL" / ma
    thu.mkdir(parents=True)
    (thu / "kenh.yaml").write_text("ten: K1\n", encoding="utf-8")
    return thu


def test_nghien_cuu_bao_ro_ba_nguon_va_do_moi(tmp_path):
    from core import nghien_cuu_vps as nc

    thu = _kenh(tmp_path) / "nghien-cuu"
    thu.mkdir()
    (thu / "doi-thu-ban-dua.txt").write_text("https://youtube.com/@a\n", encoding="utf-8")
    (thu / "trang-chu.csv").write_text("Kênh,Tiêu đề\nA,Một\n", encoding="utf-8")
    chi_so = tmp_path / "CHANNEL" / "K1" / "chi-so"
    chi_so.mkdir()
    (chi_so / "bang-tom-tat.csv").write_text("Video,View\nx,10\n", encoding="utf-8")

    ket = nc.tom_tat_nguon(str(tmp_path), "K1", dt.datetime.now())
    assert [x["ten"] for x in ket["nguon"]] == [
        "Danh sách ban đầu", "Studio của kênh", "Trang chủ kênh"]
    assert all(x["trang_thai"] in ("Đã nhận", "Mới") for x in ket["nguon"])
    assert ket["chat_luong"] == "Đủ nguồn, dữ liệu mới"


def test_san_xuat_hien_content_da_chot_va_luu_prompt(tmp_path, qapp, monkeypatch):
    from core import chon_content as cc
    from ui_qt import trang_san_xuat_vps as sx

    _kenh(tmp_path)
    uv = cc.UngVien(cc.LUONG_V7, "AAAAAAAAAAA", "Content mới", "Nguồn A",
                    "https://youtu.be/AAAAAAAAAAA", 86, "Nên làm", "đủ năm cửa")
    cc.chot(str(tmp_path), "K1", uv)
    da_luu = []
    monkeypatch.setattr(sx, "doc_prompts", lambda *_a: [("1.md", "Kịch bản", "prompt cũ")])
    monkeypatch.setattr(sx, "ghi_prompts", lambda _g, _k, nd: da_luu.append(nd) or list(nd))
    monkeypatch.setattr(sx.tt, "anh_chup", lambda *_a, **_k: {
        "kenh": [{"ma": "K1", "bay_gio": {"chu": "Chờ lịch"}, "video": {}, "luot": {}}]})

    trang = sx.TrangSanXuatVps(_App(tmp_path))
    trang._da_nap = True
    trang._nap()
    assert "Content mới" in trang._content.text()
    assert trang._ds.count() == 1
    trang._noi_dung.setPlainText("prompt mới")
    trang._luu()
    assert da_luu == [{"1.md": "prompt mới"}]
    trang.close()


def test_dang_cham_soc_phan_biet_cho_duyet_va_dang_tay(tmp_path, qapp):
    from ui_qt.trang_dang_cham_soc_vps import TrangDangChamSocVps

    trang = TrangDangChamSocVps(_App(tmp_path))
    trang._ve({"kenh": [
        {"ma": "K1", "bay_gio": {"chu": "Đã làm xong"}, "video": {},
         "ke_hoach": [{"loai": "cho_duyet", "ma_goi": "g1", "tieu_de": "Video A"}],
         "bay_ngay": {}, "phien": {}},
        {"ma": "K2", "bay_gio": {"chu": "Đã hẹn"}, "video": {},
         "ke_hoach": [{"loai": "sap_dang", "ma_goi": "g2", "tieu_de": "Video B",
                        "ngay": "27/09/2026", "gio": "20:00"}],
         "bay_ngay": {}, "phien": {"xong_hom_nay": True}},
    ]})
    assert trang._bang.item(0, 3).text() == "Chờ duyệt lịch"
    assert trang._nut_hanh_dong.text() == "Duyệt giờ đăng"
    trang._bang.selectRow(1)
    qapp.processEvents()
    assert trang._bang.item(1, 2).text() == "27/09/2026 20:00"
    assert trang._nut_hanh_dong.text() == "Đã đăng thủ công"
    trang.close()
