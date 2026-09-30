"""Việc 5b (29/09/2026) — lớp kiểm TRÙNG Ý bằng LLM (`core/kiem_trung_y.py`),
bổ sung cho so chữ của `core/trung_tieu_de.py`, và cách `core/tu_chay.py`
`_chon_nguon` dùng nó NGAY TRƯỚC KHI CHỐT nguồn (`_chon_khong_trung_y`).
"""

from __future__ import annotations

import json

import pytest

from core import kiem_trung_y as kty
from core import tu_chay as tc


@pytest.fixture(autouse=True)
def _goc_tam(tmp_path, monkeypatch):
    """Các bài gọi `_chon_khong_trung_y(".", …)`: từ 30/09/2026 lớp ấy GHI phán quyết TỆ vào
    `CHANNEL/<k>/nghien-cuu/bien-tap/nho-cham.json` — chạy trong thư mục tạm, không đụng kho thật."""
    monkeypatch.chdir(tmp_path)


def _goi_gia(ket_qua):
    """Đồ giả `goi_chat`: bắt lại lời nhắc gửi đi, trả JSON `ket_qua`."""
    lan = []

    def goi(loi_nhac, **kw):
        lan.append(loi_nhac)
        return json.dumps(ket_qua, ensure_ascii=False)
    goi.lan = lan
    return goi


def _khong_duoc_goi(*_a, **_k):
    raise AssertionError("không được gọi goi_chat ở ca này")


# ═══════════════════════════════════════════════════════════════════════════
# core.kiem_trung_y — đơn vị
# ═══════════════════════════════════════════════════════════════════════════


class TestKiemTrungYDonVi:
    def test_goi_chat_none_bo_qua(self):
        trung, voi, ly_do = kty.kiem_trung_y(None, "ứng viên", [("a", "x")])
        assert trung is False
        assert ly_do

    def test_ung_vien_rong_bo_qua_khong_goi(self):
        trung, voi, ly_do = kty.kiem_trung_y(_khong_duoc_goi, "   ", [("a", "x")])
        assert trung is False

    def test_da_lam_rong_bo_qua_khong_goi(self):
        trung, voi, ly_do = kty.kiem_trung_y(_khong_duoc_goi, "ứng viên", [])
        assert trung is False

    def test_trung_y_doc_duoc_json_va_gui_dung_ung_vien(self):
        """Ca thật (28→29/09/2026, xem docstring `core/kiem_trung_y.py`):
        SL94HyyuLXs 「IQが低い人の頭の中で起きていること」 và TL3-T7-0001
        「考えすぎる人の頭の中はこんな世界」 — so CHỮ chỉ 0,485 (dưới ngưỡng 0,80 của
        `trung_tieu_de`), nhưng LLM phải đọc ra CÙNG chủ đề."""
        goi = _goi_gia({"trung": True, "voi": "考えすぎる人の頭の中はこんな世界",
                        "ly_do": "cùng chủ đề IQ thấp, chỉ đảo trật tự từ"})
        da_lam = [("考えすぎる人の頭の中はこんな世界", "TL3-T7-0001 (tiêu đề đã đặt)")]
        trung, voi, ly_do = kty.kiem_trung_y(
            goi, "IQが低い人の頭の中で起きていること", da_lam)
        assert trung is True
        assert voi == "考えすぎる人の頭の中はこんな世界"
        assert ly_do
        assert "IQが低い人の頭の中で起きていること" in goi.lan[0]
        assert "考えすぎる人の頭の中はこんな世界" in goi.lan[0]

    def test_khong_trung_y(self):
        goi = _goi_gia({"trung": False, "voi": "", "ly_do": "khác chủ đề, khác góc nhìn"})
        trung, voi, ly_do = kty.kiem_trung_y(goi, "ứng viên mới hoàn toàn",
                                             [("một đề tài khác hẳn", "x")])
        assert trung is False
        assert voi == ""

    def test_loi_mang_khong_nem_ra_ngoai(self):
        def goi_hong(*_a, **_k):
            raise RuntimeError("mạng hỏng")
        trung, voi, ly_do = kty.kiem_trung_y(goi_hong, "ứng viên", [("a", "x")])
        assert trung is False
        assert ly_do

    def test_json_sai_dang_khong_nem(self):
        goi = _goi_gia(["không", "phải", "dict"])
        trung, voi, ly_do = kty.kiem_trung_y(goi, "ứng viên", [("a", "x")])
        assert trung is False

    def test_boc_duoc_json_boc_trong_markdown(self):
        def goi(loi_nhac, **kw):
            return "```json\n" + json.dumps({"trung": True, "voi": "x", "ly_do": "y"}) + "\n```"
        trung, voi, ly_do = kty.kiem_trung_y(goi, "ứng viên", [("x", "z")])
        assert trung is True

    def test_chi_gui_toi_da_so_ung_vien_gan_nhat(self):
        import re

        da_lam = [("đề tài số {0}".format(i), "nguồn {0}".format(i)) for i in range(30)]
        da_lam.append(("ứng viên đây luôn", "khớp gần tuyệt đối"))
        goi = _goi_gia({"trung": False, "voi": "", "ly_do": ""})
        kty.kiem_trung_y(goi, "ứng viên đây luôn", da_lam, so_ung_vien=15)
        # Ứng viên giống hệt (điểm chữ 1.0) phải lọt vào danh sách gửi.
        assert "ứng viên đây luôn" in goi.lan[0]
        # Không gửi hết 31 dòng — bảng gửi đã lọc còn tối đa 15 (mỗi dòng
        # "<số>. <tiêu đề>").
        so_dong = len(re.findall(r"(?m)^\d+\. ", goi.lan[0]))
        assert 0 < so_dong <= 15


