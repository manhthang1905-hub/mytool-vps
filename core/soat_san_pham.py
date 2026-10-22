"""SOÁT SẢN PHẨM HẰNG TUẦN + VÒNG CẢI TIẾN (17/10/2026) — thay ba lần soát tay của người giám sát.

═══ VÌ SAO ═══ Ba lần soát tay 16–17/10: đọc chữ 98 bìa đang chạy (6 bìa sai chữ), chấm 150 ảnh cảnh (51% lệch nội dung,
9% rợn), đo độc đáo kịch bản (chép, có cả dịch từng câu từ nguồn Anh). Tệp này làm cả ba mỗi tuần, mỗi kênh, ghi tỉ lệ
theo thời gian, và khi tỉ lệ xấu đi thì tự mở việc cải tiến có đo trước/sau.

═══ MỘT LƯỢT TUẦN (`soat_kenh`) ═══
  bia      bìa ĐANG CHẠY của ≤ `SO_BIA` video gần nhất — `bat_thuong.soat_bia_song` (dấu cổng chữ / hai lượt đọc mù);
           bìa sai chữ → hàng sửa bìa (skill S06)
  anh      ≤ `SO_ANH` ảnh cảnh lấy đều trong lượt MỚI NHẤT còn ảnh — giám khảo của `core.chon_anh_canh` (cùng lời nhắc
           `loi_nhac_cham`, cùng mô hình `MO_HINH_CHAM`, đi ví): tỉ lệ lệch nội dung (≤ 5), rợn (cờ / giọng ≤ 6), lỗi
           vẽ (≤ 6), lệch phong cách (≤ 6), đạt cả bốn (≥ 7), điểm trung bình
  doc_dao  `core.do_doc_dao.bang_luot` 10 lượt mới nhất + xuyên ngôn ngữ (dịch ≤ 3 nguồn mới / tuần, cache ngoài PROJECTS)
Sổ: `workspace/tu-kiem/soat-tuan/<kênh>.jsonl`.

═══ XẤU ĐI → VIỆC CẢI TIẾN ẢNH (`cai_tien_anh`) ═══ Khi lệch nội dung tăng ≥ 15 điểm (hoặc ≥ 40%), rợn ≥ 10%, hay đạt
cả bốn giảm ≥ 15 điểm so với lượt tuần trước: (1) AI chắt MỘT luật ngắn từ lý do giám khảo của các tấm tệ; (2) chạy vòng
viết lại lời nhắc SẴN CÓ (`chon_anh_canh.viet_lai_canh`, luật đó làm ghi chú) trên ≤ 4 cảnh tệ nhất, vẽ 1 tấm mỗi cảnh,
chấm bằng ĐÚNG giám khảo ấy; (3) THANH ĐẠT (`dat_thanh`): ≥ 3 cảnh chấm được, điểm trung bình tăng ≥ `THANH_TANG`
(1,5), số cảnh lệch nội dung giảm ≥ 2 (hoặc về 0), không thêm tấm rợn nào. Qua thanh và kênh không tắt
(`kenh.yaml: tu_ap_prompt_anh: false`) → SAO LƯU `CHANNEL/<k>/prompt/7-canh.md` vào `workspace/ban-va/<ngày>-tu-kiem-anh-<k>/`
(kèm GHI-CHU.md) rồi chèn / thay khối `<!-- tu-kiem -->` mang luật ấy. Không qua thanh → chỉ ghi não, không đổi gì.

    python -X utf8 -m core.soat_san_pham tuan --kenh K [--thu] [--goc G]   một lượt tuần (+ cải tiến nếu xấu đi)
    python -X utf8 -m core.soat_san_pham xem [--goc G]                     tỉ lệ tuần gần nhất mọi kênh (chỉ đọc)
"""

from __future__ import annotations

import datetime as _dt
import glob
import hashlib
import io
import json
import os
import shutil
import statistics
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SO_BIA, SO_ANH, SO_CANH_CAI_TIEN = 10, 20, 4
THANH_TANG = 1.5
XAU = {"noi_dung_hong": (15.0, 40.0), "ron": (5.0, 10.0), "dat_ca": (-15.0, None)}
DAU, HET = "<!-- tu-kiem:bat-dau -->", "<!-- tu-kiem:het -->"
THU_MUC = ("workspace", "tu-kiem")


