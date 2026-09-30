"""**Content nào đã remake rồi — theo TIÊU ĐỀ**, bổ sung cho chống trùng theo
MÃ VIDEO (`core/da_lam.py`, `core/nhom_kenh.video_da_lam_ca_nhom`).

═══ VÌ SAO CẦN THÊM LỚP NÀY (chẩn đoán 27→28/09/2026) ═══

`da_lam.doc_ma_da_lam`/`nhom_kenh.video_da_lam_ca_nhom` nối hai đầu bằng MÃ
VIDEO NGUỒN — đúng cho ca "cùng một video, remake lại". Nhưng có một ca khác
hẳn: HAI ĐỐI THỦ KHÁC KÊNH chép cùng một chủ đề (đúng dạng quen ở tiếng Nhật —
"đối thủ giật lại tiêu đề đang hot của người khác"), ra hai MÃ VIDEO KHÁC
NHAU nhưng cùng một tiêu đề gần như nguyên văn. Kênh TL1-T7 sản xuất
TL1-T7-0006 (27/09/2026, nguồn `8nPciHbf194`) rồi TL1-T7-0007 (28/09/2026,
nguồn `OmuR0oP6CYc`) — hai mã khác hẳn — nhưng CÙNG một câu tiêu đề tiếng
Nhật (chỉ đối thủ nguồn khác nhau, kênh mình vẫn ra đúng một nội dung hai lần).
Lọc theo mã không bắt được ca này.

═══ NỐI HAI ĐẦU BẰNG TIÊU ĐỀ ĐÃ CHUẨN HOÁ, SO MỜ ═══

Không thể đòi khớp tuyệt đối: nhãn chuyên mục đối thủ tự gắn ở đầu câu
("【心理学】" đối "【雑学】"), dấu câu, khoảng trắng toàn độ rộng, full/half-width
đều lệch nhau dù CÙNG một nội dung. `chuan_hoa_tieu_de_so_khop` chuẩn hoá
(mượn `core.tu_nhan_da_dang.chuan_hoa_tieu_de` — NFKC, hạ thường, gộp dấu câu)
rồi cắt thêm nhãn kiểu 【…】/[…] Ở ĐẦU câu, và `diem_giong_tieu_de` so bằng
`difflib.SequenceMatcher` (thư viện chuẩn — cùng công cụ `tu_nhan_da_dang`
dùng để tự nhận video đã đăng, không thêm phụ thuộc mới).

═══ NGƯỠNG 0,80 — ĐO TRÊN DỮ LIỆU THẬT, KHÔNG ĐOÁN (28/09/2026) ═══

Đề xuất ban đầu 0,80 (không đoán bừa) — chạy khô trên TOÀN BỘ 5 kênh thật
(`TL1`…`TL5`, 107 cặp "khác đề" thật trong lịch sử sản xuất) xác nhận đúng
con số này AN TOÀN: trần nhiễu đo được (điểm giống cao nhất giữa hai đề THẬT
SỰ khác nhau) chỉ 0,303 (TL3-T7 0001 "người IQ thấp" đối 0002 "người IQ cao"
— hai đề GẦN NHAU nhất mà vẫn là hai video khác nhau). Bốn ứng viên trùng đề
THẬT bắt được ở TL1-T7 (nhóm 0006/0007, "8nPciHbf194"/"OmuR0oP6CYc") nằm ở
dải 0,83–0,94 — CÁCH trần nhiễu ít nhất 0,52, dư sức giữ ngưỡng 0,80 mà không
cần hạ thấp hơn.

(Trước bản đo này, `chuan_hoa_tieu_de_so_khop` có một lỗi thứ tự — gọi
`chuan_hoa_tieu_de` TRƯỚC khi cắt nhãn 【…】, mà `chuan_hoa_tieu_de` đã đổi
luôn dấu 【 】 thành khoảng trắng nên `_RE_NHAN_DAU` không còn gì để nhận diện,
nhãn không hề bị cắt — vá bằng cách cắt nhãn trên chuỗi THÔ trước, xem
`chuan_hoa_tieu_de_so_khop`. Bản đo ĐẦU (còn lỗi) từng cho điểm thấp hơn ở ca
sát biên nhất, 0,7945 — sau khi vá, ca đó lên 0,8286, và ngưỡng giữ nguyên
0,80 như đề xuất ban đầu thay vì phải hạ xuống 0,75.)

Ca CHƯA bắt được, đã BÁO LẠI (không cố hạ ngưỡng thêm): `SL94HyyuLXs`
"IQが低い人の頭の中で起きていること" so với TL3-T7-0001 "低IQの人の頭の中
はこんな世界" chỉ đạt 0,485 — cùng kênh, cùng khái niệm "IQ thấp" nhưng đảo
trật tự từ tiếng Nhật ("IQが低い" đối "低IQ") khiến `SequenceMatcher` — so
theo KÝ TỰ, CÓ THỨ TỰ — chấm thấp. Vẫn còn khoảng cách an toàn tới trần nhiễu
0,303, nhưng hạ ngưỡng xuống mức bắt được ca này (~0,45) sẽ ăn sát trần nhiễu
tới mức rủi ro cao cho các kênh khác chưa đo hết. Muốn bắt đúng ca IQ này cần
tách TỪ (tokeniser tiếng Nhật thật, vd MeCab/fugashi) rồi so tập từ khoá sau
khi bỏ trợ từ — ngoài phạm vi bản vá này (thêm phụ thuộc mới, cần thẩm định
riêng). Ứng viên dạng này vẫn lọt qua — CHỦ DỰ ÁN cần tự soát tay khi thấy đề
tài gần giống trong bảng đề xuất.

Ở đây mục tiêu là LOẠI BỚT ứng viên đề xuất — bỏ sót một trùng còn hại nhiều
(tốn cả lượt sản xuất, cỡ vài chục nghìn đồng + nhiều giờ máy) so với báo
nhầm một ứng viên hợp lệ bị loại (chỉ mất đúng MỘT ứng viên trong cả bảng,
ứng viên khác vẫn còn) — nhưng vẫn giữ ngưỡng có margin rộng với trần nhiễu
đo được thay vì ăn sát mép, vì dữ liệu ngoài 5 kênh đã đo là CHƯA BIẾT.

═══ BA NGUỒN "TIÊU ĐỀ ĐÃ LÀM" ═══

1. `PROJECTS/AUTO/<kênh>[-vN]/<lượt>/0-doi-thu.txt` — dòng `TITLE:` là tiêu
   đề của VIDEO NGUỒN (đối thủ) đã remake.
2. `PROJECTS/AUTO/<kênh>[-vN]/<lượt>/1-tieu-de.txt` — dòng `TITLE:` là tiêu
   đề TOOL ĐÃ ĐẶT cho video của mình (khác tiêu đề nguồn, nhưng cùng nội dung).
3. `CHANNEL/<kênh>/ke-hoach-dang/ke-hoach.csv`, cột "Tiêu đề" — nội dung ĐÃ
   BÀN GIAO ra kế hoạch, bất kể đã đăng/đã bị đánh dấu Bỏ hay chưa: một lượt
   bị đánh Bỏ vì trùng đề vẫn PHẢI tiếp tục chặn các ứng viên trùng đề khác.
4. Video ĐÃ CÔNG KHAI trên kênh (`core.tu_nhan_da_dang.doc_video_cong_khai_tren_kenh`,
   đọc lại `chi-so/kenh/` đã quét — 0 đồng) — bắt cả ca đăng tay ngoài luồng.

Không gọi mạng, không import Qt: chỉ đọc tệp văn bản/CSV/JSON đã có sẵn trên đĩa.
"""

