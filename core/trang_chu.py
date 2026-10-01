"""Trang chủ YouTube của phiên kênh → đối thủ mới. Nửa TRÊN TOOL của đường "cào trang chủ".

Chủ dự án, 05/09/2026:
  *"cách cào đơn giản chỉ là mở trang chủ và thu nhỏ để lấy hết link về, sau đó chuyển cho bên
  tool — tool sẽ làm các việc phía sau"* … *"bên tool máy này sẽ bắt đầu lọc các tiêu đề thuộc
  đúng chủ đề tâm lý — có thể dùng API để phân loại — nếu đúng tâm lý thì lấy ra đối thủ, danh
  bạ đối thủ sẽ tăng"* … *"khi có danh bạ thì xử lý content đối thủ để phân loại tuyến và chấm điểm"*.

Đường đi, và phần nào đã có sẵn:

    máy ảo mở trang chủ ─► extension gom link ─► trạm ghi `trang-chu.csv`      (chi_so_ytb.tram)
      └► TỆP NÀY: tra kênh/tiêu đề bằng yt-dlp ─► lọc "có phải tâm lý?" ─► kênh vào HỘP THƯ
            └► "Nhận vào danh bạ" ─► "Quét đối thủ" (content.csv) ─► "Phân tuyến" ─► chấm  (đã có)

Ba luật tiền ở đây:
1. **yt-dlp trước, AI sau.** Tra tên kênh, tag, mô tả bằng yt-dlp là miễn phí. Từ khoá CHỈ còn
   quyết ca HIỂN NHIÊN (sai tiếng, Shorts, kênh tóm sách/tin tức/nhạc/game rõ ràng — xem
   `phan_loai_tien_loc`); mọi tiêu đề khác, KỂ CẢ tiêu đề từ khoá đã cho là "đúng tâm lý", đi
   qua AI ĐỌC NGHĨA khi có `goi_ai` (xem "THEO NGHĨA" dưới). Không có `goi_ai` thì y như cũ.

═══ THEO NGHĨA, KHÔNG THEO TỪ KHOÁ (29/09/2026) ═══

Chủ dự án: *"Lọc theo từ khoá là SAI — phải theo Ý NGHĨA, suy nghĩ. Đừng tiếc token."* Ba ca
thật từ khoá quyết sai: kênh 雑学 khán giả TL4 đang cùng xem (insight #8 — 4/15 kênh trong card
"đối thủ cùng khán giả" của Studio tự gọi mình là 雑学) bị loại thẳng; 「恋愛」 trong tiêu đề tâm
lý quan hệ bị loại; 「心理テスト」 trò chơi lọt vào vì có 心理. Nên khi có `goi_ai`:

    hiển nhiên lệch (tiền lọc rẻ)  → loại ngay, không hỏi AI
    còn lại                         → AI đọc nghĩa theo lô 25 (tên kênh đi kèm), nhớ 90 ngày
                                      (kho nhóm `trang-chu-ai.json`, dùng lại được giữa các kênh)
    AI lỗi / vượt trần lượt này     → dùng phán quyết từ khoá (đường lùi, ghi rõ trong log)

Tiêu đề LƯỠNG LỰ vẫn hỏi hết như trước; tiêu đề từ khoá cho "đúng" được hỏi thêm tối đa
`TOI_DA_AI_THEO_NGHIA` cái mới nhất mỗi lượt (lượt sau gánh tiếp) — trần để lượt đầu không kéo
cả giờ (nguồn LLM ban ngày 2–8 token/giây).
2. **Không tra lại thứ đã tra.** Trang chủ ngày nào cũng lặp lại vài chục video; bộ nhớ
   `trang-chu-tra.json` giữ kết quả theo mã video.
3. **Lọc theo TÊN KÊNH và TAG, không chỉ tiêu đề.** Hai kênh 雑学 lọt vào sổ vì bản cũ chỉ có link.
   Tag tuổi (50代/60代…) của kênh nguồn là thứ đã chứng minh kéo tệp già — ghi lại để bảng chấm dùng.
"""

from __future__ import annotations

import contextvars
import csv
import io
import json
import os
import re
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import doi_thu_kenh as so
from .phan_tuyen import TU_LOAI_TRU

__all__ = ["TEP", "TEP_TRA", "COT", "doc", "luu", "tra_video", "phan_loai_tam_ly",
           "hoan_thien", "tom_tat", "TU_MANH", "TU_YEU", "DAU_MOC_TUOI_KENH",
           "HANDLE_LOAI_TRU", "TEN_KENH_LOAI_TRU", "kenh_bi_loai", "phan_loai_bang_ai", "ngon_ngu_kenh", "dung_tieng",
           "TU_KENH_HIEN_NHIEN", "HANDLE_HIEN_NHIEN", "TU_TIEU_DE_HIEN_NHIEN", "kenh_lech_hien_nhien",
           "phan_loai_tien_loc", "mo_ta_ngach_cho_ai", "TOI_DA_AI_THEO_NGHIA"]

TEP = "trang-chu.csv"
TEP_TRA = "trang-chu-tra.json"
#: Phải khớp `chi_so_ytb.tram.Tram.COT_TRANG_CHU` — trạm ghi, tệp này đọc/sửa.
COT = ("Lúc quét", "Vị trí", "Kệ", "Mã video", "Tiêu đề", "Kênh",
       "Link kênh", "Lượt xem", "Đăng", "Dài", "Short", "Bị loại", "Lượt tải")

#: Từ khoá ngách — chép từ `CHANNEL/TL4-T7/CLAUDE.md` (mục "Từ khoá ngách"). MẠNH: một từ là
#: đủ. YẾU: cần ≥ 2 từ. Loại trừ dùng chung `phan_tuyen.TU_LOAI_TRU`.
TU_MANH = ("心理", "メンタル", "脳科学", "HSP", "内向", "自己肯定感", "生きづらい", "繊細さん",
           "繊細", "考えすぎ", "劣等感", "承認欲求", "アドラー", "ユング", "認知", "うつ", "不安障害", "愛着")
TU_YEU = ("人間関係", "孤独", "感情", "不安", "ストレス", "性格", "幸せ", "人生", "疲れ", "一人",
          "1人", "ひとり", "習慣", "自分を", "強い人", "特徴", "理由")
#: 雑学 viết romaji trong HANDLE kênh — 「@hitomamezatugaku」 lọt qua bộ lọc kanji ngay lượt
#: chạy khô đầu tiên (05/09/2026). Tách riêng khỏi `TU_LOAI_TRU` (từ cho TIÊU ĐỀ, dùng chung
#: với bộ phân tuyến) để không làm bẩn bộ đó; chỉ soi handle/link kênh.
HANDLE_LOAI_TRU = ("zatsugaku", "zatugaku", "zatsu", "trivia", "matome", "2ch", "5ch",
                   "youyaku", "yoyaku", "summary", "booktuber", "book_tuber", "book-tuber")

