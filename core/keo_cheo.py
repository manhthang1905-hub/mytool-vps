"""**Kéo view chéo** — kênh LỚN trong nhóm đưa video của kênh EM vào danh sách phát CÔNG KHAI của mình.

═══ VÌ SAO (06/10/2026) ═══

Nhóm `tam-ly-nhat` có hai kênh đã đứng được (TL4-T7 ~6.900 giờ xem/28 ngày, TL2-T7 ~1.200) và bốn
kênh mới (TL4-T7-K2, TL5-T7, TL6-T7, TL6-T7-K2) chưa ai biết tới. Video mới của kênh em chỉ có hai
nguồn hiển thị: trang chủ/đề xuất (cần thời gian YouTube "học" kênh) và tìm kiếm. Kênh lớn thì đã có
khán giả CÙNG NGÁCH đang xem mỗi ngày. YouTube cho phép mọi tài khoản đưa BẤT KỲ video công khai nào
vào danh sách phát của mình — nên kênh lớn (đăng nhập trong Chrome RIÊNG của nó) thêm một video kênh
em hợp chủ đề vào danh sách phát công khai của nó; người xem danh sách phát ấy (trang kênh, hết video
→ tự phát video kế) chảy sang kênh em, và YouTube thấy video kênh em được khán giả cùng ngách xem →
đề xuất nó cho đúng tệp người đó. Không tốn tiền, không cần kênh em làm gì.

═══ GIỚI HẠN (đều nằm trong `CAI_DAT_MAC_DINH`, đè được bằng `workspace/keo-cheo/cai-dat.json`) ═══

* Kênh lớn = giờ xem 28 ngày ≥ `nguong_gio_xem` (500 giờ) tính từ `chi-so/kenh-theo-ngay.csv` (số CỘNG
  DỒN trọn đời — hiệu hai mốc là số trong khoảng). Kênh em = mọi thành viên khác cùng `nhom`.
* Tối đa `toi_da_moi_kenh_chu` (2) lần thêm mỗi kênh lớn mỗi ngày, `toi_da_moi_ds` (1) video kênh em
  mỗi danh sách phát mỗi ngày — danh sách phát của kênh lớn vẫn phải là CỦA KÊNH LỚN; nhồi video kênh
  khác vào là làm loãng chính nguồn view đang nuôi nó, và nhịp thêm đều tay trông như người thật.
* Không bao giờ thêm cùng một video hai lần (sổ `workspace/keo-cheo/da-them.json`).
* Chỉ video đã công khai ≥ `gio_sau_dang` (24) giờ: giờ công khai lấy từ kế hoạch đăng (`ĐÃ ĐĂNG` +
  ngày/giờ), sổ máy đăng (`vm/logs/so-video-id.json`, `lich`), hoặc ngày đăng của `bang-tom-tat.csv`
  (chỉ có ngày → coi như 23:59 cho chắc). 24 giờ đầu YouTube đang thử video với khán giả của CHÍNH
  kênh em — để nó tự chạy trước, kéo chéo là cú đẩy thứ hai.
* Chọn danh sách phát theo CỤM CHỦ ĐỀ (`cong_thuc_v7.cum_cua_tieu_de` — theo nghĩa khi bộ nhớ phân
  cụm AI có, từ khoá là đường lùi) với bộ cụm CỦA KÊNH LỚN: cụm của tiêu đề video ∩ cụm của tên danh
  sách phát. Không khớp → AI chọn THEO NGHĨA (`core.giam_doc.quan_ly.goi_chat_that`, một lượt gọi mỗi
  (kênh lớn, video), nhớ trong `ai-chon.json`, tối đa `toi_da_goi_ai` lượt mỗi lần lập; AI được trả
  NONE = không hợp) → ví chặn/AI hỏng thì gần chữ (≥ 2 cặp chữ chung) → danh sách phát RIÊNG
  (`keo_cheo_danh_sach_phat` trong `kenh.yaml` kênh lớn, hoặc `ds_rieng` chung, vd "おすすめ"). Không
  có gì khớp thì KHÔNG thêm — sai chủ đề là khán giả kênh lớn bấm thoát, hại cả hai kênh.
* Kênh nào khai `keo_cheo_tat: true` trong `kenh.yaml` thì đứng ngoài cả hai vai.

═══ DANH SÁCH PHÁT TỰ TÌM (06/10/2026 — "máy mới chỉ cần Chrome đã đăng nhập") ═══

Không ai phải khai tên danh sách phát. Thứ tự nguồn của kênh lớn (`tra_ds`):
1. `danh_sach_phat_kenh` trong `kenh.yaml` (khai tay, nếu có).
2. `thiet-lap/ho-so.json` → `danh_sach_phat: [{ten, mo_ta}]` — skill thiết lập kênh đã TẠO đúng các
   danh sách này trên YouTube (kênh mới).
3. Sổ HỌC `ds-kenh.json` — tên thật đọc từ hộp «Lưu vào…» trên trang xem (kênh cũ dựng tay): máy DOM
   ghi mỗi lần nó mở hộp (`--hoc-ds`, và mọi lượt thêm thật). Cũ quá `tuoi_ds_hoc_ngay` (7) ngày, hoặc
   một danh sách đã lên kế hoạch mà không thấy trong hộp, thì kế hoạch kèm việc `hoc_ds`.
Không nguồn nào có gì → kế hoạch trả việc `hoc_ds` NÓI RÕ lệnh cần chạy, không im lặng bỏ qua.
Mỗi phần tử kế hoạch mang `viec`: `them` (thêm một video) | `hoc_ds` (mở hộp Lưu, đọc tên, không tích)
| `bao` (cần người: kênh chưa có danh sách phát công khai nào).

═══ ĐO THẾ NÀO ═══

View đến từ danh sách phát CỦA KÊNH KHÁC không tách riêng được trong số liệu của kênh em (Studio gộp
vào "Danh sách phát"/"Kênh khác"). Nên mỗi lần thêm ghi một DỰ ĐOÁN kèm mốc: lượt xem/hiển thị của
video lúc thêm (từ `bang-tom-tat.csv`) và của tối đa 5 video ĐỐI CHỨNG cùng kênh em (chưa được kéo,
đăng gần ngày). Sau `kiem_sau_ngay` (7) ngày `do_hieu_qua` đọc lại cùng bảng: video được kéo tăng
nhanh hơn trung vị đối chứng ≥ 20% → "kéo được"; không thì "chưa thấy". Đây là so sánh thô (video
khác nhau, tuổi khác nhau) — đủ để biết có nên tiếp tục/mở rộng, không đủ để kết luận từng video.

Không Chrome. Mạng duy nhất: lượt AI chọn danh sách theo nghĩa (tắt bằng `ai_chon_ds: false`). Máy DOM
thực thi từng việc: `vm/keo_cheo_dom.py`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import re
import statistics
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .kenh import TEP_KENH, doc_yaml, duong_kenh, liet_ke_kenh

__all__ = [
    "THU_MUC_TRANG_THAI", "TEP_DA_THEM", "TEP_CAI_DAT", "CAI_DAT_MAC_DINH",
    "thu_muc_mac_dinh", "doc_cai_dat", "gio_xem_trong_ky", "phan_vai_nhom",
    "danh_sach_phat_cua", "video_kenh_em", "chon_danh_sach", "doc_da_them", "ghi_ket_qua",
    "lap_ke_hoach", "du_doan_cho", "do_hieu_qua", "tim_kenh_cua_video",
    "TEP_DS_KENH", "TEP_AI_CHON", "ds_tu_ho_so", "doc_ds_kenh", "ghi_ds_kenh", "danh_dau_can_hoc",
    "tra_ds", "video_de_hoc", "gan_nhat_theo_chu", "tao_chon_ai",
]

THU_MUC_TRANG_THAI = os.path.join("workspace", "keo-cheo")
TEP_DA_THEM = "da-them.json"
TEP_CAI_DAT = "cai-dat.json"
TEP_DS_KENH = "ds-kenh.json"
TEP_AI_CHON = "ai-chon.json"

#: Danh sách hệ thống trong hộp Lưu — không phải danh sách phát công khai của kênh.
DS_HE_THONG = ("Xem sau", "Watch later", "後で見る", "나중에 볼 동영상")
#: Chữ trong hàng hộp Lưu nghĩa là danh sách RIÊNG TƯ (đời hộp mới ghi dưới tên) — thêm vào đó vô ích.
CHU_RIENG_TU = ("Riêng tư", "Private", "非公開", "비공개")

CAI_DAT_MAC_DINH: Dict[str, Any] = {
    "bat": True,
    "nguong_gio_xem": 500.0,
    "so_ngay_gio_xem": 28,
    "toi_da_moi_kenh_chu": 2,
    "toi_da_moi_ds": 1,
    "gio_sau_dang": 24,
    #: Video cũ hơn ngần này ngày thì không kéo nữa — cú đẩy có ích nhất khi video còn đang được thử.
    "tuoi_toi_da_ngay": 60,
    #: Danh sách phát RIÊNG chung cho mọi kênh lớn (vd "おすすめ") khi không khớp cụm — rỗng = tắt.
    #: `keo_cheo_danh_sach_phat` trong kenh.yaml kênh lớn đè lên khoá này.
    "ds_rieng": "",
    #: True: một video chỉ được kéo MỘT lần trên toàn nhóm (mọi kênh lớn). False: mỗi kênh lớn một lần.
    "mot_lan_moi_video": True,
    #: Một việc hỏng ngần này lần thì thôi (không thử lại mãi một video không thêm được).
    "toi_da_loi_moi_video": 3,
    "kiem_sau_ngay": 7,
    "so_doi_chung": 5,
    "nguong_hon_doi_chung": 0.2,
    #: Video ngắn hơn ngần này giây (Shorts) không kéo — danh sách phát dài, người xem đang ngồi xem.
    "do_dai_toi_thieu_giay": 181,
    #: Sổ học danh sách phát (hộp Lưu) cũ quá ngần này ngày → kế hoạch kèm việc `hoc_ds`.
    "tuoi_ds_hoc_ngay": 7,
    #: AI chọn danh sách theo NGHĨA khi cụm không khớp; mỗi lần lập kế hoạch gọi tối đa ngần này lượt.
    "ai_chon_ds": True,
    "toi_da_goi_ai": 12,
    "han_ai_giay": 60,
}

#: Trạng thái sổ máy đăng nghĩa là video đã được hẹn/xác nhận lên kênh.
_TT_SO_DA_LEN = ("xac-nhan", "da-len-lich", "lech-lich")
_KET_DA_THEM = ("ok", "da_co")


# ── tiện ích ─────────────────────────────────────────────────────────────────

def thu_muc_mac_dinh(goc: str) -> str:
    return os.path.join(goc, THU_MUC_TRANG_THAI)


def _so(chu: Any) -> Optional[float]:
    s = str(chu if chu is not None else "").strip().replace(" ", "").rstrip("%")
    if not s:
        return None
    if "," in s and "." not in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _doc_csv_dict(duong: str) -> List[Dict[str, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return [d for d in csv.DictReader(tep) if isinstance(d, dict)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=1, default=str)
    os.replace(tam, duong)


def _ngay(x: Any) -> _dt.date:
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    return _dt.date.fromisoformat(str(x)[:10])


def _doc_luc(ngay_s: Any, gio_s: Any = "") -> Optional[_dt.datetime]:
    """`dd/mm/yyyy` | `yyyy-mm-dd` (+ `HH:MM`) → datetime. Thiếu giờ → 23:59 (chắc phía muộn)."""
    ngay_s = str(ngay_s or "").strip()
    gio_s = str(gio_s or "").strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", ngay_s)
    if m:
        d, th, n = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh, mm = (m.group(4), m.group(5)) if m.group(4) else (None, None)
    else:
        m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2}))?", ngay_s)
        if not m:
            return None
        n, th, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh, mm = (m.group(4), m.group(5)) if m.group(4) else (None, None)
    if hh is None:
        mg = re.match(r"^(\d{1,2}):(\d{2})", gio_s)
        hh, mm = (mg.group(1), mg.group(2)) if mg else ("23", "59")
    try:
        return _dt.datetime(n, th, d, int(hh), int(mm))
    except ValueError:
        return None


def _giay(chu: Any) -> Optional[int]:
    """`20:33` / `1:02:03` → giây; không đọc được → None."""
    phan = str(chu or "").strip().split(":")
    if len(phan) < 2 or not all(p.isdigit() for p in phan):
        return None
    tong = 0
    for p in phan:
        tong = tong * 60 + int(p)
    return tong


def _cai_kenh(goc: str, kenh: str) -> Dict[str, Any]:
    return doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}


def doc_cai_dat(thu_muc: str, de: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mặc định ← `<thu_muc>/cai-dat.json` ← `de` (tham số nơi gọi)."""
    cai = dict(CAI_DAT_MAC_DINH)
    tep = _doc_json(os.path.join(thu_muc, TEP_CAI_DAT))
    if isinstance(tep, dict):
        cai.update({k: v for k, v in tep.items() if not str(k).startswith("_")})
    if de:
        cai.update(de)
    return cai


