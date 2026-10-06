"""Dữ liệu vòng 4 cho Trung tâm trực quan (06/10/2026) — CHỈ ĐỌC, mỗi nguồn bọc try riêng, có nhớ đệm.

  * `ho_so_tuong(goc, kenh)`   → /tuong.json?kenh=  : hồ sơ «tướng» của một kênh — cấp (giờ xem), quân số (đăng ký),
    dự báo YPP (`core.ypp.du_bao`), chỉ số 28 ngày, lịch sử trận (mỗi video đã lên sóng: ảnh bìa, kết quả 48 giờ từ
    `tu-hoc/van.json`, hiển thị, CTR), chuỗi thắng, cây kỹ năng (`core.ky_nang`), chăm kênh, tín hiệu học.
  * `kinh_te(goc)`             → /kinh-te.json      : ví ShopAPI (chỉ tệp cục bộ `workspace/vi/`), chi hôm nay/hôm qua
    (suy từ lịch sử số dư), trần job cùng lúc ảnh/clip/giọng (log điều phối), lần hết hạn mức gần nhất.
  * `dong_ho(goc)`             → /dong-ho.json      : lịch một ngày của máy, lấy từ cấu hình/mã (không viết cứng).
  * `day_du(goc)`              → /day-du.json       : bình luận đã trả lời hôm nay, kéo chéo + kết quả đo 7 ngày,
    nuôi trang chủ, tín hiệu học, báo cáo sức khoẻ ngày, trận gần đây toàn quân.
  * `duong_anh(goc, loai, kenh, ma)` : ảnh bìa đã chọn / logo kênh — đường đã kiểm chặt, chỉ tệp trên máy.
Không gọi mạng, không ghi tệp.
"""
from __future__ import annotations

import csv
import datetime as _dt
import glob
import io
import json
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

GOC = os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NHO_DEM_GIAY = 300.0
_MA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


# ---------------------------------------------------------------- tiện ích
def _json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _duoi(duong: str, so_byte: int = 400_000) -> List[str]:
    try:
        with open(duong, "rb") as tep:
            tep.seek(0, os.SEEK_END)
            n = tep.tell()
            tep.seek(max(0, n - so_byte))
            du = tep.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    dong = du.splitlines()
    return dong[1:] if n > so_byte else dong


