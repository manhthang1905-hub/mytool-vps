"""Vòng CHẤM TOÀN BÀI → VÁ vài bản → CHẤM SO (`core/vong_cham_sua.py`) — khoá bằng bài kiểm.

═══ VÌ SAO CÓ TỆP NÀY (09/09/2026) ═══

Lượt TL4-T7/0012: bộ chấm nhìn đúng chỗ, nhưng bản ghép cuối (hook mới + thân)
chưa bao giờ được chấm như MỘT bài — hook mới cắt mất nghịch lý + thuyết Savanna
mà chính bộ chấm bảo giữ; bản hoàn thiện bị mã vứt vì dài ×1,27 > 1,25 trước khi
bộ chấm kịp so. Chủ dự án: *"prompt càng đơn giản càng mở và có mục tiêu chính…
làm nhiều chọn ra cái hay — chấm sửa xong chấm lại vài lần cũng được"*.

Bốn nhóm bài dưới đây khoá bốn thứ:
1. Vòng dừng đúng lúc: bộ chấm nói giữ → dừng; hai vòng liền không hơn → dừng.
2. Bản vá chỉ được nhận khi CHÍNH bộ chấm chọn nó cạnh bản cũ; mã chỉ chặn
   "viết lại từ đầu", không chặn độ dài.
3. Hỏng ở đâu (chấm lỗi, vá lỗi) cũng trả về bản đang có — không bao giờ vỡ bài.
4. Lời nhắc của kênh + khuôn tâm-lý có đủ ô dữ liệu và KHÔNG dạy luật cứng;
   chữ bìa trùng video trước bị bắt; khối sự thật kênh đọc được tệp ghi tay.
"""

import io
import json
import os

import pytest

from core.vong_cham_sua import (GIU_CHU_VA, ap_dung_thay_doan, cham_toan_bai,
                                khoi_binh_luan, vong_cham_sua)

GOC = os.path.join(os.path.dirname(__file__), "..")


def _muc(nhan: str, thu_muc: str):
    """Một mục của `KENH` — tự SKIP (không FAIL) nếu thư mục không có trên đĩa.

    26/09/2026: VPS này đã xoá `CHANNEL/_KHUON/` và `CHANNEL/_MAU-GON/` (chủ dự
    án chốt: VPS chỉ cần các template TL1..TL4-T7 + TL4-T7-v2). Mục nào thiếu
    thư mục thì tự skip, không kéo cả nhóm bài tham số hoá xuống — TL4-T7-v2
    (kênh thật, đang dùng) vẫn phải kiểm bình thường.
    """
    return pytest.param(nhan, thu_muc, marks=pytest.mark.skipif(
        not os.path.isdir(thu_muc),
        reason="VPS không mang dữ liệu khuôn mẫu ({0} không tồn tại)".format(thu_muc)))


#: Hai bài so TL4-T7-v2 với TL4-T7 cũ cần CẢ HAI kênh thật — bản clone sạch / máy khác không có.
_CO_HAI_KENH_THAT = all(os.path.isfile(os.path.join(GOC, "CHANNEL", k, "kenh.yaml")) for k in ("TL4-T7", "TL4-T7-v2"))
_CAN_HAI_KENH_THAT = pytest.mark.skipif(not _CO_HAI_KENH_THAT,
                                        reason="không có kênh thật TL4-T7 / TL4-T7-v2 (bản clone sạch)")

#: Vòng này bật ở TL4-T7-v2 (bản thử lời nhắc). TL4-T7 cũ giữ nguyên dây chuyền cũ —
#: chủ dự án 09/09/2026: *"cập nhật cho TL4-T7-V2, TL4-T7 cũ cứ để như cũ"*.
KENH = [_muc("TL4-T7-v2", os.path.join(GOC, "CHANNEL", "TL4-T7-v2", "prompt")),
        _muc("khuôn tâm-lý", os.path.join(GOC, "CHANNEL", "_KHUON", "nganh",
                                          "tam-ly", "prompt")),
        _muc("bộ gọn", os.path.join(GOC, "CHANNEL", "_MAU-GON", "prompt"))]

