"""NHÃN NGHĨA TIÊU ĐỀ (G2 bản 2, 20/10/2026) — LLM ví ĐỌC tiêu đề và gắn NHÃN NGHĨA cố định cho hàm giá trị.

═══ VÌ SAO ═══ Chủ dự án 20/10: *"để mô hình hiểu nghĩa tiêu đề chứ không chỉ đếm chữ, sao không dùng ShopAPI"*. Hàm
giá trị bản 1 (`core/gia_tri`) chỉ đếm n-gram ký tự. ShopAPI KHÔNG có cổng nhúng (POST /v1/embeddings → không có),
nhưng LLM chữ của ví đọc được tiêu đề và trả NHÃN theo một lược đồ cố định (`TRUONG`): kiểu hứa hẹn, tệp khán giả, cảm
xúc kích hoạt, độ cược, độ cụ thể, ngược đời, dấu uy tín… cộng một cụm CHỦ ĐỀ ngắn (tiếng Anh ≤ 6 từ) để gom cụm.
Nhãn là ĐẶC TRƯNG cho mô hình học từ số (ridge) — LLM KHÔNG chấm điểm, không quyết gì.

═══ CÁCH CHẠY ═══ lô `LO` tiêu đề / một lượt gọi (`goi_van_ban(..., qua_vi=True)` — LUÔN đi ví ShopAPI, không bao giờ
thuê bao Claude Max), đầu ra JSON gọn `{"1": "mã|mã|…|chủ đề", …}` (mã ngắn theo thứ tự `TRUONG` — rẻ token ra), đọc
chặt + kiểm từng mã, tiêu đề hỏng/thiếu → MỘT lượt sửa (chỉ các tiêu đề hỏng); vẫn hỏng → không ghi (lần sau hỏi
lại). Khoá Idempotency = sha1(nội dung lô). Song song `SO_LUONG` lượt; van ví chặn → dừng; đang tải lên YouTube → đợi.
Nhớ đệm theo sha1(tiêu đề chuẩn NFKC) ở `workspace/gia-tri/nhan-nghia.jsonl` (chỉ nối thêm; không lên kho). Số token
THẬT (`usage`) + tiền ước theo giá ví → `workspace/gia-tri/nhan-nghia-chi.jsonl`; ước tổng vượt `TRAN_CHI_VND` → dừng.

═══ ĐO 20–21/10/2026 ═══ lượt đầu 90.946 tiêu đề (1.821 lô, 2.200 lượt gọi): đạt 90.650 (99,7%); usage 5,21 triệu token
vào + 4,89 triệu ra = 51.869đ; sổ cái ví cùng khung giờ (mọi «Trừ tiền LLM claude-sonnet-5 …») 54.027đ — ~0,6đ/tiêu đề.
Cổng đêm chậm (20–70 giây/lượt sau 23:30) → 6 lượt song song nhanh gấp ~3.

Dùng:  python -X utf8 -m core.nhan_nghia gan [--toi-da N] [--goc G]      (gắn tiêu đề CHƯA có nhãn: đối thủ + ta + ứng viên)
       python -X utf8 -m core.nhan_nghia thu "<tiêu đề>" … [--goc G]     (một lô thử, in nhãn)
       python -X utf8 -m core.nhan_nghia chi [--goc G]                   (tổng token / tiền đã chi cho nhãn)
       python -X utf8 -m core.nhan_nghia bao-cao [--goc G]               (nhãn nào kéo / đẩy xác suất nổ → bao-cao-nhan.md
                                                                          + khối «tín hiệu thị trường» của lời nhắc tiêu đề)
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import random
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

PHIEN_BAN = 1
THU_MUC = ("workspace", "gia-tri")
TEP_NHO = "nhan-nghia.jsonl"
TEP_CHI = "nhan-nghia-chi.jsonl"
LO = 50
SO_LUONG = 4
#: Giá ví (µVND/token) chủ đưa 20/10/2026 — chỉ để ƯỚC trước khi sổ cái ví xác nhận.
GIA_VAO_MICRO = 1750
GIA_RA_MICRO = 8750
#: Ước tổng chi cho một lượt gắn vượt trần → dừng (đề bài 20/10: dừng và báo nếu ước > 150.000đ).
TRAN_CHI_VND = 150_000.0
TOI_DA_TOKEN = 6000
#: Khoá cài đặt (`workspace/cai-dat.json`): gắn nhãn hằng ngày (mặc định BẬT).
KHOA_CAI = "nhan_nghia_tieu_de"

#: Lược đồ nhãn: (mã trường, mô tả cho LLM, các giá trị). Thứ tự = thứ tự mã trong đầu ra. KHÔNG đổi thứ tự / bớt giá trị
#: mà không tăng `PHIEN_BAN` (nhớ đệm cũ đọc theo thứ tự này).
TRUONG: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    ("hua", "promise type — what the title promises the viewer: secret (hidden truth/insider), reason (why X happens), "
            "howto (method/tips), list (N things/types), warning (danger/avoid), compare (A vs B / who is better), "
            "story (anecdote/case), traits (characteristics of a kind of person), fact (plain knowledge), other",
     ("secret", "reason", "howto", "list", "warning", "compare", "story", "traits", "fact", "other")),
    ("tuoi", "target age band named or clearly implied: none, 40s, 50s, 60s, 70s, 80s, senior (old people in general)",
     ("none", "40s", "50s", "60s", "70s", "80s", "senior")),
    ("gioi", "target gender: any, male, female", ("any", "male", "female")),
    ("vai", "target role/persona: none, parent, spouse (husband/wife/marriage), retiree, single (living alone), "
            "adultchild (children of aging parents), grandparent, worker, widowed",
     ("none", "parent", "spouse", "retiree", "single", "adultchild", "grandparent", "worker", "widowed")),
    ("cam", "core emotion trigger: fear (of loss/decline/danger), curiosity, reassure (relief/comfort), pride "
            "(flattery/self-worth), envy, shame (embarrassment/guilt), nostalgia, anger (indignation), hope, sadness",
     ("fear", "curiosity", "reassure", "pride", "envy", "shame", "nostalgia", "anger", "hope", "sadness")),
    ("cuoc", "stakes level 0-3: 0 trivial, 1 everyday, 2 serious (health/money/relationships), 3 life-changing/death",
     ("0", "1", "2", "3")),
    ("cuthe", "most salient concrete element: none, number (a count/age/percent), money (a sum/pension/savings), "
              "object (a concrete thing/food/habit/place), time (a concrete duration/date)",
     ("none", "number", "money", "object", "time")),
    ("nguoc", "contrarian or surprising claim (goes against common belief): y / n", ("y", "n")),
    ("uytin", "authority cue: none, doctor (doctor/neurologist/psychiatrist), research (study/science/brain science), "
              "buddhism (Buddha/monk/religion), statistic (data/survey), expert (other specialist), famous "
              "(celebrity/historical figure), elder (wisdom of old people)",
     ("none", "doctor", "research", "buddhism", "statistic", "expert", "famous", "elder")),
    ("hoi", "phrased as a question: y / n", ("y", "n")),
    ("sac", "overall valence of the framing: neg, neu, pos", ("neg", "neu", "pos")),
    ("khung", "time frame: none, afterage (after age X / from now on), oldage (in old age), endlife (last years/death), "
              "now (today/immediately), future (later/someday), past (youth/memories)",
     ("none", "afterage", "oldage", "endlife", "now", "future", "past")),
    ("ban", "addresses the viewer directly (you / your / imperative): y / n", ("y", "n")),
    ("bian", "mystery gap — withholds the key answer so you must click: y / n", ("y", "n")),
    ("hanh", "call to action: do (start/do X), stop (stop/avoid X), none", ("do", "stop", "none")),
    ("tam", "focus: self (viewer's own life/mind), others (judging other people), family (family/marriage/children), "
            "society (society/the world)",
     ("self", "others", "family", "society")),
    ("linhvuc", "domain: brain (brain/dementia/memory/cognition), mind (psychology/personality/emotions), health "
                "(body/illness/longevity), money, relation (friends/people/relationships), lifestyle (habits/home/"
                "daily life), death, spirit (luck/fortune/religion/karma), work, other",
     ("brain", "mind", "health", "money", "relation", "lifestyle", "death", "spirit", "work", "other")),
)
TEN_TRUONG = tuple(t[0] for t in TRUONG)
GIA_TRI = {t[0]: frozenset(t[2]) for t in TRUONG}
#: Trường thứ tự (đặc trưng số ngoài one-hot): mã → số.
THU_TU = {"cuoc": {"0": 0.0, "1": 1.0, "2": 2.0, "3": 3.0}, "sac": {"neg": -1.0, "neu": 0.0, "pos": 1.0}}
#: Một tiêu đề hợp lệ khi đọc được ít nhất ngần này trường (trường hỏng → None).
TRUONG_TOI_THIEU = len(TRUONG) - 2
TU_CHU_DE_TOI_DA = 6


# ── tiện ích ────────────────────────────────────────────────────────────────


def chuan(t: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(t or "")).split())


def bam(t: Any) -> str:
    return hashlib.sha1(chuan(t).encode("utf-8")).hexdigest()


def thu_muc(goc: str) -> str:
    return os.path.join(goc, *THU_MUC)


def duong_nho(goc: str) -> str:
    return os.path.join(thu_muc(goc), TEP_NHO)


def duong_chi(goc: str) -> str:
    return os.path.join(thu_muc(goc), TEP_CHI)


_KHOA_GHI = threading.Lock()


def _noi_dong(p: str, dong: Iterable[Dict[str, Any]]) -> None:
    chu = "".join(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n" for d in dong)
    if not chu:
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with _KHOA_GHI:
        with io.open(p, "a", encoding="utf-8") as tep:
            tep.write(chu)


_DEM: Dict[str, Tuple[float, int, Dict[str, Dict[str, Any]]]] = {}


def doc_nho(goc: str) -> Dict[str, Dict[str, Any]]:
    """`{sha1: {"n": {trường: mã|None}, "c": chủ đề}}` — bản cùng `PHIEN_BAN`; dòng sau ghi đè dòng trước. Nhớ đệm theo
    (thời điểm sửa, cỡ tệp)."""
    p = duong_nho(goc)
    try:
        st = os.stat(p)
    except OSError:
        return {}
    cu = _DEM.get(p)
    if cu and cu[0] == st.st_mtime and cu[1] == st.st_size:
        return cu[2]
    ra: Dict[str, Dict[str, Any]] = {}
    try:
        with io.open(p, encoding="utf-8", errors="replace") as tep:
            for d in tep:
                try:
                    x = json.loads(d)
                except ValueError:
                    continue
                if isinstance(x, dict) and x.get("v") == PHIEN_BAN and x.get("h") and isinstance(x.get("n"), dict):
                    ra[str(x["h"])] = {"n": x["n"], "c": str(x.get("c") or "")}
    except OSError:
        return {}
    _DEM[p] = (st.st_mtime, st.st_size, ra)
    return ra


def tra(goc: str, tieu_de: str, nho: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Nhãn của MỘT tiêu đề (chưa gắn → None)."""
    return (doc_nho(goc) if nho is None else nho).get(bam(tieu_de))


