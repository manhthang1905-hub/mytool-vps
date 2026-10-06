"""Mốc ≥ ~24h Studio chỉ về gói Reach (`yta_web/join`) — số TỔNG nằm ở `results[0__TOTALS_SUMS_QUERY_KEY]`
(06/10/2026). Bộ giải mã cũ bỏ qua nó nên 8 video có `tong-quan.json` rỗng ở mọi mốc ≥ 23h.

Phủ: bộ giải mã (`giai_ma.tong_tu_join`), `gom` (dòng cho video chỉ có bản rỗng), `ho_so_video.cap_nhat_chi_so`
(bản rỗng không đè khung, đánh dấu `can_chup_lai`), `tu_hoc` (lùi mốc xấp xỉ, chốt "không đo được"), mục báo cáo.

Fixture là cấu trúc khoá THẬT đã rút gọn + id/tiêu đề GIẢ (kho công khai). Toàn tmp_path, không mạng."""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import time
from types import SimpleNamespace

from core import ho_so_video as hv
from core import tu_hoc
from core.chi_so_ytb import giai_ma, gom

VID = "VID00000001"


# ── gói join rút gọn từ raw thật (khoá giữ nguyên, số giả) ───────────────────

def _cot(loai, kieu, gia_tri, total=None):
    c = {"metric": {"type": loai, "asPercentagesOfTotal": False, "includeTotal": True, "cumulative": False},
         "columnAnomalies": {}, kieu: {"values": [gia_tri]}}
    if total is not None:
        c[kieu]["total"] = total
    return c


def _goi_join(imp, ctr, views, *, loc_nguon=None, vid=VID):
    restricts = [{"dimension": {"type": "VIDEO"}, "inValues": [vid]}]
    if loc_nguon:
        restricts.append({"dimension": {"type": "TRAFFIC_SOURCE_TYPE"}, "inValues": [loc_nguon]})
    return {
        "captured_at": "2026-10-05T20:27:03.491Z",
        "href": "https://studio.youtube.com/video/{0}/analytics/tab-reach_viewers/period-default/explore".format(vid),
        "url": "/youtubei/v1/yta_web/join?alt=json",
        "request": {"nodes": [
            {"key": "0__TOTALS_SUMS_QUERY_KEY", "value": {"query": {"dimensions": [], "restricts": restricts}}}]},
        "response": {"results": [
            {"key": "0__TOTALS_SUMS_QUERY_KEY", "value": {"resultTable": {"metricColumns": [
                _cot("VIDEO_THUMBNAIL_IMPRESSIONS", "counts", imp, imp),
                _cot("VIDEO_THUMBNAIL_IMPRESSIONS_VTR", "percentages", ctr, ctr),
                _cot("EXTERNAL_VIEWS", "counts", views, views),
                _cot("AVERAGE_WATCH_TIME", "milliseconds", 180000, 180000)]}}},
            {"key": "2__TOP_ENTITIES_TABLE_QUERY_KEY", "value": {"resultTable": {
                "dimensionColumns": [{"dimension": {"type": "COUNTRY"}, "strings": {"values": ["JP"]}}],
                "metricColumns": [_cot("EXTERNAL_VIEWS", "counts", 322, 606)]}}}]},
    }


def _ghi_raw(thu_muc, ten, goi):
    os.makedirs(thu_muc, exist_ok=True)
    with io.open(os.path.join(thu_muc, ten), "w", encoding="utf-8") as f:
        json.dump(goi, f)


def _giai(tmp_path, goi_list):
    raw = str(tmp_path / "raw")
    for i, g in enumerate(goi_list):
        _ghi_raw(raw, "2026100{0}-000000_tab-reach_viewers_youtubei-v1-yta_web-join-alt-json_{0}.json".format(i), g)
    return giai_ma.sinh(raw, str(tmp_path / "out"), gio=115)


