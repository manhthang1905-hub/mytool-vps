"""Công thức VPH + bộ chọn công thức theo kênh (29/09/2026).

`core/cong_thuc_vph.py` chấm ĐỘT BIẾN view/giờ của video đối thủ so với video CÙNG TUỔI;
`core/tu_chay.chon_cong_thuc` chọn công thức theo kenh.yaml `cong_thuc_chon`. Kèm hai sửa
của Công thức V7 cùng đợt: cổng chuyển V7 nới cửa sổ 36–96h (+ nhánh CTR cao), và từ khoá
持たない không còn bắt nhầm 「他人に興味を持たない」.

Không gọi mạng, không cần Qt.
"""

from __future__ import annotations

import calendar
import datetime as dt
import io
import json
import os

from core import cong_thuc_v7 as v7
from core import cong_thuc_vph as vph
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core import tu_chay
from core.phan_tuyen import MA_LECH_NHIP

BAY_GIO = dt.datetime(2026, 9, 29, 12, 0)
SAO = "starSTAR001"   # 48 giờ tuổi, gấp ~14 lần video cùng tuổi


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _kenh(tmp_path, kenh="K", yaml_them=""):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"), "ten: {0}\n{1}".format(kenh, yaml_them))
    return goc


def _so_content(goc, kenh, dong):
    """`dong = [(mã, kênh, tiêu đề, view, ngày đăng, tuyến, tăng/ngày, view trước)]`."""
    cot = so.cot_mac_dinh()
    hang = []
    for ma, k, td, view, ngay, tuyen, tang, truoc in dong:
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": k, "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": str(view), "Ngày đăng": ngay, so.COT_TUYEN: tuyen, "Thời lượng": "15:00",
                  so.COT_TANG: str(tang), so.COT_VIEW_TRUOC: str(truoc)})
        hang.append([d.get(c, "") for c in cot])
    so.luu_bang(goc, kenh, cot, hang)
    _ghi(os.path.join(so.thu_muc_nghien_cuu(goc, kenh), so.TEP_CAI),
         json.dumps({"quet_luc": calendar.timegm(BAY_GIO.timetuple())}))
    cot2 = list(db.COT)
    h2 = []
    for ten, tt in (("心理A", db.THEO_DOI), ("心理B", db.THEO_DOI), ("心理BO", db.BO)):
        r = dict.fromkeys(cot2, "")
        r.update({"Kênh": ten, "Trạng thái": tt, "Link kênh": "https://www.youtube.com/@" + str(abs(hash(ten)))})
        h2.append([r[c] for c in cot2])
    db.luu(goc, kenh, cot2, h2)


def _kho_mau(goc, kenh="K"):
    L = MA_LECH_NHIP
    _so_content(goc, kenh, [
        (SAO, "心理A", "一人が好きな人の本当の心理", 30000, "2026-09-27", L, 0, 0),
        ("aaaaaaaaa01", "心理A", "静かな人の特徴", 2000, "2026-09-27", L, 0, 0),
        ("aaaaaaaaa02", "心理A", "優しい人の特徴", 2400, "2026-09-27", L, 0, 0),
        ("aaaaaaaaa03", "心理A", "賢い人の特徴", 1800, "2026-09-27", L, 0, 0),
        ("bbbbbbbbb01", "心理B", "嫌われる人の特徴", 1500, "2026-09-27", L, 0, 0),
        ("bbbbbbbbb02", "心理B", "繊細な人の特徴", 1600, "2026-09-27", L, 0, 0),
        ("bbbbbbbbb03", "心理B", "孤独な人の特徴", 1700, "2026-09-27", L, 0, 0),
        # Video cũ từng nổ nhưng nay đứng yên → việc của VƯỢT, không phải VPH.
        ("oldOLDold01", "心理A", "昔の大ヒット心理学", 900000, "2026-06-01", L, 0, 0),
        # Kênh bị "bỏ" và tuyến khác — lọc trước khi chấm.
        ("boBOboBO001", "心理BO", "一人が好きな人の脳", 50000, "2026-09-27", L, 0, 0),
        ("khacKHAC001", "心理B", "一人でいる人の真実", 50000, "2026-09-27", "tuyen-khac", 0, 0),
    ])


