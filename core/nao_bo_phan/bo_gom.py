"""BỘ GOM — đọc các kho CÓ SẴN (không sửa bộ phận nào), tăng dần theo con trỏ, đổi thành sự kiện có khoá bền.

Hai kiểu tệp: `tep` (JSON đọc cả tệp — chỉ đọc lại khi mtime/kích thước đổi; khoá bền chống trùng) và `noi` (nhật ký
chỉ nối thêm — đọc từ vị trí đã gom; đầu tệp đổi hoặc tệp ngắn lại = tệp mới, đọc từ đầu). Lần đầu thấy một tệp chỉ
nhận sự kiện trong `NGAY_GOM_DAU` ngày trước đó (mốc ghi vào con trỏ, giữ mãi). Tệp hỏng/thiếu → một cảnh báo được
đếm, KHÔNG bao giờ dừng cả lượt gom. Bảng nguồn `NGUON` ở cuối tệp.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import time
from collections import Counter
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from . import kho
from ._chung import (GOC, KHAU_BO_PHAN, NGAY_GOM_DAU, NHAN_KHAU, PHIEN_KY, bam, cac_kenh, chu_ky, chu_ky_su_kien,
                     doc_json, jdong as _jdong, luc_tu, tim_kenh)

_LO = 500   # số dòng mỗi lần chèn


class Ngu:
    """Ngữ cảnh đọc một tệp: tên nguồn, danh sách kênh, kênh của thư mục chứa tệp, mtime, trạng thái mang qua
    các lần gom (vd. khâu đang chạy của từng kênh trong `tu-chay.log`)."""

    def __init__(self, nguon: str, kenh_ds: Sequence[str], kenh: str = "", mtime: float = 0.0,
                 trang: Optional[Dict[str, Any]] = None) -> None:
        self.nguon, self.kenh_ds, self.kenh, self.mtime = nguon, kenh_ds, kenh, mtime
        self.trang = trang if trang is not None else {}

    def sk(self, bo_phan: str, loai: str, luc: Optional[float], khoa: str, noi_dung: Any = "", *,
           kenh: Optional[str] = None, ma_goi: str = "", chu_ky_: str = "", so: Optional[Dict[str, Any]] = None
           ) -> Optional[kho.Dong]:
        return kho.dong_su_kien(bo_phan, loai, luc=luc or self.mtime, kenh=self.kenh if kenh is None else kenh,
                                ma_goi=ma_goi, chu_ky_=chu_ky_, noi_dung=noi_dung, so=so, nguon=self.nguon,
                                khoa=khoa, kenh_ds=self.kenh_ds)

    def loi(self, bo_phan: str, cau: Any, luc: Optional[float], khoa_dau: str, **kw: Any) -> Optional[kho.Dong]:
        """Sự kiện lỗi: chữ ký từ câu đã chuẩn hoá, khoá = `khoa_dau|chữ ký`."""
        ck = kw.pop("chu_ky_", "") or chu_ky(cau, self.kenh_ds)
        return self.sk(bo_phan, "loi", luc, khoa_dau + "|" + ck, cau, chu_ky_=ck, **kw)


def _goi(kenh: str, luot: str) -> str:
    return "{0}-{1}".format(kenh, luot) if kenh and luot else ""


def _tim_goi(van: str, kenh: str) -> str:
    m = re.search(re.escape(kenh) + r"-\d{3,}", van) if kenh else None
    return m.group(0) if m else ""


def _json_tep(duong: str) -> Any:
    d = doc_json(duong)
    if d is None:
        raise ValueError("không đọc được JSON")
    return d


# ── sổ ngày `CHANNEL/<k>/tu-chay/YYYY-MM-DD.json` ───────────────────────────

_RE_DUNG_O = re.compile(r"^\s*(?:chưa xong hết\s*[—-]\s*)?(?:\[HỎNG\]\s*)?Dừng ở “([^”]+)”\s*[:.]?\s*(.*)$")


def tach_dung_o(cau: str) -> Tuple[str, str]:
    """Câu `Dừng ở “<nhãn khâu>”: <lý do>` → (mã khâu, lý do). Không khớp → ("", cả câu)."""
    m = _RE_DUNG_O.match(cau or "")
    if not m:
        return "", str(cau or "").strip()
    return NHAN_KHAU.get(m.group(1), ""), m.group(2).strip() or cau.strip()


def loi_khau(ngu: Ngu, kenh: str, luot: str, khau: str, ly_do: str, luc: Optional[float]) -> Optional[kho.Dong]:
    """Lỗi của MỘT khâu trong MỘT lượt — khoá không mang tên nguồn, nên sổ ngày và `trang-thai.json` báo cùng một
    lỗi chỉ thành một sự kiện."""
    return ngu.loi(KHAU_BO_PHAN.get(khau, "dieu-phoi"), ly_do, luc, "khau|{0}|{1}|{2}".format(kenh, luot, khau),
                   kenh=kenh, ma_goi=_goi(kenh, luot), so={"khau": khau, "luot": luot})


def doc_so_ngay(duong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    d = _json_tep(duong)
    ngay = str(d.get("ngay") or os.path.basename(duong)[:10])
    kenh = str(d.get("kenh") or ngu.kenh)
    het_ngay = luc_tu(ngay + "T23:59:59")
    luc = min(ngu.mtime, het_ngay) if het_ngay else ngu.mtime
    for r in d.get("runs") or []:
        if not isinstance(r, dict) or not r.get("ma_luot"):
            continue                          # dòng `tham_chieu_ma_luot` trỏ về sổ ngày gốc — sổ gốc đã có
        luot = str(r["ma_luot"])
        goi, k = _goi(kenh, luot), "{0}|{1}|{2}".format(kenh, ngay, luot)
        ng = r.get("nguon") if isinstance(r.get("nguon"), dict) else {}
        if ng.get("ma"):
            ly = ng.get("ly_do")
            ly = " · ".join(map(str, ly)) if isinstance(ly, list) else str(ly or "")
            yield ngu.sk("chon-content", "chon", luc, "chon|" + k, "{0} — {1}".format(ng.get("tieu_de") or "", ly),
                         kenh=kenh, ma_goi=goi, so={x: ng.get(x) for x in ("ma", "nguon", "diem", "cong_thuc", "loai",
                                                                           "cum", "tuyen", "view", "vph", "tham_do")})
        sx = r.get("san_xuat") if isinstance(r.get("san_xuat"), dict) else {}
        hong = [str(x) for x in sx.get("khau_hong") or []]
        for cau in (sx.get("loi_dung"), sx.get("loi")):
            if cau:
                khau, ly_do = tach_dung_o(str(cau))
                yield loi_khau(ngu, kenh, luot, khau or (hong[0] if hong else ""), ly_do, luc)
        bg = r.get("ban_giao") if isinstance(r.get("ban_giao"), dict) else {}
        if bg.get("loi"):
            yield ngu.loi("ban-giao", bg["loi"], luc, "ban-giao|" + k, kenh=kenh, ma_goi=goi)
        if bg.get("ly_do_trong") and not bg.get("da_ban_giao"):   # để trống mà VẪN bàn giao (tự duyệt tay) = không lỗi
            yield ngu.loi("ban-giao", bg["ly_do_trong"], luc, "ban-giao|" + k, kenh=kenh, ma_goi=goi)
        if r.get("bo"):
            yield ngu.loi("dieu-phoi", r.get("ly_do_bo") or "lượt bị bỏ", luc, "bo|" + k, kenh=kenh, ma_goi=goi)
        ph = r.get("phuc_hoi")
        if isinstance(ph, dict) and ph.get("so_lan"):
            yield ngu.sk("dieu-phoi", "sua", luc, "phuc-hoi|{0}|{1}".format(k, ph["so_lan"]),
                         "tự phục hồi (nhặt lại) lượt — lần {0}".format(ph["so_lan"]), kenh=kenh, ma_goi=goi,
                         so={"so_lan": ph.get("so_lan"), "loai_loi_truoc": ph.get("loai_loi_truoc")})


# ── lượt `PROJECTS/AUTO/<k>/<lượt>/trang-thai.json` + `9-chat-luong.json` ─────────────────────────────────────

def doc_trang_thai(duong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    d = _json_tep(duong)
    kenh = str(d.get("ma_kenh") or ngu.kenh)
    luot = str(d.get("ma_luot") or os.path.basename(os.path.dirname(duong)))
    for x, v in (d.get("khau") or {}).items():
        if not isinstance(v, dict):
            continue
        luc = luc_tu(v.get("ket_thuc")) or ngu.mtime
        if v.get("loi"):
            yield loi_khau(ngu, kenh, luot, x, str(v["loi"]), luc)
        tt, n = str(v.get("trang_thai") or ""), int(v.get("so_lan") or 0)
        if tt in ("xong", "hong") and v.get("ket_thuc"):       # một khâu đã KẾT THÚC = một sự kiện đo
            giay = round(luc - (luc_tu(v.get("bat_dau")) or luc), 1)
            yield ngu.sk(KHAU_BO_PHAN.get(x, "dieu-phoi"), "do", luc,
                         "khau-do|{0}|{1}|{2}|{3}|{4}".format(kenh, luot, x, n, tt),
                         "khâu {0}: {1}, {2} lần, {3:.0f} giây".format(x, tt, n, giay), kenh=kenh,
                         ma_goi=_goi(kenh, luot), so={"khau": x, "trang_thai": tt, "so_lan": n, "giay": giay})


def doc_chat_luong(duong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    d = _json_tep(duong)
    luc, lan = luc_tu(d.get("luc")) or ngu.mtime, str(d.get("luc") or "")
    goi, kenh = str(d.get("ma_goi") or ""), str(d.get("kenh") or ngu.kenh)
    k = "{0}|{1}".format(goi, lan)
    yield ngu.sk("kiem-chat-luong", "ket_qua", luc, "qa-ket|" + k, "điểm chất lượng {0} — {1}".format(
        d.get("diem"), "đạt" if d.get("dat") else "CHẶN"), kenh=kenh, ma_goi=goi,
        so={"diem": d.get("diem"), "dat": d.get("dat"), "so_loi": len(d.get("loi") or []),
            "so_lan_chan": d.get("so_lan_chan")})
    for l in d.get("loi") or []:
        if isinstance(l, dict) and l.get("ma"):
            ma = str(l["ma"])                 # chữ ký theo MÃ kiểm (chi tiết có số đổi từng video)
            so = {"ma": ma, "muc": l.get("muc"), "sua": l.get("sua"), "diem": d.get("diem")}
            yield ngu.sk("kiem-chat-luong", "loi", luc, "qa|{0}|{1}".format(k, ma), "{0} ({1}): {2}".format(
                ma, l.get("muc") or "", l.get("chi_tiet") or ""), kenh=kenh, ma_goi=goi,
                chu_ky_=chu_ky_su_kien(ngu.nguon, "loi", "", so, ()), so=so)
    for s in d.get("da_sua") or []:
        yield ngu.sk("kiem-chat-luong", "sua", luc, "qa-sua|{0}|{1}".format(k, bam(str(s))),
                     "đã tự sửa: {0}".format(s), kenh=kenh, ma_goi=goi)
    if d.get("lam_lai"):
        yield ngu.sk("kiem-chat-luong", "sua", luc, "qa-lam-lai|" + k, "mở lại khâu clip + dựng cho {0} cảnh".format(
            len(d["lam_lai"])), kenh=kenh, ma_goi=goi, so={"canh": list(d["lam_lai"])[:60]})


# ── máy ảo `vm/logs/` ─────────────────────────────────────────────────────────

LOI_TAI = ("loi-tai", "tai-hong", "lech-lich")


def doc_so_video_id(duong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    for khoa_goi, v in (_json_tep(duong) or {}).items():
        if not isinstance(v, dict):
            continue
        kenh, _, goi = str(khoa_goi).partition("/")
        luc, tt, lan = luc_tu(v.get("cap_nhat")), str(v.get("trang_thai") or ""), int(v.get("lan_tai_moi") or 0)
        so = {x: v.get(x) for x in ("trang_thai", "lan_tai_moi", "phu_de", "mhkt", "the", "tai_xong")}
        if tt in LOI_TAI:
            yield ngu.loi("dang-video", "tải video lên YouTube hỏng (trạng thái {0})".format(tt), luc,
                          "svid|{0}|{1}|{2}".format(khoa_goi, tt, lan), kenh=kenh, ma_goi=goi, so=so)
        elif tt in ("xac-nhan", "da-len-lich"):
            yield ngu.sk("dang-video", "ket_qua", luc, "svid|{0}|{1}".format(khoa_goi, tt),
                         "đã tải + hẹn lịch trên YouTube ({0})".format(tt), kenh=kenh, ma_goi=goi, so=so)
        if lan > 1:
            yield ngu.loi("dang-video", "phải tải lại video lên YouTube (lần tải {0})".format(lan), luc,
                          "svid|{0}|tai-lai|{1}".format(khoa_goi, lan), kenh=kenh, ma_goi=goi, so=so)


def doc_cmt_dom(duong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    for vid, v in (_json_tep(duong) or {}).items():
        if not isinstance(v, dict):
            continue
        if str(vid).startswith("_kenh:"):
            if v.get("can_xac_minh"):
                yield ngu.loi("binh-luan", "kênh cần xác minh mới ghim được bình luận", luc_tu(v["can_xac_minh"]),
                              "cmt|{0}|xac-minh|{1}".format(vid, v["can_xac_minh"]), kenh=str(vid)[6:])
            continue
        tt = str(v.get("trang_thai") or "")
        if tt:
            yield ngu.sk("binh-luan", "ket_qua", luc_tu(v.get("cap_nhat")), "cmt|{0}|{1}".format(vid, tt),
                         "bình luận mồi: {0}".format(tt), kenh=str(v.get("kenh") or ""), ma_goi=str(v.get("ma") or ""),
                         so={x: v.get(x) for x in ("trang_thai", "lan_gui", "lan_thu_ghim", "ghim")})


_RE_VM = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)[,.]\d+\s+(\w+):\s*(.*)$")
_RE_DOM = re.compile(r"^(DU PHONG|TU CHUA)\s+([\w.-]+)\s*:?\s*(.*)$")


def dong_nhat_ky_vm(bo_phan: str) -> Callable[[str, Ngu], Iterator[Optional[kho.Dong]]]:
    """Nhật ký máy DOM (`dang-dom.log`, `cmt-dom.log`): dòng `DU PHONG`/`TU CHUA <khoá>` = bộ chọn chính hụt (chữ ký
    theo KHOÁ bộ chọn — trôi DOM gom về một nơ-ron; DU PHONG = dự phòng đã cứu, là CẢNH BÁO, nơ-ron riêng với TU CHUA)
    + dòng ERROR. Dòng không ghi tên kênh thì lấy kênh được nhắc gần nhất trong cùng nhật ký (máy DOM làm lần lượt
    từng kênh)."""
    def doc(dong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
        m = _RE_VM.match(dong)
        if not m:
            return
        ts, muc, van = m.group(1), m.group(2), m.group(3).strip()
        kenh = tim_kenh(van, ngu.kenh_ds)
        if kenh:
            ngu.trang["kenh"] = kenh
        khoa = "{0}|{1}|{2}".format(ngu.nguon, ts, bam(van))
        k = _RE_DOM.match(van)
        if k:
            so = {"khoa_dom": k.group(2), "kieu": k.group(1)}
            yield ngu.sk(bo_phan, "loi", luc_tu(ts), khoa, "bộ chọn {0}: {1} — {2}".format(k.group(2), k.group(1),
                         k.group(3)), kenh=kenh or str(ngu.trang.get("kenh") or ""),
                         chu_ky_=chu_ky_su_kien(ngu.nguon, "loi", "", so, ()), so=so)
        elif muc == "ERROR":
            yield ngu.loi(bo_phan, van, luc_tu(ts), khoa, kenh=kenh, ma_goi=_tim_goi(van, kenh))
    return doc


def dong_tu_chua(dong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    """`tu-chua-dom.jsonl`: bộ chọn tự chữa — `chua` (đã chữa) là `sua`, còn lại (hụt/bỏ/loại) là `loi`; cùng
    chữ ký với dòng `DU PHONG` của khoá đó."""
    d = _jdong(dong)
    kd, ket = str(d.get("khoa") or ""), str(d.get("ket") or "")
    if kd:
        so = {"khoa_dom": kd, "ket": ket, "chon": d.get("chon")}
        yield ngu.sk("dang-video", "sua" if ket == "chua" else "loi", luc_tu(d.get("luc")),
                     "tu-chua|{0}|{1}|{2}|{3}".format(d.get("luc"), kd, ket, bam(str(d.get("chon")))),
                     "bộ chọn {0}: tự chữa {1} — {2}".format(kd, ket, d.get("ly_do") or d.get("chon") or ""), kenh="",
                     chu_ky_=chu_ky_su_kien(ngu.nguon, "loi", "", so, ()), so=so)


# ── gác tổng, viết Max, radar, ván tự học, nhật ký tự chạy ─────────────────────

#: Loại cảnh báo gác tổng → bộ phận (khớp CHUỖI CON theo thứ tự; còn lại là điều phối).
GAC_BO_PHAN = (("tai_len", "dang-video"), ("hen_lich", "dang-video"), ("ban_chup", "chi-so-studio"),
               ("khong_phat", "chi-so-studio"), ("giong_doc", "giong-doc"), ("ram", "suc-khoe-may"),
               ("dia", "suc-khoe-may"), ("khoa_may", "suc-khoe-may"), ("qua_nhieu", "suc-khoe-may"),
               ("tram", "suc-khoe-may"), ("agent", "suc-khoe-may"), ("license", "suc-khoe-may"),
               ("schtasks", "suc-khoe-may"), ("claude_max", "suc-khoe-may"))


def bo_phan_gac(loai: str) -> str:
    return next((bp for k, bp in GAC_BO_PHAN if k in loai), "dieu-phoi")


def dong_gac_tong(dong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    """`tu_sua:*` = `sua`; `giam_doc_viec` (việc nhờ người, không phải lỗi) = `do`; còn lại = `loi`. Gác tổng nhắc
    lại cùng một sự cố mỗi 15 phút — cùng `dedupe_khoa` chỉ tính MỘT sự kiện mỗi ngày."""
    d = _jdong(dong)
    lo = str(d.get("loai") or "")
    if not lo:
        return
    loai = "sua" if lo.startswith("tu_sua") else "do" if lo == "giam_doc_viec" else "loi"
    cau = str(d.get("chuyen_gi") or lo)
    kenh = str(d.get("kenh") or "") or tim_kenh(cau, ngu.kenh_ds)
    khoa = ("gac|{0}|{1}".format(d["dedupe_khoa"], str(d.get("luc"))[:10]) if d.get("dedupe_khoa") else
            "gac|{0}|{1}|{2}|{3}".format(d.get("luc"), lo, kenh, bam(cau)))
    yield ngu.sk(bo_phan_gac(lo.split(":", 1)[-1]), loai, luc_tu(d.get("luc")), khoa, cau, kenh=kenh,
                 ma_goi=_tim_goi(cau, kenh), so={"loai": lo, "muc": d.get("muc")})


#: Tên việc viết Max → bộ phận (khớp chuỗi con theo thứ tự, `_` coi như `-`; còn lại là kịch bản). Việc không tên
#: được `viet_max` ghi là `@<mô-đun gọi>` (từ 13/10/2026) — tên mô-đun cũng khớp bảng này.
VIEC_BO_PHAN = (("nao-bo-phan", "dieu-phoi"), ("thumb", "bia"), ("bia", "bia"), ("tieu-de", "tieu-de"),
                ("seo", "tieu-de"), ("binh-luan", "binh-luan"), ("bien-tap", "chon-content"),
                ("chon-content", "chon-content"), ("cum", "chon-content"), ("y-kien", "chon-content"),
                ("trung-y", "chon-content"), ("chien-truong", "chon-content"), ("phong-thi-nghiem", "chon-content"),
                ("doi-thu", "doi-thu"), ("chi-so", "chi-so-studio"), ("giam-doc", "dieu-phoi"))


def dong_viet_max(dong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    d = _jdong(dong)
    if not d.get("luc"):
        return
    viec = str(d.get("viec") or "")
    bp = next((b for k, b in VIEC_BO_PHAN if k in viec.replace("_", "-")), "kich-ban")
    so = {x: d.get(x) for x in ("ok", "giay", "token_vao", "token_ra", "usd_uoc", "mo_hinh", "effort", "luot")}
    khoa = "viet-max|{0}|{1}|{2}".format(d.get("luc"), d.get("pid"), bam(viec))
    kenh = tim_kenh(viec, ngu.kenh_ds)
    if d.get("ok"):
        yield ngu.sk(bp, "do", luc_tu(d["luc"]), khoa, "gọi Claude Max {0}: ok {1} giây".format(
            viec or "(không tên)", d.get("giay")), kenh=kenh, so=so)
    else:
        yield ngu.loi(bp, "Claude Max hỏng: {0}".format(d.get("loi") or "không rõ"), luc_tu(d["luc"]), khoa,
                      kenh=kenh, so=dict(so, viec=viec))


def dong_radar(dong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    d = _jdong(dong)
    if d.get("ma") and d.get("luc"):
        gan = str(d.get("gan") or "")
        yield ngu.sk("chon-content", "chon", luc_tu(d["luc"]), "radar|{0}|{1}|{2}".format(d["luc"], d["ma"],
                     d.get("quyet")), "radar {0}: {1} — {2}".format(d.get("quyet") or "?", d.get("kenh_nguon") or "",
                                                                    d.get("vi_sao") or ""),
                     kenh=gan if gan in ngu.kenh_ds else "",
                     so={x: d.get(x) for x in ("ma", "quyet", "view", "ky_vong", "boi", "muc", "tuoi_gio", "vung")})


def doc_van(duong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    """Ván tự học đã PHÁN theo thước chung (`core.thuoc_thang`): thắng / trung bình / trượt."""
    for goi, v in (_json_tep(duong) or {}).items():
        if isinstance(v, dict) and v.get("ket") in ("thang", "trung_binh", "truot"):
            yield ngu.sk("chon-content", "ket_qua", ngu.mtime, "van|{0}|{1}|{2}".format(goi, v["ket"], v.get("thuoc")),
                         "{0}: {1} (phân vị {2} @ {3}h)".format(goi, v["ket"], v.get("ket_pv"), v.get("ket_tuoi")),
                         ma_goi=str(goi), so={"ket": v["ket"], "ket_pv": v.get("ket_pv"), "ket_tuoi": v.get("ket_tuoi"),
                                              "ket_gia_tri": v.get("ket_gia_tri"), "thuoc": v.get("thuoc"),
                                              "nuoc": v.get("nuoc")})


_RE_LOG = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\]\s*(?:\[([^\]]+)\])?\s*(.*)$")
_RE_DANG = re.compile(r"^\[ĐANG\]\s+(.+?)(?:\s+\(.*)?$")
#: Dòng LỖI rõ ràng (bảo thủ): `[HỎNG]` / LỖI / "lỗi:" / ngoại lệ Python / "hỏng (…" hay "hỏng:" / thất bại / hết
#: lượt thử. ("hỏng" giữa câu giải thích — "hỏng vì lý do khác thì…" — không tính.)
_RE_LOI_LOG = re.compile(r"\[HỎNG\]|LỖI|\blỗi:|Traceback|\b\w+(?:Error|Exception)\b|\bhỏng(?=\s*[(:])|thất bại|"
                         r"hết lượt thử")
#: … trừ câu nói "không lỗi" và chữ của biên tập/chấm bài (LLM bình về "lỗi" của bản viết).
_RE_KHONG_LOI = re.compile(r"không (?:lỗi|hỏng)|\[biên tập|chấm toàn bài|chọn bản")


def dong_tu_chay(dong: str, ngu: Ngu) -> Iterator[Optional[kho.Dong]]:
    """`workspace/tu-chay/tu-chay.log`: bộ phận = khâu ghi trong dòng (“nhãn khâu”), không có thì khâu kênh đó
    đang chạy (dòng `[ĐANG] <nhãn>` gần nhất — nhớ qua các lần gom), không nữa thì điều phối."""
    m = _RE_LOG.match(dong)
    if not m:
        return
    ts, kenh, van = m.group(1), m.group(2) or "", m.group(3).strip()
    k = _RE_DANG.match(van)
    if k and k.group(1) in NHAN_KHAU:
        ngu.trang.setdefault("khau", {})[kenh] = NHAN_KHAU[k.group(1)]
        return
    if not _RE_LOI_LOG.search(van) or _RE_KHONG_LOI.search(van):
        return
    khau = next((x for nhan, x in NHAN_KHAU.items() if "“" + nhan + "”" in van), "") or \
        (ngu.trang.get("khau") or {}).get(kenh, "")
    kenh_that = kenh if kenh in ngu.kenh_ds else tim_kenh(van, ngu.kenh_ds)
    yield ngu.loi(KHAU_BO_PHAN.get(khau, "dieu-phoi"), van, luc_tu(ts), "tu-chay.log|{0}|{1}|{2}".format(
        ts, kenh, bam(van)), kenh=kenh_that, ma_goi=_tim_goi(van, kenh_that), so={"khau": khau})


# ── bảng nguồn + vòng gom ─────────────────────────────────────────────────────

Tim = Callable[[str, Sequence[str]], List[Tuple[str, str]]]


def _o_kenh(*duoi: str) -> Tim:
    return lambda goc, ks: [(p, k) for k in ks for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", k, *duoi)))]


def _o_luot(ten: str) -> Tim:
    return lambda goc, ks: [(p, k) for k in ks
                            for p in sorted(glob.glob(os.path.join(goc, "PROJECTS", "AUTO", k, "*", ten)))]


def _o(*duoi: str) -> Tim:
    return lambda goc, ks: [(p, "") for p in sorted(glob.glob(os.path.join(goc, *duoi)))]


#: (tên nguồn, kiểu, tìm tệp, đọc). Kiểu `tep`: đọc(đường, ngữ cảnh); kiểu `noi`: đọc(dòng, ngữ cảnh).
NGUON: Tuple[Tuple[str, str, Tim, Callable[..., Iterable[Optional[kho.Dong]]]], ...] = (
    ("so-ngay", "tep", _o_kenh("tu-chay", "????-??-??.json"), doc_so_ngay),
    ("trang-thai", "tep", _o_luot("trang-thai.json"), doc_trang_thai),
    ("chat-luong", "tep", _o_luot("9-chat-luong.json"), doc_chat_luong),
    ("so-video-id", "tep", _o("vm", "logs", "so-video-id.json"), doc_so_video_id),
    ("cmt-dom", "tep", _o("vm", "logs", "cmt-dom.json"), doc_cmt_dom),
    ("cmt-dom.log", "noi", _o("vm", "logs", "cmt-dom.log"), dong_nhat_ky_vm("binh-luan")),
    ("dang-dom.log", "noi", _o("vm", "logs", "dang-dom.log"), dong_nhat_ky_vm("dang-video")),
    ("tu-chua-dom", "noi", _o("vm", "logs", "tu-chua-dom.jsonl"), dong_tu_chua),
    ("gac-tong", "noi", _o("workspace", "gac-tong", "*.jsonl"), dong_gac_tong),
    ("viet-max", "noi", _o("workspace", "viet-max", "so-dung.jsonl"), dong_viet_max),
    ("radar", "noi", _o("CHANNEL", "_NHOM", "*", "radar", "quyet-dinh.jsonl"), dong_radar),
    ("van", "tep", _o_kenh("tu-hoc", "van.json"), doc_van),
    ("tu-chay.log", "noi", _o("workspace", "tu-chay", "tu-chay.log"), dong_tu_chay),
)


def _con_tro(con: sqlite3.Connection, tep: str) -> Optional[Dict[str, Any]]:
    r = con.execute("SELECT mtime, kich_thuoc, vi_tri, dau, tu, trang FROM con_tro WHERE tep=?", (tep,)).fetchone()
    if r is None:
        return None
    return {"mtime": r[0], "kich_thuoc": r[1], "vi_tri": r[2], "dau": r[3], "tu": r[4],
            "trang": json.loads(r[5] or "{}")}


def _dat_con_tro(con: sqlite3.Connection, tep: str, mtime: float, kt: int, vi_tri: int, dau: str, tu: float,
                 trang: Dict[str, Any]) -> None:
    con.execute("INSERT OR REPLACE INTO con_tro(tep, mtime, kich_thuoc, vi_tri, dau, tu, trang) VALUES (?,?,?,?,?,?,?)",
                (tep, mtime, kt, vi_tri, dau, tu, json.dumps(trang, ensure_ascii=False)))


def _dau_tep(duong: str) -> str:
    with open(duong, "rb") as tep:
        return bam(tep.read(256).hex())


def gom_tep(con: sqlite3.Connection, goc: str, ten: str, kieu: str, doc: Callable[..., Iterable[Any]], duong: str,
            kenh: str, kenh_ds: Sequence[str], bay_gio: float, canh_bao: Counter) -> int:
    """Gom MỘT tệp theo con trỏ. Trả số sự kiện mới. Dòng đọc hỏng → cảnh báo, đọc tiếp."""
    tep = os.path.relpath(duong, goc).replace("\\", "/")
    st = os.stat(duong)
    ct = _con_tro(con, tep)
    if ct and ct["mtime"] == st.st_mtime and ct["kich_thuoc"] == st.st_size:
        return 0
    tu = ct["tu"] if ct else bay_gio - NGAY_GOM_DAU * 86400
    dau = _dau_tep(duong) if kieu == "noi" else ""
    if ct is None and st.st_mtime < tu:       # tệp im từ trước cửa sổ nhìn lùi: không đọc, chỉ đánh dấu
        _dat_con_tro(con, tep, st.st_mtime, st.st_size, st.st_size, dau, tu, {})
        con.commit()
        return 0
    ngu = Ngu(ten, kenh_ds, kenh, st.st_mtime, dict((ct or {}).get("trang") or {}))
    them = 0
    if kieu == "tep":
        them = kho.ghi_nhieu(con, [d for d in doc(duong, ngu) if d and d[0] >= tu])
        vi_tri = st.st_size
    else:
        vi_tri = ct["vi_tri"] if ct and ct["dau"] == dau and st.st_size >= (ct["vi_tri"] or 0) else 0
        lo: List[kho.Dong] = []
        with open(duong, "rb") as f:
            f.seek(vi_tri)
            for dong_b in f:
                if not dong_b.endswith(b"\n"):
                    break                     # dòng đang ghi dở — để lần sau
                vi_tri += len(dong_b)
                try:
                    lo += [d for d in doc(dong_b.decode("utf-8", "replace").rstrip("\r\n"), ngu) if d and d[0] >= tu]
                except Exception:  # noqa: BLE001 — một dòng hỏng không chặn cả tệp
                    canh_bao[ten] += 1
                if len(lo) >= _LO:
                    them += kho.ghi_nhieu(con, lo)
                    lo = []
        them += kho.ghi_nhieu(con, lo)
    _dat_con_tro(con, tep, st.st_mtime, st.st_size, vi_tri, dau, tu, ngu.trang)
    con.commit()
    return them


def gom_su_kien(con: sqlite3.Connection, goc: str, bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Chạy mọi nguồn. Trả `{"tep": {nguồn: số tệp đã đọc}, "canh_bao": {nguồn: số}}`."""
    bay_gio = bay_gio or time.time()
    kenh_ds = cac_kenh(goc)
    doc_tep: Counter = Counter()
    canh_bao: Counter = Counter()
    for ten, kieu, tim, doc in NGUON:
        try:
            ds = tim(goc, kenh_ds)
        except Exception:  # noqa: BLE001
            canh_bao[ten] += 1
            continue
        for duong, kenh in ds:
            try:
                gom_tep(con, goc, ten, kieu, doc, duong, kenh, kenh_ds, bay_gio, canh_bao)
                doc_tep[ten] += 1
            except Exception:  # noqa: BLE001 — tệp hỏng/thiếu: đếm, đi tiếp
                canh_bao[ten] += 1
                try:
                    con.rollback()
                except sqlite3.Error:
                    pass
    return {"tep": dict(doc_tep), "canh_bao": dict(canh_bao)}


