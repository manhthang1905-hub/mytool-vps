"""MÁY STUDIO — phần THUẦN (16/10/2026) của bộ chạy hàng việc máy CÓ KIỂU (`core.giam_doc`, khoá `viec_may`).

Chủ: "mục đích cuối VPS này auto 100%". Bộ chạy DOM `vm/studio_may_dom.py` mở Chrome kênh làm việc Studio; tệp này chỉ
đọc đĩa / tính toán (có test, không mạng, không Chrome):

    ma_goi_cua_video(goc, kenh, vid)          videoId → mã gói (sổ videoId của máy đăng, lùi về hồ sơ video)
    ung_vien_bia(goc, kenh, ma_goi, anh_a)    bìa B/C cho "Thử nghiệm và so sánh": hồ sơ `-bia-2/-bia-3`, `7-thumbnail/`
                                              của lượt, gói DONE → bỏ trùng (kể cả trùng bìa A đang chạy) → CỔNG đọc
                                              được `do_bia.cham_tep` (trượt = KHÔNG BAO GIỜ tải lên) → xếp điểm giám khảo
    tep_tai_len(duong, thu_muc)               bản tải lên đúng chuẩn bìa YouTube (JPEG 1280×720, < 2 MB)
    thieu_tinh_nang(so_cmt, kenh, bay)        kênh đang bị chặn ghim = chưa bật "tính năng nâng cao" (xác minh điện thoại)
    ket_viec_test(ket_video)                  kết quả từng video → trạng thái việc (xong / bo / loi)
    doc_suc_khoe(trang)                       chữ các trang Studio → {canh_bao, chi_tiet, muc}
    dieu_kien_test / dieu_kien_suc_khoe       điều kiện tự kích hoạt (skill D13/D14 của `core/ky_nang.py`)

Thiết kế + luật an toàn: `vm/studio_may_dom.py`.
"""

from __future__ import annotations

import datetime as _dt
import glob
import hashlib
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

#: Thử nghiệm và so sánh của YouTube: tối đa 3 bìa (A đang chạy + 2 ứng viên).
TOI_DA_UNG_VIEN = 2
#: Đọc sức khoẻ Studio mỗi kênh tối đa một lần / ngần này ngày (khớp `giam_doc._tu_dong.NGAY_KIEM_LAI_SUC_KHOE`).
NGAY_SUC_KHOE = 3
#: Bị chặn ghim (`vm/logs/cmt-dom.json` → `_kenh:<k>.can_xac_minh`) trong ngần này ngày, chưa ghim được lại → coi như
#: kênh CHƯA bật tính năng nâng cao (khớp `bang_dieu_khien.NGAY_CON_THU_GHIM`).
NGAY_CHAN_GHIM = 3
#: Bìa YouTube: < 2 MB; chuẩn 1280×720.
BIA_TOI_DA_BYTE = 2 * 1024 * 1024 - 64 * 1024
BIA_CO = (1280, 720)
#: Lệch vân tay (`do_bia._lech_van_tay`) dưới ngần này = cùng một bức (bản xuất lại / bản chép).
LECH_CUNG_ANH = 6.0
_DUOI_ANH = (".jpg", ".jpeg", ".png", ".webp")
_RE_THUMB = re.compile(r"^thumb_(\d+)\.(?:jpe?g|png|webp)$", re.IGNORECASE)
_RE_BIA_N = re.compile(r"-bia-(\d+)\.jpe?g$", re.IGNORECASE)


# ── đọc đĩa ──────────────────────────────────────────────────────────────────

def _json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def thu_muc_vm(goc: str) -> str:
    try:
        from .trung_tam import thu_muc_vm as _tm  # noqa: PLC0415
        return _tm(goc)
    except Exception:  # noqa: BLE001
        return os.path.join(goc, "vm")


def ma_goi_cua_video(goc: str, kenh: str, vid: str) -> str:
    """Mã gói (`<kênh>-<lượt>`) của `vid`: sổ videoId của máy đăng (`vm/logs/so-video-id.json`, khoá `<kênh>/<mã>`),
    lùi về hồ sơ video (`CHANNEL/<kênh>/ho-so-video/*.json`, khoá `video_id`). Không thấy → ""."""
    so = _json(os.path.join(thu_muc_vm(goc), "logs", "so-video-id.json"))
    for k, v in (so.items() if isinstance(so, dict) else []):
        if isinstance(v, dict) and str(v.get("video_id") or "") == vid and str(k).startswith(kenh + "/"):
            return str(k).split("/", 1)[1]
    for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", "{0}-*.json".format(kenh)))):
        hs = _json(p)
        if isinstance(hs, dict) and str(hs.get("video_id") or "") == vid:
            return os.path.splitext(os.path.basename(p))[0]
    return ""


