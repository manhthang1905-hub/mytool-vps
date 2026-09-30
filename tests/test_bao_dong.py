"""Báo động ra NGOÀI máy (`core.bao_dong`) + cầu nối `core.alerts.canh_bao_ra_ngoai`.

Bối cảnh: `core/alerts.py` trước đây chỉ đổi màu trong giao diện — không ai
thấy nếu không ngồi trước máy. `core/bao_dong.py` thêm đường bắn Telegram/
webhook RA NGOÀI, mặc định TẮT (chưa có `bao-dong.json` là im lặng), có chống
spam theo `loai` sự cố. KHÔNG được gọi mạng thật trong test — mọi test dưới
đây monkeypatch đúng một điểm chạm mạng: `bao_dong._http_post`.
"""

from __future__ import annotations

import json

import pytest

from core import alerts, bao_dong


def _ghi_cau_hinh(goc, **noi_dung):
    with open(bao_dong.bao_dong_path_for(str(goc)), "w", encoding="utf-8") as tep:
        json.dump(noi_dung, tep, ensure_ascii=False)


@pytest.fixture(autouse=True)
def _don_bo_nho_chong_spam():
    """Không còn việc gì phải dọn: bộ chống spam nay sống trên đĩa, theo
    TỪNG `goc` (xem `core/bao_dong.py`, mục "Chống lặp SỐNG TRÊN ĐĨA") — mỗi
    test dùng một `tmp_path` riêng nên tự nhiên đã cô lập với nhau, không còn
    biến RAM cấp module (`_LAN_BAN_CUOI` của bản cũ) để mà rò rỉ giữa các
    test. Giữ fixture rỗng này lại (thay vì xoá) để không phải sửa mọi test
    hiện có — và để không lỡ gọi `quen_lich_su_chong_spam()` KHÔNG truyền
    `goc`, tức là dọn nhầm `workspace/bao-dong-da-gui.json` THẬT của kho này."""
    yield


class TestChuaCauHinhThiImLang:
    def test_khong_co_file_thi_khong_lam_gi(self, tmp_path, monkeypatch):
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append((a, k)))
        ket_qua = bao_dong.bao_dong("vi_can", "Ví sắp hết", "chi tiết", goc=str(tmp_path))
        assert ket_qua is False
        assert goi == []

    def test_file_co_nhung_khong_dien_kenh_nao_thi_im_lang(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, cooldown_giay=1)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append((a, k)))
        assert bao_dong.bao_dong("vi_can", "t", goc=str(tmp_path)) is False
        assert goi == []

    def test_enabled_false_thi_im_lang_du_da_dien_telegram(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(
            tmp_path,
            enabled=False,
            telegram={"bot_token": "123:abc", "chat_id": "999"},
        )
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append((a, k)))
        assert bao_dong.bao_dong("vi_can", "t", goc=str(tmp_path)) is False
        assert goi == []

    def test_file_json_hong_thi_im_lang_khong_nem_loi(self, tmp_path, monkeypatch):
        (tmp_path / bao_dong.BAO_DONG_FILENAME).write_text("{khong phai json", encoding="utf-8")
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append((a, k)))
        assert bao_dong.bao_dong("vi_can", "t", goc=str(tmp_path)) is False
        assert goi == []


class TestGuiDungKenh:
    def test_telegram_goi_dung_url_va_noi_dung(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "123456:ABC", "chat_id": "999"})
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append((a, k)))

        ket_qua = bao_dong.bao_dong("tram_chet", "Trạm không phản hồi", "5 phút rồi", goc=str(tmp_path))

        assert ket_qua is True
        assert len(goi) == 1
        (url, payload), kwargs = goi[0]
        assert url == "https://api.telegram.org/bot123456:ABC/sendMessage"
        assert payload["chat_id"] == "999"
        assert "Trạm không phản hồi" in payload["text"]
        assert "5 phút rồi" in payload["text"]

    def test_webhook_goi_dung_url_va_headers(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(
            tmp_path,
            webhook={"url": "https://vidu.test/hoi-chuong", "headers": {"X-Key": "bi-mat"}},
        )
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append((a, k)))

        ket_qua = bao_dong.bao_dong("dia_day", "Đĩa sắp đầy", goc=str(tmp_path))

        assert ket_qua is True
        (url, payload), kwargs = goi[0]
        assert url == "https://vidu.test/hoi-chuong"
        assert payload["loai"] == "dia_day"
        assert kwargs["headers"] == {"X-Key": "bi-mat"}

    def test_ca_hai_kenh_cung_bat_thi_ca_hai_cung_duoc_goi(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(
            tmp_path,
            telegram={"bot_token": "1:a", "chat_id": "1"},
            webhook={"url": "https://vidu.test/hoi-chuong"},
        )
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(a[0]))
        assert bao_dong.bao_dong("lich_bo_lo", "t", goc=str(tmp_path)) is True
        assert len(goi) == 2
        assert any("telegram.org" in u for u in goi)
        assert any("vidu.test" in u for u in goi)

    def test_mot_kenh_loi_khong_chan_kenh_kia(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(
            tmp_path,
            telegram={"bot_token": "1:a", "chat_id": "1"},
            webhook={"url": "https://vidu.test/hoi-chuong"},
        )

        def _post(url, payload, **kw):
            if "telegram.org" in url:
                raise RuntimeError("mạng lỗi")

        monkeypatch.setattr(bao_dong, "_http_post", _post)
        assert bao_dong.bao_dong("lich_bo_lo", "t", goc=str(tmp_path)) is True

    def test_tat_ca_kenh_loi_thi_tra_false(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})

        def _post(*a, **k):
            raise RuntimeError("mạng lỗi")

        monkeypatch.setattr(bao_dong, "_http_post", _post)
        assert bao_dong.bao_dong("lich_bo_lo", "t", goc=str(tmp_path)) is False

    def test_khong_bao_gio_nem_loi_ra_ngoai(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        monkeypatch.setattr(
            bao_dong, "_http_post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        # Không raise -> test tự fail nếu bao_dong() để lọt exception.
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path)) is False


