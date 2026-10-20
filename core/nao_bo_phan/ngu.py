"""GIẤC NGỦ ĐÊM — `python -m core.nao_bo_phan ngu` (đợt 2): mã tính số → Claude Max Opus đọc số + sổ tay → trả LỆNH
sửa sổ bài học → mã kiểm bằng chứng rồi mới áp (kiểu ACE: LLM không bao giờ viết lại cả sổ; ExpeL: so cặp được/hỏng).

═══ LUẬT (mỗi luật một câu) ═══

1. Bộ phận ngủ khi có ≥ `SU_KIEN_MOI_TOI_THIEU` sự kiện mới từ lần ngủ THÀNH CÔNG trước; mỗi đêm tối đa
   `BO_PHAN_TOI_DA_DEM` bộ phận, bận nhất trước — mỗi bộ phận đúng MỘT lượt gọi Claude Max (thuê bao; KHÔNG bao giờ ví
   ShopAPI, không đường lui về ví).
2. Bảng số do MÃ tính (không LLM), ≤ `TRAN_TO_SO` ký tự, mọi dòng mang mã sự kiện `#id` thật.
3. LLM chỉ trả ≤ `LENH_TOI_DA` lệnh `them | ung_ho | phan_doi | sua | nghi | noi`; mọi lệnh phải trích mã sự kiện CÓ
   THẬT của chính bộ phận — một mã sai là bỏ cả lệnh; bài mới cần ≥ 2 sự kiện và câu có số.
4. Bài mới trùng bài cũ (cụm 3 ký tự, Jaccard ≥ `GIONG_TRUNG`) → thành lệnh ủng hộ bài cũ; khuyên hạ chất lượng → bỏ
   ("thà không đăng còn hơn sản phẩm kém"); nói chuyện tiền / kênh / nhịp đăng → chỉ là gợi ý, không vào lời nhắc.
5. Bài mới là ứng viên, α = 1 + min(3, số bằng chứng), β = 1; ủng hộ / phản đối cộng min(3, số bằng chứng MỚI) vào
   α / β. α/(α+β) < 0,4 → nghỉ (đang dùng thì xuống thử thách trước); α ≥ 4 và ≥ 0,75 → đang dùng; đang dùng tụt dưới
   0,6 → thử thách.
6. Quá `BAI_HOC_TOI_DA` bài còn sống → nghỉ bài yếu nhất (α/(α+β) thấp nhất, cũ nhất trước).
7. Một bộ phận hỏng không chặn bộ phận khác; hỏng (LLM / JSON) thì không dời mốc — đêm sau ngủ lại.
8. Soát tuần (Chủ nhật, hoặc `--soat`), chỉ mã: đang dùng mà ≥ `NGAY_CU` ngày không xác nhận → thử thách; bài không
   còn bằng chứng có thật → nghỉ; cặp cùng phạm vi, ngược hướng, câu na ná (≥ 0,5) → cả hai thử thách; nơ-ron mồ côi
   (không nối nốt thực thể nào) → báo trong nhật ký.

Bài học tự rút: `nao/bo-phan/<bộ phận>/bai-hoc/BH-N<băm>.md` (`nguon: ngu`); mỗi lần ngủ một dòng bảng `giac_ngu` và
một khối `<bộ phận>/nhat-ky.md`.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import statistics
import time
from collections import Counter
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import kho, no_ron
from ._chung import (BAI_HOC_TOI_DA, BO_PHAN, BO_PHAN_TOI_DA_DEM, DANG_DUNG, GIONG_TRUNG, GOC, LENH_TOI_DA,
                     NGAY_CAP, NGAY_CU, NGAY_TO_SO, NGHI, NGUON_NGU, SU_KIEN_MOI_TOI_THIEU, TEN_TRANG_THAI, THU_THACH,
                     THUC_THE, TRAN_TO_SO, UNG_VIEN, bam, chuan_hoa, doc_chu, duong_vault, ghi_neu_khac, ghi_nhat_ky,
                     giong, jdong, la_canh_bao, lk, lk_the, luc_tu, ngay_gio, thuc_the, ve_ghi_chu)

NGAY = 86400.0
LOAI_LENH = ("them", "ung_ho", "phan_doi", "sua", "nghi", "noi")
#: Soát: hai bài cùng phạm vi, ngược hướng, câu na ná ≥ ngần này = mâu thuẫn. Đo trên dữ liệu thật 13/10: hai bài khác
#: tuyến (không mâu thuẫn) 0,36; "chờ 15 phút giảm hỏng" ⇄ "chờ 15 phút không giảm hỏng" 0,71.
GIONG_MAU_THUAN = 0.5
#: Lưới an toàn bằng mã cho hai luật của chủ (lời nhắc đã dặn; đây là chốt thứ hai).
_RE_HA_CHAT = re.compile(r"hạ chất lượng|giảm chất lượng|bỏ (?:qua )?(?:bước )?kiểm|tắt (?:bước )?kiểm|bỏ qua qa|"
                         r"clip từ ảnh|model (?:rẻ|yếu)|haiku|chấp nhận (?:lỗi|bản kém)|đăng (?:tạm|bản kém|bản lỗi)",
                         re.I)
_RE_TIEN_KENH = re.compile(r"\btiền\b|\bví\b|\bnạp\b|chi phí|\busd\b|mở kênh|đóng kênh|xo[áa] kênh|nhịp đăng|"
                           r"lịch đăng|đổi giọng", re.I)
Goi = Callable[[str, str], str]


# ── đọc sự kiện ──────────────────────────────────────────────────────────────

def doc_su_kien(con: sqlite3.Connection, bp: str, tu_luc: float) -> List[Dict[str, Any]]:
    ra = []
    for id_, luc, loai, kenh, goi, ck, nd, so, nguon in con.execute(
            "SELECT id, luc, loai, kenh, ma_goi, chu_ky, noi_dung, so, nguon FROM su_kien WHERE bo_phan = ? AND "
            "luc >= ? ORDER BY luc, id", (bp, tu_luc)):
        try:
            so_ = json.loads(so or "{}")
        except ValueError:
            so_ = {}
        ra.append({"id": id_, "luc": luc, "loai": loai, "kenh": kenh or "", "ma_goi": goi or "", "chu_ky": ck or "",
                   "nd": nd or "", "so": so_ if isinstance(so_, dict) else {}, "nguon": nguon or ""})
    return ra


def can_ngu(con: sqlite3.Connection, chi: Sequence[str] = (), toi_da: int = BO_PHAN_TOI_DA_DEM,
            toi_thieu: int = SU_KIEN_MOI_TOI_THIEU) -> List[Tuple[str, int, int, int]]:
    """[(bộ phận, số sự kiện mới, từ id, tới id)] cần ngủ — bận nhất trước, cắt `toi_da`."""
    moc = dict(con.execute("SELECT bo_phan, MAX(den_id) FROM giac_ngu WHERE loi = '' GROUP BY 1"))
    ds = []
    for bp in chi or BO_PHAN:
        tu = int(moc.get(bp) or 0)
        n, den = con.execute("SELECT COUNT(*), MAX(id) FROM su_kien WHERE bo_phan = ? AND id > ?", (bp, tu)).fetchone()
        if n >= toi_thieu:
            ds.append((bp, n, tu, int(den)))
    return sorted(ds, key=lambda x: (-x[1], x[0]))[:max(0, toi_da)]


# ── bảng số (mã tính, không LLM) ─────────────────────────────────────────────

_DUOC_TT = ("xong", "xac-nhan", "da-len-lich", "da-ghim", "da-gui")


def ket(e: Dict[str, Any]) -> str:
    """"hong" | "duoc" | "" — sự kiện là thất bại, thành công hay trung tính."""
    so, loai = e["so"], e["loai"]
    if loai == "loi":
        return "hong"
    tt = str(so.get("trang_thai") or "")
    if loai in ("do", "ket_qua"):
        if tt == "hong" or so.get("ok") is False or so.get("dat") is False or so.get("ket") == "truot" or \
                "loi" in tt or "hong" in tt:
            return "hong"
        if tt in _DUOC_TT or so.get("ok") or so.get("dat") or so.get("ket") == "thang":
            return "duoc"
    return ""


def _tv(xs: Sequence[float]) -> float:
    return round(statistics.median(xs), 1) if xs else 0.0


def _p90(xs: Sequence[float]) -> float:
    s = sorted(xs)
    return round(s[int(0.9 * (len(s) - 1))], 1) if s else 0.0


def _ma(ds: Sequence[Dict[str, Any]], n: int = 3) -> str:
    return " ".join("#{0}".format(e["id"]) for e in list(ds)[-n:])


def _pt(a: int, b: int) -> str:
    return "{0:.0f}%".format(100.0 * a / b) if b else "—"


def _ngan(e: Dict[str, Any], n: int = 110) -> str:
    s = " ".join(e["nd"].split())
    return s if len(s) <= n else s[:n - 1] + "…"


_SO_HIEN = ("khau", "so_lan", "giay", "trang_thai", "ket", "diem", "lan_tai_moi", "mo_hinh", "kieu", "quyet")


def _dong_sk(e: Dict[str, Any]) -> str:
    so = ", ".join("{0}={1}".format(k, e["so"][k]) for k in _SO_HIEN if e["so"].get(k) not in (None, "", []))
    return "#{0} {1}{2} {3}{4}".format(e["id"], time.strftime("%m-%d %H:%M", time.localtime(e["luc"])),
                                       " [{0}]".format(e["kenh"]) if e["kenh"] else "", _ngan(e),
                                       " {" + so + "}" if so else "")


def _muc_khau(ds: List[Dict[str, Any]]) -> List[str]:
    nhom: Dict[str, List[Dict[str, Any]]] = {}
    for e in ds:
        if e["so"].get("khau"):
            nhom.setdefault(str(e["so"]["khau"]), []).append(e)
    ra = []
    for kh, es in sorted(nhom.items(), key=lambda x: -len(x[1])):
        kt = [e for e in es if e["loai"] == "do" and e["so"].get("trang_thai") in ("xong", "hong")]
        hong = [e for e in kt if e["so"].get("trang_thai") == "hong"]
        lai = [e for e in kt if int(e["so"].get("so_lan") or 0) > 1]
        gi = [float(e["so"]["giay"]) / 60 for e in kt if isinstance(e["so"].get("giay"), (int, float))]
        loi = [e for e in es if e["loai"] == "loi"]
        ra.append("- khâu {0}: {1} lượt kết thúc · hỏng {2} ({3}) · làm lại >1 lần {4} ({5}) · thời gian trung vị "
                  "{6} phút, p90 {7} phút · {8} dòng lỗi / {9} sự cố{10}{11}".format(
                      kh, len(kt), len(hong), _pt(len(hong), len(kt)), len(lai), _pt(len(lai), len(kt)), _tv(gi),
                      _p90(gi), len(loi), len({no_ron.su_co(e["kenh"], e["ma_goi"], e["luc"]) for e in loi}),
                      " · hỏng: " + _ma(hong) if hong else "", " · làm lại: " + _ma(lai) if lai else ""))
    return ra


def _muc_nhom(ds: List[Dict[str, Any]], khoa: Callable[[Dict[str, Any]], Iterable[str]], nhan: str,
              loai: Sequence[str] = ("do", "ket_qua", "loi")) -> List[str]:
    """Theo một chiều (kênh, engine, giờ) × hoàn cảnh (khâu/nguồn): được / hỏng tính trên sự kiện KẾT QUẢ (đo,
    kết quả — một lượt một sự kiện), dòng lỗi đếm riêng — không trộn lượt gọi LLM với kết quả video."""
    dem: Dict[str, Counter] = {}
    vd: Dict[str, List[Dict[str, Any]]] = {}
    for e in ds:
        k = ket(e)
        if not k or e["loai"] not in loai:
            continue
        for g in khoa(e):
            g = "{0} · {1}".format(g, _ngu_canh(e))
            dem.setdefault(g, Counter())["dong_loi" if e["loai"] == "loi" else k] += 1
            vd.setdefault(g, []).append(e)
    return ["- {0} {1}: được {2} · hỏng {3} (tỉ lệ hỏng {4}){5} · ví dụ hỏng {6}".format(
        nhan, g, c["duoc"], c["hong"], _pt(c["hong"], c["duoc"] + c["hong"]),
        " · {0} dòng lỗi".format(c["dong_loi"]) if c["dong_loi"] else "",
        _ma([e for e in vd[g] if ket(e) == "hong"]) or "—")
        for g, c in sorted(dem.items(), key=lambda x: -sum(x[1].values())) if sum(c.values()) >= 2][:12]


def _muc_loi_lap(con: sqlite3.Connection, bp: str, ds: List[Dict[str, Any]], bay_gio: float) -> List[str]:
    nhom: Dict[str, List[Dict[str, Any]]] = {}
    for e in ds:
        if e["loai"] == "loi" and e["chu_ky"]:
            nhom.setdefault(e["chu_ky"], []).append(e)
    xep = sorted(nhom.items(), key=lambda x: (-len({no_ron.su_co(e["kenh"], e["ma_goi"], e["luc"]) for e in x[1]}),
                                              -len(x[1])))[:8]
    ra = []
    for ck, es in xep:
        sc = {no_ron.su_co(e["kenh"], e["ma_goi"], e["luc"]) for e in es}
        canh = all(la_canh_bao(e["nguon"], e["so"]) for e in es)
        ra.append("- [{0}] {1}{2} — {3} lần, {4} sự cố, kênh {5}, từ {6} tới {7} · {8}".format(
            ck, chuan_hoa(es[-1]["nd"])[:140], " (CẢNH BÁO: dự phòng đã cứu / không chặn)" if canh else "", len(es),
            len(sc), ",".join(sorted({e["kenh"] for e in es if e["kenh"]})) or "—", ngay_gio(es[0]["luc"])[5:],
            ngay_gio(es[-1]["luc"])[5:], _ma(es)))
        for sid, sluc, snd in con.execute("SELECT id, luc, noi_dung FROM su_kien WHERE bo_phan = ? AND chu_ky = ? AND "
                                          "loai = 'sua' ORDER BY luc DESC LIMIT 2", (bp, ck)):
            truoc, sau = (con.execute("SELECT COUNT(*) FROM su_kien WHERE bo_phan = ? AND chu_ky = ? AND loai = 'loi' "
                                      "AND luc >= ? AND luc < ?", (bp, ck, a, b)).fetchone()[0]
                          for a, b in ((sluc - 7 * NGAY, sluc), (sluc, sluc + 7 * NGAY)))
            ra.append("    · sửa #{0} {1} «{2}»: 7 ngày trước {3} lần · sau {4} lần (đã {5:.1f} ngày)".format(
                sid, ngay_gio(sluc)[5:], " ".join(str(snd).split())[:80], truoc, sau, (bay_gio - sluc) / NGAY))
    return ra


def _ngu_canh(e: Dict[str, Any]) -> str:
    return "khâu " + str(e["so"]["khau"]) if e["so"].get("khau") else "nguồn " + e["nguon"]


def _muc_cap(ds: List[Dict[str, Any]], toi_da: int = 10) -> List[str]:
    """Cặp HỎNG ⇄ ĐƯỢC cùng hoàn cảnh (cùng khâu — hoặc cùng nguồn khi không có khâu — cùng kênh, cách ≤ `NGAY_CAP`
    ngày, gần nhất): thất bại mới nhất trước, mỗi (chữ ký/khâu, kênh) một cặp."""
    duoc: Dict[str, List[Dict[str, Any]]] = {}
    for e in ds:
        if ket(e) == "duoc":
            duoc.setdefault(_ngu_canh(e), []).append(e)
    ra, da = [], set()
    for f in reversed(ds):
        if ket(f) != "hong" or len(ra) >= toi_da:
            continue
        k = (f["chu_ky"] or _ngu_canh(f), f["kenh"])
        if k in da:
            continue
        cung = [s for s in duoc.get(_ngu_canh(f), []) if abs(s["luc"] - f["luc"]) <= NGAY_CAP * NGAY
                and (not f["kenh"] or s["kenh"] == f["kenh"])]
        if not cung:
            continue
        da.add(k)
        s = min(cung, key=lambda x: abs(x["luc"] - f["luc"]))
        ra.append("- HỎNG {0}\n  ĐƯỢC {1}".format(_dong_sk(f), _dong_sk(s)))
    return ra


#: Thuộc tính của sự kiện `chon` đem so với kết quả cùng gói (mỗi thuộc tính một nhóm dòng).
_THUOC_CHON = ("cong_thuc", "nguon", "loai", "tuyen", "cum")

#: 13/10/2026 — video < ngưỡng hiển thị của `core.kenh_khong_phat` (50 lúc ≥ 72h) là YouTube KHÔNG PHÁT (lỗi mail /
#: kênh mới), không phải content thua: ngủ đầu tiên rút "TL5 tránh tuyến người cao tuổi 3/3 trượt" (1–26 hiển thị)
#: trong khi đó là chính ngách của TL5. Kết quả như vậy không vào mục "lựa chọn → kết quả".
NGUONG_KHONG_PHAT = 50.0


def khong_duoc_phat(e: Dict[str, Any]) -> bool:
    gt = (e.get("so") or {}).get("ket_gia_tri")
    return isinstance(gt, (int, float)) and gt < NGUONG_KHONG_PHAT


def _muc_lua_chon(ds: List[Dict[str, Any]]) -> List[str]:
    """Lựa chọn → kết quả cùng mã gói (vd. công thức / loại / tuyến / cụm của nguồn đã chọn → ván thắng / trung bình /
    trượt), chỉ nhóm có ≥ 2 ván; + đếm kết quả theo trạng thái."""
    chon = {e["ma_goi"]: e for e in ds if e["loai"] == "chon" and e["ma_goi"]}
    nhom: Dict[Tuple[str, str], Counter] = {}
    vd: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for e in ds:
        if e["loai"] == "ket_qua" and e["ma_goi"] in chon and e["so"].get("ket") and not khong_duoc_phat(e):
            c = chon[e["ma_goi"]]["so"]
            for t in _THUOC_CHON:
                gt = c.get(t)
                for g in (gt if isinstance(gt, list) else [gt]):
                    if g not in (None, "", []):
                        nhom.setdefault((t, str(g)), Counter())[str(e["so"]["ket"])] += 1
                        vd.setdefault((t, str(g)), []).append(e)
    ra = ["- chọn {0}={1} → {2} (n {3}) · {4}".format(t, g, ", ".join("{0} {1}".format(k, v) for k, v in
                                                                    c.most_common()), sum(c.values()), _ma(vd[(t, g)], 4))
          for (t, g), c in sorted(nhom.items(), key=lambda x: (_THUOC_CHON.index(x[0][0]), -sum(x[1].values())))
          if sum(c.values()) >= 2][:16]
    tt: Dict[str, List[Dict[str, Any]]] = {}
    for e in ds:
        if e["loai"] in ("ket_qua", "chon"):
            so = e["so"]
            g = "{0}:{1}".format(e["loai"], so.get("trang_thai") or so.get("ket") or so.get("quyet") or
                                 ("đạt" if so.get("dat") else "chặn" if so.get("dat") is False else "?"))
            tt.setdefault(g, []).append(e)
    ra += ["- {0}: {1} lần · {2}".format(g, len(es), _ma(es)) for g, es in sorted(tt.items(), key=lambda x: -len(x[1]))
           [:10]]
    return ra


def _muc_so_do(ds: List[Dict[str, Any]]) -> List[str]:
    nhom: Dict[str, List[Dict[str, Any]]] = {}
    for e in ds:
        if e["loai"] == "do":
            nhom.setdefault("{0} {1}".format(e["nguon"], e["so"].get("khau") or e["so"].get("mo_hinh") or ""),
                            []).append(e)
    ra = []
    for g, es in sorted(nhom.items(), key=lambda x: -len(x[1]))[:10]:
        gi = [float(e["so"]["giay"]) for e in es if isinstance(e["so"].get("giay"), (int, float))]
        tk = [float(e["so"]["token_vao"]) for e in es if isinstance(e["so"].get("token_vao"), (int, float))]
        ra.append("- {0}: {1} lần · giây trung vị {2}, p90 {3}{4} · {5}".format(
            g.strip(), len(es), _tv(gi), _p90(gi), " · token vào trung vị {0:.0f}".format(_tv(tk)) if tk else "",
            _ma(es, 2)))
    return ra


def kenh_tra_kho_ds(goc: str) -> List[str]:
    """Kênh đã TRẢ KHO (`core/tra_kho.py`) — sự kiện của chúng không vào bảng số (20/10/2026: kênh bị trả vì YouTube
    không phát, kết quả trượt của nó là "kênh không được phân phối", không phải bài học nội dung). Dòng cũ GIỮ trong
    kho, chỉ bỏ khi tính. Lỗi đọc → []."""
    try:
        from ..kenh import liet_ke_kenh  # noqa: PLC0415

        return sorted(set(liet_ke_kenh(goc, ca_tra_kho=True)) - set(liet_ke_kenh(goc)))
    except Exception:  # noqa: BLE001
        return []


def to_so(con: sqlite3.Connection, bp: str, bay_gio: float, moi: int = 0, tran: int = TRAN_TO_SO,
          bo_kenh: Iterable[str] = ()) -> str:
    """Bảng số của bộ phận trong `NGAY_TO_SO` ngày qua — mã tính, mỗi dòng có mã `#id`; cắt ≤ `tran` ký tự (mục
    quan trọng trước). `bo_kenh`: kênh không tính (kênh trả kho — `kenh_tra_kho_ds`)."""
    bo_k = {str(k) for k in (bo_kenh or ())}
    ds = [e for e in doc_su_kien(con, bp, bay_gio - NGAY_TO_SO * NGAY) if not (bo_k and e["kenh"] in bo_k)]
    bo_kp = sum(1 for e in ds if e["loai"] == "ket_qua" and khong_duoc_phat(e))
    ds = [e for e in ds if not (e["loai"] == "ket_qua" and khong_duoc_phat(e))]
    dem = Counter(e["loai"] for e in ds)
    kq = Counter(ket(e) for e in ds)
    muc = [
        ("TỔNG", ["- {0} sự kiện trong {1} ngày ({2}) · mới từ lần ngủ trước: {3} · được {4} · hỏng {5} · kênh: {6}"
                  .format(len(ds), NGAY_TO_SO, ", ".join("{0} {1}".format(k, v) for k, v in sorted(dem.items())),
                          moi, kq["duoc"], kq["hong"], ", ".join(sorted({e["kenh"] for e in ds if e["kenh"]})) or "—")]
         + (["- đã BỎ {0} kết quả video < {1:.0f} hiển thị (YouTube không phát — lỗi mail/kênh mới, không phải content "
             "thua; đừng rút bài học content từ kênh ấy)".format(bo_kp, NGUONG_KHONG_PHAT)] if bo_kp else [])),
        ("LỖI LẶP (theo chữ ký; sự cố = kênh × gói/ngày; kèm lần sửa và số lần trước/sau sửa)",
         _muc_loi_lap(con, bp, ds, bay_gio)),
        ("CẶP HỎNG ⇄ ĐƯỢC CÙNG HOÀN CẢNH (cùng khâu/nguồn, cùng kênh, cách ≤ {0} ngày)".format(NGAY_CAP),
         _muc_cap(ds)),
        ("KHÂU", _muc_khau(ds)),
        ("LỰA CHỌN → KẾT QUẢ", _muc_lua_chon(ds)),
        ("THEO KÊNH", _muc_nhom(ds, lambda e: [e["kenh"]] if e["kenh"] else [], "kênh")),
        ("THEO ENGINE", _muc_nhom(ds, lambda e: [t for l, t in thuc_the(e["nguon"], e["nd"], e["so"])
                                                 if l == "engine"], "engine")),
        ("THEO GIỜ TRONG NGÀY (chỉ lượt chạy — kết quả video không có giờ thật)", _muc_nhom(
            ds, lambda e: ["{0:02d}–{1:02d}h".format(time.localtime(e["luc"]).tm_hour // 6 * 6,
                                                     time.localtime(e["luc"]).tm_hour // 6 * 6 + 5)], "khung",
            ("do", "loi"))),
        ("SỐ ĐO (sự kiện đo)", _muc_so_do(ds)),
    ]
    ra = ["BẢNG SỐ — bộ phận {0} ({1}) · lúc {2}".format(bp, BO_PHAN.get(bp, bp), ngay_gio(bay_gio))]
    dai = len(ra[0])
    for tieu_de, dong in muc:
        if not dong:
            continue
        if dai + len(tieu_de) + 8 > tran:
            break
        ra += ["", "== " + tieu_de + " =="]
        dai += len(tieu_de) + 8
        for i, d in enumerate(dong):
            if dai + len(d) + 1 > tran - 40:
                ra.append("- … (cắt cho gọn: còn {0} dòng)".format(len(dong) - i))
                dai = tran
                break
            ra.append(d)
            dai += len(d) + 1
    return "\n".join(ra)[:tran]


# ── lời nhắc + đọc lệnh ──────────────────────────────────────────────────────

def dong_bai(b: Dict[str, Any]) -> str:
    return "- {0} [{1} α{2:g} β{3:g} n{4} {5}; phạm vi: {6}] {7}".format(
        b.get("id"), b.get("trang_thai"), float(b.get("alpha") or 1), float(b.get("beta") or 1), b.get("n", 0),
        "nên" if b.get("huong") != "tranh" else "tránh", ", ".join(b.get("pham_vi") or []) or "—", b.get("cau"))


#: Đường ví (20/10/2026): ShopAPI định tuyến tên `claude-*` sang mô hình nhanh (sổ cái ví ghi "nhamay/gemini-3-flash",
#: "gpt-5.6-terra"…) — mô hình đó đọc câu "không có gì chắc thì trả rỗng" theo nghĩa đen: 15 giấc ngủ 18–20/10 ra 1
#: lệnh (Max 17/10: 11). Chẩn đoán thật 20/10 (kich-ban, 48 sự kiện mới): lời nhắc cũ → `{"lenh": []}` 3/3 lần (opus-5,
#: fable-5 ×2), cùng bảng số đó Max ra 3 lệnh. Đường ví bắt PHÂN TÍCH TRƯỚC (bước nghĩ ghi ra giấy) rồi mới ra lệnh, và
#: nhắc lại việc SAU bảng số (mô hình nhỏ nhớ đoạn cuối hơn). Luật kiểm lệnh giữ nguyên — không hạ chuẩn bài học.
VIEC_RONG = ("VIỆC: đề xuất TỐI ĐA {toi_da} lệnh sửa sổ bài học — CHỈ phần thay đổi, KHÔNG viết lại cả sổ. Không có gì "
             "chắc thì trả\n{{\"lenh\": []}} — \"không lệnh\" tốt hơn một bài học yếu.")
VIEC_PHAN_TICH = (
    "VIỆC: đọc KỸ bảng số rồi đề xuất TỐI ĐA {toi_da} lệnh sửa sổ bài học — CHỈ phần thay đổi, KHÔNG viết lại cả sổ.\n"
    "LÀM THEO 2 BƯỚC:\n"
    "  Bước 1 — \"phan_tich\": 3–6 nhận xét ngắn, mỗi nhận xét nêu SỐ và mã sự kiện (vd \"lỗi [chữ ký] lặp 166 lần ở "
    "một kênh; #13585 hỏng 12 lần rồi #13836 cùng khâu xong 1 lần\"). Ưu tiên mục LỖI LẶP và CẶP HỎNG ⇄ ĐƯỢC.\n"
    "  Bước 2 — \"lenh\": MỖI nhận xét có mã sự kiện MỚI thành MỘT lệnh: đã có bài cùng ý → \"ung_ho\" (mới xác nhận) "
    "hoặc \"phan_doi\" (mới bác) với mã MỚI; chưa có bài → \"them\" (câu: hoàn cảnh + nên/tránh gì + số, ≥ 2 mã). Bảng "
    "có sự kiện mới thì thường có ít nhất 1 lệnh đúng.")
DUOI_PHAN_TICH = (
    "\n═══ NHẮC LẠI VIỆC ═══\n"
    "Trả về DUY NHẤT một JSON {{\"phan_tich\": [\"...\"], \"lenh\": [...]}}. Mỗi lệnh trích mã sự kiện là SỐ NGUYÊN có "
    "trong BẢNG SỐ ở trên; bài mới ≥ 2 mã và câu có số; cùng ý bài cũ thì \"ung_ho\" / \"phan_doi\" — CHỈ với mã MỚI (mã "
    "> {tu_id}; mã cũ đã tính rồi, máy bỏ); không khuyên hạ chất lượng; không bàn tiền / kênh / lịch đăng.\n"
    "Mã MỚI có trong bảng: {moi}\n"
    "Mẫu một lệnh \"them\" đúng dạng (mã giả): {{\"lenh\":\"them\",\"cau\":\"Ở khâu X kênh K, khi lỗi Y lặp 12 lần "
    "trong 13707 giây thì tránh thử lại liên tục; lượt sau cùng khâu xong 1 lần trong 2094 giây\",\"huong\":\"tranh\","
    "\"pham_vi\":[\"khau/X\",\"kenh/K\"],\"vao_loi_nhac\":false,\"bang_chung\":[101,102]}}\n")
#: Đường ví: lượt đầu không lệnh nào qua kiểm → gọi THÊM một lượt, đưa lý do máy bỏ cho mô hình sửa (sinh nhiều bản +
#: tiêu chí chấm tốt; một lượt ví ≈ 15 đ). Không bao giờ hạ luật kiểm.
VONG_SUA_VI = 1


def ve_loi_nhac(bp: str, to_so_: str, so_tay: str, bai: Sequence[Dict[str, Any]], phan_tich: bool = False,
                tu_id: int = 0) -> str:
    """Lời nhắc giấc ngủ. `phan_tich=True` (đường ví — xem `VIEC_PHAN_TICH`): phân tích trước, nhắc việc ở cuối
    (kèm mốc mã sự kiện mới `tu_id`)."""
    song = [b for b in bai if b.get("trang_thai") != NGHI]
    viec = (VIEC_PHAN_TICH if phan_tich else VIEC_RONG).format(toi_da=LENH_TOI_DA)
    dang = '{"phan_tich": ["..."], "lenh": [...]}' if phan_tich else '{"lenh": [...]}'
    duoi = ""
    if phan_tich:
        moi = sorted({int(x) for x in re.findall(r"#(\d+)", to_so_ or "") if int(x) > int(tu_id or 0)})
        duoi = DUOI_PHAN_TICH.format(tu_id=int(tu_id or 0),
                                     moi=" ".join("#%d" % x for x in moi[:40]) + (" …" if len(moi) > 40 else "")
                                     if moi else "(không có — chỉ \"them\" từ lỗi lặp / cặp nếu chưa có bài)")
    return """Bạn là bộ phận «{ten}» (mã {bp}) của một dây chuyền tự làm video YouTube, đang NGỦ để rút kinh nghiệm từ
