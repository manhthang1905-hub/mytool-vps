"""Bài học sản xuất — vòng phản hồi CTR/AVD → CÁCH THỂ HIỆN (không phải NỘI DUNG).

═══ ĐANG LÀM GÌ, VÀ VÌ SAO ═══

Ba mảnh vòng phản hồi đã có sẵn trong kho: tiêu đề (`auto_khau.tieu_de_thang_cua_kenh`),
hook/kịch bản (`chi_so_ytb.su_that_kenh`), và thumbnail (`ban_giao_dang.CHON-*` nối với
`auto_khau.KIEU_THUMB` nhưng CHƯA ai đọc CTR của nó). Tệp này KHÔNG viết lại ba mảnh đó —
nó chỉ RÚT SỐ từ chính số liệu Studio thật đã có (`CHANNEL/<kênh>/chi-so/`) thành các "quan
sát có số" (không phải luật cứng), theo đúng bản thiết kế đã duyệt
`workspace/THIET-KE-BAI-HOC-SAN-XUAT.md`.

Bước 1+2 (đã xong): CHỈ đọc đĩa và GHI một tệp JSON kết quả — không module nào gọi hàm ở đây,
không đổi hành vi tool.

Bước 3 (tệp này, thêm `xuat_markdown` + nút bấm thủ công ở `ui_qt/trang_cong_thuc_v7.py`):
người dùng tự bấm để XEM bài học — vẫn KHÔNG có gì tự động bơm vào prompt sản xuất. Việc bơm
bài học vào prompt viết/chấm là các bước sau (4-7), làm khi bước này đã chạy ổn ≥1 tuần (mục 4
của bản thiết kế).

═══ RANH GIỚI VỚI CÔNG THỨC V7 ═══

`core/cong_thuc_v7.py` CHỌN NỘI DUNG nào được làm tiếp (cờ `.thang`, dựa hiển thị 48h) —
tệp này không đụng tới quyết định đó, chỉ IMPORT `video_cua_kenh`/`cum_cua_tieu_de` để dùng
lại đúng cách tính TUỔI THẬT và CỤM CHỦ ĐỀ mà V7 đang chấm, tránh có hai định nghĩa "cụm" hay
"tuổi video" khác nhau trong kho. CTR/AVD ở đây chỉ nói về CÁCH THỂ HIỆN (tiêu đề viết sao,
ảnh bìa concept nào, video dài bao lâu) của một đề tài V7 ĐÃ chọn — không bao giờ dùng để lật
lại cờ `.thang`.

═══ AN TOÀN DỮ LIỆU ═══

Không gọi mạng, không phụ thuộc Qt, thuần đọc đĩa (và ghi đúng một tệp
`CHANNEL/<kênh>/nghien-cuu/bai-hoc-san-xuat.json`, ghi nguyên tử bằng `os.replace` như
`core/chon_content.py._luu`). Kênh mới chưa đủ mẫu thì trả danh sách rỗng — không suy diễn từ
1-2 video, không ném lỗi.

Ngưỡng độ tin cậy (thận trọng hơn V7 một bậc vì đây là suy diễn 2 tầng — cụm rồi mới CTR):
`thap` n<3, `vua` 3≤n<6, `cao` n≥6. Bài học không bao giờ bị XOÁ khi số liệu mới mâu thuẫn với
một bài học `cao` đã lưu — chỉ hạ độ tin cậy của bài học MỚI và giữ lại cả hai (xem `_hop_nhat`).
Gỡ một bài học sai là việc của người: mở tệp JSON, xoá đúng dòng đó.
"""

from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re
import statistics
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

from . import cong_thuc_v7 as _v7
from .auto_khau import KIEU_THUMB
from .chi_so_ytb import BanGhi, doc_kenh, thu_muc_cua_kenh, tim_luot_theo_tieu_de
from .doi_thu_kenh import thu_muc_nghien_cuu
from .kenh import duong_kenh

__all__ = ["VideoHoc", "BaiHoc", "video_du_tuoi_de_hoc", "rut_bai_hoc",
           "luu_bai_hoc", "doc_bai_hoc", "duong_tep_bai_hoc",
           "xuat_markdown", "duong_tep_markdown"]

#: Tên tệp kết quả, nằm cạnh các tệp nghiên cứu khác của kênh (`doi_thu.csv`, `phan-tich-*.md`).
TEN_TEP = "bai-hoc-san-xuat.json"
#: Bản người đọc — cùng thư mục, khuôn theo `CHANNEL/<kênh>/CONG-THUC-V7.md`.
TEN_TEP_MD = "BAI-HOC-SAN-XUAT.md"

#: Ngưỡng độ tin cậy — xem mục 3 bản thiết kế. `cao` được xếp hạng few-shot (bước sau); `vua`
#: chỉ bơm dạng dữ liệu thô kèm cỡ mẫu; `thap` không bơm gì, chỉ ghi cho người đọc.
NGUONG_CAO = 6
NGUONG_VUA = 3

#: Thư mục lượt sản xuất AUTO — nơi `7-thumbnail/CHON-*.jpg` và `1-tieu-de.txt` của mỗi video
#: đã đăng còn nằm lại, để nối ngược tiêu đề đã đăng ↔ concept ảnh bìa đã chọn.
_THU_MUC_AUTO = os.path.join("PROJECTS", "AUTO")


