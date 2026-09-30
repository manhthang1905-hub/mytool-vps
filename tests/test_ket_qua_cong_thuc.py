"""Kết quả theo công thức (`core/chien_luoc/ket_qua.py`) — B4 `workspace/THIET-KE-CHIEN-LUOC.md`.

Fixture: một kênh giả trên `tmp_path` — sổ lượt kiểu CŨ (chỉ `nguon.nguon`) lẫn kiểu MỚI
(`cong_thuc`/`tham_do`), hồ sơ video, và `chi-so/` 5 video để ngưỡng thắng tính theo TRUNG VỊ
kênh. Không mạng, không Qt.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ho_so_video as hv  # noqa: E402
from core.chien_luoc import ket_qua  # noqa: E402

K = "K1"
#: Ngày tương đối với HÔM NAY — `NguCanh.ket_qua` (đường trạm/vòng chọn) đọc theo giờ thật.
BAY_GIO = dt.datetime.now().replace(microsecond=0)
NGAY_CU, NGAY_1, NGAY_2 = ((BAY_GIO.date() - dt.timedelta(days=d)).isoformat() for d in (20, 7, 1))
#: video_id → hiển thị 48h. Trung vị 5.000 × 3 = 15.000 > 6.000 → ngưỡng kênh 15.000.
VIDEO = {"AAAAAAAAAA1": 3000, "AAAAAAAAAA2": 4000, "AAAAAAAAAA3": 5000,
         "AAAAAAAAAA4": 25000, "AAAAAAAAAA5": 18000}


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        if isinstance(du, str):
            tep.write(du)
        else:
            json.dump(du, tep, ensure_ascii=False)


def _run(ma_luot, link, *, nguon="mot_nut", cong_thuc=None, tham_do=None, ma_goi="", bo=False):
    ng = {"nguon": nguon, "link": link, "ma": link[-11:], "tieu_de": "nguồn " + ma_luot, "kenh": "Z"}
    if cong_thuc is not None:
        ng["cong_thuc"] = cong_thuc
    if tham_do is not None:
        ng["tham_do"] = tham_do
    r = {"ma_luot": ma_luot, "nguon": ng, "ban_giao": {"da_ban_giao": bool(ma_goi), "ma_goi": ma_goi}}
    if bo:
        r["bo"] = True
    return r


def dung_kenh(goc, yaml_them=""):
    kd = os.path.join(goc, "CHANNEL", K)
    _ghi(os.path.join(kd, "kenh.yaml"), 'ma: "{0}"\n{1}'.format(K, yaml_them))
    for vid, imp in VIDEO.items():
        _ghi(os.path.join(kd, "chi-so", vid, "48h", "tong-quan.json"),
             {"video_id": vid, "impressions": imp, "thoi_luong_giay": 900})
        _ghi(os.path.join(kd, "chi-so", vid, "48h", "_thong-tin.json"), {"tieu_de": "video " + vid})
    _ghi(os.path.join(kd, "chi-so", "AAAAAAAAAA5", "48h", "traffic-type.csv"),
         "Traffic source,Impressions,Impressions click-through rate (%)\nBrowse features,9000,6.5\n")
    _ghi(os.path.join(kd, "chi-so", "bang-tom-tat.csv"),
         "Mã video,Đăng ký,Lượt xem\nAAAAAAAAAA5,6,2000\nAAAAAAAAAA3,1,1000\n")
    # sổ lượt: 0001 kiểu CŨ (không có cong_thuc, mã gói suy từ ma_luot), 20 ngày trước
    _ghi(os.path.join(kd, "tu-chay", NGAY_CU + ".json"),
         {"runs": [_run("0001", "https://youtu.be/SRC00000001")]})
    _ghi(os.path.join(kd, "tu-chay", NGAY_1 + ".json"), {"runs": [
        _run("0002", "https://youtu.be/SRC00000002", nguon="vph", cong_thuc="vph", tham_do=True,
             ma_goi="K1-0002"),
        _run("0003", "https://youtu.be/SRC00000003", ma_goi="K1-0003"),
        _run("0004", "https://youtu.be/SRC00000004", nguon="vph"),
        _run("0005", "https://youtu.be/SRC00000005", bo=True),
    ]})
    _ghi(os.path.join(kd, "tu-chay", NGAY_2 + ".json"), {"runs": [
        _run("0006", "https://youtu.be/SRC00000006", nguon="v7", cong_thuc="v7", tham_do=False)]})
    hs = {"K1-0001": ("AAAAAAAAAA5", {"48h": {"impressions": 18000, "avd_giay": 300}}),
          "K1-0002": ("AAAAAAAAAA4", {"48h": {"impressions": 25000, "avd_giay": 200}}),
          "K1-0003": ("AAAAAAAAAA3", {"72h": {"impressions": 5000, "avd_giay": 100}}),
          # video chưa có trong chi-so (V7 không thấy) — lùi về mốc hồ sơ, so cùng ngưỡng kênh
          "K1-0004": ("BBBBBBBBBB4", {"48h": {"impressions": 16000, "avd_giay": 400}})}
    for ma_goi, (vid, cs) in hs.items():
        _ghi(hv.duong_tep_ho_so(goc, K, ma_goi), {"ma_goi": ma_goi, "video_id": vid, "chi_so": cs})
    return kd


def test_nguon_cua_goi_lay_cong_thuc_lui_ve_nhan_nguon_cho_so_cu(tmp_path):
    goc = str(tmp_path)
    dung_kenh(goc)
    ng = hv.nguon_cua_goi(goc, K)
    assert ng["K1-0001"]["cong_thuc"] == "mot_nut" and ng["K1-0001"]["ngay"] == NGAY_CU
    assert ng["K1-0002"]["cong_thuc"] == "vph" and ng["K1-0002"]["tham_do"] is True
    assert ng["K1-0004"]["cong_thuc"] == "vph"  # sổ cũ: chỉ có `nguon`
    assert ng["K1-0005"]["bo"] is True
    assert ng["K1-0001"]["ma"] == "SRC00000001"


def test_nguon_cua_goi_ma_goi_that_khong_bi_luot_suy_de(tmp_path):
    goc = str(tmp_path)
    kd = dung_kenh(goc)
    # lượt phục hồi hôm sau, cùng ma_luot 0002 nhưng chưa có ma_goi → không được đè lượt đã bàn giao
    _ghi(os.path.join(kd, "tu-chay", NGAY_2 + ".json"),
         {"runs": [_run("0002", "https://youtu.be/SRC0000009X", nguon="mot_nut")]})
    assert hv.nguon_cua_goi(goc, K)["K1-0002"]["cong_thuc"] == "vph"


def test_thong_ke_thang_theo_trung_vi_kenh_khong_theo_20000(tmp_path):
    goc = str(tmp_path)
    dung_kenh(goc)
    tk = ket_qua.thong_ke(goc, K, 0, bay_gio=BAY_GIO)
    mn = tk["mot_nut"]
    # 0001 → 18.000 hiển thị: THẮNG vì ngưỡng kênh là 15.000 (dưới 20.000 cứng vẫn thắng)
    assert (mn["lam"], mn["n"], mn["thang"], mn["truot"], mn["cho"]) == (2, 2, 1, 1, 0)
    vph = tk["vph"]
    # 0002 (V7 thấy, 25.000) thắng; 0004 không có trong chi-so → mốc hồ sơ 16.000 ≥ 15.000 thắng
    assert (vph["lam"], vph["n"], vph["thang"], vph["tham_do"]) == (2, 2, 2, 1)
    assert tk["v7"]["lam"] == 1 and tk["v7"]["n"] == 0 and tk["v7"]["cho"] == 1
    assert "K1-0005" not in sum((o["goi"] for o in tk.values()), [])  # lượt bỏ không tính
    assert mn["ctr_trang_chu_tv"] == 6.5
    assert mn["avd_giay_tv"] == 200.0  # trung vị 300 (48h) và 100 (lùi 72h)
    assert mn["sub_1k"] == round(1000.0 * 7 / 3000, 2)
    _vm, nguong = ket_qua.video_kenh(goc, K)
    assert nguong == 15000


def test_thong_ke_cua_so_ngay_bo_so_cu(tmp_path):
    goc = str(tmp_path)
    dung_kenh(goc)
    tk = ket_qua.thong_ke(goc, K, 14, bay_gio=BAY_GIO)
    assert tk["mot_nut"]["lam"] == 1  # 0001 (20 ngày trước) ngoài cửa sổ 14 ngày
    assert ket_qua.thong_ke(goc, K, 28, bay_gio=BAY_GIO)["mot_nut"]["lam"] == 2


def test_thong_ke_kenh_trong_hoac_hong_tra_rong(tmp_path):
    assert ket_qua.thong_ke(str(tmp_path), "KHONG-CO") == {}


def test_goi_y_ti_trong_chi_don_khi_du_6_video():
    tk = {"a": {"n": 2, "thang": 2}, "b": {"n": 2, "thang": 0}}
    ts, ly = ket_qua.goi_y_ti_trong(tk, {"a": 1, "b": 1})
    assert ts == {"a": 0.5, "b": 0.5} and "4/6" in ly
    tk = {"a": {"n": 4, "thang": 4}, "b": {"n": 4, "thang": 0}}
    ts, _ = ket_qua.goi_y_ti_trong(tk, {"a": 1, "b": 1})
    assert ts["a"] > ts["b"] and abs(sum(ts.values()) - 1) < 1e-6


def test_ghi_tep_chien_luoc_json_chi_goi_y_kem_mot_dong_log(tmp_path):
    goc = str(tmp_path)
    dung_kenh(goc, 'chien_luoc: "vph:0.5, mot_nut:0.5"\n')
    log = []
    duong = ket_qua.ghi_tep(goc, K, bay_gio=BAY_GIO, log=log.append)
    assert duong.endswith(os.path.join("nghien-cuu", "chien-luoc.json"))
    with io.open(duong, encoding="utf-8") as tep:
        du = json.load(tep)
    assert du["da_ap"] is False and du["nguong_thang_48h"] == 15000
    assert du["ti_trong_hien_tai"] == {"vph": 0.5, "mot_nut": 0.5}
    assert set(du["ti_trong_goi_y"]) == {"vph", "mot_nut"}
    assert du["thong_ke"]["vph"]["thang"] == 2
    assert len(log) == 1 and "gợi ý (chưa áp)" in log[0]


def test_tham_do_dem_video_that_theo_cong_thuc(tmp_path):
    """`ke_hoach`: công thức được thăm dò = công thức ít video nhất 14 ngày — giờ đếm thật qua
    `ket_qua` (trước đây mọi công thức là 0 → luôn rơi vào công thức tỉ trọng nhỏ nhất)."""
    from core import chien_luoc
    from core.chien_luoc import ngu_canh

    goc = str(tmp_path)
    dung_kenh(goc, 'chien_luoc: "vph:0.3, mot_nut:0.7"\n')
    for ma_goi in ("K1-0002", "K1-0004"):  # hai video vph mới ra, CHƯA có kết luận
        os.remove(hv.duong_tep_ho_so(goc, K, ma_goi))
    nc = ngu_canh.dung(goc, K, co_v7=False, bay_gio=BAY_GIO)
    kq = nc.ket_qua(14)
    # vph đã RA 2 video (n=0, chưa có kết luận), mot_nut 1 (n=1) trong 14 ngày → thăm dò mot_nut.
    # Coi mọi công thức là 0, hay đếm theo `n`, đều chọn nhầm vph (tỉ trọng nhỏ hơn / n nhỏ hơn).
    assert (kq["vph"]["lam"], kq["vph"]["n"], kq["mot_nut"]["lam"], kq["mot_nut"]["n"]) == (2, 0, 1, 1)
    kh = chien_luoc.ke_hoach(nc, tham_do=True)
    assert kh.tham_do == "mot_nut"
