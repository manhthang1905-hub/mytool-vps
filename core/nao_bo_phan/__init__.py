"""NÃO BỘ PHẬN — MỘT thư viện chung cho 15 bộ phận: ghi ký ức, chắt thành nơ-ron, truy xuất nhanh (13/10/2026).

Thiết kế đã duyệt: `workspace/chan-doan/thiet-ke-nao-bo-phan.md`. Đây là ĐỢT 1: lõi + gom + nơ-ron lỗi + bản chiếu
bài học + chỉ mục + `nho()` + sổ tay dựng từ số. KHÔNG LLM, không mạng, chỉ thư viện chuẩn (sqlite3 FTS5).

═══ LƯU TRỮ ═══ (dưới gốc tool; `nao/` là vault Obsidian — mở thư mục này là thấy đồ thị; KHÔNG lên git)

    nao/bo-phan.db                 su_kien (ký ức thô, không xoá) · con_tro · dung · chỉ mục (dựng lại được từ vault)
    nao/bo-phan/_ban-do.md         mục lục 15 bộ phận + số nơ-ron
    nao/bo-phan/<bộ phận>/so-tay.md            sổ tay ≤ 40 dòng: lỗi đang xảy ra · vừa hết · bài học tốt nhất
    nao/bo-phan/<bộ phận>/loi/<chữ ký>.md      nơ-ron LỖI
    nao/bo-phan/<bộ phận>/bai-hoc/BH-<băm>.md  nơ-ron BÀI HỌC (bản chiếu chỉ đọc của sổ có sẵn)
    nao/bo-phan/thuc-the/kenh/<K>.md           nốt kênh — nơ-ron nối vào để Obsidian vẽ đồ thị theo kênh

═══ LUẬT (mỗi luật một câu) ═══

1. `ghi()` không bao giờ ném lỗi, chờ khoá ≤ 0,5 giây; `khoa` trùng thì bỏ qua — gom lại bao nhiêu lần cũng không trùng.
2. Bộ gom (`bo_gom.NGUON`) chỉ ĐỌC kho có sẵn, tăng dần theo con trỏ từng tệp; lần đầu thấy một tệp chỉ nhìn lùi
   `NGAY_GOM_DAU` ngày; tệp hỏng → cảnh báo được đếm, không dừng lượt gom.
3. Chữ ký lỗi = băm của câu đã chuẩn hoá (số → `#`, id video → `<id>`, `UC…` → `<uc>`, đường dẫn → `<duong>`, mã
   gói → `<goi>`, tên kênh → `<kenh>`); lỗi kiểm chất lượng ký theo mã kiểm, trôi DOM ký theo khoá bộ chọn.
4. Lỗi của một khâu trong một lượt là MỘT sự kiện dù sổ ngày lẫn `trang-thai.json` cùng báo.
5. Nơ-ron lỗi: gặp trong 48h = đang xảy ra; im ≥ 7 ngày = đã hết; giữa hai mốc = tạm lặng; đang xảy ra mà lần quay
   lại sau quãng im ≥ 7 ngày nằm trong 7 ngày qua = tái phát.
6. Sự kiện `sua` cùng chữ ký mà ≥ 7 ngày sau lỗi không quay lại = cách sửa ĐÃ KIỂM.
7. Bài học là bản chiếu: α = 1 + phiếu ủng hộ, β = 1 + phiếu phản bác (sổ giám đốc); sổ sản xuất lấy α theo độ tin.
8. Sổ tay dựng tất định từ số, ≤ `SO_TAY_TOI_DA_DONG` dòng; tệp chỉ ghi lại khi nội dung đổi.
9. `nho()` = bm25 (hai bộ tách từ) × Thompson Beta(α, β) (lỗi: trọng số theo độ dày) × độ tươi, +1 bước lan qua
   nốt kênh; 15% quyết định có mã là đối chứng (không đưa gì) để sau này đo bài học có giúp thật không.

═══ DÙNG ═══

    from core import nao_bo_phan as nbp
    nbp.ghi(goc, "giong-doc", "loi", kenh="K1", noi_dung="...", khoa="...")     # bộ phận tự ghi (đợt 2)
    nbp.nho(goc, "anh-clip", "máy chủ ảnh treo 12 phút", k=5, quyet_dinh="K1-0031:anh")

    python -X utf8 -m core.nao_bo_phan gom [--goc G] [--ra R]    # gom + nơ-ron + sổ tay + chỉ mục (R: gốc GHI)
    python -X utf8 -m core.nao_bo_phan xem [--bo-phan X]         # lỗi đang tăng / sổ tay một bộ phận
    python -X utf8 -m core.nao_bo_phan nho --bo-phan X "<ngữ cảnh>"
    python -X utf8 -m core.nao_bo_phan dung-lai-chi-muc          # dựng lại chỉ mục từ vault
"""

from __future__ import annotations

from ._chung import (BO_PHAN, LOAI, NGAY_GOM_DAU, SO_TAY_TOI_DA_DONG, TI_LE_DOI_CHUNG, chu_ky, chuan_hoa,
                     duong_db, duong_vault)
from .bo_gom import gom
from .kho import ghi
from .no_ron import dung_lai_chi_muc
from .truy_xuat import dong_loi_dang_tang, loi_dang_tang, nho

__all__ = ["BO_PHAN", "LOAI", "NGAY_GOM_DAU", "SO_TAY_TOI_DA_DONG", "TI_LE_DOI_CHUNG", "chu_ky", "chuan_hoa",
           "duong_db", "duong_vault", "ghi", "gom", "nho", "loi_dang_tang", "dong_loi_dang_tang",
           "dung_lai_chi_muc"]
