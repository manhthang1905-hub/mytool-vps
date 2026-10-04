"""Máy đăng DOM — luồng một gói + sổ videoId (Việc B, thiết kế
`workspace/THIET-KE-MAY-DANG-DOM.md` mục 2.2, 3, 4, 8, 10).

`StudioGia` mô phỏng Studio với CÙNG giao diện `TrangStudio` (mo/tim/co/bam/go/
go_tho/doc_chu/doc_thuoc_tinh/dat_tep/phim/doc_hang/…) — không mạng, không Chrome.
"""

from __future__ import annotations

import importlib
import json
import struct
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import may_dang_dom as mdd  # noqa: E402

UC = "UC" + "a1B2c3D4e5F6g7H8i9J0kL"
BAY_GIO = datetime(2026, 9, 29, 9, 3, 20)


# ═══ HÀM THUẦN ═════════════════════════════════════════════════════════════

class TestHamThuan:
    def test_rut_video_id(self):
        assert mdd.rut_video_id("https://youtu.be/AbCdEfGhIjK") == "AbCdEfGhIjK"
        assert mdd.rut_video_id("https://studio.youtube.com/video/AbCdEfGh_-K/edit") == "AbCdEfGh_-K"
        assert mdd.rut_video_id("https://www.youtube.com/watch?v=AbCdEfGhIjK&t=3") == "AbCdEfGhIjK"
        assert mdd.rut_video_id("https://youtube.com/shorts/AbCdEfGhIjK") == "AbCdEfGhIjK"
        assert mdd.rut_video_id("https://youtu.be/AbCdEfGhIjKL") == ""      # 12 ký tự: không nhận bừa
        # hàng NHÁP thật (29/09): id chỉ nằm ở ảnh thu nhỏ
        assert mdd.rut_video_id("https://i9.ytimg.com/vi/vcfe05f792c/mqdefault.jpg?sqp=CIjY") == "vcfe05f792c"
        assert mdd.rut_video_id("") == ""

    def test_phan_tich_trang_thai(self):
        f = mdd.phan_tich_trang_thai
        assert f("Đã lên lịch\n30 thg 9, 2026, 20:00") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        assert f("Đã lên lịch 30/09/2026 20:00") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        assert f("Đã lên lịch · 30 tháng 9, 2026 lúc 20:00") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        assert f("Đã lên lịch 30 thg 9, 2026 8:00 CH") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        assert f("Không công khai")[0] == "khong_cong_khai"
        assert f("Công khai")[0] == "cong_khai"
        assert f("Riêng tư")[0] == "rieng_tu"
        assert f("Nháp  Chỉnh sửa bản nháp")[0] == "nhap"
        assert f("Tải lên không thành công")[0] == "loi_tai"
        assert f("")[0] == "khong_ro"
        assert f("Scheduled Sep 30, 2026, 8:00 PM") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        # Studio TL4 hiển thị tiếng Nhật (đo 29/09/2026): 非公開/限定公開 CHỨA 公開
        assert f("公開設定 公開")[0] == "cong_khai"
        assert f("公開 2026/09/28 公開日") == ("cong_khai", None)
        assert f("非公開")[0] == "rieng_tu"
        assert f("限定公開")[0] == "khong_cong_khai"
        assert f("下書き")[0] == "nhap"
        assert f("公開予約 2026/09/30 20:00") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        assert f("2026年9月30日 20:00 予約済み") == ("da_len_lich", datetime(2026, 9, 30, 20, 0))
        # Hàng danh sách thật (29/09): ô hiển thị + ô ngày, KHÔNG lẫn thời lượng 12:46
        assert f("Công khai\n28 thg 9, 2026 Đã xuất bản") == ("cong_khai", None)

    def test_dinh_dang_ngay(self):
        d = date(2026, 9, 3)
        assert mdd.dinh_dang_ngay(d, "{d} thg {m}, {Y}") == "3 thg 9, 2026"
        assert mdd.dinh_dang_ngay(d, "{dd}/{mm}/{Y}") == "03/09/2026"
        assert mdd.phan_tich_ngay("3 thg 9, 2026")[0] == d

    def test_ngay_studio_tieng_han(self):
        d = date(2026, 10, 5)
        assert mdd.dinh_dang_ngay(d, "{Y}. {m}. {d}.") == "2026. 10. 5."
        assert mdd.phan_tich_ngay("2026. 10. 5.")[0] == d
        assert mdd.phan_tich_ngay("2026. 9. 30. 오전 5:00")[0] == date(2026, 9, 30)
        assert mdd.phan_tich_ngay("2026-10-05")[0] == d
        assert mdd.phan_tich_ngay("v1.2.3.4")[0] is None
        assert "{Y}. {m}. {d}." in mdd.mau_ngay_thu({"dinh_dang_ngay": ["{dd}/{mm}/{Y}"]})
        assert mdd.mau_ngay_thu({}).count("{Y}. {m}. {d}.") == 1
        assert mdd.mau_ngay_thu({"dinh_dang_ngay": ["{Y}. {m}. {d}."]}) == ["{Y}. {m}. {d}."]

    def test_chuan_hoa_tieu_de(self):
        assert mdd.chuan_hoa_tieu_de("【雑学】　猫  が\n好き ") == mdd.chuan_hoa_tieu_de("【雑学】 猫 が 好き")
        assert mdd.chuan_hoa_tieu_de("ＡＢＣ") == "ABC"

    def test_gio_hen_da_qua_cong_15_lam_tron_5(self):
        dt, gc = mdd.gio_hen_hieu_luc("29/09/2026", "07:00", BAY_GIO)
        assert dt == datetime(2026, 9, 29, 9, 20)
        assert "đã qua" in gc
        dt2, gc2 = mdd.gio_hen_hieu_luc("30/09/2026", "20:00", BAY_GIO)
        assert dt2 == datetime(2026, 9, 30, 20, 0) and gc2 == ""
        assert mdd.gio_hen_hieu_luc("", "", BAY_GIO)[0] is None

    def test_kiem_du_lieu(self):
        assert mdd.kiem_du_lieu_dong({"tieu_de": "ok", "mo_ta": "x", "the": "a, b"}) == []
        loi = mdd.kiem_du_lieu_dong({"tieu_de": "a<b" + "x" * 100, "mo_ta": "x" * 5001,
                                     "the": ", ".join(["t" * 50] * 11)})
        assert len(loi) == 4


def _hop(loai, noi):
    return struct.pack(">I4s", 8 + len(noi), loai) + noi


def _mp4(tmp_path, giay=300.0, v1=False, moov_cuoi=True, largesize=False):
    thang = 1000
    if v1:
        mvhd = bytes([1, 0, 0, 0]) + b"\0" * 16 + struct.pack(">IQ", thang, int(giay * thang)) + b"\0" * 80
    else:
        mvhd = bytes([0, 0, 0, 0]) + b"\0" * 8 + struct.pack(">II", thang, int(giay * thang)) + b"\0" * 80
    moov = _hop(b"moov", _hop(b"trak", b"\0" * 20) + _hop(b"mvhd", mvhd))
    if largesize:
        noi = b"\0" * 1000
        mdat = struct.pack(">I4sQ", 1, b"mdat", 16 + len(noi)) + noi
    else:
        mdat = _hop(b"mdat", b"\0" * 1000)
    ftyp = _hop(b"ftyp", b"isom\0\0\0\0isomiso2")
    p = tmp_path / "8-video.mp4"
    p.write_bytes(ftyp + (mdat + moov if moov_cuoi else moov + mdat))
    return p


class TestMvhd:
    def test_v0_moov_cuoi(self, tmp_path):
        assert mdd.thoi_luong_mp4_mvhd(str(_mp4(tmp_path, 312.5))) == pytest.approx(312.5)

    def test_v1_moov_dau_largesize(self, tmp_path):
        assert mdd.thoi_luong_mp4_mvhd(str(_mp4(tmp_path, 1800, v1=True, moov_cuoi=False,
                                                 largesize=True))) == pytest.approx(1800)

    def test_hong(self, tmp_path):
        p = tmp_path / "x.mp4"
        p.write_bytes(b"khong phai mp4")
        assert mdd.thoi_luong_mp4_mvhd(str(p)) is None
        assert mdd.thoi_luong_mp4_mvhd(str(tmp_path / "khong-co.mp4")) is None

    def test_moc_the(self):
        assert mdd.compute_card_timestamps(300) == ["02:30:00", "03:05:00", "03:40:00", "04:15:00", "04:50:00"]


# ═══ THẺ VIDEO: chọn video view cao nhất 48 giờ qua ═══════════════════════

