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

═══ CỔNG ═══ `qua_cong(...)` (gọi từ `auto_khau._khau_kich_ban`, sau khi bài đã chốt và nắn độ dài, TRƯỚC rà soát
`3-sua.md` — nên tách câu, thẻ cảm xúc, `---` và giọng đọc đều đi trên bản đã qua cổng):
  1. trùng ≤ `NGUONG_VIET_LAI` → giữ nguyên;
  2. viết lại MỘT lượt qua phễu chữ thường (`_goi` → `goi_van_ban`: Claude Max, lùi ví ShopAPI), đưa các đoạn chép
     làm danh sách "không dùng lại"; đo lại; nhận bản mới khi qua kiểm (độ dài, ghi chú kỹ thuật, `---`, câu mời
     đăng ký) VÀ trùng thấp hơn;
  3. vẫn > `NGUONG_CHAN` → thử thêm MỘT lần từ bản tốt nhất; vẫn trượt → cảnh báo rồi ĐI TIẾP (luật chủ: thử lại,
     không bỏ lượt). Biên bản `1-doc-dao.json`; kênh tắt bằng `doc_dao: false` trong `kenh.yaml` (vẫn đo, không viết).

    python -X utf8 -m core.do_doc_dao --kenh TL2-T7 [--n 20] [--goc <gốc tool>]     # bảng mức chép, chỉ đọc
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
LOI_NHAC_VIET_LAI = """Bạn là người kể chuyện của kênh YouTube dưới đây. Kịch bản bên dưới đang CHÉP QUÁ SÁT lời thoại một video của kênh khác: <<TI_LE>> chuỗi 10 ký tự của nó có y nguyên trong bản gốc. YouTube coi đó là nội dung tái sử dụng ("đọc lại tài liệu không phải do mình tạo") — kênh có thể trượt xét kiếm tiền. Hãy VIẾT LẠI TỪNG CÂU bằng giọng riêng của kênh, bằng <<NGON_NGU>>.

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

TUYỆT ĐỐI KHÔNG DÙNG LẠI các cụm chép nguyên văn dưới đây — nói ý của chúng bằng lời khác hẳn:
<<DOAN_CHEP>>
<<NHAC_LAI>>
Kênh: <<CHANNEL>>
Tiêu đề video: <<TITLE>>

Chỉ trả về lời đọc của kịch bản mới — không tiêu đề, không ghi chú, không giải thích, không tạo file.

KỊCH BẢN CẦN VIẾT LẠI:
<<DRAFT>>
"""


