"""TRUY XUẤT `nho()` — không LLM, chỉ đọc chỉ mục (< 50 ms), + `dong_loi_dang_tang` cho `core.nao xem`.

Xếp hạng một nơ-ron của bộ phận (trạng thái khác `nghi`):

    điểm = (SAN_KHOP + độ khớp) × trọng số × độ tươi        [× (1 + LAN_TRUYEN) nếu lan 1 bước tới được]

* độ khớp = tổng −bm25 trên hai chỉ mục FTS5 (trigram cho tiếng Nhật, unicode61 bỏ dấu cho tiếng Việt), chia cho
  nơ-ron khớp nhất → [0, 1]; không khớp chữ nào = 0 (vẫn xếp được nhờ sàn `SAN_KHOP`);
* trọng số = mẫu Thompson Beta(α, β) với bài học; với lỗi = 1 − e^(−(số lần 7 ngày + 1)/5) (lỗi càng dày càng nặng);
* độ tươi = 0,5^(tuổi từ lần cuối / `NUA_DOI_NGAY` ngày);
* lan 1 bước: nơ-ron cùng nối vào một nốt thực thể (kênh) với 3 nơ-ron khớp nhất, hoặc vào kênh được nhắc tên trong
  ngữ cảnh, được thưởng.

Có `quyet_dinh` thì ghi bảng `dung` (mã các nơ-ron đã đưa) để chấm công về sau; `TI_LE_DOI_CHUNG` quyết định là ĐỐI
CHỨNG: trả danh sách rỗng, ghi `doi_chung = 1`. Gọi không có `quyet_dinh` (xem tay) thì luôn trả đủ.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional

from ._chung import (BO_PHAN, DANG, LAN_TRUYEN, NGHI, NUA_DOI_NGAY, SAN_KHOP, TAI_PHAT, TEN_TRANG_THAI,
                     TI_LE_DOI_CHUNG, duong_db)

_RE_TU = re.compile(r"\w+")
_RE_TACH = re.compile(r"[\s,.;:!?()\[\]{}「」『』【】、。・…\"'“”‘’/\\|<>#*=+—–-]+")
_RE_CJK = re.compile(r"[぀-ヿ㐀-鿿ｦ-ﾟ]")


def _cau_truy_van(tu: List[str]) -> str:
    return " OR ".join('"{0}"'.format(t.replace('"', '""')) for t in dict.fromkeys(tu))


def truy_van_viet(ngu_canh: str) -> str:
    """Từ ≥ 2 ký tự (bỏ số thuần) nối OR — unicode61 tự bỏ dấu ở cả chỉ mục lẫn câu hỏi."""
    return _cau_truy_van([w for w in _RE_TU.findall(ngu_canh.lower()) if len(w) >= 2 and not w.isdigit()][:24])


def truy_van_tri(ngu_canh: str) -> str:
    """Đoạn ≥ 3 ký tự; đoạn chữ Nhật/Hán (không có dấu cách) cắt thành mọi cụm 3 ký tự liền nhau."""
    tu: List[str] = []
    for doan in _RE_TACH.split(ngu_canh):
        if len(doan) < 3:
            continue
        tu += [doan[i:i + 3] for i in range(len(doan) - 2)] if _RE_CJK.search(doan) else [doan]
    return _cau_truy_van(tu[:32])


def _ghi_dung(con: sqlite3.Connection, quyet_dinh: str, bo_phan: str, ids: List[str], doi_chung: int) -> None:
    con.execute("INSERT INTO dung(quyet_dinh, bo_phan, bai_hoc, doi_chung, luc) VALUES (?,?,?,?,?)",
                (quyet_dinh, bo_phan, json.dumps(ids, ensure_ascii=False), doi_chung, time.time()))
    con.commit()


def nho(goc: str, bo_phan: str, ngu_canh: str, k: int = 5, quyet_dinh: str = "", *,
        rng: Optional[random.Random] = None, bay_gio: Optional[float] = None) -> List[Dict[str, Any]]:
    """Top-k nơ-ron của `bo_phan` cho `ngu_canh`: `[{id, loai, bo_phan, cau, trang_thai, diem, duong}]`. KHÔNG
    BAO GIỜ ném lỗi (hỏng → [])."""
    try:
        return _nho(goc, bo_phan, ngu_canh, k, quyet_dinh, rng or random.Random(), bay_gio or time.time())
    except Exception:  # noqa: BLE001 — não hỏng = như không có não
        return []


def _nho(goc: str, bo_phan: str, ngu_canh: str, k: int, quyet_dinh: str, rng: random.Random, bay_gio: float
         ) -> List[Dict[str, Any]]:
    p = duong_db(goc)
    if bo_phan not in BO_PHAN or not os.path.isfile(p):
        return []
    con = sqlite3.connect(p, timeout=0.5)
    try:
        if quyet_dinh and rng.random() < TI_LE_DOI_CHUNG:
            _ghi_dung(con, quyet_dinh, bo_phan, [], 1)
            return []
        ung = {r[0]: r for r in con.execute(
            "SELECT id, loai, bo_phan, cau, trang_thai, duong, alpha, beta, so_lan_7, lan_cuoi FROM no_ron "
            "WHERE bo_phan = ? AND trang_thai != ?", (bo_phan, NGHI))}
        khop: Dict[str, float] = {}
        for bang, q in (("chi_muc_viet", truy_van_viet(ngu_canh)), ("chi_muc_tri", truy_van_tri(ngu_canh))):
            if q:
                for id_, s in con.execute("SELECT id, -bm25({0}) FROM {0} WHERE {0} MATCH ? AND bo_phan = ?".format(
                        bang), (q, bo_phan)):
                    if id_ in ung:
                        khop[id_] = khop.get(id_, 0.0) + max(0.0, s)
        dinh = max(khop.values(), default=0.0)
        diem: Dict[str, float] = {}
        for id_, (_, loai, _, _, _, _, a, b, so7, lan_cuoi) in ung.items():
            tr = rng.betavariate(max(a or 1, 1e-3), max(b or 1, 1e-3)) if loai == "bai-hoc" else \
                1 - math.exp(-((so7 or 0) + 1) / 5.0)
            tuoi = 0.5 ** (max(0.0, bay_gio - lan_cuoi) / 86400 / NUA_DOI_NGAY) if lan_cuoi else 0.5
            diem[id_] = (SAN_KHOP + (khop.get(id_, 0.0) / dinh if dinh > 0 else 0.0)) * tr * tuoi
        hat = sorted(khop, key=khop.get, reverse=True)[:3]
        the = {t for (t,) in con.execute("SELECT DISTINCT toi FROM lien_ket WHERE toi LIKE 'thuc-the/%'")
               if t.rsplit("/", 1)[-1] and t.rsplit("/", 1)[-1] in ngu_canh}
        if hat:
            the |= {t for (t,) in con.execute("SELECT DISTINCT toi FROM lien_ket WHERE toi LIKE 'thuc-the/%' AND tu IN "
                                              "({0})".format(",".join("?" * len(hat))), hat)}
        if the:
            for (tu,) in con.execute("SELECT DISTINCT tu FROM lien_ket WHERE toi IN ({0})".format(
                    ",".join("?" * len(the))), sorted(the)):
                if tu in diem:
                    diem[tu] *= 1 + LAN_TRUYEN
        chon = sorted(diem, key=lambda i: (-diem[i], i))[:max(0, k)]
        if quyet_dinh:
            _ghi_dung(con, quyet_dinh, bo_phan, chon, 0)
        return [{"id": i, "loai": ung[i][1], "bo_phan": ung[i][2], "cau": ung[i][3], "trang_thai": ung[i][4],
                 "diem": round(diem[i], 4), "duong": ung[i][5]} for i in chon]
    finally:
        con.close()


def loi_dang_tang(goc: str, n: int = 10, bo_phan: str = "") -> List[Dict[str, Any]]:
    """Nơ-ron lỗi đang xảy ra / tái phát, xếp theo số lần 7 ngày (chỉ đọc chỉ mục). Không có kho → []."""
    p = duong_db(goc)
    if not os.path.isfile(p):
        return []
    con = sqlite3.connect(p, timeout=0.5)
    try:
        dk, ts = ("AND bo_phan = ?", (bo_phan,)) if bo_phan else ("", ())
        return [{"id": r[0], "bo_phan": r[1], "cau": r[2], "trang_thai": r[3], "so_lan_7": r[4], "so_lan": r[5],
                 "kenh": json.loads(r[6] or "[]")} for r in con.execute(
            "SELECT id, bo_phan, cau, trang_thai, so_lan_7, n, kenh FROM no_ron WHERE loai = 'loi' AND trang_thai IN "
            "(?, ?) {0} ORDER BY so_lan_7 DESC, lan_cuoi DESC LIMIT ?".format(dk), (DANG, TAI_PHAT) + ts + (n,))]
    finally:
        con.close()


def dong_loi(x: Dict[str, Any], n_chu: int = 140) -> str:
    cau = x["cau"] if len(x["cau"]) <= n_chu else x["cau"][: n_chu - 1] + "…"
    return "[{0}] {1}×/7 ngày, {2} kênh{3}: {4}".format(x["bo_phan"], x["so_lan_7"], len(x["kenh"]),
                                                       ", " + TEN_TRANG_THAI[x["trang_thai"]].upper()
                                                       if x["trang_thai"] == TAI_PHAT else "", cau)


def dong_loi_dang_tang(goc: str, n: int = 5) -> List[str]:
    """Mục ngắn cho `python -m core.nao xem` ([] khi chưa có não bộ phận / không có lỗi đang xảy ra)."""
    ds = loi_dang_tang(goc, n)
    if not ds:
        return []
    return ["  - " + dong_loi(x) for x in ds] + [
        "  (sổ tay từng bộ phận: nao/bo-phan/<bộ phận>/so-tay.md · `python -m core.nao_bo_phan xem`)"]
