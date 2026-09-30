"""Việc 1 (`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`): kho nhạc chuẩn hoá TĂNG DẦN.

`core/kho_nhac.py` đọc CHỈ ĐỌC `PROJECTS/music` (không đụng gì ở đó — luật 1
CLAUDE.md) và ghi bản chuẩn hoá vào `workspace/kho-nhac/`. Bài kiểm này KHÔNG
đụng `PROJECTS/music` thật: mọi tệp nguồn được sinh trong `tmp_path` bằng
`ffmpeg -f lavfi` (sine/anullsrc), và `cap_nhat()` được trỏ vào thư mục tạm
qua `thu_muc_nguon=`/`thu_muc_dich=`.
"""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from core import ffmpeg_goi_san, kho_nhac
from core.dung_video import tim_ffmpeg

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = tim_ffmpeg(GOC)
CO_FFMPEG = bool(FFMPEG) and ffmpeg_goi_san.du_dung(FFMPEG)


def _stderr_meta(comment="x", title=None):
    """Giả một đoạn `ffmpeg -i` in metadata — ĐÚNG THỤT LỀ thật (2/4 dấu
    cách) để `phan_tich_metadata` đọc ra được, không phải chuỗi tuỳ tiện."""
    dong = ["Input #0, mp3, from 'x':", "  Metadata:"]
    if title:
        dong.append("    title           : {0}".format(title))
    dong.append("    comment         : {0}".format(comment))
    dong.append("  Duration: 00:00:05.00, start: 0.000000, bitrate: 128 kb/s")
    return "\n".join(dong)


def _tao_mp3(thu_muc, ten, giay=5, tan_so=440, id_suno=None, tieu_de=None):
    """Một mp3 sine ngắn — đứng thay `PROJECTS/music` thật trong bài kiểm."""
    duong = os.path.join(thu_muc, ten)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "sine=frequency={0}:duration={1}".format(tan_so, giay)]
    if id_suno:
        cmd += ["-metadata",
                "comment=made with suno; id={0}".format(id_suno)]
    if tieu_de:
        cmd += ["-metadata", "title={0}".format(tieu_de)]
    cmd += [duong]
    subprocess.run(cmd, check=True)
    return duong


# ── 1. Chuỗi lọc FFmpeg — THUẦN, không gọi tiến trình ────────────────────────


def test_chuoi_cat_lang_co_hai_luot_silenceremove_va_areverse_o_giua():
    loc = kho_nhac.chuoi_cat_lang()
    phan = loc.split(",")
    assert phan[0].startswith("silenceremove=")
    assert phan[1] == "areverse"
    assert phan[2].startswith("silenceremove=")
    assert phan[3] == "areverse"
    assert "detection=peak" in loc
    assert "start_threshold=-50dB" in loc


def test_chuoi_loc_do_la_do_khong_ghi():
    loc = kho_nhac.chuoi_loc_do()
    assert loc.startswith(kho_nhac.chuoi_cat_lang())
    assert "loudnorm=I=-32:TP={0}:LRA=20:print_format=json".format(
        kho_nhac.TP_MUC_TIEU) in loc
    # Lượt đo không được có bất kỳ bộ lọc GHI nào (aresample/afade) — lẫn vào
    # là đo sai số thật của lượt sau khi đã ghi.
    assert "afade" not in loc


def test_chuoi_loc_ghi_dien_dung_so_do_luot_1():
    do1 = {"input_i": "-14.6", "input_tp": "-1.2", "input_lra": "3.5",
           "input_thresh": "-25.1", "target_offset": "0.3"}
    loc = kho_nhac.chuoi_loc_ghi(do1)
    assert "measured_I=-14.6" in loc
    assert "measured_TP=-1.2" in loc
    assert "measured_LRA=3.5" in loc
    assert "measured_thresh=-25.1" in loc
    assert "offset=0.3" in loc
    assert "linear=true" in loc
    assert "aresample=48000" in loc
    assert "aformat=channel_layouts=stereo" in loc
    assert "afade=t=in:d=0.3" in loc


def test_chuoi_loc_ghi_thieu_khoa_nem_key_error():
    with pytest.raises(KeyError):
        kho_nhac.chuoi_loc_ghi({"input_i": "-14.6"})


def test_chuoi_loc_khuech_dai_don_la_duong_lui_tuyen_tinh():
    loc = kho_nhac.chuoi_loc_khuech_dai_don(-17.5)
    assert "volume=-17.500dB" in loc
    assert loc.startswith(kho_nhac.chuoi_cat_lang())
    assert "afade=t=in:d=0.3" in loc


