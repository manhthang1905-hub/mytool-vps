"""Clip từ ảnh cảnh khi engine clip hết hạn mức (06/10/2026).

Luật: engine báo hết hạn mức mà đã tới hạn chót (giờ đăng − `han_clip_truoc_gio_dang`
giờ, mặc định 6) thì cảnh thiếu clip dựng từ ảnh cảnh (Ken Burns, đúng độ dài cảnh);
trước hạn chót thì chờ engine. Không gọi mạng; FFmpeg thật (bỏ qua nếu máy không có).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import auto_khau as ak  # noqa: E402
from core import clip_tu_anh as cta  # noqa: E402
from core import su_co  # noqa: E402
from core.auto import LuotChay  # noqa: E402
from core.kenh import Kenh, doc_kenh  # noqa: E402

CAU_HET = ("Kho tài khoản video đã dùng hết hạn mức credit hôm nay, dự kiến có lại từ "
           "khoảng 20:54 giờ Việt Nam. Bạn không bị trừ tiền. Vui lòng thử lại sau.")


class _LoiCong(RuntimeError):
    def __init__(self, chu, code="engine_unavailable", status=503):
        super().__init__(chu)
        self.code = code
        self.status = status


@pytest.fixture(scope="module")
def ffmpeg():
    f = ak._tim_ffmpeg()
    if not f:
        pytest.skip("máy không có FFmpeg")
    return f


def _thong_tin(ffmpeg, duong):
    tho = subprocess.run([ffmpeg, "-hide_banner", "-i", duong], capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", tho)
    giay = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    k = re.search(r"Video:.*?\b(\d{2,5})x(\d{2,5})\b", tho)
    f = re.search(r"Video:.*?(\d+(?:\.\d+)?) fps", tho)
    return giay, int(k.group(1)), int(k.group(2)), float(f.group(1)), ("Audio:" in tho)


def _anh(duong, rong=344, cao=192):
    from PIL import Image

    os.makedirs(os.path.dirname(duong), exist_ok=True)
    im = Image.new("RGB", (rong, cao), (30, 90, 160))
    for x in range(0, rong, 16):
        for y in range(cao):
            im.putpixel((x, y), (250, 240, 200))
    im.save(duong, "PNG")
    return duong


# ── 1. su_co: câu hết hạn mức là loại riêng ─────────────────────────────────


class TestPhanLoai:
    def test_cau_that_kem_ma_engine_unavailable_la_het_han_muc(self):
        assert su_co.phan_loai(_LoiCong(CAU_HET)) == su_co.HET_HAN_MUC

    def test_ban_tieng_anh_va_ban_cat_cut(self):
        assert su_co.phan_loai(RuntimeError(
            "Video account pool has used up today's credit quota")) == su_co.HET_HAN_MUC
        assert su_co.phan_loai(RuntimeError(
            "Kho tài khoản video đã dùng hết hạn mức credit hôm nay, dự kiến có lại từ khoảng")
        ) == su_co.HET_HAN_MUC

    def test_engine_unavailable_thuong_van_la_tam_nghi(self):
        loi = _LoiCong("Hệ thống đang quá tải, chưa xử lý được yêu cầu này. Bạn không bị "
                       "trừ tiền. Vui lòng thử lại sau ít phút.")
        assert su_co.phan_loai(loi) == su_co.TAM_NGHI

    def test_han_muc_luu_tru_van_la_het_kho(self):
        assert su_co.phan_loai(RuntimeError("vượt hạn mức lưu trữ")) == su_co.HET_KHO

    def test_khong_doi_tung_loi_goi(self):
        """Lời gọi lẻ ném lên NGAY — không ngồi thang ~14 phút cho từng cảnh."""
        assert not su_co.nen_thu_lai(su_co.HET_HAN_MUC, 0)
        ngu = []

        def ham():
            raise _LoiCong(CAU_HET)

        with pytest.raises(_LoiCong):
            su_co.goi_kien_nhan(ham, ngu=ngu.append)
        assert ngu == []


# ── 2. dựng clip từ ảnh ─────────────────────────────────────────────────────


class TestTao:
    @pytest.mark.parametrize("kieu", [0, 1, 3])
    def test_dung_do_dai_kho_nhip(self, tmp_path, ffmpeg, kieu):
        anh = _anh(str(tmp_path / "a.png"))
        ra = cta.tao(anh, str(tmp_path / "1.mp4"), 2.37, ffmpeg, kieu=kieu,
                     khuon=(320, 180, 24))
        giay, rong, cao, fps, co_tieng = _thong_tin(ffmpeg, ra)
        assert abs(giay - 2.37) <= 0.1
        assert (rong, cao) == (320, 180)
        assert fps == 24
        assert co_tieng, "clip thật có rãnh tiếng — clip từ ảnh cũng phải có"
        assert not os.path.exists(ra + ".tam.mp4")

    def test_mac_dinh_la_khuon_clip_that(self, tmp_path, ffmpeg):
        ra = cta.tao(_anh(str(tmp_path / "a.png")), str(tmp_path / "2.mp4"), 1.0, ffmpeg)
        _g, rong, cao, fps, _t = _thong_tin(ffmpeg, ra)
        assert (rong, cao, fps) == (1280, 720, 24)

    def test_doc_khuon_tu_clip_that_cua_goi(self, tmp_path, ffmpeg):
        d = tmp_path / "6-clip"
        d.mkdir()
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=red:s=320x176:r=25:d=1", "-pix_fmt", "yuv420p",
                        str(d / "4.mp4")], check=True)
        assert cta.khuon_clip(ffmpeg, str(d)) == (320, 176, 25)
        assert cta.khuon_clip(ffmpeg, str(tmp_path / "khong-co")) == cta.KHUON_MAC_DINH

    def test_ffmpeg_hong_thi_khong_de_tep_do(self, tmp_path):
        def chay(*_a, **_k):
            return types.SimpleNamespace(returncode=1, stderr="hong")

        with pytest.raises(RuntimeError):
            cta.tao("x.png", str(tmp_path / "3.mp4"), 1.0, "ffmpeg", chay=chay)
        assert not os.path.exists(str(tmp_path / "3.mp4"))


def test_do_dai_canh_theo_dong_thoi_gian():
    canh = [{"scene_id": 1, "srt_start": "00:00:00,000", "srt_end": "00:00:04,000"},
            {"scene_id": 2, "srt_start": "00:00:04,600", "srt_end": "00:00:07,000"},
            {"scene_id": 3, "srt_start": "bad", "duration": 3.5}]
    assert cta.giay_canh(canh, 0) == pytest.approx(4.6)   # gồm cả khoảng nghỉ
    assert cta.giay_canh(canh, 2) == pytest.approx(3.5)


# ── 3. hạn chót ─────────────────────────────────────────────────────────────


class TestHanChot:
    def test_gio_dang_tru_6_gio(self, tmp_path):
        k = Kenh(ma="K1", gio_dang="05:00")
        han, dang = cta.han_chot(str(tmp_path), k, bay_gio=dt.datetime(2026, 10, 6, 9, 0))
        assert dang == dt.datetime(2026, 10, 7, 5, 0)
        assert han == dt.datetime(2026, 10, 6, 23, 0)

    def test_khe_khong_doi_khi_toi_gan(self, tmp_path):
        """Biên 0: tới 23:30 khe vẫn là 05:00 sáng mai — hạn chót không chạy trốn."""
        k = Kenh(ma="K1", gio_dang="05:00", nhip_dang=["05:00"], tu_duyet=True,
                 bien_xu_ly_gio=12.0)
        han, _d = cta.han_chot(str(tmp_path), k, bay_gio=dt.datetime(2026, 10, 6, 23, 30))
        assert han == dt.datetime(2026, 10, 6, 23, 0)

    def test_khoa_rieng_cua_kenh(self, tmp_path):
        k = Kenh(ma="K1", gio_dang="05:00", han_clip_truoc_gio_dang=2)
        han, _d = cta.han_chot(str(tmp_path), k, bay_gio=dt.datetime(2026, 10, 6, 9, 0))
        assert han == dt.datetime(2026, 10, 7, 3, 0)

    def test_kenh_khong_co_gio_dang(self, tmp_path):
        assert cta.han_chot(str(tmp_path), Kenh(ma="K1"))[0] is None

    def test_doc_tu_kenh_yaml(self, tmp_path):
        d = tmp_path / "CHANNEL" / "KX"
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text("ma: KX\n", encoding="utf-8")
        assert doc_kenh(str(tmp_path), "KX").han_clip_truoc_gio_dang == 6.0
        (d / "kenh.yaml").write_text("ma: KX\nhan_clip_truoc_gio_dang: 3\n", encoding="utf-8")
        assert doc_kenh(str(tmp_path), "KX").han_clip_truoc_gio_dang == 3.0


# ── 4. khâu clip: trước hạn chót chờ, sau hạn chót dựng từ ảnh ──────────────


def _luot(tmp_path, so=3):
    d = tmp_path / "luot"
    canh = []
    for i in range(1, so + 1):
        _anh(str(d / "5-anh" / "{0}.png".format(i)))
        canh.append({"scene_id": i, "video_prompt": "x", "img_prompt": "y",
                     "srt_start": "00:00:0{0},000".format(i - 1),
                     "srt_end": "00:00:0{0},800".format(i - 1)})
    (d / "6-clip").mkdir(parents=True)
    (d / "4-canh.json").write_text(json.dumps(canh), encoding="utf-8")
    return LuotChay(ma_kenh="K1", ma_luot="0001", thu_muc=str(d))


class _Dong:
    """Đồng hồ giả: `ngu` đẩy giờ đi, không ngủ thật."""

    def __init__(self, luc):
        self.luc = luc
        self.da_ngu = 0.0

    def ngu(self, giay):
        self.da_ngu += giay
        self.luc += dt.timedelta(seconds=giay)


@pytest.fixture()
def dung_cu(tmp_path, monkeypatch, ffmpeg):
    luot = _luot(tmp_path)
    dong = _Dong(dt.datetime(2026, 10, 6, 22, 0))
    nhat_ky = []
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=Kenh(ma="K1"), goi_chat=lambda *a, **k: "",
                    client=None, on_log=nhat_ky.append, ffmpeg=ffmpeg, ngu=dong.ngu)
    trang = {"het": True, "goi": []}
    mau = str(tmp_path / "mau.mp4")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=blue:s=320x180:r=24:d=1", "-pix_fmt", "yuv420p", mau], check=True)

    def lam_clip_gia(_bc, _luot, c, _anh, dich, _giay, **_k):
        trang["goi"].append(int(c["scene_id"]))
        if trang["het"]:
            raise _LoiCong(CAU_HET)
        shutil.copyfile(mau, dich)

    monkeypatch.setattr(ak, "_lam_clip", lam_clip_gia)
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong.luc)
    monkeypatch.setattr(ak, "_so_luong", lambda *a, **k: 2)
    return types.SimpleNamespace(bc=bc, luot=luot, dong=dong, trang=trang, nhat_ky=nhat_ky)


def _dat_han(monkeypatch, han):
    dang = han + dt.timedelta(hours=6) if han else None
    monkeypatch.setattr(ak, "_han_clip", lambda _bc: (han, dang))


def test_qua_han_chot_thi_dung_tu_anh(dung_cu, monkeypatch, ffmpeg):
    _dat_han(monkeypatch, dt.datetime(2026, 10, 6, 21, 0))
    ket = ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
    assert ket == {"so_clip": 3, "clip_tu_anh": 3}
    assert dung_cu.dong.da_ngu == 0, "đã quá hạn chót thì không chờ thêm"
    d = os.path.join(dung_cu.luot.thu_muc, "6-clip")
    du = cta.doc_danh_dau(d)
    assert du["canh"] == [1, 2, 3] and du["tong"] == 3
    giay, rong, cao, fps, _t = _thong_tin(ffmpeg, os.path.join(d, "1.mp4"))
    assert abs(giay - 1.0) <= 0.1      # 0→1 s: tới mốc cảnh sau, tối thiểu 1 s
    assert (rong, cao, fps) == (1280, 720, 24)
    assert sum("[CLIP TỪ ẢNH]" in x for x in dung_cu.nhat_ky) == 1


def test_truoc_han_chot_thi_cho_roi_moi_dung(dung_cu, monkeypatch):
    """Hạn chót 22:50: chờ 20' → thăm dò 1 cảnh → 20' → thăm dò → 10' → dựng từ ảnh."""
    _dat_han(monkeypatch, dt.datetime(2026, 10, 6, 22, 50))
    ket = ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
    assert ket["clip_tu_anh"] == 3
    assert dung_cu.dong.da_ngu == pytest.approx(50 * 60)
    # mẻ đầu bắn 3 cảnh, rồi đúng 2 lần thăm dò MỘT cảnh — không bắn lại cả mẻ
    assert len(dung_cu.trang["goi"]) == 3 + 2
    assert sum("thăm dò lại sau" in x for x in dung_cu.nhat_ky) == 3


