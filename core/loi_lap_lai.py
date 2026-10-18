"""LỖI LẶP LẠI → SỔ TAY XỬ LÝ (17/10/2026) — đào chữ ký lỗi 14 ngày, mỗi lỗi hay gặp có một bài: phát hiện → sửa an
toàn → kiểm lại.

═══ VÌ SAO ═══ Chủ 17/10: *"nhiều ngày mày giám sát, giờ nên xem lại logic để mọi thứ hoạt động auto, tự fix, tự hoàn
thiện"*. Nhiều ngày qua người giám sát tự đọc log để thấy cùng một lỗi lặp (khoá chết chặn kênh, việc DOM bị hoãn hàng
giờ, ngôn ngữ giao diện bỏ dở, nguồn tư liệu đã gỡ làm lượt kẹt ở kịch bản…). Tệp này làm việc đọc log ấy bằng mã.

═══ ĐÀO (`dao`) ═══ Đọc CHỈ ĐỌC các nguồn (không đụng tệp nào): `vm/agent.log` (chỉ giờ — ngày suy lùi từ cuối tệp),
`vm/logs/dang-dom.log`, `vm/logs/studio-may/*.log`, `workspace/tu-chay/*.log` (dòng không giờ mang giờ dòng có giờ gần
nhất phía trên), `CHANNEL/*/tu-chay/<ngày>.json` (nhật ký lượt), `workspace/van-hanh/van-hanh.log`, sự kiện `loi` của
`nao/bo-phan.db`, `workspace/loi-chay-max.md`. Dòng LỖI (`la_loi`) → MẪU (`mau_loi`: chuẩn hoá của não bộ phận — bỏ
đường dẫn, mã, số, tên kênh — rồi gộp biến thể) → đếm theo mẫu: số lần, số ngày, kênh, nguồn, lần đầu/cuối, ví dụ.

═══ SỔ TAY (`SO_TAY`) ═══ Mỗi bài: `ma`, regex nhận mẫu, `lop` (`tu_sua` máy sửa an toàn | `thu_lai` lỗi tạm — chỉ thử
lại, luật chủ | `cho_phien` tự hồi ở phiên kế, máy kiểm lại | `nguoi` chỉ người làm được | `bao` chưa có cách sửa an toàn
— báo kèm bằng chứng). `chay_so_tay` chạy các bài `tu_sua` (gác tổng mỗi 15 phút qua `core.tu_kiem`):
  * `khoa_chet` — khoá `{pid, mốc}` (theo `van_hanh.MAU_KHOA`, TRỪ dấu đang đăng dở) trỏ PID chết ≥ 10 phút → xoá qua
    `ben_bi.don_khoa_chet_an_toan` (đổi tên nguyên tử, đọc lại). Kiểm: lượt sau khoá không còn.
  * `viec_doi` — skill nặng bị "để lượt sau"/"hoãn" liên tục > `GIO_DOI_LAU` giờ không lần nào xong → ghi
    `workspace/tu-kiem/uu-tien.json`; `ky_nang_tu` xếp việc ấy LÊN ĐẦU suất nặng lượt sau. Kiểm: có lần "xong".
  * `hl_tam` — ngôn ngữ giao diện tạm `vi` (`vm/logs/hl-tam/<k>.json`) còn đó khi không Chrome kênh nào mở: phiên DOM
    kế của kênh tự trả (`ngon_ngu_tam.tra`). Máy theo dõi tuổi; quá `GIO_HL_TAM` giờ → báo.

    python -X utf8 -m core.loi_lap_lai dao [--ngay 14] [--goc G] [--md <tệp>]   bảng chữ ký (chỉ đọc)
    python -X utf8 -m core.loi_lap_lai so-tay [--thu] [--goc G]                  chạy các bài tự sửa (--thu: chỉ in)
"""

from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

NGAY_DAO = 14
#: Skill nặng chờ suất (để lượt sau / hoãn) liên tục quá ngần này giờ mà không lần nào xong → ưu tiên.
GIO_DOI_LAU = 6.0
#: Ngôn ngữ giao diện tạm `vi` còn sót quá ngần này giờ → báo (phiên DOM kế của kênh lẽ ra đã trả).
GIO_HL_TAM = 24.0
#: Đọc tối đa ngần này byte cuối mỗi tệp log (log lớn nhất ~4 MB; 14 ngày nằm trọn).
DOC_TOI_DA_BYTE = 6_000_000
TEP_UU_TIEN = ("workspace", "tu-kiem", "uu-tien.json")
TEP_SO_TAY = ("workspace", "tu-kiem", "so-tay.json")

_RE_LOI = re.compile(
    r"lỗi(?! 0\b)|hỏng|\berror\b|exception|traceback|\bfail|thất bại|timeout|quá hạn|quá giờ|"
    r"mã thoát [1-9-]|mã [1-9]\d*\b|(?-i:\bKHÔNG\b|HỎNG)|kẹt|\btreo\b|đã chết|từ chối|(?<!không )chặn|"
    r"(?:HTTP|status[=: ]*|code[=: ]*)\s*(?:50[234]|429)\b|\(!\)|"
    r"không (được|thể|tìm|thấy|nhận|lấy|tải|đọc|mở|có quyền)|chưa xong|bỏ đó|câm|mất kết nối|unavailable",
    re.IGNORECASE)
