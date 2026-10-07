"""Nhãn cụm THEO NGHĨA cho vòng tự học (`core/cum_y_nghia.py`, 07/10/2026) — đường lùi khi bộ cụm V7 trả [].

Dữ liệu giả hoàn toàn (tiêu đề bịa, mã gói bịa); `goi_chat_that` luôn bị thay bằng đồ giả — không gọi AI thật.
"""

import datetime as _dt
import json
import os
import re

import pytest

from core import cong_thuc_v7 as v7
from core import cum_y_nghia as cyn
from core import tu_hoc
from core.giam_doc import quan_ly


def _kenh(goc, ma="A"):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('nhom: "n-gia"\n')
    with open(os.path.join(goc, "config.json"), "w", encoding="utf-8") as f:   # gốc "thật" cho `goi_vi`
        f.write("{}")


def _ho_so(goc, ma, ma_goi, tieu_de):
    d = os.path.join(goc, "CHANNEL", ma, "ho-so-video")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, ma_goi + ".json"), "w", encoding="utf-8") as f:
        json.dump({"ma_goi": ma_goi, "cong_thuc": "vph", "tieu_de": tieu_de, "thoi_luong_giay": 900}, f,
                  ensure_ascii=False)


def _van_thieu_cum(goc, ma, ma_goi):
    tu_hoc.ghi_van(goc, ma, ma_goi, {"cong_thuc": "vph"}, {})


def _cum(goc, ma="A"):
    return v7.nap_cau_hinh(goc, ma, ghi_neu_thieu=False)[0]["cum"]


def _tieu_de_tu_khoa(goc, ma="A"):
    """Tiêu đề giả chứa đúng một chữ khoá của bộ cụm mặc định → bộ cụm V7 nhận được."""
    for ma_cum, c in _cum(goc, ma).items():
        for t in c.get("tu") or []:
            td = "bài thử {0} số một".format(t)
            if v7.cum_cua_tieu_de(td, v7.nap_cau_hinh(goc, ma, ghi_neu_thieu=False)[0]):
                return td
    raise AssertionError("bộ cụm mặc định không có chữ khoá")


TD_LA = "tiêu đề giả không chữ khoá nào zq{0}"


class _Goi:
    """Đồ giả hàm gọi AI: trả `tra(so_thu_tu)` cho mọi video trong đề bài."""

    def __init__(self, tra):
        self.tra, self.lan = tra, []

    def __call__(self, de_bai, mo_hinh="", khoa="", toi_da_token=0):
        self.lan.append(de_bai)
        so = re.findall(r"(?m)^(\d+)\. ", de_bai.split("VIDEO:", 1)[1])
        return json.dumps({s: self.tra(int(s)) for s in so})


def _vi(monkeypatch, goi):
    """Thay `goi_chat_that` (van ví): `goi=None` = ví đang chặn."""
    dem = {"n": 0}

    def gia(goc, ghi=None):
        dem["n"] += 1
        return goi

    monkeypatch.setattr(quan_ly, "goi_chat_that", gia)
    return dem


