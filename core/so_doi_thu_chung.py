"""**Sổ đối thủ CHUNG của nhóm** — mỗi kênh đối thủ MỘT dòng cho cả nhóm, sổ riêng từng kênh là bản chiếu.

Chủ dự án, 12/10/2026: *"dữ liệu đối thủ khi gộp all các kênh vào sẽ có 1 danh sách toàn diện — việc theo dõi
đối thủ sẽ ok — để phát hiện ra content đột biến … giúp tao đạt mục tiêu để các kênh nổ view, kiếm tiền".*

═══ VÌ SAO ═══

Đo 12/10/2026 (8 kênh nhóm tâm lý): 14.389 dòng sổ đối thủ (`CHANNEL/<k>/nghien-cuu/doi-thu.csv`) nhưng chỉ
1.843 khoá link khác nhau (1.813 kênh thật sau khi gộp `@handle` ↔ `/channel/UC…`) — mỗi kênh đối thủ được
ghi ~8 lần. Tệ hơn: `nhom_kenh.dong_bo_doi_thu` gộp HỘP THƯ của cả nhóm vào hộp thư từng kênh, nên kênh nào có sổ
cũ (TL4-T7, sổ đứng từ 21/09) thì lượt đầu tiên chấm lại TOÀN BỘ hộp thư: 1.542 kênh, mỗi kênh một lượt yt-dlp +
một lần ghi lại `kenh-do.json` 27 MB + một phán quyết ngách — 1,5 giờ để ra đúng những phán quyết anh em đã có.

═══ SỔ CHUNG ═══ `CHANNEL/_NHOM/<nhóm>/doi-thu-chung.json` (+ bản đọc `doi-thu-chung.csv`)

    {"phien_ban": 1, "nhom", "luc", "thanh_vien": [...], "thong_ke": {...},
     "bi_danh": {khoá link: "UC…"},                      # @handle/c/user → mã kênh (nhớ mãi)
     "gieo": {kênh ta: {khoá chuẩn: {"tu", "luc", "trang_thai"}}},   # dòng sổ chung đã gieo vào sổ riêng
     "kenh": {khoá chuẩn: {
        "khoa", "uc", "link", "lien_ket": [mọi dạng link], "ten",
        "so": {Subs, Số video, Dài TV, View TV, Vượt quy mô, AI, …},  "so_luc": lần quét của bộ số,
        "quet_luc", "lan_dau",
        "ngach": {"ket": giu|bo|nghi, "ngay", "ly_do", "nguon"},   # phán quyết NGÁCH (một lần cho cả nhóm)
        "song": {"ket": het|chet|lech_tieng, "ngay", "ly_do"},     # sức sống / kênh chết / sai tiếng
        "ban_dua": bool,                                           # chủ dự án tự tay đưa — luôn quét
        "trang_thai": theo dõi|hết|bỏ (đồng thuận), "gieo": {"trang_thai", "ghi_chu", "tu"} | None,
        "theo_kenh": {kênh ta: {tt, tuyen, ghi, cua, diem, ly, quet, lan_dau, link}},   # phán quyết RIÊNG
        "lien_quan": {kênh ta: {tc, pool, khop_tep, n_content}}}}}                   # khán giả / tệp

Khoá chuẩn = mã kênh `UC…` khi biết (ảnh chụp `kenh-do.json`, `quet-kenh/`, bí danh đã nhớ), không thì
`danh_ba_doi_thu.khoa(link)`.

═══ LUẬT ═══

1. **Sổ riêng là sự thật của phần RIÊNG** (tuyến, trạng thái khách đặt tay, ghi chú, cửa/điểm/lý do): mỗi lần gộp
   (`gop`) dựng lại sổ chung TỪ ĐẦU bằng mọi sổ riêng + kho phán quyết nhóm (`kenh-ai.json`) — không ghi chú nào bị
   mất vì nó nằm nguyên ở sổ riêng, và `theo_kenh` chép đủ từng ô.
2. **Phần CHUNG chỉ là sự thật về kênh đối thủ**: số đo (lần quét mới nhất thắng), phán quyết ngách theo NGHĨA của
   nhóm (đúng vai `kenh-ai.json` — `nghien_cuu_chung`), sức sống, cờ "bạn đưa — luôn quét".
3. **Gieo, không đè** (`ap_vao_so`): link nằm trong HỘP THƯ của một kênh mà sổ riêng của nó chưa có, nếu sổ chung
   đã có phán quyết đủ chắc → thêm thẳng vào sổ riêng (trạng thái + Ghi chú NGUYÊN VĂN của dòng anh em đã chấm,
   tuyến để trống cho kênh tự gán) — KHÔNG đo lại, KHÔNG hỏi AI lại. Dòng đã có thì chỉ làm mới số đo chung
   (`COT_SO_CHUNG`) khi sổ chung quét mới hơn; cột của khách (`danh_ba_doi_thu.COT_CUA_KHACH`) không bao giờ bị đè.
   Kênh vừa bật / sổ cũ / kênh mới tạo trong nhóm vì thế không phải chấm lại cả nghìn kênh.
4. Chỉ gieo phán quyết ĐỦ CHẮC: AI ngách (giữ/bỏ), hết (sức sống), kênh chết, sai tiếng, bạn đưa. KHÔNG gieo: "bỏ"
   chỉ vì từ khoá (cổng thể loại khác nhau theo tệp — `bo_qua_zatsugaku`), máy chấm cũ trước 30/09, ghi chú tay/trống,
   ⚠ NGHI. Kênh bật `cho_phep_tep_gia` (kho phán quyết ngách RIÊNG, `nghien_cuu_chung.duong_kenh_ai`) chỉ nhận gieo
   phần không phụ thuộc tệp (chết, sai tiếng, hết, bạn đưa); phán quyết ngách của nó cũng không vào phần chung.
5. Xoá hẳn một đối thủ ở một kênh (`danh_ba_doi_thu.xoa`, gỡ cả hộp thư) → không gieo lại cho kênh ấy trừ khi link
   quay về hộp thư (y luật cũ của `nhom_kenh.dong_bo_doi_thu`).

Nơi gọi: `chot_doi_thu.chot` (đầu lượt chấm hộp thư: gộp + gieo; cuối lượt: gộp lại), `mot_nut.chay` (gộp sau
bước quét + lọc lượt quét theo tầng), `radar_dot_bien` (đọc + cập nhật `lien_quan`, xếp tầng 1–2 trước),
`kiem_ngach_doi_thu.kiem` (đo lại kênh hết theo hạn tầng). Kênh không khai `nhom` → không có sổ chung (sổ riêng của
nó vẫn là danh bạ duy nhất), mọi hàm ở đây là không-làm-gì.

═══ TẦNG ĐỐI THỦ (13/10/2026) ═══

Chủ dự án: *"1812 là quá nhiều — thị trường không thể có nhiều đối thủ thế, có gì lẫn lộn; phân tầng đối thủ để theo
dõi hiệu quả"*. Kiểm toán 13/10: 1.812 dòng = MỌI kênh từng rơi vào hộp thư CHỈ-NỐI-THÊM của nhóm (≈ 96% từ trang chủ
máy ảo, `nhom_kenh.dong_bo_doi_thu` hợp hộp thư nên dòng nào cũng nằm ở cả 8 sổ riêng) — sổ là TRÍ NHỚ "đã xét / đã
từ chối", không phải danh sách đối thủ: 1.274 bỏ (1.181 AI lạc ngách, 90 sai tiếng), 251 hết, 287 theo dõi. Đối thủ
thật là phần trong ngách + còn sống; tầng cho biết quét nó dày đến đâu (`phan_tang`, tính lại mỗi lần gộp):

    1  lõi      trong ngách, còn đăng ≤ `NGAY_SONG_TANG` ngày, đủ cỡ (Subs ≥ `SUBS_TANG_1` hoặc View TV ≥
                `VIEW_TV_TANG_1`) hoặc có mặt trong pool đề xuất / trang chủ dày của kênh ta; xếp điểm, trần
                `TRAN_TANG_1` kênh — quét hằng ngày
    2  đang lên trong ngách, còn sống, chưa vào tầng 1 nhưng có tín hiệu: radar nổ ≤ `NGAY_DOT_BIEN_TANG` ngày
                (`radar/quyet-dinh.jsonl`, bảng radar — dính `NGAY_DOT_BIEN_TANG` ngày: video nổ ở tầng 3 kéo kênh
                lên tầng 2 ngay lần gộp sau), video gần ≥ `BUNG_TANG_2` × trung vị, kênh trẻ view/tháng cao,
                Vượt quy mô cao; + phần dư đủ cỡ tầng 1 ngoài trần — 2–3 ngày/lần
    3  nhẹ      trong ngách nhưng nhỏ / chưa tín hiệu / im lâu / chưa đo được ngày đăng — tuần/lần
    ngoai       bỏ / hết / tạm ngưng ở MỌI kênh ta, kênh chết, sai tiếng — không quét; kênh hết đo lại hằng tháng
                (`den_han_do_lai`), chết / sai tiếng / lạc ngách không đo lại (y luật cũ)

Kênh bạn đưa không bao giờ dưới tầng 2 và không ra `ngoai` trừ khi chết / hết / sai tiếng (luật sức sống thắng bạn
đưa — y thứ tự `_phan_quyet_gieo`). Ngưỡng là hằng số ở đầu tệp. Ngày đăng mới nhất lấy từ ảnh chụp kênh của kho nhóm
(`kenh-do.json`, `quet-kenh/`) — cột `Đăng gần nhất` của sổ riêng phần lớn trống / cũ.

Hạn quét (`NGAY_QUET_TANG`, `loc_quet` — bước 3 của `mot_nut`): kênh đến hạn theo tầng tính từ lần quét content gần
nhất của CHÍNH kênh ta (mốc từng kênh `cai-dat.json` → `quet_kenh`, `quet_doi_thu` ghi — không dùng Quét lúc của danh
bạ vì lượt chấm hộp thư cũng ghi nó); ảnh chụp nhóm còn tươi (kênh anh em vừa quét, `nghien_cuu_chung.HAN_QUET_GIO`)
thì lấy luôn — miễn phí; trang chủ máy ảo vừa đẩy video mới của kênh → quét sớm; một kênh hai link (`@handle` +
`/channel/UC…`) chỉ quét một lần. `Tăng/ngày` chia cho khoảng quét của CHÍNH kênh (`doi_thu_kenh.gop_bang`).
`MYTOOL_QUET_THEO_TANG=0` tắt (quét mọi kênh theo dõi như cũ). Nút "Quét đối thủ" bấm tay vẫn quét đủ.

    python -m core.so_doi_thu_chung --nhom <nhóm> [--goc <cây>] [--ghi] [--gieo] [--tang [N]]   # mặc định chạy thử

Không mạng, không AI, không Qt. Ghi nguyên tử dưới khoá ngắn (`nghien_cuu_chung._KhoaNgan`).
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import math
import os
import re
import statistics
import sys
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote

from . import danh_ba_doi_thu as db

__all__ = ["TEP", "TEP_CSV", "COT_SO_CHUNG", "COT_SO_RIENG", "duong", "doc", "gop", "ap_vao_so",
           "dong_bo_truoc_chot", "gop_sau", "phan_loai_ghi_chu", "tra", "thanh_vien_nhom", "nhom_cua",
           "thong_ke_so", "TANG", "NGAY_QUET_TANG", "phan_tang", "loc_quet", "den_han_do_lai"]

TEP = "doi-thu-chung.json"
TEP_CSV = "doi-thu-chung.csv"
PHIEN_BAN = 1

#: Số đo về CHÍNH kênh đối thủ — như nhau với mọi kênh ta: lần quét mới nhất thắng, được làm mới vào sổ riêng.
COT_SO_CHUNG = ("Subs", "Số video", "Dài TV", "View TV", "Vượt quy mô", "AI")
#: Cột tính từ bảng content CỦA TỪNG kênh (`danh_ba_doi_thu.cap_nhat_tu_bang`) — chỉ để xem trong sổ chung, không
#: chép vào sổ riêng (sổ riêng tự tính lại từ bảng của nó, "luôn khớp với thứ khách đang nhìn").
COT_SO_RIENG = ("Tuổi (tháng)", "View/tháng", "Im lặng", "Mới 7 ngày", "Đăng gần nhất")

GHI_CHU_BAN_DUA = "bạn đưa — luôn quét"
LOP_GIEO = ("ban_dua", "giu", "bo", "het", "chet", "lech_tieng")
#: Lớp gieo được cho kênh có kho ngách RIÊNG (`cho_phep_tep_gia`): không phụ thuộc tệp khán giả.
LOP_GIEO_RIENG = ("ban_dua", "het", "chet", "lech_tieng")
#: Thứ tự ưu tiên khi hai sự kiện cùng ngày.
_UU_TIEN = {"chet": 6, "lech_tieng": 5, "het": 4, "bo": 3, "giu": 2, "nghi": 1}
_RE_NGAY = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?")
_RE_UC = re.compile(r"^(UC[\w-]{20,24})$")
#: Mã kênh trong link GỐC — `db.khoa` hạ chữ thường mọi khoá ASCII, mà mã UC… phân biệt hoa thường.
_RE_UC_LINK = re.compile(r"/channel/(UC[\w-]{20,24})(?![\w-])")

# ── tầng đối thủ (xem "TẦNG ĐỐI THỦ" đầu tệp) ────────────────────────────────
TANG_1, TANG_2, TANG_3, NGOAI = "1", "2", "3", "ngoai"
TANG = (TANG_1, TANG_2, TANG_3, NGOAI)
#: Còn sống = video mới nhất (ảnh chụp kênh / Đăng gần nhất) cách hôm nay ≤ ngần này ngày (= `kiem_ngach_doi_thu.NGAY_IM`).
NGAY_SONG_TANG = 30
#: Đủ cỡ tầng 1: Subs ≥ … HOẶC View TV (trung vị view lần quét) ≥ …
SUBS_TANG_1 = 10_000
VIEW_TV_TANG_1 = 5_000
#: … hoặc có mặt DÀY ở khán giả ta: ≥ ngần này video trong pool đề xuất Studio, hay ≥ ngần này dòng trang chủ máy ảo
#: (28 ngày, cộng cả nhóm — trung vị kênh nhỏ còn sống là ~20 dòng, nên ngưỡng phải cao mới là "dày").
POOL_TANG_1 = 5
TC_TANG_1 = 200
#: Trần tầng 1 (xếp theo điểm) — quét hằng ngày phải rẻ. Phần dư đủ cỡ → tầng 2; dư chỉ nhờ có mặt mà nhỏ → tầng 3.
TRAN_TANG_1 = 60
#: Tín hiệu đột biến radar (mức ≥ `MUC_DOT_BIEN_TANG`) còn kéo kênh lên tầng 2 ngần này ngày.
NGAY_DOT_BIEN_TANG = 14
MUC_DOT_BIEN_TANG = 2
#: Video ≤ 30 ngày tuổi (ảnh chụp) ≥ ngần này × trung vị view của kênh VÀ ≥ `BUNG_VIEW_TANG_2` view — sàn tuyệt đối vì
#: kênh nhỏ trung vị vài trăm view thì ×5 là chuyện thường (đo 13/10: 139/217 kênh nhỏ có ×5 ở ≥ 3.000 view).
BUNG_TANG_2 = 5.0
BUNG_VIEW_TANG_2 = 20_000
#: Kênh trẻ (ảnh chụp đủ mọi video, video cũ nhất ≤ ngần này tháng) có view/tháng ≥ …
THANG_TRE_TANG_2 = 6.0
VIEW_THANG_TRE_TANG_2 = 50_000
#: Vượt quy mô (video nhiều view nhất ÷ subs) ≥ … ở kênh còn sống, và video ấy ≥ `VIEW_VUOT_TANG_2` view (≈ vượt × subs):
#: kênh 300 subs có video 2.000 view đã là ×7 — chưa phải tín hiệu.
VUOT_TANG_2 = 5.0
VIEW_VUOT_TANG_2 = 50_000
#: Hạn quét lại (ngày) theo tầng, tính từ lần quét gần nhất của chính kênh ta — hơi dưới 1/2,5/7/30 ngày để lượt
#: nghiên cứu chạy sớm vài giờ không lỡ nhịp. Kênh chưa có tầng (mới vào sổ) → quét ngay.
NGAY_QUET_TANG = {TANG_1: 0.75, TANG_2: 2.4, TANG_3: 6.5, NGOAI: 29.5}
#: Trang chủ máy ảo của kênh ta đẩy video đăng ≤ ngần này ngày của một đối thủ chưa tới hạn → quét nó ngay lượt này.
NGAY_VIDEO_MOI_TRANG_CHU = 3
#: Thứ tự quét trong một lượt: tầng 1 → kênh mới → tầng 2 → 3 → ngoài.
_HANG_TANG = {TANG_1: 0, "": 1, TANG_2: 2, TANG_3: 3, NGOAI: 4}


# ── đường / nhóm ─────────────────────────────────────────────────────────────

def nhom_cua(goc: str, kenh: str) -> str:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        return nhom_kenh.nhom_cua_kenh(goc, kenh)
    except Exception:  # noqa: BLE001
        return ""


def thanh_vien_nhom(goc: str, nhom: str) -> List[str]:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        return list(nhom_kenh._thanh_vien_cua_nhom(goc, nhom))  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return []


def thu_muc(goc: str, nhom: str) -> str:
    from . import nhom_kenh  # noqa: PLC0415

    return nhom_kenh.duong_thu_muc_nhom(goc, nhom)


def duong(goc: str, nhom: str) -> str:
    return os.path.join(thu_muc(goc, nhom), TEP)


def _doc_json(p: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def doc(goc: str, nhom: str) -> Dict[str, Any]:
    """Sổ chung đang có (`{}` khi chưa có / hỏng)."""
    du = _doc_json(duong(goc, nhom), {})
    return du if isinstance(du, dict) and isinstance(du.get("kenh"), dict) else {}


def ghi_json_gon(p: str, du: Any) -> None:
    """Ghi JSON GỌN (không thụt lề) nguyên tử — sổ chung ~1.800 kênh × 8 kênh ta, ghi vài lần mỗi lượt nghiên cứu."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = "{0}.{1}.tmp".format(p, os.getpid())
    with io.open(tam, "w", encoding="utf-8") as tep:
        tep.write(json.dumps(du, ensure_ascii=False, separators=(",", ":")))
    for lan in range(5):
        try:
            os.replace(tam, p)
            return
        except PermissionError:   # Windows: tệp đang bị mở đọc
            if lan == 4:
                raise
            time.sleep(0.2 * (lan + 1))


