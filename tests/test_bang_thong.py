"""Bài kiểm `core/bang_thong.py` — suất tải kết quả về đĩa, liên tiến trình."""

from __future__ import annotations

import json
import os
import threading
import time

from core import bang_thong as bt
from core import khe


def _ghi_cai_dat(goc: str, cai: dict) -> None:
    duong = os.path.join(goc, "workspace", "cai-dat.json")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(cai, tep)


# ── Trần số suất ─────────────────────────────────────────────────────────


def test_tran_mac_dinh_la_6(tmp_path):
    assert bt.tran(str(tmp_path)) == bt.TRAN_MAC_DINH == 6


def test_tran_doc_cai_dat_va_kep(tmp_path):
    goc = str(tmp_path)
    _ghi_cai_dat(goc, {"tran_bang_thong": 3})
    assert bt.tran(goc) == 3
    _ghi_cai_dat(goc, {"tran_bang_thong": 999})
    assert bt.tran(goc) == 12
    _ghi_cai_dat(goc, {"tran_bang_thong": 0})
    assert bt.tran(goc) == 1
    _ghi_cai_dat(goc, {"tran_bang_thong": "khong-phai-so"})
    assert bt.tran(goc) == bt.TRAN_MAC_DINH


# ── Semaphore không vượt trần ────────────────────────────────────────────


def test_semaphore_khong_vuot_tran(tmp_path):
    goc = str(tmp_path)
    _ghi_cai_dat(goc, {"tran_bang_thong": 3})

    dinh_diem = [0]
    hien_tai = [0]
    khoa = threading.Lock()
    so_luong_luong = 10

    def _viec():
        with bt.giu(goc, cho_toi_da=8.0, nhip_kiem_giay=0.02) as _huy:
            with khoa:
                hien_tai[0] += 1
                dinh_diem[0] = max(dinh_diem[0], hien_tai[0])
            time.sleep(0.12)
            with khoa:
                hien_tai[0] -= 1

    luong = [threading.Thread(target=_viec) for _ in range(so_luong_luong)]
    for l in luong:
        l.start()
    for l in luong:
        l.join(timeout=15.0)

    assert dinh_diem[0] <= 3, "không bao giờ được vượt trần 3 suất cùng lúc"
    assert dinh_diem[0] >= 2, "bài kiểm phải THỰC SỰ ép được >1 suất cùng lúc, không chỉ chạy tuần tự"
    # Mọi tệp suất đều được dọn sạch sau khi xong.
    con_lai = os.listdir(bt.duong_thu_muc_tai(goc)) if os.path.isdir(bt.duong_thu_muc_tai(goc)) else []
    assert con_lai == []


# ── Tạm dừng khi khe "nang" đang giữ việc tai_len ───────────────────────────


def test_tam_dung_khi_dang_tai_len(tmp_path):
    goc = str(tmp_path)
    assert bt.dang_tam_dung(goc) is False

    with khe.giu(goc, "nang", "tai_len", kenh="TL1") as _huy:
        assert bt.dang_tam_dung(goc) is True
        # Có suất trống (trần mặc định 6) nhưng vẫn KHÔNG được cấp vì đang tạm dừng.
        import pytest

        with pytest.raises(khe.KheHetGio):
            with bt.giu(goc, cho_toi_da=0.3, nhip_kiem_giay=0.05):
                pass

    # Khe "nang" đã nhả -> hết tạm dừng -> cấp suất bình thường.
    assert bt.dang_tam_dung(goc) is False
    with bt.giu(goc, cho_toi_da=2.0) as _huy2:
        pass


def test_khong_tam_dung_khi_nang_giu_viec_khac(tmp_path):
    goc = str(tmp_path)
    with khe.giu(goc, "nang", "dung", kenh="TL1") as _huy:
        assert bt.dang_tam_dung(goc) is False
        with bt.giu(goc, cho_toi_da=2.0) as _huy2:
            pass
