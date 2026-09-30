"""core/an_toan_khoi_dong.py — "khởi động lại giao diện có an toàn không"

Mục 6 `workspace/THIET-KE-BANG-DIEU-KHIEN.md` (duyệt 29/09/2026), Việc 3.
Hàm thuần, chỉ đọc tệp trong `tmp_path` — không đụng gốc MyTool thật, không
sinh tiến trình con nào (điều kiện 4 dùng PID của chính tiến trình pytest
đang chạy làm "còn sống", và một PID rất lớn khó tồn tại làm "đã chết").
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from core import an_toan_khoi_dong as atk

#: Giờ giả AN TOÀN cho mọi bài không cố tình kiểm khung giờ: 15:30 —
#: ngoài 07:25–08:15, ngoài 19:00–21:05, phút 30 ngoài :58–:05.
BAY_GIO_AN_TOAN = _dt.datetime(2026, 9, 29, 15, 30)

#: PID gần như chắc chắn không tồn tại trên máy chạy test — dùng làm
#: "tiến trình đã chết" mà không phải sinh/giết tiến trình thật.
PID_KHONG_TON_TAI = 999_999_999


def _kenh(goc: str, ma: str) -> str:
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("ten: " + ma + "\n")
    return thu_muc


def _ghi_json(duong: str, du) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)


def _co_chu(ly_do, *tu_khoa) -> bool:
    return any(all(t in ly for t in tu_khoa) for ly in ly_do)


class TestMacDinhAnToan:
    def test_goc_trong_khong_co_gi_can_thi_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN)
        assert kq == {"duoc": True, "ly_do": [], "luc_an_toan_tiep": None}


class TestDangDodang:
    """(1) `vm/logs/dang-dodang.json`."""

    def test_khong_co_tep_thi_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_co_tep_thi_chua_an_toan_va_neu_ten_kenh(self, tmp_path):
        goc = str(tmp_path)
        _ghi_json(os.path.join(goc, "vm", "logs", "dang-dodang.json"),
                  {"kenh": "TL1-T7", "ma": "TL1-0007", "pid": 4321})
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "TL1-T7", "đăng")


class TestPhienDangMo:
    """(2) `phien_cuoi@<k>` / `phien_ket_qua@<k>` trong `<vm>/trang-thai.json`.

    `core.trung_tam._trang_thai_vm` chỉ được gọi khi `<vm>/config.json` có
    nội dung (đúng nếp `anh_chup` — máy chưa cấu hình `vm/` thì không có khái
    niệm "phiên" để kiểm) — mọi bài ở đây đều ghi kèm một `config.json` tối
    thiểu để `trang-thai.json` thật sự được đọc.
    """

    @staticmethod
    def _cau_hinh_vm(goc: str) -> None:
        _ghi_json(os.path.join(goc, "vm", "config.json"), {"cac_kenh": []})

    def test_phien_hom_qua_thi_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "TL1-T7")
        self._cau_hinh_vm(goc)
        _ghi_json(os.path.join(goc, "vm", "trang-thai.json"),
                  {"phien_cuoi@TL1-T7": "2026-09-28"})
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_phien_hom_nay_da_ghi_ket_thuc_thi_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "TL1-T7")
        self._cau_hinh_vm(goc)
        _ghi_json(os.path.join(goc, "vm", "trang-thai.json"), {
            "phien_cuoi@TL1-T7": "2026-09-29",
            "phien_ket_qua@TL1-T7": {"ket_thuc": "2026-09-29 14:50:00"},
        })
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_phien_hom_nay_chua_ket_thuc_thi_chua_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "TL2-T7")
        self._cau_hinh_vm(goc)
        _ghi_json(os.path.join(goc, "vm", "trang-thai.json"), {
            "phien_cuoi@TL2-T7": "2026-09-29",
            "phien_ket_qua@TL2-T7": {},
        })
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "TL2-T7", "phiên")


class TestKhungGioTranh:
    """(2) hai khung giờ cố định 07:25–08:15 và 19:00–21:05."""

    def test_ngoai_khung_thi_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_gio_sang_thi_chua_an_toan_va_co_luc_an_toan_tiep(self, tmp_path):
        bay_gio = _dt.datetime(2026, 9, 29, 7, 40)
        kq = atk.kiem_tra(str(tmp_path), bay_gio)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "07:25")
        assert kq["luc_an_toan_tiep"] is not None
        luc = _dt.datetime.fromisoformat(kq["luc_an_toan_tiep"])
        assert luc > bay_gio
        assert not (_dt.time(7, 25) <= luc.time() <= _dt.time(8, 15))

    def test_gio_toi_thi_chua_an_toan(self, tmp_path):
        bay_gio = _dt.datetime(2026, 9, 29, 20, 0)
        kq = atk.kiem_tra(str(tmp_path), bay_gio)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "19:00") or _co_chu(kq["ly_do"], "21:05")


class TestKhungGioDangTheoKenh:
    """(2) khung tối tính THẬT theo `gio_dang` của từng kênh (`kenh.yaml`) +
    `phien_truoc_phut` (`may-ao.json`) — công thức mục 6, KHÔNG phải hằng số
    19:00–21:05 cứng (đó chỉ là khung DỰ PHÒNG khi không kênh nào khai
    `gio_dang`, xem `TestKhungGioTranh`)."""

    @staticmethod
    def _kenh_gio_dang(goc: str, ma: str, gio_dang: str, phien_truoc_phut: int) -> None:
        thu_muc = os.path.join(goc, "CHANNEL", ma)
        os.makedirs(thu_muc, exist_ok=True)
        with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
            tep.write("ten: {0}\ngio_dang: '{1}'\n".format(ma, gio_dang))
        _ghi_json(os.path.join(thu_muc, "may-ao.json"),
                  {"phien_truoc_phut": phien_truoc_phut})

    def test_khung_doi_theo_gio_dang_that_cua_kenh(self, tmp_path):
        goc = str(tmp_path)
        # Công thức: [18:00 − 30' − 5', 18:00 + 60'] = [17:25, 19:00] — khác
        # hẳn khung mặc định 19:00–21:05.
        self._kenh_gio_dang(goc, "TL9-T7", "18:00", 30)
        kq = atk.kiem_tra(goc, _dt.datetime(2026, 9, 29, 17, 30))
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "TL9-T7")

    def test_ngoai_khung_that_cua_kenh_thi_an_toan_du_trung_khung_mac_dinh_cu(self, tmp_path):
        goc = str(tmp_path)
        self._kenh_gio_dang(goc, "TL9-T7", "18:00", 30)
        # 20:30 nằm NGOÀI khung thật [17:25, 19:00] của kênh này — công thức
        # thật phải thắng, không được rơi lại về hằng số cứng 19:00–21:05.
        kq = atk.kiem_tra(goc, _dt.datetime(2026, 9, 29, 20, 30))
        assert kq["duoc"] is True

    def test_khong_kenh_nao_khai_gio_dang_thi_dung_khung_du_phong(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "TL9-T7")  # kenh.yaml không có `gio_dang`
        kq = atk.kiem_tra(goc, _dt.datetime(2026, 9, 29, 20, 0))
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "19:00") or _co_chu(kq["ly_do"], "21:05")


class TestKheNangDangBan:
    """(3, sửa 29/09 tối) `core.khe.trang_thai(goc)["nang"]` — khe độc quyền
    toàn máy đang giữ việc "tai_len"/"quet" (trình duyệt còn mở). "Kênh đang
    sản xuất" một mình (điều kiện 3 CŨ, `khoa_dang_giu`) không còn chặn nữa —
    xem docstring đầu module."""

    @staticmethod
    def _ghi_khoa_nang(goc: str, *, viec: str, kenh: str = "", pid: Optional[int] = None) -> None:
        _ghi_json(os.path.join(goc, "workspace", "tu-chay", ".khoa-may"), {
            "pid": pid if pid is not None else os.getpid(), "tid": 1, "nguon": "khe",
            "loai": "nang", "viec": viec, "kenh": kenh, "uu_tien": 1,
            "bat_dau": BAY_GIO_AN_TOAN.timestamp() - 60, "han_giay": None,
        })

    def test_khong_co_khoa_thi_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "TL3-T7")
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_dang_tai_len_thi_chua_an_toan(self, tmp_path):
        goc = str(tmp_path)
        self._ghi_khoa_nang(goc, viec="tai_len", kenh="TL3-T7")
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "tải video", "TL3-T7")

    def test_dang_quet_thi_chua_an_toan(self, tmp_path):
        goc = str(tmp_path)
        self._ghi_khoa_nang(goc, viec="quet")
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "quét")

    def test_dang_viet_kich_ban_thi_an_toan(self, tmp_path):
        """Khâu nội bộ (không phải trình duyệt) giữ khe "nang" — không chặn."""
        goc = str(tmp_path)
        self._ghi_khoa_nang(goc, viec="viet_kich_ban")
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_nguoi_giu_da_chet_thi_an_toan(self, tmp_path):
        goc = str(tmp_path)
        self._ghi_khoa_nang(goc, viec="tai_len", pid=999_999_999)
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True


class TestPhutDoiGio:
    """(3) tránh phút :58–:05 mỗi giờ."""

    def test_ngoai_phut_tranh_thi_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_phut_58_thi_chua_an_toan(self, tmp_path):
        bay_gio = _dt.datetime(2026, 9, 29, 15, 58)
        kq = atk.kiem_tra(str(tmp_path), bay_gio)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "đổi giờ")

    def test_phut_03_thi_chua_an_toan(self, tmp_path):
        bay_gio = _dt.datetime(2026, 9, 29, 16, 3)
        kq = atk.kiem_tra(str(tmp_path), bay_gio)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "đổi giờ")


class TestTienTrinhCon:
    """(4) `workspace/tien-trinh-con.json`."""

    def test_so_rong_thi_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_tien_trinh_da_chet_thi_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _ghi_json(os.path.join(goc, "workspace", "tien-trinh-con.json"),
                  [{"pid": PID_KHONG_TON_TAI, "tao_luc": 0, "ten": "ffmpeg"}])
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True

    def test_tien_trinh_con_song_thi_chua_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _ghi_json(os.path.join(goc, "workspace", "tien-trinh-con.json"),
                  [{"pid": os.getpid(), "tao_luc": 0, "ten": "ffmpeg"}])
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "việc nền")

    def test_tien_trinh_chu_gui_song_thi_chua_an_toan(self, tmp_path):
        goc = str(tmp_path)
        _ghi_json(os.path.join(goc, "workspace", "tien-trinh-con.json"),
                  [{"pid": os.getpid(), "tao_luc": 0, "ten": "ffmpeg", "chu": "gui"}])
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "việc nền")

    def test_tien_trinh_chu_tu_chay_song_thi_van_an_toan(self, tmp_path):
        """Một lượt `tu_chay.py` tách rời (`chu == "tu_chay"`) không chặn
        khởi động lại giao diện nữa — xem docstring đầu module."""
        goc = str(tmp_path)
        _ghi_json(os.path.join(goc, "workspace", "tien-trinh-con.json"),
                  [{"pid": os.getpid(), "tao_luc": 0, "ten": "claude", "chu": "tu_chay"}])
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN)
        assert kq["duoc"] is True


class TestViecChayTay:
    """(5) `viec_chay_tay` — nơi gọi tự truyền vào (bộ nhớ, không có trên đĩa)."""

    def test_khong_co_viec_thi_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN, viec_chay_tay=False)
        assert kq["duoc"] is True

    def test_co_viec_thi_chua_an_toan(self, tmp_path):
        kq = atk.kiem_tra(str(tmp_path), BAY_GIO_AN_TOAN, viec_chay_tay=True)
        assert kq["duoc"] is False
        assert _co_chu(kq["ly_do"], "chạy tay")


class TestNhieuLyDoCungLuc:
    def test_gop_du_moi_ly_do_khong_chi_lay_dau(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "TL1-T7")
        _ghi_json(os.path.join(goc, "vm", "logs", "dang-dodang.json"),
                  {"kenh": "TL1-T7", "ma": "TL1-0007"})
        _ghi_json(os.path.join(goc, "workspace", "tien-trinh-con.json"),
                  [{"pid": os.getpid(), "tao_luc": 0}])
        kq = atk.kiem_tra(goc, BAY_GIO_AN_TOAN, viec_chay_tay=True)
        assert kq["duoc"] is False
        assert len(kq["ly_do"]) >= 3
        assert _co_chu(kq["ly_do"], "TL1-T7", "đăng")
        assert _co_chu(kq["ly_do"], "việc nền")
        assert _co_chu(kq["ly_do"], "chạy tay")
        # Việc thật đang chạy dở — không đoán được bao giờ xong.
        assert kq["luc_an_toan_tiep"] is None
