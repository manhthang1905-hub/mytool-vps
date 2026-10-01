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

═══ CHUẨN 01/10/2026 — BA ĐƯỜNG VÀO, MỘT CỬA DUYỆT, ĐỐI THỦ CHẾT ═══

Chủ dự án: *"Trang chủ là để ra đối thủ. Đối thủ là danh sách nguồn. Theo dõi đối thủ là hiểu
được thị trường. Đối thủ lấy từ tao cung cấp, từ Studio các kênh, từ trang chủ các kênh. Đối thủ
cũng có die (kênh bé và không phát triển tiếp). Đối thủ là những kênh còn làm, còn phát triển,
đúng chủ đề, cũng làm bằng AI."*

ĐƯỜNG VÀO — mọi ứng viên đổ về hộp thư `doi-thu.txt`, rồi qua cùng một cửa (`chot_doi_thu.chot`
→ cuối lượt `kiem_dinh_ky`):
  (a) chủ dự án: `CHANNEL/_NHOM/<nhóm>/doi-thu-them.txt`, mỗi dòng một link (`nap_duong_vao`);
  (b) Studio: khán giả cùng xem (`khan-gia-cung-xem.json`, `nap_duong_vao`) + kênh có video hàng
      xóm trong pool `traffic-related` (`cong_thuc_v7.kenh_con_thieu`, gọi trong `mot_nut`);
  (c) trang chủ các kênh (máy ảo → `tram.nhan_trang_chu`, `trang_chu.hoan_thien`).

CỬA DUYỆT — bốn điều kiện, chung cả nhóm:
  ĐÚNG CHỦ ĐỀ   LLM đọc nghĩa (trên)                        trượt → "bỏ"
  CÒN LÀM       video dài trong `NGAY_IM` ngày (luật 1)     trượt → "hết"
  CÒN PHÁT TRIỂN kênh bé (dưới phân vị nhóm) phải có: trung vị 10 video mới ≥ trung vị video
                trước (view đang tăng) HOẶC video ≤ `NGAY_IM` ngày ≥ `HE_SO_VUOT` × trung vị
                của chính kênh HOẶC video đột biến          trượt → "hết"
  LÀM BẰNG AI   LLM thị giác đọc 4 bìa thật + tiêu đề + mô tả kênh (`hoi_lam_ai`, đệm
                `kenh-lam-ai.json`) → cột "AI" = có/không. KHÔNG loại: kênh người thật quay vẫn
                là dữ liệu thị trường; V7 ưu tiên nguồn từ kênh "có".
"hết" không còn là nguồn; mỗi lượt kiểm đo lại (ảnh chụp mới, có đệm) và tự đưa về "theo dõi"
khi lại đạt (Ghi chú "hồi sinh").
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
           "lam_sach_danh_sach_chon", "la_nguoi_dat", "DAU_GIU", "DAU_NGHI", "DAU_BO",
           "HET", "DAU_HET", "hoi_lam_ai", "nap_duong_vao", "TEP_THEM", "TEP_LAM_AI"]

GIU, BO, NGHI = "giu", "bo", "nghi"
#: Đối thủ chết (01/10/2026): đúng chủ đề nhưng không còn làm / không còn phát triển.
HET = "het"
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
HE_SO_VUOT = 1.5              # "còn phát triển": video ≤ NGAY_IM ngày ≥ ngần này × trung vị kênh
HE_SO_DANG_TANG = 1.0         # "view đang tăng": trung vị 10 mới ≥ ngần này × trung vị 10–30 trước
HAN_LAM_AI_NGAY = 90          # phán quyết "làm bằng AI" còn dùng được ngần này ngày
SO_ANH_LAM_AI = 4             # số bìa thật LLM thị giác xem mỗi kênh
TEP_LAM_AI = "kenh-lam-ai.json"
TEP_THEM = "doi-thu-them.txt"  # đường vào (a): chủ dự án đưa, mỗi dòng một link kênh

DAU_GIU = "✓ AI kiểm ngách"
DAU_NGHI = "⚠ NGHI"
DAU_BO = "AI kiểm ngách"
DAU_HET = "Hết"
#: Chữ trong Ghi chú của một "bỏ" vì SỨC SỐNG (bản 30/09) — nay là "hết", lượt kiểm xét lại.
_DAU_BO_SUC_SONG = ("ngừng hoạt động", "quá yếu")
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
    vuot_gan: bool = False             # có video ≤ NGAY_IM ngày ≥ HE_SO_VUOT × trung vị kênh
    ma_video: List[str] = field(default_factory=list)  # mã video dài mới nhất (bìa cho `hoi_lam_ai`)


