# -*- coding: utf-8 -*-
"""core/dong_bo_git.py — đồng bộ HAI CHIỀU với kho chung GitHub (30/09/2026).

Kho chung (`origin`, mặc định `git@github-mytool:manhthang1905-hub/mytool-vps.git`)
là NGUỒN GỐC của mã tool cho MỌI VPS và mọi phiên phát triển. Mỗi VPS làm một
ngách/quốc gia khác; sửa ở máy nào thì đẩy lên, các máy khác tự kéo về.

    python -m core.dong_bo_git ket_noi            # kiểm/sửa đường tới GitHub (NAT64 cho máy chỉ IPv6)
    python -m core.dong_bo_git trang_thai         # nhánh, trước/sau origin, tệp đổi
    python -m core.dong_bo_git day "thông điệp" [--minor|--major] [--chi tệp…]
                                                  # kiểm -> commit -> rebase -> TỰ NÂNG VERSION
                                                  #   + 1 dòng CHANGELOG + tag v<x.y.z> -> push
    python -m core.dong_bo_git kiem               # kiểm có bản mới không (fetch, đọc origin/main:VERSION)
    python -m core.dong_bo_git keo [--ep]         # áp bản mới an toàn (thường do core.cap_nhat_git.nhip sinh ra)
    python -m core.dong_bo_git lui [--tag T]      # quay lại bản trước (tag truoc-cap-nhat-*)
    python -m core.dong_bo_git bai_hoc            # xuất bài học ngách của máy này ra chia-se/
    python -m core.dong_bo_git lich bat|tat       # bat: bảo đảm lịch ShopAPI-GacTong (15') + gỡ lịch 03:40 cũ

═══ MỘT HỆ CẬP NHẬT DUY NHẤT (30/09/2026) ═══

Kiểm định kỳ + quyết định áp nằm ở `core/cap_nhat_git.py` (gác tổng 15' và
giao diện gọi `nhip`). Đường ZIP (`core/cap_nhat_github.py`, `cap-nhat.py`) và
manifest (`core/nguon_cap_nhat.py`) không còn áp mã lên máy nào nữa. Lịch
Windows `ShopAPI-DongBoGit` (kéo 03:40 mỗi ngày) ĐÃ BỎ — `lich bat` tự gỡ nó.

═══ BẬT/TẮT: `cap-nhat.json` (riêng máy, không lên kho) ═══

    {"kho": "manhthang1905-hub/mytool-vps", "nhanh": "main", "tu_dong_cap_nhat": true,
     "dong_bo_git": {"ma_may": "vps1", "cho_toi_da_phut": 180, "theo_doi_phut": 20,
                     "khoi_dong_lai": true, "xuat_bai_hoc": true}}

`tu_dong_cap_nhat` mặc định BẬT (chỉ `false` mới tắt; công tắc "Tự động cập
nhật" trong Cài đặt). `keo --ep` bỏ qua khoá này (nút "Cập nhật ngay") nhưng
KHÔNG bỏ qua khung giờ/máy rảnh.

═══ LUẬT MÁY SẢN XUẤT (CLAUDE.md) ═══

* Không pytest toàn kho — chỉ một NHÓM test nhanh chọn sẵn (`TEST_NHANH`), chạy
  ưu tiên thấp, và chỉ khi khe "nang" trống.
* Chỉ áp mã mới trong khung phút :15–:45, khi `core.an_toan_khoi_dong` đồng ý,
  khe "nang" (`core.khe`) trống, và không lượt AUTO nào ở khâu dựng/phụ đề.
  Trong lúc áp, tool GIỮ khe "nang" để không việc nặng nào chen vào.
* Có sửa cục bộ chưa commit/chưa đẩy thì KHÔNG kéo đè — báo "máy này có sửa
  chưa đẩy".
* Sau khi áp: khởi động lại giao diện (và qua nó, ba con của vm/), theo dõi
  `theo_doi_phut` phút; tiến trình chết lặp hay kiểm khói hỏng thì tự lùi về
  tag `truoc-cap-nhat-<ts>`.

Mọi lệnh ngoài (git, ssh, taskkill, schtasks) đi qua `_chay` — test thay được.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import hashlib
import io
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REMOTE = "origin"
NHANH = "main"
HOST_SSH = "github-mytool"
URL_KHO_MAC_DINH = "git@github-mytool:manhthang1905-hub/mytool-vps.git"
KHOA_SSH_MAC_DINH = "~/.ssh/mytool_vps_deploy"

#: DNS64 công cộng (nat64.net) — trả AAAA tổng hợp cho tên chỉ có IPv4.
DNS64 = ("2a00:1098:2b::1", "2a00:1098:2c::1", "2a01:4f8:c2c:123f::1")

#: Khung phút được phép THAY TỆP MÃ SỐNG (luật vận hành VPS).
KHUNG_PHUT = (15, 45)

TIEN_TO_TAG = "truoc-cap-nhat-"
GIU_TAG = 5

TEN_VIEC_LICH = "ShopAPI-DongBoGit"

MAC_DINH: Dict[str, Any] = {
    "ma_may": "",
    "cho_toi_da_phut": 180,
    "theo_doi_phut": 20,
    "khoi_dong_lai": True,
    "xuat_bai_hoc": True,
}

#: Module chính phải import được (kiểm khói). Thiếu module nào trong cây thì
#: bỏ qua module đó (cây cũ/ mới có thể chưa có).
MODULE_CHINH = (
    "core.khe", "core.an_toan_khoi_dong", "core.tu_chay", "core.auto_khau",
    "core.dieu_phoi", "core.gac_tong", "core.lich_tu_chay", "core.canh_tram",
    "core.giam_sat_vm", "core.kiem_phat_hanh", "core.nguon_cap_nhat",
    "core.dong_bo_git", "core.cap_nhat_git", "core.chien_luoc.bai_hoc", "ui_qt.app",
)

#: Nhóm test NHANH, thuần (không mạng, không tiến trình thật) — KHÔNG phải cả kho.
TEST_NHANH = (
    "tests/test_dong_bo_git.py",
    "tests/test_dong_bo_git_quet.py",
    "tests/test_cap_nhat_git.py",
    "tests/test_an_toan_khoi_dong.py",
    "tests/test_khong_day_tep_bi_mat.py",
)

#: Tiến trình dài được khởi động lại sau khi áp mã mới. `tu_chay.py` KHÔNG ở
#: đây: lịch mở tiến trình mới mỗi lượt nên tự nhận mã mới.
TEP_GIAO_DIEN = "shopapi_studio_qt.py"
TEP_CON_VM = ("agent.py", "may_dang.py", "may_cmt.py")
CONG_AGENT_VM = 8767

ChayLenh = Callable[..., Tuple[int, str, str]]

_CO_AN = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class DongBoLoi(RuntimeError):
    """Lỗi có câu giải thích cho người vận hành."""


# ═══ tiện ích chung ═════════════════════════════════════════════════════════


def _chay_that(lenh: Sequence[str], *, cwd: Optional[str] = None, timeout: float = 300,
               env: Optional[Dict[str, str]] = None, co: int = 0) -> Tuple[int, str, str]:
    try:
        ket = subprocess.run(list(lenh), cwd=cwd, capture_output=True, timeout=timeout,
                             env=env, creationflags=_CO_AN | co)
    except subprocess.TimeoutExpired:
        return 124, "", "hết giờ ({0:.0f}s): {1}".format(timeout, " ".join(lenh[:3]))
    except OSError as loi:
        return 127, "", str(loi)
    return (ket.returncode, ket.stdout.decode("utf-8", "replace"),
            ket.stderr.decode("utf-8", "replace"))


_chay: ChayLenh = _chay_that


def _env_git() -> Dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes -o ConnectTimeout=20")
    env["LC_ALL"] = env.get("LC_ALL") or "C.UTF-8"
    return env


def git(goc: str, *tham_so: str, timeout: float = 300) -> Tuple[int, str, str]:
    return _chay(["git", *tham_so], cwd=goc, timeout=timeout, env=_env_git())


def _git_ok(goc: str, *tham_so: str, timeout: float = 300) -> str:
    ma, ra, loi = git(goc, *tham_so, timeout=timeout)
    if ma != 0:
        raise DongBoLoi("git {0} lỗi: {1}".format(" ".join(tham_so[:3]), (loi or ra).strip()[:600]))
    return ra


def _thu_muc_trang_thai(goc: str) -> str:
    return os.path.join(goc, "workspace", "dong-bo-git")


def _ghi_nhat_ky(goc: str, dong: str) -> None:
    try:
        d = _thu_muc_trang_thai(goc)
        os.makedirs(d, exist_ok=True)
        with io.open(os.path.join(d, "nhat-ky.txt"), "a", encoding="utf-8") as tep:
            tep.write("{0} {1}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def doc_trang_thai_luu(goc: str) -> Dict[str, Any]:
    try:
        with io.open(os.path.join(_thu_muc_trang_thai(goc), "trang-thai.json"), encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _luu_trang_thai(goc: str, **muc: Any) -> None:
    du = doc_trang_thai_luu(goc)
    du.update(muc)
    du["cap_nhat_luc"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        d = _thu_muc_trang_thai(goc)
        os.makedirs(d, exist_ok=True)
        tam = os.path.join(d, "trang-thai.json.tmp")
        with io.open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, os.path.join(d, "trang-thai.json"))
    except OSError:
        pass


def doc_cau_hinh(goc: str) -> Dict[str, Any]:
    """Khoá `dong_bo_git` trong `cap-nhat.json`. Thiếu/hỏng → `MAC_DINH`. Bật/tắt
    tự cập nhật KHÔNG ở đây mà là `tu_dong_cap_nhat` (`core.cap_nhat_git.doc_cau_hinh`)."""
    cfg = dict(MAC_DINH)
    try:
        with io.open(os.path.join(goc, "cap-nhat.json"), encoding="utf-8-sig") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        du = {}
    rieng = du.get("dong_bo_git") if isinstance(du, dict) else None
    if isinstance(rieng, dict):
        for k in MAC_DINH:
            if k in rieng:
                cfg[k] = rieng[k]
    cfg["ma_may"] = _ma_may_hop_le(str(cfg.get("ma_may") or "")) or _ma_may_mac_dinh()
    for k in ("cho_toi_da_phut", "theo_doi_phut"):
        try:
            cfg[k] = max(0, int(cfg[k]))
        except (TypeError, ValueError):
            cfg[k] = MAC_DINH[k]
    return cfg


def _ma_may_hop_le(ma: str) -> str:
    ma = re.sub(r"[^a-z0-9-]+", "-", ma.strip().lower()).strip("-")
    return ma[:32]


def _ma_may_mac_dinh() -> str:
    """Không lộ tên máy thật: băm tên máy thành 6 ký tự."""
    return "may-" + hashlib.sha1(socket.gethostname().encode("utf-8", "replace")).hexdigest()[:6]


def la_kho_git(goc: str) -> bool:
    return os.path.isdir(os.path.join(goc, ".git")) or os.path.isfile(os.path.join(goc, ".git"))


def dang_quan_ly(goc: str) -> bool:
    """Máy cài từ kho (có `.git`) thì MÃ CHỈ ĐƯỢC ĐỔI QUA GIT (`day`/`keo`/`lui`) —
    đường manifest/ZIP cũ phải nhường, không được hai hệ cùng tráo tệp. Tắt tự
    cập nhật (`tu_dong_cap_nhat: false`) KHÔNG trao quyền lại cho đường cũ."""
    try:
        return la_kho_git(goc)
    except Exception:  # noqa: BLE001
        return False


# ═══ 1) ket_noi — đường tới GitHub ══════════════════════════════════════════


def _hoi_aaaa(may_chu: str, ten: str, timeout: float = 4.0) -> List[str]:
    """Một câu hỏi DNS AAAA qua UDP tới `may_chu` (IPv6). Trả danh sách địa chỉ."""
    qid = random.randint(0, 0xFFFF)
    dau = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    cau = b"".join(bytes([len(p)]) + p.encode("ascii") for p in ten.split(".")) + b"\0"
    goi = dau + cau + struct.pack(">HH", 28, 1)
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        s.sendto(goi, (may_chu, 53))
        du, _ = s.recvfrom(4096)
    finally:
        s.close()
    if len(du) < 12 or struct.unpack(">H", du[:2])[0] != qid:
        return []
    so_hoi, so_dap = struct.unpack(">HH", du[4:8])
    i = 12

    def bo_ten(j: int) -> int:
        while j < len(du):
            n = du[j]
            if n == 0:
                return j + 1
            if n & 0xC0 == 0xC0:
                return j + 2
            j += n + 1
        return j

    for _ in range(so_hoi):
        i = bo_ten(i) + 4
    ra: List[str] = []
    for _ in range(so_dap):
        i = bo_ten(i)
        if i + 10 > len(du):
            break
        kieu, _lop, _ttl, dai = struct.unpack(">HHIH", du[i:i + 10])
        i += 10
        if kieu == 28 and dai == 16:
            ra.append(str(ipaddress.IPv6Address(du[i:i + 16])))
        i += dai
    return ra


def _thu_tcp(dia_chi: str, cong: int = 22, timeout: float = 6.0) -> bool:
    try:
        ho = socket.AF_INET6 if ":" in dia_chi else socket.AF_INET
        with socket.socket(ho, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((dia_chi, cong))
        return True
    except OSError:
        return False


def _ipv4_github() -> List[str]:
    try:
        return sorted({x[4][0] for x in socket.getaddrinfo("github.com", 22, socket.AF_INET)})
    except OSError:
        return []


def dia_chi_nat64(dns64: Sequence[str] = DNS64) -> List[str]:
    ra: List[str] = []
    for may_chu in dns64:
        try:
            for d in _hoi_aaaa(may_chu, "github.com"):
                if d not in ra:
                    ra.append(d)
        except OSError:
            continue
    return ra


def _duong_ssh_config() -> str:
    return os.path.join(os.path.expanduser("~"), ".ssh", "config")


def _host_name_hien_tai(duong: Optional[str] = None, host: str = HOST_SSH) -> str:
    try:
        with io.open(duong or _duong_ssh_config(), encoding="utf-8-sig") as tep:
            dong = tep.read().splitlines()
    except OSError:
        return ""
    trong = False
    for d in dong:
        m = re.match(r"^\s*Host\s+(.+?)\s*$", d, re.I)
        if m:
            trong = host in m.group(1).split()
        elif trong:
            m = re.match(r"^\s*HostName\s+(\S+)", d, re.I)
            if m:
                return m.group(1)
    return ""


def sua_ssh_config(host_name: str, *, duong: Optional[str] = None, host: str = HOST_SSH,
                   khoa: str = KHOA_SSH_MAC_DINH) -> bool:
    """Đặt `HostName` của khối `Host <host>` trong ~/.ssh/config. Chưa có khối thì
    thêm mới. Trả True nếu đã ghi thay đổi."""
    duong = duong or _duong_ssh_config()
    try:
        with io.open(duong, encoding="utf-8-sig") as tep:
            dong = tep.read().splitlines()
    except OSError:
        dong = []
    trong_khoi = False
    tim_khoi = False
    da_sua = False
    moi: List[str] = []
    for d in dong:
        m = re.match(r"^\s*Host\s+(.+?)\s*$", d, re.I)
        if m:
            trong_khoi = host in m.group(1).split()
            tim_khoi = tim_khoi or trong_khoi
        elif trong_khoi and re.match(r"^\s*HostName\s+", d, re.I):
            cu = d.split(None, 1)[1].strip() if len(d.split(None, 1)) > 1 else ""
            if cu != host_name:
                thut = re.match(r"^(\s*)", d).group(1)
                d = "{0}HostName {1}".format(thut, host_name)
                da_sua = True
        moi.append(d)
    if not tim_khoi:
        moi += ["", "# MyTool: kho chung GitHub. HostName do core/dong_bo_git.py (ket_noi) tự làm mới.",
                "Host " + host, "    HostName " + host_name, "    HostKeyAlias github.com",
                "    User git", "    IdentityFile " + khoa, "    IdentitiesOnly yes",
                "    ConnectTimeout 20"]
        da_sua = True
    if da_sua:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        if os.path.isfile(duong) and not os.path.exists(duong + ".bak-dong-bo-git"):
            shutil.copy2(duong, duong + ".bak-dong-bo-git")  # bản gốc, chỉ giữ lần đầu
        with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
            tep.write("\n".join(moi).rstrip("\n") + "\n")
    return da_sua


def ket_noi(goc: str = GOC, *, sua_config: bool = True, in_ra: Callable[[str], None] = print) -> Dict[str, Any]:
    """Tìm đường tới GitHub cổng 22: IPv4 thẳng trước, không được thì NAT64
    (DNS64). Cập nhật `HostName` của `github-mytool` khi IP đổi. Cuối cùng thử
    `git ls-remote origin` (xác thực deploy key)."""
    ket: Dict[str, Any] = {"che_do": "", "host_name": "", "xac_thuc": False, "loi": ""}
    v4 = _ipv4_github()
    if v4 and any(_thu_tcp(d, 22, 5) for d in v4[:2]):
        ket["che_do"], ket["host_name"] = "thang", "github.com"
    else:
        # HostName đang dùng còn tới được thì GIỮ (không đổi qua lại giữa các
        # tiền tố NAT64 mỗi lần gọi); không thì dò lại qua DNS64.
        hien = _host_name_hien_tai()
        ung_vien = ([hien] if hien and ":" in hien else []) + [d for d in dia_chi_nat64() if d != hien]
        for d in ung_vien:
            if _thu_tcp(d, 22, 8):
                ket["che_do"], ket["host_name"] = "nat64", d
                break
    if not ket["host_name"]:
        ket["loi"] = "Không tới được github.com:22 (cả IPv4 thẳng lẫn NAT64)."
        in_ra("! " + ket["loi"])
        return ket
    in_ra("Đường tới GitHub: {0} ({1})".format(ket["che_do"], ket["host_name"]))
    if ket["che_do"] == "nat64":
        in_ra("  HTTPS qua NAT64: git -c http.curloptResolve=github.com:443:[{0}] clone https://github.com/...".format(
            ket["host_name"]))
    if sua_config and sua_ssh_config(ket["host_name"]):
        in_ra("  đã cập nhật ~/.ssh/config: Host {0} -> HostName {1}".format(HOST_SSH, ket["host_name"]))
    if la_kho_git(goc):
        ma, ra, loi = git(goc, "ls-remote", REMOTE, "HEAD", timeout=60)
        ket["xac_thuc"] = ma == 0
        if ma == 0:
            in_ra("  xác thực kho OK ({0}).".format("kho trống" if not ra.strip() else "có nhánh"))
        else:
            chu = (loi or ra).strip()
            ket["loi"] = chu[:300]
            if "Permission denied" in chu or "publickey" in chu:
                in_ra("! Deploy key của máy này CHƯA được thêm vào kho (Settings > Deploy keys, bật Allow write).")
            else:
                in_ra("! git ls-remote lỗi: " + chu[:300])
    return ket


# ═══ 2) trang_thai ══════════════════════════════════════════════════════════


def _nhanh_hien_tai(goc: str) -> str:
    # `symbolic-ref` chạy được cả khi nhánh CHƯA có commit nào (kho vừa init).
    ma, ra, _ = git(goc, "symbolic-ref", "--short", "-q", "HEAD")
    return ra.strip() if ma == 0 else ""


def _co_ref(goc: str, ref: str) -> bool:
    return git(goc, "rev-parse", "--verify", "-q", ref)[0] == 0


def truoc_sau(goc: str) -> Tuple[Optional[int], Optional[int]]:
    """(số commit máy này TRƯỚC origin, số commit origin TRƯỚC máy này)."""
    dich = "{0}/{1}".format(REMOTE, NHANH)
    if not _co_ref(goc, dich):
        ma, ra, _ = git(goc, "rev-list", "--count", "HEAD")
        return (int(ra.strip()) if ma == 0 and ra.strip().isdigit() else None), None
    ma, ra, _ = git(goc, "rev-list", "--left-right", "--count", "HEAD..." + dich)
    if ma != 0:
        return None, None
    a, b = (ra.split() + ["0", "0"])[:2]
    return int(a), int(b)


def tep_doi_cuc_bo(goc: str) -> List[str]:
    """Dòng `git status --porcelain` (đã trừ tệp bị .gitignore chặn)."""
    ma, ra, _ = git(goc, "status", "--porcelain", "-uall")
    return [d for d in ra.splitlines() if d.strip()] if ma == 0 else []


def fetch(goc: str, *, sua_mang: bool = True) -> Tuple[bool, str]:
    ma, ra, loi = git(goc, "fetch", "--prune", "--tags", REMOTE, timeout=180)
    if ma != 0 and sua_mang:
        ket_noi(goc, in_ra=lambda s: None)
        ma, ra, loi = git(goc, "fetch", "--prune", "--tags", REMOTE, timeout=180)
    return ma == 0, (loi or ra).strip()


def trang_thai(goc: str = GOC, *, in_ra: Callable[[str], None] = print, co_fetch: bool = True) -> Dict[str, Any]:
    if not la_kho_git(goc):
        in_ra("! {0} không phải kho Git.".format(goc))
        return {"kho_git": False}
    ok_fetch, loi_fetch = fetch(goc) if co_fetch else (True, "")
    nhanh = _nhanh_hien_tai(goc)
    truoc, sau = truoc_sau(goc)
    doi = tep_doi_cuc_bo(goc)
    ma, ra, _ = git(goc, "remote", "get-url", REMOTE)
    in_ra("Kho: {0}".format(ra.strip() if ma == 0 else "(chưa có origin)"))
    in_ra("Nhánh: {0} | trước origin: {1} | sau origin: {2}{3}".format(
        nhanh or "?", "?" if truoc is None else truoc, "?" if sau is None else sau,
        "" if ok_fetch else " (fetch lỗi: {0})".format(loi_fetch[:160])))
    in_ra("Tệp đổi chưa commit: {0}".format(len(doi)))
    for d in doi[:40]:
        in_ra("  " + d)
    if len(doi) > 40:
        in_ra("  … và {0} tệp nữa".format(len(doi) - 40))
    cfg = doc_cau_hinh(goc)
    from . import cap_nhat_git as cng  # noqa: PLC0415
    ccn = cng.doc_cau_hinh(goc)
    in_ra("Phiên bản: {0} | tự động cập nhật: {1} | mã máy {2}".format(
        cng.doc_phien_ban(goc) or "?", "BẬT" if ccn["tu_dong_cap_nhat"] else "tắt", cfg["ma_may"]))
    luu = cng.doc_trang_thai(goc)
    if luu.get("cap_nhat_cuoi"):
        c = luu["cap_nhat_cuoi"]
        in_ra("Lượt cập nhật cuối: {0} {1} {2}".format(c.get("luc"), c.get("ket_qua"), c.get("chi_tiet") or ""))
    return {"kho_git": True, "nhanh": nhanh, "truoc": truoc, "sau": sau, "tep_doi": doi,
            "fetch_ok": ok_fetch}


# ═══ kiểm: py_compile + kiểm khói + test nhanh + quét bí mật ═════════════════


def bien_dich(goc: str, tep: Iterable[str]) -> List[str]:
    """Biên dịch (không ghi .pyc) từng tệp .py. Trả danh sách lỗi."""
    loi: List[str] = []
    for rel in tep:
        if not rel.endswith(".py"):
            continue
        duong = os.path.join(goc, *rel.split("/"))
        if not os.path.isfile(duong):
            continue
        try:
            with io.open(duong, "rb") as f:
                compile(f.read(), duong, "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as e:
            loi.append("{0}: {1}".format(rel, e))
    return loi


def _python() -> str:
    exe = sys.executable or "python"
    if os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.isfile(cand):
            return cand
    return exe


def kiem_khoi(goc: str, *, co_test: bool = True, in_ra: Callable[[str], None] = print) -> List[str]:
    """Import các module chính (tiến trình con) + nhóm test nhanh (ưu tiên thấp).
    Trả danh sách lỗi (rỗng = đạt)."""
    loi: List[str] = []
    co_mat = [m for m in MODULE_CHINH
              if os.path.isfile(os.path.join(goc, *m.split(".")) + ".py")
              or os.path.isfile(os.path.join(goc, *m.split("."), "__init__.py"))]
    ma_lenh = ("import importlib, sys\nsys.path.insert(0, r'{0}')\nloi = []\n"
               "for m in {1!r}:\n"
               "    try:\n        importlib.import_module(m)\n"
               "    except Exception as e:\n        loi.append('%s: %s: %s' % (m, type(e).__name__, e))\n"
               "print('\\n'.join(loi))\nsys.exit(1 if loi else 0)\n").format(goc, co_mat)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM") or "offscreen"
    co_thap = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    ma, ra, err = _chay([_python(), "-c", ma_lenh], cwd=goc, timeout=300, env=env, co=co_thap)
    if ma != 0:
        loi.append("import module chính hỏng:\n" + (ra.strip() or err.strip())[-1500:])
    in_ra("  kiểm khói import: {0} module — {1}".format(len(co_mat), "đạt" if ma == 0 else "HỎNG"))
    loi += kiem_khoi_vm(goc, env=env, co=co_thap, in_ra=in_ra)
    if co_test and not loi:
        tests = [t for t in TEST_NHANH if os.path.isfile(os.path.join(goc, *t.split("/")))]
        if tests:
            ly_do = _ly_do_may_ban_nang(goc)
            if ly_do:
                in_ra("  test nhanh: hoãn ({0}).".format(ly_do))
            else:
                co_rat_thap = getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)
                ma, ra, err = _chay([_python(), "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
                                    cwd=goc, timeout=600, env=env, co=co_rat_thap)
                dong_cuoi = (ra.strip().splitlines() or [""])[-1]
                in_ra("  test nhanh ({0} tệp): {1}".format(len(tests), dong_cuoi[:160]))
                if ma not in (0, 5):
                    loi.append("test nhanh hỏng:\n" + (ra + err)[-2000:])
    return loi


#: Máy đăng/agent `vm/` — chạy bằng tên TRẦN (`import cdp`, cwd=vm/) nên không nằm
#: trong `MODULE_CHINH` (gói `core.`). Trước 06/10/2026 bản mới làm hỏng `vm/agent.py`
#: chỉ lộ ra SAU khi đã áp + khởi động lại (`_theo_doi` thấy cổng 8767 chết lặp), còn
#: hỏng `may_dang_dom.py` (agent mở mỗi phiên) thì không bao giờ lộ: agent vẫn sống,
#: chỉ là không video nào lên. Kiểm khói import cả nhóm này ngay trong bản kiểm.
MODULE_VM = ("agent", "cdp", "may_dang_dom", "may_cmt_dom", "tu_chua_dom", "thiet_lap_kenh_dom")


def kiem_khoi_vm(goc: str, *, env: Optional[Dict[str, str]] = None, co: int = 0,
                 in_ra: Callable[[str], None] = print) -> List[str]:
    """Import (tiến trình con, `cwd=vm/`) các tệp `MODULE_VM` có mặt. `SHOPAPI_VM_GOC`
    trỏ thư mục tạm để không mã nào chạm nhật ký/sổ THẬT của máy ảo. Rỗng = đạt."""
    thu_muc_vm = os.path.join(goc, "vm")
    co_mat = [m for m in MODULE_VM if os.path.isfile(os.path.join(thu_muc_vm, m + ".py"))]
    if not co_mat:
        return []
    moi_truong = dict(env if env is not None else os.environ)
    moi_truong["PYTHONDONTWRITEBYTECODE"] = "1"
    tam = tempfile.mkdtemp(prefix="kiem-khoi-vm-")
    moi_truong["SHOPAPI_VM_GOC"] = tam
    ma_lenh = ("import importlib, sys\nsys.path.insert(0, r'{0}')\nsys.path.insert(0, r'{1}')\nloi = []\n"
               "for m in {2!r}:\n"
               "    try:\n        importlib.import_module(m)\n"
               "    except Exception as e:\n        loi.append('vm/%s: %s: %s' % (m, type(e).__name__, e))\n"
               "print('\\n'.join(loi))\nsys.exit(1 if loi else 0)\n").format(goc, thu_muc_vm, co_mat)
    try:
        ma, ra, err = _chay([_python(), "-c", ma_lenh], cwd=thu_muc_vm, timeout=180, env=moi_truong, co=co)
    finally:
        shutil.rmtree(tam, ignore_errors=True)
    in_ra("  kiểm khói vm/: {0} tệp — {1}".format(len(co_mat), "đạt" if ma == 0 else "HỎNG"))
    if ma != 0:
        return ["import máy đăng/agent vm/ hỏng:\n" + (ra.strip() or err.strip())[-1500:]]
    return []


def _ly_do_may_ban_nang(goc: str) -> str:
    """'' nếu khe "nang" trống và không lượt AUTO nào ở dựng/phụ đề."""
    try:
        from . import kiem_phat_hanh as kph  # noqa: PLC0415
        return kph._khoa_nang_dang_giu(goc) or kph._luot_dang_o_khau_nang(goc)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return ""


# ── quét bí mật: lớp kiem_phat_hanh + lớp thêm ─────────────────────────────

_MAU_THEM: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("khoá API dạng sk-…", re.compile(r"(?<![A-Za-z0-9_])sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{24,}")),
    ("khoá shopapi_…", re.compile(r"(?<![A-Za-z0-9])shopapi_(?:live|test|sk|key)?_?[A-Za-z0-9]{20,}")),
    ("token GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("khoá Google API", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("khoá AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("khoá riêng PEM/SSH", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
    ("khối mã hoá Fernet", re.compile(r"\bgAAAAA[A-Za-z0-9_\-]{60,}")),
    # (hằng hex viết tách đôi để chính tệp này không tự khớp)
    ("khối DPAPI", re.compile(r"AQAAANCMnd8BFdERjHoAwE/Cl\+sBAAAA|01000000d08c9ddf" r"0115d1118c7a00c04fc297eb", re.I)),
    # ── thêm 06/10/2026 (kiểm toàn kho công khai) ──
    ("token bot Telegram", re.compile(r"(?<![A-Za-z0-9_])(?:bot)?\d{8,10}:[A-Za-z0-9_\-]{35}(?![A-Za-z0-9_\-])")),
    ("refresh token Google OAuth (1//0…)", re.compile(r"(?<![A-Za-z0-9_/])1//0[A-Za-z0-9_\-]{20,}")),
    ("access token Google (ya29.…)", re.compile(r"\bya29\.[A-Za-z0-9_\-]{20,}")),
    ("refresh_token có giá trị", re.compile(r"refresh_token[\"']?\s*[:=]\s*[\"'][^\"'\s]{20,}[\"']", re.I)),
    ("cookie phiên Google/YouTube", re.compile(
        r"(?<![A-Za-z0-9_\-])(?:__Secure-[0-9A-Za-z]*(?:PSID|PSIDTS|PSIDCC|PAPISID|OSID)|SAPISID|APISID|"
        r"HSID|SSID|SIDCC|SID|LOGIN_INFO|VISITOR_INFO1_LIVE)\s*[=:]\s*[\"']?[A-Za-z0-9_\-./%:]{16,}")),
    ("chat id Telegram", re.compile(r"chat_?id[\"']?\s*[:=]\s*[\"']?-?\d{7,}", re.I)),
    # URL Studio luôn là kênh CỦA MÌNH (chỉ chủ kênh mở được) — id trong đó là id kênh thật.
    ("id kênh thật trong URL Studio", re.compile(r"studio\.youtube\.com/channel/UC[A-Za-z0-9_\-]{22}")),
    ("SID tài khoản Windows", re.compile(r"\bS-1-5-21-\d{6,10}-\d{6,10}-\d{6,10}(?:-\d{3,})?\b")),
    ("khoá hex dài gán cho biến bí mật", re.compile(
        r"(?:key|khoa|secret|token|bi_mat|mat_khau|password)[A-Za-z0-9_]*[\"']?\s*[:=]\s*[\"']?[0-9a-fA-F]{32,}\b",
        re.I)),
)
_MAU_EMAIL = re.compile(r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}\b")
_EMAIL_CHO_PHEP = re.compile(
    r"@(?:example\.(?:com|org|net)|[a-z0-9.\-]*\.(?:test|invalid|example|local)|localhost|"
    r"users\.noreply\.github\.com|anthropic\.com|github\.com|shopapi\.vn|"
    r"mail\.com|email\.com|domain\.com|congty\.vn|proxy\.vn|[a-z]\.[a-z]{2,3})$", re.I)
_MAU_DUONG_NGUOI_DUNG = re.compile(
    r"[A-Za-z]:(?:\\\\|\\|/)+Users(?:\\\\|\\|/)+(?!Public\b|Default\b|<|%|\{|\$|\.\.\.|…)([A-Za-z0-9_.\-]+)", re.I)
_TEN_NGUOI_DUNG_MAU = {"ten", "tên", "user", "username", "you", "ban", "name", "x", "a", "khach", "admin",
                       "administrator", "nguoi", "nguoidung", "ai-do", "claude.local.md"}

#: Đánh dấu dòng chứa chuỗi MẪU cố ý (test) — lớp quét thêm bỏ qua dòng này.
DAU_BO_QUA = "dong-bo-git: mau"

_DUOI_VAN_BAN = (".py", ".json", ".yaml", ".yml", ".md", ".txt", ".js", ".ini", ".cfg", ".csv",
                 ".bat", ".vbs", ".ps1", ".xml", ".html", ".example", ".toml")


#: Đường KHÔNG BAO GIỜ được theo dõi trong kho chung (lớp thứ hai sau .gitignore).
_THU_MUC_CAM = ("vm/logs/", "workspace/", "DONE/", "bi-mat/", "PROJECTS/", "runtime/", "models/",
                "nao/tri-nho/", "nao/nhat-ky/", "nao/ky-nang/", "vm/tien-ich/", "vm/replied/",
                "vm/da-dang-cmt-moi/", "vm/clients/")
_TEN_TEP_CAM = frozenset((
    "cai-dat.json", "cai-dat-tool.json", "secrets.json", "config.json", "cap-nhat.json", "vps.json",
    "may-ao.json", "trang-thai.json", "hanh-dong.json", "bao-dong.json", "vps-rieng.json",
    "mang-youtube.json", "hop-viec-may-ao.json", "claude.local.md", "nhat-ky-kenh.md",
    # hồ sơ Chrome
    "cookies", "cookies-journal", "login data", "login data-journal", "web data", "local state",
    "preferences", "secure preferences", "history"))
_DUOI_CAM = (".dpapi", ".sqlite", ".sqlite3", ".db", ".ldb", ".jsonl", ".csv", ".tsv", ".pem", ".key")
#: .csv/.tsv/.jsonl được phép ở những chỗ này (khuôn, dữ liệu test tổng hợp) — nội dung vẫn bị soi.
_CHO_PHEP_DU_LIEU = ("tests/", "CHANNEL/_KHUON/", "docs/")
_TEP_NHOM_CHO_PHEP = ("ngach.yaml", "INSIGHT-CHON-CONTENT.md")


def duong_cam(rel: str) -> str:
    """Lý do `rel` (đường git, dấu /) không được lên kho chung; '' nếu được."""
    rel = rel.replace("\\", "/").lstrip("/")
    thap = rel.lower()
    phan = rel.split("/")
    ten = phan[-1].lower()
    for tm in _THU_MUC_CAM:
        if thap.startswith(tm.lower()):
            return "thư mục dữ liệu riêng máy ({0})".format(tm)
    if phan[0] == "CHANNEL" and len(phan) >= 2:
        if phan[1] == "_NHOM":
            if len(phan) >= 4 and (len(phan) > 4 or phan[3] not in _TEP_NHOM_CHO_PHEP):
                return "CHANNEL/_NHOM/<ngách>/ chỉ được ngach.yaml + INSIGHT-CHON-CONTENT.md"
        elif phan[1] not in ("_KHUON", "README.md"):
            return "thư mục kênh thật CHANNEL/<kênh>/"
    if ten == "kenh.yaml" and not rel.startswith("CHANNEL/_KHUON/"):
        return "kenh.yaml của kênh thật"
    if ten in _TEN_TEP_CAM:
        return "tệp cấu hình/bí mật/hồ sơ trình duyệt riêng máy ({0})".format(ten)
    if "/user data/" in "/" + thap or "/data/profile/" in "/" + thap or "/trinh-duyet/" in "/" + thap:
        return "hồ sơ trình duyệt"
    if thap.endswith(_DUOI_CAM):
        if thap.endswith((".dpapi", ".pem", ".key", ".sqlite", ".sqlite3", ".db", ".ldb")):
            return "tệp khoá/cơ sở dữ liệu ({0})".format(os.path.splitext(thap)[1])
        if not rel.startswith(_CHO_PHEP_DU_LIEU) and ".example" not in thap and "mau" not in ten:
            return "tệp dữ liệu bảng/dòng ({0}) ngoài tests/ và khuôn".format(os.path.splitext(thap)[1])
    return ""


#: Dòng trông như dữ liệu YouTube (đường video/kênh) — CSV/JSONL có ≥ `_NGUONG_DONG_YT` dòng như vậy là dữ liệu kênh.
_MAU_DONG_YT = re.compile(r"youtube\.com/(?:watch|shorts/|channel/|@)|youtu\.be/|(?<![A-Za-z0-9_-])UC[A-Za-z0-9_-]{22}(?![A-Za-z0-9_-])")
_NGUONG_DONG_YT = 3
_MAU_VIDEO_ID_URL = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/video/|/embed/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
_MAU_KENH_ID = re.compile(r"(?<![A-Za-z0-9_-])UC[A-Za-z0-9_-]{22}(?![A-Za-z0-9_-])")
_MAU_HANDLE = re.compile(r"(?<![A-Za-z0-9_.@/-])@([A-Za-z0-9][A-Za-z0-9_.\-]{2,29})(?![A-Za-z0-9_\-])")
_MAU_TOKEN_11 = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{11}(?![A-Za-z0-9_-])")


def _giong_video_id(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", s) and re.search(r"[A-Z]", s) and re.search(r"[a-z0-9]", s))


def _bo_dau(s: str) -> str:
    import unicodedata  # noqa: PLC0415
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def _du_dai_tieu_de(td: str) -> bool:
    """Tiêu đề đủ dài để khớp mà không báo giả — KHÔNG đoán theo ngôn ngữ: chữ
    rộng (Hán/Kana/Hangul…) mang nhiều nghĩa hơn mỗi ký tự nên sàn thấp hơn."""
    import unicodedata  # noqa: PLC0415
    td = td.strip()
    rong = sum(1 for c in td if unicodedata.east_asian_width(c) in ("W", "F"))
    return len(td) >= 12 or (rong >= 4 and len(td) >= 6)


def goc_du_lieu(goc: str) -> str:
    """Thư mục có dữ liệu THẬT của máy (CHANNEL/<kênh>/, vm/, secrets.json). Một git
    worktree (`.git` là TỆP — phiên agent) không có dữ liệu kênh: đọc từ cây chính,
    không thì lớp quét chuỗi riêng máy chạy RỖNG mà tưởng sạch."""
    if [y for y in glob.glob(os.path.join(goc, "CHANNEL", "*", "kenh.yaml"))
            if not os.path.basename(os.path.dirname(y)).startswith("_")]:
        return goc
    tep = os.path.join(goc, ".git")
    if not os.path.isfile(tep):
        return goc
    try:
        with io.open(tep, encoding="utf-8") as f:
            m = re.match(r"gitdir:\s*(.+)", f.read().strip())
        if not m:
            return goc
        gitdir = m.group(1).strip()
        if not os.path.isabs(gitdir):
            gitdir = os.path.normpath(os.path.join(goc, gitdir))
        chung = gitdir
        if os.path.isfile(os.path.join(gitdir, "commondir")):
            with io.open(os.path.join(gitdir, "commondir"), encoding="utf-8") as f:
                chung = os.path.normpath(os.path.join(gitdir, f.read().strip()))
    except OSError:
        return goc
    chinh = os.path.dirname(chung) if os.path.basename(chung).lower() == ".git" else ""
    return chinh if chinh and os.path.isdir(chinh) else goc


def _doc_ke_hoach(duong: str) -> Tuple[List[str], List[str]]:
    """(tiêu đề, video id) trong một tệp kế hoạch CSV — cột nhận theo TÊN cột
    (bỏ dấu), giá trị thì ngôn ngữ nào cũng được."""
    import csv  # noqa: PLC0415
    td: List[str] = []
    vid: List[str] = []
    try:
        with io.open(duong, encoding="utf-8-sig", newline="") as f:
            dong = list(csv.reader(f))
    except (OSError, csv.Error, UnicodeDecodeError):
        return td, vid
    if not dong:
        return td, vid
    dau = [_bo_dau(h) for h in dong[0]]
    cot_td = [i for i, h in enumerate(dau) if h in ("tieu de", "title", "tieu_de", "ten video")]
    cot_id = [i for i, h in enumerate(dau) if h.replace("_", " ") in ("video id", "id video", "videoid")]
    for hang in dong[1:]:
        for i in cot_td:
            if i < len(hang) and _du_dai_tieu_de(hang[i]):
                td.append(hang[i].strip())
        for i in cot_id:
            if i < len(hang) and _giong_video_id(hang[i].strip()):
                vid.append(hang[i].strip())
        for o in hang:
            vid += [m.group(1) for m in _MAU_VIDEO_ID_URL.finditer(o) if _giong_video_id(m.group(1))]
    return td, vid


def _doc_chu(duong: str, toi_da: int = 8 * 1024 * 1024) -> str:
    try:
        with io.open(duong, "rb") as f:
            return f.read(toi_da).decode("utf-8", "replace")
    except OSError:
        return ""


def tu_cam_cua_may(goc: str, *, day_du: bool = False) -> List[Tuple[str, str]]:
    """Chuỗi RIÊNG của máy này không được lên kho: tên kênh thật (kenh.yaml `ten`),
    video id của chính kênh (tên thư mục trong CHANNEL/<kênh>/chi-so/), tên người
    dùng Windows. Đọc từ đĩa máy này — máy khác tự có danh sách của nó.

    06/10/2026: thêm tiêu đề + video id đọc từ TỆP KẾ HOẠCH (mọi ngôn ngữ — không
    đoán theo chữ), id kênh/handle (kenh.yaml, vm/config.json), id kênh/video/handle
    ĐỐI THỦ trong nghien-cuu/ và _NHOM/, email git toàn cục, khoá secrets.json.
    Chạy từ worktree thì đọc dữ liệu ở cây chính (`goc_du_lieu`)."""
    goc = goc_du_lieu(goc)
    ra: List[Tuple[str, str]] = []
    for yaml in glob.glob(os.path.join(goc, "CHANNEL", "*", "kenh.yaml")):
        ma = os.path.basename(os.path.dirname(yaml))
        if ma.startswith("_"):
            continue
        try:
            with io.open(yaml, encoding="utf-8") as tep:
                for d in tep:
                    m = re.match(r"^\s*(ten|handle|channel_id|kenh_id)\s*:\s*[\"']?(.+?)[\"']?\s*$", d)
                    if m:
                        gia_tri = re.split(r"\s+[—-]\s+", m.group(2))[0].strip()
                        if len(gia_tri) >= 4:
                            ra.append(("tên/định danh kênh thật ({0})".format(ma), gia_tri))
        except OSError:
            continue
        for d in glob.glob(os.path.join(os.path.dirname(yaml), "chi-so", "*")):
            ten = os.path.basename(d)
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", ten) and re.search(r"[A-Z]", ten) and re.search(r"[a-z0-9]", ten):
                ra.append(("video id kênh thật ({0})".format(ma), ten))
        for hs in glob.glob(os.path.join(os.path.dirname(yaml), "ho-so-video", "*.json")):
            try:
                with io.open(hs, encoding="utf-8") as tep:
                    td = str((json.load(tep) or {}).get("tieu_de") or "").strip()
            except (OSError, ValueError, AttributeError):
                continue
            if _du_dai_tieu_de(td):
                ra.append(("tiêu đề video kênh thật ({0})".format(ma), td))
        # hồ sơ thiết lập kênh (tên/handle/mô tả/danh sách phát thật trên YouTube)
        for hs in glob.glob(os.path.join(os.path.dirname(yaml), "ho-so*.json")) + \
                glob.glob(os.path.join(os.path.dirname(yaml), "thiet-lap", "ho-so*.json")):
            try:
                with io.open(hs, encoding="utf-8-sig") as tep:
                    du = json.load(tep)
            except (OSError, ValueError):
                continue
            if not isinstance(du, dict):
                continue
            for k in ("ten", "handle", "banner_chu"):
                v = str(du.get(k) or "").strip()
                if len(v) >= 4:
                    ra.append(("tên/định danh kênh thật ({0})".format(ma), v))
            mo_ta = str(du.get("mo_ta") or "").strip().splitlines()
            if mo_ta and len(mo_ta[0]) >= 12:
                ra.append(("mô tả kênh thật ({0})".format(ma), mo_ta[0][:60]))
            ds = du.get("danh_sach_phat")
            for p in ds if isinstance(ds, list) else []:
                v = str((p.get("ten") if isinstance(p, dict) else p) or "").strip()
                if _du_dai_tieu_de(v) or len(v) >= 8:
                    ra.append(("danh sách phát kênh thật ({0})".format(ma), v))
        # id kênh CỦA MÌNH: số liệu chi-so/ chứa URL Studio (chỉ chủ kênh mở được)
        so_tep, thay_id = 0, 0
        for r, _ds, fs in os.walk(os.path.join(os.path.dirname(yaml), "chi-so")):
            for f in fs:
                if not f.endswith((".json", ".txt", ".md")):
                    continue
                so_tep += 1
                ids = re.findall(r"studio\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})",
                                 _doc_chu(os.path.join(r, f), 512 * 1024))
                thay_id += len(ids)
                ra += [("id kênh thật ({0})".format(ma), i) for i in ids]
            if so_tep >= 300 or (thay_id and so_tep >= 40):
                break
        # id kênh / handle viết đâu đó trong kenh.yaml + tệp riêng của kênh
        for tep in [yaml] + glob.glob(os.path.join(os.path.dirname(yaml), "*.json")) + \
                glob.glob(os.path.join(os.path.dirname(yaml), "thiet-lap", "*.json")):
            chu = "\n".join(d for d in _doc_chu(tep, 2 * 1024 * 1024).splitlines()
                            if not d.lstrip().startswith("#"))
            ra += [("id kênh thật ({0})".format(ma), m.group(0)) for m in _MAU_KENH_ID.finditer(chu)]
            ra += [("handle kênh thật ({0})".format(ma), "@" + m.group(1)) for m in _MAU_HANDLE.finditer(chu)
                   if not _EMAIL_CHO_PHEP.search("@" + m.group(1))]
        # tệp kế hoạch: tiêu đề + video id, ngôn ngữ nào cũng được
        for kh in glob.glob(os.path.join(os.path.dirname(yaml), "ke-hoach-dang", "*.csv")) + \
                glob.glob(os.path.join(goc, "vm", "ke-hoach-{0}.csv".format(ma))):
            td, vid = _doc_ke_hoach(kh)
            ra += [("tiêu đề video kênh thật ({0})".format(ma), t) for t in td]
            ra += [("video id kênh thật ({0})".format(ma), v) for v in vid]
    # dữ liệu ĐỐI THỦ: id kênh, video id (từ URL), handle trong nghien-cuu/ và _NHOM/
    nguon_dt = (glob.glob(os.path.join(goc, "CHANNEL", "*", "nghien-cuu", "**", "*.*"), recursive=True)
                + glob.glob(os.path.join(goc, "CHANNEL", "_NHOM", "*", "**", "*.*"), recursive=True))
    da_doc = 0
    # Nhỏ trước: bảng/danh sách (csv, txt, yaml) mang nhiều id nhất trên mỗi byte;
    # trần 64MB để mỗi lượt `day` không đọc cả GB dữ liệu nghiên cứu.
    nguon_dt = sorted((t for t in nguon_dt
                       if t.lower().endswith((".csv", ".tsv", ".json", ".jsonl", ".txt", ".md", ".yaml"))),
                      key=lambda t: (not t.lower().endswith((".csv", ".tsv", ".txt", ".yaml")), t))
    for tep in nguon_dt:
        if da_doc > (2048 if day_du else 64) * 1024 * 1024:
            break
        chu = _doc_chu(tep, (16 if day_du else 2) * 1024 * 1024)
        da_doc += len(chu)
        ra += [("id kênh đối thủ", m.group(0)) for m in _MAU_KENH_ID.finditer(chu)]
        ra += [("video id đối thủ", m.group(1)) for m in _MAU_VIDEO_ID_URL.finditer(chu) if _giong_video_id(m.group(1))]
        if os.path.basename(tep).lower().startswith("doi-thu"):
            ra += [("handle kênh đối thủ", "@" + m.group(1)) for m in _MAU_HANDLE.finditer(chu)]
    # vm/: cấu hình máy đăng (URL Studio có id kênh) + mọi tệp kế hoạch
    for tep in glob.glob(os.path.join(goc, "vm", "*.json")):
        chu = _doc_chu(tep, 2 * 1024 * 1024)
        ra += [("id kênh thật (vm)", m.group(0)) for m in _MAU_KENH_ID.finditer(chu)]
    for kh in glob.glob(os.path.join(goc, "vm", "ke-hoach-*.csv")):
        td, vid = _doc_ke_hoach(kh)
        ra += [("tiêu đề video kênh thật (vm)", t) for t in td] + [("video id kênh thật (vm)", v) for v in vid]
    # email thật của người dùng (git toàn cục) — tác giả commit đã là `.invalid`
    try:
        ma_e, email, _ = _chay(["git", "config", "--global", "user.email"], timeout=20)
        email = email.strip()
        if ma_e == 0 and "@" in email and not email.endswith((".invalid", "noreply.github.com")):
            ra.append(("email người dùng (git toàn cục)", email))
    except Exception:  # noqa: BLE001
        pass
    # khoá giải mã kho bí mật: lọt vào kho là mở được mọi bí mật
    try:
        with io.open(os.path.join(goc, "secrets.json"), encoding="utf-8-sig") as tep:
            sj = json.load(tep)
        for k in ("khoa", "key"):
            v = sj.get(k) if isinstance(sj, dict) else None
            if isinstance(v, str) and len(v) >= 16:
                ra.append(("khoá giải mã secrets.json", v))
        v = sj.get("du_lieu") if isinstance(sj, dict) else None
        if isinstance(v, str) and len(v) >= 40:
            ra.append(("khối dữ liệu secrets.json", v[:40]))
    except (OSError, ValueError, AttributeError):
        pass
    nguoi = os.environ.get("USERNAME") or ""
    if nguoi and len(nguoi) >= 4 and nguoi.lower() not in ("administrator", "admin", "user"):
        ra.append(("tên người dùng Windows", nguoi))
    thay: Dict[str, str] = {}
    for loai, c in ra:
        c = c.strip()
        if len(c) >= 4 and c not in thay:
            thay[c] = loai
    return [(loai, c) for c, loai in thay.items()]


def che(chuoi: str, *, giu: int = 0) -> str:
    """Trích AN TOÀN để in/ghi nhật ký: không in nguyên chuỗi bí mật/tên kênh,
    chỉ `giu` ký tự đầu (tiền tố loại khoá như `sk-`) + độ dài + băm ngắn để đối chiếu."""
    h = hashlib.sha1(chuoi.encode("utf-8", "replace")).hexdigest()[:6]
    return "«{0}…{1}kt#{2}»".format(chuoi[:max(0, min(giu, len(chuoi) // 4))], len(chuoi), h)


def _che_email(e: str) -> str:
    ten, _, mien = e.partition("@")
    return "{0}***@{1}".format(ten[:1], mien)


def che_dong(s: str) -> str:
    """Che mọi chuỗi giống khoá/token/email trong một dòng sắp in hoặc ghi nhật ký."""
    for _ten, mau in _MAU_THEM:
        s = mau.sub(lambda m: che(m.group(0), giu=4), s)
    return _MAU_EMAIL.sub(lambda m: m.group(0) if (_EMAIL_CHO_PHEP.search(m.group(0))
                                                    or m.group(0).startswith("git@"))
                          else _che_email(m.group(0)), s)


class _BoKhop:
    """Khớp nhanh danh sách chuỗi cấm: id/handle (dạng token) tra theo TẬP, chuỗi
    tự do (tiêu đề, tên kênh, khoá) bằng MỘT biểu thức gộp."""

    def __init__(self, tu_cam: Sequence[Tuple[str, str]]):
        self.token: Dict[str, Tuple[str, str]] = {}
        tu_do: Dict[str, str] = {}
        for loai, c in tu_cam:
            if not c:
                continue
            if _giong_video_id(c) or _MAU_KENH_ID.fullmatch(c):
                self.token.setdefault(c, (loai, c))
            elif re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9_.\-]{2,29}", c):
                self.token.setdefault(c.lower(), (loai, c))
            else:
                tu_do.setdefault(c, loai)
        self.tu_do = tu_do
        self.mau = (re.compile("|".join(re.escape(c) for c in sorted(tu_do, key=len, reverse=True)))
                    if tu_do else None)

    def tim(self, dong: str) -> List[Tuple[str, str]]:
        ra: List[Tuple[str, str]] = []
        if self.token:
            for m in _MAU_TOKEN_11.finditer(dong):
                if m.group(0) in self.token:
                    ra.append(self.token[m.group(0)])
            for m in _MAU_KENH_ID.finditer(dong):
                if m.group(0) in self.token:
                    ra.append(self.token[m.group(0)])
            for m in _MAU_HANDLE.finditer(dong):
                k = "@" + m.group(1).lower()
                if k in self.token:
                    ra.append(self.token[k])
        if self.mau is not None:
            for m in self.mau.finditer(dong):
                ra.append((self.tu_do[m.group(0)], m.group(0)))
        return ra


#: Mẫu ít đặc trưng (số, id kênh) — giá trị MẪU rõ ràng trong tài liệu/test thì bỏ qua.
#: Không áp cho mẫu khoá: khoá thật không bao giờ được miễn vì "trông giả".
_MAU_LOC_GIA = frozenset(("chat id Telegram", "id kênh thật trong URL Studio"))
_GIA = re.compile(r"(.)\1{4,}|x{3,}|example|khongphaithat|dummy|fake|placeholder|123456|987654|abcdef", re.I)


def _la_mau_gia(s: str) -> bool:
    return bool(_GIA.search(s.split("/channel/")[-1] if "/channel/" in s else s))


def quet_noi_dung(rel: str, chu: str, khop: "_BoKhop",
                  mau_phu: Sequence[Tuple[str, "re.Pattern[str]"]] = ()) -> List[Tuple[str, str]]:
    """Soi NỘI DUNG một tệp. Trả `[(loại, trích ĐÃ CHE)]` — không bao giờ nguyên chuỗi."""
    ra: List[Tuple[str, str]] = []
    dong_yt = 0
    for so, dong in enumerate(chu.splitlines(), 1):
        if DAU_BO_QUA in dong:
            continue
        for ten_mau, mau in tuple(_MAU_THEM) + tuple(mau_phu):
            m = mau.search(dong)
            if m and ten_mau in _MAU_LOC_GIA and _la_mau_gia(m.group(0)):
                continue
            if m:
                ra.append((ten_mau, "dòng {0}: {1}".format(so, che(m.group(0), giu=4))))
        for m in _MAU_EMAIL.finditer(dong):
            if not _EMAIL_CHO_PHEP.search(m.group(0)) and not m.group(0).startswith("git@"):
                ra.append(("email", "dòng {0}: {1}".format(so, _che_email(m.group(0)))))
        for m in _MAU_DUONG_NGUOI_DUNG.finditer(dong):
            if m.group(1).lower() not in _TEN_NGUOI_DUNG_MAU:
                ra.append(("đường tuyệt đối có tên người dùng", "dòng {0}: …Users\\{1}".format(so, che(m.group(1)))))
        for loai, chuoi in khop.tim(dong):
            ra.append((loai, "dòng {0}: {1}".format(so, che(chuoi))))
        if so > 1 and _MAU_DONG_YT.search(dong):
            dong_yt += 1
    if dong_yt >= _NGUONG_DONG_YT and rel.lower().endswith((".csv", ".tsv", ".jsonl")):
        ra.append(("dữ liệu YouTube dạng bảng/dòng", "{0} dòng có URL/id kênh YouTube".format(dong_yt)))
    return ra


def quet_them(goc: str, tep: Iterable[str], tu_cam: Optional[Sequence[Tuple[str, str]]] = None) -> List[Tuple[str, str, str]]:
    """Lớp quét THÊM (ngoài `core.kiem_phat_hanh`): khoá, email, đường có tên
    người dùng, chuỗi riêng máy. Trả `[(tệp, loại, trích)]`."""
    khop = _BoKhop(list(tu_cam_cua_may(goc) if tu_cam is None else tu_cam))
    ra: List[Tuple[str, str, str]] = []
    for rel in tep:
        duong = os.path.join(goc, *rel.split("/"))
        if not os.path.isfile(duong):
            continue
        ly_do = duong_cam(rel)
        if ly_do:
            ra.append((rel, "đường cấm", ly_do))
        if not rel.lower().endswith(_DUOI_VAN_BAN + (".tsv", ".jsonl")):
            continue
        try:
            if os.path.getsize(duong) > 3 * 1024 * 1024:
                continue
            with io.open(duong, "rb") as f:
                chu = f.read().decode("utf-8", "replace")
        except OSError:
            continue
        ra += [(rel, loai, trich) for loai, trich in quet_noi_dung(rel, chu, khop)]
    return ra


def quet_bi_mat(goc: str, tep: Sequence[str]) -> List[str]:
    """`core.kiem_phat_hanh.quet_cay_sach` trên đúng danh sách `tep` (không chép
    cây) + `quet_them`. Trả danh sách dòng CHẶN."""
    from . import kiem_phat_hanh as kph  # noqa: PLC0415
    co_mat = [t for t in tep if os.path.isfile(os.path.join(goc, *t.split("/")))]
    cay = kph.CaySach(duong=goc, tep=tuple(co_mat), theo_doi=frozenset(co_mat))
    chan = ["[{0}] {1} — {2}".format(p.loai, p.duong, p.ghi_chu) for p in kph.quet_cay_sach(cay)]
    chan += ["[them:{1}] {0} — {2}".format(*x) for x in quet_them(goc, co_mat)]
    return chan


# ── quét TOÀN LỊCH SỬ kho (kiểm toán kho công khai: một lệnh) ─────────────────

#: Những gì có trên GitHub: nhánh chính của origin + mọi tag.
REF_CONG_KHAI = ("{0}/{1}".format(REMOTE, NHANH), "--tags")
_KICH_BLOB_TOI_DA = 3 * 1024 * 1024
#: 20 byte đầu của khối DPAPI (CryptProtectData) dạng hex.
_DAU_DPAPI_HEX = "01000000d08c9ddf" + "0115d1118c7a00c04fc297eb"
_DUOI_MEDIA = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".mp3", ".mp4", ".wav", ".ttf", ".otf",
               ".woff", ".woff2", ".zip", ".7z", ".exe", ".dll", ".pyd", ".npy", ".onnx", ".bin", ".pdf")


def _doc_blob_that(goc: str, shas: Sequence[str]) -> Iterable[Tuple[str, bytes]]:
    """Đọc hàng loạt blob qua MỘT tiến trình `git cat-file --batch` (ưu tiên thấp)."""
    import threading  # noqa: PLC0415
    co = _CO_AN | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    p = subprocess.Popen(["git", "cat-file", "--batch"], cwd=goc, stdin=subprocess.PIPE,  # noqa: S603
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=co)

    def ghi() -> None:
        try:
            for s in shas:
                p.stdin.write((s + "\n").encode("ascii"))
            p.stdin.close()
        except OSError:
            pass

    threading.Thread(target=ghi, daemon=True).start()
    try:
        for _ in shas:
            dau = p.stdout.readline().decode("ascii", "replace").split()
            if len(dau) < 3 or dau[1] == "missing":
                continue
            n = int(dau[2])
            du = p.stdout.read(n)
            p.stdout.read(1)
            yield dau[0], du
    finally:
        try:
            p.stdout.close()
        except OSError:
            pass
        p.wait(timeout=60)


_doc_blob: Callable[[str, Sequence[str]], Iterable[Tuple[str, bytes]]] = _doc_blob_that


def _git_vao(goc: str, tham_so: Sequence[str], vao: str, timeout: float = 600) -> str:
    try:
        ket = subprocess.run(["git", *tham_so], cwd=goc, input=vao.encode("utf-8"), capture_output=True,  # noqa: S603
                             timeout=timeout, creationflags=_CO_AN)
    except (OSError, subprocess.SubprocessError) as e:
        raise DongBoLoi("git {0} lỗi: {1}".format(" ".join(tham_so[:2]), e)) from e
    return ket.stdout.decode("utf-8", "replace")


def quet_lich_su(goc: str = GOC, refs: Sequence[str] = REF_CONG_KHAI, *,
                 tu_cam: Optional[Sequence[Tuple[str, str]]] = None,
                 in_ra: Callable[[str], None] = lambda s: None) -> List[Dict[str, Any]]:
    """Quét MỌI blob + MỌI đường từng có trong `refs` (mặc định: những gì đã lên
    GitHub). Trả danh sách phát hiện đã gộp theo (loại, tệp):
    `{loai, duong, commit: [...], trong_head, trich, chuoi?}` — `chuoi` (nguyên văn,
    chỉ để ghi tệp thay thế cho git filter-repo) KHÔNG bao giờ được in."""
    khop = _BoKhop(list(tu_cam_cua_may(goc, day_du=True) if tu_cam is None else tu_cam))
    nhanh_dau = next((r for r in refs if not r.startswith("-")), "HEAD")
    # 1) commit -> blob/đường (đường từng có, cả tệp đã xoá)
    log = _git_ok(goc, "log", *refs, "--root", "--raw", "--no-abbrev", "--no-renames", "-m",
                  "--format=@%h", timeout=900)
    commit_cua_blob: Dict[str, List[str]] = {}
    commit_cua_duong: Dict[str, List[str]] = {}
    duong_cua_blob: Dict[str, str] = {}
    hien = ""
    for d in log.splitlines():
        if d.startswith("@"):
            hien = d[1:].strip()
        elif d.startswith(":") and "\t" in d:
            dau, duong = d.split("\t", 1)
            phan = dau.split()
            if len(phan) >= 5 and phan[4][:1] in ("A", "M", "T", "C", "R"):
                blob = phan[3]
                ds = commit_cua_blob.setdefault(blob, [])
                if hien not in ds:
                    ds.append(hien)
                duong_cua_blob.setdefault(blob, duong)
                dc = commit_cua_duong.setdefault(duong, [])
                if hien not in dc:
                    dc.append(hien)
    # 2) HEAD công khai
    trong_head_blob: Dict[str, str] = {}
    for d in _git_ok(goc, "ls-tree", "-r", nhanh_dau).splitlines():
        dau, _, duong = d.partition("\t")
        phan = dau.split()
        if len(phan) >= 3 and phan[1] == "blob":
            trong_head_blob[phan[2]] = duong
    duong_head = set(trong_head_blob.values())
    # 3) mọi blob với kích thước
    obj = _git_ok(goc, "rev-list", "--objects", *refs, timeout=900)
    ung_vien: Dict[str, str] = {}
    for d in obj.splitlines():
        sha, _, duong = d.partition(" ")
        if duong:
            ung_vien.setdefault(sha, duong)
    kiem = _git_vao(goc, ["cat-file", "--batch-check"], "\n".join(ung_vien) + "\n")
    can_doc: List[str] = []
    for d in kiem.splitlines():
        phan = d.split()
        if len(phan) == 3 and phan[1] == "blob" and int(phan[2]) <= _KICH_BLOB_TOI_DA:
            duong = duong_cua_blob.get(phan[0]) or ung_vien.get(phan[0], "")
            # mọi blob trừ media đã biết; nhị phân khác bị nhận ra bằng byte NUL
            if not duong.lower().endswith(_DUOI_MEDIA):
                can_doc.append(phan[0])
    in_ra("  lịch sử: {0} đường, {1} blob văn bản cần soi.".format(len(commit_cua_duong), len(can_doc)))

    gop: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def them(loai: str, duong: str, commit: Sequence[str], trong_head: bool, trich: str,
             chuoi: str = "") -> None:
        k = (loai, duong)
        g = gop.setdefault(k, {"loai": loai, "duong": duong, "commit": [], "trong_head": False,
                               "trich": trich, "so": 0, "chuoi": set()})
        for c in commit:
            if c not in g["commit"]:
                g["commit"].append(c)
        g["trong_head"] = g["trong_head"] or trong_head
        g["so"] += 1
        if chuoi:
            g["chuoi"].add(chuoi)

    # 4) đường cấm (cả tệp đã xoá khỏi HEAD)
    for duong, cms in commit_cua_duong.items():
        ly_do = duong_cam(duong)
        if ly_do:
            them("đường cấm: " + ly_do, duong, cms, duong in duong_head, "")
    # 5) nội dung — thêm lớp mẫu của kiem_phat_hanh (mật khẩu, client_secret, cookie=…)
    mau_kph: Sequence[Tuple[str, "re.Pattern[str]"]] = ()
    try:
        from . import kiem_phat_hanh as kph  # noqa: PLC0415
        mau_kph = kph._MAU_NOI_DUNG_BI_MAT  # noqa: SLF001
    except Exception:  # noqa: BLE001
        pass
    for sha, du in _doc_blob(goc, can_doc):
        duong = trong_head_blob.get(sha) or duong_cua_blob.get(sha) or ung_vien.get(sha, "?")
        cms = commit_cua_blob.get(sha, ["?"])
        o_head = sha in trong_head_blob
        if b"\x00" in du[:4096]:  # nhị phân: chỉ nhận khối DPAPI
            if du[:20].hex().lower().startswith(_DAU_DPAPI_HEX[:16]) or _DAU_DPAPI_HEX in du[:512].hex().lower():
                them("khối DPAPI", duong, cms, o_head, "nhị phân")
            continue
        chu = du.decode("utf-8", "replace")
        for loai, trich in quet_noi_dung(duong, chu, khop, mau_phu=mau_kph):
            them(loai, duong, cms, o_head, trich)
        # nguyên văn (chỉ cho tệp thay thế — không in)
        for loai, c in khop.tim(chu):
            if (loai, duong) in gop:
                gop[(loai, duong)]["chuoi"].add(c)
        for ten_mau, mau in tuple(_MAU_THEM) + tuple(mau_kph):
            if (ten_mau, duong) in gop:
                gop[(ten_mau, duong)]["chuoi"].update(m.group(0) for m in mau.finditer(chu)
                                                      if DAU_BO_QUA not in m.group(0))
        if ("email", duong) in gop:
            gop[("email", duong)]["chuoi"].update(
                m.group(0) for m in _MAU_EMAIL.finditer(chu)
                if not _EMAIL_CHO_PHEP.search(m.group(0)) and not m.group(0).startswith("git@"))
    # 6) thông điệp commit + tác giả + tag có chú thích (cũng công khai trên GitHub)
    tdc = _git_ok(goc, "log", *refs, "--format=@@%h%n%an <%ae>%n%cn <%ce>%n%B", timeout=600)
    for khoi in tdc.split("@@")[1:]:
        cm, _, than = khoi.partition("\n")
        for loai, trich in quet_noi_dung("(thông điệp commit)", than, khop, mau_phu=mau_kph):
            them(loai, "(thông điệp/tác giả commit)", [cm.strip()], False, trich)
        for loai, c in khop.tim(than):
            if (loai, "(thông điệp/tác giả commit)") in gop:
                gop[(loai, "(thông điệp/tác giả commit)")]["chuoi"].add(c)
    tag = git(goc, "for-each-ref", "refs/tags", "--format=@@%(refname:short)%n%(taggername) %(taggeremail)%n%(contents)")[1]
    for khoi in tag.split("@@")[1:]:
        ten, _, than = khoi.partition("\n")
        for loai, trich in quet_noi_dung("(tag)", than, khop, mau_phu=mau_kph):
            them(loai, "(chú thích tag)", [ten.strip()], False, trich)
    return sorted(gop.values(), key=lambda g: (not g["trong_head"], g["loai"], g["duong"]))


_NANG = ("khoá", "token", "cookie", "refresh", "DPAPI", "Fernet", "PEM", "secrets.json", "SID", "mật khẩu", "hex")


def muc_do(loai: str) -> str:
    if any(k.lower() in loai.lower() for k in _NANG):
        return "NGHIÊM TRỌNG"
    if "email" in loai or "đường cấm" in loai or "kênh thật" in loai or "người dùng" in loai:
        return "CAO"
    return "VỪA"


def in_bang_lich_su(phat_hien: Sequence[Dict[str, Any]], in_ra: Callable[[str], None]) -> None:
    """In bảng phát hiện (ĐÃ CHE) + lệnh dọn lịch sử chủ kho tự chạy."""
    if not phat_hien:
        in_ra("Lịch sử sạch: không phát hiện nào.")
        return
    in_ra("| mức | loại | tệp | commit | còn ở HEAD | trích (đã che) |")
    in_ra("|---|---|---|---|---|---|")
    for g in phat_hien:
        cms = [c[:9] for c in g["commit"]]
        cm = ", ".join(cms[:3]) + (" … (+{0})".format(len(cms) - 3) if len(cms) > 3 else "")
        in_ra("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
            muc_do(g["loai"]), g["loai"], g["duong"], cm, "CÓ" if g["trong_head"] else "không",
            che_dong(str(g.get("trich") or ""))[:80]))
    duong = sorted({g["duong"] for g in phat_hien if g["loai"].startswith("đường cấm")})
    chuoi = sum(len(g.get("chuoi") or ()) for g in phat_hien)
    in_ra("")
    in_ra("Dọn lịch sử (CHỦ KHO tự quyết, chạy trên một bản clone --mirror mới):")
    if duong:
        in_ra("  git filter-repo --invert-paths " + " ".join("--path '{0}'".format(p) for p in duong))
    if chuoi:
        thong_diep = any(g["duong"].startswith("(") for g in phat_hien)
        in_ra("  git filter-repo --replace-text <tệp-thay-thế>{0}   # {1} chuỗi; tạo tệp: "
              "quet --lich-su --ghi-thay-the <tệp>".format(
                  " --replace-message <tệp-thay-thế>" if thong_diep else "", chuoi))
    in_ra("  rồi: git push --force --mirror origin  (mọi VPS: git fetch && git reset --hard origin/main);"
          " ĐỔI mọi khoá đã lộ — dọn lịch sử không thu hồi được bản đã bị sao.")


def thay_the_giu_hinh(ds: Sequence[str]) -> List[Tuple[str, str]]:
    """Mỗi chuỗi lộ -> một chuỗi MẪU RIÊNG cùng hình dạng (video id 11 ký tự, id kênh
    UC+22, @handle, email) để mã/test đọc id vẫn chạy sau khi viết lại lịch sử;
    còn lại (tiêu đề, tên, khoá) -> `***DA-XOA-n***`. Dài trước để chuỗi chứa nhau không vỡ."""
    ra: List[Tuple[str, str]] = []
    dem: Dict[str, int] = {}

    def so(k: str) -> int:
        dem[k] = dem.get(k, 0) + 1
        return dem[k]

    for c in sorted(set(ds), key=lambda s: (-len(s), s)):
        if _giong_video_id(c):
            ra.append((c, "VidMau%05d" % so("v")))
        elif _MAU_KENH_ID.fullmatch(c):
            ra.append((c, "UCkenhMau%015d" % so("uc")))
        elif re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9_.\-]{2,29}", c):
            ra.append((c, "@kenh-mau-%d" % so("h")))
        elif _MAU_EMAIL.fullmatch(c):
            ra.append((c, "nguoi%d@example.invalid" % so("e")))
        else:
            ra.append((c, "***DA-XOA-%d***" % so("x")))
    return ra


def ghi_tep_thay_the(phat_hien: Sequence[Dict[str, Any]], duong: str) -> int:
    """Tệp `--replace-text` cho git filter-repo (`literal:<chuỗi>==>mẫu`). Tệp CHỨA
    chuỗi thật — chỉ ghi ở máy này, ngoài kho (workspace/ đã bị .gitignore chặn)."""
    ds = [c for g in phat_hien for c in (g.get("chuoi") or ()) if c and "\n" not in c and "==>" not in c]
    cap = thay_the_giu_hinh(ds)
    with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
        for c, moi in cap:
            tep.write("literal:{0}==>{1}\n".format(c, moi))
    return len(cap)


# ═══ bài học dùng chung (chia-se/bai-hoc/<ma-may>-<ngach>.json) ═════════════


def _thu_muc_chia_se(goc: str) -> str:
    return os.path.join(goc, "chia-se", "bai-hoc")


def xuat_bai_hoc(goc: str = GOC, *, in_ra: Callable[[str], None] = print) -> List[str]:
    """Gom bài học phạm vi KÊNH, n ≥ 3 (`core.chien_luoc.bai_hoc.doc`) của mọi
    kênh cùng ngách trên máy này thành `chia-se/bai-hoc/<ma_may>-<ngach>.json`.
    Mỗi máy MỘT tệp riêng mỗi ngách → push không xung đột. Câu có tên kênh thật,
    video id, URL, email bị bỏ. Trả danh sách tệp đã ghi."""
    from .chien_luoc import bai_hoc as bh  # noqa: PLC0415
    from .kenh import liet_ke_kenh  # noqa: PLC0415
    cfg = doc_cau_hinh(goc)
    tu_cam = [c for _l, c in tu_cam_cua_may(goc)]
    theo_ngach: Dict[str, List[Dict[str, Any]]] = {}
    for ma in liet_ke_kenh(goc):
        ngach = bh._nhom(goc, ma)  # noqa: SLF001
        if not ngach:
            continue
        for b in bh.doc(goc, ma, tat_ca=True):
            if b.get("pham_vi") != "kenh" or not b.get("bom"):
                continue
            cau = str(b.get("cau") or "")
            if (any(c in cau for c in tu_cam) or re.search(r"https?://|www\.|@", cau)
                    or re.search(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{11}(?![A-Za-z0-9_-])", cau)
                    and re.search(r"[A-Z][a-z0-9_-]*[0-9]|[0-9][A-Za-z_-]*[A-Z]", cau)):
                continue
            theo_ngach.setdefault(ngach, []).append({
                "truc": b.get("truc"), "cum": b.get("cum") or "", "cau": cau, "n": b.get("n"),
                "dung_cho": b.get("dung_cho") or ["chon"], **({"khoa": b["khoa"]} if b.get("khoa") else {})})
    ra: List[str] = []
    os.makedirs(_thu_muc_chia_se(goc), exist_ok=True)
    for ngach, ds in sorted(theo_ngach.items()):
        # gộp trùng (cùng trục + cụm + câu) giữa các kênh cùng ngách
        thay: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for b in ds:
            k = (str(b["truc"]), str(b["cum"]), b["cau"])
            if k not in thay or int(b["n"] or 0) > int(thay[k]["n"] or 0):
                thay[k] = b
        du = {"ma_may": cfg["ma_may"], "ngach": ngach, "xuat_luc": time.strftime("%Y-%m-%d"),
              "ghi_chu": "Bài học phạm vi kênh (n>=3) của một VPS — máy khác đọc làm tiên nghiệm 'ngoai'.",
              "bai_hoc": sorted(thay.values(), key=lambda b: (str(b["truc"]), -int(b["n"] or 0)))}
        duong = os.path.join(_thu_muc_chia_se(goc), "{0}-{1}.json".format(cfg["ma_may"], _ma_may_hop_le(ngach)))
        with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
            tep.write("\n")
        ra.append(duong)
        in_ra("  bài học: {0} ({1} bài) -> {2}".format(ngach, len(thay), os.path.relpath(duong, goc)))
    return ra


def nhan_bai_hoc_ngoai(goc: str = GOC, *, in_ra: Callable[[str], None] = print) -> int:
    """Chép `chia-se/bai-hoc/<máy KHÁC>-<ngách>.json` vào
    `CHANNEL/_NHOM/<ngách>/bai-hoc-ngoai/` (nơi `bai_hoc._tu_ngoai` đọc) cho mọi
    ngách máy này có. Trả số tệp đã chép."""
    ma_may = doc_cau_hinh(goc)["ma_may"]
    so = 0
    for duong in glob.glob(os.path.join(_thu_muc_chia_se(goc), "*.json")):
        try:
            with io.open(duong, encoding="utf-8") as tep:
                du = json.load(tep)
        except (OSError, ValueError):
            continue
        if not isinstance(du, dict) or du.get("ma_may") == ma_may:
            continue
        ngach = str(du.get("ngach") or "")
        thu_muc_ngach = os.path.join(goc, "CHANNEL", "_NHOM", ngach)
        if not ngach or not os.path.isdir(thu_muc_ngach):
            continue
        dich = os.path.join(thu_muc_ngach, "bai-hoc-ngoai")
        os.makedirs(dich, exist_ok=True)
        shutil.copy2(duong, os.path.join(dich, os.path.basename(duong)))
        so += 1
    if so:
        in_ra("  nhận {0} tệp bài học của máy khác vào CHANNEL/_NHOM/*/bai-hoc-ngoai/".format(so))
    return so


# ═══ 3) day ═════════════════════════════════════════════════════════════════


def _dat_danh_tinh(goc: str, ma_may: str) -> None:
    """Tác giả commit = MÃ MÁY, email `.invalid` — email thật của người dùng
    (git config toàn cục) không bao giờ vào lịch sử kho chung."""
    email = git(goc, "config", "--local", "user.email")[1].strip()
    if not email or not email.endswith(".invalid"):
        git(goc, "config", "--local", "user.email", "{0}@mytool-vps.invalid".format(ma_may))
        git(goc, "config", "--local", "user.name", "MyTool {0}".format(ma_may))
    git(goc, "config", "--local", "core.quotepath", "false")


def _tep_dang_cho(goc: str) -> List[str]:
    """Tệp đã `git add` so với HEAD (A/M/R/C, không tính xoá)."""
    co_head = _co_ref(goc, "HEAD")
    if co_head:
        ra = _git_ok(goc, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    else:
        ra = _git_ok(goc, "ls-files", "-z")
    return [p.replace("\\", "/") for p in ra.split("\0") if p]


def _tep_doi_giua(goc: str, cu: str, moi: str) -> List[str]:
    ra = _git_ok(goc, "diff", "--name-only", "--diff-filter=ACMR", "-z", cu, moi)
    return [p for p in ra.split("\0") if p]


TEP_PHIEN_BAN = ("VERSION", "CHANGELOG.md")


def _dang_do_rebase(goc: str) -> bool:
    return (os.path.isdir(os.path.join(goc, ".git", "rebase-merge"))
            or os.path.isdir(os.path.join(goc, ".git", "rebase-apply")))


def _chon_tep(goc: str, chi: Sequence[str]) -> List[str]:
    """Chuẩn hoá danh sách `--chi` về đường tương đối kiểu git (dấu /)."""
    ra: List[str] = []
    for p in chi:
        p = str(p).strip()
        if not p:
            continue
        if os.path.isabs(p):
            p = os.path.relpath(p, goc)
        ra.append(p.replace("\\", "/"))
    return ra


def _thuoc_chon(p: str, chon: Sequence[str]) -> bool:
    """`p` (đường git, dấu /) có nằm trong một mục `--chi` (tệp hay thư mục) không."""
    for c in chon:
        c = c.rstrip("/")
        if c in ("", ".") or p == c or p.startswith(c + "/"):
            return True
    return False


def _tep_can_add(goc: str, chon: Sequence[str]) -> List[str]:
    """Mục `--chi` nào còn cần `git add -A`.

    Bỏ qua mục đã `git rm` sẵn (không còn trong chỉ mục lẫn trên đĩa) và mục
    đã `git rm --cached` rồi đưa vào .gitignore (còn trên đĩa nhưng bị chặn):
    `git add` gọi đích danh những đường đó sẽ báo lỗi, mà việc xoá đã nằm sẵn
    trong chỉ mục rồi."""
    ra: List[str] = []
    for p in chon:
        if git(goc, "ls-files", "--cached", "--", p)[1].strip():
            ra.append(p)
            continue
        if not os.path.exists(os.path.join(goc, p)):
            continue
        if git(goc, "check-ignore", "-q", "--", p)[0] == 0:
            continue
        ra.append(p)
    return ra


def _nang_phien_ban(goc: str, muc: str, thong_diep: str, ma_may: str,
                    in_ra: Callable[[str], None]) -> str:
    """Commit PHIÊN BẢN riêng (chỉ VERSION + 1 dòng CHANGELOG.md) trên HEAD rồi
    tag `v<x.y.z>`. Số mới = max(VERSION ở HEAD, ở origin) + `muc`, và tăng tiếp
    nếu tag đã có (máy khác vừa dùng). Trả số mới."""
    from . import cap_nhat_git as cng  # noqa: PLC0415
    tren_head = git(goc, "show", "HEAD:VERSION")[1].strip()
    tren_xa = git(goc, "show", "{0}/{1}:VERSION".format(REMOTE, NHANH))[1].strip()
    goc_so = tren_xa if cng.moi_hon(tren_xa, tren_head) else tren_head
    moi = cng.tang(goc_so or "0.0.0", muc)
    while _co_ref(goc, "refs/tags/v" + moi):
        moi = cng.tang(moi, "patch")
    with io.open(os.path.join(goc, "VERSION"), "w", encoding="utf-8", newline="\n") as tep:
        tep.write(moi)
    duong_cl = os.path.join(goc, "CHANGELOG.md")
    try:
        with io.open(duong_cl, encoding="utf-8-sig") as tep:
            chu = tep.read()
    except OSError:
        chu = "# Nhật ký phát hành\n"
    with io.open(duong_cl, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(cng.them_dong_changelog(chu, moi, time.strftime("%Y-%m-%d"), ma_may, thong_diep))
    _git_ok(goc, "add", "--", *TEP_PHIEN_BAN)
    _git_ok(goc, "commit", "-q", "-m", "v{0}: {1}\n\nMáy: {2}".format(moi, cng._mot_dong(thong_diep, 120), ma_may),  # noqa: SLF001
            "--", *TEP_PHIEN_BAN)
    _git_ok(goc, "tag", "v" + moi)
    in_ra("  phiên bản: {0} -> {1} ({2}), tag v{1}.".format(goc_so or "?", moi, muc))
    return moi


def _bo_phien_ban(goc: str, phien_ban: str) -> None:
    """Gỡ commit phiên bản vừa tạo (push bị từ chối) — CHỈ đụng VERSION/CHANGELOG,
    không `reset --hard` (máy có thể còn tệp dở của agent khác)."""
    git(goc, "tag", "-d", "v" + phien_ban)
    git(goc, "reset", "-q", "--soft", "HEAD~1")
    git(goc, "checkout", "HEAD", "--", *TEP_PHIEN_BAN)


def day(goc: str = GOC, thong_diep: str = "", *, bo_qua_test: bool = False,
        in_ra: Callable[[str], None] = print, khong_push: bool = False,
        muc: str = "patch", chi: Optional[Sequence[str]] = None) -> int:
    """Kiểm → commit → rebase lên origin → TỰ NÂNG VERSION (commit phiên bản
    riêng + dòng CHANGELOG + tag) → push nguyên tử (nhánh + tag).

    `muc`: "patch" (mặc định) | "minor" | "major". `chi`: chỉ commit các tệp/thư
    mục này (tệp dở của người khác để nguyên, rebase dùng --autostash).

    Mã thoát: 0 xong, 1 kiểm hỏng, 2 xung đột (đã huỷ rebase, commit cục bộ còn
    nguyên), 3 lỗi mạng/git."""
    if not la_kho_git(goc):
        in_ra("! Không phải kho Git.")
        return 3
    if muc not in ("patch", "minor", "major"):
        in_ra("! muc phải là patch/minor/major.")
        return 1
    nhanh = _nhanh_hien_tai(goc)
    if nhanh != NHANH:
        in_ra("! Đang ở nhánh '{0}', không phải '{1}' — dừng.".format(nhanh, NHANH))
        return 3
    if _dang_do_rebase(goc):
        in_ra("! Kho đang dở một lượt rebase — giải xong (hoặc `git rebase --abort`) rồi chạy lại.")
        return 2
    cfg = doc_cau_hinh(goc)
    _dat_danh_tinh(goc, cfg["ma_may"])
    chon = _chon_tep(goc, chi or [])
    if chon:
        # Chỉ commit đúng tệp đã chọn: chỉ mục (index) không được có tệp NGOÀI
        # lượt --chi, không thì `commit` cuốn luôn tệp người khác đã `git add`.
        # Tệp đã `git rm` / `git rm --cached` sẵn mà nằm trong --chi thì được.
        da_cho = [p for p in git(goc, "diff", "--cached", "--name-only", "-z")[1].split("\0") if p]
        ngoai = [p for p in da_cho if not _thuoc_chon(p, chon)]
        if ngoai:
            in_ra("! Đang có tệp đã `git add` sẵn ({0}) — không trộn vào lượt --chi.".format(
                ", ".join(ngoai[:8])))
            return 1
        them = _tep_can_add(goc, chon)
        if them:
            _git_ok(goc, "add", "-A", "--", *them)
    else:
        if cfg.get("xuat_bai_hoc"):
            try:
                xuat_bai_hoc(goc, in_ra=in_ra)
            except Exception as e:  # noqa: BLE001 — bài học hỏng không chặn việc đẩy mã
                in_ra("  (bỏ qua xuất bài học: {0})".format(e))
        _git_ok(goc, "add", "-A")

    def bo_chi_muc() -> None:
        if chon:
            git(goc, "reset", "-q", "--", *chon)
        else:
            git(goc, "reset", "-q")

    tep = _tep_dang_cho(goc)
    co_thay_doi = git(goc, "diff", "--cached", "--quiet")[0] != 0 or not _co_ref(goc, "HEAD")
    in_ra("--- {0} tệp thêm/sửa đang chờ commit{1} ---".format(len(tep), " (chọn lọc)" if chon else ""))

    if co_thay_doi:
        loi = bien_dich(goc, tep)
        if loi:
            bo_chi_muc()
            in_ra("! py_compile hỏng:\n  " + "\n  ".join(loi))
            return 1
        loi = kiem_khoi(goc, co_test=not bo_qua_test, in_ra=in_ra)
        if loi:
            bo_chi_muc()
            in_ra("! Kiểm khói hỏng — KHÔNG commit:\n" + "\n".join(loi))
            return 1
        chan = quet_bi_mat(goc, tep)
        if chan:
            bo_chi_muc()
            in_ra("! Quét bí mật/dữ liệu kênh CHẶN {0} mục — KHÔNG commit:".format(len(chan)))
            for c in chan[:60]:
                in_ra("  " + c)
            return 1
        in_ra("  quét bí mật: sạch.")
        if not thong_diep.strip():
            in_ra("! Thiếu thông điệp commit: day \"<thông điệp>\"")
            bo_chi_muc()
            return 1
        _git_ok(goc, "commit", "-q", "-m", thong_diep.strip() + "\n\nMáy: {0}".format(cfg["ma_may"]))
        in_ra("  đã commit.")

    if khong_push:
        in_ra("(khong_push) dừng trước khi đẩy — chưa nâng phiên bản.")
        return 0
    tom = thong_diep.strip() or git(goc, "log", "-1", "--format=%s")[1].strip()

    for lan in (1, 2, 3):
        ok, loi_f = fetch(goc)
        if not ok:
            in_ra("! fetch lỗi: " + loi_f[:300])
            return 3
        dich = "{0}/{1}".format(REMOTE, NHANH)
        if _co_ref(goc, dich):
            _truoc, sau = truoc_sau(goc)
            if sau:
                cu = _git_ok(goc, "rev-parse", "HEAD").strip()
                # Tệp dở (của agent khác, hay ngoài lượt --chi) đứng yên: --autostash
                # cất rồi trả lại đúng chỗ, không bị cuốn vào commit.
                tham = ["rebase"] + (["--autostash"] if tep_doi_cuc_bo(goc) else []) + [dich]
                ma, ra, err = git(goc, *tham)
                if ma != 0:
                    xung = git(goc, "diff", "--name-only", "--diff-filter=U")[1].split()
                    git(goc, "rebase", "--abort")
                    in_ra("! XUNG ĐỘT khi rebase lên {0} — đã huỷ rebase, commit của máy này còn nguyên.".format(dich))
                    in_ra("  Tệp xung đột: " + (", ".join(xung) or (err or ra).strip()[:300]))
                    in_ra("  Giải tay: git rebase origin/main → sửa → git add → git rebase --continue → day lại.")
                    return 2
                moi = _tep_doi_giua(goc, cu, "HEAD")
                loi = bien_dich(goc, moi) + kiem_khoi(goc, co_test=False, in_ra=in_ra)
                if loi:
                    in_ra("! Sau khi rebase lên mã mới của máy khác, kiểm khói HỎNG — chưa đẩy:\n" + "\n".join(loi))
                    return 1
        truoc, _sau = truoc_sau(goc)
        if not truoc:
            in_ra("Không có gì để đẩy — đã khớp origin.")
            return 0
        ban = _nang_phien_ban(goc, muc, tom, cfg["ma_may"], in_ra)
        ma, ra, err = git(goc, "push", "--atomic", "-u", REMOTE, "HEAD:" + NHANH, "refs/tags/v" + ban, timeout=300)
        if ma == 0:
            _luu_trang_thai(goc, day_cuoi=time.strftime("%Y-%m-%d %H:%M"), ban_cuoi=ban)
            _ghi_nhat_ky(goc, "day ok v{0}: {1}".format(ban, tom[:120]))
            try:
                from . import cap_nhat_git as cng  # noqa: PLC0415
                cng.kiem(goc, co_fetch=False)
            except Exception:  # noqa: BLE001
                pass
            in_ra("Đã đẩy lên {0}/{1} — phiên bản {2} (tag v{2}).".format(REMOTE, NHANH, ban))
            return 0
        _bo_phien_ban(goc, ban)
        chu = (err or ra).strip()
        if lan < 3 and ("rejected" in chu or "fetch first" in chu or "non-fast-forward" in chu
                        or "already exists" in chu):
            in_ra("  origin vừa có commit/tag mới của máy khác — kéo lại, rebase, tăng lại phiên bản.")
            continue
        in_ra("! push lỗi: " + chu[:400])
        if "Permission denied" in chu or "publickey" in chu or "denied" in chu:
            in_ra("  Deploy key của máy này chưa có quyền ghi (GitHub > Settings > Deploy keys > Allow write).")
        return 3
    return 3


# ═══ 4) keo — tự cập nhật trên máy sản xuất ═════════════════════════════════


def trong_khung(bay_gio: Optional[_dt.datetime] = None) -> bool:
    phut = (bay_gio or _dt.datetime.now()).minute
    return KHUNG_PHUT[0] <= phut <= KHUNG_PHUT[1]


def ly_do_chua_ranh(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Rỗng = được áp mã mới lúc này."""
    ly_do: List[str] = []
    if not trong_khung(bay_gio):
        ly_do.append("ngoài khung phút :{0:02d}–:{1:02d}".format(*KHUNG_PHUT))
    try:
        from . import an_toan_khoi_dong  # noqa: PLC0415
        kt = an_toan_khoi_dong.kiem_tra(goc, bay_gio)
        if not kt.get("duoc"):
            ly_do += list(kt.get("ly_do") or ["an_toan_khoi_dong chưa cho"])
    except Exception as e:  # noqa: BLE001
        ly_do.append("không kiểm được an_toan_khoi_dong: {0}".format(e))
    try:
        from . import khe  # noqa: PLC0415
        giu = khe.trang_thai(goc).get("nang")
        if giu:
            ly_do.append("khe nặng đang giữ: {0}".format(khe.mo_ta_nguoi_giu(giu)))
    except Exception:  # noqa: BLE001
        pass
    luot = _ly_do_may_ban_nang(goc)
    if luot:
        ly_do.append(luot)
    return ly_do


