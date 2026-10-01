"""**Chấm và CHỐT ứng viên đối thủ** — không cần người ngồi bấm từng kênh, không gọi AI.

Chủ dự án, 05/09/2026: *"mục đích chỉ là có 1 danh bạ đối thủ đúng chủ đề để từ đối thủ đó tìm
ra được các content để khai thác… hoàn thiện tool để về sau 1 nút là có đúng đối thủ".*

Trước đó, đường từ hộp thư vào danh bạ là cửa sổ "Lọc và chấm": khách mở, chờ tool đo từng
kênh, rồi tick từng dòng. Lượt cào trang chủ máy ảo đầu tiên đổ 25 kênh vào hộp thư một lúc —
và 44/72 kênh phải bỏ, phần lớn vì lý do MÁY đo được: 雑学/要約, view trung vị dưới 1.000,
video 45–75 phút, hay 76–96% tiêu đề gắn 50代/60代/老後. Không lý do nào cần người.

═══ MỘT THƯỚC, BỐN CỬA ═══

1. **Cửa máy** có sẵn của tool (`loc_doi_thu.loc_may`): đúng tiếng · cùng khổ với kênh mình ·
   view trung vị ≥ 1.000. Trượt là bỏ, không cần nhìn thêm.
2. **Cổng thể loại** (`trang_chu.kenh_bi_loai`): 雑学 / 要約 / tóm sách / 2ch… — tiêu đề có thể
   "đúng tâm lý" mà kênh vẫn không phải nguồn remake.
3. **Thẻ già**: % tiêu đề (25 mới nhất) gắn 50代/60代/老後/定年… (`phan_tuyen.DAU_MOC_TUOI`).
   Kênh TL4-T7 đang bị YouTube xếp vào tệp 55+; lấy nguồn từ kênh già là đổ thêm dầu. ≥ 30% → bỏ.
4. **Khớp tuyến đang đánh**: % tiêu đề dính từ khoá của tuyến (mặc định: tuyến "lệch nhịp số
   đông" — một mình, ít bạn, SNS, không hứng thú thể thao, ở nhà…). ≥ 8%, HOẶC tên kênh tự nói
   nó là kênh tâm lý (心理/脳科学/こころ) → theo dõi. Khớp 0% mà tên cũng không nói → bỏ.
   Ở giữa (self-help chung, khớp 1–7%) → **để lại hộp thư cho người quyết** — máy không đoán.

Kênh > 200.000 subs là kênh tham khảo, không phải đối thủ: nó ăn view nhờ subs sẵn có.

═══ CỬA THỨ NĂM — AI, CHỈ CHO KÊNH ĐÃ QUA BỐN CỬA MÁY ═══

Chủ dự án, 05/09/2026 (lần hai): *"tool dùng api và nhiều cách để trước khi đưa đối thủ vào là
chắc chắn đúng đối thủ, đúng chủ đề tâm lý"*. Có `client` là hỏi `loc_doi_thu.hoi_ai_kenh` (cùng
đề bài với cửa sổ "Lọc và chấm" cũ) cho kênh máy định THEO DÕI hoặc định để lại hộp thư:
`doi_thu` → theo dõi (ghi luôn tuyến AI thấy) · `gan`/`khong` → bỏ, ghi lý do AI. Kênh trượt cửa
máy KHÔNG hỏi — đó là chỗ tiết kiệm chính, y như cửa sổ cũ. AI hỏng thì giữ quyết định máy.

Mọi quyết định ghi vào cột "Ghi chú" của danh bạ kèm số đo, để người mở sổ thấy VÌ SAO — và
lật lại được bằng cách đổi "Trạng thái". Đo bằng yt-dlp, mỗi kênh một lần gọi.

═══ THEO NGHĨA: TỪ KHOÁ KHÔNG ĐƯỢC TỰ "BỎ" KÊNH NỮA (29/09/2026) ═══

Chủ dự án: *"Lọc theo từ khoá là SAI — phải theo Ý NGHĨA."* Bản cũ "bỏ" (ẩn khỏi thị trường)
không hỏi AI ba loại kênh chỉ bằng chữ: tên có 雑学/恋愛/漫画…, kênh lớn mà tên không nói
"tâm lý", kênh 0% tiêu đề khớp từ khoá tuyến. Insight #8 (29/09): 4/15 kênh Studio liệt là "đối
thủ cùng khán giả" của TL4 tự gọi mình là 雑学 — đúng loại bản cũ bỏ thẳng. Nay, khi có `client`:

    bỏ HIỂN NHIÊN (không hỏi AI)   kênh chết · sai tiếng · kênh tóm sách/tin tức/nhạc/game rõ ràng
                                   (`trang_chu.kenh_lech_hien_nhien`)
    bỏ do TỪ KHOÁ                  → hỏi AI (đọc 25 tiêu đề + mô tả ngách); AI nói đối thủ thì
                                     VÀO, AI nói gần/không thì bỏ; AI lỗi → giữ "bỏ" (đường lùi)
    theo dõi / gần ngách           → hỏi AI như trước

`xet_lai_bo_tu_khoa` chấm lại (tối đa vài kênh mỗi lượt) những kênh bản cũ đã "bỏ" bằng từ khoá
— nhận ra qua Ghi chú "không phải kênh tâm lý: …" (dấu hai chấm = máy; AI ghi "— AI:"). Không có
`client`: y như cũ.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from . import loc_doi_thu as loc
from .ho_so_ngach import doc_ngach
from .phan_tuyen import DAU_MOC_TUOI
from .trang_chu import kenh_bi_loai

try:
    from .trang_chu import kenh_lech_hien_nhien
except ImportError:  # tiến trình đang chạy đã nạp `trang_chu` bản cũ (lúc thay tệp) — coi như không hiển nhiên
    def kenh_lech_hien_nhien(ten_kenh: str = "", link_kenh: str = "", **_bo_tu) -> bool:  # type: ignore[misc]
        return False

__all__ = ["UngVien", "TU_KHOP_LECH_NHIP", "TU_GO_TOI", "TEN_KENH_TAM_LY", "GHI_CHU_BAN_DUA", "kenh_ban_dua",
           "do_ung_vien", "quyet", "chot", "bo_hien_nhien", "xet_lai_bo_tu_khoa", "DAU_BO_TU_KHOA",
           "SO_XET_LAI_MOI_LUOT"]

#: Ghi chú của một quyết định "bỏ" do LUẬT TỪ KHOÁ (không phải AI) — `quyet` viết đúng tiền tố
#: này (dấu hai chấm); `_ghep_ai` viết "không phải kênh tâm lý — AI: …". Dùng để tìm kênh bản cũ
#: bỏ bằng chữ mà xét lại theo nghĩa (`xet_lai_bo_tu_khoa`).
DAU_BO_TU_KHOA = "không phải kênh tâm lý:"
#: Mỗi lượt `chot` có ví xét lại tối đa ngần này kênh bỏ-bằng-từ-khoá cũ (lượt sau gánh tiếp).
SO_XET_LAI_MOI_LUOT = 8

#: Từ khoá tuyến "lệch nhịp số đông" (từ cột "Từ khoá nhận biết" của tuyen.csv, chuyển sang
#: chữ Nhật thường gặp trên tiêu đề). Kênh khác tuyến truyền `tu_khop` riêng vào `chot`.
TU_KHOP_LECH_NHIP = re.compile(
    "一人|ひとり|独り|ぼっち|孤独|友達|友人|群れ|人付き合い|人間関係が苦手|SNS|付き合わない|合わせない|"
    "内向|無趣味|家から出ない|外に出ない|飲み会|雑談|一人でいる|ソロ|人と関わらない|人混み|連絡しない|"
    "誘われない|集まり|静かな人|話さない|口数が少ない|群れない|独り言|スポーツに興味|家にいたい|家が好き|家を愛")
#: Khuôn "gỡ tội" — dấu hiệu tiêu đề hứa nhẹ lòng thay vì hứa việc làm.
TU_GO_TOI = re.compile("実は|本当は|本当の|強い|賢い|才能|隠された|特徴|なぜ|理由|優秀|すごい|凄い|意外")
#: Tên kênh tự khai là kênh tâm lý — đủ để theo dõi dù 25 tiêu đề mới nhất chưa dính từ khoá tuyến.
TEN_KENH_TAM_LY = ("心理", "脳科学", "こころ", "心の", "ココロ", "メンタル", "才能")


def regex_tu(tu: Sequence[str]) -> "re.Pattern[str]":
    """Danh sách từ (ngach.yaml) → regex "a|b|c" khớp NGUYÊN VĂN từng từ. Ba regex trên đều viết
    đúng dạng này, nên nhóm tam-ly-nhat ra đúng cùng một mẫu (test_ngach_tam_ly_khop_ma)."""
    return re.compile("|".join(re.escape(t) for t in tu if t))


def _tu_ngach(goc: str, kenh: str) -> Dict[str, Any]:
    """Bộ từ của hồ sơ ngách cho một lượt chốt (Đợt 4, A5). Không hồ sơ → hằng cũ, hành vi y hệt.

    Ngách khác chưa khai `ten_kenh_dung_ngach`/`tu_khop_nguon` thì lấy `tu_manh`(+`tu_yeu`) của
    chính ngách đó — cùng vai "từ tự nhận đúng ngách" — chứ không rơi về chữ Nhật tâm lý."""
    try:
        hs = doc_ngach(goc, kenh)
    except Exception:  # noqa: BLE001 — hồ sơ hỏng không được giết lượt chốt
        hs = None
    if hs is None or not hs.co():
        return {}
    ra: Dict[str, Any] = {
        "dau_moc_tuoi": list(hs.tu_tuoi) or list(DAU_MOC_TUOI),
        "ten_kenh_tam_ly": list(hs.ten_kenh_dung_ngach) or list(hs.tu_manh) or list(TEN_KENH_TAM_LY),
        "tu_loai_tru": list(hs.tu_loai_tru), "ten_kenh_loai_tru": list(hs.ten_kenh_loai_tru),
        "handle_loai_tru": list(hs.handle_loai_tru),
        "tu_kenh_hien_nhien": list(hs.tu_kenh_hien_nhien), "handle_hien_nhien": list(hs.handle_hien_nhien),
    }
    khop = list(hs.tu_khop_nguon) or (list(hs.tu_manh) + list(hs.tu_yeu))
    if khop:
        ra["tu_khop"] = regex_tu(khop)
    if hs.tu_go_toi:
        ra["tu_go_toi"] = regex_tu(hs.tu_go_toi)
    return ra

#: Chuỗi trong lỗi yt-dlp nói kênh đã chết/ẩn — bỏ luôn, không giữ trong hộp thư thử lại mãi.
#: Chỉ những câu yt-dlp nói về CHÍNH kênh — "503 Service Unavailable" là lỗi tạm của máy chủ, không tính.
_DAU_HIEU_KENH_CHET = ("does not exist", "terminated", "has been removed", "this channel", "no longer available",
                       "is private", "404", "không tồn tại")

#: Ghi chú của kênh khách đưa tay — máy không chấm, không hỏi AI, luôn quét.
GHI_CHU_BAN_DUA = "bạn đưa — luôn quét"

SO_TIEU_DE_DO = 40          # lấy ngần này video mới nhất để đo (một lời gọi yt-dlp)
NGUONG_GIA = 30             # % tiêu đề gắn thẻ tuổi → bỏ
NGUONG_KHOP = 8             # % tiêu đề khớp tuyến → theo dõi
SUBS_TOI_DA = 200_000       # trên mức này là kênh tham khảo


@dataclass
class UngVien:
    """Số đo một kênh ứng viên — đủ để quyết và đủ để giải thích."""

    ten: str = ""
    link: str = ""
    subs: int = -1
    so_video: int = 0
    dai_tv: str = ""
    view_tv: int = 0
    dinh_tren_subs: float = 0.0
    pct_gia: int = 0
    pct_khop: int = 0
    pct_khop_go_toi: int = 0
    the_loai_loai: bool = False
    cua_may_dat: bool = True
    ly_do_may: str = ""
    loi: str = ""
    tieu_de: List[str] = field(default_factory=list)
    #: Số đo bậc 1 nguyên gốc — `hoi_ai_kenh` đọc từ đây.
    so_do: Optional[loc.SoDo] = None
    #: Sức sống (30/09/2026, `kiem_ngach_doi_thu.SoKenh`) — ngày đăng video dài mới nhất, trung vị
    #: view gần, video nổi… cho cửa "ngừng hoạt động / quá yếu".
    suc_song: Optional[Any] = None


def do_ung_vien(link: str, *, lang: str = "", phut_muc_tieu: float = 0.0,
                lay_kenh: Optional[Callable[..., object]] = None,
                tu_khop: "re.Pattern[str]" = TU_KHOP_LECH_NHIP,
                cancel: Optional[threading.Event] = None,
                bo_qua_zatsugaku: bool = False,
                dau_moc_tuoi: Sequence[str] = DAU_MOC_TUOI,
                tu_go_toi: "re.Pattern[str]" = TU_GO_TOI,
                tu_loai_tru: Sequence[str] = (),
                ten_kenh_loai_tru: Sequence[str] = (),
                handle_loai_tru: Sequence[str] = ()) -> UngVien:
    """Một kênh → một `UngVien`. Lỗi mạng/kênh chết ghi vào `loi`, không ném.

    `bo_qua_zatsugaku=True` — xem `trang_chu.kenh_bi_loai`: kênh đang đánh TỆP 3 (người tò
    mò) thì 雑学 không còn là dấu loại ở cổng thể loại — kênh chuyên nhất của tệp ấy tự gọi
    mình là 雑学. Mặc định `False`: hành vi mọi nơi gọi cũ không đổi.

    `dau_moc_tuoi`/`tu_go_toi`/`tu_loai_tru`/`ten_kenh_loai_tru`/`handle_loai_tru` — 30/09/2026,
    Đợt 4 (A5): mặc định là hằng tiếng Nhật (ba bộ rỗng để `kenh_bi_loai` tự lùi về hằng của nó);
    `_chot` truyền bộ của hồ sơ ngách (`_tu_ngach`).
    """
    if lay_kenh is None:
        from .youtube import fetch_channel  # noqa: PLC0415 — yt-dlp chỉ nạp khi cần

        lay_kenh = fetch_channel
    try:
        ch = lay_kenh(link, max_videos=SO_TIEU_DE_DO, lang=lang, cancel=cancel)
    except Exception as loi:  # noqa: BLE001 — một kênh hỏng không được giết cả lượt
        return UngVien(link=link, loi=str(loi)[:160])
    so = loc.do_kenh(ch, lang)
    may = loc.loc_may(so, ngon_ngu=lang, phut_muc_tieu=phut_muc_tieu)
    td = so.tieu_de or []
    n = max(1, len(td))
    tuoi = [m for m in (dau_moc_tuoi or DAU_MOC_TUOI) if m]
    gia = sum(1 for x in td if any(m in x for m in tuoi))
    khop = sum(1 for x in td if tu_khop.search(x))
    khop_go = sum(1 for x in td if tu_khop.search(x) and (tu_go_toi or TU_GO_TOI).search(x))
    return UngVien(
        ten=so.ten, link=link, subs=so.subs, so_video=so.so_video,
        dai_tv=loc.phut_giay(so.dai_trung_vi_s) if so.dai_trung_vi_s else "",
        view_tv=so.view_trung_vi, dinh_tren_subs=so.ty_le_cao_nhat,
        pct_gia=round(100 * gia / n), pct_khop=round(100 * khop / n), pct_khop_go_toi=round(100 * khop_go / n),
        the_loai_loai=kenh_bi_loai(so.ten, link, bo_qua_zatsugaku=bo_qua_zatsugaku,
                                   tu_loai_tru=tu_loai_tru, ten_kenh_loai_tru=ten_kenh_loai_tru,
                                   handle_loai_tru=handle_loai_tru),
        cua_may_dat=may.dat, ly_do_may=may.ly_do, tieu_de=td,
        so_do=so, suc_song=_suc_song(ch),
    )


def _suc_song(ch: Any) -> Optional[Any]:
    try:
        from .kiem_ngach_doi_thu import so_kenh_tu_channel  # noqa: PLC0415

        return so_kenh_tu_channel(ch)
    except Exception:  # noqa: BLE001
        return None


def kenh_ban_dua(goc: str, kenh: str) -> set:
    """Khoá của những link khách TỰ DÁN (`doi-thu-ban-dua.txt`) — danh bạ theo định nghĩa.

    Chủ dự án 07/09/2026, thấy 大人の心理雑学 bị máy "bỏ" vì tên có 雑学: *"danh bạ đối thủ… là các
    đối thủ tao cung cấp ban đầu và trang chủ lọc về"*. Cửa máy chỉ dành cho kênh máy ảo nhặt về;
    kênh người đưa thì máy chỉ đo số (subs, view…) rồi luôn "theo dõi", không hỏi AI.
    """
    return {k for k in (db.khoa(l) for l in so.doc_ban_dua(goc, kenh)) if k}


def quyet(uv: UngVien, *, nguong_gia: int = NGUONG_GIA, nguong_khop: int = NGUONG_KHOP,
          subs_toi_da: int = SUBS_TOI_DA,
          ten_kenh_tam_ly: Sequence[str] = TEN_KENH_TAM_LY) -> Tuple[Optional[str], str]:
    """(trạng thái danh bạ hoặc `None` = để lại hộp thư thử lại lượt sau, lý do một câu).

    `ten_kenh_tam_ly` — 30/09/2026, Đợt 4 (A5): chữ kênh tự nhận đúng ngách; `_chot` truyền
    `ten_kenh_dung_ngach` của hồ sơ ngách; không truyền → hằng cũ.

    Chủ dự án 06/09/2026, nhìn hộp thư còn 8 kênh "chờ bạn quyết": *"tao muốn đơn giản hiệu quả
    và tự động mà"*. Máy quyết hết — kể cả kênh "gần" (bỏ, ghi lý do, đổi lại ở danh bạ nếu
    muốn) và kênh đã chết (bỏ). Chỉ lỗi TẠM (mạng, máy chủ) mới ở lại để lượt sau thử lại.
    """
    if uv.loi or not uv.ten:
        loi = (uv.loi or "").lower()
        if any(t in loi for t in _DAU_HIEU_KENH_CHET):
            return db.BO, "kênh không còn hoặc không xem được: " + (uv.loi or "")[:100]
        return None, "không đo được" + (": " + uv.loi if uv.loi else "")
    # ═══ DANH BẠ LÀ BẢN ĐỒ THỊ TRƯỜNG (chủ dự án 06/09/2026) ═══
    # *"đối thủ này là tài nguyên quan trọng — nó là những bên làm chủ đề tâm lý… gom được đối
    # thủ sẽ nhìn được thị trường — ở một thị trường sẽ luôn có một lượng đối thủ mới và die."*
    # Nên chỉ thứ KHÔNG PHẢI kênh tâm lý mới "bỏ" (ẩn). Kênh tâm lý nào cũng ở lại trong sổ và
    # ĐỀU được quét content ("theo dõi") — content của họ là dữ liệu thị trường, bảng "Nên làm" tự lọc
    # theo tệp. 07/09, chủ dự án: *"tạm ngưng mày cho vào danh sách làm gì"* — máy không đặt "tạm
    # ngưng" nữa; trạng thái ấy chỉ còn cho người dùng tự dừng tay một kênh đang nghỉ. Ghi chú vẫn nói
    # kênh thuộc góc nào của thị trường (tệp 55+, quá to, còn nhỏ, gần ngách) để nhìn là biết.
    if uv.the_loai_loai:
        return db.BO, "không phải kênh tâm lý: thể loại 雑学/要約/tóm sách"
    if not uv.cua_may_dat and "tiêu đề viết bằng chữ" in uv.ly_do_may:
        return db.BO, "không phải tiếng của kênh: " + uv.ly_do_may[:80]
    if not uv.cua_may_dat:
        return db.THEO_DOI, "thị trường (còn nhỏ / khác khổ): " + uv.ly_do_may[:90]
    if uv.pct_gia >= nguong_gia:
        return db.THEO_DOI, "thị trường (tệp 55+): {0}% tiêu đề gắn 50代/60代/老後".format(uv.pct_gia)
    tam_ly = any(t in uv.ten for t in (ten_kenh_tam_ly or TEN_KENH_TAM_LY))
    if uv.subs > subs_toi_da:
        # 03:16 07/09: PIVOT (kinh tế, 4 triệu subs) vào "theo dõi" chỉ vì "quá lớn" đứng trước cửa
        # tâm lý → video chứng khoán 560k view nằm đầu bảng Kết quả. Lớn hay nhỏ, KHÔNG tâm lý là bỏ.
        if not (uv.pct_khop >= nguong_khop or tam_ly):
            return db.BO, "không phải kênh tâm lý: kênh lớn ({0} subs) mà tên không nói, khớp tuyến {1}%".format(
                "{0:,}".format(uv.subs).replace(",", "."), uv.pct_khop)
        return db.THEO_DOI, "thị trường (quá lớn, {0} subs — tham khảo)".format("{0:,}".format(uv.subs).replace(",", "."))
    if uv.pct_khop >= nguong_khop or tam_ly:
        return db.THEO_DOI, "máy chấm: khớp tuyến {0}% · già {1}%".format(uv.pct_khop, uv.pct_gia)
    if uv.pct_khop == 0:
        return db.BO, "không phải kênh tâm lý: tên không nói, 0 tiêu đề khớp tuyến"
    # "gần ngách": máy không chắc → có ví thì hỏi AI (cửa thứ năm); không thì vẫn vào thị trường.
    return None, "thị trường (gần ngách, self-help chung, khớp {0}%)".format(uv.pct_khop)


def bo_hien_nhien(uv: UngVien, *, tu_kenh_hien_nhien: Sequence[str] = (),
                  handle_hien_nhien: Sequence[str] = ()) -> bool:
    """Kênh này bị bỏ vì lý do mà ĐỌC NGHĨA cũng không đổi được (chết/ẩn, sai tiếng, thể loại
    tóm sách/tin tức/nhạc/game rõ ràng) — không đáng một lượt AI. Mọi lý do "bỏ" khác của
    `quyet` là do từ khoá, và khi có ví thì phải để AI đọc nghĩa (xem đầu tệp).
    Hai bộ từ (Đợt 4): của hồ sơ ngách; rỗng → hằng của `trang_chu`."""
    if uv.loi or not uv.ten:
        return True
    if not uv.cua_may_dat and "tiêu đề viết bằng chữ" in (uv.ly_do_may or ""):
        return True
    if tu_kenh_hien_nhien or handle_hien_nhien:
        return kenh_lech_hien_nhien(uv.ten, uv.link, tu_kenh_hien_nhien=tu_kenh_hien_nhien,
                                    handle_hien_nhien=handle_hien_nhien)
    return kenh_lech_hien_nhien(uv.ten, uv.link)


def hoi_ai(client, uv: UngVien, *, mo_ta_kenh: str = "", lang: str = "", phut_muc_tieu: float = 0.0,
           hoi: Optional[Callable[..., loc.DanhGia]] = None) -> Optional[loc.DanhGia]:
    """Cửa thứ năm: hỏi AI về MỘT kênh đã qua cửa máy. Hỏng → `None` (giữ quyết định máy)."""
    if client is None or uv.so_do is None:
        return None
    hoi = hoi or loc.hoi_ai_kenh
    try:
        return hoi(client, uv.so_do, mo_ta_kenh=mo_ta_kenh, ngon_ngu=lang, phut_muc_tieu=phut_muc_tieu)
    except Exception:  # noqa: BLE001 — một kênh AI hỏng không giết cả lượt, và không lật quyết định máy
        return None


def _ghep_ai(tt: Optional[str], ly_do: str, ai: Optional[loc.DanhGia]) -> Tuple[Optional[str], str, List[str]]:
    """Quyết định cuối = máy ⊕ AI. Trả (trạng thái, lý do, tuyến AI thấy)."""
    if ai is None:
        return tt, ly_do, []
    ket = (ai.ket or "").strip().lower()
    ai_ly_do = (ai.ly_do or "").strip()
    if ai_ly_do.startswith("AI trả lời không đọc được"):
        # 06/09/2026: 記憶博士 bị "bỏ" chỉ vì AI trả về thứ không phải JSON. Không đọc được là
        # KHÔNG CÓ ý kiến — giữ quyết định máy, không lật.
        return tt, ly_do, []
    if ket == "doi_thu":
        if tt == db.BO:
            # Từ khoá định bỏ, AI đọc nghĩa thấy là đối thủ → VÀO (đúng ca kênh 雑学 tâm lý).
            return db.THEO_DOI, "AI: đối thủ ({0}đ) — {1} · lật luật từ khoá ({2})".format(
                ai.diem, ai_ly_do[:90], ly_do.replace(DAU_BO_TU_KHOA, "").strip()[:80])[:220], list(ai.tuyen)
        return db.THEO_DOI, "AI: đối thủ ({0}đ) — {1} · {2}".format(ai.diem, ai_ly_do[:90], ly_do)[:220], list(ai.tuyen)
    if ket == "gan":
        # Chủ dự án 07/09: danh bạ là kênh TÂM LÝ lấy được content. AI bảo "gần" (self-help, tâm linh,
        # kinh doanh…) tức không phải — bỏ, ghi lý do; muốn giữ thì đổi trạng thái tay.
        return db.BO, "không phải kênh tâm lý — gần ngách, AI: {0} · máy: {1}".format(ai_ly_do[:90], ly_do)[:220], []
    if ket == "khong":
        return db.BO, "không phải kênh tâm lý — AI: {0} · máy: {1}".format(ai_ly_do[:90], ly_do)[:220], []
    return tt, ly_do, []   # AI trả chữ lạ → giữ máy


def chot(goc: str, kenh: str, *, links: Optional[Sequence[str]] = None, lang: str = "",
         phut_muc_tieu: float = 0.0, lay_kenh: Optional[Callable[..., object]] = None,
         tu_khop: "re.Pattern[str]" = TU_KHOP_LECH_NHIP,
         client=None, mo_ta_kenh: Optional[str] = None,
         hoi: Optional[Callable[..., loc.DanhGia]] = None,
         on_log: Optional[Callable[[str], None]] = None,
         cancel: Optional[threading.Event] = None,
         bo_qua_zatsugaku: bool = False,
         theo_nghia: bool = True,
         xet_lai: bool = True,
         kiem_dinh_ky: bool = True,
         goi_kiem: Optional[Callable[..., str]] = None) -> Dict[str, object]:
    """Chấm `links` (mặc định: cả hộp thư) và ghi thẳng vào danh bạ.

    `client` khác `None` → thêm cửa AI (mỗi kênh một lượt gọi, trừ ví): kênh máy định theo dõi /
    để lại, VÀ (`theo_nghia`, mặc định bật — xem đầu tệp) kênh máy định BỎ bằng từ khoá. Chỉ kênh
    bỏ HIỂN NHIÊN (`bo_hien_nhien`) là không hỏi. `hoi` tách ra để test. Trả `{"cham",
    "theo_doi", "bo", "o_lai", "loi", "ai_hoi", "ai_loai", "ai_cuu", "theo_doi_links",
    "bo_links"}` (+ `"xet_lai"` khi chạy `xet_lai_bo_tu_khoa`). Kênh đã có trong danh bạ với
    trạng thái khách đặt tay thì KHÔNG bị máy đổi — máy chỉ chấm thư chưa mở (hoặc danh sách
    được truyền vào).

    `xet_lai` (mặc định bật, chỉ khi chấm HỘP THƯ, có `client` và `theo_nghia`) — cuối lượt chấm
    lại tối đa `SO_XET_LAI_MOI_LUOT` kênh cũ bị bỏ bằng từ khoá.

    `bo_qua_zatsugaku` — xem `do_ung_vien`; kênh đang đánh TỆP 3 (`mot_nut.chay` tự tính cờ
    này từ `tuyen_dang_danh`) thì cổng thể loại ở đây không loại kênh chỉ vì nó tự gọi mình
    là 雑学. Mặc định `False`: hành vi cũ không đổi.
    """
    la_hop_thu = links is None
    if la_hop_thu:
        # 01/10/2026 — BA ĐƯỜNG VÀO, MỘT CỬA: (a) `doi-thu-them.txt` của chủ dự án và (b) khán giả cùng
        # xem của Studio vào hộp thư ngay đây; (b) pool traffic-related đã vào ở `mot_nut`, (c) trang chủ
        # do máy ảo đổ. Rồi tất cả qua cùng một cửa duyệt bên dưới.
        try:
            from . import kiem_ngach_doi_thu as kn  # noqa: PLC0415

            vao = kn.nap_duong_vao(goc, kenh)
            if any(vao.values()) and on_log is not None:
                on_log("  hộp thư: +{0} kênh chủ dự án đưa (doi-thu-them.txt) · +{1} kênh khán giả cùng xem "
                       "(Studio)".format(vao.get("chu_du_an", 0), vao.get("studio", 0)))
        except Exception as loi:  # noqa: BLE001 — đường vào hỏng không giết lượt chốt
            if on_log is not None:
                on_log("  nạp đường vào đối thủ hỏng: {0}".format(str(loi)[:100]))
    if client is not None and mo_ta_kenh is None:
        mo_ta_kenh = _mo_ta_kenh_cho_ai(goc, kenh)
    tham = dict(lang=lang, phut_muc_tieu=phut_muc_tieu, lay_kenh=lay_kenh, tu_khop=tu_khop, client=client,
                mo_ta_kenh=mo_ta_kenh, hoi=hoi, on_log=on_log, cancel=cancel,
                bo_qua_zatsugaku=bo_qua_zatsugaku, theo_nghia=theo_nghia)
    dem = _chot(goc, kenh, links=links, **tham)
    if la_hop_thu and xet_lai and theo_nghia and client is not None \
            and not (cancel is not None and cancel.is_set()):
        try:
            # Kênh vừa chấm ở lượt này (kể cả AI vừa sập) không xét lại ngay — lượt sau.
            vua_cham = {db.khoa(l) for l in list(dem.get("bo_links") or []) + list(dem.get("theo_doi_links") or [])}
            dem["xet_lai"] = xet_lai_bo_tu_khoa(goc, kenh, bo_qua=vua_cham, **tham)
        except Exception as loi:  # noqa: BLE001 — xét lại hỏng không được giết lượt chốt
            if on_log is not None:
                on_log("  xét lại kênh bỏ-bằng-từ-khoá hỏng: {0}".format(str(loi)[:100]))
    if la_hop_thu and kiem_dinh_ky and client is not None and not (cancel is not None and cancel.is_set()):
        # 30/09/2026 — ĐỢT KIỂM ĐỊNH KỲ (mỗi lượt nghiên cứu ~12h): kênh "theo dõi" ngừng đăng /
        # quá yếu tự rơi ra; kênh chưa có phán quyết ngách của nhóm được LLM đọc (có trần).
        try:
            from . import kiem_ngach_doi_thu as kn  # noqa: PLC0415

            kq = kn.kiem_dinh_ky(goc, kenh, client, goi=goi_kiem, on_log=on_log)
            dem["kiem_ngach"] = {x: sum(1 for d in kq["theo_kenh"].get(kenh, []) if d["ket"] == x)
                                 for x in (kn.GIU, kn.BO, getattr(kn, "HET", "het"), kn.NGHI)}
        except Exception as loi:  # noqa: BLE001
            if on_log is not None:
                on_log("  kiểm ngách định kỳ hỏng: {0}".format(str(loi)[:100]))
    return dem


def _nguong_suc_song(goc: str, kenh: str) -> Dict[str, float]:
    """Ngưỡng "quá yếu" tương đối của nhóm (phân vị 20% trên content.csv cả nhóm). Hỏng → {}."""
    try:
        from . import kiem_ngach_doi_thu as kn  # noqa: PLC0415

        tv = kn._thanh_vien(goc, kenh)  # noqa: SLF001
        so_ = kn.so_kenh_ca_nhom(goc, tv)
        return kn.nguong_nhom(so_)
    except Exception:  # noqa: BLE001
        return {}


def _phan_quyet_kho(goc: str, kenh: str, link: str) -> Optional[Dict[str, Any]]:
    try:
        from . import kiem_ngach_doi_thu as kn  # noqa: PLC0415

        return kn.phan_quyet_nhom(goc, kenh, link)
    except Exception:  # noqa: BLE001
        return None


def _cua_suc_song(goc: str, kenh: str, uv: UngVien, nguong: Dict[str, float]) -> Tuple[bool, str]:
    if uv.suc_song is None or uv.loi or not uv.ten:
        return False, ""
    try:
        from . import kiem_ngach_doi_thu as kn  # noqa: PLC0415

        ket, ly = kn.cua_suc_song(uv.suc_song, nguong)
        return ket in (kn.BO, getattr(kn, "HET", kn.BO)), ly
    except Exception:  # noqa: BLE001
        return False, ""


def _mo_ta_kenh_cho_ai(goc: str, kenh: str) -> str:
    """Sổ tay kênh (`loc.doc_so_tay`) + mô tả ngách theo nghĩa của nhóm (`ho_so_ngach`)."""
    try:
        so_tay = loc.doc_so_tay(goc, kenh)
    except Exception:  # noqa: BLE001
        so_tay = ""
    try:
        from .trang_chu import mo_ta_ngach_cho_ai  # noqa: PLC0415

        ngach = mo_ta_ngach_cho_ai(goc, kenh)
    except Exception:  # noqa: BLE001
        ngach = ""
    if ngach:
        return "NGÁCH (đọc theo NGHĨA, không theo chữ trong tên kênh):\n{0}\n\n{1}".format(ngach, so_tay).strip()
    return so_tay


def xet_lai_bo_tu_khoa(goc: str, kenh: str, *, toi_da: int = SO_XET_LAI_MOI_LUOT,
                       bo_qua: Optional[set] = None, **tham: Any) -> Dict[str, object]:
    """Chấm lại THEO NGHĨA (qua `chot`, có AI) tối đa `toi_da` kênh danh bạ đang "bỏ" mà Ghi chú
    là của LUẬT TỪ KHOÁ (`DAU_BO_TU_KHOA`). AI nói đối thủ → kênh vào theo dõi; AI nói gần/không
    → Ghi chú đổi sang lời AI (không bị chọn lại lượt sau); AI lỗi → giữ nguyên, lượt sau thử lại.
    Không có `client` → không làm gì (`{}`)."""
    if tham.get("client") is None:
        return {}
    cot, hang = db.doc(goc, kenh)
    o = db.chi_so_cot(list(cot))
    i_l, i_t, i_g = o.get("Link kênh"), o.get("Trạng thái"), o.get("Ghi chú")
    if i_l is None or i_t is None or i_g is None:
        return {}
    ban_dua = kenh_ban_dua(goc, kenh)
    links = []
    for d in hang:
        if max(i_l, i_t, i_g) >= len(d):
            continue
        if str(d[i_t]).strip() == db.BO and str(d[i_g]).strip().startswith(DAU_BO_TU_KHOA) \
                and str(d[i_l]).strip() and db.khoa(d[i_l]) not in ban_dua \
                and db.khoa(d[i_l]) not in (bo_qua or set()):
            links.append(str(d[i_l]).strip())
    if not links:
        return {}
    links = links[:max(0, int(toi_da))]
    if tham.get("on_log") is not None:
        tham["on_log"]("  xét lại THEO NGHĨA {0} kênh từng bị bỏ bằng từ khoá…".format(len(links)))
    return _chot(goc, kenh, links=links, **tham)


def _chot(goc: str, kenh: str, *, links: Optional[Sequence[str]], lang: str, phut_muc_tieu: float,
          lay_kenh: Optional[Callable[..., object]], tu_khop: "re.Pattern[str]", client,
          mo_ta_kenh: Optional[str], hoi: Optional[Callable[..., loc.DanhGia]],
          on_log: Optional[Callable[[str], None]], cancel: Optional[threading.Event],
          bo_qua_zatsugaku: bool, theo_nghia: bool) -> Dict[str, object]:
    def log(m):
        if on_log is not None:
            on_log(m)

    if links is None:
        links = db.hop_thu(goc, kenh)
    links = [str(l).strip() for l in links if str(l).strip()]
    dem: Dict[str, object] = {"cham": 0, "theo_doi": 0, "bo": 0, "o_lai": 0, "loi": 0, "ai_hoi": 0,
                              "ai_loai": 0, "ai_cuu": 0, "theo_doi_links": [], "bo_links": []}
    if not links:
        return dem
    ban_dua = kenh_ban_dua(goc, kenh)
    ban_ghi: List[db.BanGhi] = []
    trang_thai: Dict[str, str] = {}
    ghi_chu: Dict[str, str] = {}
    tuyen_ai: Dict[str, List[str]] = {}
    nguong_ss = _nguong_suc_song(goc, kenh)
    # 30/09/2026, Đợt 4 (A5): bộ từ của hồ sơ ngách, đọc MỘT lần cho cả lượt. `tu_khop` chỉ bị
    # thay khi nơi gọi vẫn để mặc định (`TU_KHOP_LECH_NHIP`) — regex riêng của tệp thì giữ.
    tn = _tu_ngach(goc, kenh)
    if tu_khop is TU_KHOP_LECH_NHIP and tn.get("tu_khop") is not None:
        tu_khop = tn["tu_khop"]
    tham_uv = {k: tn[k] for k in ("dau_moc_tuoi", "tu_go_toi", "tu_loai_tru", "ten_kenh_loai_tru",
                                  "handle_loai_tru") if k in tn}
    tham_q = {"ten_kenh_tam_ly": tn["ten_kenh_tam_ly"]} if "ten_kenh_tam_ly" in tn else {}
    tham_hn = {k: tn[k] for k in ("tu_kenh_hien_nhien", "handle_hien_nhien") if tn.get(k)}

    def _bhn(uv: UngVien) -> bool:
        return bo_hien_nhien(uv, **tham_hn)
    if client is not None and hoi is None:
        # Kênh trong nhóm: phán quyết ngách đi qua kho chung `kenh-ai.json` — NGUỒN SỰ THẬT cho cả
        # nhóm (đợt kiểm ngách ghi vào đây), để một kênh không tự lật cái kênh anh em đã bỏ.
        try:
            from . import nghien_cuu_chung as ncc  # noqa: PLC0415

            if ncc.nhom_cua(goc, kenh):
                hoi = ncc.hoi_ai_co_dem(goc, kenh)
        except Exception:  # noqa: BLE001
            pass
    for i, link in enumerate(links, 1):
        if cancel is not None and cancel.is_set():
            break
        uv = do_ung_vien(link, lang=lang, phut_muc_tieu=phut_muc_tieu, lay_kenh=lay_kenh,
                         tu_khop=tu_khop, cancel=cancel, bo_qua_zatsugaku=bo_qua_zatsugaku, **tham_uv)
        dem["cham"] += 1
        tt, ly_do = quyet(uv, **tham_q)
        la_ban_dua = db.khoa(link) in ban_dua and not (uv.loi or not uv.ten)
        if la_ban_dua:
            tt, ly_do = db.THEO_DOI, GHI_CHU_BAN_DUA
            dem["ban_dua"] = dem.get("ban_dua", 0) + 1
        if uv.loi or not uv.ten:
            if tt == db.BO:
                # Kênh đã chết/ẩn: ghi vào danh bạ là "bỏ" (tên lấy từ link) để hộp thư thôi giữ nó.
                ban_ghi.append(db.BanGhi(ten=uv.ten or db._ten_tu_link(link), link=link))  # noqa: SLF001
                trang_thai[link] = tt
                ghi_chu[link] = ly_do
                dem["bo"] += 1
                dem["bo_links"].append(link)
                log("  [{0}/{1}] {2} → bỏ: {3}".format(i, len(links), link[:40], ly_do))
                continue
            dem["loi"] += 1
            log("  [{0}/{1}] {2} → không đo được, để lại thử lượt sau: {3}".format(i, len(links), link[:40], ly_do))
            continue
        tuyen: List[str] = []
        # 30/09/2026 — CỬA SỨC SỐNG (máy, miễn phí, trước AI): ngừng đăng video dài ≥ 30 ngày
        # hoặc quá yếu so với nhóm (không video nổi, không tăng trưởng) → bỏ, kể cả kênh bạn đưa.
        bo_song, ly_song = _cua_suc_song(goc, kenh, uv, nguong_ss)
        if bo_song:
            # 01/10/2026 — chết ≠ sai chủ đề: "hết" (lượt kiểm định kỳ đo lại, tự hồi sinh).
            tt, ly_do = getattr(db, "HET", db.BO), "Hết — " + ly_song
            la_ban_dua = False
        # Hỏi AI: máy định theo dõi/để lại (như cũ) — VÀ, theo nghĩa, cả kênh máy định BỎ bằng từ
        # khoá; chỉ kênh bỏ HIỂN NHIÊN (chết, sai tiếng, tóm sách/tin tức/nhạc…, ngừng hoạt động)
        # là không tốn lượt.
        can_ai = not bo_song and (tt != db.BO or (theo_nghia and not _bhn(uv)))
        ai_doi_thu = False
        if client is not None and can_ai and not la_ban_dua:
            ai = hoi_ai(client, uv, mo_ta_kenh=mo_ta_kenh or "", lang=lang, phut_muc_tieu=phut_muc_tieu, hoi=hoi)
            if ai is not None:
                if (ai.ly_do or "").startswith("AI trả lời không đọc được"):
                    dem["ai_khong_doc"] = dem.get("ai_khong_doc", 0) + 1
                    log("    AI trả lời không đọc được cho {0} — giữ quyết định máy. Đầu câu trả lời: {1}"
                        .format(uv.ten[:30], (ai.khac or "(rỗng)")[:160]))
                else:
                    dem["ai_hoi"] += 1
                    ai_doi_thu = (ai.ket or "").strip().lower() == "doi_thu"
                tt_cu = tt
                tt, ly_do, tuyen = _ghep_ai(tt, ly_do, ai)
                if tt == db.BO and tt_cu != db.BO:
                    dem["ai_loai"] += 1
                if tt_cu == db.BO and tt == db.THEO_DOI:
                    dem["ai_cuu"] = int(dem.get("ai_cuu", 0)) + 1
            elif tt == db.BO and not _bhn(uv):
                ly_do = ly_do + " (AI không trả lời — giữ luật từ khoá)"
        elif client is None and not bo_song and not la_ban_dua and not (tt == db.BO and _bhn(uv)):
            # Không ví (chế độ thử, lượt đầu): không hỏi được LLM — nhưng phán quyết NGÁCH đã có của
            # nhóm (`kenh-ai.json`) vẫn là sự thật dùng được, 0 đồng.
            m = _phan_quyet_kho(goc, kenh, link)
            if m is not None:
                if m.get("kiem_ngach") == "giu":
                    ai_doi_thu = True
                    tt, ly_do = db.THEO_DOI, "AI (kho nhóm {0}): đối thủ — {1}".format(
                        m.get("ngay") or "?", str(m.get("ly_do") or "")[:120])
                else:
                    tt, ly_do = db.BO, "không phải kênh tâm lý — AI (kho nhóm {0}): {1}".format(
                        m.get("ngay") or "?", str(m.get("ly_do") or "")[:120])
        # ═══ CỬA VÀO "THEO DÕI" (30/09/2026) ═══ — chỉ khi LLM phán ĐÚNG NGÁCH (hoặc kênh người
        # dán tay). Tỉ lệ khớp từ khoá của máy KHÔNG đủ: Barry Nobles (188k sub, không tâm lý) vào
        # "theo dõi" TL1 chỉ vì "khớp tuyến 12%". Không có phán quyết LLM → để lại HỘP THƯ, lượt
        # sau hỏi lại (không ghi danh bạ).
        if tt in (None, db.THEO_DOI) and not la_ban_dua and not ai_doi_thu:
            dem["o_lai"] = int(dem.get("o_lai", 0)) + 1
            log("  [{0}/{1}] {2} → để lại hộp thư: chưa có phán quyết ngách của LLM ({3})".format(
                i, len(links), (uv.ten or link)[:30], ly_do[:80]))
            continue
        log("  [{0}/{1}] {2} → {3}: {4}".format(i, len(links), (uv.ten or link)[:30], tt, ly_do))
        ban_ghi.append(db.BanGhi(ten=uv.ten, link=link, subs=uv.subs, so_video=uv.so_video,
                                 dai_tv=uv.dai_tv, view_tv=uv.view_tv, vuot_quy_mo=uv.dinh_tren_subs))
        trang_thai[link] = tt
        ghi_chu[link] = ly_do
        if tuyen:
            tuyen_ai[link] = tuyen
        if tt == db.THEO_DOI:
            dem["theo_doi"] += 1
            dem["theo_doi_links"].append(link)
        elif tt == db.TAM_NGUNG:
            dem["tam_ngung"] = dem.get("tam_ngung", 0) + 1
        elif tt == getattr(db, "HET", None):
            dem["het"] = dem.get("het", 0) + 1
            dem["bo_links"].append(link)
        else:
            dem["bo"] += 1
            dem["bo_links"].append(link)
    if not ban_ghi:
        return dem
    cot, hang = db.doc(goc, kenh)
    hang = db.gop_cham(cot, hang, ban_ghi)
    for tt in (db.THEO_DOI, db.TAM_NGUNG, getattr(db, "HET", db.BO), db.BO):
        nhom = [l for l, t in trang_thai.items() if t == tt]
        if nhom:
            hang = db.dat_trang_thai(cot, hang, nhom, tt)
    for link, ly_do in ghi_chu.items():
        hang = db._dat_cot(cot, hang, [link], "Ghi chú", ly_do)  # noqa: SLF001 — cùng gói core
    # Tuyến AI thấy — chỉ điền ô TRỐNG: cột "Tuyến" là cột của khách.
    o = db.chi_so_cot(list(cot))
    i_link, i_tuyen = o.get("Link kênh"), o.get("Tuyến")
    if i_link is not None and i_tuyen is not None:
        for dong in hang:
            k = db.khoa(dong[i_link]) if i_link < len(dong) else ""
            for link, tuyen in tuyen_ai.items():
                if k and k == db.khoa(link) and not str(dong[i_tuyen]).strip():
                    dong[i_tuyen] = " · ".join(tuyen)[:120]
    db.luu(goc, kenh, cot, hang)
    log("  chốt danh bạ: +{0} theo dõi · {1} bỏ · {7} hết · {2} để lại hộp thư · {3} không đo được · AI hỏi {4}, loại {5}"
        ", cứu {6} (từ khoá định bỏ, AI đọc nghĩa thấy là đối thủ)"
        .format(dem["theo_doi"], dem["bo"], dem["o_lai"], dem["loi"], dem["ai_hoi"], dem["ai_loai"],
                dem.get("ai_cuu", 0), dem.get("het", 0)))
    return dem
