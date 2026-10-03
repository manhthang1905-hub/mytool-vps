"""Tự động hoá "Việc của bạn" (04/10/2026): lọc nhắc của giám đốc, quyền tự nâng/hạ theo thành tích,
kênh mới không "khan", lịch tự đăng ký lại, lỗi khởi tạo ngách tự thử lại.

Cô lập: mọi thứ trong `tmp_path`; không mạng, không ví, không schtasks thật."""

from __future__ import annotations

import datetime as dt
import io
import json
import os

import pytest

import core.giam_doc as gd
from core import bang_dieu_khien as bdk
from core import gac_tong
from core.giam_doc import bao_cao, du_lieu
from core.giam_doc.suc_khoe import VIEC_CUA_BAN as VIEC_CHINH_SACH

BAY = dt.datetime(2026, 10, 4, 12, 0)


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _kenh(goc, ma="GDT", **cai):
    dong = ['ma: "{0}"'.format(ma)] + ['{0}: "{1}"'.format(k, v) for k, v in cai.items()]
    _ghi(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "\n".join(dong) + "\n")


# ═══ 1. lọc nhắc ════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cau,ky_vong", [
    ("Chờ 3 video qua 48h rồi mới đo CTR.", "cho_so"),
    ("Đợi video X đủ 7 ngày", "cho_so"),
    ("đang chờ số 48h của 2 video", "cho_so"),
    ("Mở Studio xem video A có bị giảm hiển thị không", "may"),
    ("Kiểm tra bảng pool nguồn của cụm tiền bạc", "may"),
    ("Tự xem lại kịch bản video B", "may"),
    (VIEC_CHINH_SACH, "nguoi"),
    ("Đổi tiêu đề video abc “x” thành “y” (CTR thấp).", "nguoi"),
    ("Quyết định lớn chờ bạn duyệt: chien_luoc “a” → “b”.", "nguoi"),
    ("Đăng nhập lại Google trên Chrome của kênh X (hết phiên).", "nguoi"),
    ("Nạp tiền ShopAPI, ví còn 2 ngày.", "nguoi"),
    ("Xác minh số điện thoại cho kênh mới.", "nguoi"),
])
def test_phan_loai_viec_giam_doc(cau, ky_vong):
    assert gd.phan_loai_viec(cau) == ky_vong


def test_bang_dieu_khien_chi_hien_viec_nguoi_lam_duoc():
    assert bdk.viec_gd_can_nguoi(VIEC_CHINH_SACH)
    assert bdk.viec_gd_can_nguoi("Đổi tiêu đề video A")
    assert not bdk.viec_gd_can_nguoi("Chờ 4 video qua 48h")
    assert not bdk.viec_gd_can_nguoi("Mở Studio xem kênh có cảnh báo không")


def _bao_cao_gd(goc, ma, viec):
    _ghi(os.path.join(du_lieu.thu_muc_giam_doc(goc, ma), bao_cao.TEP_BAO_CAO_JSON),
         {"luc": "2026-10-04T04:20:00", "che_do": "goi_y", "viec_cua_ban": viec})


def test_gac_tong_chi_bao_nguoi_viec_cua_nguoi_con_lai_vao_hang_doi_nao(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="goi_y")
    _bao_cao_gd(goc, "GDT", ["Chờ 3 video qua 48h.", "Mở Studio xem video A có bị giảm không", VIEC_CHINH_SACH])
    sc = gac_tong.kiem_giam_doc(goc, bay_gio=BAY)
    viec = [s for s in sc if s["loai"] == "giam_doc_viec"]
    assert len(viec) == 1 and VIEC_CHINH_SACH[:30] in viec[0]["chuyen_gi"]
    assert viec[0]["lap_gio"] == 24.0, "cảnh báo chính sách: 1 lần/ngày"
    # việc "may" nằm ở hàng đợi cho bộ não; "chờ số" chỉ vào nhật ký giám đốc
    hang = gd.doc_viec_cho_nao(goc, BAY)
    assert [m["viec"] for m in hang] == ["Mở Studio xem video A có bị giảm không"] and hang[0]["kenh"] == "GDT"
    assert os.path.isfile(os.path.join(goc, "nao", "viec-tu-giam-doc.json"))
    nk = [json.loads(x) for x in io.open(os.path.join(goc, "CHANNEL", "GDT", "giam-doc", "nhat-ky.jsonl"), encoding="utf-8")]
    assert [d["viec"] for d in nk] == ["cho_so"]
    # lượt sau: không lặp lại ở đâu cả
    gac_tong.kiem_giam_doc(goc, bay_gio=BAY + dt.timedelta(minutes=15))
    assert len(gd.doc_viec_cho_nao(goc, BAY)) == 1
    nk = [json.loads(x) for x in io.open(os.path.join(goc, "CHANNEL", "GDT", "giam-doc", "nhat-ky.jsonl"), encoding="utf-8")]
    assert len(nk) == 1, "chờ số: ghi nhật ký đúng 1 lần"


