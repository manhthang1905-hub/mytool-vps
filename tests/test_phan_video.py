"""Dựng theo PHẦN (Việc 2, `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`).

Chủ kênh đang sửa tay mọi video bằng CapCut: nghỉ ~3 giây + tối dần/sáng dần
giữa hai phần, mỗi phần một nhạc nền, SRT không còn dấu `---`, mục lục khớp
mốc thật. Bài kiểm chốt phần THUẦN của `core/phan_video.py`:

  1. đọc `silencedetect` (stderr giả), bám ứng viên về lặng GẦN NHẤT — không
     phải lặng dài nhất (nhịp nghỉ tự nhiên TL3/0004 dài hơn nhịp nghỉ phần);
  2. `bang_bu` + hàm `f` dời mốc;
  3. `sach_srt` trên đúng các câu thật TL3/0004 quanh ranh giới 93,8–95,1s;
  4. chuỗi lọc chèn lặng bù vào giọng;
  5. xếp cảnh: cảnh đầu phần bắt đầu giữa khoảng nghỉ, mờ vào/ra đúng chỗ;
  6. khung nhạc từng phần;
  7. `_bao_dam_ngat_phan` với goi_chat giả: AI đổi chữ → vứt;
  8. bàn giao giao `8-phu-de.srt` dưới tên `3-phu-de.srt`.

Không gọi mạng, không tốn tiền.
"""

from __future__ import annotations

import os

import pytest

from core import phan_video as pv
from core.phan_video import KeHoach, RanhGioi


# ── 1. silencedetect ────────────────────────────────────────────────────────

STDERR_GIA = """
[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 0.21 | silence_duration: 0.21
[silencedetect @ 0x1] silence_start: 84.126
[silencedetect @ 0x1] silence_end: 85.085 | silence_duration: 0.96
[silencedetect @ 0x1] silence_start: 93.785
[silencedetect @ 0x1] silence_end: 95.1209 | silence_duration: 1.3359
[silencedetect @ 0x1] silence_start: 102.49
[silencedetect @ 0x1] silence_end: 104.083 | silence_duration: 1.593
[silencedetect @ 0x1] silence_start: 903.9
"""


def test_doc_lang_ca_lang_cuoi_tep():
    lang = pv.doc_lang(STDERR_GIA, tong=904.8)
    assert lang[2] == (93.785, 95.1209)
    assert lang[-1] == (903.9, 904.8), "lặng tới hết tệp lấy tổng làm mép"
    assert len(pv.doc_lang(STDERR_GIA)) == 4, "không có tổng thì bỏ khoảng cuối"


def test_bam_lang_lay_khoang_CHUA_moc_khong_lay_khoang_dai_nhat():
    """Cộng dồn 2-doan TL3/0004: đoạn 1 dài 93,83s → lặng 93,785–95,12 chứa
    mốc. Lặng 102,49–104,08 DÀI hơn (1,59s) — chọn "dài nhất trong cửa" là
    bám nhầm sang câu bên cạnh khi mốc lệch."""
    lang = pv.doc_lang(STDERR_GIA, tong=904.8)
    assert pv.bam_lang(93.83, lang) == (93.785, 95.1209)
    # Mốc SRT của câu "--- ユングは、" (93,76) nằm NGAY TRƯỚC khoảng lặng.
    assert pv.bam_lang(93.76, lang) == (93.785, 95.1209)
    assert pv.bam_lang(50.0, lang) is None


def test_lang_dai_tu_nhan_ranh_gioi_khi_giong_nghi_3s():
    lang = [(0.0, 3.5), (40.0, 43.1), (70.0, 71.4), (100.0, 103.0), (118.0, 121.0)]
    ranh = pv._ranh_tu_ung_vien([], lang, 121.0, 3.0, "", lambda s: None)
    assert [(r.a, r.b) for r in ranh] == [(40.0, 43.1), (100.0, 103.0)], \
        "lặng đầu/cuối tệp không phải ranh giới; lặng 1,4s không phải"
    # Giọng cũ nghỉ 1,2s: KHÔNG được tự nhận lặng dài.
    assert pv._ranh_tu_ung_vien([], lang, 121.0, 1.2, "", lambda s: None) == []


def test_ung_vien_tu_srt():
    srt = ("1\n00:00:00,000 --> 00:00:02,000\nmở.\n\n"
           "2\n00:01:33,760 --> 00:01:35,620\n--- ユングは、\n\n"
           "3\n00:03:20,120 --> 00:03:23,100\n——— 風に舞う\n\n"
           "4\n00:03:30,000 --> 00:03:31,000\nmột - hai\n")
    assert pv.ung_vien_tu_srt(srt) == [93.76, 200.12]


