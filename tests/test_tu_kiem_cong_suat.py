"""Tự kiểm thông lượng (`core/tu_kiem.kiem_cong_suat`, 20/10/2026): video dựng xong hôm qua, trung vị giờ/video so 7
ngày trước, khe lỡ từng kênh. Dữ liệu giả trong `tmp_path` (mã kênh/video giả)."""

from __future__ import annotations

import datetime as _dt
import json
import os

from core import tu_kiem

BAY = _dt.datetime(2026, 10, 20, 10, 0)


def _luot(goc, kenh, ma, tao, gio_video, clip_phut=10.0):
    xong = tao + gio_video * 3600
    du = {"ma_kenh": kenh, "ma_luot": ma, "tao_luc": tao, "khau": {
        "clip": {"trang_thai": "xong", "bat_dau": tao, "ket_thuc": tao + clip_phut * 60},
        "dung": {"trang_thai": "xong", "bat_dau": xong - 600, "ket_thuc": xong}}}
    p = os.path.join(goc, "PROJECTS", "AUTO", kenh, ma, "trang-thai.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as tep:
        json.dump(du, tep)


def _so_video(goc, muc):
    p = os.path.join(goc, "vm", "logs", "so-video-id.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as tep:
        json.dump(muc, tep)


def _gia(monkeypatch):
    monkeypatch.setattr(tu_kiem, "_kenh_tu_chay", lambda g, k: True)
    monkeypatch.setattr(tu_kiem, "_dang_o_may_khac", lambda g, k: False)
    monkeypatch.setattr(tu_kiem, "_khe_kenh", lambda g, k: ["20:00"])
    monkeypatch.setattr(tu_kiem, "_chu_ky_kenh", lambda g, k: 1)


def _K(goc, kenh_ds):
    return tu_kiem.BoiCanh(goc, bay=BAY, thu=True, so={"muc": {}, "bao": {}}, kenh_ds=kenh_ds)


def test_dat_khi_du_khe_va_khong_cham(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _gia(monkeypatch)
    hom_qua = _dt.datetime(2026, 10, 19, 1, 0).timestamp()
    for i in range(3):
        _luot(goc, "KA", "000{0}".format(i), hom_qua - 86400 * (i + 2), 6.0)
    _luot(goc, "KA", "0009", hom_qua, 7.0)
    _so_video(goc, {"KA/KA-1": {"video_id": "vid_gia_1", "lich": "18/10/2026 20:00"},
                    "KA/KA-2": {"video_id": "vid_gia_2", "lich": "19/10/2026 20:00"}})
    m = tu_kiem.kiem_cong_suat(_K(goc, ["KA"]))[0]
    assert m["tt"] == tu_kiem.DAT and m["so_lieu"]["so_video"] == 1
    assert m["so_lieu"]["khau_phut"]["clip"] == 10.0


def test_hong_khi_lo_khe_hoac_cham_gap_doi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _gia(monkeypatch)
    hom_qua = _dt.datetime(2026, 10, 19, 1, 0).timestamp()
    for i in range(3):
        _luot(goc, "KA", "000{0}".format(i), hom_qua - 86400 * (i + 2), 5.0)
    _luot(goc, "KA", "0009", hom_qua - 10 * 3600, 30.0, clip_phut=900)      # 30 giờ/video > 2 × 5
    _so_video(goc, {"KA/KA-1": {"video_id": "vid_gia_1", "lich": "18/10/2026 20:00"},
                    "KB/KB-1": {"video_id": "vid_gia_3", "lich": "17/10/2026 20:00"}})
    m = tu_kiem.kiem_cong_suat(_K(goc, ["KA", "KB", "KMOI"]))[0]
    assert m["tt"] == tu_kiem.HONG
    assert m["so_lieu"]["lo_khe"] == {"KA": 1, "KB": 1} and m["so_lieu"]["chua_len"] == ["KMOI"]
    assert "CHẬM" in m["bang_chung"] and m["bang_chung"].startswith("lỡ khe: KA ×1, KB ×1")
    assert tu_kiem.phan_loai(_K(goc, []), m, {})["ten"] == "thông lượng sản xuất"
