"""DANH MỤC SKILL của tool (05/10/2026) — mỗi việc tool làm được là MỘT skill có định nghĩa rõ.

Chủ dự án: "những công việc định nghĩa là skill khá ok để phát triển và quản lý — 1 kênh khi bắt đầu cần skill gì
chạy, trong quá trình cần skill gì". Mỗi skill khai:
  ma       mã ngắn, duy nhất                     loai   khoi_tao (MỘT LẦN/kênh) | dinh_ky | sua_chua | mo_rong
  ten      tên người đọc                          can    skill/điều kiện phải có trước (mã skill hoặc "nguoi:<việc>")
  kiem     hàm (goc, kenh) -> (trạng thái, ghi chú) — RẺ, chỉ đọc đĩa, không mạng/không tiền
  lenh     cách chạy (dòng lệnh)                  mo_ta  một câu: làm gì, đọc lại bằng gì
Trạng thái: "dat" (xong/khỏe) | "thieu" (chưa làm) | "loi" (hỏng — cần sửa) | "cho" (đang chờ/nghỉ có lý do) | "-" (không áp).

Dùng:  python -m core.ky_nang xem [kênh ...]      bảng skill × kênh
       python -m core.ky_nang danh-muc            mô tả mọi skill
       python -m core.ky_nang thieu <kênh>        skill KHỞI TẠO kênh còn thiếu, theo thứ tự chạy
"""
from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

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
            else (CHO, "chưa có phiên não hôm nay (04:10)"))


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
    # ĐỊNH KỲ — mỗi ngày
    KyNang("D01", "Quét ngày", "dinh_ky", "Studio + trang chủ + lời thoại → số liệu học (agent, sau 05:00).", "agent (tự)", k_quet_ngay, ["K01"]),
    KyNang("D02", "Sản xuất + bàn giao video ngày mai", "dinh_ky", "Nghiên cứu → chọn nguồn → 8 khâu → QA → bàn giao lịch 05:00.", "tu_chay.py (điều phối)", k_kho_dem, ["K03", "K04", "K05"]),
    KyNang("D03", "Bình luận (mồi + trả lời)", "dinh_ky", "Phiên kênh, DOM: đăng mồi + trả lời bình luận mới — đúng NỘI DUNG video (lời thoại từ phụ đề gói), giọng kênh, đúng ngôn ngữ kênh, gõ như người (không emoji/kaomoji).", "agent phiên kênh · thử không đăng: workspace/cong-cu-dieu-phoi/thu_tra_loi.py", k_binh_luan, ["K01"]),
    KyNang("D04", "Vòng tự học", "dinh_ky", "Bảng điểm cụm/công thức/bìa/tiêu đề/hook theo số Studio.", "tu_chay.py (bước 0)", k_tu_hoc, ["D01"]),
    KyNang("D05", "Bộ não", "dinh_ky", "Phiên 04:10: chấm dự đoán, quyết định ≤3 hành động, ghi nhớ.", "ShopAPI-Nao", k_nao, []),
    KyNang("D06", "Bù màn hình kết thúc", "dinh_ky", "Video thiếu MHKT → bù giờ vắng 02:00–05:00.", "agent --bu-mhkt", k_mhkt_thieu, ["K01"]),
    KyNang("D07", "Đường tới YPP", "dinh_ky", "Dự báo ngày đủ 4000 giờ + 1000 đăng ký từ chỉ số Studio hằng ngày (cận dưới theo cửa sổ 28 ngày); cảnh báo khi gần/đạt.",
           "python -m core.ypp · --canh-bao", k_ypp, ["D01"]),
    # SỬA CHỮA — khi hỏng
    KyNang("S01", "Trả ngôn ngữ giao diện", "sua_chua", "Máy DOM tạm vi chưa trả (chết giữa chừng) → lần chạy sau tự trả.", "tự (ngon_ngu_tam.tra)", k_hl_tam, []),
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
    return ds or sorted(x for x in os.listdir(os.path.join(goc, "CHANNEL"))
                        if os.path.isfile(os.path.join(goc, "CHANNEL", x, "kenh.yaml")))


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv) or ["xem"]
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lenh, du = a[0], a[1:]
    if lenh == "danh-muc":
        for k in DANH_MUC:
            print("{0} [{1}] {2} — {3}\n     chạy: {4}{5}".format(k.ma, k.loai, k.ten, k.mo_ta, k.lenh,
                                                               "\n     cần: " + ", ".join(k.can) if k.can else ""))
        return 0
    if lenh == "md":
        ten_loai = {"khoi_tao": "KHỞI TẠO — một lần mỗi kênh (chạy theo thứ tự)", "dinh_ky": "ĐỊNH KỲ — mỗi ngày",
                    "sua_chua": "SỬA CHỮA — khi hỏng", "mo_rong": "MỞ RỘNG"}
        d = ["# Danh mục skill", "", "Sinh tự động từ `core/ky_nang.py` (`python -m core.ky_nang md`) — sửa ở mã, không sửa tay.",
             "", "Xem theo kênh: `python -m core.ky_nang xem` · skill khởi tạo còn thiếu: `python -m core.ky_nang thieu <kênh>`.", ""]
        for loai, ten in ten_loai.items():
            ds = [k for k in DANH_MUC if k.loai == loai]
            if not ds:
                continue
            d += ["## " + ten, "", "| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước |", "|---|---|---|---|---|"]
            d += ["| {0} | {1} | {2} | `{3}` | {4} |".format(k.ma, k.ten, k.mo_ta, k.lenh, ", ".join(k.can) or "—") for k in ds]
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
