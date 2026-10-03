"""Giám đốc kênh — phần NỐI vào mã sống (Agent B, 01/10/2026; `workspace/THIET-KE-GIAM-DOC.md` mục 4, 5, 7).

B0 ngưỡng thắng kênh ít video · B1 hồ sơ video (mốc giàu hơn, lịch sử sửa, thí nghiệm, bìa hạng nhì) +
`bia_theo_khuon` (`doi_boi`) · B2 khối chỉ đạo của biên tập viên (golden khi KHÔNG có chỉ đạo) +
`luat_chon_tuan` · B3 nhịp gác tổng + dòng/công tắc bảng điều khiển.

Mọi bài chạy trên `tmp_path` (kênh giả, mã video giả) — không đụng CHANNEL thật, không mạng, không Qt.
"""

from __future__ import annotations

import copy
import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import cong_thuc_v7 as v7  # noqa: E402
from core import ho_so_video as hv  # noqa: E402

BAY_GIO = dt.datetime(2026, 10, 1, 12, 0, 0)


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


# ── B0. ngưỡng thắng 48h ────────────────────────────────────────────────────

def _ds(*so48, them_khong_48h=0):
    ds = [v7.VideoMinh(ma="GDv{0:08d}".format(i), hien_thi_48h=h) for i, h in enumerate(so48)]
    ds += [v7.VideoMinh(ma="GDn{0:08d}".format(i)) for i in range(them_khong_48h)]
    return ds


def test_nguong_mot_video_48h_khong_doi_ba_lan_chinh_no_du_kenh_co_5_thu_muc():
    """Ca TL3-T7: 5 video có chi-so nhưng mới 1 video đủ 48h (15.707) — trước đây ngưỡng = 3 × 15.707."""
    ds = _ds(15707, them_khong_48h=4)
    assert v7.nguong_thang_48h(ds, v7.CAU_HINH_MAC_DINH) == 6000
    v7._danh_dau_thang(ds, v7.CAU_HINH_MAC_DINH)
    assert ds[0].thang is True


def test_nguong_tron_dan_sang_trung_vi_kenh_khi_n_tang():
    ch = v7.CAU_HINH_MAC_DINH
    # n = 2: w = (1/4)² → 0,9375 × 6.000 + 0,0625 × max(6.000, 3 × 9.599,5)
    hai = v7.nguong_thang_48h(_ds(190, 19009), ch)
    assert abs(hai - (0.9375 * 6000 + 0.0625 * 3 * 9599.5)) < 1e-6
    # n = 3: w = 0,25
    ba = v7.nguong_thang_48h(_ds(1000, 30000, 50000), ch)
    assert abs(ba - (0.75 * 6000 + 0.25 * 90000)) < 1e-6
    # n ≥ 5: y như trước — max(sàn, 3 × trung vị)
    assert v7.nguong_thang_48h(_ds(100, 158, 3500, 20000, 30000), ch) == 10500
    assert v7.nguong_thang_48h(_ds(100, 100, 100, 100, 7000), ch) == 6000
    assert v7.nguong_thang_48h(_ds(), ch) == 6000


def test_nguong_ngach_doc_tu_ngach_yaml(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\nnhom: "ngach-gia"\n')
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "ngach-gia", "ngach.yaml"),
         "mo_ta_ngach: thu\nnguong_thang_48h: 9000\n")
    ch, _ = v7.nap_cau_hinh(goc, "GDK", ghi_neu_thieu=False)
    assert ch["thang"]["nguong_ngach_48h"] == 9000
    assert v7.nguong_thang_48h(_ds(8000), ch) == 9000
    assert v7.nguong_thang_48h(_ds(100, 200, 300, 400, 30000), ch) == 6000  # đủ 5 video: ngưỡng riêng


def test_ket_qua_dung_chung_mot_cong_thuc_nguong():
    from core.chien_luoc import ket_qua

    ds = _ds(15707, them_khong_48h=4)
    assert ket_qua._nguong_thang(ds, v7.CAU_HINH_MAC_DINH) == v7.nguong_thang_48h(ds, v7.CAU_HINH_MAC_DINH)


