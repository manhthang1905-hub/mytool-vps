"""Mục lục 6–10 chương, tên chương là Ý NỘI DUNG — kiểm toán chất lượng 09/10/2026.

`workspace/chan-doan/chat-luong-2026-10-09.md`: có lượt 35 chương, có lượt 21 chương kèm chương tự giới
thiệu và chương quảng bá kênh; video thắng 6–11 chương, tên ngắn. Bài kiểm chốt:
  1. Nhiều phần hơn trần → GỘP phần kề (không cắt cụt), vẫn đúng luật YouTube.
  2. Nhãn dự phòng (không AI): ngắn, không chào/tự giới thiệu/quảng bá/tên kênh, không trùng.
  3. AI (giả) chọn chỗ gộp + đặt tên; nhãn AI sai luật thì thay riêng nhãn đó; AI hỏng → dự phòng.
  4. Cất `3-muc-luc.json`: đường SRT và đường `2-phan.json` ra CÙNG bộ chương, chỉ gọi AI một lần.
  5. Luật mở đầu kịch bản + luật mềm độ dài tiêu đề có trong lời nhắc, kênh tắt/đổi được.
"""

from __future__ import annotations

import json
import os

from core import muc_luc_chuong as mlc
from core.muc_luc_chuong import (CAM_NHAN, TEP_CACHE, chot_chuong, gop_theo_do_dai, nhan_du_phong,
                                 nhan_hop_le)


def _phan_nhieu(n: int = 35, tong: float = 1200.0):
    buoc = tong / n
    ra = [(0.0, "夜中にふと目が覚める", "夜中にふと目が覚める。理由はわからない。")]
    for i in range(1, n):
        ra.append((round(i * buoc, 1), "第{0}の話題について考えます".format(i),
                   "第{0}の話題について考えます。ここでは具体例を挙げます。".format(i)))
    return ra


def _nhan(dong):
    return [x.split(" ", 1)[1] for x in dong]


def _giay(dong):
    out = []
    for x in dong:
        p = [int(v) for v in x.split(" ", 1)[0].split(":")]
        out.append(p[-1] + 60 * p[-2] + (3600 * p[0] if len(p) == 3 else 0))
    return out


# ── 1. Gộp ──────────────────────────────────────────────────────────────────

def test_35_phan_gop_con_6_den_10_chuong_dung_luat_youtube():
    muc = chot_chuong(_phan_nhieu(), 1200.0, ngon_ngu="ja")
    assert 6 <= len(muc) <= 10
    g = _giay(muc)
    assert g[0] == 0 and all(b - a >= 10 for a, b in zip(g, g[1:])) and 1200 - g[-1] >= 10
    nh = _nhan(muc)
    assert len(set(nh)) == len(nh)
    assert all(5 <= len(x) <= 22 for x in nh)


def test_it_phan_giu_nguyen_khong_gop():
    phan = _phan_nhieu(7, 900.0)
    assert len(chot_chuong(phan, 900.0, ngon_ngu="ja")) == 7


def test_gop_theo_do_dai_gop_phan_ngan_va_uu_tien_tu_noi():
    t = [0, 5, 60, 120, 125, 300]          # phần 1 (5 s) < 10 s, phần 4 cách phần 3 có 5 s
    assert gop_theo_do_dai(t, 400.0) == [0, 2, 3, 5]
    # 12 phần đều nhau, trần 6: phần mở bằng từ nối (つまり) bị dán vào phần trước trước tiên.
    t = [i * 60.0 for i in range(12)]
    mo = ["x"] * 12
    mo[5] = "つまり、こういうことです"
    dau = gop_theo_do_dai(t, 720.0, mo, toi_da=6)
    assert len(dau) == 6 and 5 not in dau and dau[0] == 0


def test_duoi_3_chuong_tra_rong():
    assert chot_chuong([(0.0, "a", "a"), (60.0, "b", "b")], 120.0) == []


# ── 2. Nhãn dự phòng ────────────────────────────────────────────────────────

