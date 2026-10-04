"""Chế độ PHIÊN — 5 kênh / 1 VPS, bước A (18/09/2026, xem vm/KE-HOACH.md).

Quyết định chủ dự án: VPS nhiều kênh KHÔNG giữ 5 trình duyệt sống 24/7 nữa —
mỗi kênh một PHIÊN/ngày, ngay trước giờ đăng của nó: mở trình duyệt kênh đó
→ quét Studio + trang chủ → đăng ĐÚNG kênh đó (một lượt) → trả lời cmt ĐÚNG
kênh đó (một lượt) → đóng trình duyệt → sang kênh kế, không phiên nào chồng
lên phiên nào. Các bài dưới chốt: giờ mục tiêu tính từ kế hoạch đăng (trừ
lùi phút, hoặc mốc mặc định nếu kênh không có gì đăng hôm nay), hàng đợi
MỘT-LÚC-MỘT-KÊNH (hai kênh cùng phút → tuần tự, không song song), thứ tự
các bước trong một phiên (quét → đăng → cmt → đóng), tool con hỗ trợ
"--kenh X --mot-lan", và máy MỘT kênh (nếp cũ, mọi VM đang sống) KHÔNG đổi
hành vi trừ khi chủ dự án tự ép `che_do_phien: true`.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
import time
import types
from pathlib import Path

from core import ke_hoach_dang as kh
from core import vm_cai_dat
from core.chi_so_ytb.tram import Tram

GOC = Path(__file__).resolve().parent.parent


def _nap(ten_mod, duong):
    spec = importlib.util.spec_from_file_location(ten_mod, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nap_agent():
    return _nap("vm_agent_phien", GOC / "vm" / "agent.py")


def _dong_ke_hoach(ma, ngay, gio, san_sang="x", da_dang=""):
    """Một dòng đúng khuôn `core/ke_hoach_dang.COT`."""
    return [ma, ngay, gio, "tiêu đề " + ma, "", "", "", "", "", "", san_sang, da_dang, ""]


def _csv(cot, hang):
    buf = io.StringIO()
    but = csv.writer(buf)
    but.writerow(list(cot))
    for d in hang:
        but.writerow(d)
    return buf.getvalue()


def _tai_ham_thuan(tep, ten_ham, ten_ham_ke_tiep):
    """Trích MỘT hàm thuần từ `vm/<tep>` bằng cắt chuỗi + exec — tránh nạp cả
    module (đụng pyautogui/ổ cứng thật khi import), cùng kiểu
    `tests/test_vm_nhieu_kenh.py::TestGatingTuDangVaTuTraLoi` đã dùng."""
    src = (GOC / "vm" / tep).read_text(encoding="utf-8")
    khoi = src.split("def " + ten_ham)[1].split("\ndef " + ten_ham_ke_tiep)[0]
    ns: dict = {}
    exec("def " + ten_ham + khoi, ns)  # noqa: S102 — cắt mã nguồn của chính kho, không phải đồ lạ
    return ns[ten_ham]


class TestCheDoPhienBat:
    def test_tu_dong_theo_so_kenh(self):
        agent = _nap_agent()
        assert agent.che_do_phien_bat({"kenh": "A"}) is False, \
            "một kênh (nếp cũ) -> KHÔNG tự bật, VM đang sống không đổi hành vi"
        assert agent.che_do_phien_bat({"cac_kenh": ["A", "B"]}) is True, \
            ">=2 kênh (một VPS nhiều kênh) -> tự bật"
        assert agent.che_do_phien_bat({}) is False

    def test_tool_ep_tay_thang_tu_dong(self):
        agent = _nap_agent()
        assert agent.che_do_phien_bat({"cac_kenh": ["A", "B"]}, {"che_do_phien": False}) is False
        assert agent.che_do_phien_bat({"kenh": "A"}, {"che_do_phien": True}) is True
        # None (chưa có tool nào ép) -> vẫn về tự động theo số kênh
        assert agent.che_do_phien_bat({"kenh": "A"}, {"che_do_phien": None}) is False


class TestGioDangSomNhatHomNay:
    def test_bo_qua_chua_san_sang_da_dang_va_ngay_khac(self):
        agent = _nap_agent()
        cot = list(kh.COT)
        hang = [
            _dong_ke_hoach("0001", "18/09/2026", "20:00", san_sang=""),        # chưa duyệt -> bỏ
            _dong_ke_hoach("0002", "18/09/2026", "10:00", da_dang="ĐÃ ĐĂNG"),  # đã đăng -> bỏ
            _dong_ke_hoach("0003", "18/09/2026", "19:00"),                     # SỚM NHẤT hợp lệ
            _dong_ke_hoach("0004", "18/09/2026", "21:00"),                     # muộn hơn -> không thắng
            _dong_ke_hoach("0005", "19/09/2026", "05:00"),                     # ngày khác -> bỏ
        ]
        chu = _csv(cot, hang)
        assert agent.gio_dang_som_nhat_hom_nay(chu, (2026, 9, 18)) == "19:00"

    def test_khong_co_gi_dang_hom_nay(self):
        agent = _nap_agent()
        assert agent.gio_dang_som_nhat_hom_nay("", (2026, 9, 18)) == ""
        cot = list(kh.COT)
        chu = _csv(cot, [_dong_ke_hoach("0001", "19/09/2026", "08:00")])
        assert agent.gio_dang_som_nhat_hom_nay(chu, (2026, 9, 18)) == ""

    def test_chap_nhan_dinh_dang_ngay_iso(self):
        agent = _nap_agent()
        cot = list(kh.COT)
        chu = _csv(cot, [_dong_ke_hoach("0001", "2026-09-18", "09:00")])
        assert agent.gio_dang_som_nhat_hom_nay(chu, (2026, 9, 18)) == "09:00"


class TestGioPhienMucTieu:
    def test_lui_theo_phut(self):
        agent = _nap_agent()
        assert agent.gio_phien_muc_tieu("19:00", 60, "07:30") == "18:00"
        assert agent.gio_phien_muc_tieu("19:00", 90, "07:30") == "17:30"

    def test_fallback_khi_khong_co_gi_dang(self):
        agent = _nap_agent()
        assert agent.gio_phien_muc_tieu("", 60, "07:30") == "07:30"
        assert agent.gio_phien_muc_tieu(None, None, None) == "07:30"

    def test_khong_lui_qua_nua_dem_hom_truoc(self):
        agent = _nap_agent()
        assert agent.gio_phien_muc_tieu("00:20", 60, "07:30") == "00:00"


class TestDenGioPhien:
    def test_den_gio_chua_chay_hom_nay(self):
        agent = _nap_agent()
        luc = time.mktime((2026, 9, 18, 18, 5, 0, 0, 0, -1))
        assert agent.den_gio_phien("18:00", "", luc)
        assert not agent.den_gio_phien("18:00", "2026-09-18", luc), "đã chạy hôm nay thì thôi"
        som = time.mktime((2026, 9, 18, 17, 0, 0, 0, 0, -1))
        assert not agent.den_gio_phien("18:00", "", som), "chưa tới giờ thì chưa"
        assert not agent.den_gio_phien("", "", luc)


class TestMucTieuPhienQuaTram:
    def test_tinh_mot_lan_roi_cat_vao_trang_thai_khong_hoi_mang_lai(self, tmp_path):
        goc = str(tmp_path)
        (tmp_path / "CHANNEL" / "TL4-T7").mkdir(parents=True)
        hom_nay_dd = time.strftime("%d/%m/%Y")
        kh.luu_bang(goc, "TL4-T7", [_dong_ke_hoach("0001", hom_nay_dd, "19:00")])
        vm_cai_dat.luu(goc, "TL4-T7", gio_quet="")
        tram = Tram(cong=0, goc=goc)
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            agent = _nap_agent()
            cau_hinh = {"thu_muc_du_lieu": goc}
            ch_kenh = {"tram": dia_chi, "phien_truoc_phut": 60, "gio_phien": "07:30"}
            muc_tieu = agent._muc_tieu_phien_hom_nay(cau_hinh, ch_kenh, "TL4-T7")
            assert muc_tieu == "18:00"
        finally:
            tram.tat()
        # trạm đã TẮT — mốc phải ra ĐÚNG như cũ, không đụng mạng nữa
        assert agent._muc_tieu_phien_hom_nay(cau_hinh, ch_kenh, "TL4-T7") == "18:00"

    def test_tram_tat_va_chua_co_mac_thi_tra_rong_khong_cat_bua(self, tmp_path):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        ch_kenh = {"tram": "http://127.0.0.1:1"}   # không ai nghe cổng này
        assert agent._muc_tieu_phien_hom_nay(cau_hinh, ch_kenh, "TL4-T7") == ""


class TestHangDoiPhien:
    def test_hai_kenh_cung_gio_chi_chay_mot_roi_tuan_tu(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc = str(tmp_path)
        cau_hinh = {"thu_muc_du_lieu": goc}
        hom_nay = time.strftime("%Y-%m-%d")
        # Cả hai kênh đã có mục tiêu CẤT SẴN (00:00 — chắc chắn đã tới giờ);
        # không cần trạm sống vì mốc đã có trong trang-thai.json.
        agent._luu_trang_thai(cau_hinh, **{
            "phien_muc_tieu@A@" + hom_nay: "00:00",
            "phien_muc_tieu@B@" + hom_nay: "00:00",
        })
        goi = []
        monkeypatch.setattr(agent, "chay_mot_phien",
                            lambda ch_may, ch_kenh, kenh: goi.append(kenh) or {"kenh": kenh})
        hieu_luc = {"A": {"tram": "x"}, "B": {"tram": "x"}}
        assert agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"]) is True
        assert goi == ["A"], "hai kênh đến giờ cùng lúc -> CHỈ một chạy, không song song"
        assert agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"]) is True
        assert goi == ["A", "B"], "nhịp kế -> tới lượt kênh còn lại"
        assert agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"]) is False, \
            "cả hai đã chạy hôm nay -> không còn gì để làm"

    def test_som_hon_thang_truoc(self, tmp_path, monkeypatch):
        """Mục tiêu sớm hơn phải được chọn trước, dù đứng SAU trong danh sách kênh."""
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        hom_nay = time.strftime("%Y-%m-%d")
        agent._luu_trang_thai(cau_hinh, **{
            "phien_muc_tieu@B@" + hom_nay: "00:00",
            "phien_muc_tieu@A@" + hom_nay: "00:01",
        })
        goi = []
        monkeypatch.setattr(agent, "chay_mot_phien",
                            lambda ch_may, ch_kenh, kenh: goi.append(kenh) or {"kenh": kenh})
        hieu_luc = {"A": {"tram": "x"}, "B": {"tram": "x"}}
        agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"])
        assert goi == ["B"], "B (00:00) đến giờ trước A (00:01) dù đứng sau trong danh sách"

    def test_khong_kenh_nao_den_gio_thi_khong_lam_gi(self, tmp_path):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        assert agent.chay_hang_doi_phien(cau_hinh, {}, []) is False

    def test_tu_chua_mot_lan_khi_phien_hut_chrome_nhung_nay_da_tim_thay(
            self, tmp_path, monkeypatch):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        hom_nay = time.strftime("%Y-%m-%d")
        agent._luu_trang_thai(cau_hinh, **{
            "phien_cuoi@A": hom_nay,
            "phien_muc_tieu@A@" + hom_nay: "00:00",
            "phien_ket_qua@A": {
                "quet_studio": "lỗi: không thấy Chrome của kênh",
                "quet_trang_chu": "lỗi: không thấy Chrome của kênh",
                "dang": "đăng: xong",
            },
        })
        monkeypatch.setattr(agent, "tim_chrome", lambda _ch: "C:/A/A.exe")
        goi = []
        monkeypatch.setattr(agent, "chay_lai_du_lieu",
                            lambda _may, _ch, kenh: goi.append(kenh) or {
                                "kenh": kenh, "quet_studio": "ok", "quet_trang_chu": "ok"})
        monkeypatch.setattr(agent, "chay_mot_phien",
                            lambda *_a: (_ for _ in ()).throw(
                                AssertionError("tự chữa dữ liệu không được đăng/cmt lần hai")))

        # 30/09/2026: phiên không quét nữa → hàng đợi phiên KHÔNG tự chữa dữ liệu;
        # việc QUÉT NGÀY (`chay_quet_ngay`) tự thử lại trong ngày.
        assert agent.chay_hang_doi_phien(cau_hinh, {"A": {}}, ["A"]) is False
        assert goi == [], "hàng đợi phiên không còn quét lại dữ liệu"

    def test_lan_thu_mot_giay_duoc_xep_lai_khi_da_sua_thoi_gian_cho(
            self, tmp_path, monkeypatch):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        hom_nay = time.strftime("%Y-%m-%d")
        agent._luu_trang_thai(cau_hinh, **{
            "phien_cuoi@A": hom_nay,
            "thu_lai_du_lieu@A@" + hom_nay: "đã thử theo cấu hình cũ",
            "phien_ket_qua@A": {
                "thu_lai_du_lieu": hom_nay + " 12:00:00",
                "ket_thuc": hom_nay + " 12:00:02",
                "quet_studio": "đã mở Studio",
            },
        })
        monkeypatch.setattr(agent, "tim_chrome", lambda _ch: "C:/A/A.exe")
        assert agent.can_thu_lai_du_lieu(
            cau_hinh, {"cho_quet_giay": 480}, "A", hom_nay) is True


def test_agent_va_san_xuat_dung_chung_khoa_toan_vps(tmp_path, monkeypatch):
    agent = _nap_agent()
    vm = tmp_path / "vm"
    vm.mkdir()
    (tmp_path / "vps.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(agent, "GOC", str(vm))
    agent._KHOA_MAY_DANG_GIU = False
    assert agent.giu_khoa_may_chung() is True
    khoa = tmp_path / "workspace" / "tu-chay" / ".khoa-may"
    assert khoa.is_file()
    assert agent.giu_khoa_may_chung() is True
    agent.nha_khoa_may_chung()
    assert not khoa.exists()


def test_phien_chi_thanh_cong_khi_hai_bang_du_lieu_da_ve_hom_nay(tmp_path, monkeypatch):
    agent = _nap_agent()
    vm = tmp_path / "vm"
    cs = tmp_path / "CHANNEL" / "A" / "chi-so"
    vm.mkdir()
    cs.mkdir(parents=True)
    (tmp_path / "vps.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(agent, "GOC", str(vm))
    monkeypatch.setattr(agent, "_kenh_da_co_video", lambda k: True)   # kênh đã có video: luật đủ số liệu như cũ
    assert agent._du_lieu_kenh_da_ve_hom_nay({}, "A") is False
    monkeypatch.setattr(agent, "_kenh_da_co_video", lambda k: False)  # 04/10: kênh mới chưa có video → không đòi
    assert agent._du_lieu_kenh_da_ve_hom_nay({}, "A") is None
    monkeypatch.setattr(agent, "_kenh_da_co_video", lambda k: True)
    (cs / "bang-tom-tat.csv").write_text("Video\n", encoding="utf-8")
    (cs / "kenh-theo-ngay.csv").write_text("Ngày\n", encoding="utf-8")
    assert agent._du_lieu_kenh_da_ve_hom_nay({}, "A") is True


def test_thieu_bang_du_lieu_thi_tu_xep_mot_lan_sua(tmp_path, monkeypatch):
    agent = _nap_agent()
    vm = tmp_path / "vm"
    (tmp_path / "CHANNEL" / "A" / "chi-so").mkdir(parents=True)
    vm.mkdir()
    (tmp_path / "vps.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(agent, "GOC", str(vm))
    monkeypatch.setattr(agent, "_kenh_da_co_video", lambda k: True)   # kênh đã có video: luật đủ số liệu như cũ
    monkeypatch.setattr(agent, "tim_chrome", lambda _ch: "C:/A/A.exe")
    hom_nay = time.strftime("%Y-%m-%d")
    cau_hinh = {}
    monkeypatch.setattr(agent, "_doc_trang_thai", lambda _ch: {
        "phien_cuoi@A": hom_nay, "phien_ket_qua@A": {}})
    assert agent.can_thu_lai_du_lieu(cau_hinh, {}, "A", hom_nay) is True


class TestMotPhien:
    def test_thu_tu_quet_dang_cmt_dong(self, monkeypatch):
        """30/09/2026: phiên CHỈ đăng + bình luận — không quét Studio/trang chủ."""
        agent = _nap_agent()
        thu_tu = []
        cam = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("phiên không được quét"))
        monkeypatch.setattr(agent, "quet_studio", cam)
        monkeypatch.setattr(agent, "quet_trang_chu", cam)
        monkeypatch.setattr(agent, "lay_loi_thoai", cam)
        monkeypatch.setattr(agent, "_chay_mot_lan",
                            lambda duong, kenh, nhan, han_giay: thu_tu.append(nhan) or (nhan + ": ok", 0))
        monkeypatch.setattr(agent, "dong_chrome_kenh",
                            lambda ch: thu_tu.append("dong_chrome"))
        kq = agent.chay_mot_phien({}, {"kenh": "TL4-T7"}, "TL4-T7")
        assert thu_tu == ["đăng", "trả lời cmt", "dong_chrome"]
        assert kq["kenh"] == "TL4-T7"
        assert kq["dang"] == "đăng: ok" and kq["cmt"] == "trả lời cmt: ok"

    def test_mot_buoc_hong_khong_chan_cac_buoc_sau(self, monkeypatch):
        agent = _nap_agent()
        thu_tu = []

        def _no(ch):
            raise RuntimeError("Chrome không thấy")

        monkeypatch.setattr(agent, "_mo_chrome_viec_dang", _no)
        monkeypatch.setattr(agent, "co_token_oauth", lambda k: True)
        monkeypatch.setattr(agent, "_chay_mot_lan",
                            lambda duong, kenh, nhan, han_giay, **_k: thu_tu.append(nhan) or ("ok", 0))
        monkeypatch.setattr(agent, "dong_chrome_kenh",
                            lambda ch: thu_tu.append("dong_chrome"))
        agent.chay_mot_phien({}, {"kenh": "TL4-T7", "tu_dang": True}, "TL4-T7")
        assert thu_tu == ["đăng", "trả lời cmt", "dong_chrome"], \
            "mở Chrome hỏng vẫn phải đi tiếp tới đăng/cmt/đóng"

    def test_phien_chep_ket_qua_quet_ngay_cho_giao_dien(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        agent._luu_trang_thai(cau_hinh, **{"quet_ngay_ket@A": {
            "quet_studio": "tiện ích báo xong lượt 1", "quet_trang_chu": "ok",
            "ket_thuc": "2026-09-30 02:30:00"}})
        monkeypatch.setattr(agent, "_chay_mot_lan", lambda *a, **k: ("ok", 0))
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda ch: None)
        kq = agent.chay_mot_phien(cau_hinh, {"kenh": "A"}, "A")
        assert kq["quet_studio"] == "tiện ích báo xong lượt 1"
        assert kq["quet_ngay"] == "2026-09-30 02:30:00"

    def test_tu_chua_chi_quet_du_lieu_roi_dong_chrome(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        thu_tu = []
        monkeypatch.setattr(agent, "quet_studio",
                            lambda ch: thu_tu.append("studio") or "studio ok")
        monkeypatch.setattr(agent, "quet_trang_chu",
                            lambda ch: thu_tu.append("trang_chu") or "trang chủ ok")
        monkeypatch.setattr(agent, "dong_chrome_kenh",
                            lambda ch: thu_tu.append("dong"))
        ket = agent.chay_lai_du_lieu(cau_hinh, {"kenh": "A"}, "A")
        assert thu_tu == ["studio", "trang_chu", "dong"]
        assert ket["quet_studio"] == "studio ok"


class TestChayMotLan:
    def test_xong_va_qua_han(self, tmp_path):
        """29/09/2026 (Việc C): trả `(câu tóm tắt, mã thoát)` — trước đó chỉ
        trả câu chữ, `chon_duong_dang` không có gì để phân biệt "DOM báo mã 3
        thật" với "tiến trình không mở được được"."""
        agent = _nap_agent()
        script = tmp_path / "con_dang.py"   # KHÔNG đặt "con.py" — "CON" là tên
                                             # thiết bị dành riêng của Windows.
        script.write_text(
            "import sys, time\n"
            "assert sys.argv[1:] == ['--kenh', 'TL4-T7', '--mot-lan']\n"
            "time.sleep(0.05)\n", encoding="utf-8")
        ra, ma = agent._chay_mot_lan(str(script), "TL4-T7", "đăng", han_giay=10)
        assert ra.startswith("đăng: xong"), ra
        assert ma == 0

        script2 = tmp_path / "cham.py"
        script2.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
        ra2, ma2 = agent._chay_mot_lan(str(script2), "TL4-T7", "đăng", han_giay=0.2)
        assert "QUÁ HẠN" in ra2
        assert ma2 == agent.MA_QUA_HAN

    def test_khong_thay_tep_thi_noi_that(self):
        agent = _nap_agent()
        ra, ma = agent._chay_mot_lan("", "TL4-T7", "đăng", han_giay=5)
        assert "không thấy" in ra
        assert ma == agent.MA_KHONG_CHAY

    def test_them_co_dong_lenh_duoc_chuyen_nguyen(self, tmp_path):
        """`co_gi_them` thay `--mot-lan` mặc định — máy đăng DOM cần thêm
        `--kiem-dom`/`--trong-phien`."""
        agent = _nap_agent()
        script = tmp_path / "con_dom.py"
        script.write_text(
            "import sys\n"
            "assert sys.argv[1:] == ['--kenh', 'TL1-T7', '--kiem-dom', '--trong-phien'], sys.argv\n",
            encoding="utf-8")
        ra, ma = agent._chay_mot_lan(str(script), "TL1-T7", "kiểm DOM", han_giay=10,
                                     co_gi_them=("--kiem-dom", "--trong-phien"))
        assert ma == 0, ra