def _ghi(goc: str, nhom: str, du: Dict[str, Any]) -> str:
    p = duong(goc, nhom)
    ghi_json_gon(p, du)
    try:
        _ghi_csv(os.path.join(os.path.dirname(p), TEP_CSV), du)
    except OSError:
        pass  # bản đọc hỏng không làm hỏng sổ
    return p


def _khoa_ghi(goc: str, nhom: str):
    from .nghien_cuu_chung import _KhoaNgan  # noqa: PLC0415

    return _KhoaNgan(duong(goc, nhom), cho=20.0, cu=120.0)


# ── ngày / ghi chú ───────────────────────────────────────────────────────────

def _ngay_tu_dd_mm(chu: str, moc: _dt.date) -> str:
    """"30/09" → "2026-09-30" (năm suy theo `moc`: ngày sau mốc > 2 ngày → năm trước)."""
    m = _RE_NGAY.search(chu or "")
    if not m:
        return ""
    try:
        d, th = int(m.group(1)), int(m.group(2))
        nam = int(m.group(3)) if m.group(3) else moc.year
        ngay = _dt.date(nam, th, d)
    except ValueError:
        return ""
    if not m.group(3) and ngay > moc + _dt.timedelta(days=2):
        try:
            ngay = _dt.date(nam - 1, th, d)
        except ValueError:
            return ""
    return ngay.isoformat()


