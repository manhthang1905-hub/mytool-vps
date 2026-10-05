"""core/ben_bi.py — mảnh tự phục hồi (kiểm toán chạy 1 năm, 06/10/2026).

Mọi bài dùng tmp_path + seam: không tiến trình/cổng/lịch Windows thật, không mạng.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from core import ben_bi

BAY_GIO = _dt.datetime(2026, 10, 6, 3, 0)
T = BAY_GIO.timestamp()


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(du, tep)


def _doc(duong):
    with open(duong, encoding="utf-8") as tep:
        return json.load(tep)


# ═══ 1. dọn khoá chết an toàn ═══════════════════════════════════════════════


class TestDonKhoaChet:
    def test_pid_chet_va_du_tuoi_thi_xoa(self, tmp_path):
        duong = str(tmp_path / "w" / ".khoa-may")
        _ghi(duong, {"pid": 4020, "bat_dau": T - 3600})
        ok, ly_do = ben_bi.don_khoa_chet_an_toan(duong, pid_thay=4020, bat_dau_thay=T - 3600,
                                                bay_gio=T, pid_con_song=lambda p: False)
        assert ok and ly_do == ""
        assert not os.path.exists(duong)
        assert not [t for t in os.listdir(os.path.dirname(duong)) if "chet" in t]  # không để rác

    def test_pid_con_song_thi_giu(self, tmp_path):
        duong = str(tmp_path / ".khoa-may")
        _ghi(duong, {"pid": 4020, "bat_dau": T - 3600})
        ok, _ = ben_bi.don_khoa_chet_an_toan(duong, pid_thay=4020, bay_gio=T, pid_con_song=lambda p: True)
        assert not ok and os.path.exists(duong)

    def test_khoa_moi_chua_du_tuoi_thi_giu(self, tmp_path):
        duong = str(tmp_path / ".khoa-may")
        _ghi(duong, {"pid": 4020, "bat_dau": T - 60})
        ok, ly_do = ben_bi.don_khoa_chet_an_toan(duong, pid_thay=4020, bay_gio=T, pid_con_song=lambda p: False)
        assert not ok and "chưa đủ" in ly_do and os.path.exists(duong)

    def test_khoa_doi_chu_thi_giu(self, tmp_path):
        duong = str(tmp_path / ".khoa-may")
        _ghi(duong, {"pid": 5000, "bat_dau": T - 3600})
        ok, _ = ben_bi.don_khoa_chet_an_toan(duong, pid_thay=4020, bay_gio=T, pid_con_song=lambda p: False)
        assert not ok and _doc(duong)["pid"] == 5000

    def test_cung_pid_nhung_moc_moi_thi_giu(self, tmp_path):
        """PID bị tái dùng/giữ lại: mốc `bat_dau` khác ảnh chụp → không đụng."""
        duong = str(tmp_path / ".khoa-may")
        _ghi(duong, {"pid": 4020, "bat_dau": T - 100})
        ok, _ = ben_bi.don_khoa_chet_an_toan(duong, pid_thay=4020, bat_dau_thay=T - 3600,
                                            bay_gio=T, pid_con_song=lambda p: False)
        assert not ok and os.path.exists(duong)

    def test_khong_co_tep_hay_tep_hong_khong_nem(self, tmp_path):
        duong = str(tmp_path / ".khoa-may")
        assert ben_bi.don_khoa_chet_an_toan(duong, pid_thay=1, bay_gio=T)[0] is False
        with open(duong, "w", encoding="utf-8") as tep:
            tep.write("{hong")
        assert ben_bi.don_khoa_chet_an_toan(duong, pid_thay=1, bay_gio=T)[0] is False

    def test_kiem_pid_loi_thi_coi_nhu_song(self, tmp_path):
        duong = str(tmp_path / ".khoa-may")
        _ghi(duong, {"pid": 4020, "bat_dau": T - 3600})

        def _no(pid):
            raise OSError("không hỏi được")

        assert ben_bi.don_khoa_chet_an_toan(duong, pid_thay=4020, bay_gio=T, pid_con_song=_no)[0] is False
        assert os.path.exists(duong)


def test_cho_lui_dan_gap_doi_va_kep_tran():
    assert [ben_bi.cho_lui_dan(n) for n in (1, 2, 3, 4, 5, 6, 50)] == [30, 60, 120, 240, 480, 900, 900]


# ═══ 2. nhịp tim / sập vòng / hạn giờ ═══════════════════════════════════════


class TestSapVong:
    def test_lan_dau_chi_ghi_so_lan_hai_moi_bao(self, tmp_path):
        goc = str(tmp_path)
        gui = []
        assert ben_bi.ghi_loi_vong(goc, "gac_tong", RuntimeError("x"), bay_gio=BAY_GIO,
                                   gui=lambda *a, **k: gui.append(a) or True) == 1
        assert gui == []
        assert ben_bi.ghi_loi_vong(goc, "gac_tong", RuntimeError("x"), bay_gio=BAY_GIO,
                                   gui=lambda *a, **k: gui.append(a) or True) == 2
        assert len(gui) == 1 and gui[0][0] == "vong_sap:gac_tong"
        with open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8") as tep:
            assert "sập 2 lượt liền" in tep.read()

    def test_chay_tron_thi_dat_lai_dem(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.ghi_loi_vong(goc, "v", RuntimeError("x"), gui=lambda *a, **k: True)
        ben_bi.xoa_loi_vong(goc, "v")
        assert ben_bi.ghi_loi_vong(goc, "v", RuntimeError("x"), gui=lambda *a, **k: True) == 1

    def test_ghi_nhip_giu_luc_xong(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.ghi_nhip(goc, "gac_tong", "xong", bay_gio=100.0)
        ben_bi.ghi_nhip(goc, "gac_tong", "bat_dau", bay_gio=200.0)
        nhip = ben_bi.doc_nhip(goc, "gac_tong")
        assert nhip["luc"] == 200.0 and nhip["luc_xong"] == 100.0 and nhip["buoc"] == "bat_dau"
        assert ben_bi.duong_nhip(goc, "gac_tong").endswith(os.path.join("gac-tong", "nhip.json"))

    def test_hen_gio_tu_thoat_goi_thoat_ma_3(self, tmp_path):
        import threading

        goc = str(tmp_path)
        xong = threading.Event()
        ma = []

        def _thoat(m):
            ma.append(m)
            xong.set()

        ben_bi.hen_gio_tu_thoat(goc, "gac_tong", 0.05, thoat=_thoat)
        assert xong.wait(5)
        assert ma == [3]
        assert ben_bi.doc_nhip(goc, "gac_tong")["buoc"] == "het_gio"


# ═══ 3. cả máy 36 giờ không ra gói mới ═══════════════════════════════════════


def _anh_ma_goi(*ma_goi, tu_chay=True):
    return {"kenh": {"K1": {"tu_chay": tu_chay, "ke_hoach": [{"Mã gói": m} for m in ma_goi]}}}


class TestKhongSanXuat:
    def test_lan_dau_chi_dat_moc_khong_bao(self, tmp_path):
        assert ben_bi.kiem_khong_san_xuat(str(tmp_path), _anh_ma_goi("K1-0001"), bay_gio=BAY_GIO) == []

    def test_qua_36_gio_khong_goi_moi_thi_bao_khan_mot_khoa(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001"), bay_gio=BAY_GIO)
        assert ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001"),
                                          bay_gio=BAY_GIO + _dt.timedelta(hours=30)) == []
        ds = ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001"), bay_gio=BAY_GIO + _dt.timedelta(hours=37))
        assert len(ds) == 1
        sc = ds[0]
        assert sc["loai"] == "khong_san_xuat" and sc["muc"] == "khan"
        assert sc["lap_gio"] == ben_bi.NGUONG_LAP_BAO_TIEN_GIO and sc["dedupe_khoa"]
        # Lượt 15' sau: cùng khoá lọc lặp (gac_tong._loc_lap_su_co sẽ nuốt).
        ds2 = ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001"),
                                         bay_gio=BAY_GIO + _dt.timedelta(hours=37, minutes=15))
        assert ds2[0]["dedupe_khoa"] == sc["dedupe_khoa"]

    def test_co_goi_moi_thi_dat_lai_moc(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001"), bay_gio=BAY_GIO)
        assert ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001", "K1-0002"),
                                          bay_gio=BAY_GIO + _dt.timedelta(hours=35)) == []
        assert ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001", "K1-0002"),
                                          bay_gio=BAY_GIO + _dt.timedelta(hours=60)) == []

    def test_khong_kenh_nao_tu_chay_thi_khong_bao(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001"), bay_gio=BAY_GIO)
        assert ben_bi.kiem_khong_san_xuat(goc, _anh_ma_goi("K1-0001", tu_chay=False),
                                          bay_gio=BAY_GIO + _dt.timedelta(hours=99)) == []

    def test_thu_khong_ghi_dia(self, tmp_path):
        ben_bi.kiem_khong_san_xuat(str(tmp_path), _anh_ma_goi("K1-0001"), bay_gio=BAY_GIO, ghi_dia=False)
        assert not os.path.exists(os.path.join(str(tmp_path), "workspace", "gac-tong", "san-xuat-cuoi.json"))


# ═══ 4. hồi sinh máy nền ═════════════════════════════════════════════════════


class _May:
    """Seam gộp: ghi lại lần mở giao diện/agent."""

    def __init__(self, gd_song=False, pid_song=False, cong=False, cap_nhat=False):
        self.gd_song, self.pid_song, self.cong, self.cap_nhat = gd_song, pid_song, cong, cap_nhat
        self.mo_gd, self.mo_agent = [], []

    def goi(self, goc, vm, bay_gio, ghi_dia=True):
        return ben_bi.hoi_sinh_may_nen(
            goc, vm, bay_gio=bay_gio, ghi_dia=ghi_dia,
            pid_con_song=lambda p: self.pid_song, cong_nghe=lambda c: self.cong,
            giao_dien_dang_chay=lambda g: self.gd_song,
            mo_giao_dien=lambda g: self.mo_gd.append(g) or True,
            mo_agent=lambda v: self.mo_agent.append(v) or True,
            dang_cap_nhat=lambda g: self.cap_nhat)


def _nhip_agent(vm, phut_truoc):
    _ghi(os.path.join(vm, "logs", "nhip-tim.json"), {"pid": 5112, "luc": T - phut_truoc * 60, "buoc": "x"})


class TestHoiSinh:
    def test_nhip_tuoi_thi_khong_lam_gi(self, tmp_path):
        vm = str(tmp_path / "vm")
        _nhip_agent(vm, 5)
        may = _May()
        assert may.goi(str(tmp_path), vm, BAY_GIO) == ([], [])

    def test_chua_tung_co_nhip_thi_khong_lam_gi(self, tmp_path):
        may = _May()
        assert may.goi(str(tmp_path), str(tmp_path / "vm"), BAY_GIO) == ([], [])

    def test_agent_va_giao_dien_chet_thi_mo_giao_dien_roi_mo_agent(self, tmp_path):
        goc, vm = str(tmp_path), str(tmp_path / "vm")
        _nhip_agent(vm, 25)
        may = _May()
        hd, _sc = may.goi(goc, vm, BAY_GIO)
        assert [h["loai"] for h in hd] == ["mo_lai_giao_dien"] and len(may.mo_gd) == 1
        # 15' sau giao diện vẫn không lên, agent vẫn chết → mở thẳng agent (không mở GD lần 2).
        hd2, _ = may.goi(goc, vm, BAY_GIO + _dt.timedelta(minutes=15))
        assert [h["loai"] for h in hd2] == ["mo_lai_agent"] and len(may.mo_agent) == 1
        assert len(may.mo_gd) == 1
        # 5' sau nữa: chưa đủ nhịp 30' cho mỗi kiểu → không mở dồn.
        hd3, _ = may.goi(goc, vm, BAY_GIO + _dt.timedelta(minutes=20))
        assert hd3 == []

    def test_giao_dien_song_ma_agent_chet_thi_mo_agent(self, tmp_path):
        goc, vm = str(tmp_path), str(tmp_path / "vm")
        _nhip_agent(vm, 25)
        may = _May(gd_song=True)
        hd, _ = may.goi(goc, vm, BAY_GIO)
        assert [h["loai"] for h in hd] == ["mo_lai_agent"] and not may.mo_gd

    def test_pid_song_hoac_cong_bi_giu_hoac_dang_cap_nhat_thi_khong_dung(self, tmp_path):
        goc, vm = str(tmp_path), str(tmp_path / "vm")
        _nhip_agent(vm, 90)
        for may in (_May(pid_song=True), _May(cong=True), _May(cap_nhat=True)):
            assert may.goi(goc, vm, BAY_GIO) == ([], [])
            assert not may.mo_gd and not may.mo_agent

    def test_chet_qua_60_phut_thi_co_su_co_khan(self, tmp_path):
        goc, vm = str(tmp_path), str(tmp_path / "vm")
        _nhip_agent(vm, 75)
        _hd, sc = _May().goi(goc, vm, BAY_GIO)
        assert len(sc) == 1 and sc[0]["loai"] == "may_nen_chet" and sc[0]["muc"] == "khan"

    def test_thu_khong_mo_gi_that(self, tmp_path):
        goc, vm = str(tmp_path), str(tmp_path / "vm")
        _nhip_agent(vm, 25)
        may = _May()
        hd, _ = may.goi(goc, vm, BAY_GIO, ghi_dia=False)
        assert hd and hd[0]["thuc_hien"] is False and not may.mo_gd
        assert not os.path.exists(os.path.join(goc, "workspace", "gac-tong", "hoi-sinh.json"))


def test_agent_sap_lap_trong_gio_thi_bao(tmp_path):
    vm = str(tmp_path / "vm")
    _ghi(os.path.join(vm, "logs", "agent-sap.json"), {"so_lan": 4, "luc": T - 120, "tu_luc": T - 900, "loi": "X: y"})
    ds = ben_bi.kiem_agent_sap(str(tmp_path), vm, bay_gio=BAY_GIO)
    assert len(ds) == 1 and ds[0]["loai"] == "agent_sap_lap"
    assert ben_bi.kiem_agent_sap(str(tmp_path), vm, bay_gio=BAY_GIO + _dt.timedelta(hours=2)) == []


# ═══ 5. canh gác tổng ════════════════════════════════════════════════════════


class TestCanhGacTong:
    def _goi(self, goc, bay_gio, da_dang_ky=True):
        dk, gui = [], []
        cau = ben_bi.canh_gac_tong(
            goc, bay_gio=bay_gio,
            trang_thai_lich=lambda g: {"da_dang_ky": da_dang_ky},
            dang_ky_lich=lambda g: dk.append(g) or (True, "ok"),
            gui=lambda *a, **k: gui.append(a) or True)
        return cau, dk, gui

    def test_chua_tung_co_nhip_thi_im(self, tmp_path):
        assert self._goi(str(tmp_path), BAY_GIO) == ("", [], [])

    def test_nhip_moi_thi_im(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.ghi_nhip(goc, "gac_tong", "xong", bay_gio=T - 20 * 60)
        assert self._goi(goc, BAY_GIO) == ("", [], [])

    def test_im_lau_va_mat_lich_thi_dang_ky_lai_va_bao(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.ghi_nhip(goc, "gac_tong", "xong", bay_gio=T - 3 * 3600)
        cau, dk, gui = self._goi(goc, BAY_GIO, da_dang_ky=False)
        assert "đăng ký lại OK" in cau and len(dk) == 1 and len(gui) == 1 and gui[0][0] == "gac_tong_im"
        # 10' sau (nhịp điều phối kế): KHÔNG đăng ký dồn, KHÔNG ghi loi-chay-max lần nữa.
        _c2, dk2, _g2 = self._goi(goc, BAY_GIO + _dt.timedelta(minutes=10), da_dang_ky=False)
        assert dk2 == []
        with open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8") as tep:
            assert tep.read().count("Người gác tổng") == 1

    def test_im_lau_lich_con_thi_chi_bao(self, tmp_path):
        goc = str(tmp_path)
        ben_bi.ghi_nhip(goc, "gac_tong", "xong", bay_gio=T - 3 * 3600)
        cau, dk, gui = self._goi(goc, BAY_GIO, da_dang_ky=True)
        assert cau and dk == [] and len(gui) == 1


# ═══ 6. vm/agent.py::chay_ben — vòng chính sập thì tự chạy lại, lùi dần ═══════


def _nap_agent(tmp_path):
    import importlib.util
    from pathlib import Path

    duong = Path(__file__).resolve().parent.parent / "vm" / "agent.py"
    spec = importlib.util.spec_from_file_location("vm_agent_ben_bi", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC = str(tmp_path / "vm")
    return mod


class TestAgentChayBen:
    def test_sap_hai_lan_roi_chay_tron_cho_lui_dan_va_ghi_so(self, tmp_path):
        agent = _nap_agent(tmp_path)
        lan = {"n": 0}
        ngu = []

        def _chay(cfg):
            lan["n"] += 1
            if lan["n"] <= 2:
                raise RuntimeError("tram hong")

        agent.chay_ben(doc_cfg=lambda: {}, chay_fn=_chay, ngu=ngu.append)
        assert lan["n"] == 3
        assert sum(ngu) == agent.SAP_CHO_CO_SO_GIAY * 3     # 30 s rồi 60 s
        so = _doc(os.path.join(agent.GOC, "logs", "agent-sap.json"))
        assert so["so_lan"] == 2 and "tram hong" in so["loi"]
        assert os.path.isfile(os.path.join(agent.GOC, "logs", "nhip-tim.json"))  # nhịp tim vẫn ghi lúc chờ

    def test_tran_cho_15_phut_va_lat_60_giay(self, tmp_path):
        agent = _nap_agent(tmp_path)
        lan = {"n": 0}
        ngu = []

        def _chay(cfg):
            lan["n"] += 1
            if lan["n"] <= 8:
                raise RuntimeError("x")

        agent.chay_ben(doc_cfg=lambda: {}, chay_fn=_chay, ngu=ngu.append)
        assert max(ngu) <= 60.0
        assert ngu[-15:] == [60.0] * 15     # lần sập thứ 8: chờ đúng trần 900 s

    def test_keyboard_interrupt_khong_bi_nuot(self, tmp_path):
        import pytest

        agent = _nap_agent(tmp_path)

        def _chay(cfg):
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            agent.chay_ben(doc_cfg=lambda: {}, chay_fn=_chay, ngu=lambda s: None)

    def test_mot_minh_lan_hai_trong_cung_tien_trinh_van_dung(self, tmp_path):
        import socket

        agent = _nap_agent(tmp_path)
        o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        o.bind(("127.0.0.1", 0))
        cong = o.getsockname()[1]
        o.close()
        duong_pid = str(tmp_path / "agent.pid")
        try:
            assert agent.mot_minh(cong=cong, duong_pid=duong_pid) is True
            assert agent.mot_minh(cong=cong, duong_pid=duong_pid) is True   # vòng chính chạy lại sau sập
        finally:
            if agent._O_MOT_MINH is not None:
                agent._O_MOT_MINH.close()


def test_nhip_dieu_phoi_goi_canh_gac_tong_va_hong_khong_chan_dieu_phoi(tmp_path, monkeypatch):
    """`tu_chay.py --dieu-phoi` (lịch 10'): canh gác tổng chạy TRƯỚC; nó hỏng thì nhịp điều phối vẫn chạy."""
    import importlib.util
    from pathlib import Path

    from core import dieu_phoi

    duong = Path(__file__).resolve().parent.parent / "tu_chay.py"
    spec = importlib.util.spec_from_file_location("tu_chay_goc_ben_bi", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "BASE_DIR", str(tmp_path))
    dong_log = []
    monkeypatch.setattr(mod, "bo_log_tat_ca", lambda goc, **k: dong_log.append)
    nhip = []
    monkeypatch.setattr(dieu_phoi, "nhip", lambda goc, **k: nhip.append(goc) or {"bat": True})

    def _canh_hong(goc, **k):
        raise RuntimeError("canh hong")

    monkeypatch.setattr(ben_bi, "canh_gac_tong", _canh_hong)
    assert mod.main(["--dieu-phoi"]) == 0
    assert nhip == [str(tmp_path)]
    assert any("canh gác tổng hỏng" in d for d in dong_log)

    monkeypatch.setattr(ben_bi, "canh_gac_tong", lambda goc, **k: "gác tổng im 99 phút")
    assert mod.main(["--dieu-phoi"]) == 0
    assert any("gác tổng im 99 phút" in d for d in dong_log)


# ═══ 7. dong_bo_git.kiem_khoi_vm — bản cập nhật làm hỏng vm/ bị chặn trước khi áp ═


class TestKiemKhoiVm:
    def _dung(self, tmp_path, cdp_hong=False):
        vm = tmp_path / "vm"
        vm.mkdir()
        (vm / "cdp.py").write_text("X = 1\n" if not cdp_hong else "import khong_ton_tai_abc\n", encoding="utf-8")
        (vm / "agent.py").write_text("import cdp\nY = cdp.X\n", encoding="utf-8")
        return str(tmp_path)

    def test_vm_dung_thi_dat(self, tmp_path):
        from core import dong_bo_git

        assert dong_bo_git.kiem_khoi_vm(self._dung(tmp_path), in_ra=lambda s: None) == []

    def test_vm_hong_import_thi_bao_loi(self, tmp_path):
        from core import dong_bo_git

        loi = dong_bo_git.kiem_khoi_vm(self._dung(tmp_path, cdp_hong=True), in_ra=lambda s: None)
        assert len(loi) == 1 and "vm/" in loi[0]

    def test_khong_co_vm_thi_bo_qua(self, tmp_path):
        from core import dong_bo_git

        assert dong_bo_git.kiem_khoi_vm(str(tmp_path), in_ra=lambda s: None) == []


def test_don_tep_py_rong_goc(tmp_path):
    (tmp_path / "cdp_studio.py").write_text("")
    (tmp_path / "that.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "vm").mkdir()
    (tmp_path / "vm" / "rong.py").write_text("")                  # không đệ quy
    assert ben_bi.don_tep_py_rong_goc(str(tmp_path)) == ["cdp_studio.py"]
    assert (tmp_path / "that.py").exists() and (tmp_path / "vm" / "rong.py").exists()
    assert ben_bi.don_tep_py_rong_goc(str(tmp_path)) == []
