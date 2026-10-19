"""TỰ KÍCH HOẠT KỸ NĂNG (14/10/2026) — bộ chạy cho các skill có `dieu_kien` trong `core/ky_nang.py`.

Chủ: *"mấy cái mày đang làm tao nghĩ là đóng gói thành skill để tái sử dụng nhiều lần — kiểu nó auto khi có điều kiện"*.
Thiết kế đã duyệt: `workspace/chan-doan/thiet-ke-ky-nang-tu-kich-hoat.md`. Luật: `LUAT` ngay dưới (cũng in ở docs/KY-NANG.md).

Dùng:  python -X utf8 -m core.ky_nang tu-kich-hoat [--thu] [--goc G]   (--thu: chỉ in sẽ chạy gì, không chạy, không ghi)
       python -m core.ky_nang lich        in lệnh schtasks đăng ký `ShopAPI-KyNang` (mỗi giờ :35) — chủ tự đăng ký
Sổ:    workspace/ky-nang/so-chay.jsonl    mỗi dòng {luc, ma, kenh, quyet, ly_do, [lenh, ma_thoat, giay, ket, duoi]}
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core import ky_nang as kn

LUAT = (
    "Mỗi lượt quét kênh máy này quản lý × skill có `dieu_kien`; skill `toan_may` quét một lần.",
    "Chạy khi điều kiện đúng, `tu_ap`, công tắc chung bật (`workspace/cai-dat.json: ky_nang_tu_kich_hoat`), kênh không tắt "
    "skill (`kenh.yaml: ky_nang_tat: [mã, …]`), đã qua `nhip_gio` kể từ lần chạy cuối và không đang tạm dừng.",
    "Việc nhẹ chạy hết; việc NẶNG (DOM / sản xuất) tối đa MỘT mỗi lượt và chỉ khi khoá máy `.khoa-may` rảnh, không ai xếp "
    "hàng — bận thì để lượt sau, không bao giờ ép.",
    "Không chạy trong phút :55–:05.",
    "Mã thoát 0/30 = xong, 10/4 = hoãn (không tính), còn lại hay quá giờ = hỏng; xong mà điều kiện vẫn đúng với CÙNG lệnh = "
    "chưa đạt (tính hỏng).",
    "Hỏng 3 lần liền → tạm dừng skill đó ở kênh đó 24 giờ, báo Việc của bạn + báo động.",
    "`tu_ap=False` chỉ báo «nên chạy» (bảng 8790 + báo cáo ngày), không bao giờ tự chạy.",
    "Mọi kết quả, và mọi quyết định khác lần ghi trước, vào `workspace/ky-nang/so-chay.jsonl` + một sự kiện não bộ phận.",
)

SO_CHAY = ("workspace", "ky-nang", "so-chay.jsonl")
HONG_LIEN_TOI_DA, GIO_TAM_DUNG = 3, 24
HAN_NANG_PHUT, HAN_NHE_PHUT = 60, 15
UU_TIEN_NANG = ("S03", "S04", "D09", "K20", "D15", "D14", "D13")   # việc nặng gấp trước: bìa sắp lên sóng, bàn giao
#                         kẹt, thương hiệu; việc máy Studio (sức khoẻ trước thử nghiệm bìa). D18 (19/10) hết nặng: đo từ lần quét
MA_XONG, MA_HOAN = (0, 30), (10, 4)
TEN_TAC_VU = "ShopAPI-KyNang"
#: Skill → bộ phận của não (`core.nao_bo_phan.BO_PHAN`) để não học tỉ lệ thành công từng skill.
BO_PHAN = {"S02": "dieu-phoi", "S03": "bia", "S04": "ban-giao", "S05": "bia", "D09": "dang-video", "K20": "dang-video",
           "D10": "kich-ban", "D11": "bia", "D12": "suc-khoe-may", "D13": "bia", "D14": "chi-so-studio",
           "D15": "tieu-de", "D16": "chi-so-studio", "D17": "anh-clip", "S06": "bia", "D18": "doi-thu", "D19": "bia"}
NHAN = {"se_chay": "sẽ chạy", "nen_chay": "nên chạy — chờ chủ", "cho_nhip": "đã chạy, chờ nhịp", "tam_dung": "tạm dừng",
        "cong_tac_tat": "công tắc chung tắt", "tat_kenh": "tắt ở kênh này", "khong": "chưa cần", "xong": "xong",
        "hong": "hỏng", "hoan": "hoãn", "bo_qua": "để lượt sau"}
CHAY = ("xong", "hong")                              # quyết định là một lần CHẠY thật (tính nhịp + chuỗi hỏng)
ChayLenh = Callable[[List[str], str, float], Tuple[int, str]]


def _luc(bay: _dt.datetime) -> str:
    return bay.strftime("%Y-%m-%d %H:%M:%S")


# ── sổ chạy ────────────────────────────────────────────────────────────────────

def duong_so(goc: str) -> str:
    return os.path.join(goc, *SO_CHAY)


def doc_so(goc: str, toi_da: int = 5000) -> List[Dict[str, Any]]:
    try:
        with open(duong_so(goc), "r", encoding="utf-8") as tep:
            dong = tep.readlines()[-toi_da:]
    except OSError:
        return []
    ra = []
    for d in dong:
        try:
            x = json.loads(d)
        except ValueError:
            continue
        if isinstance(x, dict):
            ra.append(x)
    return ra


def _cua(so, ma, kenh) -> List[Dict[str, Any]]:
    return [x for x in so if x.get("ma") == ma and (x.get("kenh") or "") == (kenh or "")]


def lan_chay_cuoi(so, ma, kenh) -> Optional[Dict[str, Any]]:
    return next((x for x in reversed(_cua(so, ma, kenh)) if x.get("quyet") in CHAY), None)


def lan_xong_cuoi(goc: str, ma: str, kenh: str) -> str:
    return next((str(x.get("luc") or "") for x in reversed(_cua(doc_so(goc), ma, kenh)) if x.get("quyet") == "xong"), "")


def hong_lien(so, ma, kenh) -> Tuple[int, Optional[Dict[str, Any]]]:
    """(số lần chạy hỏng liền tính từ cuối, lần hỏng cuối)."""
    n, cuoi = 0, None
    for x in reversed([x for x in _cua(so, ma, kenh) if x.get("quyet") in CHAY]):
        if x.get("quyet") != "hong":
            break
        n, cuoi = n + 1, cuoi or x
    return n, cuoi


def tam_dung_toi(so, ma, kenh, bay) -> Optional[_dt.datetime]:
    n, cuoi = hong_lien(so, ma, kenh)
    t = kn._doc_luc((cuoi or {}).get("luc")) if n >= HONG_LIEN_TOI_DA else None  # noqa: SLF001
    toi = t + _dt.timedelta(hours=GIO_TAM_DUNG) if t else None
    return toi if toi and toi > bay else None


def _ghi(goc: str, x: Dict[str, Any], bay: _dt.datetime) -> Dict[str, Any]:
    """Một dòng sổ + một sự kiện não bộ phận (não hỏng không bao giờ làm hỏng lượt)."""
    muc = {"luc": _luc(bay), "ma": x["ma"], "kenh": x["kenh"], "quyet": x["quyet"], "ly_do": x["ly_do"]}
    muc.update({k: x[k] for k in ("lenh", "ma_thoat", "giay", "ket", "duoi") if x.get(k) not in (None, "", [])})
    os.makedirs(os.path.dirname(duong_so(goc)), exist_ok=True)
    with open(duong_so(goc), "a", encoding="utf-8") as tep:
        tep.write(json.dumps(muc, ensure_ascii=False) + "\n")
    try:
        from core import nao_bo_phan  # noqa: PLC0415
        nao_bo_phan.ghi(goc, BO_PHAN.get(x["ma"], "dieu-phoi"), {"xong": "ket_qua", "hong": "loi"}.get(x["quyet"], "chon"),
                        kenh=x["kenh"], noi_dung="skill {0} {1}: {2} — {3}".format(
                            x["ma"], x["ten"], NHAN.get(x["quyet"], x["quyet"]), x.get("ket") or x["ly_do"]),
                        so={"ma": x["ma"], "quyet": x["quyet"], "ma_thoat": x.get("ma_thoat"), "giay": x.get("giay")},
                        nguon="ky_nang", khoa="ky-nang|{0}|{1}|{2}|{3}".format(x["ma"], x["kenh"], muc["luc"], x["quyet"]))
    except Exception:  # noqa: BLE001
        pass
    return muc


def _ghi_neu_doi(goc, x, so, bay) -> None:
    """Quyết định không chạy: chỉ ghi khi khác dòng ghi trước của cùng (skill, kênh) — sổ không phình mỗi giờ."""
    truoc = (_cua(so, x["ma"], x["kenh"]) or [{}])[-1]
    if (truoc.get("quyet"), truoc.get("ly_do")) != (x["quyet"], x["ly_do"]):
        so.append(_ghi(goc, x, bay))


# ── đánh giá ───────────────────────────────────────────────────────────────────

def cong_tac_bat(goc: str) -> bool:
    from core import cai_dat  # noqa: PLC0415
    return bool(cai_dat.doc(goc).get("ky_nang_tu_kich_hoat", True))


def tat_o_kenh(goc: str, kenh: str) -> set:
    """`kenh.yaml: ky_nang_tat: [S03, D09]` (hoặc chuỗi "S03, D09")."""
    v = kn._kenh_yaml(goc, kenh).get("ky_nang_tat") if kenh else None  # noqa: SLF001
    ds = v if isinstance(v, list) else str(v or "").replace(",", " ").split()
    return {str(m).strip().upper() for m in ds if str(m).strip()}


def lenh_cua(k, goc: str, kenh: str) -> List[str]:
    return list(k.chay(goc, kenh) if callable(k.chay) else (k.chay or []))


def _xet(goc, k, kenh, bay, so, bat) -> Dict[str, Any]:
    try:
        dung, ly = k.dieu_kien(goc, kenh)
    except Exception as loi:  # noqa: BLE001 — một điều kiện hỏng không làm vỡ lượt
        dung, ly = False, "điều kiện lỗi: {0}".format(str(loi)[:100])
    x: Dict[str, Any] = {"ma": k.ma, "ten": k.ten, "kenh": kenh, "dung": bool(dung), "ly_do": str(ly or ""),
                         "nang": k.nang, "tu_ap": k.tu_ap, "lenh": []}
    cuoi = lan_chay_cuoi(so, k.ma, kenh)
    x["lan_cuoi"] = {t: cuoi.get(t) for t in ("luc", "quyet", "ly_do", "ket")} if cuoi else None
    toi = tam_dung_toi(so, k.ma, kenh, bay)
    luc_cuoi = kn._doc_luc((cuoi or {}).get("luc"))  # noqa: SLF001
    if not dung:
        q = "khong"
    elif k.ma in tat_o_kenh(goc, kenh):
        q = "tat_kenh"
    elif not k.tu_ap:
        q = "nen_chay"
    elif not bat:
        q = "cong_tac_tat"
    elif toi:
        q, x["ly_do"] = "tam_dung", "hỏng {0} lần liền — tạm dừng tới {1:%H:%M %d/%m}".format(hong_lien(so, k.ma, kenh)[0], toi)
    elif luc_cuoi and bay - luc_cuoi < _dt.timedelta(hours=k.nhip_gio):
        q = "cho_nhip"
    else:
        q = "se_chay"
        try:
            x["lenh"] = lenh_cua(k, goc, kenh)
        except Exception as loi:  # noqa: BLE001
            q, x["ly_do"] = "khong", "dựng lệnh lỗi: {0}".format(str(loi)[:100])
    x["quyet"] = q
    return x


def danh_gia(goc: str, bay: Optional[_dt.datetime] = None, kenh_ds: Optional[List[str]] = None,
             so: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Mọi (skill có điều kiện × kênh): {ma, ten, kenh, dung, ly_do, quyet, nang, tu_ap, lenh, lan_cuoi}. Chỉ đọc."""
    bay = bay or kn._gio()  # noqa: SLF001
    so = doc_so(goc) if so is None else so
    kenh_ds = kn._cac_kenh(goc) if kenh_ds is None else kenh_ds  # noqa: SLF001
    bat = cong_tac_bat(goc)
    return [_xet(goc, k, kenh, bay, so, bat) for k in kn.DANH_MUC if k.dieu_kien is not None
            for kenh in ([""] if k.toan_may else kenh_ds)]