# ═══════════════════════════════════════════════════════════════════════════
# core.tu_chay._chon_khong_trung_y — nối lớp kiểm vào chọn nguồn
# ═══════════════════════════════════════════════════════════════════════════


def _ds_gia(*ma_list):
    return [{"ma": ma, "tieu_de": "tiêu đề {0}".format(ma),
            "link": "https://youtu.be/" + ma, "kenh": "Z", "nguon": "mot_nut"}
           for ma in ma_list]


class TestChonKhongTrungY:
    def test_ung_vien_dau_trung_y_thi_thu_ung_vien_ke(self):
        ds = _ds_gia("AAAAAAAAAAA", "BBBBBBBBBBB")
        so_lan = {"n": 0}

        def goi(loi_nhac, **kw):
            so_lan["n"] += 1
            trung = so_lan["n"] == 1  # ứng viên đầu trùng, ứng viên kế thì không
            return json.dumps({"trung": trung, "voi": "x", "ly_do": "vì lý do"})

        log = []
        ket = tc._chon_khong_trung_y(
            ".", "K1", ds, log.append,
            da_lam_tieu_de=[("tiêu đề cũ", "nguồn cũ")], goi_chat=goi)
        assert ket["ma"] == "BBBBBBBBBBB"
        assert so_lan["n"] == 2
        assert any("TRÙNG Ý" in dong for dong in log)
        # nguồn trùng ý được nhớ TỆ — lượt sau biên tập viên/lớp kiểm khỏi xét lại
        from core import bien_tap_content as bt
        nho = bt.doc_nho_cham(".", "K1")
        assert nho["AAAAAAAAAAA"]["hang"] == bt.TE and "BBBBBBBBBBB" not in nho

    def test_khong_trung_thi_dung_ngay_mot_luot_goi(self):
        ds = _ds_gia("AAAAAAAAAAA", "BBBBBBBBBBB")
        so_lan = {"n": 0}

        def goi(loi_nhac, **kw):
            so_lan["n"] += 1
            return json.dumps({"trung": False, "voi": "", "ly_do": ""})

        ket = tc._chon_khong_trung_y(
            ".", "K1", ds, lambda *_a: None,
            da_lam_tieu_de=[("tiêu đề cũ", "nguồn cũ")], goi_chat=goi)
        assert ket["ma"] == "AAAAAAAAAAA"
        assert so_lan["n"] == 1

    def test_toi_da_3_luot_goi_roi_lay_ung_vien_con_lai_khong_kiem_them(self):
        ds = _ds_gia("AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC", "DDDDDDDDDDD")
        so_lan = {"n": 0}

        def goi(loi_nhac, **kw):
            so_lan["n"] += 1
            return json.dumps({"trung": True, "voi": "x", "ly_do": "trùng"})

        ket = tc._chon_khong_trung_y(
            ".", "K1", ds, lambda *_a: None,
            da_lam_tieu_de=[("tiêu đề cũ", "nguồn cũ")], goi_chat=goi)
        assert so_lan["n"] == tc.SO_LAN_KIEM_TRUNG_Y_TOI_DA == 3
        assert ket is not None
        assert ket["ma"] == "DDDDDDDDDDD"  # ứng viên thứ 4, chưa từng bị kiểm

    def test_het_ung_vien_giua_chung_thi_tra_none_khong_vuot_tran_goi(self):
        ds = _ds_gia("AAAAAAAAAAA", "BBBBBBBBBBB")
        so_lan = {"n": 0}

        def goi(loi_nhac, **kw):
            so_lan["n"] += 1
            return json.dumps({"trung": True, "voi": "x", "ly_do": "trùng"})

        ket = tc._chon_khong_trung_y(
            ".", "K1", ds, lambda *_a: None,
            da_lam_tieu_de=[("tiêu đề cũ", "nguồn cũ")], goi_chat=goi)
        assert ket is None
        assert so_lan["n"] == 2  # chỉ 2 ứng viên — không gọi thêm khi đã hết


