"""Dựng MỘT LẦN NÉN (`kenh.yaml: dung_mot_lan`, 30/09/2026).

Đường cũ: cắt từng clip bằng x264 `crf 14` (bản trung gian) → nối → mã lại lần
cuối. Đường mới: giải mã từng clip (cùng lọc, cùng số khung) đổ hình thô qua
ống vào lượt mã cuối. Các bài ở đây giữ ba lời hứa: tắt thì y như cũ; bật thì
đúng từng khung như cũ; hỏng thì tự lùi về đường cũ ngay trong lượt.
"""

import os
import shutil
import subprocess
import re

import pytest

from core import auto_khau as ak


def _gia(tmp_path, n):
    clip = []
    for i in range(n):
        p = tmp_path / "{0}.mp4".format(i)
        p.write_bytes(b"MP4")
        clip.append(str(p))
    mp3 = tmp_path / "g.mp3"
    mp3.write_bytes(b"MP3")
    return clip, str(mp3)


def _dieu_kien(n, nhip=24):
    return {"rong": 1280, "cao": 720, "nhip": nhip, "fps": [float(nhip)] * n}


def test_loc_cat_giu_nguyen_chuoi_cu():
    assert ak._loc_cat(4.0, None, 1.0, "black") == "tpad=stop_mode=clone:stop_duration=4.000"
    assert ak._loc_cat(5.0, (False, True), 1.0, "black").endswith(
        "fade=t=out:st=4.000:d=1.000")
    assert "fade=t=in:st=0:d=1.000:color=white" in ak._loc_cat(5.0, (True, False), 1.0, "white")
    # Cảnh ngắn: mờ không quá nửa cảnh.
    assert "d=0.400" in ak._loc_cat(0.8, (True, True), 1.0, "black")


def test_so_khung_toi_bang_t_cua_ban_cat():
    assert ak._so_khung_toi(5.0, 24) == 120
    assert ak._so_khung_toi(5.01, 24) == 121
    assert ak._so_khung_toi(0.001, 24) == 1


def test_tat_thi_khong_do_khong_ong(tmp_path, monkeypatch):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda *_a: pytest.fail("không được dò"))
    monkeypatch.setattr(ak, "_chay_ong", lambda *_a, **_k: pytest.fail("không được chạy ống"))
    clip, mp3 = _gia(tmp_path, 2)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), giay=[4.0, 4.0],
                   base_dir=".", khung=(1920, 1080))
    assert any("_noi.mp4" in " ".join(l) for l in bat)


def test_bat_thi_cung_luoi_khung_va_lenh_cuoi_nhu_cu(tmp_path, monkeypatch):
    """Số khung từng clip và chuỗi lọc tiếng của lượt cuối phải Y HỆT đường cũ."""
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: False)
    monkeypatch.setattr(ak, "_fps_clip", lambda _ff, _p: 24.0)
    clip, mp3 = _gia(tmp_path, 30)
    nhac = tmp_path / "8-nhac-nen.m4a"
    nhac.write_bytes(b"M4A")
    giay = [5.3 + 0.013 * (i % 7) for i in range(29)] + [9.7]
    mo = {3: (False, True), 4: (True, False)}
    chung = dict(giay=giay, base_dir=".", khung=(1920, 1080), mo_den=mo, giay_mo=1.0,
                 nhac_nen_san=str(nhac),
                 loc_giong="[1:a]aformat=sample_rates=48000:channel_layouts=stereo[g]")

    cu = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: cu.append(list(l)))
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), **chung)
    cat = [l for l in cu if "-frames:v" in l]
    khung_cu = [int(l[l.index("-frames:v") + 1]) for l in cat]
    vf_cu = [l[l.index("-vf") + 1] for l in cat]

    moi = {}
    monkeypatch.setattr(ak, "_chay", lambda *_a, **_k: pytest.fail("một lần nén không cắt"))
    monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda _ff, c, _g: _dieu_kien(len(c)))

    def ong(ff, lenh, o, **k):
        moi["lenh"], moi["ong"], moi["k"] = list(lenh), list(o), k

    monkeypatch.setattr(ak, "_chay_ong", ong)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), mot_lan=True, **chung)
    assert [n for _p, _l, n in moi["ong"]] == khung_cu
    assert [l for _p, l, _n in moi["ong"]] == vf_cu
    assert [p for p, _l, _n in moi["ong"]] == clip
    lenh = moi["lenh"]
    assert lenh[lenh.index("-i") - 1] == "24" and lenh[lenh.index("-i") + 1] == "pipe:0"
    assert "rawvideo" in lenh and "1280x720" in lenh
    cuoi = cu[-1]
    for khoa in ("-filter_complex", "-vf", "-crf", "-preset", "-map"):
        assert lenh[lenh.index(khoa) + 1] == cuoi[cuoi.index(khoa) + 1], khoa
    assert lenh[-1] == cuoi[-1] and "-shortest" in lenh


def test_khong_luoi_thi_so_khung_bang_t_lam_tron_len(tmp_path, monkeypatch):
    moi = {}
    monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda _ff, c, _g: _dieu_kien(len(c)))
    monkeypatch.setattr(ak, "_chay_ong", lambda ff, l, o, **k: moi.update(ong=list(o)))
    clip, mp3 = _gia(tmp_path, 2)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), giay=[4.0, 4.01],
                   base_dir=".", khung=(1920, 1080), mot_lan=True)
    assert [n for _p, _l, n in moi["ong"]] == [96, 97]


