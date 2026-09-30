"""Bài kiểm `core/don_dep_mo_rong.py` — dọn báo cáo ngày cũ + log dọn dẹp.

Quan trọng nhất trong tệp này KHÔNG PHẢI "xoá được", mà là **GIỮ ĐÚNG** thứ
không bao giờ được đụng: `trang-thai.json`, `.khoa`, `chi-so/`, `don-dep.log`
(trước khi quá cỡ), `tu-chay.log`, và mọi tệp tên lạ không khớp khuôn
`YYYY-MM-DD.md`/`.json` — dù nằm chung thư mục và dù cũ tới đâu.

Toàn bộ dùng `tmp_path`, không đụng gì tới CHANNEL/workspace thật của kho này.
Không gọi mạng.
"""

from __future__ import annotations

import datetime
import os

from core import don_dep_mo_rong as dm

KENH = "K1"


def _ghi_kenh_yaml(goc: str, **khoa) -> None:
    d = os.path.join(goc, "CHANNEL", KENH)
    os.makedirs(d, exist_ok=True)
    dong = ["ma: {0}".format(KENH)]
    for k, v in khoa.items():
        dong.append("{0}: {1}".format(k, v))
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


def _ghi(duong: str, chu: str = "x") -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


HOM_NAY = datetime.date(2026, 9, 26)


# ── Khuôn tên: chỉ nhận đúng YYYY-MM-DD.md / .json ──────────────────────────


class TestKhuonTen:
    def test_ten_la_bao_cao_ngay(self):
        assert dm._ngay_tu_ten("2026-01-01.md") == datetime.date(2026, 1, 1)
        assert dm._ngay_tu_ten("2026-01-01.json") == datetime.date(2026, 1, 1)

    def test_ten_khong_khop_thi_tra_none(self):
        for ten in ("tu-chay.log", "don-dep.log", ".khoa", "da-don.json",
                    "2026-1-1.md", "README.md", "2026-01-01.txt",
                    "2026-01-01-ban-sao.md", "trang-thai.json"):
            assert dm._ngay_tu_ten(ten) is None, ten


# ── GIỮ ĐÚNG những gì phải giữ (quan trọng nhất) ────────────────────────────


