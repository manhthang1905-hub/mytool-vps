"""**Nghiên cứu CHUNG theo nhóm kênh** — bộ đệm dùng chung cho những bước gọi
mạng/AI mà mọi kênh cùng nhóm đều làm y hệt nhau.

═══ VÌ SAO (kiểm toán 29/09/2026) ═══

Chủ dự án: *"Trên VPS thường làm CHUNG MỘT CHỦ ĐỀ → đối thủ và nguồn content
CHUNG, nghiên cứu TẬP TRUNG một chỗ; tư duy đơn giản, hiệu quả, bỏ khâu thừa."*

Đo 29/09: TL1/TL2/TL3 (nhóm `tam-ly-nhat`) mỗi lượt đều tra lại 400 video trang
chủ (bộ nhớ tra RIÊNG từng kênh, trùng 1.905/1.909 mã), mỗi kênh chấm lại ~115
kênh hộp thư (≈ 65–69 lượt AI, 24'), quét lại content của ~250 đối thủ (192
trùng cả ba, ~9'/kênh), AI phân loại lại ~281 tiêu đề "lưỡng lự" mỗi lần (không
lưu), AI gán tuyến chạm trần 240 dòng mỗi lần (câu độ tin thấp không lưu → hỏi
lại). Cùng một câu hỏi, cùng câu trả lời, trả tiền ba lần.

═══ CÁCH LÀM: BỘ ĐỆM Ở CHỖ GỌI, TỆP KẾT QUẢ VẪN RIÊNG TỪNG KÊNH ═══

Không dời `content.csv`/`doi-thu.csv` (giao diện, V7, phân tuyến cùng đọc) — mỗi
kênh vẫn giữ sổ riêng như cũ. Chỉ đặt bộ đệm NGAY Ở CHỖ GỌI mạng/AI, trong kho
chung `CHANNEL/_NHOM/<nhóm>/nghien-cuu/` (cùng nếp `loi_thoai.thu_muc_kho`):

| tệp | là gì | hạn |
|---|---|---|
| `trang-chu-tra.json` | yt-dlp tra video trang chủ theo mã | vĩnh viễn (như cũ) |
| `trang-chu-ai.json` | AI "tâm lý hay không" cho tiêu đề lưỡng lự | 90 ngày |
| `kenh-do.json` | số đo kênh ứng viên (40 video mới nhất) | 7 ngày |
| `kenh-ai.json` | phán quyết AI "đối thủ/gần/không" theo NGÁCH | 30 ngày |
|   ↳ kênh bật `cho_phep_tep_gia` | kho RIÊNG `CHANNEL/<kênh>/nghien-cuu/kenh-ai.json` (`duong_kenh_ai`) | 30 ngày |
| `quet-kenh/<khoá>.json` | ảnh chụp kênh đối thủ lúc quét content | 10 giờ |
| `nhan-tuyen/<kênh>.json` | AI gán tuyến (RIÊNG từng kênh — tuyến khác nhau) | 14 ngày |
| `nhan-tuyen/<kênh>.phan-xu.json` | AI phán "luật chữ bắt nhầm, giữ nhãn" (29/09) | 30 ngày |

Kênh KHÔNG khai `nhom` → kho là `CHANNEL/<kênh>/nghien-cuu/` của chính nó: đường
`trang-chu-tra.json` y như trước, hành vi không đổi.

Ghi an toàn khi nhiều tiến trình song song: mỗi lần ghi là ĐỌC LẠI bản trên đĩa,
GỘP khoá của mình vào, ghi tệp tạm riêng theo PID rồi `os.replace` — không bao giờ
để JSON dở dang; hai tiến trình ghi cùng lúc thì cùng lắm mất vài mục đệm (lượt
sau tra lại), không hỏng tệp. Thêm khoá O_EXCL ngắn quanh đọc-gộp-ghi để giảm cả
chuyện mất mục ấy.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import functools
import hashlib
import io
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["THU_MUC", "nhom_cua", "thu_muc", "doc_json", "ghi_json_gop", "ghi_json",
           "doc_tra", "luu_tra", "ai_trang_chu_da_biet", "ai_trang_chu_ghi",
           "lay_kenh_co_dem", "hoi_ai_co_dem", "lay_du_lieu_co_dem", "duong_kenh_ai",
           "nhan_tuyen_doc", "nhan_tuyen_ghi", "phan_xu_doc", "phan_xu_ghi",
           "khan_gia_cung_xem_doc", "khan_gia_cung_xem_ghi",
           "HAN_AI_TRANG_CHU_NGAY", "HAN_KENH_DO_NGAY", "HAN_KENH_AI_NGAY",
           "HAN_QUET_GIO", "HAN_NHAN_TUYEN_NGAY", "HAN_PHAN_XU_NGAY"]

THU_MUC = "nghien-cuu"
TEP_TRA = "trang-chu-tra.json"
TEP_AI_TRANG_CHU = "trang-chu-ai.json"
TEP_KENH_DO = "kenh-do.json"
TEP_KENH_AI = "kenh-ai.json"
THU_MUC_QUET = "quet-kenh"
THU_MUC_NHAN_TUYEN = "nhan-tuyen"
#: "Khán giả của bạn còn xem gì" (`chi_so_ytb.giai_ma.cap_nhat_khan_gia_cung_xem`,
#: insight #8 29/09/2026) — mỗi kênh nguồn ghi dưới khoá riêng của mình.
TEP_KHAN_GIA_CUNG_XEM = "khan-gia-cung-xem.json"

HAN_AI_TRANG_CHU_NGAY = 90
HAN_KENH_DO_NGAY = 7
HAN_KENH_AI_NGAY = 30
HAN_QUET_GIO = 10.0
HAN_NHAN_TUYEN_NGAY = 14
HAN_PHAN_XU_NGAY = 30


# ── đường ─────────────────────────────────────────────────────────────────────


def nhom_cua(goc: str, ma_kenh: str) -> str:
    """`nhom` của kênh; đọc hỏng → "" (coi như đứng một mình — thà hẹp còn chạy)."""
    try:
        from . import nhom_kenh  # noqa: PLC0415 — nhom_kenh nhập trang_chu → tránh vòng

        return nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return ""


def thu_muc(goc: str, ma_kenh: str) -> str:
    """Kho nghiên cứu HIỆU LỰC: nhóm → `CHANNEL/_NHOM/<nhóm>/nghien-cuu/`, không
    thì `CHANNEL/<kênh>/nghien-cuu/`."""
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    nhom = nhom_cua(goc, ma_kenh)
    if nhom:
        from . import nhom_kenh  # noqa: PLC0415

        return os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), THU_MUC)
    return thu_muc_nghien_cuu(goc, ma_kenh)


def _hom_nay() -> str:
    return _dt.date.today().isoformat()


def _con_han_ngay(ngay: Any, han_ngay: int) -> bool:
    try:
        d = _dt.date.fromisoformat(str(ngay)[:10])
    except ValueError:
        return False
    return (_dt.date.today() - d).days < han_ngay


# ── đọc/ghi JSON an toàn ──────────────────────────────────────────────────────


def doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return {} if mac_dinh is None else mac_dinh


class _KhoaNgan:
    """Khoá O_EXCL ngắn quanh đọc-gộp-ghi. Chờ tối đa `cho` giây; khoá cũ hơn
    `cu` giây (tiến trình chết giữa chừng) thì phá. Không giành được vẫn đi tiếp
    — ghi nguyên tử nên tệp không hỏng, cùng lắm mất vài mục đệm."""

    def __init__(self, duong: str, cho: float = 5.0, cu: float = 60.0) -> None:
        self.duong, self.cho, self.cu, self.giu = duong + ".khoa", cho, cu, False

    def __enter__(self) -> "_KhoaNgan":
        het = time.time() + self.cho
        while True:
            try:
                fd = os.open(self.duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("ascii"))
                os.close(fd)
                self.giu = True
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.duong) > self.cu:
                        os.remove(self.duong)
                        continue
                except OSError:
                    continue
                if time.time() >= het:
                    return self
                time.sleep(0.05)
            except OSError:
                return self

    def __exit__(self, *_a: Any) -> None:
        if self.giu:
            try:
                os.remove(self.duong)
            except OSError:
                pass


def ghi_json(duong: str, du: Any) -> None:
    """Ghi nguyên tử — tệp tạm RIÊNG theo PID (hai tiến trình không giẫm tệp tạm)."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = "{0}.{1}.tmp".format(duong, os.getpid())
    with io.open(tam, "w", encoding="utf-8") as tep:
        tep.write(json.dumps(du, ensure_ascii=False, indent=1))
    os.replace(tam, duong)


