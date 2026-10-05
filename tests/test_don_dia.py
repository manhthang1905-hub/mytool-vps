"""`core/don_dia.py` — nhịp dọn đĩa của gác tổng + xoay log. Chỉ `tmp_path`, không đụng dữ liệu thật."""

from __future__ import annotations

import datetime
import gzip
import json
import os

from core import don_dep, don_dia
from core.auto import MA_KHAU, TEP_TRANG_THAI, XONG, duong_luot

KENH, MA = "K1", "K1-0001"


def _ghi(p, chu="x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as t:
        t.write(chu)


def _dung(goc, so, tu_don=True):
    """Kênh K1: một gói DONE + lượt PROJECTS đã xong, sổ video-id = `so`."""
    done = os.path.join(goc, "DONE", KENH)
    _ghi(os.path.join(goc, "CHANNEL", KENH, "kenh.yaml"),
         "ma: K1\ntu_don: {0}\nthu_muc_done: {1}\n".format(
             "true" if tu_don else "false", done.replace("\\", "/")))
    g = os.path.join(done, MA)
    for t in ("8-video.mp4", "3-phu-de.srt", "1-binh-luan.txt"):
        _ghi(os.path.join(g, t), "0" * 1000)
    luot = duong_luot(goc, KENH, "0001")
    _ghi(os.path.join(luot, TEP_TRANG_THAI), json.dumps({"ma_kenh": KENH, "ma_luot": "0001", "khau": {
        m: {"ma": m, "trang_thai": XONG, "so_lan": 1, "loi": "", "bat_dau": 0.0, "ket_thuc": 0.0,
            "ghi_chu": {}} for m in MA_KHAU}}))
    for t in ("5-anh/a.png", "6-clip/c.mp4", "8-nhac-nen.m4a", "2-giong-doc.mp3"):
        _ghi(os.path.join(luot, t), "0" * 1000)
    for t in ("3-phu-de.srt", "8-phu-de.srt", "4-canh.json", "1-kich-ban.txt", "7-thumbnail/CHON-thumb_001.jpg"):
        _ghi(os.path.join(luot, t))
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), json.dumps({"K1/" + MA: so} if so else {}))
    return g, luot


DA_LEN = {"video_id": "v1", "trang_thai": "xac-nhan", "lich": "01/10/2026 05:00"}


def test_thu_chi_tinh_khong_xoa(tmp_path):
    goc = str(tmp_path)
    g, luot = _dung(goc, DA_LEN)
    kq = don_dia.chay(goc, thu=True, con_trong_gb_fn=lambda _g: 50.0)
    assert kq["video"][KENH]["so_goi"] == 1 and kq["video_bytes"] >= 5000
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))
    assert os.path.isfile(os.path.join(luot, "8-nhac-nen.m4a"))
    assert "sẽ giải phóng" in don_dia.tom_tat(kq)


def test_that_xoa_nang_giu_chu_va_bia_da_chon(tmp_path):
    goc = str(tmp_path)
    g, luot = _dung(goc, DA_LEN)
    kq = don_dia.chay(goc, thu=False, con_trong_gb_fn=lambda _g: 50.0)
    assert kq["video"][KENH]["so_goi"] == 1
    assert not os.path.exists(os.path.join(g, "8-video.mp4"))
    for t in ("5-anh", "6-clip", "8-nhac-nen.m4a", "2-giong-doc.mp3"):
        assert not os.path.exists(os.path.join(luot, t)), t
    # Người đọc mãi mãi: máy trả lời bình luận (DONE/<k>/<ma>/3-phu-de.srt), tự học (srt/json/kịch bản).
    assert os.path.isfile(os.path.join(g, "3-phu-de.srt"))
    for t in ("3-phu-de.srt", "8-phu-de.srt", "4-canh.json", "1-kich-ban.txt",
              "7-thumbnail/CHON-thumb_001.jpg", TEP_TRANG_THAI):
        assert os.path.isfile(os.path.join(luot, t)), t


def test_chua_xac_nhan_len_youtube_thi_khong_xoa(tmp_path):
    goc = str(tmp_path)
    g, luot = _dung(goc, {"video_id": "", "trang_thai": "dang-tai", "lich": "01/10/2026 05:00"})
    don_dia.chay(goc, thu=False, con_trong_gb_fn=lambda _g: 50.0)
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))
    assert os.path.isfile(os.path.join(luot, "6-clip", "c.mp4"))


def test_kenh_tat_tu_don_khong_dung(tmp_path):
    goc = str(tmp_path)
    g, _ = _dung(goc, DA_LEN, tu_don=False)
    kq = don_dia.chay(goc, thu=False, con_trong_gb_fn=lambda _g: 50.0)
    assert kq["video"][KENH]["chay"] is False
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))