def _moc(quet: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(str(quet or "")[:10])
    except ValueError:
        return _dt.date.today()


def phan_loai_ghi_chu(ghi: str, quet: str = "") -> Tuple[str, str]:
    """Ghi chú một dòng sổ riêng → `(lớp, ngày ISO)`.

    Lớp: `ban_dua` · `giu` (AI: đúng ngách) · `bo` (AI: lạc ngách) · `nghi` · `het` (sức sống) · `chet` (kênh không
    còn) · `lech_tieng` · `tu_khoa` (bỏ chỉ vì từ khoá) · `may` (máy chấm cũ) · `tay` (trống / khách viết tay).
    Ngày: dd/mm trong ghi chú (dấu kiểm ngách), không có thì ngày của `quet` (Quét lúc của dòng).

    >>> phan_loai_ghi_chu("✓ AI kiểm ngách 12/10: chân dung tâm lý", "2026-10-12 05:00")
    ('giu', '2026-10-12')
    >>> phan_loai_ghi_chu("không phải kênh tâm lý — AI: toàn nhạc", "2026-10-01 10:00")[0]
    'bo'
    >>> phan_loai_ghi_chu("")[0]
    'tay'
    """
    g = str(ghi or "").strip()
    moc = _moc(quet)
    ngay_quet = moc.isoformat() if quet else ""
    if not g:
        return "tay", ""
    if g.startswith(GHI_CHU_BAN_DUA):
        return "ban_dua", ngay_quet
    if g.startswith("✓ AI kiểm ngách"):
        return "giu", _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("⚠ NGHI"):
        return "nghi", _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("Hết"):
        return "het", _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("AI kiểm ngách"):
        try:
            from .kiem_ngach_doi_thu import la_bo_suc_song  # noqa: PLC0415

            suc_song = la_bo_suc_song(g)
        except Exception:  # noqa: BLE001
            suc_song = False
        return ("het" if suc_song else "bo"), _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("không phải kênh tâm lý — "):
        return "bo", ngay_quet
    if g.startswith("AI: đối thủ") or g.startswith("AI ("):
        return "giu", ngay_quet
    if g.startswith("kênh không còn hoặc không xem được"):
        return "chet", ngay_quet
    if g.startswith("không phải tiếng của kênh"):
        return "lech_tieng", ngay_quet
    if g.startswith("không phải kênh tâm lý:"):
        return "tu_khoa", ngay_quet
    if g.startswith(("thị trường (", "máy chấm:")):
        return "may", ngay_quet
    return "tay", ngay_quet


# ── bí danh (mã kênh UC…) ────────────────────────────────────────────────────

_NHO_BI_DANH: Dict[str, Tuple[Tuple[float, ...], Dict[str, str], Dict[str, Dict[str, Any]]]] = {}


def _tom_anh(ch: Dict[str, Any], luc: float) -> Optional[Dict[str, Any]]:
    """Tóm một ảnh chụp kênh (`youtube.Channel` dạng dict) → số cho tầng: `{luc, moi, cu, du, n, tv, vt, bung,
    bung_view, subs}` (`moi`/`cu` = ngày đăng video mới / cũ nhất; `vt` = view/tháng của video ≤ 90 ngày tuổi lúc
    chụp; `bung` = video ≤ 30 ngày tuổi lúc chụp nhiều view nhất ÷ trung vị view của ảnh chụp)."""
    vs = [v for v in ((ch or {}).get("videos") or []) if isinstance(v, dict)]
    if not vs:
        return None
    ngay: List[Tuple[_dt.date, int]] = []
    views: List[int] = []
    for v in vs:
        try:
            w = int(v.get("views"))
        except (TypeError, ValueError):
            w = -1
        if w >= 0:
            views.append(w)
        try:
            ngay.append((_dt.date.fromisoformat(str(v.get("upload_date") or "")[:10]), w))
        except ValueError:
            continue
    try:
        d0 = _dt.date.fromtimestamp(luc) if luc > 0 else None
    except (OverflowError, OSError, ValueError):
        d0 = None
    if d0 is None:   # ảnh chụp không ghi ngày đo → mốc là video mới nhất (không coi mọi video là "gần")
        d0 = max(d for d, _w in ngay) if ngay else _dt.date.today()
    tv = float(statistics.median(views)) if views else 0.0
    # ngày đăng của yt-dlp là xấp xỉ — có thể lệch sau ngày chụp vài ngày
    gan = [w for d, w in ngay if -3 <= (d0 - d).days <= 30 and w >= 0]
    vt = sum(w for d, w in ngay if -3 <= (d0 - d).days <= 90 and w >= 0) / (90 / 30.44)
    try:
        subs = int((ch or {}).get("subscribers"))
    except (TypeError, ValueError):
        subs = -1
    return {"luc": float(luc), "moi": max(d for d, _w in ngay).isoformat() if ngay else "",
            "cu": min(d for d, _w in ngay).isoformat() if ngay else "", "du": bool((ch or {}).get("complete")),
            "n": len(vs), "tv": tv, "vt": round(vt), "bung": (max(gan) / tv) if (gan and tv > 0) else 0.0,
            "bung_view": max(gan) if gan else 0, "subs": subs}


def _gop_tom(tom: Dict[str, Dict[str, Any]], ch: Dict[str, Any], luc: float, quet: bool) -> None:
    """Ảnh chụp mới nhất của mỗi mã kênh thắng; `moi` = ngày đăng mới nhất từng thấy; `quet` = lần quét content gần
    nhất của nhóm (ảnh chụp `quet-kenh/`)."""
    cid = str((ch or {}).get("channel_id") or "").strip()
    if not _RE_UC.match(cid):
        return
    t = _tom_anh(ch, luc)
    if t is None:
        return
    cu = tom.get(cid)
    if cu is None or t["luc"] >= cu["luc"]:
        t["moi"] = max(t["moi"], (cu or {}).get("moi") or "")
        t["quet"] = max(float((cu or {}).get("quet") or 0.0), luc if quet else 0.0)
        tom[cid] = t
    else:
        cu["moi"] = max(cu.get("moi") or "", t["moi"])
        if quet:
            cu["quet"] = max(float(cu.get("quet") or 0.0), luc)


def _them_bi_danh(ra: Dict[str, str], ch: Dict[str, Any]) -> None:
    cid = str((ch or {}).get("channel_id") or "").strip()
    if not _RE_UC.match(cid):
        return
    for l in ((ch or {}).get("input_url"), (ch or {}).get("channel_url"),
              "https://www.youtube.com/channel/" + cid,
              ("https://www.youtube.com/" + str(ch.get("handle"))) if str((ch or {}).get("handle") or "").startswith("@")
              else ""):
        k = db.khoa(str(l or ""))
        if k:
            ra.setdefault(k, cid)


def _ep_ngay_kho(ngay: Any) -> float:
    """"2026-10-12" (ngày đo của `kenh-do.json`) → epoch 12:00 giờ máy ngày ấy; hỏng → 0."""
    try:
        d = _dt.date.fromisoformat(str(ngay or "")[:10])
    except ValueError:
        return 0.0
    return time.mktime(_dt.datetime(d.year, d.month, d.day, 12, 0).timetuple())


def _anh_chup(goc: str, nhom: str) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """`({khoá link: "UC…"}, {"UC…": tóm ảnh chụp})` từ ảnh chụp kênh của kho nhóm (`kenh-do.json`,
    `quet-kenh/*.json`). `kenh-do.json` ~27 MB → nhớ trong tiến trình theo giờ sửa tệp / thư mục."""
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        kho = os.path.join(thu_muc(goc, nhom), ncc.THU_MUC)
    except Exception:  # noqa: BLE001
        return {}, {}
    p_do = os.path.join(kho, ncc.TEP_KENH_DO)
    d_q = os.path.join(kho, ncc.THU_MUC_QUET)
    try:
        dau = (os.path.getmtime(p_do), float(os.path.getsize(p_do)))
    except OSError:
        dau = (0.0, 0.0)
    try:
        dau = dau + (os.path.getmtime(d_q),)
    except OSError:
        pass
    nho = _NHO_BI_DANH.get(kho)
    if nho is None or nho[0] != dau:
        moi: Dict[str, str] = {}
        tom: Dict[str, Dict[str, Any]] = {}
        du = _doc_json(p_do, {}) or {}
        if isinstance(du, dict):
            for m in du.values():
                if isinstance(m, dict):
                    _them_bi_danh(moi, m.get("ch") or {})
                    _gop_tom(tom, m.get("ch") or {}, _ep_ngay_kho(m.get("ngay")), False)
        try:
            ten = os.listdir(d_q)
        except OSError:
            ten = []
        for t in ten:
            if t.endswith(".json"):
                m = _doc_json(os.path.join(d_q, t), {}) or {}
                if isinstance(m, dict):
                    _them_bi_danh(moi, m.get("ch") or {})
                    try:
                        luc = float(m.get("luc") or 0.0)
                    except (TypeError, ValueError):
                        luc = 0.0
                    _gop_tom(tom, m.get("ch") or {}, luc, True)
        _NHO_BI_DANH[kho] = (dau, moi, tom)
        nho = _NHO_BI_DANH[kho]
    return nho[1], nho[2]


def bang_bi_danh(goc: str, nhom: str, cu: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """`{khoá link: "UC…"}` từ ảnh chụp kênh của kho nhóm (`kenh-do.json`, `quet-kenh/*.json`) + bí danh đã nhớ."""
    ra: Dict[str, str] = dict(cu or {})
    for k, v in _anh_chup(goc, nhom)[0].items():
        ra.setdefault(k, v)
    return ra


def khoa_chuan(link: str, bi_danh: Dict[str, str]) -> str:
    """Khoá chuẩn của một link kênh: mã `UC…` khi biết, không thì `danh_ba_doi_thu.khoa`.

    `db.khoa` hạ chữ thường khoá ASCII (`@Handle` ≡ `@handle` thật), nhưng mã kênh UC… PHÂN BIỆT hoa thường — trước
    13/10 link `/channel/UC…` chưa có ảnh chụp ra khoá `channel/uc…` (3 dòng sổ thật), lệch với dòng `UC…` của cùng
    kênh khi ảnh chụp về sau. Lấy lại mã từ link GỐC.

    >>> khoa_chuan("https://www.youtube.com/channel/UCfakeTangAaaaaaaaaaaaaa/videos", {})
    'UCfakeTangAaaaaaaaaaaaaa'
    """
    k = db.khoa(link)
    if not k:
        return ""
    if k in bi_danh:
        return bi_danh[k]
    if k.lower().startswith("channel/"):
        m = _RE_UC_LINK.search(unquote(str(link or "")))
        if m:
            return m.group(1)
        uc = k.split("/", 1)[1]
        if _RE_UC.match(uc):
            return uc
    return k


# ── đọc sổ riêng + kho phán quyết ────────────────────────────────────────────

def _rieng(goc: str, kenh: str) -> bool:
    """Kênh dùng kho phán quyết ngách RIÊNG (`cho_phep_tep_gia`) — xem luật 4."""
    try:
        from .phan_tuyen import cho_phep_tep_gia  # noqa: PLC0415

        return bool(cho_phep_tep_gia(goc, kenh))
    except Exception:  # noqa: BLE001
        return False


def _ban_dua(goc: str, kenh: str) -> Set[str]:
    try:
        from .doi_thu_kenh import doc_ban_dua  # noqa: PLC0415

        return {k for k in (db.khoa(l) for l in doc_ban_dua(goc, kenh)) if k}
    except Exception:  # noqa: BLE001
        return set()


def _kenh_ai_nhom(goc: str, nhom: str) -> Dict[str, Dict[str, Any]]:
    """Kho phán quyết ngách CHUNG của nhóm (`CHANNEL/_NHOM/<nhóm>/nghien-cuu/kenh-ai.json`)."""
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        p = os.path.join(thu_muc(goc, nhom), ncc.THU_MUC, ncc.TEP_KENH_AI)
    except Exception:  # noqa: BLE001
        return {}
    du = _doc_json(p, {}) or {}
    return du if isinstance(du, dict) else {}


def _lop_kenh_ai(m: Dict[str, Any]) -> str:
    kn = str(m.get("kiem_ngach") or "").strip().lower()
    if kn in ("giu", "bo", "nghi"):
        return kn
    return {"doi_thu": "giu", "khong": "bo", "gan": "bo"}.get(str(m.get("ket") or "").strip().lower(), "")


def _o(dong: Sequence[str], o: Dict[str, int], ten: str) -> str:
    i = o.get(ten)
    return str(dong[i]).strip() if i is not None and i < len(dong) else ""


# ── gộp ──────────────────────────────────────────────────────────────────────

def _dung_lai(goc: str, nhom: str, thanh_vien: Sequence[str], cu: Dict[str, Any],
              lien_quan: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None) -> Dict[str, Any]:
    """Dựng sổ chung TỪ ĐẦU (luật 1). `cu` = sổ cũ — chỉ mang sang bí danh, mốc gieo, lần đầu thấy, liên quan, mốc
    đột biến của tầng. `lien_quan` (radar vừa tính) đè phần liên quan TRƯỚC khi xếp tầng."""
    bi = bang_bi_danh(goc, nhom, cu.get("bi_danh") or {})
    kenh_cu = cu.get("kenh") or {}
    for e in kenh_cu.values():   # bí danh suy từ sổ cũ: mọi link của một dòng UC… là bí danh của mã ấy
        if isinstance(e, dict) and _RE_UC.match(str(e.get("khoa") or "")):
            for l in e.get("lien_ket") or []:
                k = db.khoa(l)
                if k:
                    bi.setdefault(k, e["khoa"])
    kenh: Dict[str, Dict[str, Any]] = {}
    rieng = {m: _rieng(goc, m) for m in thanh_vien}
    n_dong = 0
    for m in thanh_vien:
        cot, hang = db.doc(goc, m)
        o = db.chi_so_cot(list(cot))
        if o.get("Link kênh") is None:
            continue
        bd = _ban_dua(goc, m)
        for d in hang:
            link = _o(d, o, "Link kênh")
            k = khoa_chuan(link, bi)
            if not k:
                continue
            if _RE_UC.match(k):
                # khoá thường của link (`channel/uc…`) → mã gốc: kho `kenh-ai.json` ghi khoá link hạ chữ thường
                bi.setdefault(db.khoa(link), k)
            n_dong += 1
            e = kenh.get(k)
            if e is None:
                e = kenh[k] = {"khoa": k, "uc": k if _RE_UC.match(k) else "", "link": link, "lien_ket": [],
                               "ten": "", "so": {}, "so_luc": "", "quet_luc": "", "lan_dau": "",
                               "ban_dua": False, "theo_kenh": {}, "_su_kien": []}
            if link not in e["lien_ket"]:
                e["lien_ket"].append(link)
            quet = _o(d, o, "Quét lúc")
            ten = _o(d, o, "Kênh")
            moi_hon = quet >= e["so_luc"]
            if ten and (moi_hon or not e["ten"]):
                e["ten"] = ten
            if ten and ten not in e.setdefault("ten_khac", []):
                e["ten_khac"].append(ten)   # sổ content nối với danh bạ bằng TÊN — radar tra mọi tên từng thấy
            for c in COT_SO_CHUNG + COT_SO_RIENG:
                v = _o(d, o, c)
                if v and (moi_hon or not e["so"].get(c)):
                    e["so"][c] = v
            if moi_hon and quet:
                e["so_luc"] = quet
                e["link"] = link
            e["quet_luc"] = max(e["quet_luc"], quet)
            ld = _o(d, o, "Lần đầu thấy")
            if ld and (not e["lan_dau"] or ld < e["lan_dau"]):
                e["lan_dau"] = ld
            ghi = _o(d, o, "Ghi chú")
            tt = _o(d, o, "Trạng thái")
            ban = {"tt": tt, "tuyen": _o(d, o, "Tuyến"), "ghi": ghi, "cua": _o(d, o, "Cửa"),
                   "diem": _o(d, o, "Điểm"), "ly": _o(d, o, "Lý do"), "quet": quet, "lan_dau": ld, "link": link}
            ban = {a: b for a, b in ban.items() if b or a == "tt"}   # ô trống không ghi (sổ gọn); đọc bằng .get
            if m in e["theo_kenh"]:
                # Cùng một kênh hai dòng trong MỘT sổ (`@handle` + `/channel/UC…` — quét ghi link yt-dlp trả về):
                # dòng đầu là dòng chính, dòng sau giữ nguyên văn ở `trung` (không mất ghi chú nào).
                e["theo_kenh"][m].setdefault("trung", []).append(ban)
            else:
                e["theo_kenh"][m] = ban
            lop, ngay = phan_loai_ghi_chu(ghi, quet)
            if lop == "ban_dua" or db.khoa(link) in bd:
                e["ban_dua"] = True
            if lop in ("giu", "bo", "nghi") and rieng.get(m):
                continue   # phán quyết ngách theo TỆP của kênh có kho riêng — không phải sự thật chung
            if lop in ("giu", "bo", "nghi", "het", "chet", "lech_tieng"):
                e["_su_kien"].append((ngay, _UU_TIEN[lop], lop, m, ghi))
    # Kho phán quyết ngách của nhóm (nguồn sự thật về ngách — `kiem_ngach_doi_thu`).
    kai = _kenh_ai_nhom(goc, nhom)
    tra_ai: Dict[str, Dict[str, Any]] = {}
    for l, m in kai.items():
        if isinstance(m, dict):
            k = khoa_chuan(str(l), bi)
            if k and (k not in tra_ai or str(m.get("ngay") or "") > str(tra_ai[k].get("ngay") or "")):
                tra_ai[k] = m
    for k, e in kenh.items():
        ev = sorted(e.pop("_su_kien"), key=lambda x: (x[0], x[1]))
        m = tra_ai.get(k)
        lop_ai = _lop_kenh_ai(m) if m else ""
        ngach = None
        dong_ngach = [x for x in ev if x[2] in ("giu", "bo", "nghi")]
        if dong_ngach:
            x = dong_ngach[-1]
            ngach = {"ket": x[2], "ngay": x[0], "ly_do": x[4][:200], "nguon": "so:" + x[3]}
        if lop_ai and (ngach is None or str(m.get("ngay") or "") >= ngach["ngay"]):
            ngach = {"ket": lop_ai, "ngay": str(m.get("ngay") or ""), "ly_do": str(m.get("ly_do") or "")[:200],
                     "nguon": "kenh-ai"}
        e["ngach"] = ngach
        song = None
        for x in ev:
            if x[2] in ("chet", "lech_tieng"):
                song = {"ket": x[2], "ngay": x[0], "ly_do": x[4][:200], "nguon": "so:" + x[3]}
        if song is None:
            het = [x for x in ev if x[2] == "het"]
            giu = [x for x in ev if x[2] == "giu"]
            if het and (not giu or het[-1][0] >= giu[-1][0]):
                x = het[-1]
                song = {"ket": "het", "ngay": x[0], "ly_do": x[4][:200], "nguon": "so:" + x[3]}
        e["song"] = song
        e["gieo"] = _phan_quyet_gieo(e, ev)
        e["trang_thai"] = (e["gieo"] or {}).get("trang_thai") or _da_so(e)
        e["lien_quan"] = dict((kenh_cu.get(k) or {}).get("lien_quan") or {})
        if (kenh_cu.get(k) or {}).get("lan_dau") and (not e["lan_dau"] or kenh_cu[k]["lan_dau"] < e["lan_dau"]):
            e["lan_dau"] = kenh_cu[k]["lan_dau"]
    for k, e in kenh.items():
        for l in e["lien_ket"]:
            kk = db.khoa(l)
            if kk and _RE_UC.match(k):
                bi[kk] = k
    du = {"phien_ban": PHIEN_BAN, "nhom": nhom, "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
          "thanh_vien": list(thanh_vien), "bi_danh": bi, "gieo": dict(cu.get("gieo") or {}), "kenh": kenh}
    _ap_lien_quan(du, lien_quan)
    try:
        phan_tang(du, goc=goc, nhom=nhom, cu=cu)
    except Exception:  # noqa: BLE001 — tầng hỏng không được làm hỏng sổ (lượt quét thiếu tầng = quét như cũ)
        pass
    du["thong_ke"] = thong_ke_so(du, n_dong=n_dong)
    return du


def _da_so(e: Dict[str, Any]) -> str:
    dem: Dict[str, int] = {}
    for x in (e.get("theo_kenh") or {}).values():
        t = x.get("tt") or db.THEO_DOI
        dem[t] = dem.get(t, 0) + 1
    return max(dem.items(), key=lambda kv: (kv[1], kv[0] == db.THEO_DOI))[0] if dem else ""


def _phan_quyet_gieo(e: Dict[str, Any], ev: Sequence[Tuple[str, int, str, str, str]]) -> Optional[Dict[str, Any]]:
    """Trạng thái + Ghi chú NGUYÊN VĂN để gieo dòng này vào sổ riêng còn thiếu (luật 3–4), hoặc None."""
    def ghi_cua(lop: str) -> Tuple[str, str]:
        ds = [x for x in ev if x[2] == lop]
        return (ds[-1][4], ds[-1][3]) if ds else ("", "")
    song, ngach = e.get("song") or {}, e.get("ngach") or {}
    # Thứ tự = thứ tự của cửa duyệt `chot_doi_thu._chot`: kênh chết / sai tiếng → sức sống (cả kênh bạn đưa) →
    # bạn đưa (luôn quét, không hỏi AI) → phán quyết ngách.
    if song.get("ket") in ("chet", "lech_tieng"):
        g, tu = ghi_cua(song["ket"])
        return {"trang_thai": db.BO, "ghi_chu": g, "tu": tu, "lop": song["ket"]}
    if song.get("ket") == "het":
        g, tu = ghi_cua("het")
        return {"trang_thai": db.HET, "ghi_chu": g, "tu": tu, "lop": "het"}
    if e.get("ban_dua"):
        g, tu = "", ""
        for m, x in (e.get("theo_kenh") or {}).items():
            if str(x.get("ghi") or "").startswith(GHI_CHU_BAN_DUA):
                g, tu = x["ghi"], m
                break
        return {"trang_thai": db.THEO_DOI, "ghi_chu": g or GHI_CHU_BAN_DUA, "tu": tu, "lop": "ban_dua"}
    if ngach.get("ket") == "bo":
        g, tu = ghi_cua("bo")
        if not g:
            g = "không phải kênh tâm lý — AI (sổ chung {0}): {1}".format(_dd_mm(ngach.get("ngay")),
                                                                        str(ngach.get("ly_do") or "")[:150])
            tu = "kenh-ai"
        return {"trang_thai": db.BO, "ghi_chu": g, "tu": tu, "lop": "bo"}
    if ngach.get("ket") == "giu":
        g, tu = ghi_cua("giu")
        if not g:
            g = "AI (sổ chung {0}): đối thủ — {1}".format(_dd_mm(ngach.get("ngay")), str(ngach.get("ly_do") or "")[:150])
            tu = "kenh-ai"
        return {"trang_thai": db.THEO_DOI, "ghi_chu": g, "tu": tu, "lop": "giu"}
    return None


def _dd_mm(ngay: Any) -> str:
    s = str(ngay or "")
    return "{0}/{1}".format(s[8:10], s[5:7]) if len(s) >= 10 else "?"


def thong_ke_so(du: Dict[str, Any], *, n_dong: Optional[int] = None) -> Dict[str, Any]:
    kenh = du.get("kenh") or {}
    tt: Dict[str, int] = {}
    gieo: Dict[str, int] = {}
    for e in kenh.values():
        tt[e.get("trang_thai") or "?"] = tt.get(e.get("trang_thai") or "?", 0) + 1
        g = (e.get("gieo") or {}).get("lop") or "khong"
        gieo[g] = gieo.get(g, 0) + 1
    tang: Dict[str, int] = {}
    for e in kenh.values():
        if e.get("tang"):
            tang[e["tang"]] = tang.get(e["tang"], 0) + 1
    ra = {"kenh": len(kenh), "trang_thai": tt, "gieo_duoc": gieo,
          "tang": {t: tang.get(t, 0) for t in TANG} if tang else {},
          "uc": sum(1 for e in kenh.values() if e.get("uc")),
          "ban_dua": sum(1 for e in kenh.values() if e.get("ban_dua")),
          "ghi_chu_rieng": sum(1 for e in kenh.values() for x in (e.get("theo_kenh") or {}).values() if x.get("ghi"))}
    if n_dong is not None:
        ra["dong_so_rieng"] = n_dong
    return ra


def gop(goc: str, nhom: str, *, thanh_vien: Optional[Sequence[str]] = None, ghi: bool = True,
        lien_quan: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None) -> Dict[str, Any]:
    """Dựng lại sổ chung của `nhom` từ mọi sổ riêng + kho phán quyết (luật 1–2) và ghi (`ghi=True`). Trả sổ.
    `lien_quan` (`{khoá: {kênh: {...}}}`, `radar_dot_bien` tính) → ghi đè phần liên quan của các dòng ấy."""
    tv = list(thanh_vien) if thanh_vien is not None else thanh_vien_nhom(goc, nhom)
    if not nhom or not tv:
        return {}
    if not ghi:
        return _dung_lai(goc, nhom, tv, doc(goc, nhom), lien_quan=lien_quan)
    with _khoa_ghi(goc, nhom):
        du = _dung_lai(goc, nhom, tv, doc(goc, nhom), lien_quan=lien_quan)
        _ghi(goc, nhom, du)
    return du


def _ap_lien_quan(du: Dict[str, Any], lien_quan: Optional[Dict[str, Dict[str, Dict[str, Any]]]]) -> None:
    for k, x in (lien_quan or {}).items():
        e = (du.get("kenh") or {}).get(k)
        if e is not None and isinstance(x, dict):
            e["lien_quan"] = x


# ── tầng đối thủ ─────────────────────────────────────────────────────────────

def _so_f(x: Any) -> float:
    try:
        v = float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def _gon(x: float) -> str:
    """46900 → "46,9k" — lý do tầng phải ngắn."""
    if x >= 1e6:
        return "{0:.1f}M".format(x / 1e6).replace(".", ",")
    if x >= 1e3:
        return "{0:.1f}k".format(x / 1e3).replace(".", ",")
    return "{0:.0f}".format(x)


def _dang_theo(x: Dict[str, Any]) -> bool:
    """Dòng sổ riêng (hoặc một dòng trùng của nó) đang được quét — trạng thái trống tính là theo dõi (y
    `danh_ba_doi_thu.dang_theo_doi`)."""
    return any((d.get("tt") or db.THEO_DOI) == db.THEO_DOI for d in [x] + list(x.get("trung") or []))


def _khoa_theo_ten(kenh: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """`{tên kênh: khoá}` — hai kênh trùng tên (12 cặp ở sổ thật) thì kênh nhiều kênh ta theo dõi hơn thắng."""
    ra: Dict[str, str] = {}
    hang: Dict[str, int] = {}
    for k, e in kenh.items():
        n = sum(1 for x in (e.get("theo_kenh") or {}).values() if _dang_theo(x))
        for t in [e.get("ten")] + list(e.get("ten_khac") or []):
            t = str(t or "").strip()
            if t and (t not in ra or n > hang[t]):
                ra[t], hang[t] = k, n
    return ra


def _tin_hieu_radar(goc: str, nhom: str, du: Dict[str, Any], hom_nay: _dt.date) -> Dict[str, Dict[str, Any]]:
    """`{khoá: {ngay, muc, boi, nguon}}` — video nổ (mức ≥ `MUC_DOT_BIEN_TANG`) trong `NGAY_DOT_BIEN_TANG` ngày:
    bảng radar mới nhất + sổ quyết định của radar (`core/radar_dot_bien.py`)."""
    try:
        from . import radar_dot_bien as rdb  # noqa: PLC0415

        d = os.path.join(thu_muc(goc, nhom), rdb.THU_MUC)
        p_moi, p_qd = os.path.join(d, rdb.TEP_MOI), os.path.join(d, rdb.TEP_QUYET)
    except Exception:  # noqa: BLE001
        return {}
    kenh = du.get("kenh") or {}
    ten = _khoa_theo_ten(kenh)
    moc = (hom_nay - _dt.timedelta(days=NGAY_DOT_BIEN_TANG)).isoformat()
    ra: Dict[str, Dict[str, Any]] = {}

    def them(k: str, ngay: str, muc: float, boi: float, nguon: str) -> None:
        if not k or k not in kenh or len(ngay) < 10 or ngay < moc or muc < MUC_DOT_BIEN_TANG:
            return
        cu = ra.get(k)
        if cu is None or (ngay, boi) > (cu["ngay"], cu["boi"]):
            ra[k] = {"ngay": ngay, "muc": int(muc), "boi": round(boi, 1), "nguon": nguon}
    bang = _doc_json(p_moi, {}) or {}
    if isinstance(bang, dict):
        ngay = str(bang.get("luc") or "")[:10]
        for x in bang.get("dong") or []:
            if isinstance(x, dict):
                k = str(x.get("kenh_khoa") or "")
                if k not in kenh:
                    k = ten.get(str(x.get("kenh_nguon") or "").strip(), "")
                them(k, ngay, _so_f(x.get("muc")), _so_f(x.get("boi")), "radar")
    try:
        with io.open(p_qd, encoding="utf-8") as tep:
            for dong in tep:
                try:
                    x = json.loads(dong)
                except ValueError:
                    continue
                if isinstance(x, dict):
                    them(ten.get(str(x.get("kenh_nguon") or "").strip(), ""), str(x.get("luc") or "")[:10],
                         _so_f(x.get("muc")), _so_f(x.get("boi")), "quyết định radar")
    except OSError:
        pass
    return ra


def _dat_tang(e: Dict[str, Any], tang: str, ly_do: str) -> None:
    e["tang"] = tang
    e["tang_ly_do"] = ly_do[:220]


def phan_tang(du: Dict[str, Any], *, goc: str = "", nhom: str = "", cu: Optional[Dict[str, Any]] = None,
              hom_nay: Optional[_dt.date] = None, anh: Optional[Dict[str, Dict[str, Any]]] = None,
              radar: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, int]:
    """Xếp tầng mọi dòng sổ chung (luật ở "TẦNG ĐỐI THỦ" đầu tệp) → ghi `tang`, `tang_ly_do`, `tang_diem`,
    `dang_moi` (ngày đăng mới nhất biết được), `dot_bien` (mốc nổ radar, dính `NGAY_DOT_BIEN_TANG` ngày qua các lần
    gộp) vào từng dòng. Không đụng phần nào khác của dòng (ghi chú, phán quyết riêng). Trả `{tầng: số kênh}`.
    `anh` (`{"UC…": tóm ảnh chụp}`) / `radar` (`{khoá: tín hiệu}`) để `None` → đọc từ kho nhóm `goc`/`nhom`."""
    kenh = du.get("kenh") or {}
    hom_nay = hom_nay or _dt.date.today()
    if anh is None:
        anh = _anh_chup(goc, nhom)[1] if (goc and nhom) else {}
    if radar is None:
        radar = _tin_hieu_radar(goc, nhom, du, hom_nay) if (goc and nhom) else {}
    kenh_cu = (cu or {}).get("kenh") or {}
    moc_db = (hom_nay - _dt.timedelta(days=NGAY_DOT_BIEN_TANG)).isoformat()
    ung: List[Tuple[float, str]] = []
    tam: Dict[str, Tuple[str, List[str], bool]] = {}   # khoá → (số đo, tín hiệu đang lên, đủ cỡ / bạn đưa)
    for k, e in kenh.items():
        so = e.get("so") or {}
        a = anh.get(k) or (anh.get(str(e.get("uc") or "")) if e.get("uc") else None) or {}
        moi = max(str(a.get("moi") or ""), str(so.get("Đăng gần nhất") or "")[:10])
        e["dang_moi"] = moi
        try:
            im: Optional[int] = (hom_nay - _dt.date.fromisoformat(moi)).days if moi else None
        except ValueError:
            im = None
        dot = radar.get(k)
        dcu = (kenh_cu.get(k) or {}).get("dot_bien")
        if isinstance(dcu, dict) and str(dcu.get("ngay") or "") >= moc_db \
                and (dot is None or str(dcu.get("ngay") or "") > str(dot.get("ngay") or "")):
            dot = dcu
        if dot:
            e["dot_bien"] = dict(dot)
        else:
            e.pop("dot_bien", None)
        song = (e.get("song") or {}).get("ket")
        bd = bool(e.get("ban_dua"))
        theo = [m for m, x in (e.get("theo_kenh") or {}).items() if isinstance(x, dict) and _dang_theo(x)]
        if song in ("chet", "lech_tieng"):
            e.pop("tang_diem", None)
            _dat_tang(e, NGOAI, "ngoài: kênh chết / không xem được — không quét lại" if song == "chet"
                      else "ngoài: sai tiếng — không quét lại")
            continue
        if song == "het":
            e.pop("tang_diem", None)
            _dat_tang(e, NGOAI, "ngoài: hết (không còn làm / không phát triển){0} — đo lại hằng tháng".format(
                " · bạn đưa" if bd else ""))
            continue
        if not theo and not bd:
            e.pop("tang_diem", None)
            tt = e.get("trang_thai") or ""
            _dat_tang(e, NGOAI, "ngoài: " + {db.BO: "bỏ ở mọi kênh ta (lạc ngách) — không quét lại",
                                             db.HET: "hết ở mọi kênh ta — đo lại hằng tháng",
                                             db.TAM_NGUNG: "tạm ngưng ở mọi kênh ta"}.get(
                tt, "không kênh ta nào theo dõi"))
            continue
        subs = _so_f(so.get("Subs")) or float(max(0, int(a.get("subs") or 0)))
        tv = _so_f(so.get("View TV")) or float(a.get("tv") or 0.0)
        lq = e.get("lien_quan") or {}
        tc = sum(int(_so_f((x or {}).get("tc"))) for x in lq.values() if isinstance(x, dict))
        pool = sum(int(_so_f((x or {}).get("pool"))) for x in lq.values() if isinstance(x, dict))
        # video nổ trên radar ≤ 7 ngày tuổi → kênh vừa đăng, dù ảnh chụp cũ
        song_ok = (im is not None and im <= NGAY_SONG_TANG) or bool(dot)
        tin: List[str] = []
        if dot:
            tin.append("radar ×{0} {1}".format(_gon(_so_f(dot.get("boi"))), _dd_mm(dot.get("ngay"))))
        try:
            anh_moi = (hom_nay - _dt.date.fromtimestamp(float(a.get("luc") or 0))).days <= 30
        except (OverflowError, OSError, ValueError):
            anh_moi = False
        if anh_moi and float(a.get("bung") or 0) >= BUNG_TANG_2 and float(a.get("bung_view") or 0) >= BUNG_VIEW_TANG_2:
            tin.append("video gần ×{0:.0f} trung vị".format(float(a["bung"])))
        thang = None
        if a.get("du") and a.get("cu"):
            try:
                thang = (hom_nay - _dt.date.fromisoformat(str(a["cu"]))).days / 30.44
            except ValueError:
                thang = None
        vt = float(a.get("vt") or 0.0)
        if thang is None and _so_f(so.get("Tuổi (tháng)")):
            thang, vt = _so_f(so.get("Tuổi (tháng)")), max(vt, _so_f(so.get("View/tháng")))
        if thang is not None and thang <= THANG_TRE_TANG_2 and vt >= VIEW_THANG_TRE_TANG_2:
            tin.append("kênh trẻ {0:.0f} tháng, {1}/tháng".format(max(thang, 1.0), _gon(vt)))
        vuot = _so_f(so.get("Vượt quy mô"))
        if vuot >= VUOT_TANG_2 and vuot * subs >= VIEW_VUOT_TANG_2:
            tin.append("vượt quy mô ×{0:.0f}".format(vuot))
        info = "{0} subs · view TV {1} · {2}".format(_gon(subs), _gon(tv), "im {0} ngày".format(im) if im is not None
                                                     else "chưa rõ ngày đăng")
        if tc or pool:
            info += " · trang chủ {0} · pool {1}".format(tc, pool)
        diem = (math.log10(max(tv, 1.0)) + 0.5 * math.log10(max(subs, 1.0)) + 0.4 * math.log10(1.0 + tc)
                + 0.6 * math.log10(1.0 + pool) + (0.5 if dot else 0.0) + (0.3 if bd else 0.0)
                - (0.01 * min(im, 60) if im is not None else 0.3))
        e["tang_diem"] = round(diem, 3)
        lon = subs >= SUBS_TANG_1 or tv >= VIEW_TV_TANG_1
        tam[k] = (info, tin, lon or bd)
        co_mat = pool >= POOL_TANG_1 or tc >= TC_TANG_1
        if song_ok and (lon or co_mat):
            ung.append((diem, k))
        elif song_ok and tin:
            _dat_tang(e, TANG_2, "đang lên: {0} — {1}".format(" · ".join(tin), info))
        else:
            ly = ("im {0} ngày".format(im) if im is not None and not song_ok
                  else "chưa đo được ngày đăng" if im is None else "nhỏ, chưa có tín hiệu")
            if bd:
                _dat_tang(e, TANG_2, "bạn đưa — luôn ≥ tầng 2 ({0}) — {1}".format(ly, info))
            else:
                _dat_tang(e, TANG_3, "nhẹ: {0} — {1}".format(ly, info))
    ung.sort(key=lambda x: (-x[0], x[1]))
    for i, (_d, k) in enumerate(ung, 1):
        info, tin, lon = tam[k]
        if i <= TRAN_TANG_1:
            _dat_tang(kenh[k], TANG_1, "lõi #{0}: {1}{2}".format(i, info, (" · " + " · ".join(tin)) if tin else ""))
        elif lon:
            _dat_tang(kenh[k], TANG_2, "đủ cỡ tầng 1, ngoài trần {0} (hạng {1}): {2}{3}".format(
                TRAN_TANG_1, i, info, (" · " + " · ".join(tin)) if tin else ""))
        elif tin:
            _dat_tang(kenh[k], TANG_2, "đang lên: {0} — {1}".format(" · ".join(tin), info))
        else:
            _dat_tang(kenh[k], TANG_3, "nhẹ: có mặt ở khán giả ta nhưng nhỏ, ngoài trần {0} — {1}".format(
                TRAN_TANG_1, info))
    dem = {t: 0 for t in TANG}
    for e in kenh.values():
        if e.get("tang") in dem:
            dem[e["tang"]] += 1
    return dem


def _ep_luc(s: Any) -> Optional[float]:
    """"2026-10-12 22:43" (giờ máy) → epoch; hỏng → None."""
    s = str(s or "").strip().replace("T", " ")
    for dang, dai in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
        try:
            return time.mktime(_dt.datetime.strptime(s[:dai], dang).timetuple())
        except ValueError:
            continue
    return None


def _tat_theo_tang() -> bool:
    return str(os.environ.get("MYTOOL_QUET_THEO_TANG", "")).strip().lower() in ("0", "false", "tat", "tắt", "off", "no")


def _trang_chu_gan(goc: str, kenh: str, bi: Dict[str, str]) -> Dict[str, float]:
    """`{khoá: epoch}` — lần gần nhất trang chủ máy ảo của `kenh` đẩy video MỚI (đăng ≤ `NGAY_VIDEO_MOI_TRANG_CHU`
    ngày trước lúc quét; không Short, không bị loại) của kênh đối thủ — dấu hiệu sớm nhất của một video sắp nổ."""
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    ra: Dict[str, float] = {}
    try:
        csv.field_size_limit(10_000_000)
        with io.open(os.path.join(thu_muc_nghien_cuu(goc, kenh), "trang-chu.csv"), encoding="utf-8-sig",
                     newline="") as tep:
            for r in csv.DictReader(tep):
                if str(r.get("Short") or "").strip() or str(r.get("Bị loại") or "").strip():
                    continue
                t = _ep_luc(r.get("Lúc quét"))
                dang = _ep_luc(str(r.get("Đăng") or "")[:10])
                if t is None or dang is None or t - dang > (NGAY_VIDEO_MOI_TRANG_CHU + 1) * 86400.0:
                    continue
                k = khoa_chuan(str(r.get("Link kênh") or ""), bi)
                if k and t > ra.get(k, 0.0):
                    ra[k] = t
    except (OSError, ValueError, csv.Error):
        return {}
    return ra


def loc_quet(goc: str, kenh: str, links: Sequence[str], *, du: Optional[Dict[str, Any]] = None,
             bay_gio: Optional[float] = None, on_log: Optional[Callable[[str], None]] = None,
             trang_chu: Optional[Dict[str, float]] = None) -> Tuple[List[str], Dict[str, Any]]:
    """Bước 3 của `mot_nut` (quét content đối thủ): trong `links` (kênh `theo dõi` của `kenh`) chỉ giữ kênh ĐẾN HẠN
    theo tầng — đã qua `NGAY_QUET_TANG[tầng]` ngày từ lần quét content gần nhất của CHÍNH sổ `kenh`
    (`quet_doi_thu.moc_quet_kenh`; kênh chưa có mốc = chưa quét → quét ngay) — xếp tầng 1 → kênh mới → 2 → 3 → ngoài;
    một kênh hai link (`@handle` + `/channel/UC…`) chỉ giữ một. Đến hạn sớm khi: ảnh chụp nhóm (`quet-kenh/`) còn
    tươi mà sổ này chưa ăn (kênh anh em vừa quét — miễn phí), hoặc trang chủ máy ảo của `kenh` vừa đẩy video mới của
    nó sau lần quét trước (`trang_chu` = `{khoá: epoch}`, để `None` → đọc `trang-chu.csv`). Sổ chưa có mốc từng kênh
    nào (bản trước 13/10) → quét đủ một lượt để ghi mốc. Trả `(link sẽ quét, đếm)`. Không nhóm / sổ chung chưa có tầng
    / `MYTOOL_QUET_THEO_TANG=0` / lỗi → nguyên `links` (quét như cũ). Không bao giờ ném."""
    links = [str(l).strip() for l in links if str(l).strip()]
    dem: Dict[str, Any] = {"vao": len(links), "quet": len(links), "hoan": 0, "trung": 0, "theo_tang": {}, "som": {}}
    try:
        if _tat_theo_tang() or not links:
            return links, dem
        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return links, dem
        du = du if du is not None else doc(goc, nhom)
        kenh_du = du.get("kenh") or {}
        if not kenh_du or not any(e.get("tang") for e in kenh_du.values()):
            return links, dem
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415
        from .quet_doi_thu import moc_quet_kenh  # noqa: PLC0415

        bi = du.get("bi_danh") or {}
        bay_gio = float(bay_gio or time.time())
        anh = _anh_chup(goc, nhom)[1]
        moc = moc_quet_kenh(goc, kenh)
        rieng: Dict[str, float] = {}
        for kk, t in moc.items():
            k = khoa_chuan("https://www.youtube.com/" + kk, bi)
            if k and t > rieng.get(k, 0.0):
                rieng[k] = t
        tc = (trang_chu if trang_chu is not None else _trang_chu_gan(goc, kenh, bi)) if moc else {}
        tuoi_anh = max(0.0, float(ncc.HAN_QUET_GIO) - 1.0) * 3600.0   # chừa 1 giờ cho chính lượt quét
        chon: List[Tuple[int, int, str]] = []
        thay: Set[str] = set()
        for i, l in enumerate(links):
            k = khoa_chuan(l, bi) or l
            if k in thay:
                dem["trung"] += 1
                continue
            thay.add(k)
            e = kenh_du.get(k)
            t = str((e or {}).get("tang") or "")
            han = NGAY_QUET_TANG.get(t)
            q = rieng.get(k)
            a = float((anh.get(k) or {}).get("quet") or 0.0)
            ly = ""
            if e is None or han is None:
                ly = "mới"
            elif not moc:
                ly = "chưa có mốc từng kênh"
            elif q is None:
                ly = "chưa quét"
            elif bay_gio - q >= han * 86400.0:
                ly = "đến hạn"
            elif a and q < a - 60.0 and bay_gio - a < tuoi_anh:
                ly = "ảnh chụp nhóm còn tươi"
            elif t != TANG_1 and tc.get(k, 0.0) > q:   # tầng 1 đã quét hằng ngày — không đánh thức thêm
                ly = "trang chủ vừa thấy"
            x = dem["theo_tang"].setdefault(t or "moi", [0, 0])
            x[1] += 1
            if ly:
                x[0] += 1
                if ly not in ("đến hạn", "mới", "chưa quét", "chưa có mốc từng kênh"):
                    dem["som"][ly] = dem["som"].get(ly, 0) + 1
                chon.append((_HANG_TANG.get(t, 1), i, l))
            else:
                dem["hoan"] += 1
        chon.sort()
        ra = [l for _h, _i, l in chon]
        dem["quet"] = len(ra)
        if on_log is not None:
            on_log("  quét theo tầng: {0} · {1} kênh tới hạn / {2} theo dõi{3}{4} — hoãn {5} kênh chưa tới hạn".format(
                " · ".join("{0} {1}/{2}".format("tầng " + t if t in TANG[:3] else t, x[0], x[1])
                           for t, x in sorted(dem["theo_tang"].items(), key=lambda kv: _HANG_TANG.get(
                               "" if kv[0] == "moi" else kv[0], 9))),
                len(ra), len(thay), (" · sớm: " + ", ".join("{0} {1}".format(a, b) for a, b in dem["som"].items()))
                if dem["som"] else "", " · bỏ {0} link trùng kênh".format(dem["trung"]) if dem["trung"] else "",
                dem["hoan"]))
        return ra, dem
    except Exception as loi:  # noqa: BLE001 — lọc hỏng thì quét đủ như cũ
        if on_log is not None:
            on_log("  quét theo tầng hỏng, quét đủ như cũ: {0}".format(str(loi)[:120]))
        dem.update(quet=len(links), hoan=0)
        return links, dem


def den_han_do_lai(goc: str, kenh: str, links: Sequence[str], *, du: Optional[Dict[str, Any]] = None,
                   bay_gio: Optional[float] = None) -> Set[str]:
    """Link kênh hết / bỏ-vì-sức-sống mà đợt kiểm (`kiem_ngach_doi_thu.kiem`) nên đo lại bằng ảnh chụp mới: dòng sổ
    chung ở tầng `ngoai` chỉ đo lại khi ảnh chụp gần nhất của nhóm cũ hơn `NGAY_QUET_TANG["ngoai"]` ngày (hằng tháng);
    dòng không ở `ngoai` (kênh anh em còn theo dõi) / chưa có tầng / không ảnh chụp → đo như cũ. Không nhóm / lỗi →
    mọi link."""
    tat_ca = {str(l) for l in links}
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom or _tat_theo_tang():
            return tat_ca
        du = du if du is not None else doc(goc, nhom)
        kenh_du = du.get("kenh") or {}
        if not kenh_du:
            return tat_ca
        bi = du.get("bi_danh") or {}
        anh = _anh_chup(goc, nhom)[1]
        bay_gio = float(bay_gio or time.time())
        ra: Set[str] = set()
        for l in tat_ca:
            k = khoa_chuan(l, bi)
            e = kenh_du.get(k) or {}
            luc = float((anh.get(k) or {}).get("luc") or 0.0)
            if e.get("tang") != NGOAI or not luc or bay_gio - luc >= NGAY_QUET_TANG[NGOAI] * 86400.0:
                ra.add(l)
        return ra
    except Exception:  # noqa: BLE001
        return tat_ca


# ── gieo vào sổ riêng ────────────────────────────────────────────────────────

def ap_vao_so(goc: str, kenh: str, *, du: Optional[Dict[str, Any]] = None, ghi: bool = True,
              ban_dua: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Gieo phán quyết sổ chung vào sổ riêng của `kenh` (luật 3–5). Trả `{"gieo", "lam_moi", "bo_qua",
    "theo_lop": {...}, "links": [...]}`. `ghi=False` → chỉ đếm (chạy thử)."""
    dem: Dict[str, Any] = {"gieo": 0, "lam_moi": 0, "bo_qua": 0, "theo_lop": {}, "links": []}
    nhom = nhom_cua(goc, kenh)
    if not nhom:
        return dem
    du = du if du is not None else doc(goc, nhom)
    if not du.get("kenh"):
        return dem
    bi = du.get("bi_danh") or {}
    rieng = _rieng(goc, kenh)
    lop_duoc = LOP_GIEO_RIENG if rieng else LOP_GIEO
    cot, hang = db.doc(goc, kenh)
    cot = list(cot)
    o = db.chi_so_cot(cot)
    if o.get("Link kênh") is None:
        return dem
    hang = [list(d) + [""] * (len(cot) - len(d)) for d in hang]
    co: Dict[str, int] = {}
    for i, d in enumerate(hang):
        k = khoa_chuan(_o(d, o, "Link kênh"), bi)
        if k and k not in co:
            co[k] = i
    doi = False
    # (a) làm mới số đo chung của dòng đã có: ô TRỐNG thì điền; dòng "theo dõi" mà sổ chung quét mới hơn
    #     ≥ `NGAY_LAM_MOI` ngày thì đè (dòng bỏ/hết không ai dùng số của nó — không xáo sổ vô ích).
    for k, i in co.items():
        e = du["kenh"].get(k)
        if not e:
            continue
        d = hang[i]
        q = _o(d, o, "Quét lúc")
        de = (_o(d, o, "Trạng thái") or db.THEO_DOI) == db.THEO_DOI and bool(e.get("so_luc")) \
            and _cach_ngay(q, e["so_luc"]) >= NGAY_LAM_MOI
        sua = False
        for c in COT_SO_CHUNG:
            j = o.get(c)
            v = str((e.get("so") or {}).get(c) or "")
            if j is not None and v and d[j] != v and (de or not str(d[j]).strip()):
                d[j] = v
                sua = True
        if sua:
            dem["lam_moi"] += 1
            doi = True
    # (b) gieo link hộp thư chưa có trong sổ riêng
    them: List[Tuple[str, Dict[str, Any], str]] = []
    thay: Set[str] = set(co)
    for link in db.hop_thu(goc, kenh):
        k = khoa_chuan(link, bi)
        if not k or k in thay:
            continue
        e = du["kenh"].get(k)
        g = (e or {}).get("gieo")
        if not e or not g or g.get("lop") not in lop_duoc:
            dem["bo_qua"] += 1
            continue
        thay.add(k)
        them.append((link, e, k))
    luc = time.strftime("%Y-%m-%dT%H:%M:%S")
    so_gieo = du.setdefault("gieo", {}).setdefault(kenh, {}) if ghi else {}
    for link, e, k in them:
        g = e["gieo"]
        d = [""] * len(cot)
        d[o["Link kênh"]] = link
        if "Kênh" in o:
            d[o["Kênh"]] = e.get("ten") or db._ten_tu_link(link)  # noqa: SLF001
        if "Trạng thái" in o:
            d[o["Trạng thái"]] = g["trang_thai"]
        if "Ghi chú" in o:
            d[o["Ghi chú"]] = g.get("ghi_chu") or ""
        if "Lần đầu thấy" in o:
            d[o["Lần đầu thấy"]] = e.get("lan_dau") or luc[:10]
        for c in COT_SO_CHUNG:
            if c in o and (e.get("so") or {}).get(c):
                d[o[c]] = str(e["so"][c])
        hang.append(d)
        dem["gieo"] += 1
        dem["theo_lop"][g["lop"]] = dem["theo_lop"].get(g["lop"], 0) + 1
        dem["links"].append(link)
        so_gieo[k] = {"tu": g.get("tu") or "", "luc": luc, "trang_thai": g["trang_thai"]}
        doi = True
    if doi and ghi:
        db.luu(goc, kenh, cot, hang)
    return dem


#: Dòng "theo dõi" của sổ riêng được đè số đo chung khi sổ chung quét mới hơn ngần này ngày.
NGAY_LAM_MOI = 3.0


def _cach_ngay(cu: str, moi: str) -> float:
    """Số ngày `moi` sau `cu` ("YYYY-MM-DD HH:MM"); `cu` trống → vô cực."""
    def ep(s: str) -> Optional[float]:
        for dang, dai in (("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
            try:
                return time.mktime(_dt.datetime.strptime(str(s or "")[:dai], dang).timetuple())
            except ValueError:
                continue
        return None
    a, b = ep(cu), ep(moi)
    if b is None:
        return 0.0
    if a is None:
        return float("inf")
    return (b - a) / 86400.0


def dong_bo_truoc_chot(goc: str, kenh: str, *, on_log: Optional[Callable[[str], None]] = None,
                       ghi: bool = True) -> Dict[str, Any]:
    """Đầu lượt chấm hộp thư của `kenh`: gộp sổ chung (mọi sổ riêng mới nhất) rồi gieo vào sổ của `kenh`.
    Không nhóm / lỗi → `{}` (lượt chấm đi như cũ). Không bao giờ ném."""
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return {}
        t0 = time.time()
        if not ghi:
            du = gop(goc, nhom, ghi=False)
            return ap_vao_so(goc, kenh, du=du, ghi=False) if du else {}
        with _khoa_ghi(goc, nhom):
            tv = thanh_vien_nhom(goc, nhom)
            du = _dung_lai(goc, nhom, tv, doc(goc, nhom))
            dem = ap_vao_so(goc, kenh, du=du, ghi=True)
            if dem.get("gieo") or dem.get("lam_moi"):
                # sổ riêng vừa đổi → dựng lại để sổ chung ghi ra khớp mọi sổ riêng (`gop_sau` bỏ qua theo giờ sửa)
                du = _dung_lai(goc, nhom, tv, du)
            _ghi(goc, nhom, du)
        if on_log is not None and (dem.get("gieo") or dem.get("lam_moi")):
            on_log("  sổ đối thủ chung ({0} kênh): gieo {1} kênh anh em đã chấm vào sổ {2} ({3}) — không đo lại, "
                   "không hỏi AI lại · làm mới số đo {4} dòng · {5:.1f}s".format(
                       len(du.get("kenh") or {}), dem["gieo"], kenh,
                       ", ".join("{0} {1}".format(a, b) for a, b in sorted(dem["theo_lop"].items())) or "—",
                       dem["lam_moi"], time.time() - t0))
        return dem
    except Exception as loi:  # noqa: BLE001 — sổ chung hỏng không được chặn lượt chấm
        if on_log is not None:
            on_log("  sổ đối thủ chung hỏng, chấm như cũ: {0}: {1}".format(type(loi).__name__, str(loi)[:160]))
        return {}


def gop_sau(goc: str, kenh: str, *, on_log: Optional[Callable[[str], None]] = None) -> None:
    """Sau một bước ghi sổ riêng của `kenh` (chấm hộp thư, quét): gộp lại sổ chung để kênh anh em kế tiếp thấy ngay —
    bỏ qua khi sổ riêng không đổi từ lần gộp trước (giờ sửa tệp). Không bao giờ ném."""
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return
        try:
            if os.path.getmtime(db.duong_so(goc, kenh)) < os.path.getmtime(duong(goc, nhom)):
                return
        except OSError:
            pass
        gop(goc, nhom)
    except Exception as loi:  # noqa: BLE001
        if on_log is not None:
            on_log("  gộp sổ đối thủ chung hỏng (lượt sau gộp lại): {0}".format(str(loi)[:120]))


def bo_bi_danh_da_co(goc: str, kenh: str, links: Sequence[str]) -> Tuple[List[str], int]:
    """Link hộp thư mà sổ riêng của `kenh` ĐÃ CÓ dưới dạng link khác (`@handle` ↔ `/channel/UC…`, theo bí danh của sổ
    chung) → bỏ khỏi lượt chấm (không đo lại cùng một kênh). Trả `(còn lại, số bỏ)`. Không nhóm / lỗi → nguyên."""
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom or not links:
            return list(links), 0
        bi = (doc(goc, nhom).get("bi_danh") or {})
        if not bi:
            return list(links), 0
        cot, hang = db.doc(goc, kenh)
        o = db.chi_so_cot(list(cot))
        co = {khoa_chuan(_o(d, o, "Link kênh"), bi) for d in hang}
        con = [l for l in links if khoa_chuan(l, bi) not in co]
        return con, len(links) - len(con)
    except Exception:  # noqa: BLE001
        return list(links), 0


def tra(goc: str, nhom: str, link: str, *, du: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Dòng sổ chung của một link kênh (mọi dạng link), hoặc None."""
    du = du if du is not None else doc(goc, nhom)
    k = khoa_chuan(link, du.get("bi_danh") or {})
    return (du.get("kenh") or {}).get(k) if k else None


# ── bản đọc CSV ──────────────────────────────────────────────────────────────

COT_CSV = ("Kênh", "Tầng", "Trạng thái chung", "Ngách (AI)", "Ngày phán", "Sức sống", "Bạn đưa", "AI", "Subs",
           "View TV", "Dài TV", "Số video", "View/tháng", "Im lặng", "Đăng gần nhất", "Quét lúc", "Lần đầu thấy",
           "Kênh ta theo dõi", "Kênh ta bỏ/hết", "Tuyến (theo kênh ta)", "Trang chủ/pool kênh ta", "Lý do tầng",
           "Lý do ngách", "Mã kênh", "Link kênh")
#: Thứ tự dòng của bản đọc: tầng 1 → 2 → 3 → ngoài (sổ cũ chưa có tầng: theo dõi trước), điểm tầng giảm dần.
_HANG_CSV = {TANG_1: 0, TANG_2: 1, TANG_3: 2, NGOAI: 3}


def _ghi_csv(p: str, du: Dict[str, Any]) -> None:
    rows = []
    for k, e in sorted((du.get("kenh") or {}).items(), key=lambda kv: (
            _HANG_CSV.get(str(kv[1].get("tang") or ""), 4), kv[1].get("trang_thai") != db.THEO_DOI,
            -float(kv[1].get("tang_diem") or 0.0), str(kv[1].get("ten") or ""))):
        tk = e.get("theo_kenh") or {}
        so = e.get("so") or {}
        lq = e.get("lien_quan") or {}
        rows.append({
            "Kênh": e.get("ten", ""), "Tầng": e.get("tang", ""), "Trạng thái chung": e.get("trang_thai", ""),
            "Ngách (AI)": (e.get("ngach") or {}).get("ket", ""), "Ngày phán": (e.get("ngach") or {}).get("ngay", ""),
            "Sức sống": (e.get("song") or {}).get("ket", ""), "Bạn đưa": "x" if e.get("ban_dua") else "",
            "AI": so.get("AI", ""), "Subs": so.get("Subs", ""), "View TV": so.get("View TV", ""),
            "Dài TV": so.get("Dài TV", ""), "Số video": so.get("Số video", ""), "View/tháng": so.get("View/tháng", ""),
            "Im lặng": so.get("Im lặng", ""), "Đăng gần nhất": e.get("dang_moi") or so.get("Đăng gần nhất", ""),
            "Quét lúc": e.get("quet_luc", ""), "Lần đầu thấy": e.get("lan_dau", ""),
            "Kênh ta theo dõi": " ".join(sorted(m for m, x in tk.items() if (x.get("tt") or db.THEO_DOI) == db.THEO_DOI)),
            "Kênh ta bỏ/hết": " ".join(sorted(m for m, x in tk.items() if x.get("tt") in (db.BO, db.HET))),
            "Tuyến (theo kênh ta)": " · ".join("{0}:{1}".format(m, x["tuyen"]) for m, x in sorted(tk.items())
                                              if x.get("tuyen"))[:200],
            "Trang chủ/pool kênh ta": " · ".join("{0}:{1}/{2}".format(m, int(x.get("tc") or 0), int(x.get("pool") or 0))
                                                for m, x in sorted(lq.items()) if x.get("tc") or x.get("pool"))[:200],
            "Lý do tầng": str(e.get("tang_ly_do") or ""),
            "Lý do ngách": str((e.get("ngach") or {}).get("ly_do") or "")[:160], "Mã kênh": e.get("uc", ""),
            "Link kênh": e.get("link", "")})
    tam = p + ".{0}.tmp".format(os.getpid())
    with io.open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(COT_CSV))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(tam, p)


# ── dòng lệnh ────────────────────────────────────────────────────────────────

def _in_tang(du: Dict[str, Any], n: int) -> None:
    """Số kênh từng tầng + `n` tên đầu mỗi tầng (xếp theo điểm tầng) — chỉ TÊN, không mã kênh."""
    kenh = du.get("kenh") or {}
    tk = (du.get("thong_ke") or {}).get("tang") or {}
    print("nhóm {0} · {1} kênh trong sổ · tầng 1: {2} · tầng 2: {3} · tầng 3: {4} · ngoài: {5}".format(
        du.get("nhom"), len(kenh), tk.get(TANG_1, 0), tk.get(TANG_2, 0), tk.get(TANG_3, 0), tk.get(NGOAI, 0)))
    print("hạn quét (ngày): " + " · ".join("{0} {1:g}".format(t, NGAY_QUET_TANG[t]) for t in TANG))
    for t in TANG:
        ds = sorted((e for e in kenh.values() if e.get("tang") == t),
                    key=lambda e: (-float(e.get("tang_diem") or 0.0), str(e.get("ten") or "")))
        print("── tầng {0} ({1}):".format(t, len(ds)))
        for i, e in enumerate(ds[:n], 1):
            print("  {0:2d}. {1} — {2}".format(i, e.get("ten") or "?", e.get("tang_ly_do") or ""))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.so_doi_thu_chung")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p.add_argument("--nhom", default="")
    p.add_argument("--ghi", action="store_true", help="ghi sổ chung (mặc định chỉ in thống kê)")
    p.add_argument("--gieo", action="store_true", help="gieo vào sổ riêng mọi kênh (cần --ghi)")
    p.add_argument("--tang", nargs="?", type=int, const=10, default=0, metavar="N",
                   help="in số kênh từng tầng + N tên đầu mỗi tầng (mặc định 10), bỏ phần gieo")
    a = p.parse_args(list(argv) if argv is not None else None)
    nhom = a.nhom
    if not nhom:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        nhom = next((nhom_cua(a.goc, k) for k in liet_ke_kenh(a.goc) if nhom_cua(a.goc, k)), "")
    if not nhom:
        print("không có nhóm kênh nào")
        return 1
    tv = thanh_vien_nhom(a.goc, nhom)
    du = gop(a.goc, nhom, thanh_vien=tv, ghi=bool(a.ghi))
    if a.tang:
        _in_tang(du, int(a.tang))
        return 0
    print(json.dumps({"nhom": nhom, "thanh_vien": tv, "thong_ke": du.get("thong_ke")}, ensure_ascii=False, indent=1))
    for k in tv:
        dem = ap_vao_so(a.goc, k, du=du, ghi=bool(a.ghi and a.gieo))
        print("{0}: gieo {1} {2} · làm mới số {3} · hộp thư chưa gieo được {4}".format(
            k, dem.get("gieo"), dem.get("theo_lop"), dem.get("lam_moi"), dem.get("bo_qua")))
    if a.ghi and a.gieo:
        _ghi(a.goc, nhom, du)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
