"""**Kiểm ngách + sức sống của danh bạ đối thủ** — ai được ở trạng thái "theo dõi" (30/09/2026).

═══ VÌ SAO ═══

Chủ dự án (30/09/2026) thấy danh sách đối thủ SAI và nhiều RÁC. Ca thật: "Barry Nobles"
(@barrynobles95, 188k sub, không phải kênh tâm lý) bị TL1-T7 đổi sang "theo dõi" lúc 29/09 18:03
với lý do *"máy chấm: khớp tuyến 12% · già 0%"* — trong khi TL2/TL3/TL4 đều đang "bỏ" nó. Gốc:
`chot_doi_thu.quyet` cho vào "theo dõi" chỉ bằng TỈ LỆ KHỚP TỪ KHOÁ (TL1 đo bằng regex tệp tò
mò — 犬/猫/散歩… chạm cả kênh đời sống), và AI không có ý kiến thì quyết định máy được giữ. Cả
"thị trường (còn nhỏ / khác khổ / tệp 55+ / gần ngách)" cũng vào thẳng "theo dõi" không qua AI:
163/234 kênh theo dõi của TL1 đi đường ấy.

Thêm (chủ dự án): *"kênh quá yếu, hoặc kênh đã rất lâu không đăng video thì đâu phải đối thủ"*.

═══ LUẬT MỚI — ba cửa, đo trên số đã có (content.csv cả nhóm) + một phán quyết LLM ═══

1. **NGỪNG HOẠT ĐỘNG** — video dài (≥ `GIAY_VIDEO_DAI`) mới nhất cách hôm nay ≥ `NGAY_IM` ngày
   → BỎ, TRỪ khi còn video ≤ `NGAY_DOT_BIEN` ngày đang đột biến (≥ `HE_SO_NOI` × trung vị kênh
   và vẫn đang tăng view).
2. **QUÁ YẾU** — trung vị view gần đây VÀ view/tháng đều dưới phân vị `PHAN_VI_YEU` của cả
   nhóm, KHÔNG có video nào nổi (≥ `HE_SO_NOI` × trung vị kênh), và không tăng trưởng nhanh
   (trung vị 10 video mới < `HE_SO_TANG_TRUONG` × trung vị 10–30 video trước) → BỎ.
3. **NGÁCH** — LLM mạnh (`MO_HINH`) đọc tên kênh + ~10 tiêu đề gần nhất + mô tả ngách của nhóm
   (`ngach.yaml`) → GIỮ / BỎ / NGHI. Phán quyết ghi vào kho chung nhóm `kenh-ai.json` (khoá =
   link kênh) — NGUỒN SỰ THẬT về ngách cho cả 4 kênh, để một kênh không tự lật cái kênh anh em
   đã bỏ.

Kênh do NGƯỜI đặt (Ghi chú "bạn đưa — luôn quét", có trong `doi-thu-ban-dua.txt`, hoặc Ghi chú
trống — không phân biệt được) KHÔNG bị tự bỏ: phán BỎ → thành NGHI để chủ kênh xem.

BỎ → trạng thái "bỏ", Ghi chú "AI kiểm ngách 30/09: … ‖ trước: …" (giữ lịch sử, không xoá dòng).
NGHI → giữ "theo dõi", Ghi chú mở đầu "⚠ NGHI". GIỮ → Ghi chú mở đầu "✓ AI kiểm ngách".
V7/VPH/Một nút đều gạt content của kênh "bỏ" (xem `cong_thuc_v7` "kênh nguồn đã bỏ",
`cong_thuc_vph`/`mot_nut` "kênh không theo dõi") — nên đổi trạng thái là đủ để content ra khỏi
kho ứng viên; `lam_sach_danh_sach_chon` gạt nốt bảng `danh-sach-chon.json` đã ghi sẵn.

Không import Qt. Lượt LLM đi qua `goi` (bài kiểm truyền hàm giả).
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import danh_ba_doi_thu as db

__all__ = ["GIU", "BO", "NGHI", "MO_HINH", "NGAY_IM", "PHAN_VI_YEU", "HE_SO_NOI", "SoKenh",
           "do_so_kenh", "so_kenh_tu_channel", "nguong_nhom", "cua_suc_song", "hoi_ngach",
           "phan_quyet_nhom", "ghi_phan_quyet_nhom", "ap_vao_danh_ba", "kiem", "kiem_dinh_ky",
           "lam_sach_danh_sach_chon", "la_nguoi_dat", "DAU_GIU", "DAU_NGHI", "DAU_BO"]

GIU, BO, NGHI = "giu", "bo", "nghi"
MO_HINH = "claude-fable-5"

#: Luật sức sống — ngưỡng ghi lại nguyên văn trong báo cáo.
GIAY_VIDEO_DAI = 240          # ≥ 4 phút mới tính "video dài" (Shorts/clip ngắn không phải khổ remake)
NGAY_IM = 30                  # không đăng video dài ≥ ngần này ngày → ngừng hoạt động
NGAY_DOT_BIEN = 60            # … trừ khi có video ≤ ngần này ngày đang đột biến
HE_SO_NOI = 3.0               # "nổi" = view ≥ 3 × trung vị view của chính kênh
PHAN_VI_YEU = 0.20            # quá yếu = dưới phân vị 20% của cả nhóm (cả trung vị view lẫn view/tháng)
HE_SO_TANG_TRUONG = 2.0       # tăng trưởng nhanh = trung vị 10 video mới ≥ 2 × trung vị video trước đó
SO_VIDEO_TOI_THIEU = 5        # dưới ngần này video dài thì không đo "quá yếu" (thiếu số)
HAN_PHAN_QUYET_NGAY = 30      # phán quyết ngách trong kenh-ai.json còn dùng được ngần này ngày

DAU_GIU = "✓ AI kiểm ngách"
DAU_NGHI = "⚠ NGHI"
DAU_BO = "AI kiểm ngách"
_GHI_CHU_BAN_DUA = "bạn đưa — luôn quét"


def _so(x: Any) -> float:
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _giay(chu: str) -> int:
    phan = [p for p in str(chu or "").strip().split(":") if p.strip().isdigit()]
    if not phan:
        return 0
    s = 0
    for p in phan:
        s = s * 60 + int(p)
    return s


def _ngay(chu: str) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(chu or "").strip()[:10])
    except ValueError:
        return None


# ── số đo sức sống ────────────────────────────────────────────────────────────


@dataclass
class SoKenh:
    """Số đo sức sống một kênh nguồn, tính từ danh sách video (ngày, view, giây, tăng/ngày)."""

    so_video_dai: int = 0
    ngay_moi_nhat: str = ""
    ngay_im: Optional[int] = None
    trung_vi_gan: float = 0.0          # trung vị view 15 video dài mới nhất
    view_thang: float = 0.0            # tổng view video dài đăng ≤ 30 ngày (xấp xỉ view/tháng)
    noi_max: float = 0.0               # view lớn nhất ÷ trung vị (30 video dài mới nhất)
    dot_bien_gan: bool = False         # có video ≤ NGAY_DOT_BIEN ngày ≥ HE_SO_NOI × trung vị, còn tăng
    tang_truong: float = 0.0           # trung vị 10 mới ÷ trung vị 10–30 trước
    tieu_de: List[str] = field(default_factory=list)   # 30 tiêu đề mới nhất (lượt 1 đọc 10, lượt sâu đọc 30)


def do_so_kenh(videos: Iterable[Tuple[str, float, int, float, str]],
               hom_nay: Optional[_dt.date] = None) -> SoKenh:
    """`videos` = `[(ngày đăng, view, giây, tăng/ngày, tiêu đề)]` (thứ tự bất kỳ)."""
    hom_nay = hom_nay or _dt.date.today()
    ds = []
    for ngay, view, giay, tang, td in videos:
        d = _ngay(ngay)
        if d is None:
            continue
        if giay and giay < GIAY_VIDEO_DAI:
            continue
        ds.append((d, float(view or 0), float(tang or 0), str(td or "")))
    ds.sort(key=lambda x: x[0], reverse=True)
    s = SoKenh(so_video_dai=len(ds), tieu_de=[x[3] for x in ds[:30] if x[3]])
    if not ds:
        return s
    s.ngay_moi_nhat = ds[0][0].isoformat()
    s.ngay_im = (hom_nay - ds[0][0]).days
    gan = [x[1] for x in ds[:15] if x[1] > 0]
    s.trung_vi_gan = statistics.median(gan) if gan else 0.0
    s.view_thang = sum(x[1] for x in ds if (hom_nay - x[0]).days <= 30)
    ba_muoi = [x[1] for x in ds[:30] if x[1] > 0]
    tv30 = statistics.median(ba_muoi) if ba_muoi else 0.0
    if tv30 > 0:
        s.noi_max = max(ba_muoi) / tv30
        s.dot_bien_gan = any((hom_nay - d).days <= NGAY_DOT_BIEN and v >= HE_SO_NOI * tv30 and t > 0
                             for d, v, t, _td in ds)
    moi = [x[1] for x in ds[:10] if x[1] > 0]
    cu = [x[1] for x in ds[10:30] if x[1] > 0]
    if len(moi) >= 5 and len(cu) >= 5 and statistics.median(cu) > 0:
        s.tang_truong = statistics.median(moi) / statistics.median(cu)
    return s


def so_kenh_tu_channel(ch: Any, hom_nay: Optional[_dt.date] = None) -> SoKenh:
    """Số đo từ ảnh chụp `youtube.Channel` (lúc chốt hộp thư). Chưa có tăng/ngày → coi mọi video
    'còn tăng' khi xét đột biến (đo một lần, chưa có lượt trước để so)."""
    vids = []
    for v in getattr(ch, "videos", None) or []:
        vids.append((str(getattr(v, "upload_date", "") or ""), float(getattr(v, "views", 0) or 0),
                     int(getattr(v, "duration_s", 0) or 0), 1.0, str(getattr(v, "title", "") or "")))
    return do_so_kenh(vids, hom_nay)


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with io.open(duong, encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _nghien_cuu(goc: str, ma: str) -> str:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    return thu_muc_nghien_cuu(goc, ma)


def _thanh_vien(goc: str, ma_kenh: str) -> List[str]:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        return nhom_kenh.thanh_vien(goc, ma_kenh) or [ma_kenh]
    except Exception:  # noqa: BLE001
        return [ma_kenh]


def so_kenh_ca_nhom(goc: str, cac_kenh: Sequence[str],
                    hom_nay: Optional[_dt.date] = None) -> Dict[str, SoKenh]:
    """`{tên kênh nguồn: SoKenh}` từ `content.csv` của mọi kênh trong `cac_kenh` (khử trùng link)."""
    theo: Dict[str, Dict[str, Tuple[str, float, int, float, str]]] = {}
    for ma in cac_kenh:
        for r in _doc_csv(os.path.join(_nghien_cuu(goc, ma), "content.csv")):
            ten = str(r.get("Kênh") or "").strip()
            link = str(r.get("Link video") or "").strip()
            if not ten or not link:
                continue
            theo.setdefault(ten, {})[link] = (str(r.get("Ngày đăng") or ""), _so(r.get("View")),
                                              _giay(r.get("Thời lượng") or ""), _so(r.get("Tăng/ngày")),
                                              str(r.get("Tiêu đề video") or ""))
    return {ten: do_so_kenh(v.values(), hom_nay) for ten, v in theo.items()}


def _phan_vi(ds: Sequence[float], p: float) -> float:
    ds = sorted(x for x in ds if x > 0)
    if not ds:
        return 0.0
    i = min(len(ds) - 1, max(0, int(round(p * (len(ds) - 1)))))
    return ds[i]


def nguong_nhom(so: Dict[str, SoKenh], ten_dang_theo_doi: Optional[Iterable[str]] = None) -> Dict[str, float]:
    """Ngưỡng "quá yếu" TƯƠNG ĐỐI: phân vị `PHAN_VI_YEU` của trung vị view gần đây và view/tháng,
    đo trên các kênh (đang theo dõi, nếu truyền) đủ `SO_VIDEO_TOI_THIEU` video dài."""
    chon = set(ten_dang_theo_doi) if ten_dang_theo_doi is not None else None
    mau = [s for t, s in so.items() if (chon is None or t in chon) and s.so_video_dai >= SO_VIDEO_TOI_THIEU]
    return {"trung_vi_gan": _phan_vi([s.trung_vi_gan for s in mau], PHAN_VI_YEU),
            "view_thang": _phan_vi([s.view_thang for s in mau], PHAN_VI_YEU), "so_mau": float(len(mau))}


def cua_suc_song(s: Optional[SoKenh], nguong: Dict[str, float]) -> Tuple[str, str]:
    """(`BO` hoặc "", lý do) — hai cửa máy: ngừng hoạt động, quá yếu. Thiếu số → ("", "")."""
    if s is None or not s.so_video_dai:
        return "", ""
    if s.ngay_im is not None and s.ngay_im >= NGAY_IM and not s.dot_bien_gan:
        return BO, "ngừng hoạt động: video dài mới nhất {0} ({1} ngày trước), không video nào còn đột biến".format(
            s.ngay_moi_nhat, s.ngay_im)
    if s.so_video_dai >= SO_VIDEO_TOI_THIEU and nguong.get("trung_vi_gan", 0) > 0 \
            and s.trung_vi_gan < nguong["trung_vi_gan"] and s.view_thang < nguong.get("view_thang", 0) \
            and s.noi_max < HE_SO_NOI and not s.dot_bien_gan and s.tang_truong < HE_SO_TANG_TRUONG:
        return BO, "quá yếu: trung vị view {0:,.0f} < {1:,.0f} và view/tháng {2:,.0f} < {3:,.0f} (phân vị {4:.0%} " \
                   "nhóm), video nổi nhất ×{5:.1f} trung vị".format(
                       s.trung_vi_gan, nguong["trung_vi_gan"], s.view_thang, nguong["view_thang"], PHAN_VI_YEU,
                       s.noi_max).replace(",", ".")
    return "", ""


# ── phán quyết ngách (LLM) ────────────────────────────────────────────────────


DE_BAI = (
    "Bạn kiểm DANH BẠ ĐỐI THỦ của một nhóm kênh YouTube tiếng Nhật làm theo lối REMAKE (xem video đối thủ "
    "đã thắng rồi viết lại kịch bản). Một kênh chỉ được là đối thủ khi ĐỦ cả bốn: (1) kênh TIẾNG NHẬT; "
    "(2) nội dung chính là TÂM LÝ HỌC / NÃO BỘ / HIỂU NGƯỜI – HIỂU MÌNH (chân dung một kiểu người, cảm xúc, "
    "thói quen giải thích bằng tâm lý); (3) cho khán giả Nhật, nhất là 50+; (4) dạng VIDEO DÀI kể chuyện có "
    "lời đọc (không phải Shorts, không phải cắt clip/tổng hợp/tóm tắt sách).\n\n"
    "NGÁCH CỦA NHÓM:\n{ngach}\n\n"
    "Với MỖI kênh, đọc NGHĨA các tiêu đề (không dò từ khoá) và phán:\n"
    "  \"giu\"  = đúng ngách, remake được.\n"
    "  \"bo\"   = sai ngách — nói CỤ THỂ nó là kênh gì (vd: đời sống/nấu ăn, tài chính dạy đầu tư, tin tức, "
    "tâm linh/bói toán, sức khoẻ thể chất, giải trí, tiếng Anh, tóm tắt sách…).\n"
    "  \"nghi\" = lưng chừng — có một phần tâm lý nhưng trọng tâm lệch (vd 雑学 lẫn lộn, self-help chung, "
    "tâm linh pha tâm lý, kênh bác sĩ tâm thần giảng bệnh học).\n"
    "Tỉ lệ khớp từ khoá của máy KHÔNG phải bằng chứng; chỉ nội dung thật mới là bằng chứng.\n\n"
    "Trả về DUY NHẤT một JSON: {{\"1\": {{\"k\": \"giu|bo|nghi\", \"ly_do\": \"một câu tiếng Việt ≤ 20 chữ\"}}, …}} "
    "đủ mọi số."
)


#: Lượt SÂU cho ca NGHI (chủ dự án 30/09: *"không cần xem, chủ động tất cả"*) — không còn "chờ người
#: duyệt": đọc 30 tiêu đề + số hoạt động rồi BẮT BUỘC chọn giu/bo.
DE_BAI_SAU = (
    "Lượt kiểm trước đã xếp các kênh dưới đây vào loại LƯNG CHỪNG. Giờ bạn phải QUYẾT DỨT KHOÁT, không có "
    "lựa chọn thứ ba. Tiêu chí đối thủ (đủ cả bốn): kênh TIẾNG NHẬT · nội dung CHÍNH là tâm lý học / não bộ / "
    "hiểu người – hiểu mình · hợp khán giả Nhật (nhất là 50+) · video DÀI kể chuyện có lời đọc. Kênh 雑学 hay "
    "self-help vẫn là đối thủ NẾU phần lớn video là chân dung tâm lý remake được; kênh chỉ thỉnh thoảng có "
    "một video tâm lý thì KHÔNG.\n\n"
    "NGÁCH CỦA NHÓM:\n{ngach}\n\n"
    "Đọc KỸ ~30 tiêu đề gần nhất và số hoạt động của từng kênh. Trả về DUY NHẤT một JSON: "
    "{{\"1\": {{\"k\": \"giu\" hoặc \"bo\", \"ly_do\": \"một câu tiếng Việt ≤ 25 chữ, nói rõ kênh làm gì\"}}, …}} đủ mọi số."
)


def _mo_ta_ngach(goc: str, ma_kenh: str) -> str:
    try:
        from .trang_chu import mo_ta_ngach_cho_ai  # noqa: PLC0415

        return mo_ta_ngach_cho_ai(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return "Tâm lý học / khoa học não bộ tiếng Nhật, chân dung một kiểu người."


#: 01/10/2026 — đề bài cho NGÁCH KHÁC ngách mặc định. `DE_BAI`/`DE_BAI_SAU` ở trên viết cứng "kênh TIẾNG
#: NHẬT · tâm lý học · khán giả Nhật 50+": một kênh nấu ăn Việt chạy lượt kiểm này là mọi đối thủ đúng
#: ngách bị phán "bo" và danh bạ trống trơn. Ngách khác: bốn tiêu chí lấy từ `ngach.yaml`
#: (`tieu_chi_doi_thu`), thiếu thì dựng từ tiếng + mô tả ngách.
DE_BAI_NGACH = (
    "Bạn kiểm DANH BẠ ĐỐI THỦ của một nhóm kênh YouTube {tieng} làm theo lối REMAKE (xem video đối thủ "
    "đã thắng rồi viết lại kịch bản). Một kênh chỉ được là đối thủ khi ĐỦ mọi tiêu chí:\n{tieu_chi}\n\n"
    "NGÁCH CỦA NHÓM:\n{{ngach}}\n\n"
    "Với MỖI kênh, đọc NGHĨA các tiêu đề (không dò từ khoá) và phán:\n"
    "  \"giu\"  = đúng ngách, remake được.\n"
    "  \"bo\"   = sai ngách — nói CỤ THỂ nó là kênh gì.\n"
    "  \"nghi\" = lưng chừng — có một phần đúng ngách nhưng trọng tâm lệch.\n"
    "Tỉ lệ khớp từ khoá của máy KHÔNG phải bằng chứng; chỉ nội dung thật mới là bằng chứng.\n\n"
    "Trả về DUY NHẤT một JSON: {{{{\"1\": {{{{\"k\": \"giu|bo|nghi\", \"ly_do\": \"một câu tiếng Việt ≤ 20 chữ\"}}}}, …}}}} "
    "đủ mọi số."
)

DE_BAI_SAU_NGACH = (
    "Lượt kiểm trước đã xếp các kênh dưới đây vào loại LƯNG CHỪNG. Giờ bạn phải QUYẾT DỨT KHOÁT, không có "
    "lựa chọn thứ ba. Tiêu chí đối thủ (đủ cả):\n{tieu_chi}\nKênh chỉ thỉnh thoảng có một video đúng ngách "
    "thì KHÔNG.\n\n"
    "NGÁCH CỦA NHÓM:\n{{ngach}}\n\n"
    "Đọc KỸ ~30 tiêu đề gần nhất và số hoạt động của từng kênh. Trả về DUY NHẤT một JSON: "
    "{{{{\"1\": {{{{\"k\": \"giu\" hoặc \"bo\", \"ly_do\": \"một câu tiếng Việt ≤ 25 chữ, nói rõ kênh làm gì\"}}}}, …}}}} đủ mọi số."
)


def de_bai_cho(goc: str, ma_kenh: str) -> Tuple[str, str]:
    """`(đề bài, đề bài lượt sâu)` — còn chỗ `{ngach}`. Ngách mặc định (tâm lý × Nhật) → `DE_BAI`,
    `DE_BAI_SAU` nguyên văn; ngách khác → dựng từ hồ sơ ngách. Hỏng → bản cũ."""
    try:
        from . import ho_so_ngach  # noqa: PLC0415

        hs = ho_so_ngach.doc_ngach(goc, ma_kenh)
        if ho_so_ngach.la_ngach_mac_dinh(hs):
            return DE_BAI, DE_BAI_SAU
        tieng = ho_so_ngach.ten_tieng(hs.ngon_ngu()) or "đúng tiếng của nhóm"
        tieu_chi = [str(x).strip() for x in (hs.tieu_chi_doi_thu or []) if str(x).strip()]
        if not tieu_chi:
            tieu_chi = ["kênh nói/viết {0}".format(tieng),
                        "nội dung CHÍNH đúng ngách: {0}".format(hs.mo_ta_ngach or "(xem mô tả ngách bên dưới)"),
                        "hợp khán giả của nhóm" + (" ({0})".format(
                            (hs.thi_truong or {}).get("quoc_gia")) if (hs.thi_truong or {}).get("quoc_gia") else ""),
                        "dạng VIDEO DÀI có lời đọc (không phải Shorts, không phải cắt clip/tổng hợp/reup)"]
        khoi = "\n".join("({0}) {1}".format(i, x.replace("{", "(").replace("}", ")"))
                         for i, x in enumerate(tieu_chi, 1))
        tieng_an = tieng.replace("{", "(").replace("}", ")")
        return (DE_BAI_NGACH.format(tieng=tieng_an, tieu_chi=khoi),
                DE_BAI_SAU_NGACH.format(tieng=tieng_an, tieu_chi=khoi))
    except Exception:  # noqa: BLE001
        return DE_BAI, DE_BAI_SAU


def hoi_ngach(client: Any, cac_kenh: Sequence[Dict[str, Any]], *, mo_ta_ngach: str,
              goi: Optional[Callable[..., str]] = None, so_moi_lo: int = 10,
              on_log: Optional[Callable[[str], None]] = None, sau: bool = False,
              ghi_moi_lo: Optional[Callable[[Dict[str, Dict[str, str]]], None]] = None,
              de_bai_goc: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """`cac_kenh` = `[{"link", "ten", "subs", "view_tv", "so_video", "dai_tv", "tieu_de": [...], "so"}]` →
    `{link: {"k": giu|bo|nghi, "ly_do"}}`. `sau=True` = lượt sâu (30 tiêu đề + số hoạt động, chỉ giu/bo).
    Lô hỏng thì bỏ lô ấy (không có ý kiến), đi tiếp.

    `de_bai_goc` (01/10/2026) — khuôn đề bài (còn `{ngach}`) theo ngách của nhóm (`de_bai_cho`);
    `None` = đề bài tâm lý Nhật cũ."""
    from .goi_van_ban import goi_van_ban, loc_json  # noqa: PLC0415

    goi = goi or goi_van_ban
    de_bai = (de_bai_goc or (DE_BAI_SAU if sau else DE_BAI)).format(ngach=mo_ta_ngach)
    so_td = 30 if sau else 10
    if sau:
        so_moi_lo = min(so_moi_lo, 5)
    ra: Dict[str, Dict[str, str]] = {}
    for dau in range(0, len(cac_kenh), so_moi_lo):
        lo = list(cac_kenh[dau:dau + so_moi_lo])
        khoi = []
        for i, k in enumerate(lo, 1):
            td = [t for t in (k.get("tieu_de") or []) if t][:so_td]
            s = k.get("so")
            hd = ""
            if sau and isinstance(s, SoKenh) and s.so_video_dai:
                hd = "\n   hoạt động: video dài mới nhất {0} ({1} ngày trước) · trung vị view gần {2:,.0f} · " \
                     "view/tháng ~{3:,.0f} · video nổi nhất ×{4:.1f} trung vị".format(
                         s.ngay_moi_nhat, s.ngay_im, s.trung_vi_gan, s.view_thang, s.noi_max).replace(",", ".")
            if sau and k.get("ghi_chu"):
                hd += "\n   ghi chú sổ (tuyến AI thấy trước đây): " + " ".join(str(k["ghi_chu"]).split())[:160]
            khoi.append("{0}. Kênh: {1} ({2}) · {3} sub · view trung vị {4} · {5} video · dài TV {6}{7}\n   {8}".format(
                i, k.get("ten") or "?", k.get("link") or "", k.get("subs") or "?", k.get("view_tv") or "?",
                k.get("so_video") or "?", k.get("dai_tv") or "?", hd,
                "\n   ".join("- " + t for t in td) if td else "(không có tiêu đề nào trong sổ)"))
        try:
            tho = goi(client, [{"role": "system", "content": de_bai}, {"role": "user", "content": "\n".join(khoi)}],
                      toi_da_token=max(3000, 120 * len(lo) + 600), on_log=on_log, mo_hinh=MO_HINH)
            du = loc_json(tho)
        except Exception as loi:  # noqa: BLE001
            if on_log is not None:
                on_log("  lô kiểm ngách hỏng, bỏ qua lô: {0}".format(str(loi)[:90]))
            continue
        if not isinstance(du, dict):
            continue
        for khoa, v in du.items():
            try:
                i = int(str(khoa).strip()) - 1
            except (TypeError, ValueError):
                continue
            if not 0 <= i < len(lo) or not isinstance(v, dict):
                continue
            kq = str(v.get("k") or "").strip().lower()
            if kq in ((GIU, BO) if sau else (GIU, BO, NGHI)):
                ra[str(lo[i].get("link") or "")] = {"k": kq, "ly_do": " ".join(str(v.get("ly_do") or "").split())[:200]}
        if ghi_moi_lo is not None:
            # ghi NGAY sau mỗi lô — tiến trình bị dừng giữa chừng thì lượt sau dùng lại phần đã hỏi
            try:
                ghi_moi_lo({str(k.get("link") or ""): ra[str(k.get("link") or "")] for k in lo
                            if str(k.get("link") or "") in ra})
            except Exception:  # noqa: BLE001
                pass
    return ra


def _duong_kenh_ai(goc: str, ma_kenh: str) -> str:
    """Kho phán quyết ngách: của nhóm, hoặc RIÊNG kênh bật `cho_phep_tep_gia` (phán quyết theo TỆP —
    xem `nghien_cuu_chung.duong_kenh_ai`)."""
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    try:
        return ncc.duong_kenh_ai(goc, ma_kenh)
    except AttributeError:  # tiến trình đang chạy còn giữ nghien_cuu_chung bản cũ
        return os.path.join(ncc.thu_muc(goc, ma_kenh), ncc.TEP_KENH_AI)


def _khoa_link(link: str) -> str:
    return str(link or "").strip().lower()


def phan_quyet_nhom(goc: str, ma_kenh: str, link: str) -> Optional[Dict[str, Any]]:
    """Phán quyết NGÁCH còn hạn của cả nhóm cho `link` (kho `kenh-ai.json`) — `{"kiem_ngach": giu|bo|nghi,
    "ket": doi_thu|khong|gan, "ly_do", "ngay"}` hoặc None."""
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    du = ncc.doc_json(_duong_kenh_ai(goc, ma_kenh), {})
    m = du.get(_khoa_link(link)) if isinstance(du, dict) else None
    if not isinstance(m, dict) or not ncc._con_han_ngay(m.get("ngay"), HAN_PHAN_QUYET_NGAY):  # noqa: SLF001
        return None
    if not m.get("kiem_ngach"):
        ket = str(m.get("ket") or "")
        m = dict(m, kiem_ngach={"doi_thu": GIU, "khong": BO, "gan": NGHI}.get(ket, ""))
    return m if m.get("kiem_ngach") in (GIU, BO, NGHI) else None


def ghi_phan_quyet_nhom(goc: str, ma_kenh: str, phan: Dict[str, Dict[str, str]], *, nguon: str = "kiem-ngach") -> None:
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    hom = _dt.date.today().isoformat()
    moi = {}
    for link, v in phan.items():
        if not link or v.get("k") not in (GIU, BO, NGHI):
            continue
        moi[_khoa_link(link)] = {"ket": {GIU: "doi_thu", BO: "khong", NGHI: "gan"}[v["k"]],
                                 "diem": {GIU: 80, BO: 0, NGHI: 40}[v["k"]], "ly_do": v.get("ly_do", ""),
                                 "tuyen": [], "khac": "", "ngay": hom, "kenh": nguon, "kiem_ngach": v["k"]}
    if moi:
        ncc.ghi_json_gop(_duong_kenh_ai(goc, ma_kenh), moi)


# ── áp vào danh bạ ────────────────────────────────────────────────────────────


def la_nguoi_dat(ghi_chu: str, link: str, ban_dua: set) -> bool:
    """Dòng do NGƯỜI đặt (hoặc không phân biệt được) — không được tự bỏ."""
    g = str(ghi_chu or "").strip()
    return (not g) or g.startswith(_GHI_CHU_BAN_DUA) or db.khoa(link) in ban_dua


def _goc_ghi_chu(g: str) -> str:
    """Bỏ các dấu kiểm cũ ở đầu Ghi chú để không chồng dấu mỗi lượt."""
    g = str(g or "").strip()
    for dau in (DAU_GIU, DAU_NGHI):
        if g.startswith(dau) and " ‖ " in g:
            g = g.split(" ‖ ", 1)[1]
        elif g.startswith(dau):
            g = ""
    return g


def ap_vao_danh_ba(goc: str, ma_kenh: str, phan: Dict[str, Tuple[str, str]], *, ngay: str,
                   sua: bool = True) -> List[Dict[str, str]]:
    """`phan` = `{khoá link: (giu|bo|nghi, lý do)}` → áp vào các dòng "theo dõi" của danh bạ kênh.
    Trả danh sách dòng báo cáo `{kenh, link, subs, cu, moi, ket, ly_do, nguoi_dat}`. `sua=False` →
    chỉ đề xuất (không ghi)."""
    cot, hang = db.doc(goc, ma_kenh)
    o = db.chi_so_cot(list(cot))
    i_l, i_t, i_g, i_k, i_s = o.get("Link kênh"), o.get("Trạng thái"), o.get("Ghi chú"), o.get("Kênh"), o.get("Subs")
    if i_l is None or i_t is None or i_g is None:
        return []
    try:
        from .chot_doi_thu import kenh_ban_dua  # noqa: PLC0415

        ban_dua = kenh_ban_dua(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        ban_dua = set()
    bao: List[Dict[str, str]] = []
    doi = False
    for d in hang:
        while len(d) < len(cot):
            d.append("")
        if str(d[i_t]).strip() != db.THEO_DOI:
            continue
        link = str(d[i_l]).strip()
        v = phan.get(db.khoa(link))
        if not v:
            continue
        ket, ly = v
        cu = str(d[i_g]).strip()
        nguoi = la_nguoi_dat(cu, link, ban_dua)
        moi_tt = db.THEO_DOI
        # Chủ dự án 30/09: "không cần xem, chủ động tất cả" — kênh người đặt cũng tự quyết theo
        # cùng tiêu chí (cờ `nguoi_dat` chỉ để lưu vết trong báo cáo). NGHI chỉ còn khi LLM hỏng
        # cả hai lượt → KHÔNG đổi gì, lượt sau quyết lại.
        ket_ap = ket
        if ket_ap == NGHI:
            bao.append({"kenh": str(d[i_k]) if i_k is not None else "", "link": link,
                        "subs": str(d[i_s]) if i_s is not None else "", "cu": cu, "ket": NGHI,
                        "ly_do": ly, "nguoi_dat": "x" if nguoi else ""})
            continue
        goc_g = _goc_ghi_chu(cu)
        if ket_ap == BO:
            moi_tt = db.BO
            g_moi = "{0} {1}: {2}{3}".format(DAU_BO, ngay, ly, " ‖ trước: " + goc_g if goc_g else "")
        elif ket_ap == NGHI:
            g_moi = "{0} — {1} {2}: {3}{4}".format(DAU_NGHI, DAU_BO, ngay, ly, " ‖ " + goc_g if goc_g else "")
        else:
            g_moi = "{0} {1}: {2}{3}".format(DAU_GIU, ngay, ly, " ‖ " + goc_g if goc_g else "")
        bao.append({"kenh": str(d[i_k]) if i_k is not None else "", "link": link,
                    "subs": str(d[i_s]) if i_s is not None else "", "cu": cu, "ket": ket_ap, "ly_do": ly,
                    "nguoi_dat": "x" if nguoi else ""})
        if sua:
            d[i_g] = g_moi[:400]
            if moi_tt != db.THEO_DOI:
                d[i_t] = moi_tt
            doi = True
    if sua and doi:
        db.luu(goc, ma_kenh, cot, hang)
    return bao


def lam_sach_danh_sach_chon(goc: str, ma_kenh: str) -> int:
    """Gạt khỏi `danh-sach-chon.json` (bảng Một nút đã ghi sẵn) mọi dòng của kênh nay KHÔNG còn
    "theo dõi" — để vòng chọn nguồn không đọc lại bảng cũ. Trả số dòng đã gạt."""
    duong = os.path.join(_nghien_cuu(goc, ma_kenh), "danh-sach-chon.json")
    try:
        with io.open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return 0
    cot, hang = db.doc(goc, ma_kenh)
    o = db.chi_so_cot(list(cot))
    if "Kênh" not in o or "Trạng thái" not in o:
        return 0
    tt = {str(h[o["Kênh"]]).strip(): str(h[o["Trạng thái"]]).strip() for h in hang}
    gat = 0
    if isinstance(du, dict):
        for k, v in list(du.items()):
            if isinstance(v, list):
                con = [x for x in v if not (isinstance(x, dict) and tt.get(str(x.get("kenh") or "").strip(),
                                                                          db.THEO_DOI) != db.THEO_DOI)]
                gat += len(v) - len(con)
                du[k] = con
    if gat:
        tam = duong + ".{0}.tmp".format(os.getpid())
        with io.open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    return gat


# ── đợt kiểm ──────────────────────────────────────────────────────────────────


def _theo_doi(goc: str, ma: str) -> List[Dict[str, str]]:
    cot, hang = db.doc(goc, ma)
    o = db.chi_so_cot(list(cot))
    ra = []
    for h in hang:
        g = {c: (str(h[i]) if i < len(h) else "") for c, i in o.items()}
        if g.get("Trạng thái", "").strip() == db.THEO_DOI and g.get("Link kênh", "").strip():
            ra.append(g)
    return ra


def kiem(goc: str, cac_kenh: Sequence[str], client: Any, *, sua: Sequence[str] = (),
         goi: Optional[Callable[..., str]] = None, dung_lai_phan_quyet: bool = True,
         toi_da_ai: Optional[int] = None, hom_nay: Optional[_dt.date] = None,
         on_log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Đợt kiểm TOÀN BỘ "theo dõi" của `cac_kenh` (cùng nhóm). Kênh trong `sua` được ghi danh bạ;
    kênh còn lại chỉ ra đề xuất. Trả `{"nguong", "theo_kenh": {mã: [dòng báo cáo]}, "phan": {...}}`."""
    def log(m: str) -> None:
        if on_log is not None:
            on_log(m)

    hom_nay = hom_nay or _dt.date.today()
    ngay = hom_nay.strftime("%d/%m")
    nhom_tv = list(dict.fromkeys(list(cac_kenh) + [m for k in cac_kenh for m in _thanh_vien(goc, k)]))
    so = so_kenh_ca_nhom(goc, nhom_tv, hom_nay)
    dong_td = {ma: _theo_doi(goc, ma) for ma in cac_kenh}
    ten_td = {g.get("Kênh", "").strip() for ds in dong_td.values() for g in ds}
    nguong = nguong_nhom(so, ten_td)
    log("  ngưỡng quá yếu (phân vị {0:.0%} của {1:.0f} kênh theo dõi): trung vị view < {2:,.0f} · view/tháng < {3:,.0f}"
        .format(PHAN_VI_YEU, nguong["so_mau"], nguong["trung_vi_gan"], nguong["view_thang"]))
    # Hợp mọi kênh "theo dõi" ở bất kỳ thành viên nào — phán MỘT lần cho cả nhóm.
    hop: Dict[str, Dict[str, Any]] = {}
    for ma, ds in dong_td.items():
        for g in ds:
            k = db.khoa(g["Link kênh"])
            if k not in hop:
                ten = g.get("Kênh", "").strip()
                s = so.get(ten)
                hop[k] = {"link": g["Link kênh"].strip(), "ten": ten, "subs": g.get("Subs", ""),
                          "view_tv": g.get("View TV", ""), "so_video": g.get("Số video", ""),
                          "dai_tv": g.get("Dài TV", ""), "tieu_de": list(s.tieu_de) if s else [], "so": s,
                          "ghi_chu": (g.get("Tuyến", "") + " " + g.get("Ghi chú", "")).strip()}
    # 1) phán quyết ngách: dùng lại kho nhóm nếu còn hạn, còn lại hỏi LLM theo lô
    ai: Dict[str, Dict[str, str]] = {}
    can = []
    for k, h in hop.items():
        m = phan_quyet_nhom(goc, cac_kenh[0], h["link"]) if dung_lai_phan_quyet else None
        if m is not None and m.get("kenh") == "kiem-ngach":
            ai[h["link"]] = {"k": m["kiem_ngach"], "ly_do": str(m.get("ly_do") or "")}
        else:
            can.append(h)
    if toi_da_ai is not None:
        can = can[:max(0, int(toi_da_ai))]
    co_goi = goi is not None or hasattr(client, "request")   # object() giả trong bài kiểm không phải client
    if can and client is not None and co_goi:
        log("  hỏi LLM ngách {0} kênh (dùng lại {1} phán quyết của nhóm)…".format(len(can), len(ai)))
        moi = hoi_ngach(client, can, mo_ta_ngach=_mo_ta_ngach(goc, cac_kenh[0]), goi=goi, on_log=on_log,
                        ghi_moi_lo=lambda p: ghi_phan_quyet_nhom(goc, cac_kenh[0], p),
                        de_bai_goc=de_bai_cho(goc, cac_kenh[0])[0])
        ghi_phan_quyet_nhom(goc, cac_kenh[0], moi)
        ai.update(moi)
    # 2) lượt SÂU cho mọi ca lưng chừng (NGHI, hoặc GIỮ mà sổ không có video dài nào để đo) —
    #    chủ dự án 30/09: "không cần xem, chủ động tất cả": LLM quyết dứt khoát giu/bo.
    sau = [h for h in hop.values()
           if cua_suc_song(h["so"], nguong)[0] != BO and (ai.get(h["link"]) or {}).get("k") in (NGHI,)
           or (cua_suc_song(h["so"], nguong)[0] != BO and (ai.get(h["link"]) or {}).get("k") == GIU
               and (h["so"] is None or not h["so"].so_video_dai))]
    if sau and client is not None and co_goi:
        log("  lượt SÂU (30 tiêu đề + số hoạt động) cho {0} kênh lưng chừng…".format(len(sau)))
        moi2 = hoi_ngach(client, sau, mo_ta_ngach=_mo_ta_ngach(goc, cac_kenh[0]), goi=goi, on_log=on_log, sau=True,
                         de_bai_goc=de_bai_cho(goc, cac_kenh[0])[1])
        moi2 = {l: dict(v, ly_do="(lượt sâu) " + v.get("ly_do", "")) for l, v in moi2.items()}
        ghi_phan_quyet_nhom(goc, cac_kenh[0], moi2)
        ai.update(moi2)
    # 3) quyết cuối: cửa sức sống (máy) thắng GIỮ; LLM hỏng → NGHI = không đổi gì, lượt sau quyết
    phan: Dict[str, Tuple[str, str]] = {}
    for k, h in hop.items():
        bo_may, ly_may = cua_suc_song(h["so"], nguong)
        v = ai.get(h["link"])
        if bo_may == BO:
            phan[k] = (BO, ly_may + (" · ngách: " + v["ly_do"] if v else ""))
        elif v is None or v["k"] == NGHI:
            phan[k] = (NGHI, "LLM chưa quyết được (lỗi lượt gọi) — giữ nguyên, lượt sau quyết lại")
        else:
            phan[k] = (v["k"], v["ly_do"] or "")
    theo_kenh: Dict[str, List[Dict[str, str]]] = {}
    for ma in cac_kenh:
        theo_kenh[ma] = ap_vao_danh_ba(goc, ma, phan, ngay=ngay, sua=ma in set(sua))
        if ma in set(sua):
            n = lam_sach_danh_sach_chon(goc, ma)
            if n:
                log("  {0}: gạt {1} dòng khỏi danh-sach-chon.json (kênh nguồn không còn theo dõi)".format(ma, n))
    for ma, ds in theo_kenh.items():
        so_ket = {x: sum(1 for d in ds if d["ket"] == x) for x in (GIU, BO, NGHI)}
        log("  {0}{1}: GIỮ {2} · BỎ {3} · NGHI {4}".format(ma, "" if ma in set(sua) else " (chỉ đề xuất)",
                                                           so_ket[GIU], so_ket[BO], so_ket[NGHI]))
    return {"nguong": nguong, "theo_kenh": theo_kenh, "phan": phan, "so": {h["link"]: h["so"] for h in hop.values()}}


def kiem_dinh_ky(goc: str, ma_kenh: str, client: Any, *, goi: Optional[Callable[..., str]] = None,
                 toi_da_ai: int = 30, on_log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Đợt kiểm định kỳ cho MỘT kênh (gọi cuối `chot_doi_thu.chot` mỗi lượt nghiên cứu có ví): cửa sức
    sống cho mọi "theo dõi" (miễn phí) + LLM ngách tối đa `toi_da_ai` kênh chưa có phán quyết nhóm.
    `kenh.yaml: kiem_ngach_tu_sua: false` → chỉ tính đề xuất, không ghi danh bạ."""
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        cai = {}
    tu_sua = str(cai.get("kiem_ngach_tu_sua", True)).strip().lower() not in ("false", "0", "no", "off")
    return kiem(goc, [ma_kenh], client, sua=[ma_kenh] if tu_sua else [], goi=goi, toi_da_ai=toi_da_ai,
                on_log=on_log)
