"""Nhạc nền theo PHẦN + lượt mã cuối có chuyển cảnh (Việc 2, thiết kế (f)(g)).

Chủ kênh: mỗi phần một nhạc nền cố định −18 dB dưới giọng, phần dài ghép 2–3
bài mượt, sang phần mới đổi nhạc và im ~2 giây. Bài kiểm chốt:

  1. `chon_nhac`: loại bài có giọng; xoay vòng không lặp (bài chưa dùng lên
     trước); cùng hạt giống (mã gói) → cùng lựa chọn; nới dần "10 video gần
     nhất" khi kho thiếu; phần dài nối thêm bài CÙNG NHÓM;
  2. lượt mã cuối: `amix … normalize=0` + `alimiter … level=disabled` (BẪY
     TRỘN TIẾNG), không `-stream_loop`, mờ vào/ra nằm trong bước cắt, tên bản
     cắt mang chữ ký;
  3. CHẠY THẬT một bài nhỏ: 2 clip màu + giọng sine có lặng 1,2s → nghỉ bù
     lên 3s, lớp nhạc dựng từ kho giả, đo độ dài ra = giọng + Σbù.

Không gọi mạng, không tốn tiền.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

import pytest

from core import auto_khau as ak
from core import kho_nhac as kn


def _bai(i, giay=120.0, nhom="", co_giong=False, loai="", cam_xuc=(), nguon="đoán từ tên"):
    return {"id": i, "ten": i, "nhom": nhom or i, "giay": giay, "lufs": -32.0,
            "co_giong": co_giong, "loai": loai, "cam_xuc": list(cam_xuc),
            "cam_xuc_nguon": nguon}


def _kho(*bai):
    return {"bai": {b["id"]: b for b in bai}}


PHAN_3 = [{"bat_dau": 0.0, "ket_thuc": 100.0}, {"bat_dau": 102.0, "ket_thuc": 200.0},
          {"bat_dau": 202.0, "ket_thuc": 300.0}]


# ── 1. chọn nhạc ────────────────────────────────────────────────────────────


def test_loai_bai_co_giong_va_khong_lap_trong_video():
    kho = _kho(_bai("a"), _bai("b", co_giong=True), _bai("c"), _bai("d", loai="co_giong"),
               _bai("e"))
    lua = kn.chon_nhac(PHAN_3, kho, [], hat_giong="TL3-T7-0004")
    phang = [i for p in lua for i in p]
    assert len(lua) == 3
    assert "b" not in phang and "d" not in phang
    assert len(set(phang)) == len(phang), "không bài nào lặp trong một video"


def test_cung_hat_giong_cung_ket_qua_khac_hat_giong_xoay():
    kho = _kho(*[_bai("s{0:02d}".format(i)) for i in range(20)])
    a = kn.chon_nhac(PHAN_3, kho, [], hat_giong="TL3-T7-0004")
    b = kn.chon_nhac(PHAN_3, kho, [], hat_giong="TL3-T7-0004")
    c = kn.chon_nhac(PHAN_3, kho, [], hat_giong="TL3-T7-0005")
    assert a == b
    assert a != c


def test_xoay_vong_bai_chua_dung_len_truoc_va_tranh_10_video_gan_nhat():
    kho = _kho(*[_bai("s{0:02d}".format(i)) for i in range(12)])
    gan = [["s00", "s01", "s02"], ["s03", "s04", "s05"]]
    lan = {"s00": 3.0, "s01": 3.0, "s02": 3.0, "s03": 2.0, "s04": 2.0, "s05": 2.0}
    lua = kn.chon_nhac(PHAN_3, kho, [], hat_giong="x", video_gan_day=gan,
                       lan_dung_cuoi=lan)
    phang = {i for p in lua for i in p}
    assert not phang & {"s00", "s01", "s02", "s03", "s04", "s05"}


def test_kho_thieu_thi_noi_dan_khong_bo_nhac():
    kho = _kho(_bai("a"), _bai("b"), _bai("c"), _bai("d"))
    gan = [["a", "b"], ["c", "d"]]
    lua = kn.chon_nhac(PHAN_3, kho, [], hat_giong="x", video_gan_day=gan,
                       lan_dung_cuoi={"a": 9, "b": 9, "c": 5, "d": 5})
    assert all(lua) and len(lua) == 3
    assert lua[0][0] in ("c", "d"), "nới dần: bài dùng lâu nhất được dùng lại trước"


def test_phan_dai_noi_them_bai_cung_nhom():
    kho = _kho(_bai("a1", 60, "A"), _bai("b1", 60, "B"), _bai("a2", 60, "A"),
               _bai("b2", 60, "B"), _bai("c1", 60, "C"))
    lua = kn.chon_nhac([{"bat_dau": 0.0, "ket_thuc": 150.0}], kho, [], hat_giong="h")
    p = lua[0]
    assert len(p) == 3, "60 + 56 + 56 ≥ 150"
    assert kho["bai"][p[1]]["nhom"] == kho["bai"][p[0]]["nhom"], "bài nối cùng nhóm"


def test_loc_cam_xuc_chi_khi_60_phan_tram_kho_co_nhan_chu_kenh():
    bai = [_bai("s{0}".format(i), cam_xuc=["buồn"], nguon="kênh") for i in range(6)]
    bai += [_bai("t{0}".format(i), cam_xuc=["căng"], nguon="kênh") for i in range(4)]
    kho = _kho(*bai)
    lua = kn.chon_nhac(PHAN_3, kho, [], hat_giong="h",
                       cam_xuc_phan=[["căng"], ["căng"], ["buồn"]])
    assert lua[0][0].startswith("t") and lua[1][0].startswith("t")
    assert lua[2][0].startswith("s")
    # Nhãn chỉ là "đoán từ tên" → KHÔNG lọc (quyết định 5).
    for b in kho["bai"].values():
        b["cam_xuc_nguon"] = "đoán từ tên"
    lua2 = kn.chon_nhac(PHAN_3, kho, [], hat_giong="h",
                        cam_xuc_phan=[["căng"], ["căng"], ["buồn"]])
    assert lua2 == kn.chon_nhac(PHAN_3, kho, [], hat_giong="h")


def test_lich_su_dung_doc_8_nhac_json(tmp_path):
    for luot, luc, ids in (("0001", 100.0, ["a", "b"]), ("0002", 200.0, ["c"])):
        d = tmp_path / "PROJECTS" / "AUTO" / "K" / luot
        d.mkdir(parents=True)
        (d / "8-nhac.json").write_text(json.dumps({"tao_luc": luc, "da_dung": ids}),
                                       encoding="utf-8")
    gan, lan = kn.lich_su_dung(str(tmp_path), "K",
                               bo_qua=str(tmp_path / "PROJECTS" / "AUTO" / "K" / "0003"))
    assert gan == [["c"], ["a", "b"]]
    assert lan == {"a": 100.0, "b": 100.0, "c": 200.0}
    gan2, _ = kn.lich_su_dung(str(tmp_path), "K",
                              bo_qua=str(tmp_path / "PROJECTS" / "AUTO" / "K" / "0002"))
    assert gan2 == [["a", "b"]], "không tính chính lượt đang dựng"


# ── 2. lệnh mã cuối ─────────────────────────────────────────────────────────


def test_lenh_cuoi_normalize_0_limiter_khong_nang_va_mo_trong_buoc_cat(tmp_path, monkeypatch):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: False)
    clip = []
    for i in range(3):
        p = tmp_path / "{0}.mp4".format(i)
        p.write_bytes(b"MP4")
        clip.append(str(p))
    mp3 = tmp_path / "g.mp3"
    mp3.write_bytes(b"MP3")
    nhac = tmp_path / "8-nhac-nen.m4a"
    nhac.write_bytes(b"M4A")
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0, 5.0, 4.0], base_dir=".",
                   mo_den={1: (False, True), 2: (True, False)}, giay_mo=1.0,
                   nhac_nen_san=str(nhac),
                   loc_giong="[1:a]aformat=sample_rates=48000:channel_layouts=stereo[g]")
    cat = [l for l in bat if "-vf" in l and "-t" in l]
    vf = [l[l.index("-vf") + 1] for l in cat]
    assert "fade" not in vf[0]
    assert vf[1].endswith("fade=t=out:st=4.000:d=1.000"), vf[1]
    assert "fade=t=in:st=0:d=1.000" in vf[2]
    ten = [os.path.basename(l[-1]) for l in cat]
    assert all(re.fullmatch(r"\d{4}-p[0-9a-f]{10}\.mp4", t) for t in ten), ten
    cuoi = bat[-1]
    fc = cuoi[cuoi.index("-filter_complex") + 1]
    assert "amix=inputs=2:duration=first:dropout_transition=0:normalize=0" in fc
    assert "alimiter=limit=0.9:level=disabled" in fc
    assert "-stream_loop" not in cuoi
    assert cuoi.count("-i") == 3 and str(nhac) in cuoi


def test_khong_dung_theo_phan_thi_lenh_cu_nguyen_ven(tmp_path, monkeypatch):
    """Không truyền tham số mới → tên bản cắt, lệnh cắt y như trước 28/09."""
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: False)
    p = tmp_path / "0.mp4"
    p.write_bytes(b"MP4")
    mp3 = tmp_path / "g.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", [str(p)], str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0], base_dir=".")
    assert os.path.basename(bat[0][-1]) == "0000.mp4"
    assert "fade" not in bat[0][bat[0].index("-vf") + 1]
    assert "-filter_complex" not in bat[-1]


# ── 3. chạy thật: 2 clip màu + giọng sine có lặng ───────────────────────────


def _ff():
    from core.dung_video import tim_ffmpeg

    return tim_ffmpeg() or shutil.which("ffmpeg") or ""


def _chay(ff, *tham):
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error"] + list(tham),
                   check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _dai(ff, tep):
    r = subprocess.run([ff, "-hide_banner", "-i", tep, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"time=(\d+):(\d+):([0-9.]+)", r.stderr or "")
    return int(m[-1][0]) * 3600 + int(m[-1][1]) * 60 + float(m[-1][2]) if m else 0.0


def test_chay_that_nghi_bu_len_3s_va_nhac_theo_phan(tmp_path):
    from core import phan_video as pv

    ff = _ff()
    if not ff:
        pytest.skip("máy chưa có FFmpeg")
    d = tmp_path / "luot"
    d.mkdir()
    # Giọng: 5s sine — 1,2s lặng (nghỉ phần kiểu cũ) — 5s sine.
    _chay(ff, "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
          "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=1.2",
          "-f", "lavfi", "-i", "sine=frequency=660:duration=5",
          "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]", "-map", "[a]",
          "-ar", "44100", "-ac", "1", "-b:a", "128k", str(d / "2-giong-doc.mp3"))
    (d / "3-phu-de.srt").write_text(
        "1\n00:00:00,000 --> 00:00:05,000\nphần một.\n\n"
        "2\n00:00:05,000 --> 00:00:07,000\n--- phần hai mở,\n\n"
        "3\n00:00:07,000 --> 00:00:11,200\nphần hai tiếp.\n", encoding="utf-8")
    kh = pv.lap_ke_hoach(str(d), ff, 3.0, giay_nghi_giong=1.2)
    assert len(kh.ranh) == 1
    assert kh.bu[0] == pytest.approx(3.0 - (kh.ranh[0].b - kh.ranh[0].a), abs=1e-6)
    assert 1.5 < kh.bu[0] < 2.0

    # Kho nhạc giả: 2 bài sine đã "chuẩn hoá".
    kho = tmp_path / "kho"
    (kho / "bai").mkdir(parents=True)
    for i, hz in (("aaaa0001", 220), ("bbbb0002", 330)):
        _chay(ff, "-f", "lavfi", "-i", "sine=frequency={0}:duration=20".format(hz),
              "-c:a", "aac", "-ar", "48000", "-ac", "2", str(kho / "bai" / (i + ".m4a")))
    chi = _kho(_bai("aaaa0001", 20.0), _bai("bbbb0002", 20.0))
    khung = pv.khung_nhac(kh, gap=2.0)
    lua = kn.chon_nhac(khung, chi, [], hat_giong="t", thu_muc_bai=str(kho / "bai"))
    assert len(lua) == 2 and lua[0] != lua[1], "sang phần mới đổi nhạc"
    ket = kn.lenh_lop_nhac(str(tmp_path), chi, lua, khung, ff,
                           str(d / "8-nhac-nen.m4a"), lufs_giong_do=-14.5,
                           tong_giay=kh.tong_moi, thu_muc_bai=str(kho / "bai"))
    assert (d / "8-nhac.json").exists() and len(ket["da_dung"]) == 2
    assert abs(_dai(ff, str(d / "8-nhac-nen.m4a")) - kh.tong_moi) < 0.3

    # Hai clip màu, cảnh 2 bắt đầu giữa khoảng nghỉ.
    clip = []
    for i, mau in enumerate(("red", "blue")):
        p = d / "{0}.mp4".format(i)
        _chay(ff, "-f", "lavfi", "-i", "color=c={0}:s=320x180:d=8:r=25".format(mau),
              "-pix_fmt", "yuv420p", str(p))
        clip.append(str(p))
    moi, _het, _giu, vao, ra, _bo = pv.xep_canh([0.0, 5.3], [5.0, 11.2], kh)
    giay = [moi[1] - moi[0], kh.tong_moi - moi[1]]
    ak._ghep_video(ff, clip, str(d / "2-giong-doc.mp3"), "", str(d / "8-video.mp4"),
                   giay=giay, base_dir=str(tmp_path),
                   mo_den={0: (False, True), 1: (True, False)}, giay_mo=1.0,
                   nhac_nen_san=str(d / "8-nhac-nen.m4a"),
                   loc_giong=pv.loc_giong_bu_nghi(kh.ranh, kh.bu))
    dai = _dai(ff, str(d / "8-video.mp4"))
    assert dai == pytest.approx(kh.tong_giong + kh.tong_bu, abs=0.3), \
        "độ dài video = giọng + Σbù"
    assert vao == {1} and ra == {0}


def test_cat_theo_luoi_khung_khong_troi_cong_don(tmp_path, monkeypatch):
    """Đo TL3/0004: `-t` làm tròn LÊN mỗi clip +½ khung → 151 clip hình chậm
    tiếng 2,48s ở giây 753. Đường dựng theo phần cắt theo lưới: tổng khung
    luôn bám tổng giây mong muốn, sai số không cộng dồn."""
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: False)
    monkeypatch.setattr(ak, "_fps_clip", lambda _ff, _p: 24.0)
    clip = []
    for i in range(40):
        p = tmp_path / "{0}.mp4".format(i)
        p.write_bytes(b"MP4")
        clip.append(str(p))
    mp3 = tmp_path / "g.mp3"
    mp3.write_bytes(b"MP3")
    giay = [5.3 + 0.013 * (i % 7) for i in range(40)]
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=giay, base_dir=".", mo_den={})
    cat = [l for l in bat if "-frames:v" in l]
    assert len(cat) == 40
    khung = [int(l[l.index("-frames:v") + 1]) for l in cat]
    tong = 0
    for i, n in enumerate(khung):
        tong += n
        assert abs(tong / 24.0 - sum(giay[:i + 1])) <= 0.5 / 24 + 1e-9, i
