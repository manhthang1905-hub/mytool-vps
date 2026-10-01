"""Xếp lịch nhiều khe/ngày + kho đệm (`core/xep_lich.py`, 29/09/2026).

Không mạng, không ví — mọi bài dùng `tmp_path`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from core import auto, ke_hoach_dang, xep_lich
from core.kenh import doc_kenh
from core.tu_chay import (_cua_so_san_xuat, _nhan_nuoi_luot_mo_coi, chay_mot_ngay)

NO_LOG = lambda *_a, **_k: None  # noqa: E731


def _ghi_kenh(goc, ma, **cai):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    mac_dinh = {"ma": ma, "ngon_ngu": "ja", "engine": "veo3", "phut_muc_tieu": 10}
    mac_dinh.update(cai)
    dong = []
    for k, v in mac_dinh.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, (int, float)):
            dong.append("{0}: {1}".format(k, v))
        elif isinstance(v, list):
            dong.append("{0}: [{1}]".format(k, ", ".join('"{0}"'.format(x) for x in v)))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    return thu_muc


def _ghi_ke_hoach(goc, ma, *dong_kv):
    hang = []
    for kv in dong_kv:
        d = {ten: "" for ten in ke_hoach_dang.COT}
        d.update(kv)
        hang.append([d[ten] for ten in ke_hoach_dang.COT])
    ke_hoach_dang.luu_bang(goc, ma, hang)


def _dong(goc, ma):
    cot, hang = ke_hoach_dang.doc_bang(goc, ma)
    return [dict(zip(cot, d)) for d in hang]


def _lam_kenh_san_sang(goc, ma):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(thu_muc, "nv"), exist_ok=True)
    with open(os.path.join(thu_muc, "nv", "nv1.png"), "wb") as tep:
        tep.write(b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(thu_muc, "style.yaml"), "w", encoding="utf-8") as tep:
        tep.write('image_style: "phong cách thử"\n')
    os.makedirs(os.path.join(thu_muc, "prompt"), exist_ok=True)
    for ten in ("2-viet.md", "7-canh.md"):
        with open(os.path.join(thu_muc, "prompt", ten), "w", encoding="utf-8") as tep:
            tep.write("nội dung mẫu\n")


def _chay_auto_het(luot, viec, **k):
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


# ── đọc cấu hình ─────────────────────────────────────────────────────────────


def test_chuan_hoa_nhip_nhieu_dang():
    assert xep_lich.chuan_hoa_nhip(["20:00", "12:00", "12:00"]) == ["12:00", "20:00"]
    assert xep_lich.chuan_hoa_nhip("20:00, 8:05") == ["08:05", "20:00"]
    assert xep_lich.chuan_hoa_nhip('["12:00","20:00"]') == ["12:00", "20:00"]
    assert xep_lich.chuan_hoa_nhip(720) == ["12:00"]  # PyYAML đọc 12:00 trần = 720
    assert xep_lich.chuan_hoa_nhip("25:00, abc") == []
    assert xep_lich.chuan_hoa_nhip(None) == []
    assert xep_lich.chuan_hoa_nhip(True) == []


def test_doc_kenh_nhip_dang_va_mac_dinh(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", gio_dang="20:00")
    k = doc_kenh(goc, "K1")
    assert k.nhip_dang == [] and k.kho_dem_ngay == 3 and k.bien_xu_ly_gio == 12.0
    assert k.video_toi_da_ngay == 0
    assert xep_lich.khe_cua_kenh(k) == ["20:00"]  # tương thích: thiếu nhip = [gio_dang]
    assert xep_lich.tran_video_ngay(k) == 1
    _ghi_kenh(goc, "K2", gio_dang="20:00", nhip_dang=["20:00", "12:00"], video_toi_da_ngay=4,
              kho_dem_ngay=2, tu_duyet=True)
    k2 = doc_kenh(goc, "K2")
    assert k2.nhip_dang == ["12:00", "20:00"]
    assert xep_lich.che_do_nhieu_khe(k2) is True
    assert xep_lich.tran_video_ngay(k2) == 4
    assert k2.kho_dem_ngay == 2


def test_nhip_dang_ghi_qua_ghi_cai_kenh_doc_lai_dung(tmp_path):
    from core.trung_tam import ghi_cai_kenh

    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", gio_dang="20:00", tu_duyet=True)
    ghi_cai_kenh(goc, "K1", nhip_dang="12:00, 20:00", kho_dem_ngay=3, video_toi_da_ngay=4)
    k = doc_kenh(goc, "K1")
    assert k.nhip_dang == ["12:00", "20:00"]
    assert k.video_toi_da_ngay == 4


def test_khong_tu_duyet_thi_khong_bat_che_do_moi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["12:00", "20:00"], tu_duyet=False)
    assert xep_lich.che_do_nhieu_khe(doc_kenh(goc, "K1")) is False


# ── khe trống sớm nhất ───────────────────────────────────────────────────────


def test_khe_trong_som_nhat_bien_12_gio(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["12:00", "20:00"], tu_duyet=True)
    k = doc_kenh(goc, "K1")
    # 23:00 → +12h = 11:00 hôm sau → khe 12:00 hôm sau
    assert xep_lich.khe_trong_som_nhat(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 23, 0)) \
        == ("30/09/2026", "12:00")
    # 09:00 → +12h = 21:00 → khe 12:00 hôm sau
    assert xep_lich.khe_trong_som_nhat(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 9, 0)) \
        == ("30/09/2026", "12:00")
    # 07:00 → +12h = 19:00 → 20:00 cùng ngày
    assert xep_lich.khe_trong_som_nhat(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 7, 0)) \
        == ("29/09/2026", "20:00")


def test_khe_trong_bo_qua_khe_da_co_ke_ca_da_dang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["12:00", "20:00"], tu_duyet=True)
    _ghi_ke_hoach(goc, "K1",
                  {"Mã gói": "K1-0007", "Ngày đăng": "30/09/2026", "Giờ đăng": "20:00",
                   "Sẵn sàng": "x", "Trạng thái đăng": "ĐÃ ĐĂNG", "Video ID": "abc"},
                  {"Mã gói": "K1-0008", "Ngày đăng": "30/09/2026", "Giờ đăng": "12:00",
                   "Sẵn sàng": "x"})
    k = doc_kenh(goc, "K1")
    assert xep_lich.khe_trong_som_nhat(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 20, 0)) \
        == ("01/10/2026", "12:00")


def test_khe_trong_kenh_khong_khai_gio(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", tu_duyet=True)
    assert xep_lich.khe_trong_som_nhat(goc, "K1", doc_kenh(goc, "K1")) == ("", "")


# ── kho đệm ─────────────────────────────────────────────────────────────────


def test_kho_dem_dem_khe_tuong_lai_va_goi_cho(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["12:00", "20:00"], tu_duyet=True, kho_dem_ngay=1)
    _ghi_ke_hoach(goc, "K1",
                  {"Mã gói": "A", "Ngày đăng": "28/09/2026", "Giờ đăng": "20:00",
                   "Sẵn sàng": "x", "Trạng thái đăng": "ĐÃ ĐĂNG"},       # quá khứ, đã đăng
                  {"Mã gói": "B", "Ngày đăng": "30/09/2026", "Giờ đăng": "20:00",
                   "Sẵn sàng": "x", "Trạng thái đăng": "ĐÃ ĐĂNG"},       # tương lai
                  {"Mã gói": "C", "Sẵn sàng": "x"})                          # chờ, chưa lịch
    k = doc_kenh(goc, "K1")
    kho = xep_lich.dem_kho_dem(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 14, 0))
    assert kho["khe_tuong_lai"] == ["B"] and kho["goi_cho"] == ["C"]
    assert kho["kho"] == 2 and kho["can"] == 2


def test_cua_so_kho_dem_thay_chan_cung(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["12:00", "20:00"], tu_duyet=True, kho_dem_ngay=1)
    _ghi_ke_hoach(goc, "K1", {"Mã gói": "B", "Ngày đăng": "30/09/2026", "Giờ đăng": "20:00",
                              "Sẵn sàng": "x"})  # CHƯA ĐĂNG — đường cũ sẽ chặn cứng
    k = doc_kenh(goc, "K1")
    mo, ly_do, tt = _cua_so_san_xuat(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 14, 0))
    assert mo is True and tt["che_do"] == "kho_dem" and tt["kho_dem"] == 1
    assert not tt.get("cho_nguoi")
    _ghi_ke_hoach(goc, "K1",
                  {"Mã gói": "B", "Ngày đăng": "30/09/2026", "Giờ đăng": "20:00", "Sẵn sàng": "x"},
                  {"Mã gói": "C", "Ngày đăng": "01/10/2026", "Giờ đăng": "12:00", "Sẵn sàng": "x"})
    mo, ly_do, tt = _cua_so_san_xuat(goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 14, 0))
    assert mo is False and "kho đệm đã đủ 2/2" in ly_do
    assert tt["mo_cua_san_xuat"] == "2026-09-30T20:00"


def test_cua_so_duong_cu_khi_khong_khai_nhip(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", gio_dang="20:00", tu_duyet=True)
    _ghi_ke_hoach(goc, "K1", {"Mã gói": "B", "Ngày đăng": "30/09/2026", "Giờ đăng": "20:00",
                              "Sẵn sàng": "x"})
    mo, _ly, tt = _cua_so_san_xuat(goc, "K1", doc_kenh(goc, "K1"),
                                   bay_gio=_dt.datetime(2026, 9, 29, 14, 0))
    assert mo is False and tt.get("cho_nguoi") is True  # y hệt trước


# ── xếp lại gói lỡ lịch ─────────────────────────────────────────────────────


def test_xep_lai_goi_lo_lich_chi_goi_chua_tai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["12:00", "20:00"], tu_duyet=True)
    _ghi_ke_hoach(goc, "K1",
                  {"Mã gói": "LO", "Ngày đăng": "28/09/2026", "Giờ đăng": "20:00", "Sẵn sàng": "x"},
                  {"Mã gói": "DA", "Ngày đăng": "28/09/2026", "Giờ đăng": "12:00", "Sẵn sàng": "x",
                   "Trạng thái đăng": "ĐÃ ĐĂNG"},
                  {"Mã gói": "DO", "Ngày đăng": "28/09/2026", "Giờ đăng": "10:00", "Sẵn sàng": "x",
                   "Trạng thái đăng": "ĐANG ĐĂNG · nháp x"},
                  {"Mã gói": "SO", "Ngày đăng": "28/09/2026", "Giờ đăng": "09:00", "Sẵn sàng": "x"},
                  {"Mã gói": "SAT", "Ngày đăng": "29/09/2026", "Giờ đăng": "13:50", "Sẵn sàng": "x"})
    k = doc_kenh(goc, "K1")
    doi = xep_lich.xep_lai_goi_lo_lich(
        goc, "K1", k, bay_gio=_dt.datetime(2026, 9, 29, 14, 0),
        so_video_id={"K1/SO": {"video_id": "zzz"}}, co_dang_do=False)
    assert doi == [("LO", "28/09/2026 20:00", "30/09/2026 12:00")]
    d = {x["Mã gói"]: x for x in _dong(goc, "K1")}
    assert (d["LO"]["Ngày đăng"], d["LO"]["Giờ đăng"]) == ("30/09/2026", "12:00")
    assert d["DA"]["Ngày đăng"] == "28/09/2026" and d["SO"]["Giờ đăng"] == "09:00"
    assert d["SAT"]["Giờ đăng"] == "13:50"  # mới lỡ 10' — để phiên kênh lo


def test_xep_lai_khong_lam_gi_khi_dang_dang_do(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", nhip_dang=["20:00"], tu_duyet=True)
    _ghi_ke_hoach(goc, "K1", {"Mã gói": "LO", "Ngày đăng": "28/09/2026", "Giờ đăng": "20:00",
                              "Sẵn sàng": "x"})
    assert xep_lich.xep_lai_goi_lo_lich(goc, "K1", doc_kenh(goc, "K1"),
                                        bay_gio=_dt.datetime(2026, 9, 29, 14, 0),
                                        so_video_id={}, co_dang_do=True) == []


# ── lượt đã bỏ không bị nhận nuôi lại ────────────────────────────────────────


def test_luot_da_bo_khong_bi_nhan_nuoi_lai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    luot = auto.moi_luot(goc, "K1", "0003", {"link": "https://youtu.be/AAAAAAAAAAA",
                                             "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)
    assert _nhan_nuoi_luot_mo_coi(goc, "K1", "2026-10-05", set()) == "0003"  # đối chứng
    goc2 = os.path.join(goc, "hai")
    _ghi_kenh(goc2, "K1")
    luot2 = auto.moi_luot(goc2, "K1", "0003", {"link": "https://youtu.be/AAAAAAAAAAA",
                                               "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot2)
    with open(os.path.join(luot2.thu_muc, "BO-VI-da-tu-phuc-hoi-3-lan.txt"), "w",
              encoding="utf-8") as tep:
        tep.write("bo")
    assert _nhan_nuoi_luot_mo_coi(goc2, "K1", "2026-10-05", set()) == ""


# ── tích hợp chay_mot_ngay: bàn giao xếp khe ≥ +12h, trần video/ngày ───────


def test_chay_mot_ngay_ban_giao_xep_khe_bien_12h(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", tu_duyet=True,
              gio_dang="20:00", nhip_dang=["12:00", "20:00"], voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    _ghi_ke_hoach(goc, "K1", {"Mã gói": "K1-0001", "Ngày đăng": "30/09/2026",
                              "Giờ đăng": "12:00", "Sẵn sàng": "x"})  # chưa tải — không chặn
    moi = [{"link": "https://youtu.be/JJJJJJJJJJJ", "tieu_de": "x", "kenh": "Z"}]
    goi = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi.append((ngay, gio))
        return "K1-0002", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=_dt.date(2026, 9, 29), on_log=NO_LOG,
        bay_gio=_dt.datetime(2026, 9, 29, 16, 0),
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=lambda g, k: {"moi": list(moi)},
        video_da_lam_nhom=lambda g, k: set(), tieu_de_da_lam_nhom=lambda g, k: [],
        dung_viec=lambda bc: {}, chay_auto=_chay_auto_het, ban_giao=ban_giao_gia)
    assert ket["ok"] is True, ket
    # 16:00 + 12h = 04:00 30/09 → 12:00 30/09 đã có → 20:00 30/09
    assert goi == [("30/09/2026", "20:00")]


def test_chay_mot_ngay_tran_video_toi_da_ngay(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", tu_duyet=True,
              nhip_dang=["12:00", "20:00"], video_toi_da_ngay=1, voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    thu_muc_so = os.path.join(goc, "CHANNEL", "K1", "tu-chay")
    os.makedirs(thu_muc_so, exist_ok=True)
    with open(os.path.join(thu_muc_so, "2026-09-29.json"), "w", encoding="utf-8") as tep:
        json.dump({"ngay": "2026-09-29", "kenh": "K1", "nhat_ky": [],
                   "runs": [{"ma_luot": "0001", "bo": True, "nguon": {"ma": "x"},
                             "san_xuat": {"da_chay": True}}]}, tep)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 29), on_log=NO_LOG,
        bay_gio=_dt.datetime(2026, 9, 29, 16, 0), chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=lambda g, k: {"moi": []})
    assert "đã đủ 1 video hôm nay" in ket["tom_tat"]


# ── nhịp ngày `chu_ky_dang_ngay` (01/10/2026 — giãn lịch đăng) ──────────────

def _kenh_thua(goc, ma="K2", chu_ky=2, **them):
    _ghi_kenh(goc, ma, tu_duyet=True, nhip_dang="05:00", chu_ky_dang_ngay=chu_ky, kho_dem_ngay=4,
              video_toi_da_ngay=1, **them)
    return doc_kenh(goc, ma)


def test_khe_trong_ton_trong_nhip_tinh_ca_so_may_dang(tmp_path):
    goc = str(tmp_path)
    k = _kenh_thua(goc)
    assert xep_lich.chu_ky_ngay(k) == 2
    # đã đăng 01/10 20:00 (kế hoạch) + một video đã HẸN 03/10 05:00 chỉ có trong sổ máy đăng
    _ghi_ke_hoach(goc, "K2", {"Mã gói": "K2-0001", "Ngày đăng": "01/10/2026", "Giờ đăng": "20:00",
                              "Sẵn sàng": "x", "Trạng thái đăng": "ĐÃ ĐĂNG"})
    os.makedirs(os.path.join(goc, "vm", "logs"))
    with open(os.path.join(goc, "vm", "logs", "so-video-id.json"), "w", encoding="utf-8") as tep:
        json.dump({"K2/K2-0002": {"video_id": "abc", "trang_thai": "xac-nhan", "lich": "03/10/2026 05:00"}}, tep)
    bay = _dt.datetime(2026, 10, 1, 17, 0)
    # 02/10 05:00 (cách 01/10 một ngày) và 03/10, 04/10 (cách 03/10 < 2 ngày) đều không hợp nhịp
    assert xep_lich.khe_trong_som_nhat(goc, "K2", k, bay_gio=bay) == ("05/10/2026", "05:00")
    # nhịp 1 ngày (mặc định) → đường cũ: khe trống sớm nhất
    k1 = _kenh_thua(goc, chu_ky=1)
    assert xep_lich.khe_trong_som_nhat(goc, "K2", k1, bay_gio=bay) == ("02/10/2026", "05:00")


def test_kho_dem_theo_nhip_ngay(tmp_path):
    goc = str(tmp_path)
    k = _kenh_thua(goc)
    assert xep_lich.dem_kho_dem(goc, "K2", k)["can"] == 2          # 4 ngày ở nhịp 2 ngày = 2 video
    assert xep_lich.dem_kho_dem(goc, "K2", _kenh_thua(goc, chu_ky=3))["can"] == 2   # ⌈4/3⌉
    assert xep_lich.dem_kho_dem(goc, "K2", _kenh_thua(goc, chu_ky=1))["can"] == 4   # đường cũ: 4 × 1 khe


def test_xep_lai_theo_nhip_va_chat_luong(tmp_path):
    goc = str(tmp_path)
    k = _kenh_thua(goc)
    _ghi_ke_hoach(goc, "K2",
                  {"Mã gói": "K2-0001", "Ngày đăng": "01/10/2026", "Giờ đăng": "20:00", "Sẵn sàng": "x",
                   "Trạng thái đăng": "ĐÃ ĐĂNG", "Video ID": "v1"},
                  {"Mã gói": "K2-0002", "Ngày đăng": "02/10/2026", "Giờ đăng": "12:00", "Sẵn sàng": "x"},
                  {"Mã gói": "K2-0003", "Ngày đăng": "02/10/2026", "Giờ đăng": "16:00", "Sẵn sàng": "x"})
    tc = os.path.join(goc, "CHANNEL", "K2", "tu-chay")
    os.makedirs(tc)
    with open(os.path.join(tc, "2026-10-01.json"), "w", encoding="utf-8") as tep:
        json.dump({"runs": [
            {"ban_giao": {"ma_goi": "K2-0002"}, "nguon": {"bien_tap": {"diem": 60, "hang": "TAM"}}},
            {"ban_giao": {"ma_goi": "K2-0003"}, "nguon": {"bien_tap": {"diem": 82, "hang": "TOT",
                                                                        "du_doan": {"ket_cuc": "thắng"}}}}]}, tep)
    assert xep_lich.diem_goi(goc, "K2", "K2-0003")[0] == 87.0
    doi = xep_lich.xep_lai_goi_lo_lich(goc, "K2", k, bay_gio=_dt.datetime(2026, 10, 1, 17, 0),
                                       so_video_id={}, co_dang_do=False)
    lich = {d["Mã gói"]: (d["Ngày đăng"], d["Giờ đăng"]) for d in _dong(goc, "K2")}
    # gói điểm cao (0003) lấy khe hợp nhịp sớm nhất, gói kia cách thêm 2 ngày; gói đã đăng đứng yên
    assert lich == {"K2-0001": ("01/10/2026", "20:00"), "K2-0003": ("03/10/2026", "05:00"),
                    "K2-0002": ("05/10/2026", "05:00")}
    assert {m for m, _c, _m in doi} == {"K2-0002", "K2-0003"}
    # lượt sau: không đổi gì nữa (ổn định)
    assert xep_lich.xep_lai_goi_lo_lich(goc, "K2", k, bay_gio=_dt.datetime(2026, 10, 1, 18, 0),
                                        so_video_id={}, co_dang_do=False) == []


def test_cong_nguon_dang_thua_chi_nhan_tot(tmp_path, monkeypatch):
    from core import tu_chay

    tam = [{"tieu_de": "t", "bien_tap": {"hang": "TAM", "diem": 80, "ly_do": "lý do đủ dài"}}]
    log = []
    assert tu_chay._cong_chat_luong(tam, log.append) == tam                       # luật cũ: TẠM ≥ 65 qua
    assert tu_chay._cong_chat_luong(tam, log.append, chi_tot="kho còn 1") == []   # đăng thưa, kho còn → chỉ TỐT
    goc = str(tmp_path)
    _kenh_thua(goc)
    assert tu_chay._chi_nhan_tot(goc, "K2") == ""                                  # kho cạn → luật cũ
    _ghi_ke_hoach(goc, "K2", {"Mã gói": "K2-0001", "Ngày đăng": "01/01/2099", "Giờ đăng": "05:00",
                              "Sẵn sàng": "x"})
    assert "kho đệm còn 1" in tu_chay._chi_nhan_tot(goc, "K2")
