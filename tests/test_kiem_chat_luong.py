"""core/kiem_chat_luong.py — cổng chất lượng thành phẩm. Media TỔNG HỢP (lavfi) trong tmp_path; không mạng,
không AI, không đụng dữ liệu thật. Phần cần FFmpeg tự bỏ qua khi máy không có."""
from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import subprocess
import time

import pytest

from core import auto, kiem_chat_luong as kcl
from core.dung_video import tim_ffmpeg

FF = tim_ffmpeg()
can_ff = pytest.mark.skipif(not FF, reason="máy này không có FFmpeg")


def _ff(*ts):
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", *ts], check=True, timeout=120)


def _video(duong, *, giay=12.0, am="sine=frequency=440:duration={g}", vf="", nguon="testsrc2=size=320x180:rate=24"):
    """Video hình chuyển động + tiếng tuỳ chọn. `vf` thêm bộ lọc (vd tpad để tạo khung đứng)."""
    ts = ["-f", "lavfi", "-i", "{0}:duration={1}".format(nguon, giay)]
    if am:
        ts += ["-f", "lavfi", "-i", am.format(g=giay)]
    if vf:
        ts += ["-vf", vf]
    ts += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-g", "24"]
    if am:
        ts += ["-c:a", "aac", "-ar", "48000"]
    _ff(*ts, "-t", str(giay), duong)


def _srt(duong, cues):
    kcl.ghi_srt(duong, cues)


def _luot(tmp_path, *, video_kw=None, cues=None, seo="DESCRIPTION:\nmô tả\n\n00:00 a\n00:20 b\n00:40 c\nKEYWORDS:\na, b\n"):
    goc = tmp_path / "goc"
    d = goc / "PROJECTS" / "AUTO" / "K1" / "0001"
    d.mkdir(parents=True)
    if video_kw is not None:
        _video(str(d / "8-video.mp4"), **video_kw)
    _srt(str(d / "3-phu-de.srt"), cues or [(0.0, 2.0, "chao"), (3.0, 5.0, "ban")])
    (d / "1-seo.txt").write_text(seo, encoding="utf-8")
    return str(goc), str(d)


def _gt(d):
    from core.ban_giao_dang import doc_gioi_thieu
    return doc_gioi_thieu(d)


# ── thuần (không FFmpeg) ──────────────────────────────────────────────────────

def test_danh_gia_tieng_va_hinh():
    do = {"am": {"lufs": -24.0, "tp": -0.2, "im_ngoai_max": 5.0, "im_ngoai": [[30.0, 5.0]], "im_trong_max": 3.0,
                 "im_dau": 0.0},
          "hinh": {"dong_bang_max": 9.0, "dong_bang_pct": 1.0, "den_ngoai_ranh": [], "bitrate_mbps": 3.0}}
    ma = {(x["ma"], x["muc"], x["sua"]) for x in kcl.danh_gia(do)}
    assert ("am_do_to", "chan", "chuan_hoa_am") in ma and ("am_dinh", "chan", "chuan_hoa_am") in ma
    assert ("am_lang", "chan", "") in ma, "lặng ngoài chỗ nghỉ: không sửa rẻ được → chặn"
    assert ("hinh_dong_bang", "chan", "") in ma


def test_lang_trong_cho_nghi_giua_phan_khong_tinh():
    do = {"am": {"lufs": -14.0, "tp": -3.0, "im_ngoai_max": 0.0, "im_trong_max": 4.8, "im_dau": 0.0}}
    assert kcl.danh_gia(do) == []
    assert kcl._trong_ranh(146.0, 3.0, [(145.3, 148.5)])  # noqa: SLF001


def test_doan_dong_bang_tu_goi_tin():
    goi = [(i / 24.0, 9000, False) for i in range(48)] + [(2 + i / 24.0, 40, i % 24 == 0) for i in range(24 * 5)] + \
          [(7 + i / 24.0, 9000, False) for i in range(48)]
    goi = [(t, 90000 if k else s, k) for t, s, k in goi]       # khung khoá giữa đoạn đứng vẫn to — không cắt đoạn
    db = kcl.doan_dong_bang(goi)
    assert len(db) == 1 and 4.9 <= db[0][1] <= 5.1


