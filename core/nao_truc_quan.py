"""TRANG «NÃO» của Trung tâm trực quan (06/10/2026) — cho chủ THẤY bộ não suy nghĩ, đoán, bị chấm và học.

CHỈ ĐỌC: sổ hành động `nao/hanh-dong.json`, log phiên `nao/nhat-ky/phien-*.log`, `nao/tri-nho/`, `nao/ky-nang/`,
sổ bài học `CHANNEL/<kênh>/giam-doc/bai-hoc.jsonl` (qua `giam_doc.kham_nghiem.doc_bai_hoc`). Không ghi tệp nào
(KHÔNG gọi `nao.don_het_han` — trạng thái hết hạn chỉ TÍNH để hiện), không gọi AI, không mạng.
Mỗi mục bọc try riêng: hỏng một mục thì mục đó báo `loi`, các mục khác vẫn hiện.
Mọi chuỗi ra ngoài đi qua `che()` (che khoá lần nữa dù log đã che).

    python -m core.nao_truc_quan            # in JSON (kiểm); gốc dữ liệu đổi được bằng MYTOOL_GOC
"""
from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

GOC = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SO_HANH_DONG = 50
SO_BAI_HOC = 30
SO_DONG_SUY_NGHI = 60
SO_DONG_MOT_DOAN = 40
SO_NGAY_PHIEN = 7
SO_DONG_TRI_NHO = 3
NHO_DEM_GIAY = 300.0

# ── che khoá ────────────────────────────────────────────────────────────────
_MAU_CHE = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9_\-\.=+/]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}"),   # JWT
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}"),                                    # mã bot Telegram
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),                                              # hex dài
]
_MAU_CHE_GIA_TRI = re.compile(
    r"(?i)\b(token|access_token|refresh_token|api[_-]?key|apikey|secret|client_secret|password|passwd|mat_khau|"
    r"authorization|cookie)(\"?\s*[:=]\s*\"?)([^\s\"',;&]{6,})")


def che(chu: Any) -> str:
    s = str(chu if chu is not None else "")
    for m in _MAU_CHE:
        s = m.sub("***", s)
    return _MAU_CHE_GIA_TRI.sub(lambda m: m.group(1) + m.group(2) + "***", s)


def _che_het(x: Any) -> Any:
    if isinstance(x, str):
        return che(x)
    if isinstance(x, list):
        return [_che_het(v) for v in x]
    if isinstance(x, dict):
        return {k: _che_het(v) for k, v in x.items()}
    return x