@dataclass
class VideoHoc:
    """Một video ĐỦ TUỔI để rút bài học — số đã gộp từ `cong_thuc_v7` (tuổi, cụm) và
    `chi_so_ytb` (CTR/AVD/độ dài thật), cộng concept ảnh bìa đã chọn nếu nối được."""
    ma: str
    tieu_de: str = ""
    ngay_dang: str = ""
    tuoi_gio: Optional[float] = None
    thoi_luong_giay: Optional[int] = None
    impressions: Optional[float] = None
    ctr: Optional[float] = None
    avd_giay: Optional[float] = None
    avd_pct: Optional[float] = None
    #: CTR ("Thumbnail click-through rate (%)") của hàng "Browse features" trong
    #: `traffic-type.csv`, bản chụp gần mốc 48h nhất (khung 36-60h, cùng khung "48h" mà
    #: `ho_so_video._KHUNG_MOC` dùng) — insight tâm lý Nhật 29/09/2026 mục 1: cổng quyết định
    #: là CTR TRANG CHỦ (Browse), không phải CTR tổng. `None` khi chưa có bản chụp phù hợp.
    ctr_browse_48h: Optional[float] = None
    #: Lượt xem/đăng ký của bản chụp MỚI NHẤT — dùng cho trục `sub_1k_view` (insight mục 4:
    #: nút thắt YPP có thể là ĐĂNG KÝ, không phải giờ xem; cụm kéo view chưa chắc kéo sub).
    views: Optional[float] = None
    subs: Optional[float] = None
    cum: List[str] = field(default_factory=list)
    thumb_version_desc: str = ""
    #: "ai" | "nguoi" | "luat" | "khong_ro" | "" — ai/cái gì đã chọn ảnh bìa
    #: này, đọc từ `thumbnail.chon_boi` của hồ sơ video (Việc 3). Thêm
    #: 28/09/2026 — thuần để GHI NGUỒN cho người đọc `BAI-HOC-SAN-XUAT.md`,
    #: không đổi cách `_bai_hoc_thumbnail_ctr` tính (vẫn gộp mọi nguồn).
    thumb_nguon: str = ""


@dataclass
class BaiHoc:
    """Một QUAN SÁT CÓ SỐ, không phải một luật. Đúng hình dạng đã duyệt ở mục 2.2 bản thiết kế."""
    truc: str            # "thumbnail_ctr" | "tieu_de_cum" | "do_dai_avd"
    cum: str = ""        # rỗng = áp dụng chung cả kênh, không riêng cụm nào
    quan_sat: str = ""   # câu có SỐ, vd: "mot-minh: CTR trung vị 5,1% (n=7) — kênh 4,8% (n=12)"
    so_mau: int = 0
    do_tin_cay: str = "thap"   # thap | vua | cao
    video_dan_chung: List[str] = field(default_factory=list)
    ngay_cap_nhat: str = ""


def _muc_tin_cay(n: int) -> str:
    if n >= NGUONG_CAO:
        return "cao"
    if n >= NGUONG_VUA:
        return "vua"
    return "thap"


def _pct(x: Optional[float], so_le: int = 1) -> str:
    if x is None:
        return "—"
    return "{0:.{1}f}%".format(x, so_le).replace(".", ",")


def _phut(giay: float) -> str:
    return "{0:.1f} phút".format(giay / 60.0).replace(".", ",")