def _dung_ban_kiem(goc: str, ref: str, in_ra: Callable[[str], None]) -> List[str]:
    """Dựng `ref` trong git worktree tạm NGOÀI MyTool, py_compile + kiểm khói ở đó."""
    goc_tam = os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "shopapi-dong-bo-git")
    os.makedirs(goc_tam, exist_ok=True)
    tam = os.path.join(goc_tam, time.strftime("kiem-%Y%m%d-%H%M%S"))
    ma, ra, err = git(goc, "worktree", "add", "--detach", tam, ref, timeout=300)
    if ma != 0:
        return ["không dựng được worktree tạm: " + (err or ra).strip()[:300]]
    try:
        tat_ca_py = [p for p in _git_ok(goc, "ls-tree", "-r", "--name-only", "-z", ref).split("\0")
                     if p.endswith(".py")]
        loi = bien_dich(tam, tat_ca_py)
        in_ra("  bản kiểm: py_compile {0} tệp — {1}".format(len(tat_ca_py), "đạt" if not loi else "HỎNG"))
        if not loi:
            loi = kiem_khoi(tam, co_test=True, in_ra=in_ra)
        return loi
    finally:
        git(goc, "worktree", "remove", "--force", tam, timeout=120)
        shutil.rmtree(tam, ignore_errors=True)
        git(goc, "worktree", "prune")