def test_giai_ma_doc_so_tong_cua_goi_join(tmp_path):
    tq = _giai(tmp_path, [_goi_join(1890, 6.77, 606)])
    assert (tq["impressions"], tq["ctr"], tq["views"]) == (1890, 6.77, 606)
    assert tq["avd_giay"] == 180 and tq["nguon_tong"] == "join" and tq["phien_giai_ma"] == giai_ma.PHIEN_GIAI_MA
    assert tq["video_id"] == VID


def test_giai_ma_bo_tong_da_loc_nguon_va_lay_goi_nhieu_hien_thi_nhat(tmp_path):
    # tổng của trang pool đề xuất bị lọc YT_RELATED (5 ≪ 40 thật) — không được nhận; hai gói thật: lấy lớn hơn
    tq = _giai(tmp_path, [_goi_join(5, 9.0, 2, loc_nguon="YT_RELATED"), _goi_join(40, 8.0, 12), _goi_join(19, 7.0, 6)])
    assert (tq["impressions"], tq["views"]) == (40, 12)
    tq2 = _giai(tmp_path / "x", [_goi_join(5, 9.0, 2, loc_nguon="YT_RELATED")])
    assert "impressions" not in tq2 and "views" not in tq2


def test_giai_ma_toan_so_khong_la_chua_tinh_xong_khong_nhan(tmp_path):
    tq = _giai(tmp_path, [_goi_join(0, 0, 0)])
    assert "impressions" not in tq and "nguon_tong" not in tq


def test_giai_ma_the_key_metric_thang_goi_join(tmp_path):
    raw = str(tmp_path / "raw")
    the = {"href": "https://studio.youtube.com/video/{0}/analytics/tab-overview/period-since_publish".format(VID),
           "response": {"keyMetricCardData": {"keyMetricTabs": [
               {"primaryContent": {"metric": "VIDEO_THUMBNAIL_IMPRESSIONS", "total": 77}},
               {"primaryContent": {"metric": "EXTERNAL_VIEWS", "total": 9}}]}}}
    _ghi_raw(raw, "20261002-000000_tab-overview_youtubei-v1-yta_web-get_cards-alt-json_1.json", the)
    _ghi_raw(raw, "20261002-000001_tab-reach_viewers_youtubei-v1-yta_web-join-alt-json_2.json", _goi_join(1890, 6.77, 606))
    tq = giai_ma.sinh(raw, str(tmp_path / "out"), gio=30)
    assert (tq["impressions"], tq["views"]) == (77, 9)
    assert tq["ctr"] == 6.77 and tq.get("nguon_tong") is None       # CTR thiếu ở thẻ thì bù từ join; số chính từ thẻ


# ── gom: dòng cho video chỉ có bản rỗng; mốc sớm có số thì dòng lấy mốc sớm ──

def _tq(kenh_dir, vid, nhan, **kw):
    d = os.path.join(kenh_dir, vid, nhan)
    os.makedirs(d, exist_ok=True)
    q = dict({"video_id": vid, "gio_sau_dang": int(nhan[:-1]), "tieu_de": "T " + vid, "ngay_dang": "2026-10-01"}, **kw)
    with io.open(os.path.join(d, "tong-quan.json"), "w", encoding="utf-8") as f:
        json.dump(q, f)


def test_gom_van_co_dong_khi_chi_moc_som_co_so_va_khi_toan_ban_rong(tmp_path):
    kd = str(tmp_path / "chi-so")
    _tq(kd, "VID00000001", "19h", impressions=89, ctr=1.12, views=24)
    _tq(kd, "VID00000001", "43h")
    _tq(kd, "VID00000001", "115h")
    _tq(kd, "VID00000002", "15h")
    _tq(kd, "VID00000002", "36h")
    bg = gom.gom(kd, {"tu_khoa_manh": [], "tu_khoa_yeu": [], "loai_tru": []})
    theo = {b["video_id"]: b for b in bg}
    assert set(theo) == {"VID00000001", "VID00000002"}
    assert theo["VID00000001"]["impressions"] == 89          # chỉ bản có số
    assert len([b for b in bg if b["video_id"] == "VID00000001"]) == 1
    assert theo["VID00000002"]["impressions"] is None and theo["VID00000002"]["moc_gio"] == 36   # bản rỗng mới nhất