from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .da_lam import TEP_NGUON, THU_MUC_AUTO
from .tu_nhan_da_dang import chuan_hoa_tieu_de

__all__ = [
    "NGUONG_GIONG_TIEU_DE_MAC_DINH", "TEP_TIEU_DE_DAT",
    "chuan_hoa_tieu_de_so_khop", "diem_giong_tieu_de", "trung_tieu_de",
    "doc_tieu_de_da_lam", "tim_tieu_de_trung",
]

#: Tỉ lệ giống tối thiểu (0..1, `difflib.SequenceMatcher.ratio`, sau chuẩn
#: hoá) để coi hai tiêu đề là "cùng một nội dung" — 0,80, xác nhận AN TOÀN
#: trên dữ liệu THẬT (xem "NGƯỠNG 0,80" ở docstring đầu tệp), không phải
#: đoán. Cấu hình được qua tham số `nguong` của từng hàm dưới, không phải
#: hằng số cứng.
NGUONG_GIONG_TIEU_DE_MAC_DINH = 0.80

#: Tệp tiêu đề TOOL đã đặt cho video của mình, trong mỗi thư mục lượt AUTO —
#: cạnh `TEP_NGUON` (`0-doi-thu.txt`, tiêu đề của NGUỒN đối thủ).
TEP_TIEU_DE_DAT = "1-tieu-de.txt"

