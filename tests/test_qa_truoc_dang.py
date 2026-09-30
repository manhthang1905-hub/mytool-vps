"""Cổng QA trước khi đăng (`core.qa_truoc_dang`) — điều kiện để sau này bật
`tu_duyet: true` mà không phải giao thẳng con mắt người cho máy.

Phần không cần FFmpeg (đủ file, tiêu đề, phụ đề, ảnh bìa) chạy trên mọi máy.
Phần cần dựng video thật (`TestVideoThat`) tự bỏ qua khi máy không có FFmpeg —
cùng nếp `tests/test_lam_sach.py`.
"""

from __future__ import annotations

import os
import subprocess

import pytest
from PIL import Image

from core import ban_giao_dang, ke_hoach_dang, qa_truoc_dang
from core.dung_video import tim_ffmpeg

FFMPEG = tim_ffmpeg()


# ── Tiện ích dựng gói giả trong tmp_path ─────────────────────────────────────


def _ghi_anh(duong: str, rong: int = 1920, cao: int = 1080, *, dung_luong_them: int = 0) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    Image.new("RGB", (rong, cao), color=(80, 120, 200)).save(duong, quality=90)
    if dung_luong_them:
        with open(duong, "ab") as tep:
            tep.write(b"\0" * dung_luong_them)


def _ghi_srt(duong: str, *, khoi: list) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        for i, (bd, kt, chu) in enumerate(khoi, start=1):
            tep.write("{0}\n{1} --> {2}\n{3}\n\n".format(i, bd, kt, chu))


def _goi_toi_thieu(thu_muc: str) -> None:
    """Một gói ĐỦ file cơ bản (không có FFmpeg thật) — dùng cho các bài kiểm
    không đụng tới video."""
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "8-video.mp4"), "wb") as tep:
        tep.write(b"khong phai video that")
    _ghi_srt(os.path.join(thu_muc, "3-phu-de.srt"),
            khoi=[("00:00:00,000", "00:00:02,000", "Xin chào")])
    _ghi_anh(os.path.join(thu_muc, "thumb_001.png"))
    with open(os.path.join(thu_muc, "1-binh-luan.txt"), "w", encoding="utf-8") as tep:
        tep.write("Cảm ơn đã xem!")


# ── Đủ file ───────────────────────────────────────────────────────────────────


class TestDuFile:
    def test_thu_muc_khong_ton_tai(self, tmp_path):
        kq = qa_truoc_dang.kiem_thu_muc_goi(str(tmp_path / "khong-co"))
        assert not kq.dat
        assert any("không thấy thư mục" in m for m in kq.loi)

    def test_thieu_ca_ba_bao_du_ba_loi(self, tmp_path):
        (tmp_path / "goi-trong").mkdir()
        kq = qa_truoc_dang.kiem_thu_muc_goi(str(tmp_path / "goi-trong"), tieu_de="Tiêu đề")
        assert not kq.dat
        assert any("thiếu video" in m for m in kq.loi)
        assert any("thiếu phụ đề" in m for m in kq.loi)
        assert any("thiếu ảnh bìa" in m for m in kq.loi)

    def test_thieu_binh_luan_chi_la_canh_bao_khong_chan(self, tmp_path):
        goi = str(tmp_path / "g")
        _goi_toi_thieu(goi)
        os.remove(os.path.join(goi, "1-binh-luan.txt"))
        kq = qa_truoc_dang.kiem_thu_muc_goi(goi, tieu_de="Tiêu đề hợp lệ")
        assert any("1-binh-luan.txt" in m for m in kq.canh_bao)
        # Thiếu bình luận không được nằm trong lỗi chặn đăng.
        assert not any("bình luận" in m.lower() for m in kq.loi)

    def test_goi_kieu_cu_ten_tep_la_tieu_de_van_nhan_duoc(self, tmp_path):
        """Hai gói cũ nhất trong DONE/TL1-T7 đặt tên tệp = tiêu đề video, không
        theo quy ước `8-video.mp4`/`3-phu-de.srt` — QA không được chặn nhầm."""
        goi = str(tmp_path / "g")
        os.makedirs(goi, exist_ok=True)
        with open(os.path.join(goi, "Một Tiêu Đề Video Nào Đó.mp4"), "wb") as tep:
            tep.write(b"gia")
        _ghi_srt(os.path.join(goi, "Một Tiêu Đề Video Nào Đó.srt"),
                khoi=[("00:00:00,000", "00:00:01,000", "A")])
        _ghi_anh(os.path.join(goi, "Một Tiêu Đề Video Nào Đó.png"))
        kq = qa_truoc_dang.kiem_thu_muc_goi(goi, tieu_de="Tiêu đề hợp lệ")
        assert not any("thiếu video" in m for m in kq.loi)
        assert not any("thiếu phụ đề" in m for m in kq.loi)
        assert not any("thiếu ảnh bìa" in m for m in kq.loi)


