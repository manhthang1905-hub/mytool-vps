"""Danh sách phát chủ đề tự động (16/10/2026): kế hoạch theo nghĩa (LLM giả), idempotent khi tạo, chọn danh sách cho
video mới lúc bàn giao, điều kiện skill D15 + trần bộ tự kích hoạt, đường khoá máy bận.

Cô lập: mọi thứ trong `tmp_path`; LLM và DOM đều giả; không mạng, không Chrome. Mã video / kênh / tiêu đề đều GIẢ.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import sys
import time
from pathlib import Path

import pytest

GOC_KHO = Path(__file__).resolve().parent.parent
if str(GOC_KHO / "vm") not in sys.path:
    sys.path.insert(0, str(GOC_KHO / "vm"))

import danh_sach_phat_dom as dd  # noqa: E402
import studio_may_dom as smd  # noqa: E402
import thiet_lap_kenh_dom as tl  # noqa: E402

from core import danh_sach_phat as dsp  # noqa: E402
from core import ky_nang as kn  # noqa: E402
from core import ky_nang_tu as knt  # noqa: E402

K = "KX9-T7"
BAY = dt.datetime(2026, 10, 16, 15, 35)


def _vid(i: int) -> str:
    return "FAKEvid{0:04d}".format(i)


def _goc(tmp_path, n=9, kenh=K, phat="song", yaml_them=""):
    g = tmp_path
    d = g / "CHANNEL" / kenh
    (d / "chi-so").mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text('ngon_ngu: "ja"\n' + yaml_them, encoding="utf-8")
    with io.open(str(d / "chi-so" / "bang-tom-tat.csv"), "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(["Tiêu đề", "Mã video", "Ngày đăng", "Lượt hiển thị", "Lượt xem"])
        for i in range(1, n + 1):
            w.writerow(["tieu de gia {0}".format(i), _vid(i), "2026-10-{0:02d}".format(i), str(i * 100), str(i * 10)])
        w.writerow([_vid(99), _vid(99), "2026-10-15", "3", "0"])            # tiêu đề = mã: bỏ
    (g / "workspace" / "kenh-khong-phat").mkdir(parents=True, exist_ok=True)
    (g / "workspace" / "kenh-khong-phat" / (kenh + ".json")).write_text(
        json.dumps({"trang_thai": phat, "ly_do": "gia"}), encoding="utf-8")
    return str(g)


def _tra_ke_hoach(nhom=((1, 2, 3), (4, 5, 6), (7, 8, 9)), ten=("Chu de A", "Chu de B", "Chu de C")):
    return json.dumps({"danh_sach": [{"ten": t, "mo_ta": "mo ta " + t, "cum": ["c1"], "video": list(v), "ly_do": "x",
                                      "do_tin": 0.7} for t, v in zip(ten, nhom)], "phan_bien": "pb"}, ensure_ascii=False)


class Goi:
    """LLM giả: trả lần lượt các câu trong `tra`, ghi đề bài."""

    def __init__(self, *tra):
        self.tra, self.de = list(tra), []

    def __call__(self, de, mo_hinh="", khoa="", toi_da_token=0):
        self.de.append(de)
        return self.tra.pop(0) if len(self.tra) > 1 else self.tra[0]


# ═══ 1. KẾ HOẠCH ═══════════════════════════════════════════════════════════

def test_ke_hoach_dung_khuon_va_xep_tot_truoc(tmp_path):
    goc = _goc(tmp_path)
    ke = dsp.lap_ke_hoach(goc, K, Goi(_tra_ke_hoach()))
    assert ke["so_video"] == 9 and _vid(99) not in ke["tieu_de"]
    ds = ke["danh_sach"]
    assert [d["ten"] for d in ds] == ["Chu de C", "Chu de B", "Chu de A"]              # tổng lượt xem giảm dần
    assert ds[0]["video"] == [_vid(9), _vid(8), _vid(7)]                                # tốt trước
    for d in ds:
        assert set(d) >= {"ma", "ten", "mo_ta", "cum", "video", "ly_do", "do_tin", "trang_thai", "da_them", "tai_dung"}
        assert d["trang_thai"] == dsp.KE_HOACH and d["da_them"] == []
    dsp.ghi(goc, K, ke)
    lai = dsp.doc(goc, K)
    assert lai["phien_ban"] == dsp.PHIEN_BAN and lai["kenh"] == K and len(lai["danh_sach"]) == 3
    assert os.path.isfile(os.path.join(goc, "CHANNEL", K, "nghien-cuu", "danh-sach-phat.json"))


def test_ke_hoach_video_sot_duoc_xep_bu_theo_nghia(tmp_path):
    goc = _goc(tmp_path)
    goi = Goi(_tra_ke_hoach(nhom=((1, 2, 3), (4, 5), (7, 8, 9))), json.dumps({"1": 2}))   # sót video 6 → danh sách 2
    ke = dsp.lap_ke_hoach(goc, K, goi)
    b = next(d for d in ke["danh_sach"] if d["ten"] == "Chu de B")
    assert _vid(6) in b["video"] and "Xếp mỗi video" in goi.de[-1]


@pytest.mark.parametrize("tra, loi", [
    (_tra_ke_hoach(ten=("Trung", "trung", "C")), "trùng"),
    (_tra_ke_hoach(nhom=((1, 2, 3, 4, 5, 6, 7, 8, 9),), ten=("A",)), "cần"),
    (_tra_ke_hoach(nhom=((1, 2), (3, 4), (5,)), ten=("A", "B", "C")), "cần"),
    (json.dumps({"x": 1}), "danh_sach"),
])
def test_chuan_hoa_tu_choi_sai_luat(tmp_path, tra, loi):
    video = dsp.video_kenh(_goc(tmp_path), K)
    with pytest.raises(ValueError, match=loi):
        dsp.chuan_hoa_ke_hoach(json.loads(tra), video)


def test_ke_hoach_llm_hong_hoi_lai_roi_nem(tmp_path):
    goc = _goc(tmp_path)
    assert dsp.lap_ke_hoach(goc, K, Goi("khong phai json", _tra_ke_hoach()))["danh_sach"]   # lần 2 đúng
    with pytest.raises(RuntimeError):
        dsp.lap_ke_hoach(goc, K, Goi("hong"))
    with pytest.raises(ValueError):
        dsp.lap_ke_hoach(_goc(tmp_path / "it", n=4), K, Goi(_tra_ke_hoach()))           # quá ít video


def test_ten_bo_ky_tu_cam():
    video = [{"id": _vid(i), "tieu_de": "t{0}".format(i), "view": 1} for i in range(1, 7)]
    ds, sot = dsp.chuan_hoa_ke_hoach({"danh_sach": [{"ten": "<A> ★", "video": [1, 2]}, {"ten": "B", "video": [3, 4]},
                                                    {"ten": "C", "video": [5, 6]}]}, video)
    assert ds[0]["ten"] == "A" and sot == []


# ═══ 2. IDEMPOTENT KHI TẠO ═════════════════════════════════════════════════

def test_quyet_tao_dung_lai_cho_tao():
    luc = time.time()
    assert dd.quyet_tao({"ten": "Chu  de A"}, ["chu de a", "Khac"], luc) == "co_san"      # NFKC + hoa/thường
    gan = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(luc - 60))
    xa = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(luc - 3600))
    assert dd.quyet_tao({"ten": "X", "luc_bam_tao": gan}, [], luc) == "cho"
    assert dd.quyet_tao({"ten": "X", "luc_bam_tao": xa}, [], luc) == "tao"
    assert dd.quyet_tao({"ten": "X"}, [], luc) == "tao"


class StudioGia:
    """Studio giả: bảng tên danh sách phát; `tao_ds_phat` thêm tên (đếm lần tạo)."""

    def __init__(self, co=(), dem=None):
        self.ten, self.tao, self.uc, self.dem = list(co), [], "UCgia", dem

    def mo(self, url, cho_css, han=45.0):
        pass

    def ngu(self, s):
        pass

    def js(self, bt):
        if bt is dd._JS_HANG:
            return [{"ten": t, "chu": "{0}\nCông khai\n3".format(t), "href": ["/playlist/PLgia{0:010d}/videos".format(i)]}
                    for i, t in enumerate(self.ten)]
        return {"hang": len(self.ten), "ten": list(self.ten), "trong": not self.ten,
                "chan": "1 – {0}/{1}".format(len(self.ten), self.dem if self.dem is not None else len(self.ten))}

    def tao_ds_phat(self, ten, mo_ta):
        self.tao.append((ten, mo_ta))
        self.ten.append(ten)

    def chup(self, nhan):
        pass

    def bang_chung(self, nhan):
        return {"anh": "anh-" + nhan + ".png"}


class KeoCheoGia:
    """Máy thêm giả (cùng giao diện `MayStudio`: doc_ten / them)."""

    def __init__(self, ket=None, hop=("Ten trong o",)):
        self.ket, self.goi, self.hop = dict(ket or {}), [], hop

    def doc_ten(self, vid):
        return list(self.hop)

    def them(self, vid, ten):
        self.goi.append((vid, ten))
        k = self.ket.get(vid, "ok")
        return {"ket": k(vid) if callable(k) else k}


def _ke(goc):
    ke = dsp.lap_ke_hoach(goc, K, Goi(_tra_ke_hoach()))
    dsp.ghi(goc, K, ke)
    return ke


def test_tao_thieu_dung_lai_ten_co_san_khong_tao_trung(tmp_path):
    goc = _goc(tmp_path)
    ke = _ke(goc)
    S = StudioGia(co=["Chu de B", "Cu cua chu"])
    ten = dd.ten_tren_kenh(S, KeoCheoGia(), ke, lambda s: None)
    assert "Ten trong o" in ten and "Chu de B" in ten
    ket = {"tao": [], "loi": []}
    dd.tao_thieu(S, ke, ten, lambda: dsp.ghi(goc, K, ke), lambda s: None, ket)
    assert sorted(t for t, _m in S.tao) == ["Chu de A", "Chu de C"]                     # B đã có: dùng lại
    assert all(m.startswith("mo ta") for _t, m in S.tao)
    b = next(d for d in ke["danh_sach"] if d["ten"] == "Chu de B")
    assert b["tai_dung"] is True and all(d["trang_thai"] == dsp.DA_TAO for d in ke["danh_sach"])
    assert "Cu cua chu" in S.ten                                                       # không xoá/đổi tên cái cũ
    dd.tao_thieu(S, dsp.doc(goc, K), dd.ten_tren_kenh(S, KeoCheoGia(), ke, lambda s: None), lambda: None,
                 lambda s: None, {"tao": [], "loi": []})
    assert len(S.tao) == 2                                                             # chạy lại: không tạo thêm


def test_bam_tao_ma_chua_thay_thi_khong_tao_lai(tmp_path):
    goc = _goc(tmp_path)
    ke = _ke(goc)

    class Cham(StudioGia):
        def tao_ds_phat(self, ten, mo_ta):        # bấm Tạo nhưng Studio chưa hiện
            self.tao.append((ten, mo_ta))
    S = Cham()
    ket = {"tao": [], "loi": []}
    dd.tao_thieu(S, ke, [], lambda: None, lambda s: None, ket)
    assert len(S.tao) == 3 and all(d["luc_bam_tao"] for d in ke["danh_sach"]) and len(ket["loi"]) == 3
    dd.tao_thieu(S, ke, [], lambda: None, lambda s: None, {"tao": [], "loi": []})
    assert len(S.tao) == 3                                                             # trong 30': đợi, không bấm lại


def test_khong_doc_du_ten_thi_khong_tao_mu(tmp_path):
    goc = _goc(tmp_path)
    ke = _ke(goc)
    with pytest.raises(tl.LoiMuc, match="chống trùng"):
        dd.ten_tren_kenh(StudioGia(co=["A"], dem=12), KeoCheoGia(), ke, lambda s: None)


def test_them_video_xac_nhan_loi_bo_va_khong_bam_lai(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    ke = _ke(goc)
    for d in ke["danh_sach"]:
        d["trang_thai"] = dsp.DA_TAO
    ke["danh_sach"][0]["da_them"] = [_vid(9)]
    monkeypatch.setattr(smd, "_kiem_dung", lambda agent, kenh: None)
    monkeypatch.setattr(tl, "khung_gio_tron", lambda luc, phut=0: "")
    kc = KeoCheoGia(ket={_vid(8): "da_co", _vid(7): "loi:tich: x", _vid(6): "loi:tim_ds: không có"})
    ket = {"tao": [], "them": [], "loi": [], "dung": ""}
    for _ in range(dsp.LOI_VIDEO_TOI_DA):
        dd.them_video(None, None, None, K, ke, kc, lambda: None, lambda s: None, ket, time.monotonic(), ngu=lambda s: None)
    assert _vid(9) not in [v for v, _t in kc.goi]                                     # đã xác nhận: không bấm nữa
    assert _vid(8) in ke["danh_sach"][0]["da_them"]
    assert _vid(7) in ke["video_bo"] and kc.goi.count((_vid(7), "Chu de C")) == dsp.LOI_VIDEO_TOI_DA
    b = ke["danh_sach"][1]
    assert b["loi"] == dsp.LOI_VIDEO_TOI_DA and not b["da_them"]                       # tim_ds: lỗi của danh sách
    assert _vid(6) not in ke["video_bo"]
    assert dsp.viec_con(ke)["cho_them"] == 3                                          # danh sách B còn chờ


def test_them_video_dung_khi_agent_doi_chrome(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    ke = _ke(goc)
    for d in ke["danh_sach"]:
        d["trang_thai"] = dsp.DA_TAO

    def doi(agent, kenh):
        raise tl.Hoan("agent báo có việc đăng")
    monkeypatch.setattr(smd, "_kiem_dung", doi)
    kc, ket = KeoCheoGia(), {"tao": [], "them": [], "loi": [], "dung": ""}
    dd.them_video(None, None, None, K, ke, kc, lambda: None, lambda s: None, ket, time.monotonic())
    assert kc.goi == [] and "agent" in ket["dung"]


def test_doc_lai_chi_tren_studio(tmp_path):
    goc = _goc(tmp_path)
    ke = _ke(goc)
    d, d2 = ke["danh_sach"][0], ke["danh_sach"][1]
    d.update(trang_thai=dsp.DA_TAO, da_them=[_vid(9), _vid(8)])
    d2.update(trang_thai=dsp.DA_TAO, da_them=[_vid(6), _vid(5), _vid(4), _vid(3)])
    S = StudioGia(co=[d["ten"], d2["ten"]])                                            # Studio: 3 video mỗi hàng
    ra = dd.doc_lai(S, ke, lambda s: None)
    o = ra["ds"][d["ten"]]
    assert o["thay_studio"] and o["so_video_studio"] == 3 and o["cong_khai"] is True and o["khop"]
    assert o["ma"].startswith("PLgia") and ra["anh"]
    assert ra["ds"][d2["ten"]]["khop"] is False                                        # Studio ít hơn số đã xác nhận


# ═══ 2b. THÊM QUA STUDIO (trang sửa video) ═════════════════════════════════

class StGia:
    """TrangStudio giả của trang sửa video: ô «Danh sách phát» (tích bật/tắt THẬT — bấm hai lần là bỏ tích), nút Lưu
    sáng khi có thay đổi, «Huỷ thay đổi»."""

    def __init__(self, ten, luu=None, tich_hong=False):
        self.ten, self.luu, self.tich_hong = list(ten), {k: set(v) for k, v in (luu or {}).items()}, tich_hong
        self.vid, self.hop, self.nhap, self.bam_ghi, self.mo_ghi = "", False, set(), [], []

    def mo(self, url, han=60):
        self.mo_ghi.append(url)
        self.vid = url.split("/video/")[1].split("/")[0]
        self.hop, self.nhap = False, set(self.luu.get(self.vid, set()))

    def url(self):
        return "https://studio.youtube.com/video/{0}/edit".format(self.vid)

    def _ban(self):
        return self.nhap != self.luu.get(self.vid, set())

    def tim(self, khoa, han=0, hien=True, cho_tat=False, trong=None, thu=0):
        if khoa in ("tieu_de", "playlist_mo"):
            return {"khoa": khoa}
        if khoa == "sua_luu":
            return {"khoa": khoa, "tat": not self._ban()}
        if khoa == "sua_huy_thay_doi":
            return {"khoa": khoa} if self._ban() else None
        if khoa in ("playlist_muc", "playlist_ten"):
            return {"khoa": khoa, "i": thu, "so": len(self.ten)} if self.hop and thu < len(self.ten) else None
        if khoa == "playlist_xong":
            return {"khoa": khoa} if self.hop else None
        return None

    def co(self, khoa, **kw):
        return self.tim(khoa) is not None

    def bam(self, x, hau_dieu_kien=None, han_hau=10.0, **kw):
        k = x if isinstance(x, str) else x["khoa"]
        self.bam_ghi.append(k if isinstance(x, str) else (k, x.get("i")))
        if k == "playlist_mo":
            self.hop = True
        elif k == "playlist_xong":
            self.hop = False
        elif k == "playlist_muc" and not self.tich_hong:
            self.nhap ^= {self.ten[x["i"]]}
        elif k == "sua_luu":
            self.luu[self.vid] = set(self.nhap)
        elif k == "sua_huy_thay_doi":
            self.nhap = set(self.luu.get(self.vid, set()))

    def doc_chu(self, x, han=5.0):
        if x == "tieu_de":
            return "tieu de gia"
        return "" if x["khoa"] == "playlist_muc" else self.ten[x["i"]] + "\nCông khai"

    def doc_thuoc_tinh(self, x, ten, han=5.0):
        return "true" if self.ten[x["i"]] in self.nhap else "false"

    def phim(self, ten, n=1, modifiers=0):
        self.hop = False


class SGia:
    def __init__(self, st):
        self.st = st

    def url(self):
        return self.st.url()

    def ngu(self, s):
        pass

    def bang_chung(self, nhan):
        return {"anh": "anh-" + nhan + ".png"}


def test_studio_them_mot_lan_luu_va_doc_lai():
    st = StGia(["Chu de A", "Chu de B"])
    kq = dd.MayStudio(SGia(st), lambda s: None).them(_vid(1), "Chu de B")
    assert kq["ket"] == "ok" and kq["tich_mo_lai"] is True and st.luu[_vid(1)] == {"Chu de B"}
    assert st.bam_ghi.count(("playlist_muc", 1)) == 1 and "sua_luu" in st.bam_ghi    # bấm ĐÚNG một lần
    assert all("/video/" in u and u.endswith("/edit") for u in st.mo_ghi) and len(st.mo_ghi) == 2   # chỉ trang sửa
    assert not any("watch" in u for u in st.mo_ghi)


def test_studio_da_co_khong_bam_khong_luu():
    st = StGia(["Chu de A", "Chu de B"], luu={_vid(1): {"Chu de B"}})
    kq = dd.MayStudio(SGia(st), lambda s: None).them(_vid(1), "Chu de B")
    assert kq["ket"] == "da_co" and st.luu[_vid(1)] == {"Chu de B"}
    assert not any(isinstance(b, tuple) and b[0] == "playlist_muc" for b in st.bam_ghi) and "sua_luu" not in st.bam_ghi


def test_studio_khong_thay_ten_hoac_tich_hong_thi_khong_luu():
    st = StGia(["Chu de A"])
    kq = dd.MayStudio(SGia(st), lambda s: None).them(_vid(1), "Khong co")
    assert kq["ket"].startswith("loi:tim_ds") and "sua_luu" not in st.bam_ghi and kq["anh"]
    st = StGia(["Chu de A"], tich_hong=True)
    kq = dd.MayStudio(SGia(st), lambda s: None).them(_vid(1), "Chu de A")
    assert kq["ket"].startswith("loi:tich") and "sua_luu" not in st.bam_ghi and not st.luu.get(_vid(1))


def test_studio_doc_ten_khong_tich():
    st = StGia(["Chu de A", "Chu de B"])
    assert dd.MayStudio(SGia(st), lambda s: None).doc_ten(_vid(1)) == ["Chu de A", "Chu de B"]
    assert not any(isinstance(b, tuple) for b in st.bam_ghi) and "sua_luu" not in st.bam_ghi


def test_chay_mo_phien_duoc_luu_trang_sua(tmp_path):
    goc = _goc(tmp_path)
    kw = {}

    def p(kenh, ghi, lam, che_do, **k):
        kw.update(k)
        return dd.MA_HOAN, "bận"
    dd.chay(K, lambda s: None, goi=Goi(_tra_ke_hoach()), phien=p, goc=goc)
    assert kw.get("cho_luu") is True


# ═══ 2c. CHỈ VIDEO CỦA KÊNH ════════════════════════════════════════════════

def test_chi_video_cua_kenh(tmp_path):
    goc = _goc(tmp_path)
    video = dsp.video_kenh(goc, K, rieng=False)
    tool = {_vid(i) for i in range(1, 9)}                                              # sổ phủ 8/9: video 9 là lạ
    giu, loai, nguon = dsp.loc_rieng(goc, K, video, tool)
    assert loai == [_vid(9)] and nguon == "so_tool" and len(giu) == 8
    giu, loai, nguon = dsp.loc_rieng(goc, K, video, {_vid(1)})                         # sổ phủ ít: lịch sử máy khác
    assert loai == [] and len(giu) == 9 and nguon == "studio_lich_su_may_khac"
    ke = {"danh_sach": [{"ten": "A", "video": [_vid(9), _vid(1)], "da_them": []},
                        {"ten": "B", "video": [_vid(9)], "da_them": [_vid(9)]}]}
    assert dsp.cat_ngoai_kenh(goc, K, ke, video, tool) == 1
    assert ke["danh_sach"][0]["video"] == [_vid(1)] and ke["danh_sach"][1]["video"] == [_vid(9)]   # đã xác nhận: giữ
    assert ke["ngoai_kenh"] == [_vid(9)]


def test_video_tool_doc_so_may_dang_va_ke_hoach(tmp_path):
    goc = _goc(tmp_path)
    (tmp_path / "vm" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vm" / "logs" / "so-video-id.json").write_text(json.dumps(
        {K + "/" + K + "-0001": {"video_id": _vid(1)}, "KHAC/KHAC-0001": {"video_id": _vid(2)}}), encoding="utf-8")
    hs = tmp_path / "CHANNEL" / K / "ho-so-video"
    hs.mkdir()
    (hs / "a.json").write_text(json.dumps({"video_id": _vid(3)}), encoding="utf-8")
    assert dsp.video_tool(goc, K) == {_vid(1), _vid(3)}


# ═══ 3. VIDEO MỚI LÚC BÀN GIAO ═════════════════════════════════════════════

def test_chon_danh_sach_cho_video_moi(tmp_path):
    goc = _goc(tmp_path)
    assert dsp.ten_cho_tai_len(goc, K) == ([], "")                                     # chưa có kế hoạch: như cũ
    ke = _ke(goc)
    assert dsp.ten_cho_tai_len(goc, K) == ([], "")                                     # chưa tạo trên YouTube
    for d in ke["danh_sach"][:2]:
        d["trang_thai"] = dsp.DA_TAO
    dsp.ghi(goc, K, ke)
    ten, nguon = dsp.ten_cho_tai_len(goc, K)
    assert ten == ["Chu de C", "Chu de B"] and nguon == "ke_hoach"
    assert dsp.chon_cho_video(ten, nguon, "t", "m", lambda de: "Chu de B") == "Chu de B"   # LLM chọn theo nghĩa
    assert dsp.chon_cho_video(ten, nguon, "t", "m", lambda de: "linh tinh") == "Chu de C"  # không khớp → đầu
    assert dsp.chon_cho_video(ten, nguon, "t", "m", None) == "Chu de C"                    # không có AI → đầu

    def hong(de):
        raise RuntimeError("mạng")
    assert dsp.chon_cho_video(ten, nguon, "t", "m", hong) == "Chu de C"
    assert dsp.chon_cho_video(["Y1", "Y2"], "kenh_yaml", "t", "m", None) == ""             # kenh.yaml: giữ hành vi cũ


def test_kenh_yaml_thang_ke_hoach(tmp_path):
    goc = _goc(tmp_path, yaml_them='danh_sach_phat_kenh: "Y1 | Y2"\n')
    assert dsp.ten_cho_tai_len(goc, K) == (["Y1", "Y2"], "kenh_yaml")


def test_ban_giao_ghi_cot_danh_sach_phat_tu_ke_hoach(tmp_path, monkeypatch):
    from core import ban_giao_dang, ke_hoach_dang, qa_truoc_dang
    monkeypatch.setattr(qa_truoc_dang, "kiem_thu_muc_goi", lambda *a, **k: qa_truoc_dang.KetQuaQA())
    goc = str(tmp_path / "goc")
    (tmp_path / "goc" / "CHANNEL" / "K1").mkdir(parents=True)
    (tmp_path / "goc" / "CHANNEL" / "K1" / "kenh.yaml").write_text("ma: K1\nthu_muc_done: DONE/K1\n", encoding="utf-8")
    d = tmp_path / "goc" / "PROJECTS" / "AUTO" / "K1" / "0001"
    (d / "7-thumbnail").mkdir(parents=True)
    (d / "6-clip").mkdir()
    (d / ban_giao_dang.TEP_VIDEO).write_bytes(b"video")
    (d / ban_giao_dang.TEP_SRT).write_text("1\n", encoding="utf-8")
    (d / "7-thumbnail" / "CHON-a.jpg").write_bytes(b"jpg")
    (d / "1-tieu-de.txt").write_text("TITLE: tieu de thu\n", encoding="utf-8")
    (d / "1-seo.txt").write_text("DESCRIPTION:\nmo ta thu\nKEYWORDS:\na, b\n", encoding="utf-8")
    (d / "4-canh.json").write_text(json.dumps([{"scene_id": 1}]), encoding="utf-8")
    (d / "6-clip" / "1.mp4").write_bytes(b"clip")
    dsp.ghi(goc, "K1", {"danh_sach": [{"ten": "Dau", "trang_thai": dsp.DA_TAO}, {"ten": "Hai", "trang_thai": dsp.DA_TAO},
                                      {"ten": "Chua", "trang_thai": dsp.KE_HOACH}]})
    de = []
    ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"), ngay="08/10/2026", gio="05:00",
                           goi_ai=lambda s: de.append(s) or "Hai")
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    assert hang[0][cot.index("Danh sách phát")] == "Hai"
    assert "- Dau" in de[0] and "- Chua" not in de[0]                                  # chỉ danh sách đã tạo


def test_gan_moi_uu_tien_cot_ke_hoach_dang_roi_llm(tmp_path, monkeypatch):
    goc = _goc(tmp_path, n=12)
    video = dsp.video_kenh(goc, K)
    ke = dsp.lap_ke_hoach(goc, K, Goi(_tra_ke_hoach()), video=video[:9])
    ke["danh_sach"][0]["da_them"] = list(ke["danh_sach"][0]["video"])
    monkeypatch.setattr(dsp, "_cot_ke_hoach_dang", lambda goc, kenh: {_vid(10): "Chu de A"})
    goi = Goi(json.dumps({"1": 2, "2": 9}))                                            # 11 → B · 12 → số sai → đầu
    assert dsp.gan_moi(goc, K, ke, goi, video=video) == 3
    ten = {d["ten"]: d for d in ke["danh_sach"]}
    assert _vid(10) in ten["Chu de A"]["video"] and _vid(11) in ten["Chu de B"]["video"]
    assert _vid(12) in ke["danh_sach"][0]["video"]
    assert ten["Chu de C"]["video"][:3] == [_vid(9), _vid(8), _vid(7)]                 # đã xác nhận giữ đầu
    assert "tieu de gia 10" not in goi.de[0]                                           # cột kế hoạch đăng: khỏi hỏi AI


# ═══ 4. ĐIỀU KIỆN SKILL D15 ════════════════════════════════════════════════

def test_can_chay_cac_truong_hop(tmp_path):
    goc = _goc(tmp_path)
    ok, ly = dsp.can_chay(goc, K)
    assert ok and "chưa có" in ly
    assert dsp.can_chay(_goc(tmp_path / "a", phat="chua_du"), K)[0] is False           # chưa được phát
    assert dsp.can_chay(_goc(tmp_path / "b", phat="khong_phat"), K)[0] is False
    assert dsp.can_chay(_goc(tmp_path / "c", yaml_them='danh_sach_phat_kenh: "A | B"\n'), K)[0] is False
    assert dsp.can_chay(_goc(tmp_path / "d", n=5), K)[0] is False                       # quá ít video
    ke = _ke(goc)
    assert "chưa tạo" in dsp.can_chay(goc, K)[1]
    for d in ke["danh_sach"]:
        d["trang_thai"] = dsp.DA_TAO
    dsp.ghi(goc, K, ke)
    assert "chờ thêm" in dsp.can_chay(goc, K)[1]
    for d in ke["danh_sach"]:
        d["da_them"] = list(d["video"])
    dsp.ghi(goc, K, ke)
    assert dsp.can_chay(goc, K)[0] is False


def test_can_chay_quy_tac_8_video_moi(tmp_path):
    goc = _goc(tmp_path, n=9 + dsp.MOI_TOI_THIEU)
    ke = dsp.lap_ke_hoach(goc, K, Goi(_tra_ke_hoach()), video=dsp.video_kenh(goc, K)[:9])
    for d in ke["danh_sach"]:
        d.update(trang_thai=dsp.DA_TAO, da_them=list(d["video"]))
    ke["video_bo"] = {_vid(10): "hỏng"}
    dsp.ghi(goc, K, ke)
    ok, ly = dsp.can_chay(goc, K)
    assert not ok and "7 video mới" in ly                                              # 8 mới − 1 đã bỏ = 7 < 8
    ke["video_bo"] = {}
    dsp.ghi(goc, K, ke)
    ok, ly = dsp.can_chay(goc, K)
    assert ok and "8 video mới" in ly


def test_dang_xuat_thi_nghi_roi_thu_lai(tmp_path):
    goc = _goc(tmp_path)
    dsp.ghi(goc, K, {"dang_xuat": {"luc": "2026-10-16 10:00:00"}})
    assert dsp.can_chay(goc, K, BAY)[0] is False
    assert dsp.can_chay(goc, K, BAY + dt.timedelta(hours=dsp.GIO_CHO_DANG_NHAP))[0] is True


def test_skill_d15_khai_dung_va_bi_chan_dom(tmp_path, monkeypatch):
    k = kn.theo_ma("D15")
    assert k and k.tu_ap and k.nang and not k.toan_may and "D15" in knt.UU_TIEN_NANG and "D15" in knt.BO_PHAN
    lenh = knt.lenh_cua(k, "G", K)
    assert lenh[-2:] == ["--kenh", K] and lenh[-3].endswith("danh_sach_phat_dom.py")
    goc = _goc(tmp_path)
    monkeypatch.setattr(kn, "_gio", lambda: BAY)
    monkeypatch.setattr(kn, "_san_sang_dom", lambda goc, kenh: "")
    assert kn.d_danh_sach_phat(goc, K)[0] is True
    assert kn.k_danh_sach_phat(goc, K)[0] == kn.THIEU
    monkeypatch.setattr(kn, "_san_sang_dom", lambda goc, kenh: "đăng ở máy khác")
    assert kn.d_danh_sach_phat(goc, K) == (False, "đăng ở máy khác")
    monkeypatch.setattr(kn, "_san_sang_dom", lambda goc, kenh: "")
    monkeypatch.setattr(kn, "_gio", lambda: BAY.replace(hour=3))
    assert kn.d_danh_sach_phat(goc, K)[0] is False                                     # khung cấm 02–07


def test_tu_kich_hoat_mot_kenh_moi_luot_va_tam_dung_sau_3_hong(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _goc(tmp_path, kenh="KX8-T7")
    monkeypatch.setattr(kn, "_gio", lambda: BAY)
    monkeypatch.setattr(kn, "_san_sang_dom", lambda goc, kenh: "")
    monkeypatch.setattr(kn, "DANH_MUC", [kn.theo_ma("D15")])
    monkeypatch.setattr(kn, "_cac_kenh", lambda goc: ["KX8-T7", K])
    monkeypatch.setattr(knt, "khoa_may_ban", lambda goc: "")
    monkeypatch.setattr(knt, "cong_tac_bat", lambda goc: True)
    from core import bao_dong, nao_bo_phan
    bao = []
    monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: bao.append(a))
    monkeypatch.setattr(nao_bo_phan, "ghi", lambda *a, **k: True)
    chay = []
    for i in range(3):
        monkeypatch.setattr(kn, "_gio", lambda i=i: BAY + dt.timedelta(hours=kn.NHIP_DSP_GIO * i))
        knt.tu_kich_hoat(goc, chay_lenh=lambda lenh, cwd, han: (chay.append(lenh[-1]), (1, "hỏng"))[1],
                         in_ra=lambda s: None)
        assert len(chay) == 2 * i + 1                                                  # MỘT kênh mỗi lượt
        knt.tu_kich_hoat(goc, chay_lenh=lambda lenh, cwd, han: (chay.append(lenh[-1]), (1, "hỏng"))[1],
                         in_ra=lambda s: None)
    assert any(x.get("quyet") == "bo_qua" for x in knt.doc_so(goc))
    assert bao and "D15" in bao[0][1]                                                  # hỏng 3 lần → báo động
    n0 = len(chay)
    knt.tu_kich_hoat(goc, chay_lenh=lambda lenh, cwd, han: (chay.append(lenh[-1]), (1, "hỏng"))[1], in_ra=lambda s: None)
    assert len(chay) == n0                                                            # tạm dừng 24 giờ: không chạy
    assert {x["quyet"] for x in knt.danh_gia(goc, kn._gio())} == {"tam_dung"}


# ═══ 5. BỘ CHẠY: KHOÁ MÁY BẬN · MÃ THOÁT ═══════════════════════════════════

def test_khoa_may_ban_thi_hoan_ke_hoach_van_luu(tmp_path):
    goc = _goc(tmp_path)
    goi = Goi(_tra_ke_hoach())
    phien = []

    def ban(kenh, ghi, lam, che_do, **k):
        phien.append(che_do)
        return dd.MA_HOAN, "khoá máy (.khoa-may) đang bận — không ép"
    assert dd.chay(K, lambda s: None, goi=goi, phien=ban, goc=goc) == dd.MA_HOAN
    assert phien == [dd.CHE_DO] and len(dsp.doc(goc, K)["danh_sach"]) == 3
    assert dd.chay(K, lambda s: None, goi=Goi("không được gọi lại"), phien=ban, goc=goc) == dd.MA_HOAN
    assert len(goi.de) == 1                                                            # kế hoạch cũ: không hỏi lại AI


def test_bo_qua_kenh_khong_phat_va_kenh_yaml(tmp_path):
    phien = []
    p = lambda *a, **k: phien.append(1) or (0, {})  # noqa: E731
    assert dd.chay(K, lambda s: None, goi=Goi(_tra_ke_hoach()), phien=p,
                   goc=_goc(tmp_path / "a", phat="chua_du")) == dd.MA_KHONG_CAN
    assert dd.chay(K, lambda s: None, goi=Goi(_tra_ke_hoach()), phien=p,
                   goc=_goc(tmp_path / "b", yaml_them='danh_sach_phat_kenh: "A | B"\n')) == dd.MA_KHONG_CAN
    assert phien == []


def test_dang_xuat_ghi_dau_va_ma_can_nguoi(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    monkeypatch.setattr(dd, "_bao_dang_xuat", lambda kenh, ke: None)
    ma = dd.chay(K, lambda s: None, goi=Goi(_tra_ke_hoach()), phien=lambda *a, **k: (dd.MA_CAN_NGUOI, "dang-xuat"), goc=goc)
    assert ma == dd.MA_CAN_NGUOI and dsp.doc(goc, K)["dang_xuat"]["luc"]


def test_ma_thoat_theo_tien_do():
    ke = {"danh_sach": [{"ten": "A", "trang_thai": dsp.DA_TAO, "video": ["v1", "v2"], "da_them": ["v1"]}]}
    assert dd.ma_thoat({"tao": [], "them": [{"kq": "xac_nhan"}]}, ke) == dd.MA_HOAN      # còn việc, đã tiến
    assert dd.ma_thoat({"tao": [], "them": [{"kq": "loi"}]}, ke) == dd.MA_LOI           # còn việc, không tiến
    ke["danh_sach"][0]["da_them"].append("v2")
    assert dd.ma_thoat({"tao": [], "them": []}, ke) == dd.MA_XONG


def test_phien_vua_khung_phut_35():
    luc = time.mktime((2026, 10, 16, 15, 35, 0, 0, 0, -1))
    assert tl.khung_gio_tron(luc, smd.DU_KIEN_PHUT[dd.CHE_DO]) == ""                    # bộ tự kích hoạt chạy :35


def test_ham_thuan_doc_bang():
    assert dd.ma_danh_sach(["/x", "https://studio.youtube.com/playlist/PLabcdefghijkl12/videos"]) == "PLabcdefghijkl12"
    assert dd.ma_danh_sach(["https://www.youtube.com/playlist?list=PLzzzzzzzzzzzz"]) == "PLzzzzzzzzzzzz"
    assert dd.so_video_hang("Ten\nCông khai\n12 thg 10, 2026\n7") == 7 and dd.so_video_hang("") is None


# ═══ 6. DANH SÁCH CỦA CHỦ: để yên ══════════════════════════════════════════

def test_danh_sach_cua_chu_khong_bao_gio_them_video(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    ke = _ke(goc)
    S = StudioGia(co=["Chu de B"])                                                     # có TỪ TRƯỚC kế hoạch
    dd.tao_thieu(S, ke, dd.ten_tren_kenh(S, KeoCheoGia(), ke, lambda s: None), lambda: dsp.ghi(goc, K, ke),
                 lambda s: None, {"tao": [], "loi": []})
    b = next(d for d in ke["danh_sach"] if d["ten"] == "Chu de B")
    assert b["cua_chu"] is True and b["video"] == [] and sorted(ke["cho_xep"]) == [_vid(4), _vid(5), _vid(6)]
    assert all(d is not b for d, _v in dd.viec_them(ke))                               # D15 không thêm vào
    monkeypatch.setattr(smd, "_kiem_dung", lambda agent, kenh: None)
    monkeypatch.setattr(tl, "khung_gio_tron", lambda luc, phut=0: "")
    kc = KeoCheoGia()
    dd.them_video(None, None, None, K, ke, kc, lambda: None, lambda s: None,
                  {"tao": [], "them": [], "loi": [], "dung": ""}, time.monotonic(), ngu=lambda s: None)
    assert kc.goi and all(t != "Chu de B" for _v, t in kc.goi)
    dsp.ghi(goc, K, ke)
    assert "xếp lại" in dsp.can_chay(goc, K)[1]
    goi = Goi(json.dumps({"1": 1, "2": 2, "3": 1}))
    assert dsp.gan_moi(goc, K, ke, goi) == 3                                           # nhả → xếp vào danh sách TOOL
    assert b["video"] == [] and not ke["cho_xep"] and "Chu de B" not in goi.de[0]
    dsp.ghi(goc, K, ke)
    assert "Chu de B" in dsp.ten_cho_tai_len(goc, K)[0]                                # vẫn khớp tên lúc tải lên


def test_cua_chu_danh_dau_tu_luc_lap_va_cot_ke_hoach_dang(tmp_path, monkeypatch):
    goc = _goc(tmp_path, n=10)
    goi = Goi(_tra_ke_hoach(), json.dumps({"1": 1, "2": 2, "3": 1, "4": 1}))
    ke, _v = dsp.cap_nhat_ke_hoach(goc, K, goi, ds_co=["Chu de A"], log=lambda s: None)
    a = next(d for d in ke["danh_sach"] if d["ten"] == "Chu de A")
    assert a["cua_chu"] is True and a["video"] == []
    assert all(_vid(i) in [v for d in ke["danh_sach"] if not d.get("cua_chu") for v in d["video"]] for i in (1, 2, 3))
    monkeypatch.setattr(dsp, "_cot_ke_hoach_dang", lambda goc, kenh: {_vid(11): "Chu de A"})
    ke["cho_xep"] = []
    video = dsp.video_kenh(goc, K) + [{"id": _vid(11), "tieu_de": "moi", "view": 0, "hien_thi": 0}]
    dsp.gan_moi(goc, K, ke, Goi("{}"), video=video)
    assert _vid(11) in ke["video_cua_chu"] and _vid(11) not in [v for d in ke["danh_sach"] for v in d["video"]]