# ── đề bài + đọc trả lời ────────────────────────────────────────────────────


def _ngach() -> str:
    try:
        from core import chien_truong  # noqa: PLC0415
        n = chien_truong.mo_ta_ngach()
        if n.get("ten") and n["ten"] != "Ngách":
            return "the YouTube niche \"{0}\"{1}".format(
                n["ten"], " (market language: {0})".format(n["ngon_ngu"]) if n.get("ngon_ngu") else "")
    except Exception:  # noqa: BLE001
        pass
    return "a YouTube niche for older adults (aging, psychology, brain science)"


def de_bai(tieu_de: Sequence[str], ngach: str = "") -> str:
    luoc = "\n".join("{0}. {1} = {2}".format(i + 1, t[0], t[1]) for i, t in enumerate(TRUONG))
    ds = "\n".join("{0}. {1}".format(i + 1, chuan(t)) for i, t in enumerate(tieu_de))
    vd = "|".join(t[2][0] for t in TRUONG) + "|brain aging habits"
    return ("You are a careful annotator of YouTube video TITLES from " + (ngach or _ngach()) + ". Read each title for "
            "its MEANING (what it promises, to whom, which emotion it pulls), not for keywords.\n\n"
            "For every title output exactly " + str(len(TRUONG)) + " codes in this fixed order, then a short TOPIC:\n"
            + luoc + "\n" + str(len(TRUONG) + 1) + ". topic = what the video is about, normalized, in English, 2-"
            + str(TU_CHU_DE_TOI_DA) + " lowercase words, no punctuation (e.g. 'dementia early signs', "
            "'lonely old age', 'toxic family members')\n\n"
            "Use ONLY the listed codes (lowercase). Join the " + str(len(TRUONG) + 1) + " parts with '|'. Example of "
            "one value: \"" + vd + "\"\n\n"
            "Titles:\n" + ds + "\n\n"
            "Reply ONLY with one JSON object mapping the title number to its value, for ALL " + str(len(tieu_de))
            + " titles: {\"1\": \"…\", \"2\": \"…\"}")