class TestGiuDungThuPhaiGiu:
    def test_khong_dung_tu_chay_log_du_cu_va_to(self, tmp_path):
        goc = str(tmp_path)
        thu_muc = os.path.join(goc, "workspace", "tu-chay")
        _ghi(os.path.join(thu_muc, "tu-chay.log"), "x" * 10_000)
        _ghi(os.path.join(thu_muc, "2020-01-01.md"), "cu")
        ds = dm.ung_vien_bao_cao_tat_ca_cu(goc, bay_gio=HOM_NAY)
        ten = [os.path.basename(u["duong"]) for u in ds]
        assert "tu-chay.log" not in ten
        assert "2020-01-01.md" in ten

    def test_khong_dung_don_dep_log_va_khoa_du_cu(self, tmp_path):
        goc = str(tmp_path)
        thu_muc = os.path.join(goc, "CHANNEL", KENH, "tu-chay")
        _ghi(os.path.join(thu_muc, "don-dep.log"), "x" * 10_000)
        _ghi(os.path.join(thu_muc, ".khoa"), '{"pid": 1}')
        _ghi(os.path.join(thu_muc, "2020-01-01.json"), "{}")
        ds = dm.ung_vien_bao_cao_kenh_cu(goc, KENH, bay_gio=HOM_NAY)
        ten = [os.path.basename(u["duong"]) for u in ds]
        assert "don-dep.log" not in ten and ".khoa" not in ten
        assert "2020-01-01.json" in ten

    def test_ten_la_khong_doan_du_nam_dung_thu_muc(self, tmp_path):
        """Tệp tên lạ (không khớp khuôn ngày) không bao giờ vào danh sách ứng
        viên, kể cả khi nó cũ và nằm ĐÚNG thư mục báo cáo."""
        goc = str(tmp_path)
        thu_muc = os.path.join(goc, "workspace", "tu-chay")
        _ghi(os.path.join(thu_muc, "trang-thai.json"), "{}")
        _ghi(os.path.join(thu_muc, "GHI-CHU-CUA-CHU.md"), "đừng xoá")
        ds = dm.ung_vien_bao_cao_tat_ca_cu(goc, bay_gio=HOM_NAY)
        assert ds == []

    def test_bao_cao_con_trong_han_khong_bi_dong(self, tmp_path):
        goc = str(tmp_path)
        thu_muc = os.path.join(goc, "workspace", "tu-chay")
        gan = (HOM_NAY - datetime.timedelta(days=5)).isoformat()
        _ghi(os.path.join(thu_muc, gan + ".md"), "moi")
        ds = dm.ung_vien_bao_cao_tat_ca_cu(goc, giu_ngay=180, bay_gio=HOM_NAY)
        assert ds == []

    def test_giu_ngay_0_tat_han_luon(self, tmp_path):
        goc = str(tmp_path)
        thu_muc = os.path.join(goc, "workspace", "tu-chay")
        _ghi(os.path.join(thu_muc, "2000-01-01.md"), "rat cu")
        assert dm.ung_vien_bao_cao_tat_ca_cu(goc, giu_ngay=0, bay_gio=HOM_NAY) == []

    def test_khong_dong_chi_so_du_no_khong_phai_thu_muc_tu_chay(self, tmp_path):
        """`chi-so/` không nằm trong `tu-chay/` nên không đường nào ở đây chạm
        tới nó — kiểm cho chắc bằng cách dựng cả hai cạnh nhau."""
        goc = str(tmp_path)
        _ghi(os.path.join(goc, "CHANNEL", KENH, "chi-so", "abc", "13h",
                          "tong-quan.json"), "{}")
        _ghi(os.path.join(goc, "CHANNEL", KENH, "tu-chay", "2020-01-01.json"), "{}")
        ket = dm.don_bao_cao_cu(goc, [KENH], thuc_hien=True, bay_gio=HOM_NAY)
        assert os.path.isfile(os.path.join(goc, "CHANNEL", KENH, "chi-so", "abc",
                                          "13h", "tong-quan.json"))
        assert not os.path.isfile(os.path.join(goc, "CHANNEL", KENH, "tu-chay",
                                              "2020-01-01.json"))
        assert ket["tong_bytes"] > 0


# ── Xoá thật báo cáo cũ ──────────────────────────────────────────────────────


class TestDonBaoCaoCu:
    def test_thuc_hien_false_chi_tinh_khong_xoa(self, tmp_path):
        goc = str(tmp_path)
        duong = os.path.join(goc, "workspace", "tu-chay", "2020-01-01.md")
        _ghi(duong, "cu")
        ket = dm.don_bao_cao_cu(goc, [], thuc_hien=False, bay_gio=HOM_NAY)
        assert ket["tong_bytes"] > 0
        assert os.path.isfile(duong), "thuc_hien=False không được đụng đĩa"
        assert "da_xoa_tat_ca" not in ket

    def test_thuc_hien_true_xoa_that(self, tmp_path):
        goc = str(tmp_path)
        duong = os.path.join(goc, "workspace", "tu-chay", "2020-01-01.md")
        _ghi(duong, "cu")
        ket = dm.don_bao_cao_cu(goc, [], thuc_hien=True, bay_gio=HOM_NAY)
        assert not os.path.isfile(duong)
        assert duong in ket["da_xoa_tat_ca"]

    def test_xoa_ca_bao_cao_rieng_cua_kenh(self, tmp_path):
        goc = str(tmp_path)
        duong = os.path.join(goc, "CHANNEL", KENH, "tu-chay", "2020-01-01.json")
        _ghi(duong, "{}")
        ket = dm.don_bao_cao_cu(goc, [KENH], thuc_hien=True, bay_gio=HOM_NAY)
        assert not os.path.isfile(duong)
        assert duong in ket["da_xoa_theo_kenh"][KENH]


# ── Xoay log dọn dẹp của một kênh ────────────────────────────────────────────


