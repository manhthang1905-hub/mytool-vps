"""Đội chuyên gia + hội đồng quyết định + sổ độ chính xác (Đợt F, 01/10/2026); đo công suất cửa sổ gần.

Cô lập: `tmp_path`, LLM giả (trả lời theo VAI đọc từ lời nhắc), không mạng, không ví, không CHANNEL thật.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os

from core import bien_tap_content, cong_suat, giam_doc
from core.giam_doc import hoi_dong as hd
from core.giam_doc import kham_nghiem as kn
from core.giam_doc import quan_ly
from tests.test_giam_doc_plugin import _ghi, _llm_chon_het, dung_kenh_mau

SL = {"v:A/52h/hien_thi": 1200, "v:A/52h/ctr": 4.1, "kenh/tv@48h/hien_thi": 3000, "kenh/tv@48h/ctr": 5.0,
      "kenh/tv@48h/n": 6, "v:A/giu/giu_30s": 62.0}


def _tl(chan_doan, so_dan, bai=None, cong="hien_thi", **them):
    du = {"chan_doan": chan_doan, "cong_hong": cong, "vi_sao": "cụm nguội", "du_doan_lech": "",
          "nhan": {"kieu_tieu_de": "so_dem", "kieu_hook": "nghich_ly"},
          "bai_hoc": {"truc": "hook", "gia_tri": "nghich_ly", "huong": "+", "cum": "",
                      "cau": "Hook nghịch lý giữ 62% ở 0:30."},
          "so_dan": so_dan, "luan_diem": [{"cau": "Hiển thị 1.200 < 3.000 trung vị.",
                                           "so_dan": [{"so": 1200, "nguon": "v:A/52h/hien_thi"}]}]}
    if bai:
        du["bai_hoc_cua_toi"] = bai
    du.update(them)
    return json.dumps(du, ensure_ascii=False)


def _llm(cham='{"chon": "A", "diem": {"A": 8, "B": 6}, "do_tin": 0.8, "trai_tri_thuc": false, "ly_do": "x"}',
         phan_bien=None, goi=None):
    def f(ln, mo_hinh="", khoa="", toi_da_token=0):
        if goi is not None:
            goi.append((ln[:60], mo_hinh, khoa))
        if ln.startswith("Bạn là CHUYÊN GIA NỀN TẢNG"):
            return _tl("Hiển thị 1.200 so với 3.000: cổng hiển thị hỏng.",
                       [{"so": 1200, "nguon": "v:A/52h/hien_thi"}, {"so": 3000, "nguon": "kenh/tv@48h/hien_thi"}],
                       bai={"khoa": "hien_thi|thap", "cau": "Hiển thị 1.200 @52h = 40% trung vị.",
                            "so_dan": [{"so": 1200, "nguon": "v:A/52h/hien_thi"}]})
        if ln.startswith("Bạn là CHUYÊN GIA KHÁN GIẢ"):
            return _tl("Giữ 62% ở 0:30, CTR 4,1%: cổng CTR.", [{"so": 4.1, "nguon": "v:A/52h/ctr"}], cong="ctr",
                       bai={"khoa": "hook|giu", "cau": "Hook nghịch lý giữ 62% ở 0:30.",
                            "so_dan": [{"so": 62.0, "nguon": "v:A/giu/giu_30s"}]})
        if ln.startswith("Bạn là CHUYÊN GIA CHỦ ĐỀ"):  # bịa: CTR 9 (thật 4,1)
            return _tl("CTR 9% rất cao nên lỗi ở hiển thị.", [{"so": 9, "nguon": "v:A/52h/ctr"}])
        if ln.startswith("Bạn là NGƯỜI PHẢN BIỆN"):
            return phan_bien or json.dumps({"A": {"nguoc": "CTR 4,1 < 5,0", "giai_thich_khac": "bìa", "muc": "vua"},
                                            "B": {"nguoc": "—", "giai_thich_khac": "—", "muc": "yeu"}})
        if ln.startswith("Bạn là HỘI ĐỒNG"):
            return cham
        return "rác"
    return f


# ── mã kiểm số ─────────────────────────────────────────────────────────────

def test_khop_va_so_khong_nguon():
    assert hd.khop(1200, 1200) and hd.khop("1.200", 1200) and hd.khop("4,1", 4.1) and hd.khop(10.8, 10.83)
    assert not hd.khop(9, 4.1) and not hd.khop("", 4.1)
    dung, bia = hd.kiem_so_dan([{"so": 1200, "nguon": "v:A/52h/hien_thi"}, {"so": 9, "nguon": "v:A/52h/ctr"},
                                {"so": 1, "nguon": "khoa-la"}], SL)
    assert [x["nguon"] for x in dung] == ["v:A/52h/hien_thi"] and len(bia) == 2
    tap = hd.tap_so("hiển thị 47.121, CTR 10,8%", so_lieu=SL)
    assert hd.so_khong_nguon("47.121 hiển thị, CTR 10,8%, 3 cổng, 1.200 và 77,7", tap) == ["77,7"]


# ── một phiên hội đồng (khám nghiệm) ───────────────────────────────────────

def test_hop_loai_phuong_an_so_bia_phan_bien_cham_do_tin_va_so_chuyen_gia(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K", "kenh.yaml"), "ma: K\ngiam_doc: goi_y\nnhom: ng\n")
    os.makedirs(os.path.join(goc, "CHANNEL", "_NHOM", "ng"))
    goi = []
    q = quan_ly.goi_quyet("kham_nghiem", "LỜI NHẮC KHÁM\nSỐ LIỆU ...", SL, _llm(goi=goi),
                          doc=lambda t: kn.doc_ket_qua(t, SL), goc=goc, ma="K", khoa="kh", hoi_dong=True, n=6,
                          nhan={"video_id": "A", "moc": "48h"})
    h = q["hoi_dong"]
    cg = {x["ma"]: x for x in h["chuyen_gia"]}
    assert cg["chu_de"]["loai_bo"] and "v:A/52h/ctr=9" in cg["chu_de"]["ly_do_loai"]
    assert not cg["nen_tang"]["loai_bo"] and not cg["khan_gia"]["loai_bo"]
    assert set(h["phan_bien"]["y_kien"]) == {"nen_tang", "khan_gia"}
    assert h["quyet"]["chon"] in ("nen_tang", "khan_gia") and h["quyet"]["do_tin_llm"] == 0.8
    assert 0 < h["quyet"]["do_tin"] <= 1 and h["cong"] in ("ap", "thu_nho")
    assert q["ket"]["cong_hong"] in ("hien_thi", "ctr") and q["ket"]["bai_hoc"]
    # phản biện chạy mô hình khác bậc đầu của chuyên gia
    pb = [g for g in goi if g[0].startswith("Bạn là NGƯỜI PHẢN BIỆN")][0]
    cgg = [g for g in goi if g[0].startswith("Bạn là CHUYÊN GIA NỀN TẢNG")][0]
    assert pb[1] != cgg[1]
    # sổ CỦA TỪNG chuyên gia: Nền tảng toàn cục, Khán giả kênh; Chủ đề (số bịa) không ghi
    nt = os.path.join(goc, "workspace", "giam-doc", "so-nen-tang.jsonl")
    kg = os.path.join(goc, "CHANNEL", "K", "giam-doc", "so-khan-gia.jsonl")
    assert os.path.isfile(nt) and os.path.isfile(kg)
    assert not os.path.exists(os.path.join(goc, "CHANNEL", "_NHOM", "ng", "so-chu-de.jsonl"))
    dong = json.loads(io.open(kg, encoding="utf-8").readline())
    assert dong["chuyen_gia"] == "khan_gia" and dong["pham_vi"] == "kenh" and dong["bong"] is True
    assert "Hook nghịch lý" in hd.doc_so(goc, "K", "khan_gia")[0]
    cuoi = json.load(io.open(os.path.join(goc, "CHANNEL", "K", "giam-doc", hd.TEP_CUOI), encoding="utf-8"))
    assert cuoi["kham_nghiem"]["quyet"]["do_tin"] == h["quyet"]["do_tin"]
    # sổ được đọc vào lời nhắc lần sau
    goi.clear()
    quan_ly.goi_quyet("kham_nghiem", "x", SL, _llm(goi=goi), doc=lambda t: kn.doc_ket_qua(t, SL), goc=goc, ma="K",
                      hoi_dong=True, luu=False)


def test_cong_tin_thap_quan_sat_n_it_thu_nho_va_tat_ca_bia():
    td = [{"id": "d1", "loai": "tham_so", "khoa": "phut_muc_tieu"}, {"id": "d2", "loai": "chi_dao"}]

    def doc(t):
        from core.goi_van_ban import loc_json
        du = loc_json(t)
        return {"chan_doan": du.get("chan_doan"), "chon": [dict(td[0]), dict(td[1])]} if "chon" in du else None

    def llm(do_tin, so=1200):
        def f(ln, mo_hinh="", khoa="", toi_da_token=0):
            if ln.startswith("Bạn là CHUYÊN GIA"):
                return json.dumps({"chan_doan": "hiển thị 1.200", "chon": [{"id": "d1"}, {"id": "d2"}],
                                   "so_dan": [{"so": so, "nguon": "v:A/52h/hien_thi"}]})
            if ln.startswith("Bạn là HỘI ĐỒNG"):
                return json.dumps({"chon": "A", "diem": {"A": 5}, "do_tin": do_tin})
            return "{}"
        return f

    q = hd.hop("giam_doc_kenh", "x", SL, llm(0.2), doc=doc, n=10, luu=False)
    assert q["hoi_dong"]["cong"] == "quan_sat" and q["ket"]["chon"] == []
    q = hd.hop("giam_doc_kenh", "x", SL, llm(0.9), doc=doc, n=1, luu=False)
    assert q["hoi_dong"]["cong"] == "thu_nho" and [m["id"] for m in q["ket"]["chon"]] == ["d1"]
    q = hd.hop("giam_doc_kenh", "x", SL, llm(0.9), doc=doc, n=10, luu=False)
    assert q["hoi_dong"]["cong"] == "ap" and len(q["ket"]["chon"]) == 2
    q = hd.hop("giam_doc_kenh", "x", SL, llm(0.9, so=999), doc=doc, n=10, luu=False)   # cả 3 bịa
    assert q["hoi_dong"]["cong"] == "quan_sat" and q["ket"]["chon"] == []
    # trái tri thức cần độ tin ≥ 0,8
    def trai(ln, mo_hinh="", khoa="", toi_da_token=0):
        if ln.startswith("Bạn là HỘI ĐỒNG"):
            return json.dumps({"chon": "A", "do_tin": 0.65, "trai_tri_thuc": True})   # +0,1 đồng thuận = 0,75
        return llm(0.7)(ln)
    q = hd.hop("giam_doc_kenh", "x", SL, trai, doc=doc, n=10, luu=False)
    assert q["hoi_dong"]["nguong"] == hd.NGUONG_TIN_TRAI and q["hoi_dong"]["cong"] == "thu_nho"


def test_goi_quyet_hoi_dong_hong_thi_di_duong_mot_luot(monkeypatch):
    from core import bien_tap_content as btc

    monkeypatch.setattr(btc, "thang_mo_hinh", lambda _g, _k: ["m1"])
    monkeypatch.setattr(hd, "hop", lambda *a, **k: (_ for _ in ()).throw(KeyError("x")))
    dong = []
    q = quan_ly.goi_quyet("x", "x", None, lambda *a, **k: '{"ok": 1}', doc=lambda t: json.loads(t), hoi_dong=True,
                          ghi=dong.append)
    assert q["ket"] == {"ok": 1} and any("đường một lượt" in d for d in dong)


def test_tri_thuc_doc_cau_in_dam():
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tt = hd.tri_thuc(goc)
    assert tt and any("Pool là điều kiện quyết định" in x for x in tt) and all("**" not in x for x in tt)


# ── chọn content: ý kiến chuyên gia cho biên tập viên ─────────────────────

def test_y_kien_chuyen_gia_chi_khi_bat_va_loi_nhac_bien_tap_y_het_khi_khong_co(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K", "kenh.yaml"), "ma: K\ngiam_doc: tat\n")
    uv = [{"tieu_de": "低IQの人", "view": 50000, "tuoi_ngay": 3.0, "da": "dang_len", "tang_ngay": 4000, "cum": ["iq"]}]

    def llm(ln, mo_hinh="", khoa="", toi_da_token=0):
        return json.dumps({"y_kien": "Ưu tiên U1: đà +4000/ngày."})

    assert hd.y_kien_ung_vien(goc, "K", uv, llm) == ""                     # env test tắt hội đồng
    monkeypatch.setenv("SHOPAPI_HOI_DONG", "1")
    assert hd.y_kien_ung_vien(goc, "K", uv, llm) == ""                     # kênh tắt giám đốc
    _ghi(os.path.join(goc, "CHANNEL", "K", "kenh.yaml"), "ma: K\ngiam_doc: goi_y\n")
    yk = hd.y_kien_ung_vien(goc, "K", uv, llm)
    assert yk.count("\n- ") == 3 and "- Nền tảng: Ưu tiên U1" in yk
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "K", "giam-doc", hd.TEP_CUOI))
    bc = bien_tap_content.dung_boi_canh(goc, "K")
    u = [dict(uv[0], link="https://youtu.be/x", ma="x", hang_cong_thuc=1)]
    truoc = bien_tap_content.dung_loi_nhac(bc, u, 1)
    assert bien_tap_content.dung_loi_nhac(dict(bc, _y_kien=""), u, 1) == truoc
    sau = bien_tap_content.dung_loi_nhac(dict(bc, _y_kien=yk), u, 1)
    assert "Ý KIẾN ĐỘI CHUYÊN GIA" in sau and sau.index("Ý KIẾN ĐỘI") < sau.index("ỨNG VIÊN (thứ tự")
    assert sau.replace("═══ Ý KIẾN ĐỘI CHUYÊN GIA ═══\n" + yk + "\n\n", "") == truoc


# ── sổ độ chính xác + quyền tự áp ──────────────────────────────────────────

def test_do_chinh_xac_theo_loai_va_quyen_co_tre(tmp_path):
    goc = str(tmp_path)
    tm = os.path.join(goc, "CHANNEL", "K", "giam-doc")
    dd = [{"video_id": "v{0}".format(i), "ket": "truot", "dung": i < 8} for i in range(10)]   # 8/10
    _ghi(os.path.join(tm, "du-doan.json"), json.dumps({"du_doan": dd}))
    kn._ghi_json(os.path.join(tm, "kham-nghiem", "A-48h.json"), {
        "video_id": "A", "moc": "48h", "ket": {"cong_hong": "hien_thi"},
        "ho_so": {"so_lieu": SL}})
    _ghi(os.path.join(tm, "thi-nghiem.json"), json.dumps({"thi_nghiem": [{"id": "t1", "trang_thai": "giu"},
                                                                         {"id": "t2", "trang_thai": "bo"}]}))
    _ghi(os.path.join(goc, "workspace", "tong-giam-doc", "so.json"),
         json.dumps({"thay_doi": [{"id": "x", "ma": "K", "trang_thai": "quay_lui"}]}))
    ra = hd.do_chinh_xac(goc, "K")
    lo = ra["loai"]
    assert (lo["du_doan"]["n"], lo["du_doan"]["ti_le"], lo["du_doan"]["quyen"]) == (10, 0.8, "tu_ap")
    assert lo["chan_doan_cong"]["dung"] == 1 and lo["doi_chuan"]["ti_le"] == 0.5 and lo["chia_khe"]["dung"] == 0
    assert lo["doi_chuan"]["quyen"] == "goi_y" and hd.quyen(goc, "K", "du_doan") == "tu_ap"
    assert os.path.isfile(os.path.join(tm, hd.TEP_DO_CHINH_XAC))
    # tụt còn 6/10 (≥ 55%, dưới 70%): giữ quyền đã có; 5/10: lùi goi_y
    for i in (7, 6, 5):
        dd[i]["dung"] = False
        _ghi(os.path.join(tm, "du-doan.json"), json.dumps({"du_doan": dd}))
        q = hd.do_chinh_xac(goc, "K")["loai"]["du_doan"]["quyen"]
        assert q == ("goi_y" if i == 5 else "tu_ap")


def test_chay_kenh_tu_ap_chua_co_quyen_chi_goi_y_va_quyet_lon_cho_chu(tmp_path):
    goc = str(tmp_path)
    dung_kenh_mau(goc)
    truoc = io.open(os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml"), encoding="utf-8").read()
    kq = giam_doc.chay_kenh(goc, "GD1", goi_chat=_llm_chon_het, tuan=True)
    assert kq.che_do == "tu_ap" and any(x["loai"] == "tham_so" for x in kq.se_lam)
    assert not [x for x in kq.da_lam if x.get("ket") == "da_ap" and x.get("khoa")]        # không tham số nào áp
    assert io.open(os.path.join(goc, "CHANNEL", "GD1", "kenh.yaml"), encoding="utf-8").read() == truoc
    if any(hd.la_quyet_lon(d) for d in kq.quyet_dinh.chon):
        assert any(x.startswith("Quyết định lớn chờ bạn duyệt") for x in kq.viec_cua_ban)
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "GD1", "giam-doc", hd.TEP_DO_CHINH_XAC))


# ── công suất: cửa sổ gần, mốc đổi lớn, giữ "ma" ─────────────────────────

def _nk(goc, *muc):
    d = os.path.join(goc, "workspace", "khe")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "nhat-ky.jsonl"), "a", encoding="utf-8") as tep:
        for m in muc:
            tep.write(json.dumps(m) + "\n")


def test_giu_ma_bi_cat_va_bo_luot_truoc_moc(tmp_path):
    goc = str(tmp_path)
    T = 1_000_000.0
    _nk(goc,
        {"viec_nk": "duoc", "lop": "api", "viec": "san_xuat", "pid": 1, "kenh": "K", "luc": T},         # chết, không nha
        {"viec_nk": "duoc", "lop": "api", "viec": "san_xuat", "pid": 2, "kenh": "K", "luc": T + 3600},
        {"viec_nk": "nha", "lop": "api", "viec": "san_xuat", "pid": 2, "luc": T + 7200},
        {"viec_nk": "duoc", "lop": "api", "viec": "san_xuat", "pid": 3, "kenh": "J", "luc": T})          # mở, trần 8h
    nk = cong_suat.doc_nhat_ky_khe(goc, T, T + 20 * 3600)
    assert nk["phut"]["api"]["san_xuat"] == 60.0 + 60.0 + cong_suat.TRAN_GIU_MO_PHUT
    nk = cong_suat.doc_nhat_ky_khe(goc, T, T + 20 * 3600, bo_truoc=T + 1800)
    assert nk["phut"]["api"]["san_xuat"] == 60.0 and [k for k, _a, _b in nk["bo_khoang"]] == ["K", "J"]


def test_cong_suat_khong_lui_qua_moc_doi(tmp_path):
    goc = str(tmp_path)
    moc = _dt.datetime(2026, 9, 30, 19, 15, 20).timestamp()
    den = moc + 10 * 3600
    _ghi(os.path.join(goc, "workspace", "cai-dat.json"), json.dumps({"lan_api": 2}))
    for i, (bd, kenh) in enumerate(((moc - 3 * 3600, "A"), (moc + 3600, "A"), (moc + 5 * 3600, "B"))):
        _nk(goc, {"viec_nk": "duoc", "lop": "api", "viec": "san_xuat", "pid": 10 + i, "kenh": kenh, "luc": bd},
            {"viec_nk": "nha", "lop": "api", "viec": "san_xuat", "pid": 10 + i, "luc": bd + 3600})
        d = os.path.join(goc, "PROJECTS", "AUTO", kenh, "000{0}".format(i))
        _ghi(os.path.join(d, "trang-thai.json"), json.dumps({"ma_kenh": kenh, "khau": {"dung": {
            "trang_thai": "xong", "bat_dau": bd + 600, "ket_thuc": bd + 3600}}}))
    # lượt 0 sinh trước mốc, khâu đầu bắt đầu sau mốc… vẫn bị bỏ vì nằm trong khoảng giữ làn của tiến trình cũ
    _ghi(os.path.join(goc, "PROJECTS", "AUTO", "A", "0000", "trang-thai.json"), json.dumps({"ma_kenh": "A", "khau": {
        "dung": {"trang_thai": "xong", "bat_dau": moc - 3 * 3600 + 600, "ket_thuc": moc + 1200}}}))
    cs = cong_suat.cong_suat_hien_tai(goc, gio=48, bay_gio=den)
    assert cs["cua_so_gio"] == 10.0 and cs["tu_moc_doi"].startswith("2026-09-30 19:15")
    assert cs["video_ban_giao"] == 2 and cs["phut_api_moi_video"] == 60.0