# ── B1. hồ sơ video ─────────────────────────────────────────────────────────

def _ban_ghi(thu_muc, luc, imp, ctr, moc=56):
    from core.chi_so_ytb import BanGhi

    return BanGhi(video_id="GDvideo0001", tieu_de="Tiêu đề giả GD", moc_gio=moc, luc_chup=luc,
                  impressions=imp, ctr=ctr, views=imp * ctr / 100.0, avd_giay=300, avd_pct=40,
                  subs=12, watch_hours=55.5, traffic={"browse": 60.0, "related": 30.0, "search": 10.0},
                  thu_muc=thu_muc)


def _kenh_ho_so(tmp_path, monkeypatch, ban_ghi):
    goc = str(tmp_path)
    _ghi(hv.duong_tep_ho_so(goc, "GDK", "GDK-0001"),
         dict(hv._khung_ho_so("GDK", "GDK-0001"), tieu_de="Tiêu đề giả GD", video_id="GDvideo0001"))
    monkeypatch.setattr(hv._chi_so, "doc_kenh", lambda kenh, goc=None: list(ban_ghi))
    return goc


def test_cap_nhat_chi_so_ghi_ctr_trang_chu_nguon_sub_gio_xem(tmp_path, monkeypatch):
    tm = os.path.join(str(tmp_path), "chup", "56h")
    _ghi(os.path.join(tm, "traffic-type.csv"),
         "Traffic source,Impressions,Impressions click-through rate (%)\nBrowse features,9000,7.5\n")
    goc = _kenh_ho_so(tmp_path, monkeypatch, [_ban_ghi(tm, "2026-09-30 10:00", 12000, 6.0)])
    hv.cap_nhat_chi_so(goc, "GDK", bay_gio=BAY_GIO)
    m = hv.doc_ho_so(goc, "GDK", "GDK-0001")["chi_so"]["48h"]
    assert (m["ctr_trang_chu"], m["hien_thi_trang_chu"]) == (7.5, 9000)
    assert (m["pct_browse"], m["pct_de_xuat"], m["subs"], m["gio_xem"]) == (60.0, 30.0, 12, 55.5)
    assert hv.cap_nhat_chi_so(goc, "GDK", bay_gio=BAY_GIO)["cap_nhat_moc"] == 0  # idempotent


def test_cap_nhat_chi_so_bu_khoa_moi_cho_moc_cu_mot_lan(tmp_path, monkeypatch):
    goc = _kenh_ho_so(tmp_path, monkeypatch, [_ban_ghi("", "2026-09-30 10:00", 12000, 6.0)])
    hs = hv.doc_ho_so(goc, "GDK", "GDK-0001")
    hs["chi_so"] = {"48h": {"impressions": 12000, "ctr": 6.0, "luc_chup": "2026-09-30 10:00", "moc_gio_that": 56}}
    _ghi(hv.duong_tep_ho_so(goc, "GDK", "GDK-0001"), hs)
    assert hv.cap_nhat_chi_so(goc, "GDK", bay_gio=BAY_GIO)["cap_nhat_moc"] == 1
    assert "pct_browse" in hv.doc_ho_so(goc, "GDK", "GDK-0001")["chi_so"]["48h"]
    assert hv.cap_nhat_chi_so(goc, "GDK", bay_gio=BAY_GIO)["cap_nhat_moc"] == 0


