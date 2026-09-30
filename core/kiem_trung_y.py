"""Việc 5b (29/09/2026) — LỚP KIỂM TRÙNG Ý BẰNG LLM, bổ sung cho so CHỮ của
`core/trung_tieu_de.py`.

═══ VÌ SAO CẦN THÊM LỚP NÀY ═══

`core.trung_tieu_de` so hai tiêu đề bằng `difflib.SequenceMatcher` (ngưỡng
0,80, xác nhận trên dữ liệu thật — xem docstring đầu tệp đó) — bắt tốt ca chép
GẦN NGUYÊN VĂN, nhưng bỏ lọt ca CÙNG Ý, KHÁC DIỄN ĐẠT. Ca thật đo được
28→29/09/2026: ứng viên nguồn `SL94HyyuLXs`

    IQが低い人の頭の中で起きていること
    ("Những gì xảy ra trong đầu người có IQ thấp")

so với tiêu đề TL3-T7-0001 ĐÃ LÀM

    考えすぎる人の頭の中はこんな世界
    ("Đầu người IQ thấp là một thế giới như thế này")

chỉ đạt điểm chữ 0,485 — xa dưới ngưỡng 0,80 — vì tiếng Nhật đảo trật tự
「IQが低い」(vế "IQ thấp" đứng sau) đối 「低IQ」(vế ấy đứng trước, viết tắt).
`SequenceMatcher` so THEO KÝ TỰ, CÓ THỨ TỰ, nên bản chép gần nguyên văn được
bắt tốt còn bản diễn đạt lại thì không — nhưng CẢ HAI đều là "Đầu người IQ
thấp trông như thế nào", cùng một luận điểm, sản xuất lại thì tốn một lượt vô
ích (vài chục nghìn đồng + nhiều giờ máy, xem `core.trung_tieu_de`).

Sửa bằng cách hạ ngưỡng chữ không ổn — ăn sát trần nhiễu đo được (0,303, xem
`trung_tieu_de.NGUONG_GIONG_TIEU_DE_MAC_DINH`) là rủi ro loại nhầm ứng viên
hợp lệ ở các kênh khác chưa đo hết. Cần một lớp ĐỌC HIỂU, không phải đo ký tự
— và một lượt AI ngắn rẻ hơn nhiều so với một lượt sản xuất hỏng.

═══ CÁCH DÙNG — CHỈ TRƯỚC KHI CHỐT NGUỒN ═══

`core.tu_chay._chon_nguon` gọi `kiem_trung_y` cho ỨNG VIÊN ĐANG ĐỨNG ĐẦU bảng
xếp hạng (sau khi `_uu_tien_co_kho` đã chọn) — không chấm cả bảng, vì mỗi lượt
gọi là một lượt tốn tiền. Trùng thì `_chon_nguon` loại ứng viên đó và thử ứng
viên kế, tối đa `core.tu_chay.SO_LAN_KIEM_TRUNG_Y_TOI_DA` lượt gọi cho MỖI lượt
chọn nguồn (xem tệp đó) — không loại vô hạn.

Không gọi mạng ở TẦNG NÀY (việc đó là của `goi_chat`, do nơi gọi đưa vào —
`None` thì bỏ qua hẳn lớp này, không tự dựng client). Không import Qt.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence, Tuple

from .goi_van_ban import loc_json
from .trung_tieu_de import diem_giong_tieu_de

__all__ = ["SO_UNG_VIEN_GOI_Y_MAC_DINH", "KHUON_HOI_MAC_DINH", "kiem_trung_y"]

#: Số tiêu đề ĐÃ LÀM gửi kèm cho AI — không gửi cả bảng (có thể hàng trăm dòng,
#: tốn token vô ích), chỉ gửi những cái GẦN ỨNG VIÊN NHẤT theo điểm chữ (dùng
#: lại `trung_tieu_de.diem_giong_tieu_de`). Đây KHÔNG phải một ngưỡng trùng —
#: chỉ để RÚT GỌN danh sách: ca cần lớp này bắt là ca CHỮ LỆCH (dưới 0,80) mà
#: vẫn còn đủ gần để đáng nghi (ca IQ ở trên, điểm chữ 0,485 — xa 0,80 nhưng
#: vẫn nằm trong nhóm gần nhất so với hàng chục/hàng trăm đề tài khác hẳn).
SO_UNG_VIEN_GOI_Y_MAC_DINH = 15

#: Khuôn lời nhắc mặc định. Ô: `<<UNG_VIEN>>`, `<<DA_LAM>>`.
KHUON_HOI_MAC_DINH = (
    "Đây là một tiêu đề ỨNG VIÊN cho video mới của một kênh YouTube remake, và danh sách tiêu "
    "đề kênh này ĐÃ LÀM gần đây (đánh số, gần giống chữ với ứng viên nhất trước).\n\n"
    "ỨNG VIÊN:\n<<UNG_VIEN>>\n\n"
    "ĐÃ LÀM:\n<<DA_LAM>>\n\n"
    "Hỏi: ứng viên có CÙNG CHỦ ĐỀ / CÙNG LUẬN ĐIỂM CHÍNH với tiêu đề nào trong danh sách ĐÃ "
    "LÀM không — dù diễn đạt khác, đảo trật tự từ, hay đổi từ đồng nghĩa? Khác GÓC NHÌN rõ "
    "ràng (ví dụ: \"vì sao X xảy ra\" khác \"cách khắc phục X\"; \"người có X\" khác \"người "
    "không có X\") thì KHÔNG tính là trùng.\n"
    "Trả về DUY NHẤT một JSON, không giải thích ngoài JSON:\n"
    "{\"trung\": true hoặc false, \"voi\": \"<tiêu đề đã làm nếu trung=true, để trống nếu "
    "false>\", \"ly_do\": \"một câu ngắn\"}")


def _ung_vien_gan_nhat(ung_vien: str, da_lam: Sequence[Tuple[str, str]],
                       so_luong: int) -> List[Tuple[str, str, float]]:
    """`da_lam` xếp theo điểm giống CHỮ với `ung_vien`, cao nhất trước, lấy
    `so_luong` cái đầu — xem `SO_UNG_VIEN_GOI_Y_MAC_DINH` vì sao rút gọn kiểu
    này thay vì gửi nguyên cả bảng."""
    diem = [(td, mo_ta, diem_giong_tieu_de(ung_vien, td))
            for td, mo_ta in da_lam if (td or "").strip()]
    diem.sort(key=lambda x: x[2], reverse=True)
    return diem[:max(0, so_luong)]


def kiem_trung_y(goi_chat: Optional[Callable[..., str]], ung_vien: str,
                 da_lam: Sequence[Tuple[str, str]], *,
                 so_ung_vien: int = SO_UNG_VIEN_GOI_Y_MAC_DINH,
                 khuon_hoi: str = "", khoa: str = "",
                 ghi: Optional[Callable[[str], None]] = None,
                 ) -> Tuple[bool, str, str]:
    """Hỏi AI: `ung_vien` có TRÙNG Ý (cùng chủ đề/luận điểm) với tiêu đề nào
    kênh ĐÃ LÀM không (`da_lam`, cùng khuôn `[(tiêu đề, mô tả nguồn gốc)]` mà
    `core.trung_tieu_de.doc_tieu_de_da_lam` trả về) — lớp kiểm NGỮ NGHĨA, bổ
    sung cho so chữ (`core.trung_tieu_de`, ngưỡng 0,80) vốn bỏ lọt ca "cùng ý
    khác diễn đạt" (xem docstring đầu tệp).

    Trả `(trùng?, tiêu đề trùng nếu có, lý do)`. KHÔNG BAO GIỜ ném lỗi ra
    ngoài — `goi_chat=None`, `ung_vien`/`da_lam` rỗng, hay lượt gọi hỏng (mạng,
    JSON sai dạng, chọn số lạ) đều trả về `(False, "", "<lý do bỏ qua>")`:
    lớp này chỉ ĐỀ XUẤT LOẠI ứng viên, không bao giờ được chặn cả lượt chọn
    nguồn (xem nơi gọi, `core.tu_chay._chon_nguon`).
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    ung_vien = (ung_vien or "").strip()
    if goi_chat is None:
        return False, "", "(bỏ qua: không có goi_chat — chế độ không cần lớp này)"
    if not ung_vien:
        return False, "", "(bỏ qua: ứng viên rỗng)"
    if not da_lam:
        return False, "", "(bỏ qua: chưa có tiêu đề nào đã làm để so)"

    goi_y = _ung_vien_gan_nhat(ung_vien, da_lam, so_ung_vien)
    if not goi_y:
        return False, "", "(bỏ qua: không rút được ứng viên gần nào để so)"

    danh_sach = "\n".join(
        "{0}. {1}".format(i + 1, td) for i, (td, _mt, _d) in enumerate(goi_y))
    khuon = (khuon_hoi or "").strip() or KHUON_HOI_MAC_DINH
    loi_nhac = khuon.replace("<<UNG_VIEN>>", ung_vien).replace("<<DA_LAM>>", danh_sach)

    try:
        tra = goi_chat(loi_nhac, khoa=khoa)
        ket = loc_json(tra)
        if not isinstance(ket, dict):
            raise ValueError("AI không trả về một JSON object")
        trung = bool(ket.get("trung"))
        voi = str(ket.get("voi") or "").strip()
        ly_do = str(ket.get("ly_do") or "").strip()
    except Exception as loi:  # noqa: BLE001 — hỏng thì bỏ qua lớp này, không chặn chọn nguồn
        noi("  (kiểm trùng ý hỏng: {0} — bỏ qua lớp này).".format(str(loi)[:120]))
        return False, "", "(lỗi: {0})".format(str(loi)[:120])

    return trung, voi, ly_do