# ── 2. Parse JSON `loudnorm` từ stderr FFmpeg (THUẦN) ────────────────────────

_MAU_STDERR_LOUDNORM = """
[Parsed_loudnorm_2 @ 0x]
{
\t"input_i" : "-14.60",
\t"input_tp" : "-1.20",
\t"input_lra" : "3.50",
\t"input_thresh" : "-25.10",
\t"output_i" : "-32.00",
\t"output_tp" : "-12.00",
\t"output_lra" : "3.50",
\t"output_thresh" : "-42.00",
\t"normalization_type" : "linear",
\t"target_offset" : "0.30"
}
"""


def test_parse_json_loudnorm_lay_dung_khoi_cuoi_cung():
    js = kho_nhac.parse_json_loudnorm(_MAU_STDERR_LOUDNORM)
    assert js is not None
    assert js["normalization_type"] == "linear"
    assert float(js["input_i"]) == -14.60


def test_parse_json_loudnorm_khong_co_thi_tra_none():
    assert kho_nhac.parse_json_loudnorm("chẳng có gì ở đây cả") is None
    assert kho_nhac.parse_json_loudnorm("") is None


# ── 3. Đọc metadata — chỉ khối ĐẦU TIÊN (bỏ qua ảnh bìa đính kèm) ────────────

_MAU_STDERR_METADATA = """Input #0, mp3, from 'PROJECTS/music/1 Ivory Panic.mp3':
  Metadata:
    title           : Ivory Panic
    artist          : katsu6630
    comment         : made with suno; created=2026-04-23T03:08:05.949Z; id=5b21e8ca-ffd9-453e-9b23-eaa07c518d53
  Duration: 00:02:04.94, start: 0.023021, bitrate: 181 kb/s
  Stream #0:0: Audio: mp3 (mp3float), 48000 Hz, stereo, fltp, 181 kb/s
      Metadata:
        encoder         : Lavc60.31
  Stream #0:1: Video: mjpeg (Baseline), yuvj420p(pc, bt470bg/unknown/unknown), 360x360 [SAR 1:1 DAR 1:1], 90k tbr, 90k tbn (attached pic)
      Metadata:
        title           : Cover
        comment         : Cover (front)
At least one output file must be specified
"""


def test_phan_tich_metadata_lay_khoi_dau_khong_lay_anh_bia():
    the = kho_nhac.phan_tich_metadata(_MAU_STDERR_METADATA)
    assert the["title"] == "Ivory Panic"
    assert the["artist"] == "katsu6630"
    assert "id=5b21e8ca-ffd9-453e-9b23-eaa07c518d53" in the["comment"]
    # Không được lẫn "Cover" của luồng ảnh bìa vào.
    assert the["title"] != "Cover"


def test_doc_do_dai_giay_tu_dong_duration():
    assert kho_nhac.parse_json_loudnorm  # (giữ import không bị dọn nhầm)
    giay = kho_nhac._doc_do_dai_giay(_MAU_STDERR_METADATA)
    assert abs(giay - (2 * 60 + 4.94)) < 0.01


# ── 4. Đoán tên/nhóm/cảm xúc (THUẦN) ─────────────────────────────────────────


def test_don_ten_bo_tien_to_rac():
    assert kho_nhac.don_ten(
        "4113974 Apr 22 20:10 4 Marble Applause") == "Marble Applause"
    assert kho_nhac.don_ten("Ivory Panic") == "Ivory Panic"


def test_doan_nhom_theo_quy_uoc_dat_ten():
    assert kho_nhac.doan_nhom("TL1-0023_atmosphere.mp3", "atmosphere") == "TL1-0023"
    assert kho_nhac.doan_nhom("B1.2 Something.mp3", "Something") == "B1"
    assert kho_nhac.doan_nhom("Ivory Panic.mp3", "Ivory Panic") == "Ivory Panic"


def test_doan_cam_xuc_tu_ten_theo_tu_khoa():
    assert "căng" in kho_nhac.doan_cam_xuc_tu_ten("Salt-Paper Storm")
    assert "ấm" in kho_nhac.doan_cam_xuc_tu_ten("5 Candle Static")
    assert kho_nhac.doan_cam_xuc_tu_ten("Xyz Qwerty") == []


