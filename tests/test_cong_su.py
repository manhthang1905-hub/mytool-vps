"""Cộng sự (21/10/2026): `core/cong_su.py` — kênh giả trong thư mục tạm, trang xem giả (không mạng, không Chrome)."""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from core import cong_su as cs  # noqa: E402

BAY = dt.datetime(2026, 10, 21, 10, 0)
KENH = ("KA", "KB", "KC", "KD", "KE", "KF", "KG")


def _uc(k: str) -> str:
    return "UC" + (k * 11)[:22]


def _csv(duong: Path, cot, hang) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(cot)
        w.writerows(hang)


def _goc(tmp_path: Path, video=(), kenh=KENH, chrome=None, ngay_dau=None) -> Path:
    """`video` = [(kenh, id, lúc công khai)] vào sổ máy đăng. `ngay_dau` = {kenh: ngày video đầu} (tuổi kênh)."""
    for k in kenh:
        d = tmp_path / "CHANNEL" / k
        d.mkdir(parents=True, exist_ok=True)
        (d / "kenh.yaml").write_text('ma: "{0}"\n'.format(k), encoding="utf-8")
        nd = (ngay_dau or {}).get(k, "2026-08-01")
        _csv(d / "chi-so" / "bang-tom-tat.csv", ["Tiêu đề", "Mã video", "Ngày đăng", "Lượt xem"],
             [["cũ", "old" + k + "xxxxxx"[:11 - 3 - len(k)], nd, "10"]])
    (tmp_path / "vm" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vm" / "logs" / "kenh-uc.json").write_text(json.dumps({k: _uc(k) for k in kenh}), encoding="utf-8")
    (tmp_path / "vm" / "config.json").write_text(json.dumps({"cac_kenh": [{"ma": k} for k in (chrome or kenh)]}),
                                                  encoding="utf-8")
    so = {"{0}/{0}-{1:04d}".format(k, i): {"video_id": v, "trang_thai": "xac-nhan", "lich": luc.strftime("%d/%m/%Y %H:%M")}
          for i, (k, v, luc) in enumerate(video)}
    (tmp_path / "vm" / "logs" / "so-video-id.json").write_text(json.dumps(so), encoding="utf-8")
    return tmp_path


def _tai(view: dict):
    """Trang xem giả: `view` = {video_id: số} ; id lạ → 404."""
    goi = []

    def tai(url):
        goi.append(url)
        vid = url.split("v=")[1][:11]
        if vid not in view:
            return 404, b""
        html = '{"videoDetails":{"videoId":"%s","viewCount":"%d","author":"x"}}' % (vid, view[vid])
        return 200, html.encode()
    tai.goi = goi
    return tai


@pytest.fixture(autouse=True)
def _khong_nao(monkeypatch):
    monkeypatch.setattr(cs, "ho_so_kenh", lambda goc, k, bay: {"sub": {"KA": 900, "KB": 50, "KC": 400, "KD": 10,
                                                                         "KE": 700, "KF": 300, "KG": 999}.get(k, 0),
                                                                "tuoi_ngay": {"KD": 5, "KF": 10}.get(k, 90)})
    monkeypatch.setattr(cs, "vung_video", lambda goc, vid, td, ds: "")


# ── thuần ──────────────────────────────────────────────────────────────────

def test_doc_trang_xem_va_gio_dang():
    h = ('{"videoDetails":{"videoId":"abcdefghijk","viewCount":"25013"}} ... "viewCount":"9" '
         '"publishDate":"2026-10-20T22:00:27-07:00"')
    d = cs.doc_trang_xem(h)
    assert d["view"] == 25013
    assert d["dang_luc_utc"] == dt.datetime(2026, 10, 21, 5, 0, 27)
    assert cs.doc_trang_xem("không có gì") == {"view": None, "dang_luc_utc": None}


def test_xep_uu_tien_vung_roi_kenh_moi_roi_xa_ypp():
    hs = {"KA": {"sub": 900, "tuoi_ngay": 90}, "KB": {"sub": 50, "tuoi_ngay": 90}, "KD": {"sub": 10, "tuoi_ngay": 5},
          "KE": {"sub": 700, "tuoi_ngay": 90}}
    ra = [x["kenh"] for x in cs.xep_uu_tien(["KA", "KB", "KD", "KE"], {"KE": 2, "KA": 1}, hs)]
    assert ra == ["KE", "KA", "KD", "KB"]


def test_chia_dot_co_dinh_va_can_bang():
    ds = ["KB", "KC", "KD", "KE", "KF"]
    a = cs.chia_dot(ds, "vid00000001")
    assert a == cs.chia_dot(ds, "vid00000001")          # có định
    for i in range(0, 4, 2):                             # mỗi cặp một A một B
        assert {a[ds[i]], a[ds[i + 1]]} == {"A", "B"}
    assert set(a) == set(ds) and "A" in a.values()


def _trang_xem_cong_tac(chu: str, cong_su=(), de_xuat=()) -> str:
    """Khuôn đo 21/10/2026: hộp «コラボレーター» nằm trong videoOwnerRenderer; video đề xuất có hộp riêng."""
    muc = ",".join('{"listItemViewModel":{"title":{"content":"x"},"rendererContext":{"commandContext":{"onTap":'
                   '{"innertubeCommand":{"browseEndpoint":{"browseId":"%s"}}}}}}}' % u for u in (chu,) + tuple(cong_su))
    khoi = ('"videoOwnerRenderer":{"navigationEndpoint":{"showDialogCommand":{"panelLoadingStrategy":{"inlineContent":'
            '{"dialogViewModel":{"header":{"dialogHeaderViewModel":{"headline":{"content":"コラボレーター"}}},'
            '"customContent":{"listViewModel":{"listItems":[%s]}}}}}}},"title":{"runs":[{"text":"a}b"}]}}' % muc)
    de = ",".join('{"avatarStackViewModel":{"x":{"browseEndpoint":{"browseId":"%s"}}}}' % u for u in de_xuat)
    return '{"a":1,' + khoi + ',"secondaryResults":[' + de + "]}"


def test_uc_ghi_cong_chi_doc_khoi_chu_video():
    goc_uc, cs_uc, de_xuat = "UC" + "a" * 22, "UC" + "b" * 22, "UC" + "c" * 22
    assert cs.uc_ghi_cong(_trang_xem_cong_tac(goc_uc, [cs_uc], [de_xuat])) == [goc_uc, cs_uc]
    assert cs.uc_ghi_cong("không có gì") == []


def test_doc_handle():
    h = '{"channelMetadataRenderer":{"vanityChannelUrl":"http://www.youtube.com/@%E3%81%82-x1"}}'
    assert cs.doc_handle(h) == "@あ-x1"


# ── quét + lập lô ──────────────────────────────────────────────────────────

def test_quet_lap_lo_moi_kenh_tru_nguon_tran_va_hai_dot(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=30)),
                                ("KC", "vidCCCCCCCC", BAY - dt.timedelta(hours=10)),
                                ("KE", "vidEEEEEEEE", BAY - dt.timedelta(hours=60))],
               chrome=[k for k in KENH if k != "KG"])
    tai = _tai({"vidAAAAAAAA": 20001, "vidCCCCCCCC": 19999, "vidEEEEEEEE": 90000})
    kq = cs.quet(str(goc), BAY, tai=tai)
    assert [m["video_id"] for m in kq["lo_moi"]] == ["vidAAAAAAAA"]   # C dưới ngưỡng, E quá 48 giờ
    assert not any("vidEEEEEEEE" in u for u in tai.goi)               # video quá cửa sổ: không tốn lượt mạng
    m = cs.doc_hang(str(goc))[0]
    nguoi = {n["kenh"]: n for n in m["nguoi_moi"]}
    assert "KA" not in nguoi                                           # không mời chính mình
    assert nguoi["KG"]["trang_thai"] == cs.TT_BO_QUA and "Chrome" in nguoi["KG"]["ly_do"]
    co_dot = [n for n in m["nguoi_moi"] if n.get("dot")]
    assert len(co_dot) == 5                                            # trần YouTube mặc định
    assert [n["kenh"] for n in co_dot][:2] == ["KD", "KF"]             # kênh mới trước
    assert {n["dot"] for n in co_dot} == {"A", "B"}
    for n in co_dot:
        han = dt.datetime.strptime(n["han_moi"], "%Y-%m-%d %H:%M:%S")
        assert han == (BAY if n["dot"] == "A" else BAY + dt.timedelta(hours=24))
    assert cs.quet(str(goc), BAY + dt.timedelta(hours=1), tai=tai)["lo_moi"] == []     # không lập lô trùng


