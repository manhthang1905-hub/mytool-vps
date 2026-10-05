"""Kéo view chéo (06/10/2026): `core/keo_cheo.py` (lập kế hoạch — kênh giả trong thư mục tạm) và
`vm/keo_cheo_dom.py` (máy DOM — trang giả, không Chrome, không mạng)."""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
for _p in (str(GOC), str(VM)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import keo_cheo as kc  # noqa: E402
import cdp_studio  # noqa: E402
import keo_cheo_dom as kcd  # noqa: E402

BAY_GIO = dt.datetime(2026, 10, 6, 12, 0)


# ═══ DỰNG KÊNH GIẢ ═════════════════════════════════════════════════════════

def _ghi_csv(duong: Path, cot, hang) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(cot)
        w.writerows(hang)


def dung_kenh(goc: Path, ma: str, gio_xem=None, nhom="tam-ly", ds="", video=(), them_yaml=""):
    """`gio_xem` = (giờ đầu kỳ, giờ cuối kỳ) cộng dồn cách 30 ngày. `video` = [(id, tiêu đề, lúc công khai,
    lượt xem)] — vào kế hoạch (ĐÃ ĐĂNG + ngày/giờ) và bảng tóm tắt."""
    k = goc / "CHANNEL" / ma
    k.mkdir(parents=True, exist_ok=True)
    yaml = 'ma: "{0}"\nnhom: "{1}"\n'.format(ma, nhom)
    if ds:
        yaml += 'danh_sach_phat_kenh: "{0}"\n'.format(ds)
    (k / "kenh.yaml").write_text(yaml + them_yaml, encoding="utf-8")
    if gio_xem is not None:
        a, b = gio_xem
        _ghi_csv(k / "chi-so" / "kenh-theo-ngay.csv",
                 ["Lúc chụp", "Lượt xem", "Giờ xem", "Đăng ký", "Lượt hiển thị", "Tỷ lệ bấm"],
                 [["2026-09-05 02:00", "1", str(a), "0", "", ""],
                  ["2026-10-05 02:00", "9", str(b), "0", "", ""]])
    kh, bt = [], []
    for i, (vid, td, luc, view) in enumerate(video):
        kh.append(["{0}-{1:04d}".format(ma, i + 1), luc.strftime("%d/%m/%Y"), luc.strftime("%H:%M"), td,
                   "", "", "", "", "", "", "x", "ĐÃ ĐĂNG", "", vid])
        bt.append([td, vid, luc.strftime("%Y-%m-%d"), "12:00", "48h", "100", "5%", str(view)])
    if kh:
        _ghi_csv(k / "ke-hoach-dang" / "ke-hoach.csv",
                 ["Mã gói", "Ngày đăng", "Giờ đăng", "Tiêu đề", "Mô tả", "Thẻ SEO", "Link card 1", "Link card 2",
                  "Link card 3", "Link card 4", "Sẵn sàng", "Trạng thái đăng", "Ghi chú", "Video ID"], kh)
        _ghi_csv(k / "chi-so" / "bang-tom-tat.csv",
                 ["Tiêu đề", "Mã video", "Ngày đăng", "Dài", "Mốc mới nhất", "Lượt hiển thị", "Tỷ lệ bấm",
                  "Lượt xem"], bt)
    return k


def cum_gia(_chu, td):
    ra = []
    if "孤独" in td:
        ra.append("mot-minh")
    if "頭" in td:
        ra.append("tri-tue")
    return ra


def _vid(n: int) -> str:
    return "vid{0:08d}".format(n)


def truoc(gio: float) -> dt.datetime:
    return BAY_GIO - dt.timedelta(hours=gio)


@pytest.fixture
def nhom(tmp_path):
    """Một kênh lớn (L, 800h), hai kênh em (E1, E2)."""
    dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人 | 頭がいい人の習慣")
    dung_kenh(tmp_path, "E1", (0, 20), video=[
        (_vid(1), "孤独な人ほど強い理由", truoc(30), 10),
        (_vid(2), "頭がいい人の口癖", truoc(50), 20),
        (_vid(3), "孤独を選ぶ人の本音", truoc(10), 5),          # chưa đủ 24 giờ
    ])
    dung_kenh(tmp_path, "E2", (0, 5), video=[
        (_vid(11), "孤独が平気な人の特徴", truoc(40), 7),
    ])
    return tmp_path


def lap(goc, **kw):
    kw.setdefault("thu_muc", str(goc / "trang-thai"))
    kw.setdefault("cum_cua", cum_gia)
    kw.setdefault("bay_gio", BAY_GIO)
    kw.setdefault("duong_so", "")
    return kc.lap_ke_hoach(str(goc), BAY_GIO.date(), **kw)


# ═══ LẬP KẾ HOẠCH ═══════════════════════════════════════════════════════════

class TestGioXem:
    def test_cong_don_tru_dau_ky(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900))
        # 28 ngày trước mốc cuối = 2 ngày sau mốc đầu: 100 + 800·2/30
        assert kc.gio_xem_trong_ky(str(tmp_path), "L") == pytest.approx(900 - (100 + 800 * 2 / 30), abs=0.05)

    def test_du_lieu_ngan_hon_ky(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900))
        assert kc.gio_xem_trong_ky(str(tmp_path), "L", so_ngay=60) == pytest.approx(800)

    def test_khong_co_tep(self, tmp_path):
        dung_kenh(tmp_path, "L")
        assert kc.gio_xem_trong_ky(str(tmp_path), "L") is None