def ghi_json_gop(duong: str, moi: Dict[str, Any]) -> Dict[str, Any]:
    """Đọc lại bản trên đĩa, gộp `moi` vào (khoá của mình thắng), ghi nguyên tử."""
    with _KhoaNgan(duong):
        cu = doc_json(duong, {})
        if not isinstance(cu, dict):
            cu = {}
        cu.update(moi)
        ghi_json(duong, cu)
    return cu


# ── 1) bộ nhớ tra trang chủ (yt-dlp theo mã video) ───────────────────────────


def doc_tra(goc: str, ma_kenh: str) -> Dict[str, dict]:
    """Bộ nhớ tra HIỆU LỰC. Nhóm mà kho chung chưa có tệp → gộp một lần bộ nhớ
    riêng của mọi thành viên (lần đầu chuyển sang kho chung không tra lại gì)."""
    p = os.path.join(thu_muc(goc, ma_kenh), TEP_TRA)
    if os.path.isfile(p) or not nhom_cua(goc, ma_kenh):
        du = doc_json(p, {})
        return du if isinstance(du, dict) else {}
    from . import nhom_kenh  # noqa: PLC0415
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    gop: Dict[str, dict] = {}
    for ma in nhom_kenh.thanh_vien(goc, ma_kenh):
        du = doc_json(os.path.join(thu_muc_nghien_cuu(goc, ma), TEP_TRA), {})
        if isinstance(du, dict):
            for k, v in du.items():
                if k not in gop or (v and not gop[k]):
                    gop[k] = v
    return gop


