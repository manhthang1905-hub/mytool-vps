"""`core/che_do_vps.py` — nhận diện MyTool đang chạy trong "chế độ VPS".

Thuần đọc tệp, không mạng, không Qt — chạy dưới hai giây.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from core import che_do_vps


def _ghi_marker(goc: str, du: dict) -> None:
    with open(os.path.join(goc, che_do_vps.TEN_MARKER), "w", encoding="utf-8") as tep:
        json.dump(du, tep)


def _ghi_cai_dat(goc: str, du: dict) -> None:
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w",
             encoding="utf-8") as tep:
        json.dump(du, tep)


class TestLaVps:
    def test_khong_co_tep_thi_khong_phai_vps(self, tmp_path):
        assert che_do_vps.la_vps(str(tmp_path)) is False

    def test_co_tep_thi_la_vps(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.la_vps(str(tmp_path)) is True

    def test_thu_muc_khong_ton_tai_khong_nem_loi(self):
        assert che_do_vps.la_vps(os.path.join("duong", "khong", "co")) is False

    def test_vps_luon_ep_mot_viec_nang(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99) == 1
        assert che_do_vps.gioi_han_theo_loai(
            str(tmp_path), {"image": 64, "video": 24}) == {"image": 1, "video": 1}

    def test_may_thuong_giu_muc_nguoi_dung(self, tmp_path):
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 3) == 3


class TestGioiHanTheoLop:
    """Đợt 1 mục 1.1 — tách chính sách song song theo LỚP việc.

    `lop="nang"` (mặc định) giữ NGUYÊN hành vi cũ: VPS ép về 1. `lop="api"`
    chỉ chờ mạng, không ăn CPU/RAM cục bộ, nên được chạy song song tới
    `tran_api_vps` thay vì bị ép về 1 — đây là nút thắt số 1 lộ trình v3 gỡ.
    """

    def test_khong_truyen_lop_van_la_nang_ep_ve_1(self, tmp_path):
        """Mặc định `lop="nang"` — mọi nơi gọi cũ (chưa sửa) không bị đổi hành vi."""
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99) == 1

    def test_lop_nang_tuong_minh_cung_ep_ve_1(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="nang") == 1

    def test_lop_api_tren_vps_dung_tran_mac_dinh_6(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="api") == 6

    def test_lop_api_khong_vuot_qua_so_luong_xin(self, tmp_path):
        """Xin 3 thì được 3, dù trần cho phép 6 — không tự bơm thêm luồng."""
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 3, lop="api") == 3

    def test_lop_api_doc_tran_tu_cai_dat_json(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        _ghi_cai_dat(str(tmp_path), {"tran_api_vps": 4})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="api") == 4

    def test_lop_api_kep_tran_tren_48(self, tmp_path):
        """30/09/2026: trần kẹp 8 → 48 (số job CHỜ máy chủ, tách khỏi trần
        tải/giải mã). Gõ nhầm 600 vẫn bị kẹp."""
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        _ghi_cai_dat(str(tmp_path), {"tran_api_vps": 600})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="api") == 48

    def test_lop_api_nhan_24_moi_kenh(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        _ghi_cai_dat(str(tmp_path), {"tran_api_vps": 24})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 189, lop="api") == 24
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 1, lop="api") == 1

    def test_lop_api_kep_tran_duoi_1(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        _ghi_cai_dat(str(tmp_path), {"tran_api_vps": 0})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="api") == 1

    def test_lop_api_tep_cai_dat_hong_thi_dung_mac_dinh_6(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        os.makedirs(os.path.join(str(tmp_path), "workspace"), exist_ok=True)
        with open(os.path.join(str(tmp_path), "workspace", "cai-dat.json"),
                 "w", encoding="utf-8") as tep:
            tep.write("{ khong phai json")
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="api") == 6

    def test_lop_api_thieu_khoa_thi_dung_mac_dinh_6(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        _ghi_cai_dat(str(tmp_path), {"mot_khoa_khac": True})
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 99, lop="api") == 6

    def test_may_thuong_khong_bi_anh_huong_boi_lop(self, tmp_path):
        """Không phải VPS — `lop` không có ý nghĩa gì, luôn giữ số người dùng xin."""
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 5, lop="api") == 5
        assert che_do_vps.gioi_han_song_song(str(tmp_path), 5, lop="nang") == 5

    def test_gioi_han_theo_loai_truyen_duoc_lop(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.gioi_han_theo_loai(
            str(tmp_path), {"image": 64, "video": 24}, lop="api") == {
                "image": 6, "video": 6}
        # Mặc định vẫn "nang" — nơi gọi cũ (ui_qt/app.py) không đổi hành vi.
        assert che_do_vps.gioi_han_theo_loai(
            str(tmp_path), {"image": 64, "video": 24}) == {"image": 1, "video": 1}


class TestDoc:
    def test_khong_co_tep_tra_rong(self, tmp_path):
        assert che_do_vps.doc(str(tmp_path)) == {}

    def test_tep_hong_tra_rong(self, tmp_path):
        with open(os.path.join(str(tmp_path), che_do_vps.TEN_MARKER), "w",
                  encoding="utf-8") as tep:
            tep.write("{ khong phai json")
        assert che_do_vps.doc(str(tmp_path)) == {}

    def test_tep_khong_phai_dict_tra_rong(self, tmp_path):
        _ghi_marker(str(tmp_path), [])  # type: ignore[arg-type]
        assert che_do_vps.doc(str(tmp_path)) == {}

    def test_doc_dung_noi_dung(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": "D:\\vm", "phien_ban": "1.0"})
        du = che_do_vps.doc(str(tmp_path))
        assert du["vm_dir"] == "D:\\vm"
        assert du["phien_ban"] == "1.0"


class TestThuMucVm:
    def test_khong_o_vps_nem_loi(self, tmp_path):
        try:
            che_do_vps.thu_muc_vm(str(tmp_path))
            assert False, "phải ném FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_thieu_vm_dir_nem_loi(self, tmp_path):
        _ghi_marker(str(tmp_path), {})
        try:
            che_do_vps.thu_muc_vm(str(tmp_path))
            assert False, "phải ném FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_vm_dir_khong_ton_tai_nem_loi(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path / "khong-co")})
        try:
            che_do_vps.thu_muc_vm(str(tmp_path))
            assert False, "phải ném FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_vm_dir_hop_le_tra_dung_duong(self, tmp_path):
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        _ghi_marker(str(tmp_path), {"vm_dir": str(vm_dir)})
        assert che_do_vps.thu_muc_vm(str(tmp_path)) == str(vm_dir)

    def test_vm_dir_tuong_doi_tinh_tu_mytool(self, tmp_path, monkeypatch):
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        _ghi_marker(str(tmp_path), {"vm_dir": "vm"})
        # Cố ý đứng ở nơi khác: shortcut và lịch Windows không được làm đường
        # tương đối trỏ sai.
        monkeypatch.chdir(tmp_path.parent)
        assert che_do_vps.thu_muc_vm(str(tmp_path)) == str(vm_dir)


class TestTrangMoDau:
    def test_khong_o_vps_tra_none(self, tmp_path):
        assert che_do_vps.trang_mo_dau(str(tmp_path)) is None

    def test_o_vps_tra_khoa_trung_tam(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.trang_mo_dau(str(tmp_path)) == che_do_vps.KHOA_TRANG_TRUNG_TAM


# ═══ Đợt 1 mục 1.1, ràng buộc (i): mở song song lớp "api" KHÔNG được làm ═══
# ═══ nhịp hỏi job dày hơn (luật 4 CLAUDE.md).                             ═══
#
# `core.auto_khau.SoTheoDoi` đã tự gom mọi luồng đang chờ job vào MỘT vòng
# quét nền (`GET /v1/jobs` mỗi `nhip` giây) thay vì mỗi luồng tự hỏi — bài
# dưới đây chứng minh việc TĂNG số luồng (đúng như `gioi_han_song_song(...,
# lop="api")` giờ cho phép trên VPS) không hề tăng số lượt hỏi thật ra máy
# chủ giả, kể cả khi số luồng lớn hơn cả số luồng cũ (ép về 1).


class _MayChuGiaDonGian:
    """Nhà máy giả tối thiểu: đủ cho `SoTheoDoi` — đếm `retrieve`/`list`."""

    def __init__(self, tre_giay: float = 0.15) -> None:
        self._tre = tre_giay
        self._khoa = threading.Lock()
        self._job: dict = {}
        self.so_lan_retrieve = 0
        self.so_lan_list = 0
        self.jobs = self

    def tao(self, ten: str) -> str:
        with self._khoa:
            ma = "job-{0}".format(ten)
            self._job[ma] = time.time()
            return ma

    def _trang_thai(self, ma: str) -> str:
        luc = self._job.get(ma)
        if luc is None:
            return "queued"
        return "succeeded" if time.time() - luc >= self._tre else "queued"

    def retrieve(self, ma: str) -> dict:
        with self._khoa:
            self.so_lan_retrieve += 1
        return {"id": ma, "status": self._trang_thai(ma)}

    def list(self, *, status=None, limit=100, cursor=None, **_kw) -> dict:
        with self._khoa:
            self.so_lan_list += 1
            ds = [{"id": ma, "status": self._trang_thai(ma)}
                 for ma in self._job]
        ds = [g for g in ds if g["status"] == status]
        return {"object": "list", "data": ds, "has_more": False,
               "next_cursor": None}


class TestNhipHoiKhongTangTheoSoLuong:
    def _boi_canh(self, goc: str, may: _MayChuGiaDonGian):
        from core.auto_khau import BoiCanh  # noqa: PLC0415

        return BoiCanh(goc=goc, kenh=None, goi_chat=lambda *a, **k: "",
                       client=may, on_log=lambda _d: None, nhip_hoi=0.05)

    def test_tang_so_luong_khong_tang_luot_hoi_that(self, tmp_path):
        from core.auto_khau import SoTheoDoi  # noqa: PLC0415

        goc = str(tmp_path)
        _ghi_marker(goc, {"vm_dir": goc})
        may = _MayChuGiaDonGian(tre_giay=0.1)
        bc = self._boi_canh(goc, may)
        so = SoTheoDoi(bc, nhip=0.05)

        # `SONG_SONG_KHOI` trong `core/timelapse.py` là 6 — dùng đúng số đó
        # để mô phỏng khâu clip chia khối sau khi Đợt 1 mục 1.1 mở lớp "api".
        n_luong = che_do_vps.gioi_han_song_song(goc, 6, lop="api")
        assert n_luong > 1, "phải thật sự mở song song thì mới đo được gì"

        ma = [may.tao(str(i)) for i in range(20)]
        try:
            with ThreadPoolExecutor(max_workers=n_luong) as bo:
                ket = list(bo.map(lambda m: so.cho(m, tran=30), ma))
        finally:
            so.dong()

        assert all(k["status"] == "succeeded" for k in ket)
        # Cốt lõi: KHÔNG luồng nào tự hỏi riêng — cả sổ chỉ có sổ chung
        # (`list`) làm việc, đúng như một luồng ép về 1 vẫn vậy.
        assert may.so_lan_retrieve == 0, (
            "mở {0} luồng song song mà vẫn có {1} lượt hỏi RIÊNG — nhịp hỏi "
            "job đã dày hơn, phạm luật 4 CLAUDE.md".format(
                n_luong, may.so_lan_retrieve))

    def test_so_lan_list_khong_ti_le_voi_so_luong(self, tmp_path):
        """So một sổ dùng 1 luồng với một sổ dùng 6 luồng — số lượt `list` gần
        như nhau (chỉ do nhịp thời gian, không do số luồng)."""
        from core.auto_khau import SoTheoDoi  # noqa: PLC0415

        goc = str(tmp_path)

        def _chay(n_luong: int) -> int:
            may = _MayChuGiaDonGian(tre_giay=0.1)
            bc = self._boi_canh(goc, may)
            so = SoTheoDoi(bc, nhip=0.05)
            ma = [may.tao("{0}-{1}".format(n_luong, i)) for i in range(20)]
            try:
                with ThreadPoolExecutor(max_workers=n_luong) as bo:
                    list(bo.map(lambda m: so.cho(m, tran=30), ma))
            finally:
                so.dong()
            return may.so_lan_list

        lan_1 = _chay(1)
        lan_6 = _chay(6)
        # Cùng nhịp quét (0.05s) và cùng thời gian job xong (~0.1s) thì số lượt
        # quét gần như nhau bất kể 1 hay 6 luồng — sai lệch chỉ do độ trễ hệ
        # điều hành lúc dựng luồng, không phải do TỈ LỆ với số luồng.
        assert lan_1 > 0 and lan_6 > 0
        assert lan_6 <= lan_1 * 3, (
            "6 luồng quét {0} lần, 1 luồng quét {1} lần — lượt quét đang tỉ lệ "
            "với số luồng thay vì dùng chung một sổ".format(lan_6, lan_1))
