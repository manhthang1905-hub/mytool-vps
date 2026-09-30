"""Giao diện của MÁY VPS: sáu bước rõ việc và các điều khiển cần thiết.

Chủ dự án xem bản sáu-tab trên máy thật (1416×1039), 21/09/2026: *"cái giao
diện nó xấu quá"*, *"tab vps có cần đâu"*, *"thiết kế lại all để phù hợp với
tool auto trên vps này"*, *"vì mọi thứ là auto nên nó sẽ cần các tính năng cả
phần để kiểm soát quản lý"*, rồi *"tao muốn nó đơn giản hiệu quả mà có thể
quản lý và thiết lập all ở gui để chủ động"*.

Bốn thứ bài này canh — bốn chỗ một lần "làm lại cho đẹp" dễ làm hỏng nhất:

1. **Đúng sáu trang, đúng quy trình.** Và tab "VPS" (thuê máy ảo rồi Remote Desktop
   vào chính máy mình đang ngồi) biến hẳn.
2. **Bốn cột kênh không tràn mép** ở cả 1024, 1280 lẫn 1416 — ba bề rộng thật
   (máy đang chạy là 1416; hai cái kia là cửa sổ bị kéo hẹp).
3. **Không mất nút, không mất ô tick.** Danh sách viết tay, y như nếp của
   `tests/test_trung_tam_giao_dien.py`.
4. **Không phơi tên khoá kỹ thuật.** `MyTool/CLAUDE.md`: khách không biết
   "tu_dang" là gì; nó phải hiện ra là "Tự đăng".

Không mạng, không tiền: dùng lại máy giả của `test_trung_tam` và app giả của
`test_trang_trung_tam`.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import QCheckBox, QLabel, QMessageBox, QPushButton  # noqa: E402

from test_trang_trung_tam import _AppGia, _GiamSatGia  # noqa: E402
from test_trung_tam import BAY_GIO, _ghi_json, _kenh  # noqa: E402

#: Cùng ngưỡng với `tests/test_bo_cuc.py` — cửa sổ hẹp nhất tool cho phép.
TRAN_RONG = 760

#: Ba bề rộng cửa sổ thật phải đẹp: máy đang chạy, và hai nấc bị kéo hẹp.
BE_RONG_THAT = (1024, 1280, 1416)

#: Bốn kênh thật của máy này.
BON_KENH = ("TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7")


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _dung_goc(tmp_path, monkeypatch, cac_ma=BON_KENH, *, gio_lich="2:00:00 AM") -> str:
    """Máy giả: `cac_ma` kênh đều bật tự chạy, lịch Windows ĐANG BẬT.

    `gio_lich` cố ý là chuỗi THẬT mà `schtasks` in ra trên máy đang chạy — 12
    tiếng, có AM/PM. Xem `ui_qt/widgets.py::gio_hhmm`.
    """
    from core import lich_tu_chay
    from core import trung_tam as tt

    goc = str(tmp_path)
    monkeypatch.setattr(tt, "la_vps", lambda _g: True)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    monkeypatch.setattr(lich_tu_chay, "trang_thai", lambda _g, **_k: {
        "da_dang_ky": True, "gio": gio_lich, "lan_chay_cuoi": "", "ket_qua_cuoi": ""})
    monkeypatch.setattr(lich_tu_chay, "trang_thai_canh_tram", lambda _g, **_k: {
        "da_dang_ky": True, "gio": "9:04:00 PM", "lan_chay_cuoi": "", "ket_qua_cuoi": ""})
    goc_anh_chup = tt.anh_chup
    monkeypatch.setattr(tt, "anh_chup", lambda g, **kw: goc_anh_chup(g, bay_gio=BAY_GIO, **kw))
    for i, ma in enumerate(cac_ma):
        _kenh(goc, ma, "Kênh " + ma, tu_chay=True, ngan_sach_ngay=120_000,
              tep=str(i + 1), nhom="TL", gio_dang="20:00")
    _ghi_json(os.path.join(goc, "vm", "config.json"),
              {"tram": "", "kenh": "", "cac_kenh": list(cac_ma), "chrome_theo_kenh": {}})
    return goc


def _mo(goc: str, *, co_may: bool = True):
    from ui_qt.trang_dieu_khien import TrangDieuKhien

    app = _AppGia(goc)
    if co_may:
        app.giam_sat_vm = _GiamSatGia()
    t = TrangDieuKhien(app)
    t._dong_ho.stop()          # đồng hồ 30 giây không được đọc đĩa giữa bài kiểm
    return t, app


@pytest.fixture
def bon_cot(tmp_path, monkeypatch, qapp):
    goc = _dung_goc(tmp_path, monkeypatch)
    t, app = _mo(goc)
    yield t, app, goc
    t.close()
    t.deleteLater()


# ── 1. Đúng sáu trang ─────────────────────────────────────────────────────────


def test_che_do_vps_co_sau_trang_theo_quy_trinh(tmp_path):
    """Máy có `vps.json` thì thanh bên có bảy trang: "Bảng điều khiển" đứng
    riêng (nhóm "HẰNG NGÀY"), sáu trang quy trình cũ gập vào "Nâng cao"
    (`TRANG_NANG_CAO`) — thiết kế lại 29/09/2026, Việc 2."""
    import json

    from core import che_do_vps
    from ui_qt.app import TRANG

    goc = str(tmp_path)
    with open(os.path.join(goc, che_do_vps.TEN_MARKER), "w", encoding="utf-8") as tep:
        json.dump({"vm_dir": goc}, tep)

    nav = che_do_vps.loc_trang(goc, TRANG)
    assert [k for k, _bt, _nh in nav] == [
        "tong-quan", "so-lieu-vps", "nghien-cuu-vps", "chon-content-vps",
        "san-xuat-vps", "dang-cham-soc-vps", "he-thong"]
    assert [nh for _k, _bt, nh in nav] == [
        "Bảng điều khiển", "Số liệu kênh", "Nghiên cứu", "Chọn nội dung",
        "Sản xuất", "Lịch đăng", "Cài đặt"]
    assert che_do_vps.trang_mo_dau(goc) == "tong-quan"
    assert che_do_vps.NHOM_VPS == {"tong-quan": "HẰNG NGÀY"}
    assert che_do_vps.TRANG_NANG_CAO == (
        "so-lieu-vps", "nghien-cuu-vps", "chon-content-vps", "san-xuat-vps",
        "dang-cham-soc-vps", "he-thong")


def test_bo_han_tab_vps(tmp_path):
    """Tab "VPS" để THUÊ máy ảo rồi Remote Desktop VÀO máy — ngồi ngay trên
    chính máy đó thì vô nghĩa, nên nó không còn trên thanh bên."""
    import json

    from core import che_do_vps
    from ui_qt.app import TRANG

    goc = str(tmp_path)
    with open(os.path.join(goc, che_do_vps.TEN_MARKER), "w", encoding="utf-8") as tep:
        json.dump({"vm_dir": goc}, tep)
    khoa = [k for k, _bt, _nh in che_do_vps.loc_trang(goc, TRANG)]
    assert "chrome-sach" not in khoa
    # Nhưng máy nhà (không có vps.json) thì KHÔNG mất tab nào.
    assert che_do_vps.loc_trang(str(tmp_path / "khong-co"), TRANG) == tuple(TRANG)


# ── 2. Bốn cột không tràn mép ────────────────────────────────────────────────


@pytest.mark.parametrize("rong", BE_RONG_THAT)
def test_bon_cot_khong_tran_mep(tmp_path, monkeypatch, qapp, rong):
    """Ở cả ba bề rộng thật, không cột nào thò ra ngoài vùng vẽ của trang."""
    goc = _dung_goc(tmp_path, monkeypatch)
    t, _app = _mo(goc)
    try:
        # Trừ thanh bên 240 — trang chỉ được phần còn lại của cửa sổ.
        t.resize(rong - 240, 900)
        t.show()
        qapp.processEvents()
        assert t._cot, "chưa dựng cột nào"
        tran = [ma for ma, c in t._cot.items() if c.x() + c.width() > t.width()]
        assert not tran, "cột thò ra ngoài mép ở {0}px: {1}".format(rong, tran)
    finally:
        t.close()
        t.deleteLater()


def test_trang_co_duoc_xuong_760px(bon_cot, qapp):
    """Nếp của `tests/test_bo_cuc.py`: đo `minimumSizeHint`, không phải `sizeHint`."""
    t, _app, _goc = bon_cot
    t.show()
    qapp.processEvents()
    rong = t.minimumSizeHint().width()
    assert rong <= TRAN_RONG, "trang cần {0}px, không co xuống {1}px".format(
        rong, TRAN_RONG)


def test_bon_kenh_xep_moi_kenh_mot_hang_o_man_that(bon_cot, qapp):
    """1416px: mỗi kênh một hàng để mắt quét trạng thái từ trên xuống."""
    t, _app, _goc = bon_cot
    t.resize(1416 - 240, 950)
    t.show()
    qapp.processEvents()
    assert set(t._cot) == set(BON_KENH), sorted(t._cot)
    toa_do = [(c.x(), c.y()) for c in t._cot.values()]
    assert len({y for _x, y in toa_do}) == len(BON_KENH), toa_do
    assert len({x for x, _y in toa_do}) == 1, toa_do


def test_moi_cot_hien_du_tam_khau(bon_cot, qapp):
    """Tám khâu của `core/tu_chay.py`, đủ cả tám, trong MỌI cột."""
    from core.auto import MA_KHAU

    t, _app, _goc = bon_cot
    for ma, cot in t._cot.items():
        assert list(cot._khau) == list(MA_KHAU), ma
        for nh in cot._khau.values():
            assert nh.text().strip(), "khâu không có chữ ở cột " + ma


# ── 3. Không mất nút, không mất ô tick ───────────────────────────────────────

#: Mọi nút của trang Điều khiển. Danh sách này là hợp đồng.
NUT_BAT_BUOC = (
    "Tạm dừng tất cả", "Làm mới",          # kiểm soát cả máy
    "Bật lịch", "Tắt lịch",                # lịch hằng ngày (một trong hai)
    "Chạy ngay", "Chạy lại",               # từng kênh
)

#: Mọi ô tick của trang — bốn công tắc mỗi kênh, bằng TIẾNG VIỆT.
O_TICK_BAT_BUOC = ("Tự chạy", "Tự đăng", "Trả lời bình luận", "Tự dọn")


def test_khong_mat_nut_o_tick_nao(bon_cot, qapp):
    t, _app, _goc = bon_cot
    t.show()
    qapp.processEvents()
    chu_nut = {n.text().strip() for n in t.findChildren(QPushButton)}
    thieu = [c for c in NUT_BAT_BUOC
             if c not in chu_nut and not (c in ("Bật lịch", "Tắt lịch")
                                          and chu_nut & {"Bật lịch", "Tắt lịch"})]
    assert not thieu, "mất nút: {0} (đang có: {1})".format(thieu, sorted(chu_nut))

    chu_tick = {o.text().strip() for o in t.findChildren(QCheckBox)}
    thieu = [c for c in O_TICK_BAT_BUOC if c not in chu_tick]
    assert not thieu, "mất ô tick: {0} (đang có: {1})".format(thieu, sorted(chu_tick))


def test_moi_kenh_sua_duoc_ngan_sach_ngay_tren_cot(bon_cot, qapp):
    """Ngân sách/ngày sửa ngay trên giao diện — và ghi thẳng xuống `kenh.yaml`."""
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    cot = t._cot["TL2-T7"]
    cot._o_ngan_sach.setValue(333_000)
    cot._hen.stop()
    t._doi_ngan_sach("TL2-T7", cot._o_ngan_sach.value())
    qapp.processEvents()
    assert int(doc_kenh(goc, "TL2-T7").ngan_sach_ngay) == 333_000


def test_ngan_sach_0_noi_ro_la_khong_san_xuat(tmp_path, monkeypatch, qapp):
    """0₫ KHÔNG phải "bỏ trần" — nó là "không sản xuất gì cả". Phải nói thẳng."""
    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    from core.trung_tam import ghi_cai_kenh

    ghi_cai_kenh(goc, "TL1-T7", ngan_sach_ngay=0)
    t, _app = _mo(goc)
    try:
        chu = t._cot["TL1-T7"]._nhan_canh_ns.text()
        assert "KHÔNG" in chu and "sản xuất" in chu, chu
    finally:
        t.close()
        t.deleteLater()


# ── 4. Không phơi tên khoá kỹ thuật ──────────────────────────────────────────

#: Tên khoá trong tệp, không bao giờ được hiện lên màn hình.
KHOA_KY_THUAT = ("tu_dang", "tu_tra_loi_cmt", "ngan_sach_ngay", "tu_chay",
                 "tu_don", "voice_id", "may_dang", "may_cmt")


def test_khong_hien_ten_khoa_ky_thuat(bon_cot, qapp):
    t, _app, _goc = bon_cot
    t.show()
    qapp.processEvents()
    chu = [w.text() for w in t.findChildren(QLabel)]
    chu += [w.text() for w in t.findChildren(QPushButton)]
    chu += [w.text() for w in t.findChildren(QCheckBox)]
    lo = [(c, k) for c in chu for k in KHOA_KY_THUAT if k in c]
    assert not lo, "phơi tên khoá kỹ thuật ra màn hình: {0}".format(lo)


def test_den_may_goi_ten_tieng_viet(tmp_path, monkeypatch, qapp):
    """`core.giam_sat_vm` đặt tên ba con là `agent` / `tu_dang` /
    `tu_tra_loi_cmt`. Người dùng phải thấy "Máy đăng", "Trả lời bình luận"."""
    from ui_qt.trang_trung_tam import _TEN_MAY

    assert _TEN_MAY["tu_dang"] == "Máy đăng"
    assert _TEN_MAY["tu_tra_loi_cmt"] == "Trả lời bình luận"

    class _GiamSatKhoaThat(_GiamSatGia):
        def trang_thai(self):
            return {"agent": {"song": True}, "tu_dang": {"song": False},
                    "tu_tra_loi_cmt": {"song": True}}

    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    from ui_qt.trang_dieu_khien import TrangDieuKhien

    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatKhoaThat()
    t = TrangDieuKhien(app)
    t._dong_ho.stop()
    try:
        assert "Máy đăng" in t._den["tu_dang"].text()
        assert "ĐÃ TẮT" in t._den["tu_dang"].text(), "màu không đi một mình"
        assert "Trả lời bình luận" in t._den["tu_tra_loi_cmt"].text()
    finally:
        t.close()
        t.deleteLater()


# ── Nút "Tạm dừng tất cả" ────────────────────────────────────────────────────


def test_tam_dung_tat_ca_goi_dung_duong_ghi(bon_cot, qapp, monkeypatch):
    """Một cú bấm tắt tự chạy MỌI kênh, đi đúng cửa `core.trung_tam.ghi_cai_kenh`."""
    from core import trung_tam as tt
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    goi = []
    that = tt.ghi_cai_kenh

    def ghi(g, ma, **khoa):
        goi.append((ma, dict(khoa)))
        that(g, ma, **khoa)

    monkeypatch.setattr(tt, "ghi_cai_kenh", ghi)
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.Yes))

    t._tam_dung_tat_ca()
    qapp.processEvents()
    assert sorted(ma for ma, _k in goi) == sorted(BON_KENH)
    assert all(k == {"tu_chay": False} for _ma, k in goi)
    for ma in BON_KENH:
        assert doc_kenh(goc, ma).tu_chay is False, ma
    assert "Bật lại" in t._nut_tam_dung.text()

    # Và nút ấy bật lại ĐÚNG chừng ấy kênh.
    goi.clear()
    t._tam_dung_tat_ca()
    qapp.processEvents()
    assert sorted(ma for ma, _k in goi) == sorted(BON_KENH)
    assert all(k == {"tu_chay": True} for _ma, k in goi)
    assert "Tạm dừng" in t._nut_tam_dung.text()


def test_tam_dung_khong_bat_nham_kenh_von_da_tat(tmp_path, monkeypatch, qapp):
    """Kênh chủ dự án cố ý tắt từ trước KHÔNG được nút "Bật lại" bật hộ."""
    from core import trung_tam as tt
    from core.kenh import doc_kenh

    goc = _dung_goc(tmp_path, monkeypatch)
    tt.ghi_cai_kenh(goc, "TL3-T7", tu_chay=False)
    t, _app = _mo(goc)
    try:
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.Yes))
        t._tam_dung_tat_ca()
        qapp.processEvents()
        t._tam_dung_tat_ca()
        qapp.processEvents()
        assert doc_kenh(goc, "TL3-T7").tu_chay is False
        assert doc_kenh(goc, "TL1-T7").tu_chay is True
    finally:
        t.close()
        t.deleteLater()


def test_cong_tac_ghi_dung_noi(bon_cot, qapp):
    """Bốn công tắc, hai chỗ lưu: sản xuất vào `kenh.yaml`, máy ảo vào `may-ao.json`."""
    from core import vm_cai_dat
    from core.kenh import doc_kenh

    t, _app, goc = bon_cot
    t._doi_cong_tac("TL1-T7", "tu_don", True)
    assert doc_kenh(goc, "TL1-T7").tu_don is True

    t._doi_cong_tac("TL1-T7", "tu_dang", True)
    assert vm_cai_dat.doc(goc, "TL1-T7")["tu_dang"] is True
    t._doi_cong_tac("TL1-T7", "tu_tra_loi_cmt", False)
    assert vm_cai_dat.doc(goc, "TL1-T7")["tu_tra_loi_cmt"] is False


# ── Lỗi "lịch đang tắt" trong khi lịch đang bật ──────────────────────────────


def test_gio_windows_doc_dung_moi_dinh_dang():
    """`schtasks` in giờ theo ĐỊNH DẠNG VÙNG của máy, không phải HH:MM."""
    from ui_qt.widgets import gio_hhmm

    assert gio_hhmm("2:00:00 AM") == "02:00"     # đúng chuỗi máy thật in ra
    assert gio_hhmm("9:04:00 PM") == "21:04"     # cắt [:5] sẽ thành 09:04 — lệch nửa ngày
    assert gio_hhmm("12:00:00 AM") == "00:00"
    assert gio_hhmm("12:30:00 PM") == "12:30"
    assert gio_hhmm("02:00") == "02:00"
    assert gio_hhmm("14:30:00") == "14:30"
    assert gio_hhmm("") == "" and gio_hhmm(None) == ""
    assert gio_hhmm("không phải giờ") == ""


def test_lich_dang_bat_thi_khong_kenh_nao_bao_chua_bat_lich(bon_cot, qapp):
    """Lỗi đo được trên máy thật 21/09/2026.

    `ShopAPI-TuChay` đã đăng ký thật, `trang_thai()` trả `da_dang_ky: True`,
    nhưng giao diện gắn "⚠ Chưa bật lịch" lên MỌI kênh — vì nó cắt `[:5]` cái
    chuỗi `"2:00:00 AM"` thành `"2:00:"`, thứ không ai dựng lại thành giờ được.
    """
    t, _app, _goc = bon_cot
    assert t._gio_lich() == "02:00"
    cau = [(k.get("bay_gio") or {}).get("chu") for k in (t._anh or {}).get("kenh") or []]
    assert cau, "chưa đọc được kênh nào"
    assert not [c for c in cau if "Chưa bật lịch" in str(c)], cau
    assert "Lịch chạy hằng ngày đang tắt" not in [chu for _m, chu in t.viec_can_xem()]


def test_viec_can_xem_xep_viec_nang_len_truoc(bon_cot, qapp):
    """Dải "N việc cần xem": hỏng (✕) đứng trên đáng lưu ý (⚠)."""
    from ui_qt.trang_dieu_khien import HONG, LUU_Y

    t, _app, _goc = bon_cot
    t._anh = {"o_dia": {"con_gb": 5.0}, "la_vps": True,      # ổ đĩa: HỎNG
              "kenh": [{"ma": "TL1-T7", "tu_chay": True,
                        "bay_gio": {"muc": "canh_bao", "chu": "Chưa đặt trần tiền"}}]}
    t._may = {}
    viec = t.viec_can_xem()
    assert [m for m, _c in viec] == [HONG, LUU_Y]
    t._mo_viec = True
    t._ve_viec()
    qapp.processEvents()
    assert "2 việc cần xem" in t._nut_viec.text()
    assert t._hop_viec.isVisibleTo(t)


# ── Cài đặt từng kênh: sửa được hết trên giao diện ───────────────────────────


def test_the_tu_chay_sua_duoc_moi_thiet_lap(tmp_path, monkeypatch, qapp):
    """Không việc nào bắt chủ dự án mở `kenh.yaml` bằng Notepad nữa."""
    from core.kenh import doc_kenh
    from ui_qt.trang_quan_ly_kenh import TheTuChay

    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    app = _AppGia(goc)
    the_tc = TheTuChay(app, lambda: "TL1-T7", co_lich=False)
    try:
        the_tc.nap()
        the_tc._o_voice.setText("giong-moi-123")
        the_tc._o_phut.setValue(17)
        the_tc._o_nhan_tieu_de.setText("雑学")
        the_tc._o_so_ban.setValue(4)
        the_tc._o_tu_don.setChecked(True)
        the_tc._o_don_sau.setValue(48)
        the_tc._tu_luu_tu_chay()
        k = doc_kenh(goc, "TL1-T7")
        assert k.voice_id == "giong-moi-123"
        assert int(k.phut_muc_tieu) == 17
        assert k.nhan_tieu_de == "雑学"
        assert int(k.so_ban_nhap) == 4
        assert k.tu_don is True
        assert int(k.don_sau_gio) == 48
    finally:
        the_tc.close()
        the_tc.deleteLater()


def test_the_tu_chay_khong_danh_roi_tep_khan_gia(tmp_path, monkeypatch, qapp):
    """Bốn kênh thật khai tệp bằng SLUG, ô chọn lưu MÃ SỐ.

    Không nối hai cách viết ấy lại thì ô rơi về "(chưa chọn)" và cú tự lưu kế
    tiếp ghi `tep: ""` — kênh mất tệp khán giả mà không ai bấm gì.
    """
    from core.kenh import doc_kenh
    from ui_qt.trang_quan_ly_kenh import TheTuChay

    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7",))
    from core.trung_tam import ghi_cai_kenh

    ghi_cai_kenh(goc, "TL1-T7", tep="nguoi-to-mo-xem-minh-la-kieu-nguoi-nao")
    app = _AppGia(goc)
    the_tc = TheTuChay(app, lambda: "TL1-T7", co_lich=False)
    try:
        the_tc.nap()
        assert the_tc._o_tep.currentData() == "3", "slug phải dò ra đúng tệp số 3"
        the_tc._o_phut.setValue(12)          # đụng vào một ô KHÁC → tự lưu
        assert doc_kenh(goc, "TL1-T7").tep == "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"
        # Đổi sang tệp khác thì mới ghi giá trị mới.
        the_tc._o_tep.setCurrentIndex(the_tc._o_tep.findData("4"))
        assert doc_kenh(goc, "TL1-T7").tep == "4"
    finally:
        the_tc.close()
        the_tc.deleteLater()


def test_canh_bao_trung_khong_phoi_ten_khoa(tmp_path, monkeypatch, qapp):
    """`core.nhom_kenh.kiem_trung_lap` viết cho nhật ký nên có kèm tên khoá —
    lên màn hình thì phải là chữ người thường đọc."""
    from ui_qt.trang_quan_ly_kenh import _bo_ten_khoa

    chu = _bo_ten_khoa("Cùng giọng đọc (voice_id abc123): TL1-T7, TL2-T7")
    assert "voice_id" not in chu and "mã giọng" in chu
    assert "style_name" not in _bo_ten_khoa("Cùng TÊN BỘ VẼ (style_name x)")


def test_the_tu_chay_bao_trung_giong_trong_nhom(tmp_path, monkeypatch, qapp):
    """Hai kênh anh em cùng `voice_id` là với khán giả chúng LÀ MỘT kênh."""
    from ui_qt.trang_quan_ly_kenh import TheTuChay

    goc = _dung_goc(tmp_path, monkeypatch, ("TL1-T7", "TL2-T7"))
    from core.trung_tam import ghi_cai_kenh

    ghi_cai_kenh(goc, "TL2-T7", voice_id="giong-TL1-T7")   # trùng kênh anh
    app = _AppGia(goc)
    the_tc = TheTuChay(app, lambda: "TL2-T7", co_lich=False)
    try:
        the_tc.nap()
        chu = the_tc._nhan_trung.text()
        assert "giọng" in chu.lower(), chu
        assert "TL1-T7" in chu and "TL2-T7" in chu, chu
    finally:
        the_tc.close()
        the_tc.deleteLater()