class TestPhanVai:
    def test_nguong(self, nhom):
        lon, em = kc.phan_vai_nhom(str(nhom), ["L", "E1", "E2"], dict(kc.CAI_DAT_MAC_DINH))
        assert list(lon) == ["L"] and sorted(em) == ["E1", "E2"]
        lon, em = kc.phan_vai_nhom(str(nhom), ["L", "E1", "E2"], dict(kc.CAI_DAT_MAC_DINH, nguong_gio_xem=1000))
        assert lon == {}

    def test_nguong_qua_cao_khong_viec(self, nhom):
        assert lap(nhom, cai_dat={"nguong_gio_xem": 5000}) == []

    def test_khac_nhom_khong_keo(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人")
        dung_kenh(tmp_path, "X", (0, 1), nhom="khac", video=[(_vid(1), "孤独な人", truoc(30), 1)])
        assert lap(tmp_path) == []

    def test_tat_keo_cheo(self, nhom):
        p = nhom / "CHANNEL" / "L" / "kenh.yaml"
        p.write_text(p.read_text(encoding="utf-8") + "keo_cheo_tat: true\n", encoding="utf-8")
        assert lap(nhom) == []


class TestKeHoach:
    def test_cum_sang_danh_sach_va_rai_deu_kenh_em(self, nhom):
        kh = lap(nhom)
        assert len(kh) == 2                                    # trần 2/kênh lớn/ngày
        assert {h["kenh_video"] for h in kh} == {"E1", "E2"}   # rải đều: mỗi kênh em một
        theo_vid = {h["video_id"]: h for h in kh}
        # E2 (ít giờ xem nhất) đi trước, lấy suất 孤独; E1 còn lại 頭がいい (1 video/ds/ngày)
        assert theo_vid[_vid(11)]["danh_sach_phat"] == "孤独を楽しむ人"
        assert theo_vid[_vid(11)]["cum"] == "mot-minh"
        assert theo_vid[_vid(2)]["danh_sach_phat"] == "頭がいい人の習慣"
        assert all(h["kenh_chu"] == "L" and h["cach_chon"] == "cum" for h in kh)
        assert _vid(3) not in theo_vid                         # < 24 giờ sau công khai

    def test_mot_video_mot_ds_moi_ngay_va_ds_rieng(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人")
        dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "孤独A", truoc(30), 1), (_vid(2), "孤独B", truoc(40), 1),
                                                 (_vid(4), "孤独C", truoc(45), 1)])
        kh = lap(tmp_path)
        assert [h["danh_sach_phat"] for h in kh] == ["孤独を楽しむ人"]
        kh = lap(tmp_path, cai_dat={"ds_rieng": "おすすめ"})
        assert sorted(h["danh_sach_phat"] for h in kh) == ["おすすめ", "孤独を楽しむ人"]
        assert [h["cach_chon"] for h in kh if h["danh_sach_phat"] == "おすすめ"] == ["rieng"]

    def test_ds_rieng_trong_kenh_yaml(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), them_yaml='keo_cheo_danh_sach_phat: "推し動画"\n')
        dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "全然ちがう話", truoc(30), 1)])
        kh = lap(tmp_path)
        assert [(h["danh_sach_phat"], h["cach_chon"]) for h in kh] == [("推し動画", "rieng")]

    def test_khong_ds_khong_viec(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900))
        dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "孤独A", truoc(30), 1)])
        assert lap(tmp_path) == []

    def test_khong_khop_cum_thi_khong_them(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人")
        dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "全然ちがう話", truoc(30), 1)])
        assert lap(tmp_path) == []

    def test_ai_chon_theo_nghia(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人 | 家が好き")
        dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "休日は外に出ない人", truoc(30), 1)])
        hoi = []

        def ai(td, ds):
            hoi.append((td, ds))
            return "家が好き"
        kh = lap(tmp_path, chon_ai=ai)
        assert [(h["danh_sach_phat"], h["cach_chon"]) for h in kh] == [("家が好き", "ai")]
        assert hoi and hoi[0][1] == ["孤独を楽しむ人", "家が好き"]

    def test_khong_trung_video_va_tran_ngay(self, nhom):
        tm = str(nhom / "trang-thai")
        kh = lap(nhom)
        for h in kh:
            kc.ghi_ket_qua(tm, h, "ok", luc=BAY_GIO)
        assert lap(nhom) == []                                 # đã đủ 2 lần hôm nay
        mai = BAY_GIO + dt.timedelta(days=1)
        kh2 = kc.lap_ke_hoach(str(nhom), mai.date(), thu_muc=tm, cum_cua=cum_gia, bay_gio=mai, duong_so="")
        da = {h["video_id"] for h in kh}
        assert kh2 and not ({h["video_id"] for h in kh2} & da)  # hôm sau: video khác, không lặp
        # vid3 vừa đủ 24 giờ lấy suất 孤独; vid1 cũng cụm 孤独 mà ds ấy đã đủ suất ngày → không thêm
        assert [h["video_id"] for h in kh2] == [_vid(3)]

    def test_da_co_cung_tinh_la_da_them_loi_thi_thu_lai_co_tran(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人")
        dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "孤独A", truoc(30), 1)])
        tm = str(tmp_path / "trang-thai")
        hd = lap(tmp_path)[0]
        kc.ghi_ket_qua(tm, hd, "loi:tim_ds: không có", luc=BAY_GIO)
        assert len(lap(tmp_path)) == 1                         # lỗi: còn thử lại
        kc.ghi_ket_qua(tm, hd, "loi:x", luc=BAY_GIO)
        kc.ghi_ket_qua(tm, hd, "loi:x", luc=BAY_GIO)
        assert lap(tmp_path) == []                             # hỏng 3 lần: thôi
        tm2 = str(tmp_path / "tt2")
        kc.ghi_ket_qua(tm2, hd, "da_co", luc=BAY_GIO - dt.timedelta(days=3))
        assert lap(tmp_path, thu_muc=tm2) == []

    def test_so_may_dang_cho_gio_cong_khai(self, tmp_path):
        """Video chỉ có trong sổ máy đăng (`lich`) + hồ sơ (tiêu đề) — chưa lên bảng Studio."""
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人")
        k = dung_kenh(tmp_path, "E1", (0, 1))
        (k / "ho-so-video").mkdir()
        (k / "ho-so-video" / "E1-0001.json").write_text(json.dumps({"tieu_de": "孤独の力"}), encoding="utf-8")
        so = tmp_path / "so.json"
        so.write_text(json.dumps({
            "E1/E1-0001": {"video_id": _vid(7), "trang_thai": "xac-nhan", "lich": truoc(25).strftime("%d/%m/%Y %H:%M")},
            "E1/E1-0002": {"video_id": _vid(8), "trang_thai": "xac-nhan", "lich": truoc(2).strftime("%d/%m/%Y %H:%M")},
        }), encoding="utf-8")
        kh = lap(tmp_path, duong_so=str(so))
        assert [h["video_id"] for h in kh] == [_vid(7)]

    def test_du_doan_co_moc_va_doi_chung(self, nhom):
        kh = lap(nhom)
        h = next(x for x in kh if x["video_id"] == _vid(2))
        dd = h["du_doan"]
        assert dd["view_luc_them"] == 20 and dd["kiem_sau_ngay"] == 7
        assert set(dd["doi_chung"]) <= {_vid(1), _vid(3)} and dd["doi_chung"]
        assert "đối" in dd["gia_thuyet"]


