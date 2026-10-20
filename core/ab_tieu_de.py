"""A/B TIÊU ĐỀ + BÌA (16/10/2026 — chủ duyệt «Cho dùng»): mỗi video MỚI, và mỗi video trượt mà giám đốc kênh muốn cứu,
máy đặt «Thử nghiệm A/B» của Studio ở chế độ «Tiêu đề và hình thu nhỏ»: 2–3 tiêu đề (A = tiêu đề đang chạy, B/C do giám
đốc viết — `giam_doc.cuu_ctr.viet_tieu_de_ab`) + 2–3 bìa (A = bìa đang chạy, B/C = bìa ứng viên CÓ DẤU cổng chữ). YouTube
tự chọn bản thắng theo thời gian xem. Video đã có A/B thì KHÔNG đổi tiêu đề trực tiếp nữa (`chan_doi_truc_tiep`); đổi
trực tiếp (`cuu_ctr` đo trước/sau + tự đổi lại) chỉ còn là đường lùi cho kênh / video không có A/B.

Phần THUẦN + sổ (không mạng, không Chrome). Bộ chạy DOM: `vm/studio_may_dom.py --test-compare` (skill D13).

    bat(cai)                                  công tắc kênh `ab_tieu_de` (kenh.yaml) — mặc định = `giam_doc_studio`
    kiem_tieu_de(moi, a, khac, doi_thu)       luật cứng một tiêu đề thêm: độ dài ≤ 100, giữ nhãn đầu 【…】, khác hẳn
                                              A và bản khác, không chép tiêu đề đối thủ / nguồn (`do_trung` > 0,5)
    soat_tieu_de(goi, ds, …)                  luật cứng + `cong_chu.soat_chat` (chính tả so kịch bản + đúng chủ đề)
    chon_che_do(n_tieu_de, n_bia)             «Tiêu đề và hình thu nhỏ» | «Chỉ tiêu đề» | «Chỉ hình thu nhỏ»
    lap(goc, ma, …)                           ghi sổ `CHANNEL/<k>/giam-doc/ab-tieu-de.json` + việc máy `studio_ab_tieu_de`
    xu_ly_moi(goc, ma, bs, goi_chat)          cò (a): video tool vừa đăng (≤ 72 giờ) chưa có A/B → lập
    chan_doi_truc_tiep / kenh_khong_ab        rào cho `cuu_ctr` (cò b) và đường lùi đổi trực tiếp
    cap_nhat(goc, ma, vid, …)                 bộ chạy DOM ghi kết quả (đọc lại STARTED + danh sách tiêu đề)
    can_doc_ket_qua / ghi_doc_ket_qua         (20/10) thử nghiệm đang chạy ≥ 2 ngày → D13 đọc lại bản thắng → sổ «xong»,
                                              não "tieu-de", trục tự học `kieu_tieu_de`, khối lời nhắc `khoi_thang`
    dong_qua_han                              (20/10) quá 14 ngày chưa có kết quả → đóng «không kết luận»

Trần: mỗi kênh ≤ `TOI_DA_LAP_NGAY_KENH` lượt lập / ngày (cả hai cò); mỗi video MỘT thử nghiệm (đang chạy → không đụng);
mỗi lượt bộ tự kích hoạt chạy MỘT kênh (D13).
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

TEP = "ab-tieu-de.json"
#: Giới hạn tiêu đề YouTube (ký tự).
TIEU_DE_TOI_DA = 100
TIEU_DE_TOI_THIEU = 6
#: Tiêu đề thêm chép tiêu đề đối thủ / nguồn: tỉ lệ cửa sổ `N_SO` ký tự (`do_doc_dao.do_trung`) trên ngưỡng → bỏ.
NGUONG_CHEP = 0.5
#: Tiêu đề thêm giống A / giống bản thêm khác trên ngưỡng này = "chỉ đổi vài chữ" → bỏ (A/B phải đổi GÓC bấm).
NGUONG_GIONG = 0.6
N_SO = 4
SO_TIEU_DE_THEM = 2
TOI_DA_BIEN_THE = 3
TOI_DA_LAP_NGAY_KENH = 2
#: Cò (a): video do tool đăng chưa quá ngần này giờ mà chưa có A/B.
TUOI_MOI_GIO = 72.0
#: Kênh vừa bị Studio báo không có A/B (tính năng nâng cao) trong ngần này ngày → không lập thêm, đổi trực tiếp lùi về.
NGAY_KHONG_AB = 7
#: Ký tự YouTube cấm trong tiêu đề.
_RE_CAM = re.compile(r"[<>]")
_RE_NHAN = re.compile(r"^\s*(【[^】]{1,12}】)")

CHE_DO_TIEU_DE_BIA, CHE_DO_TIEU_DE, CHE_DO_BIA = "tieu_de_bia", "tieu_de", "bia"
TEN_CHE_DO = {CHE_DO_TIEU_DE_BIA: "Tiêu đề và hình thu nhỏ", CHE_DO_TIEU_DE: "Chỉ tiêu đề", CHE_DO_BIA: "Chỉ hình thu nhỏ"}
#: Trạng thái mục sổ. Video có mục ở `TT_CHAN` → không đổi tiêu đề trực tiếp, không lập A/B mới.
TT_CHO, TT_DANG, TT_DA_DAT, TT_DA_CO, TT_LOI, TT_BO, TT_KHONG_QUYEN = (
    "cho", "dang", "da_dat", "da_co", "loi", "bo", "khong_quyen")
#: 20/10/2026: thử nghiệm đã KẾT THÚC và máy đã đọc kết quả (`ket_qua`: thắng / không kết luận). Vẫn chặn đổi trực
#: tiếp — YouTube đã đặt bản thắng, không đổi tiêu đề của video vừa có kết quả A/B.
TT_XONG = "xong"
TT_CHAN = (TT_CHO, TT_DANG, TT_DA_DAT, TT_DA_CO, TT_LOI, TT_XONG)


def _luc(t: Optional[_dt.datetime] = None) -> str:
    return (t or _dt.datetime.now()).replace(microsecond=0).isoformat()


def _gon(s: Any) -> str:
    return " ".join(str(s or "").split())


# ── công tắc ────────────────────────────────────────────────────────────────

def _co(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    s = str(x if x is not None else "").strip().lower()
    return True if s in ("true", "1", "yes", "co", "bat", "on") else False if s in (
        "false", "0", "no", "khong", "tat", "off") else None


def bat(cai: Any) -> bool:
    """`ab_tieu_de` trong kenh.yaml thắng; không khai → theo `giam_doc_studio` (kênh mà giám đốc KHÔNG được sửa Studio —
    như TL4-T7 — mặc định TẮT). Giám đốc tắt (`giam_doc: tat`) → tắt."""
    cai = getattr(cai, "cai", cai) or {}
    if str(cai.get("giam_doc") or "").strip().lower() == "tat":
        return False
    rieng = _co(cai.get("ab_tieu_de"))
    if rieng is not None:
        return rieng
    return bool(_co(cai.get("giam_doc_studio")))


# ── luật một tiêu đề ────────────────────────────────────────────────────────

def nhan_dau(tieu_de: Any) -> str:
    m = _RE_NHAN.match(str(tieu_de or ""))
    return m.group(1) if m else ""


def _bo_nhan(t: Any) -> str:
    return _RE_NHAN.sub("", str(t or ""), count=1).strip()


def chuan_nhan(moi: str, tieu_de_a: str) -> str:
    """Giữ kiểu nhãn đầu của kênh: A có 【…】 mà bản mới thiếu → gắn (nếu vừa trần 100)."""
    moi = _gon(moi).strip("“”\"'「」")
    n = nhan_dau(tieu_de_a)
    if n and not moi.startswith(n):
        cu = nhan_dau(moi)
        than = _bo_nhan(moi) if cu else moi
        if len(n + than) <= TIEU_DE_TOI_DA:
            moi = n + than
    return moi


def do_giong(a: str, b: str, n: int = N_SO) -> float:
    """Tỉ lệ cửa sổ `n` ký tự của `a` (bỏ nhãn đầu) có y nguyên trong `b` (bỏ nhãn đầu)."""
    from .do_doc_dao import do_trung  # noqa: PLC0415
    return float(do_trung(_bo_nhan(a), _bo_nhan(b), n=n)["ti_le"])


def kiem_tieu_de(moi: str, tieu_de_a: str, khac: Sequence[str] = (), doi_thu: Sequence[str] = ()) -> str:
    """'' = tiêu đề thêm qua luật cứng; khác → lý do. Luật: 6–100 ký tự, không ký tự cấm, giữ nhãn đầu của A, KHÁC HẲN
    A và các bản thêm khác (`do_giong` ≤ `NGUONG_GIONG`), KHÔNG chép tiêu đề đối thủ / video nguồn (`do_giong` ≤
    `NGUONG_CHEP`, không trùng nguyên văn)."""
    from .cong_chu import chuan  # noqa: PLC0415
    moi = _gon(moi)
    if not TIEU_DE_TOI_THIEU <= len(moi) <= TIEU_DE_TOI_DA:
        return "dài {0} ký tự (YouTube: {1}–{2})".format(len(moi), TIEU_DE_TOI_THIEU, TIEU_DE_TOI_DA)
    if _RE_CAM.search(moi):
        return "có ký tự YouTube cấm (< >)"
    n = nhan_dau(tieu_de_a)
    if n and not moi.startswith(n):
        return "mất nhãn đầu {0} của kênh".format(n)
    for x in [tieu_de_a] + [k for k in khac if k]:
        if chuan(_bo_nhan(x)) == chuan(_bo_nhan(moi)):
            return "trùng tiêu đề 「{0}」".format(_gon(x)[:40])
        g = max(do_giong(moi, x), do_giong(x, moi))
        if g > NGUONG_GIONG:
            return "gần như giống 「{0}」 ({1:.0%}) — A/B phải đổi góc bấm, không chỉ vài chữ".format(_gon(x)[:40], g)
    for x in [d for d in doi_thu if _gon(d)]:
        if chuan(_bo_nhan(x)) == chuan(_bo_nhan(moi)):
            return "chép nguyên văn tiêu đề đối thủ / nguồn 「{0}」".format(_gon(x)[:40])
        g = do_giong(moi, x)
        if g > NGUONG_CHEP:
            return "chép tiêu đề đối thủ / nguồn 「{0}」 ({1:.0%} chuỗi {2} ký tự trùng)".format(_gon(x)[:40], g, N_SO)
    return ""


def soat_tieu_de(goi: Optional[Callable[..., str]], ds: Sequence[str], *, tieu_de_a: str, ngu_canh: str = "",
                 ngon_ngu: str = "ja", doi_thu: Sequence[str] = (), khoa: str = "ab-tieu-de",
                 thang: Sequence[str] = (), toi_da: int = SO_TIEU_DE_THEM) -> Dict[str, Any]:
    """Mỗi tiêu đề thêm: `chuan_nhan` → `kiem_tieu_de` → `cong_chu.soat_chat` (chính tả so tiêu đề A + kịch bản, kanji
    ngoài nguồn phải được xác nhận, đúng chủ đề video; bản sửa của biên tập viên qua luật cứng lại). Trả `{dat: [...],
    bo: [{tieu_de, ly_do}], chua: bool}` — `chua` = có bản AI chưa soát được (nơi gọi để lượt sau, không ghi sổ)."""
    from . import cong_chu  # noqa: PLC0415
    dat: List[str] = []
    bo: List[Dict[str, str]] = []
    chua = False
    for i, t in enumerate(ds or []):
        if len(dat) >= toi_da:
            break
        t = chuan_nhan(t, tieu_de_a)
        ly = kiem_tieu_de(t, tieu_de_a, dat, doi_thu)
        if ly:
            bo.append({"tieu_de": t, "ly_do": ly})
            continue
        r = cong_chu.soat_chat(goi, t, tieu_de=tieu_de_a, ngu_canh=ngu_canh, ngon_ngu=ngon_ngu, thang=thang,
                               khoa="{0}:{1}".format(khoa, i), loai="tieu_de")
        if r.get("ok") is None:
            chua = True
            bo.append({"tieu_de": t, "ly_do": "chưa soát được: " + str(r.get("ly_do") or "")[:120]})
            continue
        if r.get("ok") is not True:
            bo.append({"tieu_de": t, "ly_do": "trượt soát chữ: " + str(r.get("ly_do") or "")[:160]})
            continue
        moi = chuan_nhan(str(r.get("chu") or t), tieu_de_a)
        ly = kiem_tieu_de(moi, tieu_de_a, dat, doi_thu) if moi != t else ""
        if ly:
            bo.append({"tieu_de": moi, "ly_do": "bản sửa chính tả: " + ly})
            continue
        dat.append(moi)
    return {"dat": dat, "bo": bo, "chua": chua}


def chon_che_do(n_tieu_de_them: int, n_bia_them: int) -> Tuple[str, int]:
    """(chế độ, số biến thể kể cả A). Có cả tiêu đề thêm lẫn bìa có dấu → «Tiêu đề và hình thu nhỏ» (mỗi biến thể một
    cặp tiêu đề + bìa); chỉ tiêu đề → «Chỉ tiêu đề»; chỉ bìa → «Chỉ hình thu nhỏ»; không có gì → ("", 0)."""
    nt = max(0, min(int(n_tieu_de_them or 0), TOI_DA_BIEN_THE - 1))
    nb = max(0, min(int(n_bia_them or 0), TOI_DA_BIEN_THE - 1))
    if nt and nb:
        return CHE_DO_TIEU_DE_BIA, 1 + min(nt, nb)
    if nt:
        return CHE_DO_TIEU_DE, 1 + nt
    if nb:
        return CHE_DO_BIA, 1 + nb
    return "", 0


# ── ngữ cảnh video (đĩa) ────────────────────────────────────────────────────

def _doc(duong: str) -> str:
    try:
        with io.open(duong, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _luot(kenh: str, ma_goi: str) -> str:
    return ma_goi[len(kenh) + 1:] if ma_goi.startswith(kenh + "-") else ma_goi.rsplit("-", 1)[-1]


def ngu_canh(goc: str, kenh: str, ma_goi: str) -> Dict[str, str]:
    """{tieu_de, ngu_canh (kịch bản / phụ đề ≤ 2.500 ký tự)} của gói (`cong_chu._ngu_canh`)."""
    try:
        from .cong_chu import _ngu_canh as nc  # noqa: PLC0415
        return nc(goc, kenh, ma_goi) if ma_goi else {"tieu_de": "", "ngu_canh": ""}
    except Exception:  # noqa: BLE001
        return {"tieu_de": "", "ngu_canh": ""}


def tieu_de_doi_thu(goc: str, kenh: str, ma_goi: str) -> List[str]:
    """Tiêu đề video ĐỐI THỦ / NGUỒN của lượt (`0-doi-thu.txt` dòng TITLE) — tiêu đề thêm không được chép."""
    if not ma_goi:
        return []
    chu = _doc(os.path.join(goc, "PROJECTS", "AUTO", kenh, _luot(kenh, ma_goi), "0-doi-thu.txt"))
    return [d.split(":", 1)[1].strip() for d in chu.splitlines() if d.strip().upper().startswith("TITLE:")
            and d.split(":", 1)[1].strip()]


# ── sổ ──────────────────────────────────────────────────────────────────────

def duong_so(goc: str, ma: str) -> str:
    from .giam_doc.du_lieu import thu_muc_giam_doc  # noqa: PLC0415
    return os.path.join(thu_muc_giam_doc(goc, ma), TEP)


def doc_so(goc: str, ma: str) -> List[Dict[str, Any]]:
    try:
        with io.open(duong_so(goc, ma), encoding="utf-8") as f:
            du = json.load(f)
    except (OSError, ValueError):
        return []
    return [m for m in (du.get("muc") if isinstance(du, dict) else None) or [] if isinstance(m, dict)]


def ghi_so(goc: str, ma: str, ds: List[Dict[str, Any]]) -> None:
    p = duong_so(goc, ma)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p + ".tam", "w", encoding="utf-8") as f:
        json.dump({"kenh": ma, "muc": ds[-300:]}, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tam", p)


def muc_cua(goc: str, ma: str, vid: str, ds: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Mục MỚI NHẤT của video trong sổ (None = chưa từng lập A/B)."""
    ds = doc_so(goc, ma) if ds is None else ds
    return next((m for m in reversed(ds) if m.get("video_id") == vid), None)


