"""ĐỘ ĐỘC ĐÁO KỊCH BẢN — đo mức chép nguồn + cổng viết lại trong khâu kịch bản (15/10/2026).

═══ VÌ SAO ═══ (`workspace/chan-doan/han-che-video-15-10.md`, mục "Làm lại sát nguồn")

116 lượt có nguồn cùng tiếng: trung vị 21% chuỗi 10 ký tự của `1-kich-ban.txt` có Y NGUYÊN trong `0-tu-lieu.txt`;
28 lượt ≥ 40%, 15 lượt ≥ 60%, cao nhất 91%. Mức nền giữa hai lượt không liên quan ~1%. Chép không giúp hiển thị
(Spearman +0,13, n = 48). Chính sách YPP "nội dung không xác thực / tái sử dụng" (07/2025) gọi đúng tên loại này —
rủi ro lớn nhất lúc xét kiếm tiền. Nên: đo, và lượt nào chép quá `NGUONG_VIET_LAI` thì viết lại bằng giọng kênh.

═══ ĐO ═══ `do_trung(kich_ban, nguon)`: chuẩn hoá (NFKC, chữ thường, bỏ thẻ cảm xúc, bỏ khoảng trắng / dấu câu / ký
hiệu) rồi đếm tỉ lệ cửa sổ `N` ký tự của kịch bản có y nguyên trong nguồn; nối các cửa sổ trùng liền nhau thành ĐOẠN
CHÉP (in lại bằng chữ gốc của kịch bản). Thuần, không mạng, ~ms. Không cần bộ tách từ (tiếng Nhật viết liền).
Giới hạn: chỉ bắt chép CHỮ — nguồn khác tiếng (bản dịch từng câu) không đo được, ghi cờ `khac_tieng`.

═══ XUYÊN NGÔN NGỮ ═══ (16/10/2026) 12/126 lượt có nguồn tiếng Anh, kịch bản dịch từng câu — đo ký tự ra ~0. Nguồn
khác tiếng: dịch nguồn MỘT lần qua phễu chữ thường (cache `0-tu-lieu-ja.txt` trong thư mục lượt), rồi `do_xuyen` gióng
câu (mỗi câu kịch bản ↔ câu / cặp câu liền của bản dịch, độ phủ 2-gram ký tự trọng số IDF) → tỉ lệ câu dịch sát. Hiệu
chỉnh trên 12 lượt nguồn Anh + 126 lượt nguồn Nhật: xem `NGUONG_XUYEN_VIET_LAI`. Cùng vòng viết lại, tối đa 2 lần;
dịch hỏng → ghi chú, đi tiếp.

═══ CỔNG ═══ `qua_cong(...)` (gọi từ `auto_khau._khau_kich_ban`, sau khi bài đã chốt và nắn độ dài, TRƯỚC rà soát
`3-sua.md` — nên tách câu, thẻ cảm xúc, `---` và giọng đọc đều đi trên bản đã qua cổng):
  1. trùng ≤ `NGUONG_VIET_LAI` → giữ nguyên;
  2. viết lại MỘT lượt qua phễu chữ thường (`_goi` → `goi_van_ban`: Claude Max, lùi ví ShopAPI), đưa các đoạn chép
     làm danh sách "không dùng lại"; đo lại; nhận bản mới khi qua kiểm (độ dài, ghi chú kỹ thuật, `---`, câu mời
     đăng ký) VÀ trùng thấp hơn;
  3. vẫn > `NGUONG_CHAN` → thử thêm MỘT lần từ bản tốt nhất; vẫn trượt → cảnh báo rồi ĐI TIẾP (luật chủ: thử lại,
     không bỏ lượt). Biên bản `1-doc-dao.json`; kênh tắt bằng `doc_dao: false` trong `kenh.yaml` (vẫn đo, không viết).

    python -X utf8 -m core.do_doc_dao --kenh TL2-T7 [--n 20] [--goc <gốc tool>]     # bảng mức chép, chỉ đọc
    ... [--xuyen] [--dich N --cache-dich <thư mục>]   # thêm cột câu sát; cho gọi AI dịch ≤ N nguồn (cache ngoài PROJECTS)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

GOC = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Độ dài cửa sổ so (ký tự sau chuẩn hoá) — đúng thước của bản chẩn đoán 15/10 và `viet_nhieu_ban.trung_nguyen_van`.
N = 10
#: Trên ngưỡng này thì viết lại (bản chẩn đoán: "chặn khi trên 15%, nhắm dưới 10%").
NGUONG_VIET_LAI = 0.15
#: Sau lượt viết lại mà còn trên ngưỡng này thì thử thêm một lần; vẫn trên → cảnh báo, đi tiếp.
NGUONG_CHAN = 0.30
SO_LAN_TOI_DA = 2
#: Số đoạn chép đưa vào lời nhắc ("đừng dùng lại") và trần chữ mỗi đoạn.
TOI_DA_DOAN = 40
TRAN_DOAN = 160
TEP = "1-doc-dao.json"
TEP_NHAP = "1-nhap-doc-dao.txt"
TEP_KB, TEP_NGUON = "1-kich-ban.txt", "0-tu-lieu.txt"

_THE = re.compile(r"\[[a-z][a-z \-]*\]")
_DONG_NGAT = re.compile(r"(?m)^\s*[-_*]{3,}\s*$")


# ── 1. ĐO ────────────────────────────────────────────────────────────────────

def chuan_hoa(chu: str) -> Tuple[str, List[int]]:
    """(chuỗi chuẩn hoá, vị trí ký tự gốc của từng ký tự chuẩn hoá). Giữ chữ/số/dấu phụ; bỏ khoảng trắng, dấu câu,
    ký hiệu, ký tự điều khiển, thẻ cảm xúc `[sighs]`. NFKC từng ký tự (ｱ→ア, ＡＢ→ab) để chỉ mục về gốc còn đúng."""
    chu = _THE.sub(lambda m: " " * len(m.group()), chu or "")
    ra: List[str] = []
    vt: List[int] = []
    for i, c in enumerate(chu):
        for x in unicodedata.normalize("NFKC", c):
            if unicodedata.category(x)[0] in "LMN":
                ra.append(x.lower())
                vt.append(i)
    return "".join(ra), vt


def _lop_chu(c: str) -> str:
    o = ord(c)
    if 0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x9FFF or 0xAC00 <= o <= 0xD7AF or 0xF900 <= o <= 0xFAFF:
        return "cjk"
    return "latin" if o < 0x2500 else "khac"


def lop_chu_chinh(chu_chuan: str) -> str:
    """Lớp chữ chiếm đa số ("cjk" / "latin" / "khac") — để biết nguồn và kịch bản có cùng tiếng không."""
    if not chu_chuan:
        return ""
    dem: Dict[str, int] = {}
    for c in chu_chuan[:4000]:
        lop = _lop_chu(c)
        dem[lop] = dem.get(lop, 0) + 1
    return max(dem, key=dem.get)


def do_trung(kich_ban: str, nguon: str, n: int = N, toi_da: int = 5) -> Dict[str, Any]:
    """`{ti_le, so_doan, vi_du, dai_nhat, ky_tu_chep, so_cua_so, khac_tieng}`.

    `ti_le` = tỉ lệ cửa sổ `n` ký tự (sau chuẩn hoá) của kịch bản có y nguyên trong nguồn (0..1). `so_doan` = số đoạn
    chép (cửa sổ trùng nối liền / chồng nhau). `vi_du` = `toi_da` đoạn dài nhất, in bằng chữ GỐC của kịch bản.
    `dai_nhat` / `ky_tu_chep` tính trên chữ chuẩn hoá. `khac_tieng` = nguồn khác lớp chữ (bản dịch: số đo vô nghĩa)."""
    a, vt = chuan_hoa(kich_ban)
    b, _ = chuan_hoa(nguon)
    ra: Dict[str, Any] = {"ti_le": 0.0, "so_doan": 0, "vi_du": [], "dai_nhat": 0, "ky_tu_chep": 0,
                          "so_cua_so": max(0, len(a) - n + 1), "khac_tieng": bool(a and b and lop_chu_chinh(a) != lop_chu_chinh(b))}
    if len(a) < n or len(b) < n:
        return ra
    kho = {b[i:i + n] for i in range(len(b) - n + 1)}
    tong = len(a) - n + 1
    doan: List[List[int]] = []
    trung = 0
    for i in range(tong):
        if a[i:i + n] in kho:
            trung += 1
            if doan and i <= doan[-1][1]:          # chồng / liền đoạn trước → nối
                doan[-1][1] = i + n
            else:
                doan.append([i, i + n])
    ra.update(ti_le=round(trung / tong, 4), so_doan=len(doan), ky_tu_chep=sum(e - s for s, e in doan),
              dai_nhat=max((e - s for s, e in doan), default=0))
    goc = kich_ban or ""
    for s, e in sorted(doan, key=lambda x: x[0] - x[1])[:max(0, toi_da)]:
        chu = " / ".join(x.strip() for x in goc[vt[s]:vt[e - 1] + 1].splitlines() if x.strip())
        ra["vi_du"].append(chu if len(chu) <= TRAN_DOAN else chu[:TRAN_DOAN] + "…")
    return ra


# ── 1b. ĐO XUYÊN NGÔN NGỮ (16/10/2026) ────────────────────────────────────────
#
# Nguồn tiếng Anh: kịch bản là bản dịch TỪNG CÂU → không có chuỗi ký tự nào trùng. Dịch nguồn MỘT lần sang tiếng
# của kịch bản (`0-tu-lieu-ja.txt`), rồi GIÓNG CÂU: mỗi câu kịch bản tìm câu (hoặc cặp câu liền) của bản dịch có
# độ phủ 2-gram ký tự CAO NHẤT, trọng số IDF trên bản dịch (cụm ngữ pháp "ます/ている" gần như không đếm; từ nội dung —
# kanji, katakana, số — đếm đậm). `ti_le` = tỉ lệ câu kịch bản có câu khớp ≥ `NGUONG_CAU_XUYEN`. Hai bản dịch ĐỘC
# LẬP của cùng một câu tiếng Anh chung phần lớn từ nội dung; viết lại thật thì không.

#: Một câu kịch bản "khớp sát" khi ≥ ngần này trọng số 2-gram của nó có trong một câu (cặp câu liền) bản dịch.
NGUONG_CAU_XUYEN = 0.5
#: Tỉ lệ câu khớp sát trên ngưỡng này → viết lại. Hiệu chỉnh 16/10 (chỉ đọc, bản dịch Claude Max):
#:   12 lượt nguồn Anh (dịch từng câu): 38–82%, trung vị 60% · cặp lệch (kịch bản A × bản dịch nguồn B, 132 cặp):
#:   trung vị 0,8%, cao nhất 8,8% · bản cổng viết lại (nguồn Nhật, cùng thước): 4–8% · nguồn Nhật trùng ký tự < 5%:
#:   trung vị 14%, cao nhất 31% (so thẳng, không qua dịch — cao hơn đo xuyên). 30% bắt cả 12, chừa biên trên 8,8%.
NGUONG_XUYEN_VIET_LAI = 0.30
#: Sau lượt viết lại còn trên ngưỡng này thì thử thêm một lần; vẫn trên → cảnh báo, đi tiếp.
NGUONG_XUYEN_CHAN = 0.45
#: Câu ngắn hơn ngần này ký tự (sau chuẩn hoá) không xét — "はい。" khớp đâu cũng được.
CAU_TOI_THIEU = 8
TEP_DICH = "0-tu-lieu-ja.txt"
_TACH_CAU = re.compile(r"(?<=[。！？!?])|\n+|(?<=[.])\s+")


def tach_cau(chu: str) -> List[Tuple[str, str]]:
    """[(câu gốc, câu chuẩn hoá)] — tách theo 。！？!? / xuống dòng / dấu chấm + khoảng trắng; bỏ `---` và câu ngắn."""
    ra: List[Tuple[str, str]] = []
    for c in _TACH_CAU.split(_DONG_NGAT.sub("\n", chu or "")):
        c = (c or "").strip()
        ch = chuan_hoa(c)[0]
        if len(ch) >= CAU_TOI_THIEU:
            ra.append((c, ch))
    return ra


def _hai_gram(s: str) -> set:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def do_xuyen(kich_ban: str, nguon_dich: str, nguong_cau: float = NGUONG_CAU_XUYEN, toi_da: int = 5) -> Dict[str, Any]:
    """`{ti_le, so_cau, so_khop, diem_tb, vi_du}` — tỉ lệ câu kịch bản khớp sát một câu (cặp câu liền) của bản dịch
    nguồn. `vi_du` = câu kịch bản khớp sát nhất (chữ gốc), cho lời nhắc viết lại. Thuần, ~0,1–1 giây."""
    kb, ng = tach_cau(kich_ban), tach_cau(nguon_dich)
    ra: Dict[str, Any] = {"ti_le": 0.0, "so_cau": len(kb), "so_khop": 0, "diem_tb": 0.0, "vi_du": []}
    if not kb or not ng:
        return ra
    don = [_hai_gram(c) for _, c in ng]
    don += [don[i] | don[i + 1] for i in range(len(don) - 1)]         # cặp câu liền: kịch bản hay gộp/tách câu
    df: Dict[str, int] = {}
    for g in (g for s in don[:len(ng)] for g in s):
        df[g] = df.get(g, 0) + 1
    import math  # noqa: PLC0415

    tong = len(ng)
    idf = {g: math.log((tong + 1) / (d + 0.5)) for g, d in df.items()}
    idf_la = math.log((tong + 1) / 0.5)                                 # 2-gram không có trong bản dịch
    chi_muc: Dict[str, List[int]] = {}
    for j, s in enumerate(don):
        for g in s:
            chi_muc.setdefault(g, []).append(j)
    diem: List[Tuple[float, int]] = []
    for i, (_, c) in enumerate(kb):
        gs = _hai_gram(c)
        mau = sum(idf.get(g, idf_la) for g in gs) or 1.0
        cong: Dict[int, float] = {}
        for g in gs:
            w = idf.get(g)
            if w is None:
                continue
            for j in chi_muc.get(g, ()):
                cong[j] = cong.get(j, 0.0) + w
        diem.append((max(cong.values(), default=0.0) / mau, i))
    khop = [x for x in diem if x[0] >= nguong_cau]
    ra.update(ti_le=round(len(khop) / len(kb), 4), so_khop=len(khop),
              diem_tb=round(sum(d for d, _ in diem) / len(diem), 4))
    for d, i in sorted(khop, reverse=True)[:max(0, toi_da)]:
        chu = kb[i][0]
        ra["vi_du"].append(chu if len(chu) <= TRAN_DOAN else chu[:TRAN_DOAN] + "…")
    return ra


#: Lời nhắc dịch nguồn — dịch SÁT từng câu (đúng thứ cần so), không tóm tắt, không thêm.
LOI_NHAC_DICH = """Dịch toàn bộ văn bản dưới đây sang <<NGON_NGU>>. Dịch sát từng câu, giữ đúng thứ tự, mỗi câu một dòng; không tóm tắt, không bỏ câu, không thêm lời, không giải thích. Chỉ trả về bản dịch.

