"""HIỆU CHUẨN BỘ CHẤM — tin KẾT QUẢ THẬT hơn điểm giám khảo LLM (20/10/2026).

═══ VÌ SAO ═══

Mọi lượt chữ đi ví ShopAPI (`workspace/cai-dat.json: viet_chu_bang: "vi"`), và sổ ví chứng minh yêu cầu
claude-fable-5 / opus-5 / sonnet-5 thực ra được phục vụ bởi gemini-3-flash / gpt-5.6-terra / flash-lite. Chủ chọn GIỮ
đường này. Hệ quả: mọi giám khảo LLM (bìa, tiêu đề, kịch bản, hook, ảnh cảnh, biên tập) đều YẾU — đo thật 20/10: điểm
giám khảo bìa ↔ CTR thật gần như không tương quan ở vài kênh; dự đoán của biên tập viên AI kém cả tỉ lệ nền (đã bị hạ
xuống chỉ phủ quyết — `nghien-cuu/bien-tap/brier.json`). Máy phải tự biết bộ chấm nào ĐANG dự báo được, bộ nào không,
và bớt quyền của bộ không dự báo — không đợi người soi.

═══ LÀM GÌ ═══

1. SỔ CÁI (`workspace/hieu-chuan/so-cai.jsonl`): mỗi bộ chấm có ảnh hưởng tới một lựa chọn ghi (bộ chấm, kênh, mã gói,
   ứng viên, điểm, có được chọn không, trọng số lúc chọn, lúc). Ghi THẲNG ở nơi chọn (bìa lô, tiêu đề, kịch bản, hook)
   + BÙ (`gom`) từ những gì đã lưu sẵn: hồ sơ video (`ho-so-video/*.json`), `PROJECTS/AUTO/<K>/<lượt>/7-thumbnail/_lo/
   xep-hang.json` (CHỈ ĐỌC), sổ Brier của biên tập. Trùng khoá (bộ chấm|kênh|gói|ứng viên) thì bỏ — không phình.
2. HIỆU CHUẨN TUẦN (kỹ năng D22): mỗi bộ chấm × kênh (và GỘP các kênh đang chạy — kết quả chuẩn hoá theo trung vị
   kênh), Spearman giữa điểm của ứng viên ĐƯỢC CHỌN và kết quả nó phải dự báo:
       bìa / tiêu đề → CTR (≥ 1.000 hiển thị, ≥ 48 giờ; có trọng số √hiển thị — sai số CTR co theo √n, trọng số
                       thẳng theo hiển thị thì một video nổ nuốt cả mẫu); bìa/tiêu đề đã sửa trên Studio → số TRƯỚC sửa.
       kịch bản → % độ dài (AVD %) và % còn lại ở 0:30;  hook → % còn lại ở 0:30;  ảnh cảnh → AVD % (yếu, chỉ báo);
       biên tập → thắng/không (thước chung `core.thuoc_thang`);
       hàm giá trị học máy (`core/gia_tri`, G2: `gia_tri_tieu_de`, `gia_tri_de_tai`) → CTR và phân vị thước chung
                       (điểm theo mô hình HIỆN HÀNH, chấm lại mỗi lượt — mô hình chỉ học video đối thủ).
   LUẬT: n ≥ `N_TOI_THIEU` và rho < `RHO_KHONG` → «không dự báo», trọng số `W_PHU_QUYET` (chỉ còn PHỦ QUYẾT lỗi rõ);
   rho ≥ `RHO_DU` → trọng số 1; giữa hai mốc nội suy thẳng. Kênh chưa đủ mẫu → dùng số GỘP; gộp cũng chưa đủ → 1
   (giữ nguyên hành vi cũ). Ghi `workspace/hieu-chuan/<ngày>.json` + `trong-so.json` (nơi chọn đọc) + một dòng báo
   cáo ngày. Hiệu chuẩn KHÔNG BAO GIỜ gỡ cổng cứng: cổng chữ `core/cong_chu.py`, sàn màu / nhân vật / lỗi thấy được,
   cổng độc đáo — mọi thứ đó vẫn chặn như cũ; chỉ phần XẾP HẠNG / SÀN «giống bìa thắng» của giám khảo bị co quyền.
3. ÁP VÀO NƠI CHỌN (trọng số < 1):
   · bìa lô (`bia_lo.chay`): sàn `bam_nhu_thang` chỉ còn phủ quyết điểm rất thấp (`SAN_BAM_PHU_QUYET`); xếp hạng =
     w × hạng giám khảo + (1 − w) × TIÊN NGHIỆM MÁY — màu (bão hoà / tương phản / dải sáng) so phân phối bìa thắng
     THẬT của kênh; họ kiểu chữ của lô đã chọn theo dữ liệu từ trước (`core/bia_du_lieu`). Tiên nghiệm cũng vào sổ
     (bộ chấm `bia_mau`) để chính nó được hiệu chuẩn.
   · tiêu đề (`auto_khau._chon_tieu_de_nguyen_goc`): giám khảo chỉ phủ quyết điểm ≤ `TD_PHU_QUYET`; xếp hạng
     nghiêng về LOẠI ứng viên đã cho CTR thật tốt hơn (đối chứng = tiêu đề nguồn / nắn khuôn / bản N — đo lại mỗi tuần,
     `tien_nghiem_tieu_de`) × hệ số Thompson kiểu tiêu đề (kết quả thật, `core/tu_hoc`).
   · hook (`tu_hoc.bo_chon`): điểm giám khảo mũ w trước khi nhân hệ số Thompson; kịch bản / ảnh cảnh / biên tập: trọng
     số được ghi + báo (chưa có tổng có trọng số để áp).
4. HOOK ↔ GIỮ CHÂN: % còn lại ở 0:30 theo nhãn hook so trung vị kênh; lần THỬ hook của bộ não (`nao.py thu --truc
   hook`) — gói nào, 0:30 bao nhiêu → sự kiện não bộ phận «kich-ban».
5. BÀI HỌC CÓ GIÚP KHÔNG: bảng `dung` (`nao/bo-phan.db`: quyết định nào được đưa bài nào, 15% đối chứng) × nhãn thắng
   của video → mỗi bộ phận: tỉ lệ thắng có bài vs đối chứng. Bài học tự rút (`BH-N…`) đã dùng ≥ `N_BAI_HOC` lần mà đối
   chứng cũng ≥ `N_BAI_HOC` và không hơn → NGHỈ (đổi trạng thái, không xoá; ghi lịch sử + nhật ký bộ phận). Bài bản chiếu
   (`BH-<hex>`) do sổ nguồn quyết — chỉ báo «đề nghị nghỉ».

Dùng:  python -X utf8 -m core.hieu_chuan chay [--thu] [--goc G]   (--thu: CHỈ ĐỌC — không ghi gì, in bảng)
       python -X utf8 -m core.hieu_chuan gom [--goc G]             (chỉ bù sổ cái)
Không gọi LLM, không mạng, không tiền.
"""

from __future__ import annotations

import csv
import datetime as _dt
import glob
import hashlib
import io
import json
import math
import os
import re
import statistics
import sys
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

THU_MUC = ("workspace", "hieu-chuan")
TEP_SO_CAI = "so-cai.jsonl"
TEP_TRONG_SO = "trong-so.json"
PHIEN_BAN = 1

#: Luật trọng số (đề bài 20/10): n ≥ 10 và rho < 0,2 → không dự báo; rho ≥ 0,4 → đủ quyền.
N_TOI_THIEU = 10
RHO_KHONG, RHO_DU = 0.2, 0.4
W_PHU_QUYET = 0.25
#: Kết quả: video ≥ 48 giờ; CTR cần ≥ 1.000 hiển thị.
TUOI_TOI_THIEU = 48.0
IMP_TOI_THIEU = 1000.0
#: Nhịp hiệu chuẩn (ngày) — kỹ năng D22.
NGAY_NHIP = 7
#: Áp vào nơi chọn: sàn phủ quyết `bam_nhu_thang` của bìa lô (1–10) và điểm tiêu đề (1–10) khi giám khảo không dự báo.
SAN_BAM_PHU_QUYET = 4.0
TD_PHU_QUYET = 3.0
#: Tiên nghiệm tiêu đề khi giám khảo bị co quyền: LOẠI ứng viên (đối chứng = tiêu đề nguồn | nắn khuôn | bản N) theo
#: CTR THẬT khi loại ấy được chọn (tỉ lệ so trung vị kênh, gộp các kênh), co về 1 với `CO_TIEN_NGHIEM` mẫu ảo; loại có
#: < `N_TOI_THIEU` lần chọn thì trung tính. Đo 20/10: nắn khuôn ×0,75 (n 9), đối chứng ×1,27 (n 4), bản N ×1,00 (n 31)
#: — đặt tay «nắn khuôn trước» là sai; chưa loại nào đủ mẫu → xếp hạng còn lại do hệ số Thompson kiểu tiêu đề.
LOAI_TD = ("đối chứng", "nắn khuôn", "bản N")
CO_TIEN_NGHIEM = 5.0
#: Bài học: cần ≥ ngần này quyết định CÓ bài và ≥ ngần này ĐỐI CHỨNG (đã có nhãn thắng/không) mới kết luận.
N_BAI_HOC = 8

