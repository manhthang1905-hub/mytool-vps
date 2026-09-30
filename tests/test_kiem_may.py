# -*- coding: utf-8 -*-
"""`core/kiem_may.py` — bảng kiểm máy VPS OK/THIẾU (Việc 5.1).

Không gọi mạng thật: `kiem_tram`/`kiem_agent` chỉ được gọi với `tmp_path` giả
lập cổng KHÔNG CÓ AI NGHE (loopback, cổng cao ít dùng) — kết nối chắc chắn bị
từ chối ngay, không treo, không cần server thật.
"""

from __future__ import annotations

import json
import os

from core import kiem_may


def test_kiem_python_ok_tren_may_dang_chay_test():
    m = kiem_may.kiem_python()
    assert m.ok is True  # chính máy chạy pytest đã qua yêu cầu 3.9+/64-bit


def test_kiem_thu_vien_tra_mot_dong_moi_thu_vien():
    ket = kiem_may.kiem_thu_vien()
    ten = [m.ten for m in ket]
    assert any("websocket-client" in t for t in ten)
    assert len(ket) == len(kiem_may.THU_VIEN_CAN)


def test_kiem_vps_json_thieu_tep():
    m = kiem_may.kiem_vps_json(goc="/duong/khong/co/that")
    assert m.ok is False


def test_kiem_vps_json_hop_le(tmp_path):
    (tmp_path / "vm").mkdir()
    (tmp_path / "vps.json").write_text(json.dumps({"vm_dir": "vm"}), encoding="utf-8")
    m = kiem_may.kiem_vps_json(goc=str(tmp_path))
    assert m.ok is True


def test_kiem_vps_json_vm_dir_khong_ton_tai(tmp_path):
    (tmp_path / "vps.json").write_text(json.dumps({"vm_dir": "vm-khong-co"}), encoding="utf-8")
    m = kiem_may.kiem_vps_json(goc=str(tmp_path))
    assert m.ok is False


def test_kiem_vps_json_doc_loi_khong_sap(tmp_path):
    (tmp_path / "vps.json").write_text("{ khong phai json", encoding="utf-8")
    m = kiem_may.kiem_vps_json(goc=str(tmp_path))
    assert m.ok is False


def test_kiem_whisper_thieu(tmp_path):
    m = kiem_may.kiem_whisper(goc=str(tmp_path))
    assert m.ok is False


def test_kiem_whisper_co(tmp_path):
    duong = tmp_path / "models" / "faster-whisper-small"
    duong.mkdir(parents=True)
    (duong / "config.json").write_text("{}", encoding="utf-8")
    m = kiem_may.kiem_whisper(goc=str(tmp_path))
    assert m.ok is True


def test_kiem_tram_cong_khong_ai_nghe():
    m = kiem_may.kiem_tram(cong=18765)
    assert m.ok is False


def test_kiem_agent_cong_khong_ai_nghe():
    m = kiem_may.kiem_agent(cong=18767, timeout=0.3)
    assert m.ok is False


def test_kiem_lich_doc_qua_core_lich_tu_chay(tmp_path, monkeypatch):
    """`core.lich_tu_chay.trang_thai` hỏi `schtasks` THẬT theo TÊN việc (không
    theo `goc`) — máy chạy bài kiểm này có thể đã có/chưa có ba việc đó thật
    sự. Để không phụ thuộc trạng thái máy, giả luôn hàm `trang_thai`."""
    from core import lich_tu_chay

    def _gia(goc, *, chay_lenh=None, ten_viec=lich_tu_chay.TEN_VIEC):
        return {"da_dang_ky": ten_viec == lich_tu_chay.TEN_VIEC,
                "gio": "02:00" if ten_viec == lich_tu_chay.TEN_VIEC else "",
                "lan_chay_cuoi": "", "ket_qua_cuoi": ""}

    monkeypatch.setattr(lich_tu_chay, "trang_thai", _gia)
    ket = kiem_may.kiem_lich(goc=str(tmp_path))
    assert len(ket) == 3
    assert ket[0].ok is True  # ShopAPI-TuChay
    assert ket[1].ok is False and ket[2].ok is False


def test_in_bang_tra_true_khi_het_ok(capsys):
    ket = [kiem_may.MucKiem("a", True), kiem_may.MucKiem("b", True)]
    dat = kiem_may.in_bang(ket)
    assert dat is True
    ra = capsys.readouterr().out
    assert "Tất cả" in ra


def test_in_bang_tra_false_khi_co_thieu(capsys):
    ket = [kiem_may.MucKiem("a", True), kiem_may.MucKiem("b", False, "vi du")]
    dat = kiem_may.in_bang(ket)
    assert dat is False
    ra = capsys.readouterr().out
    assert "THIẾU" in ra
    assert "vi du" in ra


def test_main_tra_ma_khac_khong_khi_thieu(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kiem_may, "GOC", str(tmp_path))
    ma = kiem_may.main([])
    assert ma != 0
    ra = capsys.readouterr().out
    assert "THIẾU" in ra


def test_main_khong_day_du_bo_qua_tram_agent(tmp_path, monkeypatch):
    goi = {"tram": 0, "agent": 0}
    monkeypatch.setattr(kiem_may, "kiem_tram", lambda *a, **k: goi.__setitem__("tram", goi["tram"] + 1))
    monkeypatch.setattr(kiem_may, "kiem_agent", lambda *a, **k: goi.__setitem__("agent", goi["agent"] + 1))
    kiem_may.kiem_tat_ca(goc=str(tmp_path), day_du=False)
    assert goi == {"tram": 0, "agent": 0}


def test_kiem_tat_ca_day_du_goi_tram_agent(tmp_path, monkeypatch):
    goi = {"tram": 0, "agent": 0}
    monkeypatch.setattr(kiem_may, "kiem_tram", lambda *a, **k: goi.__setitem__("tram", goi["tram"] + 1) or kiem_may.MucKiem("t", False))
    monkeypatch.setattr(kiem_may, "kiem_agent", lambda *a, **k: goi.__setitem__("agent", goi["agent"] + 1) or kiem_may.MucKiem("a", False))
    kiem_may.kiem_tat_ca(goc=str(tmp_path), day_du=True)
    assert goi == {"tram": 1, "agent": 1}