VĂN BẢN:
<<NGUON>>
"""


def ban_dich_nguon(thu_muc: str, nguon: str, dich: Callable[[str], str], ghi: Optional[Callable[[str], None]] = None,
                   ten_tep: str = TEP_DICH, khong_nuot: Tuple[type, ...] = ()) -> Tuple[str, str]:
    """(bản dịch, nguồn: 'cache' | 'moi' | 'loi: …'). Cache `<thu_muc>/0-tu-lieu-ja.txt`, dòng đầu `#nguon:<băm>` —
    nguồn đổi thì dịch lại. Gọi `dich(nguon)` hỏng / rỗng → ('', 'loi: …') (không bao giờ ném)."""
    duong = os.path.join(thu_muc, ten_tep) if thu_muc else ""
    dau = "#nguon:" + bam(nguon)
    san = doc_ban_dich(thu_muc, nguon, ten_tep)
    if san:
        return san, "cache"
    try:
        moi = (dich(nguon) or "").strip()
    except khong_nuot:
        raise
    except Exception as loi:  # noqa: BLE001 — dịch hỏng: không đo xuyên, không chặn
        return "", "loi: {0}".format(str(loi)[:160])
    if len(chuan_hoa(moi)[0]) < max(50, len(chuan_hoa(nguon)[0]) // 10):
        return "", "loi: bản dịch rỗng/quá ngắn ({0} ký tự)".format(len(moi))
    if duong:
        try:
            os.makedirs(thu_muc, exist_ok=True)
            with open(duong, "w", encoding="utf-8") as tep:
                tep.write(dau + "\n" + moi + "\n")
        except OSError as loi:
            if ghi:
                ghi("  (không ghi được bản dịch nguồn: {0})".format(str(loi)[:80]))
    return moi, "moi"


def doc_ban_dich(thu_muc: str, nguon: str, ten_tep: str = TEP_DICH) -> str:
    """Bản dịch đã cache cho ĐÚNG nguồn này ('' nếu chưa có / nguồn đã đổi). Không gọi AI."""
    cu = _doc(os.path.join(thu_muc, ten_tep)) if thu_muc else ""
    dong1, _, than = cu.partition("\n")
    return than if dong1.strip() == "#nguon:" + bam(nguon) and than.strip() else ""


def do_xuyen_cuoi(thu_muc: str, kich_ban: str, nguon: str) -> Optional[Dict[str, Any]]:
    """Đo xuyên ngôn ngữ bằng bản dịch đã cache trong thư mục lượt; chưa có bản dịch → None (không gọi AI)."""
    ban_dich = doc_ban_dich(thu_muc, nguon)
    return do_xuyen(kich_ban, ban_dich, toi_da=3) if ban_dich else None


def so_dau_ngat(chu: str) -> int:
    return len(_DONG_NGAT.findall(chu or ""))


def bam(*chu: str) -> str:
    return hashlib.sha1("\x00".join(chu).encode("utf-8")).hexdigest()[:12]


def bat(k: Any) -> bool:
    """Cổng bật cho kênh `k` (`kenh.yaml: doc_dao`, mặc định BẬT)."""
    gt = getattr(k, "doc_dao", True)
    return not (gt is False or str(gt).strip().lower() in ("false", "no", "0", "tat", "off"))


# ── 2. CỔNG VIẾT LẠI ─────────────────────────────────────────────────────────

#: Lời nhắc viết lại — KHÔNG đưa bản gốc vào (đưa là mời chép lại); chỉ đưa bản đang có + các đoạn đã chép.
LOI_NHAC_VIET_LAI = """Bạn là người kể chuyện của kênh YouTube dưới đây. Kịch bản bên dưới đang CHÉP QUÁ SÁT lời thoại một video của kênh khác: <<MUC_CHEP>>. YouTube coi đó là nội dung tái sử dụng ("đọc lại tài liệu không phải do mình tạo") — kênh có thể trượt xét kiếm tiền. Hãy VIẾT LẠI TỪNG CÂU bằng giọng riêng của kênh, bằng <<NGON_NGU>>.