# ── Tiêu đề / mô tả ───────────────────────────────────────────────────────────


class TestTieuDe:
    def test_rong_bao_loi(self):
        assert any("chưa có tiêu đề" in m for m in qa_truoc_dang._kiem_tieu_de(""))

    def test_qua_100_ky_tu_bao_loi(self):
        loi = qa_truoc_dang._kiem_tieu_de("x" * 101)
        assert any("100 ký tự" in m for m in loi)

    def test_dung_100_ky_tu_khong_loi(self):
        assert qa_truoc_dang._kiem_tieu_de("x" * 100) == []

    def test_mo_ta_rong_chi_canh_bao(self, tmp_path):
        goi = str(tmp_path / "g")
        _goi_toi_thieu(goi)
        kq = qa_truoc_dang.kiem_thu_muc_goi(goi, tieu_de="Đủ tiêu đề", mo_ta="")
        assert any("chưa có mô tả" in m for m in kq.canh_bao)
        assert kq.dat  # thiếu mô tả không chặn


# ── Phụ đề ───────────────────────────────────────────────────────────────────


class TestSrt:
    def test_parse_duoc_khong_loi(self, tmp_path):
        duong = str(tmp_path / "p.srt")
        _ghi_srt(duong, khoi=[("00:00:00,000", "00:00:02,000", "Chào bạn")])
        loi, canh_bao = qa_truoc_dang._kiem_srt(duong, giay_video=10.0)
        assert loi == []
        assert canh_bao == []

    def test_khoi_rong_chu_bi_canh_bao(self, tmp_path):
        duong = str(tmp_path / "p.srt")
        _ghi_srt(duong, khoi=[("00:00:00,000", "00:00:02,000", "Chào"),
                              ("00:00:02,000", "00:00:04,000", "")])
        _, canh_bao = qa_truoc_dang._kiem_srt(duong, giay_video=10.0)
        assert any("không có chữ" in m for m in canh_bao)

    def test_moc_cuoi_vuot_video_bao_loi(self, tmp_path):
        duong = str(tmp_path / "p.srt")
        _ghi_srt(duong, khoi=[("00:00:00,000", "00:00:20,000", "Chào")])
        loi, _ = qa_truoc_dang._kiem_srt(duong, giay_video=10.0)
        assert any("vượt quá độ dài video" in m for m in loi)

    def test_khong_doc_duoc_khoi_nao_bao_loi(self, tmp_path):
        duong = str(tmp_path / "p.srt")
        with open(duong, "w", encoding="utf-8") as tep:
            tep.write("chữ không có mốc thời gian nào cả")
        loi, _ = qa_truoc_dang._kiem_srt(duong, giay_video=10.0)
        assert loi


# ── Ảnh bìa ──────────────────────────────────────────────────────────────────