def qua_cong(ban: str, nguon: str, *, viet: Optional[Callable[[str, Dict[str, Any], int, str], str]],
             kiem: Callable[[str, str], str], nguong_viet_lai: float = NGUONG_VIET_LAI,
             nguong_chan: float = NGUONG_CHAN, ghi: Optional[Callable[[str], None]] = None,
             khong_nuot: Tuple[type, ...] = ()) -> Tuple[str, Dict[str, Any]]:
    """Đo `ban`; trên `nguong_viet_lai` thì gọi `viet(ban_dang_tot, so_do_cua_no, lan, nhac_lai) -> bản mới` tối đa
    `SO_LAN_TOI_DA` lần (lần 2 chỉ khi bản tốt nhất còn > `nguong_chan`); `so_do["vi_du"]` = các đoạn chép.
    `kiem(moi, ban_goc) -> lý do loại` ("" = qua). Giữ bản trùng THẤP NHẤT đã qua kiểm. `viet=None` = kênh tắt: chỉ
    đo. Không bao giờ ném lỗi (trừ `khong_nuot`, vd lệnh Dừng). Trả `(bản chọn, biên bản)`."""
    ghi = ghi or (lambda _s: None)
    do0 = do_trung(ban, nguon, toi_da=TOI_DA_DOAN)
    bb: Dict[str, Any] = {"truoc": do0["ti_le"], "sau": do0["ti_le"], "so_doan_truoc": do0["so_doan"],
                          "dai_nhat_truoc": do0["dai_nhat"], "vi_du_truoc": do0["vi_du"][:5], "khac_tieng": do0["khac_tieng"],
                          "lan": [], "viet_lai": False, "canh_bao": ""}
    if do0["khac_tieng"]:
        bb["ghi_chu"] = "nguồn khác tiếng — đo chuỗi ký tự không bắt được bản dịch, không viết lại"
        return ban, bb
    if do0["ti_le"] <= nguong_viet_lai:
        return ban, bb
    if viet is None:
        bb["ghi_chu"] = "kênh tắt viết lại (doc_dao: false) — chỉ đo"
        ghi("  độ độc đáo: kịch bản trùng nguồn {0:.0%} — kênh tắt cổng viết lại, chỉ ghi số.".format(do0["ti_le"]))
        return ban, bb
    tot, do_tot, nhac = ban, do0, ""
    for lan in range(1, SO_LAN_TOI_DA + 1):
        if lan > 1 and do_tot["ti_le"] <= nguong_chan:
            break
        ghi("  độ độc đáo: kịch bản trùng nguồn {0:.0%} (> {1:.0%}) — viết lại bằng giọng kênh, lần {2}/{3}…".format(
            do_tot["ti_le"], nguong_viet_lai, lan, SO_LAN_TOI_DA))
        muc: Dict[str, Any] = {"lan": lan, "tu": "goc" if tot is ban else "ban_tot"}
        try:
            moi = (viet(tot, do_tot, lan, nhac) or "").strip()
        except khong_nuot:
            raise
        except Exception as loi:  # noqa: BLE001 — gọi AI hỏng: thử lần sau / giữ bản đang có
            moi, muc["loi"] = "", str(loi)[:160]
        do_moi = do_trung(moi, nguon, toi_da=TOI_DA_DOAN) if moi else None
        ly_do = ("lỗi gọi AI: " + muc["loi"]) if muc.get("loi") else "bản trả về rỗng" if not moi else kiem(moi, ban)
        if not ly_do and do_moi["ti_le"] >= do_tot["ti_le"]:
            ly_do = "không bớt chép ({0:.0%} ≥ {1:.0%})".format(do_moi["ti_le"], do_tot["ti_le"])
        muc.update(ti_le=do_moi["ti_le"] if do_moi else None, ky_tu=len(moi), nhan=not ly_do, ly_do=ly_do)
        bb["lan"].append(muc)
        if ly_do:
            ghi("    → bỏ bản viết lại: {0}".format(ly_do))
            nhac = "Lần viết lại trước bị loại: {0}. Sửa đúng chỗ ấy.".format(ly_do)
        else:
            ghi("    → nhận: trùng {0:.0%} → {1:.0%}".format(do_tot["ti_le"], do_moi["ti_le"]))
            tot, do_tot = moi, do_moi
            nhac = "Bản này đã viết lại một lần mà vẫn còn {0:.0%} trùng — đổi mạnh tay hơn.".format(do_moi["ti_le"])
    bb.update(sau=do_tot["ti_le"], viet_lai=tot is not ban, so_doan_sau=do_tot["so_doan"],
              vi_du_sau=do_tot["vi_du"][:5])
    if do_tot["ti_le"] > nguong_chan:
        bb["canh_bao"] = "sau {0} lần viết lại kịch bản vẫn trùng nguồn {1:.0%} (> {2:.0%}) — vẫn đi tiếp".format(
            len(bb["lan"]), do_tot["ti_le"], nguong_chan)
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
        return {"ti_le": cuoi, "truoc": bb.get("truoc"), "sau": bb.get("sau"), "viet_lai": bool(bb.get("viet_lai")),
                "so_lan": len(bb.get("lan") or []), "canh_bao": bb.get("canh_bao") or "",
                "khac_tieng": bool(bb.get("khac_tieng")), "bat": bb.get("bat", True), "nguon": "cong"}
    kb, ng = _doc(os.path.join(thu_muc_luot, TEP_KB)), _doc(os.path.join(thu_muc_luot, TEP_NGUON))
    if not kb.strip() or not ng.strip():
        return None
    do = do_trung(kb, ng, toi_da=0)
    return {"ti_le": do["ti_le"], "truoc": None, "sau": None, "viet_lai": False, "so_lan": 0, "canh_bao": "",
            "khac_tieng": do["khac_tieng"], "bat": None, "nguon": "do_lai"}


