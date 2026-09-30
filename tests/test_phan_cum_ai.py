"""Phân cụm THEO NGHĨA bằng AI (`core/phan_cum_ai.py`) + điểm móc biên tập viên AI
(`core/tu_chay._bien_tap_ai`). Không gọi mạng: AI là hàm giả."""

from __future__ import annotations

import json
import os
import sys
import types

import pytest

from core import cong_thuc_v7 as v7
from core import phan_cum_ai as pca
from core import tu_chay

def _gia_bien_tap(monkeypatch, ns):
    """Thay core.bien_tap_content bằng đồ giả — cả sys.modules LẪN thuộc tính của gói `core`:
    `from . import bien_tap_content` đọc thuộc tính gói trước, nên chỉ vá sys.modules thì bài này
    hỏng khi chạy SAU một tệp test đã nạp module thật (30/09/2026)."""
    import core
    monkeypatch.setitem(sys.modules, "core.bien_tap_content", ns)
    monkeypatch.setattr(core, "bien_tap_content", ns, raising=False)


TD_BAY = "頭のいい人が他人に興味を持たない本当の理由"


@pytest.fixture(autouse=True)
def _don_bo_nho():
    pca._BANG.clear()
    pca._NGUON.clear()
    yield
    pca._BANG.clear()
    pca._NGUON.clear()


def _goc(tmp_path, kenh="K", yaml=""):
    goc = str(tmp_path)
    d = os.path.join(goc, "CHANNEL", kenh)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write("ten: {0}\n{1}".format(kenh, yaml))
    return goc


def test_ai_phan_cum_theo_nghia_thang_tu_khoa_va_nho_lai(tmp_path):
    goc = _goc(tmp_path)
    ch = v7.CAU_HINH_MAC_DINH
    goi = []

    def ai(loi_nhac, mo_hinh="", khoa="", toi_da_token=0):
        goi.append(loi_nhac)
        assert "theo Ý NGHĨA" in loi_nhac and TD_BAY in loi_nhac
        return json.dumps({"1": ["tri-tue", "khong-co-cum-nay"], "2": []})

    n = pca.phan_loai(goc, "K", ch, [(TD_BAY, ""), ("今日の天気", "")], ai)
    assert n == 2 and len(goi) == 1
    assert v7.cum_cua_tieu_de(TD_BAY) == ["tri-tue"], "AI thắng từ khoá; mã lạ bị bỏ"
    assert v7.cum_cua_tieu_de("今日の天気") == []
    # Tiến trình mới: nạp lại từ đĩa, không hỏi lại AI.
    pca._BANG.clear()
    pca._NGUON.clear()
    assert pca.phan_loai(goc, "K", ch, [(TD_BAY, "")], ai) == 0 and len(goi) == 1
    assert pca.tra_cum(TD_BAY, ch) == ["tri-tue"]


def test_ai_loi_thi_lui_ve_tu_khoa(tmp_path):
    goc = _goc(tmp_path)

    def hong(*a, **k):
        raise RuntimeError("máy chủ bận")

    assert pca.phan_loai(goc, "K", v7.CAU_HINH_MAC_DINH, [("物を持たない人の特徴", "")], hong) == 0
    assert "vat-chat" in v7.cum_cua_tieu_de("物を持たない人の特徴"), "chưa phân → từ khoá"


def test_doi_bo_cum_thi_khong_doc_nham_nhan_cu(tmp_path):
    goc = _goc(tmp_path)
    ch = v7.CAU_HINH_MAC_DINH
    pca.phan_loai(goc, "K", ch, [(TD_BAY, "")], lambda *a, **k: '{"1": ["tri-tue"]}')
    ch2 = dict(ch, cum=dict(ch["cum"], moi={"ten": "cụm mới", "tu": ["x"]}))
    assert pca.khoa_bo_cum(ch2) != pca.khoa_bo_cum(ch)
    assert pca.tra_cum(TD_BAY, ch2) is None


# ── điểm móc biên tập viên AI ────────────────────────────────────────────────

def _ds():
    return [{"ma": "aaaaaaaaaa{0}".format(i), "tieu_de": "t{0}".format(i), "diem": 90 - i,
             "link": "https://www.youtube.com/watch?v=aaaaaaaaaa{0}".format(i), "ly_do": []}
            for i in range(3)]


def test_bien_tap_ai_xep_lai_va_ghi_ly_do(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    nhan = {}

    def chon(goc_, kenh_, top, goi_chat):
        nhan["top"] = top
        return {"thu_tu": [{"ma": "aaaaaaaaaa2", "ly_do_bien_tap": "hợp tệp hơn"}, "aaaaaaaaaa0"],
                "ly_do": "chung"}

    _gia_bien_tap(monkeypatch, types.SimpleNamespace(chon=chon))
    ds = tu_chay._bien_tap_ai(goc, "K", _ds(), lambda *a, **k: "", False, lambda m: None)
    assert [d["ma"] for d in ds] == ["aaaaaaaaaa2", "aaaaaaaaaa0", "aaaaaaaaaa1"]
    assert ds[0]["bien_tap"] == {"hang_cong_thuc": 3, "ly_do": "hợp tệp hơn"}
    assert any("Biên tập AI" in x for x in ds[0]["ly_do"])
    for khoa in ("tieu_de", "link", "cong_thuc", "tep", "tuoi_gio", "vph", "dot_bien", "cum", "diem_cong_thuc"):
        assert khoa in nhan["top"][0]


def test_bien_tap_ai_hong_hoac_tat_thi_giu_thu_tu(tmp_path, monkeypatch):
    goc = _goc(tmp_path)

    def hong(*a, **k):
        raise ValueError("x")

    _gia_bien_tap(monkeypatch, types.SimpleNamespace(chon=hong))
    ds = tu_chay._bien_tap_ai(goc, "K", _ds(), lambda *a, **k: "", False, lambda m: None)
    assert [d["ma"] for d in ds] == [d["ma"] for d in _ds()]
    goc2 = _goc(tmp_path / "tat", "K", "bien_tap_ai: false\n")
    goi = []
    _gia_bien_tap(monkeypatch,
                        types.SimpleNamespace(chon=lambda *a: goi.append(1) or []))
    tu_chay._bien_tap_ai(goc2, "K", _ds(), lambda *a, **k: "", False, lambda m: None)
    assert not goi
    # Không có ví (goi_chat None) → không gọi.
    tu_chay._bien_tap_ai(goc, "K", _ds(), None, False, lambda m: None)
    assert not goi