def test_gac_tong_thu_khong_ghi_hang_doi(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="goi_y")
    _bao_cao_gd(goc, "GDT", ["Mở Studio xem video A"])
    sc = gac_tong.kiem_giam_doc(goc, bay_gio=BAY, ghi_dia=False)
    assert not [s for s in sc if s["loai"] == "giam_doc_viec"]
    assert not os.path.exists(os.path.join(goc, "nao", "viec-tu-giam-doc.json"))


def test_hang_doi_nao_het_han_va_khong_ghi_lai(tmp_path):
    goc = str(tmp_path)
    assert gd.ghi_viec_may(goc, "KA", "Kiểm tra bảng pool", "may", bay_gio=BAY)
    assert not gd.ghi_viec_may(goc, "KA", "Kiểm tra bảng pool", "may", bay_gio=BAY + dt.timedelta(days=1))
    assert len(gd.doc_viec_cho_nao(goc, BAY + dt.timedelta(days=8))) == 1
    assert gd.doc_viec_cho_nao(goc, BAY + dt.timedelta(days=10)) == []


# kênh mới ──────────────────────────────────────────────────────────────────────

def test_kenh_moi_chua_co_video_khong_phat_khan(tmp_path):
    snap = {"tu_chay": True, "ke_hoach": [], "kenh_moi": True}
    assert gac_tong._kiem_khong_video_moi("K", snap, BAY) == []
    snap["kenh_moi"] = False
    ds = gac_tong._kiem_khong_video_moi("K", snap, BAY)
    assert ds and ds[0]["muc"] == "khan", "kênh cũ chưa có video vẫn khan"


def test_la_kenh_moi_theo_ngay_bat_dau(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "KM", ngay_bat_dau="2026-10-03")
    _kenh(goc, "KC", ngay_bat_dau="2026-09-21")
    _kenh(goc, "KK")
    assert gac_tong._la_kenh_moi(goc, "KM", BAY) is True
    assert gac_tong._la_kenh_moi(goc, "KC", BAY) is False
    assert gac_tong._la_kenh_moi(goc, "KK", BAY) is False
    assert gac_tong._la_kenh_moi(goc, "KM", BAY + dt.timedelta(days=3)) is False, "đủ 3 ngày: khan trở lại"


# ═══ 2. quyền theo thành tích ═══════════════════════════════════════════════════

def _du_doan(goc, ma, dung, sai):
    ds = [{"video_id": "v{0}".format(i), "dung": i < dung} for i in range(dung + sai)]
    _ghi(os.path.join(du_lieu.thu_muc_giam_doc(goc, ma), "du-doan.json"), {"du_doan": ds})


def _luc_ghi():
    ghi = []
    return ghi, lambda g, m, **kv: ghi.append((m, kv))


def test_nang_len_tu_ap_khi_du_nguong(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="goi_y")
    _du_doan(goc, "GDT", 7, 3)  # 70% trên n=10
    ghi, ghi_cai = _luc_ghi()
    ra = gd.tu_nang_ha_quyen(goc, bay_gio=BAY, ghi_cai=ghi_cai)
    assert [(d["ma"], d["truoc"], d["sau"]) for d in ra] == [("GDT", "goi_y", "tu_ap")]
    assert ghi == [("GDT", {"giam_doc": "tu_ap"})]
    assert "7/10" in ra[0]["ly_do"] and "70%" in ra[0]["ly_do"]
    nk = [json.loads(x) for x in io.open(os.path.join(goc, "CHANNEL", "GDT", "giam-doc", "nhat-ky.jsonl"), encoding="utf-8")]
    assert nk[-1]["viec"] == "doi_quyen" and nk[-1]["truoc"] == "goi_y" and nk[-1]["sau"] == "tu_ap"
    assert "7/10" in nk[-1]["ly_do_llm"]