def _don_tag_cu(goc: str) -> None:
    ra = git(goc, "tag", "--list", TIEN_TO_TAG + "*", "--sort=-creatordate")[1].split()
    for t in ra[GIU_TAG:]:
        git(goc, "tag", "-d", t)


def _tien_trinh_python() -> List[Tuple[int, str]]:
    if os.name != "nt":
        return []
    lenh = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
            "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
    ma, ra, _ = _chay(["powershell", "-NoProfile", "-NonInteractive", "-Command", lenh], timeout=60)
    ds: List[Tuple[int, str]] = []
    for d in ra.splitlines():
        pid, _, cmd = d.partition("\t")
        if pid.strip().isdigit():
            ds.append((int(pid), cmd))
    return ds


def _tim(ds: List[Tuple[int, str]], goc: str, ten_tep: str) -> List[int]:
    """PID có dòng lệnh chứa đúng đường `<goc>/<ten_tep>` (không khớp tên na ná)."""
    can = os.path.normcase(os.path.join(os.path.abspath(goc), ten_tep))
    ra = []
    for pid, cmd in ds:
        c = os.path.normcase(cmd.replace("/", os.sep))
        i = c.find(can)
        if i >= 0 and c[i + len(can):i + len(can) + 1] in ("", '"', " ", "'"):
            ra.append(pid)
    return ra