class TestDoHieuQua:
    def test_keo_duoc(self, tmp_path):
        dung_kenh(tmp_path, "L", (100, 900), ds="孤独を楽しむ人")
        k = dung_kenh(tmp_path, "E1", (0, 1), video=[(_vid(1), "孤独A", truoc(30), 10),
                                                     (_vid(2), "別の話", truoc(40), 10)])
        tm = str(tmp_path / "trang-thai")
        hd = lap(tmp_path)[0]
        assert hd["video_id"] == _vid(1) and hd["du_doan"]["doi_chung"] == {_vid(2): 10}
        kc.ghi_ket_qua(tm, hd, "ok", luc=BAY_GIO)
        assert kc.do_hieu_qua(str(tmp_path), tm, bay_gio=BAY_GIO + dt.timedelta(days=3)) == []  # chưa đủ 7 ngày
        _ghi_csv(k / "chi-so" / "bang-tom-tat.csv", ["Tiêu đề", "Mã video", "Ngày đăng", "Lượt xem"],
                 [["孤独A", _vid(1), "2026-10-05", "50"], ["別の話", _vid(2), "2026-10-04", "12"]])
        do = kc.do_hieu_qua(str(tmp_path), tm, bay_gio=BAY_GIO + dt.timedelta(days=8))
        assert len(do) == 1 and do[0]["do_sau"]["ket"] == "keo_duoc"
        assert do[0]["do_sau"]["tang"] == pytest.approx(4.0)
        assert kc.do_hieu_qua(str(tmp_path), tm, bay_gio=BAY_GIO + dt.timedelta(days=9)) == []  # đo một lần
        so = kc.doc_da_them(tm)
        assert so["muc"][0]["do_sau"]["ket"] == "keo_duoc"