def doc_mot(chu: Any) -> Optional[Dict[str, Any]]:
    """"mã|mã|…|chủ đề" → `{"n": {trường: mã|None}, "c": chủ đề}`; quá ít trường đọc được → None."""
    if not isinstance(chu, str):
        return None
    p = [a.strip() for a in chu.split("|")]
    if len(p) < len(TRUONG):
        return None
    n: Dict[str, Optional[str]] = {}
    tot = 0
    for i, (ma, _mt, _gt) in enumerate(TRUONG):
        v = p[i].lower().strip().strip("'\"")
        if ma in ("nguoc", "hoi", "ban", "bian") and v in ("yes", "no"):
            v = v[0]
        if v in GIA_TRI[ma]:
            n[ma] = v
            tot += 1
        else:
            n[ma] = None
    if tot < TRUONG_TOI_THIEU:
        return None
    cd = " ".join("|".join(p[len(TRUONG):]).replace("|", " ").lower().split()[:TU_CHU_DE_TOI_DA])
    return {"n": n, "c": cd}


def doc_tra_loi(chu: str, so: int) -> Dict[int, Dict[str, Any]]:
    """Trả lời của một lô → `{chỉ số 0..so−1: nhãn}` (chỉ các tiêu đề đọc được). JSON hỏng → {}."""
    from core.goi_van_ban import loc_json  # noqa: PLC0415
    try:
        du = loc_json(chu)
    except Exception:  # noqa: BLE001
        return {}
    if isinstance(du, list):
        du = {str(i + 1): v for i, v in enumerate(du)}
    if not isinstance(du, dict):
        return {}
    ra: Dict[int, Dict[str, Any]] = {}
    for k, v in du.items():
        try:
            i = int(str(k).strip().rstrip(".")) - 1
        except ValueError:
            continue
        if 0 <= i < so:
            x = doc_mot(v)
            if x is not None:
                ra[i] = x
    return ra


# ── gọi ví ──────────────────────────────────────────────────────────────────


def khoa_lo(tieu_de: Sequence[str], hau_to: str = "") -> str:
    h = hashlib.sha1(("nhan-nghia:v{0}:".format(PHIEN_BAN) + "\n".join(chuan(t) for t in tieu_de)).encode("utf-8"))
    return "nhan-nghia-" + h.hexdigest()[:32] + hau_to


def ham_goi_vi(goc: str, ghi: Callable[[str], None] = lambda *_a: None) -> Optional[Callable[..., str]]:
    """Hàm gọi LLM qua VÍ ShopAPI (`qua_vi=True` — không bao giờ thuê bao Claude Max). Van ví chặn / chưa đăng nhập
    → None. Hàm trả về nhận (đề bài, khoá, so_dung)."""
    try:
        from core.giam_doc.quan_ly import vi_cho_phep  # noqa: PLC0415
        ly = vi_cho_phep(goc)
    except Exception:  # noqa: BLE001
        ly = ""
    if ly:
        ghi("  [nhãn nghĩa] không gọi AI: " + ly)
        return None
    try:
        from core.api import build_client  # noqa: PLC0415
        from core.config import CONFIG_FILENAME, load_config  # noqa: PLC0415
        ch = load_config(os.path.join(goc, CONFIG_FILENAME))
        if ch.problem:
            ghi("  [nhãn nghĩa] tool chưa đăng nhập được: " + str(ch.problem))
            return None
        client = build_client(ch)
    except Exception as loi:  # noqa: BLE001
        ghi("  [nhãn nghĩa] không dựng được client: " + str(loi)[:120])
        return None

    def goi(de: str, khoa: str, so_dung: Dict[str, Any]) -> str:
        from core.goi_van_ban import goi_van_ban, tin_nhan_viet  # noqa: PLC0415
        return goi_van_ban(client, tin_nhan_viet(de), toi_da_token=TOI_DA_TOKEN, khoa=khoa, qua_vi=True, goc=goc,
                           so_dung=so_dung)
    return goi