GOC_DOI_THU = "一人の時間が長いほどストレスは低くなります。研究チームは二十一日間の日記を集めました。" * 3
BAN = "一人の夜、部屋の静けさが深く息をつかせる。" * 40
CAU_THEM = "心理学の研究では、知能の高い人ほど友人と会うほど満足度が下がるという逆説さえ出ています。"
BAN_VA = BAN[: len(BAN) // 2] + CAU_THEM + BAN[len(BAN) // 2:]
BAN_LA = "雨の音がガラスを伝って落ちていく。" * 45


def _json(**k):
    return json.dumps(k, ensure_ascii=False)


class _Ai:
    """Mỗi lượt gọi trả về mục kế tiếp; nhớ lời nhắc để kiểm. Mục là Exception
    thì ném; mục là hàm thì gọi với lời nhắc (bộ chấm "đọc" bài rồi mới chọn)."""

    def __init__(self, tra):
        self.tra = list(tra)
        self.nhan = []

    def __call__(self, loi_nhac, **_k):
        self.nhan.append(loi_nhac)
        r = self.tra.pop(0)
        if isinstance(r, Exception):
            raise r
        if callable(r):
            return r(loi_nhac)
        return r


def _nhan_cua(loi_nhac, chua):
    """Nhãn (A/B/C…) của bản trong lời nhắc có chứa `chua`; '' nếu không có.
    Các bản được XÁO thứ tự trước khi bày (`thu_tu_cham`), nên bộ chấm giả phải
    đọc lời nhắc thay vì tin bản cũ luôn là A."""
    for khoi in loi_nhac.split("=== BẢN ")[1:]:
        nhan, _, than = khoi.partition(" ===")
        if chua in than.replace("\n", ""):
            return nhan.strip()
    return ""


def chon_ban_co(chua, **them):
    """Bộ chấm so giả: chọn bản có `chua` (bản vá); không có → A."""
    def _cham(loi_nhac):
        nhan = _nhan_cua(loi_nhac, chua) or "A"
        ket = {"chon": nhan}
        if "ban_do_rot" in them:
            ket["ban_do_rot"] = {nhan: them["ban_do_rot"]}
        return _json(**ket)
    return _cham


def chon_ban_khong_co(chua):
    """Bộ chấm so giả: vẫn thích bản cũ (bản KHÔNG chứa `chua`)."""
    def _cham(loi_nhac):
        for khoi in loi_nhac.split("=== BẢN ")[1:]:
            nhan, _, than = khoi.partition(" ===")
            if chua not in than.replace("\n", ""):
                return _json(chon=nhan.strip())
        return _json(chon="A")
    return _cham


# ── 1. Dừng đúng lúc ─────────────────────────────────────────────────────────

class TestDung:
    def test_bo_cham_noi_giu_thi_dung_ngay_khong_va(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="giữ", cho_kem_nhat="")])
        va = _Ai([])
        ban, bien_ban, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=3)
        assert ban == BAN
        assert len(cham.nhan) == 1 and not va.nhan
        assert "giữ" in bien_ban

    def test_hai_vong_lien_khong_hon_thi_dung(self):
        # chấm: sửa · so: chọn cũ · chấm: sửa · so: chọn cũ → dừng (không tới vòng 3)
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="đoạn 2 khô"),
                    chon_ban_khong_co(CAU_THEM),
                    _json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="đoạn 2 khô"),
                    chon_ban_khong_co(CAU_THEM),
                    _json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="đoạn 2 khô")])
        va = _Ai([BAN_VA] * 6)
        ban, bien_ban, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=3, so_ban_va=2)
        assert ban == BAN
        assert len(cham.nhan) == 4, "2 chấm + 2 so, không có vòng 3"
        assert "hai vòng không hơn" in bien_ban

    def test_toi_da_so_vong(self):
        # mỗi vòng đều nhận bản vá → chạy đúng so_vong vòng rồi thôi
        tra = []
        for _ in range(3):
            tra += [_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x"), chon_ban_co(CAU_THEM)]
        cham = _Ai(tra)
        va = _Ai([BAN_VA] * 6)
        ban, bien_ban, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=3, so_ban_va=2)
        assert ban == BAN_VA
        assert len(cham.nhan) == 6
        assert bien_ban.count("→ nhận") == 3


# ── 2. Cửa thật là bộ chấm so; mã chỉ chặn "viết lại từ đầu" ──────────────────

