# -*- coding: utf-8 -*-
"""Đóng gói BẢN SẠCH MyTool cho VPS mới / ngách mới (16/10/2026, làm lại 22/10/2026).

    python -X utf8 scripts\\dong_goi_ban_sach.py                      # ra <cha của MyTool>\\BAN-SACH\\MyTool-sach-v<VERSION>.zip
    python -X utf8 scripts\\dong_goi_ban_sach.py --ra D:\\tam --tai-nguyen C:\\...\\MyTool --ref HEAD

Gói (giải nén vào `Documents\\TL\\`):
    MyTool/                     mã tại `--ref` (`git archive` — đúng những gì đã commit), trừ dữ liệu ngách máy đầu
                                (`CHANNEL/_NHOM/`, `chia-se/bai-hoc/*.json`); + `models/faster-whisper-small/`,
                                `runtime/ffmpeg-goi/`, `ui_qt/mau_phong_cach/` (ảnh mẫu phong cách, bị .gitignore chặn khỏi
                                kho) lấy từ `--tai-nguyen`; + `cap-nhat.json` tắt tự cập nhật (máy này không nối GitHub).
    khoi-tao/                   mẫu đầu vào ngach.txt / giong.txt / doi-thu.txt (`docs/ban-sach/khoi-tao-mau/`).
    kho/DAT-CHROME-VAO-DAY.txt  chỗ đặt Chrome Portable đã đăng nhập Gmail.
    HUONG-DAN.txt, PROMPT-SESSION-MAY-MOI.md, BAI-HOC-VPS-1.md   (`docs/ban-sach/`).

KHÔNG có: dữ liệu kênh (CHANNEL/<mã>), workspace/, logs, nhật ký, kho, bi-mat, config.json/secrets.json, vm/config.json,
mô hình đã học / bộ nhớ đệm, PROJECTS/. Trước khi ghi zip: quét bí mật + chuỗi riêng của máy (tên kênh thật, video id, email,
khoá, UC id) bằng chính bộ quét của `core.dong_bo_git`/`core.kiem_phat_hanh` trên cây đã xuất — có phát hiện thì DỪNG.

TẤT ĐỊNH: thứ tự tệp sắp xếp, thời điểm mọi tệp = thời điểm commit `--ref`, nén deflate mức 6 — cùng ref + cùng tài
nguyên → cùng nội dung zip.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from typing import Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Đường (theo cây `git archive`) KHÔNG đi vào gói: hồ sơ/bài học của ngách máy đầu.
LOAI_TRU = (re.compile(r"^CHANNEL/_NHOM/"), re.compile(r"^chia-se/bai-hoc/.+\.json$"))
#: Tài nguyên không có trong kho git — chép từ `--tai-nguyen` (thư mục MyTool đang chạy).
TAI_NGUYEN = ("models/faster-whisper-small", "runtime/ffmpeg-goi", "ui_qt/mau_phong_cach")
TAI_NGUYEN_BAT_BUOC = ("models/faster-whisper-small", "runtime/ffmpeg-goi")
CAP_NHAT_TAT = ('{\n  "_ghi_chu": "Ban sach: may nay KHONG noi GitHub - tat tu cap nhat. Muon ban moi thi xin goi moi.",\n'
                '  "kho": "",\n  "tu_dong_cap_nhat": false,\n  "kiem_moi_phut": 30\n}\n')
DAT_CHROME = ("Dat moi Chrome Portable DA DANG NHAP Gmail vao day, moi Chrome mot thu muc:\r\n"
              "    kho\\<ten tuy y>\\<ten tuy y>.exe\r\n"
              "Moi Chrome = mot kenh. May tu dat ten ma kenh (K1, K2...) khi khoi tao. Xem HUONG-DAN.txt.\r\n")
DUOI_VAN_BAN = (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".js", ".html", ".css", ".bat", ".vbs", ".ini",
                ".cfg", ".toml", ".example", ".svg")


def _git(goc: str, *ts: str) -> bytes:
    p = subprocess.run(["git", "-C", goc, *ts], capture_output=True, check=False)
    if p.returncode != 0:
        raise SystemExit("git {0} lỗi: {1}".format(" ".join(ts[:2]), p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout


def bi_loai(rel: str) -> bool:
    return any(m.search(rel) for m in LOAI_TRU)


def doc_archive(goc: str, ref: str) -> Tuple[Dict[str, bytes], Tuple[int, ...], str]:
    """{đường: nội dung} của `git archive <ref>` (trừ `LOAI_TRU`), thời điểm commit (date_time zip), VERSION."""
    tho = _git(goc, "archive", "--format=tar", ref)
    tep: Dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(tho), mode="r:") as t:
        for m in t.getmembers():
            if not m.isfile() or bi_loai(m.name):
                continue
            tep[m.name] = t.extractfile(m).read()
    luc = int(_git(goc, "log", "-1", "--format=%ct", ref).decode().strip())
    d = _dt.datetime.utcfromtimestamp(luc)
    ver = tep.get("VERSION", b"0").decode("utf-8").strip()
    return tep, (d.year, d.month, d.day, d.hour, d.minute, d.second), ver


def tep_tai_nguyen(tai_nguyen: str) -> List[Tuple[str, str]]:
    """[(đường trong gói dưới MyTool/, đường trên đĩa)] của các thư mục tài nguyên, sắp xếp."""
    ra = []
    for thu in TAI_NGUYEN:
        goc_thu = os.path.join(tai_nguyen, *thu.split("/"))
        if not os.path.isdir(goc_thu):
            if thu in TAI_NGUYEN_BAT_BUOC:
                raise SystemExit("thiếu tài nguyên {0} trong {1} (--tai-nguyen)".format(thu, tai_nguyen))
            continue
        for g, ds, ts in os.walk(goc_thu):
            ds.sort()
            for t in sorted(ts):
                if t.endswith((".pyc", ".tmp", ".tam")) or "__pycache__" in g:
                    continue
                p = os.path.join(g, t)
                ra.append((os.path.relpath(p, tai_nguyen).replace("\\", "/"), p))
    return sorted(ra)


def tai_lieu_goc(tep: Dict[str, bytes]) -> Dict[str, bytes]:
    """Tệp ở GỐC gói (ngoài MyTool/): hướng dẫn + mẫu đầu vào + chỗ đặt kho, lấy từ `docs/ban-sach/` của chính cây."""
    ra: Dict[str, bytes] = {}
    for ten in ("HUONG-DAN.txt", "PROMPT-SESSION-MAY-MOI.md", "BAI-HOC-VPS-1.md"):
        nd = tep.get("docs/ban-sach/" + ten)
        if nd is None:
            raise SystemExit("thiếu docs/ban-sach/{0} trong ref — commit tài liệu trước khi đóng gói".format(ten))
        ra[ten] = nd.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n") if ten.endswith(".txt") else nd
    for rel, nd in tep.items():
        if rel.startswith("docs/ban-sach/khoi-tao-mau/"):
            ra["khoi-tao/" + rel.rsplit("/", 1)[1]] = nd
    ra["kho/DAT-CHROME-VAO-DAY.txt"] = DAT_CHROME.encode("utf-8")
    return ra


def quet(goc: str, tep: Dict[str, bytes], goc_du_lieu: str) -> List[str]:
    """Xuất các tệp VĂN BẢN của gói ra thư mục tạm rồi chạy bộ quét phát hành (bí mật, email, khoá, UC id, tên kênh /
    video id THẬT của máy đọc từ `goc_du_lieu`). Trả danh sách dòng CHẶN (rỗng = sạch)."""
    sys.path.insert(0, goc)
    from core import dong_bo_git as dbg  # noqa: PLC0415
    tam = tempfile.mkdtemp(prefix="ban-sach-quet-")
    try:
        ds = []
        for rel, nd in tep.items():
            if not rel.lower().endswith(DUOI_VAN_BAN) and "." in rel.rsplit("/", 1)[-1]:
                continue
            p = os.path.join(tam, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(nd)
            ds.append(rel)
        from core import kiem_phat_hanh as kph  # noqa: PLC0415
        cay = kph.CaySach(duong=tam, tep=tuple(ds), theo_doi=frozenset(ds))
        chan = ["[{0}] {1} — {2}".format(p.loai, p.duong, p.ghi_chu) for p in kph.quet_cay_sach(cay)]
        chan += ["[them:{1}] {0} — {2}".format(*x) for x in dbg.quet_them(tam, ds, dbg.tu_cam_cua_may(goc_du_lieu))]
        return chan
    finally:
        shutil.rmtree(tam, ignore_errors=True)


def chuoi_may(goc_du_lieu: str) -> List[str]:
    """Lớp quét THỨ HAI, thuần chuỗi: tên/handle/UC kênh thật (kenh.yaml, `vm/logs/tao-kenh/*.json`, `vm/logs/kenh-uc.json`)
    + video id kênh thật (`CHANNEL/<k>/chi-so/<id>/`). 22/10/2026: một tên kênh thật nằm trong một bài kiểm mà bộ quét
    phát hành không bắt — lớp này bắt bằng so chuỗi thẳng."""
    import glob  # noqa: PLC0415
    import json  # noqa: PLC0415
    ra = set()
    for y in glob.glob(os.path.join(goc_du_lieu, "CHANNEL", "*", "kenh.yaml")):
        if os.path.basename(os.path.dirname(y)).startswith("_"):
            continue
        with io.open(y, encoding="utf-8", errors="replace") as f:
            for d in f:
                m = re.match(r"^\s*(ten|handle|channel_id|kenh_id)\s*:\s*[\"']?(.+?)[\"']?\s*$", d)
                if m:
                    v = re.split(r"\s+[—-]\s+", m.group(2))[0].strip()
                    if len(v) >= 4 and not v.startswith("("):
                        ra.add(v)
        for d in glob.glob(os.path.join(os.path.dirname(y), "chi-so", "*")):
            t = os.path.basename(d)
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", t) and re.search(r"[A-Z]", t) and re.search(r"[a-z0-9]", t):
                ra.add(t)
    for j in glob.glob(os.path.join(goc_du_lieu, "vm", "logs", "tao-kenh", "*.json")):
        try:
            with io.open(j, encoding="utf-8") as f:
                d = json.load(f)
            ra.update(str(d.get(k)).strip() for k in ("ten", "handle", "uc") if len(str(d.get(k) or "").strip()) >= 4)
        except (OSError, ValueError, AttributeError):
            continue
    try:
        with io.open(os.path.join(goc_du_lieu, "vm", "logs", "kenh-uc.json"), encoding="utf-8") as f:
            ra.update(v for v in json.load(f).values() if isinstance(v, str) and len(v) >= 10)
    except (OSError, ValueError, AttributeError):
        pass
    return sorted(ra)


def quet_chuoi(tep: Dict[str, bytes], cam: Sequence[str]) -> List[str]:
    """[dòng chặn] — tệp văn bản nào chứa chuỗi riêng của máy (chỉ in tệp + độ dài chuỗi, không in chuỗi)."""
    ra = []
    for rel, nd in sorted(tep.items()):
        if not rel.lower().endswith(DUOI_VAN_BAN) and "." in rel.rsplit("/", 1)[-1]:
            continue
        chu = nd.decode("utf-8", "replace")
        for v in cam:
            if v in chu:
                ra.append("[chuỗi riêng máy] {0} — chuỗi dài {1}".format(rel, len(v)))
    return ra


def ghi_zip(dich: str, tep_ma: Dict[str, bytes], tep_goc: Dict[str, bytes], tai: List[Tuple[str, str]],
            luc: Tuple[int, ...], them_ma: Dict[str, bytes]) -> Tuple[int, int]:
    """Ghi zip tất định. Trả (số tệp, số byte)."""
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    tam = dich + ".dang-ghi"
    muc: List[Tuple[str, Optional[bytes], Optional[str]]] = []
    muc += [("MyTool/" + r, nd, None) for r, nd in {**tep_ma, **them_ma}.items()]
    muc += [("MyTool/" + r, None, p) for r, p in tai]
    muc += [(r, nd, None) for r, nd in tep_goc.items()]
    muc.sort(key=lambda x: x[0])
    with zipfile.ZipFile(tam, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for ten, nd, p in muc:
            zi = zipfile.ZipInfo(ten, date_time=luc)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            if nd is None:
                with open(p, "rb") as f:
                    nd = f.read()
            z.writestr(zi, nd, compresslevel=6)
    os.replace(tam, dich)
    return len(muc), os.path.getsize(dich)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Đóng gói bản sạch MyTool cho VPS mới.")
    ap.add_argument("--goc", default=GOC, help="kho git MyTool (mặc định: kho chứa script này)")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--tai-nguyen", default="", help="thư mục MyTool có models/ runtime/ (mặc định = --goc)")
    ap.add_argument("--ra", default="", help="thư mục ra (mặc định <cha của --goc>\\BAN-SACH)")
    ap.add_argument("--bo-quet", action="store_true", help="KHÔNG quét bí mật (chỉ để thử)")
    ap.add_argument("--giu-cu", action="store_true", help="không xoá các MyTool-sach-*.zip cũ trong thư mục ra")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    goc = os.path.abspath(a.goc)
    tai_nguyen = os.path.abspath(a.tai_nguyen or goc)
    ra = os.path.abspath(a.ra or os.path.join(os.path.dirname(goc), "BAN-SACH"))
    tep, luc, ver = doc_archive(goc, a.ref)
    print("mã: {0} tệp tại {1} (v{2}); bỏ {3}".format(len(tep), a.ref, ver, ", ".join(m.pattern for m in LOAI_TRU)))
    tep_goc = tai_lieu_goc(tep)
    them = {"cap-nhat.json": CAP_NHAT_TAT.encode("utf-8")}
    tai = tep_tai_nguyen(tai_nguyen)
    print("tài nguyên: {0} tệp từ {1}".format(len(tai), tai_nguyen))
    if not a.bo_quet:
        # `cap-nhat.json` của gói là KHUÔN do script viết (tắt tự cập nhật) — quét nội dung dưới tên khác, không phải
        # tệp cấu hình riêng máy (luật "đường cấm" của bộ quét chặn theo TÊN).
        tat_ca = {**tep, **{"_goc/" + k: v for k, v in tep_goc.items()},
                  **{"_khuon/" + k.replace(".json", ".mau.json"): v for k, v in them.items()}}
        if goc not in sys.path:
            sys.path.insert(0, goc)
        from core.dong_bo_git import goc_du_lieu  # noqa: PLC0415 — chạy từ worktree: dữ liệu máy ở cây chính
        goc_dl = goc_du_lieu(tai_nguyen)
        cam = chuoi_may(goc_dl)
        print("chuỗi riêng máy để soi: {0} (từ {1})".format(len(cam), goc_dl))
        chan = quet(goc, tat_ca, goc_dl) + quet_chuoi(tat_ca, cam)
        if chan:
            print("DỪNG — quét thấy {0} chỗ không được lên gói:".format(len(chan)))
            for d in chan[:60]:
                print("  " + d)
            return 2
        print("quét bí mật / dữ liệu máy: sạch")
    dich = os.path.join(ra, "MyTool-sach-v{0}.zip".format(ver))
    if not a.giu_cu and os.path.isdir(ra):
        for t in os.listdir(ra):
            if t.startswith("MyTool-sach-") and t.endswith(".zip") and os.path.join(ra, t) != dich:
                os.remove(os.path.join(ra, t))
    n, kich = ghi_zip(dich, tep, tep_goc, tai, luc, them)
    print("{0}  {1:.0f} MB  {2} tệp".format(dich, kich / 1e6, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
