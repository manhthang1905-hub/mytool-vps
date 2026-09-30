"""Nhà máy trả về đoạn đọc bị CẮT MẤT ÂM ĐẦU — phải bắt và đọc lại.

═══ ĐO 27/08/2026 TRÊN BA LƯỢT THẬT CỦA TL4-T7 ═══

Chủ dự án: *"tao nghe voice như kiểu có câu đó, tao sợ là kịch bản voice sai"*.
Kịch bản KHÔNG sai — chuỗi gửi cho máy đọc có 4.954 ký tự và **0 chữ số**.
Cái sai nằm ở tệp tiếng trả về:

    lượt 0053   đoạn 1, 2, 3 mở đầu ở −1,8 / −11,0 / −2,3 dB   (3/5 hỏng)
    lượt 0050   5/8 đoạn
    T-0031-map  3/5 đoạn

Đoạn lành mở đầu bằng im lặng: −58 … −84 dB. Đoạn hỏng bắt đầu **ngay tại mốc
0,000 giây** bằng tiếng gần cực đại — phần đầu của chữ đầu tiên đã bị xén.
Nghe được bằng tai: chữ mở màn `夜` (yo-ru) ra thành "buruu"; whisper cũng chép
nhầm thành ブルー. Cứ mỗi chỗ nối đoạn (~3 phút) lại một chữ bị nuốt.

Bộ chép tự động của CapCut gặp mấy mảnh âm cụt cộng khoảng lặng thì điền bừa
số vào — đó là chỗ "1, 2, 3, 4" mà chủ dự án thấy trong bản xuất.

Bài kiểm này dựng tệp mp3 THẬT bằng FFmpeg (một tiếng bíp có/không có nhịp im
lặng dẫn vào) — không gọi mạng, không tốn tiền.
"""

import os
import shutil
import subprocess

import pytest

from core.auto_khau import (DEM_DOC_LAI, GIAY_CHEN_LANG_AM_DAU,
                            GIAY_NGHE_AM_DAU, NGUONG_AM_DAU, _bi_xen_am_dau,
                            _chen_lang_dau_doan, _dai_clip, _dinh_am_dau)


def _ffmpeg():
    from core.dung_video import tim_ffmpeg
    return tim_ffmpeg() or shutil.which("ffmpeg") or ""


ff = _ffmpeg()
pytestmark = pytest.mark.skipif(not ff, reason="máy chưa có FFmpeg")


def _mp3(duong, dan_vao_giay):
    """Tiếng bíp 1 giây, có `dan_vao_giay` im lặng dẫn vào."""
    loc = "sine=frequency=440:duration=1"
    if dan_vao_giay:
        loc = "anullsrc=r=44100:cl=mono,atrim=0:{0}[a];sine=frequency=440:duration=1[b];[a][b]concat=n=2:v=0:a=1".format(
            dan_vao_giay)
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-filter_complex" if dan_vao_giay else "-f",
                    loc if dan_vao_giay else "lavfi",
                    *([] if dan_vao_giay else ["-i", loc]),
                    "-t", "2", duong], check=True)
    return duong


class TestDoAmDau:
    def test_bat_dau_bang_tieng_thi_coi_la_bi_xen(self, tmp_path):
        tep = _mp3(str(tmp_path / "cut.mp3"), 0)
        dinh = _dinh_am_dau(ff, tep)
        assert dinh is not None and dinh > NGUONG_AM_DAU
        assert _bi_xen_am_dau(ff, tep) is True

    def test_co_nhip_im_lang_dan_vao_thi_lanh(self, tmp_path):
        tep = _mp3(str(tmp_path / "lanh.mp3"), 0.4)
        assert _bi_xen_am_dau(ff, tep) is False

    def test_khong_do_duoc_thi_KHONG_bao_hong(self, tmp_path):
        """Cửa soi hỏng không được làm hỏng khâu đọc — im lặng đi tiếp."""
        assert _dinh_am_dau("", str(tmp_path / "x.mp3")) is None
        assert _dinh_am_dau(ff, str(tmp_path / "khong-co.mp3")) is None
        assert _bi_xen_am_dau(ff, str(tmp_path / "khong-co.mp3")) is False

    def test_moc_tach_duoc_hai_nhom_do_that(self):
        """−30 dB nằm giữa hai nhóm đo được, không bắt oan đoạn lành."""
        assert NGUONG_AM_DAU == -30.0
        assert -11.0 > NGUONG_AM_DAU        # đoạn hỏng nhẹ nhất của 0053
        assert -58.1 < NGUONG_AM_DAU        # đoạn lành ồn nhất của 0051
        assert 0.02 <= GIAY_NGHE_AM_DAU <= 0.2


