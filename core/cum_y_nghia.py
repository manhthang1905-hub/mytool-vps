"""Nhãn CỤM theo Ý NGHĨA cho vòng tự học (07/10/2026) — đường lùi khi bộ nhận cụm V7 trả `[]`.

Báo cáo ngày (`bao_cao_ngay._muc_hoc`) đo: "Ván không nhãn cụm — TL1-T7 11/17, TL4-T7-K2 2/3, …". Nguyên nhân: nhãn
cụm của ván lấy từ `cum_tu_hoc` (lúc chọn) → `cum` của dòng nguồn → `cum_cua(tiêu đề)` (V7: nhãn AI
`phan_cum_ai` nếu có, không thì từ khoá). `phan_cum_ai` chỉ gán khi đề tài CHÍNH thuộc cụm (0–2 cụm, được phép
`[]`), từ khoá thì chỉ bắt chữ — tiêu đề nằm ngoài cả hai cho nhãn rỗng, trục cụm không học được video đó và hệ
số Thompson của bộ chọn content mù với nó.

Ở đây: MỘT lượt LLM (theo lô, nhiều tiêu đề một lần — như `chien_truong_ai`) xếp mỗi tiêu đề vào ĐÚNG MỘT cụm
có sẵn của kênh (mã + tên + chữ ví dụ từ cấu hình V7, mô tả ngách từ `ngach.yaml`) theo NGHĨA, hoặc
`khac` khi không cụm nào hợp. `khac` là một cánh tay thật của trục cụm: "đề tài ngoài các cụm" thắng hay
trượt cũng là điều cần học. Nguyên tắc chủ dự án: "phân loại theo nghĩa, không lọc từ khoá; không tiếc token".

Bộ nhớ `CHANNEL/<k>/tu-hoc/cum-y-nghia.json` = `{"bo": {khoá bộ cụm: {khoá tiêu đề: {"c", "t", "ngay"} |
{"hong": n}}}}` — mỗi tiêu đề (chuẩn hoá NFKC) chỉ hỏi MỘT lần; kênh đổi bộ cụm thì khoá bộ cụm đổi, nhãn cũ
không bị đọc nhầm. LLM trả mã lạ → không nhãn (đếm `hong`, quá `SO_LAN_HONG_TOI_DA` lần thì thôi hỏi).

Chặn & an toàn: tối đa `TOI_DA_MOT_LUOT` tiêu đề mỗi lượt; ví AI chặn (`goi_chat_that` trả None) → bỏ qua;
mọi lỗi → `tu_hoc.canh_bao`, không bao giờ ném ra ngoài (học không được chặn sản xuất).

Nơi gọi: `tu_hoc.cham_van(dung_ai=True)` (vòng học, bù nhãn ván cũ/mới), `phan_cum_ai.lam_nong` (lúc chọn,
ứng viên đầu bảng), `chien_luoc._ap_he_so_cum` (chỉ ĐỌC bộ nhớ — gắn `cum_tu_hoc` cho nguồn).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

CUM_KHAC = "khac"
TEP = "cum-y-nghia.json"
TOI_DA_MOT_LUOT = 60
LO = 60
SO_LAN_HONG_TOI_DA = 2
MO_HINH = "claude-sonnet-5"
#: Nguồn của nhãn cụm (ghi kèm `cum_nguon` ở dòng nguồn và `nuoc` của ván).
NGUON_NGUON, NGUON_TU_KHOA, NGUON_Y_NGHIA = "nguon", "tu_khoa", "y_nghia"


def duong(goc: str, ma_kenh: str) -> str:
    from .kenh import duong_kenh  # noqa: PLC0415

    return os.path.join(duong_kenh(goc, ma_kenh), "tu-hoc", TEP)


def _cau_hinh(goc: str, ma_kenh: str) -> Dict[str, Any]:
    from . import cong_thuc_v7 as v7  # noqa: PLC0415

    ch, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
    return ch or {}


def _khoa_tieu_de(td: str) -> str:
    from .phan_cum_ai import khoa_tieu_de  # noqa: PLC0415 — cùng cách chuẩn hoá (NFKC, gộp khoảng trắng)

    return khoa_tieu_de(td)


def _khoa_bo(ch: Dict[str, Any]) -> str:
    from .phan_cum_ai import khoa_bo_cum  # noqa: PLC0415

    return khoa_bo_cum(ch)


def _canh_bao(goc: str, loi: Any, ma_kenh: str) -> None:
    try:
        from . import tu_hoc  # noqa: PLC0415

        tu_hoc.canh_bao(goc, "cum_y_nghia", loi, ma_kenh)
    except Exception:  # noqa: BLE001
        pass


class BoNho:
    """Bộ nhớ nhãn theo nghĩa của MỘT kênh với bộ cụm hiện tại. Đọc đĩa lười, một lần; `duong_tep` thay được
    (chạy thử ghi ra bản sao tạm, không đụng cây thật)."""

    def __init__(self, goc: str, ma_kenh: str, ch: Optional[Dict[str, Any]] = None,
                 duong_tep: Optional[str] = None) -> None:
        self.goc, self.ma_kenh = goc, ma_kenh
        self.ch = ch if ch else _cau_hinh(goc, ma_kenh)
        self.cum: Dict[str, Any] = dict(self.ch.get("cum") or {})
        self.bo = _khoa_bo(self.ch) if self.cum else ""
        self.duong = duong_tep or duong(goc, ma_kenh)
        self._du: Optional[Dict[str, Any]] = None

    def _doc(self) -> Dict[str, Any]:
        if self._du is None:
            try:
                with io.open(self.duong, encoding="utf-8") as tep:
                    du = json.load(tep)
                self._du = du if isinstance(du, dict) else {}
            except (OSError, ValueError):
                self._du = {}
        return self._du

    def _muc(self, td: str) -> Dict[str, Any]:
        if not self.bo or not str(td or "").strip():
            return {}
        o = ((self._doc().get("bo") or {}).get(self.bo) or {}).get(_khoa_tieu_de(td))
        return o if isinstance(o, dict) else {}

    def hop_le(self, ma: Any) -> bool:
        return str(ma or "") == CUM_KHAC or str(ma or "") in self.cum

    def tra(self, td: str) -> str:
        """Nhãn đã hỏi của tiêu đề (`mã cụm` | `khac`), "" nếu chưa có / mã không còn trong bộ cụm."""
        c = str(self._muc(td).get("c") or "")
        return c if self.hop_le(c) else ""

    def so_hong(self, td: str) -> int:
        try:
            return int(self._muc(td).get("hong") or 0)
        except (TypeError, ValueError):
            return 0

    def ghi(self, moi: Dict[str, Dict[str, Any]]) -> None:
        """Gộp `{khoá tiêu đề: mục}` vào tệp (đọc lại đĩa trước khi ghi — không mất nhãn tiến trình khác vừa ghi)."""
        if not moi or not self.bo:
            return
        from .tu_hoc import _ghi_nguyen_tu  # noqa: PLC0415

        self._du = None
        du = self._doc()
        bang = du.setdefault("bo", {}).setdefault(self.bo, {})
        bang.update(moi)
        du["phien_ban"] = 1
        _ghi_nguyen_tu(self.duong, json.dumps(du, ensure_ascii=False, indent=0) + "\n")


def goi_vi(goc: str, log: Optional[Callable[[str], None]] = None) -> Optional[Callable[..., str]]:
    """Hàm gọi AI qua ví (`giam_doc.quan_ly.goi_chat_that`); None khi ví chặn, gốc không có `config.json`
    (thư mục tạm của bài kiểm — không bao giờ gọi AI thật từ đó) hoặc không dựng được."""
    try:
        from .config import CONFIG_FILENAME  # noqa: PLC0415
        from .giam_doc import quan_ly  # noqa: PLC0415

        if not os.path.isfile(os.path.join(goc, CONFIG_FILENAME)):
            return None
        return quan_ly.goi_chat_that(goc, log)
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, loi, "")
        return None


def la_goi_that(goi_chat: Any) -> bool:
    """Hàm gọi AI của vòng tự chạy THẬT (không phải đồ giả của bài kiểm): `goi_chat_that` gắn `.that`, vòng tự
    chạy dựng bằng `tu_chay._dung_goi_chat_mac_dinh`. Đồ giả → False: lúc chọn nguồn không gọi thêm AI."""
    if goi_chat is None:
        return False
    if getattr(goi_chat, "that", False) is True:
        return True
    return str(getattr(goi_chat, "__qualname__", "")).startswith("_dung_goi_chat_mac_dinh.")


def _mo_ta_ngach(goc: str, ma_kenh: str) -> str:
    try:
        from .ho_so_ngach import doc_ngach  # noqa: PLC0415

        n = doc_ngach(goc, ma_kenh)
        if getattr(n, "co", lambda: False)():
            return str(n.mo_ta_phan_cum or n.mo_ta_ngach or "").strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def de_bai(cum: Dict[str, Any], lo: Sequence[Tuple[str, str]], mo_ta_ngach: str = "") -> str:
    ds_cum = "\n".join("- {0}: {1}{2}".format(ma, str((c or {}).get("ten") or ""), " (vd: {0})".format(
        "、".join(str(t) for t in ((c or {}).get("tu") or [])[:6])) if (c or {}).get("tu") else "")
        for ma, c in cum.items())
    ds = "\n".join("{0}. {1}{2}".format(i + 1, td, "  〔{0}〕".format(mt[:220]) if mt else "")
                   for i, (td, mt) in enumerate(lo))
    return (
        "Bạn xếp video YouTube{ngach} vào CỤM CHỦ ĐỀ của kênh theo Ý NGHĨA — video thật sự nói về điều gì, hứa gì "
        "với người xem — KHÔNG theo từ khoá. Bỏ qua nhãn thể loại trong ngoặc 【】 và hashtag.\n\n"
        "CỤM (mã: tên — chữ ví dụ chỉ để hiểu nghĩa, KHÔNG phải luật khớp chữ):\n{cum}\n\n"
        "Quy tắc:\n"
        "- Mỗi video đúng MỘT mã: cụm mà người xem của video này sẽ coi là CÙNG ĐỀ TÀI (gần nhất về nghĩa).\n"
        "- Đề tài chính khác hẳn mọi cụm → \"{khac}\". Không đặt mã mới, chỉ dùng mã trong danh sách hoặc \"{khac}\".\n\n"
        "VIDEO:\n{ds}\n\n"
        "Trả về DUY NHẤT một object JSON, đủ mọi số thứ tự: {{\"1\": \"<mã>\", \"2\": \"{khac}\", ...}}"
    ).format(ngach=" ({0})".format(mo_ta_ngach) if mo_ta_ngach else "", cum=ds_cum, ds=ds, khac=CUM_KHAC)


def phan_loai(goc: str, ma_kenh: str, muc: Sequence[Tuple[str, str]], goi: Optional[Callable[..., str]], *,
              bo: Optional[BoNho] = None, toi_da: int = TOI_DA_MOT_LUOT, mo_hinh: str = MO_HINH,
              log: Optional[Callable[[str], None]] = None) -> int:
    """Gán nhãn cho các `(tiêu đề, mô tả)` CHƯA có trong bộ nhớ (tối đa `toi_da`, lô `LO`). `goi` = hàm gọi AI đã
    qua van ví (None → không làm gì). Trả số tiêu đề có nhãn mới. Không ném lỗi."""
    if goi is None or not muc:
        return 0
    try:
        bo = bo or BoNho(goc, ma_kenh)
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, loi, ma_kenh)
        return 0
    if not bo.cum:
        return 0
    can: List[Tuple[str, str]] = []
    thay: set = set()
    for td, mt in muc:
        if len(can) >= int(toi_da):
            break
        td = " ".join(str(td or "").split())
        k = _khoa_tieu_de(td) if td else ""
        if not k or k in thay or bo.tra(td) or bo.so_hong(td) >= SO_LAN_HONG_TOI_DA:
            continue
        thay.add(k)
        can.append((td, " ".join(str(mt or "").split())))
    if not can:
        return 0
    from .goi_van_ban import loc_json  # noqa: PLC0415

    mo_ta = _mo_ta_ngach(goc, ma_kenh)
    hom_nay = _dt.date.today().isoformat()
    da = 0
    for i in range(0, len(can), LO):
        lo = can[i:i + LO]
        khoa = "cum-y-nghia-{0}-{1}-{2}".format(ma_kenh, bo.bo, hashlib.sha1(
            "|".join(t for t, _ in lo).encode("utf-8")).hexdigest()[:10])
        try:
            tho = goi(de_bai(bo.cum, lo, mo_ta), mo_hinh=mo_hinh, khoa=khoa,
                      toi_da_token=max(4096, 40 * len(lo) + 1000))
            du = loc_json(tho)
            if isinstance(du, list):
                du = {str(j + 1): x for j, x in enumerate(du)}
            if not isinstance(du, dict):
                raise ValueError("câu trả lời nhãn cụm không phải JSON object")
        except Exception as loi:  # noqa: BLE001 — một lô hỏng: dừng lượt (mạng/ví), lượt sau hỏi lại
            _canh_bao(goc, loi, ma_kenh)
            break
        moi: Dict[str, Dict[str, Any]] = {}
        for j, (td, _mt) in enumerate(lo):
            v = du.get(str(j + 1))
            v = v[0] if isinstance(v, list) and v else v
            ma = str(v or "").strip()
            ma = ma.lower() if ma.lower() == CUM_KHAC else ma
            if bo.hop_le(ma):
                moi[_khoa_tieu_de(td)] = {"c": ma, "t": td[:60], "ngay": hom_nay}
            else:  # mã lạ / thiếu → không nhãn (không bịa), đếm hỏng để thôi hỏi mãi
                moi[_khoa_tieu_de(td)] = {"hong": bo.so_hong(td) + 1, "t": td[:60], "ngay": hom_nay}
        sai = sum(1 for m in moi.values() if "c" not in m)
        if sai:
            _canh_bao(goc, "LLM trả {0}/{1} mã cụm lạ — để trống".format(sai, len(lo)), ma_kenh)
        try:
            bo.ghi(moi)
        except Exception as loi:  # noqa: BLE001
            _canh_bao(goc, loi, ma_kenh)
            break
        da += len(lo) - sai
    if log is not None and da:
        log("  nhãn cụm theo nghĩa: {0}/{1} tiêu đề có nhãn mới.".format(da, len(can)))
    return da


def gan_ung_vien(goc: str, ma_kenh: str, ch: Dict[str, Any], goi_chat: Any, tieu_de: Sequence[str], *,
                 cum_cua: Optional[Callable[[str], List[str]]] = None, toi_da: int = TOI_DA_MOT_LUOT,
                 log: Optional[Callable[[str], None]] = None) -> int:
    """Lúc CHỌN (gọi cuối `phan_cum_ai.lam_nong`): ứng viên đầu bảng mà bộ nhận cụm V7 trả `[]` → hỏi nhãn
    theo nghĩa, để `_ap_he_so_cum` gắn được `cum_tu_hoc`. Chỉ chạy với hàm gọi AI THẬT (`la_goi_that`) và
    qua van ví. Trả số tiêu đề có nhãn mới."""
    if not la_goi_that(goi_chat):
        return 0
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        nhan_v7 = cum_cua or (lambda td: list(v7.cum_cua_tieu_de(td, ch) or []))
        bo = BoNho(goc, ma_kenh, ch=ch)
        muc = [(t, "") for t in tieu_de if t and not nhan_v7(t) and not bo.tra(t)]
        if not muc:
            return 0
        goi = goi_vi(goc, log)
        return phan_loai(goc, ma_kenh, muc, goi, bo=bo, toi_da=toi_da, log=log) if goi is not None else 0
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, loi, ma_kenh)
        return 0