def test_ghi_sua_va_do_truoc_sau_bang_hieu_hai_ban_chup(tmp_path, monkeypatch):
    ds = [_ban_ghi("", "2026-09-30 10:00", 2000, 3.0)]
    goc = _kenh_ho_so(tmp_path, monkeypatch, ds)
    assert hv.ghi_sua(goc, "GDK", "KHONG-CO", loai="tieu_de", cu="a", moi="b") is None
    hv.cap_nhat_chi_so(goc, "GDK", bay_gio=BAY_GIO)
    muc = hv.ghi_sua(goc, "GDK", "GDK-0001", loai="tieu_de", cu="cũ", moi="mới", thi_nghiem="tn-1",
                     bay_gio=dt.datetime(2026, 9, 30, 12, 0))
    assert muc["moc_truoc"]["impressions"] == 2000 and muc["doi_boi"] == "giam_doc"
    # bản chụp sau: 3.000 hiển thị thêm, CTR cộng dồn 4,2% → CTR riêng phần sau = (5000×4,2 − 2000×3)/3000 = 5,0
    ds.append(_ban_ghi("", "2026-10-01 10:00", 5000, 4.2, moc=80))
    hv.cap_nhat_chi_so(goc, "GDK", bay_gio=BAY_GIO)
    do = hv.doc_ho_so(goc, "GDK", "GDK-0001")["lich_su_sua"][0]["do"]
    assert do["du"] is True and do["truoc"]["ctr"] == 3.0
    assert do["sau"] == {"hien_thi": 3000, "ctr": 5.0}


def test_do_truoc_sau_chua_du_500_hien_thi_moi_phia():
    muc = {"moc_truoc": {"impressions": 400, "ctr": 3.0, "luc_chup": "2026-09-30 10:00"}}
    do = hv.do_truoc_sau(muc, {"impressions": 2000, "ctr": 4.0, "luc_chup": "2026-10-01 10:00"})
    assert do["du"] is False and do["sau"]["hien_thi"] == 1600


def test_tao_ho_so_chep_bia_hang_nhi_va_gan_thi_nghiem_dang_mo(tmp_path):
    from core.auto import duong_luot
    from core.giam_doc import so_thi_nghiem as stn

    goc = str(tmp_path)
    tm = os.path.join(duong_luot(goc, "GDK", "0001"), "7-thumbnail")
    _ghi(os.path.join(duong_luot(goc, "GDK", "0001"), "1-tieu-de.txt"), "TITLE: X\nTHUMB: Y\n")
    os.makedirs(tm, exist_ok=True)
    for so_ in (1, 2, 3):
        with io.open(os.path.join(tm, "thumb_{0:03d}.png".format(so_)), "wb") as tep:
            tep.write(b"\xff\xd8\xff\xe0BIA" + bytes([so_]))
    with io.open(os.path.join(tm, "CHON-thumb_002.jpg"), "wb") as tep:
        tep.write(b"\xff\xd8\xff\xe0BIA\x02")
    _ghi(os.path.join(tm, "chon-bia.json"), {
        "chon": {"so": 2, "tep": "CHON-thumb_002.jpg", "chon_boi": "ai", "tong_diem": 80},
        "ung_vien": [{"so": 1, "tong_diem": 70, "kieu": "a", "loai": ""},
                     {"so": 2, "tong_diem": 80, "kieu": "b", "loai": ""},
                     {"so": 3, "tong_diem": 75, "kieu": "c", "loai": "chữ sai"}]})
    tn = stn.mo(goc, "GDK", viec="do_dai", gia_thuyet="thử", bien={"loai": "tham_so", "khoa": "phut_muc_tieu",
                "cu": 15, "moi": 17}, chi_so="gio_xem_1k", nen={}, co_mau=4, han_ngay=21, ly_do_llm="",
                tut_pct=20, bay_gio=BAY_GIO)
    hv.tao_ho_so(goc, "GDK", "0001", "GDK-0001")
    hs = hv.doc_ho_so(goc, "GDK", "GDK-0001")
    assert hs["bia_2"]["so"] == 1 and hs["bia_2"]["tep"] == "thumb_001.png"  # tấm 3 bị loại
    with io.open(hv.duong_bia_2_ho_so(goc, "GDK", "GDK-0001"), "rb") as tep:
        assert tep.read().endswith(b"BIA\x01")
    assert hs["thi_nghiem"] == tn["id"] and hs["lich_su_sua"] == []