class TestChonNguonNoiKiemTrungY:
    """`_chon_nguon` — cổng bật/tắt lớp Việc 5b, không đụng gì khi tắt."""

    def test_kiem_trung_y_bat_false_thi_khong_goi_ai(self):
        ds_fn = lambda goc, kenh: {  # noqa: E731 — đồ giả `mot_nut.doc_danh_sach`
            "moi": [{"link": "https://youtu.be/EEEEEEEEEEE", "tieu_de": "đề tài mới",
                    "kenh": "Z", "view": 0, "vuot": 0.0, "tang": 0.0, "ngay": "",
                    "tuyen": "", "chu_de": "", "but": 0.0, "diem": 0}],
            "vuot": [], "but": []}
        ket = tc._chon_nguon(
            ".", "K1", False, set(), cham_v7=lambda *a, **k: None,
            doc_danh_sach=ds_fn, log=lambda *_a: None,
            da_lam_tieu_de=[("đề tài cũ", "nguồn cũ")],
            goi_chat=_khong_duoc_goi, kiem_trung_y_bat=False)
        assert ket["ma"] == "EEEEEEEEEEE"

    def test_goi_chat_none_thi_khong_goi_ai(self):
        """Đúng ca `che_do="thu"`: nơi gọi CHỈ đưa `goi_chat=None` — lớp Việc 5b
        phải bỏ qua hoàn toàn dù `kiem_trung_y_bat=True`."""
        ds_fn = lambda goc, kenh: {  # noqa: E731
            "moi": [{"link": "https://youtu.be/FFFFFFFFFFF", "tieu_de": "đề tài mới",
                    "kenh": "Z", "view": 0, "vuot": 0.0, "tang": 0.0, "ngay": "",
                    "tuyen": "", "chu_de": "", "but": 0.0, "diem": 0}],
            "vuot": [], "but": []}
        ket = tc._chon_nguon(
            ".", "K1", False, set(), cham_v7=lambda *a, **k: None,
            doc_danh_sach=ds_fn, log=lambda *_a: None,
            da_lam_tieu_de=[("đề tài cũ", "nguồn cũ")],
            goi_chat=None, kiem_trung_y_bat=True)
        assert ket["ma"] == "FFFFFFFFFFF"

    def test_khong_da_lam_tieu_de_thi_khong_goi_ai(self):
        ds_fn = lambda goc, kenh: {  # noqa: E731
            "moi": [{"link": "https://youtu.be/GGGGGGGGGGG", "tieu_de": "đề tài mới",
                    "kenh": "Z", "view": 0, "vuot": 0.0, "tang": 0.0, "ngay": "",
                    "tuyen": "", "chu_de": "", "but": 0.0, "diem": 0}],
            "vuot": [], "but": []}
        ket = tc._chon_nguon(
            ".", "K1", False, set(), cham_v7=lambda *a, **k: None,
            doc_danh_sach=ds_fn, log=lambda *_a: None,
            da_lam_tieu_de=None, goi_chat=_khong_duoc_goi, kiem_trung_y_bat=True)
        assert ket["ma"] == "GGGGGGGGGGG"
