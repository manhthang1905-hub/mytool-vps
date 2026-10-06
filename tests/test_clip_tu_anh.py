"""Clip khi engine clip hết hạn mức / cảnh bị từ chối — luật 07/10/2026.

Chủ dự án 07/10/2026: *"Chỗ ShopAPI lỗi thì retry thôi — không nên dùng các phương
án mà sản phẩm cuối kém — thà không đăng còn hơn là sản phẩm cuối không ổn."*
Mặc định: hết hạn mức thì CHỜ engine (không hạn chót), cảnh hỏng vì lý do khác thì
cứu bằng clip thật (viết lại lời nhắc, vẽ lại ảnh), hết vòng thì dừng báo người;
khâu dựng không dựng video thiếu clip thật. Đường lùi Ken Burns (06/10, thư viện
`core/clip_tu_anh.py`) chỉ còn khi kênh tự bật `clip_tu_anh: true`.
Không gọi mạng; FFmpeg thật (bỏ qua nếu máy không có).
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


# ── 4. khâu clip ─────────────────────────────────────────────────────────────
#
# Luật 07/10/2026: mặc định (kênh KHÔNG khai `clip_tu_anh`) kho clip hết hạn mức
# thì CHỜ engine, không hạn chót, không bao giờ dựng cảnh từ ảnh. Đường lùi cũ
# (hạn chót → Ken Burns) chỉ còn khi kênh tự bật `clip_tu_anh: true`.


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
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=Kenh(ma="K1", gio_dang="05:00"),
                    goi_chat=lambda *a, **k: "", client=None, on_log=nhat_ky.append,
                    ffmpeg=ffmpeg, ngu=dong.ngu)
    trang = {"het": True, "goi": [], "het_sau": None}
    mau = str(tmp_path / "mau.mp4")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=blue:s=320x180:r=24:d=1", "-pix_fmt", "yuv420p", mau], check=True)

    def lam_clip_gia(_bc, _luot, c, _anh, dich, _giay, **_k):
        trang["goi"].append(int(c["scene_id"]))
        if trang["het_sau"] is not None and dong.luc >= trang["het_sau"]:
            trang["het"] = False
        if trang["het"]:
            raise _LoiCong(CAU_HET)
        shutil.copyfile(mau, dich)

    monkeypatch.setattr(ak, "_lam_clip", lam_clip_gia)
    monkeypatch.setattr(ak, "_bay_gio", lambda: dong.luc)
    monkeypatch.setattr(ak, "_so_luong", lambda *a, **k: 2)
    return types.SimpleNamespace(bc=bc, luot=luot, dong=dong, trang=trang, nhat_ky=nhat_ky, mau=mau)


def _dat_han(monkeypatch, han):
    dang = han + dt.timedelta(hours=6) if han else None
    monkeypatch.setattr(ak, "_han_clip", lambda _bc: (han, dang))


def _bat_clip_tu_anh(dung_cu, **them):
    dung_cu.bc.kenh = Kenh(ma="K1", gio_dang="05:00", clip_tu_anh=True, **them)


class TestMacDinhKhongDungTuAnh:
    """1a — mặc định: không hạn chót, chờ engine tới khi có lại, chỉ clip thật."""

    def test_han_clip_mac_dinh_la_khong_co_han(self, dung_cu):
        assert ak._han_clip(dung_cu.bc) == (None, None)

    def test_qua_ca_gio_dang_van_cho_engine_roi_lam_clip_that(self, dung_cu):
        # Engine có lại sau 07/10 09:00 — đã qua cả giờ đăng 05:00 lẫn hạn chót cũ 23:00.
        dung_cu.trang["het_sau"] = dt.datetime(2026, 10, 7, 9, 0)
        ket = ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
        assert ket == {"so_clip": 3}
        d = os.path.join(dung_cu.luot.thu_muc, "6-clip")
        assert cta.doc_danh_dau(d) == {}, "không bao giờ ghi tu-anh.json"
        assert not any("[CLIP TỪ ẢNH]" in x for x in dung_cu.nhat_ky)
        assert dung_cu.dong.da_ngu == pytest.approx(11 * 3600)   # 22:00 → 09:00, 20'/lần
        assert any("Không hạn chót" in x for x in dung_cu.nhat_ky)

    def test_cho_lau_thi_bao_mot_lan(self, dung_cu, monkeypatch):
        bao = []
        from core import bao_dong
        monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: bao.append((a, k)) or True)
        dung_cu.trang["het_sau"] = dt.datetime(2026, 10, 7, 12, 0)
        ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
        assert [a[0] for a, _k in bao] == ["cho_clip_lau"]

    def test_khau_clip_go_clip_tu_anh_cu_roi_lam_lai(self, dung_cu):
        """Gói cũ còn clip từ ảnh (đêm 06/10) → khâu clip gỡ đúng các clip được liệt
        kê và làm lại bằng engine; clip thật giữ nguyên, không gọi lại."""
        d = os.path.join(dung_cu.luot.thu_muc, "6-clip")
        for n in (1, 2, 3):
            shutil.copyfile(dung_cu.mau, os.path.join(d, "{0}.mp4".format(n)))
        with open(os.path.join(d, cta.TEP_DANH_DAU), "w", encoding="utf-8") as tep:
            json.dump({"canh": [2, 3], "tong": 3}, tep)
        luot = dung_cu.luot
        assert ak._canh_con_thieu_clip(luot, dung_cu.bc.kenh) == [2, 3]
        assert not ak._khau_clip(dung_cu.bc).soi_lai(luot)
        dung_cu.trang["het"] = False
        ket = ak._khau_clip(dung_cu.bc)(luot, luot.tt("clip"))
        assert ket == {"so_clip": 3}
        assert sorted(dung_cu.trang["goi"]) == [2, 3]
        assert not os.path.exists(os.path.join(d, cta.TEP_DANH_DAU))
        assert ak._khau_clip(dung_cu.bc).soi_lai(luot)


class TestBatClipTuAnh:
    """Kênh TỰ BẬT `clip_tu_anh: true` — đường lùi cũ giữ nguyên."""

    def test_qua_han_chot_thi_dung_tu_anh(self, dung_cu, monkeypatch, ffmpeg):
        _bat_clip_tu_anh(dung_cu)
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
        assert ak._khau_clip(dung_cu.bc).soi_lai(dung_cu.luot), "kênh bật thì clip từ ảnh được nhận"

    def test_truoc_han_chot_thi_cho_roi_moi_dung(self, dung_cu, monkeypatch):
        """Hạn chót 22:50: chờ 20' → thăm dò 1 cảnh → 20' → thăm dò → 10' → dựng từ ảnh."""
        _bat_clip_tu_anh(dung_cu)
        _dat_han(monkeypatch, dt.datetime(2026, 10, 6, 22, 50))
        ket = ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
        assert ket["clip_tu_anh"] == 3
        assert dung_cu.dong.da_ngu == pytest.approx(50 * 60)
        # mẻ đầu bắn 3 cảnh, rồi đúng 2 lần thăm dò MỘT cảnh — không bắn lại cả mẻ
        assert len(dung_cu.trang["goi"]) == 3 + 2
        assert sum("thăm dò lại sau" in x for x in dung_cu.nhat_ky) == 3

    def test_truoc_han_chot_engine_co_lai_thi_lam_clip_that(self, dung_cu, monkeypatch):
        _bat_clip_tu_anh(dung_cu)
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

    def test_bat_ma_khong_co_gio_dang_thi_cho_khong_han(self, dung_cu, monkeypatch):
        _bat_clip_tu_anh(dung_cu)
        _dat_han(monkeypatch, None)
        dung_cu.trang["het_sau"] = dt.datetime(2026, 10, 6, 23, 0)
        ket = ak._khau_clip(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("clip"))
        assert ket == {"so_clip": 3}
        assert dung_cu.dong.da_ngu == pytest.approx(60 * 60)