def _csv(duong: str) -> List[Dict[str, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(io.StringIO(tep.read())))
    except (OSError, csv.Error):
        return []


def _so(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _muc(ten: str, ham: Callable[[], Any], ra: Dict[str, Any], loi: Dict[str, str]) -> None:
    try:
        ra[ten] = ham()
    except Exception as e:  # noqa: BLE001
        ra[ten] = None
        loi[ten] = "{0}: {1}".format(type(e).__name__, str(e)[:120])


def cac_kenh(goc: str) -> List[str]:
    d = _json(os.path.join(goc, "vm", "cai-dat-tool.json"))
    return list(((d or {}).get("kenh") or {}).keys()) if isinstance(d, dict) else []


def _yaml_khoa(goc: str, kenh: str, khoa: str) -> str:
    try:
        with open(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8") as tep:
            for dong in tep:
                if dong.startswith(khoa + ":"):
                    return dong.split(":", 1)[1].split("#", 1)[0].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _ten_kenh(goc: str, kenh: str) -> str:
    hs = _json(os.path.join(goc, "CHANNEL", kenh, "thiet-lap", "ho-so.json")) or {}
    return str(hs.get("ten") or "") or _yaml_khoa(goc, kenh, "ten").split(" — ")[0].strip()


# ---------------------------------------------------------------- ảnh (đường kiểm chặt)
def duong_anh(goc: str, loai: str, kenh: str, ma: str = "") -> Optional[str]:
    """`bia` → CHANNEL/<kenh>/ho-so-video/anh/<ma>.jpg ; `logo` → CHANNEL/<kenh>/thiet-lap/logo.png. Kênh phải có
    trong cài đặt, mã chỉ gồm chữ/số/-/_, đường thật phải nằm trong thư mục kênh. Sai bất kỳ → None."""
    if not _MA.match(kenh or "") or kenh not in cac_kenh(goc):
        return None
    goc_kenh = os.path.realpath(os.path.join(goc, "CHANNEL", kenh))
    if loai == "bia":
        if not _MA.match(ma or ""):
            return None
        p = os.path.join(goc_kenh, "ho-so-video", "anh", ma + ".jpg")
    elif loai == "logo":
        p = os.path.join(goc_kenh, "thiet-lap", "logo.png")
    else:
        return None
    p = os.path.realpath(p)
    if os.path.commonpath([goc_kenh, p]) != goc_kenh or not os.path.isfile(p):
        return None
    return p


# ---------------------------------------------------------------- trận (video đã lên sóng)
def _ke_hoach(goc: str, kenh: str) -> Dict[str, Dict[str, str]]:
    ra = {}
    for r in _csv(os.path.join(goc, "CHANNEL", kenh, "ke-hoach-dang", "ke-hoach.csv")):
        ma = (r.get("Mã gói") or "").strip()
        if ma:
            ra[ma] = r
    return ra


def cac_tran(goc: str, kenh: str, bay: _dt.datetime, toi_da: int = 40) -> List[Dict[str, Any]]:
    """Mỗi video đã có hồ sơ (đã bàn giao) = một trận; kết quả 48 giờ lấy từ sổ ván của vòng tự học."""
    thu = os.path.join(goc, "CHANNEL", kenh, "ho-so-video")
    van = _json(os.path.join(goc, "CHANNEL", kenh, "tu-hoc", "van.json")) or {}
    kh = _ke_hoach(goc, kenh)
    ra = []
    for p in glob.glob(os.path.join(thu, "*.json")):
        hs = _json(p)
        if not isinstance(hs, dict):
            continue
        ma = str(hs.get("ma_goi") or os.path.basename(p)[:-5])
        r = kh.get(ma, {})
        ngay = ""
        try:
            ngay = _dt.datetime.strptime((r.get("Ngày đăng") or "").strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            ngay = str(hs.get("lich_dang") or "")[:10]
        if ngay and ngay > bay.strftime("%Y-%m-%d"):
            continue                                          # chưa lên sóng
        cs = hs.get("chi_so") or {}
        moc = next((k for k in ("48h", "72h", "24h") if isinstance(cs.get(k), dict)), "")
        m48 = cs.get(moc) if moc else (hs.get("so_lieu_moi_nhat") or {})
        m48 = m48 if isinstance(m48, dict) else {}
        m7 = cs.get("7d") or {}
        moc = moc or str(m48.get("moc") or "")
        v = van.get(ma) or {}
        ket = {"thang": "thang", "truot": "thua"}.get(v.get("ket48") or "", "")
        if not ket:
            ket = "khong_do" if v.get("khong_do") else "cho"
        ra.append({
            "ma": ma, "tieu_de": str(hs.get("tieu_de") or r.get("Tiêu đề") or "")[:140], "ngay": ngay,
            "gio": (r.get("Giờ đăng") or "").strip(), "video_id": hs.get("video_id") or r.get("Video ID") or "",
            "ket": ket, "ket7": {"thang": "thang", "truot": "thua"}.get(v.get("ket7") or "", ""),
            "hien_thi": _so(m48.get("impressions")), "ctr": _so(m48.get("ctr")), "xem": _so(m48.get("views")), "moc": moc,
            "hien_thi_7d": _so(m7.get("impressions")), "cum": ((v.get("nuoc") or {}).get("cum") or ""),
            "anh": os.path.isfile(os.path.join(thu, "anh", ma + ".jpg")),
        })
    ra.sort(key=lambda x: (x["ngay"] or "", x["ma"]), reverse=True)
    return ra[:toi_da]


def _chuoi(tran: List[Dict[str, Any]]) -> Dict[str, Any]:
    co = [t["ket"] for t in tran if t["ket"] in ("thang", "thua")]           # mới → cũ
    hien, n = (co[0], 0) if co else ("", 0)
    for k in co:
        if k != hien:
            break
        n += 1
    tot, dai = 0, 0
    for k in co:
        dai = dai + 1 if k == "thang" else 0
        tot = max(tot, dai)
    th = co.count("thang")
    return {"so_tran": len(co), "thang": th, "thua": len(co) - th, "ti_le": round(th / len(co) * 100, 1) if co else None,
            "chuoi": n, "chuoi_loai": hien, "chuoi_thang_dai_nhat": tot, "cho": sum(1 for t in tran if t["ket"] == "cho")}


# ---------------------------------------------------------------- hồ sơ tướng
def _chi_so_28(goc: str, kenh: str) -> Dict[str, Any]:
    ds = _csv(os.path.join(goc, "CHANNEL", kenh, "chi-so", "kenh-theo-ngay.csv"))
    if not ds:
        return {}
    r = ds[-1]
    return {"luc": r.get("Lúc chụp", ""), "xem": _so(r.get("Lượt xem")), "gio": _so(r.get("Giờ xem")),
            "dang_ky": _so(r.get("Đăng ký")), "hien_thi": _so(r.get("Lượt hiển thị")), "ctr": _so(r.get("Tỷ lệ bấm")),
            "chuoi_gio": [_so(x.get("Giờ xem")) for x in ds[-30:]]}


def cay_ky_nang(goc: str, kenh: str) -> List[Dict[str, Any]]:
    from core import ky_nang  # noqa: PLC0415
    ra = []
    for k, tt, gc in ky_nang.kiem_kenh(goc, kenh):
        ra.append({"ma": k.ma, "ten": k.ten, "loai": k.loai, "mo_ta": k.mo_ta, "lenh": str(k.lenh or "").replace("<kenh>", kenh)[:200],
                   "can": list(k.can or []), "tt": tt, "ghi_chu": str(gc or "")[:200]})
    return ra


def _nuoi(goc: str, kenh: str) -> Dict[str, Any]:
    d = _json(os.path.join(goc, "vm", "logs", "nuoi-trang-chu", kenh + ".json"))
    if not isinstance(d, dict):
        return {}
    lan = [x for x in (d.get("lan_do") or []) if isinstance(x, dict)]
    cuoi = lan[-1] if lan else {}
    return {"trang_thai": d.get("trang_thai") or "", "pct_chu_de": cuoi.get("pct_chu_de"), "pct_ngach": cuoi.get("pct_ngach"),
            "luc": cuoi.get("luc") or "", "so_lan_do": len(lan), "so_phien": len(d.get("phien") or []),
            "chuoi": [x.get("pct_chu_de") for x in lan[-12:]]}


def binh_luan_hom_nay(goc: str, bay: _dt.datetime) -> Dict[str, Dict[str, int]]:
    hom = bay.strftime("%Y-%m-%d")
    mau = re.compile(r"kênh (\S+): trả lời (\d+) · bỏ qua (\d+) · lỗi (\d+)")
    ra: Dict[str, Dict[str, int]] = {}
    for dong in _duoi(os.path.join(goc, "vm", "logs", "cmt-dom.log")):
        if not dong.startswith(hom):
            continue
        m = mau.search(dong)
        if m:
            x = ra.setdefault(m.group(1), {"tra_loi": 0, "bo_qua": 0, "loi": 0, "phien": 0})
            x["tra_loi"] += int(m.group(2)); x["bo_qua"] += int(m.group(3)); x["loi"] += int(m.group(4)); x["phien"] += 1
    return ra


def _hoc(goc: str, kenh: str, bay: _dt.datetime) -> Dict[str, Any]:
    from core import tu_hoc  # noqa: PLC0415
    t = tu_hoc.tin_hieu_thieu(goc, kenh, bay.timestamp())
    return {k: (len(v) if isinstance(v, (list, tuple, set)) else v) for k, v in (t or {}).items()}


def ho_so_tuong(goc: Optional[str] = None, kenh: str = "", bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    goc = goc or GOC
    bay = bay_gio or _dt.datetime.now()
    if kenh not in cac_kenh(goc):
        return {"loi": "không có kênh này"}
    ra: Dict[str, Any] = {"kenh": kenh, "luc": bay.strftime("%Y-%m-%d %H:%M:%S")}
    loi: Dict[str, str] = {}
    _muc("ten", lambda: _ten_kenh(goc, kenh), ra, loi)
    _muc("logo", lambda: duong_anh(goc, "logo", kenh) is not None, ra, loi)
    _muc("chi_so", lambda: _chi_so_28(goc, kenh), ra, loi)

    def _ypp():
        from core import ypp  # noqa: PLC0415
        return ypp.du_bao(goc, kenh, bay)
    _muc("ypp", _ypp, ra, loi)
    _muc("tran", lambda: cac_tran(goc, kenh, bay), ra, loi)
    ra["thanh_tich"] = _chuoi(ra["tran"] or [])
    ctr = sorted(t["ctr"] for t in (ra["tran"] or []) if t.get("ctr") is not None)
    ra["thanh_tich"]["ctr_trung_vi"] = ctr[len(ctr) // 2] if ctr else None
    _muc("ky_nang", lambda: cay_ky_nang(goc, kenh), ra, loi)
    _muc("nuoi", lambda: _nuoi(goc, kenh), ra, loi)
    _muc("binh_luan", lambda: binh_luan_hom_nay(goc, bay).get(kenh) or {}, ra, loi)
    _muc("hoc", lambda: _hoc(goc, kenh, bay), ra, loi)
    _muc("nhip_dang", lambda: _yaml_khoa(goc, kenh, "nhip_dang") or _yaml_khoa(goc, kenh, "gio_dang"), ra, loi)
    ra["loi_nguon"] = loi
    return ra


# ---------------------------------------------------------------- kinh tế
_LUC = re.compile(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\]")
_TRAN = re.compile(r"cổng khai trần job cùng lúc: ảnh (\d+), clip (\d+), giọng (\d+)")


def kinh_te(goc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    goc = goc or GOC
    bay = bay_gio or _dt.datetime.now()
    ra: Dict[str, Any] = {"luc": bay.strftime("%Y-%m-%d %H:%M:%S")}
    loi: Dict[str, str] = {}

    def _vi():
        sd = _json(os.path.join(goc, "workspace", "vi", "so-du.json")) or {}
        tt = _json(os.path.join(goc, "workspace", "vi", "trang-thai.json")) or {}
        dg = tt.get("danh_gia") or {}
        hom, qua = bay.strftime("%Y-%m-%d"), (bay - _dt.timedelta(days=1)).strftime("%Y-%m-%d")
        chi = {hom: 0.0, qua: 0.0}
        nap = {hom: 0.0, qua: 0.0}
        truoc = None
        chuoi = []
        for dong in _duoi(os.path.join(goc, "workspace", "vi", "lich-su-so-du.jsonl"), 600_000):
            try:
                x = json.loads(dong)
                luc, vnd = float(x["luc"]), float(x["vnd"])
            except (ValueError, KeyError, TypeError):
                continue
            ngay = _dt.datetime.fromtimestamp(luc).strftime("%Y-%m-%d")
            if truoc is not None and ngay in chi:
                d = vnd - truoc
                (chi if d < 0 else nap)[ngay] += abs(d)
            truoc = vnd
            chuoi.append((luc, vnd))
        moc = bay.timestamp() - 86400 * 3
        return {"so_du": _so(sd.get("vnd")), "luc": sd.get("luc"), "chi_hom_nay": round(chi[hom]), "chi_hom_qua": round(chi[qua]),
                "nap_hom_nay": round(nap[hom]), "uoc_video": _so(dg.get("uoc_video_vnd")), "chi_ngay_uoc": _so(dg.get("chi_ngay_vnd")),
                "du_video": dg.get("du_video"), "ngay_con": dg.get("ngay_con"), "muc": dg.get("muc") or "", "chan": bool(tt.get("chan")),
                "ly_do_chan": str(tt.get("ly_do_chan") or "")[:160],
                "chuoi": [round(v) for l, v in chuoi if l >= moc][::max(1, len([1 for l, _ in chuoi if l >= moc]) // 48)]}
    _muc("vi", _vi, ra, loi)

    def _cong():
        tot = None
        for p in glob.glob(os.path.join(goc, "workspace", "tu-chay", "dieu-phoi-*.log")):
            for dong in reversed(_duoi(p, 200_000)):
                m = _TRAN.search(dong)
                if m:          # dòng không mang giờ → lấy giờ sửa tệp log (log mới nhất thắng)
                    lm = _LUC.search(dong)
                    luc = lm.group(1) if lm else _dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")
                    if tot is None or luc > tot["luc"]:
                        tot = {"luc": luc, "anh": int(m.group(1)), "clip": int(m.group(2)), "giong": int(m.group(3))}
                    break
        return tot or {}
    _muc("tran_job", _cong, ra, loi)

    def _han_muc():
        hom = bay.strftime("%Y-%m-%d")
        ra2 = {"anh": "", "clip": "", "giong": ""}
        for dong in _duoi(os.path.join(goc, "workspace", "tu-chay", "tu-chay.log"), 800_000):
            if not dong.startswith("[" + hom) or "hết hạn mức" not in dong:
                continue
            thap = dong.lower()
            loai = "clip" if "clip" in thap else "giong" if ("giọng" in thap or "tts" in thap) else "anh" if ("ảnh" in thap or "image" in thap) else ""
            if loai:
                ra2[loai] = dong[1:20]
        return ra2
    _muc("het_han_muc", _han_muc, ra, loi)

    def _chi_ngay():
        ds = sorted(glob.glob(os.path.join(goc, "workspace", "chi-phi", "????-??-??.json")))[-7:]
        out = []
        for p in ds:
            d = _json(p) or {}
            out.append({"ngay": d.get("ngay") or os.path.basename(p)[:10], "tong_micro": d.get("tong_micro"),
                        "so_video_ban_giao": d.get("so_video_ban_giao")})
        return out
    _muc("chi_phi_ngay", _chi_ngay, ra, loi)
    ra["loi_nguon"] = loi
    return ra


# ---------------------------------------------------------------- đồng hồ một ngày
def _hang_so(goc: str, tep: str, ten: str) -> Optional[str]:
    try:
        with open(os.path.join(goc, tep), "r", encoding="utf-8") as f:
            m = re.search(r"^" + ten + r"\s*=\s*(.+?)\s*(?:#.*)?$", f.read(), re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def _hhmm(s: Any) -> str:
    m = re.search(r"(\d{1,2}):(\d{2})", str(s or ""))
    return "{0:02d}:{1}".format(int(m.group(1)), m.group(2)) if m else ""


def _cong_phut(hhmm: str, phut: int) -> str:
    h, m = map(int, hhmm.split(":"))
    t = (h * 60 + m + phut) % 1440
    return "{0:02d}:{1:02d}".format(t // 60, t % 60)


def dong_ho(goc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    goc = goc or GOC
    bay = bay_gio or _dt.datetime.now()
    ev: List[Dict[str, Any]] = []
    loi: Dict[str, str] = {}
    cai = _json(os.path.join(goc, "vm", "cai-dat-tool.json")) or {}
    kenh = list((cai.get("kenh") or {}).keys())
    tam: Dict[str, Any] = {}

    def _quet():
        g0 = _hhmm(_hang_so(goc, os.path.join("vm", "agent.py"), "QUET_NGAY_GIO_MAC_DINH")) or "02:10"
        cach = int(re.sub(r"\D", "", _hang_so(goc, os.path.join("vm", "agent.py"), "QUET_NGAY_CACH_PHUT") or "30") or 30)
        for i, k in enumerate(kenh):
            ch = (cai.get("kenh") or {}).get(k) or {}
            g = _hhmm(ch.get("quet_ngay_gio")) or _cong_phut(g0, i * int(ch.get("quet_ngay_cach_phut") or cach))
            ev.append({"gio": g, "dai": 25, "loai": "quet", "ten": "Quét ngày", "kenh": k})
        return True
    _muc("quet", _quet, tam, loi)

    def _nao():
        import inspect  # noqa: PLC0415
        from core import lich_tu_chay  # noqa: PLC0415
        g = _hhmm(inspect.signature(lich_tu_chay.dang_ky_nao).parameters["gio"].default)
        ev.append({"gio": g, "dai": 20, "loai": "nao", "ten": "Bộ não họp", "kenh": ""})
        return True
    _muc("nao", _nao, tam, loi)

    def _dang():
        gio = {}
        for k in kenh:
            g = _hhmm(_yaml_khoa(goc, k, "nhip_dang") or _yaml_khoa(goc, k, "gio_dang"))
            if g:
                gio.setdefault(g, []).append(k)
        for g, ds in gio.items():
            ev.append({"gio": g, "dai": 10, "loai": "len_song", "ten": "Video lên sóng", "kenh": ",".join(ds)})
            ev.append({"gio": g, "dai": 0, "loai": "san_xuat", "ten": "Mở cửa sản xuất video ngày mai", "kenh": ",".join(ds)})
        return True
    _muc("dang", _dang, tam, loi)

    def _bao_cao():
        from core import bao_cao_ngay  # noqa: PLC0415
        h, m = bao_cao_ngay.GIO_GUI
        ev.append({"gio": "{0:02d}:{1:02d}".format(h, m), "dai": 5, "loai": "bao_cao", "ten": "Báo cáo sức khoẻ", "kenh": ""})
        return True
    _muc("bao_cao", _bao_cao, tam, loi)

    def _phien():
        gio = {}
        for k in kenh:
            ch = (cai.get("kenh") or {}).get(k) or {}
            for g in str(ch.get("gio_phien") or cai.get("gio_phien") or "").split(","):
                g = _hhmm(g)
                if g:
                    gio.setdefault(g, []).append(k)
        for g, ds in gio.items():
            ev.append({"gio": g, "dai": 40, "loai": "phien", "ten": "Phiên kênh: kiểm máy đăng, bình luận", "kenh": ",".join(ds)})
        return True
    _muc("phien", _phien, tam, loi)

    def _keo():
        s = _hang_so(goc, os.path.join("vm", "agent.py"), "GIO_KEO_CHEO") or ""
        m = re.findall(r"\d+", s)
        if len(m) >= 2:
            ev.append({"gio": "{0:02d}:00".format(int(m[0])), "den": "{0:02d}:00".format(int(m[1])), "loai": "keo_cheo",
                       "ten": "Kéo view chéo (1 lần trong khung)", "kenh": ""})
        return True
    _muc("keo", _keo, tam, loi)

    def _clip():
        thu = os.path.join(goc, "workspace", "tu-chay", "cho-clip")
        for p in sorted(glob.glob(os.path.join(thu, "*.json"))):
            d = _json(p) or {}
            try:
                tuoi = bay.timestamp() - float(d.get("luc") or 0)
            except (TypeError, ValueError):
                continue
            han = str(d.get("han") or "")
            if 0 <= tuoi <= 45 * 60 and han[:10] == bay.strftime("%Y-%m-%d"):
                ev.append({"gio": _hhmm(han[11:16]), "dai": 0, "loai": "han_clip", "ten": "Hạn chót chờ kho clip", "kenh": d.get("kenh") or ""})
        return True
    _muc("clip", _clip, tam, loi)
    ev = [e for e in ev if e.get("gio")]
    ev.sort(key=lambda e: (e["gio"], e["loai"], e.get("kenh") or ""))
    lap = [{"ten": "Gác tổng: kiểm cả máy, tự sửa, báo động", "moi_phut": 15}, {"ten": "Điều phối sinh lượt sản xuất", "moi_phut": 10}]
    return {"luc": bay.strftime("%Y-%m-%d %H:%M:%S"), "su_kien": ev, "lap": lap, "loi_nguon": loi}


# ---------------------------------------------------------------- đầy đủ
def day_du(goc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    goc = goc or GOC
    bay = bay_gio or _dt.datetime.now()
    kenh = cac_kenh(goc)
    ra: Dict[str, Any] = {"luc": bay.strftime("%Y-%m-%d %H:%M:%S"), "kenh": kenh}
    loi: Dict[str, str] = {}
    _muc("binh_luan", lambda: binh_luan_hom_nay(goc, bay), ra, loi)

    def _keo():
        d = _json(os.path.join(goc, "workspace", "keo-cheo", "da-them.json")) or {}
        out = []
        for x in (d.get("muc") or [])[-40:]:
            if not isinstance(x, dict):
                continue
            do = x.get("do_sau") or {}
            dd = x.get("du_doan") or {}
            out.append({"ngay": x.get("ngay") or "", "kenh_chu": x.get("kenh_chu") or "", "kenh_video": x.get("kenh_video") or "",
                        "tieu_de": str(x.get("tieu_de") or "")[:120], "danh_sach_phat": str(x.get("danh_sach_phat") or "")[:80],
                        "ket": str(x.get("ket") or "")[:40], "cum": x.get("cum") or "", "kiem_sau_ngay": dd.get("kiem_sau_ngay"),
                        "do": {"ket": do.get("ket"), "tang": do.get("tang"), "tang_doi_chung_tv": do.get("tang_doi_chung_tv"), "luc": do.get("luc")} if do else None})
        return out[::-1]
    _muc("keo_cheo", _keo, ra, loi)
    _muc("nuoi", lambda: {k: _nuoi(goc, k) for k in kenh}, ra, loi)
    hoc: Dict[str, Any] = {}
    for k in kenh:
        try:
            hoc[k] = _hoc(goc, k, bay)
        except Exception as e:  # noqa: BLE001
            loi["hoc:" + k] = str(e)[:100]
    ra["hoc"] = hoc

    def _bao():
        ds = sorted(glob.glob(os.path.join(goc, "workspace", "bao-cao-ngay", "????-??-??.md")))
        if not ds:
            return {"ngay": [], "noi_dung": ""}
        with open(ds[-1], "r", encoding="utf-8", errors="replace") as tep:
            noi = tep.read(30_000)
        try:
            from core import nao_truc_quan  # noqa: PLC0415
            noi = nao_truc_quan.che(noi)
        except Exception:  # noqa: BLE001
            pass
        return {"ngay": [os.path.basename(p)[:10] for p in ds[-14:]], "moi_nhat": os.path.basename(ds[-1])[:10], "noi_dung": noi}
    _muc("bao_cao", _bao, ra, loi)
    tran: Dict[str, Any] = {}
    for k in kenh:
        try:
            ds = cac_tran(goc, k, bay, 30)
            tran[k] = {"tran": ds[:8], "thanh_tich": _chuoi(ds),
                       "max_hien_thi": max([t["hien_thi_7d"] or t["hien_thi"] or 0 for t in ds] or [0])}
        except Exception as e:  # noqa: BLE001
            loi["tran:" + k] = str(e)[:100]
    ra["tran"] = tran
    ra["loi_nguon"] = loi
    return ra


# ---------------------------------------------------------------- nhớ đệm
_NHO: Dict[str, Any] = {}
_KHOA = threading.Lock()


def nho(khoa: str, ham: Callable[[], Dict[str, Any]], han: float = NHO_DEM_GIAY) -> Dict[str, Any]:
    with _KHOA:
        c = _NHO.get(khoa)
        if c and time.time() - c[0] <= han:
            return c[1]
    du = ham()
    with _KHOA:
        _NHO[khoa] = (time.time(), du)
    return du


if __name__ == "__main__":
    import sys
    k = sys.argv[1] if len(sys.argv) > 1 else (cac_kenh(GOC) or [""])[0]
    for ten, d in (("tuong", ho_so_tuong(GOC, k)), ("kinh_te", kinh_te()), ("dong_ho", dong_ho()), ("day_du", day_du())):
        print("=====", ten)
        print(json.dumps(d, ensure_ascii=False)[:2500])
