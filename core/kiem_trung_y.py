"""Việc 5b (29/09/2026) — LỚP KIỂM TRÙNG Ý BẰNG LLM, bổ sung cho so CHỮ của
`core/trung_tieu_de.py`.

═══ VÌ SAO CẦN THÊM LỚP NÀY ═══

`core.trung_tieu_de` so hai tiêu đề bằng `difflib.SequenceMatcher` (ngưỡng
0,80, xác nhận trên dữ liệu thật — xem docstring đầu tệp đó) — bắt tốt ca chép
GẦN NGUYÊN VĂN, nhưng bỏ lọt ca CÙNG Ý, KHÁC DIỄN ĐẠT. Ca thật đo được
28→29/09/2026: ứng viên nguồn `vidGia1428b`

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

from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from .goi_van_ban import loc_json
from .trung_tieu_de import diem_giong_tieu_de

__all__ = ["SO_UNG_VIEN_GOI_Y_MAC_DINH", "KHUON_HOI_MAC_DINH", "kiem_trung_y", "khoa_video_thang",
           "la_cua_video_thang", "bo_video_thang"]

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


# ── biến thể của video THẮNG (12/10/2026) ───────────────────────────────────
#
# `workspace/chan-doan/nao-vong-hoc-2026-10-12.md` mục 2: lớp này loại cả nguồn GẦN GIỐNG video THẮNG của chính kênh —
# triệt tiêu đúng luật số 1 của TL4 ("làm tiếp cụm vừa thắng": cùng chủ ngữ hẹp, góc mới; V10 thắng rồi V11·V12 cùng
# cụm cũng thắng). Giờ: tiêu đề ĐÃ LÀM thuộc video THẮNG (thước chung `core.thuoc_thang`) hoặc đang NÓNG của CHÍNH
# kênh được bỏ khỏi danh sách so trùng ý. Vẫn chặn: trùng thứ kênh đã làm/đã lên kế hoạch mà KHÔNG thắng, mọi thứ của
# kênh anh em (mô tả mang tiền tố "<kênh>: "), cùng link nguồn (`da_lam`/khoá nhóm) và tiêu đề gần nguyên văn (so chữ
# ≥ 0,80 ở `NguCanh.loc` — chép lại đúng góc cũ không phải "góc mới").

#: Bộ nhớ trong tiến trình: `(goc, kenh) → (lúc, (khoá, tiêu đề))` — video_cua_kenh đọc cả chi-so, không đọc lại mỗi lượt.
_NHO_THANG: Dict[Tuple[str, str], Tuple[float, Tuple[Set[str], Set[str]]]] = {}
NHO_THANG_GIAY = 600.0


def khoa_video_thang(goc: str, ma_kenh: str) -> Tuple[Set[str], Set[str]]:
    """`(khoá mô tả, tiêu đề)` của các video THẮNG / đang nóng của CHÍNH kênh: khoá = mô tả mà
    `trung_tieu_de.doc_tieu_de_da_lam` gắn cho chúng ("đã đăng <mã video>", "kế hoạch <mã gói>", tiền tố
    "lượt <kênh>/<lượt> ("); tiêu đề = tiêu đề kênh đã đăng + tiêu đề hồ sơ. Đọc đĩa, có nhớ `NHO_THANG_GIAY`.
    Hỏng → hai tập rỗng (= hành vi cũ: không miễn gì)."""
    import time as _time  # noqa: PLC0415

    nho = _NHO_THANG.get((goc, ma_kenh))
    if nho is not None and _time.time() - nho[0] < NHO_THANG_GIAY:
        return nho[1]
    khoa: Set[str] = set()
    tieu_de: Set[str] = set()
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        ch, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
        thang = [v for v in v7.video_cua_kenh(goc, ma_kenh, ch) if getattr(v, "thang", False)]
        vid = {v.ma for v in thang}
        tieu_de |= {str(v.tieu_de).strip() for v in thang if str(v.tieu_de or "").strip()}
        khoa |= {"đã đăng " + m for m in vid}
        if vid:
            from .chien_luoc import ket_qua  # noqa: PLC0415

            for ma_goi, hs in ket_qua.ho_so_theo_goi(goc, ma_kenh).items():
                if str(hs.get("video_id") or "") not in vid:
                    continue
                khoa.add("kế hoạch " + ma_goi)
                if ma_goi.startswith(ma_kenh + "-"):
                    khoa.add("lượt {0}/{1} (".format(ma_kenh, ma_goi[len(ma_kenh) + 1:]))
                if str(hs.get("tieu_de") or "").strip():
                    tieu_de.add(str(hs["tieu_de"]).strip())
    except Exception:  # noqa: BLE001 — không đọc được thì không miễn (an toàn: như trước)
        khoa, tieu_de = set(), set()
    _NHO_THANG[(goc, ma_kenh)] = (_time.time(), (khoa, tieu_de))
    return khoa, tieu_de


def la_cua_video_thang(tieu_de: str, mo_ta: str, khoa: Tuple[Set[str], Set[str]], ma_kenh: str = "") -> bool:
    """Một dòng ĐÃ LÀM `(tiêu đề, mô tả)` có thuộc video THẮNG của CHÍNH kênh không. Dòng của kênh anh em (mô tả có
    tiền tố "<kênh>: " hoặc "<kênh khác> đã đăng") không bao giờ được miễn."""
    k_mo_ta, k_td = khoa
    mo_ta = str(mo_ta or "")
    if any(mo_ta == k or (k.endswith("(") and mo_ta.startswith(k)) for k in k_mo_ta):
        return True
    if str(tieu_de or "").strip() not in k_td:
        return False
    dau = mo_ta.split(": ", 1)[0] if ": " in mo_ta else ""
    if dau and " " not in dau:  # "TL2-T7: lượt …" — của kênh anh em
        return False
    if " đã đăng" in mo_ta and ma_kenh and not mo_ta.startswith(ma_kenh + " đã đăng"):
        return False
    return True


def bo_video_thang(da_lam: Sequence[Tuple[str, str]], khoa: Tuple[Set[str], Set[str]],
                   ma_kenh: str = "") -> Tuple[List[Tuple[str, str]], int]:
    """`(danh sách đã làm BỎ các dòng của video thắng của chính kênh, số dòng đã bỏ)` — xem đầu mục."""
    if not (khoa[0] or khoa[1]):
        return list(da_lam), 0
    giu = [(t, m) for t, m in da_lam if not la_cua_video_thang(t, m, khoa, ma_kenh)]
    return giu, len(da_lam) - len(giu)


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
