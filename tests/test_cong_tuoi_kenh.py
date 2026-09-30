"""Cổng tuổi THEO KÊNH — kenh.yaml `cho_phep_tep_gia` (30/09/2026, kênh 5: tệp 65+).

Mặc định TẮT: kênh không khai chạy y hệt trước (TL1–TL4). Bật: VPH / V7 / Một nút / luật cứng không
loại nguồn chỉ vì mốc tuổi; phán quyết ngách đối thủ dùng kho RIÊNG của kênh (không kho nhóm).
Không gọi mạng.
"""

from __future__ import annotations

import io
import json
import os

from core import cong_thuc_vph as vph
from core import nghien_cuu_chung as ncc
from core import phan_tuyen as pt
from core.chien_luoc import ngu_canh

from test_cong_thuc_vph import BAY_GIO, SAO, _ghi, _kenh, _so_content

TUOI = "60代で幸せな人の本当の心理"


def _kho_tuoi(goc, kenh="K"):
    L = pt.MA_LECH_NHIP
    _so_content(goc, kenh, [
        (SAO, "心理A", TUOI, 30000, "2026-09-27", L, 0, 0),
        ("aaaaaaaaa01", "心理A", "静かな人の特徴", 2000, "2026-09-27", L, 0, 0),
        ("aaaaaaaaa02", "心理A", "優しい人の特徴", 2400, "2026-09-27", L, 0, 0),
        ("aaaaaaaaa03", "心理A", "賢い人の特徴", 1800, "2026-09-27", L, 0, 0),
        ("bbbbbbbbb01", "心理B", "嫌われる人の特徴", 1500, "2026-09-27", L, 0, 0),
        ("bbbbbbbbb02", "心理B", "繊細な人の特徴", 1600, "2026-09-27", L, 0, 0),
        ("bbbbbbbbb03", "心理B", "孤独な人の特徴", 1700, "2026-09-27", L, 0, 0),
        # từ loại trừ THỂ LOẠI vẫn loại dù bật khoá
        ("mangaMANGA1", "心理B", "60代の漫画で学ぶ心理", 40000, "2026-09-27", L, 0, 0),
    ])


def test_mac_dinh_tat_vph_van_loai_moc_tuoi(tmp_path):
    goc = _kenh(tmp_path)
    _kho_tuoi(goc)
    assert pt.cho_phep_tep_gia(goc, "K") is False
    ma = [d.ma for d in vph.cham(goc, "K", bay_gio=BAY_GIO).ung_vien]
    assert SAO not in ma


def test_bat_khoa_vph_giu_moc_tuoi_nhung_van_loai_the_loai(tmp_path):
    goc = _kenh(tmp_path, yaml_them="cho_phep_tep_gia: true\n")
    _kho_tuoi(goc)
    assert pt.cho_phep_tep_gia(goc, "K") is True
    ma = [d.ma for d in vph.cham(goc, "K", bay_gio=BAY_GIO).ung_vien]
    assert ma and ma[0] == SAO
    assert "mangaMANGA1" not in ma


def test_doc_khoa_chuoi_va_sai(tmp_path):
    for gt, mong in (("false", False), ('"true"', True), ("0", False), ("yes", True)):
        goc = _kenh(tmp_path / gt.strip('"'), yaml_them="cho_phep_tep_gia: {0}\n".format(gt))
        assert pt.cho_phep_tep_gia(goc, "K") is mong, gt
    assert pt.cho_phep_tep_gia(str(tmp_path / "khong-co"), "K") is False


def test_luat_cung_bo_moc_tuoi():
    ma_co = {pt.MA_LECH_NHIP, pt.MA_TRUNG_NIEN}
    assert pt.ap_luat_cung(TUOI, "", pt.MA_LECH_NHIP, ma_co) == pt.MA_TRUNG_NIEN
    assert pt.ap_luat_cung(TUOI, "", pt.MA_LECH_NHIP, ma_co, bo_moc_tuoi=True) == pt.MA_LECH_NHIP
    assert pt.ap_luat_cung("60代の漫画", "", pt.MA_LECH_NHIP, ma_co, bo_moc_tuoi=True) == pt.MA_KHAC


def test_ngu_canh_va_mo_ta_cho_llm(tmp_path):
    goc = _kenh(tmp_path / "a")
    assert ngu_canh.dung(goc, "K", co_v7=False).cho_phep_tep_gia is False
    assert pt.mo_ta_tep_gia(goc, "K") == ""
    goc = _kenh(tmp_path / "b", yaml_them='cho_phep_tep_gia: true\ntep: "t65"\nluat_chon: "chân dung | sức khoẻ → lệch"\n')
    assert ngu_canh.dung(goc, "K", co_v7=False).cho_phep_tep_gia is True
    mo = pt.mo_ta_tep_gia(goc, "K")
    assert "NGƯỜI GIÀ (t65)" in mo and "sức khoẻ → lệch" in mo


def test_kho_phan_quyet_ngach_theo_kenh(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "g", "ngach.yaml"), "mo_ta_ngach: x\n")
    _ghi(os.path.join(goc, "CHANNEL", "A", "kenh.yaml"), 'nhom: "g"\n')
    _ghi(os.path.join(goc, "CHANNEL", "B", "kenh.yaml"), 'nhom: "g"\ncho_phep_tep_gia: true\n')
    chung = ncc.duong_kenh_ai(goc, "A")
    rieng = ncc.duong_kenh_ai(goc, "B")
    assert chung == os.path.join(ncc.thu_muc(goc, "A"), ncc.TEP_KENH_AI)
    assert rieng != chung and os.path.join("CHANNEL", "B", "nghien-cuu") in rieng
    # kênh bật khoá không thấy phán quyết "không" của kho nhóm
    from core import kiem_ngach_doi_thu as kn

    import datetime as dt

    link = "https://www.youtube.com/@senior"
    hom = dt.date.today().isoformat()
    _ghi(chung, json.dumps({link: {"ket": "khong", "ngay": hom, "kiem_ngach": "bo"}}))
    assert (kn.phan_quyet_nhom(goc, "A", link) or {}).get("kiem_ngach") == "bo"
    assert kn.phan_quyet_nhom(goc, "B", link) is None
    kn.ghi_phan_quyet_nhom(goc, "B", {link: {"k": "giu", "ly_do": "chân dung 65+"}})
    assert (kn.phan_quyet_nhom(goc, "B", link) or {}).get("kiem_ngach") == "giu"
    with io.open(chung, encoding="utf-8") as tep:
        assert json.load(tep)[link]["kiem_ngach"] == "bo"   # kho nhóm không bị ghi đè