class TestNhanBanVa:
    def test_nhan_ban_va_khi_bo_cham_chon_no(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="thiếu nghịch lý",
                          mat_gi_cua_goc="con số nghiên cứu"),
                    chon_ban_co(CAU_THEM, ban_do_rot=[{"doan": "mở", "con_lai": 80}]),
                    _json(chon="A", giu_hay_sua="giữ")])
        va = _Ai([BAN_VA, BAN_VA])
        ban, bien_ban, bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=3, so_ban_va=2)
        assert ban == BAN_VA
        assert "nhận bản vá A" in bien_ban
        assert bd == [{"doan": "mở", "con_lai": 80}], "bản đồ rớt của bản cuối được trả về"
        # lời chê của bộ chấm phải tới tay bước vá, và bản đang có cũng vậy
        assert "thiếu nghịch lý" in va.nhan[0] and "con số nghiên cứu" in va.nhan[0]
        assert BAN in va.nhan[0]
        # chấm so phải thấy bản cũ VÀ các bản vá cạnh nhau
        assert "=== BẢN A ===" in cham.nhan[1] and "=== BẢN C ===" in cham.nhan[1]

    def test_ban_va_viet_lai_tu_dau_bi_bo_khong_can_bo_cham(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x")])
        va = _Ai([BAN_LA, BAN_LA])
        ban, bien_ban, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=3, so_ban_va=2)
        assert ban == BAN
        assert "bỏ bản vá" in bien_ban
        assert len(cham.nhan) == 1, "không có bản vá nào thì không tốn lượt chấm so"

    def test_khong_chan_do_dai_trong_khoang_rong(self):
        # bản vá dài ×1,4 (từng bị rào chắn 1,25 của bước hoàn thiện vứt) vẫn tới bộ chấm
        dai = BAN + CAU_THEM * 8
        assert 1.3 < len(dai) / len(BAN) < 1.6
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x"), chon_ban_co(CAU_THEM)])
        va = _Ai([dai])
        ban, _bb, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=1)
        assert ban == dai

    def test_don_chu_ai_tra_ve_truoc_khi_cham(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x"), chon_ban_co(CAU_THEM)])
        va = _Ai(["GHI CHÚ: đã sửa\n" + BAN_VA])
        ban, _bb, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=1,
                                     don=lambda c: c.split("\n", 1)[1])
        assert ban == BAN_VA

    def test_nguong_viet_lai(self):
        assert 0.3 <= GIU_CHU_VA <= 0.7

    def test_bay_cung_hinh_thuc_va_xao_thu_tu(self):
        """0001 trên v2: bộ chấm chê một câu, hai bản vá bỏ câu ấy, chấm so vẫn
        chọn "A" = bản cũ luôn đứng đầu. Nay: mọi bản bày mỗi câu một dòng, và
        thứ tự xáo theo nội dung (cùng đầu vào → cùng thứ tự)."""
        from core.vong_cham_sua import hien_de_cham, thu_tu_cham
        assert hien_de_cham("一人の夜。部屋の静けさ。\n\n深く息を。") == "一人の夜。\n部屋の静けさ。\n深く息を。"
        ba = ["x" * 50 + "。", "y" * 50 + "。", "z" * 50 + "。"]
        t = thu_tu_cham(ba)
        assert sorted(t) == [0, 1, 2] and t == thu_tu_cham(list(ba))
        # qua nhiều đầu vào khác nhau, bản đầu KHÔNG luôn ở vị trí A
        vi_tri_dau = {thu_tu_cham([s * 40 + "。", "b" * 40 + "。"])[0] for s in "abcdefghij"}
        assert vi_tri_dau == {0, 1}
        # chấm so: bộ chấm chọn theo NỘI DUNG (bản có câu thêm) dù nó ở vị trí nào
        cham = _Ai([chon_ban_co(CAU_THEM)])
        i, _ket = cham_toan_bai(cham, [BAN, BAN_VA], GOC_DOI_THU)
        assert i == 1
        nhan = _nhan_cua(cham.nhan[0], CAU_THEM)
        assert nhan in ("A", "B")


# ── 3. Không bao giờ vỡ bài ──────────────────────────────────────────────────

class TestKhongVo:
    def test_cham_hong_thi_giu_ban(self):
        cham = _Ai([RuntimeError("cổng lỗi")])
        ban, bien_ban, _bd = vong_cham_sua(cham, _Ai([]), BAN, GOC_DOI_THU)
        assert ban == BAN and "chấm hỏng" in bien_ban

    def test_cham_tra_json_lung_tung_thi_giu_ban(self):
        i, ket = cham_toan_bai(lambda _p: "tôi nghĩ bản này ổn", [BAN], GOC_DOI_THU)
        assert i == 0 and "loi" in ket

    def test_va_hong_mot_ban_van_di_tiep(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x"), chon_ban_co(CAU_THEM)])
        va = _Ai([RuntimeError("mạng"), BAN_VA])
        ban, _bb, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=2)
        assert ban == BAN_VA

    def test_bai_rong(self):
        ban, bien_ban, _bd = vong_cham_sua(_Ai([]), _Ai([]), "", GOC_DOI_THU)
        assert ban == "" and "rỗng" in bien_ban


# ── 4. Dữ liệu cho bộ chấm, lời nhắc, chữ bìa ─────────────────────────────────

