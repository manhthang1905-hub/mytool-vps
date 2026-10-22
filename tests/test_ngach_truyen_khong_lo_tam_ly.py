"""VPS thứ hai — ngách TRUYỆN KỂ (22/10/2026): các lời nhắc chính dựng cho một ngách giả "truyện kể tiếng Anh · US"
KHÔNG được lọt chữ của ngách mặc định (tâm lý học × Nhật, khán giả trung niên–cao tuổi); và với nhóm tâm lý Nhật thật
của kho, cùng các hàm ấy trả ĐÚNG lời nhắc cũ (máy đầu không đổi một ký tự).

Chỉ đĩa trong `tmp_path`, không mạng, không ví, không Chrome.
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC_KHO, "vm"))

from core import ho_so_ngach as hsn  # noqa: E402

YAML_TAM_LY = os.path.join(GOC_KHO, "CHANNEL", "_NHOM", "tam-ly-nhat", "ngach.yaml")
if not os.path.isfile(YAML_TAM_LY):         # gói bản sạch không mang hồ sơ nhóm máy đầu → bản sao trong khuôn
    YAML_TAM_LY = os.path.join(GOC_KHO, "CHANNEL", "_KHUON", "ngach-mau-ja-tam-ly.yaml")

HO_SO_TRUYEN = """mo_ta_ngach: "Life stories — narrated true-to-life stories about family, work and second chances"
ngon_ngu_nguon: en
dang_thang: 'a narrated story with a twist — "she never expected what happened next"'
mo_ta_cho_loc_ai: >-
  In niche: long narrated stories (family drama, workplace revenge, kindness rewarded) told by a voice-over.
  Not in niche: news, gaming, music, cooking, shorts, compilations.
luat_chon:
  - "Only narrated stories with a clear arc."
tieu_chi_doi_thu: ["English-language channel", "main content is narrated life stories", "adult audience", "long videos with voice-over"]
khan_gia_mo_ta: "English-speaking adults 35-65 who listen to stories while doing chores"
chu_de_rong: "narrated stories / storytelling"
khan_gia_loai_tru: ["children and teenagers (school stories, kids cartoons)"]
lac_de_vi_du: ["news", "gaming", "music", "cooking"]
tep_khan_gia:
  - {ma: gia-dinh, ten: "Family drama", ten_ngan: "Family"}
  - {ma: cong-so, ten: "Workplace justice", ten_ngan: "Work"}
