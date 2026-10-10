"""10/10/2026: ShopAPI tắt hẳn engine TTS cả buổi trưa — câu báo phải là "nhà máy nghỉ" (chờ rồi thử lại),
KHÔNG phải `CHET` (hai lần liên tiếp là trần L3 bỏ hẳn lượt dở, mất kịch bản/ảnh đã làm)."""
from core import su_co


def test_khong_co_engine_tts_la_nha_may_nghi():
    cau = 'Hệ thống không có engine nào phục vụ loại yêu cầu "tts".'
    assert su_co.phan_loai(RuntimeError(cau)) == su_co.NHA_MAY_NGHI
    boc = "Dừng ở “Đọc thành giọng”: " + cau        # câu lưu lại trong sổ sau khi lượt dừng
    assert su_co.phan_loai(RuntimeError(boc)) == su_co.NHA_MAY_NGHI


def test_nha_may_nghi_khong_nam_trong_loai_khong_tu_het():
    from core import tu_chay
    assert su_co.NHA_MAY_NGHI not in tu_chay._LOAI_LOI_KHONG_TU_HET  # noqa: SLF001


def test_cau_tieng_anh_cung_vay():
    assert su_co.phan_loai(RuntimeError("No engine available for request type tts")) == su_co.NHA_MAY_NGHI
