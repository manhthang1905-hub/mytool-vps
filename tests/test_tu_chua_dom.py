"""Máy đăng TỰ CHỮA bộ chọn DOM (`vm/tu_chua_dom.py` + móc trong `TrangStudio._tim_spec`).

Không mạng, không Chrome: `CdpGia` trả lời `window.__yd.<ham>(…)` trên một DOM
giả (mỗi phần tử khai sẵn bộ chọn nó khớp); AI là hàm giả đếm số lần gọi.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import tu_chua_dom  # noqa: E402


class CdpGia:
    """CDP giả tối thiểu cho TrangStudio: thế giới riêng + `window.__yd.*` trên DOM giả."""

    def __init__(self, dom):
        self.dom = dom            # [{khop:set(sel), tag, chu, aria, role, attr:{}}]
        self.goi_ham = []
        self.giu_tab = set()

    def bom(self, _t=0):
        pass

    def goi(self, method, params=None, sid=None, han=None):
        p = params or {}
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "F1"}}}
        if method == "Page.createIsolatedWorld":
            return {"executionContextId": 7}
        if method == "Runtime.evaluate":
            bt = p["expression"]
            if bt.startswith("((function(CAM)"):
                return {"result": {"value": True}}
            m = re.match(r"window\.__yd\.(\w+)\((.*)\)$", bt, re.S)
            ten, doi = m.group(1), json.loads("[" + m.group(2) + "]")
            self.goi_ham.append(ten)
            return {"result": {"value": getattr(self, "y_" + ten, lambda *a: None)(*doi)}}
        return {}

    # — window.__yd giả —
    def _tra(self, i, cach, sel, so):
        e = self.dom[i]
        return {"khop": True, "cach": cach, "sel": sel, "so": so, "id": "e%d" % i, "tag": e["tag"],
                "rect": {"x": 1, "y": 1, "w": 50, "h": 20}, "tat": False, "cam": e.get("cam", ""),
                "mo_ta": e["tag"]}

    def y_tim(self, spec, o):
        for n, sel in enumerate(spec.get("chon") or []):
            ok = [i for i, e in enumerate(self.dom) if sel in e["khop"]]
            if ok:
                return self._tra(ok[min(o.get("thu") or 0, len(ok) - 1)], "chon#%d" % (n + 1), sel, len(ok))
        for i, e in enumerate(self.dom):
            if e.get("chu") and e["chu"] in (spec.get("chu") or []):
                return self._tra(i, "chu", e["chu"], 1)
        return {"khop": False, "loi_bo_chon": []}

    def y_chu(self, pid):
        return self.dom[int(pid[1:])].get("chu", "")

    def y_thuocTinh(self, pid, ten):
        e = self.dom[int(pid[1:])]
        if ten == "aria-label":
            return e.get("aria")
        if ten == "role":
            return e.get("role")
        return (e.get("attr") or {}).get(ten)

    def y_banDo(self, toi_da):
        return [{"tag": e["tag"], "id": "", "name": "", "role": e.get("role", ""), "aria": e.get("aria", ""),
                 "cls": "", "chu": e.get("chu", ""), "href": "", "tat": False, "sau": False,
                 "rect": [1, 1, 50, 20]} for e in self.dom][:toi_da]


class AiGia:
    def __init__(self, *tra_loi):
        self.tra_loi = list(tra_loi)
        self.de_bai = []

    def __call__(self, p):
        self.de_bai.append(p)
        tl = self.tra_loi[min(len(self.de_bai) - 1, len(self.tra_loi) - 1)] if self.tra_loi else ""
        return tl if isinstance(tl, str) else json.dumps(tl)


@pytest.fixture(autouse=True)
def _bat(monkeypatch):
    monkeypatch.delenv(tu_chua_dom.BIEN_TAT, raising=False)
    monkeypatch.setattr(tu_chua_dom, "NGUONG_HAN", 0.0)   # han=0 vẫn chữa → test không ngồi chờ


def _bo():
    return cdp_studio.doc_bo_chon(duong_tu_chua="")


def _chua(tmp_path, ai, **kw):
    return tu_chua_dom.TuChuaDom(goi_ai=ai, duong_tu_chua=str(tmp_path / "tu-chua.json"),
                                 duong_dem=str(tmp_path / "dem.json"),
                                 duong_nhat_ky=str(tmp_path / "tu-chua.jsonl"), **kw)


def _trang(dom, chua, bo=None):
    nk = []
    t = cdp_studio.TrangStudio(CdpGia(dom), "T1", "S1", bo_chon=bo or _bo(), nhat_ky=nk.append,
                               ngu=lambda s: None, rng=random.Random(1), tu_chua=chua)
    return t, nk


NUT_MOI = {"khop": {"ytcp-button#next-v2", "#next-v2"}, "tag": "ytcp-button", "chu": "Tiếp tục đi",
           "aria": "Tiếp"}


# ── chữa thành công + ghi tệp + dùng lại ─────────────────────────────────

def test_chua_thanh_cong_ghi_tep_va_dung_lai(tmp_path):
    ai = AiGia({"chon": ["#khong-co", "ytcp-button#next-v2"], "ly_do": "nút Tiếp mới"})
    chua = _chua(tmp_path, ai)
    t, nk = _trang([dict(NUT_MOI)], chua)
    kq = t.tim("nut_tiep", han=0)
    assert kq and kq["cach"] == "tu_chua" and kq["id"] == "e0"
    assert len(ai.de_bai) == 1
    p = ai.de_bai[0]
    assert "nut_tiep" in p and "ytcp-uploads-dialog #next-button" in p and "Tiếp" in p
    tc = json.loads((tmp_path / "tu-chua.json").read_text(encoding="utf-8"))
    assert tc["nut_tiep"]["chon"] == ["ytcp-button#next-v2"]
    assert tc["nut_tiep"]["chon_cu"] == _bo()["phan_tu"]["nut_tiep"]["chon"]
    assert tc["nut_tiep"]["luc"] and "Tiếp" in tc["nut_tiep"]["ly_do"]
    assert any("TU CHUA nut_tiep: nhận" in s for s in nk)
    nhat = [json.loads(x) for x in (tmp_path / "tu-chua.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["ket"] for x in nhat] == ["loai", "chua"]
    # cùng phiên: lần sau khớp thẳng bằng bộ chọn tự chữa (chon#1), không hỏi AI
    kq2 = t.tim("nut_tiep", han=0)
    assert kq2["cach"] == "chon#1" and kq2["sel"] == "ytcp-button#next-v2"
    # phiên mới: nạp qua doc_bo_chon (gộp tệp tự chữa), không hỏi AI
    bo = cdp_studio.doc_bo_chon(duong_tu_chua=str(tmp_path / "tu-chua.json"))
    t2, _ = _trang([dict(NUT_MOI)], _chua(tmp_path, ai), bo=bo)
    kq3 = t2.tim("nut_tiep", han=0)
    assert kq3["cach"] == "chon#1" and kq3["sel"] == "ytcp-button#next-v2"
    assert len(ai.de_bai) == 1


def test_bo_chon_goc_khop_thi_khong_dung_toi_ai(tmp_path):
    ai = AiGia({"chon": ["ytcp-button#next-v2"]})
    dom = [{"khop": {"ytcp-uploads-dialog #next-button"}, "tag": "ytcp-button", "chu": "Tiếp"}]
    t, nk = _trang(dom, _chua(tmp_path, ai))
    kq = t.tim("nut_tiep", han=0)
    assert kq["cach"] == "chon#1" and ai.de_bai == []
    assert not (tmp_path / "tu-chua.json").exists() and not nk


def test_cho_ngan_duoi_nguong_khong_chua(tmp_path, monkeypatch):
    """co()/cho_mat() dò han=0 để biết VẮNG — không được hỏi AI."""
    monkeypatch.setattr(tu_chua_dom, "NGUONG_HAN", 3.0)
    ai = AiGia({"chon": ["ytcp-button#next-v2"]})
    t, _ = _trang([dict(NUT_MOI)], _chua(tmp_path, ai))
    assert t.co("nut_tiep") is False and t.cho_mat("nut_tiep", han=0) is True
    assert ai.de_bai == []


# ── ứng viên bị loại ─────────────────────────────────────────────────────

def test_loai_ung_vien_khop_0_hoac_nhieu_va_nho_am(tmp_path):
    dom = [dict(NUT_MOI), dict(NUT_MOI)]          # "ytcp-button#next-v2" khớp 2 phần tử
    ai = AiGia({"chon": ["#khong-co", "ytcp-button#next-v2"]})
    chua = _chua(tmp_path, ai)
    t, nk = _trang(dom, chua)
    assert t.tim("nut_tiep", han=0) is None
    assert not (tmp_path / "tu-chua.json").exists()
    nhat = [json.loads(x) for x in (tmp_path / "tu-chua.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["ket"] for x in nhat] == ["loai", "loai", "khong"]
    assert "khớp 0" in nhat[0]["ly_do"] and "khớp 2" in nhat[1]["ly_do"]
    assert any("không nhận ứng viên nào" in s for s in nk)
    # hỏi hụt → nhớ âm 1 giờ: lần sau không gọi AI
    assert t.tim("nut_tiep", han=0) is None and len(ai.de_bai) == 1
    # tiến trình khác (bộ chữa mới, cùng sổ đếm) cũng tôn trọng hạn âm
    t2, _ = _trang(dom, _chua(tmp_path, ai))
    assert t2.tim("nut_tiep", han=0) is None and len(ai.de_bai) == 1


def test_khoa_danh_sach_nhan_nhieu_khop(tmp_path):
    o = {"khop": {"ytcp-playlist-dialog-v2 [role=checkbox]"}, "tag": "div", "role": "checkbox"}
    ai = AiGia({"chon": ["ytcp-playlist-dialog-v2 [role=checkbox]"]})
    t, _ = _trang([dict(o), dict(o), dict(o)], _chua(tmp_path, ai))
    kq = t.tim("playlist_muc", han=0)
    assert kq and kq["cach"] == "tu_chua" and kq["so"] == 3


def test_loai_khi_chu_khong_khop_goi_y_hoac_the_vo_ly(tmp_path):
    dom = [{"khop": {"#nut-la"}, "tag": "ytcp-button", "chu": "Hủy", "aria": "Hủy"},
           {"khop": {"span.tieu-de"}, "tag": "span", "chu": "tiêu đề"}]
    ai = AiGia({"chon": ["#nut-la"]}, {"chon": ["span.tieu-de"]})
    chua = _chua(tmp_path, ai, han_am=0)
    t, _ = _trang(dom, chua)
    assert t.tim("nut_tiep", han=0) is None            # chữ "Hủy" ≠ gợi ý "Tiếp"
    assert t.tim("tieu_de", han=0) is None             # khoá ô gõ mà là <span>
    ly = [json.loads(x)["ly_do"] for x in (tmp_path / "tu-chua.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any("chữ không khớp" in s for s in ly) and any("ô gõ" in s for s in ly)


def test_loai_phan_tu_cam(tmp_path):
    dom = [dict(NUT_MOI, cam="aria chứa phản hồi")]
    ai = AiGia({"chon": ["ytcp-button#next-v2"]})
    t, _ = _trang(dom, _chua(tmp_path, ai))
    assert t.tim("nut_tiep", han=0) is None


# ── công tắc / hạn mức / không AI ────────────────────────────────────────

def test_cong_tac_tat(tmp_path, monkeypatch):
    monkeypatch.setenv(tu_chua_dom.BIEN_TAT, "0")
    ai = AiGia({"chon": ["ytcp-button#next-v2"]})
    t, _ = _trang([dict(NUT_MOI)], _chua(tmp_path, ai))
    assert t.tim("nut_tiep", han=0) is None and ai.de_bai == []
    # mặc định (tu_chua=None) khi tắt: không tạo bộ chữa
    t2, _ = _trang([dict(NUT_MOI)], None)
    assert t2.tim("nut_tiep", han=0) is None and t2._tu_chua is False
    # tắt thì cũng không gộp tệp tự chữa
    p = tmp_path / "tc.json"
    p.write_text(json.dumps({"nut_tiep": {"chon": ["#x-moi"]}}), encoding="utf-8")
    assert "#x-moi" not in cdp_studio.doc_bo_chon(duong_tu_chua=str(p))["phan_tu"]["nut_tiep"]["chon"]


def test_han_muc_moi_khoa_moi_ngay(tmp_path):
    gio = [1_800_000_000.0]
    ai = AiGia({"chon": ["#khong-co"]})
    chua = _chua(tmp_path, ai, han_am=0, toi_da_ngay=3, bay_gio=lambda: gio[0])
    t, _ = _trang([dict(NUT_MOI)], chua)
    for _ in range(5):
        assert t.tim("nut_tiep", han=0) is None
    assert len(ai.de_bai) == 3
    assert "hết hạn mức ngày" in chua.ly_do_khong_chua("nut_tiep", {})
    gio[0] += 86400                                   # ngày mới → đếm lại
    assert t.tim("nut_tiep", han=0) is None and len(ai.de_bai) == 4


def test_han_muc_phien(tmp_path):
    ai = AiGia({"chon": ["#khong-co"]})
    chua = _chua(tmp_path, ai, han_am=0, toi_da_phien=2)
    t, _ = _trang([dict(NUT_MOI)], chua)
    for k in ("nut_tiep", "hien_them", "playlist_xong"):
        t.tim(k, han=0)
    assert len(ai.de_bai) == 2


def test_khong_co_ai_thi_khong_lam_gi(tmp_path, monkeypatch):
    monkeypatch.setattr(tu_chua_dom, "goi_ai_mac_dinh", lambda ghi=None: None)
    chua = _chua(tmp_path, None)
    t, nk = _trang([dict(NUT_MOI)], chua)
    assert t.tim("nut_tiep", han=0) is None and t.tim("nut_tiep", han=0) is None
    assert sum("không có AI" in s for s in nk) == 1
    assert not (tmp_path / "dem.json").exists()


def test_khoa_do_trang_thai_va_ban_do_rong_khong_hoi(tmp_path):
    ai = AiGia({"chon": ["ytcp-button#next-v2"]})
    t, _ = _trang([dict(NUT_MOI)], _chua(tmp_path, ai))
    assert t.tim("hop_da_xong", han=0) is None          # vắng là bình thường
    t2, _ = _trang([], _chua(tmp_path, ai))              # trang trống → không có gì để hỏi
    assert t2.tim("nut_tiep", han=0) is None
    assert ai.de_bai == []


def test_ai_tra_loi_hong_va_loi(tmp_path):
    ai = AiGia("xin lỗi, tôi không biết")
    t, _ = _trang([dict(NUT_MOI)], _chua(tmp_path, ai, han_am=0))
    assert t.tim("nut_tiep", han=0) is None

    def no(_p):
        raise RuntimeError("mạng hỏng")
    t2, nk = _trang([dict(NUT_MOI)], _chua(tmp_path, no, han_am=0))
    assert t2.tim("hien_them", han=0) is None and any("gọi AI lỗi" in s for s in nk)


# ── gộp ưu tiên trong doc_bo_chon + bỏ khi hụt ───────────────────────────

def test_gop_uu_tien_doc_bo_chon(tmp_path):
    goc = _bo()
    p = tmp_path / "tc.json"
    p.write_text(json.dumps({
        "nut_tiep": {"chon": ["ytcp-button#next-v2"], "chon_cu": goc["phan_tu"]["nut_tiep"]["chon"]},
        "hien_them": {"chon": ["#moi-hien-them"], "chon_cu": ["#nguoi-da-sua-json"]},   # JSON đã đổi → bỏ
        "tieu_de": {"chon": ["#lech[ngoac"]},                                           # cú pháp hỏng → bỏ
        "khoa_la": {"chon": ["#x"]},                                                    # khoá không có → bỏ
    }, ensure_ascii=False), encoding="utf-8")
    bo = cdp_studio.doc_bo_chon(duong_tu_chua=str(p))
    nt = bo["phan_tu"]["nut_tiep"]
    assert nt["chon"][0] == "ytcp-button#next-v2" and nt["chon"][1:] == goc["phan_tu"]["nut_tiep"]["chon"]
    assert nt["_tu_chua"] == ["ytcp-button#next-v2"] and nt["chu"] == goc["phan_tu"]["nut_tiep"]["chu"]
    assert bo["phan_tu"]["hien_them"] == goc["phan_tu"]["hien_them"]
    assert bo["phan_tu"]["tieu_de"] == goc["phan_tu"]["tieu_de"]
    assert "khoa_la" not in bo["phan_tu"]
    assert cdp_studio.kiem_bo_chon(bo) == []
    # tệp hỏng → bộ gốc nguyên vẹn
    p.write_text("{hỏng", encoding="utf-8")
    assert cdp_studio.doc_bo_chon(duong_tu_chua=str(p)) == goc
    # đọc tệp bộ chọn tường minh thì mặc định KHÔNG gộp
    assert "_tu_chua" not in json.dumps(cdp_studio.doc_bo_chon(cdp_studio.DUONG_BO_CHON))


def test_tu_chua_hut_goc_khop_lai_thi_bo(tmp_path):
    goc = _bo()
    p = tmp_path / "tu-chua.json"
    p.write_text(json.dumps({"nut_tiep": {"chon": ["ytcp-button#next-v2"],
                                          "chon_cu": goc["phan_tu"]["nut_tiep"]["chon"]}}), encoding="utf-8")
    bo = cdp_studio.doc_bo_chon(duong_tu_chua=str(p))
    ai = AiGia({"chon": ["#x"]})
    dom = [{"khop": {"ytcp-uploads-dialog #next-button"}, "tag": "ytcp-button", "chu": "Tiếp"}]
    t, nk = _trang(dom, _chua(tmp_path, ai), bo=bo)
    kq = t.tim("nut_tiep", han=0)
    assert kq["cach"] == "chon#1" and kq["sel"] == "ytcp-uploads-dialog #next-button"
    assert "nut_tiep" not in json.loads(p.read_text(encoding="utf-8"))
    assert t.bo["phan_tu"]["nut_tiep"]["chon"] == goc["phan_tu"]["nut_tiep"]["chon"]
    assert "_tu_chua" not in t.bo["phan_tu"]["nut_tiep"]
    assert any("bỏ bộ chọn tự chữa" in s for s in nk) and not any("DU PHONG" in s for s in nk)
    assert ai.de_bai == [] and bo["phan_tu"]["nut_tiep"]["_tu_chua"]     # dict người gọi không bị sửa


def test_tu_chua_hut_han_thi_bo_roi_chua_lai(tmp_path):
    goc = _bo()
    p = tmp_path / "tu-chua.json"
    p.write_text(json.dumps({"nut_tiep": {"chon": ["#cu-tu-chua"],
                                          "chon_cu": goc["phan_tu"]["nut_tiep"]["chon"]}}), encoding="utf-8")
    bo = cdp_studio.doc_bo_chon(duong_tu_chua=str(p))
    ai = AiGia({"chon": ["ytcp-button#next-v2"]})
    t, nk = _trang([dict(NUT_MOI)], _chua(tmp_path, ai), bo=bo)
    kq = t.tim("nut_tiep", han=0)
    assert kq and kq["cach"] == "tu_chua"
    assert json.loads(p.read_text(encoding="utf-8"))["nut_tiep"]["chon"] == ["ytcp-button#next-v2"]
    assert json.loads(p.read_text(encoding="utf-8"))["nut_tiep"]["chon_cu"] == goc["phan_tu"]["nut_tiep"]["chon"]
    assert "#cu-tu-chua" not in t.bo["phan_tu"]["nut_tiep"]["chon"]
    assert any("bỏ bộ chọn tự chữa" in s for s in nk)


# ── hàm thuần ────────────────────────────────────────────────────────────

def test_doc_tra_loi_va_rut_ban_do():
    s, ly = tu_chua_dom.doc_tra_loi('đây: ```json\n{"chon": ["#a", "#a", "#b", "#c", "#d"], "ly_do": "x"}\n```')
    assert s == ["#a", "#b", "#c"] and ly == "x"
    assert tu_chua_dom.doc_tra_loi("không có json") == ([], "")
    bd = [{"tag": "div", "chu": "khác"}] * 300 + [{"tag": "ytcp-button", "chu": "Tiếp"}]
    rut = tu_chua_dom.rut_ban_do(bd, {"chon": ["#next-button"], "chu": ["Tiếp"]}, toi_da=250)
    assert len(rut) == 250 and rut[-1]["chu"] == "Tiếp"
    assert tu_chua_dom.loai_khoa("o_ngay_mo") == "nut" and tu_chua_dom.loai_khoa("o_gio") == "nhap"
    assert tu_chua_dom.loai_khoa("link_video") == "lien_ket" and tu_chua_dom.loai_khoa("hop_upload") == "khac"
