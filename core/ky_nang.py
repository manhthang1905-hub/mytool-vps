"""DANH MỤC SKILL của tool (05/10/2026) — mỗi việc tool làm được là MỘT skill có định nghĩa rõ.

Chủ dự án: "những công việc định nghĩa là skill khá ok để phát triển và quản lý — 1 kênh khi bắt đầu cần skill gì
chạy, trong quá trình cần skill gì". Mỗi skill khai:
  ma       mã ngắn, duy nhất                     loai   khoi_tao (MỘT LẦN/kênh) | dinh_ky | sua_chua | mo_rong
  ten      tên người đọc                          can    skill/điều kiện phải có trước (mã skill hoặc "nguoi:<việc>")
  kiem     hàm (goc, kenh) -> (trạng thái, ghi chú) — RẺ, chỉ đọc đĩa, không mạng/không tiền
  lenh     cách chạy (dòng lệnh)                  mo_ta  một câu: làm gì, đọc lại bằng gì
Trạng thái: "dat" (xong/khỏe) | "thieu" (chưa làm) | "loi" (hỏng — cần sửa) | "cho" (đang chờ/nghỉ có lý do) | "-" (không áp).

TỰ KÍCH HOẠT (14/10/2026, chủ: "đóng gói thành skill… nó auto khi có điều kiện") — skill khai thêm (tuỳ chọn):
  dieu_kien  hàm (goc, kenh) -> (đúng?, lý do) — RẺ, chỉ đọc đĩa; đúng = nên chạy
  chay       argv (list) hoặc hàm (goc, kenh) -> argv; chạy bằng tiến trình con có hạn giờ
  nhip_gio   không chạy lại trước N giờ (tính từ lần chạy cuối)   tu_ap  True = máy tự chạy · False = chỉ báo "nên chạy"
  nang       việc DOM/sản xuất: cần khoá máy rảnh, mỗi lượt tối đa MỘT   toan_may  không theo kênh (một lần mỗi lượt)
Bộ chạy + sổ + luật: `core/ky_nang_tu.py`.

Dùng:  python -m core.ky_nang xem [kênh ...]      bảng skill × kênh
       python -m core.ky_nang danh-muc            mô tả mọi skill
       python -m core.ky_nang thieu <kênh>        skill KHỞI TẠO kênh còn thiếu, theo thứ tự chạy
       python -m core.ky_nang tu-kich-hoat [--thu] [--goc G]   một lượt tự kích hoạt (--thu: chỉ in, không chạy/ghi)
       python -m core.ky_nang lich                in lệnh đăng ký tác vụ ShopAPI-KyNang (mỗi giờ :35) — chủ tự đăng ký
"""
from __future__ import annotations

import datetime as _dt
import glob
import importlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

DAT, THIEU, LOI, CHO, KHONG = "dat", "thieu", "loi", "cho", "-"
KY_HIEU = {DAT: "✅", THIEU: "⬜", LOI: "❌", CHO: "⏳", KHONG: "·"}


@dataclass
class KyNang:
    ma: str
    ten: str
    loai: str
    mo_ta: str
    lenh: str
    kiem: Callable[[str, str], Tuple[str, str]]
    can: List[str] = field(default_factory=list)
    dieu_kien: Optional[Callable[[str, str], Tuple[bool, str]]] = None
    chay: Any = None
    nhip_gio: float = 24.0
    tu_ap: bool = False
    nang: bool = False
    toan_may: bool = False
    han_phut: float = 0.0          # hạn giờ riêng (0 = mặc định của ky_nang_tu: nặng 60', nhẹ 15')
    mot_kenh: bool = False         # việc nhẹ mà dài (nhiều lượt AI): mỗi lượt tự kích hoạt chỉ MỘT kênh — không dồn 8 kênh


# ── tiện ích đọc đĩa (thuần, hỏng → None) ──────────────────────────────────────

