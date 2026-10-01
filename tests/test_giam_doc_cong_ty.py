"""Công ty YouTube (bản gọn, 01/10/2026): khám nghiệm video, bài học vào sổ chung, tổng giám đốc.

Cô lập: kênh giả trong `tmp_path` (`tests/du-lieu/giam-doc/kenh-mau.json` qua `dung_kenh_mau`), LLM giả —
không mạng, không ví, không đọc/ghi CHANNEL thật.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import types

from core import giam_doc
from core.chien_luoc import bai_hoc
from core.giam_doc import kham_nghiem as kn
from core.giam_doc import quan_ly, tong
from core.giam_doc.du_lieu import BangSo
from tests.test_giam_doc_plugin import _bs, _ghi, _v, dung_kenh_mau

BAY = _dt.datetime(2026, 10, 1, 12, 0)


def _tra_loi(bai=None, chan_doan="Hiển thị 48h 1.200 so với trung vị 3.000: cổng hiển thị hỏng.", **them):
    du = {"chan_doan": chan_doan, "cong_hong": "hien_thi", "vi_sao": "cụm nguội", "du_doan_lech": "",
          "nhan": {"kieu_tieu_de": "so_dem", "kieu_hook": "la_lung"},
          "bai_hoc": bai if bai is not None else {"truc": "hook", "gia_tri": "nghich_ly", "huong": "+", "cum": "",
                                                  "cau": "Hook nghịch lý giữ 62% ở 0:30 (kênh 48%)."},
          "so_dan": [{"so": 1200, "nguon": "v:A/52h/hien_thi"}, {"so": 9, "nguon": "v:A/52h/ctr"}]}
    du.update(them)
    return json.dumps(du, ensure_ascii=False)


# ── đọc kết quả ────────────────────────────────────────────────────────────

def test_doc_ket_qua_soat_dang_va_so_dan():
    sl = {"v:A/52h/hien_thi": 1200, "v:A/52h/ctr": 4.1}
    k = kn.doc_ket_qua(_tra_loi(), sl)
    assert k["cong_hong"] == "hien_thi" and k["nhan"] == {"kieu_tieu_de": "so_dem", "kieu_hook": "khac"}
    assert k["bai_hoc"]["truc"] == "hook" and k["bai_hoc"]["huong"] == "+"
    assert [x["khop"] for x in k["so_dan"]] == [True, False]
    assert kn.doc_ket_qua(_tra_loi(chan_doan="cổng hiển thị hỏng"), sl) is None      # chẩn đoán không có số
    assert kn.doc_ket_qua("rác", sl) is None
    lac = kn.doc_ket_qua(_tra_loi(bai={"truc": "mau_sac", "gia_tri": "x", "huong": "+", "cau": "3 lần"}), sl)
    assert lac is not None and lac["bai_hoc"] is None                                 # trục lạ → bỏ bài học
    khong_so = kn.doc_ket_qua(_tra_loi(bai={"truc": "hook", "gia_tri": "x", "huong": "+", "cau": "hook hay"}), sl)
    assert khong_so["bai_hoc"] is None


# ── chọn video cần khám ────────────────────────────────────────────────────

def _chup(tuoi, imp=1000.0):
    return {"moc": "{0:.0f}h".format(tuoi), "tuoi": tuoi, "hien_thi": imp, "ctr": 5.0}


def test_can_kham_moc_muon_nhat_toi_da_2_lan_va_4_video():
    vs = [_v("V{0}".format(i), tuoi_gio=300 - i, chup=[_chup(50), _chup(170)]) for i in range(6)]
    vs.append(_v("MOI", tuoi_gio=20, chup=[_chup(20)]))
    bs = _bs(vs)
    ds = kn.can_kham(bs, da={})
    assert [(v["id"], m) for v, m in ds] == [("V0", "7d"), ("V1", "7d"), ("V2", "7d"), ("V3", "7d")]
    ds = kn.can_kham(bs, da={"V0": ["7d"], "V1": ["48h", "7d"], "V2": ["48h"]})
    assert ("V0", "7d") not in [(v["id"], m) for v, m in ds] and all(v["id"] != "V1" for v, _m in ds)
    assert ("V2", "7d") in [(v["id"], m) for v, m in ds]
    assert all(v["id"] != "MOI" for v, _m in kn.can_kham(bs, da={}, toi_da=10))


# ── một lượt khám trọn (kênh giả trên đĩa) ────────────────────────────────

def _kenh(tmp_path, che_do="goi_y"):
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    p = os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml")
    _ghi(p, io.open(p, encoding="utf-8").read().replace("giam_doc: tu_ap", "giam_doc: " + che_do))
    return goc


def test_chay_kenh_kham_ghi_ban_kham_va_bai_hoc_bong(tmp_path, monkeypatch):
    from core import bien_tap_content

    monkeypatch.setattr(bien_tap_content, "thang_mo_hinh", lambda _g, _k: ["m1"])
    goc = _kenh(tmp_path)
    loi_nhac = []

    def llm(ln, mo_hinh="", khoa="", toi_da_token=0):
        if ln.startswith("Bạn khám nghiệm"):
            loi_nhac.append(ln)
            return _tra_loi()
        return json.dumps({"chan_doan": "Cổng hiển thị 3 video yếu.", "chon": []})

    kq = giam_doc.chay_kenh(goc, "GD1", goi_chat=llm, tuan=True)
    assert kq.kham and all(x.get("ket") for x in kq.kham) and len(kq.kham) <= kn.TOI_DA_MOI_VONG
    assert "SỐ LIỆU" in loi_nhac[0] and "kenh/tv@" in loi_nhac[0]
    tm = kn.thu_muc(goc, "GD1")
    tep = sorted(os.listdir(tm))
    assert len(tep) == len(kq.kham)
    ban = json.load(io.open(os.path.join(tm, tep[0]), encoding="utf-8"))
    assert ban["bong"] is True and ban["nhan"]["do_dai_nhom"] and ban["ket"]["so_dan"]
    dong = [json.loads(x) for x in io.open(os.path.join(goc, "CHANNEL", "GD1", "giam-doc", kn.TEP_BAI_HOC), encoding="utf-8")]
    assert len(dong) == len(kq.kham) and dong[0]["khoa"] == "hook|nghich_ly|+|" and dong[0]["bong"] is True
    # lượt sau: không khám lại video cùng mốc
    kq2 = giam_doc.chay_kenh(goc, "GD1", goi_chat=llm, tuan=True)
    assert {(x["video_id"], x["moc"]) for x in kq2.kham}.isdisjoint({(x["video_id"], x["moc"]) for x in kq.kham})
    # bài bóng: không bơm vào bộ chấm, kể cả n ≥ 3
    gop = kn.doc_bai_hoc(goc, "GD1")
    assert gop[0]["n"] >= 3 and gop[0]["bong"] and not gop[0]["bom"]
    assert bai_hoc.khoi_kham_nghiem(goc, "GD1", "kich_ban") == ""
    # khối KHÁM NGHIỆM GẦN ĐÂY vào lời nhắc giám đốc kênh
    assert "KHÁM NGHIỆM GẦN ĐÂY" in kn.khoi_gan_day(goc, "GD1") and "kieu_tieu_de: so_dem" in kn.khoi_gan_day(goc, "GD1")


def test_kham_lai_khong_nhan_doi_phieu(tmp_path):
    goc = str(tmp_path)
    for i in range(2):
        kn._ghi_bai_hoc(goc, "X", {"video_id": "A", "moc": "7d", "truc": "hook", "cau": "1 lần", "lan": i}, "A", "7d")
    dong = kn._doc_dong(os.path.join(goc, "CHANNEL", "X", "giam-doc", kn.TEP_BAI_HOC))
    assert len(dong) == 1 and dong[0]["lan"] == 1


def _so_bai(goc, ma, ds):
    tm = os.path.join(goc, "CHANNEL", ma, "giam-doc")
    os.makedirs(tm, exist_ok=True)
    with io.open(os.path.join(tm, kn.TEP_BAI_HOC), "w", encoding="utf-8") as tep:
        for vid, huong, bong in ds:
            tep.write(json.dumps({"truc": "hook", "gia_tri": "nghich_ly", "huong": huong, "cum": "", "video_id": vid,
                                  "moc": "7d", "cau": "Hook nghịch lý giữ 62% ở 0:30.", "bong": bong,
                                  "luc": _dt.datetime.now().isoformat()}, ensure_ascii=False) + "\n")


def test_doc_bai_hoc_gop_theo_khoa_n_mau_thuan_bong(tmp_path):
    goc = str(tmp_path)
    _so_bai(goc, "X", [("A", "+", False), ("B", "+", False), ("C", "+", False)])
    b = kn.doc_bai_hoc(goc, "X")[0]
    assert (b["n"], b["bom"], b["mau_thuan"]) == (3, True, False) and b["video"] == ["A", "B", "C"]
    _so_bai(goc, "X", [("A", "+", False), ("B", "+", False), ("C", "+", False), ("D", "-", False)])
    b = kn.doc_bai_hoc(goc, "X")[0]
    assert (b["n"], b["bom"], b["mau_thuan"]) == (2, False, True)
    _so_bai(goc, "X", [("A", "+", True), ("B", "+", True), ("C", "+", True)])
    assert not kn.doc_bai_hoc(goc, "X")[0]["bom"] and kn.doc_bai_hoc(goc, "X", bo_bong=True)[0]["bom"]


# ── sổ bài học chung + MỘT móc ở bộ chấm kịch bản ─────────────────────────

def _khoi_khan_gia(goc, ma, d):
    from core import auto_khau

    _ghi(os.path.join(d, auto_khau.TEP_BINH_LUAN_GOC), "(không lấy được)\n")
    bc = types.SimpleNamespace(goc=goc, ghi=lambda *_a: None, cancel=None)
    k = types.SimpleNamespace(ma=ma, duong=os.path.join(goc, "CHANNEL", ma), ngon_ngu="ja")
    return auto_khau._khoi_khan_gia(bc, k, d)


def test_khoi_khan_gia_y_het_tung_byte_khi_chua_co_bai_hoc_bom_duoc(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "X", "kenh.yaml"), "ma: X\ngiam_doc: goi_y\n")
    d = os.path.join(goc, "luot")
    goc_ra = _khoi_khan_gia(goc, "X", d)
    assert goc_ra["SU_THAT_KENH"] == "(chưa có)"
    _so_bai(goc, "X", [("A", "+", False), ("B", "+", False)])                    # n = 2
    assert _khoi_khan_gia(goc, "X", d) == goc_ra
    _so_bai(goc, "X", [("A", "+", True), ("B", "+", True), ("C", "+", True)])    # bóng
    assert _khoi_khan_gia(goc, "X", d) == goc_ra
    _so_bai(goc, "X", [("A", "+", False), ("B", "+", False), ("C", "+", False)])
    st = _khoi_khan_gia(goc, "X", d)["SU_THAT_KENH"]
    assert st.startswith("(chưa có)\n\nBÀI HỌC TỪ KHÁM NGHIỆM VIDEO CỦA KÊNH")
    assert "- Hook nghịch lý giữ 62% ở 0:30 (khám nghiệm 3 video)" in st


def test_bai_hoc_kham_nghiem_vao_so_chung_pham_vi_kenh(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "X", "kenh.yaml"), "ma: X\ngiam_doc: tu_ap\n")
    _so_bai(goc, "X", [("A", "+", True), ("B", "+", True), ("C", "+", True)])   # tu_ap: bóng tính như thật
    ds = [b for b in bai_hoc._tu_kham_nghiem(goc, "X")]
    assert len(ds) == 1 and ds[0]["pham_vi"] == "kenh" and ds[0]["bom"] and ds[0]["khoa"] == "hook|nghich_ly|+|"
    assert ds[0]["dung_cho"] == ["kich_ban"]
    assert "Hook nghịch lý" in bai_hoc.khoi_kham_nghiem(goc, "X", "kich_ban")
    assert bai_hoc.khoi_kham_nghiem(goc, "X", "tieu_de") == ""


# ── giám đốc kênh đọc khám nghiệm; một cửa LLM ─────────────────────────────

def test_loi_nhac_giam_doc_y_het_khi_chua_kham_va_co_khoi_khi_da_kham(tmp_path):
    goc = str(tmp_path)
    bs = BangSo(goc=goc, ma_kenh="X", bay_gio=BAY, cai={}, ctr_muc_tieu=5.0)
    goc_rong = BangSo(goc="", ma_kenh="X", bay_gio=BAY, cai={}, ctr_muc_tieu=5.0)
    truoc = quan_ly.loi_nhac(goc_rong, {}, [], [], {"tham_so_con": 2, "studio_con": 2})
    assert quan_ly.loi_nhac(bs, {}, [], [], {"tham_so_con": 2, "studio_con": 2}) == truoc
    kn._ghi_json(os.path.join(kn.thu_muc(goc, "X"), "A-7d.json"), {
        "video_id": "A", "moc": "7d", "luc": "2026-10-01T10:00:00", "ket_luan": "truot",
        "ket": {"chan_doan": "CTR 2,1% (kênh 5%).", "cong_hong": "ctr"}, "nhan": {"kieu_tieu_de": "to_mo"}})
    sau = quan_ly.loi_nhac(bs, {}, [], [], {"tham_so_con": 2, "studio_con": 2})
    assert "KHÁM NGHIỆM GẦN ĐÂY (1 video" in sau and "kieu_tieu_de: to_mo 1 video (thắng 0, trượt 1)" in sau
    assert sau.index("QUAN SÁT") < sau.index("KHÁM NGHIỆM") < sau.index("THÍ NGHIỆM ĐANG MỞ")


def test_goi_quyet_thang_mo_hinh_va_so_lieu(monkeypatch):
    from core import bien_tap_content

    monkeypatch.setattr(bien_tap_content, "thang_mo_hinh", lambda _g, _k: ["a", "b", "c"])
    goi = []

    def llm(ln, mo_hinh="", khoa="", toi_da_token=0):
        goi.append((mo_hinh, khoa))
        if mo_hinh == "a":
            raise RuntimeError("502")
        return "rác" if mo_hinh == "b" else '{"ok": 1}'

    q = quan_ly.goi_quyet("kham_nghiem", "x", {"k": 1}, llm, doc=lambda t: json.loads(t) if t.startswith("{") else None,
                          khoa="kh")
    assert q["ket"] == {"ok": 1} and q["mo_hinh"] == "c" and [g[1] for g in goi] == ["kh-1", "kh-2", "kh-3"]
    assert quan_ly.goi_quyet("x", "x", None, None, doc=lambda t: None)["loi"]


# ── tổng giám đốc ──────────────────────────────────────────────────────────

def _dong(ma, loai, khe, da=1.0, chu_ky=1):
    return {"ma": ma, "cac_ma": [ma], "loai": loai, "khe": khe, "da": da,
            "chay": [{"ma": ma, "nhip": ["0{0}:00".format(i) for i in range(khe)], "video_toi_da_ngay": khe,
                      "ngan_sach_ngay": 100, "chu_ky": chu_ky}]}


def test_xep_loai_va_chia_khe_theo_nhip_ngay():
    """01/10/2026: luật NHỊP NGÀY — lên dày hơn một bậc (tối đa 1/ngày), chững/tụt thưa hơn (tối đa 1/3 ngày),
    kênh nhiều khe/ngày về 1/ngày; tổng video/ngày ≤ 85% trần máy."""
    assert tong.xep_loai({"da": 1.3, "ti_le_thang": 0.3}) == "len"
    assert tong.xep_loai({"da": 1.3, "ti_le_thang": 0.1}) == "chung"
    assert tong.xep_loai({"da": 0.7}) == "tut" and tong.xep_loai({"da": None}) == "chung"
    bang = [_dong("A", "len", 1, 1.5, chu_ky=2), _dong("B", "tut", 1, 0.5, chu_ky=2),
            _dong("C", "chung", 1, chu_ky=3), _dong("D", "len", 1, 2.0, chu_ky=1), _dong("E", "chung", 3)]
    ra = {x["ma"]: (x["khe_moi"], x["chu_ky_moi"]) for x in tong.chia_khe(bang, 100)}
    # A lên 1/2 → 1/ngày; B tụt 1/2 → 1/3; C đã 1/3 (trần thưa) giữ; D đã 1/ngày (trần dày) giữ; E 3 khe → 1/ngày
    assert ra == {"A": (1.0, 1), "B": (0.33, 3), "E": (1.0, 1)}
    # trần máy 3 → tổng ≤ 2,55: bỏ bước dày lên của A, rồi giãn kênh dày nhất (D, E → 1/2 ngày)
    assert {x["ma"]: x["khe_moi"] for x in tong.chia_khe(bang, 3)} == {"B": 0.33, "D": 0.5, "E": 0.5}
    assert tong.ten_tan_suat(0.5) == "1 video/2 ngày" and tong.ten_tan_suat(1.0) == "1 video/ngày"


def test_luat_so_kenh_theo_thi_truong(tmp_path):
    """01/10/2026 LUẬT SỐ KÊNH: tối đa = nguồn nổ/tháng ÷ 15 khi trang chủ lên/ổn định; kênh thứ 2+ chờ kênh đầu
    thắng ≥ 2 video; mở mỗi lần một kênh; bảng vào báo cáo công ty."""
    assert tong.so_kenh_toi_da(33.3, "len") == 2 and tong.so_kenh_toi_da(14.9, "on") == 0
    assert tong.so_kenh_toi_da(40, "giam") == 0 and tong.so_kenh_toi_da(None, "len") == 0
    goc = str(tmp_path)
    for ma, tep in (("A1", "tep-a"), ("A1-v2", "tep-a"), ("B1", "tep-b")):
        os.makedirs(os.path.join(goc, "CHANNEL", ma))
        with io.open(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "w", encoding="utf-8") as f:
            f.write('tep: "{0}"\n'.format(tep))
    os.makedirs(os.path.join(goc, "workspace", "chuan-bi-kenh-moi"))
    with io.open(os.path.join(goc, tong.TEP_THI_TRUONG), "w", encoding="utf-8") as f:
        json.dump({"tep": {"tep-a": {"ten": "A", "nguon_no_thang": 31, "trang_chu": "on"},
                           "tep-b": {"ten": "B", "nguon_no_thang": 45, "trang_chu": "len"},
                           "tep-c": {"ten": "C", "nguon_no_thang": 20, "trang_chu": "len"},
                           "tep-d": {"ten": "D", "nguon_no_thang": 60, "trang_chu": "giam"}}}, f)
    bang = [{"ma": "A1", "thang_tong": 1}, {"ma": "B1", "thang_tong": 3}]
    ra = {d["tep"]: (d["toi_da"], d["dang_co"], d["de_xuat_mo"]) for d in tong.bang_so_kenh(goc, bang)}
    assert ra == {"tep-a": (2, 1, 0), "tep-b": (3, 1, 1), "tep-c": (1, 0, 1), "tep-d": (0, 0, 0)}
    assert len(tong.de_xuat_kenh_moi(goc, {"con_du_video_ngay": 3}, bang)) == 2
    assert tong.de_xuat_kenh_moi(goc, {"con_du_video_ngay": 1}, bang) == []
    kq = {"luc": "2026-10-05T09:00:00", "che_do": "goi_y", "bang": [], "tran": 5, "thuc_don": [], "da_lam": [],
          "quay_lui": [], "kenh_moi": [], "so_kenh": tong.bang_so_kenh(goc, bang)}
    md = tong.chu_bao_cao(kq)
    assert "Số kênh theo thị trường" in md and "| B | 45,0 | lên | 3 | 1 (B1) | 1 |" in md


def test_kenh_nhan_ban_K2_la_kenh_youtube_rieng(tmp_path):
    """01/10/2026: kênh nhân bản đặt đuôi `-K2` (TL4-T7-K2, TL6-T7-K2) là MỘT KÊNH YOUTUBE RIÊNG — chỉ `-v<n>` mới
    gộp với kênh gốc (cùng kênh YouTube). Bảng công ty, bảng số kênh và `ma_youtube` đều tách."""
    from core.bang_dieu_khien import ma_youtube

    goc = str(tmp_path)
    for ma in ("TL4-T7", "TL4-T7-v2", "TL4-T7-K2", "TL6-T7", "TL6-T7-K2"):
        os.makedirs(os.path.join(goc, "CHANNEL", ma))
        with io.open(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "w", encoding="utf-8") as f:
            f.write('tep: "{0}"\n'.format("t1" if ma.startswith("TL4") else "t8"))
    assert {k: sorted(v) for k, v in tong._cac_kenh(goc).items()} == {
        "TL4-T7": ["TL4-T7", "TL4-T7-v2"], "TL4-T7-K2": ["TL4-T7-K2"], "TL6-T7": ["TL6-T7"], "TL6-T7-K2": ["TL6-T7-K2"]}
    assert ma_youtube("TL4-T7-v2") == "TL4-T7" and ma_youtube("TL4-T7-K2") == "TL4-T7-K2"
    os.makedirs(os.path.join(goc, "workspace", "chuan-bi-kenh-moi"))
    with io.open(os.path.join(goc, tong.TEP_THI_TRUONG), "w", encoding="utf-8") as f:
        json.dump({"tep": {"t1": {"nguon_no_thang": 31, "trang_chu": "on"},
                           "t8": {"nguon_no_thang": 30, "trang_chu": "len"}}}, f)
    ra = {d["tep"]: (d["dang_co"], d["kenh"]) for d in tong.bang_so_kenh(goc, [])}
    assert ra == {"t1": (2, ["TL4-T7", "TL4-T7-K2"]), "t8": (2, ["TL6-T7", "TL6-T7-K2"])}


def test_nhip_moi_them_giua_khoang_trong_bot_khe_yeu_nhat():
    assert tong.nhip_moi(["08:00", "20:00"], 3) == ["02:00", "08:00", "20:00"]
    video = [(_dt.datetime(2026, 9, 1, 8, 0), 9000), (_dt.datetime(2026, 9, 2, 20, 0), 300),
             (_dt.datetime(2026, 9, 3, 12, 5), 5000)]
    assert tong.nhip_moi(["08:00", "12:00", "20:00"], 2, video) == ["08:00", "12:00"]
    assert tong.nhip_moi(["08:00", "12:00"], 1) == ["08:00"]


def _kenh_tong(goc, ma="T1", khe="05:00, 12:00, 20:00"):
    _ghi(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"),
         'ma: {0}\ntu_chay: true\ntu_duyet: true\nnhip_dang: "{1}"\nvideo_toi_da_ngay: 3\nngan_sach_ngay: 500000\n'
         .format(ma, khe))


def test_hop_tuan_thu_khong_ghi_tu_ap_doi_khe_va_nghi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh_tong(goc)
    _ghi(os.path.join(goc, "CHANNEL", "T1-v2", "kenh.yaml"), "ma: T1-v2\ntu_chay: false\n")
    monkeypatch.setattr(tong, "bang_cong_ty", lambda g, b=None: [dict(
        _dong("T1", "len", 3, 1.4), cac_ma=["T1", "T1-v2"],
        chay=[{"ma": "T1", "nhip": ["05:00", "12:00", "20:00"], "video_toi_da_ngay": 3, "ngan_sach_ngay": 500000}],
        hien_thi_7=14000, hien_thi_7_truoc=10000, gio_xem_7=50.0, sub_7=20, thang_28=2, kl_28=4, tv_48h_14=3000,
        ypp_sub=300, ypp_gio=900.0, bao_cao_kenh="", _video=[])])
    monkeypatch.setattr(tong, "_uoc_vnd", lambda g, m: 200000)
    from core import cong_suat

    monkeypatch.setattr(cong_suat, "cong_suat_hien_tai", lambda g, gio=24: {
        "tran_video_ngay_khe_nang": 20.0, "tran_video_ngay_lan_api": 30.0, "con_du_video_ngay": 3, "phan_tram_khe_nang": 40})

    def llm(ln, mo_hinh="", khoa="", toi_da_token=0):
        return json.dumps({"chan_doan": "T1 lên: đà 1,4.", "chon": [{"id": "t1", "ly_do": "đà 1,4"}],
                           "so_dan": [{"so": 1.4, "nguon": "k:T1/da"}]})

    kq = tong.hop_tuan(goc, llm, thu=True, bay_gio=BAY)
    assert kq["se_lam"] and not os.path.exists(os.path.join(goc, tong.THU_MUC))
    # nhịp ngày: kênh 3 khe/ngày (dù đang lên) → MỘT khe/ngày, chu kỳ 1 ngày
    assert "k:T1/da = 1.4" in kq["loi_nhac"] and kq["thuc_don"][0]["moi"]["nhip_dang"] == "05:00"
    assert kq["thuc_don"][0]["moi"]["chu_ky_dang_ngay"] == 1
    # tu_ap nhưng chưa có thành tích chia khe (n < 10) → chỉ gợi ý (Đợt F: quyền tự áp theo độ chính xác)
    from core.giam_doc import hoi_dong

    kq = tong.hop_tuan(goc, llm, ep_che_do="tu_ap", bay_gio=BAY - _dt.timedelta(days=30))
    assert not kq["da_lam"] and kq["se_lam"] and kq["quyen_chia_khe"] == "goi_y"
    os.remove(os.path.join(goc, tong.THU_MUC, tong.TEP_SO))
    monkeypatch.setattr(hoi_dong, "quyen", lambda g, m, l: "tu_ap")
    kq = tong.hop_tuan(goc, llm, ep_che_do="tu_ap", bay_gio=BAY)
    from core.kenh import doc_yaml

    cai = doc_yaml(os.path.join(goc, "CHANNEL", "T1", "kenh.yaml"))
    assert int(cai["video_toi_da_ngay"]) == 1 and int(cai["ngan_sach_ngay"]) == 500000
    assert str(cai["nhip_dang"]) == "05:00" and int(cai["chu_ky_dang_ngay"]) == 1
    assert os.path.isfile(os.path.join(goc, tong.THU_MUC, tong.TEP_MD))
    assert "T1 3 video/ngày→1 video/ngày" in tong.cau_the(goc)["cau"]
    # tuần sau: đang nghỉ 14 ngày → chặn
    _kenh_tong(goc, khe="00:00, 05:00, 12:00, 20:00")
    monkeypatch.setattr(tong, "bang_cong_ty", lambda g, b=None: [dict(
        _dong("T1", "len", 4, 1.4), cac_ma=["T1"], hien_thi_7=1, hien_thi_7_truoc=1, gio_xem_7=1, sub_7=1, thang_28=1,
        kl_28=1, tv_48h_14=1, ypp_sub=1, ypp_gio=1, bao_cao_kenh="", _video=[])])
    kq = tong.hop_tuan(goc, llm, ep_che_do="tu_ap", bay_gio=BAY + _dt.timedelta(days=7))
    assert not kq["da_lam"] and "nghỉ" in kq["thuc_don"][0]["ly_do_kiem"]


def test_quay_lui_khi_hien_thi_tut_30_phan_tram():
    luc = BAY - _dt.timedelta(days=8)
    so_ = {"thay_doi": [{"id": "x", "ma": "T1", "luc": luc.isoformat(), "khe_cu": 3, "khe_moi": 4, "trang_thai": "mo",
                         "nen": {"tv_48h_14": 3000}, "cu": {}, "moi": {}}]}
    bang = [{"cac_ma": ["T1"], "_video": [(luc + _dt.timedelta(days=1), 1500), (luc + _dt.timedelta(days=2), 1800)]}]
    assert tong.can_quay_lui(bang, {}, so_, BAY)[0]["ly_do_quay_lui"].startswith("hiển thị 48h")
    bang[0]["_video"] = [(luc + _dt.timedelta(days=1), 2900), (luc + _dt.timedelta(days=2), 3100)]
    assert tong.can_quay_lui(bang, {}, so_, BAY) == []
    assert tong.can_quay_lui(bang, {"phan_tram_khe_nang": 95}, so_, BAY)[0]["ly_do_quay_lui"].startswith("máy quá tải")


def test_den_han_thu_hai_sau_luot_tuan_va_mot_lan(tmp_path):
    goc = str(tmp_path)
    thu_hai = _dt.datetime(2026, 10, 5, 9, 0)
    assert not tong.den_han(goc, thu_hai)                                   # chưa bật
    _ghi(os.path.join(goc, "workspace", "cai-dat.json"), '{"tong_giam_doc": "goi_y"}')
    assert tong.den_han(goc, thu_hai) and not tong.den_han(goc, thu_hai + _dt.timedelta(days=1))
    _ghi(os.path.join(goc, "CHANNEL", "G", "kenh.yaml"), "ma: G\ngiam_doc: goi_y\n")
    assert not tong.den_han(goc, thu_hai)                                   # giám đốc kênh chưa chạy lượt tuần
    giam_doc.stn.ghi_trang_thai(goc, "G", ngay_tuan="2026-10-05")
    assert tong.den_han(goc, thu_hai)
    kn._ghi_json(os.path.join(goc, tong.THU_MUC, tong.TEP_SO), {"hop": [{"ngay": "2026-10-05"}], "thay_doi": []})
    assert not tong.den_han(goc, thu_hai)