class TestXoayLogKenh:
    def test_duoi_nguong_khong_xoay(self, tmp_path):
        goc = str(tmp_path)
        duong = dm._duong_log_don_dep(goc, KENH)
        _ghi(duong, "mot dong")
        ket = dm._xoay_log_kenh(goc, KENH, thuc_hien=True, gioi_han_byte=1024)
        assert ket["vuot_nguong"] is False
        assert os.path.isfile(duong)
        assert not os.path.exists(duong + ".cu")

    def test_vuot_nguong_thi_xoay_giu_ban_cu(self, tmp_path):
        goc = str(tmp_path)
        duong = dm._duong_log_don_dep(goc, KENH)
        _ghi(duong, "x" * 2000)
        ket = dm._xoay_log_kenh(goc, KENH, thuc_hien=True, gioi_han_byte=1024)
        assert ket["vuot_nguong"] is True and ket["da_xoay"] is True
        assert not os.path.exists(duong), "phải đổi tên đi, không giữ tên cũ"
        with open(duong + ".cu", encoding="utf-8") as tep:
            assert tep.read() == "x" * 2000

    def test_thuc_hien_false_khong_dong_dia(self, tmp_path):
        goc = str(tmp_path)
        duong = dm._duong_log_don_dep(goc, KENH)
        _ghi(duong, "x" * 2000)
        dm._xoay_log_kenh(goc, KENH, thuc_hien=False, gioi_han_byte=1024)
        assert os.path.isfile(duong) and not os.path.exists(duong + ".cu")


# ── Cửa `tu_don` — giống hệt nguyên tắc của core/don_dep.py ─────────────────


