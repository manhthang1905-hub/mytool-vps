"""Trang ĐIỀU KHIỂN sau khi dọn: cột chỉ còn TÌNH TRẠNG, núm vặn vào hộp ⚙.

Chủ dự án xem bản trước trên máy thật (1416×995), 22/09/2026: *"những gì đang
hiển thị ở tab điều khiển tao xem rất khó quản lý - rất khó hiểu nó đang như
nào. tao nghĩ mỗi kênh có 1 mục cài đặt để cài giờ đăng rồi all các thứ để
kiểm soát kênh đó - còn nội dung ở ngoài thì cần thể hiện. nói chung nó là
auto nên phải tối giản phải đơn giản dễ dùng"*.

Sáu thứ bài này canh — sáu chỗ mà một lần "gọn lại cho đẹp" sau này dễ làm
hỏng nhất:

1. **Cột không còn ô tích, ô ngân sách, ô nhật ký.** Ba thứ ấy làm cột rối;
   chúng phải sống trong hộp ⚙ Cài đặt và hộp nhật ký, không trong cột.
2. **Bốn cột không tràn mép** ở cả 1024, 1280 lẫn 1416 — ba bề rộng thật.
3. **Hộp ⚙ Cài đặt mở được cho TỪNG kênh** và có đủ bảy mục kiểm soát.
4. **Công tắc trong hộp ghi ĐÚNG đường cũ** — `kenh.yaml` cho hai cái về sản
   xuất, `may-ao.json` cho hai cái về máy ảo. Dọn giao diện không được đổi
   chỗ lưu, nếu không máy ảo và vòng tự chạy đọc hụt mất cài đặt.
5. **Câu tình trạng đổi theo trạng thái, và LUÔN kèm chữ** — không bao giờ
   chỉ có màu.
6. **Đúng một nút chạy hiện ra**: "Chạy lại" khi lượt hỏng, còn lại "Chạy
   ngay"; cạnh nó là "⚙ Cài đặt".

Không mạng, không tiền: dùng lại máy giả của `test_giao_dien_vps`.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import (  # noqa: E402
    QCheckBox, QPlainTextEdit, QPushButton, QSpinBox, QTimeEdit,
)

from test_giao_dien_vps import BON_KENH, _dung_goc, _mo  # noqa: E402


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def bon_cot(tmp_path, monkeypatch, qapp):
    goc = _dung_goc(tmp_path, monkeypatch)
    t, app = _mo(goc)
    yield t, app, goc
    t.close()
    t.deleteLater()


# ── 1. Cột CHỈ CÒN TÌNH TRẠNG ────────────────────────────────────────────────


def test_cot_khong_con_o_tich_o_tien_o_nhat_ky(bon_cot, qapp):
    """Ba thứ chủ dự án chê làm cột rối, không cái nào còn nằm TRONG cột."""
    t, _app, _goc = bon_cot
    t.show()
    qapp.processEvents()
    assert t._cot, "chưa dựng cột nào"
    for ma, cot in t._cot.items():
        assert cot.findChildren(QCheckBox) == [], "ô tích còn trong cột " + ma
        assert cot.findChildren(QSpinBox) == [], "ô số còn trong cột " + ma
        assert cot.findChildren(QTimeEdit) == [], "ô giờ còn trong cột " + ma
        assert cot.findChildren(QPlainTextEdit) == [], \
            "ô nhật ký còn trong cột " + ma


def test_cot_hien_dung_hai_nut(bon_cot, qapp):
    """Người xem luôn thấy ĐÚNG hai nút: một nút chạy và "⚙ Cài đặt"."""
    t, _app, _goc = bon_cot
    t.show()
    qapp.processEvents()
    for ma, cot in t._cot.items():
        hien = [n.text().strip() for n in cot.findChildren(QPushButton)
                if n.isVisibleTo(cot)]
        assert len(hien) == 2, "cột {0} hiện {1} nút: {2}".format(ma, len(hien), hien)
        assert "⚙ Cài đặt" in hien, hien
        assert ("Chạy ngay" in hien) != ("Chạy lại" in hien), hien


def test_cot_van_du_tam_khau_va_giau_phut_cua_khau_da_xong(bon_cot, qapp):
    """Tám khâu còn đủ trong tooltip nhưng mặt chính chỉ hiện một thanh tổng."""
    from core.auto import MA_KHAU

    t, _app, _goc = bon_cot
    cot = t._cot["TL1-T7"]
    assert list(cot._khau) == list(MA_KHAU)
    cot.nap({"ma": "TL1-T7", "bay_gio": {"chu": "Chưa chạy hôm nay", "muc": "nghi"},
             "luot": {"khau": [
                 {"ma": "kich-ban", "ten": "Viết kịch bản", "ten_ngan": "Kịch bản",
                  "trang_thai": "xong", "giay": 310, "loi": ""}]}}, {})
    assert cot._khau_phu["kich-ban"].text() == "", "phút của khâu đã xong còn trên cột"
    assert "5 phút" in cot._khau["kich-ban"].toolTip()
    assert cot._thanh_khau.value() == 1
    assert cot._nhan_tien_do.text() == "Đã xong 1/8 khâu"
    assert all(not o.isVisibleTo(cot) for o in cot._khau.values())


def test_khau_dang_chay_hien_tien_do(bon_cot, qapp):
    """Khâu ĐANG chạy được hiện tiến độ — lấy từ dấu `[N/M]` của nhật ký."""
    t, _app, _goc = bon_cot
    cot = t._cot["TL1-T7"]
    cot.nap({"ma": "TL1-T7",
             "bay_gio": {"chu": "Đang làm video · khâu Ảnh", "muc": "dang"},
             "nhat_ky": ["[116/141] Đang tạo ảnh cảnh 116"],
             "luot": {"khau": [{"ma": "anh", "ten": "Tạo ảnh từng cảnh",
                                "ten_ngan": "Ảnh", "trang_thai": "dang",
                                "giay": 0, "loi": ""}]}}, {})
    assert cot._khau_phu["anh"].text() == "116/141"
    assert "Ảnh 116/141" in cot._nhan_tien_do.text()


# ── 2. Bốn cột không tràn mép ────────────────────────────────────────────────


@pytest.mark.parametrize("rong", (1024, 1280, 1416))
def test_bon_cot_khong_tran_mep_sau_khi_don(tmp_path, monkeypatch, qapp, rong):
    """Trừ thanh bên 240 — trang chỉ được phần còn lại của cửa sổ."""
    goc = _dung_goc(tmp_path, monkeypatch)
    t, _app = _mo(goc)
    try:
        t.resize(rong - 240, 955)
        t.show()
        qapp.processEvents()
        assert t._cot, "chưa dựng cột nào"
        tran = [ma for ma, c in t._cot.items() if c.x() + c.width() > t.width()]
        assert not tran, "cột thò ra ngoài mép ở {0}px: {1}".format(rong, tran)
        # Và không cột nào bị cắt cụt hai cái nút.
        for ma, c in t._cot.items():
            assert c.height() >= c.sizeHint().height(), ma
    finally:
        t.close()
        t.deleteLater()


# ── 3. Hộp ⚙ Cài đặt: mở được cho TỪNG kênh, đủ bảy mục ──────────────────────

#: Bảy thứ kiểm soát của một kênh. Danh sách này là hợp đồng.
BAY_MUC = ("o_gio_dang", "o_chu_ky_dang", "o_san_xuat_truoc",
           "o_phut_phien", "o_ngan_sach")


def test_hop_cai_dat_mo_duoc_cho_tung_kenh(bon_cot, qapp):
    t, _app, _goc = bon_cot
    for ma in BON_KENH:
        t._mo_cai_dat(ma)
        qapp.processEvents()
        hop = t._hop_cai[ma]
        assert hop.isVisible(), "hộp cài đặt của {0} không mở".format(ma)
        assert ma in hop.windowTitle()
        hop.close()


def test_hop_cai_dat_co_du_bay_muc(bon_cot, qapp):
    """Giờ đăng · phút mở phiên · bốn công tắc · tiền mỗi ngày — và dòng chỉ đường."""
    t, _app, _goc = bon_cot
    hop = t._hop_cai["TL1-T7"]
    for ten in BAY_MUC:
        assert getattr(hop, ten, None) is not None, "thiếu " + ten
    assert sorted(hop.o_cong_tac) == sorted(
        ["tu_chay", "tu_dang", "tu_don", "tu_tra_loi_cmt"])

    chu = " ".join(nh.text() for nh in hop.findChildren(type(hop.nhan_canh_ns)))
    assert "Giờ đăng" in chu
    assert "Mở phiên trước giờ đăng" in chu
    assert "Tiền mỗi ngày" in chu
    # Dòng chỉ đường — đừng nhân bản mấy ô ấy vào đây.
    assert "Quản lý kênh" in chu and "Giọng đọc" in chu

    # Nhãn "Tự đăng" phải nói rõ hậu quả: bật là video tự lên sóng.
    tip = hop.o_cong_tac["tu_dang"].toolTip()
    assert "tự lên sóng" in tip and "không ai duyệt" in tip, tip


def test_hop_cai_dat_canh_bao_0d(tmp_path, monkeypatch, qapp):
    """0₫ KHÔNG phải "bỏ trần" — nó là "không sản xuất gì cả"."""
    from core.trung_tam import ghi_cai_kenh

    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    ghi_cai_kenh(goc, "TL1-T7", ngan_sach_ngay=0)
    t, _app = _mo(goc)
    try:
        chu = t._hop_cai["TL1-T7"].nhan_canh_ns.text()
        assert "KHÔNG" in chu and "sản xuất" in chu, chu
    finally:
        t.close()
        t.deleteLater()


# ── 4. Công tắc trong hộp ghi ĐÚNG đường cũ ──────────────────────────────────


def test_cong_tac_trong_hop_ghi_dung_hai_noi(bon_cot, qapp):
    """Dọn giao diện KHÔNG được đổi chỗ lưu: sản xuất → `kenh.yaml`, máy ảo →
    `may-ao.json`. Đổi chỗ là vòng tự chạy hoặc máy ảo đọc hụt cài đặt."""
    from core import vm_cai_dat
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    hop = t._hop_cai["TL1-T7"]

    hop.o_cong_tac["tu_don"].setChecked(True)
    qapp.processEvents()
    assert doc_kenh(goc, "TL1-T7").tu_don is True

    hop.o_cong_tac["tu_chay"].setChecked(False)
    qapp.processEvents()
    assert doc_kenh(goc, "TL1-T7").tu_chay is False

    hop.o_cong_tac["tu_dang"].setChecked(True)
    qapp.processEvents()
    assert vm_cai_dat.doc(goc, "TL1-T7")["tu_dang"] is True

    hop.o_cong_tac["tu_tra_loi_cmt"].setChecked(True)
    qapp.processEvents()
    assert vm_cai_dat.doc(goc, "TL1-T7")["tu_tra_loi_cmt"] is True


def test_gio_dang_sua_duoc_trong_hop(bon_cot, qapp):
    """Thứ chủ dự án nhắc đích danh — và nó phải rơi đúng khoá `gio_dang`
    trong `kenh.yaml`, thứ `core/tu_chay.py` đọc để hẹn giờ lên sóng."""
    from PyQt5.QtCore import QTime
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    hop = t._hop_cai["TL2-T7"]
    assert hop.o_gio_dang.time().toString("HH:mm") == "20:00", "chưa đọc giờ đang có"
    hop.o_gio_dang.setTime(QTime(21, 30))
    hop._hen_gio.stop()
    t._doi_gio_dang("TL2-T7", hop.o_gio_dang.time().toString("HH:mm"))
    qapp.processEvents()
    assert doc_kenh(goc, "TL2-T7").gio_dang == "21:30"


def test_nhip_dang_sua_duoc_trong_hop(bon_cot, qapp):
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    hop = t._hop_cai["TL2-T7"]
    hop.o_chu_ky_dang.setValue(3)
    hop.o_san_xuat_truoc.setValue(30)
    hop._hen_nhip.stop()
    t._doi_nhip_dang("TL2-T7", 3, 30)
    qapp.processEvents()
    kenh = doc_kenh(goc, "TL2-T7")
    assert kenh.chu_ky_dang_ngay == 3
    assert kenh.san_xuat_truoc_gio == 30


def test_phut_mo_phien_la_cua_rieng_tung_kenh(bon_cot, qapp):
    """Trước đây ô này ở dải trên và ghi cho MỌI kênh một lượt."""
    from core import vm_cai_dat

    t, _app, goc = bon_cot
    hop = t._hop_cai["TL3-T7"]
    hop.o_phut_phien.setValue(45)
    hop._hen_phien.stop()
    t._doi_phut_phien("TL3-T7", hop.o_phut_phien.value())
    qapp.processEvents()
    assert int(vm_cai_dat.doc(goc, "TL3-T7")["phien_truoc_phut"]) == 45
    # Và kênh bên cạnh KHÔNG bị ghi theo.
    assert int(vm_cai_dat.doc(goc, "TL1-T7")["phien_truoc_phut"]) == 60


def test_tien_moi_ngay_sua_duoc_trong_hop(bon_cot, qapp):
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    hop = t._hop_cai["TL2-T7"]
    hop.o_ngan_sach.setValue(333_000)
    hop._hen.stop()
    t._doi_ngan_sach("TL2-T7", hop.o_ngan_sach.value())
    qapp.processEvents()
    assert int(doc_kenh(goc, "TL2-T7").ngan_sach_ngay) == 333_000


def test_giu_toi_da_luot_sua_duoc_trong_hop(bon_cot, qapp):
    """Trần SỐ LƯỢT giữ trên đĩa phải chỉnh được NGAY TRÊN GIAO DIỆN.

    Chủ dự án, 21/09/2026: *"tao muốn nó đơn giản hiệu quả mà có thể quản lý và
    thiết lập all ở gui để chủ động"*. Ô này phải rơi đúng khoá
    `giu_toi_da_luot` trong `kenh.yaml` — thứ `core/don_dep.ung_vien_qua_so_luot`
    đọc — và KHÔNG ghi lây sang kênh bên cạnh.
    """
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    hop = t._hop_cai["TL2-T7"]
    hop.o_giu_luot.setValue(4)
    hop._hen_giu.stop()
    t._doi_giu_luot("TL2-T7", hop.o_giu_luot.value())
    qapp.processEvents()
    assert int(doc_kenh(goc, "TL2-T7").giu_toi_da_luot) == 4
    assert int(doc_kenh(goc, "TL1-T7").giu_toi_da_luot) == 0

    # 0 phải ghi được — đó là cách TẮT luật, không phải "bỏ trống".
    hop.o_giu_luot.setValue(0)
    hop._hen_giu.stop()
    t._doi_giu_luot("TL2-T7", hop.o_giu_luot.value())
    qapp.processEvents()
    assert int(doc_kenh(goc, "TL2-T7").giu_toi_da_luot) == 0


def test_giu_toi_da_luot_noi_that_khi_tu_don_dang_tat(bon_cot, qapp):
    """Đặt một con số mà "Tự dọn" tắt thì không có gì xảy ra — phải nói ra, đừng
    để người ta ngồi đợi (`MyTool/CLAUDE.md`, "Nói thật khi hỏng")."""
    t, _app, _goc = bon_cot
    hop = t._hop_cai["TL1-T7"]

    hop.nap({"tu_don": False, "giu_toi_da_luot": 3}, {})
    assert "chỉ có tác dụng khi" in hop.nhan_giu_luot.text()
    assert hop.o_giu_luot.value() == 3

    hop.nap({"tu_don": True, "giu_toi_da_luot": 3}, {})
    assert "chỉ có tác dụng khi" not in hop.nhan_giu_luot.text()


# ── 5. Câu tình trạng ────────────────────────────────────────────────────────

#: `(ảnh chụp kênh, câu phải hiện ra)` — năm trạng thái người ta gặp thật.
CA_TINH_TRANG = (
    ({"bay_gio": {"chu": "Đang làm video · khâu Ảnh", "muc": "dang"},
      "nhat_ky": ["[116/141] cảnh"],
      "luot": {"khau": [{"ma": "anh", "ten_ngan": "Ảnh", "trang_thai": "dang"}]}},
     "Đang tạo ảnh — 116/141 cảnh"),
    ({"bay_gio": {"chu": "Chờ duyệt", "muc": "cho"}}, "Xong, chờ bạn hẹn giờ đăng"),
    ({"bay_gio": {"chu": "Chờ đăng 20:00", "muc": "cho"}},
     "Đã hẹn đăng 20:00 hôm nay"),
    ({"bay_gio": {"chu": "Lỗi: khâu Ảnh — máy chủ ảnh bận", "muc": "loi"},
      "luot": {"khau": [{"ma": "anh", "ten_ngan": "Ảnh", "trang_thai": "hong",
                         "loi": "máy chủ ảnh bận"}]}},
     "Dừng khi tạo ảnh — máy chủ ảnh bận"),
    ({"bay_gio": {"chu": "Chưa chạy hôm nay", "muc": "nghi"}}, "Hôm nay chưa chạy"),
    ({"bay_gio": {"chu": "Chỉ đăng, không sản xuất", "muc": "nghi"}},
     "Chỉ đăng, không tự làm video"),
)


@pytest.mark.parametrize("k,cho_doi", CA_TINH_TRANG)
def test_cau_tinh_trang_noi_bang_loi_thuong(k, cho_doi):
    from ui_qt.trang_dieu_khien import cau_tinh_trang

    assert cau_tinh_trang(k) == cho_doi


def test_cau_tinh_trang_bo_vet_loi_ky_thuat():
    """Câu này lên MÀN HÌNH, nên nó đi qua `gon_dong_nhat_ky` như mọi dòng khác."""
    from ui_qt.trang_dieu_khien import cau_tinh_trang

    cau = cau_tinh_trang({
        "bay_gio": {"chu": "Lỗi: khâu Kịch bản — không lấy được lời thoại",
                    "muc": "loi"},
        "luot": {"khau": [{"ma": "kich-ban", "ten_ngan": "Kịch bản",
                           "trang_thai": "hong",
                           "loi": "không lấy được lời thoại "
                                  "(FileNotFoundError: ctranslate2.dll)"}]}})
    assert "FileNotFoundError" not in cau and "ctranslate2" not in cau, cau
    assert "không lấy được lời thoại" in cau, cau


def test_tien_do_nhat_ky_khong_nham_ngay_thang():
    from ui_qt.trang_dieu_khien import tien_do_nhat_ky

    assert tien_do_nhat_ky(["[116/141] Đang tạo ảnh"]) == "116/141"
    assert tien_do_nhat_ky(["Đăng ngày 22/09/2026", "xong"]) == ""
    assert tien_do_nhat_ky([]) == ""


def test_mau_cot_luon_di_kem_chu(bon_cot, qapp):
    """Màu KHÔNG bao giờ đi một mình: mỗi mức có câu riêng và một dấu riêng."""
    from ui_qt.trang_dieu_khien import HONG, LUU_Y, THUONG, TOT, muc_mau_cot

    t, _app, _goc = bon_cot
    cot = t._cot["TL1-T7"]
    da_thay = set()
    for k, cho_doi in (
            ({"bay_gio": {"chu": "Đang chọn video", "muc": "dang"}}, TOT),
            ({"bay_gio": {"chu": "Chưa đặt trần tiền", "muc": "canh_bao"}}, LUU_Y),
            ({"bay_gio": {"chu": "Lỗi: máy chủ bận", "muc": "loi"}}, HONG),
            ({"bay_gio": {"chu": "Chưa chạy hôm nay", "muc": "nghi"}}, THUONG)):
        cot.nap(dict(k, ma="TL1-T7"), {})
        assert muc_mau_cot(k["bay_gio"]["muc"]) == cho_doi
        assert cot._muc_mau == cho_doi
        assert cot.cau.strip(), "câu tình trạng trống ở mức " + cho_doi
        assert cot.cau in cot._nhan_tt.text(), cot._nhan_tt.text()
        da_thay.add(cot.cau)
    assert len(da_thay) == 4, "bốn trạng thái mà câu không đổi: {0}".format(da_thay)


# ── 6. Nhật ký: bấm câu tình trạng thì mở ra ─────────────────────────────────


def test_bam_cau_tinh_trang_mo_nhat_ky_cua_dung_kenh_do(bon_cot, qapp):
    t, _app, _goc = bon_cot
    cot = t._cot["TL2-T7"]
    cot._nhan_tt.bam.emit()
    qapp.processEvents()
    hop = t._hop_nhat_ky["TL2-T7"]
    assert hop.isVisible()
    assert "TL2-T7" in hop.windowTitle()
    hop.close()


def test_nhat_ky_van_di_qua_gon_dong_nhat_ky(bon_cot, qapp):
    """Vết lỗi Python không được lên màn hình; nguyên văn ở tooltip."""
    t, _app, _goc = bon_cot
    hop = t._hop_nhat_ky["TL1-T7"]
    tho = ("Dừng ở Viết kịch bản: không lấy được lời thoại "
           "(FileNotFoundError: Could not find module 'ctranslate2.dll')")
    hop.nap({"ma": "TL1-T7", "bay_gio": {"chu": "Chưa chạy hôm nay", "muc": "nghi"},
             "nhat_ky": [tho]})
    chu = hop.o_nhat_ky.toPlainText()
    assert "FileNotFoundError" not in chu and "ctranslate2" not in chu, chu
    assert "không lấy được lời thoại" in chu
    assert "ctranslate2" in hop.o_nhat_ky.toolTip(), "mất nguyên văn để truy lỗi"


# ── 7. Dòng "N việc cần xem" nhóm theo kênh ──────────────────────────────────


def test_viec_can_xem_nhom_theo_kenh_va_noi_lam_gi_tiep(bon_cot, qapp):
    from ui_qt.trang_dieu_khien import HONG, LUU_Y

    t, _app, _goc = bon_cot
    t._anh = {"o_dia": {"con_gb": 5.0}, "la_vps": True, "kenh": [
        {"ma": "TL1-T7", "tu_chay": True,
         "bay_gio": {"muc": "canh_bao", "chu": "Chưa đặt trần tiền"}},
        {"ma": "TL3-T7", "tu_chay": True,
         "bay_gio": {"muc": "loi", "chu": "Lỗi: khâu Ảnh — máy chủ bận"},
         "luot": {"khau": [{"ma": "anh", "ten_ngan": "Ảnh", "trang_thai": "hong",
                            "loi": "máy chủ bận"}]}},
    ]}
    t._may = {}
    nhom = t.viec_theo_nhom()
    ten_nhom = [ten for ten, _v in nhom]
    assert ten_nhom == [t.NHOM_MAY, "TL3-T7", "TL1-T7"], ten_nhom
    # Mỗi việc nói rõ LÀM GÌ TIẾP THEO.
    for _ten, muc_viec in nhom:
        for _m, chu, goi in muc_viec:
            assert chu.strip() and goi.strip().startswith("→"), (chu, goi)

    # Bản phẳng vẫn xếp việc nặng lên trước — hợp đồng cũ của `viec_can_xem`.
    assert [m for m, _c in t.viec_can_xem()] == [HONG, HONG, LUU_Y]

    t._mo_viec = True
    t._ve_viec()
    qapp.processEvents()
    assert "3 việc cần xem" in t._nut_viec.text()
    assert t._hop_viec.isVisibleTo(t)