# ── tiện ích ────────────────────────────────────────────────────────────────
def _cat(chu: Any, n: int) -> str:
    s = " ".join(str(chu or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def _json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def cac_kenh(goc: str) -> List[str]:
    """Kênh máy này quản lý (khai trong `vm/cai-dat-tool.json`) — như `chien_truong._cac_kenh`."""
    d = _json(os.path.join(goc, "vm", "cai-dat-tool.json"))
    return sorted(((d or {}).get("kenh") or {}).keys()) if isinstance(d, dict) else []


def _muc(ten: str, ham, ra: Dict[str, Any]) -> None:
    try:
        ra[ten] = ham()
    except Exception as loi:  # noqa: BLE001 — một mục hỏng không làm hỏng trang
        ra[ten] = {"loi": "{0}: {1}".format(type(loi).__name__, _cat(loi, 200))}


# ── sổ hành động ────────────────────────────────────────────────────────────
def _trang_thai_hien(d: Dict[str, Any], hom: str) -> str:
    """Trạng thái như `nao.don_het_han` SẼ đặt (chỉ tính, không ghi)."""
    from core import nao  # noqa: PLC0415

    tt = str(d.get("trang_thai") or "")
    if tt == "mo" and d.get("lenh") == "tranh" and str((d.get("tham_so") or {}).get("het_han") or "9") < hom:
        return "xong"
    if nao._qua_han_de_xuat(d, hom):
        return "het_han"
    return tt


def _toi_han(d: Dict[str, Any], tt: str, hom: str) -> bool:
    return (tt in ("mo", "xong") and not d.get("cham") and not d.get("khong_tinh")
            and str(d.get("kiem_ngay") or "9") <= hom)


def _noi_dung(d: Dict[str, Any]) -> str:
    ts = d.get("tham_so") or {}
    l = d.get("lenh")
    if l == "thu":
        return "{0}={1} · {2} video (đã dùng {3})".format(ts.get("truc"), ts.get("gia_tri"), ts.get("so_video"),
                                                         ts.get("da_dung", 0))
    if l == "tranh":
        return "{0}={1} · tránh tới {2}".format(ts.get("truc"), ts.get("gia_tri"), ts.get("het_han") or "?")
    if l == "uu-tien-nguon":
        return str(ts.get("link") or "")
    if l == "bai-hoc":
        return "{0}: {1}".format(ts.get("thao_tac") or "?", ts.get("noi_dung") or ts.get("id") or "")
    return str(ts.get("noi_dung") or "")


def doc_hanh_dong(goc: str, hom: str) -> List[Dict[str, Any]]:
    from core import nao  # noqa: PLC0415

    ra = []
    for d in nao.doc_hanh_dong(goc):
        tt = _trang_thai_hien(d, hom)
        ra.append({"id": str(d.get("id") or ""), "luc": str(d.get("luc") or ""), "lenh": str(d.get("lenh") or ""),
                   "kenh": str((d.get("tham_so") or {}).get("kenh") or ""), "noi_dung": _cat(_noi_dung(d), 300),
                   "ly_do": _cat(d.get("ly_do"), 400), "du_doan": _cat(d.get("du_doan"), 300),
                   "kiem_ngay": str(d.get("kiem_ngay") or ""), "trang_thai": tt, "cham": d.get("cham") or "",
                   "ghi_chu_cham": _cat(d.get("ghi_chu_cham"), 300), "cham_luc": str(d.get("cham_luc") or ""),
                   "khong_tinh": bool(d.get("khong_tinh")), "toi_han": _toi_han(d, tt, hom),
                   "ghi_chu_dieu_phoi": _cat(d.get("ghi_chu_dieu_phoi"), 300)})
    ra.sort(key=lambda x: (x["luc"], x["id"]), reverse=True)
    return ra


def chuoi_ti_le(goc: str) -> List[Dict[str, Any]]:
    """Tỉ lệ đúng CỘNG DỒN theo ngày chấm (`cham_luc`, thiếu thì `kiem_ngay`) — cùng luật `nao.ti_le_dung`."""
    from core import nao  # noqa: PLC0415

    theo: Dict[str, List[int]] = {}
    for d in nao.doc_hanh_dong(goc):
        if d.get("cham") not in ("dung", "sai") or d.get("khong_tinh"):
            continue
        ngay = str(d.get("cham_luc") or "")[:10] or str(d.get("kiem_ngay") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", ngay):
            continue
        o = theo.setdefault(ngay, [0, 0])
        o[0] += d["cham"] == "dung"
        o[1] += 1
    ra, dung, tong = [], 0, 0
    for ngay in sorted(theo):
        dung += theo[ngay][0]
        tong += theo[ngay][1]
        ra.append({"ngay": ngay, "dung": dung, "tong": tong, "ti_le": round(100.0 * dung / tong, 1),
                   "dung_ngay": theo[ngay][0], "tong_ngay": theo[ngay][1]})
    return ra


# ── log phiên ───────────────────────────────────────────────────────────────
_RE_DONG = re.compile(r"^(\d{2}:\d{2}:\d{2}) (.*)$")
_RE_CONG_CU = re.compile(r"^\[([A-Za-z_][\w\-]*)\]\s?(.*)$")
_RE_KET = re.compile(r"KET QUA:\s*(thanh cong|that bai)(?:.*?mã\s+(-?\d+))?(?:.*?(\d+|None)\s+lượt)?"
                     r"(?:.*?([\d.]+)s)?(?:.*?chi phí ước tính\s+([\d.?]+|None)\s*USD)?")


def _xuong_dong(chu: str) -> List[str]:
    """Log gộp văn bản của não thành MỘT dòng (`nao._cat`) — chèn lại xuống dòng trước tiêu đề/gạch đầu dòng."""
    s = " ".join(str(chu or "").split())
    s = re.sub(r"\s+(?=#{1,4}\s)", "\n", s)
    s = re.sub(r"\s+(?=---(?:\s|$))", "\n", s)
    s = re.sub(r"(?<=---)\s+", "\n", s)
    s = re.sub(r"\s+(?=[-•*]\s+\S)", "\n", s)
    s = re.sub(r"\s+(?=\d{1,2}\.\s+\S)", "\n", s)
    s = re.sub(r"\s+(?=\*\*[^*\n]{2,80}:\*\*)", "\n", s)
    ra = []
    for x in s.split("\n"):
        if re.match(r"^#{1,4}\s", x) and " **" in x:     # "## Quyết định **KHÔNG …**" → tiêu đề + thân
            dau, _, than = x.partition(" **")
            ra += [dau, "**" + than]
        else:
            ra.append(x)
    return [x for x in ra if x.strip()]


def _doc_log(duong: str) -> List[str]:
    try:
        with io.open(duong, encoding="utf-8", errors="replace") as tep:
            return tep.read().splitlines()
    except OSError:
        return []


def ket_qua_log(dong: List[str]) -> Dict[str, Any]:
    """Lần chạy cuối trong một log ngày: kết quả, mã thoát, lượt, giây, USD; số lần bắt đầu."""
    ra: Dict[str, Any] = {"so_lan": sum(1 for x in dong if "=== BAT DAU PHIEN" in x)}
    for x in reversed(dong):
        m = _RE_KET.search(x)
        if m:
            ra.update({"thanh_cong": m.group(1) == "thanh cong", "ma": int(m.group(2)) if m.group(2) else None,
                       "luot": m.group(3) if m.group(3) not in (None, "None") else None,
                       "giay": m.group(4), "usd": m.group(5) if m.group(5) not in (None, "?", "None") else None,
                       "het_gio": "HẾT GIỜ" in x, "dong": _cat(x[9:] if _RE_DONG.match(x) else x, 200)})
            break
    return ra


def doc_phien(dong: List[str], toi_da: int = SO_DONG_SUY_NGHI) -> Dict[str, Any]:
    """Log phiên → các khối: `nghi` (văn bản não), `cong_cu` (gộp lệnh/kết quả công cụ liền nhau),
    `bat_dau`, `ket`, `tom_tat`. Tối đa `toi_da` dòng hiển thị — thiếu chỗ thì bỏ khối CŨ, giữ phần kết luận."""
    khoi: List[Dict[str, Any]] = []
    nhom: Optional[Dict[str, Any]] = None

    def dong_nhom() -> None:
        nonlocal nhom
        if nhom:
            nhom["tom"] = ", ".join("{0}×{1}".format(k, v) if v > 1 else k for k, v in nhom.pop("_dem").items())
            khoi.append(nhom)
        nhom = None

    for x in dong:
        m = _RE_DONG.match(x)
        luc, than = (m.group(1), m.group(2)) if m else ("", x)
        if not than.strip():
            continue
        if than.startswith("=== BAT DAU PHIEN"):
            dong_nhom()
            khoi.append({"loai": "bat_dau", "luc": luc, "chu": _cat(than.strip("= "), 200)})
        elif than.startswith("lệnh:"):
            continue
        elif than.startswith("[não]"):
            dong_nhom()
            ds = _xuong_dong(than[5:])
            if len(ds) > SO_DONG_MOT_DOAN:
                ds = ds[:SO_DONG_MOT_DOAN] + ["… (còn {0} dòng)".format(len(ds) - SO_DONG_MOT_DOAN)]
            khoi.append({"loai": "nghi", "luc": luc, "dong": ds})
        elif than.startswith("KET QUA:"):
            dong_nhom()
            khoi.append({"loai": "ket", "luc": luc, "chu": _cat(than, 300),
                         "thanh_cong": "thanh cong" in than[:30]})
        elif than.startswith("tóm tắt của não:"):
            dong_nhom()
            noi = than.split(":", 1)[1]
            truoc = next((k for k in reversed(khoi) if k["loai"] == "nghi"), None)
            a, b = " ".join(noi.split()), " ".join(" ".join(truoc["dong"]).split()) if truoc else ""
            n = min(len(a), len(b), 200)
            if truoc and n and a[:n] == b[:n]:
                continue   # trùng lời cuối của não (log cắt hai bản ở độ dài khác nhau)
            khoi.append({"loai": "tom_tat", "luc": luc, "dong": _xuong_dong(noi)[:SO_DONG_MOT_DOAN]})
        elif than.startswith(("nhật ký ngày:", "đuôi đầu ra:", "bản claude")):
            dong_nhom()
            khoi.append({"loai": "ghi_chu", "luc": luc, "chu": _cat(than, 300)})
        else:
            mc = _RE_CONG_CU.match(than)
            if nhom is None:
                nhom = {"loai": "cong_cu", "luc": luc, "_dem": {}, "dong": [], "loi": 0, "so": 0}
            if mc:
                nhom["_dem"][mc.group(1)] = nhom["_dem"].get(mc.group(1), 0) + 1
                nhom["so"] += 1
            elif than.lstrip().startswith("→ LỖI"):
                nhom["loi"] += 1
            if len(nhom["dong"]) < 12:
                nhom["dong"].append(_cat(than.strip(), 180))
    dong_nhom()

    def so_dong(k: Dict[str, Any]) -> int:
        return len(k["dong"]) if k["loai"] in ("nghi", "tom_tat") else 1

    tong = sum(so_dong(k) for k in khoi)
    an = 0
    while tong > toi_da and len(khoi) > 1:
        i = next((j for j, k in enumerate(khoi) if k["loai"] not in ("ket", "tom_tat")), None)
        if i is None:
            break
        tong -= so_dong(khoi[i])
        khoi.pop(i)
        an += 1
    return {"khoi": khoi, "an": an, "so_dong": tong}


def danh_sach_phien(goc: str, so_ngay: int = SO_NGAY_PHIEN) -> List[Dict[str, Any]]:
    """Các log `phien-YYYY-MM-DD.log` mới → cũ (tối đa `so_ngay` tệp), mỗi tệp đã dựng sẵn khối suy nghĩ."""
    thu = os.path.join(goc, "nao", "nhat-ky")
    ds = []
    for p in glob.glob(os.path.join(thu, "phien-*.log")):
        m = re.match(r"^phien-(\d{4}-\d{2}-\d{2})\.log$", os.path.basename(p))
        if m:
            ds.append((m.group(1), p))
    ra = []
    for ngay, p in sorted(ds, reverse=True)[:so_ngay]:
        dong = _doc_log(p)
        try:
            ph = doc_phien(dong)
        except Exception as loi:  # noqa: BLE001
            ph = {"khoi": [], "an": 0, "loi": _cat(loi, 200)}
        ph.update({"ngay": ngay, "ket_qua": ket_qua_log(dong),
                   "nhat_ky": os.path.isfile(os.path.join(thu, ngay + ".md"))})
        ra.append(ph)
    return ra


def lan_chay_cuoi(goc: str) -> Dict[str, Any]:
    from core import nao  # noqa: PLC0415

    thu = os.path.join(goc, "nao", "nhat-ky")
    ds = sorted(p for p in glob.glob(os.path.join(thu, "phien-*.log"))
                if re.match(r"^phien-\d{4}-\d{2}-\d{2}\.log$", os.path.basename(p)))
    if not ds:
        return {"co": False}
    p = ds[-1]
    lan, xong = nao._da_xong_hom_nay(p)
    kq = ket_qua_log(_doc_log(p))
    return {"co": True, "ngay": os.path.basename(p)[6:16], "so_lan": lan, "thanh_cong": xong,
            "ma": kq.get("ma"), "luot": kq.get("luot"), "giay": kq.get("giay"), "usd": kq.get("usd"),
            "het_gio": kq.get("het_gio", False), "dang_chay": os.path.isfile(os.path.join(goc, "nao", ".khoa-phien"))}


# ── trí nhớ, kỹ năng ────────────────────────────────────────────────────────
def _dau_tep(duong: str, n: int = SO_DONG_TRI_NHO) -> List[str]:
    """`n` dòng đầu có nghĩa: tệp có frontmatter `---` thì lấy `description:` rồi tới thân bài."""
    try:
        with io.open(duong, encoding="utf-8", errors="replace") as tep:
            dong = tep.read(20000).splitlines()
    except OSError:
        return []
    ra: List[str] = []
    if dong and dong[0].strip() == "---":
        try:
            het = next(i for i in range(1, len(dong)) if dong[i].strip() == "---")
        except StopIteration:
            het = 0
        for x in dong[1:het]:
            if x.strip().lower().startswith("description:"):
                ra.append(x.split(":", 1)[1].strip())
        dong = dong[het + 1:]
    for x in dong:
        if x.strip() and x.strip() != "---":
            ra.append(_cat(x, 220))
        if len(ra) >= n:
            break
    return ra[:n]


def tri_nho(goc: str) -> Dict[str, Any]:
    thu = os.path.join(goc, "nao", "tri-nho")
    tep = []
    for goc_con, _thu, cac in os.walk(thu):
        for ten in cac:
            p = os.path.join(goc_con, ten)
            try:
                st = os.stat(p)
            except OSError:
                continue
            tep.append({"ten": os.path.relpath(p, thu).replace("\\", "/"), "co": st.st_size,
                        "sua": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)), "_t": st.st_mtime,
                        "dau": _dau_tep(p) if ten.lower().endswith((".md", ".txt", ".json", ".yaml", ".yml")) else []})
    tep.sort(key=lambda x: (x["ten"] != "MEMORY.md", -x["_t"]))
    for x in tep:
        x.pop("_t")
    kn = os.path.join(goc, "nao", "ky-nang")
    try:
        ky_nang = sorted(x for x in os.listdir(kn) if not x.startswith("."))
    except OSError:
        ky_nang = []
    return {"tep": tep, "ky_nang": ky_nang}


# ── bài học ─────────────────────────────────────────────────────────────────
def bai_hoc(goc: str, kenh: List[str], toi_da: int = SO_BAI_HOC) -> Dict[str, Any]:
    """Bài học CÒN ÁP (trạng thái `that` / `gia_thuyet`, bỏ `bo`) của mọi kênh, mới cập nhật trước."""
    from core.giam_doc import kham_nghiem as kn  # noqa: PLC0415
    from core.giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    ra, dem = [], {"that": 0, "gia_thuyet": 0, "bo": 0}
    for k in kenh:
        try:
            ds = kn.doc_bai_hoc(goc, k)
            tho = kn._doc_dong(os.path.join(thu_muc_giam_doc(goc, k), kn.TEP_BAI_HOC))
        except Exception:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
            continue
        cuoi: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        nguon: Dict[Tuple[str, str, str], set] = {}
        for d in tho:
            kh = (str(d.get("truc") or ""), str(d.get("gia_tri") or ""), str(d.get("cum") or ""))
            if str(d.get("luc") or "") >= str((cuoi.get(kh) or {}).get("luc") or ""):
                cuoi[kh] = d
            nguon.setdefault(kh, set()).add("não" if d.get("nguon") == "nao" else "khám nghiệm")
        for b in ds:
            dem[b["trang_thai"]] = dem.get(b["trang_thai"], 0) + 1
            if b["trang_thai"] == "bo":
                continue
            kh = (b["truc"], b["gia_tri"], b["cum"])
            c = cuoi.get(kh) or {}
            ra.append({"kenh": k, "id": b["id"], "truc": b["truc"], "cum": b["cum"], "huong": b["huong"],
                       "noi_dung": _cat(b["cau"], 400), "trang_thai": b["trang_thai"], "cong": b["cong"],
                       "tru": b["tru"], "bong": bool(b.get("bong")), "nguon": " + ".join(sorted(nguon.get(kh) or [])),
                       "moc": str(c.get("moc") or ""), "luc": str(c.get("luc") or "")[:16].replace("T", " ")})
    ra.sort(key=lambda x: x["luc"], reverse=True)
    return {"ds": ra[:toi_da], "tong": len(ra), "dem": dem}


# ── ghép ────────────────────────────────────────────────────────────────────
def tinh(goc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    goc = goc or GOC
    bay_gio = bay_gio or _dt.datetime.now()
    hom = bay_gio.strftime("%Y-%m-%d")
    ra: Dict[str, Any] = {"luc": bay_gio.strftime("%Y-%m-%d %H:%M:%S"), "hom_nay": hom}
    kenh = cac_kenh(goc)
    ra["kenh"] = kenh
    _muc("hanh_dong", lambda: doc_hanh_dong(goc, hom), ra)
    _muc("chuoi_ti_le", lambda: chuoi_ti_le(goc), ra)
    _muc("phien", lambda: danh_sach_phien(goc), ra)
    _muc("lan_cuoi", lambda: lan_chay_cuoi(goc), ra)
    _muc("tri_nho", lambda: tri_nho(goc), ra)
    _muc("bai_hoc", lambda: bai_hoc(goc, kenh), ra)

    def diem() -> Dict[str, Any]:
        from core import nao  # noqa: PLC0415

        goc_ds = nao.doc_hanh_dong(goc)
        dung, tong = nao.ti_le_dung(goc_ds)
        hd = ra["hanh_dong"] if isinstance(ra.get("hanh_dong"), list) else []
        bh = ra.get("bai_hoc") if isinstance(ra.get("bai_hoc"), dict) else {}
        return {"dung": dung, "da_cham": tong, "ti_le": round(100.0 * dung / tong, 1) if tong else None,
                "hom_nay": sum(1 for d in goc_ds if str(d.get("luc") or "")[:10] == hom and not d.get("khong_tinh")
                               and d.get("trang_thai") != "huy"),
                "han_muc": nao.han_muc_ngay(goc_ds), "han_muc_day": nao.TOI_DA_MOI_NGAY,
                "nguong_cham": nao.TOI_THIEU_DA_CHAM, "tong": len(goc_ds),
                "dang_mo": sum(1 for d in hd if d["trang_thai"] == "mo"),
                "toi_han": sum(1 for d in hd if d["toi_han"]),
                "bai_hoc_nao": sum(1 for d in hd if d["lenh"] == "bai-hoc"
                                   and d["noi_dung"].startswith("them")),
                "bai_hoc_so": bh.get("tong"), "bai_hoc_dem": bh.get("dem") or {}}

    _muc("diem", diem, ra)
    return _che_het(ra)


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None}
_KHOA = threading.Lock()


def tinh_nho(han: float = NHO_DEM_GIAY) -> Dict[str, Any]:
    """`tinh()` nhớ đệm ~5 phút (não chạy mỗi ngày một lần — không cần tươi hơn)."""
    with _KHOA:
        if _NHO["du"] is None or time.time() - _NHO["luc"] > han:
            _NHO["du"], _NHO["luc"] = tinh(), time.time()
        return _NHO["du"]


if __name__ == "__main__":
    print(json.dumps(tinh(), ensure_ascii=False, indent=1)[:8000])
