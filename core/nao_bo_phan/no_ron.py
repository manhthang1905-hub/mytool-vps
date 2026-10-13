"""NƠ-RON, SỔ TAY, BẢN ĐỒ, CHỈ MỤC — dựng lại bằng mã mỗi lần gom (không LLM).

* Nơ-ron LỖI `<bộ phận>/loi/<chữ ký>.md`: gộp mọi sự kiện `loi` cùng chữ ký từ sổ sự kiện (sự kiện `sua` cùng chữ
  ký = "cách sửa đã thử"; ≥ 7 ngày sau không tái phát = ĐÃ KIỂM). Do máy dựng — sửa tay sẽ bị ghi đè; chữ ký không
  còn sự kiện nào (đổi cách chuẩn hoá) thì tệp bị xoá.
* Nơ-ron BÀI HỌC `<bộ phận>/bai-hoc/BH-<băm>.md`: BẢN CHIẾU chỉ đọc của sổ bài học có sẵn (giám đốc kênh + sổ sản
  xuất) — bài biến khỏi nguồn thì chuyển `nghi`, không xoá.
* Sổ tay `<bộ phận>/so-tay.md`, bản đồ `_ban-do.md`, nốt kênh `thuc-the/kenh/<K>.md`.
* Chỉ mục (`no_ron`, FTS5 hai bộ tách từ, `lien_ket`) dựng lại TOÀN BỘ từ vault (`dung_lai_chi_muc`).
"""

from __future__ import annotations

import glob
import io
import json
import os
import re
import sqlite3
import time
from collections import Counter, deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import kho
from ._chung import (BO_PHAN, CANH_BAO, DA_HET, DANG, DANG_DUNG, GIO_DANG_XAY_RA, LOI, N_BAI_HOC_SO_TAY,
                     NGAY_DA_HET, NGAY_HET_GAN_DAY, NGHI, NGUON_NGU, SO_TAY_TOI_DA_DONG, TAI_PHAT, TAM_LANG,
                     TEN_TRANG_THAI, THU_THACH, THUC_THE, TRUC_BO_PHAN, UNG_VIEN, bam, cac_kenh, chuan_hoa, doc_chu,
                     doc_ghi_chu, doc_json, duong_vault, ghi_nhat_ky, ghi_neu_khac, jdong as _jdong, la_canh_bao, lk,
                     lk_kenh, lk_the, luc_tu, ngay_gio, ten_tep, thuc_the, ve_ghi_chu)

NGAY = 86400.0


def su_co(kenh: str, ma_goi: str, luc: float) -> Tuple[str, str]:
    """Một SỰ CỐ = cặp (kênh, gói) — lỗi không gắn gói thì (kênh, ngày): mười dòng log của cùng một lượt hỏng là một
    sự cố, không phải mười."""
    return (kenh, ma_goi or time.strftime("%Y-%m-%d", time.localtime(luc)))


def ti_le_tang(so_48: int, so_5: int) -> float:
    """Nhịp sự cố 48h qua so với 5 ngày trước đó (mỗi bên +1 cho đỡ chia 0): (n48+1)/2 : (n5+1)/5."""
    return round(((so_48 + 1) / 2.0) / ((so_5 + 1) / 5.0), 2)


# ── nơ-ron lỗi ───────────────────────────────────────────────────────────────

def trang_thai_loi(lan_cuoi: float, tro_lai: Optional[float], bay_gio: float) -> str:
    """Gặp trong 48h → đang xảy ra (tái phát nếu lần QUAY LẠI sau quãng im ≥ 7 ngày nằm trong 7 ngày qua);
    im ≥ 7 ngày → đã hết; ở giữa → tạm lặng."""
    if lan_cuoi >= bay_gio - GIO_DANG_XAY_RA * 3600:
        return TAI_PHAT if tro_lai and tro_lai >= bay_gio - NGAY_DA_HET * NGAY else DANG
    return DA_HET if lan_cuoi <= bay_gio - NGAY_DA_HET * NGAY else TAM_LANG


