"""`core/cong_suat.py` — đo công suất thật (phút/khâu, % khe, ước video/ngày).

Ba lượt giả, không mạng, không đụng workspace/cong-suat thật (mọi bài dùng
`tmp_path` làm `goc`). Xem `workspace/LO-TRINH-PHAT-HANH-V3.md`, Đợt 0 mục 0.1.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from core import cong_suat


def _epoch(ngay: str, gio: str = "10:00:00") -> float:
    return datetime.strptime("{0} {1}".format(ngay, gio), "%Y-%m-%d %H:%M:%S").timestamp()


def _ghi_luot(goc: str, kenh: str, luot: str, ngay: str,
              anh_phut: float, dung_phut: float, phude_phut: float) -> None:
    """Một `trang-thai.json` giả: khâu `anh` (lớp A), `dung`+`phu-de` (lớp B)."""
    thu_muc = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)
    os.makedirs(thu_muc, exist_ok=True)
    bd = _epoch(ngay, "01:00:00")

    def _khau(phut: float, bat_dau: float):
        return {"ma": "x", "trang_thai": "xong", "so_lan": 1, "loi": "",
                "bat_dau": bat_dau, "ket_thuc": bat_dau + phut * 60.0, "ghi_chu": {}}

    du = {
        "ma_kenh": kenh, "ma_luot": luot, "tao_luc": bd,
        "khau": {
            "anh": _khau(anh_phut, bd),
            "dung": _khau(dung_phut, bd + anh_phut * 60.0),
            "phu-de": _khau(phude_phut, bd + (anh_phut + dung_phut) * 60.0),
            # Khâu đang chạy dở — thiếu ket_thuc, phải bị BỎ QUA, không được
            # làm nhiễu trung vị.
            "clip": {"ma": "clip", "trang_thai": "dang_chay", "so_lan": 1,
                     "loi": "", "bat_dau": bd, "ket_thuc": None, "ghi_chu": {}},
        },
    }
    with open(os.path.join(thu_muc, "trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)


def _ghi_phien(goc: str, theo_kenh: dict) -> None:
    """`vm/trang-thai.json` giả — `theo_kenh`: {kênh: (ngày, bắt_đầu, kết_thúc)}."""
    du = {}
    for kenh, (ngay, bd, kt) in theo_kenh.items():
        du["phien_ket_qua@{0}".format(kenh)] = {
            "kenh": kenh, "bat_dau": "{0} {1}".format(ngay, bd),
            "ket_thuc": "{0} {1}".format(ngay, kt),
        }
    os.makedirs(os.path.join(goc, "vm"), exist_ok=True)
    with open(os.path.join(goc, "vm", "trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)


def _ghi_dang_dom(goc: str, dong: list) -> None:
    os.makedirs(os.path.join(goc, "vm", "logs"), exist_ok=True)
    with open(os.path.join(goc, "vm", "logs", "dang-dom.log"), "w",
             encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


def _ghi_tu_chay(goc: str, ngay: str, kenh_video: dict) -> None:
    """`workspace/tu-chay/<ngày>.json` giả.

    `kenh_video`: {kênh: có_video_xong (bool)} — mọi kênh trong đó được coi là
    "che_do: that" (đang chạy thật, không phải lượt thử).
    """
    ket_qua = []
    for kenh, co_video in kenh_video.items():
        tom_tat = ("{0}: xong video lượt 0001 (...)".format(kenh) if co_video
                   else "{0}: chưa đến lúc chốt nội dung mới.".format(kenh))
        ket_qua.append({"kenh": kenh, "ok": True, "tom_tat": tom_tat, "loi": "",
                        "bat_dau": ngay + "T00:00:00", "keo_nhau": "",
                        "cho_nguoi": False, "ket_thuc": ngay + "T01:00:00"})
    du = {"ngay": ngay, "runs": [{"luc": ngay + "T00:00:00", "che_do": "that",
                                  "ket_qua": ket_qua}]}
    thu_muc = os.path.join(goc, "workspace", "tu-chay")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "{0}.json".format(ngay)), "w",
             encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)


# ═══ Nguồn 1: trang-thai.json ═══════════════════════════════════════════════


class TestDocKhau:
    def test_doc_dung_lop_va_phut(self, tmp_path):
        goc = str(tmp_path)
        _ghi_luot(goc, "K1", "0001", "2026-09-20", anh_phut=50, dung_phut=20,
                 phude_phut=5)
        ban_ghi = cong_suat.doc_khau(goc)
        theo_khau = {b["khau"]: b for b in ban_ghi}
        assert theo_khau["anh"]["lop"] == "A"
        assert theo_khau["anh"]["phut"] == 50.0
        assert theo_khau["anh"]["ngay"] == "2026-09-20"
        assert theo_khau["dung"]["lop"] == "B"
        assert theo_khau["phu-de"]["lop"] == "B"

    def test_bo_qua_khau_dang_chay_do(self, tmp_path):
        """Khâu chưa có `ket_thuc` (đang chạy dở) không được lọt vào trung vị."""
        goc = str(tmp_path)
        _ghi_luot(goc, "K1", "0001", "2026-09-20", anh_phut=50, dung_phut=20,
                 phude_phut=5)
        ban_ghi = cong_suat.doc_khau(goc)
        assert "clip" not in {b["khau"] for b in ban_ghi}

    def test_loc_theo_tu_ngay(self, tmp_path):
        goc = str(tmp_path)
        _ghi_luot(goc, "K1", "0001", "2026-09-20", anh_phut=50, dung_phut=20,
                 phude_phut=5)
        _ghi_luot(goc, "K1", "0002", "2026-09-26", anh_phut=400, dung_phut=30,
                 phude_phut=8)
        moi = cong_suat.doc_khau(goc, tu="2026-09-24")
        assert all(b["ngay"] >= "2026-09-24" for b in moi)
        assert len(moi) == 3  # anh + dung + phu-de của MỖI lượt 0002

    def test_khong_co_tep_nao_tra_rong(self, tmp_path):
        assert cong_suat.doc_khau(str(tmp_path)) == []


# ═══ Nguồn 2: phiên kênh ═════════════════════════════════════════════════════


class TestDocPhienQuet:
    def test_tinh_dung_phut(self, tmp_path):
        goc = str(tmp_path)
        _ghi_phien(goc, {"K1": ("2026-09-20", "07:30:00", "07:47:00")})
        ban_ghi = cong_suat.doc_phien_quet(goc)
        assert len(ban_ghi) == 1
        assert ban_ghi[0]["lop"] == "C"
        assert round(ban_ghi[0]["phut"], 1) == 17.0

    def test_khong_co_tep_tra_rong(self, tmp_path):
        assert cong_suat.doc_phien_quet(str(tmp_path)) == []


# ═══ Nguồn 3: nhật ký máy đăng ════════════════════════════════════════════


class TestDocTaiLen:
    def test_khop_bat_dau_va_ket_qua_theo_ma(self, tmp_path):
        goc = str(tmp_path)
        _ghi_dang_dom(goc, [
            "2026-09-20 08:00:00,000 INFO: K1-0001: đã chọn tệp (hop_chon_tep) "
            "— YouTube bắt đầu tải",
            "2026-09-20 08:20:00,000 INFO: K1-0001: KẾT QUẢ xong",
        ])
        ban_ghi = cong_suat.doc_tai_len(goc)
        assert len(ban_ghi) == 1
        assert ban_ghi[0]["ma"] == "K1-0001"
        assert ban_ghi[0]["kenh"] == "K1"
        assert round(ban_ghi[0]["phut"], 1) == 20.0
        assert ban_ghi[0]["lop"] == "C"

    def test_thu_lai_chi_tinh_lan_gan_nhat(self, tmp_path):
        """Bấm lại/mở Chrome lại: mốc BẮT ĐẦU thứ hai mới là mốc đúng."""
        goc = str(tmp_path)
        _ghi_dang_dom(goc, [
            "2026-09-20 08:00:00,000 INFO: K1-0001: đã chọn tệp (hop_chon_tep) "
            "— YouTube bắt đầu tải",
            "2026-09-20 08:05:00,000 WARNING: K1-0001: HỎNG SAU khi chạm kênh",
            "2026-09-20 08:10:00,000 INFO: K1-0001: đã chọn tệp (hop_chon_tep) "
            "— YouTube bắt đầu tải",
            "2026-09-20 08:16:00,000 INFO: K1-0001: KẾT QUẢ xong",
        ])
        ban_ghi = cong_suat.doc_tai_len(goc)
        assert len(ban_ghi) == 1
        assert round(ban_ghi[0]["phut"], 1) == 6.0

    def test_lan_thu_hong_khong_co_ket_qua_thi_khong_tinh(self, tmp_path):
        goc = str(tmp_path)
        _ghi_dang_dom(goc, [
            "2026-09-20 08:00:00,000 INFO: K1-0001: đã chọn tệp (hop_chon_tep) "
            "— YouTube bắt đầu tải",
            "2026-09-20 08:05:00,000 WARNING: K1-0001: HỎNG SAU khi chạm kênh",
        ])
        assert cong_suat.doc_tai_len(goc) == []

    def test_khong_co_tep_tra_rong(self, tmp_path):
        assert cong_suat.doc_tai_len(str(tmp_path)) == []


# ═══ Nguồn 4: hoạt động theo ngày ════════════════════════════════════════


class TestDocHoatDongKenh:
    def test_dem_dung_so_kenh_va_so_video(self, tmp_path):
        goc = str(tmp_path)
        _ghi_tu_chay(goc, "2026-09-27", {"K1": True, "K2": False})
        hd = cong_suat.doc_hoat_dong_kenh(goc)
        assert hd["2026-09-27"]["so_kenh"] == 2
        assert hd["2026-09-27"]["so_video"] == 1

    def test_khong_co_tep_tra_rong(self, tmp_path):
        assert cong_suat.doc_hoat_dong_kenh(str(tmp_path)) == {}


# ═══ Công thức C.2 — ba lượt giả ═══════════════════════════════════════════


class TestPhanTichCongThucC2:
    """Ba lượt giả (một trước mốc, hai sau mốc) + số liệu C, đối chiếu tay.

    Trước mốc (2026-09-20): K1/0001 — ảnh 50', dựng 20', phụ đề 5'.
    Sau mốc   (2026-09-26): K1/0002 — ảnh 400', dựng 30', phụ đề 8'.
    Sau mốc   (2026-09-27): K2/0001 — ảnh 300', dựng 25', phụ đề 6'.

    Trung vị CẢ GIAI ĐOẠN: ảnh [50,300,400]→300 · dựng [20,25,30]→25 ·
    phụ đề [5,6,8]→6 → Bv = 25+6 = 31.
    Phiên quét: K1 15', K2 17' → trung vị 16 (Q).
    Tải lên: K1 20', K2 10' → trung vị 15 (Ct).
    N = 2 kênh (K1, K2 đều "che_do": "that" ngày 27/09, ngày gần nhất).
    Khe = 1152 phút/ngày.
    video_ngay_bc = (1152 − 2·16) / (31+15) = 1120/46 ≈ 24,35.
    video_ngay_a (L=1 mặc định) = 8·1 = 8 → trần thật = min(24,35; 8) = 8.
    Thực tế gần nhất (27/09): 1 video xong (K1 có "xong video", K2 không).
    Máy còn dư = 8 − 1 = 7.
    """

    def _dung_bo_du_lieu(self, goc: str) -> None:
        _ghi_luot(goc, "K1", "0001", "2026-09-20", anh_phut=50, dung_phut=20,
                 phude_phut=5)
        _ghi_luot(goc, "K1", "0002", "2026-09-26", anh_phut=400, dung_phut=30,
                 phude_phut=8)
        _ghi_luot(goc, "K2", "0001", "2026-09-27", anh_phut=300, dung_phut=25,
                 phude_phut=6)
        _ghi_phien(goc, {
            "K1": ("2026-09-20", "07:00:00", "07:15:00"),
            "K2": ("2026-09-20", "07:00:00", "07:17:00"),
        })
        _ghi_dang_dom(goc, [
            "2026-09-20 08:00:00,000 INFO: K1-0001: đã chọn tệp (hop_chon_tep) "
            "— YouTube bắt đầu tải",
            "2026-09-20 08:20:00,000 INFO: K1-0001: KẾT QUẢ xong",
            "2026-09-20 09:00:00,000 INFO: K2-0001: đã chọn tệp (hop_chon_tep) "
            "— YouTube bắt đầu tải",
            "2026-09-20 09:10:00,000 INFO: K2-0001: KẾT QUẢ xong",
        ])
        _ghi_tu_chay(goc, "2026-09-27", {"K1": True, "K2": False})

    def test_trung_vi_theo_giai_doan(self, tmp_path):
        goc = str(tmp_path)
        self._dung_bo_du_lieu(goc)
        kq = cong_suat.phan_tich(goc)
        anh_truoc = kq["phut_theo_khau"]["truoc_moc"]["anh"]
        anh_sau = kq["phut_theo_khau"]["tu_moc"]["anh"]
        anh_tong = kq["phut_theo_khau"]["tong"]["anh"]
        assert anh_truoc == {"so_mau": 1, "trung_vi": 50.0, "min": 50.0, "max": 50.0}
        assert anh_sau["trung_vi"] == 350.0  # trung bình (300+400)/2 của median 2 mẫu
        assert anh_sau["min"] == 300.0 and anh_sau["max"] == 400.0
        assert anh_tong["trung_vi"] == 300.0

    def test_cong_thuc_c2_dung_nhu_tinh_tay(self, tmp_path):
        goc = str(tmp_path)
        self._dung_bo_du_lieu(goc)
        kq = cong_suat.phan_tich(goc)
        c2 = kq["cong_thuc_c2"]
        assert c2["khe_ngay_phut"] == 1152.0
        assert c2["so_kenh_n"] == 2
        assert c2["q_phien_quet_phut"] == 16.0
        assert c2["bv_lop_b_phut_moi_video"] == 31.0
        assert c2["ct_lop_c_phut_moi_video"] == 15.0
        assert round(c2["video_ngay_toi_da_lop_bc"], 2) == round(1120 / 46, 2)
        assert c2["video_ngay_toi_da_lop_a"] == 8.0
        assert c2["video_ngay_toi_da"] == 8.0  # trần lớp A thắng (L=1 mặc định)
        assert c2["video_ngay_thuc_te_gan_nhat"] == 1
        assert c2["may_con_du_video_ngay"] == 7.0

    def test_tang_lan_song_song_thi_tran_lop_a_tang(self, tmp_path):
        """L (làn song song lớp A) tăng thì trần lớp A tăng theo 8·L."""
        goc = str(tmp_path)
        self._dung_bo_du_lieu(goc)
        kq = cong_suat.phan_tich(goc, lan_song_song=4)
        c2 = kq["cong_thuc_c2"]
        assert c2["video_ngay_toi_da_lop_a"] == 32.0
        # Giờ trần lớp B∪C thắng (~24,35 < 32).
        assert c2["video_ngay_toi_da"] < 32.0
        assert round(c2["video_ngay_toi_da"], 2) == round(1120 / 46, 2)

    def test_truyen_thang_so_kenh_ghi_de_tu_dem(self, tmp_path):
        goc = str(tmp_path)
        self._dung_bo_du_lieu(goc)
        kq = cong_suat.phan_tich(goc, so_kenh=5)
        assert kq["cong_thuc_c2"]["so_kenh_n"] == 5

    def test_khong_du_lieu_thi_khong_nem_loi(self, tmp_path):
        """Thư mục trống — mọi con số phải là 0/None, không phải lỗi chia 0."""
        kq = cong_suat.phan_tich(str(tmp_path))
        c2 = kq["cong_thuc_c2"]
        assert c2["so_kenh_n"] == 0
        assert c2["video_ngay_toi_da_lop_bc"] is None
        assert c2["video_ngay_toi_da"] == 8.0  # chỉ còn trần lớp A (L mặc định 1)
        assert c2["may_con_du_video_ngay"] is None


# ═══ Ghi báo cáo ═════════════════════════════════════════════════════════


class TestGhiBaoCao:
    def test_ghi_ca_json_va_md(self, tmp_path):
        goc = str(tmp_path)
        _ghi_luot(goc, "K1", "0001", "2026-09-20", anh_phut=50, dung_phut=20,
                 phude_phut=5)
        kq = cong_suat.phan_tich(goc)
        duong = cong_suat.ghi_bao_cao(goc, kq, ngay="2026-09-29")
        assert os.path.isfile(duong["json"])
        assert os.path.isfile(duong["md"])
        with open(duong["json"], "r", encoding="utf-8") as tep:
            lai = json.load(tep)
        assert lai["cong_thuc_c2"]["q_phien_quet_phut"] == kq["cong_thuc_c2"][
            "q_phien_quet_phut"]
        with open(duong["md"], "r", encoding="utf-8") as tep:
            noi_dung = tep.read()
        assert "Ước tối đa" in noi_dung or "Máy còn dư" in noi_dung

    def test_duong_dan_dung_ten_ngay(self, tmp_path):
        goc = str(tmp_path)
        kq = cong_suat.phan_tich(goc)
        duong = cong_suat.ghi_bao_cao(goc, kq, ngay="2026-01-02")
        assert duong["json"].endswith(os.path.join("cong-suat", "2026-01-02.json"))
        assert duong["md"].endswith(os.path.join("cong-suat", "2026-01-02.md"))


class TestDoThatChuKy:
    def _luot(self, goc, kenh, luot, bd, dung_kt):
        import json as _j
        d = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "trang-thai.json"), "w", encoding="utf-8") as f:
            _j.dump({"ma_kenh": kenh, "ma_luot": luot, "khau": {
                "anh": {"bat_dau": bd, "ket_thuc": bd + 3 * 3600, "trang_thai": "xong"},
                "dung": {"bat_dau": dung_kt - 600, "ket_thuc": dung_kt, "trang_thai": "xong"}}}, f)

    def test_chu_ky_va_khau_nghen(self, tmp_path):
        import time
        goc = str(tmp_path)
        now = time.time()
        for i in range(3):
            self._luot(goc, "K1", "000%d" % i, now - 86400 + i * 100, now - 86400 + 4 * 3600 + i * 100)
        r = cong_suat.do_chu_ky_that(goc, bay_gio=now)
        assert r["so_luot"] == 3 and r["khau_nghen"] == "anh"
        assert 5.9 < r["theo_kenh"]["K1"]["video_ngay"] < 6.1  # 4h/video
        assert r["tong_video_ngay"] == r["theo_kenh"]["K1"]["video_ngay"]

    def test_lan_mac_dinh_doc_cai_dat(self, tmp_path):
        import json as _j
        os.makedirs(os.path.join(str(tmp_path), "workspace"))
        with open(os.path.join(str(tmp_path), "workspace", "cai-dat.json"), "w") as f:
            _j.dump({"lan_api": 4}, f)
        kq = cong_suat.phan_tich(str(tmp_path))
        assert kq["cong_thuc_c2"]["lan_song_song_lop_a"] == 4