def test_bia_theo_khuon_khong_coi_bia_giam_doc_doi_la_bia_tay(tmp_path, monkeypatch):
    from core import bia_theo_khuon as btk

    monkeypatch.setattr(btk, "khac_bia_tool", lambda a, b: 99.0)  # ảnh YouTube luôn "khác" bìa tool
    goc = str(tmp_path)
    for ma, sua in (("GDK-0001", True), ("GDK-0002", False)):
        hs = dict(hv._khung_ho_so("GDK", ma), video_id="GDvid" + ma[-4:] + "xx",
                  thumbnail={"tep": "CHON-thumb_001.jpg", "nhom": "khuon"},
                  chi_so={"48h": {"impressions": 5000, "ctr": 6.0, "luc_chup": "2026-09-29 10:00",
                                  "moc_gio_that": 48}})
        if sua:
            hs["lich_su_sua"] = [{"luc": "2026-09-30T10:00:00", "loai": "bia", "doi_boi": "giam_doc"}]
        _ghi(hv.duong_tep_ho_so(goc, "GDK", ma), hs)
    hoc = btk.hoc_sau_video(goc, "GDK", {"ctr": 5.0, "video_id": "khac"},
                            anh_that_cua=lambda vid: "co-anh")
    theo = {d["ma_goi"]: d for d in hoc["nhat_ky"]}
    assert theo["GDK-0002"].get("bia_tay") is True  # khác bìa, không ai ghi sửa → bìa tay như cũ
    # giám đốc đổi bìa SAU mốc 48h → không phải bìa tay, số 48h vẫn tính cho bìa tool chọn
    assert theo["GDK-0001"].get("doi_boi") == "giam_doc" and not theo["GDK-0001"].get("bia_tay")
    assert theo["GDK-0001"]["ket_qua"] == "giu"


# ── B2. chỉ đạo của giám đốc trong lời nhắc biên tập ────────────────────────

_BOI_CANH = {"muc_tieu": "MT", "dinh_vi": "DV", "khan_gia": "KG", "video_minh": "VM", "video_nhom": "VN",
             "insight_nhom": "IN", "bai_hoc": "BH", "xu_huong": "XH", "da_lam": "DL", "tu_sua": "TS",
             "_ma_khan_gia_xem": ""}
_UV = [{"tieu_de": "nguồn {x}", "kenh": "k", "view": 1000, "noi_dung": "nd"}]


def test_khong_chi_dao_loi_nhac_giong_tung_byte_ban_cu():
    from core import bien_tap_content as btc

    cu = btc.DE_BAI.format(so_uv=1, so_chon=2, thang=btc._ngan_so(btc.NGUONG_THANG_48H),
                           truot=btc._ngan_so(btc.NGUONG_TRUOT_48H), ung_vien=btc._khoi_ung_vien(_UV),
                           **{k: v for k, v in _BOI_CANH.items() if not k.startswith("_")})
    assert btc.dung_loi_nhac(dict(_BOI_CANH), _UV, 2) == cu
    gon = dict(_BOI_CANH, _de_bai=btc.DE_BAI_GON, bai_hoc_kenh="b", nguon_giu_roi="n", ngon_ngu="tiếng Nhật",
               khan_gia_mo_ta="k", ctr_thang="5%", ctr_truot="3%", ctr_tot="5%", luat_ngach="    - l",
               thang="6.000", truot="1.800", khoi_nhom="")
    tra_loi = btc.DE_BAI[btc.DE_BAI.index("═══ TRẢ LỜI ═══"):]
    cu_gon = (btc.DE_BAI_GON_KHUON + tra_loi).format(
        so_uv=1, so_chon=2, ung_vien=btc._khoi_ung_vien(_UV), **{k: v for k, v in gon.items() if not k.startswith("_")})
    assert btc.dung_loi_nhac(gon, _UV, 2) == cu_gon


