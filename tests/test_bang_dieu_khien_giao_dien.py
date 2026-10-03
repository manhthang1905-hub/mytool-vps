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
    # Phòng điều hành (01/10/2026): KHÔNG sinh tiến trình tính số thật trong bài kiểm.
    from core import bang_dieu_khien as bdk

    monkeypatch.setattr(bdk, "sinh_tinh_so", lambda g, ds: 0)
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
    from core import vm_cai_dat
    vm_cai_dat.luu(goc, "K2", ghim_dom=True)      # việc ghim chỉ hiện khi kênh BẬT ghim
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
    from core import vm_cai_dat
    vm_cai_dat.luu(goc, "K2", ghim_dom=True)
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
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    the = t._the_kenh["K3"]
    dang_chay = the._tu_chay
    the._nut_tam_dung.click()
    qapp.processEvents()
    assert goi and goi[0] == (goc, "K3", "tu_chay", not dang_chay)


def test_tam_dung_kenh_hoi_lai_bam_khong_thi_khong_ghi(trang, monkeypatch, qapp):
    from core import bang_dieu_khien as bdk

    t, _app, _goc = trang
    goi = []
    monkeypatch.setattr(bdk, "doi_cong_tac", lambda g, ma, khoa, bat: goi.append((ma, khoa, bat)))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
    the = t._the_kenh["K1"]
    assert the._tu_chay and the._nut_tam_dung.text() == "Tạm dừng kênh"
    the._nut_tam_dung.click()
    qapp.processEvents()
    assert goi == []


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


def test_dong_may_o_cong_ty_an_khi_chua_hop_hien_khi_co_bao_cao(trang, qapp):
    """01/10/2026: ô "Công ty" (tổng giám đốc) — chưa có báo cáo thì ẩn; có thì hiện, bấm = Báo cáo công ty."""
    t, _app, _goc = trang
    dm = t._dong_may
    assert not dm._o_cong_ty.isVisibleTo(dm)
    dm.nap({"cong_ty": {"cau": "Công ty (gợi ý) 05/10: 4 kênh · lên 1 · chững 2 · tụt 1 · 18 khe", "bao_cao": "x"}},
           _goc, "", "")
    assert dm._o_cong_ty.isVisibleTo(dm) and "4 kênh" in dm._o_cong_ty.text()
    goi = []
    t._mo_bao_cao_cong_ty = lambda: goi.append(1)
    t._hanh_dong("bao_cao_cong_ty", {})
    assert goi == [1]


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
        "tu_chay": True, "tu_duyet": False, "video_ke_tiep": {}, "video_gan_day": [],
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
    assert the._nhan_ke_tiep.text().startswith("Lịch đăng tiếp")
    the.deleteLater()


def test_video_ke_tiep_rong_khong_co_gio_thi_chi_noi_chua_co(qapp):
    the = _the_don(qapp, video_ke_tiep={})
    assert the._nhan_ke_tiep.text() == "Lịch đăng tiếp: chưa có"
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


# ── Phòng điều hành công ty (Đợt G, 01/10/2026) ──────────────────────────────

_PHONG_MAU = {
    "muc": "hong", "ma_so": "K1",
    "so": {"loai": "tut", "da": 0.43, "thang_28": 4, "kl_28": 6,
           "cong": [{"ten": "Hiển thị", "muc": "hong", "chu": "1.709 / cần 6.000", "n": 3},
                    {"ten": "Tỉ lệ bấm trang chủ", "muc": "tot", "chu": "12,1% / mục tiêu 5,0%", "n": 2},
                    {"ten": "Giữ chân", "muc": "chua", "chu": "chưa đủ số", "n": 0}],
           "video": [{"id": "v1", "tieu_de": "Video một", "ket": "cho", "tuoi_gio": 16.5, "doan": "truot"},
                     {"id": "v2", "tieu_de": "Video hai", "ket": "thang", "hien_thi_48h": 15707},
                     {"id": "v3", "tieu_de": "Video ba", "ket": "truot", "hien_thi_48h": 1709}]},
    "ypp": {"sub": 30.0, "gio_xem": 167.0},
    "doi_ai": [{"ai": "Giám đốc kênh", "cau": "Cổng hiển thị hỏng nặng."},
               {"ai": "Khám nghiệm", "cau": "video v3 (7d): hook lệch tiêu đề."}],
    "dang_thu": ["Cứu tỉ lệ bấm: đổi tiêu đề"],
    "lich_tiep": [{"chu_luc": "20:00 01/10", "chu": "20:00 01/10 · đã hẹn", "da_hen": True, "tieu_de": "Video tối"},
                  {"chu_luc": "khe 05:00 03/10", "chu": "khe 05:00 03/10 — máy chọn content & sản xuất lúc 05:00 02/10",
                   "da_hen": False, "tieu_de": ""}],
}