def test_nhan_du_phong_bo_chao_tu_gioi_thieu_quang_ba_ten_kenh():
    phan = [
        (0.0, "会議が終わった後、その人だけが残って椅子を静かに戻していました",
         "会議が終わった後、その人だけが残って椅子を静かに戻していました。"),
        (56.0, "テスト回廊へようこそ", "テスト回廊へようこそ。今日は存在感の正体を探ります。"),
        (130.0, "二つ目は言葉です", "二つ目は言葉です。話し方に全てが出ます。"),
        (400.0, "テスト回廊ではこれからも人間の奥を照らしていきます",
         "テスト回廊ではこれからも人間の奥を照らしていきます。チャンネル登録お願いします。"),
    ]
    muc = chot_chuong(phan, 460.0, ngon_ngu="ja", cam_them=("テスト回廊",))
    nh = _nhan(muc)
    # Phần cuối chỉ toàn quảng bá kênh + xin đăng ký → không thành chương riêng (dán vào phần trước).
    assert len(muc) == 3 and _giay(muc)[-1] == 130
    for x in nh:
        assert "ようこそ" not in x and "テスト回廊" not in x and "登録" not in x, x
        assert 5 <= len(x) <= 22
    assert nh[1] == "今日は存在感の正体を探ります"
    assert len(set(nh)) == 3


def test_nhan_du_phong_khong_trung_va_co_duong_lui_cuoi():
    da = ["二つ目は言葉です"]
    n = nhan_du_phong("二つ目は言葉です", "二つ目は言葉です。", "ja", da, 3)
    assert n != "二つ目は言葉です" and nhan_hop_le(n, "ja", da)
    assert nhan_du_phong("ようこそ", "チャンネル登録お願いします。", "ja", [], 2) == "第2章"


def test_nhan_hop_le_luat():
    assert nhan_hop_le("睡眠が脳を変える理由", "ja")
    assert not nhan_hop_le("人生の羅針盤へようこそ", "ja")
    assert not nhan_hop_le("あ" * 23, "ja")
    assert not nhan_hop_le("睡眠", "ja")
    assert not nhan_hop_le("睡眠が脳を変える理由", "ja", ["睡眠が脳を変える理由"])
    assert not nhan_hop_le("Welcome back to the channel", "en")
    assert nhan_hop_le("Why sleep rewires the brain", "en")
    assert "チャンネル登録" in "".join(CAM_NHAN) or "登録" in CAM_NHAN


# ── 3. AI (giả) ─────────────────────────────────────────────────────────────

class _AI:
    def __init__(self, tra):
        self.tra, self.goi, self.loi_nhac = tra, 0, []

    def __call__(self, loi_nhac, khoa_phu):
        self.goi += 1
        self.loi_nhac.append(loi_nhac)
        if isinstance(self.tra, Exception):
            raise self.tra
        return self.tra if isinstance(self.tra, str) else self.tra(loi_nhac)


def _tra_ai(ds):
    return "```json\n" + json.dumps({"chuong": [{"phan": p, "nhan": n} for p, n in ds]},
                                    ensure_ascii=False) + "\n```"


def test_ai_gop_va_dat_ten_cat_vao_tep(tmp_path):
    ds = [(1, "目が覚める夜の不安"), (5, "最初の習慣：歩く"), (10, "睡眠が記憶を整える"),
          (15, "学び続ける脳"), (20, "読書という借り物の経験"), (25, "人と話す効能"), (30, "五つをつなぐ答え")]
    ai = _AI(_tra_ai(ds))
    muc = chot_chuong(_phan_nhieu(), 1200.0, goi_ai=ai, thu_muc=str(tmp_path), ngon_ngu="ja")
    assert _nhan(muc) == [n for _p, n in ds]
    assert _giay(muc)[1] == int(4 * 1200 / 35)
    assert ai.goi == 1
    lo = ai.loi_nhac[0]
    assert "GỘP" in lo and "KHÔNG chào hỏi" in lo and "8–22 ký tự" in lo
    cache = json.load(open(os.path.join(str(tmp_path), TEP_CACHE), encoding="utf-8"))
    assert list(cache.values())[0]["nguon"] == "ai"
    # Lần sau (đường khác / chạy lại): đọc tệp cất, KHÔNG gọi AI.
    hong = _AI(RuntimeError("không được gọi"))
    assert chot_chuong(_phan_nhieu(), 1200.0, goi_ai=hong, thu_muc=str(tmp_path), ngon_ngu="ja") == muc
    assert hong.goi == 0