số liệu của chính mình. Bên dưới: (1) BẢNG SỐ máy tính từ sổ sự kiện thô — mỗi dòng có mã sự kiện #id thật;
(2) SỔ TAY hiện tại; (3) BÀI HỌC hiện có do các giấc ngủ trước rút (id, trạng thái, α/β, câu).

{viec}

Các lệnh (JSON):
- {{"lenh":"them","cau":"<MỘT câu tiếng Việt có SỐ cụ thể: trong hoàn cảnh nào (khâu/engine/kênh/giờ) thì nên/tránh làm gì, vì số nào>","huong":"nen"|"tranh","pham_vi":["khau/<mã>","engine/<tên>","kenh/<mã>","bo-chon/<khoá>","ma-kiem/<mã>"],"vao_loi_nhac":true|false,"bang_chung":[<mã sự kiện>,...]}}
- {{"lenh":"ung_ho","id":"BH-...","bang_chung":[...]}}   (sự kiện MỚI xác nhận bài cũ)
- {{"lenh":"phan_doi","id":"BH-...","bang_chung":[...]}} (sự kiện bác bài cũ)
- {{"lenh":"sua","id":"BH-...","cau":"<câu mới có số>","bang_chung":[...]}}
- {{"lenh":"nghi","id":"BH-...","ly_do":"...","bang_chung":[...]}}
- {{"lenh":"noi","tu":"BH-...","toi":"<id nơ-ron khác, vd {bp}/loi/<chữ ký>>","bang_chung":[...]}}