class TestKhauGiongDocGoiCuaSoi:
    def _nguon(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"), encoding="utf-8") as t:
            return t.read()

    def test_doc_xong_thi_soi_am_dau_va_doc_lai_bang_khoa_moi(self):
        chu = self._nguon()
        khuc = chu[chu.index("def _khau_giong_doc"):chu.index("def _noi_mp3")]
        assert "_bi_xen_am_dau(ffmpeg_doc, tep)" in khuc, (
            "tải xong mà không soi âm đầu — bản cụt sẽ lọt thẳng vào video")
        # 29/09/2026: đọc lại lần 1 không còn gửi y NGUYÊN `chu` — đo được đọc
        # lại y hệt chữ cũ vô ích 68% (17/25 lượt). Vẫn dùng khoá MỚI
        # (`:am-dau`), nhưng văn bản gửi đi đổi sang có đệm `DEM_DOC_LAI`.
        assert 'doc(":am-dau", DEM_DOC_LAI + chu)' in khuc, (
            "đọc lại phải dùng khoá MỚI và chữ mở đầu có đệm")
        assert khuc.count("_bi_xen_am_dau(ffmpeg_doc, tep)") == 2, (
            "phải soi lại sau khi đọc lại, để còn nói thật với người dùng")

    def test_doc_lai_dung_MOT_lan(self):
        """Đọc lại mãi là đốt ví: bản thứ hai còn cụt thì CHÈN LẶNG, không
        đọc lại tiếp (29/09/2026)."""
        chu = self._nguon()
        khuc = chu[chu.index("def _khau_giong_doc"):chu.index("def _noi_mp3")]
        assert khuc.count('doc(":am-dau", DEM_DOC_LAI + chu)') == 1
        assert "_chen_lang_dau_doan(ffmpeg_doc, tep)" in khuc, (
            "vẫn cụt sau khi đọc lại thì phải chèn lặng, không đọc lại tiếp")
        assert "giữ, nhưng chữ đầu đoạn có thể nghe hụt" in khuc, (
            "vẫn phải còn đường lùi nếu chèn lặng cũng hỏng")


class TestChenLangDauDoan:
    def test_chen_lang_keo_dai_tep_dung_khoang(self, tmp_path):
        tep = _mp3(str(tmp_path / "cut.mp3"), 0)
        dai_truoc = _dai_clip(ff, tep)
        assert dai_truoc > 0

        ok = _chen_lang_dau_doan(ff, tep)
        assert ok is True

        dai_sau = _dai_clip(ff, tep)
        # Phải dài hơn khoảng đúng GIAY_CHEN_LANG_AM_DAU (cho phép sai số nhỏ
        # do làm tròn khi mã hoá mp3).
        assert dai_sau - dai_truoc == pytest.approx(GIAY_CHEN_LANG_AM_DAU, abs=0.15)
        # Sau khi chèn, đoạn đầu phải LÀNH (không còn bị coi là cụt âm đầu).
        assert _bi_xen_am_dau(ff, tep) is False

    def test_thieu_ffmpeg_thi_khong_hong_giu_nguyen_tep(self, tmp_path):
        tep = _mp3(str(tmp_path / "cut.mp3"), 0)
        noi_dung_truoc = open(tep, "rb").read()
        assert _chen_lang_dau_doan("", tep) is False
        assert open(tep, "rb").read() == noi_dung_truoc

    def test_tep_khong_ton_tai_thi_tra_false(self, tmp_path):
        assert _chen_lang_dau_doan(ff, str(tmp_path / "khong-co.mp3")) is False