def _json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _thu_muc(goc: str, *phan: str) -> str:
    return os.path.join(goc, *THU_MUC, *phan)


def _bam(*p: Any) -> str:
    return hashlib.sha1("|".join(str(x) for x in p).encode("utf-8")).hexdigest()[:12]


# ── ảnh cảnh ───────────────────────────────────────────────────────────────────

def mau_canh(goc: str, kenh: str, n: int = SO_ANH) -> Dict[str, Any]:
    """Lượt MỚI NHẤT còn `5-anh/` + `4-canh.json` → ≤ n cảnh lấy đều: {luot, canh: [{so, tep, loi_doc, ai, prompt}]}."""
    d = os.path.join(goc, "PROJECTS", "AUTO", kenh)
    try:
        luot = sorted((x for x in os.listdir(d) if x.isdigit()), reverse=True)
    except OSError:
        return {"luot": "", "canh": []}
    for l in luot:
        tm = os.path.join(d, l)
        canh = _json(os.path.join(tm, "4-canh.json"))
        if not isinstance(canh, list) or not os.path.isdir(os.path.join(tm, "5-anh")):
            continue
        co = []
        for i, c in enumerate(canh, 1):
            so = int(c.get("scene_id") or i) if isinstance(c, dict) else i
            p = os.path.join(tm, "5-anh", "{0}.png".format(so))
            if isinstance(c, dict) and os.path.isfile(p):
                co.append({"so": so, "tep": p, "loi_doc": str(c.get("srt_text") or ""),
                           "ai": ", ".join(x for x in (str(c.get("primary_subject") or ""),
                                                       str(c.get("characters_used") or "")) if x) or "(not given)",
                           "prompt": str(c.get("img_prompt") or "")})
        if len(co) >= 5:
            buoc = max(1.0, len(co) / float(n))
            return {"luot": l, "canh": [co[int(i * buoc)] for i in range(min(n, len(co)))]}
    return {"luot": "", "canh": []}


def _ref(goc: str, kenh: str) -> str:
    p = os.path.join(goc, "CHANNEL", kenh, "nv", "nv1.png")
    return p if os.path.isfile(p) else ""


def _phong(goc: str, kenh: str) -> str:
    try:
        from .kenh import doc_kenh  # noqa: PLC0415
        st = getattr(doc_kenh(goc, kenh), "style", None) or {}
    except Exception:  # noqa: BLE001
        st = {}
    return " ".join(str(st.get(k) or "") for k in ("scene_plan_style", "palette")).strip()


def cham_mot(goi: Callable[..., str], tep: str, *, loi_doc: str, ai: str, phong: str, ref: str, khoa: str,
             nc_anh: Tuple[str, str] = ("", "")
             ) -> Optional[Dict[str, Any]]:
    """MỘT ảnh qua giám khảo của `chon_anh_canh` (đi ví — `qua_vi`). None = AI hỏng / trả rác."""
    from . import chon_anh_canh as cac  # noqa: PLC0415
    from .goi_van_ban import loc_json, qua_vi  # noqa: PLC0415
    ln = cac.loi_nhac_cham(loi_doc=loi_doc, mo_ta=ai, phong_cach=phong, so_tham_chieu=1 if ref else 0, so_ung_vien=1,
                           tieng_en=nc_anh[0], kenh_en=nc_anh[1])
    anh = ([cac.anh_data_url(ref, 512, nhan="REF")] if ref else []) + [cac.anh_data_url(tep, 768, nhan="1")]
    try:
        with qua_vi():
            tho = goi(ln, mo_hinh=cac.MO_HINH_CHAM, khoa=khoa, toi_da_token=1500, anh=anh)
        return cac.doc_cham(loc_json(str(tho or "")), 1).get(1)
    except Exception:  # noqa: BLE001
        return None


