"""KHO CHROME (20/10/2026) — `<cha của MyTool>\\kho\\`: Chrome Portable MỚI chủ thả vào (đã đăng nhập Gmail bằng tay) để
thay kênh hỏng / mở rộng, cạnh Chrome của các kênh đã trả kho (`core/tra_kho.py`).

Chủ: tên thư mục Chrome mới tuỳ ý (không phải mã kênh). Máy KHÔNG bao giờ gõ mật khẩu/2FA hay tự đăng nhập Google —
đăng nhập là việc của chủ; Chrome chưa đăng nhập thì bỏ qua + báo "Việc của bạn".

Một thư mục trong kho là Chrome MỚI dùng được khi:
  * có `<TÊN>\\<TÊN>.exe` (launcher Chrome Portable) + `<TÊN>\\App\\Chrome-bin\\chrome.exe`;
  * `<TÊN>` không phải mã kênh trong CHANNEL/ (Chrome của kênh trả kho nằm đây để còn lấy lại);
  * chưa có trong sổ `kho\\_da-dung.json` (đã giao cho kênh nào);
  * hồ sơ `Data\\profile\\Default` có phiên Google/YouTube (đọc TÊN cookie trong bản sao CSDL — không mở Chrome,
    không đọc giá trị cookie).

`lap_dat` dời (đổi tên, cùng ổ) `kho\\<TÊN>` → `<cha>\\<MÃ MỚI>` và đổi launcher thành `<MÃ MỚI>.exe` (cùng `<TÊN>.ini`
nếu có — nếp PortableApps; `mo_kenh.chep_chrome_portable` cũng chỉ đổi launcher). Không bao giờ xoá, không đè.

    python -m core.kho_chrome quet          # chỉ đọc: liệt kê kho + phân loại
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_SO = "_da-dung.json"
#: Cookie cho biết hồ sơ có phiên Google (đăng nhập Gmail) hoặc YouTube. Chỉ đọc TÊN.
COOKIE_GOOGLE = ("SID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID")


def thu_muc_kho(goc: str) -> str:
    from .tra_kho import thu_muc_kho as _tm  # noqa: PLC0415

    return _tm(goc)


def _doc_json(duong: str) -> Dict[str, Any]:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def doc_so(goc: str) -> Dict[str, Any]:
    """Sổ Chrome đã giao: {tên thư mục kho: {kenh, luc}}."""
    return _doc_json(os.path.join(thu_muc_kho(goc), TEP_SO))


def _ghi_so(goc: str, so: Dict[str, Any]) -> None:
    duong = os.path.join(thu_muc_kho(goc), TEP_SO)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(so, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def da_dang_nhap(duong_exe: str) -> Tuple[Optional[bool], str]:
    """Hồ sơ Chrome Portable có phiên Google (Gmail) hoặc YouTube chưa — TÊN cookie trong bản sao CSDL cookie, không
    mở Chrome. (True|False|None khi không đọc được, lý do)."""
    d = os.path.join(os.path.dirname(duong_exe), "Data", "profile", "Default")
    for p in (os.path.join(d, "Network", "Cookies"), os.path.join(d, "Cookies")):
        if not os.path.isfile(p):
            continue
        fd, t = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        try:
            shutil.copyfile(p, t)
            con = sqlite3.connect(t)
            try:
                yt = con.execute("select 1 from cookies where name='LOGIN_INFO' and host_key like '%youtube.com' limit 1").fetchone()
                gg = con.execute("select 1 from cookies where host_key like '%google.com' and name in ({0}) limit 1".format(
                    ",".join("?" * len(COOKIE_GOOGLE))), COOKIE_GOOGLE).fetchone()
            finally:
                con.close()
            if yt or gg:
                return True, "có phiên " + ("YouTube" if yt else "Google")
            return False, "hồ sơ chưa có phiên Google/YouTube"
        except (OSError, sqlite3.Error) as e:
            return None, "không đọc được cookie: {0}".format(str(e)[:80])
        finally:
            try:
                os.remove(t)
            except OSError:
                pass
    return False, "Chrome chưa chạy lần nào (chưa có hồ sơ)"


def _ma_kenh_da_co(goc: str) -> set:
    """Mọi mã kênh (kể cả trả kho) — tên thư mục kho trùng mã kênh là Chrome của kênh đó, không phải Chrome mới."""
    d = os.path.join(goc, "CHANNEL")
    try:
        return {k for k in os.listdir(d) if os.path.isdir(os.path.join(d, k))}
    except OSError:
        return set()


def quet(goc: str, kiem: Optional[Callable[[str], Tuple[Optional[bool], str]]] = None) -> List[Dict[str, Any]]:
    """CHỈ ĐỌC. Mỗi thư mục trong kho: {ten, loai, ly_do}. loai: moi (dùng được) | kenh (Chrome của kênh, vd trả kho)
    | da_dung | thieu_launcher | thieu_chrome | chua_dang_nhap | khong_doc_duoc."""
    kho = thu_muc_kho(goc)
    try:
        ten = sorted(os.listdir(kho))
    except OSError:
        return []
    kenh = _ma_kenh_da_co(goc)
    so = doc_so(goc)
    ra: List[Dict[str, Any]] = []
    for t in ten:
        d = os.path.join(kho, t)
        if t.startswith((".", "_")) or not os.path.isdir(d):
            continue
        exe = os.path.join(d, t + ".exe")
        x: Dict[str, Any] = {"ten": t, "loai": "moi", "ly_do": ""}
        if t in kenh:
            x.update(loai="kenh", ly_do="Chrome của kênh {0} (trả kho) — giữ để lấy lại".format(t))
        elif t in so:
            x.update(loai="da_dung", ly_do="đã giao cho kênh {0}".format((so.get(t) or {}).get("kenh") or "?"))
        elif not os.path.isfile(exe):
            x.update(loai="thieu_launcher", ly_do="thiếu {0}.exe (launcher phải trùng tên thư mục)".format(t))
        elif not os.path.isfile(os.path.join(d, "App", "Chrome-bin", "chrome.exe")):
            x.update(loai="thieu_chrome", ly_do="thiếu App\\Chrome-bin\\chrome.exe")
        else:
            ok, ly = (kiem or da_dang_nhap)(exe)
            if ok is None:
                x.update(loai="khong_doc_duoc", ly_do=ly)
            elif not ok:
                x.update(loai="chua_dang_nhap", ly_do=ly)
            else:
                x["ly_do"] = ly
        ra.append(x)
    return ra


def chrome_cua_kenh(goc: str, ma: str) -> str:
    """Tên thư mục kho đã giao cho kênh `ma` ('' nếu chưa)."""
    for t, v in doc_so(goc).items():
        if isinstance(v, dict) and v.get("kenh") == ma:
            return t
    return ""


def giu(goc: str, ten: str, ma: str) -> bool:
    """Ghi sổ: Chrome `ten` giao cho kênh `ma` (TRƯỚC khi dời — sập giữa chừng không giao hai lần). False nếu đã giao
    cho kênh khác."""
    so = doc_so(goc)
    cu = so.get(ten) if isinstance(so.get(ten), dict) else None
    if cu and cu.get("kenh") != ma:
        return False
    so[ten] = {"kenh": ma, "luc": time.strftime("%Y-%m-%d %H:%M")}
    _ghi_so(goc, so)
    return True


def lap_dat(goc: str, ten: str, ma: str) -> Tuple[str, str]:
    """Dời `kho\\<ten>` → `<cha>\\<ma>` + đổi launcher `<ten>.exe` → `<ma>.exe`. Chạy lại an toàn.
    (da_lap | co_san | hong, ghi chú)."""
    cha = os.path.dirname(os.path.abspath(goc))
    nguon = os.path.join(thu_muc_kho(goc), ten)
    dich = os.path.join(cha, ma)
    if os.path.isfile(os.path.join(dich, ma + ".exe")):
        return "co_san", "đã có " + os.path.join(dich, ma + ".exe")
    if not os.path.isdir(dich):
        if not os.path.isdir(nguon):
            return "hong", "không thấy {0} trong kho".format(ten)
        try:
            os.rename(nguon, dich)
        except OSError as e:
            return "hong", "chưa dời được Chrome {0} ({1}) — lượt sau thử lại".format(ten, str(e)[:100])
    # đã dời (lần này hoặc lần trước sập ngay sau khi dời): đổi tên launcher (+ .ini cùng tên nếu có)
    cu = os.path.join(dich, ten + ".exe")
    if not os.path.isfile(cu):
        return "hong", "thư mục {0} đã có nhưng thiếu cả {1}.exe lẫn {2}.exe — không đè, người kiểm tra".format(dich, ma, ten)
    try:
        for duoi in (".ini",):
            if os.path.isfile(os.path.join(dich, ten + duoi)) and not os.path.exists(os.path.join(dich, ma + duoi)):
                os.rename(os.path.join(dich, ten + duoi), os.path.join(dich, ma + duoi))
        os.rename(cu, os.path.join(dich, ma + ".exe"))
    except OSError as e:
        return "hong", "chưa đổi tên launcher ({0}) — lượt sau thử lại".format(str(e)[:100])
    return "da_lap", "Chrome {0} (kho) → {1}".format(ten, os.path.join(dich, ma + ".exe"))


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    a = list(sys.argv[1:] if argv is None else argv) or ["quet"]
    goc = GOC
    if "--goc" in a:
        i = a.index("--goc")
        goc, a = os.path.abspath(a[i + 1]), a[:i] + a[i + 2:]
    print("Kho Chrome: {0}".format(thu_muc_kho(goc)))
    ds = quet(goc)
    for x in ds:
        print("  {0:<24} {1:<15} {2}".format(x["ten"], x["loai"], x["ly_do"]))
    print("=> {0} Chrome mới dùng được".format(sum(1 for x in ds if x["loai"] == "moi")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
