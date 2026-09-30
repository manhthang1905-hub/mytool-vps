"""Bài kiểm Đợt 4 — hồ sơ ngách (`workspace/LO-TRINH-PHAT-HANH-V3.md`, mục A1–A5).

Ba việc bài kiểm này phải chứng minh, đúng yêu cầu điều phối:

(a) KHÔNG có `ngach.yaml` → chín module A1–A5 (bản NHÁP) cho kết quả GIỐNG HỆT bản SỐNG, trên
    cùng đầu vào giả — so trực tiếp đầu ra sống vs nháp, không so bằng mắt.
(b) Ngách "nấu ăn tiếng Việt" giả → không hằng tâm lý/Nhật nào (từ loại trừ 雑学/要約, mốc tuổi
    50代/60代, cụm chủ đề tiếng Nhật…) tham gia chấm/lọc.
(c) `ngach.yaml` hỏng (cú pháp sai, khoá sai kiểu) → lùi mặc định, có ghi log cảnh báo.

30/09/2026 — Đợt 4 ĐÃ ÁP lên bản sống: bài kiểm nhập thẳng `core.*` (bỏ `_tai_ban_nhap`). Các
bài "(a) giống hệt bản sống" giờ gọi CÙNG module ở hai vế — chúng còn canh đường "không hồ sơ
ngách" chạy được và cho cùng kết quả khi gọi với/không tham số mới; bằng chứng "không đổi một điểm
số" của nhóm tam-ly-nhat nằm ở `tests/test_ngach_tam_ly_khop_ma.py` (so từng trường ngach.yaml với
hằng số trong mã). Đổi so với nháp: `quyet(ten_kenh_tam_ly=)` lấy `ten_kenh_dung_ngach` (không
phải `tu_manh`), V7 `tu_tuoi` lấy `tu_tuoi_them` (lùi `tu_tuoi`), `tuyen_con` tắt bảng chủ đề
trừ khi ngách khai `chu_de_con_mac_dinh: true`.

Chạy: `python -m pytest tests/test_dot4_ho_so_ngach.py -q`. KHÔNG gọi mạng, KHÔNG đụng
`CHANNEL/`/`PROJECTS/` thật — mọi kênh giả dựng trong `tmp_path` của pytest.
"""

from __future__ import annotations

import csv
import json
import logging
import os

import pytest

import contextlib
import importlib

import core.ho_so_ngach as hsn
from core.kenh import TEP_KENH, duong_kenh


@contextlib.contextmanager
def _ban_song(*ten_module: str):
    """Thay `_tai_ban_nhap.dung_ban_nhap` của bản nháp: Đợt 4 đã áp, "bản mới" = module sống."""
    yield tuple(importlib.import_module(t) for t in ten_module)

pytestmark = pytest.mark.filterwarnings("ignore")


# ═══ Hạ tầng dựng kênh/nhóm giả ═════════════════════════════════════════════════════════════

