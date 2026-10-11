"""Thước thắng CHUNG (`core/thuoc_thang.py`, 12/10/2026) — một định nghĩa "video thắng" cho mọi bộ phận.

Kiểm toán 12/10 (`workspace/chan-doan/*-2026-10-12.md`): thước 48h (max(6.000, 3 × trung vị)) gắn TRƯỢT cho video nổ
ngày 3–5 (TL1 vidGia685d6 2.303 @46h → 28.624 @94h), bản chụp muộn rỗng, nhãn thư mục ≠ tuổi thật, cửa sổ 96h bỏ
sót số 94h. Số giả hoàn toàn trong tmp_path — không mạng, không AI.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os

from core import cong_thuc_v7 as v7
from core import thuoc_thang as tt
from core import tu_hoc
from core.chien_luoc import ket_qua

DANG0 = dt.datetime(2026, 9, 1, 0, 0)


def _ts(d):
    return d.replace(tzinfo=dt.timezone.utc).timestamp()


def _c(ma, ngay, *diem):
    """Chuỗi giả: video đăng `ngay` ngày sau DANG0, `diem` = (tuổi giờ, hiển thị)."""
    dang = _ts(DANG0 + dt.timedelta(days=ngay))
    return tt.Chuoi(ma=ma, dang=dang, diem=[tt.Diem(tuoi=float(t), hien_thi=float(h), xem=None) for t, h in diem])


def _kenh(n=8, *, ngay0=0, gia_tri=lambda i: 500 + 300 * i, tuoi=(48, 110)):
    """n video tham chiếu, mỗi ngày một video, tăng dần — số ở các tuổi `tuoi`."""
    return {"R%02d" % i: _c("R%02d" % i, ngay0 + i, *[(t, gia_tri(i) * (t / 110.0)) for t in tuoi])
            for i in range(n)}


# ── làm sạch chuỗi ──────────────────────────────────────────────────────────

def test_lam_sach_bo_ban_chep_trung_va_ban_hong():
    D = tt.Diem
    sach, bo = tt.lam_sach([
        D(25, 6899, 900), D(25.1, 6899, 900),          # cùng một lần chụp chép hai thư mục → một
        D(49, 0, 0),                                   # đọc 0 sau 6.899: số cộng dồn không giảm → hỏng
        D(72, 9000, 1200),
        D(96, 9000, 1200, tuoi_that=False),            # bản theo nhãn thư mục trùng số bản tuổi thật → bỏ
        D(120, 9500, 1300)])
    assert [d.tuoi for d in sach] == [25.1, 72, 120] and bo == 3
    # số LỚN đứng im ≥ 12h = bản cũ chép sang thư mục muộn → giữ bản SỚM; số nhỏ đứng im = video không được phát
    assert [d.tuoi for d in tt.lam_sach([D(59, 2068, 500), D(94, 2068, 500)])[0]] == [59]
    assert [d.tuoi for d in tt.lam_sach([D(40, 20, 1), D(150, 20, 1)])[0]] == [150]


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as f:
        f.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _moc(thu_muc_video, ten, dang, gio, imp, views=None, *, thong_tin=True, captured=True, tieu_de="t"):
    """Một thư mục chụp: raw mang `captured_at` = đăng + `gio` (giờ thật), tong-quan, có/không `_thong-tin.json`."""
    d = os.path.join(thu_muc_video, ten)
    tq = {"impressions": imp, "views": views if views is not None else (None if imp is None else imp // 10)}
    _ghi(os.path.join(d, "tong-quan.json"), tq)
    if thong_tin:
        _ghi(os.path.join(d, "_thong-tin.json"), {"tieu_de": tieu_de, "ngay_dang": dang.strftime("%Y-%m-%dT%H:%M:%S.000Z")})
    if captured:
        cap = (dang + dt.timedelta(hours=gio)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _ghi(os.path.join(d, "raw", "a_join_1.json"), {"captured_at": cap, "url": "x", "response": {}})


def test_doc_chuoi_tuoi_that_tu_captured_at_khong_tin_nhan_thu_muc(tmp_path):
    vd = str(tmp_path / "chi-so" / "vidGiaa25e1")
    dang = dt.datetime(2026, 10, 1, 9, 0)
    _moc(vd, "11h", dang, 10.9, 11)
    _moc(vd, "59h", dang, 59.3, 293)
    _moc(vd, "94h", dang, 59.3, 293, thong_tin=False)        # báo thức dồn chùm: thư mục "94h" mang số 59h
    _moc(vd, "79h", dang, 82.8, 2068, thong_tin=False)       # thiếu _thong-tin → giờ đăng lấy từ thư mục khác
    _moc(vd, "35h", dang, 82.7, 15)                          # số cũ lẫn vào lúc 82,7h: thấp hơn đỉnh → hỏng
    _moc(vd, "107h", dang, 106.9, 12475)
    _moc(vd, "203h", dang, 202.8, None)                      # Studio trả rỗng → bỏ
    _moc(vd, "48h", dang, 0, 400, captured=False, thong_tin=False)   # gói cũ không captured_at → tuổi theo nhãn
    c = tt.doc_chuoi(vd)
    assert c.ma == "vidGiaa25e1" and c.dang == _ts(dang)
    # bản nhãn "48h" (400) lệch thứ tự với bản tuổi thật 59,3h (293) → bỏ bản NHÃN, không bỏ bản tuổi thật
    assert [(round(d.tuoi, 1), d.hien_thi, d.tuoi_that) for d in c.diem] == [
        (10.9, 11, True), (59.3, 293, True), (82.8, 2068, True), (106.9, 12475, True)]
    assert c.bo == 3   # bản chép "94h", bản cũ 15 @82,7h, bản nhãn 48h


# ── giai đoạn: không bao giờ phán ở 48h ─────────────────────────────────────

def test_khong_phan_o_48h_chi_tin_hieu_som():
    ch = _kenh()
    ch["V"] = _c("V", 20, (22, 1470), (46, 2303))
    k = tt.danh_gia_mot("V", ch, tuoi_nay=50)
    assert k.nhan == tt.CHUA_DU and k.giai_doan == "som" and k.som_phan_vi is not None and not k.chot
    # cùng số 46h nhưng video đã 200h tuổi (số muộn rỗng): vẫn chưa phán — thiếu số, không đoán
    assert tt.danh_gia_mot("V", ch, tuoi_nay=200).nhan == tt.CHUA_DU


def test_ban_94h_duoc_dung_khi_video_da_qua_96h_ca_ai4byjmlpba():
    """Ca thật TL1: 2.303 @46h (thước 48h cũ: TRƯỢT, ngưỡng 6.000) → 28.624 @94h, bản 142h rỗng → THẮNG."""
    ch = _kenh(10, gia_tri=lambda i: 300 + 700 * i)          # tham chiếu @94h: ~250 → ~5.700
    ch["AI"] = _c("AI", 30, (22, 1470), (46, 2303), (94, 28624))
    assert tt.danh_gia_mot("AI", ch, tuoi_nay=90).nhan == tt.CHUA_DU          # chưa qua 96h: chờ
    k = tt.danh_gia_mot("AI", ch, tuoi_nay=150)
    assert k.nhan == tt.THANG and k.giai_doan == "phan_quyet_lui" and k.tuoi == 94 and k.phan_vi == 100
    assert k.do_tin < tt.danh_gia_mot("AI", dict(ch, AI=_c("AI", 30, (46, 2303), (110, 28624))), 150).do_tin


def test_uu_tien_ban_96_168h_roi_ban_som_nhat_sau_168h():
    ch = _kenh(tuoi=(48, 110, 160, 250))
    ch["V"] = _c("V", 20, (48, 100), (100, 1000), (150, 3000), (300, 90000))
    assert tt.danh_gia_mot("V", ch, 400).tuoi == 150                           # muộn nhất trong [96,168]
    ch["V"] = _c("V", 20, (48, 100), (200, 3000), (300, 90000))
    assert tt.danh_gia_mot("V", ch, 400).tuoi == 200                           # không có → sớm nhất sau 168h


# ── chống trôi: nhãn đông cứng từ 168h ──────────────────────────────────────

def test_nhan_khong_troi_khi_video_sau_ve_so_hay_ban_muon_moi():
    ch = _kenh(8)
    ch["V"] = _c("V", 9, (48, 2000), (110, 4000))
    truoc = tt.danh_gia_mot("V", ch, 300)
    # 10 video đăng SAU, nổ lớn, số chụp sau lúc chốt của V (đăng V + 168h) — không được kéo V xuống
    for i in range(10):
        ch["S%02d" % i] = _c("S%02d" % i, 12 + i, (48, 50000), (110, 90000))
    # bản chụp muộn mới của chính V (sau 168h) không đè bản 110h
    ch["V"] = _c("V", 9, (48, 2000), (110, 4000), (400, 4100))
    sau = tt.danh_gia_mot("V", ch, 500)
    assert (sau.nhan, sau.phan_vi, sau.tuoi) == (truoc.nhan, truoc.phan_vi, truoc.tuoi) == (tt.THANG, 100.0, 110)


def test_tham_chieu_ca_hai_phia_khong_chi_video_cu():
    """Kênh đang lớn: video đăng ngay sau (đã có số trước lúc chốt) vẫn là tham chiếu — so với chỉ video cũ sẽ thổi
    phồng nhãn thắng."""
    ch = _kenh(8, gia_tri=lambda i: 100 + 20 * i)                     # đời cũ: rất nhỏ
    ch["V"] = _c("V", 8, (110, 4000))
    for i in range(4):                                                # 4 video ngay sau, cùng kênh lớn hơn hẳn
        ch["S%d" % i] = _c("S%d" % i, 8 + (i + 1) * 0.5, (110, 9000 + i))
    k = tt.danh_gia_mot("V", ch, 200)
    assert k.phan_vi < 75 and k.nhan == tt.TRUNG_BINH


# ── nhãn + sàn ──────────────────────────────────────────────────────────────

def test_san_tuyet_doi_kenh_chet_va_thang_lon():
    chet = {"D%d" % i: _c("D%d" % i, i, (110, 5 + i)) for i in range(8)}
    k = tt.danh_gia_mot("D7", chet, 200)
    assert k.phan_vi == 100 and k.nhan == tt.TRUOT, "top kênh chết (12 hiển thị) vẫn là không được phát"
    ch = {"T%d" % i: _c("T%d" % i, i, (110, 30000 + 10000 * i)) for i in range(8)}
    assert tt.danh_gia_mot("T0", ch, 200).nhan == tt.THANG, "≥ 20.000 là thắng dù đáy của kênh rất mạnh"
    it = {"A": _c("A", 0, (110, 6000)), "B": _c("B", 1, (110, 100))}
    assert tt.danh_gia_mot("A", it, 200).nhan == tt.THANG and tt.danh_gia_mot("B", it, 200).nhan == tt.TRUOT
    it["C"] = _c("C", 2, (110, 1000))
    assert tt.danh_gia_mot("C", it, 200).nhan == tt.TRUNG_BINH                 # < 4 tham chiếu: sàn tuyệt đối


def test_phan_vi_dung_can_so_cong_don():
    # tham chiếu chỉ có bản 70h = 5.000 → ở 100h ít nhất 5.000 (cận dưới) → chắc chắn trên 4.000
    assert tt.phan_vi(4000, [tt.khoang_tai([tt.Diem(70, 5000, None)], 100)]) == (0.0, 0)
    assert tt.khoang_tai([tt.Diem(30, 5000, None)], 100) is None            # xa quá [60h, 160h]: không so
    lo, uoc, hi = tt.khoang_tai([tt.Diem(80, 1000, None), tt.Diem(120, 3000, None)], 100)
    assert (lo, uoc, hi) == (1000, 2000, 3000)


def test_xac_suat_cum_kem_hon_nen():
    assert tt.xac_suat_kem_hon(["truot"] * 7, ["thang", "thang", "trung_binh", "truot", "thang", "trung_binh"]) > 0.9
    assert tt.xac_suat_kem_hon(["truot"] * 3, ["thang", "trung_binh", "truot", "truot", "truot"]) < 0.9
    assert abs(tt.xac_suat_kem_hon(["thang", "truot"], ["thang", "truot"]) - 0.5) < 0.01
    assert tt.xac_suat_kem_hon([], ["thang"]) is None


def test_muc_thang():
    ch = {"M%d" % i: _c("M%d" % i, i, (96, 1000 * (i + 1))) for i in range(8)}
    assert tt.muc_thang(ch) == 6250.0                    # phân vị 75 của 1.000…8.000
    assert tt.muc_thang({"A": _c("A", 0, (96, 9))}) is None


# ── đường thật: V7 → ket_qua → tự học → sổ dự đoán ──────────────────────────

def _kenh_dia(goc, ma="TLX"):
    """Kênh trên đĩa: 6 video tham chiếu + video nổ muộn (vidGia685d6) + video thắng sớm 48h nhưng tắt."""
    tm = os.path.join(goc, "CHANNEL", ma)
    _ghi(os.path.join(tm, "kenh.yaml"), "ten: {0}\n".format(ma))
    goc_ngay = dt.datetime(2026, 9, 25, 22, 0)
    for i in range(6):
        vd = os.path.join(tm, "chi-so", "Ref%08d" % i)
        dang = goc_ngay + dt.timedelta(days=i)
        _moc(vd, "46h", dang, 46, 200 + 100 * i, tieu_de="ref %d" % i)
        _moc(vd, "94h", dang, 94, 4000 + 1500 * i, tieu_de="ref %d" % i)     # 4.000 … 11.500 @94h
    vd = os.path.join(tm, "chi-so", "vidGia685d6")
    dang = dt.datetime(2026, 10, 5, 22, 0, 37)
    _moc(vd, "22h", dang, 21.8, 1470, tieu_de="【脳科学】品格の正体")
    _moc(vd, "46h", dang, 45.8, 2303, tieu_de="【脳科学】品格の正体")
    _moc(vd, "94h", dang, 93.9, 28624, tieu_de="【脳科学】品格の正体")
    _moc(vd, "142h", dang, 93.9, None, thong_tin=False)          # bản 142h rỗng (thật ra chụp lúc 94h)
    vd = os.path.join(tm, "chi-so", "Som48hTat01")
    dang = dt.datetime(2026, 10, 3, 22, 0)
    _moc(vd, "46h", dang, 46, 7000, tieu_de="nổ sớm rồi tắt")      # thước 48h cũ: THẮNG
    _moc(vd, "110h", dang, 110, 7100, tieu_de="nổ sớm rồi tắt")
    return ma


def test_duong_that_v7_ket_qua_tu_hoc(tmp_path):
    goc = str(tmp_path)
    ma = _kenh_dia(goc)
    bay = dt.datetime(2026, 10, 12, 0, 0)
    vs = {v.ma: v for v in v7.video_cua_kenh(goc, ma, v7.CAU_HINH_MAC_DINH, bay)}
    ai = vs["vidGia685d6"]
    assert ai.hien_thi_48h is not None and ai.hien_thi_48h < 6000          # đúng cái thước cũ nhìn thấy
    assert ai.nhan_thang == "thang" and ai.thang and ai.tuoi_do == 93.9 and ai.hien_thi_do == 28624
    assert ket_qua.ket_luan(ai, {}, None) == "thang"
    som = vs["Som48hTat01"]
    assert som.nhan_thang == "trung_binh" and not som.thang, "7.000 @46h nhưng chỉ 7.100 @110h: không thắng"
    # tự học: ván cũ mang nhãn 48h sai → chấm lại theo thước chung
    for g, vid in (("TLX-0001", "vidGia685d6"), ("TLX-0002", "Som48hTat01")):
        _ghi(os.path.join(goc, "CHANNEL", ma, "ho-so-video", g + ".json"), {"ma_goi": g, "video_id": vid})
    tu_hoc._luu_van(goc, ma, {  # noqa: SLF001
        "TLX-0001": {"ma_goi": "TLX-0001", "nuoc": {"cum": "khac"}, "ket48": "truot", "ket_muon": "truot",
                     "du_doan": {"ket_cuc": "thắng"}, "dung": False},
        "TLX-0002": {"ma_goi": "TLX-0002", "nuoc": {"cum": "khac"}, "ket48": "thang", "ket_tv": "thang"}})
    r = tu_hoc.cham_van(goc, ma)
    van = tu_hoc.doc_van(goc, ma)
    a, b = van["TLX-0001"], van["TLX-0002"]
    assert a["ket"] == "thang" and a["ket48"] == "thang" and a["ket_lui"] is True and a["dung"] is True
    assert a["thuoc"] == tt.PHIEN_BAN and "ket_muon" not in a
    assert b["ket"] == "trung_binh" and b["ket48"] == "truot" and "ket_tv" not in b
    assert r["thang"] == 1 and r["da_phan"] == 2
    o = tu_hoc.bang_diem(goc, ma)["cum"]["khac"]
    assert o["thang"] == 1 and o["n"] == 2
    # chấm lại: nhãn ổn định, không ghi gì
    assert tu_hoc.cham_van(goc, ma)["ket"] == 0


def test_loi_tam_khong_xoa_nhan_da_cham(tmp_path, monkeypatch):
    goc = str(tmp_path)
    ma = _kenh_dia(goc)
    _ghi(os.path.join(goc, "CHANNEL", ma, "ho-so-video", "TLX-0001.json"), {"ma_goi": "TLX-0001", "video_id": "vidGia685d6"})
    tu_hoc.ghi_van(goc, ma, "TLX-0001", {"cum": "khac"})
    tu_hoc.cham_van(goc, ma)
    assert tu_hoc.doc_van(goc, ma)["TLX-0001"]["ket"] == "thang"

    def hong(*a, **k):
        raise OSError("ổ đĩa bận")

    monkeypatch.setattr(v7, "video_cua_kenh", hong)
    tu_hoc.cham_van(goc, ma)
    assert tu_hoc.doc_van(goc, ma)["TLX-0001"]["ket"] == "thang"          # giữ nhãn, không chấm bằng sàn
    assert any(d["nguon"] == "thuoc_thang" for d in tu_hoc.doc_canh_bao(goc))


def test_so_du_doan_giam_doc_cham_lai_theo_thuoc_chung(tmp_path):
    from core.giam_doc import so_thi_nghiem as stn

    goc = str(tmp_path)
    tm = os.path.join(goc, "CHANNEL", "K", "giam-doc")
    _ghi(os.path.join(tm, "du-doan.json"), {"kenh": "K", "du_doan": [
        {"video_id": "a", "ket": "truot", "ket_that": "truot", "dung": True},     # chấm bằng thước 48h cũ
        {"video_id": "b", "ket": "truot", "ket_that": "truot", "dung": True},
        {"video_id": "c", "ket": "thang"}]})
    tc = stn.cham_du_doan(goc, "K", {"a": "thang", "b": "", "c": "truot"})
    ds = {d["video_id"]: d for d in stn.doc_du_doan(goc, "K")}
    assert ds["a"]["ket_that"] == "thang" and ds["a"]["dung"] is False and ds["a"]["thuoc"] == tt.PHIEN_BAN
    assert "dung" not in ds["b"] and ds["b"]["thuoc"] == tt.PHIEN_BAN        # thước chung chưa phán: gỡ điểm cũ
    assert ds["c"]["dung"] is False and tc["moi"] == 3
    assert stn.cham_du_doan(goc, "K", {"a": "thang", "b": "", "c": "truot"})["moi"] == 0   # ổn định