# ── 4b. cứu cảnh hỏng vì lý do KHÁC hạn mức (luật 07/10/2026, 1b) ──────────


CAU_TU_CHOI = "máy chủ báo job hỏng vì nội dung: content_rejected — prompt bị từ chối"
LOI_NHAC_CLIP = "a quiet cat walks slowly through the misty garden at dawn, soft light"
LOI_NHAC_MOI = "a quiet cat strolls slowly through the misty garden at dawn, gentle soft light"


@pytest.fixture()
def cuu(dung_cu, monkeypatch):
    """Cảnh 2 bị bộ lọc chặn chừng nào lời nhắc clip còn là bản gốc."""
    canh = json.loads(open(os.path.join(dung_cu.luot.thu_muc, "4-canh.json"),
                           encoding="utf-8").read())
    for c in canh:
        c["video_prompt"] = LOI_NHAC_CLIP
        c["img_prompt"] = "a quiet cat in a misty garden at dawn, watercolor"
    with open(os.path.join(dung_cu.luot.thu_muc, "4-canh.json"), "w", encoding="utf-8") as tep:
        json.dump(canh, tep)
    dung_cu.trang["het"] = False
    trang = {"chan_loi_nhac": {LOI_NHAC_CLIP}, "goi_ai": [], "ve_anh": []}

    def lam_clip_gia(_bc, _luot, c, _anh, dich, _giay, **_k):
        dung_cu.trang["goi"].append(int(c["scene_id"]))
        if int(c["scene_id"]) == 2 and c["video_prompt"] in trang["chan_loi_nhac"]:
            raise RuntimeError(CAU_TU_CHOI)
        shutil.copyfile(dung_cu.mau, dich)

    def goi_chat(loi_nhac, **_k):
        trang["goi_ai"].append(loi_nhac)
        return LOI_NHAC_MOI if "text-to-video" in loi_nhac else \
            "a calm cat sitting in a misty garden at dawn, watercolor"

    def lam_anh_gia(_bc, _luot, c, tep, _hop, so=None):
        trang["ve_anh"].append(int(c["scene_id"]))
        _anh(tep)

    monkeypatch.setattr(ak, "_lam_clip", lam_clip_gia)
    monkeypatch.setattr(ak, "_lam_anh_canh", lam_anh_gia)
    monkeypatch.setattr(ak, "ThamChieu", lambda bc: ak._HopTrong())
    dung_cu.bc.goi_chat = goi_chat
    return types.SimpleNamespace(dc=dung_cu, trang=trang)


