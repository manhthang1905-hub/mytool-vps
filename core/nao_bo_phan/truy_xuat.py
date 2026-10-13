"""TRUY XUẤT `nho()` — không LLM, chỉ đọc chỉ mục (< 50 ms), + `dong_loi_dang_tang` cho `core.nao xem`.

Xếp hạng một nơ-ron của bộ phận (trạng thái khác `nghi`):

    điểm = (SAN_KHOP + độ khớp) × trọng số × độ tươi        [× (1 + LAN_TRUYEN) nếu lan 1 bước tới được]

* độ khớp = tổng −bm25 trên hai chỉ mục FTS5 (trigram cho tiếng Nhật, unicode61 bỏ dấu cho tiếng Việt), chia cho
  nơ-ron khớp nhất → [0, 1]; không khớp chữ nào = 0 (vẫn xếp được nhờ sàn `SAN_KHOP`);
* trọng số = mẫu Thompson Beta(α, β) với bài học; với lỗi = 1 − e^(−(số lần 7 ngày + 1)/5) (lỗi càng dày càng nặng),
  nơ-ron CẢNH BÁO nhân thêm `TRONG_CANH_BAO`;
* độ tươi = 0,5^(tuổi từ lần cuối / `NUA_DOI_NGAY` ngày);
* lan 1 bước: nơ-ron cùng nối vào một nốt thực thể (kênh, khâu, engine, bộ chọn, mã kiểm) với 3 nơ-ron khớp nhất,
  hoặc vào kênh được nhắc tên trong ngữ cảnh, được thưởng.

Có `quyet_dinh` thì ghi bảng `dung` (MỘT dòng mỗi quyết định — gọi lại cùng mã không ghi thêm) để chấm công về sau;
`TI_LE_DOI_CHUNG` quyết định là ĐỐI CHỨNG: trả danh sách rỗng, ghi `doi_chung = 1`. Gọi không có `quyet_dinh` (xem tay)
thì luôn trả đủ. `khoi_loi_nhac` = khối ≤ 6 dòng cho lời nhắc của khâu viết (mẫu ngẫu nhiên gieo theo mã quyết định →
cùng quyết định luôn cùng kết quả, kể cả đối chứng).
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

from ._chung import (BO_PHAN, CANH_BAO, DANG, DANG_DUNG, DUNG_CHO_BO_PHAN, LAN_TRUYEN, MA_KIEM_BO_PHAN, NGHI,
                     NGUON_NGU, NUA_DOI_NGAY, SAN_KHOP, TAI_PHAT, TAM_LANG, TEN_TRANG_THAI, THU_THACH, TI_LE_DOI_CHUNG,
                     TRONG_CANH_BAO, UNG_VIEN, doc_chu, doc_ghi_chu, duong_db, ngay_gio)

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
    if con.execute("SELECT 1 FROM dung WHERE quyet_dinh = ? AND bo_phan = ?", (quyet_dinh, bo_phan)).fetchone():
        return                                  # một quyết định MỘT dòng (lời nhắc dựng lại nhiều lần trong một lượt)
    con.execute("INSERT INTO dung(quyet_dinh, bo_phan, bai_hoc, doi_chung, luc) VALUES (?,?,?,?,?)",
                (quyet_dinh, bo_phan, json.dumps(ids, ensure_ascii=False), doi_chung, time.time()))
    con.commit()


def nho(goc: str, bo_phan: str, ngu_canh: str, k: int = 5, quyet_dinh: str = "", *,
        rng: Optional[random.Random] = None, bay_gio: Optional[float] = None,
        loi_nhac: bool = False, kenh: str = "") -> List[Dict[str, Any]]:
    """Top-k nơ-ron của `bo_phan` cho `ngu_canh`: `[{id, loai, bo_phan, cau, trang_thai, diem, duong}]`. KHÔNG
    BAO GIỜ ném lỗi (hỏng → []). `loi_nhac=True`: chỉ ứng viên được vào lời nhắc — bài học tự rút có
    `vao_loi_nhac`, lỗi/cảnh báo ĐANG có của bộ phận và mục kiểm chất lượng thuộc bộ phận (`MA_KIEM_BO_PHAN`); có
    `kenh` thì bỏ nơ-ron gắn kênh KHÁC (mỗi kênh một tệp khán giả — không bê bài kênh này sang kênh kia)."""
    try:
        return _nho(goc, bo_phan, ngu_canh, k, quyet_dinh, rng or random.Random(), bay_gio or time.time(), loi_nhac,
                    kenh)
    except Exception:  # noqa: BLE001 — não hỏng = như không có não
        return []


_COT_NO_RON = "id, loai, bo_phan, cau, trang_thai, duong, alpha, beta, so_lan_7, lan_cuoi, muc, su_co_48, kenh"


def _ung_vien(con: sqlite3.Connection, bo_phan: str, loi_nhac: bool, kenh: str = "") -> Dict[str, tuple]:
    if not loi_nhac:
        ds = con.execute("SELECT {0} FROM no_ron WHERE bo_phan = ? AND trang_thai != ?".format(_COT_NO_RON),
                         (bo_phan, NGHI))
    else:
        ma_kiem = [t for t, bp in MA_KIEM_BO_PHAN if bp == bo_phan]
        dk_kiem = " OR ".join(["id IN (SELECT tu FROM lien_ket WHERE toi LIKE ? ESCAPE '!')"] * len(ma_kiem)) or "0"
        ds = con.execute(
            "SELECT {0} FROM no_ron WHERE (loai = 'bai-hoc' AND bo_phan = ? AND nguon = ? AND vao_loi_nhac = 1 AND "
            "trang_thai != ?) OR (loai = 'loi' AND trang_thai IN (?, ?) AND (bo_phan = ? OR (bo_phan = "
            "'kiem-chat-luong' AND ({1}))))".format(_COT_NO_RON, dk_kiem),
            [bo_phan, NGUON_NGU, NGHI, DANG, TAI_PHAT, bo_phan] +
            ["thuc-the/ma-kiem/" + t.replace("_", "!_") + "%" for t in ma_kiem])
    hop = {kenh, re.sub(r"[-_]v\d+$", "", kenh, flags=re.IGNORECASE)}        # bản thử `…-v2` = kênh gốc
    ra = {r[0]: r for r in ds if not kenh or hop & set(json.loads(r[12] or "[]") or [kenh])}
    if loi_nhac:
        # 13/10/2026 — chống học sai lan kênh: bài GỘP nhiều kênh (vd "cụm trí tuệ thua 6/9" trong khi TL4 thắng 83%
        # ở cụm ấy) không vào lời nhắc — chỉ bài gắn CHÍNH kênh. Cảnh báo (không chặn video, vd "mô tả không có
        # chương" lọt vào lời nhắc tiêu đề) không phải việc người viết sửa được → bỏ. Lọc Ở ĐÂY để bảng `dung`
        # chỉ ghi đúng thứ đã đưa ra (chấm công đợt 3).
        ra = {i: r for i, r in ra.items()
              if (r[1] != "bai-hoc" or (kenh and json.loads(r[12] or "[]"))) and (r[1] == "bai-hoc" or r[10] != CANH_BAO)}
    return ra


def _nho(goc: str, bo_phan: str, ngu_canh: str, k: int, quyet_dinh: str, rng: random.Random, bay_gio: float,
         loi_nhac: bool = False, kenh: str = "") -> List[Dict[str, Any]]:
    p = duong_db(goc)
    if bo_phan not in BO_PHAN or not os.path.isfile(p):
        return []
    con = sqlite3.connect(p, timeout=0.5)
    try:
        if quyet_dinh and rng.random() < TI_LE_DOI_CHUNG:
            _ghi_dung(con, quyet_dinh, bo_phan, [], 1)
            return []
        ung = _ung_vien(con, bo_phan, loi_nhac, kenh)
        khop: Dict[str, float] = {}
        for bang, q in (("chi_muc_viet", truy_van_viet(ngu_canh)), ("chi_muc_tri", truy_van_tri(ngu_canh))):
            if q:
                for id_, s in con.execute("SELECT id, -bm25({0}) FROM {0} WHERE {0} MATCH ?".format(bang), (q,)):
                    if id_ in ung:
                        khop[id_] = khop.get(id_, 0.0) + max(0.0, s)
        dinh = max(khop.values(), default=0.0)
        diem: Dict[str, float] = {}
        for id_, (_, loai, _, _, _, _, a, b, so7, lan_cuoi, muc, _s48, _k) in ung.items():
            tr = rng.betavariate(max(a or 1, 1e-3), max(b or 1, 1e-3)) if loai == "bai-hoc" else \
                (1 - math.exp(-((so7 or 0) + 1) / 5.0)) * (TRONG_CANH_BAO if muc == CANH_BAO else 1.0)
            tuoi = 0.5 ** (max(0.0, bay_gio - lan_cuoi) / 86400 / NUA_DOI_NGAY) if lan_cuoi else 0.5
            diem[id_] = (SAN_KHOP + (khop.get(id_, 0.0) / dinh if dinh > 0 else 0.0)) * tr * tuoi
        hat = sorted(khop, key=khop.get, reverse=True)[:3]
        the = {t for (t,) in con.execute("SELECT DISTINCT toi FROM lien_ket WHERE toi LIKE 'thuc-the/kenh/%'")
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
    """Nơ-ron LỖI (không tính cảnh báo) đang xảy ra / tái phát, xếp theo nhịp SỰ CỐ khác nhau 48h qua so với 5 ngày
    trước (`no_ron.ti_le_tang`), rồi số sự cố 48h, rồi số lần 7 ngày (chỉ đọc chỉ mục). Không có kho → []."""
    p = duong_db(goc)
    if not os.path.isfile(p):
        return []
    con = sqlite3.connect(p, timeout=0.5)
    try:
        dk, ts = ("AND bo_phan = ?", (bo_phan,)) if bo_phan else ("", ())
        return [{"id": r[0], "bo_phan": r[1], "cau": r[2], "trang_thai": r[3], "so_lan_7": r[4], "so_lan": r[5],
                 "kenh": json.loads(r[6] or "[]"), "su_co_48": r[7] or 0, "ti_le_tang": r[8] or 0.0}
                for r in con.execute(
            "SELECT id, bo_phan, cau, trang_thai, so_lan_7, n, kenh, su_co_48, ti_le_tang FROM no_ron WHERE loai = "
            "'loi' AND trang_thai IN (?, ?) AND COALESCE(muc, 'loi') != ? {0} ORDER BY ti_le_tang DESC, su_co_48 DESC, "
            "so_lan_7 DESC, lan_cuoi DESC LIMIT ?".format(dk), (DANG, TAI_PHAT, CANH_BAO) + ts + (n,))]
    finally:
        con.close()


def dong_loi(x: Dict[str, Any], n_chu: int = 140) -> str:
    cau = x["cau"] if len(x["cau"]) <= n_chu else x["cau"][: n_chu - 1] + "…"
    return "[{0}] {1}×/7 ngày, {2} kênh, {3} sự cố/48h ×{4} so 5 ngày trước{5}: {6}".format(
        x["bo_phan"], x["so_lan_7"], len(x["kenh"]), x.get("su_co_48", 0), x.get("ti_le_tang", 0),
        ", " + TEN_TRANG_THAI[x["trang_thai"]].upper() if x["trang_thai"] == TAI_PHAT else "", cau)


def dong_loi_dang_tang(goc: str, n: int = 5) -> List[str]:
    """Mục ngắn cho `python -m core.nao xem` ([] khi chưa có não bộ phận / không có lỗi đang xảy ra)."""
    ds = loi_dang_tang(goc, n)
    if not ds:
        return []
    return ["  - " + dong_loi(x) for x in ds] + [
        "  (sổ tay từng bộ phận: nao/bo-phan/<bộ phận>/so-tay.md · `python -m core.nao_bo_phan xem`)"]


def tom_tat(goc: str, bay_gio: Optional[float] = None) -> List[Dict[str, Any]]:
    """Mỗi bộ phận một dòng số (chỉ đọc kho): sự kiện 7 ngày, lỗi theo trạng thái, cảnh báo đang có, bài học tự rút
    theo trạng thái, bài bản chiếu còn sống, lần ngủ cuối. Kho thiếu / hỏng → ném (nơi gọi tự bọc)."""
    bay_gio = bay_gio or time.time()
    con = sqlite3.connect("file:{0}?mode=ro".format(duong_db(goc).replace("\\", "/")), uri=True, timeout=0.5)
    try:
        ra = {bp: {"ma": bp, "ten": ten, "su_kien_7": 0, "loi": {}, "canh_bao": 0, "bai_ngu": {}, "ban_chieu": 0,
                   "ngu_cuoi": "", "ngu_ap": 0} for bp, ten in BO_PHAN.items()}
        for bp, n in con.execute("SELECT bo_phan, COUNT(*) FROM su_kien WHERE luc >= ? GROUP BY 1",
                                 (bay_gio - 7 * 86400,)):
            if bp in ra:
                ra[bp]["su_kien_7"] = n
        for bp, loai, tt, muc, nguon, n in con.execute(
                "SELECT bo_phan, loai, trang_thai, COALESCE(muc, 'loi'), COALESCE(nguon, ''), COUNT(*) FROM no_ron "
                "GROUP BY 1, 2, 3, 4, 5"):
            x = ra.get(bp)
            if x is None:
                continue
            if loai == "loi" and muc == CANH_BAO:
                x["canh_bao"] += n if tt in (DANG, TAI_PHAT) else 0
            elif loai == "loi":
                x["loi"][tt] = x["loi"].get(tt, 0) + n
            elif nguon == NGUON_NGU:
                x["bai_ngu"][tt] = x["bai_ngu"].get(tt, 0) + n
            elif tt != NGHI:
                x["ban_chieu"] += n
        try:
            for bp, luc, ap in con.execute("SELECT bo_phan, MAX(luc), ap FROM giac_ngu WHERE loi = '' GROUP BY 1"):
                if bp in ra:
                    ra[bp]["ngu_cuoi"], ra[bp]["ngu_ap"] = ngay_gio(luc), ap or 0
        except sqlite3.Error:           # kho đợt 1 chưa có bảng giấc ngủ
            pass
        return list(ra.values())
    finally:
        con.close()


def dong_bo_phan(goc: str) -> List[str]:
    """Mục cho `core.nao xem`: một dòng mỗi bộ phận CÓ hoạt động + đường tới bản đồ ([] khi chưa có não)."""
    if not os.path.isfile(duong_db(goc)):
        return []
    ds = [x for x in tom_tat(goc) if x["su_kien_7"] or x["bai_ngu"] or sum(x["loi"].values())]
    tt = lambda d, *k: sum(d.get(i, 0) for i in k)  # noqa: E731
    return ["  - {0}: {1} sự kiện/7n · lỗi {2} đang/{3} lặng · {4} cảnh báo · bài tự rút {5} đang dùng/{6} ứng viên/"
            "{7} thử thách · {8} bản chiếu · ngủ {9}".format(
                x["ma"], x["su_kien_7"], tt(x["loi"], DANG, TAI_PHAT), tt(x["loi"], TAM_LANG), x["canh_bao"],
                tt(x["bai_ngu"], DANG_DUNG), tt(x["bai_ngu"], UNG_VIEN), tt(x["bai_ngu"], THU_THACH), x["ban_chieu"],
                x["ngu_cuoi"][:10] or "chưa") for x in ds] + [
        "  (bản đồ: nao/bo-phan/_ban-do.md · sổ tay: nao/bo-phan/<bộ phận>/so-tay.md · nhật ký: .../nhat-ky.md)"]


#: Đầu khối não bộ phận trong lời nhắc của khâu viết.
DAU_KHOI = "BÀI HỌC TỪ NÃO BỘ PHẬN (tự rút, có bằng chứng):"


def khoi_loi_nhac(goc: str, dung_cho: str, ngu_canh: str = "", quyet_dinh: str = "", k: int = 6,
                  kenh: str = "") -> str:
    """Khối ≤ `k` dòng cho lời nhắc của khâu `dung_cho` ("chon" | "bien_tap" | "kich_ban" | "tieu_de" | "bia"):
    bài học TỰ RÚT (`nguon: ngu`, `vao_loi_nhac`) + lỗi/cảnh báo đang có của bộ phận và mục kiểm thuộc bộ phận — bài
    bản chiếu đã có ở `chien_luoc.bai_hoc.khoi_chu`, không nhắc lại; có `kenh` thì bỏ nơ-ron gắn kênh khác. Có
    `quyet_dinh` thì ghi bảng `dung`; 15% đối chứng → "". Không có gì / hỏng → "" (lời nhắc y hệt từng byte)."""
    try:
        bp = DUNG_CHO_BO_PHAN.get(str(dung_cho or ""))
        if not bp:
            return ""
        ds = nho(goc, bp, ngu_canh or BO_PHAN[bp], k, quyet_dinh, rng=random.Random(quyet_dinh or None),
                 loi_nhac=True, kenh=kenh)
        dong = []
        for x in ds[:k]:
            dau, _ = doc_ghi_chu(doc_chu(os.path.join(goc, x["duong"])) or "")
            if x["loai"] == "bai-hoc":
                dong.append("- {0} ({1} · {2})".format(x["cau"], TEN_TRANG_THAI.get(x["trang_thai"], x["trang_thai"]),
                                                       "kênh " + ", ".join(dau["kenh"]) if dau.get("kenh")
                                                       else "gộp nhiều kênh — tiên nghiệm"))
                continue
            dong.append("- Đang gặp{0}: {1} ({2} sự cố/48h)".format(
                " (cảnh báo)" if dau.get("muc") == CANH_BAO else "", " ".join(str(dau.get("vi_du") or x["cau"])
                                                                            .split())[:200], dau.get("su_co_48h", 0)))
        return (DAU_KHOI + "\n" + "\n".join(dong)) if dong else ""
    except Exception:  # noqa: BLE001 — não hỏng = lời nhắc như cũ
        return ""