class TestThumbnail:
    def test_dung_chuan_khong_loi(self, tmp_path):
        duong = str(tmp_path / "a.png")
        _ghi_anh(duong, 1920, 1080)
        loi, canh_bao = qa_truoc_dang._kiem_thumbnail(duong)
        assert loi == []

    def test_nho_hon_toi_thieu_bao_loi(self, tmp_path):
        duong = str(tmp_path / "a.png")
        _ghi_anh(duong, 640, 360)
        loi, _ = qa_truoc_dang._kiem_thumbnail(duong)
        assert any("nhỏ hơn mức tối thiểu" in m for m in loi)

    def test_le_ti_le_bao_loi(self, tmp_path):
        duong = str(tmp_path / "a.png")
        _ghi_anh(duong, 1920, 1200)  # vuông hơn hẳn 16:9
        loi, _ = qa_truoc_dang._kiem_thumbnail(duong)
        assert any("lệch tỉ lệ" in m for m in loi)

    def test_nang_hon_2mb_bao_loi(self, tmp_path):
        duong = str(tmp_path / "a.png")
        _ghi_anh(duong, 1920, 1080, dung_luong_them=3 * 1024 * 1024)
        loi, _ = qa_truoc_dang._kiem_thumbnail(duong)
        assert any("vượt mức khuyên dùng" in m for m in loi)

    def test_hong_khong_mo_duoc_bao_loi(self, tmp_path):
        duong = str(tmp_path / "a.png")
        with open(duong, "wb") as tep:
            tep.write(b"khong phai anh")
        loi, _ = qa_truoc_dang._kiem_thumbnail(duong)
        assert any("mở không được" in m for m in loi)

    def test_ti_le_gan_1376x768_khong_bi_bat_oan(self, tmp_path):
        """Ảnh bìa thật của cả tám gói trong DONE/ đều 1376x768 — lệch 16:9
        một chút vì làm tròn, KHÔNG được coi là lỗi."""
        duong = str(tmp_path / "a.png")
        _ghi_anh(duong, 1376, 768)
        loi, _ = qa_truoc_dang._kiem_thumbnail(duong)
        assert loi == []


# ── Độ dài / độ phân giải (thuần, không cần FFmpeg) ──────────────────────────


class TestDoDaiDoPhanGiai:
    def test_trong_dung_sai_khong_loi(self):
        assert qa_truoc_dang._kiem_do_dai(
            giay_video=900, phut_muc_tieu=15, chenh_cho_phep=0.15,
            do_dai_tu_do=False, do_dai_theo_goc=False) == []

    def test_ngoai_dung_sai_bao_loi(self):
        loi = qa_truoc_dang._kiem_do_dai(
            giay_video=1200, phut_muc_tieu=15, chenh_cho_phep=0.15,
            do_dai_tu_do=False, do_dai_theo_goc=False)
        assert any("ngoài khoảng cho phép" in m for m in loi)

    def test_do_dai_tu_do_bo_qua_kiem(self):
        assert qa_truoc_dang._kiem_do_dai(
            giay_video=99999, phut_muc_tieu=15, chenh_cho_phep=0.15,
            do_dai_tu_do=True, do_dai_theo_goc=False) == []

    def test_thap_hon_cau_hinh_bao_loi(self):
        loi, canh_bao = qa_truoc_dang._kiem_do_phan_giai(1280, 720, "1080p")
        assert any("thấp hơn cấu hình kênh" in m for m in loi)
        assert canh_bao == []

    def test_cao_hon_cau_hinh_chi_canh_bao(self):
        loi, canh_bao = qa_truoc_dang._kiem_do_phan_giai(3840, 2160, "1080p")
        assert loi == []
        assert any("CAO hơn cấu hình kênh" in m for m in canh_bao)

    def test_dung_cau_hinh_khong_loi_khong_canh_bao(self):
        loi, canh_bao = qa_truoc_dang._kiem_do_phan_giai(1920, 1080, "1080p")
        assert loi == [] and canh_bao == []

    def test_giu_nguyen_bo_qua_kiem(self):
        """"Giữ nguyên" chỉ tắt so với cấu hình kênh — sàn tối thiểu 1280x720
        vẫn còn, xem `test_duoi_san_toi_thieu_luon_la_loi`."""
        loi, canh_bao = qa_truoc_dang._kiem_do_phan_giai(1920, 1080, "Giữ nguyên")
        assert loi == [] and canh_bao == []

    def test_duoi_san_toi_thieu_luon_la_loi(self):
        loi, _ = qa_truoc_dang._kiem_do_phan_giai(640, 360, "Giữ nguyên")
        assert any("thấp hơn sàn tối thiểu" in m for m in loi)