class TestChongSpam:
    def test_cung_loai_trong_khoang_lang_thi_bi_chan(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=3600)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("tram_chet", "t", goc=str(tmp_path), bay_gio=1000.0) is True
        assert bao_dong.bao_dong("tram_chet", "t", goc=str(tmp_path), bay_gio=1000.0 + 60) is False
        assert len(goi) == 1

    def test_qua_khoang_lang_thi_ban_lai_duoc(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=100)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=0.0) is True
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=50.0) is False
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=101.0) is True
        assert len(goi) == 2

    def test_loai_khac_nhau_khong_lam_lay_lan_nhau(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"})
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("vi_can", "t", goc=str(tmp_path), bay_gio=0.0) is True
        assert bao_dong.bao_dong("tram_chet", "t", goc=str(tmp_path), bay_gio=0.5) is True
        assert len(goi) == 2

    def test_cooldown_tu_dinh_trong_config_duoc_ton_trong(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=5)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=0.0) is True
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=4.0) is False
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=6.0) is True
        assert len(goi) == 2

    def test_ke_ca_gui_loi_van_tinh_vao_khoang_lang(self, tmp_path, monkeypatch):
        """Gửi lỗi vẫn tiêu một lượt chống spam — tránh dội liên tục khi
        chính kênh báo cũng đang hỏng (xem lý do trong docstring module)."""
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=100)
        so_lan_goi = []

        def _post(*a, **k):
            so_lan_goi.append(1)
            raise RuntimeError("mạng lỗi")

        monkeypatch.setattr(bao_dong, "_http_post", _post)
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=0.0) is False
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=1.0) is False
        assert len(so_lan_goi) == 1

    def test_quen_lich_su_cho_ban_lai_ngay(self, tmp_path, monkeypatch):
        _ghi_cau_hinh(tmp_path, telegram={"bot_token": "1:a", "chat_id": "1"}, cooldown_giay=3600)
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))

        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=0.0) is True
        # Kho chống lặp giờ sống THEO `goc` (mỗi cài đặt một kho riêng) — phải
        # truyền đúng `goc=str(tmp_path)` thì mới dọn đúng kho của TEST này,
        # không phải kho thật của chính kho mã nguồn.
        bao_dong.quen_lich_su_chong_spam("x", goc=str(tmp_path))
        assert bao_dong.bao_dong("x", "t", goc=str(tmp_path), bay_gio=1.0) is True
        assert len(goi) == 2


class TestCanhBaoRaNgoai:
    """Cầu nối `core.alerts.canh_bao_ra_ngoai` — dùng lại `low_balance_warning_vnd`
    qua `assess_balance()` đã có sẵn, bắn tiếp sang `core.bao_dong`."""

    def test_muc_ok_khong_goi_bao_dong(self, tmp_path, monkeypatch):
        goi = []
        monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: goi.append((a, k)) or True)
        alert = alerts.assess_balance(1_000_000_000_000, floor_vnd=50_000)  # còn nhiều -> OK
        assert alert.level == alerts.LEVEL_OK
        assert alerts.canh_bao_ra_ngoai(alert, goc=str(tmp_path)) is False
        assert goi == []

    def test_muc_low_goi_bao_dong_voi_dung_loai_va_chu(self, tmp_path, monkeypatch):
        goi = []
        monkeypatch.setattr(
            bao_dong, "bao_dong", lambda loai, tieu_de, chi_tiet="", **k: goi.append((loai, tieu_de, chi_tiet, k)) or True
        )
        alert = alerts.assess_balance(1, floor_vnd=50_000)  # gần như trống -> LOW/EMPTY
        assert alert.is_warning
        ket_qua = alerts.canh_bao_ra_ngoai(alert, goc=str(tmp_path))
        assert ket_qua is True
        assert len(goi) == 1
        loai, tieu_de, chi_tiet, kwargs = goi[0]
        assert loai == "vi_can"
        assert tieu_de == alert.title
        assert kwargs["goc"] == str(tmp_path)

    def test_end_to_end_khong_gia_lap_bao_dong_van_im_lang_neu_chua_cau_hinh(self, tmp_path, monkeypatch):
        """Không monkeypatch `bao_dong.bao_dong` — kiểm tra đường dây thật
        chạy hết tới `core.bao_dong` mà vẫn im lặng đúng nghĩa (không lỗi,
        không gọi mạng) vì `tmp_path` chưa có `bao-dong.json`."""
        goi = []
        monkeypatch.setattr(bao_dong, "_http_post", lambda *a, **k: goi.append(1))
        alert = alerts.assess_balance(1, floor_vnd=50_000)
        assert alerts.canh_bao_ra_ngoai(alert, goc=str(tmp_path)) is False
        assert goi == []
