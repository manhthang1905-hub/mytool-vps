// Cắm CỜ "tab này là tab lấy lời thoại" NGAY KHI TRANG BẮT ĐẦU NẠP.
//
// ═══ VÌ SAO CẦN MỘT TỆP RIÊNG CHỈ ĐỂ LÀM MỘT VIỆC (đo thật 22/09/2026, 09:52–10:03) ═══
//
// Phiên thật của kênh TL1-T7 ra "0 lấy được · 0 không có bảng phụ đề · 8 chưa về", và
// LevelDB của tiện ích (`Local Extension Settings/ghbmnnjooekpmoecnnnilnnbdlolhkhi`) KHÔNG
// có một dòng log nào chứa "lời thoại" — tức `loi-thoai.js` thoát trước khi kịp báo gì.
//
// Thủ phạm nằm trong tệp phiên Chromium
// `TL1-T7/Data/profile/Default/Sessions/Session_13434519629720236` (mtime 10:05:38): nó
// chứa CẢ HAI địa chỉ cho cùng một video —
//
//     https://www.youtube.com/watch?v=i2EAnLd8Duo&shopapi_lt=1
//     https://www.youtube.com/watch?v=i2EAnLd8Duo
//
// Tức tab ĐÃ mở đúng địa chỉ kèm dấu (đường mở tab của agent không sai một ly), rồi YouTube
// tự `replaceState` gỡ `&shopapi_lt=1` đi để chuẩn hoá địa chỉ. `loi-thoai.js` chạy ở
// `document_idle` — tới lúc ấy dấu đã mất, và cái cửa `if (!…has('shopapi_lt')) return;`
// đóng sập trong im lặng.
//
// Bài học không phải "đổi selector" mà là: **đừng để sự thật sống trong một chỗ YouTube
// được phép viết lại**. Nay sự thật nằm ở BA chỗ, và `loi-thoai.js` nhận bất kỳ chỗ nào:
//
//   1. `background.js` bắt `chrome.tabs.onUpdated` — sự kiện ấy tới kèm địa chỉ GỐC, trước
//      khi YouTube kịp gỡ dấu; đây là nguồn chính.
//   2. cờ `sessionStorage` do TỆP NÀY cắm ở `document_start` — sớm hơn mọi thứ YouTube làm.
//   3. địa chỉ còn dấu (nết cũ) — vẫn giữ, vì có trang YouTube không chuẩn hoá.
//
// Tệp này là lớp 2. Nó tồn tại riêng vì `run_at` là thuộc tính của TỆP trong manifest,
// không phải của một dòng mã: muốn chạy ở `document_start` thì phải là một tệp khác.
// `document_idle` cho `loi-thoai.js` vẫn đúng — nó cần DOM đã dựng mới bấm được nút.
//
// Cờ sống đúng MỘT lần nạp trang: `loi-thoai.js` đọc rồi xoá ngay. Lần nạp kế (background
// điều hướng sang video kế, địa chỉ lại kèm dấu) thì tệp này cắm lại. Nhờ vậy một người
// ngồi xem tiếp trong đúng tab ấy sau khi lượt xong không bị hút oan.
(() => {
  'use strict';
  if (location.hostname !== 'www.youtube.com') return;
  if (location.pathname !== '/watch') return;
  if (!new URLSearchParams(location.search).has('shopapi_lt')) return;
  try { sessionStorage.setItem('shopapi_lt', '1'); } catch (e) {}
})();