def chan_doi_truc_tiep(goc: str, ma: str, vid: str, ds: Optional[List[Dict[str, Any]]] = None) -> str:
    """Lý do KHÔNG đổi tiêu đề trực tiếp: video đang / đã thử nghiệm A/B (YouTube chọn) hoặc A/B đang xếp hàng. ""."""
    m = muc_cua(goc, ma, vid, ds)
    if m and m.get("trang_thai") in TT_CHAN:
        return "video {0} A/B tiêu đề ({1}) — YouTube chọn bản thắng, không đổi trực tiếp".format(
            "đang / đã có thử nghiệm" if m["trang_thai"] in (TT_DA_DAT, TT_DA_CO, TT_DANG) else "đang chờ đặt",
            m["trang_thai"])
    return ""


def kenh_khong_ab(goc: str, ma: str, bay_gio: Optional[_dt.datetime] = None,
                  ds: Optional[List[Dict[str, Any]]] = None) -> str:
    """Lý do kênh KHÔNG dùng được A/B lúc này: Studio vừa báo không có quyền (≤ `NGAY_KHONG_AB` ngày), hoặc sổ chặn
    ghim báo chưa có tính năng nâng cao. "" = dùng được (đổi tiêu đề trực tiếp chỉ là đường lùi khi khác "")."""
    bay_gio = bay_gio or _dt.datetime.now()
    ds = doc_so(goc, ma) if ds is None else ds
    moc = (bay_gio - _dt.timedelta(days=NGAY_KHONG_AB)).isoformat()
    m = next((x for x in reversed(ds) if x.get("trang_thai") == TT_KHONG_QUYEN
              and str(x.get("cap_nhat") or x.get("luc") or "")[:19] >= moc[:19]), None)
    if m:
        return "Studio báo kênh chưa dùng được Thử nghiệm A/B ({0})".format(str(m.get("ly_do") or "")[:100])
    try:
        from . import studio_may  # noqa: PLC0415
        with io.open(os.path.join(studio_may.thu_muc_vm(goc), "logs", "cmt-dom.json"), encoding="utf-8") as f:
            so_cmt = json.load(f)
        return studio_may.thieu_tinh_nang(so_cmt, ma, bay_gio)
    except (OSError, ValueError, ImportError):
        return ""