# ═══ MÁY DOM — TRANG GIẢ ═══════════════════════════════════════════════════

class TrangGia:
    """Trang xem giả: nút Lưu (thẳng hoặc trong menu «⋯»), hộp Lưu với các hàng danh sách phát.

    `luu` = trạng thái PHÍA YOUTUBE (đã lưu); `hien` = trạng thái hộp đang hiện. Mở hộp → hien = luu.
    `ben`: tích có được YouTube lưu không (False → đọc lại thấy mất). `an_tich`: bấm không đổi gì."""

    def __init__(self, ds, vid="abcdefghijk", cach="truc_tiep", ben=True, an_tich=False, url_lech=False):
        self.luu = dict(ds)
        self.hien = {}
        self.vid = vid
        self.cach = cach
        self.ben = ben
        self.an_tich = an_tich
        self.url_lech = url_lech
        self.bam_ds = []
        self.mo = False
        self.menu = False
        self.trang = ""
        self.esc = 0

    def mo_video(self, vid):
        self.trang = vid

    def url(self):
        return "https://www.youtube.com/watch?v=" + ("zzzzzzzzzzz" if self.url_lech else self.trang)

    def tim(self, khoa):
        if khoa == "kc_nut_luu" and self.cach == "truc_tiep" and self.trang:
            return {"id": "nut_luu", "khoa": khoa, "cach": "chon#1"}
        if khoa == "kc_nut_them" and self.cach == "menu" and self.trang:
            return {"id": "nut_them", "khoa": khoa, "cach": "chon#1"}
        if khoa == "kc_dong_hop" and self.mo:
            return {"id": "dong", "khoa": khoa}
        return None

    def tim_loc_chu(self, khoa):
        if khoa == "kc_menu_luu" and self.menu:
            return {"id": "menu_luu", "khoa": khoa}
        return None

    def _mo_hop(self):
        self.mo, self.menu = True, False
        self.hien = dict(self.luu)

    def bam(self, pt):
        i = pt["id"]
        self.bam_ds.append(i)
        if i == "nut_luu":
            self._mo_hop()
        elif i == "nut_them":
            self.menu = True
        elif i == "menu_luu":
            self._mo_hop()
        elif i == "dong":
            self.mo = False
        elif i.startswith("hang:"):
            ten = i[5:]
            if not self.an_tich:
                self.hien[ten] = not self.hien[ten]
                if self.ben:
                    self.luu[ten] = self.hien[ten]
        else:
            raise AssertionError("bấm lạ " + i)

    def doc_hop(self):
        if not self.mo:
            return {"hop": False, "hang": []}
        return {"hop": True, "hang": [{"id": "hang:" + t, "khoa": "kc_hang_ds", "ten": t, "chon": c}
                                      for t, c in self.hien.items()]}

    def phim_esc(self):
        self.esc += 1
        self.mo = self.menu = False

    def chup(self, nhan):
        return "anh-" + nhan


DS = {"Xem sau": False, "おすすめ": False, "おすすめ 2": False, "孤独を楽しむ人": True}


def may(trang):
    return kcd.KeoCheo(trang, nhat_ky=lambda _s: None, ngu=lambda _s: None)