#: Dòng có chữ "lỗi"/"không" nhưng là thông tin bình thường — không tính.
_RE_KHONG_PHAI = re.compile(
    r"lỗi 0\b|ok \d+ · lỗi 0|không có (việc|mã cần đăng|gì|lỗi|bình luận mới)|không có việc|0 lỗi|không đổi|"
    r"không cần|không áp|^\s*$|đang chờ việc nặng|vẫn đang làm|đã có sẵn|không làm lại|Không nghiên cứu lại|"
    r"chọn tấm|Claude Max chấm|tốt nhất [\d.]+/\d+|giữ lời nhắc|dựng trên máy|không tốn tiền|một lần nén|phóng \d|"
    r"hình ngắn hơn tiếng|chốt danh bạ|→ bỏ:|không phải kênh tâm lý|không có video công khai|đã sống lại|"
    r"đã TRẢ lại|cứu cảnh \d+: đã có|đường viết chữ:|ghép video \d+%|không chặn|tiến trình con xong \(mã 0\)",
    re.IGNORECASE)
_RE_GIO_DAU = re.compile(r"^\[?(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})")
_RE_GIO_NGAN = re.compile(r"^(\d{2}):(\d{2}):(\d{2}) ")
_RE_KENH = re.compile(r"\b(TL\d(?:-T7)?(?:-K\d|-v\d)?|K\d)\b")

Dong = Tuple[float, str, str, str]       # (epoch, nguồn, kênh, chữ)


# ── tiện ích ───────────────────────────────────────────────────────────────────

def _doc_duoi(duong: str, toi_da: int = DOC_TOI_DA_BYTE) -> List[str]:
    try:
        with open(duong, "rb") as tep:
            tep.seek(0, os.SEEK_END)
            n = tep.tell()
            tep.seek(max(0, n - toi_da))
            du = tep.read()
    except OSError:
        return []
    chu = du.decode("utf-8", "replace")
    if n > toi_da:
        chu = chu.split("\n", 1)[-1]
    return chu.splitlines()