# ── vai: kênh lớn / kênh em ─────────────────────────────────────────────────

def gio_xem_trong_ky(goc: str, kenh: str, so_ngay: int = 28,
                     bay_gio: Optional[_dt.datetime] = None) -> Optional[float]:
    """Giờ xem của kênh trong `so_ngay` ngày tính tới mốc chụp mới nhất (≤ `bay_gio`).

    `kenh-theo-ngay.csv` là số CỘNG DỒN (xem `core/giam_doc/du_lieu.py`): lấy mốc mới nhất trừ giá trị
    nội suy ở `mốc − so_ngay`. Dữ liệu bắt đầu SAU điểm ấy thì trừ dòng đầu tiên (cận dưới — kênh có
    số trước khi tool chụp sẽ bị đếm thiếu, không bao giờ thừa). Không có tệp/số → None."""
    hang = _doc_csv_dict(os.path.join(duong_kenh(goc, kenh), "chi-so", "kenh-theo-ngay.csv"))
    ds: List[Tuple[_dt.datetime, float]] = []
    for d in hang:
        luc = _doc_luc(str(d.get("Lúc chụp") or "")[:16])
        g = _so(d.get("Giờ xem"))
        if luc is None or g is None:
            continue
        if bay_gio is not None and luc > bay_gio:
            continue
        ds.append((luc, g))
    if not ds:
        return None
    ds.sort()
    moc_cuoi, gia_cuoi = ds[-1]
    dau = moc_cuoi - _dt.timedelta(days=int(so_ngay))
    if dau <= ds[0][0]:
        return round(max(0.0, gia_cuoi - ds[0][1]) if len(ds) > 1 else gia_cuoi, 2)
    gia_dau = ds[0][1]
    for (t0, v0), (t1, v1) in zip(ds, ds[1:]):
        if t0 <= dau <= t1:
            k = (dau - t0).total_seconds() / max(1.0, (t1 - t0).total_seconds())
            gia_dau = v0 + (v1 - v0) * k
            break
    return round(max(0.0, gia_cuoi - gia_dau), 2)