class TestDuLieu:
    def test_khoi_binh_luan(self):
        k = khoi_binh_luan([(84, "多数派が正解とは限らない"), (0, "  "), (5, "x\ny")], toi_da=2)
        assert k.splitlines() == ["(84) 多数派が正解とは限らない", "(5) x y"]

    def test_binh_luan_va_su_that_di_vao_loi_nhac_cham(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="giữ")])
        vong_cham_sua(cham, _Ai([]), BAN, GOC_DOI_THU, chung={
            "BINH_LUAN_GOC": "(84) 多数派が正解とは限らない",
            "SU_THAT_KENH": "- V7: xem trung bình 28%",
            "PHUT": "13"})
        p = cham.nhan[0]
        assert "多数派が正解とは限らない" in p and "xem trung bình 28%" in p
        from core.vong_cham_sua import hien_de_cham
        assert GOC_DOI_THU in p and hien_de_cham(BAN) in p and "<<" not in p

    @pytest.mark.parametrize("nhan,thu_muc", KENH)
    def test_loi_nhac_kenh_du_o_va_khong_day_luat_cung(self, nhan, thu_muc):
        cham = io.open(os.path.join(thu_muc, "2g-cham-toan-bai.md"), encoding="utf-8").read()
        va = io.open(os.path.join(thu_muc, "2h-va-toan-bai.md"), encoding="utf-8").read()
        for o in ("<<SO_BAN>>", "<<PHUT>>", "<<COMPETITOR_TRANSCRIPT>>", "<<BINH_LUAN_GOC>>",
                  "<<SU_THAT_KENH>>", "<<CAC_BAN>>", "<<NGON_NGU>>"):
            assert o in cham, "{0}: thiếu ô {1} trong lời nhắc chấm".format(nhan, o)
        # Khán giả đi theo ô <<NGON_NGU>> của kênh — KHÔNG ghim tên một nước/tiếng,
        # để nhân bản kênh sang tiếng khác không phải sửa lẻ (chủ dự án 09/09/2026).
        for ghim in ("Nhật", "Japan", "Việt", "Hàn", "Anh", "日本"):
            assert ghim not in cham and ghim not in va, (
                "{0}: lời nhắc ghim cứng khán giả '{1}'".format(nhan, ghim))
        for o in ("<<CHO_KEM>>", "<<MAT_GI>>", "<<NGON_NGU>>", "<<COMPETITOR_TRANSCRIPT>>",
                  "<<DRAFT>>"):
            assert o in va, "{0}: thiếu ô {1} trong lời nhắc vá".format(nhan, o)
        for khoa in ("giu_hay_sua", "cho_kem_nhat", "mat_gi_cua_goc", "ban_do_rot"):
            assert khoa in cham
        # Lời nhắc nêu MỤC TIÊU, không đóng khung cách làm: không có mốc giây, không
        # có "ý 1 phải", không có danh sách từ cấm. Chủ dự án: prompt dài, cứng thì
        # content không hay.
        for cam in ("giây thứ", "10%", "từ cấm", "phải nằm", "không được dùng"):
            assert cam not in cham, "{0}: lời nhắc chấm đang dạy luật cứng: {1}".format(nhan, cam)
        assert len(cham) < 2500 and len(va) < 1200, "lời nhắc phải ngắn"

    @pytest.mark.parametrize("nhan,thu_muc", KENH)
    def test_loi_nhac_that_dien_kin_moi_o(self, nhan, thu_muc):
        """Chạy vòng bằng đúng lời nhắc của kênh: không ô `<<…>>` nào còn sót."""
        cham_md = io.open(os.path.join(thu_muc, "2g-cham-toan-bai.md"), encoding="utf-8").read()
        va_md = io.open(os.path.join(thu_muc, "2h-va-toan-bai.md"), encoding="utf-8").read()
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="đoạn 2 khô",
                          mat_gi_cua_goc="con số"), chon_ban_co(CAU_THEM)])
        va = _Ai([BAN_VA])
        ban, _bb, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, khuon_cham=cham_md,
                                     khuon_va=va_md, so_vong=1, so_ban_va=1,
                                     chung={"NGON_NGU": "tiếng Nhật", "PHUT": "13"})
        assert ban == BAN_VA
        for p in cham.nhan + va.nhan:
            assert "<<" not in p, "{0}: còn ô chưa điền: {1}".format(nhan, p[:200])
        assert GOC_DOI_THU in va.nhan[0] and "đoạn 2 khô" in va.nhan[0]

    @_CAN_HAI_KENH_THAT
    def test_v2_moi_bo_cham_sua_deu_nhan_du_lieu_khan_gia(self):
        """Ở v2, chấm 3 bản / hoàn thiện / chấm hook cũng được xem bình luận gốc + số kênh."""
        d = os.path.join(GOC, "CHANNEL", "TL4-T7-v2", "prompt")
        for ten, o in (("2b-cham.md", ("<<BINH_LUAN_GOC>>", "<<SU_THAT_KENH>>")),
                       ("2e-cham-hook.md", ("<<BINH_LUAN_GOC>>", "<<SU_THAT_KENH>>")),
                       ("2c-hoan-thien.md", ("<<BINH_LUAN_GOC>>",))):
            chu = io.open(os.path.join(d, ten), encoding="utf-8").read()
            for x in o:
                assert x in chu, "v2/{0} thiếu ô {1}".format(ten, x)
        # kênh cũ giữ nguyên lời nhắc cũ
        cu = io.open(os.path.join(GOC, "CHANNEL", "TL4-T7", "prompt", "2b-cham.md"),
                     encoding="utf-8").read()
        assert "<<BINH_LUAN_GOC>>" not in cu

    def test_so_voi_that(self):
        from core.vong_cham_sua import so_voi_that
        ret = [100 - i * 0.8 for i in range(101)]          # thật: rớt đều tới 20%
        ban_do = [{"doan": "mở", "tu_pct": 0, "den_pct": 10, "con_lai": 70},
                  {"doan": "ý 1", "tu_pct": 10, "den_pct": 30, "con_lai": 60},
                  {"doan": "hỏng", "con_lai": 50}]
        dong = so_voi_that(ban_do, ret)
        assert len(dong) == 2
        assert "đoán còn 70% người, thật 92%" in dong[0] and "(+22)" in dong[0]
        assert "thật 76%" in dong[1]
        assert so_voi_that(ban_do, []) == [] and so_voi_that("x", ret) == []

    @pytest.mark.parametrize("nhan,thu_muc", KENH)
    def test_loi_nhac_gac_ban_doc(self, nhan, thu_muc):
        chu = io.open(os.path.join(thu_muc, "2i-kiem-doc.md"), encoding="utf-8").read()
        for o in ("<<TRUOC>>", "<<DRAFT>>", "<<NGON_NGU>>"):
            assert o in chu, "{0}: 2i thiếu ô {1}".format(nhan, o)
        assert "OK" in chu and "---" in chu

    def test_gac_ban_doc_ok_thi_giu_co_sua_thi_nhan_viet_lai_thi_bo(self):
        from core.auto import LuotChay
        from core.auto_khau import BoiCanh, _kiem_ban_doc

        class _K:
            mo_hinh = "m"
            ngon_ngu = "ja"
            so_vong_cham = 3
            prompt = {"2i-kiem-doc.md": "gac <<TRUOC>> <<DRAFT>> <<NGON_NGU>>"}

        sau = "\n".join(["一人の夜、部屋の静けさ。"] * 30 + ["---"] + ["深く息をつかせる。"] * 30)
        sua_nho = sau.replace("深く息をつかせる。", "深く息をつかせるのです。", 3)

        def chay(tra):
            ai = _Ai([tra])
            bc = BoiCanh(goc=".", kenh=_K(), goi_chat=ai, on_log=lambda _d: None, ngu=lambda _g: None)
            return _kiem_ban_doc(bc, LuotChay(ma_kenh="K", ma_luot="L", thu_muc="."), _K(),
                                 {"NGON_NGU": "tiếng Nhật"}, "truoc", sau), ai

        ra, ai = chay("OK")
        assert ra == sau and "<<" not in ai.nhan[0] and "truoc" in ai.nhan[0]
        ra, _ = chay(sua_nho)
        assert ra == sua_nho
        ra, _ = chay(BAN_LA)
        assert ra == sau, "bản gác viết lại từ đầu thì bỏ"
        ra, _ = chay(sau.replace("---", ""))
        assert ra == sau, "mất dòng --- thì bỏ"

    def test_su_that_tu_luot_va_tim_luot_theo_tieu_de(self, tmp_path):
        from core.chi_so_ytb import su_that_tu_luot, tim_luot_theo_tieu_de
        auto = tmp_path / "PROJECTS" / "AUTO"
        luot = auto / "K-v2" / "0003"
        luot.mkdir(parents=True)
        io.open(str(luot / "1-tieu-de.txt"), "w", encoding="utf-8").write(
            "TITLE: 一人が好きな人だけに現れる5つの知的特徴｜心理学が明かした驚きの真実\nTHUMB: x\n")
        io.open(str(luot / "3-phu-de.srt"), "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:03,000\n夜の部屋。\n\n"
            "2\n00:01:00,000 --> 00:01:04,000\n一つ目の特徴は、考える習慣です。\n\n"
            "3\n00:09:30,000 --> 00:09:33,000\nチャンネル登録をお願いします。\n\n"
            "4\n00:09:55,000 --> 00:10:00,000\nご視聴ありがとうございました。\n")
        json.dump([{"doan": "mở", "tu_pct": 0, "den_pct": 10, "con_lai": 70}],
                  io.open(str(luot / "1-ban-do-rot-ghep.json"), "w", encoding="utf-8"))
        # khớp tiêu đề dù khác khoảng trắng / dấu
        d = tim_luot_theo_tieu_de("一人が好きな人だけに現れる5つの知的特徴 ｜ 心理学が明かした驚きの真実", str(auto))
        assert d == str(luot)
        assert tim_luot_theo_tieu_de("khác hẳn", str(auto)) == ""
        ret = [100 - i * 0.5 for i in range(101)]
        dong = su_that_tu_luot(d, ret)
        assert any(x.startswith("ý thứ nhất vào ở 1:00 (10% bài)") for x in dong)
        assert any(x.startswith("mời đăng ký ở 9:30 (95% bài)") for x in dong)
        assert any("đoán còn 70% người, thật 95%" in x for x in dong)

    @_CAN_HAI_KENH_THAT
    def test_kenh_v2_bat_vong_kenh_cu_giu_nguyen(self):
        from core.kenh import doc_kenh
        k = doc_kenh(os.path.join(GOC), "TL4-T7-v2")
        assert k.so_vong_cham == 3 and k.so_ban_va == 2 and k.so_ban_nhap == 5
        assert k.prompt.get("2g-cham-toan-bai.md", "").strip()
        assert k.prompt.get("2h-va-toan-bai.md", "").strip()
        cu = doc_kenh(os.path.join(GOC), "TL4-T7")
        assert cu.so_vong_cham == 0, "TL4-T7 cũ phải chạy y như trước"
        assert "2g-cham-toan-bai.md" not in cu.prompt

    def test_chu_bia_trung_luot_truoc(self, tmp_path):
        from core.auto_khau import _chu_bia_trung_luot_truoc
        kenh = tmp_path / "AUTO" / "K"
        (kenh / "0009").mkdir(parents=True)
        (kenh / "0012").mkdir()
        io.open(str(kenh / "0009" / "1-tieu-de.txt"), "w", encoding="utf-8").write(
            "TITLE: x\nTHUMB: 『これ』を一人でしているなら あなたのIQは非常に高いかも\n")
        d = str(kenh / "0012")
        assert _chu_bia_trung_luot_truoc(d, "『これ』を一人でしているなら あなたのIQは非常に高いかも")
        assert _chu_bia_trung_luot_truoc(d, "これを一人でしているならあなたのIQは非常に高いかも")
        assert not _chu_bia_trung_luot_truoc(d, "一人が好きな人 5つの知的特徴")
        # lượt hiện tại không tự so với chính nó
        io.open(str(kenh / "0012" / "1-tieu-de.txt"), "w", encoding="utf-8").write(
            "TITLE: y\nTHUMB: 友達 少なくていい\n")
        assert not _chu_bia_trung_luot_truoc(d, "友達 少なくていい")
        # kênh khác trong cùng PROJECTS/AUTO cũng được so — TL4-T7 và TL4-T7-v2
        # đăng lên cùng một kênh YouTube
        k2 = tmp_path / "AUTO" / "K-v2" / "0001"
        k2.mkdir(parents=True)
        assert _chu_bia_trung_luot_truoc(str(k2), "『これ』を一人でしているなら あなたのIQは非常に高いかも")

    def test_su_that_kenh_doc_tep_ghi_tay(self, tmp_path):
        from core.chi_so_ytb import su_that_kenh
        tep = tmp_path / "su-that-cham.txt"
        io.open(str(tep), "w", encoding="utf-8").write("- V7: ý 1 vào ở 3:55, AVD 4:40 rơi đúng đó\n")
        ra = su_that_kenh("KHONG-CO-KENH-NAY", str(tmp_path), tep_them=str(tep))
        assert "V7: ý 1 vào ở 3:55" in ra
        assert su_that_kenh("KHONG-CO-KENH-NAY", str(tmp_path)) == ""


