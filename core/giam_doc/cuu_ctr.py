"""Cứu video hỏng cổng CTR ở giờ 52–120 (View = Hiển thị × CTR × Giữ chân — sửa ĐÚNG cổng hỏng).

Điều kiện: video tuổi 52–120h, đã phán TRƯỢT, hiển thị ≥ 500, CTR trang chủ (Browse) < 0,8 × mục tiêu
CTR của kênh. Hiển thị thấp mà CTR ổn → lỗi ở cổng HIỂN THỊ (chủ đề / nguồn): không sửa, chỉ ghi quan
sát. Video thắng không bao giờ bị đụng.

Hai chế độ (khoá kenh.yaml `giam_doc_studio`):
  * false (mặc định) — CHỈ GỢI Ý: giám đốc chọn trong thực đơn, tiêu đề mới vào "Việc của bạn".
  * true — CỨU THẬT (01/10/2026, đợt 1b):
      1. HỘI ĐỒNG (`quan_ly.goi_quyet("cuu_ctr")`: 3 chuyên gia + phản biện + chấm) viết tiêu đề mới theo
         khung tiêu đề thắng (`docs/kien-thuc/con-duong-kenh-thang.md` §3) + tiêu đề thắng của kênh và
         ngách, ≤ 100 ký tự, kèm độ tin. Tin thấp (cổng "quan_sat") → không đề xuất.
      2. DUYỆT: kênh < 1.000 sub TỰ ÁP ngay (đã có đo trước/sau + tự đổi lại); kênh ≥ 1.000 sub: lần sửa đầu chờ chủ
         bấm "Duyệt" (Phòng điều hành → Việc của bạn); sổ `giam-doc/duyet-sua.json`. Đã duyệt ≥ 1 lần và ≥ 1 lần
         kết quả TỐT → kênh tự áp.
      3. HÀNG `vm/logs/hang-sua.json` → máy DOM sửa giờ vắng (`vm/agent.py: chay_sua_video` →
         `vm/may_dang_dom.py: sua_video_mot`), kết quả lượt cuối `vm/logs/sua-cuoi.json`.
      4. `dong_bo` (mỗi nhịp gác tổng, qua `giam_doc.nhip`): xếp hàng mục đã duyệt; máy sửa xong → ghi
         `lich_su_sua` vào hồ sơ video; ĐO CTR trước/sau bằng HIỆU hai bản chụp (trang chủ nếu mỗi phía
         ≥ 500 hiển thị trang chủ, không thì CTR chung ≥ 500/phía): tốt (≥ +10%) · giữ (≥ 0%) · tệ hơn →
         ĐỔI LẠI tiêu đề cũ rồi thử BÌA HẠNG NHÌ (`bia-2.jpg`); bìa cũng tệ hơn → trả bìa gốc. 14 ngày chưa
         đủ số → `chua_du` (giữ nguyên). Mỗi video một lần cứu trong đời.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .du_lieu import chu_so, ctr_trang_chu, moi_nhat, thu_muc_giam_doc, thu_muc_kenh

TEN = "cuu_ctr"
MO_TA = "Cứu video trượt vì CTR trang chủ thấp ở giờ 52–120 (đổi tiêu đề trước, bìa sau)"
NHIP = "ngay"
CHI_SO_CHINH = "ctr_browse_sau_sua"
TUOI = (52.0, 120.0)
HE_SO_CTR = 0.8
HIEN_THI_TOI_THIEU = 500

TIEU_DE_TOI_DA = 100
TEP_DUYET = "duyet-sua.json"
TEP_HANG = os.path.join("vm", "logs", "hang-sua.json")
SUB_KENH_NHO = 1000       # dưới ngần này sub: tự áp NGAY (đã có đo trước/sau + tự đổi lại nếu tệ hơn) — 04/10/2026
SO_LAN_DUYET = 1          # kênh ≥ 1.000 sub: chủ duyệt 1 lần sửa đầu
SO_LAN_TOT = 1            # … và ≥ 1 lần tốt → kênh được tự áp
TI_LE_TOT = 1.10          # CTR sau / trước ≥ 1,10 → tốt
TI_LE_GIU = 1.00          # < 1,00 → quay lui
DO_TOI_DA_NGAY = 14       # quá hạn mà chưa đủ hiển thị → chua_du (giữ nguyên)
HIEN_THI_DO = 500         # mỗi phía của phép đo
LOI_TOI_DA = 3            # máy sửa hỏng ngần này lần → bỏ
KHOA_HANG_QUA_HAN = 15 * 60
_RE_NHAN = re.compile(r"^\s*(【[^】]{1,12}】)")


# ── plugin (thuần, 0 đồng) ─────────────────────────────────────────────────

def _trong_khung(bs: Any) -> List[Dict[str, Any]]:
    return [v for v in bs.video if v.get("tuoi_gio") is not None and TUOI[0] <= v["tuoi_gio"] <= TUOI[1]
            and (moi_nhat(v) or {}).get("tuoi", 0) >= 36]


def ap_dung(bs: Any) -> float:
    """Chạy khi có video trong khung 52–120h đã có bản chụp ≥ 36h và kênh có mục tiêu CTR."""
    return 1.0 if bs.ctr_muc_tieu and _trong_khung(bs) else 0.0


def _chan_doan(bs: Any, v: Dict[str, Any]) -> Dict[str, Any]:
    b = moi_nhat(v) or {}
    tc = ctr_trang_chu(v, 36.0, TUOI[1] + 24)
    imp = b.get("hien_thi") or 0
    ctr = tc["ctr_browse"] if tc else b.get("ctr")
    nhan_ctr = "CTR trang chủ @{0:.0f}h".format(tc["tuoi"]) if tc else "CTR chung (thiếu bảng Browse)"
    muc = bs.ctr_muc_tieu
    dau = "“{0}” ({1}, {2:.0f}h): {3} hiển thị, {4} {5}".format(
        v["tieu_de"][:40], v["id"], b.get("tuoi", 0), chu_so(imp), nhan_ctr, chu_so(ctr, 1, "%"))
    q = {"video_id": v["id"], "n": 1, "tin_cay": "thap", "ctr": ctr, "hien_thi": imp, "trang_chu": bool(tc)}
    if v.get("thang"):
        return dict(q, cau=dau + " — đang THẮNG, không đụng.", cong="thang")
    if imp < HIEN_THI_TOI_THIEU or ctr is None:
        return dict(q, cau=dau + " — chưa đủ hiển thị để phán cổng CTR.", cong="chua_du")
    if ctr < HE_SO_CTR * muc:
        tr = " và đã phán TRƯỢT" if v.get("ket_luan") == "truot" else " (chưa phán trượt)"
        return dict(q, cau=dau + " < {0:.0%} mục tiêu {1} — HỎNG CỔNG CTR{2}.".format(HE_SO_CTR, chu_so(muc, 1, "%"), tr),
                    cong="ctr")
    if v.get("ket_luan") == "truot":
        vung = "" if bs.n_48h >= 5 else " (lưu ý: ngưỡng thắng {0} tính từ {1} video có số 48h — chưa vững)".format(
            chu_so(bs.nguong_thang_48h), bs.n_48h)
        return dict(q, cau=dau + " ≥ {0:.0%} mục tiêu {1} mà vẫn trượt — lỗi ở cổng HIỂN THỊ (chủ đề/nguồn), "
                    "đổi tiêu đề không cứu được{2}.".format(HE_SO_CTR, chu_so(muc, 1, "%"), vung), cong="hien_thi")
    return dict(q, cau=dau + " — CTR ổn, chưa có kết luận trượt.", cong="on")


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """Chẩn đoán cổng của từng video trong khung 52–120h."""
    return [_chan_doan(bs, v) for v in _trong_khung(bs)]


def _pool(bs: Any, vid: str, toi_da: int = 5) -> List[str]:
    """Tiêu đề video mà YouTube đặt cạnh video này (bảng đề xuất), nhiều view nhất trước."""
    try:
        from .. import cong_thuc_v7 as v7  # noqa: PLC0415

        bang = v7.doc_bang_de_xuat(os.path.join(thu_muc_kenh(bs.goc, bs.ma_kenh), "chi-so"), vid) or {}
    except Exception:  # noqa: BLE001
        return []
    dong = sorted(bang.get("dong") or [], key=lambda d: -(d.get("xem") or 0))
    return [str(d.get("tieu_de"))[:60] for d in dong if d.get("tieu_de")][:toi_da]


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mỗi video hỏng cổng CTR đã trượt → một việc Studio "đổi tiêu đề"."""
    thang = [v["tieu_de"] for v in bs.video if v.get("thang")][:3]
    ra = []
    for q in qs:
        v = bs.video_theo_id(q["video_id"])
        if q.get("cong") != "ctr" or not v or v.get("ket_luan") != "truot":
            continue
        da_cham = [u.get("tieu_de") for u in v.get("tieu_de_da_cham") or []
                   if u.get("tieu_de") and u.get("tieu_de") != v["tieu_de"]][:5]
        ra.append({"loai": "viec_studio", "viec": "doi_tieu_de", "video_id": v["id"], "tieu_de_cu": v["tieu_de"],
                   "can_noi_dung": True, "chi_goi_y": not bat_studio(bs),
                   "goi_y": {"tieu_de_da_cham": da_cham, "tieu_de_thang_kenh": thang, "cum": v.get("cum"),
                             "pool": _pool(bs, v["id"])},
                   "chan_doan": {"ctr": q["ctr"], "hien_thi": q["hien_thi"], "trang_chu": q.get("trang_chu")},
                   "gia_thuyet": "Đổi tiêu đề nâng CTR trang chủ từ {0} lên ≥ {1}.".format(
                       chu_so(q["ctr"], 1, "%"), chu_so(HE_SO_CTR * bs.ctr_muc_tieu, 1, "%")),
                   "chi_so": CHI_SO_CHINH, "co_mau": 1, "han_ngay": 7,
                   "nen": {"gia_tri": q["ctr"], "n": 1, "tu_video": [v["id"]]}})
    return ra


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Việc Studio không mở thí nghiệm tham số — kết quả đo nằm ở `duyet-sua.json` (`dong_bo`)."""
    return None


# ── tiện ích sổ ────────────────────────────────────────────────────────────

def _luc(t: Optional[_dt.datetime] = None) -> str:
    return (t or _dt.datetime.now()).replace(microsecond=0).isoformat()


def _doc_json(duong: str, mac_dinh: Any) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, type(mac_dinh)) else mac_dinh
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1, default=str)
    os.replace(tam, duong)


def _chuan(t: Any) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()


def bat_studio(bs_hoac_cai: Any) -> bool:
    """`giam_doc_studio: true` trong kenh.yaml."""
    cai = getattr(bs_hoac_cai, "cai", bs_hoac_cai) or {}
    return str(cai.get("giam_doc_studio", "")).strip().lower() in ("true", "1", "yes", "co")


def duong_duyet(goc: str, ma: str) -> str:
    return os.path.join(thu_muc_giam_doc(goc, ma), TEP_DUYET)


def doc_duyet(goc: str, ma: str) -> List[Dict[str, Any]]:
    """Mọi mục cứu của kênh (cũ → mới)."""
    du = _doc_json(duong_duyet(goc, ma), {})
    return [m for m in du.get("muc") or [] if isinstance(m, dict)]


def _ghi_duyet(goc: str, ma: str, ds: List[Dict[str, Any]]) -> None:
    _ghi_json(duong_duyet(goc, ma), {"kenh": ma, "muc": ds})


def quyen_studio(goc: str, ma: str, ds: Optional[List[Dict[str, Any]]] = None,
                 sub: Optional[float] = None) -> Dict[str, Any]:
    """{"quyen": "can_duyet" | "tu_ap", "duyet", "tot", "nho"}. Kênh dưới `SUB_KENH_NHO` sub (hoặc chưa biết sub)
    TỰ ÁP ngay — đã có đo CTR trước/sau và tự đổi lại khi tệ hơn. Kênh ≥ 1.000 sub: chủ duyệt `SO_LAN_DUYET` lần đầu
    và ≥ `SO_LAN_TOT` lần có kết quả TỐT (tiêu đề hoặc bìa) mới tự áp."""
    ds = doc_duyet(goc, ma) if ds is None else ds
    da = [m for m in ds if m.get("duyet_boi") == "chu"]
    tot = sum(1 for m in da if "tot" in (m.get("ket"), m.get("ket_bia")))
    nho = sub is None or sub < SUB_KENH_NHO
    tu_ap = nho or (len(da) >= SO_LAN_DUYET and tot >= SO_LAN_TOT)
    return {"quyen": "tu_ap" if tu_ap else "can_duyet", "duyet": len(da), "tot": tot, "nho": nho}


def cho_duyet(goc: str, ma: str) -> List[Dict[str, Any]]:
    """Mục chờ chủ bấm Duyệt / Bỏ (bảng điều khiển đọc)."""
    return [m for m in doc_duyet(goc, ma) if m.get("trang_thai") == "cho_duyet"]


def ghi_duyet(goc: str, ma: str, id_muc: str, *, duyet: bool, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Chủ bấm Duyệt (`duyet=True`) / Bỏ trên Phòng điều hành — CHỈ ghi sổ duyệt; nhịp gác tổng kế tiếp
    xếp hàng sửa. True nếu có mục đang chờ mang id này."""
    ds = doc_duyet(goc, ma)
    for m in ds:
        if m.get("id") == id_muc and m.get("trang_thai") == "cho_duyet":
            m.update(trang_thai="duyet" if duyet else "bo", duyet_boi="chu" if duyet else "",
                     duyet_luc=_luc(bay_gio))
            _ghi_duyet(goc, ma, ds)
            return True
    return False