def _cac_nhom(goc: str) -> Dict[str, List[str]]:
    ra: Dict[str, List[str]] = {}
    for ma in liet_ke_kenh(goc):
        cai = _cai_kenh(goc, ma)
        nhom = str(cai.get("nhom") or "").strip()
        if not nhom or _bat(cai.get("keo_cheo_tat")):
            continue
        ra.setdefault(nhom, []).append(ma)
    return ra


def _bat(x: Any) -> bool:
    return x is True or str(x or "").strip().lower() in ("true", "1", "yes", "co", "có")


def phan_vai_nhom(goc: str, thanh_vien: Sequence[str], cai: Dict[str, Any],
                  bay_gio: Optional[_dt.datetime] = None) -> Tuple[Dict[str, float], Dict[str, float]]:
    """`(kênh lớn {mã: giờ xem}, kênh em {mã: giờ xem})` — kênh chưa có số là kênh em (giờ 0)."""
    lon: Dict[str, float] = {}
    em: Dict[str, float] = {}
    for ma in thanh_vien:
        g = gio_xem_trong_ky(goc, ma, int(cai.get("so_ngay_gio_xem") or 28), bay_gio)
        if g is not None and g >= float(cai.get("nguong_gio_xem") or 0):
            lon[ma] = g
        else:
            em[ma] = g or 0.0
    return lon, em


def ds_tu_ho_so(goc: str, kenh: str) -> List[Tuple[str, str]]:
    """`[(tên, mô tả)]` từ `thiet-lap/ho-so.json` (skill thiết lập kênh đã tạo đúng các danh sách này)."""
    hs = _doc_json(os.path.join(duong_kenh(goc, kenh), "thiet-lap", "ho-so.json"))
    ra: List[Tuple[str, str]] = []
    ds = hs.get("danh_sach_phat") if isinstance(hs, dict) else None
    for d in ds if isinstance(ds, list) else []:
        if isinstance(d, dict) and str(d.get("ten") or "").strip():
            ra.append((str(d["ten"]).strip(), str(d.get("mo_ta") or "").strip()))
        elif isinstance(d, str) and d.strip():
            ra.append((d.strip(), ""))
    return ra


def doc_ds_kenh(thu_muc: str) -> Dict[str, Dict[str, Any]]:
    d = _doc_json(os.path.join(thu_muc, TEP_DS_KENH))
    return {k: v for k, v in d.items() if isinstance(v, dict)} if isinstance(d, dict) else {}


def ghi_ds_kenh(thu_muc: str, kenh: str, hang: Sequence[Any], luc: Optional[_dt.datetime] = None,
                video: str = "") -> Dict[str, Any]:
    """Ghi tên danh sách phát ĐỌC ĐƯỢC từ hộp Lưu (`hang`: [{ten, chu_hang}] hoặc [tên]) vào sổ học.

    Bỏ danh sách hệ thống (Xem sau…); hàng mang chữ "Riêng tư/非公開/Private" ghi riêng (`rieng_tu`) —
    thêm video vào danh sách riêng tư thì không ai thấy. Trả mục vừa ghi."""
    luc = luc or _dt.datetime.now()
    ten: List[str] = []
    rieng_tu: List[str] = []
    he = {_chuan(x) for x in DS_HE_THONG}
    for h in hang or []:
        t = _chuan(h.get("ten") if isinstance(h, dict) else h)
        chu = str(h.get("chu_hang") or "") if isinstance(h, dict) else ""
        if not t or t in he or t in ten or t in rieng_tu:
            continue
        phu = _chuan(chu.replace(t, "", 1)) if chu else ""
        (rieng_tu if any(w in phu for w in CHU_RIENG_TU) else ten).append(t)
    so = doc_ds_kenh(thu_muc)
    so[kenh] = {"ten": ten, "rieng_tu": rieng_tu, "luc": luc.strftime("%Y-%m-%d %H:%M:%S"),
                "video": video, "can_hoc_lai": False}
    _ghi_json(os.path.join(thu_muc, TEP_DS_KENH), so)
    return so[kenh]


def danh_dau_can_hoc(thu_muc: str, kenh: str, ly_do: str) -> None:
    """Lượt sau phải học lại danh sách của `kenh` (hộp không đọc được / danh sách đã lên kế hoạch không có)."""
    so = doc_ds_kenh(thu_muc)
    muc = so.setdefault(kenh, {"ten": [], "rieng_tu": [], "luc": ""})
    muc["can_hoc_lai"] = True
    muc["ly_do_hoc_lai"] = str(ly_do)[:200]
    _ghi_json(os.path.join(thu_muc, TEP_DS_KENH), so)


def _chuan(s: Any) -> str:
    import unicodedata  # noqa: PLC0415

    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def lenh_hoc_ds(kenh: str) -> str:
    return "python vm/keo_cheo_dom.py --hoc-ds --kenh {0}".format(kenh)