#: Từ ở TÊN KÊNH đánh dấu cả một THỂ LOẠI không remake được — khác `TU_LOAI_TRU` (áp lên từng
#: tiêu đề). Lượt cào trang chủ thật 05/09/2026 lọt 本要約チャンネル (@youyaku) và アバタロー
#: (@Aba_Book_Tuber): kênh tóm sách nói về tâm lý thì tiêu đề vẫn "đúng tâm lý", nhưng nguồn
#: remake của kênh kể chuyện tâm lý không thể là kênh đọc sách người khác.
TEN_KENH_LOAI_TRU = ("要約", "まとめ", "朗読", "オーディオブック", "名言集", "ゆっくり解説", "切り抜き")


#: ═══ TIỀN LỌC RẺ — CHỈ CA HIỂN NHIÊN (29/09/2026) ═══
#:
#: Tập CON của các bộ loại trừ ở trên, gồm đúng những dấu hiệu mà đọc nghĩa cũng không đổi được
#: kết luận: kênh tóm sách/đọc sách/cắt clip/tổng hợp 2ch (không phải nguồn remake của kênh kể
#: chuyện tâm lý, bất kể đề tài), kênh tin tức/thể thao/nhạc/game/anime. CỐ Ý KHÔNG có 雑学
#: (insight #8: kênh 雑学 tâm lý là đối thủ thật khán giả đang cùng xem), 恋愛 (tâm lý quan hệ),
#: 漫画 (kênh giải thích tâm lý bằng truyện tranh) — ba cái đó để AI đọc nghĩa.
TU_KENH_HIEN_NHIEN = TEN_KENH_LOAI_TRU + ("ニュース", "速報", "野球", "サッカー", "ゲーム実況", "実況",
                                          "アニメ", "BGM", "音楽", "歌ってみた", "料理", "ホラー", "政治",
                                          "ドラマ", "反応集", "海外の反応", "2ch", "5ch", "ゆっくり", "スカッと")
HANDLE_HIEN_NHIEN = ("matome", "2ch", "5ch", "youyaku", "yoyaku", "summary", "booktuber", "book_tuber",
                     "book-tuber", "news", "music", "gaming")
#: Dấu thể loại HIỂN NHIÊN trong TIÊU ĐỀ (có chắn phủ định như `phan_tuyen._dinh_tu_loai_tru`:
#: 「ニュースや政治に興味がない人」 không bị bắt).
TU_TIEU_DE_HIEN_NHIEN = ("速報", "反応集", "海外の反応", "ゲーム実況", "歌ってみた", "作業用BGM", "スカッと", "2ch", "5ch")
#: Mỗi lượt `hoan_thien` hỏi AI thêm tối đa ngần này tiêu đề mà từ khoá đã cho "đúng" (mới
#: nhất trước). Tiêu đề lưỡng lự không tính vào trần này — chúng vẫn được hỏi hết như trước.
TOI_DA_AI_THEO_NGHIA = 200

_DUOI_PHU_DINH_TD = ("に興味がない", "に全く興味がない", "に興味が持てない", "をしない", "を見ない", "が苦手",
                     "に興味のない", "に夢中になれない")


def kenh_lech_hien_nhien(ten_kenh: str = "", link_kenh: str = "", *,
                         tu_kenh_hien_nhien: Sequence[str] = TU_KENH_HIEN_NHIEN,
                         handle_hien_nhien: Sequence[str] = HANDLE_HIEN_NHIEN) -> bool:
    """Kênh HIỂN NHIÊN không phải nguồn remake tâm lý (tóm sách, tin tức, nhạc, game…) — tiền lọc
    rẻ không cần AI. Khác `kenh_bi_loai` (giữ nguyên cho nơi gọi cũ): không bắt 雑学/恋愛/漫画.

    Hai bộ từ — 30/09/2026 Đợt 4: mặc định là hằng tiếng Nhật; `hoan_thien` truyền bộ của
    `ho_so_ngach` (rỗng → hằng cũ)."""
    ten = ten_kenh or ""
    if any(t in ten for t in (tu_kenh_hien_nhien or TU_KENH_HIEN_NHIEN)):
        return True
    h = (link_kenh or "").lower()
    return any(t in h for t in (handle_hien_nhien or HANDLE_HIEN_NHIEN))


def _tieu_de_lech_hien_nhien(tieu_de: str, tu: Sequence[str] = TU_TIEU_DE_HIEN_NHIEN) -> bool:
    td = tieu_de or ""
    for t in (tu or TU_TIEU_DE_HIEN_NHIEN):
        i = td.find(t)
        while i >= 0:
            if not any(td[i + len(t):].lstrip("やと・,、 ").startswith(d) for d in _DUOI_PHU_DINH_TD):
                return True
            i = td.find(t, i + 1)
    return False


def phan_loai_tien_loc(tieu_de: str, ten_kenh: str = "", link_kenh: str = "", lang: str = "",
                       short: bool = False, *,
                       tu_kenh_hien_nhien: Sequence[str] = TU_KENH_HIEN_NHIEN,
                       handle_hien_nhien: Sequence[str] = HANDLE_HIEN_NHIEN,
                       tu_tieu_de_hien_nhien: Sequence[str] = TU_TIEU_DE_HIEN_NHIEN) -> str:
    """`'lech'` nếu HIỂN NHIÊN không phải nguồn (sai tiếng, Shorts, kênh/tiêu đề thể loại rõ ràng),
    `''` nếu phải đọc nghĩa. Không bao giờ trả `'dung'` — "đúng tâm lý" là việc của AI.
    Ba bộ từ: xem `kenh_lech_hien_nhien` (Đợt 4, theo hồ sơ ngách)."""
    if short:
        return "lech"
    if (tieu_de or ten_kenh) and not dung_tieng((tieu_de or "") + " " + (ten_kenh or ""), lang):
        return "lech"
    if kenh_lech_hien_nhien(ten_kenh, link_kenh, tu_kenh_hien_nhien=tu_kenh_hien_nhien,
                            handle_hien_nhien=handle_hien_nhien) \
            or _tieu_de_lech_hien_nhien(tieu_de, tu_tieu_de_hien_nhien):
        return "lech"
    return ""


def kenh_bi_loai(ten_kenh: str = "", link_kenh: str = "", *, bo_qua_zatsugaku: bool = False,
                 tu_loai_tru: Sequence[str] = TU_LOAI_TRU,
                 ten_kenh_loai_tru: Sequence[str] = TEN_KENH_LOAI_TRU,
                 handle_loai_tru: Sequence[str] = HANDLE_LOAI_TRU) -> bool:
    """Kênh nguồn dính từ loại trừ (kanji ở tên) hay romaji ở handle/link.

    `bo_qua_zatsugaku=True`: kênh đang đánh TỆP 3 (người tò mò) — kênh chuyên nhất của tệp ấy
    TỰ GỌI MÌNH là 雑学 (`BAN-DO-TEP-KHAN-GIA.md`: カップ麺を待つ間に見たい雑学, 71%). Không có
    cờ này thì lượt cào trang chủ loại thẳng chính nguồn remake tốt nhất của kênh ấy — kênh
    còn chưa kịp vào hộp thư đã bị bỏ. Mặc định `False`: hành vi mọi nơi gọi cũ không đổi.

    `tu_loai_tru`/`ten_kenh_loai_tru`/`handle_loai_tru` — 30/09/2026, Đợt 4 (A4): mặc định là ba
    hằng tiếng Nhật của ngách "tâm lý"; nơi gọi biết ngách của kênh (`ho_so_ngach`) truyền bộ
    của ngách đó; rỗng → hằng cũ.
    """
    tu_loai_tru = tu_loai_tru or TU_LOAI_TRU
    ten_kenh_loai_tru = ten_kenh_loai_tru or TEN_KENH_LOAI_TRU
    handle_loai_tru = handle_loai_tru or HANDLE_LOAI_TRU
    tu = tu_loai_tru if not bo_qua_zatsugaku else tuple(t for t in tu_loai_tru if t != "雑学")
    if any(t in (ten_kenh or "") for t in tu) or any(t in (ten_kenh or "") for t in ten_kenh_loai_tru):
        return True
    h = (link_kenh or "").lower()
    return any(t in h for t in handle_loai_tru) or any(t in (link_kenh or "") for t in tu)


