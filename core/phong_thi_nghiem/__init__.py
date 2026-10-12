"""PHÒNG THÍ NGHIỆM CHỌN CONTENT — nhiều giả thuyết (bộ chấm) chạy song song, đo bằng kết quả thật (12/10/2026).

Kế hoạch: `workspace/chan-doan/ke-hoach-phong-thi-nghiem-content.md` (đây là ĐỢT 1). Thay "một công thức cố định"
bằng một sổ giả thuyết dạng DỮ LIỆU, mỗi ngày mọi giả thuyết xếp top-K trên CÙNG một vũ trụ ứng viên (chỉ đối thủ
thật) và CÙNG một kho đặc trưng; đo ba tầng (thị trường, cầu nối, sản xuất — tầng 3 là đợt 2).

Mảnh:
  * `nguon`      — đọc đĩa: "thế giới" của một kênh ở một mốc (hiện tại / hết một ngày quá khứ, không rò tương lai);
  * `vu_tru`     — vũ trụ ứng viên 3 nguồn (sổ đối thủ, pool Studio, trang chủ máy ảo) + luật đối thủ thật;
  * `dac_trung`  — kho đặc trưng chung, ảnh chụp ngày `CHANNEL/<k>/phong-thi-nghiem/kho-<ngày>.csv.gz`;
  * `gia_thuyet` — sổ giả thuyết `workspace/phong-thi-nghiem/gia-thuyet.json` + bộ chấm theo loại;
  * `nhat_ky`    — nhật ký bóng (top-K mỗi giả thuyết, mỗi kênh, mỗi ngày; chỉ nối);
  * `danh_gia`   — tầng 1 + tầng 2, hậu nghiệm Beta phân tầng, P(tốt nhất), bảng xếp hạng, khung
                   `chon_gia_thuyet_cho_khe` cho đợt 2;
  * `ai`         — H-AI (một lượt gọi/kênh/ngày, chỉ khi có ví);
  * `chay`       — lượt hằng ngày (nối vào `mot_nut` sau bước chấm V7, cờ `phong_thi_nghiem` mặc định BẬT) và chạy
                   ngược lịch sử; `bao_cao` — báo cáo chạy ngược / đợt 2.
  ĐỢT 2 (12/10/2026):
  * `danh_gia`   — tầng 1 CÔNG BẰNG (mỗi ứng viên một lần, kết quả nổ +7n, so rút ngẫu nhiên cùng vũ trụ / cùng tầng
                   gấp × tuổi × đà / tập qua cổng), ghi công chính xác của khe, tiên nghiệm tầng 1 yếu, P(tốt nhất) hai bậc;
  * `chia_khe`   — mỗi khe sản xuất chọn MỘT giả thuyết bằng Thompson phân tầng (nối vào `chien_luoc.xep_hang`, cờ
                   `phong_thi_nghiem_chia_khe`, mặc định BẬT cho `chia_khe.KENH_MAC_DINH`);
  * `luat`       — luật quyết: dẫn đầu / loại / mở thử / tốt nghiệp, sổ `quyet-dinh.jsonl`;
  * `truc_quan`  — tab «Phòng thí nghiệm» của trung tâm 8790; `bao_cao_nao` — mục trong `python -m core.nao xem`;
  * `gia_thuyet.de_xuat` — bộ não thêm giả thuyết mới dạng dữ liệu (`python -m core.nao gia-thuyet-moi`).

    python -m core.phong_thi_nghiem --ngay [--kenh K] [--ai]     # lượt hằng ngày (mặc định không gọi AI)
    python -m core.phong_thi_nghiem --nguoc [--tu 2026-09-20]    # chạy ngược + báo cáo
    python -m core.phong_thi_nghiem --danh-gia [--so-sanh-cu] [--bao-cao]   # tính lại bảng + luật quyết
    python -m core.phong_thi_nghiem --khe                        # chia khe minh hoạ + tỉ phần khe dự kiến

Không Qt, không mạng (trừ H-AI qua ví). Nhập gói này rẻ: các mảnh nạp muộn.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def bat(goc: str, kenh: str) -> bool:
    from .chay import bat as _bat  # noqa: PLC0415

    return _bat(goc, kenh)


def chay_ngay(goc: str, kenh: str, **kw: Any) -> Dict[str, Any]:
    from .chay import chay_ngay as _f  # noqa: PLC0415

    return _f(goc, kenh, **kw)


def chay_ngay_an_toan(goc: str, kenh: str, **kw: Any) -> Dict[str, Any]:
    """Lượt hằng ngày KHÔNG BAO GIỜ ném lỗi — nơi gọi là bước nghiên cứu của sản xuất."""
    try:
        from .chay import chay_ngay_an_toan as _f  # noqa: PLC0415
    except Exception as loi:  # noqa: BLE001 — nhập hỏng cũng không được chặn sản xuất
        return {"kenh": kenh, "loi": "nhập phòng thí nghiệm hỏng: {0}".format(str(loi)[:200])}
    return _f(goc, kenh, **kw)


def chay_nguoc(goc: str, kenh_ds: Any = None, **kw: Any) -> Dict[str, Any]:
    from .chay import chay_nguoc as _f  # noqa: PLC0415

    return _f(goc, kenh_ds, **kw)


def posterior(goc: str, kenh: str, **kw: Any) -> Dict[str, Tuple[float, float]]:
    from .danh_gia import posterior as _f  # noqa: PLC0415

    return _f(goc, kenh, **kw)


def chon_gia_thuyet_cho_khe(goc: str, kenh: str, **kw: Any) -> Dict[str, Any]:
    """Khung đợt 1 — xem `danh_gia.chon_gia_thuyet_cho_khe`; sản xuất dùng `chia_khe.phan_bo`."""
    from .danh_gia import chon_gia_thuyet_cho_khe as _f  # noqa: PLC0415

    return _f(goc, kenh, **kw)


def phan_bo_khe(goc: str, kenh: str, **kw: Any) -> Dict[str, Any]:
    """Chia MỘT khe sản xuất (Thompson phân tầng) — xem `chia_khe.phan_bo`."""
    from .chia_khe import phan_bo as _f  # noqa: PLC0415

    return _f(goc, kenh, **kw)


def bang_xep_hang(goc: str) -> Dict[str, Any]:
    from .danh_gia import doc_bang  # noqa: PLC0415

    return doc_bang(goc)


__all__ = ["bat", "chay_ngay", "chay_ngay_an_toan", "chay_nguoc", "posterior", "chon_gia_thuyet_cho_khe",
           "phan_bo_khe", "bang_xep_hang"]