# ── Ghi/xoá tệp kết quả ───────────────────────────────────────────────────────


class TestGhiKetQua:
    def test_dat_sach_thi_khong_ghi_gi_va_xoa_tep_cu(self, tmp_path):
        goi = str(tmp_path)
        duong_cu = os.path.join(goi, qa_truoc_dang.TEN_TEP_KET_QUA)
        with open(duong_cu, "w", encoding="utf-8") as tep:
            tep.write("lần trước hỏng")
        ket_qua = qa_truoc_dang.KetQuaQA()
        duong = qa_truoc_dang.ghi_ket_qua(goi, ket_qua)
        assert duong == ""
        assert not os.path.exists(duong_cu)

    def test_hong_thi_ghi_tep_co_ly_do(self, tmp_path):
        goi = str(tmp_path)
        ket_qua = qa_truoc_dang.KetQuaQA(loi=["thiếu video (không thấy tệp .mp4 nào trong gói)"])
        duong = qa_truoc_dang.ghi_ket_qua(goi, ket_qua)
        assert os.path.isfile(duong)
        noi_dung = open(duong, encoding="utf-8").read()
        assert "CHƯA ĐẠT" in noi_dung
        assert "thiếu video" in noi_dung


# ── Nối vào core.ban_giao_dang.ban_giao ──────────────────────────────────────


def _ghi_kenh_toi_thieu(goc, ma, **thay_doi):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    noi_dung = {"ma": ma, "phut_muc_tieu": 0}  # 0 = không kiểm độ dài, khỏi cần video thật
    noi_dung.update(thay_doi)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        for k, v in noi_dung.items():
            tep.write("{0}: {1}\n".format(k, v))