def test_ai_nhan_sai_luat_thay_rieng_nhan_do():
    phan = _phan_nhieu(5, 600.0)
    ds = [(1, "テスト回廊へようこそ"), (2, "あ" * 40), (3, "睡眠の話"), (4, "睡眠の話"), (5, "最後のまとめ")]
    muc = chot_chuong(phan, 600.0, goi_ai=_AI(_tra_ai(ds)), ngon_ngu="ja", cam_them=("テスト回廊",))
    nh = _nhan(muc)
    assert len(nh) == 5 and nh[2] == "睡眠の話" and nh[4] == "最後のまとめ"
    assert "ようこそ" not in nh[0] and len(nh[1]) <= 22 and nh[3] != "睡眠の話"


def test_ai_hong_thi_du_phong_lan_sau_thu_lai_ai(tmp_path):
    d = str(tmp_path)
    muc1 = chot_chuong(_phan_nhieu(), 1200.0, goi_ai=_AI(RuntimeError("502")), thu_muc=d, ngon_ngu="ja")
    assert 6 <= len(muc1) <= 10
    cache = json.load(open(os.path.join(d, TEP_CACHE), encoding="utf-8"))
    assert list(cache.values())[0]["nguon"] == "du_phong"
    ds = [(1, "目が覚める夜の不安"), (12, "習慣を変える一歩"), (24, "続ける仕組み"), (30, "答え合わせ")]
    ai = _AI(_tra_ai(ds))
    muc2 = chot_chuong(_phan_nhieu(), 1200.0, goi_ai=ai, thu_muc=d, ngon_ngu="ja")
    assert ai.goi == 1 and _nhan(muc2) == [n for _p, n in ds]


def test_ai_json_sai_cau_truc_thu_lai_mot_lan_roi_du_phong():
    ai = _AI("không phải json")
    muc = chot_chuong(_phan_nhieu(), 1200.0, goi_ai=ai, ngon_ngu="ja")
    assert ai.goi == 2 and 6 <= len(muc) <= 10
    # Ít phần (≤ trần) mà AI tự gộp → sai luật "mỗi phần một chương" → dự phòng.
    ai2 = _AI(_tra_ai([(1, "目が覚める夜"), (3, "習慣を変える"), (5, "続ける仕組み")]))
    assert len(chot_chuong(_phan_nhieu(6, 600.0), 600.0, goi_ai=ai2, ngon_ngu="ja")) == 6


# ── 4. Hai đường, một bộ chương ─────────────────────────────────────────────

def _srt(*cau):
    return "\n\n".join("{0}\n{1} --> {2}\n{3}".format(i, a, b, c) for i, (a, b, c) in enumerate(cau, 1)) + "\n"


SRT = _srt(
    ("00:00:00,180", "00:00:05,000", "夜の部屋に、小さな明かり。"),
    ("00:00:58,000", "00:01:05,000", "--- 一つ目は、予測できない愛情です。"),
    ("00:03:31,000", "00:03:32,000", "--- では、"),
    ("00:03:32,660", "00:03:40,000", "この防衛は日常でどんな姿になるのでしょう。"),
    ("00:13:26,000", "00:13:40,000", "--- あなたは、壊れてなどいません。"),
    ("00:14:50,000", "00:14:58,000", "最後まで、ありがとう。"),
)


