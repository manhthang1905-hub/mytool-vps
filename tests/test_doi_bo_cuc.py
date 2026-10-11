"""11/10/2026: lời nhắc ảnh LÀNH mà clip treo — viết lại phải ra bản KHÁC (đổi bố cục), không được trả đúng bản cũ."""
from core.viet_lai_prompt import doi_bo_cuc

GOC = ("Low angle looking up at the reference character looking out toward the glowing orange dusk horizon "
       "beyond the train tracks, Ultra-minimal thin-line stick figure psychology illustration")


def test_thay_goc_may_o_dau_va_giu_noi_dung():
    moi = doi_bo_cuc(GOC, 1)
    assert moi != GOC and not moi.lower().startswith("low angle")
    assert "reference character" in moi and "Ultra-minimal thin-line stick figure" in moi


def test_vong_khac_ra_bo_cuc_khac():
    assert doi_bo_cuc(GOC, 1) != doi_bo_cuc(GOC, 2)


def test_khong_co_goc_may_thi_them_vao_dau():
    p = "The reference character sits on a bench, Ultra-minimal thin-line stick figure"
    moi = doi_bo_cuc(p, 1)
    assert moi != p and moi.endswith(p)


def test_rong_tra_rong():
    assert doi_bo_cuc("", 1) == ""
