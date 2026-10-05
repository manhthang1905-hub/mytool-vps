"""05/10: trả lời bình luận ĐÚNG nội dung video (lời thoại), đúng ngôn ngữ kênh, gõ như người (không kaomoji)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vm"))
import may_cmt_dom as m  # noqa: E402


def test_van_ban_srt(tmp_path):
    p = tmp_path / "a.srt"
    p.write_text("1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n2\n00:00:03,000 --> 00:00:05,000\n今日は銭湯の話です\n",
                 encoding="utf-8")
    assert m.van_ban_srt(str(p)) == "こんにちは 今日は銭湯の話です"
    assert m.van_ban_srt(str(tmp_path / "khong.srt")) == ""


def test_chon_doan_ngan_dua_nguyen_dai_chon_doan_lien_quan():
    assert m.chon_doan("abc", "x") == "abc"
    dai = "あ" * 3000 + "銭湯で心も体も整う五百円の必要経費" + "い" * 6000
    ra = m.chon_doan(dai, "500円の銭湯は最高の必要経費", toi_da=1500, mo_dau=300)
    assert len(ra) < 2000 and "必要経費" in ra


def test_lam_sach_bo_kaomoji_va_emoji():
    s = m.lam_sach_tra_loi("本当にそうですね(^^) また見てくださいね😊 www")
    assert "(^^)" not in s and "😊" not in s and "www" not in s and "本当にそうですね" in s


def test_dung_ngon_ngu():
    assert m.dung_ngon_ngu("ありがとうございます", "ja")
    assert not m.dung_ngon_ngu("Thank you so much", "ja")
    assert m.dung_ngon_ngu("anything", "es")          # không có mẫu → không chặn


def test_prompt_co_loi_thoai_va_luat_go_nhu_nguoi():
    p = m.tao_prompt("銭湯の話よかった", "Japanese", "warm", "銭湯の心理", "mô tả", "今日は銭湯の話です")
    assert "transcript" in p and "今日は銭湯の話です" in p and "kaomoji" in p and "Japanese" in p
