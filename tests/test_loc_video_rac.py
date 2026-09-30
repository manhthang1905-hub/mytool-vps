# -*- coding: utf-8 -*-
"""Lọc VIDEO RÁC khỏi số liệu kênh — khoá `ngay_bat_dau` trong `kenh.yaml`.

═══ CHUYỆN NÀY BẮT ĐẦU TỪ MỘT CON QUAY ĐỒ CHƠI ═══

Bốn kênh đang chạy đều là kênh YouTube **có sẵn**, đổi sang làm tâm lý Nhật. Mắt
cào Studio cào TẤT CẢ video trên kênh, nên `CHANNEL/TL4-T7/chi-so/` (đo 22/09/2026)
có hai video của đời trước nằm chung `bang-tom-tat.csv` với video tâm lý:

    v47c6f05e48  "Mô hình đồ chơi cũ số 1"   đăng 2018-12-09
    v8754af58fc  "Mở hộp đồ chơi cũ số 5"      đăng 2018-12-27
                 → 35.701 lượt hiển thị, CTR 7,97%

35.701 hiển thị vượt xa mọi ngưỡng THẮNG, nên video đồ chơi 2018 tự nhận là "video
thắng" của một kênh tâm lý — kéo theo `thanh_tich_cum`, mẫu nắn tiêu đề
(`auto_khau.tieu_de_thang_cua_kenh`) và cổng chuyển V7 (`da_co_video_thang`).

Ba kênh mới còn nặng hơn: `CHANNEL/TL1-T7/chi-so/` có 22 video đăng 2026-06/07 —
video tâm lý của một KHUÔN KHÁC. Chủ dự án: *"số liệu 3 kênh mới không dùng được
đâu — chỉ dùng được số liệu TL4-T7 thôi"*.

Bộ test này canh đúng ba điều:

1. **Mốc rỗng thì KHÔNG đổi gì** — bản gửi khách và mọi khuôn cũ giữ nguyên hành vi.
2. **Có mốc thì video cũ ra khỏi bảng VÀ ra khỏi bộ chấm**, nhưng gói raw vẫn nằm
   nguyên trên đĩa (kho bằng chứng, không xoá).
3. **Video chưa biết ngày đăng bị coi là ngoài phạm vi, và có dòng nhật ký** — thà
   thiếu một dòng bảng còn hơn cho rác vào vòng học, nhưng không được mất dấu.

Không đụng `CHANNEL/` thật: mọi thứ dựng trong `tmp_path`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chi_so_ytb as cs  # noqa: E402
from core import cong_thuc_v7 as v7  # noqa: E402
from core import kenh as mod_kenh  # noqa: E402
from core import nhom_kenh  # noqa: E402
from core.chi_so_ytb import loc_video as lv  # noqa: E402

#: Hai video đồ chơi và một video tâm lý — copy đúng hình dạng đo được trên TL4-T7.
DO_CHOI = ("v8754af58fc", "2018-12-27T05:18:06.000Z",
           "Mở hộp đồ chơi cũ số 5 chính hãng", 35701, 7.97)
TAM_LY = ("v2b628f09d6", "2026-09-14T11:00:00.000Z",
          "【心理学】なぜかお金持ちに見えない人の「恐ろしい特徴」", 181062, 5.52)
#: Mốc thật của TL4-T7: video tâm lý đầu tiên (`vba4ef7584a`) đăng ngày này.
MOC_TL4 = "2026-08-22"


# ── Dựng cảnh ────────────────────────────────────────────────────────────────


def _ghi_json(duong, du_lieu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(json.dumps(du_lieu, ensure_ascii=False))


def _ban_chup(thu_muc_kenh, ma, ngay_dang, tieu_de, imp, ctr, *, moc_gio=48,
              co_ngay=True):
    """Một bản chụp tối thiểu đúng hình mắt cào ghi ra: `<mã>/<mốc>h/…`."""
    snap = os.path.join(thu_muc_kenh, "chi-so", ma, "{0}h".format(moc_gio))
    tq = {"video_id": ma, "impressions": imp, "ctr": ctr, "views": 4000,
          "unique_viewers": 3000, "views_chot": 3900, "avd_giay": 300,
          "avd_pct": 35.5, "watch_hours": 300.0, "subs": 10,
          "gio_sau_dang": moc_gio}
    tt = {"kenh": os.path.basename(thu_muc_kenh), "id": ma,
          "label": "{0}h".format(moc_gio), "tieu_de": tieu_de,
          "thoi_luong": 900, "gio": moc_gio}
    if co_ngay:
        tq["ngay_dang"] = ngay_dang
        tt["ngay_dang"] = ngay_dang
    _ghi_json(os.path.join(snap, "tong-quan.json"), tq)
    _ghi_json(os.path.join(snap, "_thong-tin.json"), tt)
    return snap


def _dung_kenh(goc_channel, ma="TL4-T7", moc="", nhom="", tep="", them_yaml=""):
    """Thư mục kênh có `kenh.yaml` — `moc` rỗng nghĩa là kênh không khai khoá."""
    thu_muc = os.path.join(goc_channel, ma)
    os.makedirs(thu_muc, exist_ok=True)
    dong = ['ma: "{0}"'.format(ma), 'ten: "kênh thử"']
    if moc:
        dong.append('ngay_bat_dau: "{0}"'.format(moc))
    if nhom:
        dong.append('nhom: "{0}"'.format(nhom))
    if tep:
        dong.append('tep: "{0}"'.format(tep))
    if them_yaml:
        dong.append(them_yaml)
    with io.open(os.path.join(thu_muc, mod_kenh.TEP_KENH), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    return thu_muc


@pytest.fixture()
def kenh_hai_doi(tmp_path):
    """Gốc TOOL giả với `CHANNEL/TL4-T7/chi-so/` mang cả video 2018 và 2026."""
    goc_tool = str(tmp_path)
    goc_channel = os.path.join(goc_tool, mod_kenh.THU_MUC_KENH)
    thu_muc = _dung_kenh(goc_channel)
    for ma, ngay, td, imp, ctr in (DO_CHOI, TAM_LY):
        _ban_chup(thu_muc, ma, ngay, td, imp, ctr)
    return goc_tool, goc_channel, thu_muc


def _dat_moc(thu_muc_kenh, moc):
    """Thêm khoá `ngay_bat_dau` vào `kenh.yaml` đã có — như giao diện vẫn ghi."""
    p = os.path.join(thu_muc_kenh, mod_kenh.TEP_KENH)
    chu = io.open(p, encoding="utf-8").read()
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(chu + 'ngay_bat_dau: "{0}"\n'.format(moc))


# ── A. Khoá trong kenh.yaml ──────────────────────────────────────────────────


class TestKhoaNgayBatDau:
    def test_doc_kenh_doc_dung_khoa(self, tmp_path):
        goc_channel = os.path.join(str(tmp_path), mod_kenh.THU_MUC_KENH)
        _dung_kenh(goc_channel, moc=MOC_TL4)
        assert mod_kenh.doc_kenh(str(tmp_path), "TL4-T7").ngay_bat_dau == MOC_TL4

    def test_thieu_khoa_thi_rong_khong_phai_loi(self, tmp_path):
        goc_channel = os.path.join(str(tmp_path), mod_kenh.THU_MUC_KENH)
        _dung_kenh(goc_channel)
        assert mod_kenh.doc_kenh(str(tmp_path), "TL4-T7").ngay_bat_dau == ""

    def test_ngay_go_sai_thi_rong_chu_khong_loai_sach_kenh(self, tmp_path):
        """"2026-13-45" đúng khuôn chữ nhưng không phải ngày. Phải thành RỖNG (=
        không lọc), chứ không thành một mốc vô nghĩa loại sạch mọi video."""
        goc_channel = os.path.join(str(tmp_path), mod_kenh.THU_MUC_KENH)
        _dung_kenh(goc_channel, moc="2026-13-45")
        assert mod_kenh.doc_kenh(str(tmp_path), "TL4-T7").ngay_bat_dau == ""

    def test_khong_boc_nhay_trong_yaml_van_doc_duoc(self, tmp_path):
        """PyYAML đổi `ngay_bat_dau: 2026-08-22` không nháy thành `datetime.date`.
        Quên ca này là một lần sửa tay `kenh.yaml` làm mốc hỏng lặng lẽ."""
        goc_channel = os.path.join(str(tmp_path), mod_kenh.THU_MUC_KENH)
        thu_muc = _dung_kenh(goc_channel)
        with io.open(os.path.join(thu_muc, mod_kenh.TEP_KENH), "a",
                     encoding="utf-8", newline="\n") as f:
            f.write("ngay_bat_dau: 2026-08-22\n")
        assert mod_kenh.doc_kenh(str(tmp_path), "TL4-T7").ngay_bat_dau == MOC_TL4

    def test_bon_kenh_that_da_khai_moc(self):
        """Bốn kênh trên máy này phải có mốc — nếu ai xoá đi thì số liệu rác quay
        lại ngay mà không ai thấy. TL4-T7 lấy ngày video tâm lý đầu tiên; ba kênh
        em lấy ngày được tạo trong tool."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.isdir(os.path.join(goc, mod_kenh.THU_MUC_KENH, "TL4-T7")):
            pytest.skip("máy này không có bốn kênh thật")
        assert mod_kenh.doc_kenh(goc, "TL4-T7").ngay_bat_dau == "2026-08-22"
        for ma in ("TL1-T7", "TL2-T7", "TL3-T7"):
            assert mod_kenh.doc_kenh(goc, ma).ngay_bat_dau == "2026-09-21", ma