def _mmss_avd(giay: Optional[float]) -> str:
    """`mm:ss` cho AVD tính bằng GIÂY — xem `_bai_hoc_do_dai_avd` vì sao KHÔNG dùng AVD%."""
    if giay is None:
        return "—"
    giay_int = int(round(giay))
    return "{0}:{1:02d}".format(giay_int // 60, giay_int % 60)


def _so(x: Optional[float], so_le: int = 1) -> str:
    """Số thập phân kiểu Việt (dấu phẩy) — dùng cho các trục KHÔNG phải phần trăm,
    vd sub/1.000 view."""
    if x is None:
        return "—"
    return "{0:.{1}f}".format(x, so_le).replace(".", ",")


def _dan_dau(quan_sat: str) -> str:
    """Nhãn đứng đầu câu quan sát (trước dấu `:` đầu tiên) — dùng để so hai lần tính có cùng
    kết luận hay không. Mọi câu `quan_sat` do module này viết ra đều đặt nhãn dẫn đầu là bên
    THẮNG của phép so sánh, và nhãn không bao giờ chứa dấu `:` (xem `_phut`)."""
    return (quan_sat or "").split(":", 1)[0].strip()


# ── Gộp video đủ tuổi ─────────────────────────────────────────────────────────


def _anh_bia_da_chon(thu_muc_luot: str) -> str:
    """Tên tệp `CHON-*` trong `7-thumbnail/` của một lượt AUTO — rỗng nếu chưa ai chọn.

    Cố tình KHÔNG rơi về "lấy tấm đầu" như `ban_giao_dang._tim_thumb` — đó là quyết định dự
    phòng của khâu bàn giao khi không ai chọn, không phải bằng chứng "concept X được chọn vì
    CTR cao". Bài học sản xuất chỉ được phép bám đúng cái NGƯỜI đã bấm chọn.
    """
    thu_muc = os.path.join(thu_muc_luot, "7-thumbnail")
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return ""
    for t in ten:
        if t.startswith("CHON-") and os.path.splitext(t)[1].lower() in (
                ".jpg", ".jpeg", ".png", ".webp"):
            return t
    return ""


_RE_THUMB_SO = re.compile(r"thumb_(\d+)\.", re.IGNORECASE)


def _version_desc_tu_ten_anh(ten_tep: str) -> str:
    """`CHON-thumb_002.png` → `dramatic_scene`.

    Khâu 7 đặt tên ảnh theo CHỈ SỐ thứ tự (`thumb_{i:03d}`, xem `auto_khau._tep_bia` và
    `_chuan_bi_bia` ~dòng 6743-6788), không theo tên concept. Vị trí trong `KIEU_THUMB` (cùng
    tệp, ~dòng 6529) là mối nối DUY NHẤT trên đĩa giữa tên tệp và `version_desc` — đổi thứ tự
    `KIEU_THUMB` mà không đổi tên tệp cũ thì mối nối này lệch, nhưng đó là rủi ro có sẵn của
    tool, không phải thứ tệp này gây ra.
    """
    ten = ten_tep[5:] if ten_tep.upper().startswith("CHON-") else ten_tep
    m = _RE_THUMB_SO.match(ten)
    if not m:
        return ""
    idx = int(m.group(1)) - 1
    if 0 <= idx < len(KIEU_THUMB):
        return KIEU_THUMB[idx][0]
    return ""


#: Khung "mốc 48h" để đọc `traffic-type.csv` — CÙNG khung mà `ho_so_video._KHUNG_MOC` dùng
#: cho tên khoá "48h" (nhân đôi có chủ ý, xem ghi chú `ho_so_video._version_desc_tu_ten_anh`
#: về vì sao hai module không nhập hàm/hằng riêng của nhau).
_MOC_BROWSE_THAP, _MOC_BROWSE_CAO = 36.0, 60.0
_RE_MOC_GIO_THU_MUC = re.compile(r"(\d+)h")


def _doc_ctr_browse_48h(kenh_chi_so_dir: str, video_id: str) -> Optional[float]:
    """CTR ("Thumbnail click-through rate (%)") của hàng "Browse features" trong
    `traffic-type.csv` — bản chụp GẦN 48h NHẤT còn trong khung 36-60h.

    `traffic-type.csv` là bảng THÔ Studio xuất riêng theo LOẠI bề mặt (Trang chủ · Tiếp theo ·
    Tìm kiếm…) — `chi_so_ytb.tram._bung_zip` ghi nó cạnh `tong-quan.json` khi dòng tiêu đề bắt
    đầu bằng "Traffic source,". KHÔNG có bộ giải mã nào gộp bảng này vào `tong-quan.json`/
    `BanGhi` (`traffic` ở đó chỉ là % VIEW theo nguồn, không phải CTR theo nguồn — xem
    `giai_ma.py` dòng ~283), nên đọc thẳng CSV ở đây thay vì qua `chi_so_ytb.doc_kenh`.

    Không có thư mục video/không có bản chụp nào trong khung/không có hàng "Browse features"
    → `None`, không suy diễn.
    """
    thu_muc_video = os.path.join(kenh_chi_so_dir, video_id)
    ung_vien: List[Tuple[float, str]] = []
    try:
        ten_con = os.listdir(thu_muc_video)
    except OSError:
        return None
    for ten in ten_con:
        m = _RE_MOC_GIO_THU_MUC.fullmatch(ten)
        if not m:
            continue
        gio = float(m.group(1))
        if not (_MOC_BROWSE_THAP <= gio < _MOC_BROWSE_CAO):
            continue
        duong = os.path.join(thu_muc_video, ten, "traffic-type.csv")
        if os.path.isfile(duong):
            ung_vien.append((gio, duong))
    if not ung_vien:
        return None
    ung_vien.sort(key=lambda x: -x[0])  # gần 60h nhất (chín nhất trong khung) thắng
    try:
        with io.open(ung_vien[0][1], encoding="utf-8-sig") as tep:
            noi_dung = tep.read()
    except OSError:
        return None
    for dong in noi_dung.splitlines():
        cot = dong.split(",")
        if cot and cot[0].strip() == "Browse features" and len(cot) > 2:
            try:
                return float(cot[2].strip())
            except ValueError:
                return None
    return None


def _thumb_tu_ho_so(goc: str, kenh: str) -> Dict[str, Tuple[str, str]]:
    """`{video_id: (kiểu thumbnail, ai/cái gì đã chọn)}` đọc từ hồ sơ video bền
    (`core.ho_so_video`, Việc 3, 28/09/2026) — ưu tiên nguồn NÀY hơn quét
    `PROJECTS/AUTO` (xem `_anh_bia_da_chon` dưới): thư mục lượt AUTO bị
    `core.don_dep*` xoá sau khi đăng, còn hồ sơ thì không, nên đây là nguồn
    BỀN duy nhất một khi video đã đăng lâu — đúng lúc `video_du_tuoi_de_hoc`
    cần nó nhất (video ≥7 ngày tuổi gần như chắc chắn đã bị dọn).

    Trả rỗng, KHÔNG ném lỗi, khi kho chưa có hồ sơ nào (kênh chưa chạy qua
    Việc 3, hoặc `core.ho_so_video` không nạp được).
    """
    ra: Dict[str, Tuple[str, str]] = {}
    try:
        from . import ho_so_video  # noqa: PLC0415 — tránh vòng nhập lúc nạp module
        thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
        ten_tep = os.listdir(thu_muc)
    except Exception:  # noqa: BLE001
        return ra
    for ten in ten_tep:
        if not ten.endswith(".json"):
            continue
        try:
            with io.open(os.path.join(thu_muc, ten), encoding="utf-8") as tep:
                ho_so = json.load(tep)
        except (OSError, ValueError):
            continue
        if not isinstance(ho_so, dict):
            continue
        vid = ho_so.get("video_id")
        thumb = ho_so.get("thumbnail") or {}
        kieu = thumb.get("kieu") if isinstance(thumb, dict) else ""
        if vid and kieu:
            ra[str(vid)] = (str(kieu), str(thumb.get("chon_boi") or ""))
    return ra


def video_du_tuoi_de_hoc(goc: str, kenh: str, tuoi_toi_thieu_gio: float = 168,
                         *, bay_gio: Optional[_dt.datetime] = None) -> List[VideoHoc]:
    """Video của `kenh` đã ≥ `tuoi_toi_thieu_gio` (mặc định 7 ngày) VÀ có đủ ctr/avd/impressions.

    Tuổi thật và cụm chủ đề lấy qua `cong_thuc_v7.video_cua_kenh` — dùng lại đúng bộ máy V7
    đang chấm "thắng" thay vì tự tính lại tuổi từ `ngay_dang` (V7 đã xử lý hai định dạng ngày
    và phạm vi `ngay_bat_dau` của kênh, tự viết lại là nhân đôi một chỗ có thể lệch).

    CTR/AVD/độ dài lấy qua `chi_so_ytb.doc_kenh` vì `VideoMinh` của V7 không mang các số này.
    Bản chụp MỚI NHẤT của video làm nguồn CTR/AVD (đã ổn định ở mốc xa); độ dài thật thì lấy ở
    BẤT KỲ bản chụp nào có, vì bản mới nhất của một số video (đo trên TL4-T7: `v94a9288a26`,
    `v5d2ba23cb3`) không mang `thoi_luong_giay` dù các bản chụp sớm hơn có.

    Kiểu ảnh bìa: đọc HỒ SƠ VIDEO trước (`_thumb_tu_ho_so`, khớp thẳng bằng `video_id` —
    đáng tin hơn khớp mờ tiêu đề), video nào chưa có hồ sơ (đăng trước Việc 3 và chưa chạy
    `ho_so_video.bu_ho_so`) thì lùi về quét `PROJECTS/AUTO` như cũ (`_anh_bia_da_chon`, chỉ
    nhận ảnh `CHON-*` — tức người/AI đã BẤM CHỌN, không phải cả tấm mặc định rơi vào).
    """
    ra: List[VideoHoc] = []
    try:
        videos_v7 = {v.ma: v for v in _v7.video_cua_kenh(goc, kenh, bay_gio=bay_gio)}
        channel_dir = duong_kenh(goc)
        ban_ghi = doc_kenh(kenh, goc=channel_dir)
    except Exception:  # noqa: BLE001 — kênh mới/thiếu số liệu thì trả rỗng, không vỡ khâu gọi
        return ra
    theo_video: Dict[str, List[BanGhi]] = {}
    for b in ban_ghi:
        theo_video.setdefault(b.video_id, []).append(b)

    thu_muc_auto = os.path.join(goc, _THU_MUC_AUTO)
    thumb_ho_so = _thumb_tu_ho_so(goc, kenh)
    kenh_chi_so_dir = thu_muc_cua_kenh(channel_dir, kenh)
    for ma, danh_sach in theo_video.items():
        vm = videos_v7.get(ma)
        if vm is None or vm.tuoi_gio is None or vm.tuoi_gio < tuoi_toi_thieu_gio:
            continue
        danh_sach.sort(key=lambda b: (b.moc_gio if b.moc_gio is not None else -1))
        moi_nhat = danh_sach[-1]
        if moi_nhat.ctr is None or moi_nhat.avd_pct is None or moi_nhat.impressions is None:
            continue
        thoi_luong = next((b.thoi_luong_giay for b in reversed(danh_sach)
                           if b.thoi_luong_giay), None)
        tieu_de = vm.tieu_de or next((b.tieu_de for b in reversed(danh_sach) if b.tieu_de), "")
        version_desc, nguon_thumb = thumb_ho_so.get(ma, ("", ""))
        if not version_desc:
            try:
                thu_muc_luot = tim_luot_theo_tieu_de(tieu_de, thu_muc_auto) if tieu_de else ""
                if thu_muc_luot:
                    anh = _anh_bia_da_chon(thu_muc_luot)
                    if anh:
                        version_desc = _version_desc_tu_ten_anh(anh)
                        nguon_thumb = "nguoi"  # `_anh_bia_da_chon` chỉ nhận `CHON-*`
            except Exception:  # noqa: BLE001 — thiếu nối thumbnail thì thôi, vẫn còn CTR/AVD
                pass
        ra.append(VideoHoc(
            ma=ma, tieu_de=tieu_de, ngay_dang=vm.ngay_dang, tuoi_gio=vm.tuoi_gio,
            thoi_luong_giay=thoi_luong, impressions=moi_nhat.impressions,
            ctr=moi_nhat.ctr, avd_giay=moi_nhat.avd_giay, avd_pct=moi_nhat.avd_pct,
            ctr_browse_48h=_doc_ctr_browse_48h(kenh_chi_so_dir, ma),
            views=moi_nhat.views, subs=moi_nhat.subs,
            cum=list(vm.cum), thumb_version_desc=version_desc, thumb_nguon=nguon_thumb,
        ))
    return ra


# ── Rút bài học ───────────────────────────────────────────────────────────────


def _bai_hoc_tieu_de_cum(videos: Sequence[VideoHoc], hom_nay: str) -> List[BaiHoc]:
    """Trục `tieu_de_cum`: CTR trung vị của mỗi CỤM CHỦ ĐỀ so với trung vị cả kênh.

    Video không thuộc cụm nào (`cum` rỗng — đề tài ngoài bộ từ khoá cấu hình, hoặc video đời
    trước kênh) vẫn góp vào trung vị NỀN của kênh nhưng không tự bịa một "cụm rỗng" để so sánh.
    """
    co_ctr = [v for v in videos if v.ctr is not None]
    if not co_ctr:
        return []
    ctr_kenh = [v.ctr for v in co_ctr]
    tv_kenh = statistics.median(ctr_kenh)
    theo_cum: Dict[str, List[VideoHoc]] = {}
    for v in co_ctr:
        for c in v.cum:
            theo_cum.setdefault(c, []).append(v)
    ra: List[BaiHoc] = []
    for cum, ds in sorted(theo_cum.items()):
        n = len(ds)
        tv_cum = statistics.median(v.ctr for v in ds)
        dan_chung = [v.ma for v in sorted(ds, key=lambda v: -(v.ctr or 0))[:5]]
        quan_sat = "{0}: CTR trung vị {1} (n={2}) — trung vị cả kênh {3} (n={4})".format(
            cum, _pct(tv_cum), n, _pct(tv_kenh), len(co_ctr))
        ra.append(BaiHoc(truc="tieu_de_cum", cum=cum, quan_sat=quan_sat, so_mau=n,
                         do_tin_cay=_muc_tin_cay(n), video_dan_chung=dan_chung,
                         ngay_cap_nhat=hom_nay))
    return ra


def _bai_hoc_do_dai_avd(videos: Sequence[VideoHoc], hom_nay: str) -> List[BaiHoc]:
    """Trục `do_dai_avd`: chia video làm hai nhóm NGẮN/DÀI theo TRUNG VỊ độ dài của chính kênh
    (không phải một ngưỡng phút cố định — mỗi kênh một nhịp khác nhau), so AVD TÍNH BẰNG GIÂY
    trung vị.

    ═══ VÌ SAO GIÂY, KHÔNG PHẢI % (đổi 29/09/2026) ═══

    AVD% = giây xem tuyệt đối ÷ độ dài video — cùng một lượng giây xem thật, video NGẮN tự ra
    % cao hơn video DÀI mà không cần giữ chân tốt hơn thật. Bài học "≤15 phút tốt hơn" từng ở
    mức tin CAO hoá ra là ẢO SỐ HỌC của chính công thức này: insight tâm lý Nhật 29/09/2026
    (mục 5) đo trên TL4 — AVD giây gần như PHẲNG (4:40-5:40) bất kể độ dài, trong khi AVD% luôn
    đẩy kết luận về phía "ngắn thắng"; 5 video thắng thật dài 15:19-18:57, đối thủ 15-21 phút
    hit 14,5% so với 10,4% của 12-15 phút. AVD giây không có thiên lệch cơ học đó.

    Một bài học `cao` đã lưu trước đây (tính bằng %) có thể kết luận NGƯỢC với bài mới (tính
    bằng giây) trên CÙNG một kênh — đó không phải lỗi, mà đúng là điều mục này sửa. Cơ chế giữ
    lịch sử (`_hop_nhat`, gọi trong `luu_bai_hoc`) tự phát hiện nhãn dẫn đầu đổi chiều, HẠ tin
    cậy bài mới và GHI RÕ mâu thuẫn, không xoá bài `cao` cũ — người đọc `BAI-HOC-SAN-XUAT.md`
    thấy cả hai, không bị âm thầm đổi kết luận.

    Áp dụng CHUNG cả kênh (`cum=""`), không tách theo từng cụm — độ dài là quyết định sản xuất
    của cả kênh (`phut_muc_tieu` trong `kenh.yaml`), không phải của riêng một chủ đề, và tách
    nhỏ theo cụm ở đây chỉ làm cỡ mẫu vốn đã ít càng thêm vụn.
    """
    co_du = [v for v in videos if v.thoi_luong_giay and v.avd_giay is not None]
    if len(co_du) < 2:
        return []
    nguong = statistics.median(v.thoi_luong_giay for v in co_du)
    ngan = [v for v in co_du if v.thoi_luong_giay <= nguong]
    dai = [v for v in co_du if v.thoi_luong_giay > nguong]
    if not ngan or not dai:
        return []
    tv_ngan = statistics.median(v.avd_giay for v in ngan)
    tv_dai = statistics.median(v.avd_giay for v in dai)
    so_mau = min(len(ngan), len(dai))
    nhan_ngan = "ngắn (≤{0})".format(_phut(nguong))
    nhan_dai = "dài (>{0})".format(_phut(nguong))
    if tv_ngan >= tv_dai:
        thang, thua = (nhan_ngan, tv_ngan, ngan), (nhan_dai, tv_dai, dai)
    else:
        thang, thua = (nhan_dai, tv_dai, dai), (nhan_ngan, tv_ngan, ngan)
    (nhan1, tv1, ds1), (nhan2, tv2, ds2) = thang, thua
    quan_sat = "{0}: AVD trung vị {1} (n={2}) — {3}: {4} (n={5})".format(
        nhan1, _mmss_avd(tv1), len(ds1), nhan2, _mmss_avd(tv2), len(ds2))
    dan_chung = [v.ma for v in sorted(ds1, key=lambda v: -(v.avd_giay or 0))[:5]]
    return [BaiHoc(truc="do_dai_avd", cum="", quan_sat=quan_sat, so_mau=so_mau,
                   do_tin_cay=_muc_tin_cay(so_mau), video_dan_chung=dan_chung,
                   ngay_cap_nhat=hom_nay)]


def _bai_hoc_thumbnail_ctr(videos: Sequence[VideoHoc], hom_nay: str) -> List[BaiHoc]:
    """Trục `thumbnail_ctr`: CTR trung vị theo CONCEPT ảnh bìa đã chọn (`version_desc`).

    Ưu tiên so trong CÙNG MỘT CỤM trước (cô lập ảnh hưởng của ảnh bìa khỏi ảnh hưởng của đề tài
    — dramatic_scene ăn CTR ở cụm này chưa chắc ăn ở cụm khác); kênh nào chưa đủ mẫu để tách
    theo cụm thì vẫn có thêm một dòng gộp cả kênh (`cum=""`) làm phao — thà một quan sát rộng
    còn hơn không có gì.
    """
    co_thumb = [v for v in videos if v.thumb_version_desc and v.ctr is not None]
    ra: List[BaiHoc] = []

    def _dong(cum: str, ds: Sequence[VideoHoc]) -> Optional[BaiHoc]:
        theo_concept: Dict[str, List[VideoHoc]] = {}
        for v in ds:
            theo_concept.setdefault(v.thumb_version_desc, []).append(v)
        if len(theo_concept) < 2:
            return None
        thong_ke = sorted(
            ((c, statistics.median(v.ctr for v in vs), len(vs), vs)
             for c, vs in theo_concept.items()),
            key=lambda x: -x[1])
        quan_sat = "; ".join("{0}: CTR trung vị {1} (n={2})".format(c, _pct(tv), n)
                             for c, tv, n, _vs in thong_ke)
        so_mau = min(n for _c, _tv, n, _vs in thong_ke)
        dan_chung = [v.ma for v in sorted(thong_ke[0][3], key=lambda v: -(v.ctr or 0))[:5]]
        return BaiHoc(truc="thumbnail_ctr", cum=cum, quan_sat=quan_sat, so_mau=so_mau,
                     do_tin_cay=_muc_tin_cay(so_mau), video_dan_chung=dan_chung,
                     ngay_cap_nhat=hom_nay)

    theo_cum: Dict[str, List[VideoHoc]] = {}
    for v in co_thumb:
        for c in v.cum:
            theo_cum.setdefault(c, []).append(v)
    for cum, ds in sorted(theo_cum.items()):
        d = _dong(cum, ds)
        if d:
            ra.append(d)

    d_chung = _dong("", co_thumb)
    if d_chung:
        ra.append(d_chung)
    return ra


def _bai_hoc_ctr_browse(videos: Sequence[VideoHoc], hom_nay: str) -> List[BaiHoc]:
    """Trục `ctr_browse_48h`: CTR TRANG CHỦ (Browse) @48h theo CỤM CHỦ ĐỀ — insight tâm lý
    Nhật 29/09/2026 mục 1: cổng quyết định thật là CTR Browse, không phải CTR tổng (video
    thắng sống nhờ trang chủ 70-95% view; video trượt kẹt ở cột đề xuất). CTR tổng (`v.ctr`,
    trục `tieu_de_cum`) bị PHA LOÃNG bởi các nguồn khác nên không thấy được cổng này.

    Cùng khuôn với `_bai_hoc_thumbnail_ctr`: ưu tiên so trong CÙNG MỘT CỤM, cộng thêm một dòng
    gộp cả kênh (`cum=""`) làm phao cho kênh chưa đủ mẫu tách cụm.
    """
    co_ctr = [v for v in videos if v.ctr_browse_48h is not None]
    if not co_ctr:
        return []
    tv_kenh = statistics.median(v.ctr_browse_48h for v in co_ctr)
    ra: List[BaiHoc] = []

    def _dong(cum: str, ds: Sequence[VideoHoc]) -> BaiHoc:
        n = len(ds)
        tv_cum = statistics.median(v.ctr_browse_48h for v in ds)
        dan_chung = [v.ma for v in sorted(ds, key=lambda v: -(v.ctr_browse_48h or 0))[:5]]
        quan_sat = "{0}: CTR Browse@48h trung vị {1} (n={2}) — trung vị cả kênh {3} (n={4})".format(
            cum or "cả kênh", _pct(tv_cum), n, _pct(tv_kenh), len(co_ctr))
        return BaiHoc(truc="ctr_browse_48h", cum=cum, quan_sat=quan_sat, so_mau=n,
                     do_tin_cay=_muc_tin_cay(n), video_dan_chung=dan_chung, ngay_cap_nhat=hom_nay)

    theo_cum: Dict[str, List[VideoHoc]] = {}
    for v in co_ctr:
        for c in v.cum:
            theo_cum.setdefault(c, []).append(v)
    for cum, ds in sorted(theo_cum.items()):
        ra.append(_dong(cum, ds))
    ra.append(_dong("", co_ctr))
    return ra


def _bai_hoc_sub_1k_view(videos: Sequence[VideoHoc], hom_nay: str) -> List[BaiHoc]:
    """Trục `sub_1k_view`: ĐĂNG KÝ / 1.000 VIEW theo CỤM CHỦ ĐỀ — insight tâm lý Nhật
    29/09/2026 mục 4: nút thắt YPP có thể là ĐĂNG KÝ chứ không phải giờ xem, và cụm kéo VIEW
    chưa chắc là cụm kéo SUB (TL4 đo được: cụm vat-chat ~2,2 sub/1k view, cụm mot-minh 4,2-7,1).

    Tính TỶ LỆ CỘNG DỒN của cả nhóm (tổng sub ÷ tổng view × 1.000), KHÔNG lấy trung vị từng
    video — số sub một video riêng lẻ thường chỉ 0-3, quá thưa để trung vị có nghĩa; cộng dồn
    trước rồi mới chia đúng theo cách insight đã tính.
    """
    co_view = [v for v in videos if v.views]
    if not co_view:
        return []
    tong_view_kenh = sum(v.views for v in co_view)
    tong_sub_kenh = sum(v.subs or 0 for v in co_view)
    ti_le_kenh = tong_sub_kenh * 1000.0 / tong_view_kenh
    theo_cum: Dict[str, List[VideoHoc]] = {}
    for v in co_view:
        for c in v.cum:
            theo_cum.setdefault(c, []).append(v)
    ra: List[BaiHoc] = []
    for cum, ds in sorted(theo_cum.items()):
        tong_view = sum(v.views for v in ds)
        if not tong_view:
            continue
        tong_sub = sum(v.subs or 0 for v in ds)
        ti_le = tong_sub * 1000.0 / tong_view
        n = len(ds)
        dan_chung = [v.ma for v in sorted(ds, key=lambda v: -(v.views or 0))[:5]]
        quan_sat = "{0}: {1} sub/1.000 view (n={2}) — cả kênh {3} (n={4})".format(
            cum, _so(ti_le), n, _so(ti_le_kenh), len(co_view))
        ra.append(BaiHoc(truc="sub_1k_view", cum=cum, quan_sat=quan_sat, so_mau=n,
                         do_tin_cay=_muc_tin_cay(n), video_dan_chung=dan_chung,
                         ngay_cap_nhat=hom_nay))
    return ra


def rut_bai_hoc(goc: str, kenh: str, *, tuoi_toi_thieu_gio: float = 168,
               bay_gio: Optional[_dt.datetime] = None) -> List[BaiHoc]:
    """Năm trục bài học sản xuất của một kênh — CTR×cụm, AVD×độ dài (giây), CTR×concept ảnh
    bìa, CTR Browse@48h×cụm, sub/1.000 view×cụm.

    Thuần tính toán, KHÔNG đọc/ghi tệp `bai-hoc-san-xuat.json` — muốn lưu thì gọi `luu_bai_hoc`
    với kết quả trả về ở đây. Kênh chưa đủ video đủ tuổi thì trả `[]`, không ném lỗi.
    """
    videos = video_du_tuoi_de_hoc(goc, kenh, tuoi_toi_thieu_gio, bay_gio=bay_gio)
    if not videos:
        return []
    hom_nay = (bay_gio or _dt.datetime.utcnow()).date().isoformat()
    ra: List[BaiHoc] = []
    ra.extend(_bai_hoc_tieu_de_cum(videos, hom_nay))
    ra.extend(_bai_hoc_do_dai_avd(videos, hom_nay))
    ra.extend(_bai_hoc_thumbnail_ctr(videos, hom_nay))
    ra.extend(_bai_hoc_ctr_browse(videos, hom_nay))
    ra.extend(_bai_hoc_sub_1k_view(videos, hom_nay))
    return ra


# ── Lưu / đọc, giữ lịch sử ─────────────────────────────────────────────────────


def duong_tep_bai_hoc(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEN_TEP)


def _ha_tin_cay(muc: str) -> str:
    return {"cao": "vua", "vua": "thap"}.get(muc, "thap")


def _hop_nhat(cu: List[BaiHoc], moi: List[BaiHoc]) -> List[BaiHoc]:
    """Gộp bài học vừa tính (`moi`) với bài học đã lưu trên đĩa (`cu`) — GIỮ LỊCH SỬ.

    Luật (mục 2.2/3 bản thiết kế): "không xoá khi mâu thuẫn — chỉ hạ độ tin cậy". Nghĩa là:

    - Bài cũ cùng trục+cụm mà KHÔNG mâu thuẫn (cùng nhãn dẫn đầu, hoặc bài cũ chưa từng đạt
      `cao`) → bài mới THAY THẾ bình thường. Đây chỉ là số liệu được cập nhật thêm mẫu, không
      phải một sự thật khác, giữ cả hai chỉ làm phình file vô ích.
    - Bài cũ đã từng `cao` mà bài mới kết luận NGƯỢC LẠI → bài cũ vẫn nằm nguyên trong file (ai
      đọc cũng thấy cả hai vế), còn bài MỚI bị hạ một bậc tin cậy và ghi rõ đang mâu thuẫn với
      gì — không âm thầm thay một sự thật đã `cao` bằng một sự thật khác chỉ vì tính lại mới hơn.
    - Bài cũ không còn trục+cụm nào tương ứng ở lần tính mới (vd kênh đổi cấu hình cụm) → vẫn
      giữ, vì đó vẫn là lịch sử thật đã đo được.
    """
    theo_khoa: Dict[Tuple[str, str], BaiHoc] = {(b.truc, b.cum): b for b in cu}
    ra: List[BaiHoc] = []
    giu_lai_lich_su: List[BaiHoc] = []
    for m in moi:
        khoa = (m.truc, m.cum)
        c = theo_khoa.pop(khoa, None)
        if (c is not None and c.do_tin_cay == "cao"
                and _dan_dau(c.quan_sat) and _dan_dau(m.quan_sat)
                and _dan_dau(c.quan_sat) != _dan_dau(m.quan_sat)):
            m = replace(m, do_tin_cay=_ha_tin_cay(m.do_tin_cay),
                       quan_sat="{0} (mâu thuẫn với lần trước: {1})".format(
                           m.quan_sat, c.quan_sat))
            giu_lai_lich_su.append(c)
        ra.append(m)
    ra.extend(theo_khoa.values())       # bài cũ không được tính lại lần này — vẫn là lịch sử
    ra.extend(giu_lai_lich_su)          # bài `cao` bị bài mới mâu thuẫn — giữ nguyên, không xoá
    return ra


def doc_bai_hoc(goc: str, kenh: str) -> List[BaiHoc]:
    """Đọc bài học đã lưu; tệp chưa có/hỏng thì trả `[]`, không ném lỗi."""
    duong = duong_tep_bai_hoc(goc, kenh)
    try:
        with io.open(duong, encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return []
    ra: List[BaiHoc] = []
    for m in (du_lieu.get("bai_hoc") or []):
        if not isinstance(m, dict):
            continue
        try:
            ra.append(BaiHoc(
                truc=str(m.get("truc") or ""), cum=str(m.get("cum") or ""),
                quan_sat=str(m.get("quan_sat") or ""), so_mau=int(m.get("so_mau") or 0),
                do_tin_cay=str(m.get("do_tin_cay") or "thap"),
                video_dan_chung=list(m.get("video_dan_chung") or []),
                ngay_cap_nhat=str(m.get("ngay_cap_nhat") or ""),
            ))
        except (TypeError, ValueError):
            continue
    return ra


def luu_bai_hoc(goc: str, kenh: str, bai_hoc_moi: List[BaiHoc], *,
               luc: Optional[_dt.datetime] = None) -> str:
    """Gộp `bai_hoc_moi` với bài học đã lưu (`_hop_nhat`) rồi ghi nguyên tử. Trả đường dẫn tệp.

    Ghi kiểu `.tmp` + `os.replace` — cùng khuôn `core/chon_content.py._luu` — để một tiến trình
    khác đọc file này (vd trạm HTTP đang phục vụ trang) không bao giờ thấy JSON viết dở.
    """
    duong = duong_tep_bai_hoc(goc, kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    hop_nhat = _hop_nhat(doc_bai_hoc(goc, kenh), bai_hoc_moi)
    goi = {
        "kenh": kenh,
        "cap_nhat_luc": (luc or _dt.datetime.now()).replace(microsecond=0).isoformat(),
        "bai_hoc": [asdict(b) for b in hop_nhat],
    }
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(goi, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)
    return duong


# ── Bản người đọc (Bước 3) ──────────────────────────────────────────────────


#: Tên tiếng Việt dễ đọc cho mỗi trục — dùng cả ở đây lẫn tooltip nút bấm (`ui_qt`).
_TRUC_TEN: Dict[str, str] = {
    "tieu_de_cum": "Cụm đề tài × Tỷ lệ bấm (CTR)",
    "do_dai_avd": "Độ dài video × Xem trung bình (AVD, tính bằng giây)",
    "thumbnail_ctr": "Concept ảnh bìa × Tỷ lệ bấm (CTR)",
    "ctr_browse_48h": "Cụm đề tài × Tỷ lệ bấm TRANG CHỦ (CTR Browse) @48h",
    "sub_1k_view": "Cụm đề tài × Đăng ký / 1.000 view",
}
#: Vì sao một trục có thể trống dù kênh đã có video đủ tuổi — nói thật, không im lặng để trống.
_TRUC_LY_DO_RONG: Dict[str, str] = {
    "tieu_de_cum": "chưa video đủ tuổi nào rơi đúng một cụm chủ đề đã cấu hình cho kênh này",
    "do_dai_avd": "chưa đủ video đủ tuổi để tách hai nhóm ngắn/dài (cần ít nhất 2 video có độ dài)",
    "thumbnail_ctr": "chưa nối được ảnh bìa ĐÃ CHỌN (`7-thumbnail/CHON-*.jpg`) của video nào với một "
                     "lượt sản xuất AUTO còn trên đĩa — có thể lượt đã bị dọn dẹp, hoặc video không "
                     "sản xuất qua khâu AUTO của tool",
    "ctr_browse_48h": "chưa có bản chụp nào trong khung 36-60h sau đăng còn `traffic-type.csv` trên "
                      "đĩa (bảng thô Studio xuất riêng, khác `tong-quan.json`)",
    "sub_1k_view": "chưa video đủ tuổi nào có đủ Lượt xem để tính tỷ lệ, hoặc chưa rơi đúng cụm chủ "
                  "đề đã cấu hình",
}
#: Thứ tự cố định khi in — CTR×cụm, AVD×độ dài, CTR×ảnh bìa (bản thiết kế gốc), rồi hai trục
#: thêm 29/09/2026 (insight tâm lý Nhật): CTR Browse@48h×cụm, sub/1.000 view×cụm.
_THU_TU_TRUC: Tuple[str, ...] = ("tieu_de_cum", "do_dai_avd", "thumbnail_ctr",
                                 "ctr_browse_48h", "sub_1k_view")


def duong_tep_markdown(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEN_TEP_MD)


def _ghi_md(duong: str, dong: List[str]) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    os.replace(tam, duong)


def xuat_markdown(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> str:
    """Ghi `CHANNEL/<kênh>/nghien-cuu/BAI-HOC-SAN-XUAT.md` — bản người đọc, khuôn theo
    `CONG-THUC-V7.md` (mục "LUẬT ĐANG DÙNG" / "BẰNG CHỨNG" / "VIỆC CÒN TREO`). Trả đường dẫn.

    Tự đi hết đường `rut_bai_hoc()` → `luu_bai_hoc()` → đọc lại từ đĩa (`doc_bai_hoc`) rồi mới
    viết .md — để bản .md luôn khớp ĐÚNG cái đã lưu (đã gộp lịch sử/mâu thuẫn qua `_hop_nhat`),
    không phải bản tính tạm trong bộ nhớ mà `luu_bai_hoc` có thể đã hạ tin cậy hay giữ lại một
    bài học `cao` cũ. Gọi hàm này một mình là đủ — người gọi (nút bấm, hay `--thu`) không cần tự
    gọi `rut_bai_hoc`/`luu_bai_hoc` trước.
    """
    videos = video_du_tuoi_de_hoc(goc, kenh, bay_gio=bay_gio)
    luu_bai_hoc(goc, kenh, rut_bai_hoc(goc, kenh, bay_gio=bay_gio), luc=bay_gio)
    bai_hoc = doc_bai_hoc(goc, kenh)
    ten_video = {v.ma: (v.tieu_de or v.ma) for v in videos}
    luc = bay_gio or _dt.datetime.now()
    hom_nay = luc.date().isoformat()

    theo_truc: Dict[str, List[BaiHoc]] = {}
    for b in bai_hoc:
        theo_truc.setdefault(b.truc, []).append(b)

    L: List[str] = [
        "# BÀI HỌC SẢN XUẤT — {0} (file sống)".format(kenh),
        "",
        "Rút từ số liệu Studio THẬT (`chi-so/`) — đây là QUAN SÁT CÓ SỐ, không phải luật cứng. "
        "Không đụng tới đề tài `CONG-THUC-V7.md` đã chọn (mục \"Cụm đang thắng\" ở đó vẫn quyết "
        "định LÀM VIDEO GÌ); bài học ở đây chỉ nói CÁCH THỂ HIỆN — viết tiêu đề sao cho hợp cụm, "
        "chọn ảnh bìa concept nào, video nên dài bao lâu.",
        "",
        "**Độ tin cậy:** THẤP (dưới 3 video, n<3) — chỉ để biết, đừng theo · VỪA (3-5 video) — "
        "tham khảo, đừng ép · CAO (từ 6 video trở lên) — đủ để tin khi chọn cách thể hiện.",
        "",
        "Cập nhật lúc: {0} · {1} video đủ tuổi (≥7 ngày) đang được tính vào bài học.".format(
            luc.replace(microsecond=0).isoformat(), len(videos)),
        "",
    ]

    if not videos:
        L.append("**Chưa đủ dữ liệu (cần video ≥7 ngày tuổi).** Kênh còn quá mới hoặc chưa có "
                 "video nào đủ 7 ngày kèm đủ Tỷ lệ bấm/Xem trung bình/Lượt hiển thị — quay lại "
                 "xem sau khi kênh đăng và chạy được một thời gian.")
        L.append("")
        duong = duong_tep_markdown(goc, kenh)
        _ghi_md(duong, L)
        return duong

    L.append("## 1. LUẬT ĐANG DÙNG — cập nhật {0}".format(hom_nay))
    L.append("")
    for truc in _THU_TU_TRUC:
        L.append("### {0}".format(_TRUC_TEN[truc]))
        ds = theo_truc.get(truc) or []
        if not ds:
            L.append("_Chưa đủ dữ liệu ({0})._".format(_TRUC_LY_DO_RONG[truc]))
        else:
            for b in sorted(ds, key=lambda x: (x.cum, -x.so_mau)):
                nhan_cum = " [cụm {0}]".format(b.cum) if b.cum else ""
                L.append("- **{0}**{1}: {2}".format(b.do_tin_cay.upper(), nhan_cum, b.quan_sat))
        L.append("")

    L.append("## 2. BẰNG CHỨNG — mọi bài học đã rút (kể cả bài `thấp`/`vừa` chưa đủ tin cậy)")
    L.append("")
    L.append("| Trục | Cụm | Quan sát | Số mẫu | Độ tin cậy | Video dẫn chứng | Cập nhật |")
    L.append("|---|---|---|---|---|---|---|")
    for b in sorted(bai_hoc, key=lambda x: (_THU_TU_TRUC.index(x.truc)
                                            if x.truc in _THU_TU_TRUC else 99, x.cum)):
        dan_chung = ", ".join((ten_video.get(m, m) or m)[:24] for m in b.video_dan_chung[:3]) or "—"
        L.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            _TRUC_TEN.get(b.truc, b.truc), b.cum or "(chung)", b.quan_sat, b.so_mau,
            b.do_tin_cay, dan_chung, b.ngay_cap_nhat or "—"))
    L.append("")

    L.append("## 3. VIỆC CÒN TREO")
    L.append("")
    con_treo = False
    can_them = [b for b in bai_hoc if b.do_tin_cay != "cao"]
    if can_them:
        con_treo = True
        L.append("**Chưa đủ tin cậy, cần thêm mẫu:**")
        for b in sorted(can_them, key=lambda x: x.so_mau):
            trung_gian = NGUONG_VUA if b.do_tin_cay == "thap" else NGUONG_CAO
            thieu = max(0, trung_gian - b.so_mau)
            len_muc = "vừa" if b.do_tin_cay == "thap" else "cao"
            L.append("- [{0} / cụm {1}] còn thiếu khoảng {2} video nữa mới lên mức {3}: {4}".format(
                _TRUC_TEN.get(b.truc, b.truc), b.cum or "(chung)", thieu, len_muc, b.quan_sat))
        L.append("")
    mau_thuan = [b for b in bai_hoc if "mâu thuẫn" in b.quan_sat]
    if mau_thuan:
        con_treo = True
        L.append("**Đang mâu thuẫn với lần đo trước (giữ lại cả hai bên, chưa xoá bài nào):**")
        for b in mau_thuan:
            L.append("- [{0} / cụm {1}] {2}".format(_TRUC_TEN.get(b.truc, b.truc), b.cum or "(chung)",
                                                    b.quan_sat))
        L.append("")
    truc_rong = [t for t in _THU_TU_TRUC if not theo_truc.get(t)]
    if truc_rong:
        con_treo = True
        L.append("**Trục chưa có bài học nào:**")
        for t in truc_rong:
            L.append("- {0}: {1}.".format(_TRUC_TEN[t], _TRUC_LY_DO_RONG[t]))
        L.append("")
    if not con_treo:
        L.append("Không có gì đang treo lúc này — mọi trục đều đủ mẫu và không mâu thuẫn.")
        L.append("")

    duong = duong_tep_markdown(goc, kenh)
    _ghi_md(duong, L)
    return duong