def test_canh_bi_tu_choi_viet_lai_loi_nhac_clip_roi_lam_clip_that(cuu):
    dc = cuu.dc
    ket = ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    assert ket == {"so_clip": 3}
    d = dc.luot.thu_muc
    assert os.path.exists(os.path.join(d, "6-clip", "2.mp4"))
    canh = json.loads(open(os.path.join(d, "4-canh.json"), encoding="utf-8").read())
    assert canh[1]["video_prompt"] == LOI_NHAC_MOI, "lời nhắc mới phải ghi vào 4-canh.json"
    assert cuu.trang["ve_anh"] == [], "viết lại lời nhắc clip đã đủ — không vẽ lại ảnh"
    assert cta.doc_danh_dau(os.path.join(d, "6-clip")) == {}


def test_viet_lai_khong_du_thi_ve_lai_anh(cuu):
    cuu.trang["chan_loi_nhac"].add(LOI_NHAC_MOI)      # bản viết lại cũng bị chặn …
    dc = cuu.dc
    goc = ak._lam_clip

    def lam_clip(_bc, _luot, c, anh, dich, giay, **k):
        # … nhưng ảnh mới (vẽ lại) thì qua
        if int(c["scene_id"]) == 2 and 2 in cuu.trang["ve_anh"]:
            shutil.copyfile(dc.mau, dich)
            return
        goc(_bc, _luot, c, anh, dich, giay, **k)

    ak._lam_clip = lam_clip
    try:
        ket = ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    finally:
        ak._lam_clip = goc
    assert ket == {"so_clip": 3}
    assert cuu.trang["ve_anh"] == [2]
    assert os.path.exists(os.path.join(dc.luot.thu_muc, "5-anh", "2.png.cu")), "ảnh cũ cất .cu"