# ── 5. Vân tay + ngân sách (không cần FFmpeg — dùng tệp giả) ─────────────────


def test_van_tay_nhanh_khop_thi_bo_qua_khong_mo_lai(tmp_path, monkeypatch):
    """Lần 2 gọi `cap_nhat` với cùng tệp y hệt không được đụng tới FFmpeg
    chuẩn hoá — chặn `_chuan_hoa_mot_bai` để lộ ra ngay nếu code cố xử lý
    lại."""
    nguon = tmp_path / "nguon"
    nguon.mkdir()
    dich = tmp_path / "dich"
    (nguon / "a.mp3").write_bytes(b"khong phai mp3 that, chi de do van tay")

    goi = {"n": 0}

    def _chuan_hoa_gia(ffmpeg, vao, ra):
        goi["n"] += 1
        os.makedirs(os.path.dirname(ra), exist_ok=True)
        with open(ra, "wb") as tep:
            tep.write(b"gia")
        return 60.0, -32.0, -12.0

    monkeypatch.setattr(kho_nhac, "_chuan_hoa_mot_bai", _chuan_hoa_gia)
    monkeypatch.setattr(ffmpeg_goi_san, "du_dung", lambda _f: True)
    monkeypatch.setattr(kho_nhac, "_do_co_giong", lambda ff, d: (False, ""))
    monkeypatch.setattr(kho_nhac, "_chay_ffmpeg",
                        lambda cmd, timeout=600.0: _stderr_meta())

    kq1 = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                            thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    assert kq1["moi"] == 1
    assert goi["n"] == 1

    kq2 = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                            thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    assert kq2["moi"] == 0
    assert kq2["bo_qua_khong_doi"] == 1
    assert goi["n"] == 1, "lần 2 KHÔNG được gọi lại FFmpeg chuẩn hoá"


def test_ngan_sach_giay_dung_som_va_bao_con_lai(tmp_path, monkeypatch):
    nguon = tmp_path / "nguon"
    nguon.mkdir()
    dich = tmp_path / "dich"
    for i in range(3):
        (nguon / "b{0}.mp3".format(i)).write_bytes(
            "khac nhau {0}".format(i).encode())

    def _chuan_hoa_cham(ffmpeg, vao, ra):
        os.makedirs(os.path.dirname(ra), exist_ok=True)
        with open(ra, "wb") as tep:
            tep.write(b"gia")
        return 60.0, -32.0, -12.0

    monkeypatch.setattr(kho_nhac, "_chuan_hoa_mot_bai", _chuan_hoa_cham)
    monkeypatch.setattr(ffmpeg_goi_san, "du_dung", lambda _f: True)
    monkeypatch.setattr(kho_nhac, "_do_co_giong", lambda ff, d: (False, ""))
    monkeypatch.setattr(kho_nhac, "_chay_ffmpeg",
                        lambda cmd, timeout=600.0: _stderr_meta())

    kq = kho_nhac.cap_nhat("khong-dung", 0.0, thu_muc_nguon=str(nguon),
                           thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    assert kq["het_ngan_sach"] is True
    assert kq["con_lai"] >= 1
    assert kq["moi"] == 0, "ngân sách 0 giây thì không được xử lý bài nào mới"


def test_khong_co_ffmpeg_du_dung_thi_bao_loi_chung_khong_nem_ngoai(tmp_path, monkeypatch):
    monkeypatch.setattr(ffmpeg_goi_san, "du_dung", lambda _f: False)
    kq = kho_nhac.cap_nhat(str(tmp_path), None,
                           thu_muc_nguon=str(tmp_path / "khong-ton-tai"),
                           thu_muc_dich=str(tmp_path / "dich"),
                           ffmpeg="ffmpeg-gia")
    assert kq["loi_chung"]
    assert kq["moi"] == 0


# ── 6. Chỉ mục CSV: chủ kênh sửa `cam_xuc`/`loai` thì tool không đè ──────────


def test_csv_ghi_de_cam_xuc_va_loai_duoc_giu_lai_lan_sau(tmp_path, monkeypatch):
    nguon = tmp_path / "nguon"
    nguon.mkdir()
    dich = tmp_path / "dich"
    (nguon / "c.mp3").write_bytes(b"noi dung co dinh")

    def _chuan_hoa_gia(ffmpeg, vao, ra):
        os.makedirs(os.path.dirname(ra), exist_ok=True)
        with open(ra, "wb") as tep:
            tep.write(b"gia")
        return 90.0, -32.0, -12.0

    monkeypatch.setattr(kho_nhac, "_chuan_hoa_mot_bai", _chuan_hoa_gia)
    monkeypatch.setattr(ffmpeg_goi_san, "du_dung", lambda _f: True)
    monkeypatch.setattr(kho_nhac, "_do_co_giong", lambda ff, d: (False, ""))
    monkeypatch.setattr(
        kho_nhac, "_chay_ffmpeg",
        lambda cmd, timeout=600.0: _stderr_meta(title="Storm Test"))

    kq1 = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                            thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    assert kq1["moi"] == 1
    id8 = next(iter(kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))["bai"]))
    # Máy tự đoán "căng" từ chữ "Storm" — có hậu tố "(đoán từ tên)" trong CSV.
    assert "căng" in kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))["bai"][id8]["cam_xuc"]

    duong_csv = kho_nhac._duong_csv(str(dich))
    with open(duong_csv, "r", encoding="utf-8-sig") as tep:
        noi_dung = tep.read()
    assert "(đoán từ tên)" in noi_dung

    # Chủ kênh sửa tay: bỏ hậu tố, đổi nhãn, đổi loại.
    import csv as _csv
    with open(duong_csv, "r", encoding="utf-8-sig", newline="") as tep:
        dong = list(_csv.reader(tep))
    cot = dong[0]
    i_id, i_cam, i_loai = cot.index("id"), cot.index("cam_xuc"), cot.index("loai")
    for d in dong[1:]:
        if d[i_id] == id8:
            d[i_cam] = "vui"
            d[i_loai] = "mo_dau"
    with open(duong_csv, "w", encoding="utf-8-sig", newline="") as tep:
        w = _csv.writer(tep)
        w.writerows(dong)

    # Chạy lại: KHÔNG có tệp nguồn nào đổi, nhưng vẫn phải đọc CSV và giữ sửa.
    kq2 = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                            thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    assert kq2["bo_qua_khong_doi"] == 1
    chi_muc2 = kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))
    b = chi_muc2["bai"][id8]
    assert b["cam_xuc"] == ["vui"]
    assert b["cam_xuc_nguon"] == "kênh"
    assert b["loai"] == "mo_dau"

    with open(duong_csv, "r", encoding="utf-8-sig") as tep:
        noi_dung2 = tep.read()
    assert "(đoán từ tên)" not in noi_dung2
    assert "vui" in noi_dung2 and "mo_dau" in noi_dung2