def _epoch(ngay: str, gio: str) -> Optional[float]:
    try:
        return _dt.datetime.strptime(ngay + " " + gio, "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        return None


def _kenh_trong(chu: str, mac_dinh: str = "") -> str:
    m = _RE_KENH.search(chu)
    return m.group(1) if m else mac_dinh


def la_loi(chu: str) -> bool:
    s = str(chu or "")
    return bool(_RE_LOI.search(s)) and not _RE_KHONG_PHAI.search(s)


# ── đọc nguồn (CHỈ ĐỌC) ────────────────────────────────────────────────────────

def doc_log_co_ngay(duong: str, nguon: str, kenh: str = "") -> Iterator[Dong]:
    """Log mỗi dòng mở đầu `YYYY-MM-DD HH:MM:SS` hoặc `[YYYY-MM-DD HH:MM:SS]`; dòng không giờ mang giờ dòng trên."""
    luc: Optional[float] = None
    for d in _doc_duoi(duong):
        m = _RE_GIO_DAU.match(d)
        if m:
            luc = _epoch(m.group(1), m.group(2)) or luc
            d = d[m.end():].lstrip("],:0123456789 ")
        if luc is not None:
            yield luc, nguon, _kenh_trong(d, kenh), d.strip()


def doc_log_chi_gio(duong: str, nguon: str) -> Iterator[Dong]:
    """Log chỉ có `HH:MM:SS` (agent.log): ngày suy LÙI từ ngày sửa tệp — giờ tăng khi đi lùi = qua nửa đêm."""
    try:
        ngay = _dt.datetime.fromtimestamp(os.path.getmtime(duong)).date()
    except OSError:
        return
    dong = _doc_duoi(duong)
    ra: List[Dong] = []
    truoc: Optional[int] = None
    for d in reversed(dong):
        m = _RE_GIO_NGAN.match(d)
        if not m:
            continue
        giay = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        if truoc is not None and giay > truoc + 300:
            ngay -= _dt.timedelta(days=1)
        truoc = giay
        luc = _dt.datetime.combine(ngay, _dt.time()).timestamp() + giay
        ra.append((luc, nguon, _kenh_trong(d), d[m.end():].strip()))
    return iter(reversed(ra))


def doc_nhat_ky_luot(goc: str) -> Iterator[Dong]:
    """`CHANNEL/<k>/tu-chay/<ngày>.json`: dòng nhật ký + lý do dừng của lượt (giờ = trưa ngày sổ — đủ cho đếm ngày)."""
    for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", "*", "tu-chay", "????-??-??.json"))):
        kenh = os.path.basename(os.path.dirname(os.path.dirname(p)))
        ngay = os.path.basename(p)[:10]
        luc = _epoch(ngay, "12:00:00")
        if luc is None:
            continue
        try:
            with io.open(p, encoding="utf-8") as tep:
                du = json.load(tep)
        except (OSError, ValueError):
            continue
        for d in (du.get("nhat_ky") or []) if isinstance(du, dict) else []:
            yield luc, "luot", kenh, str(d).strip()
        for r in (du.get("runs") or []) if isinstance(du, dict) else []:
            if isinstance(r, dict) and not r.get("ok") and (r.get("ly_do") or r.get("loi")):
                yield luc, "luot", kenh, str(r.get("ly_do") or r.get("loi")).strip()


def doc_nao_loi(goc: str, tu: float) -> Iterator[Dong]:
    p = os.path.join(goc, "nao", "bo-phan.db")
    if not os.path.isfile(p):
        return
    for che_do in ("mode=ro", "immutable=1"):
        try:
            con = sqlite3.connect("file:{0}?{1}".format(urllib.request.pathname2url(p), che_do), uri=True, timeout=2)
            try:
                hang = con.execute("SELECT luc, kenh, noi_dung, nguon FROM su_kien WHERE loai = 'loi' AND luc >= ?",
                                   (tu,)).fetchall()
            finally:
                con.close()
        except sqlite3.Error:
            continue
        for luc, kenh, nd, ng in hang:
            yield float(luc), "nao:" + str(ng or "?"), str(kenh or ""), str(nd or "")
        return


_RE_MAX = re.compile(r"^- \[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\] \*\*(\w+)\*\*(?: · kênh ([^ ]+))? — (.*)$")


def doc_loi_chay_max(goc: str) -> Iterator[Dong]:
    for d in _doc_duoi(os.path.join(goc, "workspace", "loi-chay-max.md")):
        m = _RE_MAX.match(d.strip())
        if m:
            luc = _epoch(m.group(1), m.group(2) + ":00")
            if luc is not None:
                yield luc, "loi-chay-max:" + m.group(3), m.group(4) or "", m.group(5)


def cac_nguon(goc: str, tu: float) -> List[Tuple[str, Callable[[], Iterable[Dong]]]]:
    vm = os.path.join(goc, "vm")
    ra: List[Tuple[str, Callable[[], Iterable[Dong]]]] = [
        ("vm/agent.log", lambda: doc_log_chi_gio(os.path.join(vm, "agent.log"), "agent")),
        ("vm/logs/dang-dom.log", lambda: doc_log_co_ngay(os.path.join(vm, "logs", "dang-dom.log"), "dang-dom")),
        ("workspace/van-hanh/van-hanh.log",
         lambda: doc_log_co_ngay(os.path.join(goc, "workspace", "van-hanh", "van-hanh.log"), "van-hanh")),
        ("CHANNEL/*/tu-chay/*.json", lambda: doc_nhat_ky_luot(goc)),
        ("nao/bo-phan.db", lambda: doc_nao_loi(goc, tu)),
        ("workspace/loi-chay-max.md", lambda: doc_loi_chay_max(goc)),
    ]
    for p in sorted(glob.glob(os.path.join(vm, "logs", "studio-may", "*.log"))):
        k = os.path.basename(p)[:-4]
        ra.append(("vm/logs/studio-may/" + os.path.basename(p),
                   (lambda p=p, k=k: doc_log_co_ngay(p, "studio-may", k))))
    for p in sorted(glob.glob(os.path.join(goc, "workspace", "tu-chay", "*.log"))):
        if os.path.getmtime(p) < tu:
            continue
        ten = os.path.basename(p)
        k = _kenh_trong(ten.replace("-", " ").replace(" T7", "-T7").replace(" K", "-K"))
        ra.append(("workspace/tu-chay/" + ten, (lambda p=p, ten=ten, k=k: doc_log_co_ngay(p, "tu-chay:" + ten[:-4], k))))
    return ra


# ── mẫu lỗi ───────────────────────────────────────────────────────────────────

_GOP = (
    (re.compile(r"^(?:\[<kenh>\]\s*|#\)\s*|\[OK\]\s*)+"), ""),
    (re.compile(r"^(?:lần # hỏng \(|lý do cảnh hỏng: |thăm dò cảnh #: |cảnh #: chưa ra clip \()+"), ""),
    (re.compile(r"^(?:cảnh #: )+(?=cảnh #)"), ""),
    (re.compile(r"(\(dấu hiệu:).*"), r"\1 …)"),
    (re.compile(r"\(“.*"), "(“…”)"),
    (re.compile(r"ERROR: \[youtube\] <ma>?:?"), "ERROR: [youtube] <id>:"),
    (re.compile(r"\s*[—-]\s*thử lại sau # giây\.?"), " — thử lại"),
    (re.compile(r"\(#/#\)"), "(n/m)"),
)


def mau_loi(chu: str, kenh_ds: Sequence[str] = ()) -> str:
    try:
        from .nao_bo_phan._chung import chuan_hoa  # noqa: PLC0415
        s = chuan_hoa(chu, kenh_ds)
    except Exception:  # noqa: BLE001
        s = re.sub(r"\d+", "#", " ".join(str(chu).split()))[:160]
    s = re.sub(r"\b[A-Za-z0-9_-]{11}\b(?=[: ])", "<id>", s)
    for re_, thay in _GOP:
        s = re_.sub(thay, s)
    return " ".join(s.split())[:140]


def dao(goc: str, *, ngay: int = NGAY_DAO, bay: Optional[float] = None, toi_da_nhom: int = 200) -> Dict[str, Any]:
    """Đào mọi nguồn `ngay` ngày gần nhất → `{tu, den, nguon: {tên: số dòng lỗi}, nhom: [...]}` xếp theo số lần."""
    bay = time.time() if bay is None else bay
    tu = bay - ngay * 86400
    try:
        from .ky_nang import _cac_kenh  # noqa: PLC0415
        kenh_ds = _cac_kenh(goc)
    except Exception:  # noqa: BLE001
        kenh_ds = []
    nhom: Dict[str, Dict[str, Any]] = {}
    dem_nguon: Counter = Counter()
    # Một sự việc thường ghi ở nhiều nơi (log điều phối + tu-chay.log + nhật ký lượt + sự kiện não gom lại từ log):
    # đếm MỘT lần mỗi (mẫu, kênh, 2 phút); nguồn chỉ có ngày (nhật ký lượt) chỉ tính khi ngày ấy chưa nguồn nào có.
    da_thay: set = set()
    ngay_co: set = set()
    for ten, ham in sorted(cac_nguon(goc, tu), key=lambda x: x[0].startswith("CHANNEL")):
        try:
            for luc, nguon, kenh, chu in ham():
                if luc < tu or luc > bay + 3600 or not la_loi(chu):
                    continue
                m = mau_loi(chu, kenh_ds)
                if len(m) < 8:
                    continue
                ngay_s = _dt.date.fromtimestamp(luc).isoformat()
                khoa = (m, kenh, ngay_s) if nguon == "luot" else (m, kenh, int(luc // 120))
                if khoa in da_thay or (nguon == "luot" and (m, kenh, ngay_s) in ngay_co):
                    continue
                da_thay.add(khoa)
                ngay_co.add((m, kenh, ngay_s))
                dem_nguon[ten] += 1
                g = nhom.setdefault(m, {"mau": m, "so": 0, "ngay": set(), "kenh": Counter(), "nguon": Counter(),
                                        "dau": luc, "cuoi": luc, "vi_du": chu[:240]})
                g["so"] += 1
                g["ngay"].add(_dt.date.fromtimestamp(luc).isoformat())
                if kenh:
                    g["kenh"][kenh] += 1
                g["nguon"][nguon.split(":")[0]] += 1
                if luc < g["dau"]:
                    g["dau"] = luc
                if luc >= g["cuoi"]:
                    g["cuoi"], g["vi_du"] = luc, chu[:240]
        except Exception as loi:  # noqa: BLE001 — một nguồn hỏng không làm vỡ bảng
            dem_nguon[ten + " (lỗi đọc: {0})".format(str(loi)[:60])] += 0
    ds = sorted(nhom.values(), key=lambda g: (-g["so"], g["mau"]))[:toi_da_nhom]
    for g in ds:
        g["so_ngay"] = len(g.pop("ngay"))
        g["kenh"] = dict(g["kenh"].most_common(8))
        g["nguon"] = dict(g["nguon"])
        g["bai"] = phan_lop(g["mau"] + " " + g["vi_du"])
    return {"tu": _dt.datetime.fromtimestamp(tu).isoformat(timespec="minutes"),
            "den": _dt.datetime.fromtimestamp(bay).isoformat(timespec="minutes"), "nguon": dict(dem_nguon),
            "nhom": ds}


# ── sổ tay ────────────────────────────────────────────────────────────────────

#: (mã, regex trên mẫu + ví dụ, lớp, tên đọc, phát hiện → sửa → kiểm)
SO_TAY: Tuple[Tuple[str, "re.Pattern[str]", str, str, str], ...] = (
    ("nguon_mat", re.compile(r"no longer available|Video unavailable|uploader has closed|video (đã )?bị gỡ|"
                             r"không lấy được lời thoại", re.I), "tu_sua",
     "Video tư liệu đã bị gỡ — lượt kẹt ở kịch bản",
     "lượt dừng ở kịch bản, log yt-dlp «unavailable» + trang xem công khai playabilityStatus ERROR (hai bằng chứng) → "
     "bỏ lượt theo đúng luật L3 của tu_chay (`_bo_luot_qua_han`, giữ khoá kênh lúc ghi) → lượt sau tự chọn nguồn mới; "
     "kiểm: sổ lượt có `bo` + có lượt mới"),
    ("luot_ket", re.compile(r"Dừng ở “|chưa xong hết|chưa xong — chạy tiếp|không làm được clip thật|CẦN NGƯỜI XEM",
                            re.I), "tu_sua",
     "Lượt sản xuất kẹt cùng một khâu nhiều ngày (L3 không bỏ vì tưởng lỗi phía ShopAPI)",
     "lượt chưa bỏ, tự phục hồi ≥ 10 lần: cùng cảnh «không làm được clip thật» ≥ 72 giờ → bỏ lượt (không xoá gì, "
     "gỡ được bằng cách xoá khoá `bo`) để kênh làm video mới; ≥ 24 giờ → báo; lỗi tạm ShopAPI khác: chỉ thử lại, "
     "≥ 72 giờ → báo; kiểm: kênh có lượt mới, nhịp đăng giữ"),
    ("khoa_chet", re.compile(r"khoá .*(PID|pid) .*(chết|CHẾT)|khoá cũ|lock|\.khoa\b", re.I), "tu_sua",
     "Khoá trỏ tiến trình đã chết",
     "khoá {pid, mốc} theo van_hanh.MAU_KHOA, PID chết ≥ 10 phút → xoá nguyên tử (ben_bi.don_khoa_chet_an_toan); "
     "kiểm: lượt sau khoá không còn"),
    ("viec_doi", re.compile(r"xếp hàng chờ khe|để lượt sau|khoá máy bận|đang chờ việc nặng|hoãn|Chrome kênh đang "
                            r"chạy|việc khác đang dùng|khe .* bận", re.I), "tu_sua",
     "Việc bị hoãn / chờ khe lâu",
     "skill nặng bị để lượt sau liên tục > 6 giờ → uu-tien.json, ky_nang_tu xếp lên đầu; kiểm: có lần xong"),
    ("launcher_ket", re.compile(r"launcher .*kẹt|không Chrome con", re.I), "tu_sua", "Launcher Chrome kẹt",
     "van_hanh.don_launcher_ket mỗi 5 phút (đã có); kiểm: van-hanh.log"),
    ("hl_tam", re.compile(r"hl[=-]?tam|giao diện .*'vi-VN'|ngôn ngữ giao diện", re.I), "cho_phien",
     "Ngôn ngữ giao diện tạm vi chưa trả",
     "phiên DOM kế của kênh tự trả (ngon_ngu_tam.tra); máy theo dõi tuổi vm/logs/hl-tam/<k>.json, > 24 giờ → báo"),
    ("shopapi_tam", re.compile(r"\b50[234]\b|tạm gián đoạn|máy chủ nhận việc rồi bỏ đó|bỏ đó|đặt lại bằng khoá mới|"
                               r"máy chủ treo|chưa trả kết quả|engine_unavailable|[Hh]àng chờ .* quá dài|trục trặc tạm|"
                               r"không có máy chạy việc|Claude Code thoát lỗi|Claude Max hỏng|hết hạn mức|"
                               r"server|ShopAPI.*(lỗi|hỏng)|giọng.*(lỗi|hỏng)|TTS|ElevenLabs|429|rate", re.I), "thu_lai",
     "ShopAPI / giọng / ảnh tạm lỗi",
     "luật chủ: CHỈ thử lại, không hạ chất lượng; bộ chạy đã tự đặt lại khoá mới; báo khi kéo dài > 6 giờ"),
    ("dom_bo_chon", re.compile(r"bộ chọn|selector|không nhận ra ô|TU CHUA|tự chữa|không thấy nút|không tìm thấy (ô|nút)",
                               re.I), "bao",
     "Studio đổi giao diện — bộ chọn DOM hỏng",
     "TU CHUA (vm/logs/tu-chua-dom.jsonl) tự đề xuất bộ chọn mới; tỉ lệ thành công thấp → báo kèm ảnh"),
    ("youtube_chan_ip", re.compile(r"chặn địa chỉ mạng|proxy|Sign in to confirm|bot", re.I), "nguoi",
     "YouTube chặn tải tư liệu từ IP máy",
     "cần proxy IP dân cư (mang-youtube.json) — chỉ người làm được"),
    ("can_xac_minh", re.compile(r"xác minh|verify|tính năng nâng cao|chặn ghim", re.I), "nguoi",
     "Kênh cần xác minh điện thoại (tính năng nâng cao)", "youtube.com/verify — chỉ người làm được"),
    ("ram_thap", re.compile(r"RAM .*(còn|trống)", re.I), "bao", "RAM thấp",
     "báo số liệu + đề nghị nâng phần cứng (không tự hạ quy mô)"),
    ("chua_tai_len", re.compile(r"chưa thấy tải lên|không có video mới|48 giờ không", re.I), "bao",
     "Video chưa tải lên đúng hạn", "tu_kiem phân loại nguyên nhân từ log máy đăng + điều phối"),
)
LOP_TEN = {"tu_sua": "máy tự sửa", "thu_lai": "lỗi tạm — chỉ thử lại", "cho_phien": "tự hồi ở phiên kế (máy kiểm)",
           "nguoi": "chỉ người làm được", "bao": "báo kèm bằng chứng"}


def phan_lop(chu: str) -> str:
    for ma, re_, _lop, _ten, _cach in SO_TAY:
        if re_.search(chu or ""):
            return ma
    return ""


def bai(ma: str) -> Optional[Dict[str, str]]:
    for m, _re, lop, ten, cach in SO_TAY:
        if m == ma:
            return {"ma": m, "lop": lop, "ten": ten, "cach": cach}
    return None


def bang_md(kq: Dict[str, Any], top: int = 15, *, ty_le_tu_chua: str = "") -> str:
    """Bảng chữ ký (top N) + sổ tay → Markdown cho `workspace/chan-doan/loi-lap-lai-<ngày>.md`."""
    d = ["# Lỗi lặp lại — {0} → {1}".format(kq["tu"][:16].replace("T", " "), kq["den"][:16].replace("T", " ")), "",
         "Sinh bằng `python -X utf8 -m core.loi_lap_lai dao` (chỉ đọc log). Mẫu = câu lỗi đã chuẩn hoá (bỏ đường dẫn, "
         "mã, số, tên kênh).", "", "## Nguồn đã đọc", ""]
    d += ["- `{0}`: {1} dòng lỗi".format(k, v) for k, v in sorted(kq["nguon"].items(), key=lambda x: -x[1])]
    d += ["", "## Top {0} chữ ký".format(top), "",
          "| # | Lần | Ngày | Mẫu lỗi | Kênh | Nguồn | Bài · lớp |", "|---|---|---|---|---|---|---|"]
    for i, g in enumerate(kq["nhom"][:top], 1):
        b = bai(g.get("bai") or "")
        d.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            i, g["so"], g["so_ngay"], g["mau"].replace("|", "/")[:110],
            ", ".join("{0}×{1}".format(k, v) for k, v in list(g["kenh"].items())[:3]) or "—",
            ", ".join(g["nguon"]), "{0} · {1}".format(b["ma"], LOP_TEN[b["lop"]]) if b else "chưa có bài"))
    d += ["", "## Sổ tay (phát hiện → sửa an toàn → kiểm lại)", "", "| Bài | Lớp | Sự việc | Cách |", "|---|---|---|---|"]
    d += ["| {0} | {1} | {2} | {3} |".format(m, LOP_TEN[lop], ten, cach) for m, _r, lop, ten, cach in SO_TAY]
    if ty_le_tu_chua:
        d += ["", "## Tự chữa bộ chọn DOM (TU CHUA)", "", ty_le_tu_chua]
    return "\n".join(d) + "\n"


def ty_le_tu_chua(goc: str) -> Dict[str, Any]:
    """Tỉ lệ thành công tự chữa bộ chọn DOM (`vm/logs/tu-chua-dom.jsonl`: ket chua|khong|bo|loai|dat...)."""
    dem: Counter = Counter()
    khoa: Counter = Counter()
    for d in _doc_duoi(os.path.join(goc, "vm", "logs", "tu-chua-dom.jsonl"), 2_000_000):
        try:
            x = json.loads(d)
        except ValueError:
            continue
        if isinstance(x, dict):
            dem[str(x.get("ket"))] += 1
            khoa[str(x.get("khoa"))] += 1
    tong = sum(dem.values())
    dat = sum(v for k, v in dem.items() if k in ("dat", "ok", "sua", "xong"))
    return {"tong": tong, "dat": dat, "ty_le": round(dat / tong, 3) if tong else None, "ket": dict(dem),
            "khoa": dict(khoa.most_common(6))}


# ── chạy các bài tự sửa ───────────────────────────────────────────────────────

def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)


