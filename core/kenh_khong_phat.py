"""KÊNH KHÔNG ĐƯỢC PHÁT — phát hiện kênh YouTube không phân phối, dừng làm video MỚI, báo chủ kèm danh sách kiểm
Studio, tự chạy lại (12/10/2026).

═══ VÌ SAO ═══ (`workspace/chan-doan/nao-vong-hoc-2026-10-12.md` mục 5 #1, `view-giam-2026-10-12.md` mục 0.6)

Ba kênh mở cùng đợt có 0–24 lượt hiển thị MỖI video sau 5–8 video (kênh anh em mở cùng ngày có 3,5–15 nghìn), mà
không ai báo chủ: ~3/7 lượt sản xuất mỗi ngày — và ~40% hạn mức kho clip — đổ vào kênh YouTube không phát. Việc
"kiểm hạn chế Studio" bị phân cho bộ não (không mở được Studio) với nhãn "không báo chủ". Đây là việc CHỈ NGƯỜI làm
được: mở Studio xem chế độ hiển thị, "dành cho trẻ em", hạn chế/cảnh cáo, xác minh, nội dung dùng lại…

═══ LUẬT (mã tính, hàm thuần `phan_xet`) ═══

* Chuỗi số mỗi video = THƯỚC CHUNG `core.thuoc_thang.chuoi_kenh` (tuổi THẬT từ `captured_at`, bản rỗng/hỏng đã bỏ,
  lọc `ngay_bat_dau`). Xét video đã đăng, MỚI → CŨ.
* Video ≥ `TUOI_DO` giờ tuổi: số đo = hiển thị ở bản chụp MUỘN NHẤT có tuổi ≥ `TUOI_DO` (số cộng dồn — nhỏ hơn
  `NGUONG_HIEN_THI` ở tuổi đó là chắc chắn "không được phát"). Không có bản ≥ 72h mà bản trẻ hơn đã ≥ ngưỡng → coi như
  được phát; còn lại "thiếu số" — bỏ qua (không đoán), xét video cũ hơn (tối đa `SO_VIDEO_XET_TOI_DA` video).
* KHÔNG ĐƯỢC PHÁT = `SO_VIDEO` video đo được GẦN NHẤT đều < `NGUONG_HIEN_THI`, và không video nào MỚI hơn đã ≥
  `NGUONG_SONG` (video trẻ < 72h cũng tính — tín hiệu YouTube bắt đầu phát).
* Chỉ tính video đăng SAU `moc_xoa` (chủ đã kiểm Studio): sau khi chủ xoá cờ, cần 3 video MỚI cùng < 50 mới báo lại.

═══ HÀNH VI ═══

* Cờ bật → `dang_dung()` True: bộ điều phối (`core.dieu_phoi.trang_thai_kenh`) và cổng `tu_chay._cua_so_san_xuat`
  KHÔNG mở lượt sản xuất MỚI (lý do hiện ở bảng điều khiển). Video đã hẹn lịch / đang tải lên KHÔNG bị đụng; lượt DỞ
  (đã trót trả tiền) vẫn làm nốt nhưng xếp SAU mọi kênh đang được phát → làn API + kho clip dồn cho kênh sống.
* Lần đầu bật (mỗi "đợt" `lan`): một khối việc + danh sách kiểm vào `workspace/loi-chay-max.md`; "Việc của bạn"
  (`viec_cua_ban`, nút "Đã kiểm Studio"); gác tổng báo khẩn + nhắc lại mỗi 24 giờ (`dedupe` theo đợt).
* Tự chạy lại khi: (1) chủ xoá cờ — nút "Đã kiểm Studio" (`workspace/viec-da-xong.json` khoá `khong-phat:<k>:*`),
  `python -m core.kenh_khong_phat xoa --kenh K`, hoặc `da_kiem_studio: "YYYY-MM-DD"` trong kenh.yaml; (2) một video
  mới ≥ `NGUONG_SONG` hiển thị. Tắt hẳn cho một kênh: `kenh_khong_phat: tat` trong kenh.yaml.
* Trạng thái `workspace/kenh-khong-phat/<k>.json` (ghi nguyên tử, khoá ngắn). Tính lại khi bảng tóm tắt Studio đổi
  hoặc quá `GIO_TINH_LAI` giờ; cờ cũ hơn `GIO_CO_CU` giờ (không ai tính lại — gác tổng/điều phối chết) KHÔNG chặn sản
  xuất (không được kẹt im lặng vì một tệp cũ).

    python -m core.kenh_khong_phat [--kenh K] [--thu]   # quyết định trên số thật (--thu: không ghi gì)
    python -m core.kenh_khong_phat xoa --kenh K         # chủ đã kiểm Studio → chạy lại kênh
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

PHIEN_BAN = 1
NGUONG_HIEN_THI = 50.0
TUOI_DO = 72.0
SO_VIDEO = 3
NGUONG_SONG = 300.0
SO_VIDEO_XET_TOI_DA = 8
GIO_TINH_LAI = 3.0
GIO_CO_CU = 48.0
THU_MUC = os.path.join("workspace", "kenh-khong-phat")
KHOA_VIEC = "khong-phat"

SONG, KHONG_PHAT, CHUA_DU, TAT = "song", "khong_phat", "chua_du", "tat"


# ── tiện ích ────────────────────────────────────────────────────────────────

def _f(x: Any) -> str:
    try:
        return "{0:,.0f}".format(float(x)).replace(",", ".")
    except (TypeError, ValueError):
        return "?"


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(p: str, du: Any) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = "{0}.{1}.tam".format(p, os.getpid())
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    for lan in range(5):
        try:
            os.replace(tam, p)
            return
        except PermissionError:  # Windows: tệp đang mở ở tiến trình khác
            if lan == 4:
                raise
            time.sleep(0.2)


def duong(goc: str, kenh: str) -> str:
    return os.path.join(goc, THU_MUC, "{0}.json".format(kenh))


def _iso(epoch: Optional[float]) -> str:
    return _dt.datetime.fromtimestamp(epoch).isoformat(timespec="minutes") if epoch else ""


def _epoch(chu: Any) -> Optional[float]:
    s = str(chu or "").strip()
    if not s:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d\d-\d\d", s):
            return time.mktime(time.strptime(s, "%Y-%m-%d"))
        return _dt.datetime.fromisoformat(s[:19]).timestamp()
    except (ValueError, OverflowError, OSError):
        return None


# ── luật (hàm thuần) ────────────────────────────────────────────────────────

def phan_xet(chuoi: Dict[str, Any], bay_gio: float, moc_xoa: Optional[float] = None) -> Dict[str, Any]:
    """Quyết định trên `{mã: thuoc_thang.Chuoi}` của MỘT kênh lúc `bay_gio` (epoch). Chỉ dùng bản chụp chụp TỚI
    `bay_gio` (chấm ngược lịch sử được) và video đăng sau `moc_xoa`. Trả `{trang_thai, bang_chung[{ma, dang, tuoi,
    hien_thi}], song_vi, n_thieu, ly_do}` — `trang_thai` ∈ song | khong_phat | chua_du."""
    vs = [c for c in chuoi.values() if c.dang is not None and c.dang <= bay_gio
          and (moc_xoa is None or c.dang > moc_xoa)]
    vs.sort(key=lambda c: -c.dang)
    bang: List[Dict[str, Any]] = []
    thieu = xet = 0
    ra: Dict[str, Any] = {"trang_thai": CHUA_DU, "bang_chung": bang, "song_vi": None, "n_thieu": 0, "ly_do": ""}
    for c in vs:
        pts = [d for d in c.diem if d.hien_thi is not None and (d.luc is None or d.luc <= bay_gio + 60)]
        tuoi_nay = (bay_gio - c.dang) / 3600.0
        lon_nhat = max((float(d.hien_thi) for d in pts), default=None)
        if lon_nhat is not None and lon_nhat >= NGUONG_SONG:
            ra.update(trang_thai=SONG, song_vi={"ma": c.ma, "hien_thi": lon_nhat, "tuoi": round(tuoi_nay)},
                      ly_do="video {0} đã có {1} hiển thị (≥ {2}) — YouTube đang phát".format(
                          c.ma, _f(lon_nhat), _f(NGUONG_SONG)))
            break
        if tuoi_nay < TUOI_DO:
            continue
        xet += 1
        if xet > SO_VIDEO_XET_TOI_DA:
            break
        muon = [d for d in pts if d.tuoi >= TUOI_DO]
        if not muon:
            if lon_nhat is not None and lon_nhat >= NGUONG_HIEN_THI:
                ra.update(trang_thai=SONG, song_vi={"ma": c.ma, "hien_thi": lon_nhat, "tuoi": round(tuoi_nay)},
                          ly_do="video {0} đã {1} hiển thị trước 72h (≥ {2})".format(
                              c.ma, _f(lon_nhat), _f(NGUONG_HIEN_THI)))
                break
            thieu += 1
            continue
        d = max(muon, key=lambda x: x.tuoi)
        if float(d.hien_thi) >= NGUONG_HIEN_THI:
            ra.update(trang_thai=SONG, song_vi={"ma": c.ma, "hien_thi": float(d.hien_thi), "tuoi": round(d.tuoi)},
                      ly_do="video {0} có {1} hiển thị @{2:.0f}h (≥ {3})".format(
                          c.ma, _f(d.hien_thi), d.tuoi, _f(NGUONG_HIEN_THI)))
            break
        bang.append({"ma": c.ma, "dang": _iso(c.dang), "tuoi": round(d.tuoi), "hien_thi": float(d.hien_thi)})
        if len(bang) >= SO_VIDEO:
            ra.update(trang_thai=KHONG_PHAT, ly_do="{0} video gần nhất đều < {1} hiển thị sau ≥ {2:.0f}h: {3}".format(
                len(bang), _f(NGUONG_HIEN_THI), TUOI_DO,
                ", ".join("{0} {1} @{2}h".format(b["ma"], _f(b["hien_thi"]), b["tuoi"]) for b in bang)))
            break
    ra["n_thieu"] = thieu
    if ra["trang_thai"] == CHUA_DU:
        ra["ly_do"] = "mới đo được {0}/{1} video ≥ {2:.0f}h tuổi{3}".format(
            len(bang), SO_VIDEO, TUOI_DO, " ({0} video thiếu số ≥ 72h)".format(thieu) if thieu else "")
    return ra


# ── cờ của chủ ──────────────────────────────────────────────────────────────

def _cai_kenh(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        return dict(doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {})
    except Exception:  # noqa: BLE001
        return {}


def da_tat(cai: Dict[str, Any]) -> bool:
    """`kenh_khong_phat: tat` (hoặc false/khong) trong kenh.yaml → không bao giờ dừng kênh này."""
    v = cai.get("kenh_khong_phat")
    return v is False or str(v if v is not None else "").strip().lower() in ("tat", "false", "khong", "0", "no")


def moc_xoa_cua_chu(goc: str, kenh: str, tt: Optional[Dict[str, Any]] = None,
                    cai: Optional[Dict[str, Any]] = None) -> Tuple[Optional[float], str]:
    """`(epoch, nguồn)` lần CHỦ xoá cờ gần nhất: CLI (`moc_xoa` trong tệp trạng thái), nút "Đã kiểm Studio"
    (`workspace/viec-da-xong.json` khoá `khong-phat:<k>:*`), hoặc `da_kiem_studio: YYYY-MM-DD` trong kenh.yaml."""
    ung: List[Tuple[float, str]] = []
    tt = tt if tt is not None else (_doc_json(duong(goc, kenh)) or {})
    e = _epoch((tt or {}).get("moc_xoa_chu"))
    if e:
        ung.append((e, str((tt or {}).get("xoa_boi") or "chu_cli")))
    cai = cai if cai is not None else _cai_kenh(goc, kenh)
    e = _epoch(cai.get("da_kiem_studio"))
    if e:
        ung.append((e, "chu_kenh_yaml"))
    du = _doc_json(os.path.join(goc, "workspace", "viec-da-xong.json"))
    if isinstance(du, dict):
        tien_to = "{0}:{1}:".format(KHOA_VIEC, kenh)
        for k, v in du.items():
            if str(k).startswith(tien_to):
                e = _epoch(v)
                if e:
                    ung.append((e, "chu_nut"))
    if not ung:
        return None, ""
    return max(ung)


# ── trạng thái (đọc / tính lại / ghi) ───────────────────────────────────────

class _Khoa:
    """Khoá ngắn quanh đọc-sửa-ghi tệp trạng thái (gác tổng và điều phối có thể chạy cùng lúc). Không lấy được trong
    ~5 giây thì vẫn chạy (thà ghi liều còn hơn treo)."""

    def __init__(self, p: str) -> None:
        self.p = p + ".khoa"
        self.co = False

    def __enter__(self) -> "_Khoa":
        os.makedirs(os.path.dirname(self.p), exist_ok=True)
        for _ in range(50):
            try:
                os.close(os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                self.co = True
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.p) > 60:
                        os.remove(self.p)
                        continue
                except OSError:
                    pass
                time.sleep(0.1)
            except OSError:
                break
        return self

    def __exit__(self, *a: Any) -> None:
        if self.co:
            try:
                os.remove(self.p)
            except OSError:
                pass


def _dau(goc: str, kenh: str) -> str:
    """Dấu vân tay rẻ của số Studio kênh (mtime bảng tóm tắt + số thư mục video) — đổi thì tính lại."""
    p = os.path.join(goc, "CHANNEL", kenh, "chi-so")
    try:
        m = os.path.getmtime(os.path.join(p, "bang-tom-tat.csv"))
    except OSError:
        m = 0.0
    try:
        n = sum(1 for x in os.listdir(p) if len(x) == 11)
    except OSError:
        n = 0
    return "{0:.0f}:{1}".format(m, n)


def doc(goc: str, kenh: str) -> Dict[str, Any]:
    du = _doc_json(duong(goc, kenh))
    return du if isinstance(du, dict) else {}


def _anh_em(goc: str, kenh: str) -> List[str]:
    """Kênh anh em CÙNG nhóm mà trùng tệp khán giả (`tep`) hoặc trùng giọng (`voice_id`) — rủi ro "trùng nội dung"."""
    cai = _cai_kenh(goc, kenh)
    try:
        from . import nhom_kenh  # noqa: PLC0415

        ds = [k for k in (nhom_kenh.thanh_vien(goc, kenh) or []) if k != kenh]
    except Exception:  # noqa: BLE001
        ds = []

    def tep(k: str, c: Dict[str, Any]) -> str:
        t = str(c.get("tep") or "").strip()
        if t:
            return t
        try:
            from . import cong_thuc_v7 as v7  # noqa: PLC0415

            return str((v7.nap_cau_hinh(goc, k, ghi_neu_thieu=False)[0] or {}).get("tep") or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    t0, g0 = tep(kenh, cai), str(cai.get("voice_id") or "").strip()
    ra = []
    for k in ds:
        if re.search(r"-v\d+$", k):
            continue
        c = _cai_kenh(goc, k)
        lys = []
        if t0 and tep(k, c) == t0:
            lys.append("cùng tệp người xem")
        if g0 and str(c.get("voice_id") or "").strip() == g0:
            lys.append("cùng giọng đọc")
        if lys:
            ra.append("{0} ({1})".format(k, ", ".join(lys)))
    return ra


def danh_sach_kiem(goc: str, kenh: str) -> List[str]:
    """Danh sách kiểm Studio cụ thể (câu người thường hiểu) — chỉ NGƯỜI làm được."""
    cai = _cai_kenh(goc, kenh)
    nn = str(cai.get("ngon_ngu") or "").strip()
    ae = _anh_em(goc, kenh)
    return [
        "Nội dung → từng video: chế độ hiển thị phải là Công khai hoặc Đã lên lịch (không Riêng tư/Không công "
        "khai), cột Hạn chế không có chữ nào (bản quyền, nguyên tắc cộng đồng, giới hạn độ tuổi).",
        "Mỗi video và Cài đặt → Kênh → Cài đặt nâng cao: \"Dành cho trẻ em\" phải là KHÔNG (video dành cho trẻ em "
        "không được đề xuất trên Trang chủ).",
        "youtube.com/features (Trạng thái và tính năng): có cảnh cáo, gậy vi phạm (strike), hạn chế tính năng nào "
        "không; kênh đã xác minh số điện thoại chưa.",
        "Thông báo/Kiếm tiền: có cảnh báo \"nội dung dùng lại\" (reused content) hay spam không"
        + ("; kênh này trùng với kênh anh em {0} — YouTube có thể coi là bản sao, không phát".format(", ".join(ae))
           if ae else "") + ".",
        "Cài đặt → Mặc định tải lên: chế độ hiển thị, \"dành cho trẻ em\", danh mục, ngôn ngữ video{0}.".format(
            " (phải là {0})".format(nn) if nn else ""),
        "Cài đặt → Kênh → Thông tin cơ bản: quốc gia của kênh khớp thị trường người xem{0}.".format(
            " (kênh tiếng {0})".format(nn) if nn else ""),
    ]


def _cau_viec(goc: str, kenh: str, tt: Dict[str, Any]) -> Tuple[str, str]:
    bc = tt.get("bang_chung") or []
    chuyen = ("Kênh {0} không được YouTube phát: {1} video gần nhất mỗi video dưới {2} lượt hiển thị sau ≥ 3 ngày "
              "({3}). Máy đã DỪNG làm video mới cho kênh này (video đã hẹn lịch vẫn đăng); hạn mức kho clip dồn cho "
              "kênh đang được phát.").format(
        kenh, len(bc), _f(NGUONG_HIEN_THI),
        ", ".join("{0}: {1} @{2}h".format(b.get("ma"), _f(b.get("hien_thi")), b.get("tuoi")) for b in bc))
    can = ("Mở YouTube Studio kênh {0}, kiểm 6 mục (chi tiết ở workspace/loi-chay-max.md hoặc nút Chi tiết). Kiểm "
           "xong bấm \"Đã kiểm Studio\" (hoặc `python -m core.kenh_khong_phat xoa --kenh {0}`): máy làm video lại; "
           "3 video mới vẫn dưới {1} hiển thị thì báo lại. Video mới nào ≥ {2} hiển thị → máy tự chạy lại.").format(
        kenh, _f(NGUONG_HIEN_THI), _f(NGUONG_SONG))
    return chuyen, can


def _ghi_loi_chay_max(goc: str, kenh: str, tt: Dict[str, Any], bay_gio: _dt.datetime) -> None:
    """Một khối (dòng việc + danh sách kiểm thụt lề) vào `workspace/loi-chay-max.md` — MỘT lần mỗi đợt."""
    chuyen, can = _cau_viec(goc, kenh, tt)
    p = os.path.join(goc, "workspace", "loi-chay-max.md")
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "a", encoding="utf-8") as tep:
            tep.write("- [{0}] **khan** · kênh {1} — {2}\n".format(bay_gio.strftime("%Y-%m-%d %H:%M"), kenh, chuyen))
            for i, d in enumerate(danh_sach_kiem(goc, kenh), 1):
                tep.write("    {0}. {1}\n".format(i, d))
            tep.write("    → {0}\n".format(can))
    except OSError:
        pass


def cap_nhat(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None, ghi: bool = True,
             ep: bool = False) -> Dict[str, Any]:
    """Trạng thái của kênh, TÍNH LẠI khi số Studio đổi / quá `GIO_TINH_LAI` giờ / mốc xoá của chủ đổi (`ep` = luôn
    tính). `ghi=False`: không ghi đĩa (chạy thử). Trả bản trạng thái (xem `doc`). Không ném lỗi."""
    bay_gio = bay_gio or _dt.datetime.now()
    now = bay_gio.timestamp()
    p = duong(goc, kenh)
    try:
        with (_Khoa(p) if ghi else _KhongKhoa()):
            cu = doc(goc, kenh)
            cai = _cai_kenh(goc, kenh)
            moc, nguon_xoa = moc_xoa_cua_chu(goc, kenh, cu, cai)
            dau = _dau(goc, kenh)
            tuoi_tinh = now - (_epoch(cu.get("luc_tinh")) or 0.0)
            if (not ep and cu.get("phien_ban") == PHIEN_BAN and cu.get("dau") == dau
                    and cu.get("moc_xoa") == _iso(moc) and 0 <= tuoi_tinh < GIO_TINH_LAI * 3600
                    and cu.get("tat") == da_tat(cai)):
                return cu
            from . import thuoc_thang  # noqa: PLC0415

            kq = phan_xet(thuoc_thang.chuoi_kenh(goc, kenh), now, moc)
            moi = dict(cu)
            moi.update(kenh=kenh, phien_ban=PHIEN_BAN, luc_tinh=bay_gio.isoformat(timespec="seconds"), dau=dau,
                       moc_xoa=_iso(moc), nguon_xoa=nguon_xoa, tat=da_tat(cai),
                       ket=kq["trang_thai"], ly_do=kq["ly_do"], bang_chung=kq["bang_chung"], song_vi=kq["song_vi"])
            dung_cu = cu.get("trang_thai") == KHONG_PHAT
            dung_moi = kq["trang_thai"] == KHONG_PHAT and not moi["tat"]
            lich = list(cu.get("lich_su") or [])
            if dung_moi and not dung_cu:
                moi["lan"] = int(cu.get("lan") or 0) + 1
                moi["tu_luc"] = moi["luc_tinh"]
                lich.append({"luc": moi["luc_tinh"], "su": "dung", "lan": moi["lan"], "ly_do": kq["ly_do"]})
                if ghi:
                    _ghi_loi_chay_max(goc, kenh, moi, bay_gio)
            elif dung_cu and not dung_moi:
                su = ("tat" if moi["tat"] else "chu_xoa" if (moc and cu.get("moc_xoa") != moi["moc_xoa"])
                      else "tu_mo")
                moi["mo_luc"] = moi["luc_tinh"]
                lich.append({"luc": moi["luc_tinh"], "su": su, "lan": int(cu.get("lan") or 0),
                             "ly_do": kq["ly_do"] if su == "tu_mo" else nguon_xoa or "kenh_khong_phat: tat"})
            moi["trang_thai"] = KHONG_PHAT if dung_moi else (TAT if moi["tat"] and kq["trang_thai"] == KHONG_PHAT
                                                             else kq["trang_thai"])
            moi["lich_su"] = lich[-20:]
            if ghi:
                _ghi_json(p, moi)
            return moi
    except Exception as loi:  # noqa: BLE001 — hỏng thì như không có bộ phát hiện (không chặn sản xuất)
        return {"kenh": kenh, "trang_thai": "", "loi": "{0}: {1}".format(type(loi).__name__, str(loi)[:160])}


class _KhongKhoa:
    def __enter__(self) -> "_KhongKhoa":
        return self

    def __exit__(self, *a: Any) -> None:
        return None


def dang_dung(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None, tinh: bool = False,
              ghi: bool = True) -> Tuple[bool, str]:
    """`(dừng sản xuất MỚI?, lý do)`. `tinh=False` (cổng sản xuất, giao diện): chỉ đọc tệp trạng thái — cờ chỉ có
    hiệu lực khi được tính ≤ `GIO_CO_CU` giờ trước và chủ chưa xoá sau đó. `tinh=True` (điều phối/gác tổng): tính lại
    nếu cần (`cap_nhat`). Hỏng → (False, "")."""
    try:
        bay_gio = bay_gio or _dt.datetime.now()
        tt = cap_nhat(goc, kenh, bay_gio=bay_gio, ghi=ghi) if tinh else doc(goc, kenh)
        if tt.get("trang_thai") != KHONG_PHAT:
            return False, ""
        luc = _epoch(tt.get("luc_tinh")) or 0.0
        if bay_gio.timestamp() - luc > GIO_CO_CU * 3600:
            return False, ""
        cai = _cai_kenh(goc, kenh)
        if da_tat(cai):
            return False, ""
        moc, _ng = moc_xoa_cua_chu(goc, kenh, tt, cai)
        if moc and _iso(moc) != tt.get("moc_xoa"):
            return False, ""   # chủ vừa xoá cờ — tính lại ở nhịp sau (chỉ video đăng sau mốc mới tính)
        return True, ("kênh không được YouTube phát ({0}) — dừng làm video mới, chờ chủ kiểm Studio".format(
            tt.get("ly_do") or "?"))
    except Exception:  # noqa: BLE001
        return False, ""


def xoa(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None, boi: str = "chu_cli") -> Dict[str, Any]:
    """Chủ đã kiểm Studio → ghi mốc xoá, tính lại ngay (chỉ video đăng SAU mốc này mới tính lại cờ)."""
    bay_gio = bay_gio or _dt.datetime.now()
    p = duong(goc, kenh)
    with _Khoa(p):
        tt = doc(goc, kenh)
        tt.update(kenh=kenh, moc_xoa_chu=bay_gio.isoformat(timespec="seconds"), xoa_boi=boi)
        _ghi_json(p, tt)
    return cap_nhat(goc, kenh, bay_gio=bay_gio, ep=True)


# ── cho gác tổng / Việc của bạn ─────────────────────────────────────────────

def su_co(goc: str, kenh: str, tt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sự cố cho gác tổng (`core.gac_tong.kiem_su_co`) khi kênh đang bị dừng — hình dạng `gac_tong._su_co`, mức
    khẩn, chống lặp theo đợt + nhắc lại mỗi 24 giờ. None khi không dừng."""
    if tt.get("trang_thai") != KHONG_PHAT:
        return None
    chuyen, can = _cau_viec(goc, kenh, tt)
    return {"loai": "kenh_khong_phat", "kenh": kenh, "muc": "khan", "chuyen_gi": chuyen, "can_lam_gi": can,
            "neu_khong_lam": "Kênh không có người xem; mỗi video làm thêm là tiền và kho clip đổ đi.",
            "dedupe_khoa": "kenh_khong_phat:{0}:{1}".format(kenh, tt.get("lan") or 1), "lap_gio": 24.0}


