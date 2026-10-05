"""Khuôn ảnh bìa THẮNG — Việc 4 của `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

═══ VÌ SAO CÓ TỆP NÀY ═══

Việc 3 (`core/ho_so_video.py`) đã chụp lại "tool đã chọn ảnh bìa nào cho video
này" và nối được số liệu Studio thật (CTR/impressions/AVD) theo 4 mốc giờ
chuẩn. Còn thiếu một bước: đọc NGƯỢC từ số đó ra "ảnh bìa nào đang THẮNG",
rồi nhờ AI NHÌN đúng tấm ảnh ấy tả lại thành một KHUÔN CHỮ (bố cục, màu, chữ)
— để khâu sinh ảnh bìa (`core/auto_khau.py`, kiểu `khuon_thang`) có thể DỰNG
LẠI đúng khuôn đó cho video mới, thay vì đoán mò một bố cục chưa ai đo.

    `tim_video_thang()`  — video nào đang thắng CỦA CHÍNH kênh (mượn của nhóm
                           chỉ khi kênh tự bật `bia_khuon_nhom: true`, xem dưới).
    `anh_da_dang()`      — tải/định vị bản ảnh bìa LÂU DÀI của video đó.
    `cap_nhat()`         — gộp hai hàm trên + 1 lượt AI tả khuôn khi người
                           thắng vừa đổi; ghi `nghien-cuu/khuon-bia-thang.json`
                           (giữ lịch sử, không xoá bản cũ).
    `doc_bai_hoc_anh_bia()` — câu văn ngắn để chèn vào lời nhắc sinh ảnh bìa
                              (`auto_khau._loi_nhac_bia`, chỗ `<<BAI_HOC_ANH_BIA>>`).

═══ 30/09/2026 — VIỆC 4b: TẮT MƯỢN KHUÔN NHÓM THEO MẶC ĐỊNH ═══

Dữ liệu thật 29/09/2026 cho thấy TL1-T7 và TL2-T7 đang MƯỢN khuôn thắng của
TL3-T7 (cùng nhóm) vì chưa đủ mẫu riêng. Chủ dự án cho rằng việc này SAI về
nguyên tắc: mỗi kênh có tệp khán giả riêng, khuôn của kênh khác không chắc
đúng gu khán giả kênh này. Từ nay `tim_video_thang()` CHỈ mượn khuôn nhóm khi
kênh tự bật cờ `bia_khuon_nhom: true` trong `kenh.yaml` (`core/kenh.py`,
mặc định `False`) — kênh chưa đủ dữ liệu riêng thì coi như CHƯA CÓ khuôn,
để `core/chon_bia.py` chuyển sang THĂM DÒ CÓ CHỦ ĐÍCH (ngưỡng khám phá rộng
hơn) thay vì giả vờ đã có một khuôn không chắc đúng gu.

Không gọi mạng trừ khi CẦN tải ảnh bìa đối chứng (`anh_da_dang`, một lần rồi
lưu vĩnh viễn) hoặc mô tả khuôn bằng AI (`cap_nhat`, chỉ khi người thắng vừa
đổi) — cả hai đều rất hiếm khi xảy ra (một lần/kênh cho tới khi có video mới
thắng). Gọi từ `core/vong_hoc.py` bước 4 — KHÔNG được ném lỗi ra ngoài làm
chặn sản xuất, nhưng bản thân module này cứ để lỗi cục bộ nổi lên (người gọi
tự `try/except`, giữ đúng nếp `ho_so_video.py`).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import statistics
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from . import ho_so_video
from .doi_thu_kenh import thu_muc_nghien_cuu
from .kenh import duong_kenh

__all__ = [
    "UngVienThang", "tim_video_thang", "anh_da_dang", "anh_that", "duong_anh_that", "cap_nhat",
    "ghi_ket_qua_thu",
    "doc_khuon", "duong_tep_khuon", "doc_bai_hoc_anh_bia",
]

TEN_TEP = "khuon-bia-thang.json"

#: Khung "video đủ chín để đánh giá thumbnail" — cùng khung 36-96h mà quyết
#: định 7 bản thiết kế chốt (chụp quá sớm thì CTR còn nhảy, quá muộn thì rơi
#: khỏi cả hai mốc chuẩn 48h/72h mà `ho_so_video` đã gộp sẵn).
_MOC_CHAP_NHAN = ("48h", "72h")
_MOC_GIO_THAP, _MOC_GIO_CAO = 36.0, 96.0

NGUONG_IMPRESSIONS = 1000
HE_SO_TRUNG_VI = 1.3
CONG_DIEM_PHAN_TRAM = 1.5

#: AVD video thắng thấp hơn ngần này lần so với trung vị AVD của kênh thì cờ
#: "video thắng vì HÌNH (bố cục/màu bắt mắt), không phải vì LỜI HỨA giữ được
#: người xem" — chỉ học bố cục/màu, không học "kiểu lời hứa" của tấm đó.
#: TL3-T7/0001 (vea03c3caae): AVD 20% ở mốc 48h so trung vị kênh — đo thật
#: 28/09/2026, xem `workspace/THIET-KE-DUNG-VA-VONG-HOC.md` mục 0.
NGUONG_AVD_THAP = 0.6

_RE_ID8 = re.compile(r"[^a-z0-9]+")


@dataclass
class UngVienThang:
    """Một video ĐỦ TUỔI để xét làm khuôn thắng — một điểm chụp trong 36-96h."""
    kenh: str
    ma_goi: str
    video_id: str
    tieu_de: str
    ctr: float
    impressions: float
    avd_pct: Optional[float]
    moc_gio: Optional[float]
    tep_anh_luot: str = ""  # tên tệp ảnh bìa (vd `thumb_001.png`/`CHON-thumb_002.jpg`)


# ── Đọc/ghi đĩa ──────────────────────────────────────────────────────────────


def duong_tep_khuon(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEN_TEP)


def doc_khuon(goc: str, kenh: str) -> Optional[Dict[str, Any]]:
    try:
        with io.open(duong_tep_khuon(goc, kenh), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return None
    return du if isinstance(du, dict) else None


def _ghi_khuon(goc: str, kenh: str, obj: Dict[str, Any]) -> None:
    """Ghi nguyên tử `.tmp` + `os.replace` — cùng khuôn `core/ho_so_video.py._ghi_json`."""
    duong = duong_tep_khuon(goc, kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)


# ── Ứng viên thắng ────────────────────────────────────────────────────────────


def _ung_vien_cua_kenh(goc: str, kenh: str) -> List[UngVienThang]:
    """Mọi điểm chụp trong khung 36-96h của MỌI hồ sơ video của `kenh` — đọc
    thẳng `CHANNEL/<kenh>/ho-so-video/*.json` (Việc 3), không đọc lại
    `chi_so_ytb` lần hai: hồ sơ đã gộp sẵn đúng mốc và đã có `video_id`."""
    ra: List[UngVienThang] = []
    thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
    try:
        ten_tep = sorted(t for t in os.listdir(thu_muc) if t.endswith(".json"))
    except OSError:
        return ra
    for ten in ten_tep:
        ma_goi = ten[:-len(".json")]
        ho_so = ho_so_video.doc_ho_so(goc, kenh, ma_goi)
        if not isinstance(ho_so, dict):
            continue
        video_id = ho_so.get("video_id")
        chi_so = ho_so.get("chi_so") or {}
        if not video_id or not isinstance(chi_so, dict):
            continue
        # Cả 48h và 72h đều có thể rơi trong khung — video Studio chỉ TĂNG số,
        # nên lấy bản có `moc_gio_that` LỚN NHẤT còn trong khung (chín nhất).
        ung_vien_moc = []
        for ten_moc in _MOC_CHAP_NHAN:
            m = chi_so.get(ten_moc)
            if not isinstance(m, dict):
                continue
            gio = m.get("moc_gio_that")
            if gio is None or not (_MOC_GIO_THAP <= gio < _MOC_GIO_CAO):
                continue
            if m.get("ctr") is None or m.get("impressions") is None:
                continue
            ung_vien_moc.append((gio, m))
        if not ung_vien_moc:
            continue
        gio, m = max(ung_vien_moc, key=lambda x: x[0])
        thumb = ho_so.get("thumbnail") or {}
        ra.append(UngVienThang(
            kenh=kenh, ma_goi=ma_goi, video_id=str(video_id),
            tieu_de=str(ho_so.get("tieu_de") or ""),
            ctr=float(m["ctr"]), impressions=float(m["impressions"]),
            avd_pct=m.get("avd_pct"), moc_gio=gio,
            tep_anh_luot=str(thumb.get("tep") or "") if isinstance(thumb, dict) else "",
        ))
    return ra


def _trung_vi_ctr(ds: List[UngVienThang]) -> Optional[float]:
    cac_ctr = [u.ctr for u in ds]
    return statistics.median(cac_ctr) if cac_ctr else None


def _thang_theo_nguong(ds: List[UngVienThang], nguong_median: float) -> Optional[UngVienThang]:
    """Ứng viên CTR cao nhất trong `ds` thoả cả hai luật thắng — `None` nếu
    không ai đạt. Trần imp là luật LOẠI (chụp quá sớm/ít hiển thị thì CTR chưa
    ổn định), không phải một phần của công thức trung vị."""
    dat = [u for u in ds if u.impressions >= NGUONG_IMPRESSIONS
          and u.ctr >= max(HE_SO_TRUNG_VI * nguong_median, nguong_median + CONG_DIEM_PHAN_TRAM)]
    if not dat:
        return None
    return max(dat, key=lambda u: u.ctr)


def tim_video_thang(goc: str, kenh: str,
                    cho_phep_muon_nhom: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    """Video đang THẮNG của `kenh` — của chính kênh nếu đủ mẫu & đủ CTR.

    `cho_phep_muon_nhom` (mặc định `None`) — khi kênh KHÔNG có đủ mẫu riêng
    (hoặc mẫu riêng không ai đạt ngưỡng ngay cả sau khi nới bằng trung vị
    NHÓM), có được phép MƯỢN video của kênh khác cùng nhóm
    (`core.nhom_kenh.thanh_vien`) hay không:

    - `None` (mọi lời gọi cũ không truyền gì) — tự đọc cờ `bia_khuon_nhom`
      của chính `kenh` từ `kenh.yaml` (`core.kenh.doc_kenh`), mặc định `False`.
    - `True`/`False` tường minh — làm chủ hẳn, không đọc cấu hình.

    MẶC ĐỊNH TẮT từ 30/09/2026 (Việc 4b) — mỗi kênh có tệp khán giả riêng,
    khuôn thắng của kênh khác trong nhóm không chắc đúng gu khán giả kênh
    này. Tắt thì kênh chưa đủ mẫu riêng coi như CHƯA CÓ khuôn (trả `None`),
    KHÔNG suy diễn từ trung vị nhóm lẫn không mượn video của kênh khác.

    Ngưỡng theo quyết định 7 bản thiết kế: impressions ≥ 1.000, mốc 36-96h giờ,
    CTR ≥ max(1,3×trung vị, trung vị+1,5 điểm %). Trung vị dùng để so là trung
    vị CỦA CHÍNH KÊNH khi kênh có ≥3 điểm chụp đủ tuổi; ít hơn thì (chỉ khi
    `cho_phep_muon_nhom=True`) dùng trung vị GỘP CẢ NHÓM (mẫu của một kênh còn
    quá ít để tự làm chuẩn cho chính nó).

    Trả `None` khi không ai đạt ngưỡng (chưa có gì để làm khuôn) — KHÔNG suy
    diễn từ một video chưa đủ số.
    """
    if cho_phep_muon_nhom is None:
        try:
            from . import kenh as _kenh_mod  # noqa: PLC0415
            cho_phep_muon_nhom = bool(getattr(_kenh_mod.doc_kenh(goc, kenh), "bia_khuon_nhom", False))
        except Exception:  # noqa: BLE001 — đọc cấu hình hỏng thì mặc định KHÔNG mượn
            cho_phep_muon_nhom = False

    rieng = _ung_vien_cua_kenh(goc, kenh)
    tv_rieng = _trung_vi_ctr(rieng)
    du_mau_rieng = len(rieng) >= 3

    if du_mau_rieng and tv_rieng is not None:
        thang = _thang_theo_nguong(rieng, tv_rieng)
        if thang is not None:
            return _ket_qua(thang, nguon="kenh", nguong_median=tv_rieng, so_mau=len(rieng))

    # 30/09/2026 — kênh CHƯA đủ 3 mẫu chín nhưng có một video mà BẰNG CHỨNG TUYỆT
    # ĐỐI đã đủ (ngưỡng khai thác `bia_theo_khuon`: CTR ≥ 7%, ≥10.000 hiển thị —
    # TL3-T7/vea03c3caae 9,73% / 19.618): đó là khuôn CỦA CHÍNH KÊNH, không cần
    # trung vị. Trước đây nhánh này rơi vào `return None` khi tắt mượn nhóm, nên
    # khuôn TL3 không bao giờ được làm mới (và không bao giờ tả lại từ ảnh thật).
    if not du_mau_rieng and rieng:
        try:
            from . import bia_theo_khuon as _btk  # noqa: PLC0415
            ch = _btk.cau_hinh_kenh(goc, kenh)
            ctr_min, imp_min = float(ch["bia_khai_thac_ctr_min"]), float(ch["bia_khai_thac_imp_min"])
        except Exception:  # noqa: BLE001
            ctr_min, imp_min = 7.0, 10000.0
        du_bang_chung = [u for u in rieng if u.ctr >= ctr_min and u.impressions >= imp_min]
        if du_bang_chung:
            thang = max(du_bang_chung, key=lambda u: u.ctr)
            return _ket_qua(thang, nguon="kenh", nguong_median=ctr_min, so_mau=len(rieng))

    if not cho_phep_muon_nhom:
        # Chưa đủ mẫu riêng (hoặc mẫu riêng không ai đạt ngưỡng) và kênh KHÔNG
        # bật mượn nhóm — coi như chưa có khuôn, không cần đọc `thanh_vien`
        # hay tính trung vị nhóm (sẽ không dùng tới, đỡ đọc đĩa thừa).
        return None

    try:
        from . import nhom_kenh  # noqa: PLC0415 — tránh vòng nhập lúc nạp module
        thanh_vien = nhom_kenh.thanh_vien(goc, kenh) or [kenh]
    except Exception:  # noqa: BLE001 — kênh đứng một mình khi không đọc được nhóm
        thanh_vien = [kenh]

    theo_nhom: Dict[str, List[UngVienThang]] = {}
    ca_nhom: List[UngVienThang] = []
    for k in thanh_vien:
        ds = rieng if k == kenh else _ung_vien_cua_kenh(goc, k)
        theo_nhom[k] = ds
        ca_nhom.extend(ds)

    tv_nhom = _trung_vi_ctr(ca_nhom)

    # Chưa đủ mẫu RIÊNG, hoặc đủ mẫu mà vẫn chưa ai đạt ngưỡng của chính kênh:
    # thử lại BẰNG TRUNG VỊ NHÓM (rộng hơn, đúng ngưỡng "chuẩn dùng chung" khi
    # một kênh còn quá ít dữ liệu để tự làm chuẩn cho mình).
    if tv_nhom is None:
        return None
    thang_rieng_theo_nhom = _thang_theo_nguong(rieng, tv_nhom)
    if thang_rieng_theo_nhom is not None:
        return _ket_qua(thang_rieng_theo_nhom, nguon="kenh", nguong_median=tv_nhom, so_mau=len(rieng))

    # Kênh này không có video nào thắng — mượn ứng viên CAO NHẤT đạt ngưỡng
    # của MỘT KÊNH KHÁC trong nhóm (không phải "video cao nhất cả nhóm" gộp
    # thô: mỗi ứng viên vẫn phải tự thắng NGƯỠNG NHÓM trước khi được mượn).
    ung_vien_khac = [u for k, ds in theo_nhom.items() if k != kenh for u in ds]
    thang_nhom = _thang_theo_nguong(ung_vien_khac, tv_nhom)
    if thang_nhom is not None:
        return _ket_qua(thang_nhom, nguon="nhom", nguong_median=tv_nhom, so_mau=len(ca_nhom))
    return None


def _ket_qua(u: UngVienThang, *, nguon: str, nguong_median: float, so_mau: int) -> Dict[str, Any]:
    return {
        "kenh_goc": u.kenh, "ma_goi": u.ma_goi, "video_id": u.video_id,
        "tieu_de": u.tieu_de, "ctr": u.ctr, "impressions": u.impressions,
        "avd_pct": u.avd_pct, "moc_gio": u.moc_gio, "tep_anh_luot": u.tep_anh_luot,
        "nguon": nguon, "trung_vi_dung": round(nguong_median, 4), "so_mau": so_mau,
    }


# ── Ảnh bìa lâu dài ───────────────────────────────────────────────────────────


def duong_anh_thang(goc: str, kenh: str, video_id: str) -> str:
    """Bản sao ảnh bìa THẮNG lâu dài — `CHANNEL/<kenh>/ho-so-video/anh/<id>.jpg`,
    tách khỏi `<ma_goi>.jpg` (ảnh ĐANG DÙNG của từng gói, `ho_so_video`) vì một
    video thắng có thể được nhiều lượt/nhiều kênh trong nhóm tham chiếu tới."""
    return os.path.join(ho_so_video.duong_thu_muc_ho_so(goc, kenh), "anh",
                        "{0}.jpg".format(video_id))


def _tai_url(url: str) -> Optional[bytes]:
    try:
        from .mang_an_toan import mo_url  # noqa: PLC0415 — cửa chung có chứng chỉ (certifi)

        with mo_url(url, cho=20) as ph:  # URL cố định https://i.ytimg.com
            if getattr(ph, "status", 200) >= 400:
                return None
            du = ph.read()
        return du if du else None
    except Exception:  # noqa: BLE001 — mạng hỏng/ảnh gỡ là chuyện thường, không phải lỗi
        return None


def anh_da_dang(goc: str, kenh: str, video_id: str, *, ma_goi: str = "",
                tieu_de: str = "", tai_anh: Optional[Callable[[str], Optional[bytes]]] = None
                ) -> str:
    """Đường dẫn ảnh bìa LÂU DÀI của `video_id` — có sẵn thì trả ngay; chưa có
    thì đi tìm theo thứ tự rẻ dần tới đắt dần:

    1. Ảnh của CHÍNH `ma_goi` trong `ho-so-video/anh/<ma_goi>.jpg` (Việc 3 đã
       lưu — không cần tải gì, chỉ CHÉP).
    2. Dò lượt trong `DONE/<kenh>/<mã>/` bằng tiêu đề (`chi_so_ytb.tim_luot_theo_tieu_de`
       kiểu chuẩn hoá của `ban_giao_dang._tim_thumb`) rồi chép từ đó.
    3. Tải trực tiếp từ YouTube: `https://i.ytimg.com/vi/<id>/maxresdefault.jpg`,
       hỏng (video riêng tư/gỡ, hoặc chưa có bản max-res) thì lùi `hqdefault.jpg`.

    Trả `""` khi không cách nào có ảnh — người gọi (`cap_nhat`) phải chịu được
    trường hợp này êm, không ném lỗi.
    """
    dich = duong_anh_thang(goc, kenh, video_id)
    if os.path.isfile(dich):
        return dich

    # 1) Ảnh của chính gói đã có trong hồ sơ (Việc 3).
    if ma_goi:
        nguon = ho_so_video.duong_anh_ho_so(goc, kenh, ma_goi)
        if os.path.isfile(nguon):
            try:
                os.makedirs(os.path.dirname(dich), exist_ok=True)
                tam = dich + ".tmp"
                with open(nguon, "rb") as f_in, open(tam, "wb") as f_out:
                    f_out.write(f_in.read())
                os.replace(tam, dich)
                return dich
            except OSError:
                pass

    tai_fn = tai_anh or _tai_url
    for ten_kich_thuoc in ("maxresdefault", "hqdefault"):
        du_lieu = tai_fn("https://i.ytimg.com/vi/{0}/{1}.jpg".format(video_id, ten_kich_thuoc))
        if du_lieu:
            try:
                os.makedirs(os.path.dirname(dich), exist_ok=True)
                tam = dich + ".tmp"
                with open(tam, "wb") as tep:
                    tep.write(du_lieu)
                os.replace(tam, dich)
                return dich
            except OSError:
                continue
    return ""


def duong_anh_that(goc: str, kenh: str, video_id: str) -> str:
    """Bìa THẬT đang hiển thị trên YouTube — `ho-so-video/anh/<id>-that.jpg`."""
    return os.path.join(ho_so_video.duong_thu_muc_ho_so(goc, kenh), "anh",
                        "{0}-that.jpg".format(video_id))


def anh_that(goc: str, kenh: str, video_id: str, *,
             tai_anh: Optional[Callable[[str], Optional[bytes]]] = None) -> str:
    """Tải LẠI bìa đang hiển thị trên YouTube (maxresdefault → hqdefault) mỗi lần
    gọi — chủ kênh có thể đổi bìa trên Studio bất cứ lúc nào. Tải hỏng thì giữ
    bản đã lưu lần trước. Trả `""` khi chưa từng có.

    ═══ VÌ SAO (30/09/2026) ═══ Bìa thắng TL3 vea03c3caae trên YouTube là tấm
    chủ kênh ĐĂNG TAY (nền tím, chữ trần đỏ/vàng) — khác hẳn tấm tool tạo lúc
    sản xuất (`<ma_goi>.jpg`, nền cam, chữ trong khối đen). Khuôn cũ tả từ tấm
    tool tạo, nên tool học đúng kiểu THUA."""
    dich = duong_anh_that(goc, kenh, video_id)
    tai_fn = tai_anh or _tai_url
    for ten_kich_thuoc in ("maxresdefault", "hqdefault"):
        du_lieu = tai_fn("https://i.ytimg.com/vi/{0}/{1}.jpg".format(video_id, ten_kich_thuoc))
        if du_lieu:
            try:
                os.makedirs(os.path.dirname(dich), exist_ok=True)
                tam = dich + ".tmp"
                with open(tam, "wb") as tep:
                    tep.write(du_lieu)
                os.replace(tam, dich)
                return dich
            except OSError:
                continue
    return dich if os.path.isfile(dich) else ""


# ── Mô tả khuôn bằng AI (nhìn ảnh) ────────────────────────────────────────────


_LOI_NHAC_DOC_BIA = """This is the CURRENT best-performing YouTube thumbnail of a channel \
(CTR {ctr:.2f}%, {impressions:.0f} impressions at ~{moc_gio:.0f}h after upload). Describe its \
LAYOUT so another artist could rebuild the same winning composition for a DIFFERENT story, \
reusing the character/scene of the new story instead of this one.