def sua_khoa_chet(goc: str, *, thu: bool = False, bay: Optional[float] = None,
                  pid_con_song: Optional[Callable[[int], bool]] = None) -> List[Dict[str, Any]]:
    """Khoá `{pid, mốc}` trỏ PID chết ≥ `van_hanh.TUOI_KHOA_CHET_GIAY` → xoá an toàn. KHÔNG đụng dấu đang đăng dở
    (`dang-dodang.json` — dấu ấy là bằng chứng cho lượt đăng sau; chỉ lần khởi động máy mới dọn)."""
    from . import van_hanh  # noqa: PLC0415
    ra = van_hanh.don_khoa_khoi_dong(goc, 0.0, bay_gio=bay, thu=True, pid_con_song=pid_con_song)
    can = [m for m in ra if m.get("xoa") is None and "dang-dodang" not in str(m.get("duong"))]
    if thu or not can:
        return [dict(m, xoa=None if thu else False) for m in can]
    from . import ben_bi  # noqa: PLC0415
    song = pid_con_song
    if song is None:
        from . import khe  # noqa: PLC0415
        song = khe.pid_con_song
    kq = []
    for m in can:
        p = m["duong"] if os.path.isabs(m["duong"]) else os.path.join(goc, m["duong"])
        ok, vi_sao = ben_bi.don_khoa_chet_an_toan(p, pid_thay=int(m["pid"]), bay_gio=bay,
                                                  tuoi_toi_thieu_giay=van_hanh.TUOI_KHOA_CHET_GIAY, pid_con_song=song)
        kq.append(dict(m, xoa=bool(ok), ly_do=m["ly_do"] + ("" if ok else " — không xoá: " + vi_sao)))
    return kq