def ky_lai(con: sqlite3.Connection, kenh_ds: Sequence[str]) -> Dict[str, int]:
    """Tính lại chữ ký mọi sự kiện `loi`/`sua` DO BỘ GOM tạo (nguồn trong `NGUON`) theo luật hiện hành
    (`chu_ky_su_kien`); khoá có đuôi `|<chữ ký cũ>` đổi theo để lần gom sau không chèn trùng (đụng khoá có sẵn = cùng
    một sự kiện → giữ khoá cũ). Không xoá dòng nào. Ghi `meta.phien_ky`."""
    nguon_gom = {n[0] for n in NGUON}
    dem: Counter = Counter()
    for id_, nguon, loai, nd, so, ck, khoa in con.execute(
            "SELECT id, nguon, loai, noi_dung, so, chu_ky, khoa FROM su_kien WHERE loai IN ('loi', 'sua')").fetchall():
        if nguon not in nguon_gom:
            continue
        dem["xet"] += 1
        try:
            moi = chu_ky_su_kien(nguon, loai, nd, json.loads(so or "{}"), kenh_ds, ck or "")
        except ValueError:
            continue
        if moi == (ck or ""):
            continue
        k_moi = khoa[:-len(ck)] + moi if ck and str(khoa).endswith("|" + ck) else khoa
        try:
            con.execute("UPDATE su_kien SET chu_ky = ?, khoa = ? WHERE id = ?", (moi, k_moi, id_))
        except sqlite3.IntegrityError:
            con.execute("UPDATE su_kien SET chu_ky = ? WHERE id = ?", (moi, id_))
            dem["giu_khoa"] += 1
        dem["doi"] += 1
    kho.dat_meta(con, "phien_ky", PHIEN_KY)
    con.commit()
    return dict(dem)