def test_sua_mo_ta_chuong_va_the():
    mt = "gioi thieu\n00:05 mo\n00:30 hai\n00:35 sat qua\n01:00 ba\n09:00 vuot duoi\n#tag"
    moi, the, da = kcl.sua_mo_ta(mt, ", ".join("the{0:03d}".format(i) for i in range(100)), 120.0)
    dong = moi.splitlines()
    assert "00:00 mo" in dong and "00:35 sat qua" not in dong and "09:00 vuot duoi" not in dong
    assert kcl.do_meta("t", moi, the, 120.0)["chuong_hop_le"]
    assert len(the.replace(" ", "")) <= 500 and da


def test_sua_mo_ta_it_hon_ba_chuong_thi_bo_het():
    moi, _t, da = kcl.sua_mo_ta("x\n00:00 a\n00:20 b\n", "", 600.0)
    assert "00:00" not in moi and da


def test_mo_ta_rong_thi_chan():
    loi = kcl.danh_gia({"meta": kcl.do_meta("tieu de", "", "", 600)})
    assert [x["ma"] for x in loi if x["muc"] == "chan"] == ["meta_mo_ta_rong"]


def test_kich_ban_cau_rao_va_lap():
    kb = kcl.do_kich_ban("人生の羅針盤へようこそ。" + "同じ文章を繰り返します。" * 60)
    assert "ようこそ" in kb["rao"] and kb["lap_pct"] > 50
    loi = {x["ma"]: x["muc"] for x in kcl.danh_gia({"kich_ban": kb})}
    assert loi == {"kb_rao": "canh_bao", "kb_lap": "canh_bao"}, "kịch bản chỉ cảnh báo, không chặn"


def test_lech_phu_de_deu_va_khong_deu():
    khoi = [i * 3.0 for i in range(60)]
    noi = [(k, k + 1.5) for k in khoi]
    dung = [(k, k + 1.4, "x") for k in khoi]
    assert kcl.lech_phu_de(dung, khoi, noi)["khop05"] == 1.0
    lech = [(k + 1.2, k + 2.6, "x") for k in khoi]
    r = kcl.lech_phu_de(lech, khoi, noi)
    assert r["khop05"] < 0.45 and abs(r["doi_tot"] + 1.2) < 0.06 and r["khop05_tot"] == 1.0
    assert [x["ma"] for x in kcl.danh_gia({"phu_de": dict(r, so=60)})] == ["pd_lech"]
    # khởi âm KHÔNG đều (như giọng thật) + phụ đề TRÔI dần (0 → 4 s, kiểu mốc rải theo số chữ) → không độ dời
    # nào cứu được
    import random
    rd = random.Random(3)
    khoi2, t = [], 0.0
    for _ in range(80):
        khoi2.append(round(t, 2))
        t += rd.uniform(1.5, 4.5)
    noi2 = [(k, k + 1.0) for k in khoi2]
    lon = [(k + 0.05 * i, k + 1.0 + 0.05 * i, "x") for i, k in enumerate(khoi2)]
    r2 = kcl.lech_phu_de(sorted(lon), khoi2, noi2)
    assert [x["ma"] for x in kcl.danh_gia({"phu_de": dict(r2, so=80)})] == ["pd_lech_khong_deu"], r2


def test_lech_phu_de_doan_noi_khong_phu():
    khoi = [0.0, 3.0, 20.0]
    noi = [(0.0, 2.0), (3.0, 15.0), (20.0, 22.0)]
    r = kcl.lech_phu_de([(0.0, 2.0, "a"), (3.0, 4.0, "b"), (20.0, 22.0, "c")], khoi, noi)
    assert r["thieu_max"] == pytest.approx(11.0) and r["thieu_luc"] == pytest.approx(4.0)


def test_sua_phu_de_doi_kep_duoi_bo_rong(tmp_path):
    d = str(tmp_path)
    kcl.ghi_srt(os.path.join(d, "3-phu-de.srt"), [(1.0, 2.0, "a"), (1.5, 3.0, "b"), (4.0, 5.0, "。"), (9.0, 12.0, "c")])
    do = {"dai_video": 10.0, "phu_de": {"khop05": 0.1, "khop05_tot": 0.9, "doi_tot": -0.5}}
    da = kcl.sua_phu_de(d, do, kcl.NGUONG)
    cues = kcl.doc_srt(os.path.join(d, "3-phu-de.srt"))
    assert da and [c[2] for c in cues] == ["a", "b", "c"]
    assert cues[0][0] == pytest.approx(0.5) and cues[0][1] <= cues[1][0] + 1e-6, "dời −0,5 s, hết chồng"
    assert cues[-1][1] == pytest.approx(10.0), "kẹp về đuôi video"