def _thu_muc_done(goc: str, kenh: str) -> str:
    d = _json(os.path.join(thu_muc_vm(goc), "thu-muc-dang-{0}.json".format(kenh))) or {}
    tm = str(d.get("thu_muc_done") or "") if isinstance(d, dict) else ""
    return tm or os.path.join(goc, "DONE", kenh)


def _sha(duong: str) -> str:
    try:
        with open(duong, "rb") as tep:
            return hashlib.sha1(tep.read()).hexdigest()
    except OSError:
        return ""


# ── ứng viên bìa ─────────────────────────────────────────────────────────────

def _nguon_ung_vien(goc: str, kenh: str, ma_goi: str) -> List[Dict[str, Any]]:
    """Mọi tệp bìa KHÁC bìa đang chọn của gói, kèm điểm giám khảo nếu biết: [{tep, nguon, diem_gk}] (chưa lọc)."""
    ra: List[Dict[str, Any]] = []
    thu_anh = os.path.join(goc, "CHANNEL", kenh, "ho-so-video", "anh")
    hs = _json(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", ma_goi + ".json")) or {}
    b2 = hs.get("bia_2") if isinstance(hs, dict) and isinstance(hs.get("bia_2"), dict) else {}
    diem_hs = {}
    for hang, b in ((2, b2), (3, b2.get("bia_3") if isinstance(b2.get("bia_3"), dict) else {})):
        if b:
            diem_hs[hang] = b.get("tong_diem")
    # 1) bìa hạng nhì/ba giám khảo đã lưu lâu dài (`ho_so_video._sao_luu_bia_2`) — sống qua dọn lượt
    for p in sorted(glob.glob(os.path.join(thu_anh, "{0}-bia-*.jpg".format(ma_goi)))):
        m = _RE_BIA_N.search(p)
        if m:
            ra.append({"tep": p, "nguon": "ho-so:bia-" + m.group(1), "diem_gk": diem_hs.get(int(m.group(1)))})
    # 2) bộ bìa của lượt còn trên đĩa (`7-thumbnail/thumb_NNN.*`, điểm theo `chon-bia.json`, bỏ tấm bị loại)
    luot = ma_goi[len(kenh) + 1:] if ma_goi.startswith(kenh + "-") else ma_goi.rsplit("-", 1)[-1]
    thu_thumb = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "7-thumbnail")
    cb = _json(os.path.join(thu_thumb, "chon-bia.json")) or {}
    so_chon = ((cb.get("chon") or {}) if isinstance(cb, dict) else {}).get("so")
    uv = {int(u["so"]): u for u in (cb.get("ung_vien") or [] if isinstance(cb, dict) else [])
          if isinstance(u, dict) and u.get("so") is not None}
    try:
        ten = sorted(os.listdir(thu_thumb))
    except OSError:
        ten = []
    for t in ten:
        m = _RE_THUMB.match(t)
        if not m:
            continue
        so = int(m.group(1))
        u = uv.get(so) or {}
        if (so_chon is not None and so == int(so_chon)) or u.get("loai"):
            continue
        ra.append({"tep": os.path.join(thu_thumb, t), "nguon": "luot:thumb_{0:03d}".format(so), "diem_gk": u.get("tong_diem")})
    # 3) gói DONE (thường chỉ còn CHON-* = bìa A — trùng thì bị bỏ ở bước lọc)
    goi = os.path.join(_thu_muc_done(goc, kenh), ma_goi)
    try:
        ten = sorted(os.listdir(goi))
    except OSError:
        ten = []
    for t in ten:
        if os.path.splitext(t)[1].lower() in _DUOI_ANH and not t.upper().startswith("CHON-"):
            ra.append({"tep": os.path.join(goi, t), "nguon": "done:" + t, "diem_gk": None})
    return ra


def _cham_mac_dinh(duong: str) -> Dict[str, Any]:
    from . import do_bia  # noqa: PLC0415
    return do_bia.cham_tep(duong)