def danh_gia_kenh(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """Mã skill → đánh giá cho MỘT kênh (kèm skill toàn máy) — cho bảng 8790."""
    so = doc_so(goc)
    return {x["ma"]: dict(x, nhan=NHAN.get(x["quyet"], x["quyet"])) for x in danh_gia(goc, kenh_ds=[kenh], so=so)}


# ── chạy ───────────────────────────────────────────────────────────────────────

def phut_cam(bay: _dt.datetime) -> bool:
    return bay.minute >= 55 or bay.minute < 5


def khoa_may_ban(goc: str) -> str:
    """'' nếu khe "nang" (`workspace/tu-chay/.khoa-may`) rảnh và không vé nào xếp hàng; câu lý do nếu bận. CHỈ ĐỌC
    (không dọn vé chết như `khe.trang_thai`) — chạy thử trên dữ liệu thật không được ghi gì."""
    from core import khe  # noqa: PLC0415

    def song(du) -> bool:
        try:
            return isinstance(du, dict) and khe.pid_con_song(int(du.get("pid") or 0))
        except (TypeError, ValueError):
            return False
    giu = kn._json(khe.duong_khoa_nang(goc))  # noqa: SLF001
    if song(giu):
        return "khoá máy đang giữ: " + khe.mo_ta_nguoi_giu(giu)
    try:
        ve = [kn._json(khe.duong_cho(goc), t) for t in os.listdir(khe.duong_cho(goc)) if t.endswith(".json")]  # noqa: SLF001
    except OSError:
        ve = []
    cho = [v for v in ve if song(v) and (v or {}).get("loai") == "nang"]
    return "{0} việc đang xếp hàng khoá máy".format(len(cho)) if cho else ""


def _chay_that(lenh: List[str], cwd: str, han_giay: float) -> Tuple[int, str]:
    """Tiến trình con không cửa sổ; quá hạn → giết cả cây (taskkill /T). Trả (mã thoát, đuôi đầu ra)."""
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    p = subprocess.Popen(lenh, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=co, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    try:
        ra, _ = p.communicate(timeout=han_giay)
        return p.returncode, (ra or b"").decode("utf-8", "replace")[-600:]
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, creationflags=co, check=False)
        p.kill()
        ra, _ = p.communicate()
        return -9, "quá {0:.0f} phút — đã dừng cả cây tiến trình. {1}".format(
            han_giay / 60, (ra or b"").decode("utf-8", "replace")[-500:])


def lenh_ngan(lenh: List[str], goc: str) -> str:
    return " ".join("python" if i == 0 and a == sys.executable else
                    (os.path.relpath(a, goc) if os.path.isabs(a) and a.startswith(goc) else a) for i, a in enumerate(lenh))


def _chay_mot(goc: str, x: Dict[str, Any], chay_lenh: ChayLenh, so: List[Dict[str, Any]]) -> None:
    k = kn.theo_ma(x["ma"])
    t0 = time.time()
    try:
        ma, duoi = chay_lenh(x["lenh"], goc, (k.han_phut or (HAN_NANG_PHUT if k.nang else HAN_NHE_PHUT)) * 60.0)
    except Exception as loi:  # noqa: BLE001
        ma, duoi = -1, "không chạy được: {0}".format(str(loi)[:200])
    if ma in MA_HOAN:
        q, ket = "hoan", "hoãn (mã {0}) — lượt sau thử lại".format(ma)
    elif ma not in MA_XONG:
        q, ket = "hong", "mã thoát {0}".format(ma)
    else:
        try:
            dung, ly2 = k.dieu_kien(goc, x["kenh"])
            con = dung and lenh_cua(k, goc, x["kenh"]) == x["lenh"]
        except Exception:  # noqa: BLE001
            con, ly2 = False, ""
        q, ket = ("hong", "chạy xong mà điều kiện vẫn đúng (chưa đạt): " + ly2) if con else ("xong", "đạt")
    x.update(quyet=q, ket=ket, ma_thoat=ma, giay=round(time.time() - t0, 1), duoi=str(duoi or "").strip()[-600:],
             lenh=lenh_ngan(x["lenh"], goc))
    so.append(_ghi(goc, x, kn._gio()))  # noqa: SLF001
    n = hong_lien(so, x["ma"], x["kenh"])[0] if q == "hong" else 0
    if n >= HONG_LIEN_TOI_DA:
        try:
            from core import bao_dong  # noqa: PLC0415
            bao_dong.bao_dong("ky_nang_tam_dung", "Skill {0} «{1}» hỏng {2} lần liền{3} — máy tạm dừng {4} giờ".format(
                x["ma"], x["ten"], n, " ở kênh " + x["kenh"] if x["kenh"] else "", GIO_TAM_DUNG),
                "{0}\n{1}".format(ket, x["duoi"][-300:]), goc=goc, kenh=x["kenh"] or None)
        except Exception:  # noqa: BLE001
            pass


def _thu_tu(x: Dict[str, Any], doi: Optional[set] = None) -> Tuple[bool, bool, int, str]:
    """Nhẹ trước nặng; trong việc nặng: việc ĐÓI SUẤT (`core.loi_lap_lai` — bị "để lượt sau" liên tục > 6 giờ, sổ
    `workspace/tu-kiem/uu-tien.json`) lên đầu, rồi theo `UU_TIEN_NANG`."""
    return (x["nang"], "{0}|{1}".format(x["ma"], x["kenh"] or "") not in (doi or set()),
            (UU_TIEN_NANG.index(x["ma"]) if x["ma"] in UU_TIEN_NANG else len(UU_TIEN_NANG)), x["kenh"])


def _viec_doi(goc: str) -> set:
    try:
        from core import loi_lap_lai  # noqa: PLC0415
        return set((loi_lap_lai.doc_uu_tien(goc).get("viec") or {}).keys())
    except Exception:  # noqa: BLE001
        return set()


def _dong(x: Dict[str, Any], goc: str) -> str:
    return "{0:<10} {1} {2:<28} {3:<20} {4}{5}".format(
        x["kenh"] or "(máy)", x["ma"], x["ten"][:28], NHAN.get(x["quyet"], x["quyet"]),
        x.get("ket") or x["ly_do"], "  → " + (x["lenh"] if isinstance(x["lenh"], str) else lenh_ngan(x["lenh"], goc))
        if x["lenh"] else "")


def tu_kich_hoat(goc: str, *, thu: bool = False, chay_lenh: Optional[ChayLenh] = None,
                 in_ra: Callable[[str], None] = print) -> List[Dict[str, Any]]:
    """MỘT lượt tự kích hoạt (luật `LUAT`). `thu=True`: chỉ in, không chạy, không ghi gì."""
    bay = kn._gio()  # noqa: SLF001
    if phut_cam(bay) and not thu:
        in_ra("phút :{0:02d} nằm trong :55–:05 — bỏ lượt này".format(bay.minute))
        return []
    so = doc_so(goc)
    ds = danh_gia(goc, bay, so=so)
    if thu:
        in_ra("CHẠY THỬ {0:%H:%M %d/%m} — công tắc chung {1} · khoá máy {2}{3}".format(
            bay, "bật" if cong_tac_bat(goc) else "TẮT", khoa_may_ban(goc) or "rảnh",
            " · phút :55–:05: lượt thật sẽ bỏ qua" if phut_cam(bay) else ""))
        for x in sorted(ds, key=lambda x: (x["kenh"], x["ma"])):
            in_ra(_dong(x, goc))
        return ds
    chay_lenh = chay_lenh or _chay_that
    da_nang = False
    doi = _viec_doi(goc)
    mot_kenh_da: set = set()
    for x in sorted(ds, key=lambda x: _thu_tu(x, doi)):
        if x["quyet"] == "se_chay":
            k_ = kn.theo_ma(x["ma"])
            if phut_cam(kn._gio()):  # noqa: SLF001
                x.update(quyet="bo_qua", ly_do="phút :55–:05 — để lượt sau")
            elif getattr(k_, "mot_kenh", False) and x["ma"] in mot_kenh_da:
                x.update(quyet="bo_qua", ly_do="lượt này đã chạy skill này cho một kênh — kênh này lượt sau")
            elif x["nang"] and da_nang:
                x.update(quyet="bo_qua", ly_do="lượt này đã có một việc nặng — để lượt sau")
            elif x["nang"]:
                da_nang = True                # bận hay không, lượt này hết suất việc nặng
                ban = khoa_may_ban(goc)
                if ban:
                    x.update(quyet="bo_qua", ly_do="khoá máy bận — để lượt sau, không ép ({0})".format(ban))
        if x["quyet"] == "se_chay":
            if getattr(kn.theo_ma(x["ma"]), "mot_kenh", False):
                mot_kenh_da.add(x["ma"])
            _chay_mot(goc, x, chay_lenh, so)
        elif x["quyet"] not in ("khong", "cho_nhip"):
            _ghi_neu_doi(goc, x, so, kn._gio())  # noqa: SLF001
        if x["quyet"] not in ("khong", "cho_nhip"):
            in_ra(_dong(x, goc))
    return ds


# ── báo: Việc của bạn · báo cáo ngày · lịch ───────────────────────────────────

def viec_cua_ban(goc: str, bay: Optional[_dt.datetime] = None) -> List[Dict[str, str]]:
    """Việc chỉ người làm được: skill tạm dừng (hỏng 3 lần), kenh.yaml thiếu khoá / BOM không tự gỡ (S02), não bộ phận
    chưa ngủ > 30 giờ (D12). Mỗi phần tử {khoa, kenh, chu, goi_y} — khoá đổi khi sự việc đổi (bấm Đã xử lý chỉ ẩn lần này)."""
    bay = bay or kn._gio()  # noqa: SLF001
    ra: List[Dict[str, str]] = []
    so = doc_so(goc)
    for ma, kenh in sorted({(x.get("ma"), x.get("kenh") or "") for x in so if x.get("quyet") == "hong"}):
        toi = tam_dung_toi(so, ma, kenh, bay)
        if not toi:
            continue
        n, cuoi = hong_lien(so, ma, kenh)
        k = kn.theo_ma(ma)
        ra.append({"khoa": "ky-nang-dung:{0}:{1}:{2}".format(ma, kenh, cuoi.get("luc")), "kenh": kenh,
                   "chu": "Skill {0} «{1}» hỏng {2} lần liền{3} — máy tạm dừng tới {4:%H:%M %d/%m}".format(
                       ma, k.ten if k else "?", n, " ở kênh " + kenh if kenh else "", toi),
                   "goi_y": "→ lỗi cuối: {0} · sổ workspace/ky-nang/so-chay.jsonl; hết hạn máy tự thử lại".format(
                       str(cuoi.get("ket") or cuoi.get("ly_do") or "?")[:120])})
    for kenh in kn._cac_kenh(goc):  # noqa: SLF001
        try:
            c = kn._kham_cau_hinh(goc, kenh)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            continue
        if not c["tu_chay"]:
            continue
        if c["bom"][0] == "bao":
            ra.append({"khoa": "ky-nang:S02:{0}:bom".format(kenh), "kenh": kenh,
                       "chu": "kenh.yaml kênh {0}: {1}".format(kenh, c["bom"][1]),
                       "goi_y": "→ mở kenh.yaml, xoá ký tự lạ U+FEFF giữa tệp, lưu UTF-8 (máy không tự gỡ vì sợ đổi nghĩa)"})
        if c["thieu"]:
            ra.append({"khoa": "ky-nang:S02:{0}:{1}".format(kenh, ",".join(k for k, _g in c["thieu"])), "kenh": kenh,
                       "chu": "kenh.yaml kênh {0} thiếu khoá tự chạy: {1}".format(kenh, ", ".join(k for k, _g in c["thieu"])),
                       "goi_y": "→ thêm: " + " · ".join(g for _k, g in c["thieu"])})
    try:
        _gom, ngu, co = kn._nao_bp(goc)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        co, ngu = False, None
    if co and (ngu is None or ngu > kn.GIO_NGU_CU):
        ra.append({"khoa": "ky-nang:D12:ngu:{0:%Y-%m-%d}".format(bay), "kenh": "",
                   "chu": "Não bộ phận chưa ngủ {0} (> {1:.0f} giờ)".format(
                       "lần nào" if ngu is None else "{0:.0f} giờ".format(ngu), kn.GIO_NGU_CU),
                   "goi_y": "→ xem tác vụ ShopAPI-NaoBoPhan-Ngu (03:40) · chạy tay: python -X utf8 -m core.nao_bo_phan ngu"})
    return ra


def dong_bao_cao(goc: str, bay: Optional[_dt.datetime] = None) -> List[str]:
    """≤ 4 dòng cho mục Skill của báo cáo ngày: đã chạy 24 giờ · nên chạy (chờ chủ) · tạm dừng · sẽ chạy lượt tới."""
    bay = bay or kn._gio()  # noqa: SLF001
    so = doc_so(goc)
    moc = _luc(bay - _dt.timedelta(hours=24))
    chay = [x for x in so if x.get("quyet") in CHAY + ("hoan",) and str(x.get("luc") or "") >= moc]
    ds = danh_gia(goc, bay, so=so)

    def gop(muc) -> str:
        nhom: Dict[str, List[str]] = {}
        for ma, chu in muc:
            nhom.setdefault(ma, []).append(chu)
        return " · ".join("{0} {1}".format(ma, ", ".join(dict.fromkeys(v))) for ma, v in sorted(nhom.items()))
    ra = []
    if chay:
        ra.append("- Tự kích hoạt 24 giờ: " + gop((x["ma"], "{0} {1}".format(x.get("kenh") or "máy", NHAN.get(x["quyet"])))
                                                 for x in chay))
    for q, nhan in (("nen_chay", "Nên chạy (chờ chủ duyệt)"), ("tam_dung", "Tạm dừng (hỏng 3 lần)"),
                    ("se_chay", "Sẽ chạy lượt tới")):
        muc = [(x["ma"], x["kenh"] or "máy") for x in ds if x["quyet"] == q]
        if muc:
            ra.append("- {0}: {1}".format(nhan, gop(muc)))
    return ra


def lenh_lich(goc: str, py: str = "") -> str:
    """Dòng schtasks đăng ký `ShopAPI-KyNang` (mỗi giờ phút :35, pythonw không cửa sổ, đứng ở gốc tool để `-m` chạy).
    KHÔNG tự đăng ký — chủ chạy dòng này (hoặc đặt bằng Task Scheduler)."""
    if not py:
        try:
            from core.loi_tat import _pythonw_cho  # noqa: PLC0415
            py = _pythonw_cho(goc)
        except Exception:  # noqa: BLE001
            py = sys.executable
    tr = 'cmd /c cd /d \\"{0}\\" && \\"{1}\\" -X utf8 -m core.ky_nang tu-kich-hoat'.format(goc, py)
    return 'schtasks /Create /TN {0} /SC HOURLY /MO 1 /ST 00:35 /F /TR "{1}"'.format(TEN_TAC_VU, tr)