def test_doc_gioi_thieu_seo_thieu_tieu_de_muc_va_bom(tmp_path):
    from core.ban_giao_dang import doc_gioi_thieu
    (tmp_path / "1-seo.txt").write_text("mô tả dòng một\n\n00:00 mở\n\nHASHTAGS:\n#a\nKEYWORDS:\nx, y\n",
                                        encoding="utf-8")
    gt = doc_gioi_thieu(str(tmp_path))
    assert gt["mo_ta"].startswith("mô tả dòng một") and "HASHTAGS" not in gt["mo_ta"] and gt["the"] == "x, y"
    (tmp_path / "1-seo.txt").write_text("DESCRIPTION:\nco tieu de\nKEYWORDS:\nz\n", encoding="utf-8-sig")
    assert doc_gioi_thieu(str(tmp_path))["mo_ta"] == "co tieu de"


def test_chi_so_ho_so_va_ho_so_video(tmp_path):
    from core import ho_so_video
    kq = {"diem": 93, "dat": True, "loi": [{"ma": "kb_rao", "muc": "canh_bao"}], "da_sua": ["x"],
          "do": {"am": {"lufs": -14.1, "tp": -2.0, "im_ngoai_max": 1.0}, "hinh": {"dong_bang_pct": 0.5},
                 "clip": {"tinh_pct": 4.0, "trung": []}, "phu_de": {"cps95": 8.0, "khop05": 0.6},
                 "kich_ban": {"rao": ["ようこそ"]}, "meta": {"chuong": 7}}}
    (tmp_path / kcl.TEP_KET_QUA).write_text(json.dumps(kq), encoding="utf-8")
    ra = ho_so_video._chat_luong(str(tmp_path))  # noqa: SLF001
    assert ra["cl_diem"] == 93 and ra["cl_lufs"] == -14.1 and ra["cl_clip_tinh_pct"] == 4.0
    assert ra["cl_rao"] == 1 and ra["cl_loi"] == ["kb_rao"] and ra["chat_luong"]["dat"] is True
    from core import tu_hoc
    assert "chat_luong" in tu_hoc.TRUC
    assert [tu_hoc.nhom_chat_luong({"cl_diem": x}) for x in (60, 90, 100)] == ["<80", "80-94", "95+"]
    assert tu_hoc.nhom_chat_luong({}) == ""


def test_muc_chat_luong_bao_cao_ngay(tmp_path):
    from core import bao_cao_ngay as bc
    bg = _dt.datetime(2026, 10, 9, 7, 0)
    p = kcl.duong_nhat_ky(str(tmp_path))
    os.makedirs(os.path.dirname(p))
    ts = bg.timestamp()
    with open(p, "w", encoding="utf-8") as f:
        for x in ({"ts": ts - 3600, "kenh": "K1", "ma_goi": "K1-0001", "dat": True, "diem": 96, "da_sua": 1},
                  {"ts": ts - 7200, "kenh": "K2", "ma_goi": "K2-0003", "dat": False, "diem": 40,
                   "loi": ["am_lang"], "lam_lai": 0},
                  {"ts": ts - 90000, "kenh": "K1", "ma_goi": "K1-0000", "dat": False, "diem": 10, "loi": ["cu"]}):
            f.write(json.dumps(x) + "\n")
    r = "\n".join(bc._muc_chat_luong(str(tmp_path), bg))  # noqa: SLF001
    assert "2 lần kiểm · 1 đạt (1 có tự sửa) · 1 chặn" in r and "am_lang x1" in r and "K2-0003" in r
    assert "K1 96" in r and "cu" not in r.replace("cửa", "")
    assert "chưa video nào" in bc._muc_chat_luong(str(tmp_path / "x"), bg)[0]  # noqa: SLF001


# ── FFmpeg thật trên media tổng hợp ───────────────────────────────────────────

