"""Lọc VIDEO RÁC ra khỏi số liệu kênh — một mốc ngày, dùng chung cho mọi nơi đọc `chi-so/`.

═══ VÌ SAO CẦN CÁI NÀY ═══

Bốn kênh đang chạy đều là kênh YouTube **có sẵn**, đổi sang làm tâm lý Nhật. Trên
kênh còn nguyên video của đời trước, và extension cào Studio thì cào TẤT CẢ — nó
không biết video nào do tool này làm.

Bằng chứng đo trên `CHANNEL/TL4-T7/chi-so/` (22/09/2026):

    v47c6f05e48  "Mô hình đồ chơi cũ số 1"      đăng 2018-12-09
    v8754af58fc  "Mở hộp đồ chơi cũ số 5"         đăng 2018-12-27
                 → 35.701 lượt hiển thị, CTR 7,97%
    vba4ef7584a  video TÂM LÝ đầu tiên của kênh            đăng 2026-08-22

Hai video đồ chơi ấy nằm CHUNG `bang-tom-tat.csv` với video tâm lý. Hậu quả không
phải "bảng hơi bẩn" — nó sai tới tận vòng học:

* `cong_thuc_v7.video_cua_kenh()` đọc mọi thư mục trong `chi-so/` rồi
  `_danh_dau_thang` chấm THẮNG theo hiển thị mốc 48h. 35.701 hiển thị của video
  đồ chơi vượt xa ngưỡng, nên nó thành "video thắng" của kênh tâm lý.
* `thanh_tich_cum` nhân điểm cụm chủ đề theo thành tích thật → cụm rút từ tiêu đề
  đồ chơi được cộng điểm.
* `auto_khau.tieu_de_thang_cua_kenh()` lấy tiêu đề "đang thắng" làm MẪU nắn tiêu
  đề mới → tiêu đề video tâm lý bị nắn theo khuôn tiêu đề mở hộp đồ chơi.
* `da_co_video_thang()` là cổng chuyển kênh sang chấm bằng Công thức V7 — video
  2018 bật cổng ấy sớm hơn sự thật.

Ba kênh mới còn nặng hơn: `CHANNEL/TL1-T7/chi-so/` (cào lần đầu 22/09/2026) có 22
video đăng 2026-06-20 → 07-21 — video tâm lý của một KHUÔN KHÁC, không phải tool
này làm. Chủ dự án nói thẳng: *"số liệu 3 kênh mới không dùng được đâu — chỉ dùng
được số liệu TL4-T7 thôi"*. TL2/TL3-T7 chưa cào nhưng cùng tình trạng.

═══ CÁCH CHẶN: MỘT KHOÁ, MỘT HÀM ═══

`kenh.yaml` có khoá `ngay_bat_dau: "YYYY-MM-DD"` — ngày kênh bắt đầu làm nội dung
của tool này. Video đăng TRƯỚC ngày đó không được tính vào số liệu và vòng học.

Khoá RỖNG nghĩa là không lọc gì: bản gửi khách và mọi khuôn cũ giữ y hành vi cũ.

Video **không có ngày đăng** (thư mục `chi-so/<id>` chỉ có gói raw chưa giải mã)
thì coi là NGOÀI phạm vi khi kênh đã khai mốc — lọt rác vào vòng học tệ hơn là
thiếu một dòng, và số liệu ấy quay lại ngay lần giải mã sau. Mỗi ca như vậy ghi
một dòng vào `chi-so/_ngoai-pham-vi.log` để không mất dấu.

Không xoá gì: gói raw vẫn nằm nguyên trong `chi-so/<id>/` — đây là kho bằng chứng,
chỉ là nó không lên bảng và không vào bộ chấm.

Mô-đun thuần tuý: không mạng, không Qt, chỉ đọc tệp.
"""

from __future__ import annotations

import datetime as _dt
import io
import os
import re
from typing import Any, Callable, Iterable, List, Optional, Sequence, TypeVar

__all__ = [
    "KHOA_MOC", "TEN_TEP_NHAT_KY", "chuan_ngay", "moc_cua_thu_muc",
    "moc_cua_kenh", "trong_pham_vi", "loc_theo_ngay", "ghi_nhat_ky",
]

#: Tên khoá trong `kenh.yaml`. Một chỗ khai để `core/kenh.py`, giao diện và bộ lọc
#: không bao giờ gọi nó bằng hai tên khác nhau.
KHOA_MOC = "ngay_bat_dau"

#: Nhật ký video bị bỏ vì thiếu ngày đăng — nằm ngay trong `chi-so/` của kênh, cạnh
#: dữ liệu nó nói về. Không đẩy vào nhật ký chung của tool: đây là chuyện của MỘT
#: kênh, và người mở thư mục số liệu là người cần đọc nó.
TEN_TEP_NHAT_KY = "_ngoai-pham-vi.log"

_NGAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
#: Bản thử `<kênh>-v2` / `<kênh>-v3`: không có `chi-so/` riêng, nó đăng lên cùng một
#: kênh YouTube với kênh gốc. Cùng quy ước với `core/da_lam.doc_ma_da_lam` và
#: `auto_khau.tieu_de_thang_cua_kenh`.
_DUOI_BAN_THU = re.compile(r"[-_]v\d+$", re.IGNORECASE)

T = TypeVar("T")


def chuan_ngay(gia_tri: Any) -> str:
    """Bất cứ thứ gì mang ngày → `"YYYY-MM-DD"`; không đọc được → `""`.

    Ba dạng thật đang có trên đĩa, phải nhận cả ba:

    * `"2018-12-27T05:18:06.000Z"` — `_thong-tin.json` / `tong-quan.json` của
      extension (ISO đầy đủ, có múi giờ Z).
    * `"2026-09-16"` — cột "Ngày đăng" của `bang-tom-tat.csv`.
    * `datetime.date(2026, 8, 22)` — PyYAML tự đổi `ngay_bat_dau: 2026-08-22`
      KHÔNG bọc nháy thành đối tượng ngày. Quên ca này thì một lần sửa tay
      `kenh.yaml` là mốc biến thành `"2026-08-22 00:00:00"` và so chuỗi sai.

    Chỉ lấy phần NGÀY: giờ đăng không giúp gì cho câu hỏi "video này thuộc đời
    nào của kênh", mà lại kéo theo chuyện múi giờ.
    """
    if gia_tri is None:
        return ""
    if isinstance(gia_tri, (_dt.datetime, _dt.date)):
        return gia_tri.strftime("%Y-%m-%d")
    m = _NGAY.match(str(gia_tri).strip())
    if not m:
        return ""
    try:  # chặn "2026-13-45": đúng khuôn chữ nhưng không phải ngày
        _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return ""
    return m.group(0)


def moc_cua_thu_muc(thu_muc_kenh: str) -> str:
    """Mốc `ngay_bat_dau` của kênh có thư mục này — `""` nếu kênh không khai.

    Nhận THƯ MỤC KÊNH chứ không nhận `(goc, mã)`: hai bộ gọi dùng hai nghĩa khác
    nhau cho chữ "gốc" (`cong_thuc_v7` đưa gốc TOOL rồi tự `duong_kenh()`, còn
    `chi_so_ytb` đưa thẳng thư mục CHỨA các kênh). Nhận thư mục kênh thì không ai
    đoán sai được.

    Kênh bản thử `<kênh>-v2` không khai mốc thì lùi về `kenh.yaml` của kênh gốc:
    hai bản đăng lên cùng một kênh YouTube nên cùng một ngày bắt đầu, và bản thử
    vốn đọc `chi-so/` của kênh gốc.
    """
    thu_muc_kenh = str(thu_muc_kenh or "")
    if not thu_muc_kenh:
        return ""
    from ..kenh import TEP_KENH, doc_yaml  # noqa: PLC0415 — tránh vòng nhập lúc nạp mô-đun

    moc = chuan_ngay((doc_yaml(os.path.join(thu_muc_kenh, TEP_KENH)) or {}).get(KHOA_MOC))
    if moc:
        return moc
    ten = os.path.basename(os.path.normpath(thu_muc_kenh))
    ten_goc = _DUOI_BAN_THU.sub("", ten)
    if ten_goc and ten_goc != ten:
        cha = os.path.dirname(os.path.normpath(thu_muc_kenh))
        return chuan_ngay((doc_yaml(os.path.join(cha, ten_goc, TEP_KENH)) or {}).get(KHOA_MOC))
    return ""


def moc_cua_kenh(goc_chua_kenh: str, ma_kenh: str) -> str:
    """Như `moc_cua_thu_muc` nhưng nhận `(thư mục CHỨA các kênh, mã kênh)` —
    đúng cặp tham số mà `core/chi_so_ytb` vẫn dùng."""
    if not goc_chua_kenh or not ma_kenh:
        return ""
    return moc_cua_thu_muc(os.path.join(goc_chua_kenh, ma_kenh))


def trong_pham_vi(moc: str, ngay_dang: Any, *,
                  ghi: Optional[Callable[[str], None]] = None,
                  nhan: str = "") -> bool:
    """Video đăng `ngay_dang` có được tính vào số liệu của kênh khai mốc `moc` không.

    `moc` rỗng → luôn `True` (kênh chưa khai mốc thì hành vi y như trước khoá này
    ra đời — bản gửi khách không đổi một dòng số nào).

    `ngay_dang` rỗng/không đọc được mà `moc` CÓ → `False`, và gọi `ghi` một dòng.
    Chọn phía an toàn: video chưa giải mã xong thì thiếu một dòng bảng, lần đọc sau
    có ngày là nó tự quay lại; còn cho lọt thì video 2018 đi thẳng vào bộ chấm.
    """
    moc = chuan_ngay(moc)
    if not moc:
        return True
    ngay = chuan_ngay(ngay_dang)
    if not ngay:
        if ghi is not None:
            ghi("bỏ {0}: chưa biết ngày đăng (mốc kênh {1})".format(nhan or "?", moc))
        return False
    return ngay >= moc


