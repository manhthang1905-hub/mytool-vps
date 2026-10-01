"""Cứu video CTR thấp (01/10/2026): hội đồng → chủ duyệt 3 lần đầu → hàng sửa → máy DOM đổi tiêu đề/bìa →
đo trước/sau → giữ / quay lui; vá lỗ bản chụp 48h; giờ online; luật bìa.

Cô lập: mọi thứ trong `tmp_path`; không mạng, không ví, không đọc/ghi CHANNEL hay vm/logs thật (có bài canh).
VideoId trong bài đều giả.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

GOC_KHO = Path(__file__).resolve().parent.parent
VM = GOC_KHO / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import may_dang_dom as mdd  # noqa: E402

from core import cong_thuc_v7 as v7  # noqa: E402
from core.giam_doc import cuu_ctr, du_lieu, gioi_han  # noqa: E402
from core.giam_doc.du_lieu import BangSo  # noqa: E402

BAY = _dt.datetime(2026, 10, 1, 12, 0)
K = "GDX"


def _ghi(p, du):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _doc(p):
    with io.open(p, encoding="utf-8") as tep:
        return json.load(tep)


# ═══ VÁ LỖ BẢN CHỤP 48H ═════════════════════════════════════════════════════

def test_lay_48h_du_phong_thu_tu_va_do_lech():
    assert v7.lay_48h_du_phong([(30.0, 100.0), (60.0, 400.0)]) == (pytest.approx(280.0), "noi_suy", 0.0)
    assert v7.lay_48h_du_phong([(11.3, 82.0), (37.7, 198.0)]) == (198.0, "gan", -10.3)   # chỉ có bản 38h
    assert v7.lay_48h_du_phong([(122.2, 1706.0), (124.9, 1709.0)]) == (1706.0, "sau", 74.2)  # chỉ có bản 122–125h
    assert v7.lay_48h_du_phong([(5.0, 1.0), (20.0, 9.0)]) == (None, "", None)


def _chup(tm, moc, gio_sau_dang, dang_utc, imp, *, thong_tin=True, ctr_b=None):
    """Một thư mục mốc giả: raw có `captured_at` = đăng + `gio_sau_dang` (UTC)."""
    d = os.path.join(tm, moc)
    cap = (dang_utc + _dt.timedelta(hours=gio_sau_dang)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    _ghi(os.path.join(d, "raw", "1.json"), '{"captured_at": "%s", "x": 1}' % cap)
    _ghi(os.path.join(d, "tong-quan.json"), {"impressions": imp, "ctr": 4.0, "views": imp // 25})
    if thong_tin:
        _ghi(os.path.join(d, "_thong-tin.json"), {"tieu_de": "t", "ngay_dang": dang_utc.strftime("%Y-%m-%dT%H:%M:%S")})
    if ctr_b is not None:
        _ghi(os.path.join(d, "traffic-type.csv"), "Traffic source,Imp,CTR,Views\nBrowse features,{0},{1},1\n".format(imp, ctr_b))


def test_video_qua_48h_chi_co_ban_125h_van_co_phan_quyet_va_nhan_dung(tmp_path):
    """Video chỉ có bản 122–125h (một bản nằm trong thư mục tên "13h", không có _thong-tin.json) →
    trước đây không phán, không khám; nay lấy bản SAU gần nhất (trần trên) + ghi độ lệch, nhãn = tuổi thật."""
    goc = str(tmp_path)
    tm = os.path.join(goc, "CHANNEL", K, "chi-so", "FAKEc432aaa")
    dang = _dt.datetime.utcnow() - _dt.timedelta(hours=150)
    _chup(tm, "122h", 122.2, dang, 1706)
    _chup(tm, "13h", 124.9, dang, 1709, thong_tin=False, ctr_b=13.3)
    vm = {v.ma: v for v in v7.video_cua_kenh(goc, K)}["FAKEc432aaa"]
    assert vm.hien_thi_48h == 1706 and vm.cach_48h == "sau" and vm.lech_48h == pytest.approx(74.2, abs=0.1)
    chup = du_lieu.doc_ban_chup(tm)
    assert [b["moc"] for b in chup] == ["122h", "125h"] and chup[-1]["thu_muc"] == "13h"
    assert chup[-1]["ctr_browse"] == 13.3


def test_gom_moc_gio_theo_tuoi_that_khong_theo_nhan(tmp_path):
    from core.chi_so_ytb import gom

    tm = os.path.join(str(tmp_path), "chi-so")
    dang = _dt.datetime.utcnow() - _dt.timedelta(hours=150)
    for moc in ("6h", "13h", "24h", "48h"):  # một lượt bù chép CÙNG bản 125h vào mọi thư mục
        _chup(os.path.join(tm, "FAKEc432bbb"), moc, 124.9, dang, 1709, thong_tin=(moc == "48h"))
    bg = [b for b in gom.gom(tm, {}) if b["video_id"] == "FAKEc432bbb"]
    assert [b["moc_gio"] for b in bg] == [125], "bốn bản trùng gộp còn một, mốc = tuổi thật"


def test_video_chua_qua_48h_khong_phan_som(tmp_path):
    goc = str(tmp_path)
    tm = os.path.join(goc, "CHANNEL", K, "chi-so", "FAKEtre40hh")
    dang = _dt.datetime.utcnow() - _dt.timedelta(hours=40)
    _chup(tm, "38h", 38.0, dang, 200)
    vm = {v.ma: v for v in v7.video_cua_kenh(goc, K)}["FAKEtre40hh"]
    assert vm.hien_thi_48h is None and vm.cach_48h == ""


# ═══ HỘI ĐỒNG VIẾT TIÊU ĐỀ + SỔ DUYỆT ═══════════════════════════════════════

def test_doc_tieu_de_luat_100_ky_tu_nhan_dau_va_khac_cu():
    cu = "【脳科学】高いIQを持つ人だけが見てる世界とは"
    ok = cuu_ctr.doc_tieu_de(json.dumps({"tieu_de_moi": "IQが高い人だけが気づく５つの違和感", "ly_do": "x"}), cu)
    assert ok["tieu_de_moi"].startswith("【脳科学】"), "giữ nhãn đầu"
    assert cuu_ctr.doc_tieu_de(json.dumps({"tieu_de_moi": "あ" * 101}), cu) is None
    assert cuu_ctr.doc_tieu_de(json.dumps({"tieu_de_moi": cu}), cu) is None
    assert cuu_ctr.doc_tieu_de("rác", cu) is None


def _kenh(goc, *dong):
    _ghi(os.path.join(goc, "CHANNEL", K, "kenh.yaml"), "\n".join(('ma: "{0}"'.format(K),) + dong) + "\n")


def _bs_hong(goc):
    hong = {"id": "FAKEhong001", "ma_goi": K + "-0007", "tieu_de": "【脳科学】高いIQを持つ人だけが見てる世界とは",
            "cum": [], "ket_luan": "truot", "thang": False, "hien_thi_48h": 900.0, "tuoi_gio": 70.0,
            "chup": [{"tuoi": 66.0, "moc": "66h", "hien_thi": 3000, "ctr": 3.0, "ctr_browse": 2.0}],
            "lich_su_sua": [], "tieu_de_da_cham": [], "tu_tool": True}
    bs = BangSo(goc=goc, ma_kenh=K, bay_gio=BAY, cai={"giam_doc": "goi_y", "giam_doc_studio": True},
                ctr_muc_tieu=5.0, nguong_thang_48h=6000)
    bs.video = [hong]
    return bs


def test_xu_ly_hoi_dong_lap_muc_cho_duyet_va_chu_duyet(tmp_path, monkeypatch):
    from core import bien_tap_content

    monkeypatch.setattr(bien_tap_content, "thang_mo_hinh", lambda _g, _k: ["m1"])
    goc = str(tmp_path)
    _kenh(goc, 'giam_doc: "goi_y"', "giam_doc_studio: true")
    bs = _bs_hong(goc)
    qs = cuu_ctr.quan_sat(bs)
    td = [dict(d, plugin="cuu_ctr", duoc=True) for d in cuu_ctr.de_xuat(bs, qs)]
    assert td and td[0]["chi_goi_y"] is False
    loi_nhac = []

    def llm(ln, mo_hinh="", khoa="", toi_da_token=0):
        loi_nhac.append(ln)
        return json.dumps({"tieu_de_moi": "IQが高い人だけが気づく世界の違和感５選", "khung": "so_dem_tri_tue",
                           "ly_do": "CTR trang chủ 2,0% < 4%"})
    ra = cuu_ctr.xu_ly(goc, K, bs, td, llm)
    assert len(ra) == 1 and ra[0]["trang_thai"] == "cho_duyet"
    assert ra[0]["tieu_de_moi"] == "【脳科学】IQが高い人だけが気づく世界の違和感５選"
    assert "KHUNG TIÊU ĐỀ THẮNG" in loi_nhac[0] and "≤ 100 ký tự" in loi_nhac[0]
    assert [m["id"] for m in cuu_ctr.cho_duyet(goc, K)] == [ra[0]["id"]]
    nk = [json.loads(x) for x in io.open(os.path.join(goc, "CHANNEL", K, "giam-doc", "nhat-ky.jsonl"), encoding="utf-8")]
    assert any(d["viec"] == "viec_studio" and d["video_id"] == "FAKEhong001" for d in nk), "trừ ngân sách 2/tuần"
    assert cuu_ctr.xu_ly(goc, K, bs, td, llm) == [], "mỗi video một lần"
    assert cuu_ctr.ghi_duyet(goc, K, ra[0]["id"], duyet=True)
    assert cuu_ctr.doc_duyet(goc, K)[0]["trang_thai"] == "duyet" and not cuu_ctr.cho_duyet(goc, K)


def test_quyen_tu_ap_sau_3_lan_duyet_2_lan_tot():
    ds = [{"duyet_boi": "chu", "ket": "tot"}, {"duyet_boi": "chu", "ket": "quay_lui", "ket_bia": "tot"},
          {"duyet_boi": "chu", "ket": "giu"}]
    assert cuu_ctr.quyen_studio("", K, ds)["quyen"] == "tu_ap"
    assert cuu_ctr.quyen_studio("", K, ds[:2])["quyen"] == "can_duyet"
    assert cuu_ctr.quyen_studio("", K, [dict(d, ket="giu", ket_bia="") for d in ds])["quyen"] == "can_duyet"


def test_gioi_han_tuoi_52_120_va_khong_dung_video_thang():
    bs = BangSo(goc="", ma_kenh=K, bay_gio=BAY, cai={})
    bs.video = [{"id": "a", "ma_goi": "G", "ket_luan": "truot", "thang": False, "lich_su_sua": [], "tuoi_gio": 130.0},
                {"id": "b", "ma_goi": "G", "ket_luan": "truot", "thang": False, "lich_su_sua": [], "tuoi_gio": 60.0},
                {"id": "c", "ma_goi": "G", "ket_luan": "thang", "thang": True, "lich_su_sua": [], "tuoi_gio": 60.0}]
    so = {"nhat_ky": [], "thi_nghiem": [], "trang_thai": {}}
    assert "52–120h" in gioi_han.kiem({"loai": "viec_studio", "video_id": "a"}, so, bs)[1]
    assert gioi_han.kiem({"loai": "viec_studio", "video_id": "b"}, so, bs)[0]
    assert not gioi_han.kiem({"loai": "viec_studio", "video_id": "c"}, so, bs)[0]


# ═══ ĐỒNG BỘ: hàng sửa ↔ hồ sơ ↔ đo trước/sau ↔ quay lui ═══════════════════════

def test_do_ctr_trang_chu_uu_tien_moi_phia_500():
    ls = {"moc_truoc": {"luc_chup": "2026-10-01 02:30", "impressions": 3000, "ctr": 3.0,
                        "hien_thi_trang_chu": 2000, "ctr_trang_chu": 2.0}}
    sau = {"luc_chup": "2026-10-04 02:30", "impressions": 4200, "ctr": 3.2, "hien_thi_trang_chu": 2800,
           "ctr_trang_chu": 2.5}
    do = cuu_ctr.do_ctr(ls, sau)
    assert do["du"] and do["nguon"] == "trang_chu" and do["sau"] == pytest.approx(3.75, abs=0.01)
    assert cuu_ctr.phan_xu(do) == "tot"
    it = dict(sau, hien_thi_trang_chu=2300, ctr_trang_chu=1.8)
    do2 = cuu_ctr.do_ctr(ls, it)
    assert do2["nguon"] == "chung" and do2["du"], "trang chủ < 500 hiển thị sau → lùi về CTR chung"
    assert cuu_ctr.phan_xu(cuu_ctr.do_ctr(ls, dict(it, impressions=3300))) == "", "cả hai < 500 → chưa đủ"


def _ho_so(goc, ma_goi, vid, so_lieu):
    _ghi(os.path.join(goc, "CHANNEL", K, "ho-so-video", ma_goi + ".json"),
         {"ma_goi": ma_goi, "kenh": K, "video_id": vid, "tieu_de": "cũ", "so_lieu_moi_nhat": so_lieu})


def test_dong_bo_tron_vong_duyet_sua_do_quay_lui_bia(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, 'giam_doc: "goi_y"', "giam_doc_studio: true")
    mg = K + "-0007"
    _ho_so(goc, mg, "FAKEhong001", {"luc_chup": "2026-10-01 02:30", "impressions": 3000, "ctr": 3.0,
                                    "moc_gio_that": 66})
    bia2 = os.path.join(goc, "CHANNEL", K, "ho-so-video", "anh", mg + "-bia-2.jpg")
    _ghi(bia2, "jpg")
    _ghi(os.path.join(goc, "CHANNEL", K, "ho-so-video", "anh", mg + ".jpg"), "jpg-goc")
    muc = {"id": "s-FAKEhong001-1", "video_id": "FAKEhong001", "ma_goi": mg, "tieu_de_cu": "cũ", "tieu_de_moi": "mới",
           "ly_do": "CTR thấp", "anh_du_phong": bia2, "trang_thai": "duyet", "duyet_boi": "chu", "luc": BAY.isoformat()}
    _ghi(cuu_ctr.duong_duyet(goc, K), {"kenh": K, "muc": [muc]})
    # (1) đã duyệt → hàng
    assert cuu_ctr.dong_bo(goc, bay_gio=BAY)["xep"] == 1
    hang = cuu_ctr.doc_hang(goc)
    assert [(v["buoc"], v["tieu_de"], v["tieu_de_cu"]) for v in hang] == [("tieu_de", "mới", "cũ")]
    assert cuu_ctr.doc_duyet(goc, K)[0]["trang_thai"] == "da_xep"
    # (2) máy DOM báo xong → lich_su_sua trong hồ sơ
    hang[0].update(trang_thai="xong", ket_luc="2026-10-02 03:10:00")
    _ghi(os.path.join(goc, cuu_ctr.TEP_HANG), {"viec": hang})
    assert cuu_ctr.dong_bo(goc, bay_gio=BAY + _dt.timedelta(days=1))["ghi_sua"] == 1
    hs = _doc(os.path.join(goc, "CHANNEL", K, "ho-so-video", mg + ".json"))
    ls = hs["lich_su_sua"][-1]
    assert ls["loai"] == "tieu_de" and ls["moi"] == "mới" and ls["doi_boi"] == "giam_doc"
    assert cuu_ctr.doc_duyet(goc, K)[0]["trang_thai"] == "da_sua"
    # (3) bản chụp sau: CTR tệ hơn, đủ hiển thị → quay lui tiêu đề + thử bìa hạng nhì
    hs["so_lieu_moi_nhat"] = {"luc_chup": "2026-10-05 02:30", "impressions": 3800, "ctr": 2.6, "moc_gio_that": 160}
    _ghi(os.path.join(goc, "CHANNEL", K, "ho-so-video", mg + ".json"), hs)
    cuu_ctr.dong_bo(goc, bay_gio=BAY + _dt.timedelta(days=4))
    m = cuu_ctr.doc_duyet(goc, K)[0]
    assert m["ket"] == "quay_lui" and m["trang_thai"] == "cho_quay_lui" and m["ctr_goc"] == 3.0
    buoc = [(v["buoc"], v.get("tieu_de") or os.path.basename(v.get("anh") or "")) for v in cuu_ctr.doc_hang(goc)]
    assert buoc[1:] == [("quay_lui_tieu_de", "cũ"), ("bia", mg + "-bia-2.jpg")]


def test_dong_bo_khong_lam_gi_khi_khong_kenh_bat_studio(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, 'giam_doc: "goi_y"')
    assert cuu_ctr.dong_bo(goc) == {"xep": 0, "ghi_sua": 0, "phan_xu": 0}
    assert not os.path.exists(os.path.join(goc, cuu_ctr.TEP_HANG))


# ═══ MÁY DOM: sua_video_mot ═════════════════════════════════════════════════

class TrangSuaVideoGia:
    """Trang sửa Studio giả: ô tiêu đề, nút Lưu (tắt khi không có thay đổi), nút tải bìa."""

    def __init__(self, video):
        self.video = video          # vid → {"title", "thumb"}
        self.vid = None
        self.dang = None            # tiêu đề đang gõ (chưa lưu)
        self.anh_cho = None
        self.dem_luu = 0
        self.du_phong = {}
        self.bang_chung = []

    def mo(self, url, cho_khoa=None, han=60):
        self.vid = url.split("/video/")[1].split("/")[0] if "/video/" in url else None
        self.dang, self.anh_cho = None, None
        return True

    def bat_json(self, url, chua_url, han=30, toi_da=4):
        self.mo(url)
        v = self.video.get(self.vid)
        if v is None:
            return [{"videos": []}]
        return [{"videos": [{"videoId": self.vid, "title": v["title"], "thumbnailDetails": {
            "thumbnails": [{"url": "https://i.ytimg.com/vi/{0}/default.jpg?sqp={1}".format(self.vid, v["thumb"])}]}}]}]

    def _ban(self):
        return self.dang is not None or self.anh_cho is not None

    def tim(self, khoa, han=10, hien=True, cho_tat=False, trong=None, thu=0):
        v = self.video.get(self.vid)
        if v is None:
            return None
        if khoa in ("tieu_de", "sua_bia_input", "sua_huy_thay_doi"):  # như trang thật: chỉ có ô tệp ẩn
            return {"khoa": khoa}
        if khoa == "sua_luu":
            return {"khoa": khoa, "tat": not self._ban()}
        return None

    def co(self, khoa, **kw):
        return self.tim(khoa) is not None

    def doc_chu(self, x, han=5):
        v = self.video.get(self.vid) or {}
        return self.dang if self.dang is not None else v.get("title", "")

    def go(self, khoa, chu, han_tim=10):
        self.dang = chu
        return chu

    def dat_tep(self, khoa_nut, duong, khoa_input=None, han=8):
        self.anh_cho = duong
        return "file-chooser"

    def bam(self, x, hau_dieu_kien=None, han_hau=10, han_tim=10, cho_tat=False):
        khoa = x["khoa"] if isinstance(x, dict) else x
        v = self.video[self.vid]
        if khoa == "sua_luu":
            self.dem_luu += 1
            if self.dang is not None:
                v["title"] = self.dang
            if self.anh_cho is not None:
                v["thumb"] += 1
            self.dang, self.anh_cho = None, None
        elif khoa == "sua_huy_thay_doi":
            self.dang, self.anh_cho = None, None
        if hau_dieu_kien is not None and not hau_dieu_kien():
            raise cdp_studio.LoiThaoTac(khoa, "hậu điều kiện không đạt")
        return {"khoa": khoa}

    def ghi_bang_chung(self, nhan):
        self.bang_chung.append(nhan)
        return {}

    def dong(self):
        pass


def _may(tmp_path, trang):
    return mdd.MayDangDom("TL3-T7", cdp_studio.doc_bo_chon(), lambda: trang,
                          mdd.SoVideoId(str(tmp_path / "so.json")), lambda *a, **k: True, str(tmp_path / "DONE"),
                          nhat_ky=lambda s: None, bay_gio=lambda: datetime(2026, 10, 2, 3, 5), ngu=lambda s: None,
                          duong_uc=str(tmp_path / "uc.json"), duong_dodang=str(tmp_path / "dodang.json"),
                          thu_muc_chi_so=str(tmp_path / "chi-so"))


def test_sua_video_mot_doi_tieu_de_doc_lai_luu(tmp_path):
    tr = TrangSuaVideoGia({"FAKEsua0001": {"title": "cũ", "thumb": 1}})
    kq = _may(tmp_path, tr).sua_video_mot("TL3-T7/0007", "FAKEsua0001", tieu_de="mới", tieu_de_cu="cũ")
    assert kq["ket"] == "ok" and kq["doc_lai"] == "mới" and tr.video["FAKEsua0001"]["title"] == "mới"
    assert tr.dem_luu == 1 and any(b.startswith("sua-doc-lai-") for b in tr.bang_chung)


def test_sua_video_mot_chu_da_sua_tay_thi_khong_de(tmp_path):
    tr = TrangSuaVideoGia({"FAKEsua0002": {"title": "chủ tự đổi", "thumb": 1}})
    kq = _may(tmp_path, tr).sua_video_mot("TL3-T7/0008", "FAKEsua0002", tieu_de="mới", tieu_de_cu="cũ")
    assert kq["ket"] == "khong-the" and tr.dem_luu == 0 and tr.video["FAKEsua0002"]["title"] == "chủ tự đổi"


def test_sua_video_mot_doi_bia_so_url_anh(tmp_path):
    anh = tmp_path / "bia-2.jpg"
    anh.write_bytes(b"jpg")
    tr = TrangSuaVideoGia({"FAKEsua0003": {"title": "t", "thumb": 1}})
    kq = _may(tmp_path, tr).sua_video_mot("TL3-T7/0009", "FAKEsua0003", anh=str(anh))
    assert kq["ket"] == "ok" and kq["anh_doi"] is True and tr.video["FAKEsua0003"]["thumb"] == 2
    assert _may(tmp_path, TrangSuaVideoGia({})).sua_video_mot("k", "FAKEkhong01", tieu_de="x")["ket"] == "khong-the"


def test_hang_sua_kenh_quay_lui_truoc_tran_moi_dem():
    hang = [{"id": "a:tieu_de", "kenh": "TL3-T7", "video_id": "v1", "tieu_de": "x", "buoc": "tieu_de", "them_luc": "1"},
            {"id": "b:tieu_de", "kenh": "TL3-T7", "video_id": "v2", "tieu_de": "x", "buoc": "tieu_de", "them_luc": "2"},
            {"id": "c:tieu_de", "kenh": "TL3-T7", "video_id": "v3", "tieu_de": "x", "buoc": "tieu_de", "them_luc": "3"},
            {"id": "d:quay_lui_tieu_de", "kenh": "TL3-T7", "video_id": "v4", "tieu_de": "x", "buoc": "quay_lui_tieu_de",
             "them_luc": "4"},
            {"id": "e:tieu_de", "kenh": "TL3-T7", "video_id": "v5", "tieu_de": "x", "trang_thai": "xong"},
            {"id": "f:tieu_de", "kenh": "TL3-T7", "video_id": "v6", "tieu_de": "x", "trang_thai": "loi", "lan_loi": 1,
             "thu_ngay": "2026-10-02"},
            {"id": "g:tieu_de", "kenh": "TL1-T7", "video_id": "v7", "tieu_de": "x"}]
    assert [v["id"] for v in mdd.hang_sua_kenh(hang, "TL3-T7", "2026-10-02", 2)] == [
        "d:quay_lui_tieu_de", "a:tieu_de", "b:tieu_de"]
    assert "f:tieu_de" in [v["id"] for v in mdd.hang_sua_kenh(hang, "TL3-T7", "2026-10-03", 9)]


def test_sua_video_cap_nhat_hang_tmp_va_canh_vm_logs_that(tmp_path):
    that = Path(mdd.THU_MUC_LOG)
    truoc = {p.name: p.stat().st_mtime for p in that.glob("*")} if that.is_dir() else {}
    duong = str(tmp_path / "logs" / "hang-sua.json")
    viec = [{"id": "s-1:tieu_de", "kenh": "TL3-T7", "ma_goi": "TL3-T7-0007", "video_id": "FAKEsua0004",
             "tieu_de": "mới", "tieu_de_cu": "cũ", "buoc": "tieu_de", "trang_thai": "cho"}]
    _ghi(duong, {"viec": viec})
    tr = TrangSuaVideoGia({"FAKEsua0004": {"title": "cũ", "thumb": 1}})
    assert _may(tmp_path, tr).sua_video(viec, duong_hang=duong) == mdd.MA_XONG
    assert mdd.doc_hang_sua(duong)[0]["trang_thai"] == "xong"
    assert _doc(str(tmp_path / "logs" / "sua-cuoi.json"))["ket"][0]["trang_thai"] == "xong"
    sau = {p.name: p.stat().st_mtime for p in that.glob("*")} if that.is_dir() else {}
    assert {n: t for n, t in sau.items() if truoc.get(n) != t} == {}, "bài kiểm chạm vm/logs thật"


def test_cam_bam_rieng_cho_luong_sua_van_chan_nut_phan_hoi():
    bo = cdp_studio.doc_bo_chon()
    cam = bo["cam_bam_sua_video"]
    assert not any("#save" in s for s in cam["chon"]) and "feedback" in " ".join(cam["aria_chua"])
    assert any("#save" in s for s in bo["cam_bam"]["chon"]), "luồng khác vẫn cấm bấm Lưu trang sửa"


# ═══ AGENT: khe giờ vắng, nhường 60' trước phiên ═══════════════════════════

def _nap_agent(tmp_path):
    spec = importlib.util.spec_from_file_location("agent_sua_video", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC = str(tmp_path / "vm")
    (tmp_path / "vm" / "logs").mkdir(parents=True, exist_ok=True)
    return mod


def _luc(h, m):
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, h, m, 0, 0, 0, -1))


class TestAgentSua:
    CAC = ["TL4-T7", "TL1-T7", "TL2-T7", "TL3-T7"]

    def _cau(self, tmp_path, **tt):
        hom = time.strftime("%Y-%m-%d")
        base = {"quet_ngay@{0}@{1}".format(k, hom): {"lan": 1, "xong": True} for k in self.CAC}
        base.update(tt)
        (tmp_path / "vm" / "trang-thai.json").write_text(json.dumps(base), encoding="utf-8")
        return {"thu_muc_du_lieu": str(tmp_path / "vm")}

    def test_nhuong_60_phut_truoc_phien(self, tmp_path):
        ag = _nap_agent(tmp_path)
        hl = {k: {"kenh": k, "cach_dang": "dom"} for k in self.CAC}
        cau = self._cau(tmp_path, **{"phien_muc_tieu@TL1-T7@" + time.strftime("%Y-%m-%d"): "04:00"})
        assert ag.han_sua_video(cau, hl, self.CAC, "TL3-T7", _luc(3, 10))[0] == 0
        con, _ = ag.han_sua_video(cau, hl, self.CAC, "TL3-T7", _luc(2, 45))
        assert con == pytest.approx(15 * 60), "kết thúc trước phiên 04:00 đúng 60 phút"
        assert ag.han_sua_video(cau, hl, self.CAC, "TL3-T7", _luc(1, 30))[0] == 0, "ngoài giờ vắng"

    def test_chay_sua_video_goi_may_dom(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        hl = {k: {"kenh": k, "cach_dang": "dom"} for k in self.CAC}
        cau = self._cau(tmp_path)
        (tmp_path / "vm" / "logs" / "hang-sua.json").write_text(json.dumps({"viec": [
            {"id": "s:tieu_de", "kenh": "TL3-T7", "video_id": "FAKEsua0005", "tieu_de": "mới", "buoc": "tieu_de"}]}),
            encoding="utf-8")
        for ten, f in (("van_ipv4_mo", lambda: False), ("tim_chrome", lambda ch: "C:/x.exe"),
                       ("_chrome_dang_chay", lambda c: True), ("dong_chrome_kenh", lambda ch: None),
                       ("ghi_che_do_mat_cao", lambda ch, q, *a, **k: None),
                       ("giu_khoa_may_chung", lambda viec="", kenh="", uu_tien=1: True),
                       ("nha_khoa_may_chung", lambda: None)):
            monkeypatch.setattr(ag, ten, f)
        goi = []
        assert ag.chay_sua_video(cau, hl, self.CAC, bay_gio=_luc(4, 10),
                                 chay_con=lambda d, k, n, han_giay, co_gi_them=(): goi.append((k, co_gi_them))
                                 or ("xong", 0)) is True
        assert goi[0][0] == "TL3-T7" and "--sua-video" in goi[0][1] and "--trong-phien" in goi[0][1]


# ═══ GIỜ ONLINE + LUẬT BÌA ═════════════════════════════════════════════════

def test_lam_moi_gio_online_chi_khi_co_luot_quet_moi(tmp_path, monkeypatch):
    from core import giam_doc
    from core.chi_so_ytb import giai_ma

    goc = str(tmp_path)
    raw = os.path.join(goc, "CHANNEL", K, "chi-so", "kenh", "kenh-20261001", "raw")
    os.makedirs(raw)
    goi = []
    monkeypatch.setattr(giai_ma, "cap_nhat_gio_online", lambda r, d: goi.append(r) or {"ok": 1})
    assert giam_doc.lam_moi_gio_online(goc) == {K: "ghi"}
    assert giam_doc.lam_moi_gio_online(goc) == {} and len(goi) == 1, "không có lượt quét mới thì không đọc lại"


def test_luat_bia_cam_anh_that_va_nhan_vat_30_phan_tram():
    from core import bia_theo_khuon as btk
    from core import chon_bia

    p = btk.loi_nhac_theo_khuon({"nhan_vat": {"vi_tri": "trai", "co_pct": 15}}, phong_cach="flat", bien_the={})
    assert "NO real people" in p and "30% of the frame height" in p and "about 30% of frame height" in p
    q = btk.loi_nhac_chuan_ngach({"chu": {}, "nhan_vat": {"bieu_cam_ro": True}}, bo_ao={}, bien_the={})
    assert "NO real people" in q and "at least 30% of the frame" in q
    ket = chon_bia._KetQuaCham(so=1, loi_nang=["anh_that"])
    assert chon_bia._kiem_loai(ket, chu_bia_mong_doi="", doi_chieu_chu=False) == "người thật / ảnh chụp"
    assert "anh_that" in chon_bia._LOI_NHAC_GIAM_KHAO and "30% of the frame height" in chon_bia._LOI_NHAC_GIAM_KHAO