GIỮ NGUYÊN:
- chủ đề, các luận điểm, sự thật, nghiên cứu đã nêu (không bịa số liệu hay nghiên cứu mới) và thứ tự các phần;
- đoạn mở đầu (hook): giữ ý và lực móc, câu đầu tiên vẫn là câu móc — chỉ đổi chữ;
- mỗi dòng chỉ có --- (dấu ngắt phần) nếu bài đang có: đúng số lượng, đúng chỗ chuyển ý tương ứng;
- câu mời đăng ký và câu hứa video tiếp (nếu bài đang có): đúng vị trí, chỉ được sửa chữ;
- độ dài: bài đang có <<CHARS_NOW>> ký tự đọc lên; bản mới phải nằm trong khoảng <<CHARS_MIN>>–<<CHARS_MAX>> ký tự.

PHẢI ĐỔI:
- mọi câu diễn đạt lại bằng lời của chính kênh: cấu trúc câu khác, từ khác, nhịp khác; không giữ cụm dài nào của bản gốc;
- thêm góc nhìn riêng của người kể kênh ở vài chỗ (cảm nhận, quan điểm, một câu kiểu "theo tôi…") — ngắn, tự nhiên, đúng giọng kênh;
- ví dụ nào lấy từ bản gốc thì thay bằng ví dụ đời thường MỚI, cụ thể, gần với cuộc sống hằng ngày của khán giả kênh (người nói <<NGON_NGU>>).

