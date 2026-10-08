"""MHKT: nút Lưu tắt vì phần tử bắt đầu ngoài 20 giây cuối (09/10/2026, TL2-T7).

Studio giả: 2 hàng «Đăng ký» + «Video» đều 19:22:00 – 19:42:00, banner đỏ, Lưu tắt tới
khi cả hai ô bắt đầu ≥ 19:23. Không chạm vm/logs thật."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import may_dang_dom as mdd  # noqa: E402

BANNER_VI = "Bạn chỉ có thể thêm các thành phần trong vòng 20 giây cuối cùng của video"


class TrinhSoanGia:
    def __init__(self, banner=BANNER_VI, gio=None, nhan_enter=True, khong_nhan_gi=False):
        self.banner = banner
        self.hang = ["Đăng ký: kênh", "Video: Phù hợp nhất với người xem"]
        self.gio = gio or [["19:22:00", "19:42:00"], ["19:22:00", "19:42:00"]]
        self.chon = 0
        self.nhan_enter = nhan_enter          # False: Enter không có tác dụng (chỉ Tab nhận)
        self.khong_nhan_gi = khong_nhan_gi
        self.cho_go = None
        self.phim_da = []
        self.da_go = []
        self.dem_luu = 0

    def _loi(self, i):
        d, _ = self.gio[i]
        p = [int(x) for x in d.split(":")]
        return p[0] * 60 + p[1] < 19 * 60 + 23

    def _luu_tat(self):
        return any(self._loi(i) for i in range(len(self.hang)))

    def tim(self, khoa, han=10, hien=True, cho_tat=False, trong=None, thu=0):
        if khoa == "mhkt_luu":
            return {"khoa": khoa, "id": "luu", "tat": self._luu_tat()}
        if khoa == "mhkt_phan_tu":
            return {"khoa": khoa, "id": "hang#%d" % thu, "so": len(self.hang), "thu": thu}
        if khoa in ("mhkt_gio_dau", "mhkt_gio_cuoi"):
            return {"khoa": khoa, "id": khoa, "tat": False}
        if khoa == "mhkt_modal":
            return {"khoa": khoa, "id": "modal"}
        if khoa == "mhkt_phan_tu_loi":
            return {"khoa": khoa, "id": "loi", "so": 1} if self._luu_tat() else None
        return None

    def co(self, khoa, **kw):
        return self.tim(khoa) is not None

    def doc_chu(self, x, han=5):
        khoa = x["khoa"] if isinstance(x, dict) else x
        if khoa == "mhkt_modal":
            return "Màn hình kết thúc " + (self.banner if self._luu_tat() else "") + " Hủy thay đổi Lưu"
        if khoa == "mhkt_phan_tu":
            return self.hang[int(str(x["id"]).split("#")[1])]
        if khoa == "mhkt_gio_dau":
            return self.gio[self.chon][0]
        if khoa == "mhkt_gio_cuoi":
            return self.gio[self.chon][1]
        return ""

    def doc_tat_ca(self, khoa):
        if khoa == "mhkt_phan_tu_loi":
            return [{"chu": self.hang[i]} for i in range(len(self.hang)) if self._loi(i)]
        return [{"chu": h} for h in self.hang]

    def bam(self, x, hau_dieu_kien=None, han_hau=10, han_tim=10, cho_tat=False):
        khoa = x["khoa"] if isinstance(x, dict) else x
        if khoa == "mhkt_phan_tu":
            self.chon = int(str(x["id"]).split("#")[1])
        if khoa == "mhkt_luu":
            if self._luu_tat():
                raise cdp_studio.LoiThaoTac(khoa, "nút đang bị vô hiệu")
            self.dem_luu += 1
        return x if isinstance(x, dict) else {"khoa": x}

    def go_tho(self, khoa, chu, xoa=True, han_tim=10):
        self.cho_go = (khoa, chu)
        self.da_go.append(chu)

    def phim(self, ten, n=1, modifiers=0):
        self.phim_da.append(ten)
        if not self.cho_go or self.khong_nhan_gi:
            return
        khoa, chu = self.cho_go
        nhan = (ten == "Enter" and self.nhan_enter) or ten == "Tab"
        if nhan and khoa == "mhkt_gio_dau":
            if ":" not in chu:
                chu = "{0}:{1}:{2}".format(chu[:2], chu[2:4], chu[4:6])
            self.gio[self.chon][0] = chu
            self.cho_go = None

    def ghi_bang_chung(self, nhan):
        return {}


def _may(tmp_path, nk):
    return mdd.MayDangDom("TL2-T7", cdp_studio.doc_bo_chon(), lambda: None,
                          mdd.SoVideoId(str(tmp_path / "so.json")), lambda *a, **k: True, str(tmp_path / "DONE"),
                          nhat_ky=nk, bay_gio=lambda: datetime(2026, 10, 9, 4, 5), ngu=lambda s: None,
                          duong_uc=str(tmp_path / "uc.json"), duong_dodang=str(tmp_path / "dodang.json"),
                          han_mhkt=1, thu_muc_chi_so=str(tmp_path / "chi-so"))


class TestGio:
    def test_doi_qua_lai(self):
        assert mdd.gio_sang_giay("19:22:00") == 19 * 60 + 22
        assert mdd.gio_sang_giay("00:05:50") == pytest.approx(5.5)
        assert mdd.gio_sang_giay("1:02:03:00") == 3723
        assert mdd.gio_sang_giay("") is None and mdd.gio_sang_giay("ab:cd") is None
        assert mdd.giay_sang_gio(19 * 60 + 23) == "19:23:00"
        assert mdd.giay_sang_gio(3723, 4) == "1:02:03:00"

    def test_selectors_moi_co_trong_json(self):
        bo = cdp_studio.doc_bo_chon()
        for k in ("mhkt_modal", "mhkt_gio_dau", "mhkt_gio_cuoi", "mhkt_phan_tu_loi"):
            assert bo["phan_tu"][k]["chon"], k
        ct = bo["chu_trang_thai"]["mhkt_loi_20s"]
        assert any("20 giây" in w for w in ct) and any("20 秒" in w for w in ct) and any("20 seconds" in w for w in ct)


class TestSuaGio:
    def test_sua_gio_bat_dau_roi_luu(self, tmp_path):
        nk = []
        m, tr = _may(tmp_path, nk.append), TrinhSoanGia()
        assert m._mhkt_luu(tr, {"ma": "TL2-T7-0021"}, "nhập") is True
        assert tr.gio == [["19:23:00", "19:42:00"]] * 2 and tr.dem_luu == 1
        assert any("19:22:00 → 19:23:00" in s for s in nk), nk

    @pytest.mark.parametrize("banner", ["最後の 20 秒間にのみ要素を追加できます",
                                        "You can only add elements in the last 20 seconds of the video"])
    def test_banner_ja_en(self, tmp_path, banner):
        m, tr = _may(tmp_path, lambda s: None), TrinhSoanGia(banner=banner)
        assert m._mhkt_luu(tr, {"ma": "x"}, "mẫu") is True

    def test_enter_khong_nhan_thi_thu_chu_so_va_tab(self, tmp_path):
        m, tr = _may(tmp_path, lambda s: None), TrinhSoanGia(nhan_enter=False)
        assert m._mhkt_luu(tr, {"ma": "x"}, "mẫu") is True
        assert "Tab" in tr.phim_da

    def test_khong_sua_duoc_thi_van_that_bai_toi_da_2_luot(self, tmp_path):
        nk = []
        m, tr = _may(tmp_path, nk.append), TrinhSoanGia(khong_nhan_gi=True)
        assert m._mhkt_luu(tr, {"ma": "x"}, "mẫu") is False
        assert sum("sửa giờ bắt đầu lượt" in s for s in nk) == 2
        assert tr.dem_luu == 0

    def test_khong_dua_bat_dau_sat_ket_thuc(self, tmp_path):
        m = _may(tmp_path, lambda s: None)
        tr = TrinhSoanGia(gio=[["19:22:00", "19:26:00"], ["19:22:00", "19:26:00"]])
        assert m._mhkt_luu(tr, {"ma": "x"}, "mẫu") is False
        assert tr.da_go == [], "kết thúc − 19 s < bắt đầu hiện tại → không đụng"

    def test_luu_tat_ma_khong_phai_loi_20s_thi_khong_go_gi(self, tmp_path):
        m, tr = _may(tmp_path, lambda s: None), TrinhSoanGia(banner="")
        tr.tim = lambda khoa, **kw: ({"khoa": khoa, "id": "luu", "tat": True} if khoa == "mhkt_luu" else None)
        assert m._mhkt_luu(tr, {"ma": "x"}, "mẫu") is False and tr.da_go == []

    def test_luu_bat_san_thi_khong_sua(self, tmp_path):
        m, tr = _may(tmp_path, lambda s: None), TrinhSoanGia(gio=[["19:24:00", "19:42:00"]] * 2)
        assert m._mhkt_luu(tr, {"ma": "x"}, "mẫu") is True and tr.da_go == []
