"""QUÉT NGÀY — mỗi kênh MỘT việc quét độc lập mỗi ngày (30/09/2026).

Chủ kênh: "vừa đăng video mới vừa quét". Các bài dưới chốt: giờ quét rải theo
vị trí kênh (khoá cấu hình), chỉ chạy một lần/ngày khi xong, thử lại trong ngày
khi hỏng (có trần), giữ khe Chrome dùng chung ("quet"), và CỔNG QUÉT của mắt cào
(`che-do.json`) — mở cho lượt quét, chặn cho mọi lần mở Chrome khác.
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


def _nap_agent(tmp_path):
    spec = importlib.util.spec_from_file_location("agent_quet_ngay", GOC / "vm" / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC = str(tmp_path)
    mod.THU_MUC_TIEN_ICH = str(tmp_path / "tien-ich")
    return mod


def _luc(h, m):
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, h, m, 0, 0, 0, -1))


class TestGioQuetNgay:
    def test_mac_dinh_rai_30_phut_tu_0210(self, tmp_path):
        ag = _nap_agent(tmp_path)
        assert [ag.gio_quet_ngay_kenh({}, i) for i in range(4)] == ["02:10", "02:40", "03:10", "03:40"]

    def test_khoa_cau_hinh(self, tmp_path):
        ag = _nap_agent(tmp_path)
        ch = {"quet_ngay_gio": "01:05", "quet_ngay_cach_phut": 20}
        assert ag.gio_quet_ngay_kenh(ch, 2) == "01:45"

    def test_den_han_mot_lan_thu_lai_co_tran(self, tmp_path):
        ag = _nap_agent(tmp_path)
        assert ag.quet_ngay_den_han({}, "02:10", _luc(2, 9)) is False
        assert ag.quet_ngay_den_han({}, "02:10", _luc(2, 10)) is True
        assert ag.quet_ngay_den_han({"xong": True, "lan": 1}, "02:10", _luc(9, 0)) is False
        hong = {"lan": 1, "luc": _luc(2, 10), "xong": False}
        assert ag.quet_ngay_den_han(hong, "02:10", _luc(2, 40)) is False, "chưa đủ 45' thì chưa thử lại"
        assert ag.quet_ngay_den_han(hong, "02:10", _luc(2, 56)) is True
        assert ag.quet_ngay_den_han({"lan": 3, "luc": 1}, "02:10", _luc(9, 0)) is False, "trần 3 lượt/ngày"


class TestChayQuetNgay:
    def _chuan_bi(self, ag, monkeypatch, ket_qua):
        monkeypatch.setattr(ag, "van_ipv4_mo", lambda: False)
        monkeypatch.setattr(ag, "tim_chrome", lambda ch: "C:/x/{0}.exe".format(ch.get("kenh")))
        khoa = []
        monkeypatch.setattr(ag, "giu_khoa_may_chung",
                            lambda viec="", kenh="", uu_tien=1: khoa.append((viec, kenh)) or True)
        monkeypatch.setattr(ag, "nha_khoa_may_chung", lambda: khoa.append("nha"))
        chay = []
        monkeypatch.setattr(ag, "chay_quet_ngay_mot_kenh",
                            lambda cau_hinh, ch, kenh: chay.append(kenh) or dict(ket_qua, kenh=kenh))
        return khoa, chay

    def test_chay_kenh_som_nhat_giu_khe_quet_roi_xong_ca_ngay(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        cau = {"thu_muc_du_lieu": str(tmp_path)}
        khoa, chay = self._chuan_bi(ag, monkeypatch,
                                    {"xong": True, "quet_studio": "tiện ích báo xong", "ket_thuc": "x"})
        hl = {"A": {"kenh": "A"}, "B": {"kenh": "B"}}
        assert ag.chay_quet_ngay(cau, hl, ["A", "B"], bay_gio=_luc(3, 0)) is True
        assert chay == ["A"] and khoa[0] == ("quet", "A") and khoa[-1] == "nha"
        assert ag.chay_quet_ngay(cau, hl, ["A", "B"], bay_gio=_luc(3, 1)) is True
        assert chay == ["A", "B"]
        assert ag.chay_quet_ngay(cau, hl, ["A", "B"], bay_gio=_luc(9, 0)) is False, "mỗi kênh 1 lần/ngày"
        tt = ag._doc_trang_thai(cau)
        assert tt["phien_ket_qua@A"]["quet_studio"] == "tiện ích báo xong", "giao diện đọc chỗ cũ"

    def test_chua_toi_gio_thi_khong_chay(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        cau = {"thu_muc_du_lieu": str(tmp_path)}
        _k, chay = self._chuan_bi(ag, monkeypatch, {"xong": True})
        assert ag.chay_quet_ngay(cau, {"A": {}, "B": {}}, ["A", "B"], bay_gio=_luc(2, 20)) is True
        assert chay == ["A"]
        assert ag.chay_quet_ngay(cau, {"A": {}, "B": {}}, ["A", "B"], bay_gio=_luc(2, 25)) is False, \
            "kênh thứ hai chỉ tới lượt 02:40"

    def test_hong_thi_thu_lai_trong_ngay(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        cau = {"thu_muc_du_lieu": str(tmp_path)}
        _khoa, chay = self._chuan_bi(ag, monkeypatch, {"xong": False, "quet_studio": "lỗi: x"})
        hl = {"A": {"kenh": "A"}}
        assert ag.chay_quet_ngay(cau, hl, ["A"], bay_gio=_luc(2, 30)) is True
        assert ag.chay_quet_ngay(cau, hl, ["A"], bay_gio=_luc(2, 45)) is False
        assert ag.chay_quet_ngay(cau, hl, ["A"], bay_gio=_luc(3, 20)) is True
        assert ag.chay_quet_ngay(cau, hl, ["A"], bay_gio=_luc(4, 10)) is True
        assert ag.chay_quet_ngay(cau, hl, ["A"], bay_gio=_luc(9, 0)) is False, "trần 3 lượt"
        assert chay == ["A", "A", "A"]

    def test_khe_ban_thi_khong_tinh_luot(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        cau = {"thu_muc_du_lieu": str(tmp_path)}
        self._chuan_bi(ag, monkeypatch, {"xong": True})
        monkeypatch.setattr(ag, "giu_khoa_may_chung", lambda **k: False)
        assert ag.chay_quet_ngay(cau, {"A": {}}, ["A"], bay_gio=_luc(3, 0)) is False
        assert not ag._doc_trang_thai(cau), "khe bận thì không ghi lượt"

    def test_dang_do_dang_thi_hoan(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        cau = {"thu_muc_du_lieu": str(tmp_path)}
        _k, chay = self._chuan_bi(ag, monkeypatch, {"xong": True})
        (tmp_path / "logs").mkdir()
        (tmp_path / "logs" / "dang-dodang.json").write_text("{}", encoding="utf-8")
        assert ag.chay_quet_ngay(cau, {"A": {}}, ["A"], bay_gio=_luc(3, 0)) is False
        assert chay == []


class TestMotLuotQuetNgay:
    def test_mo_cong_quet_roi_dong_cong_va_dong_chrome(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        thu_tu = []
        monkeypatch.setattr(ag, "tim_chrome", lambda ch: "")
        monkeypatch.setattr(ag, "quet_studio",
                            lambda ch, cho_giay=None, ma="", han_quet=None:
                            thu_tu.append(("studio", bool(ma), han_quet > cho_giay)) or "tiện ích báo xong")
        monkeypatch.setattr(ag, "quet_trang_chu", lambda ch: thu_tu.append("trang_chu") or "ok")
        monkeypatch.setattr(ag, "lay_loi_thoai", lambda ch: thu_tu.append("loi_thoai") or {})
        monkeypatch.setattr(ag, "ghi_che_do_mat_cao",
                            lambda ch, quet, han_giay=0, ma="": thu_tu.append(("cong", quet)))
        monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: thu_tu.append("dong"))
        # Cổng "trang chủ đủ tin để cào" đọc sổ thật của kênh — bài này chỉ chốt THỨ TỰ các bước.
        monkeypatch.setattr(ag, "trang_chu_tin_cay", lambda _k: (True, ""))
        ket = ag.chay_quet_ngay_mot_kenh({}, {"kenh": "A"}, "A")
        assert thu_tu == [("studio", True, True), "trang_chu", "loi_thoai", ("cong", False), "dong"]
        assert ket["xong"] is True


class TestCongQuetMatCao:
    def test_ghi_cho_phep_chan_va_xoa(self, tmp_path):
        ag = _nap_agent(tmp_path)
        # 01/10/2026: máy một kênh cũng dùng `tien-ich/<kênh>/` (chưa có mắt cào phẳng nếp cũ)
        tm = tmp_path / "tien-ich" / "A"
        tm.mkdir(parents=True)
        ch = {"kenh": "A"}
        ag.ghi_che_do_mat_cao(ch, True, 600, "123")
        d = json.loads((tm / "che-do.json").read_text(encoding="utf-8"))
        assert d["che_do"] == "phien" and d["ma"] == "123"
        assert d["quet_den"] > time.time() * 1000 + 590 * 1000
        ag.ghi_che_do_mat_cao(ch, False)
        d = json.loads((tm / "che-do.json").read_text(encoding="utf-8"))
        assert d["quet_den"] == 0, "Chrome mở cho việc đăng — cổng CHẶN"
        ag.ghi_che_do_mat_cao(ch, None)
        assert not (tm / "che-do.json").exists(), "máy một kênh nếp cũ — tự do"

    def test_mat_cao_bao_xong_qua_danh_sach_tab(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)

        class _TL:
            def __init__(self, du):
                self.du = du

            def read(self):
                return json.dumps(self.du).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        tabs = [{"url": "chrome-extension://abc/nghi.html"}]
        monkeypatch.setattr(ag.urllib.request, "urlopen", lambda url, timeout=3: _TL(tabs))
        assert ag._mat_cao_bao_xong({"kenh": "A"}, "777") is False
        tabs.append({"url": "chrome-extension://abc/nghi.html?quet_xong=777"})
        assert ag._mat_cao_bao_xong({"kenh": "A"}, "777") is True
        assert ag._mat_cao_bao_xong({"kenh": "A"}, "") is False

    def test_mat_cao_js_co_cong_quet(self):
        js = (GOC / "core" / "ytb_extension" / "background.js").read_text(encoding="utf-8")
        for can in ("che-do.json", "choPhepQuet", "quet_xong=", "batDauQuetNeuCan", "kiemXongQuet"):
            assert can in js, can
        tc = (GOC / "core" / "ytb_extension" / "trang-chu.js").read_text(encoding="utf-8")
        assert "cho_phep_quet" in tc


def test_doi_ten_nen_theo_ban_buoc_chrome_nap_worker_moi(tmp_path):
    """30/09/2026 22:40: Chrome giữ service worker CŨ dù đĩa đã mới → đổi URL script theo nội dung."""
    ag = _nap_agent(tmp_path)
    tm = tmp_path / "ext"
    tm.mkdir()
    (tm / "background.js").write_text("// v1", encoding="utf-8")
    (tm / "manifest.json").write_text(json.dumps({"background": {"service_worker": "background.js"}}), encoding="utf-8")
    t1 = ag.doi_ten_nen_theo_ban(str(tm))
    assert t1.startswith("nen-") and (tm / t1).read_text(encoding="utf-8") == "// v1"
    assert json.loads((tm / "manifest.json").read_text(encoding="utf-8"))["background"]["service_worker"] == t1
    (tm / "background.js").write_text("// v2", encoding="utf-8")
    t2 = ag.doi_ten_nen_theo_ban(str(tm))
    assert t2 != t1 and not (tm / t1).exists()
