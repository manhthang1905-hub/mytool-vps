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
from ._chung import (BO_PHAN, DA_HET, DANG, DANG_DUNG, GIO_DANG_XAY_RA, N_BAI_HOC_SO_TAY, NGAY_DA_HET,
                     NGAY_HET_GAN_DAY, NGHI, SO_TAY_TOI_DA_DONG, TAI_PHAT, TAM_LANG, TEN_TRANG_THAI, THU_THACH,
                     TRUC_BO_PHAN, UNG_VIEN, bam, cac_kenh, chuan_hoa, doc_chu, doc_ghi_chu, doc_json,
                     duong_vault, ghi_neu_khac, jdong as _jdong, lk, lk_kenh, luc_tu, ngay_gio, ten_tep, ve_ghi_chu)

NGAY = 86400.0


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
    for bp, ck, luc, loai, kenh, nd, nguon in con.execute(
            "SELECT bo_phan, chu_ky, luc, loai, kenh, noi_dung, nguon FROM su_kien "
            "WHERE chu_ky != '' AND loai IN ('loi', 'sua') ORDER BY luc, id"):
        n = nr.get((bp, ck))
        if loai == "sua":
            if n is not None:
                n["sua"].append((luc, nd))
            continue
        if n is None:
            n = nr[(bp, ck)] = {"bo_phan": bp, "chu_ky": ck, "so_lan": 0, "so_7": 0, "so_48": 0, "lan_dau": luc,
                                "lan_cuoi": luc, "tro_lai": None, "ngay": Counter(), "kenh": Counter(),
                                "nguon": set(), "vi_du": deque(maxlen=3), "cau": Counter(), "sua": deque(maxlen=5)}
        elif luc - n["lan_cuoi"] >= NGAY_DA_HET * NGAY:
            n["tro_lai"] = luc
        n["so_lan"] += 1
        n["lan_cuoi"] = luc
        if luc >= bay_gio - 7 * NGAY:
            n["so_7"] += 1
            n["ngay"][time.strftime("%m-%d", time.localtime(luc))] += 1
        if luc >= bay_gio - GIO_DANG_XAY_RA * 3600:
            n["so_48"] += 1
        if kenh:
            n["kenh"][kenh] += 1
        if nguon:
            n["nguon"].add(nguon)
        n["vi_du"].append((luc, kenh, nd))
        n["cau"][chuan_hoa(nd, kenh_ds)] += 1
    for n in nr.values():
        n["trang_thai"] = trang_thai_loi(n["lan_cuoi"], n["tro_lai"], bay_gio)
        n["cau_chinh"] = n["cau"].most_common(1)[0][0] if n["cau"] else n["chu_ky"]
        n["id"] = "{0}/loi/{1}".format(n["bo_phan"], n["chu_ky"])
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
    dau = {"loai": "loi", "chu_ky": n["chu_ky"], "bo_phan": bp, "trang_thai": n["trang_thai"],
           "so_lan": n["so_lan"], "so_lan_7_ngay": n["so_7"], "so_lan_48h": n["so_48"],
           "lan_dau": ngay_gio(n["lan_dau"]), "lan_cuoi": ngay_gio(n["lan_cuoi"]), "kenh": kenh,
           "nguon": sorted(n["nguon"])}
    ngay7 = [time.strftime("%m-%d", time.localtime(bay_gio - i * NGAY)) for i in range(6, -1, -1)]
    than = ["# " + n["cau_chinh"], "", "## Quan sát",
            "- {0} — tổng {1} lần, lần đầu {2}, lần cuối {3}{4}.".format(
                TEN_TRANG_THAI[n["trang_thai"]], n["so_lan"], ngay_gio(n["lan_dau"]), ngay_gio(n["lan_cuoi"]),
                ", quay lại sau quãng im ≥ {0} ngày lúc {1}".format(NGAY_DA_HET, ngay_gio(n["tro_lai"]))
                if n["tro_lai"] else ""),
            "- 7 ngày: " + " · ".join("{0}: {1}".format(d, n["ngay"].get(d, 0)) for d in ngay7)]
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


def ve_so_tay(bp: str, loi: Sequence[Dict[str, Any]], bai: Sequence[Dict[str, Any]], bay_gio: float) -> str:
    """Sổ tay bộ phận (dựng tất định): (a) lỗi đang xảy ra/tái phát theo số lần 7 ngày, (b) lỗi đã hết trong 14 ngày
    qua, (c) bài học tốt nhất theo trung bình hậu nghiệm α/(α+β) với n ≥ 3. Tổng ≤ `SO_TAY_TOI_DA_DONG` dòng."""
    dang = sorted((n for n in loi if n["trang_thai"] in (DANG, TAI_PHAT)), key=lambda n: (-n["so_7"], -n["lan_cuoi"]))
    het = sorted((n for n in loi if n["trang_thai"] == DA_HET
                  and n["lan_cuoi"] >= bay_gio - (NGAY_DA_HET + NGAY_HET_GAN_DAY) * NGAY), key=lambda n: -n["lan_cuoi"])
    tot = sorted((b for b in bai if b["n"] >= N_BAI_HOC_SO_TAY and b["trang_thai"] != NGHI),
                 key=lambda b: -b["alpha"] / (b["alpha"] + b["beta"]))
    muc = [
        ("## Lỗi đang xảy ra ({0})".format(len(dang)),
         ["- **{0}×/7 ngày** {1} — {2} kênh{3}{4}".format(n["so_7"], lk(n["id"], n["cau_chinh"]), len(n["kenh"]),
                                                          ", TÁI PHÁT" if n["trang_thai"] == TAI_PHAT else "",
                                                          ", có cách sửa đã kiểm" if sua_da_kiem(n, bay_gio) else "")
          for n in dang]),
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
               "Máy dựng lại từ số mỗi lần gom (không LLM). Lỗi xếp theo số lần trong 7 ngày; bài học theo "
               "α/(α+β). {0}".format(lk("_ban-do", "Bản đồ"))]
    than = dau_bai + _cat_muc(muc, SO_TAY_TOI_DA_DONG - len(dau_bai))
    if len(than) == len(dau_bai):
        than += ["", "(chưa có lỗi đang xảy ra, lỗi vừa hết hay bài học đủ mẫu)"]
    return ve_ghi_chu({"loai": "so-tay", "bo_phan": bp}, "\n".join(than))


