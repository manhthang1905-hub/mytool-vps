# -*- coding: utf-8 -*-
"""13/10/2026 — kênh tự chạy KHÔNG khai `thu_muc_done` thì mặc định `DONE/<mã>`.

Ca gốc: TL4-T7 bật `tu_chay: true` 12/10 mà kenh.yaml thiếu khoá → lượt 0001 dựng xong
`8-video.mp4` nhưng không bàn giao, nhặt lại 3 lần rồi L3 bỏ lượt — video không lên sóng.
Khai TƯỜNG MINH `thu_muc_done: ""` vẫn là ý chủ (không bàn giao) — giữ nguyên.
"""
import os

from core.kenh import doc_kenh


def _ghi(goc, ma, than):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write(than)


def test_tu_chay_khong_khai_thi_mac_dinh_done_ma_kenh(tmp_path):
    goc = str(tmp_path)
    _ghi(goc, "K1", 'ma: "K1"\ntu_chay: true\n')
    k = doc_kenh(goc, "K1")
    assert os.path.normcase(k.thu_muc_done) == os.path.normcase(os.path.join(goc, "DONE", "K1"))


def test_khai_tuong_minh_rong_thi_giu_rong(tmp_path):
    goc = str(tmp_path)
    _ghi(goc, "K1", 'ma: "K1"\ntu_chay: true\nthu_muc_done: ""\n')
    assert doc_kenh(goc, "K1").thu_muc_done == ""


def test_khong_tu_chay_thi_khong_tu_dien(tmp_path):
    goc = str(tmp_path)
    _ghi(goc, "K1", 'ma: "K1"\ntu_chay: false\n')
    assert doc_kenh(goc, "K1").thu_muc_done == ""


def test_khai_san_thi_dung_dung_cai_da_khai(tmp_path):
    goc = str(tmp_path)
    _ghi(goc, "K1", 'ma: "K1"\ntu_chay: true\nthu_muc_done: "DONE/khac"\n')
    k = doc_kenh(goc, "K1")
    assert os.path.normcase(k.thu_muc_done) == os.path.normcase(os.path.join(goc, "DONE", "khac"))