def so_lap_hom_nay(ds: List[Dict[str, Any]], bay_gio: _dt.datetime) -> int:
    hom = bay_gio.date().isoformat()
    return sum(1 for m in ds if str(m.get("luc") or "")[:10] == hom)


def lap(goc: str, ma: str, *, video_id: str, ma_goi: str, tieu_de_a: str, tieu_de_them: Sequence[str], nguon: str,
        ly_do: str = "", bo: Sequence[Dict[str, Any]] = (), bay_gio: Optional[_dt.datetime] = None,
        ds: Optional[List[Dict[str, Any]]] = None, do_tin: Any = None) -> Dict[str, Any]:
    """Ghi MỘT mục sổ + việc máy `studio_ab_tieu_de` (bộ chạy D13). `nguon`: "moi" (cò a) | "truot" (cò b). Tiêu đề
    thêm phải ĐÃ qua `soat_tieu_de` (bộ chạy chỉ soát lại luật cứng). Trả mục."""
    from .giam_doc import _tu_dong as td  # noqa: PLC0415
    bay_gio = bay_gio or _dt.datetime.now()
    ds = doc_so(goc, ma) if ds is None else ds
    m = {"id": "ab-{0}-{1}".format(video_id, bay_gio.strftime("%Y%m%d%H%M")), "video_id": video_id, "ma_goi": ma_goi,
         "tieu_de_a": _gon(tieu_de_a), "tieu_de_them": [_gon(t) for t in tieu_de_them][:TOI_DA_BIEN_THE - 1],
         "soat": {"ok": True, "phien": _phien_soat(), "luc": _luc(bay_gio)}, "nguon": nguon,
         "ly_do": _gon(ly_do)[:300], "do_tin": do_tin, "bo": list(bo)[:6], "trang_thai": TT_CHO,
         "luc": _luc(bay_gio), "cap_nhat": _luc(bay_gio), "ket": {}}
    td.ghi_viec_may_kieu(goc, td.LOAI_AB_TIEU_DE, ma, video_ids=[video_id], nguon="giam-doc:ab-" + nguon,
                         chu="A/B tiêu đề + bìa video {0}".format(video_id), bay_gio=bay_gio)
    m["viec"] = td._id_viec_may(td.LOAI_AB_TIEU_DE, ma, [video_id])  # noqa: SLF001
    ds.append(m)
    ghi_so(goc, ma, ds)
    _ghi_nao(goc, ma, m, "lap", "A/B {0}: {1} tiêu đề thêm — {2}".format(nguon, len(m["tieu_de_them"]), m["ly_do"]))
    return m