# ── B. Hàm dùng chung ───────────────────────────────────────────────────────


class TestChuanNgay:
    @pytest.mark.parametrize("vao,ra", [
        ("2018-12-27T05:18:06.000Z", "2018-12-27"),   # _thong-tin.json
        ("2026-09-16", "2026-09-16"),                 # cột CSV
        (" 2026-09-16 ", "2026-09-16"),
        (_dt.date(2026, 8, 22), "2026-08-22"),        # PyYAML
        (_dt.datetime(2026, 8, 22, 3, 4), "2026-08-22"),
        ("", ""), (None, ""), ("hôm qua", ""), ("2026-13-45", ""),
        ("26-08-22", ""),
    ])
    def test_moi_dang_ngay_that_tren_dia(self, vao, ra):
        assert lv.chuan_ngay(vao) == ra


class TestTrongPhamVi:
    def test_moc_rong_thi_nhan_het(self):
        assert lv.trong_pham_vi("", "2018-12-27T00:00:00Z") is True
        assert lv.trong_pham_vi("", "") is True

    def test_truoc_moc_thi_loai_dung_moc_thi_nhan(self):
        assert lv.trong_pham_vi(MOC_TL4, "2018-12-27") is False
        assert lv.trong_pham_vi(MOC_TL4, "2026-08-21") is False
        assert lv.trong_pham_vi(MOC_TL4, MOC_TL4) is True
        assert lv.trong_pham_vi(MOC_TL4, "2026-09-14T11:00:00Z") is True

    def test_thieu_ngay_thi_ngoai_pham_vi_va_ghi_mot_dong(self):
        ghi = []
        assert lv.trong_pham_vi(MOC_TL4, "", ghi=ghi.append, nhan="abc") is False
        assert len(ghi) == 1 and "abc" in ghi[0]

    def test_moc_cua_thu_muc_lui_ve_kenh_goc_cho_ban_thu(self, tmp_path):
        """`TL4-T7-v2` không có `chi-so/` riêng (đăng cùng kênh YouTube với bản
        gốc) nên phải dùng mốc của `TL4-T7` — cùng quy ước `da_lam`/`auto_khau`."""
        goc_channel = os.path.join(str(tmp_path), mod_kenh.THU_MUC_KENH)
        _dung_kenh(goc_channel, ma="TL4-T7", moc=MOC_TL4)
        _dung_kenh(goc_channel, ma="TL4-T7-v2")
        assert lv.moc_cua_kenh(goc_channel, "TL4-T7-v2") == MOC_TL4
        assert lv.moc_cua_kenh(goc_channel, "khong-co-kenh-nay") == ""

    def test_nhat_ky_khong_lap_lai_mot_dong(self, tmp_path):
        d = str(tmp_path)
        for _ in range(5):
            lv.ghi_nhat_ky(d, "bỏ abc: chưa biết ngày đăng")
        chu = io.open(os.path.join(d, lv.TEN_TEP_NHAT_KY), encoding="utf-8").read()
        assert chu.count("bỏ abc") == 1, "nối mù thì nhật ký thành thứ không ai mở"