class TestCuaTuDon:
    def test_tu_don_tat_thi_khong_dung_gi(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh_yaml(goc)  # không khai tu_don — mặc định tắt
        duong = os.path.join(goc, "CHANNEL", KENH, "tu-chay", "2020-01-01.json")
        _ghi(duong, "{}")
        ket = dm.don_theo_cai_dat(goc, KENH, bay_gio=HOM_NAY)
        assert ket["chay"] is False
        assert os.path.isfile(duong), "tu_don tắt thì không được đụng gì"

    def test_tu_don_bat_thi_don_that(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh_yaml(goc, tu_don="true")
        duong = os.path.join(goc, "CHANNEL", KENH, "tu-chay", "2020-01-01.json")
        _ghi(duong, "{}")
        ket = dm.don_theo_cai_dat(goc, KENH, bay_gio=HOM_NAY)
        assert ket["chay"] is True
        assert not os.path.isfile(duong)

    def test_khoa_gia_tri_giu_ngay_rieng_cua_kenh(self, tmp_path):
        """`don_mo_rong_giu_ngay: 3` — báo cáo 5 ngày trước phải bị dọn dù
        mặc định máy là 180 ngày."""
        goc = str(tmp_path)
        _ghi_kenh_yaml(goc, tu_don="true", don_mo_rong_giu_ngay=3)
        cu = (HOM_NAY - datetime.timedelta(days=5)).isoformat()
        duong = os.path.join(goc, "CHANNEL", KENH, "tu-chay", cu + ".json")
        _ghi(duong, "{}")
        dm.don_theo_cai_dat(goc, KENH, bay_gio=HOM_NAY)
        assert not os.path.isfile(duong)

    def test_bao_cao_chung_chi_don_khi_co_kenh_bat_tu_don(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh_yaml(goc)  # K1 — tu_don tắt
        duong_chung = os.path.join(goc, "workspace", "tu-chay", "2020-01-01.md")
        _ghi(duong_chung, "cu")
        ket = dm.don_tat_ca_theo_cai_dat(goc, [KENH], bay_gio=HOM_NAY)
        assert ket["bao_cao_chung"]["chay"] is False
        assert os.path.isfile(duong_chung)

        # Kênh thứ hai bật tu_don — giờ báo cáo CHUNG mới được dọn.
        d2 = os.path.join(goc, "CHANNEL", "K2")
        os.makedirs(d2, exist_ok=True)
        with open(os.path.join(d2, "kenh.yaml"), "w", encoding="utf-8") as tep:
            tep.write("ma: K2\ntu_don: true\n")
        ket2 = dm.don_tat_ca_theo_cai_dat(goc, [KENH, "K2"], bay_gio=HOM_NAY)
        assert ket2["bao_cao_chung"]["chay"] is True
        assert not os.path.isfile(duong_chung)

    def test_mot_kenh_hong_khong_chan_kenh_khac(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _ghi_kenh_yaml(goc, tu_don="true")

        goc_that = dm.doc_kenh

        def gia(g, ma):
            if ma == KENH:
                raise RuntimeError("kenh.yaml hỏng")
            return goc_that(g, ma)

        monkeypatch.setattr(dm, "doc_kenh", gia)
        d2 = os.path.join(goc, "CHANNEL", "K2")
        os.makedirs(d2, exist_ok=True)
        with open(os.path.join(d2, "kenh.yaml"), "w", encoding="utf-8") as tep:
            tep.write("ma: K2\ntu_don: true\n")
        ket = dm.don_tat_ca_theo_cai_dat(goc, [KENH, "K2"], bay_gio=HOM_NAY)
        assert ket["theo_kenh"][KENH]["chay"] is False
        assert ket["theo_kenh"]["K2"]["chay"] is True


# ── Sức khoẻ đĩa — đo, không xoá ─────────────────────────────────────────────


class TestSucKhoeDia:
    def test_do_dung_kich_thuoc_tung_vung(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh_yaml(goc, thu_muc_done=os.path.join(goc, "DONE_RIENG"))
        _ghi(os.path.join(goc, "PROJECTS", "AUTO", KENH, "0001", "8-video.mp4"), "v" * 1000)
        _ghi(os.path.join(goc, "DONE_RIENG", "goi", "8-video.mp4"), "v" * 500)
        _ghi(os.path.join(goc, "CHANNEL", KENH, "chi-so", "a", "13h", "x.json"), "{}")
        _ghi(os.path.join(goc, "workspace", "tam.txt"), "w" * 300)
        _ghi(os.path.join(goc, "models", "m", "f.bin"), "m" * 700)

        sk = dm.suc_khoe_dia(goc, [KENH])
        assert sk["theo_kenh"][KENH]["projects_auto"] == 1000
        assert sk["theo_kenh"][KENH]["done"] == 500
        assert sk["theo_kenh"][KENH]["chi_so"] == 2  # nội dung "{}"
        assert sk["workspace_bytes"] >= 300
        assert sk["models_bytes"] == 700

    def test_canh_bao_khi_dia_duoi_nguong(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        os.makedirs(goc, exist_ok=True)

        def gia_disk_usage(_duong):
            tong = 100 * 1024 ** 3
            con = 2 * 1024 ** 3  # dưới ngưỡng mặc định 5 GB
            return (tong, tong - con, con)

        monkeypatch.setattr(dm.shutil, "disk_usage", gia_disk_usage)
        sk = dm.suc_khoe_dia(goc, [])
        assert sk["canh_bao_dia"] is True
        assert round(sk["dia_con_trong_gb"], 1) == 2.0

    def test_khong_canh_bao_khi_dia_du(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        os.makedirs(goc, exist_ok=True)

        def gia_disk_usage(_duong):
            tong = 100 * 1024 ** 3
            con = 50 * 1024 ** 3
            return (tong, tong - con, con)

        monkeypatch.setattr(dm.shutil, "disk_usage", gia_disk_usage)
        sk = dm.suc_khoe_dia(goc, [])
        assert sk["canh_bao_dia"] is False

    def test_dinh_dang_md_co_canh_bao(self):
        chu = dm.dinh_dang_suc_khoe_dia_md({
            "dia_con_trong_gb": 2.0, "dia_tong_gb": 100.0, "canh_bao_dia": True,
            "nguong_canh_bao_gb": 5.0, "theo_kenh": {}, "workspace_bytes": 0,
            "models_bytes": 0,
        })
        assert "CẢNH BÁO" in chu and "2.0 GB" in chu

    def test_dinh_dang_md_khong_canh_bao(self):
        chu = dm.dinh_dang_suc_khoe_dia_md({
            "dia_con_trong_gb": 50.0, "dia_tong_gb": 100.0, "canh_bao_dia": False,
            "nguong_canh_bao_gb": 5.0, "theo_kenh": {}, "workspace_bytes": 0,
            "models_bytes": 0,
        })
        assert "CẢNH BÁO" not in chu
