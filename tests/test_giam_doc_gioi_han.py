"""Giới hạn an toàn của giám đốc kênh: biên/bước, ngân sách tuần, nghỉ 14 ngày, 1 thí nghiệm / chỉ số,
chủ sửa tay, quay lui, luật Studio, chế độ. Kênh giả trong `tmp_path` — không đụng CHANNEL thật."""

from __future__ import annotations

import datetime as _dt
import io
import os

import pytest

from core.giam_doc import gioi_han as gh
from core.giam_doc import so_thi_nghiem as stn
from core.giam_doc.du_lieu import BangSo
from core.kenh import doc_yaml

BAY = _dt.datetime(2026, 10, 1, 12, 0)


def _bs(goc="", ma="A", **cai):
    return BangSo(goc=goc, ma_kenh=ma, bay_gio=BAY, cai=dict({"phut_muc_tieu": 15}, **cai))


def _so(nhat_ky=(), thi_nghiem=(), chu_giu=None):
    return {"nhat_ky": list(nhat_ky), "thi_nghiem": list(thi_nghiem), "trang_thai": {"chu_giu": chu_giu or {}}}


def _ts(khoa, gia_tri, **k):
    return dict({"loai": "tham_so", "khoa": khoa, "gia_tri": gia_tri}, **k)


def _luc(ngay_truoc):
    return (BAY - _dt.timedelta(days=ngay_truoc)).isoformat()


def _kenh(goc, ma="A", *dong):
    tm = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(tm, exist_ok=True)
    with io.open(os.path.join(tm, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(('ma: "{0}"'.format(ma),) + dong) + "\n")
    return os.path.join(tm, "kenh.yaml")


# ── biên + bước ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("khoa,cu,moi,duoc", [
    ("phut_muc_tieu", 15, 17, True), ("phut_muc_tieu", 15, 18, True), ("phut_muc_tieu", 15, 19, False),
    ("phut_muc_tieu", 11, 9, False), ("phut_muc_tieu", 15, 15, False), ("phut_muc_tieu", 15, 16.5, False),
    ("chien_luoc_tham_do", 20, 30, True), ("chien_luoc_tham_do", 20, 36, False), ("chien_luoc_tham_do", 30, 15, False),
    ("chien_luoc_tu_hoc", False, True, True), ("chien_luoc_tu_hoc", True, True, False),
    ("chien_luoc_tu_hoc", False, False, False),
    ("chien_luoc", "v7:0.5, vph:0.5", "v7:0.7, vph:0.3", True),
    ("chien_luoc", "v7:0.5, vph:0.5", "v7:0.9, vph:0.1", False),       # bước 0,4
    ("chien_luoc", "v7:0.2, vph:0.8", "v7:0.05, vph:0.95", False),     # ngoài biên 0,1–0,9
    ("chien_luoc", "v7:0.5, vph:0.5", "v7:0.5, mot_nut:0.5", False),   # đổi tập công thức
    ("chien_luoc", "tu_dong", "v7:0.5, vph:0.5", False),               # chưa khai ≥ 2 công thức
    ("luat_chon_tuan", "", "a | b | c", True), ("luat_chon_tuan", "", "a | b | c | d", False),
    ("luat_chon_tuan", "a", "a", False),
])
def test_bien_va_buoc(khoa, cu, moi, duoc):
    assert gh.kiem_gia_tri(khoa, cu, moi)[0] is duoc


def test_khoa_la_ngoai_tam_va_chu_cam():
    bs = _bs(giam_doc_khong_dung="phut_muc_tieu, chien_luoc")
    for khoa in ("ngan_sach_ngay", "tu_dang", "voice_id", "nhip_dang"):
        ok, ly = gh.kiem(_ts(khoa, 1), _so(), bs)
        assert not ok and "ngoài tầm" in ly
    assert not gh.kiem(_ts("khoa_la", 1), _so(), bs)[0]
    ok, ly = gh.kiem(_ts("phut_muc_tieu", 17), _so(), bs)
    assert not ok and "chủ cấm" in ly
    assert not gh.kiem({"loai": "xoa_kenh"}, _so(), bs)[0]


# ── ngân sách / nghỉ / thí nghiệm ───────────────────────────────────────────

def test_ngan_sach_2_tham_so_moi_tuan():
    bs = _bs()
    hai = [{"luc": _luc(2), "viec": "tham_so", "khoa": "chien_luoc_tham_do"},
           {"luc": _luc(3), "viec": "tham_so", "khoa": "luat_chon_tuan"}]
    ok, ly = gh.kiem(_ts("phut_muc_tieu", 17), _so(hai), bs)
    assert not ok and "ngân sách" in ly
    cu = [dict(d, luc=_luc(20)) for d in hai]
    assert gh.kiem(_ts("phut_muc_tieu", 17), _so(cu), bs)[0]
    assert gh.ngan_sach(_so(hai), BAY)["tham_so_con"] == 0


