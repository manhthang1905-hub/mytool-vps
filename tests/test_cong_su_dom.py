"""Máy cộng sự DOM (21/10/2026): `vm/cong_su_dom.py` — trang giả (không Chrome, không mạng)."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
for _p in (str(GOC), str(GOC / "vm")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cong_su_dom as csd  # noqa: E402
import cdp_studio  # noqa: E402
from core import cong_su as cs  # noqa: E402

BO = {"url": {"sua": "https://studio/video/{id}/edit", "cs_loi_moi": "https://studio/channel/{uc}/videos/collaboration"},
      "phan_tu": {}}


class TrangGia:
    """Trang sửa + hộp Mời cộng sự + tab Video cộng tác, đủ để chạy luồng."""

    def __init__(self, kenh_youtube=None, co_khoi=True, het_cho_sau=99, canh_bao="", hang_tab=None):
        self.kenh_youtube = kenh_youtube or {}      # handle → tên (kết quả tìm)
        self.co_khoi = co_khoi
        self.het_cho_sau = het_cho_sau
        self.canh_bao_chu = canh_bao
        self.hang_tab = hang_tab or {}              # vid → {"co_nut": bool}
        self.da_luu = []                            # handle đã ở khối (đã mời)
        self.chon = []                              # handle đã chọn trong hộp (chưa lưu)
        self.hop_mo = False
        self.go_chu = ""
        self.nhat = []
        self.url_ = ""

    # giao diện TrangCongSu
    def mo(self, url):
        self.nhat.append(("mo", url))
        self.url_ = url

    def url(self):
        return self.url_

    def tim(self, khoa, han=0):
        if khoa == "tieu_de":
            return {"khoa": khoa}
        if khoa == "hien_them":
            return {"khoa": khoa}
        if khoa == "cs_khoi":
            return {"khoa": khoa} if self.co_khoi else None
        if khoa == "cs_nut_mo":
            return {"khoa": khoa}
        if khoa in ("cs_hop_xong", "cs_hop_huy"):
            return {"khoa": khoa} if self.hop_mo else None
        if khoa == "sua_luu":
            return {"khoa": khoa, "tat": True}
        if khoa == "cs_nut_moi":
            return None
        return None

    def hien(self, khoa):
        return khoa == "cs_het_cho" and len(self.da_luu) + len(self.chon) >= self.het_cho_sau

    def bam(self, pt):
        k = pt.get("khoa")
        self.nhat.append(("bam", k))
        if k == "cs_nut_mo":
            self.hop_mo = True
        elif k == "cs_goi_y":
            self.chon.append(pt["handle"])
        elif k == "cs_hop_xong":
            self.da_luu += self.chon
            self.chon, self.hop_mo = [], False
        elif k == "cs_hop_huy":
            self.chon, self.hop_mo = [], False
        elif k == "cs_nut_nhan":
            self.hang_tab[pt["vid"]]["co_nut"] = False

    def go(self, khoa, chu):
        self.nhat.append(("go", khoa, chu))
        self.go_chu = chu
        return chu

    def phim(self, ten):
        self.nhat.append(("phim", ten))

    def doc(self):
        # đo 21/10/2026: hàng cộng sự chỉ có trong HỘP, mang tên kênh + nhãn trạng thái (không @handle, không UC)
        hang = [{"chu": "{0} Đã gửi lời mời".format(self.kenh_youtube.get(h, "?")), "uc": [], "hrefs": [],
                 "ten": self.kenh_youtube.get(h, "?"), "nhan": "Đã gửi lời mời", "state": "pending"}
                for h in self.da_luu] if self.hop_mo else []
        return {"hop": self.hop_mo, "khoi": self.co_khoi, "hang": hang, "link": [], "o_tim": "o" if self.hop_mo else ""}

    def goi_y(self):
        if not self.go_chu:
            return []
        return [{"khoa": "cs_goi_y", "handle": h, "ten": t, "chu": t} for h, t in self.kenh_youtube.items()
                if self.go_chu.lstrip("@") in h.lstrip("@")]

    def canh_bao(self):
        return self.canh_bao_chu

    def hang_video(self, vid):
        if vid not in self.hang_tab:
            return {"hang": False}
        nut = {"khoa": "cs_nut_nhan", "vid": vid} if self.hang_tab[vid]["co_nut"] else None
        return {"hang": True, "chu": "video", "nut": nut}

    def ghi_chan_doan(self, nhan):
        self.nhat.append(("chan_doan", nhan))
        return {"anh": "x.png"}


def _may(tr):
    return csd.MayCongSu(tr, BO, nhat_ky=lambda s: None, ngu=lambda s: None)


NGUOI = [{"kenh": "KB", "uc": "UC" + "b" * 22, "handle": "@kenh-b", "ten": "B"},
         {"kenh": "KC", "uc": "UC" + "c" * 22, "handle": "@kenh-c", "ten": "C"}]


def test_trang_thai_hang_theo_nhan_hop():
    assert csd.MayCongSu.trang_thai_hang({"ten": "B", "nhan": "Cộng sự đang hoạt động", "state": "complete"}) == "nhan"
    assert csd.MayCongSu.trang_thai_hang({"ten": "B", "nhan": "Đã gửi lời mời", "state": "pending"}) == "cho"
    assert csd.MayCongSu.trang_thai_hang({}) == ""
    hop = {"hop": True, "hang": [{"ten": "B", "nhan": "Cộng sự đang hoạt động", "state": "complete"}]}
    assert csd.MayCongSu.da_co(hop, "", "", "B") and not csd.MayCongSu.da_co(hop, "", "", "C")


def test_moi_theo_handle_luu_va_doc_lai():
    tr = TrangGia({"@kenh-b": "B", "@kenh-c": "C", "@kenh-bx": "giả"})
    kq = _may(tr).moi("vid00000001", NGUOI)
    assert [r["ket"] for r in kq] == ["da_moi", "da_moi"]
    assert tr.da_luu == ["@kenh-b", "@kenh-c"]
    assert ("go", "cs_o_tim", "@kenh-b") in tr.nhat


def test_handle_mo_ho_hai_goi_y_khong_chon_mu():
    tr = TrangGia({"@kenh-b": "B"})
    tr.goi_y = lambda: [{"khoa": "cs_goi_y", "handle": "@kenh-b"}, {"khoa": "cs_goi_y", "handle": "@KENH-B"}]
    kq = _may(tr).moi("vid00000001", NGUOI[:1])
    assert kq[0]["ket"].startswith("loi:") and "không chọn mù" in kq[0]["ket"]
    assert ("bam", "cs_hop_huy") in tr.nhat and tr.da_luu == []           # không lưu gì


def test_da_co_san_khong_go_lai():
    tr = TrangGia({"@kenh-b": "B", "@kenh-c": "C"})
    tr.da_luu = ["@kenh-b"]
    kq = _may(tr).moi("vid00000001", NGUOI)
    assert [r["ket"] for r in kq] == ["da_co", "da_moi"]
    assert ("go", "cs_o_tim", "@kenh-b") not in tr.nhat


def test_het_cho_youtube():
    tr = TrangGia({"@kenh-b": "B", "@kenh-c": "C"}, het_cho_sau=1)
    kq = _may(tr).moi("vid00000001", NGUOI)
    assert [r["ket"] for r in kq] == ["da_moi", "tran"]


def test_thieu_handle_khong_moi():
    tr = TrangGia({"@kenh-b": "B"})
    kq = _may(tr).moi("vid00000001", [{"kenh": "KB", "uc": "UC" + "b" * 22, "handle": ""}])
    assert kq[0]["ket"].startswith("loi:") and "@handle" in kq[0]["ket"]


def test_canh_bao_youtube_dung():
    tr = TrangGia({"@kenh-b": "B"}, canh_bao="Tính năng này bị hạn chế")
    with pytest.raises(csd.CanhBaoYouTube):
        _may(tr).moi("vid00000001", NGUOI)


def test_khong_co_khoi_la_khong_tinh_nang():
    with pytest.raises(csd.KhongCoTinhNang):
        _may(TrangGia(co_khoi=False)).moi("vid00000001", NGUOI)


def test_che_do_thu_khong_go_khong_luu():
    tr = TrangGia({"@kenh-b": "B"})
    kq = _may(tr).moi("vid00000001", NGUOI, che_do="thu")
    assert all(r["ket"].startswith("thu:") for r in kq)
    assert not any(x[0] == "go" for x in tr.nhat) and tr.da_luu == []


def test_nhan_bam_chap_nhan_va_doc_lai():
    tr = TrangGia(hang_tab={"vid00000001": {"co_nut": True}})
    may = _may(tr)
    may.uc = "UC" + "b" * 22
    assert may.nhan({"video_id": "vid00000001"})["ket"] == "da_nhan"
    assert tr.nhat[0] == ("mo", "https://studio/channel/{0}/videos/collaboration".format(may.uc))
    assert may.nhan({"video_id": "vid00000001"})["ket"] == "da_nhan_san"
    with pytest.raises(csd.LoiCongSu):
        may.nhan({"video_id": "vidKHONGCO1"})


def test_nhan_che_do_thu():
    tr = TrangGia(hang_tab={"vid00000001": {"co_nut": True}})
    assert _may(tr).nhan({"video_id": "vid00000001"}, che_do="thu")["ket"] == "thu:co_nut_nhan"
    assert tr.hang_tab["vid00000001"]["co_nut"] is True


def test_bo_chon_that_du_khoa():
    bo, loi = csd.chuan_bi_bo(cdp_studio.doc_bo_chon())
    assert loi == [] and "cs_loi_moi" in bo["url"]


def test_ke_hoach_moi_truoc_nhan_sau(tmp_path, monkeypatch):
    """Lượt kế hoạch: mời (Chrome kênh nguồn) → ghi da_moi → vòng nhận lấy việc mới (Chrome kênh được mời)."""
    monkeypatch.setattr(csd, "GOC_TOOL", str(tmp_path))
    monkeypatch.setattr(cs, "trong_gio_cam", lambda bay, cai: "")
    lo = {"id": "moi_cong_su:vid00000001", "loai": cs.LOAI, "kenh_nguon": "KA", "video_id": "vid00000001",
          "trang_thai": "mo", "nguoi_moi": [dict(n, dot="A", trang_thai=cs.TT_CHO, han_moi="2000-01-01 00:00:00")
                                            for n in NGUOI]}
    cs.ghi_hang(str(tmp_path), [lo])
    goi = []

    def chay(kenh, ds, che_do, tu_giu=True, ngu=None):
        goi.append((kenh, [v["viec"] for v in ds]))
        if ds[0]["viec"] == "moi":
            kq = [{"kenh": n["kenh"], "ket": "da_moi"} for n in ds[0]["nguoi"]]
            csd._ghi_ket(cs, ds[0], kq)
            return csd.MA_XONG, [dict(ds[0], ket=kq)]
        return csd.MA_XONG, [dict(ds[0], ket="da_nhan")]
    ma, _ = csd.chay_ke_hoach("that", tu_giu=False, chay=chay)
    assert ma == csd.MA_XONG
    assert goi == [("KA", ["moi"]), ("KB", ["nhan"]), ("KC", ["nhan"])]
    n = cs.doc_hang(str(tmp_path))[0]["nguoi_moi"]
    assert {x["trang_thai"] for x in n} == {cs.TT_DA_MOI}        # `chay` giả không ghi da_nhan


def test_da_co_doc_chu_khoi_chi_khi_hop_dong():
    khoi = {"hop": False, "hang": [], "chu": "Cộng tác Kênh B @kenh-b Đang chờ phản hồi · Mời cộng sự"}
    h = csd.MayCongSu.da_co(khoi, "UC" + "b" * 22, "@kenh-b")
    assert h.get("tu_chu_khoi") and csd.MayCongSu.trang_thai_hang(h) == "cho"
    assert csd.MayCongSu.da_co(khoi, "", "@kenh") == {}                     # không khớp tiền tố
    assert csd.MayCongSu.da_co(dict(khoi, hop=True), "", "@kenh-b") == {}   # hộp mở: chữ có cả kết quả tìm


def test_ke_hoach_dung_khan_khong_lam(tmp_path, monkeypatch):
    monkeypatch.setattr(csd, "GOC_TOOL", str(tmp_path))
    cs.dat_dung(str(tmp_path), "thử")
    ma, ra = csd.chay_ke_hoach("that", tu_giu=False, chay=lambda *a, **k: pytest.fail("không được chạy"))
    assert ma == csd.MA_CHAN and ra == []


def test_phien_agent_co_buoc_cong_su_truoc_khi_dong_chrome(monkeypatch):
    """Chủ 21/10: KHÔNG mở Chrome thêm — bước cộng sự nằm TRONG phiên ngày của kênh, sau bình luận, trước đóng Chrome."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("vm_agent_cong_su", GOC / "vm" / "agent.py")
    ag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ag)
    goi = []
    monkeypatch.setattr(ag, "GOC", str(GOC / "vm"))
    monkeypatch.setattr(ag, "_mo_chrome_viec_dang", lambda ch: True)
    monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: goi.append("dong"))
    monkeypatch.setattr(ag, "doi_viec_khoa_may", lambda v: None)
    monkeypatch.setattr(ag, "_doc_trang_thai", lambda c: {})
    monkeypatch.setattr(ag, "co_token_oauth", lambda k: False)
    monkeypatch.setattr(ag, "_chay_mot_lan", lambda duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",):
                        goi.append((Path(duong).name, tuple(co_gi_them))) or ("ok", 0))
    ag.chay_mot_phien({}, {"kenh": "K", "cach_dang": "anh", "tu_dang": True}, "K")
    ten = [g[0] if isinstance(g, tuple) else g for g in goi]
    assert ("cong_su_dom.py", ("--phien", "--trong-phien")) in goi
    assert ten.index("cong_su_dom.py") > ten.index("may_cmt_dom.py") and ten[-1] == "dong"
    goi.clear()
    ag.chay_mot_phien({"phien_cong_su": False}, {"kenh": "K", "cach_dang": "anh", "tu_dang": True}, "K")
    assert "cong_su_dom.py" not in [g[0] if isinstance(g, tuple) else g for g in goi]


def test_phien_khong_viec_khong_noi_chrome(tmp_path, monkeypatch):
    monkeypatch.setattr(csd, "GOC_TOOL", str(tmp_path))
    monkeypatch.setattr(csd, "chay_kenh", lambda *a, **k: pytest.fail("không việc thì không được nối Chrome"))
    monkeypatch.setattr(csd, "_cai_nhat_ky", lambda: None)
    assert csd.main(["--phien", "--kenh", "KA", "--trong-phien"]) == csd.MA_XONG