LUẬT (máy kiểm từng lệnh, sai là bỏ):
1. Mọi lệnh phải trích ≥ 1 mã sự kiện CÓ THẬT trong bảng số, của chính bộ phận này (số nguyên, không có dấu #). Một
   mã sai là bỏ cả lệnh.
2. Bài mới dựa trên ≥ 2 sự kiện; ưu tiên so CẶP hỏng ⇄ được cùng hoàn cảnh; câu phải có số (tỉ lệ, số lần, phút…).
3. Cùng ý với bài đã có → dùng "ung_ho", không "them".
4. TUYỆT ĐỐI không khuyên hạ chất lượng sản phẩm (bỏ bước kiểm, model yếu hơn, clip từ ảnh, đăng bản kém…) — luật của
   chủ: "thà không đăng còn hơn sản phẩm kém". Lỗi thì hướng tới chờ/thử lại đúng cách, không phải hạ chuẩn.
5. Không quyết chuyện tiền, ví, mở/đóng kênh, nhịp/lịch đăng — ý như vậy chỉ là gợi ý (vao_loi_nhac=false).
6. "vao_loi_nhac": true CHỈ khi câu giúp trực tiếp người VIẾT nội dung của khâu (kịch bản, tiêu đề, bìa, chọn content);
   bài vận hành (chờ máy chủ, thử lại, bộ chọn DOM…) để false.
7. Không bịa số: chỉ dùng số có trong bảng.

Trả về DUY NHẤT một JSON {dang} — không chữ nào khác.

═══ (1) BẢNG SỐ ═══
{to_so}

═══ (2) SỔ TAY HIỆN TẠI ═══
{so_tay}

═══ (3) BÀI HỌC TỰ RÚT HIỆN CÓ ({n}) ═══
{bai}
{duoi}""".format(ten=BO_PHAN.get(bp, bp), bp=bp, viec=viec, dang=dang, to_so=to_so_, duoi=duoi,
                 so_tay=so_tay.strip() or "(chưa có)", n=len(song),
                 bai="\n".join(dong_bai(b) for b in song) or "(chưa có)")


def doc_lenh(chu: str) -> List[Any]:
    """Bóc danh sách lệnh từ câu trả lời (`{"lenh": [...]}` hoặc `[...]`). Không đọc được → ValueError."""
    from ..goi_van_ban import loc_json  # noqa: PLC0415

    d = loc_json(chu)
    ds = d.get("lenh") if isinstance(d, dict) else d
    if not isinstance(ds, list):
        raise ValueError("không thấy danh sách lệnh trong câu trả lời")
    return ds


# ── kiểm lệnh (mã) ───────────────────────────────────────────────────────────

def _ids(x: Any) -> List[int]:
    ra = []
    for v in x if isinstance(x, list) else [x] if x not in (None, "") else []:
        m = re.fullmatch(r"#?\s*(\d+)", str(v).strip())
        if m and int(m.group(1)) not in ra:
            ra.append(int(m.group(1)))
    return ra


def _pham_vi(x: Any) -> List[str]:
    ra = []
    for t in x if isinstance(x, list) else []:
        loai, _, ten = str(t).strip().partition("/")
        ten = " ".join(ten.split())[:60]
        if loai in THUC_THE and ten and loai + "/" + ten not in ra:
            ra.append(loai + "/" + ten)
    return ra[:6]


def kiem_lenh(con: sqlite3.Connection, bp: str, lenh: Sequence[Any], bai: Sequence[Dict[str, Any]]
              ) -> Tuple[List[Dict[str, Any]], List[Tuple[Any, str]]]:
    """(lệnh được áp — đã chuẩn hoá, lệnh bị bỏ + lý do). Xem luật 3–4 ở đầu tệp."""
    co = {b["id"]: b for b in bai}
    moi: List[Dict[str, Any]] = []
    ap: List[Dict[str, Any]] = []
    bo: List[Tuple[Any, str]] = []
    da_tinh: Dict[str, set] = {}
    for i, l in enumerate(lenh):
        if i >= LENH_TOI_DA:
            bo.append((l, "quá {0} lệnh".format(LENH_TOI_DA)))
            continue
        if not isinstance(l, dict) or l.get("lenh") not in LOAI_LENH:
            bo.append((l, "loại lệnh lạ"))
            continue
        loai, ids = l["lenh"], _ids(l.get("bang_chung"))
        if not ids:
            bo.append((l, "thiếu bằng chứng"))
            continue
        that = {r[0] for r in con.execute("SELECT id FROM su_kien WHERE bo_phan = ? AND id IN ({0})".format(
            ",".join("?" * len(ids))), [bp] + ids)}
        sai = [x for x in ids if x not in that]
        if sai:
            bo.append((l, "mã sự kiện không có thật / của bộ phận khác: " + " ".join("#%d" % x for x in sai)))
            continue
        cau = " ".join(str(l.get("cau") or "").split())[:300]
        if loai in ("them", "sua"):
            if not re.search(r"\d", cau):
                bo.append((l, "câu không có số"))
                continue
            if _RE_HA_CHAT.search(cau):
                bo.append((l, "khuyên hạ chất lượng — luật chủ: thà không đăng còn hơn sản phẩm kém"))
                continue
        if loai == "them":
            if len(ids) < 2:
                bo.append((l, "bài mới cần ≥ 2 sự kiện"))
                continue
            trung = max(list(co.values()) + moi, key=lambda b: giong(b["cau"], cau), default=None)
            if trung is not None and giong(trung["cau"], cau) >= GIONG_TRUNG:
                if trung.get("trang_thai") == NGHI:
                    bo.append((l, "trùng bài đã nghỉ " + str(trung["id"])))
                    continue
                if "id" not in trung or trung in moi:
                    bo.append((l, "trùng một bài mới khác trong cùng đêm"))
                    continue
                l, loai = {"lenh": "ung_ho", "id": trung["id"], "bang_chung": ids, "tu_them": cau}, "ung_ho"
            else:
                tien = bool(_RE_TIEN_KENH.search(cau))
                pv = _pham_vi(l.get("pham_vi"))
                # 13/10/2026: bằng chứng chỉ của MỘT kênh mà LLM quên gắn kênh → mã tự gắn `kenh/<mã>` (bài không
                # gắn kênh không vào lời nhắc — `truy_xuat.khoi_loi_nhac`; kênh khác dữ liệu khác, vd cụm trí tuệ).
                kenh_bc = {r[0] for r in con.execute("SELECT DISTINCT kenh FROM su_kien WHERE id IN ({0})".format(
                    ",".join("?" * len(ids))), ids) if r[0]}
                if len(kenh_bc) == 1 and not any(t.startswith("kenh/") for t in pv):
                    pv = pv + ["kenh/" + next(iter(kenh_bc))]
                x = {"lenh": "them", "cau": cau, "huong": "tranh" if l.get("huong") == "tranh" else "nen",
                     "pham_vi": pv, "vao_loi_nhac": bool(l.get("vao_loi_nhac")) and not tien,
                     "chi_goi_y": tien, "bang_chung": ids}
                moi.append(x)
                ap.append(x)
                continue
        if loai == "noi":
            tu, toi = str(l.get("tu") or ""), str(l.get("toi") or "")
            ben = tu if tu in co else toi if toi in co else ""
            kia = toi if ben == tu else tu
            if not ben:
                bo.append((l, "nối phải có một đầu là bài học tự rút của bộ phận"))
                continue
            if not (con.execute("SELECT 1 FROM no_ron WHERE id = ?", (kia,)).fetchone() or kia in co):
                bo.append((l, "nơ-ron đích không có: " + kia))
                continue
            ap.append({"lenh": "noi", "id": ben, "toi": kia if "/" in kia else bp + "/bai-hoc/" + kia,
                       "bang_chung": ids})
            continue
        b = co.get(str(l.get("id") or ""))
        if b is None:
            bo.append((l, "không phải bài học tự rút của bộ phận: " + str(l.get("id"))))
            continue
        if b.get("trang_thai") == NGHI:
            bo.append((l, "bài đã nghỉ: " + str(b["id"])))
            continue
        if loai in ("ung_ho", "phan_doi"):
            cu = da_tinh.setdefault(b["id"], set(b.get("ung_ho") or []) | set(b.get("phan_doi") or []))
            them = [x for x in ids if x not in cu]
            if not them:
                bo.append((l, "bằng chứng đã tính rồi"))
                continue
            cu.update(them)                           # một sự kiện chỉ tính MỘT lần cho một bài, kể cả trong cùng đêm
            ap.append({"lenh": loai, "id": b["id"], "bang_chung": them, "tu_them": l.get("tu_them", "")})
        elif loai == "sua":
            ap.append({"lenh": "sua", "id": b["id"], "cau": cau, "bang_chung": ids,
                       "chi_goi_y": bool(_RE_TIEN_KENH.search(cau))})
        elif loai == "nghi":
            ly = " ".join(str(l.get("ly_do") or "").split())[:200]
            if not ly:
                bo.append((l, "nghỉ cần lý do"))
                continue
            ap.append({"lenh": "nghi", "id": b["id"], "ly_do": ly, "bang_chung": ids})
    return ap, bo


# ── áp lệnh: tệp bài học, trạng thái, trần ───────────────────────────────────

def xep_trang_thai(alpha: float, beta: float, cu: str) -> str:
    """Luật 5 (đầu tệp)."""
    if cu == NGHI:
        return NGHI
    m = alpha / (alpha + beta)
    if m < 0.4:
        return THU_THACH if cu == DANG_DUNG else NGHI
    if alpha >= 4 and m >= 0.75:
        return DANG_DUNG
    if cu == DANG_DUNG and m < 0.6:
        return THU_THACH
    return cu


def _lich_su(than: str) -> List[str]:
    ra, trong = [], False
    for d in than.splitlines():
        if d.startswith("## "):
            trong = d.strip() == "## Lịch sử"
        elif trong and d.startswith("- "):
            ra.append(d[2:])
    return ra


_KHOA_DAU = ("loai", "id", "bo_phan", "nguon", "trang_thai", "alpha", "beta", "n", "huong", "pham_vi", "kenh",
             "vao_loi_nhac", "chi_goi_y", "ung_ho", "phan_doi", "noi", "tao_luc", "cap_nhat", "xac_nhan_cuoi")


def ve_bai_ngu(b: Dict[str, Any], sk: Dict[int, Tuple[float, str, str, str]]) -> str:
    """Tệp nơ-ron bài học tự rút: frontmatter (α/β, phạm vi, mã bằng chứng) + câu + bằng chứng (đọc từ sổ sự kiện) +
    lịch sử + liên kết (sổ tay, nốt thực thể, nơ-ron được nối)."""
    b["n"] = len(b.get("ung_ho") or []) + len(b.get("phan_doi") or [])
    b["kenh"] = [t.partition("/")[2] for t in b.get("pham_vi") or [] if t.startswith("kenh/")]
    than = ["# " + b["cau"], "", "## Bằng chứng"]
    for vai, ids in (("ủng hộ", b.get("ung_ho") or []), ("phản bác", b.get("phan_doi") or [])):
        for i in ids[-12:]:
            luc, kenh, loai, nd = sk.get(i, (0.0, "", "?", "(không còn trong sổ)"))
            than.append("- #{0} `{1}`{2} {3}: {4} ({5})".format(i, ngay_gio(luc), " [{0}]".format(kenh) if kenh else "",
                                                               loai, " ".join(str(nd).split())[:160], vai))
    than += ["", "## Lịch sử"] + ["- " + x for x in b.get("lich_su") or []]
    than += ["", "## Liên kết", "- " + lk(b["bo_phan"] + "/so-tay", "Sổ tay " + BO_PHAN.get(b["bo_phan"], b["bo_phan"]))]
    if b.get("pham_vi"):
        than.append("- " + " · ".join(lk_the(t) for t in b["pham_vi"]))
    if b.get("noi"):
        than.append("- nối: " + " · ".join(lk(t) for t in b["noi"]))
    return ve_ghi_chu({k: b.get(k, "") for k in _KHOA_DAU}, "\n".join(than))


def _su_kien(con: sqlite3.Connection, ids: Iterable[int]) -> Dict[int, Tuple[float, str, str, str]]:
    ids = sorted(set(ids))
    ra: Dict[int, Tuple[float, str, str, str]] = {}
    for i in range(0, len(ids), 500):
        lo = ids[i:i + 500]
        for r in con.execute("SELECT id, luc, kenh, loai, noi_dung FROM su_kien WHERE id IN ({0})".format(
                ",".join("?" * len(lo))), lo):
            ra[r[0]] = (r[1], r[2] or "", r[3], r[4] or "")
    return ra


def ghi_bai(con: sqlite3.Connection, vault: str, b: Dict[str, Any]) -> bool:
    p = b.get("duong") or os.path.join(vault, b["bo_phan"], "bai-hoc", b["id"] + ".md")
    b["duong"] = p
    return ghi_neu_khac(p, ve_bai_ngu(b, _su_kien(con, (b.get("ung_ho") or []) + (b.get("phan_doi") or []))))


def ap_lenh(con: sqlite3.Connection, vault: str, bp: str, ap: Sequence[Dict[str, Any]], bai: List[Dict[str, Any]],
            bay_gio: float) -> List[str]:
    """Áp lệnh đã kiểm vào tệp bài học (+ trần `BAI_HOC_TOI_DA`). Trả dòng nhật ký."""
    luc = ngay_gio(bay_gio)
    co = {b["id"]: b for b in bai}
    for b in bai:
        b.setdefault("lich_su", _lich_su(b.get("than") or ""))
    doi, dong = set(), []
    for l in ap:
        loai, ids = l["lenh"], l["bang_chung"]
        if loai == "them":
            l["id"] = "BH-N" + bam("{0}|{1}|{2}".format(bp, l["cau"], bay_gio), 7)
            b = {"loai": "bai-hoc", "id": l["id"], "bo_phan": bp,
                 "nguon": NGUON_NGU, "trang_thai": UNG_VIEN, "alpha": 1 + min(3, len(ids)), "beta": 1,
                 "huong": l["huong"], "pham_vi": l["pham_vi"], "vao_loi_nhac": l["vao_loi_nhac"],
                 "chi_goi_y": l["chi_goi_y"], "ung_ho": list(ids), "phan_doi": [], "noi": [], "tao_luc": luc,
                 "cap_nhat": luc, "xac_nhan_cuoi": luc, "cau": l["cau"],
                 "lich_su": ["{0} thêm (giấc ngủ) — {1} bằng chứng".format(luc, len(ids))]}
            co[b["id"]] = b
            bai.append(b)
            dong.append("- thêm {0} ({1} bằng chứng{2})".format(lk(bp + "/bai-hoc/" + b["id"], b["cau"]), len(ids),
                                                              ", chỉ gợi ý" if b["chi_goi_y"] else ""))
        else:
            b = co[l["id"]]
            cu = b.get("trang_thai")
            if loai in ("ung_ho", "phan_doi"):
                b[loai] = list(b.get(loai) or []) + list(ids)
                k = "alpha" if loai == "ung_ho" else "beta"
                b[k] = float(b.get(k) or 1) + min(3, len(ids))
                if loai == "ung_ho":
                    b["xac_nhan_cuoi"] = luc
                b["trang_thai"] = xep_trang_thai(float(b.get("alpha") or 1), float(b.get("beta") or 1), cu)
                ghi_chu = "{0} {1} +{2} bằng chứng{3}".format(luc, "ủng hộ" if loai == "ung_ho" else "phản đối",
                                                              len(ids), " (từ một bài mới trùng ý)" if l.get("tu_them")
                                                              else "")
            elif loai == "sua":
                b["cau"] = l["cau"]
                b["ung_ho"] = list(b.get("ung_ho") or []) + [x for x in ids if x not in (b.get("ung_ho") or [])]
                if l.get("chi_goi_y"):                  # câu mới nói chuyện tiền / kênh → chỉ gợi ý
                    b["chi_goi_y"], b["vao_loi_nhac"] = True, False
                ghi_chu = "{0} sửa câu".format(luc)
            elif loai == "nghi":
                b["trang_thai"] = NGHI
                ghi_chu = "{0} nghỉ — {1}".format(luc, l["ly_do"])
            else:
                b["noi"] = list(b.get("noi") or []) + ([l["toi"]] if l["toi"] not in (b.get("noi") or []) else [])
                ghi_chu = "{0} nối → {1}".format(luc, l["toi"])
            if b.get("trang_thai") != cu:
                ghi_chu += " · {0} → {1}".format(TEN_TRANG_THAI.get(cu, cu), TEN_TRANG_THAI.get(b["trang_thai"]))
            b["cap_nhat"] = luc
            b.setdefault("lich_su", []).append(ghi_chu)
            dong.append("- {0} {1}: {2}".format(loai, lk(bp + "/bai-hoc/" + b["id"], b["cau"]), ghi_chu[len(luc) + 1:]))
        doi.add(b["id"])
    song = sorted((b for b in bai if b.get("trang_thai") != NGHI), key=lambda b: (no_ron._tb(b), str(b.get("cap_nhat"))))
    for b in song[:max(0, len(song) - BAI_HOC_TOI_DA)]:
        b["trang_thai"], b["cap_nhat"] = NGHI, luc
        b.setdefault("lich_su", []).append("{0} nghỉ — vượt trần {1} bài, bài yếu nhất".format(luc, BAI_HOC_TOI_DA))
        dong.append("- nghỉ (vượt trần {0}) {1}".format(BAI_HOC_TOI_DA, lk(bp + "/bai-hoc/" + b["id"], b["cau"])))
        doi.add(b["id"])
    for b in bai:
        if b["id"] in doi:
            ghi_bai(con, vault, b)
    return dong


# ── một bộ phận ngủ ──────────────────────────────────────────────────────────

def _token(ra: str, viec: str, t0: float) -> Tuple[int, int]:
    """Token của lượt gọi Max vừa xong — đọc đuôi sổ dùng thuê bao `workspace/viet-max/so-dung.jsonl`."""
    try:
        with open(os.path.join(ra, "workspace", "viet-max", "so-dung.jsonl"), "rb") as tep:
            tep.seek(max(0, os.path.getsize(tep.name) - 65536))
            dong = tep.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return 0, 0
    vao = ra_ = 0
    for d in map(jdong, dong):
        if d.get("viec") == viec and (luc_tu(d.get("luc")) or 0) >= t0 - 2:
            vao += int(d.get("token_vao") or 0)
            ra_ += int(d.get("token_ra") or 0)
    return vao, ra_


def goi_max(ra: str, loi_nhac: str, bp: str) -> str:
    """MỘT lượt Claude Max (thang opus-5-5 → …, thuê bao của máy; `dung_goi_chat_max` không có đường về ví)."""
    from .. import viet_max  # noqa: PLC0415

    return viet_max.dung_goi_chat_max(ra, viec="nao-bo-phan-ngu:" + bp)(loi_nhac, toi_da_token=4000)


def ve_phan_hoi(lenh: Sequence[Any], bo: Sequence[Tuple[Any, str]], tu_id: int) -> str:
    """Đoạn nối vào lời nhắc cho lượt sửa (đường ví): lượt trước đề xuất gì, máy bỏ vì sao."""
    ly = Counter(str(l) for _x, l in bo)
    return ("\n═══ LƯỢT TRƯỚC: {0} lệnh đề xuất, KHÔNG lệnh nào qua kiểm ═══\n{1}\nĐọc lại BẢNG SỐ và đề xuất lại theo đúng "
            "luật: ung_ho/phan_doi chỉ với mã > {2}; nhận xét nào có mã mới mà chưa có bài thì \"them\" (≥ 2 mã có "
            "trong bảng, câu có số).\n").format(
        len(lenh), "\n".join("- bỏ {0} lệnh: {1}".format(n, x) for x, n in ly.most_common(6)) or
        "- bạn trả danh sách lệnh rỗng", int(tu_id or 0))


def ngu_mot(con: sqlite3.Connection, ra: str, bp: str, moi: int, tu_id: int, den_id: int, goi: Goi, bay_gio: float,
            phan_tich: bool = False, so_dung: Optional[Dict[str, Dict[str, int]]] = None) -> Dict[str, Any]:
    """Một bộ phận ngủ. `phan_tich` (đường ví): lời nhắc phân tích trước + `VONG_SUA_VI` lượt sửa khi không lệnh nào
    qua kiểm. `so_dung[bp]` (đường ví): token thật `goi` cộng vào — không có thì đọc sổ thuê bao Max (`_token`)."""
    vault = duong_vault(ra)
    t0 = time.time()
    so = to_so(con, bp, bay_gio, moi, bo_kenh=kenh_tra_kho_ds(ra))
    bai = no_ron.doc_bai_ngu(vault, bp)
    loi_nhac = ve_loi_nhac(bp, so, doc_chu(os.path.join(vault, bp, "so-tay.md")) or "", bai, phan_tich=phan_tich,
                           tu_id=tu_id)
    lenh = doc_lenh(goi(loi_nhac, bp))
    ap, bo = kiem_lenh(con, bp, lenh, bai)
    vong = 0
    loi_vong: List[str] = []
    while phan_tich and not ap and vong < VONG_SUA_VI:
        vong += 1
        try:
            lenh2 = doc_lenh(goi(loi_nhac + ve_phan_hoi(lenh, bo, tu_id), bp))
        except Exception as loi:  # noqa: BLE001 — lượt sửa hỏng: giữ kết quả lượt đầu (đã ghi đủ lý do bỏ)
            loi_vong.append("{0}: {1}".format(type(loi).__name__, str(loi)[:160]))
            break
        ap, bo2 = kiem_lenh(con, bp, lenh2, bai)
        lenh, bo = list(lenh) + list(lenh2), list(bo) + list(bo2)
    dong = ap_lenh(con, vault, bp, ap, bai, bay_gio)
    sd = (so_dung or {}).get(bp) or {}
    if sd:
        tv, tr = int(sd.get("token_vao") or 0), int(sd.get("token_ra") or 0)
    else:
        tv, tr = _token(ra, "nao-bo-phan-ngu:" + bp, t0)
    giay = round(time.time() - t0, 1)
    chi_tiet = {"ap": ap, "bo": [{"lenh": l, "ly_do": ly} for l, ly in bo], "ky_tu_to_so": len(so),
                "duong": "vi" if phan_tich else "max", "vong_sua": vong, "luot_goi": int(sd.get("luot") or 0)}
    if loi_vong:
        chi_tiet["loi_vong_sua"] = loi_vong
    con.execute("INSERT INTO giac_ngu(luc, bo_phan, tu_id, den_id, de_xuat, ap, bo, giay, ky_tu, token_vao, token_ra, "
                "chi_tiet, loi) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, '')",
                (bay_gio, bp, tu_id, den_id, len(lenh), len(ap), len(bo), giay, len(loi_nhac), tv, tr,
                 json.dumps(chi_tiet, ensure_ascii=False, default=str)))
    con.commit()
    ghi_nhat_ky(vault, bp, "{0} — ngủ ({1} sự kiện mới · {2} lệnh: áp {3}, bỏ {4} · {5} giây{6})".format(
        ngay_gio(bay_gio), moi, len(lenh), len(ap), len(bo), giay, " · {0} token vào".format(tv) if tv else ""),
        dong + ["- bỏ {0}: {1}".format(l.get("lenh") if isinstance(l, dict) else "?", ly) for l, ly in bo]
        or ["- không lệnh nào (bảng số chưa đủ chắc cho bài mới)"])
    cham = {x.get("id") for x in ap}
    return {"bo_phan": bp, "su_kien_moi": moi, "ky_tu_to_so": len(so), "ky_tu_loi_nhac": len(loi_nhac),
            "de_xuat": len(lenh), "ap": ap, "bo": bo, "giay": giay, "token_vao": tv, "token_ra": tr,
            "bai": [{k: b.get(k) for k in ("id", "cau", "trang_thai", "alpha", "beta", "n", "vao_loi_nhac")}
                    for b in bai if b["id"] in cham]}


# ── soát tuần (chỉ mã) ───────────────────────────────────────────────────────

def soat(con: sqlite3.Connection, vault: str, bay_gio: float) -> Dict[str, Dict[str, int]]:
    """Luật 8 (đầu tệp). Trả {bộ phận: {cu, khong_bang_chung, mau_thuan, mo_coi}} (chỉ bộ phận có gì để báo)."""
    luc, kq = ngay_gio(bay_gio), {}
    for bp in BO_PHAN:
        bai = no_ron.doc_bai_ngu(vault, bp)
        dem, dong, doi = Counter(), [], set()

        def chuyen(b: Dict[str, Any], tt: str, vi_sao: str) -> None:
            if b.get("trang_thai") == tt:
                return
            b.setdefault("lich_su", _lich_su(b.get("than") or "")).append("{0} soát: {1} → {2} — {3}".format(
                luc, TEN_TRANG_THAI.get(b.get("trang_thai")), TEN_TRANG_THAI.get(tt), vi_sao))
            b["trang_thai"], b["cap_nhat"] = tt, luc
            dong.append("- {0}: → {1} — {2}".format(lk(bp + "/bai-hoc/" + b["id"], b["cau"]), TEN_TRANG_THAI.get(tt),
                                                    vi_sao))
            doi.add(b["id"])

        song = [b for b in bai if b.get("trang_thai") != NGHI]
        ids = sorted({i for b in song for i in (b.get("ung_ho") or []) + (b.get("phan_doi") or [])})
        that = {r[0] for r in con.execute("SELECT id FROM su_kien WHERE bo_phan = ? AND id IN ({0})".format(
            ",".join("?" * len(ids))), [bp] + ids)} if ids else set()
        for b in song:
            if not set((b.get("ung_ho") or []) + (b.get("phan_doi") or [])) & that:
                chuyen(b, NGHI, "không còn bằng chứng có thật")
                dem["khong_bang_chung"] += 1
            elif b.get("trang_thai") == DANG_DUNG and bay_gio - (luc_tu(b.get("xac_nhan_cuoi")) or 0) >= NGAY_CU * NGAY:
                chuyen(b, THU_THACH, "≥ {0} ngày không ai xác nhận".format(NGAY_CU))
                dem["cu"] += 1
        song = [b for b in song if b.get("trang_thai") != NGHI]
        for i, a in enumerate(song):
            for b in song[i + 1:]:
                if (a.get("pham_vi") and set(a["pham_vi"]) == set(b.get("pham_vi") or []) and
                        a.get("huong") != b.get("huong") and giong(a["cau"], b["cau"]) >= GIONG_MAU_THUAN):
                    for x, y in ((a, b), (b, a)):
                        chuyen(x, THU_THACH, "mâu thuẫn với " + y["id"])
                    dem["mau_thuan"] += 1
        nghi = {bp + "/bai-hoc/" + b["id"] for b in bai if b.get("trang_thai") == NGHI}
        mo_coi = [r[0] for r in con.execute(
            "SELECT id FROM no_ron WHERE bo_phan = ? AND trang_thai != ? AND id NOT IN (SELECT tu FROM lien_ket WHERE "
            "toi LIKE 'thuc-the/%') ORDER BY id", (bp, NGHI)) if r[0] not in nghi]
        if mo_coi:
            dem["mo_coi"] = len(mo_coi)
            dong.append("- mồ côi (không nối nốt thực thể nào): {0} — {1}".format(
                len(mo_coi), " · ".join(lk(x) for x in mo_coi[:5])))
        for b in bai:
            if b["id"] in doi:
                ghi_bai(con, vault, b)
        ghi_nhat_ky(vault, bp, luc + " — soát tuần", dong)
        if dem:
            kq[bp] = dict(dem)
    kho.dat_meta(con, "soat_cuoi", time.strftime("%Y-%m-%d", time.localtime(bay_gio)))
    con.commit()
    return kq


# ── cả đêm ───────────────────────────────────────────────────────────────────

def ngu(goc: str = GOC, ra: str = "", bay_gio: Optional[float] = None, goi: Optional[Goi] = None,
        chi: Sequence[str] = (), toi_da: int = BO_PHAN_TOI_DA_DEM, soat_tuan: Optional[bool] = None,
        phan_tich: Optional[bool] = None, bao: bool = True) -> Dict[str, Any]:
    """Giấc ngủ đêm (đọc mốc / ghi ở `ra`, mặc định `goc`). `goi(lời nhắc, bộ phận) -> chữ` thay được trong bài kiểm;
    mặc định = ví (`viet_chu_bang: "vi"`, lời nhắc phân tích trước + lượt sửa) hoặc `goi_max` (thuê bao). Không bao giờ
    ném lỗi ra khỏi một bộ phận; xong thì dựng lại sổ tay + chỉ mục, rồi tự soát sức khoẻ (`suc_khoe`) — hỏng thì
    `kq["canh_bao"]` + báo động chống lặp (`bao=False` để tắt trong bài kiểm)."""
    t0 = time.time()
    bay_gio = bay_gio or time.time()
    ra = ra or goc
    kq: Dict[str, Any] = {"bo_phan": [], "soat": {}, "bo_qua": ""}
    so_dung: Dict[str, Dict[str, int]] = {}
    con = kho.mo(ra, cho=5.0)
    try:
        ds = can_ngu(con, chi, toi_da)
        if ds and goi is None:
            from .. import viet_max  # noqa: PLC0415

            # 17/10/2026 — chủ dự án: "Claude Max sắp hết token, all mọi thứ dùng ShopAPI". Cài đặt chọn ví
            # (`viet_chu_bang: "vi"`) thì giấc ngủ cũng đi ví (cùng mô hình mạnh nhất ví có).
            from .. import cai_dat  # noqa: PLC0415

            if str(cai_dat.doc(goc).get("viet_chu_bang") or "").strip().lower() == "vi":  # chủ CHỌN ví (không phải "tự động thiếu CLI")
                from ..giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415

                g = goi_chat_that(goc)
                if g is None:
                    kq["bo_qua"] = "van ví đang chặn gọi AI — giấc ngủ đợi lượt sau"
                    ds = []
                else:
                    phan_tich, goi = True, _goi_vi(g, so_dung)
            elif viet_max.co_claude_code():
                goi = lambda loi_nhac, bp: goi_max(ra, loi_nhac, bp)  # noqa: E731
            else:
                kq["bo_qua"] = "máy không có Claude Code — giấc ngủ chỉ chạy bằng thuê bao Claude Max, KHÔNG đi ví"
                ds = []
        for bp, moi, tu, den in ds:
            try:
                kq["bo_phan"].append(ngu_mot(con, ra, bp, moi, tu, den, goi, bay_gio, phan_tich=bool(phan_tich),
                                             so_dung=so_dung))
            except Exception as loi:  # noqa: BLE001 — một bộ phận hỏng không chặn bộ phận khác; mốc không dời
                try:
                    con.rollback()
                    con.execute("INSERT INTO giac_ngu(luc, bo_phan, tu_id, den_id, giay, loi) VALUES (?,?,?,?,?,?)",
                                (bay_gio, bp, tu, den, round(time.time() - t0, 1),
                                 "{0}: {1}".format(type(loi).__name__, str(loi)[:300])))
                    con.commit()
                except sqlite3.Error:
                    pass
                kq["bo_phan"].append({"bo_phan": bp, "su_kien_moi": moi, "loi": "{0}: {1}".format(
                    type(loi).__name__, str(loi)[:300])})
        if soat_tuan is None:
            soat_tuan = (time.localtime(bay_gio).tm_wday == 6 and
                         kho.doc_meta(con, "soat_cuoi") != time.strftime("%Y-%m-%d", time.localtime(bay_gio)))
        if soat_tuan:
            kq["soat"] = soat(con, duong_vault(ra), bay_gio)
        if ds or soat_tuan:
            kq["vault"] = {k: v for k, v in no_ron.dung_vault(con, goc, ra, bay_gio).items() if k != "no_ron"}
        if ds:
            kq["canh_bao"] = suc_khoe(con)
    finally:
        con.close()
    if kq.get("canh_bao") and bao:
        bao_ngu_rong(goc, kq["canh_bao"], bay_gio)
    kq["giay"] = round(time.time() - t0, 1)
    return kq


# ── sức khoẻ giấc ngủ: không chết im lặng ────────────────────────────────────

#: Bấy nhiêu ĐÊM ngủ liền (đêm có ít nhất một bộ phận ngủ) mà không áp được lệnh nào = hỏng (18–20/10/2026: 15 giấc ngủ
#: ra 1 lệnh, bảng ghi token 0, không lỗi, không ai biết).
DEM_RONG_TOI_DA = 3
LOAI_BAO_DONG = "nao_ngu_rong"


def _goi_vi(g: Callable[..., str], so_dung: Dict[str, Dict[str, int]]) -> Goi:
    """Gọi ví cho giấc ngủ: khoá chống trùng THEO LỜI NHẮC (gọi lại đúng lời nhắc → nhận lại đúng câu trả lời; đêm sau
    lời nhắc khác → khoá khác — khoá cố định `nao-bo-phan-ngu:<bộ phận>` cũ đụng "khoá đã dùng" từ đêm thứ hai và hết
    4 lượt đổi khoá ở đêm thứ năm); token thật cộng vào `so_dung[bộ phận]`."""
    import hashlib  # noqa: PLC0415

    def goi(loi_nhac: str, bp: str) -> str:
        bam_ = hashlib.sha1(loi_nhac.encode("utf-8", "replace")).hexdigest()[:16]
        return g(loi_nhac, mo_hinh=MO_HINH_VI, toi_da_token=4000, khoa="nao-bo-phan-ngu:{0}:{1}".format(bp, bam_),
                 so_dung=so_dung.setdefault(bp, {}))
    return goi


#: Tên mô hình gửi ví (máy chủ ShopAPI tự định tuyến tên này sang mô hình thật — xem `VIEC_PHAN_TICH`).
MO_HINH_VI = "claude-opus-5"


def dem_ngu(con: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Mỗi ĐÊM ngủ một dòng (theo ngày giờ máy của `luc`), cũ → mới: {ngay, giac, loi, ap, de_xuat, token}."""
    ra: Dict[str, Dict[str, Any]] = {}
    for luc, ap, dx, tv, tr, loi in con.execute(
            "SELECT luc, ap, de_xuat, token_vao, token_ra, loi FROM giac_ngu ORDER BY luc, id"):
        ngay = time.strftime("%Y-%m-%d", time.localtime(float(luc or 0)))
        d = ra.setdefault(ngay, {"ngay": ngay, "giac": 0, "loi": 0, "ap": 0, "de_xuat": 0, "token": 0})
        if loi:
            d["loi"] += 1
            continue
        d["giac"] += 1
        d["ap"] += int(ap or 0)
        d["de_xuat"] += int(dx or 0)
        d["token"] += int(tv or 0) + int(tr or 0)
    return [ra[k] for k in sorted(ra)]


def suc_khoe(con: sqlite3.Connection, so_dem: int = DEM_RONG_TOI_DA) -> str:
    """'' nếu giấc ngủ khoẻ; câu người đọc được nếu HỎNG: `so_dem` đêm ngủ liền không áp lệnh nào, hoặc đêm gần nhất
    có giấc ngủ không lỗi mà token ghi 0 (gọi AI không thật / không đo được)."""
    try:
        dem = dem_ngu(con)
    except sqlite3.Error:
        return ""
    if not dem:
        return ""
    cuoi = dem[-so_dem:]
    if len(cuoi) >= so_dem and all(d["ap"] == 0 for d in cuoi):
        return ("Não bộ phận ngủ {0} đêm liền ({1} → {2}) mà không rút được bài học nào: {3} giấc ngủ, {4} lệnh đề xuất, "
                "0 lệnh áp{5}.").format(so_dem, cuoi[0]["ngay"], cuoi[-1]["ngay"], sum(d["giac"] for d in cuoi),
                                       sum(d["de_xuat"] for d in cuoi),
                                       ", {0} giấc hỏng".format(sum(d["loi"] for d in cuoi))
                                       if any(d["loi"] for d in cuoi) else "")
    d = dem[-1]
    if d["giac"] and not d["token"]:
        return ("Não bộ phận ngủ đêm {0} ({1} giấc) nhưng bảng ghi 0 token — lượt gọi AI không thật hoặc không đo "
                "được.").format(d["ngay"], d["giac"])
    return ""


def suc_khoe_tep(goc: str) -> str:
    """`suc_khoe` đọc CHỈ ĐỌC `nao/bo-phan.db` (cho bảng "Việc của bạn" / tự kiểm). Không có kho / lỗi → ''."""
    import urllib.request  # noqa: PLC0415

    p = os.path.join(goc, "nao", "bo-phan.db")
    if not os.path.isfile(p):
        return ""
    try:
        con = sqlite3.connect("file:{0}?mode=ro".format(urllib.request.pathname2url(p)), uri=True, timeout=1)
    except sqlite3.Error:
        return ""
    try:
        return suc_khoe(con)
    finally:
        con.close()


def bao_ngu_rong(goc: str, cau: str, bay_gio: Optional[float] = None) -> bool:
    """Báo động (chống lặp theo loại — đường `core.bao_dong` chung). Không ném lỗi."""
    try:
        from .. import bao_dong  # noqa: PLC0415

        return bool(bao_dong.bao_dong(
            LOAI_BAO_DONG, cau, "Máy tự thử lại mỗi đêm 03:40. Xem bảng giac_ngu trong nao/bo-phan.db và nhật ký "
            "nao/bo-phan/<bộ phận>/nhat-ky.md; chạy tay: python -X utf8 -m core.nao_bo_phan ngu --bo-phan <mã>.",
            goc=goc, bay_gio=bay_gio))
    except Exception:  # noqa: BLE001
        return False
