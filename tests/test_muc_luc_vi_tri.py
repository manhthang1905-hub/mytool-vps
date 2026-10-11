"""12/10/2026: khối 目次 phải nằm TRONG phần DESCRIPTION, không bao giờ lọt sau KEYWORDS:/TAGS: (cột thẻ)."""
from core.phan_video import chen_khoi_vao_mo_ta

KHOI = ["━━━━", "📌 目次", "00:00 a", "02:00 b", "04:00 c", "━━━━"]


def _vi_tri(cac, chu):
    return next(i for i, x in enumerate(cac) if x.startswith(chu))


def test_khong_co_hashtags_label_thi_chen_truoc_keywords():
    seo = ["DESCRIPTION:", "mô tả", "", "#a #b", "", "KEYWORDS:", "k1, k2"]
    ra = chen_khoi_vao_mo_ta(seo, KHOI)
    assert _vi_tri(ra, "📌") < _vi_tri(ra, "#a") < _vi_tri(ra, "KEYWORDS:")
    assert ra[-1] == "k1, k2"


def test_co_hashtags_label_giu_nhu_cu():
    seo = ["DESCRIPTION:", "mô tả", "", "HASHTAGS:", "#a"]
    ra = chen_khoi_vao_mo_ta(seo, KHOI)
    assert _vi_tri(ra, "📌") < _vi_tri(ra, "HASHTAGS:")


def test_mo_ta_khong_hashtag_chen_sau_dong_chu_cuoi():
    seo = ["DESCRIPTION:", "mô tả 1", "mô tả 2", "", "TAGS:", "t"]
    ra = chen_khoi_vao_mo_ta(seo, KHOI)
    assert _vi_tri(ra, "mô tả 2") < _vi_tri(ra, "📌") < _vi_tri(ra, "TAGS:")


def test_khong_co_nhan_nao_thi_noi_cuoi():
    ra = chen_khoi_vao_mo_ta(["mô tả"], KHOI)
    assert ra[0] == "mô tả" and ra[-1] == "━━━━"
