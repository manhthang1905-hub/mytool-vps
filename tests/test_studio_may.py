"""Máy Studio (16/10/2026): bộ chạy hàng việc máy có kiểu `studio_test_compare` / `studio_kiem_suc_khoe`.

Ứng viên bìa + cổng đọc được + xếp hạng, luật trạng thái việc (xong / bo / loi / can_nguoi), đường máy bận (việc giữ
`cho`), đọc chữ sức khoẻ Studio (đoạn chữ GIẢ), lịch tự kích hoạt (skill D13/D14, trần 1 lần / 3 ngày).

Cô lập: mọi thứ trong `tmp_path`; không mạng, không Chrome, không tiến trình thật. Mã video / kênh đều giả.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
import time
from pathlib import Path

import pytest

GOC_KHO = Path(__file__).resolve().parent.parent
if str(GOC_KHO / "vm") not in sys.path:
    sys.path.insert(0, str(GOC_KHO / "vm"))

import studio_may_dom as sdm  # noqa: E402

import core.giam_doc as gd  # noqa: E402
from core import ky_nang as kn  # noqa: E402
from core import ky_nang_tu as knt  # noqa: E402
from core import studio_may as sm  # noqa: E402

K = "KX1-T7"
V1, V2 = "FAKEvid0001", "FAKEvid0002"
MA1, MA2 = K + "-0001", K + "-0002"
BAY = dt.datetime(2026, 10, 16, 12, 0)


def _ghi(p, du):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    with io.open(str(p), "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _anh(p, mau=(10, 20, 30), co=(1280, 720)):
    from PIL import Image
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    Image.new("RGB", co, mau).save(str(p), format="JPEG", quality=90)
    return str(p)


def _cham(diem):
    """Cổng giả: tên tệp → báo cáo (dat, diem)."""
    def cham(p):
        return diem.get(os.path.basename(p), {"dat": True, "diem": 80.0})
    return cham


def _vt(p):
    """Vân tay giả: theo băm nội dung (cùng tệp chép = cùng vân tay, khác tệp = lệch xa)."""
    import hashlib
    with open(p, "rb") as tep:
        b = hashlib.sha256(tep.read()).digest()
    return list(b) * 2


@pytest.fixture()
def goc(tmp_path):
    g = tmp_path / "MyTool"
    hs = g / "CHANNEL" / K / "ho-so-video"
    _ghi(hs / (MA1 + ".json"), {"video_id": V1, "bia_2": {"tong_diem": 60.0, "bia_3": {"tong_diem": 50.0}}})
    _ghi(hs / (MA2 + ".json"), {"video_id": V2, "bia_2": None})
    _anh(hs / "anh" / (MA1 + ".jpg"), (200, 0, 0))                 # bìa đang dùng (A)
    _anh(hs / "anh" / (MA1 + "-bia-2.jpg"), (0, 200, 0))
    _anh(hs / "anh" / (MA1 + "-bia-3.jpg"), (0, 0, 200))
    th = g / "PROJECTS" / "AUTO" / K / "0001" / "7-thumbnail"
    _ghi(th / "chon-bia.json", {"chon": {"so": 1}, "ung_vien": [
        {"so": 1, "tong_diem": 80.0}, {"so": 2, "tong_diem": 70.0}, {"so": 3, "tong_diem": 90.0, "loai": "chu_sai"},
        {"so": 4, "tong_diem": 55.0}, {"so": 5, "tong_diem": 65.0}]})
    _anh(th / "thumb_001.jpg", (200, 0, 0))                        # tấm đã chọn = A
    _anh(th / "thumb_002.jpg", (0, 200, 0))                        # = bìa-2 (chép) → trùng
    _anh(th / "thumb_003.jpg", (1, 2, 3))                          # bị loại (chữ sai) → không bao giờ là ứng viên
    _anh(th / "thumb_004.jpg", (50, 50, 50))
    _anh(th / "thumb_005.jpg", (90, 90, 0))
    _anh(th / "CHON-thumb_001.jpg", (200, 0, 0))
    _ghi(g / "vm" / "logs" / "so-video-id.json", {K + "/" + MA1: {"video_id": V1}, K + "/" + MA2: {"video_id": V2}})
    return str(g)


# ═══ 1. ỨNG VIÊN BÌA: nguồn, trùng, cổng, xếp hạng ═══════════════════════════

def test_ma_goi_tu_so_va_ho_so(goc):
    assert sm.ma_goi_cua_video(goc, K, V1) == MA1
    os.remove(os.path.join(goc, "vm", "logs", "so-video-id.json"))
    assert sm.ma_goi_cua_video(goc, K, V2) == MA2                   # lùi về hồ sơ video
    assert sm.ma_goi_cua_video(goc, K, "FAKEvid9999") == ""


def test_ung_vien_xep_theo_diem_giam_khao_bo_trung_va_bia_a(goc):
    a = os.path.join(goc, "CHANNEL", K, "ho-so-video", "anh", MA1 + ".jpg")
    chon, bo = sm.ung_vien_bia(goc, K, MA1, a, cham=_cham({}), van_tay=_vt)
    ten = [os.path.basename(u["tep"]) for u in chon]
    # thumb_002 (70) trùng bìa-2 (60): giữ bản ĐẦU gặp (bìa-2 hồ sơ, điểm 60); thumb_005 (65) xếp trước
    assert ten == ["thumb_005.jpg", MA1 + "-bia-2.jpg"]
    assert [u["diem_gk"] for u in chon] == [65.0, 60.0]
    ly = {os.path.basename(u["tep"]): u["ly_do"] for u in bo}
    assert "trùng" in ly["thumb_002.jpg"]
    assert "thumb_003.jpg" not in ly and all("thumb_003" not in os.path.basename(u["tep"]) for u in chon)
    assert "thumb_001.jpg" not in ly                                 # tấm đã chọn không phải ứng viên
    assert "CHON-thumb_001.jpg" not in ly
    assert any("đủ 2 ứng viên" in v for v in ly.values())            # bìa-3 / thumb_004 thừa


def test_cong_doc_duoc_chan_tam_truot_va_khong_ket_luan(goc):
    chon, bo = sm.ung_vien_bia(goc, K, MA1, (), van_tay=_vt, cham=_cham({
        MA1 + "-bia-2.jpg": {"dat": False, "ly_do": ["dòng 1: tương phản 1.8:1"]},
        "thumb_005.jpg": {"dat": None, "ly_do": ["không dò ra dòng chữ"]},
        "thumb_004.jpg": {"dat": True, "diem": 70, "bo_cuc": {"chong_khung": True}}}))
    ten = [os.path.basename(u["tep"]) for u in chon]
    assert MA1 + "-bia-2.jpg" not in ten and "thumb_005.jpg" not in ten and "thumb_004.jpg" not in ten
    ly = {os.path.basename(u["tep"]): u["ly_do"] for u in bo}
    assert ly[MA1 + "-bia-2.jpg"].startswith("trượt cổng") and ly["thumb_005.jpg"].startswith("trượt cổng")
    assert ly["thumb_004.jpg"].startswith("bố cục hỏng")
    assert all(u["diem_doc"] is not None or u.get("diem_doc") is None for u in chon)


def test_ung_vien_trung_bia_a_bi_bo(goc):
    a = _anh(os.path.join(goc, "tmp-a.jpg"), (0, 200, 0))           # bìa đang chạy CHÍNH là bìa-2
    chon, bo = sm.ung_vien_bia(goc, K, MA1, [a], cham=_cham({}), van_tay=_vt)
    assert MA1 + "-bia-2.jpg" not in [os.path.basename(u["tep"]) for u in chon]
    assert any(u["ly_do"] == "trùng bìa A đang chạy" for u in bo)


def test_video_khong_con_ung_vien(goc):
    chon, bo = sm.ung_vien_bia(goc, K, MA2, (), cham=_cham({}), van_tay=_vt)
    assert chon == [] and bo == []


def test_tep_tai_len_chuan_bia(goc, tmp_path):
    p = _anh(tmp_path / "x.jpg", co=(1376, 768))
    t = sm.tep_tai_len(p, str(tmp_path / "ra"))
    from PIL import Image
    assert t != p and Image.open(t).size == (1280, 720) and os.path.getsize(t) <= sm.BIA_TOI_DA_BYTE
    q = _anh(tmp_path / "y.jpg")
    assert sm.tep_tai_len(q, str(tmp_path / "ra")) == q


# ═══ 2. LUẬT TRẠNG THÁI VIỆC ═════════════════════════════════════════════════

def test_ket_viec_test():
    xong = sm.ket_viec_test({V1: {"ket": "da_dat", "so_bia": 3}, V2: {"ket": "khong_ung_vien"}})
    assert xong[0] == "xong" and "3 bìa" in xong[1]
    assert sm.ket_viec_test({V1: {"ket": "da_co", "trang_thai": "dang_chay"}})[0] == "xong"
    assert sm.ket_viec_test({V1: {"ket": "khong_ung_vien"}, V2: {"ket": "khong_ung_vien"}})[0] == "bo"
    assert sm.ket_viec_test({V1: {"ket": "da_dat"}, V2: {"ket": "loi", "ly_do": "x"}})[0] == "loi"
    bo = sm.ket_viec_test({V1: {"ket": "khong_quyen", "ly_do": "thiếu tính năng nâng cao"}, V2: {"ket": "da_dat"}})
    assert bo == ("bo", "thiếu tính năng nâng cao")
    assert sm.ket_viec_test({})[0] == "bo"


def test_thieu_tinh_nang_theo_so_ghim():
    so = {"_kenh:" + K: {"can_xac_minh": "2026-10-16 01:00:00"}, V1: {"kenh": K, "da_ghim": ""}}
    assert "tính năng nâng cao" in sm.thieu_tinh_nang(so, K, BAY)
    assert sm.thieu_tinh_nang(so, K, BAY + dt.timedelta(days=4)) == ""          # chặn cũ: không còn tính
    so2 = dict(so, **{V2: {"kenh": K, "da_ghim": "2026-10-16 03:00:00"}})
    assert sm.thieu_tinh_nang(so2, K, BAY) == ""                                  # đã ghim được sau lần chặn
    assert sm.thieu_tinh_nang({}, K, BAY) == ""


def _viec_test(goc, vids=(V1, V2)):
    gd.ghi_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE, K, video_ids=list(vids), nguon="nao:n999", chu="thử", bay_gio=BAY)
    return gd.doc_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE)[0]["id"]


def _viec_sk(goc):
    gd.ghi_viec_may_kieu(goc, gd.LOAI_KIEM_SUC_KHOE, K, nguon="giam-doc:" + K, chu="sức khoẻ", bay_gio=BAY)
    return gd.doc_viec_may_kieu(goc, gd.LOAI_KIEM_SUC_KHOE)[0]["id"]


def _tt(goc, i):
    return next(m for m in gd.doc_viec_may_kieu(goc, None, None) if m["id"] == i)


@pytest.fixture()
def may(goc, monkeypatch):
    monkeypatch.setattr(sdm, "GOC", os.path.join(goc, "vm"))
    monkeypatch.setattr(sdm, "GOC_TOOL", goc)
    monkeypatch.setattr(sdm, "_kiem_dung", lambda agent, kenh: None)
    return []


def _tai_gia(url):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1280, 720), (200, 0, 0)).save(b, format="JPEG", quality=90)
    return b.getvalue()


def test_may_ban_viec_giu_cho(goc, may):
    i = _viec_test(goc)
    goi = []

    def phien(kenh, ghi, lam, che_do, **kw):
        goi.append(che_do)
        return sdm.MA_HOAN, "khoá máy (.khoa-may) đang bận — không ép"
    ma = sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=phien)
    assert ma == sdm.MA_HOAN and goi == ["test"]
    m = _tt(goc, i)
    assert m["trang_thai"] == "cho" and m["lan_thu"] == 0 and m["ket"] == {}


def test_suc_khoe_may_ban_giu_cho(goc, may):
    i = _viec_sk(goc)
    ma = sdm.chay_suc_khoe(K, may.append, phien=lambda *a, **kw: (sdm.MA_HOAN, "van IPv4 đang mở"))
    assert ma == sdm.MA_HOAN and _tt(goc, i)["trang_thai"] == "cho" and _tt(goc, i)["lan_thu"] == 0


def test_test_xong_va_hoan_giua_chung(goc, may, monkeypatch):
    i = _viec_test(goc)
    vu = []

    def mot(S, vid, kh, ghi, thu=False, khong_luu=False):
        vu.append((vid, [os.path.basename(u["tep"]) for u in kh["chon"]]))
        return {"ket": "da_dat", "so_bia": 1 + len(kh["chon"]), "trang_thai": "dang_chay"}
    monkeypatch.setattr(sdm, "test_mot_video", mot)

    def phien(kenh, ghi, lam, che_do, **kw):
        assert kw.get("cho_luu") is True
        return sdm.MA_XONG, lam(object(), None, None)
    assert sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=phien) == sdm.MA_XONG
    m = _tt(goc, i)
    assert m["trang_thai"] == "xong"
    assert m["ket"]["video"][V1]["ket"] == "da_dat" and m["ket"]["video"][V2]["ket"] == "khong_ung_vien"
    assert [v for v, _c in vu] == [V1] and len(vu[0][1]) == 2      # V2 không ứng viên: không mở trang
    assert m["ket"]["video"][V1]["ma_goi"] == MA1


def test_test_hoan_giua_phien_tra_ve_cho(goc, may, monkeypatch):
    i = _viec_test(goc)

    def mot(*a, **kw):
        raise sdm.tl.Hoan("dừng giữa chừng: agent báo có việc đăng")
    monkeypatch.setattr(sdm, "test_mot_video", mot)

    def phien(kenh, ghi, lam, che_do, **kw):
        try:
            return sdm.MA_XONG, lam(object(), None, None)
        except sdm.tl.Hoan as h:
            return sdm.MA_HOAN, str(h)
    assert sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=phien) == sdm.MA_HOAN
    m = _tt(goc, i)
    assert m["trang_thai"] == "cho" and m["lan_thu"] == 0


def test_test_dang_xuat_thanh_loi_roi_bo(goc, may):
    i = _viec_test(goc)
    for lan in range(1, 6):
        ma = sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}),
                           phien=lambda *a, **kw: (sdm.MA_CAN_NGUOI, "dang-xuat"))
        m = _tt(goc, i)
        if lan < 5:
            assert ma == sdm.MA_CAN_NGUOI and m["trang_thai"] == "loi" and m["ket"]["ly_do"] == "dang-xuat"
            assert m["lan_thu"] == lan
    assert _tt(goc, i)["trang_thai"] == "bo"                         # 5 lần lỗi → bỏ (không lặp mãi)
    assert sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=lambda *a, **kw: 1 / 0) == sdm.MA_KHONG_CAN


def test_test_khong_quyen_bo(goc, may, monkeypatch):
    i = _viec_test(goc)
    monkeypatch.setattr(sdm, "test_mot_video", lambda *a, **kw: {"ket": "khong_quyen", "ly_do": "cần tính năng nâng cao"})
    sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=lambda k, g, lam, c, **kw: (0, lam(object(), None, None)))
    m = _tt(goc, i)
    assert m["trang_thai"] == "bo" and "nâng cao" in m["ket"]["ly_do"]


def test_test_kenh_bi_chan_ghim_bo_khong_mo_chrome(goc, may):
    i = _viec_test(goc)
    _ghi(os.path.join(goc, "vm", "logs", "cmt-dom.json"),
         {"_kenh:" + K: {"can_xac_minh": time.strftime("%Y-%m-%d %H:%M:%S")}})
    ma = sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=lambda *a, **kw: 1 / 0)
    assert ma == sdm.MA_XONG and _tt(goc, i)["trang_thai"] == "bo"
    assert "tính năng nâng cao" in _tt(goc, i)["ket"]["ly_do"]


def test_test_khong_ung_vien_bo_khong_mo_chrome(goc, may):
    i = _viec_test(goc, (V2,))
    ma = sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=lambda *a, **kw: 1 / 0)
    assert ma == sdm.MA_XONG and _tt(goc, i)["trang_thai"] == "bo"


def test_test_video_loi_thanh_loi(goc, may, monkeypatch):
    i = _viec_test(goc)
    monkeypatch.setattr(sdm, "test_mot_video", lambda *a, **kw: {"ket": "loi", "ly_do": "đọc lại lệch"})
    ma = sdm.chay_test(K, may.append, tai=_tai_gia, cham=_cham({}), phien=lambda k, g, lam, c, **kw: (0, lam(object(), None, None)))
    assert ma == sdm.MA_LOI and _tt(goc, i)["trang_thai"] == "loi" and _tt(goc, i)["lan_thu"] == 1


# ═══ 3. ĐỌC SỨC KHOẺ (chữ trang GIẢ) ═════════════════════════════════════════

KHONG_SAO = {
    "tinh_nang": {"chu": "Cài đặt\nKênh\nĐủ điều kiện sử dụng tính năng\nTính năng tiêu chuẩn\nĐã bật\n"
                         "Gậy cảnh cáo vi phạm bản quyền\nKhông có\nCảnh cáo vi phạm Nguyên tắc cộng đồng\nKhông có\n"
                         "Tìm hiểu thêm về gậy cảnh cáo vi phạm bản quyền"},
    "kiem_tien": {"chu": "Kiếm tiền\nTham gia Chương trình Đối tác YouTube\n1.000 người đăng ký\n4.000 giờ xem"},
    "ban_quyen": {"chu": "Bản quyền\nKhông có gậy cảnh cáo vi phạm bản quyền nào"},
}


def test_suc_khoe_binh_thuong():
    kq = sm.doc_suc_khoe(KHONG_SAO)
    assert kq["canh_bao"] is False and kq["muc"] == [] and set(kq["doc_duoc"]) == {"tinh_nang", "kiem_tien", "ban_quyen"}


@pytest.mark.parametrize("chu,loai", [
    ("Gậy cảnh cáo vi phạm bản quyền\n1 gậy cảnh cáo — hết hạn sau 90 ngày", "gay_ban_quyen"),
    ("Kênh của bạn đã nhận 1 cảnh cáo vi phạm Nguyên tắc cộng đồng", "gay_cong_dong"),
    ("Kết quả xét duyệt: Nội dung dùng lại", "dung_lai"),
    ("Your channel has 1 copyright strike", "gay_ban_quyen"),
    ("Reused content", "dung_lai"),
    ("コミュニティ ガイドライン違反の警告を受けました", "gay_cong_dong"),
])
def test_suc_khoe_thay_van_de(chu, loai):
    kq = sm.doc_suc_khoe(dict(KHONG_SAO, kiem_tien={"chu": chu}))
    assert kq["canh_bao"] is True and kq["muc"][0]["loai"] == loai and "THẤY" in kq["chi_tiet"]


def test_suc_khoe_trang_rong_khong_ket_luan():
    kq = sm.doc_suc_khoe({"tinh_nang": {"chu": ""}, "kiem_tien": {"loi": "x"}})
    assert kq["canh_bao"] is False and kq["doc_duoc"] == []


def test_chay_suc_khoe_can_nguoi_va_tran_3_ngay(goc, may):
    i = _viec_sk(goc)
    trang = dict(KHONG_SAO, kiem_tien={"chu": "Reused content", "url": "u", "anh": "a.png"})
    ma = sdm.chay_suc_khoe(K, may.append, phien=lambda *a, **kw: (sdm.MA_XONG, trang))
    m = _tt(goc, i)
    assert ma == sdm.MA_XONG and m["trang_thai"] == "can_nguoi" and m["ket"]["canh_bao"] is True
    assert set(m["ket"]) >= {"canh_bao", "chi_tiet", "trang", "anh"}
    assert os.path.isfile(sm.duong_ket_suc_khoe(goc, K))
    # việc mới cùng kênh trong 3 ngày: đóng bằng lần đọc ấy, KHÔNG mở Chrome
    du = json.load(open(os.path.join(goc, gd._tu_dong.TEP_HANG_DOI), encoding="utf-8"))
    du["viec_may"] = []
    _ghi(os.path.join(goc, gd._tu_dong.TEP_HANG_DOI), du)
    i2 = _viec_sk(goc)
    assert sdm.chay_suc_khoe(K, may.append, phien=lambda *a, **kw: 1 / 0) == sdm.MA_XONG
    assert _tt(goc, i2)["trang_thai"] == "can_nguoi" and _tt(goc, i2)["ket"]["tu_lan_doc"]


def test_chay_suc_khoe_xong_khi_sach(goc, may):
    i = _viec_sk(goc)
    assert sdm.chay_suc_khoe(K, may.append, phien=lambda *a, **kw: (sdm.MA_XONG, KHONG_SAO)) == sdm.MA_XONG
    assert _tt(goc, i)["trang_thai"] == "xong" and _tt(goc, i)["ket"]["canh_bao"] is False


def test_chay_suc_khoe_dang_xuat_loi(goc, may):
    i = _viec_sk(goc)
    assert sdm.chay_suc_khoe(K, may.append, phien=lambda *a, **kw: (sdm.MA_CAN_NGUOI, "dang-xuat")) == sdm.MA_CAN_NGUOI
    assert _tt(goc, i)["trang_thai"] == "loi" and _tt(goc, i)["ket"]["ly_do"] == "dang-xuat"


# ═══ 4. BẢO VỆ + LỊCH TỰ KÍCH HOẠT ════════════════════════════════════════════

def test_phien_sap_toi():
    luc = time.mktime((2026, 10, 16, 7, 20, 0, 0, 0, -1))
    tt = {"phien_muc_tieu@KA-T7@2026-10-16": "07:30", "phien_cuoi@KA-T7": "2026-10-15"}
    assert "KA-T7" in sdm.phien_sap_toi(tt, luc, 15)
    assert sdm.phien_sap_toi(tt, luc, 5) == ""
    assert sdm.phien_sap_toi(dict(tt, **{"phien_cuoi@KA-T7": "2026-10-16"}), luc, 15) == ""   # đã chạy hôm nay
    tre = time.mktime((2026, 10, 16, 8, 0, 0, 0, 0, -1))
    assert "KA-T7" in sdm.phien_sap_toi(tt, tre, 15)                                            # quá hạn chưa chạy
    assert sdm.phien_sap_toi(tt, time.mktime((2026, 10, 16, 10, 0, 0, 0, 0, -1)), 15) == ""   # quá 90' → thôi chờ


def test_phan_loai_thu_nghiem():
    assert sdm.phan_loai_thu_nghiem("Thử nghiệm và so sánh\nĐang chạy · 3 hình thu nhỏ") == "dang_chay"
    assert sdm.phan_loai_thu_nghiem("Test complete — view results") == "xong"
    assert sdm.phan_loai_thu_nghiem("Hình thu nhỏ\nTải tệp lên\nThử nghiệm và so sánh") == ""


def test_skill_d13_d14_khai_dung():
    for ma, co in (("D13", "--test-compare"), ("D14", "--suc-khoe")):
        k = kn.theo_ma(ma)
        assert k and k.tu_ap and k.nang and not k.toan_may and k.dieu_kien is not None
        lenh = knt.lenh_cua(k, "G", "KX")
        assert lenh[-1] == co and lenh[-3:-1] == ["--kenh", "KX"] and lenh[-4].endswith("studio_may_dom.py")
        assert ma in knt.BO_PHAN


def _san_sang(monkeypatch):
    monkeypatch.setattr(kn, "_san_sang_dom", lambda goc, kenh: "")


def test_dieu_kien_test(goc, monkeypatch):
    _san_sang(monkeypatch)
    monkeypatch.setattr(kn, "_gio", lambda: BAY)
    assert kn.d_test_compare(goc, K)[0] is False
    _viec_test(goc)
    dung, ly = kn.d_test_compare(goc, K)
    assert dung and "2 video" in ly
    monkeypatch.setattr(kn, "_gio", lambda: BAY.replace(hour=3))
    assert kn.d_test_compare(goc, K) == (False, "khung cấm 02–07 của thiết lập kênh")


def test_dieu_kien_suc_khoe_tran_3_ngay(goc, monkeypatch):
    _san_sang(monkeypatch)
    monkeypatch.setattr(kn, "_gio", lambda: BAY.replace(hour=3))
    _viec_sk(goc)
    assert kn.d_suc_khoe_studio(goc, K)[0] is False                  # khung cấm, chưa có lần đọc
    _ghi(sm.duong_ket_suc_khoe(goc, K), {"luc": (BAY - dt.timedelta(days=1)).isoformat(), "canh_bao": False})
    dung, ly = kn.d_suc_khoe_studio(goc, K)
    assert dung and "không mở Chrome" in ly                          # lần đọc còn mới: đóng việc, không cần khung
    _ghi(sm.duong_ket_suc_khoe(goc, K), {"luc": (BAY - dt.timedelta(days=4)).isoformat(), "canh_bao": False})
    assert kn.d_suc_khoe_studio(goc, K)[0] is False                  # cũ → phải mở Chrome → khung cấm chặn
    monkeypatch.setattr(kn, "_gio", lambda: BAY)
    assert kn.d_suc_khoe_studio(goc, K)[0] is True


def test_moi_luot_mot_viec_nang(goc, monkeypatch):
    """Bộ tự kích hoạt: hai kênh cùng có việc Studio → lượt này chạy MỘT, kênh kia để lượt sau."""
    _san_sang(monkeypatch)
    monkeypatch.setattr(kn, "_gio", lambda: BAY.replace(minute=35))
    monkeypatch.setattr(knt, "khoa_may_ban", lambda goc: "")
    monkeypatch.setattr(knt, "cong_tac_bat", lambda goc: True)
    gd.ghi_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE, "KX1-T7", video_ids=[V1], bay_gio=BAY)
    gd.ghi_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE, "KX2-T7", video_ids=[V2], bay_gio=BAY)
    monkeypatch.setattr(kn, "DANH_MUC", [kn.theo_ma("D13")])
    monkeypatch.setattr(kn, "_cac_kenh", lambda goc: ["KX1-T7", "KX2-T7"])
    chay = []
    knt.tu_kich_hoat(goc, chay_lenh=lambda lenh, cwd, han: (chay.append(lenh), (10, "hoãn"))[1], in_ra=lambda s: None)
    assert len(chay) == 1
    so = knt.doc_so(goc)
    assert any(x.get("quyet") == "bo_qua" for x in so) and any(x.get("quyet") == "hoan" for x in so)


# ═══ 5. ĐỌC LẠI THỬ NGHIỆM (gói Studio) · TRANG NỘI DUNG · BỘ CHỌN ══════════

def test_phan_tich_thu_nghiem():
    assert sdm.phan_tich_thu_nghiem({}) == {"co": False, "trang_thai": "", "so_bia": None}   # đo thật: chưa thử nghiệm = {}
    assert sdm.phan_tich_thu_nghiem(None)["co"] is False
    chay = sdm.phan_tich_thu_nghiem({"experimentState": "EXPERIMENT_STATE_RUNNING",
                                     "thumbnailArms": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "metrics": [{}, {}, {}, {}]})
    assert chay["co"] and chay["trang_thai"] == "dang_chay" and chay["so_bia"] == 3        # «metrics» không phải nhánh bìa
    xong = sdm.phan_tich_thu_nghiem({"status": "COMPLETED", "variants": [{}, {}]})
    assert xong["trang_thai"] == "xong" and xong["so_bia"] == 2
    la = sdm.phan_tich_thu_nghiem({"id": "x"})
    assert la["co"] and la["trang_thai"] == "co" and la["so_bia"] is None                   # khuôn lạ: có thử nghiệm, không so số


def test_suc_khoe_trang_noi_dung():
    hang = "Video\nThông báo\nChế độ hiển thị\nNgày\n11:47\nTiêu đề giả 1\n—\nCông khai\n14 thg 10, 2026\nĐã xuất bản\n395\n1\n"
    assert sm.doc_suc_khoe({"noi_dung": {"chu": hang}})["canh_bao"] is False
    kq = sm.doc_suc_khoe({"noi_dung": {"chu": hang + "13:16\nTiêu đề giả 2\nNguyên tắc cộng đồng\nCông khai\n"}})
    assert kq["canh_bao"] is True and kq["muc"][0]["loai"] == "han_che_video"
    kq = sm.doc_suc_khoe({"noi_dung": {"chu": hang + "13:16\nTiêu đề giả 3\nBản quyền\nCông khai\n"}})
    assert kq["canh_bao"] is False and kq["thong_tin"][0]["loai"] == "khieu_nai_ban_quyen" and "ghi nhận" in kq["chi_tiet"]
    # chữ «Nguyên tắc cộng đồng» đứng riêng ở trang KHÁC không phải ô hạn chế
    assert sm.doc_suc_khoe({"bang_dieu_khien": {"chu": "Nguyên tắc cộng đồng"}})["canh_bao"] is False


def test_suc_khoe_trang_tinh_nang_that():
    """Khuôn chữ đo thật 16/10 (Cài đặt → Kênh → Điều kiện sử dụng tính năng): có chữ «xác minh» nhưng KHÔNG phải cảnh báo."""
    chu = ("Điều kiện sử dụng tính năng\nBạn có thể quản lý quyền sử dụng các tính năng khác tại đây. Đối với các tính năng "
           "bậc trung và nâng cao, bạn phải thực hiện bước xác minh bổ sung. Tìm hiểu thêm\n1. Các tính năng cơ bản\nĐã bật\n"
           "2. Các tính năng bậc trung\nĐã bật\n3. Các tính năng nâng cao\nĐã bật\nĐóng\nLưu")
    ban_quyen = "Phát hiện nội dung\nBản quyền\nYêu cầu gỡ bỏ\nChưa có nội dung gì\nBạn chưa gửi yêu cầu gỡ bỏ do vi phạm bản quyền."
    assert sm.doc_suc_khoe({"tinh_nang": {"chu": chu}, "ban_quyen": {"chu": ban_quyen}})["canh_bao"] is False


def test_thu_chi_doc_khong_ghi_viec(goc, may, monkeypatch):
    i = _viec_test(goc)
    seen = []
    monkeypatch.setattr(sdm, "test_mot_video", lambda S, vid, kh, ghi, thu=False, khong_luu=False:
                        (seen.append((vid, thu)), {"ket": "doc"})[1])

    def phien(kenh, ghi, lam, che_do, **kw):
        assert kw.get("cho_luu") is False                            # --thu: nút Lưu vẫn bị cấm
        return sdm.MA_XONG, lam(object(), None, None)
    assert sdm.chay_test(K, may.append, thu=True, tai=_tai_gia, cham=_cham({}), phien=phien) == sdm.MA_XONG
    assert seen == [(V1, True), (V2, True)]                          # đọc cả video không ứng viên
    m = _tt(goc, i)
    assert m["trang_thai"] == "cho" and m["ket"] == {} and m["lan_thu"] == 0


def test_bo_chon_ab_trong_json():
    import re as _re

    import cdp_studio
    bo = cdp_studio.doc_bo_chon(str(GOC_KHO / "vm" / "studio-selectors.json"), duong_tu_chua="")
    assert cdp_studio.kiem_bo_chon(bo) == []
    pt = bo["phan_tu"]
    assert pt["ab_nut"]["chon"] == ["ytcp-button#ab-test-button"] and "Thử nghiệm A/B" in pt["ab_nut"]["chu"]
    assert "chip-1" in pt["ab_chip_bia"]["chon"][0] and "set-test-button" in pt["ab_thiet_lap"]["chon"][0]
    assert all(pt[k].get("phu") for k in ("ab_nut", "ab_chip_bia", "ab_o_bia", "ab_thiet_lap"))
    assert _re.search(sdm.RE_NUT_TEST, "Thử nghiệm A/B", _re.I) and _re.search(sdm.RE_CHIP_BIA, "Chỉ hình thu nhỏ", _re.I)
    assert _re.search(sdm.RE_NUT_THIET_LAP, "Thiết lập thử nghiệm", _re.I)