# ── 2. bảng bù + f ──────────────────────────────────────────────────────────


def _kh(*ranh, tong=300.0, p=3.0):
    r = [RanhGioi(a, b) for a, b in ranh]
    return KeHoach(tong_giong=tong, ranh=r, bu=pv.bang_bu(r, p), giay_nghi=p)


def test_bang_bu_va_ham_f():
    kh = _kh((10.0, 11.2), (20.0, 23.5))
    assert kh.bu == pytest.approx([1.8, 0.0]), "nghỉ đủ dài thì không bù"
    assert kh.f(5.0) == 5.0
    assert kh.f(10.0) == 10.0, "hết lời a_k chưa dời"
    assert kh.f(11.2) == pytest.approx(13.0), "giọng vào lại b_k dời đủ e_k"
    assert kh.f(30.0) == pytest.approx(31.8)
    assert kh.b2(0) - kh.a2(0) == pytest.approx(3.0), "nghỉ trong video đúng P"
    assert kh.m2(0) == pytest.approx(11.5)
    assert kh.tong_moi == pytest.approx(301.8)
    assert kh.khong_bu().tong_moi == 300.0


# ── 3. SRT sạch — câu THẬT của TL3/0004 quanh ranh giới đầu tiên ─────────────

SRT_TL3_0004 = """32
00:01:30,880 --> 00:01:33,760
」という聖域への入り口なのです。

33
00:01:33,760 --> 00:01:35,620
--- ユングは、

34
00:01:35,620 --> 00:01:38,720
人間が社会の中で生きていくために身につける

35
00:01:38,720 --> 00:01:42,300
外面的な役割を「ペルソナ」と呼びました。
"""


def test_sach_srt_that_tl3_0004():
    from core.phu_de import doc_srt

    kh = _kh((93.785, 95.1209), tong=904.8)
    cau = pv.sach_srt(doc_srt(SRT_TL3_0004), kh)
    assert all("---" not in c.chu for c in cau), "lỗi (a): tiền tố --- lọt sang YouTube"
    a2, b2 = kh.a2(0), kh.b2(0)
    for c in cau:
        assert c.ket_thuc <= a2 + 1e-6 or c.bat_dau >= b2 - 1e-6, \
            "lỗi (b): câu {0!r} hiện trong khoảng nghỉ".format(c.chu)
    yung = next(c for c in cau if c.chu == "ユングは、")
    assert yung.bat_dau == pytest.approx(b2), "câu mở phần hiện lúc giọng vào lại"
    assert cau[0].ket_thuc == pytest.approx(93.76)
    # Câu sau ranh giới dời đúng e_k.
    assert cau[2].bat_dau == pytest.approx(95.62 + kh.bu[0])


def test_sach_srt_cau_chay_qua_mep_nghi_va_cau_trong_nghi():
    from core.phu_de import Cau

    kh = _kh((10.0, 11.0))
    cau = [Cau(1, 8.0, 10.6, "chạy qua mép"), Cau(2, 10.3, 10.9, "trong nghỉ"),
           Cau(3, 11.0, 13.0, "sau nghỉ")]
    ra = pv.sach_srt(cau, kh)
    assert ra[0].ket_thuc == pytest.approx(10.0)
    # Câu trong nghỉ bị dồn về b'_k TRÙNG mốc câu sau → gộp chữ, không vứt.
    assert [c.chu for c in ra] == ["chạy qua mép", "trong nghỉ sau nghỉ"]
    assert ra[1].bat_dau == pytest.approx(kh.b2(0))
    assert [c.so for c in ra] == [1, 2]
    assert all(ra[i].ket_thuc <= ra[i + 1].bat_dau + 1e-9 for i in range(len(ra) - 1))


def test_bo_tien_to_ngat():
    assert pv.bo_tien_to_ngat("--- ユングは、") == "ユングは、"
    assert pv.bo_tien_to_ngat("——— a") == "a"
    assert pv.bo_tien_to_ngat("một - hai") == "một - hai"
    assert pv.bo_tien_to_ngat("---") == ""


# ── 4. lọc giọng chèn lặng bù ───────────────────────────────────────────────


def test_loc_giong_bu_nghi():
    kh = _kh((10.0, 11.2), (20.0, 23.5), (40.0, 41.0))
    loc = pv.loc_giong_bu_nghi(kh.ranh, kh.bu)
    assert loc.startswith("[1:a]aformat=sample_rates=48000:channel_layouts=stereo")
    assert "asplit=3" in loc, "hai chỗ bù (chỗ thứ hai nghỉ đủ) → 3 khúc"
    assert "aevalsrc=0|0:c=stereo:s=48000:d=1.8000" in loc
    assert "aevalsrc=0|0:c=stereo:s=48000:d=2.0000" in loc
    assert "atrim=start=10.6000:end=40.5000" in loc, "cắt đúng giữa khoảng nghỉ"
    assert loc.endswith("concat=n=5:v=0:a=1[g]")
    # Không bù gì: chỉ đổi định dạng, không asplit.
    assert pv.loc_giong_bu_nghi([], []) == (
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        "asetpts=PTS-STARTPTS[g]")


