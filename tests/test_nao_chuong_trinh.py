"""Chương trình hằng ngày của bộ não (`core/nao_chuong_trinh.py`, 12/10/2026) + phần đi kèm: radar nổ (mã tính, CLI
`uu-tien-nguon --radar`: kiểm bằng mã, ngoài hạn mức ngày, hạn 48 giờ), giờ phiên đợi quét Studio (`nao.cho_quet_xong`),
số cấp kênh trọn đời (`core.chi_so_kenh`) và YPP gắn nhãn trượt/trọn đời (`core.ypp`, báo cáo ngày).

Không mạng; mọi thứ trong `tmp_path`; mã video giả.
"""

from __future__ import annotations

import datetime as dt
import json
import os

import pytest

from core import chi_so_kenh, nao, nao_chuong_trinh as ct, thuoc_thang as tt, ypp

BAY = dt.datetime(2026, 10, 12, 9, 0)
NOW = BAY.timestamp()


class _VM:
    """VideoMinh tối giản (đủ trường `nao_chuong_trinh` đọc)."""

    def __init__(self, ma, tuoi_nay, diem, tieu_de="架空の動画タイトル", cum=("tri-tue",)):
        dang = NOW - tuoi_nay * 3600.0
        self.ma, self.tieu_de, self.cum, self.tuoi_gio = ma, tieu_de, list(cum), tuoi_nay
        self.chuoi = tt.Chuoi(ma=ma, dang=dang, diem=[tt.Diem(tuoi=float(t), hien_thi=float(h), xem=1.0,
                                                              luc=dang + t * 3600.0) for t, h in diem])


def _ds_radar():
    ref = [_VM("FAKEref%04d" % i, 200 + 10 * i, [(24, 100), (72, 100 + 48 * (8 + i))]) for i in range(6)]
    nong = _VM("FAKEhot0001", 50, [(24, 300), (48, 3300)])        # +3.000 trong 24h = 125/giờ ≫ P80 (~12/giờ)
    thuong = _VM("FAKEmid0001", 50, [(24, 100), (48, 340)])       # 10/giờ
    return ref + [nong, thuong]


@pytest.fixture()
def radar_gia(monkeypatch):
    ds = _ds_radar()
    monkeypatch.setattr(ct, "_video_kenh", lambda goc, k, bg: (ds, lambda td: ["tri-tue"]))
    return ds


def test_radar_chi_bat_video_doc_hon_p80_cua_chinh_kenh(radar_gia):
    r = ct.radar_kenh("", "KA", BAY)
    assert [v["ma"] for v in r["video"]] == ["FAKEhot0001"]
    v = r["video"][0]
    assert v["n"] == 6 and v["doc"] == pytest.approx(125.0) and v["tang"] == pytest.approx(3000.0)
    assert ct.la_radar("", "KA", "FAKEhot0001", BAY)[0] is True
    ok, ly = ct.la_radar("", "KA", "FAKEmid0001", BAY)
    assert ok is False and "không nằm trên radar" in ly


def test_radar_it_tham_chieu_thi_khong_xep(monkeypatch):
    ds = _ds_radar()[4:]                                           # còn 2 tham chiếu
    monkeypatch.setattr(ct, "_video_kenh", lambda goc, k, bg: (ds, lambda td: []))
    r = ct.radar_kenh("", "KA", BAY)
    assert r["video"] == [] and "chưa đủ 5 video tham chiếu" in r["ly_do"]


def _goc_nao(tmp_path):
    for ma in ("KA", "KB"):
        d = tmp_path / "CHANNEL" / ma
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text('nhom: "n1"\n', encoding="utf-8")
    return str(tmp_path)


def _chay(goc, *argv, bay_gio=BAY):
    try:
        nao.chay_lenh(nao._parser().parse_args(list(argv)), goc, bay_gio)
        return 0
    except nao.TuChoi as loi:
        return str(loi)


def _ep(goc, link, radar="FAKEhot0001", bay_gio=BAY):
    return _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", link, "--radar", radar, "--ly-do",
                 "RADAR FAKEhot0001 +3.000 hiển thị 24–48h > P80 kênh (n 6)", "--du-doan",
                 "video làm từ nguồn này đạt phân vị ≥ 50 hiển thị @96h so kênh", "--kiem-ngay", "2026-10-20",
                 bay_gio=bay_gio)