def test_het_vong_cuu_thi_dung_luot_bao_can_nguoi_xem(cuu, monkeypatch):
    from core import bao_dong
    bao = []
    monkeypatch.setattr(bao_dong, "bao_dong_khan", lambda *a, **k: bao.append(a) or True)
    cuu.trang["chan_loi_nhac"].update({LOI_NHAC_MOI})
    dc = cuu.dc
    goc = ak._lam_clip

    def lam_clip(_bc, _luot, c, anh, dich, giay, **k):
        if int(c["scene_id"]) == 2:
            dc.trang["goi"].append(2)
            raise RuntimeError(CAU_TU_CHOI)
        goc(_bc, _luot, c, anh, dich, giay, **k)

    monkeypatch.setattr(ak, "_lam_clip", lam_clip)
    with pytest.raises(ak.LoiCanhKhongLamDuoc, match="cảnh 2 không làm được clip thật — cần người xem"):
        ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    assert not os.path.exists(os.path.join(dc.luot.thu_muc, "6-clip", "2.mp4"))
    assert [a[0] for a in bao] == ["clip_canh_khong_lam_duoc"]
    md = os.path.join(dc.bc.goc, "workspace", "loi-chay-max.md")
    assert "cần người xem" in open(md, encoding="utf-8").read()
    so_cuu = json.loads(open(os.path.join(dc.luot.thu_muc, ak.TEP_CUU_CANH), encoding="utf-8").read())
    assert so_cuu["2"]["vong"] == ak.SO_VONG_CUU_CANH
    # Lần chạy khâu sau (ba lượt thử của auto.chay, lượt phục hồi): ném NGAY, không gọi máy chủ,
    # không báo lại.
    truoc = len(dc.trang["goi"])
    so_ai = len(cuu.trang["goi_ai"])
    with pytest.raises(ak.LoiCanhKhongLamDuoc):
        ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    assert dc.trang["goi"][truoc:] == [2], "chỉ mẻ thường gọi lại cảnh 2 một lần, không vòng cứu"
    assert len(cuu.trang["goi_ai"]) == so_ai
    assert len(bao) == 1


def test_nguoi_sua_loi_nhac_thi_cuu_lai_tu_dau(cuu, monkeypatch):
    from core import bao_dong
    monkeypatch.setattr(bao_dong, "bao_dong_khan", lambda *a, **k: True)
    dc = cuu.dc
    d = dc.luot.thu_muc
    with open(os.path.join(d, ak.TEP_CUU_CANH), "w", encoding="utf-8") as tep:
        json.dump({"2": {"vong": ak.SO_VONG_CUU_CANH, "dau": "lech", "loi": "x"}}, tep)
    ket = ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    assert ket == {"so_clip": 3}
    assert "2" not in json.loads(open(os.path.join(d, ak.TEP_CUU_CANH), encoding="utf-8").read())


def test_het_han_muc_giua_luc_cuu_thi_quay_ve_cho(cuu):
    """Đang cứu cảnh 2 thì kho clip hết hạn mức → quay về vòng chờ (không đốt vòng cứu)."""
    dc = cuu.dc
    goc = ak._lam_clip
    lan = {"n": 0}

    def lam_clip(_bc, _luot, c, anh, dich, giay, **k):
        if int(c["scene_id"]) == 2 and c["video_prompt"] == LOI_NHAC_MOI:
            lan["n"] += 1
            if lan["n"] <= 2:       # lúc cứu + mẻ ngay sau: kho vẫn hết
                raise _LoiCong(CAU_HET)
        goc(_bc, _luot, c, anh, dich, giay, **k)

    ak._lam_clip = lam_clip
    try:
        ket = ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    finally:
        ak._lam_clip = goc
    assert ket == {"so_clip": 3}
    assert dc.dong.da_ngu == pytest.approx(20 * 60)
    assert not os.path.exists(os.path.join(dc.luot.thu_muc, ak.TEP_CUU_CANH)) or \
        "2" not in json.loads(open(os.path.join(dc.luot.thu_muc, ak.TEP_CUU_CANH), encoding="utf-8").read())


def test_su_co_may_chu_khong_dot_vong_cuu(cuu, monkeypatch):
    """Cảnh hỏng vì cổng quá tải (không phải vì nội dung) → ném lên cho lượt thử khâu
    làm lại; không viết lại lời nhắc, không tính vòng cứu."""
    dc = cuu.dc
    goc = ak._lam_clip
    cau = ("Hệ thống đang quá tải, chưa xử lý được yêu cầu này. Bạn không bị trừ tiền. "
           "Vui lòng thử lại sau ít phút.")

    def lam_clip(_bc, _luot, c, anh, dich, giay, **k):
        if int(c["scene_id"]) == 2:
            raise _LoiCong(cau, code="engine_unavailable")
        goc(_bc, _luot, c, anh, dich, giay, **k)

    monkeypatch.setattr(ak, "_lam_clip", lam_clip)
    with pytest.raises(_LoiCong):
        ak._khau_clip(dc.bc)(dc.luot, dc.luot.tt("clip"))
    assert cuu.trang["goi_ai"] == [] and cuu.trang["ve_anh"] == []
    assert not os.path.exists(os.path.join(dc.luot.thu_muc, ak.TEP_CUU_CANH))


