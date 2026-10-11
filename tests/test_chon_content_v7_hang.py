"""Chọn content 12/10/2026 — V7 chọn theo HẠNG, trọng số theo bằng chứng, cổng tuổi theo tệp, chia khe V7/VPH,
biên tập chỉ phủ quyết (+ sổ Brier), đường ép chọn của bộ não, kiểm trùng ý miễn biến thể video thắng, chủ quyền vùng.

Dữ liệu giả hoàn toàn (mã video/kênh/tiêu đề bịa). Không mạng, không ví.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import types

from core import chien_luoc
from core import chien_truong
from core import chu_quyen_vung as cq
from core import cong_thuc_v7 as v7
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core import du_doan_bien_tap as ddbt
from core import kiem_trung_y
from core import nao
from core import tu_chay
from core.chien_luoc import ngu_canh
from core.chien_luoc import v7 as ct_v7
from core.phan_tuyen import MA_TRUNG_NIEN

K = "KX-T1"
NO_LOG = lambda _m: None  # noqa: E731


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _kenh(goc, ma=K, *yaml, v7_cfg=None):
    _ghi(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "\n".join(('ma: "{0}"'.format(ma),) + yaml) + "\n")
    if v7_cfg is not None:
        _ghi(os.path.join(so.thu_muc_nghien_cuu(goc, ma), v7.TEP_CAU_HINH), json.dumps(v7_cfg, ensure_ascii=False))
    return ma


def _cfg_cu(**them):
    """Tệp cấu hình V7 phiên bản 4 như mọi kênh đang có trên đĩa (mặc định cũ ghi nguyên ra)."""
    ch = json.loads(json.dumps(v7.CAU_HINH_MAC_DINH, ensure_ascii=False))
    ch["phien_ban"] = 4
    ch["trong_so"] = {"cum": 30, "pool": 25, "no": 20, "len": 15, "khuon": 10}
    ch["no"].update(san_view=50000, loai_kenh_yeu=True)
    ch["khuon"].pop("phan", None)
    ch.pop("chon", None)
    ch.pop("tuoi", None)
    ch.update(them)
    return ch


# ── cấu hình phiên bản 5 ─────────────────────────────────────────────────────

def test_nang_cap_v5_chi_doi_khoa_con_gia_tri_mac_dinh_cu():
    tep = _cfg_cu()
    tep["no"]["san_view"] = 30000            # khách đã tự sửa → giữ
    moi, doi = v7.nang_cap_v5(tep, v7.CAU_HINH_MAC_DINH)
    assert moi["phien_ban"] == 5 and moi["trong_so"] == {"cum": 30, "pool": 25, "no": 30, "len": 0, "khuon": 15}
    assert moi["no"]["san_view"] == 30000 and moi["no"]["loai_kenh_yeu"] is False
    assert any("trong_so" in x for x in doi) and not any("san_view" in x for x in doi)
    assert v7.nang_cap_v5(moi, v7.CAU_HINH_MAC_DINH) == (moi, [])        # đã ≥ 5: không đụng


def test_nang_cap_tep_trung_nien_cong_tuoi_theo_tep():
    tep = _cfg_cu(tep=MA_TRUNG_NIEN, tu_tuoi=list(v7._TU_TUOI_TRUNG_NIEN_CU))
    moi, _doi = v7.nang_cap_v5(tep, v7.CAU_HINH_MAC_DINH)
    assert moi["tu_tuoi"] == v7.TU_TUOI_TRUNG_NIEN and moi["tuoi"]["ai_lon_tuoi"] == "tru"
    em = v7.cau_hinh_cho_tep(_cfg_cu(), MA_TRUNG_NIEN)
    assert em["tu_tuoi"] == v7.TU_TUOI_TRUNG_NIEN and em["tuoi"]["ai_lon_tuoi"] == "tru"
    assert em["phien_ban"] == 5 and em["chon"]["theo_hang"] and em["trong_so"]["len"] == 0


def test_nap_cau_hinh_kenh_chay_chien_luoc_duoc_nang_va_sao_luu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K, 'chien_luoc: "v7:0.5, vph:0.5"', v7_cfg=_cfg_cu())
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, K), v7.TEP_CAU_HINH)
    ch, _ = v7.nap_cau_hinh(goc, K, ghi_neu_thieu=False)
    assert ch["trong_so"]["no"] == 30 and ch["no"]["san_view"] == 10000 and ch["chon"]["theo_hang"]
    assert ch["_nang_cap"] and json.load(io.open(duong, encoding="utf-8"))["phien_ban"] == 4   # không ghi
    v7.nap_cau_hinh(goc, K)                                                                       # có ghi
    assert json.load(io.open(duong, encoding="utf-8"))["phien_ban"] == 5
    assert json.load(io.open(duong + v7.DUOI_SAO_LUU_V5, encoding="utf-8"))["phien_ban"] == 4


def test_kenh_khong_tron_cong_thuc_giu_luat_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K, 'cong_thuc_chon: "v7"', v7_cfg=_cfg_cu())
    ch, _ = v7.nap_cau_hinh(goc, K)
    assert ch["trong_so"]["len"] == 15 and ch["no"]["san_view"] == 50000 and not ch["chon"]["theo_hang"]
    assert ch["khuon"]["phan"]["dai_tot"] == 0.5
    _kenh(goc, K, 'cong_thuc_chon: "v7"', "v7_nang_cap: true")
    assert v7.nap_cau_hinh(goc, K, ghi_neu_thieu=False)[0]["chon"]["theo_hang"]


def test_chon_theo_hang_top_n_va_san():
    ch = {"chon": {"theo_hang": True, "top_n": 3, "diem_san": 20, "vuot_san": 3}}
    ds = [{"ma": "a", "diem": 50, "vuot": 9}, {"ma": "b", "diem": 40, "vuot": 2}, {"ma": "c", "diem": 15, "vuot": 30},
          {"ma": "d", "diem": 30, "vuot": None}, {"ma": "e", "diem": 99, "vuot": 40}]
    nhan, bo = v7.chon_theo_hang(ds, ch)
    assert [d["ma"] for d in nhan] == ["a"]
    assert {d["ma"]: ly for d, ly in bo}["b"].startswith("nguồn chỉ gấp")
    assert "ngoài top 3" in {d["ma"]: ly for d, ly in bo}["e"]
    cu, _ = v7.chon_theo_hang([dict(d, loai=v7.NEN_LAM if d["ma"] == "c" else v7.BO) for d in ds],
                              {"chon": {"theo_hang": False}})
    assert [d["ma"] for d in cu] == ["c"]


def _so_content(goc, dong):
    cot = so.cot_mac_dinh()
    hang = []
    for ma, kenh, td, view, tang, dai in dong:
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": kenh, "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": view, so.COT_TANG: tang, "Thời lượng": dai, "Ngày đăng": "2026-10-01"})
        hang.append([d[c] for c in cot])
    so.luu_bang(goc, K, cot, hang)


def _danh_ba(goc, dong):
    cot = list(db.COT)
    hang = []
    for i, (ten, tv) in enumerate(dong):
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": ten, "Trạng thái": db.THEO_DOI, "View TV": tv, "Link kênh": "https://www.youtube.com/@gia" + str(i)})
        hang.append([d[c] for c in cot])
    db.luu(goc, K, cot, hang)


def test_cham_v5_kenh_yeu_chi_tru_san_view_10k_dang_len_khong_tinh(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K, 'chien_luoc: "v7:0.5, vph:0.5"')
    _so_content(goc, [
        ("gia00000001", "kenhYeu", "【心理学】静かな人ほど持っている特徴", "30000", "500", "15:00"),
        ("gia00000002", "kenhManh", "【心理学】優しい人ほど隠している本音", "20000", "900", "35:00"),
        ("gia00000003", "kenhManh", "【心理学】強い人の意外な理由", "5000", "100", "15:00"),
    ])
    _danh_ba(goc, [("kenhYeu", "1000"), ("kenhManh", "2000")])
    kq = v7.cham(goc, K)
    diem = {d.ma: d for d in kq.ung_vien}
    loai = {d.ma: d.bi_loai for d in kq.bi_loai}
    assert "gia00000001" in diem and any("kênh yếu, −5" in x for x in diem["gia00000001"].ly_do)
    assert any("dài 15:00 — khuôn 12–21" in x for x in diem["gia00000001"].ly_do)
    assert "gia00000002" in diem, "nguồn 20.000 view qua sàn 10.000"
    assert loai["gia00000003"].startswith("nguồn quá nhỏ")
    assert all(d.diem_len == 0 for d in kq.ung_vien)
    assert any("không tính điểm" in x for x in diem["gia00000002"].ly_do)
    # Nổ: gấp 30× (≥ 25) → trần 30 trừ 5 kênh yếu = 25; gấp 10× trên kênh thường ≥ 75% của 30.
    assert diem["gia00000001"].diem_no == 25 and diem["gia00000002"].diem_no >= 22.5


def test_cong_tuoi_che_do_tru(tmp_path):
    goc = str(tmp_path)
    cfg = dict(v7.CAU_HINH_MAC_DINH, tu_tuoi=["晩年"], tuoi={"tu_khoa": "tru", "ai_lon_tuoi": "tru", "tru": 10})
    _kenh(goc, K, 'chien_luoc: "v7:0.5, vph:0.5"', v7_cfg=cfg)
    _so_content(goc, [("gia00000011", "kenhManh", "晩年に幸せな人の特徴", "90000", "500", "15:00"),
                      ("gia00000012", "kenhManh", "静かな人の特徴", "90000", "500", "15:00")])
    _danh_ba(goc, [("kenhManh", "3000")])
    kq = v7.cham(goc, K)
    diem = {d.ma: d for d in kq.ung_vien}
    assert "gia00000011" in diem, "chế độ trừ: không loại"
    assert diem["gia00000011"].diem == diem["gia00000012"].diem - 10
    assert any("chỉ trừ điểm" in x for x in diem["gia00000011"].ly_do)


# ── bộ điều phối: V7 theo hạng + chia khe ────────────────────────────────────

def _dong_v7(ma, diem, vuot=10.0, loai=v7.BO):
    return v7.DongV7(ma=ma, tieu_de="tiêu đề " + ma, link="https://youtu.be/" + ma, kenh="kenhManh", diem=diem,
                     loai=loai, vuot=vuot, dai_giay=900)


def _cham_v7_gia(dong, ch=None):
    ch = ch or json.loads(json.dumps(v7.CAU_HINH_MAC_DINH))
    return lambda _g, _k: types.SimpleNamespace(ung_vien=list(dong), bi_loai=[], cau_hinh=ch)


def test_v7_chien_luoc_nhan_top_hang_khong_can_60_diem(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K)
    dong = [_dong_v7("v7gia%05d" % i, 50 - i, vuot=(2.0 if i == 1 else 10.0)) for i in range(12)]
    nc = ngu_canh.dung(goc, K, co_v7=False, cham_v7=_cham_v7_gia(dong))
    assert ct_v7.ap_dung(nc) > 0, "kênh chưa có video thắng vẫn dùng được V7 khi chọn theo hạng"
    ra = ct_v7.cham(nc)
    ma = [d["ma"] for d in ra]
    assert ma[0] == "v7gia00000" and "v7gia00001" not in ma and len(ma) == 9   # top 10, bỏ 1 dòng gấp 2×
    assert ra[0]["hang_v7"] == 1 and any("chọn theo hạng" in x for x in ra[0]["ly_do"])
    ch_cu = dict(json.loads(json.dumps(v7.CAU_HINH_MAC_DINH)), chon={"theo_hang": False})
    nc2 = ngu_canh.dung(goc, K, co_v7=True, cham_v7=_cham_v7_gia(
        dong[:2] + [_dong_v7("v7giaNENLAM", 61, loai=v7.NEN_LAM)], ch_cu))
    assert [d["ma"] for d in ct_v7.cham(nc2)] == ["v7giaNENLAM"]


def _so_luot(goc, ma, cong_thuc, ngay="2026-10-10"):
    duong = tu_chay.duong_bao_cao_ngay(goc, ma, ngay)
    du = json.load(io.open(duong, encoding="utf-8")) if os.path.isfile(duong) else {"runs": []}
    n = len(du["runs"]) + 1
    du["runs"].append({"ma_luot": "{0}{1:03d}".format(ngay[-2:], n),
                       "nguon": {"link": "https://youtu.be/luot{0}{1:04d}".format(ngay[-2:], n), "cong_thuc": cong_thuc},
                       "ban_giao": {"ma_goi": "{0}-{1}{2:03d}".format(ma, ngay[-2:], n)}})
    _ghi(duong, json.dumps(du))


VPH = [{"nguon": "vph", "ma": "vphgia%04d" % i, "link": "https://youtu.be/vphgia%04d" % i, "tieu_de": "vph %d" % i,
        "diem": 90 - i, "ly_do": []} for i in range(4)]


def _xep(goc, dong_v7):
    return tu_chay.ung_vien_xep_hang(goc, K, False, set(), cham_v7=_cham_v7_gia(dong_v7),
                                     cham_vph=lambda _g, _k: [dict(d) for d in VPH], log=NO_LOG)


def test_chia_khe_v7_thieu_thi_ca_bang_v7_dung_truoc(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K, 'chien_luoc: "v7:0.5, vph:0.5"', "chien_luoc_tham_do: 0", "phan_cum_ai: false")
    dong = [_dong_v7("v7gia%05d" % i, 50 - i) for i in range(3)]
    for _ in range(3):
        _so_luot(goc, K, "vph", ngay=dt.date.today().isoformat())
    ds = _xep(goc, dong)
    assert [d["cong_thuc"] for d in ds[:3]] == ["v7", "v7", "v7"], "V7 thiếu khe (0/3) → cả bảng V7 trước"
    for _ in range(4):
        _so_luot(goc, K, "v7", ngay=dt.date.today().isoformat())
    assert _xep(goc, dong)[0]["cong_thuc"] == "vph", "V7 đã đủ (4/7 ≥ 50%) → khe cho VPH"
    # V7 rỗng (không dòng nào qua sàn) → VPH lấp.
    assert {d["cong_thuc"] for d in _xep(goc, [])} == {"vph"}


def test_muc_tieu_khe_v7_khong_duoi_ti_trong_khai():
    kh = chien_luoc.KeHoach({"v7": 0.2, "vph": 0.8}, cu=False, khai={"v7": 0.5, "vph": 0.5})
    assert chien_luoc.muc_tieu_khe(kh) == {"v7": 0.5, "vph": 0.5}


# ── biên tập: sổ dự đoán + Brier ─────────────────────────────────────────────

def test_so_du_doan_bien_tap_ghi_khi_doi_va_brier(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K)
    uv = [{"ma": "bt%09d" % i, "link": "https://youtu.be/bt%09d" % i, "tieu_de": "t%d" % i} for i in range(3)]
    ket = {"hang": {uv[0]["link"]: "TOT", uv[1]["link"]: "TE"}, "diem_bt": {uv[0]["link"]: 80, uv[1]["link"]: 5},
           "du_doan": {uv[0]["link"]: {"ket_cuc": "thắng"}}}
    assert ddbt.ghi(goc, K, uv, ket) == 2
    assert ddbt.ghi(goc, K, uv, ket) == 0, "phán quyết nhớ 18h trả lại cùng số → không ghi lại"
    assert ddbt.doc(goc, K)[0]["p"] == 0.8
    b = ddbt.brier([(0.8, 1), (0.8, 0), (0.1, 0), (0.1, 0)])
    assert b["n"] == 4 and b["brier"] == round((0.04 + 0.64 + 0.01 + 0.01) / 4, 4) and b["ti_le_thang"] == 0.25
    assert b["ky_nang"] is not None and b["ky_nang"] < 1
    assert ddbt.cham(goc, K)["n"] == 0                                     # chưa video nào làm từ các nguồn này


# ── bộ não: ép chọn ──────────────────────────────────────────────────────────

def _de_cu(goc, *link, kenh=K):
    ds = [{"id": "n%03d" % (i + 1), "luc": "2026-10-12T05:00:00", "lenh": "uu-tien-nguon",
           "tham_so": {"kenh": kenh, "link": l}, "ly_do": "nguồn làm tiếp video thắng", "du_doan": "x" * 12,
           "kiem_ngay": "2026-10-20", "trang_thai": "mo", "cham": None} for i, l in enumerate(link)]
    nao.ghi_hanh_dong(goc, ds)


def test_ep_chon_noi_nguon_ngoai_top_va_cong_mem_khong_noi_cong_cung(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, K)
    ngoai_top = _dong_v7("epgiaNGOAI1", 10)
    mem = _dong_v7("epgiaMEM001", 0)
    mem.bi_loai = "nguồn quá nhỏ (8.000 view)"
    cung = _dong_v7("epgiaCUNG01", 0)
    cung.bi_loai = "kênh nguồn lạc ngách"
    kq = types.SimpleNamespace(ung_vien=[_dong_v7("v7gia%05d" % i, 50 - i) for i in range(12)] + [ngoai_top],
                               bi_loai=[mem, cung], cau_hinh=v7.CAU_HINH_MAC_DINH)
    _de_cu(goc, "https://youtu.be/epgiaNGOAI1", "https://www.youtube.com/watch?v=epgiaMEM001",
           "https://youtu.be/epgiaCUNG01", "https://youtu.be/epgiaKHONG1")
    log = []
    nc = ngu_canh.dung(goc, K, co_v7=False, log=log.append)
    nc._kq_v7 = kq
    ds = nao.ep_chon(nc, [{"ma": "v7gia00000", "link": "https://youtu.be/v7gia00000", "tieu_de": "x", "diem": 50}])
    them = {d["ma"]: d for d in ds[1:]}
    assert set(them) == {"epgiaNGOAI1", "epgiaMEM001"} and all(d["ep_chon"] for d in them.values())
    assert any("cổng chất lượng" in x and "n003" in x for x in log) and any("chưa có trong sổ" in x for x in log)
    ra = nao.ap_uu_tien(goc, K, ds)
    assert {ra[0]["ma"], ra[1]["ma"]} == {"epgiaNGOAI1", "epgiaMEM001"} and ra[0]["bo_nao"]


def test_nguon_ep_chon_khong_bi_cua_kho_loi_thoai_doi(tmp_path, monkeypatch):
    from core import loi_thoai

    monkeypatch.setattr(loi_thoai, "co_loi_thoai", lambda _g, _k, ma: ma == "b")
    ds = [{"ma": "a", "tieu_de": "a", "ep_chon": True}, {"ma": "b", "tieu_de": "b"}]
    assert tu_chay._uu_tien_co_kho(str(tmp_path), K, ds, NO_LOG)["ma"] == "a"
    assert tu_chay._uu_tien_co_kho(str(tmp_path), K, [dict(ds[0], ep_chon=False), ds[1]], NO_LOG)["ma"] == "b"


# ── kiểm trùng ý: miễn biến thể video thắng ─────────────────────────────────

def test_la_cua_video_thang_chi_mien_dong_cua_chinh_kenh():
    khoa = ({"đã đăng vidTHANG001", "kế hoạch KX-T1-0005", "lượt KX-T1/0005 ("}, {"tiêu đề thắng"})
    assert kiem_trung_y.la_cua_video_thang("bất kỳ", "đã đăng vidTHANG001", khoa, K)
    assert kiem_trung_y.la_cua_video_thang("nguồn của nó", "lượt KX-T1/0005 (tiêu đề nguồn)", khoa, K)
    assert kiem_trung_y.la_cua_video_thang("tiêu đề thắng", "KX-T1 đã đăng · 9k hiển thị", khoa, K)
    assert not kiem_trung_y.la_cua_video_thang("tiêu đề thắng", "KY-T2: kế hoạch KY-T2-0001", khoa, K)
    assert not kiem_trung_y.la_cua_video_thang("tiêu đề thắng", "KY-T2 đã đăng · 9k hiển thị", khoa, K)
    assert not kiem_trung_y.la_cua_video_thang("khác", "lượt KX-T1/0006 (tiêu đề nguồn)", khoa, K)
    giu, n = kiem_trung_y.bo_video_thang([("a", "đã đăng vidTHANG001"), ("b", "lượt KX-T1/0006 (x)")], khoa, K)
    assert giu == [("b", "lượt KX-T1/0006 (x)")] and n == 1


def test_chon_khong_trung_y_cho_phep_bien_the_video_thang(tmp_path, monkeypatch):
    monkeypatch.setattr(kiem_trung_y, "khoa_video_thang", lambda _g, _k: ({"đã đăng vidTHANG001"}, set()))
    hoi = []

    def goi(loi_nhac, **_kw):
        hoi.append(loi_nhac)
        return json.dumps({"trung": "người hiền thắng" in loi_nhac, "voi": "người hiền thắng", "ly_do": "x"})

    ds = [{"ma": "c1", "tieu_de": "người hiền góc mới", "link": "https://youtu.be/c1"}]
    da_lam = [("người hiền thắng", "đã đăng vidTHANG001"), ("chuyện khác", "lượt KX-T1/0002 (tiêu đề nguồn)")]
    log = []
    assert tu_chay._chon_khong_trung_y(str(tmp_path), K, ds, log.append, da_lam_tieu_de=da_lam,
                                       goi_chat=goi)["ma"] == "c1"
    assert hoi and "người hiền thắng" not in hoi[0] and any("video THẮNG" in x for x in log)


# ── chủ quyền vùng ───────────────────────────────────────────────────────────

def test_chon_chu_theo_thang_vung_loi_va_vung_nong():
    tk = {"vung-a": {"KA": {"thang": 2, "n": 4, "hien_thi_thang": 90000}, "KB": {"thang": 2, "n": 3,
                                                                              "hien_thi_thang": 20000}},
          "vung-b": {"KA": {"thang": 3, "n": 3, "hien_thi_thang": 10}},
          "vung-c": {"KC": {"thang": 0, "n": 2, "pv_tb": 60.0}}}
    song = {"KA": True, "KB": True, "KC": True, "KD": False}
    tt = {"vung-a": 9e6, "vung-b": 1e6, "vung-c": 5e6, "vung-d": 4e6, "vung-nho": 1000}
    ra = cq.chon_chu(tk, song, tt, {"KB": {"vung-d"}}, cu={"vung": {"vung-x": {"chu": "KD", "nguon": "tay"}}})
    assert ra["vung-a"]["chu"] == "KB", "bằng thắng → vùng là phần lớn hơn trong video thắng của kênh (lõi)"
    assert ra["vung-b"]["chu"] == "KA"
    assert ra["vung-c"]["chu"] == "KC", "vùng nóng chưa ai thắng → kênh đã có video trong vùng"
    assert ra["vung-d"]["chu"] == "KB", "vùng là cụm riêng của tệp kênh"
    assert "vung-nho" not in ra and ra["vung-x"] == {"chu": "KD", "nguon": "tay"}
    # Ổn định: chủ cũ giữ vùng khi kênh khác không NHIỀU thắng hơn; AI hợp tệp thắng điểm máy cho vùng nóng.
    ra2 = cq.chon_chu(tk, song, tt, {}, cu={"vung": {"vung-a": {"chu": "KA", "nguon": "tu_dong"}}},
                      hop_ai={"vung-d": "KC"})
    assert ra2["vung-a"]["chu"] == "KA" and ra2["vung-d"]["chu"] == "KC"


def _nhom(goc, *ma):
    for m in ma:
        _kenh(goc, m, 'nhom: "nhom-gia"')


def test_ap_chu_quyen_phat_chia_se_nhuong_va_chu_da_phu_quyet(tmp_path):
    goc = str(tmp_path)
    _nhom(goc, "KA", "KB", "KC")
    cq.ghi(goc, {"he_so_phat": 0.6, "vung": {
        "vung-a": {"chu": "KB"}, "vung-b": {"chu": "KB", "chia_se": ["KA"]}, "vung-c": {"chu": "KB", "nhuong": True},
        "vung-d": {"chu": "KB", "chan": True}, "vung-e": {"chu": "KA"}}})
    _ghi(os.path.join(goc, "CHANNEL", "KB", "nghien-cuu", "bien-tap", "nho-cham.json"),
         json.dumps({"tuchoi00001": {"hang": "TE", "luc": "2026-10-12T05:00:00"}}))
    dong = [{"ma": m, "link": "https://youtu.be/" + m, "tieu_de": m, "diem": 50.0, "cum_tu_hoc": v, "ly_do": []}
            for m, v in (("phat0000001", "vung-a"), ("chiase00001", "vung-b"), ("nhuong00001", "vung-c"),
                         ("chan0000001", "vung-d"), ("cuaminh0001", "vung-e"), ("tuchoi00001", "vung-a"))]
    bang = {"v7": dong}
    nc = ngu_canh.dung(goc, "KA", co_v7=False)
    assert cq.ap_he_so(nc, bang) == (1, 1)
    d = {x["ma"]: x for x in bang["v7"]}
    assert d["phat0000001"]["diem"] == 30.0 and d["phat0000001"]["tin_hieu"]["chu_quyen"]["chu"] == "KB"
    assert d["chiase00001"]["diem"] == d["nhuong00001"]["diem"] == d["tuchoi00001"]["diem"] == 50.0
    assert "chan0000001" not in d and d["cuaminh0001"]["tin_hieu"]["vung_chu"] == "vung-e"
    assert bang["v7"][-1]["ma"] == "phat0000001", "xếp lại sau khi phạt"
    # Kênh không cùng nhóm: bản đồ không áp.
    _kenh(goc, "KZ")
    assert cq.ap_he_so(ngu_canh.dung(goc, "KZ", co_v7=False), {"v7": [dict(dong[0])]}) == (0, 0)


def test_lenh_tan_cong_khong_giao_vung_cua_kenh_khac():
    ds = [{"ma": "vung-a", "ten": "A", "co_hoi": 90.0, "dich": 1, "ta_kenh": []},
          {"ma": "vung-b", "ten": "B", "co_hoi": 50.0, "dich": 1, "ta_kenh": []}]
    quan = [{"ma": "KA", "so_video": 3}, {"ma": "KB", "so_video": 3}]
    ra = {x["kenh"]: [v["ma"] for v in x["vung"]] for x in chien_truong.de_xuat_tan_cong(
        ds, quan, so_vung=1, chu_quyen={"vung": {"vung-a": {"chu": "KB"}}})}
    assert ra == {"KA": ["vung-b"], "KB": ["vung-a"]}