def test_khoa_vua_doi_nghi_14_ngay_ke_ca_sau_quay_lui():
    bs = _bs()
    for viec in ("tham_so", "quay_lui"):
        nk = [{"luc": _luc(10), "viec": viec, "khoa": "phut_muc_tieu"}]
        ok, ly = gh.kiem(_ts("phut_muc_tieu", 17), _so(nk), bs)
        assert not ok and "nghỉ" in ly
    nk = [{"luc": _luc(15), "viec": "tham_so", "khoa": "phut_muc_tieu"}]
    assert gh.kiem(_ts("phut_muc_tieu", 17), _so(nk), bs)[0]


def test_mot_thi_nghiem_mo_moi_chi_so():
    bs = _bs()
    tn = [{"id": "t", "trang_thai": "mo", "chi_so": "gio_xem_1k_hien_thi_52h"}]
    ok, ly = gh.kiem(_ts("phut_muc_tieu", 17, chi_so="gio_xem_1k_hien_thi_52h"), _so(thi_nghiem=tn), bs)
    assert not ok and "thí nghiệm mở" in ly
    tn[0]["trang_thai"] = "giu"
    assert gh.kiem(_ts("phut_muc_tieu", 17, chi_so="gio_xem_1k_hien_thi_52h"), _so(thi_nghiem=tn), bs)[0]


def test_chi_dao_han_va_do_dai():
    bs = _bs()
    assert gh.kiem({"loai": "chi_dao", "noi_dung": "Ưu tiên cụm X", "han_ngay": 7}, _so(), bs)[0]
    assert not gh.kiem({"loai": "chi_dao", "noi_dung": "x" * 201, "han_ngay": 7}, _so(), bs)[0]
    assert not gh.kiem({"loai": "chi_dao", "noi_dung": "x", "han_ngay": 30}, _so(), bs)[0]
    assert not gh.kiem({"loai": "chi_dao", "noi_dung": " ", "han_ngay": 7}, _so(), bs)[0]


# ── Studio ─────────────────────────────────────────────────────────────────

def _video(vid, **k):
    return dict({"id": vid, "ma_goi": "G1", "ket_luan": "truot", "thang": False, "lich_su_sua": []}, **k)


def test_luat_studio():
    bs = _bs(gio_dang="20:00")
    bs.video = [_video("ok"), _video("thang", thang=True, ket_luan="thang"), _video("cho", ket_luan=""),
                _video("sua", lich_su_sua=[{"luc": "x"}]), _video("ngoai", ma_goi="")]
    sv = lambda vid: {"loai": "viec_studio", "video_id": vid, "noi_dung": "tiêu đề"}  # noqa: E731
    assert gh.kiem(sv("ok"), _so(), bs)[0]
    for vid, chu in (("thang", "thắng"), ("cho", "chưa bị phán trượt"), ("sua", "một lần"), ("ngoai", "hồ sơ"),
                     ("khong", "không có video")):
        ok, ly = gh.kiem(sv(vid), _so(), bs)
        assert not ok and chu in ly, (vid, ly)
    nk = [{"luc": _luc(1), "viec": "viec_studio", "video_id": "ok"}]
    assert "một lần" in gh.kiem(sv("ok"), _so(nk), bs)[1]
    nk2 = [{"luc": _luc(1), "viec": "viec_studio", "video_id": x} for x in ("p", "q")]
    assert "Studio/tuần" in gh.kiem(sv("ok"), _so(nk2), bs)[1]
    ok, ly = gh.kiem(sv("ok"), _so(), bs, bay_gio=BAY.replace(hour=19, minute=20))
    assert not ok and "phiên" in ly
    assert gh.ap("", "A", sv("ok"), bs)["ket"] == "chi_goi_y"  # đợt 1: không vào hàng sửa


def test_gan_phien_qua_nua_dem():
    bs = _bs(nhip_dang="00:30, 12:00")
    assert gh.gan_phien(bs, BAY.replace(hour=23, minute=50)) == "00:30"
    assert gh.gan_phien(bs, BAY.replace(hour=10, minute=0)) == ""


# ── chế độ ─────────────────────────────────────────────────────────────────

def test_che_do_cap_v2_toi_da_goi_y(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "A-v2")
    assert gh.che_do(_bs(goc, "A", giam_doc="tu_ap")) == "goi_y"
    assert gh.che_do(_bs(goc, "A", giam_doc="tu_ap", giam_doc_cho_phep_ab="true")) == "tu_ap"
    assert gh.che_do(_bs(goc, "B", giam_doc="tu_ap")) == "tu_ap"
    assert gh.che_do(_bs(goc, "B")) == "tat" and gh.che_do(_bs(goc, "B", giam_doc="bua")) == "tat"