def viec_doi_lau(so: Sequence[Dict[str, Any]], bay: _dt.datetime, gio: float = GIO_DOI_LAU) -> List[Dict[str, Any]]:
    """(skill, kênh) có quyết định "bo_qua"/"hoan" liên tục > `gio` giờ (tính từ lần chờ ĐẦU sau lần xong/hỏng cuối) —
    sổ `workspace/ky-nang/so-chay.jsonl` (thuần)."""
    theo: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for x in so:
        theo[(str(x.get("ma")), str(x.get("kenh") or ""))].append(x)
    ra = []
    for (ma, kenh), ds in theo.items():
        dau = None
        for x in ds:
            q = x.get("quyet")
            if q in ("bo_qua", "hoan"):
                dau = dau or str(x.get("luc") or "")
            else:                     # chạy thật (xong/hỏng), hết điều kiện, tạm dừng, tắt… = không còn đói suất
                dau = None
        if not dau:
            continue
        try:
            t = _dt.datetime.strptime(dau[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        gio_doi = (bay - t).total_seconds() / 3600.0
        if gio_doi >= gio:
            cuoi = ds[-1]
            ra.append({"ma": ma, "kenh": kenh, "tu": dau, "gio": round(gio_doi, 1), "ly_do": str(cuoi.get("ly_do") or "")})
    return sorted(ra, key=lambda x: -x["gio"])


def doc_uu_tien(goc: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(goc, *TEP_UU_TIEN))
    return du if isinstance(du, dict) else {}


def uu_tien_cua(goc: str, ma: str, kenh: str) -> bool:
    """`ky_nang_tu._thu_tu` hỏi: (skill, kênh) đang bị đói suất nặng → xếp lên đầu."""
    return "{0}|{1}".format(ma, kenh or "") in (doc_uu_tien(goc).get("viec") or {})


def sua_viec_doi(goc: str, *, thu: bool = False, bay: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    from . import ky_nang_tu  # noqa: PLC0415
    bay = bay or _dt.datetime.now()
    ds = viec_doi_lau(ky_nang_tu.doc_so(goc), bay)
    if not thu:
        _ghi_json(os.path.join(goc, *TEP_UU_TIEN), {
            "luc": bay.isoformat(timespec="seconds"),
            "viec": {"{0}|{1}".format(x["ma"], x["kenh"]): {"tu": x["tu"], "gio": x["gio"], "ly_do": x["ly_do"][:200]}
                     for x in ds}})
    return ds


def hl_tam_cu(goc: str, *, bay: Optional[float] = None, gio: float = GIO_HL_TAM) -> List[Dict[str, Any]]:
    """Ngôn ngữ giao diện tạm còn sót: `vm/logs/hl-tam/<k>.json` (tuổi giờ). Quá `gio` → cần báo."""
    bay = time.time() if bay is None else bay
    ra = []
    for p in glob.glob(os.path.join(goc, "vm", "logs", "hl-tam", "*.json")):
        tuoi = (bay - os.path.getmtime(p)) / 3600.0
        ra.append({"kenh": os.path.basename(p)[:-5], "gio": round(tuoi, 1), "qua_han": tuoi >= gio})
    return ra


# ── lượt kẹt (L3 không bỏ vì tưởng lỗi phía ShopAPI) ─────────────────────────

#: Lượt tự phục hồi ít nhất ngần này lần mới xét là "kẹt".
SO_LAN_KET = 10
#: Cùng cảnh "không làm được clip thật — cần người xem": báo sau ngần này giờ, bỏ lượt sau ngần này giờ.
GIO_BAO_KET, GIO_BO_KET = 24.0, 72.0
#: Lỗi tạm phía ShopAPI (luật chủ: chỉ thử lại) kéo dài ngần này giờ → báo (không bỏ).
GIO_BAO_SHOPAPI = 72.0
_RE_NGUON_MAT_LOG = re.compile(r"no longer available|Video unavailable|uploader has closed|has been removed", re.I)
_RE_CLIP_KET = re.compile(r"không làm được clip thật|cần người xem", re.I)
_RE_LOI_THOAI = re.compile(r"không lấy được lời thoại", re.I)


def trang_xem_hong(vid: str, tai: Optional[Callable[[str], Optional[bytes]]] = None) -> Optional[bool]:
    """Trang xem CÔNG KHAI của video: True = YouTube báo lỗi (gỡ / riêng tư / tài khoản đóng — playabilityStatus
    ERROR | LOGIN_REQUIRED | UNPLAYABLE); False = phát được; None = không đọc được (mạng)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(vid or "")):
        return None
    if tai is None:
        def tai(url: str) -> Optional[bytes]:
            try:
                from .mang_an_toan import mo_url  # noqa: PLC0415
                with mo_url(url, cho=20, headers={"Accept-Language": "en"}) as ph:
                    return ph.read()
            except Exception:  # noqa: BLE001
                return None
    du = tai("https://www.youtube.com/watch?v=" + vid)
    if not du:
        return None
    m = re.search(r'"playabilityStatus":\{"status":"([A-Z_]+)"', du.decode("utf-8", "replace"))
    if not m:
        return None
    return m.group(1) in ("ERROR", "LOGIN_REQUIRED", "UNPLAYABLE")


def _log_noi_nguon_mat(goc: str, kenh: str, vid: str) -> bool:
    for p in (os.path.join(goc, "workspace", "tu-chay", "dieu-phoi-{0}.log".format(kenh)),
              os.path.join(goc, "workspace", "tu-chay", "tu-chay.log")):
        for d in _doc_duoi(p, 1_500_000):
            if vid in d and _RE_NGUON_MAT_LOG.search(d):
                return True
    return False


def luot_ket(goc: str, *, bay: Optional[float] = None, so_ngay: int = 7) -> List[Dict[str, Any]]:
    """Lượt CHƯA bỏ, chưa xong, tự phục hồi ≥ `SO_LAN_KET` lần — từ sổ `CHANNEL/<k>/tu-chay/<ngày>.json` (chỉ đọc).
    Mỗi mục {kenh, ngay, ma_luot, so_lan, gio, loi, nguon, lop: nguon_mat?|clip_ket|shopapi}."""
    bay = time.time() if bay is None else bay
    try:
        from .ky_nang import _cac_kenh  # noqa: PLC0415
        kenh_ds = _cac_kenh(goc)
    except Exception:  # noqa: BLE001
        kenh_ds = []
    ra = []
    for kenh in kenh_ds:
        for i in range(so_ngay):
            ngay = (_dt.date.fromtimestamp(bay) - _dt.timedelta(days=i)).isoformat()
            du = _doc_json(os.path.join(goc, "CHANNEL", kenh, "tu-chay", ngay + ".json"))
            for r in (du.get("runs") or []) if isinstance(du, dict) else []:
                if not isinstance(r, dict) or r.get("bo") or r.get("tham_chieu_ma_luot") or r.get("ok") is True:
                    continue
                ph = r.get("phuc_hoi") if isinstance(r.get("phuc_hoi"), dict) else {}
                so_lan = int(ph.get("so_lan") or 0)
                if so_lan < SO_LAN_KET:
                    continue
                sx = r.get("san_xuat") if isinstance(r.get("san_xuat"), dict) else {}
                loi = str(sx.get("loi_dung") or sx.get("loi") or "")
                try:
                    gio = (bay - float(ph.get("lan_dau_luc"))) / 3600.0
                except (TypeError, ValueError):
                    gio = 0.0
                lop = ("nguon_mat?" if _RE_LOI_THOAI.search(loi) else "clip_ket" if _RE_CLIP_KET.search(loi)
                       else "shopapi")
                ra.append({"kenh": kenh, "ngay": ngay, "ma_luot": str(r.get("ma_luot") or ""), "so_lan": so_lan,
                           "gio": round(gio, 1), "loi": loi[:300], "nguon": str((r.get("nguon") or {}).get("ma") or ""),
                           "lop": lop})
    return ra


def _bo_luot(goc: str, kenh: str, ngay: str, ma_luot: str, ly_do: str) -> Tuple[bool, str]:
    """Bỏ lượt ĐÚNG đường L3 của `core.tu_chay` (cờ `bo` + tệp BO-VI + nhả nguồn + báo `nhac`) — GIỮ khoá kênh lúc ghi
    sổ để không đè lên một lượt đang chạy. Không xoá tệp nào."""
    from . import tu_chay  # noqa: PLC0415
    ok, ly = tu_chay._giu_khoa(goc, kenh)  # noqa: SLF001
    if not ok:
        return False, "kênh đang chạy lượt ({0}) — để lần sau".format(ly)
    try:
        bc = tu_chay._doc_bao_cao_ngay(goc, kenh, ngay)  # noqa: SLF001
        run = next((r for r in bc.get("runs") or [] if str(r.get("ma_luot")) == ma_luot
                    and not r.get("tham_chieu_ma_luot")), None)
        if run is None or run.get("bo"):
            return False, "không còn lượt cần bỏ"
        tu_chay._bo_luot_qua_han(goc, kenh, run, bc, ngay, ly_do, lambda s: None)  # noqa: SLF001
        try:
            tu_chay._go_dau_cho_engine(goc, kenh, run)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            pass
        return True, "đã bỏ lượt"
    finally:
        tu_chay._nha_khoa(goc, kenh)  # noqa: SLF001


def sua_luot_ket(goc: str, *, thu: bool = False, bay: Optional[float] = None,
                 kiem_nguon: Optional[Callable[[str], Optional[bool]]] = None,
                 bo_luot: Optional[Callable[..., Tuple[bool, str]]] = None) -> List[Dict[str, Any]]:
    """Mỗi lượt kẹt → quyết: `bo` (nguồn mất có hai bằng chứng | clip kẹt ≥ 72 giờ) · `bao` · `cho` (chỉ thử lại)."""
    kiem_nguon = kiem_nguon or trang_xem_hong
    bo_luot = bo_luot or _bo_luot
    ra = []
    for x in luot_ket(goc, bay=bay):
        x = dict(x, quyet="cho", ly_do="")
        if x["lop"] == "nguon_mat?":
            mat = kiem_nguon(x["nguon"]) if x["nguon"] else None
            log_noi = _log_noi_nguon_mat(goc, x["kenh"], x["nguon"]) if x["nguon"] else False
            if mat and log_noi:
                x.update(lop="nguon_mat", quyet="bo", ly_do="video tư liệu {0} đã bị gỡ (yt-dlp: unavailable + trang "
                         "xem công khai báo lỗi) — nguồn không bao giờ quay lại".format(x["nguon"]))
            else:
                x.update(lop="shopapi" if mat is False else "nguon_mat?", quyet="bao" if x["gio"] >= GIO_BAO_KET else "cho",
                         ly_do="không lấy được lời thoại nguồn {0} ({1})".format(
                             x["nguon"], "nguồn vẫn phát được — nghi IP bị chặn" if mat is False else "chưa đủ bằng chứng"))
        elif x["lop"] == "clip_ket":
            if x["gio"] >= GIO_BO_KET:
                x.update(quyet="bo", ly_do="kẹt {0:.0f} giờ / {1} lần ở cùng khâu clip («không làm được clip thật») — "
                         "không phải lỗi tạm; bỏ lượt để kênh làm video mới (không hạ chất lượng)".format(
                             x["gio"], x["so_lan"]))
            elif x["gio"] >= GIO_BAO_KET:
                x.update(quyet="bao", ly_do="kẹt {0:.0f} giờ ở khâu clip — tự bỏ lượt khi đủ {1:.0f} giờ".format(
                    x["gio"], GIO_BO_KET))
        elif x["gio"] >= GIO_BAO_SHOPAPI:
            x.update(quyet="bao", ly_do="lỗi tạm phía ShopAPI kéo dài {0:.0f} giờ — chỉ thử lại (luật chủ)".format(x["gio"]))
        if x["quyet"] == "bo" and not thu:
            ok, ly = bo_luot(goc, x["kenh"], x["ngay"], x["ma_luot"], "[tự kiểm] " + x["ly_do"])
            x.update(da_bo=ok, ket=ly)
            try:
                from . import nao_bo_phan  # noqa: PLC0415
                nao_bo_phan.ghi(goc, "dieu-phoi", "sua" if ok else "loi", kenh=x["kenh"],
                                ma_goi="{0}-{1}".format(x["kenh"], x["ma_luot"]),
                                noi_dung="tự kiểm bỏ lượt kẹt {0}/{1}: {2} — {3}".format(
                                    x["kenh"], x["ma_luot"], x["ly_do"], ly), nguon="tu_kiem",
                                khoa="tu-kiem:bo-luot:{0}:{1}:{2}".format(x["kenh"], x["ma_luot"], ok))
            except Exception:  # noqa: BLE001
                pass
        ra.append(x)
    return ra


def chay_so_tay(goc: str, *, thu: bool = False) -> Dict[str, Any]:
    """Các bài `tu_sua` + theo dõi `cho_phien`. Không bao giờ ném (gác tổng gọi mỗi 15 phút)."""
    ra: Dict[str, Any] = {"luc": _dt.datetime.now().isoformat(timespec="seconds")}
    for ten, ham in (("khoa_chet", lambda: sua_khoa_chet(goc, thu=thu)),
                     ("viec_doi", lambda: sua_viec_doi(goc, thu=thu)),
                     ("luot_ket", lambda: sua_luot_ket(goc, thu=thu)),
                     ("hl_tam", lambda: hl_tam_cu(goc))):
        try:
            ra[ten] = ham()
        except Exception as loi:  # noqa: BLE001
            ra[ten] = {"loi": str(loi)[:200]}
    if not thu:
        try:
            _ghi_json(os.path.join(goc, *TEP_SO_TAY), ra)
        except OSError:
            pass
    return ra


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.loi_lap_lai")
    p.add_argument("lenh", choices=("dao", "so-tay"))
    p.add_argument("--ngay", type=int, default=NGAY_DAO)
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p.add_argument("--md", default="")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--thu", action="store_true")
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    if a.lenh == "so-tay":
        print(json.dumps(chay_so_tay(goc, thu=a.thu), ensure_ascii=False, indent=1))
        return 0
    kq = dao(goc, ngay=a.ngay)
    tc = ty_le_tu_chua(goc)
    dong_tc = "{0} lần ghi · đạt {1} ({2}) · kết: {3} · khoá: {4}".format(
        tc["tong"], tc["dat"], "-" if tc["ty_le"] is None else "{0:.0%}".format(tc["ty_le"]),
        json.dumps(tc["ket"], ensure_ascii=False), json.dumps(tc["khoa"], ensure_ascii=False))
    md = bang_md(kq, a.top, ty_le_tu_chua=dong_tc)
    if a.md:
        os.makedirs(os.path.dirname(os.path.abspath(a.md)), exist_ok=True)
        with io.open(a.md, "w", encoding="utf-8") as tep:
            tep.write(md)
        print("đã ghi", a.md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
