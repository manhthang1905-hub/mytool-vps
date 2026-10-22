# Luật của chủ dự án

Đây là những bài học chủ dự án đã chốt khi vận hành VPS đầu tiên (09–10/2026). Chúng áp dụng cho MỌI ngách và mọi máy.

Phiên Claude trên máy mới đọc tệp này trước khi đổi bất cứ điều gì. Mỗi luật kèm lý do để còn áp đúng chỗ. Số liệu riêng của từng kênh không nằm ở đây.

## Mục tiêu
- Máy tự vận hành kênh như người thật: tự học, tự sửa, chạy cả năm không cần người. Chỉ cần ví ShopAPI còn tiền.
- Mục tiêu là sản phẩm tốt nhất, kiếm tiền nhanh, chiếm top ngách. Không đặt trần chi phí, nhưng không gọi API trả tiền theo vòng lặp vô ích.
- "Việc của bạn" chỉ chứa việc máy không được làm:
  - đăng nhập Google, 2FA hoặc xác minh điện thoại;
  - nạp tiền;
  - bản quyền Windows, thuê VPS;
  - quyết định chiến lược chủ được hỏi.

  Mọi việc khác phải có bộ tự làm.
- Bật máy lên là mọi thứ tự chạy (`core/van_hanh.py`). Thành phần chạy lâu mới thêm vào phải có đủ 3 thứ: đường tự bật, chó canh, dọn khoá cũ sau khi khởi động lại.
- Không chết im lặng: hỏng thì tự sửa hoặc báo, không đứng yên.

## Chất lượng: thà không đăng còn hơn đăng đồ kém
- ShopAPI lỗi thì chỉ thử lại. Cấm mọi đường lui hạ chất lượng (ví dụ clip làm từ ảnh tĩnh).
- **Bìa sai chữ là tối kỵ.** Cổng chữ bìa (`core/cong_chu.py`) hoạt động như sau:
  - soát chữ định viết trước khi vẽ;
  - đọc lại chữ trên ảnh 2 lần độc lập, phải khớp từng ký tự;
  - bìa đạt được đóng dấu `chu_khop` kèm sha1 của tệp;
  - mọi lối ra YouTube (đăng, thay bìa, A/B) từ chối bìa không có dấu.

  Ưu tiên chữ do code vẽ, không để máy vẽ ảnh tự viết chữ.
- Giọng đọc dùng nguyên bản cổng giọng trả về. Không chỉnh tốc độ hay cao độ. Giọng không ổn thì đổi `voice_id`.
- Mỗi kênh một giọng riêng. Nhiều kênh chung một giọng là dấu hiệu "mạng kênh sản xuất hàng loạt".

## Không lách YouTube
- Luôn khai "nội dung có AI" (nhãn chỉnh sửa/tổng hợp). Nhãn này không làm giảm hiển thị. Không khai mới là chỗ nguy, vì có thể mất quyền kiếm tiền.
- Không xoá dấu chìm (SynthID), không giả chữ ký phần mềm dựng, không đổi tên hay thông số tệp để giấu AI. Đổi tên tệp mp4/srt/thumb thành tiêu đề cũng không có tác dụng gì.
- Kịch bản không được chép video nguồn. Cổng độc đáo (`core/do_doc_dao.py`) đo tỉ lệ trùng: trùng trên 15% thì tự viết lại bằng giọng kênh. Rủi ro lớn nhất là bị từ chối kiếm tiền khi YouTube xét duyệt.
- Đăng đều, khoảng 1 video/ngày/kênh. Đăng dồn nhiều video trong vài ngày làm lượt hiển thị tụt mạnh.

## Học đúng chỗ
- Học bìa từ ảnh bìa THẬT trên YouTube (`i.ytimg.com`), không học từ tệp tool tự làm. Chủ có thể đã đổi bìa tay.
- Mỗi kênh học từ số liệu của chính nó và bám khuôn bìa thắng của nó. Chỉ khoảng 1/5 video thử kiểu khác.
- Chọn và phân cụm nội dung bằng LLM theo nghĩa, không lọc bằng từ khoá.
- Mọi quyết định của AI phải:
  - đặt nhiều giả thuyết;
  - kiểm bằng số và bằng mã;
  - tự phản biện và ghi độ tin.

  Quyền tự áp dụng chỉ mở khi tỉ lệ đúng đã được kiểm.
- Lời nhắc hay khuôn mới phải tạo thử ra kết quả thật rồi chấm, chứ không đoán.
- Mỗi bộ phận có não riêng (`core/nao_bo_phan`): ghi quyết định, lỗi và kết quả thành bài học, mỗi đêm chắt lọc. Bỏ dữ liệu của video chưa được phát (dưới 50 lượt hiển thị).

## Tăng trưởng
- Nút nghẽn để vào YPP thường là lượt đăng ký, không phải giờ xem. Dùng hình mờ, trang chủ kênh, trailer, ghim bình luận, câu kêu gọi đăng ký giữa video.
- A/B bìa bằng «Thử nghiệm A/B» của Studio. Máy tự bật, mỗi lần chỉ thử bìa.
- Đổi tiêu đề video trượt được tự làm, có rào:
  - không đụng video đang ngang hoặc trên trung vị kênh;
  - mỗi video tối đa 1 lần/14 ngày;
  - đo CTR trước/sau, tệ hơn thì tự đổi lại.
- Ngôn ngữ và địa điểm kênh chỉ đặt một lần, làm trên giao diện youtube.com như người, rồi đọc lại để kiểm.

## Vận hành máy
- Mỗi lúc chỉ chạy một việc nặng. Không chạy cả bộ pytest trên VPS; chỉ chạy test của phần vừa sửa.
- Việc nặng xếp hàng lần lượt, không bỏ việc khi máy bận. Phần nhẹ thì tách ra chạy ngay.
- Chỉ đổi mã đang chạy trong phút :15–:45, để tránh giờ đăng và giờ dựng.
- Không bao giờ dừng tiến trình đang đăng, đang dựng hay đang làm phụ đề. Kiểm `.khoa-may` trước.
- Không gõ mật khẩu hay 2FA thay người. Mật khẩu chỉ nằm trong `bi-mat/` dạng mã hoá DPAPI, không in ra và không ghi log.
- Không tự bật `tu_chay`, `tu_dang`, `tu_duyet`, `tu_don`, `ngan_sach_ngay`. Chủ kênh tự quyết các công tắc tiền và tự chạy.
  Ngoại lệ chủ đã duyệt: kênh do luồng tự động mở — thay kênh hỏng (D20, 20/10) và khởi tạo VPS mới (D28, 22/10) — được
  máy bật `tu_chay`/`tu_duyet`/`tu_dang` SAU khi có kênh thương hiệu + UC ghim + thiết lập 11/11.
- Không đổi tên, handle hay banner của kênh chính. Không xoá gì trên YouTube nếu không được bảo.
- Đổi luật cố định (ví dụ gỡ một cổng duyệt) thì phải hỏi chủ rõ từng luật.
- Ổ đĩa: video đã lên YouTube thì máy tự xoá tệp nặng, và tự xoá Chrome bản cũ. Ổ còn dưới 10 GB thì dừng dựng video mới và báo.

## Báo cáo cho chủ
- Ngắn gọn, bằng tiếng Việt, nói kết quả trước, không kể chuyện bản nháp.
- Chủ hỏi "sao kênh X tệ" thì đọc số thật trước: lượt hiển thị, CTR, giữ chân, nguồn traffic. Sau đó soát ảnh bìa thật, rồi mới kết luận.
