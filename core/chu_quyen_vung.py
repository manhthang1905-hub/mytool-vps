"""CHỦ QUYỀN VÙNG ĐỀ TÀI — mỗi vùng đề tài một kênh chủ, chống kênh anh em ăn thịt nhau (12/10/2026).

`workspace/chan-doan/v7-chon-content-2026-10-12.md` mục 4 + 6 (P7b): ăn thịt nhau xảy ra ở tầng ĐỀ TÀI chứ không ở tầng
link — top-20 V7 của 7 kênh gần như là một danh sách (26/72 mã ở ≥ 2 kênh), TL6 × TL6-K2 chung 13/20 ứng viên VPH,
top-5 V7 của TL4-T7 có 4 nguồn kênh anh em đã làm; lệnh tấn công giao trùng vùng cho hai kênh. Trong khi vùng lớn và
đang lên nhất (tuổi tác, 17% thị trường) ta chỉ giữ 0,06%, và ~39% thị trường chưa kênh nào nhận.

═══ BẢN ĐỒ ═══ `workspace/chien-truong/chu-quyen-vung.json` (máy này; sửa tay được):

    {"phien_ban": 1, "luc": "...", "he_so_phat": 0.6,
     "vung": {"<mã vùng>": {"chu": "<kênh>", "nguon": "tu_dong" | "tay", "ly_do": "...",
                            "chia_se": ["<kênh được dùng không phạt>"], "nhuong": false, "chan": false,
                            "thang": {"<kênh>": n}, "thi_truong": <view đối thủ 28 ngày>}}}

  * `nguon: "tay"` — dòng chủ dự án sửa: lần sinh lại GIỮ NGUYÊN. Dòng "tu_dong" sinh lại mỗi ngày (`cap_nhat`, gọi từ
    `chien_truong.tinh`), nhưng ỔN ĐỊNH: chủ cũ chỉ mất vùng khi kênh khác có NHIỀU video thắng hơn trong vùng, hoặc
    khi chủ cũ không còn được YouTube phát.
  * Chủ = kênh có nhiều video THẮNG (thước chung `core.thuoc_thang`) nhất trong vùng (bằng nhau → tổng hiển thị của
    các video thắng). Vùng có thị trường mà CHƯA kênh nào thắng = "vùng nóng chưa chủ" → giao kênh HỢP TỆP nhất còn
    được phát (`_diem_hop`): vùng là cụm RIÊNG của tệp kênh đó (mã `tep-*` trong cấu hình V7 của nó) > kênh đã có video
    trong vùng (phân vị cùng tuổi) > lệnh tấn công của chiến trường giao vùng cho nó; trừ dần theo số vùng kênh đã
    giữ (để toả ra phủ ngách, không dồn một kênh).

═══ ÁP KHI CHỌN NGUỒN ═══ `ap_he_so(nc, bang)` (gọi từ `chien_luoc.xep_hang`, sau lệnh tấn công): ứng viên thuộc vùng
mà kênh ANH EM KHÁC (cùng nhóm) làm chủ → điểm × `he_so_phat` (0,6 như P7b) hoặc bị bỏ (`chan: true`) — TRỪ KHI: kênh
mình nằm trong `chia_se`, chủ đã `nhuong` vùng, hoặc chính kênh chủ đã PHỦ QUYẾT đúng nguồn ấy (biên tập của nó chấm
TỆ, `bien-tap/nho-cham.json`) — nguồn chủ đã từ chối thì kênh khác được nhận. Vùng của ứng viên = nhãn cụm tự học (như
`chien_luoc.tan_cong`), "khac"/rỗng → vùng AI theo link (`workspace/chien-truong/vung-ai.json`).

Không mạng, không tiền; chỉ đọc/ghi đĩa. Không mã kênh/ngách viết cứng.

    python -m core.chu_quyen_vung            # in bản đồ ĐỀ XUẤT (không ghi)
    python -m core.chu_quyen_vung --ghi      # ghi bản đồ (giữ dòng sửa tay)
"""

from __future__ import annotations

import copy
import datetime as _dt
import io
import json
import os
import re
import statistics
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