# ── 5. khâu dựng: không clip thật đủ thì KHÔNG dựng (luật 07/10/2026) ──────


def _cho_dung(dung_cu, monkeypatch, ffmpeg):
    from core import moc_canh

    d = dung_cu.luot.thu_muc
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=3", os.path.join(d, "2-giong-doc.mp3")],
                   check=True)
    monkeypatch.setattr(moc_canh, "chon_moc", lambda *a, **k: types.SimpleNamespace(
        tin=False, nguon=moc_canh.NGUON_BANG, canh=[], ghi_chu=""))
    return d


def test_khau_dung_khong_dung_khi_thieu_clip(dung_cu, monkeypatch, ffmpeg):
    d = _cho_dung(dung_cu, monkeypatch, ffmpeg)
    dung_cu.bc.kenh = Kenh(ma="K1", dot_phu_de=False, giay_nghi_phan=0.0, giay_nghi_chuyen_phan=0.0)
    shutil.copyfile(dung_cu.mau, os.path.join(d, "6-clip", "1.mp4"))
    shutil.copyfile(dung_cu.mau, os.path.join(d, "6-clip", "3.mp4"))
    with pytest.raises(RuntimeError, match=r"thiếu clip thật cho 1/3 cảnh \(2\)"):
        ak._khau_dung(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("dung"))
    assert not os.path.exists(os.path.join(d, "8-video.mp4"))


def test_khau_dung_khong_dung_khi_co_clip_tu_anh(dung_cu, monkeypatch, ffmpeg):
    d = _cho_dung(dung_cu, monkeypatch, ffmpeg)
    dung_cu.bc.kenh = Kenh(ma="K1", dot_phu_de=False, giay_nghi_phan=0.0, giay_nghi_chuyen_phan=0.0)
    for n in (1, 2, 3):
        shutil.copyfile(dung_cu.mau, os.path.join(d, "6-clip", "{0}.mp4".format(n)))
    with open(os.path.join(d, "6-clip", cta.TEP_DANH_DAU), "w", encoding="utf-8") as tep:
        json.dump({"canh": [2], "tong": 3}, tep)
    with pytest.raises(RuntimeError, match="thiếu clip thật"):
        ak._khau_dung(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("dung"))


def test_khau_dung_chua_co_clip_nao_khong_tu_dung_tu_anh(dung_cu, monkeypatch, ffmpeg):
    d = _cho_dung(dung_cu, monkeypatch, ffmpeg)
    _dat_han(monkeypatch, dt.datetime(2026, 10, 6, 21, 0))   # đã quá "hạn chót" cũ
    dung_cu.bc.kenh = Kenh(ma="K1", dot_phu_de=False, giay_nghi_phan=0.0, giay_nghi_chuyen_phan=0.0)
    with pytest.raises(RuntimeError, match="thiếu clip thật cho 3/3"):
        ak._khau_dung(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("dung"))
    assert cta.doc_danh_dau(os.path.join(d, "6-clip")) == {}


def test_khau_dung_kenh_bat_clip_tu_anh_dung_duoc(dung_cu, monkeypatch, ffmpeg):
    d = _cho_dung(dung_cu, monkeypatch, ffmpeg)
    dung_cu.bc.kenh = Kenh(ma="K1", dot_phu_de=False, giay_nghi_phan=0.0,
                           giay_nghi_chuyen_phan=0.0, clip_tu_anh=True)
    cta.bu_canh_thieu(d, ak._doc_canh(dung_cu.luot), ffmpeg, ly_do="thử", ghi=lambda s: None)
    ket = ak._khau_dung(dung_cu.bc)(dung_cu.luot, dung_cu.luot.tt("dung"))
    assert ket["so_clip"] == 3
    giay, _r, _c, _f, _t = _thong_tin(ffmpeg, os.path.join(d, "8-video.mp4"))
    assert giay == pytest.approx(3.0, abs=0.3)


def test_soi_lai_khau_dung_bat_dung_lai_video_tren_clip_tu_anh(dung_cu):
    d = dung_cu.luot.thu_muc
    open(os.path.join(d, "8-video.mp4"), "wb").write(b"x")
    with open(os.path.join(d, "6-clip", cta.TEP_DANH_DAU), "w", encoding="utf-8") as tep:
        json.dump({"canh": [1], "tong": 3}, tep)
    assert not ak._khau_dung(dung_cu.bc).soi_lai(dung_cu.luot)


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
