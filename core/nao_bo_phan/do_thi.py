"""ĐỒ THỊ THẦN KINH của não bộ phận — trang `/nao-do-thi` của 8790 (vẽ bằng force-graph). CHỈ ĐỌC: kho mở `mode=ro`,
vault chỉ đọc; không LLM, không ghi gì.

    do_thi(goc)                 -> {luc, co_kho, nut, day, dem}            (`do_thi_nho`: nhớ đệm 60 giây)
    song(goc, tu, dung, ngu)    -> {luc, xung, con_tro: {tu, dung, ngu}, dem}   xung thần kinh mới hơn con trỏ
    no_ron(goc, id)             -> {id, dau, than} | None                  chữ một nốt, đường khoá trong `nao/bo-phan/`

NÚT: `nao-trung-tam` · 15 bộ phận (hub) · nơ-ron lỗi / cảnh báo / bài học (bỏ `nghi` và `da-het` im quá 14 ngày) ·
thực thể (`thuc-the/*`) nối ≥ 2 nơ-ron. Quá `TRAN_NUT` nút thì giữ nơ-ron sôi động nhất (to nhất, gặp gần nhất).
DÂY: trung tâm→bộ phận (`goc`) · bộ phận→nơ-ron (`thuoc`) · nơ-ron→thực thể (`the`, bảng `lien_ket`) · nơ-ron→nơ-ron
(`noi` của bài tự rút) · ĐỒNG KÍCH HOẠT (`dong` — "cùng cháy thì nối"): hai nơ-ron có sự kiện trong cùng một SỰ CỐ
(cùng gói; không gói thì cùng kênh × ngày) 14 ngày qua, trọng số = số sự cố chung ≥ `DONG_TOI_THIEU`, giữ `TRAN_DONG`
dây nặng nhất. Bài tự rút (giấc ngủ) mang sự kiện bằng chứng (`ung_ho`/`phan_doi`) của nó vào phép đếm.
XUNG: sự kiện (`chon|loi|sua|ket_qua|do`, lỗi/sửa → nơ-ron theo chữ ký) · `dung` (bài/nơ-ron được đưa vào lời nhắc) ·
`ngu` (giấc ngủ áp lệnh lên bài nào). Lần gọi đầu (`tu` < 0) chỉ trả `XUNG_DAU` xung gần nhất trong 10 phút qua.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import re
import sqlite3
import threading
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from ._chung import (BO_PHAN, CANH_BAO, DA_HET, DANG, DANG_DUNG, NGHI, TAI_PHAT, THUC_THE, doc_chu, doc_ghi_chu,
                     duong_db, duong_vault, ngay_gio)
from .no_ron import doc_bai_ngu, su_co

NGAY = 86400.0
TRUNG_TAM = "nao-trung-tam"
TRAN_NUT = 600
TRAN_THE = 80               # chỗ chừa cho nốt thực thể trong trần nút
NGAY_DONG = 14
DONG_TOI_THIEU = 2
TRAN_DONG = 300
TRAN_XUNG = 200
XUNG_DAU = 50
GIAY_XUNG_DAU = 600
TRAN_CHU = 60000            # chữ một nốt trả về tối đa (nhật ký dài → giữ đuôi)


def _mo(goc: str) -> sqlite3.Connection:
    return sqlite3.connect("file:{0}?mode=ro".format(duong_db(goc).replace("\\", "/")), uri=True, timeout=0.5)


def _ngan(chu: Any, n: int = 60) -> str:
    s = " ".join(str(chu or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _json(s: Any, mac_dinh: Any) -> Any:
    try:
        d = json.loads(s or "null")
    except (TypeError, ValueError):
        return mac_dinh
    return d if isinstance(d, type(mac_dinh)) else mac_dinh


def _kich_loi(so7: Any, s48: Any, canh_bao: bool) -> float:
    """Nơ-ron lỗi to theo số lần 7 ngày + sự cố 48h; cảnh báo nhỏ hơn."""
    return round((2.5 + min(6.0, 1.2 * math.sqrt((so7 or 0) + 2 * (s48 or 0)))) * (0.7 if canh_bao else 1.0), 2)


def _kich_bai(a: Any, b: Any, n: Any) -> float:
    """Nơ-ron bài học to theo α/(α+β) × độ dày bằng chứng (n bão hoà ở 20)."""
    tb = float(a or 1) / (float(a or 1) + float(b or 1))
    return round(2 + 4 * tb * min(1.0, math.log1p(n or 0) / math.log1p(20)), 2)


def _dem(con: sqlite3.Connection, bay_gio: float) -> Dict[str, Any]:
    """Bộ đếm thanh trên: sự kiện 24h, lỗi đang cháy (không tính cảnh báo), bài đang dùng, giấc ngủ cuối."""
    mot = lambda sql, *ts: con.execute(sql, ts).fetchone()[0]  # noqa: E731
    ra = {"su_kien_24h": mot("SELECT COUNT(*) FROM su_kien WHERE luc >= ?", bay_gio - NGAY),
          "loi_dang": mot("SELECT COUNT(*) FROM no_ron WHERE loai = 'loi' AND COALESCE(muc, 'loi') != ? AND "
                          "trang_thai IN (?, ?)", CANH_BAO, DANG, TAI_PHAT),
          "bai_dang_dung": mot("SELECT COUNT(*) FROM no_ron WHERE loai = 'bai-hoc' AND trang_thai = ?", DANG_DUNG),
          "ngu_cuoi": ""}
    try:
        ra["ngu_cuoi"] = ngay_gio(mot("SELECT MAX(luc) FROM giac_ngu WHERE loi = ''"))
    except sqlite3.Error:       # kho đợt 1 chưa có bảng giấc ngủ
        pass
    return ra


# ── đồ thị ───────────────────────────────────────────────────────────────────

def _dong_kich_hoat(con: sqlite3.Connection, goc: str, giu: Dict[str, Dict[str, Any]], moc: float
                    ) -> List[Tuple[str, str, int]]:
    """[(a, b, số sự cố chung)] giữa các nơ-ron đang giữ — xem đầu tệp."""
    nhom: Dict[Tuple[str, str], set] = {}

    def them(id_: str, kenh: str, goi: str, luc: float) -> None:
        if kenh or goi:
            nhom.setdefault(su_co(kenh, goi, luc), set()).add(id_)

    for bp, ck, kenh, goi, luc in con.execute("SELECT bo_phan, chu_ky, kenh, ma_goi, luc FROM su_kien WHERE luc >= ? "
                                              "AND loai = 'loi' AND chu_ky != ''", (moc,)):
        if "{0}/loi/{1}".format(bp, ck) in giu:
            them("{0}/loi/{1}".format(bp, ck), kenh, goi, luc)
    bang: Dict[int, set] = {}
    for b in doc_bai_ngu(duong_vault(goc)):
        id_ = "{0}/bai-hoc/{1}".format(b.get("bo_phan"), b.get("id"))
        if id_ in giu:
            for i in list(b.get("ung_ho") or []) + list(b.get("phan_doi") or []):
                if isinstance(i, int):
                    bang.setdefault(i, set()).add(id_)
    ids = sorted(bang)
    for i in range(0, len(ids), 500):
        lo = ids[i:i + 500]
        for sid, kenh, goi, luc in con.execute("SELECT id, kenh, ma_goi, luc FROM su_kien WHERE luc >= ? AND id IN "
                                               "({0})".format(",".join("?" * len(lo))), [moc] + lo):
            for id_ in bang[sid]:
                them(id_, kenh, goi, luc)
    dem: Counter = Counter()
    for ds in nhom.values():
        dem.update(itertools.combinations(sorted(ds), 2))
    return [(a, b, w) for (a, b), w in sorted(dem.items(), key=lambda x: (-x[1], x[0]))
            if w >= DONG_TOI_THIEU][:TRAN_DONG]


def do_thi(goc: str, bay_gio: Optional[float] = None) -> Dict[str, Any]:
    bay_gio = bay_gio or time.time()
    bp_nut = {bp: {"id": bp, "nhom": "bo-phan", "ten": ten, "bo_phan": bp, "trang_thai": "", "kich_thuoc": 7.0,
                   "mau": "bo-phan", "tep": bp + "/so-tay", "thu_tu": i, "su_kien_7": 0, "so_loi": 0, "so_bai": 0}
              for i, (bp, ten) in enumerate(BO_PHAN.items())}
    nut: List[Dict[str, Any]] = [{"id": TRUNG_TAM, "nhom": "trung-tam", "ten": "Não trung tâm", "bo_phan": "",
                                  "trang_thai": "", "kich_thuoc": 16.0, "mau": "trung-tam", "tep": "_ban-do"}]
    nut += bp_nut.values()
    day = [{"source": TRUNG_TAM, "target": bp, "loai": "goc", "trong_so": 1} for bp in BO_PHAN]
    ra = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "co_kho": os.path.isfile(duong_db(goc)), "nut": nut, "day": day,
          "dem": {}}
    if not ra["co_kho"]:
        return ra
    moc = bay_gio - NGAY_DONG * NGAY
    con = _mo(goc)
    try:
        con.execute("BEGIN")            # một ảnh chụp nhất quán cho mọi câu đọc
        nr = []
        for id_, loai, bp, tt, cau, a, b, n, so7, lan_cuoi, kenh, muc, nguon, s48 in con.execute(
                "SELECT id, loai, bo_phan, trang_thai, cau, alpha, beta, n, so_lan_7, lan_cuoi, kenh, "
                "COALESCE(muc, 'loi'), COALESCE(nguon, ''), COALESCE(su_co_48, 0) FROM no_ron"):
            if bp not in bp_nut or tt == NGHI or (tt == DA_HET and (lan_cuoi or 0) < moc):
                continue
            if loai == "loi":
                nhom = "canh-bao" if muc == CANH_BAO else "loi"
                kich = _kich_loi(so7, s48, nhom == "canh-bao")
                mau = "canh-bao" if nhom == "canh-bao" and tt != DA_HET else tt
            else:
                nhom, kich, mau = "bai-hoc", _kich_bai(a, b, n), tt
            nr.append({"id": id_, "nhom": nhom, "ten": _ngan(cau), "cau": _ngan(cau, 240), "bo_phan": bp,
                       "trang_thai": tt, "kich_thuoc": kich, "mau": mau, "tep": id_, "kenh": _json(kenh, []),
                       "nguon": nguon, "lan_cuoi": int(lan_cuoi or 0)})
        nr.sort(key=lambda x: (-x["kich_thuoc"], -x["lan_cuoi"], x["id"]))
        nr = nr[:max(0, TRAN_NUT - len(nut) - TRAN_THE)]
        giu = {x["id"]: x for x in nr}
        the_dem: Counter = Counter()
        the_day, noi = [], set()
        for tu, toi in con.execute("SELECT tu, toi FROM lien_ket"):
            if tu in giu and toi.startswith("thuc-the/"):
                the_day.append((tu, toi))
                the_dem[toi] += 1
            elif tu in giu and toi in giu and toi != tu:
                noi.add((tu, toi))
        the = [t for t, c in sorted(the_dem.items(), key=lambda x: (-x[1], x[0])) if c >= 2]
        the = the[:max(0, TRAN_NUT - len(nut) - len(nr))]
        for t in the:
            loai_t, _, ten = t[len("thuc-the/"):].partition("/")
            nr.append({"id": t, "nhom": "thuc-the", "ten": "{0} {1}".format(THUC_THE.get(loai_t, loai_t), ten),
                       "bo_phan": "", "trang_thai": loai_t, "kich_thuoc": round(1.5 + min(3.0, the_dem[t] / 4.0), 2),
                       "mau": "thuc-the", "tep": t, "so_noi": the_dem[t]})
        nut += nr
        dong = _dong_kich_hoat(con, goc, giu, moc)
        the_co = set(the)
        day += [{"source": x["bo_phan"], "target": x["id"], "loai": "thuoc", "trong_so": 1} for x in giu.values()]
        day += [{"source": a, "target": b, "loai": "the", "trong_so": 1} for a, b in the_day if b in the_co]
        day += [{"source": a, "target": b, "loai": "noi", "trong_so": 1} for a, b in sorted(noi)]
        day += [{"source": a, "target": b, "loai": "dong", "trong_so": w} for a, b, w in dong]
        for bp, n in con.execute("SELECT bo_phan, COUNT(*) FROM su_kien WHERE luc >= ? GROUP BY 1",
                                 (bay_gio - 7 * NGAY,)):
            if bp in bp_nut:
                bp_nut[bp].update(su_kien_7=n, kich_thuoc=round(7 + min(7.0, math.sqrt(n) / 3), 2))
        for x in giu.values():
            if x["nhom"] == "loi" and x["trang_thai"] in (DANG, TAI_PHAT):
                bp_nut[x["bo_phan"]]["so_loi"] += 1
            elif x["nhom"] == "bai-hoc":
                bp_nut[x["bo_phan"]]["so_bai"] += 1
        ra["dem"] = dict(_dem(con, bay_gio), nut=len(nut), day=len(day), dong=len(dong),
                         no_ron=len(giu), thuc_the=len(the))
    finally:
        con.close()
    return ra


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None, "goc": ""}
_KHOA = threading.Lock()


def do_thi_nho(goc: str, han: float = 60.0) -> Dict[str, Any]:
    with _KHOA:
        if _NHO["du"] is None or _NHO["goc"] != goc or time.time() - _NHO["luc"] > han:
            _NHO.update(du=do_thi(goc), luc=time.time(), goc=goc)
        return _NHO["du"]


# ── xung thần kinh ───────────────────────────────────────────────────────────

def _ket(so: Dict[str, Any]) -> str:
    """Kết cục của một sự kiện kết quả / đo: thang | truot | trung_binh | ""."""
    if so.get("ket"):
        return str(so["ket"])
    for k in ("dat", "ok"):
        if isinstance(so.get(k), bool):
            return "thang" if so[k] else "truot"
    return "truot" if so.get("trang_thai") == "hong" else ""


def _moi(con: sqlite3.Connection, bang: str, cot: str, tu: int, bay_gio: float, dau: int) -> Tuple[list, int]:
    """(dòng của `bang` có id > tu — mới nhất, tối đa `TRAN_XUNG`, xếp tăng; con trỏ mới = id lớn nhất). `tu` < 0
    (lần đầu) hoặc lớn hơn id lớn nhất (kho dựng lại) → `dau` dòng gần nhất trong `GIAY_XUNG_DAU` giây qua."""
    dinh = con.execute("SELECT COALESCE(MAX(id), 0) FROM " + bang).fetchone()[0]
    if tu < 0 or tu > dinh:
        ds = con.execute("SELECT {0} FROM {1} WHERE luc >= ? ORDER BY id DESC LIMIT ?".format(cot, bang),
                         (bay_gio - GIAY_XUNG_DAU, dau)).fetchall()
    else:
        ds = con.execute("SELECT {0} FROM {1} WHERE id > ? ORDER BY id DESC LIMIT ?".format(cot, bang),
                         (tu, TRAN_XUNG)).fetchall()
    return ds[::-1], dinh


def song(goc: str, tu: int = -1, dung: int = -1, ngu: int = -1, bay_gio: Optional[float] = None) -> Dict[str, Any]:
    bay_gio = bay_gio or time.time()
    ra = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "xung": [],
          "con_tro": {"tu": max(tu, 0), "dung": max(dung, 0), "ngu": max(ngu, 0)}, "dem": {}}
    if not os.path.isfile(duong_db(goc)):
        return ra
    xung: List[Dict[str, Any]] = []
    con = _mo(goc)
    try:
        con.execute("BEGIN")
        ds, ra["con_tro"]["tu"] = _moi(con, "su_kien", "id, luc, bo_phan, loai, kenh, chu_ky, noi_dung, so", tu,
                                       bay_gio, XUNG_DAU)
        for id_, luc, bp, loai, kenh, ck, nd, so in ds:
            xung.append({"id": id_, "luc": int(luc), "bo_phan": bp, "loai": loai, "kenh": kenh or "",
                         "chu": _ngan(nd, 120),
                         "no_ron": ["{0}/loi/{1}".format(bp, ck)] if ck and loai in ("loi", "sua") else [],
                         "ket": _ket(_json(so, {})) if loai in ("ket_qua", "do") else ""})
        try:
            ds, ra["con_tro"]["dung"] = _moi(con, "dung", "id, luc, bo_phan, quyet_dinh, bai_hoc, doi_chung", dung,
                                             bay_gio, 20)
            for id_, luc, bp, qd, bh, dc in ds:
                ids = [str(x) for x in _json(bh, [])]
                xung.append({"id": "d{0}".format(id_), "luc": int(luc or 0), "bo_phan": bp, "loai": "dung",
                             "kenh": re.sub(r"-\d{3,}$", "", str(qd or "").split(":")[0]), "no_ron": ids,
                             "ket": "doi-chung" if dc else "",
                             "chu": "đối chứng — lời nhắc {0} không nhận bài nào".format(qd) if dc else
                             "lời nhắc {0} nhận {1} nơ-ron".format(qd, len(ids)) if ids else
                             "lời nhắc {0}: não chưa có nơ-ron hợp".format(qd)})
            ds, ra["con_tro"]["ngu"] = _moi(con, "giac_ngu", "id, luc, bo_phan, de_xuat, ap, bo, chi_tiet, loi", ngu,
                                            bay_gio, 15)
            for id_, luc, bp, dx, ap, bo, ct, loi in ds:
                ids = ["{0}/bai-hoc/{1}".format(bp, l["id"]) for l in _json(ct, {}).get("ap") or []
                       if isinstance(l, dict) and l.get("id")]
                xung.append({"id": "n{0}".format(id_), "luc": int(luc or 0), "bo_phan": bp, "loai": "ngu", "kenh": "",
                             "no_ron": ids, "ket": "truot" if loi else "",
                             "chu": "ngủ hỏng: " + _ngan(loi, 90) if loi else
                             "ngủ: áp {0}/{1} lệnh, bỏ {2}".format(ap or 0, dx or 0, bo or 0)})
        except sqlite3.Error:           # kho đợt 1 chưa có bảng giấc ngủ
            pass
        ra["dem"] = _dem(con, bay_gio)
    finally:
        con.close()
    ra["xung"] = sorted(xung, key=lambda x: x["luc"])
    return ra


# ── chữ một nốt ──────────────────────────────────────────────────────────────

def no_ron(goc: str, id_: str) -> Optional[Dict[str, Any]]:
    """Frontmatter + thân markdown của nốt `nao/bo-phan/<id>.md` (nơ-ron, thực thể, sổ tay, nhật ký, bản đồ). Đường
    lạ (`..`, tuyệt đối, `\\`, `:`, ra ngoài vault) hoặc không có tệp → None."""
    id_ = str(id_ or "")
    phan = id_.split("/")
    if not id_ or len(id_) > 300 or any(c in id_ for c in "\\:\x00") or any(p in ("", ".", "..") for p in phan):
        return None
    vault = os.path.realpath(duong_vault(goc))
    p = os.path.realpath(os.path.join(vault, *phan) + ".md")
    try:
        if os.path.commonpath([vault, p]) != vault or not os.path.isfile(p):
            return None
    except ValueError:                  # khác ổ đĩa
        return None
    van = doc_chu(p)
    if van is None:
        return None
    dau, than = doc_ghi_chu(van)
    if len(than) > TRAN_CHU:
        than = "… (cắt bớt phần đầu)\n" + than[-TRAN_CHU:]
    return {"id": id_, "dau": dau, "than": than}
