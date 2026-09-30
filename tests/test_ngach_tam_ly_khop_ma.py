"""Nhóm `tam-ly-nhat`: MỌI trường `doc_ngach` phải bằng đúng hằng số mặc định trong mã.

30/09/2026 — Đợt 4 áp lên bản sống: mã (`cong_thuc_v7`, `phan_tuyen`, `trang_chu`, `chot_doi_thu`,
`tram`, `tuyen_con`, `cong_thuc_vph`, `phan_cum_ai`, `cong_thuc_v7_ai`, `auto_khau`…) giờ ĐỌC
`CHANNEL/_NHOM/tam-ly-nhat/ngach.yaml` thay cho hằng cứng. TL1–TL4 đều khai `nhom: tam-ly-nhat`,
nên tệp này lệch một chữ khỏi hằng số là điểm số của cả 4 kênh đổi theo. Bài này đọc ĐÚNG tệp
thật của kho (chép sang `tmp_path`, không ghi gì vào kho) và so từng trường với hằng trong mã.

Sửa hằng trong mã mà quên tệp (hay ngược lại) → bài này đỏ. Thêm trường mới vào `HoSoNgach` mà
chưa khai nó so với hằng nào → `test_moi_truong_deu_duoc_so` đỏ.
"""

from __future__ import annotations

import dataclasses
import os
import shutil

import pytest

from core import chot_doi_thu as cd
from core import cong_thuc_v7 as v7
from core import phan_tuyen as pt
from core import trang_chu as tc
from core import trung_tam as tt
from core.ho_so_ngach import HoSoNgach, doc_ngach

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_THAT = os.path.join(GOC_KHO, "CHANNEL", "_NHOM", "tam-ly-nhat", "ngach.yaml")

#: trường → hằng số trong mã (so bằng `==` sau khi đổi về list).
_C = v7.CAU_HINH_MAC_DINH
HANG_SO = {
    "tu_manh": list(tc.TU_MANH),
    "tu_yeu": list(tc.TU_YEU),
    "tu_loai_tru": list(pt.TU_LOAI_TRU),
    "ten_kenh_loai_tru": list(tc.TEN_KENH_LOAI_TRU),
    "handle_loai_tru": list(tc.HANDLE_LOAI_TRU),
    "tu_kenh_hien_nhien": list(tc.TU_KENH_HIEN_NHIEN),
    "handle_hien_nhien": list(tc.HANDLE_HIEN_NHIEN),
    "tu_tieu_de_hien_nhien": list(tc.TU_TIEU_DE_HIEN_NHIEN),
    "dau_moc_tuoi_kenh": list(tc.DAU_MOC_TUOI_KENH),
    "tu_tuoi": list(pt.DAU_MOC_TUOI),
    "tu_tuoi_them": list(_C["tu_tuoi"]),
    "tu_chan_dung": list(_C["tu_chan_dung"]),
    "tu_cach_lam": list(_C["tu_cach_lam"]),
    "tu_ghep_khong_phai_nguoi": list(_C["tu_ghep_khong_phai_nguoi"]),
    "cum": _C["cum"],
    "ngach_tu": list(_C["ngach"]["tu"]),
    "ngach_tu_lac": list(_C["ngach"]["tu_lac"]),
    "ten_kenh_dung_ngach": list(cd.TEN_KENH_TAM_LY),
    "tu_khop_nguon": cd.TU_KHOP_LECH_NHIP.pattern.split("|"),
    "tu_go_toi": cd.TU_GO_TOI.pattern.split("|"),
    # Năm tệp của mã, ĐÚNG thứ tự, rồi tới tệp THÊM chỉ khai trong yaml (`TEP_THEM`).
    "tep_khan_gia": [{"ma": m, "ten": ten, "ten_ngan": ngan} for m, ten, ngan in tt.TEP_KHAN_GIA_DAY_DU]
    + [dict(d) for d in (
        # 30/09/2026 — kênh 5: tệp 65+ (workspace/chuan-bi-kenh-5/de-xuat-ngach.yaml).
        {"ma": "7", "ten": "Người 65+ đang sống tuổi già", "ten_ngan": "Tuổi già",
         "ma_tuyen": "nguoi-cao-tuoi-dang-song-tuoi-gia"},
    )],
    "chu_de_con_mac_dinh": True,
}

#: Trường không có hằng tương ứng một-một — được so gián tiếp qua ĐẦU RA của hàm dùng nó (các bài
#: `test_*_giong_het` bên dưới), hoặc chỉ là mô tả cho người/AI đọc từ trước Đợt 4.
SO_QUA_DAU_RA = {
    "mau_tieu_de", "mo_ta_kenh_cho_ai", "dang_thang_cho_ai", "luat_kenh_nguon",
    "mo_ta_phan_cum", "nhan_the_loai_mau", "vi_du_phan_cum", "thi_truong",
}
MO_TA = {"nguon", "nhom", "mo_ta_ngach", "ngon_ngu_nguon", "dang_thang", "luat_chon"}


