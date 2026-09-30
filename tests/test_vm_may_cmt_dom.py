"""Máy bình luận DOM (29/09/2026): bình luận mồi + GHIM + trả lời bình luận mới
trong Chrome kênh, không OAuth. Không mạng, không Chrome — trang giả `TrangGia`
mô phỏng trang xem YouTube và trang Bình luận của Studio theo DOM đã đo thật.
Mọi đường ghi (sổ, replied, CHANNEL/…) trỏ vào thư mục tạm."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import may_cmt_dom as mcd  # noqa: E402

BO = cdp_studio.doc_bo_chon()
VID = "vff186160a1"
HANDLE_URL = "https://www.youtube.com/@%E3%82%84%E3%81%95-l6n"
SEED = "私はハーブを育てています🌱\n\nあなたは普段、庭いじりをしますか？\nぜひコメントで教えてください。"


# ═══ HÀM THUẦN ═══════════════════════════════════════════════════════════

class TestHamThuan:
    def test_loai_binh_luan(self):
        assert mcd.loai_binh_luan("素敵な動画ありがとうございます") == ""
        assert mcd.loai_binh_luan("Video hay quá, cảm ơn bạn") == ""
        assert mcd.loai_binh_luan("xem thêm tại https://abc.xyz") == "link"
        assert mcd.loai_binh_luan("ghé www.kenh.com nhé") == "link"
        assert mcd.loai_binh_luan("sub4sub pls") == "spam"
        assert mcd.loai_binh_luan("チャンネル登録お願いします！") == "spam"
        assert mcd.loai_binh_luan("お前はバカだ") == "xuc_pham"
        assert mcd.loai_binh_luan("đồ óc chó") == "xuc_pham"
        assert mcd.loai_binh_luan("   ") == "rong"
        assert mcd.loai_binh_luan("🌱🌱") == "rong"
        assert mcd.loai_binh_luan("wowwwwwwwwwwwwwww") == "lap_ky_tu"
        # "cút" là từ riêng — không bắt nhầm chữ chứa nó
        assert mcd.loai_binh_luan("tôi thích nghe nhạc") == ""

    def test_khop_noi_dung_bo_bieu_tuong_va_xuong_dong(self):
        doc = "私はハーブを育てています\n\nあなたは普段、庭いじりをしますか？ ぜひコメントで教えてください。"
        assert mcd.khop_noi_dung(SEED, doc)
        assert mcd.khop_noi_dung(SEED, doc[:30])  # trang thu gọn "Đọc thêm"
        assert not mcd.khop_noi_dung(SEED, "まったく別のコメントです。まったく別のコメントです。")
        assert not mcd.khop_noi_dung(SEED, "")

    def test_id_binh_luan(self):
        assert mcd.rut_comment_id(["https://www.youtube.com/watch?v=x&lc=Ugy96qh6Bbosuo_JIGZ4AaABAg"]) \
            == "Ugy96qh6Bbosuo_JIGZ4AaABAg"
        assert mcd.id_luong({"comment_id": "UgzABCDEFGHIJKLMNOP"}) == "UgzABCDEFGHIJKLMNOP"
        assert mcd.id_luong({"hrefs": ["https://youtube.com/@a"]}) == ""
        assert mcd.khoa_binh_luan("", "a", "chữ").startswith("h:")
        assert mcd.khoa_binh_luan("Ugx1", "a", "chữ") == "Ugx1"

    def test_la_cua_kenh(self):
        assert mcd.la_cua_kenh(HANDLE_URL, "", "@やさ-l6n")
        assert mcd.la_cua_kenh("http://www.youtube.com/channel/UCabcdefghijklmnopqrstuv", "UCabcdefghijklmnopqrstuv")
        assert not mcd.la_cua_kenh("https://www.youtube.com/@nguoi-xem", "UCabcdefghijklmnopqrstuv", "@やさ-l6n")
        assert not mcd.la_cua_kenh("", "UCx", "@a")

    def test_prompt_theo_ngon_ngu_kenh_khong_theo_duoi_ten(self):
        p = mcd.tao_prompt("Nice video!", mcd.ten_ngon_ngu("ja"), "polite", "【雑学】題", "mô tả")
        assert "Always reply in Japanese" in p and "Viewer comment: Nice video!" in p
        assert "【雑学】題" in p and "no emojis" in p
        assert mcd.ten_ngon_ngu("vi") == "Vietnamese" and mcd.ten_ngon_ngu("pt-BR") == "Portuguese"
        assert "SAME language" in mcd.tao_prompt("x", "")

    def test_lam_sach_tra_loi(self):
        assert mcd.lam_sach_tra_loi("「ありがとうございます😊」") == "ありがとうございます"
        assert "http" not in mcd.lam_sach_tra_loi("xem https://a.com nhé")
        assert len(mcd.lam_sach_tra_loi("a" * 900)) == 500

    def test_bo_dong_can_ghim(self):
        chu = ("# Việc tay\n\n- [2026-09-29] **A** — https://www.youtube.com/watch?v=AAAAAAAAAAA\n  > câu 1\n"
               "- [2026-09-29] **B** — https://www.youtube.com/watch?v=" + VID + "\n  > câu 2\n")
        moi, so = mcd.bo_dong_can_ghim(chu, VID)
        assert so == 1 and VID not in moi and "câu 2" not in moi
        assert "AAAAAAAAAAA" in moi and "câu 1" in moi
        assert mcd.bo_dong_can_ghim(chu, "")[1] == 0

    def test_phan_tich_lich(self):
        assert mcd.phan_tich_lich("30/09/2026", "20:00") == datetime(2026, 9, 30, 20, 0)
        assert mcd.phan_tich_lich("2026-09-28", "") == datetime(2026, 9, 28)
        assert mcd.phan_tich_lich("", "20:00") is None


def _hang(ma, ngay, gio, tt="ĐÃ ĐĂNG", vid="", td="tiêu đề"):
    return {"Mã gói": ma, "Ngày đăng": ngay, "Giờ đăng": gio, "Tiêu đề": td, "Mô tả": "m",
            "Trạng thái đăng": tt, "Video ID": vid}


class TestChonGoi:
    BAY = datetime(2026, 9, 29, 21, 0)

    def test_loc_trang_thai_cua_so_va_so(self):
        hang = [_hang("K-0001", "28/09/2026", "10:30", "ĐÃ ĐĂNG (tay)"),
                _hang("K-0002", "30/09/2026", "20:00", "ĐÃ ĐĂNG", "VIDTUONGLAI"),   # chưa tới giờ
                _hang("K-0003", "10/09/2026", "10:00", "ĐÃ ĐĂNG"),                  # quá 7 ngày
                _hang("K-0004", "29/09/2026", "08:00", ""),                         # chưa đăng
                _hang("K-0005", "29/09/2026", "09:00", "ĐÃ ĐĂNG", "VIDDAGHIM01")]
        so_cmt = {"VIDDAGHIM01": {"da_ghim": "2026-09-29 10:00"}}
        ra = mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY)
        assert [g["ma"] for g in ra] == ["K-0001"]
        # --ma bỏ cửa sổ ngày nhưng vẫn tôn trọng sổ
        assert [g["ma"] for g in mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY, ma="K-0003")] == ["K-0003"]
        assert mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY, ma="K-0005") == []

    def test_lich_so_video_thang_ngay_ke_hoach_va_id_tu_so(self):
        hang = [_hang("K-0007", "", "", "ĐÃ ĐĂNG")]
        so_video = {"K/K-0007": {"video_id": "vcfe05f792c", "lich": "29/09/2026 20:00"}}
        ra = mcd.chon_goi_can_moi(hang, so_video, {}, "K", self.BAY)
        assert ra and ra[0]["video_id"] == "vcfe05f792c" and ra[0]["lich"] == datetime(2026, 9, 29, 20, 0)

    def test_so_cmt_theo_ma_khi_ke_hoach_chua_co_video_id(self):
        hang = [_hang("K-0005", "28/09/2026", "17:34", "ĐÃ ĐĂNG (tay)")]
        so_cmt = {VID: {"kenh": "K", "ma": "K-0005", "da_ghim": "x"}}
        assert mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY) == []

    def test_cho_xac_minh_thu_lai_moi_ngay_mot_lan(self):
        hang = [_hang("K-0005", "28/09/2026", "17:34", "ĐÃ ĐĂNG", VID)]
        so_cmt = {VID: {"trang_thai": "cho-xac-minh", "ghim_cho_xac_minh": "2026-09-29 20:40:00"}}
        assert mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY) == []
        assert len(mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY + timedelta(days=1))) == 1

    def test_ket_thuc_khong_chon_lai(self):
        hang = [_hang("K-0005", "28/09/2026", "17:34", "ĐÃ ĐĂNG", VID)]
        for tt in ("tat-binh-luan", "ghim-khac", "khong-co-van-ban"):
            assert mcd.chon_goi_can_moi(hang, {}, {VID: {"trang_thai": tt}}, "K", self.BAY) == []
        assert mcd.chon_goi_can_moi(hang, {}, {VID: {"lan_thu_ghim": mcd.TRAN_THU_GHIM}}, "K", self.BAY) == []

    def test_ghim_tat_thi_da_moi_la_xong(self):
        # 30/09/2026: ghim_dom=false → video đã có mồi không vào hàng nữa (vòng 20 phút TL3-0005)
        hang = [_hang("K-0005", "29/09/2026", "16:00", "ĐÃ ĐĂNG", VID)]
        so_cmt = {VID: {"da_dang_moi": "2026-09-29 16:08:32", "trang_thai": "da-dang", "ghim": "tat"}}
        assert mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY, ghim_bat=False) == []
        # chưa có mồi thì vẫn làm mồi dù ghim tắt
        assert len(mcd.chon_goi_can_moi(hang, {}, {}, "K", self.BAY, ghim_bat=False)) == 1
        # bật ghim lại → xét lại để ghim
        assert len(mcd.chon_goi_can_moi(hang, {}, so_cmt, "K", self.BAY, ghim_bat=True)) == 1


class TestVanBanMoi:
    def test_done_roi_projects_roi_so(self, tmp_path):
        luot = tmp_path / "PROJECTS" / "AUTO" / "K" / "0005"
        luot.mkdir(parents=True)
        (luot / "1-binh-luan.txt").write_text("từ lượt", encoding="utf-8")
        (luot / "1-tieu-de.txt").write_text("TITLE: Tiêu đề A\nTHUMB: x\n", encoding="utf-8")
        assert mcd.doc_van_ban_moi(str(tmp_path), "K", "K-0005", tieu_de="Tiêu đề A") == "từ lượt"
        # tiêu đề lượt KHÁC kế hoạch → không dùng, lùi bản sao trong sổ
        assert mcd.doc_van_ban_moi(str(tmp_path), "K", "K-0005", {"van_ban": "sổ"}, tieu_de="Khác") == "sổ"
        done = tmp_path / "DONE" / "K" / "K-0005"
        done.mkdir(parents=True)
        (done / "1-binh-luan.txt").write_text("từ DONE\r\n", encoding="utf-8")
        assert mcd.doc_van_ban_moi(str(tmp_path), "K", "K-0005", tieu_de="Khác") == "từ DONE"


class TestSo:
    def test_so_cmt_nguyen_tu(self, tmp_path):
        so = mcd.SoCmt(str(tmp_path / "logs" / "cmt-dom.json"))
        so.cap_nhat(VID, da_dang_moi="x")
        so.cap_nhat(VID, da_ghim="y")
        assert so.lay(VID)["da_dang_moi"] == "x" and so.lay(VID)["da_ghim"] == "y"
        assert not list((tmp_path / "logs").glob("*.tam"))

    def test_replied_chung_dinh_dang_may_cmt(self, tmp_path):
        (tmp_path / "K.txt").write_text("Ugx_cu\n", encoding="utf-8")
        s = mcd.SoDaTraLoi("K", str(tmp_path))
        s.them("Ugx_moi")
        s.them("Ugx_moi")
        assert (tmp_path / "K.txt").read_text(encoding="utf-8").split("\n") == ["Ugx_cu", "Ugx_moi"]
        assert s.co("Ugx_cu")


# ═══ TRANG GIẢ ═══════════════════════════════════════════════════════════

class _CdpGia:
    def __init__(self, tr):
        self.tr = tr

    def goi(self, method, params=None, sid=None, han=30):
        if method == "Input.insertText":
            self.tr.go_vao((params or {}).get("text", ""))
        return {}


class TrangGia:
    """Trang xem + Studio Bình luận theo DOM đo 29/09 (chỉ trạng thái cần cho luồng)."""

    def __init__(self, luong_xem=None, luong_sc=None, xac_minh=False, tat=False):
        self.trang = ""
        self.luong_xem = luong_xem if luong_xem is not None else []
        self.luong_sc = luong_sc if luong_sc is not None else []
        self.xac_minh = xac_minh
        self.tat = tat
        self.hop_mo = False
        self.dem = ""
        self.menu = self.xn = self.hop_xm = False
        self.tra_loi_cho = None
        self.da_gui = []
        self.da_bam = []
        self.cdp = _CdpGia(self)
        self.sid = "S"
        self.id_moi = 0

    # hợp đồng TrangStudio
    def mo(self, url, cho_khoa=None, han=60):
        self.trang = "xem" if "watch?v=" in url else "studio"
        self.hop_mo = self.menu = self.xn = self.hop_xm = False
        self.tra_loi_cho = None
        return True

    def _pt(self, khoa, **them):
        return dict({"khop": True, "khoa": khoa, "id": khoa, "cach": "chon#1",
                     "rect": {"x": 10, "y": 10, "w": 50, "h": 20}}, **them)

    def tim(self, khoa, han=10.0, hien=True, cho_tat=False, trong=None, thu=0):
        x, s = self.trang == "xem", self.trang == "studio"
        co = {
            "xem_o_mo": x and not self.tat and not self.hop_mo,
            "xem_o_go": x and self.hop_mo,
            "xem_gui": x and self.hop_mo and bool(self.dem),
            "xem_huy": x and self.hop_mo,
            "xem_bl_khung": x and not self.tat,
            "xem_bl_tat": x and self.tat,
            "xem_luong": x,
            "xem_menu": x and trong is not None,
            "xem_menu_ghim": self.menu,
            "xem_xac_nhan_ghim": self.xn,
            "xem_hop_xac_minh": self.hop_xm,
            "xem_hop_xac_minh_huy": self.hop_xm,
            "sc_luong": s and bool(self.luong_sc),
            "sc_trong": s and not self.luong_sc,
            "sc_khung": s,
            "sc_nut_tra_loi": s and trong is not None,
            "sc_o_tra_loi": s and trong is not None and self.tra_loi_cho == trong.get("id"),
            "sc_gui_tra_loi": s and trong is not None and self.tra_loi_cho == trong.get("id") and bool(self.dem),
            "sc_huy_tra_loi": s and trong is not None and self.tra_loi_cho == trong.get("id"),
        }.get(khoa, False)
        if not co:
            return None
        return self._pt(khoa, luong=(trong or {}).get("id"))

    def co(self, khoa, **kw):
        return self.tim(khoa, han=0, **kw) is not None

    def bam(self, pt, hau_dieu_kien=None, han_hau=10.0, han_tim=10.0, cho_tat=False):
        if not isinstance(pt, dict):
            k = pt
            pt = self.tim(k)
            if not pt:
                raise cdp_studio.LoiThaoTac(k, "không thấy")
        k = pt["khoa"]
        self.da_bam.append(k)
        if k == "xem_o_mo":
            self.hop_mo = True
        elif k == "xem_gui":
            self.id_moi += 1
            self.luong_xem.insert(0, {"id": "t%d" % self.id_moi, "noi_dung": self.dem.replace("🌱", ""),
                                      "tac_gia_href": HANDLE_URL, "ghim": False,
                                      "hrefs": [HANDLE_URL, "https://www.youtube.com/watch?v=%s&lc=UgxMOI_abcdefgh%d" % (VID, self.id_moi)]})
            self.da_gui.append(self.dem)
            self.hop_mo, self.dem = False, ""
        elif k == "xem_menu":
            self.menu = True
        elif k == "xem_menu_ghim":
            self.menu = False
            if self.xac_minh:
                self.hop_xm = True
            else:
                self.xn = True
        elif k == "xem_xac_nhan_ghim":
            self.xn = False
            for t in self.luong_xem:
                if t["id"] == "t%d" % self.id_moi or t.get("cua_minh"):
                    t["ghim"] = True
                    break
        elif k == "xem_hop_xac_minh_huy":
            self.hop_xm = False
        elif k == "sc_nut_tra_loi":
            self.tra_loi_cho = pt["luong"]
        elif k == "sc_gui_tra_loi":
            for t in self.luong_sc:
                if t["id"] == self.tra_loi_cho:
                    t.setdefault("cac_noi_dung", [t["noi_dung"]]).append(self.dem)
            self.da_gui.append(self.dem)
            self.tra_loi_cho, self.dem = None, ""
        elif k == "sc_huy_tra_loi":
            self.tra_loi_cho, self.dem = None, ""
        if hau_dieu_kien is not None and not hau_dieu_kien():
            raise cdp_studio.LoiThaoTac(k, "bấm xong nhưng hậu điều kiện không đạt")
        return pt

    def go_vao(self, chu):
        self.dem += chu

    def _ctrl_a(self):
        pass

    def phim(self, ten, n=1, modifiers=0):
        if ten == "Delete":
            self.dem = ""
        elif ten == "Enter":
            self.dem += "\n"
        elif ten == "Escape":
            self.menu = self.xn = self.hop_xm = False

    def doc_chu(self, pt, han=5.0):
        if pt["khoa"] == "xem_xac_nhan_ghim":
            return "Ghim"
        return self.dem

    def doc_thuoc_tinh(self, pt, ten, han=5.0):
        return ""

    def js_tho(self, bt):
        if "specLuong" in bt:
            ds = self.luong_xem if self.trang == "xem" else self.luong_sc
            return [dict(t, cac_noi_dung=list(t.get("cac_noi_dung") or [t["noi_dung"]])) for t in ds]
        return True

    def _js(self, ham, *doi, **kw):
        return {"rect": {"x": 0, "y": 0, "w": 100, "h": 40}}

    def _chuot_toi(self, x, y):
        pass

    def chup(self, nhan):
        return ""

    def ghi_bang_chung(self, nhan):
        return {}

    def dong(self):
        pass


def _may(tmp_path, tr, cai=None, tra_kenh=None, sinh=None):
    (tmp_path / "CHANNEL" / "K").mkdir(parents=True, exist_ok=True)
    luot = tmp_path / "PROJECTS" / "AUTO" / "K" / "0005"
    luot.mkdir(parents=True, exist_ok=True)
    (luot / "1-binh-luan.txt").write_text(SEED, encoding="utf-8")
    so = mcd.SoCmt(str(tmp_path / "cmt-dom.json"))
    may = mcd.MayCmtDom(
        "K", BO, lambda: tr, so, nhat_ky=lambda s: None, ngu=lambda s: None,
        sinh_tra_loi=sinh or (lambda p: "ありがとうございます"),
        so_tra_loi=mcd.SoDaTraLoi("K", str(tmp_path / "replied")),
        cai=dict({"ngon_ngu": "ja"}, **(cai or {})), goc_tool=str(tmp_path),
        tra_kenh=tra_kenh or (lambda td, vid: [{"video_id": VID, "loai": "cong_khai", "tieu_de": td}]),
        lay_uc=lambda: "UCabcdefghijklmnopqrstuv")
    may.lay_uc()
    return may


GOI = {"ma": "K-0005", "tieu_de": "tiêu đề", "video_id": ""}


class TestMoiVaGhim:
    def test_dang_roi_ghim_roi_xoa_can_ghim(self, tmp_path):
        tr = TrangGia()
        may = _may(tmp_path, tr)
        (tmp_path / "CHANNEL" / "K" / "can-ghim.md").write_text(
            "# x\n\n- [t] **a** — https://www.youtube.com/watch?v=%s\n  > dòng\n" % VID, encoding="utf-8")
        ket = may.dang_va_ghim(dict(GOI))
        assert "ĐÃ GHIM" in ket and "đã đăng mồi" in ket
        assert len(tr.da_gui) == 1 and "\n" in tr.da_gui[0], "nhiều dòng giữ xuống dòng (Shift+Enter)"
        muc = may.so.lay(VID)
        assert muc["da_dang_moi"] and muc["da_ghim"] and muc["comment_id"] == "UgxMOI_abcdefgh1"
        assert VID not in (tmp_path / "CHANNEL" / "K" / "can-ghim.md").read_text(encoding="utf-8")
        assert may.so.lay("_kenh:K")["handle"] == "@やさ-l6n"

    def test_chay_lai_khong_dang_doi_ke_ca_mat_so(self, tmp_path):
        tr = TrangGia()
        may = _may(tmp_path, tr)
        may.dang_va_ghim(dict(GOI))
        assert "đã ghim" in may.dang_va_ghim(dict(GOI))
        # mất sổ: đọc trang thấy bình luận của mình đã ghim → không đăng lại
        (tmp_path / "cmt-dom.json").unlink()
        may2 = _may(tmp_path, tr)
        ket = may2.dang_va_ghim(dict(GOI))
        assert "có sẵn" in ket and "GHIM (sẵn)" in ket
        assert len(tr.da_gui) == 1

    def test_kenh_chua_xac_minh_thi_huy_hop_va_ghi_viec_tay(self, tmp_path):
        tr = TrangGia(xac_minh=True)
        may = _may(tmp_path, tr)
        ket = may.dang_va_ghim(dict(GOI))
        assert "CHƯA GHIM" in ket and "verify" in ket
        assert not tr.hop_xm, "phải bấm Huỷ hộp xác minh"
        muc = may.so.lay(VID)
        assert muc["trang_thai"] == "cho-xac-minh" and not muc.get("da_ghim")
        assert int(muc.get("lan_thu_ghim") or 0) == 0, "không tính vào trần thử ghim"
        cg = (tmp_path / "CHANNEL" / "K" / "can-ghim.md").read_text(encoding="utf-8")
        assert VID in cg and "youtube.com/verify" in cg
        # lượt sau cùng ngày: không đăng lại, không mở lại hộp
        tr.hop_xm = False
        may.so.cap_nhat(VID, trang_thai="da-dang")
        ket2 = may.dang_va_ghim(dict(GOI))
        assert "đã biết hôm nay" in ket2 and len(tr.da_gui) == 1
        assert "xem_menu" not in tr.da_bam[tr.da_bam.index("xem_hop_xac_minh_huy") + 1:]

    def test_chua_cong_khai_khong_dang(self, tmp_path):
        tr = TrangGia()
        may = _may(tmp_path, tr, tra_kenh=lambda td, v: [{"video_id": VID, "loai": "da_len_lich", "tieu_de": td}])
        assert "chưa công khai" in may.dang_va_ghim(dict(GOI))
        assert tr.da_gui == [] and tr.trang == ""

    def test_khong_thay_video_tren_kenh(self, tmp_path):
        may = _may(tmp_path, TrangGia(), tra_kenh=lambda td, v: [])
        assert "chưa thấy video" in may.dang_va_ghim(dict(GOI))

    def test_da_co_ghim_khac_thi_khong_dang(self, tmp_path):
        tr = TrangGia(luong_xem=[{"id": "x", "noi_dung": "chủ kênh tự ghim tay", "ghim": True,
                                  "tac_gia_href": HANDLE_URL, "hrefs": []}])
        may = _may(tmp_path, tr)
        assert "GHIM khác" in may.dang_va_ghim(dict(GOI))
        assert tr.da_gui == [] and may.so.lay(VID)["trang_thai"] == "ghim-khac"

    def test_tat_binh_luan(self, tmp_path):
        tr = TrangGia(tat=True)
        may = _may(tmp_path, tr)
        assert "TẮT bình luận" in may.dang_va_ghim(dict(GOI))
        assert may.so.lay(VID)["trang_thai"] == "tat-binh-luan"

    def test_da_gui_ma_khong_doc_thay_thi_khong_gui_lai(self, tmp_path):
        tr = TrangGia()
        may = _may(tmp_path, tr)
        may.so.cap_nhat(VID, lan_gui=1, trang_thai="dang-gui")
        ket = may.dang_va_ghim(dict(GOI))
        assert "không gửi lại" in ket and tr.da_gui == []

    def test_ghim_dom_tat_thi_dang_mo_nhung_khong_ghim(self, tmp_path):
        """Chủ dự án 29/09/2026: bình luận được thì cứ bình luận, GHIM để tối ưu sau."""
        tr = TrangGia()
        may = _may(tmp_path, tr, cai={"ghim_dom": False})
        ket = may.dang_va_ghim(dict(GOI))
        assert "đã đăng mồi" in ket and "ghim TẮT" in ket and "ĐÃ GHIM" not in ket
        assert len(tr.da_gui) == 1
        muc = may.so.lay(VID)
        assert muc.get("ghim") == "tat" and not muc.get("da_ghim")
        assert not (tmp_path / "CHANNEL" / "K" / "can-ghim.md").exists()
        assert "xem_menu" not in tr.da_bam and "xem_menu_ghim" not in tr.da_bam
        assert not muc.get("lan_thu_ghim")


class TestTraLoi:
    def _luong(self):
        return [
            {"id": "a", "comment_id": "UgxCHU", "noi_dung": "cảm ơn mọi người", "tac_gia_href": HANDLE_URL,
             "la_chu": True},
            {"id": "b", "comment_id": "UgxSPAM", "noi_dung": "xem kênh tôi https://spam.xyz",
             "tac_gia_href": "https://www.youtube.com/@spam"},
            {"id": "c", "comment_id": "UgxMOT", "noi_dung": "とても参考になりました",
             "tac_gia_href": "https://www.youtube.com/@a"},
            {"id": "d", "comment_id": "UgxHAI", "noi_dung": "面白かったです",
             "tac_gia_href": "https://www.youtube.com/@b"},
        ]

    def test_tra_loi_toi_da_bo_chu_kenh_va_spam(self, tmp_path):
        tr = TrangGia(luong_sc=self._luong())
        de_bai = []
        gian = []
        may = _may(tmp_path, tr, sinh=lambda p: de_bai.append(p) or "「ありがとうございます😊」")
        may.ngu = lambda s: gian.append(s)
        kq = may.tra_loi(2)
        assert kq["da_tra_loi"] == 2 and kq["bo_qua"] == 1
        assert tr.da_gui == ["ありがとうございます", "ありがとうございます"], "đã làm sạch ngoặc + biểu tượng"
        assert all("Always reply in Japanese" in p for p in de_bai)
        assert any(20 <= g <= 60 for g in gian), "giãn 20–60s giữa hai trả lời"
        replied = (tmp_path / "replied" / "K.txt").read_text(encoding="utf-8").split("\n")
        assert {"UgxCHU", "UgxSPAM", "UgxMOT", "UgxHAI"} <= set(replied)
        assert tr.luong_sc[1].get("cac_noi_dung") is None, "spam để nguyên, không trả lời"

    def test_khong_tra_loi_lai(self, tmp_path):
        tr = TrangGia(luong_sc=self._luong())
        may = _may(tmp_path, tr)
        may.tra_loi(10)
        n = len(tr.da_gui)
        may2 = _may(tmp_path, tr)
        assert may2.tra_loi(10)["da_tra_loi"] == 0 and len(tr.da_gui) == n

    def test_tram_khong_sinh_duoc_thi_bo_qua_khong_ghi_so(self, tmp_path):
        tr = TrangGia(luong_sc=self._luong()[2:3])
        may = _may(tmp_path, tr, sinh=lambda p: None)
        kq = may.tra_loi(5)
        assert kq["da_tra_loi"] == 0 and kq["loi"] == 1 and tr.da_gui == []
        assert not (tmp_path / "replied" / "K.txt").exists()

    def test_trong_thi_khong_lam_gi(self, tmp_path):
        may = _may(tmp_path, TrangGia(luong_sc=[]))
        assert may.tra_loi(10) == {"da_tra_loi": 0, "bo_qua": 0, "loi": 0}


class TestDocCaiDat:
    def test_mac_dinh_ghim_dom_tat(self, tmp_path):
        ra = mcd.doc_cai_dat("K", goc_tool=str(tmp_path), thu_muc_vm=str(tmp_path))
        assert ra["ghim_dom"] is False

    def test_doc_ghim_dom_tu_may_ao_json(self, tmp_path):
        (tmp_path / "CHANNEL" / "K").mkdir(parents=True)
        (tmp_path / "CHANNEL" / "K" / "may-ao.json").write_text(
            json.dumps({"ghim_dom": True}), encoding="utf-8")
        ra = mcd.doc_cai_dat("K", goc_tool=str(tmp_path), thu_muc_vm=str(tmp_path))
        assert ra["ghim_dom"] is True


class TestBoChon:
    def test_du_khoa_binh_luan_va_cam_bam_rieng(self):
        pt = BO["phan_tu"]
        for k in ("xem_o_mo", "xem_o_go", "xem_gui", "xem_luong", "xem_menu", "xem_menu_ghim",
                  "xem_xac_nhan_ghim", "xem_hop_xac_minh", "xem_hop_xac_minh_huy", "xem_huy_hieu_ghim",
                  "sc_luong", "sc_trong", "sc_nut_tra_loi", "sc_o_tra_loi", "sc_gui_tra_loi", "sc_huy_tra_loi"):
            assert k in pt, k
        assert not pt["xem_menu_ghim"].get("chon"), "Ghim chỉ chọn theo CHỮ, không theo vị trí trong menu"
        for k in ("xem", "cmt_video", "cmt_chua_phan_hoi"):
            assert k in BO["url"]
        assert "{uc}" in BO["url"]["cmt_chua_phan_hoi"] and "{id}" in BO["url"]["xem"]
        cam = BO["cam_bam_binh_luan"]
        assert "phản hồi" not in [s.lower() for s in cam["aria_chua"]], \
            "nút Phản hồi của bình luận không được bị chặn"
        assert any("gửi ý kiến" in s for s in cam["aria_chua"]), "vẫn chặn nút Gửi ý kiến phản hồi"
        assert cdp_studio.kiem_bo_chon(BO) == []


# ═══ AGENT ═══════════════════════════════════════════════════════════════

def _nap_agent(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("vm_agent_cmt_dom", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "GOC", str(tmp_path))
    (tmp_path / "logs").mkdir(exist_ok=True)
    monkeypatch.setattr(mod, "ghi", lambda s: None)
    monkeypatch.setattr(mod, "_duong_trang_thai", lambda ch: str(tmp_path / "trang-thai.json"))
    mod._GHIM_SOM["luc"] = 0.0
    return mod


class TestAgent:
    def test_chon_may_cmt(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        assert ag.chon_may_cmt(True, True, False) == "dom"
        assert ag.chon_may_cmt(None, True, False) == "dom", "chưa đặt cờ = bật"
        assert ag.chon_may_cmt(True, True, True) == "api", "có token OAuth → API như cũ"
        assert ag.chon_may_cmt(False, True, False) == "api"
        assert ag.chon_may_cmt(True, False, False) == "api", "kênh không tu_dang → không DOM"

    def test_co_token_oauth(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        assert not ag.co_token_oauth("K")
        (tmp_path / "tokens").mkdir()
        (tmp_path / "tokens" / "K.json").write_text("{}", encoding="utf-8")
        assert ag.co_token_oauth("K")

    def test_khoa_moi_hai_dau(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        if str(GOC) not in sys.path:
            sys.path.insert(0, str(GOC))
        from core.vm_cai_dat import MAC_DINH
        for k in ("binh_luan_dom", "cmt_toi_da_phien", "ghim_dom"):
            assert k in ag.KHOA_TU_TOOL and k in MAC_DINH
        assert MAC_DINH["binh_luan_dom"] is True and MAC_DINH["cmt_toi_da_phien"] == 10
        assert MAC_DINH["ghim_dom"] is False

    def test_phien_goi_may_cmt_dom_khi_tu_dang_khong_token(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        goi = []
        monkeypatch.setattr(ag, "quet_studio", lambda ch: "ok")
        monkeypatch.setattr(ag, "quet_trang_chu", lambda ch: "ok")
        monkeypatch.setattr(ag, "lay_loi_thoai", lambda ch: {"lay_duoc": 0})
        monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: goi.append("dong"))
        monkeypatch.setattr(ag, "_chay_mot_lan", lambda duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",):
                            goi.append((Path(duong).name, tuple(co_gi_them))) or ("ok", 0))
        ag.chay_mot_phien({}, {"kenh": "K", "tu_dang": True, "cach_dang": "anh"}, "K")
        assert ("may_cmt_dom.py", ("--mot-lan", "--trong-phien")) in goi
        assert not any(isinstance(g, tuple) and g[0] == "may_cmt.py" for g in goi)
        assert goi[-1] == "dong", "bình luận chạy TRƯỚC khi đóng Chrome"
        goi.clear()
        ag.chay_mot_phien({}, {"kenh": "K", "tu_dang": True, "binh_luan_dom": False}, "K")
        assert any(isinstance(g, tuple) and g[0] == "may_cmt.py" for g in goi)

    def test_video_can_ghim_som(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        bay = time.mktime((2026, 9, 30, 20, 10, 0, 0, 0, -1))
        so_video = {"K/K-0007": {"video_id": "V7", "trang_thai": "xac-nhan", "lich": "30/09/2026 20:00"},
                    "K/K-0008": {"video_id": "V8", "trang_thai": "xac-nhan", "lich": "30/09/2026 20:08"},  # <5'
                    "K/K-0001": {"video_id": "V1", "trang_thai": "xac-nhan", "lich": "20/09/2026 20:00"},  # >72h
                    "K/K-0009": {"video_id": "V9", "trang_thai": "nhap", "lich": "30/09/2026 19:00"},
                    "K2/K2-0001": {"video_id": "W1", "trang_thai": "xac-nhan", "lich": "30/09/2026 20:00"}}
        assert ag.video_can_ghim_som(so_video, {}, "K", bay) == ["K-0007"]
        assert ag.video_can_ghim_som(so_video, {"V7": {"da_ghim": "x"}}, "K", bay) == []
        assert ag.video_can_ghim_som(so_video, {"V7": {"trang_thai": "cho-xac-minh",
                                                        "ghim_cho_xac_minh": "2026-09-30 20:06:00"}}, "K", bay) == []
        # 30/09/2026: ghim tắt → đã có mồi là xong; bật ghim → xét lại
        moi = {"V7": {"da_dang_moi": "2026-09-30 20:08:00", "trang_thai": "da-dang", "ghim": "tat"}}
        assert ag.video_can_ghim_som(so_video, moi, "K", bay, ghim_bat=False) == []
        assert ag.video_can_ghim_som(so_video, moi, "K", bay, ghim_bat=True) == ["K-0007"]
        assert ag.video_can_ghim_som(so_video, {}, "K", bay, ghim_bat=False) == ["K-0007"]

    def test_chay_ghim_som_ghim_tat_khong_mo_chrome(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        bay = time.mktime((2026, 9, 30, 20, 30, 0, 0, 0, -1))
        (tmp_path / "logs" / "so-video-id.json").write_text(json.dumps(
            {"K/K-0007": {"video_id": "V7", "trang_thai": "xac-nhan", "lich": "30/09/2026 20:00"}}), encoding="utf-8")
        (tmp_path / "logs" / "cmt-dom.json").write_text(json.dumps(
            {"V7": {"da_dang_moi": "2026-09-30 20:08:00", "trang_thai": "da-dang", "ghim": "tat"}}),
            encoding="utf-8")
        monkeypatch.setattr(ag, "van_ipv4_mo", lambda: False)
        monkeypatch.setattr(ag, "giu_khoa_may_chung", lambda **kw: pytest.fail("không được giành khoá"))
        hl = {"K": {"kenh": "K", "tu_dang": True, "ghim_dom": False}}
        assert ag.chay_ghim_som({}, hl, ["K"], bay, chay_con=lambda *a, **k: pytest.fail("không chạy")) is False

    def test_chay_ghim_som_mo_chrome_chay_dong(self, tmp_path, monkeypatch):
        ag = _nap_agent(tmp_path, monkeypatch)
        bay = time.mktime((2026, 9, 30, 20, 10, 0, 0, 0, -1))
        (tmp_path / "logs" / "so-video-id.json").write_text(json.dumps(
            {"K/K-0007": {"video_id": "V7", "trang_thai": "xac-nhan", "lich": "30/09/2026 20:00"}}), encoding="utf-8")
        su_kien = []
        monkeypatch.setattr(ag, "van_ipv4_mo", lambda: False)
        monkeypatch.setattr(ag, "giu_khoa_may_chung", lambda **kw: su_kien.append(("khoa", kw.get("viec"))) or True)
        monkeypatch.setattr(ag, "nha_khoa_may_chung", lambda: su_kien.append("nha"))
        monkeypatch.setattr(ag, "tim_chrome", lambda ch: "C:/K/K.exe")
        monkeypatch.setattr(ag, "_chrome_dang_chay", lambda c: False)
        monkeypatch.setattr(ag, "mo_chrome_kenh", lambda *a, **k: su_kien.append("mo"))
        monkeypatch.setattr(ag, "_cho_devtools", lambda *a: True)
        monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: su_kien.append("dong"))

        def con(duong, kenh, nhan, han_giay, co_gi_them=()):
            su_kien.append((Path(duong).name, tuple(co_gi_them)))
            return "ok", 0
        hl = {"K": {"kenh": "K", "tu_dang": True}}
        assert ag.chay_ghim_som({}, hl, ["K"], bay, chay_con=con) is True
        assert su_kien == [("khoa", "binh_luan"), "mo", ("may_cmt_dom.py", ("--chi-moi", "--trong-phien")),
                           "dong", "nha"]
        # chu kỳ: gọi lại ngay thì không chạy
        assert ag.chay_ghim_som({}, hl, ["K"], bay + 60, chay_con=con) is False
        # phút :55–:05 nhường tu_chay
        ag._GHIM_SOM["luc"] = 0.0
        assert ag.chay_ghim_som({}, hl, ["K"], time.mktime((2026, 9, 30, 21, 58, 0, 0, 0, -1)),
                                chay_con=con) is False
        # kênh không tu_dang → không làm gì
        ag._GHIM_SOM["luc"] = 0.0
        assert ag.chay_ghim_som({}, {"K": {"tu_dang": False}}, ["K"], bay + 3600, chay_con=con) is False