_RE_TITLE_LINE = re.compile(r"^TITLE:\s*(.+?)\s*$", re.MULTILINE)

#: Nhãn chuyên mục đối thủ tự gắn Ở ĐẦU tiêu đề — 【…】 kiểu Nhật hay gặp nhất,
#: và [...] kiểu La-tinh. Hai đối thủ remake cùng chủ đề gần như luôn đổi nhãn
#: khác nhau ("【心理学】" đối "【雑学】") dù nội dung giống hệt — giữ nhãn lại
#: trong chuỗi so khớp làm giảm điểm giống một cách giả tạo, đúng ca bắt được
#: 27→28/09/2026 (TL1-T7-0006 dùng "【雑学】", cả hai nguồn đều "【心理学】").
_RE_NHAN_DAU = re.compile(r"^(?:[【\[][^】\]]{0,40}[】\]]\s*)+")
#: Nhãn 【…】 Ở CUỐI câu (「…の心理【グレーな心理学】」) — xem `chuan_hoa_tieu_de_so_khop`.
_RE_NHAN_CUOI = re.compile(r"(?:\s*【[^】]{0,40}】)+\s*$")


def chuan_hoa_tieu_de_so_khop(tieu_de: str) -> str:
    """Bỏ mọi nhãn 【…】/[…] Ở ĐẦU câu (xem `_RE_NHAN_DAU`) RỒI MỚI chuẩn hoá
    (`chuan_hoa_tieu_de`: NFKC, hạ thường, gộp dấu câu).

    ═══ THỨ TỰ BẮT BUỘC — CẮT NHÃN TRƯỚC (28/09/2026) ═══

    `chuan_hoa_tieu_de` đã đổi CẢ 【 】 (dấu câu CJK) thành khoảng trắng — chạy
    nó trước thì `_RE_NHAN_DAU` không còn dấu ngoặc nào để nhận diện "đây là
    một nhãn" nữa (chữ bên trong nhãn lẫn luôn vào câu, không cắt được). Cắt
    nhãn trên chuỗi THÔ (còn nguyên dấu ngoặc) rồi mới chuẩn hoá phần còn lại.
    """
    tho = str(tieu_de or "")
    truoc = None
    while truoc != tho:
        truoc = tho
        tho = _RE_NHAN_DAU.sub("", tho).strip()
    # 30/09/2026 — nhãn Ở CUỐI câu cũng là nhãn kênh: 「昔より物欲が減った人の心理【グレーな心理学】」 và
    # 「【雑学】昔より物欲が減った人の心理」 cùng MỘT nội dung mà chỉ giống 0,76 (< 0,80) vì nhãn cuối —
    # nguồn TL4 đã làm (V13, trượt) lọt lên hạng 6 bảng TL1. Cắt nhãn cuối, chừa lại nếu cắt xong rỗng.
    cuoi = _RE_NHAN_CUOI.sub("", tho).strip()
    if cuoi:
        tho = cuoi
    return chuan_hoa_tieu_de(tho)


def diem_giong_tieu_de(a: str, b: str) -> float:
    """Tỉ lệ giống (0..1) giữa hai tiêu đề THÔ — tự chuẩn hoá trước khi so."""
    ca, cb = chuan_hoa_tieu_de_so_khop(a), chuan_hoa_tieu_de_so_khop(b)
    if not ca or not cb:
        return 0.0
    return SequenceMatcher(None, ca, cb).ratio()


def trung_tieu_de(a: str, b: str, nguong: float = NGUONG_GIONG_TIEU_DE_MAC_DINH) -> bool:
    """Hai tiêu đề có nên coi là CÙNG một nội dung không (điểm giống ≥ `nguong`)."""
    return diem_giong_tieu_de(a, b) >= nguong


