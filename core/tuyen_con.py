"""**Tệp khán giả → tuyến con** — nhận diện bằng từ khoá, không cần AI.

Chủ dự án, 06/09/2026: *"các tuyến mày đang phân không giống kiểu tao làm theo tệp khán giả… lúc trước
tao phân có 3: NGƯỜI SỐNG LỆCH NHỊP SỐ ĐÔNG · NGƯỜI BỊ ĐÁNH GIÁ THẤP HƠN NĂNG LỰC THẬT · NGƯỜI TÒ MÒ XEM
MÌNH LÀ KIỂU NGƯỜI NÀO… trong tệp lệch nhịp có các tuyến con: người thích ở một mình, người không dùng
mạng xã hội, người không thích thể thao…"*

Hai tầng:
  * **Tệp** (mã trong `nghien-cuu/tuyen.csv`, cột "Tuyến / Kênh" của sổ content) — AI + luật cứng gán.
  * **Chủ đề** (tuyến con, cột "Chủ đề") — nhận diện bằng từ khoá ở đây. Mỗi chủ đề thuộc đúng một
    tệp, nên nhận ra chủ đề là suy được tệp: dòng nào máy nhận ra thì điền cả hai (khi ô tệp trống),
    AI chỉ còn phải xem phần máy không nhận ra. Phân loại vì thế ổn định, lặp lại được, và đọc được
    lý do ("vì tiêu đề có SNS").

Thứ tự ưu tiên khi một tiêu đề dính nhiều nhóm: từ loại trừ (雑学…) → mốc tuổi (tệp trung niên) →
chủ đề của tệp lệch nhịp → cảnh giác → đánh giá thấp → tò mò. Đúng PHÂN XỬ trong tuyen.csv: "cùng nói
phòng bừa: xin được phép bừa → lệch nhịp; xin cách dọn / bừa vì tuổi → trung niên".

═══ TỆP LÀ VIỆC CỦA AI ĐỌC NGHĨA; REGEX CHỈ CÒN LÀ ĐƯỜNG LÙI (29/09/2026) ═══

Chủ dự án: *"Lọc theo từ khoá là SAI — phải theo Ý NGHĨA."* Trong chuỗi "một nút", bước 4a
(`dien_chu_de`) chạy TRƯỚC bước 4b (AI gán tuyến) và điền TỆP cho mọi dòng trống regex nhận ra —
mà 4b chỉ gán dòng còn trống, nên regex QUYẾT tệp cho gần hết dòng mới ("猫" → tò mò, "一人で" →
lệch nhịp) và AI không bao giờ được đọc chúng. Nay:

  * Kênh ĐANG dùng AI gán tuyến (kho `nhan-tuyen/<kênh>.json` có mục còn hạn) → dòng MỚI (≤
    `NGAY_DE_AI` ngày) còn trống thì regex KHÔNG điền tệp, để 4b đọc nghĩa. Regex chỉ điền tệp
    cho dòng cũ (AI không bao giờ xem) và cho dòng AI đã bỏ qua quá `NGAY_LUI` ngày kể từ lần đầu
    thấy (AI lỗi kéo dài — đường lùi, không để dòng trống mãi).
  * Cột "Chủ đề" (tuyến con) vẫn do regex điền — nó chỉ là chú thích, không quyết loại/giữ.
  * Kênh chưa từng dùng AI → y như cũ.

`tep_theo_nghia` cho nơi khác (vd `tu_chay.cong_diem_anh_em`) hỏi tệp theo NHÃN ĐÃ ĐỌC NGHĨA trong
sổ trước, regex sau.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .phan_tuyen import DAU_MOC_TUOI, MA_LECH_NHIP, MA_TRUNG_NIEN, _dinh_tu_loai_tru

__all__ = ["CHU_DE", "MA_THAP", "MA_TO_MO", "MA_CANH_GIAC", "nhan_dien", "dien_chu_de", "ten_chu_de",
           "regex_cua_tep", "tep_theo_nghia", "NGAY_DE_AI", "NGAY_LUI"]

#: Dòng đăng trong ngần này ngày là việc của AI gán tuyến (khớp `mot_nut.NGAY_AI`).
NGAY_DE_AI = 30
#: Dòng mới còn trống ngần này ngày kể từ "Lần đầu thấy" mà AI vẫn chưa gán (lỗi kéo dài) →
#: regex điền tệp làm đường lùi.
NGAY_LUI = 2

MA_THAP = "nguoi-bi-danh-gia-thap-hon-nang-luc-that"
MA_TO_MO = "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"
MA_CANH_GIAC = "nguoi-canh-giac-ke-doc-hai"

#: (mã chủ đề, tên hiện, regex tiếng Nhật) — theo thứ tự ưu tiên trong từng tệp.
CHU_DE: Dict[str, List[Tuple[str, str, "re.Pattern[str]"]]] = {
    MA_LECH_NHIP: [
        ("khong-sns", "không dùng mạng xã hội", re.compile("SNS|インスタ|投稿しない|投稿をしない|投稿もしない|既読")),
        ("khong-the-thao", "không hứng thú thể thao / trào lưu", re.compile(
            "スポーツ|ワールドカップ|野球に興味|流行に|ブランドに興味|熱狂できない|夢中になれない|興味がない人|興味が持てない|興味のない人")),
        ("o-nha", "thích ở nhà, không ra ngoài", re.compile(
            "家にいたい|家から出|外に出ない|出かけない|家が好き|家にいる|家を愛|休日に予定|予定を入れない|遠出")),
        ("it-ban", "ít bạn, giữ khoảng cách", re.compile(
            "友達が少な|友人が少な|友達がいな|人付き合い|人間関係から距離|疎遠|群れない|群れる|連絡を絶|縁を切|付き合わない|合わせない")),
        ("noi-mot-minh", "hay nói một mình", re.compile("独り言|ひとりごと")),
        ("dam-dong-met", "mệt khi ở đám đông", re.compile("人混み|飲み会|誰といても|大勢|集まり|雑談が苦手|複数人|会話が苦手|人といると疲れ")),
        ("phong-bua", "phòng bừa (xin được phép)", re.compile("部屋が汚|散らか")),
        ("mot-minh", "thích ở một mình", re.compile(
            "一人が好き|1人が好き|ひとりが好き|一人の時間|1人の時間|ひとり時間|一人時間|一人でいる|一人でいても|一人で|1人で|ひとりで|孤独を好|孤独を選|孤独が好|ソロ|ぼっち|静かな人|口数が少な|無口|話さない人|内向")),
    ],
    MA_CANH_GIAC: [
        ("ke-doc-hai", "nhận diện người độc hại", re.compile(
            "性格が悪い|ずるい|テイカー|嫉妬|攻撃してくる|無礼|話が通じない|非を認めない|関わってはいけない|見下す|マウント|操る|支配|裏切|毒親|危険な人|やばい人|悪口|敵が多い|離れるべき人|距離を置くべき")),
    ],
    MA_THAP: [
        ("hoc-van-iq", "học vấn, IQ không đo được", re.compile("学歴|IQ|知能|高知能|頭がいい人|頭のいい人|頭の良い人|賢い人|地頭|天才")),
        ("no-luc", "cố gắng không được đền đáp", re.compile("努力|報われ|評価され|認められ|軽く扱われ|尊重され|大器晩成|遅咲き|突然成長|花開く")),
        ("tai-nang-an", "tài năng bị ẩn", re.compile("隠された才能|隠れた才能|才能|能力が高い|ずば抜け|優秀|センス")),
    ],
    MA_TO_MO: [
        ("dong-vat", "thói quen vô hại: thú cưng", re.compile("猫|犬|動物|ペット")),
        ("thoi-quen-vat", "thói quen vô hại khác", re.compile(
            "早起き|朝型|夜型|財布|同じ映画|会釈|コーヒー|紅茶|読書が好き|散歩|手書き|左利き|血液型|植物|園芸|庭いじり|バイク|登山|道を聞かれ|自分で直す|料理が好き|お菓子作り|音楽が好き|文字|字が|ゲームが好き")),
    ],
}

#: Tệp trung niên: chủ đề theo mốc tuổi / dọn nhà (luật cứng đã đưa mốc tuổi về tệp này).
CHU_DE_TRUNG_NIEN: List[Tuple[str, str, "re.Pattern[str]"]] = [
    ("don-nha", "dọn nhà, bỏ bớt đồ", re.compile("片付け|捨て|断捨離|掃除|物が多い|ミニマ|もったいな|整理|家事")),
    ("tri-nho", "trí nhớ, não già", re.compile("物忘れ|認知症|脳の老化|記憶力|海馬|脳年齢")),
    ("tuoi-tac", "tuổi tác là nhân vật chính", re.compile("|".join(re.escape(m) for m in DAU_MOC_TUOI if m) + "|人生後半|昭和|1970|1974|老い|老け")),
]

_TU_KHOA_TRUNG_NIEN = re.compile("片付け|捨て|断捨離|掃除|物が多い|ミニマ|もったいな|家事卒業|物忘れ|認知症|脳の老化|海馬|人生後半|昭和|1970|1974|老い|老け")


#: Không có tuyến con nào cho tệp này (mã lạ) — regex không khớp gì cả, thay vì `None` để mọi
#: nơi gọi khỏi phải tự kiểm tra rỗng.
_KHONG_KHOP = re.compile(r"(?!x)x")


def regex_cua_tep(ma: str) -> "re.Pattern[str]":
    """Regex nhận diện của MỘT TỆP — hợp mọi từ khoá tuyến con thuộc tệp đó.

    Dùng làm `tu_khop` cho `chot_doi_thu.chot` khi kênh trong nhóm đánh một tệp KHÁC tệp 1
    (`MA_LECH_NHIP` giữ nguyên `chot_doi_thu.TU_KHOP_LECH_NHIP` — tay soạn riêng, không đổi
    qua hàm này) — không có nó thì mọi kênh trong nhóm bị đo bằng từ khoá của tệp 1, và kênh
    tệp 3/4/8 không kênh nào "khớp tuyến" được, dồn hết về "thị trường (gần ngách)".

    Mã lạ (không có trong `CHU_DE` lẫn không phải `MA_TRUNG_NIEN`) → regex không khớp gì.
    """
    ds = CHU_DE_TRUNG_NIEN if ma == MA_TRUNG_NIEN else CHU_DE.get(ma)
    if not ds:
        return _KHONG_KHOP
    return re.compile("|".join(rx.pattern for _m, _ten, rx in ds))


def ten_chu_de(ma: str) -> str:
    for ds in list(CHU_DE.values()) + [CHU_DE_TRUNG_NIEN]:
        for m, ten, _rx in ds:
            if m == ma:
                return ten
    return ma


def nhan_dien(tieu_de: str, kenh_nguon: str = "", *, chu_biet: bool = True) -> Optional[Tuple[str, str]]:
    """`(mã tệp, mã chủ đề)` cho một tiêu đề, hoặc `None` khi không nhận ra (để AI / để trống).

    `chu_biet=False` — 30/09/2026, Đợt 4 (A2): bảng `CHU_DE`/`CHU_DE_TRUNG_NIEN` là từ khoá tiếng
    Nhật của năm tệp ngách "tâm lý" (có cả chữ La-tinh "SNS" — khớp NHẦM tiêu đề Việt/Anh của ngách
    khác). `False` tắt hẳn việc dò bảng (trả `None`). Mặc định `True`: hành vi cũ."""
    td = (tieu_de or "").strip()
    if not chu_biet or not td or _dinh_tu_loai_tru(td):
        return None
    if any(m in td for m in DAU_MOC_TUOI) or _TU_KHOA_TRUNG_NIEN.search(td):
        # "phòng bừa" xin được phép bừa là lệch nhịp — chỉ khi KHÔNG có mốc tuổi/cách dọn.
        for m, _ten, rx in CHU_DE_TRUNG_NIEN:
            if rx.search(td):
                return MA_TRUNG_NIEN, m
        return MA_TRUNG_NIEN, "tuoi-tac"
    # Tò mò xét TRƯỚC đánh giá thấp: "道を聞かれる人の才能" là thói quen vô hại (tò mò), chữ 才能 chỉ là khuôn.
    for tep in (MA_LECH_NHIP, MA_CANH_GIAC, MA_TO_MO, MA_THAP):
        for m, _ten, rx in CHU_DE[tep]:
            if rx.search(td):
                return tep, m
    return None


def _dang_dung_ai(goc: str, kenh: str) -> Dict[str, dict]:
    """Bộ nhớ AI gán tuyến còn hạn của kênh (`nghien_cuu_chung.nhan_tuyen_doc`) — rỗng = kênh
    chưa dùng AI (hoặc đọc hỏng) → `dien_chu_de` chạy y như cũ."""
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        return ncc.nhan_tuyen_doc(goc, kenh) or {}
    except Exception:  # noqa: BLE001
        return {}


def _ngay(chu: Any) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(chu or "").strip()[:10])
    except ValueError:
        return None


#: Bộ đệm nhãn sổ theo (đường tệp, mtime) — `tep_theo_nghia` bị gọi cho từng ứng viên.
_DEM_NHAN: Dict[str, Tuple[float, Dict[str, str], Dict[str, str]]] = {}


def tep_theo_nghia(goc: str, ma_kenh: str, tieu_de: str, link: str = "",
                   kenh_nguon: str = "") -> Optional[Tuple[str, str]]:
    """`(mã tệp, nguồn)` của một tiêu đề: NHÃN TRONG SỔ trước (AI đọc nghĩa hoặc người đặt — cột
    "Tuyến / Kênh" của `content.csv`, tra theo link rồi theo tiêu đề; "khac" cũng là một nhãn),
    không có thì mới regex (`nhan_dien`). `nguồn` ∈ {"so", "regex"}.
    `None` = không ai nhận ra. Dành cho nơi khác thay dần `nhan_dien` (chỉ biết chữ) — không mạng."""
    try:
        from . import doi_thu_kenh as so  # noqa: PLC0415

        duong = os.path.join(so.thu_muc_nghien_cuu(goc, ma_kenh), "content.csv")
        mt = os.path.getmtime(duong)
        dem = _DEM_NHAN.get(duong)
        if dem is None or dem[0] != mt:
            cot, hang = so.doc_bang(goc, ma_kenh)
            o = {c: i for i, c in enumerate(cot)}
            i_t, i_l, i_td = o.get(so.COT_TUYEN), o.get(so.COT_LINK), o.get("Tiêu đề video")
            theo_link: Dict[str, str] = {}
            theo_td: Dict[str, str] = {}
            if i_t is not None:
                for d in hang:
                    ma = str(d[i_t]).strip() if i_t < len(d) else ""
                    if not ma:
                        continue
                    if i_l is not None and i_l < len(d) and str(d[i_l]).strip():
                        theo_link[so.ma_video(str(d[i_l])) or str(d[i_l]).strip()] = ma
                    if i_td is not None and i_td < len(d) and str(d[i_td]).strip():
                        theo_td[str(d[i_td]).strip()] = ma
            dem = (mt, theo_link, theo_td)
            _DEM_NHAN[duong] = dem
        _mt, theo_link, theo_td = dem
        khoa_l = so.ma_video(link) or str(link or "").strip()
        ma = theo_link.get(khoa_l) if khoa_l else None
        ma = ma or theo_td.get(str(tieu_de or "").strip())
        if ma:
            return ma, "so"
    except (OSError, ValueError):
        pass
    kq = nhan_dien(tieu_de, kenh_nguon)
    return (kq[0], "regex") if kq else None


def dien_chu_de(goc: str, kenh: str, *, tep_dang_mo: Optional[Sequence[str]] = None,
                de_cho_ai: Optional[bool] = None,
                hom_nay: Optional[_dt.date] = None) -> Dict[str, int]:
    """Điền cột "Chủ đề" cho mọi dòng content nhận ra được; điền cả "Tuyến / Kênh" khi ô ấy TRỐNG
    — TRỪ dòng mới để dành cho AI đọc nghĩa (xem đầu tệp).

    Không đè nhãn tệp đã có (AI/người đặt) — chỉ thêm chủ đề cho nó. Dòng đã có tệp mà máy nhận ra
    chủ đề của TỆP KHÁC thì chủ đề để trống (không cãi nhau với nhãn). `tep_dang_mo`: chỉ điền tệp
    trong danh sách này (mặc định: mọi tệp máy biết). `de_cho_ai`: `None` = tự nhận (kênh có bộ nhớ
    AI gán tuyến còn hạn), `True`/`False` = ép. Trả {"chu_de": n, "tep_moi": n, "xem": n,
    "de_cho_ai": n}.
    """
    from . import doi_thu_kenh as so  # noqa: PLC0415
    from .ho_so_ngach import doc_ngach  # noqa: PLC0415

    # 30/09/2026, Đợt 4 (A2): ngách có hồ sơ mà KHÔNG khai `chu_de_con_mac_dinh: true` thì bảng chủ
    # đề tiếng Nhật không có nghĩa cho nó — tắt nhận diện. Nhóm tam-ly-nhat khai true; không hồ sơ → cũ.
    hs = doc_ngach(goc, kenh)
    chu_biet = (not hs.co()) or hs.chu_de_con_mac_dinh

    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    i_td, i_t, i_cd, i_k = o.get("Tiêu đề video"), o.get(so.COT_TUYEN), o.get(so.COT_CHU_DE), o.get("Kênh")
    i_ngay, i_dau, i_link = o.get("Ngày đăng"), o.get(so.COT_LAN_DAU), o.get(so.COT_LINK)
    dem = {"chu_de": 0, "tep_moi": 0, "xem": 0}
    if i_td is None or i_t is None or i_cd is None:
        return dem
    da_hoi = _dang_dung_ai(goc, kenh) if de_cho_ai is None else {}
    che_do_ai = bool(da_hoi) if de_cho_ai is None else bool(de_cho_ai)
    hom_nay = hom_nay or _dt.date.today()
    moc_moi = hom_nay - _dt.timedelta(days=NGAY_DE_AI)
    cho_phep = set(tep_dang_mo) if tep_dang_mo else None
    doi = False
    for d in hang:
        while len(d) < len(cot):
            d.append("")
        td = str(d[i_td]).strip()
        if not td:
            continue
        dem["xem"] += 1
        kq = nhan_dien(td, str(d[i_k]) if i_k is not None else "", chu_biet=chu_biet)
        if kq is None:
            continue
        tep, cd = kq
        if cho_phep is not None and tep not in cho_phep:
            continue
        nhan = str(d[i_t]).strip()
        if not nhan and che_do_ai:
            ngay_dang = _ngay(d[i_ngay]) if i_ngay is not None else None
            moi = ngay_dang is None or ngay_dang >= moc_moi
            dau = _ngay(d[i_dau]) if i_dau is not None else None
            link = str(d[i_link]).strip() if i_link is not None else ""
            ai_da_hoi = link in da_hoi
            qua_han = dau is not None and (hom_nay - dau).days > NGAY_LUI and not ai_da_hoi
            if moi and not qua_han:
                # Dòng mới: tệp là việc AI đọc nghĩa (bước 4b ngay sau). AI đã hỏi mà "chưa chắc"
                # thì cũng để trống — trống nói thật; regex đoán thay là nói dối.
                dem["de_cho_ai"] = dem.get("de_cho_ai", 0) + 1
                continue
        if not nhan:
            d[i_t] = tep
            dem["tep_moi"] += 1
            doi = True
            nhan = tep
        if nhan == tep and str(d[i_cd]).strip() != cd:
            d[i_cd] = cd
            dem["chu_de"] += 1
            doi = True
    if doi:
        so.luu_bang(goc, kenh, cot, hang)
    return dem