def ti_le_anh(kq: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    ds = [m for m in kq if m]
    n = len(ds)
    if not n:
        return {"n": 0}

    def pt(f):
        return round(100.0 * sum(1 for m in ds if f(m)) / n, 1)
    d = lambda m, k: float((m.get("diem") or {}).get(k) or 0)  # noqa: E731
    return {"n": n, "noi_dung_hong": pt(lambda m: d(m, "noi_dung") <= 5),
            "ron": pt(lambda m: m.get("kinh_di") or d(m, "giong") <= 6), "loi_ve": pt(lambda m: d(m, "loi") <= 6),
            "lech_phong": pt(lambda m: d(m, "phong_cach") <= 6),
            "dat_ca": pt(lambda m: all(d(m, k) >= 7 for k in ("noi_dung", "giong", "loi", "phong_cach"))),
            "diem_tb": round(statistics.mean(float(m.get("tong") or 0) for m in ds), 2)}


def xau_hon(cu: Dict[str, Any], moi: Dict[str, Any]) -> List[str]:
    """THUẦN: các tỉ lệ ảnh xấu đi vượt ngưỡng (`XAU`: (đổi điểm %, mức tuyệt đối))."""
    if not moi.get("n"):
        return []
    ra = []
    for k, (doi, muc) in XAU.items():
        v, c = moi.get(k), (cu or {}).get(k)
        if v is None:
            continue
        if doi < 0:
            if c is not None and v - c <= doi:
                ra.append(k)
        elif (c is not None and v - c >= doi) or (muc is not None and v >= muc):
            ra.append(k)
    return ra


# ── độc đáo ────────────────────────────────────────────────────────────────────

def doc_dao(goc: str, kenh: str, *, thu: bool = False) -> Dict[str, Any]:
    from . import do_doc_dao as dd  # noqa: PLC0415
    dich = None if thu else dd._dich_mac_dinh(goc)  # noqa: SLF001
    xu = dd._XuyenBaoCao(thu_muc_dich=_thu_muc(goc, "dich"), dich=dich, con_lai=0 if thu else 3)  # noqa: SLF001
    ds = dd.bang_luot(goc, kenh, 10, xu)
    cung = [x["ti_le"] for x in ds if not x["khac_tieng"]]
    xuyen = [x["cau_sat"] for x in ds if x["khac_tieng"] and x.get("cau_sat") is not None]
    chep = [x["luot"] for x in ds if (not x["khac_tieng"] and x["ti_le"] > dd.NGUONG_VIET_LAI)
            or (x["khac_tieng"] and (x.get("cau_sat") or 0) > dd.NGUONG_XUYEN_VIET_LAI)]
    return {"n": len(ds), "trung_vi": round(statistics.median(cung), 3) if cung else None,
            "xuyen_trung_vi": round(statistics.median(xuyen), 3) if xuyen else None, "chep": chep,
            "ti_le_chep": round(100.0 * len(chep) / len(ds), 1) if ds else None}


# ── vòng cải tiến ảnh ─────────────────────────────────────────────────────────

LOI_NHAC_LUAT = """You improve the scene-image prompt template of a Japanese psychology YouTube channel. The art director
rejected these generated scene images for these reasons:
{ly_do}
Write ONE short rule (at most 2 sentences, English) to add to the template that tells the scene-prompt writer how to avoid
these failures (concrete: what must be visible, what must never appear). Return the rule only."""


def dat_thanh(truoc: Sequence[Dict[str, Any]], sau: Sequence[Dict[str, Any]]) -> Tuple[bool, str]:
    """THUẦN: thanh đạt trước/sau (cùng cảnh, cùng giám khảo)."""
    cap = [(a, b) for a, b in zip(truoc, sau) if a and b]
    if len(cap) < 3:
        return False, "chỉ {0} cảnh chấm được cả trước lẫn sau (< 3)".format(len(cap))
    tang = statistics.mean(float(b.get("tong") or 0) for _a, b in cap) - statistics.mean(float(a.get("tong") or 0)
                                                                                     for a, _b in cap)
    nd = lambda m: float((m.get("diem") or {}).get("noi_dung") or 0) <= 5  # noqa: E731
    hong_a, hong_b = sum(nd(a) for a, _ in cap), sum(nd(b) for _, b in cap)
    ron_moi = sum(1 for a, b in cap if b.get("kinh_di") and not a.get("kinh_di"))
    ok = tang >= THANH_TANG and (hong_a - hong_b >= 2 or (hong_a > 0 and hong_b == 0)) and ron_moi == 0
    return ok, "điểm TB {0:+.2f} (cần ≥ +{1}), lệch nội dung {2}→{3}, rợn mới {4}".format(tang, THANH_TANG, hong_a,
                                                                                       hong_b, ron_moi)


def ap_luat(goc: str, kenh: str, luat: str, ly_do: str, bay: Optional[_dt.datetime] = None) -> str:
    """Sao lưu rồi chèn / thay khối tự kiểm trong `CHANNEL/<k>/prompt/7-canh.md`. Trả đường bản sao lưu."""
    bay = bay or _dt.datetime.now()
    p = os.path.join(goc, "CHANNEL", kenh, "prompt", "7-canh.md")
    with io.open(p, encoding="utf-8") as tep:
        cu = tep.read()
    sl = os.path.join(goc, "workspace", "ban-va", "{0:%Y-%m-%d}-tu-kiem-anh-{1}".format(bay, kenh))
    os.makedirs(sl, exist_ok=True)
    shutil.copy2(p, os.path.join(sl, "7-canh.md"))
    with io.open(os.path.join(sl, "GHI-CHU.md"), "w", encoding="utf-8") as tep:
        tep.write("# Tự kiểm — cải tiến lời nhắc ảnh cảnh {0} ({1:%d/%m/%Y %H:%M})\n\nVì sao: {2}\n\nLuật thêm:\n\n> {3}\n\n"
                  "Hoàn tác: chép `7-canh.md` ở thư mục này đè lên `CHANNEL/{0}/prompt/7-canh.md`, hoặc xoá khối "
                  "`{4}` … `{5}`.\n".format(kenh, bay, ly_do, luat, DAU, HET))
    khoi = "{0}\n## Luật tự kiểm ({1:%d/%m/%Y}, đo trước/sau)\n{2}\n{3}".format(DAU, bay, luat.strip(), HET)
    if DAU in cu and HET in cu:
        moi = cu[:cu.index(DAU)] + khoi + cu[cu.index(HET) + len(HET):]
    else:
        moi = cu.rstrip() + "\n\n" + khoi + "\n"
    with io.open(p + ".tam", "w", encoding="utf-8") as tep:
        tep.write(moi)
    os.replace(p + ".tam", p)
    return sl


def cai_tien_anh(goc: str, kenh: str, canh: Sequence[Dict[str, Any]], cham: Sequence[Optional[Dict[str, Any]]], *,
                 goi: Callable[..., str], ve: Callable[[str, int, str, List[str]], List[str]], thu: bool = False,
                 log: Callable[[str], None] = print) -> Dict[str, Any]:
    from . import chon_anh_canh as cac  # noqa: PLC0415
    cap = sorted(((c, m) for c, m in zip(canh, cham) if m), key=lambda x: float(x[1].get("tong") or 0))[:SO_CANH_CAI_TIEN]
    if len(cap) < 3:
        return {"ket": "bo", "ly_do": "không đủ cảnh đã chấm"}
    ly = "\n".join("- {0} (content {1}, tone {2}): {3} {4}".format(
        c["loi_doc"][:80], (m.get("diem") or {}).get("noi_dung"), (m.get("diem") or {}).get("giong"), m.get("ly_do", ""),
        m.get("sua", "")) for c, m in cap)
    luat = " ".join(str(goi(LOI_NHAC_LUAT.format(ly_do=ly), mo_hinh=cac.MO_HINH_CHAM, khoa="tu-kiem-luat:" + _bam(ly),
                            toi_da_token=300) or "").split())[:400]
    if len(luat) < 20:
        return {"ket": "bo", "ly_do": "AI không chắt được luật"}
    try:
        from .kenh import doc_kenh  # noqa: PLC0415
        st = getattr(doc_kenh(goc, kenh), "style", None) or {}
    except Exception:  # noqa: BLE001
        st = {}
    ref, phong = _ref(goc, kenh), _phong(goc, kenh)
    nc_anh = cac.ngu_canh_anh(goc, kenh)
    thu_muc = _thu_muc(goc, "cai-tien", kenh, _dt.date.today().isoformat())
    os.makedirs(thu_muc, exist_ok=True)
    truoc, sau, mau = [], [], []
    for c, m in cap:
        than, duoi = cac.tach_than_duoi(c["prompt"], st)
        moi = cac.viet_lai_canh(lambda l: goi(l, mo_hinh=cac.MO_HINH_CHAM, khoa="tu-kiem-vl:" + _bam(l), toi_da_token=1200),
                                than, loi_doc=c["loi_doc"], ghi_chu="- " + luat + "\n- " + str(m.get("ly_do") or ""),
                                tieng_en=nc_anh[0], kenh_en=nc_anh[1])
        if not moi:
            continue
        ln = "{0}, {1}".format(moi.rstrip(" ,."), duoi) if duoi else moi
        dich = os.path.join(thu_muc, "{0}.png".format(c["so"]))
        try:
            tep = (ve(ln, 1, "tu-kiem-ve:" + _bam(kenh, ln), [dich]) or [""])[0]
        except Exception as loi:  # noqa: BLE001
            log("cải tiến ảnh: vẽ cảnh {0} hỏng ({1})".format(c["so"], str(loi)[:100]))
            continue
        b = cham_mot(goi, tep, loi_doc=c["loi_doc"], ai=c["ai"], phong=phong, ref=ref, nc_anh=nc_anh,
                     khoa="tu-kiem-cham-sau:" + _bam(tep)) if tep else None
        truoc.append(m)
        sau.append(b)
        mau.append({"so": c["so"], "truoc": m.get("tong"), "sau": (b or {}).get("tong"), "tep": tep})
    ok, cau = dat_thanh(truoc, sau)
    ra = {"ket": "dat" if ok else "khong_dat", "luat": luat, "thanh": cau, "mau": mau, "da_ap": ""}
    cai = {}
    try:
        from .ky_nang import _kenh_yaml  # noqa: PLC0415
        cai = _kenh_yaml(goc, kenh)
    except Exception:  # noqa: BLE001
        pass
    if ok and cai.get("tu_ap_prompt_anh") is not False and not thu:
        ra["da_ap"] = ap_luat(goc, kenh, luat, cau)
    if not thu:
        try:
            from . import nao_bo_phan  # noqa: PLC0415
            nao_bo_phan.ghi(goc, "anh-clip", "sua" if ra["da_ap"] else "do", kenh=kenh,
                            noi_dung="tự kiểm cải tiến ảnh cảnh: {0} — {1}{2}".format(
                                ra["ket"], cau, " → ĐÃ áp vào 7-canh.md: " + luat if ra["da_ap"] else ""),
                            so={"mau": mau}, nguon="tu_kiem", khoa="tu-kiem:cai-tien:{0}:{1}".format(kenh, _bam(luat)))
        except Exception:  # noqa: BLE001
            pass
    return ra


# ── lượt tuần ─────────────────────────────────────────────────────────────────

def doc_lich_su(goc: str, kenh: str) -> List[Dict[str, Any]]:
    try:
        with io.open(_thu_muc(goc, "soat-tuan", kenh + ".jsonl"), encoding="utf-8") as tep:
            return [json.loads(d) for d in tep if d.strip()]
    except (OSError, ValueError):
        return []


def soat_kenh(goc: str, kenh: str, *, thu: bool = False, goi: Optional[Callable[..., str]] = None,
              ve: Optional[Callable[..., List[str]]] = None, tai: Any = None,
              log: Callable[[str], None] = print) -> Dict[str, Any]:
    from . import bat_thuong  # noqa: PLC0415
    if goi is None and not thu:
        goi = bat_thuong._goi_that(goc)  # noqa: SLF001
    ra: Dict[str, Any] = {"kenh": kenh, "luc": _dt.datetime.now().isoformat(timespec="seconds")}
    # bìa đang chạy
    vids = [x["ma"] for x in bat_thuong.tin_hieu_kenh(goc, kenh)][-SO_BIA:]
    import tempfile  # noqa: PLC0415
    bia = bat_thuong.soat_bia_song(goc, kenh, vids, goi, tai=tai,
                                   luu=tempfile.mkdtemp(prefix="tu-kiem-thu-") if thu else "")
    sai = [b for b in bia if b["ok"] is False]
    ra["bia"] = {"n": len(bia), "doc_duoc": sum(1 for b in bia if b["ok"] is not None), "sai": [b["ma"] or b["vid"] for b in sai]}
    ra["bia"]["xep_sua"] = len(bat_thuong.xep_sua_bia(goc, kenh, sai, thu=thu))
    # ảnh cảnh
    mc = mau_canh(goc, kenh)
    ref, phong = _ref(goc, kenh), _phong(goc, kenh)
    from . import chon_anh_canh as cac_nc  # noqa: PLC0415 — 22/10/2026: câu tả kênh theo hồ sơ ngách
    nc_anh = cac_nc.ngu_canh_anh(goc, kenh)
    cham = [cham_mot(goi, c["tep"], loi_doc=c["loi_doc"], ai=c["ai"], phong=phong, ref=ref, nc_anh=nc_anh,
                     khoa="tu-kiem-cham:{0}:{1}:{2}".format(kenh, mc["luot"], c["so"])) if goi else None
            for c in mc["canh"]]
    ra["anh"] = dict(ti_le_anh(cham), luot=mc["luot"], mau=len(mc["canh"]))
    # độc đáo
    try:
        ra["doc_dao"] = doc_dao(goc, kenh, thu=thu)
    except Exception as loi:  # noqa: BLE001
        ra["doc_dao"] = {"loi": str(loi)[:200]}
    dd = ra["doc_dao"]
    if not thu and (dd.get("ti_le_chep") or 0) >= 30:
        try:
            from . import nao_bo_phan  # noqa: PLC0415
            nao_bo_phan.ghi(goc, "kich-ban", "loi", kenh=kenh, noi_dung="soát tuần: {0}% lượt gần đây chép nguồn quá ngưỡng "
                            "({1}) — rủi ro bị từ chối kiếm tiền".format(dd["ti_le_chep"], ", ".join(dd.get("chep") or [])),
                            nguon="tu_kiem", khoa="tu-kiem:chep:{0}:{1}".format(kenh, _dt.date.today().isoformat()))
        except Exception:  # noqa: BLE001
            pass
    truoc = next((x for x in reversed(doc_lich_su(goc, kenh)) if (x.get("anh") or {}).get("n")), {})
    ra["anh_xau"] = xau_hon(truoc.get("anh") or {}, ra["anh"])
    if ra["anh_xau"] and goi is not None and not thu:
        try:
            if ve is None:
                from .bia_lo import _ve_that  # noqa: PLC0415
                ve = _ve_that(goc, [ref] if ref else [])
            ra["cai_tien"] = cai_tien_anh(goc, kenh, mc["canh"], cham, goi=goi, ve=ve, log=log)
        except Exception as loi:  # noqa: BLE001
            ra["cai_tien"] = {"ket": "hong", "ly_do": str(loi)[:200]}
    elif ra["anh_xau"]:
        ra["cai_tien"] = {"ket": "se_chay", "ly_do": "chạy thử: sẽ mở việc cải tiến (" + ", ".join(ra["anh_xau"]) + ")"}
    if not thu:
        p = _thu_muc(goc, "soat-tuan", kenh + ".jsonl")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "a", encoding="utf-8") as tep:
            tep.write(json.dumps(ra, ensure_ascii=False) + "\n")
    return ra