def test_truoc_han_chot_engine_co_lai_thi_lam_clip_that(dung_cu, monkeypatch):
    _dat_han(monkeypatch, dt.datetime(2026, 10, 7, 3, 0))
    goc_ngu = dung_cu.dong.ngu

    def ngu_roi_co_lai(giay):
        goc_ngu(giay)
        dung_cu.trang["het"] = False

    dung_cu.bc.ngu = ngu_roi_co_lai
    ket = ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
    assert ket == {"so_clip": 3}
    assert dung_cu.dong.da_ngu == pytest.approx(20 * 60)
    assert cta.doc_danh_dau(os.path.join(dung_cu.luot.thu_muc, "6-clip")) == {}


def test_kenh_khong_co_gio_dang_thi_nhu_cu(dung_cu, monkeypatch):
    _dat_han(monkeypatch, None)
    with pytest.raises(Exception) as loi:
        ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
    assert su_co.phan_loai(loi.value) == su_co.HET_HAN_MUC
    assert dung_cu.dong.da_ngu == 0


# ── 5. khâu dựng: không clip nào + quá hạn chót → dựng được ─────────────────


def test_khau_dung_khong_con_no_khi_toan_clip_tu_anh(dung_cu, monkeypatch, ffmpeg):
    from core import moc_canh

    d = dung_cu.luot.thu_muc
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=3", os.path.join(d, "2-giong-doc.mp3")],
                   check=True)
    _dat_han(monkeypatch, dt.datetime(2026, 10, 6, 21, 0))
    monkeypatch.setattr(moc_canh, "chon_moc", lambda *a, **k: types.SimpleNamespace(
        tin=False, nguon=moc_canh.NGUON_BANG, canh=[], ghi_chu=""))
    dung_cu.bc.kenh = Kenh(ma="K1", dot_phu_de=False, giay_nghi_phan=0.0,
                           giay_nghi_chuyen_phan=0.0)
    ket = ak._khau_dung(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("dung"))
    assert ket["so_clip"] == 3
    giay, rong, cao, _f, _t = _thong_tin(ffmpeg, os.path.join(d, "8-video.mp4"))
    assert giay == pytest.approx(3.0, abs=0.3)
    assert cta.doc_danh_dau(os.path.join(d, "6-clip"))["canh"] == [1, 2, 3]


def test_khau_dung_truoc_han_chot_van_bao_nhu_cu(dung_cu, monkeypatch):
    _dat_han(monkeypatch, dt.datetime(2026, 10, 7, 3, 0))
    with pytest.raises(RuntimeError, match="chưa có clip nào"):
        ak._khau_dung(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("dung"))


# ── 6. hồ sơ video ghi lại để tự học thấy ──────────────────────────────────


def test_ho_so_ghi_clip_tu_anh(tmp_path):
    from core import ho_so_video as hv

    d = tmp_path / "PROJECTS" / "AUTO" / "K1" / "0001"
    (d / "6-clip").mkdir(parents=True)
    (d / "6-clip" / "tu-anh.json").write_text(json.dumps({"canh": [2, 5], "tong": 90}),
                                              encoding="utf-8")
    hs = hv._xay_ho_so(str(tmp_path), "K1", str(d), "K1-0001")
    assert hs["clip_tu_anh"] == "2/90"
    assert hv._khung_ho_so("K1", "K1-0002")["clip_tu_anh"] is None