#: Bộ chấm → (tên đọc, kết quả nó phải dự báo theo thứ tự ưu tiên). Kết quả: ctr | avd_pct | giu_30s | thang.
BO_CHAM: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "bia_lo": ("giám khảo bìa lô (tổng)", ("ctr",)),
    "bia_lo_bam": ("giám khảo bìa lô — «bấm như bìa thắng»", ("ctr",)),
    "bia_mau": ("tiên nghiệm máy bìa lô (màu so bìa thắng)", ("ctr",)),
    "bia": ("giám khảo bìa đời cũ (chon_bia)", ("ctr",)),
    "tieu_de": ("giám khảo tiêu đề", ("ctr",)),
    "kich_ban": ("giám khảo bản kịch bản", ("avd_pct", "giu_30s")),
    "hook": ("giám khảo hook", ("giu_30s",)),
    "anh_canh": ("giám khảo ảnh cảnh", ("avd_pct",)),
    "bien_tap": ("biên tập viên AI (xác suất thắng)", ("thang",)),
    # 20/10/2026 — G2: hàm giá trị HỌC MÁY (`core/gia_tri`, học trên video đối thủ) — đo như mọi bộ chấm khác
    "gia_tri_tieu_de": ("hàm giá trị học máy — tiêu đề được chọn", ("ctr", "pv")),
    "gia_tri_de_tai": ("hàm giá trị học máy — đề tài (tiêu đề nguồn)", ("pv", "ctr")),
}
#: Bộ chấm là MÔ HÌNH (điểm đổi khi học lại mỗi tuần) → dòng sổ cái được cập nhật theo mô hình hiện hành.
BO_CHAM_MO_HINH = ("gia_tri_tieu_de", "gia_tri_de_tai")
#: Chuỗi lùi khi bộ chấm chưa đủ mẫu (kênh → gộp → bộ chấm cùng lượt chấm). KHÔNG lùi bìa lô về giám khảo bìa đời cũ
#: (`bia`): khác lời nhắc, khác cách so (tờ điện thoại cạnh bìa thắng) — đo 20/10: `bia` gộp rho −0,39 (n 45) mà
#: `bia_lo` gộp +0,68 (n 6); mượn số của dụng cụ khác để tước quyền là phạt oan.
LUI = {"bia_lo_bam": ("bia_lo",)}
TEN_MUC = {"khong_du_bao": "không dự báo", "yeu": "yếu", "du_bao": "dự báo được", "chua_du": "chưa đủ mẫu",
           "mac_dinh": "mặc định"}
_RE_GOI = re.compile(r"^(.+)-(\d{3,5})$")