def luu_tra(goc: str, ma_kenh: str, bo_nho: Dict[str, dict]) -> None:
    p = os.path.join(thu_muc(goc, ma_kenh), TEP_TRA)
    if nhom_cua(goc, ma_kenh):
        ghi_json_gop(p, bo_nho)
    else:
        ghi_json(p, bo_nho)


# ── 2) AI "tâm lý hay không" cho tiêu đề trang chủ lưỡng lự (#3) ─────────────


def ai_trang_chu_da_biet(goc: str, ma_kenh: str, tieu_de: Sequence[str]) -> Dict[str, str]:
    """`{tiêu đề: 'dung'|'lech'}` đã hỏi AI trong `HAN_AI_TRANG_CHU_NGAY` ngày."""
    du = doc_json(os.path.join(thu_muc(goc, ma_kenh), TEP_AI_TRANG_CHU), {})
    ra: Dict[str, str] = {}
    if not isinstance(du, dict):
        return ra
    for td in tieu_de:
        m = du.get(td)
        if isinstance(m, dict) and m.get("kq") in ("dung", "lech") \
                and _con_han_ngay(m.get("ngay"), HAN_AI_TRANG_CHU_NGAY):
            ra[td] = m["kq"]
    return ra


def ai_trang_chu_ghi(goc: str, ma_kenh: str, phan: Dict[str, str]) -> None:
    moi = {td: {"kq": kq, "ngay": _hom_nay()} for td, kq in (phan or {}).items()
           if kq in ("dung", "lech")}
    if moi:
        ghi_json_gop(os.path.join(thu_muc(goc, ma_kenh), TEP_AI_TRANG_CHU), moi)


# ── ảnh chụp kênh (youtube.Channel) ↔ JSON ───────────────────────────────────


def _kenh_ra_dict(ch: Any) -> Optional[dict]:
    try:
        return dataclasses.asdict(ch)
    except Exception:  # noqa: BLE001 — không phải dataclass (giả trong bài kiểm) → không đệm
        return None


def _kenh_tu_dict(d: dict) -> Any:
    from .youtube import Channel, Video  # noqa: PLC0415

    ten_video = {f.name for f in dataclasses.fields(Video)}
    ten_kenh = {f.name for f in dataclasses.fields(Channel)} - {"videos"}
    ch = Channel(**{k: v for k, v in d.items() if k in ten_kenh})
    ch.videos = [Video(**{k: v for k, v in (x or {}).items() if k in ten_video})
                 for x in (d.get("videos") or [])]
    return ch


# ── 3) số đo kênh ứng viên lúc chốt hộp thư (`chot_doi_thu.do_ung_vien`) ─────