def test_co_chi_dao_thi_them_khoi_truoc_ung_vien(tmp_path):
    from core import bien_tap_content as btc
    from core.giam_doc import du_lieu

    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\nluat_chon_tuan: "Ưu tiên cụm IQ {thử}"\n')
    _ghi(os.path.join(du_lieu.thu_muc_giam_doc(goc, "GDK"), "chi-dao.json"), {"chi_dao": [
        {"noi_dung": "Dồn cụm trí tuệ", "het_han": "2026-10-08T00:00:00"},
        {"noi_dung": "đã hết hạn", "het_han": "2026-09-01T00:00:00"}]})
    khoi = btc._khoi_chi_dao(goc, "GDK", BAY_GIO)
    assert "Dồn cụm trí tuệ (tới 2026-10-08)" in khoi and "đã hết hạn" not in khoi
    assert "Luật chọn tuần này: Ưu tiên cụm IQ {thử}" in khoi
    chu = btc.dung_loi_nhac(dict(_BOI_CANH, chi_dao=khoi), _UV, 2)
    i, j = chu.index(btc.TIEU_DE_CHI_DAO), chu.index("═══ ỨNG VIÊN (thứ tự của công thức) ═══")
    assert i < j and "{thử}" in chu
    assert btc._khoi_chi_dao(str(tmp_path / "trong"), "GDK", BAY_GIO) == ""


def test_dung_boi_canh_khong_them_khoa_khi_khong_co_chi_dao(tmp_path, monkeypatch):
    from core import bien_tap_content as btc

    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\n')
    assert "chi_dao" not in btc.dung_boi_canh(goc, "GDK", bay_gio=BAY_GIO)


def test_ngu_canh_doc_luat_chon_tuan(tmp_path):
    from core.chien_luoc import ngu_canh

    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\nluat_chon: "gốc"\n')
    nc = ngu_canh.dung(goc, "GDK", co_v7=False, bay_gio=BAY_GIO)
    assert nc.luat_chon == ["gốc"] and nc.luat_chon_tuan == []
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\nluat_chon: "gốc"\nluat_chon_tuan: "a | b"\n')
    nc = ngu_canh.dung(goc, "GDK", co_v7=False, bay_gio=BAY_GIO)
    assert nc.luat_chon == ["gốc", "a", "b"] and nc.luat_chon_tuan == ["a", "b"]


# ── chế độ bóng: dự đoán + tự chấm ──────────────────────────────────────────

def test_du_doan_giu_lan_dau_va_tu_cham_khi_video_co_ket_luan(tmp_path):
    from core.giam_doc import so_thi_nghiem as stn

    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\n')
    assert stn.ghi_du_doan(goc, "GDK", [{"video_id": "GDvideo0001", "ket": "thang"},
                                        {"video_id": "GDvideo0002", "ket": "truot"}], bay_gio=BAY_GIO) == 2
    assert stn.ghi_du_doan(goc, "GDK", [{"video_id": "GDvideo0001", "ket": "truot"}]) == 0  # không đoán lại
    tc = stn.cham_du_doan(goc, "GDK", {"GDvideo0001": "thang", "GDvideo0002": ""}, bay_gio=BAY_GIO)
    assert (tc["tong"], tc["dung"], tc["cho"]) == (1, 1, 1)
    tc = stn.cham_du_doan(goc, "GDK", {"GDvideo0002": "thang"})
    assert (tc["tong"], tc["dung"], tc["moi"]) == (2, 1, 1)


def test_doc_ket_qua_chi_giu_du_doan_cho_video_dang_cho():
    from core.giam_doc import quan_ly

    tho = json.dumps({"chan_doan": "x", "chon": [], "du_doan": [
        {"video_id": "GDvideo0001", "ket": "thang", "ly_do": "a"},
        {"video_id": "GDvideo0009", "ket": "truot"}, {"video_id": "GDvideo0001", "ket": "truot"},
        {"video_id": "GDvideo0002", "ket": "vua"}]})
    kq = quan_ly.doc_ket_qua(tho, [], [], 2, {"GDvideo0001", "GDvideo0002"})
    assert kq["du_doan"] == [{"video_id": "GDvideo0001", "ket": "thang", "ly_do": "a"}]
    assert "du_doan" in quan_ly.DANG_TRA_LOI


# ── B3. gác tổng + bảng điều khiển ──────────────────────────────────────────

def _kenh_bat(goc, che_do="goi_y"):
    _ghi(os.path.join(goc, "CHANNEL", "GDK", "kenh.yaml"), 'ma: "GDK"\ngiam_doc: "{0}"\n'.format(che_do))


