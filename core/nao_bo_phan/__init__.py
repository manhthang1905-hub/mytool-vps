"""NÃO BỘ PHẬN — MỘT thư viện chung cho 15 bộ phận: ghi ký ức, chắt thành nơ-ron, truy xuất nhanh (13/10/2026).

Thiết kế đã duyệt: `workspace/chan-doan/thiet-ke-nao-bo-phan.md`. ĐỢT 1: lõi + gom + nơ-ron lỗi + bản chiếu bài học
+ chỉ mục + `nho()` + sổ tay dựng từ số (không LLM, chỉ thư viện chuẩn — sqlite3 FTS5). ĐỢT 2: cảnh báo tách khỏi lỗi,
"lỗi đang tăng" theo sự cố, nốt thực thể, nhật ký bộ phận, `ky-lai`, GIẤC NGỦ (`ngu.py` — LLM duy nhất của gói, qua
thuê bao Claude Max), khối bài học vào lời nhắc của khâu viết (`khoi_loi_nhac`), panel trang 8790.

═══ LƯU TRỮ ═══ (dưới gốc tool; `nao/` là vault Obsidian — mở thư mục này là thấy đồ thị; KHÔNG lên git)

    nao/bo-phan.db                 su_kien (ký ức thô, không xoá) · con_tro · dung · giac_ngu · meta · chỉ mục
    nao/bo-phan/_ban-do.md         mục lục 15 bộ phận + số nơ-ron
    nao/bo-phan/<bộ phận>/so-tay.md            sổ tay ≤ 40 dòng: lỗi đang xảy ra · bài tự rút · cảnh báo · vừa hết · bản chiếu
    nao/bo-phan/<bộ phận>/nhat-ky.md           nhật ký thay đổi (chỉ nối thêm): gom · ngủ · soát
    nao/bo-phan/<bộ phận>/loi/<chữ ký>.md      nơ-ron LỖI (hoặc CẢNH BÁO — `muc: canh-bao`)
    nao/bo-phan/<bộ phận>/bai-hoc/BH-<băm>.md  nơ-ron BÀI HỌC bản chiếu (sổ có sẵn, chỉ đọc)
    nao/bo-phan/<bộ phận>/bai-hoc/BH-N<băm>.md nơ-ron BÀI HỌC tự rút khi ngủ (`nguon: ngu`, có mã sự kiện bằng chứng)
    nao/bo-phan/thuc-the/<loại>/<tên>.md       nốt thực thể: kenh · khau · engine · bo-chon · ma-kiem

═══ LUẬT (mỗi luật một câu) ═══

1. `ghi()` không bao giờ ném lỗi, chờ khoá ≤ 0,5 giây; `khoa` trùng thì bỏ qua — gom lại bao nhiêu lần cũng không trùng.
2. Bộ gom (`bo_gom.NGUON`) chỉ ĐỌC kho có sẵn, tăng dần theo con trỏ từng tệp; lần đầu thấy một tệp chỉ nhìn lùi
   `NGAY_GOM_DAU` ngày; tệp hỏng → cảnh báo được đếm, không dừng lượt gom.
3. Chữ ký lỗi (`chu_ky_su_kien`, một chỗ) = băm của câu đã chuẩn hoá; lỗi kiểm chất lượng ký theo mã kiểm, trôi DOM
   ký theo khoá bộ chọn (DU PHONG riêng TU CHUA). Đổi luật → tăng `PHIEN_KY`, lượt gom sau tự `ky_lai` một lần.
4. Lỗi của một khâu trong một lượt là MỘT sự kiện dù sổ ngày lẫn `trang-thai.json` cùng báo.
5. Nơ-ron lỗi: gặp trong 48h = đang xảy ra; im ≥ 7 ngày = đã hết; giữa hai mốc = tạm lặng; đang xảy ra mà lần quay
   lại sau quãng im ≥ 7 ngày nằm trong 7 ngày qua = tái phát.
6. Nơ-ron mà MỌI sự kiện là cảnh báo (DU PHONG, mục kiểm `canh_bao`) là CẢNH BÁO: trọng số × 0,3, không vào "lỗi đang
   tăng"; "lỗi đang tăng" xếp theo nhịp SỰ CỐ (kênh × gói/ngày) 48h qua so với 5 ngày trước.
7. Sự kiện `sua` cùng chữ ký mà ≥ 7 ngày sau lỗi không quay lại = cách sửa ĐÃ KIỂM.
8. Bài học bản chiếu: α = 1 + phiếu ủng hộ, β = 1 + phiếu phản bác (sổ giám đốc); sổ sản xuất lấy α theo độ tin. Bài
   tự rút chỉ giấc ngủ / soát sửa (luật ở `ngu.py`).
9. Sổ tay dựng tất định từ số, ≤ `SO_TAY_TOI_DA_DONG` dòng; tệp chỉ ghi lại khi nội dung đổi; mỗi lượt đổi gì thì
   nối một khối vào `nhat-ky.md` của bộ phận.
10. `nho()` = bm25 (hai bộ tách từ) × Thompson Beta(α, β) (lỗi: trọng số theo độ dày) × độ tươi, +1 bước lan qua
   nốt thực thể; 15% quyết định có mã là đối chứng (không đưa gì); một quyết định một dòng `dung`.

═══ DÙNG ═══

    from core import nao_bo_phan as nbp
    nbp.ghi(goc, "giong-doc", "loi", kenh="K1", noi_dung="...", khoa="...")     # bộ phận tự ghi
    nbp.nho(goc, "anh-clip", "máy chủ ảnh treo 12 phút", k=5, quyet_dinh="K1-0031:anh")
    nbp.khoi_loi_nhac(goc, "tieu_de", "<tiêu đề nháp>", quyet_dinh="K1-0031:tieu_de:2026-10-14")

    python -X utf8 -m core.nao_bo_phan gom [--goc G] [--ra R]    # gom + nơ-ron + sổ tay + chỉ mục (R: gốc GHI)
    python -X utf8 -m core.nao_bo_phan ngu [--bo-phan X] [--toi-da N] [--soat]   # giấc ngủ đêm (Claude Max)
    python -X utf8 -m core.nao_bo_phan xem [--bo-phan X]         # lỗi đang tăng + một dòng mỗi bộ phận / sổ tay
    python -X utf8 -m core.nao_bo_phan nho --bo-phan X "<ngữ cảnh>"
    python -X utf8 -m core.nao_bo_phan ky-lai                    # tính lại chữ ký theo luật hiện hành
    python -X utf8 -m core.nao_bo_phan dung-lai-chi-muc          # dựng lại chỉ mục từ vault
"""

from __future__ import annotations

from ._chung import (BO_PHAN, LOAI, NGAY_GOM_DAU, SO_TAY_TOI_DA_DONG, TI_LE_DOI_CHUNG, chu_ky, chuan_hoa,
                     duong_db, duong_vault)
from .bo_gom import gom, ky_lai
from .kho import ghi
from .no_ron import dung_lai_chi_muc
from .truy_xuat import dong_bo_phan, dong_loi_dang_tang, khoi_loi_nhac, loi_dang_tang, nho, tom_tat

__all__ = ["BO_PHAN", "LOAI", "NGAY_GOM_DAU", "SO_TAY_TOI_DA_DONG", "TI_LE_DOI_CHUNG", "chu_ky", "chuan_hoa",
           "duong_db", "duong_vault", "ghi", "gom", "ky_lai", "nho", "loi_dang_tang", "dong_loi_dang_tang",
           "dong_bo_phan", "khoi_loi_nhac", "tom_tat", "dung_lai_chi_muc"]