# ── áp, quay lui, chủ sửa tay ──────────────────────────────────────────────

def test_ap_va_quay_lui_tra_gia_tri_cu(tmp_path):
    goc = str(tmp_path)
    yaml = _kenh(goc, "A", "phut_muc_tieu: 15", "# ghi chú của chủ giữ nguyên")
    bs = _bs(goc, "A")
    kq = gh.ap(goc, "A", _ts("phut_muc_tieu", 17, chi_so="gx", co_mau=4, han_ngay=28, plugin="do_dai",
                             nen={"gia_tri": 4.0}), bs, ly_do_llm="thử 17", bay_gio=BAY)
    assert kq["ket"] == "da_ap" and doc_yaml(yaml)["phut_muc_tieu"] in (17, "17")
    assert "# ghi chú của chủ giữ nguyên" in io.open(yaml, encoding="utf-8").read()
    tn = stn.dang_mo(stn.doc(goc, "A"))[0]
    assert tn["viec"] == "do_dai" and tn["bien"] == {"loai": "tham_so", "khoa": "phut_muc_tieu", "cu": 15, "moi": 17}
    assert stn.doc_nhat_ky(goc, "A")[-1]["viec"] == "tham_so"
    gh.quay_lui(goc, "A", tn, ly_do="tụt", bay_gio=BAY)
    assert doc_yaml(yaml)["phut_muc_tieu"] in (15, "15")
    assert stn.doc(goc, "A")[0]["trang_thai"] == "quay_lui"
    assert gh.ngan_sach(stn.doc_so(goc, "A"), BAY)["khoa_nghi"]["phut_muc_tieu"] > BAY.isoformat()


def test_chu_sua_tay_giu_30_ngay(tmp_path):
    goc = str(tmp_path)
    yaml = _kenh(goc, "A", "phut_muc_tieu: 15")
    gh.ap(goc, "A", _ts("phut_muc_tieu", 17), _bs(goc, "A"), bay_gio=BAY)
    assert gh.chu_da_sua(goc, "A", _bs(goc, "A", phut_muc_tieu=17), bay_gio=BAY) == []
    with io.open(yaml, "w", encoding="utf-8") as tep:
        tep.write('ma: "A"\nphut_muc_tieu: 16\n')
    bs = _bs(goc, "A", phut_muc_tieu=16)
    assert gh.chu_da_sua(goc, "A", bs, bay_gio=BAY) == ["phut_muc_tieu"]
    so_ = stn.doc_so(goc, "A")
    so_["nhat_ky"] = []  # bỏ cò "nghỉ 14 ngày" để thấy riêng cò "chủ giữ"
    ok, ly = gh.kiem(_ts("phut_muc_tieu", 14), so_, bs, bay_gio=BAY + _dt.timedelta(days=20))
    assert not ok and "chủ đã sửa tay" in ly
    assert gh.kiem(_ts("phut_muc_tieu", 14), so_, bs, bay_gio=BAY + _dt.timedelta(days=31))[0]
    assert gh.chu_da_sua(goc, "A", bs, bay_gio=BAY) == []  # đã quên da_ghi → không báo lại


def _kenh_ngay(moi_ngay):
    ra, tong, n = [], 0.0, len(moi_ngay)
    ra.append({"luc": BAY - _dt.timedelta(days=n), "hien_thi": 0.0})
    for i, x in enumerate(moi_ngay):
        tong += x
        ra.append({"luc": BAY - _dt.timedelta(days=n - i - 1), "hien_thi": tong})
    return ra


def test_ly_do_quay_lui_ba_co():
    tn = {"id": "t", "bat_dau": _luc(8), "chi_so": "gx", "quay_lui_khi": {"tut_pct": 20}}
    dang = lambda ngay: [{"id": "v%d" % i, "dang_luc": BAY - _dt.timedelta(days=d)}  # noqa: E731
                         for i, d in enumerate(ngay)]
    bs = _bs()
    bs.kenh_ngay = _kenh_ngay([1000] * 16 + [400] * 8)
    bs.video = dang([1, 3, 5, 10, 12, 14, 16, 18, 20])
    assert "tụt" in gh.ly_do_quay_lui(bs, tn)
    bs.video = dang([10, 12, 14, 16, 18, 20])  # ngừng đăng 7 ngày → không phải lỗi thí nghiệm
    assert gh.ly_do_quay_lui(bs, tn) == ""
    assert gh.ly_do_quay_lui(bs, tn, bao_dong=True) == "sức khoẻ kênh báo động"
    kl = {"so": {"nen": 6.0, "moi": 4.0, "n": 3}}
    assert "tệ hơn nền" in gh.ly_do_quay_lui(bs, tn, ket_luan=kl)
    assert gh.ly_do_quay_lui(bs, tn, ket_luan={"so": {"nen": 6.0, "moi": 4.0, "n": 2}}) == ""