Return JSON only, six short fields (plain text, no markdown):
{{
  "bo_cuc": "framing — subject size/position in frame, camera distance, where the empty space for text sits",
  "mau_sac": "dominant palette — 2-4 colours, as names or hex if you can read them, and which one dominates",
  "anh_sang": "light source(s), direction, and which area is brightest vs darkest",
  "vi_tri_chu": "how many text blocks, where each sits (top/bottom/left/right), reading order",
  "kieu_chu": "font weight/style, stroke or shadow behind the text, any background shape behind the text",
  "diem_hut_mat": "the one element the eye is pulled to first, and why it works"
}}"""


def _tao_khuon_chu(goi_chat: Callable[..., str], duong_anh: str, *, ctr: float,
                   impressions: float, moc_gio: float) -> Dict[str, Any]:
    """Khuôn CÓ CẤU TRÚC (30/09/2026, `bia_theo_khuon.LOI_NHAC_DOC_BIA_CAU_TRUC`,
    cùng tên trường với nghiên cứu `workspace/nghien-cuu-bia/`) + lượt SOI màu
    từng ký tự của mỗi tầng chữ. Vẫn giữ 6 trường văn xuôi cũ."""
    from .goi_van_ban import loc_json  # noqa: PLC0415
    from .cham_anh import data_url  # noqa: PLC0415
    from . import bia_theo_khuon as _btk  # noqa: PLC0415

    loi_nhac = _btk.LOI_NHAC_DOC_BIA_CAU_TRUC.format(ctr=ctr, impressions=impressions,
                                                     moc_gio=moc_gio or 0.0)
    tra_loi = goi_chat(loi_nhac, toi_da_token=2500, anh=data_url(duong_anh))
    kc = _btk.chuan_hoa_khuon_chu(loc_json(str(tra_loi or "")))
    if not kc:
        return {}
    if (kc.get("chu") or {}).get("tang"):
        try:
            kc = _btk.soi_mau_tang(goi_chat, duong_anh, kc, os.path.dirname(duong_anh))
        except Exception:  # noqa: BLE001 — lượt soi hỏng thì giữ bản tả tổng thể
            pass
    return kc


def cap_nhat(goc: str, kenh: str, goi_chat: Optional[Callable[..., str]], *,
            bay_gio: Optional[_dt.datetime] = None,
            tai_anh: Optional[Callable[[str], Optional[bytes]]] = None) -> Optional[Dict[str, Any]]:
    """Cập nhật khuôn ảnh bìa thắng của `kenh` — gọi mỗi lượt từ `core.vong_hoc`.

    Người thắng KHÔNG đổi (đúng video_id đã lưu trước) thì chỉ cập nhật số đo
    mới nhất (CTR/imp có thể đã tăng), KHÔNG gọi AI lần nữa. Người thắng vừa
    đổi (video mới, hoặc lần đầu có người thắng) mới tốn một lượt nhìn ảnh —
    và chỉ khi có `goi_chat` (Việc 3 gọi `truoc_luot` với `goi_chat=None` thì
    coi như "chưa dựng khuôn chữ", nhưng vẫn ghi lại video thắng).

    Trả `None` khi chưa ai thắng (chưa đủ số liệu) — không ghi gì, không xoá
    khuôn cũ nếu đã có (một lượt chưa đủ số liệu không có nghĩa khuôn cũ sai).
    """
    thang = tim_video_thang(goc, kenh)
    if thang is None:
        return None

    cu = doc_khuon(goc, kenh) or {}
    video_id_cu = cu.get("video_id")

    # 30/09/2026 — khuôn cũ đã ĐỦ BẰNG CHỨNG (≥ imp khai thác) thì chỉ nhường chỗ
    # cho video cũng đủ hiển thị: một video 2.000 hiển thị CTR cao không được hất
    # khuôn 19.618 hiển thị (CTR hiển thị ít còn nhảy).
    try:
        from . import bia_theo_khuon as _btk  # noqa: PLC0415
        imp_min = float(_btk.cau_hinh_kenh(goc, kenh)["bia_khai_thac_imp_min"])
    except Exception:  # noqa: BLE001
        imp_min = 10000.0
    if (video_id_cu and video_id_cu != thang["video_id"] and not cu.get("het_hieu_luc")
            and cu.get("nguon") in (None, "", "kenh") and float(cu.get("imp") or 0) >= imp_min
            and float(thang.get("impressions") or 0) < imp_min):
        thang = dict(thang, video_id=video_id_cu, ma_goi=cu.get("ma_goi", ""),
                     tieu_de=cu.get("tieu_de", ""), ctr=cu.get("ctr"), impressions=cu.get("imp"),
                     avd_pct=cu.get("avd_pct"), moc_gio=cu.get("moc_gio"), nguon="kenh",
                     kenh_goc=cu.get("kenh_goc", kenh))
    nguoi_thang_doi = video_id_cu != thang["video_id"]

    # ═══ ẢNH THẬT TRÊN YOUTUBE (30/09/2026) ═══ Tải lại MỖI lượt cập nhật (chủ
    # kênh có thể đổi bìa trên Studio). Chỉ khi YouTube không trả ảnh nào mới
    # lùi về đường cũ (`anh_da_dang`: có thể là tấm TOOL tạo) — và khi đó khuôn
    # đánh `anh_that: false`, KHÔNG được dùng để khai thác.
    duong_that = anh_that(goc, kenh, thang["video_id"], tai_anh=tai_anh)
    duong_anh = duong_that or anh_da_dang(goc, kenh, thang["video_id"],
                                          ma_goi=thang["ma_goi"] if thang["nguon"] == "kenh" else "",
                                          tieu_de=thang.get("tieu_de", ""), tai_anh=tai_anh)
    sha1_moi = _sha1_tep(duong_anh) if duong_anh else ""
    bia_doi = bool(duong_that) and sha1_moi != cu.get("sha1_that")

    khuon_chu = cu.get("khuon_chu") if isinstance(cu.get("khuon_chu"), dict) else {}
    # Khuôn cũ tả từ ảnh TOOL (chưa có `anh_that`) hoặc bìa thật vừa đổi → tả lại.
    phai_ta_lai = nguoi_thang_doi or not khuon_chu or (bool(duong_that) and (
        not cu.get("anh_that") or bia_doi))
    if phai_ta_lai and goi_chat is not None and duong_anh:
        try:
            khuon_moi = _tao_khuon_chu(goi_chat, duong_anh, ctr=thang["ctr"],
                                       impressions=thang["impressions"],
                                       moc_gio=thang.get("moc_gio") or 0.0)
            if khuon_moi:
                khuon_chu = khuon_moi
        except Exception:  # noqa: BLE001 — mô tả hỏng thì giữ khuôn cũ (nếu có), không chặn
            pass

    # ═══ CỜ AVD THẤP — quyết định "chỉ học bố cục/màu" ═══
    #
    # Một video có thể THẮNG vì ảnh bìa/tiêu đề hứa hẹn quá đà (CTR cao) nhưng
    # AVD (giữ chân) thấp hơn hẳn mặt bằng kênh — nghĩa là người xem bấm vào
    # rồi bỏ đi ngay, tức LỜI HỨA trên bìa không khớp nội dung. Vẫn đáng học
    # BỐ CỤC/MÀU (thứ kéo được cú bấm), nhưng KHÔNG học kiểu "lời hứa" của nó.
    chi_hoc_bo_cuc = False
    avd_trung_vi_kenh = None
    if thang.get("avd_pct") is not None:
        rieng = _ung_vien_cua_kenh(goc, kenh)
        cac_avd = [u.avd_pct for u in rieng if u.avd_pct is not None]
        if len(cac_avd) >= 2:
            avd_trung_vi_kenh = statistics.median(cac_avd)
            if avd_trung_vi_kenh and thang["avd_pct"] < NGUONG_AVD_THAP * avd_trung_vi_kenh:
                chi_hoc_bo_cuc = True

    hom_nay = (bay_gio or _dt.datetime.now()).replace(microsecond=0).isoformat()
    lich_su = list(cu.get("lich_su") or [])
    if nguoi_thang_doi or not lich_su:
        lich_su.append({"video_id": thang["video_id"], "ctr": thang["ctr"],
                        "impressions": thang["impressions"], "nguon": thang["nguon"],
                        "tu_ngay": hom_nay})

    moi = {
        "video_id": thang["video_id"], "kenh_goc": thang["kenh_goc"],
        "ma_goi": thang["ma_goi"], "tieu_de": thang.get("tieu_de", ""),
        "ctr": thang["ctr"], "imp": thang["impressions"],
        "moc_gio": thang.get("moc_gio"), "avd_pct": thang.get("avd_pct"),
        "avd_trung_vi_kenh": avd_trung_vi_kenh, "chi_hoc_bo_cuc": chi_hoc_bo_cuc,
        "nguon": thang["nguon"], "tep": duong_anh,
        "sha1": sha1_moi,
        "khuon_chu": khuon_chu, "ngay_so_lieu": hom_nay, "lich_su": lich_su,
    }
    # ═══ BÌA THẬT, VÒNG THỬ, VÒNG HỌC (30/09/2026, `core/bia_theo_khuon.py`) ═══
    ta_tu_anh_that = bool(duong_that) and (phai_ta_lai and goi_chat is not None or cu.get("anh_that"))
    moi["anh_that"] = bool(ta_tu_anh_that and khuon_chu)
    moi["sha1_that"] = sha1_moi if duong_that else cu.get("sha1_that", "")
    tep_tool = ho_so_video.duong_anh_ho_so(goc, kenh, thang["ma_goi"]) if thang.get("ma_goi") else ""
    try:
        from . import bia_theo_khuon as _btk  # noqa: PLC0415
        chenh = _btk.khac_bia_tool(duong_anh, tep_tool) if (duong_that and tep_tool) else None
    except Exception:  # noqa: BLE001
        chenh = None
    moi["bia_doi_tay"] = bool(chenh is not None and chenh > 22.0)
    if chenh is not None:
        moi["chenh_bia_tool"] = round(chenh, 1)
    # Vòng thử: khuôn MỚI (người thắng đổi / bìa thật đổi) phải qua vòng tạo thử
    # trước khi khai thác; khuôn cũ giữ kết quả thử của nó.
    thu_cu = cu.get("thu") if isinstance(cu.get("thu"), dict) else {}
    moi["thu"] = ({"trang_thai": "cho_thu", "so_lan": 0} if (nguoi_thang_doi or bia_doi and cu.get("anh_that"))
                  else (thu_cu or {"trang_thai": "cho_thu", "so_lan": 0}))
    hoc_cu = cu.get("hoc") if (isinstance(cu.get("hoc"), dict) and not nguoi_thang_doi) else {}
    moi["hoc"] = hoc_cu
    try:
        from . import bia_theo_khuon as _btk  # noqa: PLC0415
        moi["hoc"] = _btk.hoc_sau_video(goc, kenh, moi,
                                        anh_that_cua=lambda vid: anh_that(goc, kenh, vid, tai_anh=tai_anh))
    except Exception:  # noqa: BLE001 — vòng học hỏng không chặn cập nhật khuôn
        pass
    _ghi_khuon(goc, kenh, moi)

    if nguoi_thang_doi:
        try:
            from . import bai_hoc_san_xuat  # noqa: PLC0415 — tránh vòng nhập
            _them_dong_bai_hoc_md(goc, kenh, moi)
        except Exception:  # noqa: BLE001 — dòng markdown chỉ là tiện đọc, không chặn
            pass
    return moi


def ghi_ket_qua_thu(goc: str, kenh: str, *, dat: bool, chi_tiet: Dict[str, Any]) -> None:
    """Ghi kết quả VÒNG TẠO THỬ khuôn (`auto_khau._thu_khuon_nho`) vào khuôn."""
    khuon = doc_khuon(goc, kenh)
    if not khuon:
        return
    thu = dict(khuon.get("thu") or {})
    thu.update(trang_thai="dat" if dat else "khong_dat", so_lan=int(thu.get("so_lan") or 0) + 1,
               luc=_dt.datetime.now().replace(microsecond=0).isoformat(), chi_tiet=chi_tiet)
    khuon["thu"] = thu
    _ghi_khuon(goc, kenh, khuon)


def _sha1_tep(duong: str) -> str:
    try:
        with open(duong, "rb") as tep:
            return hashlib.sha1(tep.read()).hexdigest()  # noqa: S324 — chỉ để phát hiện đổi tệp, không mật mã
    except OSError:
        return ""


def _them_dong_bai_hoc_md(goc: str, kenh: str, khuon: Dict[str, Any]) -> None:
    """Thêm một dòng vào `BAI-HOC-SAN-XUAT.md` khi người thắng vừa đổi — cùng
    thư mục `nghien-cuu/` với chính `khuon-bia-thang.json`, KHÔNG đụng nội
    dung do `bai_hoc_san_xuat.xuat_markdown` tự viết (chỉ nối thêm)."""
    duong = os.path.join(thu_muc_nghien_cuu(goc, kenh), "BAI-HOC-SAN-XUAT.md")
    dong = ("\n- **Khuôn ảnh bìa thắng đổi** ({ngay}): `{video_id}` (nguồn {nguon}), "
           "CTR {ctr:.2f}% / {imp:.0f} lượt hiển thị @{gio:.0f}h.{co}\n").format(
        ngay=khuon.get("ngay_so_lieu", "")[:10], video_id=khuon.get("video_id", ""),
        nguon=khuon.get("nguon", ""), ctr=khuon.get("ctr") or 0.0,
        imp=khuon.get("imp") or 0.0, gio=khuon.get("moc_gio") or 0.0,
        co=(" AVD thấp hơn hẳn trung vị kênh — chỉ học bố cục/màu, không học lời hứa."
            if khuon.get("chi_hoc_bo_cuc") else ""))
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(duong, "a", encoding="utf-8") as tep:
            tep.write(dong)
    except OSError:
        pass


# ── Câu chèn vào lời nhắc sinh ảnh bìa (`auto_khau._loi_nhac_bia`) ────────────


#: Câu chèn thay khối khuôn chữ khi kênh CHƯA có khuôn thắng hợp lệ (chưa có
#: khuôn nào, hoặc khuôn cũ đã bị đánh dấu `het_hieu_luc` — xem Việc 4b
#: 30/09/2026, migrate khuôn mượn nhóm của TL1-T7/TL2-T7).
_CAU_CHUA_CO_KHUON = "(kênh chưa có dữ liệu thumbnail riêng — đang thử nghiệm nhiều kiểu)"


def doc_bai_hoc_anh_bia(goc: str, kenh: str) -> str:
    """Khối văn bản chèn vào `<<BAI_HOC_ANH_BIA>>` của `prompt/8-thumbnail.md` —
    khuôn chữ + số đo của ảnh bìa đang thắng. KHÔNG còn trả rỗng: chưa có khuôn
    nào (kênh mới, bước 4 chưa từng chạy với `goi_chat` thật), hoặc khuôn hiện
    có đã bị đánh dấu `het_hieu_luc` (chính sách mượn nhóm đổi 30/09/2026) —
    trả câu placeholder `_CAU_CHUA_CO_KHUON` để lời nhắc luôn có một câu."""
    khuon = doc_khuon(goc, kenh)
    if not khuon or not khuon.get("khuon_chu") or khuon.get("het_hieu_luc"):
        return _CAU_CHUA_CO_KHUON
    kc = khuon["khuon_chu"]
    dong = ["## WINNING THUMBNAIL TEMPLATE (measured, real CTR {0:.2f}% / {1:.0f} impressions, "
           "data from {2})".format(khuon.get("ctr") or 0.0, khuon.get("imp") or 0.0,
                                    str(khuon.get("ngay_so_lieu") or "")[:10])]
    nhan = {"bo_cuc": "Composition", "mau_sac": "Palette", "anh_sang": "Lighting",
           "vi_tri_chu": "Text placement", "kieu_chu": "Text style", "diem_hut_mat": "Focal point"}
    for khoa, ten in nhan.items():
        if kc.get(khoa):
            dong.append("- {0}: {1}".format(ten, kc[khoa]))
    if khuon.get("chi_hoc_bo_cuc"):
        dong.append("Note: this video's high CTR came with LOW audience retention — copy its "
                    "LAYOUT/COLOUR only, do not copy any implied promise/claim from it.")
    dong.append("For the `khuon_thang` concept, rebuild this template with the CURRENT story's "
               "character/scene and the exact hook text given above.")
    return "\n".join(dong) + "\n"