def _doc_title_tu_tep(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            chu = tep.read()
    except OSError:
        return ""
    tim = _RE_TITLE_LINE.search(chu)
    return tim.group(1).strip() if tim else ""


def doc_tieu_de_da_lam(goc: str, kenh: str) -> List[Tuple[str, str]]:
    """`[(tiêu đề THÔ, mô tả nguồn gốc cho log/người đọc)]` — mọi tiêu đề kênh
    này ĐÃ LÀM, gộp bốn nguồn ở docstring đầu tệp. Trùng lặp giữa các nguồn
    không sao — nơi gọi chỉ cần MỘT khớp là đủ để loại một ứng viên.

    Thư mục/tệp thiếu đều bỏ qua êm — kênh mới, chưa có kế hoạch, chưa quét
    Studio lần nào đều là trạng thái bình thường, không phải lỗi.
    """
    ra: List[Tuple[str, str]] = []

    # 1) + 2) mọi lượt AUTO (kể cả bản thử `<kênh>-v2`, `-v3` — cùng luật với
    # `da_lam.doc_ma_da_lam`).
    auto = os.path.join(goc, THU_MUC_AUTO)
    try:
        anh_em = sorted(d for d in os.listdir(auto)
                        if d == kenh or re.fullmatch(re.escape(kenh) + r"-v\d+", d))
    except OSError:
        anh_em = []
    for thu in anh_em:
        thu_muc = os.path.join(auto, thu)
        tien_to = "" if thu == kenh else thu[len(kenh) + 1:] + "/"
        try:
            ten_luot = sorted(os.listdir(thu_muc))
        except OSError:
            continue
        for ten in ten_luot:
            duong_luot = os.path.join(thu_muc, ten)
            if not os.path.isdir(duong_luot):
                continue
            mo_ta_luot = "{0}/{1}{2}".format(kenh, tien_to, ten)
            tieu_de_nguon = _doc_title_tu_tep(os.path.join(duong_luot, TEP_NGUON))
            if tieu_de_nguon:
                ra.append((tieu_de_nguon, "lượt {0} (tiêu đề nguồn)".format(mo_ta_luot)))
            tieu_de_dat = _doc_title_tu_tep(os.path.join(duong_luot, TEP_TIEU_DE_DAT))
            if tieu_de_dat:
                ra.append((tieu_de_dat, "lượt {0} (tiêu đề đã đặt)".format(mo_ta_luot)))

    # 3) kế hoạch đăng — mọi dòng, bất kể trạng thái (xem docstring).
    try:
        from . import ke_hoach_dang  # noqa: PLC0415 — tránh vòng nhập

        cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
        if "Tiêu đề" in cot:
            i_td = cot.index("Tiêu đề")
            i_ma = cot.index("Mã gói") if "Mã gói" in cot else -1
            for dong in hang:
                if i_td >= len(dong):
                    continue
                tieu_de = str(dong[i_td]).strip()
                if not tieu_de:
                    continue
                ma_goi = str(dong[i_ma]).strip() if 0 <= i_ma < len(dong) else ""
                ra.append((tieu_de, "kế hoạch {0}".format(ma_goi or kenh)))
    except Exception:  # noqa: BLE001 — kế hoạch hỏng không được chặn chống trùng
        pass

    # 4) video đã công khai trên kênh (0 đồng, đọc lại số liệu Studio đã quét).
    try:
        from . import tu_nhan_da_dang

        for video_id, thong_tin in (tu_nhan_da_dang.doc_video_cong_khai_tren_kenh(goc, kenh)
                                    or {}).items():
            tieu_de = str((thong_tin or {}).get("tieu_de") or "").strip()
            if tieu_de:
                ra.append((tieu_de, "đã đăng {0}".format(video_id)))
    except Exception:  # noqa: BLE001 — số liệu Studio hỏng không được chặn chống trùng
        pass

    return ra


def tim_tieu_de_trung(tieu_de: str, da_lam: Sequence[Tuple[str, str]],
                      nguong: float = NGUONG_GIONG_TIEU_DE_MAC_DINH
                      ) -> Optional[Tuple[str, str, float]]:
    """Tiêu đề `tieu_de` có trùng cái nào trong `da_lam` không (điểm ≥ `nguong`).

    Trả `(tiêu đề đã làm, mô tả nguồn gốc, điểm giống)` của khớp ĐIỂM CAO NHẤT
    nếu có, `None` nếu không ứng viên nào đạt ngưỡng. Quét hết `da_lam` (không
    dừng ở khớp đầu tiên) để log luôn chỉ ra bản khớp RÕ NHẤT, dễ đối chiếu
    tay hơn một khớp bất kỳ vượt ngưỡng.
    """
    if not tieu_de or not da_lam:
        return None
    tot_nhat: Optional[Tuple[str, str, float]] = None
    for tieu_de_cu, mo_ta in da_lam:
        diem = diem_giong_tieu_de(tieu_de, tieu_de_cu)
        if diem >= nguong and (tot_nhat is None or diem > tot_nhat[2]):
            tot_nhat = (tieu_de_cu, mo_ta, diem)
    return tot_nhat
