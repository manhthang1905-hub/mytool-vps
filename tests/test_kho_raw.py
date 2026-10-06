"""`core/chi_so_ytb/kho_raw.py` — đọc raw `.json`/`.json.gz` như nhau + nén gói cũ nguyên tử.

Chỉ `tmp_path`, mã video giả (`VID00000001`), không đụng dữ liệu thật."""

from __future__ import annotations

import gzip
import json
import os
import time

import pytest

from core import cong_thuc_v7, don_dia
from core.chi_so_ytb import giai_ma, gom, kho_raw

KENH = "KX"
CU = time.time() - 30 * 86400        # mtime gói "cũ" (30 ngày)
NAY = time.time() - 3600             # gói mới về 1 giờ trước


def _goi(vid, i, **them):
    g = {"captured_at": "2026-09-0{0}T10:00:00.000Z".format(1 + i % 8),
         "href": "https://studio.youtube.com/video/{0}/analytics/tab-reach_viewers/"
                 "?dimension=TRAFFIC_SOURCE_DETAIL&ddr_value=YT_RELATED".format(vid),
         "response": {"cards": [{"keyMetricCardData": {"keyMetricTabs": [{"primaryContent": {
             "metric": "EXTERNAL_VIEWS", "total": 100 + i}}]}}],
             "chu": "khối lặp " * 200}}
    g.update(them)
    return g


def _ghi(p, du, mtime):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(du, f, ensure_ascii=False)
    os.utime(p, (mtime, mtime))
    return p


def _cay(goc):
    """Hai mốc của VID00000001: mốc 6h cũ (sẽ nén), mốc 30h mới (giữ nguyên)."""
    cs = os.path.join(str(goc), "CHANNEL", KENH, "chi-so")
    ra = []
    for moc, mt in (("6h", CU), ("30h", NAY)):
        raw = os.path.join(cs, "VID00000001", moc, "raw")
        for i, ten in enumerate(("20260901-100000_tab-overview_youtubei-v1-yta_web-get_cards-alt-json_1.json",
                                 "20260901-100001_tab-reach_youtubei-v1-yta_web-join-alt-json_2.json")):
            ra.append(_ghi(os.path.join(raw, ten), _goi("VID00000001", i), mt))
    return cs, ra


def test_mo_doc_va_liet_ke_tron_json_gz(tmp_path):
    raw = tmp_path / "raw"
    a = _ghi(str(raw / "a_yta_web.json"), {"x": 1}, NAY)
    b = _ghi(str(raw / "b_yta_web.json"), {"x": 2}, CU)
    assert kho_raw.nen_mot(b) >= 0 and not os.path.exists(b) and os.path.exists(b + ".gz")
    (raw / "c.txt").write_text("khác mẫu", encoding="utf-8")
    (raw / "d_yta_web.json.gz.tam").write_bytes(b"do dang")
    assert kho_raw.liet_ke(str(raw), "*.json") == [a, b + ".gz"]
    assert [kho_raw.doc_json(p) for p in kho_raw.liet_ke(str(raw), "*.json")] == [{"x": 1}, {"x": 2}]
    assert kho_raw.doc_json(b) == {"x": 2}               # tên gốc → tự mở bản .gz
    assert kho_raw.ten_goc(b + ".gz") == b
    with kho_raw.mo_doc(b + ".gz") as f:
        assert f.read(4) == '{"x"'


def test_ca_hai_ban_thi_lay_ban_goc(tmp_path):
    p = _ghi(str(tmp_path / "raw" / "a.json"), {"moi": True}, NAY)
    with gzip.open(p + ".gz", "wt", encoding="utf-8") as f:
        json.dump({"moi": False}, f)
    assert kho_raw.liet_ke(str(tmp_path / "raw")) == [p]


def test_nen_cu_chi_nen_goi_cu_giu_mtime_va_noi_dung(tmp_path):
    cs, tep = _cay(tmp_path)
    truoc = {p: (kho_raw.doc_json(p), os.stat(p).st_mtime_ns) for p in tep}
    thu = kho_raw.nen_cu(str(tmp_path), thu=True)
    assert thu["so_tep"] == 2 and all(os.path.exists(p) for p in tep)     # thử: không ghi gì
    kq = kho_raw.nen_cu(str(tmp_path))
    assert kq["so_tep"] == 2 and kq["bytes_sau"] < kq["bytes_truoc"]
    assert kq["bytes_sau"] == thu["bytes_sau"] and set(kq["theo_kenh"]) == {KENH}
    for p, (du, mt) in truoc.items():
        cu = "{0}6h{0}".format(os.sep) in p
        that = p + ".gz" if cu else p
        assert os.path.exists(that) and os.path.exists(p) is not cu
        assert kho_raw.doc_json(that) == du
        assert os.stat(that).st_mtime_ns == mt                           # luc_chup / giải lại dựa mtime
    assert kho_raw.nen_cu(str(tmp_path))["so_tep"] == 0                 # lượt sau: không còn gì


