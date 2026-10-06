"""TRUNG TÂM TRỰC QUAN (05/10/2026) — bản đồ sống của VPS: dây chuyền, từng kênh, máy, bộ não, sự kiện.

Chỉ ĐỌC trạng thái tool đang ghi (kế hoạch đăng, lượt sản xuất, điều phối, quét ngày, danh mục skill, nhật ký) —
không bấm, không sửa gì. Máy chủ nhỏ RIÊNG (không đụng trạm 8765 đang chạy trong MyTool):

    python -m core.truc_quan            # mở http://127.0.0.1:8790  (trang: ui_web/truc-quan.html)
    python -m core.truc_quan --json     # in ảnh chụp dữ liệu (kiểm)
    python -m core.truc_quan --cong 8791   # cổng khác (mặc định 8790)
Trang: `/` chiến trường · `/hau-can` dây chuyền · `/nao` bộ não (`core.nao_truc_quan`) · `/gioi-thieu` trình chiếu giới thiệu
Tĩnh: `/vendor/...` = ui_web/vendor (he-thong.css, chung.js, phông woff2 tự chứa — không CDN; máy IPv6-only).
"""
from __future__ import annotations

import ctypes
import datetime as _dt
import json
import os
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VM = os.path.join(GOC, "vm")
# 8790 (06/10/2026): 8765–8781 là cổng trạm/agent/KHOÁ máy DOM (8770 = khoá máy đăng DOM — từng bị trung tâm
# chiếm làm máy đăng thoát mã 4). Không dùng cổng trong dải đó.
CONG = 8790
KHAU = ("kich-ban", "giong-doc", "phu-de", "bang-canh", "anh", "clip", "thumbnail", "dung")
TEN_KHAU = {"kich-ban": "Kịch bản", "giong-doc": "Giọng đọc", "phu-de": "Phụ đề", "bang-canh": "Bảng cảnh",
            "anh": "Ảnh cảnh", "clip": "Clip", "thumbnail": "Ảnh bìa", "dung": "Dựng video"}


