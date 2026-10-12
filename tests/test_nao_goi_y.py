"""Tests `core/nao_goi_y.py` — gợi ý bắt buộc cho bộ não (video thắng lớn + nguồn nhân bản, bài học bị bác bỏ).
Không mạng; dữ liệu giả trong `tmp_path`; nhãn thước chung (`core.thuoc_thang`) / cụm thay bằng hàm giả (không
dựng thư mục chi-so thật). 12/10/2026: "thắng" = nhãn thước chung (hoặc đang nóng), không còn ngưỡng 48h."""

import csv
import datetime as dt
import json
import os

import pytest

from core import nao, nao_goi_y

BAY_GIO = dt.datetime(2026, 10, 6, 4, 10)


def _k(nhan, pv, gia_tri=None, tuoi=None, nong=False, som=None):
    return {"nhan": nhan, "phan_vi": pv, "gia_tri": gia_tri, "tuoi": tuoi, "nong": nong, "som_phan_vi": som}


KET = {"WIN00000001": _k("thang", 92.0, 8497.0, 110.0),
       "LOSE0000001": _k("truot", 10.0, 300.0, 120.0),
       "OLD00000001": _k("thang", 99.0, 9000.0, 130.0),
       "HOT00000001": _k("chua_du", 70.0, nong=True, som=95.0),      # chưa phán, đang nóng → vẫn nhân bản
       "MID00000001": _k("chua_du", 60.0, som=60.0)}                 # chưa phán, không nóng → bỏ

CUM_THEO_CHU = {"年金": "vat-chat", "IQ": "tri-tue"}


def _cum_cua(td):
    return [ma for tu, ma in CUM_THEO_CHU.items() if tu in td]


@pytest.fixture(autouse=True)
def _ngưỡng_giả(monkeypatch):
    monkeypatch.setattr(nao_goi_y, "_ket_kenh", lambda goc, kenh, bg: (KET, _cum_cua, {}))


def _viet_csv(duong, cot, hang):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cot)
        w.writerows(hang)


def _goc(tmp_path, tom_tat, content=(), bai_hoc=()):
    goc = tmp_path
    k = goc / "CHANNEL" / "KA"
    k.mkdir(parents=True)
    (k / "kenh.yaml").write_text("ten: KA\n", encoding="utf-8")
    _viet_csv(str(k / "chi-so" / "bang-tom-tat.csv"),
              ["Tiêu đề", "Mã video", "Ngày đăng", "Dài", "Mốc mới nhất", "Lượt hiển thị", "Tỷ lệ bấm", "Lượt xem"],
              [[t, m, d, "10:00", "35h", hi, "9.47%", "3870"] for (t, m, d, hi) in tom_tat])
    _viet_csv(str(k / "nghien-cuu" / "content.csv"),
              ["Kênh", "Tiêu đề video", "Link video", "Ngày đăng", "View", "Tăng/ngày", "Đã làm"],
              [[kn, t, "https://www.youtube.com/watch?v=" + m, d, v, tg, da] for (kn, t, m, d, v, tg, da) in content])
    if bai_hoc:
        (k / "giam-doc").mkdir()
        with open(str(k / "giam-doc" / "bai-hoc.jsonl"), "w", encoding="utf-8") as f:
            for b in bai_hoc:
                f.write(json.dumps(b, ensure_ascii=False) + "\n")
    return str(goc)


def _bai(truc, gt, huong, cau, video_id="vidCu000001", cum=""):
    return {"truc": truc, "gia_tri": gt, "huong": huong, "cum": cum, "cau": cau, "video_id": video_id,
            "khoa": "{0}|{1}|{2}|{3}".format(truc, gt, huong, cum), "moc": "48h", "bong": False,
            "luc": "2026-10-01T10:00:00"}


TOM_TAT = [("年金テスト用の架空タイトル", "WIN00000001", "2026-10-03", "8497"),
           ("【雑学】別の動画 IQ", "LOSE0000001", "2026-10-03", "300"),
           ("年金の昔の動画", "OLD00000001", "2026-08-01", "9000")]