def test_giai_lai_phien_cu_chi_khi_rong_va_co_goi_join(tmp_path):
    from core.chi_so_ytb import _can_giai_lai_phien_cu as can
    raw = str(tmp_path / "raw")
    _ghi_raw(raw, "x_tab-reach_viewers_youtubei-v1-yta_web-join-alt-json_1.json", {})
    tq = str(tmp_path / "tong-quan.json")

    def ghi(q):
        with io.open(tq, "w", encoding="utf-8") as f:
            json.dump(q, f)
    ghi({"video_id": VID})
    assert can(tq, raw) is True
    ghi({"video_id": VID, "phien_giai_ma": 2})
    assert can(tq, raw) is False
    ghi({"video_id": VID, "impressions": 5})
    assert can(tq, raw) is False


# ── ho_so_video.cap_nhat_chi_so ──────────────────────────────────────────────

def _b(luc, moc, imp, views=None, ctr=None):
    return SimpleNamespace(video_id=VID, tieu_de="Tiêu đề giả", luc_chup=luc, moc_gio=moc, impressions=imp, views=views,
                           ctr=ctr, avd_pct=None, avd_giay=None, thu_muc="", traffic={}, subs=None, watch_hours=None)


def _dung_hs(tmp_path, monkeypatch, ban_ghi):
    g = str(tmp_path)
    hv._luu_ho_so(g, "K", "K-0001", {"tieu_de": "Tiêu đề giả", "video_id": VID, "chi_so": {}})
    monkeypatch.setattr(hv._chi_so, "doc_kenh", lambda kenh, goc=None, **k: ban_ghi)
    return g


def test_ban_chup_rong_khong_de_khung_co_so(tmp_path, monkeypatch):
    bg = [_b("2026-10-03 10:00", 40, 1000, 50, 3.0), _b("2026-10-03 12:00", 42, None)]
    g = _dung_hs(tmp_path, monkeypatch, bg)
    hv.cap_nhat_chi_so(g, "K", bay_gio=_dt.datetime(2026, 10, 3, 13, 0))
    k48 = hv.doc_ho_so(g, "K", "K-0001")["chi_so"]["48h"]
    assert k48["impressions"] == 1000 and not k48.get("can_chup_lai")


def test_khung_chi_co_ban_rong_danh_dau_can_chup_lai_va_con_cua_so(tmp_path, monkeypatch):
    bg = [_b("2026-10-01 20:00", 20, 300, 20, 2.0), _b("2026-10-03 10:00", 40, None)]
    g = _dung_hs(tmp_path, monkeypatch, bg)
    hv.cap_nhat_chi_so(g, "K", bay_gio=_dt.datetime(2026, 10, 3, 11, 0))
    hs = hv.doc_ho_so(g, "K", "K-0001")
    assert hs["chi_so"]["48h"]["can_chup_lai"] is True and hs["chi_so"]["48h"]["impressions"] is None
    assert hs["so_lieu_moi_nhat"]["moc"] == "24h"             # khung rỗng không làm "mới nhất"
    assert hv.moc_can_chup_lai(g, "K", bay_gio=_dt.datetime(2026, 10, 3, 11, 0)) == [("K-0001", "48h")]   # 41h < 60h
    assert hv.moc_can_chup_lai(g, "K", bay_gio=_dt.datetime(2026, 10, 5, 12, 0)) == []                     # 90h: đóng
    # lần sau có số thật → ghi đè, cờ biến mất
    monkeypatch.setattr(hv._chi_so, "doc_kenh",
                        lambda kenh, goc=None, **k: bg + [_b("2026-10-03 15:00", 45, 900, 40, 2.5)])
    hv.cap_nhat_chi_so(g, "K", bay_gio=_dt.datetime(2026, 10, 3, 16, 0))
    k48 = hv.doc_ho_so(g, "K", "K-0001")["chi_so"]["48h"]
    assert k48["impressions"] == 900 and "can_chup_lai" not in k48