def _phien_soat() -> int:
    try:
        from .cong_chu import PHIEN_SOAT  # noqa: PLC0415
        return int(PHIEN_SOAT)
    except Exception:  # noqa: BLE001
        return 0


def cap_nhat(goc: str, ma: str, vid: str, *, bay_gio: Optional[_dt.datetime] = None, **truong: Any) -> bool:
    """Bộ chạy DOM ghi kết quả cho mục MỚI NHẤT của video (`trang_thai`, `ket`, …). Không có mục → False."""
    ds = doc_so(goc, ma)
    m = muc_cua(goc, ma, vid, ds)
    if m is None:
        return False
    m.update(truong)
    m["cap_nhat"] = _luc(bay_gio)
    if truong.get("trang_thai") in (TT_DA_DAT, TT_DA_CO) and not m.get("dat_luc"):
        m["dat_luc"] = m["cap_nhat"]          # 20/10/2026: mốc thử nghiệm bắt đầu — đọc kết quả / đóng quá hạn tính từ đây
    ghi_so(goc, ma, ds)
    if truong.get("trang_thai") in (TT_DA_DAT, TT_KHONG_QUYEN, TT_BO):
        _ghi_nao(goc, ma, m, str(truong["trang_thai"]), str((truong.get("ket") or {}).get("ly_do") or "")[:200])
    return True


def tieu_de_cho_may(goc: str, ma: str, vid: str, tieu_de_a: str = "") -> Dict[str, Any]:
    """Cho bộ chạy DOM: mục sổ còn chờ đặt của video → {tieu_de: [đã qua luật cứng lại], muc} ({} = không có)."""
    m = muc_cua(goc, ma, vid)
    if not m or m.get("trang_thai") not in (TT_CHO, TT_LOI, TT_DANG) or not (m.get("soat") or {}).get("ok"):
        return {}
    a = _gon(tieu_de_a) or m.get("tieu_de_a") or ""
    dat: List[str] = []
    for t in m.get("tieu_de_them") or []:
        if not kiem_tieu_de(t, a, dat, tieu_de_doi_thu(goc, ma, str(m.get("ma_goi") or ""))):
            dat.append(_gon(t))
    return {"tieu_de": dat[:TOI_DA_BIEN_THE - 1], "muc": m}


def _ghi_nao(goc: str, ma: str, m: Dict[str, Any], quyet: str, ly: str) -> None:
    """Một sự kiện não bộ phận "tieu-de" (hỏng không chặn)."""
    try:
        from . import nao_bo_phan  # noqa: PLC0415
        nao_bo_phan.ghi(goc, "tieu-de", "chon", kenh=ma, ma_goi=str(m.get("ma_goi") or ""),
                        noi_dung="A/B tiêu đề {0}: {1} “{2}” + {3} — {4}".format(
                            m.get("video_id"), quyet, str(m.get("tieu_de_a") or "")[:50],
                            " / ".join("“{0}”".format(t[:40]) for t in m.get("tieu_de_them") or []), ly)[:600],
                        so={"quyet": quyet, "nguon": m.get("nguon"), "id": m.get("id")}, nguon="ab_tieu_de",
                        khoa="ab-tieu-de|{0}|{1}".format(m.get("id"), quyet))
    except Exception:  # noqa: BLE001
        pass