def test_duong_srt_va_duong_2_phan_cung_bo_chuong_mot_lan_ai(tmp_path):
    from core.auto_khau import _muc_luc_tu_srt
    from core.phan_video import KeHoach, RanhGioi, bang_bu, muc_luc

    d = str(tmp_path)
    ai = _AI(_tra_ai([(1, "夜の部屋の小さな明かり"), (2, "予測できない愛情"), (3, "日常に出る防衛"),
                      (4, "壊れていないあなたへ")]))
    a = _muc_luc_tu_srt(SRT, goi_ai=ai, thu_muc=d, ngon_ngu="ja")
    ranh = [RanhGioi(57.5, 58.9), RanhGioi(210.5, 211.8), RanhGioi(805.4, 806.6)]
    kh = KeHoach(tong_giong=900.0, ranh=ranh, bu=bang_bu(ranh, 3.0), giay_nghi=3.0)
    b = muc_luc(kh, SRT, lam_sach=True, goi_ai=ai, thu_muc=d, ngon_ngu="ja")
    assert ai.goi == 1, "đường thứ hai đọc tệp cất, không gọi AI lần nữa"
    assert _nhan(a) == _nhan(b) == ["夜の部屋の小さな明かり", "予測できない愛情", "日常に出る防衛", "壊れていないあなたへ"]
    assert _giay(b)[1] == 59, "mốc theo trục của đường 2-phan (giữa khoảng nghỉ)"


def test_tuy_chon_muc_luc_goi_ai_bac_giua(tmp_path):
    from core.auto_khau import BoiCanh, _tuy_chon_muc_luc
    from core.kenh import Kenh

    goi = []

    def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=0, **_k):
        goi.append((mo_hinh, khoa, toi_da_token))
        return _tra_ai([(1, "目が覚める夜の不安"), (2, "習慣を変える一歩"), (3, "続ける仕組み")])

    k = Kenh(ma="TLX", ten="テスト回廊", ngon_ngu="ja", mo_hinh="claude-opus-x", chuong_toi_da=8)
    bc = BoiCanh(goc=str(tmp_path), kenh=k, goi_chat=goi_chat, ngu=lambda s: None)
    d = os.path.join(str(tmp_path), "TLX", "0001")
    os.makedirs(d)
    tc = _tuy_chon_muc_luc(bc, d)
    assert tc["toi_da"] == 8 and tc["cam_them"] == ("テスト回廊",) and tc["thu_muc"] == d
    muc = chot_chuong(_phan_nhieu(3, 300.0), 300.0, **tc)
    assert len(muc) == 3 and goi and goi[0][0] == mlc.MO_HINH_NHAN and "muc-luc" in goi[0][1]
    # Đồ giả không có goi_chat → không gọi AI.

    class _BC:
        kenh = k

        def ghi(self, _s):
            pass

    assert _tuy_chon_muc_luc(_BC(), d)["goi_ai"] is None


# ── 5. Lời nhắc ─────────────────────────────────────────────────────────────