def test_khung_rong_cu_tu_ban_loi_duoc_danh_dau(tmp_path, monkeypatch):
    g = _dung_hs(tmp_path, monkeypatch, [_b("2026-10-02 10:00", 20, 10, 1, 1.0)])
    hs = hv.doc_ho_so(g, "K", "K-0001")
    hs["chi_so"] = {"48h": {"impressions": None, "ctr": None, "views": None, "luc_chup": "2026-10-03 10:00", "moc_gio_that": 40}}
    hv._luu_ho_so(g, "K", "K-0001", hs)
    hv.cap_nhat_chi_so(g, "K", bay_gio=_dt.datetime(2026, 10, 3, 11, 0))
    assert hv.doc_ho_so(g, "K", "K-0001")["chi_so"]["48h"]["can_chup_lai"] is True


# ── tu_hoc: lùi mốc xấp xỉ, "không đo được", tách báo cáo ───────────────────

def _kenh(goc, ma):
    os.makedirs(os.path.join(goc, "CHANNEL", ma), exist_ok=True)
    with open(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('nhom: "n1"\n')


def _hs(goc, ma, ma_goi, **kw):
    d = os.path.join(goc, "CHANNEL", ma, "ho-so-video")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, ma_goi + ".json"), "w", encoding="utf-8") as f:
        json.dump(dict({"ma_goi": ma_goi}, **kw), f)


def test_moc_do_duoc_lui_xap_xi_khi_48h_72h_trong():
    hs = {"chi_so": {"24h": {"impressions": 500, "moc_gio_that": 23},
                     "ngay4": {"impressions": 2000, "moc_gio_that": 100},
                     "48h": {"impressions": None, "views": None, "can_chup_lai": True, "moc_gio_that": 40}}}
    m = tu_hoc._moc_do_duoc(hs)  # noqa: SLF001
    assert m["impressions"] == 2000 and m["xap_xi"] is True and m["moc_dung"] == "ngay4"
    assert tu_hoc._moc_do_duoc({"chi_so": {"24h": {"impressions": 5, "moc_gio_that": 10}}}) == {}  # noqa: SLF001 — <22h không dùng
    chuan = {"chi_so": {"48h": {"impressions": 7, "moc_gio_that": 48}, "ngay4": {"impressions": 9, "moc_gio_that": 100}}}
    assert "xap_xi" not in tu_hoc._moc_do_duoc(chuan)  # noqa: SLF001


def test_ket_luan_48h_xap_xi_chi_tin_chieu_an_toan():
    kq = SimpleNamespace(ket_luan=lambda vm, hs, ng: "thang" if hs["chi_so"]["48h"]["impressions"] >= ng else "truot")

    def kl(moc_gio, imp):
        hs = {"chi_so": {"ngayX": {"impressions": imp, "moc_gio_that": moc_gio}}}
        return tu_hoc._ket_luan_48h(kq, None, hs, 1000.0)  # noqa: SLF001
    assert kl(30, 1500) == "thang" and kl(30, 200) == ""      # mốc sớm: chỉ "thắng" là chắc
    assert kl(100, 200) == "truot" and kl(100, 5000) == ""    # mốc muộn: chỉ "trượt" là chắc
    assert kl(50, 1500) == "thang" and kl(50, 200) == "truot"  # 48–60h coi như cùng tuổi


