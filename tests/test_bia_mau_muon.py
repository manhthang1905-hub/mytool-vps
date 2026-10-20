"""Bìa thắng MƯỢN của kênh gốc có nhân vật khác (`bia_lo.mau_muon`, 20/10/2026)."""
import json
import os

from core import bia_lo as b


def _kenh(goc, ma, nv):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "style.yaml"), "w", encoding="utf-8") as f:
        f.write('default_character_lock: "{0}"\n'.format(nv))


def test_mau_muon_khi_kenh_goc_khac_nhan_vat(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "TLx-T7", "round white head, no hair")
    _kenh(goc, "TLx-T7-K3", "short black hair, navy sweater")
    _kenh(goc, "TLy-T7-K2", "round white head, no hair")
    os.makedirs(os.path.join(goc, "workspace", "mo-kenh"))
    with open(os.path.join(goc, "workspace", "mo-kenh", "trang-thai.json"), "w", encoding="utf-8") as f:
        json.dump({"TLx-T7-K3": {"kenh_goc": "TLx-T7"}, "TLy-T7-K2": {"kenh_goc": "TLx-T7"}}, f)
    assert b.mau_muon(goc, "TLx-T7-K3") == "TLx-T7"
    assert b.mau_muon(goc, "TLy-T7-K2") == ""      # cùng nhân vật → bìa thắng dùng thẳng
    assert b.mau_muon(goc, "TLx-T7") == ""


def test_san_mau_muon_ngang_bia_giau_khong_ket_san_7():
    assert b.san_cua({"bam_giau": 4}, {"muon": "TLx-T7", "bam": 7})[0] == 5.0
    assert b.san_cua({"bam_giau": 6}, {"muon": "TLx-T7", "bam": 7})[0] == 6.0
    assert b.san_cua({"bam_giau": 9}, {"muon": "TLx-T7", "bam": 7})[0] == 7.0
    assert b.san_cua({"bam_giau": 4}, {"bam": 7})[0] == 7.0   # kênh thường giữ nguyên sàn