def test_kiem_ket_bao_sau_6_gio_den_han_lien(tmp_path):
    import core.giam_doc as gd

    goc = str(tmp_path)
    _kenh_bat(goc)
    assert gd.kiem_ket(goc, bay_gio=dt.datetime(2026, 10, 1, 1, 0)) == []  # ghi mốc thấy đến hạn
    assert gd.kiem_ket(goc, bay_gio=dt.datetime(2026, 10, 1, 6, 30)) == []
    ket = gd.kiem_ket(goc, bay_gio=dt.datetime(2026, 10, 1, 7, 5))
    assert [k["ma"] for k in ket] == ["GDK"] and ket[0]["gio"] >= 6
    gd.stn.ghi_trang_thai(goc, "GDK", ngay_chay="2026-10-01")
    assert gd.kiem_ket(goc, bay_gio=dt.datetime(2026, 10, 1, 8, 0)) == []  # đã chạy → xoá mốc
    assert gd.kiem_ket(goc, bay_gio=dt.datetime(2026, 10, 2, 1, 0)) == []  # ngày mới: mốc mới


def test_gac_tong_su_co_giam_doc_ket_va_viec_cua_ban(tmp_path):
    import core.giam_doc as gd
    from core import gac_tong
    from core.giam_doc import bao_cao, du_lieu

    goc = str(tmp_path)
    _kenh_bat(goc)
    gd.kiem_ket(goc, bay_gio=dt.datetime(2026, 10, 1, 0, 30))
    _ghi(os.path.join(du_lieu.thu_muc_giam_doc(goc, "GDK"), bao_cao.TEP_BAO_CAO_JSON),
         {"luc": "2026-10-01T00:20:00", "che_do": "goi_y", "viec_cua_ban": ["Đổi tiêu đề video A"]})
    sc = gac_tong.kiem_giam_doc(goc, bay_gio=dt.datetime(2026, 10, 1, 7, 0))
    loai = sorted(s["loai"] for s in sc)
    assert loai == ["giam_doc_ket", "giam_doc_viec"]
    viec = next(s for s in sc if s["loai"] == "giam_doc_viec")
    assert viec["dedupe_khoa"].startswith("giam_doc:viec:GDK:") and viec["muc"] == "nhac"
    # lọc lặp của gác tổng: việc của NGƯỜI (04/10/2026) chỉ báo lại 1 lần / ngày, không phải mỗi 4 giờ
    bg = dt.datetime(2026, 10, 1, 7, 0)
    assert len(gac_tong._loc_lap_su_co(goc, [viec], bg)) == 1
    assert gac_tong._loc_lap_su_co(goc, [viec], bg + dt.timedelta(hours=3)) == []
    assert gac_tong._loc_lap_su_co(goc, [viec], bg + dt.timedelta(hours=4, minutes=1)) == []
    assert gac_tong._loc_lap_su_co(goc, [viec], bg + dt.timedelta(hours=23)) == []
    assert len(gac_tong._loc_lap_su_co(goc, [viec], bg + dt.timedelta(hours=24, minutes=1))) == 1
    _kenh_bat(goc, "tat")
    assert gac_tong.kiem_giam_doc(goc, bay_gio=dt.datetime(2026, 10, 1, 7, 0)) == []