def bo_tu_ngach(goc: str, kenh: str) -> Dict[str, List[str]]:
    """Mọi bộ từ lọc trang chủ của kênh theo hồ sơ ngách (Đợt 4). Khoá = tên tham số của
    `phan_loai_tam_ly` / `phan_loai_tien_loc` / `kenh_bi_loai`; khoá hồ sơ bỏ trống → hằng cũ.
    Kênh không nhóm, nhóm chưa có ngach.yaml, tệp hỏng → toàn hằng cũ."""
    try:
        from .ho_so_ngach import doc_ngach  # noqa: PLC0415

        hs = doc_ngach(goc, kenh)
    except Exception:  # noqa: BLE001 — hồ sơ hỏng không được làm vỡ lượt cào
        hs = None

    def lay(truong, mac_dinh):
        return list(getattr(hs, truong, None) or []) or list(mac_dinh)
    return {
        "tu_manh": lay("tu_manh", TU_MANH), "tu_yeu": lay("tu_yeu", TU_YEU),
        "tu_loai_tru": lay("tu_loai_tru", TU_LOAI_TRU),
        "ten_kenh_loai_tru": lay("ten_kenh_loai_tru", TEN_KENH_LOAI_TRU),
        "handle_loai_tru": lay("handle_loai_tru", HANDLE_LOAI_TRU),
        "tu_kenh_hien_nhien": lay("tu_kenh_hien_nhien", TU_KENH_HIEN_NHIEN),
        "handle_hien_nhien": lay("handle_hien_nhien", HANDLE_HIEN_NHIEN),
        "tu_tieu_de_hien_nhien": lay("tu_tieu_de_hien_nhien", TU_TIEU_DE_HIEN_NHIEN),
        "dau_moc_tuoi_kenh": lay("dau_moc_tuoi_kenh", DAU_MOC_TUOI_KENH),
    }


_KHOA_TAM_LY = ("tu_manh", "tu_yeu", "tu_loai_tru", "ten_kenh_loai_tru", "handle_loai_tru")
_KHOA_TIEN_LOC = ("tu_kenh_hien_nhien", "handle_hien_nhien", "tu_tieu_de_hien_nhien")


def _chon(bo: Optional[Dict[str, List[str]]], khoa: Sequence[str]) -> Dict[str, List[str]]:
    return {k: bo[k] for k in khoa if bo and bo.get(k)}


_CHU_NHAT = re.compile(r"[぀-ヿ一-鿿]")

#: Bảng chữ nhận ra một tiếng (ngoài tiếng Nhật) — `dung_tieng`. Tiếng Việt: chữ có dấu riêng.
_CHU_THEO_TIENG = {
    "vi": re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
                     re.IGNORECASE),
    "ko": re.compile(r"[가-힣ᄀ-ᇿ]"),
    "zh": re.compile(r"[一-鿿]"),
    "th": re.compile(r"[฀-๿]"),
    "ru": re.compile(r"[Ѐ-ӿ]"),
    "ar": re.compile(r"[؀-ۿ]"),
    "hi": re.compile(r"[ऀ-ॿ]"),
}


def ngon_ngu_kenh(goc: str, kenh: str) -> str:
    """`ngon_ngu` trong kenh.yaml của kênh — thiếu thì trả "" (không lọc theo tiếng)."""
    try:
        import yaml  # noqa: PLC0415
        from .kenh import duong_kenh  # noqa: PLC0415

        p = os.path.join(duong_kenh(goc), kenh, "kenh.yaml")
        return str((yaml.safe_load(io.open(p, encoding="utf-8")) or {}).get("ngon_ngu") or "").strip().lower()
    except Exception:  # noqa: BLE001
        return ""


def dung_tieng(chu: str, lang: str) -> bool:
    """Chữ này có thuộc tiếng của kênh không. Hiện chỉ biết phân biệt tiếng Nhật.

    ═══ VÌ SAO CẦN ═══
    Lượt cào trang chủ thật đầu tiên (05/09/2026, máy dev đăng nhập tài khoản, IP Việt Nam) trả
    422 video: VTV24, PEWPEW, Booba, Charlie Puth, La Psicología Invisible… — và trạm đã nối
    **267 kênh** như thế vào hộp thư của một kênh tiếng Nhật trước khi ai kịp nhìn. Kênh `ja` mà
    tiêu đề + tên kênh không có một chữ Nhật nào thì không thể là nguồn remake, bất kể đề tài.
    Tiếng khác chưa có luật → trả True (không lọc), không đoán.
    """
    if not lang or not chu:
        return True
    if lang.startswith("ja"):
        return bool(_CHU_NHAT.search(chu))
    # 01/10/2026 — tiếng có chữ viết RIÊNG nhận ra được bằng bảng chữ (VPS ngách/quốc gia khác).
    # Tiếng dùng chung chữ La-tinh trơn (en, es, fr…) không đoán được → không lọc (như cũ).
    khuon = _CHU_THEO_TIENG.get(lang.lower().split("-")[0])
    if khuon is not None:
        return bool(khuon.search(chu))
    return True


#: Kênh nguồn tự gắn thẻ tuổi già — đo 05/09/2026: nguồn từ kênh ≥ 34% video gắn thẻ này cho ra
#: V4 (100% người xem lặp) và V5 (51 hiển thị). Ghi cờ để bảng chấm trừ điểm; KHÔNG tự loại ở đây.
DAU_MOC_TUOI_KENH = ("50代", "60代", "70代", "老後", "定年", "シニア", "高齢", "中年", "熟年", "還暦", "年金")


def _duong(goc: str, kenh: str, ten: str) -> str:
    return os.path.join(so.thu_muc_nghien_cuu(goc, kenh), ten)


def doc(goc: str, kenh: str) -> List[Dict[str, str]]:
    """Mọi dòng của `trang-chu.csv`, mỗi dòng một dict theo `COT`. Không có tệp → []."""
    p = _duong(goc, kenh, TEP)
    try:
        with open(p, "r", encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except OSError:
        return []


def luu(goc: str, kenh: str, dong: Sequence[Dict[str, str]]) -> None:
    """Ghi lại cả bảng — nguyên tử. Cột theo `COT`; ô lạ bị bỏ."""
    p = _duong(goc, kenh, TEP)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(COT), extrasaction="ignore")
        w.writeheader()
        for d in dong:
            w.writerow({k: d.get(k, "") for k in COT})
    os.replace(tam, p)