def test_tu_khoa_trung_thi_khong_goi_ai(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    td = _tieu_de_tu_khoa(g)
    _ho_so(g, "A", "A-1", td)
    _van_thieu_cum(g, "A", "A-1")
    goi = _Goi(lambda i: "khac")
    dem = _vi(monkeypatch, goi)
    r = tu_hoc.cham_van(g, "A", dung_ai=True)
    nuoc = tu_hoc.doc_van(g, "A")["A-1"]["nuoc"]
    assert nuoc["cum"] == v7.cum_cua_tieu_de(td, v7.nap_cau_hinh(g, "A", ghi_neu_thieu=False)[0])[0]
    assert nuoc["cum_nguon"] == "tu_khoa" and r["cum_bu"] == 1
    assert goi.lan == [] and dem["n"] == 0


def test_tu_khoa_truot_thi_llm_gan_va_nho(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    ma_cum = sorted(_cum(g))[0]
    _ho_so(g, "A", "A-1", TD_LA.format(1))
    _van_thieu_cum(g, "A", "A-1")
    goi = _Goi(lambda i: ma_cum)
    _vi(monkeypatch, goi)
    tu_hoc.cham_van(g, "A", dung_ai=True)
    nuoc = tu_hoc.doc_van(g, "A")["A-1"]["nuoc"]
    assert nuoc["cum"] == ma_cum and nuoc["cum_nguon"] == "y_nghia"
    assert len(goi.lan) == 1 and ma_cum in goi.lan[0] and TD_LA.format(1) in goi.lan[0]
    assert os.path.isfile(cyn.duong(g, "A"))
    # Lần hai: tiêu đề đã nhớ → không hỏi lại.
    assert cyn.phan_loai(g, "A", [(TD_LA.format(1), "")], goi) == 0
    assert len(goi.lan) == 1
    assert cyn.BoNho(g, "A").tra(TD_LA.format(1)) == ma_cum


def test_khac_la_nhan_hop_le(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    _ho_so(g, "A", "A-1", TD_LA.format(2))
    _van_thieu_cum(g, "A", "A-1")
    _vi(monkeypatch, _Goi(lambda i: "KHAC"))
    tu_hoc.cham_van(g, "A", dung_ai=True)
    assert tu_hoc.doc_van(g, "A")["A-1"]["nuoc"]["cum"] == cyn.CUM_KHAC


def test_ma_la_thi_khong_nhan(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    _ho_so(g, "A", "A-1", TD_LA.format(3))
    _van_thieu_cum(g, "A", "A-1")
    goi = _Goi(lambda i: "cum-bia-ra")
    _vi(monkeypatch, goi)
    r = tu_hoc.cham_van(g, "A", dung_ai=True)
    assert "cum" not in tu_hoc.doc_van(g, "A")["A-1"]["nuoc"] and r["cum_bu"] == 0
    assert cyn.BoNho(g, "A").so_hong(TD_LA.format(3)) == 1
    assert any(c["nguon"] == "cum_y_nghia" for c in tu_hoc.doc_canh_bao(g))
    # Hỏng quá SO_LAN_HONG_TOI_DA lần thì thôi hỏi.
    tu_hoc.cham_van(g, "A", dung_ai=True)
    tu_hoc.cham_van(g, "A", dung_ai=True)
    assert len(goi.lan) == cyn.SO_LAN_HONG_TOI_DA


def test_vi_chan_khong_nhan_khong_vo(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    _ho_so(g, "A", "A-1", TD_LA.format(4))
    _van_thieu_cum(g, "A", "A-1")
    dem = _vi(monkeypatch, None)
    r = tu_hoc.cham_van(g, "A", dung_ai=True)
    assert dem["n"] == 1 and r["cum_bu"] == 0
    assert "cum" not in tu_hoc.doc_van(g, "A")["A-1"]["nuoc"]


def test_ai_hong_khong_vo_cham_van(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    _ho_so(g, "A", "A-1", TD_LA.format(5))
    _van_thieu_cum(g, "A", "A-1")

    def no(*a, **k):
        raise RuntimeError("mạng sập")

    _vi(monkeypatch, no)
    r = tu_hoc.cham_van(g, "A", dung_ai=True)
    assert r["cum_bu"] == 0 and any(c["nguon"] == "cum_y_nghia" for c in tu_hoc.doc_canh_bao(g))


def test_mac_dinh_khong_goi_ai(tmp_path, monkeypatch):
    """`cham_van` không cờ (bài kiểm cũ, chạy tay) không bao giờ gọi AI."""
    g = str(tmp_path)
    _kenh(g)
    _ho_so(g, "A", "A-1", TD_LA.format(6))
    _van_thieu_cum(g, "A", "A-1")
    dem = _vi(monkeypatch, _Goi(lambda i: "khac"))
    tu_hoc.cham_van(g, "A")
    assert dem["n"] == 0


def test_bu_hoi_to_nhieu_van_mot_luot_va_bao_cao_giam(tmp_path, monkeypatch):
    from core import bao_cao_ngay as bc

    g = str(tmp_path)
    _kenh(g)
    for i in range(1, 5):
        _ho_so(g, "A", "A-%d" % i, TD_LA.format(10 + i))
        _van_thieu_cum(g, "A", "A-%d" % i)
    monkeypatch.setattr(bc, "_cac_kenh", lambda goc: ["A"])
    truoc = "\n".join(bc._muc_hoc(g, _dt.datetime.now()))  # noqa: SLF001
    assert "Ván không nhãn cụm" in truoc and "A 4/4" in truoc
    ma_cum = sorted(_cum(g))[-1]
    goi = _Goi(lambda i: ma_cum if i % 2 else "khac")
    _vi(monkeypatch, goi)
    r = tu_hoc.cham_van(g, "A", dung_ai=True)
    assert r["cum_bu"] == 4 and len(goi.lan) == 1          # 4 ván cũ, MỘT lượt gọi theo lô
    assert tu_hoc.tin_hieu_thieu(g, "A")["khong_cum"] == 0
    sau = "\n".join(bc._muc_hoc(g, _dt.datetime.now()))  # noqa: SLF001
    assert "Ván không nhãn cụm" not in sau
    assert tu_hoc.bang_diem(g, "A") is not None


def test_tran_moi_luot(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    goi = _Goi(lambda i: "khac")
    muc = [(TD_LA.format(100 + i), "") for i in range(cyn.TOI_DA_MOT_LUOT + 15)]
    assert cyn.phan_loai(g, "A", muc, goi) == cyn.TOI_DA_MOT_LUOT
    assert sum(len(re.findall(r"(?m)^\d+\. ", x.split("VIDEO:", 1)[1])) for x in goi.lan) == cyn.TOI_DA_MOT_LUOT


def test_bang_diem_hoc_canh_tay_khac(tmp_path):
    g = str(tmp_path)
    _kenh(g)
    tu_hoc.ghi_van(g, "A", "A-1", {"cum": cyn.CUM_KHAC, "cum_nguon": "y_nghia"}, {})
    v = tu_hoc.doc_van(g, "A")
    v["A-1"]["ket7"] = "thang"
    tu_hoc._luu_van(g, "A", v)  # noqa: SLF001
    assert tu_hoc.bang_diem(g, "A")["cum"][cyn.CUM_KHAC]["n"] == 1


# ── lúc chọn: `_ap_he_so_cum` luôn gắn nhãn, `gan_ung_vien` chỉ với AI thật ───

def test_ap_he_so_cum_gan_nhan_ca_khi_chua_co_bang_diem(tmp_path):
    from core import chien_luoc
    from core.chien_luoc import ngu_canh

    g = str(tmp_path)
    _kenh(g)
    ma_cum = sorted(_cum(g))[0]
    bo = cyn.BoNho(g, "A")
    bo.ghi({tu_hoc_khoa(TD_LA.format(7)): {"c": ma_cum, "t": "x", "ngay": "2026-10-07"}})
    td_kw = _tieu_de_tu_khoa(g)
    nc = ngu_canh.dung(g, "A", co_v7=False)
    bang = {"vph": [{"ma": "1", "diem": 10, "tieu_de": TD_LA.format(7), "cum": []},
                    {"ma": "2", "diem": 9, "tieu_de": td_kw, "cum": []},
                    {"ma": "3", "diem": 8, "tieu_de": TD_LA.format(8), "cum": []}]}
    chien_luoc._ap_he_so_cum(nc, bang)  # noqa: SLF001
    d1, d2, d3 = bang["vph"]
    assert (d1["cum_tu_hoc"], d1["cum_nguon"]) == (ma_cum, "y_nghia")
    assert d2["cum_nguon"] == "tu_khoa" and d2["cum_tu_hoc"]
    assert "cum_tu_hoc" not in d3 and "he_so_cum" not in d1     # chưa có bảng điểm: không nhân hệ số
    assert [d["diem"] for d in bang["vph"]] == [10, 9, 8]
    # Ván ghi lúc bàn giao lấy đúng nhãn + nguồn nhãn đã dùng lúc chọn.
    nuoc = tu_hoc._nuoc_tu(d1, {}, None)  # noqa: SLF001
    assert (nuoc["cum"], nuoc["cum_nguon"]) == (ma_cum, "y_nghia")


def tu_hoc_khoa(td):
    from core.phan_cum_ai import khoa_tieu_de

    return khoa_tieu_de(td)


def test_gan_ung_vien_chi_voi_ham_that(tmp_path, monkeypatch):
    g = str(tmp_path)
    _kenh(g)
    ch = v7.nap_cau_hinh(g, "A", ghi_neu_thieu=False)[0]
    goi = _Goi(lambda i: "khac")
    dem = _vi(monkeypatch, goi)
    ds = [TD_LA.format(20), _tieu_de_tu_khoa(g)]
    assert cyn.gan_ung_vien(g, "A", ch, lambda *a, **k: "{}", ds) == 0    # đồ giả của bài kiểm khác: không gọi
    assert dem["n"] == 0

    def that(*a, **k):
        return "{}"

    that.that = True
    assert cyn.gan_ung_vien(g, "A", ch, that, ds) == 1                  # chỉ tiêu đề bộ cụm trả []
    assert len(goi.lan) == 1 and _tieu_de_tu_khoa(g) not in goi.lan[0]
    assert cyn.BoNho(g, "A").tra(TD_LA.format(20)) == cyn.CUM_KHAC


def test_goi_vi_khong_co_config_thi_khong_goi(tmp_path, monkeypatch):
    dem = _vi(monkeypatch, _Goi(lambda i: "khac"))
    assert cyn.goi_vi(str(tmp_path)) is None and dem["n"] == 0


@pytest.mark.parametrize("ham, ky_vong", [(None, False), (lambda: 0, False)])
def test_la_goi_that(ham, ky_vong):
    assert cyn.la_goi_that(ham) is ky_vong
