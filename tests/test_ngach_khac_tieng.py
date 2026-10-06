"""Máy mới + chủ đề mới + TIẾNG KHÁC (06/10/2026 — chạy khô ngách "nấu ăn gia đình Hàn · KR · ko", 2 kênh giả).

Mỗi bài chốt một chỗ chạy thử đã vỡ hoặc ngầm giả định tiếng Nhật / máy này:

* bìa: font Nhật (Yu Gothic/Meiryo) không có chữ Hangul → ô vuông; trần chữ bìa 12/20 ký tự đếm cho chữ Nhật cắt cụt
  bìa tiếng Anh/Việt;
* kênh THỨ HAI của nhóm đánh lại đúng tệp khán giả của kênh đầu, tên kênh rơi về câu tiếng Việt;
* kenh.yaml không có quốc gia → hồ sơ Studio/địa điểm xem phải suy từ tiếng (en ≠ luôn US);
* ngôn ngữ video Studio (`ngon_ngu_video`) thiếu `ko`; nhãn mục lục chỉ có 目次/Chapters.

Dữ liệu đều giả (tên món/kênh bịa), chỉ ghi trong `tmp_path`. Không mạng, không tiền, không Qt.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys

import pytest

from core import khoi_tao_ngach as ktn

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HO_SO_HAN = {
    "mo_ta_ngach": "집밥 요리 레시피 — món nhà làm kiểu Hàn, làm theo từng bước",
    "mo_ta_cho_loc_ai": "Thuộc ngách: video tiếng Hàn dạy nấu một món nhà làm. Lệch: mukbang, review quán.",
    "luat_chon": ["Chỉ chọn video dạy nấu một món cụ thể."],
    "tieu_chi_doi_thu": ["kênh nói tiếng Hàn", "dạy nấu ăn", "khán giả nấu ở nhà", "video dài có lời đọc"],
    "khan_gia_mo_ta": "",
    "tep_khan_gia": [{"ma": "moi-tap-nau", "ten": "Người mới tập nấu", "ten_ngan": "Mới tập"},
                     {"ma": "noi-tro", "ten": "Nội trợ lâu năm", "ten_ngan": "Nội trợ"}],
    "cum": {"jjigae": {"ten": "Canh hầm", "tu": ["찌개", "국"]}},
    "tu_khoa_tim": ["집밥 레시피", "반찬 만들기"],
    "mau_tieu_de": "kênh YouTube nấu ăn gia đình tiếng Hàn",
    "the_loai_en": "Korean home cooking",
    "giong_van": "Korean — warm, friendly home cook",
    "ten_kenh_goi_y": "오늘의 밥상",
    "thi_truong": {"mui_gio": "Asia/Seoul", "gio_dang_goi_y": "18:00", "quy_mo": "vua"},
}


def _goi_gia(loi_nhac, *, khoa="", toi_da_token=0, mo_hinh=""):
    if "ho-so-ngach" in khoa:
        return json.dumps(HO_SO_HAN, ensure_ascii=False)
    if khoa.startswith("khoi-tao:style"):
        return json.dumps({k: "Korean kitchen " + k for k in ktn.KHOA_STYLE_VIET_LAI})
    return loi_nhac.split("=== LỜI NHẮC GỐC", 1)[-1].split("===\n", 1)[-1]


def _anh_gia(prompt, dich):
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    with open(dich, "wb") as tep:
        tep.write(b"\x89PNG\r\n\x1a\n" + b"0" * 2000)
    return dich


def _goc(tmp_path) -> str:
    goc = str(tmp_path / "MyTool")
    shutil.copytree(os.path.join(GOC_KHO, "CHANNEL", "_KHUON"), os.path.join(goc, "CHANNEL", "_KHUON"))
    return goc


def _tao(goc, ma):
    yc = ktn.YeuCau(chu_de="nấu ăn gia đình Hàn", quoc_gia="KR", ngon_ngu="ko", nhom="bep-han", ma_kenh=ma,
                    bo_nghien_cuu=True)
    return ktn.khoi_tao(goc, yc, goi=_goi_gia, tim=lambda *a, **k: [], tao_anh=_anh_gia, log=lambda m: None)


def _yaml(goc, ma):
    from core.kenh import doc_yaml
    return doc_yaml(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"))


# ── khởi tạo hai kênh cùng nhóm ──────────────────────────────────────────────────────────────────


def test_hai_kenh_cung_nhom_moi_kenh_mot_tep_va_ten_rieng(tmp_path):
    goc = _goc(tmp_path)
    _tao(goc, "KA1")
    _tao(goc, "KA2")
    a, b = _yaml(goc, "KA1"), _yaml(goc, "KA2")
    assert a["tep"] == "moi-tap-nau" and b["tep"] == "noi-tro", "kênh thứ hai phải đánh tệp còn trống"
    assert a["ten"] == "오늘의 밥상"
    assert b["ten"] != a["ten"] and b["ten"].startswith("오늘의 밥상"), \
        "kênh 2 dùng lại hồ sơ: tên gợi ý vẫn đọc được (không rơi về câu tiếng Việt), và không trùng kênh 1"
    assert b["giong_van"] == "Korean — warm, friendly home cook"
    for y in (a, b):
        assert y["ngon_ngu"] == "ko" and y["quoc_gia"] == "KR" and y["dia_diem_xem"] == "KR"
        assert y["chu_bia_hoa"] is False


def test_khan_gia_mo_ta_khong_bao_gio_rong(tmp_path):
    """Khoá rỗng → `bien_tap_content` lùi về khán giả mặc định của mã (người Nhật 55+)."""
    hs = ktn.chuan_hoa_ho_so(HO_SO_HAN, ktn.YeuCau(chu_de="nấu ăn", quoc_gia="KR", ngon_ngu="ko").chuan())
    assert hs["khan_gia_mo_ta"] and "Nhật" not in hs["khan_gia_mo_ta"]
    nhap = ktn.chuan_hoa_ho_so(ktn.ho_so_nhap(ktn.YeuCau(chu_de="tài chính", quoc_gia="US", ngon_ngu="en").chuan()),
                               ktn.YeuCau(chu_de="tài chính", quoc_gia="US", ngon_ngu="en").chuan())
    assert nhap["khan_gia_mo_ta"] and "Nhật" not in nhap["khan_gia_mo_ta"]


def test_thiet_lap_kenh_bu_quoc_gia_va_mo_ta_ngach_tu_ho_so(tmp_path):
    from core import thiet_lap_kenh as tl

    goc = _goc(tmp_path)
    _tao(goc, "KA1")
    kh = tl._yaml_kenh("KA1", goc)
    assert kh["quoc_gia"] == "KR"
    assert "집밥" in kh["luat_chon"], "LLM viết hồ sơ Studio phải biết kênh nói về gì"
    p = tl.loi_nhac_ho_so("KA1", kh, [])
    assert "language of the channel text: ko" in p and "집밥" in p


def test_kenh_khong_nhom_giu_nguyen_kenh_yaml(tmp_path):
    from core import thiet_lap_kenh as tl

    d = tmp_path / "CHANNEL" / "LE1"
    d.mkdir(parents=True)
    (d / "kenh.yaml").write_text('ma: "LE1"\nngon_ngu: "ja"\n', encoding="utf-8")
    kh = tl._yaml_kenh("LE1", str(tmp_path))
    assert "luat_chon" not in kh and "quoc_gia" not in kh


# ── bìa: font + trần chữ theo loại chữ ───────────────────────────────────────────────────────────


def test_font_bia_theo_loai_chu():
    from core import bia_theo_khuon as b

    assert b.bo_font_cho("一人の時間", "ja")[0] == "NotoSansJP-Black.otf", "chữ Nhật giữ nguyên thứ tự font cũ"
    assert b.bo_font_cho("IQ 130", "")[0] == "NotoSansJP-Black.otf", "không biết tiếng + ASCII trơn: như cũ"
    assert b.bo_font_cho("된장찌개", "")[0] in b._FONT_HAN
    assert b.bo_font_cho("Easy dinner", "ko")[0] in b._FONT_HAN
    assert b.bo_font_cho("Bí quyết nấu phở", "")[0] in b._FONT_LA_TINH
    assert b.bo_font_cho("Easy dinner", "en")[0] in b._FONT_LA_TINH


def test_tim_font_doc_thu_muc_assets_fonts(tmp_path):
    from core import bia_theo_khuon as b

    fonts = tmp_path / "assets" / "fonts"
    fonts.mkdir(parents=True)
    (fonts / "NotoSansKR-Black.otf").write_bytes(b"x")
    # Font kèm tool (`assets/fonts/`) thắng font hệ thống — máy không có Malgun Gothic vẫn vẽ được Hangul.
    assert b._tim_font(str(tmp_path), "된장찌개", "ko").endswith("NotoSansKR-Black.otf")


def test_tran_chu_bia_la_tinh_gap_doi_chu_nhat_giu_nguyen():
    from core import bia_theo_khuon as b

    assert b.tran_ky_tu("一人の時間が長い") == (b.TRAN_KY_TU_TANG, b.TRAN_KY_TU_TONG)
    assert b.tran_ky_tu("된장찌개 황금레시피") == (b.TRAN_KY_TU_TANG, b.TRAN_KY_TU_TONG)
    assert b.tran_ky_tu("Never wash rice") == (b.TRAN_KY_TU_TANG * 2, b.TRAN_KY_TU_TONG * 2)
    tang = [{"phan_mau": [{"chu": "NEVER WASH"}]}, {"phan_mau": [{"chu": "RICE LIKE THIS"}]}]
    assert b.kiem_chu_tang(tang, "NEVER WASH RICE LIKE THIS", co_dinh=True), "bìa tiếng Anh 21 chữ cái phải hợp lệ"
    assert not b.kiem_chu_tang([{"phan_mau": [{"chu": "一人の時間が長いほどストレス"}]}], "", co_dinh=False)


# ── Studio / mô tả ───────────────────────────────────────────────────────────────────────────────


def test_ngon_ngu_video_studio_co_tieng_han():
    with io.open(os.path.join(GOC_KHO, "vm", "studio-selectors.json"), encoding="utf-8") as tep:
        bo = json.load(tep)
    for ma in ("ja", "vi", "en", "ko"):
        ten = bo["ngon_ngu_video"][ma]
        assert ten and isinstance(ten, list), ma
    assert "Tiếng Hàn" in bo["ngon_ngu_video"]["ko"], "máy đăng ép giao diện vi — tên tiếng Việt phải có"


def test_ten_nuoc_du_cho_moi_nuoc_suy_tu_tieng():
    vm = os.path.join(GOC_KHO, "vm")
    if vm not in sys.path:
        sys.path.append(vm)       # cùng cách `tests/test_thiet_lap_kenh.py` nạp module máy ảo
    import thiet_lap_kenh_dom as tl
    for nn, gl in tl.GL_THEO_NGON_NGU.items():
        assert gl in tl.TEN_NUOC, (nn, gl)


def test_nhan_muc_luc_theo_tieng():
    from core.phan_video import co_muc_luc, dau_muc_luc

    assert dau_muc_luc("ja") == "📌 目次", "kênh Nhật giữ nguyên"
    assert dau_muc_luc("ko") == "📌 목차" and dau_muc_luc("vi") == "📌 Mục lục"
    assert dau_muc_luc("en") == dau_muc_luc("") == "📌 Chapters"
    assert co_muc_luc("x\n📌 목차\n0:00 a") and co_muc_luc("目次") and not co_muc_luc("목차를 보세요")


def test_dat_muc_luc_seo_kenh_han(tmp_path):
    from core.phan_video import dat_muc_luc_seo

    p = tmp_path / "1-seo.txt"
    p.write_text("TITLE: x\nDESCRIPTION:\n본문\nHASHTAGS: #a\n", encoding="utf-8")
    assert dat_muc_luc_seo(str(p), ["0:00 시작", "1:00 재료", "2:00 끓이기"], "ko") == "chen"
    chu = p.read_text(encoding="utf-8")
    assert "📌 목차" in chu and "目次" not in chu
    assert dat_muc_luc_seo(str(p), ["0:00 시작", "1:00 재료", "2:00 끓이기"], "ko") == "giu", "chạy lại không chèn đúp"


def test_whisper_nhan_ma_ngan():
    """`nghe_bang_whisper` chuẩn hoá mã tiếng ("ko-KR"/"KO" → "ko") trước khi đưa Whisper — đọc mã nguồn, không nạp
    mô hình (faster-whisper nặng, máy sạch có thể chưa có models/)."""
    import re

    with io.open(os.path.join(GOC_KHO, "core", "phu_de.py"), encoding="utf-8") as tep:
        chu = tep.read()
    assert re.search(r'language=\(str\(ngon_ngu or ""\)\.strip\(\)\.lower\(\)\.split\("-"\)\[0\]', chu)


def test_kho_giong_nhom_tieng_khac_khong_gieo_giong_nhat(tmp_path):
    """`mo_kenh.doc_kho_giong` gieo GIONG_KHOI_DAU (giọng Nhật) cho nhóm chưa có kho — nhóm tiếng Hàn thì không."""
    from core import mo_kenh as mk

    goc = _goc(tmp_path)
    _tao(goc, "KA1")
    assert mk.doc_kho_giong(goc, "bep-han", ghi=False) == [], "nhóm Hàn chưa có giọng Hàn nào → rỗng, không giọng Nhật"
    d = os.path.join(goc, "CHANNEL", "_NHOM", "tam-ly-x")
    os.makedirs(d)
    io.open(os.path.join(d, "ngach.yaml"), "w", encoding="utf-8").write("thi_truong:\n  ngon_ngu: ja\n")
    assert [g["voice_id"] for g in mk.doc_kho_giong(goc, "tam-ly-x", ghi=False)] == \
        [g["voice_id"] for g in mk.GIONG_KHOI_DAU], "nhóm tiếng Nhật giữ nguyên như cũ"