def test_khong_nang_khi_thieu_mau_hoac_duoi_70(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="goi_y")
    _du_doan(goc, "GDT", 6, 3)  # n=9 < 10
    ghi, ghi_cai = _luc_ghi()
    assert gd.tu_nang_ha_quyen(goc, bay_gio=BAY, ghi_cai=ghi_cai) == []
    _du_doan(goc, "GDT", 6, 4)  # 60% trên n=10
    assert gd.tu_nang_ha_quyen(goc, bay_gio=BAY, ghi_cai=ghi_cai) == [] and not ghi


def test_lui_ve_goi_y_khi_tut_duoi_55(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="tu_ap")
    _du_doan(goc, "GDT", 5, 5)  # 50% < 55%
    ghi, ghi_cai = _luc_ghi()
    ra = gd.tu_nang_ha_quyen(goc, bay_gio=BAY, ghi_cai=ghi_cai)
    assert [(d["truoc"], d["sau"]) for d in ra] == [("tu_ap", "goi_y")] and ghi == [("GDT", {"giam_doc": "goi_y"})]
    assert "50%" in ra[0]["ly_do"] and "55%" in ra[0]["ly_do"]


def test_tu_ap_giu_quyen_trong_vung_55_70(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="tu_ap")
    _du_doan(goc, "GDT", 6, 4)  # 60%: chưa tới 70% nhưng chưa tụt dưới 55%
    ghi, ghi_cai = _luc_ghi()
    assert gd.tu_nang_ha_quyen(goc, bay_gio=BAY, ghi_cai=ghi_cai) == [] and not ghi


def test_khong_dung_kenh_tat_kenh_v2_va_kenh_mau(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "KT", giam_doc="tat")
    _kenh(goc, "KP", giam_doc="goi_y")
    _kenh(goc, "KP-v2", giam_doc="goi_y")
    _kenh(goc, "_MAU", giam_doc="goi_y")
    for ma in ("KT", "KP", "KP-v2", "_MAU"):
        _du_doan(goc, ma, 9, 1)
    ghi, ghi_cai = _luc_ghi()
    assert gd.tu_nang_ha_quyen(goc, bay_gio=BAY, ghi_cai=ghi_cai) == [] and not ghi


def test_nang_quyen_ghi_that_kenh_yaml_khong_chu_thich(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, giam_doc="goi_y", giam_doc_studio="true")
    _du_doan(goc, "GDT", 8, 2)
    gd.tu_nang_ha_quyen(goc, bay_gio=BAY)
    chu = io.open(os.path.join(goc, "CHANNEL", "GDT", "kenh.yaml"), encoding="utf-8").read()
    assert 'giam_doc: "tu_ap"' in chu and "#" not in chu and 'giam_doc_studio: "true"' in chu


# ═══ 5. việc máy tự xử ══════════════════════════════════════════════════════════

def _anh_lich(tat=True, tu_chay=True):
    return {"luc": BAY.isoformat(timespec="seconds"), "kenh": {"K": {"tu_chay": tu_chay}},
            "may": {"schtasks_tu_chay": {"da_dang_ky": not tat}}}


def test_lich_tat_may_tu_dang_ky_lai_va_khong_la_viec_cua_nguoi(tmp_path):
    goc = str(tmp_path)
    goi = []
    ra = gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(), bay_gio=BAY, dang_ky_lich=lambda g: goi.append(g) or (True, "ok"))
    assert goi == [goc] and [h["loai"] for h in ra] == ["tu_xu_ly:lich"] and ra[0]["thuc_hien"] is True
    assert bdk.da_tu_xu_ly(goc, "lich", BAY)
    # bảng điều khiển không hiện "Lịch tự chạy đang tắt"
    k = {"ma": "K", "tu_chay": True}
    viec = bdk.viec_cua_ban(goc, anh={"kenh": [k]}, bay_gio=BAY, gio_lich="")
    assert not [v for v in viec if v["khoa"] == "lich"]
    # không ghi loi-chay-max.md
    assert not os.path.exists(os.path.join(goc, "workspace", "loi-chay-max.md"))
    # chưa tới 6 giờ: không thử lại
    gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(), bay_gio=BAY + dt.timedelta(hours=1),
                               dang_ky_lich=lambda g: goi.append("lan2") or (True, "ok"))
    assert goi == [goc]


