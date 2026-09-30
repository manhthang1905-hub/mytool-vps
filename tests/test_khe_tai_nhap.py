"""Khe "nang" TÁI NHẬP (vá sự cố tự khoá chết 29/09/2026 18:36→19:53).

PID 6668 giữ `.khoa-may` kiểu CŨ `{pid, bat_dau}` cả lượt, rồi tới khâu phụ đề
xin khe "nang" → chờ CHÍNH NÓ vô hạn, kéo TL2/TL3 đứng theo."""
import json
import os
import threading

import pytest

from core import khe


def _goc(tmp_path):
    return str(tmp_path)


def _ghi_khoa_cu(goc, pid):
    p = khe.duong_khoa_nang(goc)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as t:
        json.dump({"pid": pid, "bat_dau": 1790680000.0}, t)
    return p


def test_khoa_cu_cua_chinh_minh_thi_cho_qua_va_khong_xoa(tmp_path):
    goc = _goc(tmp_path)
    p = _ghi_khoa_cu(goc, os.getpid())
    with khe.giu(goc, khe.LOP_NANG, viec="phu_de", cho_toi_da=2, nhip_kiem_giay=0.05):
        pass
    assert os.path.isfile(p), "nhả khe tái nhập không được xoá khoá của lượt ngoài"
    ph = khe.thu_giu(goc, khe.LOP_NANG, viec="nen")
    assert ph is not None
    ph.nha()
    assert os.path.isfile(p)


def test_long_nhau_cung_luong_khong_tu_khoa(tmp_path):
    goc = _goc(tmp_path)
    with khe.giu(goc, khe.LOP_NANG, viec="dung", cho_toi_da=2, nhip_kiem_giay=0.05):
        with khe.giu(goc, khe.LOP_NANG, viec="qa_chep", cho_toi_da=2, nhip_kiem_giay=0.05):
            pass
        assert os.path.isfile(khe.duong_khoa_nang(goc)), "lớp trong nhả mất khoá lớp ngoài"
    assert not os.path.isfile(khe.duong_khoa_nang(goc))


def test_luong_khac_cung_tien_trinh_van_phai_cho(tmp_path):
    goc = _goc(tmp_path)
    loi = []
    with khe.giu(goc, khe.LOP_NANG, viec="dung", cho_toi_da=2, nhip_kiem_giay=0.05):
        def khac():
            try:
                with khe.giu(goc, khe.LOP_NANG, viec="giong_doc", cho_toi_da=0.3,
                             nhip_kiem_giay=0.05):
                    pass
            except khe.KheHetGio as e:
                loi.append(e)
        t = threading.Thread(target=khac)
        t.start()
        t.join(5)
    assert loi, "luồng khác cùng tiến trình không được lọt vào khe độc quyền"


def test_khoa_cu_cua_tien_trinh_khac_con_song_thi_cho_co_tran(tmp_path):
    goc = _goc(tmp_path)
    import subprocess
    import sys
    con = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        _ghi_khoa_cu(goc, con.pid)
        with pytest.raises(khe.KheHetGio):
            with khe.giu(goc, khe.LOP_NANG, viec="phu_de", cho_toi_da=0.3, nhip_kiem_giay=0.05):
                pass
    finally:
        con.kill()


def test_mo_ta_nguoi_giu_doc_duoc_dinh_dang_cu():
    assert khe.mo_ta_nguoi_giu({"pid": 6668, "bat_dau": 1790680000.0}).startswith(
        "PID 6668 (khoá cả lượt kiểu cũ")
    m = khe.mo_ta_nguoi_giu({"pid": 4232, "nguon": "khe", "viec": "phu_de", "kenh": "TL3-T7",
                             "bat_dau": 1790680000.0})
    assert "phu_de TL3-T7" in m and m.startswith("PID 4232")
    assert khe.mo_ta_nguoi_giu(None) == "không ai"
