"""Phần dùng chung của phòng thí nghiệm: đường dẫn, đọc/ghi nguyên tử, số, ngày giờ.

Không mạng, không Qt. Mọi hàm đọc hỏng → giá trị rỗng, không ném ra nơi gọi.
"""

from __future__ import annotations

import csv
import datetime as _dt
import gzip
import io
import json
import math
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

#: Thư mục dữ liệu riêng của MỘT kênh: `CHANNEL/<k>/phong-thi-nghiem/` (kho đặc trưng hằng ngày, thống kê vũ trụ,
#: kết quả AI). Thư mục chung mọi kênh: `workspace/phong-thi-nghiem/` (sổ giả thuyết, nhật ký bóng, bảng xếp hạng).
THU_MUC = "phong-thi-nghiem"
TEP_GIA_THUYET = "gia-thuyet.json"
TEP_BANG_XEP_HANG = "bang-xep-hang.json"
TIEN_TO_NHAT_KY = "nhat-ky-bong-"

#: Số giây một ngày.
NGAY_GIAY = 86400.0


#: Biến môi trường: gốc RIÊNG để GHI dữ liệu phòng thí nghiệm (chạy thử không đụng cây thật; đọc vẫn từ `goc`).
BIEN_GOC_GHI = "MYTOOL_PTN_GHI"


def goc_ghi(goc: str) -> str:
    return os.environ.get(BIEN_GOC_GHI) or goc


def thu_muc_chung(goc: str) -> str:
    return os.path.join(goc_ghi(goc), "workspace", THU_MUC)


def thu_muc_kenh(goc: str, kenh: str) -> str:
    return os.path.join(goc_ghi(goc), "CHANNEL", kenh, THU_MUC)


def thu_muc_nghien_cuu(goc: str, kenh: str) -> str:
    return os.path.join(goc, "CHANNEL", kenh, "nghien-cuu")


# ── số / chữ ────────────────────────────────────────────────────────────────

