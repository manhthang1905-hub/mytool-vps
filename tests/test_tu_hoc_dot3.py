"""Tests đợt 3 tự học: sổ bài học có bộ đếm (delta cong/tru/them) + hiệu chỉnh dự đoán biên tập."""

from __future__ import annotations

import datetime as _dt
import io
import json
import os

from core import tu_hoc
from core.chien_luoc import bai_hoc
from core.giam_doc import kham_nghiem as kn

BAI = {"truc": "hook", "gia_tri": "nghich_ly", "cum": ""}


def _ghi_dong(goc, ma, dong):
    tm = os.path.join(goc, "CHANNEL", ma, "giam-doc")
    os.makedirs(tm, exist_ok=True)
    with io.open(os.path.join(tm, kn.TEP_BAI_HOC), "a", encoding="utf-8") as tep:
        for d in dong:
            tep.write(json.dumps(d, ensure_ascii=False) + "\n")


def _goc_bai(goc, ma="K", video="A", gia_tri="nghich_ly", cau="Hook nghịch lý giữ 62% ở 0:30."):
    _ghi_dong(goc, ma, [{"truc": "hook", "gia_tri": gia_tri, "huong": "+", "cum": "", "video_id": video, "moc": "48h",
                         "cau": cau, "bong": True, "luc": _dt.datetime.now().isoformat()}])
    return kn.id_bai("hook", gia_tri, "")


def _bai(goc, ma="K"):
    return {b["id"]: b for b in kn.doc_bai_hoc(goc, ma)}


def test_trang_thai_nguong():
    tt = kn.trang_thai
    assert tt(0, 0) == "gia_thuyet" and tt(2, 0) == "gia_thuyet"
    assert tt(3, 0) == "that" and tt(3, 1) == "that" and tt(4, 2) == "that"
    assert tt(3, 2) == "gia_thuyet"            # 3 < 2×2
    assert tt(1, 2) == "gia_thuyet" and tt(0, 2) == "bo" and tt(1, 3) == "bo" and tt(5, 7) == "bo"
    assert tt(9, 0, gach=True) == "bo"          # chủ gạch: luôn bỏ


def test_ap_delta_cong_tru_them_va_chong_lap(tmp_path):
    goc = str(tmp_path)
    bid = _goc_bai(goc)
    assert _bai(goc)[bid]["trang_thai"] == "gia_thuyet" and _bai(goc)[bid]["cong"] == 1
    ap = lambda vid, delta: kn.ap_delta(goc, "K", delta, vid, "48h", _dt.datetime.now().isoformat())  # noqa: E731
    assert ap("B", [{"op": "cong", "id": bid}])["cong"] == 1
    # chống lặp: cùng video cộng/trừ lại, hoặc video gốc (A) cộng lại → bỏ qua
    assert ap("B", [{"op": "cong", "id": bid}])["bo_qua"] == 1
    assert ap("B", [{"op": "tru", "id": bid}])["bo_qua"] == 1
    assert ap("A", [{"op": "cong", "id": bid}])["bo_qua"] == 1
    assert _bai(goc)[bid]["cong"] == 2
    assert ap("C", [{"op": "cong", "id": bid}])["cong"] == 1
    b = _bai(goc)[bid]
    assert (b["cong"], b["tru"], b["trang_thai"], b["bom"]) == (3, 0, "that", True)
    assert {x["video_id"] for x in b["bang_chung"]} == {"A", "B", "C"}
    # trừ: D bác bỏ → cong 3, tru 1 vẫn thật; thêm E, F bác bỏ → 3 < 2×3 → giả thuyết
    assert ap("D", [{"op": "tru", "id": bid}])["tru"] == 1 and _bai(goc)[bid]["trang_thai"] == "that"
    ap("E", [{"op": "tru", "id": bid}])
    assert _bai(goc)[bid]["trang_thai"] == "gia_thuyet"
    for v in ("F", "G", "H"):
        ap(v, [{"op": "tru", "id": bid}])
    assert _bai(goc)[bid]["trang_thai"] == "bo"          # tru 5 ≥ cong 3 + 2
    # id lạ, bài đã bỏ → bỏ qua; "them" tạo bài mới 1 lần, "them" trùng chữ = cộng
    assert ap("Z", [{"op": "cong", "id": "bffffff"}, {"op": "cong", "id": bid}])["bo_qua"] == 2
    kq = ap("M", [{"op": "them", "noi_dung": "Tiêu đề có số 7 giữ CTR 6%."}])
    assert kq["them"] == 1
    kq = ap("N", [{"op": "them", "noi_dung": "tiêu đề có số 7  giữ CTR 6%."}])
    assert kq["them"] == 0 and kq["cong"] == 1
    moi = [b for b in kn.doc_bai_hoc(goc, "K") if b["truc"] == "tu_do"]
    assert len(moi) == 1 and moi[0]["cong"] == 2 and moi[0]["trang_thai"] == "gia_thuyet"
    # tối đa 3 thao tác mỗi lần
    nhieu = [{"op": "them", "noi_dung": "Bài số {0} có 5 video.".format(i)} for i in range(5)]
    assert ap("P", nhieu)["them"] == 3