# ── hội đồng viết tiêu đề mới ──────────────────────────────────────────────

def khung_tieu_de(goc: str) -> str:
    """Mục "## 3. Tiêu đề" của `docs/kien-thuc/con-duong-kenh-thang.md` (khung tiêu đề thắng của ngách)."""
    try:
        with io.open(os.path.join(goc, "docs", "kien-thuc", "con-duong-kenh-thang.md"), encoding="utf-8") as tep:
            chu = tep.read()
    except OSError:
        return ""
    m = re.search(r"^## 3\. Tiêu đề\s*\n(.*?)(?=^## )", chu, flags=re.S | re.M)
    return re.sub(r"\*\*|\*", "", m.group(1)).strip() if m else ""


def _thang_ngach(goc: str, ma: str, toi_da: int = 6) -> List[str]:
    """Tiêu đề đang thắng của các kênh CÙNG NGÁCH (khoá `nhom` của kenh.yaml), trừ chính kênh."""
    try:
        from ..auto_khau import tieu_de_thang_cua_kenh  # noqa: PLC0415
        from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        from .hoi_dong import _ngach  # noqa: PLC0415

        ng = _ngach(goc, ma)
        if not ng:
            return []
        goc_ma = re.sub(r"-v\d+$", "", ma)
        ra: List[str] = []
        for k in sorted(os.listdir(duong_kenh(goc))):
            if k.startswith("_") or re.sub(r"-v\d+$", "", k) == goc_ma:
                continue
            if str((doc_yaml(os.path.join(duong_kenh(goc, k), TEP_KENH)) or {}).get("nhom") or "").strip() != ng:
                continue
            ra += [t for t in tieu_de_thang_cua_kenh(goc, k, toi_da=3) if t not in ra]
        return ra[:toi_da]
    except Exception:  # noqa: BLE001
        return []


