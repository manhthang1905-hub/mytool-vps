"""Bốn việc não học + kỹ năng phải được bộ cài đặt cho máy mới (16/10/2026)."""

from __future__ import annotations

import os

from core import lich_tu_chay as l


def _goc(tmp_path, thieu=()):
    for _ten, _lich, lenh in l.VIEC_NAO_MO_RONG:
        mod = lenh.split()[0]
        if mod in thieu:
            continue
        p = os.path.join(str(tmp_path), *mod.split(".")) + ".py"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").close()
    return str(tmp_path)


def test_dat_du_bon_viec_dung_lenh(tmp_path):
    goi = []
    ok, chu = l.dang_ky_nao_mo_rong(_goc(tmp_path), chay_lenh=lambda c: (goi.append(c), (0, ""))[1])
    assert ok and len(goi) == 4
    ten = [c[c.index("/TN") + 1] for c in goi]
    assert ten == ["ShopAPI-KyNang", "ShopAPI-NaoBoPhan", "ShopAPI-NaoBoPhan-Ngu", "ShopAPI-PhongThiNghiem"]
    for c in goi:
        assert c[0] == "schtasks" and c[-1] == "/F" and "/RU" not in c
        tr = c[c.index("/TR") + 1]
        assert os.path.abspath(str(tmp_path)) in tr and "-X utf8 -m core." in tr
    assert "core.ky_nang tu-kich-hoat" in goi[0][goi[0].index("/TR") + 1]
    assert "4/4" in chu


def test_thieu_module_bo_qua_viec_do(tmp_path):
    goi = []
    ok, chu = l.dang_ky_nao_mo_rong(_goc(tmp_path, thieu=("core.phong_thi_nghiem",)),
                                    chay_lenh=lambda c: (goi.append(c), (0, ""))[1])
    assert not ok and len(goi) == 3 and "phong_thi_nghiem" in chu


def test_mot_viec_hong_khong_chan_viec_khac(tmp_path):
    goi = []

    def chay(c):
        goi.append(c)
        return (1, "loi") if "ShopAPI-NaoBoPhan" in c else (0, "")

    ok, chu = l.dang_ky_nao_mo_rong(_goc(tmp_path), chay_lenh=chay)
    assert not ok and len(goi) == 4 and "Hỏng" in chu