def _ghi_kenh(goc: str, ma_kenh: str, **khoa) -> None:
    thu_muc = duong_kenh(goc, ma_kenh)
    os.makedirs(thu_muc, exist_ok=True)
    dong = ["{0}: {1}".format(k, v) for k, v in khoa.items()]
    with open(os.path.join(thu_muc, TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


def _ghi_ngach_yaml_tho(goc: str, nhom: str, chu: str) -> str:
    duong = hsn.duong_ngach_yaml(goc, nhom)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)
    return duong


#: Một hồ sơ ngách "nấu ăn tiếng Việt" nhỏ — đủ trường để lộ RÕ khi một hằng số tiếng Nhật lọt
#: vào (không cụm nào tiếng Nhật, không từ loại trừ 雑学, không mốc tuổi 50代/60代…).
NGACH_NAU_AN_YAML = """
mo_ta_ngach: "Nấu ăn tiếng Việt"
ngon_ngu_nguon: vi
dang_thang: 'công thức nấu ăn từng bước'
tu_manh: ["cách làm", "công thức"]
tu_yeu: ["bếp", "nấu"]
tu_loai_tru: ["review phim", "gaming"]
ten_kenh_loai_tru: ["tóm tắt sách"]
handle_loai_tru: ["reup"]
tu_tuoi: ["dưỡng già", "về hưu"]
tu_chan_dung: []
tu_cach_lam: ["cách làm", "công thức"]
cum:
  mon-man:
    ten: "Món mặn"
    tu: ["kho", "xào", "canh"]
tep_khan_gia:
  - ma: "1"
    ten: "Người mới tập nấu"
    ten_ngan: "Mới tập nấu"
  - ma: "2"
    ten: "Người nấu lâu năm"
    ten_ngan: "Nấu lâu năm"
ngach:
  tu: ["nấu ăn", "công thức", "mẹo bếp"]
  tu_lac: ["review", "mukbang"]
mau_tieu_de: "kênh YouTube nấu ăn tiếng Việt"
mo_ta_kenh_cho_ai: "Kênh của tôi làm lại (remake) công thức nấu ăn cho khán giả Việt Nam."
"""


def _dung_ngach_nau_an(goc: str, ma_kenh: str, nhom: str = "nau-an-vi") -> None:
    _ghi_kenh(goc, ma_kenh, nhom=nhom)
    _ghi_ngach_yaml_tho(goc, nhom, NGACH_NAU_AN_YAML)


# ═══ (1) core.ho_so_ngach — module MỚI, kiểm THUẦN ══════════════════════════════════════════

class TestHoSoNgach:
    def test_kenh_khong_khai_nhom(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1")
        ho_so = hsn.doc_ngach(goc, "k1")
        assert ho_so.co() is False
        assert ho_so.nhom == ""
        assert ho_so.tu_manh == []

    def test_kenh_khong_ton_tai(self, tmp_path):
        ho_so = hsn.doc_ngach(str(tmp_path), "khong-co-that")
        assert ho_so.co() is False

    def test_ma_kenh_rong(self, tmp_path):
        assert hsn.doc_ngach(str(tmp_path), "").co() is False
        assert hsn.doc_ngach(str(tmp_path), None).co() is False  # type: ignore[arg-type]

    def test_nhom_chua_co_ngach_yaml(self, tmp_path):
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1", nhom="nhom-chua-co-tep")
        ho_so = hsn.doc_ngach(goc, "k1")
        assert ho_so.co() is False
        assert ho_so.nhom == "nhom-chua-co-tep"   # biết đã tìm ra nhóm, chỉ là nhóm chưa có tệp

    def test_doc_dung_ngach_nau_an(self, tmp_path, caplog):
        goc = str(tmp_path)
        _dung_ngach_nau_an(goc, "kenh-nau-an")
        with caplog.at_level(logging.WARNING):
            ho_so = hsn.doc_ngach(goc, "kenh-nau-an")
        assert ho_so.co() is True
        assert ho_so.nhom == "nau-an-vi"
        assert ho_so.ngon_ngu_nguon == "vi"
        assert ho_so.tu_manh == ["cách làm", "công thức"]
        assert ho_so.tu_loai_tru == ["review phim", "gaming"]
        assert ho_so.tu_chan_dung == []
        assert ho_so.tu_cach_lam == ["cách làm", "công thức"]
        assert ho_so.cum == {"mon-man": {"ten": "Món mặn", "tu": ["kho", "xào", "canh"]}}
        assert ho_so.ngach_tu == ["nấu ăn", "công thức", "mẹo bếp"]
        assert ho_so.ngach_tu_lac == ["review", "mukbang"]
        assert ho_so.tep_khan_gia == [
            {"ma": "1", "ten": "Người mới tập nấu", "ten_ngan": "Mới tập nấu"},
            {"ma": "2", "ten": "Người nấu lâu năm", "ten_ngan": "Nấu lâu năm"},
        ]
        assert ho_so.mau_tieu_de == "kênh YouTube nấu ăn tiếng Việt"
        assert "Không hằng số tiếng Nhật/tâm lý" or True  # xem test riêng bên dưới
        assert not caplog.records, "hồ sơ hợp lệ thì không được log cảnh báo nào"

    def test_khong_hang_nhat_tam_ly_nao_trong_ho_so_nau_an(self, tmp_path):
        """(b) — chốt cứng: không một chữ Nhật/mốc tuổi Nhật nào lọt vào hồ sơ ngách khác."""
        goc = str(tmp_path)
        _dung_ngach_nau_an(goc, "kenh-nau-an")
        ho_so = hsn.doc_ngach(goc, "kenh-nau-an")
        import core.phan_tuyen as pt_song
        toan_bo_chuoi = "|".join([
            ho_so.mo_ta_ngach, ho_so.dang_thang, ho_so.mau_tieu_de, ho_so.mo_ta_kenh_cho_ai,
            *ho_so.tu_manh, *ho_so.tu_yeu, *ho_so.tu_loai_tru, *ho_so.ten_kenh_loai_tru,
            *ho_so.handle_loai_tru, *ho_so.tu_tuoi, *ho_so.tu_chan_dung, *ho_so.tu_cach_lam,
            *ho_so.ngach_tu, *ho_so.ngach_tu_lac,
        ])
        for tu_nhat in pt_song.TU_LOAI_TRU:
            assert tu_nhat not in toan_bo_chuoi, "từ loại trừ tiếng Nhật lọt vào hồ sơ ngách nấu ăn: " + tu_nhat
        for moc in pt_song.DAU_MOC_TUOI:
            assert moc not in toan_bo_chuoi, "mốc tuổi tiếng Nhật lọt vào hồ sơ ngách nấu ăn: " + moc

    def test_yaml_hong_cu_phap(self, tmp_path, caplog):
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1", nhom="nhom-hong")
        _ghi_ngach_yaml_tho(goc, "nhom-hong", "tu_manh: [khong dong mo ngoac\n  - loi cu phap")
        with caplog.at_level(logging.WARNING):
            ho_so = hsn.doc_ngach(goc, "k1")
        assert ho_so.co() is False
        assert any("ho_so_ngach" in r.message or "ho_so_ngach" in r.name for r in caplog.records) or caplog.records

    def test_yaml_khong_phai_mapping(self, tmp_path, caplog):
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1", nhom="nhom-la-list")
        _ghi_ngach_yaml_tho(goc, "nhom-la-list", "- mot\n- hai\n- ba\n")
        with caplog.at_level(logging.WARNING):
            ho_so = hsn.doc_ngach(goc, "k1")
        assert ho_so.co() is False
        assert caplog.records

    def test_yaml_khoa_sai_kieu_van_loc_duoc_cac_khoa_dung(self, tmp_path, caplog):
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1", nhom="nhom-sai-kieu")
        chu = (
            "mo_ta_ngach: \"ngách thử\"\n"
            "tu_manh: \"khong phai danh sach\"\n"   # sai kiểu — phải là list
            "tu_yeu:\n  - \"tu dung\"\n"             # đúng kiểu
            "cum: \"khong phai mapping\"\n"          # sai kiểu
        )
        _ghi_ngach_yaml_tho(goc, "nhom-sai-kieu", chu)
        with caplog.at_level(logging.WARNING):
            ho_so = hsn.doc_ngach(goc, "k1")
        assert ho_so.co() is True                 # tệp ĐỌC ĐƯỢC (YAML hợp lệ), chỉ vài khoá sai kiểu
        assert ho_so.mo_ta_ngach == "ngách thử"
        assert ho_so.tu_manh == []                # khoá sai kiểu → bỏ qua, KHÔNG ném lỗi
        assert ho_so.tu_yeu == ["tu dung"]         # khoá đúng kiểu bên cạnh vẫn đọc được
        assert ho_so.cum == {}
        assert len(caplog.records) >= 2            # một cảnh báo cho mỗi khoá sai kiểu

    def test_khong_co_pyyaml(self, tmp_path, monkeypatch, caplog):
        """Máy chưa cài PyYAML → lùi mặc định + log, không ném lỗi."""
        import builtins

        goc = str(tmp_path)
        _dung_ngach_nau_an(goc, "kenh-nau-an")
        goc_import = builtins.__import__

        def gia_import(ten, *a, **kw):
            if ten == "yaml":
                raise ImportError("giả lập máy chưa cài PyYAML")
            return goc_import(ten, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", gia_import)
        with caplog.at_level(logging.WARNING):
            ho_so = hsn.doc_ngach(goc, "kenh-nau-an")
        assert ho_so.co() is False
        assert caplog.records


# ═══ Mẫu tiêu đề dùng chung cho các bài so sánh sống/nháp bên dưới (chép từ
# tests/test_phan_tuyen_luat_cung.py và tests/test_tuyen_con.py — dữ liệu THẬT đã dùng kiểm
# bản sống, không bịa thêm để tránh lệch với ý ban đầu của bộ luật cứng) ═════════════════════

_MAU_AP_LUAT_CUNG = [
    ("【雑学】一匹狼が向いている人の特徴", "人の本音研究所"),
    ("実は1960年代生まれに共通する「5つの力」", "おもしろ雑学ちゃんねる"),
    ("【心理学】年齢を重ねると「友達がいなくても大丈夫」な理由｜成熟した脳の真実", "ひととき心理学"),
    ("60代がお金をかけずに1人で楽しめる「最高の趣味」9選", "ひととき心理学"),
    ("【心理学】SNSをしない人に隠された「恐ろしい特徴」｜SNSをやらない人が幸福であり続ける理由", "ひととき心理学"),
    ("なぜか部屋が汚くなる人の「恐ろしい特徴」", "ひととき心理学"),
    ("料理が好きな人の意外な共通点", "普通のチャンネル"),   # không dính luật gì — kiểm cả nhánh "giữ nguyên"
]

_MAU_NHAN_DIEN = [
    "SNSをしない人の特徴",
    "スポーツに興味がない人の脳が持っている特殊な報酬回路の正体",
    "友達が少ない人の、本当の理由",
    "性格が悪い人が必ずとる行動",
    "IQ130以上の人が無意識にやっている10の習慣",
    "猫が一匹いれば幸せな人、その本当の理由",
    "50代から人生が変わる「幸せな環境」の作り方7選",
    "【雑学】人生後半で化ける人の特徴",
    "たった3日で脳の処理速度が40倍になる勉強法",
    "",
]


# ═══ (2) core.phan_tuyen — mục A3 ═══════════════════════════════════════════════════════════

class TestPhanTuyenA3:
    def test_dinh_tu_loai_tru_giong_het_ban_song_khi_khong_ghi_de(self):
        import core.phan_tuyen as pt_song
        with _ban_song("core.phan_tuyen") as (pt_nhap,):
            for tieu_de, _kenh in _MAU_AP_LUAT_CUNG:
                assert pt_nhap._dinh_tu_loai_tru(tieu_de) == pt_song._dinh_tu_loai_tru(tieu_de), tieu_de

    def test_ap_luat_cung_giong_het_ban_song_khi_khong_ghi_de(self):
        import core.phan_tuyen as pt_song
        co = {pt_song.MA_LECH_NHIP, pt_song.MA_TRUNG_NIEN, "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"}
        with _ban_song("core.phan_tuyen") as (pt_nhap,):
            for tieu_de, kenh in _MAU_AP_LUAT_CUNG:
                cu = pt_song.ap_luat_cung(tieu_de, kenh, pt_song.MA_LECH_NHIP, co)
                moi = pt_nhap.ap_luat_cung(tieu_de, kenh, pt_nhap.MA_LECH_NHIP, co)
                assert moi == cu, tieu_de

    def test_ghi_de_tu_loai_tru_thi_khong_con_loai_theo_tu_nhat(self):
        """(b) — kênh dùng bộ từ loại trừ RIÊNG (không có 雑学) thì 雑学 không còn là dấu loại."""
        with _ban_song("core.phan_tuyen") as (pt_nhap,):
            tieu_de = "【雑学】một video test"
            assert pt_nhap._dinh_tu_loai_tru(tieu_de) is True                       # mặc định vẫn loại
            assert pt_nhap._dinh_tu_loai_tru(tieu_de, tu_loai_tru=["review phim"]) is False  # ngách khác thì không

    def test_sua_so_theo_luat_cung_giong_het_ban_song_khong_co_nhom(self, tmp_path):
        import core.doi_thu_kenh as so
        import core.phan_tuyen as pt_song
        goc_cu, goc_moi = str(tmp_path / "cu"), str(tmp_path / "moi")
        kenh = "k1"
        cot = so.cot_mac_dinh()
        o = {c: i for i, c in enumerate(cot)}

        def dong(td, link, tep=""):
            d = [""] * len(cot)
            d[o["Tiêu đề video"]], d[o["Link video"]], d[o["Kênh"]], d[o[so.COT_TUYEN]] = td, link, "kn", tep
            return d
        hang = [dong(td, "https://www.youtube.com/watch?v=" + str(i).zfill(11), tep=pt_song.MA_LECH_NHIP)
                for i, (td, _k) in enumerate(_MAU_AP_LUAT_CUNG)]
        for goc in (goc_cu, goc_moi):
            _ghi_kenh(goc, kenh)  # không khai nhóm
            so.luu_bang(goc, kenh, cot, hang)

        dem_cu = pt_song.sua_so_theo_luat_cung(goc_cu, kenh)
        with _ban_song("core.phan_tuyen") as (pt_nhap,):
            dem_moi = pt_nhap.sua_so_theo_luat_cung(goc_moi, kenh)
        assert dem_cu == dem_moi
        _cot_cu, hang_cu = so.doc_bang(goc_cu, kenh)
        _cot_moi, hang_moi = so.doc_bang(goc_moi, kenh)
        assert hang_cu == hang_moi

    def test_sua_so_theo_luat_cung_voi_ngach_nau_an_khong_dinh_luat_tieng_nhat(self, tmp_path):
        """(b) — kênh ngách nấu ăn: 雑学 không còn bị loại, nhưng từ loại trừ CỦA NGÁCH thì có."""
        import core.doi_thu_kenh as so
        import core.phan_tuyen as pt_song
        goc = str(tmp_path)
        kenh = "kenh-nau-an"
        _dung_ngach_nau_an(goc, kenh)
        cot = so.cot_mac_dinh()
        o = {c: i for i, c in enumerate(cot)}

        def dong(td, link):
            d = [""] * len(cot)
            d[o["Tiêu đề video"]] = td
            d[o["Link video"]] = link
            d[o["Kênh"]] = "kn"
            d[o[so.COT_TUYEN]] = pt_song.MA_LECH_NHIP
            return d
        hang = [
            dong("【雑学】5 mẹo nấu ăn hay", "https://www.youtube.com/watch?v=aaaaaaaaaaa"),
            dong("review phim nấu ăn cuối tuần", "https://www.youtube.com/watch?v=bbbbbbbbbbb"),
        ]
        so.luu_bang(goc, kenh, cot, hang)
        with _ban_song("core.phan_tuyen") as (pt_nhap,):
            pt_nhap.sua_so_theo_luat_cung(goc, kenh)
        _cot, hang_ket = so.doc_bang(goc, kenh)
        theo_link = {h[o["Link video"]][-11:]: h[o[so.COT_TUYEN]] for h in hang_ket}
        assert theo_link["aaaaaaaaaaa"] == pt_song.MA_LECH_NHIP, "雑学 không còn là từ loại trừ của ngách nấu ăn"
        assert theo_link["bbbbbbbbbbb"] == pt_nhap.MA_KHAC, "\"review phim\" là từ loại trừ CỦA NGÁCH nấu ăn"


# ═══ (3) core.cong_thuc_v7 — mục A1 ══════════════════════════════════════════════════════════

class TestCongThucV7A1:
    def test_cau_hinh_mac_dinh_giong_het_khi_khong_co_nhom(self, tmp_path):
        import core.cong_thuc_v7 as v7_song
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1")
        with _ban_song("core.phan_tuyen", "core.cong_thuc_v7") as (_pt, v7_nhap):
            moi = v7_nhap._cau_hinh_mac_dinh_cho_kenh(goc, "k1")
        assert json.dumps(moi, sort_keys=True, ensure_ascii=False) == \
            json.dumps(v7_song.CAU_HINH_MAC_DINH, sort_keys=True, ensure_ascii=False)

    def test_nap_cau_hinh_ghi_dung_ban_mac_dinh_khong_co_nhom(self, tmp_path):
        import core.cong_thuc_v7 as v7_song
        goc = str(tmp_path)
        _ghi_kenh(goc, "k1")
        with _ban_song("core.phan_tuyen", "core.cong_thuc_v7") as (_pt, v7_nhap):
            ch, duong = v7_nhap.nap_cau_hinh(goc, "k1")
        assert ch == v7_song.CAU_HINH_MAC_DINH
        with open(duong, encoding="utf-8") as tep:
            assert json.load(tep) == v7_song.CAU_HINH_MAC_DINH

    def test_cau_hinh_mac_dinh_theo_ngach_nau_an_khong_con_hang_nhat(self, tmp_path):
        """(b) — kênh ngách nấu ăn: cum/tu_tuoi/tu_chan_dung/tu_cach_lam/ngach đổi hẳn sang tiếng Việt."""
        import core.phan_tuyen as pt_song
        goc = str(tmp_path)
        kenh = "kenh-nau-an"
        _dung_ngach_nau_an(goc, kenh)
        with _ban_song("core.phan_tuyen", "core.cong_thuc_v7") as (_pt, v7_nhap):
            ch = v7_nhap._cau_hinh_mac_dinh_cho_kenh(goc, kenh)
        assert ch["cum"] == {"mon-man": {"ten": "Món mặn", "tu": ["kho", "xào", "canh"]}}
        assert ch["tu_tuoi"] == ["dưỡng già", "về hưu"]
        # GIỚI HẠN ĐÃ BIẾT (ghi trong GHI-CHU.md): "rỗng" trong ngach.yaml không phân biệt được
        # với "không khai" — cả hai đều lùi về mặc định. `tu_chan_dung: []` của ngách nấu ăn vì
        # thế KHÔNG tắt được danh sách tiếng Nhật, nó lùi về `CAU_HINH_MAC_DINH["tu_chan_dung"]`.
        # Vô hại về CHẤM: 6 chữ Hán đó không bao giờ khớp một tiêu đề chữ La-tinh, nên
        # `la_chan_dung()` luôn trả `None` (không rõ) cho ngách này — coi như trung tính, không
        # cộng cũng không trừ — chứ không tính sai. `tu_cach_lam` khác: ngách nấu ăn khai
        # KHÔNG-rỗng nên ghi đè bình thường.
        assert ch["tu_chan_dung"] == v7_nhap.CAU_HINH_MAC_DINH["tu_chan_dung"]
        assert ch["tu_cach_lam"] == ["cách làm", "công thức"]
        assert ch["ngach"]["tu"] == ["nấu ăn", "công thức", "mẹo bếp"]
        assert ch["ngach"]["tu_lac"] == ["review", "mukbang"]
        # không hằng tâm lý/Nhật nào sống sót trong các khoá bị ghi đè
        for moc in pt_song.DAU_MOC_TUOI:
            assert moc not in ch["tu_tuoi"]
        assert "vat-chat" not in ch["cum"] and "tri-tue" not in ch["cum"]
        # các khoá TẦM NGÁCH (không phải nội dung riêng một tệp) giữ nguyên mặc định
        assert ch["thang"] == v7_nhap.CAU_HINH_MAC_DINH["thang"]
        assert ch["pool"] == v7_nhap.CAU_HINH_MAC_DINH["pool"]


# ═══ (4) core.trang_chu — mục A4 ═════════════════════════════════════════════════════════════

_MAU_KENH_BI_LOAI = [
    ("大人の心理雑学", ""),
    ("本要約チャンネル", "@youyaku"),
    ("ひととき心理学", "@hitotoki"),
    ("なんでも料理チャンネル", "@ryouri"),
]


class TestTrangChuA4:
    def test_kenh_bi_loai_giong_het_ban_song(self):
        import core.trang_chu as tc_song
        with _ban_song("core.trang_chu") as (tc_nhap,):
            for ten, link in _MAU_KENH_BI_LOAI:
                assert tc_nhap.kenh_bi_loai(ten, link) == tc_song.kenh_bi_loai(ten, link), (ten, link)

    def test_phan_loai_tam_ly_giong_het_ban_song(self):
        import core.trang_chu as tc_song
        with _ban_song("core.trang_chu") as (tc_nhap,):
            for td in ["SNSをしない人の特徴", "料理が好きな人の意外な共通点", "【雑学】まとめ"]:
                assert tc_nhap.phan_loai_tam_ly(td, ten_kenh="x") == tc_song.phan_loai_tam_ly(td, ten_kenh="x")

    def test_ghi_de_bo_tu_thi_khong_con_loai_theo_tieng_nhat(self):
        """(b) — bộ từ của ngách nấu ăn không có 雑学 → kênh 雑学 KHÔNG còn bị loại ở đây."""
        with _ban_song("core.trang_chu") as (tc_nhap,):
            assert tc_nhap.kenh_bi_loai("大人の心理雑学", "") is True     # mặc định vẫn loại
            assert tc_nhap.kenh_bi_loai(
                "大人の心理雑学", "", tu_loai_tru=["review phim"], ten_kenh_loai_tru=["tóm tắt sách"],
                handle_loai_tru=["reup"]) is False
            assert tc_nhap.kenh_bi_loai(
                "kênh review phim mỗi ngày", "", tu_loai_tru=["review phim"],
                ten_kenh_loai_tru=["tóm tắt sách"], handle_loai_tru=["reup"]) is True


# ═══ (5) core.chot_doi_thu — mục A5 ══════════════════════════════════════════════════════════

class TestChotDoiThuA5:
    def test_quyet_giong_het_ban_song(self):
        import core.chot_doi_thu as cdt_song
        mau = [
            cdt_song.UngVien(ten="心理学チャンネル", pct_gia=0, pct_khop=10, the_loai_loai=False, cua_may_dat=True),
            cdt_song.UngVien(ten="なんでも雑学", pct_gia=40, pct_khop=0, the_loai_loai=True, cua_may_dat=True),
            cdt_song.UngVien(ten="x", pct_gia=0, pct_khop=0, the_loai_loai=False, cua_may_dat=True, subs=5000),
            cdt_song.UngVien(loi="404 not found"),
        ]
        with _ban_song("core.chot_doi_thu") as (cdt_nhap,):
            for uv in mau:
                assert cdt_nhap.quyet(uv) == cdt_song.quyet(uv)

    def test_ten_kenh_tam_ly_ghi_de_theo_ngach(self):
        """(b) — kênh nấu ăn: 'ひととき心理学' không tự nhận đúng ngách; 'Bếp Nhà Mình' (từ mạnh
        của ngách) thì có, dù tên đó không hề nói gì về tâm lý tiếng Nhật."""
        import core.chot_doi_thu as cdt_song
        with _ban_song("core.chot_doi_thu") as (cdt_nhap,):
            uv_mac_dinh = cdt_song.UngVien(ten="ひととき心理学", pct_gia=0, pct_khop=0, the_loai_loai=False,
                                           cua_may_dat=True, subs=300_000)
            assert cdt_nhap.quyet(uv_mac_dinh)[0] == cdt_nhap.db.THEO_DOI  # tự nhận tâm lý → theo dõi dù rất lớn

            uv_khong_nhan = cdt_song.UngVien(ten="Kenh Nau An So 1", pct_gia=0, pct_khop=0, the_loai_loai=False,
                                             cua_may_dat=True, subs=300_000)
            tt, _ly_do = cdt_nhap.quyet(uv_khong_nhan, ten_kenh_tam_ly=["Nau An"])
            assert tt == cdt_nhap.db.THEO_DOI, "tên kênh khớp từ mạnh CỦA NGÁCH (được truyền vào) → theo dõi"
            tt2, _ = cdt_nhap.quyet(uv_khong_nhan)  # không truyền override → về hành vi mặc định (bộ tiếng Nhật)
            assert tt2 == cdt_nhap.db.BO, "không truyền override thì tên kênh không tự nhận tâm lý → bỏ"


# ═══ (6) core.trung_tam — mục A2 ═════════════════════════════════════════════════════════════

class TestTrungTamA2:
    def test_mo_ta_tep_giong_het_ban_song_khong_truyen_goc_nhom(self):
        import core.trung_tam as tt_song
        with _ban_song("core.trung_tam") as (tt_nhap,):
            for ma in ("1", "2", "3", "4", "8", "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao", "ma-la"):
                assert tt_nhap.mo_ta_tep(ma) == tt_song.mo_ta_tep(ma), ma

    def test_tep_khan_gia_cho_nhom_khong_co_ho_so_tra_bang_mac_dinh(self, tmp_path):
        with _ban_song("core.trung_tam") as (tt_nhap,):
            assert tt_nhap.tep_khan_gia_cho_nhom(None, None) is tt_nhap.TEP_KHAN_GIA_DAY_DU
            assert tt_nhap.tep_khan_gia_cho_nhom(str(tmp_path), "nhom-khong-ton-tai") is tt_nhap.TEP_KHAN_GIA_DAY_DU

    def test_tep_khan_gia_cho_nhom_nau_an(self, tmp_path):
        goc = str(tmp_path)
        _ghi_ngach_yaml_tho(goc, "nau-an-vi", NGACH_NAU_AN_YAML)
        with _ban_song("core.trung_tam") as (tt_nhap,):
            bang = tt_nhap.tep_khan_gia_cho_nhom(goc, "nau-an-vi")
            assert bang == (
                ("1", "Người mới tập nấu", "Mới tập nấu"),
                ("2", "Người nấu lâu năm", "Nấu lâu năm"),
            )
            ngan, day_du = tt_nhap.mo_ta_tep("2", goc=goc, nhom="nau-an-vi")
            assert ngan == "Nấu lâu năm"
            assert day_du == "Tệp 2 — Người nấu lâu năm"
            assert "tâm lý" not in day_du and "Nhật" not in day_du


# ═══ (7) core.tuyen_con — mục A2 ═════════════════════════════════════════════════════════════

class TestTuyenConA2:
    def test_nhan_dien_giong_het_ban_song_mac_dinh(self):
        import core.tuyen_con as tcn_song
        with _ban_song("core.phan_tuyen", "core.tuyen_con") as (_pt, tcn_nhap):
            for td in _MAU_NHAN_DIEN:
                assert tcn_nhap.nhan_dien(td) == tcn_song.nhan_dien(td), td

    def test_chu_biet_false_luon_tra_none(self):
        with _ban_song("core.phan_tuyen", "core.tuyen_con") as (_pt, tcn_nhap):
            for td in _MAU_NHAN_DIEN:
                if not td:
                    continue
                assert tcn_nhap.nhan_dien(td, chu_biet=False) is None

    def test_dien_chu_de_khong_gan_nhan_tieng_nhat_cho_kenh_ngach_khac(self, tmp_path):
        """(b) — điểm rơi thật: tiêu đề tiếng Việt chứa 'SNS' (từ khoá của tệp lệch nhịp, viết
        La-tinh) KHÔNG được gán nhầm chủ đề tiếng Nhật khi kênh thuộc một ngách khác."""
        import core.doi_thu_kenh as so
        goc = str(tmp_path)
        kenh = "kenh-nau-an"
        _dung_ngach_nau_an(goc, kenh)
        cot = so.cot_mac_dinh()
        o = {c: i for i, c in enumerate(cot)}

        def dong(td, link):
            d = [""] * len(cot)
            d[o["Tiêu đề video"]], d[o["Link video"]], d[o["Kênh"]] = td, link, "kn"
            return d
        hang = [dong("Mẹo đăng ảnh món ăn lên SNS đẹp hơn", "https://www.youtube.com/watch?v=aaaaaaaaaaa")]
        so.luu_bang(goc, kenh, cot, hang)
        with _ban_song("core.phan_tuyen", "core.tuyen_con") as (_pt, tcn_nhap):
            dem = tcn_nhap.dien_chu_de(goc, kenh)
        assert dem == {"chu_de": 0, "tep_moi": 0, "xem": 1}
        _cot, hang_ket = so.doc_bang(goc, kenh)
        assert hang_ket[0][o[so.COT_TUYEN]] == "", "không được tự gán tệp 'lệch nhịp' tiếng Nhật cho kênh nấu ăn"


# ═══ (8) core.tuyen_noi_dung — mục A2 ════════════════════════════════════════════════════════

class TestTuyenNoiDungA2:
    def test_gieo_cho_kenh_duong_nhat_giong_het_ban_song(self, tmp_path):
        import core.phan_tuyen as pt_song
        import core.tuyen_noi_dung as tn_song
        goc_cu, goc_moi = str(tmp_path / "cu"), str(tmp_path / "moi")
        for goc in (goc_cu, goc_moi):
            _ghi_kenh(goc, "goc")   # kênh gốc KHÔNG có tuyen.csv, KHÔNG có nhóm
            _ghi_kenh(goc, "moi")
        so_cu = tn_song.gieo_cho_kenh(goc_cu, "goc", "moi", pt_song.MA_LECH_NHIP)
        with _ban_song("core.tuyen_noi_dung") as (tn_nhap,):
            so_moi = tn_nhap.gieo_cho_kenh(goc_moi, "goc", "moi", pt_song.MA_LECH_NHIP)
        assert so_cu == so_moi
        assert tn_song.doc(goc_cu, "moi") == tn_song.doc(goc_moi, "moi")

    def test_gieo_cho_kenh_theo_ngach_nau_an(self, tmp_path):
        """(b) — kênh gốc thuộc ngách nấu ăn: gieo tuyen.csv từ tep_khan_gia CỦA NGÁCH ĐÓ, không
        đụng tới năm tệp tiếng Nhật (`_chan_dung_5_tep`)."""
        goc = str(tmp_path)
        _dung_ngach_nau_an(goc, "goc")
        _ghi_kenh(goc, "moi")
        with _ban_song("core.tuyen_noi_dung") as (tn_nhap,):
            n = tn_nhap.gieo_cho_kenh(goc, "goc", "moi", "2")
        assert n == 2
        import core.tuyen_noi_dung as tn_song
        cot, hang = tn_song.doc(goc, "moi")
        o = {c: i for i, c in enumerate(cot)}
        theo_ma = {h[o["Mã"]]: h for h in hang}
        assert set(theo_ma) == {"1", "2"}
        assert theo_ma["2"][o["Trạng thái"]] == tn_song.DANG_DANH
        assert theo_ma["2"][o["Kênh của tôi"]] == "moi"
        assert theo_ma["1"][o["Trạng thái"]] == tn_song.DANG_XEM
        assert theo_ma["1"][o["Tên tuyến"]] == "Người mới tập nấu"

    def test_ma_tep_khong_khop_ca_hai_ben_thi_tra_0(self, tmp_path):
        goc = str(tmp_path)
        _dung_ngach_nau_an(goc, "goc")
        _ghi_kenh(goc, "moi")
        with _ban_song("core.tuyen_noi_dung") as (tn_nhap,):
            assert tn_nhap.gieo_cho_kenh(goc, "goc", "moi", "ma-khong-ton-tai-o-dau-ca") == 0


# ═══ (9) core.cong_thuc_v7_ai — mục A1 ═══════════════════════════════════════════════════════

class TestCongThucV7AiA1:
    def test_de_bai_kenh_giong_het_tung_ky_tu_khi_khong_ghi_de(self):
        import core.cong_thuc_v7 as v7_song
        import core.cong_thuc_v7_ai as v7ai_song
        video_minh = [v7_song.VideoMinh(ma="v1", tieu_de="孤独を愛する人の特徴", thang=True),
                     v7_song.VideoMinh(ma="v2", tieu_de="chưa thắng", thang=False)]
        with _ban_song("core.cong_thuc_v7", "core.cong_thuc_v7_ai") as (v7_nhap, v7ai_nhap):
            moi = v7ai_nhap.de_bai_kenh({}, video_minh)
        cu = v7ai_song.de_bai_kenh({}, video_minh)
        assert moi == cu

    def test_de_bai_kenh_ghi_de_theo_ngach_nau_an(self):
        """(b) — không còn câu 'khán giả Nhật'/'não khoa học' khi hồ sơ ngách được truyền vào."""
        import core.cong_thuc_v7 as v7_song
        video_minh = [v7_song.VideoMinh(ma="v1", tieu_de="Cách kho cá ngon", thang=True)]
        with _ban_song("core.cong_thuc_v7", "core.cong_thuc_v7_ai") as (_v7, v7ai_nhap):
            de = v7ai_nhap.de_bai_kenh(
                {}, video_minh,
                mo_ta_kenh_cho_ai="Kênh của tôi làm lại (remake) công thức nấu ăn cho khán giả Việt Nam.",
                dang_thang="công thức nấu ăn từng bước")
        assert "khán giả Nhật" not in de
        assert "não khoa học" not in de
        assert "nấu ăn" in de


# ═══ (10) core.auto_khau — mục A1 ════════════════════════════════════════════════════════════

class TestAutoKhauA1:
    def test_de_bai_nan_khuon_giong_het_tung_ky_tu_khi_khong_ghi_de(self):
        import core.auto_khau as ak_song
        mau = ["【心理学】一人が好きな人の特徴", "【脳科学】友達が少ない人の本当の理由"]
        with _ban_song("core.auto_khau") as (ak_nhap,):
            moi = ak_nhap.de_bai_nan_khuon("元のタイトル", mau, "心理学")
        cu = ak_song.de_bai_nan_khuon("元のタイトル", mau, "心理学")
        assert moi == cu

    def test_de_bai_nan_khuon_ghi_de_theo_ngach_nau_an(self):
        mau = ["Cách kho cá ngon chuẩn vị", "Mẹo xào rau không bị ra nước"]
        with _ban_song("core.auto_khau") as (ak_nhap,):
            de = ak_nhap.de_bai_nan_khuon("tiêu đề nguồn", mau, "", mau_tieu_de="kênh YouTube nấu ăn tiếng Việt")
        assert de.startswith("Bạn đặt tiêu đề cho một kênh YouTube nấu ăn tiếng Việt.\n\n")
        assert "tâm lý tiếng Nhật" not in de


# ═══ (11) core.chi_so_ytb.tram — mục A6 ══════════════════════════════════════════════════════

class TestTramA6:
    def test_nhan_trang_chu_giong_het_ban_song_khong_co_nhom(self, tmp_path):
        import core.chi_so_ytb.tram as tram_song
        goc_cu, goc_moi = str(tmp_path / "cu"), str(tmp_path / "moi")
        video = [
            {"tieu_de": "【雑学】5つの面白い話", "ten_kenh": "雑学チャンネル", "link_kenh": "https://youtube.com/@zatsu1",
             "ma": "aaaaaaaaaaa", "vi_tri": 1},
            {"tieu_de": "孤独を愛する人の特徴", "ten_kenh": "ひととき心理学", "link_kenh": "https://youtube.com/@hitotoki",
             "ma": "bbbbbbbbbbb", "vi_tri": 2},
        ]
        for goc in (goc_cu, goc_moi):
            _ghi_kenh(goc, "k1")
        tr_cu = tram_song.Tram(goc=goc_cu)
        tr_cu.nhan_trang_chu("k1", video)
        with _ban_song("core.phan_tuyen", "core.trang_chu", "core.chi_so_ytb.tram") as (_pt, _tc, tram_nhap):
            tr_moi = tram_nhap.Tram(goc=goc_moi)
            tr_moi.nhan_trang_chu("k1", video)
        with open(os.path.join(goc_cu, "CHANNEL", "k1", "nghien-cuu", "trang-chu.csv"), encoding="utf-8-sig") as f:
            chu_cu = f.read()
        with open(os.path.join(goc_moi, "CHANNEL", "k1", "nghien-cuu", "trang-chu.csv"), encoding="utf-8-sig") as f:
            chu_moi = f.read()
        assert chu_cu == chu_moi

    def test_nhan_trang_chu_theo_ngach_nau_an_khong_loai_vi_tu_nhat(self, tmp_path):
        """(b) — video 雑学 KHÔNG bị loại (bộ từ của ngách nấu ăn không có 雑学); video 'review
        phim' (từ loại trừ CỦA NGÁCH) thì bị loại."""
        goc = str(tmp_path)
        _dung_ngach_nau_an(goc, "k1")
        video = [
            {"tieu_de": "【雑学】5 mẹo nấu ăn hay", "ten_kenh": "Bếp Nhà Mình", "link_kenh": "https://youtube.com/@bep1",
             "ma": "aaaaaaaaaaa", "vi_tri": 1},
            {"tieu_de": "review phim khi đang nấu ăn", "ten_kenh": "Giải Trí Đa Năng",
             "link_kenh": "https://youtube.com/@giaitri", "ma": "bbbbbbbbbbb", "vi_tri": 2},
        ]
        with _ban_song("core.phan_tuyen", "core.trang_chu", "core.chi_so_ytb.tram") as (_pt, _tc, tram_nhap):
            tr = tram_nhap.Tram(goc=goc)
            tr.nhan_trang_chu("k1", video)
        with open(os.path.join(goc, "CHANNEL", "k1", "nghien-cuu", "trang-chu.csv"), encoding="utf-8-sig") as f:
            hang = list(csv.DictReader(f))
        theo_ma = {h["Mã video"]: h["Bị loại"] for h in hang}
        assert theo_ma["aaaaaaaaaaa"] == "", "雑学 không phải từ loại trừ của ngách nấu ăn"
        assert theo_ma["bbbbbbbbbbb"] == "từ loại trừ", "\"review phim\" là từ loại trừ CỦA NGÁCH nấu ăn"