TEP = os.path.join("workspace", "chien-truong", "chu-quyen-vung.json")
TEP_LICH_SU = os.path.join("workspace", "chien-truong", "lich-su.jsonl")
TEP_TAN_CONG = os.path.join("workspace", "chien-truong", "tan-cong.json")
HE_SO_PHAT = 0.6
KHAC = "khac"
#: Vùng "nóng" cần ít nhất ngần này view đối thủ 28 ngày để được giao chủ khi chưa ai thắng.
THI_TRUONG_TOI_THIEU = 500_000
#: Kênh "được phát": trung vị hiển thị (mới nhất) các video đủ 3 ngày tuổi ≥ ngần này, hoặc đã có video thắng.
SAN_DUOC_PHAT = 300.0
#: Điểm hợp tệp (`_diem_hop`).
DIEM_TEP_RIENG = 3.0
DIEM_CO_MAT = 1.0
DIEM_LENH = 1.0
TRU_MOI_VUNG = 1.5
_RE_BAN_THU = re.compile(r"-v\d+$")


def duong(goc: str) -> str:
    return os.path.join(goc, TEP)


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def doc(goc: str) -> Dict[str, Any]:
    """Bản đồ đang dùng (`{}` khi chưa có / hỏng)."""
    du = _doc_json(duong(goc))
    return du if isinstance(du, dict) and isinstance(du.get("vung"), dict) else {}


def ghi(goc: str, du: Dict[str, Any]) -> str:
    p = duong(goc)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(json.dumps(du, ensure_ascii=False, indent=1) + "\n")
    os.replace(tam, p)
    return p


# ── chọn chủ (hàm thuần) ─────────────────────────────────────────────────────

def _diem_hop(kenh: str, vung: str, tk: Dict[str, Dict[str, Dict[str, Any]]], tep_rieng: Dict[str, Set[str]],
              lenh: Dict[str, Set[str]], so_vung_giu: Dict[str, int]) -> float:
    o = (tk.get(vung) or {}).get(kenh) or {}
    d = 0.0
    if vung in (tep_rieng.get(kenh) or set()):
        d += DIEM_TEP_RIENG
    if o.get("n"):
        d += DIEM_CO_MAT + (float(o.get("pv_tb") or 0.0) / 100.0)
    if vung in (lenh.get(kenh) or set()):
        d += DIEM_LENH
    return d - TRU_MOI_VUNG * so_vung_giu.get(kenh, 0)


