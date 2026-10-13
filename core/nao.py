"""BỘ NÃO — một agent Claude Code chạy mỗi sáng, nhìn toàn cảnh, nhớ, tự chấm mình và chỉnh hướng (03/10/2026).

    python -m core.nao <lệnh>

Tư tưởng: dây chuyền (tự chọn → sản xuất → đăng → đo → tự học) đã tự chạy. Bộ não làm thứ nó KHÔNG làm được:
đọc cả bức tranh, suy nghĩ có giả thuyết cạnh tranh, ghi nhớ giữa các phiên, và đẩy dây chuyền một chút
(thử / tránh / đề cử nguồn / bài học / đề xuất). Nó KHÔNG sửa mã, KHÔNG đăng, KHÔNG tiêu tiền ngoài phiên của nó.

Hai nửa trong một tệp:
  1. CLI an toàn (`xem`, `thu`, `tranh`, `bai-hoc`, `uu-tien-nguon`, `de-xuat`, `cham`, `huy`) — bộ não chỉ có CỬA này.
     Giới hạn kiểm BẰNG MÃ; vượt thì từ chối kèm lý do. Quyền co lại khi dự đoán của chính nó hay sai.
  2. `phien` — dựng và chạy `claude` không giao diện (qua `core.claude_code`), thư mục làm việc `nao/`,
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
#: Model của phiên khi đi ví ShopAPI. Trên thuê bao Claude Max (12/10/2026) phiên lấy bậc ĐANG MỞ của thang chung
#: `core.viet_max.thang_mo_hinh` (đầu thang mặc định claude-opus-5-5, chủ dự án chọn) — xem `chay_phien`.
MO_HINH_PHIEN = "claude-fable-5"
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
    "(4) Làm ít mà chắc; mẫu n<3 thì nói rõ là chưa chắc và đừng dùng làm lý do duy nhất của một hành động. "
    "(5) Mục VIỆC BẮT BUỘC là CHƯƠNG TRÌNH (a)–(f): với MỖI phần ghi một quyết định có số (n, ngày kiểm) — lệnh in "
    "sẵn chỉ là gợi ý của máy, chạy khi bạn đồng ý, sửa khi cần, bỏ thì ghi lý do; việc chỉ người làm được thì `de-xuat`.")
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
    """`(số đúng, số đã chấm)` — chỉ tính hành động có dự đoán (không tính ghi cộng/trừ, không tính đề cử MÁY tạo —
    `tu_dong`, vd radar thị trường: phòng thí nghiệm đo chúng, không phải quyền của não)."""
    da = [d for d in ds if d.get("cham") in ("dung", "sai") and not d.get("khong_tinh") and not d.get("tu_dong")]
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
    # 12/10/2026 — RADAR NỔ (`core.nao_chuong_trinh`): `uu-tien-nguon --radar <video>` chỉ hợp lệ khi MÃ xác nhận video
    # đang trên radar của kênh; không tính hạn mức ngày, ≤ `SO_NGUON_RADAR` nguồn mỗi video, hạn vào sản xuất 48 giờ.
    radar = str(tham_so.get("radar") or "").strip() if lenh == "uu-tien-nguon" else ""
    ly_radar = ""
    if radar:
        from . import nao_chuong_trinh  # noqa: PLC0415

        ok_r, ly_radar = nao_chuong_trinh.la_radar(goc, str(tham_so.get("kenh") or ""), radar, bay_gio)
        if not ok_r:
            raise TuChoi(ly_radar)
        da_ep = sum(1 for d in ds if d.get("lenh") == "uu-tien-nguon" and d.get("trang_thai") != "huy"
                    and (d.get("tham_so") or {}).get("radar") == radar
                    and (d.get("tham_so") or {}).get("kenh") == tham_so.get("kenh"))
        if da_ep >= nao_chuong_trinh.SO_NGUON_RADAR:
            raise TuChoi("video {0} đã có {1} nguồn radar — tối đa {2}".format(
                radar, da_ep, nao_chuong_trinh.SO_NGUON_RADAR))
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
                      and not d.get("khong_tinh") and not d.get("ngoai_han_muc") and d.get("trang_thai") != "huy")
        tran = han_muc_ngay(ds)
        if da_dung >= tran and not radar:
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
    if radar:
        hd["ngoai_han_muc"] = True
        hd["tham_so"]["han_san_xuat"] = (bay_gio + _dt.timedelta(hours=GIO_RADAR_SAN_XUAT)).replace(
            microsecond=0).isoformat()
        hd["tham_so"]["radar_ly_do"] = ly_radar
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
        elif _radar_qua_han(d, bay_gio or _dt.datetime.now()):
            d["trang_thai"] = "xong"
            d["khong_tinh"] = True
            d["ghi_chu_cham"] = ("radar: quá {0} giờ chưa vào sản xuất (hạn {1}) — không có hiệu lực, không tính "
                                 "điểm").format(GIO_RADAR_SAN_XUAT, str((d.get("tham_so") or {}).get("han_san_xuat"))[:16])
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
    `["<mã gói>: kết quả THẮNG/trung bình/trượt/chờ (thước chung), CTR … — hiển thị @48h …"]`. Không đọc được → []."""
    try:
        from . import tu_hoc  # noqa: PLC0415
        from .chien_luoc import ket_qua  # noqa: PLC0415

        van = tu_hoc.doc_van(goc, kenh)
        hs_ds = ket_qua.ho_so_theo_goi(goc, kenh)
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, "nao.ket_qua_goi", loi, kenh)
        return []
    chu = {"thang": "THẮNG", "trung_binh": "trung bình", "truot": "trượt"}
    ra = []
    for ma in goi or []:
        v, hs = van.get(ma) or {}, hs_ds.get(ma) or {}
        m = tu_hoc._moc_do_duoc(hs)  # noqa: SLF001
        # Kết quả = THƯỚC CHUNG (`core.thuoc_thang`: phân vị cùng tuổi, phán ≥ 96h) — không còn "thắng @48h".
        ket = chu.get(v.get("ket"), "chờ")
        if v.get("ket"):
            ket += " (phân vị {0} @{1}h)".format(_f(v.get("ket_pv")), _f(v.get("ket_tuoi")))
        elif v.get("ket_som") is not None:
            ket += " (tín hiệu sớm: phân vị {0})".format(_f(v.get("ket_som")))
        ra.append("{0}: kết quả {1}, CTR-so-kênh {2} — hiển thị @48h {3}, CTR {4}".format(
            ma, ket, chu.get(v.get("ket_ctr"), "chờ"),
            _f(m.get("impressions")) + (" (~{0})".format(m.get("moc_dung")) if m.get("xap_xi") else ""),
            _f(m.get("ctr"), 2, "%")))
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


#: Lý do cổng V7 mà nguồn bộ não đề cử vẫn được ÉP qua (12/10/2026): các cổng MỀM — trên số của ta chúng loại cả video
#: thắng (nguồn < sàn view, kênh nguồn trung vị thấp, bảng đề xuất mỏng). Cổng cứng (đã làm, lạc ngách, kênh bỏ, độ
#: dài ngoài khuôn, nhắm tệp khác) vẫn chặn — ép chọn chỉ bỏ qua XẾP HẠNG, không bỏ qua chất lượng.
CONG_MEM_EP = ("nguồn quá nhỏ", "kênh nguồn quá yếu", "bảng đề xuất", "không có trong bảng đề xuất",
               "cổng bảng đề xuất")
