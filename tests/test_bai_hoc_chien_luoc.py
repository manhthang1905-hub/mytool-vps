"""Một chỗ đọc bài học (`core/chien_luoc/bai_hoc.py`) — mục 3a/3b `workspace/THIET-KE-CHIEN-LUOC.md`.

Kiểm luật phạm vi kênh > nhóm > ngoài, ngưỡng n ≥ 3 mới bơm, và điểm thoát (đường giữ chân →
30s/2p/vách → nối về nguồn). Fixture trên `tmp_path`, không mạng, không Qt.
"""

from __future__ import annotations

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ho_so_video as hv  # noqa: E402
from core.chien_luoc import bai_hoc as bh  # noqa: E402

K = "K1"
NHOM = "g1"


def _ghi(duong, du):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        if isinstance(du, str):
            tep.write(du)
        else:
            json.dump(du, tep, ensure_ascii=False)


def _kenh(goc, nhom=NHOM):
    kd = os.path.join(goc, "CHANNEL", K)
    _ghi(os.path.join(kd, "kenh.yaml"), 'ma: "{0}"\nnhom: "{1}"\n'.format(K, nhom))
    return kd


def _nhom(goc):
    nd = os.path.join(goc, "CHANNEL", "_NHOM", NHOM)
    _ghi(os.path.join(nd, "INSIGHT-CHON-CONTENT.md"),
         "INSIGHT nhóm.\n\n1. CTR trang chủ là cổng quyết định. Video thắng đạt 5,5–6,2%. Câu thứ ba bị cắt.\n"
         "2. Độ dài 15–21 phút hit 14,5%.\n")
    _ghi(os.path.join(nd, "bang-nhom.csv"),
         "Kênh,Tệp,Tiêu đề,Mã video,Ngày đăng,Lượt hiển thị\n"
         + "".join("K9,1,tiêu đề {0},VVVVVVVVV{0:02d},2026-09-01,{1}\n".format(i, 1000 * i) for i in range(1, 5)))
    _ghi(os.path.join(nd, "bai-hoc-ngoai", "may-khac.json"), {"bai_hoc": [
        {"truc": "tieu_de_cum", "cum": "x", "cau": "ngoài: cụm x CTR 7% (n=9).", "n": 9},
        {"truc": "mo_dau", "cau": "ngoài: mở đầu bằng câu hỏi giữ 2:00 tốt hơn 6 điểm (n=12).", "n": 12},
    ]})
    return nd


def _san_xuat(goc, bai):
    _ghi(os.path.join(goc, "CHANNEL", K, "nghien-cuu", "bai-hoc-san-xuat.json"), {"kenh": K, "bai_hoc": bai})


def test_luat_pham_vi_kenh_truoc_nhom_khi_kenh_chua_co_so_ngoai_khi_n_bang_0(tmp_path):
    goc = str(tmp_path)
    _kenh(goc)
    _nhom(goc)
    _san_xuat(goc, [
        {"truc": "tieu_de_cum", "cum": "x", "quan_sat": "x: CTR trung vị 5,1% (n=5) — kênh 4,8% (n=9)",
         "so_mau": 5, "do_tin_cay": "vua"},
        {"truc": "tieu_de_cum", "cum": "y", "quan_sat": "y: CTR trung vị 9,0% (n=1)", "so_mau": 1},
    ])
    ds = bh.doc(goc, K, "chon", tat_ca=True)
    pv = [b["pham_vi"] for b in ds if b["bom"]]
    assert pv and pv[0] == "kenh" and pv == sorted(pv, key=bh.PHAM_VI.index)
    # nhóm: kênh chưa có video nào đo 48h → insight nhóm vào (cỡ mẫu = số video trong bảng nhóm)
    ins = [b for b in ds if b["truc"] == "insight_nhom"]
    assert len(ins) == 2 and ins[0]["pham_vi"] == "nhom" and ins[0]["n"] == 4
    assert "Câu thứ ba" not in ins[0]["cau"]  # tối đa 2 câu
    # ngoài: trục (tieu_de_cum, x) kênh đã có n=5 → KHÔNG vào; trục mo_dau kênh n=0 → vào
    ngoai = [b for b in ds if b["pham_vi"] == "ngoai"]
    assert [b["truc"] for b in ngoai] == ["mo_dau"]
    # n < 3: có trong danh sách cho người đọc nhưng không bơm
    y = [b for b in ds if b["cum"] == "y" and b["truc"] == "tieu_de_cum"]
    assert y and y[0]["bom"] is False
    chu = bh.khoi_chu(goc, K, "chon")
    assert "x: CTR trung vị 5,1%" in chu and "y: CTR" not in chu
    assert bh.NHAN_NHOM.strip() in chu and bh.NHAN_NGOAI.strip() in chu
    assert chu.index("x: CTR") < chu.index(bh.NHAN_NHOM.strip())