# ── C. Cắm vào mọi nơi đọc số liệu ──────────────────────────────────────────


class TestBangTomTat:
    def test_moc_rong_thi_y_nhu_cu(self, kenh_hai_doi):
        _goc_tool, goc_channel, _tm = kenh_hai_doi
        ma_ds = {b.video_id for b in cs.doc_kenh("TL4-T7", goc_channel)}
        assert ma_ds == {DO_CHOI[0], TAM_LY[0]}, \
            "kênh chưa khai mốc thì không được đổi một dòng số nào"

    def test_co_moc_thi_video_2018_ra_khoi_bang(self, kenh_hai_doi):
        _goc_tool, goc_channel, tm = kenh_hai_doi
        _dat_moc(tm, MOC_TL4)
        ma_ds = {b.video_id for b in cs.doc_kenh("TL4-T7", goc_channel)}
        assert ma_ds == {TAM_LY[0]}

        duong = cs.xuat_tom_tat("TL4-T7", goc_channel)
        chu = io.open(duong, encoding="utf-8-sig").read()
        assert "đồ chơi cũ" not in chu and DO_CHOI[0] not in chu
        assert TAM_LY[0] in chu and "2026-09-14" in chu

    def test_goi_raw_van_nam_nguyen_tren_dia(self, kenh_hai_doi):
        """Bảng sạch nhưng KHO BẰNG CHỨNG không bị xoá — sau này đổi mốc là số
        liệu quay lại ngay, không phải cào lại tám phút."""
        _goc_tool, goc_channel, tm = kenh_hai_doi
        _dat_moc(tm, MOC_TL4)
        cs.xuat_tom_tat("TL4-T7", goc_channel)
        assert os.path.isfile(os.path.join(
            tm, "chi-so", DO_CHOI[0], "48h", "tong-quan.json"))

    def test_thieu_ngay_dang_thi_ngoai_pham_vi_va_co_nhat_ky(self, tmp_path):
        goc_channel = os.path.join(str(tmp_path), mod_kenh.THU_MUC_KENH)
        tm = _dung_kenh(goc_channel, moc=MOC_TL4)
        _ban_chup(tm, "khongcongay", "", "video chưa giải mã xong", 999, 3.0,
                  co_ngay=False)
        _ban_chup(tm, TAM_LY[0], TAM_LY[1], TAM_LY[2], TAM_LY[3], TAM_LY[4])

        ma_ds = {b.video_id for b in cs.doc_kenh("TL4-T7", goc_channel)}
        assert ma_ds == {TAM_LY[0]}, "không biết ngày thì phải coi là ngoài phạm vi"
        nk = os.path.join(tm, "chi-so", lv.TEN_TEP_NHAT_KY)
        assert os.path.isfile(nk), "bỏ một video thì không được bỏ im lặng"
        assert "khongcongay" in io.open(nk, encoding="utf-8").read()

    def test_su_that_kenh_khong_lay_video_doi_truoc(self, kenh_hai_doi):
        """`su_that_kenh` là khối số đưa cho bộ chấm kịch bản làm chuẩn so — lấy
        đường giữ chân của video đồ chơi làm chuẩn là dạy kênh học sai."""
        _goc_tool, goc_channel, tm = kenh_hai_doi
        _dat_moc(tm, MOC_TL4)
        st = cs.su_that_kenh("TL4-T7", goc_channel)
        assert "đồ chơi cũ" not in st