def gom_no_ron_loi(con: sqlite3.Connection, kenh_ds: Sequence[str], bay_gio: float
                   ) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Một lượt quét sổ sự kiện theo thời gian → `{(bộ phận, chữ ký): nơ-ron}` (bộ nhớ O(số nơ-ron))."""
    nr: Dict[Tuple[str, str], Dict[str, Any]] = {}
    moc48, moc7 = bay_gio - GIO_DANG_XAY_RA * 3600, bay_gio - 7 * NGAY
    for bp, ck, luc, loai, kenh, nd, nguon, so_, goi in con.execute(
            "SELECT bo_phan, chu_ky, luc, loai, kenh, noi_dung, nguon, so, ma_goi FROM su_kien "
            "WHERE chu_ky != '' AND loai IN ('loi', 'sua') ORDER BY luc, id"):
        n = nr.get((bp, ck))
        if loai == "sua":
            if n is not None:
                n["sua"].append((luc, nd))
            continue
        try:
            so = json.loads(so_ or "{}")
        except ValueError:
            so = {}
        if n is None:
            n = nr[(bp, ck)] = {"bo_phan": bp, "chu_ky": ck, "so_lan": 0, "so_7": 0, "so_48": 0, "lan_dau": luc,
                                "lan_cuoi": luc, "tro_lai": None, "ngay": Counter(), "kenh": Counter(),
                                "nguon": set(), "vi_du": deque(maxlen=3), "cau": Counter(), "sua": deque(maxlen=5),
                                "canh_bao": True, "su_co_48": set(), "su_co_5": set(), "the": Counter()}
        elif luc - n["lan_cuoi"] >= NGAY_DA_HET * NGAY:
            n["tro_lai"] = luc
        n["so_lan"] += 1
        n["lan_cuoi"] = luc
        if luc >= moc7:
            n["so_7"] += 1
            n["ngay"][time.strftime("%m-%d", time.localtime(luc))] += 1
            n["su_co_48" if luc >= moc48 else "su_co_5"].add(su_co(kenh, goi, luc))
        if luc >= moc48:
            n["so_48"] += 1
        if kenh:
            n["kenh"][kenh] += 1
        if nguon:
            n["nguon"].add(nguon)
        n["canh_bao"] = n["canh_bao"] and la_canh_bao(nguon, so)
        for loai_t, ten in thuc_the(nguon, nd, so):
            n["the"][loai_t + "/" + ten] += 1
        n["vi_du"].append((luc, kenh, nd))
        n["cau"][chuan_hoa(nd, kenh_ds)] += 1
    for n in nr.values():
        n["trang_thai"] = trang_thai_loi(n["lan_cuoi"], n["tro_lai"], bay_gio)
        n["cau_chinh"] = n["cau"].most_common(1)[0][0] if n["cau"] else n["chu_ky"]
        n["id"] = "{0}/loi/{1}".format(n["bo_phan"], n["chu_ky"])
        n["muc"] = CANH_BAO if n["canh_bao"] else LOI
        n["n48"], n["n5"] = len(n["su_co_48"]), len(n["su_co_5"])
        n["ti_le_tang"] = ti_le_tang(n["n48"], n["n5"])
    return nr


def _kiem_sua(n: Dict[str, Any], luc: float, bay_gio: float) -> str:
    if n["lan_cuoi"] > luc:
        return "lỗi còn gặp sau lần sửa"
    if luc <= bay_gio - NGAY_DA_HET * NGAY:
        return "ĐÃ KIỂM — {0:.0f} ngày không tái phát".format((bay_gio - luc) / NGAY)
    return "chưa đủ {0} ngày để kiểm".format(NGAY_DA_HET)


def sua_da_kiem(n: Dict[str, Any], bay_gio: float) -> bool:
    return any(_kiem_sua(n, l, bay_gio).startswith("ĐÃ KIỂM") for l, _ in n["sua"])


def ve_loi(n: Dict[str, Any], bay_gio: float) -> str:
    bp, kenh = n["bo_phan"], [k for k, _ in n["kenh"].most_common()]
    the = sorted(n.get("the") or {})
    vi_du = " ".join(str(n["vi_du"][-1][2]).split())[:200] if n["vi_du"] else ""
    dau = {"loai": "loi", "chu_ky": n["chu_ky"], "bo_phan": bp, "trang_thai": n["trang_thai"],
           "muc": n.get("muc", LOI), "so_lan": n["so_lan"], "so_lan_7_ngay": n["so_7"], "so_lan_48h": n["so_48"],
           "su_co_48h": n.get("n48", 0), "su_co_5_ngay_truoc": n.get("n5", 0), "ti_le_tang": n.get("ti_le_tang", 0.0),
           "lan_dau": ngay_gio(n["lan_dau"]), "lan_cuoi": ngay_gio(n["lan_cuoi"]), "kenh": kenh,
           "nguon": sorted(n["nguon"]), "thuc_the": the, "vi_du": vi_du}
    ngay7 = [time.strftime("%m-%d", time.localtime(bay_gio - i * NGAY)) for i in range(6, -1, -1)]
    than = ["# " + n["cau_chinh"], "", "## Quan sát",
            "- {0}{1} — tổng {2} lần, lần đầu {3}, lần cuối {4}{5}.".format(
                TEN_TRANG_THAI[n["trang_thai"]], " (CẢNH BÁO — dự phòng đã cứu / không chặn)"
                if n.get("muc") == CANH_BAO else "", n["so_lan"], ngay_gio(n["lan_dau"]), ngay_gio(n["lan_cuoi"]),
                ", quay lại sau quãng im ≥ {0} ngày lúc {1}".format(NGAY_DA_HET, ngay_gio(n["tro_lai"]))
                if n["tro_lai"] else ""),
            "- 7 ngày: " + " · ".join("{0}: {1}".format(d, n["ngay"].get(d, 0)) for d in ngay7),
            "- Sự cố khác nhau (kênh × gói/ngày): 48h qua {0} · 5 ngày trước đó {1} · nhịp ×{2}".format(
                n.get("n48", 0), n.get("n5", 0), n.get("ti_le_tang", 0.0))]
    if kenh:
        than.append("- Kênh: " + " · ".join("{0} ×{1}".format(k, c) for k, c in n["kenh"].most_common()))
    than.append("- Nguồn: " + ", ".join(sorted(n["nguon"])))
    than.append("- Ví dụ gần nhất:")
    than += ["  - `{0}`{1} {2}".format(ngay_gio(l), " [{0}]".format(k) if k else "", " ".join(str(nd).split())[:240])
             for l, k, nd in reversed(n["vi_du"])]
    if n["sua"]:
        than += ["", "## Cách sửa đã thử"]
        than += ["- `{0}` {1} — {2}".format(ngay_gio(l), " ".join(str(nd).split())[:200], _kiem_sua(n, l, bay_gio))
                 for l, nd in reversed(n["sua"])]
    than += ["", "## Liên kết", "- " + lk(bp + "/so-tay", "Sổ tay " + BO_PHAN.get(bp, bp))]
    if kenh:
        than.append("- " + " · ".join(lk_kenh(k) for k in kenh))
    if the:
        than.append("- " + " · ".join(lk_the(t) for t in the))
    return ve_ghi_chu(dau, "\n".join(than))


# ── nơ-ron bài học (bản chiếu) ────────────────────────────────────────────────

def bai_hoc_giam_doc(goc: str, kenh: str, bay_gio: float) -> List[Dict[str, Any]]:
    """`CHANNEL/<k>/giam-doc/bai-hoc.jsonl` gộp theo khoá (trục, giá trị, cụm) đúng luật của
    `giam_doc.kham_nghiem.doc_bai_hoc`: mỗi video MỘT phiếu (phiếu đầu thắng), cộng = video cùng hướng bài gốc,
    trừ = video ngược hướng; α = 1 + cộng, β = 1 + trừ; trạng thái: "that" → đang dùng, "bo" (kể cả chủ gạch) →
    nghỉ, có phiếu trừ → thử thách, còn lại → ứng viên."""
    p = os.path.join(goc, "CHANNEL", kenh, "giam-doc", "bai-hoc.jsonl")
    if not os.path.isfile(p):
        return []
    from ..giam_doc import kham_nghiem as kn  # noqa: PLC0415

    tu = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(bay_gio - kn.NGAY_BAI_HOC * NGAY))
    nhom: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    with io.open(p, encoding="utf-8", errors="replace") as tep:
        for dong in tep:
            d = _jdong(dong)
            if (d.get("truc") in kn.TRUC_DOC and d.get("video_id") and str(d.get("luc") or "") >= tu
                    and re.search(r"\d", str(d.get("cau") or ""))):
                nhom.setdefault((d["truc"], str(d.get("gia_tri") or ""), str(d.get("cum") or "")), []).append(d)
    gach = set()        # nút "Sai" của chủ (`bang_dieu_khien.TEP_BAI_HOC_GACH`) — đọc thẳng, khỏi nạp cả bảng
    p_gach = os.path.join(os.path.dirname(p), "bai-hoc-gach.jsonl")
    if os.path.isfile(p_gach):
        with io.open(p_gach, encoding="utf-8", errors="replace") as tep:
            gach = {str(_jdong(d).get("ma_bai")) for d in tep} - {"None"}
    ra = []
    for (truc, gt, cum), ds in nhom.items():
        ds.sort(key=lambda x: str(x.get("luc")))
        huong = ds[0].get("huong") if ds[0].get("huong") in ("+", "-") else "+"
        lap: Dict[str, Tuple[Any, Any]] = {}
        for x in ds:
            lap.setdefault(str(x["video_id"]), (x.get("huong"), x.get("moc")))
        cong = sum(1 for h, _ in lap.values() if h == huong)
        tru = len(lap) - cong
        tt = kn.trang_thai(cong, tru, kn.ma_bai_kn(truc, gt, cum) in gach)
        cung = [x for x in ds if x.get("huong") == huong] or ds
        so_dan = next((x.get("so_dan") for x in ds if x.get("so_dan")), []) or []
        ra.append({"id": "BH-" + bam("gd|{0}|{1}|{2}|{3}".format(kenh, truc, gt, cum), 8),
                   "bo_phan": TRUC_BO_PHAN.get(truc, "chon-content"), "nguon": "giam-doc/bai-hoc.jsonl",
                   "trang_thai": {"that": DANG_DUNG, "bo": NGHI}.get(tt, THU_THACH if tru else UNG_VIEN),
                   "alpha": 1 + cong, "beta": 1 + tru, "n": cong + tru, "kenh": kenh, "truc": truc,
                   "cap_nhat": luc_tu(ds[-1].get("luc")), "cau": str(cung[-1].get("cau") or ""),
                   "bong": all(x.get("bong") for x in cung),
                   "bang_chung": ["video `{0}` ({1}{2})".format(v, "ủng hộ" if h == huong else "phản bác",
                                                                ", " + str(m) if m else "")
                                  for v, (h, m) in sorted(lap.items())],
                   "so_dan": ["`{0}` = {1}".format(s.get("nguon"), s.get("so")) for s in so_dan
                              if isinstance(s, dict)][:8]})
    return ra


def bai_hoc_san_xuat(goc: str, kenh: str) -> List[Dict[str, Any]]:
    """`CHANNEL/<k>/nghien-cuu/bai-hoc-san-xuat.json` (quan sát số, không có bộ đếm thắng/thua): α = 1 + {thấp 0,
    vừa 1, cao 2} theo độ tin của nguồn, β = 1 (+1 khi nguồn ghi "mâu thuẫn"); cao → đang dùng, mâu thuẫn → thử
    thách, còn lại → ứng viên; n = số mẫu."""
    d = doc_json(os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "bai-hoc-san-xuat.json"))
    if not isinstance(d, dict):
        return []
    ra, da = [], Counter()
    for b in d.get("bai_hoc") or []:
        if not isinstance(b, dict) or not b.get("quan_sat"):
            continue
        truc, cum, dtc = str(b.get("truc") or ""), str(b.get("cum") or ""), str(b.get("do_tin_cay") or "")
        da[(truc, cum)] += 1
        mt = "mâu thuẫn" in str(b["quan_sat"])
        ra.append({"id": "BH-" + bam("sx|{0}|{1}|{2}|{3}".format(kenh, truc, cum, da[(truc, cum)]), 8),
                   "bo_phan": TRUC_BO_PHAN.get(truc, "chon-content"), "nguon": "nghien-cuu/bai-hoc-san-xuat.json",
                   "trang_thai": THU_THACH if mt else DANG_DUNG if dtc == "cao" else UNG_VIEN,
                   "alpha": 1 + {"vua": 1, "cao": 2}.get(dtc, 0), "beta": 1 + int(mt), "n": int(b.get("so_mau") or 0),
                   "kenh": kenh, "truc": truc, "cap_nhat": luc_tu(b.get("ngay_cap_nhat") or d.get("cap_nhat_luc")),
                   "cau": str(b["quan_sat"]), "bong": False,
                   "bang_chung": ["video `{0}`".format(v) for v in b.get("video_dan_chung") or []] +
                                 ["độ tin của nguồn: {0}".format(dtc or "?")], "so_dan": []})
    return ra


def ve_bai_hoc(b: Dict[str, Any]) -> str:
    bp = b["bo_phan"]
    dau = {"loai": "bai-hoc", "id": b["id"], "bo_phan": bp, "nguon": b["nguon"], "trang_thai": b["trang_thai"],
           "alpha": b["alpha"], "beta": b["beta"], "n": b["n"], "kenh": b["kenh"], "truc": b["truc"],
           "bong": bool(b.get("bong")), "cap_nhat": ngay_gio(b.get("cap_nhat"))}
    than = ["# " + " ".join(b["cau"].split()), "", "## Bằng chứng"] + ["- " + x for x in b["bang_chung"][:15]]
    if b.get("so_dan"):
        than.append("- Số dẫn: " + " · ".join(b["so_dan"]))
    than += ["", "## Liên kết", "- {0} · {1}".format(lk(bp + "/so-tay", "Sổ tay " + BO_PHAN.get(bp, bp)),
                                                     lk_kenh(b["kenh"]))]
    return ve_ghi_chu(dau, "\n".join(than))


def doc_bai_hoc(goc: str, kenh_ds: Sequence[str], bay_gio: float) -> Tuple[List[Dict[str, Any]], int]:
    """Mọi bài học của mọi kênh (+ số nguồn đọc hỏng)."""
    ra: List[Dict[str, Any]] = []
    hong = 0
    for k in kenh_ds:
        for ham in (lambda: bai_hoc_giam_doc(goc, k, bay_gio), lambda: bai_hoc_san_xuat(goc, k)):
            try:
                ra += ham()
            except Exception:  # noqa: BLE001 — một sổ hỏng không chặn sổ khác
                hong += 1
    return ra, hong


# ── sổ tay, bản đồ, nốt kênh ─────────────────────────────────────────────────

def _cat_muc(muc: Sequence[Tuple[str, List[str]]], tran: int) -> List[str]:
    """Ghép các mục (tiêu đề, dòng) theo thứ tự ưu tiên, tổng ≤ `tran` dòng; dòng bị cắt được đếm ở dòng cuối."""
    ra: List[str] = []
    bo = 0
    for tieu_de, dong in muc:
        if not dong:
            continue
        if len(ra) + 3 > tran - 1:
            bo += len(dong)
            continue
        ra += ["", tieu_de]
        for x in dong:
            if len(ra) < tran - 1:
                ra.append(x)
            else:
                bo += 1
    if bo:
        ra.append("- … còn {0} mục (xem thư mục `loi/`, `bai-hoc/`)".format(bo))
    return ra


def doc_bai_ngu(vault: str, bp: str = "") -> List[Dict[str, Any]]:
    """Bài học DO GIẤC NGỦ rút (`nguon: ngu`) của một / mọi bộ phận, đọc thẳng từ vault: frontmatter + `cau` +
    `duong` + `than` (thân nguyên văn — giữ mục Lịch sử). Mã bài tự rút là `BH-N…` (bản chiếu: `BH-<hex thường>`)."""
    ra = []
    for p in sorted(glob.glob(os.path.join(vault, bp or "*", "bai-hoc", "BH-N*.md"))):
        dau, than = doc_ghi_chu(doc_chu(p) or "")
        if dau.get("nguon") == NGUON_NGU:
            dau.update(duong=p, than=than, cau=next((d[2:].strip() for d in than.splitlines() if d.startswith("# ")),
                                                     ""))
            ra.append(dau)
    return ra


def _tb(b: Dict[str, Any]) -> float:
    a, be = float(b.get("alpha") or 1), float(b.get("beta") or 1)
    return a / (a + be)


def ve_so_tay(bp: str, loi: Sequence[Dict[str, Any]], bai: Sequence[Dict[str, Any]], bay_gio: float,
              bai_ngu: Sequence[Dict[str, Any]] = ()) -> str:
    """Sổ tay bộ phận (dựng tất định): (a) lỗi đang xảy ra/tái phát — nhịp sự cố 48h so 5 ngày trước, rồi số lần 7
    ngày; (b) bài học tự rút (giấc ngủ) còn sống; (c) cảnh báo đang có; (d) lỗi đã hết trong 14 ngày qua; (e) bài
    học bản chiếu tốt nhất theo α/(α+β) với n ≥ 3. Tổng ≤ `SO_TAY_TOI_DA_DONG` dòng."""
    song = [n for n in loi if n["trang_thai"] in (DANG, TAI_PHAT)]
    xep = lambda n: (-n.get("ti_le_tang", 0.0), -n.get("n48", 0), -n["so_7"], -n["lan_cuoi"])  # noqa: E731
    dang = sorted((n for n in song if n.get("muc", LOI) != CANH_BAO), key=xep)
    canh = sorted((n for n in song if n.get("muc", LOI) == CANH_BAO), key=xep)
    het = sorted((n for n in loi if n["trang_thai"] == DA_HET
                  and n["lan_cuoi"] >= bay_gio - (NGAY_DA_HET + NGAY_HET_GAN_DAY) * NGAY), key=lambda n: -n["lan_cuoi"])
    tot = sorted((b for b in bai if b["n"] >= N_BAI_HOC_SO_TAY and b["trang_thai"] != NGHI), key=lambda b: -_tb(b))
    hang = {DANG_DUNG: 0, THU_THACH: 1, UNG_VIEN: 2}
    tu_rut = sorted((b for b in bai_ngu if b.get("trang_thai") != NGHI),
                    key=lambda b: (hang.get(b.get("trang_thai"), 3), -_tb(b), str(b.get("id"))))
    muc = [
        ("## Lỗi đang xảy ra ({0})".format(len(dang)),
         ["- **{0}×/7 ngày** · {1} sự cố/48h ×{2} {3} — {4} kênh{5}{6}".format(
             n["so_7"], n.get("n48", 0), n.get("ti_le_tang", 0.0), lk(n["id"], n["cau_chinh"]), len(n["kenh"]),
             ", TÁI PHÁT" if n["trang_thai"] == TAI_PHAT else "",
             ", có cách sửa đã kiểm" if sua_da_kiem(n, bay_gio) else "") for n in dang]),
        ("## Bài học tự rút — giấc ngủ ({0})".format(len(tu_rut)),
         ["- **{0:.2f}** {1} — {2} bằng chứng · {3}{4}".format(
             _tb(b), lk(b["bo_phan"] + "/bai-hoc/" + str(b["id"]), b["cau"]), b.get("n", 0),
             TEN_TRANG_THAI.get(b.get("trang_thai"), b.get("trang_thai")), " · chỉ gợi ý" if b.get("chi_goi_y") else "")
          for b in tu_rut]),
        ("## Cảnh báo đang có — dự phòng đã cứu / mục kiểm không chặn ({0})".format(len(canh)),
         ["- {0}×/7 ngày · {1} sự cố/48h {2}".format(n["so_7"], n.get("n48", 0), lk(n["id"], n["cau_chinh"]))
          for n in canh]),
        ("## Đã hết gần đây ({0})".format(len(het)),
         ["- {0} — im từ {1} ({2} lần trước đó){3}".format(lk(n["id"], n["cau_chinh"]), ngay_gio(n["lan_cuoi"])[:10],
                                                           n["so_lan"], ", có cách sửa đã kiểm"
                                                           if sua_da_kiem(n, bay_gio) else "") for n in het]),
        ("## Bài học tốt nhất (n ≥ {0}, {1})".format(N_BAI_HOC_SO_TAY, len(tot)),
         ["- **{0:.2f}** {1} — n {2} · {3} · {4}".format(b["alpha"] / (b["alpha"] + b["beta"]),
                                                         lk(b["bo_phan"] + "/bai-hoc/" + b["id"], b["cau"]), b["n"],
                                                         b["kenh"], TEN_TRANG_THAI[b["trang_thai"]]) for b in tot]),
    ]
    dau_bai = ["# Sổ tay — " + BO_PHAN.get(bp, bp), "",
               "Máy dựng lại từ số mỗi lần gom / ngủ (không LLM). Lỗi xếp theo nhịp sự cố 48h so 5 ngày trước; bài "
               "học theo α/(α+β). {0} · {1}".format(lk("_ban-do", "Bản đồ"), lk(bp + "/nhat-ky", "Nhật ký"))]
    than = dau_bai + _cat_muc(muc, SO_TAY_TOI_DA_DONG - len(dau_bai))
    if len(than) == len(dau_bai):
        than += ["", "(chưa có lỗi đang xảy ra, lỗi vừa hết hay bài học đủ mẫu)"]
    return ve_ghi_chu({"loai": "so-tay", "bo_phan": bp}, "\n".join(than))


def ve_ban_do(dem: Dict[str, Dict[str, int]]) -> str:
    than = ["# Bản đồ não bộ phận", "",
            "Mỗi bộ phận: sổ tay (thứ bộ phận đọc khi làm) · nơ-ron lỗi theo trạng thái · cảnh báo · bài học (bản "
            "chiếu + tự rút khi ngủ) · nhật ký. Máy dựng lại mỗi lần `python -m core.nao_bo_phan gom` / `ngu`.", ""]
    for bp, ten in BO_PHAN.items():
        c = dem.get(bp) or {}
        than.append("- {0} — {1} sự kiện/7 ngày · lỗi: {2} đang xảy ra, {3} tái phát, {4} tạm lặng, {5} đã hết · "
                    "{6} cảnh báo · {7} bài học ({8} tự rút)".format(
                        lk(bp + "/so-tay", ten), c.get("su_kien_7", 0), c.get(DANG, 0), c.get(TAI_PHAT, 0),
                        c.get(TAM_LANG, 0), c.get(DA_HET, 0), c.get("canh_bao", 0), c.get("bai_hoc", 0),
                        c.get("bai_ngu", 0)))
    return ve_ghi_chu({"loai": "ban-do"}, "\n".join(than))


def ve_the(the: str) -> str:
    """Nốt thực thể `thuc-the/<loại>/<tên>.md` (kênh, khâu, engine, bộ chọn, mã kiểm)."""
    loai, _, ten = the.partition("/")
    return ve_ghi_chu({"loai": loai, "ten": ten}, "# {0}\n\nNốt thực thể {1} — nơ-ron lỗi và bài học của {1} này nối "
                      "vào đây (Obsidian: Backlinks / Graph).".format(ten, THUC_THE.get(loai, loai)))


def ve_kenh(kenh: str) -> str:
    return ve_the("kenh/" + kenh)


def _nhat_ky_gom(vault: str, cu: Dict[str, Tuple[str, str]], moi: Dict[str, Tuple[str, str, str]],
                 bay_gio: float) -> int:
    """Mỗi bộ phận MỘT khối nhật ký khi não đổi so với lượt trước: nơ-ron mới, đổi trạng thái, nơ-ron bị bỏ.
    `cu`/`moi`: {id: (bộ phận, trạng thái[, câu])} — chỉ nơ-ron do máy dựng (lỗi + bản chiếu), không gồm bài tự rút."""
    dong: Dict[str, List[str]] = {}
    for id_, (bp, tt, cau) in sorted(moi.items()):
        if id_ not in cu:
            dong.setdefault(bp, []).append("- mới: {0} ({1})".format(lk(id_, cau), TEN_TRANG_THAI.get(tt, tt)))
        elif cu[id_][1] != tt:
            dong.setdefault(bp, []).append("- {0}: {1} → {2}".format(lk(id_, cau), TEN_TRANG_THAI.get(cu[id_][1],
                                                                                                    cu[id_][1]),
                                                                    TEN_TRANG_THAI.get(tt, tt)))
    for id_, (bp, tt) in sorted(cu.items()):
        if id_ not in moi:
            dong.setdefault(bp, []).append("- bỏ: `{0}` (không còn sự kiện / nguồn)".format(id_))
    return sum(ghi_nhat_ky(vault, bp, ngay_gio(bay_gio) + " — gom", d) for bp, d in dong.items() if bp in BO_PHAN)


# ── dựng cả vault ────────────────────────────────────────────────────────────

def dung_vault(con: sqlite3.Connection, goc: str, ra: str, bay_gio: float) -> Dict[str, Any]:
    """Nơ-ron lỗi + bài học + nốt thực thể + sổ tay + bản đồ (ghi CHỈ tệp đổi nội dung) + nhật ký thay đổi rồi dựng
    lại chỉ mục. Bài học TỰ RÚT (`nguon: ngu`) không bao giờ bị đụng ở đây — chỉ giấc ngủ / soát sửa chúng."""
    kenh_ds = cac_kenh(goc)
    vault = duong_vault(ra)
    ghi = 0
    try:
        cu = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT id, bo_phan, trang_thai FROM no_ron WHERE COALESCE(nguon, '') != ?", (NGUON_NGU,))}
    except sqlite3.Error:
        cu = {}
    loi = gom_no_ron_loi(con, kenh_ds, bay_gio)
    giu = set()
    for n in loi.values():
        p = os.path.join(vault, n["bo_phan"], "loi", n["chu_ky"] + ".md")
        giu.add(os.path.normcase(p))
        ghi += ghi_neu_khac(p, ve_loi(n, bay_gio))
    for p in glob.glob(os.path.join(vault, "*", "loi", "*.md")):
        if os.path.normcase(p) not in giu:
            os.remove(p)
    bai, hong = doc_bai_hoc(goc, kenh_ds, bay_gio)
    giu = set()
    for b in bai:
        p = os.path.join(vault, b["bo_phan"], "bai-hoc", b["id"] + ".md")
        giu.add(os.path.normcase(p))
        ghi += ghi_neu_khac(p, ve_bai_hoc(b))
    moi = {n["id"]: (n["bo_phan"], n["trang_thai"], n["cau_chinh"]) for n in loi.values()}
    moi.update({b["bo_phan"] + "/bai-hoc/" + b["id"]: (b["bo_phan"], b["trang_thai"], b["cau"]) for b in bai})
    for p in glob.glob(os.path.join(vault, "*", "bai-hoc", "BH-*.md")):     # biến khỏi nguồn → nghỉ, không xoá
        if os.path.normcase(p) not in giu:
            dau, than = doc_ghi_chu(doc_chu(p) or "")
            if not dau or dau.get("nguon") == NGUON_NGU:
                continue
            if dau.get("trang_thai") != NGHI:
                dau["trang_thai"] = NGHI
                ghi += ghi_neu_khac(p, ve_ghi_chu(dau, than))
            moi[os.path.relpath(p, vault)[:-3].replace("\\", "/")] = (str(dau.get("bo_phan") or ""), NGHI, next(
                (d[2:].strip() for d in than.splitlines() if d.startswith("# ")), ""))
    bai_ngu = doc_bai_ngu(vault)
    the = {"kenh/" + k for n in loi.values() for k in n["kenh"]} | {"kenh/" + b["kenh"] for b in bai if b["kenh"]}
    the |= {t for n in loi.values() for t in n["the"]} | {t for b in bai_ngu for t in b.get("pham_vi") or []
                                                           if t.partition("/")[0] in THUC_THE}
    for t in sorted(the):
        loai_t, _, ten = t.partition("/")
        ghi += ghi_neu_khac(os.path.join(vault, "thuc-the", loai_t, ten_tep(ten) + ".md"), ve_the(t))
    dem: Dict[str, Dict[str, int]] = {bp: Counter() for bp in BO_PHAN}
    for bp, n in con.execute("SELECT bo_phan, COUNT(*) FROM su_kien WHERE luc >= ? GROUP BY 1", (bay_gio - 7 * NGAY,)):
        if bp in dem:
            dem[bp]["su_kien_7"] = n
    for n in loi.values():
        dem[n["bo_phan"]]["canh_bao" if n["muc"] == CANH_BAO else n["trang_thai"]] += 1
    for b in bai:
        if b["trang_thai"] != NGHI:
            dem[b["bo_phan"]]["bai_hoc"] += 1
    for b in bai_ngu:
        if b.get("trang_thai") != NGHI and b.get("bo_phan") in dem:
            dem[b["bo_phan"]]["bai_hoc"] += 1
            dem[b["bo_phan"]]["bai_ngu"] += 1
    for bp in BO_PHAN:
        ghi += ghi_neu_khac(os.path.join(vault, bp, "so-tay.md"), ve_so_tay(
            bp, [n for n in loi.values() if n["bo_phan"] == bp], [b for b in bai if b["bo_phan"] == bp], bay_gio,
            [b for b in bai_ngu if b.get("bo_phan") == bp]))
    ghi += ghi_neu_khac(os.path.join(vault, "_ban-do.md"), ve_ban_do(dem))
    nhat_ky = _nhat_ky_gom(vault, cu, moi, bay_gio) if cu else 0
    chi_muc = dung_lai_chi_muc(ra, con)
    return {"no_ron": {bp: {k: v for k, v in c.items() if k != "su_kien_7"} for bp, c in dem.items()},
            "ghi_tep": ghi, "canh_bao_bai_hoc": hong, "chi_muc": chi_muc, "nhat_ky": nhat_ky}


# ── chỉ mục (dựng lại được hoàn toàn từ vault) ───────────────────────────────

_RE_LK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")


def _dich(t: str) -> str:
    t = t.strip()
    return t[len("bo-phan/"):] if t.startswith("bo-phan/") else t


def dung_lai_chi_muc(ra: str, con: Optional[sqlite3.Connection] = None) -> Dict[str, int]:
    """Xoá rồi dựng lại `no_ron`, `chi_muc_tri`, `chi_muc_viet`, `lien_ket` CHỈ từ các tệp .md của vault."""
    rieng = con is None
    con = con or kho.mo(ra, cho=5.0)
    vault = duong_vault(ra)
    dem = Counter()
    try:
        for bang in ("no_ron", "chi_muc_tri", "chi_muc_viet", "lien_ket"):
            con.execute("DELETE FROM " + bang)
        for thu_muc, _, tep_ds in os.walk(vault):
            for ten in sorted(tep_ds):
                if not ten.endswith(".md"):
                    continue
                p = os.path.join(thu_muc, ten)
                id_ = os.path.relpath(p, vault)[:-3].replace("\\", "/")
                dau, than = doc_ghi_chu(doc_chu(p) or "")
                loai, bp = dau.get("loai"), str(dau.get("bo_phan") or "")
                if loai == "nhat-ky":           # nhật ký chỉ nối thêm: không tính là liên kết của nơ-ron
                    continue
                con.executemany("INSERT OR IGNORE INTO lien_ket(tu, toi) VALUES (?,?)",
                                [(id_, _dich(m.group(1))) for m in _RE_LK.finditer(than)])
                if loai not in ("loi", "bai-hoc"):
                    continue
                cau = next((d[2:].strip() for d in than.splitlines() if d.startswith("# ")), id_)
                kenh = dau.get("kenh")
                kenh = [str(k) for k in kenh] if isinstance(kenh, list) else [str(kenh)] if kenh else []
                con.execute("INSERT OR REPLACE INTO no_ron(id, loai, bo_phan, trang_thai, cau, duong, alpha, beta, n, "
                            "so_lan_7, lan_cuoi, kenh, muc, nguon, su_co_48, ti_le_tang, vao_loi_nhac) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (id_, loai, bp, str(dau.get("trang_thai") or ""), cau, "nao/bo-phan/" + id_ + ".md",
                             float(dau.get("alpha") or 1), float(dau.get("beta") or 1),
                             int(dau.get("so_lan") or dau.get("n") or 0), int(dau.get("so_lan_7_ngay") or 0),
                             luc_tu(dau.get("lan_cuoi") or dau.get("cap_nhat")), json.dumps(kenh, ensure_ascii=False),
                             str(dau.get("muc") or LOI), str(dau.get("nguon") or "") if loai == "bai-hoc" else "",
                             int(dau.get("su_co_48h") or 0), float(dau.get("ti_le_tang") or 0),
                             int(bool(dau.get("vao_loi_nhac")))))
                van = " ".join([cau, _RE_LK.sub(lambda m: m.group(2) or m.group(1), than), BO_PHAN.get(bp, ""),
                                " ".join(kenh)])
                for bang in ("chi_muc_tri", "chi_muc_viet"):
                    con.execute("INSERT INTO {0}(id, bo_phan, van) VALUES (?,?,?)".format(bang), (id_, bp, van))
                dem[loai] += 1
        con.commit()
    finally:
        if rieng:
            con.close()
    return dict(dem)
