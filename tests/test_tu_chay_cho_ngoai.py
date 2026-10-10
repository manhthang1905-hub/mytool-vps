"""10/10/2026: lượt dừng vì PHÍA ShopAPI (TTS tắt cả buổi) không bị trần L3 (3 lần nhặt lại) bỏ oan;
lượt kẹt thật (câu lạ / hỏng thật) vẫn bị trần chặn như cũ."""
import datetime as dt

from core import tu_chay

TTS = 'Dừng ở “Đọc thành giọng”: Hệ thống không có engine nào phục vụ loại yêu cầu "tts".'


def _run(loi_dung="", loi="", so_lan=3):
    return {"san_xuat": {"loi": loi, "loi_dung": loi_dung, "khau_hong": ["giong-doc"]},
            "phuc_hoi": {"so_lan": so_lan, "lan_dau_luc": dt.datetime.now().timestamp()}}


def _ly_do(run):
    hom = dt.date.today()
    return tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom, hom.isoformat())  # noqa: SLF001


def test_tts_tat_mien_tran_so_lan():
    assert _ly_do(_run(loi_dung=TTS)) == ""


def test_cau_la_van_bi_tran():
    assert "chạm trần" in _ly_do(_run(loi_dung="Dừng ở “Đọc thành giọng”: lần chạy trước bị dừng đột ngột"))


def test_tran_48_gio_van_giu_cho_loi_shopapi():
    run = _run(loi_dung=TTS)
    run["phuc_hoi"]["lan_dau_luc"] = (dt.datetime.now() - dt.timedelta(hours=50)).timestamp()
    assert "48" in _ly_do(run)


def test_loi_dung_khong_vao_luat_loi_lap_lai():
    """Câu tóm tắt nằm ở `loi_dung`, KHÔNG phải `loi` → `_loai_loi_san_xuat` không thấy, không bỏ vì lặp."""
    run = _run(loi_dung="Dừng ở “Ảnh”: câu lạ không khớp dấu hiệu nào", so_lan=1)
    run["phuc_hoi"]["loai_loi_truoc"] = "chet"
    assert tu_chay._loai_loi_san_xuat(run) == ""  # noqa: SLF001
    assert _ly_do(run) == ""