def do_so_kenh(videos: Iterable[Sequence[Any]],
               hom_nay: Optional[_dt.date] = None) -> SoKenh:
    """`videos` = `[(ngày đăng, view, giây, tăng/ngày, tiêu đề[, mã video])]` (thứ tự bất kỳ)."""
    hom_nay = hom_nay or _dt.date.today()
    ds = []
    for x in videos:
        ngay, view, giay, tang, td = x[:5]
        ma = str(x[5]) if len(x) > 5 and x[5] else ""
        d = _ngay(ngay)
        if d is None:
            continue
        if giay and giay < GIAY_VIDEO_DAI:
            continue
        ds.append((d, float(view or 0), float(tang or 0), str(td or ""), ma))
    ds.sort(key=lambda x: x[0], reverse=True)
    s = SoKenh(so_video_dai=len(ds), tieu_de=[x[3] for x in ds[:30] if x[3]],
               ma_video=[x[4] for x in ds if x[4]][:12])
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
                             for d, v, t, _td, _m in ds)
        s.vuot_gan = any((hom_nay - d).days <= NGAY_IM and v >= HE_SO_VUOT * tv30 for d, v, _t, _td, _m in ds)
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
                     int(getattr(v, "duration_s", 0) or 0), 1.0, str(getattr(v, "title", "") or ""),
                     str(getattr(v, "video_id", "") or "")))
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
    from .doi_thu_kenh import ma_video  # noqa: PLC0415

    theo: Dict[str, Dict[str, Tuple[str, float, int, float, str, str]]] = {}
    for ma in cac_kenh:
        for r in _doc_csv(os.path.join(_nghien_cuu(goc, ma), "content.csv")):
            ten = str(r.get("Kênh") or "").strip()
            link = str(r.get("Link video") or "").strip()
            if not ten or not link:
                continue
            theo.setdefault(ten, {})[link] = (str(r.get("Ngày đăng") or ""), _so(r.get("View")),
                                              _giay(r.get("Thời lượng") or ""), _so(r.get("Tăng/ngày")),
                                              str(r.get("Tiêu đề video") or ""), ma_video(link))
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
    """(`HET` hoặc "", lý do) — hai điều kiện máy của cửa duyệt: CÒN LÀM, CÒN PHÁT TRIỂN (xem đầu
    tệp). Trượt = đối thủ chết ("hết"), không phải sai chủ đề. Thiếu số → ("", "")."""
    if s is None or not s.so_video_dai:
        return "", ""
    if s.ngay_im is not None and s.ngay_im >= NGAY_IM and not s.dot_bien_gan:
        return HET, "không còn làm: video dài mới nhất {0} ({1} ngày trước), không video nào còn đột biến".format(
            s.ngay_moi_nhat, s.ngay_im)
    be = s.so_video_dai >= SO_VIDEO_TOI_THIEU and nguong.get("trung_vi_gan", 0) > 0 \
        and s.trung_vi_gan < nguong["trung_vi_gan"] and s.view_thang < nguong.get("view_thang", 0)
    phat_trien = s.tang_truong >= HE_SO_DANG_TANG or s.vuot_gan or s.dot_bien_gan
    if be and not phat_trien:
        return HET, "không còn phát triển: kênh bé (trung vị view {0} < {1}; view/tháng {2} < {3} — phân vị " \
                    "{4:.0%} nhóm), view không tăng (×{5:.2f}), không video {6} ngày nào ≥{7:g}× trung vị " \
                    "kênh".format(_n(s.trung_vi_gan), _n(nguong["trung_vi_gan"]), _n(s.view_thang),
                                  _n(nguong["view_thang"]), PHAN_VI_YEU, s.tang_truong, NGAY_IM, HE_SO_VUOT)
    return "", ""


def _n(x: float) -> str:
    return "{0:,.0f}".format(float(x or 0)).replace(",", ".")


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


# ── làm bằng AI? (LLM thị giác, 01/10/2026) ──────────────────────────────────


DE_BAI_AI = (
    "Bạn xem các kênh YouTube dưới đây. Mỗi kênh có: tên, mô tả kênh, ~10 tiêu đề gần nhất, rồi vài ẢNH BÌA "
    "THẬT của kênh ấy (ảnh đi ngay sau phần chữ của đúng kênh đó). Phán kênh có LÀM BẰNG AI không.\n"
    "  \"ai\": true  = video dựng bằng máy, không người thật quay: giọng đọc AI/TTS, ảnh minh hoạ hoặc hoạt "
    "hình do AI tạo, ảnh tĩnh + chữ, nhân vật vẽ/AI lặp lại.\n"
    "  \"ai\": false = có NGƯỜI THẬT quay/xuất hiện: mặt thật trên bìa, vlog, người giảng trước máy quay, "
    "bác sĩ/chuyên gia thật, phỏng vấn, cắt từ TV/podcast có người.\n"
    "Trả về DUY NHẤT một JSON: {\"1\": {\"ai\": true, \"ly_do\": \"một câu tiếng Việt ≤ 20 chữ\"}, …} đủ mọi số."
)