def chon_chu(tk: Dict[str, Dict[str, Dict[str, Any]]], song: Dict[str, bool], thi_truong: Dict[str, float],
             tep_rieng: Dict[str, Set[str]], *, cu: Optional[Dict[str, Any]] = None,
             lenh: Optional[Dict[str, Set[str]]] = None,
             hop_ai: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    """Bản đồ `{vùng: mục}` (xem đầu tệp) từ thống kê `tk = {vùng: {kênh: {thang, n, hien_thi_thang, pv_tb}}}`,
    `song = {kênh: được phát?}`, `thi_truong = {vùng: view đối thủ}`, `tep_rieng = {kênh: {mã cụm riêng của tệp}}`,
    bản đồ cũ `cu` (dòng `tay` giữ nguyên; dòng `tu_dong` ổn định), lệnh tấn công `lenh = {kênh: {vùng}}` và
    `hop_ai = {vùng: kênh}` — kênh hợp tệp nhất theo NGHĨA do AI đọc (`hoi_ai_hop_tep`), thắng điểm hợp tệp của máy
    cho vùng nóng chưa ai thắng (kênh đó phải còn được phát).

    Bằng số video thắng: kênh mà vùng là phần LỚN HƠN trong các video thắng của nó (vùng "lõi" của kênh) được chủ —
    không để kênh nhiều thắng ở chỗ khác giành vùng lõi của kênh nhỏ — rồi tới tổng hiển thị."""
    cu_vung = dict((cu or {}).get("vung") or {})
    lenh = lenh or {}
    hop_ai = hop_ai or {}
    tong_thang: Dict[str, int] = {}
    for theo_k in tk.values():
        for k, o in theo_k.items():
            tong_thang[k] = tong_thang.get(k, 0) + int(o.get("thang") or 0)
    ra: Dict[str, Dict[str, Any]] = {}
    for v, m in cu_vung.items():
        if isinstance(m, dict) and m.get("nguon") == "tay":
            ra[v] = copy.deepcopy(m)
    so_vung: Dict[str, int] = {}
    for m in ra.values():
        if m.get("chu"):
            so_vung[m["chu"]] = so_vung.get(m["chu"], 0) + 1
    # 1) vùng có video THẮNG: chủ = nhiều thắng nhất (bằng → tổng hiển thị của video thắng); chủ cũ chỉ mất vùng khi
    #    kênh khác NHIỀU thắng hơn hẳn hoặc chủ cũ không còn được phát.
    for v in sorted(tk):
        if v in ra or v in ("", KHAC):
            continue
        thang = {k: o for k, o in tk[v].items() if int(o.get("thang") or 0) > 0}
        if not thang:
            continue
        tot = max(thang, key=lambda k: (int(thang[k]["thang"]),
                                        int(thang[k]["thang"]) / float(max(1, tong_thang.get(k, 1))),
                                        float(thang[k].get("hien_thi_thang") or 0), k))
        cu_m = cu_vung.get(v) if isinstance(cu_vung.get(v), dict) else {}
        chu_cu = str(cu_m.get("chu") or "")
        if (chu_cu and chu_cu != tot and song.get(chu_cu, True)
                and int((tk[v].get(chu_cu) or {}).get("thang") or 0) >= int(thang[tot]["thang"])):
            tot = chu_cu
        ra[v] = {"chu": tot, "nguon": "tu_dong", "chia_se": list(cu_m.get("chia_se") or []),
                 "nhuong": bool(cu_m.get("nhuong")), "chan": bool(cu_m.get("chan")),
                 "thang": {k: int(o["thang"]) for k, o in sorted(thang.items())},
                 "thi_truong": round(float(thi_truong.get(v) or 0)),
                 "ly_do": "nhiều video THẮNG nhất trong vùng ({0} video, {1:,.0f} hiển thị)".format(
                     int(thang[tot]["thang"]), float(thang[tot].get("hien_thi_thang") or 0)).replace(",", ".")}
        so_vung[tot] = so_vung.get(tot, 0) + 1
    # 2) vùng NÓNG chưa ai thắng: giao kênh hợp tệp nhất còn được phát, vùng lớn trước.
    nong = sorted((v for v, x in thi_truong.items() if v not in ra and v not in ("", KHAC)
                   and float(x or 0) >= THI_TRUONG_TOI_THIEU), key=lambda v: (-float(thi_truong[v]), v))
    con_song = sorted(k for k, s in song.items() if s)
    for v in nong:
        if not con_song:
            break
        cu_m = cu_vung.get(v) if isinstance(cu_vung.get(v), dict) else {}
        chu_cu = str(cu_m.get("chu") or "")
        if chu_cu and song.get(chu_cu):
            tot = chu_cu
            ly = "giữ chủ cũ (vùng nóng chưa ai thắng)"
        elif hop_ai.get(v) in con_song:
            tot = str(hop_ai[v])
            ly = "vùng nóng chưa ai thắng — AI đọc tệp khán giả: hợp {0} nhất".format(tot)
        else:
            diem = {k: _diem_hop(k, v, tk, tep_rieng, lenh, so_vung) for k in con_song}
            tot = max(con_song, key=lambda k: (diem[k], -so_vung.get(k, 0), k))
            lys = []
            if v in (tep_rieng.get(tot) or set()):
                lys.append("cụm riêng của tệp kênh")
            if ((tk.get(v) or {}).get(tot) or {}).get("n"):
                lys.append("kênh đã có video trong vùng")
            if v in (lenh.get(tot) or set()):
                lys.append("chiến trường đã lệnh")
            ly = "vùng nóng chưa ai thắng — kênh hợp tệp nhất còn được phát ({0})".format(
                ", ".join(lys) or "kênh đang giữ ít vùng nhất")
        ra[v] = {"chu": tot, "nguon": "tu_dong", "chia_se": list(cu_m.get("chia_se") or []),
                 "nhuong": bool(cu_m.get("nhuong")), "chan": bool(cu_m.get("chan")), "thang": {},
                 "thi_truong": round(float(thi_truong.get(v) or 0)), "ly_do": ly}
        so_vung[tot] = so_vung.get(tot, 0) + 1
    return ra


# ── thu số liệu (đọc đĩa) ───────────────────────────────────────────────────

def cac_kenh(goc: str) -> List[str]:
    """Kênh có nhóm (`kenh.yaml: nhom`), bỏ bản thử A/B `-vN`."""
    try:
        from . import nhom_kenh  # noqa: PLC0415
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        return [k for k in liet_ke_kenh(goc) if not _RE_BAN_THU.search(k) and nhom_kenh.nhom_cua_kenh(goc, k)]
    except Exception:  # noqa: BLE001
        return []


def _vung_ai(goc: str) -> Dict[str, str]:
    """`{link: vùng}` + `{mã video: vùng}` (tra được cả link viết khác dạng)."""
    du = _doc_json(os.path.join(goc, "workspace", "chien-truong", "vung-ai.json")) or {}
    v = du.get("video") if isinstance(du, dict) else None
    ra: Dict[str, str] = {}
    for k, x in (v.items() if isinstance(v, dict) else []):
        ra[str(k)] = str(x)
        ma = _khoa_link(k)
        if ma:
            ra.setdefault(ma, str(x))
    return ra


def _khoa_link(link: Any) -> str:
    try:
        from .doi_thu_kenh import ma_video  # noqa: PLC0415

        return str(ma_video(str(link or "")) or "")
    except Exception:  # noqa: BLE001
        return ""


def vung_cua_nhan(nhan: str, link: str, vung_ai: Dict[str, str]) -> str:
    """Vùng = nhãn cụm (khác "khac"/rỗng), không thì vùng AI theo link (khoá link đầy đủ hoặc theo mã video)."""
    nhan = str(nhan or "").strip()
    if nhan and nhan != KHAC:
        return nhan
    if not link:
        return ""
    v = vung_ai.get(link) or vung_ai.get(_khoa_link(link))
    return "" if not v or v in ("ngoai-ngach", KHAC) else str(v)


def thong_ke(goc: str, kenh_ds: Sequence[str]) -> Tuple[Dict[str, Dict[str, Dict[str, Any]]], Dict[str, bool],
                                                        Dict[str, Set[str]]]:
    """`(tk, song, tep_rieng)` — xem `chon_chu`. Video của ta: `cong_thuc_v7.video_cua_kenh` (nhãn thước chung);
    vùng của video = nhãn cụm của ván tự học (đúng nhãn đã dùng lúc chọn), "khac" → vùng AI theo LINK NGUỒN, không
    có ván → nhãn theo nghĩa (`cum_y_nghia`) → từ khoá."""
    from . import cong_thuc_v7 as v7  # noqa: PLC0415
    from . import ho_so_video, tu_hoc  # noqa: PLC0415
    from .chien_luoc import ket_qua  # noqa: PLC0415

    vung_ai = _vung_ai(goc)
    mac_dinh = set((v7.CAU_HINH_MAC_DINH.get("cum") or {}).keys())
    tk: Dict[str, Dict[str, Dict[str, Any]]] = {}
    song: Dict[str, bool] = {}
    tep_rieng: Dict[str, Set[str]] = {}
    for k in kenh_ds:
        try:
            ch, _ = v7.nap_cau_hinh(goc, k, ghi_neu_thieu=False)
            vs = v7.video_cua_kenh(goc, k, ch)
        except Exception:  # noqa: BLE001
            continue
        tep_rieng[k] = {c for c in (ch.get("cum") or {}) if c.startswith("tep-") or c not in mac_dinh}
        van = tu_hoc.doc_van(goc, k)
        hs = ket_qua.ho_so_theo_goi(goc, k)
        nguon = ho_so_video.nguon_cua_goi(goc, k)
        theo_vid: Dict[str, Tuple[str, str]] = {}
        for ma_goi, h in hs.items():
            vid = str(h.get("video_id") or "")
            if vid:
                theo_vid[vid] = (str(((van.get(ma_goi) or {}).get("nuoc") or {}).get("cum") or ""),
                                 str((nguon.get(ma_goi) or {}).get("link") or ""))
        try:
            from . import cum_y_nghia  # noqa: PLC0415

            bo = cum_y_nghia.BoNho(goc, k, ch=ch)
        except Exception:  # noqa: BLE001
            bo = None
        moi_nhat: List[float] = []
        co_thang = False
        for vm in vs:
            nhan, link = theo_vid.get(vm.ma, ("", ""))
            if not nhan and bo is not None and vm.tieu_de:
                try:
                    nhan = bo.tra(vm.tieu_de)
                except Exception:  # noqa: BLE001
                    nhan = ""
            if not nhan and vm.cum:
                nhan = vm.cum[0]
            v = vung_cua_nhan(nhan, link, vung_ai)
            ket = getattr(vm, "ket", None)
            gia = getattr(ket, "gia_tri", None) if ket is not None else None
            if gia is None and getattr(vm, "chuoi", None) is not None and getattr(vm.chuoi, "diem", None):
                gia = max((d.hien_thi or 0.0) for d in vm.chuoi.diem)
            if (vm.tuoi_gio or 0) >= 72 and gia is not None:
                moi_nhat.append(float(gia))
            if vm.nhan_thang == "thang":
                co_thang = True
            if not v:
                continue
            o = tk.setdefault(v, {}).setdefault(k, {"thang": 0, "n": 0, "da_phan": 0, "hien_thi_thang": 0.0,
                                                     "_pv": []})
            o["n"] += 1
            if vm.da_phan:
                o["da_phan"] += 1
                if vm.phan_vi is not None:
                    o["_pv"].append(float(vm.phan_vi))
            if vm.nhan_thang == "thang":
                o["thang"] += 1
                o["hien_thi_thang"] += float(gia or 0.0)
        song[k] = co_thang or (len(moi_nhat) >= 1 and statistics.median(moi_nhat) >= SAN_DUOC_PHAT) or not moi_nhat
        try:  # cờ "kênh không được phát" (`core/kenh_khong_phat.py`, 12/10/2026): không giao vùng cho kênh đang bị dừng
            from . import kenh_khong_phat  # noqa: PLC0415

            if kenh_khong_phat.dang_dung(goc, k)[0]:
                song[k] = False
        except Exception:  # noqa: BLE001
            pass
    for v, theo_k in tk.items():
        for o in theo_k.values():
            pv = o.pop("_pv", [])
            o["pv_tb"] = round(sum(pv) / len(pv), 1) if pv else None
    return tk, song, tep_rieng


def thi_truong_moi_nhat(goc: str) -> Dict[str, float]:
    """`{vùng: view đối thủ 28 ngày}` từ ảnh chụp mới nhất `lich-su.jsonl` của chiến trường ({} nếu chưa có)."""
    try:
        with io.open(os.path.join(goc, TEP_LICH_SU), encoding="utf-8") as tep:
            dong = [x for x in tep.read().splitlines() if x.strip()]
        du = json.loads(dong[-1]) if dong else {}
    except (OSError, ValueError, IndexError):
        return {}
    v = du.get("vung") if isinstance(du, dict) else None
    if isinstance(v, dict):
        return {str(k): float((x or {}).get("dich") or 0) for k, x in v.items()}
    if isinstance(v, list):
        return {str(x.get("ma")): float(x.get("dich") or 0) for x in v if isinstance(x, dict) and x.get("ma")}
    return {}


def _lenh(goc: str) -> Dict[str, Set[str]]:
    du = _doc_json(os.path.join(goc, TEP_TAN_CONG)) or {}
    return {str(k): {str(v.get("ma")) for v in (ds or []) if isinstance(v, dict) and v.get("ma")}
            for k, ds in ((du.get("kenh") or {}) if isinstance(du, dict) else {}).items()}


#: Câu trả lời AI "vùng → kênh hợp tệp" được dùng lại ngần này ngày (bản đồ sinh lại mỗi ngày).
NGAY_GIU_HOP_AI = 7


def _mo_ta_kenh(goc: str, kenh: str) -> str:
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        y = doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}
        ch, _ = v7.nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    except Exception:  # noqa: BLE001
        return kenh
    tep = str(ch.get("tep") or y.get("tep") or "").strip()
    gia = str(y.get("cho_phep_tep_gia") or "").strip().lower() in ("true", "1", "yes")
    return "{0}: tệp khán giả “{1}”{2}".format(kenh, tep.replace("-", " ") or "?", " (người cao tuổi)" if gia else "")


