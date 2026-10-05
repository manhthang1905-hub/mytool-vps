"""AI CHIA VÙNG cho chiến trường (06/10/2026) — video đối thủ mà bộ cụm TỪ KHOÁ không nhận (rơi vào «Đề tài khác»,
~55% lượt xem ngách) được AI xếp vào vùng theo NGHĨA (nguyên tắc chủ dự án: phân loại theo nghĩa, không lọc từ khoá).

Mỗi tiêu đề → một vùng có sẵn của ngách, hoặc VÙNG MỚI do AI đặt (dùng lại nhất quán qua các lô). Nhớ đệm
`workspace/chien-truong/vung-ai.json` — mỗi video chỉ hỏi MỘT lần; chạy lại chỉ hỏi video mới.

    python -m core.chien_truong_ai [--toi-da 1500]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Dict, List

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP = os.path.join(GOC, "workspace", "chien-truong", "vung-ai.json")
LO = 60


def doc() -> Dict:
    try:
        with open(TEP, "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi(d: Dict) -> None:
    os.makedirs(os.path.dirname(TEP), exist_ok=True)
    with open(TEP + ".tam", "w", encoding="utf-8") as tep:
        json.dump(d, tep, ensure_ascii=False, indent=0)
    os.replace(TEP + ".tam", TEP)


def _de_bai(vung: Dict[str, str], lo: List[Dict]) -> str:
    ds_vung = "\n".join("- {0}: {1}".format(m, t) for m, t in vung.items())
    ds = "\n".join("{0}. {1}".format(i + 1, x["tieu_de"]) for i, x in enumerate(lo))
    return ("You classify Japanese YouTube video titles from a Japanese PSYCHOLOGY niche into TOPIC TERRITORIES, by "
            "MEANING (what the video is about for the viewer), not by keywords.\n\n"
            "Existing territories (id: Vietnamese name):\n" + ds_vung + "\n\n"
            "Rules:\n- Put each title in the ONE best existing territory when it truly fits.\n"
            "- If none fits, create a NEW territory id 'moi-<short-latin-slug>' with a short Vietnamese name (max 6 words) "
            "describing the psychological topic (e.g. 'moi-noi-doi' → 'Nói dối / lừa dối'). Reuse a new id for every "
            "title of the same topic. Prefer few broad territories over many tiny ones.\n"
            "- Titles that are not about psychology / human behaviour at all → 'ngoai-ngach'.\n\n"
            "Titles:\n" + ds + "\n\n"
            "Reply ONLY with JSON: {\"gan\": {\"1\": \"<id>\", \"2\": \"<id>\", ...}, \"moi\": {\"moi-xxx\": \"<Vietnamese name>\"}}")


def chay(toi_da: int = 1500, ghi_log=print) -> Dict:
    if GOC not in sys.path:
        sys.path.insert(0, GOC)
    from core import chien_truong  # noqa: PLC0415
    from core.giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415
    goi = goi_chat_that(GOC, ghi_log)
    if goi is None:
        return {"loi": "ví AI đang chặn"}
    nho = doc()
    nho.setdefault("video", {})
    nho.setdefault("vung_moi", {})
    ds = [x for x in chien_truong.video_khac() if x["link"] not in nho["video"]][:toi_da]
    ghi_log("AI chia vùng: {0} video «Đề tài khác» chưa gán (lấy nhiều lượt xem nhất trước)".format(len(ds)))
    vung = dict(chien_truong.ten_vung_tu_khoa())
    vung.pop(chien_truong.KHAC, None)
    da = 0
    for i in range(0, len(ds), LO):
        lo = ds[i:i + LO]
        vung_hien = dict(vung, **nho["vung_moi"])
        try:
            tra = goi(_de_bai(vung_hien, lo), mo_hinh="claude-sonnet-5", khoa="chien-truong-vung-{0}".format(
                abs(hash(tuple(x["link"] for x in lo))) % 10 ** 10), toi_da_token=4000)
            m = re.search(r"\{.*\}", tra or "", re.S)
            kq = json.loads(m.group(0)) if m else {}
        except Exception as loi:  # noqa: BLE001 — một lô hỏng thì lô sau vẫn chạy
            ghi_log("  lô {0}: lỗi {1}".format(i // LO + 1, str(loi)[:120]))
            continue
        for ma, ten in (kq.get("moi") or {}).items():
            if str(ma).startswith("moi-") and ten:
                nho["vung_moi"].setdefault(str(ma), str(ten)[:60])
        for so, ma in (kq.get("gan") or {}).items():
            try:
                x = lo[int(so) - 1]
            except (ValueError, IndexError):
                continue
            ma = str(ma)
            if ma in vung_hien or ma in nho["vung_moi"] or ma == "ngoai-ngach":
                nho["video"][x["link"]] = ma
                da += 1
        ghi(nho)
        ghi_log("  lô {0}/{1}: gán {2} · vùng mới {3}".format(i // LO + 1, (len(ds) + LO - 1) // LO, da, len(nho["vung_moi"])))
        time.sleep(0.5)
    return {"da_gan": da, "vung_moi": nho["vung_moi"]}


def gop(toi_da_vung: int = 12, ghi_log=print) -> Dict:
    """Gộp vùng MỚI vụn (AI đặt theo từng lô) thành ≤ `toi_da_vung` vùng lớn, hoặc nhập vào vùng có sẵn — một lượt AI
    nhìn TOÀN BỘ danh sách (tên + số video). Ghi lại map video theo vùng đã gộp."""
    if GOC not in sys.path:
        sys.path.insert(0, GOC)
    from core import chien_truong  # noqa: PLC0415
    from core.giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415
    nho = doc()
    moi = nho.get("vung_moi") or {}
    if not moi:
        return {"gop": 0}
    dem: Dict[str, int] = {}
    for ma in (nho.get("video") or {}).values():
        dem[ma] = dem.get(ma, 0) + 1
    co_san = dict(chien_truong.ten_vung_tu_khoa())
    co_san.pop(chien_truong.KHAC, None)
    de = ("Merge these fine-grained psychology TOPIC TERRITORIES (Japanese YouTube niche) into at most {0} BROAD new "
          "territories, or map them into an existing territory when it fits by meaning.\n\nExisting territories:\n{1}\n\n"
          "Fine territories to merge (id: Vietnamese name — number of videos):\n{2}\n\n"
          "Reply ONLY JSON: {{\"map\": {{\"<fine id>\": \"<existing id OR new broad id moi-<slug>>\"}}, "
          "\"moi\": {{\"moi-<slug>\": \"<Vietnamese name, max 5 words>\"}}}}").format(
        toi_da_vung, "\n".join("- {0}: {1}".format(m, t) for m, t in co_san.items()),
        "\n".join("- {0}: {1} — {2}".format(m, t, dem.get(m, 0)) for m, t in sorted(moi.items(), key=lambda x: -dem.get(x[0], 0))))
    goi = goi_chat_that(GOC, ghi_log)
    if goi is None:
        return {"loi": "ví AI đang chặn"}
    tra = goi(de, mo_hinh="claude-sonnet-5", khoa="chien-truong-gop-{0}".format(len(moi)), toi_da_token=6000)
    m = re.search(r"\{.*\}", tra or "", re.S)
    kq = json.loads(m.group(0)) if m else {}
    ban_do = {str(a): str(b) for a, b in (kq.get("map") or {}).items()}
    lon = {str(a): str(b)[:60] for a, b in (kq.get("moi") or {}).items() if str(a).startswith("moi-")}
    hop_le = set(co_san) | set(lon) | {"ngoai-ngach"}
    for lk, ma in list((nho.get("video") or {}).items()):
        if ma in moi:
            moi_ma = ban_do.get(ma)
            nho["video"][lk] = moi_ma if moi_ma in hop_le else ma
    con = {m2 for m2 in nho["video"].values() if m2.startswith("moi-")}
    nho["vung_moi"] = {m2: lon.get(m2) or moi.get(m2, m2) for m2 in con}
    nho["gop_luc"] = time.strftime("%Y-%m-%d %H:%M")
    ghi(nho)
    ghi_log("gộp: {0} vùng vụn → {1} vùng mới".format(len(moi), len(nho["vung_moi"])))
    return {"truoc": len(moi), "sau": len(nho["vung_moi"]), "vung_moi": nho["vung_moi"]}


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--gop" in a:
        print(json.dumps(gop(), ensure_ascii=False)[:3000])
    else:
        n = int(a[a.index("--toi-da") + 1]) if "--toi-da" in a else 1500
        print(json.dumps(chay(n), ensure_ascii=False)[:2000])
        print(json.dumps(gop(), ensure_ascii=False)[:3000])