# ── cò (a): video mới ───────────────────────────────────────────────────────

def ung_vien_moi(bs: Any, ds: List[Dict[str, Any]], tuoi_gio: float = TUOI_MOI_GIO) -> List[Dict[str, Any]]:
    """Video do TOOL đăng, tuổi ≤ `tuoi_gio`, chưa từng có mục sổ — mới trước."""
    co = {m.get("video_id") for m in ds}
    ra = [v for v in getattr(bs, "video", []) or [] if v.get("tu_tool") and v.get("ma_goi") and v.get("id") not in co
          and v.get("tuoi_gio") is not None and 0 <= float(v["tuoi_gio"]) <= tuoi_gio]
    return sorted(ra, key=lambda v: float(v["tuoi_gio"]))


def xu_ly_moi(goc: str, ma: str, bs: Any, goi_chat: Optional[Callable[..., str]], *, viet: bool = True,
              ghi: Optional[Callable[[str], None]] = None,
              viet_tieu_de: Optional[Callable[..., Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Cò (a), gọi từ lượt giám đốc kênh: mỗi video mới chưa có A/B (≤ trần ngày) → giám đốc viết 2 tiêu đề thêm →
    `soat_tieu_de` → `lap` (không có tiêu đề nào qua soát vẫn lập: bộ chạy dùng «Chỉ hình thu nhỏ» nếu có bìa có dấu).
    AI chưa soát được → để lượt sau (không ghi). `viet=False` (thử): không ghi gì. Trả các mục vừa lập."""
    ghi = ghi or (lambda s: None)
    if not bat(getattr(bs, "cai", {})) or goi_chat is None:
        return []
    ds = doc_so(goc, ma)
    bay = getattr(bs, "bay_gio", None) or _dt.datetime.now()
    ly = kenh_khong_ab(goc, ma, bay, ds)
    if ly:
        ghi("  [A/B tiêu đề] {0}: {1} — không lập".format(ma, ly))
        return []
    if viet_tieu_de is None:
        from .giam_doc.cuu_ctr import viet_tieu_de_ab as viet_tieu_de  # noqa: PLC0415
    ra: List[Dict[str, Any]] = []
    for v in ung_vien_moi(bs, ds):
        if so_lap_hom_nay(ds, bay) >= TOI_DA_LAP_NGAY_KENH:
            ghi("  [A/B tiêu đề] {0}: đủ {1} lượt lập hôm nay — video còn lại để mai".format(ma, TOI_DA_LAP_NGAY_KENH))
            break
        nc = ngu_canh(goc, ma, v["ma_goi"])
        dt = tieu_de_doi_thu(goc, ma, v["ma_goi"])
        kq = viet_tieu_de(bs, v, goi_chat, n=SO_TIEU_DE_THEM, ngu_canh=nc.get("ngu_canh") or "", doi_thu=dt, luu=viet,
                          ghi=ghi)
        if kq.get("loi"):
            ghi("  [A/B tiêu đề] {0}: giám đốc chưa viết được tiêu đề ({1}) — lượt sau".format(v["id"], kq["loi"]))
            continue
        s = soat_tieu_de(goi_chat, kq.get("tieu_de") or [], tieu_de_a=v.get("tieu_de") or "",
                         ngu_canh=nc.get("ngu_canh") or "", ngon_ngu=str(getattr(bs, "cai", {}).get("ngon_ngu") or "ja"),
                         doi_thu=dt, khoa="ab-tieu-de:{0}".format(v["id"]))
        if s["chua"] and not s["dat"]:
            ghi("  [A/B tiêu đề] {0}: chưa soát được tiêu đề (AI lỗi) — lượt sau".format(v["id"]))
            continue
        ghi("  [A/B tiêu đề] {0}: {1} tiêu đề qua soát, bỏ {2}{3}".format(
            v["id"], len(s["dat"]), len(s["bo"]), " ({0})".format("; ".join(b["ly_do"][:60] for b in s["bo"][:2]))
            if s["bo"] else ""))
        if not viet:
            ra.append({"video_id": v["id"], "tieu_de_them": s["dat"], "bo": s["bo"], "trang_thai": "thu"})
            continue
        ra.append(lap(goc, ma, video_id=v["id"], ma_goi=v["ma_goi"], tieu_de_a=v.get("tieu_de") or "",
                      tieu_de_them=s["dat"], nguon="moi", ly_do=kq.get("ly_do") or "", bo=s["bo"], bay_gio=bay, ds=ds,
                      do_tin=kq.get("do_tin")))
    return ra


# ── kết quả thử nghiệm (20/10/2026): đọc lại → sổ → não "tieu-de" + trục tự học `kieu_tieu_de` ─────────────────
#
# Trước đây sổ chỉ biết "đã đặt / đang chạy": 11 thử nghiệm 17–20/10 nằm mãi "đang chạy", không ai đọc bản thắng về.
# Giờ: bộ chạy DOM D13 (`vm/studio_may_dom.py --test-compare`, CÙNG phiên trang sửa đã đọc `videoCreatorExperiment`)
# ghé lại video có thử nghiệm đang chạy (`can_doc_ket_qua`, ≤ 1 lần/ngày/video) → `ghi_doc_ket_qua` → kết thúc thì ghi
# bản thắng + số đo, một sự kiện não bộ phận "tieu-de" (giấc ngủ rút bài) và cặp thắng/thua cho trục `kieu_tieu_de`
# (`tu_hoc.bang_diem` cộng thẳng — lượt viết tiêu đề chọn theo đó) + khối "A/B đã có kết quả" trong lời nhắc tiêu đề
# (`khoi_thang`). Quá `NGAY_DONG_KHONG_KL` ngày vẫn chưa ra kết quả → đóng "không kết luận" (không học gì).

#: Thử nghiệm đặt xong ≥ ngần này ngày mới đọc kết quả (YouTube cần thời gian xem).
NGAY_DOC_KQ_TU = 2.0
#: Một video đọc lại tối đa mỗi ngần này giờ (kể cả lần đọc hỏng — không mở trang dày).
GIO_DOC_KQ_LAI = 24.0
#: Đặt quá ngần này ngày vẫn chưa kết thúc / chưa đọc được → đóng "không kết luận".
NGAY_DONG_KHONG_KL = 14.0
#: Mỗi phiên D13 đọc tối đa ngần này video.
TOI_DA_DOC_KQ_PHIEN = 4
KL_THANG, KL_KHONG = "thang", "khong_ket_luan"
_RE_KHOA_NHANH = re.compile(r"arm|variant|treatment|option|experimentArm", re.I)
_RE_KHOA_THANG = re.compile(r"winn|isbest|preferred|isleading", re.I)
_RE_KHOA_SO = re.compile(r"share|percent|ratio|watch|perform|score|rate|impression|ctr", re.I)
_RE_XONG = re.compile(r"STATE_(COMPLETED?|ENDED|FINISHED|CONCLUDED|STOPPED|EXPIRED)|RESULT_STATE_(?!NOT_CONCLUSIVE_YET)[A-Z_]+")
_RE_KHONG_KL = re.compile(r"INCONCLUSIVE|NO_WINNER|NOT_CONCLUSIVE(?!_YET)|_TIE\b|_TIED|NO_DIFFERENCE|EQUAL|SAME_PERFORM")


def _so_thuc(x: Any) -> Optional[float]:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def _nhanh(d: Dict[str, Any]) -> Dict[str, Any]:
    """Một nhánh thử nghiệm (dict thô) → {tieu_de, thang (True/False/None), so {khoá: số}, chu (mọi chuỗi ngắn)}."""
    ra: Dict[str, Any] = {"tieu_de": "", "thang": None, "so": {}, "chu": []}

    def duyet(x: Any, khoa: str = "", duong: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                duyet(v, str(k), duong + "/" + str(k))
        elif isinstance(x, list):
            for y in x:
                duyet(y, khoa, duong)
        else:
            if _RE_KHOA_THANG.search(khoa) and (x is True or (isinstance(x, str) and x.strip().lower() in ("true", "1"))):
                ra["thang"] = True
            elif _RE_KHOA_THANG.search(khoa) and x is False and ra["thang"] is None:
                ra["thang"] = False
            if isinstance(x, str):
                s = " ".join(x.split())
                if re.search(r"WINNER|WINNING|PREFERRED", s.upper()) and re.search(r"state|status|result|label", khoa, re.I):
                    ra["thang"] = True
                if (not ra["tieu_de"] and re.search(r"title", duong, re.I) and not re.search(r"id$|url|token|key", khoa, re.I)
                        and len(s) >= 2):
                    ra["tieu_de"] = s
                if s and len(s) <= 80:
                    ra["chu"].append(s)
            so = _so_thuc(x) if _RE_KHOA_SO.search(khoa) else None
            if so is not None:
                ra["so"].setdefault(khoa, so)
    duyet(d)
    return ra


def doc_ket_thu_nghiem(exp: Any) -> Dict[str, Any]:
    """`videoCreatorExperiment` THÔ (gói Studio của trang sửa) → {xong, khong_ket_luan, trang_thai_tho, nhanh: [...],
    thang: chỉ số nhánh thắng | None, suy_ra (thắng suy từ số, không có cờ), tho (JSON rút gọn để học khuôn)}.
    Khuôn thật của thử nghiệm KẾT THÚC chưa ai thấy (đo 18/10: STARTED + RESULT_STATE_NOT_CONCLUSIVE_YET) nên đọc
    RỘNG: cờ winner/preferred trên nhánh, khoá "winning…" tham chiếu id nhánh, cuối cùng số "share/percent" cao nhất."""
    if not isinstance(exp, dict) or not exp:
        return {"xong": False, "khong_ket_luan": False, "trang_thai_tho": "", "nhanh": [], "thang": None}
    trang: List[str] = []
    ds_nhanh: List[List[Dict[str, Any]]] = []
    tham_chieu: List[str] = []

    def duyet(x: Any, khoa: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                duyet(v, str(k))
        elif isinstance(x, list):
            if x and all(isinstance(y, dict) for y in x) and _RE_KHOA_NHANH.search(khoa):
                ds_nhanh.append(x)
            for y in x:
                duyet(y, khoa)
        elif isinstance(x, str):
            if re.search(r"state|status|result", khoa, re.I):
                trang.append(x)
            if _RE_KHOA_THANG.search(khoa):
                tham_chieu.append(x.strip())
    duyet(exp)
    s = " ".join(trang).upper()
    xong = bool(_RE_XONG.search(s))
    khong_kl = bool(xong and _RE_KHONG_KL.search(s))
    nhanh = [_nhanh(d) for d in (max(ds_nhanh, key=len) if ds_nhanh else [])]
    thang: Optional[int] = next((i for i, n in enumerate(nhanh) if n["thang"] is True), None)
    if thang is None and tham_chieu:
        thang = next((i for i, n in enumerate(nhanh) if any(t and t in n["chu"] for t in tham_chieu)), None)
    suy_ra = False
    if thang is None and xong and not khong_kl and len(nhanh) >= 2:
        khoa = next((k for n in nhanh for k in n["so"] if re.search(r"share|percent", k, re.I)), "")
        gt = [(n["so"].get(khoa), i) for i, n in enumerate(nhanh) if khoa and n["so"].get(khoa) is not None]
        if len(gt) >= 2:
            gt.sort(reverse=True)
            if gt[0][0] > gt[1][0]:
                thang, suy_ra = gt[0][1], True
    try:
        tho = json.dumps(exp, ensure_ascii=False)[:4000]
    except (TypeError, ValueError):
        tho = ""
    return {"xong": xong, "khong_ket_luan": khong_kl or (xong and thang is None), "ro_khong_ket_luan": khong_kl,
            "trang_thai_tho": s[:160],
            "nhanh": [{k: n[k] for k in ("tieu_de", "thang", "so")} for n in nhanh], "thang": thang, "suy_ra": suy_ra,
            "tho": tho}


def _moc_dat(m: Dict[str, Any]) -> str:
    return str(m.get("dat_luc") or m.get("cap_nhat") or m.get("luc") or "")[:19]


def _dang_chay(m: Dict[str, Any]) -> bool:
    return m.get("trang_thai") in (TT_DA_DAT, TT_DA_CO) and not m.get("ket_qua")


def _tuoi_ngay(moc: str, bay_gio: _dt.datetime) -> Optional[float]:
    try:
        return (bay_gio - _dt.datetime.fromisoformat(moc)).total_seconds() / 86400.0
    except ValueError:
        return None


def can_doc_ket_qua(goc: str, ma: str, bay_gio: Optional[_dt.datetime] = None,
                    ds: Optional[List[Dict[str, Any]]] = None, toi_da: int = TOI_DA_DOC_KQ_PHIEN) -> List[str]:
    """Video có thử nghiệm ĐANG CHẠY đủ tuổi (≥ `NGAY_DOC_KQ_TU` ngày), chưa đọc trong `GIO_DOC_KQ_LAI` giờ — cũ trước."""
    bay_gio = bay_gio or _dt.datetime.now()
    ds = doc_so(goc, ma) if ds is None else ds
    ra: List[Tuple[str, str]] = []
    da: set = set()
    for m in reversed(ds):
        vid = str(m.get("video_id") or "")
        if not vid or vid in da:
            continue
        da.add(vid)                                   # chỉ mục MỚI NHẤT của video
        if not _dang_chay(m):
            continue
        tuoi = _tuoi_ngay(_moc_dat(m), bay_gio)
        doc = _tuoi_ngay(str(m.get("doc_kq_luc") or "")[:19], bay_gio)
        if tuoi is None or tuoi < NGAY_DOC_KQ_TU or (doc is not None and doc * 24.0 < GIO_DOC_KQ_LAI):
            continue
        ra.append((_moc_dat(m), vid))
    return [v for _m, v in sorted(ra)][:max(0, int(toi_da))]


def _chuan(t: Any) -> str:
    import unicodedata  # noqa: PLC0415
    return " ".join(unicodedata.normalize("NFKC", str(t or "")).split())


def _ds_tieu_de(m: Dict[str, Any]) -> List[str]:
    """Tiêu đề các nhánh theo thứ tự đặt: A (đang chạy lúc đặt) rồi B, C."""
    k = m.get("ket") or {}
    ds = [t for t in (k.get("tieu_de") or k.get("tieu_de_doc_lai") or []) if t]
    return ds or ([m.get("tieu_de_a")] + list(m.get("tieu_de_them") or []) if m.get("tieu_de_a") else [])


def _nhan(t: str) -> str:
    try:
        from .tu_hoc import nhan_tieu_de_regex  # noqa: PLC0415 — đường lùi (bộ chạy DOM không có LLM); ghi `nhan_doan`
        return nhan_tieu_de_regex(t)
    except Exception:  # noqa: BLE001
        return ""


def ket_qua_tu(m: Dict[str, Any], kt: Dict[str, Any], bay_gio: Optional[_dt.datetime] = None,
               tieu_de_hien: str = "") -> Dict[str, Any]:
    """Mục sổ + kết quả đọc (`doc_ket_thu_nghiem`) → `ket_qua` {ket_luan, thang (A/B/C), tieu_de_thang, tieu_de_thua,
    nhan_thang, nhan_thua, so, suy_ra, luc}. Không có cờ thắng: YouTube ĐỔI tiêu đề video sang bản thắng khi B/C thắng —
    `tieu_de_hien` (tiêu đề video lúc đọc) khớp B/C → B/C thắng (`suy_ra` "tieu_de_hien"); khớp A thì không phân biệt
    được "A thắng" với "không kết luận / dừng" → không kết luận."""
    td = _ds_tieu_de(m)
    nhanh = kt.get("nhanh") or []
    i = kt.get("thang")
    ra: Dict[str, Any] = {"luc": _luc(bay_gio), "trang_thai_tho": kt.get("trang_thai_tho") or "",
                          "so": [n.get("so") or {} for n in nhanh], "suy_ra": bool(kt.get("suy_ra"))}
    if i is None and tieu_de_hien and not kt.get("ro_khong_ket_luan"):
        k = next((k for k, t in enumerate(td) if k > 0 and _chuan(t) == _chuan(tieu_de_hien)), None)
        if k is not None:
            i, ra["suy_ra"] = k, "tieu_de_hien"
            nhanh = []                                   # nhánh thô không mang tiêu đề: dùng thứ tự đặt
    if i is None:
        ra["ket_luan"] = KL_KHONG
        return ra
    t_thang = (nhanh[i].get("tieu_de") if i < len(nhanh) else "") or (td[i] if i < len(td) else "")
    j = next((k for k, t in enumerate(td) if _chuan(t) == _chuan(t_thang)), i if i < len(td) else None)
    thua = [t for k, t in enumerate(td) if k != j]
    ra.update(ket_luan=KL_THANG, thang=chr(65 + j) if j is not None else "?", tieu_de_thang=t_thang,
              tieu_de_thua=thua, nhan_thang=_nhan(t_thang), nhan_thua=[_nhan(t) for t in thua], nhan_doan=True)
    return ra


def _hoc_ket_qua(goc: str, ma: str, m: Dict[str, Any]) -> None:
    """Sự kiện não bộ phận "tieu-de" (loại `ket_qua`: bản THÁCH ĐẤU thắng = `thang`, A giữ = `truot` của bản thêm).
    Không chặn."""
    kq = m.get("ket_qua") or {}
    try:
        from . import nao_bo_phan  # noqa: PLC0415
        if kq.get("ket_luan") == KL_THANG:
            nd = "A/B tiêu đề {0}: YouTube chọn {1} «{2}» hơn {3}".format(
                m.get("video_id"), kq.get("thang"), str(kq.get("tieu_de_thang") or "")[:60],
                " / ".join("«{0}»".format(t[:40]) for t in kq.get("tieu_de_thua") or []))
            so = {"ket": "truot" if kq.get("thang") == "A" else "thang", "thang_la": kq.get("thang"),
                  "kieu_tieu_de": kq.get("nhan_thang"), "kieu_thua": kq.get("nhan_thua"), "nguon": m.get("nguon"),
                  "id": m.get("id"), "suy_ra": kq.get("suy_ra")}
        else:
            nd = "A/B tiêu đề {0}: kết thúc KHÔNG KẾT LUẬN ({1})".format(m.get("video_id"),
                                                                        str(kq.get("ly_do") or kq.get("trang_thai_tho") or "")[:80])
            so = {"ket": "khong_ket_luan", "id": m.get("id"), "nguon": m.get("nguon")}
        nao_bo_phan.ghi(goc, "tieu-de", "ket_qua", kenh=ma, ma_goi=str(m.get("ma_goi") or ""), noi_dung=nd[:600],
                        so=so, nguon="ab_tieu_de", khoa="ab-tieu-de|{0}|ket".format(m.get("id")))
    except Exception:  # noqa: BLE001
        pass


def kt_khong_con() -> Dict[str, Any]:
    """Gói Studio đọc ĐƯỢC mà `videoCreatorExperiment` rỗng ở video sổ ghi đang thử nghiệm = thử nghiệm đã kết thúc
    (Studio gỡ khỏi trang sửa); bản thắng chỉ còn suy từ tiêu đề hiện tại (`ket_qua_tu`)."""
    return {"xong": True, "khong_ket_luan": True, "ro_khong_ket_luan": False, "nhanh": [], "thang": None,
            "trang_thai_tho": "KHONG_CON_THU_NGHIEM"}


def ghi_doc_ket_qua(goc: str, ma: str, vid: str, kt: Optional[Dict[str, Any]],
                    bay_gio: Optional[_dt.datetime] = None, tieu_de_hien: str = "") -> Optional[Dict[str, Any]]:
    """Bộ chạy DOM vừa đọc thử nghiệm của `vid` (`kt` = `doc_ket_thu_nghiem` / `kt_khong_con`; None = đọc hỏng) và
    tiêu đề video lúc đọc. Luôn ghi mốc đọc; kết thúc → `trang_thai` xong + `ket_qua` + học; chưa kết thúc mà quá
    `NGAY_DONG_KHONG_KL` → đóng không kết luận. Trả `ket_qua` khi vừa đóng, None khi còn chạy / không có mục."""
    bay_gio = bay_gio or _dt.datetime.now()
    ds = doc_so(goc, ma)
    m = muc_cua(goc, ma, vid, ds)
    if not m or not _dang_chay(m):
        return None
    m["doc_kq_luc"] = _luc(bay_gio)
    if kt is not None:
        m["doc_kq"] = {k: kt.get(k) for k in ("xong", "khong_ket_luan", "trang_thai_tho", "thang", "suy_ra")}
        if kt.get("xong") and kt.get("tho"):
            m["doc_kq_tho"] = kt["tho"]
    kq: Optional[Dict[str, Any]] = None
    if kt is not None and kt.get("xong"):
        kq = ket_qua_tu(m, kt, bay_gio, tieu_de_hien=tieu_de_hien)
    elif (_tuoi_ngay(_moc_dat(m), bay_gio) or 0) >= NGAY_DONG_KHONG_KL:
        kq = {"luc": _luc(bay_gio), "ket_luan": KL_KHONG, "ly_do": "đặt quá {0:g} ngày chưa có kết quả".format(
            NGAY_DONG_KHONG_KL), "trang_thai_tho": (kt or {}).get("trang_thai_tho") or ""}
    if kq is not None:
        m.update(trang_thai=TT_XONG, ket_qua=kq, cap_nhat=_luc(bay_gio))
    ghi_so(goc, ma, ds)
    if kq is not None:
        _hoc_ket_qua(goc, ma, m)
    return kq


def dong_qua_han(goc: str, ma: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Thử nghiệm đặt quá `NGAY_DONG_KHONG_KL` ngày mà máy chưa đọc được kết quả (kênh mất phiên, bộ chạy hoãn…) →
    đóng "không kết luận" (không học gì). Gọi mỗi lượt giám đốc kênh. Trả các mục vừa đóng."""
    bay_gio = bay_gio or _dt.datetime.now()
    ds = doc_so(goc, ma)
    ra = []
    for m in ds:
        if _dang_chay(m) and (_tuoi_ngay(_moc_dat(m), bay_gio) or 0) >= NGAY_DONG_KHONG_KL and \
                muc_cua(goc, ma, str(m.get("video_id") or ""), ds) is m:
            m.update(trang_thai=TT_XONG, cap_nhat=_luc(bay_gio), ket_qua={
                "luc": _luc(bay_gio), "ket_luan": KL_KHONG,
                "ly_do": "đặt quá {0:g} ngày chưa đọc được kết quả".format(NGAY_DONG_KHONG_KL)})
            ra.append(m)
    if ra:
        ghi_so(goc, ma, ds)
        for m in ra:
            _hoc_ket_qua(goc, ma, m)
    return ra


def ket_qua_xong(goc: str, ma: str) -> List[Dict[str, Any]]:
    """Mọi `ket_qua` THẮNG đã đọc của kênh (cũ → mới) — `tu_hoc.bang_diem` + `khoi_thang` đọc."""
    return [dict(m["ket_qua"], video_id=m.get("video_id"), ma_goi=m.get("ma_goi")) for m in doc_so(goc, ma)
            if m.get("trang_thai") == TT_XONG and (m.get("ket_qua") or {}).get("ket_luan") == KL_THANG]


def khoi_thang(goc: str, ma: str, toi_da: int = 6) -> str:
    """Khối lời nhắc cho lượt VIẾT/CHẤM tiêu đề: các cặp thắng/thua A/B mới nhất của CHÍNH kênh (YouTube chọn theo
    thời gian xem). Chưa có kết quả → "" (lời nhắc y hệt từng byte)."""
    ds = ket_qua_xong(goc, ma)[-max(1, int(toi_da)):]
    if not ds:
        return ""
    dong = ["- THẮNG «{0}» ({1}) — thua: {2}".format(str(k.get("tieu_de_thang") or "")[:90], k.get("nhan_thang") or "?",
                                                    " / ".join("«{0}»".format(str(t)[:70]) for t in k.get("tieu_de_thua")
                                                               or []) or "?")
            for k in reversed(ds)]
    return ("KẾT QUẢ A/B TIÊU ĐỀ CỦA KÊNH (YouTube chọn bản thắng theo thời gian xem trên chính video của kênh — học "
            "GÓC BẤM của bản thắng, đừng chép nguyên câu):\n" + "\n".join(dong))