# ── 7. Mất gốc: tệp nguồn biến mất → cờ `mat_goc`, KHÔNG xoá bản đã chuẩn hoá ─


def test_mat_goc_khong_xoa_ban_da_chuan_hoa(tmp_path, monkeypatch):
    nguon = tmp_path / "nguon"
    nguon.mkdir()
    dich = tmp_path / "dich"
    (nguon / "d.mp3").write_bytes(b"se bi xoa")

    def _chuan_hoa_gia(ffmpeg, vao, ra):
        os.makedirs(os.path.dirname(ra), exist_ok=True)
        with open(ra, "wb") as tep:
            tep.write(b"gia")
        return 50.0, -32.0, -12.0

    monkeypatch.setattr(kho_nhac, "_chuan_hoa_mot_bai", _chuan_hoa_gia)
    monkeypatch.setattr(ffmpeg_goi_san, "du_dung", lambda _f: True)
    monkeypatch.setattr(kho_nhac, "_do_co_giong", lambda ff, d: (False, ""))
    monkeypatch.setattr(kho_nhac, "_chay_ffmpeg",
                        lambda cmd, timeout=600.0: _stderr_meta())

    kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                      thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    id8 = next(iter(kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))["bai"]))
    duong_bai = os.path.join(str(dich), "bai", id8 + ".m4a")
    assert os.path.isfile(duong_bai)

    os.remove(str(nguon / "d.mp3"))
    kq2 = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                            thu_muc_dich=str(dich), ffmpeg="ffmpeg-gia")
    assert kq2["mat_goc"] == 1
    chi_muc = kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))
    assert chi_muc["bai"][id8]["mat_goc"] is True
    assert os.path.isfile(duong_bai), "gốc mất thì vẫn giữ bản đã chuẩn hoá"


# ── 8. Chống trùng theo Suno `id=` (FFmpeg thật) ─────────────────────────────