def test_cli_radar_kiem_bang_ma_ngoai_han_muc_va_het_han_48h(tmp_path, radar_gia):
    goc = _goc_nao(tmp_path)
    for i in range(3):   # dùng hết 3 hành động/ngày bằng đề cử thường
        assert _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "https://youtu.be/AAAAAAAAAA%d" % i,
                     "--ly-do", "nguồn cùng cụm, view 100k trong 5 ngày", "--du-doan",
                     "video làm từ nguồn này đạt phân vị ≥ 50 hiển thị @96h so kênh", "--kiem-ngay",
                     "2026-10-20") == 0
    assert "hôm nay đã dùng 3/3" in _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "https://youtu.be/BBBBBBBBBBB",
                                          "--ly-do", "nguồn cùng cụm, view 100k", "--du-doan",
                                          "video làm từ nguồn này đạt phân vị ≥ 50", "--kiem-ngay", "2026-10-20")
    assert "không nằm trên radar" in _ep(goc, "https://youtu.be/CCCCCCCCCCC", radar="FAKEmid0001")
    assert _ep(goc, "https://youtu.be/CCCCCCCCCCC") == 0               # radar: ngoài hạn mức ngày
    assert _ep(goc, "https://youtu.be/DDDDDDDDDDD") == 0
    assert "tối đa 2" in _ep(goc, "https://youtu.be/EEEEEEEEEEE")      # ≤ 2 nguồn mỗi video radar
    d = [x for x in nao.doc_hanh_dong(goc) if (x.get("tham_so") or {}).get("radar")]
    assert len(d) == 2 and all(x["ngoai_han_muc"] for x in d)
    assert d[0]["tham_so"]["han_san_xuat"] == (BAY + dt.timedelta(hours=48)).isoformat()
    assert "RADAR FAKEhot0001" in nao.dong_hanh_dong(d[0])
    # một đề cử radar được chọn vào lượt → không hết hạn; đề cử kia quá 48h chưa chọn → đóng, không tính điểm
    nao.dung_xong_de_cu(goc, "KA", chon="https://youtu.be/CCCCCCCCCCC", bay_gio=BAY + dt.timedelta(hours=10))
    nao.don_het_han(goc, bay_gio=BAY + dt.timedelta(hours=49))
    theo = {x["tham_so"]["link"]: x for x in nao.doc_hanh_dong(goc) if (x.get("tham_so") or {}).get("radar")}
    assert theo["https://youtu.be/CCCCCCCCCCC"]["trang_thai"] == "mo"
    het = theo["https://youtu.be/DDDDDDDDDDD"]
    assert het["trang_thai"] == "xong" and het["khong_tinh"] and "48 giờ" in het["ghi_chu_cham"]


# ── giờ phiên: đợi quét Studio xong ─────────────────────────────────────────