def _chi_so_gia(tmp_path, top48=None, tong=None):
    """Dựng `chi-so/` giả đúng khuôn mắt cào ghi (gói get_cards + bang-tom-tat.csv)."""
    goc = tmp_path / "chi-so"
    if top48 is not None:
        raw = goc / "kenh" / "kenh-20260929" / "raw"
        raw.mkdir(parents=True)
        cards = {"response": {"cards": [
            {"config": {}},
            {"latestActivityCardData": {"datas": [{
                "timePeriod": mdd._KY_48H,
                "topEntitiesData": {
                    "dimensionColumns": [{"dimension": {"type": "VIDEO"}, "strings": {"values": list(top48)}}],
                    "metricColumns": [{"metric": {"type": "EXTERNAL_VIEWS"},
                                       "counts": {"values": list(top48.values())}}]}}]}}]}}
        (raw / "20260929-073542_tab-content_youtubei-v1-yta_web-get_cards-alt-json_2.json").write_text(
            json.dumps(cards), encoding="utf-8")
        # gói CŨ hơn mang số khác — phải lấy gói MỚI nhất
        cu = goc / "kenh" / "kenh-20260920" / "raw"
        cu.mkdir(parents=True)
        cards2 = json.loads(json.dumps(cards))
        cards2["response"]["cards"][1]["latestActivityCardData"]["datas"][0]["topEntitiesData"][
            "metricColumns"][0]["counts"]["values"] = [1] * len(top48)
        (cu / "20260920-070000_tab-overview_youtubei-v1-yta_web-get_cards-alt-json_5.json").write_text(
            json.dumps(cards2), encoding="utf-8")
    if tong is not None:
        goc.mkdir(parents=True, exist_ok=True)
        dong = ["Tiêu đề,Mã video,Ngày đăng,Lượt xem"] + ['"t",{0},2026-09-2x,{1}'.format(k, v) for k, v in tong.items()]
        (goc / "bang-tom-tat.csv").write_text("\n".join(dong), encoding="utf-8-sig")
    return str(goc)


class TestTheVideo:
    def test_doc_48h_goi_moi_nhat(self, tmp_path):
        g = _chi_so_gia(tmp_path, top48={"v425582e4bd": 91, "v6ec3fe0d22": 89, "vff186160a1": 9})
        assert mdd.doc_view_48h(g) == {"v425582e4bd": 91, "v6ec3fe0d22": 89, "vff186160a1": 9}
        assert mdd.doc_view_48h(str(tmp_path / "khong-co")) == {}

    def test_xep_theo_48h_loai_video_dang_dang(self, tmp_path):
        g = _chi_so_gia(tmp_path, top48={"AAAAAAAAAAA": 9, "BBBBBBBBBBB": 91, "CCCCCCCCCCC": 50},
                        tong={"AAAAAAAAAAA": 1000, "BBBBBBBBBBB": 5, "CCCCCCCCCCC": 7, "DDDDDDDDDDD": 3})
        ds = mdd.chon_video_the(mdd.doc_view_48h(g), mdd.doc_view_tong(g), loai_tru={"CCCCCCCCCCC"})
        # 48h thắng tổng view; C bị loại (đang đăng); D không có 48h → lùi tổng view, xếp sau
        assert ds == ["https://youtu.be/BBBBBBBBBBB", "https://youtu.be/AAAAAAAAAAA",
                      "https://youtu.be/DDDDDDDDDDD"]

    def test_lui_tong_view_khi_thieu_48h(self, tmp_path):
        g = _chi_so_gia(tmp_path, tong={"AAAAAAAAAAA": 10, "BBBBBBBBBBB": 300, "EEEEEEEEEEE": 20})
        assert mdd.chon_video_the(mdd.doc_view_48h(g), mdd.doc_view_tong(g), loai_tru={"EEEEEEEEEEE"}) == [
            "https://youtu.be/BBBBBBBBBBB", "https://youtu.be/AAAAAAAAAAA"]

    def test_uu_tien_link_nguoi_dien_toi_da_4_khong_trung(self):
        v48 = {"A" * 11: 5, "B" * 11: 4, "C" * 11: 3, "D" * 11: 2}
        ds = mdd.chon_video_the(v48, {}, co_san=["https://youtu.be/" + "C" * 11, "", "https://youtu.be/" + "Z" * 11])
        assert ds == ["https://youtu.be/" + "C" * 11, "https://youtu.be/" + "Z" * 11,
                      "https://youtu.be/" + "A" * 11, "https://youtu.be/" + "B" * 11]

    def test_khong_co_gi_thi_rong(self):
        assert mdd.chon_video_the({}, {}, loai_tru={"X"}) == []


# ═══ BẢNG QUYẾT ĐỊNH (mục 3) ═══════════════════════════════════════════════

TD = "【雑学】朝いつも同じ夢を見る人"
DONG = {"ma": "TL1-T7-0007", "tieu_de": TD}
HOM_NAY = "2026-09-29"


def _h(vid, loai, tieu_de=TD, luc=None):
    return {"video_id": vid, "loai": loai, "tieu_de": tieu_de, "luc": luc}