def _json(*phan) -> Optional[dict]:
    try:
        with open(os.path.join(*phan), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _yaml(goc: str, kenh: str, khoa: str) -> str:
    """Giá trị một khoá đơn trong kenh.yaml (bỏ nháy, bỏ chú thích cuối dòng)."""
    try:
        with open(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8") as tep:
            for dong in tep:
                if dong.startswith(khoa + ":"):
                    v = dong.split(":", 1)[1].split(" #", 1)[0].strip()
                    return v.strip('"').strip("'")
    except OSError:
        pass
    return ""


def _tuoi_gio(duong: str) -> Optional[float]:
    try:
        return (_dt.datetime.now().timestamp() - os.path.getmtime(duong)) / 3600.0
    except OSError:
        return None


def _vm(goc: str, *phan) -> str:
    return os.path.join(goc, "vm", *phan)


# ── KIỂM từng skill ────────────────────────────────────────────────────────────

def _dang_o_may_khac(goc, kenh) -> bool:
    """Kênh làm ở máy khác, máy này chỉ chăm/quét (may-ao cach_dang=anh, vd TL4-T7)."""
    d = dict((((_json(_vm(goc, "cai-dat-tool.json")) or {}).get("kenh") or {}).get(kenh)) or {})
    d.update(_json(goc, "CHANNEL", kenh, "may-ao.json") or {})
    return str(d.get("cach_dang") or "") == "anh" and not d.get("tu_dang")


def k_chrome(goc, kenh):
    d = _json(_vm(goc, "logs", "kiem-dom", kenh + ".json"))
    if _dang_o_may_khac(goc, kenh):
        return KHONG, "đăng ở máy khác — máy này chỉ quét/chăm"
    if not d:
        return THIEU, "chưa kiểm DOM lần nào (Chrome kênh đăng nhập?)"
    return (DAT if d.get("ok") else LOI), "kiểm DOM {0}: {1}".format(str(d.get("ngay") or "")[:16],
                                                                   "OK" if d.get("ok") else ", ".join(d.get("hong") or []))


def k_tai_khoan(goc, kenh):
    try:
        sys.path.insert(0, _vm(goc))
        import kho_bi_mat  # noqa: PLC0415
        c = kho_bi_mat.co_tai_khoan(kenh)
    except Exception:  # noqa: BLE001
        return THIEU, "chưa có kho bí mật"
    return (DAT if c["email"] else THIEU), "email {0} · 2FA {1}".format("có" if c["email"] else "thiếu",
                                                                       "có" if c["totp"] else "thiếu")


def k_may_ao(goc, kenh):
    d = _json(goc, "CHANNEL", kenh, "may-ao.json") or {}
    if not d:
        return THIEU, "chưa có may-ao.json"
    ok = bool(d.get("tu_dang")) and str(d.get("cach_dang") or "") != "anh"
    return (DAT if ok else CHO), "tu_dang={0} cach_dang={1}".format(d.get("tu_dang"), d.get("cach_dang"))


def k_ngach(goc, kenh):
    ok = bool(_yaml(goc, kenh, "nhom") and _yaml(goc, kenh, "tep"))
    co_tuyen = os.path.isfile(os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "tuyen.csv"))
    return (DAT if ok and co_tuyen else THIEU), "nhóm/tệp {0} · tuyến {1}".format("có" if ok else "thiếu",
                                                                                "có" if co_tuyen else "thiếu")


def k_giong(goc, kenh):
    v = _yaml(goc, kenh, "voice_id")
    return (DAT if v else THIEU), "voice_id {0}".format("có" if v else "thiếu")


def k_nhan_vat(goc, kenh):
    anh = [p for p in glob.glob(os.path.join(goc, "CHANNEL", kenh, "nv", "*")) if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    return (DAT if anh else THIEU), "{0} ảnh nhân vật".format(len(anh))


def k_keo_cheo(goc, kenh):
    """D08 kéo view chéo: kênh lớn (≥500h/28n) thêm video kênh em vào danh sách phát — 1 lần/ngày qua agent.
    Đạt = hôm nay/hôm qua đã chạy; chờ = kênh chưa đủ lớn / chưa tới lượt; thiếu = quá 2 ngày không chạy."""
    import datetime as _d  # noqa: PLC0415
    ng = _json(_vm(goc, "logs", "keo-cheo-ngay.json")) or {}
    so = _json(goc, "workspace", "keo-cheo", "da-them.json") or {}
    muc = [m for m in (so.get("muc") or []) if m.get("kenh_chu") == kenh]
    hom = _d.date.today()
    ngay = str(ng.get("ngay") or "")
    if ngay and (hom - _d.date.fromisoformat(ngay)).days <= 1:
        return DAT, "chạy {0} · kênh này đã thêm {1} video".format(ngay, len(muc))
    if not ngay:
        return CHO, "chưa chạy lần nào (agent chạy 09:00–20:00)"
    return THIEU, "lần cuối {0} — quá 2 ngày".format(ngay)


def k_doi_thu(goc, kenh):
    p = os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "doi-thu.csv")
    t = _tuoi_gio(p)
    if t is None:
        return THIEU, "chưa có danh bạ đối thủ"
    return (DAT if t < 72 else CHO), "danh bạ đối thủ cập nhật {0:.0f} giờ trước".format(t)


def _so_thiet_lap(goc, kenh):
    return _json(_vm(goc, "logs", "thiet-lap-kenh", kenh + ".json")) or {}


def _k_muc_thiet_lap(muc: str):
    def kiem(goc, kenh):
        so = _so_thiet_lap(goc, kenh)
        if not so and _yaml(goc, kenh, "thiet_lap_kenh").lower() != "true":
            return KHONG, "kênh thiết lập tay (trước khi có skill)"
        if not so:
            return THIEU, "chưa chạy thiết lập kênh"
        m = (so.get("muc") or {}).get(muc) or {}
        tt = m.get("tt") or "chua"
        if tt == "dat":
            return DAT, "đạt {0}".format(m.get("luc") or "")
        if tt == "cho":
            return CHO, str(m.get("ly_do") or "YouTube chưa cho đổi lại")[:80]
        if tt in ("hong", "can_nguoi"):
            return LOI, str(m.get("ly_do") or tt)[:80]
        return THIEU, tt
    return kiem


def k_ngon_ngu(goc, kenh):
    d = _json(_vm(goc, "logs", "thiet-lap-kenh", kenh + ".ngon-ngu.json"))
    if not d:
        return _k_muc_thiet_lap("ngon_ngu")(goc, kenh)
    dd = (d.get("dia_diem") or {}).get("ket")
    ok = d.get("ket") in ("giong", "doi") and dd in (None, "giong", "doi")
    return (DAT if ok else LOI), "giao diện {0} · địa điểm {1}".format(d.get("lang_sau"), dd or "?")


def k_nuoi(goc, kenh):
    d = _json(_vm(goc, "logs", "nuoi-trang-chu", kenh + ".json")) or {}
    bat = _yaml(goc, kenh, "nuoi_trang_chu").lower() == "true"
    if _yaml(goc, kenh, "trang_chu_tin_cay").lower() == "true" and not bat:
        return KHONG, "trang chủ đã tin cậy (trang_chu_tin_cay) — không cần nuôi"
    if d.get("trang_thai") == "dat":
        return DAT, str(d.get("ly_do") or "đạt")[:80]
    if bat:
        return CHO, "đang nuôi: " + str(d.get("ly_do") or "")[:70]
    return THIEU, "chưa nuôi (tắt)"


def k_oauth_client(goc, kenh):
    c = [p for p in glob.glob(_vm(goc, "clients", "*.json"))]
    # 05/10: chủ chọn bình luận DOM (API rắc rối) — không có client là "không dùng", không phải thiếu.
    return (DAT if c else KHONG), ("{0} tệp client".format(len(c)) if c else "không dùng — bình luận chạy DOM")


def k_token(goc, kenh):
    p = _vm(goc, "tokens", kenh + ".json")
    d = _json(p)
    if not d:
        return KHONG, "không dùng — bình luận chạy DOM"
    if not d.get("refresh_token"):
        return LOI, "token không có refresh_token — phải lấy lại"
    st = _json(_vm(goc, "logs", "oauth", kenh + ".json")) or {}
    if st.get("tt") == "hong":
        return LOI, "làm mới hỏng: " + str(st.get("ly_do") or "")[:60]
    return DAT, "có refresh_token"


def k_quet_ngay(goc, kenh):
    tt = _json(_vm(goc, "trang-thai.json")) or {}
    hom = _dt.date.today().isoformat()
    q = tt.get("quet_ngay@{0}@{1}".format(kenh, hom))
    if isinstance(q, dict) and q.get("xong"):
        return DAT, "đã quét hôm nay"
    if isinstance(q, dict):
        return CHO, "đã thử {0} lần, số liệu chưa về đủ".format(q.get("lan"))
    return THIEU, "chưa quét hôm nay"


def _ke_hoach(goc, kenh):
    try:
        sys.path.insert(0, goc)
        from core import ke_hoach_dang  # noqa: PLC0415
        return ke_hoach_dang.doc_bang(goc, kenh)
    except Exception:  # noqa: BLE001
        return [], []


def k_kho_dem(goc, kenh):
    cot, hang = _ke_hoach(goc, kenh)
    if not cot:
        return THIEU, "chưa có kế hoạch đăng"
    i_ng, i_tt = cot.index("Ngày đăng"), cot.index("Trạng thái đăng")
    mai = (_dt.date.today() + _dt.timedelta(days=1)).strftime("%d/%m/%Y")
    co = [r for r in hang if len(r) > i_ng and r[i_ng].strip() == mai and not (len(r) > i_tt and r[i_tt].startswith("Bỏ"))]
    if not co:
        return THIEU, "chưa có video ngày mai ({0})".format(mai)
    dang = [r for r in co if len(r) > i_tt and r[i_tt].upper().startswith("ĐÃ ĐĂNG")]
    return (DAT if dang else CHO), "video {0}: {1}".format(mai, "đã hẹn lịch" if dang else "chờ tải lên")


def k_binh_luan(goc, kenh):
    d = _json(_vm(goc, "logs", "cmt-dom-cuoi.json")) or {}
    tt = _json(_vm(goc, "trang-thai.json")) or {}
    hom = _dt.date.today().isoformat()
    if tt.get("phien_cuoi@" + kenh) == hom:
        return DAT, "phiên hôm nay đã chạy (mồi + trả lời)"
    return CHO, "chờ phiên kênh hôm nay"


def k_tu_hoc(goc, kenh):
    if _dang_o_may_khac(goc, kenh):
        return KHONG, "sản xuất ở máy khác — học ở máy đó"
    t = _tuoi_gio(os.path.join(goc, "CHANNEL", kenh, "tu-hoc", "bang-diem.md"))
    if t is None:
        return THIEU, "chưa có bảng điểm tự học"
    return (DAT if t < 36 else LOI), "bảng điểm cập nhật {0:.0f} giờ trước".format(t)


def k_nao(goc, kenh):
    hom = _dt.date.today().isoformat()
    return ((DAT, "phiên não hôm nay có") if os.path.isfile(os.path.join(goc, "nao", "nhat-ky", hom + ".md"))
            else (CHO, "chưa có phiên não hôm nay (sau quét Studio, mặc định 06:45)"))


def k_hl_tam(goc, kenh):
    p = _vm(goc, "logs", "hl-tam", kenh + ".json")
    return ((LOI, "ngôn ngữ giao diện đang TẠM — chưa trả") if os.path.isfile(p) else (DAT, "không có ngôn ngữ tạm"))


def k_mhkt_thieu(goc, kenh):
    d = _json(_vm(goc, "logs", "mhkt-thieu.json"))
    ds = [x for x in ((d or {}).get("video") or (d if isinstance(d, list) else []) or []) if isinstance(x, dict) and x.get("kenh") == kenh] \
        if isinstance(d, dict) else []
    return ((CHO, "{0} video thiếu MHKT — bù giờ vắng".format(len(ds))) if ds else (DAT, "không thiếu MHKT"))


def k_ypp(goc, kenh):
    from core import ypp
    r = ypp.du_bao(goc, kenh)
    tt = r["trang_thai"]
    if tt == "dat":
        return DAT, "đủ 4000 giờ + 1000 đăng ký (theo cửa sổ 28 ngày) — nộp đơn YPP"
    if tt == "chua_du_so":
        return THIEU, "chưa đủ 3 lần chụp chỉ số để dự báo"
    if tt == "cham":
        return CHO, "chưa tăng ({0:.0f}h, {1} đk) — chưa ước được ngày".format(r["gio"], r["dang_ky"])
    return CHO, "{0:.0f}h/4000, {1}/1000 đk — ETA ~{2} (còn ~{3:.0f} ngày)".format(r["gio"], r["dang_ky"], r["ngay_du_kien"], r["ngay_toi"])


# ── TỰ KÍCH HOẠT (14/10/2026): điều kiện + lệnh — bộ chạy ở `core/ky_nang_tu.py` ──────────────────────────────

def _gio() -> _dt.datetime:
    """Đồng hồ của điều kiện + bộ chạy (bài kiểm thay bằng giờ cố định)."""
    return _dt.datetime.now()


#: MÃ của vm/ (hàm thuần của máy đăng: hàng sửa, xếp video giới thiệu) — dữ liệu luôn đọc ở `goc`.
_VM_MA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm")


def _nap_vm(ten: str):
    if _VM_MA not in sys.path:
        sys.path.append(_VM_MA)               # nối ĐUÔI: không che mô-đun core cùng tên
    return importlib.import_module(ten)


def _py(*thong_so: str) -> List[str]:
    return [sys.executable, "-X", "utf8"] + list(thong_so)


def _kenh_yaml(goc, kenh) -> dict:
    from core.kenh import doc_yaml  # noqa: PLC0415
    return doc_yaml(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"))


def _doc_luc(chu) -> Optional[_dt.datetime]:
    try:
        return _dt.datetime.strptime(str(chu or "")[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _san_sang_dom(goc, kenh) -> str:
    """'' nếu máy này mở Chrome kênh làm DOM được; câu lý do nếu không."""
    if _dang_o_may_khac(goc, kenh):
        return "đăng ở máy khác"
    tt, gc = k_chrome(goc, kenh)
    return "" if tt == DAT else "Chrome kênh chưa kiểm DOM đạt ({0})".format(gc[:60])


def _khung_thiet_lap(bay) -> str:
    """`vm/thiet_lap_kenh_dom.py` không chạy 02:00–07:00 (giờ đăng/quét) — đừng gọi để nó hoãn."""
    return "khung cấm 02–07 của thiết lập kênh" if 2 <= bay.hour < 7 else ""


# S02 · Khám cấu hình kênh ─────────────────────────────────────────────────────

def _chuan(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v).strip().lower()


def kham_bom(tho: str) -> Tuple[str, str]:
    """BOM (U+FEFF) kẹt GIỮA kenh.yaml → ('go', lý do) gỡ được · ('bao', lý do) không tự gỡ · ('', '') không kẹt.
    Kẹt = YAML chuẩn đọc bản gốc hỏng (hoặc ra khoá dính BOM). Gỡ được = YAML chuẩn đọc bản đã gỡ ra ĐÚNG các khoá
    đơn mà bộ đọc tối giản (`core.kenh._yaml_toi_gian`) đọc từ bản gốc — tức là gỡ không đổi nghĩa."""
    if "﻿" not in tho.lstrip("﻿"):
        return "", ""
    import yaml  # noqa: PLC0415
    from core.kenh import _yaml_toi_gian  # noqa: PLC0415

    try:
        y = yaml.safe_load(tho.replace("﻿", ""))
    except yaml.YAMLError as loi:
        return "bao", "kenh.yaml hỏng cả khi gỡ BOM: {0}".format(str(loi).splitlines()[0][:80])
    try:
        if yaml.safe_load(tho) == y:
            return "", ""                     # YAML chuẩn vẫn đọc đúng — không đụng tệp
    except yaml.YAMLError:
        pass
    if not isinstance(y, dict):
        return "bao", "kenh.yaml gỡ BOM xong không ra bảng khoá"
    tg = {str(k).replace("﻿", "").strip(): v for k, v in _yaml_toi_gian(tho).items()}
    lech = [k for k, v in y.items() if not isinstance(v, (dict, list)) and _chuan(v) != _chuan(tg.get(k))]
    if lech:
        return "bao", "BOM kẹt giữa kenh.yaml nhưng gỡ ra lệch giá trị: {0}".format(", ".join(map(str, lech[:5])))
    return "go", "BOM kẹt giữa kenh.yaml làm YAML chuẩn đọc sai — gỡ xong hai bộ đọc cùng giá trị"


def _kham_cau_hinh(goc, kenh) -> Dict[str, Any]:
    """{tu_chay, bom: (kq, lý do), thieu: [(khoá, gợi ý)]} — chỉ đọc. KHÔNG bao giờ tự bật tu_chay/tu_dang/tu_duyet/
    tu_don/ngan_sach_ngay: thiếu khoá chỉ báo chủ kèm khoá gợi ý."""
    try:
        with open(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8", newline="") as tep:
            tho = tep.read()
    except OSError:
        return {"tu_chay": False, "bom": ("", ""), "thieu": []}
    from core.kenh import doc_kenh  # noqa: PLC0415
    k = doc_kenh(goc, kenh)
    thieu = []
    if k.tu_chay:
        if not k.thu_muc_done:            # khoá vắng → mặc định v2.191 DONE/<mã>; khai "" mới là thiếu
            thieu.append(("thu_muc_done", "thu_muc_done: DONE/{0}".format(kenh)))
        if not (k.gio_dang or k.nhip_dang):
            thieu.append(("nhip_dang", 'nhip_dang: "05:00"'))
        if k.ngan_sach_ngay <= 0:
            thieu.append(("ngan_sach_ngay", "ngan_sach_ngay: <₫ mỗi ngày — chủ tự đặt>"))
        if not k.voice_id:
            thieu.append(("voice_id", "voice_id: <mã giọng trong kho giọng>"))
    return {"tu_chay": bool(k.tu_chay), "bom": kham_bom(tho), "thieu": thieu}


def k_cau_hinh(goc, kenh):
    c = _kham_cau_hinh(goc, kenh)
    if not c["tu_chay"]:
        return KHONG, "kênh không tự chạy"
    loi = ([c["bom"][1]] if c["bom"][0] else []) + ["thiếu " + k for k, _g in c["thieu"]]
    return (LOI, " · ".join(loi)[:140]) if loi else (DAT, "kenh.yaml đọc chuẩn, đủ khoá tự chạy")


def d_cau_hinh(goc, kenh):
    c = _kham_cau_hinh(goc, kenh)
    if not c["tu_chay"]:
        return False, "kênh không tự chạy"
    if c["bom"][0] == "go":
        return True, c["bom"][1]
    return False, c["bom"][1] or ("thiếu khoá — chỉ báo chủ" if c["thieu"] else "kenh.yaml chuẩn")


def go_bom(goc, kenh) -> Tuple[bool, str]:
    """Gỡ MỌI U+FEFF khỏi kenh.yaml sau khi `kham_bom` nói gỡ được; bản cũ cất `workspace/sao-luu/kenh-yaml/`."""
    p = os.path.join(goc, "CHANNEL", kenh, "kenh.yaml")
    with open(p, "r", encoding="utf-8", newline="") as tep:
        tho = tep.read()
    kq, ly = kham_bom(tho)
    if kq != "go":
        return False, ly or "không có BOM kẹt"
    sao = os.path.join(goc, "workspace", "sao-luu", "kenh-yaml", "{0}-{1}.yaml".format(kenh, _gio().strftime("%Y%m%d-%H%M%S")))
    os.makedirs(os.path.dirname(sao), exist_ok=True)
    shutil.copy2(p, sao)
    with open(p + ".tam", "w", encoding="utf-8", newline="") as tep:
        tep.write(tho.replace("﻿", ""))
    os.replace(p + ".tam", p)
    return True, "đã gỡ {0} BOM (bản cũ: {1})".format(tho.count("﻿"), sao)


# S03 · Đổi bìa gấp ────────────────────────────────────────────────────────────

GIO_BIA_GAP = 12           # video lên sóng trong ngần này giờ (hoặc đã lên) thì không đợi khe đêm
GIO_SUA_DOI = 36           # việc sửa (bìa / tiêu đề) chờ khe đêm quá ngần này giờ = đói khe → làm ngay khi máy rảnh
NHUONG_PHIEN_PHUT = 68     # = agent.SUA_NHUONG_PHIEN_PHUT (60) + BU_MHKT_TOI_THIEU_PHUT (8)


def _cau_hinh_vm(goc, kenh) -> dict:
    d = dict((((_json(_vm(goc, "cai-dat-tool.json")) or {}).get("kenh") or {}).get(kenh)) or {})
    d.update(_json(goc, "CHANNEL", kenh, "may-ao.json") or {})
    return d


def _gio_len_song(goc, kenh) -> Dict[str, _dt.datetime]:
    """Mã gói → giờ lên sóng (kế hoạch đăng: Ngày đăng dd/mm/yyyy + Giờ đăng HH:MM)."""
    cot, hang = _ke_hoach(goc, kenh)
    if not all(c in cot for c in ("Mã gói", "Ngày đăng", "Giờ đăng")):
        return {}
    i_m, i_n, i_g = cot.index("Mã gói"), cot.index("Ngày đăng"), cot.index("Giờ đăng")
    ra = {}
    for r in hang:
        try:
            ra[r[i_m].strip()] = _dt.datetime.strptime("{0} {1}".format(r[i_n].strip(), r[i_g].strip()), "%d/%m/%Y %H:%M")
        except (IndexError, ValueError):
            continue
    return ra


def _bia_gap(goc, kenh, bay) -> List[dict]:
    """Việc `bia` còn phải làm trong `vm/logs/hang-sua.json` (ĐÚNG bộ lọc `may_dang_dom.hang_sua_kenh` mà agent dùng)
    của video lên sóng < `GIO_BIA_GAP` giờ nữa hoặc đã lên sóng."""
    mdd = _nap_vm("may_dang_dom")
    viec = list(mdd.hang_sua_kenh(mdd.doc_hang_sua(_vm(goc, "logs", "hang-sua.json")), kenh,
                                  bay.date().isoformat(), toi_da=99))
    gio = _gio_len_song(goc, kenh) if viec else {}

    def doi(v) -> bool:
        """18/10/2026 (tự kiểm): việc sửa (bìa HAY tiêu đề) chờ khe đêm quá `GIO_SUA_DOI` giờ — khe 02–05 chật (nhường
        phiên đăng + quét ngày), TL6-T7-0004 đổi tiêu đề chờ 166 giờ không tới lượt → làm như việc gấp."""
        t = _doc_luc(v.get("them_luc"))
        return bool(t and bay - t > _dt.timedelta(hours=GIO_SUA_DOI))
    return [dict(v, len_song=gio.get(v.get("ma_goi")) or bay, doi=doi(v)) for v in viec
            if (v.get("anh") and v.get("ma_goi") in gio and gio[v["ma_goi"]] - bay < _dt.timedelta(hours=GIO_BIA_GAP))
            or doi(v)]


def _nhuong_phien(goc, bay) -> str:
    """Luật `agent.han_sua_video`: phiên kênh (đăng) hôm nay chưa chạy mà còn < 68 phút (hoặc đã quá giờ) → không sửa."""
    tt = _json(_vm(goc, "trang-thai.json")) or {}
    hom = bay.date().isoformat()
    for khoa, gio in tt.items():
        if not (str(khoa).startswith("phien_muc_tieu@") and str(khoa).endswith("@" + hom) and isinstance(gio, str)):
            continue
        k = str(khoa).split("@")[1]
        if str(tt.get("phien_cuoi@" + k) or "") == hom:
            continue
        try:
            moc = _dt.datetime.combine(bay.date(), _dt.datetime.strptime(gio.strip(), "%H:%M").time())
        except ValueError:
            continue
        if moc - bay < _dt.timedelta(minutes=NHUONG_PHIEN_PHUT):
            return "phiên kênh {0} lúc {1} sắp/đang tới — không sửa video".format(k, gio)
    return ""


def k_bia_gap(goc, kenh):
    if _dang_o_may_khac(goc, kenh):
        return KHONG, "đăng ở máy khác"
    gap = _bia_gap(goc, kenh, _gio())
    return (CHO, "{0} việc bìa gấp (video lên sóng < {1} giờ / đã lên sóng)".format(len(gap), GIO_BIA_GAP)) if gap \
        else (DAT, "không có việc bìa gấp")


def d_bia_gap(goc, kenh):
    bay = _gio()
    gap = _bia_gap(goc, kenh, bay)
    if not gap:
        return False, "không có việc bìa gấp"
    if 2 <= bay.hour < 5:
        return False, "đang khe đêm 02–05 — agent tự sửa"
    dem = bay.replace(hour=2, minute=0, second=0, microsecond=0)
    dem += _dt.timedelta(days=1) if dem <= bay else _dt.timedelta(0)
    if dem - bay <= _dt.timedelta(hours=2) and not any(v.get("doi") for v in gap):
        return False, "khe đêm 02:00 còn ≤ 2 giờ — để agent sửa"
    ly = (_san_sang_dom(goc, kenh) or ("kênh tắt sua_video" if _cau_hinh_vm(goc, kenh).get("sua_video") is False else "")
          or _nhuong_phien(goc, bay)
          or ("đang có máy đăng dở (dang-dodang.json)" if os.path.exists(_vm(goc, "logs", "dang-dodang.json")) else ""))
    if ly:
        return False, ly
    v = min(gap, key=lambda x: x["len_song"])
    return True, "{0} việc bìa chờ — video {1} {2}, khe đêm còn xa".format(
        len(gap), "đã lên sóng" if v["len_song"] <= bay else "lên sóng", v["len_song"].strftime("%H:%M %d/%m"))


def c_bia_gap(goc, kenh):
    return _py(os.path.join(goc, "vm", "may_dang_dom.py"), "--kenh", kenh, "--sua-video", "--toi-da-video", "2")


# S05 · Dấu cổng chữ cho gói chờ đăng (16/10/2026) ────────────────────────────

def _goi_chua_dau(goc, kenh) -> List[str]:
    """Mã gói chờ đăng (kế hoạch chưa ĐÃ ĐĂNG, còn thư mục ở DONE) mà bìa CHƯA có dấu cổng chữ — máy đăng sẽ GIỮ gói."""
    try:
        from core import cong_chu  # noqa: PLC0415
        return [g["ma"] for g in cong_chu.goi_cho_dang(goc, kenh) if cong_chu.kiem_dau(g["anh"])]
    except Exception:  # noqa: BLE001
        return []


def k_dau_bia(goc, kenh):
    if _dang_o_may_khac(goc, kenh):
        return KHONG, "đăng ở máy khác"
    ds = _goi_chua_dau(goc, kenh)
    return (CHO, "{0} gói chờ đăng chưa có dấu cổng chữ ({1}) — máy đăng giữ".format(len(ds), ", ".join(ds[:3])))         if ds else (DAT, "mọi gói chờ đăng có dấu cổng chữ")


def d_dau_bia(goc, kenh):
    ds = [] if _dang_o_may_khac(goc, kenh) else _goi_chua_dau(goc, kenh)
    return (True, "{0} gói chờ đăng chưa có dấu cổng chữ".format(len(ds))) if ds else (False, "không có gói thiếu dấu")


# S04 · Bàn giao lượt kẹt cấu hình ─────────────────────────────────────────────

#: Lý do dừng nhắc tới khoá kenh.yaml = lỗi CẤU HÌNH (sửa khoá là bàn giao được) — không phải lỗi máy chủ.
DAU_CAU_HINH = ("thu_muc_done", "kenh.yaml")


def luot_ket_cau_hinh(goc, kenh, so_ngay: int = 7) -> List[Tuple[str, str, str]]:
    """[(ngày sổ, mã lượt, lý do)] — lượt có `8-video.mp4`, `da_ban_giao: false`, lý do dừng GẦN NHẤT (lỗi bàn giao >
    lý do để trống > lý do bỏ của L3) là lỗi cấu hình. Chỉ xét sổ `so_ngay` ngày gần nhất (cửa sổ nhặt lại của L3)."""
    ra = []
    for p in sorted(glob.glob(os.path.join(goc, "CHANNEL", kenh, "tu-chay", "????-??-??.json")))[-so_ngay:]:
        for r in (_json(p) or {}).get("runs") or []:
            bg = r.get("ban_giao") if isinstance(r.get("ban_giao"), dict) else {}
            luot = str(r.get("ma_luot") or "")
            if not luot or bg.get("da_ban_giao"):
                continue
            ly = str(bg.get("loi") or bg.get("ly_do_trong") or r.get("ly_do_bo") or "")
            # = core.auto.duong_luot(goc, kenh, luot)
            if any(d in ly for d in DAU_CAU_HINH) and os.path.isfile(os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "8-video.mp4")):
                ra.append((os.path.basename(p)[:10], luot, ly))
    return ra


def k_ban_giao_ket(goc, kenh):
    ds = luot_ket_cau_hinh(goc, kenh)
    return (LOI, "{0} lượt xong video mà kẹt cấu hình: {1}".format(len(ds), ", ".join(x[1] for x in ds))) if ds \
        else (DAT, "không có lượt kẹt cấu hình")


def d_ban_giao_ket(goc, kenh):
    ds = luot_ket_cau_hinh(goc, kenh)
    if not ds:
        return False, "không có lượt xong video mà kẹt cấu hình"
    from core.kenh import doc_kenh  # noqa: PLC0415
    if not doc_kenh(goc, kenh).thu_muc_done:
        return False, "kenh.yaml vẫn chưa có thu_muc_done — xem S02"
    dp = {x.get("ma"): x for x in ((_json(goc, "workspace", "khe", "dieu-phoi.json") or {}).get("kenh") or [])
          if isinstance(x, dict)}
    if (dp.get(kenh) or {}).get("dang_chay"):
        return False, "kênh đang chạy lượt — để tu_chay tự bàn giao"
    ngay, luot, ly = ds[0]
    return True, "lượt {0} (sổ {1}) xong video mà kẹt cấu hình: {2}".format(luot, ngay, ly[:90])


def c_ban_giao_ket(goc, kenh):
    ngay, luot, _ly = luot_ket_cau_hinh(goc, kenh)[0]
    return _py("-m", "core.ban_giao_dang", "ban-giao-tay", kenh, luot, ngay)


# D09 · Thương hiệu kênh (hình mờ) ─────────────────────────────────────────────

NGAY_KIEM_THUONG_HIEU = 30


def _thuong_hieu(goc, kenh) -> dict:
    """Kết quả `vm/thiet_lap_kenh_dom.py --kiem-thuong-hieu` mới nhất (`<K>.thuong-hieu.json`)."""
    return _json(_vm(goc, "logs", "thiet-lap-kenh", kenh + ".thuong-hieu.json")) or {}


def _viec_thuong_hieu(goc, kenh, bay) -> Tuple[str, str]:
    """('kiem' | 'dat' | '', lý do): chưa kiểm / kiểm cũ ≥ 30 ngày / lần trước chưa xong → kiểm (chỉ đọc); kiểm thấy
    THIẾU hình mờ → gắn (`--dat-hinh-mo` đọc lại trước khi gắn)."""
    d = _thuong_hieu(goc, kenh)
    luc = _doc_luc(d.get("luc"))
    if not d or luc is None:
        return "kiem", "chưa kiểm thương hiệu (hình mờ)"
    co = True if (d.get("dat_hinh_mo") or {}).get("ket") == "dat" else (d.get("hinh_mo") or {}).get("co")
    if co is False:
        return "dat", "kiểm {0} thấy THIẾU hình mờ".format(luc.strftime("%d/%m"))
    tuoi = (bay - luc).total_seconds() / 86400
    if tuoi >= NGAY_KIEM_THUONG_HIEU:
        return "kiem", "kết quả kiểm cũ {0:.0f} ngày".format(tuoi)
    if str(d.get("ket_qua") or "") != "xong":
        return "kiem", "lần kiểm {0} chưa xong: {1}".format(luc.strftime("%d/%m"), str(d.get("ket_qua"))[:60])
    return "", "hình mờ {0} · kiểm {1:.0f} ngày trước".format("có" if co else "chưa đọc được", tuoi)


def k_thuong_hieu(goc, kenh):
    viec, ly = _viec_thuong_hieu(goc, kenh, _gio())
    if not viec:
        return DAT, ly
    return (LOI if viec == "dat" else (THIEU if not _thuong_hieu(goc, kenh) else CHO)), ly


def d_thuong_hieu(goc, kenh):
    bay = _gio()
    viec, ly = _viec_thuong_hieu(goc, kenh, bay)
    if not viec:
        return False, ly
    chan = _san_sang_dom(goc, kenh) or _khung_thiet_lap(bay)
    return (False, chan) if chan else (True, ly)


def c_thuong_hieu(goc, kenh):
    viec, _ly = _viec_thuong_hieu(goc, kenh, _gio())
    return _py(os.path.join(goc, "vm", "thiet_lap_kenh_dom.py"), "--kenh", kenh, "--kiem-thuong-hieu") + \
        (["--dat-hinh-mo"] if viec == "dat" else [])


# K20 · Trang chủ + video giới thiệu ───────────────────────────────────────────

NGAY_LAM_MOI_GIOI_THIEU = 30


def _trang_chu(goc, kenh) -> Dict[str, Any]:
    """{bat, trailer, vid, luc_dat} theo kết quả thương hiệu mới nhất: lượt có `--dat-trang-chu` đạt → bản ĐỌC LẠI sau
    Xuất bản; lượt chỉ kiểm → bản đọc. `luc_dat` = lần máy đặt trang chủ đạt gần nhất (bản này hoặc `lich_su`)."""
    d = _thuong_hieu(goc, kenh)
    dt = d.get("dat_trang_chu") if isinstance(d.get("dat_trang_chu"), dict) else {}
    if dt.get("ket") == "dat":
        dl = dt.get("doc_lai") if isinstance(dt.get("doc_lai"), dict) else {}
        tr = dl.get("trailer") if isinstance(dl.get("trailer"), dict) else {}
        vid = (list(tr.get("ma") or []) + [((d.get("chon_video") or {}).get("gioi_thieu") or {}).get("vid")])[0]
        return {"bat": dl.get("bat"), "trailer": bool(tr.get("co")), "vid": vid, "luc_dat": str(d.get("luc") or "")}
    td = (d.get("tieu_diem") or {}).get("trailer")
    luc = [str(x.get("luc")) for x in d.get("lich_su") or [] if isinstance(x, dict) and x.get("dat_trang_chu") == "dat"]
    return {"bat": d.get("trang_chu_bat"), "trailer": bool(td.get("co") if isinstance(td, dict) else td), "vid": None,
            "luc_dat": max(luc) if luc else ""}


def _video_thang_nhat(goc, kenh, bay) -> Optional[dict]:
    """Video giới thiệu theo ĐÚNG luật của `--dat-trang-chu` (`thiet_lap_kenh_dom.xep_video_gioi_thieu`: dài, ≥ 7 ngày,
    hiển thị × tỷ lệ bấm), bỏ video lần trước Studio đọc là KHÔNG công khai."""
    import csv  # noqa: PLC0415
    try:
        with open(os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv"), "r", encoding="utf-8-sig", newline="") as tep:
            hang = list(csv.DictReader(tep))
    except OSError:
        return None
    loai = ((_thuong_hieu(goc, kenh).get("chon_video") or {}).get("loai")) or {}
    ung = _nap_vm("thiet_lap_kenh_dom").xep_video_gioi_thieu(hang, _kenh_yaml(goc, kenh).get("ngay_bat_dau"), bay.date())
    return next((u for u in ung if loai.get(u["vid"]) in (None, "cong_khai")), None)


def _viec_trang_chu(goc, kenh, bay) -> Tuple[bool, str]:
    if not _thuong_hieu(goc, kenh):
        return False, "chưa kiểm thương hiệu — chờ D09"
    thang = _video_thang_nhat(goc, kenh, bay)
    if not thang:
        return False, "chưa có video đủ chuẩn làm video giới thiệu (dài, ≥ 7 ngày, có lượt bấm)"
    tc = _trang_chu(goc, kenh)
    if not tc["bat"] or not tc["trailer"]:
        return True, "thẻ Trang chủ {0}".format("tắt" if not tc["bat"] else "bật mà chưa có video giới thiệu")
    from core import ky_nang_tu  # noqa: PLC0415 — sổ chạy (lần K20 xong cuối)
    luc = _doc_luc(max(tc["luc_dat"], ky_nang_tu.lan_xong_cuoi(goc, "K20", kenh)))
    if luc is None or (bay - luc).days < NGAY_LAM_MOI_GIOI_THIEU:
        return False, "trang chủ bật, có video giới thiệu{0}".format(" (đặt {0:%d/%m})".format(luc) if luc else "")
    if tc["vid"] and tc["vid"] == thang["vid"]:
        return False, "video giới thiệu vẫn là video thắng nhất"
    return True, "đã {0} ngày — video thắng nhất {1}, cập nhật video giới thiệu".format(
        (bay - luc).days, "đã đổi" if tc["vid"] else "có thể đã đổi")


def k_trang_chu(goc, kenh):
    if not _thuong_hieu(goc, kenh):
        return THIEU, "chưa kiểm thương hiệu (D09)"
    can, ly = _viec_trang_chu(goc, kenh, _gio())
    tc = _trang_chu(goc, kenh)
    return (THIEU if not (tc["bat"] and tc["trailer"]) else (CHO if can else DAT)), ly


def d_trang_chu(goc, kenh):
    bay = _gio()
    can, ly = _viec_trang_chu(goc, kenh, bay)
    if not can:
        return False, ly
    chan = _san_sang_dom(goc, kenh) or _khung_thiet_lap(bay)
    return (False, chan) if chan else (True, ly)


def c_trang_chu(goc, kenh):
    return _py(os.path.join(goc, "vm", "thiet_lap_kenh_dom.py"), "--kenh", kenh, "--dat-trang-chu")


# D10 · Đòn bẩy đăng ký · D11 · Lô bìa (chỉ báo) ───────────────────────────────

def k_don_bay_sub(goc, kenh):
    from core import chuyen_doi_sub, kenh_khong_phat  # noqa: PLC0415
    from core.kenh import doc_kenh  # noqa: PLC0415
    if kenh_khong_phat.dang_dung(goc, kenh)[0]:
        return KHONG, "kênh không được phát — chưa cần đòn bẩy đăng ký"
    bat, ly = chuyen_doi_sub.kenh_bat(goc, doc_kenh(goc, kenh))
    return (DAT, "đang bật ({0})".format(ly)) if bat else \
        (THIEU, "kênh có phân phối mà đòn bẩy đăng ký tắt ({0}) — nên bật chuyen_doi_sub".format(ly))


def k_bia_lo(goc, kenh):
    from core import bia_theo_khuon  # noqa: PLC0415
    tk = bia_theo_khuon.trang_thai_khai_thac(goc, kenh)
    if tk.get("che_do") != "khai_thac":
        return KHONG, "chưa có khuôn thắng thật ({0})".format(str(tk.get("ly_do") or "?")[:70])
    if _kenh_yaml(goc, kenh).get("bia_lo") is True:
        return DAT, "bia_lo đang bật"
    return THIEU, "có khuôn thắng thật ({0}) mà chưa bật bia_lo — nên bật".format(str(tk.get("ly_do") or "")[:70])


def _chi_bao(kiem):
    """Điều kiện của kỹ năng chỉ báo: kiểm ra THIẾU = nên chạy."""
    def dieu_kien(goc, kenh):
        tt, ly = kiem(goc, kenh)
        return tt == THIEU, ly
    return dieu_kien


# D12 · Não bộ phận khỏe ───────────────────────────────────────────────────────

GIO_GOM_CU, GIO_NGU_CU = 2.0, 30.0


def _nao_bp(goc) -> Tuple[Optional[float], Optional[float], bool]:
    """(giờ từ lần gom cuối, giờ từ giấc ngủ cuối không lỗi, có kho) — đọc CHỈ ĐỌC `nao/bo-phan.db`. Mốc gom = meta
    `gom_cuoi` (`nao_bo_phan.gom` ghi); kho cũ chưa có mốc thì lấy giờ sửa tệp kho/WAL."""
    import sqlite3  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415
    p = os.path.join(goc, "nao", "bo-phan.db")
    if not os.path.isfile(p):
        return None, None, False
    gom = ngu = None
    for che_do in ("mode=ro", "immutable=1"):
        try:
            con = sqlite3.connect("file:{0}?{1}".format(urllib.request.pathname2url(p), che_do), uri=True, timeout=1)
            try:
                r = con.execute("SELECT gia_tri FROM meta WHERE khoa = 'gom_cuoi'").fetchone()
                gom = float(r[0]) if r and r[0] else None
                ngu = con.execute("SELECT MAX(luc) FROM giac_ngu WHERE loi = ''").fetchone()[0]
            finally:
                con.close()
            break
        except (sqlite3.Error, ValueError, TypeError):
            continue
    if gom is None:
        gom = max(os.path.getmtime(x) for x in (p, p + "-wal") if os.path.isfile(x))
    bay = _gio().timestamp()
    return (bay - gom) / 3600.0, (None if ngu is None else (bay - float(ngu)) / 3600.0), True


def k_nao_bp(goc, kenh):
    gom, ngu, co = _nao_bp(goc)
    if not co:
        return THIEU, "chưa có kho não bộ phận (nao/bo-phan.db)"
    loi = (["gom cũ {0:.1f} giờ".format(gom)] if gom > GIO_GOM_CU else []) + \
        (["chưa ngủ {0}".format("lần nào" if ngu is None else "{0:.0f} giờ".format(ngu))] if ngu is None or ngu > GIO_NGU_CU else [])
    return (LOI, " · ".join(loi)) if loi else (DAT, "gom {0:.1f} giờ trước · ngủ {1:.0f} giờ trước".format(gom, ngu))


def d_nao_bp(goc, kenh):
    gom, _ngu, co = _nao_bp(goc)
    if not co:
        return True, "chưa có kho não bộ phận — gom lần đầu"
    return (True, "gom não bộ phận cũ {0:.1f} giờ (> {1:.0f})".format(gom, GIO_GOM_CU)) if gom > GIO_GOM_CU else \
        (False, "gom {0:.1f} giờ trước".format(gom))


# D13 · Thử nghiệm và so sánh bìa · D14 · Đọc sức khoẻ Studio (hàng việc máy có kiểu, 16/10/2026) ────────────────
# Bộ chạy `vm/studio_may_dom.py` (phần thuần `core/studio_may.py`). Mỗi lượt tự kích hoạt tối đa MỘT việc nặng = MỘT kênh;
# bộ chạy tự kiểm khoá máy / van IPv4 / phiên đăng / Chrome kênh đang mở → hoãn (mã 10, không tính hỏng, việc giữ `cho`).

NHIP_TEST_GIO, NHIP_SUC_KHOE_GIO = 3, 6


def _studio_may_chan(goc, kenh) -> str:
    return _san_sang_dom(goc, kenh) or _khung_thiet_lap(_gio()) or \
        ("đang có máy đăng dở (dang-dodang.json)" if os.path.exists(_vm(goc, "logs", "dang-dodang.json")) else "")


def k_test_compare(goc, kenh):
    from core import studio_may  # noqa: PLC0415
    dung, ly = studio_may.dieu_kien_test(goc, kenh)
    return (CHO, ly) if dung else (DAT, ly)


def d_test_compare(goc, kenh):
    from core import studio_may  # noqa: PLC0415
    dung, ly = studio_may.dieu_kien_test(goc, kenh)
    if not dung:
        return False, ly
    chan = _studio_may_chan(goc, kenh)
    return (False, chan) if chan else (True, ly)


def k_suc_khoe_studio(goc, kenh):
    from core import studio_may  # noqa: PLC0415
    dung, ly = studio_may.dieu_kien_suc_khoe(goc, kenh, _gio())
    if dung:
        return CHO, ly
    d = studio_may.lan_doc_suc_khoe(goc, kenh)
    if not d:
        return DAT, ly
    return (LOI if d.get("canh_bao") else DAT), "đọc Studio {0}: {1}".format(str(d.get("luc"))[:16], str(d.get("chi_tiet"))[:90])


def d_suc_khoe_studio(goc, kenh):
    from core import studio_may  # noqa: PLC0415
    dung, ly = studio_may.dieu_kien_suc_khoe(goc, kenh, _gio())
    if not dung:
        return False, ly
    if studio_may.con_moi_suc_khoe(goc, kenh, _gio()):
        return True, ly                    # đóng việc bằng lần đọc còn mới — không mở Chrome, khỏi chờ khung
    chan = _studio_may_chan(goc, kenh)
    return (False, chan) if chan else (True, ly)


# D15 · Danh sách phát chủ đề (16/10/2026) ──────────────────────────────────────────────────────────────────────
# Phần thuần + LLM `core/danh_sach_phat.py`, bộ chạy DOM `vm/danh_sach_phat_dom.py` (khung `studio_may_dom.chay_phien`).
# Kênh khai `danh_sach_phat_kenh` trong kenh.yaml → K14 lo, D15 đứng ngoài; kênh chưa được phát → bỏ.

NHIP_DSP_GIO = 3


def k_danh_sach_phat(goc, kenh):
    from core import danh_sach_phat as dsp  # noqa: PLC0415
    if dsp.ten_yaml(goc, kenh):
        return KHONG, "kenh.yaml khai danh_sach_phat_kenh (K14)"
    dung, ly = dsp.can_chay(goc, kenh, _gio())
    co = bool(dsp.doc(goc, kenh).get("danh_sach"))
    if dung:
        return (CHO if co else THIEU), ly
    return (DAT if co else KHONG), ly


def d_danh_sach_phat(goc, kenh):
    from core import danh_sach_phat as dsp  # noqa: PLC0415
    dung, ly = dsp.can_chay(goc, kenh, _gio())
    if not dung:
        return False, ly
    chan = _studio_may_chan(goc, kenh)
    return (False, chan) if chan else (True, ly)


# D16 · Phát hiện tụt · D17 · Soát sản phẩm tuần · S06 · Sửa bìa sai chữ đang chạy (17/10/2026) ───────────────

def _bao_cao_bat_thuong(goc, kenh) -> dict:
    return _json(goc, "workspace", "tu-kiem", "bat-thuong", kenh + ".json") or {}


def k_bat_thuong(goc, kenh):
    d = _bao_cao_bat_thuong(goc, kenh)
    if not d:
        return THIEU, "chưa phát hiện tụt lần nào"
    p = d.get("phat_hien") or {}
    if p.get("tut"):
        return LOI, "tụt {0} từ {1}: {2}".format(", ".join(p["tut"]), d.get("tut_tu") or "?", "; ".join(d.get("gay") or [])[:90])
    return DAT, "lúc {0}: {1}".format(str(d.get("luc"))[:16], "không tụt" if p.get("du") else p.get("ly_do", "")[:80])


def d_bat_thuong(goc, kenh):
    if _dang_o_may_khac(goc, kenh):
        return False, "kênh làm ở máy khác"
    t = _tuoi_gio(os.path.join(goc, "workspace", "tu-kiem", "bat-thuong", kenh + ".json"))
    return (True, "chưa phát hiện tụt lần nào") if t is None else         ((t >= 20, "lần phát hiện cuối {0:.0f} giờ trước".format(t)))


def k_soat_tuan(goc, kenh):
    from core import soat_san_pham as ss  # noqa: PLC0415
    ls = ss.doc_lich_su(goc, kenh)
    if not ls:
        return THIEU, "chưa soát sản phẩm lần nào"
    x = ls[-1]
    return (LOI if x.get("anh_xau") or (x.get("bia") or {}).get("sai") else DAT), "soát {0}: ảnh {1} · bìa sai {2} · chép {3}".format(
        str(x.get("luc"))[:10], (x.get("anh") or {}).get("dat_ca"), len((x.get("bia") or {}).get("sai") or []),
        (x.get("doc_dao") or {}).get("ti_le_chep"))


def d_soat_tuan(goc, kenh):
    if _dang_o_may_khac(goc, kenh):
        return False, "kênh làm ở máy khác"
    from core import soat_san_pham as ss  # noqa: PLC0415
    return ss.can_chay(goc, kenh, _gio())


def _viec_sua_bia(goc, kenh) -> list:
    from core import bat_thuong  # noqa: PLC0415
    return bat_thuong.viec_sua_bia(goc, kenh)


def k_sua_bia(goc, kenh):
    ds = _viec_sua_bia(goc, kenh)
    return (CHO, "{0} bìa đang chạy sai chữ chờ sửa".format(len(ds))) if ds else (DAT, "không có bìa sai chữ chờ sửa")


def d_sua_bia(goc, kenh):
    ds = _viec_sua_bia(goc, kenh)
    return (True, "{0} bìa sai chữ chờ sửa ({1})".format(len(ds), ds[0].get("ma"))) if ds else (False, "không có")


def c_sua_bia(goc, kenh):
    ds = _viec_sua_bia(goc, kenh)
    return _py("-m", "core.bat_thuong", "sua-bia", "--kenh", kenh, "--vid", str(ds[0].get("vid") if ds else ""))


# ── DANH MỤC ───────────────────────────────────────────────────────────────────

DANH_MUC: List[KyNang] = [
    # KHỞI TẠO — một lần mỗi kênh, theo thứ tự chạy
    KyNang("K01", "Chrome kênh đã đăng nhập", "khoi_tao", "Chrome Portable riêng của kênh đã đăng nhập Google/YouTube; đọc lại bằng kiểm DOM (UC kênh).",
           "nguoi: đăng nhập Chrome · rồi python vm/may_dang_dom.py --kenh K --kiem-dom", k_chrome, ["nguoi:dang_nhap_chrome"]),
    KyNang("K02", "Tài khoản kênh (kho bí mật)", "khoi_tao", "Email/mật khẩu/2FA cất mã hoá DPAPI ở bi-mat/ (không lên git).",
           "nguoi: điền dữ liệu ban đầu", k_tai_khoan, ["nguoi:du_lieu_ban_dau"]),
    KyNang("K03", "Ngách + tuyến + tệp khán giả", "khoi_tao", "ngach.yaml, nhóm/tệp trong kenh.yaml, tuyến nội dung.",
           "python -m core.khoi_tao_ngach --chu-de \"…\" --quoc-gia QG --ngon-ngu NN --ma-kenh K", k_ngach, ["K01"]),
    KyNang("K04", "Giọng đọc", "khoi_tao", "voice_id của nhà cung cấp giọng, lấy từ kho giọng (kho-giong.json).", "nguoi: điền voice_id trong kenh.yaml (nhóm có kho-giong.json thì mo_kenh chuan-bi tự gán)", k_giong, []),
    KyNang("K05", "Nhân vật tham chiếu", "khoi_tao", "Ảnh nv/ — mọi ảnh cảnh và bìa vẽ đúng nhân vật này.", "core.thiet_lap_kenh (ảnh ShopAPI)", k_nhan_vat, []),
    KyNang("K06", "Ngôn ngữ hiển thị + địa điểm", "khoi_tao", "youtube.com → menu avatar → Ngôn ngữ/Địa điểm = nước kênh; đọc lại menu.",
           "python vm/thiet_lap_kenh_dom.py --kenh K --ngon-ngu", k_ngon_ngu, ["K01"]),
    KyNang("K07", "Tên kênh", "khoi_tao", "Studio → Tuỳ chỉnh → tên; đọc lại trang công khai.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("ten"), ["K01", "K06"]),
    KyNang("K08", "Handle", "khoi_tao", "@handle theo tên kênh; YouTube giới hạn đổi 14 ngày.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("handle"), ["K07"]),
    KyNang("K09", "Mô tả + từ khoá + quốc gia", "khoi_tao", "SEO kênh, quốc gia cư trú = nước kênh.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("mo_ta"), ["K06"]),
    KyNang("K10", "Logo", "khoi_tao", "Ảnh ShopAPI theo hồ sơ; đọc lại trang công khai.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("logo"), ["K05"]),
    KyNang("K11", "Banner", "khoi_tao", "Ảnh ShopAPI theo hồ sơ.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("banner"), ["K05"]),
    KyNang("K12", "Hình mờ", "khoi_tao", "Watermark kênh.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("hinh_mo"), ["K10"]),
    KyNang("K13", "Mặc định tải lên (Giáo dục)", "khoi_tao", "Danh mục Giáo dục + ngôn ngữ video/mô tả mặc định.", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("mac_dinh"), ["K06"]),
    KyNang("K14", "Danh sách phát", "khoi_tao", "Tạo các danh sách phát theo cụm nội dung (danh_sach_phat_kenh).", "python vm/thiet_lap_kenh_dom.py --kenh K", _k_muc_thiet_lap("danh_sach_phat"), ["K03"]),
    KyNang("K15", "Bật tự đăng trên máy", "khoi_tao", "may-ao.json: tu_dang=true, cach_dang=tu_dong.", "core.trung_tam.them_kenh_vao_vm", k_may_ao, ["K01"]),
    KyNang("K16", "Danh bạ đối thủ", "khoi_tao", "Nghiên cứu nhóm: chấm hộp thư → doi-thu.csv.", "python tu_chay.py --kenh K (bước 1)", k_doi_thu, ["K03"]),
    KyNang("K17", "Nuôi trang chủ", "khoi_tao", "Xem video thắng của đối thủ + Không quan tâm lạc đề tới khi trang chủ >90% chủ đề.",
           "kenh.yaml nuoi_trang_chu: true (agent tự chạy)", k_nuoi, ["K06"]),
    KyNang("K18", "OAuth client (dùng chung)", "khoi_tao", "Tệp client Google Cloud (đã xuất bản) ở vm/clients/ — mở đường API bình luận.",
           "nguoi: tạo OAuth client một lần", k_oauth_client, ["nguoi:google_cloud"]),
    KyNang("K19", "Token bình luận (API)", "khoi_tao", "Đồng ý một lần trong Chrome kênh → vm/tokens/<K>.json. Không có thì bình luận chạy DOM.",
           "python vm/setup_oauth.py --kenh K", k_token, ["K18", "K01"]),
    KyNang("K20", "Trang chủ + video giới thiệu", "khoi_tao",
           "Kích hoạt: kết quả kiểm thương hiệu thấy thẻ Trang chủ tắt / chưa có video giới thiệu; hằng tháng video thắng "
           "nhất (luật của chế độ: dài, ≥ 7 ngày, hiển thị × tỷ lệ bấm, công khai) đổi → đặt lại. Đọc lại sau Xuất bản (chủ duyệt 14/10).",
           "python vm/thiet_lap_kenh_dom.py --kenh K --dat-trang-chu", k_trang_chu, ["D09"],
           dieu_kien=d_trang_chu, chay=c_trang_chu, nhip_gio=24, tu_ap=True, nang=True),
    # ĐỊNH KỲ — mỗi ngày
    KyNang("D01", "Quét ngày", "dinh_ky", "Studio + trang chủ + lời thoại → số liệu học (agent, sau 05:00).", "agent (tự)", k_quet_ngay, ["K01"]),
    KyNang("D02", "Sản xuất + bàn giao video ngày mai", "dinh_ky", "Nghiên cứu → chọn nguồn → 8 khâu → QA → bàn giao lịch 05:00.", "tu_chay.py (điều phối)", k_kho_dem, ["K03", "K04", "K05"]),
    KyNang("D03", "Bình luận (mồi + trả lời)", "dinh_ky", "Phiên kênh, DOM: đăng mồi + trả lời bình luận mới — đúng NỘI DUNG video (lời thoại từ phụ đề gói), giọng kênh, đúng ngôn ngữ kênh, gõ như người (không emoji/kaomoji).", "agent phiên kênh · thử không đăng: workspace/cong-cu-dieu-phoi/thu_tra_loi.py", k_binh_luan, ["K01"]),
    KyNang("D04", "Vòng tự học", "dinh_ky", "Bảng điểm cụm/công thức/bìa/tiêu đề/hook theo số Studio.", "tu_chay.py (bước 0)", k_tu_hoc, ["D01"]),
    KyNang("D05", "Bộ não", "dinh_ky", "Phiên sáng (06:45, đợi quét Studio xong): chấm dự đoán, chương trình 6 việc, ghi nhớ.", "ShopAPI-Nao", k_nao, []),
    KyNang("D06", "Bù màn hình kết thúc", "dinh_ky", "Video thiếu MHKT → bù giờ vắng 02:00–05:00.", "agent --bu-mhkt", k_mhkt_thieu, ["K01"]),
    KyNang("D07", "Đường tới YPP", "dinh_ky", "Dự báo ngày đủ 4000 giờ + 1000 đăng ký từ chỉ số Studio hằng ngày (cận dưới theo cửa sổ 28 ngày); cảnh báo khi gần/đạt.",
           "python -m core.ypp · --canh-bao", k_ypp, ["D01"]),
    KyNang("D08", "Kéo view chéo", "dinh_ky", "Kênh lớn thêm video kênh em vào danh sách phát (playlist tự học từ hộp Lưu, AI chọn theo nghĩa); mỗi lần thêm có dự đoán, đo sau 7 ngày.",
           "python vm/keo_cheo_dom.py --ke-hoach (agent tự chạy 1 lần/ngày)", k_keo_cheo, ["D01"]),
    KyNang("D09", "Thương hiệu kênh (hình mờ)", "dinh_ky",
           "Kích hoạt: chưa có kết quả kiểm thương hiệu hoặc cũ > 30 ngày → kiểm (CHỈ ĐỌC hình mờ, trailer, video nổi bật); "
           "kiểm thấy THIẾU hình mờ → gắn (toàn bộ video), đọc lại.",
           "python vm/thiet_lap_kenh_dom.py --kenh K --kiem-thuong-hieu [--dat-hinh-mo]", k_thuong_hieu, ["K01"],
           dieu_kien=d_thuong_hieu, chay=c_thuong_hieu, nhip_gio=24, tu_ap=True, nang=True),
    KyNang("D10", "Đòn bẩy đăng ký", "dinh_ky",
           "Kích hoạt: kênh có phân phối (không bị cờ «không phát») mà `chuyen_doi_sub` đang tắt → CHỈ BÁO nên bật.",
           "kenh.yaml: chuyen_doi_sub: {bat: true} (chủ duyệt)", k_don_bay_sub, ["D01"],
           dieu_kien=_chi_bao(k_don_bay_sub), tu_ap=False),
    KyNang("D11", "Lô bìa", "dinh_ky",
           "Kích hoạt: kênh có khuôn bìa thắng THẬT (đủ bằng chứng, đang khai thác) mà chưa bật `bia_lo` → CHỈ BÁO nên bật.",
           "kenh.yaml: bia_lo: true (chủ duyệt)", k_bia_lo, ["D01"], dieu_kien=_chi_bao(k_bia_lo), tu_ap=False),
    KyNang("D12", "Não bộ phận khỏe", "dinh_ky",
           "Kích hoạt (toàn máy): lần gom nao/bo-phan.db cũ > 2 giờ → gom lại; giấc ngủ cuối cũ > 30 giờ → báo Việc của bạn.",
           "python -m core.nao_bo_phan gom", k_nao_bp, [],
           dieu_kien=d_nao_bp, chay=lambda goc, kenh: _py("-m", "core.nao_bo_phan", "gom"), nhip_gio=1, tu_ap=True,
           toan_may=True),
    KyNang("D13", "Thử nghiệm A/B tiêu đề + bìa", "dinh_ky",
           "Kích hoạt: hàng việc máy có `studio_test_compare` (đề xuất bộ não) hoặc `studio_ab_tieu_de` (giám đốc kênh: "
           "video mới / video trượt, kenh.yaml `ab_tieu_de`) → Studio, trang sửa video, «Thử nghiệm A/B»: «Tiêu đề và "
           "hình thu nhỏ» (tiêu đề A + 1–2 tiêu đề đã soát, bìa A + 1–2 bìa có dấu cổng chữ) | «Chỉ tiêu đề» | «Chỉ hình "
           "thu nhỏ» → Lưu → đọc lại thử nghiệm STARTED + tiêu đề. Video đã có thử nghiệm → không đụng. Kênh thiếu tính "
           "năng nâng cao / không còn ứng viên → bỏ việc.",
           "python vm/studio_may_dom.py --kenh K --test-compare", k_test_compare, ["K01"],
           dieu_kien=d_test_compare, chay=lambda goc, kenh: _py(os.path.join(goc, "vm", "studio_may_dom.py"), "--kenh", kenh,
                                                                 "--test-compare"),
           nhip_gio=NHIP_TEST_GIO, tu_ap=True, nang=True),
    KyNang("D14", "Đọc sức khoẻ Studio", "dinh_ky",
           "Kích hoạt: hàng việc máy có `studio_kiem_suc_khoe` của kênh (cò sức khoẻ giám đốc) → CHỈ ĐỌC Studio: gậy / cảnh "
           "cáo, kiếm tiền, «nội dung dùng lại»; thấy thật mới báo chủ. Mỗi kênh mở Chrome tối đa 1 lần / 3 ngày.",
           "python vm/studio_may_dom.py --kenh K --suc-khoe", k_suc_khoe_studio, ["K01"],
           dieu_kien=d_suc_khoe_studio, chay=lambda goc, kenh: _py(os.path.join(goc, "vm", "studio_may_dom.py"), "--kenh",
                                                                    kenh, "--suc-khoe"),
           nhip_gio=NHIP_SUC_KHOE_GIO, tu_ap=True, nang=True),
    KyNang("D15", "Danh sách phát chủ đề", "dinh_ky",
           "Kích hoạt: kênh ĐƯỢC PHÁT, kenh.yaml không khai danh_sach_phat_kenh, và chưa có danh sách phát chủ đề / còn "
           "danh sách chưa tạo / video chờ thêm / ≥ 8 video mới chưa vào danh sách nào → LLM gom video đã đăng thành 3–5 "
           "danh sách theo nghĩa (tên + mô tả tiếng kênh, video tốt trước) → nghien-cuu/danh-sach-phat.json → Studio tạo "
           "(Công khai, tên đã có thì dùng lại, không tạo trùng / xoá / đổi tên) → thêm video qua trang sửa Studio (không mở trang xem) → đọc lại. Chỉ video của chính kênh. Video mới lúc bàn "
           "giao: LLM chọn danh sách hợp nhất, hỏng thì danh sách đầu.",
           "python vm/danh_sach_phat_dom.py --kenh K", k_danh_sach_phat, ["K01", "D01"],
           dieu_kien=d_danh_sach_phat, chay=lambda goc, kenh: _py(os.path.join(goc, "vm", "danh_sach_phat_dom.py"),
                                                                   "--kenh", kenh),
           nhip_gio=NHIP_DSP_GIO, tu_ap=True, nang=True),
    # SỬA CHỮA — khi hỏng
    KyNang("S01", "Trả ngôn ngữ giao diện", "sua_chua", "Máy DOM tạm vi chưa trả (chết giữa chừng) → lần chạy sau tự trả.", "tự (ngon_ngu_tam.tra)", k_hl_tam, []),
    KyNang("S02", "Khám cấu hình kênh", "sua_chua",
           "Kênh tự chạy: BOM (U+FEFF) kẹt giữa kenh.yaml → gỡ (chỉ khi YAML chuẩn và bộ đọc tối giản ra cùng giá trị, bản "
           "cũ cất sao-luu); thiếu khoá bắt buộc (thu_muc_done, giờ/nhịp đăng, ngan_sach_ngay > 0, voice_id) → báo Việc "
           "của bạn kèm khoá gợi ý. KHÔNG bao giờ tự bật tu_chay/tu_dang/tu_duyet/tu_don/ngan_sach_ngay.",
           "python -m core.ky_nang go-bom K", k_cau_hinh, [],
           dieu_kien=d_cau_hinh, chay=lambda goc, kenh: _py("-m", "core.ky_nang", "go-bom", kenh), nhip_gio=24, tu_ap=True),
    KyNang("S03", "Đổi bìa gấp", "sua_chua",
           "Kích hoạt: hàng sửa có việc bìa đang chờ cho video lên sóng < 12 giờ hoặc đã lên sóng — hoặc việc sửa bất kỳ "
           "(bìa / tiêu đề) chờ khe đêm quá 36 giờ (đói khe) — mà khe đêm 02–05 còn "
           "> 2 giờ (nhường phiên đăng 60', không đụng máy đăng dở) → sửa video ngay khi khoá máy rảnh.",
           "python vm/may_dang_dom.py --kenh K --sua-video", k_bia_gap, ["K01"],
           dieu_kien=d_bia_gap, chay=c_bia_gap, nhip_gio=1, tu_ap=True, nang=True),
    KyNang("S04", "Bàn giao lượt kẹt", "sua_chua",
           "Kích hoạt: lượt có 8-video.mp4, da_ban_giao false, lý do dừng là lỗi CẤU HÌNH (khoá kenh.yaml — không phải lỗi máy "
           "chủ) và khoá đã sửa → bàn giao đúng luồng bước 5 (khe trống sớm nhất, cổng chất lượng).",
           "python -m core.ban_giao_dang ban-giao-tay K <lượt> <ngày sổ>", k_ban_giao_ket, ["D02"],
           dieu_kien=d_ban_giao_ket, chay=c_ban_giao_ket, nhip_gio=6, tu_ap=True, nang=True),
    KyNang("S05", "Dấu cổng chữ bìa chờ đăng", "sua_chua",
           "Kích hoạt: gói chờ đăng có bìa CHƯA có dấu cổng chữ (bàn giao trước luật 16/10, hoặc bìa đổi tay) → soát chữ bìa, "
           "đọc chữ trên bìa hai lượt khớp tuyệt đối → đóng dấu; bìa sai chữ → bìa dự phòng chữ vẽ bằng mã; AI lỗi → giữ gói, "
           "giờ sau thử lại (máy đăng không bao giờ tải bìa không dấu).",
           "python -X utf8 -m core.cong_chu dau-goi --kenh K", k_dau_bia, ["D02"],
           dieu_kien=d_dau_bia, chay=lambda goc, kenh: _py("-m", "core.cong_chu", "dau-goi", "--kenh", kenh), nhip_gio=1,
           tu_ap=True),
    # TỰ KIỂM – TỰ SỬA – TỰ HOÀN THIỆN (17/10/2026; gác tổng chạy `core.tu_kiem` mỗi 15 phút)
    KyNang("D16", "Phát hiện tụt + tự chẩn đoán", "dinh_ky",
           "Mỗi ngày: hiển thị @72h / CTR / AVD / trang chủ / đăng ký mỗi 1k của video đã qua 96 giờ so nền của CHÍNH "
           "kênh (thước chung). Tụt → soát chữ bìa đang chạy, lệch kiểu bìa, lệch đề tài, lỗi sản xuất → tự xếp sửa bìa "
           "sai chữ (S06), A/B cho video yếu, ghi não.", "python -X utf8 -m core.bat_thuong kenh --kenh K",
           k_bat_thuong, ["D01"], dieu_kien=d_bat_thuong,
           chay=lambda goc, kenh: _py("-m", "core.bat_thuong", "kenh", "--kenh", kenh), nhip_gio=20, tu_ap=True,
           han_phut=40, mot_kenh=True),
    KyNang("D17", "Soát sản phẩm tuần", "dinh_ky",
           "Mỗi tuần: chữ bìa đang chạy, 20 ảnh cảnh qua giám khảo, độ độc đáo kịch bản (kể cả xuyên ngôn ngữ); tỉ lệ "
           "ảnh xấu đi → vòng cải tiến lời nhắc đo trước/sau, chỉ áp vào prompt/7-canh.md khi qua thanh (có sao lưu).",
           "python -X utf8 -m core.soat_san_pham tuan --kenh K", k_soat_tuan, ["D02"], dieu_kien=d_soat_tuan,
           chay=lambda goc, kenh: _py("-m", "core.soat_san_pham", "tuan", "--kenh", kenh), nhip_gio=24 * 6, tu_ap=True,
           han_phut=60, mot_kenh=True),
    KyNang("S06", "Sửa bìa sai chữ đang chạy", "sua_chua",
           "Kích hoạt: hàng `workspace/tu-kiem/viec-sua-bia.json` (D16/D17 thấy bìa ĐANG CHẠY sai chữ) → soát chữ bìa → "
           "bìa lô chữ vẽ bằng mã → đọc lại hai lượt + dấu cổng chữ → xếp đổi bìa (máy DOM), tự kiểm đọc lại i.ytimg.com.",
           "python -X utf8 -m core.bat_thuong sua-bia --kenh K", k_sua_bia, ["D16"], dieu_kien=d_sua_bia,
           chay=c_sua_bia, nhip_gio=1, tu_ap=True, han_phut=40, mot_kenh=True),
]


def theo_ma(ma: str) -> Optional[KyNang]:
    return next((k for k in DANH_MUC if k.ma == ma), None)


def kiem_kenh(goc: str, kenh: str) -> List[Tuple[KyNang, str, str]]:
    ra = []
    for k in DANH_MUC:
        try:
            tt, gc = k.kiem(goc, kenh)
        except Exception as loi:  # noqa: BLE001 — một skill kiểm hỏng không làm vỡ bảng
            tt, gc = LOI, "kiểm lỗi: {0}".format(str(loi)[:60])
        ra.append((k, tt, gc))
    return ra


def thieu_khoi_tao(goc: str, kenh: str) -> List[Tuple[KyNang, str, str]]:
    return [(k, tt, gc) for k, tt, gc in kiem_kenh(goc, kenh) if k.loai == "khoi_tao" and tt in (THIEU, LOI)]


def _cac_kenh(goc: str) -> List[str]:
    """Kênh máy này THẬT SỰ quản lý (khai trong vm/cai-dat-tool.json) — bỏ thư mục khuôn mẫu (vd TL4-T7-v2)."""
    d = _json(_vm(goc, "cai-dat-tool.json")) or {}
    ds = sorted((d.get("kenh") or {}).keys())
    ds = ds or sorted(x for x in os.listdir(os.path.join(goc, "CHANNEL"))
                      if os.path.isfile(os.path.join(goc, "CHANNEL", x, "kenh.yaml")))
    # 19/10: kênh đã TRẢ KHO (core/tra_kho.py) không còn kỹ năng nào chạy/báo
    return [k for k in ds if not str(_kenh_yaml(goc, k).get("tra_kho") or "").strip()]


def _tu_kich_hoat_chu(k: KyNang) -> str:
    """Một ô "Tự kích hoạt" cho bảng md: tự áp / chỉ báo · nhịp · nặng · toàn máy."""
    if k.dieu_kien is None:
        return "—"
    return " · ".join(x for x in ("tự chạy" if k.tu_ap else "chỉ báo", "nhịp {0:g} giờ".format(k.nhip_gio) if k.tu_ap else "",
                                  "nặng (khoá máy)" if k.nang else "", "toàn máy" if k.toan_may else "") if x)


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv) or ["xem"]
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lenh, du = a[0], a[1:]
    if "--goc" in du:                      # đọc dữ liệu ở gốc khác (vd chạy thử trên bản chính từ một worktree)
        i = du.index("--goc")
        goc, du = os.path.abspath(du[i + 1]), du[:i] + du[i + 2:]
    if lenh == "tu-kich-hoat":
        from core import ky_nang_tu  # noqa: PLC0415
        ky_nang_tu.tu_kich_hoat(goc, thu="--thu" in du)
        return 0
    if lenh == "go-bom":
        ok, ly = go_bom(goc, du[0])
        print(ly)
        return 0 if ok else 2
    if lenh == "lich":
        from core import ky_nang_tu  # noqa: PLC0415
        print(ky_nang_tu.lenh_lich(goc))
        return 0
    if lenh == "danh-muc":
        for k in DANH_MUC:
            print("{0} [{1}] {2} — {3}\n     chạy: {4}{5}".format(k.ma, k.loai, k.ten, k.mo_ta, k.lenh,
                                                               "\n     cần: " + ", ".join(k.can) if k.can else ""))
        return 0
    if lenh == "md":
        from core import ky_nang_tu  # noqa: PLC0415
        ten_loai = {"khoi_tao": "KHỞI TẠO — một lần mỗi kênh (chạy theo thứ tự)", "dinh_ky": "ĐỊNH KỲ — mỗi ngày",
                    "sua_chua": "SỬA CHỮA — khi hỏng", "mo_rong": "MỞ RỘNG"}
        d = ["# Danh mục skill", "", "Sinh tự động từ `core/ky_nang.py` (`python -m core.ky_nang md`) — sửa ở mã, không sửa tay.",
             "", "Xem theo kênh: `python -m core.ky_nang xem` · skill khởi tạo còn thiếu: `python -m core.ky_nang thieu <kênh>`.", "",
             "## Tự kích hoạt", "", "Bộ chạy `python -X utf8 -m core.ky_nang tu-kich-hoat [--thu]` (`core/ky_nang_tu.py`), "
             "tác vụ Windows `ShopAPI-KyNang` mỗi giờ phút :35 — chủ tự đăng ký (`python -m core.ky_nang lich` in đúng "
             "đường của máy):", "", "```", ky_nang_tu.lenh_lich("<MyTool>", py="<pythonw.exe>"), "```", "",
             "Luật (mỗi luật một câu):", ""] + ["{0}. {1}".format(i, x) for i, x in enumerate(ky_nang_tu.LUAT, 1)] + [""]
        for loai, ten in ten_loai.items():
            ds = [k for k in DANH_MUC if k.loai == loai]
            if not ds:
                continue
            d += ["## " + ten, "", "| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước | Tự kích hoạt |", "|---|---|---|---|---|---|"]
            d += ["| {0} | {1} | {2} | `{3}` | {4} | {5} |".format(k.ma, k.ten, k.mo_ta, k.lenh, ", ".join(k.can) or "—",
                                                               _tu_kich_hoat_chu(k)) for k in ds]
            d.append("")
        with open(os.path.join(goc, "docs", "KY-NANG.md"), "w", encoding="utf-8") as tep:
            tep.write("\n".join(d))
        print("đã ghi docs/KY-NANG.md")
        return 0
    cac = du or _cac_kenh(goc)
    if lenh == "thieu":
        for kenh in cac:
            ds = thieu_khoi_tao(goc, kenh)
            print("== {0}: {1} skill khởi tạo còn thiếu/hỏng".format(kenh, len(ds)))
            for k, tt, gc in ds:
                print("  {0} {1} {2} — {3}\n      → {4}".format(KY_HIEU[tt], k.ma, k.ten, gc, k.lenh))
        return 0
    bang = {kenh: kiem_kenh(goc, kenh) for kenh in cac}
    print("{0:<5} {1:<34} ".format("mã", "skill") + " ".join("{0:<10}".format(k[:10]) for k in cac))
    for i, k in enumerate(DANH_MUC):
        print("{0:<5} {1:<34} ".format(k.ma, k.ten[:34]) + " ".join("{0:<10}".format(KY_HIEU[bang[kenh][i][1]]) for kenh in cac))
    print("\n✅ đạt  ⬜ thiếu  ❌ hỏng  ⏳ chờ/đang  · không áp — chi tiết: python -m core.ky_nang thieu <kênh>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