def _ten_vung(goc: str, kenh_ds: Sequence[str]) -> Dict[str, str]:
    ra: Dict[str, str] = {}
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        for k in kenh_ds:
            ch, _ = v7.nap_cau_hinh(goc, k, ghi_neu_thieu=False)
            for ma, c in (ch.get("cum") or {}).items():
                ra.setdefault(ma, str((c or {}).get("ten") or ma))
    except Exception:  # noqa: BLE001
        pass
    du = _doc_json(os.path.join(goc, "workspace", "chien-truong", "vung-ai.json")) or {}
    for ma, ten in ((du.get("vung_moi") or {}) if isinstance(du, dict) else {}).items():
        ra.setdefault(str(ma), str(ten))
    return ra


def de_bai_hop_tep(vung: Dict[str, Tuple[str, float]], kenh_mo_ta: Sequence[str]) -> str:
    ds_v = "\n".join("- {0}: {1} (view đối thủ 28 ngày ≈ {2:,.0f})".format(ma, ten, tt).replace(",", ".")
                     for ma, (ten, tt) in vung.items())
    return ("Đây là các kênh YouTube ANH EM cùng một ngách — mỗi kênh đánh MỘT tệp khán giả riêng:\n{0}\n\n"
            "Các VÙNG ĐỀ TÀI dưới đây đang có thị trường lớn nhưng CHƯA kênh nào của ta thắng:\n{1}\n\n"
            "Giao MỖI vùng cho ĐÚNG MỘT kênh mà người xem của kênh đó sẽ coi đề tài này là CỦA MÌNH (đọc NGHĨA của "
            "tệp khán giả, không khớp chữ). Hai vùng có thể cùng một kênh nếu thật sự hợp. Chỉ dùng mã kênh trong "
            "danh sách. Trả về DUY NHẤT một object JSON: {{\"<mã vùng>\": \"<mã kênh>\", ...}}").format(
        "\n".join("- " + m for m in kenh_mo_ta), ds_v)