def tien_micro(so_dung: Dict[str, Any]) -> int:
    return int(so_dung.get("token_vao") or 0) * GIA_VAO_MICRO + int(so_dung.get("token_ra") or 0) * GIA_RA_MICRO


def gan_lo(goi: Callable[..., str], tieu_de: Sequence[str], ngach: str = "") -> Tuple[Dict[int, Dict[str, Any]],
                                                                                   Dict[str, Any]]:
    """Một lô: gọi → đọc; tiêu đề hỏng/thiếu → MỘT lượt sửa với đúng các tiêu đề ấy. Trả (nhãn theo chỉ số, sổ dùng)."""
    so_dung: Dict[str, Any] = {}
    ra: Dict[int, Dict[str, Any]] = {}
    try:
        ra = doc_tra_loi(goi(de_bai(tieu_de, ngach), khoa_lo(tieu_de), so_dung), len(tieu_de))
    except Exception as loi:  # noqa: BLE001
        so_dung["loi"] = str(loi)[:200]
    thieu = [i for i in range(len(tieu_de)) if i not in ra]
    if thieu and "loi" not in so_dung:          # gọi hỏng hẳn (mạng/ví) → không sửa; lần sau hỏi lại
        con = [tieu_de[i] for i in thieu]
        try:
            sua = doc_tra_loi(goi(de_bai(con, ngach) + "\n\nIMPORTANT: answer EVERY title, exactly "
                                  + str(len(TRUONG) + 1) + " '|'-separated parts each, valid JSON only.",
                                  khoa_lo(con, ":sua"), so_dung), len(con))
            for j, x in sua.items():
                ra[thieu[j]] = x
            so_dung["sua"] = len(con)
        except Exception as loi:  # noqa: BLE001
            so_dung["loi_sua"] = str(loi)[:200]
    return ra, so_dung


def _dang_tai_len(goc: str) -> bool:
    try:
        from core import khe  # noqa: PLC0415
        return bool(khe.co_cho_tai_len(goc))
    except Exception:  # noqa: BLE001
        return False


def gan(goc: str, tieu_de: Sequence[str], *, goi: Optional[Callable[..., str]] = None, lo: int = LO,
        so_luong: int = SO_LUONG, tran_vnd: float = TRAN_CHI_VND, toi_da: int = 0, nguon: str = "gan",
        in_ra: Callable[[str], None] = print, ngu: Callable[[float], None] = time.sleep) -> Dict[str, Any]:
    """Gắn nhãn các tiêu đề CHƯA có trong nhớ đệm (bỏ trùng). Ghi nối thêm sau MỖI lô (dừng giữa chừng không mất).
    Ước tổng (tiền thật mỗi tiêu đề × số còn lại) > `tran_vnd` → dừng, `dung_vi_tran`."""
    nho = doc_nho(goc)
    thay, can = set(), []
    for t in tieu_de:
        c = chuan(t)
        h = bam(c)
        if c and h not in nho and h not in thay:
            thay.add(h)
            can.append(c)
    random.Random(len(can)).shuffle(can)     # dừng giữa chừng vẫn là mẫu rải đều mọi kênh/thời gian
    if toi_da > 0:
        can = can[:toi_da]
    bc: Dict[str, Any] = {"can": len(can), "da": 0, "hong": 0, "luot": 0, "token_vao": 0, "token_ra": 0,
                          "micro": 0, "lo": 0}
    if not can:
        return bc
    if goi is None:
        goi = ham_goi_vi(goc, in_ra)
        if goi is None:
            bc["loi"] = "ví không cho gọi / chưa đăng nhập"
            return bc
    ngach = _ngach()
    cac_lo = [can[i:i + lo] for i in range(0, len(can), lo)]
    khoa = threading.Lock()
    dung = threading.Event()
    t0 = time.time()

    def mot(ds: List[str]) -> None:
        if dung.is_set():
            return
        while _dang_tai_len(goc) and not dung.is_set():
            ngu(30.0)
        try:
            from core.giam_doc.quan_ly import vi_cho_phep  # noqa: PLC0415
            if vi_cho_phep(goc):
                dung.set()
                bc["loi"] = "van ví chặn giữa chừng"
                return
        except Exception:  # noqa: BLE001
            pass
        nhan, sd = gan_lo(goi, ds, ngach)
        luc = time.strftime("%Y-%m-%d %H:%M:%S")
        _noi_dong(duong_nho(goc), ({"h": bam(ds[i]), "v": PHIEN_BAN, "n": x["n"], "c": x["c"], "luc": luc}
                                   for i, x in sorted(nhan.items())))
        tien = tien_micro(sd)
        _noi_dong(duong_chi(goc), [{"luc": luc, "nguon": nguon, "n": len(ds), "dat": len(nhan),
                                    "token_vao": int(sd.get("token_vao") or 0), "token_ra": int(sd.get("token_ra") or 0),
                                    "luot": int(sd.get("luot") or 0), "micro": tien,
                                    **({"loi": sd["loi"]} if sd.get("loi") else {})}])
        with khoa:
            bc["lo"] += 1
            bc["da"] += len(nhan)
            bc["hong"] += len(ds) - len(nhan)
            for k in ("token_vao", "token_ra", "luot"):
                bc[k] += int(sd.get(k) or 0)
            bc["micro"] += tien
            xong = bc["da"] + bc["hong"]
            uoc = bc["micro"] / 1e6 / max(1, xong) * len(can)
            bc["uoc_tong_vnd"] = round(uoc)
            if bc["lo"] >= 3 and uoc > tran_vnd:
                dung.set()
                bc["dung_vi_tran"] = True
            if bc["lo"] == 1 or bc["lo"] % 20 == 0 or dung.is_set():
                in_ra("  nhãn nghĩa: lô {0}/{1} · đạt {2} hỏng {3} · token vào {4} ra {5} · ~{6:,.0f}đ (ước tổng {7:,.0f}đ)"
                      " · {8:.0f}s".format(bc["lo"], len(cac_lo), bc["da"], bc["hong"], bc["token_vao"], bc["token_ra"],
                                           bc["micro"] / 1e6, uoc, time.time() - t0))
            if bc["lo"] >= 3 and bc["da"] == 0:
                dung.set()
                bc["loi"] = "3 lô liền không đọc được nhãn nào"

    with ThreadPoolExecutor(max_workers=max(1, int(so_luong))) as ex:
        list(ex.map(mot, cac_lo))
    bc["vnd"] = round(bc["micro"] / 1e6, 1)
    bc["giay"] = round(time.time() - t0, 1)
    return bc


