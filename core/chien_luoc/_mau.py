"""KHUÔN công thức chọn nguồn — chép tệp này thành `core/chien_luoc/<ten>.py` rồi điền 3 chỗ.

Tệp bắt đầu bằng `_` nên sổ đăng ký bỏ qua; bản chép (không có `_`) được tự phát hiện, không phải
sửa `tu_chay` hay chỗ nào khác. Hợp đồng đầy đủ + dòng chuẩn: docstring `core/chien_luoc/ngu_canh.py`.

Luật:
* KHÔNG `import core.tu_chay` ở đầu tệp (tu_chay nạp gói này lúc khởi động → vòng nhập). Cần gì của
  tu_chay thì nhập TRONG hàm.
* `cham` không gọi mạng, không tốn ví: chỉ đọc sổ trên đĩa (trạm `/loi-thoai/can-lay` gọi nó nhiều
  lần mỗi ngày). Việc cần AI (phân cụm theo nghĩa, biên tập viên) đã có ở khâu sau.
* Phân loại nội dung theo NGHĨA (nhãn cụm do AI gán, cột Tuyến của sổ content…), KHÔNG thêm bộ lọc từ
  khoá mới.
* Trả dòng ĐÃ XẾP, mạnh nhất trước; `diem` theo thang riêng của công thức (bộ điều phối trộn theo
  THỨ HẠNG, không so điểm giữa các công thức).
* Thiếu dữ liệu thì `ap_dung` trả 0 — bộ điều phối tự bỏ qua, không log lỗi.
"""

from __future__ import annotations

from typing import Any, Dict, List

TEN = "ten_cong_thuc"            # = tên tệp; dùng trong kenh.yaml `chien_luoc: "ten_cong_thuc:0.3, …"`
MO_TA = "Một câu: công thức này bắt loại nguồn nào"
LUI_KHI_RONG = ""                # tên công thức lùi về khi bảng rỗng; "" = không lùi


def ap_dung(nc: Any) -> float:
    """0..1 — công thức hợp với kênh/giai đoạn này tới đâu; 0 = không dùng được (thiếu dữ liệu)."""
    return 0.0


def cham(nc: Any) -> List[Dict[str, Any]]:
    """Bảng ứng viên, dòng chuẩn. Luôn qua `nc.loc` (loại đã làm / trùng tiêu đề) trước khi trả."""
    ds: List[Dict[str, Any]] = []
    # ds.append({"nguon": TEN, "ma": ..., "link": ..., "tieu_de": ..., "kenh": ..., "diem": 0..100,
    #            "loai": "", "view": ..., "ly_do": ["vì sao dòng này mạnh — có số"]})
    return nc.loc(ds)