def test_cham_van_chot_khong_do_duoc_sau_7_ngay_va_tin_hieu_tach_doi(tmp_path):
    g = str(tmp_path)
    _kenh(g, "A")
    hom_nay = _dt.date.today()
    cu, moi = (hom_nay - _dt.timedelta(days=9)).isoformat(), (hom_nay - _dt.timedelta(days=5)).isoformat()
    _hs(g, "A", "A-CU", ngay_dang=cu, chi_so={"48h": {"impressions": None, "can_chup_lai": True, "moc_gio_that": 40}})
    _hs(g, "A", "A-MOI", ngay_dang=moi, chi_so={})
    # có số mốc sớm 24h nhưng chưa đủ chắc → "chưa tới mốc", không bị chốt
    _hs(g, "A", "A-SOM", ngay_dang=moi, chi_so={"24h": {"impressions": 10, "moc_gio_that": 23}})
    tu_hoc._luu_van(g, "A", {m: {"ma_goi": m, "nuoc": {"cum": "x"}, "ngay": d}  # noqa: SLF001
                             for m, d in (("A-CU", cu), ("A-MOI", moi), ("A-SOM", moi))})
    r = tu_hoc.cham_van(g, "A")
    van = tu_hoc.doc_van(g, "A")
    assert r["khong_do"] == 1 and van["A-CU"]["khong_do"] and "khong_do" not in van["A-MOI"]
    assert "khong_do" not in van["A-SOM"] and not van["A-SOM"].get("ket48")      # 10 < ngưỡng nhưng mốc 23h: "trượt" chưa chắc
    t = tu_hoc.tin_hieu_thieu(g, "A", time.time())
    assert t["khong_do"] == ["A-CU"] and "A-CU" not in t["thieu_48h"]
    assert t["studio_rong"] == ["A-MOI"] and t["cho_moc"] == ["A-SOM"]
    assert tu_hoc.cham_van(g, "A")["khong_do"] == 0                                # chạy lại: không đếm lại


def test_khong_do_duoc_go_co_khi_so_ve_sau(tmp_path, monkeypatch):
    from core.chien_luoc import ket_qua
    monkeypatch.setattr(ket_qua, "video_kenh", lambda g, k: ({}, 1000.0))
    g = str(tmp_path)
    _kenh(g, "A")
    cu = (_dt.date.today() - _dt.timedelta(days=9)).isoformat()
    _hs(g, "A", "A-CU", ngay_dang=cu, chi_so={})
    tu_hoc._luu_van(g, "A", {"A-CU": {"ma_goi": "A-CU", "nuoc": {"cum": "x"}, "ngay": cu}})  # noqa: SLF001
    tu_hoc.cham_van(g, "A")
    assert tu_hoc.doc_van(g, "A")["A-CU"]["khong_do"]
    # số về muộn ở mốc ~50h (cùng tuổi 48h) → có kết luận, cờ "không đo được" tự gỡ
    _hs(g, "A", "A-CU", ngay_dang=cu, video_id="vidgia", chi_so={"ngay2": {"impressions": 90000, "moc_gio_that": 50}})
    tu_hoc.cham_van(g, "A")
    v = tu_hoc.doc_van(g, "A")["A-CU"]
    assert v["ket48"] == "thang" and "khong_do" not in v


def test_muc_hoc_tach_studio_rong_voi_chua_toi_moc(tmp_path, monkeypatch):
    from core import bao_cao_ngay as bc
    monkeypatch.setattr(bc, "_cac_kenh", lambda goc: ["A"])
    monkeypatch.setattr(tu_hoc, "tin_hieu_thieu", lambda g, k, ts: {
        "van": 5, "thieu_48h": ["1", "2", "3"], "studio_rong": ["1", "2"], "cho_moc": ["3"], "khong_do": ["4"],
        "khong_cum": 0, "van_cu_gio": 1.0})
    ra = "\n".join(bc._muc_hoc(str(tmp_path), _dt.datetime.now()))  # noqa: SLF001
    assert "Studio rỗng" in ra and "A 2" in ra
    assert "chưa tới mốc" in ra and "A 1" in ra
    assert "không đo được" in ra
