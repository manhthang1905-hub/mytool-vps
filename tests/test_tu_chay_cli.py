"""Nhãn dòng kết quả + mã thoát của CLI gốc `tu_chay.py` (`python tu_chay.py
--tat-ca` / `--kenh`) — phần V2-tối-giản (chẩn đoán 26/09/2026).

Hai hàm `_nhan_ket_qua`/`_ma_thoat` được tách thuần tuý (không gọi mạng, không
đọc `config.json`/`secrets.json`) để kiểm được ở đây, đúng luật 3 của CLAUDE.md.

Nạp `tu_chay.py` Ở GỐC KHO (không phải `core/tu_chay.py`) qua `importlib`, vì
trùng tên module với gói `core.tu_chay` — `import tu_chay` trần sẽ mơ hồ tuỳ
`sys.path`.
"""

from __future__ import annotations

import importlib.util
import os


def _nap_tu_chay_cli():
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    duong = os.path.join(goc, "tu_chay.py")
    spec = importlib.util.spec_from_file_location("_tu_chay_cli_goc_test", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_cli = _nap_tu_chay_cli()


def test_nhan_cho_nguoi_uu_tien_hon_ok_va_loi():
    assert _cli._nhan_ket_qua({"cho_nguoi": True, "ok": True}) == "[CHỜ NGƯỜI] "
    assert _cli._nhan_ket_qua({"cho_nguoi": True, "ok": False}) == "[CHỜ NGƯỜI] "


def test_nhan_ok_va_loi_giu_nguyen_khi_khong_cho_nguoi():
    assert _cli._nhan_ket_qua({"cho_nguoi": False, "ok": True}) == "[OK]  "
    assert _cli._nhan_ket_qua({"cho_nguoi": False, "ok": False}) == "[LỖI] "


def test_ma_thoat_co_loi_la_1_du_co_kenh_cho_nguoi():
    bao_cao = {"co_loi": True,
              "ket_qua": [{"ok": False, "cho_nguoi": False}, {"ok": True, "cho_nguoi": True}]}
    assert _cli._ma_thoat(bao_cao) == 1


def test_ma_thoat_2_khi_tat_ca_kenh_deu_cho_nguoi():
    bao_cao = {"co_loi": False,
              "ket_qua": [{"ok": True, "cho_nguoi": True}, {"ok": True, "cho_nguoi": True}]}
    assert _cli._ma_thoat(bao_cao) == 2


def test_ma_thoat_0_khi_it_nhat_mot_kenh_chay_binh_thuong():
    bao_cao = {"co_loi": False,
              "ket_qua": [{"ok": True, "cho_nguoi": True}, {"ok": True, "cho_nguoi": False}]}
    assert _cli._ma_thoat(bao_cao) == 0


def test_ma_thoat_0_khi_khong_co_kenh_nao_de_chay():
    assert _cli._ma_thoat({"co_loi": False, "ket_qua": []}) == 0