def lay_kenh_co_dem(goc: str, ma_kenh: str,
                    lay_kenh: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """Bọc `youtube.fetch_channel` (chữ ký của `do_ung_vien`) bằng `kenh-do.json`."""
    if lay_kenh is None:
        from .youtube import fetch_channel as lay_kenh  # noqa: PLC0415
    p = os.path.join(thu_muc(goc, ma_kenh), TEP_KENH_DO)
    bo: Dict[str, Any] = {"du": None}

    def _lay(link: str, *, max_videos: int = 0, lang: str = "", cancel=None, **k: Any) -> Any:
        khoa = "{0}|{1}|{2}".format(str(link).strip().lower(), int(max_videos or 0), lang or "")
        if bo["du"] is None:
            du = doc_json(p, {})
            bo["du"] = du if isinstance(du, dict) else {}
        m = bo["du"].get(khoa)
        if isinstance(m, dict) and _con_han_ngay(m.get("ngay"), HAN_KENH_DO_NGAY):
            try:
                return _kenh_tu_dict(m.get("ch") or {})
            except Exception:  # noqa: BLE001 — bản đệm hỏng → đo lại
                pass
        ch = lay_kenh(link, max_videos=max_videos, lang=lang, cancel=cancel, **k)
        d = _kenh_ra_dict(ch)
        if d is not None and d.get("videos"):
            muc = {"ngay": _hom_nay(), "ch": d}
            bo["du"][khoa] = muc
            try:
                ghi_json_gop(p, {khoa: muc})
            except OSError:
                pass
        return ch

    return _lay


# ── 4) phán quyết AI cho kênh ứng viên (cửa thứ năm) ─────────────────────────


def duong_kenh_ai(goc: str, ma_kenh: str) -> str:
    """Kho phán quyết NGÁCH của kênh đối thủ: `kenh-ai.json` chung của nhóm — TRỪ kênh bật kenh.yaml
    `cho_phep_tep_gia` (tệp người già, 30/09/2026): kho chung đã phán "không" nhiều kênh senior theo
    tệp 25–62 của TL1–TL4, nên kênh ấy dùng kho RIÊNG `CHANNEL/<kênh>/nghien-cuu/kenh-ai.json` (phán
    với mô tả ngách + luật chọn của chính nó), không đọc cũng không ghi đè kho nhóm."""
    try:
        from .phan_tuyen import cho_phep_tep_gia  # noqa: PLC0415

        rieng = cho_phep_tep_gia(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        rieng = False
    if rieng:
        from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

        return os.path.join(thu_muc_nghien_cuu(goc, ma_kenh), TEP_KENH_AI)
    return os.path.join(thu_muc(goc, ma_kenh), TEP_KENH_AI)


def hoi_ai_co_dem(goc: str, ma_kenh: str,
                  hoi: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """Bọc `loc_doi_thu.hoi_ai_kenh` bằng `kenh-ai.json` — chấm theo NGÁCH của nhóm
    (một kênh đối thủ là/không là kênh tâm lý thì như nhau với mọi tệp)."""
    from . import loc_doi_thu as loc  # noqa: PLC0415

    if hoi is None:
        # 01/10/2026: ngách KHÁC ngách mặc định → đề bài không mang ví dụ "tâm lý" (`de_bai_loc_cho`);
        # ngách mặc định → `hoi_ai_kenh` y như cũ.
        # getattr: tiến trình đang chạy còn giữ `loc_doi_thu` bản cũ (trước 01/10) thì đi đường cũ.
        cho = getattr(loc, "de_bai_loc_cho", None)
        de_bai = cho(goc, ma_kenh) if cho is not None else loc.DE_BAI_LOC
        hoi = loc.hoi_ai_kenh if de_bai is loc.DE_BAI_LOC else functools.partial(loc.hoi_ai_kenh, de_bai=de_bai)
    p = duong_kenh_ai(goc, ma_kenh)

    def _hoi(client: Any, so_do: Any, **k: Any) -> Any:
        khoa = str(getattr(so_do, "link", "") or "").strip().lower()
        if khoa:
            du = doc_json(p, {})
            m = du.get(khoa) if isinstance(du, dict) else None
            if isinstance(m, dict) and _con_han_ngay(m.get("ngay"), HAN_KENH_AI_NGAY):
                return loc.DanhGia(ket=str(m.get("ket") or ""), diem=int(m.get("diem") or 0),
                                   ly_do=str(m.get("ly_do") or ""), tuyen=list(m.get("tuyen") or []),
                                   khac=str(m.get("khac") or ""))
        ai = hoi(client, so_do, **k)
        ket = str(getattr(ai, "ket", "") or "").strip().lower()
        if khoa and ket in ("doi_thu", "gan", "khong") \
                and not str(getattr(ai, "ly_do", "") or "").startswith("AI trả lời không đọc được"):
            try:
                ghi_json_gop(p, {khoa: {"ket": ket, "diem": int(getattr(ai, "diem", 0) or 0),
                                        "ly_do": str(getattr(ai, "ly_do", "") or ""),
                                        "tuyen": list(getattr(ai, "tuyen", []) or []),
                                        "khac": "", "ngay": _hom_nay(), "kenh": ma_kenh}})
            except OSError:
                pass
        return ai

    return _hoi


# ── 5) quét content đối thủ (`quet_doi_thu.quet` → `doi_thu.lay_du_lieu`) ───


def _duong_quet(goc: str, ma_kenh: str, khoa: str) -> str:
    ten = hashlib.sha1(khoa.encode("utf-8")).hexdigest()[:20] + ".json"
    return os.path.join(thu_muc(goc, ma_kenh), THU_MUC_QUET, ten)


def lay_du_lieu_co_dem(goc: str, ma_kenh: str, *,
                       han_gio: float = HAN_QUET_GIO) -> Callable[..., Any]:
    """`doi_thu.lay_du_lieu` với bước thu thập đi qua kho `quet-kenh/`: kênh đối
    thủ nào trong nhóm vừa quét trong `han_gio` giờ thì dùng lại ảnh chụp, chỉ
    gọi yt-dlp cho kênh chưa có. Link không phải link kênh → đường cũ (`collect`)."""
    from .doi_thu import lay_du_lieu  # noqa: PLC0415
    from .youtube import INPUT_CHANNEL, collect  # noqa: PLC0415

    def _thu_thap(inputs: List[Tuple[str, str]], *, max_videos: int = 0, expand: bool = False,
                  cancel=None, on_log=None, lang: str = "", **k: Any):
        co: List[Any] = []
        thieu: List[Tuple[str, str]] = []
        for kind, value in inputs:
            if kind == INPUT_CHANNEL:
                khoa = "{0}|{1}|{2}".format(str(value).strip().lower(), int(max_videos or 0), lang or "")
                m = doc_json(_duong_quet(goc, ma_kenh, khoa), {})
                if isinstance(m, dict) and m.get("luc") \
                        and time.time() - float(m["luc"]) < han_gio * 3600:
                    try:
                        co.append(_kenh_tu_dict(m.get("ch") or {}))
                        continue
                    except Exception:  # noqa: BLE001
                        pass
            thieu.append((kind, value))
        if co and on_log is not None:
            on_log("  dùng lại {0} kênh đối thủ nhóm đã quét ≤{1:.0f} giờ — chỉ quét mới {2} kênh."
                   .format(len(co), han_gio, len(thieu)))
        moi: List[Any] = []
        hits: List[Any] = []
        if thieu:
            moi, hits = collect(thieu, max_videos=max_videos, expand=expand, cancel=cancel,
                                on_log=on_log, lang=lang)
            for ch in moi:
                d = _kenh_ra_dict(ch)
                if d is None or not d.get("videos"):
                    continue
                khoa = "{0}|{1}|{2}".format(str(ch.input_url).strip().lower(),
                                            int(max_videos or 0), lang or "")
                try:
                    ghi_json(_duong_quet(goc, ma_kenh, khoa), {"luc": time.time(), "ch": d})
                except OSError:
                    pass
        ra: List[Any] = []
        thay: set = set()
        for ch in co + moi:
            k2 = ch.channel_id or str(ch.channel_url).lower()
            if k2 and k2 in thay:
                continue
            thay.add(k2)
            ra.append(ch)
        return ra, hits

    return functools.partial(lay_du_lieu, thu_thap=_thu_thap)


# ── 6) nhãn tuyến AI — RIÊNG từng kênh, nằm trong kho nhóm (#4) ──────────────


def _duong_nhan_tuyen(goc: str, ma_kenh: str) -> str:
    from .doi_thu_kenh import ten_kenh_an_toan  # noqa: PLC0415

    return os.path.join(thu_muc(goc, ma_kenh), THU_MUC_NHAN_TUYEN,
                        ten_kenh_an_toan(ma_kenh) + ".json")


def nhan_tuyen_doc(goc: str, ma_kenh: str) -> Dict[str, dict]:
    """`{link: {ma, do_tin, ngay}}` đã hỏi trong `HAN_NHAN_TUYEN_NGAY` ngày —
    KỂ CẢ câu AI trả "chưa chắc" (không ghi được vào sổ): không hỏi lại nó mỗi ngày."""
    du = doc_json(_duong_nhan_tuyen(goc, ma_kenh), {})
    if not isinstance(du, dict):
        return {}
    return {l: m for l, m in du.items()
            if isinstance(m, dict) and _con_han_ngay(m.get("ngay"), HAN_NHAN_TUYEN_NGAY)}


def nhan_tuyen_ghi(goc: str, ma_kenh: str, moi: Dict[str, dict]) -> None:
    if moi:
        ghi_json_gop(_duong_nhan_tuyen(goc, ma_kenh), moi)


# ── 6b) phán xử luật cứng THEO NGHĨA — RIÊNG từng kênh (29/09/2026) ──────────
#
# `phan_tuyen.gan_tuyen` hỏi AI "luật chữ này có bắt nhầm không" trước khi đè nhãn; câu "giữ"
# được `sua_so_theo_luat_cung` ghi vào đây để các lượt sau không đè lại nhãn đã phán xử.


def _duong_phan_xu(goc: str, ma_kenh: str) -> str:
    from .doi_thu_kenh import ten_kenh_an_toan  # noqa: PLC0415

    return os.path.join(thu_muc(goc, ma_kenh), THU_MUC_NHAN_TUYEN,
                        ten_kenh_an_toan(ma_kenh) + ".phan-xu.json")


def phan_xu_doc(goc: str, ma_kenh: str) -> Dict[str, dict]:
    """`{tiêu đề: {"giu": [mã…], "ngay"}}` còn hạn `HAN_PHAN_XU_NGAY` ngày."""
    du = doc_json(_duong_phan_xu(goc, ma_kenh), {})
    if not isinstance(du, dict):
        return {}
    return {t: m for t, m in du.items()
            if isinstance(m, dict) and _con_han_ngay(m.get("ngay"), HAN_PHAN_XU_NGAY)}


def phan_xu_ghi(goc: str, ma_kenh: str, moi: Dict[str, dict]) -> None:
    moi = {t: dict(m, ngay=m.get("ngay") or _hom_nay()) for t, m in (moi or {}).items() if isinstance(m, dict)}
    if moi:
        ghi_json_gop(_duong_phan_xu(goc, ma_kenh), moi)


# ── 7) "khán giả của bạn còn xem gì" — kho chung, mỗi kênh nguồn một khoá ────


def khan_gia_cung_xem_doc(goc: str, ma_kenh: str) -> Dict[str, dict]:
    """Kho "khán giả cũng xem" HIỆU LỰC của kênh (nhóm → kho chung nhóm, không
    thì `CHANNEL/<kênh>/nghien-cuu/`): `{kênh nguồn ghi: bản ghi}`, mỗi bản ghi
    mang `nguon: "khan_gia_cung_xem"`, `kenh_canh_tranh`, `video_dang_xem`,
    `ung_vien_doi_thu_uu_tien` (xem `chi_so_ytb.giai_ma.cap_nhat_khan_gia_cung_xem`)."""
    du = doc_json(os.path.join(thu_muc(goc, ma_kenh), TEP_KHAN_GIA_CUNG_XEM), {})
    return du if isinstance(du, dict) else {}


def khan_gia_cung_xem_ghi(goc: str, ma_kenh: str, moi: Dict[str, dict]) -> None:
    """Gộp một lượt đọc mới vào kho — nhiều kênh trong nhóm cùng ghi, mỗi kênh
    một khoá riêng (khoá của kênh này không đè bản ghi của kênh khác)."""
    if moi:
        ghi_json_gop(os.path.join(thu_muc(goc, ma_kenh), TEP_KHAN_GIA_CUNG_XEM), moi)