def hoi_ai_hop_tep(goc: str, vung: Dict[str, Tuple[str, float]], kenh_ds: Sequence[str],
                   goi: Optional[Any]) -> Dict[str, str]:
    """AI đọc NGHĨA tệp khán giả → `{vùng: kênh}` cho các vùng nóng chưa chủ. `goi` None / lỗi / mã lạ → {}."""
    if goi is None or not vung or not kenh_ds:
        return {}
    try:
        from .goi_van_ban import loc_json  # noqa: PLC0415

        tho = goi(de_bai_hop_tep(vung, [_mo_ta_kenh(goc, k) for k in kenh_ds]), mo_hinh="claude-sonnet-5",
                  khoa="chu-quyen-vung-{0}".format(_dt.date.today().isoformat()), toi_da_token=2000)
        du = loc_json(tho)
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(du, dict):
        return {}
    return {str(v): str(k) for v, k in du.items() if str(v) in vung and str(k) in kenh_ds}


def de_xuat(goc: str, kenh_ds: Optional[Sequence[str]] = None, *, thi_truong: Optional[Dict[str, float]] = None,
            bay_gio: Optional[_dt.datetime] = None, goi: Optional[Any] = None) -> Dict[str, Any]:
    """Bản đồ ĐỀ XUẤT (không ghi): gộp bản cũ (giữ dòng tay), thống kê thắng theo vùng, thị trường, lệnh tấn công;
    `goi` (hàm gọi AI qua ví) → vùng nóng chưa chủ được AI giao theo NGHĨA tệp khán giả (nhớ `NGAY_GIU_HOP_AI` ngày)."""
    kenh_ds = list(kenh_ds) if kenh_ds is not None else cac_kenh(goc)
    tk, song, tep_rieng = thong_ke(goc, kenh_ds)
    tt = thi_truong if thi_truong is not None else thi_truong_moi_nhat(goc)
    cu = doc(goc)
    lenh = _lenh(goc)
    hom = (bay_gio or _dt.datetime.now()).date()
    nho_ai = {v: x for v, x in ((cu.get("hop_ai") or {}) if isinstance(cu.get("hop_ai"), dict) else {}).items()
              if isinstance(x, dict) and x.get("kenh") and str(x.get("ngay") or "") >=
              (hom - _dt.timedelta(days=NGAY_GIU_HOP_AI)).isoformat()}
    hop = {v: str(x["kenh"]) for v, x in nho_ai.items()}
    vung = chon_chu(tk, song, tt, tep_rieng, cu=cu, lenh=lenh, hop_ai=hop)
    if goi is not None:
        ten = _ten_vung(goc, kenh_ds)
        can = {v: (ten.get(v, v), float(tt.get(v) or 0)) for v, m in vung.items()
               if m.get("nguon") == "tu_dong" and not m.get("thang") and v not in hop}
        moi = hoi_ai_hop_tep(goc, can, [k for k in kenh_ds if song.get(k)], goi)
        if moi:
            nho_ai.update({v: {"kenh": k, "ngay": hom.isoformat()} for v, k in moi.items()})
            hop.update(moi)
            cu_khong_chu = dict(cu, vung={v: m for v, m in (cu.get("vung") or {}).items()
                                          if not (isinstance(m, dict) and v in moi and m.get("nguon") != "tay")})
            vung = chon_chu(tk, song, tt, tep_rieng, cu=cu_khong_chu, lenh=lenh, hop_ai=hop)
    return {"phien_ban": 1, "luc": (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d %H:%M"),
            "he_so_phat": float(cu.get("he_so_phat") or HE_SO_PHAT), "vung": vung, "hop_ai": nho_ai,
            "kenh_duoc_phat": {k: bool(song.get(k)) for k in kenh_ds},
            "cach_doc": "chu = kênh chủ vùng; kênh anh em khác chọn nguồn thuộc vùng này bị nhân he_so_phat (chan: "
                        "true → bỏ) trừ khi có tên trong chia_se, chủ nhuong, hoặc chủ đã phủ quyết đúng nguồn đó. "
                        "Sửa tay một dòng thì đặt nguon: \"tay\" để lần sinh lại giữ nguyên."}


def cap_nhat(goc: str, kenh_ds: Optional[Sequence[str]] = None, *,
             thi_truong: Optional[Dict[str, float]] = None, dung_ai: bool = False) -> Dict[str, Any]:
    """Sinh lại + ghi bản đồ (giữ dòng sửa tay). Tắt bằng MYTOOL_CHIEN_TRUONG_GHI=0 (chỉ trả, không ghi).
    `dung_ai` → hỏi AI (qua van ví, `cum_y_nghia.goi_vi`) kênh hợp tệp cho vùng nóng chưa chủ."""
    goi = None
    if dung_ai:
        try:
            from . import cum_y_nghia  # noqa: PLC0415

            goi = cum_y_nghia.goi_vi(goc)
        except Exception:  # noqa: BLE001
            goi = None
    du = de_xuat(goc, kenh_ds, thi_truong=thi_truong, goi=goi)
    if os.environ.get("MYTOOL_CHIEN_TRUONG_GHI", "1") != "0":
        ghi(goc, du)
    return du


#: Bản đồ sinh lại tối đa một lần mỗi ngần này giờ (trang trực quan gọi chiến trường mỗi 10 phút).
GIO_SINH_LAI = 20.0


def cap_nhat_neu_cu(goc: str, kenh_ds: Optional[Sequence[str]] = None, *,
                    thi_truong: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Như `cap_nhat` (có hỏi AI hợp tệp) nhưng chỉ khi bản đồ chưa có / cũ hơn `GIO_SINH_LAI` giờ; còn lại đọc bản đã
    ghi. Ghi tắt (MYTOOL_CHIEN_TRUONG_GHI=0) → chỉ đọc. Hỏng → {} (không chặn chiến trường)."""
    try:
        if os.environ.get("MYTOOL_CHIEN_TRUONG_GHI", "1") == "0":
            return doc(goc)
        p = duong(goc)
        import time as _time  # noqa: PLC0415

        if os.path.isfile(p) and _time.time() - os.path.getmtime(p) < GIO_SINH_LAI * 3600 and doc(goc):
            return doc(goc)
        return cap_nhat(goc, kenh_ds, thi_truong=thi_truong, dung_ai=True)
    except Exception:  # noqa: BLE001
        return {}


def duoc_danh(ban_do: Dict[str, Any], kenh: str, vung: str) -> Tuple[bool, bool]:
    """`(được đánh vùng này?, là chủ vùng?)` theo bản đồ — vùng không có chủ / bản đồ trống → (True, False)."""
    m = chu_cua(ban_do, vung)
    chu = str(m.get("chu") or "")
    if not chu:
        return True, False
    if chu == kenh:
        return True, True
    return bool(m.get("nhuong") or kenh in (m.get("chia_se") or [])), False


# ── áp khi chọn nguồn ────────────────────────────────────────────────────────

def _chu_da_phu_quyet(goc: str, chu: str, ma: str, nho: Dict[str, Dict[str, Any]]) -> bool:
    if chu not in nho:
        du = _doc_json(os.path.join(goc, "CHANNEL", chu, "nghien-cuu", "bien-tap", "nho-cham.json"))
        nho[chu] = du if isinstance(du, dict) else {}
    return str((nho[chu].get(ma) or {}).get("hang") or "").upper() == "TE"


def chu_cua(ban_do: Dict[str, Any], vung: str) -> Dict[str, Any]:
    m = (ban_do.get("vung") or {}).get(vung)
    return m if isinstance(m, dict) else {}


def ap_he_so(nc: Any, bang: Dict[str, List[Dict[str, Any]]]) -> Tuple[int, int]:
    """Áp bản đồ lên các bảng công thức (sửa tại chỗ, xếp lại). Trả `(số dòng bị phạt, số dòng bị bỏ)`."""
    ban_do = doc(nc.goc)
    if not ban_do.get("vung"):
        return 0, 0
    try:
        from . import nhom_kenh  # noqa: PLC0415

        anh_em = set(nhom_kenh.thanh_vien(nc.goc, nc.ma_kenh) or []) - {nc.ma_kenh}
    except Exception:  # noqa: BLE001
        anh_em = set()
    if not anh_em:
        return 0, 0
    from . import tu_hoc  # noqa: PLC0415

    vung_ai = _vung_ai(nc.goc)
    he = float(ban_do.get("he_so_phat") or HE_SO_PHAT)
    nho: Dict[str, Dict[str, Any]] = {}
    phat = bo = 0
    for ten in list(bang):
        moi: List[Dict[str, Any]] = []
        doi = False
        for d in bang[ten]:
            v = vung_cua_nhan(tu_hoc.nhan_cum(d, nc.cum_cua), str(d.get("link") or ""), vung_ai)
            m = chu_cua(ban_do, v) if v else {}
            chu = str(m.get("chu") or "")
            if not chu or chu == nc.ma_kenh or chu not in anh_em:
                if chu == nc.ma_kenh:
                    d.setdefault("tin_hieu", {})["vung_chu"] = v
                moi.append(d)
                continue
            if nc.ma_kenh in (m.get("chia_se") or []) or m.get("nhuong"):
                moi.append(d)
                continue
            if _chu_da_phu_quyet(nc.goc, chu, str(d.get("ma") or ""), nho):
                d["ly_do"] = list(d.get("ly_do") or []) + [
                    "vùng “{0}” của {1}, nhưng {1} đã phủ quyết nguồn này — kênh này được nhận".format(v, chu)]
                moi.append(d)
                continue
            if m.get("chan") and not d.get("ep_chon"):
                bo += 1
                doi = True
                continue
            try:
                d["diem"] = round(float(d.get("diem") or 0) * he, 2)
            except (TypeError, ValueError):
                moi.append(d)
                continue
            d["he_so_chu_quyen"] = he
            d.setdefault("tin_hieu", {})["chu_quyen"] = {"vung": v, "chu": chu}
            d["ly_do"] = list(d.get("ly_do") or []) + [
                "chủ quyền vùng: “{0}” thuộc {1} → ×{2:g} (chống ăn thịt nhau)".format(v, chu, he)]
            phat += 1
            doi = True
            moi.append(d)
        if doi:
            moi.sort(key=lambda d: -float(d.get("diem") or 0) if isinstance(d.get("diem"), (int, float)) else 0)
        bang[ten] = moi
    if phat or bo:
        nc.ghi("  chủ quyền vùng: {0} ứng viên thuộc vùng của kênh anh em ×{1:g}{2}.".format(
            phat, he, ", bỏ {0} (vùng chặn)".format(bo) if bo else ""))
    return phat, bo


def dong_bang(du: Dict[str, Any]) -> Iterable[str]:
    """Dòng in người đọc của bản đồ (vùng lớn trước)."""
    vung = du.get("vung") or {}
    for v, m in sorted(vung.items(), key=lambda kv: (-float(kv[1].get("thi_truong") or 0), kv[0])):
        yield "{0:<20} → {1:<11} [{2}] {3}{4}".format(
            v, m.get("chu") or "—", m.get("nguon"), m.get("ly_do") or "",
            " · thị trường {0:,.0f}".format(float(m.get("thi_truong") or 0)).replace(",", ".")
            if m.get("thi_truong") else "")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.chu_quyen_vung")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p.add_argument("--ghi", action="store_true", help="ghi bản đồ (giữ dòng sửa tay)")
    a = p.parse_args(argv)
    du = cap_nhat(a.goc) if a.ghi else de_xuat(a.goc)
    print("Kênh được phát:", ", ".join("{0}{1}".format(k, "" if s else " (KHÔNG)")
                                      for k, s in du["kenh_duoc_phat"].items()))
    for dong in dong_bang(du):
        print(dong)
    return 0


if __name__ == "__main__":
    sys.exit(main())
