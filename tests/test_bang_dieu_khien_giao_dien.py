"""Bài kiểm giao diện cho trang **Bảng điều khiển** (Việc 2,
`workspace/THIET-KE-BANG-DIEU-KHIEN.md`, duyệt 29/09/2026).

Nếp giống hệt `tests/test_giao_dien_vps.py`: máy giả trên `tmp_path`, app giả
`_AppGia` (không mạng, `run_bg` chạy NGAY trên luồng gọi), Qt offscreen. Không
gọi mạng — `core.tong_quan_vps.canh_bao_windows` (chạy `wevtutil.exe`, thật,
mất tới 8 giây) bị monkeypatch về `{}` trong `_dung_goc`; bài kiểm riêng cho
dòng "Windows sắp hết hạn" tự patch lại giá trị khác `{}`.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import (  # noqa: E402
    QCheckBox, QLabel, QMessageBox, QPushButton,
)

from test_trung_tam import BAY_GIO, dung_may  # noqa: E402

#: Cùng ngưỡng `tests/test_bo_cuc.py` — cửa sổ hẹp nhất tool cho phép.
TRAN_RONG = 760
#: Ba bề rộng cửa sổ thật (máy đang chạy là 1416; hai cái kia bị kéo hẹp).
BE_RONG_THAT = (1024, 1280, 1416)


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _AppGia:
    """App giả — `run_bg` chạy NGAY trên luồng gọi, không luồng nền/mạng."""

    def __init__(self, goc: str):
        self.base_dir = goc
        self.client = None
        self.last_wallet_micro = None
        self.thong_bao = []
        self.trang_mo = []

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def trang(self, _khoa):
        return None

    def show_page(self, khoa):
        self.trang_mo.append(khoa)

    def note_balance(self, so_du):
        pass

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001 — cùng nết run_bg thật
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


class _GiamSatGia:
    """Ba con máy TÊN ĐÚNG khoá mà `core.bang_dieu_khien` đọc (`agent`,
    `tu_dang`, `tu_tra_loi_cmt`) — khác `_GiamSatGia` của
    `test_trang_trung_tam.py` (khoá `may_dang`/`may_cmt`, dành cho trang cũ)."""

    def __init__(self):
        self.khoi_lai = []

    def trang_thai(self):
        return {"agent": {"song": True, "pid": 11, "lan_khoi": 0, "loi_cuoi": ""},
                "tu_dang": {"song": True, "pid": 12, "lan_khoi": 0, "loi_cuoi": ""},
                "tu_tra_loi_cmt": {"song": True, "pid": 13, "lan_khoi": 0, "loi_cuoi": ""}}

    def khoi_dong_lai(self, ten):
        self.khoi_lai.append(ten)


def _dung_goc(tmp_path, monkeypatch, *, gio_lich="2:00:00 AM") -> str:
    """Máy giả: K1 đang làm video, K2 chờ duyệt, K3 đã hẹn (máy đăng quản),
    K4 lỗi, K5 chưa đặt trần tiền, K6 không tự chạy/không máy đăng quản (đi
    vào "Kênh khác") — nguyên `test_trung_tam.dung_may`, dùng lại thay vì
    dựng tay để có đủ `ke-hoach.csv`/`chi-so` thật cho các dòng việc."""
    from core import lich_tu_chay
    from core import tong_quan_vps
    from core import trung_tam as tt

    goc = str(tmp_path)
    monkeypatch.setattr(tt, "la_vps", lambda _g: True)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    monkeypatch.setattr(lich_tu_chay, "trang_thai", lambda _g, **_k: {
        "da_dang_ky": True, "gio": gio_lich, "lan_chay_cuoi": "", "ket_qua_cuoi": ""})
    # `wevtutil.exe` thật mất tới 8 giây và không việc gì bài kiểm phải chờ nó
    # — mặc định coi như Windows không báo gì; bài kiểm riêng patch lại.
    monkeypatch.setattr(tong_quan_vps, "canh_bao_windows", lambda *a, **k: {})
    # Máy THẬT chạy VPS này đang chật đĩa (ghi trong CLAUDE.local.md) — không
    # để dung lượng đĩa thật của máy chạy bài kiểm lẻn vào kết quả kiểm.
    monkeypatch.setattr(tt, "_o_dia", lambda _g: {"con_gb": 500.0, "tong_gb": 1000.0})
    goc_anh_chup = tt.anh_chup
    monkeypatch.setattr(tt, "anh_chup", lambda g, **kw: goc_anh_chup(g, bay_gio=BAY_GIO, **kw))
    dung_may(goc, BAY_GIO)
    return goc


def _mo(goc: str, *, co_may: bool = True, client=None):
    from ui_qt.trang_bang_dieu_khien import TrangBangDieuKhien

    app = _AppGia(goc)
    app.client = client
    if co_may:
        app.giam_sat_vm = _GiamSatGia()
    t = TrangBangDieuKhien(app)
    t._dong_ho.stop()          # đồng hồ 30 giây không được đọc đĩa giữa bài kiểm
    return t, app


@pytest.fixture
def trang(tmp_path, monkeypatch, qapp):
    goc = _dung_goc(tmp_path, monkeypatch)
    t, app = _mo(goc)
    yield t, app, goc
    t.close()
    t.deleteLater()


# ── Co được xuống 760px, không tràn ở ba bề rộng thật ────────────────────────


def test_trang_co_duoc_xuong_760px(trang, qapp):
    t, _app, _goc = trang
    t.show()
    qapp.processEvents()
    rong = t.minimumSizeHint().width()
    assert rong <= TRAN_RONG, "trang cần {0}px, không co xuống {1}px".format(rong, TRAN_RONG)


@pytest.mark.parametrize("rong", BE_RONG_THAT)
def test_khong_tran_mep_o_be_rong_that(tmp_path, monkeypatch, qapp, rong):
    goc = _dung_goc(tmp_path, monkeypatch)
    t, _app = _mo(goc)
    try:
        t.resize(rong - 240, 900)
        t.show()
        qapp.processEvents()
        assert t._the_kenh, "chưa dựng thẻ kênh nào"
        tran = [ma for ma, c in t._the_kenh.items() if c.x() + c.width() > t.width()]
        assert not tran, "thẻ thò ra ngoài mép ở {0}px: {1}".format(rong, tran)
    finally:
        t.close()
        t.deleteLater()


# ── Không phơi từ ngữ kỹ thuật ────────────────────────────────────────────────

_TU_CAM = ("tu_dang", "tu_chay", "cho_duyet", ".json", "CTR")


def test_khong_hien_tu_ngu_ky_thuat(trang, qapp):
    t, _app, _goc = trang
    t.show()
    qapp.processEvents()
    chu = [w.text() for w in t.findChildren(QLabel)]
    chu += [w.text() for w in t.findChildren(QPushButton)]
    chu += [w.text() for w in t.findChildren(QCheckBox)]
    lo = [(c, tu) for c in chu for tu in _TU_CAM if tu in c]
    assert not lo, "phơi từ ngữ kỹ thuật ra màn hình: {0}".format(lo)


# ── Không có việc → câu trấn an ───────────────────────────────────────────────


def test_khong_co_viec_thi_bao_may_tu_chay(tmp_path, monkeypatch, qapp):
    """Máy trống trơn (không kênh nào, đã đăng nhập, không máy con để trông)
    thì khối Việc chỉ còn MỘT câu trấn an, không phải một danh sách rỗng lặng
    lẽ."""
    from core import lich_tu_chay
    from core import tong_quan_vps
    from core import trung_tam as tt
    from ui_qt.trang_bang_dieu_khien import TrangBangDieuKhien

    goc = str(tmp_path)
    monkeypatch.setattr(tt, "la_vps", lambda _g: True)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    monkeypatch.setattr(lich_tu_chay, "trang_thai", lambda _g, **_k: {
        "da_dang_ky": True, "gio": "2:00:00 AM", "lan_chay_cuoi": "", "ket_qua_cuoi": ""})
    monkeypatch.setattr(tong_quan_vps, "canh_bao_windows", lambda *a, **k: {})
    monkeypatch.setattr(tt, "_o_dia", lambda _g: {"con_gb": 500.0, "tong_gb": 1000.0})
    goc_anh_chup = tt.anh_chup
    monkeypatch.setattr(tt, "anh_chup", lambda g, **kw: goc_anh_chup(g, bay_gio=BAY_GIO, **kw))

    app = _AppGia(goc)
    app.client = object()          # "đã đăng nhập" — không thì luôn có 1 việc
    t = TrangBangDieuKhien(app)
    t._dong_ho.stop()
    try:
        assert t._bang.get("viec") == []
        assert t._khoi_viec._nhan_rong.isVisibleTo(t), "câu trấn an phải hiện dù cửa sổ chưa show()"
        assert "Không có việc gì" in t._khoi_viec._nhan_rong.text()
        assert "máy đang tự chạy" in t._khoi_viec._nhan_rong.text()
    finally:
        t.close()
        t.deleteLater()


# ── Windows sắp hết hạn (dòng 14, ghép thêm ở Việc 2) ────────────────────────


def test_canh_bao_windows_ra_dong_viec_dau_tien(tmp_path, monkeypatch, qapp):
    from core import tong_quan_vps

    goc = _dung_goc(tmp_path, monkeypatch)
    monkeypatch.setattr(tong_quan_vps, "canh_bao_windows", lambda *a, **k: {
        "muc": "loi", "tieu_de": "Windows đã tự tắt do hết hạn Evaluation",
        "chi_tiet": "chạy slmgr.vbs /xpr để kiểm tra"})
    t, _app = _mo(goc)
    try:
        # `t._bang["viec"]` (kết quả thô của `bang_dieu_khien.viec_cua_ban`)
        # không có dòng này — Việc 2 tự ghép thêm lúc vẽ (`_ve_viec`).
        assert all(v["khoa"] != "windows-canh-bao" for v in t._bang.get("viec") or [])
        assert t._windows_canh_bao.get("tieu_de", "").startswith("Windows đã tự tắt")
        nut = [n for n in t._khoi_viec.findChildren(QPushButton) if n.text() == "Xem cách xử lý"]
        assert nut, "thiếu nút 'Xem cách xử lý' của dòng cảnh báo Windows"
    finally:
        t.close()
        t.deleteLater()


# ── Mỗi nút gọi đúng đường ghi ────────────────────────────────────────────────


def test_nut_da_ghim_goi_danh_dau_xong(trang, monkeypatch, qapp):
    from core import bang_dieu_khien as bdk

    t, _app, goc = trang
    duong = os.path.join(goc, "CHANNEL", "K2", "can-ghim.md")
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("- [2026-09-18 10:00] **Video cần ghim** — "
                  "https://www.youtube.com/watch?v=vidGhim\n"
                  "  > bình luận mở đầu\n")
    goi = []
    monkeypatch.setattr(bdk, "danh_dau_xong", lambda g, k, **kw: goi.append((g, k)))
    t.lam_moi()
    qapp.processEvents()
    nut = next(n for n in t._khoi_viec.findChildren(QPushButton) if n.text() == "Đã ghim")
    nut.click()
    qapp.processEvents()
    assert goi == [(goc, "ghim:vidGhim")]


def test_chep_link_dat_vao_clipboard(trang, monkeypatch, qapp):
    t, _app, goc = trang
    duong = os.path.join(goc, "CHANNEL", "K2", "can-ghim.md")
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("- [2026-09-18 10:00] **Video cần ghim** — "
                  "https://www.youtube.com/watch?v=vidGhim2\n  > ghi chú\n")
    t.lam_moi()
    qapp.processEvents()
    nut = next(n for n in t._khoi_viec.findChildren(QPushButton) if n.text() == "Chép link")
    nut.click()
    qapp.processEvents()
    from PyQt5.QtWidgets import QApplication

    assert "vidGhim2" in QApplication.clipboard().text()


def test_cong_tac_tu_lam_video_ghi_dung_duong(trang, monkeypatch, qapp):
    from core import bang_dieu_khien as bdk

    t, _app, goc = trang
    goi = []
    monkeypatch.setattr(bdk, "doi_cong_tac", lambda g, ma, khoa, bat: goi.append((g, ma, khoa, bat)))
    the = t._the_kenh["K3"]
    the._o_tu_chay.setChecked(not the._o_tu_chay.isChecked())
    qapp.processEvents()
    assert goi and goi[0][:3] == (goc, "K3", "tu_chay")


def test_cong_tac_tu_len_lich_hoi_lai_truoc_khi_bat(trang, monkeypatch, qapp):
    """Quyết định 1: bật "Tự lên lịch" phải hỏi lại trước khi ghi."""
    from core import trung_tam as tt

    t, _app, goc = trang
    goi = []
    monkeypatch.setattr(tt, "ghi_cai_kenh", lambda g, ma, **kw: goi.append((g, ma, kw)))
    the = t._the_kenh["K1"]
    assert the._o_tu_duyet.isChecked() is False

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
    the._o_tu_duyet.setChecked(True)
    qapp.processEvents()
    assert goi == [], "bấm Không thì KHÔNG được ghi"

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    the._o_tu_duyet.setChecked(True)
    qapp.processEvents()
    assert goi == [(goc, "K1", {"tu_duyet": True})]


def test_nut_mo_thu_muc_the_goi_dung_thu_muc(trang, monkeypatch, qapp):
    from ui_qt import trang_bang_dieu_khien as mod

    t, _app, goc = trang
    mo = []
    monkeypatch.setattr(mod, "mo_thu_muc", lambda d: mo.append(d))
    t._the_hanh_dong("K1", "mo_thu_muc")
    assert mo, "chưa mở thư mục nào"


def test_dong_may_bam_vi_mo_trang_he_thong(trang, qapp):
    # 29/09/2026 (kiểm toán #12): "may-vi" không nằm trong `TRANG_VPS` nên
    # trên VPS bấm nút không ra gì — khoá đúng là "he-thong" (cùng file
    # `trang_may_vi.py`, lớp `TrangHeThongVps`, xem `ui_qt/app.py:566`).
    t, app, _goc = trang
    t._hanh_dong("mo_vi", {})
    assert app.trang_mo == ["he-thong"]


# ── Thẻ không dựng lại khi làm mới ────────────────────────────────────────────


def test_the_khong_dung_lai_khi_lam_moi(trang, qapp):
    t, _app, _goc = trang
    truoc = {ma: id(c) for ma, c in t._the_kenh.items()}
    assert truoc
    t.lam_moi()
    qapp.processEvents()
    sau = {ma: id(c) for ma, c in t._the_kenh.items()}
    assert truoc == sau, "thẻ kênh bị dựng lại (đổi id) giữa hai lần làm mới"


# ── Tiêu đề thẻ bỏ phần mô tả, dòng "Video kế tiếp" nói rõ khi trống ──────────


def _the_don(qapp, **k_over):
    from core import bang_dieu_khien as bdk
    from ui_qt.trang_bang_dieu_khien import TheKenhLon

    k = {"ma": "K1", "ten": "K1", "bay_gio": {"chu": "Hôm nay chưa chạy", "muc": "nghi"},
        "tu_chay": False, "tu_duyet": False, "video_ke_tiep": {}, "video_gan_day": [],
        "may_dang_hoc": ""}
    k.update(k_over)
    k["muc_the"] = bdk.muc_the(k)
    the = TheKenhLon("K1", lambda *a: None, lambda *a: None)
    the.nap(k)
    qapp.processEvents()
    return the


def test_ten_the_bo_phan_mo_ta_sau_gach_ngang(qapp):
    """Dữ liệu thật 29/09/2026 (TL1-T7): `ten` trong kenh.yaml là
    "tên — mô tả dài" — tiêu đề thẻ chỉ hiện phần tên, mô tả dồn hết vào
    tooltip, kẻo tiêu đề tràn cả hàng."""
    the = _the_don(qapp, ten="テスト用チャンネル — 心理学、テスト用の説明")
    assert the._nhan_ten.text() == "K1 · テスト用チャンネル"
    assert "心理学" in the._nhan_ten.toolTip()
    the.deleteLater()


def test_ten_the_khong_co_gach_ngang_giu_nguyen(qapp):
    the = _the_don(qapp, ten="Tên gọn")
    assert the._nhan_ten.text() == "K1 · Tên gọn"
    the.deleteLater()


def test_video_ke_tiep_rong_noi_ro_luc_may_lam_lai(qapp):
    the = _the_don(qapp, video_ke_tiep={}, video_ke_tiep_tu="29/09 20:00")
    assert "chưa có" in the._nhan_ke_tiep.text()
    assert "29/09 20:00" in the._nhan_ke_tiep.text()
    the.deleteLater()


def test_video_ke_tiep_rong_khong_co_gio_thi_chi_noi_chua_co(qapp):
    the = _the_don(qapp, video_ke_tiep={})
    assert the._nhan_ke_tiep.text() == "Video kế tiếp  — chưa có"
    the.deleteLater()


# ── Trang ẩn không đọc đĩa ────────────────────────────────────────────────────


def test_trang_an_khong_doc_dia(tmp_path, monkeypatch, qapp):
    goc = _dung_goc(tmp_path, monkeypatch)
    t, app = _mo(goc)
    try:
        assert not t.isVisible()
        so_lan = []
        that = app.run_bg

        def dem(viec, on_ok=None, on_err=None):
            so_lan.append(1)
            return that(viec, on_ok=on_ok, on_err=on_err)

        app.run_bg = dem
        t.lam_moi(bat_buoc=False)
        assert not so_lan, "trang ẩn mà vẫn đọc đĩa (gọi run_bg)"
        t.lam_moi(bat_buoc=True)
        assert so_lan, "lam_moi(bat_buoc=True) phải đọc đĩa kể cả khi ẩn"
    finally:
        t.close()
        t.deleteLater()