def test_lich_tat_thu_hong_thi_van_hien_cho_nguoi(tmp_path):
    goc = str(tmp_path)
    gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(), bay_gio=BAY, dang_ky_lich=lambda g: (False, "Access denied"))
    assert not bdk.da_tu_xu_ly(goc, "lich", BAY)
    viec = bdk.viec_cua_ban(goc, anh={"kenh": [{"ma": "K", "tu_chay": True}]}, bay_gio=BAY, gio_lich="")
    assert [v for v in viec if v["khoa"] == "lich"]


def test_lich_tat_thu_3_lan_van_con_thi_hien_lai(tmp_path):
    goc = str(tmp_path)
    t = BAY
    for _ in range(3):
        gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(), bay_gio=t, dang_ky_lich=lambda g: (True, "ok"))
        t += dt.timedelta(hours=7)
    assert not bdk.da_tu_xu_ly(goc, "lich", t - dt.timedelta(hours=7))


def test_lich_da_bat_thi_quen_so_va_che_do_thu_khong_lam_gi(tmp_path):
    goc = str(tmp_path)
    goi = []
    gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(), bay_gio=BAY, ghi_dia=False, dang_ky_lich=lambda g: goi.append(1))
    assert goi == [] and not os.path.exists(bdk.duong_tu_xu_ly(goc))
    gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(), bay_gio=BAY, dang_ky_lich=lambda g: (True, "ok"))
    assert os.path.exists(bdk.duong_tu_xu_ly(goc))
    gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(tat=False), bay_gio=BAY, dang_ky_lich=lambda g: goi.append(2))
    assert goi == [] and json.load(io.open(bdk.duong_tu_xu_ly(goc), encoding="utf-8")) == {}
    # không kênh tu_chay thì cũng không đăng ký
    gac_tong.tu_xu_ly_viec_may(goc, _anh_lich(tu_chay=False), bay_gio=BAY, dang_ky_lich=lambda g: goi.append(3))
    assert goi == []


def test_so_lieu_studio_chi_bao_khi_cu_qua_72_gio(tmp_path):
    goc = str(tmp_path)
    duong = os.path.join(goc, "CHANNEL", "K1", "chi-so", "bang-tom-tat.csv")
    _ghi(duong, "a\n")
    k = {"ma": "K1", "tu_chay": True}
    bay = dt.datetime.now()
    for gio, co in ((60, False), (80, True)):
        t = (bay - dt.timedelta(hours=gio)).timestamp()
        os.utime(duong, (t, t))
        viec = bdk.viec_cua_ban(goc, anh={"kenh": [k]}, bay_gio=bay, gio_lich="02:00")
        assert bool([v for v in viec if v["khoa"].startswith("so-lieu-cu:")]) is co


# ═══ 1e. lỗi khởi tạo ngách tự thử lại ══════════════════════════════════════════

def test_loi_khoi_tao_tu_thu_lai_chi_bao_nguoi_sau_3_ngay(tmp_path):
    from core import khoi_tao_ngach as ktn

    goc = str(tmp_path)
    kq = ktn.KetQua()
    kq.ma_kenh = "KN"
    ktn._viec_tu_thu_lai(goc, kq, "nghien_cuu", "Nghiên cứu khởi động hỏng (x)")
    assert kq.tu_thu_lai and not kq.viec_cua_ban, "lần đầu: máy tự thử lại, không báo người"
    # sổ ghi ngày đầu = hôm nay; lùi ngày đầu 4 ngày → còn hỏng ≥ 3 ngày thì báo người
    duong = os.path.join(goc, "workspace", "khoi-tao-ngach", "loi-tu-thu-lai.json")
    du = json.load(io.open(duong, encoding="utf-8"))
    du["KN|nghien_cuu"] = (dt.date.today() - dt.timedelta(days=4)).isoformat()
    _ghi(duong, du)
    kq2 = ktn.KetQua()
    kq2.ma_kenh = "KN"
    ktn._viec_tu_thu_lai(goc, kq2, "nghien_cuu", "Nghiên cứu khởi động hỏng (x)")
    assert kq2.viec_cua_ban == ["Nghiên cứu khởi động hỏng (x)"] and not kq2.tu_thu_lai
    # lượt sau không còn lỗi → quên mốc
    kq3 = ktn.KetQua()
    kq3.ma_kenh = "KN"
    ktn._quen_loi_da_het(goc, kq3)
    assert "KN|nghien_cuu" not in json.load(io.open(duong, encoding="utf-8"))