def so(x: Any) -> Optional[float]:
    """Số từ ô bảng ("409000", "1,2", "30.2%") — rỗng/hỏng/vô cực → None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    chu = str(x).strip().replace("%", "")
    if not chu:
        return None
    if "," in chu and "." not in chu and re.fullmatch(r"-?\d+,\d+", chu):
        chu = chu.replace(",", ".")
    else:
        chu = chu.replace(",", "")
    try:
        v = float(chu)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def phut(chu: Any) -> Optional[float]:
    """"15:09" / "1:02:03" → phút; hỏng → None."""
    phan = [p.strip() for p in str(chu or "").strip().split(":")]
    if not phan or not all(p.isdigit() for p in phan):
        return None
    giay = 0
    for p in phan:
        giay = giay * 60 + int(p)
    return giay / 60.0


def lam_tron(x: Optional[float], le: int = 3) -> Optional[float]:
    if x is None:
        return None
    try:
        return round(float(x), le)
    except (TypeError, ValueError):
        return None


# ── ngày giờ (ngày theo giờ MÁY — cùng cách tên tệp sổ `tu-chay/<ngày>.json`, `sao-luu/content-<ngày>.csv`) ──

def ngay_cua(d: Any) -> Optional[_dt.date]:
    if isinstance(d, _dt.datetime):
        return d.date()
    if isinstance(d, _dt.date):
        return d
    try:
        return _dt.date.fromisoformat(str(d or "").strip()[:10])
    except ValueError:
        return None


def cong_ngay(ngay: str, n: int) -> str:
    d = ngay_cua(ngay)
    return (d + _dt.timedelta(days=n)).isoformat() if d else ""


def epoch_luc(chu: Any) -> Optional[float]:
    """"2026-10-11 05:25" (giờ máy) / ISO → epoch; hỏng → None."""
    s = str(chu or "").strip().replace("T", " ")
    if not s:
        return None
    for dang, dai in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
        try:
            return time.mktime(_dt.datetime.strptime(s[:dai], dang).timetuple())
        except ValueError:
            continue
    return None


def moc_cuoi_ngay(ngay: str) -> float:
    """Epoch lúc 00:00 (giờ máy) của ngày SAU `ngay` — "thông tin tới hết ngày `ngay`"."""
    d = ngay_cua(ngay)
    if d is None:
        return time.time()
    sau = d + _dt.timedelta(days=1)
    return time.mktime(_dt.datetime(sau.year, sau.month, sau.day).timetuple())


def epoch_ngay_dang(chu: Any) -> Optional[float]:
    """`Ngày đăng` chỉ có NGÀY → mốc giữa ngày (12:00 UTC, như `cong_thuc_vph._tuoi_gio`)."""
    d = ngay_cua(chu)
    if d is None:
        return None
    return _dt.datetime(d.year, d.month, d.day, 12, 0, tzinfo=_dt.timezone.utc).timestamp()


def hom_nay() -> str:
    return _dt.date.today().isoformat()


def luc_iso(t: Optional[float] = None) -> str:
    return _dt.datetime.fromtimestamp(t if t is not None else time.time()).strftime("%Y-%m-%dT%H:%M:%S")


# ── tệp ─────────────────────────────────────────────────────────────────────

def doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def ghi_nguyen_tu(duong: str, noi_dung: str) -> str:
    """Ghi tệp tạm rồi `os.replace` (Windows: thử lại khi tệp đang mở)."""
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(noi_dung)
    for lan in range(5):
        try:
            os.replace(tam, duong)
            break
        except PermissionError:
            if lan == 4:
                raise
            time.sleep(0.2 * (lan + 1))
    return duong


def ghi_json(duong: str, du: Any) -> str:
    return ghi_nguyen_tu(duong, json.dumps(du, ensure_ascii=False, indent=1) + "\n")


def doc_csv(duong: str) -> List[Dict[str, str]]:
    """Mọi dòng của một CSV (utf-8-sig) thành dict theo tên cột; hỏng → []."""
    try:
        with io.open(duong, encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except (OSError, ValueError, csv.Error):
        return []


def ghi_csv_gz(duong: str, cot: Sequence[str], hang: Iterable[Dict[str, Any]]) -> str:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tmp"
    with gzip.open(tam, "wt", encoding="utf-8", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(cot), extrasaction="ignore")
        w.writeheader()
        for r in hang:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cot})
    os.replace(tam, duong)
    return duong


def doc_csv_gz(duong: str) -> List[Dict[str, str]]:
    try:
        with gzip.open(duong, "rt", encoding="utf-8", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except (OSError, ValueError, EOFError, csv.Error):
        return []


def them_dong(duong: str, dong: Iterable[Dict[str, Any]]) -> int:
    """Nối các dòng JSON vào cuối tệp jsonl (chỉ nối — không sửa dòng cũ). Trả số dòng đã nối."""
    ds = [json.dumps(d, ensure_ascii=False, separators=(",", ":")) for d in dong]
    if not ds:
        return 0
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with io.open(duong, "a", encoding="utf-8", newline="\n") as tep:
        tep.write("\n".join(ds) + "\n")
    return len(ds)


def doc_jsonl(duong: str) -> List[Dict[str, Any]]:
    ra: List[Dict[str, Any]] = []
    try:
        with io.open(duong, encoding="utf-8") as tep:
            for dong in tep:
                dong = dong.strip()
                if not dong:
                    continue
                try:
                    x = json.loads(dong)
                except ValueError:
                    continue  # dòng đứt (máy tắt giữa lúc ghi) — bỏ, không làm hỏng cả sổ
                if isinstance(x, dict):
                    ra.append(x)
    except OSError:
        pass
    return ra


def doc_yaml_kenh(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        from ..kenh import doc_yaml  # noqa: PLC0415

        return doc_yaml(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml")) or {}
    except Exception:  # noqa: BLE001
        return {}


def trung_vi(xs: Sequence[float]) -> Optional[float]:
    ds = sorted(x for x in xs if x is not None)
    if not ds:
        return None
    n = len(ds)
    return ds[n // 2] if n % 2 else (ds[n // 2 - 1] + ds[n // 2]) / 2.0


def phan_vi(xs: Sequence[float], p: float) -> Optional[float]:
    ds = sorted(x for x in xs if x is not None)
    if not ds:
        return None
    vt = (len(ds) - 1) * max(0.0, min(1.0, p))
    i = int(math.floor(vt))
    j = min(len(ds) - 1, i + 1)
    return ds[i] + (ds[j] - ds[i]) * (vt - i)
