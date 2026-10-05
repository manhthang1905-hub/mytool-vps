"""BỘ NÃO — một agent Claude Code chạy mỗi sáng, nhìn toàn cảnh, nhớ, tự chấm mình và chỉnh hướng (03/10/2026).

    python -m core.nao <lệnh>

Tư tưởng: dây chuyền (tự chọn → sản xuất → đăng → đo → tự học) đã tự chạy. Bộ não làm thứ nó KHÔNG làm được:
đọc cả bức tranh, suy nghĩ có giả thuyết cạnh tranh, ghi nhớ giữa các phiên, và đẩy dây chuyền một chút
(thử / tránh / đề cử nguồn / bài học / đề xuất). Nó KHÔNG sửa mã, KHÔNG đăng, KHÔNG tiêu tiền ngoài phiên của nó.

Hai nửa trong một tệp:
  1. CLI an toàn (`xem`, `thu`, `tranh`, `bai-hoc`, `uu-tien-nguon`, `de-xuat`, `cham`, `huy`) — bộ não chỉ có CỬA này.
     Giới hạn kiểm BẰNG MÃ; vượt thì từ chối kèm lý do. Quyền co lại khi dự đoán của chính nó hay sai.
  2. `phien` — dựng và chạy `claude` headless (qua `core.claude_code`), thư mục làm việc `nao/`,
     KHÔNG `bypassPermissions`: chỉ Read/Grep/Glob, Write/Edit trong `nao/`, Bash `python -m core.nao`.

Dây chuyền hỏi bộ não qua các hàm "hiệu lực" (`hieu_luc`, `tru_luot`, `he_so_cum`, `ap_uu_tien`, `dong_de_cu`,
`viec_de_xuat`). Mọi nơi gọi bọc try/except: lỗi ở đây = như không có bộ não.

Lưu trữ: `nao/hanh-dong.json` (danh sách hành động, ghi nguyên tử). Dữ liệu kênh KHÔNG được đẩy lên git
(xem `.gitignore`); chỉ `nao/CLAUDE.md` (lời nhắc hệ thống) được đẩy.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEP_HANH_DONG = "hanh-dong.json"
LENH_HANH_DONG = ("thu", "tranh", "bai-hoc", "uu-tien-nguon", "de-xuat")

# ── giới hạn (kiểm bằng mã) ──────────────────────────────────────────────────
TOI_DA_MOI_NGAY = 3
TOI_DA_MOI_NGAY_KEM = 1          # khi dự đoán của não sai nhiều
TOI_THIEU_DA_CHAM = 10           # từ ngần này hành động đã chấm mới xét "tỉ lệ đúng"
TI_LE_DUNG_TOI_THIEU = 0.5
TOI_DA_SO_VIDEO_THU = 2
TOI_DA_NGAY_TRANH = 14
TOI_DA_NGAY_KIEM = 30
NGAY_DE_XUAT_HET_HAN = 7         # đề xuất mở quá ngần này ngày mà chủ không xử lý → tự đóng `het_han`
DIEM_CONG_UU_TIEN = 1000.0
HE_SO_CUM_THU = 1.5
#: Trục mà dây chuyền THẬT SỰ đọc hiệu lực của bộ não (cum: xếp hạng nguồn; kieu_tieu_de/hook: chấm phương án;
#: kieu_bia: chọn bìa). `cong_thuc`/`do_dai` chưa nối → `thu`/`tranh` ở đó chỉ là lời nói gió, nên từ chối.
TRUC_CO_HIEU_LUC = ("cum", "kieu_tieu_de", "kieu_bia", "hook")

# ── phiên ────────────────────────────────────────────────────────────────────
MO_HINH_PHIEN = "claude-fable-5"   # bậc mạnh nhất của thang model (core.viet_max.THANG_MO_HINH[0])
SO_LUOT_TOI_DA = 40
GIO_HET_GIO_PHIEN = 30 * 60
LAN_THU_TOI_DA_MOI_NGAY = 2
CAU_HOI_PHIEN = "Bắt đầu phiên sáng {0}. Làm đúng 6 bước trong CLAUDE.md."
#: Dặn thêm cho MỌI phiên (nối vào system prompt, không sửa `nao/CLAUDE.md`). Rút từ phiên thật đầu tiên 03/10/2026:
#: não chạy 3 lệnh ghi song song và quên bước ghi trí nhớ.
CHI_DAO_PHIEN = (
    "Nhắc thêm cho phiên này: (1) Chạy lệnh `python -m core.nao` TUẦN TỰ, mỗi lượt đúng MỘT lệnh, không chạy song song. "
    "(2) Phiên chỉ XONG khi đã ghi nhật ký `nhat-ky/<ngày>.md` VÀ đã cập nhật `tri-nho/MEMORY.md` (mỗi sự thật bền một "
    "dòng, có số + ngày; nếu thật sự không có gì mới thì ghi một dòng nói rõ như vậy). Ghi trí nhớ/nhật ký BẰNG công cụ "
    "Write/Edit, không chỉ nói là đã ghi. (3) `thu`/`tranh` chỉ có hiệu lực ở các trục cum, kieu_tieu_de, kieu_bia, hook. "
    "(4) Làm ít mà chắc; mẫu n<3 thì nói rõ là chưa chắc và đừng dùng làm lý do duy nhất của một hành động.")
DONG_GIOI_THIEU_TRI_NHO = ("# Trí nhớ của bộ não\n\nSự thật bền về từng kênh (tệp khán giả, cái đã chứng minh, "
                           "cái đã thất bại). Mỗi mục một dòng, có số và ngày.\n")

def _mau(goc: str, *phan: str) -> str:
    """Mẫu đường cho quy tắc quyền của Claude Code: tuyệt đối dạng `//c/Users/...` (đo thật 03/10/2026: mẫu tương đối
    `./nhat-ky/**` KHÔNG khớp đường tuyệt đối mà Write nhận được → bị từ chối)."""
    d = os.path.abspath(os.path.join(goc, *phan)).replace("\\", "/")
    return "//" + d[0].lower() + d[2:] if len(d) > 1 and d[1] == ":" else d


def cong_cu(goc: str = GOC) -> Tuple[List[str], List[str]]:
    """`(cho phép, cấm)` cho `--allowedTools` / `--disallowedTools`. Ghi chỉ trong `nao/{tri-nho,nhat-ky,ky-nang}`;
    Bash chỉ `python -m core.nao`. Cấm thắng cho phép (kể cả `hanh-dong.json`: chỉ ghi qua CLI)."""
    cho = ["Read", "Grep", "Glob"]
    for sub in ("tri-nho", "nhat-ky", "ky-nang"):
        cho += ["Write({0}/**)".format(_mau(goc, "nao", sub)), "Edit({0}/**)".format(_mau(goc, "nao", sub))]
    cho += ["Bash(python -m core.nao)", "Bash(python -m core.nao *)"]
    cam = ["Read(**/secrets.json)", "Read(**/config.json)", "Read({0}/**)".format(_mau(goc, ".claude")),
           "Write({0})".format(_mau(goc, "nao", TEP_HANH_DONG)), "Edit({0})".format(_mau(goc, "nao", TEP_HANH_DONG)),
           "WebFetch", "WebSearch", "NotebookEdit", "Task", "Agent"]
    return cho, cam


class TuChoi(Exception):
    """Lệnh bị từ chối — thông điệp là lý do in cho bộ não."""


# ═══ lưu trữ ═════════════════════════════════════════════════════════════════

def duong_nao(goc: str = GOC) -> str:
    return os.path.join(goc, "nao")


def duong_hanh_dong(goc: str = GOC) -> str:
    return os.path.join(duong_nao(goc), TEP_HANH_DONG)


def doc_hanh_dong(goc: str = GOC) -> List[Dict[str, Any]]:
    try:
        with io.open(duong_hanh_dong(goc), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return []
    if isinstance(du, dict):
        du = du.get("hanh_dong") or []
    return [d for d in du if isinstance(d, dict)] if isinstance(du, list) else []


def _ghi_nguyen_tu(duong: str, noi_dung: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(noi_dung)
    for lan in range(5):
        try:
            os.replace(tam, duong)
            return
        except PermissionError:  # Windows: tệp đang bị chương trình khác mở
            if lan == 4:
                raise
            time.sleep(0.2)


def ghi_hanh_dong(goc: str, ds: List[Dict[str, Any]]) -> None:
    _ghi_nguyen_tu(duong_hanh_dong(goc), json.dumps(ds, ensure_ascii=False, indent=1) + "\n")


_DO_SAU_KHOA = [0]


class _khoa_hd:
    """Khoá liên tiến trình cho đọc-sửa-ghi `hanh-dong.json` (bộ não có thể chạy nhiều lệnh CÙNG LÚC; dây chuyền
    cũng ghi `da_dung`). Tạo tệp O_EXCL, chờ tối đa ~10 giây, khoá cũ > 30 giây thì giành lại; không lấy được thì
    vẫn chạy (thà ghi liều một lần còn hơn treo dây chuyền). Lồng nhau (cùng tiến trình) không khoá lại."""

    def __init__(self, goc: str) -> None:
        self.duong = os.path.join(duong_nao(goc), ".khoa-hd")
        self.co = False

    def __enter__(self) -> "_khoa_hd":
        _DO_SAU_KHOA[0] += 1
        if _DO_SAU_KHOA[0] > 1:
            return self
        os.makedirs(os.path.dirname(self.duong), exist_ok=True)
        for _ in range(100):
            try:
                os.close(os.open(self.duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                self.co = True
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.duong) > 30:
                        os.remove(self.duong)
                        continue
                except OSError:
                    pass
                time.sleep(0.1)
            except OSError:
                break
        return self

    def __exit__(self, *a: Any) -> None:
        _DO_SAU_KHOA[0] -= 1
        if self.co:
            try:
                os.remove(self.duong)
            except OSError:
                pass


def _hom_nay(bay_gio: Optional[_dt.datetime] = None) -> str:
    return (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d")


def _chuan(gia_tri: Any) -> str:
    return str(gia_tri or "").strip().lower()


def _chuan_truc(truc: Any, gia_tri: Any) -> str:
    """Nhãn chuẩn theo trục — CÙNG luật `tu_hoc.chuan_gia_tri` (vd. `khuon_thang_2` → `khuon_thang`), để `thu`/
    `tranh` khớp đúng cánh tay mà bảng điểm và bộ chọn đang dùng."""
    try:
        from . import tu_hoc  # noqa: PLC0415

        return tu_hoc.chuan_gia_tri(str(truc or ""), gia_tri)
    except Exception:  # noqa: BLE001
        return _chuan(gia_tri)


def _canh_bao(goc: str, nguon: str, loi: Any, kenh: str = "") -> None:
    try:
        from . import tu_hoc  # noqa: PLC0415

        tu_hoc.canh_bao(goc, nguon, loi, kenh)
    except Exception:  # noqa: BLE001
        pass


# ═══ kiểm tra / tạo hành động ═════════════════════════════════════════════════

def _kenh_ton_tai(goc: str, ma: str) -> bool:
    if not ma:
        return False
    try:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        return ma in liet_ke_kenh(goc)
    except Exception:  # noqa: BLE001
        return os.path.isfile(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"))


def _ngay(chu: Any) -> Optional[_dt.date]:
    try:
        return _dt.datetime.strptime(str(chu or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def ti_le_dung(ds: List[Dict[str, Any]]) -> Tuple[int, int]:
    """`(số đúng, số đã chấm)` — chỉ tính hành động có dự đoán (không tính ghi cộng/trừ)."""
    da = [d for d in ds if d.get("cham") in ("dung", "sai") and not d.get("khong_tinh")]
    return sum(1 for d in da if d["cham"] == "dung"), len(da)


def han_muc_ngay(ds: List[Dict[str, Any]]) -> int:
    """Quyền theo thành tích: ≥ 10 hành động đã chấm mà đúng < 50% thì chỉ 1 hành động/ngày."""
    dung, tong = ti_le_dung(ds)
    if tong >= TOI_THIEU_DA_CHAM and dung / tong < TI_LE_DUNG_TOI_THIEU:
        return TOI_DA_MOI_NGAY_KEM
    return TOI_DA_MOI_NGAY


def _dang_mo_thu(ds: List[Dict[str, Any]], kenh: str, truc: str) -> Optional[Dict[str, Any]]:
    for d in ds:
        ts = d.get("tham_so") or {}
        if (d.get("lenh") == "thu" and d.get("trang_thai") == "mo" and ts.get("kenh") == kenh
                and ts.get("truc") == truc):
            return d
    return None


def _kiem_truc_gia_tri(truc: str, gia_tri: str) -> str:
    from . import tu_hoc  # noqa: PLC0415

    if truc not in TRUC_CO_HIEU_LUC:
        raise TuChoi("trục “{0}” chưa được dây chuyền đọc — `thu`/`tranh` chỉ có hiệu lực ở: {1}".format(
            truc, ", ".join(TRUC_CO_HIEU_LUC)))
    if not gia_tri:
        raise TuChoi("thiếu --gia-tri")
    tap = tu_hoc._TAP_NHAN.get(truc)
    if tap and gia_tri not in tap:
        raise TuChoi("giá trị “{0}” không hợp lệ cho trục {1} — chọn: {2}".format(gia_tri, truc, ", ".join(tap)))
    return gia_tri


def tao_hanh_dong(goc: str, *a: Any, **kw: Any) -> Any:
    with _khoa_hd(goc):
        return _tao_hanh_dong_g(goc, *a, **kw)


def _tao_hanh_dong_g(goc: str, lenh: str, tham_so: Dict[str, Any], *, ly_do: str = "", du_doan: str = "",
                  kiem_ngay: str = "", bay_gio: Optional[_dt.datetime] = None,
                  khong_tinh: bool = False) -> Dict[str, Any]:
    """Kiểm giới hạn rồi ghi MỘT hành động mới. Ném `TuChoi` kèm lý do khi vượt quyền.
    `khong_tinh=True` (bài học cộng/trừ): không cần dự đoán, không tính vào hạn mức ngày và tỉ lệ đúng."""
    bay_gio = bay_gio or _dt.datetime.now()
    hom_nay = _hom_nay(bay_gio)
    ds = doc_hanh_dong(goc)
    don_het_han(goc, ds, bay_gio)
    if not khong_tinh:
        if not (du_doan or "").strip() or len((du_doan or "").strip()) < 10:
            raise TuChoi("thiếu --du-doan (một câu đo được, ví dụ “2 video kế của TL2 thuộc cụm X có hiển thị 48h ≥ trung vị kênh”)")
        if len((ly_do or "").strip()) < 10:
            raise TuChoi("thiếu --ly-do (có số thật: video_id, hiển thị, CTR...)")
        han = _ngay(kiem_ngay)
        if han is None:
            raise TuChoi("--kiem-ngay phải dạng YYYY-MM-DD")
        hom = _ngay(hom_nay)
        if han <= hom:
            raise TuChoi("--kiem-ngay phải SAU hôm nay ({0})".format(hom_nay))
        if (han - hom).days > TOI_DA_NGAY_KIEM:
            raise TuChoi("--kiem-ngay tối đa {0} ngày kể từ hôm nay".format(TOI_DA_NGAY_KIEM))
        da_dung = sum(1 for d in ds if str(d.get("luc") or "")[:10] == hom_nay
                      and not d.get("khong_tinh") and d.get("trang_thai") != "huy")
        tran = han_muc_ngay(ds)
        if da_dung >= tran:
            dung, tong = ti_le_dung(ds)
            vi_sao = (" (quyền bị co vì tỉ lệ đúng {0}/{1} < 50% — chấm lại cho thật thà và rút kinh nghiệm)"
                      .format(dung, tong) if tran < TOI_DA_MOI_NGAY else "")
            raise TuChoi("hôm nay đã dùng {0}/{1} hành động{2}".format(da_dung, tran, vi_sao))
    kenh = str(tham_so.get("kenh") or "")
    if lenh != "de-xuat" or kenh:
        if not _kenh_ton_tai(goc, kenh):
            raise TuChoi("kênh “{0}” không tồn tại".format(kenh))
    # 03/10/2026: ngày kiểm phải SAU lúc video bị ảnh hưởng có số 48h — tức khe trống kế tiếp của kênh
    # (video đã hẹn lịch không còn đổi được) + 2 ngày. Phiên đầu tiên đặt 10/10 cho TL3 dù khe kế là 13/10.
    if not khong_tinh and kenh and lenh in ("thu", "tranh", "uu-tien-nguon"):
        try:
            from . import kenh as _kenh_mod, xep_lich  # noqa: PLC0415
            ngay_k, _g = xep_lich.khe_trong_som_nhat(goc, kenh, _kenh_mod.doc_kenh(goc, kenh), bay_gio=bay_gio)
            som = (_dt.datetime.strptime(ngay_k, "%d/%m/%Y").date() + _dt.timedelta(days=2)) if ngay_k else None
        except Exception:  # noqa: BLE001 — không tính được thì không chặn
            som = None
        han = _ngay(kiem_ngay)
        if som is not None and han is not None and han < som:
            raise TuChoi("--kiem-ngay {0} quá sớm: video đầu tiên chịu ảnh hưởng đăng {1}, có số 48h từ {2} "
                         "(video đã hẹn lịch không đổi được). Đặt ≥ {2}.".format(
                             kiem_ngay, ngay_k, som.isoformat()))
    if lenh == "thu":
        n = int(tham_so.get("so_video") or 0)
        if not 1 <= n <= TOI_DA_SO_VIDEO_THU:
            raise TuChoi("--so-video phải từ 1 tới {0}".format(TOI_DA_SO_VIDEO_THU))
        _kiem_truc_gia_tri(str(tham_so.get("truc")), str(tham_so.get("gia_tri")))
        cu = _dang_mo_thu(ds, kenh, str(tham_so["truc"]))
        if cu:
            raise TuChoi("kênh {0} trục {1} đã có một lần thử đang mở ({2}: {3}) — chờ nó xong hoặc `huy {2}`".format(
                kenh, tham_so["truc"], cu["id"], (cu.get("tham_so") or {}).get("gia_tri")))
        if _hieu_luc_tu(ds, kenh, str(tham_so["truc"]), bay_gio).get(_chuan(tham_so["gia_tri"])) == 0.0:
            raise TuChoi("giá trị này đang bị `tranh` — gỡ `tranh` trước")
    elif lenh == "tranh":
        n = int(tham_so.get("ngay") or 0)
        if not 1 <= n <= TOI_DA_NGAY_TRANH:
            raise TuChoi("--ngay phải từ 1 tới {0}".format(TOI_DA_NGAY_TRANH))
        _kiem_truc_gia_tri(str(tham_so.get("truc")), str(tham_so.get("gia_tri")))
        if _hieu_luc_tu(ds, kenh, str(tham_so["truc"]), bay_gio).get(_chuan(tham_so["gia_tri"])) == 1.0:
            raise TuChoi("giá trị này đang được `thu` — `huy` lần thử trước")
        tham_so["het_han"] = (bay_gio.date() + _dt.timedelta(days=n)).isoformat()
    elif lenh == "uu-tien-nguon":
        if not re.match(r"^https?://", str(tham_so.get("link") or "")):
            raise TuChoi("--link phải là địa chỉ http(s) của video đối thủ")
        if not (ly_do or "").strip():
            raise TuChoi("thiếu --ly-do")
    elif lenh == "de-xuat":
        if not str(tham_so.get("noi_dung") or "").strip():
            raise TuChoi("thiếu nội dung đề xuất")
    n_id = 1 + max([int(m.group(1)) for d in ds for m in [re.match(r"^n(\d+)$", str(d.get("id") or ""))] if m] or [0])
    hd = {"id": "n{0:03d}".format(n_id), "luc": bay_gio.replace(microsecond=0).isoformat(), "lenh": lenh,
          "tham_so": tham_so, "ly_do": (ly_do or "").strip(), "du_doan": (du_doan or "").strip(),
          "kiem_ngay": (kiem_ngay or "").strip(), "trang_thai": "xong" if khong_tinh else "mo",
          "cham": None, "ghi_chu_cham": ""}
    if khong_tinh:
        hd["khong_tinh"] = True
    if lenh == "thu":
        hd["tham_so"]["da_dung"] = 0
    ds.append(hd)
    ghi_hanh_dong(goc, ds)
    return hd


def _qua_han_de_xuat(d: Dict[str, Any], hom_nay: str) -> bool:
    """Đề xuất còn mở mà đã quá `NGAY_DE_XUAT_HET_HAN` ngày kể từ lúc đề xuất."""
    ngay_de, hom = _ngay(str(d.get("luc") or "")[:10]), _ngay(hom_nay)
    return bool(d.get("lenh") == "de-xuat" and d.get("trang_thai") == "mo" and ngay_de and hom
                and (hom - ngay_de).days > NGAY_DE_XUAT_HET_HAN)


def don_het_han(goc: str, ds: Optional[List[Dict[str, Any]]] = None, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """`tranh` quá hạn / `thu` hết lượt → `xong` (chờ chấm); `de-xuat` mở quá 7 ngày chủ không xử lý → `het_han`
    (không hiện cho chủ nữa; bộ não thấy trong `xem` để tự quyết lại). Ghi lại nếu có đổi."""
    ds = doc_hanh_dong(goc) if ds is None else ds
    hom_nay = _hom_nay(bay_gio)
    doi = False
    for d in ds:
        if d.get("trang_thai") == "mo" and d.get("lenh") == "tranh" and str((d.get("tham_so") or {}).get("het_han") or "9") < hom_nay:
            d["trang_thai"] = "xong"
            doi = True
        elif _qua_han_de_xuat(d, hom_nay):
            d["trang_thai"] = "het_han"
            d["het_han_luc"] = hom_nay
            doi = True
    if doi:
        ghi_hanh_dong(goc, ds)
    return doi


# ═══ HIỆU LỰC vào dây chuyền ══════════════════════════════════════════════════

def _hieu_luc_tu(ds: List[Dict[str, Any]], kenh: str, truc: str, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, float]:
    hom_nay = _hom_nay(bay_gio)
    ra: Dict[str, float] = {}
    for d in ds:
        ts = d.get("tham_so") or {}
        if d.get("trang_thai") != "mo" or ts.get("kenh") != kenh or ts.get("truc") != truc:
            continue
        gt = _chuan_truc(truc, ts.get("gia_tri"))
        if not gt:
            continue
        if d.get("lenh") == "thu" and int(ts.get("da_dung") or 0) < int(ts.get("so_video") or 0):
            ra.setdefault(gt, 1.0)
        elif d.get("lenh") == "tranh" and str(ts.get("het_han") or "") >= hom_nay:
            ra[gt] = 0.0  # tránh thắng thử
    return ra


def hieu_luc(goc: str, kenh: str, truc: str, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, float]:
    """`{giá trị (chữ thường): điểm}`: `thu` còn lượt → 1,0 (trần), `tranh` còn hạn → 0,0 (sàn). Hỏng → {}."""
    try:
        return _hieu_luc_tu(doc_hanh_dong(goc), kenh, truc, bay_gio)
    except Exception as loi:  # noqa: BLE001 — sổ hành động hỏng: não mất hiệu lực, phải có cảnh báo
        _canh_bao(goc, "nao.hieu_luc", loi, kenh)
        return {}


def ap_hieu_luc_rut(goc: str, kenh: str, truc: str, ket: Dict[str, float]) -> Dict[str, float]:
    """Đè điểm Thompson (`tu_hoc.rut`) theo hiệu lực của bộ não."""
    try:
        for g, v in hieu_luc(goc, kenh, truc).items():
            for k in list(ket):
                if _chuan_truc(truc, k) == g:
                    ket[k] = v
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, "nao.ap_hieu_luc_rut", loi, kenh)
    return ket


def he_so_cum(goc: str, kenh: str, cum: str, he: float) -> float:
    """Hệ số xếp hạng của một cụm: `thu` → 1,5 (mạnh hơn trần 1,2 của Thompson); `tranh` → giữ sàn Thompson."""
    try:
        if hieu_luc(goc, kenh, "cum").get(_chuan_truc("cum", cum)) == 1.0:
            return HE_SO_CUM_THU
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, "nao.he_so_cum", loi, kenh)
    return he


def co_hieu_luc(goc: str, kenh: str, truc: str) -> bool:
    return bool(hieu_luc(goc, kenh, truc))


def tru_luot(goc: str, *a: Any, **kw: Any) -> Any:
    with _khoa_hd(goc):
        return _tru_luot_g(goc, *a, **kw)


def _tru_luot_g(goc: str, kenh: str, nuoc: Dict[str, Any], ma_goi: str = "") -> int:
    """Một ván MỚI vừa ghi (`tu_hoc.ghi_van`) với `nuoc` → trừ 1 lượt mọi `thu` mở khớp. Hết lượt → `xong`.
    `ma_goi` được ghi vào `tham_so.goi` — lúc tới hạn kiểm, `xem` in kết quả ĐÚNG các video ấy cho não chấm.
    Trả số hành động bị trừ. Hỏng thì 0 (có cảnh báo), không ném."""
    try:
        ds = doc_hanh_dong(goc)
        n = 0
        for d in ds:
            ts = d.get("tham_so") or {}
            if d.get("lenh") != "thu" or d.get("trang_thai") != "mo" or ts.get("kenh") != kenh:
                continue
            truc = ts.get("truc")
            if _chuan_truc(truc, (nuoc or {}).get(truc)) != _chuan_truc(truc, ts.get("gia_tri")):
                continue
            ts["da_dung"] = int(ts.get("da_dung") or 0) + 1
            if ma_goi and ma_goi not in (ts.get("goi") or []):
                ts["goi"] = list(ts.get("goi") or []) + [ma_goi]
            n += 1
            if ts["da_dung"] >= int(ts.get("so_video") or 0):
                d["trang_thai"] = "xong"
        if n:
            ghi_hanh_dong(goc, ds)
        return n
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, "nao.tru_luot", loi, kenh)
        return 0


def ket_qua_goi(goc: str, kenh: str, goi: Any) -> List[str]:
    """Kết quả ĐO ĐƯỢC của các video một hành động `thu` đã sinh ra (`tham_so.goi`), từ ván tự học + hồ sơ video:
    `["<mã gói>: 48h THẮNG/trượt/chờ, 7d …, CTR … — hiển thị @48h …"]`. Không đọc được → []."""
    try:
        from . import tu_hoc  # noqa: PLC0415
        from .chien_luoc import ket_qua  # noqa: PLC0415

        van = tu_hoc.doc_van(goc, kenh)
        hs_ds = ket_qua.ho_so_theo_goi(goc, kenh)
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, "nao.ket_qua_goi", loi, kenh)
        return []
    chu = {"thang": "THẮNG", "truot": "trượt"}
    ra = []
    for ma in goi or []:
        v, hs = van.get(ma) or {}, hs_ds.get(ma) or {}
        m = tu_hoc._moc_do_duoc(hs)  # noqa: SLF001
        ra.append("{0}: 48h {1}, 7d {2}, CTR-so-kênh {3} — hiển thị @48h {4}, CTR {5}".format(
            ma, chu.get(v.get("ket48"), "chờ"), chu.get(v.get("ket7"), "chờ"), chu.get(v.get("ket_ctr"), "chờ"),
            _f(m.get("impressions")), _f(m.get("ctr"), 2, "%")))
    return ra


# ── đề cử nguồn ──────────────────────────────────────────────────────────────

_RE_ID_VIDEO = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/embed/)([\w-]{11})")


def _khoa_link(link: Any) -> str:
    s = str(link or "").strip()
    m = _RE_ID_VIDEO.search(s)
    return m.group(1) if m else s.rstrip("/").lower()


def _de_cu_mo(goc: str, kenh: str) -> List[Dict[str, Any]]:
    return [d for d in doc_hanh_dong(goc) if d.get("lenh") == "uu-tien-nguon" and d.get("trang_thai") == "mo"
            and (d.get("tham_so") or {}).get("kenh") == kenh]


def ap_uu_tien(goc: str, kenh: str, ds: List[Dict[str, Any]], log: Any = None) -> List[Dict[str, Any]]:
    """Ứng viên có link được bộ não đề cử → cộng điểm mạnh và đưa lên đầu bảng. Link không có trong bảng
    thì không làm gì ở đây (chỉ còn lời nhắc biên tập, xem `dong_de_cu`). Hỏng → trả `ds` nguyên."""
    try:
        cu = {_khoa_link((d.get("tham_so") or {}).get("link")): d for d in _de_cu_mo(goc, kenh)}
        if not cu or not ds:
            return ds
        dau, con = [], []
        for u in ds:
            d = cu.get(_khoa_link(u.get("link")))
            if d is None:
                con.append(u)
                continue
            u = dict(u)
            u["diem_goc_nao"] = u.get("diem", 0)
            try:
                u["diem"] = round(float(u.get("diem") or 0) + DIEM_CONG_UU_TIEN, 2)
            except (TypeError, ValueError):
                u["diem"] = DIEM_CONG_UU_TIEN
            u["bo_nao"] = d.get("ly_do") or ""
            dau.append(u)
            _DE_CU_THAY.setdefault(kenh, set()).add(d["id"])
            if log:
                log("  [bộ não] đề cử {0}: {1}".format(d["id"], (d.get("ly_do") or "")[:100]))
        if log:
            for d in cu.values():
                if d["id"] not in _DE_CU_THAY.get(kenh, ()):
                    log("  [bộ não] đề cử {0} KHÔNG có trong danh sách ứng viên (bị lọc: đã làm / quá cũ / lạc ngách / "
                        "thiếu lời thoại) — giữ lại cho lượt sau".format(d["id"]))
        return dau + con if dau else ds
    except Exception:  # noqa: BLE001
        return ds


def dong_de_cu(goc: str, kenh: str) -> List[str]:
    """Dòng "Bộ não đề cử: … vì …" cho lời nhắc biên tập (mọi đề cử còn mở của kênh)."""
    try:
        return ["- Bộ não đề cử: {0} vì {1}".format((d.get("tham_so") or {}).get("link"), (d.get("ly_do") or "")[:240])
                for d in _de_cu_mo(goc, kenh)[:3]]
    except Exception:  # noqa: BLE001
        return []


def dung_xong_de_cu(goc: str, *a: Any, **kw: Any) -> Any:
    with _khoa_hd(goc):
        return _dung_xong_de_cu_g(goc, *a, **kw)


#: id đề cử đã THẬT SỰ có mặt trong danh sách ứng viên ở lượt chọn này (cùng tiến trình với `_chon_nguon`).
_DE_CU_THAY: Dict[str, set] = {}
#: Đề cử vắng mặt khỏi danh sách ứng viên ngần này lượt thì đóng, không tính điểm (04/10/2026).
DE_CU_VANG_TOI_DA = 3


def _dung_xong_de_cu_g(goc: str, kenh: str) -> int:
    """Lần chọn content thật đã chạy → đề cử nào ĐÃ có mặt trong danh sách ứng viên thì `xong` (dùng MỘT lần).
    04/10/2026: trước đây mọi đề cử mở đều `xong` dù link không có trong bảng (TL3 n001: nguồn đề cử bị lọc,
    lượt chọn nguồn khác, hành động "xong" mà không có hiệu lực). Vắng mặt → giữ lại, quá
    `DE_CU_VANG_TOI_DA` lượt thì đóng `khong_tinh` kèm lý do để não tự quyết lại."""
    try:
        ds = doc_hanh_dong(goc)
        thay = _DE_CU_THAY.pop(kenh, set())
        n = 0
        luc = _dt.datetime.now().replace(microsecond=0).isoformat()
        for d in ds:
            if d.get("lenh") == "uu-tien-nguon" and d.get("trang_thai") == "mo" and (d.get("tham_so") or {}).get("kenh") == kenh:
                ts = d.setdefault("tham_so", {})
                if d.get("id") in thay:
                    d["trang_thai"] = "xong"
                    ts["da_dung_luc"] = luc
                else:
                    ts["lan_vang"] = int(ts.get("lan_vang") or 0) + 1
                    if ts["lan_vang"] < DE_CU_VANG_TOI_DA:
                        n += 1
                        continue
                    d["trang_thai"] = "xong"
                    d["khong_tinh"] = True
                    d["ghi_chu_cham"] = ("nguồn đề cử không vào danh sách ứng viên {0} lượt (bị lọc: đã làm / quá cũ / "
                                         "lạc ngách / thiếu lời thoại) — không có hiệu lực, không tính điểm").format(ts["lan_vang"])
                n += 1
        if n:
            ghi_hanh_dong(goc, ds)
        return n
    except Exception:  # noqa: BLE001
        return 0


# ── đề xuất cho chủ ──────────────────────────────────────────────────────────

def viec_de_xuat(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, str]]:
    """Đề xuất còn mở (≤ 7 ngày) cho "Việc của bạn": `[{khoa, kenh, chu, goi_y}]`. Hỏng → []."""
    try:
        return [{"khoa": "nao:" + d["id"], "kenh": str((d.get("tham_so") or {}).get("kenh") or ""),
                 "chu": "Bộ não đề xuất: " + str((d.get("tham_so") or {}).get("noi_dung") or "")[:300],
                 "goi_y": "→ duyệt hoặc bỏ qua; não đoán: {0} (kiểm {1})".format(
                     (d.get("du_doan") or "")[:120], d.get("kiem_ngay") or "?")}
                for d in doc_hanh_dong(goc) if d.get("lenh") == "de-xuat" and d.get("trang_thai") == "mo"
                and not _qua_han_de_xuat(d, _hom_nay(bay_gio))]
    except Exception:  # noqa: BLE001
        return []


# ═══ LỆNH ĐỌC ════════════════════════════════════════════════════════════════

def _cat(chu: Any, n: int) -> str:
    s = " ".join(str(chu or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def _so(x: Any) -> Optional[float]:
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def _f(x: Any, le: int = 0, hau: str = "") -> str:
    v = _so(x)
    if v is None:
        return "?"
    return ("{0:,.%df}" % le).format(v).replace(",", ".") + hau if le == 0 else ("{0:.%df}" % le).format(v) + hau


def dong_hanh_dong(d: Dict[str, Any]) -> str:
    ts = d.get("tham_so") or {}
    chi = {"thu": lambda: "{0}/{1}={2} x{3} (đã {4})".format(ts.get("kenh"), ts.get("truc"), ts.get("gia_tri"),
                                                           ts.get("so_video"), ts.get("da_dung")),
           "tranh": lambda: "{0}/{1}={2} tới {3}".format(ts.get("kenh"), ts.get("truc"), ts.get("gia_tri"), ts.get("het_han")),
           "uu-tien-nguon": lambda: "{0} {1}".format(ts.get("kenh"), _cat(ts.get("link"), 60)),
           "bai-hoc": lambda: "{0} {1} {2}".format(ts.get("kenh"), ts.get("thao_tac"), _cat(ts.get("noi_dung") or ts.get("id"), 70)),
           "de-xuat": lambda: _cat(ts.get("noi_dung"), 90)}.get(d.get("lenh"), lambda: "")()
    cham = ""
    if d.get("cham"):
        cham = " | CHẤM {0}: {1}".format(d["cham"].upper(), _cat(d.get("ghi_chu_cham"), 80))
    return "{0} [{1}] {2} {3} | lý do: {4} | đoán: {5} | kiểm {6}{7}".format(
        d.get("id"), d.get("trang_thai"), d.get("lenh"), chi, _cat(d.get("ly_do"), 70), _cat(d.get("du_doan"), 90),
        d.get("kiem_ngay") or "-", cham)


def bao_cao_hanh_dong(goc: str, bay_gio: Optional[_dt.datetime] = None, chi_can_chu_y: bool = False) -> List[str]:
    hom_nay = _hom_nay(bay_gio)
    ds = doc_hanh_dong(goc)
    don_het_han(goc, ds, bay_gio)
    dung, tong = ti_le_dung(ds)
    da = sum(1 for d in ds if str(d.get("luc") or "")[:10] == hom_nay and not d.get("khong_tinh") and d.get("trang_thai") != "huy")
    dong = ["Hành động của não: {0} tổng; đã chấm {1} (đúng {2}); hôm nay dùng {3}/{4} hành động.".format(
        len(ds), tong, dung, da, han_muc_ngay(ds))]
    hien = []
    for d in ds:
        toi_han = d.get("trang_thai") in ("mo", "xong") and not d.get("cham") and not d.get("khong_tinh") \
            and str(d.get("kiem_ngay") or "9") <= hom_nay
        if chi_can_chu_y and not (d.get("trang_thai") == "mo" or toi_han):
            continue
        hien.append(("TỚI HẠN KIỂM " if toi_han else "") + dong_hanh_dong(d))
        ts = d.get("tham_so") or {}
        if d.get("lenh") == "thu" and (toi_han or ts.get("goi")):
            # Vòng kín cho não: in số ĐO ĐƯỢC của đúng các video lần thử này sinh ra — não chấm `dung|sai` theo số,
            # không phải tự đi tìm video nào thuộc lần thử.
            kq = ket_qua_goi(goc, str(ts.get("kenh") or ""), ts.get("goi"))
            hien += ["    ↳ " + x for x in kq] or (["    ↳ chưa ra video nào khớp lần thử — huỷ hoặc chấm `sai` kèm lý do"]
                                                if toi_han else [])
    if not hien:
        dong.append("  (không có hành động mở / tới hạn kiểm)" if chi_can_chu_y else "  (chưa có hành động nào)")
    return dong + ["  " + h for h in hien[-40:]]


def _hieu_luc_kenh(goc: str) -> Dict[Tuple[str, str, str], str]:
    ra: Dict[Tuple[str, str, str], str] = {}
    for d in doc_hanh_dong(goc):
        ts = d.get("tham_so") or {}
        if d.get("trang_thai") == "mo" and d.get("lenh") in ("thu", "tranh"):
            ra[(ts.get("kenh"), ts.get("truc"), _chuan_truc(ts.get("truc"), ts.get("gia_tri")))] = (
                "THỬ còn {0} lượt".format(int(ts.get("so_video") or 0) - int(ts.get("da_dung") or 0)) if d["lenh"] == "thu"
                else "TRÁNH tới {0}".format(ts.get("het_han")))
    return ra


def dong_bang_diem(goc: str, kenh: str, toi_da: int = 0) -> List[str]:
    from . import tu_hoc  # noqa: PLC0415

    bd = tu_hoc.bang_diem(goc, kenh)
    nao = _hieu_luc_kenh(goc)
    ra: List[str] = []
    for truc in tu_hoc.TRUC:
        if truc not in bd:
            continue
        hang = sorted(bd[truc].items(), key=lambda x: (-x[1]["n"], -x[1]["a"] / (x[1]["a"] + x[1]["b"])))
        ra.append("  {0}:".format(truc))
        for gt, o in (hang[:toi_da] if toi_da else hang):
            ra.append("    {0}: thắng {1}/{2}{5}{6}, TB Beta {3:.2f}{4}".format(
                _cat(gt, 40), o["thang"], o["n"], o["a"] / (o["a"] + o["b"]),
                " [{0}]".format(nao[(kenh, truc, _chuan(gt))]) if (kenh, truc, _chuan(gt)) in nao else "",
                ", hiển thị48h≥tv {0}/{1}".format(o["thang_tv"], o["n_tv"]) if o.get("n_tv") else "",
                ", CTR≥tv {0}/{1}".format(o["thang_ctr"], o["n_ctr"]) if o.get("n_ctr") else ""))
    return ra or ["  (bảng điểm trống — chưa có ván nào có kết luận)"]


def _doc_tom_tat(goc: str, kenh: str) -> List[Dict[str, str]]:
    """`CHANNEL/<kênh>/chi-so/bang-tom-tat.csv` — số MỚI NHẤT mỗi video (hiển thị, CTR, xem, AVD, % giữ, sub)."""
    import csv  # noqa: PLC0415

    try:
        with io.open(os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv"), encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (OSError, csv.Error):
        return []


def _video_gan_day(goc: str, kenh: str, ngay: int, bay_gio: Optional[_dt.datetime]) -> List[str]:
    """Video đăng trong `ngay` ngày: số mới nhất từ bảng tóm tắt Studio + nhãn từ ván tự học."""
    from . import tu_hoc  # noqa: PLC0415
    from .chien_luoc import ket_qua  # noqa: PLC0415

    han = ((bay_gio or _dt.datetime.now()).date() - _dt.timedelta(days=ngay)).isoformat()
    van = tu_hoc.doc_van(goc, kenh)
    theo_vid: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for ma, hs in ket_qua.ho_so_theo_goi(goc, kenh).items():
        if hs.get("video_id"):
            theo_vid[str(hs["video_id"])] = (ma, hs)
    ra = []
    for r in _doc_tom_tat(goc, kenh):
        vid, d = str(r.get("Mã video") or ""), str(r.get("Ngày đăng") or "")
        if not vid or d < han:
            continue
        ma, hs = theo_vid.get(vid, ("", {}))
        v = van.get(ma) or {}
        nuoc = v.get("nuoc") or {}
        kl = v.get("ket7") or v.get("ket48") or ""
        ra.append((d, "  {0} {1} | {2} | cụm {3} | tiêu đề {4} | @{5}: hiển thị {6}, CTR {7}, xem {8}, AVD {9} ({10}), sub {11} | giờ xem 7d {12} | {13}".format(
            vid + ("/" + ma if ma else ""), d[5:], _cat(r.get("Tiêu đề"), 34), _cat(nuoc.get("cum"), 22) or "?", nuoc.get("kieu_tieu_de") or "?",
            r.get("Mốc mới nhất") or "?", r.get("Lượt hiển thị") or "?", r.get("Tỷ lệ bấm") or "?", r.get("Lượt xem") or "?",
            r.get("Xem TB") or "?", r.get("% độ dài") or "?", r.get("Đăng ký") or "?", _f(tu_hoc._gio_7d(hs), 1),
            {"thang": "THẮNG", "truot": "trượt"}.get(kl, "chờ"))))
    return [x[1] for x in sorted(ra, key=lambda x: x[0], reverse=True)]


def doi_thu_dang_no(goc: str, n: int = 8, ngay: int = 14, bay_gio: Optional[_dt.datetime] = None) -> Tuple[List[str], str]:
    """Video đối thủ mới đăng trong `ngay` ngày, view cao nhất, từ các lần quét kênh của nhóm. `(dòng, thư mục)`."""
    mau = os.path.join(goc, "CHANNEL", "_NHOM", "*", "nghien-cuu", "quet-kenh")
    han = ((bay_gio or _dt.datetime.now()).date() - _dt.timedelta(days=ngay)).strftime("%Y-%m-%d")
    tim: Dict[str, Tuple[float, str]] = {}
    for tep in glob.glob(os.path.join(mau, "*.json")):
        try:
            with io.open(tep, encoding="utf-8") as f:
                ch = (json.load(f) or {}).get("ch") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for v in ch.get("videos") or []:
            ud = str(v.get("upload_date") or "")
            vw = _so(v.get("views"))
            if not ud or ud < han or vw is None or not v.get("video_id"):
                continue
            tim[v["video_id"]] = (vw, "  {0} | {1} | {2} view, kênh {3} ({4} sub) | {5} | {6}".format(
                v["video_id"], ud[5:], _f(vw), _cat(ch.get("name"), 22), _f(ch.get("subscribers")), _cat(v.get("title"), 44),
                v.get("url") or ""))
    top = sorted(tim.values(), key=lambda x: -x[0])[:n]
    return [t[1] for t in top], os.path.dirname(mau)


def bao_cao(goc: str = GOC, bay_gio: Optional[_dt.datetime] = None, toi_da_dong: int = 250) -> str:
    """Báo cáo `xem`: gọn (≤ ~250 dòng), mỗi phần bọc try riêng — hỏng phần nào chỉ phần đó báo lỗi."""
    from . import tu_hoc  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    d: List[str] = ["BÁO CÁO CHO BỘ NÃO — {0}".format(bay_gio.strftime("%Y-%m-%d %H:%M"))]

    def phan(ten: str, ham: Any) -> None:
        d.append("")
        d.append("== " + ten + " ==")
        try:
            d.extend(ham())
        except Exception as loi:  # noqa: BLE001
            d.append("  (lỗi đọc phần này: {0}: {1})".format(type(loi).__name__, _cat(loi, 120)))

    try:
        from . import bang_dieu_khien as bdk  # noqa: PLC0415

        anh = bdk.anh_bang(goc, bay_gio=bay_gio)
    except Exception as loi:  # noqa: BLE001
        anh = {"kenh": [], "viec": []}
        d.append("(không dựng được ảnh bảng điều khiển: {0})".format(_cat(loi, 120)))
        bdk = None
    kenh_ds = [k for k in anh.get("kenh") or [] if k.get("ma")]

    def kenh() -> List[str]:
        ra = []
        for k in kenh_ds:
            y = k.get("ypp") or {}
            lich = []
            try:
                lich = [x.get("chu") or x.get("luc") for x in bdk.lich_dang_tiep(goc, k, bay_gio=bay_gio)][:3]
            except Exception:  # noqa: BLE001
                pass
            ra.append("- {0}: {1}".format(k["ma"], _cat(bdk.cau_tinh_trang(k), 150)))
            ra.append("    YPP: {0} sub, {1} giờ xem — {2}".format(_f(y.get("dang_ky")), _f(y.get("gio_xem"), 0),
                                                                    _cat(k.get("con_thieu_ypp"), 100)))
            ra.append("    lịch đăng tới: {0}".format("; ".join(lich) if lich else (_cat(k.get("video_ke_tiep"), 60) or "chưa có")))
        return ra

    def bat_buoc() -> List[str]:
        from . import nao_goi_y  # noqa: PLC0415

        return nao_goi_y.dong_bat_buoc(goc, [k["ma"] for k in kenh_ds], bay_gio)

    phan("VIỆC BẮT BUỘC XEM HÔM NAY (máy tính sẵn — xử lý TRƯỚC: chạy lệnh kèm theo hoặc ghi lý do bỏ qua vào nhật ký)", bat_buoc)
    phan("KÊNH", kenh)

    def video() -> List[str]:
        ra = []
        for k in kenh_ds:
            vs = _video_gan_day(goc, k["ma"], 14, bay_gio)
            if vs:
                ra.append("- {0} ({1} video trong 14 ngày):".format(k["ma"], len(vs)))
                ra += vs[:8]
        return ra or ["  (không có video 14 ngày gần đây có hồ sơ)"]

    phan("VIDEO 14 NGÀY (video_id/mã gói — hồ sơ ở ho-so-video/<mã gói>.json — mm-dd | tiêu đề | cụm | kiểu tiêu đề | số mới nhất @mốc | thắng/trượt theo kênh)", video)

    def diem() -> List[str]:
        ra = []
        for k in kenh_ds:
            dl = dong_bang_diem(goc, k["ma"], toi_da=3)
            if len(dl) > 1 or "trống" not in dl[0]:
                ra.append("- {0}:".format(k["ma"]))
                ra += dl
        return ra or ["  (chưa kênh nào có bảng điểm)"]

    phan("BẢNG ĐIỂM TỰ HỌC (top 3 mỗi trục; đầy đủ: `bang-diem <kênh>`)", diem)

    def bai() -> List[str]:
        from .giam_doc import kham_nghiem as kn  # noqa: PLC0415

        ra = []
        for k in kenh_ds:
            for b in kn.doc_bai_hoc(goc, k["ma"])[:5]:
                ra.append("  {0} {1} {2} [{3}] cộng {4}/trừ {5}: {6}".format(
                    k["ma"], b["id"], "{0}={1}".format(b["truc"], b["gia_tri"])[:26], b["trang_thai"], b["cong"], b["tru"],
                    _cat(b["cau"], 100)))
        return ra or ["  (sổ bài học trống)"]

    phan("BÀI HỌC (id dùng cho `bai-hoc cong|tru`)", bai)

    def hieu_chinh() -> List[str]:
        ra = [("  {0}: {1}".format(k["ma"], tu_hoc.cau_hieu_chinh(goc, k["ma"]))) for k in kenh_ds
              if tu_hoc.cau_hieu_chinh(goc, k["ma"])]
        return ra or ["  (chưa đủ ván có cả dự đoán lẫn số thật)"]

    phan("HIỆU CHỈNH DỰ ĐOÁN CỦA BIÊN TẬP", hieu_chinh)
    phan("HÀNH ĐỘNG CỦA NÃO (đang mở / tới hạn kiểm)", lambda: bao_cao_hanh_dong(goc, bay_gio, chi_can_chu_y=True))

    thu_muc_dt = ""

    def doi_thu() -> List[str]:
        nonlocal thu_muc_dt
        ds, thu_muc_dt = doi_thu_dang_no(goc, 8, 14, bay_gio)
        return ds or ["  (không thấy video đối thủ mới trong dữ liệu quét — tự đọc: {0})".format(thu_muc_dt)]

    phan("ĐỐI THỦ ĐANG NỔ (đăng ≤14 ngày, view cao nhất)", doi_thu)

    def viec() -> List[str]:
        # "lich" bỏ: `anh_bang` ở đây không hỏi Task Scheduler nên dòng "lịch tắt" luôn sai.
        return ["  - {0}".format(_cat(v.get("chu"), 150)) for v in (anh.get("viec") or []) if v.get("khoa") != "lich"][:6] or ["  (không có)"]

    phan("VIỆC ĐANG CHỜ CHỦ (cảnh báo)", viec)

    def de_xuat_het_han() -> List[str]:
        ds = [d for d in doc_hanh_dong(goc) if d.get("lenh") == "de-xuat"
              and (d.get("trang_thai") == "het_han" or _qua_han_de_xuat(d, _hom_nay(bay_gio)))
              and (_ngay(str(d.get("het_han_luc") or d.get("luc") or "")[:10]) or _dt.date.min) >= bay_gio.date() - _dt.timedelta(days=14)]
        return ["  - {0} [đề xuất {1}, chủ không xử lý {2} ngày → ĐÃ ĐÓNG] tự quyết lại: làm / bỏ / đề xuất lại"
                .format(_cat((d.get("tham_so") or {}).get("noi_dung"), 110), str(d.get("luc") or "")[:10],
                        NGAY_DE_XUAT_HET_HAN) for d in ds[-6:]] or ["  (không có)"]

    phan("ĐỀ XUẤT CỦA NÃO HẾT HẠN (chủ không xử lý — tự quyết lại)", de_xuat_het_han)

    def giam_doc_nho() -> List[str]:
        from .giam_doc import doc_viec_cho_nao  # noqa: PLC0415

        return ["  - [{0}] {1}".format(m.get("kenh") or "?", _cat(m.get("viec"), 200))
                for m in doc_viec_cho_nao(goc, bay_gio)[:8]] or ["  (không có)"]

    phan("GIÁM ĐỐC KÊNH NHỜ XEM (tự xem số bằng `xem`/chi-so rồi quyết; KHÔNG báo chủ)", giam_doc_nho)
    def mo_kenh_moi() -> List[str]:
        from . import mo_kenh as _mk  # noqa: PLC0415

        return _mk.tom_tat_nao(goc)

    phan("MỞ KÊNH MỚI (số do mã tính — luật số kênh; chỉ ĐỀ XUẤT, mở bằng `python -m core.mo_kenh`)", mo_kenh_moi)

    d.append("")
    d.append("== ĐỌC SÂU (chỉ đọc) ==")
    d.append("  CHANNEL/<kênh>/tu-hoc/{bang-diem.md,van.json} · ho-so-video/*.json · giam-doc/ · chi-so/ · kenh.yaml")
    d.append("  Đối thủ: CHANNEL/_NHOM/*/nghien-cuu/quet-kenh/*.json (mỗi tệp một kênh đối thủ), trang-chu-ai.json, kenh-ai.json")
    d.append("  Nhóm: CHANNEL/_NHOM/*/INSIGHT-CHON-CONTENT.md · Trí nhớ: nao/tri-nho/ · Nhật ký: nao/nhat-ky/")
    if len(d) > toi_da_dong:
        d = d[:toi_da_dong - 1] + ["… (cắt bớt cho gọn; đọc tệp ở trên để xem thêm)"]
    return "\n".join(d)


# ═══ LỆNH HÀNH ĐỘNG ═════════════════════════════════════════════════════════

def bai_hoc(goc: str, kenh: str, thao_tac: str, noi_dung: str = "", bay_gio: Optional[_dt.datetime] = None,
            du_doan: str = "", kiem_ngay: str = "", ly_do: str = "") -> Dict[str, Any]:
    """Sổ bài học qua `giam_doc.kham_nghiem.ap_delta` (nguồn "nao"). `cong`/`tru` không cần dự đoán."""
    from .giam_doc import kham_nghiem as kn  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    if not _kenh_ton_tai(goc, kenh):
        raise TuChoi("kênh “{0}” không tồn tại".format(kenh))
    if thao_tac not in ("them", "cong", "tru"):
        raise TuChoi("thao tác phải là them | cong <id> | tru <id>")
    noi_dung = (noi_dung or "").strip()
    if not noi_dung:
        raise TuChoi("thiếu nội dung (bài học cho `them`, id bài cho `cong`/`tru`)")
    if thao_tac == "them":
        if not re.search(r"\d", noi_dung):
            raise TuChoi("bài học phải có số / video_id làm bằng chứng (không có chữ số nào)")
        delta = [{"op": "them", "noi_dung": noi_dung}]
    else:
        delta = [{"op": thao_tac, "id": noi_dung}]
        if noi_dung not in {b["id"] for b in kn.doc_bai_hoc(goc, kenh) if b["trang_thai"] != "bo"}:
            raise TuChoi("không có bài “{0}” (hoặc đã bỏ) trong sổ kênh {1} — xem id ở `xem`".format(noi_dung, kenh))
    hom_nay = _hom_nay(bay_gio)
    kem = thao_tac != "them"
    # Kiểm hạn mức TRƯỚC khi ghi vào sổ (`them` tính vào hạn mức ngày; cộng/trừ thì không).
    hd = None
    if not kem:
        tao_thu = tao_hanh_dong(goc, "bai-hoc", {"kenh": kenh, "thao_tac": thao_tac, "noi_dung": noi_dung}, ly_do=ly_do,
                                du_doan=du_doan, kiem_ngay=kiem_ngay, bay_gio=bay_gio)
        hd = tao_thu
    kq = kn.ap_delta(goc, kenh, delta, "nao-{0}".format(hom_nay), "nao", bay_gio.replace(microsecond=0).isoformat(),
                     False, nguon="nao")
    if not any(kq.get(x) for x in ("cong", "tru", "them")):
        if hd:  # không ghi được vào sổ → không giữ hành động rỗng
            ds = [x for x in doc_hanh_dong(goc) if x.get("id") != hd["id"]]
            ghi_hanh_dong(goc, ds)
        raise TuChoi("sổ bài học bỏ qua thao tác (trùng bài đã gạch, hoặc hôm nay đã {0} bài này rồi)".format(thao_tac))
    if kem:
        hd = tao_hanh_dong(goc, "bai-hoc", {"kenh": kenh, "thao_tac": thao_tac, "noi_dung": noi_dung}, ly_do=ly_do,
                           bay_gio=bay_gio, khong_tinh=True)
    return hd


def cham(goc: str, *a: Any, **kw: Any) -> Any:
    with _khoa_hd(goc):
        return _cham_g(goc, *a, **kw)


def _cham_g(goc: str, id_: str, ket: str, ghi_chu: str) -> Dict[str, Any]:
    if ket not in ("dung", "sai"):
        raise TuChoi("kết quả chấm phải là dung hoặc sai")
    if not (ghi_chu or "").strip():
        raise TuChoi("thiếu lý do chấm (nêu số thật)")
    ds = doc_hanh_dong(goc)
    for d in ds:
        if d.get("id") == id_:
            if d.get("khong_tinh"):
                raise TuChoi("{0} là ghi cộng/trừ bài học, không có dự đoán để chấm".format(id_))
            if d.get("trang_thai") == "huy":
                raise TuChoi("{0} đã huỷ".format(id_))
            d["cham"], d["ghi_chu_cham"] = ket, ghi_chu.strip()
            d["cham_luc"] = _dt.datetime.now().replace(microsecond=0).isoformat()
            if d.get("trang_thai") == "mo":
                d["trang_thai"] = "xong"   # chấm rồi thì hết hiệu lực
            ghi_hanh_dong(goc, ds)
            return d
    raise TuChoi("không có hành động {0}".format(id_))


def huy(goc: str, *a: Any, **kw: Any) -> Any:
    with _khoa_hd(goc):
        return _huy_g(goc, *a, **kw)


def _huy_g(goc: str, id_: str) -> Dict[str, Any]:
    ds = doc_hanh_dong(goc)
    for d in ds:
        if d.get("id") == id_:
            if d.get("trang_thai") != "mo":
                raise TuChoi("{0} đang ở trạng thái {1}, chỉ huỷ được hành động đang mở".format(id_, d.get("trang_thai")))
            if d.get("lenh") == "bai-hoc":
                raise TuChoi("bài học đã ghi vào sổ — dùng `bai-hoc cong|tru` để chỉnh, không huỷ được")
            d["trang_thai"] = "huy"
            ghi_hanh_dong(goc, ds)
            return d
    raise TuChoi("không có hành động {0}".format(id_))


# ═══ PHIÊN ═══════════════════════════════════════════════════════════════════

def chuan_bi_thu_muc(goc: str = GOC) -> None:
    n = duong_nao(goc)
    for sub in ("tri-nho", "nhat-ky", "ky-nang"):
        os.makedirs(os.path.join(n, sub), exist_ok=True)
    tn = os.path.join(n, "tri-nho", "MEMORY.md")
    if not os.path.isfile(tn):
        _ghi_nguyen_tu(tn, DONG_GIOI_THIEU_TRI_NHO)


def lenh_phien(duong_claude: str, goc: str = GOC, mo_hinh: str = MO_HINH_PHIEN, so_luot: Optional[int] = SO_LUOT_TOI_DA) -> List[str]:
    """Dòng lệnh `claude` cho một phiên: headless, KHÔNG bypassPermissions (`dontAsk` = ngoài danh sách cho phép
    thì từ chối, không hỏi). Lời nhắc đi qua stdin (cờ nhiều giá trị không nuốt mất nó)."""
    from . import claude_code  # noqa: PLC0415

    co = claude_code.lenh_chay("", duong_claude or "claude", mo_hinh=mo_hinh, toan_quyen=False)[:-1]
    co = [x for x in co if x != "--include-partial-messages"]
    co += ["--permission-mode", "dontAsk", "--add-dir", goc, "--append-system-prompt", CHI_DAO_PHIEN]
    if so_luot:
        co += ["--max-turns", str(so_luot)]
    cho, cam = cong_cu(goc)
    co += ["--allowedTools", ",".join(cho), "--disallowedTools", ",".join(cam)]
    return co


def tim_claude(goc: str = GOC) -> str:
    from . import claude_code  # noqa: PLC0415

    duong = claude_code.tim_lenh("claude", goc)
    if duong:
        return duong
    mau = os.path.join(os.path.expanduser("~"), ".vscode", "extensions", "anthropic.claude-code-*", "resources",
                       "native-binary", "claude.exe")

    def khoa(p: str) -> Tuple[int, ...]:
        m = re.search(r"claude-code-([\d.]+)", p)
        return tuple(int(x) for x in m.group(1).split(".") if x.isdigit()) if m else (0,)

    ds = sorted(glob.glob(mau), key=khoa, reverse=True)
    return ds[0] if ds else ""


def moi_truong_phien(goc: str = GOC) -> Tuple[Dict[str, str], str]:
    """`(env, khoá để che log)`. Khoá/địa chỉ ví lấy từ `core.config` (không in ra đâu cả)."""
    from . import claude_code  # noqa: PLC0415
    from .config import load_config  # noqa: PLC0415

    cau = load_config(os.path.join(goc, "config.json"))
    khoa = (cau.api_key or "").strip()
    mt = claude_code.moi_truong(khoa, cau.base_url or "")
    mt["PYTHONPATH"] = goc + (os.pathsep + mt["PYTHONPATH"] if mt.get("PYTHONPATH") else "")
    mt["PYTHONIOENCODING"] = "utf-8"
    mt["PYTHONUTF8"] = "1"
    return mt, khoa


def _che(chu: str, khoa: str) -> str:
    if khoa and len(khoa) > 6:
        chu = chu.replace(khoa, "***")
    return re.sub(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9_\-\.]{12,})", "***", chu)


def _pid_song(pid: int) -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", "PID eq {0}".format(pid), "/NH"], capture_output=True, text=True,
                           timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return str(pid) in (r.stdout or "")
    except Exception:  # noqa: BLE001
        return False


def lay_khoa(goc: str = GOC) -> bool:
    """Khoá tệp chống chạy chồng. Khoá cũ (chết hoặc > 45 phút) thì giành lại."""
    duong = os.path.join(duong_nao(goc), ".khoa-phien")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                f.write(json.dumps({"pid": os.getpid(), "luc": time.time()}))
            return True
        except FileExistsError:
            try:
                with io.open(duong, encoding="utf-8") as f:
                    c = json.load(f)
            except (OSError, ValueError):
                c = {}
            tuoi = time.time() - float(c.get("luc") or 0)
            if tuoi < GIO_HET_GIO_PHIEN + 900 and int(c.get("pid") or 0) and _pid_song(int(c["pid"])):
                return False
            try:
                os.remove(duong)
            except OSError:
                return False
    return False


def tra_khoa(goc: str = GOC) -> None:
    try:
        os.remove(os.path.join(duong_nao(goc), ".khoa-phien"))
    except OSError:
        pass


def _da_xong_hom_nay(duong_log: str) -> Tuple[int, bool]:
    """(số lần đã bắt đầu, đã thành công) — đếm trong log ngày."""
    try:
        with io.open(duong_log, encoding="utf-8") as f:
            nd = f.read()
    except OSError:
        return 0, False
    return nd.count("=== BAT DAU PHIEN"), "KET QUA: thanh cong" in nd


def _tom_tat_cong_cu(ten: str, vao: Any) -> str:
    try:
        if isinstance(vao, dict):
            v = vao.get("command") or vao.get("file_path") or vao.get("path") or vao.get("pattern") or json.dumps(vao, ensure_ascii=False)
        else:
            v = vao
        return "[{0}] {1}".format(ten, _cat(v, 260))
    except Exception:  # noqa: BLE001
        return "[{0}]".format(ten)


def _chay_mot_lan(lenh: List[str], loi_nhac: str, goc: str, mt: Dict[str, str], khoa: str, ghi: Any) -> Dict[str, Any]:
    """Chạy tiến trình, đọc stream-json, ghi log đã che khoá. Trả `{ma, ket, usd, luot, giay, loi_cuoi}`."""
    kq: Dict[str, Any] = {"ma": -1, "ket": "", "usd": None, "luot": None, "giay": 0.0, "loi": "", "hang_cuoi": []}
    t0 = time.time()
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    tt = subprocess.Popen(lenh, cwd=duong_nao(goc), env=mt, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1, creationflags=co)
    het_gio = {"co": False}

    def giet() -> None:
        het_gio["co"] = True
        try:
            subprocess.run(["taskkill", "/PID", str(tt.pid), "/T", "/F"], capture_output=True, timeout=30, creationflags=co)
        except Exception:  # noqa: BLE001
            try:
                tt.kill()
            except Exception:  # noqa: BLE001
                pass

    dem = threading.Timer(GIO_HET_GIO_PHIEN, giet)
    dem.daemon = True
    dem.start()
    try:
        try:
            tt.stdin.write(loi_nhac)
            tt.stdin.close()
        except OSError:
            pass
        from . import claude_code  # noqa: PLC0415

        for dong in iter(tt.stdout.readline, ""):
            kq["hang_cuoi"] = (kq["hang_cuoi"] + [dong.strip()])[-6:]
            su = claude_code.doc_su_kien(dong)
            if su is None:
                continue
            loai = su.get("type")
            if loai == "assistant":
                for k in (su.get("message") or {}).get("content") or []:
                    if k.get("type") == "text" and (k.get("text") or "").strip():
                        ghi("[não] " + _cat(k["text"], 1800))
                    elif k.get("type") == "tool_use":
                        ghi(_tom_tat_cong_cu(k.get("name"), k.get("input")))
            elif loai == "user":
                for k in (su.get("message") or {}).get("content") or []:
                    if isinstance(k, dict) and k.get("type") == "tool_result":
                        nd = k.get("content")
                        nd = " ".join(x.get("text", "") for x in nd if isinstance(x, dict)) if isinstance(nd, list) else str(nd or "")
                        ghi("   → {0}{1}".format("LỖI " if k.get("is_error") else "", _cat(nd, 220)))
            elif loai == "result":
                kq["ket"] = str(su.get("result") or "")
                kq["usd"] = su.get("total_cost_usd")
                kq["luot"] = su.get("num_turns")
                kq["loi"] = "loi" if su.get("is_error") else ""
                kq["subtype"] = su.get("subtype")
        tt.wait()
        kq["ma"] = tt.returncode
    finally:
        dem.cancel()
        try:
            tt.stdout.close()
        except Exception:  # noqa: BLE001
            pass
    kq["giay"] = round(time.time() - t0, 1)
    kq["het_gio"] = het_gio["co"]
    return kq


def chay_phien(goc: str = GOC, ep: bool = False, thu: bool = False, bay_gio: Optional[_dt.datetime] = None) -> int:
    """Một phiên não. Mã thoát: 0 xong (hoặc đã có phiên hôm nay) · 1 hỏng · 3 đang có phiên khác."""
    bay_gio = bay_gio or _dt.datetime.now()
    hom_nay = _hom_nay(bay_gio)
    chuan_bi_thu_muc(goc)
    duong_log = os.path.join(duong_nao(goc), "nhat-ky", "phien-{0}.log".format(hom_nay))
    lan, xong = _da_xong_hom_nay(duong_log)
    if not ep and not thu and xong:
        print("Hôm nay đã có phiên thành công ({0}) — bỏ qua. Dùng --ep để chạy lại.".format(duong_log))
        return 0
    if not ep and not thu and lan >= LAN_THU_TOI_DA_MOI_NGAY:
        print("Hôm nay đã thử {0} lần mà chưa xong — dừng, xem {1}.".format(lan, duong_log))
        return 1
    duong = tim_claude(goc)
    if not duong:
        print("Không tìm thấy Claude Code (claude) trên máy.")
        return 1
    loi_nhac = CAU_HOI_PHIEN.format(hom_nay)
    lenh = lenh_phien(duong, goc)
    if thu:
        print(" ".join(lenh) + "\n(stdin) " + loi_nhac)
        return 0
    if not lay_khoa(goc):
        print("Đang có phiên khác chạy (khoá nao/.khoa-phien) — thoát.")
        return 3
    f = io.open(duong_log, "a", encoding="utf-8", newline="\n")
    mt, khoa = moi_truong_phien(goc)

    def ghi(chu: str) -> None:
        f.write(_che("{0} {1}\n".format(time.strftime("%H:%M:%S"), chu), khoa))
        f.flush()

    try:
        ghi("=== BAT DAU PHIEN {0} · model {1} · tối đa {2} lượt · hết giờ {3} phút".format(
            hom_nay, MO_HINH_PHIEN, SO_LUOT_TOI_DA, GIO_HET_GIO_PHIEN // 60))
        ghi("lệnh: " + " ".join(lenh[:1] + lenh[1:]))
        kq = _chay_mot_lan(lenh, loi_nhac, goc, mt, khoa, ghi)
        txt = " ".join(kq["hang_cuoi"]).lower()
        if kq["ma"] != 0 and not kq["ket"] and "max-turns" in txt and ("unknown" in txt or "unrecognized" in txt):
            ghi("bản claude không nhận --max-turns — chạy lại không có cờ này")
            kq = _chay_mot_lan(lenh_phien(duong, goc, so_luot=None), loi_nhac, goc, mt, khoa, ghi)
        nk = os.path.join(duong_nao(goc), "nhat-ky", hom_nay + ".md")
        thanh_cong = kq["ma"] == 0 and not kq["loi"] and not kq.get("het_gio") and os.path.isfile(nk)   # phải có nhật ký
        ghi("KET QUA: {0} · mã {1} · {2} lượt · {3}s · chi phí ước tính {4} USD{5}".format(
            "thanh cong" if thanh_cong else "that bai", kq["ma"], kq["luot"], kq["giay"],
            kq["usd"] if kq["usd"] is not None else "?", " · HẾT GIỜ" if kq.get("het_gio") else ""))
        if not thanh_cong:
            ghi("đuôi đầu ra: " + _cat(" | ".join(kq["hang_cuoi"]), 600))
        if kq["ket"]:
            ghi("tóm tắt của não: " + _cat(kq["ket"], 2000))
        ghi("nhật ký ngày: {0}".format("có" if os.path.isfile(nk) else "KHÔNG THẤY (não không ghi nhật ký)"))
        try:
            with io.open(os.path.join(duong_nao(goc), "nhat-ky", "chi-phi.jsonl"), "a", encoding="utf-8", newline="\n") as c:
                c.write(json.dumps({"ngay": hom_nay, "usd_uoc_tinh": kq["usd"], "luot": kq["luot"], "giay": kq["giay"],
                                    "model": MO_HINH_PHIEN, "thanh_cong": thanh_cong}, ensure_ascii=False) + "\n")
        except OSError:
            pass
        print("Phiên {0}: {1} lượt, {2}s, ~{3} USD. Log: {4}".format("xong" if thanh_cong else "HỎNG", kq["luot"], kq["giay"],
                                                                     kq["usd"], duong_log))
        return 0 if thanh_cong else 1
    except Exception as loi:  # noqa: BLE001
        ghi("KET QUA: that bai · ngoại lệ {0}: {1}".format(type(loi).__name__, _cat(loi, 300)))
        print("Phiên hỏng: {0}".format(_cat(loi, 200)))
        return 1
    finally:
        f.close()
        tra_khoa(goc)


# ═══ CLI ═════════════════════════════════════════════════════════════════════

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m core.nao", description="Bộ não của kênh — CLI an toàn.")
    s = p.add_subparsers(dest="lenh", required=True)
    s.add_parser("xem", help="báo cáo gọn tình hình")
    s.add_parser("xem-hanh-dong", help="mọi hành động của não + trạng thái chấm")
    b = s.add_parser("bang-diem", help="bảng điểm tự học một kênh")
    b.add_argument("kenh")

    def them_chung(x: argparse.ArgumentParser, kiem: bool = True) -> None:
        x.add_argument("--du-doan", default="", help="dự đoán đo được")
        x.add_argument("--kiem-ngay", default="", help="YYYY-MM-DD ngày kiểm")
        x.add_argument("--ly-do", default="", help="lý do (có số)")

    t = s.add_parser("thu", help="ép N video thử một lựa chọn")
    t.add_argument("--kenh", required=True)
    t.add_argument("--truc", required=True)
    t.add_argument("--gia-tri", required=True)
    t.add_argument("--so-video", type=int, required=True)
    them_chung(t)
    tr = s.add_parser("tranh", help="tạm tránh một lựa chọn N ngày")
    tr.add_argument("--kenh", required=True)
    tr.add_argument("--truc", required=True)
    tr.add_argument("--gia-tri", required=True)
    tr.add_argument("--ngay", type=int, required=True)
    them_chung(tr)
    bh = s.add_parser("bai-hoc", help="sổ bài học")
    bh.add_argument("--kenh", required=True)
    bh.add_argument("thao_tac", choices=["them", "cong", "tru"])
    bh.add_argument("noi_dung", help="bài học (them) hoặc id bài (cong/tru)")
    them_chung(bh)
    u = s.add_parser("uu-tien-nguon", help="đề cử 1 video đối thủ cho lần chọn content tới")
    u.add_argument("--kenh", required=True)
    u.add_argument("--link", required=True)
    them_chung(u)
    dx = s.add_parser("de-xuat", help="việc lớn chờ chủ duyệt")
    dx.add_argument("noi_dung")
    dx.add_argument("--kenh", default="")
    them_chung(dx)
    c = s.add_parser("cham", help="tự chấm hành động cũ")
    c.add_argument("id")
    c.add_argument("ket", choices=["dung", "sai"])
    c.add_argument("ghi_chu")
    h = s.add_parser("huy", help="gỡ hành động đang mở")
    h.add_argument("id")
    ph = s.add_parser("phien", help="chạy một phiên não (claude headless)")
    ph.add_argument("--ep", action="store_true", help="bỏ giới hạn một phiên/ngày")
    ph.add_argument("--thu", action="store_true", help="chỉ in lệnh, không chạy")
    return p


def chay_lenh(ns: argparse.Namespace, goc: str = GOC, bay_gio: Optional[_dt.datetime] = None) -> str:
    """Thực thi một lệnh đã parse, trả chữ để in. Ném `TuChoi` khi vượt quyền."""
    l = ns.lenh
    if l == "xem":
        return bao_cao(goc, bay_gio)
    if l == "xem-hanh-dong":
        return "\n".join(bao_cao_hanh_dong(goc, bay_gio))
    if l == "bang-diem":
        if not _kenh_ton_tai(goc, ns.kenh):
            raise TuChoi("kênh “{0}” không tồn tại".format(ns.kenh))
        return "\n".join(["BẢNG ĐIỂM — {0}".format(ns.kenh)] + dong_bang_diem(goc, ns.kenh))
    chung = dict(ly_do=getattr(ns, "ly_do", ""), du_doan=getattr(ns, "du_doan", ""),
                 kiem_ngay=getattr(ns, "kiem_ngay", ""), bay_gio=bay_gio)
    if l == "thu":
        hd = tao_hanh_dong(goc, "thu", {"kenh": ns.kenh, "truc": ns.truc, "gia_tri": ns.gia_tri.strip(),
                                        "so_video": ns.so_video}, **chung)
    elif l == "tranh":
        hd = tao_hanh_dong(goc, "tranh", {"kenh": ns.kenh, "truc": ns.truc, "gia_tri": ns.gia_tri.strip(),
                                          "ngay": ns.ngay}, **chung)
    elif l == "bai-hoc":
        hd = bai_hoc(goc, ns.kenh, ns.thao_tac, ns.noi_dung, bay_gio, ns.du_doan, ns.kiem_ngay, ns.ly_do)
    elif l == "uu-tien-nguon":
        hd = tao_hanh_dong(goc, "uu-tien-nguon", {"kenh": ns.kenh, "link": ns.link.strip()}, **chung)
    elif l == "de-xuat":
        hd = tao_hanh_dong(goc, "de-xuat", {"kenh": ns.kenh, "noi_dung": ns.noi_dung.strip()}, **chung)
    elif l == "cham":
        hd = cham(goc, ns.id, ns.ket, ns.ghi_chu)
    elif l == "huy":
        hd = huy(goc, ns.id)
    else:
        raise TuChoi("lệnh lạ")
    return "ĐÃ GHI: " + dong_hanh_dong(hd)


def main(argv: Optional[List[str]] = None, goc: str = GOC) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ns = _parser().parse_args(argv)
    if ns.lenh == "phien":
        return chay_phien(goc, ep=ns.ep, thu=ns.thu)
    try:
        print(chay_lenh(ns, goc))
        return 0
    except TuChoi as loi:
        print("TỪ CHỐI: {0}".format(loi))
        return 2


if __name__ == "__main__":
    sys.exit(main())
