"""Giám đốc kênh — sổ đăng ký, bảng số, 5 việc đợt 1, bộ não (LLM giả), một lượt chạy trọn.

Cô lập: kênh giả dựng trong `tmp_path` từ `tests/du-lieu/giam-doc/kenh-mau.json`; không mạng, không ví,
không đọc/ghi CHANNEL thật.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re

from core import giam_doc
from core.giam_doc import bao_cao, cuu_ctr, dan_cum, do_dai, du_lieu, muc_tieu_ypp, quan_ly, suc_khoe
from core.giam_doc.du_lieu import BangSo

MAU = os.path.join(os.path.dirname(__file__), "du-lieu", "giam-doc", "kenh-mau.json")
BAY = _dt.datetime(2026, 10, 1, 12, 0)


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def dung_kenh_mau(goc, ma="GD1"):
    """Dựng kênh giả trên đĩa theo kenh-mau.json (tuổi video tính theo giờ thật lúc chạy)."""
    with io.open(MAU, encoding="utf-8") as tep:
        mau = json.load(tep)
    tm = os.path.join(goc, "CHANNEL", ma)
    _ghi(os.path.join(tm, "kenh.yaml"), "\n".join(mau["kenh_yaml"]) + "\n")
    bay = _dt.datetime.now()
    k = mau["kenh_theo_ngay"]
    dong = ["Lúc chụp,Lượt xem,Giờ xem,Đăng ký,Lượt hiển thị,Tỷ lệ bấm"]
    for i in range(k["so_ngay"], -1, -1):
        n = k["so_ngay"] - i
        dong.append('"{0:%Y-%m-%d %H:%M}","{1}","{2}","{3}","{4}","5.0"'.format(
            bay - _dt.timedelta(days=i), n * k["xem_moi_ngay"], n * k["gio_moi_ngay"], n * k["sub_moi_ngay"],
            n * k["hien_thi_moi_ngay"]))
    _ghi(os.path.join(tm, "chi-so", "kenh-theo-ngay.csv"), "\n".join(dong) + "\n")
    tom = ["Tiêu đề,Mã video,Ngày đăng,Dài,Mốc mới nhất,Lượt hiển thị,Tỷ lệ bấm,Lượt xem,Xem thật ước,"
           "View/người,JP %,Xem TB,% độ dài,Đăng ký,Số lần chụp"]
    utc = _dt.datetime.utcnow()
    for v in mau["video"]:
        dang = (utc - _dt.timedelta(hours=v["gio_truoc"])).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        cuoi = None
        for moc, tq in v["chup"].items():
            d = os.path.join(tm, "chi-so", v["id"], moc)
            _ghi(os.path.join(d, "_thong-tin.json"), json.dumps({"tieu_de": v["tieu_de"], "ngay_dang": dang}))
            tq2 = dict(tq, thoi_luong_giay=v["phut"] * 60, traffic={"browse": 80.0, "related": 15.0})
            ctr_b = tq2.pop("ctr_browse", None)
            _ghi(os.path.join(d, "tong-quan.json"), json.dumps(tq2))
            if ctr_b is not None:
                _ghi(os.path.join(d, "traffic-type.csv"),
                     "Traffic source,Thumbnail impressions,Thumbnail click-through rate (%),Views\n"
                     "Total,{0},{1},{2}\nBrowse features,{0},{1},{2}\n".format(tq["impressions"], ctr_b, tq["views"]))
            cuoi = tq
        tom.append('"{0}","{1}","{2}","","","{3}","","{4}","","","","","","{5}",""'.format(
            v["tieu_de"], v["id"], dang[:10], cuoi["impressions"], cuoi["views"], cuoi["subs"]))
        _ghi(os.path.join(tm, "ho-so-video", v["goi"] + ".json"), json.dumps(
            {"ma_goi": v["goi"], "kenh": ma, "video_id": v["id"], "tieu_de": v["tieu_de"],
             "tieu_de_cham": {"ung_vien": v.get("tieu_de_cham", [])}}, ensure_ascii=False))
    _ghi(os.path.join(tm, "chi-so", "bang-tom-tat.csv"), "﻿" + "\n".join(tom) + "\n")
    return ma


def _v(vid, **k):
    """Video tối giản cho BangSo trong bộ nhớ."""
    v = {"id": vid, "ma_goi": "G-" + vid, "tieu_de": "t " + vid, "cum": [], "ket_luan": "", "thang": False,
         "hien_thi_48h": None, "chup": [], "tuoi_gio": 100.0, "dai_giay": 900, "tu_tool": True,
         "dang_luc": BAY - _dt.timedelta(hours=k.get("tuoi_gio", 100.0)), "lich_su_sua": [], "tieu_de_da_cham": []}
    v.update(k)
    return v


def _bs(video=(), **k):
    bs = BangSo(goc="", ma_kenh="X", bay_gio=BAY, cai={"phut_muc_tieu": 15}, ctr_muc_tieu=5.0,
                ypp={"rang_buoc": "gio_xem"}, nguong_thang_48h=7500)
    bs.video = list(video)
    for a, b in k.items():
        setattr(bs, a, b)
    return bs


# ── sổ đăng ký ──────────────────────────────────────────────────────────────

def test_so_dang_ky_dung_thu_tu_va_bo_mau():
    so = giam_doc.so_dang_ky(tai_lai=True)
    assert list(so) == ["suc_khoe", "cuu_ctr", "dan_cum", "muc_tieu_ypp", "do_dai"]
    for m in so.values():
        assert m.NHIP in ("ngay", "tuan") and isinstance(m.CHI_SO_CHINH, str) and m.MO_TA


# ── bảng số (đọc đĩa) ───────────────────────────────────────────────────────

def test_tom_tat_doc_kenh_mau(tmp_path):
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    bs = du_lieu.tom_tat(goc, "GD1")
    assert len(bs.video) == 6 and bs.video[0]["id"] == "GDvideo0006"  # mới → cũ
    v6 = bs.video_theo_id("GDvideo0006")
    assert v6["ket_luan"] == "truot" and v6["ma_goi"] == "GD1-0006" and "vat-chat" in v6["cum"]
    assert du_lieu.ctr_trang_chu(v6)["ctr_browse"] == 2.0
    assert bs.video_theo_id("GDvideo0001")["thang"] and bs.nguong_thang_48h == 7200
    b = du_lieu.moc_52(bs.video_theo_id("GDvideo0001"))
    assert b["moc"] == "48h" and abs(b["gx_1k"] - 6.5) < 0.01
    assert abs(bs.video_theo_id("GDvideo0001")["sub_1k"] - 18 / 1.9) < 0.01
    h7 = du_lieu.trong_khoang(bs, "hien_thi", bs.bay_gio - _dt.timedelta(days=7), bs.bay_gio)
    assert 6900 <= h7 <= 7100
    assert bs.phut_muc_tieu == 15 and bs.ctr_muc_tieu == 5.0
    assert not os.path.exists(os.path.join(goc, "CHANNEL", "GD1", "giam-doc"))


# ── suc_khoe ───────────────────────────────────────────────────────────────

def _kenh_ngay(moi_ngay):
    """Dòng cộng dồn từ list số hiển thị mỗi ngày (cũ → mới), dòng cuối = BAY."""
    ra, tong = [], 0.0
    n = len(moi_ngay)
    ra.append({"luc": BAY - _dt.timedelta(days=n), "hien_thi": 0.0})
    for i, x in enumerate(moi_ngay):
        tong += x
        ra.append({"luc": BAY - _dt.timedelta(days=n - i - 1), "hien_thi": tong})
    return ra


def test_suc_khoe_bao_dong_khi_sup_va_video_moi_yeu():
    video = [_v("n%d" % i, hien_thi_48h=x, tuoi_gio=24.0 * (i + 3)) for i, x in
             enumerate([300, 250, 280, 5000, 6000, 5500, 4000])]
    bs = _bs(video, kenh_ngay=_kenh_ngay([1000] * 14 + [300] * 7))
    qs = suc_khoe.quan_sat(bs)
    assert suc_khoe.bao_dong(qs) and any("viec_cua_ban" in q for q in qs)


def test_suc_khoe_nguoi_sau_video_no_chi_canh_bao():
    video = [_v("n%d" % i, hien_thi_48h=x, tuoi_gio=24.0 * (i + 3)) for i, x in
             enumerate([9000, 8000, 7000, 5000, 4000, 3000])]
    bs = _bs(video, kenh_ngay=_kenh_ngay([5000] * 14 + [1500] * 7))
    qs = suc_khoe.quan_sat(bs)
    assert not suc_khoe.bao_dong(qs) and qs[0]["cau"].startswith("CẢNH BÁO")


def test_suc_khoe_ngung_dang_khong_bao_dong():
    video = [_v("n%d" % i, hien_thi_48h=5000, tuoi_gio=24.0 * (10 + i)) for i in range(6)]
    bs = _bs(video, kenh_ngay=_kenh_ngay([1000] * 14 + [300] * 7))
    assert not suc_khoe.bao_dong(suc_khoe.quan_sat(bs))


# ── cuu_ctr ────────────────────────────────────────────────────────────────

def _chup(tuoi, imp, ctr_b=None, **k):
    return dict({"tuoi": tuoi, "hien_thi": imp, "ctr": 3.0, "ctr_browse": ctr_b}, **k)


def test_cuu_ctr_goi_y_doi_tieu_de_dung_cong():
    hong = _v("hong", tuoi_gio=60.0, ket_luan="truot", chup=[_chup(56, 3000, 2.0)],
              tieu_de_da_cham=[{"tieu_de": "t hong"}, {"tieu_de": "bản khác"}])
    on = _v("on", tuoi_gio=70.0, ket_luan="truot", chup=[_chup(60, 2000, 6.0)])
    thang = _v("thang", tuoi_gio=55.0, ket_luan="thang", thang=True, chup=[_chup(50, 40000, 2.0)])
    bs = _bs([hong, on, thang])
    qs = cuu_ctr.quan_sat(bs)
    cong = {q["video_id"]: q["cong"] for q in qs}
    assert cong == {"hong": "ctr", "on": "hien_thi", "thang": "thang"}
    dx = cuu_ctr.de_xuat(bs, qs)
    assert [d["video_id"] for d in dx] == ["hong"] and dx[0]["loai"] == "viec_studio"
    assert dx[0]["goi_y"]["tieu_de_da_cham"] == ["bản khác"] and dx[0]["can_noi_dung"]


def test_cuu_ctr_ngoai_khung_khong_chay():
    bs = _bs([_v("gia", tuoi_gio=120.0, ket_luan="truot", chup=[_chup(100, 3000, 1.0)])])
    assert cuu_ctr.ap_dung(bs) == 0.0


# ── dan_cum ────────────────────────────────────────────────────────────────

def test_dan_cum_don_va_tam_bo_cum_va_kep_ti_trong():
    video = ([_v("a%d" % i, cum=["iq"], ket_luan="thang", thang=True, hien_thi_48h=20000) for i in range(2)]
             + [_v("b%d" % i, cum=["mot"], ket_luan="truot", hien_thi_48h=900) for i in range(3)])
    bs = _bs(video, cai={"chien_luoc": "v7:0.5, vph:0.5"},
             chien_luoc_tep={"ti_trong_goi_y": {"v7": 0.9, "vph": 0.1}, "ly_do_goi_y": "test"})
    dx = dan_cum.de_xuat(bs, dan_cum.quan_sat(bs))
    viec = {d["viec"]: d for d in dx}
    assert "iq" in viec["don_cum"]["noi_dung"] and "mot" in viec["bo_cum"]["noi_dung"]
    assert viec["bo_cum"]["han_ngay"] == 21 and viec["luat_chon_tuan"]["loai"] == "tham_so"
    assert viec["ti_trong"]["gia_tri"] == "v7:0.7, vph:0.3"  # gợi ý 0,9 bị kẹp bước ±0,2
    assert "tu_hoc" not in viec  # chưa đủ n


def test_dan_cum_ket_luan_ti_le_thang():
    tn = {"id": "t1", "bat_dau": (BAY - _dt.timedelta(days=10)).isoformat(), "co_mau": 2, "nen": {"gia_tri": 0.2}}
    video = [_v("m%d" % i, tuoi_gio=80.0, ket_luan="thang" if i else "truot") for i in range(3)]
    kl = dan_cum.ket_luan(_bs(video), tn)
    assert kl["ket"] == "mo_rong" and kl["so"]["n"] == 3


# ── muc_tieu_ypp ───────────────────────────────────────────────────────────

def test_muc_tieu_ypp_thieu_sub_xen_cum_va_loi_moi():
    video = ([_v("s%d" % i, cum=["keo-sub"], sub_1k=9.0, xem_tron_doi=1000) for i in range(2)]
             + [_v("t%d" % i, cum=["thuong"], sub_1k=2.0, xem_tron_doi=1000) for i in range(3)])
    bs = _bs(video, ypp={"rang_buoc": "sub", "sub": 600, "gio_xem": 5000, "thieu_sub": 400, "thieu_gio": 0},
             bai_hoc=[{"pham_vi": "kenh", "truc": "giu_chan", "cum": "", "n": 9,
                       "cau": "Kênh: …; vách rơi dốc nhất thường quanh 1:14 (n=9)."}])
    assert muc_tieu_ypp.ap_dung(bs) == 1.0
    dx = muc_tieu_ypp.de_xuat(bs, muc_tieu_ypp.quan_sat(bs))
    assert {d["viec"] for d in dx} == {"xen_cum_ypp", "loi_moi_dang_ky"}
    assert "keo-sub" in dx[0]["noi_dung"] and "1:14" in dx[1]["noi_dung"]
    assert muc_tieu_ypp.ap_dung(_bs(video, giai_doan="kiem_tien", ypp={"rang_buoc": "sub"})) == 0.0


# ── do_dai ─────────────────────────────────────────────────────────────────

def test_do_dai_thi_nghiem_ve_phia_nhom_nhieu_gio_xem():
    video = ([_v("v%d" % i, dai_giay=15 * 60, chup=[_chup(52, 1000, gx_1k=4.0)]) for i in range(3)]
             + [_v("d%d" % i, dai_giay=19 * 60, chup=[_chup(52, 1000, gx_1k=6.0)]) for i in range(2)])
    bs = _bs(video)
    dx = do_dai.de_xuat(bs, do_dai.quan_sat(bs))
    assert len(dx) == 1 and dx[0]["khoa"] == "phut_muc_tieu" and dx[0]["gia_tri"] == 18
    assert dx[0]["co_mau"] == 4 and dx[0]["nen"]["gia_tri"] == 4.0
    bs.cai["phut_muc_tieu"] = 25
    assert do_dai.de_xuat(bs, do_dai.quan_sat(bs)) == []  # mọi video về "ngắn", không nhóm nào hơn → im


def test_do_dai_ket_luan_theo_trung_vi():
    tn = {"id": "t", "bat_dau": (BAY - _dt.timedelta(days=30)).isoformat(), "co_mau": 4, "nen": {"gia_tri": 4.0}}
    tot = [_v("x%d" % i, chup=[_chup(52, 1000, gx_1k=5.0)]) for i in range(4)]
    assert do_dai.ket_luan(_bs(tot), tn)["ket"] == "giu"
    it = [_v("y%d" % i, chup=[_chup(52, 1000, gx_1k=5.0)]) for i in range(3)]
    assert do_dai.ket_luan(_bs(it), tn)["ket"] == "chua_du"
    hoa = [_v("z%d" % i, chup=[_chup(52, 1000, gx_1k=4.1)]) for i in range(4)]
    assert do_dai.ket_luan(_bs(hoa), tn)["ket"] == "bo"


# ── bộ não ─────────────────────────────────────────────────────────────────

THUC_DON = [{"id": "d1", "loai": "tham_so", "khoa": "phut_muc_tieu", "gia_tri": 17, "plugin": "do_dai"},
            {"id": "d2", "loai": "tham_so", "khoa": "chien_luoc_tham_do", "gia_tri": 25, "plugin": "x"},
            {"id": "d3", "loai": "viec_studio", "video_id": "v", "plugin": "cuu_ctr"},
            {"id": "d4", "loai": "chi_dao", "noi_dung": "cũ", "han_ngay": 7, "plugin": "dan_cum"}]


def test_doc_ket_qua_loai_id_la_va_vuot_ngan_sach():
    tho = json.dumps({"chan_doan": "CTR thấp", "chon": [
        {"id": "d9"}, {"id": "d1", "ly_do": "a"}, {"id": "d2"}, {"id": "d3"}, {"id": "d4", "noi_dung": "mới"}],
        "ket_luan": [{"id": "tn1", "ket": "giu"}, {"id": "la", "ket": "giu"}, {"id": "tn1", "ket": "xx"}],
        "viec_cua_ban": "nạp tiền"})
    kq = quan_ly.doc_ket_qua("```json\n" + tho + "\n```", THUC_DON, [{"id": "tn1"}], toi_da_tham_so=1)
    assert [d["id"] for d in kq["chon"]] == ["d1", "d4"]  # d9 lạ, d2 vượt ngân sách, d3 thiếu tiêu đề
    assert kq["chon"][1]["noi_dung"] == "mới" and kq["ket_luan"] == [{"id": "tn1", "ket": "giu", "ly_do": ""}]
    assert kq["viec_cua_ban"] == ["nạp tiền"]
    assert quan_ly.doc_ket_qua("không phải json", THUC_DON, []) is None
    assert quan_ly.doc_ket_qua("[1, 2]", THUC_DON, []) is None


def test_nghi_lui_bac_mo_hinh_khi_hong(monkeypatch):
    from core import bien_tap_content

    monkeypatch.setattr(bien_tap_content, "thang_mo_hinh", lambda _g, _k: ["m1", "m2", "m3"])
    goi = []

    def gia(ln, mo_hinh, khoa, toi_da_token):
        goi.append(mo_hinh)
        if mo_hinh == "m1":
            raise RuntimeError("502")
        if mo_hinh == "m2":
            return "lỗi"
        return json.dumps({"chan_doan": "ok", "chon": [{"id": "d1", "ly_do": "x"}]})

    bs = _bs()
    qd = quan_ly.nghi(bs, {}, THUC_DON[:1], [], {"tham_so_con": 2, "studio_con": 2}, gia)
    assert goi == ["m1", "m2", "m3"] and qd.mo_hinh == "m3" and qd.chon[0]["id"] == "d1" and not qd.loi
    assert "MỤC TIÊU" in qd.loi_nhac and "THỰC ĐƠN" in qd.loi_nhac and "d1 [do_dai/tham_so]" in qd.loi_nhac
    hong = quan_ly.nghi(bs, {}, THUC_DON[:1], [], {"tham_so_con": 2}, lambda *a, **k: "rác")
    assert hong.loi and not hong.chon


# ── một lượt trọn ──────────────────────────────────────────────────────────

def _llm_chon_het(ln, mo_hinh="", khoa="", toi_da_token=0):
    chon = [dict({"id": i, "ly_do": "thử"}, **({"noi_dung": "【脳科学】本当のお金持ちが絶対にしないこと"}
                                              if loai == "viec_studio" else {}))
            for i, loai in re.findall(r"^(d\d+) \[\w+/(\w+)\]", ln, flags=re.M)]
    return json.dumps({"chan_doan": "Cụm trí tuệ thắng, cụm một mình trượt.", "chon": chon,
                       "tuan_toi": "đo luật chọn tuần"})


def test_chay_kenh_thu_khong_ghi_gi(tmp_path):
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    truoc = io.open(os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml"), encoding="utf-8").read()
    kq = giam_doc.chay_kenh(goc, "GD1", che_do="thu", goi_chat=_llm_chon_het, tuan=True)
    assert kq.quyet_dinh is not None and kq.quyet_dinh.chon and not kq.bao_dong
    assert any(d["plugin"] == "cuu_ctr" and d["duoc"] for d in kq.thuc_don)
    assert not os.path.exists(os.path.join(goc, "CHANNEL", "GD1", "giam-doc"))
    assert io.open(os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml"), encoding="utf-8").read() == truoc
    chu = bao_cao.in_ket_qua(kq, ca_loi_nhac=True)
    assert "QUYẾT ĐỊNH" in chu and "LỜI NHẮC" in chu


def test_chay_kenh_tu_ap_ghi_so_va_kenh_yaml(tmp_path, monkeypatch):
    from core.giam_doc import hoi_dong

    monkeypatch.setattr(hoi_dong, "quyen", lambda g, m, l: "tu_ap")  # đã có thành tích (Đợt F: quyền theo độ chính xác)
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    kq = giam_doc.chay_kenh(goc, "GD1", goi_chat=_llm_chon_het, tuan=True)
    assert kq.che_do == "tu_ap"
    from core.kenh import doc_yaml

    cai = doc_yaml(os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml"))
    assert "luat_chon_tuan" in cai and "mot-minh" in str(cai["luat_chon_tuan"])
    tm = os.path.join(goc, "CHANNEL", "GD1", "giam-doc")
    for ten in ("thi-nghiem.json", "nhat-ky.jsonl", "trang-thai.json", "chi-dao.json", "BAO-CAO-TUAN.md"):
        assert os.path.isfile(os.path.join(tm, ten)), ten
    assert len(giam_doc.doc_chi_dao(goc, "GD1")) >= 2
    assert any("Đổi tiêu đề video GDvideo0006" in x for x in kq.viec_cua_ban)  # đợt 1: chỉ gợi ý
    # chạy lại cùng ngày: luat_chon_tuan đang nghỉ 14 ngày + 1 thí nghiệm mở / chỉ số
    kq2 = giam_doc.chay_kenh(goc, "GD1", goi_chat=_llm_chon_het, tuan=True)
    d = next(d for d in kq2.thuc_don if d.get("khoa") == "luat_chon_tuan")
    assert not d["duoc"]
    assert "Giám đốc kênh" in bao_cao.cau_the(goc, "GD1")


def test_che_do_tat_khong_lam_gi(tmp_path):
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    p = os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml")
    chu = io.open(p, encoding="utf-8").read().replace("giam_doc: tu_ap", "giam_doc: tat")
    _ghi(p, chu)
    kq = giam_doc.chay_kenh(goc, "GD1", goi_chat=_llm_chon_het)
    assert kq.che_do == "tat" and not kq.viec and not os.path.exists(os.path.join(goc, "CHANNEL", "GD1", "giam-doc"))
    assert giam_doc.nhip(goc, thu=True)["viec"] == []


def test_nhip_va_chay_het_khong_lap_khi_hong(tmp_path, monkeypatch):
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    p = os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml")
    _ghi(p, io.open(p, encoding="utf-8").read().replace("giam_doc: tu_ap", "giam_doc: goi_y"))
    n = giam_doc.nhip(goc, thu=True)
    assert [v["ma"] for v in n["viec"]] == ["GD1"] and n["pid"] == 0
    assert giam_doc.nhip(goc, sinh=lambda _g: 4242)["pid"] == 4242

    def hong(*_a, **_k):
        raise RuntimeError("đĩa hỏng")

    monkeypatch.setattr(giam_doc, "chay_kenh", hong)
    monkeypatch.setattr(quan_ly, "goi_chat_that", lambda *_a, **_k: None)
    assert giam_doc.chay_het(goc) == []
    assert not os.path.exists(os.path.join(goc, "workspace", "giam-doc", ".khoa"))  # nhả khoá
    assert giam_doc.nhip(goc, thu=True)["viec"] == []  # hôm nay không sinh lại
    assert "hỏng" in bao_cao.cau_the(goc, "GD1")