class TestChonDuongDang:
    """Hàm thuần mục 8 bản thiết kế: cach_dang + mã thoát DOM + có desktop
    → "xong" | "anh" (lùi) | "dung" (không lùi)."""

    def test_cach_anh_luon_di_thang_anh(self):
        agent = _nap_agent()
        assert agent.chon_duong_dang("anh", None, True) == "anh"
        assert agent.chon_duong_dang("anh", 3, True) == "anh"

    def test_ma_0_la_xong_bat_ke_cach(self):
        agent = _nap_agent()
        assert agent.chon_duong_dang("dom", 0, False) == "xong"
        assert agent.chon_duong_dang("tu_dong", 0, False) == "xong"

    def test_cach_dom_khong_tu_lui(self):
        """Chủ dự án đã ép CHỈ dùng DOM — hỏng thì dừng, không lén lùi ảnh."""
        agent = _nap_agent()
        assert agent.chon_duong_dang("dom", 3, True) == "dung"
        assert agent.chon_duong_dang("dom", 1, True) == "dung"
        assert agent.chon_duong_dang("dom", 4, True) == "dung"

    def test_tu_dong_lui_dung_ma_3_va_co_desktop(self):
        agent = _nap_agent()
        assert agent.chon_duong_dang("tu_dong", 3, True) == "anh"
        assert agent.chon_duong_dang("tu_dong", 3, False) == "dung", \
            "mã 3 nhưng KHÔNG desktop — đường ảnh cũng không dùng được, đừng lùi"

    def test_tu_dong_ma_1_va_4_khong_lui(self):
        """Mã 1 = đã chạm kênh (có videoId) — lùi là đăng đôi. Mã 4 = bị chặn
        an toàn (van IPv4/khoá) — lùi cũng vấp đúng cửa đó."""
        agent = _nap_agent()
        assert agent.chon_duong_dang("tu_dong", 1, True) == "dung"
        assert agent.chon_duong_dang("tu_dong", 4, True) == "dung"