def gom(goc: str = GOC, ra: str = "", bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Một lượt gom đầy đủ: sự kiện (đọc ở `goc`) → nơ-ron + sổ tay + bản đồ + chỉ mục (ghi ở `ra`, mặc định
    `goc`). Luật ký đổi (`PHIEN_KY`) thì `ky_lai` một lần TRƯỚC khi gom. Trả bảng tóm tắt (`__main__.in_tom_tat`)."""
    from . import no_ron  # noqa: PLC0415

    t0 = time.time()
    bay_gio = bay_gio or time.time()
    ra = ra or goc
    con = kho.mo(ra, cho=5.0)
    try:
        ky = ky_lai(con, cac_kenh(goc)) if kho.doc_meta(con, "phien_ky") != str(PHIEN_KY) else {}
        truoc = con.execute("SELECT COALESCE(MAX(id), 0) FROM su_kien").fetchone()[0]
        tk = gom_su_kien(con, goc, bay_gio)
        if ky.get("doi"):
            tk["ky_lai"] = ky
        them: Dict[str, Dict[str, int]] = {}
        for bp, loai, n in con.execute("SELECT bo_phan, loai, COUNT(*) FROM su_kien WHERE id > ? GROUP BY 1, 2",
                                       (truoc,)):
            them.setdefault(bp, {})[loai] = n
        tk["them"] = them
        tk["them_nguon"] = dict(con.execute("SELECT nguon, COUNT(*) FROM su_kien WHERE id > ? GROUP BY 1", (truoc,)))
        tk.update(no_ron.dung_vault(con, goc, ra, bay_gio))
        kho.dat_meta(con, "gom_cuoi", "%.0f" % time.time())     # skill D12 (`core/ky_nang.py`) đọc: gom cũ > 2 giờ → gom lại
        con.commit()
    finally:
        con.close()
    tk["giay"] = round(time.time() - t0, 2)
    return tk
