"""Tải lên BỔ SUNG trong ngày (29/09/2026): agent tải gói xong SAU phiên sáng,
và máy đăng DOM nhận lịch tương lai trong cửa sổ (bây giờ + biên, + cửa sổ].

Không mạng, không Chrome. Agent được nạp như `tests/test_vm_agent.py`, mọi
đường ghi (GOC, trạng thái, khoá máy) trỏ vào thư mục tạm — KHÔNG đụng
`vm/agent.log`/`vm/trang-thai.json` thật của VPS.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import may_dang_dom as mdd  # noqa: E402


def _nap_agent(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("vm_agent_tbs", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "GOC", str(tmp_path))
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(mod, "ghi", lambda s: None)
    monkeypatch.setattr(mod, "_duong_trang_thai", lambda ch: str(tmp_path / "trang-thai.json"))
    mod._TAI_BO_SUNG["luc"] = 0.0
    return mod


COT = "Mã gói,Ngày đăng,Giờ đăng,Tiêu đề,Mô tả,Thẻ SEO,Link card 1,Link card 2,Link card 3,Link card 4,Sẵn sàng,Trạng thái đăng,Ghi chú"


def _csv(*dong):
    return "\n".join([COT] + [",".join(d) for d in dong]) + "\n"


def _d(ma, ngay, gio, san="x", tt=""):
    return (ma, ngay, gio, "t", "m", "", "", "", "", "", san, tt, "")


# 29/09/2026 12:15 giờ máy
BAY_GIO = time.mktime((2026, 9, 29, 12, 15, 0, 0, 0, -1))


class TestMaCanTaiBoSung:
    def test_loc_cua_so_va_so(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        chu = _csv(_d("M1", "30/09/2026", "20:00"),              # trong cửa sổ
                   _d("M2", "29/09/2026", "13:00"),              # < bây giờ + 2h → để phiên lo
                   _d("M3", "08/10/2026", "20:00"),              # > 7 ngày
                   _d("M4", "30/09/2026", "20:00", tt="ĐÃ ĐĂNG"),
                   _d("M5", "01/10/2026", "20:00", san=""),      # chưa Sẵn sàng
                   _d("M6", "02/10/2026", "20:00"),              # đã có id trong sổ
                   _d("M7", "", ""))
        so = {"TL2-T7/M6": {"video_id": "AAAAAAAAAAA"}}
        assert ag.ma_can_tai_bo_sung(chu, "TL2-T7", so, BAY_GIO, cua_so_ngay=7) == ["M1"]

    def test_goi_hong_de_nhap_duoc_tai_moi(self, tmp_path, monkeypatch):
        # 30/09/2026 TL1-T7-0009: lượt hỏng để nháp, trạm ghi "ĐANG ĐĂNG · nháp …"
        ag = _nap_agent(tmp_path, monkeypatch)
        dd = "ĐANG ĐĂNG · nháp MOlIrxOu6fE"
        chu = _csv(_d("N1", "30/09/2026", "16:00", tt=dd),        # nháp, 1 lần hôm nay → tải mới
                   _d("N2", "30/09/2026", "17:00", tt=dd),        # nháp, đã 2 lần hôm nay → thôi
                   _d("N3", "30/09/2026", "18:00", tt=dd),        # đã hẹn lịch (chưa xác nhận) → thôi
                   _d("N4", "30/09/2026", "20:00"),               # chưa có id → tải
                   _d("N5", "30/09/2026", "21:00", tt="CHƯA XÁC NHẬN LỊCH · X"))
        so = {"TL1-T7/N1": {"video_id": "MOlIrxOu6fE", "trang_thai": "nhap", "lan_tai_moi": 1,
                            "ngay_tai": "2026-09-29"},
              "TL1-T7/N2": {"video_id": "B", "trang_thai": "nhap", "lan_tai_moi": 2, "ngay_tai": "2026-09-29"},
              "TL1-T7/N3": {"video_id": "C", "trang_thai": "da-len-lich", "ngay_tai": "2026-09-29"}}
        assert ag.ma_can_tai_bo_sung(chu, "TL1-T7", so, BAY_GIO) == ["N1", "N4"]
        # hôm sau: lần tải mới tính lại từ 0
        so["TL1-T7/N2"]["ngay_tai"] = "2026-09-28"
        assert ag.ma_can_tai_bo_sung(chu, "TL1-T7", so, BAY_GIO) == ["N1", "N2", "N4"]

    def test_tran_goi_moi_kenh_ngay(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        chu = _csv(_d("A", "30/09/2026", "20:00"), _d("B", "30/09/2026", "21:00"),
                   _d("N", "30/09/2026", "22:00", tt="ĐANG ĐĂNG · nháp X"))
        so = {"K/X{0}".format(i): {"video_id": "v", "trang_thai": "xac-nhan", "ngay_tai": "2026-09-29"}
              for i in range(ag.TAI_LEN_TOI_DA_KENH_NGAY - 1)}
        so["K/N"] = {"video_id": "X", "trang_thai": "nhap", "lan_tai_moi": 1, "ngay_tai": "2026-09-29"}
        # N có id (tính vào trần kênh nhưng không bị trần cắt) → A, B hết chỗ
        assert ag.ma_can_tai_bo_sung(chu, "K", so, BAY_GIO) == ["N"]
        del so["K/X0"]
        assert ag.ma_can_tai_bo_sung(chu, "K", so, BAY_GIO) == ["A", "N"]

    def test_khe_tranh_phut_00(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        assert ag._khe_tai_bo_sung_mo(time.mktime((2026, 9, 29, 12, 15, 0, 0, 0, -1)))
        assert not ag._khe_tai_bo_sung_mo(time.mktime((2026, 9, 29, 12, 57, 0, 0, 0, -1)))
        assert not ag._khe_tai_bo_sung_mo(time.mktime((2026, 9, 29, 13, 3, 0, 0, 0, -1)))


class TestChayTaiBoSung:
    def _chuan_bi(self, tmp_path, monkeypatch, khoa=True, van=False):
        ag = _nap_agent(tmp_path, monkeypatch)
        goi = {"con": [], "chrome": [], "dong": [], "nha": 0}
        monkeypatch.setattr(ag, "van_ipv4_mo", lambda: van)
        monkeypatch.setattr(ag, "giu_khoa_may_chung", lambda **_k: khoa)
        monkeypatch.setattr(ag, "nha_khoa_may_chung", lambda: goi.__setitem__("nha", goi["nha"] + 1))
        monkeypatch.setattr(ag, "tim_chrome", lambda ch: "C:/TL2-T7/TL2-T7.exe")
        monkeypatch.setattr(ag, "_chrome_dang_chay", lambda c: False)
        monkeypatch.setattr(ag, "mo_chrome_kenh", lambda ch, url, c, da_chay=None: goi["chrome"].append(url))
        monkeypatch.setattr(ag, "_cho_devtools", lambda cong, han: "ws://x")
        monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: goi["dong"].append(ch.get("kenh")))

        def chay_con(duong, kenh, nhan, han_giay, co_gi_them=()):
            goi["con"].append((Path(duong).name, kenh, tuple(co_gi_them)))
            return "xong (1 phút, mã 0)", 0
        hieu_luc = {"TL2-T7": {"kenh": "TL2-T7", "tu_dang": True, "cach_dang": "tu_dong"},
                    "TL4-T7": {"kenh": "TL4-T7", "tu_dang": False, "cach_dang": "anh"}}
        ke = {"TL2-T7": _csv(_d("TL2-T7-0001", "30/09/2026", "20:00")),
              "TL4-T7": _csv(_d("TL4-T7-0009", "30/09/2026", "20:00"))}
        return ag, goi, hieu_luc, ke, chay_con

    def test_chay_dung_kenh_dung_co(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch)
        assert ag.chay_tai_bo_sung({}, hl, ["TL4-T7", "TL2-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is True
        assert goi["con"] == [("may_dang_dom.py", "TL2-T7",
                               ("--mot-lan", "--trong-phien", "--cua-so-gio",
                                str(int(ag.CUA_SO_TAI_BO_SUNG_NGAY * 24)), "--bien-gio", "2.0",
                                "--toi-da-ngay", str(ag.TAI_LEN_TOI_DA_KENH_NGAY)))]
        assert goi["chrome"] and goi["dong"] == ["TL2-T7"] and goi["nha"] == 1
        # chu kỳ 25 phút: nhịp kế KHÔNG chạy lại
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO + 60,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False
        tt = json.loads((tmp_path / "trang-thai.json").read_text(encoding="utf-8"))
        assert tt["tai_bo_sung@TL2-T7@2026-09-29"] == 1

    def test_khoa_may_ban_thi_nhuong(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch, khoa=False)
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False
        assert goi["con"] == [] and goi["chrome"] == []

    def test_van_ipv4_thi_khong_mo_chrome(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch, van=True)
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False
        assert goi["chrome"] == [] and goi["con"] == []

    def test_dang_do_thi_hoan(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch)
        (tmp_path / "logs" / "dang-dodang.json").write_text("{}", encoding="utf-8")
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False
        assert goi["con"] == []

    def test_tran_luot_ngay(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch)
        (tmp_path / "trang-thai.json").write_text(
            json.dumps({"tai_bo_sung@TL2-T7@2026-09-29": ag.TAI_BO_SUNG_TOI_DA_LUOT_NGAY}), encoding="utf-8")
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False

    def test_tran_luot_goi_ngay(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch)
        for _ in range(ag.TAI_BO_SUNG_TOI_DA_LUOT_GOI_NGAY):
            ag._TAI_BO_SUNG["luc"] = 0.0
            assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO,
                                       tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is True
        ag._TAI_BO_SUNG["luc"] = 0.0
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False
        tt = json.loads((tmp_path / "trang-thai.json").read_text(encoding="utf-8"))
        assert tt["tai_bo_sung_goi@TL2-T7@2026-09-29"] == {"TL2-T7-0001": 2}

    def test_xoay_vong_cong_bang(self, tmp_path, monkeypatch):
        # 30/09/2026: kênh đứng đầu danh sách không được thắng mãi
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch)
        hl["TL1-T7"] = {"kenh": "TL1-T7", "tu_dang": True, "cach_dang": "tu_dong"}
        ke["TL1-T7"] = _csv(_d("TL1-T7-0012", "01/10/2026", "20:00"))
        ke["TL2-T7"] = _csv(_d("TL2-T7-0001", "30/09/2026", "20:00"), _d("TL2-T7-0002", "30/09/2026", "22:00"))
        tai = lambda ch, k: ke[k]  # noqa: E731
        ag._TAI_BO_SUNG["cuoi"] = {}
        (tmp_path / "trang-thai.json").write_text(json.dumps({"tai_bo_sung@TL2-T7@2026-09-29": 1}),
                                                  encoding="utf-8")
        # TL2 đứng trước nhưng đã chạy 1 lượt → TL1 (0 lượt) trước
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7", "TL1-T7"], bay_gio=BAY_GIO,
                                   tai_ke_hoach=tai, chay_con=cc) is True
        assert goi["con"][-1][1] == "TL1-T7"
        # cùng số lượt (1–1) → kênh lâu chưa chạy nhất (TL2 chưa chạy trong phiên này)
        ag._TAI_BO_SUNG["luc"] = 0.0
        assert ag.chay_tai_bo_sung({}, hl, ["TL1-T7", "TL2-T7"], bay_gio=BAY_GIO + 1600,
                                   tai_ke_hoach=tai, chay_con=cc) is True
        assert goi["con"][-1][1] == "TL2-T7"

    def test_khe_00_khong_chay(self, tmp_path, monkeypatch):
        ag, goi, hl, ke, cc = self._chuan_bi(tmp_path, monkeypatch)
        luc = time.mktime((2026, 9, 29, 20, 1, 0, 0, 0, -1))
        assert ag.chay_tai_bo_sung({}, hl, ["TL2-T7"], bay_gio=luc,
                                   tai_ke_hoach=lambda ch, k: ke[k], chay_con=cc) is False


class TestMayDomCuaSo:
    def _hang(self, ma, ngay, gio, tt="EDIT XONG", kenh="TL2-T7"):
        import nguon_tool as nt
        r = [""] * nt.RONG_DONG
        r[nt.O_MA], r[nt.O_KENH], r[nt.O_TRANG_THAI], r[nt.O_NGAY], r[nt.O_GIO] = ma, kenh, tt, ngay, gio
        return r

    def test_cua_so_nhan_lich_tuong_lai(self):
        bg = datetime(2026, 9, 29, 23, 30)
        hang = [[""] * 64, self._hang("A", "30/09/2026", "20:00"), self._hang("B", "30/09/2026", "01:00"),
                self._hang("C", "07/10/2026", "20:00"), self._hang("D", "30/09/2026", "20:00", tt="ĐÃ ĐĂNG")]
        cs = (timedelta(hours=2), timedelta(hours=168))
        assert [d["ma"] for d in mdd.chon_ma_can_dang(hang, "TL2-T7", bg, cua_so=cs)] == ["A"]
        # không cửa sổ: nếp cũ — chỉ HÔM NAY
        assert mdd.chon_ma_can_dang(hang, "TL2-T7", bg) == []

    def test_tran_tai_moi_ngay(self):
        cac = [{"ma": m} for m in ("A", "B", "C", "D")]
        so = {"TL2-T7/X": {"ngay_tai": "2026-09-29"}, "TL2-T7/Y": {"ngay_tai": "2026-09-28"},
              "TL2-T7/C": {"video_id": "CCCCCCCCCCC", "ngay_tai": "2026-09-29"}}
        # đã tải mới 2 gói hôm nay (X, C) → còn 1 chỗ; C có id nên không tính vào trần
        assert [d["ma"] for d in mdd.gioi_han_tai_moi(cac, so, "TL2-T7", "2026-09-29", 3)] == ["C", "A"]
        assert [d["ma"] for d in mdd.gioi_han_tai_moi(cac, {}, "TL2-T7", "2026-09-29", 3)] == ["A", "B", "C"]
