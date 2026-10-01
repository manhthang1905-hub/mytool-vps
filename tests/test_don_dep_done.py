"""Luật dọn gói DONE (`core/don_dep.ung_vien_done`) + van ổ 10 GB (01/10/2026). Chỉ `tmp_path`."""

from __future__ import annotations

import datetime
import json
import os

from core import cong_suat, don_dep, don_dep_mo_rong, ke_hoach_dang
from core.auto import MA_KHAU, TEP_TRANG_THAI, XONG, duong_luot

KENH, MA = "K1", "K1-0001"
BAY_GIO = datetime.datetime(2026, 10, 5, 12, 0)


def _ghi(p, chu="x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as t:
        t.write(chu)


def _dung(goc, so=None, ghi_chu=""):
    done = os.path.join(goc, "DONE", KENH)
    _ghi(os.path.join(goc, "CHANNEL", KENH, "kenh.yaml"),
         "ma: K1\ntu_don: true\nthu_muc_done: {0}\n".format(done.replace("\\", "/")))
    g = os.path.join(done, MA)
    for t in ("8-video.mp4", "3-phu-de.srt", "CHON-thumb.jpg", "1-binh-luan.txt", "qa.json"):
        _ghi(os.path.join(g, t), "0" * 100)
    luot = duong_luot(goc, KENH, "0001")
    _ghi(os.path.join(luot, TEP_TRANG_THAI), json.dumps({"ma_kenh": KENH, "ma_luot": "0001", "khau": {
        m: {"ma": m, "trang_thai": XONG, "so_lan": 1, "loi": "", "bat_dau": 0.0, "ket_thuc": 0.0,
            "ghi_chu": {}} for m in MA_KHAU}}))
    _ghi(os.path.join(luot, "5-anh", "a.png"))
    _ghi(os.path.join(luot, "3-phu-de.srt"))
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), json.dumps({"K1/" + MA: so} if so else {}))
    if ghi_chu:
        cot = list(ke_hoach_dang.COT)
        d = dict.fromkeys(cot, "")
        d.update({"Mã gói": MA, "Ghi chú": ghi_chu})
        ke_hoach_dang.luu_bang(goc, KENH, [[d[c] for c in cot]], cot)
    return g, luot


def test_da_len_youtube_xoa_ngay_ca_hai_phia_giu_chu(tmp_path):
    """Chủ kênh 01/10: lên YouTube xong (kể cả lịch còn ở tương lai) là xoá ngay; chỉ giữ tệp chữ."""
    goc = str(tmp_path)
    g, luot = _dung(goc, {"video_id": "v1", "trang_thai": "da-len-lich", "lich": "09/10/2026 05:00"})
    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO)
    for t in ("8-video.mp4", "CHON-thumb.jpg"):
        assert not os.path.exists(os.path.join(g, t))
    assert not os.path.exists(os.path.join(luot, "5-anh"))
    for t in ("3-phu-de.srt", "1-binh-luan.txt", "qa.json"):
        assert os.path.isfile(os.path.join(g, t))
    assert os.path.isfile(os.path.join(luot, "3-phu-de.srt"))


def test_chua_len_hoac_dang_tai_thi_giu(tmp_path):
    goc = str(tmp_path)
    _dung(goc, {"video_id": "", "trang_thai": "dang-tai", "lich": "01/09/2026 12:00"})
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO) == []
    _dung(goc, {"video_id": "v1", "trang_thai": "xac-nhan", "lich": "01/09/2026 12:00"})
    _ghi(os.path.join(goc, "vm", "logs", "dang-dodang.json"), json.dumps({"kenh": KENH, "ma": MA}))
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO) == []


def test_goi_bo_xoa_ngay(tmp_path):
    goc = str(tmp_path)
    g, _ = _dung(goc, ghi_chu="Bỏ, trùng nội dung")
    u = don_dep.ung_vien_done(goc, KENH, bay_gio=datetime.datetime.now() + datetime.timedelta(seconds=1))
    assert [x["ma_goi"] for x in u] == [MA]


def test_van_o_10gb_va_dieu_phoi(tmp_path):
    from core import dieu_phoi

    assert don_dep_mo_rong.van_o("x", 9.5)["duoc_mo_moi"] is False
    assert don_dep_mo_rong.van_o("x", 10.5)["duoc_mo_moi"] is True
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vps.json"), "{}")
    _ghi(os.path.join(goc, "workspace", "cai-dat.json"), json.dumps({"dieu_phoi": True, "lan_api": 2}))
    _ghi(os.path.join(goc, "CHANNEL", "K2", "kenh.yaml"),
         'ma: "K2"\nngon_ngu: "ja"\nengine: "veo3"\nphut_muc_tieu: 10\ntu_chay: true\ntu_duyet: true\n'
         'ngan_sach_ngay: 5000000\nnhip_dang: "12:00, 20:00"\nvideo_toi_da_ngay: 4\n')
    sinh = []
    kw = dict(bay_gio=datetime.datetime(2026, 9, 29, 14, 0), ram=10.0,
              sinh=lambda g, ma: sinh.append(ma) or 1, log=lambda d: None)
    ra = dieu_phoi.nhip(goc, dia_gb=8.0, **kw)
    assert sinh == [] and "ổ đĩa" in ra["chan"]
    dieu_phoi.nhip(goc, dia_gb=30.0, **kw)
    assert sinh == ["K2"]


def test_tran_o_dia_vao_cong_suat(tmp_path, monkeypatch):
    assert cong_suat.tran_theo_o_dia(str(tmp_path), con_trong_gb=30.0)["tran_video_ngay"] is None
    monkeypatch.setattr(cong_suat, "tran_theo_o_dia",
                        lambda goc, so_kenh=None: {"tran_video_ngay": 0.5, "gb_moi_video": 1.1})
    cs = cong_suat.cong_suat_hien_tai(str(tmp_path))
    from core.giam_doc import tong
    assert cs["nut_that"] == "ổ đĩa" and tong.tran_may(cs) == 0.5