# ── 4. BÁO CÁO (chỉ đọc) ────────────────────────────────────────────────────

def cac_kenh_co_luot(goc: str) -> List[str]:
    d = os.path.join(goc, "PROJECTS", "AUTO")
    try:
        return sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
    except OSError:
        return []


def bang_luot(goc: str, kenh: str, n: int = 20) -> List[Dict[str, Any]]:
    """N lượt MỚI NHẤT (theo tên thư mục) có cả kịch bản lẫn nguồn: số đo + biên bản cổng nếu có."""
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
        ra.append({"luot": ten, "ti_le": do["ti_le"], "so_doan": do["so_doan"], "dai_nhat": do["dai_nhat"],
                   "khac_tieng": do["khac_tieng"], "vi_du": (do["vi_du"] or [""])[0],
                   "cong": ("{0:.0%}→{1:.0%}".format(bb.get("truoc", 0), bb.get("sau", 0)) if bb else "")})
    return list(reversed(ra))


def _tom_tat(ds: Sequence[Dict[str, Any]]) -> str:
    so = [x["ti_le"] for x in ds if not x["khac_tieng"]]
    if not so:
        return "không có lượt nào đo được (cùng tiếng)"
    return "n={0} · trung vị {1:.0%} · ≥15%: {2} · ≥40%: {3} · ≥60%: {4} · cao nhất {5:.0%}{6}".format(
        len(so), statistics.median(so), sum(x > NGUONG_VIET_LAI for x in so), sum(x >= 0.4 for x in so),
        sum(x >= 0.6 for x in so), max(so), " · khác tiếng: {0}".format(len(ds) - len(so)) if len(so) < len(ds) else "")


def bao_cao(goc: str, kenh_ds: Sequence[str], n: int = 20, vi_du: bool = False) -> str:
    dong: List[str] = []
    tat_ca: List[Dict[str, Any]] = []
    for kenh in kenh_ds:
        ds = bang_luot(goc, kenh, n)
        tat_ca += ds
        dong.append("\n== {0} — {1} lượt mới nhất: {2}".format(kenh, len(ds), _tom_tat(ds)))
        dong.append("  lượt   trùng  đoạn  dài nhất  cổng")
        for x in ds:
            dong.append("  {0:<6} {1:>5}  {2:>5}  {3:>8}  {4}{5}".format(
                x["luot"], "-" if x["khac_tieng"] else "{0:.0%}".format(x["ti_le"]), x["so_doan"],
                x["dai_nhat"], "nguồn khác tiếng" if x["khac_tieng"] else x["cong"] or "-",
                ("  「{0}」".format(x["vi_du"][:60]) if vi_du and x["vi_du"] else "")))
    if len(kenh_ds) > 1:
        dong.append("\n== TẤT CẢ: " + _tom_tat(tat_ca))
    return "\n".join(dong).lstrip("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -X utf8 -m core.do_doc_dao",
                                 description="Mức chép nguồn của kịch bản các lượt gần nhất (chỉ đọc).")
    ap.add_argument("--kenh", action="append", default=[], help="mã kênh (lặp lại / cách nhau dấu phẩy); bỏ trống = mọi kênh")
    ap.add_argument("--n", type=int, default=20, help="số lượt mới nhất mỗi kênh (mặc định 20)")
    ap.add_argument("--goc", default=GOC, help="gốc tool (mặc định: thư mục chứa core/)")
    ap.add_argument("--vi-du", action="store_true", help="in kèm đoạn chép dài nhất của mỗi lượt")
    a = ap.parse_args(argv)
    kenh = [x.strip() for v in a.kenh for x in v.split(",") if x.strip()] or cac_kenh_co_luot(a.goc)
    bat_dau = time.time()
    print(bao_cao(a.goc, kenh, a.n, a.vi_du))
    print("\n(đo {0} kênh trong {1:.1f} giây; cửa sổ {2} ký tự, ngưỡng viết lại {3:.0%}, ngưỡng cảnh báo {4:.0%})".format(
        len(kenh), time.time() - bat_dau, N, NGUONG_VIET_LAI, NGUONG_CHAN))
    return 0


if __name__ == "__main__":
    sys.exit(main())