def ve_ban_do(dem: Dict[str, Dict[str, int]]) -> str:
    than = ["# Bản đồ não bộ phận", "",
            "Mỗi bộ phận: sổ tay (thứ bộ phận đọc khi làm) · nơ-ron lỗi theo trạng thái · bài học (bản chiếu). Máy "
            "dựng lại mỗi lần `python -m core.nao_bo_phan gom`.", ""]
    for bp, ten in BO_PHAN.items():
        c = dem.get(bp) or {}
        than.append("- {0} — {1} sự kiện/7 ngày · lỗi: {2} đang xảy ra, {3} tái phát, {4} tạm lặng, {5} đã hết · "
                    "{6} bài học".format(lk(bp + "/so-tay", ten), c.get("su_kien_7", 0), c.get(DANG, 0),
                                         c.get(TAI_PHAT, 0), c.get(TAM_LANG, 0), c.get(DA_HET, 0), c.get("bai_hoc", 0)))
    return ve_ghi_chu({"loai": "ban-do"}, "\n".join(than))


def ve_kenh(kenh: str) -> str:
    return ve_ghi_chu({"loai": "kenh", "ten": kenh}, "# {0}\n\nNốt thực thể kênh — nơ-ron lỗi và bài học của kênh này "
                      "nối vào đây (Obsidian: Backlinks / Graph).".format(kenh))


# ── dựng cả vault ────────────────────────────────────────────────────────────

def dung_vault(con: sqlite3.Connection, goc: str, ra: str, bay_gio: float) -> Dict[str, Any]:
    """Nơ-ron lỗi + bài học + nốt kênh + sổ tay + bản đồ (ghi CHỈ tệp đổi nội dung) rồi dựng lại chỉ mục."""
    kenh_ds = cac_kenh(goc)
    vault = duong_vault(ra)
    ghi = 0
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
    for p in glob.glob(os.path.join(vault, "*", "bai-hoc", "BH-*.md")):     # biến khỏi nguồn → nghỉ, không xoá
        if os.path.normcase(p) not in giu:
            dau, than = doc_ghi_chu(doc_chu(p) or "")
            if dau and dau.get("trang_thai") != NGHI:
                dau["trang_thai"] = NGHI
                ghi += ghi_neu_khac(p, ve_ghi_chu(dau, than))
    for k in sorted({k for n in loi.values() for k in n["kenh"]} | {b["kenh"] for b in bai if b["kenh"]}):
        ghi += ghi_neu_khac(os.path.join(vault, "thuc-the", "kenh", ten_tep(k) + ".md"), ve_kenh(k))
    dem: Dict[str, Dict[str, int]] = {bp: Counter() for bp in BO_PHAN}
    for bp, n in con.execute("SELECT bo_phan, COUNT(*) FROM su_kien WHERE luc >= ? GROUP BY 1", (bay_gio - 7 * NGAY,)):
        if bp in dem:
            dem[bp]["su_kien_7"] = n
    for n in loi.values():
        dem[n["bo_phan"]][n["trang_thai"]] += 1
    for b in bai:
        if b["trang_thai"] != NGHI:
            dem[b["bo_phan"]]["bai_hoc"] += 1
    for bp in BO_PHAN:
        ghi += ghi_neu_khac(os.path.join(vault, bp, "so-tay.md"), ve_so_tay(
            bp, [n for n in loi.values() if n["bo_phan"] == bp], [b for b in bai if b["bo_phan"] == bp], bay_gio))
    ghi += ghi_neu_khac(os.path.join(vault, "_ban-do.md"), ve_ban_do(dem))
    chi_muc = dung_lai_chi_muc(ra, con)
    return {"no_ron": {bp: {k: v for k, v in c.items() if k != "su_kien_7"} for bp, c in dem.items()},
            "ghi_tep": ghi, "canh_bao_bai_hoc": hong, "chi_muc": chi_muc}


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
                con.executemany("INSERT OR IGNORE INTO lien_ket(tu, toi) VALUES (?,?)",
                                [(id_, _dich(m.group(1))) for m in _RE_LK.finditer(than)])
                loai, bp = dau.get("loai"), str(dau.get("bo_phan") or "")
                if loai not in ("loi", "bai-hoc"):
                    continue
                cau = next((d[2:].strip() for d in than.splitlines() if d.startswith("# ")), id_)
                kenh = dau.get("kenh")
                kenh = [str(k) for k in kenh] if isinstance(kenh, list) else [str(kenh)] if kenh else []
                con.execute("INSERT OR REPLACE INTO no_ron(id, loai, bo_phan, trang_thai, cau, duong, alpha, beta, n, "
                            "so_lan_7, lan_cuoi, kenh) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (id_, loai, bp, str(dau.get("trang_thai") or ""), cau, "nao/bo-phan/" + id_ + ".md",
                             float(dau.get("alpha") or 1), float(dau.get("beta") or 1),
                             int(dau.get("so_lan") or dau.get("n") or 0), int(dau.get("so_lan_7_ngay") or 0),
                             luc_tu(dau.get("lan_cuoi") or dau.get("cap_nhat")), json.dumps(kenh, ensure_ascii=False)))
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