# ── nguồn tiêu đề ───────────────────────────────────────────────────────────


def tieu_de_ta(goc: str) -> List[str]:
    """Tiêu đề video của ta (bảng Studio) + tiêu đề trong hồ sơ video + MỌI ứng viên tiêu đề đã chấm của gói."""
    ra: List[str] = []
    try:
        import csv  # noqa: PLC0415
        from core import hieu_chuan as hc  # noqa: PLC0415
        for k in hc.kenh_hoc(goc):
            p = os.path.join(goc, "CHANNEL", k, "chi-so", "bang-tom-tat.csv")
            try:
                with io.open(p, encoding="utf-8-sig") as tep:
                    ra += [str(d.get("Tiêu đề") or "") for d in csv.DictReader(tep)]
            except OSError:
                pass
            for hs in hc.ho_so_kenh(goc, k).values():
                ra.append(str(hs.get("tieu_de") or ""))
                tc = hs.get("tieu_de_cham") if isinstance(hs.get("tieu_de_cham"), dict) else {}
                ra += [str(u.get("tieu_de") or "") for u in tc.get("ung_vien") or [] if isinstance(u, dict)]
    except Exception:  # noqa: BLE001
        pass
    return [t for t in ra if t.strip()]


def tieu_de_doi_thu(goc: str) -> List[str]:
    try:
        from core import gia_tri  # noqa: PLC0415
        return [x["tieu_de"] for x in gia_tri.doc_video(goc)]
    except Exception:  # noqa: BLE001
        return []


def bat(goc: str) -> bool:
    try:
        with io.open(os.path.join(goc, "workspace", "cai-dat.json"), encoding="utf-8") as tep:
            cai = json.load(tep)
    except (OSError, ValueError):
        return True
    return not (isinstance(cai, dict) and cai.get(KHOA_CAI) is False)


def chua_gan(goc: str) -> Tuple[int, int]:
    """(số tiêu đề của ta chưa gắn, số tiêu đề đối thủ chưa gắn) — không gọi mạng."""
    nho = doc_nho(goc)
    ta = {bam(t) for t in tieu_de_ta(goc)} - set(nho)
    dt = {bam(t) for t in tieu_de_doi_thu(goc)} - set(nho)
    return len(ta), len(dt - ta)


def chay(goc: str, *, toi_da: int = 0, so_luong: int = SO_LUONG, in_ra: Callable[[str], None] = print
         ) -> Dict[str, Any]:
    """Gắn nhãn mọi tiêu đề chưa có: của ta (ưu tiên — ít, cần cho kiểm chuyển giao) rồi đối thủ."""
    ta = gan(goc, tieu_de_ta(goc), toi_da=toi_da, so_luong=so_luong, nguon="ta", in_ra=in_ra)
    if ta.get("loi") or ta.get("dung_vi_tran"):
        return {"ta": ta}
    con = max(0, toi_da - ta["can"]) if toi_da > 0 else 0
    if toi_da > 0 and con == 0:
        return {"ta": ta}
    dt = gan(goc, tieu_de_doi_thu(goc), toi_da=con, so_luong=so_luong, nguon="doi-thu", in_ra=in_ra)
    return {"ta": ta, "doi_thu": dt}


def tong_chi(goc: str) -> Dict[str, Any]:
    ra = {"lo": 0, "tieu_de": 0, "dat": 0, "token_vao": 0, "token_ra": 0, "micro": 0}
    try:
        with io.open(duong_chi(goc), encoding="utf-8") as tep:
            for d in tep:
                try:
                    x = json.loads(d)
                except ValueError:
                    continue
                ra["lo"] += 1
                ra["tieu_de"] += int(x.get("n") or 0)
                ra["dat"] += int(x.get("dat") or 0)
                for k in ("token_vao", "token_ra", "micro"):
                    ra[k] += int(x.get(k) or 0)
    except OSError:
        pass
    ra["vnd"] = round(ra["micro"] / 1e6, 1)
    return ra