def test_bang_dieu_khien_dong_giam_doc_cong_tac_va_viec(tmp_path, monkeypatch):
    from core import bang_dieu_khien as bdk
    from core.giam_doc import bao_cao, du_lieu

    goc = str(tmp_path)
    _kenh_bat(goc, "tat")
    assert bdk.giam_doc_the(goc, "GDK") == {"che_do": "tat", "cau": "", "bao_cao": ""}
    ghi = {}
    monkeypatch.setattr(bdk.tt, "ghi_cai_kenh", lambda g, m, **kv: ghi.update(kv))
    bdk.doi_giam_doc(goc, "GDK", "goi_y")
    assert ghi == {"giam_doc": "goi_y"}
    try:
        bdk.doi_giam_doc(goc, "GDK", "lung_tung")
        raise AssertionError("phải ném lỗi")
    except ValueError:
        pass
    _kenh_bat(goc, "goi_y")
    tm = du_lieu.thu_muc_giam_doc(goc, "GDK")
    _ghi(os.path.join(tm, bao_cao.TEP_BAO_CAO_JSON), {"luc": BAY_GIO.isoformat(), "che_do": "goi_y",
         "chan_doan": "CTR trang chủ 8,9% tốt, hiển thị yếu.", "viec_cua_ban": ["Quyết định lớn chờ bạn duyệt: x", "Xem Studio"],
         "tu_cham": {"tong": 2, "dung": 1}})
    _ghi(os.path.join(tm, bao_cao.TEP_BAO_CAO_MD), "# Báo cáo\n")
    the = bdk.giam_doc_the(goc, "GDK")
    assert the["che_do"] == "goi_y" and the["bao_cao"].endswith("BAO-CAO-TUAN.md")
    assert "CTR trang chủ 8,9%" in the["cau"] and "đoán đúng 1/2" in the["cau"]
    monkeypatch.setattr(bdk, "dong_may", lambda *a, **kw: {"vi": {"muc": bdk.TOT, "so_ngay_con_chay": None},
                                                           "o_dia": {"muc": bdk.TOT, "con_gb": None}})
    viec = bdk.viec_cua_ban(goc, anh={"kenh": [{"ma": "GDK"}]}, bay_gio=BAY_GIO, gio_lich="02:00")
    gd = [v for v in viec if v["khoa"].startswith("giam-doc:GDK:")]
    assert len(gd) == 1 and gd[0]["chu"] == "Giám đốc kênh: Quyết định lớn chờ bạn duyệt: x"
    # "Xem Studio" chỉ là gợi ý → sang Đội AI nói, không nằm ở Việc của bạn
    assert [x["cau"] for x in bdk.goi_y_giam_doc(goc, "GDK")] == ["Xem Studio"]
    bdk.danh_dau_xong(goc, gd[0]["khoa"])
    viec = bdk.viec_cua_ban(goc, anh={"kenh": [{"ma": "GDK"}]}, bay_gio=BAY_GIO, gio_lich="02:00")
    assert not [v for v in viec if v["khoa"].startswith("giam-doc:")]


def test_the_kenh_cong_tac_ba_nac_bao_hanh_dong():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    from ui_qt.trang_bang_dieu_khien import TheKenhLon

    bam = []
    the = TheKenhLon("GDK", lambda *a: None, lambda ma, hd: bam.append((ma, hd)))
    the.nap({"ma": "GDK", "giam_doc": {"che_do": "goi_y", "cau": "Giám đốc kênh (…): ổn.", "bao_cao": "x.md"}})
    assert bam == [] and the._o_giam_doc.currentData() == "goi_y"
    assert the._nut_bao_cao.isEnabled() and not the._nhan_giam_doc.isHidden()
    the._o_giam_doc.setCurrentIndex(the._o_giam_doc.findData("tu_ap"))
    assert bam == [("GDK", "giam_doc=tu_ap")]
    the._nut_bao_cao.click()
    assert bam[-1] == ("GDK", "bao_cao_giam_doc")
    the.nap({"ma": "GDK"})
    assert the._o_giam_doc.currentData() == "tat" and not the._nut_bao_cao.isEnabled()