# ── 5. Vá kiểu "thay đoạn" — patch nhỏ thay vì viết lại cả bài (29/09/2026) ──

class TestApDungThayDoan:
    def test_ap_dung_vai_cap_dung(self):
        ban = "chào buổi sáng. hôm nay trời đẹp. tạm biệt."
        sua = [{"tim": "chào buổi sáng", "thay": "chào buổi tối"},
              {"tim": "tạm biệt", "thay": "hẹn gặp lại"}]
        ra, ap = ap_dung_thay_doan(ban, sua)
        assert ra == "chào buổi tối. hôm nay trời đẹp. hẹn gặp lại."
        assert ap == 2

    def test_cap_khong_tim_thay_thi_bo_qua_khong_loi(self):
        ban = "chào buổi sáng. hôm nay trời đẹp."
        sua = [{"tim": "không có trong bài", "thay": "x"},
              {"tim": "hôm nay trời đẹp", "thay": "hôm nay trời mưa"}]
        ghi_lai = []
        ra, ap = ap_dung_thay_doan(ban, sua, ghi=ghi_lai.append)
        assert ra == "chào buổi sáng. hôm nay trời mưa."
        assert ap == 1
        assert any("không thấy" in d for d in ghi_lai)

    def test_moi_cap_chi_thay_lan_dau_gap(self):
        ban = "lặp. lặp. lặp."
        ra, ap = ap_dung_thay_doan(ban, [{"tim": "lặp", "thay": "khác"}])
        assert ra == "khác. lặp. lặp."
        assert ap == 1

    def test_khong_co_cap_nao_thi_giu_nguyen(self):
        ban = "giữ nguyên."
        ra, ap = ap_dung_thay_doan(ban, [])
        assert ra == ban and ap == 0

    def test_cap_khong_phai_mapping_bi_bo_qua(self):
        ra, ap = ap_dung_thay_doan("a", ["không phải dict", 123])
        assert ra == "a" and ap == 0