class TestKiemDomDauPhienVaDangTheoCachDang:
    """chay_mot_phien nối với cach_dang của kênh (Việc C, 29/09/2026)."""

    def test_cach_anh_khong_goi_kiem_dom(self, monkeypatch):
        agent = _nap_agent()
        thu_tu = []
        monkeypatch.setattr(agent, "quet_studio", lambda ch: thu_tu.append("studio") or "ok")
        monkeypatch.setattr(agent, "quet_trang_chu", lambda ch: thu_tu.append("trang_chu") or "ok")
        monkeypatch.setattr(agent, "_chay_mot_lan",
                            lambda duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",):
                                thu_tu.append(nhan) or (nhan + ": ok", 0))
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda ch: thu_tu.append("dong"))
        agent.chay_mot_phien({}, {"kenh": "TL4-T7", "cach_dang": "anh"}, "TL4-T7")
        assert "kiểm DOM" not in thu_tu
        assert thu_tu == ["đăng", "trả lời cmt", "dong"]

    def test_cach_tu_dong_goi_kiem_dom_dau_phien_va_dang_qua_dom(self, monkeypatch):
        agent = _nap_agent()
        thu_tu = []
        goi_them = []
        monkeypatch.setattr(agent, "quet_studio", lambda ch: thu_tu.append("studio") or "ok")
        monkeypatch.setattr(agent, "quet_trang_chu", lambda ch: thu_tu.append("trang_chu") or "ok")

        def _chay(duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",)):
            thu_tu.append(nhan)
            goi_them.append((nhan, tuple(co_gi_them)))
            if nhan == "đăng (DOM)":
                return "đăng (DOM): xong (mã 0)", 0
            return nhan + ": ok", 0

        monkeypatch.setattr(agent, "_chay_mot_lan", _chay)
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda ch: thu_tu.append("dong"))
        kq = agent.chay_mot_phien({}, {"kenh": "TL1-T7", "cach_dang": "tu_dong"}, "TL1-T7")
        assert thu_tu == ["kiểm DOM", "đăng (DOM)", "trả lời cmt", "dong"]
        assert ("kiểm DOM", ("--kiem-dom", "--trong-phien")) in goi_them
        assert ("đăng (DOM)", ("--mot-lan", "--trong-phien")) in goi_them
        assert kq["dang"] == "đăng (DOM): xong (mã 0)"

    def test_cach_tu_dong_ma_3_co_desktop_thi_lui_anh(self, monkeypatch):
        agent = _nap_agent()
        thu_tu = []
        monkeypatch.setattr(agent, "quet_studio", lambda ch: "ok")
        monkeypatch.setattr(agent, "quet_trang_chu", lambda ch: "ok")
        monkeypatch.setattr(agent, "co_desktop_dau_vao", lambda: True)

        def _chay(duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",)):
            thu_tu.append(nhan)
            if nhan == "đăng (DOM)":
                return "đăng (DOM): mã 3", 3
            return nhan + ": ok", 0

        monkeypatch.setattr(agent, "_chay_mot_lan", _chay)
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda ch: None)
        kq = agent.chay_mot_phien({}, {"kenh": "TL1-T7", "cach_dang": "tu_dong"}, "TL1-T7")
        assert "đăng (ảnh, lùi từ DOM)" in thu_tu, "mã 3 + có desktop -> phải lùi đường ảnh"
        assert "lùi từ DOM" in kq["dang"] or "đăng (ảnh" in kq["dang"]

    def test_cach_tu_dong_ma_1_khong_lui(self, monkeypatch):
        """Đã chạm kênh (mã 1) — không được lùi, kẻo đăng đôi."""
        agent = _nap_agent()
        thu_tu = []
        monkeypatch.setattr(agent, "quet_studio", lambda ch: "ok")
        monkeypatch.setattr(agent, "quet_trang_chu", lambda ch: "ok")
        monkeypatch.setattr(agent, "co_desktop_dau_vao", lambda: True)

        def _chay(duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",)):
            thu_tu.append(nhan)
            if nhan == "đăng (DOM)":
                return "đăng (DOM): mã 1", 1
            return nhan + ": ok", 0

        monkeypatch.setattr(agent, "_chay_mot_lan", _chay)
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda ch: None)
        agent.chay_mot_phien({}, {"kenh": "TL1-T7", "cach_dang": "tu_dong"}, "TL1-T7")
        assert "đăng (ảnh, lùi từ DOM)" not in thu_tu