def test_che_do_goi_y_bong_khong_ap_gi_chi_ghi_se_lam_va_du_doan(tmp_path):
    import re

    import core.giam_doc as gd
    from core.giam_doc import bao_cao
    from core.kenh import doc_yaml
    from tests.test_giam_doc_plugin import dung_kenh_mau

    goc = str(tmp_path)
    dung_kenh_mau(goc)
    p = os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml")
    _ghi(p, io.open(p, encoding="utf-8").read().replace("giam_doc: tu_ap", "giam_doc: goi_y"))
    truoc = doc_yaml(p)

    def llm(ln, mo_hinh="", khoa="", toi_da_token=0):
        chon = [{"id": i, "ly_do": "thử", **({"noi_dung": "tiêu đề mới"} if loai == "viec_studio" else {})}
                for i, loai in re.findall(r"^(d\d+) \[\w+/(\w+)\]", ln, flags=re.M)]
        cho = re.findall(r"^- (GDvideo\d{4}) .*→ chờ", ln, flags=re.M)
        return json.dumps({"chan_doan": "Cổng hiển thị yếu.", "chon": chon, "tuan_toi": "đo tiếp",
                           "du_doan": [{"video_id": v, "ket": "truot", "ly_do": "x"} for v in cho]})

    kq = gd.chay_kenh(goc, "GD1", goi_chat=llm, tuan=True)
    assert kq.che_do == "goi_y" and kq.se_lam and not [x for x in kq.da_lam if x.get("ket") == "da_ap"]
    assert doc_yaml(p) == truoc  # không đổi kenh.yaml
    tm = os.path.join(goc, "CHANNEL", "GD1", "giam-doc")
    assert not os.path.exists(os.path.join(tm, "chi-dao.json"))  # chỉ đạo không vào biên tập viên
    assert gd.stn.dang_mo(gd.stn.doc(goc, "GD1")) == []
    nk = gd.stn.doc_nhat_ky(goc, "GD1")
    assert nk and all(d["viec"] in ("goi_y", "chu_sua", "luot") for d in nk)
    md = io.open(os.path.join(tm, bao_cao.TEP_BAO_CAO_MD), encoding="utf-8").read()
    assert "## Sẽ làm (chế độ gợi ý — CHƯA áp gì)" in md
    bc = json.load(io.open(os.path.join(tm, bao_cao.TEP_BAO_CAO_JSON), encoding="utf-8"))
    assert bc["se_lam"] and bc["che_do"] == "goi_y"
    if kq.tu_cham.get("moi_doan"):
        assert os.path.isfile(os.path.join(tm, gd.stn.TEP_DU_DOAN))


# ── B5. mắt cào máy một kênh ────────────────────────────────────────────────

def test_thu_muc_tien_ich_may_mot_kenh_dung_thu_muc_rieng(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agent_gd_noi", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm", "agent.py"))
    ag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ag)
    ag.THU_MUC_TIEN_ICH = str(tmp_path / "tien-ich")
    mot = {"kenh": "GDK"}
    assert ag._thu_muc_tien_ich_kenh(mot) == os.path.join(ag.THU_MUC_TIEN_ICH, "GDK")
    assert ag._thu_muc_tien_ich_kenh({}) == ag.THU_MUC_TIEN_ICH
    # máy một kênh nếp cũ: đã có mắt cào PHẲNG mà chưa có bản riêng → giữ phẳng (không đổi ID extension)
    _ghi(os.path.join(ag.THU_MUC_TIEN_ICH, "manifest.json"), "{}")
    assert ag._thu_muc_tien_ich_kenh(mot) == ag.THU_MUC_TIEN_ICH
    _ghi(os.path.join(ag.THU_MUC_TIEN_ICH, "GDK", "manifest.json"), "{}")
    assert ag._thu_muc_tien_ich_kenh(mot) == os.path.join(ag.THU_MUC_TIEN_ICH, "GDK")


def test_moi_luot_ghi_mot_dong_nhat_ky_ke_ca_khong_chon_gi(tmp_path):
    import core.giam_doc as gd
    from tests.test_giam_doc_plugin import dung_kenh_mau

    goc = str(tmp_path)
    dung_kenh_mau(goc)
    p = os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml")
    _ghi(p, io.open(p, encoding="utf-8").read().replace("giam_doc: tu_ap", "giam_doc: goi_y"))
    gd.chay_kenh(goc, "GD1", goi_chat=lambda *a, **k: json.dumps({"chan_doan": "Ổn.", "chon": []}))
    nk = [d for d in gd.stn.doc_nhat_ky(goc, "GD1") if d["viec"] == "luot"]
    assert len(nk) == 1 and nk[0]["sau"]["chon"] == 0 and nk[0]["ly_do_llm"] == "Ổn."