class TestVongChamSuaKieuThayDoan:
    def test_kieu_thay_doan_ap_dung_dung_cho_thay(self):
        tim = BAN[: len(BAN) // 4] or BAN[:10]
        assert tim and tim in BAN
        thay = tim + CAU_THEM

        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="đoạn mở nhạt",
                          mat_gi_cua_goc="câu nghịch lý"),
                    chon_ban_co(CAU_THEM)])
        va = _Ai([_json(sua=[{"tim": tim, "thay": thay}])])
        ban, bien_ban, _bd = vong_cham_sua(
            cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=1, kieu_va="thay_doan")

        assert CAU_THEM in ban
        assert ban == BAN.replace(tim, thay, 1)
        assert "nhận bản vá A" in bien_ban
        # lời nhắc vá phải dùng khuôn "thay đoạn" (đòi JSON {"sua": [...]}) chứ
        # không phải khuôn nguyên văn cũ.
        assert '"sua"' in va.nhan[0] and "KHÔNG viết lại cả bài" in va.nhan[0]

    def test_khong_ap_duoc_cap_nao_thi_bo_ban_va_giu_ban_cu(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x")])
        # "tim" không khớp gì trong bài — không áp được cặp nào.
        va = _Ai([_json(sua=[{"tim": "cụm không tồn tại trong BAN", "thay": "y"}])])
        ban, bien_ban, _bd = vong_cham_sua(
            cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=1, kieu_va="thay_doan")
        assert ban == BAN
        assert "không áp được cặp thay nào" in bien_ban
        assert len(cham.nhan) == 1, "không có bản vá nào dùng được thì không tốn lượt chấm so"

    def test_json_hong_thi_bo_ban_va_khong_vo_vong(self):
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="x")])
        va = _Ai(["đây không phải JSON hợp lệ chút nào"])
        ban, bien_ban, _bd = vong_cham_sua(
            cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=1, kieu_va="thay_doan")
        assert ban == BAN
        assert "không bản vá nào dùng được" in bien_ban

    def test_mac_dinh_khong_truyen_kieu_va_thi_hanh_vi_y_het_cu(self):
        """`kieu_va` mặc định phải là `"nguyen_van"` — không đổi hành vi cũ khi
        nơi gọi chưa biết tới tham số mới."""
        cham = _Ai([_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="thiếu nghịch lý",
                          mat_gi_cua_goc="con số nghiên cứu"),
                    chon_ban_co(CAU_THEM)])
        va = _Ai([BAN_VA])
        ban, bien_ban, _bd = vong_cham_sua(cham, va, BAN, GOC_DOI_THU, so_vong=1, so_ban_va=1)
        assert ban == BAN_VA
        assert "nhận bản vá A" in bien_ban
        # lời nhắc vá phải dùng khuôn NGUYÊN VĂN cũ (đòi trả nguyên văn cả bài).
        assert "Trả về NGUYÊN VĂN toàn" in va.nhan[0]


