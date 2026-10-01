"""Phòng điều hành công ty (Đợt G, 01/10/2026) — phần DỮ LIỆU của `core.bang_dieu_khien` (mục 10), không Qt.

Cô lập: kênh giả trong `tmp_path` (`tests/test_giam_doc_plugin.dung_kenh_mau` + tệp tay), không mạng, không
sinh tiến trình thật.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os

from core import bang_dieu_khien as bdk
from core.giam_doc import du_lieu as dl

BAY = _dt.datetime(2026, 10, 1, 12, 0)


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _gd(goc, ma, ten):
    return os.path.join(goc, "CHANNEL", ma, "giam-doc", ten)


def _video(vid, tuoi, *, h48=None, kl="", thang=False, ctr_b=None, avd=None, hien_thi=None, ngay=None):
    chup = []
    if hien_thi is not None or ctr_b is not None or avd is not None:
        chup.append({"tuoi": float(tuoi), "hien_thi": hien_thi, "ctr_browse": ctr_b, "avd_pct": avd})
    return {"id": vid, "tieu_de": "Video " + vid, "tuoi_gio": tuoi, "hien_thi_48h": h48, "ket_luan": kl,
            "thang": thang, "dang_luc": ngay or (BAY - _dt.timedelta(hours=tuoi)), "chup": chup}


def _bs_gia(goc, ma, video, kenh_ngay=()):
    return dl.BangSo(goc=goc, ma_kenh=ma, bay_gio=BAY, video=list(video), kenh_ngay=list(kenh_ngay),
                     nguong_thang_48h=6000.0, ctr_muc_tieu=5.0, ypp={"sub": 30.0, "gio_xem": 167.0})


# ── thuật ngữ ──────────────────────────────────────────────────────────────


def test_thuat_ngu_doi_chu_ky_thuat_sang_chu_nguoi_thuong():
    assert bdk._thuat_ngu("CTR trang chủ 13% nhưng AVD thấp, gx_1k 2.9") == \
        "tỉ lệ bấm trang chủ 13% nhưng thời lượng xem TB thấp, giờ xem/1k hiển thị 2.9"
    assert "CTR" not in bdk._mot_cau("CTR chung 4%. Câu hai không lấy.")


# ── phần NẶNG: tinh_so_kenh ────────────────────────────────────────────────


def test_tinh_so_kenh_ba_cong_xep_loai_va_phan_quyet(tmp_path, monkeypatch):
    goc = str(tmp_path)
    video = [
        _video("v1", 16, hien_thi=25),                                   # mới, chưa đủ 48h
        _video("v2", 64, hien_thi=198, ctr_b=5.0, avd=40.0),             # quá 48h, thiếu bản 48h → lấy 198
        _video("v3", 125, h48=1709, kl="truot", ctr_b=13.3, avd=23.0, hien_thi=1709),
        _video("v4", 200, h48=15707, kl="thang", thang=True, ctr_b=10.8, avd=21.0, hien_thi=23729),
    ]
    kenh_ngay = [{"luc": BAY - _dt.timedelta(days=14), "xem": 0.0, "sub": 0.0, "gio_xem": 0.0, "hien_thi": 0.0},
                 {"luc": BAY - _dt.timedelta(days=7), "xem": 1000.0, "sub": 10.0, "gio_xem": 50.0, "hien_thi": 10000.0},
                 {"luc": BAY, "xem": 1500.0, "sub": 15.0, "gio_xem": 70.0, "hien_thi": 17000.0}]
    monkeypatch.setattr(dl, "tom_tat", lambda g, m, bay_gio=None: _bs_gia(g, m, video, kenh_ngay))
    _ghi(_gd(goc, "K1", "du-doan.json"), {"du_doan": [{"video_id": "v2", "ket": "truot", "ly_do": "ít hiển thị"}]})

    so = bdk.tinh_so_kenh(goc, "K1", bay_gio=BAY)

    cong = {c["ten"]: c for c in so["cong"]}
    # Trung vị (198, 1709, 15707) = 1709 < 50% × 6000 → đỏ; không xanh oan vì chỉ video thắng có số 48h.
    assert cong["Hiển thị"]["muc"] == bdk.HONG and cong["Hiển thị"]["gia_tri"] == 1709
    assert cong["Tỉ lệ bấm trang chủ"]["muc"] == bdk.TOT
    assert cong["Giữ chân"]["muc"] == bdk.TOT and cong["Giữ chân"]["chuan"] == 21.0
    # Hiển thị 7 ngày 7000 / tuần trước 10000 = 0,7 → tụt (`tong.xep_loai`).
    assert so["da"] == 0.7 and so["loai"] == "tut"
    assert so["tuan"]["nay"]["xem"] == 500 and so["tuan"]["truoc"]["xem"] == 1000
    assert [v["ket"] for v in so["video"]] == ["cho", "cho", "truot"]
    assert so["video"][1]["doan"] == "truot"
    json.dumps(so)  # ghi được ra bộ đệm


def test_tinh_so_kenh_chay_that_tren_kenh_mau(tmp_path):
    """Không giả `tom_tat`: kênh mẫu của giám đốc kênh — chỉ cần chạy trọn, ra đủ khung."""
    from tests.test_giam_doc_plugin import dung_kenh_mau

    goc = str(tmp_path)
    dung_kenh_mau(goc)
    so = bdk.tinh_so_kenh(goc, "GD1")
    assert so["loai"] in bdk.XEP_LOAI
    assert [c["ten"] for c in so["cong"]] == ["Hiển thị", "Tỉ lệ bấm trang chủ", "Giữ chân"]
    assert len(so["video"]) == 3 and so["tuan"]["nay"]["xem"] is not None


def test_bo_dem_so_kenh_tinh_lai_khi_du_lieu_doi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"), "ma: K1\n")
    monkeypatch.setattr(bdk, "tinh_so_kenh", lambda g, m, bay_gio=None: {
        "ma": m, "luc": BAY.isoformat(), "chu_ky": bdk._chu_ky_so_kenh(g, m), "loai": "chung"})
    assert bdk.so_kenh_cu(goc, "K1", bay_gio=BAY)
    bdk.tinh_va_luu(goc, "K1", bay_gio=BAY)
    assert bdk.doc_so_kenh(goc, "K1")["loai"] == "chung"
    assert not bdk.so_kenh_cu(goc, "K1", bay_gio=BAY + _dt.timedelta(hours=1))
    assert bdk.so_kenh_cu(goc, "K1", bay_gio=BAY + _dt.timedelta(hours=7)), "cũ quá 6 giờ phải tính lại"
    _ghi(_gd(goc, "K1", "bao-cao.json"), {"chan_doan": "mới"})
    assert bdk.so_kenh_cu(goc, "K1", bay_gio=BAY + _dt.timedelta(hours=1)), "giám đốc ghi tệp mới → tính lại"


def test_cli_tinh_so_ghi_bo_dem_va_go_khoa(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.chdir(goc)
    monkeypatch.setattr(bdk, "tinh_so_kenh", lambda g, m, bay_gio=None: {"ma": m, "luc": BAY.isoformat()})
    _ghi(bdk._duong_khoa_tinh(goc), {"pid": os.getpid(), "luc": 0})
    assert bdk._main(["tinh-so", "K1", "K2"]) == 0
    assert bdk.doc_so_kenh(goc, "K2")["ma"] == "K2"
    assert not os.path.exists(bdk._duong_khoa_tinh(goc))
    assert bdk._main([]) == 2


def test_sinh_tinh_so_khong_sinh_khi_dang_tinh(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi(bdk._duong_khoa_tinh(goc), {"pid": os.getpid(), "luc": _dt.datetime.now().timestamp()})
    assert bdk.dang_tinh(goc)
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được sinh")))
    assert bdk.sinh_tinh_so(goc, ["K1"]) == 0
    assert bdk.sinh_tinh_so(goc, []) == 0


# ── phần NHẸ ───────────────────────────────────────────────────────────────


def test_doi_ai_noi_doc_so_chuyen_gia_truoc(tmp_path):
    goc = str(tmp_path)
    _ghi(_gd(goc, "K1", "bao-cao.json"), {"chan_doan": "Cổng hiển thị hỏng. Câu hai.", "luc": "2026-10-01T10:00"})
    ra = bdk.doi_ai_noi(goc, "K1")
    assert ra == [{"ai": "Giám đốc kênh", "cau": "Cổng hiển thị hỏng.", "luc": "2026-10-01T10:00"}]
    _ghi(_gd(goc, "K1", "doi-ai.json"), {"nen_tang": {"cau": "CTR trang chủ ổn.", "luc": "x"},
                                         "chu_de": {"cau": "Cụm IQ đang lên."}})
    ra = bdk.doi_ai_noi(goc, "K1")
    assert [x["ai"] for x in ra] == ["Nền tảng", "Chủ đề"]
    assert ra[0]["cau"] == "tỉ lệ bấm trang chủ ổn."


def test_doi_ai_noi_lui_ve_kham_nghiem(tmp_path):
    goc = str(tmp_path)
    _ghi(_gd(goc, "K1", os.path.join("kham-nghiem", "vid1-48h.json")),
         {"video_id": "vid1", "moc": "48h", "luc": "2026-10-01T12:00", "ket": {"chan_doan": "Giữ chân tốt 40%."}})
    ra = bdk.doi_ai_noi(goc, "K1")
    assert ra[0]["ai"] == "Khám nghiệm" and "vid1" in ra[0]["cau"]


def test_dang_thu_thi_nghiem_mo_hoac_goi_y(tmp_path):
    goc = str(tmp_path)
    assert bdk.dang_thu(goc, "K1") == []
    _ghi(_gd(goc, "K1", "bao-cao.json"), {"che_do": "goi_y", "se_lam": [
        {"loai": "tham_so", "khoa": "phut_muc_tieu", "cu": 15, "moi": 20}]})
    assert bdk.dang_thu(goc, "K1") == ["Định thử (chưa áp): phut_muc_tieu: 15 → 20"]
    _ghi(_gd(goc, "K1", "thi-nghiem.json"), {"thi_nghiem": [
        {"id": "t1", "viec": "cuu_ctr", "gia_thuyet": "Đổi tiêu đề nâng CTR", "trang_thai": "mo"}]})
    assert bdk.dang_thu(goc, "K1") == ["Cứu tỉ lệ bấm: Đổi tiêu đề nâng tỉ lệ bấm"]


def test_lich_dang_tiep_hai_khe_kem_video_da_xep(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"), 'ma: K1\nnhip_dang: "05:00, 20:00"\n')
    k = {"ma": "K1", "ke_hoach": [{"ngay": "01/10/2026", "gio": "20:00", "tieu_de": "Video tối", "loai": "sap_dang"}]}
    ra = bdk.lich_dang_tiep(goc, k, bay_gio=BAY)
    assert [x["chu_luc"] for x in ra] == ["20:00 hôm nay", "05:00 mai"]
    assert ra[0]["tieu_de"] == "Video tối" and ra[1]["tieu_de"] == ""


def test_muc_phong_kenh_tut_la_do():
    k_tot = {"bay_gio": {"muc": "dang", "chu": "Đang làm video"}}
    assert bdk.muc_phong(k_tot, {"loai": "len"}) == bdk.TOT
    assert bdk.muc_phong(k_tot, {"loai": "tut"}) == bdk.HONG
    assert bdk.muc_phong({"bay_gio": {"muc": "cho", "chu": "Chờ duyệt"}}, {}) == bdk.LUU_Y
    assert bdk.muc_phong({"bay_gio": {"muc": "loi"}}, {"loai": "len"}) == bdk.HONG


def test_tong_tuan_chi_so_kenh_co_du_hai_tuan():
    cac = [{"tuan": {"nay": {"xem": 100.0}, "truoc": {"xem": 200.0}}},
           {"tuan": {"nay": {"xem": 50.0}, "truoc": {"xem": None}}}]
    t = bdk._tong_tuan(cac)
    assert t["xem"] == {"nay": 150.0, "pct": -50}
    assert t["sub"] == {"nay": None, "pct": None}


def test_phong_dieu_hanh_xep_kenh_do_len_dau_va_bao_can_tinh(tmp_path, monkeypatch):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "ma: {0}\n".format(ma))
    _ghi(bdk._duong_so_kenh(goc, "K2"), {"ma": "K2", "luc": BAY.isoformat(), "chu_ky": bdk._chu_ky_so_kenh(goc, "K2"),
                                         "loai": "tut"})
    bang = {"kenh": [{"ma": "K1", "bay_gio": {"muc": "dang", "chu": "Đang làm video"}, "ypp": {"dang_ky": 30}},
                     {"ma": "K2", "bay_gio": {"muc": "dang", "chu": "Đang làm video"}}],
            "kenh_khac": [], "viec": [{"khoa": "x"}], "may": {}}
    ph = bdk.phong_dieu_hanh(goc, bang, bay_gio=BAY + _dt.timedelta(minutes=5))
    assert ph["thu_tu"] == ["K2", "K1"]
    assert ph["can_tinh"] == ["K1"]
    assert ph["the"]["K1"]["ypp"]["sub"] == 30.0 and ph["the"]["K1"]["ypp"]["can_gio"] == 4000
    assert ph["cong_ty"]["so_viec"] == 1


# ── ba trang chi tiết ──────────────────────────────────────────────────────


def _bai_kn(**kw):
    b = {"pham_vi": "kenh", "truc": "hook", "cum": "tri-tue", "cau": "Đi thẳng vào nội dung trong 30s đầu.",
         "n": 1, "tin_cay": "thap", "bom": False, "bong": True, "video": ["aV4P"], "nguon": "kham_nghiem",
         "khoa": "hook|ngan_gon|+|tri-tue"}
    b.update(kw)
    return b


def test_gach_bai_kham_nghiem_go_khoi_so_va_ghi_so_gach(tmp_path, monkeypatch):
    from core.chien_luoc import bai_hoc
    from core.giam_doc import kham_nghiem

    goc = str(tmp_path)
    dong = [{"truc": "hook", "gia_tri": "ngan_gon", "huong": "+", "cum": "tri-tue", "cau": "Hook 65% có số 30s.",
             "video_id": "aV4P", "moc": "7d", "luc": "2026-10-01T12:00"},
            {"truc": "tieu_de", "gia_tri": "so_dem", "huong": "-", "cum": "tri-tue", "cau": "Tiêu đề 5% có số.",
             "video_id": "hTiU", "moc": "48h", "luc": "2026-10-01T12:00"}]
    _ghi(_gd(goc, "K1", "bai-hoc.jsonl"), "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dong))
    monkeypatch.setattr(bai_hoc, "doc", lambda g, m, tat_ca=False, bay_gio=None: [
        _bai_kn(), {"pham_vi": "nhom", "truc": "cum_thang_truot", "cum": "x", "cau": "cụm x 1/3", "n": 3}])

    ds = bdk.so_bai_hoc(goc, "K1")
    assert [(d["ten_chuyen_gia"], d["ten_pham_vi"]) for d in ds] == [("Khán giả", "Kênh này"), ("Chủ đề", "Nhóm kênh")]
    ghi = bdk.gach_bai_hoc(goc, "K1", ds[0], bay_gio=BAY)
    assert ghi["da_loai_khoi_loi_nhac"] and ghi["ma_bai"] == "kn:hook|ngan_gon|tri-tue"
    con = kham_nghiem.doc_bai_hoc(goc, "K1", bay_gio=BAY)
    assert [b["truc"] for b in con] == ["tieu_de"], "bài đã gạch không còn trong nguồn của lời nhắc"
    assert bdk.khoa_bai_hoc_gach(goc, "K1") == {"kn:hook|ngan_gon|tri-tue"}

    monkeypatch.setattr(bai_hoc, "doc", lambda g, m, tat_ca=False, bay_gio=None: [])
    ds = bdk.so_bai_hoc(goc, "K1")
    assert len(ds) == 1 and ds[0]["da_gach"] and ds[0]["video"] == ["aV4P"]


def test_gach_bai_nguon_khac_chi_ghi_so(tmp_path):
    goc = str(tmp_path)
    b = {"pham_vi": "kenh", "truc": "cong_thuc", "cum": "v7", "cau": "Công thức v7: 1/3 thắng", "n": 3}
    ghi = bdk.gach_bai_hoc(goc, "K1", b)
    assert not ghi["da_loai_khoi_loi_nhac"] and ghi["ma_bai"].startswith("h:")
    assert bdk.ma_bai(b) in bdk.khoa_bai_hoc_gach(goc, "K1")


def test_so_quyet_dinh_ti_le_dung_theo_loai(tmp_path):
    goc = str(tmp_path)
    _ghi(_gd(goc, "K1", "du-doan.json"), {"du_doan": [
        {"video_id": "a", "ket": "truot", "ly_do": "CTR thấp", "luc": "2026-09-28T10:00", "dung": True, "ket_that": "truot"},
        {"video_id": "b", "ket": "thang", "ly_do": "?", "luc": "2026-09-29T10:00", "dung": False, "ket_that": "truot"},
        {"video_id": "c", "ket": "truot", "ly_do": "?", "luc": "2026-09-30T10:00"}]})
    _ghi(_gd(goc, "K1", "thi-nghiem.json"), {"thi_nghiem": [
        {"id": "t1", "viec": "do_dai", "gia_thuyet": "20 phút", "trang_thai": "giu", "bat_dau": "2026-09-20T00:00",
         "ket_luan": {"ly_do": "+15%"}}]})
    _ghi(_gd(goc, "K1", "nhat-ky.jsonl"), json.dumps({"luc": "2026-10-01T10:20", "viec": "luot", "sau": {
        "che_do": "goi_y", "chon": 0, "thuc_don": 2, "du_doan_moi": 1}, "ly_do_llm": "Cổng HIỂN THỊ hỏng"}) + "\n")
    du = bdk.so_quyet_dinh(goc, "K1")
    # Tỉ lệ đúng = `giam_doc.hoi_dong.do_chinh_xac` (định nghĩa của hội đồng), số quyết định = cả bài chưa chấm.
    ti = {t["loai"]: t for t in du["ti_le"]}
    assert (ti["du_doan"]["dung"], ti["du_doan"]["tong"], ti["du_doan"]["so_quyet"]) == (1, 2, 3)
    assert (ti["doi_chuan"]["dung"], ti["doi_chuan"]["tong"]) == (1, 1)
    assert ti["du_doan"]["quyen"] == "goi_y"
    assert "luot" not in ti, "loại không chấm được không vào dòng tỉ lệ đúng"
    assert not os.path.exists(_gd(goc, "K1", "do-chinh-xac.json")), "trang chỉ ĐỌC, không ghi sổ độ chính xác"
    assert du["dong"][0]["loai"] == "luot" and "chọn 0/2" in du["dong"][0]["quyet"]
    assert any("tỉ lệ bấm thấp" == d["vi_sao"] for d in du["dong"]), "chữ AI đã đổi thuật ngữ"


def test_bao_cao_tuan_doc_ca_kenh_va_cong_ty(tmp_path):
    goc = str(tmp_path)
    _ghi(_gd(goc, "K1", "BAO-CAO-TUAN.md"), "# Báo cáo\nCTR ổn")
    _ghi(os.path.join(goc, "workspace", "tong-giam-doc", "BAO-CAO-CONG-TY.md"), "# Công ty")
    du = bdk.bao_cao_tuan(goc, "K1")
    assert du["kenh"] == "# Báo cáo\ntỉ lệ bấm ổn" and du["cong_ty"] == "# Công ty"


def test_so_quyet_dinh_tu_dem_khi_khong_co_hoi_dong(tmp_path, monkeypatch):
    import sys

    goc = str(tmp_path)
    _ghi(_gd(goc, "K1", "du-doan.json"), {"du_doan": [{"video_id": "a", "ket": "truot", "dung": True, "luc": "x"}]})
    monkeypatch.setitem(sys.modules, "core.giam_doc.hoi_dong", None)
    ti = {t["loai"]: t for t in bdk.so_quyet_dinh(goc, "K1")["ti_le"]}
    assert (ti["du_doan"]["dung"], ti["du_doan"]["tong"]) == (1, 1)


def test_doi_ai_noi_doc_phien_hoi_dong_cuoi(tmp_path):
    goc = str(tmp_path)
    pa = json.dumps({"chan_doan": "CTR trang chủ 13% nhưng hiển thị hỏng. Câu hai.", "chon": []}, ensure_ascii=False)
    _ghi(_gd(goc, "K1", "hoi-dong-cuoi.json"), {"kham_nghiem": {
        "luc": "2026-10-01T12:41:10", "loai": "kham_nghiem", "quyet": {"chon": "khan_gia"},
        "chuyen_gia": [{"ma": "nen_tang", "phuong_an": pa},
                       {"ma": "khan_gia", "phuong_an": pa[:40] + "…", "luan_diem": [{"cau": "Giữ chân 30s 70%.", "giu": True}]},
                       {"ma": "chu_de", "loai_bo": True, "phuong_an": pa}]}})
    _ghi(_gd(goc, "K1", "bao-cao.json"), {"chan_doan": "Giám đốc nói."})
    ra = bdk.doi_ai_noi(goc, "K1")
    assert [x["ai"] for x in ra] == ["Nền tảng", "Khán giả ★"], "chuyên gia bị loại vì số bịa không nói"
    assert ra[0]["cau"] == "tỉ lệ bấm trang chủ 13% nhưng hiển thị hỏng."
    assert ra[1]["cau"].startswith("tỉ lệ bấm trang chủ"), "phương án bị cắt vẫn lấy được câu chẩn đoán"


def test_bai_hoc_so_chuyen_gia_va_gach_go_khoi_so(tmp_path, monkeypatch):
    from core.chien_luoc import bai_hoc
    from core.giam_doc import hoi_dong

    goc = str(tmp_path)
    monkeypatch.setattr(bai_hoc, "doc", lambda g, m, tat_ca=False, bay_gio=None: [])
    duong = hoi_dong.duong_so(goc, "K1", "khan_gia")
    dong = [{"luc": "1", "chuyen_gia": "khan_gia", "kenh": "K1", "video_id": "v1", "moc": "7d", "khoa": "vach_rot",
             "cau": "Vách rớt 11% ở giây 68.", "bong": True},
            {"luc": "2", "chuyen_gia": "khan_gia", "kenh": "K1", "video_id": "v2", "moc": "7d", "khoa": "vach_rot",
             "cau": "Vách rớt 9% ở giây 70.", "bong": True},
            {"luc": "3", "chuyen_gia": "khan_gia", "kenh": "K1", "video_id": "v3", "moc": "48h", "khoa": "hook",
             "cau": "Hook 30s giữ 70%.", "bong": True}]
    _ghi(duong, "".join(json.dumps(d, ensure_ascii=False) + chr(10) for d in dong))
    ds = bdk.so_bai_hoc(goc, "K1")
    vr = next(d for d in ds if d["khoa"] == "vach_rot")
    assert (vr["ten_chuyen_gia"], vr["ten_pham_vi"], vr["n"], vr["video"]) ==         ("Khán giả", "Sổ chuyên gia · kênh này", 2, ["v1", "v2"])
    ghi = bdk.gach_bai_hoc(goc, "K1", vr)
    assert ghi["da_loai_khoi_loi_nhac"] and len(ghi["dong_goc"]) == 2
    assert [x for x in hoi_dong.doc_so(goc, "K1", "khan_gia") if "Vách" in x] == [], "đã ra khỏi lời nhắc chuyên gia"
    assert any("Hook" in x for x in hoi_dong.doc_so(goc, "K1", "khan_gia"))
    ds = bdk.so_bai_hoc(goc, "K1")
    assert next(d for d in ds if d["khoa"] == "vach_rot")["da_gach"]