def so_lieu_video(bs: Any, v: Dict[str, Any]) -> Dict[str, Any]:
    """{khoá nguồn: số} cho hội đồng (cùng kiểu khoá khám nghiệm `v:<vid>/<mốc>/<trường>`)."""
    b = moi_nhat(v) or {}
    nhan = "v:{0}/{1}".format(v["id"], b.get("moc", "?"))
    sl: Dict[str, Any] = {}
    for k in ("hien_thi", "ctr", "ctr_browse", "hien_thi_browse", "tuoi", "xem", "avd_pct"):
        if b.get(k) is not None:
            sl["{0}/{1}".format(nhan, k)] = b[k]
    tc = ctr_trang_chu(v, 36.0, 1e9)
    if tc and tc.get("moc") != b.get("moc"):
        sl["v:{0}/{1}/ctr_browse".format(v["id"], tc["moc"])] = tc["ctr_browse"]
    for k, x in (("kenh/ctr_trang_chu_muc_tieu", bs.ctr_muc_tieu), ("kenh/nguong_thang_48h", bs.nguong_thang_48h),
                 ("v:{0}/hien_thi_48h".format(v["id"]), v.get("hien_thi_48h"))):
        if x is not None:
            sl[k] = round(float(x), 2)
    for o in bs.video:
        tco = ctr_trang_chu(o, 36.0, 1e9) if o.get("thang") and o["id"] != v["id"] else None
        if tco:
            sl["v:{0}/{1}/ctr_browse".format(o["id"], tco["moc"])] = tco["ctr_browse"]
    return sl


