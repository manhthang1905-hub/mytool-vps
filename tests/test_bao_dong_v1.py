"""Test cho phần MỚI của `core.bao_dong` (kế hoạch gia cố, việc V1):

* chống lặp chuyển từ RAM sang FILE (`workspace/bao-dong-da-gui.json`), ghi
  nguyên tử (`.tmp` + `os.replace`), sống sót qua "tiến trình mới" (mô phỏng
  bằng `importlib.reload`) và độc lập theo `kenh`;
* hai mức mới `khan` (gửi ngay, nhắc lại mỗi 24h) và `nhac` (gộp vào hàng đợi
  bản tin, không bắn ngay);
* khuôn tin 3 dòng bắt buộc cho mức `khan` (:func:`khuon_tin_khan`);
* gửi thất bại không được ném lỗi, phải ghi `workspace/bao-dong-loi.log` và
  trạng thái đọc được qua :func:`core.bao_dong.doc_trang_thai_gui`.

Test cũ ở `test_bao_dong.py` (chưa cấu hình thì im lặng, hai kênh cùng bắn,
chống spam theo `loai`...) vẫn còn nguyên và vẫn phải xanh — file này chỉ
thêm phần MỚI, không lặp lại phần đã có. KHÔNG gọi mạng thật: mọi test
monkeypatch đúng một điểm chạm mạng `bao_dong._http_post`.
"""

from __future__ import annotations

import importlib
import json
import os

from core import bao_dong


def _ghi_cau_hinh(goc, **noi_dung):
    with open(bao_dong.bao_dong_path_for(str(goc)), "w", encoding="utf-8") as tep:
        json.dump(noi_dung, tep, ensure_ascii=False)


class TestChongLapTrenDia:
    def test_ghi_nguyen_tu_khong_con_sot_file_tam(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: None)

        assert bao_dong.bao_dong("tram_chet", "t", goc=str(tmp_path), bay_gio=0.0) is True

        duong_kho = os.path.join(str(tmp_path), "workspace", bao_dong.DA_GUI_FILENAME)
        assert os.path.isfile(duong_kho)
        assert not os.path.isfile(duong_kho + ".tmp")
        with open(duong_kho, "r", encoding="utf-8") as tep:
            kho = json.load(tep)
        assert kho["da_gui"]["tram_chet"]["lan_cuoi"] == 0.0

    def test_chong_lap_song_sot_qua_tien_trinh_moi_gia_lap(self, tmp_path, monkeypatch):
        """Mô phỏng "tiến trình mới" bằng `importlib.reload`: module nạp lại
        không còn giữ bất kỳ biến RAM nào của lần gọi trước — nếu chống lặp
        vẫn đúng thì chắc chắn nó đang đọc từ FILE, không phải bộ nhớ tiến
        trình (đúng lỗi bản cũ mắc phải: RAM reset mỗi lần `tu_chay.py` hay
        `gac_tong.py` chạy lại)."""
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=3600)
        goc = str(tmp_path)

        goi_1 = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi_1.append(1))
        assert bao_dong.bao_dong("tram_chet", "t", goc=goc, bay_gio=0.0) is True
        assert len(goi_1) == 1

        # "Tiến trình" thứ hai: nạp lại module.
        mod_2 = importlib.reload(bao_dong)
        goi_2 = []
        monkeypatch.setattr(mod_2, "_http_post", lambda *a, **k: goi_2.append(1))

        # Vẫn trong khoảng lặng 3600s kể từ lần bắn của "tiến trình" 1.
        assert mod_2.bao_dong("tram_chet", "t", goc=goc, bay_gio=10.0) is False
        assert goi_2 == []

        # Qua khỏi khoảng lặng thì bắn lại bình thường.
        assert mod_2.bao_dong("tram_chet", "t", goc=goc, bay_gio=4000.0) is True
        assert len(goi_2) == 1

    def test_khoa_theo_kenh_doc_lap_voi_nhau(self, tmp_path, monkeypatch):
        """Kênh TL1 hết tiền không được che mất báo động của kênh TL2 hết
        tiền — hai kênh có đồng hồ chống spam RIÊNG dù cùng `loai`."""
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=3600)
        goc = str(tmp_path)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("vi_can", "t", goc=goc, kenh="TL1", bay_gio=0.0) is True
        assert bao_dong.bao_dong("vi_can", "t", goc=goc, kenh="TL2", bay_gio=1.0) is True
        # Cùng kênh TL1, còn trong khoảng lặng -> bị chặn.
        assert bao_dong.bao_dong("vi_can", "t", goc=goc, kenh="TL1", bay_gio=2.0) is False
        assert len(goi) == 2

    def test_quen_khong_kenh_xoa_ca_khoa_khong_kenh_lan_moi_kenh(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=3600)
        goc = str(tmp_path)
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: None)

        assert bao_dong.bao_dong("x", "t", goc=goc, bay_gio=0.0) is True
        assert bao_dong.bao_dong("x", "t", goc=goc, kenh="TL1", bay_gio=0.0) is True
        # Cả hai đều đang trong khoảng lặng.
        assert bao_dong.bao_dong("x", "t", goc=goc, bay_gio=1.0) is False
        assert bao_dong.bao_dong("x", "t", goc=goc, kenh="TL1", bay_gio=1.0) is False

        bao_dong.quen_lich_su_chong_spam("x", goc=goc)  # không truyền kenh

        assert bao_dong.bao_dong("x", "t", goc=goc, bay_gio=2.0) is True
        assert bao_dong.bao_dong("x", "t", goc=goc, kenh="TL1", bay_gio=2.0) is True