def test_ngay_giu_sau_cong_khai(tmp_path, monkeypatch):
    """`NGAY_SAU_CONG_KHAI > 0`: chưa đủ N ngày sau giờ công khai thì giữ, đủ thì xoá."""
    goc = str(tmp_path)
    _dung(goc, DA_LEN)
    monkeypatch.setattr(don_dep, "NGAY_SAU_CONG_KHAI", 3)
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=datetime.datetime(2026, 10, 3, 5, 0)) == []
    assert len(don_dep.ung_vien_done(goc, KENH, bay_gio=datetime.datetime(2026, 10, 4, 5, 1))) == 1


def test_van_o_dong_khi_duoi_nguong(tmp_path):
    goc = str(tmp_path)
    kq = don_dia.chay(goc, thu=True, danh_sach_kenh=[], con_trong_gb_fn=lambda _g: 4.0)
    assert kq["van_o"]["duoc_mo_moi"] is False
    assert "VAN Ổ ĐANG ĐÓNG" in don_dia.tom_tat(kq)


# ── Xoay log ─────────────────────────────────────────────────────────────────


def test_xoay_log_qua_co_giu_k_ban_nen(tmp_path):
    goc = str(tmp_path)
    p = os.path.join(goc, "workspace", "a.log")
    for lan in range(5):
        _ghi(p, "dong {0}\n".format(lan) * 50)
        ds = don_dia.ung_vien_xoay_log(goc, gioi_han=10)
        assert [u["duong"] for u in ds] == [p]
        assert don_dia.xoay_log(p, giu=3) is True
        assert not os.path.exists(p)
    with gzip.open(p + ".1.gz", "rt", encoding="utf-8") as f:
        assert f.read().startswith("dong 4")
    assert os.path.isfile(p + ".3.gz") and not os.path.exists(p + ".4.gz")


def test_log_nho_jsonl_projects_leveldb_khong_dung(tmp_path):
    goc = str(tmp_path)
    to = "x" * 100
    _ghi(os.path.join(goc, "nho.log"), "x")
    _ghi(os.path.join(goc, "CHANNEL", "K1", "giam-doc", "bai-hoc.jsonl"), to)
    _ghi(os.path.join(goc, "PROJECTS", "AUTO", "K1", "0001", "x.log"), to)
    _ghi(os.path.join(goc, ".git", "x.log"), to)
    _ghi(os.path.join(goc, "vm", "ldb", "CURRENT"), "MANIFEST-1")
    _ghi(os.path.join(goc, "vm", "ldb", "000003.log"), to)
    assert don_dia.ung_vien_xoay_log(goc, gioi_han=10) == []


def test_tep_tam_rot_lai_duoc_nen_luot_sau(tmp_path):
    goc = str(tmp_path)
    p = os.path.join(goc, "b.log")
    _ghi(p + ".dang-xoay", "cu\n")
    ds = don_dia.ung_vien_xoay_log(goc)
    assert [u["duong"] for u in ds] == [p + ".dang-xoay"]
    assert don_dia.xoay_log(ds[0]["duong"]) is True
    assert os.path.isfile(p + ".1.gz") and not os.path.exists(p + ".dang-xoay")


def test_xoay_log_tep_bi_giu_thi_bo_qua(tmp_path, monkeypatch):
    p = os.path.join(str(tmp_path), "c.log")
    _ghi(p, "x" * 100)

    def _loi(*_a, **_k):
        raise PermissionError("đang mở")

    monkeypatch.setattr(don_dia.os, "replace", _loi)
    assert don_dia.xoay_log(p) is False
    assert os.path.isfile(p)


# ── Nhịp gác tổng ────────────────────────────────────────────────────────────


def test_nhip_moi_3_gio_mot_lan(tmp_path, monkeypatch):
    goc = str(tmp_path)
    goi = []
    monkeypatch.setattr(don_dia, "chay", lambda g, thu=True, **_k: goi.append(thu) or {"thu": thu})
    assert don_dia.nhip(goc, bay_gio=1_000_000.0) == {"thu": False}
    assert don_dia.nhip(goc, bay_gio=1_000_000.0 + 2 * 3600) is None
    assert don_dia.nhip(goc, bay_gio=1_000_000.0 + 3 * 3600 + 1) == {"thu": False}
    assert goi == [False, False]


def test_dong_lenh_khong_co_co_thi_chi_in_huong_dan(capsys):
    assert don_dia._main([]) == 0  # noqa: SLF001
    assert "--thu" in capsys.readouterr().out