#: Đề cử đã được CHỌN vào một lượt mà quá ngần này ngày chưa bàn giao → đóng (không tính), não tự quyết lại.
NGAY_CHO_BAN_GIAO = 10
#: Đề cử RADAR (`uu-tien-nguon --radar`) phải vào sản xuất (được chọn) trong ngần này giờ — quá hạn tự đóng không tính.
GIO_RADAR_SAN_XUAT = 48


def _radar_qua_han(d: Dict[str, Any], bay_gio: _dt.datetime) -> bool:
    """Đề cử radar (của ta `radar` hoặc THỊ TRƯỜNG `radar_thi_truong`) còn mở, CHƯA được chọn vào lượt nào, đã quá
    `han_san_xuat`."""
    ts = d.get("tham_so") or {}
    han = str(ts.get("han_san_xuat") or "")
    return bool(d.get("lenh") == "uu-tien-nguon" and d.get("trang_thai") == "mo"
                and (ts.get("radar") or ts.get("radar_thi_truong")) and han
                and not ts.get("chon_luc") and han[:19] < bay_gio.replace(microsecond=0).isoformat())


#: Đề cử RADAR THỊ TRƯỜNG (`core.radar_dot_bien`) do MÁY tạo: tối đa ngần này mỗi kênh mỗi ngày.
RADAR_TT_MOI_KENH_NGAY = 1
#: Giả thuyết phòng thí nghiệm được ghi công khi nguồn radar thị trường vào sản xuất (`chia_khe.chot_nguon`).
GT_RADAR = "H-RADAR"


