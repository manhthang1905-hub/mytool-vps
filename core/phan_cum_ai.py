"""Phân CỤM chủ đề theo Ý NGHĨA bằng AI — thay từ khoá cho `cong_thuc_v7._cum_cua`.

Chủ dự án, 29/09/2026: *"Lọc theo từ khoá là SAI — phải theo Ý NGHĨA."* Đúng ca đo được:
"持たない" trong cụm tiền bắt 「頭のいい人が他人に興味を持たない…」; "脳" kéo mọi 【脳科学】 vào
một cụm; 「精神年齢」 ăn điểm ké cụm IQ. Từ khoá không đọc được câu.

═══ HAI NỬA, TÁCH HẲN ═══

* `phan_loai(...)` — GỌI AI (qua `goi_chat` của vòng tự chạy), theo lô, chỉ cho tiêu đề CHƯA
  có trong bộ nhớ. Chỉ chạy ở chỗ có ví: `tu_chay._chon_nguon` khi `che_do == "that"`.
* `tra_cum(td, ch)` — CHỈ ĐỌC bộ nhớ trên đĩa, không mạng. `cong_thuc_v7._cum_cua` hỏi hàm này
  trước; không có câu trả lời (chưa phân, AI lỗi) thì mới lùi về từ khoá.

═══ BỘ NHỚ ═══

`<kho nghiên cứu của nhóm>/phan-cum-ai/<khoá bộ cụm>.json` — `{khoá tiêu đề: {"c": [mã cụm],
"t": tiêu đề rút gọn, "ngay": ngày}}`. Khoá bộ cụm băm từ (mã, tên) các cụm của cấu hình V7:
kênh đổi danh sách cụm (vd tách 精神年齢) thì dùng tệp mới, không đọc nhầm nhãn cũ. Khoá tiêu đề
băm từ tiêu đề đã chuẩn hoá — cùng tiêu đề ở kênh nào cũng không hỏi lại.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["PHIEN_BAN", "THU_MUC", "khoa_bo_cum", "khoa_tieu_de", "nap", "tra_cum", "phan_loai",
           "de_bai"]

PHIEN_BAN = 1
THU_MUC = "phan-cum-ai"
SO_MOI_LO = 40
SO_LUONG_SONG_SONG = 4
TOI_DA_CUM_MOT_TIEU_DE = 2
#: Lô hỏng → chẻ đôi + lùi mô hình (xem `phan_loai.mot_lo_cuu`) tới khi cô lập được đúng tiêu đề
#: làm hỏng lô: 40 → 20 → 10 → 5 → 3 → 2 → 1 là 6 tầng, thêm một tầng thử mô hình khác cho lô 1.
BAC_CHE_TOI_DA = 7
#: Cả một lượt `phan_loai` quá ngần này lượt gọi hỏng thì thôi chẻ (cổng sập ≠ lô độc).
TRAN_GOI_HONG = 24
#: Thang mô hình lùi khi lô hỏng (mô hình của kênh đứng đầu).
THANG_LUI = ("claude-sonnet-5", "claude-opus-5", "claude-fable-5")

#: `{khoá bộ cụm: {khoá tiêu đề: [mã cụm]}}` đã nạp trong tiến trình này — xem `nap`.
_BANG: Dict[str, Dict[str, List[str]]] = {}
#: `{khoá bộ cụm: (đường tệp, mtime lúc nạp)}` — nạp lại khi tệp trên đĩa đổi.
_NGUON: Dict[str, Tuple[str, float]] = {}
_KHOA = threading.Lock()
_NHO_KHOA_BO: Dict[int, Tuple[Any, str]] = {}


def khoa_bo_cum(ch: Dict) -> str:
    cum = ch.get("cum") or {}
    nho = _NHO_KHOA_BO.get(id(cum))
    if nho is not None and nho[0] is cum:
        return nho[1]
    ds = sorted((ma, str((c or {}).get("ten") or "")) for ma, c in cum.items())
    khoa = hashlib.sha1(json.dumps([PHIEN_BAN, ds], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    _NHO_KHOA_BO[id(cum)] = (cum, khoa)
    return khoa


def _chuan(td: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(td or ""))).strip()


def khoa_tieu_de(td: str) -> str:
    return hashlib.sha1(_chuan(td).encode("utf-8")).hexdigest()[:20]


def _duong(goc: str, kenh: str, ch: Dict) -> str:
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    return os.path.join(ncc.thu_muc(goc, kenh), THU_MUC, khoa_bo_cum(ch) + ".json")


def nap(goc: str, kenh: str, ch: Dict) -> int:
    """Nạp bộ nhớ phân cụm của bộ cụm `ch` vào tiến trình (đọc đĩa, không mạng). Trả số mục."""
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    try:
        duong = _duong(goc, kenh, ch)
    except Exception:  # noqa: BLE001
        return 0
    khoa = khoa_bo_cum(ch)
    try:
        mtime = os.path.getmtime(duong)
    except OSError:
        return len(_BANG.get(khoa, {}))
    with _KHOA:
        if _NGUON.get(khoa) == (duong, mtime):
            return len(_BANG.get(khoa, {}))
        du = ncc.doc_json(duong, {})
        bang: Dict[str, List[str]] = dict(_BANG.get(khoa, {}))
        for k, m in (du or {}).items():
            if isinstance(m, dict) and isinstance(m.get("c"), list):
                bang[k] = [str(x) for x in m["c"]]
        _BANG[khoa] = bang
        _NGUON[khoa] = (duong, mtime)
        return len(bang)


def tra_cum(td: str, ch: Dict) -> Optional[List[str]]:
    """Cụm AI đã gán cho tiêu đề `td` (theo bộ cụm `ch`) — `None` nếu chưa phân (→ từ khoá)."""
    bang = _BANG.get(khoa_bo_cum(ch))
    if not bang:
        return None
    c = bang.get(khoa_tieu_de(td))
    if c is None:
        return None
    cum = ch.get("cum") or {}
    return [x for x in c if x in cum]


#: Ba mảnh đề bài của ngách MẶC ĐỊNH (tâm lý Nhật) — dùng khi kênh không có hồ sơ ngách. Nhóm
#: tam-ly-nhat khai đúng ba chuỗi này trong ngach.yaml (`mo_ta_phan_cum`, `nhan_the_loai_mau`,
#: `vi_du_phan_cum`) → đề bài trùng từng ký tự (tests/test_ngach_tam_ly_khop_ma.py).
MO_TA_MAC_DINH = "tiếng Nhật (ngách tâm lý)"
NHAN_MAU_MAC_DINH = "【心理学】【脳科学】【雑学】"
VI_DU_MAC_DINH = "(「他人に興味を持たない」 không phải chuyện tiền; 「精神年齢」 không phải IQ trừ khi có cụm riêng)"


def de_bai(ch: Dict, ngach: Any = None) -> str:
    """Đề bài phân cụm theo nghĩa. `ngach` = `HoSoNgach` của kênh (30/09/2026, B8): có hồ sơ thì
    câu mở / nhãn ngoặc mẫu / câu ví dụ lấy từ đó (thiếu mảnh nào thì viết trung tính theo
    `mo_ta_ngach`, KHÔNG rơi về chữ Nhật tâm lý); không có hồ sơ → ba mảnh mặc định như cũ."""
    if ngach is not None and getattr(ngach, "co", lambda: False)():
        mo_ta = ngach.mo_ta_phan_cum or ("({0})".format(ngach.mo_ta_ngach) if ngach.mo_ta_ngach else "")
        nhan, vi_du = ngach.nhan_the_loai_mau, ngach.vi_du_phan_cum
    else:
        mo_ta, nhan, vi_du = MO_TA_MAC_DINH, NHAN_MAU_MAC_DINH, VI_DU_MAC_DINH
    cum = "\n".join("- {0}: {1} (vd: {2})".format(ma, c.get("ten", ""), "、".join((c.get("tu") or [])[:6]))
                    for ma, c in (ch.get("cum") or {}).items())
    return (
        "Bạn phân loại tiêu đề video YouTube {mo_ta}vào CỤM CHỦ ĐỀ theo Ý NGHĨA, "
        "không theo từ khoá. Đọc cả câu: tiêu đề thật sự hứa với người xem điều gì, nói về kiểu "
        "người nào. Bỏ qua nhãn thể loại trong ngoặc{nhan}.\n\n"
        "CỤM (mã: tên — ví dụ chữ chỉ để hiểu nghĩa, KHÔNG phải luật khớp chữ):\n{cum}\n\n"
        "Quy tắc:\n"
        "- Mỗi tiêu đề 0, 1 hoặc tối đa {toi_da} mã cụm, cụm chính trước. Không cụm nào hợp → [].\n"
        "- Chỉ gán khi ĐỀ TÀI CHÍNH thuộc cụm, không gán vì một chữ lướt qua{vi_du}.\n"
        "- Chỉ dùng mã có trong danh sách.\n\n"
        "Trả về DUY NHẤT một object JSON: {{\"1\": [\"ma\"], \"2\": [], ...}}, đủ mọi số thứ tự."
    ).format(mo_ta=(mo_ta + " ") if mo_ta else "", nhan=(" như " + nhan) if nhan else "",
             cum=cum, toi_da=TOI_DA_CUM_MOT_TIEU_DE, vi_du=(" " + vi_du) if vi_du else "")


def _mot_lo(goi_chat: Callable[..., str], ch: Dict, lo: Sequence[Tuple[str, str]], mo_hinh: str,
            khoa: str, bac: int = 0, de: str = "") -> Dict[int, List[str]]:
    chu = "\n".join("{0}. {1}{2}".format(i + 1, td, ("  〔mô tả: " + mt[:100] + "〕") if mt else "")
                    for i, (td, mt) in enumerate(lo))
    from .goi_van_ban import loc_json  # noqa: PLC0415

    # Trần cũ 40×lô+400 (= 2.000 cho lô 40) — cổng trả RỖNG khi trần thấp (xem goi_van_ban.SAN_MAX_TOKENS).
    tho = goi_chat((de or de_bai(ch)) + "\n\nTIÊU ĐỀ:\n" + chu, mo_hinh=mo_hinh, khoa=khoa,
                   toi_da_token=max(4096, 80 * len(lo) + 1000) * (1 + bac))
    du = loc_json(tho)
    if not isinstance(du, (dict, list)):
        raise ValueError("câu trả lời phân cụm không phải JSON")
    if isinstance(du, list):
        du = {str(i + 1): m for i, m in enumerate(du)}
    ra: Dict[int, List[str]] = {}
    cum = ch.get("cum") or {}
    for k, v in (du or {}).items():
        try:
            i = int(str(k).strip()) - 1
        except ValueError:
            continue
        if not 0 <= i < len(lo):
            continue
        ds = v if isinstance(v, list) else ([v] if isinstance(v, str) else [])
        ra[i] = [str(x) for x in ds if str(x) in cum][:TOI_DA_CUM_MOT_TIEU_DE]
    return ra


def phan_loai(goc: str, kenh: str, ch: Dict, muc: Sequence[Tuple[str, str]],
              goi_chat: Callable[..., str], *, mo_hinh: str = "claude-sonnet-5",
              toi_da: int = 1200, log: Optional[Callable[[str], None]] = None) -> int:
    """Gọi AI phân cụm cho các `(tiêu đề, mô tả)` CHƯA có trong bộ nhớ, theo lô `SO_MOI_LO`,
    `SO_LUONG_SONG_SONG` lô cùng lúc, tối đa `toi_da` tiêu đề một lượt. Ghi bộ nhớ sau MỖI lô
    (lỗi giữa chừng không mất phần đã trả tiền). Lô hỏng vì nội dung (trả rỗng / JSON hỏng) → chẻ đôi +
    lùi mô hình + nới trần ngay trong lượt (`mot_lo_cuu`); chỉ tiêu đề vẫn hỏng mới để lượt sau. Trả số mục mới."""
    from . import nghien_cuu_chung as ncc  # noqa: PLC0415

    nap(goc, kenh, ch)
    khoa_bo = khoa_bo_cum(ch)
    da = _BANG.get(khoa_bo, {})
    # 30/09/2026, B8: đề bài theo hồ sơ ngách của kênh, dựng MỘT lần cho cả lượt.
    try:
        from .ho_so_ngach import doc_ngach  # noqa: PLC0415

        de = de_bai(ch, doc_ngach(goc, kenh))
    except Exception:  # noqa: BLE001
        de = de_bai(ch)
    can: List[Tuple[str, str]] = []
    thay: set = set()
    for td, mt in muc:
        k = khoa_tieu_de(td)
        if not _chuan(td) or k in da or k in thay:
            continue
        thay.add(k)
        can.append((_chuan(td), str(mt or "").strip()))
        if len(can) >= toi_da:
            break
    if not can:
        return 0
    duong = _duong(goc, kenh, ch)
    lo_tat_ca = [can[i:i + SO_MOI_LO] for i in range(0, len(can), SO_MOI_LO)]
    if log is not None:
        log("  AI phân cụm theo nghĩa: {0} tiêu đề mới, {1} lô ({2} song song)…".format(
            len(can), len(lo_tat_ca), SO_LUONG_SONG_SONG))
    hom_nay = _dt.date.today().isoformat()
    dem = [0, 0, 0]  # nhãn mới · lô bỏ hẳn · lượt gọi hỏng

    thang = [mo_hinh] + [m for m in THANG_LUI if m != mo_hinh]

    def ghi_nho(lo: Sequence[Tuple[str, str]], ket: Dict[int, List[str]]) -> None:
        moi = {khoa_tieu_de(lo[i][0]): {"c": c, "t": lo[i][0][:60], "ngay": hom_nay}
               for i, c in ket.items()}
        if moi:
            ncc.ghi_json_gop(duong, moi)
            with _KHOA:
                _BANG.setdefault(khoa_bo, {}).update({k: v["c"] for k, v in moi.items()})
                dem[0] += len(moi)

    def mot_lo_cuu(lo: Sequence[Tuple[str, str]], bac: int, nhan: str) -> None:
        """Gọi một lô; hỏng (vd "Máy chủ trả về nội dung rỗng" — 5/30 lô đêm 29/09 23:07,
        luôn cùng lô dù đã đổi khoá 4 lần) thì CHẺ ĐÔI + lùi mô hình + nới trần, tới lô 1 tiêu
        đề. Một tiêu đề độc làm rỗng cả lô 40 thì chỉ còn chính nó hỏng, không mất 39 cái kia,
        và không để lượt sau (lượt sau hỏi lại đúng lô ấy, rỗng lại)."""
        mh = thang[min(bac, len(thang) - 1)]
        try:
            ket = _mot_lo(goi_chat, ch, lo, mh, "phan-cum-{0}-{1}-b{2}".format(
                khoa_bo, khoa_tieu_de("|".join(t for t, _ in lo)), bac), bac=min(bac, 3), de=de)
        except Exception as loi:  # noqa: BLE001 — một lô hỏng không giết cả lượt
            with _KHOA:
                dem[2] += 1
                qua_tran = dem[2] > TRAN_GOI_HONG
            # Chỉ chẻ khi hỏng vì NỘI DUNG (trả rỗng / JSON hỏng — `TraRong` là ValueError). Mạng sập,
            # hết tiền… thì chẻ chỉ nhân số lượt gọi hỏng; và cả lượt quá `TRAN_GOI_HONG` lượt hỏng thì thôi.
            che_duoc = isinstance(loi, ValueError) and not qua_tran
            if che_duoc and len(lo) > 1 and bac < BAC_CHE_TOI_DA:
                if log is not None:
                    log("  lô phân cụm {0} ({1} tiêu đề, {2}) hỏng: {3} — chẻ đôi, thử {4}.".format(
                        nhan, len(lo), mh, str(loi)[:70], thang[min(bac + 1, len(thang) - 1)]))
                giua = len(lo) // 2
                mot_lo_cuu(lo[:giua], bac + 1, nhan + "a")
                mot_lo_cuu(lo[giua:], bac + 1, nhan + "b")
                return
            if che_duoc and bac < BAC_CHE_TOI_DA:
                # Lô đã nhỏ: thử thêm đúng một bậc mô hình khác trước khi bỏ.
                mot_lo_cuu(lo, bac + 1, nhan + "'")
                return
            dem[1] += 1
            if log is not None:
                log("  lô phân cụm {0} ({1} tiêu đề) vẫn hỏng sau khi chẻ/lùi mô hình: {2} — các tiêu đề "
                    "này dùng từ khoá: {3}".format(nhan, len(lo), str(loi)[:80],
                                                   " | ".join(t[:30] for t, _ in lo[:3])))
            return
        ghi_nho(lo, ket)

    def chay(so_lo: int) -> None:
        mot_lo_cuu(lo_tat_ca[so_lo], 0, str(so_lo + 1))

    with ThreadPoolExecutor(max_workers=SO_LUONG_SONG_SONG) as ex:
        list(ex.map(chay, range(len(lo_tat_ca))))
    if log is not None:
        log("  AI phân cụm xong: {0} tiêu đề có nhãn mới{1}.".format(
            dem[0], ", {0} lô hỏng".format(dem[1]) if dem[1] else ""))
    return dem[0]


def lam_nong(goc: str, kenh: str, ch: Dict, goi_chat: Callable[..., str],
             tieu_de_ung_vien: Sequence[str], *, mo_hinh: str = "claude-sonnet-5",
             toi_da: int = 1200, ngay_trang_chu: int = 28,
             log: Optional[Callable[[str], None]] = None) -> int:
    """Gom mọi tiêu đề mà việc CHỌN NGUỒN hôm nay cần cụm, rồi `phan_loai` phần chưa phân.

    Ưu tiên (hết `toi_da` thì phần sau để lượt sau): (1) video của chính kênh + kênh anh em
    (cụm đang thắng / thừa hưởng), (2) ứng viên đầu bảng của công thức, (3) trang chủ máy ảo
    `ngay_trang_chu` ngày gần nhất (xu hướng cụm), mới trước. Trả số tiêu đề mới được phân."""
    from . import cong_thuc_v7 as v7  # noqa: PLC0415 — cong_thuc_v7 nhập module này

    muc: List[Tuple[str, str]] = []
    try:
        from . import nhom_kenh  # noqa: PLC0415
        ds_kenh = nhom_kenh.thanh_vien(goc, kenh) or [kenh]
    except Exception:  # noqa: BLE001
        ds_kenh = [kenh]
    for k in ds_kenh:
        try:
            ch_k, _ = v7.nap_cau_hinh(goc, k, ghi_neu_thieu=False)
            muc += [(v.tieu_de, "") for v in v7.video_cua_kenh(goc, k, ch_k) if v.tieu_de]
        except Exception:  # noqa: BLE001
            continue
    muc += [(t, "") for t in tieu_de_ung_vien if t]
    moc = _dt.date.today()
    tc = []
    for r in v7._dong_trang_chu(goc, kenh):
        if str(r.get("Short") or "").strip() or str(r.get("Bị loại") or "").strip():
            continue
        try:
            tuoi = (moc - _dt.date.fromisoformat(str(r.get("Lúc quét") or "")[:10])).days
        except ValueError:
            continue
        if 0 <= tuoi < ngay_trang_chu and r.get("Tiêu đề"):
            tc.append((tuoi, str(r["Tiêu đề"])))
    tc.sort(key=lambda x: x[0])
    muc += [(t, "") for _tuoi, t in tc]
    return phan_loai(goc, kenh, ch, muc, goi_chat, mo_hinh=mo_hinh, toi_da=toi_da, log=log)
