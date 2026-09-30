"""Phần NHÌN của trang Trung tâm: bốn kênh cạnh nhau, màu báo, không mất nút.

Chủ dự án, 21/09/2026: *"làm lại tab Trung tâm cho đẹp / dễ dùng hơn"* — **giữ
nguyên dữ liệu và chức năng, viết lại phần nhìn**, với ba yêu cầu rõ: bố cục rõ
hơn, **4 kênh đặt cạnh nhau dễ so sánh**, **màu báo đỏ/vàng khi có sự cố**.

Ba thứ bài này canh, vì ba thứ ấy là chỗ một lần "làm cho đẹp" hay làm hỏng:

1. **Mất nút.** Vẽ lại một trang 1.775 dòng thì thứ dễ rơi nhất là cái nút
   không ai nhớ tới — và người dùng chỉ phát hiện ra vào đúng ngày họ cần nó.
   `test_khong_mat_nut_o_tick_nao` giữ một danh sách ĐẦY ĐỦ, viết tay.
2. **Tràn mép cửa sổ.** Đúng nếp của `tests/test_bo_cuc.py`: đo
   `minimumSizeHint().width()`, không phải `sizeHint()` — trang muốn rộng thì
   không sao, trang không chịu CO mới là trang có phần nằm ngoài mép phải.
   Bốn thẻ cạnh nhau là đúng chỗ dễ dính lỗi ấy nhất.
3. **Màu đi một mình.** Người dùng có thể không phân biệt được đỏ với vàng, nên
   mỗi chỗ đổi màu phải đổi cả CHỮ.

Không mạng, không tiền: dùng lại máy giả của `test_trung_tam.dung_may` và app
giả của `test_trang_trung_tam`.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QCheckBox, QPushButton  # noqa: E402

from test_trang_trung_tam import _AppGia, _GiamSatGia  # noqa: E402
from test_trung_tam import BAY_GIO, _ghi_json, _kenh  # noqa: E402

#: Cùng ngưỡng với `tests/test_bo_cuc.py` — bề rộng cửa sổ hẹp nhất tool cho phép.
TRAN_RONG = 760

#: Bốn kênh thật sắp có trên máy này: TL4-T7 đang chạy, ba kênh kia sắp thêm.
BON_KENH = ("TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7")


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _dung_goc(tmp_path, monkeypatch, cac_ma) -> str:
    """Máy giả có đúng `cac_ma` kênh, kênh nào cũng bật tự chạy."""
    from core import lich_tu_chay
    from core import trung_tam as tt

    goc = str(tmp_path)
    monkeypatch.setattr(tt, "la_vps", lambda _g: False)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    monkeypatch.setattr(lich_tu_chay, "trang_thai", lambda _g, **_k: {
        "da_dang_ky": True, "gio": "02:00:00", "lan_chay_cuoi": "", "ket_qua_cuoi": ""})
    goc_anh_chup = tt.anh_chup
    monkeypatch.setattr(tt, "anh_chup", lambda g, **kw: goc_anh_chup(g, bay_gio=BAY_GIO, **kw))
    for i, ma in enumerate(cac_ma):
        _kenh(goc, ma, "Kênh " + ma, tu_chay=True, ngan_sach_ngay=120_000,
              tep=str(i + 1), nhom="TL", gio_dang="20:00")
    _ghi_json(os.path.join(goc, "vm", "config.json"),
              {"tram": "", "kenh": "", "cac_kenh": [], "chrome_theo_kenh": {}})
    return goc


def _mo_trang(goc: str):
    from ui_qt.trang_trung_tam import TrangTrungTam

    app = _AppGia(goc)
    t = TrangTrungTam(app)
    t._dong_ho.stop()          # không để đồng hồ 30 giây đọc đĩa giữa bài kiểm
    return t, app


@pytest.fixture
def bon_kenh(tmp_path, monkeypatch, qapp):
    goc = _dung_goc(tmp_path, monkeypatch, BON_KENH)
    t, app = _mo_trang(goc)
    yield t, app, goc
    t.close()
    t.deleteLater()


@pytest.fixture
def mot_kenh(tmp_path, monkeypatch, qapp):
    """Hôm nay máy thật đúng là chỉ có MỘT kênh — bố cục phải tử tế cả ở đây."""
    goc = _dung_goc(tmp_path, monkeypatch, ("TL4-T7",))
    t, app = _mo_trang(goc)
    yield t, app, goc
    t.close()
    t.deleteLater()


# ── Bốn kênh cạnh nhau ───────────────────────────────────────────────────────


def test_bon_kenh_bon_the_dung_canh_nhau(bon_kenh, qapp):
    """Bốn kênh = bốn thẻ, và trên cửa sổ đủ rộng chúng nằm CÙNG MỘT HÀNG.

    Cùng hàng mới là "đặt cạnh nhau dễ so sánh": mắt quét ngang một lượt là
    xong, không phải cuộn.
    """
    t, _app, _goc = bon_kenh
    t.resize(1180, 900)
    t.show()
    qapp.processEvents()
    assert set(t._the_kenh) == set(BON_KENH), sorted(t._the_kenh)
    dinh = {the.y() for the in t._the_kenh.values()}
    assert len(dinh) == 1, "bốn thẻ không nằm cùng một hàng: {0}".format(sorted(dinh))
    # Và chúng thật sự xếp ngang, mỗi thẻ một chỗ khác nhau.
    assert len({the.x() for the in t._the_kenh.values()}) == 4


def test_mot_kenh_van_tu_te(mot_kenh, qapp):
    """Một kênh thì một thẻ — không có ô trống giả, không có bảng rỗng."""
    t, _app, _goc = mot_kenh
    t.resize(1180, 900)
    t.show()
    qapp.processEvents()
    assert list(t._the_kenh) == ["TL4-T7"]
    assert not t._nhan_trong.isVisibleTo(t), "có kênh thì không nhắc “chưa có kênh nào”"
    assert t._the_kenh["TL4-T7"].isVisibleTo(t)


@pytest.mark.parametrize("so_kenh", (1, 4))
def test_khong_tran_mep_cua_so(tmp_path, monkeypatch, qapp, so_kenh):
    """Nếp của `test_bo_cuc.py`: trang phải CO được xuống 760px.

    Bốn thẻ nằm trong `HangXuongDong` nên chúng tự xuống hàng; bề rộng tối
    thiểu của cả trang chỉ còn bằng MỘT thẻ.
    """
    goc = _dung_goc(tmp_path, monkeypatch, BON_KENH[:so_kenh])
    t, _app = _mo_trang(goc)
    try:
        t.resize(TRAN_RONG, 900)
        t.show()
        qapp.processEvents()
        rong = t.minimumSizeHint().width()
        assert rong <= TRAN_RONG, (
            "{0} kênh: trang cần {1}px, phần thừa bị đẩy ra ngoài mép phải"
            .format(so_kenh, rong))
        # Thẻ cũng không được thò ra khỏi mép phải của chính trang.
        for ma, the in t._the_kenh.items():
            assert the.x() + the.width() <= t.width() + 1, ma
    finally:
        t.close()
        t.deleteLater()


def test_hang_hai_the_khong_bi_cat_khi_cua_so_hep(tmp_path, monkeypatch, qapp):
    """Cửa sổ hẹp → thẻ xuống hàng → hàng dưới phải hiện ĐỦ, không cụt.

    Bọc trang trong vùng cuộn y như `ui_qt/app.py` làm: đó mới là chỗ thật
    trang sống. Không có bài này thì hai thẻ hàng dưới bị xén ngang bụng và
    trông y như giao diện hỏng.
    """
    from PyQt5.QtCore import Qt as _Qt
    from PyQt5.QtWidgets import QFrame, QScrollArea

    goc = _dung_goc(tmp_path, monkeypatch, BON_KENH)
    t, _app = _mo_trang(goc)
    cuon = QScrollArea()
    cuon.setWidget(t)
    cuon.setWidgetResizable(True)
    cuon.setFrameShape(QFrame.NoFrame)
    cuon.setHorizontalScrollBarPolicy(_Qt.ScrollBarAlwaysOff)
    try:
        cuon.resize(TRAN_RONG, 660)
        cuon.show()
        qapp.processEvents()
        qapp.processEvents()
        can = t._hop_the.heightForWidth(t._hop_the.width())
        assert t._hop_the.height() >= can, (
            "hàng thẻ cao {0}px nhưng chỉ được {1}px — hàng dưới bị cắt"
            .format(can, t._hop_the.height()))
        day_the = max(the.y() + the.height() for the in t._the_kenh.values())
        assert day_the <= t._hop_the.height(), "thẻ thò ra khỏi hàng"
    finally:
        cuon.close()
        t.close()
        cuon.deleteLater()


def test_the_bam_duoc_de_chon_kenh(bon_kenh, qapp):
    t, _app, _goc = bon_kenh
    t._chon_kenh("TL2-T7")
    qapp.processEvents()
    assert t._ma_chon == "TL2-T7"
    assert t._the_kenh["TL2-T7"]._chon, "thẻ đang chọn phải tự đánh dấu"
    assert not t._the_kenh["TL1-T7"]._chon, "chỉ MỘT thẻ được đánh dấu"


def test_doi_qua_bang_va_quay_lai(bon_kenh, qapp):
    """Bảng cũ không mất: bấm “Bảng” là nó hiện ra, đủ chín cột như trước."""
    from ui_qt.trang_trung_tam import COT_BANG

    t, _app, _goc = bon_kenh
    t.show()
    t._chon_kieu.set("Bảng")
    qapp.processEvents()
    assert t._bang_kenh.isVisibleTo(t) and not t._hop_the.isVisibleTo(t)
    assert t._bang_kenh.columnCount() == len(COT_BANG) == 9
    assert t._bang_kenh.rowCount() == 4
    assert [t._bang_kenh.horizontalHeaderItem(c).text() for c in range(9)] == list(COT_BANG)
    t._chon_kieu.set("Thẻ")
    qapp.processEvents()
    assert t._hop_the.isVisibleTo(t) and not t._bang_kenh.isVisibleTo(t)


# ── Màu báo: đỏ / vàng, và LUÔN kèm chữ ──────────────────────────────────────


def _anh_gia(muc_theo_kenh: dict, **khac) -> dict:
    """Ảnh chụp giả — chỉ đủ phần trang vẽ ra, không đụng đĩa."""
    chu = {"loi": "Lỗi: mạng chập", "canh_bao": "Dở ở khâu Clip", "dang": "Đang làm video"}
    kenh = [{"ma": ma, "ten": "Kênh " + ma, "tep": "1", "tu_chay": True,
             "bay_gio": {"chu": chu.get(muc, "Chưa chạy hôm nay"), "muc": muc,
                         "chi_tiet": "chi tiết " + ma},
             "video": {"tieu_de": ""}, "dang_luc": "", "bay_ngay": {}, "ypp": {},
             "tien": {"hom_nay": 0, "tran": 120_000}, "luot": {"khau": []},
             "ke_hoach": [], "nhat_ky": [], "phien": {}, "dang_chay": False}
            for ma, muc in muc_theo_kenh.items()]
    anh = {"luc": "2026-09-21T09:00:00", "la_vps": False, "kenh": kenh, "kenh_khac": [],
           "tien": {"hom_nay": 0, "thang": 0}, "o_dia": {"con_gb": 200.0}, "nhom": None}
    anh.update(khac)
    return anh


def test_the_doi_mau_theo_muc_va_luon_co_chu(bon_kenh, qapp):
    """Ba mức rõ ràng, và mức nào cũng nói thành lời."""
    from ui_qt.trang_trung_tam import HONG, LUU_Y, THUONG

    t, _app, _goc = bon_kenh
    t._anh = _anh_gia({"TL1-T7": "dang", "TL2-T7": "canh_bao", "TL3-T7": "loi",
                       "TL4-T7": "nghi"})
    t._ve_bang()
    qapp.processEvents()
    assert t._the_kenh["TL1-T7"]._muc == THUONG
    assert t._the_kenh["TL2-T7"]._muc == LUU_Y
    assert t._the_kenh["TL3-T7"]._muc == HONG
    assert t._the_kenh["TL4-T7"]._muc == THUONG
    # Màu KHÔNG đi một mình: câu trạng thái phải có chữ thật.
    for ma in ("TL2-T7", "TL3-T7"):
        chu = t._the_kenh[ma]._nhan_tt.text()
        assert chu.strip(" ⚠✕"), "thẻ {0} chỉ có màu, không có chữ".format(ma)
        assert t._the_kenh[ma]._nhan_tt.toolTip()


def test_ba_muc_ba_mau_khac_nhau():
    """Bình thường / đáng chú ý / hỏng phải là ba màu thật sự khác nhau."""
    from ui_qt.trang_trung_tam import HONG, LUU_Y, THUONG, _MAU_BAO

    mau = [_MAU_BAO[m] for m in (THUONG, LUU_Y, HONG)]
    assert len({m[0] for m in mau}) == 3, "màu chữ ba mức bị trùng"
    assert len({m[1] for m in mau}) == 3, "màu nền ba mức bị trùng"


def test_o_dia_thap_thi_do_va_noi_ro(bon_kenh, qapp):
    """Ổ đĩa là rủi ro to nhất của máy này (còn hơn chục GB) — phải nổi."""
    from ui_qt.trang_trung_tam import HONG, LUU_Y, THUONG

    t, _app, _goc = bon_kenh
    for con_gb, muc in ((9.0, HONG), (18.0, LUU_Y), (200.0, THUONG)):
        t._anh = _anh_gia({"TL1-T7": "nghi"}, o_dia={"con_gb": con_gb})
        t._ve_dia()
        t._ve_canh_bao()
        qapp.processEvents()
        assert "{0:.0f} GB".format(con_gb) in t._nhan_dia.text()
        viec = [c for m, c in t._viec_can_lam() if "Ổ đĩa" in c]
        if muc == THUONG:
            assert not viec
        else:
            assert viec and [m for m, c in t._viec_can_lam() if "Ổ đĩa" in c] == [muc]
            assert t._nhan_bao.isVisible() or t._nhan_bao.isVisibleTo(t)


def test_dai_canh_bao_goi_ten_tung_viec(bon_kenh, qapp):
    """Một dòng, nói rõ có mấy việc và là việc gì — không bắt ai tự đi tìm."""
    from ui_qt.trang_trung_tam import HONG

    t, app, _goc = bon_kenh
    app.giam_sat_vm = _GiamSatGia()
    t._may = {"may_dang": {"song": False}, "agent": {"song": True}}
    t._anh = _anh_gia({"TL1-T7": "loi", "TL2-T7": "canh_bao", "TL3-T7": "nghi"},
                      o_dia={"con_gb": 8.0}, la_vps=True)
    t._ve_canh_bao()
    qapp.processEvents()
    chu = t._nhan_bao.text()
    assert t._nhan_bao.isVisibleTo(t)
    assert "Ổ đĩa" in chu and "TL1-T7" in chu and "TL2-T7" in chu
    assert "Máy đăng" in chu, "máy con chết phải được gọi tên"
    assert "TL3-T7" not in chu, "kênh không có chuyện gì thì đừng kể"
    # Nặng nhất là đỏ, và số việc nói bằng chữ số chứ không bắt ai tự đếm.
    assert HONG in [m for m, _c in t._viec_can_lam()]
    assert "4 việc" in chu, chu


def test_khong_co_su_co_thi_dai_canh_bao_bien_mat(bon_kenh, qapp):
    t, _app, _goc = bon_kenh
    t._may = {}
    t._anh = _anh_gia({"TL1-T7": "ok", "TL2-T7": "dang"})
    t._ve_canh_bao()
    qapp.processEvents()
    assert not t._nhan_bao.isVisibleTo(t), "mọi thứ ổn thì đừng chiếm một dòng để khoe"


def test_lich_tat_thi_bao_vang(bon_kenh, qapp):
    from ui_qt.trang_trung_tam import LUU_Y

    t, _app, _goc = bon_kenh
    t._lich = {"da_dang_ky": False}
    t._anh = _anh_gia({"TL1-T7": "nghi"})
    t._ve_lich()
    t._ve_canh_bao()
    qapp.processEvents()
    assert "TẮT" in t._nut_lich.text()
    assert (LUU_Y, "Lịch hằng ngày đang tắt") in t._viec_can_lam()


def test_vi_thap_thi_bao(bon_kenh, qapp):
    from core.money import MICRO_PER_VND
    from ui_qt.trang_trung_tam import HONG, LUU_Y, THUONG

    t, app, _goc = bon_kenh
    app.client = object()
    for vnd, muc in ((50_000, HONG), (200_000, LUU_Y), (900_000, THUONG)):
        app.last_wallet_micro = vnd * MICRO_PER_VND
        assert t._muc_vi() == muc, vnd
    app.last_wallet_micro = None
    assert t._muc_vi() == THUONG, "chưa biết số dư thì đừng doạ"


def test_may_con_chet_hien_chu_khong_chi_mau(tmp_path, monkeypatch, qapp):
    """Đèn máy con: người không phân biệt màu vẫn phải đọc ra nó đang tắt."""
    from core import trung_tam as tt

    goc = _dung_goc(tmp_path, monkeypatch, BON_KENH[:2])
    monkeypatch.setattr(tt, "la_vps", lambda _g: True)
    from ui_qt.trang_trung_tam import TrangTrungTam

    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()
    t = TrangTrungTam(app)
    t._dong_ho.stop()
    try:
        assert t._hop_may.isVisibleTo(t)
        assert "ĐÃ TẮT" in t._den["may_dang"].text()
        assert "Máy đăng" in t._den["may_dang"].text()
        assert "TẮT" not in t._den["agent"].text()
    finally:
        t.close()
        t.deleteLater()


# ── Không mất chức năng nào ──────────────────────────────────────────────────

#: Mọi nút bấm được của trang, viết tay. Danh sách này là hợp đồng: bỏ một nút
#: khỏi giao diện thì phải bỏ ở đây, và bỏ ở đây thì phải có người duyệt.
NUT_BAT_BUOC = (
    "Thêm kênh", "Cài đặt máy",          # hàng tiêu đề
    "Làm mới",                            # khối kênh + mục Nhật ký
    "Chạy ngay", "Chạy thử", "Mở thư mục",           # Tiến độ
    "Duyệt đăng", "Xem video", "Bỏ", "Mở gói",       # Chờ duyệt
    "Đọc số liệu",                                   # Hiệu quả
    "▸ Nhóm kênh",                                   # Nhóm kênh
    "Thẻ", "Bảng",                                   # đổi cách xem khối kênh
)

#: Mọi ô tick của trang.
O_TICK_BAT_BUOC = ("Hiện mọi kênh", "Tự chạy")

#: Năm mục của khối "Kênh đang chọn".
MUC_BAT_BUOC = ("Tiến độ", "Chờ duyệt", "Hiệu quả", "Nhật ký", "Cài đặt")


def test_khong_mat_nut_o_tick_nao(bon_kenh, qapp):
    t, _app, _goc = bon_kenh
    t.show()
    qapp.processEvents()
    chu_nut = {n.text().strip() for n in t.findChildren(QPushButton)}
    thieu = [c for c in NUT_BAT_BUOC if c not in chu_nut]
    assert not thieu, "mất nút: {0} (đang có: {1})".format(thieu, sorted(chu_nut))

    chu_tick = {o.text().strip() for o in t.findChildren(QCheckBox)}
    thieu = [c for c in O_TICK_BAT_BUOC if c not in chu_tick]
    assert not thieu, "mất ô tick: {0} (đang có: {1})".format(thieu, sorted(chu_tick))

    assert [t._tabs.tabText(i) for i in range(t._tabs.count())] == list(MUC_BAT_BUOC)


def test_muc_nhat_ky_van_chon_duoc_nguon(bon_kenh):
    """Mục Nhật ký chọn nguồn — hai nguồn cố định, cộng máy con khi có VPS."""
    t, _app, _goc = bon_kenh
    co = [t._o_nguon_log.itemData(i) for i in range(t._o_nguon_log.count())]
    assert co[:2] == ["tu_chay", "chay_tay"]


def test_o_tick_tu_chay_tren_the_ghi_xuong_tep(bon_kenh, qapp):
    """Ô tick trên thẻ ghi thẳng vào kênh.yaml, y như ô tick trong bảng."""
    from core.kenh import doc_kenh

    t, _app, goc = bon_kenh
    the = t._the_kenh["TL3-T7"]
    assert the._o_tu_chay.isChecked()
    the._o_tu_chay.setChecked(False)
    qapp.processEvents()
    assert doc_kenh(goc, "TL3-T7").tu_chay is False
    # Tắt tự chạy = kênh rời danh sách, y hệt nết của bảng cũ.
    assert "TL3-T7" not in t._the_kenh
    t._o_tat_ca.setChecked(True)        # "Hiện mọi kênh" để bật lại ngay ở đây
    qapp.processEvents()
    the = t._the_kenh["TL3-T7"]
    assert not the._o_tu_chay.isChecked(), "vẽ lại phải đúng trạng thái trong tệp"
    the._o_tu_chay.setChecked(True)
    qapp.processEvents()
    assert doc_kenh(goc, "TL3-T7").tu_chay is True


def test_ve_lai_khong_de_lai_the_thua(bon_kenh, qapp):
    """Làm mới nhiều lần không được đẻ thêm thẻ — 30 giây một lần, cả ngày."""
    t, _app, _goc = bon_kenh
    for _ in range(3):
        t.lam_moi()
        qapp.processEvents()
    assert len(t._the_kenh) == 4
    from ui_qt.trang_trung_tam import TheKenh

    assert len(t._hop_the.findChildren(TheKenh)) == 4


def test_the_hien_du_so_lieu_cua_dong_bang(bon_kenh, qapp):
    """Thẻ không được nghèo hơn dòng bảng cũ: đủ năm nhóm số liệu."""
    t, _app, _goc = bon_kenh
    t._anh = _anh_gia({"TL1-T7": "dang"})
    t._anh["kenh"][0].update(
        video={"tieu_de": "【心理学】一人が好きな人ほど実は賢い理由"},
        dang_luc="21/09 20:00",
        bay_ngay={"so_video": 3, "views": 53229, "ctr": 5.12, "dang_ky": 120},
        ypp={"gio_xem": 3823.0, "dang_ky": 388},
        tien={"hom_nay": 90000, "tran": 120000})
    t._ve_bang()
    qapp.processEvents()
    the = t._the_kenh["TL1-T7"]
    assert set(the._gia) == {"video", "dang", "bay_ngay", "ypp", "tien"}
    assert "20:00" in the._gia["dang"].text()
    assert "53,2k" in the._gia["bay_ngay"].text()
    # Chữ trên thẻ CẮT THEO PIXEL nên bề ngang máy chạy test đổi là chữ đổi —
    # số đầy đủ phải luôn còn nguyên ở tooltip.
    assert the._gia["ypp"].text().startswith("3.823 giờ")
    assert "3.823/4.000 giờ xem" in the._gia["ypp"].toolTip()
    assert "1.000 người đăng ký" in the._gia["ypp"].toolTip()
    assert "90k₫" in the._gia["tien"].text()
    assert "90.000₫" in the._gia["tien"].toolTip()
    # Tên đầy đủ của video không mất, nó nằm ở tooltip.
    assert "一人が好きな人ほど" in the._gia["video"].toolTip()
    # Cột "Tệp" của bảng cũ không mất: nó nằm trong tooltip của tên kênh.
    assert "Tệp khán giả" in the._nhan_ten.toolTip()


def test_o_chi_so_tren_dai_co_ten_va_so(bon_kenh, qapp):
    """Bốn ô số liệu của máy: tên ở trên, số ở dưới, đọc được cả hai."""
    t, _app, _goc = bon_kenh
    qapp.processEvents()
    assert "Ổ đĩa" in t._nhan_dia.text()
    assert "Ví" in t._nhan_vi.text()
    assert "Lịch" in t._nut_lich.text() and "02:00" in t._nut_lich.text()
    assert "Tiền" in t._nhan_tien.text()


def test_bang_van_giu_o_tick_va_dong_chon(bon_kenh, qapp):
    """Đường cũ vẫn nguyên: tick trong bảng vẫn ghi, chọn dòng vẫn đổi chi tiết."""
    from core.kenh import doc_kenh

    t, _app, goc = bon_kenh
    t._chon_kieu.set("Bảng")
    qapp.processEvents()
    hang = {str(t._bang_kenh.item(r, 0).data(Qt.UserRole)): r
            for r in range(t._bang_kenh.rowCount())}
    t._bang_kenh.selectRow(hang["TL2-T7"])
    assert t._ma_chon == "TL2-T7"
    t._bang_kenh.item(hang["TL4-T7"], 8).setCheckState(Qt.Unchecked)
    qapp.processEvents()
    assert doc_kenh(goc, "TL4-T7").tu_chay is False