# ── tiện ích ────────────────────────────────────────────────────────────────


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with io.open(duong + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tmp", duong)


def _so(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(float(v)) else None
    s = str(v if v is not None else "").strip().replace(",", "").replace("%", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def _tv(xs: Iterable[Optional[float]]) -> Optional[float]:
    ds = [float(x) for x in xs if x is not None]
    return round(float(statistics.median(ds)), 3) if ds else None


def thu_muc(goc: str) -> str:
    return os.path.join(goc, *THU_MUC)


def _hang(xs: Sequence[float]) -> List[float]:
    thu = sorted(range(len(xs)), key=lambda i: xs[i])
    h = [0.0] * len(xs)
    i = 0
    while i < len(thu):
        j = i
        while j + 1 < len(thu) and xs[thu[j + 1]] == xs[thu[i]]:
            j += 1
        for k in range(i, j + 1):
            h[thu[k]] = (i + j) / 2.0
        i = j + 1
    return h


def spearman(a: Sequence[float], b: Sequence[float], w: Optional[Sequence[float]] = None) -> Optional[float]:
    """Spearman (hạng trung bình khi hoà); `w` = trọng số từng cặp (Pearson có trọng số trên hạng). < 4 cặp, hoặc
    một phía không đổi → None."""
    n = len(a)
    if n < 4 or n != len(b) or (w is not None and len(w) != n):
        return None
    ra, rb = _hang(list(a)), _hang(list(b))
    ww = [max(0.0, float(x)) for x in (w or [1.0] * n)]
    tw = sum(ww)
    if tw <= 0:
        return None
    ma = sum(x * p for x, p in zip(ra, ww)) / tw
    mb = sum(y * p for y, p in zip(rb, ww)) / tw
    sab = sum(p * (x - ma) * (y - mb) for x, y, p in zip(ra, rb, ww))
    sa = math.sqrt(sum(p * (x - ma) ** 2 for x, p in zip(ra, ww)))
    sb = math.sqrt(sum(p * (y - mb) ** 2 for y, p in zip(rb, ww)))
    if sa <= 1e-12 or sb <= 1e-12:
        return None
    return round(sab / (sa * sb), 3)


def kenh_hoc(goc: str) -> List[str]:
    """Kênh đang chạy được học: `kenh.liet_ke_kenh` (đã bỏ kênh trả kho) — chỉ kênh có hồ sơ video."""
    try:
        from .kenh import liet_ke_kenh  # noqa: PLC0415
        ds = liet_ke_kenh(goc)
    except Exception:  # noqa: BLE001
        return []
    return [k for k in ds if glob.glob(os.path.join(goc, "CHANNEL", k, "ho-so-video", "*.json"))]


def ho_so_kenh(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{mã gói: hồ sơ}` — đọc thẳng `CHANNEL/<k>/ho-so-video/*.json` (không nạp `ho_so_video`, vốn kéo cả dây chuyền)."""
    ra: Dict[str, Dict[str, Any]] = {}
    for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", "*.json"))):
        d = _doc_json(p)
        if isinstance(d, dict):
            ra[str(d.get("ma_goi") or os.path.splitext(os.path.basename(p))[0])] = d
    return ra


# ── 1) Sổ cái ───────────────────────────────────────────────────────────────


def duong_so_cai(goc: str) -> str:
    return os.path.join(thu_muc(goc), TEP_SO_CAI)


def doc_so_cai(goc: str) -> List[Dict[str, Any]]:
    """Mọi dòng sổ — cùng khoá thì dòng SAU thắng (bù từ hồ sơ video sửa «được chọn» khi cổng chữ đổi tấm bìa)."""
    try:
        with io.open(duong_so_cai(goc), encoding="utf-8") as tep:
            dong = tep.readlines()
    except OSError:
        return []
    ra: Dict[str, Dict[str, Any]] = {}
    for d in dong:
        try:
            x = json.loads(d)
        except ValueError:
            continue
        if isinstance(x, dict) and x.get("bo_cham") and x.get("khoa"):
            ra.pop(x["khoa"], None)
            ra[x["khoa"]] = x
    return list(ra.values())


def _khac(a: Optional[Dict[str, Any]], b: Dict[str, Any]) -> bool:
    return a is None or bool(a.get("chon")) != bool(b.get("chon")) or _so(a.get("diem")) != _so(b.get("diem"))


def khoa_dong(bo_cham: str, kenh: str, ma_goi: str, ung_vien: Any) -> str:
    return hashlib.sha1("|".join((bo_cham, kenh, ma_goi, str(ung_vien))).encode("utf-8")).hexdigest()[:16]  # noqa: S324


def dong_so_cai(bo_cham: str, kenh: str, ma_goi: str, ung_vien: Any, diem: Any, *, chon: bool,
                phu: Optional[Dict[str, Any]] = None, trong_so: Optional[float] = None, nguon: str = "truc-tiep",
                luc: str = "") -> Optional[Dict[str, Any]]:
    d = _so(diem)
    if d is None or not bo_cham or not kenh or not ma_goi:
        return None
    ra = {"khoa": khoa_dong(bo_cham, kenh, ma_goi, ung_vien), "bo_cham": bo_cham, "kenh": kenh, "ma_goi": ma_goi,
          "ung_vien": str(ung_vien), "diem": round(d, 3), "chon": bool(chon), "nguon": nguon,
          "luc": luc or time.strftime("%Y-%m-%d %H:%M:%S")}
    if phu:
        ra["phu"] = {k: v for k, v in phu.items() if v is not None}
    if trong_so is not None:
        ra["trong_so"] = round(float(trong_so), 3)
    return ra


def _noi(goc: str, dong: Sequence[Dict[str, Any]]) -> int:
    """Nối các dòng CHƯA có khoá (hoặc khác «được chọn»/điểm so dòng đang có) vào sổ. Trả số dòng mới."""
    if not dong:
        return 0
    co = {x["khoa"]: x for x in doc_so_cai(goc)}
    moi = []
    for d in dong:
        if d and _khac(co.get(d["khoa"]), d):
            co[d["khoa"]] = d
            moi.append(d)
    if not moi:
        return 0
    p = duong_so_cai(goc)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "a", encoding="utf-8", newline="\n") as tep:
        for d in moi:
            tep.write(json.dumps(d, ensure_ascii=False) + "\n")
    return len(moi)


def ghi(goc: str, bo_cham: str, kenh: str, ma_goi: str, ung_vien: Sequence[Dict[str, Any]], *,
        trong_so: Optional[float] = None) -> int:
    """Nơi chọn ghi THẲNG: `ung_vien` = `[{id, diem, chon, phu?}]`. Không bao giờ ném lỗi. Trả số dòng mới."""
    try:
        dong = [dong_so_cai(bo_cham, kenh, ma_goi, u.get("id"), u.get("diem"), chon=bool(u.get("chon")),
                            phu=u.get("phu"), trong_so=trong_so) for u in ung_vien or () if isinstance(u, dict)]
        return _noi(goc, [d for d in dong if d])
    except Exception:  # noqa: BLE001 — sổ hỏng không bao giờ làm hỏng nơi chọn
        return 0


def _chu(i: int) -> str:
    return chr(65 + i)


def _dong_chon_chu(bo_cham: str, kenh: str, ma: str, diem: Any, chon_chu: str, luc: str,
                   phu: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if not isinstance(diem, dict) or not chon_chu:
        return []
    ra = []
    for k, v in diem.items():
        d = dong_so_cai(bo_cham, kenh, ma, str(k).upper(), v, chon=str(k).upper() == chon_chu.upper(),
                        phu=phu if str(k).upper() == chon_chu.upper() else None, nguon="bu", luc=luc)
        if d:
            ra.append(d)
    return ra


_RE_THUMB = re.compile(r"thumb_(\d+)\.", re.I)


def _mau_thang(tm: str, dem: Dict[str, List[Dict[str, float]]]) -> List[Dict[str, float]]:
    """Số đo màu các bìa thắng trong thư mục (đệm theo thư mục). Hỏng → []."""
    if tm not in dem:
        ra: List[Dict[str, float]] = []
        try:
            from . import bia_lo  # noqa: PLC0415
            for b in bia_lo.bia_thu_muc(tm, toi_da=99) if tm and os.path.isdir(tm) else []:
                try:
                    ra.append(bia_lo.do_mau(b["tep"]))
                except (OSError, ValueError):
                    continue
        except Exception:  # noqa: BLE001
            ra = []
        dem[tm] = ra
    return dem[tm]


def _bu_mot(goc: str, kenh: str, ma: str, hs: Dict[str, Any],
            dem_mau: Optional[Dict[str, List[Dict[str, float]]]] = None) -> List[Dict[str, Any]]:
    """Dòng sổ cái suy từ MỘT hồ sơ video (+ `xep-hang.json` của lượt nếu thư mục còn — chỉ đọc)."""
    luc = str(hs.get("tao_luc") or "")[:19].replace("T", " ")
    ra: List[Dict[str, Any]] = []
    th = hs.get("thumbnail") if isinstance(hs.get("thumbnail"), dict) else {}
    luot = str(hs.get("luot") or "")
    xh = _doc_json(os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "7-thumbnail", "_lo", "xep-hang.json")) \
        if luot else None
    if isinstance(xh, dict) and xh.get("top"):
        m = _RE_THUMB.search(str(th.get("tep") or ""))
        i_chon = int(m.group(1)) - 1 if m else 0
        for i, u in enumerate(xh.get("top") or []):
            if not isinstance(u, dict):
                continue
            chon = i == i_chon
            d = dong_so_cai("bia_lo", kenh, ma, u.get("ma") or i + 1, u.get("tong"), chon=chon, nguon="bu", luc=luc,
                            phu={"hang_2": u.get("hang_2"), **{k: v for k, v in (u.get("diem") or {}).items()}})
            if d:
                ra.append(d)
            b = dong_so_cai("bia_lo_bam", kenh, ma, u.get("ma") or i + 1, (u.get("diem") or {}).get("bam_nhu_thang"),
                            chon=chon, nguon="bu", luc=luc)
            if b:
                ra.append(b)
            # tiên nghiệm máy của tấm: màu lúc chấm so bìa thắng HIỆN có trong thư mục mẫu của lô (xấp xỉ)
            tn = (u.get("hieu_chuan") or {}).get("tien_nghiem")
            if tn is None and dem_mau is not None and isinstance(u.get("mau_do"), dict):
                tn = tien_nghiem_mau(u["mau_do"], _mau_thang(str(xh.get("thu_muc_mau") or ""), dem_mau))
            m_ = dong_so_cai("bia_mau", kenh, ma, u.get("ma") or i + 1, tn, chon=chon, nguon="bu", luc=luc)
            if m_:
                ra.append(m_)
    elif th.get("diem_giam_khao") is not None:
        bo = "bia_lo" if str(th.get("kieu") or "") == "bia_lo" else "bia"
        d = dong_so_cai(bo, kenh, ma, th.get("tep") or "chon", th.get("diem_giam_khao"), chon=True, nguon="bu",
                        luc=luc, phu={"kieu": th.get("kieu"), "chon_boi": th.get("chon_boi")})
        if d:
            ra.append(d)
    tc = hs.get("tieu_de_cham") if isinstance(hs.get("tieu_de_cham"), dict) else {}
    if isinstance(tc.get("chon"), int) and isinstance(tc.get("diem"), dict):
        uv = tc.get("ung_vien") or []
        ten = str((uv[tc["chon"]] or {}).get("ten") or "") if 0 <= tc["chon"] < len(uv) else ""
        ra += _dong_chon_chu("tieu_de", kenh, ma, tc["diem"], _chu(tc["chon"]), luc, phu={"ten": ten})
    kb = hs.get("kich_ban") if isinstance(hs.get("kich_ban"), dict) else {}
    ra += _dong_chon_chu("kich_ban", kenh, ma, kb.get("diem"), str(kb.get("ban_chon") or ""), luc)
    hn = kb.get("hook_nhan") if isinstance(kb.get("hook_nhan"), dict) else {}
    ra += _dong_chon_chu("hook", kenh, ma, kb.get("hook_diem"), str(kb.get("hook_chon") or ""), luc,
                         phu={"nhan": hn.get("hook"), "thu_nghiem": (hn.get("thu_nghiem") or {}).get("id")})
    ac = hs.get("anh_canh") if isinstance(hs.get("anh_canh"), dict) else {}
    d = dong_so_cai("anh_canh", kenh, ma, "tb", ac.get("diem_tb"), chon=True, nguon="bu", luc=luc,
                    phu={"so_canh": ac.get("so_canh")})
    if d:
        ra.append(d)
    return ra + _dong_gia_tri(goc, kenh, ma, hs, luc)


def _dong_gia_tri(goc: str, kenh: str, ma: str, hs: Dict[str, Any], luc: str) -> List[Dict[str, Any]]:
    """G2 (20/10/2026): điểm hàm giá trị học máy (`core/gia_tri`, mô hình HIỆN HÀNH) của tiêu đề ĐƯỢC CHỌN
    (`gia_tri_tieu_de`) và của tiêu đề NGUỒN — ứng viên «đối chứng» = đề tài (`gia_tri_de_tai`). Mô hình học trên
    video ĐỐI THỦ (không có video của ta) nên chấm lại video cũ không rò nhãn. Chưa có mô hình → []."""
    try:
        from . import gia_tri  # noqa: PLC0415
        mh = gia_tri.nap(goc)
        if mh is None:
            return []
        tc = hs.get("tieu_de_cham") if isinstance(hs.get("tieu_de_cham"), dict) else {}
        uv = [u for u in tc.get("ung_vien") or [] if isinstance(u, dict)]
        nguon = next((str(u.get("tieu_de") or "") for u in uv if u.get("ten") == LOAI_TD[0]), "")
        td = str(hs.get("tieu_de") or "")
        diem = gia_tri.du_doan_nhieu(goc, [td, nguon], dai_giay=_so(hs.get("thoi_luong_giay")), mh=mh)
        tep = str((mh.get("hien_hanh") or {}).get("tep") or "")
        ra = []
        for bo, chu, p in (("gia_tri_tieu_de", td, diem[0]), ("gia_tri_de_tai", nguon, diem[1])):
            d = dong_so_cai(bo, kenh, ma, "chon" if bo == "gia_tri_tieu_de" else "nguon", p, chon=True,
                            nguon="mo-hinh", luc=luc, phu={"mo_hinh": tep}) if chu else None
            if d:
                ra.append(d)
        return ra
    except Exception:  # noqa: BLE001 — hàm giá trị hỏng không làm hỏng sổ cái
        return []


def _bu_bien_tap(goc: str, kenh: str) -> List[Dict[str, Any]]:
    du = _doc_json(os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "bien-tap", "brier.json")) or {}
    ra = []
    for x in du.get("chi_tiet") or []:
        if isinstance(x, dict) and x.get("ma_goi"):
            d = dong_so_cai("bien_tap", kenh, str(x["ma_goi"]), x.get("nguon") or "nguon", x.get("p"), chon=True,
                            nguon="bu", luc=str(du.get("cap_nhat_luc") or "")[:19].replace("T", " "),
                            phu={"hang": x.get("hang")})
            if d:
                ra.append(d)
    return ra


def gom(goc: str, kenh_ds: Optional[Sequence[str]] = None, *, ghi_dia: bool = True) -> Tuple[List[Dict[str, Any]], int]:
    """Bù sổ cái từ hồ sơ video + `xep-hang.json` + sổ Brier. Trả (mọi dòng sổ sau bù, số dòng mới/sửa).
    Dòng bù bìa có «được chọn» khác dòng ghi thẳng (cổng chữ đổi tấm sau khi lô chọn) → dòng bù thắng.
    `ghi_dia=False`: không ghi (chạy thử) — trả sổ hiện có + dòng bù trong bộ nhớ."""
    co = {x["khoa"]: x for x in doc_so_cai(goc)}
    moi: List[Dict[str, Any]] = []
    dem_mau: Dict[str, List[Dict[str, float]]] = {}
    for k in kenh_ds if kenh_ds is not None else kenh_hoc(goc):
        bu = [d for ma, hs in ho_so_kenh(goc, k).items() for d in _bu_mot(goc, k, ma, hs, dem_mau)]
        for d in bu + _bu_bien_tap(goc, k):
            cu = co.get(d["khoa"])
            if cu is None or ((d["bo_cham"].startswith("bia") or d["bo_cham"] in BO_CHAM_MO_HINH) and _khac(cu, d)):
                co[d["khoa"]] = d
                moi.append(d)
    if ghi_dia and moi:
        _noi(goc, moi)
    return list(co.values()), len(moi)


# ── 2) Kết quả thật ─────────────────────────────────────────────────────────


def _bang(goc: str, kenh: str, bay: _dt.datetime) -> Dict[str, Dict[str, Any]]:
    """Bảng Studio của kênh (bản chụp mới nhất, đã lọc video đời trước): `{vid: {tuoi, imp, ctr, avd_pct}}`."""
    p = os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv")
    try:
        with io.open(p, encoding="utf-8-sig") as tep:
            hang = list(csv.DictReader(tep))
    except OSError:
        return {}
    try:
        from .chi_so_ytb import loc_video as _loc  # noqa: PLC0415
        hang = _loc.loc_hang_bang(_loc.moc_cua_thu_muc(os.path.dirname(os.path.dirname(p))), hang)
    except Exception:  # noqa: BLE001
        pass
    from .bia_du_lieu import _tuoi  # noqa: PLC0415
    ra: Dict[str, Dict[str, Any]] = {}
    for d in hang:
        vid = str(d.get("Mã video") or "").strip()
        if vid and vid not in ra:
            ra[vid] = {"tuoi": _tuoi(d, bay), "imp": _so(d.get("Lượt hiển thị")) or 0.0,
                       "ctr": _so(d.get("Tỷ lệ bấm")), "avd_pct": _so(d.get("% độ dài"))}
    return ra


def _giu_30s(goc: str, kenh: str, vid: str) -> Optional[float]:
    """% người xem còn lại ở 0:30 — bản chụp muộn nhất có `retention.xlsx` (bộ đọc của khám nghiệm)."""
    try:
        from .chien_luoc import bai_hoc  # noqa: PLC0415
        r, dai = bai_hoc._duong_giu_chan(os.path.join(goc, "CHANNEL", kenh, "chi-so", vid))  # noqa: SLF001
        return _so(bai_hoc.do_duong_giu_chan(r, dai).get("giu_30s"))
    except Exception:  # noqa: BLE001
        return None


def _ctr_truoc_sua(hs: Dict[str, Any]) -> Optional[Tuple[float, float, str]]:
    """Bìa/tiêu đề đã sửa trên Studio: (CTR, hiển thị, mốc) của bản chụp ≥ 36 giờ TRƯỚC lần sửa đầu (≥ 1.000 hiển
    thị); không có → số `moc_truoc` của lần sửa; vẫn không → None (bỏ video khỏi mẫu CTR)."""
    sua = sorted(str(x.get("luc") or "") for x in hs.get("lich_su_sua") or []
                 if isinstance(x, dict) and x.get("loai") in ("bia", "tieu_de"))
    dau = sua[0].replace("T", " ") if sua else ""
    tot: Optional[Tuple[float, float, str]] = None
    for moc, c in (hs.get("chi_so") or {}).items():
        if not isinstance(c, dict):
            continue
        imp, ctr, gio = _so(c.get("impressions")), _so(c.get("ctr")), _so(c.get("moc_gio_that"))
        if imp is None or ctr is None or imp < IMP_TOI_THIEU or (gio is not None and gio < 36):
            continue
        if dau and str(c.get("luc_chup") or "") >= dau[:16]:
            continue
        if tot is None or imp > tot[1]:
            tot = (ctr, imp, str(moc))
    if tot:
        return tot
    for x in hs.get("lich_su_sua") or []:
        mt = (x or {}).get("moc_truoc") if isinstance(x, dict) else None
        if isinstance(mt, dict) and (_so(mt.get("impressions")) or 0) >= IMP_TOI_THIEU and _so(mt.get("ctr")) is not None:
            return float(mt["ctr"]), float(mt["impressions"]), "truoc-sua"
    return None


def ket_qua_kenh(goc: str, kenh: str, bay: Optional[_dt.datetime] = None, *,
                 ho_so: Optional[Dict[str, Dict[str, Any]]] = None, giu: bool = True) -> Dict[str, Dict[str, Any]]:
    """`{mã gói: {video_id, ctr, imp, ctr_nguon, avd_pct, giu_30s, thang, pv}}` — kết quả THẬT của video máy làm."""
    bay = bay or _dt.datetime.now()
    hs_ds = ho_so if ho_so is not None else ho_so_kenh(goc, kenh)
    bang = _bang(goc, kenh, bay)
    try:
        from . import thuoc_thang  # noqa: PLC0415
        nhan = thuoc_thang.danh_gia_kenh(goc, kenh, bay_gio=bay)
    except Exception:  # noqa: BLE001
        nhan = {}
    ra: Dict[str, Dict[str, Any]] = {}
    for ma, hs in hs_ds.items():
        vid = str(hs.get("video_id") or "")
        if not vid:
            continue
        r = bang.get(vid) or {}
        tuoi = _so(r.get("tuoi"))
        moi = hs.get("so_lieu_moi_nhat") if isinstance(hs.get("so_lieu_moi_nhat"), dict) else {}
        k: Dict[str, Any] = {"video_id": vid, "tuoi": tuoi}
        da_sua = any(isinstance(x, dict) and x.get("loai") in ("bia", "tieu_de") for x in hs.get("lich_su_sua") or [])
        if da_sua:
            t = _ctr_truoc_sua(hs)
            if t:
                k.update(ctr=t[0], imp=t[1], ctr_nguon=t[2])
        elif tuoi is not None and tuoi >= TUOI_TOI_THIEU and float(r.get("imp") or 0) >= IMP_TOI_THIEU \
                and r.get("ctr") is not None:
            k.update(ctr=float(r["ctr"]), imp=float(r["imp"]), ctr_nguon="bang")
        elif (_so(moi.get("moc_gio_that")) or 0) >= TUOI_TOI_THIEU and (_so(moi.get("impressions")) or 0) >= \
                IMP_TOI_THIEU and _so(moi.get("ctr")) is not None:
            k.update(ctr=float(moi["ctr"]), imp=float(moi["impressions"]), ctr_nguon="ho-so")
        if tuoi is not None and tuoi >= TUOI_TOI_THIEU and r.get("avd_pct") is not None:
            k["avd_pct"] = float(r["avd_pct"])
        elif (_so(moi.get("moc_gio_that")) or 0) >= TUOI_TOI_THIEU and _so(moi.get("avd_pct")) is not None:
            k["avd_pct"] = float(moi["avd_pct"])
        if giu:
            g = _giu_30s(goc, kenh, vid)
            if g is not None:
                k["giu_30s"] = g
        n = nhan.get(vid)
        if n is not None and getattr(n, "nhan", "") in ("thang", "trung_binh", "truot"):
            k["thang"] = 1.0 if n.nhan == "thang" else 0.0
            k["nhan"] = n.nhan
            k["pv"] = getattr(n, "phan_vi", None)
        ra[ma] = k
    return ra


# ── 3) Hiệu chuẩn ───────────────────────────────────────────────────────────


def _muc(rho: Optional[float], n: int) -> Tuple[str, float]:
    if rho is None or n < N_TOI_THIEU:
        return "chua_du", 1.0
    if rho < RHO_KHONG:
        return "khong_du_bao", W_PHU_QUYET
    if rho >= RHO_DU:
        return "du_bao", 1.0
    return "yeu", round(W_PHU_QUYET + (1.0 - W_PHU_QUYET) * (rho - RHO_KHONG) / (RHO_DU - RHO_KHONG), 3)


def _cap(dong: Sequence[Dict[str, Any]], kq: Dict[str, Dict[str, Dict[str, Any]]], ket: str,
         chuan: Optional[Dict[str, Dict[str, Optional[float]]]] = None) -> List[Tuple[float, float, float, str]]:
    """(điểm, kết quả, trọng số, kênh) của các dòng ĐƯỢC CHỌN có kết quả `ket`. `chuan` (gộp): kết quả chia/trừ trung
    vị kênh — CTR chia (tỉ lệ), % trừ (điểm phần trăm), thắng giữ nguyên."""
    ra = []
    for d in dong:
        if not d.get("chon"):
            continue
        k = (kq.get(d["kenh"]) or {}).get(d["ma_goi"]) or {}
        y = _so(k.get(ket))
        if y is None:
            continue
        w = math.sqrt(float(k.get("imp") or 0)) if ket == "ctr" else 1.0
        if chuan is not None and ket not in ("thang", "pv"):     # phân vị thước chung đã theo chính kênh
            tv = (chuan.get(d["kenh"]) or {}).get(ket)
            if tv is None or (ket == "ctr" and tv <= 0):
                continue
            y = y / tv if ket == "ctr" else y - tv
        ra.append((float(d["diem"]), y, w, d["kenh"]))
    return ra


def _do(cap: Sequence[Tuple[float, float, float, str]], ket: str) -> Dict[str, Any]:
    a, b, w = [c[0] for c in cap], [c[1] for c in cap], [c[2] for c in cap]
    rho = spearman(a, b)
    ra = {"ket": ket, "n": len(cap), "rho": rho}
    if ket == "ctr":
        ra["rho_w"] = spearman(a, b, w)
    ra["rho_dung"] = ra.get("rho_w") if ket == "ctr" and ra.get("rho_w") is not None else rho
    return ra


def hieu_chuan(goc: str, dong: Sequence[Dict[str, Any]], kq: Dict[str, Dict[str, Dict[str, Any]]],
               kenh_ds: Sequence[str]) -> Dict[str, Any]:
    """Bảng (bộ chấm × kênh + gộp) và trọng số. Kết quả của bộ chấm có nhiều kết quả: lấy kết quả rho TỐT nhất (đủ
    mẫu) — bộ chấm chỉ bị co quyền khi KHÔNG kết quả nào nó phải dự báo được dự báo."""
    chuan = {k: {"ctr": _tv(x.get("ctr") for x in (kq.get(k) or {}).values()),
                 "avd_pct": _tv(x.get("avd_pct") for x in (kq.get(k) or {}).values()),
                 "giu_30s": _tv(x.get("giu_30s") for x in (kq.get(k) or {}).values())} for k in kenh_ds}
    theo_bo: Dict[str, List[Dict[str, Any]]] = {}
    for d in dong:
        if d.get("kenh") in kenh_ds and d.get("bo_cham") in BO_CHAM:
            theo_bo.setdefault(d["bo_cham"], []).append(d)
    bang: List[Dict[str, Any]] = []
    chung: Dict[str, Dict[str, Any]] = {}
    rieng: Dict[str, Dict[str, Dict[str, Any]]] = {k: {} for k in kenh_ds}

    def chon_tot(ds: List[Dict[str, Any]]) -> Dict[str, Any]:
        du = [x for x in ds if x["n"] >= N_TOI_THIEU and x["rho_dung"] is not None]
        if du:
            return max(du, key=lambda x: x["rho_dung"])
        return max(ds, key=lambda x: x["n"]) if ds else {"n": 0, "rho_dung": None}

    for bo, ds in sorted(theo_bo.items()):
        ket_ds = BO_CHAM[bo][1]
        do_chung = [_do(_cap(ds, kq, ket, chuan), ket) for ket in ket_ds]
        for x in do_chung:
            bang.append(dict(x, bo_cham=bo, kenh="(gộp)"))
        t = chon_tot(do_chung)
        muc, w = _muc(t.get("rho_dung"), int(t.get("n") or 0))
        chung[bo] = {"w": w, "muc": muc, "rho": t.get("rho_dung"), "n": int(t.get("n") or 0), "ket": t.get("ket"),
                     "nguon": "chung"}
        for k in kenh_ds:
            dk = [d for d in ds if d["kenh"] == k]
            if not dk:
                continue
            do_k = [_do(_cap(dk, kq, ket), ket) for ket in ket_ds]
            for x in do_k:
                bang.append(dict(x, bo_cham=bo, kenh=k))
            t = chon_tot(do_k)
            muc, w = _muc(t.get("rho_dung"), int(t.get("n") or 0))
            if muc == "chua_du":
                c = chung[bo]
                rieng[k][bo] = dict(c, n_kenh=int(t.get("n") or 0), rho_kenh=t.get("rho_dung"),
                                    nguon="chung" if c["muc"] != "chua_du" else "mac_dinh")
            else:
                rieng[k][bo] = {"w": w, "muc": muc, "rho": t.get("rho_dung"), "n": int(t.get("n") or 0),
                                "ket": t.get("ket"), "nguon": "kenh"}
    return {"bang": bang, "trong_so": {"chung": chung, "kenh": rieng,
                                       "tien_nghiem": {"tieu_de": tien_nghiem_tieu_de(dong, kq, chuan)}},
            "chuan": chuan}


# ── 4) Trọng số cho nơi chọn ────────────────────────────────────────────────

_DEM_TS: Dict[str, Tuple[float, Any]] = {}


def duong_trong_so(goc: str) -> str:
    return os.path.join(thu_muc(goc), TEP_TRONG_SO)


def _doc_trong_so(goc: str) -> Dict[str, Any]:
    p = duong_trong_so(goc)
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return {}
    cu = _DEM_TS.get(p)
    if cu and cu[0] == mt:
        return cu[1]
    du = _doc_json(p) or {}
    _DEM_TS[p] = (mt, du)
    return du


def trong_so(goc: str, kenh: str, bo_cham: str) -> Dict[str, Any]:
    """`{w, muc, rho, n, nguon, bo_cham}` của bộ chấm ở kênh — chưa đủ mẫu thì đi chuỗi lùi `LUI`; không có gì → w=1
    (`mac_dinh`, giữ hành vi cũ). Không bao giờ ném lỗi."""
    try:
        du = _doc_trong_so(goc)
        for bo in (bo_cham,) + tuple(LUI.get(bo_cham, ())):
            x = ((du.get("kenh") or {}).get(kenh) or {}).get(bo) or (du.get("chung") or {}).get(bo)
            if isinstance(x, dict) and x.get("muc") not in (None, "chua_du") and x.get("nguon") != "mac_dinh":
                return dict(x, bo_cham=bo, w=float(x.get("w") if x.get("w") is not None else 1.0))
    except Exception:  # noqa: BLE001
        pass
    return {"w": 1.0, "muc": "mac_dinh", "nguon": "mac_dinh", "bo_cham": bo_cham}


def loai_td(ten: Any) -> str:
    t = str(ten or "")
    return t if t in LOAI_TD[:2] else "bản N"


def tien_nghiem_tieu_de(dong: Sequence[Dict[str, Any]], kq: Dict[str, Dict[str, Dict[str, Any]]],
                        chuan: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Any]:
    """`{loại: {n, ti_le, co, he}}`: CTR thật (÷ trung vị kênh) khi loại ứng viên ấy được chọn, co về 1
    (`CO_TIEN_NGHIEM`); `he` = tỉ lệ đã co ÷ tỉ lệ đã co lớn nhất (0..1]."""
    nhom: Dict[str, List[float]] = {}
    for d in dong:
        if d.get("bo_cham") != "tieu_de" or not d.get("chon"):
            continue
        x = (kq.get(d["kenh"]) or {}).get(d["ma_goi"]) or {}
        tv = (chuan.get(d["kenh"]) or {}).get("ctr")
        if x.get("ctr") is None or not tv:
            continue
        nhom.setdefault(loai_td((d.get("phu") or {}).get("ten")), []).append(float(x["ctr"]) / float(tv))
    ra: Dict[str, Any] = {}
    for l in LOAI_TD:
        v = nhom.get(l) or []
        r = float(statistics.median(v)) if v else 1.0
        # < `N_TOI_THIEU` lần chọn: TRUNG TÍNH (1) — thiên lệch chọn mẫu + n nhỏ; nhất là không được đẩy «đối chứng»
        # (tiêu đề nguồn nguyên văn) lên chỉ vì vài video (rủi ro chép).
        co = (len(v) * r + CO_TIEN_NGHIEM) / (len(v) + CO_TIEN_NGHIEM) if len(v) >= N_TOI_THIEU else 1.0
        ra[l] = {"n": len(v), "ti_le": round(r, 3), "co": round(co, 3)}
    cao = max(x["co"] for x in ra.values()) or 1.0
    for x in ra.values():
        x["he"] = round(x["co"] / cao, 3)
    return ra


def tien_nghiem_luu(goc: str, ten: str) -> Dict[str, Any]:
    """Tiên nghiệm đã lưu ở lần hiệu chuẩn gần nhất (`trong-so.json: tien_nghiem.<ten>`). Không có → {}."""
    try:
        return dict(((_doc_trong_so(goc).get("tien_nghiem") or {}).get(ten)) or {})
    except Exception:  # noqa: BLE001
        return {}


def chon_tieu_de(ten_ban: Sequence[str], diem: Dict[str, Any], chon_gk: int, w: float,
                 he_so: Optional[Dict[int, float]] = None,
                 tien_nghiem: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
    """Chọn tiêu đề khi giám khảo bị co quyền (w < 1): ứng viên điểm ≤ `TD_PHU_QUYET` bị PHỦ QUYẾT; còn lại xếp theo
    w × điểm/10 + (1 − w) × tiên nghiệm (loại ứng viên theo CTR thật — `tien_nghiem_tieu_de` — × hệ số Thompson kiểu
    tiêu đề, cũng từ kết quả thật). w ≥ 1 → giữ nguyên lựa chọn của giám khảo. Trả (chỉ số, ghi chép)."""
    n = len(ten_ban)
    if w >= 1.0 or n < 2:
        return chon_gk, {}
    dg = {i: _so((diem or {}).get(_chu(i))) for i in range(n)}
    con = [i for i in range(n) if dg[i] is None or dg[i] > TD_PHU_QUYET] or list(range(n))
    tong: Dict[int, float] = {}
    for i in con:
        he_loai = _so(((tien_nghiem or {}).get(loai_td(ten_ban[i])) or {}).get("he"))
        tn = (he_loai if he_loai is not None else 1.0) * float((he_so or {}).get(i, 1.0))
        g = (dg[i] if dg[i] is not None else 5.0) / 10.0
        tong[i] = round(w * g + (1.0 - w) * tn, 4)
    moi = max(con, key=lambda i: (tong[i], i == chon_gk, -i))
    return moi, {"w": round(w, 3), "chon_giam_khao": chon_gk, "chon": moi, "tong": {_chu(i): v for i, v in tong.items()},
                 "phu_quyet": [_chu(i) for i in range(n) if i not in con]}


def tien_nghiem_mau(do: Optional[Dict[str, float]], thang: Sequence[Dict[str, float]]) -> Optional[float]:
    """Tiên nghiệm MÁY của một bìa: trung bình (3 số đo màu) tỉ lệ bìa thắng thật của kênh có số đo ≤ số đo của tấm —
    0..1, càng cao càng «đậm như bìa thắng». Thiếu số đo / < 2 bìa thắng → None."""
    if not do or len(thang) < 2:
        return None
    phan = []
    for k in ("bao_hoa", "tuong_phan", "dai_sang"):
        x = _so(do.get(k))
        ds = [float(t[k]) for t in thang if _so(t.get(k)) is not None]
        if x is None or len(ds) < 2:
            continue
        phan.append(sum(1 for v in ds if v <= x) / float(len(ds)))
    return round(sum(phan) / len(phan), 4) if phan else None


def xep_bia(da_cham: Sequence[Dict[str, Any]], w: float, tien_nghiem: Callable[[Dict[str, Any]], Optional[float]]
            ) -> List[Dict[str, Any]]:
    """Xếp lại các tấm ĐÃ chấm (thứ tự đầu vào = thứ hạng giám khảo) khi w < 1: w × hạng giám khảo (0..1) + (1 − w) ×
    hạng tiên nghiệm máy (0..1). Tấm không có tiên nghiệm đứng giữa. Ghi `u["hieu_chuan"]`. w ≥ 1 → giữ nguyên."""
    ds = list(da_cham)
    if w >= 1.0 or len(ds) < 2:
        return ds
    n = len(ds)
    tn = [tien_nghiem(u) for u in ds]
    co = [x for x in tn if x is not None]
    hang_tn = _hang([x if x is not None else (statistics.median(co) if co else 0.0) for x in tn])
    tong = []
    for i, u in enumerate(ds):
        g = 1.0 - i / float(n - 1)
        p = hang_tn[i] / float(n - 1)
        t = round(w * g + (1.0 - w) * p, 4)
        u["hieu_chuan"] = {"w": round(w, 3), "hang_giam_khao": i + 1, "tien_nghiem": tn[i], "tong": t}
        tong.append((t, -i, u))
    return [u for _t, _i, u in sorted(tong, key=lambda x: (x[0], x[1]), reverse=True)]


# ── 5) Hook ↔ giữ chân 0:30 ─────────────────────────────────────────────────


def do_hook(goc: str, kq: Dict[str, Dict[str, Dict[str, Any]]], kenh_ds: Sequence[str]) -> Dict[str, Any]:
    """% còn lại ở 0:30 theo nhãn hook so trung vị kênh + các lần THỬ hook của bộ não (gói nào, 0:30 bao nhiêu)."""
    ra: Dict[str, Any] = {"kenh": {}, "thu": []}
    hs_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for k in kenh_ds:
        hs = hs_cache.setdefault(k, ho_so_kenh(goc, k))
        tat_ca = [x.get("giu_30s") for x in (kq.get(k) or {}).values() if x.get("giu_30s") is not None]
        nen = _tv(tat_ca)
        nhan: Dict[str, List[float]] = {}
        for ma, x in (kq.get(k) or {}).items():
            hn = ((hs.get(ma) or {}).get("kich_ban") or {}).get("hook_nhan") or {}
            if x.get("giu_30s") is not None and hn.get("hook"):
                nhan.setdefault(str(hn["hook"]), []).append(float(x["giu_30s"]))
        ra["kenh"][k] = {"nen": nen, "n_nen": len(tat_ca), "nhan": {
            h: {"n": len(v), "tv": _tv(v), "lech": round(_tv(v) - nen, 1) if nen is not None else None}
            for h, v in sorted(nhan.items())}}
    try:
        from . import nao  # noqa: PLC0415
        hd = nao.doc_hanh_dong(goc)
    except Exception:  # noqa: BLE001
        hd = []
    for d in hd:
        ts = d.get("tham_so") or {}
        if d.get("lenh") != "thu" or ts.get("truc") != "hook" or ts.get("kenh") not in kenh_ds:
            continue
        k = ts["kenh"]
        goi = []
        for ma in ts.get("goi") or []:
            x = (kq.get(k) or {}).get(ma) or {}
            hn = ((hs_cache.get(k, {}).get(ma) or {}).get("kich_ban") or {}).get("hook_nhan") or {}
            goi.append({"ma_goi": ma, "giu_30s": x.get("giu_30s"), "nhan": hn.get("hook")})
        ra["thu"].append({"id": d.get("id"), "kenh": k, "gia_tri": ts.get("gia_tri"), "trang_thai": d.get("trang_thai"),
                          "da_dung": int(ts.get("da_dung") or 0), "so_video": int(ts.get("so_video") or 0),
                          "kiem_ngay": d.get("kiem_ngay"), "goi": goi, "nen": ra["kenh"].get(k, {}).get("nen")})
    return ra


def giu_30s_goi(goc: str, kenh: str, ma_goi: str) -> Optional[float]:
    """0:30 của MỘT gói (cho `nao.ket_qua_goi`)."""
    hs = _doc_json(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", ma_goi + ".json")) or {}
    return _giu_30s(goc, kenh, str(hs.get("video_id"))) if hs.get("video_id") else None


def nen_giu_30s(goc: str, kenh: str) -> Optional[float]:
    """Trung vị 0:30 của kênh theo lần hiệu chuẩn gần nhất (rẻ — không đọc lại đường giữ chân)."""
    p = moi_nhat(goc)
    du = _doc_json(p) if p else None
    return (((du or {}).get("hook") or {}).get("kenh") or {}).get(kenh, {}).get("nen")


# ── 6) Bài học có giúp không ────────────────────────────────────────────────


def _goi_cua_quyet_dinh(goc: str, qd: str, hs_moi: Dict[str, Dict[str, Dict[str, Any]]]) -> List[Tuple[str, str]]:
    """`<mã gói>:<khâu>:<ngày>` → [(kênh, mã gói)]; `<kênh>:bien_tap:<ngày>` → gói bàn giao của kênh hôm đó (sổ lượt)."""
    phan = str(qd or "").split(":")
    if len(phan) < 2:
        return []
    dau, ngay = phan[0], phan[-1]
    m = _RE_GOI.match(dau)
    if m and m.group(1) in hs_moi and dau in hs_moi[m.group(1)]:
        return [(m.group(1), dau)]
    if dau in hs_moi:
        du = _doc_json(os.path.join(goc, "CHANNEL", dau, "tu-chay", ngay + ".json")) or {}
        return [(dau, str((r.get("ban_giao") or {}).get("ma_goi"))) for r in du.get("runs") or []
                if isinstance(r, dict) and (r.get("ban_giao") or {}).get("ma_goi")]
    return []


def bai_hoc_uplift(goc: str, kq: Dict[str, Dict[str, Dict[str, Any]]], kenh_ds: Sequence[str]) -> Dict[str, Any]:
    """Bảng `dung` × nhãn thắng: mỗi bộ phận (có bài / đối chứng / không bài nào khớp) + mỗi bài học đã dùng."""
    import sqlite3  # noqa: PLC0415
    p = os.path.join(goc, "nao", "bo-phan.db")
    ra: Dict[str, Any] = {"bo_phan": {}, "bai": {}, "n_dung": 0, "n_doi_chung": 0}
    if not os.path.isfile(p):
        return ra
    try:
        con = sqlite3.connect("file:{0}?mode=ro".format(p.replace("\\", "/")), uri=True, timeout=2)
        try:
            dong = con.execute("SELECT quyet_dinh, bo_phan, bai_hoc, doi_chung FROM dung").fetchall()
        finally:
            con.close()
    except Exception as loi:  # noqa: BLE001
        ra["loi"] = str(loi)[:120]
        return ra
    hs_moi = {k: ho_so_kenh(goc, k) for k in kenh_ds}
    ra["n_dung"], ra["n_doi_chung"] = len(dong), sum(1 for r in dong if r[3])
    for qd, bp, bai, dc in dong:
        try:
            ids = [str(x) for x in json.loads(bai or "[]")]
        except ValueError:
            ids = []
        nhom = "doi_chung" if dc else ("co_bai" if ids else "khong_bai")
        ket = [((kq.get(k) or {}).get(ma) or {}).get("thang") for k, ma in _goi_cua_quyet_dinh(goc, qd, hs_moi)]
        ket = [x for x in ket if x is not None]
        o = ra["bo_phan"].setdefault(bp, {})
        for g in ("co_bai", "doi_chung", "khong_bai"):
            o.setdefault(g, {"n_qd": 0, "n": 0, "thang": 0.0})
        o[nhom]["n_qd"] += 1
        o[nhom]["n"] += len(ket)
        o[nhom]["thang"] += sum(ket)
        if nhom == "co_bai":
            for i in ids:
                b = ra["bai"].setdefault(i, {"bo_phan": bp, "n_qd": 0, "n": 0, "thang": 0.0})
                b["n_qd"] += 1
                b["n"] += len(ket)
                b["thang"] += sum(ket)
    for bp, o in ra["bo_phan"].items():
        for g in o.values():
            g["ti_le"] = round(g["thang"] / g["n"], 3) if g["n"] else None
        a, c = o["co_bai"]["ti_le"], o["doi_chung"]["ti_le"]
        o["uplift"] = round(a - c, 3) if a is not None and c is not None else None
    for i, b in ra["bai"].items():
        b["ti_le"] = round(b["thang"] / b["n"], 3) if b["n"] else None
        dc = ra["bo_phan"].get(b["bo_phan"], {}).get("doi_chung") or {}
        b["uplift"] = round(b["ti_le"] - dc["ti_le"], 3) if b["ti_le"] is not None and dc.get("ti_le") is not None \
            else None
        du = b["n"] >= N_BAI_HOC and int(dc.get("n") or 0) >= N_BAI_HOC
        b["ket_luan"] = ("khong_giup" if du and (b["uplift"] or 0) <= 0 else "giup" if du else "chua_du")
        b["tu_rut"] = "/bai-hoc/BH-N" in i
    return ra


def nghi_bai_khong_giup(goc: str, ub: Dict[str, Any]) -> List[str]:
    """Bài học TỰ RÚT kết luận «không giúp» → trạng thái NGHỈ (không xoá), lịch sử + nhật ký bộ phận. Trả mã bài đã nghỉ."""
    can = [i for i, b in (ub.get("bai") or {}).items() if b.get("ket_luan") == "khong_giup" and b.get("tu_rut")]
    if not can:
        return []
    from .nao_bo_phan import _chung as ch, kho, ngu, no_ron  # noqa: PLC0415
    vault, luc, xong = ch.duong_vault(goc), ch.ngay_gio(time.time()), []
    con = kho.mo(goc, cho=2.0)
    try:
        for bp in sorted({ub["bai"][i]["bo_phan"] for i in can}):
            dong = []
            for b in no_ron.doc_bai_ngu(vault, bp):
                ma = "{0}/bai-hoc/{1}".format(bp, b.get("id"))
                if ma not in can or b.get("trang_thai") == ch.NGHI:
                    continue
                x = ub["bai"][ma]
                vi_sao = "hiệu chuẩn: có bài thắng {0:.0%} (n {1}) ≤ đối chứng {2:.0%} (n {3})".format(
                    x["ti_le"], x["n"], x["ti_le"] - x["uplift"], ub["bo_phan"][bp]["doi_chung"]["n"])
                b.setdefault("lich_su", ngu._lich_su(b.get("than") or "")).append(  # noqa: SLF001
                    "{0} nghỉ — {1}".format(luc, vi_sao))
                b["trang_thai"], b["cap_nhat"] = ch.NGHI, luc
                ngu.ghi_bai(con, vault, b)
                con.execute("UPDATE no_ron SET trang_thai = ? WHERE id = ?", (ch.NGHI, ma))
                dong.append("- nghỉ {0}: {1}".format(ma, vi_sao))
                xong.append(ma)
            ch.ghi_nhat_ky(vault, bp, luc + " — hiệu chuẩn bài học", dong)
        con.commit()
    finally:
        con.close()
    return xong


# ── 7) Lượt hiệu chuẩn tuần ─────────────────────────────────────────────────


def moi_nhat(goc: str) -> str:
    ds = sorted(glob.glob(os.path.join(thu_muc(goc), "????-??-??.json")))
    return ds[-1] if ds else ""


def can_chay(goc: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    bay = bay or _dt.datetime.now()
    if not kenh_hoc(goc):
        return False, "chưa kênh nào có hồ sơ video"
    p = moi_nhat(goc)
    if not p:
        return True, "chưa hiệu chuẩn lần nào"
    try:
        ngay = _dt.datetime.strptime(os.path.basename(p)[:10], "%Y-%m-%d")
    except ValueError:
        return True, "tệp hiệu chuẩn lạ"
    tuoi = (bay - ngay).days
    if tuoi >= NGAY_NHIP:
        return True, "lần trước {0} ({1} ngày)".format(ngay.date().isoformat(), tuoi)
    return False, "lần trước {0} ({1} ngày < {2})".format(ngay.date().isoformat(), tuoi, NGAY_NHIP)


def _tuan(bay: _dt.datetime) -> str:
    n, t, _ = bay.isocalendar()
    return "{0}-W{1:02d}".format(n, t)


def _ghi_nao_hook(goc: str, hk: Dict[str, Any], bay: _dt.datetime) -> int:
    """Sự kiện não bộ phận «kich-ban»: mỗi kênh × nhãn hook có số 0:30 (một lần/tuần) + mỗi lần thử hook."""
    try:
        from . import nao_bo_phan as nbp  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return 0
    n, tuan = 0, _tuan(bay)
    for k, o in (hk.get("kenh") or {}).items():
        for h, x in (o.get("nhan") or {}).items():
            if x.get("lech") is None:
                continue
            n += bool(nbp.ghi(goc, "kich-ban", "ket_qua", kenh=k, khoa="hieu-chuan-hook:{0}:{1}:{2}".format(k, h, tuan),
                              noi_dung="hook «{0}» — còn {1}% ở 0:30 (n {2}) so trung vị kênh {3}% ({4:+.1f} điểm)".format(
                                  h, x["tv"], x["n"], o["nen"], x["lech"]),
                              so={"hook": h, "n": x["n"], "giu_30s": x["tv"], "nen": o["nen"], "lech": x["lech"]},
                              nguon="hieu_chuan"))
    for t in hk.get("thu") or []:
        do = [g for g in t["goi"] if g.get("giu_30s") is not None]
        nd = "thử hook «{0}» {1}: {2}/{3} video{4}".format(
            t["gia_tri"], t["id"], t["da_dung"], t["so_video"],
            (" — 0:30: " + ", ".join("{0} {1}%".format(g["ma_goi"], g["giu_30s"]) for g in do) +
             " (kênh {0}%)".format(t.get("nen"))) if do else " — chưa có số giữ chân")
        n += bool(nbp.ghi(goc, "kich-ban", "ket_qua", kenh=t["kenh"], khoa="hieu-chuan-thu:{0}:{1}:{2}".format(
            t["id"], len(do), tuan), noi_dung=nd, so={"thu": t["id"], "goi": t["goi"], "nen": t.get("nen")},
            nguon="hieu_chuan"))
    return n


def chay(goc: str, *, thu: bool = False, bay: Optional[_dt.datetime] = None,
         kenh_ds: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Một lượt: bù sổ cái → kết quả thật → bảng + trọng số → hook → bài học. `thu=True`: CHỈ ĐỌC."""
    bay = bay or _dt.datetime.now()
    kenh_ds = list(kenh_ds) if kenh_ds is not None else kenh_hoc(goc)
    dong, n_moi = gom(goc, kenh_ds, ghi_dia=not thu)
    kq = {k: ket_qua_kenh(goc, k, bay) for k in kenh_ds}
    hc = hieu_chuan(goc, dong, kq, kenh_ds)
    hk = do_hook(goc, kq, kenh_ds)
    ub = bai_hoc_uplift(goc, kq, kenh_ds)
    bc: Dict[str, Any] = {"phien_ban": PHIEN_BAN, "luc": bay.strftime("%Y-%m-%d %H:%M:%S"), "ngay": bay.date().isoformat(),
                          "kenh_ds": kenh_ds, "so_cai": {"dong": len(dong), "moi": n_moi},
                          "luat": {"n_toi_thieu": N_TOI_THIEU, "rho_khong": RHO_KHONG, "rho_du": RHO_DU,
                                   "w_phu_quyet": W_PHU_QUYET, "n_bai_hoc": N_BAI_HOC},
                          "bang": hc["bang"], "trong_so": hc["trong_so"], "chuan": hc["chuan"], "hook": hk,
                          "bai_hoc": ub, "da_nghi": []}
    bc["tom_tat"] = tom_tat(bc)
    if not thu:
        _ghi_json(duong_trong_so(goc), dict(hc["trong_so"], luc=bc["luc"], phien_ban=PHIEN_BAN))
        try:
            bc["da_nghi"] = nghi_bai_khong_giup(goc, ub)
        except Exception as loi:  # noqa: BLE001
            bc["loi_nghi"] = str(loi)[:160]
        bc["su_kien_nao"] = _ghi_nao_hook(goc, hk, bay)
        _ghi_json(os.path.join(thu_muc(goc), bay.date().isoformat() + ".json"), bc)
    return bc


def tom_tat(bc: Dict[str, Any]) -> str:
    """Một dòng tiếng Việt cho báo cáo ngày."""
    ts = bc.get("trong_so") or {}
    khong, du = [], []
    for bo, x in sorted((ts.get("chung") or {}).items()):
        if x.get("muc") == "khong_du_bao":
            khong.append("{0} gộp (rho {1}, n {2})".format(bo, x.get("rho"), x.get("n")))
        elif x.get("muc") == "du_bao":
            du.append("{0} gộp".format(bo))
    for k, o in sorted((ts.get("kenh") or {}).items()):
        for bo, x in sorted(o.items()):
            if x.get("nguon") != "kenh":
                continue
            if x.get("muc") == "khong_du_bao":
                khong.append("{0} {1} (rho {2}, n {3})".format(bo, k, x.get("rho"), x.get("n")))
            elif x.get("muc") == "du_bao":
                du.append("{0} {1}".format(bo, k))
    phan = ["không dự báo → chỉ phủ quyết: " + ("; ".join(khong[:6]) + (" …" if len(khong) > 6 else "") if khong
                                                else "không có")]
    if du:
        phan.append("đủ tin: " + ", ".join(du[:6]))
    ub = bc.get("bai_hoc") or {}
    bp = ["{0} {1:+.0%} (n {2}/{3})".format(b, o["uplift"], o["co_bai"]["n"], o["doi_chung"]["n"])
          for b, o in sorted((ub.get("bo_phan") or {}).items()) if o.get("uplift") is not None
          and o["co_bai"]["n"] >= N_BAI_HOC and o["doi_chung"]["n"] >= N_BAI_HOC]
    phan.append("bài học vs đối chứng: " + (", ".join(bp) if bp else "chưa đủ video có nhãn (cần ≥ {0}/{0})".format(
        N_BAI_HOC)))
    if bc.get("da_nghi"):
        phan.append("đã nghỉ {0} bài không giúp".format(len(bc["da_nghi"])))
    return "Hiệu chuẩn bộ chấm ({0}): {1}".format(bc.get("ngay"), " · ".join(phan))


def dong_bao_cao(goc: str, bay: Optional[_dt.datetime] = None) -> List[str]:
    """Dòng cho báo cáo ngày: tóm tắt lần hiệu chuẩn gần nhất (+ cảnh báo khi quá 8 ngày chưa chạy)."""
    p = moi_nhat(goc)
    if not p:
        return ["- Hiệu chuẩn bộ chấm: chưa chạy lần nào (kỹ năng D22)"]
    du = _doc_json(p) or {}
    ra = ["- " + str(du.get("tom_tat") or tom_tat(du))]
    try:
        tuoi = ((bay or _dt.datetime.now()) - _dt.datetime.strptime(os.path.basename(p)[:10], "%Y-%m-%d")).days
        if tuoi > NGAY_NHIP + 1:
            ra.append("- Hiệu chuẩn bộ chấm CŨ {0} ngày — D22 không chạy?".format(tuoi))
    except ValueError:
        pass
    return ra


def in_bao_cao(bc: Dict[str, Any], in_ra: Callable[[str], None] = print) -> None:
    in_ra("HIỆU CHUẨN BỘ CHẤM — {0} · kênh: {1} · sổ cái {2} dòng (+{3} bù)".format(
        bc["luc"], ", ".join(bc["kenh_ds"]), bc["so_cai"]["dong"], bc["so_cai"]["moi"]))
    in_ra("  {0:<11} {1:<10} {2:<8} {3:>3} {4:>7} {5:>7}".format("bộ chấm", "kênh", "kết quả", "n", "rho", "rho_w"))
    for x in sorted(bc["bang"], key=lambda x: (x["bo_cham"], x["kenh"] != "(gộp)", x["kenh"], x["ket"])):
        if not x["n"]:
            continue
        in_ra("  {0:<11} {1:<10} {2:<8} {3:>3} {4:>7} {5:>7}".format(
            x["bo_cham"], x["kenh"], x["ket"], x["n"], "-" if x["rho"] is None else x["rho"],
            "" if x.get("rho_w") is None else x["rho_w"]))
    in_ra("  TRỌNG SỐ (gộp): " + "; ".join("{0}={1} {2}".format(b, x["w"], TEN_MUC.get(x["muc"], x["muc"]))
                                         for b, x in sorted(bc["trong_so"]["chung"].items())))
    tn = ((bc["trong_so"].get("tien_nghiem") or {}).get("tieu_de")) or {}
    if tn:
        in_ra("  TIÊN NGHIỆM tiêu đề (CTR ÷ trung vị kênh khi loại ấy được chọn): " + "; ".join(
            "{0} ×{1} n{2} → hệ {3}".format(l, x["ti_le"], x["n"], x["he"]) for l, x in tn.items()))
    for k, o in sorted(bc["trong_so"]["kenh"].items()):
        in_ra("  TRỌNG SỐ {0}: {1}".format(k, "; ".join("{0}={1} {2}/{3}".format(
            b, x["w"], TEN_MUC.get(x["muc"], x["muc"]), x.get("nguon")) for b, x in sorted(o.items()))))
    hk = bc.get("hook") or {}
    for k, o in sorted((hk.get("kenh") or {}).items()):
        if o.get("nhan"):
            in_ra("  HOOK {0}: kênh 0:30 {1}% (n {2}) · {3}".format(k, o.get("nen"), o.get("n_nen"), ", ".join(
                "{0} {1}% n{2} ({3:+.1f})".format(h, x["tv"], x["n"], x["lech"] or 0) for h, x in o["nhan"].items())))
    for t in hk.get("thu") or []:
        in_ra("  THỬ HOOK {0} {1}={2} [{3}] {4}/{5} video, gói: {6}".format(
            t["id"], t["kenh"], t["gia_tri"], t["trang_thai"], t["da_dung"], t["so_video"],
            ", ".join("{0} 0:30={1}".format(g["ma_goi"], g["giu_30s"]) for g in t["goi"]) or "(chưa có)"))
    ub = bc.get("bai_hoc") or {}
    in_ra("  BÀI HỌC: {0} quyết định, {1} đối chứng".format(ub.get("n_dung"), ub.get("n_doi_chung")))
    for bp, o in sorted((ub.get("bo_phan") or {}).items()):
        in_ra("    {0}: có bài {1}/{2} video thắng (qd {3}) · đối chứng {4}/{5} (qd {6}) · không bài {7}/{8} · "
              "uplift {9}".format(bp, int(o["co_bai"]["thang"]), o["co_bai"]["n"], o["co_bai"]["n_qd"],
                                  int(o["doi_chung"]["thang"]), o["doi_chung"]["n"], o["doi_chung"]["n_qd"],
                                  int(o["khong_bai"]["thang"]), o["khong_bai"]["n"], o.get("uplift")))
    kl: Dict[str, int] = {}
    for b in (ub.get("bai") or {}).values():
        kl[b["ket_luan"]] = kl.get(b["ket_luan"], 0) + 1
    in_ra("    bài đã dùng: {0} — {1}".format(len(ub.get("bai") or {}), kl))
    if bc.get("da_nghi"):
        in_ra("    ĐÃ NGHỈ: " + ", ".join(bc["da_nghi"]))
    in_ra("  " + bc.get("tom_tat", ""))


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(prog="core.hieu_chuan", description=__doc__.split("\n")[0])
    ap.add_argument("lenh", choices=("chay", "gom"))
    ap.add_argument("--thu", action="store_true", help="CHỈ ĐỌC — không ghi gì")
    ap.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    if a.lenh == "gom":
        dong, n = gom(a.goc, ghi_dia=not a.thu)
        print("sổ cái: {0} dòng ({1} mới{2})".format(len(dong), n, ", chạy thử" if a.thu else ""))
        return 0
    in_bao_cao(chay(a.goc, thu=a.thu))
    return 0


if __name__ == "__main__":
    sys.exit(main())