@pytest.fixture()
def goc(tmp_path):
    thu_muc = tmp_path / "CHANNEL" / "_NHOM" / "tam-ly-nhat"
    thu_muc.mkdir(parents=True)
    shutil.copyfile(YAML_THAT, str(thu_muc / "ngach.yaml"))
    kenh = tmp_path / "CHANNEL" / "KENH-THU"
    kenh.mkdir(parents=True)
    (kenh / "kenh.yaml").write_text('nhom: "tam-ly-nhat"\n', encoding="utf-8")
    return str(tmp_path)


@pytest.fixture()
def hs(goc):
    ho_so = doc_ngach(goc, "KENH-THU")
    assert ho_so.co(), "ngach.yaml thật không đọc được"
    return ho_so


def test_moi_truong_deu_duoc_so():
    ten = {f.name for f in dataclasses.fields(HoSoNgach)}
    thieu = ten - set(HANG_SO) - SO_QUA_DAU_RA - MO_TA
    assert not thieu, "trường mới chưa có bài so với mã: {0}".format(sorted(thieu))


@pytest.mark.parametrize("truong", sorted(HANG_SO))
def test_truong_bang_hang_so(hs, truong):
    assert getattr(hs, truong) == HANG_SO[truong], truong


def test_thu_tu_cum_giong_ma(hs):
    # dict so bằng == không tính thứ tự; thứ tự cụm đi vào bảng báo cáo và vòng lặp chấm.
    assert list(hs.cum) == list(_C["cum"])


def test_cau_hinh_v7_mac_dinh_giong_het(goc):
    assert v7._cau_hinh_mac_dinh_cho_kenh(goc, "KENH-THU") == _C


def test_de_bai_kenh_nguon_giong_het(goc, hs):
    from core import cong_thuc_v7_ai as ai

    vm = [v7.VideoMinh(ma="a", tieu_de="お金持ちほど買わないもの", thang=True)]
    cu = ai.de_bai_kenh(_C, vm)
    moi = ai.de_bai_kenh(_C, vm, **ai.tham_so_de_bai_kenh(hs))
    assert moi == cu


def test_de_bai_nan_khuon_giong_het(hs):
    from core import auto_khau

    mau = ["お金持ちほど絶対に買わないもの"]
    assert auto_khau.de_bai_nan_khuon("x", mau, "", mau_tieu_de=hs.mau_tieu_de) == \
        auto_khau.de_bai_nan_khuon("x", mau, "")


def test_de_bai_phan_cum_giong_het(hs):
    from core import phan_cum_ai

    assert phan_cum_ai.de_bai(_C, ngach=hs) == phan_cum_ai.de_bai(_C)


def test_bac_lam_tron_view_giong_het(hs):
    from core import cong_thuc_vph as vph

    bac = vph.bac_lam_tron_tu_ngach(hs)
    for view in (0, 9_999, 10_000, 135_000, 999_999, 1_000_000, 25_000_000):
        assert vph._bac_hien_thi(view, bac) == vph._bac_hien_thi_jp(view), view


def test_regex_chot_doi_thu_giong_het(hs):
    assert cd.regex_tu(hs.tu_khop_nguon).pattern == cd.TU_KHOP_LECH_NHIP.pattern
    assert cd.regex_tu(hs.tu_go_toi).pattern == cd.TU_GO_TOI.pattern


def test_ma_tep_doc_tep_them_cua_ngach(goc):
    """30/09/2026: `ma_tep` nhận mã khai trong `tep_khan_gia` (không cứng 1·2·3·4·8); bảng cứng giữ y."""
    from core import tuyen_noi_dung as tn

    assert tn.ma_tep("7", goc) == "nguoi-cao-tuoi-dang-song-tuoi-gia"
    assert tn.ma_tep("nguoi-cao-tuoi-dang-song-tuoi-gia", goc) == "nguoi-cao-tuoi-dang-song-tuoi-gia"
    assert tn.ma_tep("1", goc) == pt.MA_LECH_NHIP and tn.ma_tep("4", goc) == pt.MA_TRUNG_NIEN
    assert tn.ma_tep("9", goc) == ""
    # tên tệp trên giao diện: slug của tệp cũ vẫn ra tên ngắn khi truyền goc+nhom
    assert tt.mo_ta_tep(pt.MA_TRUNG_NIEN, goc=goc, nhom="tam-ly-nhat")[0] == "Trung niên"
    assert tt.mo_ta_tep("nguoi-cao-tuoi-dang-song-tuoi-gia", goc=goc, nhom="tam-ly-nhat")[0] == "Tuổi già"
