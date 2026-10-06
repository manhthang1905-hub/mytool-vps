#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tong_hop.py — Gom MỌI snapshot đã cào của một kênh thành một khối dữ liệu duy nhất.

    python tong_hop.py du-lieu/k1            # in tóm tắt + ghi lich-su.json

Đầu ra: du-lieu/<kênh>/lich-su.json — mảng bản ghi, mỗi bản ghi là một (video × mốc),
chứa TẤT CẢ chỉ số đã cào. Dùng cho: bảng điều khiển, và cho agent đọc trực tiếp.
"""
import csv
import datetime
import glob
import io
import json
import os
import re
import sys

if sys.stdout is not None:
    # Chạy dưới `pythonw.exe` (CHAY-GON.vbs, không cửa sổ đen) thì sys.stdout
    # là None — không có console nào để đổi bảng mã. Module này còn bị IMPORT
    # (không chỉ chạy trực tiếp) từ core/cong_thuc_v7.py, nên thiếu chặn ở đây
    # là cả tool sập ngay lúc dựng tab Phân tích.
    sys.stdout.reconfigure(encoding="utf-8")
GOC = os.path.dirname(os.path.abspath(__file__))


def doc_csv(p):
    if not os.path.exists(p):
        return []
    return [r for r in csv.reader(io.open(p, encoding="utf-8-sig")) if any(c.strip() for c in r)]


def doc_retention(p):
    if not os.path.exists(p):
        return []
    try:
        import openpyxl
        ws = openpyxl.load_workbook(p).active
        return [round(float(r[1]), 1) for r in list(ws.iter_rows(values_only=True))[1:] if r[1] is not None]
    except Exception:
        return []


def luc_chup(tm):
    """Thời điểm chụp thật, đọc TRONG gói chứ không lấy mtime của tệp.

    ═══ VÌ SAO KHÔNG DÙNG MTIME ═══

    Bản cũ lấy mtime của tệp raw mới nhất. Đúng chừng nào tệp còn nằm nguyên chỗ tiện ích
    ghi ra — và sai ngay khi nó được chép đi, vì mtime lúc đó là **giờ chép**, không phải
    giờ chụp.

    Đúng cảnh đang dùng: tiện ích chạy trong máy ảo, đẩy gói về trạm nhận ở máy này. Mọi
    tệp tới trong cùng một lượt nên mang cùng một mtime.

    Hỏng dây chuyền, không phải hỏng một ô:
      1. mọi lần chụp có cùng `luc_chup`;
      2. `gio_dang()` suy ngược giờ đăng = lúc chụp − mốc, rồi mốc được TÍNH LẠI từ đó, nên
         mọi lần chụp của một video nhận cùng một mốc;
      3. khoá gộp là `(video, mốc)` → tất cả trùng khoá và gộp làm một.
    Đo thật: 52 lần chụp có chỉ số còn **5**, mỗi video một dòng, mất sạch trục thời gian —
    tức mất luôn cách so hai video ở cùng mốc giờ, thứ cả phương pháp dựa vào.

    Tiện ích đã ghi `captured_at` (ISO, giờ UTC) vào đầu MỌI gói. Con số ấy đi theo tệp qua
    mọi lần chép, nên đọc nó. Chỉ đọc 400 byte đầu vì đó là khoá đầu tiên của gói — quét cả
    97 MB raw chỉ để lấy một dấu thời gian là phí.
    """
    moc = []
    for p in glob.glob(os.path.join(tm, "raw", "*")):
        try:
            with io.open(p, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r'"captured_at"\s*:\s*"([^"]+)"', f.read(400))
            if m:
                t = datetime.datetime.strptime(m.group(1)[:19], "%Y-%m-%dT%H:%M:%S")
                moc.append(t.replace(tzinfo=datetime.timezone.utc).astimezone().timestamp())
                continue
        except Exception:
            pass
        try:
            moc.append(os.path.getmtime(p))     # gói cũ chưa có captured_at
        except OSError:
            pass
    t = max(moc) if moc else os.path.getmtime(tm)
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def _captured_at_that(thu_muc_moc):
    """Epoch giây CHỤP THẬT — CHỈ đọc `captured_at` trong `raw/*`, KHÔNG suy từ mtime.

    Khác `luc_chup` (có lùi về mtime cho gói cũ, xem docstring hàm đó): hàm này phục vụ
    `tuoi_that_gio`, nơi cần biết THẬT SỰ có đo được tuổi hay không. mtime là giờ tệp TỚI
    MÁY NÀY (chép/đồng bộ) — dùng nó để tính TUỔI thì sai theo đúng cách `luc_chup` đã cảnh
    báo, nên ở đây thà trả `None` để nơi gọi lùi về nhãn thư mục còn hơn suy nhầm.

    `None` nếu không gói raw nào mang `captured_at` đọc được.
    """
    moc = []
    for p in glob.glob(os.path.join(thu_muc_moc, "raw", "*")):
        try:
            with io.open(p, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r'"captured_at"\s*:\s*"([^"]+)"', f.read(400))
            if m:
                t = datetime.datetime.strptime(m.group(1)[:19], "%Y-%m-%dT%H:%M:%S")
                moc.append(t.replace(tzinfo=datetime.timezone.utc).timestamp())
        except Exception:
            pass
    return max(moc) if moc else None


def tuoi_that_gio(thu_muc_moc):
    """Tuổi THẬT của video (giờ, có thể lẻ) TẠI LÚC CHỤP = giờ chụp thật − giờ đăng — đọc
    thẳng từ gói dữ liệu, KHÔNG suy từ tên thư mục `thu_muc_moc` (kiểu `13h`, `48h`).

    ═══ VÌ SAO CẦN HÀM NÀY ═══

    VPS giờ chỉ mở trình duyệt của một kênh MỘT LẦN/ngày (phiên ngắn trước giờ đăng của
    kênh đó). Báo thức mốc (`chrome.alarms`) quá hạn dồn lại nổ thành CHÙM ngay khi Chrome
    mở: báo thức tên "13h" có thể chụp đúng lúc video đã 23 giờ tuổi, nhưng tiện ích vẫn
    lưu vào thư mục `13h/` vì đó là NHÃN DỰ ĐỊNH của báo thức, không phải tuổi thật lúc
    chụp. `core/cong_thuc_v7.py` trước đây tin thẳng tên thư mục này.

    Cùng cơ chế `captured_at` mà `gom()`/`gio_dang()` dùng để suy lại mốc giờ (đọc trong
    docstring `luc_chup`) — ở đây trả thẳng số giờ, không định dạng chuỗi, để nơi gọi so
    với một cửa sổ dung sai (`core.cong_thuc_v7.CUA_SO_TUOI_THAT`).

    Trả `None` khi không đủ dữ liệu để tính: thiếu `_thong-tin.json`/`ngay_dang`, hoặc
    không gói raw nào mang `captured_at` — nơi gọi khi đó lùi về nhãn thư mục.
    """
    cap = _captured_at_that(thu_muc_moc)
    if cap is None:
        return None
    try:
        with io.open(os.path.join(thu_muc_moc, "_thong-tin.json"), encoding="utf-8") as f:
            tt = json.load(f)
    except (OSError, ValueError):
        return None
    ngay = tt.get("ngay_dang")
    if not ngay:
        return None
    try:
        dang = datetime.datetime.strptime(str(ngay)[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        try:
            dang = datetime.datetime.strptime(str(ngay)[:10], "%Y-%m-%d")
        except ValueError:
            return None
    dang_ts = dang.replace(tzinfo=datetime.timezone.utc).timestamp()
    return (cap - dang_ts) / 3600.0


def dang_that_cua_video(thu_muc_video):
    """Epoch giây GIỜ ĐĂNG THẬT của video — `ngay_dang` (ISO có giờ, UTC) trong `_thong-tin.json`
    của BẤT KỲ mốc nào của video (không phải mốc nào cũng có tệp này). `None` khi không có giờ.

    01/10/2026 (vá lỗ dữ liệu): `gio_dang()` suy giờ đăng từ NHÃN thư mục — nhưng một lượt bù
    từng ghi CÙNG bản chụp 125h vào mọi thư mục 6h…96h (một video TL3, 01/10), trung vị nhãn lệch hẳn và
    bản 125h bị gắn nhãn 33h/36h. Giờ đăng ghi trong gói là sự thật duy nhất không phụ thuộc nhãn."""
    for p in sorted(glob.glob(os.path.join(thu_muc_video, "*", "_thong-tin.json"))):
        try:
            ngay = str((json.load(io.open(p, encoding="utf-8")) or {}).get("ngay_dang") or "")
            t = datetime.datetime.strptime(ngay[:19], "%Y-%m-%dT%H:%M:%S")
        except (OSError, ValueError, TypeError, AttributeError):
            continue
        return t.replace(tzinfo=datetime.timezone.utc).timestamp()
    return None


def gio_dang(ban_ghi):
    """Giờ đăng thật của từng video, suy ngược từ các bản có nhãn mốc của extension:
    giờ đăng = lúc chụp − mốc. Lấy TRUNG VỊ vì một vài thư mục bị ghi đè muộn nên lệch hẳn
    (ví dụ thư mục 33h của video 2 mang mtime trễ 6 tiếng so với 17h/39h/48h)."""
    goc = {}
    for b in ban_ghi:
        if b["moc_gio"] is None or not b["luc_chup"]:
            continue
        t = datetime.datetime.strptime(b["luc_chup"], "%Y-%m-%d %H:%M").timestamp()
        goc.setdefault(b["video_id"], []).append(t - b["moc_gio"] * 3600)
    return {v: sorted(ts)[len(ts) // 2] for v, ts in goc.items()}


def phan_loai_nguon(t, nganh):
    if any(k in t for k in nganh.get("loai_tru", [])):
        return "lech"
    if any(k in t for k in nganh.get("tu_khoa_manh", [])):
        return "dung"
    if sum(1 for k in nganh.get("tu_khoa_yeu", []) if k in t) >= 2:
        return "dung"
    return "trung_tinh"


def gom(kenh_dir, nganh):
    ban_ghi = []
    # Hai lượt: lượt 1 đọc hết `tong-quan.json` để biết video nào CHƯA bản nào có số. Video ấy vẫn phải có MỘT dòng
    # (bản rỗng mới nhất) — bản cũ bỏ mọi bản rỗng nên 4 video (06/10/2026) mất khỏi `bang-tom-tat.csv`, bảng hiện
    # như chưa từng chụp thay vì "chụp rồi mà Studio rỗng". Video có số ở mốc sớm thì dòng lấy mốc sớm đó.
    tat_ca, co_so, rong_moi = [], set(), {}
    for tq_p in glob.glob(os.path.join(kenh_dir, "*", "*", "tong-quan.json")):
        tm = os.path.dirname(tq_p)
        try:
            q = json.load(io.open(tq_p, encoding="utf-8"))
        except Exception:
            continue
        tat_ca.append((tq_p, tm, q))
        vid = q.get("video_id") or os.path.basename(os.path.dirname(tm))
        if q.get("impressions") is not None or q.get("views") is not None:
            co_so.add(vid)
        elif vid != "kenh" and (q.get("gio_sau_dang") or 0) >= (rong_moi.get(vid) or (-1, ""))[0]:
            rong_moi[vid] = (q.get("gio_sau_dang") or 0, tq_p)
    for tq_p, tm, q in tat_ca:
        # ĐỪNG bỏ theo TÊN THƯ MỤC. Lịch hằng ngày của tiện ích ghi gói kênh vào
        # `chi-so/kenh/kenh-<ngày>/`, và chính gói đó mới có thẻ phễu — nơi duy nhất có
        # TỔNG IMPRESSIONS và CTR TOÀN KÊNH. Bộ lọc `startswith("kenh")` cũ ném hết chúng
        # đi, chỉ còn các gói `tay-*` gom rời (không có phễu) ⇒ hai cột "Lượt hiển thị" và
        # "Tỷ lệ bấm" của `kenh-theo-ngay.csv` trống suốt từ 28/08 tới 05/09/2026, đúng hai
        # cột cho biết cổng 1 và cổng 2 của kênh đang ở đâu.
        # Bản ghi cấp kênh vẫn được loại khỏi bảng VIDEO — nhưng loại ở `doc_kenh()` theo
        # `video_id == "kenh"`, tức theo NỘI DUNG gói, không theo cách đặt tên thư mục.
        # Bản chụp "tay-*" (extension bắt được từ tab đang mở) trước đây bị bỏ hết. Nhưng đúng những
        # bản đó giữ mốc 69h của video 2 — mốc cho thấy nó đã dừng. Giữ lại, miễn là có chỉ số thật.
        vid = q.get("video_id") or os.path.basename(os.path.dirname(tm))
        if q.get("impressions") is None and q.get("views") is None:
            if vid in co_so or (rong_moi.get(vid) or (0, ""))[1] != tq_p:
                continue

        # --- vùng: LUÔN lấy dòng Total làm mẫu số
        geo_rows = doc_csv(os.path.join(tm, "geo.csv"))
        vung, tong_geo = {}, 0
        if geo_rows:
            for r in geo_rows[1:]:
                ten, vw = r[0].strip(), float(r[1] or 0)
                if ten == "Total":
                    tong_geo = vw
                else:
                    vung[ten] = {"views": vw, "avd": r[2] if len(r) > 2 else ""}
            if not tong_geo:
                tong_geo = sum(v["views"] for v in vung.values())
        for v in vung.values():
            v["pct"] = round(100 * v["views"] / tong_geo, 1) if tong_geo else None

        # --- pool đề xuất
        pool_rows = doc_csv(os.path.join(tm, "traffic-related.csv"))
        pool = {"so_nguon": 0, "imp": 0, "views": 0, "dung_pct_imp": None, "top": [], "phan_bo": {}}
        if len(pool_rows) > 2:
            ng = [r for r in pool_rows[2:] if len(r) > 5 and r[2]]
            dem = {"dung": [0, 0], "lech": [0, 0], "trung_tinh": [0, 0]}
            for r in ng:
                k = phan_loai_nguon(r[2], nganh)
                dem[k][0] += float(r[3] or 0)
                dem[k][1] += float(r[5] or 0)
            ti = sum(v[0] for v in dem.values())
            pool = {
                "so_nguon": len(ng),
                "imp": float(pool_rows[1][3] or 0) if len(pool_rows[1]) > 3 else ti,
                "ctr": float(pool_rows[1][4] or 0) if len(pool_rows[1]) > 4 and pool_rows[1][4] else None,
                "views": float(pool_rows[1][5] or 0) if len(pool_rows[1]) > 5 and pool_rows[1][5] else None,
                # Bảng nguồn KHÔNG BAO GIỜ liệt kê hết: tổng impressions các nguồn chỉ bằng một
                # phần Total (video 1 @133h: 565/2465 = 23%). "Đúng ngách %" vì thế luôn tính
                # trên một mẫu con — ghi lại độ phủ để biết con số đó có đáng tin không.
                # Mẫu 5% thì tỷ lệ đúng ngách nhảy loạn giữa các mốc mà không nói lên điều gì.
                "phu_pct": round(100 * ti / float(pool_rows[1][3]), 1)
                           if len(pool_rows[1]) > 3 and float(pool_rows[1][3] or 0) else None,
                "dung_pct_imp": round(100 * dem["dung"][0] / ti, 1) if ti else None,
                "dung_pct_view": round(100 * dem["dung"][1] / sum(v[1] for v in dem.values()), 1) if sum(v[1] for v in dem.values()) else None,
                "imp_moi_nguon": round(ti / len(ng), 1) if ng else None,
                "phan_bo": {k: {"imp": v[0], "views": v[1]} for k, v in dem.items()},
                "top": [{"tieu_de": r[2][:70], "imp": float(r[3] or 0), "views": float(r[5] or 0),
                         "loai": phan_loai_nguon(r[2], nganh)}
                        for r in sorted(ng, key=lambda r: -float(r[3] or 0))[:10]],
            }

        ban_ghi.append({
            "video_id": vid,
            "tieu_de": q.get("tieu_de", ""),
            "ngay_dang": q.get("ngay_dang"),
            "moc_gio": q.get("gio_sau_dang"),
            "luc_chup": luc_chup(tm),
            "thoi_luong_giay": q.get("thoi_luong_giay"),
            "impressions": q.get("impressions"),
            "impressions_24h": q.get("impressions_24h"),
            "ctr": q.get("ctr"),
            "views": q.get("views"),
            # Lượt xem THẬT (engaged) — thứ YouTube dùng để tính tiền và xét bật kiếm tiền.
            # Từ 24/08/2026 "views" là lượt công khai, đếm ngay từ khung hình đầu, nên nó phồng
            # lên theo nguồn traffic: video được đẩy lên trang chủ đo được 54% thật, còn video
            # sống bằng đề xuất vẫn 98%. Mọi tỷ lệ tính từ lượt xem phải dùng con số này.
            "views_that": q.get("views_that") or q.get("views_that_uoc"),
            "views_that_uoc_tinh": q.get("views_that") is None,
            "unique_viewers": q.get("unique_viewers"),
            # Lượt xem của CHÍNH cửa sổ đã chốt sổ (thẻ giữ chân). `views` là số realtime,
            # `unique_viewers` lại thuộc cửa sổ chốt — chia hai số của hai cửa sổ là ra tỷ lệ
            # xem-lặp ảo. V6 ngày 05/09/2026: 46 ÷ 13 = 3,5 (như thể số bẩn) trong khi cùng cửa
            # sổ là 26 ÷ 13 = 2,0. Luật 5 của sổ tay kênh chấm trên tỷ lệ này nên phải khớp cửa sổ.
            "views_chot": q.get("avd_tren_so_luot"),
            "watch_hours": q.get("watch_hours"),
            "avd_giay": q.get("avd_giay"),
            "avd_pct": q.get("avd_pct") or (round(100 * q["avd_giay"] / q["thoi_luong_giay"], 1)
                                            if q.get("avd_giay") and q.get("thoi_luong_giay") else None),
            "subs": q.get("subs"),
            "traffic": q.get("traffic") or {},
            "thiet_bi": q.get("thiet_bi") or {},
            "phu_de": q.get("phu_de") or {},
            "external": q.get("external_chi_tiet") or {},
            "vung_tong_views": tong_geo,
            "vung": vung,
            "pool": pool,
            "retention": doc_retention(os.path.join(tm, "retention.xlsx")),
            "imp_theo_gio": q.get("imp_theo_gio") or [],
            # Đường dẫn TUYỆT ĐỐI. Trước đây lấy tương đối so với thư mục mã — chạy được
            # khi mã và dữ liệu nằm cùng ổ, nhưng trên máy người dùng công cụ ở ổ D còn
            # thư mục Tải xuống ở ổ C, và relpath giữa hai ổ ném lỗi làm hỏng cả lượt đọc.
            "thu_muc": os.path.abspath(tm).replace("\\", "/"),
        })
    # Mốc giờ tính lại đồng loạt trên một gốc duy nhất mỗi video, để mọi bản chụp — kể cả tay-* —
    # nằm trên cùng một trục và so sánh được với nhau.
    goc = gio_dang(ban_ghi)
    # 01/10/2026: có GIỜ ĐĂNG THẬT (`_thong-tin.json`) + `captured_at` thì mốc = tuổi thật lúc chụp
    # — không tin nhãn thư mục (xem `dang_that_cua_video`). Thiếu một trong hai → cách cũ.
    dang_that = {}
    for b in ban_ghi:
        vid = b["video_id"]
        if vid and vid != "kenh" and vid not in dang_that:
            dang_that[vid] = dang_that_cua_video(os.path.dirname(b["thu_muc"]))
    for b in ban_ghi:
        d = dang_that.get(b["video_id"])
        cap = _captured_at_that(b["thu_muc"]) if d else None
        if d and cap:
            b["moc_gio"] = int(round((cap - d) / 3600.0))
            b["gio_dang"] = datetime.datetime.fromtimestamp(d).strftime("%Y-%m-%d %H:%M")
            continue
        g = goc.get(b["video_id"])
        if g and b["luc_chup"]:
            t = datetime.datetime.strptime(b["luc_chup"], "%Y-%m-%d %H:%M").timestamp()
            b["moc_gio"] = round((t - g) / 3600)
            b["gio_dang"] = datetime.datetime.fromtimestamp(g).strftime("%Y-%m-%d %H:%M")
    ban_ghi.sort(key=lambda b: (b.get("video_id") or "", b.get("luc_chup") or ""))
    # Cùng một mốc giờ thường có 2–3 bản (lịch của extension + bản bắt được từ tab đang mở).
    # Giữ bản chụp muộn nhất có đủ chỉ số — số của Studio chỉ tăng, nên bản muộn là bản đúng.
    giu = {}
    for b in ban_ghi:
        # Bản ghi cấp kênh không có mốc giờ — khoá theo lúc chụp để không gộp mất lịch sử.
        k = (b["video_id"], b["moc_gio"] if b["moc_gio"] is not None else b["luc_chup"])
        cu = giu.get(k)
        diem = (b.get("impressions") is not None, sum(1 for v in b.values() if v not in (None, "", {}, [])))
        if not cu or diem >= cu[0]:
            giu[k] = (diem, b)
    return sorted((v[1] for v in giu.values()), key=lambda b: (b.get("video_id") or "", b.get("luc_chup") or ""))


def cap_nhat_gio_online_va_khan_gia(goc, ma_kenh, kenh_dir):
    """Gọi sau khi `chi-so/kenh/kenh-<ngày>/raw/` có dữ liệu mới (một phiên quét
    tab-build_audience): nhờ `chi_so_ytb.giai_ma` giải mã giờ khán giả online
    (→ `chi-so/gio-online.json`, insight #7 29/09/2026) và card "khán giả cũng
    xem" (→ kho nghiên cứu nhóm, insight #8) từ lượt raw GẦN NHẤT có dữ liệu.

    Không tốn mạng — chỉ đọc JSON đã cào sẵn. An toàn gọi lại nhiều lần: cả
    hai hàm bên dưới tự so `captured_at`/dán nhãn nguồn trước khi ghi, gọi lại
    trên cùng một lượt quét không ghi thừa. Chỉ xét TỐI ĐA 5 thư mục `kenh-*`
    gần nhất — đủ cho một phiên, khỏi quét lại cả lịch sử mỗi lần gọi.

    Trả `{"gio_online": bảng hoặc None, "khan_gia_cung_xem": bản ghi hoặc None}`.
    """
    from . import giai_ma  # noqa: PLC0415 — chỉ nhập khi thật sự cần, tránh nặng lúc chỉ gọi gom()

    raws = sorted(glob.glob(os.path.join(kenh_dir, "kenh", "kenh-*", "raw")), reverse=True)[:5]
    ra = {"gio_online": None, "khan_gia_cung_xem": None}
    for raw in raws:
        if ra["gio_online"] is None:
            ra["gio_online"] = giai_ma.cap_nhat_gio_online(raw, kenh_dir)
        if ra["khan_gia_cung_xem"] is None:
            ra["khan_gia_cung_xem"] = giai_ma.cap_nhat_khan_gia_cung_xem(goc, ma_kenh, raw)
        if ra["gio_online"] is not None and ra["khan_gia_cung_xem"] is not None:
            break
    return ra


def main():
    kenh_dir = sys.argv[1] if len(sys.argv) > 1 else "du-lieu/k1"
    kenh_dir = os.path.join(GOC, kenh_dir) if not os.path.isabs(kenh_dir) else kenh_dir
    ten_kenh = os.path.basename(kenh_dir.rstrip("/\\"))
    ng_p = os.path.join(GOC, "nganh", f"{ten_kenh}.json")
    if not os.path.exists(ng_p):
        ng_p = os.path.join(GOC, "nganh", "kenh1.json")
    nganh = json.load(io.open(ng_p, encoding="utf-8"))
    bg = gom(kenh_dir, nganh)
    out = os.path.join(kenh_dir, "lich-su.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps({"kenh": ten_kenh, "nganh": nganh.get("ten"), "ban_ghi": bg}, ensure_ascii=False, indent=1))
    print(f"{len(bg)} bản ghi từ {len(set(b['video_id'] for b in bg))} video → {out}")
    for b in bg:
        so = lambda x, d="—": d if x is None else x
        print(f"  {b['video_id']} {b['luc_chup']} {str(so(b['moc_gio']))+'h':>6} "
              f"imp={so(b['impressions']):>6} ctr={so(b['ctr'])} views={so(b['views'])} "
              f"uniq={so(b['unique_viewers'])} avd={so(b['avd_pct'])}% "
              f"pool={b['pool']['so_nguon']}ng/{so(b['pool']['dung_pct_imp'])}%")


if __name__ == "__main__":
    main()