def tao_ep_chon_radar(goc: str, kenh: str, link: str, ma: str, *, ly_do: str, du_doan: str,
                      so_lieu: Optional[Dict[str, Any]] = None, nguon_dong: Optional[Dict[str, Any]] = None,
                      toi_da_ngay: int = RADAR_TT_MOI_KENH_NGAY,
                      bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """ĐƯỜNG ÉP CHỌN của RADAR THỊ TRƯỜNG (12/10/2026): video đối thủ nổ cực mạnh → một `uu-tien-nguon` MÁY tạo
    (`tu_dong: "radar"`), có `radar_thi_truong` = mã video, phải vào sản xuất ≤ `GIO_RADAR_SAN_XUAT` giờ (quá hạn tự
    đóng không tính). Kiểm BẰNG MÃ: kênh có thật, link http, mã 11 ký tự, ≤ `toi_da_ngay` đề cử radar thị trường mỗi
    kênh mỗi ngày, không trùng đề cử đang mở/đã làm của bất kỳ kênh nào. Ngoài hạn mức ngày của não, không vào tỉ lệ
    đúng của não. Ném `TuChoi` kèm lý do."""
    with _khoa_hd(goc):
        bay_gio = bay_gio or _dt.datetime.now()
        hom = _hom_nay(bay_gio)
        ds = doc_hanh_dong(goc)
        don_het_han(goc, ds, bay_gio)
        if not _kenh_ton_tai(goc, kenh):
            raise TuChoi("kênh “{0}” không tồn tại".format(kenh))
        if not re.match(r"^https?://", str(link or "")):
            raise TuChoi("link phải là địa chỉ http(s) của video đối thủ")
        if not re.match(r"^[\w-]{11}$", str(ma or "")):
            raise TuChoi("mã video không hợp lệ")
        if len((ly_do or "").strip()) < 10 or len((du_doan or "").strip()) < 10:
            raise TuChoi("thiếu lý do / dự đoán có số")
        da = [d for d in ds if d.get("lenh") == "uu-tien-nguon" and (d.get("tham_so") or {}).get("radar_thi_truong")
              and (d.get("tham_so") or {}).get("kenh") == kenh and str(d.get("luc") or "")[:10] == hom
              and d.get("trang_thai") != "huy"]
        if len(da) >= max(1, int(toi_da_ngay)):
            raise TuChoi("{0} đã có {1} đề cử radar thị trường hôm nay (trần {2})".format(kenh, len(da), toi_da_ngay))
        khoa = _khoa_link(link)
        for d in ds:
            ts = d.get("tham_so") or {}
            if d.get("lenh") == "uu-tien-nguon" and _khoa_link(ts.get("link")) == khoa and d.get("trang_thai") == "mo":
                raise TuChoi("nguồn đã có đề cử đang mở {0} cho {1}".format(d.get("id"), ts.get("kenh")))
        n_id = 1 + max([int(m.group(1)) for d in ds for m in [re.match(r"^n(\d+)$", str(d.get("id") or ""))] if m]
                       or [0])
        hd = {"id": "n{0:03d}".format(n_id), "luc": bay_gio.replace(microsecond=0).isoformat(), "lenh": "uu-tien-nguon",
              "tham_so": {"kenh": kenh, "link": str(link), "radar_thi_truong": str(ma),
                          "han_san_xuat": (bay_gio + _dt.timedelta(hours=GIO_RADAR_SAN_XUAT)).replace(
                              microsecond=0).isoformat(),
                          "radar_so": dict(so_lieu or {}), "nguon_dong": dict(nguon_dong or {})},
              "ly_do": str(ly_do).strip()[:600], "du_doan": str(du_doan).strip()[:300],
              "kiem_ngay": (bay_gio.date() + _dt.timedelta(days=6)).isoformat(), "trang_thai": "mo",
              "cham": None, "ghi_chu_cham": "", "ngoai_han_muc": True, "tu_dong": "radar"}
        ds.append(hd)
        ghi_hanh_dong(goc, ds)
        return hd


def _gan_radar(u: Dict[str, Any], hd: Dict[str, Any]) -> Dict[str, Any]:
    """Dòng ứng viên của một đề cử RADAR THỊ TRƯỜNG: ghi công phòng thí nghiệm cho `GT_RADAR` (`chia_khe.chot_nguon`
    giữ công này) + số đo radar để tra."""
    ts = hd.get("tham_so") or {}
    so = dict(ts.get("radar_so") or {})
    u["radar_thi_truong"] = {"id": hd.get("id"), "ma": ts.get("radar_thi_truong"), "boi": so.get("boi"),
                             "muc": so.get("muc"), "tuoi_gio": so.get("tuoi_gio"), "ky_vong": so.get("ky_vong")}
    u["gia_thuyet_radar"] = GT_RADAR
    u["tin_hieu"] = dict(u.get("tin_hieu") or {}, radar_thi_truong=hd.get("id"))
    return u


def _dong_radar(hd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Dòng chuẩn dựng từ `nguon_dong` của đề cử radar thị trường khi video CHƯA có trong sổ content của kênh (radar
    thấy nó ở sổ kênh anh em) — để nguồn nổ vào sản xuất ngay lượt kế, không đợi lượt nghiên cứu sau."""
    ts = hd.get("tham_so") or {}
    n = ts.get("nguon_dong") or {}
    ma, link = str(n.get("ma") or ts.get("radar_thi_truong") or ""), str(n.get("link") or ts.get("link") or "")
    if not ma or not link:
        return None
    so = ts.get("radar_so") or {}
    return {"nguon": "radar", "cong_thuc": "radar", "tham_do": False, "ma": ma, "link": link,
            "tieu_de": str(n.get("tieu_de") or ""), "kenh": str(n.get("kenh") or ""), "diem": 0.0, "loai": "RADAR",
            "diem_cum": 0.0, "thua_huong": "", "cum": list(n.get("cum") or []), "view": float(n.get("view") or 0),
            "vuot": n.get("boi"), "dai_giay": n.get("dai_giay"), "hang_v7": 999, "dot_bien": n.get("boi"),
            "tuoi_gio": n.get("tuoi_gio"),
            "ly_do": ["radar thị trường: ×{0} kỳ vọng ở {1}h ({2} view; nguồn ở sổ kênh anh em)".format(
                so.get("boi"), so.get("tuoi_gio"), so.get("view"))]}


def ep_chon(nc: Any, ds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ĐƯỜNG ÉP CHỌN (12/10/2026, `workspace/chan-doan/nao-vong-hoc-2026-10-12.md` #6): đề cử còn mở của kênh mà bảng
    trộn `ds` KHÔNG có (ngoài top hạng V7 / bị cổng MỀM) → tra trong bảng V7 ĐẦY ĐỦ (`nc._kq_v7`, chưa có thì chấm
    lại — chỉ đọc đĩa) và NỐI vào cuối `ds` (qua `nc.loc`: trùng đã làm/đang giữ thì vẫn bị bỏ); `ap_uu_tien` sau đó
    đưa nó lên đầu. Nguồn không có trong sổ content hoặc vướng cổng cứng → chỉ log lý do. Không ghi đĩa (trạm
    `/loi-thoai/can-lay` cũng gọi đường này — để trình duyệt hút đúng lời thoại của nguồn bị ép). Hỏng → `ds`."""
    try:
        mo = _de_cu_mo(nc.goc, nc.ma_kenh)
    except Exception:  # noqa: BLE001
        return ds
    if not mo:
        return ds
    co = {_khoa_link(d.get("link")) for d in ds} | {str(d.get("ma") or "") for d in ds}
    thieu = [d for d in mo if _khoa_link((d.get("tham_so") or {}).get("link")) not in co]
    if not thieu:
        return ds
    from . import cong_thuc_v7 as v7  # noqa: PLC0415
    from . import doi_thu_kenh as so  # noqa: PLC0415
    from .chien_luoc import v7 as ct_v7  # noqa: PLC0415

    kq = getattr(nc, "_kq_v7", None)
    if kq is None:
        try:
            kq = (getattr(nc, "cham_v7", None) or v7.cham)(nc.goc, nc.ma_kenh)
            nc._kq_v7 = kq  # noqa: SLF001
        except Exception as loi:  # noqa: BLE001
            nc.ghi("  [bộ não] không chấm được bảng V7 để ép đề cử ({0}).".format(str(loi)[:100]))
            return ds
    bang: Dict[str, Tuple[Any, str]] = {}
    for d in getattr(kq, "ung_vien", None) or []:
        bang[str(getattr(d, "ma", "") or "")] = (d, "")
    for d in getattr(kq, "bi_loai", None) or []:
        bang.setdefault(str(getattr(d, "ma", "") or ""), (d, str(getattr(d, "bi_loai", "") or "")))
    them: List[Dict[str, Any]] = []
    for hd in thieu:
        khoa = _khoa_link((hd.get("tham_so") or {}).get("link"))
        la_radar_tt = bool((hd.get("tham_so") or {}).get("radar_thi_truong"))
        if khoa in (getattr(nc, "loai_tru", None) or ()):
            nc.ghi("  [bộ não] đề cử {0}: nguồn đã làm / đang được kênh anh em giữ — không ép.".format(hd.get("id")))
            continue
        x = bang.get(khoa)
        if x is None and la_radar_tt:
            # Radar thị trường thấy video ở sổ của kênh ANH EM — dựng dòng từ số đo đã ghi trong đề cử (cổng
            # chất lượng phía sau vẫn chạy: biên tập phủ quyết, trùng ý, kho lời thoại, giữ nguồn nhóm).
            u = _dong_radar(hd)
            if u is not None:
                u.update(tin_hieu={"ep_chon_nao": hd.get("id")}, ep_chon=True)
                u["ly_do"] = list(u.get("ly_do") or []) + ["RADAR THỊ TRƯỜNG ÉP CHỌN {0}: {1}".format(
                    hd.get("id"), (hd.get("ly_do") or "")[:200])]
                them.append(_gan_radar(u, hd))
                continue
        if x is None:
            nc.ghi("  [bộ não] đề cử {0}: nguồn chưa có trong sổ content của kênh — không ép được (cần quét/thêm vào "
                   "hộp thư trước).".format(hd.get("id")))
            continue
        d, ly = x
        if ly and not any(m in ly for m in CONG_MEM_EP):
            nc.ghi("  [bộ não] đề cử {0}: vướng cổng chất lượng “{1}” — không ép.".format(hd.get("id"), ly[:80]))
            continue
        hang = next((i + 1 for i, u in enumerate(getattr(kq, "ung_vien", None) or [])
                     if str(getattr(u, "ma", "") or "") == khoa), 0)
        u = ct_v7._dong(d, v7, so, hang or 999)
        u.update(cong_thuc="v7", tham_do=False, tin_hieu={"ep_chon_nao": hd.get("id")}, ep_chon=True)
        u["ly_do"] = list(u.get("ly_do") or []) + ["{0} ÉP CHỌN {1}{2}: {3}".format(
            "RADAR THỊ TRƯỜNG" if la_radar_tt else "bộ não", hd.get("id"),
            " (bỏ qua cổng mềm “{0}”)".format(ly[:60]) if ly else
            " (hạng V7 {0}, ngoài top)".format(hang) if hang else "", (hd.get("ly_do") or "")[:160])]
        them.append(_gan_radar(u, hd) if la_radar_tt else u)
    if not them:
        return ds
    them = nc.loc(them)
    for u in them:
        nc.ghi("  [bộ não] ép chọn: nối “{0}” vào bảng (đề cử {1}).".format(
            str(u.get("tieu_de") or "")[:60], (u.get("tin_hieu") or {}).get("ep_chon_nao")))
    return list(ds) + them


def ap_uu_tien(goc: str, kenh: str, ds: List[Dict[str, Any]], log: Any = None) -> List[Dict[str, Any]]:
    """Ứng viên có link được bộ não đề cử → cộng điểm mạnh và đưa lên đầu bảng, gắn `bo_nao` (lý do) + `ep_chon`
    (12/10/2026: dòng ép chọn được GHIM — biên tập AI chỉ được phủ quyết, cửa kho lời thoại không đổi nó, kiểm trùng ý
    không loại vì gần video thắng của chính kênh; xem `tu_chay._chon_nguon_goc`). Link không có trong bảng thì không
    làm gì ở đây (`ep_chon` của bộ điều phối đã thử nối nó vào). Hỏng → trả `ds` nguyên."""
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
            u["bo_nao"] = d.get("ly_do") or "đề cử của bộ não"
            u["ep_chon"] = True
            u["de_cu_nao"] = d.get("id")
            if (d.get("tham_so") or {}).get("radar_thi_truong"):
                u = _gan_radar(u, d)
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


def _dung_xong_de_cu_g(goc: str, kenh: str, chon: str = "", bay_gio: Optional[_dt.datetime] = None) -> int:
    """Lần chọn content thật đã chạy (`chon` = link nguồn lượt này lấy) → cập nhật đề cử mở của kênh.

    12/10/2026 (`workspace/chan-doan/nao-vong-hoc-2026-10-12.md` #6): trước đây đề cử CÓ MẶT trong bảng là `xong` ngay
    — 3 đề cử có mặt, bị biên tập AI xếp xuống, lượt chọn nguồn khác mà vẫn ghi đã dùng. Giờ CHỈ `ghi_ban_giao` (gói
    bàn giao dùng ĐÚNG link) mới đóng `xong`. Ở đây:
      * link == `chon` → ghi `chon_luc` (đang sản xuất), vẫn mở chờ bàn giao; quá `NGAY_CHO_BAN_GIAO` ngày không bàn
        giao → đóng `khong_tinh`;
      * có trong bảng mà lượt chọn nguồn khác (bị phủ quyết / trùng ý) → đếm `lan_bo_qua`; vắng khỏi bảng → đếm
        `lan_vang`; mỗi loại tới `DE_CU_VANG_TOI_DA` lượt thì đóng `khong_tinh` kèm lý do để não tự quyết lại."""
    try:
        ds = doc_hanh_dong(goc)
        thay = _DE_CU_THAY.pop(kenh, set())
        n = 0
        bg = bay_gio or _dt.datetime.now()
        luc = bg.replace(microsecond=0).isoformat()
        khoa_chon = _khoa_link(chon) if chon else ""
        for d in ds:
            if d.get("lenh") == "uu-tien-nguon" and d.get("trang_thai") == "mo" and (d.get("tham_so") or {}).get("kenh") == kenh:
                ts = d.setdefault("tham_so", {})
                if khoa_chon and _khoa_link(ts.get("link")) == khoa_chon:
                    ts["chon_luc"] = luc
                    ts["lan_chon"] = int(ts.get("lan_chon") or 0) + 1
                    n += 1
                    continue
                if ts.get("chon_luc"):
                    try:
                        cho = (bg - _dt.datetime.fromisoformat(str(ts["chon_luc"]))).days
                    except (TypeError, ValueError):
                        cho = 0
                    if cho <= NGAY_CHO_BAN_GIAO:
                        continue  # đang sản xuất (nguồn nằm trong "đã làm" nên vắng khỏi bảng) — chờ bàn giao
                    d["trang_thai"] = "xong"
                    d["khong_tinh"] = True
                    d["ghi_chu_cham"] = ("đã chọn {0} nhưng {1} ngày chưa bàn giao được video — không có hiệu lực, "
                                         "không tính điểm").format(str(ts["chon_luc"])[:10], cho)
                    n += 1
                    continue
                if _radar_qua_han(d, bg):
                    d["trang_thai"] = "xong"
                    d["khong_tinh"] = True
                    d["ghi_chu_cham"] = ("radar: quá {0} giờ chưa vào sản xuất — không có hiệu lực, không tính "
                                         "điểm").format(GIO_RADAR_SAN_XUAT)
                    n += 1
                    continue
                if d.get("id") in thay:
                    ts["lan_bo_qua"] = int(ts.get("lan_bo_qua") or 0) + 1
                    ts["bo_qua_luc"] = luc
                    if ts["lan_bo_qua"] >= DE_CU_VANG_TOI_DA:
                        d["trang_thai"] = "xong"
                        d["khong_tinh"] = True
                        d["ghi_chu_cham"] = ("có trong bảng ứng viên nhưng không được chọn {0} lượt (biên tập phủ "
                                             "quyết / trùng ý / thiếu lời thoại) — không có hiệu lực, không tính "
                                             "điểm").format(ts["lan_bo_qua"])
                    n += 1
                    continue
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


def ghi_ban_giao(goc: str, kenh: str, ma_goi: str, link: str, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Gói `ma_goi` vừa BÀN GIAO với nguồn `link` (gọi từ `tu_chay` ngay sau bàn giao) → mọi đề cử `uu-tien-nguon` còn
    mở của kênh có ĐÚNG link ấy thành `xong`, ghi `tham_so.goi` (để `xem` in "n0xx → <mã gói> → kết quả"). Trả id các
    đề cử vừa đóng. Hỏng → [] (có cảnh báo), không ném."""
    if not (ma_goi and link):
        return []
    try:
        with _khoa_hd(goc):
            ds = doc_hanh_dong(goc)
            khoa = _khoa_link(link)
            luc = (bay_gio or _dt.datetime.now()).replace(microsecond=0).isoformat()
            ra: List[str] = []
            for d in ds:
                ts = d.get("tham_so") or {}
                if (d.get("lenh") != "uu-tien-nguon" or d.get("trang_thai") != "mo" or ts.get("kenh") != kenh
                        or _khoa_link(ts.get("link")) != khoa):
                    continue
                if ma_goi not in (ts.get("goi") or []):
                    ts["goi"] = list(ts.get("goi") or []) + [ma_goi]
                ts["da_dung_luc"] = luc
                d["tham_so"] = ts
                d["trang_thai"] = "xong"
                ra.append(str(d.get("id")))
            if ra:
                ghi_hanh_dong(goc, ds)
            return ra
    except Exception as loi:  # noqa: BLE001
        _canh_bao(goc, "nao.ghi_ban_giao", loi, kenh)
        return []


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
           "uu-tien-nguon": lambda: "{0} {1}{2}{3}".format(
               ts.get("kenh"), _cat(ts.get("link"), 60),
               " [RADAR {0}, vào sản xuất trước {1}]".format(ts.get("radar"), str(ts.get("han_san_xuat") or "")[:16])
               if ts.get("radar") else "",
               " → " + ", ".join(ts["goi"]) if ts.get("goi") else
               " (đang sản xuất từ {0})".format(str(ts.get("chon_luc"))[:10]) if ts.get("chon_luc") else
               " (có trong bảng, chưa được chọn {0} lượt)".format(ts.get("lan_bo_qua")) if ts.get("lan_bo_qua")
               else ""),
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
    da = sum(1 for d in ds if str(d.get("luc") or "")[:10] == hom_nay and not d.get("khong_tinh")
             and not d.get("ngoai_han_muc") and d.get("trang_thai") != "huy")
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
        elif d.get("lenh") == "uu-tien-nguon" and (toi_han or ts.get("goi")):
            # 12/10/2026: "n0xx → TLx-00yy → kết quả" — chỉ gói bàn giao dùng ĐÚNG link đề cử (`ghi_ban_giao`).
            kq = ket_qua_goi(goc, str(ts.get("kenh") or ""), ts.get("goi"))
            hien += ["    ↳ {0} → {1}".format(d.get("id"), x) for x in kq] or (
                ["    ↳ {0} → chưa có video nào làm từ đúng link này — chấm `sai`/huỷ kèm lý do".format(d.get("id"))]
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
                "",
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
        kl = v.get("ket") or ""   # thước chung (`core.thuoc_thang`) — cùng nhãn V7/giám đốc/tự học
        ra.append((d, "  {0} {1} | {2} | cụm {3} | tiêu đề {4} | @{5}: hiển thị {6}, CTR {7}, xem {8}, AVD {9} ({10}), sub {11} | giờ xem 7d {12} | {13}".format(
            vid + ("/" + ma if ma else ""), d[5:], _cat(r.get("Tiêu đề"), 34), _cat(nuoc.get("cum"), 22) or "?", nuoc.get("kieu_tieu_de") or "?",
            r.get("Mốc mới nhất") or "?", r.get("Lượt hiển thị") or "?", r.get("Tỷ lệ bấm") or "?", r.get("Lượt xem") or "?",
            r.get("Xem TB") or "?", r.get("% độ dài") or "?", r.get("Đăng ký") or "?", _f(tu_hoc._gio_7d(hs), 1),
            ({"thang": "THẮNG", "trung_binh": "trung bình", "truot": "trượt"}.get(kl, "chờ")
             + (" pv {0}".format(_f(v.get("ket_pv"))) if kl else "")))))
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


def bao_cao(goc: str = GOC, bay_gio: Optional[_dt.datetime] = None, toi_da_dong: int = 340) -> str:
    """Báo cáo `xem`: gọn (≤ ~340 dòng), mỗi phần bọc try riêng — hỏng phần nào chỉ phần đó báo lỗi."""
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
            try:
                # 12/10/2026: sub TRỌN ĐỜI + nhãn nguồn số (`core.ypp`), không còn "sub" của cửa sổ 28 ngày trượt.
                from . import ypp as _ypp  # noqa: PLC0415

                r = _ypp.du_bao(goc, k["ma"], bay_gio)
                ra.append("    YPP: {0} · {1} (28 ngày trượt: {2} sub mới, {3} giờ) — {4}".format(
                    _ypp.nhan_sub(r), _ypp.nhan_gio(r), _f(r.get("dang_ky_28")), _f(r.get("gio_28"), 0),
                    _cat(k.get("con_thieu_ypp"), 100)))
            except Exception:  # noqa: BLE001
                ra.append("    YPP (28 ngày trượt): {0} sub mới, {1} giờ xem — {2}".format(
                    _f(y.get("dang_ky")), _f(y.get("gio_xem"), 0), _cat(k.get("con_thieu_ypp"), 100)))
            ra.append("    lịch đăng tới: {0}".format("; ".join(lich) if lich else (_cat(k.get("video_ke_tiep"), 60) or "chưa có")))
        return ra

    def bat_buoc() -> List[str]:
        # 12/10/2026: CHƯƠNG TRÌNH mục 6 (`core/nao_chuong_trinh.py`) thay cho lệnh in sẵn (việc vặt).
        from . import nao_chuong_trinh  # noqa: PLC0415

        return nao_chuong_trinh.chuong_trinh(goc, [k["ma"] for k in kenh_ds], bay_gio)

    phan("VIỆC BẮT BUỘC HÔM NAY — CHƯƠNG TRÌNH 5 VIỆC (mã tính số, BẠN QUYẾT: với mỗi mục chạy/sửa lệnh hoặc ghi "
         "\"giữ nguyên vì …\" có số vào nhật ký; mỗi hành động nêu n + ngày kiểm)", bat_buoc)
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

    phan("GIÁM ĐỐC KÊNH NHỜ XEM (tự xem số bằng `xem`/chi-so rồi quyết; việc CHỈ NGƯỜI làm được — Studio: hạn chế, "
         "xác minh, dành cho trẻ em… — thì `de-xuat` cho chủ)", giam_doc_nho)
    def mo_kenh_moi() -> List[str]:
        from . import mo_kenh as _mk  # noqa: PLC0415

        return _mk.tom_tat_nao(goc)

    phan("MỞ KÊNH MỚI (số do mã tính — luật số kênh; chỉ ĐỀ XUẤT, mở bằng `python -m core.mo_kenh`)", mo_kenh_moi)

    def phong_thi_nghiem() -> List[str]:
        from .phong_thi_nghiem import bao_cao_nao  # noqa: PLC0415

        return bao_cao_nao.dong_nao(goc)

    phan("PHÒNG THÍ NGHIỆM CHỌN CONTENT (giả thuyết × kênh: n, TB [CI90], P(tốt nhất) (Δ so ngày trước); quyết định; "
         "việc sắp tới ngưỡng — đề xuất giả thuyết mới bằng `gia-thuyet-moi`)", phong_thi_nghiem)

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
    """Dòng lệnh `claude` cho một phiên: không giao diện, KHÔNG bypassPermissions (`dontAsk` = ngoài danh sách cho phép
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
    """CLI `claude` — dùng CHUNG bộ dò với đường viết chữ (`core.claude_code.tim_claude`: PATH rồi extension VS Code,
    bản mới nhất). Trước 12/10/2026 hàm này tự dò extension còn `viet_max` thì không — cùng máy hai kết luận."""
    from . import claude_code  # noqa: PLC0415

    return claude_code.tim_claude(goc)


def phien_qua_max(goc: str = GOC) -> bool:
    """Phiên não chạy trên THUÊ BAO Claude Max của máy (đăng nhập sẵn) thay vì khoá ShopAPI?

    Chủ dự án 12/10/2026: *"llm dùng claude 20x chính hãng"* — cùng công tắc với mọi việc viết chữ
    (`core.viet_max.duong_viet_chu`: Cài đặt → "Viết chữ bằng"). Lỗi dò → ví (đường cũ)."""
    try:
        from .viet_max import duong_viet_chu  # noqa: PLC0415

        return duong_viet_chu(goc)[0] == "max"
    except Exception:  # noqa: BLE001
        return False


def moi_truong_phien(goc: str = GOC, qua_max: Optional[bool] = None) -> Tuple[Dict[str, str], str]:
    """`(env, khoá để che log)`. Khoá/địa chỉ ví lấy từ `core.config` (không in ra đâu cả).

    `qua_max` (mặc định: theo `phien_qua_max`) → môi trường ĐÃ GỠ SẠCH mọi biến khoá
    (`claude_code.moi_truong_max`): Claude Code chạy bằng phiên đăng nhập Max của máy, khoá ShopAPI không bao giờ
    thành biến môi trường của nó. Khoá vẫn được trả về để `_che` che nếu nó lỡ lọt vào log."""
    from . import claude_code  # noqa: PLC0415
    from .config import load_config  # noqa: PLC0415

    cau = load_config(os.path.join(goc, "config.json"))
    khoa = (cau.api_key or "").strip()
    if qua_max is None:
        qua_max = phien_qua_max(goc)
    if qua_max:
        mt = claude_code.moi_truong_max()
        mt["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    else:
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
                           encoding="utf-8", errors="replace", timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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


def _them_co_max(lenh: List[str]) -> List[str]:
    """Phiên trên thuê bao Max — quyền/sandbox giữ nguyên, chỉ BỚT đi:

    * `--strict-mcp-config` (không kèm `--mcp-config`): không nạp máy chủ MCP nào của tài khoản claude.ai.
    * `--setting-sources project,local`: không nạp `~/.claude/settings.json` — ở đó máy khách có thể bị Studio cắm
      khoá ShopAPI vào `env` (`claude_code.cai_vao_may`), và Claude Code thấy khoá là dùng khoá thay phiên đăng nhập.
      Quyền của phiên não đến từ cờ `--allowedTools/--disallowedTools` (`cong_cu`), không từ tệp ấy."""
    if "--strict-mcp-config" in lenh:
        return list(lenh)
    return list(lenh[:2]) + ["--strict-mcp-config", "--setting-sources", "project,local"] + list(lenh[2:])


#: Phiên não đợi suất Claude (chung với đường viết chữ, `core.viet_max.giu_suat`) tối đa ngần này giây; quá thì vẫn
#: chạy (một phiên/ngày — không được vì kẹt suất mà mất buổi sáng) và ghi rõ vào log.
GIAY_CHO_SUAT_PHIEN = 45 * 60


def _chay_mot_lan_co_suat(lenh: List[str], loi_nhac: str, goc: str, mt: Dict[str, str], khoa: str, ghi: Any,
                          qua_max: bool, mo_hinh: str) -> Dict[str, Any]:
    """`_chay_mot_lan`, nhưng trên thuê bao Max thì giữ một SUẤT tiến trình `claude` của máy (trần chung với mọi việc
    viết chữ) và ghi sổ dùng thuê bao (`workspace/viet-max/so-dung.jsonl`) — để nhìn được tải thuê bao cả máy."""
    if not qua_max:
        return _chay_mot_lan(lenh, loi_nhac, goc, mt, khoa, ghi)
    from . import viet_max  # noqa: PLC0415

    try:
        with viet_max.giu_suat(goc, viec="nao:phien", cho_toi_da=GIAY_CHO_SUAT_PHIEN, gio_han=GIO_HET_GIO_PHIEN):
            kq = _chay_mot_lan(lenh, loi_nhac, goc, mt, khoa, ghi)
    except viet_max.HetGioChoSuat:
        ghi("đợi suất Claude quá {0} phút (máy đang viết nhiều) — chạy phiên không giữ suất".format(
            GIAY_CHO_SUAT_PHIEN // 60))
        kq = _chay_mot_lan(lenh, loi_nhac, goc, mt, khoa, ghi)
    viet_max.ghi_so_dung(goc, {"mo_hinh": mo_hinh, "giay": kq.get("giay"), "ok": kq.get("ma") == 0 and not kq.get("loi"),
                               "viec": "nao:phien", "luot": kq.get("luot"), "usd_uoc": kq.get("usd"),
                               "loi": "" if kq.get("ma") == 0 else _cat(" | ".join(kq.get("hang_cuoi") or []), 160)})
    return kq


# ── giờ phiên: CHỜ QUÉT STUDIO XONG (12/10/2026) ─────────────────────────────
#
# `workspace/chan-doan/nao-vong-hoc-2026-10-12.md` mục 3 + 5 #8: phiên 04:10 chạy TRƯỚC khi 4 kênh quét xong (lượt quét
# ngày của từng kênh cách nhau 30 phút, kênh cuối ~05:40–06:05) → não luôn xem 4 kênh bằng số HÔM QUA. Giờ phiên tự
# đợi: không bắt đầu trước `nao_gio_phien` (mặc định 06:45, `workspace/cai-dat.json`) VÀ đợi mọi lượt QUÉT NGÀY hôm
# nay của máy ảo kết thúc (xong, hoặc hết lượt thử — cùng luật `vm/agent._quet_ngay_ket_thuc`); quá `nao_cho_quet_toi_da`
# (mặc định 09:30) thì vẫn chạy, ghi rõ kênh nào chưa quét. Lịch Windows cũ 04:10 vẫn đúng (phiên tự đợi); dời lịch
# về giờ mới thì đỡ giữ tiến trình chờ: `python -m core.nao lich` in đúng lệnh `schtasks`.

GIO_PHIEN_MAC_DINH = "06:45"
GIO_CHO_QUET_TOI_DA_MAC_DINH = "09:30"
GIAY_NHIP_CHO_QUET = 5 * 60
QUET_NGAY_TOI_DA_LAN = 3   # khớp `vm/agent.QUET_NGAY_TOI_DA_LAN`


def _doc_json_tep(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _gio_hop_le(chu: Any, mac_dinh: str) -> str:
    s = str(chu or "").strip()
    return s if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s) else mac_dinh


def gio_phien(goc: str = GOC) -> Tuple[str, str]:
    """`(giờ bắt đầu sớm nhất, giờ thôi đợi quét)` "HH:MM" — `workspace/cai-dat.json` khoá `nao_gio_phien`,
    `nao_cho_quet_toi_da`; thiếu/sai → 06:45 / 09:30."""
    cai = _doc_json_tep(os.path.join(goc, "workspace", "cai-dat.json"))
    cai = cai if isinstance(cai, dict) else {}
    return (_gio_hop_le(cai.get("nao_gio_phien"), GIO_PHIEN_MAC_DINH),
            _gio_hop_le(cai.get("nao_cho_quet_toi_da"), GIO_CHO_QUET_TOI_DA_MAC_DINH))


def _thu_muc_vm(goc: str) -> str:
    try:
        from . import trung_tam  # noqa: PLC0415

        return trung_tam.thu_muc_vm(goc)
    except Exception:  # noqa: BLE001
        return os.path.join(goc, "vm")


def quet_hom_nay(goc: str = GOC, bay_gio: Optional[_dt.datetime] = None) -> Tuple[List[str], List[str]]:
    """`(kênh CHƯA quét xong hôm nay, kênh đã xong)` theo `vm/trang-thai.json` (khoá `quet_ngay@<kênh>@<ngày>` của
    máy ảo). Kênh chưa từng có lượt quét ngày nào trên máy này thì bỏ (không đợi kênh máy không quét). Không có máy
    ảo / tệp hỏng → ([], [])."""
    vm = _thu_muc_vm(goc)
    tt = _doc_json_tep(os.path.join(vm, "trang-thai.json"))
    if not isinstance(tt, dict):
        return [], []
    cai = _doc_json_tep(os.path.join(vm, "cai-dat-tool.json"))
    kenh = list(((cai or {}).get("kenh") or {}).keys()) if isinstance(cai, dict) else []
    hom = (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d")
    chua, xong = [], []
    for k in kenh:
        if not any(str(x).startswith("quet_ngay@{0}@".format(k)) for x in tt):
            continue
        muc = tt.get("quet_ngay@{0}@{1}".format(k, hom))
        muc = muc if isinstance(muc, dict) else {}
        if muc.get("xong") or int(muc.get("lan") or 0) >= QUET_NGAY_TOI_DA_LAN:
            xong.append(k)
        else:
            chua.append(k)
    return chua, xong


def cho_quet_xong(goc: str = GOC, *, bay_gio_fn: Any = None, ngu: Any = None, ghi: Any = None) -> Dict[str, Any]:
    """ĐỢI tới giờ phiên + mọi lượt quét Studio hôm nay xong (xem khối chú thích trên). `bay_gio_fn`/`ngu` là seam
    test (mặc định đồng hồ máy / `threading.Event().wait`). Trả `{cho_giay, ly_do, chua}`."""
    bay_gio_fn = bay_gio_fn or _dt.datetime.now
    su_kien = threading.Event()
    ngu = ngu or (lambda giay: su_kien.wait(giay))
    ghi = ghi or (lambda _chu: None)
    gio, han = gio_phien(goc)
    t0 = bay_gio_fn()

    def moc(hhmm: str, ngay: _dt.date) -> _dt.datetime:
        h, m = (int(x) for x in hhmm.split(":"))
        return _dt.datetime.combine(ngay, _dt.time(h, m))

    bat_dau, het = moc(gio, t0.date()), moc(han, t0.date())
    da_bao = False
    while True:
        bg = bay_gio_fn()
        if bg < bat_dau:
            if not da_bao:
                ghi("phiên não đợi tới {0} (giờ phiên `nao_gio_phien`) rồi kiểm quét Studio".format(gio))
                da_bao = True
            ngu(min(GIAY_NHIP_CHO_QUET * 2, max(1.0, (bat_dau - bg).total_seconds())))
            continue
        chua, _xong = quet_hom_nay(goc, bg)
        cho = round((bg - t0).total_seconds())
        if not chua:
            return {"cho_giay": cho, "ly_do": "quét Studio hôm nay đã xong" if _xong else "không có lượt quét để đợi",
                    "chua": []}
        if bg >= het:
            return {"cho_giay": cho, "ly_do": "quá {0} vẫn chưa quét xong: {1} — chạy với số cũ của các kênh này".format(
                han, ", ".join(chua)), "chua": chua}
        ghi("đợi quét Studio xong: còn {0}".format(", ".join(chua)))
        ngu(GIAY_NHIP_CHO_QUET)


def lenh_doi_lich(goc: str = GOC) -> str:
    """Lệnh `schtasks` dời lịch phiên não `ShopAPI-Nao` về giờ phiên đang cấu hình (người vận hành tự chạy)."""
    from .lich_tu_chay import TEN_VIEC_NAO  # noqa: PLC0415

    return 'schtasks /Change /TN "{0}" /ST {1}'.format(TEN_VIEC_NAO, gio_phien(goc)[0])


def chay_phien(goc: str = GOC, ep: bool = False, thu: bool = False, bay_gio: Optional[_dt.datetime] = None,
               cho: bool = True) -> int:
    """Một phiên não. Mã thoát: 0 xong (hoặc đã có phiên hôm nay) · 1 hỏng · 3 đang có phiên khác.
    `cho` (mặc định): đợi giờ phiên + quét Studio hôm nay xong (`cho_quet_xong`) trước khi chạy."""
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
    if thu:
        g, h = gio_phien(goc)
        chua, _x = quet_hom_nay(goc, bay_gio)
        print("Giờ phiên: không trước {0}, đợi quét Studio tới {1} (còn chưa quét hôm nay: {2}). Dời lịch: {3}".format(
            g, h, ", ".join(chua) or "không", lenh_doi_lich(goc)))
    elif cho:
        def _ghi_cho(chu: str) -> None:
            try:
                with io.open(duong_log, "a", encoding="utf-8", newline="\n") as f_cho:
                    f_cho.write("{0} [chờ] {1}\n".format(time.strftime("%H:%M:%S"), chu))
            except OSError:
                pass
        kq_cho = cho_quet_xong(goc, ghi=_ghi_cho)
        _ghi_cho("{0} (đợi {1} phút)".format(kq_cho["ly_do"], kq_cho["cho_giay"] // 60))
        bay_gio = _dt.datetime.now()
    loi_nhac = CAU_HOI_PHIEN.format(hom_nay)
    qua_max = phien_qua_max(goc)
    mo_hinh = MO_HINH_PHIEN
    if qua_max:
        from . import viet_max  # noqa: PLC0415

        mo_hinh = viet_max.mo_hinh_dang_dung(goc)
    lenh = lenh_phien(duong, goc, mo_hinh=mo_hinh)
    if qua_max:
        lenh = _them_co_max(lenh)
    if thu:
        print(" ".join(lenh) + "\n(stdin) " + loi_nhac)
        return 0
    if not lay_khoa(goc):
        print("Đang có phiên khác chạy (khoá nao/.khoa-phien) — thoát.")
        return 3
    f = io.open(duong_log, "a", encoding="utf-8", newline="\n")
    mt, khoa = moi_truong_phien(goc, qua_max=qua_max)

    def ghi(chu: str) -> None:
        f.write(_che("{0} {1}\n".format(time.strftime("%H:%M:%S"), chu), khoa))
        f.flush()

    try:
        ghi("=== BAT DAU PHIEN {0} · model {1} · {2} · tối đa {3} lượt · hết giờ {4} phút".format(
            hom_nay, mo_hinh, "thuê bao Claude Max của máy" if qua_max else "ví ShopAPI",
            SO_LUOT_TOI_DA, GIO_HET_GIO_PHIEN // 60))
        ghi("lệnh: " + " ".join(lenh[:1] + lenh[1:]))
        kq = _chay_mot_lan_co_suat(lenh, loi_nhac, goc, mt, khoa, ghi, qua_max, mo_hinh)
        txt = " ".join(kq["hang_cuoi"]).lower()
        if kq["ma"] != 0 and not kq["ket"] and "max-turns" in txt and ("unknown" in txt or "unrecognized" in txt):
            ghi("bản claude không nhận --max-turns — chạy lại không có cờ này")
            lenh = lenh_phien(duong, goc, mo_hinh=mo_hinh, so_luot=None)
            kq = _chay_mot_lan_co_suat(_them_co_max(lenh) if qua_max else lenh, loi_nhac, goc, mt, khoa, ghi,
                                       qua_max, mo_hinh)
        # Thuê bao cạn hạn mức model này → khoá bậc ấy (sổ chung với đường viết chữ) và chạy lại MỘT lần bằng
        # bậc dưới. Không đợi: cửa sổ hạn mức mở lại tính bằng giờ (xem `core.viet_max.THANG_MO_HINH`).
        if qua_max and (kq["ma"] != 0 or kq.get("loi")):
            from . import viet_max  # noqa: PLC0415

            loi_tho = RuntimeError(" ".join([str(kq.get("ket") or "")] + list(kq.get("hang_cuoi") or [])))
            vi_sao = viet_max.ly_do_tut_bac(loi_tho)
            if vi_sao:
                viet_max.ghi_han_muc(goc, mo_hinh, viet_max.gio_mo_lai(loi_tho, time.time()) if vi_sao == "han_muc"
                                     else time.time() + viet_max.GIAY_KHOA_MODEL_HONG)
                ke = viet_max.mo_hinh_dang_dung(goc)
                if ke != mo_hinh:
                    ghi("{0} {1} — chạy lại bằng {2}.".format(
                        mo_hinh, "cạn hạn mức thuê bao" if vi_sao == "han_muc" else "máy không dùng được", ke))
                    mo_hinh = ke
                    lenh = _them_co_max(lenh_phien(duong, goc, mo_hinh=mo_hinh))
                    kq = _chay_mot_lan_co_suat(lenh, loi_nhac, goc, mt, khoa, ghi, qua_max, mo_hinh)
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
                                    "model": mo_hinh, "duong": "claude_max" if qua_max else "vi",
                                    "thanh_cong": thanh_cong}, ensure_ascii=False) + "\n")
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


def de_xuat_gia_thuyet(goc: str, ns: argparse.Namespace) -> str:
    """`gia-thuyet-moi`: thêm một giả thuyết `trong_so` vào sổ phòng thí nghiệm (trạng thái bóng — chưa nhận khe sản
    xuất tới khi luật `phong_thi_nghiem.luat.du_thu` cho). Không tính vào hạn mức hành động/ngày (không đổi sản xuất
    ngay); hạn mức riêng: ≤ 2 đề xuất / 7 ngày, ≤ 6 giả thuyết của não đang chạy bóng. Lỗi → `TuChoi`."""
    from .phong_thi_nghiem import gia_thuyet as gtm  # noqa: PLC0415

    if getattr(ns, "dac_trung", False):
        so_, chu = gtm.dac_trung_hop_le()
        return ("ĐẶC TRƯNG SỐ (trọng số + cổng): {0}\nĐẶC TRƯNG CHỮ (chỉ cổng: co/khong/==/!=): {1}\nVí dụ: --trong-so "
                "\"log_pool_cum_xem:1,log_vuot:0.8,dai_tot:0.5\" --cong \"vuot>=3; tang_duong co; vung_cua_anh_em "
                "khong\" --tran \"log_vuot:3.912\"").format(", ".join(so_), ", ".join(chu))
    try:
        kq = gtm.de_xuat(goc, ns.id, mo_ta=ns.mo_ta, trong_so=gtm.phan_tich_cap(ns.trong_so),
                         cong=gtm.phan_tich_cong(ns.cong), tran=gtm.phan_tich_cap(ns.tran), ly_do=ns.ly_do,
                         tac_gia="nao")
    except ValueError as loi:
        raise TuChoi(str(loi)) from None
    g = kq["gia_thuyet"]
    thu = "; ".join("{0} {1}: {2} qua cổng".format(x["kenh"], x["ngay"], x["n_du"]) for x in kq.get("thu") or [])
    return ("ĐÃ GHI giả thuyết {0} (bóng, phiên bản 1): {1}\n  thử trên kho gần nhất: {2}\n  Mã sẽ ghi nhật ký bóng mỗi "
            "ngày; sau ≥ 7 ngày + qua sàn tầng 1 thì được 1 khe/kênh/tuần. Xem: `python -m core.nao phong-thi-nghiem`."
            .format(g["id"], g["mo_ta"], thu or "chưa có ảnh chụp kho"))


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
    u.add_argument("--radar", default="", help="video_id của kênh đang trên RADAR NỔ (mã kiểm) — không tính hạn mức "
                                               "ngày, phải vào sản xuất trong 48 giờ")
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
    pt = s.add_parser("phong-thi-nghiem", help="mục phòng thí nghiệm (bảng xếp hạng, quyết định, sắp tới ngưỡng)")
    pt.add_argument("--kenh", action="append", default=[])
    gm = s.add_parser("gia-thuyet-moi", help="đề xuất MỘT giả thuyết chọn content mới (dạng dữ liệu, chạy bóng trước)")
    gm.add_argument("--id", default="", help="H-TEN (chữ HOA/số/gạch)")
    gm.add_argument("--mo-ta", default="", help="một câu: giả thuyết là gì")
    gm.add_argument("--trong-so", default="", help="đặc_trưng:hệ_số,... (điểm = Σ hệ số × giá trị)")
    gm.add_argument("--cong", default="", help="điều kiện cách nhau bằng ; — f>=số | f<=số | f co | f khong")
    gm.add_argument("--tran", default="", help="đặc_trưng:trần,... (giá trị bị kẹp trước khi nhân)")
    gm.add_argument("--ly-do", default="", help="lý lẽ + số: vì sao bộ chấm này nhặt đúng thứ sẽ thắng")
    gm.add_argument("--dac-trung", action="store_true", help="chỉ in danh sách đặc trưng dùng được")
    ph = s.add_parser("phien", help="chạy một phiên não (claude không giao diện)")
    ph.add_argument("--ep", action="store_true", help="bỏ giới hạn một phiên/ngày")
    ph.add_argument("--thu", action="store_true", help="chỉ in lệnh, không chạy")
    ph.add_argument("--khong-cho", action="store_true", help="không đợi giờ phiên / quét Studio xong")
    s.add_parser("lich", help="giờ phiên đang cấu hình + lệnh schtasks dời lịch ShopAPI-Nao (chỉ in)")
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
    if l == "phong-thi-nghiem":
        from .phong_thi_nghiem import bao_cao_nao  # noqa: PLC0415

        return "\n".join(["PHÒNG THÍ NGHIỆM CHỌN CONTENT"] + bao_cao_nao.dong_nao(goc, kenh_ds=ns.kenh or None))
    if l == "gia-thuyet-moi":
        return de_xuat_gia_thuyet(goc, ns)
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
        ts = {"kenh": ns.kenh, "link": ns.link.strip()}
        if str(getattr(ns, "radar", "") or "").strip():
            ts["radar"] = str(ns.radar).strip()
        hd = tao_hanh_dong(goc, "uu-tien-nguon", ts, **chung)
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
        return chay_phien(goc, ep=ns.ep, thu=ns.thu, cho=not ns.khong_cho)
    if ns.lenh == "lich":
        g, h = gio_phien(goc)
        chua, xong = quet_hom_nay(goc)
        print("Phiên não: không bắt đầu trước {0}; đợi quét Studio hôm nay xong tới {1} (workspace/cai-dat.json: "
              "nao_gio_phien, nao_cho_quet_toi_da).\nQuét hôm nay: xong {2} · chưa {3}.\nDời lịch Windows (chạy một "
              "lần, cửa sổ lệnh thường):\n  {4}".format(g, h, ", ".join(xong) or "-", ", ".join(chua) or "-",
                                                         lenh_doi_lich(goc)))
        return 0
    try:
        print(chay_lenh(ns, goc))
        return 0
    except TuChoi as loi:
        print("TỪ CHỐI: {0}".format(loi))
        return 2


if __name__ == "__main__":
    sys.exit(main())
