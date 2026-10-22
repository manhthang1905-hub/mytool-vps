"""**KHỞI TẠO VPS MỚI cho một NGÁCH MỚI** — một lệnh, máy tự đi hết (22/10/2026, VPS thứ hai: ngách TRUYỆN KỂ).

Chủ dự án: *"đầu vào chỉ là thư mục kho chứa các Chrome đã đăng nhập, voice ID của kênh, và vài đối thủ. Logic: cho các
Chrome xem đúng chủ đề tới khi trang chủ đầy ngách → quét trang chủ ra danh sách đối thủ → từ content đối thủ học ngách
có bao nhiêu TUYẾN → từ đó tạo kênh phát triển và chiếm lĩnh ngách."*

═══ ĐẦU VÀO (thư mục `<cha của MyTool>\\khoi-tao\\`, mẫu ở `docs/ban-sach/khoi-tao-mau/`) ═══
  `..\\kho\\<tên>\\<tên>.exe`  Chrome Portable, mỗi cái ĐÃ ĐĂNG NHẬP Gmail tay (một tài khoản = một kênh).
  `ngach.txt`   `khoa: giá trị` mỗi dòng — chu_de, quoc_gia, ngon_ngu (bắt buộc); khan_gia, khong_nham (cách nhau `;`),
                tu_khoa (`;`), nhom, tien_to (mã kênh, mặc định K); dòng tự do còn lại = mô tả ngách cho AI đọc.
  `giong.txt`   voice_id ElevenLabs, mỗi dòng một giọng, ghi chú sau `#` (tuỳ ý). Mỗi kênh một giọng KHÁC nhau.
  `doi-thu.txt` link/handle kênh đối thủ hạt giống, mỗi dòng một kênh.

═══ CÁC BƯỚC (sổ `workspace/khoi-tao-vps/trang-thai.json`; chạy lại an toàn, sập giữa chừng thì làm tiếp) ═══
  kiem       môi trường + đầu vào (ví ShopAPI, Python, FFmpeg, Whisper, kho có Chrome đã đăng nhập, tệp đầu vào).
  kho        mỗi Chrome kho → mã K1…Kn (`tien_to`), dời ra `<cha>\\<Kx>\\<Kx>.exe` (`core/kho_chrome.lap_dat`, ghi sổ trước).
  ngach      `core/khoi_tao_ngach` (hồ sơ ngách bằng AI + kênh đầu K1 + nghiên cứu khởi động: đối thủ hạt giống vào
             `_NHOM/<nhóm>/doi-thu-them.txt`, tìm theo `tu_khoa_tim`, chuỗi Một nút) · kho giọng nhóm từ giong.txt.
  nuoi       bật `nuoi_trang_chu` cho K1 + bản NHÁP `workspace/chuan-bi-<Kx>/` cho K2…Kn → agent nuôi trang chủ bằng
             video đối thủ (vm/nuoi_trang_chu, D18) tới khi ≥ 90 % đúng chủ đề (sổ `trang_thai: dat`). Chờ tối đa
             `NGAY_NUOI_TOI_DA` ngày rồi đi tiếp với những kênh đã đạt (kênh chưa đạt vẫn nuôi tiếp).
  doi_thu    ô trang chủ mà lượt nuôi đã phán đúng ngách/chủ đề → tra kênh nguồn (yt-dlp) → hộp thư đối thủ K1 → Một
             nút (chốt đối thủ + kiểm ngách THEO NGHĨA bằng hồ sơ ngách + quét content).
  tuyen      `core/tuyen_thi_truong`: content đối thủ → TUYẾN theo nghĩa (LLM) + số đo (nguồn nổ/tháng…) →
             `tep_khan_gia` của ngach.yaml + `workspace/chuan-bi-kenh-moi/thi-truong.json`.
  phan_kenh  chia kênh cho tuyến (danh mục đầu tư, `tuyen_thi_truong.phan_kenh`) → K1 đổi tệp + tuyen.csv; mọi kênh
             vào luồng mở kênh (`core/mo_kenh`, loai `khoi_tao_vps`): góc riêng + nhân vật/kiểu hình/prompt MỚI từ khuôn
             K1 (không chép nhân vật), giọng riêng, hồ sơ/logo/banner.
  mo_kenh    mỗi nhịp: tạo kênh thương hiệu + ghim UC (`vm/tao_kenh_thuong_hieu.py`, một lượt DOM/nhịp) → mo_kenh tự
             ghép máy đăng → thiết lập 11/11 → bật tu_chay/tu_duyet/tu_dang (sản xuất + đăng hằng ngày).
  xong       một tin báo chủ. Về sau: đo lại thị trường mỗi `NGAY_DO_LAI` ngày; kho có Chrome mới đã đăng nhập + giong.txt
             có giọng mới → MỞ RỘNG (quay lại kho → nuôi → … cho kênh mới; kênh cũ giữ tuyến; chừa `KHO_DU_PHONG` Chrome cho
             D20 thay kênh hỏng; tắt: `workspace/cai-dat.json: khoi_tao_vps_mo_rong: false`).

    python -m core.khoi_tao_vps kiem            # chỉ đọc: thiếu gì, việc của người
    python -m core.khoi_tao_vps chay            # đi tiếp các bước tới khi phải chờ (lần đầu: kiem → … → nuoi)
    python -m core.khoi_tao_vps nhip            # một nhịp (skill D28 gọi mỗi giờ khi `can_lam`)
    python -m core.khoi_tao_vps xem             # sổ trạng thái

Máy KHÔNG tự đăng nhập Google, không gõ mật khẩu/2FA, không nạp ví. Mọi LLM đi ví ShopAPI. Một việc nặng mỗi lúc
(DOM tạo kênh dưới khoá máy `nang`; nuôi trang chủ do agent điều phối).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import re
import shutil
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_SO = ("workspace", "khoi-tao-vps", "trang-thai.json")
TEP_NHAT_KY = ("workspace", "khoi-tao-vps", "nhat-ky.log")
THU_MUC_DAU_VAO = "khoi-tao"                      # <cha của MyTool>\khoi-tao\
BUOC = ("kiem", "kho", "ngach", "nuoi", "doi_thu", "tuyen", "phan_kenh", "mo_kenh", "xong")
LOAI_MO_KENH = "khoi_tao_vps"
NGAY_NUOI_TOI_DA = 7
SO_DAT_DE_DI_TIEP = 1                             # hết hạn nuôi: cần ít nhất ngần này kênh đạt để đi tiếp
GIO_THU_LAI = 6.0
SO_O_TRA_TOI_DA = 300                             # ô trang chủ tra kênh nguồn mỗi lượt (yt-dlp, không tiền)
NGAY_DO_LAI = 25
SO_LAN_TAO_KENH_BAO = 3
KHOA_VIEC = "khoi-tao-vps"
KHO_DU_PHONG = 1                                  # Chrome kho chừa lại cho D20 (thay kênh hỏng)


# ── sổ ───────────────────────────────────────────────────────────────────────────────────────────

def _duong(goc: str, phan: Sequence[str]) -> str:
    return os.path.join(goc, *phan)


def _doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)


def doc_so(goc: str) -> Dict[str, Any]:
    so = _doc_json(_duong(goc, TEP_SO), {}) or {}
    so.setdefault("buoc", "")
    so.setdefault("kenh", {})
    so.setdefault("viec_nguoi", [])
    return so


def luu_so(goc: str, so: Dict[str, Any]) -> None:
    so["cap_nhat"] = _bay_gio().strftime("%Y-%m-%d %H:%M")
    _ghi_json(_duong(goc, TEP_SO), so)


def _bay_gio(b: Optional[_dt.datetime] = None) -> _dt.datetime:
    return b or _dt.datetime.now()


def _nhat_ky(goc: str, dong: str) -> None:
    d = _duong(goc, TEP_NHAT_KY)
    try:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        with io.open(d, "a", encoding="utf-8") as tep:
            tep.write("{0} {1}\n".format(_bay_gio().strftime("%Y-%m-%d %H:%M"), dong))
    except OSError:
        pass


def _gio_tu(chu: Any, bay_gio: _dt.datetime) -> Optional[float]:
    try:
        return (bay_gio - _dt.datetime.strptime(str(chu or ""), "%Y-%m-%d %H:%M")).total_seconds() / 3600.0
    except ValueError:
        return None


# ── đầu vào (thuần) ──────────────────────────────────────────────────────────────────────────────

def thu_muc_dau_vao(goc: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(goc)), THU_MUC_DAU_VAO)


def _doc_tep(duong: str) -> str:
    try:
        with io.open(duong, encoding="utf-8-sig") as tep:
            return tep.read()
    except OSError:
        return ""


def doc_ngach_txt(chu: str) -> Dict[str, Any]:
    """`ngach.txt` → {chu_de, quoc_gia, ngon_ngu, khan_gia, khong_nham[], tu_khoa[], nhom, tien_to, mo_ta}. Khoá nhận cả
    tên tiếng Việt có dấu thường gặp (chủ đề / quốc gia / ngôn ngữ / khán giả / không nhắm / từ khoá)."""
    ten = {"chu_de": "chu_de", "chủ đề": "chu_de", "quoc_gia": "quoc_gia", "quốc gia": "quoc_gia",
           "ngon_ngu": "ngon_ngu", "ngôn ngữ": "ngon_ngu", "khan_gia": "khan_gia", "khán giả": "khan_gia",
           "khong_nham": "khong_nham", "không nhắm": "khong_nham", "tu_khoa": "tu_khoa", "từ khoá": "tu_khoa",
           "từ khóa": "tu_khoa", "nhom": "nhom", "nhóm": "nhom", "tien_to": "tien_to", "tiền tố": "tien_to"}
    ra: Dict[str, Any] = {"chu_de": "", "quoc_gia": "", "ngon_ngu": "", "khan_gia": "", "khong_nham": [], "tu_khoa": [],
                          "nhom": "", "tien_to": "K", "mo_ta": ""}
    tu_do: List[str] = []
    for dong in str(chu or "").splitlines():
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        m = re.match(r"^([^:：]{2,20})[:：]\s*(.*)$", d)
        k = ten.get(m.group(1).strip().lower()) if m else None
        if not k:
            tu_do.append(d)
            continue
        gt = m.group(2).strip()
        if k in ("khong_nham", "tu_khoa"):
            ra[k] += [x.strip() for x in re.split(r"[;；|]", gt) if x.strip()]
        else:
            ra[k] = gt
    ra["quoc_gia"] = ra["quoc_gia"].upper()[:2]
    ra["ngon_ngu"] = ra["ngon_ngu"].lower().split("-")[0][:5]
    ra["tien_to"] = re.sub(r"[^A-Za-z0-9-]", "", ra["tien_to"] or "K") or "K"
    ra["mo_ta"] = " ".join(tu_do)[:1500]
    return ra


def doc_giong_txt(chu: str) -> List[Dict[str, str]]:
    """voice_id mỗi dòng (ghi chú sau `#`), bỏ trùng, giữ thứ tự."""
    from .giong_moi import MAU_VOICE  # noqa: PLC0415
    ra, thay = [], set()
    for dong in str(chu or "").splitlines():
        v, _, ghi = dong.partition("#")
        v = v.strip()
        if v and MAU_VOICE.match(v) and v not in thay:
            thay.add(v)
            ra.append({"voice_id": v, "ghi_chu": ghi.strip()[:120]})
    return ra


def doc_doi_thu_txt(chu: str) -> List[str]:
    """Link/handle kênh mỗi dòng → link chuẩn `https://www.youtube.com/@handle` / `/channel/UC…` (bỏ trùng)."""
    ra: List[str] = []
    for dong in str(chu or "").splitlines():
        d = dong.split("#")[0].strip()
        if not d:
            continue
        m = re.search(r"(?:youtube\.com/)?(@[\w.\-]+|channel/UC[\w-]{20,}|c/[\w.\-]+|user/[\w.\-]+)", d)
        if not m:
            continue
        link = "https://www.youtube.com/" + m.group(1)
        if link not in ra:
            ra.append(link)
    return ra


def doc_dau_vao(goc: str, thu_muc: str = "") -> Dict[str, Any]:
    tm = thu_muc or thu_muc_dau_vao(goc)
    return {"thu_muc": tm, "ngach": doc_ngach_txt(_doc_tep(os.path.join(tm, "ngach.txt"))),
            "giong": doc_giong_txt(_doc_tep(os.path.join(tm, "giong.txt"))),
            "doi_thu": doc_doi_thu_txt(_doc_tep(os.path.join(tm, "doi-thu.txt")))}


def nhom_tu_dau_vao(nc: Dict[str, Any]) -> str:
    from .khoi_tao_ngach import slug  # noqa: PLC0415
    return slug(nc.get("nhom") or "") or slug("{0}-{1}".format(nc.get("chu_de") or "", nc.get("quoc_gia") or ""))


# ── kiểm (chỉ đọc) ──────────────────────────────────────────────────────────────────────────────

def kiem(goc: str, dau_vao: Optional[Dict[str, Any]] = None, *, quet: Optional[Callable[..., Any]] = None,
         co_vi: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """{loi: [chặn], canh_bao: [], viec_nguoi: [], chrome_moi: [tên], dau_vao}. Không mạng, không ghi."""
    dv = dau_vao or doc_dau_vao(goc)
    loi, canh, nguoi = [], [], []
    nc = dv["ngach"]
    if not nc.get("chu_de") or len(nc.get("quoc_gia") or "") != 2 or not nc.get("ngon_ngu"):
        loi.append("ngach.txt thiếu chu_de / quoc_gia (2 chữ) / ngon_ngu — {0}".format(os.path.join(dv["thu_muc"], "ngach.txt")))
    if not dv["doi_thu"]:
        canh.append("doi-thu.txt trống — máy chỉ tìm đối thủ theo từ khoá (chậm hơn, kém chắc hơn)")
    ds = []
    try:
        from . import kho_chrome  # noqa: PLC0415
        ds = list((quet or kho_chrome.quet)(goc))
    except Exception as e:  # noqa: BLE001
        loi.append("không quét được kho Chrome: {0}".format(str(e)[:120]))
    moi = [x["ten"] for x in ds if x.get("loai") == "moi"]
    for x in ds:
        if x.get("loai") == "chua_dang_nhap":
            nguoi.append("Chrome «{0}» trong kho chưa đăng nhập Gmail — mở {0}.exe, đăng nhập tay rồi đóng".format(x["ten"]))
    if not moi:
        loi.append("kho Chrome không có Chrome mới nào đã đăng nhập Gmail ({0})".format(_kho(goc)))
    if len(dv["giong"]) < len(moi):
        canh.append("giong.txt có {0} giọng cho {1} Chrome — kênh thiếu giọng sẽ chờ".format(len(dv["giong"]), len(moi)))
    ly = (co_vi or _kiem_vi)(goc)
    if ly:
        loi.append(ly)
        nguoi.append("Nạp khoá ShopAPI: đăng nhập trong giao diện tool, hoặc ghi \"api_key\" vào config.json (tool tự cất "
                     "vào secrets.json mã hoá ở lần mở đầu)")
    if not (shutil.which("ffmpeg") or os.path.isdir(os.path.join(goc, "runtime", "ffmpeg-goi"))):
        canh.append("không thấy FFmpeg (runtime/ffmpeg-goi hoặc PATH) — imageio-ffmpeg của requirements sẽ được dùng")
    if not os.path.isdir(os.path.join(goc, "models", "faster-whisper-small")):
        canh.append("thiếu models/faster-whisper-small (phụ đề/căn lời) — chép từ gói sạch")
    if not os.path.isfile(os.path.join(goc, "vps.json")):
        canh.append("chưa chạy CAI-DAT-VPS.bat (vps.json, vm/config.json, lịch Windows)")
    return {"loi": loi, "canh_bao": canh, "viec_nguoi": nguoi, "chrome_moi": moi, "dau_vao": dv}


def _kho(goc: str) -> str:
    try:
        from .tra_kho import thu_muc_kho  # noqa: PLC0415
        return thu_muc_kho(goc)
    except Exception:  # noqa: BLE001
        return os.path.join(os.path.dirname(os.path.abspath(goc)), "kho")


def _kiem_vi(goc: str) -> str:
    try:
        from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415
        cfg = load_config(os.path.join(goc, CONFIG_FILENAME))
        if cfg.problem:
            return "chưa có khoá ShopAPI dùng được: {0}".format(str(cfg.problem)[:120])
        if not str(getattr(cfg, "api_key", "") or "").strip():
            return "chưa có khoá ShopAPI (config.json / secrets.json)"
    except Exception as e:  # noqa: BLE001
        return "không đọc được cấu hình ShopAPI: {0}".format(str(e)[:120])
    return ""


def _client(goc: str) -> Any:
    from .api import build_client  # noqa: PLC0415
    from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415
    cfg = load_config(os.path.join(goc, CONFIG_FILENAME))
    if cfg.problem:
        raise RuntimeError("không đọc được cấu hình ShopAPI: {0}".format(str(cfg.problem)[:120]))
    return build_client(cfg)


# ── các bước ─────────────────────────────────────────────────────────────────────────────────────

def ma_kenh_moi(goc: str, tien_to: str, da_dung: Sequence[str]) -> str:
    """Mã kế `<tiền tố><số>` chưa có CHANNEL/<mã>, thư mục `<cha>\\<mã>` hay trong sổ."""
    cha = os.path.dirname(os.path.abspath(goc))
    i = 1
    while True:
        ma = "{0}{1}".format(tien_to, i)
        if ma not in da_dung and not os.path.exists(os.path.join(goc, "CHANNEL", ma)) and not os.path.exists(os.path.join(cha, ma)):
            return ma
        i += 1


def buoc_kho(goc: str, so: Dict[str, Any], dv: Dict[str, Any], log: Callable[[str], None], *,
             quet: Optional[Callable[..., Any]] = None, lap_dat: Optional[Callable[..., Tuple[str, str]]] = None,
             giu: Optional[Callable[..., bool]] = None) -> str:
    from . import kho_chrome  # noqa: PLC0415
    ds = [x for x in (quet or kho_chrome.quet)(goc) if x.get("loai") == "moi"]
    da = {d.get("chrome_kho") for d in so["kenh"].values()}
    tran = int(so.pop("mo_rong", 0) or 0) if so.get("ngach_xong") else len(ds)  # mở rộng: chừa Chrome cho D20
    for x in sorted(ds, key=lambda x: x["ten"]):
        if x["ten"] in da:
            continue
        if tran <= 0:
            break
        tran -= 1
        ma = ma_kenh_moi(goc, dv["ngach"].get("tien_to") or "K", list(so["kenh"]))
        if not (giu or kho_chrome.giu)(goc, x["ten"], ma):
            continue
        so["kenh"][ma] = {"chrome_kho": x["ten"], "dat_chrome": "", "giong": "", "tuyen": ""}
        luu_so(goc, so)
    for ma, d in sorted(so["kenh"].items()):
        if d.get("dat_chrome") == "ok":
            continue
        tt, gc = (lap_dat or kho_chrome.lap_dat)(goc, d["chrome_kho"], ma)
        d["dat_chrome"] = "ok" if tt != "hong" else "hong: " + str(gc)[:160]
        log("{0}: Chrome kho «{1}» → {2} ({3})".format(ma, d["chrome_kho"], tt, gc))
        _nhat_ky(goc, "đặt Chrome {0} ← {1}: {2}".format(ma, d["chrome_kho"], gc))
    luu_so(goc, so)
    ok = [m for m, d in so["kenh"].items() if d.get("dat_chrome") == "ok"]
    if not ok:
        so["loi"] = "chưa đặt được Chrome nào (Chrome đang mở? đóng hết Chrome kho rồi chạy lại)"
        return "loi"
    # giọng: mỗi kênh một giọng CHƯA kênh nào dùng, theo thứ tự giong.txt (đợt mở rộng: giọng mới thêm cuối tệp)
    dung = {d.get("giong") for d in so["kenh"].values() if d.get("giong")} | set(_giong_dang_dung(goc))
    con = [g["voice_id"] for g in dv["giong"] if g["voice_id"] not in dung]
    for ma in sorted(so["kenh"]):
        if not so["kenh"][ma].get("giong") and con:
            so["kenh"][ma]["giong"] = con.pop(0)
    if so.get("ngach_xong") and so.get("nhom"):
        ghi_kho_giong(goc, so["nhom"], dv["giong"], dv["ngach"].get("ngon_ngu") or "")
    so["buoc"] = "nuoi" if so.get("ngach_xong") else "ngach"
    return "tiep"


def _giong_dang_dung(goc: str) -> List[str]:
    try:
        from .thay_kenh import giong_dang_dung  # noqa: PLC0415
        return list(giong_dang_dung(goc))
    except Exception:  # noqa: BLE001
        return []


def ghi_kho_giong(goc: str, nhom: str, giong: Sequence[Dict[str, str]], ngon_ngu: str) -> str:
    """`CHANNEL/_NHOM/<nhóm>/kho-giong.json` từ giong.txt — ky_tu_moi_phut THAM KHẢO theo tiếng (đo lại sau video đầu)."""
    from .khoi_tao_ngach import thong_tin_tieng  # noqa: PLC0415
    from .mo_kenh import duong_kho_giong  # noqa: PLC0415
    kt = int(thong_tin_tieng(ngon_ngu)["ky_tu"])
    duong = duong_kho_giong(goc, nhom)
    cu = _doc_json(duong, {}) or {}
    co = {x.get("voice_id") for x in cu.get("giong") or [] if isinstance(x, dict)}
    ds = [x for x in cu.get("giong") or [] if isinstance(x, dict)]
    for g in giong:
        if g["voice_id"] not in co:
            ds.append({"voice_id": g["voice_id"], "ky_tu_moi_phut": kt,
                       "ghi_chu": ("giong.txt: " + g.get("ghi_chu", "")).strip(" :") + " — ký tự/phút THAM KHẢO theo tiếng"})
    _ghi_json(duong, {"nhom": nhom, "cap_nhat": _dt.date.today().isoformat(), "ghi_chu": "Kho giọng ĐÃ DUYỆT (khởi tạo "
                      "VPS từ giong.txt). Đo lại ky_tu_moi_phut sau video đầu mỗi kênh.", "giong": ds})
    return duong


def ghi_doi_thu_them(goc: str, nhom: str, links: Sequence[str]) -> str:
    """Đối thủ hạt giống → `_NHOM/<nhóm>/doi-thu-them.txt` (đường vào (a) "chủ đưa", `kiem_ngach_doi_thu`)."""
    from .ho_so_ngach import duong_ngach_yaml  # noqa: PLC0415
    from .kiem_ngach_doi_thu import TEP_THEM  # noqa: PLC0415
    duong = os.path.join(os.path.dirname(duong_ngach_yaml(goc, nhom)), TEP_THEM)
    cu = [x.strip() for x in _doc_tep(duong).splitlines() if x.strip()]
    moi = cu + [x for x in links if x not in cu]
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write("\n".join(moi) + "\n")
    return duong


def buoc_ngach(goc: str, so: Dict[str, Any], dv: Dict[str, Any], log: Callable[[str], None], *,
               khoi_tao: Optional[Callable[..., Any]] = None, client: Any = None) -> str:
    from . import khoi_tao_ngach as ktn  # noqa: PLC0415
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415
    nc = dv["ngach"]
    nhom = so.get("nhom") or nhom_tu_dau_vao(nc)
    so["nhom"] = nhom
    dau = sorted(m for m, d in so["kenh"].items() if d.get("dat_chrome") == "ok")[0]
    so["kenh_dau"] = dau
    if dv["doi_thu"]:
        ghi_doi_thu_them(goc, nhom, dv["doi_thu"])
    yc = ktn.YeuCau(chu_de=nc["chu_de"], quoc_gia=nc["quoc_gia"], ngon_ngu=nc["ngon_ngu"], kenh_mau=list(dv["doi_thu"][:3]),
                    tu_khoa=list(nc.get("tu_khoa") or []), ma_kenh=dau, nhom=nhom, mo_ta_them=nc.get("mo_ta") or "",
                    khan_gia=nc.get("khan_gia") or "", khan_gia_loai_tru=list(nc.get("khong_nham") or []))
    if not os.path.isfile(os.path.join(goc, "CHANNEL", dau, "kenh.yaml")) or not so.get("ngach_xong"):
        log("── khởi tạo ngách «{0}» ({1}/{2}) → nhóm {3}, kênh đầu {4} ──".format(
            nc["chu_de"], nc["quoc_gia"], nc["ngon_ngu"], nhom, dau))
        (khoi_tao or ktn.khoi_tao)(goc, yc, client=client if client is not None else _client(goc), log=log)
        so["ngach_xong"] = _bay_gio().strftime("%Y-%m-%d %H:%M")
    ghi_kho_giong(goc, nhom, dv["giong"], nc["ngon_ngu"])
    g = so["kenh"][dau].get("giong")
    khoa: Dict[str, Any] = {"thiet_lap_kenh": False, "tu_chay": False}
    if g:
        khoa.update(voice_id=g, ky_tu_moi_phut=int(ktn.thong_tin_tieng(nc["ngon_ngu"])["ky_tu"]))
    # Kênh đầu: CHƯA thiết lập Studio / chưa tự đăng — tài khoản kho có thể chưa có kênh thương hiệu. `mo_kenh.kich_hoat`
    # (can_thuong_hieu) bật lại cả hai sau khi tạo kênh thương hiệu + ghim UC + thiết lập 11/11.
    ghi_cai_kenh(goc, dau, **khoa)
    try:
        from . import vm_cai_dat  # noqa: PLC0415
        vm_cai_dat.luu(goc, dau, tu_dang=False, cach_dang="tu_dong")
    except Exception as e:  # noqa: BLE001
        log("  (không ghi được may-ao.json {0}: {1})".format(dau, str(e)[:100]))
    so["buoc"] = "nuoi"
    return "tiep"


def _yaml_nhap(ma: str, nhom: str, ngon_ngu: str, ten: str) -> str:
    return ("# Bản NHÁP để NUÔI TRANG CHỦ trước khi mở kênh (core/khoi_tao_vps). CHANNEL/{0} thắng bản này khi đã dựng.\n"
            "ten: \"(nuôi trang chủ) — {3}\"\nnhom: \"{1}\"\nngon_ngu: {2}\nnuoi_trang_chu: true\ntu_chay: false\n").format(
                ma, nhom, ngon_ngu, ten.replace('"', "'"))


def buoc_nuoi(goc: str, so: Dict[str, Any], dv: Dict[str, Any], log: Callable[[str], None], *,
              bay_gio: Optional[_dt.datetime] = None) -> str:
    """Bật nuôi cho kênh CHƯA có tuyến (đợt đầu: mọi kênh; đợt mở rộng: kênh mới) rồi CHỜ: mọi kênh ấy đạt, hoặc hết
    `NGAY_NUOI_TOI_DA` ngày mà ≥ `SO_DAT_DE_DI_TIEP` kênh đạt."""
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415
    bay = _bay_gio(bay_gio)
    nhom, dau = so["nhom"], so["kenh_dau"]
    tat_ca = sorted(m for m, d in so["kenh"].items() if d.get("dat_chrome") == "ok" and not d.get("tuyen"))
    chua = [m for m in tat_ca if not so["kenh"][m].get("nuoi_tu")]
    if chua:
        from .ho_so_ngach import doc_ngach_nhom  # noqa: PLC0415
        hs = doc_ngach_nhom(goc, nhom)
        ten = (hs.mo_ta_ngach or dv["ngach"]["chu_de"]).split(" — ")[0][:80]
        for ma in chua:
            if os.path.isfile(os.path.join(goc, "CHANNEL", ma, "kenh.yaml")):
                ghi_cai_kenh(goc, ma, nuoi_trang_chu=True)
            else:
                duong = os.path.join(goc, "workspace", "chuan-bi-" + ma, "CHANNEL", ma, "kenh.yaml")
                os.makedirs(os.path.dirname(duong), exist_ok=True)
                with io.open(duong, "w", encoding="utf-8") as tep:
                    tep.write(_yaml_nhap(ma, nhom, dv["ngach"]["ngon_ngu"], ten))
            so["kenh"][ma]["nuoi_tu"] = bay.strftime("%Y-%m-%d %H:%M")
        so.setdefault("nuoi_tu", bay.strftime("%Y-%m-%d %H:%M"))
        log("bật nuôi trang chủ cho {0} kênh ({1}) — agent nuôi khi máy rảnh (mục tiêu ≥ 90 % đúng chủ đề)".format(
            len(chua), ", ".join(chua)))
        _nhat_ky(goc, "bật nuôi trang chủ: " + ", ".join(chua))
        return "cho"
    if not tat_ca:
        so["buoc"] = "doi_thu"
        return "tiep"
    dat = [m for m in tat_ca if trang_thai_nuoi(goc, m) == "dat"]
    gio = max(_gio_tu(so["kenh"][m].get("nuoi_tu"), bay) or 0.0 for m in tat_ca)
    so["nuoi_dat"] = dat
    if len(dat) >= len(tat_ca) or (gio >= NGAY_NUOI_TOI_DA * 24 and len(dat) >= SO_DAT_DE_DI_TIEP):
        log("nuôi trang chủ: {0}/{1} kênh đạt sau {2:.0f} giờ → quét trang chủ ra đối thủ".format(len(dat), len(tat_ca), gio))
        so["buoc"] = "doi_thu"
        return "tiep"
    if gio >= NGAY_NUOI_TOI_DA * 24 and not dat:
        _viec(so, "nuoi", "Nuôi trang chủ {0:.0f} ngày chưa kênh nào đạt ≥ 90 % đúng chủ đề".format(gio / 24),
              "→ xem vm/logs/nuoi-trang-chu/<kênh>.md (agent có chạy? Chrome có mở được? captcha?)")
    return "cho"


def trang_thai_nuoi(goc: str, ma: str) -> str:
    return str((_doc_json(os.path.join(goc, "vm", "logs", "nuoi-trang-chu", ma + ".json"), {}) or {}).get("trang_thai") or "")


def o_dung_ngach(goc: str, cac_kenh: Sequence[str]) -> List[str]:
    """Mã video mọi ô trang chủ mà lượt nuôi đã phán `dung_ngach` / `dung_chu_de` (sổ `vm/logs/nuoi-trang-chu`)."""
    ra: List[str] = []
    for ma in cac_kenh:
        cache = (_doc_json(os.path.join(goc, "vm", "logs", "nuoi-trang-chu", ma + ".json"), {}) or {}).get("cache") or {}
        uu = sorted((k for k, v in cache.items() if not k.startswith("tl:") and v == "dung_ngach"))
        phu = sorted((k for k, v in cache.items() if not k.startswith("tl:") and v == "dung_chu_de"))
        for k in uu + phu:
            if k not in ra:
                ra.append(k)
    return ra


def buoc_doi_thu(goc: str, so: Dict[str, Any], log: Callable[[str], None], *, tra: Optional[Callable[..., Dict[str, str]]] = None,
                 mot_nut: Optional[Callable[..., Any]] = None, client: Any = None) -> str:
    from . import doi_thu_kenh as dtk  # noqa: PLC0415
    dau = so["kenh_dau"]
    dot = sorted(m for m, d in so["kenh"].items() if d.get("dat_chrome") == "ok")
    if (so.get("doi_thu_tra") or {}).get("dot") != dot:                 # mỗi đợt kênh (đầu / mở rộng) tra một lần
        if tra is None:
            from .trang_chu import tra_video as tra  # noqa: PLC0415
        lang = str(_cai(goc, dau).get("ngon_ngu") or "")
        ids = o_dung_ngach(goc, list(so["kenh"]))[:SO_O_TRA_TOI_DA]
        links: List[str] = []
        for vid in ids:
            try:
                tt = tra(vid, lang=lang) or {}
            except Exception:  # noqa: BLE001 — một video tra hỏng: bỏ qua
                tt = {}
            link = str(tt.get("link_kenh") or "").strip()
            if link and not tt.get("short") and link not in links:
                links.append(link)
        cu = dtk.doc_doi_thu(goc, dau)
        moi = [x for x in links if x not in cu]
        if moi:
            dtk.luu_doi_thu(goc, dau, (cu.strip() + "\n" if cu.strip() else "") + "\n".join(moi))
        so["doi_thu_tra"] = {"o": len(ids), "kenh": len(links), "moi": len(moi), "luc": _bay_gio().strftime("%Y-%m-%d %H:%M"),
                             "dot": dot}
        luu_so(goc, so)
        log("trang chủ: {0} ô đúng ngách → {1} kênh nguồn ({2} mới) vào hộp thư đối thủ {3}".format(len(ids), len(links), len(moi), dau))
    if mot_nut is None:
        from .mot_nut import chay as mot_nut  # noqa: PLC0415
    log("Một nút {0}: chốt đối thủ + kiểm ngách theo nghĩa + quét content…".format(dau))
    mot_nut(goc, dau, client=client if client is not None else _client(goc), on_log=lambda m: log("   " + str(m)))
    so["buoc"] = "tuyen"
    return "tiep"


def buoc_tuyen(goc: str, so: Dict[str, Any], log: Callable[[str], None], *, chay_tuyen: Optional[Callable[..., Any]] = None,
               client: Any = None) -> str:
    from . import tuyen_thi_truong as ttt  # noqa: PLC0415
    kq = (chay_tuyen or ttt.chay)(goc, so["nhom"], ghi_ho_so_ngach=True,
                                   client=client if client is not None or chay_tuyen else _client(goc), log=log)
    so["tuyen"] = [{k: d.get(k) for k in ("ma", "ten", "nguon_no_thang", "toi_da", "so_video")} for d in kq.get("tuyen") or []]
    so["do_thi_truong"] = _bay_gio().strftime("%Y-%m-%d %H:%M")
    so["buoc"] = "phan_kenh"
    return "tiep"


def buoc_phan_kenh(goc: str, so: Dict[str, Any], dv: Dict[str, Any], log: Callable[[str], None]) -> str:
    from . import mo_kenh  # noqa: PLC0415
    from . import tuyen_thi_truong as ttt  # noqa: PLC0415
    from .khoi_tao_ngach import thong_tin_tieng  # noqa: PLC0415
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415
    kq = _doc_json(os.path.join(ttt.thu_muc(goc, so["nhom"]), "ket-qua.json"), {}) or {}
    so_do = kq.get("tuyen") or []
    if not so_do:
        so["loi"] = "chưa có kết quả tuyến"
        return "loi"
    kenh = sorted(m for m, d in so["kenh"].items() if d.get("dat_chrome") == "ok")
    phan = ttt.phan_kenh(kenh, so_do, {m: d["tuyen"] for m, d in so["kenh"].items() if d.get("tuyen")})
    dau = so["kenh_dau"]
    kt = int(thong_tin_tieng(dv["ngach"]["ngon_ngu"])["ky_tu"])
    st = mo_kenh.doc_trang_thai(goc)
    for ma in kenh:
        t = phan.get(ma) or so_do[0]["ma"]
        moi_gan = so["kenh"][ma].get("tuyen") != t
        so["kenh"][ma]["tuyen"] = t
        ten_t = next((d["ten"] for d in so_do if d["ma"] == t), t)
        if ma == dau and moi_gan:
            ghi_cai_kenh(goc, dau, tep=t)
            ttt.ghi_tuyen_csv(goc, dau, so_do, t)
            try:
                mo_kenh._gieo_so_lieu(goc, dau, {"tep": t, "kenh_goc": dau})  # noqa: SLF001
            except Exception as e:  # noqa: BLE001
                log("  gieo V7 {0} hỏng (không chặn): {1}".format(dau, str(e)[:120]))
        if ma not in st["kenh"]:
            g = so["kenh"][ma].get("giong")
            st["kenh"][ma] = {"trang_thai": "de_xuat", "tep": t, "ten_tep": ten_t, "nhom": so["nhom"], "kenh_goc": dau,
                              "loai": LOAI_MO_KENH, "tu_dong": True, "can_thuong_hieu": True,
                              "chrome_kho": so["kenh"][ma].get("chrome_kho") or "", "kiem_cuoi": 0, "loi": "",
                              "ngay_de_xuat": _bay_gio().strftime("%Y-%m-%d"),
                              "ly_do": "khởi tạo VPS: tuyến «{0}» (đo từ content đối thủ)".format(ten_t)}
            if g:
                st["kenh"][ma]["giong"] = {"voice_id": g, "ky_tu_moi_phut": kt, "ghi_chu": "giong.txt (khởi tạo VPS)"}
        log("{0} → tuyến «{1}»".format(ma, ten_t))
    mo_kenh.luu_trang_thai(goc, st)
    _nhat_ky(goc, "chia kênh: " + ", ".join("{0}→{1}".format(m, so["kenh"][m]["tuyen"]) for m in kenh))
    so["buoc"] = "mo_kenh"
    return "tiep"


def _cai(goc: str, ma: str) -> Dict[str, Any]:
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        return doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        return {}


def buoc_mo_kenh(goc: str, so: Dict[str, Any], log: Callable[[str], None], *, bay_gio: Optional[_dt.datetime] = None,
                 chay_tao_kenh: Optional[Callable[[str, str], int]] = None) -> str:
    """Mỗi nhịp: MỘT lượt DOM tạo kênh thương hiệu cho kênh đã chuẩn bị xong (có tên gợi ý). mo_kenh (gác tổng 15')
    tự chuẩn bị / ghép máy đăng / thiết lập 11/11 / bật tự chạy. Mọi kênh `xong` → bước xong."""
    from . import mo_kenh, thay_kenh  # noqa: PLC0415
    bay = _bay_gio(bay_gio)
    st = mo_kenh.doc_trang_thai(goc)
    kenh = sorted(m for m, d in so["kenh"].items() if d.get("dat_chrome") == "ok")
    da_dom = False
    xong = []
    for ma in kenh:
        d = st["kenh"].get(ma) or {}
        if d.get("trang_thai") == "xong":
            xong.append(ma)
            continue
        if d.get("trang_thai") in ("de_xuat", "", None) or not d.get("ten_goi_y"):
            continue
        ok, _uc = thay_kenh.thuong_hieu_xong(goc, ma)
        if ok:
            continue
        k = so["kenh"][ma]
        gio = _gio_tu(k.get("tao_kenh_luc"), bay)
        if da_dom or (gio is not None and gio < (GIO_THU_LAI if int(k.get("tao_kenh_lan") or 0) else 0.0)):
            continue
        da_dom = True
        ma_ra = (chay_tao_kenh or thay_kenh._chay_tao_kenh)(goc, ma)  # noqa: SLF001
        k["tao_kenh_luc"] = bay.strftime("%Y-%m-%d %H:%M")
        if ma_ra == thay_kenh.MA_HOAN:
            continue
        ok, ly = thay_kenh.thuong_hieu_xong(goc, ma)
        if ok:
            thay_kenh._dong_bo_ten_ho_so(goc, ma)  # noqa: SLF001
            k["tao_kenh_lan"] = 0
            log("{0}: kênh thương hiệu xong + UC đã ghim".format(ma))
            _nhat_ky(goc, "kênh thương hiệu {0} xong".format(ma))
        else:
            k["tao_kenh_lan"] = int(k.get("tao_kenh_lan") or 0) + 1
            log("{0}: tạo kênh thương hiệu chưa xong (lần {1}, mã {2}): {3}".format(ma, k["tao_kenh_lan"], ma_ra, ly))
            if k["tao_kenh_lan"] >= SO_LAN_TAO_KENH_BAO or ma_ra == 20:
                _viec(so, "tao-kenh:" + ma, "Tạo kênh thương hiệu {0} cần người ({1})".format(ma, ly),
                      "→ mở Chrome {0}, xử lý (đăng nhập lại / CAPTCHA / xác minh điện thoại) rồi đóng; máy thử lại mỗi "
                      "{1:.0f} giờ".format(ma, GIO_THU_LAI))
    so["mo_kenh_xong"] = xong
    if kenh and len(xong) == len(kenh):
        so["buoc"] = "xong"
        so["ngay_xong"] = bay.strftime("%Y-%m-%d")
        _bao(goc, "Khởi tạo VPS xong: {0} kênh đang tự chạy".format(len(xong)),
             "Ngách nhóm {0}: ".format(so.get("nhom")) + ", ".join("{0} → {1}".format(m, so["kenh"][m].get("tuyen")) for m in xong))
        _nhat_ky(goc, "XONG khởi tạo VPS")
        return "tiep"
    return "cho"


def so_mo_rong(goc: str, so: Dict[str, Any], dv: Optional[Dict[str, Any]] = None,
               quet: Optional[Callable[..., Any]] = None) -> int:
    """Số kênh MỞ RỘNG làm được ngay: Chrome kho mới đã đăng nhập (chưa trong sổ) trừ `KHO_DU_PHONG` (để dành D20 thay
    kênh hỏng), giới hạn bởi số giọng giong.txt chưa kênh nào dùng. Tắt: `workspace/cai-dat.json: khoi_tao_vps_mo_rong: false`."""
    if (_doc_json(os.path.join(goc, "workspace", "cai-dat.json"), {}) or {}).get("khoi_tao_vps_mo_rong") is False:
        return 0
    try:
        from . import kho_chrome  # noqa: PLC0415
        da = {d.get("chrome_kho") for d in so["kenh"].values()}
        moi = [x for x in (quet or kho_chrome.quet)(goc) if x.get("loai") == "moi" and x["ten"] not in da]
    except Exception:  # noqa: BLE001
        return 0
    dv = dv or doc_dau_vao(goc)
    dung = {d.get("giong") for d in so["kenh"].values() if d.get("giong")} | set(_giong_dang_dung(goc))
    giong = [g for g in dv["giong"] if g["voice_id"] not in dung]
    return max(0, min(len(moi) - KHO_DU_PHONG, len(giong)))


def buoc_xong(goc: str, so: Dict[str, Any], log: Callable[[str], None], *, bay_gio: Optional[_dt.datetime] = None,
              chay_tuyen: Optional[Callable[..., Any]] = None, dv: Optional[Dict[str, Any]] = None,
              quet: Optional[Callable[..., Any]] = None) -> str:
    """Duy trì: (1) kho có Chrome mới + giong.txt có giọng mới → MỞ RỘNG (quay lại bước kho: đặt Chrome → nuôi → tuyến →
    chia kênh, kênh cũ giữ tuyến); (2) đo lại thị trường mỗi `NGAY_DO_LAI` ngày (nhãn nhớ đệm — chỉ tiêu đề mới tốn lượt)
    để `mo_kenh` / tổng giám đốc luôn có số thị trường ≤ 30 ngày tuổi."""
    n = so_mo_rong(goc, so, dv, quet)
    if n > 0:
        so["mo_rong"] = n
        so["buoc"] = "kho"
        log("mở rộng: kho có Chrome mới + giọng mới → thêm {0} kênh".format(n))
        _nhat_ky(goc, "mở rộng {0} kênh".format(n))
        return "tiep"
    gio = _gio_tu(so.get("do_thi_truong"), _bay_gio(bay_gio))
    if gio is not None and gio < NGAY_DO_LAI * 24:
        return "cho"
    from . import tuyen_thi_truong as ttt  # noqa: PLC0415
    (chay_tuyen or ttt.chay)(goc, so["nhom"], log=log, client=None if chay_tuyen else _client(goc))
    so["do_thi_truong"] = _bay_gio(bay_gio).strftime("%Y-%m-%d %H:%M")
    return "cho"


def _viec(so: Dict[str, Any], khoa: str, chu: str, goi_y: str) -> None:
    ds = [v for v in so.get("viec_nguoi") or [] if v.get("khoa") != KHOA_VIEC + ":" + khoa]
    ds.append({"khoa": KHOA_VIEC + ":" + khoa, "chu": chu, "goi_y": goi_y, "luc": _bay_gio().strftime("%Y-%m-%d %H:%M")})
    so["viec_nguoi"] = ds


def _bao(goc: str, tieu: str, chi: str) -> None:
    try:
        from .bao_dong import bao_dong  # noqa: PLC0415
        bao_dong("khoi_tao_vps", tieu, chi[:3000])
    except Exception:  # noqa: BLE001
        pass


# ── nhịp ─────────────────────────────────────────────────────────────────────────────────────────

def can_lam(goc: str, bay_gio: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """RẺ (đọc sổ): có bước đến hạn không — điều kiện skill D28."""
    so = doc_so(goc)
    b = so.get("buoc")
    if not b:
        return False, "chưa khởi tạo (chạy `python -m core.khoi_tao_vps chay` một lần)"
    bay = _bay_gio(bay_gio)
    if b in ("kho", "ngach", "doi_thu", "tuyen", "phan_kenh"):
        gio = _gio_tu(so.get("loi_luc"), bay)
        if so.get("loi") and gio is not None and gio < GIO_THU_LAI:
            return False, "bước {0} lỗi, thử lại sau {1:.0f} giờ".format(b, GIO_THU_LAI - gio)
        return True, "bước " + b
    if b == "nuoi":
        return True, "kiểm nuôi trang chủ"
    if b == "mo_kenh":
        return True, "mở kênh: tạo kênh thương hiệu / chờ thiết lập"
    if b == "xong":
        gio = _gio_tu(so.get("do_thi_truong"), bay)
        if gio is None or gio >= NGAY_DO_LAI * 24:
            return True, "đo lại thị trường"
        n = so_mo_rong(goc, so)
        return n > 0, ("mở rộng {0} kênh từ kho".format(n) if n else "xong — chờ đo lại thị trường")
    return False, "bước lạ " + str(b)


def nhip(goc: str, *, log: Callable[[str], None] = print, bay_gio: Optional[_dt.datetime] = None,
         dau_vao: Optional[Dict[str, Any]] = None, toi_da_buoc: int = len(BUOC) + 2, **cam: Any) -> str:
    """Đi tiếp các bước tới khi phải chờ. `cam` = chỗ cắm đồ giả cho bài kiểm (quet, lap_dat, giu, khoi_tao, tra,
    mot_nut, chay_tuyen, chay_tao_kenh, client, co_vi). Trả bước hiện tại."""
    so = doc_so(goc)
    dv = dau_vao or doc_dau_vao(goc)
    if not so.get("buoc"):
        so["buoc"] = "kiem"
        so["bat_dau"] = _bay_gio(bay_gio).strftime("%Y-%m-%d %H:%M")
    for _ in range(toi_da_buoc):
        b = so["buoc"]
        try:
            if b == "kiem":
                k = kiem(goc, dv, quet=cam.get("quet"), co_vi=cam.get("co_vi"))
                so["kiem"] = {x: k[x] for x in ("loi", "canh_bao", "viec_nguoi", "chrome_moi")}
                for v in k["viec_nguoi"]:
                    _viec(so, "kiem:" + v[:40], v, "")
                if k["loi"]:
                    so["loi"] = "; ".join(k["loi"])
                    kq = "loi"
                else:
                    so["buoc"], kq = "kho", "tiep"
            elif b == "kho":
                kq = buoc_kho(goc, so, dv, log, quet=cam.get("quet"), lap_dat=cam.get("lap_dat"), giu=cam.get("giu"))
            elif b == "ngach":
                kq = buoc_ngach(goc, so, dv, log, khoi_tao=cam.get("khoi_tao"), client=cam.get("client"))
            elif b == "nuoi":
                kq = buoc_nuoi(goc, so, dv, log, bay_gio=bay_gio)
            elif b == "doi_thu":
                kq = buoc_doi_thu(goc, so, log, tra=cam.get("tra"), mot_nut=cam.get("mot_nut"), client=cam.get("client"))
            elif b == "tuyen":
                kq = buoc_tuyen(goc, so, log, chay_tuyen=cam.get("chay_tuyen"), client=cam.get("client"))
            elif b == "phan_kenh":
                kq = buoc_phan_kenh(goc, so, dv, log)
            elif b == "mo_kenh":
                kq = buoc_mo_kenh(goc, so, log, bay_gio=bay_gio, chay_tao_kenh=cam.get("chay_tao_kenh"))
            elif b == "xong":
                kq = buoc_xong(goc, so, log, bay_gio=bay_gio, chay_tuyen=cam.get("chay_tuyen"), dv=dv, quet=cam.get("quet"))
            else:
                kq = "cho"
        except Exception as loi:  # noqa: BLE001 — một bước hỏng: ghi, nhịp sau thử lại (không vỡ skill)
            so["loi"] = "{0}: {1}".format(type(loi).__name__, str(loi)[:300])
            kq = "loi"
        if kq == "loi":
            so["loi_luc"] = _bay_gio(bay_gio).strftime("%Y-%m-%d %H:%M")
            log("khởi tạo VPS — bước {0} LỖI: {1}".format(b, so.get("loi")))
            _nhat_ky(goc, "lỗi bước {0}: {1}".format(b, so.get("loi")))
        elif kq == "tiep":
            so["loi"] = ""
            _nhat_ky(goc, "xong bước {0} → {1}".format(b, so["buoc"]))
        luu_so(goc, so)
        if kq != "tiep" or so["buoc"] == b:
            break
    return so["buoc"]


def viec_cua_ban(goc: str) -> List[Dict[str, str]]:
    """Việc CHỈ người làm được (cho bảng điều khiển): {khoa, kenh, chu, goi_y}."""
    so = doc_so(goc)
    if not so.get("buoc") or so.get("buoc") == "xong":
        return []
    return [{"khoa": v["khoa"], "kenh": "", "chu": v.get("chu") or "", "goi_y": v.get("goi_y") or ""}
            for v in so.get("viec_nguoi") or [] if v.get("khoa")]


def tom_tat(goc: str) -> List[str]:
    so = doc_so(goc)
    if not so.get("buoc"):
        return ["chưa khởi tạo VPS (python -m core.khoi_tao_vps kiem)"]
    ra = ["bước: {0}{1} · nhóm {2}".format(so["buoc"], (" — LỖI: " + so["loi"]) if so.get("loi") else "", so.get("nhom") or "?")]
    for ma, d in sorted(so["kenh"].items()):
        ra.append("  {0}: Chrome «{1}» {2} · giọng {3} · tuyến {4} · nuôi {5}".format(
            ma, d.get("chrome_kho"), d.get("dat_chrome") or "-", (d.get("giong") or "-")[:6] + "…" if d.get("giong") else "-",
            d.get("tuyen") or "-", trang_thai_nuoi(goc, ma) or "-"))
    for v in so.get("viec_nguoi") or []:
        ra.append("  VIỆC CỦA BẠN: {0} {1}".format(v.get("chu"), v.get("goi_y") or ""))
    return ra


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.khoi_tao_vps", description=__doc__.split("\n")[0])
    s = ap.add_subparsers(dest="lenh", required=True)
    for ten in ("kiem", "chay", "nhip", "xem"):
        p = s.add_parser(ten)
        p.add_argument("--dau-vao", default="", help="thư mục chứa ngach.txt / giong.txt / doi-thu.txt")
        p.add_argument("--goc", default="", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    goc = os.path.abspath(a.goc or GOC)
    if a.lenh == "xem":
        print("\n".join(tom_tat(goc)))
        return 0
    dv = doc_dau_vao(goc, a.dau_vao)
    if a.lenh == "kiem":
        k = kiem(goc, dv)
        print("Đầu vào: {0}".format(dv["thu_muc"]))
        print("  ngách: {0} · {1}/{2} · khán giả: {3} · không nhắm: {4}".format(
            dv["ngach"]["chu_de"] or "?", dv["ngach"]["quoc_gia"] or "?", dv["ngach"]["ngon_ngu"] or "?",
            dv["ngach"]["khan_gia"] or "-", "; ".join(dv["ngach"]["khong_nham"]) or "-"))
        print("  {0} giọng · {1} đối thủ hạt giống · {2} Chrome kho đã đăng nhập".format(
            len(dv["giong"]), len(dv["doi_thu"]), len(k["chrome_moi"])))
        for x in k["loi"]:
            print("  ✗ " + x)
        for x in k["canh_bao"]:
            print("  ⚠ " + x)
        for x in k["viec_nguoi"]:
            print("  → VIỆC CỦA BẠN: " + x)
        print("SẴN SÀNG" if not k["loi"] else "CHƯA SẴN SÀNG")
        return 0 if not k["loi"] else 1
    if a.lenh == "nhip":
        ok, ly = can_lam(goc)
        if not ok:
            print("khởi tạo VPS: " + ly)
            return 0
    b = nhip(goc, dau_vao=dv)
    print("\n".join(tom_tat(goc)))
    return 1 if doc_so(goc).get("loi") else 0


if __name__ == "__main__":
    raise SystemExit(main())
