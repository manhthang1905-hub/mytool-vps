"""Sổ đối thủ CHUNG của nhóm (`core/so_doi_thu_chung.py`, 12/10/2026).

Canh: một dòng mỗi kênh đối thủ (gộp `@handle` ↔ `UC…` qua ảnh chụp kênh) · không mất ghi chú nào (kể cả dòng trùng
trong MỘT sổ) · số đo lần quét mới nhất thắng · gieo phán quyết đủ chắc vào sổ kênh còn thiếu (không gieo bỏ-vì-từ-khoá,
ghi chú tay) · kênh kho ngách riêng chỉ nhận phần không phụ thuộc tệp · `chot` hộp thư không đo lại kênh đã có trong
sổ chung · số đo chung chỉ điền ô trống / dòng theo dõi cũ. Toàn bộ link, mã kênh, tên kênh là GIẢ.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chot_doi_thu as cdt  # noqa: E402
from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import so_doi_thu_chung as sdc  # noqa: E402

NHOM = "ngach-gia"
UC = "UCgiaGiaGiaGiaGiaGiaGia1"          # mã kênh giả (24 ký tự, đúng dạng UC…)
L_HANDLE = "https://www.youtube.com/@kenhgia-a"
L_UC = "https://www.youtube.com/channel/" + UC


def _kenh(goc, ma, nhom=NHOM, them=""):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(d, "nghien-cuu"), exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ma: {0}\nngon_ngu: ja\n".format(ma) + ("nhom: {0}\n".format(nhom) if nhom else "") + them)


def _so(goc, ma, dong):
    """`dong` = [{cột: giá trị}] → doi-thu.csv của kênh."""
    cot = list(db.COT)
    hang = [[str(d.get(c, "")) for c in cot] for d in dong]
    db.luu(goc, ma, cot, hang)


def _hop_thu(goc, ma, links):
    so.luu_doi_thu(goc, ma, "\n".join(links))


def _kenh_do(goc, cac):
    """Ảnh chụp kênh giả trong kho nhóm: `[(input_url, channel_id)]`."""
    p = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "nghien-cuu", "kenh-do.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    du = {"{0}|40|ja".format(l): {"ngay": "2026-10-10", "ch": {"input_url": l, "channel_id": cid,
                                                               "channel_url": "https://www.youtube.com/channel/" + cid}}
          for l, cid in cac}
    with open(p, "w", encoding="utf-8") as t:
        json.dump(du, t)


def test_mot_dong_moi_kenh_gop_handle_va_uc_khong_mat_ghi_chu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    _kenh_do(goc, [(L_HANDLE, UC)])
    _so(goc, "A", [
        {"Kênh": "KenhGiaA", "Link kênh": L_HANDLE, "Trạng thái": db.THEO_DOI, "Subs": "100",
         "Ghi chú": "✓ AI kiểm ngách 10/10: đúng ngách", "Quét lúc": "2026-10-10 05:00", "Tuyến": "tep-a"},
        # dòng TRÙNG trong cùng sổ A (quét ghi link /channel/UC… yt-dlp trả về)
        {"Kênh": "KenhGiaA", "Link kênh": L_UC, "Trạng thái": db.THEO_DOI, "Ghi chú": "ghi tay của chủ",
         "Quét lúc": "2026-10-09 05:00"}])
    _so(goc, "B", [{"Kênh": "KenhGiaA", "Link kênh": L_UC, "Trạng thái": db.BO, "Subs": "120",
                    "Ghi chú": "không phải kênh tâm lý — AI: lạc", "Quét lúc": "2026-10-11 06:00"}])
    du = sdc.gop(goc, NHOM)
    assert list(du["kenh"]) == [UC]
    e = du["kenh"][UC]
    assert e["so"]["Subs"] == "120"                           # lần quét mới nhất thắng
    assert e["quet_luc"] == "2026-10-11 06:00"
    tk = e["theo_kenh"]
    ghi = {tk["A"]["ghi"], tk["B"]["ghi"]} | {x["ghi"] for x in tk["A"].get("trung", [])}
    assert ghi == {"✓ AI kiểm ngách 10/10: đúng ngách", "ghi tay của chủ", "không phải kênh tâm lý — AI: lạc"}
    assert tk["A"]["tuyen"] == "tep-a" and tk["B"]["tt"] == db.BO
    assert du["thong_ke"]["dong_so_rieng"] == 3 and du["thong_ke"]["kenh"] == 1
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "_NHOM", NHOM, sdc.TEP))
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "_NHOM", NHOM, sdc.TEP_CSV))
    assert sdc.tra(goc, NHOM, L_HANDLE)["khoa"] == UC         # tra được bằng mọi dạng link


def _so_a_day_du(goc):
    _so(goc, "A", [
        {"Kênh": "X", "Link kênh": "https://www.youtube.com/@giax", "Trạng thái": db.THEO_DOI, "Subs": "900",
         "Ghi chú": "✓ AI kiểm ngách 11/10: chân dung tâm lý", "Quét lúc": "2026-10-11 05:00", "Tuyến": "tep-a"},
        {"Kênh": "Y", "Link kênh": "https://www.youtube.com/@giay", "Trạng thái": db.BO,
         "Ghi chú": "không phải kênh tâm lý — AI: toàn nhạc", "Quét lúc": "2026-10-01 05:00"},
        {"Kênh": "Z", "Link kênh": "https://www.youtube.com/@giaz", "Trạng thái": db.BO,
         "Ghi chú": "không phải kênh tâm lý: thể loại 雑学/要約/tóm sách", "Quét lúc": "2026-10-01 05:00"},
        {"Kênh": "W", "Link kênh": "https://www.youtube.com/@giaw", "Trạng thái": db.HET,
         "Ghi chú": "Hết 11/10: không còn làm", "Quét lúc": "2026-10-11 05:00"},
        {"Kênh": "V", "Link kênh": "https://www.youtube.com/@giav", "Trạng thái": db.THEO_DOI, "Ghi chú": ""},
        {"Kênh": "U", "Link kênh": "https://www.youtube.com/@giau", "Trạng thái": db.THEO_DOI,
         "Ghi chú": "bạn đưa — luôn quét"}])


LINKS = ["https://www.youtube.com/@gia" + x for x in "xyzwvu"]


def test_gieo_phan_quyet_du_chac_vao_so_kenh_con_thieu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    _so_a_day_du(goc)
    _hop_thu(goc, "B", LINKS)
    du = sdc.gop(goc, NHOM)
    dem = sdc.ap_vao_so(goc, "B", du=du)
    assert dem["gieo"] == 4 and dem["bo_qua"] == 2, dem          # Z (từ khoá) và V (tay) không gieo
    assert dem["theo_lop"] == {"giu": 1, "bo": 1, "het": 1, "ban_dua": 1}
    cot, hang = db.doc(goc, "B")
    o = db.chi_so_cot(cot)
    theo = {h[o["Kênh"]]: h for h in hang}
    assert set(theo) == {"X", "Y", "W", "U"}
    assert theo["X"][o["Trạng thái"]] == db.THEO_DOI and theo["X"][o["Ghi chú"]].startswith("✓ AI kiểm ngách")
    assert theo["X"][o["Tuyến"]] == ""                            # tuyến là phán quyết RIÊNG — không chép
    assert theo["X"][o["Subs"]] == "900"
    assert theo["Y"][o["Trạng thái"]] == db.BO and theo["W"][o["Trạng thái"]] == db.HET
    assert theo["U"][o["Ghi chú"]] == "bạn đưa — luôn quét"
    assert sorted(db.hop_thu(goc, "B")) == ["https://www.youtube.com/@giav", "https://www.youtube.com/@giaz"]
    assert sdc.ap_vao_so(goc, "B", du=sdc.gop(goc, NHOM))["gieo"] == 0   # lần hai không thêm gì


def test_kenh_kho_ngach_rieng_chi_nhan_phan_khong_phu_thuoc_tep(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B", them="cho_phep_tep_gia: true\n")
    _so_a_day_du(goc)
    _hop_thu(goc, "B", LINKS)
    dem = sdc.ap_vao_so(goc, "B", du=sdc.gop(goc, NHOM))
    assert dem["theo_lop"] == {"het": 1, "ban_dua": 1}, dem


def test_phan_quyet_ngach_cua_kenh_kho_rieng_khong_vao_phan_chung(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", them="cho_phep_tep_gia: true\n")
    _kenh(goc, "B")
    _so(goc, "A", [{"Kênh": "Y", "Link kênh": "https://www.youtube.com/@giay", "Trạng thái": db.BO,
                    "Ghi chú": "không phải kênh tâm lý — AI: không hợp tệp người già"}])
    _hop_thu(goc, "B", ["https://www.youtube.com/@giay"])
    du = sdc.gop(goc, NHOM)
    assert du["kenh"]["@giay"]["ngach"] is None
    assert sdc.ap_vao_so(goc, "B", du=du)["gieo"] == 0


def test_chot_hop_thu_khong_do_lai_kenh_anh_em_da_cham(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    _so_a_day_du(goc)
    moi = "https://www.youtube.com/@giamoi"
    _hop_thu(goc, "B", LINKS + [moi])
    goi = []

    def lay_kenh(link, **kw):
        goi.append(link)
        raise RuntimeError("không có mạng trong bài kiểm")
    dem = cdt.chot(goc, "B", lay_kenh=lay_kenh, lang="ja", xet_lai=False, kiem_dinh_ky=False)
    assert sorted(goi) == sorted(["https://www.youtube.com/@giav", "https://www.youtube.com/@giaz", moi]), goi
    assert dem["cham"] == 3
    _c, hang = db.doc(goc, "B")
    assert len(hang) == 4                                          # 4 dòng gieo từ sổ chung, không đo
    du = sdc.doc(goc, NHOM)
    assert du and "B" in (du["kenh"]["@giax"]["theo_kenh"])        # gộp lại sau lượt chấm: B đã có mặt


def test_so_do_chung_chi_dien_o_trong_hoac_dong_theo_doi_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    _so(goc, "A", [
        {"Kênh": "X", "Link kênh": "https://www.youtube.com/@giax", "Trạng thái": db.THEO_DOI, "Subs": "900",
         "View TV": "5000", "Quét lúc": "2026-10-11 05:00", "Ghi chú": "✓ AI kiểm ngách 11/10: ok"},
        {"Kênh": "Y", "Link kênh": "https://www.youtube.com/@giay", "Trạng thái": db.BO, "Subs": "70",
         "Quét lúc": "2026-10-11 05:00", "Ghi chú": "không phải kênh tâm lý — AI: lạc"}])
    _so(goc, "B", [
        {"Kênh": "X", "Link kênh": "https://www.youtube.com/@giax", "Trạng thái": db.THEO_DOI, "Subs": "10",
         "Quét lúc": "2026-10-01 05:00", "Ghi chú": "của B"},
        {"Kênh": "Y", "Link kênh": "https://www.youtube.com/@giay", "Trạng thái": db.BO, "Subs": "50",
         "Quét lúc": "2026-09-20 05:00", "Ghi chú": "của B nữa"}])
    dem = sdc.ap_vao_so(goc, "B", du=sdc.gop(goc, NHOM))
    assert dem["lam_moi"] == 1
    cot, hang = db.doc(goc, "B")
    o = db.chi_so_cot(cot)
    theo = {h[o["Kênh"]]: h for h in hang}
    assert theo["X"][o["Subs"]] == "900" and theo["X"][o["View TV"]] == "5000"   # theo dõi, cũ > 3 ngày → đè
    assert theo["Y"][o["Subs"]] == "50"                                         # dòng bỏ: không xáo
    assert theo["X"][o["Ghi chú"]] == "của B" and theo["X"][o["Quét lúc"]] == "2026-10-01 05:00"


@pytest.mark.parametrize("ghi, lop", [
    ("✓ AI kiểm ngách 12/10: chân dung", "giu"), ("AI kiểm ngách 30/09: tâm linh", "bo"),
    ("AI kiểm ngách 30/09: ngừng hoạt động — video dài mới nhất cách 90 ngày", "het"),
    ("Hết — không còn làm: video dài mới nhất 2025-12-13", "het"), ("⚠ NGHI: chưa rõ", "nghi"),
    ("không phải kênh tâm lý — gần ngách, AI: self-help", "bo"), ("AI: đối thủ (80đ) — chân dung", "giu"),
    ("kênh không còn hoặc không xem được: 404", "chet"), ("không phải tiếng của kênh: tiêu đề viết bằng chữ", "lech_tieng"),
    ("không phải kênh tâm lý: thể loại 雑学", "tu_khoa"), ("thị trường (còn nhỏ / khác khổ): 43:05", "may"),
    ("bạn đưa — luôn quét ‖ ✓ AI kiểm ngách 12/10", "ban_dua"), ("", "tay"), ("ghi tay", "tay")])
def test_phan_loai_ghi_chu(ghi, lop):
    assert sdc.phan_loai_ghi_chu(ghi, "2026-10-12 05:00")[0] == lop


def test_ngay_dd_mm_doi_nam(tmp_path):
    assert sdc.phan_loai_ghi_chu("✓ AI kiểm ngách 30/12: x", "2027-01-02 05:00")[1] == "2026-12-30"


def test_kenh_khong_nhom_khong_lam_gi(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "C", nhom="")
    _hop_thu(goc, "C", ["https://www.youtube.com/@giax"])
    assert sdc.dong_bo_truoc_chot(goc, "C") == {}
    assert sdc.ap_vao_so(goc, "C")["gieo"] == 0