@pytest.mark.parametrize("dk", ["khong_ma_lai", "giu_tieng", "khong_dong_nhat"])
def test_thieu_dieu_kien_thi_di_duong_cu(tmp_path, monkeypatch, dk):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: False)
    monkeypatch.setattr(ak, "_chay_ong", lambda *_a, **_k: pytest.fail("không được chạy ống"))
    if dk == "khong_dong_nhat":
        monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda *_a: None)
    else:
        monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda _ff, c, _g: _dieu_kien(len(c)))
    clip, mp3 = _gia(tmp_path, 2)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), giay=[4.0, 4.0],
                   base_dir=".", khung=None if dk == "khong_ma_lai" else (1920, 1080),
                   giu_tieng=(dk == "giu_tieng"), mot_lan=True)
    assert any("_noi.mp4" in " ".join(l) for l in bat)


def test_ong_hong_thi_tu_lui_ve_duong_cu_trong_luot(tmp_path, monkeypatch):
    bat, nk = [], []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_fps_clip", lambda _ff, _p: 24.0)
    monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda _ff, c, _g: _dieu_kien(len(c)))

    def hong(*_a, **_k):
        raise RuntimeError("giải mã clip 2 ra 10/96 khung")

    monkeypatch.setattr(ak, "_chay_ong", hong)
    clip, mp3 = _gia(tmp_path, 2)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), giay=[4.0, 4.0],
                   base_dir=".", khung=(1920, 1080), mo_den={}, ghi=nk.append, mot_lan=True)
    assert any("lùi về cắt từng clip" in d for d in nk)
    assert len([l for l in bat if "-frames:v" in l]) == 2, "đã cắt lại như cũ"
    assert bat[-1][-1] == str(tmp_path / "ra.mp4")


def test_bam_dung_khong_lui_ma_dung_han(tmp_path, monkeypatch):
    from core.auto import Cancelled

    monkeypatch.setattr(ak, "_chay", lambda *_a, **_k: pytest.fail("không được lùi"))
    monkeypatch.setattr(ak, "_dieu_kien_mot_lan", lambda _ff, c, _g: _dieu_kien(len(c)))

    def dung(*_a, **_k):
        raise Cancelled("dừng")

    monkeypatch.setattr(ak, "_chay_ong", dung)
    clip, mp3 = _gia(tmp_path, 2)
    with pytest.raises(Cancelled):
        ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"), giay=[4.0, 4.0],
                       base_dir=".", khung=(1920, 1080), mot_lan=True)


def test_kenh_khoa_mac_dinh_tat_va_doc_duoc(tmp_path):
    from core.kenh import Kenh, doc_kenh

    assert Kenh.__dataclass_fields__["dung_mot_lan"].default is False
    d = tmp_path / "CHANNEL" / "K1"
    d.mkdir(parents=True)
    (d / "kenh.yaml").write_text("ten: K1\ndung_mot_lan: true\n", encoding="utf-8")
    assert doc_kenh(str(tmp_path), "K1").dung_mot_lan is True
    (d / "kenh.yaml").write_text("ten: K1\n", encoding="utf-8")
    assert doc_kenh(str(tmp_path), "K1").dung_mot_lan is False


# ── chạy thật: cùng số khung, cùng độ dài, SSIM cao ─────────────────────────


def _ff():
    from core.dung_video import tim_ffmpeg

    return tim_ffmpeg() or shutil.which("ffmpeg") or ""


def _tao(ff, *tham):
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error"] + list(tham),
                   check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _dem(ff, tep):
    r = subprocess.run([ff, "-hide_banner", "-i", tep, "-map", "0:v:0", "-c", "copy",
                        "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.findall(r"frame=\s*(\d+)", r.stderr or "")
    return int(m[-1]) if m else -1


def test_chay_that_mot_lan_bang_duong_cu(tmp_path):
    ff = _ff()
    if not ff:
        pytest.skip("máy chưa có FFmpeg")
    clip = []
    for i, mau in enumerate(("red", "green", "blue")):
        p = tmp_path / "{0}.mp4".format(i)
        _tao(ff, "-f", "lavfi", "-i", "testsrc2=s=320x180:d=3:r=24", "-vf",
             "drawbox=c={0}:t=20".format(mau), "-pix_fmt", "yuv420p", str(p))
        clip.append(str(p))
    mp3 = tmp_path / "g.mp3"
    _tao(ff, "-f", "lavfi", "-i", "sine=frequency=440:duration=8.5", "-b:a", "128k", str(mp3))
    giay = [2.3, 4.1, 2.1]     # clip giữa dài hơn clip (tpad giữ khung cuối)
    chung = dict(giay=giay, base_dir=str(tmp_path), khung=(640, 360),
                 mo_den={0: (False, True), 1: (True, False)}, giay_mo=0.5)
    ra = {}
    for ten, ml in (("cu", False), ("moi", True)):
        (tmp_path / ten).mkdir()
        dich = str(tmp_path / ten / "ra.mp4")
        ak._ghep_video(ff, clip, str(mp3), "", dich, mot_lan=ml, **chung)
        ra[ten] = dich
    assert _dem(ff, ra["moi"]) == _dem(ff, ra["cu"]) == round(sum(giay) * 24)
    r = subprocess.run([ff, "-hide_banner", "-i", ra["moi"], "-i", ra["cu"], "-lavfi",
                        "ssim", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    ssim = float(re.search(r"All:([\d.]+)", r.stderr).group(1))
    assert ssim >= 0.98, ssim
    assert not os.path.exists(str(tmp_path / "moi" / "_noi.mp4"))