TUYỆT ĐỐI KHÔNG DÙNG LẠI các cụm / câu dưới đây (đang chép nguyên văn hoặc dịch sát bản gốc) — nói ý của chúng bằng lời khác hẳn, đổi cả cấu trúc câu:
<<DOAN_CHEP>>
<<NHAC_LAI>>
Kênh: <<CHANNEL>>
Tiêu đề video: <<TITLE>>

Chỉ trả về lời đọc của kịch bản mới — không tiêu đề, không ghi chú, không giải thích, không tạo file.

KỊCH BẢN CẦN VIẾT LẠI:
<<DRAFT>>
"""


def _mo_ta(do: Dict[str, Any], che_do: str) -> str:
    """Câu nói mức chép cho lời nhắc viết lại (`<<MUC_CHEP>>`)."""
    if che_do == "xuyen":
        return "{0:.0%} câu của nó là bản dịch sát từng câu của bản gốc tiếng nước ngoài".format(do["ti_le"])
    return "{0:.0%} chuỗi 10 ký tự của nó có y nguyên trong bản gốc".format(do["ti_le"])


def qua_cong(ban: str, nguon: str, *, viet: Optional[Callable[[str, Dict[str, Any], int, str], str]],
             kiem: Callable[[str, str], str], nguong_viet_lai: float = NGUONG_VIET_LAI,
             nguong_chan: float = NGUONG_CHAN, ghi: Optional[Callable[[str], None]] = None,
             khong_nuot: Tuple[type, ...] = (), dich: Optional[Callable[[str], str]] = None,
             thu_muc: str = "") -> Tuple[str, Dict[str, Any]]:
    """Đo `ban`; trên `nguong_viet_lai` thì gọi `viet(ban_dang_tot, so_do_cua_no, lan, nhac_lai) -> bản mới` tối đa
    `SO_LAN_TOI_DA` lần (lần 2 chỉ khi bản tốt nhất còn > `nguong_chan`); `so_do["vi_du"]` = các đoạn chép,
    `so_do["mo_ta"]` = câu nói mức chép. `kiem(moi, ban_goc) -> lý do loại` ("" = qua). Giữ bản trùng THẤP NHẤT đã
    qua kiểm. `viet=None` = kênh tắt: chỉ đo. Không bao giờ ném lỗi (trừ `khong_nuot`, vd lệnh Dừng).

    Nguồn KHÁC TIẾNG (16/10/2026): có `dich(nguon) -> bản dịch` thì dịch nguồn MỘT lần (cache `thu_muc/0-tu-lieu-ja.txt`),
    đo GIÓNG CÂU (`do_xuyen`) với ngưỡng `NGUONG_XUYEN_VIET_LAI` / `NGUONG_XUYEN_CHAN`, rồi cùng vòng viết lại. Dịch hỏng →
    ghi chú, đi tiếp (không chặn). Trả `(bản chọn, biên bản)`."""
    ghi = ghi or (lambda _s: None)
    do0 = do_trung(ban, nguon, toi_da=TOI_DA_DOAN)
    bb: Dict[str, Any] = {"truoc": do0["ti_le"], "sau": do0["ti_le"], "so_doan_truoc": do0["so_doan"],
                          "dai_nhat_truoc": do0["dai_nhat"], "vi_du_truoc": do0["vi_du"][:5], "khac_tieng": do0["khac_tieng"],
                          "lan": [], "viet_lai": False, "canh_bao": "", "che_do": "ky_tu"}
    che_do = "ky_tu"

    def do_fn(chu: str) -> Dict[str, Any]:
        return do_trung(chu, nguon, toi_da=TOI_DA_DOAN)
    if do0["khac_tieng"]:
        if dich is None:
            bb["ghi_chu"] = "nguồn khác tiếng — đo chuỗi ký tự không bắt được bản dịch, không viết lại"
            return ban, bb
        ban_dich, tt = ban_dich_nguon(thu_muc, nguon, dich, ghi, khong_nuot=khong_nuot)
        bb["xuyen"] = {"dich": tt, "tep": TEP_DICH if thu_muc and ban_dich else "", "ky_tu_dich": len(ban_dich)}
        if not ban_dich:
            bb["ghi_chu"] = "nguồn khác tiếng — dịch nguồn hỏng ({0}), không đo xuyên ngôn ngữ được, đi tiếp".format(tt)
            ghi("  độ độc đáo: nguồn khác tiếng, dịch nguồn hỏng ({0}) — bỏ qua cổng, đi tiếp.".format(tt[:100]))
            return ban, bb
        che_do, nguong_viet_lai, nguong_chan = "xuyen", NGUONG_XUYEN_VIET_LAI, NGUONG_XUYEN_CHAN

        def do_fn(chu: str) -> Dict[str, Any]:  # noqa: F811 — đo gióng câu trên bản dịch
            return do_xuyen(chu, ban_dich, toi_da=TOI_DA_DOAN)
        do0 = do_fn(ban)
        bb.update(che_do="xuyen", truoc=do0["ti_le"], sau=do0["ti_le"], so_doan_truoc=do0["so_khop"],
                  vi_du_truoc=do0["vi_du"][:5], dai_nhat_truoc=0)
        bb["xuyen"].update(truoc=do0["ti_le"], sau=do0["ti_le"], so_cau=do0["so_cau"], nguong=nguong_viet_lai)
        ghi("  độ độc đáo: nguồn khác tiếng — {0:.0%} câu kịch bản dịch sát bản gốc (bản dịch {1}).".format(
            do0["ti_le"], "có sẵn" if tt == "cache" else "mới"))
    do0["mo_ta"] = _mo_ta(do0, che_do)
    don_vi = "câu dịch sát" if che_do == "xuyen" else "trùng nguồn"
    if do0["ti_le"] <= nguong_viet_lai:
        return ban, bb
    if viet is None:
        bb["ghi_chu"] = "kênh tắt viết lại (doc_dao: false) — chỉ đo"
        ghi("  độ độc đáo: kịch bản {0} {1:.0%} — kênh tắt cổng viết lại, chỉ ghi số.".format(don_vi, do0["ti_le"]))
        return ban, bb
    tot, do_tot, nhac = ban, do0, ""
    for lan in range(1, SO_LAN_TOI_DA + 1):
        if lan > 1 and do_tot["ti_le"] <= nguong_chan:
            break
        ghi("  độ độc đáo: kịch bản {0} {1:.0%} (> {2:.0%}) — viết lại bằng giọng kênh, lần {3}/{4}…".format(
            don_vi, do_tot["ti_le"], nguong_viet_lai, lan, SO_LAN_TOI_DA))
        muc: Dict[str, Any] = {"lan": lan, "tu": "goc" if tot is ban else "ban_tot"}
        try:
            moi = (viet(tot, do_tot, lan, nhac) or "").strip()
        except khong_nuot:
            raise
        except Exception as loi:  # noqa: BLE001 — gọi AI hỏng: thử lần sau / giữ bản đang có
            moi, muc["loi"] = "", str(loi)[:160]
        do_moi = do_fn(moi) if moi else None
        if do_moi is not None:
            do_moi["mo_ta"] = _mo_ta(do_moi, che_do)
        ly_do = ("lỗi gọi AI: " + muc["loi"]) if muc.get("loi") else "bản trả về rỗng" if not moi else kiem(moi, ban)
        if not ly_do and do_moi["ti_le"] >= do_tot["ti_le"]:
            ly_do = "không bớt chép ({0:.0%} ≥ {1:.0%})".format(do_moi["ti_le"], do_tot["ti_le"])
        muc.update(ti_le=do_moi["ti_le"] if do_moi else None, ky_tu=len(moi), nhan=not ly_do, ly_do=ly_do)
        bb["lan"].append(muc)
        if ly_do:
            ghi("    → bỏ bản viết lại: {0}".format(ly_do))
            nhac = "Lần viết lại trước bị loại: {0}. Sửa đúng chỗ ấy.".format(ly_do)
        else:
            ghi("    → nhận: {0} {1:.0%} → {2:.0%}".format(don_vi, do_tot["ti_le"], do_moi["ti_le"]))
            tot, do_tot = moi, do_moi
            nhac = "Bản này đã viết lại một lần mà vẫn còn {0} — đổi mạnh tay hơn.".format(do_moi["mo_ta"])
    bb.update(sau=do_tot["ti_le"], viet_lai=tot is not ban, so_doan_sau=do_tot.get("so_doan", do_tot.get("so_khop")),
              vi_du_sau=do_tot["vi_du"][:5])
    if che_do == "xuyen":
        bb["xuyen"]["sau"] = do_tot["ti_le"]
    if do_tot["ti_le"] > nguong_chan:
        bb["canh_bao"] = "sau {0} lần viết lại kịch bản vẫn {1} {2:.0%} (> {3:.0%}) — vẫn đi tiếp".format(
            len(bb["lan"]), don_vi, do_tot["ti_le"], nguong_chan)
        ghi("  ⚠ độ độc đáo: " + bb["canh_bao"])
    return tot, bb


# ── 3. BIÊN BẢN ─────────────────────────────────────────────────────────────

def doc_bien_ban(thu_muc_luot: str) -> Dict[str, Any]:
    try:
        with open(os.path.join(thu_muc_luot, TEP), encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_bien_ban(thu_muc_luot: str, bb: Dict[str, Any]) -> None:
    from .ghi_dia import ghi_json  # noqa: PLC0415

    ghi_json(os.path.join(thu_muc_luot, TEP), dict(bb, phien=1, nguong_viet_lai=NGUONG_VIET_LAI,
                                                   nguong_chan=NGUONG_CHAN, n=N))


def _doc(p: str) -> str:
    try:
        with open(p, encoding="utf-8", errors="replace") as tep:
            return tep.read()
    except OSError:
        return ""


def tom_tat_ho_so(thu_muc_luot: str) -> Optional[Dict[str, Any]]:
    """Cho hồ sơ video: biên bản `1-doc-dao.json` (gọn) nếu có; lượt cũ chưa có biên bản thì ĐO LẠI từ hai tệp chữ
    (rẻ, thuần) — để não nối độ độc đáo với kết quả cả cho video đăng trước cổng. Không đo được → None."""
    bb = doc_bien_ban(thu_muc_luot)
    if bb:
        cuoi = bb.get("cuoi", bb.get("sau"))
        xu = bb.get("xuyen") if isinstance(bb.get("xuyen"), dict) else {}
        return {"ti_le": cuoi, "truoc": bb.get("truoc"), "sau": bb.get("sau"), "viet_lai": bool(bb.get("viet_lai")),
                "so_lan": len(bb.get("lan") or []), "canh_bao": bb.get("canh_bao") or "",
                "khac_tieng": bool(bb.get("khac_tieng")), "bat": bb.get("bat", True), "nguon": "cong",
                "che_do": bb.get("che_do") or "ky_tu", "xuyen": xu.get("cuoi", xu.get("sau"))}
    kb, ng = _doc(os.path.join(thu_muc_luot, TEP_KB)), _doc(os.path.join(thu_muc_luot, TEP_NGUON))
    if not kb.strip() or not ng.strip():
        return None
    do = do_trung(kb, ng, toi_da=0)
    xu = do_xuyen_cuoi(thu_muc_luot, kb, ng) if do["khac_tieng"] else None
    return {"ti_le": do["ti_le"], "truoc": None, "sau": None, "viet_lai": False, "so_lan": 0, "canh_bao": "",
            "khac_tieng": do["khac_tieng"], "bat": None, "nguon": "do_lai", "che_do": "xuyen" if xu else "ky_tu",
            "xuyen": xu["ti_le"] if xu else None}


# ── 4. BÁO CÁO (chỉ đọc) ────────────────────────────────────────────────────

def cac_kenh_co_luot(goc: str) -> List[str]:
    from .kenh import bo_kenh_tra_kho  # noqa: PLC0415 — 20/10: kênh trả kho không tính

    d = os.path.join(goc, "PROJECTS", "AUTO")
    try:
        return bo_kenh_tra_kho(goc, sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))))
    except OSError:
        return []


class _XuyenBaoCao:
    """Đo xuyên ngôn ngữ cho báo cáo: bản dịch lấy từ cache thư mục lượt, rồi cache `thu_muc_dich/<kênh>-<lượt>.txt`,
    rồi (nếu cho) gọi AI tối đa `con_lai` lần, cache vào `thu_muc_dich` — KHÔNG BAO GIỜ ghi vào PROJECTS."""

    def __init__(self, thu_muc_dich: str = "", dich: Optional[Callable[[str], str]] = None, con_lai: int = 0) -> None:
        self.thu_muc_dich, self.dich, self.con_lai, self.da_goi = thu_muc_dich, dich, max(0, int(con_lai)), 0

    def ban_dich(self, tm: str, kenh: str, luot: str, nguon: str) -> Tuple[str, str]:
        san = doc_ban_dich(tm, nguon)
        if san:
            return san, "lượt"
        ten = "{0}-{1}.txt".format(kenh, luot)
        san = doc_ban_dich(self.thu_muc_dich, nguon, ten)
        if san:
            return san, "cache"
        if self.dich is None or self.con_lai <= 0 or not self.thu_muc_dich:
            return "", "chưa dịch"
        self.con_lai -= 1
        self.da_goi += 1
        ban, tt = ban_dich_nguon(self.thu_muc_dich, nguon, self.dich, ten_tep=ten)
        return ban, ("mới" if ban else tt)


def bang_luot(goc: str, kenh: str, n: int = 20, xuyen: Optional[_XuyenBaoCao] = None) -> List[Dict[str, Any]]:
    """N lượt MỚI NHẤT (theo tên thư mục) có cả kịch bản lẫn nguồn: số đo + biên bản cổng nếu có. `xuyen`: thêm
    `cau_sat` (tỉ lệ câu khớp sát — nguồn cùng tiếng so thẳng, nguồn khác tiếng so với bản dịch)."""
    d = os.path.join(goc, "PROJECTS", "AUTO", kenh)
    try:
        luot = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
    except OSError:
        return []
    ra: List[Dict[str, Any]] = []
    for ten in reversed(luot):
        if len(ra) >= max(1, n):
            break
        tm = os.path.join(d, ten)
        kb, ng = _doc(os.path.join(tm, TEP_KB)), _doc(os.path.join(tm, TEP_NGUON))
        if not kb.strip() or not ng.strip():
            continue
        do = do_trung(kb, ng, toi_da=1)
        bb = doc_bien_ban(tm)
        x = {"luot": ten, "ti_le": do["ti_le"], "so_doan": do["so_doan"], "dai_nhat": do["dai_nhat"],
             "khac_tieng": do["khac_tieng"], "vi_du": (do["vi_du"] or [""])[0],
             "cong": ("{0:.0%}→{1:.0%}{2}".format(bb.get("truoc", 0), bb.get("sau", 0),
                                                 " (câu)" if bb.get("che_do") == "xuyen" else "") if bb else ""),
             "cau_sat": None, "dich": ""}
        if xuyen is not None:
            if do["khac_tieng"]:
                ban_dich, x["dich"] = xuyen.ban_dich(tm, kenh, ten, ng)
                if ban_dich:
                    xd = do_xuyen(kb, ban_dich, toi_da=1)
                    x.update(cau_sat=xd["ti_le"], vi_du=(xd["vi_du"] or [""])[0])
            else:
                x["cau_sat"] = do_xuyen(kb, ng, toi_da=0)["ti_le"]
        ra.append(x)
    return list(reversed(ra))


def _tom_tat(ds: Sequence[Dict[str, Any]]) -> str:
    so = [x["ti_le"] for x in ds if not x["khac_tieng"]]
    xu = [x["cau_sat"] for x in ds if x["khac_tieng"] and x.get("cau_sat") is not None]
    them = ""
    if len(so) < len(ds):
        them = " · khác tiếng: {0}".format(len(ds) - len(so))
        if xu:
            them += " (câu dịch sát: trung vị {0:.0%}, > {1:.0%}: {2}/{3})".format(
                statistics.median(xu), NGUONG_XUYEN_VIET_LAI, sum(v > NGUONG_XUYEN_VIET_LAI for v in xu), len(xu))
    if not so:
        return "không có lượt nào đo được (cùng tiếng)" + them
    return "n={0} · trung vị {1:.0%} · ≥15%: {2} · ≥40%: {3} · ≥60%: {4} · cao nhất {5:.0%}{6}".format(
        len(so), statistics.median(so), sum(x > NGUONG_VIET_LAI for x in so), sum(x >= 0.4 for x in so),
        sum(x >= 0.6 for x in so), max(so), them)


def bao_cao(goc: str, kenh_ds: Sequence[str], n: int = 20, vi_du: bool = False,
            xuyen: Optional[_XuyenBaoCao] = None) -> str:
    dong: List[str] = []
    tat_ca: List[Dict[str, Any]] = []
    for kenh in kenh_ds:
        ds = bang_luot(goc, kenh, n, xuyen)
        tat_ca += ds
        dong.append("\n== {0} — {1} lượt mới nhất: {2}".format(kenh, len(ds), _tom_tat(ds)))
        dong.append("  lượt   trùng  đoạn  dài nhất  {0}cổng".format("câu sát  " if xuyen is not None else ""))
        for x in ds:
            cau = ""
            if xuyen is not None:
                cau = "{0:>7}  ".format("-" if x.get("cau_sat") is None else "{0:.0%}{1}".format(
                    x["cau_sat"], "*" if x["khac_tieng"] else ""))
            dong.append("  {0:<6} {1:>5}  {2:>5}  {3:>8}  {4}{5}{6}".format(
                x["luot"], "-" if x["khac_tieng"] else "{0:.0%}".format(x["ti_le"]), x["so_doan"],
                x["dai_nhat"], cau, ("nguồn khác tiếng" + (" (bản dịch: {0})".format(x["dich"]) if x.get("dich") else ""))
                if x["khac_tieng"] else x["cong"] or "-",
                ("  「{0}」".format(x["vi_du"][:60]) if vi_du and x["vi_du"] else "")))
    if len(kenh_ds) > 1:
        dong.append("\n== TẤT CẢ: " + _tom_tat(tat_ca))
    if xuyen is not None:
        dong.append("\n(câu sát = tỉ lệ câu kịch bản khớp sát ≥ {0:.0%} một câu nguồn; * = so với bản dịch nguồn "
                    "khác tiếng, ngưỡng viết lại {1:.0%}; đã gọi AI dịch {2} lần)".format(
                        NGUONG_CAU_XUYEN, NGUONG_XUYEN_VIET_LAI, xuyen.da_goi))
    return "\n".join(dong).lstrip("\n")


def _dich_mac_dinh(goc_cong_cu: str, ngon_ngu: str = "tiếng Nhật") -> Optional[Callable[[str], str]]:
    """Hàm dịch qua phễu chữ thường (Claude Max, lùi ví ShopAPI — `giam_doc.quan_ly.goi_chat_that`); None nếu van ví
    chặn mà máy không có thuê bao."""
    from .giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415

    goi = goi_chat_that(goc_cong_cu, ghi=lambda s: print(s, file=sys.stderr))
    if goi is None:
        return None
    from .chia_canh import dien_khuon  # noqa: PLC0415

    def dich(nguon: str) -> str:
        return goi(dien_khuon(LOI_NHAC_DICH, {"NGON_NGU": ngon_ngu, "NGUON": nguon}), khoa="doc-dao:dich:" + bam(nguon),
                   toi_da_token=32768)
    return dich


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -X utf8 -m core.do_doc_dao",
                                 description="Mức chép nguồn của kịch bản các lượt gần nhất (chỉ đọc PROJECTS).")
    ap.add_argument("--kenh", action="append", default=[], help="mã kênh (lặp lại / cách nhau dấu phẩy); bỏ trống = mọi kênh")
    ap.add_argument("--n", type=int, default=20, help="số lượt mới nhất mỗi kênh (mặc định 20)")
    ap.add_argument("--goc", default=GOC, help="gốc tool (mặc định: thư mục chứa core/)")
    ap.add_argument("--vi-du", action="store_true", help="in kèm đoạn chép dài nhất của mỗi lượt")
    ap.add_argument("--xuyen", action="store_true", help="thêm cột «câu sát» (gióng câu; nguồn khác tiếng dùng bản dịch đã cache)")
    ap.add_argument("--dich", type=int, default=0, metavar="N",
                    help="cho gọi AI dịch tối đa N nguồn khác tiếng chưa có bản dịch (kèm --xuyen)")
    ap.add_argument("--cache-dich", default="", help="thư mục cache bản dịch của báo cáo (mặc định <gốc>/workspace/doc-dao/dich)")
    a = ap.parse_args(argv)
    kenh = [x.strip() for v in a.kenh for x in v.split(",") if x.strip()] or cac_kenh_co_luot(a.goc)
    xu = None
    if a.xuyen or a.dich:
        xu = _XuyenBaoCao(a.cache_dich or os.path.join(a.goc, "workspace", "doc-dao", "dich"),
                          _dich_mac_dinh(GOC) if a.dich > 0 else None, a.dich)
    bat_dau = time.time()
    print(bao_cao(a.goc, kenh, a.n, a.vi_du, xu))
    print("\n(đo {0} kênh trong {1:.1f} giây; cửa sổ {2} ký tự, ngưỡng viết lại {3:.0%}, ngưỡng cảnh báo {4:.0%})".format(
        len(kenh), time.time() - bat_dau, N, NGUONG_VIET_LAI, NGUONG_CHAN))
    return 0


if __name__ == "__main__":
    sys.exit(main())