def _bo_cuc_hong(bc: Dict[str, Any]) -> List[str]:
    try:
        from . import do_bia  # noqa: PLC0415
        return list(do_bia.ly_do_bo_cuc(bc))
    except Exception:  # noqa: BLE001
        return []


def _van_tay(duong: str) -> List[int]:
    try:
        from . import do_bia  # noqa: PLC0415
        return do_bia.van_tay(duong)
    except Exception:  # noqa: BLE001
        return []


def _lech(a: List[int], b: List[int]) -> float:
    if not a or not b or len(a) != len(b):
        return 255.0
    return sum(abs(int(x) - int(y)) for x, y in zip(a, b)) / float(len(a))


def ung_vien_bia(goc: str, kenh: str, ma_goi: str, anh_a: Any = (), *,
                 cham: Optional[Callable[[str], Dict[str, Any]]] = None,
                 van_tay: Optional[Callable[[str], List[int]]] = None,
                 toi_da: int = TOI_DA_UNG_VIEN) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(chọn, bỏ). `anh_a`: tệp bìa A (bìa đang chạy tải từ i.ytimg.com, bản sao `ho-so-video/anh/<mã>.jpg`, …) — ứng
    viên CÙNG bức với A bị bỏ. Cổng: `cham_tep` phải `dat is True` và bố cục không hỏng (như `do_bia.xep_doi_bia`).
    Xếp: điểm giám khảo giảm dần (chưa có điểm xếp sau), rồi điểm đọc được. `chon` tối đa `toi_da` mục
    {tep, nguon, diem_gk, diem_doc}; `bo` = [{tep, nguon, ly_do}]."""
    cham = cham or _cham_mac_dinh
    van_tay = van_tay or _van_tay
    a_ds = [anh_a] if isinstance(anh_a, str) else list(anh_a or [])
    a_ds = [p for p in a_ds if p and os.path.isfile(p)]
    vt_a = [v for v in (van_tay(p) for p in a_ds) if v]
    sha_a = {_sha(p) for p in a_ds}
    thay_sha, thay_vt = set(), []
    tot, bo = [], []
    for u in _nguon_ung_vien(goc, kenh, ma_goi):
        p = u["tep"]
        s = _sha(p)
        if not s:
            bo.append(dict(u, ly_do="không đọc được tệp"))
            continue
        vt = van_tay(p)
        if s in sha_a or any(_lech(vt, x) < LECH_CUNG_ANH for x in vt_a):
            bo.append(dict(u, ly_do="trùng bìa A đang chạy"))
            continue
        if s in thay_sha or any(_lech(vt, x) < LECH_CUNG_ANH for x in thay_vt):
            bo.append(dict(u, ly_do="trùng một ứng viên khác"))
            continue
        thay_sha.add(s)
        if vt:
            thay_vt.append(vt)
        try:
            bc = cham(p) or {}
        except Exception as loi:  # noqa: BLE001 — ảnh hỏng: không qua cổng
            bc = {"dat": None, "ly_do": ["chấm lỗi: {0}".format(str(loi)[:80])]}
        if bc.get("dat") is not True:
            bo.append(dict(u, ly_do="trượt cổng đọc được: " + ("; ".join(bc.get("ly_do") or []) or "không kết luận")[:160]))
            continue
        hong = _bo_cuc_hong(bc)
        if hong:
            bo.append(dict(u, ly_do="bố cục hỏng: " + "; ".join(hong)[:160]))
            continue
        tot.append(dict(u, diem_doc=bc.get("diem")))
    tot.sort(key=lambda u: (u.get("diem_gk") is None, -float(u.get("diem_gk") or 0), -float(u.get("diem_doc") or 0)))
    for u in tot[toi_da:]:
        bo.append(dict(u, ly_do="đủ {0} ứng viên tốt hơn".format(toi_da)))
    return tot[:toi_da], bo


def tep_tai_len(duong: str, thu_muc: str) -> str:
    """Bản tải lên chuẩn bìa YouTube: JPEG 1280×720 (cắt giữa về 16:9), < 2 MB. Tệp gốc đã đúng chuẩn thì trả nguyên."""
    from PIL import Image, ImageOps  # noqa: PLC0415
    with Image.open(duong) as anh:
        dung = anh.size == BIA_CO and anh.format in ("JPEG", "PNG") and os.path.getsize(duong) <= BIA_TOI_DA_BYTE
        if dung:
            return duong
        moi = ImageOps.fit(anh.convert("RGB"), BIA_CO, method=Image.LANCZOS)
    os.makedirs(thu_muc, exist_ok=True)
    dich = os.path.join(thu_muc, "{0}-{1}.jpg".format(os.path.splitext(os.path.basename(duong))[0], _sha(duong)[:8]))
    for q in (92, 85, 78, 70):
        moi.save(dich, format="JPEG", quality=q)
        if os.path.getsize(dich) <= BIA_TOI_DA_BYTE:
            break
    return dich


# ── quyền / trạng thái việc ──────────────────────────────────────────────────

def _gio(chu: Any) -> Optional[_dt.datetime]:
    try:
        return _dt.datetime.fromisoformat(str(chu or "").strip()[:19].replace(" ", "T"))
    except ValueError:
        return None


def thieu_tinh_nang(so_cmt: Any, kenh: str, bay: _dt.datetime, ngay: int = NGAY_CHAN_GHIM) -> str:
    """Lý do (chuỗi) nếu kênh ĐANG bị YouTube chặn ghim = chưa bật "tính năng nâng cao" (Thử nghiệm và so sánh cũng cần
    nó): lần chặn cuối ≤ `ngay` ngày và chưa ghim được lần nào sau đó. "" = không biết là thiếu (vẫn vào Studio xem)."""
    so = so_cmt if isinstance(so_cmt, dict) else {}
    k = so.get("_kenh:" + kenh) if isinstance(so.get("_kenh:" + kenh), dict) else {}
    chan = _gio(k.get("can_xac_minh"))
    if chan is None or (bay - chan).total_seconds() > ngay * 86400:
        return ""
    duoc = [_gio(k.get("ghim_duoc"))] + [_gio(m.get("da_ghim")) for v, m in so.items()
                                        if isinstance(m, dict) and not str(v).startswith("_") and m.get("kenh") == kenh]
    if any(d is not None and d > chan for d in duoc):
        return ""
    return ("kênh chưa bật tính năng nâng cao (YouTube chặn ghim từ {0:%d/%m %H:%M}, chờ xác minh điện thoại) — "
            "Thử nghiệm và so sánh cần tính năng nâng cao".format(chan))


#: Kết quả một video của `studio_test_compare`.
KV_DA_DAT, KV_DA_CO, KV_KHONG_UNG_VIEN, KV_KHONG_QUYEN, KV_LOI = "da_dat", "da_co", "khong_ung_vien", "khong_quyen", "loi"


def ket_viec_test(ket_video: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """Kết quả từng video → (trạng thái việc, lý do). Kênh không có quyền → `bo`; video lỗi → `loi` (thử lại, 5 lần thành
    `bo`); mọi video đã có thử nghiệm (máy vừa đặt / có sẵn) hoặc không có ứng viên, ít nhất một video có → `xong`; không
    video nào có ứng viên → `bo`."""
    ds = [(v, k) for v, k in (ket_video or {}).items() if isinstance(k, dict)]
    if not ds:
        return "bo", "việc không có video"
    q = [k for _v, k in ds if k.get("ket") == KV_KHONG_QUYEN]
    if q:
        return "bo", str(q[0].get("ly_do") or "kênh chưa bật tính năng nâng cao")
    loi = [(v, k) for v, k in ds if k.get("ket") not in (KV_DA_DAT, KV_DA_CO, KV_KHONG_UNG_VIEN)]
    if loi:
        return "loi", "; ".join("{0}: {1}".format(v, str(k.get("ly_do") or "lỗi"))[:160] for v, k in loi)[:400]
    co = [v for v, k in ds if k.get("ket") in (KV_DA_DAT, KV_DA_CO)]
    if not co:
        return "bo", "không video nào có bìa ứng viên qua cổng đọc được (bìa nhì/ba không còn trên đĩa)"
    return "xong", "; ".join("{0}: {1}".format(v, {KV_DA_DAT: "máy vừa đặt thử nghiệm {0} bìa".format(k.get("so_bia") or "?"),
                                                    KV_DA_CO: "đã có thử nghiệm ({0})".format(k.get("trang_thai") or "?"),
                                                    KV_KHONG_UNG_VIEN: "không có ứng viên"}[k["ket"]]) for v, k in ds)[:400]


# ── đọc sức khoẻ Studio ──────────────────────────────────────────────────────

#: Một dòng/câu CÓ vấn đề (đa ngôn ngữ: vi / en / ja). Câu "không có / none / ありません" bị loại ở `_khong_co`.
MAU_VAN_DE = (
    ("gay_ban_quyen", r"(gậy|cảnh cáo).{0,30}bản quyền|copyright strike|著作権侵害の警告"),
    ("gay_cong_dong", r"(gậy|cảnh cáo).{0,40}(nguyên tắc cộng đồng|chính sách)|community guidelines (strike|warning)|"
                      r"コミュニティ ガイドライン(の)?違反(警告)?|コミュニティガイドライン(の)?違反"),
    ("dung_lai", r"nội dung (được )?dùng lại|nội dung sử dụng lại|reused content|再利用されたコンテンツ"),
    ("han_che", r"tính năng (bị|đã bị) hạn chế|bị hạn chế tính năng|features? (are |is )?(restricted|limited)|"
                r"機能(が|は)?制限"),
    ("tu_choi_ypp", r"(đơn đăng ký|yêu cầu).{0,30}(bị từ chối|không được chấp thuận)|not approved for (the )?youtube partner|"
                    r"application (was )?rejected|審査.{0,10}(不承認|承認されませんでした)"),
)
#: Câu phủ định (không có vi phạm) — dòng khớp mẫu vấn đề mà có những chữ này thì KHÔNG tính.
RE_KHONG_CO = re.compile(r"\b(không có|chưa có|không bị|none|no (active )?(strikes?|warnings?|issues?)|0 (gậy|strikes?))\b|"
                         r"ありません|なし|0 件|問題はありません|không có vấn đề|good standing|tình trạng tốt|^\s*0\s*$", re.IGNORECASE)
#: Dòng là chữ HƯỚNG DẪN chung (link "Tìm hiểu thêm về gậy…") — không tính.
RE_HUONG_DAN = re.compile(r"tìm hiểu (thêm|về)|learn (more|about)|詳細|xem (chính sách|nguyên tắc)|chính sách của youtube là gì|"
                          r"about (copyright|community)|\?$", re.IGNORECASE)


#: Ô «Thông báo» (trước gọi «Hạn chế») của danh sách video (trang Nội dung; đo 16/10/2026: không có gì = "—") — ô đứng riêng một dòng. Nguyên tắc cộng đồng = CẢNH BÁO; bản quyền
#: (khiếu nại Content ID, KHÔNG phải gậy) chỉ ghi thông tin.
MAU_THEO_TRANG = {"noi_dung": (("han_che_video", r"^(nguyên tắc cộng đồng|community guidelines|コミュニティ ?ガイドライン|"
                                                 r"giới hạn độ tuổi|age[- ]restricted|年齢制限)$"),)}
MAU_THONG_TIN = {"noi_dung": (("khieu_nai_ban_quyen", r"^(bản quyền|copyright|著作権)$"),)}
TEN_LOAI = {"gay_ban_quyen": "gậy/cảnh cáo bản quyền", "gay_cong_dong": "gậy/cảnh cáo nguyên tắc cộng đồng",
            "dung_lai": "nội dung dùng lại", "han_che": "tính năng bị hạn chế", "tu_choi_ypp": "YPP bị từ chối",
            "han_che_video": "video bị hạn chế vì nguyên tắc cộng đồng", "khieu_nai_ban_quyen": "khiếu nại bản quyền (không phải gậy)"}


def doc_suc_khoe(trang: Dict[str, Any]) -> Dict[str, Any]:
    """`trang`: {tên trang: {"chu": chữ trang (innerText + chữ hộp), "loi": "..."}}. Trả {canh_bao, chi_tiet, muc: [{loai,
    trang, dong}], thong_tin: [...], doc_duoc: [trang đọc được]}. Chỉ tính DÒNG khớp mẫu vấn đề mà không phải câu phủ định
    / câu hướng dẫn; ô «Hạn chế» của trang Nội dung xét riêng. Đọc thiếu trang → `canh_bao` chỉ dựa trên trang đã đọc."""
    muc: List[Dict[str, str]] = []
    tin: List[Dict[str, str]] = []
    doc_duoc = []
    for ten, du in (trang or {}).items():
        du = du if isinstance(du, dict) else {"chu": str(du or "")}
        chu = str(du.get("chu") or "")
        if not chu.strip():
            continue
        doc_duoc.append(ten)
        dong = [" ".join(d.split()) for d in re.split(r"[\n\r\t]+", chu)]
        for i, d in enumerate(dong):
            if not d or len(d) > 400 or RE_HUONG_DAN.search(d):
                continue
            # câu phủ định có thể nằm ngay dòng kế (Studio tách nhãn / giá trị: "Gậy bản quyền" ↵ "Không có")
            ke = next((x for x in dong[i + 1:i + 3] if x), "")
            for loai, mau in MAU_VAN_DE + MAU_THEO_TRANG.get(ten, ()):
                if re.search(mau, d, re.IGNORECASE) and not RE_KHONG_CO.search(d) and not (len(ke) < 40 and RE_KHONG_CO.search(ke)):
                    muc.append({"loai": loai, "trang": ten, "dong": (d + (" · " + ke if ke and len(ke) < 60 else ""))[:240]})
                    break
            else:
                for loai, mau in MAU_THONG_TIN.get(ten, ()):
                    if re.search(mau, d, re.IGNORECASE):
                        tin.append({"loai": loai, "trang": ten, "dong": d[:120]})
                        break
    gon: List[Dict[str, str]] = []
    for m in muc:
        if not any(x["loai"] == m["loai"] and x["dong"] == m["dong"] for x in gon):
            gon.append(m)
    if gon:
        chi_tiet = "THẤY: " + " | ".join("{0} ({1}: «{2}»)".format(TEN_LOAI[m["loai"]], m["trang"], m["dong"][:120])
                                          for m in gon[:6])
    else:
        chi_tiet = "Không thấy cảnh báo / gậy / nội dung dùng lại trên: " + (", ".join(doc_duoc) or "(không đọc được trang nào)")
    if tin:
        chi_tiet += " · ghi nhận: {0} video có {1}".format(len(tin), TEN_LOAI[tin[0]["loai"]])
    return {"canh_bao": bool(gon), "chi_tiet": chi_tiet[:1200], "muc": gon[:12], "thong_tin": tin[:20], "doc_duoc": doc_duoc}


# ── lịch tự kích hoạt (skill D13 / D14) ───────────────────────────────────────

def duong_ket_suc_khoe(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_vm(goc), "logs", "studio-may", "{0}.suc-khoe.json".format(kenh))


def lan_doc_suc_khoe(goc: str, kenh: str) -> Dict[str, Any]:
    """Kết quả đọc sức khoẻ Studio THÀNH CÔNG gần nhất của kênh ({} nếu chưa có)."""
    d = _json(duong_ket_suc_khoe(goc, kenh))
    return d if isinstance(d, dict) and d.get("luc") else {}


def con_moi_suc_khoe(goc: str, kenh: str, bay: _dt.datetime, ngay: int = NGAY_SUC_KHOE) -> Optional[Dict[str, Any]]:
    """Lần đọc gần nhất nếu còn MỚI (< `ngay` ngày) — khi ấy không mở Chrome lần nữa."""
    d = lan_doc_suc_khoe(goc, kenh)
    t = _gio(d.get("luc"))
    return d if t is not None and (bay - t).total_seconds() < ngay * 86400 else None


def viec_mo(goc: str, loai: str, kenh: str) -> List[Dict[str, Any]]:
    from . import giam_doc  # noqa: PLC0415
    return [m for m in giam_doc.doc_viec_may_kieu(goc, loai) if m.get("kenh") == kenh]


def dieu_kien_test(goc: str, kenh: str) -> Tuple[bool, str]:
    from . import giam_doc  # noqa: PLC0415
    ds = viec_mo(goc, giam_doc.LOAI_TEST_COMPARE, kenh)
    if not ds:
        return False, "không có việc Thử nghiệm và so sánh"
    return True, "{0} việc Thử nghiệm và so sánh ({1} video)".format(len(ds), sum(len(m.get("video_ids") or []) for m in ds))


def dieu_kien_suc_khoe(goc: str, kenh: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    from . import giam_doc  # noqa: PLC0415
    ds = viec_mo(goc, giam_doc.LOAI_KIEM_SUC_KHOE, kenh)
    if not ds:
        return False, "không có việc đọc sức khoẻ Studio"
    cu = con_moi_suc_khoe(goc, kenh, bay or _dt.datetime.now())
    if cu:
        return True, "việc đọc sức khoẻ — đã đọc {0} (< {1} ngày): đóng việc bằng kết quả ấy, không mở Chrome".format(
            str(cu.get("luc"))[:16], NGAY_SUC_KHOE)
    return True, "việc đọc sức khoẻ Studio (cảnh báo / gậy / nội dung dùng lại)"
