"""Gỡ chặn YouTube: proxy + cookie trình duyệt kênh — `core/mang_youtube.py`.

Đêm 22/09/2026 ba kênh chết ở khâu `kich-ban` vì YouTube chặn IP của VPS (đo
được: *"Sign in to confirm you're not a bot"*, `IpBlocked` kèm *"an IP belonging
to a cloud provider"*, và có cookie thì thành *"Requested format is not
available"* trên cả video đối chứng `dQw4w9WgXcQ`).

Bộ kiểm này canh bốn lời hứa của bản vá, và **lời hứa thứ nhất là nặng nhất**:

1. Máy không có `mang-youtube.json` phải chạy **y hệt** như trước — không thêm
   một lượt gọi nào, không thêm một khoá tuỳ chọn nào. Hàng trăm máy khách
   đang chạy tốt, không ai được trả giá cho sự cố của một VPS.
2. Có khai proxy thì proxy phải xuống **cả ba** đường ra mạng: `yt-dlp`, tệp
   phụ đề tải bằng `urllib`, và `youtube-transcript-api`.
3. Đọc cookie hỏng (trình duyệt đang mở) thì **đi tiếp không cookie**, kèm một
   dòng nhật ký nói rõ vì sao — chứ không làm vỡ cả lượt chạy đêm.
4. Câu lỗi phải nói được bản chất cho người thường đọc lúc 2 giờ sáng.

Không bài nào ở đây gọi mạng thật.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import mang_youtube as my  # noqa: E402
from core import script_video as sv  # noqa: E402
from core import youtube as yt  # noqa: E402


@pytest.fixture(autouse=True)
def _quen_bo_nho():
    """Cấu hình và kho cookie đều nhớ suốt tiến trình — dọn giữa các bài."""
    my.quen_bo_nho_dem()
    yield
    my.quen_bo_nho_dem()


def _ghi_cau_hinh(thu_muc, **khoa) -> str:
    goc = str(thu_muc)
    with open(os.path.join(goc, my.MANG_FILENAME), "w", encoding="utf-8") as tep:
        json.dump(khoa, tep)
    return goc


def _ho_so_gia(thu_muc) -> str:
    """Dựng thư mục `<goc>/TL3-T7/Data/profile` cạnh một `MyTool` giả."""
    goc = os.path.join(str(thu_muc), "MyTool")
    ho_so = os.path.join(str(thu_muc), "TL3-T7", "Data", "profile")
    os.makedirs(goc, exist_ok=True)
    os.makedirs(ho_so, exist_ok=True)
    return goc, ho_so


class _YdlGia:
    """`YoutubeDL` giả: ghi lại tuỳ chọn, rồi diễn theo `kich_ban`."""

    def __init__(self, kich_ban):
        self.kich_ban = list(kich_ban)
        self.tuy_chon = []

    def __call__(self, tuy):
        self.tuy_chon.append(dict(tuy))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, _url, download=False):
        ra = self.kich_ban.pop(0)
        if isinstance(ra, Exception):
            raise ra
        return ra


def _cam_ydl(monkeypatch, kich_ban):
    may = _YdlGia(kich_ban)
    monkeypatch.setattr(yt, "_ydl_class", lambda: may)
    # Không nấc nào được ngủ: bài kiểm phải xong trong tích tắc.
    monkeypatch.setattr(yt.time, "sleep", lambda _s: None)
    return may


# ── Lời hứa 1: không có tệp cấu hình thì KHÔNG ĐỔI GÌ ───────────────────────


class TestKhongCauHinhThiYHetNhuCu:

    def test_thieu_tep_thi_cau_hinh_rong_va_khong_nem_loi(self, tmp_path):
        cau = my.doc_cau_hinh(str(tmp_path))
        assert cau == my.CauHinhMang()
        assert cau.trong

    def test_tep_hong_cu_phap_cung_khong_giet_luot_chay(self, tmp_path):
        """Một dấu phẩy thừa lúc 2 giờ sáng không được làm chết lượt chạy đêm."""
        with open(os.path.join(str(tmp_path), my.MANG_FILENAME), "w",
                  encoding="utf-8") as tep:
            tep.write('{"proxy": "http://p",,,}')
        assert my.doc_cau_hinh(str(tmp_path)).trong

    def test_tep_rong_ruot_cung_la_net_cu(self, tmp_path):
        goc = _ghi_cau_hinh(tmp_path, proxy="", dung_cookie=False)
        assert my.doc_cau_hinh(goc).trong
        assert [n.ten for n in my.cac_nac(my.doc_cau_hinh(goc), goc)] == ["thẳng"]

    def test_chi_mot_nac_va_nac_do_khong_them_tuy_chon_nao(self, tmp_path):
        nac = my.cac_nac(my.doc_cau_hinh(str(tmp_path)), str(tmp_path))
        assert len(nac) == 1 and nac[0].tran
        assert my.tuy_chon_ytdlp(nac[0]) == {}, (
            "thêm bất kỳ khoá nào vào tuỳ chọn yt-dlp của máy không khai cấu "
            "hình là đổi hành vi của toàn bộ máy khách")

    def test_ytdlp_nhan_dung_bo_tuy_chon_cu(self, monkeypatch):
        may = _cam_ydl(monkeypatch, [{"id": "abc"}])
        assert yt._extract("http://v", {"extract_flat": False}) == {"id": "abc"}
        assert len(may.tuy_chon) == 1, "chỉ được gọi MỘT lượt, không leo nấc nào"
        assert "proxy" not in may.tuy_chon[0]
        assert "cookiesfrombrowser" not in may.tuy_chon[0]

    def test_tai_tieng_khong_them_khoa_nao(self, monkeypatch, tmp_path):
        thay = {}

        def tai_gia(_lop, _url, thu_muc, khach, tuy_them=None):
            thay["tuy_them"] = tuy_them
            open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"x")

        monkeypatch.setattr(sv, "_tai_mot_khach", tai_gia)
        monkeypatch.setattr(yt, "_ydl_class", lambda: object)
        assert sv._tai_tieng("http://v", str(tmp_path)) == ""
        assert thay["tuy_them"] == {}


# ── Thứ tự các nấc: rẻ trước, đắt sau ───────────────────────────────────────


class TestThuTuCacNac:

    def test_co_proxy_thi_thu_thang_truoc(self, tmp_path):
        goc = _ghi_cau_hinh(tmp_path, proxy="http://u:p@host:1")
        assert [n.ten for n in my.cac_nac(my.doc_cau_hinh(goc), goc)] == [
            "thẳng", "proxy"]

    def test_du_bon_nac_khi_co_ca_proxy_lan_cookie(self, tmp_path):
        goc, ho_so = _ho_so_gia(tmp_path)
        _ghi_cau_hinh(goc, proxy="http://p", dung_cookie=True,
                      kenh_lay_cookie="TL3-T7")
        nac = my.cac_nac(my.doc_cau_hinh(goc), goc)
        assert [n.ten for n in nac] == ["thẳng", "cookie", "proxy", "proxy+cookie"]
        assert nac[1].ho_so == ho_so and not nac[1].proxy
        assert nac[3].ho_so == ho_so and nac[3].proxy == "http://p"

    def test_tat_thu_khong_proxy_truoc_thi_bo_hai_nac_dau(self, tmp_path):
        goc, _ = _ho_so_gia(tmp_path)
        _ghi_cau_hinh(goc, proxy="http://p", dung_cookie=True,
                      kenh_lay_cookie="TL3-T7", thu_khong_proxy_truoc=False)
        assert [n.ten for n in my.cac_nac(my.doc_cau_hinh(goc), goc)] == [
            "proxy", "proxy+cookie"]

    def test_khong_proxy_ma_tat_thu_thang_thi_van_con_duong_di(self, tmp_path):
        """`thu_khong_proxy_truoc=false` mà quên khai proxy → đừng câm hẳn."""
        goc = _ghi_cau_hinh(tmp_path, thu_khong_proxy_truoc=False)
        assert [n.ten for n in my.cac_nac(my.doc_cau_hinh(goc), goc)] == ["thẳng"]

    def test_khai_sai_ma_kenh_thi_khong_dung_nac_cookie(self, tmp_path):
        """Hồ sơ không có thật mà vẫn dựng nấc cookie là mỗi video hỏng thêm một lượt."""
        goc, _ = _ho_so_gia(tmp_path)
        _ghi_cau_hinh(goc, dung_cookie=True, kenh_lay_cookie="TL9-" "KHONG-CO")
        assert [n.ten for n in my.cac_nac(my.doc_cau_hinh(goc), goc)] == ["thẳng"]

    def test_moi_nac_dung_mot_luot_khong_thu_lai_vo_han(self, monkeypatch):
        chan = RuntimeError("ERROR: Sign in to confirm you're not a bot")
        may = _cam_ydl(monkeypatch, [chan, chan])
        monkeypatch.setattr(my, "cac_nac", lambda *_a, **_k: [
            my.NAC_TRAN, my.Nac("proxy", proxy="http://p")])
        with pytest.raises(RuntimeError):
            yt._extract("http://v", {})
        assert len(may.tuy_chon) == 2, (
            "dấu chặn-theo-IP thì hỏi lại ba lần cũng ra ba lần y hệt — mỗi nấc "
            "đúng một lượt")


# ── Lời hứa 2: proxy xuống đủ cả ba đường ra mạng ───────────────────────────


class TestProxyXuongDungCho:

    def test_xuong_yt_dlp(self, monkeypatch):
        may = _cam_ydl(monkeypatch, [{"id": "abc"}])
        monkeypatch.setattr(my, "cac_nac",
                            lambda *_a, **_k: [my.Nac("proxy", proxy="http://p:9")])
        yt._extract("http://v", {})
        assert may.tuy_chon[0]["proxy"] == "http://p:9"

    def test_xuong_cookie_dung_bo_bon_yt_dlp_doi(self):
        nac = my.Nac("proxy+cookie", proxy="http://p", ho_so=r"C:\ho\so",
                     trinh_duyet="chrome")
        assert my.tuy_chon_ytdlp(nac) == {
            "proxy": "http://p",
            "cookiesfrombrowser": ("chrome", r"C:\ho\so", None, None),
        }

    def test_xuong_tep_phu_de_tai_bang_urllib(self, monkeypatch):
        """Địa chỉ tệp phụ đề ràng theo IP — xin một đằng tải một nẻo là hỏng."""
        thay = {}

        class _PhanHoi:
            def read(self):
                return b"WEBVTT\n\n00:00.000 --> 00:01.000\nxin chao\n"

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        def mo_gia(proxy):
            thay["proxy"] = proxy
            return lambda _dc, timeout=0: _PhanHoi()

        monkeypatch.setattr(my, "mo_url_qua_proxy", mo_gia)
        chu, vi_sao = sv._tai_chu("http://sub", proxy="http://p:9")
        assert chu == "xin chao" and vi_sao == ""
        assert thay["proxy"] == "http://p:9"

    def test_khong_proxy_thi_tep_phu_de_van_di_duong_cu(self, monkeypatch):
        def khong_duoc_goi(_p):
            raise AssertionError("không khai proxy thì đừng dựng opener nào")

        monkeypatch.setattr(my, "mo_url_qua_proxy", khong_duoc_goi)
        chu, _ = sv._tai_chu("http://sub",
                             mo_url=lambda _dc, timeout=0: _MoGia("WEBVTT\n\nxin chao\n"))
        assert chu == "xin chao"

    def test_xuong_youtube_transcript_api(self):
        """Bản 1.x nhận proxy ở HÀM DỰNG — không phải biến môi trường."""
        thay = {}

        class _ApiGia:
            def __init__(self, **tuy):
                thay.update(tuy)

            def fetch(self, _vid, languages=None):
                return []

        sv._mot_nac_thu_vien(_ApiGia, "abc", ["vi"],
                             my.proxy_transcript(my.Nac("proxy", proxy="http://p:9")),
                             None)
        cau_hinh = thay.get("proxy_config")
        assert cau_hinh is not None, "thiếu proxy_config là đường dự phòng vẫn chết"
        assert cau_hinh.to_requests_dict() == {"http": "http://p:9",
                                               "https": "http://p:9"}

    def test_transcript_khong_proxy_thi_dung_y_nhu_cu(self):
        thay = {}

        class _ApiGia:
            def __init__(self, **tuy):
                thay["tuy"] = tuy

            def fetch(self, _vid, languages=None):
                return []

        sv._mot_nac_thu_vien(_ApiGia, "abc", ["vi"], None, None)
        assert thay["tuy"] == {}

    def test_tai_tieng_nhan_proxy_o_vong_ngoai(self, monkeypatch, tmp_path):
        """Vòng ngoài là nấc mạng, vòng trong là ứng dụng giả — không đảo."""
        da_thu = []

        def tai_gia(_lop, _url, thu_muc, khach, tuy_them=None):
            da_thu.append((dict(tuy_them or {}).get("proxy", ""), khach))
            if not tuy_them:
                raise RuntimeError("Sign in to confirm you're not a bot")
            open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"x")

        monkeypatch.setattr(sv, "_tai_mot_khach", tai_gia)
        monkeypatch.setattr(yt, "_ydl_class", lambda: object)
        monkeypatch.setattr(my, "cac_nac", lambda *_a, **_k: [
            my.NAC_TRAN, my.Nac("proxy", proxy="http://p")])
        assert sv._tai_tieng("http://v", str(tmp_path)) == ""
        # Vét hết ứng dụng miễn phí rồi mới đụng tới proxy (tính tiền theo GB).
        assert [p for p, _ in da_thu[:len(sv.KHACH_YOUTUBE)]] == [""] * len(
            sv.KHACH_YOUTUBE)
        assert da_thu[len(sv.KHACH_YOUTUBE)][0] == "http://p"


class _MoGia:
    def __init__(self, chu):
        self._chu = chu.encode("utf-8")

    def read(self):
        return self._chu

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


# ── Lời hứa 3: cookie hỏng thì đi tiếp, và nói vì sao ───────────────────────


class TestCookieHongThiDiTiep:

    def test_doc_cookie_hong_thi_tra_none_va_ghi_ly_do(self, monkeypatch):
        import yt_dlp.cookies as kho

        def no(*_a, **_k):
            raise PermissionError("Could not copy Chrome cookie database")

        monkeypatch.setattr(kho, "extract_cookies_from_browser", no)
        dong = []
        assert my.kho_cookie(my.Nac("cookie", ho_so=r"C:\ho\so"), dong.append) is None
        assert dong and "cookie" in dong[0].lower()
        assert "trình duyệt đang mở" in dong[0], (
            "đọc log lúc 2 giờ sáng phải biết ngay là do trình duyệt đang mở")

    def test_phien_transcript_hong_thi_none_chu_khong_nem_loi(self, monkeypatch):
        monkeypatch.setattr(my, "kho_cookie", lambda *_a, **_k: None)
        assert my.phien_transcript(my.Nac("cookie", ho_so=r"C:\x")) is None

    def test_nac_cookie_hong_khong_lam_vo_ca_luot(self, monkeypatch):
        """Nấc cookie gãy → leo tiếp nấc proxy → vẫn ra dữ liệu."""
        # Nấc cookie gãy ở CẢ ba lượt thử lại — lỗi kho cookie không phải lỗi
        # mạng nhất thời, hỏi lại bao nhiêu lần cũng thế.
        may = _cam_ydl(monkeypatch, [
            RuntimeError("Sign in to confirm you're not a bot"),
            RuntimeError("Could not copy Chrome cookie database"),
            RuntimeError("Could not copy Chrome cookie database"),
            RuntimeError("Could not copy Chrome cookie database"),
            {"id": "abc"},
        ])
        monkeypatch.setattr(my, "cac_nac", lambda *_a, **_k: [
            my.NAC_TRAN,
            my.Nac("cookie", ho_so=r"C:\ho\so"),
            my.Nac("proxy", proxy="http://p"),
        ])
        dong = []
        assert yt._extract("http://v", {}, on_log=dong.append) == {"id": "abc"}
        chu = " ".join(dong)
        assert my.LOI_COOKIE.split("(")[0].strip() in chu
        assert "qua được bằng nấc «proxy»" in chu, (
            "nhật ký phải nói NẤC NÀO CỨU ĐƯỢC — đó là thứ đỡ cho lần sau khỏi "
            "phải đo lại từ đầu")

    def test_la_loi_cookie_phan_biet_dung_thu_pham(self):
        assert my.la_loi_cookie("Could not copy Chrome cookie database")
        assert my.la_loi_cookie("sqlite3.OperationalError: database is locked")
        assert not my.la_loi_cookie("Sign in to confirm you're not a bot")

    def test_cookie_doc_duoc_ma_youtube_khong_nhan_thi_noi_khac_han(self):
        """Đo thật 22/09/2026: 92 cookie đọc ngon lành, YouTube vẫn không nhận.

        Hai kiểu hỏng, hai việc phải làm khác hẳn: một cái đóng trình duyệt là
        xong, một cái chạy lại bao nhiêu lần cũng thế.
        """
        cau = my.giai_thich_loi_cookie(
            "ERROR: [youtube] dQw4w9WgXcQ: The page needs to be reloaded.")
        assert cau == my.LOI_COOKIE_CHET
        assert "TẮT dung_cookie" in cau
        assert "văng luôn đăng nhập" in cau, (
            "trình duyệt kênh là thứ dùng để ĐĂNG VIDEO — mất đăng nhập của nó "
            "đắt hơn nhiều lần một đoạn lời thoại")
        assert my.giai_thich_loi_cookie("database is locked") == my.LOI_COOKIE

    def test_nac_thang_luon_dung_truoc_nac_cookie(self, tmp_path):
        """Đo thật: có ca nấc cookie LÀM HỎNG lượt mà nấc thẳng đang chạy được."""
        goc, _ = _ho_so_gia(tmp_path)
        _ghi_cau_hinh(goc, dung_cookie=True, kenh_lay_cookie="TL3-T7")
        ten = [n.ten for n in my.cac_nac(my.doc_cau_hinh(goc), goc)]
        assert ten == ["thẳng", "cookie"]

    def test_mac_dinh_khong_muon_cookie(self):
        """Mượn cookie có cái giá riêng — không ai được bật hộ người dùng."""
        assert my.CauHinhMang().dung_cookie is False


# ── Lời hứa 4: câu lỗi cho người thường ─────────────────────────────────────


class TestCauLoiNguoiThuongHieu:

    @pytest.mark.parametrize("chu", [
        "ERROR: [youtube] abc: Sign in to confirm you're not a bot",
        "ERROR: [youtube] abc: Sign in to confirm you\u2019re not a bot",
        "IpBlocked: You are doing requests from an IP belonging to a cloud provider",
    ])
    def test_nhan_dung_dau_chac_chan(self, chu):
        assert my.la_dau_chan_ip(chu) == "chac"

    @pytest.mark.parametrize("chu", [
        "ERROR: Requested format is not available",
        "ERROR: [youtube] dQw4w9WgXcQ: No video formats found!",
        "PoTokenRequired",
    ])
    def test_nhan_dung_dau_nghi_ngo(self, chu):
        assert my.la_dau_chan_ip(chu) == "nghi"

    @pytest.mark.parametrize("chu", [
        "Video unavailable", "This video is private",
        "YouTube chặn tải phụ đề (lỗi 429)", "",
    ])
    def test_khong_vo_doan_cho_loi_thuong(self, chu):
        assert my.la_dau_chan_ip(chu) == "", (
            "429 là chặn theo NHỊP HỎI, vài giây sau là qua — bắt chủ dự án đi "
            "thuê proxy để chữa nó là chữa nhầm bệnh")

    def test_cau_loi_noi_du_ai_chan_chan_gi_va_go_the_nao(self):
        cau = my.cau_loi_chan_ip("chac", "Sign in to confirm you're not a bot")
        assert "YouTube đang chặn địa chỉ mạng của máy này" in cau
        assert "IP máy chủ thuê" in cau
        assert "proxy IP dân cư" in cau and "mang-youtube.json" in cau
        assert "Sign in to confirm" in cau, "vẫn phải giữ nguyên văn để lần ra được"

    def test_lay_script_bi_chan_bot_thi_noi_dung_ban_chat(self, monkeypatch):
        monkeypatch.setattr(
            yt, "_extract",
            lambda *_a, **_k: (_ for _ in ()).throw(
                RuntimeError("ERROR: Sign in to confirm you're not a bot")))
        ket = sv.lay_script("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert "proxy IP dân cư" in ket.loi
        assert "không mở được video" not in ket.loi

    def test_mo_duoc_ma_rong_khong_duoc_noi_la_video_thieu_phu_de(self, monkeypatch):
        """Bộ mặt thứ hai của cùng một cái chặn: qua cửa mà tay trắng."""
        monkeypatch.setattr(yt, "_extract", lambda *_a, **_k: {})
        monkeypatch.setattr(sv, "_tu_thu_vien", lambda _: ("", ""))
        ket = sv.lay_script("http://v", cho_phep_nghe=False)
        assert "chặn địa chỉ mạng" in ket.loi
        assert "video không có phụ đề" not in ket.loi, (
            "đổ lỗi cho video là dắt người ta đi đổi video — video nào cũng thế")

    def test_video_khong_co_phu_de_that_thi_van_noi_nhu_cu(self, monkeypatch):
        monkeypatch.setattr(yt, "_extract", lambda *_a, **_k: {
            "id": "abc", "title": "T", "duration": 60})
        monkeypatch.setattr(sv, "_tu_thu_vien", lambda _: ("", ""))
        ket = sv.lay_script("http://v", cho_phep_nghe=False)
        assert ket.loi.startswith("video không có phụ đề")

    def test_duong_tu_nghe_hong_vi_chan_thi_cung_noi_chuyen_proxy(self, monkeypatch):
        monkeypatch.setattr(yt, "_extract", lambda *_a, **_k: {
            "id": "abc", "title": "T", "duration": 60})
        monkeypatch.setattr(sv, "_tu_thu_vien", lambda _: ("", ""))
        monkeypatch.setattr(sv, "_tu_nghe", lambda *_a, **_k: (
            "", "", "không tải được tiếng của video (Sign in to confirm you're "
            "not a bot)"))
        ket = sv.lay_script("http://v", cho_phep_nghe=True)
        assert "proxy IP dân cư" in ket.loi