@pytest.mark.skipif(not CO_FFMPEG, reason="máy này không có FFmpeg đủ dùng")
def test_hai_tep_cung_suno_id_chi_ra_mot_bai(tmp_path):
    nguon = tmp_path / "nguon"
    nguon.mkdir()
    dich = tmp_path / "dich"
    ma = "5b21e8ca-ffd9-453e-9b23-eaa07c518d53"
    _tao_mp3(str(nguon), "1 Ivory Panic.mp3", giay=3, tan_so=440, id_suno=ma,
             tieu_de="Ivory Panic")
    _tao_mp3(str(nguon), "1.1 Ivory Panic (ban sao).mp3", giay=3, tan_so=440,
             id_suno=ma, tieu_de="Ivory Panic")

    kq = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                           thu_muc_dich=str(dich), ffmpeg=FFMPEG)
    assert kq["tong_bai_trong_kho"] == 1
    assert kq["trung_gop"] == 1
    assert kq["moi"] == 1
    chi_muc = kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))
    [b] = chi_muc["bai"].values()
    assert len(b["nguon"]) == 2


# ── 9. Chạy thật 2–3 tệp sine/anullsrc: đo lại ~−32 LUFS ─────────────────────


@pytest.mark.skipif(not CO_FFMPEG, reason="máy này không có FFmpeg đủ dùng")
def test_chuan_hoa_that_ra_khoang_am_32_lufs(tmp_path):
    nguon = tmp_path / "nguon"
    nguon.mkdir()
    dich = tmp_path / "dich"
    _tao_mp3(str(nguon), "sine1.mp3", giay=5, tan_so=220, tieu_de="Panic Test")
    _tao_mp3(str(nguon), "sine2.mp3", giay=6, tan_so=880, tieu_de="Calm Hearth")
    _tao_mp3(str(nguon), "sine3.mp3", giay=4, tan_so=550, tieu_de="Silent Drift")

    kq = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                           thu_muc_dich=str(dich), ffmpeg=FFMPEG)
    assert kq["moi"] == 3
    assert not kq["loi"], kq["loi"]

    chi_muc = kho_nhac._doc_chi_muc_tu_thu_muc(str(dich))
    assert len(chi_muc["bai"]) == 3
    thu_muc_bai = os.path.join(str(dich), "bai")
    for id8, b in chi_muc["bai"].items():
        duong_bai = os.path.join(thu_muc_bai, id8 + ".m4a")
        assert os.path.isfile(duong_bai)
        assert os.path.getsize(duong_bai) > 0
        if b["giay"] < 0.5:
            continue  # anullsrc: cắt lặng có thể còn gần như rỗng, không đo LUFS được
        do_lai = kho_nhac.do_lufs_that(FFMPEG, duong_bai)
        if do_lai is None:
            continue
        assert abs(do_lai["lufs"] - (-32.0)) < 2.0, (id8, do_lai)

    # Chỉ mục ghi ra đĩa, CSV có BOM (UTF-8-BOM) để Excel không vỡ chữ Việt.
    duong_csv = kho_nhac._duong_csv(str(dich))
    with open(duong_csv, "rb") as tep:
        assert tep.read(3) == b"\xef\xbb\xbf"

    duong_json = kho_nhac._duong_json(str(dich))
    with open(duong_json, "r", encoding="utf-8") as tep:
        du = json.load(tep)
    assert len(du["bai"]) == 3

    # Lượt 2 trên đúng kho đó: gần như 0 việc (tăng dần thật sự).
    kq2 = kho_nhac.cap_nhat("khong-dung", None, thu_muc_nguon=str(nguon),
                            thu_muc_dich=str(dich), ffmpeg=FFMPEG)
    assert kq2["moi"] == 0
    assert kq2["bo_qua_khong_doi"] == 3


# ── 10. Việc 2 đã cài phần lõi (28/09/2026) — bài kiểm đầy đủ ở
#        `tests/test_nhac_theo_phan.py`; ở đây chỉ chốt hợp đồng biên ──────────


def test_chon_nhac_kho_rong_tra_rong_va_lenh_lop_nhac_bao_loi_ro():
    assert kho_nhac.chon_nhac([], {}, [], hat_giong="TL1-0001") == []
    assert kho_nhac.chon_nhac([{"bat_dau": 0, "ket_thuc": 60}], {"bai": {}}, [],
                              hat_giong="TL1-0001") == []
    with pytest.raises(ValueError):
        kho_nhac.lenh_lop_nhac("goc", {}, [], [], "ffmpeg", "ra.m4a")