def loi_nhac_tieu_de(bs: Any, v: Dict[str, Any], d: Dict[str, Any], so_lieu: Dict[str, Any]) -> str:
    """Bài toán cho hội đồng: MỘT tiêu đề mới cho video hỏng cổng CTR."""
    g = d.get("goi_y") or {}
    cd = d.get("chan_doan") or {}
    nhan = _RE_NHAN.match(v.get("tieu_de") or "")
    khung = khung_tieu_de(bs.goc) if bs.goc else ""
    ngach = _thang_ngach(bs.goc, bs.ma_kenh) if bs.goc else []
    dong = [
        "CỨU VIDEO CTR THẤP — kênh YouTube {0}. Video {1} đã TRƯỢT (dưới ngưỡng thắng {2} hiển thị @48h). {3} {4} "
        "với {5} hiển thị < {6:.0%} mục tiêu {7}: cổng hỏng là CTR (người thấy mà không bấm), không phải hiển thị. "
        "Việc: viết MỘT tiêu đề mới cho CHÍNH video này (cùng nội dung — không hứa điều video không nói) để người "
        "lướt trang chủ bấm vào.".format(
            bs.ma_kenh, v["id"], chu_so(bs.nguong_thang_48h), "CTR trang chủ" if cd.get("trang_chu") else "CTR chung",
            chu_so(cd.get("ctr"), 1, "%"), chu_so(cd.get("hien_thi")), HE_SO_CTR, chu_so(bs.ctr_muc_tieu, 1, "%")),
        "TIÊU ĐỀ HIỆN TẠI: “{0}”".format(v.get("tieu_de")),
        "MỤC TIÊU KÊNH\n" + str(bs.muc_tieu or "").strip(),
        "KHUNG TIÊU ĐỀ THẮNG CỦA NGÁCH (docs/kien-thuc, đã chứng minh)\n" + (khung or "(không đọc được)"),
        "TIÊU ĐỀ ĐANG THẮNG CỦA KÊNH: " + (" / ".join(g.get("tieu_de_thang_kenh") or []) or "(chưa có)"),
        "TIÊU ĐỀ ĐANG THẮNG CỦA NGÁCH (kênh anh em cùng ngách): " + (" / ".join(ngach) or "(chưa có)"),
        "POOL (video YouTube đặt cạnh video này): " + (" / ".join(g.get("pool") or []) or "(chưa có)"),
        "BẢN TIÊU ĐỀ KHÁC ĐÃ CHẤM LÚC LÀM VIDEO: " + (" / ".join(g.get("tieu_de_da_cham") or []) or "(không có)"),
        "LUẬT: ≤ {0} ký tự; cùng ngôn ngữ với tiêu đề hiện tại; {1}theo đúng MỘT khung thắng ở trên (hai vế / số "
        "đếm + trí tuệ + nhãn khoa học / tò mò) và giống CHỦ NGỮ của tiêu đề thắng của kênh; khác hẳn tiêu đề hiện "
        "tại (đổi góc bấm, không chỉ đổi vài chữ).".format(
            TIEU_DE_TOI_DA, "giữ nhãn đầu {0}; ".format(nhan.group(1)) if nhan else ""),
        "Chỉ trả MỘT khối JSON:\n{\"tieu_de_moi\": \"…\", \"khung\": \"hai_ve|so_dem_tri_tue|to_mo|chan_dung|khac\", "
        "\"ly_do\": \"1–2 câu có số: vì sao tiêu đề này kéo CTR trang chủ lên\", \"so_dan\": [{\"so\": 1.2, "
        "\"nguon\": \"<khoá SỐ LIỆU>\"}]}",
        "SỐ LIỆU (khoá nguồn: giá trị)\n" + "\n".join("{0}: {1}".format(k, x) for k, x in so_lieu.items()),
    ]
    return "\n\n".join(dong)