mau_tieu_de: "kênh YouTube truyện kể tiếng Anh"
mo_ta_kenh_cho_ai: "Kênh của tôi remake truyện kể có lời đọc cho khán giả Mỹ."
the_loai_en: "storytelling"
nhan_the_loai_mau: "[Story]"
thi_truong: {quoc_gia: US, ngon_ngu: en, mui_gio: America/New_York}
"""

#: Chữ của ngách mặc định — không được xuất hiện trong lời nhắc của ngách truyện kể tiếng Anh.
CAM = ("tâm lý", "Tâm lý", "TÂM LÝ", "心理", "psycholog", "Psycholog", "cao tuổi", "trung niên", "TRUNG NIÊN",
       "NGƯỜI LỚN", "55+", "50+", "tiếng Nhật", "TIẾNG NHẬT", "Japanese", "Nhật", "スクールカースト", "雑学", "脳科学", "não bộ")


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


@pytest.fixture()
def goc_truyen(tmp_path):
    goc = str(tmp_path / "truyen")
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "truyen-ke-us", "ngach.yaml"), HO_SO_TRUYEN)
    _ghi(os.path.join(goc, "CHANNEL", "S1", "kenh.yaml"), 'ten: "Story One"\nnhom: "truyen-ke-us"\nngon_ngu: en\ntep: "gia-dinh"\n')
    return goc


@pytest.fixture()
def goc_tam_ly(tmp_path):
    goc = str(tmp_path / "tam-ly")
    d = os.path.join(goc, "CHANNEL", "_NHOM", "tam-ly-nhat")
    os.makedirs(d)
    shutil.copyfile(YAML_TAM_LY, os.path.join(d, "ngach.yaml"))
    _ghi(os.path.join(goc, "CHANNEL", "T1", "kenh.yaml"), 'nhom: "tam-ly-nhat"\nngon_ngu: ja\n')
    return goc


def _khong_lo(ten, chu):
    lo = [t for t in CAM if t in chu]
    assert not lo, "{0} lọt chữ ngách mặc định {1}:\n{2}".format(ten, lo, chu[:1500])


def _loi_nhac_truyen(goc):
    import nuoi_trang_chu as nuoi
    from core import (auto_khau, chon_anh_canh, cong_thuc_v7_ai, kiem_ngach_doi_thu, loc_doi_thu, phan_cum_ai, phan_tuyen,
                      trang_chu)
    import thiet_lap_kenh_dom as tld

    hs = hsn.doc_ngach(goc, "S1")
    assert hs.co() and not hsn.la_ngach_mac_dinh(hs)
    ra = {}
    ra["nuoi.phan_loai"] = nuoi.de_bai_phan_loai_cho("S1", goc).format("mô tả", "1|A story|Chan", 1)
    de, sau = kiem_ngach_doi_thu.de_bai_cho(goc, "S1")
    ra["kiem_ngach"] = de.format(ngach="NGACH")
    ra["kiem_ngach_sau"] = sau.format(ngach="NGACH")
    ra["trang_chu.loc"] = trang_chu.de_bai_loc_cho(goc, "S1").replace("{ngach}", trang_chu.mo_ta_ngach_cho_ai(goc, "S1"))
    nc = tld.ngu_canh_mo_ta("S1", goc)
    ra["mo_ta_kenh"] = tld.loi_nhac_mo_ta_kenh("Story One", {"ten": "Story One", "luat_chon": "family stories"}, ["T"], [], nc=nc)
    ra["cham_tieu_de"] = auto_khau._tieu_chi_cham_tieu_de_cho(goc, "S1")  # noqa: SLF001
    ch = {"cum": {"x": {"ten": "Family"}}}
    ra["v7_ai"] = cong_thuc_v7_ai.de_bai(ch, [], "", hs=hs)
    tieng_en, kenh_en = chon_anh_canh.ngu_canh_anh(goc, "S1")
    ra["anh.cham"] = chon_anh_canh.loi_nhac_cham(loi_doc="She opened the door.", mo_ta="a woman", phong_cach="soft",
                                                 so_tham_chieu=1, so_ung_vien=3, tieng_en=tieng_en, kenh_en=kenh_en)
    bat = []
    chon_anh_canh.viet_lai_canh(lambda l: bat.append(l) or "", "a woman opening a door in a warm kitchen at dusk",
                                loi_doc="She opened the door.", ghi_chu="- too dark", tieng_en=tieng_en, kenh_en=kenh_en)
    ra["anh.viet_lai"] = bat[0]
    ra["phan_xu"] = phan_tuyen.de_bai_phan_xu_cho(hs)
    ra["gan_tuyen"] = phan_tuyen.de_bai_gan_cho(hs)
    ra["loc_doi_thu"] = loc_doi_thu.de_bai_loc_cho(goc, "S1")
    ra["phan_cum"] = phan_cum_ai.de_bai({"cum": {"x": {"ten": "Family", "tu": ["family"]}}}, hs)
    return ra


def test_loi_nhac_ngach_truyen_khong_lo_chu_tam_ly_nhat(goc_truyen):
    for ten, chu in _loi_nhac_truyen(goc_truyen).items():
        _khong_lo(ten, chu)


def test_loi_nhac_ngach_truyen_mang_dung_ho_so(goc_truyen):
    ra = _loi_nhac_truyen(goc_truyen)
    assert "tiếng Anh" in ra["nuoi.phan_loai"] and "narrated stories / storytelling" in ra["nuoi.phan_loai"]
    assert "children and teenagers" in ra["nuoi.phan_loai"] and "gaming" in ra["nuoi.phan_loai"]
    assert "children and teenagers" in ra["kiem_ngach"] and "children and teenagers" in ra["kiem_ngach_sau"]
    assert "6. ĐÚNG KHÁN GIẢ" in ra["cham_tieu_de"] and "children and teenagers" in ra["cham_tieu_de"]
    assert "English storytelling channel" in ra["mo_ta_kenh"] and "WRITE: English, 300-900" in ra["mo_ta_kenh"]
    assert "(English)" in ra["anh.cham"] and "storytelling" in ra["anh.cham"]
    assert "[Story]" in ra["v7_ai"]


def test_mo_ta_kenh_tieng_khac_khong_doi_kana(goc_truyen):
    import thiet_lap_kenh_dom as tld

    chu = "A warm home for life stories. " * 12
    assert not any("kana" in x for x in tld.kiem_mo_ta_kenh(chu, ngon_ngu="en"))
    assert any("kana" in x for x in tld.kiem_mo_ta_kenh(chu))            # mặc định tiếng Nhật: như cũ
    assert tld.do_dai_mo_ta_cho("ja") == (tld.MO_TA_KENH_TOI_THIEU, tld.MO_TA_KENH_TOI_DA)


def test_the_loai_may_theo_ngach_cua_may(goc_truyen, goc_tam_ly):
    assert hsn.the_loai_may(goc_truyen) == "storytelling"
    assert hsn.the_loai_may(goc_tam_ly) == "psychology"


def test_nhom_tam_ly_nhat_loi_nhac_giu_nguyen_van(goc_tam_ly):
    """Máy đầu: mọi lời nhắc vừa tổng quát hoá trả ĐÚNG bản cũ cho nhóm tâm lý Nhật."""
    import nuoi_trang_chu as nuoi
    from core import auto_khau, chon_anh_canh, cong_thuc_v7_ai, kiem_max_anh
    import thiet_lap_kenh_dom as tld

    hs = hsn.doc_ngach(goc_tam_ly, "T1")
    assert hsn.la_ngach_mac_dinh(hs)
    assert nuoi.de_bai_phan_loai_cho("T1", goc_tam_ly) is nuoi.DE_BAI_PHAN_LOAI_TAM_LY
    assert "NGƯỜI LỚN TRUNG NIÊN–CAO TUỔI" in nuoi.DE_BAI_PHAN_LOAI_TAM_LY
    assert nuoi.DE_BAI_PHAN_LOAI is nuoi.DE_BAI_PHAN_LOAI_TAM_LY
    assert auto_khau._tieu_chi_cham_tieu_de_cho(goc_tam_ly, "T1") is auto_khau._TIEU_CHI_CHAM_TIEU_DE  # noqa: SLF001
    assert chon_anh_canh.ngu_canh_anh(goc_tam_ly, "T1") == ("", "")
    ch = {"cum": {"x": {"ten": "X"}}}
    assert cong_thuc_v7_ai.de_bai(ch, [], "", hs=hs) == cong_thuc_v7_ai.de_bai(ch, [], "")
    assert "【心理学】【脳科学】【雑学】" in cong_thuc_v7_ai.de_bai(ch, [], "", hs=hs)
    nc = tld.ngu_canh_mo_ta("T1", goc_tam_ly)
    assert nc["mac_dinh"] is True
    kh = {"ten": "x", "luat_chon": "y"}
    assert tld.loi_nhac_mo_ta_kenh("A", kh, ["t"], [], nc=nc) == tld.loi_nhac_mo_ta_kenh("A", kh, ["t"], [])
    ln = chon_anh_canh.loi_nhac_cham(loi_doc="x", mo_ta="y", phong_cach="z", so_tham_chieu=0, so_ung_vien=2)
    assert ln.startswith(chon_anh_canh._DAU_CHAM)  # noqa: SLF001
    assert chon_anh_canh.ban_dia_loi_nhac(ln, "", "") == ln
    assert kiem_max_anh.LOI_NHAC_LO.split("\n{ta_ref}")[0].startswith("You are a strict art director")


def test_ngach_truyen_nuoi_trang_chu_doc_ban_nhap(tmp_path):
    """Kênh NHÁP đang nuôi (`workspace/chuan-bi-<K>/`) chưa có CHANNEL/<K> vẫn được đề bài theo hồ sơ nhóm."""
    import nuoi_trang_chu as nuoi

    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "truyen-ke-us", "ngach.yaml"), HO_SO_TRUYEN)
    _ghi(os.path.join(goc, "workspace", "chuan-bi-S2", "CHANNEL", "S2", "kenh.yaml"),
         'ten: "(nuôi trang chủ) — x"\nnhom: "truyen-ke-us"\nngon_ngu: en\nnuoi_trang_chu: true\n')
    de = nuoi.de_bai_phan_loai_cho("S2", goc)
    assert de is not nuoi.DE_BAI_PHAN_LOAI_TAM_LY and "tiếng Anh" in de
    _khong_lo("nuoi.nhap", de.format("m", "1|t|k", 1))