def _doc_tra(goc: str, kenh: str) -> Dict[str, dict]:
    # 29/09/2026: kênh trong nhóm dùng CHUNG bộ nhớ tra (`nghien_cuu_chung`) —
    # trước đây ba kênh cùng nhóm tra lại cùng ~400 mã mỗi lượt. Kênh không nhóm:
    # đúng đường cũ `CHANNEL/<kênh>/nghien-cuu/trang-chu-tra.json`.
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    return ncc.doc_tra(goc, kenh)


def _luu_tra(goc: str, kenh: str, bo_nho: Dict[str, dict]) -> None:
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    ncc.luu_tra(goc, kenh, bo_nho)


def tra_video(ma: str, *, lang: str = "", cancel: Optional[threading.Event] = None) -> Dict[str, str]:
    """Metadata một video bằng yt-dlp — **có gọi mạng, không tốn tiền**. Không lấy được → {}.

    Dùng `youtube._extract` của tool (đã có thử lại, ngắt được, không in chữ đỏ) thay vì tự
    gọi YoutubeDL; `_args_ngon_ngu(lang)` giữ tiêu đề TIẾNG GỐC — tiêu đề bị dịch máy là lỗi
    đã làm hỏng ~40% sổ đối thủ TL4-T7 trước đây.
    """
    from .youtube import _args_ngon_ngu, _extract  # noqa: PLC0415 — cùng gói

    tt = _extract("https://www.youtube.com/watch?v=" + ma,
                  {"extract_flat": False, "extractor_args": _args_ngon_ngu(lang)},
                  cancel=cancel) or {}
    if not tt:
        return {}
    handle = str(tt.get("uploader_id") or "")
    link = ("https://www.youtube.com/" + handle) if handle.startswith("@") else str(tt.get("channel_url") or "")
    d = int(tt.get("duration") or 0)
    ngay = str(tt.get("upload_date") or "")
    return {
        "tieu_de": str(tt.get("title") or ""),
        "ten_kenh": str(tt.get("channel") or tt.get("uploader") or ""),
        "link_kenh": link,
        "luot_xem": str(tt.get("view_count") or ""),
        "dang": "{0}-{1}-{2}".format(ngay[:4], ngay[4:6], ngay[6:8]) if len(ngay) == 8 else "",
        "dai": "{0}:{1:02d}".format(d // 60, d % 60) if d else "",
        "short": d and d <= 180,
        "tags": [str(t) for t in (tt.get("tags") or [])],
        "mo_ta": str(tt.get("description") or "")[:600],
        "sub_kenh": str(tt.get("channel_follower_count") or ""),
    }


def binh_luan_video(ma: str, *, so: int = 30, lang: str = "",
                    cancel: Optional[threading.Event] = None) -> List[Tuple[int, str]]:
    """Bình luận nhiều like nhất dưới một video, bằng yt-dlp — **có mạng, không tốn tiền**.

    Trả `[(like, chữ), …]` xếp theo like giảm dần, chỉ bình luận gốc (không lấy trả
    lời). Đây là "người xem thật khen chỗ nào" — thứ bộ chấm kịch bản cần mà kịch
    bản gốc không nói. Lấy không được → `[]`, nơi gọi tự ghi "(không có)".
    """
    from .youtube import _args_ngon_ngu, _extract  # noqa: PLC0415 — cùng gói

    n = max(1, int(so or 1))
    args = _args_ngon_ngu(lang)
    yt = args.setdefault("youtube", {})
    # max_comments = "tổng, số bình luận gốc, số trả lời, trả lời mỗi luồng"
    yt["max_comments"] = [str(n * 2), str(n * 2), "0", "0"]
    yt["comment_sort"] = ["top"]
    tt = _extract("https://www.youtube.com/watch?v=" + ma,
                  {"extract_flat": False, "getcomments": True, "extractor_args": args},
                  cancel=cancel) or {}
    ra: List[Tuple[int, str]] = []
    for c in tt.get("comments") or []:
        if not isinstance(c, dict):
            continue
        if c.get("parent") not in (None, "", "root"):
            continue
        chu = " ".join(str(c.get("text") or "").split())
        if chu:
            ra.append((int(c.get("like_count") or 0), chu))
    ra.sort(key=lambda x: -x[0])
    return ra[:n]


def phan_loai_tam_ly(tieu_de: str, tags: Sequence[str] = (), mo_ta: str = "",
                     ten_kenh: str = "", link_kenh: str = "", lang: str = "", *,
                     bo_qua_zatsugaku: bool = False,
                     tu_manh: Sequence[str] = TU_MANH, tu_yeu: Sequence[str] = TU_YEU,
                     tu_loai_tru: Sequence[str] = TU_LOAI_TRU,
                     ten_kenh_loai_tru: Sequence[str] = TEN_KENH_LOAI_TRU,
                     handle_loai_tru: Sequence[str] = HANDLE_LOAI_TRU) -> str:
    """'dung' · 'lech' · 'lung' — bằng từ khoá ngách, không gọi ai.

    Thứ tự cố ý: từ loại trừ thắng trước (雑学 trong tên kênh là loại dù tiêu đề có 心理学);
    rồi MẠNH (một từ là đủ); rồi YẾU (cần ≥ 2). Còn lại là lưỡng lự — chỗ duy nhất đáng tốn AI.

    `bo_qua_zatsugaku` — xem `kenh_bi_loai`; kênh đang đánh TỆP 3 thì 雑学 không loại.

    Năm bộ từ — 30/09/2026, Đợt 4 (A4): mặc định là hằng tiếng Nhật của ngách "tâm lý"; nơi gọi
    truyền `bo_tu_ngach(goc, kenh)`; rỗng → hằng cũ. Đây chỉ là ĐƯỜNG LÙI khi AI đọc nghĩa lỗi.
    """
    tu_manh = tu_manh or TU_MANH
    tu_yeu = tu_yeu or TU_YEU
    tu_loai_tru = tu_loai_tru or TU_LOAI_TRU
    tu = tu_loai_tru if not bo_qua_zatsugaku else tuple(t for t in tu_loai_tru if t != "雑学")
    if any(t in (tieu_de or "") for t in tu) or kenh_bi_loai(
            ten_kenh, link_kenh, bo_qua_zatsugaku=bo_qua_zatsugaku, tu_loai_tru=tu_loai_tru,
            ten_kenh_loai_tru=ten_kenh_loai_tru, handle_loai_tru=handle_loai_tru):
        return "lech"
    if (tieu_de or ten_kenh) and not dung_tieng((tieu_de or "") + " " + (ten_kenh or ""), lang):
        return "lech"
    chu = " ".join((tieu_de or "", " ".join(tags or ()), (mo_ta or "")[:300]))
    if any(t in chu for t in tu_manh):
        return "dung"
    if sum(1 for t in tu_yeu if t in (tieu_de or "")) >= 2:
        return "dung"
    return "lung"


#: Mô tả ngách MẶC ĐỊNH khi nhóm chưa có `ngach.yaml` (`core.ho_so_ngach`) — đúng ngách TL1–TL4.
MO_TA_NGACH_MAC_DINH = (
    "Tâm lý học / khoa học não bộ tiếng Nhật cho người xem TỰ HIỂU MÌNH: video kể về một KIỂU NGƯỜI, "
    "một cảm xúc, một thói quen, một nét tính cách — và giải thích nó bằng tâm lý/não bộ (\"người như "
    "thế này thì thật ra…\"). Kể cả khi tiêu đề không có chữ 心理, kể cả kênh tự gọi mình là 雑学, kể cả "
    "đề tài tiền bạc/nhà cửa/tuổi tác NẾU trọng tâm là tâm lý con người (\"tâm lý người giàu\", \"vì sao "
    "người thích ở nhà\").")

#: Mô hình cho lượt ĐỌC NGHĨA. ShopAPI tính CÙNG GIÁ cho sonnet/opus/fable (đo `GET /v1/models`
#: 29/09/2026) — chủ dự án: "đừng tiếc token" → dùng bậc mạnh nhất.
MO_HINH_LOC_NGHIA = "claude-fable-5"

DE_BAI_TAM_LY = (
    "Bạn lọc NGUỒN cho một kênh YouTube tiếng Nhật làm theo lối remake (xem video đối thủ đã thắng rồi "
    "viết lại kịch bản). Bạn nhận một danh sách tiêu đề video (kèm tên kênh). Với MỖI tiêu đề, ĐỌC "
    "NGHĨA — không dò từ khoá — và trả lời: video này có thuộc NGÁCH của kênh không.\n\n"
    "NGÁCH:\n{ngach}\n\n"
    "'dung' = trọng tâm video là thứ của ngách trên (kể cả khi không có chữ nào quen thuộc).\n"
    "'lech' = trọng tâm là thứ khác: giải trí, tin tức, thể thao, phim, nhạc, game, nấu ăn, mẹo vặt "
    "thuần tuý, đầu tư/tài chính dạy cách làm, sức khoẻ thể chất, chuyện người nổi tiếng, 雑学 không "
    "dính tới tâm lý con người, trò chơi 心理テスト, tóm tắt sách, video tổng hợp/cắt clip.\n\n"
    "Tên kênh chỉ là gợi ý bối cảnh — một kênh 雑学 vẫn có video đúng ngách, một kênh 心理 vẫn có video lệch.\n\n"
    "Trả về JSON duy nhất dạng {{\"1\": \"dung\", \"2\": \"lech\", …}} theo số thứ tự, đủ mọi số. Không giải thích."
)

#: 01/10/2026 — đề bài lọc cho NGÁCH KHÁC ngách mặc định (khởi tạo ngách bằng AI, khuôn `_KHUON`).
#: `DE_BAI_TAM_LY` ở trên liệt kê "nấu ăn, mẹo vặt…" là LỆCH — đúng cho tâm lý Nhật, nhưng giết
#: sạch nguồn của một kênh nấu ăn. Ngách khác: cái gì lệch là do `mo_ta_cho_loc_ai` của chính nó nói.
DE_BAI_NGACH = (
    "Bạn lọc NGUỒN cho một kênh YouTube {tieng} làm theo lối remake (xem video đối thủ đã thắng rồi "
    "viết lại kịch bản). Bạn nhận một danh sách tiêu đề video (kèm tên kênh). Với MỖI tiêu đề, ĐỌC "
    "NGHĨA — không dò từ khoá — và trả lời: video này có thuộc NGÁCH của kênh không.\n\n"
    "NGÁCH:\n{ngach}\n\n"
    "'dung' = trọng tâm video là thứ của ngách trên (kể cả khi không có chữ nào quen thuộc).\n"
    "'lech' = trọng tâm là thứ khác ngách trên (xem phần 'không thuộc ngách' nếu có), hoặc là Shorts, "
    "video tổng hợp/cắt clip, tóm tắt, reup.\n\n"
    "Tên kênh chỉ là gợi ý bối cảnh — một kênh tạp nham vẫn có video đúng ngách, một kênh đúng ngách vẫn "
    "có video lệch.\n\n"
    "Trả về JSON duy nhất dạng {{\"1\": \"dung\", \"2\": \"lech\", …}} theo số thứ tự, đủ mọi số. Không giải thích."
)


def de_bai_loc_cho(goc: str, kenh: str) -> str:
    """Khuôn đề bài lọc nghĩa của kênh (còn chỗ `{ngach}`): ngách mặc định → `DE_BAI_TAM_LY` nguyên
    văn; ngách khác → `DE_BAI_NGACH` theo tiếng của kênh. Hỏng → `DE_BAI_TAM_LY`."""
    try:
        from . import ho_so_ngach  # noqa: PLC0415

        hs = ho_so_ngach.doc_ngach(goc, kenh)
        if ho_so_ngach.la_ngach_mac_dinh(hs):
            return DE_BAI_TAM_LY
        tieng = ho_so_ngach.ten_tieng(ngon_ngu_kenh(goc, kenh) or hs.ngon_ngu()) or "cùng tiếng với kênh"
        return DE_BAI_NGACH.replace("{tieng}", tieng)
    except Exception:  # noqa: BLE001
        return DE_BAI_TAM_LY


#: Ngữ cảnh cho `phan_loai_bang_ai` khi nơi gọi (mot_nut: `lambda tds: phan_loai_bang_ai(client,
#: tds)`) không truyền: `hoan_thien` đặt `{"ngach": …, "kenh_cua": {tiêu đề: tên kênh}}` quanh
#: đúng lời gọi `goi_ai` của nó. Dùng contextvar để không phải sửa chữ ký hàm của nơi gọi.
_NGU_CANH_AI: "contextvars.ContextVar[Optional[Dict[str, Any]]]" = contextvars.ContextVar(
    "trang_chu_ngu_canh_ai", default=None)


def mo_ta_ngach_cho_ai(goc: str, kenh: str) -> str:
    """Mô tả ngách cho lời nhắc lọc — `ngach.yaml` của nhóm (`mo_ta_ngach`, `dang_thang`,
    `mo_ta_cho_loc_ai`) nếu có, không thì `MO_TA_NGACH_MAC_DINH`; cộng một câu về TIẾNG của kênh
    (đo 29/09/2026: không nói thì AI nhận cả video tâm lý tiếng Anh/Hàn là "đúng"). Không ném lỗi."""
    mo_ta = MO_TA_NGACH_MAC_DINH
    try:
        from . import ho_so_ngach  # noqa: PLC0415

        hs = ho_so_ngach.doc_ngach(goc, kenh)
        if hs.co():
            tho = ho_so_ngach.doc_ngach_tho(goc, hs.nhom) or {}
            phan = [x for x in (hs.mo_ta_ngach, str(tho.get("mo_ta_cho_loc_ai") or "").strip(),
                                ("Dạng thắng: " + hs.dang_thang) if hs.dang_thang else "") if x]
            if phan:
                mo_ta = "\n".join(phan)
    except Exception:  # noqa: BLE001
        pass
    try:
        # 30/09/2026 — kênh bật kenh.yaml `cho_phep_tep_gia` (tệp người già): nói rõ với LLM rằng
        # nhắm người già là ĐÚNG tệp, kèm luật chọn riêng của kênh. Kênh không bật → "" (như cũ).
        from .phan_tuyen import mo_ta_tep_gia  # noqa: PLC0415

        them = mo_ta_tep_gia(goc, kenh)
        if them:
            mo_ta += "\n" + them
    except Exception:  # noqa: BLE001
        pass
    lang = ngon_ngu_kenh(goc, kenh)
    if lang:
        if lang.startswith("ja"):
            ten = "tiếng Nhật"
        else:
            # 01/10/2026: tên tiếng thay cho mã trần ("vi" → "tiếng Việt") — tiếng Nhật giữ nguyên câu cũ.
            try:
                from .ho_so_ngach import ten_tieng  # noqa: PLC0415

                ten = ten_tieng(lang) or lang
            except Exception:  # noqa: BLE001
                ten = lang
        mo_ta += "\nChỉ nhận video viết/nói bằng tiếng của kênh ({0}); tiêu đề tiếng khác → 'lech'.".format(ten)
    return mo_ta


def phan_loai_bang_ai(client, tieu_de: Sequence[str], *,
                      goi: Optional[Callable[..., str]] = None,
                      so_moi_lo: int = 25,
                      on_log: Optional[Callable[[str], None]] = None,
                      mo_ta_ngach: Optional[str] = None,
                      kenh_cua: Optional[Dict[str, str]] = None,
                      mo_hinh: str = MO_HINH_LOC_NGHIA) -> Dict[str, str]:
    """Phân 'dung'/'lech' theo NGHĨA cho một danh sách tiêu đề — **tốn tiền**.

    `mo_ta_ngach`/`kenh_cua` (tiêu đề → tên kênh) thiếu thì lấy từ ngữ cảnh `hoan_thien` đặt
    (`_NGU_CANH_AI`), không có nữa thì mô tả ngách mặc định. Một lô hỏng thì để trống lô ấy và đi
    tiếp — không kéo sập cả lượt (cùng nết với `phan_tuyen.gan_tuyen`).
    """
    from .goi_van_ban import goi_van_ban, loc_json  # noqa: PLC0415

    goi = goi or goi_van_ban
    nc = _NGU_CANH_AI.get() or {}
    if mo_ta_ngach is None:
        mo_ta_ngach = str(nc.get("ngach") or "") or MO_TA_NGACH_MAC_DINH
    if kenh_cua is None:
        kenh_cua = nc.get("kenh_cua") or {}
    # 01/10/2026: `hoan_thien` đặt khuôn đề bài theo ngách của kênh (`de_bai_loc_cho`) — không có
    # ngữ cảnh (nơi gọi cũ, bài kiểm) thì đề bài tâm lý cũ, nguyên văn.
    de_bai = str(nc.get("de_bai") or DE_BAI_TAM_LY).format(ngach=mo_ta_ngach)
    ra: Dict[str, str] = {}
    tds = [str(t) for t in tieu_de if str(t).strip()]
    for dau in range(0, len(tds), so_moi_lo):
        lo = tds[dau:dau + so_moi_lo]
        chu = "\n".join("{0}. {1}{2}".format(i + 1, t, "  〔kênh: {0}〕".format(kenh_cua[t]) if kenh_cua.get(t) else "")
                        for i, t in enumerate(lo))
        try:
            tho = goi(client, [{"role": "system", "content": de_bai},
                               {"role": "user", "content": chu}],
                      toi_da_token=12 * len(lo) + 80, on_log=on_log, mo_hinh=mo_hinh)
            du = loc_json(tho)
        except Exception as loi:  # noqa: BLE001
            if on_log is not None:
                on_log("  lô phân loại tâm lý hỏng, bỏ qua: {0}".format(str(loi)[:80]))
            continue
        if not isinstance(du, dict):
            continue
        for k, v in du.items():
            try:
                i = int(str(k).strip()) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(lo) and str(v).strip().lower() in ("dung", "lech"):
                ra[lo[i]] = str(v).strip().lower()
    return ra


def _them_hop_thu(goc: str, kenh: str, links: Sequence[str]) -> int:
    """Nối link kênh vào hộp thư (`doi-thu.txt`), khử trùng — cùng luật với `tram.nhan_doi_thu`."""
    cu = so.doc_doi_thu(goc, kenh)
    da_co = {d.strip() for d in cu.splitlines() if d.strip()}
    moi = []
    for l in links:
        l = str(l).strip()
        if l and l not in da_co:
            moi.append(l)
            da_co.add(l)
    if moi:
        so.luu_doi_thu(goc, kenh, (cu.strip() + "\n" if cu.strip() else "") + "\n".join(moi))
    return len(moi)


def _phan_loai_theo_nghia(goc: str, kenh: str, dong: List[Dict[str, str]], bo_nho: Dict[str, dict],
                          dem: Dict[str, int], kenh_dung: Dict[str, str], *,
                          goi_ai: Callable[[Sequence[str]], Dict[str, str]], lang: str,
                          bo_qua_zatsugaku: bool, nho_ai: bool, log: Callable[[str], None],
                          toi_da: int, bo_tu: Optional[Dict[str, List[str]]] = None) -> None:
    """Đường THEO NGHĨA của `hoan_thien` (xem đầu tệp). Sửa `dong`/`dem`/`kenh_dung` tại chỗ.

    1. Tiền lọc hiển nhiên (`phan_loai_tien_loc`) → loại, không hỏi AI.
    2. Còn lại: phán quyết từ khoá (`phan_loai_tam_ly`) giữ làm ĐƯỜNG LÙI.
    3. Hỏi AI: mọi tiêu đề lưỡng lự + tối đa `toi_da` tiêu đề từ khoá đã phân (mới quét nhất
       trước) — trừ tiêu đề kho nhóm đã có câu trả lời ≤90 ngày (dùng lại, không hỏi lại).
    4. Phán quyết AI thắng; không có (AI lỗi / vượt trần) thì dùng từ khoá.
    """
    theo_td: Dict[str, List[Dict[str, str]]] = {}
    tu_khoa: Dict[str, str] = {}
    moi_nhat: Dict[str, str] = {}
    kenh_cua: Dict[str, str] = {}
    for d in dong:
        ma = (d.get("Mã video") or "").strip()
        kq = bo_nho.get(ma) or {}
        td = d.get("Tiêu đề") or ""
        if phan_loai_tien_loc(td, d.get("Kênh", ""), d.get("Link kênh", ""), lang,
                              short=d.get("Short") == "x", **_chon(bo_tu, _KHOA_TIEN_LOC)) == "lech":
            d["Bị loại"] = d.get("Bị loại") or "không tâm lý"
            dem["loai"] += 1
            continue
        khoa = td or ma
        theo_td.setdefault(khoa, []).append(d)
        if khoa not in tu_khoa:
            tu_khoa[khoa] = phan_loai_tam_ly(td, kq.get("tags", ()), kq.get("mo_ta", ""), d.get("Kênh", ""),
                                             d.get("Link kênh", ""), lang, bo_qua_zatsugaku=bo_qua_zatsugaku,
                                             **_chon(bo_tu, _KHOA_TAM_LY))
        moi_nhat[khoa] = max(moi_nhat.get(khoa, ""), str(d.get("Lúc quét") or ""))
        if d.get("Kênh") and khoa not in kenh_cua:
            kenh_cua[khoa] = str(d.get("Kênh"))
    ai: Dict[str, str] = {}
    # Dòng chưa tra được tiêu đề (khoá là mã video) không có gì để AI đọc — để từ khoá/lượt sau.
    can_hoi = [t for t in theo_td if t and (theo_td[t][0].get("Tiêu đề") or "").strip()]
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    if nho_ai and can_hoi:
        ai = ncc.ai_trang_chu_da_biet(goc, kenh, can_hoi)
        can_hoi = [t for t in can_hoi if t not in ai]
    lung_td = [t for t in can_hoi if tu_khoa.get(t) == "lung"]
    da_phan = sorted((t for t in can_hoi if tu_khoa.get(t) != "lung"), key=lambda t: moi_nhat.get(t, ""),
                     reverse=True)
    dem["de_luot_sau"] = max(0, len(da_phan) - max(0, int(toi_da)))
    can_hoi = lung_td + da_phan[:max(0, int(toi_da))]
    dem["ai_hoi"] = len(can_hoi)
    if ai or can_hoi:
        log("  AI đọc nghĩa: dùng lại {0} tiêu đề đã hỏi, hỏi mới {1} ({2} lưỡng lự + {3} từ khoá đã phân; "
            "để lượt sau {4}).".format(len(ai), len(can_hoi), len(lung_td), len(can_hoi) - len(lung_td),
                                       dem["de_luot_sau"]))
    if can_hoi:
        tok = _NGU_CANH_AI.set({"ngach": mo_ta_ngach_cho_ai(goc, kenh), "kenh_cua": kenh_cua,
                                "de_bai": de_bai_loc_cho(goc, kenh)})
        try:
            moi = goi_ai(can_hoi) or {}
        except Exception as loi:  # noqa: BLE001 — AI hỏng: đường lùi là từ khoá
            log("  AI đọc nghĩa hỏng — dùng phán quyết từ khoá cho lượt này: {0}".format(str(loi)[:90]))
            moi = {}
        finally:
            _NGU_CANH_AI.reset(tok)
        moi = {t: v for t, v in moi.items() if v in ("dung", "lech")}
        if len(moi) < len(can_hoi):
            log("  AI trả {0}/{1} tiêu đề — phần còn lại dùng từ khoá.".format(len(moi), len(can_hoi)))
        if nho_ai and moi:
            try:
                ncc.ai_trang_chu_ghi(goc, kenh, moi)
            except OSError:
                pass
        ai.update(moi)
    lat = 0
    so_lung = 0
    for td, ds in theo_td.items():
        kw = tu_khoa.get(td, "lung")
        kq_ai = ai.get(td)
        cuoi = kq_ai if kq_ai in ("dung", "lech") else kw
        if kq_ai in ("dung", "lech") and kw in ("dung", "lech") and kq_ai != kw:
            lat += 1
        if cuoi == "lung":
            so_lung += 1
        for d in ds:
            if cuoi == "dung":
                d["Bị loại"] = ""
                dem["tam_ly"] += 1
                if d.get("Link kênh"):
                    kenh_dung[d["Link kênh"]] = d.get("Kênh", "")
            elif cuoi == "lech":
                d["Bị loại"] = "không tâm lý (AI)" if kq_ai == "lech" else (d.get("Bị loại") or "không tâm lý")
                dem["loai"] += 1
    dem["lung"] = so_lung
    dem["ai_lat"] = lat
    if lat:
        log("  AI đọc nghĩa LẬT {0} phán quyết từ khoá (đúng→lệch hoặc lệch→đúng).".format(lat))


def hoan_thien(goc: str, kenh: str, *, lang: str = "",
               tra: Callable[..., Dict[str, str]] = tra_video,
               goi_ai: Optional[Callable[[Sequence[str]], Dict[str, str]]] = None,
               cancel: Optional[threading.Event] = None,
               on_log: Optional[Callable[[str], None]] = None,
               toi_da_tra: int = 400,
               bo_qua_zatsugaku: bool = False,
               nho_ai: bool = False,
               theo_nghia: bool = True,
               toi_da_ai_theo_nghia: int = TOI_DA_AI_THEO_NGHIA) -> Dict[str, int]:
    """Việc "phía sau" mà chủ dự án nói: tra → lọc tâm lý → kênh vào hộp thư.

    `tra`     — tách ra để test dựng dữ liệu giả không cần mạng.
    `goi_ai`  — nhận danh sách tiêu đề, trả `{tiêu đề: 'dung'|'lech'}`. `None` = không gọi AI:
                y như cũ — từ khoá phân, phần lưỡng lự để nguyên (kênh KHÔNG vào hộp thư).
    `theo_nghia` (mặc định bật, chỉ có tác dụng khi có `goi_ai`) — xem "THEO NGHĨA" đầu tệp: từ
                khoá chỉ còn tiền lọc ca hiển nhiên + đường lùi; AI đọc nghĩa cả phần từ khoá đã
                phân (tối đa `toi_da_ai_theo_nghia` tiêu đề mới mỗi lượt). `False` = đường cũ:
                AI chỉ thấy phần lưỡng lự.
    Trả số đếm để giao diện báo: video · đã tra · tâm lý · lưỡng lự · loại · kênh mới (đường theo
    nghĩa thêm `ai_hoi`, `ai_lat`, `de_luot_sau`).
    """
    lang = lang or ngon_ngu_kenh(goc, kenh)
    # 30/09/2026, Đợt 4 (A4): bộ từ lọc theo hồ sơ ngách của nhóm — tam-ly-nhat là bản sao đúng các
    # hằng ở đầu tệp; kênh không nhóm → hằng cũ.
    bo_tu = bo_tu_ngach(goc, kenh)
    dong = doc(goc, kenh)
    bo_nho = _doc_tra(goc, kenh)
    dem = {"video": len(dong), "da_tra": 0, "tam_ly": 0, "lung": 0, "loai": 0, "kenh_moi": 0,
           "kenh_the_tuoi": 0}
    if not dong:
        return dem

    def log(m):
        if on_log is not None:
            on_log(m)

    # 1) tra những mã chưa có trong bộ nhớ — mỗi mã một lần, cả đời
    can = []
    for d in dong:
        ma = (d.get("Mã video") or "").strip()
        if ma and ma not in bo_nho and ma not in can:
            can.append(ma)
    can = can[:toi_da_tra]
    for i, ma in enumerate(can, 1):
        if cancel is not None and cancel.is_set():
            break
        kq = tra(ma, lang=lang, cancel=cancel) or {}
        bo_nho[ma] = kq
        dem["da_tra"] += 1
        if i % 10 == 0:
            log("  đã tra {0}/{1} video trang chủ…".format(i, len(can)))
            _luu_tra(goc, kenh, bo_nho)          # rớt giữa chừng cũng không mất phần đã tra
    _luu_tra(goc, kenh, bo_nho)

    # 2) đắp vào bảng + phân loại bằng từ khoá
    kenh_dung: Dict[str, str] = {}      # link kênh → tên (để đếm và ghi nhật ký)
    lung: Dict[str, List[Dict[str, str]]] = {}
    for d in dong:
        ma = (d.get("Mã video") or "").strip()
        kq = bo_nho.get(ma) or {}
        if kq:
            for k_csv, k_kq in (("Tiêu đề", "tieu_de"), ("Kênh", "ten_kenh"), ("Link kênh", "link_kenh"),
                                ("Lượt xem", "luot_xem"), ("Đăng", "dang"), ("Dài", "dai")):
                if not (d.get(k_csv) or "").strip() and kq.get(k_kq):
                    d[k_csv] = str(kq[k_kq])
            if kq.get("short"):
                d["Short"] = "x"
    if goi_ai is not None and theo_nghia:
        _phan_loai_theo_nghia(goc, kenh, dong, bo_nho, dem, kenh_dung, goi_ai=goi_ai, lang=lang,
                              bo_qua_zatsugaku=bo_qua_zatsugaku, nho_ai=nho_ai, log=log,
                              toi_da=toi_da_ai_theo_nghia, bo_tu=bo_tu)
        dong_cu: List[Dict[str, str]] = []
    else:
        dong_cu = dong
    for d in dong_cu:
        ma = (d.get("Mã video") or "").strip()
        kq = bo_nho.get(ma) or {}
        loai = phan_loai_tam_ly(d.get("Tiêu đề", ""), kq.get("tags", ()), kq.get("mo_ta", ""),
                                d.get("Kênh", ""), d.get("Link kênh", ""), lang,
                                bo_qua_zatsugaku=bo_qua_zatsugaku, **_chon(bo_tu, _KHOA_TAM_LY))
        if d.get("Short") == "x" and loai == "dung":
            loai = "lech"                 # Short không remake được — không phải nguồn
        if loai == "lech":
            d["Bị loại"] = d.get("Bị loại") or "không tâm lý"
            dem["loai"] += 1
        elif loai == "dung":
            d["Bị loại"] = ""
            dem["tam_ly"] += 1
            if d.get("Link kênh"):
                kenh_dung[d["Link kênh"]] = d.get("Kênh", "")
        else:
            lung.setdefault(d.get("Tiêu đề") or ma, []).append(d)
    if dong_cu:
        dem["lung"] = len(lung)

    # 3) phần lưỡng lự — chỉ khi được phép tốn tiền (đường cũ; đường theo nghĩa đã làm ở trên)
    if lung and goi_ai is not None:
        # (29/09/2026, #3) `nho_ai`: tiêu đề đã hỏi AI (kho nhóm, ≤90 ngày) không hỏi
        # lại — trước đây ~281 tiêu đề lưỡng lự đi hỏi lại MỖI lượt, không lưu gì.
        phan: Dict[str, str] = {}
        can_hoi = list(lung.keys())
        if nho_ai:
            from . import nghien_cuu_chung as ncc  # noqa: PLC0415

            phan = ncc.ai_trang_chu_da_biet(goc, kenh, can_hoi)
            can_hoi = [td for td in can_hoi if td not in phan]
            if phan:
                log("  AI phân loại: {0} tiêu đề đã hỏi trước đây (dùng lại), hỏi mới {1}."
                    .format(len(phan), len(can_hoi)))
        if can_hoi:
            # 01/10/2026: ngách KHÁC ngách mặc định → đề bài + mô tả theo hồ sơ ngách (đường cũ không
            # đặt ngữ cảnh, nên kênh tâm lý Nhật đi y hệt trước).
            tok_cu = None
            de_bai_cu = de_bai_loc_cho(goc, kenh)
            if de_bai_cu is not DE_BAI_TAM_LY:
                tok_cu = _NGU_CANH_AI.set({"ngach": mo_ta_ngach_cho_ai(goc, kenh), "de_bai": de_bai_cu})
            try:
                moi = goi_ai(can_hoi) or {}
            except Exception as loi:  # noqa: BLE001 — AI hỏng thì phần lưỡng lự để nguyên
                log("  AI phân loại hỏng, để nguyên phần lưỡng lự: {0}".format(str(loi)[:90]))
                moi = {}
            finally:
                if tok_cu is not None:
                    _NGU_CANH_AI.reset(tok_cu)
            if nho_ai and moi:
                try:
                    ncc.ai_trang_chu_ghi(goc, kenh, moi)
                except OSError:
                    pass
            phan.update(moi)
        for td, ds in lung.items():
            kq = phan.get(td)
            if kq in ("dung", "lech"):
                # `dem["lung"]` đếm TIÊU ĐỀ (len(lung)) — trừ một lần mỗi tiêu đề,
                # không phải mỗi dòng (bản cũ ra số âm, vd. "lưỡng lự -290").
                dem["lung"] -= 1
            for d in ds:
                if kq == "dung":
                    d["Bị loại"] = ""
                    dem["tam_ly"] += 1
                    if d.get("Link kênh"):
                        kenh_dung[d["Link kênh"]] = d.get("Kênh", "")
                elif kq == "lech":
                    d["Bị loại"] = "không tâm lý (AI)"
                    dem["loai"] += 1

    # 4) thẻ tuổi của kênh nguồn — ghi để bảng chấm dùng, không tự loại
    for link in list(kenh_dung):
        tags_kenh = " ".join(" ".join(kq.get("tags", ())) + " " + kq.get("mo_ta", "")
                             for kq in bo_nho.values() if kq.get("link_kenh") == link)
        if any(t in tags_kenh for t in bo_tu["dau_moc_tuoi_kenh"]):
            dem["kenh_the_tuoi"] += 1

    luu(goc, kenh, dong)
    dem["kenh_moi"] = _them_hop_thu(goc, kenh, list(kenh_dung))
    log("  trang chủ: {video} video · tra {da_tra} · tâm lý {tam_ly} · lưỡng lự {lung} · "
        "loại {loai} · +{kenh_moi} kênh vào hộp thư ({kenh_the_tuoi} kênh có thẻ tuổi)".format(**dem))
    return dem


def tom_tat(goc: str, kenh: str) -> str:
    """Một dòng cho giao diện: lượt quét gần nhất là gì."""
    dong = doc(goc, kenh)
    if not dong:
        return "chưa có lượt quét trang chủ nào"
    # Một ĐỢT quét = extension 2.6.1 tải lại trang chủ 3 lượt, gửi 3 gói cách nhau 1–2 phút →
    # "Lúc quét" khác nhau vài phút. Gom mọi dòng trong 10 phút quanh mốc mới nhất thành một đợt.
    from datetime import datetime, timedelta  # noqa: PLC0415

    def _gio(ch):
        try:
            return datetime.strptime(ch, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    luc = max((d.get("Lúc quét") or "") for d in dong)
    moc = _gio(luc)
    gan = [d for d in dong if (d.get("Lúc quét") or "") == luc or
           (moc and _gio(d.get("Lúc quét") or "") and moc - _gio(d["Lúc quét"]) <= timedelta(minutes=10))]
    chua = sum(1 for d in gan if not (d.get("Kênh") or "").strip())
    loai = sum(1 for d in gan if (d.get("Bị loại") or "").strip())
    theo_luot = {}
    for d in gan:
        k = (d.get("Lượt tải") or "").strip()
        if k:
            theo_luot[k] = theo_luot.get(k, 0) + 1
    them = ""
    if len(theo_luot) > 1:
        them = " · mới theo lượt tải " + "/".join(str(theo_luot[k]) for k in sorted(theo_luot))
    return "đợt {0}: {1} video · {2} chưa tra · {3} bị loại{4}".format(luc, len(gan), chua, loai, them)