def can_chay(goc: str) -> Tuple[bool, str]:
    """Kỹ năng hằng ngày: cài đặt bật, van ví mở, còn tiêu đề chưa gắn."""
    if not bat(goc):
        return False, "cài đặt {0} tắt".format(KHOA_CAI)
    try:
        from core.giam_doc.quan_ly import vi_cho_phep  # noqa: PLC0415
        ly = vi_cho_phep(goc)
        if ly:
            return False, "van ví chặn: " + ly
    except Exception:  # noqa: BLE001
        pass
    nho = doc_nho(goc)
    ta = len({bam(t) for t in tieu_de_ta(goc)} - set(nho))
    if ta:
        return True, "{0} tiêu đề của ta chưa có nhãn".format(ta)
    try:
        import glob  # noqa: PLC0415
        moi = max((os.path.getmtime(p) for p in glob.glob(os.path.join(goc, "CHANNEL", "_NHOM", "*", "nghien-cuu",
                                                                           "kenh-do.json"))
                   + glob.glob(os.path.join(goc, "CHANNEL", "*", "nghien-cuu", "content.csv"))), default=0.0)
        if moi > os.path.getmtime(duong_nho(goc)):
            return True, "dữ liệu đối thủ mới hơn lượt gắn nhãn trước"
    except OSError:
        return True, "chưa gắn nhãn lần nào"
    return False, "mọi tiêu đề đã có nhãn"


# ── tín hiệu thị trường: nhãn nào kéo / đẩy xác suất nổ (báo cáo + khối lời nhắc tiêu đề) ──────────────────────

TEP_TIN_HIEU = "tin-hieu-thi-truong.json"
TEP_BAO_CAO = "bao-cao-nhan.md"
#: Khoá cài đặt: chèn khối «tín hiệu thị trường» vào lời nhắc VIẾT tiêu đề (mặc định BẬT; chỉ là gợi ý, không đổi chọn).
KHOA_KHOI = "tin_hieu_thi_truong_tieu_de"
N_HO_TRO_MIN = 300
NGAY_KHOI_TOI_DA = 30

TEN_VI = {
    "hua": "kiểu hứa hẹn", "tuoi": "tuổi nhắm tới", "gioi": "giới", "vai": "vai/tệp", "cam": "cảm xúc kích hoạt",
    "cuoc": "độ cược", "cuthe": "chi tiết cụ thể", "nguoc": "ngược đời/bất ngờ", "uytin": "dấu uy tín",
    "hoi": "dạng câu hỏi", "sac": "sắc thái", "khung": "khung thời gian", "ban": "gọi thẳng người xem",
    "bian": "giấu đáp án (khoảng trống tò mò)", "hanh": "kêu gọi hành động", "tam": "tâm điểm", "linhvuc": "lĩnh vực",
}
MA_VI = {
    "secret": "bí mật", "reason": "lý do", "howto": "cách làm", "list": "danh sách", "warning": "cảnh báo",
    "compare": "so sánh", "story": "câu chuyện", "traits": "đặc điểm người", "fact": "kiến thức", "other": "khác",
    "none": "không", "senior": "người già nói chung", "any": "chung", "male": "nam", "female": "nữ",
    "parent": "cha mẹ", "spouse": "vợ chồng", "retiree": "người nghỉ hưu", "single": "sống một mình",
    "adultchild": "con của cha mẹ già", "grandparent": "ông bà", "worker": "người đi làm", "widowed": "góa",
    "fear": "sợ mất/suy", "curiosity": "tò mò", "reassure": "an lòng", "pride": "tự hào", "envy": "ghen tị",
    "shame": "xấu hổ", "nostalgia": "hoài niệm", "anger": "bất bình", "hope": "hy vọng", "sadness": "buồn",
    "number": "con số", "money": "tiền", "object": "vật/thói quen cụ thể", "time": "thời lượng/ngày cụ thể",
    "y": "có", "n": "không", "doctor": "bác sĩ", "research": "nghiên cứu", "buddhism": "Phật/nhà sư",
    "statistic": "thống kê", "expert": "chuyên gia", "famous": "người nổi tiếng", "elder": "lời người già",
    "neg": "tiêu cực", "neu": "trung tính", "pos": "tích cực", "afterage": "sau tuổi X", "oldage": "tuổi già",
    "endlife": "cuối đời", "now": "ngay bây giờ", "future": "sau này", "past": "quá khứ", "do": "hãy làm",
    "stop": "đừng/bỏ", "self": "bản thân", "others": "người khác", "family": "gia đình", "society": "xã hội",
    "brain": "não/trí nhớ", "mind": "tâm lý/tính cách", "health": "sức khoẻ", "relation": "quan hệ",
    "lifestyle": "lối sống", "death": "cái chết", "spirit": "vận may/tâm linh", "work": "công việc",
    "0": "0 (vặt)", "1": "1 (thường ngày)", "2": "2 (nghiêm trọng)", "3": "3 (đổi đời/sống chết)",
}


def nhan_vi(khoa: str) -> str:
    """"hua=secret" → "kiểu hứa hẹn: bí mật"."""
    f, _s, v = khoa.partition("=")
    return "{0}: {1}".format(TEN_VI.get(f, f), MA_VI.get(v, v))