class TestQuyetDinh:
    def test_1_co_id_da_len_lich(self):
        for loai in ("da_len_lich", "cong_khai"):
            q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11}, [_h("A" * 11, loai)], HOM_NAY)
            assert q["hanh_dong"] == "da_co" and q["video_id"] == "A" * 11 and not q["tay"]

    def test_2_co_id_nhap_de_ke_tai_moi(self):
        # 30/09/2026 chủ kênh chốt: nháp của lượt hỏng để kệ → tải mới, id cũ chỉ báo
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11}, [_h("A" * 11, "nhap", tieu_de="8 video")], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi" and "A" * 11 in q["nhap_thua"]
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11, "lan_tai_moi": 2, "ngay_tai": HOM_NAY},
                           [_h("A" * 11, "nhap")], HOM_NAY)
        assert q["hanh_dong"] == "dung"          # trần tải mới/ngày vẫn giữ

    def test_2b_so_da_hen_ma_kenh_khong_thay_thi_khong_tai_lai(self):
        for tt in ("da-len-lich", "xac-nhan", "lech-lich"):
            q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11, "trang_thai": tt}, [], HOM_NAY)
            assert q["hanh_dong"] == "bao_chu_kenh", tt
            q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11, "trang_thai": tt},
                               [_h("A" * 11, "khong_ro")], HOM_NAY)
            assert q["hanh_dong"] == "bao_chu_kenh", tt
        # sổ đã hẹn nhưng kênh báo LỖI TẢI → được tải mới
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11, "trang_thai": "da-len-lich"},
                           [_h("A" * 11, "loi_tai")], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi"

    def test_3_co_id_loi_tai_hoac_mat(self):
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11}, [_h("A" * 11, "loi_tai")], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi" and "A" * 11 in q["nhap_thua"]
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11}, [], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi"
        # trần 2 lần/ngày
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11, "lan_tai_moi": 2, "ngay_tai": HOM_NAY}, [], HOM_NAY)
        assert q["hanh_dong"] == "dung"
        q = mdd.quyet_dinh(DONG, {"video_id": "A" * 11, "lan_tai_moi": 2, "ngay_tai": "2026-09-28"}, [], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi"

    def test_4_khong_id_cung_tieu_de_da_dang(self):
        for loai in ("cong_khai", "da_len_lich", "khong_cong_khai"):
            q = mdd.quyet_dinh(DONG, {}, [_h("B" * 11, loai), _h("C" * 11, "nhap")], HOM_NAY)
            assert q["hanh_dong"] == "da_co" and q["tay"] and q["video_id"] == "B" * 11
            assert q["nhap_thua"] == ["C" * 11]

    def test_5_khong_id_cung_tieu_de_nhap_tai_moi(self):
        q = mdd.quyet_dinh(DONG, {}, [_h("C" * 11, "nhap", luc=datetime(2026, 9, 28)),
                                      _h("D" * 11, "nhap", luc=datetime(2026, 9, 29))], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi" and q["video_id"] == ""
        assert sorted(q["nhap_thua"]) == ["C" * 11, "D" * 11]

    def test_lich_da_dat_khop(self):
        f = mdd.lich_da_dat_khop
        assert f({"lich_dat": "01/10/2026 05:00", "trang_thai": "da-len-lich"}, "01/10/2026 05:00")
        assert not f({"lich_dat": "01/10/2026 05:00"}, "01/10/2026 05:30")
        # sổ đời trước (chưa có lich_dat): nhận `lich` khi trạng thái da-len-lich
        assert f({"lich": "01/10/2026 05:00", "trang_thai": "da-len-lich"}, "01/10/2026 05:00")
        assert not f({"lich": "01/10/2026 05:00", "trang_thai": "nhap"}, "01/10/2026 05:00")
        assert not f({}, "01/10/2026 05:00")

    def test_6_khong_id_rieng_tu(self):
        q = mdd.quyet_dinh(DONG, {}, [_h("E" * 11, "rieng_tu")], HOM_NAY)
        assert q["hanh_dong"] == "bao_chu_kenh"

    def test_7_khong_co_gi(self):
        q = mdd.quyet_dinh(DONG, {}, [_h("F" * 11, "cong_khai", tieu_de="video khác")], HOM_NAY)
        assert q["hanh_dong"] == "tai_moi"

    def test_tieu_de_so_bang_chuan_hoa(self):
        # Studio trả tiêu đề có khoảng trắng đầu/cuối, xuống dòng, dấu cách toàn khổ
        q = mdd.quyet_dinh(DONG, {}, [_h("B" * 11, "cong_khai", tieu_de="\n " + TD + "　 ")], HOM_NAY)
        assert q["hanh_dong"] == "da_co"


# ═══ Sổ + chọn mã + bao_dang ═══════════════════════════════════════════════

def test_so_video_id_nguyen_tu(tmp_path):
    so = mdd.SoVideoId(str(tmp_path / "so.json"))
    so.cap_nhat("TL1-T7/TL1-T7-0007", video_id="A" * 11, trang_thai="nhap")
    so.cap_nhat("TL1-T7/TL1-T7-0007", trang_thai="xac-nhan")
    m = mdd.SoVideoId(str(tmp_path / "so.json")).lay("TL1-T7/TL1-T7-0007")
    assert m["video_id"] == "A" * 11 and m["trang_thai"] == "xac-nhan" and m["cap_nhat"]
    # không sót tệp tạm (`vm-goc-mac-dinh` là thư mục conftest tự tạo cho mọi bài)
    assert [p.name for p in tmp_path.iterdir() if p.name != "vm-goc-mac-dinh"] == ["so.json"]


def _hang(ma, trang_thai, ngay="29/09/2026", gio="20:00", kenh="TL1-T7", tieu_de="t"):
    import nguon_tool as nt
    r = [""] * nt.RONG_DONG
    r[nt.O_MA], r[nt.O_KENH], r[nt.O_TRANG_THAI] = ma, kenh, trang_thai
    r[nt.O_NGAY], r[nt.O_GIO], r[nt.O_TIEU_DE] = ngay, gio, tieu_de
    return r


def test_chon_ma_can_dang():
    hang = [[""] * 64,
            _hang("M1", "EDIT XONG"),
            _hang("M2", "ĐÃ ĐĂNG"),
            _hang("M3", "EDIT XONG", gio="08:00"),                   # giờ đã qua
            _hang("M4", "ĐANG ĐĂNG · nháp AAAAAAAAAAA", gio="08:00"),   # dở: vẫn nhận
            _hang("M5", "EDIT XONG", ngay="30/09/2026"),              # mai
            _hang("M6", "EDIT XONG", kenh="TL2-T7"),
            _hang("M7", "", ngay="", gio="")]
    assert [d["ma"] for d in mdd.chon_ma_can_dang(hang, "TL1-T7", BAY_GIO)] == ["M1", "M4"]
    assert [d["ma"] for d in mdd.chon_ma_can_dang(hang, "TL1-T7", BAY_GIO, bo_loc_ngay=True,
                                                  ma="M5")] == ["M5"]


def test_trung_tieu_de():
    hang = [[""] * 64, _hang("M1", "", tieu_de="A B"), _hang("M2", "", tieu_de="A  B"), _hang("M3", "", tieu_de="C")]
    assert mdd.trung_tieu_de(hang, "TL1-T7") == [("M1", "M2")]


def test_bao_dang_them_video_id_va_hang_cho(tmp_path, monkeypatch):
    import nguon_tool as nt
    importlib.reload(nt)
    monkeypatch.setattr(nt, "__file__", str(tmp_path / "nguon_tool.py"))
    gui = []
    song = {"on": False}

    class _Tra:
        def read(self):
            return b"{}"

    def urlopen(req, timeout=0):
        if not song["on"]:
            raise OSError("trạm tắt")
        gui.append(json.loads(req.data.decode("utf-8")))
        return _Tra()
    monkeypatch.setattr(nt.urllib.request, "urlopen", urlopen)
    cfg = {"tram": "http://127.0.0.1:1"}
    assert nt.bao_dang(cfg, "M1", "ĐÃ ĐĂNG", kenh="TL1-T7", video_id="A" * 11, lich="30/09/2026 20:00") is False
    cho = json.loads((tmp_path / "cho-bao-TL1-T7.json").read_text(encoding="utf-8"))
    assert cho[0]["them"] == {"video_id": "A" * 11, "lich": "30/09/2026 20:00"}
    song["on"] = True
    assert nt.bao_dang(cfg, "M2", "ĐÃ ĐĂNG", kenh="TL1-T7") is True
    assert gui[0] == {"kenh": "TL1-T7", "ma": "M1", "trang_thai": "ĐÃ ĐĂNG",
                      "video_id": "A" * 11, "lich": "30/09/2026 20:00"}
    assert gui[1] == {"kenh": "TL1-T7", "ma": "M2", "trang_thai": "ĐÃ ĐĂNG"}   # gọi kiểu cũ: y hệt trước
    assert not (tmp_path / "cho-bao-TL1-T7.json").exists()


# ═══ StudioGia ═════════════════════════════════════════════════════════════

class KenhGia:
    def __init__(self):
        self.uc = UC
        self.video = []
        self.dem = 0
        self.loi = set()          # tiêm lỗi
        self.lech_phut = 0
        self.dut_con = 0          # số lần go(mo_ta) sẽ ném đứt
        self.lan_dat_tep_video = 0
        self.an_gio = False       # Studio chỉ hiện "Đã lên lịch", không kèm giờ (đo 30/09)
        self.mhkt_nguon = {}      # videoId nguồn trong hộp chọn MHKT → có MHKT để nhập không
        self.mhkt_nhap_tu = []
        self.tien_do = None       # None = giả lập tải xong ở lần đọc 2; [] = không đọc được gì
        self.goi_studio = {}      # videoId → {"status", "lengthSeconds"} cho hậu kiểm

    def moi_id(self):
        self.dem += 1
        return ("VID" + str(self.dem)).ljust(11, "x")

    def tim_video(self, vid):
        return next((v for v in self.video if v["id"] == vid), None)


def _chu_trang_thai(v, an_gio=False):
    if v["loai"] == "da_len_lich":
        if an_gio:
            return "Chế độ hiển thị Đã lên lịch"
        l = v["lich"]
        return "Đã lên lịch\n{0} thg {1}, {2}, {3:%H:%M}".format(l.day, l.month, l.year, l)
    return {"nhap": "Nháp", "cong_khai": "Công khai", "rieng_tu": "Riêng tư",
            "loi_tai": "Tải lên không thành công"}.get(v["loai"], "")


class StudioGia:
    """Cùng giao diện với `cdp_studio.TrangStudio`."""

    def __init__(self, k: KenhGia):
        self.k = k
        self._url = "about:blank"
        self.trang = ""
        self.q = None
        self.vid_sua = None
        self.hop = None
        self.da_xong_hop = False
        self.dem_id = {}
        self.dem_tien_do = 0
        self.dong_ = False
        self.bang_chung = []
        self.du_phong = {}
        self._go = {}
        self._o_cuoi = None

    # điều hướng
    def mo(self, url, cho_khoa=None, han=60):
        self._url, self.trang, self.hop = url, "", None
        if url.rstrip("/") == "https://studio.youtube.com":
            self._url = "https://studio.youtube.com/channel/{0}".format(self.k.uc)
        elif "d=ud" in url:
            self.hop = {"vid": None, "buoc": 0}
        elif "/videos/upload" in url:
            self.trang = "ds"
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            self.q = json.loads(qs["filter"][0])[0]["value"] if "filter" in qs else None
        elif "/video/" in url and url.endswith("/edit"):
            self.trang = "sua"
            self.vid_sua = url.split("/video/")[1].split("/")[0]
        return self.tim(cho_khoa) if cho_khoa else True

    def url(self):
        return self._url

    # trạng thái → khoá hiện
    def _v(self):
        return self.k.tim_video(self.hop["vid"]) if self.hop and self.hop.get("vid") else None

    def _hien(self, khoa):
        h = self.hop or {}
        b = h.get("buoc")
        co_hop = self.hop is not None
        co_vid = co_hop and bool(h.get("vid"))
        con = h.get("con")            # hộp con đang mở
        m = {
            "hop_upload": co_hop,
            "nut_chon_tep": co_hop and not co_vid, "o_tep_video": co_hop and not co_vid,
            "link_video": co_vid, "tien_do": co_vid, "dong_hop_upload": co_hop,
            "tieu_de": (co_vid and b == 0 and not con) or self.trang == "sua",
            "mo_ta": (co_vid and b == 0 and not con) or self.trang == "sua",
            "nut_thumbnail": co_vid and b == 0 and not con,
            "playlist_mo": (co_vid and b == 0 and not con) or self.trang == "sua",
            "khong_tre_em": co_vid and b == 0 and not con,
            "hien_them": (co_vid and b == 0 and not con) or self.trang == "sua",
            "ai_co": co_vid and b == 0 and h.get("them") and not con,
            "o_the": (co_vid and b == 0 and h.get("them") and not con) or self.trang == "sua",
            "hang_sua_nhap": self.trang == "ds" and any(v["loai"] == "nhap" for v in self._hang()),
            "the_da_co": (co_vid and bool((self._v() or {}).get("the")))
                         or (self.trang == "sua" and bool((self.k.tim_video(self.vid_sua) or {}).get("the"))),
            "playlist_muc": con == "playlist", "playlist_xong": con == "playlist",
            "nut_tiep": co_vid and b < 3 and not con,
            "phu_de_them": co_vid and b == 1 and not con, "mhkt_them": co_vid and b == 1 and not con,
            "the_them": co_vid and b == 1 and not con, "mhkt_nhap": co_vid and b == 1 and not con,
            "phu_de_tai_tep": con == "phu_de", "phu_de_ngon_ngu": False,
            "phu_de_co_moc": con == "phu_de_tep", "phu_de_tiep_tuc": con == "phu_de_tep",
            "phu_de_xong": con == "phu_de_xong",
            "mhkt_video_dau": False, "mhkt_xac_nhan": False, "nut_thu_lai": con == "mhkt_loi",
            "hop_mhkt": con in ("mhkt", "mhkt_chon"), "mhkt_mau": con == "mhkt",
            "mhkt_nhap_trong": con == "mhkt", "mhkt_chon_video": con == "mhkt_chon",
            "mhkt_luu": con == "mhkt" and h.get("mhkt_mau_da") is not None,
            "mhkt_phan_tu": con == "mhkt" and h.get("mhkt_mau_da") is not None,
            "mhkt_hop_chon": con == "mhkt_chon", "mhkt_dong_chon": con == "mhkt_chon",
            "mhkt_tim_video": con == "mhkt_chon", "mhkt_mau_video_dk": False,
            "hop_the": con in ("the", "the_menu", "the_chon_ds", "the_chon_video"),
            "the_loai_dau": con == "the" and not h.get("the_ds"),
            "the_nut_them": con == "the" and bool(h.get("the_ds")),
            "the_menu_video": con == "the_menu", "the_menu_ds": con == "the_menu",
            "the_chon_ds": con == "the_chon_ds", "the_chon_video": con == "the_chon_video",
            "the_tim_video": con == "the_chon_video",
            "the_dong_chon": con in ("the_chon_ds", "the_chon_video"),
            "the_moc": con == "the" and bool(h.get("the_ds")), "the_moc_o": con == "the" and bool(h.get("the_ds")),
            "the_muc_ten": con == "the" and bool(h.get("the_ds")),
            "the_luu": con == "the", "hop_con_huy": con == "the", "the_dau_phat": con == "the",
            "the_xoa": False,
            "len_lich_mo": co_vid and b == 3, "nut_xong": co_vid and b == 3,
            "o_ngay_mo": co_vid and b == 3 and h.get("lich_mo"),
            "o_gio": co_vid and b == 3 and h.get("lich_mo"),
            "o_ngay": con == "ngay",
            "hop_da_xong": self.da_xong_hop, "dong_hop_da_xong": self.da_xong_hop,
            "hang_video": self.trang == "ds" and bool(self._hang()),
            "hang_tieu_de": self.trang == "ds" and bool(self._hang()),
            "danh_sach_trong": self.trang == "ds" and not self._hang(),
            "hien_thi_trang_sua": self.trang == "sua" and bool(self.k.tim_video(self.vid_sua)),
        }
        return bool(m.get(khoa))

    def tim(self, khoa, han=10, hien=True, cho_tat=False, trong=None, thu=0):
        if khoa in self.k.loi and khoa in ("nut_chon_tep", "o_tep_video"):
            return None
        if not self._hien(khoa):
            return None
        so = 3 if khoa == "playlist_muc" else 6 if khoa == "mhkt_mau" else 1
        if khoa in ("the_moc", "the_moc_o", "the_muc_ten"):
            so = len((self.hop or {}).get("the_ds") or [])
            if thu >= so:
                return None
        return {"khoa": khoa, "id": "{0}#{1}".format(khoa, thu), "cach": "chon#1", "so": so,
                "thu": thu}

    def tim_chua(self, khoa, chuoi, han=8):
        h = self.hop or {}
        if h.get("con") == "mhkt_chon" and khoa == "mhkt_chon_video":
            if self.k.tim_video(chuoi) or chuoi in self.k.mhkt_nguon:
                return {"khoa": khoa, "id": "mhkt#" + chuoi, "vid": chuoi, "cach": "chua", "so": 1}
            return None
        if h.get("con") != "the_chon_video":
            return None
        cua_kenh = {v["id"] for v in self.k.video if v["loai"] == "cong_khai"}
        if chuoi in cua_kenh or chuoi in (h.get("the_tim") or ""):
            return {"khoa": khoa, "id": "vid#" + chuoi, "vid": chuoi, "cach": "chua", "so": 1}
        return None

    def tim_chu(self, chu, han=5, cho_tat=False):
        return None

    def co(self, khoa, **kw):
        return self.tim(khoa) is not None

    def cho_mat(self, khoa, han=10):
        return not self.co(khoa)

    def cho_mat_ca_tat(self, khoa, han=10):
        return not self.co(khoa)

    def bi_che(self, khoa):
        return False

    def _khoa(self, x):
        return x["khoa"] if isinstance(x, dict) else x

    def bam(self, x, hau_dieu_kien=None, han_hau=10, han_tim=10, cho_tat=False):
        khoa = self._khoa(x)
        if khoa == "hang_sua_nhap":
            vid = x["vid"]
            self.trang, self.hop = "", {"vid": vid, "buoc": 0}
            self._check(hau_dieu_kien, khoa)
            return x
        if not self._hien(khoa):
            raise cdp_studio.LoiThaoTac(khoa, "không thấy")
        h = self.hop
        v = self._v()
        if khoa == "nut_tiep":
            h["buoc"] += 1
        elif khoa == "hien_them":
            h["them"] = True
        elif khoa in ("khong_tre_em", "ai_co"):
            v[khoa] = True
        elif khoa == "playlist_mo":
            h["con"] = "playlist"
        elif khoa == "playlist_muc":
            v["playlist"] = "DS {0}".format(x.get("thu", 0) + 1)
        elif khoa == "playlist_xong":
            h["con"] = None
        elif khoa == "phu_de_them":
            h["con"] = "phu_de"
        elif khoa == "phu_de_tai_tep":
            h["con"] = "phu_de_tep"
        elif khoa == "phu_de_co_moc":
            h["co_moc"] = True
        elif khoa == "phu_de_xong":
            h["con"] = None
            v["phu_de"] = True
        elif khoa == "mhkt_nhap":
            h["con"] = "mhkt_loi" if "mhkt" in self.k.loi else "mhkt"
        elif khoa == "nut_thu_lai":
            h["con"] = "mhkt_loi" if "mhkt" in self.k.loi else "mhkt"
        elif khoa == "mhkt_mau":
            h["mhkt_mau_da"] = x.get("thu", 0)
        elif khoa == "mhkt_nhap_trong":
            h["con"] = "mhkt_chon"
        elif khoa == "mhkt_chon_video":
            nguon = x.get("vid") if isinstance(x, dict) else None
            if nguon and not self.k.mhkt_nguon.get(nguon, True):
                h["mhkt_khong_nguon"] = True          # Studio: "Video này không có MHKT để nhập"
            else:
                h["con"], h["mhkt_mau_da"] = "mhkt", "nhap:" + str(nguon)
                self.k.mhkt_nhap_tu.append(nguon)
        elif khoa == "mhkt_them":
            h["con"] = "mhkt_loi" if "mhkt" in self.k.loi else "mhkt"
        elif khoa == "mhkt_dong_chon":
            h["con"] = "mhkt"
        elif khoa == "mhkt_luu":
            v["mhkt"] = True
            h["con"] = None
        elif khoa == "the_them":
            h["con"], h["the_ds"] = "the", list(v.get("the_card") or [])
        elif khoa == "the_loai_dau":
            h["con"] = "the_chon_video" if x.get("thu", 0) == 0 else "the_chon_ds"
        elif khoa == "the_nut_them":
            h["con"] = "the_menu"
        elif khoa == "the_menu_video":
            h["con"] = "the_chon_video"
        elif khoa == "the_menu_ds":
            h["con"] = "the_chon_ds"
        elif khoa == "the_chon_ds":
            h["the_ds"] = (h.get("the_ds") or []) + ["ds"]
            h["the_gio"] = (h.get("the_gio") or []) + [h.get("dau_phat", "00:00:00")]
            h["con"] = "the"
        elif khoa == "the_chon_video":
            h["the_ds"] = (h.get("the_ds") or []) + ["video:" + x["vid"]]
            h["the_gio"] = (h.get("the_gio") or []) + [h.get("dau_phat", "00:00:00")]
            h["con"] = "the"
        elif khoa == "the_dong_chon":
            h["con"] = "the"
        elif khoa == "the_moc":
            pass
        elif khoa == "the_luu":
            v["the_card"] = list(h.get("the_ds") or [])
            v["the_gio"] = list(h.get("the_gio") or [])
            h["con"] = None
        elif khoa == "hop_con_huy":
            h["con"] = None
        elif khoa == "len_lich_mo":
            h["lich_mo"] = True
        elif khoa == "o_ngay_mo":
            h["con"] = "ngay"
        elif khoa == "nut_xong":
            ngay = cdp_studio.chuan_chu(h.get("ngay_chu"))
            dd = mdd.phan_tich_ngay(ngay)[0]
            g = mdd.phan_tich_gio(h.get("gio_chu"))
            v["loai"] = "da_len_lich"
            v["lich"] = datetime(dd.year, dd.month, dd.day, g[0], g[1]) + timedelta(minutes=self.k.lech_phut)
            self.hop = None
            self.da_xong_hop = True
        elif khoa == "dong_hop_da_xong":
            self.da_xong_hop = False
        elif khoa == "dong_hop_upload":
            self.hop = None
        self._o_cuoi = khoa
        self._check(hau_dieu_kien, khoa)
        return x if isinstance(x, dict) else {"khoa": khoa}

    def _check(self, hau, khoa):
        if hau is not None and not hau():
            raise cdp_studio.LoiThaoTac(khoa, "hậu điều kiện không đạt")

    def go(self, khoa, chu, han_tim=10):
        self.bam(khoa)
        v = self._v()
        if khoa == "mo_ta" and self.k.dut_con > 0:
            self.k.dut_con -= 1
            raise ConnectionError("đứt DevTools giả")
        v[khoa] = chu
        return chu

    def go_tho(self, khoa, chu, xoa=True, han_tim=10):
        self.bam(khoa)
        k = self._khoa(khoa)
        self._go[k] = chu
        if k == "the_tim_video":
            self.hop["the_tim"] = chu
        if k == "the_dau_phat":
            self.hop["dau_phat"] = chu

    def doc_tat_ca(self, khoa):
        h = self.hop or {}
        if khoa == "the_moc" and h.get("con") == "the":
            return [{"chu": g, "value": g} for g in sorted(h.get("the_gio") or [])]
        if khoa == "the_dau_phat" and h.get("con") == "the":
            return [{"chu": h.get("dau_phat", ""), "value": h.get("dau_phat", "")}]
        return []

    def phim(self, ten, n=1, modifiers=0):
        h = self.hop or {}
        if ten == "Enter":
            o = self._o_cuoi
            if o == "o_the":
                self._v()["the"] = mdd.tach_the(self._go.get("o_the"))
            elif o == "o_ngay":
                h["ngay_chu"] = self._go.get("o_ngay")
                h["con"] = None
            elif o == "o_gio":
                h["gio_chu"] = self._go.get("o_gio")
        elif ten == "Escape" and h:
            h["con"] = None

    def doc_chu(self, x, han=5):
        khoa = self._khoa(x)
        h = self.hop or {}
        if khoa == "o_ngay_mo":
            return h.get("ngay_chu") or ""
        if khoa == "nut_xong":
            return "Lên lịch"
        if khoa == "tien_do":
            self.dem_tien_do += 1
            if self.k.tien_do is not None:
                ds = self.k.tien_do
                return ds[min(self.dem_tien_do - 1, len(ds) - 1)] if ds else ""
            return "Đang tải lên 40%" if self.dem_tien_do < 2 else "Đã tải lên"
        if khoa == "mhkt_hop_chon":
            return "Chọn một video cụ thể Video này không có màn hình kết thúc để nhập" \
                if h.get("mhkt_khong_nguon") else "Chọn một video cụ thể"
        if khoa == "hop_upload":
            return ("Tải lên không thành công" if "loi_tai" in self.k.loi else
                    "Bước {0}".format(h.get("buoc")))
        if khoa == "hien_thi_trang_sua":
            return _chu_trang_thai(self.k.tim_video(self.vid_sua), self.k.an_gio)
        if khoa == "playlist_muc":
            return "DS {0}".format(x.get("thu", 0) + 1)
        return ""

    def doc_thuoc_tinh(self, x, ten, han=5):
        khoa = self._khoa(x)
        v = self._v() or {}
        if khoa == "link_video" and ten == "href":
            return "https://youtu.be/" + self.hop["vid"]
        if khoa == "o_gio" and ten == "value":
            return (self.hop or {}).get("gio_chu")
        if ten == "aria-checked":
            if khoa in ("khong_tre_em", "ai_co"):
                return "true" if v.get(khoa) else "false"
            if khoa == "phu_de_co_moc":
                return "true" if (self.hop or {}).get("co_moc") else "false"
            return "false"
        return None

    def _hang(self):
        vs = [v for v in reversed(self.k.video)
              if self.q is None or self.q in v.get("tieu_de", "")]
        return vs

    def doc_hang(self):
        ra = []
        for v in self._hang():
            ra.append({"tieu_de": v.get("tieu_de", ""),
                       "hrefs": [] if v.get("an_id") else ["https://studio.youtube.com/video/{0}/edit".format(v["id"])],
                       "chu": _chu_trang_thai(v, self.k.an_gio), "che_do": _chu_trang_thai(v, self.k.an_gio),
                       "nut_nhap": ({"khoa": "hang_sua_nhap", "vid": v["id"]} if v["loai"] == "nhap" else None)})
        return ra

    def dat_tep(self, khoa_nut, duong, khoa_input=None, han=8):
        if khoa_nut == "nut_chon_tep":
            if "nut_chon_tep" in self.k.loi:
                raise cdp_studio.LoiThaoTac(khoa_nut, "không thấy")
            self.k.lan_dat_tep_video += 1
            vid = self.k.moi_id()
            self.k.video.append({"id": vid, "tieu_de": "8 video", "loai": "nhap"})
            self.hop["vid"] = vid
            return "hop_chon_tep"
        v = self._v()
        if khoa_nut == "nut_thumbnail":
            v["thumbnail"] = duong
        elif khoa_nut == "phu_de_tiep_tuc":
            v["srt"] = duong
            self.hop["con"] = "phu_de_xong"
        return "hop_chon_tep"

    def don_hop_la(self, che=None):
        return 0

    def ghi_bang_chung(self, nhan):
        self.bang_chung.append(nhan)
        return {}

    def giu_khi_roi(self, giu=True):
        pass

    def dong(self):
        self.dong_ = True

    def bat_json(self, url, chua_url, han=30, toi_da=4):
        if chua_url == "get_creator_videos" and "/video/" in url:
            vid = url.split("/video/")[1].split("/")[0]
            g = self.k.goi_studio.get(vid)
            return [{"videos": [dict(g, videoId=vid)]}] if g else []
        return []


# ═══ Luồng trọn + tiêm lỗi ═════════════════════════════════════════════════

MO_TA = "毎晩同じ時刻に目が覚める人は…\n\n📌目次\n00:00 はじめに\n01:23 本題"


@pytest.fixture
def moi(tmp_path):
    done = tmp_path / "DONE"
    goi = done / "TL1-T7-0007"
    goi.mkdir(parents=True)
    _mp4(goi, 600)
    (goi / "3-phu-de.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nx\n", encoding="utf-8")
    (goi / "thumb_001.png").write_bytes(b"png")
    return tmp_path


def _dong(**kw):
    d = {"ma": "TL1-T7-0007", "kenh": "TL1-T7", "tieu_de": TD, "mo_ta": MO_TA,
         "the": "目覚める, 潜在意識, 夜中", "trang_thai": "EDIT XONG",
         "link": ["https://youtu.be/AAAAAAAAAAA", "", "", ""], "ngay": "30/09/2026", "gio": "20:00"}
    d.update(kw)
    return d


def _may(tmp_path, kenh_gia, bao, **kw):
    tabs = []

    def tao():
        t = StudioGia(kenh_gia)
        tabs.append(t)
        return t
    m = mdd.MayDangDom("TL1-T7", cdp_studio.doc_bo_chon(), tao,
                       mdd.SoVideoId(str(tmp_path / "so.json")), bao, str(tmp_path / "DONE"),
                       nhat_ky=lambda s: None, bay_gio=lambda: BAY_GIO, ngu=lambda s: None,
                       duong_uc=str(tmp_path / "uc.json"), duong_dodang=str(tmp_path / "dodang.json"),
                       han_mhkt=1, cai_dat_kenh={"ngon_ngu": "ja"},
                       thu_muc_chi_so=kw.pop("thu_muc_chi_so", str(tmp_path / "chi-so-rong")), **kw)
    m._tabs_gia = tabs
    return m


class Bao:
    def __init__(self):
        self.ds = []

    def __call__(self, ma, tt, **them):
        self.ds.append((ma, tt, them))
        return True

    def trang_thai(self):
        return [x[1] for x in self.ds]


class TestLuong:
    def test_tron_luong_tai_moi(self, moi):
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert len(k.video) == 1
        v = k.video[0]
        vid = v["id"]
        assert v["tieu_de"] == TD and v["mo_ta"] == MO_TA and "\n📌目次\n" in v["mo_ta"]
        assert v["khong_tre_em"] and v["ai_co"] and v["playlist"] == "DS 1"
        assert v["the"] == ["目覚める", "潜在意識", "夜中"]
        assert v["thumbnail"].endswith("thumb_001.png") and v["srt"].endswith("3-phu-de.srt")
        assert v["phu_de"] and v["mhkt"] and v["the_card"] == ["ds", "video:AAAAAAAAAAA"]
        assert v["loai"] == "da_len_lich" and v["lich"] == datetime(2026, 9, 30, 20, 0)
        # videoId báo trạm NGAY sau chọn tệp, rồi mới ĐÃ ĐĂNG kèm id + lịch
        assert bao.ds[0] == ("TL1-T7-0007", "ĐANG ĐĂNG · nháp " + vid, {"video_id": vid})
        assert bao.ds[-1] == ("TL1-T7-0007", "ĐÃ ĐĂNG", {"video_id": vid, "lich": "30/09/2026 20:00"})
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["video_id"] == vid and so["trang_thai"] == "xac-nhan" and so["lan_tai_moi"] == 1
        assert so["phu_de"] == "ok" and so["mhkt"] == "ok:mau" and so["the"] == "ok:2"
        assert so["tai_xong"] is True and so["tai_xong_luc"], "phải ghi bằng chứng tải xong vào sổ"
        assert json.loads((moi / "uc.json").read_text(encoding="utf-8")) == {"TL1-T7": UC}
        assert not (moi / "dodang.json").exists()

    def test_the_video_top_48h_cua_kenh(self, moi):
        """Cột Link card rỗng → thẻ trỏ video CÔNG KHAI view 48h cao nhất của
        kênh; loại video đang đăng + video đã hẹn lịch trong sổ."""
        k, bao = KenhGia(), Bao()
        for vid in ("PUBAxxxxxxx", "PUBBxxxxxxx", "PUBCxxxxxxx", "PUBDxxxxxxx", "PUBExxxxxxx"):
            k.video.append({"id": vid, "tieu_de": "cũ " + vid, "loai": "cong_khai"})
        g = _chi_so_gia(moi, top48={"PUBBxxxxxxx": 90, "PUBAxxxxxxx": 50, "HENxxxxxxxx": 70,
                                    "PUBCxxxxxxx": 10, "PUBDxxxxxxx": 5, "PUBExxxxxxx": 1})
        m = _may(moi, k, bao, thu_muc_chi_so=g)
        m.so.cap_nhat("TL1-T7/TL1-T7-0009", video_id="HENxxxxxxxx", trang_thai="xac-nhan",
                      lich="02/10/2026 20:00")
        assert m.chay([_dong(link=["", "", "", ""])]) == mdd.MA_XONG
        v = next(x for x in k.video if x["tieu_de"] == TD)
        assert v["the_card"] == ["ds", "video:PUBBxxxxxxx", "video:PUBAxxxxxxx",
                                 "video:PUBCxxxxxxx", "video:PUBDxxxxxxx"]
        # mốc = 5 mốc trong 50% cuối (thời lượng mvhd 600s), đặt qua ĐẦU PHÁT trước mỗi thẻ
        assert v["the_gio"] == mdd.compute_card_timestamps(600, n=5, tail_gap=10)
        assert m.so.lay("TL1-T7/TL1-T7-0007")["the"] == "ok:5"

    def test_mhkt_nhap_tu_video_da_co_mhkt_bo_qua_nguon_khong_co(self, moi):
        """30/09/2026 (TL2-T7-0007/0008, TL1-T7-0013): chỉ nhập từ video mà sổ ghi
        mhkt=ok…; nguồn Studio báo "không có MHKT" thì thử nguồn kế."""
        k, bao = KenhGia(), Bao()
        k.mhkt_nguon = {"CUxxxxxxxx9": False, "CUxxxxxxxx2": True}
        m = _may(moi, k, bao)
        m.so.cap_nhat("TL1-T7/TL1-T7-0001", video_id="CUxxxxxxxx2", trang_thai="xac-nhan", mhkt="ok:nhap")
        m.so.cap_nhat("TL1-T7/TL1-T7-0002", video_id="CUxxxxxxxx9", trang_thai="xac-nhan", mhkt="ok")
        m.so.cap_nhat("TL1-T7/TL1-T7-0003", video_id="KHONGxxxxxx", trang_thai="xac-nhan", mhkt="bo")
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert k.mhkt_nhap_tu == ["CUxxxxxxxx2"], "video mhkt=bo không được làm nguồn; nguồn báo thiếu thì bỏ"
        assert m.so.lay("TL1-T7/TL1-T7-0007")["mhkt"] == "ok:nhap"

    def test_mhkt_khong_nguon_hop_le_thi_dung_mau(self, moi):
        k, bao = KenhGia(), Bao()
        k.mhkt_nguon = {"CUxxxxxxxx1": False}
        m = _may(moi, k, bao)
        m.so.cap_nhat("TL1-T7/TL1-T7-0002", video_id="CUxxxxxxxx1", trang_thai="xac-nhan", mhkt="ok")
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert m.so.lay("TL1-T7/TL1-T7-0007")["mhkt"] == "ok:mau"
        v = next(x for x in k.video if x["tieu_de"] == TD)
        assert v["mhkt"] is True

    def test_khong_doc_duoc_tien_do_thi_KHONG_len_lich(self, moi):
        """30/09/2026: bản cũ trả False sau 30 giây không đọc được tiến độ và vẫn bấm
        Lên lịch. Giờ: chờ tới hạn theo dung lượng, không bằng chứng → không lên lịch."""
        k, bao = KenhGia(), Bao()
        k.tien_do = []
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_HONG
        v = next(x for x in k.video)
        assert v["loai"] == "nhap", "chưa có bằng chứng tải xong thì không được bấm Lên lịch"
        assert "ĐÃ ĐĂNG" not in bao.trang_thai()
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["trang_thai"] == "nhap" and so.get("tai_xong") is False

    def test_dang_xu_ly_la_bang_chung_tai_xong(self, moi):
        k, bao = KenhGia(), Bao()
        k.tien_do = ["Đã tải được 83% ... Còn 24 giây", "Đang xử lý đến độ phân giải tối đa là HD ... Còn 3 phút"]
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert next(x for x in k.video)["loai"] == "da_len_lich"

    def test_hau_kiem_thoi_luong_khop_ghi_so(self, moi):
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        k.goi_studio["VID1xxxxxxx"] = {"status": "VIDEO_STATUS_PROCESSED", "lengthSeconds": "600"}
        assert m.chay([_dong()]) == mdd.MA_XONG
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["tai_xong"] is True and so["thoi_luong"] == 600.0 and so["thoi_luong_tep"] == 600.0
        assert so["hau_kiem"].startswith("ok")

    def test_hau_kiem_hong_thi_danh_dau_tai_moi(self, moi):
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        k.goi_studio["VID1xxxxxxx"] = {"status": "VIDEO_STATUS_FAILED"}
        assert m.chay([_dong()]) == mdd.MA_HONG
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["trang_thai"] == "tai-hong" and so["tai_xong"] is False
        assert bao.trang_thai()[-1].startswith("ĐANG ĐĂNG · tải hỏng")
        qd = mdd.quyet_dinh(_dong(), so, [{"video_id": "VID1xxxxxxx", "tieu_de": TD, "loai": "da_len_lich"}],
                            BAY_GIO.date().isoformat())
        assert qd["hanh_dong"] == "tai_moi", "gói tải hỏng: lượt sau TẢI MỚI (nháp/bản hỏng để kệ)"

    def test_hau_kiem_hong_khong_cham_vm_logs_that(self, moi):
        """Canh cô lập (30/09/2026, rò 22:18/22:23): chạy luồng hậu kiểm HỎNG xong,
        không tệp nào trong vm/logs THẬT bị tạo/đổi; sự cố nằm cạnh sổ tạm."""
        that = Path(mdd.THU_MUC_LOG)
        truoc = {p.name: p.stat().st_mtime for p in that.glob("*")} if that.is_dir() else {}
        md = Path(mdd.GOC).parent / "workspace" / "loi-chay-max.md"
        md_truoc = md.stat().st_mtime if md.exists() else None
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        k.goi_studio["VID1xxxxxxx"] = {"status": "VIDEO_STATUS_FAILED"}
        m.chay([_dong()])
        sau = {p.name: p.stat().st_mtime for p in that.glob("*")} if that.is_dir() else {}
        assert {n: t for n, t in sau.items() if truoc.get(n) != t} == {}, "bài kiểm chạm vm/logs thật"
        assert (md.stat().st_mtime if md.exists() else None) == md_truoc, "bài kiểm ghi loi-chay-max.md thật"
        assert (moi / "su-co-tai-len.jsonl").exists()

    def test_mhkt_loi_van_len_lich(self, moi):
        k, bao = KenhGia(), Bao()
        k.loi.add("mhkt")
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert k.video[0]["loai"] == "da_len_lich"
        assert m.so.lay("TL1-T7/TL1-T7-0007")["mhkt"] == "bo"
        assert bao.trang_thai()[-1] == "ĐÃ ĐĂNG"
        assert any("Màn hình kết thúc" in c for c in m.bao_cao["canh_bao"])

    def test_bo_chon_chinh_hong_truoc_cham_kenh_ma_3(self, moi):
        k, bao = KenhGia(), Bao()
        k.loi.add("nut_chon_tep")
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_LUI
        assert k.video == [] and bao.ds == []

    def test_dut_sau_co_id_ma_1_luot_sau_tai_moi_de_ke_nhap(self, moi):
        """30/09/2026 chủ kênh chốt: nháp của lượt hỏng để kệ (chủ kênh xoá) —
        lượt sau TẢI MỚI, id cũ vào `id_cu`, không mở lại/sửa/xoá nháp."""
        k, bao = KenhGia(), Bao()
        k.dut_con = 1
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_HONG
        vid = k.video[0]["id"]
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["video_id"] == vid and so["trang_thai"] == "nhap"
        assert bao.trang_thai() == ["ĐANG ĐĂNG · nháp " + vid]
        bao2 = Bao()
        m2 = _may(moi, k, bao2)
        assert m2.chay([_dong(trang_thai="ĐANG ĐĂNG · nháp " + vid)]) == mdd.MA_XONG
        assert k.lan_dat_tep_video == 2 and len(k.video) == 2
        cu, moi_v = k.tim_video(vid), k.video[1]
        assert cu["loai"] == "nhap"                       # nháp cũ để nguyên
        assert moi_v["loai"] == "da_len_lich" and moi_v["tieu_de"] == TD
        so2 = m2.so.lay("TL1-T7/TL1-T7-0007")
        assert so2["video_id"] == moi_v["id"] and so2["id_cu"] == [vid] and so2["lan_tai_moi"] == 2
        assert {"ma": "TL1-T7-0007", "video_id": vid} in m2.bao_cao["nhap_thua"]
        assert bao2.ds[-1][1] == "ĐÃ ĐĂNG" and bao2.ds[-1][2]["video_id"] == moi_v["id"]

    def test_xac_nhan_da_len_lich_khong_gio_theo_lich_dat(self, moi):
        """30/09 TL1-T7-0011: Studio chỉ hiện "Chế độ hiển thị Đã lên lịch" (không
        giờ) → giờ đã đọc lại lúc tải khớp sổ thì coi là xác nhận, không lặp."""
        k, bao = KenhGia(), Bao()
        k.an_gio = True
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["trang_thai"] == "xac-nhan" and so["xac_nhan_cach"] == "trang-thai+lich-dat"
        assert so["lich_dat"] == "30/09/2026 20:00"
        assert bao.ds[-1] == ("TL1-T7-0007", "ĐÃ ĐĂNG", {"video_id": k.video[0]["id"],
                                                         "lich": "30/09/2026 20:00"})

    def test_xac_nhan_so_doi_truoc_khong_lich_dat(self, moi):
        """Sổ đời trước (TL1-T7-0011 lúc 12:11): da-len-lich + lich, chưa có lich_dat."""
        k, bao = KenhGia(), Bao()
        k.an_gio = True
        k.video.append({"id": "SCHEDxxxxxx", "tieu_de": TD, "loai": "da_len_lich",
                        "lich": datetime(2026, 9, 30, 20, 0)})
        m = _may(moi, k, bao)
        m.so.cap_nhat("TL1-T7/TL1-T7-0007", video_id="SCHEDxxxxxx", trang_thai="da-len-lich",
                      lich="30/09/2026 20:00")
        assert m.chay([_dong(trang_thai="ĐANG ĐĂNG · nháp SCHEDxxxxxx")]) == mdd.MA_XONG
        assert k.lan_dat_tep_video == 0
        assert m.so.lay("TL1-T7/TL1-T7-0007")["trang_thai"] == "xac-nhan"
        assert bao.ds[-1][1] == "ĐÃ ĐĂNG"

    def test_chua_xac_nhan_3_luot_thi_thoi_kiem(self, moi):
        """Không đọc được giờ + không có giờ đã đặt khớp → chua_xac_nhan; lượt
        thứ 3 đổi Trạng thái đăng khỏi ĐANG ĐĂNG để không mở Chrome mãi."""
        k = KenhGia()
        k.an_gio = True
        k.video.append({"id": "SCHEDxxxxxx", "tieu_de": TD, "loai": "da_len_lich",
                        "lich": datetime(2026, 9, 30, 20, 0)})
        tt = []
        for lan in range(3):
            bao = Bao()
            m = _may(moi, k, bao)
            if lan == 0:
                m.so.cap_nhat("TL1-T7/TL1-T7-0007", video_id="SCHEDxxxxxx", trang_thai="da-len-lich")
            assert m.chay([_dong(trang_thai="ĐANG ĐĂNG · nháp SCHEDxxxxxx")]) == mdd.MA_HONG
            tt.append(bao.trang_thai())
        assert k.lan_dat_tep_video == 0
        assert tt[0] == [] and tt[1] == []
        assert tt[2] == ["CHƯA XÁC NHẬN LỊCH · SCHEDxxxxxx"]
        so = mdd.SoVideoId(str(moi / "so.json")).lay("TL1-T7/TL1-T7-0007")
        assert so["lan_chua_xac_nhan"] == 3 and "lich" not in so

    def test_cung_tieu_de_cong_khai_khong_tai(self, moi):
        k, bao = KenhGia(), Bao()
        k.video.append({"id": "PUBxxxxxxxx", "tieu_de": TD, "loai": "cong_khai"})
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert k.lan_dat_tep_video == 0 and len(k.video) == 1
        assert bao.ds == [("TL1-T7-0007", "ĐÃ ĐĂNG (tay)", {"video_id": "PUBxxxxxxxx"})]

    def test_cung_tieu_de_rieng_tu_bao_chu_kenh(self, moi):
        k, bao = KenhGia(), Bao()
        k.video.append({"id": "PRIxxxxxxxx", "tieu_de": TD, "loai": "rieng_tu"})
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_HONG
        assert k.lan_dat_tep_video == 0 and bao.ds == []

    def test_gio_da_qua_cong_15(self, moi):
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        assert m.chay([_dong(ngay="29/09/2026", gio="07:00")]) == mdd.MA_XONG
        assert k.video[0]["lich"] == datetime(2026, 9, 29, 9, 20)
        assert bao.ds[-1][2]["lich"] == "29/09/2026 09:20"
        assert any("đã qua" in c for c in m.bao_cao["canh_bao"])

    def test_lech_gio_khong_bao_da_dang(self, moi):
        k, bao = KenhGia(), Bao()
        k.lech_phut = 30
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_HONG
        assert "ĐÃ ĐĂNG" not in bao.trang_thai()
        assert bao.ds[-1][1] == "LỆCH LỊCH 30/09/2026 20:30"
        assert m.so.lay("TL1-T7/TL1-T7-0007")["trang_thai"] == "lech-lich"

    def test_uc_lech_dung_kenh_ma_4(self, moi):
        k, bao = KenhGia(), Bao()
        (moi / "uc.json").write_text(json.dumps({"TL1-T7": "UC" + "z" * 22}), encoding="utf-8")
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_CHAN
        assert k.video == []

    def test_loi_du_lieu_khong_tai(self, moi):
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        assert m.chay([_dong(ngay="", gio="")]) == mdd.MA_HONG
        assert k.video == [] and bao.ds == []

    def test_nhap_cung_tieu_de_de_ke_tai_moi(self, moi):
        """Không có id trong sổ, kênh có nháp cùng tiêu đề → để kệ nháp (chỉ báo), tải mới."""
        k, bao = KenhGia(), Bao()
        k.video.append({"id": "DRAFTxxxxxx", "tieu_de": TD, "loai": "nhap"})
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert k.lan_dat_tep_video == 1 and k.video[0]["loai"] == "nhap"
        assert k.video[1]["loai"] == "da_len_lich"
        assert {"ma": "TL1-T7-0007", "video_id": "DRAFTxxxxxx"} in m.bao_cao["nhap_thua"]

    def test_so_co_id_ma_nhap_khong_doc_duoc_id_van_tai_moi(self, moi):
        """30/09: nháp không đọc được id cũng để kệ — trước đây dừng hẳn (lặp
        hỏng mãi); giờ báo rồi tải mới, id cũ vào id_cu."""
        k, bao = KenhGia(), Bao()
        k.video.append({"id": "vcfe05f792c", "tieu_de": "8 video", "loai": "nhap", "an_id": True})
        m = _may(moi, k, bao)
        m.so.cap_nhat("TL1-T7/TL1-T7-0007", video_id="vcfe05f792c", trang_thai="nhap",
                      lan_tai_moi=1, ngay_tai=BAY_GIO.date().isoformat())
        assert m.chay([_dong()]) == mdd.MA_XONG
        assert k.lan_dat_tep_video == 1 and len(k.video) == 2
        so = m.so.lay("TL1-T7/TL1-T7-0007")
        assert so["id_cu"] == ["vcfe05f792c"] and so["lan_tai_moi"] == 2
        assert any("không đọc được id" in c for c in m.bao_cao["canh_bao"])

    def test_chay_lai_sau_xong_la_da_co(self, moi):
        k, bao = KenhGia(), Bao()
        m = _may(moi, k, bao)
        assert m.chay([_dong()]) == mdd.MA_XONG
        bao2 = Bao()
        assert _may(moi, k, bao2).chay([_dong()]) == mdd.MA_XONG
        assert k.lan_dat_tep_video == 1
        assert bao2.ds[-1][1] == "ĐÃ ĐĂNG"


class TestTaiXongHamThuan:
    def test_phan_loai_tien_do_chu_that(self):
        f = mdd.phan_loai_tien_do
        assert f("Đã tải được 83% ... Còn 24 giây") == ("dang", 83)
        assert f("Đã hoàn tất quá trình tải lên ... Quá trình xử lý sẽ sớm bắt đầu")[0] == "xong"
        assert f("Đang xử lý đến độ phân giải tối đa là HD ... Còn 3 phút")[0] == "xong"
        assert f("Đang kiểm tra 14% ... Còn 9 phút")[0] == "xong"
        assert f("Đã kiểm tra xong. Không phát hiện vấn đề nào.")[0] == "xong"
        assert f("Uploading 100%")[0] == "xong"
        assert f("Tải lên không thành công")[0] == "loi"
        assert f("") == ("", None)

    def test_loc_dong_tien_do_bo_chu_la(self):
        chu = "Thành phần\nVideo: Video đã tải lên gần đây nhất\nĐã tải được 40% ... Còn 2 phút"
        assert mdd.loc_dong_tien_do(chu) == "Đã tải được 40% ... Còn 2 phút"
        assert mdd.loc_dong_tien_do("Video: Video đã tải lên gần đây nhất") == ""

    def test_han_cho_tai_theo_dung_luong(self, tmp_path):
        p = tmp_path / "a.mp4"
        p.write_bytes(b"x" * (400 * 1024 * 1024 // 1024))   # 400 KB
        assert mdd.han_cho_tai(str(p)) == 600.0
        assert mdd.han_cho_tai(str(tmp_path / "khong-co.mp4")) == 600.0

    def test_danh_gia_hau_kiem(self):
        f = mdd.danh_gia_hau_kiem
        assert f("VIDEO_STATUS_PROCESSED", 600, 600.4)["ket"] == "ok"
        assert f("VIDEO_STATUS_PROCESSED", 300, 600.0)["ket"] == "hong"
        assert f("VIDEO_STATUS_UPLOADED", None, 600.0)["ket"] == "ok"
        assert f("VIDEO_STATUS_FAILED", None, 600.0)["ket"] == "hong"
        assert f("", None, 600.0, "Tải lên bị gián đoạn")["ket"] == "hong"
        assert f("", None, 600.0, "Đã lên lịch")["ket"] == "chua-ro"

    def test_danh_sach_thieu_mhkt(self):
        so = {"K/1": {"video_id": "a", "trang_thai": "xac-nhan", "mhkt": "bo"},
              "K/2": {"video_id": "b", "trang_thai": "xac-nhan", "mhkt": "ok:nhap"},
              "K/3": {"video_id": "c", "trang_thai": "nhap", "mhkt": "bo"}}
        assert list(mdd.danh_sach_thieu_mhkt(so)) == ["K/1"]

    def test_view_48h_kem_luc_tu_ten_tep(self, tmp_path):
        g = _chi_so_gia(tmp_path, top48={"AAAAAAAAAAA": 5})
        v, luc = mdd.doc_view_48h_kem_luc(g)
        assert v == {"AAAAAAAAAAA": 5}
        assert time.strftime("%Y%m%d-%H%M%S", time.localtime(luc)) == "20260929-073542"


def test_kiem_dom_tren_studio_gia(tmp_path):
    """--kiem-dom mức 1 + 2 trên StudioGia: không chọn tệp, không gõ, không lên lịch."""
    k = KenhGia()
    k.video.append({"id": "PUBxxxxxxxx", "tieu_de": "cũ", "loai": "cong_khai"})
    k.video.append({"id": "DRAFTxxxxxx", "tieu_de": "8 video", "loai": "nhap"})
    tr = StudioGia(k)
    kq = mdd.kiem_dom(None, "TL1-T7", cdp_studio.doc_bo_chon(), sau=True, tao_trang=lambda: tr,
                      duong_uc=str(tmp_path / "uc.json"), ngu=lambda s: None, nhat_ky=lambda s: None)
    assert kq["uc"] == UC
    assert k.lan_dat_tep_video == 0
    assert k.video[1]["loai"] == "nhap"                      # không lên lịch
    assert kq["nhap_8_video"] == ["DRAFTxxxxxx"]
    for khoa in ("hop_upload", "nut_chon_tep", "hang_video", "tieu_de", "nut_tiep", "phu_de_them",
                 "len_lich_mo", "o_ngay_mo", "o_gio", "nut_xong", "o_ngay"):
        assert kq["chi_tiet"][khoa]["khop"], khoa
    assert kq["nut_xong_chu"] == "Lên lịch"
    assert tr.dong_


def test_kiem_dom_video_khong_the_khong_bi_bao_hong(tmp_path):
    """Vá 30/09/2026 (TL3-T7): video mới nhất được chọn để tự kiểm KHÔNG có
    thẻ nào — `the_da_co` (chip thẻ đã có) hợp lý trống, KHÔNG phải selector
    hỏng. Phải bị loại khỏi `hong`, chỉ ghi chú lại, không kéo `ok` xuống
    False vì mỗi thứ khác đều khớp."""
    k = KenhGia()
    k.video.append({"id": "PUBxxxxxxxx", "tieu_de": "cũ", "loai": "cong_khai"})  # không có "the"
    tr = StudioGia(k)
    kq = mdd.kiem_dom(None, "TL1-T7", cdp_studio.doc_bo_chon(), tao_trang=lambda: tr,
                      duong_uc=str(tmp_path / "uc.json"), ngu=lambda s: None, nhat_ky=lambda s: None)
    assert "the_da_co" not in kq["hong"]
    assert kq["chi_tiet"]["the_da_co"]["khop"] is None
    assert any("the_da_co" in c and "không có thẻ" in c for c in kq["ghi_chu"])


def test_kiem_dom_video_co_the_van_kiem_binh_thuong(tmp_path):
    """Video có thẻ thì `the_da_co` vẫn phải khớp bình thường (không bị bỏ
    qua oan khi selector thật sự hỏng)."""
    k = KenhGia()
    k.video.append({"id": "PUBxxxxxxxx", "tieu_de": "cũ", "loai": "cong_khai",
                    "the": ["a", "b"]})
    tr = StudioGia(k)
    kq = mdd.kiem_dom(None, "TL1-T7", cdp_studio.doc_bo_chon(), tao_trang=lambda: tr,
                      duong_uc=str(tmp_path / "uc.json"), ngu=lambda s: None, nhat_ky=lambda s: None)
    assert "the_da_co" not in kq["hong"]
    assert kq["chi_tiet"]["the_da_co"]["khop"] is True