class TestDongChromeKenh:
    def test_van_ipv4_mo_thi_dung_im(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        (tmp_path / "van-ipv4.json").write_text("{}", encoding="utf-8")
        goi = []
        monkeypatch.setattr(agent, "tim_chrome", lambda ch: goi.append(1) or "x.exe")
        agent.dong_chrome_kenh({})
        assert not goi, "van IPv4 đang mở -> agent đứng ngoài, không đụng Chrome"

    def test_gui_browser_close_cong_dong_sach_thi_khong_taskkill(self, monkeypatch):
        """Việc C, 29/09/2026: `Browser.close` tự đóng cổng sạch (Chrome tự
        thoát bình thường, không crash) — KHÔNG được taskkill nữa. Taskkill
        ngay sau Browser.close (nếp cũ, "Lỗi 2" thiết kế) làm Chrome coi như
        bị giết đột ngột, lần mở kế hiện hộp "Restore pages?"."""
        agent = _nap_agent()
        da_goi = {"url": [], "ws": [], "taskkill": []}

        class _TraLoi:
            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def read(self):
                return json.dumps({"webSocketDebuggerUrl": "ws://kenh-a"}).encode()

            def close(self):
                pass

        def _urlopen(url, timeout=0):
            da_goi["url"].append((url, timeout))
            if len(da_goi["url"]) == 1:
                return _TraLoi()
            raise OSError("cổng đã đóng")   # mọi lần hỏi SAU: cổng đã đóng sạch

        class _WS:
            def send(self, chu):
                da_goi["ws"].append(json.loads(chu))

            def close(self):
                pass

        monkeypatch.setattr(agent, "van_ipv4_mo", lambda: False)
        monkeypatch.setattr(agent, "tim_chrome", lambda _ch: "C:/TL/A/A.exe")
        monkeypatch.setattr(agent, "_cong_devtools", lambda _ch: 9307)
        monkeypatch.setattr(agent.urllib.request, "urlopen", _urlopen)
        monkeypatch.setitem(sys.modules, "websocket", types.SimpleNamespace(
            create_connection=lambda *_a, **_kw: _WS()))
        monkeypatch.setattr(agent.subprocess, "run",
                            lambda cmd, **_kw: da_goi["taskkill"].append(cmd))
        monkeypatch.setattr(agent.time, "sleep", lambda _s: None)

        agent.dong_chrome_kenh({"kenh": "A"})

        assert da_goi["url"][0][0].endswith(":9307/json/version")
        assert da_goi["ws"] == [{"id": 1, "method": "Browser.close"}]
        assert da_goi["taskkill"] == [], \
            "cổng đã tự đóng sạch — taskkill là LƯỚI CUỐI, không phải bước mặc định"

    def test_cong_khong_dong_sau_10s_thi_taskkill_la_luoi_cuoi(self, monkeypatch):
        """Chrome kẹt (không tự thoát dù đã gửi Browser.close) — taskkill vẫn
        phải chạy, nhưng CHỈ SAU khi đã chờ hết 10 giây (thứ tự đảo của Việc
        C), không phải ngay sau Browser.close như nếp cũ."""
        agent = _nap_agent()
        thu_tu = []

        class _TraLoi:
            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def read(self):
                return json.dumps({"webSocketDebuggerUrl": "ws://kenh-a"}).encode()

            def close(self):
                pass

        def _urlopen(url, timeout=0):
            thu_tu.append("url")
            return _TraLoi()   # cổng KHÔNG BAO GIỜ đóng — Chrome kẹt

        class _WS:
            def send(self, chu):
                thu_tu.append("ws")

            def close(self):
                pass

        monkeypatch.setattr(agent, "van_ipv4_mo", lambda: False)
        monkeypatch.setattr(agent, "tim_chrome", lambda _ch: "C:/TL/A/A.exe")
        monkeypatch.setattr(agent, "_cong_devtools", lambda _ch: 9307)
        monkeypatch.setattr(agent.urllib.request, "urlopen", _urlopen)
        monkeypatch.setitem(sys.modules, "websocket", types.SimpleNamespace(
            create_connection=lambda *_a, **_kw: _WS()))
        monkeypatch.setattr(agent.subprocess, "run",
                            lambda cmd, **_kw: thu_tu.append("taskkill"))
        monkeypatch.setattr(agent.time, "sleep", lambda _s: None)  # bài kiểm không chờ thật 10s

        agent.dong_chrome_kenh({"kenh": "A"})

        assert thu_tu[-1] == "taskkill", "taskkill phải đến SAU cùng, sau khi đã chờ hết hạn"
        assert thu_tu.count("url") >= 20, "phải chờ đủ vòng (≈10s) trước khi bỏ cuộc"
        assert thu_tu.count("taskkill") == 1


class TestKhoaTuToolMoi:
    def test_ba_khoa_moi_co_ca_hai_dau_va_khop_nhau(self):
        agent = _nap_agent()
        from core.vm_cai_dat import KHOA_DIEU_KHIEN

        for khoa in ("che_do_phien", "phien_truoc_phut", "gio_phien"):
            assert khoa in agent.KHOA_TU_TOOL, khoa
            assert khoa in KHOA_DIEU_KHIEN, khoa
        assert set(agent.KHOA_TU_TOOL) == set(KHOA_DIEU_KHIEN)

    def test_cach_dang_co_ca_hai_dau_va_mac_dinh_anh(self):
        """Việc C, 29/09/2026: `cach_dang` phải khớp cả `agent.KHOA_TU_TOOL`
        VÀ `vm_cai_dat.KHOA_DIEU_KHIEN` — thiếu một đầu là tool đổi được núm
        này nhưng agent lặng lẽ bỏ qua (`ap_cai_dat_tool` lọc theo
        `KHOA_TU_TOOL`)."""
        agent = _nap_agent()
        from core.vm_cai_dat import KHOA_DIEU_KHIEN, MAC_DINH

        assert "cach_dang" in agent.KHOA_TU_TOOL
        assert "cach_dang" in KHOA_DIEU_KHIEN
        assert MAC_DINH["cach_dang"] == "anh", \
            "giai đoạn chuyển (quyết định 6) — đừng tự đổi mặc định ở đây"


class TestLegacyKhongDoi:
    def test_mot_kenh_khong_di_qua_hang_doi_phien(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        goi_hang_doi = []
        monkeypatch.setattr(agent, "chay_hang_doi_phien",
                            lambda *a, **k: goi_hang_doi.append(1) or False)
        monkeypatch.setattr(agent, "giu_chrome", lambda ch: None)
        monkeypatch.setattr(agent, "giu_tool_dang", lambda ch: None)
        monkeypatch.setattr(agent, "tim_chrome", lambda ch: "")
        cau_hinh = {"tram": "http://127.0.0.1:1", "kenh": "TL4-T7", "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        assert not goi_hang_doi, "máy một kênh (nếp cũ, VM đang sống) không được đụng hàng đợi phiên"

    def test_nhieu_kenh_tu_dong_di_qua_hang_doi_phien(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        goi_hang_doi = []
        monkeypatch.setattr(agent, "chay_hang_doi_phien",
                            lambda *a, **k: goi_hang_doi.append(1) or False)

        def _khong_duoc_goi(ch):
            raise AssertionError("giu_chrome không được gọi ở chế độ phiên")

        monkeypatch.setattr(agent, "giu_chrome", _khong_duoc_goi)
        monkeypatch.setattr(agent, "giu_tool_dang", _khong_duoc_goi)
        monkeypatch.setattr(agent, "tim_chrome", lambda ch: "")
        cau_hinh = {"tram": "http://127.0.0.1:1", "cac_kenh": ["A", "B"], "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        assert goi_hang_doi == [1]


class TestDongLenhMotLan:
    """`--kenh X --mot-lan` — CLI mà agent.py gọi cho may_dang.py/may_cmt.py."""

    def test_may_dang_doc_co_dong_lenh(self):
        ham = _tai_ham_thuan("may_dang.py", "_doc_co_dong_lenh", "_loc_kenh")
        assert ham(["--kenh", "TL4-T7", "--mot-lan"]) == (True, "TL4-T7")
        assert ham([]) == (False, None)
        assert ham(["--kenh"]) == (False, None), "thiếu giá trị sau --kenh -> None, không nổ"
        assert ham(["--mot-lan"]) == (True, None)

    def test_may_dang_loc_kenh(self):
        ham = _tai_ham_thuan("may_dang.py", "_loc_kenh", "discover_channels")
        ds = [{"code": "A"}, {"code": "B"}]
        assert ham(ds, None) == ds
        assert ham(ds, "") == ds
        assert ham(ds, "B") == [{"code": "B"}]
        assert ham(ds, "C") == []

    def test_may_cmt_doc_co_dong_lenh(self):
        ham = _tai_ham_thuan("may_cmt.py", "_doc_co_dong_lenh", "run_all")
        assert ham(["--kenh", "TL4-T7", "--mot-lan"]) == (True, "TL4-T7")
        assert ham(["--mot-lan"]) == (True, None)
        assert ham(["test", "TL4-T7"]) == (False, None)


class TestCungMay:
    """`may_dang._cung_may` — kênh tự chạy trên VPS (sản xuất + đăng CÙNG một
    máy, xem vm/KE-HOACH-5-KENH.md): gói đã nằm sẵn, bỏ hẳn SMB/tsclient/IPv4
    và bước copy-sang-chỗ-khác (không ai dọn bản sao thừa đó)."""

    def _cung_may(self):
        src = (GOC / "vm" / "may_dang.py").read_text(encoding="utf-8")
        khoi = src.split("def _cung_may")[1].split("\nVAN_IPV4")[0]
        ns: dict = {"os": __import__("os"), "SERVER_DONE_ROOT_GOC": None, "LOCAL_DONE_ROOT": ""}
        exec("def _cung_may" + khoi, ns)
        return ns["_cung_may"]

    def test_cung_duong_thi_cung_may(self):
        ham = self._cung_may()
        assert ham("D:\\AUTO\\done", "D:\\AUTO\\done") is True
        assert ham("D:/AUTO/done/", "D:\\AUTO\\done") is True, "khác kiểu gạch chéo vẫn coi là một"

    def test_duong_local_khong_unc_thi_cung_may(self):
        ham = self._cung_may()
        assert ham("D:\\AUTO\\done", "C:\\Users\\x\\Desktop\\done") is True, \
            "đường ổ đĩa của chính máy (không \\\\server\\...) -> đọc thẳng được"

    def test_duong_unc_thi_khong_phai_cung_may(self):
        ham = self._cung_may()
        assert ham(r"\\tsclient\D\AUTO\done", "C:\\Users\\x\\Desktop\\done") is False
        assert ham(r"\\192.168.88.41\D\AUTO\done", "C:\\Users\\x\\Desktop\\done") is False

    def test_rong_thi_khong_phai_cung_may(self):
        ham = self._cung_may()
        assert ham("", "C:\\Users\\x\\Desktop\\done") is False
        assert ham(None, "C:\\Users\\x\\Desktop\\done") is False