def phan_tich(ds: Sequence[Dict[str, Any]], *, nguong: float = math.log(3.0), n_min: int = N_HO_TRO_MIN,
              lam: float = 10.0) -> Dict[str, Any]:
    """Hiệu ứng từng nhãn lên xác suất NỔ (y_no ≥ log 3) trên video đối thủ có nhãn (`x["nghia"]`, `x["y_no"]`,
    `x["dang"]`, [`x["vung"]`]):
      biên  = tỉ lệ nổ khi có nhãn ÷ tỉ lệ nền (lift), hiệu y_no trung bình;
      điều chỉnh = hệ số hồi quy tuyến tính (ridge) của chỉ báo nổ trên MỌI nhãn + vùng — điểm phần trăm khi các nhãn
                   khác giữ nguyên; tính riêng trên nửa cũ và nửa mới theo ngày đăng → «ổn định» khi cùng dấu.
    Chỉ nhãn có ≥ `n_min` video. Chủ đề: từ (tiếng Anh) ≥ `n_min`÷2 video, chỉ biên."""
    import numpy as np  # noqa: PLC0415
    co = [x for x in ds if isinstance(x.get("nghia"), dict) and x.get("y_no") is not None]
    if len(co) < 200:
        return {"n": len(co)}
    y = np.array([float(x["y_no"]) for x in co])
    no = (y >= nguong).astype(np.float64)
    nen = float(no.mean())
    dem: Dict[str, int] = {}
    for x in co:
        for f, v in (x["nghia"].get("n") or {}).items():
            if v and f in GIA_TRI:
                dem[f + "=" + v] = dem.get(f + "=" + v, 0) + 1
    # Mã hoá theo MỐC: mỗi trường bỏ giá trị phổ biến nhất — không thì cả bộ giá trị một trường thẳng hàng với hằng số,
    # hệ số không xác định (đo 21/10: «gọi thẳng: có» và «: không» cùng +3,7 điểm %). Hiệu ứng = so với mốc của trường.
    moc_truong: Dict[str, str] = {}
    for k, _c in sorted(dem.items(), key=lambda kv: -kv[1]):
        moc_truong.setdefault(k.split("=", 1)[0], k)
    cot = sorted(k for k, c in dem.items() if c >= n_min and moc_truong.get(k.split("=", 1)[0]) != k)
    vung = sorted({str(x.get("vung")) for x in co if x.get("vung")})
    vung = [v for v in vung if sum(1 for x in co if x.get("vung") == v) >= n_min]
    chi = {k: i for i, k in enumerate(cot)}
    chi_v = {v: len(cot) + i for i, v in enumerate(vung)}
    X = np.zeros((len(co), len(cot) + len(vung)), dtype=np.float64)
    for i, x in enumerate(co):
        for f, v in (x["nghia"].get("n") or {}).items():
            j = chi.get("{0}={1}".format(f, v))
            if j is not None:
                X[i, j] = 1.0
        j = chi_v.get(str(x.get("vung")))
        if j is not None:
            X[i, j] = 1.0
    dang = np.array([x["dang"].toordinal() if hasattr(x.get("dang"), "toordinal") else 0 for x in co])
    giua = np.median(dang)

    def he_so(m: Any) -> Any:
        A = X[m]
        tb = A.mean(axis=0)
        A = A - tb
        b = no[m] - no[m].mean()
        return np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ b)

    w_all = he_so(np.ones(len(co), dtype=bool))
    w_cu, w_moi = he_so(dang < giua), he_so(dang >= giua)
    ra = []
    for k in cot:
        j = chi[k]
        m = X[:, j] > 0
        p = float(no[m].mean())
        ra.append({"khoa": k, "n": int(m.sum()), "ti_le": round(p, 4), "lift": round(p / nen, 2) if nen else None,
                   "y_tb": round(float(y[m].mean() - y.mean()), 3), "dieu_chinh_pp": round(float(w_all[j]) * 100, 2),
                   "cu_pp": round(float(w_cu[j]) * 100, 2), "moi_pp": round(float(w_moi[j]) * 100, 2),
                   "on_dinh": bool(np.sign(w_cu[j]) == np.sign(w_moi[j])),
                   "so_voi": moc_truong.get(k.split("=", 1)[0], "")})
    ra.sort(key=lambda r: -r["dieu_chinh_pp"])
    dem_cd: Dict[str, List[int]] = {}
    for i, x in enumerate(co):
        for t in set(str(x["nghia"].get("c") or "").split()):
            if len(t) >= 3:
                dem_cd.setdefault(t, []).append(i)
    cd = []
    for t, idx in dem_cd.items():
        if len(idx) >= max(50, n_min // 2):
            p = float(no[idx].mean())
            cd.append({"tu": t, "n": len(idx), "ti_le": round(p, 4), "lift": round(p / nen, 2) if nen else None})
    cd.sort(key=lambda r: -(r["lift"] or 0))
    return {"n": len(co), "nen": round(nen, 4), "nhan": ra, "chu_de": cd, "n_vung_kiem_soat": len(vung)}


def _ten_moc(r: Dict[str, Any]) -> str:
    v = str(r.get("so_voi") or "").partition("=")[2]
    return MA_VI.get(v, v or "mốc")


def bao_cao(goc: str, pt: Dict[str, Any], *, top: int = 10, luc: str = "") -> str:
    """Báo cáo ngắn (tiếng Việt) `workspace/gia-tri/bao-cao-nhan.md` + dữ liệu khối lời nhắc `tin-hieu-thi-truong.json`."""
    luc = luc or time.strftime("%Y-%m-%d %H:%M")
    nh = pt.get("nhan") or []
    duong = [r for r in nh if r["dieu_chinh_pp"] > 0][:top]
    am = sorted([r for r in nh if r["dieu_chinh_pp"] < 0], key=lambda r: r["dieu_chinh_pp"])[:top]

    def dong(r: Dict[str, Any]) -> str:
        return "| {0} | {1} | {2:+.1f} | ×{3} | {4:,} | {5:+.1f} / {6:+.1f}{7} |".format(
            nhan_vi(r["khoa"]), _ten_moc(r), r["dieu_chinh_pp"], r["lift"], r["n"], r["cu_pp"], r["moi_pp"],
            "" if r["on_dinh"] else " (lật dấu)")

    dau = ("| Nhãn | So với mốc | Điều chỉnh (điểm %) | Lift biên | n | Nửa cũ / nửa mới |\n"
           "|---|---|---|---|---|---|")
    cd = pt.get("chu_de") or []
    chu = ["# Nhãn nghĩa tiêu đề → xác suất nổ ({0})".format(luc), "",
           "{0:,} video đối thủ có nhãn; tỉ lệ nổ nền (≥ 3× trung vị chính kênh cùng tuổi) {1:.1%}. «Điều chỉnh» = "
           "điểm phần trăm xác suất nổ khi có nhãn, các nhãn khác và vùng đề tài ({2} vùng) giữ nguyên (hồi quy "
           "tuyến tính ridge). «Lift biên» = tỉ lệ nổ khi có nhãn ÷ nền, chưa điều chỉnh. Chỉ nhãn ≥ {3} video. Là "
           "TƯƠNG QUAN trên dữ liệu đối thủ, không phải nhân quả.".format(
               pt.get("n", 0), pt.get("nen") or 0, pt.get("n_vung_kiem_soat", 0), N_HO_TRO_MIN), "",
           "## Kéo xác suất nổ LÊN", "", dau] + [dong(r) for r in duong] + [
           "", "## Kéo xác suất nổ XUỐNG", "", dau] + [dong(r) for r in am] + [
           "", "## Từ chủ đề (biên, ≥ {0} video)".format(max(50, N_HO_TRO_MIN // 2)), "",
           "Cao nhất: " + ", ".join("{0} ×{1} (n {2})".format(r["tu"], r["lift"], r["n"]) for r in cd[:top]), "",
           "Thấp nhất: " + ", ".join("{0} ×{1} (n {2})".format(r["tu"], r["lift"], r["n"]) for r in cd[-top:][::-1]), ""]
    md = "\n".join(chu)
    os.makedirs(thu_muc(goc), exist_ok=True)
    with io.open(os.path.join(thu_muc(goc), TEP_BAO_CAO), "w", encoding="utf-8") as tep:
        tep.write(md)
    du = {"luc": luc, "n": pt.get("n"), "nen": pt.get("nen"),
          "len": [r for r in duong if r["on_dinh"]][:6], "xuong": [r for r in am if r["on_dinh"]][:6]}
    p = os.path.join(thu_muc(goc), TEP_TIN_HIEU)
    with io.open(p + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
    return md


def khoi_tin_hieu(goc: str) -> str:
    """Khối «TÍN HIỆU THỊ TRƯỜNG» cho lời nhắc VIẾT tiêu đề — gợi ý, không đổi cách chọn. Cài đặt `KHOA_KHOI` tắt /
    chưa có dữ liệu / dữ liệu > `NGAY_KHOI_TOI_DA` ngày → "" (lời nhắc y hệt từng byte)."""
    try:
        with io.open(os.path.join(goc, "workspace", "cai-dat.json"), encoding="utf-8") as tep:
            cai = json.load(tep)
        if isinstance(cai, dict) and cai.get(KHOA_KHOI) is False:
            return ""
    except (OSError, ValueError):
        pass
    p = os.path.join(thu_muc(goc), TEP_TIN_HIEU)
    try:
        if time.time() - os.path.getmtime(p) > NGAY_KHOI_TOI_DA * 86400:
            return ""
        with io.open(p, encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return ""
    if not isinstance(du, dict) or not (du.get("len") or du.get("xuong")):
        return ""

    def ds(rs: Sequence[Dict[str, Any]]) -> str:
        return "; ".join("{0} ({1:+.1f} điểm % so với «{2}», n {3:,})".format(
            nhan_vi(r["khoa"]), r["dieu_chinh_pp"], _ten_moc(r), r["n"]) for r in rs)
    chu = ["TÍN HIỆU THỊ TRƯỜNG (học từ {0:,} video đối thủ cùng ngách: nhãn nghĩa tiêu đề ↔ xác suất video nổ gấp 3 "
           "trung vị kênh; nền {1:.0%}. Là tương quan, chỉ để GỢI Ý — chỉ dùng khi hợp với nội dung thật của video, "
           "không bịa chi tiết):".format(int(du.get("n") or 0), float(du.get("nen") or 0))]
    if du.get("len"):
        chu.append("- Hay đi cùng video nổ: " + ds(du["len"]))
    if du.get("xuong"):
        chu.append("- Hay đi cùng video chìm: " + ds(du["xuong"]))
    return "\n".join(chu)


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(prog="core.nhan_nghia", description=__doc__.split("\n")[0])
    ap.add_argument("lenh", choices=("gan", "thu", "chi", "bao-cao"))
    ap.add_argument("chu", nargs="*")
    ap.add_argument("--toi-da", type=int, default=0)
    ap.add_argument("--song-song", type=int, default=SO_LUONG, help="số lượt gọi song song (kẹp 1..6)")
    ap.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    if a.lenh == "chi":
        print(json.dumps(tong_chi(a.goc), ensure_ascii=False))
        return 0
    if a.lenh == "bao-cao":
        from core import gia_tri  # noqa: PLC0415
        ds, _tt = gia_tri.tap_hoc(a.goc, print)
        print(bao_cao(a.goc, phan_tich(ds)))
        return 0
    if a.lenh == "thu":
        goi = ham_goi_vi(a.goc, print)
        if goi is None:
            return 4
        nhan, sd = gan_lo(goi, a.chu)
        for i, t in enumerate(a.chu):
            print(t, "→", json.dumps(nhan.get(i), ensure_ascii=False))
        print(json.dumps(dict(sd, micro=tien_micro(sd)), ensure_ascii=False))
        return 0
    try:
        from core.gia_tri import _ha_uu_tien  # noqa: PLC0415
        _ha_uu_tien()
    except Exception:  # noqa: BLE001
        pass
    bc = chay(a.goc, toi_da=a.toi_da, so_luong=max(1, min(6, a.song_song)))
    print(json.dumps(bc, ensure_ascii=False))
    return 0 if not any((v or {}).get("loi") for v in bc.values()) else 30


if __name__ == "__main__":
    sys.exit(main())
