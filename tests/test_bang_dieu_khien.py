"""Lõi dữ liệu thuần của Bảng điều khiển (`core/bang_dieu_khien.py`, Việc 1,
`workspace/THIET-KE-BANG-DIEU-KHIEN.md`).

`tmp_path` cho mọi ca — không đụng gốc MyTool thật, không dựng PyQt5. Dùng lại
`_kenh`, `_ghi_json`, `_ke_hoach`, `BAY_GIO` của `tests/test_trung_tam.py` để
dựng dữ liệu giả, đúng nếp bài kiểm cũ.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from test_trung_tam import BAY_GIO, _ghi, _ghi_json, _ke_hoach, _kenh

from core import bang_dieu_khien as bdk
from core.money import MICRO_PER_VND


# ── Dựng dữ liệu tối giản cho viec_cua_ban / anh_bang (không cần anh_chup đầy đủ) ──


def _k(ma: str = "K1", **over) -> dict:
    base = {
        "ma": ma, "ten": ma, "tep": "", "nhom": "",
        "tu_chay": True, "trong_vm": False, "tu_duyet": False, "tu_don": False,
        "gio_dang": "20:00", "ngan_sach_ngay": 150000,
        "bay_gio": {"chu": "Hôm nay chưa chạy", "muc": "nghi", "chi_tiet": ""},
        "video": {"tieu_de": "", "ma_luot": "", "ma_goi": ""},
        "dang_luc": "", "bay_ngay": {}, "ypp": {},
        "tien": {"hom_nay": 0, "tran": 150000},
        "luot": {"khau": []}, "ke_hoach": [], "nhat_ky": [], "phien": {},
        "dang_chay": False,
    }
    base.update(over)
    return base


def _anh(kenh: list, **over) -> dict:
    base = {"kenh": kenh, "kenh_khac": [], "o_dia": {"con_gb": 100.0},
            "tien": {"hom_nay": 0, "thang": 0}}
    base.update(over)
    return base


# ═══════════════════════════════════════════════════════════════════════════
# Chuyển từ ui_qt/trang_dieu_khien.py — vẫn phải đúng y hệt qua core.
# ═══════════════════════════════════════════════════════════════════════════


def test_gon_dong_nhat_ky_bo_vet_loi_ky_thuat():
    cau = bdk.gon_dong_nhat_ky(
        "Dừng ở Viết kịch bản: không lấy được lời thoại "
        "(FileNotFoundError: Could not find module 'C:\\\\a\\\\ctranslate2.dll')")
    assert "FileNotFoundError" not in cau
    assert cau.startswith("Dừng ở Viết kịch bản")


def test_tien_do_nhat_ky_khong_nham_ngay_thang():
    assert bdk.tien_do_nhat_ky(["[116/141] Đang tạo ảnh"]) == "116/141"
    assert bdk.tien_do_nhat_ky(["Đăng ngày 22/09/2026", "xong"]) == ""
    assert bdk.tien_do_nhat_ky([]) == ""


def test_cau_tinh_trang_cho_duyet():
    assert bdk.cau_tinh_trang(
        _k(bay_gio={"chu": "Chờ duyệt", "muc": "cho"})) == "Xong, chờ bạn hẹn giờ đăng"


def test_cau_tinh_trang_nghi_nhung_da_hen_tuong_lai():
    """Dữ liệu thật 29/09/2026 (TL1-T7/TL3-T7): video đã hẹn 30/09 20:00 —
    `bay_gio.chu` báo "Nghỉ hôm nay" (trung_tam chỉ xét kế hoạch ĐÚNG hôm
    nay) nhưng câu hiện ra phải nói rõ đã hẹn, không phải "hết việc"."""
    k = _k(bay_gio={"chu": "Nghỉ hôm nay", "muc": "nghi"}, dang_luc="30/09 20:00")
    assert bdk.cau_tinh_trang(k) == "Đã hẹn đăng 20:00 ngày 30/09"
    assert bdk.muc_the(k) == bdk.TOT


def test_cau_tinh_trang_nghi_that_su_khong_doi():
    k = _k(bay_gio={"chu": "Nghỉ hôm nay", "muc": "nghi"}, dang_luc="")
    assert bdk.cau_tinh_trang(k) == "Hôm nay nghỉ, không có video mới"
    assert bdk.muc_the(k) == bdk.TAT


def test_cau_tinh_trang_chua_chay_hom_nay_nhung_da_hen():
    k = _k(bay_gio={"chu": "Chưa chạy hôm nay", "muc": "nghi"}, dang_luc="01/10 09:00")
    assert bdk.cau_tinh_trang(k) == "Đã hẹn đăng 09:00 ngày 01/10"


def test_trang_dieu_khien_import_nguoc():
    """Trang cũ (`ui_qt/trang_dieu_khien.py`) vẫn phải lộ đúng tên này — bài
    kiểm cũ `tests/test_dieu_khien_cot_gon.py` import từ đó, không phải từ
    core."""
    from ui_qt import trang_dieu_khien as td

    assert td.cau_tinh_trang is bdk.cau_tinh_trang
    assert td.tien_do_nhat_ky is bdk.tien_do_nhat_ky
    assert td.gon_dong_nhat_ky is bdk.gon_dong_nhat_ky
    assert td.VIEC_KHAU is bdk.VIEC_KHAU
    assert td.DON_VI_KHAU is bdk.DON_VI_KHAU
    assert td._KY_THUAT is bdk._KY_THUAT


# ═══════════════════════════════════════════════════════════════════════════
# muc_the / video_ke_tiep
# ═══════════════════════════════════════════════════════════════════════════


def test_muc_the_moi_ca():
    assert bdk.muc_the(_k(bay_gio={"chu": "Lỗi: khâu Ảnh", "muc": "loi"})) == bdk.HONG
    assert bdk.muc_the(_k(bay_gio={"chu": "Chờ duyệt", "muc": "cho"})) == bdk.CHO_BAN
    assert bdk.muc_the(_k(bay_gio={"chu": "Chờ đăng 20:00", "muc": "cho"})) == bdk.TOT
    assert bdk.muc_the(_k(bay_gio={"chu": "Chưa đặt trần tiền", "muc": "canh_bao"})) == bdk.LUU_Y
    assert bdk.muc_the(_k(bay_gio={"chu": "Tắt tự chạy", "muc": "tat"})) == bdk.TAT
    assert bdk.muc_the(_k(bay_gio={"chu": "Nghỉ hôm nay", "muc": "nghi"})) == bdk.TAT
    assert bdk.muc_the(_k(bay_gio={"chu": "Đang làm video", "muc": "dang"})) == bdk.TOT


def test_video_ke_tiep_uu_tien_cho_duyet():
    k = _k(ke_hoach=[{"ma_goi": "K1-0001", "loai": "cho_duyet", "tieu_de": "Video chờ duyệt"}],
          video={"tieu_de": "Video đang làm", "ma_goi": ""})
    assert bdk.video_ke_tiep(k) == {"tieu_de": "Video chờ duyệt", "loai": "cho_duyet",
                                    "ma_goi": "K1-0001"}


def test_video_ke_tiep_lui_ve_video_dang_lam():
    k = _k(ke_hoach=[], video={"tieu_de": "Video đang làm", "ma_goi": "K1-0002"})
    assert bdk.video_ke_tiep(k) == {"tieu_de": "Video đang làm", "loai": "dang_lam",
                                    "ma_goi": "K1-0002"}


def test_video_ke_tiep_rong():
    assert bdk.video_ke_tiep(_k()) == {}


def test_video_ke_tiep_khong_lay_video_da_cong_khai():
    """Dữ liệu thật 29/09/2026 (TL2-T7): gói mới nhất trong `k["video"]" đã
    ĐĂNG (28/09 10:30) — không còn là "video kế tiếp" nữa."""
    k = _k(ke_hoach=[{"ma_goi": "K1-0003", "loai": "da_dang", "tieu_de": "Video đã đăng",
                      "ngay": "28/09/2026", "gio": "10:30"}],
          video={"tieu_de": "Video đã đăng", "ma_goi": "K1-0003"})
    assert bdk.video_ke_tiep(k) == {}


def test_video_ke_tiep_van_lay_khi_khong_khop_dong_ke_hoach():
    """Gói không tra được trong kế hoạch (ví dụ vừa mới sinh) — vẫn coi là
    đang làm, giữ đúng hành vi cũ."""
    k = _k(ke_hoach=[{"ma_goi": "K1-9999", "loai": "da_dang", "tieu_de": "Khác gói"}],
          video={"tieu_de": "Video đang làm", "ma_goi": "K1-0002"})
    assert bdk.video_ke_tiep(k) == {"tieu_de": "Video đang làm", "loai": "dang_lam",
                                    "ma_goi": "K1-0002"}


def test_may_dang_hoc_doc_khuon_rieng(tmp_path):
    """30/09/2026, Việc 4b: khuôn RIÊNG thật của chính kênh (`nguon: "kenh"`)
    giờ có tiền tố "khuôn riêng:" — không còn nhánh mơ hồ không rõ nguồn."""
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "nghien-cuu", "khuon-bia-thang.json"),
              {"video_id": "abc123", "ngay_so_lieu": "2026-09-29 08:00", "ctr": 9.7,
               "nguon": "kenh"})
    assert bdk.may_dang_hoc(goc, "K1") == (
        "Máy đang học: khuôn riêng: khuôn ảnh bìa thắng đổi 2026-09-29 (tỷ lệ bấm 9.7%)")


def test_may_dang_hoc_tham_do_khi_chua_co_khuon(tmp_path):
    """30/09/2026, Việc 4b: không còn `""` — chưa có khuôn nào (và không có
    hồ sơ video nào) thì báo đang THĂM DÒ, x=0."""
    assert bdk.may_dang_hoc(str(tmp_path), "K1") == (
        "Máy đang học: thumbnail: đang thử kiểu (0/7), chưa đủ dữ liệu riêng")


def test_may_dang_hoc_tham_do_dem_dung_so_kieu_da_thu(tmp_path):
    """Kênh có 5 hồ sơ video với `thumbnail.kieu` gồm 3 kiểu KHÁC NHAU và
    KHÔNG có `khuon-bia-thang.json` — phải đếm đúng (3/7)."""
    goc = str(tmp_path)
    thu_muc_ho_so = os.path.join(goc, "CHANNEL", "K1", "ho-so-video")
    os.makedirs(thu_muc_ho_so, exist_ok=True)
    kieu_moi_ho_so = ["portrait_main", "portrait_main", "dramatic_scene", "youtube_ctr", "youtube_ctr"]
    for i, kieu in enumerate(kieu_moi_ho_so):
        _ghi_json(os.path.join(thu_muc_ho_so, "K1-{0:04d}.json".format(i)),
                  {"thumbnail": {"kieu": kieu}})
    assert bdk.may_dang_hoc(goc, "K1") == (
        "Máy đang học: thumbnail: đang thử kiểu (3/7), chưa đủ dữ liệu riêng")


def test_may_dang_hoc_khuon_het_hieu_luc_thi_tham_do(tmp_path):
    """Một khuôn có đủ `video_id`/`ctr` nhưng bị đánh dấu `het_hieu_luc: true`
    (migrate 30/09/2026, khuôn mượn nhóm cũ) — phải rơi vào nhánh THĂM DÒ, dù
    có đủ dữ liệu số."""
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "nghien-cuu", "khuon-bia-thang.json"),
              {"video_id": "abc123", "ngay_so_lieu": "2026-09-29 08:00", "ctr": 9.7,
               "nguon": "nhom", "kenh_goc": "TL3-T7", "het_hieu_luc": True})
    assert bdk.may_dang_hoc(goc, "K1") == (
        "Máy đang học: thumbnail: đang thử kiểu (0/7), chưa đủ dữ liệu riêng")


def test_may_dang_hoc_noi_ro_muon_khuon_cua_kenh_khac(tmp_path):
    """Dữ liệu thật 29/09/2026 (TL1-T7/TL2-T7 mượn khuôn của TL3-T7) — khuôn
    "nguon": "nhom" (còn hợp lệ, không `het_hieu_luc` — một máy khác tự bật
    `bia_khuon_nhom: true`) phải nói rõ mượn của kênh nào, không để giống hệt
    như khuôn của chính kênh. Hành vi này GIỮ NGUYÊN sau bản vá 30/09/2026."""
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "nghien-cuu", "khuon-bia-thang.json"),
              {"video_id": "abc123", "ngay_so_lieu": "2026-09-29 08:00", "ctr": 9.7,
               "nguon": "nhom", "kenh_goc": "TL3-T7"})
    assert bdk.may_dang_hoc(goc, "K1") == (
        "Máy đang học: khuôn ảnh bìa thắng đổi 2026-09-29 (tỷ lệ bấm 9.7%) "
        "(mượn khuôn của TL3-T7)")


def test_may_dang_hoc_cua_chinh_kenh_khong_ghi_muon(tmp_path):
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "nghien-cuu", "khuon-bia-thang.json"),
              {"video_id": "abc123", "ngay_so_lieu": "2026-09-29 08:00", "ctr": 9.7,
               "nguon": "kenh", "kenh_goc": "K1"})
    cau = bdk.may_dang_hoc(goc, "K1")
    assert "mượn" not in cau
    assert "khuôn riêng:" in cau


# ═══════════════════════════════════════════════════════════════════════════
# video_gan_day — mũi tên so cùng mốc tuổi
# ═══════════════════════════════════════════════════════════════════════════


def _csv_chi_so(goc: str, ma: str, hang: list) -> None:
    d = os.path.join(goc, "CHANNEL", ma, "chi-so")
    cot = ("Tiêu đề,Mã video,Ngày đăng,Dài,Mốc mới nhất,Lượt hiển thị,"
          "Tỷ lệ bấm,Lượt xem,Xem TB,% độ dài,Đăng ký,Số lần chụp")
    dong = [cot]
    for h in hang:
        dong.append(",".join('"{0}"'.format(h.get(c, "")) for c in
                             ("tieu_de", "video_id", "ngay_dang", "dai", "moc",
                              "hien_thi", "ctr", "views", "xem_tb", "avd", "dang_ky", "so_lan")))
    _ghi(os.path.join(d, "bang-tom-tat.csv"), "\r\n".join(dong) + "\r\n")


def test_video_gan_day_mui_ten_len_va_khong_mui_ten(tmp_path):
    goc = str(tmp_path)
    hom_nay = BAY_GIO.date()
    _csv_chi_so(goc, "K1", [
        # Video mới nhất: CTR 9% ở mốc ~48h — cao hơn hẳn trung vị (4%, 3%) cùng mốc.
        {"tieu_de": "Video mới", "video_id": "vNew", "ngay_dang": hom_nay.isoformat(),
         "moc": "48h", "ctr": "9%", "views": "500", "avd": "40%"},
        {"tieu_de": "Video cũ 1", "video_id": "v1",
         "ngay_dang": (hom_nay - _dt.timedelta(days=5)).isoformat(),
         "moc": "48h", "ctr": "4%", "views": "300", "avd": "35%"},
        {"tieu_de": "Video cũ 2", "video_id": "v2",
         "ngay_dang": (hom_nay - _dt.timedelta(days=10)).isoformat(),
         "moc": "48h", "ctr": "3%", "views": "200", "avd": "30%"},
        # Video ở mốc lệch xa mọi mốc chuẩn (10h, lệch >30% so với 24h) — không so được.
        {"tieu_de": "Video mốc lạ", "video_id": "v3",
         "ngay_dang": (hom_nay - _dt.timedelta(days=1)).isoformat(),
         "moc": "10h", "ctr": "5%", "views": "50", "avd": "20%"},
    ])
    ra = bdk.video_gan_day(goc, "K1", n=4, bay_gio=BAY_GIO)
    theo_id = {d["video_id"]: d for d in ra}
    assert theo_id["vNew"]["mui_ten"] == "len"
    assert theo_id["v3"]["mui_ten"] == "", "mốc 10h lệch quá xa 24h — không so được"


def test_video_gan_day_chi_lay_n_video_moi_nhat(tmp_path):
    goc = str(tmp_path)
    hom_nay = BAY_GIO.date()
    _csv_chi_so(goc, "K2", [
        {"tieu_de": "A", "video_id": "a", "ngay_dang": (hom_nay - _dt.timedelta(days=1)).isoformat()},
        {"tieu_de": "B", "video_id": "b", "ngay_dang": (hom_nay - _dt.timedelta(days=2)).isoformat()},
        {"tieu_de": "C", "video_id": "c", "ngay_dang": (hom_nay - _dt.timedelta(days=3)).isoformat()},
    ])
    ra = bdk.video_gan_day(goc, "K2", n=2, bay_gio=BAY_GIO)
    assert [d["video_id"] for d in ra] == ["a", "b"]


# ═══════════════════════════════════════════════════════════════════════════
# doc_can_ghim / danh_dau_xong — "can-ghim đã đánh dấu thì biến mất"
# ═══════════════════════════════════════════════════════════════════════════


def test_doc_can_ghim_va_bien_mat_khi_da_xong(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K1", "can-ghim.md"),
        "- [2026-09-29 20:05] **Video một** — https://www.youtube.com/watch?v=abc123\n"
        "  > Ghim bình luận mở đầu, hỏi khán giả thích cảnh nào nhất.\n")
    pins = bdk.doc_can_ghim(goc, "K1")
    assert pins == [{"luc": "2026-09-29 20:05", "tieu_de": "Video một", "video_id": "abc123",
                     "ghi_chu": "Ghim bình luận mở đầu, hỏi khán giả thích cảnh nào nhất."}]

    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    khoa = [v["khoa"] for v in viec]
    assert "ghim:abc123" in khoa

    bdk.danh_dau_xong(goc, "ghim:abc123", bay_gio=BAY_GIO)
    assert "ghim:abc123" in bdk.doc_da_xong(goc)
    viec2 = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    assert "ghim:abc123" not in [v["khoa"] for v in viec2]


def test_danh_dau_xong_ghi_nguyen_tu(tmp_path):
    goc = str(tmp_path)
    bdk.danh_dau_xong(goc, "ghim:v1", bay_gio=BAY_GIO)
    bdk.danh_dau_xong(goc, "nhap:v2", bay_gio=BAY_GIO)
    duong = os.path.join(goc, "workspace", "viec-da-xong.json")
    assert os.path.isfile(duong)
    assert not os.path.isfile(duong + ".tmp")
    with open(duong, encoding="utf-8") as tep:
        du = json.load(tep)
    assert set(du) == {"ghim:v1", "nhap:v2"}


# ═══════════════════════════════════════════════════════════════════════════
# doc_nhap_thua
# ═══════════════════════════════════════════════════════════════════════════


def test_doc_nhap_thua_doc_dong_canh_bao(tmp_path):
    goc = str(tmp_path)
    thu_muc_vm = os.path.join(goc, "vm")
    _ghi(os.path.join(thu_muc_vm, "logs", "dang-dom.log"),
        "2026-09-29 10:15:23,456 INFO: kênh K1: quyết định tai_moi — ổn\n"
        "2026-09-29 10:15:24,000 WARNING: CẢNH BÁO K1: NHÁP THỪA trên kênh dQw4w9WgXcQ "
        "(chỉ báo, không xoá)\n"
        "2026-09-29 10:16:00,000 WARNING: CẢNH BÁO K2: NHÁP THỪA trên kênh other123 "
        "(chỉ báo, không xoá)\n")
    ra = bdk.doc_nhap_thua(thu_muc_vm)
    assert {(d["kenh"], d["video_id"]) for d in ra} == {("K1", "dQw4w9WgXcQ"), ("K2", "other123")}
    ra_k1 = bdk.doc_nhap_thua(thu_muc_vm, "K1")
    assert [d["video_id"] for d in ra_k1] == ["dQw4w9WgXcQ"]


def test_doc_nhap_thua_khong_co_tep(tmp_path):
    assert bdk.doc_nhap_thua(os.path.join(str(tmp_path), "vm")) == []


# ═══════════════════════════════════════════════════════════════════════════
# doc_kiem_dom
# ═══════════════════════════════════════════════════════════════════════════


def test_doc_kiem_dom_dich_ten_buoc(tmp_path):
    goc = str(tmp_path)
    thu_muc_vm = os.path.join(goc, "vm")
    _ghi_json(os.path.join(thu_muc_vm, "logs", "kiem-dom", "K1.json"),
              {"ngay": "2026-09-29 08:00:00", "kenh": "K1", "ok": False,
               "hong": ["tieu_de", "ma_moi_chua_biet"]})
    kq = bdk.doc_kiem_dom(thu_muc_vm, "K1")
    assert kq["ok"] is False
    assert kq["hong_ten"] == ["ô tiêu đề", "ma_moi_chua_biet"]


def test_doc_kiem_dom_chua_kiem_lan_nao(tmp_path):
    assert bdk.doc_kiem_dom(os.path.join(str(tmp_path), "vm"), "K1") is None


# ═══════════════════════════════════════════════════════════════════════════
# so_ngay_con_chay / dong_may
# ═══════════════════════════════════════════════════════════════════════════


def _bao_cao_tien(goc: str, ma: str, ngay: _dt.date, vnd: int) -> None:
    from core.tu_chay import duong_bao_cao_ngay

    _ghi_json(duong_bao_cao_ngay(goc, ma, ngay.isoformat()), {
        "ngay": ngay.isoformat(), "kenh": ma,
        "runs": [{"ma_luot": "0001", "ngan_sach": {"uoc_tinh_vnd": vnd},
                 "san_xuat": {"da_chay": True}}],
    })


def test_so_ngay_con_chay_chua_uoc_duoc_khi_thieu_so(tmp_path):
    goc = str(tmp_path)
    assert bdk.so_ngay_con_chay(goc, ["K1"], None, bay_gio=BAY_GIO) is None
    assert bdk.so_ngay_con_chay(goc, ["K1"], 1_000_000, bay_gio=BAY_GIO) is None


def test_so_ngay_con_chay_tinh_dung(tmp_path):
    goc = str(tmp_path)
    _bao_cao_tien(goc, "K1", BAY_GIO.date(), 200_000)
    so_du = 100_000 * MICRO_PER_VND
    so_ngay = bdk.so_ngay_con_chay(goc, ["K1"], so_du, bay_gio=BAY_GIO)
    assert so_ngay == 0.5


def test_dong_may_muc_vi_va_dia(tmp_path):
    goc = str(tmp_path)
    _bao_cao_tien(goc, "K1", BAY_GIO.date(), 200_000)
    anh = _anh([_k("K1")], o_dia={"con_gb": 5.0})
    dm = bdk.dong_may(goc, anh, bay_gio=BAY_GIO, so_du_micro=50_000 * MICRO_PER_VND,
                      gio_lich="02:00")
    assert dm["vi"]["muc"] == bdk.HONG, "0,25 ngày (<1) → đỏ"
    assert dm["o_dia"]["muc"] == bdk.HONG, "5 GB < 10 GB → đỏ"
    assert dm["lich"] == {"bat": True, "gio": "02:00"}


# ═══════════════════════════════════════════════════════════════════════════
# Đường ghi công tắc — thuần, không QMessageBox
# ═══════════════════════════════════════════════════════════════════════════


def test_doi_cong_tac_ghi_dung_tep(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "Kênh một", tu_chay=False)
    bdk.doi_cong_tac(goc, "K1", "tu_chay", True)
    from core.kenh import doc_kenh

    assert doc_kenh(goc, "K1").tu_chay is True

    bdk.doi_cong_tac(goc, "K1", "tu_dang", True)
    from core import vm_cai_dat

    assert vm_cai_dat.doc(goc, "K1")["tu_dang"] is True


def test_doi_ngan_sach_va_gio_dang(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "Kênh một")
    bdk.doi_ngan_sach(goc, "K1", 200000)
    bdk.doi_gio_dang(goc, "K1", "21:30")
    from core.kenh import doc_kenh

    k = doc_kenh(goc, "K1")
    assert k.ngan_sach_ngay == 200000
    assert k.gio_dang == "21:30"


def test_tam_dung_va_bat_lai_tat_ca(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "Kênh một", tu_chay=True)
    _kenh(goc, "K2", "Kênh hai", tu_chay=True)
    from core.kenh import doc_kenh

    da_tat = bdk.tam_dung_tat_ca(goc, ["K1", "K2"])
    assert da_tat == ["K1", "K2"]
    assert doc_kenh(goc, "K1").tu_chay is False
    assert doc_kenh(goc, "K2").tu_chay is False

    bdk.bat_lai_tam_dung(goc, da_tat)
    assert doc_kenh(goc, "K1").tu_chay is True
    assert doc_kenh(goc, "K2").tu_chay is True


# ═══════════════════════════════════════════════════════════════════════════
# viec_cua_ban — mỗi dòng bảng "Khối việc của bạn" ít nhất một ca
# ═══════════════════════════════════════════════════════════════════════════


def _muc_theo_khoa(viec: list, khoa_prefix: str):
    return next((v for v in viec if v["khoa"].startswith(khoa_prefix)), None)


def test_viec_dong_1_cho_duyet_chua_qua_han(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "Kênh một", tu_chay=True)
    _ke_hoach(goc, "K1", [{"Mã gói": "K1-0001", "Tiêu đề": "Video chờ", "Sẵn sàng": "x"}])
    k1 = _k("K1", ke_hoach=[{"ma_goi": "K1-0001", "loai": "cho_duyet", "tieu_de": "Video chờ"}],
           bay_gio={"chu": "Chờ duyệt", "muc": "cho"})
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "cho-duyet:")
    assert v is not None, "Chờ duyệt phải ra việc"
    assert v["muc"] == bdk.CANH_BAO
    assert "Video chờ" in v["chu"]
    assert ("hen_gio" in [n[1] for n in v["nut"]]) and ("bo_dang" in [n[1] for n in v["nut"]])


def test_viec_dong_2_cho_duyet_qua_han(tmp_path):
    goc = str(tmp_path)
    thu_muc_done = os.path.join(goc, "ban-giao")
    _kenh(goc, "K1", "Kênh một", tu_chay=True, thu_muc_done=thu_muc_done,
         cho_dang_toi_da_ngay=3)
    _ke_hoach(goc, "K1", [{"Mã gói": "K1-0001", "Tiêu đề": "Video chờ lâu", "Sẵn sàng": "x"}])
    thu_muc_goi = os.path.join(thu_muc_done, "K1-0001")
    os.makedirs(thu_muc_goi, exist_ok=True)
    cu = (BAY_GIO - _dt.timedelta(days=5)).timestamp()
    os.utime(thu_muc_goi, (cu, cu))

    k1 = _k("K1", ke_hoach=[{"ma_goi": "K1-0001", "loai": "cho_duyet", "tieu_de": "Video chờ lâu"}],
           bay_gio={"chu": "Chờ duyệt", "muc": "cho"})
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "qua-han:")
    assert v is not None, "chờ quá cho_dang_toi_da_ngay ngày phải ra việc riêng"
    assert "3 ngày" in v["chu"] and "Video chờ lâu" in v["chu"]
    assert "danh_dau_dang_tay" in [n[1] for n in v["nut"]]
    assert _muc_theo_khoa(viec, "cho-duyet:") is None, "đã quá hạn thì không còn ở dòng 1 nữa"


def test_viec_dong_3_qua_gio_dang():
    k1 = _k("K1", bay_gio={"chu": "Quá giờ đăng 20:00", "muc": "canh_bao"},
           video={"tieu_de": "", "ma_goi": "K1-0003"})
    viec = bdk.viec_cua_ban("goc-khong-dung", anh=_anh([k1]), bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "qua-gio:")
    assert v is not None and v["muc"] == bdk.HONG
    assert "danh_dau_dang_tay" in [n[1] for n in v["nut"]]


def test_viec_dong_9_muc_loi():
    k1 = _k("K1", bay_gio={"chu": "Lỗi: khâu Ảnh — timeout", "muc": "loi"})
    viec = bdk.viec_cua_ban("goc-khong-dung", anh=_anh([k1]), bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "loi:")
    assert v is not None and v["muc"] == bdk.HONG
    assert "chay_lai" in [n[1] for n in v["nut"]]


def test_viec_dong_4_ghim_chua_danh_dau(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K1", "can-ghim.md"),
        "- [2026-09-29 20:05] **Video một** — https://www.youtube.com/watch?v=abc123\n"
        "  > ghim mở đầu\n")
    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "ghim:")
    assert v is not None and v["xong_tay"] is True
    assert "danh_dau_xong" in [n[1] for n in v["nut"]]


def test_viec_dong_5_nhap_thua_chua_danh_dau(tmp_path):
    goc = str(tmp_path)
    thu_muc_vm = os.path.join(goc, "vm")
    _ghi(os.path.join(thu_muc_vm, "logs", "dang-dom.log"),
        "2026-09-29 10:15:24,000 WARNING: CẢNH BÁO K1: NHÁP THỪA trên kênh dQw4w9WgXcQ "
        "(chỉ báo, không xoá)\n")
    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO, thu_muc_vm=thu_muc_vm)
    v = _muc_theo_khoa(viec, "nhap:")
    assert v is not None and v["xong_tay"] is True
    assert "studio.youtube.com" in v["nut"][0][2]["url"]


def test_viec_dong_6_vi_sap_can(tmp_path):
    goc = str(tmp_path)
    _bao_cao_tien(goc, "K1", BAY_GIO.date(), 200_000)
    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO,
                            so_du_micro=50_000 * MICRO_PER_VND)
    v = _muc_theo_khoa(viec, "vi")
    assert v is not None and v["muc"] == bdk.HONG
    assert "Ví còn" in v["chu"]


def test_viec_dong_7_chua_dang_nhap():
    viec = bdk.viec_cua_ban("goc-khong-dung", anh=_anh([]), bay_gio=BAY_GIO, co_client=False)
    v = _muc_theo_khoa(viec, "dang-nhap")
    assert v is not None and v["muc"] == bdk.HONG


def test_viec_dong_8_o_dia_sap_day():
    viec = bdk.viec_cua_ban("goc-khong-dung", anh=_anh([], o_dia={"con_gb": 5.0}),
                            bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "dia")
    assert v is not None and v["muc"] == bdk.HONG


def test_viec_dong_10_kiem_dom_hong(tmp_path):
    from core import vm_cai_dat

    goc = str(tmp_path)
    thu_muc_vm = os.path.join(goc, "vm")
    _ghi_json(os.path.join(thu_muc_vm, "logs", "kiem-dom", "K1.json"),
              {"ngay": "2026-09-29 08:00:00", "kenh": "K1", "ok": False, "hong": ["tieu_de"]})
    vm_cai_dat.luu(goc, "K1", tu_dang=True, cach_dang="dom")
    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO, thu_muc_vm=thu_muc_vm)
    v = _muc_theo_khoa(viec, "kiem-dom:")
    assert v is not None
    assert "ô tiêu đề" in v["chu"]


def test_viec_dong_10_khong_hien_khi_khong_dung_may_dang_dom(tmp_path):
    """Dữ liệu thật 29/09/2026 (TL4-T7: `tu_dang=false`, `cach_dang="anh"`) —
    kết quả kiểm DOM không liên quan gì tới kênh đang ở đường ảnh cũ/chưa
    bật máy đăng, không được hiện thành việc phải sửa."""
    goc = str(tmp_path)
    thu_muc_vm = os.path.join(goc, "vm")
    _ghi_json(os.path.join(thu_muc_vm, "logs", "kiem-dom", "K1.json"),
              {"ngay": "2026-09-29 08:00:00", "kenh": "K1", "ok": False, "hong": ["tieu_de"]})
    # Mặc định `vm_cai_dat.doc` (chưa ghi tệp nào): tu_dang=False, cach_dang="anh".
    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO, thu_muc_vm=thu_muc_vm)
    assert _muc_theo_khoa(viec, "kiem-dom:") is None


def test_viec_dong_11_may_dang_tat():
    viec = bdk.viec_cua_ban(
        "goc-khong-dung", anh=_anh([]), bay_gio=BAY_GIO,
        trang_thai_may={"agent": {"song": True}, "tu_dang": {"song": False},
                        "tu_tra_loi_cmt": {"song": True}})
    v = _muc_theo_khoa(viec, "may:tu_dang")
    assert v is not None and v["muc"] == bdk.HONG


def test_viec_dong_11_che_do_phien_khong_bao_may_dang_tat(tmp_path):
    """Chế độ phiên: `GiamSat` CỐ Ý không nuôi máy đăng/trả lời ngoài phiên —
    KHÔNG được báo hỏng vì lẽ đó."""
    goc = str(tmp_path)
    thu_muc_vm = os.path.join(goc, "vm")
    _ghi_json(os.path.join(thu_muc_vm, "cai-dat-tool.json"), {"che_do_phien": True})
    trang_thai_may = {"agent": {"song": True}, "tu_dang": {"song": False},
                      "tu_tra_loi_cmt": {"song": False}}
    viec = bdk.viec_cua_ban(goc, anh=_anh([]), bay_gio=BAY_GIO, thu_muc_vm=thu_muc_vm,
                            trang_thai_may=trang_thai_may)
    assert _muc_theo_khoa(viec, "may:tu_dang") is None
    assert _muc_theo_khoa(viec, "may:tu_tra_loi_cmt") is None

    # Không ở chế độ phiên thì hai máy này PHẢI báo khi tắt.
    _ghi_json(os.path.join(thu_muc_vm, "cai-dat-tool.json"), {"che_do_phien": False})
    viec3 = bdk.viec_cua_ban(goc, anh=_anh([]), bay_gio=BAY_GIO, thu_muc_vm=thu_muc_vm,
                             trang_thai_may=trang_thai_may)
    assert _muc_theo_khoa(viec3, "may:tu_dang") is not None


def test_viec_dong_12_lich_tat_co_kenh_tu_chay():
    k1 = _k("K1", tu_chay=True)
    viec = bdk.viec_cua_ban("goc-khong-dung", anh=_anh([k1]), bay_gio=BAY_GIO, gio_lich="")
    v = _muc_theo_khoa(viec, "lich")
    assert v is not None and v["muc"] == bdk.CANH_BAO


def test_viec_dong_13_so_lieu_studio_cu(tmp_path):
    goc = str(tmp_path)
    duong = os.path.join(goc, "CHANNEL", "K1", "chi-so", "bang-tom-tat.csv")
    _ghi(duong, "Tiêu đề,Mã video,Ngày đăng\n")
    bay_gio_that = _dt.datetime.now()
    cu = (bay_gio_that - _dt.timedelta(hours=96)).timestamp()
    os.utime(duong, (cu, cu))
    k1 = _k("K1", tu_chay=True)
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=bay_gio_that)
    v = _muc_theo_khoa(viec, "so-lieu-cu:")
    assert v is not None
    assert "cũ" in v["chu"]


def test_doc_tinh_trang_chua_co_tep_thi_rong(tmp_path):
    assert bdk.doc_tinh_trang(str(tmp_path)) == {}


def test_doc_tinh_trang_doc_dung_tep(tmp_path):
    goc = str(tmp_path)
    du = {"luc": "2026-09-29T18:00:00", "kenh": {"K1": {"trang_thai": "cho_nguoi", "ly_do": "hết tiền"}},
         "so_su_co": 1, "may": {}}
    _ghi_json(os.path.join(goc, "workspace", "tinh-trang.json"), du)
    assert bdk.doc_tinh_trang(goc) == du


def test_viec_dong_14_gac_tong_cho_nguoi_ra_viec(tmp_path):
    """Mục 2, GHI-CHU bản vá 2026-09-29-tu-canh-loi: khối "Việc của bạn" đọc
    `workspace/tinh-trang.json` (do `core.gac_tong` ghi mỗi 15') cho những sự
    cố "chế độ chạy max" mà các kiểm khác (đọc trực tiếp ke-hoach.csv/bay_gio)
    không có tầm nhìn máy để thấy — ví dụ "đứng khâu quá lâu"."""
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "workspace", "tinh-trang.json"), {
        "luc": "2026-09-29T18:00:00",
        "kenh": {"K1": {"trang_thai": "cho_nguoi", "ly_do": "Kênh K1 đứng ở khâu “dung_video” 130 phút"}},
        "so_su_co": 1, "may": {},
    })
    k1 = _k("K1", bay_gio={"chu": "Đang tạo ảnh", "muc": "dang_lam"})
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    v = _muc_theo_khoa(viec, "gac-tong:K1")
    assert v is not None
    assert v["muc"] == bdk.HONG
    assert "đứng ở khâu" in v["chu"]
    assert "nhat_ky" in [n[1] for n in v["nut"]]


def test_viec_dong_14_khong_trung_khi_da_co_muc_loi_khac(tmp_path):
    """Kênh đã có một mục HỎNG khác (ví dụ "loi:") thì không thêm dòng thứ
    hai của gác tổng cho CÙNG kênh — tránh hai dòng nói cùng một chuyện."""
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "workspace", "tinh-trang.json"), {
        "luc": "2026-09-29T18:00:00",
        "kenh": {"K1": {"trang_thai": "cho_nguoi", "ly_do": "lý do khác"}},
        "so_su_co": 1, "may": {},
    })
    k1 = _k("K1", bay_gio={"chu": "Lỗi: khâu Ảnh", "muc": "loi"})
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    assert _muc_theo_khoa(viec, "gac-tong:K1") is None
    assert _muc_theo_khoa(viec, "loi:") is not None


def test_viec_dong_14_khong_cho_nguoi_thi_khong_ra_viec(tmp_path):
    goc = str(tmp_path)
    _ghi_json(os.path.join(goc, "workspace", "tinh-trang.json"), {
        "luc": "2026-09-29T18:00:00", "kenh": {"K1": {"trang_thai": "xong", "ly_do": "ok"}},
        "so_su_co": 0, "may": {},
    })
    k1 = _k("K1")
    viec = bdk.viec_cua_ban(goc, anh=_anh([k1]), bay_gio=BAY_GIO)
    assert _muc_theo_khoa(viec, "gac-tong:") is None


def test_viec_xep_hong_truoc_canh_bao_truoc_thuong():
    k1 = _k("K1", bay_gio={"chu": "Lỗi: khâu Ảnh", "muc": "loi"})
    viec = bdk.viec_cua_ban("goc-khong-dung", anh=_anh([k1], o_dia={"con_gb": 5.0}),
                            bay_gio=BAY_GIO, co_client=False)
    muc_thu_tu = [v["muc"] for v in viec]
    thu_tu_so = [bdk._THU_TU_MUC[m] for m in muc_thu_tu]
    assert thu_tu_so == sorted(thu_tu_so), "phải xếp hỏng trước, thường sau cùng"


# ═══════════════════════════════════════════════════════════════════════════
# anh_bang — gói toàn bộ
# ═══════════════════════════════════════════════════════════════════════════


def test_anh_bang_goi_du_khoa(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "Kênh một", tu_chay=True, ngan_sach_ngay=150000)
    anh = _anh([_k("K1")])
    ra = bdk.anh_bang(goc, bay_gio=BAY_GIO, anh=anh, gio_lich="02:00",
                      so_du_micro=1_000_000 * MICRO_PER_VND, co_client=True)
    assert set(ra) == {"kenh", "kenh_khac", "viec", "may", "luc"}
    assert ra["kenh"][0]["ma"] == "K1"
    assert "muc_the" in ra["kenh"][0]
    assert "video_ke_tiep" in ra["kenh"][0]
    assert "video_gan_day" in ra["kenh"][0]
    assert isinstance(ra["viec"], list)
    assert set(ra["may"]) == {"vi", "o_dia", "may_nen", "lich", "cong_suat", "chi_phi_that"}