def can_chay(goc: str, kenh: str, bay: Optional[_dt.datetime] = None, ngay: int = 7) -> Tuple[bool, str]:
    bay = bay or _dt.datetime.now()
    ls = doc_lich_su(goc, kenh)
    if not ls:
        return True, "chưa soát sản phẩm lần nào"
    try:
        cuoi = _dt.datetime.fromisoformat(str(ls[-1].get("luc"))[:19])
    except ValueError:
        return True, "sổ soát hỏng mốc"
    return ((bay - cuoi).days >= ngay), "lần soát cuối {0:%d/%m}".format(cuoi)


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.soat_san_pham")
    p.add_argument("lenh", choices=("tuan", "xem"))
    p.add_argument("--kenh", default="")
    p.add_argument("--thu", action="store_true")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    if a.lenh == "tuan":
        print(json.dumps(soat_kenh(goc, a.kenh, thu=a.thu), ensure_ascii=False, indent=1))
        return 0
    from .ky_nang import _cac_kenh  # noqa: PLC0415
    for k in ([a.kenh] if a.kenh else _cac_kenh(goc)):
        ls = doc_lich_su(goc, k)
        x = ls[-1] if ls else {}
        print("{0:<10} {1}  bìa {2} · ảnh {3} · độc đáo {4}".format(k, str(x.get("luc") or "chưa soát")[:16], x.get("bia"),
                                                                 x.get("anh"), x.get("doc_dao")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
