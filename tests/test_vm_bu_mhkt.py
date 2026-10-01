"""BÙ MÀN HÌNH KẾT THÚC video đã đăng mà thiếu (01/10/2026).

Video lên kênh với sổ `mhkt` = bo / lỗi / rỗng tự vào hàng bù đêm sau; agent chạy
`may_dang_dom.py --bu-mhkt` giờ vắng (sau QUÉT NGÀY của kênh, trước 05:00, nhường
phiên/quét), tối đa 3 video/kênh/đêm. Máy đăng: trang sửa → nhập từ video đã có
MHKT / dựng mẫu → Lưu → ĐỌC LẠI → sổ `mhkt=ok:bu` (hoặc `khong-the` + lý do).

Mọi bài chạy trong thư mục tạm — KHÔNG chạm vm/logs thật (có bài canh).
VideoId trong bài đều giả (không phải id thật của kênh).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import may_dang_dom as mdd  # noqa: E402

K = "TL1-T7"


def _muc(vid, mhkt="bo", lich="30/09/2026 20:00", **kw):
    d = {"video_id": vid, "trang_thai": "xac-nhan", "mhkt": mhkt, "lich": lich}
    d.update(kw)
    return d


# ═══ HÀNG BÙ (hàm thuần) ═══════════════════════════════════════════════════

class TestHangBu:
    def test_chon_bo_loi_rong_lich_cu_truoc_tran_3(self):
        so = {
            K + "/0007": _muc("FAKEaaaaaa1", "bo", "30/09/2026 20:00"),
            K + "/0008": _muc("FAKEaaaaaa2", "bo", "30/09/2026 05:00"),
            K + "/0009": _muc("FAKEaaaaaa3", "", "01/10/2026 16:00"),
            K + "/0010": _muc("FAKEaaaaaa4", "loi: x", "30/09/2026 16:00"),
            K + "/0011": _muc("FAKEaaaaaa5", None, "01/10/2026 05:00"),
            K + "/0001": _muc("FAKEaaaaaa6", "ok:nhap"),
            K + "/0002": _muc("FAKEaaaaaa7", "ok:bu"),
            K + "/0003": _muc("FAKEaaaaaa8", "khong-the", mhkt_bu_ly_do="video dưới 25 giây"),
            K + "/0004": _muc("FAKEaaaaaa9", "bo", tai_xong=False),
            K + "/0005": _muc("FAKEaaaab10", "bo", trang_thai="nhap"),
            K + "/0006": _muc("FAKEaaaab11", "bo", mhkt_bu_loi_lan=3),
            "TL2-T7/0001": _muc("FAKEaaaab12", "bo"),
        }
        assert mdd.hang_bu_mhkt(so, K, "2026-10-01") == [
            (K + "/0008", "FAKEaaaaaa2"), (K + "/0010", "FAKEaaaaaa4"), (K + "/0007", "FAKEaaaaaa1")]
        assert len(mdd.hang_bu_mhkt(so, K, "2026-10-01", toi_da=10)) == 5

    def test_moi_video_mot_lan_moi_dem_da_thu_tru_tran(self):
        so = {K + "/1": _muc("FAKEbbbbbb1", "bo", mhkt_bu_ngay="2026-10-01", mhkt_bu_ket="loi", mhkt_bu_loi_lan=1),
              K + "/2": _muc("FAKEbbbbbb2", "ok:bu", mhkt_bu_ngay="2026-10-01", mhkt_bu_ket="ok"),
              K + "/3": _muc("FAKEbbbbbb3", "khong-the", mhkt_bu_ngay="2026-10-01", mhkt_bu_ket="khong-the"),
              K + "/4": _muc("FAKEbbbbbb4", "bo"), K + "/5": _muc("FAKEbbbbbb5", "bo")}
        assert mdd.hang_bu_mhkt(so, K, "2026-10-01") == [(K + "/4", "FAKEbbbbbb4")], \
            "2 video đã thử thật đêm nay → còn 1 chỗ; bỏ qua (khong-the) không tính"
        # Đêm sau: video hỏng lần 1 quay lại hàng.
        assert (K + "/1", "FAKEbbbbbb1") in mdd.hang_bu_mhkt(so, K, "2026-10-02")

    def test_danh_sach_thieu_kem_ly_do(self):
        so = {K + "/1": _muc("FAKEccccccc", "khong-the", mhkt_bu_ket="khong-the", mhkt_bu_luc="2026-10-01 03:00:00",
                             mhkt_bu_ly_do="Shorts"),
              K + "/2": _muc("FAKEcccccc2", "ok:bu")}
        ds = mdd.danh_sach_thieu_mhkt(so)
        assert list(ds) == [K + "/1"] and ds[K + "/1"]["ly_do"] == "Shorts"


# ═══ TRANG SỬA giả (trình soạn MHKT) ═══════════════════════════════════════

class TrangSuaGia:
    """Trang sửa Studio + trình soạn màn hình kết thúc — cùng giao diện TrangStudio."""

    def __init__(self, video: dict, nguon_co_mhkt: dict = None, luu_hong: bool = False):
        self.video = video                    # vid → {"dai", "mhkt": [...], "shorts"}
        self.nguon = nguon_co_mhkt or {}      # vid nguồn trong hộp chọn → có MHKT để nhập không
        self.luu_hong = luu_hong
        self.vid = None
        self.soan = None                      # None | "soan" | "chon"
        self.hang = []
        self.khong_nguon = False
        self.dem_luu = 0
        self.bang_chung = []

    def _v(self):
        return self.video.get(self.vid)

    def mo(self, url, cho_khoa=None, han=60):
        self.vid = url.split("/video/")[1].split("/")[0] if "/video/" in url else None
        self.soan, self.hang, self.khong_nguon = None, [], False
        return True

    def bat_json(self, url, chua_url, han=30, toi_da=4):
        self.mo(url)
        v = self._v()
        if v is None:
            return [{"videos": []}]
        return [{"videos": [{"videoId": self.vid, "status": "VIDEO_STATUS_PROCESSED",
                             "lengthSeconds": str(v.get("dai", 600))}]}]

    def _hien(self, khoa):
        v = self._v()
        s = self.soan
        return bool({
            "tieu_de": v is not None,
            "mhkt_mo_sua": v is not None and not v.get("shorts") and s is None,
            "hop_mhkt": s in ("soan", "chon"),
            "mhkt_phan_tu": s == "soan" and bool(self.hang),
            "mhkt_mau": s == "soan" and not self.hang,
            "mhkt_nhap_trong": s == "soan",
            "mhkt_chon_video": s == "chon",
            "mhkt_hop_chon": s == "chon", "mhkt_dong_chon": s == "chon", "mhkt_tim_video": s == "chon",
            "mhkt_luu": s == "soan" and bool(self.hang),
            "hop_con_huy": s == "soan",
        }.get(khoa))

    def tim(self, khoa, han=10, hien=True, cho_tat=False, trong=None, thu=0):
        if not self._hien(khoa):
            return None
        so = 6 if khoa == "mhkt_mau" else 1
        return {"khoa": khoa, "id": "{0}#{1}".format(khoa, thu), "so": so, "thu": thu, "tat": False}

    def co(self, khoa, **kw):
        return self.tim(khoa) is not None

    def tim_chua(self, khoa, chuoi, han=8):
        if self.soan == "chon" and khoa == "mhkt_chon_video" and chuoi in self.nguon:
            return {"khoa": khoa, "id": "the#" + chuoi, "vid": chuoi, "so": 1}
        return None

    def bam(self, x, hau_dieu_kien=None, han_hau=10, han_tim=10, cho_tat=False):
        khoa = x["khoa"] if isinstance(x, dict) else x
        if not self._hien(khoa):
            raise cdp_studio.LoiThaoTac(khoa, "không thấy")
        if khoa == "mhkt_mo_sua":
            self.soan, self.hang = "soan", list(self._v().get("mhkt") or [])
        elif khoa == "mhkt_nhap_trong":
            self.soan = "chon"
        elif khoa == "mhkt_chon_video":
            if self.nguon.get(x.get("vid")):
                self.soan, self.hang = "soan", ["Video: Phù hợp nhất với người xem", "Đăng ký: kênh"]
            else:
                self.khong_nguon = True
        elif khoa == "mhkt_dong_chon":
            self.soan = "soan"
        elif khoa == "mhkt_mau":
            self.hang = ["Đăng ký: kênh", "Video: Phù hợp nhất với người xem"]
        elif khoa == "mhkt_luu":
            self.dem_luu += 1
            if not self.luu_hong:
                self._v()["mhkt"] = list(self.hang)
            self.soan = None
        elif khoa == "hop_con_huy":
            self.soan = None
        if hau_dieu_kien is not None and not hau_dieu_kien():
            raise cdp_studio.LoiThaoTac(khoa, "hậu điều kiện không đạt")
        return x if isinstance(x, dict) else {"khoa": khoa}

    def go_tho(self, khoa, chu, xoa=True, han_tim=10):
        pass

    def doc_chu(self, x, han=5):
        khoa = x["khoa"] if isinstance(x, dict) else x
        if khoa == "mhkt_mau":
            return "1 video, 1 đăng ký" if (x.get("thu") if isinstance(x, dict) else 0) == 1 else "mẫu khác"
        if khoa == "mhkt_hop_chon":
            return "Chọn một video cụ thể" + (" Video này không có màn hình kết thúc để nhập"
                                               if self.khong_nguon else "")
        return ""

    def doc_tat_ca(self, khoa):
        return [{"chu": h} for h in self.hang] if khoa == "mhkt_phan_tu" and self.soan == "soan" else []

    def phim(self, ten, n=1, modifiers=0):
        pass

    def ghi_bang_chung(self, nhan):
        self.bang_chung.append(nhan)
        return {}

    def dong(self):
        pass


def _may(tmp_path, trang):
    m = mdd.MayDangDom(K, cdp_studio.doc_bo_chon(), lambda: trang,
                       mdd.SoVideoId(str(tmp_path / "so.json")), lambda *a, **k: True, str(tmp_path / "DONE"),
                       nhat_ky=lambda s: None, bay_gio=lambda: datetime(2026, 10, 1, 3, 5), ngu=lambda s: None,
                       duong_uc=str(tmp_path / "uc.json"), duong_dodang=str(tmp_path / "dodang.json"),
                       han_mhkt=1, thu_muc_chi_so=str(tmp_path / "chi-so"))
    return m


class TestBuMotVideo:
    def test_nhap_tu_video_da_co_mhkt_luu_doc_lai_ghi_ok_bu(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd01": {"dai": 800}}, nguon_co_mhkt={"FAKEnguon01": True})
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/0014", **_muc("FAKEnguon01", "ok:mau"))
        m.so.cap_nhat(K + "/0007", **_muc("FAKEddddd01", "bo"))
        kq = m.bu_mhkt_mot(K + "/0007", "FAKEddddd01")
        assert kq["ket"] == "ok" and tr.dem_luu == 1
        so = m.so.lay(K + "/0007")
        assert so["mhkt"] == "ok:bu" and so["mhkt_bu_cach"] == "nhap" and so["mhkt_nguon"] == "FAKEnguon01"
        assert so["mhkt_bu_ngay"] == "2026-10-01" and "Đăng ký" in so["mhkt_bu_doc_lai"]
        assert tr.video["FAKEddddd01"]["mhkt"], "Studio giả phải thật sự lưu MHKT"
        assert any(b.startswith("bu-mhkt-doc-lai-") for b in tr.bang_chung), "đọc lại phải chụp bằng chứng"

    def test_khong_co_nguon_thi_dung_mau(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd02": {"dai": 800}})
        m = _may(tmp_path, tr)
        m.so.cap_nhat("TL2-T7/0004", **_muc("FAKEddddd02", "bo"))
        m.kenh = "TL2-T7"
        assert m.bu_mhkt_mot("TL2-T7/0004", "FAKEddddd02")["ket"] == "ok"
        so = m.so.lay("TL2-T7/0004")
        assert so["mhkt"] == "ok:bu" and so["mhkt_bu_cach"] == "mau"

    def test_nguon_bao_khong_co_mhkt_thi_lui_mau(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd03": {"dai": 800}}, nguon_co_mhkt={"FAKEnguon02": False})
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/0001", **_muc("FAKEnguon02", "ok"))
        m.so.cap_nhat(K + "/0008", **_muc("FAKEddddd03", "bo"))
        assert m.bu_mhkt_mot(K + "/0008", "FAKEddddd03")["ket"] == "ok"
        assert m.so.lay(K + "/0008")["mhkt_bu_cach"] == "mau"

    def test_da_co_san_khong_luu_gi(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd04": {"dai": 800, "mhkt": ["Video: x"]}})
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/0009", **_muc("FAKEddddd04", "bo"))
        assert m.bu_mhkt_mot(K + "/0009", "FAKEddddd04")["ket"] == "ok"
        assert tr.dem_luu == 0 and m.so.lay(K + "/0009")["mhkt_bu_cach"] == "co-san"

    def test_video_khong_con_ton_tai(self, tmp_path):
        tr = TrangSuaGia({})
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/0010", **_muc("FAKEddddd05", "bo"))
        assert m.bu_mhkt_mot(K + "/0010", "FAKEddddd05")["ket"] == "khong-the"
        so = m.so.lay(K + "/0010")
        assert so["mhkt"] == "khong-the" and "không còn" in so["mhkt_bu_ly_do"]
        assert mdd.hang_bu_mhkt(m.so.doc(), K, "2026-10-02") == [], "khong-the không vào hàng bù nữa"

    def test_video_duoi_25_giay_va_shorts(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd06": {"dai": 20}, "FAKEddddd07": {"dai": 58, "shorts": True}})
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/0011", **_muc("FAKEddddd06", "bo"))
        m.so.cap_nhat(K + "/0012", **_muc("FAKEddddd07", "bo"))
        assert m.bu_mhkt_mot(K + "/0011", "FAKEddddd06")["ket"] == "khong-the"
        assert "25 giây" in m.so.lay(K + "/0011")["mhkt_bu_ly_do"]
        assert m.bu_mhkt_mot(K + "/0012", "FAKEddddd07")["ket"] == "khong-the"
        assert "Shorts" in m.so.lay(K + "/0012")["mhkt_bu_ly_do"]
        assert tr.dem_luu == 0

    def test_luu_ma_doc_lai_khong_thay_la_loi_dem_sau_thu_lai(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd08": {"dai": 800}}, luu_hong=True)
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/0013", **_muc("FAKEddddd08", "bo"))
        assert m.bu_mhkt_mot(K + "/0013", "FAKEddddd08")["ket"] == "loi"
        so = m.so.lay(K + "/0013")
        assert so["mhkt"] == "bo" and so["mhkt_bu_loi_lan"] == 1 and "đọc lại" in so["mhkt_bu_ly_do"]
        assert mdd.hang_bu_mhkt(m.so.doc(), K, "2026-10-01") == []
        assert mdd.hang_bu_mhkt(m.so.doc(), K, "2026-10-02") == [(K + "/0013", "FAKEddddd08")]

    def test_bu_nhieu_video_ma_thoat(self, tmp_path):
        tr = TrangSuaGia({"FAKEddddd09": {"dai": 800}, "FAKEddddd10": {"dai": 800}},
                         nguon_co_mhkt={"FAKEddddd09": True})
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/a", **_muc("FAKEddddd09", "bo"))
        m.so.cap_nhat(K + "/b", **_muc("FAKEddddd10", "bo"))
        assert m.bu_mhkt([(K + "/a", "FAKEddddd09"), (K + "/b", "FAKEddddd10")]) == mdd.MA_XONG
        assert m.so.lay(K + "/b")["mhkt_bu_cach"] == "nhap", "video bù trước thành nguồn nhập cho video sau"

    def test_canh_khong_cham_vm_logs_that(self, tmp_path):
        that = Path(mdd.THU_MUC_LOG)
        truoc = {p.name: p.stat().st_mtime for p in that.glob("*")} if that.is_dir() else {}
        tr = TrangSuaGia({"FAKEddddd11": {"dai": 800}}, luu_hong=True)
        m = _may(tmp_path, tr)
        m.so.cap_nhat(K + "/x", **_muc("FAKEddddd11", "bo"))
        m.bu_mhkt([(K + "/x", "FAKEddddd11")])
        sau = {p.name: p.stat().st_mtime for p in that.glob("*")} if that.is_dir() else {}
        assert {n: t for n, t in sau.items() if truoc.get(n) != t} == {}, "bài kiểm chạm vm/logs thật"


# ═══ AGENT: lịch bù giờ vắng ═══════════════════════════════════════════════

def _nap_agent(tmp_path):
    spec = importlib.util.spec_from_file_location("agent_bu_mhkt", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC = str(tmp_path / "vm")
    mod.THU_MUC_TIEN_ICH = str(tmp_path / "vm" / "tien-ich")
    (tmp_path / "vm" / "logs").mkdir(parents=True, exist_ok=True)
    return mod


def _luc(h, m):
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, h, m, 0, 0, 0, -1))


def _hom_nay():
    return time.strftime("%Y-%m-%d")


class TestAgentBu:
    CAC = ["TL4-T7", "TL1-T7", "TL2-T7", "TL3-T7"]

    def _hl(self):
        return {k: {"kenh": k, "tu_dang": True, "cach_dang": "dom"} for k in self.CAC}

    def _cau(self, tmp_path, **tt):
        cau = {"thu_muc_du_lieu": str(tmp_path / "vm")}
        base = {"quet_ngay@{0}@{1}".format(k, _hom_nay()): {"lan": 1, "xong": True} for k in self.CAC}
        base.update(tt)
        (tmp_path / "vm" / "trang-thai.json").write_text(json.dumps(base), encoding="utf-8")
        return cau

    def _so(self, tmp_path, so):
        (tmp_path / "vm" / "logs" / "so-video-id.json").write_text(json.dumps(so), encoding="utf-8")

    def _chuan_bi(self, ag, monkeypatch):
        monkeypatch.setattr(ag, "van_ipv4_mo", lambda: False)
        monkeypatch.setattr(ag, "tim_chrome", lambda ch: "C:/x/{0}.exe".format(ch.get("kenh")))
        monkeypatch.setattr(ag, "_chrome_dang_chay", lambda c: True)
        monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: None)
        monkeypatch.setattr(ag, "ghi_che_do_mat_cao", lambda ch, q, *a, **k: None)
        khoa = []
        monkeypatch.setattr(ag, "giu_khoa_may_chung",
                            lambda viec="", kenh="", uu_tien=1: khoa.append((viec, kenh)) or True)
        monkeypatch.setattr(ag, "nha_khoa_may_chung", lambda: khoa.append("nha"))
        goi = []

        def chay_con(duong, kenh, nhan, han_giay, co_gi_them=()):
            goi.append((os.path.basename(duong), kenh, han_giay, tuple(co_gi_them)))
            return "xong", 0
        return khoa, goi, chay_con

    def test_khung_gio_va_nhuong(self, tmp_path):
        ag = _nap_agent(tmp_path)
        hl = self._hl()
        cau = self._cau(tmp_path)
        assert ag.han_bu_mhkt(cau, hl, self.CAC, "TL1-T7", _luc(1, 30))[0] == 0, "trước 02:00"
        assert ag.han_bu_mhkt(cau, hl, self.CAC, "TL1-T7", _luc(4, 58))[0] == 0, "sau 05:00 − 5'"
        assert ag.han_bu_mhkt(cau, hl, self.CAC, "TL1-T7", _luc(3, 57))[0] == 0, "phút :55–:05"
        con, _ = ag.han_bu_mhkt(cau, hl, self.CAC, "TL1-T7", _luc(4, 10))
        assert con == pytest.approx(30 * 60), "trần 30 phút"
        con, _ = ag.han_bu_mhkt(cau, hl, self.CAC, "TL1-T7", _luc(4, 40))
        assert con == pytest.approx(15 * 60), "kết thúc trước 05:00 − 5'"
        # Quét của chính kênh chưa xong → chờ.
        cau2 = self._cau(tmp_path, **{"quet_ngay@TL1-T7@" + _hom_nay(): {"lan": 1, "xong": False, "luc": _luc(2, 40)}})
        assert ag.han_bu_mhkt(cau2, hl, self.CAC, "TL1-T7", _luc(3, 10))[0] == 0
        # Quét kênh khác 03:10 sắp tới → nhường; còn xa → hạn tới trước giờ quét.
        cau3 = self._cau(tmp_path, **{"quet_ngay@TL2-T7@" + _hom_nay(): {}})
        assert ag.han_bu_mhkt(cau3, hl, self.CAC, "TL1-T7", _luc(3, 6))[0] == 0
        con, _ = ag.han_bu_mhkt(cau3, hl, self.CAC, "TL1-T7", _luc(2, 45))
        assert con == pytest.approx(25 * 60)
        # Phiên kênh 04:00 chưa chạy → nhường 20', hạn kết thúc trước phiên 10'.
        cau4 = self._cau(tmp_path, **{"phien_muc_tieu@TL3-T7@" + _hom_nay(): "04:00"})
        assert ag.han_bu_mhkt(cau4, hl, self.CAC, "TL1-T7", _luc(3, 45))[0] == 0
        con, _ = ag.han_bu_mhkt(cau4, hl, self.CAC, "TL1-T7", _luc(3, 20))
        assert con == pytest.approx(30 * 60)
        cau5 = self._cau(tmp_path, **{"phien_muc_tieu@TL3-T7@" + _hom_nay(): "04:00",
                                      "phien_cuoi@TL3-T7": _hom_nay()})
        assert ag.han_bu_mhkt(cau5, hl, self.CAC, "TL1-T7", _luc(3, 45))[0] > 0, "phiên đã chạy thì thôi nhường"

    def test_chay_mot_kenh_giu_khe_truyen_tran_3(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        hl = self._hl()
        cau = self._cau(tmp_path)
        self._so(tmp_path, {"TL1-T7/0007": _muc("FAKEeeeee01"), "TL2-T7/0004": _muc("FAKEeeeee02"),
                            "TL4-T7/0001": _muc("FAKEeeeee03", "ok:nhap")})
        khoa, goi, chay_con = self._chuan_bi(ag, monkeypatch)
        assert ag.chay_bu_mhkt(cau, hl, self.CAC, bay_gio=_luc(4, 10), chay_con=chay_con) is True
        ten, kenh, han, co = goi[0]
        assert ten == "may_dang_dom.py" and kenh == "TL1-T7"
        assert "--bu-mhkt" in co and "--trong-phien" in co and co[co.index("--toi-da-video") + 1] == "3"
        assert khoa[0] == ("bu_mhkt", "TL1-T7") and khoa[-1] == "nha"
        assert han <= 35 * 60
        # Nhịp kế (sau chu kỳ): kênh khác chưa chạy lượt nào được trước.
        assert ag.chay_bu_mhkt(cau, hl, self.CAC, bay_gio=_luc(4, 16), chay_con=chay_con) is True
        assert goi[1][1] == "TL2-T7"
        tt = ag._doc_trang_thai(cau)
        assert tt["bu_mhkt@TL1-T7@" + _hom_nay()] == 1

    def test_khong_hang_ngoai_khung_hoac_tat(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path)
        hl = self._hl()
        cau = self._cau(tmp_path)
        khoa, goi, chay_con = self._chuan_bi(ag, monkeypatch)
        self._so(tmp_path, {"TL1-T7/0001": _muc("FAKEeeeee04", "ok:mau")})
        assert ag.chay_bu_mhkt(cau, hl, self.CAC, bay_gio=_luc(4, 10), chay_con=chay_con) is False
        self._so(tmp_path, {"TL1-T7/0007": _muc("FAKEeeeee05")})
        ag._BU_MHKT["luc"] = 0
        assert ag.chay_bu_mhkt(cau, hl, self.CAC, bay_gio=_luc(12, 10), chay_con=chay_con) is False
        ag._BU_MHKT["luc"] = 0
        hl["TL1-T7"]["bu_mhkt"] = False
        assert ag.chay_bu_mhkt(cau, hl, self.CAC, bay_gio=_luc(4, 10), chay_con=chay_con) is False
        assert goi == [] and khoa == []

    def test_quet_vat_qua_nua_dem_tinh_ngay_bat_dau(self, tmp_path):
        """TL3 bắt đầu 23:48, xong 00:00:52 — bảng ghi 23:59 hôm trước vẫn là ĐỦ cho
        ngày bắt đầu (trước đây so với ngày lúc kết thúc → 'chưa đủ' oan)."""
        ag = _nap_agent(tmp_path)
        (tmp_path / "vps.json").write_text("{}", encoding="utf-8")
        cs = tmp_path / "CHANNEL" / "TL3-T7" / "chi-so"
        cs.mkdir(parents=True)
        hom_qua = time.time() - 86400
        for ten in ("bang-tom-tat.csv", "kenh-theo-ngay.csv"):
            (cs / ten).write_text("x", encoding="utf-8")
            os.utime(cs / ten, (hom_qua, hom_qua))
        cau = {"thu_muc_du_lieu": str(tmp_path / "vm")}
        ngay_bat_dau = time.strftime("%Y-%m-%d", time.localtime(hom_qua))
        assert ag._du_lieu_kenh_da_ve_hom_nay(cau, "TL3-T7") is False
        assert ag._du_lieu_kenh_da_ve_hom_nay(cau, "TL3-T7", ngay=ngay_bat_dau) is True
        hai_ngay = time.strftime("%Y-%m-%d", time.localtime(hom_qua - 86400))
        assert ag._du_lieu_kenh_da_ve_hom_nay(cau, "TL3-T7", ngay=hai_ngay) is True
        cu = hom_qua - 2 * 86400
        for ten in ("bang-tom-tat.csv", "kenh-theo-ngay.csv"):
            os.utime(cs / ten, (cu, cu))
        assert ag._du_lieu_kenh_da_ve_hom_nay(cau, "TL3-T7", ngay=ngay_bat_dau) is False