def _json(*phan) -> dict:
    try:
        with open(os.path.join(*phan), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _duoi(duong: str, n: int = 400) -> List[str]:
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            return tep.read().splitlines()[-n:]
    except OSError:
        return []


def _ram_gb() -> Dict[str, float]:
    class M(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("tong", ctypes.c_ulonglong),
                    ("trong", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                    ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
    try:
        m = M()
        m.dwLength = ctypes.sizeof(M)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return {"tong": round(m.tong / 2 ** 30, 1), "trong": round(m.trong / 2 ** 30, 1)}
    except Exception:  # noqa: BLE001
        return {"tong": 0.0, "trong": 0.0}


def _cac_kenh() -> List[str]:
    return sorted((_json(VM, "cai-dat-tool.json").get("kenh") or {}).keys())


def _ten_kenh(kenh: str) -> str:
    hs = _json(GOC, "CHANNEL", kenh, "thiet-lap", "ho-so.json")
    if hs.get("ten"):
        return str(hs["ten"])
    try:
        with open(os.path.join(GOC, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8") as tep:
            for dong in tep:
                if dong.startswith("ten:"):
                    return dong.split(":", 1)[1].strip().strip('"').split(" — ")[0].strip()
    except OSError:
        pass
    return ""


def _video_mai(kenh: str, tu_ngay: Optional[_dt.date] = None) -> Dict[str, Any]:
    """Video lên sóng SỚM NHẤT từ `tu_ngay` (mặc định ngày mai; bỏ dòng «Bỏ»): mã, ngày, tiêu đề, trạng thái."""
    try:
        sys.path.insert(0, GOC)
        from core import ke_hoach_dang  # noqa: PLC0415
        cot, hang = ke_hoach_dang.doc_bang(GOC, kenh)
    except Exception:  # noqa: BLE001
        return {}
    if not cot:
        return {}
    o = {c: cot.index(c) for c in cot}

    def g(r, c):
        return r[o[c]].strip() if c in o and o[c] < len(r) else ""
    mai = tu_ngay or (_dt.date.today() + _dt.timedelta(days=1))
    ung = []
    for r in hang:
        try:
            d = _dt.datetime.strptime(g(r, "Ngày đăng"), "%d/%m/%Y").date()
        except ValueError:
            continue
        if d >= mai and not g(r, "Trạng thái đăng").startswith("Bỏ"):
            ung.append((d, r))
    if not ung:
        return {"co": False, "ngay": mai.strftime("%d/%m")}
    d, r = min(ung, key=lambda x: x[0])
    tt = g(r, "Trạng thái đăng").upper()
    return {"co": True, "ma": g(r, "Mã gói"), "ngay": d.strftime("%d/%m"), "gio": g(r, "Giờ đăng"),
            "tieu_de": g(r, "Tiêu đề")[:90], "da_hen": tt.startswith("ĐÃ ĐĂNG"), "dang_dang": tt.startswith("ĐANG ĐĂNG")}


def _luot_moi_nhat(kenh: str) -> Dict[str, Any]:
    thu = os.path.join(GOC, "PROJECTS", "AUTO", kenh)
    try:
        ds = [os.path.join(thu, x) for x in os.listdir(thu) if os.path.isfile(os.path.join(thu, x, "trang-thai.json"))]
    except OSError:
        return {}
    if not ds:
        return {}
    p = max(ds, key=lambda x: os.path.getmtime(os.path.join(x, "trang-thai.json")))
    d = _json(p, "trang-thai.json")
    khau = d.get("khau") or {}
    ra = []
    for m in KHAU:
        k = khau.get(m) or {}
        gc = k.get("ghi_chu") or {}
        ra.append({"ma": m, "ten": TEN_KHAU[m], "tt": k.get("trang_thai") or "cho",
                   "xong": gc.get("xong"), "tong": gc.get("tong")})
    return {"luot": d.get("ma_luot") or os.path.basename(p), "khau": ra,
            "cap_nhat": os.path.getmtime(os.path.join(p, "trang-thai.json"))}


def _ky_nang(kenh: str) -> Dict[str, Any]:
    try:
        from core import ky_nang  # noqa: PLC0415
        kq = ky_nang.kiem_kenh(GOC, kenh)
    except Exception:  # noqa: BLE001
        return {}
    dem: Dict[str, int] = {}
    loi = []
    for k, tt, gc in kq:
        dem[tt] = dem.get(tt, 0) + 1
        if tt in ("loi", "thieu") or (tt == "cho" and k.loai == "khoi_tao"):
            loi.append({"ma": k.ma, "ten": k.ten, "tt": tt, "ghi_chu": gc[:90]})
    return {"dem": dem, "can_chu_y": loi[:8]}


def chup() -> Dict[str, Any]:
    """Ảnh chụp toàn máy cho trang trực quan."""
    bay = time.time()
    hom = _dt.date.today().isoformat()
    tt = _json(VM, "trang-thai.json")
    dp = {x.get("ma"): x for x in (_json(GOC, "workspace", "khe", "dieu-phoi.json").get("kenh") or []) if isinstance(x, dict)}
    kenh = []
    for k in _cac_kenh():
        vm_k = (_json(VM, "cai-dat-tool.json").get("kenh") or {}).get(k) or {}
        o_may_khac = str(vm_k.get("cach_dang") or "") == "anh" and not vm_k.get("tu_dang")
        mai = _video_mai(k)
        d = dp.get(k) or {}
        luot = _luot_moi_nhat(k) if d.get("dang_chay") else {}
        khau_dang = next((x for x in luot.get("khau", []) if x["tt"] not in ("xong", "bo_qua")), None) if luot else None
        if o_may_khac:
            tram = "khac"
        elif d.get("dang_chay"):
            tram = "san_xuat" if (khau_dang and khau_dang["tt"] == "dang") or any(
                x["tt"] == "xong" for x in luot.get("khau", [])) else "nghien_cuu"
            if luot and not khau_dang:
                tram = "ban_giao"
        elif mai.get("da_hen"):
            tram = "da_hen"
        elif mai.get("co"):
            tram = "cho_dang"
        else:
            tram = "cho"
        q = tt.get("quet_ngay@{0}@{1}".format(k, hom))
        kn = _ky_nang(k)
        hong = (kn.get("dem") or {}).get("loi", 0)
        kenh.append({
            "ma": k, "ten": _ten_kenh(k), "tram": tram, "o_may_khac": o_may_khac,
            "suc_khoe": "hong" if hong else ("tot" if tram in ("da_hen", "khac") else "dang"),
            "ly_do_dp": str(d.get("ly_do") or "")[:140], "video_mai": mai, "luot": luot,
            "khau_dang": khau_dang, "quet": ("xong" if isinstance(q, dict) and q.get("xong") else
                                            ("chưa đủ ({0} lần)".format(q.get("lan")) if isinstance(q, dict) else "chưa")),
            "phien": tt.get("phien_cuoi@" + k) == hom, "ky_nang": kn,
            "ngon_ngu_tam": os.path.isfile(os.path.join(VM, "logs", "hl-tam", k + ".json")),
        })
    o = shutil.disk_usage(GOC)
    nhip = os.path.join(VM, "logs", "nhip-tim.json")
    tuoi_nhip = bay - os.path.getmtime(nhip) if os.path.isfile(nhip) else None
    su_kien = [x for x in _duoi(os.path.join(VM, "logs", "agent-gui.log"), 300)
               if x[:2].isdigit() and "đang chờ việc nặng" not in x and "INFO:" not in x][-10:]
    sx = [x for x in _duoi(os.path.join(GOC, "workspace", "tu-chay", "tu-chay.log"), 60) if "đã tra" not in x][-6:]
    moc = (_dt.datetime.now() - _dt.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    loi = [x for x in _duoi(os.path.join(GOC, "workspace", "loi-chay-max.md"), 200)
           if x.startswith("- [") and "**nhac**" not in x and x[3:19] >= moc][-5:]
    return {
        "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
        "may": {"ram": _ram_gb(), "o_trong_gb": round(o.free / 2 ** 30, 1), "o_tong_gb": round(o.total / 2 ** 30, 1),
                "agent_song": tuoi_nhip is not None and tuoi_nhip < 300, "nhip_giay": round(tuoi_nhip or -1),
                "dang_dang": os.path.isfile(os.path.join(VM, "logs", "dang-dodang.json"))},
        "nao": {"phien_hom_nay": os.path.isfile(os.path.join(GOC, "nao", "nhat-ky", hom + ".md"))},
        "kenh": kenh, "su_kien": su_kien, "san_xuat": sx, "loi": loi,
    }


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None}
_KHOA = threading.Lock()


def chup_nho(han: float = 20.0) -> Dict[str, Any]:
    with _KHOA:
        if _NHO["du"] is None or time.time() - _NHO["luc"] > han:
            _NHO["du"], _NHO["luc"] = chup(), time.time()
        return _NHO["du"]


_NHO_CT: Dict[str, Any] = {"luc": 0.0, "du": None}


def chien_truong_nho(han: float = 600.0) -> Dict[str, Any]:
    """Số liệu chiến trường (đọc ~20.000 video đối thủ) — nhớ đệm 10 phút."""
    with _KHOA:
        if _NHO_CT["du"] is None or time.time() - _NHO_CT["luc"] > han:
            from core import chien_truong  # noqa: PLC0415
            _NHO_CT["du"], _NHO_CT["luc"] = chien_truong.tinh(), time.time()
        return _NHO_CT["du"]


# Tệp tĩnh giao diện (phông, CSS/JS dùng chung) — chỉ thư mục ui_web/vendor, chỉ đuôi trong danh sách trắng.
VENDOR = os.path.join(GOC, "ui_web", "vendor")
_LOAI_TINH = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".woff2": "font/woff2",
              ".ttf": "font/ttf", ".svg": "image/svg+xml"}


def tep_tinh(duong_url: str, goc: Optional[str] = None) -> Optional[str]:
    """`/vendor/a/b.css?v=1` → đường tuyệt đối trong ui_web/vendor, hoặc None (sai đuôi, lách thư mục, không có)."""
    goc = os.path.realpath(goc or VENDOR)
    con = duong_url.split("?", 1)[0].split("#", 1)[0]
    if not con.startswith("/vendor/"):
        return None
    try:
        from urllib.parse import unquote  # noqa: PLC0415
        con = unquote(con[len("/vendor/"):])
    except Exception:  # noqa: BLE001
        return None
    phan = con.split("/")
    if not con or "\\" in con or ":" in con or "\x00" in con or any(p in ("", ".", "..") for p in phan):
        return None
    if os.path.splitext(con)[1].lower() not in _LOAI_TINH:
        return None
    p = os.path.realpath(os.path.join(goc, *phan))
    if os.path.commonpath([goc, p]) != goc or not os.path.isfile(p):
        return None
    return p


def noi_dung_gioi_thieu(goc: Optional[str] = None) -> Dict[str, Any]:
    """Nội dung bài trình chiếu «Giới thiệu»: tệp RIÊNG của máy `workspace/gioi-thieu/noi-dung.json` (không lên kho
    chung — có số liệu, câu chuyện của máy này); thiếu/hỏng thì bản MẶC ĐỊNH trung tính trong kho
    `ui_web/vendor/gioi-thieu-mac-dinh.json`. Trả kèm `_nguon` = "may" | "mac_dinh"."""
    goc = goc or GOC
    for nguon, p in (("may", os.path.join(goc, "workspace", "gioi-thieu", "noi-dung.json")),
                     ("mac_dinh", os.path.join(VENDOR, "gioi-thieu-mac-dinh.json"))):
        d = _json(p)
        if isinstance(d.get("slides"), list) and d["slides"]:
            d["_nguon"] = nguon
            return d
    return {"_nguon": "trong", "slides": []}


class _Xu(BaseHTTPRequestHandler):
    def log_message(self, *a):  # im lặng
        pass

    def _gui(self, ma: int, loai: str, du: bytes, luu: str = "no-store") -> None:
        self.send_response(ma)
        self.send_header("Content-Type", loai)
        self.send_header("Cache-Control", luu)
        self.end_headers()
        self.wfile.write(du)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/vendor/"):
            p = tep_tinh(self.path)
            if not p:
                return self._gui(404, "text/plain; charset=utf-8", b"khong co")
            duoi = os.path.splitext(p)[1].lower()
            with open(p, "rb") as tep:      # phông để lâu; CSS/JS nhỏ thì luôn hỏi lại (đổi giao diện là thấy ngay)
                return self._gui(200, _LOAI_TINH[duoi], tep.read(),
                                 "max-age=604800" if duoi in (".woff2", ".ttf") else "no-cache")
        if self.path.startswith("/chien-truong.json"):
            try:
                return self._gui(200, "application/json; charset=utf-8",
                                 json.dumps(chien_truong_nho(), ensure_ascii=False).encode("utf-8"))
            except Exception as loi:  # noqa: BLE001
                return self._gui(500, "application/json", json.dumps({"loi": str(loi)[:200]}).encode("utf-8"))
        if self.path.startswith("/chien-truong-lich-su.json"):      # chuỗi ảnh chụp theo ngày (mặc định 60 ngày)
            try:
                from core import chien_truong_lich_su  # noqa: PLC0415
                return self._gui(200, "application/json; charset=utf-8",
                                 json.dumps(chien_truong_lich_su.doc_lich_su(GOC, 60), ensure_ascii=False).encode("utf-8"))
            except Exception as loi:  # noqa: BLE001
                return self._gui(500, "application/json", json.dumps({"loi": str(loi)[:200]}).encode("utf-8"))
        if self.path.startswith("/nao.json"):      # trang Não: hành động, phiên, trí nhớ, bài học (nhớ đệm 5 phút)
            try:
                from core import nao_truc_quan  # noqa: PLC0415
                return self._gui(200, "application/json; charset=utf-8",
                                 json.dumps(nao_truc_quan.tinh_nho(), ensure_ascii=False).encode("utf-8"))
            except Exception as loi:  # noqa: BLE001
                return self._gui(500, "application/json", json.dumps({"loi": str(loi)[:200]}).encode("utf-8"))
        if self.path.startswith(("/anh-bia/", "/logo/")):     # ảnh bìa đã chọn / logo kênh — chỉ tệp trên máy, đường kiểm chặt
            from core import tuong_truc_quan as tq4  # noqa: PLC0415
            from urllib.parse import unquote  # noqa: PLC0415
            phan = unquote(self.path.split("?", 1)[0]).strip("/").split("/")
            p = None
            if phan[0] == "anh-bia" and len(phan) == 3 and phan[2].endswith(".jpg"):
                p = tq4.duong_anh(tq4.GOC, "bia", phan[1], phan[2][:-4])
            elif phan[0] == "logo" and len(phan) == 2 and phan[1].endswith(".png"):
                p = tq4.duong_anh(tq4.GOC, "logo", phan[1][:-4])
            if not p:
                return self._gui(404, "text/plain; charset=utf-8", b"khong co")
            with open(p, "rb") as tep:
                return self._gui(200, "image/jpeg" if p.endswith(".jpg") else "image/png", tep.read(), "max-age=3600")
        for duong, ten_ham in (("/tuong.json", "ho_so_tuong"), ("/kinh-te.json", "kinh_te"), ("/dong-ho.json", "dong_ho"),
                               ("/day-du.json", "day_du")):
            if self.path.startswith(duong):        # dữ liệu vòng 4 (nhớ đệm 5 phút, mỗi nguồn bọc riêng)
                try:
                    from core import tuong_truc_quan as tq4  # noqa: PLC0415
                    from urllib.parse import parse_qs, urlsplit  # noqa: PLC0415
                    kenh = (parse_qs(urlsplit(self.path).query).get("kenh") or [""])[0]
                    ham = getattr(tq4, ten_ham)
                    du = tq4.nho(ten_ham + ":" + kenh, (lambda: ham(tq4.GOC, kenh)) if ten_ham == "ho_so_tuong" else (lambda: ham(tq4.GOC)))
                    return self._gui(200, "application/json; charset=utf-8", json.dumps(du, ensure_ascii=False).encode("utf-8"))
                except Exception as loi:  # noqa: BLE001
                    return self._gui(500, "application/json", json.dumps({"loi": str(loi)[:200]}).encode("utf-8"))
        if self.path.startswith("/gioi-thieu.json"):      # nội dung trình chiếu (riêng máy → mặc định)
            return self._gui(200, "application/json; charset=utf-8",
                             json.dumps(noi_dung_gioi_thieu(), ensure_ascii=False).encode("utf-8"))
        if self.path.startswith("/su-kien.json"):      # chiến báo: video ta lên sóng, lệnh não, sự cố, kho clip (5 phút)
            try:
                from core import su_kien_truc_quan  # noqa: PLC0415
                return self._gui(200, "application/json; charset=utf-8",
                                 json.dumps(su_kien_truc_quan.tinh_nho(), ensure_ascii=False).encode("utf-8"))
            except Exception as loi:  # noqa: BLE001
                return self._gui(500, "application/json", json.dumps({"loi": str(loi)[:200]}).encode("utf-8"))
        if self.path.startswith("/du-lieu.json"):
            try:
                return self._gui(200, "application/json; charset=utf-8",
                                 json.dumps(chup_nho(), ensure_ascii=False).encode("utf-8"))
            except Exception as loi:  # noqa: BLE001
                return self._gui(500, "application/json", json.dumps({"loi": str(loi)[:200]}).encode("utf-8"))
        ten = ("truc-quan.html" if self.path.startswith("/hau-can") else
               "nao.html" if self.path.startswith("/nao") else
               "gioi-thieu.html" if self.path.startswith("/gioi-thieu") else "chien-truong.html")
        p = os.path.join(GOC, "ui_web", ten)
        try:
            with open(p, "rb") as tep:
                return self._gui(200, "text/html; charset=utf-8", tep.read())
        except OSError:
            return self._gui(404, "text/plain; charset=utf-8", "thiếu ui_web/{0}".format(ten).encode("utf-8"))


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if "--json" in a:
        print(json.dumps(chup(), ensure_ascii=False, indent=1)[:6000])
        return 0
    cong = CONG
    if "--cong" in a:      # cổng khác (kiểm thử song song máy chủ thật); mặc định vẫn 8790
        cong = int(a[a.index("--cong") + 1])
    sv = ThreadingHTTPServer(("127.0.0.1", cong), _Xu)
    print("Trung tâm trực quan: http://127.0.0.1:{0}".format(cong), flush=True)
    sv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
