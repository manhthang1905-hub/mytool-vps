"""GIỌNG MỚI CHO KÊNH HỒI SINH (22/10/2026, chủ duyệt) — mỗi kênh hồi sinh một giọng ElevenLabs MỚI, chưa kênh nào dùng.

Chủ đưa voice_id theo một trong hai cách:
  * nhắn cho người điều phối → người ấy ghi vào tệp dưới;
  * tự ghi tệp `<cha của MyTool>\\kho\\giong-moi.txt`: MỖI DÒNG MỘT voice_id, ghi chú sau dấu `#` (tuỳ ý), dòng trống
    / dòng bắt đầu bằng `#` bỏ qua.
Máy lấy LẦN LƯỢT từ trên xuống, ghi sổ `kho\\_giong-da-dung.json` ({voice_id: {kenh, luc, ghi_chu, ky_tu_moi_phut}})
TRƯỚC khi dùng — không giao một giọng cho hai kênh. Giọng mà BẤT KỲ kênh nào trong CHANNEL/ đang ghi (kể cả kênh trả
kho) bị bỏ qua: không bao giờ dùng lại giọng kênh khác. Hết giọng → `cap` trả None, nơi gọi (core/thay_kenh) đứng chờ +
MỘT việc người "cần giọng ElevenLabs mới".

ĐO `ky_tu_moi_phut` (cách chọn giọng 15/10/2026, `workspace/giong-doc-so-sanh/15-10/`): đọc CÙNG một đoạn mẫu bằng giọng
mới và giọng tham chiếu (giọng kênh cũ, đã có `ky_tu_moi_phut` đo trên video thật), đo thời lượng bằng FFmpeg:
    ky_tu_moi_phut(mới) = round(ky_tu_moi_phut(tham chiếu) × ký_tự/phút(mới) ÷ ký_tự/phút(tham chiếu))
(15/10: 5AeT… 341,7 vs b34… 337,1 → 270 × 1,0137 = 274 — khớp số đã ghi). Chỉ TỈ LỆ được dùng vì đoạn mẫu đọc nhanh
hơn cả video. Giọng giữ NGUYÊN mặc định ElevenLabs — không gửi tốc độ/cao độ (chủ 15/10). TTS đi ví ShopAPI
(`client.tts`), ~2 đoạn × ~1 phút.

    python -m core.giong_moi xem            # chỉ đọc: giọng trong tệp, giọng đã giao, giọng còn dùng được
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_DS = "giong-moi.txt"
TEP_SO = "_giong-da-dung.json"
#: voice_id ElevenLabs: chữ + số, ~20 ký tự.
MAU_VOICE = re.compile(r"^[A-Za-z0-9]{16,40}$")
#: Đoạn mẫu: tối đa ngần này ký tự (cổng TTS nhận ≤ 1.000 ký tự/lượt), tối thiểu ngần này ký tự không trắng.
DAI_MAU_TOI_DA = 900
DAI_MAU_TOI_THIEU = 150
#: Tỉ lệ ký tự/phút mới ÷ tham chiếu ngoài khoảng này = số đo hỏng (tệp lỗi/đọc sai) → không nhận.
TI_LE_HOP_LE = (0.6, 1.6)
TEP_MAU_NHOM = "doan-mau-giong.txt"


def thu_muc_kho(goc: str) -> str:
    from .tra_kho import thu_muc_kho as _tm  # noqa: PLC0415

    return _tm(goc)


def duong_ds(goc: str) -> str:
    return os.path.join(thu_muc_kho(goc), TEP_DS)


def _doc_json(duong: str) -> Dict[str, Any]:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def doc_so(goc: str) -> Dict[str, Any]:
    return _doc_json(os.path.join(thu_muc_kho(goc), TEP_SO))


def _ghi_so(goc: str, so: Dict[str, Any]) -> None:
    duong = os.path.join(thu_muc_kho(goc), TEP_SO)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(so, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def doc_ds(goc: str) -> List[Dict[str, str]]:
    """Giọng chủ đưa, đúng thứ tự tệp: [{voice_id, ghi_chu}]. Dòng sai dạng bỏ qua; trùng giữ lần đầu."""
    try:
        with io.open(duong_ds(goc), encoding="utf-8-sig") as tep:
            dong = tep.read().splitlines()
    except OSError:
        return []
    ra: List[Dict[str, str]] = []
    co = set()
    for d in dong:
        d = d.strip()
        if not d or d.startswith("#"):
            continue
        v, _, ghi = d.partition("#")
        v = (v.split() or [""])[0].strip().strip('"').strip("'")
        if MAU_VOICE.match(v) and v not in co:
            co.add(v)
            ra.append({"voice_id": v, "ghi_chu": ghi.strip()})
    return ra


def dau(goc: str) -> str:
    """Vân tay tệp giọng (mtime) — đổi thì xét lại việc đang chờ giọng."""
    try:
        return "{0:.0f}".format(os.path.getmtime(duong_ds(goc)))
    except OSError:
        return ""


def giong_kenh(goc: str, tru: str = "") -> Dict[str, str]:
    """{voice_id: mã kênh} của MỌI kênh trong CHANNEL/ (kể cả trả kho), trừ `tru`."""
    from .kenh import TEP_KENH, doc_yaml, duong_kenh, liet_ke_kenh  # noqa: PLC0415

    ra: Dict[str, str] = {}
    for m in liet_ke_kenh(goc, ca_tra_kho=True):
        if m == tru:
            continue
        try:
            v = str((doc_yaml(os.path.join(duong_kenh(goc, m), TEP_KENH)) or {}).get("voice_id") or "").strip()
        except Exception:  # noqa: BLE001
            v = ""
        if v:
            ra.setdefault(v, m)
    return ra


def giong_cua(goc: str, ma: str) -> Optional[Dict[str, Any]]:
    """Giọng đã giao cho kênh `ma` (sổ), None nếu chưa."""
    for v, x in doc_so(goc).items():
        if isinstance(x, dict) and x.get("kenh") == ma:
            return dict(x, voice_id=v)
    return None


def xet(goc: str) -> List[Dict[str, Any]]:
    """CHỈ ĐỌC. Mỗi giọng trong tệp: {voice_id, ghi_chu, tt: con | da_giao | dang_dung, kenh}."""
    so = doc_so(goc)
    dung = giong_kenh(goc)
    ra = []
    for x in doc_ds(goc):
        v = x["voice_id"]
        if isinstance(so.get(v), dict):
            ra.append(dict(x, tt="da_giao", kenh=str(so[v].get("kenh") or "")))
        elif v in dung:
            ra.append(dict(x, tt="dang_dung", kenh=dung[v]))
        else:
            ra.append(dict(x, tt="con", kenh=""))
    return ra


def con_lai(goc: str) -> List[str]:
    return [x["voice_id"] for x in xet(goc) if x["tt"] == "con"]


def cap(goc: str, ma: str, bay_gio: Optional[_dt.datetime] = None) -> Optional[Dict[str, Any]]:
    """Giọng mới cho kênh `ma`: đã giao → trả lại (chạy lại an toàn); chưa → giọng ĐẦU TIÊN còn dùng được, ghi sổ TRƯỚC
    khi trả. Hết → None."""
    cu = giong_cua(goc, ma)
    if cu:
        return cu
    dung = giong_kenh(goc, tru=ma)
    so = doc_so(goc)
    for x in doc_ds(goc):
        v = x["voice_id"]
        if v in so or v in dung:
            continue
        so[v] = {"kenh": ma, "luc": (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d %H:%M"), "ghi_chu": x["ghi_chu"]}
        _ghi_so(goc, so)
        return dict(so[v], voice_id=v)
    return None


def ghi_do(goc: str, voice_id: str, ky_tu_moi_phut: int, chi_tiet: Dict[str, Any]) -> None:
    so = doc_so(goc)
    x = so.get(voice_id) if isinstance(so.get(voice_id), dict) else {}
    x.update({"ky_tu_moi_phut": int(ky_tu_moi_phut), "do": chi_tiet})
    so[voice_id] = x
    _ghi_so(goc, so)


# ═══════════════════════════ đo ký tự/phút ═══════════════════════════════════
def so_ky_tu(chu: str) -> int:
    return len(re.sub(r"\s", "", chu or ""))


def cat_mau(chu: str, toi_da: int = DAI_MAU_TOI_DA) -> str:
    """Cắt đoạn mẫu ≤ `toi_da` ký tự ở cuối câu gần nhất (。！？.!? hoặc xuống dòng)."""
    s = re.sub(r"[ \t]+", " ", str(chu or "")).strip()
    if len(s) <= toi_da:
        return s
    dau_cau = [m.end() for m in re.finditer(r"[。！？.!?\n]", s[:toi_da])]
    return s[:dau_cau[-1]].strip() if dau_cau and dau_cau[-1] >= toi_da // 2 else s[:toi_da].strip()


def doan_mau(goc: str, cu: str) -> str:
    """Đoạn mẫu đọc thử (tiếng của kênh): `CHANNEL/_NHOM/<nhóm>/doan-mau-giong.txt` > mô tả kênh cũ (hồ sơ thiết lập).
    Thiếu → ném."""
    from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    y = doc_yaml(os.path.join(duong_kenh(goc, cu), TEP_KENH)) or {}
    nhom = str(y.get("nhom") or "")
    nguon = []
    if nhom:
        try:
            with io.open(os.path.join(goc, "CHANNEL", "_NHOM", nhom, TEP_MAU_NHOM), encoding="utf-8-sig") as tep:
                nguon.append(tep.read())
        except OSError:
            pass
    nguon.append(str(_doc_json(os.path.join(duong_kenh(goc, cu), "thiet-lap", "ho-so.json")).get("mo_ta") or ""))
    for chu in nguon:
        m = cat_mau(chu)
        if so_ky_tu(m) >= DAI_MAU_TOI_THIEU:
            return m
    raise RuntimeError("không có đoạn mẫu đọc thử ≥ {0} ký tự (thêm CHANNEL/_NHOM/{1}/{2})".format(
        DAI_MAU_TOI_THIEU, nhom or "<nhóm>", TEP_MAU_NHOM))


def giong_tham_chieu(goc: str, cu: str) -> Dict[str, Any]:
    """Giọng tham chiếu có `ky_tu_moi_phut` đã đo: giọng kênh cũ; không có → kênh khác cùng nhóm. {voice_id, ky, kenh}."""
    from .kenh import TEP_KENH, doc_yaml, duong_kenh, liet_ke_kenh  # noqa: PLC0415

    def lay(m: str) -> Optional[Dict[str, Any]]:
        y = doc_yaml(os.path.join(duong_kenh(goc, m), TEP_KENH)) or {}
        v = str(y.get("voice_id") or "").strip()
        try:
            k = int(float(y.get("ky_tu_moi_phut") or 0))
        except (TypeError, ValueError):
            k = 0
        return {"voice_id": v, "ky": k, "kenh": m, "nhom": str(y.get("nhom") or ""),
                "ngon_ngu": str(y.get("ngon_ngu") or "")} if v and k > 0 else None

    x = lay(cu)
    if x:
        return x
    nhom = str((doc_yaml(os.path.join(duong_kenh(goc, cu), TEP_KENH)) or {}).get("nhom") or "")
    for m in liet_ke_kenh(goc):
        y = lay(m)
        if y and y["nhom"] == nhom:
            return y
    raise RuntimeError("không có giọng tham chiếu (kênh {0} / nhóm {1} chưa có voice_id + ky_tu_moi_phut)".format(cu, nhom or "?"))


def _doc_giong_that(goc: str) -> Callable[[str, str, str, str], float]:
    """`doc(voice_id, chu, ngon_ngu, dich) -> giây`: TTS qua ví ShopAPI (giọng mặc định, không tốc độ/cao độ) + FFmpeg."""
    from .api import build_client  # noqa: PLC0415
    from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415
    from .dung_video import doc_thoi_luong, tim_ffmpeg  # noqa: PLC0415
    from .khoi_tao_ngach import tao_va_tai_job  # noqa: PLC0415

    cfg = load_config(os.path.join(goc, CONFIG_FILENAME))
    if cfg.problem:
        raise RuntimeError("không đọc được cấu hình ShopAPI: " + str(cfg.problem)[:100])
    client = build_client(cfg)
    ff = tim_ffmpeg(goc)
    if not ff:
        raise RuntimeError("không tìm thấy FFmpeg để đo thời lượng giọng mẫu")

    def doc(voice_id: str, chu: str, ngon_ngu: str, dich: str) -> float:
        khoa = "do-giong-" + hashlib.sha1("{0}|{1}".format(voice_id, chu).encode("utf-8")).hexdigest()[:24]
        if not os.path.isfile(dich):
            tao_va_tai_job(client, lambda k: client.tts.create_and_wait(
                text=chu, voice_id=voice_id, format="mp3", language_code=ngon_ngu or None, idempotency_key=k,
                timeout=900), khoa, dich, "giọng mẫu")
        return float(doc_thoi_luong(ff, dich) or 0.0)
    return doc


def do_ky_tu_moi_phut(goc: str, voice_id: str, cu: str, *, ma: str = "",
                      doc: Optional[Callable[[str, str, str, str], float]] = None,
                      log: Callable[[str], None] = print) -> Dict[str, Any]:
    """Đo `ky_tu_moi_phut` cho giọng mới theo giọng tham chiếu của dòng kênh `cu` (xem đầu tệp). Lỗi → ném."""
    ref = giong_tham_chieu(goc, cu)
    mau = doan_mau(goc, cu)
    n = so_ky_tu(mau)
    tm = os.path.join(goc, "workspace", "mo-kenh", "do-giong", ma or cu)
    os.makedirs(tm, exist_ok=True)
    with io.open(os.path.join(tm, "doan-mau.txt"), "w", encoding="utf-8", newline="\n") as tep:
        tep.write(mau)
    doc = doc or _doc_giong_that(goc)
    t_moi = doc(voice_id, mau, ref["ngon_ngu"], os.path.join(tm, "giong-moi.mp3"))
    t_ref = doc(ref["voice_id"], mau, ref["ngon_ngu"], os.path.join(tm, "giong-tham-chieu.mp3"))
    if t_moi <= 0 or t_ref <= 0:
        raise RuntimeError("không đo được thời lượng giọng mẫu (mới {0:.1f}s, tham chiếu {1:.1f}s)".format(t_moi, t_ref))
    cpm_moi, cpm_ref = n / t_moi * 60.0, n / t_ref * 60.0
    ti_le = cpm_moi / cpm_ref
    if not TI_LE_HOP_LE[0] <= ti_le <= TI_LE_HOP_LE[1]:
        raise RuntimeError("số đo giọng lạ: tỉ lệ ký tự/phút {0:.2f} ngoài {1}–{2} — không nhận".format(
            ti_le, TI_LE_HOP_LE[0], TI_LE_HOP_LE[1]))
    ky = int(round(ref["ky"] * ti_le))
    kq = {"ky_tu_moi_phut": ky, "so_ky_tu": n, "giay_moi": round(t_moi, 2), "giay_tham_chieu": round(t_ref, 2),
          "cpm_moi": round(cpm_moi, 1), "cpm_tham_chieu": round(cpm_ref, 1), "ky_tham_chieu": ref["ky"],
          "kenh_tham_chieu": ref["kenh"], "luc": time.strftime("%Y-%m-%d %H:%M")}
    with io.open(os.path.join(tm, "so-do.json"), "w", encoding="utf-8", newline="\n") as tep:
        json.dump(kq, tep, ensure_ascii=False, indent=1)
    log("{0}: đo giọng mới — {1} ký tự, {2:.1f} ký tự/phút vs tham chiếu {3:.1f} ({4}) → ky_tu_moi_phut {5}".format(
        ma or cu, n, cpm_moi, cpm_ref, ref["kenh"], ky))
    return kq


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    a = list(sys.argv[1:] if argv is None else argv) or ["xem"]
    goc = GOC
    if "--goc" in a:
        i = a.index("--goc")
        goc, a = os.path.abspath(a[i + 1]), a[:i] + a[i + 2:]
    ds = xet(goc)
    print("Tệp giọng mới: {0} ({1})".format(duong_ds(goc), "có" if os.path.isfile(duong_ds(goc)) else "CHƯA CÓ"))
    for x in ds:
        print("  {0}…  {1:<9} {2} {3}".format(x["voice_id"][:4], x["tt"], x["kenh"], x["ghi_chu"]))
    print("=> {0} giọng còn dùng được".format(sum(1 for x in ds if x["tt"] == "con")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