# ── 5. xếp cảnh ─────────────────────────────────────────────────────────────


def test_xep_canh_canh_dau_phan_bat_dau_giua_khoang_nghi():
    kh = _kh((20.0, 21.2), (50.0, 53.1), tong=80.0)
    moc = [0.2, 8.0, 15.0, 21.3, 30.0, 49.0, 53.2, 60.0]
    het = [7.9, 14.9, 19.9, 29.9, 48.9, 50.0, 59.9, 80.0]
    moi, _het_moi, giu, vao, ra, bo = pv.xep_canh(moc, het, kh)
    assert moi[0] == 0.0
    assert all(giu)
    assert moi[3] == pytest.approx(kh.m2(0)), "cảnh gần b_k nhất vào ở giữa nghỉ"
    assert moi[6] == pytest.approx(kh.m2(1))
    assert vao == {3, 6} and ra == {2, 5}
    assert bo == []
    assert moi[4] == pytest.approx(30.0 + kh.bu[0]), "cảnh giữa phần dời theo f"


def test_xep_canh_khong_co_canh_gan_ranh_gioi_thi_bo_chuyen():
    kh = _kh((20.0, 21.2), tong=80.0)
    moc = [0.0, 10.0, 40.0]
    _m, _h, giu, vao, ra, bo = pv.xep_canh(moc, [9.9, 39.9, 80.0], kh)
    assert bo == [0] and not vao and not ra and all(giu)


def test_xep_canh_canh_lot_giua_nghi_bi_bo():
    kh = _kh((20.0, 21.2), tong=80.0)
    moc = [0.0, 10.0, 20.9, 21.25, 40.0]
    _m, _h, giu, vao, ra, _bo = pv.xep_canh(moc, [9.9, 20.8, 21.2, 39.9, 80.0], kh)
    assert giu == [True, True, False, True, True]
    assert vao == {3} and ra == {1}


# ── 6. khung nhạc ───────────────────────────────────────────────────────────


def test_khung_nhac_im_2s_giua_phan():
    kh = _kh((20.0, 21.2), (50.0, 53.1), tong=80.0)
    k = pv.khung_nhac(kh, gap=2.0)
    assert k[0]["bat_dau"] == 0.0 and k[0]["mo_vao"] == 2.0
    assert k[0]["ket_thuc"] == pytest.approx(kh.a2(0) + 0.5)
    assert k[1]["bat_dau"] == pytest.approx(kh.b2(0) - 0.5)
    assert k[1]["bat_dau"] - k[0]["ket_thuc"] == pytest.approx(2.0), "im đúng 2s"
    assert k[-1]["ket_thuc"] == pytest.approx(kh.tong_moi) and k[-1]["mo_ra"] == 3.0
    assert k[1]["mo_vao"] == 1.5 and k[1]["mo_ra"] == 2.0


def test_cam_xuc_ve_sau_mui_ten():
    assert pv._doi_cam_xuc("uncertain, seeking → shocked, awakening") == ["căng", "hùng tráng"]
    assert pv._doi_cam_xuc("fearful → centered, resolute") == ["tĩnh lặng", "hùng tráng"]


# ── 7. `_bao_dam_ngat_phan` với goi_chat giả ────────────────────────────────


class _K:
    ngat_phan_tu_dong = True
    ky_tu_moi_phut = 10
    mo_hinh = "gia"
    ngon_ngu = "vi"


def _bc(tra_ve):
    from core.auto_khau import BoiCanh

    goi = []

    def goi_chat(loi_nhac, **kw):
        goi.append(kw.get("khoa"))
        return tra_ve(loi_nhac)

    bc = BoiCanh(goc=".", kenh=_K(), goi_chat=goi_chat, ngu=lambda s: None)
    return bc, goi


BAI = "\n".join("Câu số {0} của bài viết khá dài.".format(i) for i in range(1, 21))


def test_ngat_phan_ai_doi_chu_thi_vut():
    from core.auto import LuotChay
    from core.auto_khau import _bao_dam_ngat_phan

    def sai(_ln):
        return BAI.replace("Câu số 3", "Câu thứ 3").replace(
            "Câu số 8", "---\nCâu số 8").replace("Câu số 15", "---\nCâu số 15")

    bc, goi = _bc(sai)
    luot = LuotChay(ma_kenh="K", ma_luot="0001", thu_muc=".")
    assert _bao_dam_ngat_phan(bc, luot, _K(), BAI) == BAI
    assert goi == ["K:0001:chat:ngat-phan"], "đúng một lượt, khoá cố định"