# ── Mục E 29/09/2026: nơi gọi thật (`auto_khau._vong_cham_sua_luot`) bật
# `thay_doan` MẶC ĐỊNH, đọc `vong_cham_sua_kieu` trong kenh.yaml để tắt. ──────

#: Dấu nhận khuôn vá của KÊNH (kiểu nguyên văn) trong lời nhắc gửi đi.
_DAU_KHUON_KENH = "KHUON-VA-CUA-KENH-NGUYEN-VAN"


class _KenhGia:
    mo_hinh = "m"
    ngon_ngu = "ja"
    so_ban_va = 1
    ma = "K"

    def __init__(self, duong):
        self.duong = duong
        self.prompt = {
            "2g-cham-toan-bai.md": "cham <<COMPETITOR_TRANSCRIPT>>\n<<CAC_BAN>>",
            "2h-va-toan-bai.md": _DAU_KHUON_KENH + " — Trả về NGUYÊN VĂN toàn bộ "
                                 "<<CHO_KEM>> <<COMPETITOR_TRANSCRIPT>> <<DRAFT>>",
        }


def _chay_luot(tmp_path, kenh_yaml, tra_cham, tra_va):
    from core.auto import LuotChay
    from core.auto_khau import BoiCanh, _vong_cham_sua_luot

    if kenh_yaml is not None:
        io.open(str(tmp_path / "kenh.yaml"), "w", encoding="utf-8").write(kenh_yaml)
    k = _KenhGia(str(tmp_path))
    ai = _Ai(tra_cham + tra_va)
    bc = BoiCanh(goc=str(tmp_path), kenh=k, goi_chat=ai, on_log=lambda _d: None,
                 ngu=lambda _g: None)
    ra = _vong_cham_sua_luot(
        bc, LuotChay(ma_kenh="K", ma_luot="L", thu_muc=str(tmp_path)), k,
        {"NGON_NGU": "tiếng Nhật", "BINH_LUAN_GOC": "(không có)",
         "SU_THAT_KENH": "(chưa có)"},
        BAN, GOC_DOI_THU, str(tmp_path), nhan="ghep", so_vong=1)
    return ra, ai