CONTENT = [
    ("kenhA", "年金で暮らす60代の話", "SRC00000001", "2026-09-20", "11000", "193", ""),
    ("kenhA", "年金月8万円の生活術", "SRC00000002", "2026-09-30", "5500", "4856", ""),
    ("kenhB", "IQが高い人の特徴", "OTHER000001", "2026-09-30", "90000", "9000", ""),          # khác cụm
    ("kenhC", "年金の話 すでに作った", "DONE0000001", "2026-09-30", "50000", "5000", "0003"),  # cột Đã làm
    ("kenhC", "年金の話 của chính mình", "WIN00000001", "2026-10-03", "50000", "5000", ""),     # video của mình
    ("kenhC", "年金の話 quá cũ", "OLDSRC00001", "2026-01-01", "50000", "5000", ""),
]


def test_video_thang_lon_loc_ngay_va_nguong(tmp_path):
    goc = _goc(tmp_path, TOM_TAT, CONTENT)
    vs = nao_goi_y.video_thang_lon(goc, "KA", BAY_GIO)
    assert [v["video_id"] for v in vs] == ["WIN00000001"]     # LOSE trượt, OLD quá 10 ngày
    v = vs[0]
    assert v["nhan"] == "thang" and v["phan_vi"] == 92.0 and v["ti_so"] == pytest.approx(0.92)
    assert v["cum"] == ["vat-chat"] and v["hien_thi"] == 8497.0 and v["moc"] == "110h"


def test_video_dang_nong_chua_phan_van_duoc_nhan_ban(tmp_path):
    tt = TOM_TAT + [("年金の新しい動画", "HOT00000001", "2026-10-05", "3000"),
                    ("年金の普通の動画", "MID00000001", "2026-10-05", "900")]
    vs = nao_goi_y.video_thang_lon(_goc(tmp_path, tt, CONTENT), "KA", BAY_GIO)
    assert [(v["video_id"], v["nhan"]) for v in vs] == [("WIN00000001", "thang"), ("HOT00000001", "nong")]
    assert vs[1]["phan_vi"] == 95.0 and vs[1]["hien_thi"] == 3000.0   # số mới nhất của bảng tóm tắt
    dong = nao_goi_y.dong_bat_buoc(_goc(tmp_path / "b", tt, CONTENT), ["KA"], BAY_GIO)
    assert any("ĐANG NÓNG" in d and "HOT00000001" in d for d in dong)
    assert any("[THẮNG" in d and "WIN00000001" in d and "phân vị 92" in d for d in dong)


def test_nguon_nhan_ban_cung_cum_chua_lam_xep_theo_tang_ngay(tmp_path):
    goc = _goc(tmp_path, TOM_TAT, CONTENT)
    v = nao_goi_y.video_thang_lon(goc, "KA", BAY_GIO)[0]
    ma = [u["ma"] for u in v["nguon"]]
    assert ma == ["SRC00000002", "SRC00000001"]               # tăng/ngày cao trước; không có IQ/Đã làm/video mình/quá cũ
    # lệnh gợi ý chạy được qua đúng parser CLI, kiem-ngay hợp lệ (sau hôm nay, ≤ 30 ngày)
    ns = nao._parser().parse_args(_tach(v["nguon"][0]["lenh"]))
    assert ns.lenh == "uu-tien-nguon" and ns.kenh == "KA" and ns.link.endswith("SRC00000002")
    han = dt.date.fromisoformat(ns.kiem_ngay)
    assert BAY_GIO.date() < han <= BAY_GIO.date() + dt.timedelta(days=30)
    assert len(ns.ly_do) >= 10 and len(ns.du_doan) >= 10


def _tach(lenh):
    import shlex

    return shlex.split(lenh)[3:]


def test_lenh_goi_y_duoc_nao_chap_nhan(tmp_path):
    goc = _goc(tmp_path, TOM_TAT, CONTENT)
    v = nao_goi_y.video_thang_lon(goc, "KA", BAY_GIO)[0]
    ns = nao._parser().parse_args(_tach(v["nguon"][0]["lenh"]))
    hd = nao.chay_lenh(ns, goc, BAY_GIO)
    assert "uu-tien-nguon" in hd
    # đã đề cử video thắng này → lần sau không gợi ý lại (ly_do nhắc video_id) và nguồn đã đề cử bị loại
    vs = nao_goi_y.video_thang_lon(goc, "KA", BAY_GIO)
    assert vs[0]["da_xu_ly"] and vs[0]["nguon"] == []
    assert "không có" in nao_goi_y.dong_bat_buoc(goc, ["KA"], BAY_GIO)[0]