class TestCongThucV7:
    def test_moc_rong_thi_video_2018_van_duoc_cham(self, kenh_hai_doi):
        goc_tool, _goc_channel, _tm = kenh_hai_doi
        ds = v7.video_cua_kenh(goc_tool, "TL4-T7")
        assert {v.ma for v in ds} == {DO_CHOI[0], TAM_LY[0]}

    def test_co_moc_thi_video_2018_ra_khoi_video_cua_kenh(self, kenh_hai_doi):
        goc_tool, _goc_channel, tm = kenh_hai_doi
        _dat_moc(tm, MOC_TL4)
        ds = v7.video_cua_kenh(goc_tool, "TL4-T7")
        assert {v.ma for v in ds} == {TAM_LY[0]}
        assert all("đồ chơi cũ" not in (v.tieu_de or "") for v in ds)

    def test_video_2018_khong_con_tu_nhan_la_video_thang(self, kenh_hai_doi):
        goc_tool, _goc_channel, tm = kenh_hai_doi
        truoc = [v for v in v7.video_cua_kenh(goc_tool, "TL4-T7")
                 if v.ma == DO_CHOI[0]]
        assert truoc and truoc[0].thang, \
            "đo lại bằng chứng: 35.701 hiển thị vốn ĐANG được chấm là thắng"
        _dat_moc(tm, MOC_TL4)
        assert not [v for v in v7.video_cua_kenh(goc_tool, "TL4-T7")
                    if v.ma == DO_CHOI[0]]

    def test_cong_chuyen_v7_khong_bat_boi_video_do_choi(self, tmp_path):
        """`da_co_video_thang` là cổng chuyển kênh sang chấm bằng Công thức V7.
        Một mình video đồ chơi 2018 qua mọi ngưỡng `chuyen_v7` → bật cổng sớm."""
        goc_tool = str(tmp_path)
        goc_channel = os.path.join(goc_tool, mod_kenh.THU_MUC_KENH)
        tm = _dung_kenh(goc_channel)
        snap = _ban_chup(tm, DO_CHOI[0], DO_CHOI[1], DO_CHOI[2], 35701, 7.97)
        raw = os.path.join(snap, "raw")
        os.makedirs(raw, exist_ok=True)
        _ghi_json(os.path.join(raw, "20181227-000000_tab-x_join_1.json"),
                  {"href": "https://studio.youtube.com/?ddr_value=YT_RELATED"})

        assert v7.da_co_video_thang(goc_tool, "TL4-T7") is True, \
            "đo lại bằng chứng: video đồ chơi vốn ĐANG bật cổng chuyển V7"
        _dat_moc(tm, MOC_TL4)
        assert v7.da_co_video_thang(goc_tool, "TL4-T7") is False

    def test_thanh_tich_cum_khong_con_cum_do_choi(self, kenh_hai_doi):
        """Cụm chủ đề được cộng điểm theo thành tích THẬT của cụm. Cụm rút từ
        tiêu đề đồ chơi không được có mặt trong bảng thành tích."""
        goc_tool, _goc_channel, tm = kenh_hai_doi
        _dat_moc(tm, MOC_TL4)
        ch = v7.CAU_HINH_MAC_DINH
        ds = v7.video_cua_kenh(goc_tool, "TL4-T7")
        assert "đồ chơi cũ" not in " ".join(v.tieu_de or "" for v in ds)
        # Gọi cho chắc hàm vẫn chạy trên danh sách đã lọc (không ném lỗi).
        assert isinstance(v7.thanh_tich_cum(ds, ch), dict)