def test_luat_mo_dau_trong_loi_nhac_va_kenh_tat_duoc():
    from core.auto_khau import luat_mo_dau, them_luat_mo_dau
    from core.kenh import Kenh

    k = Kenh(ngon_ngu="ja", ky_tu_moi_phut=300)
    ra = them_luat_mo_dau("Viết kịch bản.\n<<COMPETITOR_TRANSCRIPT>>", k)
    assert ra.startswith("Viết kịch bản.\n═══ LUẬT MỞ ĐẦU") and ra.endswith("\n<<COMPETITOR_TRANSCRIPT>>")
    for cum in ("KHÔNG chào hỏi", "KHÔNG tự giới thiệu", "KHÔNG xin đăng ký", "MÓC", "60 giây", "~300 ký tự",
                "đoạn KẾT"):
        assert cum in ra, cum
    # Luật nằm TRƯỚC khối dữ liệu (cả dòng nhãn "…:"), bản nháp vẫn là thứ cuối cùng của lời nhắc.
    ht = them_luat_mo_dau("hoàn thiện bài.\n\nkịch bản gốc:\n\n<<COMPETITOR_TRANSCRIPT>>\n\ncần sửa:\n\n<<DRAFT>>", k)
    assert ht.endswith("<<DRAFT>>") and ht.index("LUẬT MỞ ĐẦU") < ht.index("kịch bản gốc:")
    assert ht.startswith("hoàn thiện bài.")
    # Không có ô dữ liệu → nối cuối.
    assert them_luat_mo_dau("Viết.", k).startswith("Viết.\n\n═══ LUẬT MỞ ĐẦU")
    # Ô đặt sẵn → luật nằm đúng chỗ, không nối cuối.
    o = them_luat_mo_dau("A\n<<LUAT_MO_DAU>>\nB", k)
    assert o.index("LUẬT MỞ ĐẦU") < o.index("\nB")
    # Kênh đổi số giây / tắt hẳn; lời nhắc rỗng (bước tắt) giữ rỗng.
    assert "45 giây" in luat_mo_dau(Kenh(giay_mo_dau_toi_da=45, ky_tu_moi_phut=300))
    assert them_luat_mo_dau("Viết.", Kenh(luat_mo_dau=False)) == "Viết."
    assert them_luat_mo_dau("", k) == ""


def test_luat_mo_dau_vao_ca_buoc_viet_hoan_thien_va_hook():
    import inspect

    from core import auto_khau

    src = inspect.getsource(auto_khau)
    assert "khuon = them_luat_mo_dau(khuon, k)" in src
    assert 'them_luat_mo_dau(k.prompt.get("2c-hoan-thien.md", ""), k)' in src
    assert 'them_luat_mo_dau(k.prompt.get("2d-hook.md", ""), k)' in src


def test_kenh_yaml_doc_khoa_moi(tmp_path):
    from core.kenh import doc_kenh, duong_kenh

    d = duong_kenh(str(tmp_path), "TLX")
    os.makedirs(d)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('ma: TLX\nngon_ngu: ja\nluat_mo_dau: false\ngiay_mo_dau_toi_da: 45\n'
                'tieu_de_ky_tu: "30-40"\nchuong_toi_da: 8\n')
    k = doc_kenh(str(tmp_path), "TLX")
    assert (k.luat_mo_dau, k.giay_mo_dau_toi_da, k.tieu_de_ky_tu, k.chuong_toi_da) == (False, 45, "30-40", 8)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write("ma: TLX\nngon_ngu: ja\n")
    k = doc_kenh(str(tmp_path), "TLX")
    assert (k.luat_mo_dau, k.giay_mo_dau_toi_da, k.tieu_de_ky_tu, k.chuong_toi_da) == (True, 60, "", 10)


def test_luat_mem_do_dai_tieu_de():
    from core.auto_khau import _de_bai_n_ban_tieu_de, khoang_tieu_de, luat_do_dai_tieu_de
    from core.kenh import Kenh

    assert khoang_tieu_de(Kenh(ngon_ngu="ja")) == (28, 38)
    assert khoang_tieu_de(Kenh(ngon_ngu="en")) is None, "tiếng khác: không bịa số"
    assert khoang_tieu_de(Kenh(ngon_ngu="en", tieu_de_ky_tu="45-65")) == (45, 65)
    assert khoang_tieu_de(Kenh(ngon_ngu="ja", tieu_de_ky_tu="0")) is None
    assert khoang_tieu_de(Kenh(ngon_ngu="ja", tieu_de_ky_tu="tat")) is None
    luat = luat_do_dai_tieu_de(Kenh(ngon_ngu="ja"))
    assert "28–38 ký tự" in luat and "MỀM" in luat
    assert luat in _de_bai_n_ban_tieu_de("x", 4, "", luat)
    # Không truyền luật → lời nhắc cũ y nguyên từng byte.
    assert _de_bai_n_ban_tieu_de("x", 4, "") == _de_bai_n_ban_tieu_de("x", 4, "", "")
    assert "Độ dài TITLE" not in _de_bai_n_ban_tieu_de("x", 4, "")