def _dung_luot_toi_thieu(goc, kenh, luot):
    """Một LƯỢT (`PROJECTS/AUTO/<kênh>/<lượt>`) đủ bộ để `ban_giao_dang.ban_giao`
    xuất gói — KHÁC cấu trúc gói đã xuất (`_goi_toi_thieu`): ảnh bìa của một
    lượt còn nằm trong `7-thumbnail/`, `ban_giao_dang._tim_thumb` chỉ tìm ở đó
    (xem `core/ban_giao_dang.py`), chưa được xuất phẳng ra cạnh video."""
    from core.auto import duong_luot

    thu_muc = duong_luot(goc, kenh, luot)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "8-video.mp4"), "wb") as tep:
        tep.write(b"khong phai video that")
    _ghi_srt(os.path.join(thu_muc, "3-phu-de.srt"),
            khoi=[("00:00:00,000", "00:00:02,000", "Xin chào")])
    _ghi_anh(os.path.join(thu_muc, "7-thumbnail", "CHON-1.jpg"))
    with open(os.path.join(thu_muc, "1-binh-luan.txt"), "w", encoding="utf-8") as tep:
        tep.write("Cảm ơn đã xem!")
    with open(os.path.join(thu_muc, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: Tiêu đề hợp lệ cho lượt thử\n")
    with open(os.path.join(thu_muc, "1-seo.txt"), "w", encoding="utf-8") as tep:
        tep.write("DESCRIPTION:\nMô tả thử\nKEYWORDS:\ntừ khoá, thử\n")
    return thu_muc


class TestNoiVaoBanGiao:
    @pytest.mark.skipif(not FFMPEG, reason="máy này không có FFmpeg")
    def test_qua_qa_thi_danh_san_sang_va_dat_gio(self, tmp_path):
        from core.auto import duong_luot

        goc = str(tmp_path)
        _ghi_kenh_toi_thieu(goc, "K1")  # phut_muc_tieu 0 -> bỏ qua kiểm độ dài
        thu_muc_luot = duong_luot(goc, "K1", "0001")
        # Video THẬT (không phải byte giả) — máy này có FFmpeg nên `ban_giao`
        # sẽ thật sự mở tệp ra kiểm, phải đưa cho nó thứ mở được.
        _dung_video_that(os.path.join(thu_muc_luot, "8-video.mp4"), giay=2,
                         rong=1920, cao=1080)
        _ghi_srt(os.path.join(thu_muc_luot, "3-phu-de.srt"),
                khoi=[("00:00:00,000", "00:00:01,000", "Xin chào")])
        _ghi_anh(os.path.join(thu_muc_luot, "7-thumbnail", "CHON-1.jpg"), 1920, 1080)
        with open(os.path.join(thu_muc_luot, "1-binh-luan.txt"), "w", encoding="utf-8") as tep:
            tep.write("Cảm ơn đã xem!")
        with open(os.path.join(thu_muc_luot, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
            tep.write("TITLE: Tiêu đề hợp lệ cho lượt thử\n")
        with open(os.path.join(thu_muc_luot, "1-seo.txt"), "w", encoding="utf-8") as tep:
            tep.write("DESCRIPTION:\nMô tả thử\nKEYWORDS:\ntừ khoá, thử\n")

        done = os.path.join(goc, "done")
        ma, moi = ban_giao_dang.ban_giao(goc, "K1", "0001", done, ngay="20/09/2026", gio="20:00")
        assert moi is True
        duong_loi = os.path.join(done, ma, qa_truoc_dang.TEN_TEP_KET_QUA)
        # Video 1920x1080 đúng khớp "1080p" mặc định -> không cảnh báo độ phân
        # giải; không đứng hình/đen (testsrc có chuyển động) -> QA sạch hoàn
        # toàn, không để lại tệp cạnh gói.
        noi_dung_loi = open(duong_loi, encoding="utf-8").read() if os.path.exists(duong_loi) else ""
        assert not os.path.exists(duong_loi), noi_dung_loi
        cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
        dong = dict(zip(cot, hang[0]))
        assert dong["Sẵn sàng"] == "x"
        assert dong["Ngày đăng"] == "20/09/2026"
        assert dong["Giờ đăng"] == "20:00"

    def test_khong_qua_qa_thi_khong_danh_san_sang_khong_dat_gio(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh_toi_thieu(goc, "K1")
        thu_muc_luot = _dung_luot_toi_thieu(goc, "K1", "0001")
        # Xoá tiêu đề để QA chắc chắn KHÔNG đạt (dễ giả lập hơn video hỏng).
        with open(os.path.join(thu_muc_luot, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
            tep.write("")
        done = os.path.join(goc, "done")
        ma, moi = ban_giao_dang.ban_giao(goc, "K1", "0001", done, ngay="20/09/2026", gio="20:00")
        assert moi is True
        cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
        dong = dict(zip(cot, hang[0]))
        assert dong["Sẵn sàng"] == ""
        assert dong["Ngày đăng"] == ""
        assert dong["Giờ đăng"] == ""
        duong_loi = os.path.join(done, ma, qa_truoc_dang.TEN_TEP_KET_QUA)
        assert os.path.isfile(duong_loi)
        assert "chưa có tiêu đề" in open(duong_loi, encoding="utf-8").read()

    def test_ban_giao_lai_khong_dung_dong_da_duyet_tay(self, tmp_path):
        """Dòng đã có sẵn (chủ dự án lỡ tự tay đánh Sẵn sàng) không bị QA xoá
        khi bàn giao lại cùng mã gói — xem docstring `ban_giao`."""
        goc = str(tmp_path)
        _ghi_kenh_toi_thieu(goc, "K1")
        thu_muc_luot = _dung_luot_toi_thieu(goc, "K1", "0001")
        done = os.path.join(goc, "done")
        ma, _ = ban_giao_dang.ban_giao(goc, "K1", "0001", done)
        # Chủ dự án tự tay duyệt, đặt giờ tay trong Excel.
        cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
        o_ma = cot.index("Mã gói")
        for dong in hang:
            if dong[o_ma].strip() == ma:
                dong[cot.index("Sẵn sàng")] = "x"
                dong[cot.index("Ngày đăng")] = "01/01/2027"
        ke_hoach_dang.luu_bang(goc, "K1", hang, cot)
        # Bàn giao lại (vd chạy lại lượt) — dù nội dung lượt vẫn y nguyên.
        ban_giao_dang.ban_giao(goc, "K1", "0001", done)
        cot2, hang2 = ke_hoach_dang.doc_bang(goc, "K1")
        dong2 = dict(zip(cot2, hang2[0]))
        assert dong2["Sẵn sàng"] == "x"
        assert dong2["Ngày đăng"] == "01/01/2027"


# ── Video thật (cần FFmpeg — bỏ qua nếu máy không có) ────────────────────────


def _dung_video_that(duong: str, *, giay: float = 3.0, rong: int = 1920, cao: int = 1080,
                     co_tieng: bool = True) -> None:
    """`testsrc` (có chuyển động) chứ không phải `color=` (một màu đứng
    im) — một khung hình không đổi suốt clip tự nó đã là "đứng hình", làm
    `freezedetect` báo cảnh báo ở MỌI video test, che mất bài kiểm thật sự
    đang nhắm tới. Cùng nếp `tests/test_lam_sach.py`."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    lenh = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "testsrc=size={0}x{1}:rate=24:duration={2}".format(rong, cao, giay)]
    if co_tieng:
        lenh += ["-f", "lavfi", "-i", "sine=frequency=440:duration={0}".format(giay)]
    lenh += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if co_tieng:
        lenh += ["-c:a", "aac", "-shortest"]
    lenh += [duong]
    subprocess.run(lenh, check=True, timeout=60)


@pytest.mark.skipif(not FFMPEG, reason="máy này không có FFmpeg")
class TestVideoThat:
    def test_video_du_tieng_va_do_phan_giai_khop_thi_khong_loi(self, tmp_path):
        duong = str(tmp_path / "v.mp4")
        _dung_video_that(duong, giay=3, rong=1920, cao=1080)
        tt = qa_truoc_dang.doc_thong_tin_media(FFMPEG, duong)
        assert tt.mo_duoc
        assert tt.co_tieng
        assert (tt.rong, tt.cao) == (1920, 1080)
        assert 2.5 < tt.giay < 3.5

    def test_video_khong_tieng_bi_bao_loi_qua_kiem_thu_muc_goi(self, tmp_path):
        goi = str(tmp_path / "g")
        os.makedirs(goi, exist_ok=True)
        _dung_video_that(os.path.join(goi, "8-video.mp4"), giay=2, co_tieng=False)
        _ghi_srt(os.path.join(goi, "3-phu-de.srt"),
                khoi=[("00:00:00,000", "00:00:01,000", "A")])
        _ghi_anh(os.path.join(goi, "thumb.png"))
        kq = qa_truoc_dang.kiem_thu_muc_goi(goi, tieu_de="Đủ tiêu đề", ffmpeg=FFMPEG)
        assert any("không có tiếng" in m for m in kq.loi)

    def test_tep_khong_phai_video_bao_khong_mo_duoc(self, tmp_path):
        goi = str(tmp_path / "g")
        os.makedirs(goi, exist_ok=True)
        with open(os.path.join(goi, "8-video.mp4"), "wb") as tep:
            tep.write(b"khong phai video that")
        _ghi_srt(os.path.join(goi, "3-phu-de.srt"),
                khoi=[("00:00:00,000", "00:00:01,000", "A")])
        _ghi_anh(os.path.join(goi, "thumb.png"))
        kq = qa_truoc_dang.kiem_thu_muc_goi(goi, tieu_de="Đủ tiêu đề", ffmpeg=FFMPEG)
        assert any("không mở được" in m for m in kq.loi)

    def test_giai_ma_day_du_bat_loi_o_tep_that_lanh(self, tmp_path):
        """`giai_ma_day_du=True` phải để LÀNH đi qua — tránh bắt oan khi bật."""
        duong = str(tmp_path / "v.mp4")
        _dung_video_that(duong, giay=1)
        assert qa_truoc_dang._giai_ma_day_du(FFMPEG, duong) == ""