@can_ff
def test_do_am_va_sua_do_to_roi_do_lai(tmp_path):
    """Tiếng nhỏ −40 LUFS → CHẶN có cách sửa → chuẩn hoá → đo lại ĐẠT, ghi 9-chat-luong.json + nhật ký."""
    goc, d = _luot(tmp_path, video_kw={"am": "sine=frequency=440:duration={g},volume=0.02"})
    t0 = time.time()
    kq = kcl.kiem_va_sua(goc, d, FF, gt=_gt(d), ma_goi="K1-0001", kenh="K1")
    assert time.time() - t0 < 60
    assert kq.dat, kq.ly_do()
    assert any("chuẩn hoá tiếng" in x for x in kq.da_sua)
    am = kq.do["am"]
    assert -16.5 <= am["lufs"] <= -11.5 and am["tp"] <= -1.0
    du = kcl.doc_ket_qua(d)
    assert du["dat"] is True and du["da_sua"] and du["do"]["am"]["lufs"] == am["lufs"]
    assert kcl.doc_nhat_ky(goc)[-1]["ma_goi"] == "K1-0001"
    assert "Video:" in subprocess.run([FF, "-hide_banner", "-i", os.path.join(d, "8-video.mp4")],
                                      capture_output=True, text=True).stderr, "hình còn nguyên sau khi sửa tiếng"


@can_ff
def test_lang_chet_giua_video_thi_chan_khong_sua(tmp_path):
    am = "aevalsrc='0.3*sin(2*PI*440*t)*(lt(t,3)+gt(t,9))':s=48000:d={g}"
    goc, d = _luot(tmp_path, video_kw={"am": am})
    kq = kcl.kiem_va_sua(goc, d, FF, gt=_gt(d))
    assert not kq.dat and "am_lang" in {x["ma"] for x in kq.chan}
    assert kq.do["am"]["im_ngoai_max"] > 5.0 and "lặng" in kq.ly_do()


@can_ff
def test_khung_dung_va_khung_den(tmp_path):
    goc, d = _luot(tmp_path, video_kw={"giay": 14.0, "vf": "trim=duration=8,tpad=stop_mode=clone:stop_duration=6"})
    do = kcl.do_luot(d, FF)
    # đọc gói tin hụt ~1–2 s đầu đoạn đứng (bộ mã còn tinh chỉnh khung) — ngưỡng chặn đã tính phần hụt ấy
    assert do["hinh"]["dong_bang_max"] >= 3.5, do["hinh"]
    assert "hinh_dong_bang" in {x["ma"] for x in kcl.danh_gia(do)}
    # khung đen 3 s ở giữa (ngoài chỗ nghỉ) — bắt; nằm trong chỗ nghỉ giữa phần — bỏ qua
    goc2, d2 = _luot(tmp_path / "b", video_kw={"giay": 12.0, "vf": "drawbox=c=black:t=fill:enable='between(t,5,8)'"})
    do2 = kcl.do_luot(d2, FF)
    assert do2["hinh"]["den_ngoai_ranh"], do2["hinh"]
    with open(os.path.join(d2, "8-phan.json"), "w", encoding="utf-8") as f:
        json.dump({"ranh": [{"a": 4.8, "b": 8.2, "a_moi": 4.8, "b_moi": 8.2}]}, f)
    assert kcl.do_luot(d2, FF)["hinh"]["den_ngoai_ranh"] == []


@can_ff
def test_phu_de_lech_deu_tu_doi_roi_do_lai(tmp_path):
    """Giọng: tiếng 1,5 s rồi lặng 1,5 s (khởi âm mỗi 3 s). Phụ đề trễ đều 1,2 s → dời → ĐẠT."""
    goc, d = _luot(tmp_path, video_kw={"giay": 30.0},
                   cues=[(k * 3.0 + 1.2, k * 3.0 + 2.6, "cau {0}".format(k)) for k in range(10)])
    _ff("-f", "lavfi", "-i", "aevalsrc='0.4*sin(2*PI*300*t)*lt(mod(t,3),1.5)':s=48000:d=30",
        "-c:a", "libmp3lame", os.path.join(d, "2-giong-doc.mp3"))
    kq = kcl.kiem_va_sua(goc, d, FF, gt=_gt(d))
    assert any("phụ đề" in x for x in kq.da_sua), kq.loi
    assert kq.do["phu_de"]["khop05"] >= 0.9 and kq.dat, kq.ly_do()
    assert kcl.doc_srt(os.path.join(d, "3-phu-de.srt"))[0][0] == pytest.approx(0.0, abs=0.06)


def _clip(duong, nguon, vf=""):
    _ff("-f", "lavfi", "-i", nguon + ":duration=8", *(["-vf", vf] if vf else []), "-c:v", "libx264",
        "-preset", "ultrafast", "-pix_fmt", "yuv420p", duong)