def test_the_phong_dieu_hanh_hien_du_cac_dong(qapp):
    the = _the_don(qapp, phong=_PHONG_MAU, giam_doc={"che_do": "goi_y", "cau": "x", "bao_cao": "x.md"})
    assert "tụt" in the._nhan_loai.text()
    assert [o.text().split("\n")[0] for o in the._o_cong] == ["Hiển thị", "Tỉ lệ bấm trang chủ", "Giữ chân"]
    assert "chờ (16 giờ)" in the._hang_video[0].text() and "đoán trượt" in the._hang_video[0].text()
    assert "thắng" in the._hang_video[1].text() and "trượt" in the._hang_video[2].text()
    assert the._nhan_giam_doc.text() == "Giám đốc kênh: Cổng hiển thị hỏng nặng."
    assert the._nhan_ai[0].text().startswith("Khám nghiệm:") and the._nhan_ai[1].isHidden()
    assert the._nhan_dang_thu.text() == "Đang thử: Cứu tỉ lệ bấm: đổi tiêu đề"
    assert the._nhan_ke_tiep.text() == "Lịch đăng tiếp: 20:00 01/10 · đã hẹn 「Video tối」 · khe 05:00 03/10 — máy chọn content & sản xuất lúc 05:00 02/10"
    assert the._nhan_ypp_sub.text() == "Sub 30/1.000" and the._thanh_sub.value() == 30
    assert the._muc == "hong"
    the.deleteLater()


def test_the_bam_ba_nut_chi_tiet_bao_dung_hanh_dong(qapp):
    from ui_qt.trang_bang_dieu_khien import TheKenhLon

    bam = []
    the = TheKenhLon("K1", lambda *a: None, lambda ma, hd: bam.append(hd))
    the.nap({"ma": "K1", "giam_doc": {"bao_cao": "x.md"}, "phong": _PHONG_MAU})
    the._nut_bao_cao.click()
    the._nut_bai_hoc.click()
    the._nut_quyet.click()
    assert bam == ["bao_cao_giam_doc", "bai_hoc", "quyet_dinh"]
    assert the._nut_quyet.text() == "Quyết định && độ chính xác"
    the.deleteLater()


def test_trang_xep_kenh_do_len_dau_va_sinh_tinh_so(tmp_path, monkeypatch, qapp):
    from core import bang_dieu_khien as bdk

    goc = _dung_goc(tmp_path, monkeypatch)
    sinh = []
    monkeypatch.setattr(bdk, "sinh_tinh_so", lambda g, ds: sinh.append(list(ds)) or 123)
    that = bdk.phong_dieu_hanh

    def phong(g, bang, **kw):
        ph = that(g, bang, **kw)
        ph["thu_tu"] = list(reversed(ph["thu_tu"]))
        return ph

    monkeypatch.setattr(bdk, "phong_dieu_hanh", phong)
    t, _app = _mo(goc)
    try:
        # 03/10/2026: thứ tự nay ở CỘT TRÁI (mỗi kênh một dòng) — kênh tự chạy theo `thu_tu`, kênh không tự
        # chạy (sản xuất ở máy khác) xuống cuối.
        dau = next(m for m in t._phong["thu_tu"] if (t._kenh(m) or {}).get("tu_chay"))
        assert t._thu_tu_ben[0] == dau
        assert t._v_dong.itemAt(0).widget() is t._dong_ben[dau]
        cuoi = [m for m in t._thu_tu_ben if not (t._kenh(m) or {}).get("tu_chay")]
        assert t._thu_tu_ben[len(t._thu_tu_ben) - len(cuoi):] == cuoi
        assert sinh and set(sinh[0]) >= {"K1", "K2"}, "chưa có bộ đệm số → phải sinh tiến trình tính"
        t.lam_moi()
        assert len(sinh) == 1, "không sinh lại trong vòng GIAY_TINH_LAI"
        assert t._khoi_cong_ty._o_video.text().startswith("Video hôm nay")
    finally:
        t.close()
        t.deleteLater()


def test_chon_kenh_doi_vung_chinh_va_ba_tab(trang, qapp):
    """03/10/2026: bấm một dòng cột trái → vùng giữa là kênh đó (thẻ đầy đủ + tab Video/Bài học);
    bấm "Toàn công ty" → lại ba tab công ty."""
    t, _app, _goc = trang
    assert [t._tab.tabText(i) for i in range(3)] == list(t.TAB_CONG_TY)
    ma = t._thu_tu_ben[0]
    t.chon(ma)
    assert [t._tab.tabText(i) for i in range(3)] == list(t.TAB_KENH)
    assert t._the_kenh[ma].isVisibleTo(t)
    assert not [m for m, c in t._the_kenh.items() if m != ma and c.isVisibleTo(t)]
    t._tab.setCurrentIndex(1)
    assert "Kế hoạch đăng" in " ".join(w.text() for w in t._trang_k[1].findChildren(QLabel))
    t._tab.setCurrentIndex(2)
    from ui_qt.trang_phong_chi_tiet import HopBaiHoc, HopQuyetDinh

    assert t._trang_k[2].findChildren(HopBaiHoc) and t._trang_k[2].findChildren(HopQuyetDinh)
    t.chon("")
    assert t._tab.tabText(1) == "Báo cáo tuần" and t._tieu.text() == "Toàn công ty"