def test_bai_hoc_bi_bac_bo_va_xac_nhan(tmp_path):
    tt = [("【雑学】年金の人気動画", "WIN00000001", "2026-10-03", "8497")]
    bh = [_bai("tieu_de", "nhan_ngach", "-", "Tránh dùng nhãn 【雑学】 làm CTR giảm còn 1.72%"),
          _bai("cum", "vat-chat", "+", "Cụm vat-chat đạt hiển thị 8000", video_id="vidCu000002"),
          _bai("hook", "truc_tiep", "-", "Hook 30s sụt giữ chân 50%", video_id="vidCu000003"),   # trục không nhận ra → bỏ
          _bai("cum", "tri-tue", "-", "Cụm tri-tue nín hiển thị 40", video_id="vidCu000004")]   # video thắng không thuộc cụm
    goc = _goc(tmp_path, tt, bai_hoc=bh)
    ra = nao_goi_y.bai_hoc_bi_bac_bo(goc, "KA", BAY_GIO)
    theo = {b["loai"]: b for b in ra}
    assert sorted(theo) == ["cong", "tru"] and len(ra) == 2
    assert "【雑学】" in theo["tru"]["dac_diem"] and "vat-chat" in theo["cong"]["dac_diem"]
    ns = nao._parser().parse_args(_tach(theo["tru"]["lenh"]))
    assert ns.lenh == "bai-hoc" and ns.thao_tac == "tru" and ns.noi_dung == theo["tru"]["id"] and "WIN00000001" in ns.ly_do
    # chạy thật lệnh tru qua CLI → lần sau không gợi ý lại bài này
    nao.chay_lenh(ns, goc, BAY_GIO)
    sau = nao_goi_y.bai_hoc_bi_bac_bo(goc, "KA", BAY_GIO)
    assert [b["loai"] for b in sau] == ["cong"]


def test_bai_hoc_khong_goi_y_khi_video_khong_thang(tmp_path):
    tt = [("【雑学】年金の動画", "LOSE0000001", "2026-10-03", "300")]
    goc = _goc(tmp_path, tt, bai_hoc=[_bai("tieu_de", "nhan_ngach", "-", "Tránh nhãn 【雑学】 CTR 1.72%")])
    assert nao_goi_y.bai_hoc_bi_bac_bo(goc, "KA", BAY_GIO) == []


def test_xem_co_muc_bat_buoc_o_dau_va_khong_vo(tmp_path):
    goc = _goc(tmp_path, TOM_TAT, CONTENT)
    bc = nao.bao_cao(goc, BAY_GIO)
    assert "VIỆC BẮT BUỘC HÔM NAY — CHƯƠNG TRÌNH" in bc
    assert bc.index("VIỆC BẮT BUỘC HÔM NAY") < bc.index("== KÊNH ==")
    assert "BÁO CÁO CHO BỘ NÃO" in bc.splitlines()[0]
    # 12/10/2026: chương trình 5 việc (mã tính, não quyết) thay lệnh in sẵn; không còn lệnh bài học bằng MỘT video
    for phan in ("(a) DANH MỤC KÊNH", "(b) RADAR NỔ", "(c) SĂN KHOẢNG TRỐNG", "(d) BAO BÌ A/B", "(e) GIỮ CHÂN"):
        assert phan in bc, phan
    assert "bai-hoc --kenh" not in bc.split("== KÊNH ==")[0]


def test_hong_thi_im_lang(tmp_path, monkeypatch):
    goc = _goc(tmp_path, TOM_TAT, CONTENT)
    monkeypatch.setattr(nao_goi_y, "_ket_kenh", lambda *a: (_ for _ in ()).throw(RuntimeError("hỏng")))
    assert nao_goi_y.video_thang_lon(goc, "KA", BAY_GIO) == []
    assert nao_goi_y.bai_hoc_bi_bac_bo(goc, "KA", BAY_GIO) == []