@can_ff
def test_clip_trung_va_tinh_mo_lai_khau_clip_moi_canh_mot_lan(tmp_path):
    goc, d = _luot(tmp_path, video_kw={"giay": 10.0})
    os.makedirs(os.path.join(d, "6-clip"))
    canh = [{"scene_id": i, "srt_start": "00:00:{0:02d},000".format(i)} for i in range(1, 6)]
    with open(os.path.join(d, "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump(canh, f)
    for i in (1, 2, 3):
        _clip(os.path.join(d, "6-clip", "{0}.mp4".format(i)), "testsrc2=size=160x90:rate=24", "hue=h={0}".format(i * 60))
    shutil.copy(os.path.join(d, "6-clip", "1.mp4"), os.path.join(d, "6-clip", "4.mp4"))      # trùng hệt
    _clip(os.path.join(d, "6-clip", "5.mp4"), "color=c=gray:size=160x90:rate=24")            # tĩnh cả 8 s
    luot = auto.moi_luot(goc, "K1", "0001", {})
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    auto.ghi_luot(luot)
    cl = kcl.do_clip(FF, d)
    assert cl["trung"] == [[1, 4]] and cl["tinh"] == [5]
    kq = kcl.kiem_va_sua(goc, d, FF, gt=_gt(d))
    assert not kq.dat and kq.lam_lai == [4, 5]
    assert not os.path.exists(os.path.join(d, "6-clip", "4.mp4")) and os.path.exists(os.path.join(d, "6-clip", "1.mp4"))
    assert not os.path.exists(os.path.join(d, "8-video.mp4")), "video dựng bị xoá để dựng lại"
    l2 = auto.doc_luot(d)
    assert l2.tt("clip").trang_thai == auto.CHO and l2.tt("dung").trang_thai == auto.CHO
    assert kcl.doc_ket_qua(d)["da_lam_lai"] == {"4": 1, "5": 1}
    # Lượt sau: cảnh 5 lại ra clip tĩnh, đã làm lại một lần → KHÔNG làm lại nữa, chặn chờ người
    _video(os.path.join(d, "8-video.mp4"), giay=10.0)
    _clip(os.path.join(d, "6-clip", "4.mp4"), "testsrc=size=160x90:rate=24")                  # bản mới, khác hẳn
    _clip(os.path.join(d, "6-clip", "5.mp4"), "color=c=gray:size=160x90:rate=24")            # lại tĩnh
    kq2 = kcl.kiem_va_sua(goc, d, FF, gt=_gt(d))
    assert not kq2.dat and kq2.lam_lai == [] and "cần người xem" in kq2.ly_do()
    assert os.path.exists(os.path.join(d, "8-video.mp4"))


@can_ff
def test_ban_giao_chan_khi_chat_luong_khong_dat(tmp_path):
    from core import ban_giao_dang, ke_hoach_dang
    goc, d = _luot(tmp_path, video_kw=None)
    (tmp_path / "goc" / "CHANNEL" / "K1").mkdir(parents=True)
    (tmp_path / "goc" / "CHANNEL" / "K1" / "kenh.yaml").write_text("ma: K1\nthu_muc_done: DONE/K1\n", encoding="utf-8")
    os.makedirs(os.path.join(d, "7-thumbnail"))
    open(os.path.join(d, "7-thumbnail", "CHON-a.jpg"), "wb").write(b"jpg")
    open(os.path.join(d, "8-video.mp4"), "wb").write(b"video")
    chan = kcl.KetQuaChatLuong(loi=[{"ma": "am_lang", "muc": "chan", "chi_tiet": "lặng 6s", "sua": ""}])
    with pytest.raises(RuntimeError, match="chất lượng chưa đạt — lặng 6s"):
        ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"),
                               kiem_cl=lambda *a, **k: chan)
    assert not os.path.exists(os.path.join(goc, "DONE", "K1", "K1-0001"))
    assert ke_hoach_dang.doc_bang(goc, "K1")[1] == []
    # đạt + mô tả đã được cổng sửa → dòng kế hoạch mang mô tả ĐÃ SỬA
    dat = kcl.KetQuaChatLuong(gt={"mo_ta": "mo ta da sua", "the": "a"})
    ma, moi = ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"),
                                     kiem_cl=lambda *a, **k: dat)
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    assert moi and hang[0][cot.index("Mô tả")] == "mo ta da sua"