def doc_tieu_de(tho: str, cu: str) -> Optional[Dict[str, Any]]:
    """Câu trả lời → {tieu_de_moi, khung, ly_do} đã soát (6–100 ký tự, khác tiêu đề cũ, giữ nhãn đầu)."""
    from ..goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return None
    if not isinstance(du, dict):
        return None
    moi = _chuan(du.get("tieu_de_moi")).strip("“”\"'")
    nhan = _RE_NHAN.match(cu or "")
    if nhan and not moi.startswith(nhan.group(1)) and len(nhan.group(1) + moi) <= TIEU_DE_TOI_DA:
        moi = nhan.group(1) + moi
    if not 6 <= len(moi) <= TIEU_DE_TOI_DA or re.sub(r"\W", "", moi) == re.sub(r"\W", "", cu or ""):
        return None
    return {"tieu_de_moi": moi, "khung": _chuan(du.get("khung"))[:30], "ly_do": _chuan(du.get("ly_do"))[:300],
            "so_dan": du.get("so_dan") if isinstance(du.get("so_dan"), list) else []}


def chon_tieu_de(bs: Any, d: Dict[str, Any], goi_chat: Callable[..., str], *, luu: bool = True,
                 ghi: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Một phiên hội đồng (qua `quan_ly.goi_quyet`) → {tieu_de_moi, ly_do, khung, do_tin, cong, mo_hinh} | {loi}."""
    from .quan_ly import goi_quyet  # noqa: PLC0415

    v = bs.video_theo_id(str(d.get("video_id") or ""))
    if v is None:
        return {"loi": "không có video"}
    sl = so_lieu_video(bs, v)
    q = goi_quyet("cuu_ctr", loi_nhac_tieu_de(bs, v, d, sl), sl, goi_chat, goc=bs.goc, ma=bs.ma_kenh, luu=luu,
                  ghi=ghi, khoa="cuu-ctr-{0}-{1}".format(v["id"], bs.bay_gio.strftime("%Y%m%d")),
                  nhan={"video_id": v["id"], "moc": (moi_nhat(v) or {}).get("moc")},
                  doc=lambda tho: doc_tieu_de(tho, v.get("tieu_de") or ""))
    if q.get("ket") is None:
        return {"loi": q.get("loi") or "hội đồng không ra tiêu đề"}
    hd = q.get("hoi_dong") or {}
    return dict(q["ket"], do_tin=(hd.get("quyet") or {}).get("do_tin"), cong=hd.get("cong") or "ap",
                mo_hinh=q.get("mo_hinh"))


def _anh_du_phong(goc: str, ma: str, ma_goi: str) -> str:
    """Bìa thay thế: bìa hạng nhì đã lưu (`ho-so-video/anh/<mã gói>-bia-2.jpg`); không có → ""."""
    try:
        from ..ho_so_video import duong_bia_2_ho_so  # noqa: PLC0415

        p = duong_bia_2_ho_so(goc, ma, ma_goi)
        return p if os.path.isfile(p) else ""
    except Exception:  # noqa: BLE001
        return ""


def xu_ly(goc: str, ma: str, bs: Any, thuc_don: List[Dict[str, Any]], goi_chat: Optional[Callable[..., str]], *,
          viet: bool = True, ghi: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """`chay_kenh` gọi khi `giam_doc_studio: true`: mỗi việc Studio của `cuu_ctr` đã qua `gioi_han.kiem`
    → hội đồng viết tiêu đề → mục "chờ duyệt" (hoặc "tự áp" khi kênh đã đủ thành tích và hội đồng tin
    đủ). `viet=False` (chế độ thử): chỉ hỏi hội đồng, không ghi gì. Trả các mục vừa lập."""
    if goi_chat is None:
        return []
    from . import so_thi_nghiem as stn  # noqa: PLC0415

    ds = doc_duyet(goc, ma) if goc else []
    da_co = {m.get("video_id") for m in ds}
    q = quyen_studio(goc, ma, ds, sub=_so(((getattr(bs, "ypp", None) or {}).get("sub"))))
    ra = []
    for d in thuc_don:
        if d.get("plugin") != TEN or d.get("loai") != "viec_studio" or not d.get("duoc") or d["video_id"] in da_co:
            continue
        v = bs.video_theo_id(d["video_id"])
        if v is None:
            continue
        kq = chon_tieu_de(bs, d, goi_chat, luu=viet, ghi=ghi)
        if kq.get("loi") or kq.get("cong") == "quan_sat":
            if ghi:
                ghi("  [cứu CTR] {0}: {1}".format(d["video_id"], kq.get("loi") or "hội đồng tin thấp ({0}) — chỉ "
                                                  "quan sát".format(kq.get("do_tin"))))
            continue
        tu_ap = q["quyen"] == "tu_ap" and kq.get("cong") == "ap"
        cd = d.get("chan_doan") or {}
        muc = {"id": "s-{0}-{1}".format(v["id"], bs.bay_gio.strftime("%Y%m%d%H%M")), "video_id": v["id"],
               "ma_goi": v.get("ma_goi") or "", "luc": _luc(bs.bay_gio), "tuoi_gio": v.get("tuoi_gio"),
               "tieu_de_cu": v.get("tieu_de") or "", "tieu_de_moi": kq["tieu_de_moi"], "khung": kq.get("khung"),
               "ly_do": kq.get("ly_do") or "", "do_tin": kq.get("do_tin"), "mo_hinh": kq.get("mo_hinh"),
               "chan_doan": {"ctr": cd.get("ctr"), "hien_thi": cd.get("hien_thi"), "trang_chu": cd.get("trang_chu"),
                             "muc_tieu": bs.ctr_muc_tieu},
               "anh_du_phong": _anh_du_phong(goc, ma, v.get("ma_goi") or "") if goc else "",
               "trang_thai": "tu_ap" if tu_ap else "cho_duyet", "duyet_boi": "may" if tu_ap else "",
               "ket": "", "ket_bia": ""}
        ra.append(muc)
        if viet:
            ds.append(muc)
            da_co.add(v["id"])
            stn.ghi_nhat_ky(goc, ma, viec="viec_studio", video_id=v["id"], truoc=muc["tieu_de_cu"],
                            sau=muc["tieu_de_moi"], ly_do_llm=muc["ly_do"], so_lieu=muc["chan_doan"],
                            trang_thai=muc["trang_thai"], do_tin=muc["do_tin"], bay_gio=bs.bay_gio)
    if viet and ra:
        _ghi_duyet(goc, ma, ds)
    return ra


# ── hàng sửa (vm/logs/hang-sua.json — dùng chung với máy DOM) ───────────────

def giu_khoa_hang(goc: str) -> Optional[str]:
    """Khoá tệp hàng `hang-sua.json.khoa` (máy DOM dùng cùng khoá). None = đang bị giữ."""
    duong = os.path.join(goc, TEP_HANG) + ".khoa"
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return duong
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(duong) > KHOA_HANG_QUA_HAN:
                    os.remove(duong)
                    continue
            except OSError:
                pass
            return None
    return None


def doc_hang(goc: str) -> List[Dict[str, Any]]:
    return [x for x in _doc_json(os.path.join(goc, TEP_HANG), {}).get("viec") or [] if isinstance(x, dict)]


def _ghi_hang(goc: str, ds: List[Dict[str, Any]]) -> None:
    _ghi_json(os.path.join(goc, TEP_HANG), {"viec": ds})


def _viec_hang(muc: Dict[str, Any], ma: str, buoc: str, *, tieu_de: str = "", anh: str = "",
               tieu_de_cu: str = "", bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    v = {"id": "{0}:{1}".format(muc["id"], buoc), "muc": muc["id"], "buoc": buoc, "kenh": ma,
         "ma_goi": muc.get("ma_goi"), "video_id": muc["video_id"], "them_luc": _luc(bay_gio), "trang_thai": "cho",
         "lan_loi": 0}
    if tieu_de:
        v["tieu_de"] = tieu_de
    if tieu_de_cu:
        v["tieu_de_cu"] = tieu_de_cu
    if anh:
        v["anh"] = os.path.abspath(anh)
    return v


# ── đo trước / sau ─────────────────────────────────────────────────────────

def _so(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def do_ctr(ls: Dict[str, Any], sau: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """CTR trước (cộng dồn tới lúc sửa, `moc_truoc` của `lich_su_sua`) và sau (HIỆU bản chụp mới nhất − bản
    trước) — ưu tiên TRANG CHỦ khi mỗi phía ≥ 500 hiển thị trang chủ, không thì CTR chung (≥ 500/phía).
    {du, nguon, truoc, sau, hien_thi}."""
    t = (ls or {}).get("moc_truoc") or {}
    sau = sau or {}
    ra: Dict[str, Any] = {"du": False, "nguon": "", "truoc": None, "sau": None, "hien_thi": None}
    if not sau or str(sau.get("luc_chup") or "") <= str(t.get("luc_chup") or ""):
        return ra
    for nguon, ki, kc in (("trang_chu", "hien_thi_trang_chu", "ctr_trang_chu"), ("chung", "impressions", "ctr")):
        it, ct, is_, cs = _so(t.get(ki)), _so(t.get(kc)), _so(sau.get(ki)), _so(sau.get(kc))
        if None in (it, ct, is_, cs) or is_ <= it:
            continue
        them = is_ - it
        ra.update(nguon=nguon, truoc=round(ct, 2), sau=round(max(0.0, (is_ * cs - it * ct) / them), 2),
                  hien_thi={"truoc": it, "sau": round(them)})
        if it >= HIEN_THI_DO and them >= HIEN_THI_DO:
            ra["du"] = True
            return ra
    return ra


def phan_xu(do: Dict[str, Any], *, ctr_goc: Optional[float] = None) -> str:
    """"tot" | "giu" | "quay_lui" | "" (chưa đủ số). `ctr_goc`: bước bìa so với CTR GỐC của video (trước lần
    sửa tiêu đề), không so với giai đoạn tiêu đề mới."""
    if not do.get("du"):
        return ""
    truoc = ctr_goc if ctr_goc else do.get("truoc")
    if not truoc:
        return "tot" if (do.get("sau") or 0) > 0 else "giu"
    ti = float(do["sau"]) / float(truoc)
    return "tot" if ti >= TI_LE_TOT else "giu" if ti >= TI_LE_GIU else "quay_lui"


# ── đồng bộ (mỗi nhịp gác tổng) ────────────────────────────────────────────

def _kenh_studio(goc: str) -> List[str]:
    from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    ra = []
    try:
        ten = sorted(os.listdir(duong_kenh(goc)))
    except OSError:
        return ra
    for ma in ten:
        if ma.startswith("_"):
            continue
        cai = doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}
        if str(cai.get("giam_doc") or "tat").strip().lower() in ("goi_y", "tu_ap") and bat_studio(cai):
            ra.append(ma)
    return ra


#: bước của máy DOM → trạng thái mục khi bước đó xong
_SAU_BUOC = {"tieu_de": "da_sua", "quay_lui_tieu_de": "quay_lui", "bia": "da_sua_bia", "quay_lui_bia": "xong"}


def _ghi_buoc_xong(goc: str, ma: str, m: Dict[str, Any], buoc: str, vh: Dict[str, Any], bay_gio: _dt.datetime) -> None:
    """Máy DOM báo xong một bước → `lich_su_sua` của hồ sơ (số chụp mới nhất làm `moc_truoc`)."""
    from .. import ho_so_video  # noqa: PLC0415

    loai = "bia" if buoc.endswith("bia") else "tieu_de"
    if buoc == "tieu_de":
        cu, moi = m.get("tieu_de_cu"), m.get("tieu_de_moi")
    elif buoc == "quay_lui_tieu_de":
        cu, moi = m.get("tieu_de_moi"), m.get("tieu_de_cu")
    else:
        cu, moi = "", os.path.basename(str(vh.get("anh") or ""))
    try:
        ho_so_video.cap_nhat_chi_so(goc, ma, bay_gio=bay_gio)
    except Exception:  # noqa: BLE001 — đo vẫn được, chỉ kém chính xác
        pass
    ho_so_video.ghi_sua(goc, ma, m.get("ma_goi") or "", loai=loai, cu=cu, moi=moi, doi_boi="giam_doc",
                        ly_do=("quay lui: " if buoc.startswith("quay") else "") + str(m.get("ly_do") or "")[:200],
                        bay_gio=bay_gio)
    m[buoc + "_luc"] = str(vh.get("ket_luc") or _luc(bay_gio))


def _phan_xu_muc(goc: str, ma: str, m: Dict[str, Any], hang: List[Dict[str, Any]], bay_gio: _dt.datetime,
                 ghi: Optional[Callable[[str], None]]) -> bool:
    """Đo + phân xử một mục đã sửa (tiêu đề hoặc bìa). True nếu có thay đổi."""
    from .. import ho_so_video  # noqa: PLC0415

    buoc = "tieu_de" if m["trang_thai"] == "da_sua" else "bia"
    hs = ho_so_video.doc_ho_so(goc, ma, m.get("ma_goi") or "") or {}
    luc = str(m.get(buoc + "_luc") or m.get("luc") or "")
    ls = next((x for x in reversed(hs.get("lich_su_sua") or []) if isinstance(x, dict)
               and x.get("loai") == buoc and str(x.get("luc") or "") >= luc[:16]), None)
    do = do_ctr(ls or {}, hs.get("so_lieu_moi_nhat"))
    ket = phan_xu(do, ctr_goc=m.get("ctr_goc") if buoc == "bia" else None)
    doi = do != m.get("do_" + buoc)
    m["do_" + buoc] = do
    try:
        qua = (bay_gio - _dt.datetime.fromisoformat(luc[:19])).days
    except ValueError:
        qua = 0
    if not ket and qua >= DO_TOI_DA_NGAY:
        ket = "chua_du"
    if not ket:
        return doi
    if buoc == "tieu_de":
        m["ket"], m["ctr_goc"] = ket, do.get("truoc")
        m["trang_thai"] = "xong"
        if ket == "quay_lui":
            hang.append(_viec_hang(m, ma, "quay_lui_tieu_de", tieu_de=m.get("tieu_de_cu", ""),
                                   tieu_de_cu=m.get("tieu_de_moi", ""), bay_gio=bay_gio))
            if m.get("anh_du_phong") and os.path.isfile(m["anh_du_phong"]):
                hang.append(_viec_hang(m, ma, "bia", anh=m["anh_du_phong"], bay_gio=bay_gio))
            m["trang_thai"] = "cho_quay_lui"
    else:
        m["ket_bia"] = ket
        m["trang_thai"] = "xong"
        goc_anh = ho_so_video.duong_anh_ho_so(goc, ma, m.get("ma_goi") or "")
        if ket == "quay_lui" and os.path.isfile(goc_anh):
            hang.append(_viec_hang(m, ma, "quay_lui_bia", anh=goc_anh, bay_gio=bay_gio))
            m["trang_thai"] = "cho_quay_lui"
    if ghi:
        ghi("  [cứu CTR] {0} {1} ({2}): {3} — CTR {4} → {5} ({6})".format(
            ma, m.get("video_id"), buoc, ket, do.get("truoc"), do.get("sau"), do.get("nguon") or "chưa đủ số"))
    return True


def dong_bo(goc: str, *, bay_gio: Optional[_dt.datetime] = None,
            ghi: Optional[Callable[[str], None]] = None) -> Dict[str, int]:
    """Một nhịp (gác tổng → `giam_doc.nhip`): (1) mục đã duyệt / tự áp → hàng sửa; (2) bước máy DOM đã
    làm → `lich_su_sua` + sổ duyệt; (3) đo trước/sau → tốt / giữ / quay lui. Không mạng, không AI."""
    bay_gio = bay_gio or _dt.datetime.now()
    dem = {"xep": 0, "ghi_sua": 0, "phan_xu": 0}
    kenh = _kenh_studio(goc)
    if not kenh:
        return dem
    khoa = giu_khoa_hang(goc)
    if khoa is None:
        return dem
    try:
        hang = doc_hang(goc)
        theo_id = {x.get("id"): x for x in hang}
        doi_hang = False
        for ma in kenh:
            ds = doc_duyet(goc, ma)
            doi = False
            for m in ds:
                if m.get("trang_thai") in ("duyet", "tu_ap"):  # (1)
                    vh = _viec_hang(m, ma, "tieu_de", tieu_de=m["tieu_de_moi"], tieu_de_cu=m.get("tieu_de_cu", ""),
                                    bay_gio=bay_gio)
                    if vh["id"] not in theo_id:
                        hang.append(vh)
                        theo_id[vh["id"]] = vh
                        doi_hang = True
                    m["trang_thai"], m["xep_luc"] = "da_xep", _luc(bay_gio)
                    doi = True
                    dem["xep"] += 1
                    continue
                for buoc in ("tieu_de", "quay_lui_tieu_de", "bia", "quay_lui_bia"):  # (2)
                    vh = theo_id.get("{0}:{1}".format(m.get("id"), buoc))
                    if not vh or vh.get("da_ghi") or vh.get("trang_thai") not in ("xong", "khong-the", "loi"):
                        continue
                    if vh["trang_thai"] == "loi" and int(vh.get("lan_loi") or 0) < LOI_TOI_DA:
                        continue  # máy thử lại đêm sau
                    vh["da_ghi"] = True
                    doi_hang = doi = True
                    if vh["trang_thai"] != "xong":
                        m["trang_thai"], m["loi"] = "loi", "{0}: {1}".format(buoc, vh.get("ly_do") or vh["trang_thai"])[:200]
                        break
                    _ghi_buoc_xong(goc, ma, m, buoc, vh, bay_gio)
                    dem["ghi_sua"] += 1
                    m["trang_thai"] = _SAU_BUOC[buoc]
                    if buoc == "quay_lui_tieu_de" and "{0}:bia".format(m["id"]) not in theo_id:
                        m["trang_thai"] = "xong"
                if m.get("trang_thai") in ("da_sua", "da_sua_bia"):  # (3)
                    n_hang = len(hang)
                    tt_cu = m.get("trang_thai")
                    if _phan_xu_muc(goc, ma, m, hang, bay_gio, ghi):
                        doi = True
                        dem["phan_xu"] += int(m.get("trang_thai") != tt_cu)
                    if len(hang) != n_hang:
                        theo_id = {x.get("id"): x for x in hang}
                        doi_hang = True
            if doi:
                _ghi_duyet(goc, ma, ds)
        if doi_hang:
            _ghi_hang(goc, hang)
    finally:
        try:
            os.remove(khoa)
        except OSError:
            pass
    return dem


def dong_viec_cua_ban(m: Dict[str, Any]) -> str:
    """Một câu cho khối "Việc của bạn": tiêu đề cũ → mới + lý do ngắn + độ tin."""
    tin = m.get("do_tin")
    return "Đổi tiêu đề video {0}: “{1}” → “{2}”. Lý do: {3}{4}".format(
        m.get("video_id"), m.get("tieu_de_cu"), m.get("tieu_de_moi"), _chuan(m.get("ly_do"))[:160] or "CTR trang chủ thấp",
        " (độ tin {0:.2f})".format(float(tin)) if isinstance(tin, (int, float)) else "")
