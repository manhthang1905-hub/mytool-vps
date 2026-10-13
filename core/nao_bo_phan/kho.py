"""Kho SQLite `nao/bo-phan.db` (WAL) + `ghi()` — ký ức thô của mọi bộ phận.

Bảng: `su_kien` (ký ức thô, KHÔNG BAO GIỜ xoá), `con_tro` (đã gom mỗi tệp tới đâu), `dung` (quyết định nào đã được
đưa những nơ-ron nào — chấm công về sau). Bảng chỉ mục (`no_ron`, `chi_muc_tri`, `chi_muc_viet`, `lien_ket`) dựng
lại được hoàn toàn từ vault markdown (`no_ron.dung_lai_chi_muc`).
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from ._chung import BO_PHAN, LOAI, bam, cac_kenh, chu_ky, duong_db

_LUOC_DO = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS su_kien(id INTEGER PRIMARY KEY, luc REAL NOT NULL, bo_phan TEXT NOT NULL,
    loai TEXT NOT NULL, kenh TEXT DEFAULT '', ma_goi TEXT DEFAULT '', chu_ky TEXT DEFAULT '',
    noi_dung TEXT DEFAULT '', so TEXT DEFAULT '{}', nguon TEXT DEFAULT '', khoa TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS su_kien_chu_ky ON su_kien(chu_ky, luc);
CREATE INDEX IF NOT EXISTS su_kien_luc ON su_kien(luc);
CREATE TABLE IF NOT EXISTS con_tro(tep TEXT PRIMARY KEY, mtime REAL, kich_thuoc INTEGER, vi_tri INTEGER,
    dau TEXT, tu REAL, trang TEXT);
CREATE TABLE IF NOT EXISTS dung(id INTEGER PRIMARY KEY, quyet_dinh TEXT, bo_phan TEXT, bai_hoc TEXT,
    doi_chung INTEGER DEFAULT 0, luc REAL);
CREATE TABLE IF NOT EXISTS no_ron(id TEXT PRIMARY KEY, loai TEXT, bo_phan TEXT, trang_thai TEXT, cau TEXT,
    duong TEXT, alpha REAL, beta REAL, n INTEGER, so_lan_7 INTEGER, lan_cuoi REAL, kenh TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS chi_muc_tri USING fts5(id UNINDEXED, bo_phan UNINDEXED, van,
    tokenize='trigram');
CREATE VIRTUAL TABLE IF NOT EXISTS chi_muc_viet USING fts5(id UNINDEXED, bo_phan UNINDEXED, van,
    tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS lien_ket(tu TEXT, toi TEXT, PRIMARY KEY(tu, toi));
"""
_DA_DUNG: set = set()

#: Một dòng sự kiện đúng thứ tự cột của `CHEN`.
Dong = Tuple[float, str, str, str, str, str, str, str, str, str]
CHEN = ("INSERT OR IGNORE INTO su_kien(luc, bo_phan, loai, kenh, ma_goi, chu_ky, noi_dung, so, nguon, khoa) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)")


def mo(goc: str, cho: float = 1.0) -> sqlite3.Connection:
    """Mở (tạo nếu chưa có) kho của gốc `goc`. `cho` = số giây chờ khoá tối đa."""
    p = duong_db(goc)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    moi = not os.path.isfile(p)
    con = sqlite3.connect(p, timeout=cho)
    if moi or p not in _DA_DUNG:
        con.executescript(_LUOC_DO)
        _DA_DUNG.add(p)
    return con


def dong_su_kien(bo_phan: str, loai: str, *, luc: Optional[float] = None, kenh: str = "", ma_goi: str = "",
                 chu_ky_: str = "", noi_dung: Any = "", so: Optional[Dict[str, Any]] = None, nguon: str = "",
                 khoa: str = "", kenh_ds: Sequence[str] = ()) -> Optional[Dong]:
    """Dựng một dòng hợp lệ (bộ phận/loại lạ → None). Lỗi không kèm chữ ký → tự tính từ câu lỗi; thiếu khoá →
    băm của nội dung + giây (cùng câu, cùng giây = cùng sự kiện)."""
    if bo_phan not in BO_PHAN or loai not in LOAI:
        return None
    luc = float(luc) if luc else time.time()
    nd = " ".join(str(noi_dung or "").split())[:2000]
    ck = chu_ky_ or (chu_ky(nd, kenh_ds) if loai == "loi" and nd else "")
    so_ = json.dumps(so or {}, ensure_ascii=False, default=str)[:4000]
    khoa = khoa or "ghi|" + bam("|".join((bo_phan, loai, kenh, ma_goi, ck, nd, "%.0f" % luc)), 16)
    return (luc, bo_phan, loai, str(kenh or ""), str(ma_goi or ""), ck, nd, so_, str(nguon or ""), khoa)


def ghi_nhieu(con: sqlite3.Connection, dong: Iterable[Optional[Dong]]) -> int:
    """Chèn nhiều dòng (trùng khoá bỏ qua). Trả số dòng mới."""
    truoc = con.total_changes
    con.executemany(CHEN, [d for d in dong if d])
    return con.total_changes - truoc


def ghi(goc: str, bo_phan: str, loai: str, *, kenh: str = "", ma_goi: str = "", chu_ky: str = "",
        noi_dung: Any = "", so: Optional[Dict[str, Any]] = None, nguon: str = "", khoa: str = "",
        luc: Optional[float] = None) -> bool:
    """Ghi MỘT sự kiện cho bộ phận `bo_phan`. KHÔNG BAO GIỜ ném lỗi, chờ khoá tối đa 0,5 giây; trùng `khoa` bỏ
    qua. Trả True khi đã thêm dòng mới."""
    try:
        d = dong_su_kien(bo_phan, loai, luc=luc, kenh=kenh, ma_goi=ma_goi, chu_ky_=chu_ky, noi_dung=noi_dung,
                         so=so, nguon=nguon, khoa=khoa, kenh_ds=cac_kenh(goc))
        if d is None:
            return False
        con = mo(goc, cho=0.5)
        try:
            n = ghi_nhieu(con, [d])
            con.commit()
            return n > 0
        finally:
            con.close()
    except Exception:  # noqa: BLE001 — não hỏng không bao giờ làm hỏng bộ phận
        return False