def loc_theo_ngay(moc: str, danh_sach: Iterable[T],
                  ngay_cua: Callable[[T], Any], *,
                  nhan_cua: Optional[Callable[[T], str]] = None,
                  ghi: Optional[Callable[[str], None]] = None) -> List[T]:
    """Giữ lại những mục trong phạm vi. `moc` rỗng → trả về nguyên danh sách."""
    if not chuan_ngay(moc):
        return list(danh_sach)
    return [m for m in danh_sach
            if trong_pham_vi(moc, ngay_cua(m), ghi=ghi,
                             nhan=(nhan_cua(m) if nhan_cua else ""))]


def ghi_nhat_ky(thu_muc_chi_so: str, dong: str) -> None:
    """Nối một dòng vào `chi-so/_ngoai-pham-vi.log`, KHÔNG lặp lại dòng đã có.

    Bộ đọc số liệu chạy mỗi lượt tự chạy (nhiều lần một ngày, nhiều bộ gọi cùng
    đọc một kênh). Nối mù thì một video thiếu ngày đẻ ra hàng nghìn dòng giống
    nhau trong vài tuần và nhật ký thành thứ không ai mở. Dòng đã có thì im.

    Ghi hỏng (đĩa đầy, thư mục chỉ-đọc) thì bỏ qua: nhật ký không bao giờ được
    làm vỡ lượt đọc số liệu.
    """
    if not thu_muc_chi_so or not dong:
        return
    duong = os.path.join(thu_muc_chi_so, TEN_TEP_NHAT_KY)
    try:
        if os.path.isfile(duong):
            with io.open(duong, encoding="utf-8") as tep:
                cu = tep.read()
            if dong in cu:
                return
            if len(cu) > 200_000:  # tự cắt: nhật ký không phình thành vấn đề mới
                with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
                    tep.write(cu[-100_000:])
        with io.open(duong, "a", encoding="utf-8", newline="\n") as tep:
            tep.write("{0} {1}\n".format(
                _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), dong))
    except OSError:
        pass


def but_nhat_ky(thu_muc_chi_so: str) -> Callable[[str], None]:
    """Cây bút `ghi` để truyền vào `trong_pham_vi`/`loc_theo_ngay`."""
    return lambda dong: ghi_nhat_ky(thu_muc_chi_so, dong)


def ngay_dang_cua_video(thu_muc_video: str) -> str:
    """Ngày đăng đọc từ dữ liệu THÔ của một video: `chi-so/<id>/<mốc>/…`.

    Tìm ở hai tệp, theo thứ tự:

    * `_thong-tin.json` — extension ghi riêng (tiêu đề, độ dài, `ngay_dang`), vì
      không gói nào của Studio mang mấy thứ ấy.
    * `tong-quan.json` — bản đã giải mã, `_gan_thong_tin()` đã chép `ngay_dang`
      sang. Có ca chỉ còn tệp này (bản giải mã cũ, `_thong-tin.json` đã dọn).

    Tên khoá `ngay_dang` xác nhận trên tệp thật của TL4-T7 (`v8754af58fc/67424h/`
    → `"ngay_dang": "2018-12-27T05:18:06.000Z"`). Không thấy ở mốc nào → `""`.
    """
    import json  # noqa: PLC0415

    if not thu_muc_video or not os.path.isdir(thu_muc_video):
        return ""
    try:
        cac_moc = sorted(os.listdir(thu_muc_video))
    except OSError:
        return ""
    for con in cac_moc:
        d = os.path.join(thu_muc_video, con)
        if not os.path.isdir(d):
            continue
        for ten in ("_thong-tin.json", "tong-quan.json"):
            try:
                with io.open(os.path.join(d, ten), encoding="utf-8") as tep:
                    ngay = chuan_ngay((json.load(tep) or {}).get("ngay_dang"))
            except (OSError, ValueError, AttributeError):
                continue
            if ngay:
                return ngay
    return ""


def loc_hang_bang(moc: str, hang: Sequence[dict],
                  cot: str = "Ngày đăng") -> List[dict]:
    """Lọc các dòng đọc từ `bang-tom-tat.csv` / `bang-nhom.csv` theo cột ngày đăng.

    Có cả bộ lọc phía CSV *và* phía bảng vì hai thứ lệch nhịp: `bang-tom-tat.csv`
    trên đĩa có thể là bản viết TRƯỚC khi kênh khai mốc (hoặc do bản tool cũ viết),
    và `nhom_kenh`/`trung_tam` đọc thẳng tệp ấy chứ không dựng lại. Lọc lại lúc đọc
    thì mốc ăn ngay, không phải chờ lượt cào sau.

    Dòng thiếu ngày đăng ở đây KHÔNG ghi nhật ký: `doc_kenh()` đã ghi khi dựng bảng,
    ghi lần nữa là hai dòng cho một chuyện.
    """
    if not chuan_ngay(moc):
        return list(hang)
    return [d for d in hang if trong_pham_vi(moc, (d or {}).get(cot))]