def _cong_nghe(cong: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", cong), timeout=2):
            return True
    except OSError:
        return False


def _mo_giao_dien(goc: str) -> bool:
    vbs = os.path.join(goc, "CHAY-GON.vbs")
    if not os.path.isfile(vbs):
        return False
    co = 0
    for ten in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
        co |= getattr(subprocess, ten, 0)
    try:
        subprocess.Popen(["wscript.exe", vbs], cwd=goc, creationflags=co, close_fds=True,  # noqa: S603
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def khoi_dong_lai(goc: str, *, in_ra: Callable[[str], None] = print) -> Dict[str, Any]:
    """Khởi động lại giao diện (và ba con vm/ — giao diện mới tự mở lại chúng qua
    `core.giam_sat_vm`). Chỉ gọi SAU khi `ly_do_chua_ranh` rỗng. Trả những gì
    ĐANG sống trước khi khởi động lại (để theo dõi)."""
    ds = _tien_trinh_python()
    gd = _tim(ds, goc, TEP_GIAO_DIEN)
    try:
        from . import trung_tam as tt  # noqa: PLC0415
        thu_muc_vm = tt.thu_muc_vm(goc)
    except Exception:  # noqa: BLE001
        thu_muc_vm = os.path.join(goc, "vm")
    con = [p for t in TEP_CON_VM for p in _tim(ds, thu_muc_vm, t)]
    truoc = {"giao_dien": bool(gd), "agent_vm": _cong_nghe(CONG_AGENT_VM)}
    if not gd:
        in_ra("  giao diện không chạy — không mở mới (máy này tự mở khi đăng nhập).")
        return truoc
    for pid in gd + con:
        _chay(["taskkill", "/PID", str(pid), "/T", "/F"], timeout=30)
    time.sleep(3)
    ok = _mo_giao_dien(goc)
    in_ra("  đã khởi động lại giao diện ({0}) + {1} tiến trình vm/.".format("mở lại OK" if ok else "MỞ LẠI HỎNG", len(con)))
    _ghi_nhat_ky(goc, "khoi dong lai giao dien pid={0} con_vm={1} mo_lai={2}".format(gd, con, ok))
    return truoc


def _theo_doi(goc: str, truoc: Dict[str, Any], phut: int, in_ra: Callable[[str], None],
              ngu: Callable[[float], None] = time.sleep) -> str:
    """Theo dõi sau cập nhật. '' = ổn; câu lý do = chết lặp (cần lùi)."""
    if phut <= 0:
        return ""
    han = time.time() + phut * 60
    an_han = time.time() + 180  # cho giao diện/agent 3 phút để lên
    hong_lien: Dict[str, int] = {"giao_dien": 0, "agent_vm": 0}
    lan_mo_lai = 0
    while time.time() < han:
        ngu(60)
        if time.time() < an_han:
            continue
        ds = _tien_trinh_python()
        song = {"giao_dien": bool(_tim(ds, goc, TEP_GIAO_DIEN)), "agent_vm": _cong_nghe(CONG_AGENT_VM)}
        for k in hong_lien:
            if truoc.get(k) and not song[k]:
                hong_lien[k] += 1
            else:
                hong_lien[k] = 0
        if hong_lien["giao_dien"] == 1 and lan_mo_lai < 2:
            lan_mo_lai += 1
            _mo_giao_dien(goc)
            in_ra("  theo dõi: giao diện không sống — mở lại lần {0}.".format(lan_mo_lai))
        for k, n in hong_lien.items():
            if n >= 3:
                return "{0} chết lặp sau cập nhật ({1} lần kiểm liền, đã mở lại {2} lần)".format(k, n, lan_mo_lai)
    return ""


def _lui(goc: str, tag: str, ly_do: str, in_ra: Callable[[str], None], sha_bo_qua: str = "") -> None:
    """Tự lùi sau cập nhật hỏng. Bản hỏng (`sha_bo_qua`) bị BỎ QUA ở các lượt
    nhịp sau — không thì cứ 30 phút lại cài lại đúng bản vừa làm chết máy."""
    in_ra("! LÙI về {0}: {1}".format(tag, ly_do))
    git(goc, "reset", "--hard", tag)
    _luu_trang_thai(goc, lui_cuoi={"tag": tag, "ly_do": ly_do[:400], "luc": time.strftime("%Y-%m-%d %H:%M")})
    _ghi_nhat_ky(goc, "LUI ve {0}: {1}".format(tag, ly_do[:300]))
    try:
        from . import cap_nhat_git as cng  # noqa: PLC0415
        cng.ghi_trang_thai(goc, bo_qua_sha=sha_bo_qua, hen_cap_nhat=False, hien_tai=cng.doc_phien_ban(goc))
        cng.ghi_ket_qua(goc, "da_lui", "tự lùi về {0}: {1}".format(tag, ly_do), tag=tag)
    except Exception:  # noqa: BLE001 — ghi trạng thái hỏng không được chặn việc lùi
        pass


def keo(goc: str = GOC, *, ep: bool = False, cho_toi_da_phut: Optional[int] = None,
        in_ra: Callable[[str], None] = print, ngu: Callable[[float], None] = time.sleep,
        bay_gio: Callable[[], _dt.datetime] = _dt.datetime.now) -> int:
    """Áp bản mới an toàn. Mã thoát: 0 (đã áp / không có gì mới / tắt / đang có
    lượt khác), 1 bản mới hỏng kiểm, 3 máy có sửa chưa đẩy / lỗi git, 4 chưa gặp
    lúc máy rảnh, 5 đã lùi sau cập nhật. Mọi kết quả ghi vào
    `workspace/cap-nhat/trang-thai.json` (giao diện đọc)."""
    from . import cap_nhat_git as cng  # noqa: PLC0415
    if not ep and not cng.doc_cau_hinh(goc)["tu_dong_cap_nhat"]:
        in_ra("Tự động cập nhật đang TẮT (cap-nhat.json: tu_dong_cap_nhat=false) — thoát. "
              "Bấm “Cập nhật ngay” trong Cài đặt, hoặc chạy `keo --ep`.")
        return 0
    if not la_kho_git(goc):
        in_ra("! Không phải kho Git — cài lại bằng CAI-DAT-VPS.bat (git clone) để tự cập nhật.")
        return 3
    if not cng.giu_khoa(goc, "keo"):
        in_ra("Đang có một lượt cập nhật khác chạy — thoát.")
        return 0
    try:
        return _keo(goc, ep=ep, cho_toi_da_phut=cho_toi_da_phut, in_ra=in_ra, ngu=ngu, bay_gio=bay_gio)
    finally:
        cng.nha_khoa(goc)


def _keo(goc: str, *, ep: bool, cho_toi_da_phut: Optional[int], in_ra: Callable[[str], None],
         ngu: Callable[[float], None], bay_gio: Callable[[], _dt.datetime]) -> int:
    from . import cap_nhat_git as cng  # noqa: PLC0415
    cfg = doc_cau_hinh(goc)
    if _nhanh_hien_tai(goc) != NHANH:
        in_ra("! Không ở nhánh {0} — không kéo.".format(NHANH))
        cng.ghi_ket_qua(goc, "chua_ap", "máy không ở nhánh {0}".format(NHANH))
        return 3
    doi = tep_doi_cuc_bo(goc)
    if doi:
        in_ra("! Máy này có sửa chưa đẩy ({0} tệp) — KHÔNG kéo đè. Chạy `python -m core.dong_bo_git day \"...\"` trước.".format(len(doi)))
        cng.ghi_trang_thai(goc, co_sua_chua_day=doi[:60])
        cng.ghi_ket_qua(goc, "chua_ap", "máy có sửa chưa đẩy ({0} tệp)".format(len(doi)))
        return 3
    ok, loi = fetch(goc)
    if not ok:
        in_ra("! fetch lỗi: " + loi[:300])
        cng.ghi_ket_qua(goc, "loi", "không nối được GitHub: " + loi[:200])
        return 3
    dich = "{0}/{1}".format(REMOTE, NHANH)
    if not _co_ref(goc, dich):
        in_ra("origin chưa có nhánh {0} — không có gì để kéo.".format(NHANH))
        return 0
    truoc, sau = truoc_sau(goc)
    if not sau:
        in_ra("Đã mới nhất." + ("" if not truoc else " (máy này có {0} commit chưa đẩy)".format(truoc)))
        cng.ghi_trang_thai(goc, hen_cap_nhat=False)
        cng.kiem(goc, co_fetch=False)
        return 0
    if truoc:
        in_ra("! Máy này có {0} commit chưa đẩy, origin có {1} commit mới — không fast-forward được. "
              "Chạy `day` để rebase + đẩy.".format(truoc, sau))
        cng.ghi_ket_qua(goc, "chua_ap", "máy có {0} commit chưa đẩy lên kho".format(truoc))
        return 3
    moi = _git_ok(goc, "rev-parse", dich).strip()
    ban_moi = git(goc, "show", dich + ":VERSION")[1].strip() or moi[:10]
    ban_cu = cng.doc_phien_ban(goc) or "?"
    in_ra("origin có {0} commit mới (bản {1}, {2}) — dựng bản kiểm…".format(sau, ban_moi, moi[:10]))
    # Dựng + kiểm là việc vừa-nặng: chỉ làm khi máy rảnh (nhịp đã kiểm trước khi sinh,
    # nhưng `keo --ep` chạy tay thì chưa).
    cho = cfg["cho_toi_da_phut"] if cho_toi_da_phut is None else cho_toi_da_phut
    ly_do = ly_do_chua_ranh(goc, bay_gio())
    if ly_do and not cho:
        in_ra("  máy chưa rảnh — để lượt sau: {0}".format("; ".join(ly_do)[:200]))
        cng.ghi_trang_thai(goc, quyet="cho", quyet_ly_do="; ".join(ly_do)[:300])
        return 4
    loi_kiem = _dung_ban_kiem(goc, moi, in_ra)
    if loi_kiem:
        in_ra("! Bản mới HỎNG kiểm — không áp:\n" + "\n".join(loi_kiem)[:3000])
        _luu_trang_thai(goc, ban_hong=moi)
        cng.ghi_trang_thai(goc, bo_qua_sha=moi, hen_cap_nhat=False)
        cng.ghi_ket_qua(goc, "hong_kiem", "bản {0} hỏng kiểm, không áp (bỏ qua tới khi có bản mới hơn): {1}".format(
            ban_moi, "; ".join(loi_kiem)[:250]), len=ban_moi)
        return 1

    han = time.time() + cho * 60
    from . import khe  # noqa: PLC0415
    phien = None
    while True:
        ly_do = ly_do_chua_ranh(goc, bay_gio())
        if not ly_do:
            phien = khe.thu_giu(goc, khe.LOP_NANG, "cap_nhat_git", uu_tien=1)
            if phien is not None:
                break
            ly_do = ["không giành được khe nặng"]
        if time.time() >= han:
            in_ra("! Chưa gặp lúc máy rảnh ({0} phút): {1}".format(cho, "; ".join(ly_do)[:300]))
            cng.ghi_trang_thai(goc, quyet="cho", quyet_ly_do="; ".join(ly_do)[:300])
            return 4
        in_ra("  chờ máy rảnh: {0}".format("; ".join(ly_do)[:200]))
        ngu(300)

    tag = TIEN_TO_TAG + time.strftime("%Y%m%d-%H%M%S")
    try:
        if tep_doi_cuc_bo(goc):
            in_ra("! Vừa có sửa cục bộ trong lúc chờ — không kéo đè.")
            cng.ghi_ket_qua(goc, "chua_ap", "vừa có sửa cục bộ trong lúc chờ")
            return 3
        cu = _git_ok(goc, "rev-parse", "HEAD").strip()
        _git_ok(goc, "tag", tag, cu)
        ma, ra, err = git(goc, "merge", "--ff-only", moi)
        if ma != 0:
            in_ra("! merge --ff-only lỗi: " + (err or ra).strip()[:300])
            git(goc, "reset", "--hard", tag)
            cng.ghi_ket_qua(goc, "loi", "merge --ff-only lỗi: " + (err or ra).strip()[:200])
            return 3
        doi_moi = _tep_doi_giua(goc, cu, "HEAD")
        loi = bien_dich(goc, doi_moi) + kiem_khoi(goc, co_test=False, in_ra=in_ra)
        if loi:
            _lui(goc, tag, "kiểm khói sau khi áp hỏng: " + "; ".join(loi)[:300], in_ra, sha_bo_qua=moi)
            return 5
        try:
            nhan_bai_hoc_ngoai(goc, in_ra=in_ra)
        except Exception as e:  # noqa: BLE001
            in_ra("  (bỏ qua nhận bài học: {0})".format(e))
        in_ra("Đã áp {0} -> {1} (lùi được bằng tag {2}).".format(cu[:10], moi[:10], tag))
        _ghi_nhat_ky(goc, "ap {0} -> {1} tag {2}".format(cu[:10], moi[:10], tag))
        _luu_trang_thai(goc, keo_cuoi="{0}: đã áp {1}".format(time.strftime("%Y-%m-%d %H:%M"), moi[:10]),
                        tag_lui=tag)
        cng.ghi_trang_thai(goc, hen_cap_nhat=False, bo_qua_sha="", hien_tai=ban_moi, ban_moi="",
                           thay_doi=[], so_commit_moi=0)
        cng.ghi_ket_qua(goc, "thanh_cong", "đã cập nhật {0} → {1}".format(ban_cu, ban_moi),
                        tu=ban_cu, len=ban_moi, tag=tag)
    finally:
        phien.nha()

    if cfg.get("khoi_dong_lai"):
        truoc_kd = khoi_dong_lai(goc, in_ra=in_ra)
        ly_do_lui = _theo_doi(goc, truoc_kd, int(cfg["theo_doi_phut"]), in_ra, ngu)
        if ly_do_lui:
            _lui(goc, tag, ly_do_lui, in_ra, sha_bo_qua=moi)
            khoi_dong_lai(goc, in_ra=in_ra)
            return 5
    _don_tag_cu(goc)
    return 0


def lui_ban(goc: str = GOC, tag: Optional[str] = None, *, in_ra: Callable[[str], None] = print,
            bay_gio: Callable[[], _dt.datetime] = _dt.datetime.now) -> int:
    """Nút "Quay lại bản trước": `reset --hard` về tag `truoc-cap-nhat-*` (mới nhất,
    hoặc `tag`) — chỉ khi cây sạch + máy rảnh; rồi khởi động lại giao diện. Bản
    đang có trên kho bị BỎ QUA (không tự cài lại) cho tới khi có bản mới hơn.
    Mã: 0 xong/đang có lượt khác, 3 lỗi/cây bẩn, 4 máy chưa rảnh (nhịp tự thử lại)."""
    from . import cap_nhat_git as cng  # noqa: PLC0415
    if not la_kho_git(goc):
        in_ra("! Không phải kho Git.")
        return 3
    if not cng.giu_khoa(goc, "lui"):
        in_ra("Đang có một lượt cập nhật khác chạy — thoát.")
        return 0
    try:
        tags = cng.tag_lui(goc)
        tag = tag or (tags[0] if tags else "")
        if not tag or not _co_ref(goc, "refs/tags/" + tag):
            in_ra("! Không có tag để quay lại.")
            cng.ghi_trang_thai(goc, hen_quay_lai="")
            cng.ghi_ket_qua(goc, "loi", "không có bản trước để quay lại")
            return 3
        doi = tep_doi_cuc_bo(goc)
        if doi:
            in_ra("! Máy có sửa chưa đẩy ({0} tệp) — không quay lại.".format(len(doi)))
            cng.ghi_ket_qua(goc, "chua_ap", "máy có sửa chưa đẩy — chưa quay lại được")
            return 3
        ly_do = ly_do_chua_ranh(goc, bay_gio())
        from . import khe  # noqa: PLC0415
        phien = None if ly_do else khe.thu_giu(goc, khe.LOP_NANG, "cap_nhat_git", uu_tien=1)
        if phien is None:
            ly = "; ".join(ly_do or ["không giành được khe nặng"])
            in_ra("  máy chưa rảnh — quay lại sau: " + ly[:200])
            cng.ghi_trang_thai(goc, quyet="cho", quyet_ly_do=ly[:300])
            return 4
        try:
            ban_cu = cng.doc_phien_ban(goc) or "?"
            sha_xa = git(goc, "rev-parse", "{0}/{1}".format(REMOTE, NHANH))[1].strip()
            _git_ok(goc, "reset", "--hard", tag)
            ban = cng.doc_phien_ban(goc) or "?"
            cng.ghi_trang_thai(goc, hen_quay_lai="", hen_cap_nhat=False, bo_qua_sha=sha_xa, hien_tai=ban)
            cng.ghi_ket_qua(goc, "da_quay_lai", "đã quay lại {0} → {1} (theo yêu cầu); bỏ qua bản trên kho "
                            "tới khi có bản mới hơn".format(ban_cu, ban), tu=ban_cu, len=ban, tag=tag)
            _ghi_nhat_ky(goc, "QUAY LAI ve {0} ({1} -> {2})".format(tag, ban_cu, ban))
            in_ra("Đã quay lại {0} ({1} → {2}).".format(tag, ban_cu, ban))
        finally:
            phien.nha()
        if doc_cau_hinh(goc).get("khoi_dong_lai"):
            khoi_dong_lai(goc, in_ra=in_ra)
        cng.kiem(goc, co_fetch=False)
        return 0
    finally:
        cng.nha_khoa(goc)


# ═══ 5) lịch Windows ════════════════════════════════════════════════════════


def dang_ky_lich(goc: str = GOC) -> Tuple[bool, str]:
    """Kiểm cập nhật chạy trong gác tổng (`core.cap_nhat_git.nhip`, mỗi 15') →
    bảo đảm lịch `ShopAPI-GacTong`, và GỠ lịch `ShopAPI-DongBoGit` 03:40 cũ."""
    from . import lich_tu_chay as ltc  # noqa: PLC0415
    ok1, cau1 = ltc.dang_ky_gac_tong(goc)
    ok2, cau2 = ltc.huy_dong_bo_git(goc)
    return ok1 and ok2, cau1 + "\n" + cau2


def huy_lich(goc: str = GOC) -> Tuple[bool, str]:
    """Chỉ gỡ lịch 03:40 cũ. Muốn tắt tự cập nhật: công tắc trong Cài đặt, hoặc
    `python -m core.cap_nhat_git tu_dong tat` (gác tổng còn nhiều việc khác)."""
    from . import lich_tu_chay as ltc  # noqa: PLC0415
    return ltc.huy_dong_bo_git(goc)


# ═══ dòng lệnh ══════════════════════════════════════════════════════════════


def _in_an_toan(s: str) -> None:
    # Không bao giờ in/ghi nhật ký chuỗi giống khoá/token/email (vd stderr của git).
    s = che_dong(s)
    try:
        print(s, flush=True)
    except (UnicodeEncodeError, OSError, AttributeError):
        pass
    if s.startswith("!"):
        _ghi_nhat_ky(GOC, s)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.dong_bo_git",
                                 description="Đồng bộ hai chiều với kho chung GitHub.")
    ap.add_argument("--goc", default=GOC)
    sub = ap.add_subparsers(dest="lenh")
    sub.add_parser("ket_noi")
    sub.add_parser("trang_thai")
    p = sub.add_parser("day")
    p.add_argument("thong_diep", nargs="?", default="")
    p.add_argument("--bo-qua-test", action="store_true")
    p.add_argument("--khong-push", action="store_true", help="kiểm + commit, không đẩy")
    nhom = p.add_mutually_exclusive_group()
    nhom.add_argument("--minor", action="store_true", help="nâng x.Y.0 (mặc định +patch)")
    nhom.add_argument("--major", action="store_true", help="nâng X.0.0")
    p.add_argument("--chi", nargs="+", default=None, metavar="TỆP",
                   help="chỉ commit các tệp/thư mục này (tệp dở của người khác để nguyên)")
    p = sub.add_parser("keo")
    p.add_argument("--ep", action="store_true", help="bỏ qua tu_dong_cap_nhat (vẫn giữ khung giờ/máy rảnh)")
    p.add_argument("--cho-toi-da-phut", type=int, default=None)
    p = sub.add_parser("lui", help="quay lại bản trước (tag truoc-cap-nhat-*)")
    p.add_argument("--tag", default=None)
    sub.add_parser("kiem", help="kiểm có bản mới không")
    sub.add_parser("bai_hoc")
    p = sub.add_parser("quet", help="quét bí mật trên các tệp git sẽ theo dõi")
    p.add_argument("--lich-su", action="store_true",
                   help="quét TOÀN LỊCH SỬ những gì đã lên GitHub (origin/main + tag), in bảng")
    p.add_argument("--ref", nargs="+", default=None, metavar="REF",
                   help="ref thay cho origin/main --tags (vd --all)")
    p.add_argument("--ghi-thay-the", default=None, metavar="TỆP",
                   help="ghi tệp --replace-text cho git filter-repo (CHỨA chuỗi thật — để ngoài kho)")
    p = sub.add_parser("lich")
    p.add_argument("viec", choices=("bat", "tat"))
    ns = ap.parse_args(argv)
    goc = os.path.abspath(ns.goc)
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
    try:
        if ns.lenh == "ket_noi":
            return 0 if ket_noi(goc, in_ra=_in_an_toan).get("host_name") else 3
        if ns.lenh == "trang_thai":
            trang_thai(goc, in_ra=_in_an_toan)
            return 0
        if ns.lenh == "day":
            return day(goc, ns.thong_diep, bo_qua_test=ns.bo_qua_test, in_ra=_in_an_toan,
                       khong_push=ns.khong_push, chi=ns.chi,
                       muc="major" if ns.major else ("minor" if ns.minor else "patch"))
        if ns.lenh == "keo":
            return keo(goc, ep=ns.ep, cho_toi_da_phut=ns.cho_toi_da_phut, in_ra=_in_an_toan)
        if ns.lenh == "lui":
            return lui_ban(goc, ns.tag, in_ra=_in_an_toan)
        if ns.lenh == "kiem":
            from . import cap_nhat_git as cng  # noqa: PLC0415
            tt = cng.kiem(goc)
            _in_an_toan(cng.tom_tat(tt))
            for d in tt.get("thay_doi") or []:
                _in_an_toan("  {phien_ban} ({ngay}, {may}): {noi_dung}".format(**d))
            if tt.get("co_sua_chua_day"):
                _in_an_toan("  ! máy có {0} tệp sửa chưa đẩy — không tự cập nhật.".format(
                    len(tt["co_sua_chua_day"])))
            return 0
        if ns.lenh == "bai_hoc":
            xuat_bai_hoc(goc, in_ra=_in_an_toan)
            return 0
        if ns.lenh == "quet" and ns.lich_su:
            duong_tt = os.path.abspath(ns.ghi_thay_the) if ns.ghi_thay_the else ""
            # tệp thay thế CHỨA chuỗi thật: chỉ ngoài kho, hoặc trong thư mục kho cấm (workspace/)
            if duong_tt and os.path.normcase(duong_tt).startswith(os.path.normcase(goc + os.sep)) and \
                    not duong_cam(os.path.relpath(duong_tt, goc).replace("\\", "/")):
                _in_an_toan("! --ghi-thay-the phải nằm NGOÀI kho hoặc trong workspace/ (bị .gitignore chặn).")
                return 3
            ph = quet_lich_su(goc, tuple(ns.ref) if ns.ref else REF_CONG_KHAI, in_ra=_in_an_toan)
            in_bang_lich_su(ph, _in_an_toan)
            if duong_tt:
                _in_an_toan("  đã ghi {0} chuỗi vào {1} — XOÁ tệp sau khi dọn.".format(
                    ghi_tep_thay_the(ph, duong_tt), duong_tt))
            return 1 if ph else 0
        if ns.lenh == "quet":
            tep =[p for p in _git_ok(goc, "ls-files", "-co", "--exclude-standard", "-z").split("\0") if p]
            chan = quet_bi_mat(goc, tep)
            _in_an_toan("{0} tệp, {1} mục chặn.".format(len(tep), len(chan)))
            for c in chan:
                _in_an_toan("  " + c)
            return 1 if chan else 0
        if ns.lenh == "lich":
            ok, cau = dang_ky_lich(goc) if ns.viec == "bat" else huy_lich(goc)
            _in_an_toan(cau)
            return 0 if ok else 3
    except DongBoLoi as e:
        _in_an_toan("! " + str(e))
        return 3
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