def test_nen_hong_giua_chung_khong_mat_goc(tmp_path, monkeypatch):
    p = _ghi(str(tmp_path / "raw" / "a.json"), {"x": 1}, CU)
    that = os.replace

    def hong(a, b):
        raise PermissionError("bị giữ")
    monkeypatch.setattr(kho_raw.os, "replace", hong)
    assert kho_raw.nen_mot(p) == 0
    assert os.path.exists(p) and os.listdir(str(tmp_path / "raw")) == ["a.json"]   # không rớt .tam
    monkeypatch.setattr(kho_raw.os, "replace", that)
    # đọc lại không khớp → bỏ, giữ gốc
    goc_mo = gzip.open
    monkeypatch.setattr(kho_raw.gzip, "open", lambda d, m="rb", **k: (
        goc_mo(d, m, **k) if "w" in m else __import__("io").BytesIO(b"sai")))
    assert kho_raw.nen_mot(p) == 0 and os.listdir(str(tmp_path / "raw")) == ["a.json"]


def test_xoa_goc_bi_chan_thi_con_ca_hai_luot_sau_xong(tmp_path, monkeypatch):
    p = _ghi(str(tmp_path / "raw" / "a.json"), {"x": 1}, CU)
    xoa = os.remove
    monkeypatch.setattr(kho_raw.os, "remove", lambda d: (_ for _ in ()).throw(PermissionError(d)))
    assert kho_raw.nen_mot(p) == 0
    assert kho_raw.liet_ke(str(tmp_path / "raw")) == [p] and os.path.exists(p + ".gz")
    monkeypatch.setattr(kho_raw.os, "remove", xoa)
    assert kho_raw.nen_mot(p) > 0 or not os.path.exists(p)
    assert os.listdir(str(tmp_path / "raw")) == ["a.json.gz"]


def test_nguoi_doc_ra_y_het_sau_khi_nen(tmp_path, capsys):
    cs, _tep = _cay(tmp_path)
    moc = os.path.join(cs, "VID00000001", "6h")
    with open(os.path.join(moc, "_thong-tin.json"), "w", encoding="utf-8") as f:
        json.dump({"ngay_dang": "2026-08-31T10:00:00.000Z"}, f)
    raw = os.path.join(moc, "raw")
    with open(os.path.join(raw, "x.json"), "w", encoding="utf-8") as f:   # tên không có yta_web
        f.write("{}")
    os.utime(os.path.join(raw, "x.json"), (CU, CU))

    def chup():
        out = os.path.join(str(tmp_path), "ra")
        giai_ma.sinh(raw, out)
        with open(os.path.join(out, "tong-quan.json"), encoding="utf-8") as f:
            tq = f.read()
        return (tq, gom.luc_chup(moc), gom.tuoi_that_gio(moc), giai_ma.doc_gio_online(raw),
                [os.path.basename(kho_raw.ten_goc(p)) for p in cong_thuc_v7._raw_join(moc)],
                [cong_thuc_v7._href_join(p) for p in cong_thuc_v7._raw_join(moc)])
    truoc = chup()
    assert kho_raw.nen_cu(str(tmp_path))["so_tep"] == 3
    assert not [t for t in os.listdir(raw) if not t.endswith(".gz")]
    assert chup() == truoc
    capsys.readouterr()


def test_don_dia_thu_bao_raw_that_nen(tmp_path):
    _cay(tmp_path)
    kq = don_dia.chay(str(tmp_path), thu=True, danh_sach_kenh=[], con_trong_gb_fn=lambda _g: 50.0)
    assert kq["raw"]["so_tep"] == 2 and "2 raw sẽ nén" in don_dia.tom_tat(kq)
    kq = don_dia.chay(str(tmp_path), thu=False, danh_sach_kenh=[], con_trong_gb_fn=lambda _g: 50.0)
    assert kq["raw"]["so_tep"] == 2 and "2 raw đã nén" in don_dia.tom_tat(kq)
    assert don_dia.chay(str(tmp_path), thu=False, danh_sach_kenh=[],
                        con_trong_gb_fn=lambda _g: 50.0)["raw"]["so_tep"] == 0


@pytest.mark.parametrize("ten", ["a.json.gz", "a.json.gz.tam"])
def test_nen_mot_bo_qua_tep_da_nen(tmp_path, ten):
    p = tmp_path / ten
    p.write_bytes(b"x")
    assert kho_raw.nen_mot(str(p)) == 0 and p.read_bytes() == b"x"