class TestBangNhom:
    def _nhom_hai_kenh(self, tmp_path, moc_tl4=""):
        goc_tool = str(tmp_path)
        goc_channel = os.path.join(goc_tool, mod_kenh.THU_MUC_KENH)
        tm4 = _dung_kenh(goc_channel, ma="TL4-T7", moc=moc_tl4,
                         nhom="tam-ly-nhat", tep="4")
        for ma, ngay, td, imp, ctr in (DO_CHOI, TAM_LY):
            _ban_chup(tm4, ma, ngay, td, imp, ctr)
        cs.xuat_tom_tat("TL4-T7", goc_channel)
        return goc_tool

    def test_moc_rong_thi_bang_nhom_y_nhu_cu(self, tmp_path):
        goc_tool = self._nhom_hai_kenh(tmp_path)
        hang = nhom_kenh.bang_nhom(goc_tool, "tam-ly-nhat")
        assert any("đồ chơi cũ" in (d.get("Tiêu đề") or "") for d in hang)

    def test_co_moc_thi_bang_nhom_khong_con_cum_do_choi(self, tmp_path):
        goc_tool = self._nhom_hai_kenh(tmp_path, moc_tl4=MOC_TL4)
        hang = nhom_kenh.bang_nhom(goc_tool, "tam-ly-nhat")
        assert hang, "phải còn video tâm lý"
        assert not any("đồ chơi cũ" in (d.get("Tiêu đề") or "") for d in hang)

        # Bảng nhóm là nơi ba kênh em HỌC của kênh anh (`tu_chay.cong_diem_anh_em`
        # đọc qua `doc_bang_nhom`) — cụm "đồ chơi" lọt vào đây là ba kênh học sai.
        nhom_kenh.ghi_bang_nhom(goc_tool, "tam-ly-nhat")
        bang = lambda td: ["do-choi"] if "đồ chơi cũ" in td else ["tam-ly"]  # noqa: E731
        ra = nhom_kenh.doc_bang_nhom(goc_tool, "tam-ly-nhat", cum_cua=bang)
        assert "do-choi" not in ra

    def test_loc_lai_ca_khi_csv_tren_dia_la_ban_cu(self, tmp_path):
        """Tệp `bang-tom-tat.csv` có thể là bản viết TRƯỚC khi kênh khai mốc.
        Lọc lúc ĐỌC thì mốc ăn ngay, không phải chờ lượt cào sau."""
        goc_tool = self._nhom_hai_kenh(tmp_path)          # CSV viết khi chưa có mốc
        tm4 = os.path.join(goc_tool, mod_kenh.THU_MUC_KENH, "TL4-T7")
        with io.open(os.path.join(tm4, "chi-so", "bang-tom-tat.csv"),
                     encoding="utf-8-sig") as f:
            assert any("đồ chơi cũ" in (d.get("Tiêu đề") or "")
                       for d in csv.DictReader(f)), "cảnh dựng sai: CSV phải còn rác"
        _dat_moc(tm4, MOC_TL4)
        hang = nhom_kenh.bang_nhom(goc_tool, "tam-ly-nhat")
        assert not any("đồ chơi cũ" in (d.get("Tiêu đề") or "") for d in hang)