def test_ngat_phan_ai_chi_chen_dau_thi_nhan():
    from core.auto import LuotChay
    from core.auto_khau import _bao_dam_ngat_phan, tach_phan

    def dung(_ln):
        return BAI.replace("Câu số 8", "---\nCâu số 8").replace(
            "Câu số 15", "\n---\n\nCâu số 15")

    bc, _goi = _bc(dung)
    ra = _bao_dam_ngat_phan(bc, LuotChay(ma_kenh="K", ma_luot="1", thu_muc="."),
                            _K(), BAI)
    assert len(tach_phan(ra)) == 3


def test_ngat_phan_khong_goi_khi_du_phan_hoac_ngan_hoac_tat():
    from core.auto import LuotChay
    from core.auto_khau import _bao_dam_ngat_phan

    bc, goi = _bc(lambda _ln: "x")
    luot = LuotChay(ma_kenh="K", ma_luot="1", thu_muc=".")
    du_phan = "a\n---\nb\n---\nc"
    assert _bao_dam_ngat_phan(bc, luot, _K(), du_phan) == du_phan
    assert _bao_dam_ngat_phan(bc, luot, _K(), "ngắn") == "ngắn"

    class Tat(_K):
        ngat_phan_tu_dong = False

    assert _bao_dam_ngat_phan(bc, luot, Tat(), BAI) == BAI
    assert goi == []


def test_ngat_phan_goi_chat_nem_loi_khong_chan():
    from core.auto import LuotChay
    from core.auto_khau import _bao_dam_ngat_phan

    def hong(_ln):
        raise ValueError("hỏng mạng giả")

    bc, _goi = _bc(hong)
    assert _bao_dam_ngat_phan(bc, LuotChay(ma_kenh="K", ma_luot="1", thu_muc="."),
                              _K(), BAI) == BAI


# ── 8. bàn giao: giao `8-phu-de.srt` dưới tên `3-phu-de.srt` ────────────────


def test_xuat_goi_uu_tien_srt_sach_ten_dich_giu_nguyen(tmp_path):
    from core.ban_giao_dang import xuat_goi

    luot = tmp_path / "luot"
    (luot / "7-thumbnail").mkdir(parents=True)
    (luot / "8-video.mp4").write_bytes(b"MP4")
    (luot / "3-phu-de.srt").write_text("cu", encoding="utf-8")
    (luot / "7-thumbnail" / "thumb_001.png").write_bytes(b"PNG")
    goi = xuat_goi(str(luot), str(tmp_path / "DONE"), "K-0001")
    assert (tmp_path / "DONE" / "K-0001" / "3-phu-de.srt").read_text(encoding="utf-8") == "cu"
    (luot / "8-phu-de.srt").write_text("sach", encoding="utf-8")
    xuat_goi(str(luot), str(tmp_path / "DONE"), "K-0001")
    assert (tmp_path / "DONE" / "K-0001" / "3-phu-de.srt").read_text(encoding="utf-8") == "sach"
    assert not os.path.exists(os.path.join(goi, "8-phu-de.srt"))
    assert sorted(os.listdir(goi)) == ["3-phu-de.srt", "8-video.mp4", "thumb_001.png"]


# ── 9. kênh: khoá mới đọc được, gõ nhầm không làm hỏng ──────────────────────


def test_kenh_doc_khoa_dung_theo_phan(tmp_path):
    from core.kenh import doc_kenh

    thu = tmp_path / "CHANNEL" / "K"
    thu.mkdir(parents=True)
    (thu / "kenh.yaml").write_text('ma: "K"\n', encoding="utf-8")
    k = doc_kenh(str(tmp_path), "K")
    assert (k.giay_nghi_chuyen_phan, k.chuyen_phan, k.nhac_theo_phan,
            k.ngat_phan_tu_dong) == (3.0, "den", True, False), "mặc định: cờ 0₫ bật"
    (thu / "kenh.yaml").write_text(
        'ma: "K"\ngiay_nghi_chuyen_phan: -2\nchuyen_phan: "xoay"\n'
        'nhac_theo_phan: false\nnhac_duoi_giong_db: 90\nngat_phan_tu_dong: true\n',
        encoding="utf-8")
    k = doc_kenh(str(tmp_path), "K")
    assert k.giay_nghi_chuyen_phan == 0.0 and k.chuyen_phan == "den"
    assert k.nhac_theo_phan is False and k.nhac_duoi_giong_db == 40.0
    assert k.ngat_phan_tu_dong is True
