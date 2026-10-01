"""KHUÔN việc của giám đốc kênh — chép thành `core/giam_doc/<ten>.py` rồi điền.

Tệp bắt đầu bằng `_` nên sổ đăng ký bỏ qua; bản chép (không `_`) tự được phát hiện, không sửa chỗ nào
khác. Luật:
* THUẦN và 0 đồng: chỉ đọc `bs` (BangSo — `du_lieu.tom_tat`), không gọi mạng, không ghi đĩa.
* Mỗi quan sát là một câu CÓ SỐ + `n` + `tin_cay` ("thap" n<3, "vua" n<6, "cao").
* Đề xuất chỉ là THỰC ĐƠN: LLM (`quan_ly.nghi`) chọn, `gioi_han.kiem` loại mọi thứ lạ. Không tự áp.
* Chỉ số của chính kênh; số nhóm chỉ là tiên nghiệm yếu khi n < 3.
* Thiếu dữ liệu → `ap_dung` trả 0 (bộ điều phối bỏ qua, không log lỗi).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

TEN = "ten_viec"                 # = tên tệp
MO_TA = "Một câu: việc này canh / cải thiện cái gì"
NHIP = "tuan"                    # "ngay" | "tuan"
CHI_SO_CHINH = ""                # 1 thí nghiệm mở / chỉ số chính; "" = việc không mở thí nghiệm


def ap_dung(bs: Any) -> float:
    """0..1 — đủ dữ liệu tới đâu; 0 = không chạy."""
    return 0.0


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """[{cau (có số), n, tin_cay}] — thứ giám đốc thấy."""
    return []


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Thực đơn hành động. Mỗi mục: loai ("tham_so" | "chi_dao" | "viec_studio"), khoa?, gia_tri?,
    video_id?, noi_dung?, gia_thuyet, chi_so, co_mau, han_ngay (+ nen{gia_tri,n} khi mở thí nghiệm)."""
    return []


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """{ket: giu|bo|mo_rong|chua_du, so:{nen, moi, n}} cho thí nghiệm của việc này; None = không phán."""
    return None