class TestMayDom:
    def test_thu_khong_bam_gi(self):
        tr = TrangGia(DS)
        kq = may(tr).them("abcdefghijk", "おすすめ", "thu")
        assert kq["ket"] == "thu:ok" and tr.bam_ds == [] and tr.esc == 0
        assert tr.luu == DS

    def test_thu_khong_thay_nut_luu(self):
        tr = TrangGia(DS, cach="khong")
        kq = may(tr).them("abcdefghijk", "おすすめ", "thu")
        assert kq["ket"].startswith("loi:nut_luu") and tr.bam_ds == []

    def test_that_tich_dung_hang_va_doc_lai(self):
        tr = TrangGia(DS)
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"] == "ok"
        assert tr.bam_ds == ["nut_luu", "hang:おすすめ", "dong", "nut_luu", "dong"]
        assert tr.luu == dict(DS, **{"おすすめ": True})            # chỉ đúng hàng đó đổi
        assert not tr.mo
        assert "おすすめ 2" in kq["danh_sach_co"]

    def test_ten_chuan_hoa_nfkc(self):
        tr = TrangGia({"ＡＢＣ  おすすめ": False})
        kq = may(tr).them("abcdefghijk", "ABC おすすめ")
        assert kq["ket"] == "ok" and tr.luu == {"ＡＢＣ  おすすめ": True}

    def test_doc_lai_hong_thi_bao(self):
        tr = TrangGia(DS, ben=False)
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"].startswith("loi:doc_lai") and kq["loi_buoc"] == "doc_lai"
        assert kq.get("anh") == "anh-keo-cheo-loi-abcdefghijk"
        assert not tr.mo

    def test_bam_ma_khong_tich(self):
        tr = TrangGia(DS, an_tich=True)
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"].startswith("loi:tich")
        assert tr.bam_ds.count("hang:おすすめ") == 1              # không bấm lần hai (lần hai = bỏ tích)
        assert not tr.mo

    def test_da_co_khong_bam(self):
        tr = TrangGia(DS)
        kq = may(tr).them("abcdefghijk", "孤独を楽しむ人")
        assert kq["ket"] == "da_co" and tr.bam_ds == ["nut_luu", "dong"]
        assert tr.luu == DS

    def test_khong_co_danh_sach(self):
        tr = TrangGia(DS)
        kq = may(tr).them("abcdefghijk", "không tồn tại")
        assert kq["ket"].startswith("loi:tim_ds") and "おすすめ" in kq["ket"]
        assert not tr.mo and all(not b.startswith("hang:") for b in tr.bam_ds)

    def test_trung_ten_khong_doan(self):
        tr = TrangGia({"おすすめ": False, "おすすめ ": False})
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"].startswith("loi:tim_ds") and all(not b.startswith("hang:") for b in tr.bam_ds)

    def test_qua_menu(self):
        tr = TrangGia(DS, cach="menu")
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"] == "ok"
        assert tr.bam_ds == ["nut_them", "menu_luu", "hang:おすすめ", "dong", "nut_them", "menu_luu", "dong"]

    def test_doc_hop_khong_tich(self):
        tr = TrangGia(DS)
        kq = may(tr).them("abcdefghijk", "おすすめ", "doc_hop")
        assert kq["ket"] == "doc_hop:chua_tich" and tr.bam_ds == ["nut_luu", "dong"] and tr.luu == DS

    def test_sai_trang(self):
        tr = TrangGia(DS, url_lech=True)
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"].startswith("loi:mo") and tr.bam_ds == []

    def test_trang_thai_khong_doc_duoc(self):
        tr = TrangGia({"おすすめ": None})
        kq = may(tr).them("abcdefghijk", "おすすめ")
        assert kq["ket"].startswith("loi:trang_thai") and all(not b.startswith("hang:") for b in tr.bam_ds)


class TestBoChon:
    def test_khoa_moi_hop_le(self):
        bo = cdp_studio.doc_bo_chon()
        assert cdp_studio.kiem_bo_chon(bo) == []
        bo2, loi = kcd.chuan_bi_bo(bo)
        assert loi == []
        assert bo2["cam_bam"]["aria_chua"] == bo["cam_bam_keo_cheo"]["aria_chua"]
        assert bo["cam_bam"] != bo2["cam_bam"]                  # bản gốc không bị đổi
        for k in kcd.KHOA_KEO_CHEO:
            spec = bo["phan_tu"][k]
            assert spec.get("chon"), k
        assert bo["phan_tu"]["kc_menu_luu"]["loc_chu"] is True
        for k in ("kc_nut_luu", "kc_menu_luu"):
            chu = bo["phan_tu"][k]["chu"]
            assert {"Lưu", "保存", "Save"} <= set(chu)

    def test_hang_cua(self):
        hop = {"hang": [{"ten": "おすすめ"}, {"ten": "おすすめ 2"}, {"ten": " おすすめ"}]}
        assert len(kcd.hang_cua(hop, "おすすめ")) == 2
        assert kcd.hang_cua(hop, "x") == []