def test_dai_duoi_nhan_tinh_hinh_may(tmp_path, monkeypatch, qapp):
    goc = _dung_goc(tmp_path, monkeypatch)
    from ui_qt.trang_bang_dieu_khien import TrangBangDieuKhien

    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()
    nhan_duoc = []
    app.dat_thanh_duoi = lambda chu, tip="": nhan_duoc.append(chu)
    t = TrangBangDieuKhien(app)
    t._dong_ho.stop()
    try:
        assert nhan_duoc and "Agent đăng: chạy" in nhan_duoc[-1] and "Ổ trống 500 GB" in nhan_duoc[-1]
    finally:
        t.close()
        t.deleteLater()


def test_chi_tiet_may_bat_tat_dong_may(trang, qapp):
    t, _app, _goc = trang
    assert not t._dong_may.isVisibleTo(t)
    t._hanh_dong("chi_tiet_may", {})
    assert t._dong_may.isVisibleTo(t) and "▾" in t._khoi_cong_ty._nut_chi_tiet.text()


def test_khong_phoi_tu_ky_thuat_tren_the_phong(qapp):
    the = _the_don(qapp, phong=_PHONG_MAU)
    chu = [w.text() for w in the.findChildren(QLabel)] + [w.text() for w in the.findChildren(QPushButton)]
    assert not [c for c in chu for tu in _TU_CAM if tu in c]
    the.deleteLater()


def test_hop_bai_hoc_nut_sai_goi_gach(tmp_path, monkeypatch, qapp):
    from core import bang_dieu_khien as bdk
    from ui_qt.trang_phong_chi_tiet import HopBaiHoc

    app = _AppGia(str(tmp_path))
    hop = HopBaiHoc(app, "K1", tu_nap=False)
    dong = [{"ma_bai": "kn:a", "chuyen_gia": "khan_gia", "ten_pham_vi": "Kênh này", "pham_vi": "kenh",
             "cau": "Hook 30s đầu.", "n": 3, "tin_cay": "vua", "bom": True, "video": ["aV4P"], "da_gach": False},
            {"ma_bai": "h:b", "chuyen_gia": "chu_de", "ten_pham_vi": "Nhóm kênh", "pham_vi": "nhom",
             "cau": "Cụm IQ.", "n": 1, "da_gach": True}]
    hop.ve(dong)
    nut = [n for n in hop.findChildren(QPushButton) if n.text() == "Sai"]
    assert len(nut) == 1, "bài đã gạch không còn nút Sai"
    goi = []
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(bdk, "gach_bai_hoc", lambda g, m, b, **kw: goi.append((m, b["ma_bai"])))
    monkeypatch.setattr(bdk, "so_bai_hoc", lambda g, m, **kw: [dict(dong[0], da_gach=True)])
    nut[0].click()
    assert goi == [("K1", "kn:a")]
    assert "0 bài học · 1 đã gạch" in hop._nhan_trang.text()
    hop.deleteLater()


def test_hop_quyet_dinh_va_bao_cao_tuan(tmp_path, qapp):
    from ui_qt.trang_phong_chi_tiet import HopBaoCaoTuan, HopQuyetDinh

    app = _AppGia(str(tmp_path))
    hop = HopQuyetDinh(app, "K1", tu_nap=False)
    hop.ve({"ti_le": [{"loai": "du_doan", "ten_loai": "Đoán thắng/trượt", "dung": 1, "tong": 2, "so_quyet": 3}],
            "dong": [{"luc": "2026-10-01 10:20", "ten_loai": "Đoán thắng/trượt", "quyet": "Video a: đoán trượt",
                      "vi_sao": "ít hiển thị", "ket_qua": "ĐÚNG", "dung": True}]})
    assert "1/2" in hop._nhan_ti_le.text() and hop.bang.rowCount() == 1
    assert hop.bang.item(0, 4).text() == "ĐÚNG"
    hop.deleteLater()
    bc = HopBaoCaoTuan(app, "K1")
    assert [bc.the.tabText(i) for i in range(bc.the.count())] == ["Kênh K1", "Công ty"]
    bc.deleteLater()