class TestTrungTam:
    def test_man_hinh_khong_doc_so_cua_video_doi_truoc(self, tmp_path):
        """Màn hình Trung tâm đọc thẳng `bang-tom-tat.csv`. Ô "7 ngày" vốn tự
        loại video cũ bằng cửa sổ ngày, nhưng bảng đưa vào nó phải sạch sẵn."""
        from core import trung_tam  # noqa: PLC0415

        goc_tool = str(tmp_path)
        goc_channel = os.path.join(goc_tool, mod_kenh.THU_MUC_KENH)
        tm = _dung_kenh(goc_channel, moc=MOC_TL4)
        for ma, ngay, td, imp, ctr in (DO_CHOI, TAM_LY):
            _ban_chup(tm, ma, ngay, td, imp, ctr)
        cs.xuat_tom_tat("TL4-T7", goc_channel)
        hang = trung_tam._doc_csv(
            os.path.join(tm, "chi-so", "bang-tom-tat.csv"))
        sach = lv.loc_hang_bang(lv.moc_cua_thu_muc(tm), hang)
        assert not any("đồ chơi cũ" in (d.get("Tiêu đề") or "") for d in sach)
        assert len(sach) == 1


# ── D. Mắt cào không chụp video đời trước ───────────────────────────────────


class TestMatCao:
    def test_background_js_co_cong_loc(self):
        """Mắt cào bỏ hẳn video đăng trước mốc: mỗi video là gần một phút cào mà
        số liệu ấy rồi bị lọc đi hết ở phía tool — cào xong để đấy."""
        nen = io.open(os.path.join(cs.thu_muc_extension(), "background.js"),
                      encoding="utf-8").read()
        assert "async function mocMs" in nen
        assert "function ngoaiPhamVi" in nen
        assert "ngoaiPhamVi(v, moc)" in nen, "cổng phải nằm trong chupVideo"
        assert "lenh.ngay_bat_dau" in nen, "mốc phải xuống được qua /lenh-tien-ich"

    def test_cau_hinh_json_co_khoa_de_trong(self):
        """Khoá phải CÓ trong tệp cấu hình đi kèm, và để TRỐNG: bản gửi khách
        không được tự lọc video của kênh họ."""
        p = os.path.join(cs.thu_muc_extension(), "cau-hinh.json")
        c = json.load(io.open(p, encoding="utf-8"))
        assert c.get("ngay_bat_dau") == ""
        assert c.get("host") == ""

    def test_tram_kem_moc_vao_cau_tra_loi_lenh_tien_ich(self, tmp_path):
        """Trạm trả `ngay_bat_dau` của kênh cho MỌI lượt hỏi (tiện ích hỏi mỗi
        phút), nên đổi ô trên giao diện là mắt cào biết trong một phút."""
        from core.chi_so_ytb import tram  # noqa: PLC0415

        goc_tool = str(tmp_path)
        goc_channel = os.path.join(goc_tool, mod_kenh.THU_MUC_KENH)
        _dung_kenh(goc_channel, moc=MOC_TL4)
        d = os.path.dirname(tram.thu_muc_kenh("TL4-T7", goc_tool))
        assert lv.moc_cua_thu_muc(d) == MOC_TL4
        # Mã kênh lạ → không có `kenh.yaml` → mốc rỗng → cào như cũ.
        d_la = os.path.dirname(tram.thu_muc_kenh("KHONG-CO", goc_tool))
        assert lv.moc_cua_thu_muc(d_la) == ""


# ── E. Giao diện ────────────────────────────────────────────────────────────


class TestGiaoDien:
    def test_the_tu_chay_co_o_ngay_bat_dau_va_tu_luu(self):
        """Chủ dự án muốn thiết lập MỌI thứ ngay trên giao diện. Ô này phải có
        mặt, phải tự lưu như các ô khác, và tooltip phải nói rõ hậu quả."""
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "ui_qt", "trang_quan_ly_kenh.py")
        chu = io.open(p, encoding="utf-8").read()
        assert "_o_ngay_bat_dau" in chu
        assert "Ngày bắt đầu làm nội dung" in chu
        assert "ngay_bat_dau=self._o_ngay_bat_dau" in chu, "sửa là phải lưu ngay"
        assert "không được tính vào số liệu" in chu.replace("KHÔNG", "không")
