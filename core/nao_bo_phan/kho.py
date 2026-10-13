"""Kho SQLite `nao/bo-phan.db` (WAL) + `ghi()` — ký ức thô của mọi bộ phận.

Bảng: `su_kien` (ký ức thô, KHÔNG BAO GIỜ xoá), `con_tro` (đã gom mỗi tệp tới đâu), `dung` (quyết định nào đã được
đưa những nơ-ron nào — chấm công về sau; MỘT dòng mỗi quyết định), `giac_ngu` (mỗi lần một bộ phận ngủ: lệnh đề xuất
/ áp / bỏ + lý do, giây, token), `meta` (phiên luật ký, ngày soát). Bảng chỉ mục (`no_ron`, `chi_muc_tri`,
`chi_muc_viet`, `lien_ket`) dựng lại được hoàn toàn từ vault markdown (`no_ron.dung_lai_chi_muc`). Cột mới của bảng
cũ được `mo()` thêm bằng `ALTER TABLE` (kho cũ không phải dựng lại).
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
CREATE TABLE IF NOT EXISTS giac_ngu(id INTEGER PRIMARY KEY, luc REAL, bo_phan TEXT, tu_id INTEGER, den_id INTEGER,
    de_xuat INTEGER DEFAULT 0, ap INTEGER DEFAULT 0, bo INTEGER DEFAULT 0, giay REAL, ky_tu INTEGER,
    token_vao INTEGER, token_ra INTEGER, chi_tiet TEXT DEFAULT '{}', loi TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS meta(khoa TEXT PRIMARY KEY, gia_tri TEXT);
"""
#: Cột thêm sau đợt 1 (bảng, cột, kiểu) — kho cũ được thêm bằng ALTER TABLE, giá trị điền ở lượt dựng chỉ mục sau.
_COT_MOI = (("no_ron", "muc", "TEXT DEFAULT 'loi'"), ("no_ron", "nguon", "TEXT DEFAULT ''"),
            ("no_ron", "su_co_48", "INTEGER DEFAULT 0"), ("no_ron", "ti_le_tang", "REAL DEFAULT 0"),
            ("no_ron", "vao_loi_nhac", "INTEGER DEFAULT 0"))
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
        for bang, cot, kieu in _COT_MOI:
            if cot not in {r[1] for r in con.execute("PRAGMA table_info({0})".format(bang))}:
                con.execute("ALTER TABLE {0} ADD COLUMN {1} {2}".format(bang, cot, kieu))
        con.commit()
        _DA_DUNG.add(p)
    return con


def doc_meta(con: sqlite3.Connection, khoa: str) -> str:
    r = con.execute("SELECT gia_tri FROM meta WHERE khoa = ?", (khoa,)).fetchone()
    return str(r[0]) if r else ""


def dat_meta(con: sqlite3.Connection, khoa: str, gia_tri: Any) -> None:
    con.execute("INSERT OR REPLACE INTO meta(khoa, gia_tri) VALUES (?,?)", (khoa, str(gia_tri)))


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