def test_vph_bat_video_tre_dot_bien_va_loc_nhu_mot_nut(tmp_path):
    goc = _kenh(tmp_path)
    _kho_mau(goc)
    kq = vph.cham(goc, "K", bay_gio=BAY_GIO)
    ma = [d.ma for d in kq.ung_vien]
    assert ma and ma[0] == SAO, [(d.ma, d.dot_bien) for d in kq.ung_vien]
    sao = kq.ung_vien[0]
    assert sao.dot_bien > 5 and sao.ty_kenh and sao.ty_ngach and 40 <= sao.tuoi_gio <= 56
    assert any("đột biến" in x for x in sao.ly_do)
    assert not {"oldOLDold01", "boBOboBO001", "khacKHAC001"} & set(ma)
    assert any("video cũ không bứt" in g for g in kq.ghi_chu)


def test_vph_dinh_dang_chung_cho_chon_nguon(tmp_path):
    goc = _kenh(tmp_path)
    _kho_mau(goc)
    ds = vph.ung_vien_chon_nguon(goc, "K", bay_gio=BAY_GIO)
    assert ds[0]["ma"] == SAO and ds[0]["nguon"] == "vph"
    for khoa in ("link", "tieu_de", "kenh", "diem", "ly_do", "vph", "dot_bien", "tuoi_gio"):
        assert khoa in ds[0]


def test_vph_kho_trong_khong_vo(tmp_path):
    kq = vph.cham(_kenh(tmp_path), "K", bay_gio=BAY_GIO)
    assert kq.ung_vien == [] and kq.canh_bao


# ── bộ chọn công thức ────────────────────────────────────────────────────────

def test_chon_cong_thuc_theo_kenh_yaml(tmp_path):
    goc = _kenh(tmp_path, "A", 'cong_thuc_chon: "vph"\n')
    assert tu_chay.chon_cong_thuc(goc, "A", True)[0] == "vph"
    _kenh(tmp_path, "B", 'cong_thuc_chon: "v7"\n')
    ten, ly = tu_chay.chon_cong_thuc(goc, "B", False)
    assert ten == "vph" and "chưa có cong-thuc-v7.json" in ly
    v7.nap_cau_hinh(goc, "B")  # ghi cấu hình mặc định
    ten, ly = tu_chay.chon_cong_thuc(goc, "B", False)
    assert ten == "v7" and "chỉ định chủ kênh" in ly
    _kenh(tmp_path, "C")
    assert tu_chay.chon_cong_thuc(goc, "C", True)[0] == "v7"
    assert tu_chay.chon_cong_thuc(goc, "C", False)[0] == "vph"
    _kenh(tmp_path, "D", 'cong_thuc_chon: "mot_nut"\n')
    assert tu_chay.chon_cong_thuc(goc, "D", False)[0] == "mot_nut"


def test_ung_vien_xep_hang_dung_vph_va_roi_ve_mot_nut(tmp_path):
    goc = _kenh(tmp_path, "K", 'cong_thuc_chon: "vph"\n')
    log = []
    dong_vph = [{"nguon": "vph", "ma": SAO, "link": "https://www.youtube.com/watch?v=" + SAO,
                 "tieu_de": "一人が好きな人", "kenh": "心理A", "diem": 90, "ly_do": ["đột biến"]}]
    mot_nut = {"moi": [{"link": "https://www.youtube.com/watch?v=motNUTmot01", "tieu_de": "x", "view": 5}]}
    ds = tu_chay.ung_vien_xep_hang(goc, "K", False, set(), cham_vph=lambda g, k: dong_vph,
                                   doc_danh_sach=lambda g, k: mot_nut, log=log.append)
    assert [d["ma"] for d in ds] == [SAO]
    assert any("đang dùng công thức VPH" in x for x in log)
    ds = tu_chay.ung_vien_xep_hang(goc, "K", False, {SAO}, cham_vph=lambda g, k: dong_vph,
                                   doc_danh_sach=lambda g, k: mot_nut, log=log.append)
    assert [d["ma"] for d in ds] == ["motNUTmot01"], "VPH hết ứng viên → không đứng kênh"