class TestMucKhan:
    def test_khan_gui_ngay_va_nhac_lai_moi_24h(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        goc = str(tmp_path)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("vi_can", "t", goc=goc, muc=bao_dong.MUC_KHAN, bay_gio=0.0) is True
        # 1 giờ sau -> mặc định khan là 24 giờ, còn quá sớm để nhắc lại.
        assert bao_dong.bao_dong("vi_can", "t", goc=goc, muc=bao_dong.MUC_KHAN, bay_gio=3600.0) is False
        # Hơn 24 giờ -> nhắc lại.
        assert bao_dong.bao_dong("vi_can", "t", goc=goc, muc=bao_dong.MUC_KHAN, bay_gio=90000.0) is True
        assert len(goi) == 2

    def test_khuon_tin_khan_dung_3_dong_dung_thu_tu(self):
        tieu_de, chi_tiet = bao_dong.khuon_tin_khan(
            "Ví ShopAPI đã hết tiền",
            "Nạp thêm ít nhất 50.000đ",
            "Máy sẽ ngừng sản xuất video mới cho tới khi có tiền",
        )
        van_ban = "{0}\n{1}".format(tieu_de, chi_tiet)
        dong = van_ban.splitlines()
        assert len(dong) == 3
        assert dong[0] == "Ví ShopAPI đã hết tiền"
        assert dong[1].startswith("Bạn cần làm gì:")
        assert dong[2].startswith("Nếu không làm thì sao:")
        # Không lẫn từ kỹ thuật vào khuôn (chỉ kiểm phần khuôn tool tự thêm).
        for tu_cam in ("token", "endpoint", "schema", "HTTP"):
            assert tu_cam not in tieu_de
            assert tu_cam.lower() not in chi_tiet.lower()

    def test_bao_dong_khan_dung_dung_khuon_va_gui_qua_telegram(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(a))

        ket_qua = bao_dong.bao_dong_khan(
            "vi_can",
            "Ví ShopAPI đã hết tiền",
            "Nạp thêm ít nhất 50.000đ",
            "Máy sẽ ngừng sản xuất video mới",
            goc=str(tmp_path),
            kenh="TL1",
        )
        assert ket_qua is True
        assert len(goi) == 1
        (_url, payload), = ((a[0], a[1]) for a in goi)
        van_ban = payload["text"]
        assert "Ví ShopAPI đã hết tiền" in van_ban
        assert "Bạn cần làm gì: Nạp thêm ít nhất 50.000đ" in van_ban
        assert "Nếu không làm thì sao: Máy sẽ ngừng sản xuất video mới" in van_ban


class TestMucNhac:
    def test_nhac_khong_goi_mang_ma_xep_vao_hang_doi(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        goc = str(tmp_path)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        ket_qua = bao_dong.bao_dong(
            "video_moi", "Hôm nay kênh TL1 chưa có video mới", goc=goc,
            muc=bao_dong.MUC_NHAC, kenh="TL1", bay_gio=0.0,
        )
        assert ket_qua is True
        assert goi == []  # KHÔNG gọi mạng ngay

        cho_ban_tin = bao_dong.lay_va_xoa_cac_tin_nhac(goc)
        assert len(cho_ban_tin) == 1
        assert cho_ban_tin[0]["loai"] == "video_moi"
        assert cho_ban_tin[0]["kenh"] == "TL1"
        assert cho_ban_tin[0]["tieu_de"] == "Hôm nay kênh TL1 chưa có video mới"

        # Lấy một lần là hết -> lần lấy sau rỗng (đã "gộp vào bản tin" rồi).
        assert bao_dong.lay_va_xoa_cac_tin_nhac(goc) == []

    def test_khong_co_tin_nhac_nao_thi_tra_danh_sach_rong(self, tmp_path):
        assert bao_dong.lay_va_xoa_cac_tin_nhac(str(tmp_path)) == []


class TestGuiThatBaiKhongNemLoi:
    def test_gui_loi_tra_false_ghi_log_va_trang_thai(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        goc = str(tmp_path)

        def _hong(*a, **k):
            raise RuntimeError("mất mạng giả lập")

        monkeypatch.setattr(bao_dong, "_http_post", _hong)

        ket_qua = bao_dong.bao_dong("tram_chet", "Trạm không phản hồi", goc=goc, bay_gio=123.0)
        assert ket_qua is False  # không ném Exception ra ngoài test

        duong_log = os.path.join(goc, "workspace", bao_dong.LOI_LOG_FILENAME)
        assert os.path.isfile(duong_log)
        with open(duong_log, "r", encoding="utf-8") as tep:
            noi_dung = tep.read()
        assert "tram_chet" in noi_dung
        assert "mất mạng giả lập" in noi_dung

        trang_thai = bao_dong.doc_trang_thai_gui(goc)
        assert trang_thai["gui_that_bai_lan_cuoi"] == 123.0
        assert trang_thai["loai_that_bai_lan_cuoi"] == "tram_chet"
        assert "mất mạng giả lập" in trang_thai["loi_that_bai_lan_cuoi"]

    def test_chua_that_bai_lan_nao_thi_trang_thai_rong(self, tmp_path):
        assert bao_dong.doc_trang_thai_gui(str(tmp_path)) == {}

    def test_gui_khan_loi_van_khong_nem_va_van_ghi_trang_thai(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        goc = str(tmp_path)
        monkeypatch.setattr(
            bao_dong, "_http_post",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bot bị chặn")),
        )

        ket_qua = bao_dong.bao_dong_khan(
            "license_windows", "Windows sắp hết hạn", "Bật lại máy trong 3 ngày tới",
            "Máy sẽ tự tắt và ngừng đăng video", goc=goc,
        )
        assert ket_qua is False
        assert bao_dong.doc_trang_thai_gui(goc)["loai_that_bai_lan_cuoi"] == "license_windows"