def test_delta_doc_ket_qua_giu_khoa_cu():
    tho = json.dumps({"chan_doan": "Hiển thị 1.200 thấp.", "cong_hong": "ctr", "delta": [
        {"op": "cong", "id": "b123abc"}, {"op": "tru", "id": "hỏng"}, {"op": "them", "noi_dung": "không có số"},
        {"op": "them", "noi_dung": "Hook 30 giây giữ 60%."}, {"op": "xoa", "id": "b123abc"}, {"op": "cong", "id": "b000000"},
        {"op": "cong", "id": "b999999"}]}, ensure_ascii=False)
    k = kn.doc_ket_qua(tho, {})
    assert k["chan_doan"] and "bai_hoc" in k and "so_dan" in k          # định dạng cũ còn nguyên
    assert [d["op"] for d in k["delta"]] == ["cong", "them", "cong"]    # ≤ 3, bỏ op/id/nội dung sai
    assert "delta" not in kn.doc_ket_qua(json.dumps({"chan_doan": "Có số 3."}), {})


def test_gach_la_bo_va_khong_them_lai(tmp_path):
    goc = str(tmp_path)
    bid = _goc_bai(goc)
    for v in ("B", "C"):
        kn.ap_delta(goc, "K", [{"op": "cong", "id": bid}], v, "48h", _dt.datetime.now().isoformat())
    assert _bai(goc)[bid]["trang_thai"] == "that"
    tm = os.path.join(goc, "CHANNEL", "K", "giam-doc")
    with io.open(os.path.join(tm, "bai-hoc-gach.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"ma_bai": kn.ma_bai_kn("hook", "nghich_ly", "")}) + "\n")
    assert _bai(goc)[bid]["trang_thai"] == "bo" and not _bai(goc)[bid]["bom"]


def test_loi_nhac_co_so_bai_va_delta(tmp_path):
    goc = str(tmp_path)
    bid = _goc_bai(goc)
    so = kn.doc_bai_hoc(goc, "K")
    hs = {"moc": "48h", "ban_chup": "50h", "so_lieu": {"x": 1}, "chu": {
        "tieu_de": "t", "ngay_dang": "d", "phut": 10, "cum": [], "cong_thuc": "v7", "ket_luan": "thang", "chu_bia": "",
        "bia": {}, "kich_ban": {}, "tieu_de_ung_vien": [], "tieu_de_ly_do": "", "hook_30s": "", "vach": "",
        "cau_tai_vach": "", "su_that_luot": [], "pool": [], "bien_tap": {}, "du_doan_giam_doc": {}, "binh_luan": []}}
    ln = kn.loi_nhac(hs, "", "K", so)
    assert bid in ln and "cong 1/tru 0" in ln and '"delta"' in ln and kn.DANG_TRA_LOI in ln
    assert "SỔ BÀI HỌC HIỆN CÓ" not in kn.loi_nhac(hs, "", "K", [])


def _kn_dong(truc_ten, cong, tru, tt, cau):
    return {"nguon": "kham_nghiem", "truc": "hook", "cau": cau, "cong": cong, "tru": tru, "trang_thai": tt}


def test_bom_chi_that_va_toi_da_2_gia_thuyet():
    ds = [_kn_dong("t", c, 0, "that", "that%d" % c) for c in (3, 4, 5, 6, 7, 8, 9)]
    ds += [_kn_dong("g", c, 0, "gia_thuyet", "gt%d" % c) for c in (1, 2, 1)]
    ds += [_kn_dong("b", 0, 3, "bo", "bo")]
    that, gt = bai_hoc.chon_bai_kham_nghiem(ds)
    assert [b["cau"] for b in that] == ["that9", "that8", "that7", "that6", "that5"]     # ≤ 5, cong − tru giảm
    assert len(gt) == 2 and gt[0]["cau"] == "gt2" and all(b["trang_thai"] == "gia_thuyet" for b in gt)


def test_khoi_kham_nghiem_nhan_dang_kiem(tmp_path):
    goc = str(tmp_path)
    bid = _goc_bai(goc, gia_tri="la")
    for v in ("B", "C"):
        kn.ap_delta(goc, "K", [{"op": "cong", "id": bid}], v, "48h", _dt.datetime.now().isoformat())
    _goc_bai(goc, gia_tri="moi", cau="Hook mới 1 video thử.", video="Q")
    ra = bai_hoc.khoi_kham_nghiem(goc, "K", "kich_ban").splitlines()
    assert len(ra) == 2 and not ra[0].startswith("- (đang kiểm") and ra[1].startswith("- (đang kiểm, chưa chắc)")


# ── Phần B: hiệu chỉnh ─────────────────────────────────────────────────────

def _van(goc, ma, ma_goi, ctr_doan, lech_ctr, avd_lech=None, dung=None):
    v = tu_hoc.doc_van(goc, ma)
    v[ma_goi] = {"ma_goi": ma_goi, "nuoc": {}, "du_doan": {"ctr_so": ctr_doan}, "lech": {}}
    if lech_ctr is not None:
        v[ma_goi]["lech"]["ctr"] = lech_ctr
    if avd_lech is not None:
        v[ma_goi]["lech"]["avd"] = avd_lech
    if dung is not None:
        v[ma_goi]["dung"] = dung
    tu_hoc._luu_van(goc, ma, v)


def test_hieu_chinh_n_nho_thi_rong(tmp_path):
    goc = str(tmp_path)
    assert tu_hoc.hieu_chinh(goc, "K") == {} and tu_hoc.cau_hieu_chinh(goc, "K") == ""
    _van(goc, "K", "1", 6.0, 2.0, dung=True)
    assert tu_hoc.hieu_chinh(goc, "K") == {} and tu_hoc.cau_hieu_chinh(goc, "K") == ""


def test_hieu_chinh_dung_so(tmp_path):
    goc = str(tmp_path)
    # đoán 6 thật 4 (+50%), đoán 8 thật 4 (+100%), đoán 3 thật 4 (−25%): trung bình +41,7%
    _van(goc, "K", "1", 6.0, 2.0, avd_lech=30, dung=True)
    _van(goc, "K", "2", 8.0, 4.0, avd_lech=-10, dung=True)
    _van(goc, "K", "3", 3.0, -1.0, avd_lech=10, dung=False)
    h = tu_hoc.hieu_chinh(goc, "K")
    assert h["n"] == 3 and h["lech_ctr_pct"] == 41.7 and h["lech_avd_giay"] == 10.0
    assert (h["dung"], h["tong_dung"], h["ti_le_dung"]) == (2, 3, 0.67)
    assert tu_hoc.cau_hieu_chinh(goc, "K") == ("Hiệu chỉnh từ 3 video: bạn đoán CTR cao hơn thật trung bình 41.7%; "
                                              "đoán AVD cao hơn thật trung bình 10 giây; đoán thắng/trượt đúng 2/3.")
    md = open(tu_hoc.ghi_bang_diem_md(goc, "K"), encoding="utf-8").read()
    assert "Trình độ dự đoán: đúng 2/3 (67%); lệch CTR +41.7%" in md


def test_hieu_chinh_vao_tu_sua_va_do_chinh_xac(tmp_path):
    from core import bien_tap_content as bt
    from core.giam_doc import hoi_dong

    goc = str(tmp_path)
    _van(goc, "K", "1", 6.0, 2.0, dung=True)
    _van(goc, "K", "2", 3.0, -1.0, dung=False)
    assert "Hiệu chỉnh từ 2 video" in bt.doc_bai_hoc_bien_tap(goc, "K")
    dcx = hoi_dong.do_chinh_xac(goc, "K", ghi=False)["loai"]["du_doan_bien_tap"]
    assert (dcx["n"], dcx["dung"], dcx["ti_le"]) == (2, 1, 0.5)