def viec_cua_ban(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> Optional[Dict[str, Any]]:
    """Mục "Việc của bạn" (dict thô cho `bang_dieu_khien._viec`) khi kênh đang bị dừng — chỉ ĐỌC trạng thái."""
    dung, _ly = dang_dung(goc, kenh, bay_gio=bay_gio)
    if not dung:
        return None
    tt = doc(goc, kenh)
    chuyen, can = _cau_viec(goc, kenh, tt)
    lan = int(tt.get("lan") or 1)
    chi_tiet = "\n".join(["{0}. {1}".format(i, d) for i, d in enumerate(danh_sach_kiem(goc, kenh), 1)] + ["", can])
    return {"khoa": "{0}:{1}:{2}".format(KHOA_VIEC, kenh, lan), "kenh": kenh, "chu": chuyen,
            "goi_y": "→ mở Studio kiểm 6 mục (bấm Chi tiết), xong bấm “Đã kiểm Studio” — máy làm video lại",
            "chi_tiet": chi_tiet}


def tom_tat(goc: str, kenh: str) -> Dict[str, Any]:
    """Bản gọn cho báo cáo (bộ não, ảnh chụp gác tổng): `{dung, trang_thai, ly_do, lan, tu_luc}` — chỉ đọc."""
    tt = doc(goc, kenh)
    dung, _ly = dang_dung(goc, kenh)
    return {"dung": dung, "trang_thai": tt.get("trang_thai") or "", "ly_do": tt.get("ly_do") or "",
            "lan": tt.get("lan") or 0, "tu_luc": tt.get("tu_luc") or "", "bang_chung": tt.get("bang_chung") or []}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.kenh_khong_phat", description="Kênh không được YouTube phát.")
    p.add_argument("lenh", nargs="?", default="xem", choices=["xem", "xoa"])
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p.add_argument("--kenh", action="append", default=[])
    p.add_argument("--thu", action="store_true", help="chỉ tính và in, không ghi gì")
    a = p.parse_args(argv)
    ks = a.kenh
    if a.lenh == "xoa":
        if not ks:
            print("Cần --kenh K")
            return 2
        for k in ks:
            tt = xoa(a.goc, k)
            print("{0}: đã ghi chủ kiểm Studio — trạng thái mới: {1} ({2})".format(k, tt.get("trang_thai"),
                                                                                tt.get("ly_do")))
        return 0
    if not ks:
        from . import tu_chay  # noqa: PLC0415

        ks = list(tu_chay.kenh_tu_chay(a.goc))
    for k in ks:
        tt = cap_nhat(a.goc, k, ghi=not a.thu, ep=True)
        print("{0}: {1} — {2}{3}".format(k, {"khong_phat": "KHÔNG ĐƯỢC PHÁT → dừng làm video mới", "song": "được phát",
                                              "chua_du": "chưa đủ số", "tat": "không được phát (bộ phát hiện TẮT)"}
                                         .get(tt.get("trang_thai"), tt.get("trang_thai") or "?"),
                                         tt.get("ly_do") or tt.get("loi") or "",
                                         " · đợt {0}".format(tt.get("lan")) if tt.get("lan") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