class TestNoiDayKieuVaAutoKhau:
    def test_mac_dinh_thay_doan_dung_khuon_json_khong_dung_khuon_kenh(self, tmp_path):
        """Kênh không khai khoá → `thay_doan`. Lời nhắc vá phải là khuôn JSON dựng
        sẵn, KHÔNG phải `2h` nguyên văn của kênh: dùng khuôn kênh thì AI trả cả
        bài, `loc_json` hỏng và mọi bản vá bị bỏ."""
        tim = BAN[:40]
        cham = [_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="đoạn mở nhạt",
                      mat_gi_cua_goc="câu nghịch lý")]
        va = [_json(sua=[{"tim": tim, "thay": tim + CAU_THEM}])]
        ra, ai = _chay_luot(tmp_path, None, cham, va + [chon_ban_co(CAU_THEM)])
        loi_nhac_va = ai.nhan[1]
        assert '"sua"' in loi_nhac_va and _DAU_KHUON_KENH not in loi_nhac_va
        assert ra == BAN.replace(tim, tim + CAU_THEM, 1)

    def test_kenh_dat_nguyen_van_thi_quay_ve_khuon_kenh(self, tmp_path):
        cham = [_json(chon="A", giu_hay_sua="sửa", cho_kem_nhat="thiếu nghịch lý",
                      mat_gi_cua_goc="con số")]
        ra, ai = _chay_luot(tmp_path, "vong_cham_sua_kieu: nguyen_van\n", cham,
                            [BAN_VA, chon_ban_co(CAU_THEM)])
        assert _DAU_KHUON_KENH in ai.nhan[1]
        assert CAU_THEM in ra

    def test_doc_kieu_va_kenh(self, tmp_path):
        from core.auto_khau import BoiCanh, _kieu_va_kenh
        bc = BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=None)
        k = _KenhGia(str(tmp_path))
        assert _kieu_va_kenh(bc, k) == "thay_doan", "không có kenh.yaml → mặc định bật"
        for chu, mong in (("vong_cham_sua_kieu: nguyen_van\n", "nguyen_van"),
                          ("vong_cham_sua_kieu: THAY_DOAN\n", "thay_doan"),
                          ("vong_cham_sua_kieu: bay-ba\n", "thay_doan"),
                          ("ten: K\n", "thay_doan")):
            io.open(str(tmp_path / "kenh.yaml"), "w", encoding="utf-8").write(chu)
            assert _kieu_va_kenh(bc, k) == mong, chu