def tra_ds(goc: str, kenh: str, cai: Dict[str, Any], thu_muc: Optional[str] = None,
           bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Danh sách phát của kênh lớn: `{chu_de, rieng, mo_ta, nguon, can_hoc, ly_do_hoc}`.

    Nguồn theo thứ tự: kenh.yaml → thiet-lap/ho-so.json → sổ học `ds-kenh.json` (xem docstring đầu
    tệp). `can_hoc`: nên mở hộp Lưu đọc lại (chưa có nguồn, sổ học cũ quá `tuoi_ds_hoc_ngay`, hoặc bị
    đánh dấu học lại) — danh sách cũ vẫn dùng được trong lúc chờ."""
    bay_gio = bay_gio or _dt.datetime.now()
    ck = _cai_kenh(goc, kenh)
    rieng = str(ck.get("keo_cheo_danh_sach_phat") or cai.get("ds_rieng") or "").strip()
    ra: Dict[str, Any] = {"chu_de": [], "rieng": rieng, "mo_ta": {}, "nguon": "", "can_hoc": False,
                          "ly_do_hoc": ""}
    tu_yaml = [t.strip() for t in str(ck.get("danh_sach_phat_kenh") or "").split("|") if t.strip()]
    if tu_yaml:
        ra.update(chu_de=tu_yaml, nguon="kenh.yaml")
        return ra
    hs = ds_tu_ho_so(goc, kenh)
    if hs:
        ra.update(chu_de=[t for t, _m in hs], mo_ta={t: m for t, m in hs if m}, nguon="ho-so")
        return ra
    muc = doc_ds_kenh(thu_muc or thu_muc_mac_dinh(goc)).get(kenh) or {}
    ten = [str(t) for t in muc.get("ten") or [] if str(t).strip()]
    try:
        luc = _dt.datetime.strptime(str(muc.get("luc") or "")[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        luc = None
    if ten:
        ra.update(chu_de=ten, nguon="hoc")
    if not muc or luc is None:
        ra.update(can_hoc=True, ly_do_hoc="chưa học danh sách phát của {0}".format(kenh))
    elif muc.get("can_hoc_lai"):
        ra.update(can_hoc=True, ly_do_hoc="cần học lại: {0}".format(muc.get("ly_do_hoc_lai") or "?"))
    elif bay_gio - luc > _dt.timedelta(days=float(cai.get("tuoi_ds_hoc_ngay") or 7)):
        ra.update(can_hoc=True, ly_do_hoc="sổ học danh sách phát {0} cũ ({1})".format(kenh, muc.get("luc")))
    return ra


def danh_sach_phat_cua(goc: str, kenh: str, cai: Dict[str, Any],
                       thu_muc: Optional[str] = None) -> Tuple[List[str], str]:
    """`(danh sách phát theo chủ đề, danh sách phát riêng)` của kênh lớn — xem `tra_ds`."""
    d = tra_ds(goc, kenh, cai, thu_muc)
    return d["chu_de"], d["rieng"]


# ── video kênh em ───────────────────────────────────────────────────────────

def _tieu_de_ho_so(goc: str, kenh: str, ma_goi: str) -> str:
    hs = _doc_json(os.path.join(duong_kenh(goc, kenh), "ho-so-video", "{0}.json".format(ma_goi)))
    return str((hs or {}).get("tieu_de") or "").strip() if isinstance(hs, dict) else ""


def _bang_tom_tat(goc: str, kenh: str) -> List[Dict[str, str]]:
    hang = _doc_csv_dict(os.path.join(duong_kenh(goc, kenh), "chi-so", "bang-tom-tat.csv"))
    try:
        from .chi_so_ytb import loc_video as _loc  # noqa: PLC0415

        hang = _loc.loc_hang_bang(_loc.moc_cua_thu_muc(duong_kenh(goc, kenh)), hang)
    except Exception:  # noqa: BLE001 — bộ lọc đời trước hỏng thì dùng cả bảng
        pass
    return hang


def _ke_hoach(goc: str, kenh: str) -> List[Dict[str, str]]:
    duong = os.path.join(duong_kenh(goc, kenh), "ke-hoach-dang", "ke-hoach.csv")
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            chu = tep.read()
    except OSError:
        return []
    try:
        return [d for d in csv.DictReader(io.StringIO(chu)) if isinstance(d, dict)]
    except csv.Error:
        return []


def video_kenh_em(goc: str, kenh: str, duong_so: Optional[str] = None) -> List[Dict[str, Any]]:
    """Video ĐÃ/SẼ công khai của kênh em: `[{video_id, tieu_de, dang_luc, view, hien_thi, giay, nguon}]`.

    Gộp ba nguồn theo `video_id` (giờ công khai chính xác nhất thắng: kế hoạch/sổ có giờ, bảng
    Studio chỉ có ngày). Nơi gọi tự lọc theo `dang_luc` — hàm này không biết "bây giờ"."""
    ra: Dict[str, Dict[str, Any]] = {}

    def gop(vid: str, **truong: Any) -> None:
        vid = str(vid or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            return
        o = ra.setdefault(vid, {"video_id": vid, "tieu_de": "", "dang_luc": None, "view": None,
                                "hien_thi": None, "giay": None, "nguon": [], "chinh_xac": False})
        for k, v in truong.items():
            if k == "dang_luc":
                if v is None:
                    continue
                cx = bool(truong.get("_cx"))
                if o["dang_luc"] is None or (cx and not o["chinh_xac"]):
                    o["dang_luc"], o["chinh_xac"] = v, cx
            elif k == "nguon":
                if v not in o["nguon"]:
                    o["nguon"].append(v)
            elif k.startswith("_"):
                continue
            elif v not in (None, "") and o.get(k) in (None, ""):
                o[k] = v

    kh = _ke_hoach(goc, kenh)
    tieu_de_ma = {str(d.get("Mã gói") or "").strip(): str(d.get("Tiêu đề") or "").strip() for d in kh}
    for d in kh:
        tt = str(d.get("Trạng thái đăng") or "").strip().upper()
        if not tt.startswith("ĐÃ ĐĂNG"):
            continue
        luc = _doc_luc(d.get("Ngày đăng"), d.get("Giờ đăng"))
        cx = bool(re.match(r"^\d{1,2}:\d{2}", str(d.get("Giờ đăng") or "").strip()))
        gop(d.get("Video ID"), tieu_de=str(d.get("Tiêu đề") or "").strip(), dang_luc=luc, _cx=cx,
            nguon="ke-hoach")

    so = _doc_json(duong_so) if duong_so else None
    if isinstance(so, dict):
        tien_to = kenh + "/"
        for khoa, m in so.items():
            if not str(khoa).startswith(tien_to) or not isinstance(m, dict):
                continue
            if m.get("trang_thai") not in _TT_SO_DA_LEN:
                continue
            ma = str(khoa)[len(tien_to):]
            luc = _doc_luc(m.get("lich_dat") or m.get("lich"))
            gop(m.get("video_id"), tieu_de=tieu_de_ma.get(ma) or _tieu_de_ho_so(goc, kenh, ma),
                dang_luc=luc, _cx=luc is not None, giay=m.get("thoi_luong"), nguon="so-video-id")

    for d in _bang_tom_tat(goc, kenh):
        gop(d.get("Mã video"), tieu_de=str(d.get("Tiêu đề") or "").strip(),
            dang_luc=_doc_luc(d.get("Ngày đăng")), _cx=False,
            view=_so(d.get("Lượt xem")), hien_thi=_so(d.get("Lượt hiển thị")),
            giay=_giay(d.get("Dài")), nguon="bang-tom-tat")
    return list(ra.values())


# ── chọn danh sách phát ─────────────────────────────────────────────────────

def chon_danh_sach(tieu_de: str, cum_video: Sequence[str], danh_sach: Sequence[str],
                   cum_cua_ds: Callable[[str], Sequence[str]], ds_rieng: str = "",
                   bo_qua: Sequence[str] = (), chon_ai: Optional[Callable[[str, List[str]], str]] = None
                   ) -> Tuple[str, List[str], str]:
    """`(tên danh sách phát, cụm chung, cách chọn)` — `("", [], "")` khi không có chỗ hợp.

    1. CỤM: danh sách phát có nhiều cụm chung nhất với video (hoà → thứ tự khai trong kenh.yaml).
    2. AI (nếu nơi gọi đưa `chon_ai(tiêu đề, [tên])` → tên | "" = không hợp | None = AI không dùng
       được): chọn theo NGHĨA trong số còn lại.
    3. RIÊNG: danh sách phát riêng của kênh lớn (vd "おすすめ").
    2b. AI không dùng được và không có danh sách riêng → GẦN CHỮ (`gan_nhat_theo_chu`, đường lùi cuối).
    `bo_qua`: danh sách phát đã đủ suất hôm nay."""
    bo = set(bo_qua or ())
    cv = set(cum_video or ())
    con = [t for t in danh_sach if t not in bo and t != ds_rieng]
    tot, tot_chung = "", []
    for t in con:
        try:
            chung = sorted(cv & set(cum_cua_ds(t) or ()))
        except Exception:  # noqa: BLE001
            chung = []
        if len(chung) > len(tot_chung):
            tot, tot_chung = t, chung
    if tot:
        return tot, tot_chung, "cum"
    if con:
        ai: Optional[str] = None
        if chon_ai is not None:
            try:
                tra = chon_ai(tieu_de, list(con))
                ai = None if tra is None else str(tra).strip()
            except Exception:  # noqa: BLE001 — AI hỏng = AI không dùng được
                ai = None
        if ai and ai in con:
            return ai, [], "ai"
        if ai is None and not (ds_rieng and ds_rieng not in bo):   # có danh sách riêng thì riêng trước
            gan = gan_nhat_theo_chu(tieu_de, con)
            if gan:
                return gan, [], "gan_chu"
    if ds_rieng and ds_rieng not in bo:
        return ds_rieng, [], "rieng"
    return "", [], ""


_NHAN = re.compile(r"【[^】]*】|\[[^\]]*\]|［[^］]*］|#\S+")
#: Chữ "có nghĩa" cho cặp chữ: kanji, katakana, chữ Latin/số (hiragana đơn thuần là trợ từ: の, が…).
_CHU_NGHIA = re.compile(r"[一-鿿゠-ヿA-Za-z0-9À-ỹ]")


def _cap_chu(s: str) -> set:
    s = re.sub(r"\s+", "", _NHAN.sub(" ", _chuan(s)))
    return {s[i:i + 2] for i in range(len(s) - 1) if _CHU_NGHIA.search(s[i:i + 2])}


def gan_nhat_theo_chu(tieu_de: str, danh_sach: Sequence[str], toi_thieu: int = 2) -> str:
    """ĐƯỜNG LÙI CUỐI (ví AI chặn): danh sách có nhiều cặp chữ chung nhất với tiêu đề, ≥ `toi_thieu`."""
    a = _cap_chu(tieu_de)
    tot, diem = "", 0
    for t in danh_sach:
        d = len(a & _cap_chu(t))
        if d > diem:
            tot, diem = t, d
    return tot if diem >= toi_thieu else ""


def tao_chon_ai(goc: str, thu_muc: str, cai: Dict[str, Any], goi_ai: Optional[Callable[[str], str]] = None,
                nhat_ky: Optional[Callable[[str], None]] = None):
    """Bộ chọn danh sách THEO NGHĨA cho một lần lập kế hoạch: `chon(kênh lớn, video, tiêu đề, [tên], {mô tả})`
    → tên | "" (AI nói không hợp) | None (AI không dùng được: ví chặn, hết lượt, lỗi).

    Một lượt gọi mỗi (kênh lớn, video, bộ tên danh sách) — nhớ trong `ai-chon.json`; tối đa
    `toi_da_goi_ai` lượt gọi THẬT mỗi lần lập. `goi_ai(đề) → chữ`; None → `goi_chat_that(goc)` lúc cần."""
    nk = nhat_ky or (lambda _s: None)
    duong = os.path.join(thu_muc, TEP_AI_CHON)
    nho = _doc_json(duong)
    nho = nho if isinstance(nho, dict) else {}
    hop: Dict[str, Any] = {"goi": goi_ai, "da_tao": goi_ai is not None, "so_lan": 0, "bao_chan": False}
    toi_da = int(cai.get("toi_da_goi_ai") or 0)
    han = float(cai.get("han_ai_giay") or 60)

    def lay_goi():
        if not hop["da_tao"]:
            hop["da_tao"] = True
            try:
                from .giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415
                hop["goi"] = goi_chat_that(goc, nk)
            except Exception as loi:  # noqa: BLE001
                nk("kéo chéo: không dựng được AI chọn danh sách: {0}".format(str(loi)[:120]))
                hop["goi"] = None
        return hop["goi"]

    def chon(chu: str, vid: str, tieu_de: str, ds: Sequence[str], mo_ta: Optional[Dict[str, str]] = None):
        ds = [str(t) for t in ds if str(t).strip()]
        if not ds:
            return ""
        khoa = "{0}/{1}".format(chu, vid)
        muc = nho.get(khoa)
        if isinstance(muc, dict) and sorted(muc.get("ds") or []) == sorted(ds):
            return str(muc.get("ten") or "")
        goi = lay_goi()
        if goi is None:
            if not hop["bao_chan"]:
                nk("kéo chéo: AI chọn danh sách KHÔNG dùng được (ví chặn/chưa đăng nhập) — lùi danh sách riêng/gần chữ")
                hop["bao_chan"] = True
            return None
        if hop["so_lan"] >= toi_da:
            if hop["so_lan"] == toi_da:
                nk("kéo chéo: đã gọi AI {0} lượt lần này (trần toi_da_goi_ai) — phần còn lại lùi".format(toi_da))
                hop["so_lan"] += 1
            return None
        hop["so_lan"] += 1
        mo_ta = mo_ta or {}
        de = ("You place a video into ONE playlist of a YouTube channel, judged by MEANING (topic and audience), "
              "not by shared words.\nPlaylists:\n"
              + "\n".join("- " + t + ((" — " + mo_ta[t][:160]) if mo_ta.get(t) else "") for t in ds)
              + "\n\nVideo title: " + str(tieu_de)[:300]
              + "\n\nIf no playlist fits the video's topic well enough that its viewers would want it, reply NONE."
              "\nReply with ONLY the exact playlist name, or NONE.")
        try:
            from .ban_giao_dang import _goi_co_han  # noqa: PLC0415
            tra = str(_goi_co_han(goi, de, han) or "").strip().strip("\"'`「」『』- ").strip()
        except Exception as loi:  # noqa: BLE001
            nk("kéo chéo: AI chọn danh sách lỗi ({0}) — lùi".format(str(loi)[:120]))
            return None
        ten = ""
        if tra and tra.upper() != "NONE":
            ten = next((t for t in ds if _chuan(t) == _chuan(tra)), "")
            if not ten:
                co = [t for t in ds if t in tra]
                ten = co[0] if len(co) == 1 else ""
        nk("kéo chéo: AI chọn cho {0} ({1}) → {2}".format(vid, chu, ten or "không hợp ({0})".format(tra[:40])))
        nho[khoa] = {"ds": ds, "ten": ten, "tra": tra[:80], "luc": _dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
        try:
            _ghi_json(duong, nho)
        except OSError:
            pass
        return ten

    return chon


def video_de_hoc(goc: str, kenh: str, duong_so: Optional[str] = None,
                 bay_gio: Optional[_dt.datetime] = None) -> str:
    """Một video CÔNG KHAI của chính `kenh` (mới nhất đã qua giờ công khai) — để mở hộp Lưu học tên."""
    bay_gio = bay_gio or _dt.datetime.now()
    ds = [v for v in video_kenh_em(goc, kenh, duong_so)
          if v.get("dang_luc") is not None and v["dang_luc"] <= bay_gio - _dt.timedelta(hours=1)]
    ds.sort(key=lambda v: v["dang_luc"], reverse=True)
    return ds[0]["video_id"] if ds else ""


# ── sổ đã thêm ──────────────────────────────────────────────────────────────

def doc_da_them(thu_muc: str) -> Dict[str, Any]:
    d = _doc_json(os.path.join(thu_muc, TEP_DA_THEM))
    if not isinstance(d, dict) or not isinstance(d.get("muc"), list):
        return {"phien_ban": 1, "muc": []}
    d["muc"] = [m for m in d["muc"] if isinstance(m, dict)]
    return d


def ghi_ket_qua(thu_muc: str, hanh_dong: Dict[str, Any], ket: str,
                luc: Optional[_dt.datetime] = None, **them: Any) -> Dict[str, Any]:
    """Nối một kết quả máy DOM vào sổ (`ket`: ok | da_co | loi:<lý do>). Trả mục vừa ghi."""
    luc = luc or _dt.datetime.now()
    so = doc_da_them(thu_muc)
    muc = dict(hanh_dong)
    muc.update(them)
    muc["ket"] = str(ket)
    muc["luc"] = luc.strftime("%Y-%m-%d %H:%M:%S")
    muc["ngay"] = luc.date().isoformat()
    so["muc"].append(muc)
    _ghi_json(os.path.join(thu_muc, TEP_DA_THEM), so)
    return muc


# ── dự đoán + đo ────────────────────────────────────────────────────────────

def du_doan_cho(goc: str, kenh_video: str, video_id: str, cai: Optional[Dict[str, Any]] = None,
                bay_gio: Optional[_dt.datetime] = None, bo_video: Sequence[str] = ()) -> Dict[str, Any]:
    """Mốc đo lúc thêm: số của video + tối đa `so_doi_chung` video đối chứng cùng kênh (đăng gần nhất,
    chưa từng được kéo — `bo_video`)."""
    cai = cai or CAI_DAT_MAC_DINH
    bay_gio = bay_gio or _dt.datetime.now()
    bang = {str(d.get("Mã video") or ""): d for d in _bang_tom_tat(goc, kenh_video)}
    goc_v = bang.get(video_id) or {}
    ngay_v = _doc_luc(goc_v.get("Ngày đăng"))
    bo = set(bo_video or ()) | {video_id}
    dc = []
    for vid, d in bang.items():
        if not vid or vid in bo or _so(d.get("Lượt xem")) is None:
            continue
        nd = _doc_luc(d.get("Ngày đăng"))
        if nd is None or nd > bay_gio:
            continue
        lech = abs((nd - ngay_v).total_seconds()) if ngay_v else (bay_gio - nd).total_seconds()
        dc.append((lech, vid, _so(d.get("Lượt xem"))))
    dc.sort()
    nguong = float(cai.get("nguong_hon_doi_chung") or 0.2)
    return {
        "luc_moc": bay_gio.strftime("%Y-%m-%d %H:%M"),
        "view_luc_them": _so(goc_v.get("Lượt xem")),
        "hien_thi_luc_them": _so(goc_v.get("Lượt hiển thị")),
        "doi_chung": {vid: v for _l, vid, v in dc[:int(cai.get("so_doi_chung") or 5)]},
        "kiem_sau_ngay": int(cai.get("kiem_sau_ngay") or 7),
        "gia_thuyet": ("sau {0} ngày lượt xem video này tăng (theo tỉ lệ) nhanh hơn trung vị nhóm đối "
                       "chứng cùng kênh ≥ {1:.0f}%").format(int(cai.get("kiem_sau_ngay") or 7), nguong * 100),
    }


def _ty_le_tang(truoc: Optional[float], sau: Optional[float]) -> Optional[float]:
    if truoc is None or sau is None:
        return None
    return (sau - truoc) / max(1.0, truoc)


def do_hieu_qua(goc: str, thu_muc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None,
                cai_dat: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Đo các lần thêm `ok` đã đủ `kiem_sau_ngay` ngày mà chưa đo: ghi `do_sau` vào sổ, trả các mục vừa đo."""
    thu_muc = thu_muc or thu_muc_mac_dinh(goc)
    cai = doc_cai_dat(thu_muc, cai_dat)
    bay_gio = bay_gio or _dt.datetime.now()
    so = doc_da_them(thu_muc)
    vua_do = []
    bang_cache: Dict[str, Dict[str, Dict[str, str]]] = {}
    for m in so["muc"]:
        if m.get("ket") != "ok" or m.get("do_sau"):
            continue
        dd = m.get("du_doan") or {}
        try:
            luc = _dt.datetime.strptime(str(m.get("luc"))[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if bay_gio - luc < _dt.timedelta(days=int(dd.get("kiem_sau_ngay") or cai["kiem_sau_ngay"])):
            continue
        kv = str(m.get("kenh_video") or "")
        if kv not in bang_cache:
            bang_cache[kv] = {str(d.get("Mã video") or ""): d for d in _bang_tom_tat(goc, kv)}
        bang = bang_cache[kv]
        now = _so((bang.get(str(m.get("video_id"))) or {}).get("Lượt xem"))
        tang = _ty_le_tang(dd.get("view_luc_them"), now)
        tang_dc = [t for t in (_ty_le_tang(v, _so((bang.get(vid) or {}).get("Lượt xem")))
                               for vid, v in (dd.get("doi_chung") or {}).items()) if t is not None]
        tv_dc = statistics.median(tang_dc) if tang_dc else None
        if tang is None or tv_dc is None:
            ket = "khong_du_so"
        elif tang >= tv_dc + float(cai.get("nguong_hon_doi_chung") or 0.2):
            ket = "keo_duoc"
        else:
            ket = "chua_thay"
        m["do_sau"] = {"luc": bay_gio.strftime("%Y-%m-%d %H:%M"), "view": now,
                       "tang": None if tang is None else round(tang, 3),
                       "tang_doi_chung_tv": None if tv_dc is None else round(tv_dc, 3),
                       "so_doi_chung": len(tang_dc), "ket": ket}
        vua_do.append(m)
    if vua_do:
        _ghi_json(os.path.join(thu_muc, TEP_DA_THEM), so)
    return vua_do


def tim_kenh_cua_video(goc: str, video_id: str, duong_so: Optional[str] = None) -> str:
    """Kênh (trong tool) có video này — "" nếu không thấy. Cho lệnh tay của máy DOM."""
    for ma in liet_ke_kenh(goc):
        if any(v["video_id"] == video_id for v in video_kenh_em(goc, ma, duong_so)):
            return ma
    return ""


# ── lập kế hoạch ────────────────────────────────────────────────────────────

def _bo_cum_kenh(goc: str, kenh: str) -> Callable[[str], List[str]]:
    from . import cong_thuc_v7 as v7  # noqa: PLC0415 — nhập muộn (mô-đun nặng)

    try:
        ch, _d = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    except Exception:  # noqa: BLE001
        ch = None
    if ch:
        v7.nap_phan_cum(goc, kenh, ch)

    def cum(tieu_de: str) -> List[str]:
        try:
            return list(v7.cum_cua_tieu_de(tieu_de, ch))
        except Exception:  # noqa: BLE001
            return []
    return cum


def lap_ke_hoach(goc: str, ngay: Any = None, *, thu_muc: Optional[str] = None,
                 cai_dat: Optional[Dict[str, Any]] = None, duong_so: Optional[str] = None,
                 cum_cua: Optional[Callable[[str, str], Sequence[str]]] = None,
                 chon_ai: Optional[Callable[[str, List[str]], Optional[str]]] = None,
                 goi_ai: Optional[Callable[[str], str]] = None,
                 bay_gio: Optional[_dt.datetime] = None,
                 nhat_ky: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Việc kéo chéo hôm `ngay`. Mỗi phần tử có `viec`:

    * `them`   — `{kenh_chu, danh_sach_phat, video_id, kenh_video, cum, cach_chon, ly_do, du_doan, ...}`
    * `hoc_ds` — `{kenh_chu, video_id (video công khai của chính kênh lớn, "" nếu không biết), lenh, ly_do}`:
      mở hộp Lưu đọc tên danh sách phát (không tích). Đứng TRƯỚC các việc `them` của cùng kênh.
    * `bao`    — cần người (kênh lớn chưa có danh sách phát công khai nào): `{kenh_chu, ly_do}`.

    `cum_cua(kênh lớn, tiêu đề)` → [mã cụm]; mặc định bộ cụm `cong_thuc_v7` CỦA KÊNH LỚN.
    `chon_ai(tiêu đề, [tên])` đè hẳn bộ chọn AI (bài kiểm); không có thì `ai_chon_ds` bật → `tao_chon_ai`
    với `goi_ai(đề) → chữ` (None → ví ShopAPI qua `goi_chat_that`).
    `duong_so`: sổ máy đăng (mặc định `<goc>/vm/logs/so-video-id.json`). `thu_muc`: chỗ các sổ.
    `bay_gio`: mặc định bây giờ (ngày khác hôm nay → 23:59 ngày đó). Chỉ ghi bộ nhớ AI (`ai-chon.json`)."""
    nk = nhat_ky or (lambda _s: None)
    thu_muc = thu_muc or thu_muc_mac_dinh(goc)
    cai = doc_cai_dat(thu_muc, cai_dat)
    hom_nay = _ngay(ngay) if ngay is not None else (bay_gio or _dt.datetime.now()).date()
    if bay_gio is None:
        bay_gio = _dt.datetime.now()
        if bay_gio.date() != hom_nay:
            bay_gio = _dt.datetime.combine(hom_nay, _dt.time(23, 59))
    if not cai.get("bat", True):
        nk("kéo chéo: đang TẮT (cai-dat.json bat=false)")
        return []
    duong_so = duong_so if duong_so is not None else os.path.join(goc, "vm", "logs", "so-video-id.json")
    ngay_s = hom_nay.isoformat()

    so = doc_da_them(thu_muc)
    da_video_toan_bo: set = set()
    da_video_theo_chu: set = set()
    loi_video: Dict[str, int] = {}
    dem_chu: Dict[str, int] = {}
    dem_ds: Dict[Tuple[str, str], int] = {}
    dem_em_tong: Dict[str, int] = {}
    dem_em_hom_nay: Dict[str, int] = {}
    for m in so["muc"]:
        vid, chu, ket = str(m.get("video_id") or ""), str(m.get("kenh_chu") or ""), str(m.get("ket") or "")
        if ket in _KET_DA_THEM:
            da_video_toan_bo.add(vid)
            da_video_theo_chu.add((chu, vid))
            em = str(m.get("kenh_video") or "")
            dem_em_tong[em] = dem_em_tong.get(em, 0) + 1
            if ket == "ok" and m.get("ngay") == ngay_s:
                dem_chu[chu] = dem_chu.get(chu, 0) + 1
                k = (chu, str(m.get("danh_sach_phat") or ""))
                dem_ds[k] = dem_ds.get(k, 0) + 1
                dem_em_hom_nay[em] = dem_em_hom_nay.get(em, 0) + 1
        elif ket.startswith("loi"):
            loi_video[vid] = loi_video.get(vid, 0) + 1

    toan_bo = bool(cai.get("mot_lan_moi_video", True))
    toi_chu = int(cai.get("toi_da_moi_kenh_chu") or 0)
    toi_ds = int(cai.get("toi_da_moi_ds") or 0)
    toi_loi = int(cai.get("toi_da_loi_moi_video") or 0)
    sau_dang = _dt.timedelta(hours=float(cai.get("gio_sau_dang") or 0))
    tuoi_toi_da = _dt.timedelta(days=float(cai.get("tuoi_toi_da_ngay") or 36500))
    ngan_nhat = int(cai.get("do_dai_toi_thieu_giay") or 0)

    ra: List[Dict[str, Any]] = []
    da_len_ke_hoach: set = set()
    bo_cum: Dict[str, Callable[[str], List[str]]] = {}

    def cum_cua_kenh(chu: str, td: str) -> List[str]:
        if cum_cua is not None:
            try:
                return [str(c) for c in (cum_cua(chu, td) or ())]
            except Exception:  # noqa: BLE001
                return []
        if chu not in bo_cum:
            bo_cum[chu] = _bo_cum_kenh(goc, chu)
        return bo_cum[chu](td)

    ai_hop: Dict[str, Any] = {}

    def bo_chon_ai(chu: str, vid: str, ds_du: List[str], mo_ta: Dict[str, str]):
        """`chon_ai(tiêu đề, [còn lại])` cho một video — hỏi AI với ĐỦ bộ tên (nhớ ổn định theo kênh)."""
        if chon_ai is not None:
            return chon_ai
        if not cai.get("ai_chon_ds", True):
            return None
        if "chon" not in ai_hop:
            ai_hop["chon"] = tao_chon_ai(goc, thu_muc, cai, goi_ai, nk)
        return lambda td, _con: ai_hop["chon"](chu, vid, td, ds_du, mo_ta)

    for nhom, thanh_vien in sorted(_cac_nhom(goc).items()):
        lon, em = phan_vai_nhom(goc, thanh_vien, cai, bay_gio)
        if not lon or not em:
            nk("nhóm {0}: {1} kênh lớn, {2} kênh em — không có gì để kéo".format(nhom, len(lon), len(em)))
            continue
        ung_vien: Dict[str, List[Dict[str, Any]]] = {}
        for ma in em:
            ds = []
            for v in video_kenh_em(goc, ma, duong_so):
                luc = v.get("dang_luc")
                if luc is None or luc > bay_gio - sau_dang or luc < bay_gio - tuoi_toi_da:
                    continue
                if v.get("giay") is not None and ngan_nhat and float(v["giay"]) < ngan_nhat:
                    continue
                if not v.get("tieu_de"):
                    continue
                if toi_loi and loi_video.get(v["video_id"], 0) >= toi_loi:
                    continue
                ds.append(v)
            ds.sort(key=lambda v: v["dang_luc"], reverse=True)
            ung_vien[ma] = ds
        nk("nhóm {0}: kênh lớn {1} · kênh em {2}".format(
            nhom, ", ".join("{0} ({1:.0f}h)".format(k, g) for k, g in sorted(lon.items(), key=lambda x: -x[1])),
            ", ".join("{0} ({1} video đủ tuổi)".format(k, len(ung_vien.get(k) or [])) for k in sorted(em))))

        for chu in sorted(lon, key=lambda k: -lon[k]):
            con = toi_chu - dem_chu.get(chu, 0)
            if con <= 0:
                nk("{0}: đã đủ {1} lần thêm hôm nay".format(chu, toi_chu))
                continue
            tds = tra_ds(goc, chu, cai, thu_muc, bay_gio)
            chu_de, rieng, mo_ta = tds["chu_de"], tds["rieng"], tds["mo_ta"]
            if tds["can_hoc"]:
                vh = video_de_hoc(goc, chu, duong_so, bay_gio)
                lenh = lenh_hoc_ds(chu) + ("" if vh else " --video <videoId công khai của {0}>".format(chu))
                ra.append({"viec": "hoc_ds", "ngay": ngay_s, "nhom": nhom, "kenh_chu": chu, "video_id": vh,
                           "lenh": lenh, "ly_do": "{0} — chạy: {1}".format(tds["ly_do_hoc"], lenh)})
                nk("{0}: {1} — chạy: {2}{3}".format(chu, tds["ly_do_hoc"], lenh,
                                                    " (tạm dùng sổ cũ)" if chu_de else ""))
            if not chu_de and not rieng:
                if not tds["can_hoc"]:
                    ly = ("{0}: hộp Lưu không có danh sách phát CÔNG KHAI nào — tạo một danh sách công khai "
                          "trên kênh (hoặc khai ds_rieng/keo_cheo_danh_sach_phat) rồi chạy: {1}").format(
                              chu, lenh_hoc_ds(chu))
                    ra.append({"viec": "bao", "ngay": ngay_s, "nhom": nhom, "kenh_chu": chu, "ly_do": ly})
                    nk(ly)
                continue
            cum_ds_cache: Dict[str, List[str]] = {}

            def cum_ds(t: str, _chu: str = chu) -> List[str]:
                if t not in cum_ds_cache:
                    cum_ds_cache[t] = cum_cua_kenh(_chu, t)
                return cum_ds_cache[t]

            thu_tu_em = sorted(em, key=lambda k: (dem_em_hom_nay.get(k, 0), dem_em_tong.get(k, 0), em[k], k))
            em_luot_nay: set = set()
            for vong in (1, 2):
                for ma_em in thu_tu_em:
                    if con <= 0:
                        break
                    if vong == 1 and ma_em in em_luot_nay:
                        continue
                    for v in ung_vien.get(ma_em) or []:
                        vid = v["video_id"]
                        if vid in da_len_ke_hoach or (chu, vid) in da_video_theo_chu:
                            continue
                        if toan_bo and vid in da_video_toan_bo:
                            continue
                        day = [t for t in chu_de + ([rieng] if rieng else [])
                               if toi_ds and dem_ds.get((chu, t), 0) >= toi_ds]
                        cv = cum_cua_kenh(chu, v["tieu_de"])
                        ten, chung, cach = chon_danh_sach(
                            v["tieu_de"], cv, chu_de, cum_ds, rieng, day,
                            bo_chon_ai(chu, vid, [t for t in chu_de if t != rieng], mo_ta))
                        if not ten:
                            continue
                        ly_do = {
                            "cum": "cụm chung {0} giữa tiêu đề và danh sách phát".format(", ".join(chung)),
                            "ai": "AI chọn theo nghĩa (không có cụm chung)",
                            "gan_chu": "gần chữ (AI không dùng được, không có danh sách riêng)",
                            "rieng": "danh sách phát riêng (không có danh sách chủ đề hợp)",
                        }[cach]
                        hd = {
                            "viec": "them", "ngay": ngay_s, "nhom": nhom, "kenh_chu": chu, "danh_sach_phat": ten,
                            "video_id": vid, "kenh_video": ma_em, "tieu_de": v["tieu_de"],
                            "cum": ",".join(chung or cv), "cach_chon": cach, "nguon_ds": tds["nguon"],
                            "ly_do": "{0} {1:.0f}h/{2}n ≥ {3:.0f}h kéo {4}: {5}; công khai {6}".format(
                                chu, lon[chu], int(cai.get("so_ngay_gio_xem") or 28),
                                float(cai.get("nguong_gio_xem") or 0), ma_em, ly_do,
                                v["dang_luc"].strftime("%Y-%m-%d %H:%M")),
                            "du_doan": du_doan_cho(goc, ma_em, vid, cai, bay_gio,
                                                   bo_video=da_video_toan_bo | da_len_ke_hoach),
                        }
                        ra.append(hd)
                        da_len_ke_hoach.add(vid)
                        em_luot_nay.add(ma_em)
                        dem_em_hom_nay[ma_em] = dem_em_hom_nay.get(ma_em, 0) + 1
                        dem_ds[(chu, ten)] = dem_ds.get((chu, ten), 0) + 1
                        con -= 1
                        break
            if con > 0:
                nk("{0}: chỉ lên được {1}/{2} việc (hết video hợp/hết suất danh sách phát)".format(
                    chu, toi_chu - dem_chu.get(chu, 0) - con, toi_chu - dem_chu.get(chu, 0)))
    return ra