def test_quet_thu_khong_ghi(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    kq = cs.quet(str(goc), BAY, tai=_tai({"vidAAAAAAAA": 50000}), thu=True)
    assert len(kq["lo_moi"]) == 1 and cs.doc_hang(str(goc)) == []
    assert not os.path.exists(os.path.join(str(goc), cs.THU_MUC, cs.TEP_QUET))


def test_mot_lo_moi_kenh_nguon_moi_ngay(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAA1", BAY - dt.timedelta(hours=3)),
                                ("KA", "vidAAAAAAA2", BAY - dt.timedelta(hours=20))])
    kq = cs.quet(str(goc), BAY, tai=_tai({"vidAAAAAAA1": 50000, "vidAAAAAAA2": 60000}))
    assert len(kq["lo_moi"]) == 1 and kq["bo"] and "hôm nay" in kq["bo"][0]["ly_do"]


def test_ngoai_san_khong_lam(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    (goc / "workspace").mkdir(exist_ok=True)
    (goc / "workspace" / "cai-dat.json").write_text(json.dumps({"cong_su": {"bat": False}}), encoding="utf-8")
    assert cs.quet(str(goc), BAY, tai=_tai({"vidAAAAAAAA": 50000}))["lo_moi"] == []
    assert cs.can_quet(str(goc), BAY)[0] is False


# ── việc DOM + trần ngày ───────────────────────────────────────────────────

def _lo(goc, bay=BAY, view=30000):
    cs.quet(str(goc), bay, tai=_tai({"vidAAAAAAAA": view}))
    return cs.doc_hang(str(goc))[0]


def test_viec_dom_dot_a_ngay_dot_b_sau_24h_va_tran_ngay(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    m = _lo(goc)
    v = cs.viec_dom(str(goc), BAY)
    a = [n["kenh"] for n in m["nguoi_moi"] if n.get("dot") == "A"]
    assert [x["viec"] for x in v] == ["moi"] and [n["kenh"] for n in v[0]["nguoi"]] == a
    v2 = cs.viec_dom(str(goc), BAY + dt.timedelta(hours=25))
    assert len(v2[0]["nguoi"]) == 5
    v3 = cs.viec_dom(str(goc), BAY, cai=dict(cs.CAI_DAT_MAC_DINH, toi_da_moi_ngay=1))
    assert len(v3[0]["nguoi"]) == 1


def test_trang_thai_moi_nhan_va_tu_kiem_qua_48h_thu_lai_mot_lan(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    m = _lo(goc)
    k = next(n["kenh"] for n in m["nguoi_moi"] if n.get("dot") == "A")
    cs.cap_nhat_nguoi(str(goc), m["id"], k, trang_thai=cs.TT_DA_MOI, luc_moi=cs._luc(BAY), link="https://x")
    v = [x for x in cs.viec_dom(str(goc), BAY) if x["viec"] == "nhan"]
    assert v and v[0]["kenh"] == k and v[0]["link"] == "https://x"
    tk = [x for x in cs.muc_tu_kiem(str(goc), BAY + dt.timedelta(hours=49), tai=_tai({})) if k in x["khoa"]]
    assert tk[0]["tt"] == "hong" and tk[0]["thu_lai"] == "cong_su"
    ok, _ = cs.thu_lai_nhan(str(goc), m["id"], k)
    assert ok
    ok2, ly = cs.thu_lai_nhan(str(goc), m["id"], k)
    assert not ok2 and "đã thử" in ly


def test_xac_minh_cong_khai_ghi_trang_thai(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    m = _lo(goc)
    k = next(n["kenh"] for n in m["nguoi_moi"] if n.get("dot") == "A")
    cs.cap_nhat_nguoi(str(goc), m["id"], k, trang_thai=cs.TT_DA_NHAN, luc_nhan=cs._luc(BAY))

    def tai(url):
        return 200, _trang_xem_cong_tac(_uc("KA"), [_uc(k)]).encode()
    tk = [x for x in cs.muc_tu_kiem(str(goc), BAY + dt.timedelta(hours=1), tai=tai) if k in x["khoa"]]
    assert tk[0]["tt"] == "dat"
    n = next(n for n in cs.doc_hang(str(goc))[0]["nguoi_moi"] if n["kenh"] == k)
    assert n["trang_thai"] == cs.TT_XAC_MINH


def test_dung_khan_chan_dom_va_bao_nguoi(tmp_path):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    _lo(goc)
    assert cs.can_dom(str(goc), BAY)[0] is True
    cs.dat_dung(str(goc), "hộp hạn chế cộng tác", kenh="KA")
    assert cs.can_dom(str(goc), BAY)[0] is False
    tk = cs.muc_tu_kiem(str(goc), BAY, tai=_tai({}))
    assert tk[0]["khoa"] == "cong_su:dung" and tk[0]["nguoi"]


def test_gio_cam():
    cai = cs.CAI_DAT_MAC_DINH
    assert cs.trong_gio_cam(dt.datetime(2026, 10, 21, 3, 0), cai)
    assert cs.trong_gio_cam(dt.datetime(2026, 10, 21, 19, 30), cai)
    assert not cs.trong_gio_cam(dt.datetime(2026, 10, 21, 10, 0), cai)


# ── đo ────────────────────────────────────────────────────────────────────

def test_do_hieu_qua_a_so_b(tmp_path, monkeypatch):
    goc = _goc(tmp_path, video=[("KA", "vidAAAAAAAA", BAY - dt.timedelta(hours=3))])
    m = _lo(goc)
    for n in m["nguoi_moi"]:
        if n.get("dot") == "A":
            cs.cap_nhat_nguoi(str(goc), m["id"], n["kenh"], trang_thai=cs.TT_DA_NHAN,
                              luc_nhan=cs._luc(BAY + dt.timedelta(hours=16)))
        elif n.get("dot") == "B":
            cs.cap_nhat_nguoi(str(goc), m["id"], n["kenh"], trang_thai=cs.TT_DA_NHAN,
                              luc_nhan=cs._luc(BAY + dt.timedelta(hours=40)))
    a = {n["kenh"] for n in m["nguoi_moi"] if n.get("dot") == "A"}
    ngay_a = (BAY + dt.timedelta(hours=2)).date()

    def chuoi(goc_, kenh, metric):
        ra = {}
        for i in range(-10, 12):
            d = ngay_a + dt.timedelta(days=i)
            ra[d.isoformat()] = 100.0 * (2.0 if (kenh in a and i >= 0) else 1.0)
        return ra
    monkeypatch.setattr(cs, "_chuoi", chuoi)
    assert cs.do_hieu_qua(str(goc), BAY + dt.timedelta(days=3)) == []          # chưa đủ ngày
    vua = cs.do_hieu_qua(str(goc), BAY + dt.timedelta(days=11))
    assert len(vua) == 1
    do = cs.doc_hang(str(goc))[0]["do_sau"]
    assert do["a_b"]["view"]["nang"] == pytest.approx(1.0)
    assert do["ket"] == "nang_ro"
    assert cs.do_hieu_qua(str(goc), BAY + dt.timedelta(days=12)) == []          # không đo lại