def _vm(goc, trang_thai, kenh=("KA", "KB")):
    vm = os.path.join(goc, "vm")
    os.makedirs(vm, exist_ok=True)
    with open(os.path.join(vm, "trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump(trang_thai, tep)
    with open(os.path.join(vm, "cai-dat-tool.json"), "w", encoding="utf-8") as tep:
        json.dump({"kenh": {k: {} for k in kenh}}, tep)


def test_cho_toi_gio_phien_roi_doi_quet_xong(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(nao, "_thu_muc_vm", lambda g: os.path.join(g, "vm"))
    tt_vm = {"quet_ngay@KA@2026-10-11": {"xong": True}, "quet_ngay@KB@2026-10-11": {"xong": True},
             "quet_ngay@KA@2026-10-12": {"xong": True, "lan": 1}, "quet_ngay@KB@2026-10-12": {"xong": False, "lan": 1}}
    _vm(goc, tt_vm)
    assert nao.quet_hom_nay(goc, BAY) == (["KB"], ["KA"])
    dong = {"t": dt.datetime(2026, 10, 12, 4, 10)}
    ghi = []

    def ngu(giay):
        dong["t"] += dt.timedelta(seconds=giay)
        if dong["t"] >= dt.datetime(2026, 10, 12, 7, 0):     # lượt quét KB xong lúc ~07:00
            tt_vm["quet_ngay@KB@2026-10-12"] = {"xong": True, "lan": 1}
            _vm(goc, tt_vm)

    kq = nao.cho_quet_xong(goc, bay_gio_fn=lambda: dong["t"], ngu=ngu, ghi=ghi.append)
    assert kq["chua"] == [] and "xong" in kq["ly_do"]
    assert dong["t"] >= dt.datetime(2026, 10, 12, 7, 0) and any("06:45" in x for x in ghi)
    assert any("còn KB" in x for x in ghi)


def test_qua_han_cho_van_chay_va_lenh_schtasks(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(nao, "_thu_muc_vm", lambda g: os.path.join(g, "vm"))
    _vm(goc, {"quet_ngay@KA@2026-10-11": {"xong": True}, "quet_ngay@KA@2026-10-12": {"xong": False, "lan": 1}},
        kenh=("KA",))
    os.makedirs(os.path.join(goc, "workspace"), exist_ok=True)
    with open(os.path.join(goc, "workspace", "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump({"nao_gio_phien": "07:00", "nao_cho_quet_toi_da": "07:30"}, tep)
    assert nao.gio_phien(goc) == ("07:00", "07:30")
    dong = {"t": dt.datetime(2026, 10, 12, 7, 5)}
    kq = nao.cho_quet_xong(goc, bay_gio_fn=lambda: dong["t"],
                           ngu=lambda g: dong.__setitem__("t", dong["t"] + dt.timedelta(seconds=g)))
    assert kq["chua"] == ["KA"] and "quá 07:30" in kq["ly_do"]
    assert nao.lenh_doi_lich(goc) == 'schtasks /Change /TN "ShopAPI-Nao" /ST 07:00'
    assert nao.gio_phien(str(tmp_path / "khong-co")) == ("06:45", "09:30")


# ── số cấp kênh trọn đời + YPP nhãn trượt/trọn đời ──────────────────────────

def _goi_kenh(goc, k, ngay, sub, views=(), gio_ms=(), traffic=None):
    d = os.path.join(goc, "CHANNEL", k, "chi-so", "kenh", "kenh-" + ngay)
    os.makedirs(os.path.join(d, "raw"), exist_ok=True)
    x0 = int(dt.datetime(2026, 9, 1, 7, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
    tabs = []
    for metric, ys in (("EXTERNAL_VIEWS", views), ("EXTERNAL_WATCH_TIME", gio_ms)):
        if ys:
            tabs.append({"primaryContent": {"metric": metric, "mainSeries": {
                "datums": [{"x": x0 + i * 86400000, "y": y} for i, y in enumerate(ys)]}}})
    cards = [{"latestActivityCardData": {"lifetimeSubsData": {"metricColumns": [{"counts": {"values": [sub]}}]}}},
             {"keyMetricCardData": {"keyMetricTabs": tabs}}]
    with open(os.path.join(d, "raw", ngay + "-020000_tab-overview_get_screen-alt-json_1.json"), "w",
              encoding="utf-8") as tep:
        json.dump({"response": {"cards": cards}}, tep)
    with open(os.path.join(d, "tong-quan.json"), "w", encoding="utf-8") as tep:
        json.dump({"traffic": traffic or {"browse": 80.0, "related": 15.0, "search": 1.0}}, tep)


def test_sub_tron_doi_chuoi_ngay_va_traffic(tmp_path):
    goc = str(tmp_path)
    _goi_kenh(goc, "KA", "20261011", 700, views=[10] * 20 + [100] * 7 + [5], traffic={"related": 92.0})
    _goi_kenh(goc, "KA", "20261012", 713, views=[10] * 20 + [100] * 7 + [7], traffic={"related": 49.0})
    _goi_kenh(goc, "KA", "20261010", 690, traffic={"related": 70.0})
    os.makedirs(os.path.join(goc, "CHANNEL", "KA", "chi-so", "kenh", "22h"))     # thư mục lạc: bỏ
    assert chi_so_kenh.sub_tron_doi(goc, "KA") == {"so": 713, "ngay": "2026-10-12", "nguon": "studio_thoi_gian_thuc"}
    assert chi_so_kenh.chuoi_sub_tron_doi(goc, "KA") == [("2026-10-10", 690), ("2026-10-11", 700),
                                                         ("2026-10-12", 713)]
    assert chi_so_kenh.toc_do_sub(chi_so_kenh.chuoi_sub_tron_doi(goc, "KA")) == pytest.approx(11.5)
    v = chi_so_kenh.view_ngay(goc, "KA")
    assert v["tb7"] == pytest.approx(100.0) and v["xu_huong"] == pytest.approx(10.0)   # ngày cuối (chưa chốt) bỏ
    assert chi_so_kenh.ti_le_traffic(goc, "KA")["de_xuat"] == 70.0                    # trung vị, không bản lẻ
    assert chi_so_kenh.sub_tron_doi(goc, "KHONG")["so"] is None


def test_ypp_dung_sub_tron_doi_va_bao_cao_ngay_khong_noi_giam(tmp_path):
    goc = str(tmp_path)
    d = os.path.join(goc, "CHANNEL", "KA", "chi-so")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh-theo-ngay.csv"), "w", encoding="utf-8") as tep:
        tep.write("Lúc chụp,Lượt xem,Giờ xem,Đăng ký,Lượt hiển thị,Tỷ lệ bấm\n"
                  '"2026-10-10 02:13","1","6864.7","617","",""\n"2026-10-11 02:11","1","6718.9","605","",""\n'
                  '"2026-10-12 02:12","1","6526.9","580","",""\n')
    _goi_kenh(goc, "KA", "20261011", 706, gio_ms=[3.6e6 * 200] * 28)
    _goi_kenh(goc, "KA", "20261012", 713, gio_ms=[3.6e6 * 250] * 28)
    r = ypp.du_bao(goc, "KA", BAY)
    assert r["dang_ky"] == 713 and r["nguon_sub"] == "tron_doi" and r["dang_ky_28"] == 580 and r["truot_giam"]
    assert r["toc_dk"] == pytest.approx(7.0) and r["toc_gio"] == pytest.approx(250.0)
    # giờ xem: chuỗi ngày đã chụp (6.750 = 27 ngày chốt × 250) > tổng 28 ngày trượt (6.526,9) → dùng chuỗi ngày
    assert ypp.nhan_sub(r) == "713 sub trọn đời" and r["nguon_gio"] == "chuoi_ngay" and r["gio"] == pytest.approx(6750.0)
    assert "≤ 365 ngày" in ypp.nhan_gio(r)
    os.makedirs(os.path.join(goc, "vm"), exist_ok=True)
    with open(os.path.join(goc, "vm", "cai-dat-tool.json"), "w", encoding="utf-8") as tep:
        json.dump({"kenh": {"KA": {}}}, tep)
    from core import bao_cao_ngay

    dong = bao_cao_ngay._muc_ypp(goc, BAY)  # noqa: SLF001
    assert "713/1000 sub trọn đời" in dong[0] and "28 ngày trượt" in dong[-1] and "không phải" in dong[-1]


# ── gộp: mỗi phần bọc riêng, không vỡ khi kho rỗng ─────────────────────────

def test_chuong_trinh_kho_rong_khong_vo(tmp_path):
    ds = ct.chuong_trinh(str(tmp_path), ["KA"], BAY, ghi=False)
    chu = "\n".join(ds)
    for phan in ("(a) DANH MỤC KÊNH", "(b) RADAR NỔ", "(c) SĂN KHOẢNG TRỐNG", "(d) BAO BÌ A/B", "(e) GIỮ CHÂN"):
        assert phan in chu
    assert "n < 3" in ds[0]
    assert not os.path.exists(os.path.join(str(tmp_path), ct.TEP_SAN))   # chạy thử: không ghi


def test_san_khoang_trong_tuan_mot_lan(tmp_path, monkeypatch):
    goc = str(tmp_path)
    p = os.path.join(goc, "workspace", "chien-truong")
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "lich-su.jsonl"), "w", encoding="utf-8") as tep:
        for ngay, dich in (("2026-10-05", 2_000_000), ("2026-10-12", 5_000_000)):
            tep.write(json.dumps({"ngay": ngay, "vung": {"vung-a": {"dich": dich, "ta": 0, "thi_phan": 0.0},
                                                         "vung-b": {"dich": 9_000_000, "ta": 50_000,
                                                                    "thi_phan": 0.5}}}) + "\n")
    with open(os.path.join(p, "chu-quyen-vung.json"), "w", encoding="utf-8") as tep:
        json.dump({"vung": {"vung-a": {"chu": "KA", "ly_do": "giả"}}, "kenh_duoc_phat": {"KA": True}}, tep)
    ds = ct.khoang_trong(goc, BAY)
    assert [m["vung"] for m in ds] == ["vung-a"] and ds[0]["da_7"] == 3_000_000 and ds[0]["chu"] == "KA"
    lan1 = ct.dong_khoang_trong(goc, BAY)
    assert "vung-a" in "\n".join(lan1) and os.path.isfile(os.path.join(goc, ct.TEP_SAN))
    lan2 = ct.dong_khoang_trong(goc, BAY + dt.timedelta(days=1))
    assert len(lan2) == 1 and "đã săn" in lan2[0]