def test_nhom_bi_gat_khi_kenh_da_co_du_so_tren_truc(tmp_path, monkeypatch):
    from core.cong_thuc_v7 import VideoMinh

    goc = str(tmp_path)
    _kenh(goc)
    _nhom(goc)
    ds = [VideoMinh(ma="M%010d" % i, hien_thi_48h=1000.0 * i) for i in range(3)]
    monkeypatch.setattr(bh, "_video_v7", lambda _g, _k: (ds, 6000.0))
    assert not [b for b in bh.doc(goc, K, "chon", tat_ca=True) if b["truc"] == "insight_nhom"]


def test_loc_dung_cho_va_toi_da(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, nhom="")
    _san_xuat(goc, [
        {"truc": "thumbnail_ctr", "cum": "", "quan_sat": "bìa kiểu A: CTR 6% (n=4)", "so_mau": 4},
        {"truc": "do_dai_avd", "cum": "", "quan_sat": "ngắn giữ hơn (n=6)", "so_mau": 6},
    ])
    assert [b["truc"] for b in bh.doc(goc, K, "bia")] == ["thumbnail_ctr"]
    assert [b["truc"] for b in bh.doc(goc, K, "kich_ban")] == ["do_dai_avd"]
    assert len(bh.doc(goc, K, "", toi_da=1)) == 1
    assert bh.doc(str(tmp_path / "khong-co"), "KX", "chon") == []  # kênh không có gì: rỗng, không lỗi


def test_do_duong_giu_chan_30s_2p_va_vach_bo_man_ket():
    r = [100.0 - 0.3 * i for i in range(100)]
    for i in range(41, 100):
        r[i] -= 15.0          # vách ở 40→41 (≈ 4:09 trên video 600s)
    for i in range(96, 100):
        r[i] -= 40.0          # màn kết rơi mạnh hơn — không được tính là vách
    do = bh.do_duong_giu_chan(r, 600)
    assert do["giu_30s"] == round(r[5], 1) and do["giu_2p"] == round(r[20], 1)
    assert do["vach"] in ("3:57", "4:03", "4:09") and do["vach_rot"] >= 15
    assert bh.do_duong_giu_chan([], 600)["giu_2p"] is None
    assert bh.do_duong_giu_chan(r, 90)["giu_2p"] is None  # video ngắn hơn 2:00


def _retention(duong, r):
    openpyxl = pytest.importorskip("openpyxl")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Video position (%)", "Absolute audience retention (%)"])
    for i, v in enumerate(r):
        ws.append([i, v])
    wb.save(duong)


def test_diem_thoat_noi_ve_nguon_va_khoi_giu_tot_roi_som(tmp_path):
    from core import loi_thoai

    goc = str(tmp_path)
    kd = _kenh(goc, nhom="")
    giu2 = {"AAAAAAAAAA1": 30.0, "AAAAAAAAAA2": 45.0, "AAAAAAAAAA3": 60.0}
    runs = []
    for so, (vid, g) in enumerate(sorted(giu2.items()), 1):
        moc = os.path.join(kd, "chi-so", vid, "72h")
        _ghi(os.path.join(moc, "tong-quan.json"), {"video_id": vid, "impressions": 1000, "thoi_luong_giay": 600})
        _ghi(os.path.join(moc, "_thong-tin.json"), {"tieu_de": "video " + vid})
        _retention(os.path.join(moc, "retention.xlsx"), [90.0] * 20 + [g] * 80)
        ma_goi = "K1-%04d" % so
        _ghi(hv.duong_tep_ho_so(goc, K, ma_goi), {"ma_goi": ma_goi, "video_id": vid})
        runs.append({"ma_luot": "%04d" % so, "ban_giao": {"ma_goi": ma_goi},
                     "nguon": {"nguon": "vph", "link": "https://youtu.be/SRC0000000%d" % so,
                               "tieu_de": "nguồn %d" % so}})
    _ghi(os.path.join(kd, "tu-chay", "2026-09-29.json"), {"runs": runs})
    loi_thoai.ghi(goc, K, "SRC00000003", text="mở đầu nguồn ba " * 40)
    dt = {d["video_id"]: d for d in bh.diem_thoat(goc, K)}
    assert dt["AAAAAAAAAA1"]["nhom"] == "roi_som" and dt["AAAAAAAAAA3"]["nhom"] == "giu_tot"
    assert dt["AAAAAAAAAA2"]["nhom"] == ""
    assert dt["AAAAAAAAAA3"]["nguon"]["ma"] == "SRC00000003" and dt["AAAAAAAAAA3"]["giu_2p"] == 60.0
    khoi = bh.khoi_nguon_giu_roi(goc, K)
    assert "[GIỮ TỐT]" in khoi and "[RƠI SỚM]" in khoi and "nguồn 3" in khoi
    mo_dau = khoi.split("mở đầu lời thoại nguồn: “", 1)[1].split("”", 1)[0]
    assert mo_dau.startswith("mở đầu nguồn ba") and len(mo_dau) <= 300
    # bài học có số theo kênh (n=3 → bơm được)
    gc = [b for b in bh.doc(goc, K, "kich_ban", tat_ca=True) if b["truc"] == "giu_chan" and not b["cum"]]
    assert gc and gc[0]["n"] == 3 and "45%" in gc[0]["cau"] and gc[0]["bom"]
