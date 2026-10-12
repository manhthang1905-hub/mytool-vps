"""SỐ CẤP KÊNH từ bản chụp Studio — sub TRỌN ĐỜI, chuỗi ngày, tỉ lệ traffic (12/10/2026).

═══ VÌ SAO ═══ (`workspace/chan-doan/{nao-vong-hoc,view-giam}-2026-10-12.md`)

`kenh-theo-ngay.csv` (nguồn của `core.ypp` cũ) chỉ có TỔNG CỬA SỔ 28 NGÀY TRƯỢT: "đăng ký" là sub MỚI trong 28 ngày,
nên kênh đã qua 28 ngày tuổi bị báo THẤP hơn thật (một kênh 605 "sub" trong khi Studio ghi 713 trọn đời), và con số
TỰ TỤT khi ngày nổ cũ rời cửa sổ — báo cáo ngày đọc thành "đang giảm". Gói raw của trang Tổng quan lại có sẵn số trọn
đời: thẻ thời gian thực `latestActivityCardData.lifetimeSubsData` (số "チャンネル登録者数" hiện tại). Cùng gói có chuỗi
NGÀY 28 ngày (`keyMetricCardData…mainSeries.datums`) — đủ để tính view/ngày 7 ngày và xu hướng, không cần đoán từ tổng
trượt — và bảng nguồn traffic cấp kênh (`tong-quan.json: traffic`).

Thư mục chụp cấp kênh: `CHANNEL/<k>/chi-so/kenh/{kenh,tay}-YYYYMMDD[-HHMM]/` (`raw/*.json[.gz]` + `tong-quan.json`).
Thư mục khác trong `chi-so/kenh/` (vd mốc video lạc chỗ "22h") bị bỏ. Chỉ đọc đĩa, không mạng; hỏng → None/{}.

    python -m core.chi_so_kenh [--kenh K]        # in sub trọn đời, view/ngày 7d, % traffic đề xuất (chỉ đọc)
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import statistics
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

_RE_THU_MUC = re.compile(r"^(kenh|tay)-(\d{8})(?:-(\d{4}))?$")
#: Số thư mục chụp mới nhất được đọc khi tìm một số (mỗi thư mục vài gói raw, ~0,1 giây).
SO_THU_MUC_TOI_DA = 12
#: Ngày (giờ Mỹ của Studio) mới nhất trong MỘT gói thường chưa trọn (Studio trễ 1–2 ngày) — bị bỏ trừ khi một gói
#: muộn hơn chứa ngày đó ở vị trí chưa phải cuối.
BO_NGAY_CUOI = True


def _so(x: Any) -> Optional[float]:
    if x is None or isinstance(x, bool):
        return None
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


_BO_NHO: Dict[Tuple[str, str, str, Any], Tuple[float, Any]] = {}


def _nho(ham: Any) -> Any:
    """Nhớ kết quả theo (hàm, gốc, kênh, tham số) + mtime thư mục `chi-so/kenh` (bản chụp mới → tính lại) — giao diện
    gọi mỗi lần làm mới bảng, đọc gói raw lại mỗi lần là phí."""
    def boc(goc: str, kenh: str, *vi_tri: Any, **kw: Any) -> Any:
        try:
            m = os.path.getmtime(os.path.join(goc, "CHANNEL", kenh, "chi-so", "kenh"))
            moi = thu_muc_chup(goc, kenh)[:1]
            if moi:
                m += os.path.getmtime(os.path.join(moi[0][0], "raw")) if os.path.isdir(
                    os.path.join(moi[0][0], "raw")) else 0.0
        except OSError:
            m = 0.0
        khoa = (ham.__name__, goc, kenh, (vi_tri, tuple(sorted(kw.items()))))
        cu = _BO_NHO.get(khoa)
        if cu is not None and cu[0] == m:
            return cu[1]
        ra = ham(goc, kenh, *vi_tri, **kw)
        if len(_BO_NHO) > 500:
            _BO_NHO.clear()
        _BO_NHO[khoa] = (m, ra)
        return ra
    boc.__name__ = ham.__name__
    boc.__doc__ = ham.__doc__
    boc.goc = ham  # type: ignore[attr-defined]  — bản không nhớ (test)
    return boc


def thu_muc_chup(goc: str, kenh: str) -> List[Tuple[str, str]]:
    """`[(đường thư mục, "YYYY-MM-DD")]` các bản chụp CẤP KÊNH, MỚI → CŨ (cùng ngày: giờ muộn trước, `kenh-` trước
    `tay-`)."""
    base = os.path.join(goc, "CHANNEL", kenh, "chi-so", "kenh")
    try:
        ten = os.listdir(base)
    except OSError:
        return []
    ds = []
    for t in ten:
        m = _RE_THU_MUC.match(t)
        if not m or not os.path.isdir(os.path.join(base, t)):
            continue
        d = m.group(2)
        ds.append(((d, m.group(3) or "2400", 1 if m.group(1) == "kenh" else 0),
                   os.path.join(base, t), "{0}-{1}-{2}".format(d[:4], d[4:6], d[6:])))
    ds.sort(key=lambda x: x[0], reverse=True)
    return [(p, n) for _k, p, n in ds]


def _goi_raw(thu_muc: str) -> Iterable[Tuple[str, Any]]:
    from .chi_so_ytb import kho_raw  # noqa: PLC0415

    raw = os.path.join(thu_muc, "raw")
    if not os.path.isdir(raw):
        return
    for f in kho_raw.liet_ke(raw, "*"):
        ten = os.path.basename(f)
        if "get_cards" not in ten and "get_screen" not in ten:
            continue
        try:
            yield f, kho_raw.doc_json(f)
        except Exception:  # noqa: BLE001 — một gói hỏng không chặn gói khác
            continue


def _the(goi: Any) -> List[Dict[str, Any]]:
    try:
        ds = ((goi or {}).get("response") or {}).get("cards") or []
    except AttributeError:
        return []
    return [c for c in ds if isinstance(c, dict)]


def sub_tu_goi(goi: Any) -> Optional[int]:
    """Sub TRỌN ĐỜI trong MỘT gói raw (thẻ thời gian thực), None nếu gói không có."""
    for c in _the(goi):
        ls = (c.get("latestActivityCardData") or {}).get("lifetimeSubsData")
        if not isinstance(ls, dict):
            continue
        try:
            v = ls["metricColumns"][0]["counts"]["values"][0]
        except (KeyError, IndexError, TypeError):
            continue
        so = _so(v)
        if so is not None and so >= 0:
            return int(so)
    return None


@_nho
def sub_tron_doi(goc: str, kenh: str, *, toi_da: int = SO_THU_MUC_TOI_DA) -> Dict[str, Any]:
    """`{"so": int|None, "ngay": "YYYY-MM-DD"|"", "nguon": "studio_thoi_gian_thuc"|""}` — số sub TRỌN ĐỜI mới nhất
    (Studio, thẻ thời gian thực của trang Tổng quan). Chưa chụp được → `so` None (người đọc phải thấy "chưa rõ")."""
    for thu, ngay in thu_muc_chup(goc, kenh)[:toi_da]:
        for _f, goi in _goi_raw(thu):
            so = sub_tu_goi(goi)
            if so is not None:
                return {"so": so, "ngay": ngay, "nguon": "studio_thoi_gian_thuc"}
    return {"so": None, "ngay": "", "nguon": ""}


@_nho
def chuoi_sub_tron_doi(goc: str, kenh: str, *, toi_da: int = 30) -> List[Tuple[str, int]]:
    """`[(ngày, sub trọn đời)]` CŨ → MỚI, một số mỗi ngày (bản chụp muộn nhất của ngày) — để tính tốc độ tăng THẬT
    (hiệu hai số trọn đời), không suy từ tổng 28 ngày trượt."""
    theo_ngay: Dict[str, int] = {}
    for thu, ngay in thu_muc_chup(goc, kenh)[:toi_da]:
        if ngay in theo_ngay:
            continue
        for _f, goi in _goi_raw(thu):
            so = sub_tu_goi(goi)
            if so is not None:
                theo_ngay[ngay] = so
                break
    return sorted(theo_ngay.items())


def toc_do_sub(chuoi: List[Tuple[str, int]], *, so_ngay: int = 7) -> Optional[float]:
    """Sub/ngày từ chuỗi trọn đời: (số cuối − số ở ~`so_ngay` ngày trước) / số ngày. < 2 điểm → None."""
    if len(chuoi) < 2:
        return None
    cuoi_ngay, cuoi = chuoi[-1]
    d1 = _dt.date.fromisoformat(cuoi_ngay)
    truoc = [(n, s) for n, s in chuoi[:-1] if (d1 - _dt.date.fromisoformat(n)).days <= so_ngay]
    n0, s0 = (truoc[0] if truoc else chuoi[-2])
    ngay = (d1 - _dt.date.fromisoformat(n0)).days
    if ngay <= 0:
        return None
    return max(0.0, (cuoi - s0) / float(ngay))


def _datums(goi: Any, metric: str) -> List[Tuple[str, float]]:
    """Chuỗi ngày `[(YYYY-MM-DD giờ Mỹ, giá trị)]` của THẺ ĐẦU TIÊN có chỉ số `metric` trong gói (gói cấp kênh có
    nhiều thẻ cùng tên khác cửa sổ — thẻ đầu là cửa sổ 28 ngày của trang)."""
    for c in _the(goi):
        km = c.get("keyMetricCardData")
        if not isinstance(km, dict):
            continue
        for t in km.get("keyMetricTabs") or []:
            pc = (t or {}).get("primaryContent") or {}
            if pc.get("metric") != metric:
                continue
            ra = []
            for d in ((pc.get("mainSeries") or {}).get("datums") or []):
                x, y = _so((d or {}).get("x")), _so((d or {}).get("y"))
                if x is None or y is None:
                    continue
                # x = mốc nửa đêm giờ Thái Bình Dương (ms) → +12h rồi lấy ngày UTC là đúng ngày Studio ghi.
                ngay = _dt.datetime.utcfromtimestamp(x / 1000.0 + 12 * 3600).date().isoformat()
                ra.append((ngay, y))
            if ra:
                return ra
    return []


@_nho
def chuoi_ngay(goc: str, kenh: str, metric: str = "EXTERNAL_VIEWS", *, so_goi: int = 4) -> Dict[str, float]:
    """`{ngày: giá trị}` từ `so_goi` bản chụp cấp kênh mới nhất có thẻ chỉ số (gộp: bản MỚI ghi đè bản cũ). Ngày cuối
    của mỗi bản bị bỏ (Studio chưa chốt — `BO_NGAY_CUOI`) trừ khi bản muộn hơn có ngày đó."""
    ban: List[List[Tuple[str, float]]] = []
    for thu, _ngay in thu_muc_chup(goc, kenh)[:SO_THU_MUC_TOI_DA]:
        for _f, goi in _goi_raw(thu):
            ds = _datums(goi, metric)
            if ds:
                ban.append(ds)
                break
        if len(ban) >= so_goi:
            break
    ra: Dict[str, float] = {}
    for ds in reversed(ban):          # cũ → mới: bản mới ghi đè
        dung = ds[:-1] if (BO_NGAY_CUOI and len(ds) > 1) else ds
        for n, y in dung:
            ra[n] = y
    return dict(sorted(ra.items()))


@_nho
def chuoi_dai(goc: str, kenh: str, metric: str, *, so_thu_muc: int = 80, cach_ngay: int = 20) -> Dict[str, float]:
    """Chuỗi ngày DÀI (tới vài tháng) của `metric`: gộp các bản chụp cấp kênh cách nhau ~`cach_ngay` ngày (mỗi bản
    phủ 28 ngày) — đọc ít gói mà vẫn phủ hết lịch sử đã chụp. Bản mới ghi đè bản cũ; ngày cuối của mỗi bản bị bỏ."""
    ban: List[List[Tuple[str, float]]] = []
    moc_cu: Optional[_dt.date] = None
    for thu, ngay in thu_muc_chup(goc, kenh)[:so_thu_muc]:
        d = _dt.date.fromisoformat(ngay)
        if moc_cu is not None and len(ban) >= 2 and d > moc_cu - _dt.timedelta(days=cach_ngay):
            continue
        for _f, goi in _goi_raw(thu):
            ds = _datums(goi, metric)
            if ds:
                ban.append(ds)
                moc_cu = d
                break
    ra: Dict[str, float] = {}
    for ds in reversed(ban):
        for n, y in (ds[:-1] if (BO_NGAY_CUOI and len(ds) > 1) else ds):
            ra[n] = y
    return dict(sorted(ra.items()))


def gio_xem(goc: str, kenh: str, *, so_ngay: int = 365) -> Dict[str, Any]:
    """Giờ xem từ CHUỖI NGÀY Studio đã chụp (không phải tổng 28 ngày trượt): `{gio_365, tu, den, n_ngay, toc_7}` —
    `gio_365` = tổng ≤ `so_ngay` ngày gần nhất có số (Studio tính cả video riêng tư/đã xoá — ước, không phải số YPP
    chính thức), `toc_7` = giờ/ngày trung bình 7 ngày chốt gần nhất. Không có chuỗi → các số None."""
    c = chuoi_dai(goc, kenh, "EXTERNAL_WATCH_TIME")
    ngay = sorted(c)
    ra: Dict[str, Any] = {"gio_365": None, "tu": "", "den": "", "n_ngay": 0, "toc_7": None}
    if not ngay:
        return ra
    den = _dt.date.fromisoformat(ngay[-1])
    dung = [n for n in ngay if (den - _dt.date.fromisoformat(n)).days < so_ngay]
    ra.update(gio_365=round(sum(c[n] for n in dung) / 3.6e6, 1), tu=dung[0], den=ngay[-1], n_ngay=len(dung))
    cuoi = [c[n] for n in ngay[-7:]]
    if len(cuoi) >= 3:
        ra["toc_7"] = round(sum(cuoi) / len(cuoi) / 3.6e6, 2)
    return ra


def view_ngay(goc: str, kenh: str) -> Dict[str, Any]:
    """`{tb7, tb7_truoc, xu_huong, ngay_cuoi, n}` — view/ngày trung bình 7 ngày Studio đã chốt gần nhất, 7 ngày trước
    đó, xu hướng = tb7 / tb7_truoc (None khi thiếu). Studio trễ 1–2 ngày: `ngay_cuoi` = ngày chốt mới nhất."""
    c = chuoi_ngay(goc, kenh, "EXTERNAL_VIEWS")
    ngay = sorted(c)
    ra: Dict[str, Any] = {"tb7": None, "tb7_truoc": None, "xu_huong": None, "ngay_cuoi": ngay[-1] if ngay else "",
                          "n": len(ngay)}
    if len(ngay) >= 3:
        cuoi = [c[n] for n in ngay[-7:]]
        ra["tb7"] = sum(cuoi) / len(cuoi)
        truoc = [c[n] for n in ngay[-14:-7]]
        if len(truoc) >= 3:
            ra["tb7_truoc"] = sum(truoc) / len(truoc)
            if ra["tb7_truoc"] > 0:
                ra["xu_huong"] = ra["tb7"] / ra["tb7_truoc"]
    return ra


@_nho
def ti_le_traffic(goc: str, kenh: str, *, so_ban: int = 7) -> Dict[str, Any]:
    """`{de_xuat, trang_chu, tim_kiem, n, ngay}` — % traffic cấp kênh (TRUNG VỊ của ≤ `so_ban` bản chụp cấp kênh mới
    nhất có bảng traffic: một bản lẻ dao động mạnh, vd 92% → 49% trong một ngày). Không có → các số None, n 0."""
    ds: Dict[str, List[float]] = {"related": [], "browse": [], "search": []}
    ngay = ""
    n = 0
    for thu, nd in thu_muc_chup(goc, kenh)[:SO_THU_MUC_TOI_DA * 2]:
        tq = _doc_json(os.path.join(thu, "tong-quan.json"))
        tr = (tq or {}).get("traffic_chuan") or (tq or {}).get("traffic") if isinstance(tq, dict) else None
        if not isinstance(tr, dict) or not tr:
            continue
        n += 1
        ngay = ngay or nd
        for k in ds:
            v = _so(tr.get(k))
            ds[k].append(v if v is not None else 0.0)
        if n >= so_ban:
            break

    def tv(x: List[float]) -> Optional[float]:
        return round(statistics.median(x), 1) if x else None

    return {"de_xuat": tv(ds["related"]), "trang_chu": tv(ds["browse"]), "tim_kiem": tv(ds["search"]), "n": n,
            "ngay": ngay}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.chi_so_kenh")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p.add_argument("--kenh", action="append", default=[])
    a = p.parse_args(argv)
    ks = a.kenh
    if not ks:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        ks = list(liet_ke_kenh(a.goc))
    for k in ks:
        s = sub_tron_doi(a.goc, k)
        v = view_ngay(a.goc, k)
        t = ti_le_traffic(a.goc, k)
        print("{0}: sub trọn đời {1} ({2}) · view/ngày 7d {3} (trước {4}) · đề xuất {5}% (n {6})".format(
            k, s["so"] if s["so"] is not None else "chưa rõ", s["ngay"] or "-",
            "?" if v["tb7"] is None else round(v["tb7"]), "?" if v["tb7_truoc"] is None else round(v["tb7_truoc"]),
            t["de_xuat"], t["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