def test_ung_vien_xep_hang_v7_theo_chi_dinh_du_chua_qua_nguong(tmp_path):
    goc = _kenh(tmp_path, "K", 'cong_thuc_chon: "v7"\n')
    v7.nap_cau_hinh(goc, "K")

    class _D:
        ma, link, tieu_de, kenh, diem, loai, diem_cum, ly_do = (
            "v7v7v7v7v71", "", "IQが高い人", "c", 80, v7.LAM_NGAY, 22.5, [])
        bi_loai, thua_huong = "", "TL4-T7"

    class _KQ:
        ung_vien = [_D()]
    ds = tu_chay.ung_vien_xep_hang(goc, "K", False, set(), cham_v7=lambda g, k: _KQ(),
                                   doc_danh_sach=lambda g, k: {})
    assert [d["ma"] for d in ds] == ["v7v7v7v7v71"] and ds[0]["thua_huong"] == "TL4-T7"


# ── Công thức V7: cổng chuyển V7 nới cửa sổ, 持たない ────────────────────────

def _moc(goc, kenh, ma, gio, imp, ctr, avd=20.0):
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", ma, "{0}h".format(gio))
    _ghi(os.path.join(d, "tong-quan.json"), json.dumps({"impressions": imp, "ctr": ctr, "avd_pct": avd}))
    _ghi(os.path.join(d, "_thong-tin.json"), json.dumps({"tieu_de": "x", "ngay_dang": "2026-09-20T00:00:00.000Z"}))
    cap = dt.datetime(2026, 9, 20) + dt.timedelta(hours=gio)
    _ghi(os.path.join(d, "raw", "a.json"), json.dumps({"captured_at": cap.strftime("%Y-%m-%dT%H:%M:%S.000Z")}))
    _ghi(os.path.join(d, "raw", "b_join.json"), json.dumps(
        {"href": "https://studio.youtube.com/video/x?ddr_value=YT_RELATED&dimension=TRAFFIC_SOURCE_DETAIL"}))


def test_chuyen_v7_nhan_ctr_cao_o_moc_56h(tmp_path):
    """Ca TL3-T7: 19.618 hiển thị @56h, CTR 9,73% — trước đây trượt vì không có bản chụp 44–54h."""
    goc = str(tmp_path)
    _moc(goc, "K3", "vea03c3caae", 56, 19618, 9.73)
    assert v7.da_co_video_thang(goc, "K3") is True


def test_chuyen_v7_ctr_thuong_duoi_20000_thi_chua(tmp_path):
    goc = str(tmp_path)
    _moc(goc, "K1", "normNORM001", 56, 15000, 5.0)
    assert v7.da_co_video_thang(goc, "K1") is False
    _moc(goc, "K2", "lateLATE001", 120, 90000, 9.0)
    assert v7.da_co_video_thang(goc, "K2") is False, "ngoài cửa sổ 36–96h thì không tính"


def test_mot_tu_mochi_tai_khong_bat_nham_cum_tien():
    assert "vat-chat" not in v7.cum_cua_tieu_de("頭のいい人が他人に興味を持たない本当の理由")
    assert "vat-chat" in v7.cum_cua_tieu_de("物を持たない人の意外な特徴")
    assert v7.cum_cua_tieu_de("精神年齢が高い人の特徴") == ["tinh-than-tuoi"]