def _duong_lam_ai(goc: str, ma_kenh: str) -> str:
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    return os.path.join(ncc.thu_muc(goc, ma_kenh), TEP_LAM_AI)


def lam_ai_kho(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{khoá link: {"ai": bool, "ly_do", "ngay"}}` còn hạn `HAN_LAM_AI_NGAY` (kho chung nhóm)."""
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    du = ncc.doc_json(_duong_lam_ai(goc, ma_kenh), {})
    if not isinstance(du, dict):
        return {}
    return {k: v for k, v in du.items() if isinstance(v, dict) and isinstance(v.get("ai"), bool)
            and ncc._con_han_ngay(v.get("ngay"), HAN_LAM_AI_NGAY)}  # noqa: SLF001


def _ghi_lam_ai(goc: str, ma_kenh: str, phan: Dict[str, Dict[str, Any]]) -> None:
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    hom = _dt.date.today().isoformat()
    moi = {_khoa_link(l): {"ai": bool(v["ai"]), "ly_do": str(v.get("ly_do") or ""), "ngay": hom}
           for l, v in phan.items() if l and isinstance(v.get("ai"), bool)}
    if moi:
        ncc.ghi_json_gop(_duong_lam_ai(goc, ma_kenh), moi)


def _tai_url(url: str) -> Optional[bytes]:
    import urllib.request  # noqa: PLC0415

    try:
        rq = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ja,en;q=0.8"})
        with urllib.request.urlopen(rq, timeout=20) as ph:  # noqa: S310 — chỉ youtube.com / i.ytimg.com
            return ph.read() or None
    except Exception:  # noqa: BLE001 — mạng hỏng / ảnh gỡ là chuyện thường
        return None


def mo_ta_kenh(link: str, tai: Optional[Callable[[str], Optional[bytes]]] = None) -> str:
    """Mô tả kênh (thẻ `og:description` của trang kênh). Hỏng → ""."""
    import html  # noqa: PLC0415
    import re  # noqa: PLC0415

    du = (tai or _tai_url)(str(link or "").strip())
    if not du:
        return ""
    m = re.search(r'<meta property="og:description" content="([^"]*)"', du.decode("utf-8", "replace"))
    return " ".join(html.unescape(m.group(1)).split())[:400] if m else ""


def hoi_lam_ai(client: Any, cac_kenh: Sequence[Dict[str, Any]], *, goi: Optional[Callable[..., str]] = None,
               tai: Optional[Callable[[str], Optional[bytes]]] = None, so_moi_lo: int = 4,
               on_log: Optional[Callable[[str], None]] = None,
               ghi_moi_lo: Optional[Callable[[Dict[str, Dict[str, Any]]], None]] = None) -> Dict[str, Dict[str, Any]]:
    """Điều kiện thứ tư của cửa duyệt — LLM thị giác đọc `SO_ANH_LAM_AI` bìa thật + tiêu đề + mô tả.
    `cac_kenh` = `[{"link", "ten", "tieu_de": [...], "ma_video": [...], "mo_ta"?}]` → `{link: {"ai", "ly_do"}}`.
    Kênh không tải được bìa nào thì không hỏi. Lô hỏng → bỏ lô, đi tiếp."""
    import base64  # noqa: PLC0415

    from .goi_van_ban import goi_van_ban, khoi_anh, loc_json  # noqa: PLC0415

    goi = goi or goi_van_ban
    tai = tai or _tai_url
    chuan_bi = []
    for k in cac_kenh:
        anh = []
        for ma in list(k.get("ma_video") or [])[:SO_ANH_LAM_AI * 2]:
            du = tai("https://i.ytimg.com/vi/{0}/mqdefault.jpg".format(ma))
            if du:
                anh.append(khoi_anh("data:image/jpeg;base64," + base64.b64encode(du).decode("ascii")))
            if len(anh) >= SO_ANH_LAM_AI:
                break
        if anh:
            mo_ta = k.get("mo_ta")
            if mo_ta is None:
                mo_ta = mo_ta_kenh(str(k.get("link") or ""), tai)
            chuan_bi.append((k, mo_ta, anh))
    ra: Dict[str, Dict[str, Any]] = {}
    for dau in range(0, len(chuan_bi), so_moi_lo):
        lo = chuan_bi[dau:dau + so_moi_lo]
        noi: List[Dict[str, Any]] = []
        for i, (k, mo_ta, anh) in enumerate(lo, 1):
            td = [t for t in (k.get("tieu_de") or []) if t][:10]
            noi.append({"type": "text", "text": "{0}. Kênh: {1} ({2})\n   mô tả: {3}\n   {4}\n   ẢNH BÌA của kênh {0}:".format(
                i, k.get("ten") or "?", k.get("link") or "", mo_ta or "(không có)",
                "\n   ".join("- " + t for t in td) or "(không có tiêu đề)")})
            noi.extend(anh)
        try:
            tho = goi(client, [{"role": "system", "content": DE_BAI_AI}, {"role": "user", "content": noi}],
                      toi_da_token=max(2000, 100 * len(lo) + 600), on_log=on_log, mo_hinh=MO_HINH)
            du = loc_json(tho)
        except Exception as loi:  # noqa: BLE001
            if on_log is not None:
                on_log("  lô kiểm 'làm bằng AI' hỏng, bỏ qua lô: {0}".format(str(loi)[:90]))
            continue
        if not isinstance(du, dict):
            continue
        moi: Dict[str, Dict[str, Any]] = {}
        for khoa, v in du.items():
            try:
                i = int(str(khoa).strip()) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(lo) and isinstance(v, dict) and isinstance(v.get("ai"), bool):
                moi[str(lo[i][0].get("link") or "")] = {"ai": v["ai"],
                                                         "ly_do": " ".join(str(v.get("ly_do") or "").split())[:160]}
        ra.update(moi)
        if ghi_moi_lo is not None and moi:
            try:
                ghi_moi_lo(moi)
            except Exception:  # noqa: BLE001
                pass
    return ra


# ── ba đường vào (01/10/2026) ─────────────────────────────────────────────────


def _thu_muc_them(goc: str, ma_kenh: str) -> str:
    """Chỗ để `doi-thu-them.txt`: `CHANNEL/_NHOM/<nhóm>/` (kênh có nhóm), không thì `nghien-cuu/` của kênh."""
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    if ncc.nhom_cua(goc, ma_kenh):
        return os.path.dirname(ncc.thu_muc(goc, ma_kenh))
    return _nghien_cuu(goc, ma_kenh)


def nap_duong_vao(goc: str, ma_kenh: str) -> Dict[str, int]:
    """Đổ hai đường vào chưa nối vào HỘP THƯ của `ma_kenh` (rồi cửa `chot` duyệt như mọi ứng viên):
    (a) `doi-thu-them.txt` của chủ dự án; (b) khán giả cùng xem của Studio (`ung_vien_doi_thu_uu_tien`).
    Bỏ link đã có ở hộp thư/danh bạ (kể cả mã kênh UC… đã biết qua ảnh chụp `kenh-do.json`)."""
    from . import doi_thu_kenh as so  # noqa: PLC0415
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    a: List[str] = []
    try:
        with io.open(os.path.join(_thu_muc_them(goc, ma_kenh), TEP_THEM), encoding="utf-8-sig") as tep:
            a = [d.strip() for d in tep if d.strip() and not d.strip().startswith("#") and db.khoa(d.strip())]
    except OSError:
        pass
    b: List[str] = []
    try:
        for ban in (ncc.khan_gia_cung_xem_doc(goc, ma_kenh) or {}).values():
            for u in (ban or {}).get("ung_vien_doi_thu_uu_tien") or []:
                if isinstance(u, dict) and db.khoa(str(u.get("link") or "")):
                    b.append(str(u["link"]).strip())
    except Exception:  # noqa: BLE001
        b = []
    if not a and not b:
        return {"chu_du_an": 0, "studio": 0}
    hop = so.doc_doi_thu(goc, ma_kenh).strip()
    cot, hang = db.doc(goc, ma_kenh)
    da = set(db.theo_khoa(cot, hang)) | {db.khoa(d) for d in hop.splitlines() if db.khoa(d)}
    try:   # mã kênh UC… của kênh đã biết dưới dạng @handle
        for m in (ncc.doc_json(os.path.join(ncc.thu_muc(goc, ma_kenh), ncc.TEP_KENH_DO), {}) or {}).values():
            ch = (m or {}).get("ch") or {}
            if db.khoa(str(ch.get("input_url") or "")) in da and ch.get("channel_id"):
                da.add(db.khoa("https://www.youtube.com/channel/" + str(ch["channel_id"])))
    except Exception:  # noqa: BLE001
        pass
    dem = {"chu_du_an": 0, "studio": 0}
    moi: List[str] = []
    for nhan, ds in (("chu_du_an", a), ("studio", b)):
        for l in ds:
            k = db.khoa(l)
            if k and k not in da:
                da.add(k)
                moi.append(l)
                dem[nhan] += 1
    if moi:
        so.luu_doi_thu(goc, ma_kenh, (hop + "\n" if hop else "") + "\n".join(moi))
    return dem


# ── áp vào danh bạ ────────────────────────────────────────────────────────────


def la_nguoi_dat(ghi_chu: str, link: str, ban_dua: set) -> bool:
    """Dòng do NGƯỜI đặt (hoặc không phân biệt được) — không được tự bỏ."""
    g = str(ghi_chu or "").strip()
    return (not g) or g.startswith(_GHI_CHU_BAN_DUA) or db.khoa(link) in ban_dua


def _goc_ghi_chu(g: str) -> str:
    """Bỏ các dấu kiểm cũ ở đầu Ghi chú để không chồng dấu mỗi lượt (giữ phần lịch sử sau ‖)."""
    g = str(g or "").strip()
    for dau in (DAU_GIU, DAU_NGHI, DAU_HET):
        if g.startswith(dau) and " ‖ " in g:
            g = g.split(" ‖ ", 1)[1]
        elif g.startswith(dau):
            g = ""
    if la_bo_suc_song(g):
        g = g.split(" ‖ ", 1)[1] if " ‖ " in g else ""
    if g.startswith("trước: "):
        g = g[len("trước: "):]
    return g


def la_bo_suc_song(ghi_chu: str) -> bool:
    """Dòng "bỏ" vì SỨC SỐNG (bản 30/09: ngừng hoạt động / quá yếu) — không phải vì sai chủ đề."""
    g = str(ghi_chu or "").strip()
    dau = g.split(" · ngách:", 1)[0].split(" ‖ ", 1)[0]
    return (g.startswith(DAU_BO) or g.startswith("không phải đối thủ")) and any(t in dau for t in _DAU_BO_SUC_SONG)


def _can_xet(tt: str, ghi_chu: str) -> bool:
    """Dòng thuộc đợt kiểm: "theo dõi", "hết", và "bỏ" vì sức sống (bản cũ — nay là "hết")."""
    tt = str(tt or "").strip()
    return tt in (db.THEO_DOI, db.HET) or (tt == db.BO and la_bo_suc_song(ghi_chu))


def ap_vao_danh_ba(goc: str, ma_kenh: str, phan: Dict[str, Tuple[str, str]], *, ngay: str,
                   sua: bool = True, ai_co: Optional[Dict[str, bool]] = None) -> List[Dict[str, str]]:
    """`phan` = `{khoá link: (giu|bo|het|nghi, lý do)}` → áp vào các dòng đợt kiểm (`_can_xet`) của danh bạ.
    giu → "theo dõi" (hồi sinh nếu đang hết/bỏ-sức-sống) · bo → "bỏ" · het → "hết" · nghi → không đổi.
    `ai_co` = `{khoá link: True/False}` → cột "AI" (có/không) cho mọi dòng có phán quyết.
    Trả dòng báo cáo `{kenh, link, subs, cu, cu_tt, moi_tt, ket, ly_do, nguoi_dat, ai}`. `sua=False` → chỉ đề xuất."""
    cot, hang = db.doc(goc, ma_kenh)
    o = db.chi_so_cot(list(cot))
    i_l, i_t, i_g, i_k, i_s = o.get("Link kênh"), o.get("Trạng thái"), o.get("Ghi chú"), o.get("Kênh"), o.get("Subs")
    i_ai = o.get(db.COT_AI)
    if i_l is None or i_t is None or i_g is None:
        return []
    ai_co = ai_co or {}
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
        link = str(d[i_l]).strip()
        k = db.khoa(link)
        if sua and i_ai is not None and k in ai_co:
            chu_ai = "có" if ai_co[k] else "không"
            if d[i_ai] != chu_ai:
                d[i_ai] = chu_ai
                doi = True
        cu_tt, cu = str(d[i_t]).strip(), str(d[i_g]).strip()
        if not _can_xet(cu_tt, cu):
            continue
        v = phan.get(k)
        if not v:
            continue
        ket, ly = v
        nguoi = la_nguoi_dat(cu, link, ban_dua)
        # Chủ dự án 30/09: "không cần xem, chủ động tất cả" — kênh người đặt cũng tự quyết theo
        # cùng tiêu chí (cờ `nguoi_dat` chỉ để lưu vết). NGHI chỉ còn khi LLM hỏng → KHÔNG đổi gì.
        moi_tt = {GIU: db.THEO_DOI, BO: db.BO, HET: db.HET}.get(ket, cu_tt)
        dong_bao = {"kenh": str(d[i_k]) if i_k is not None else "", "link": link,
                    "subs": str(d[i_s]) if i_s is not None else "", "cu": cu, "cu_tt": cu_tt, "moi_tt": moi_tt,
                    "ket": ket, "ly_do": ly, "nguoi_dat": "x" if nguoi else "",
                    "ai": ("có" if ai_co[k] else "không") if k in ai_co else ""}
        bao.append(dong_bao)
        if ket == NGHI:
            continue
        goc_g = _goc_ghi_chu(cu)
        if ket == BO:
            g_moi = "{0} {1}: {2}{3}".format(DAU_BO, ngay, ly, " ‖ trước: " + goc_g if goc_g else "")
        elif ket == HET:
            g_moi = "{0} {1}: {2}{3}".format(DAU_HET, ngay, ly, " ‖ " + goc_g if goc_g else "")
        else:
            g_moi = "{0} {1}{2}: {3}{4}".format(DAU_GIU, ngay, " (hồi sinh)" if cu_tt != db.THEO_DOI else "",
                                               ly, " ‖ " + goc_g if goc_g else "")
        if sua and (g_moi[:400] != cu or moi_tt != cu_tt):
            d[i_g] = g_moi[:400]
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
    """Dòng thuộc đợt kiểm (`_can_xet`): "theo dõi", "hết", "bỏ" vì sức sống."""
    cot, hang = db.doc(goc, ma)
    o = db.chi_so_cot(list(cot))
    ra = []
    for h in hang:
        g = {c: (str(h[i]) if i < len(h) else "") for c, i in o.items()}
        if _can_xet(g.get("Trạng thái", ""), g.get("Ghi chú", "")) and g.get("Link kênh", "").strip():
            ra.append(g)
    return ra


def _lay_kenh_mac_dinh(goc: str, ma_kenh: str) -> Callable[..., Any]:
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    if ncc.nhom_cua(goc, ma_kenh):
        return ncc.lay_kenh_co_dem(goc, ma_kenh)   # đệm `kenh-do.json` 7 ngày, chung cả nhóm
    from .youtube import fetch_channel  # noqa: PLC0415

    return fetch_channel


def _dem_trang_thai(goc: str, cac_kenh: Sequence[str]) -> Dict[str, Dict[str, int]]:
    ra = {}
    for ma in cac_kenh:
        cot, hang = db.doc(goc, ma)
        o = db.chi_so_cot(list(cot))
        dem = {db.THEO_DOI: 0, db.BO: 0, db.HET: 0, "ai_co": 0}
        for h in hang:
            tt = str(h[o["Trạng thái"]]).strip() if "Trạng thái" in o and o["Trạng thái"] < len(h) else ""
            if tt in dem:
                dem[tt] += 1
            if tt == db.THEO_DOI and db.COT_AI in o and o[db.COT_AI] < len(h) and h[o[db.COT_AI]] == "có":
                dem["ai_co"] += 1
        ra[ma] = dem
    return ra


def kiem(goc: str, cac_kenh: Sequence[str], client: Any, *, sua: Sequence[str] = (),
         goi: Optional[Callable[..., str]] = None, dung_lai_phan_quyet: bool = True,
         toi_da_ai: Optional[int] = None, hom_nay: Optional[_dt.date] = None,
         on_log: Optional[Callable[[str], None]] = None,
         lay_kenh: Optional[Callable[..., Any]] = None, toi_da_lam_moi: Optional[int] = None,
         goi_anh: Optional[Callable[..., str]] = None, tai_anh: Optional[Callable[[str], Optional[bytes]]] = None,
         toi_da_lam_ai: Optional[int] = None) -> Dict[str, Any]:
    """Đợt kiểm cửa duyệt cho mọi dòng "theo dõi"/"hết"/"bỏ-sức-sống" của `cac_kenh` (cùng nhóm). Kênh
    trong `sua` được ghi danh bạ; kênh còn lại chỉ ra đề xuất.

    Số đo: "theo dõi" lấy từ `content.csv` cả nhóm (quét mỗi lượt); "hết"/"bỏ" không còn được quét nên
    đo bằng ảnh chụp mới (`lay_kenh`, mặc định có đệm nhóm; tối đa `toi_da_lam_moi` kênh) — chỉ khi có
    `lay_kenh` hoặc client thật. "Làm bằng AI": `hoi_lam_ai` cho kênh đúng chủ đề chưa có phán quyết
    (đệm `kenh-lam-ai.json`, tối đa `toi_da_lam_ai`) — chỉ khi có `goi_anh` hoặc client thật.
    Trả `{"nguong", "theo_kenh": {mã: [dòng báo cáo]}, "phan", "so", "truoc", "sau", "ai"}`."""
    def log(m: str) -> None:
        if on_log is not None:
            on_log(m)

    hom_nay = hom_nay or _dt.date.today()
    ngay = hom_nay.strftime("%d/%m")
    truoc = _dem_trang_thai(goc, cac_kenh)
    nhom_tv = list(dict.fromkeys(list(cac_kenh) + [m for k in cac_kenh for m in _thanh_vien(goc, k)]))
    so = so_kenh_ca_nhom(goc, nhom_tv, hom_nay)
    dong_td = {ma: _theo_doi(goc, ma) for ma in cac_kenh}
    ten_td = {g.get("Kênh", "").strip() for ds in dong_td.values() for g in ds
              if g.get("Trạng thái", "").strip() == db.THEO_DOI}
    nguong = nguong_nhom(so, ten_td)
    log("  ngưỡng kênh bé (phân vị {0:.0%} của {1:.0f} kênh theo dõi): trung vị view < {2:,.0f} · view/tháng < {3:,.0f}"
        .format(PHAN_VI_YEU, nguong["so_mau"], nguong["trung_vi_gan"], nguong["view_thang"]))
    co_mang = hasattr(client, "request")   # object() giả trong bài kiểm không phải client
    # Hợp mọi dòng ở bất kỳ thành viên nào — phán MỘT lần cho cả nhóm. Kênh "theo dõi" ở một kênh nào
    # đó thì số đo content.csv là tươi; chỉ kênh "hết"/"bỏ" ở MỌI kênh mới cần ảnh chụp mới.
    hop: Dict[str, Dict[str, Any]] = {}
    for ma, ds in dong_td.items():
        for g in ds:
            k = db.khoa(g["Link kênh"])
            la_td = g.get("Trạng thái", "").strip() == db.THEO_DOI
            if k in hop:
                hop[k]["theo_doi"] = hop[k]["theo_doi"] or la_td
                continue
            ten = g.get("Kênh", "").strip()
            s = so.get(ten)
            hop[k] = {"link": g["Link kênh"].strip(), "ten": ten, "subs": g.get("Subs", ""),
                      "view_tv": g.get("View TV", ""), "so_video": g.get("Số video", ""),
                      "dai_tv": g.get("Dài TV", ""), "tieu_de": list(s.tieu_de) if s else [], "so": s,
                      "ghi_chu": (g.get("Tuyến", "") + " " + g.get("Ghi chú", "")).strip(), "theo_doi": la_td}
    # 0) ảnh chụp mới cho kênh không còn được quét ("hết", "bỏ" vì sức sống) — để biết nó hồi sinh chưa
    if lay_kenh is None and co_mang:
        lay_kenh = _lay_kenh_mac_dinh(goc, cac_kenh[0])
    if lay_kenh is not None:
        can_moi = [h for h in hop.values() if not h["theo_doi"]]
        if toi_da_lam_moi is not None:
            can_moi = can_moi[:max(0, int(toi_da_lam_moi))]
        if can_moi:
            log("  đo lại {0} kênh hết/bỏ-sức-sống (ảnh chụp mới, có đệm)…".format(len(can_moi)))
        try:   # cùng `lang` với lượt chốt → trúng đệm `kenh-do.json` (khoá link|số video|lang)
            from .trang_chu import ngon_ngu_kenh  # noqa: PLC0415

            lang = ngon_ngu_kenh(goc, cac_kenh[0])
        except Exception:  # noqa: BLE001
            lang = ""
        for h in can_moi:
            try:
                ch = lay_kenh(h["link"], max_videos=SO_TIEU_DE_CHUP, lang=lang)
            except Exception:  # noqa: BLE001 — một kênh hỏng không giết đợt kiểm
                continue
            s = so_kenh_tu_channel(ch, hom_nay) if ch is not None else None
            if s is not None and s.so_video_dai:
                h["so"], h["tieu_de"] = s, list(s.tieu_de)
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
    co_goi = goi is not None or co_mang
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
           if (ai.get(h["link"]) or {}).get("k") == NGHI
           or ((ai.get(h["link"]) or {}).get("k") == GIU and (h["so"] is None or not h["so"].so_video_dai))]
    if sau and client is not None and co_goi:
        log("  lượt SÂU (30 tiêu đề + số hoạt động) cho {0} kênh lưng chừng…".format(len(sau)))
        moi2 = hoi_ngach(client, sau, mo_ta_ngach=_mo_ta_ngach(goc, cac_kenh[0]), goi=goi, on_log=on_log, sau=True,
                         de_bai_goc=de_bai_cho(goc, cac_kenh[0])[1])
        moi2 = {l: dict(v, ly_do="(lượt sâu) " + v.get("ly_do", "")) for l, v in moi2.items()}
        ghi_phan_quyet_nhom(goc, cac_kenh[0], moi2)
        ai.update(moi2)
    # 3) quyết cuối — cửa duyệt: sai chủ đề → bỏ; đúng chủ đề mà không còn làm/không phát triển → hết;
    #    LLM hỏng → NGHI = không đổi gì (trừ kênh đang theo dõi đã chết: hết ngay, ngách xét lượt sau)
    phan: Dict[str, Tuple[str, str]] = {}
    for k, h in hop.items():
        het, ly_may = cua_suc_song(h["so"], nguong)
        v = ai.get(h["link"])
        if v is not None and v["k"] == BO:
            phan[k] = (BO, v["ly_do"] or "")
        elif het == HET and ((v is not None and v["k"] == GIU) or h["theo_doi"]):
            phan[k] = (HET, ly_may)
        elif v is None or v["k"] == NGHI:
            phan[k] = (NGHI, "LLM chưa quyết được (lỗi lượt gọi) — giữ nguyên, lượt sau quyết lại")
        else:
            phan[k] = (v["k"], v["ly_do"] or "")
    # 4) làm bằng AI? — cho kênh đúng chủ đề (theo dõi / hết), đệm `HAN_LAM_AI_NGAY` ngày
    kho_ai = lam_ai_kho(goc, cac_kenh[0])
    if (goi_anh is not None or co_mang) and client is not None:
        can_ai = [h for k, h in hop.items() if phan[k][0] in (GIU, HET) and _khoa_link(h["link"]) not in kho_ai
                  and h["so"] is not None and h["so"].ma_video]
        can_ai.sort(key=lambda h: phan[db.khoa(h["link"])][0] != GIU)   # theo dõi trước
        if toi_da_lam_ai is not None:
            can_ai = can_ai[:max(0, int(toi_da_lam_ai))]
        if can_ai:
            log("  LLM thị giác 'làm bằng AI?' cho {0} kênh ({1} bìa/kênh)…".format(len(can_ai), SO_ANH_LAM_AI))
            hoi_lam_ai(client, [{"link": h["link"], "ten": h["ten"], "tieu_de": h["tieu_de"],
                                 "ma_video": h["so"].ma_video} for h in can_ai],
                       goi=goi_anh, tai=tai_anh, on_log=on_log,
                       ghi_moi_lo=lambda p: _ghi_lam_ai(goc, cac_kenh[0], p))
            kho_ai = lam_ai_kho(goc, cac_kenh[0])
    ai_co = {}
    for k, h in hop.items():
        m = kho_ai.get(_khoa_link(h["link"]))
        if m is not None:
            ai_co[k] = bool(m["ai"])
    theo_kenh: Dict[str, List[Dict[str, str]]] = {}
    for ma in cac_kenh:
        theo_kenh[ma] = ap_vao_danh_ba(goc, ma, phan, ngay=ngay, sua=ma in set(sua), ai_co=ai_co)
        if ma in set(sua):
            n = lam_sach_danh_sach_chon(goc, ma)
            if n:
                log("  {0}: gạt {1} dòng khỏi danh-sach-chon.json (kênh nguồn không còn theo dõi)".format(ma, n))
    for ma, ds in theo_kenh.items():
        so_ket = {x: sum(1 for d in ds if d["ket"] == x) for x in (GIU, BO, HET, NGHI)}
        log("  {0}{1}: GIỮ {2} · BỎ {3} · HẾT {4} · NGHI {5}".format(
            ma, "" if ma in set(sua) else " (chỉ đề xuất)", so_ket[GIU], so_ket[BO], so_ket[HET], so_ket[NGHI]))
    return {"nguong": nguong, "theo_kenh": theo_kenh, "phan": phan, "so": {h["link"]: h["so"] for h in hop.values()},
            "truoc": truoc, "sau": _dem_trang_thai(goc, cac_kenh), "ai": ai_co}


#: Số video một ảnh chụp đo lại kênh hết — trùng `chot_doi_thu.SO_TIEU_DE_DO` để dùng chung đệm `kenh-do.json`.
SO_TIEU_DE_CHUP = 40


def kiem_dinh_ky(goc: str, ma_kenh: str, client: Any, *, goi: Optional[Callable[..., str]] = None,
                 toi_da_ai: int = 30, on_log: Optional[Callable[[str], None]] = None,
                 toi_da_lam_moi: int = 40, toi_da_lam_ai: int = 24) -> Dict[str, Any]:
    """Đợt kiểm định kỳ cho MỘT kênh (gọi cuối `chot_doi_thu.chot` mỗi lượt nghiên cứu có ví): cửa duyệt
    cho mọi "theo dõi"/"hết" + LLM ngách tối đa `toi_da_ai` kênh chưa có phán quyết nhóm + đo lại tối đa
    `toi_da_lam_moi` kênh hết + "làm bằng AI" tối đa `toi_da_lam_ai` kênh.
    `kenh.yaml: kiem_ngach_tu_sua: false` → chỉ tính đề xuất, không ghi danh bạ."""
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        cai = {}
    tu_sua = str(cai.get("kiem_ngach_tu_sua", True)).strip().lower() not in ("false", "0", "no", "off")
    return kiem(goc, [ma_kenh], client, sua=[ma_kenh] if tu_sua else [], goi=goi, toi_da_ai=toi_da_ai,
                on_log=on_log, toi_da_lam_moi=toi_da_lam_moi, toi_da_lam_ai=toi_da_lam_ai)
